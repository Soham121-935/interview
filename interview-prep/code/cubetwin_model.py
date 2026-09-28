"""
cubetwin_model.py
=================

A dependency-free (stdlib only) reference implementation of the physics that the
CubeTwin CubeSat energy digital-twin simulator describes on its public page:

    https://aerospace.ishavasyam.org/space/cubesat

Why this file exists
--------------------
The iTelematics / EV Society CubeTwin 12-week roadmap asks students to build
exactly this: a `calculateOrbitalPeriod()` function, a solar/load power model, an
energy-integrating battery model with SOC limits, a mode state machine with
safe-mode hysteresis, fault injection, telemetry logging, energy-accounting
closure and a seeded Monte Carlo uncertainty runner.

Every equation below is taken from the published CubeTwin lesson cards:

    T      = 2*pi*sqrt((Re + h)^3 / mu)                       (orbit & eclipse)
    Psolar = G * A * eta_cell * derating * max(0, cos theta)  (solar & PMAD)
    Pnet   = Psolar_delivered - Pload                         (power balance)
    E      = E + eta_c * Pnet * dt/3600            (charging)
    E      = E + Pnet * dt/(3600 * eta_d)          (discharging)
    SOC    = 100 * E / usable_capacity,  DoD = 100 - SOC
    Vterm  = OCV(SOC) - I * Rinternal
    dT     = dt/Cth * (I^2*R + Qext - (T - Tbus)/Rth)

Units are explicit everywhere: kilometres, watts, watt-hours, seconds, degrees C,
ohms.

Honest scope: this is a teaching/portfolio artefact, not flight software. No
measured data calibrates it. Simulation results are not flight evidence.
"""

from __future__ import annotations

import copy
import math
import random
import statistics
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants (published CubeTwin model assumptions)
# ---------------------------------------------------------------------------

RE_KM: float = 6371.0                # Earth mean radius [km]
MU_KM3_S2: float = 398600.4418       # Earth gravitational parameter [km^3/s^2]
SOLAR_CONSTANT_W_M2: float = 1361.0  # mean total solar irradiance [W/m^2]

SECONDS_PER_MINUTE = 60.0
SECONDS_PER_HOUR = 3600.0


# ---------------------------------------------------------------------------
# 1. Orbit
# ---------------------------------------------------------------------------

def orbital_period(altitude_km: float, mu: float = MU_KM3_S2, re: float = RE_KM) -> float:
    """Circular two-body orbital period in MINUTES for an altitude in km.

    T = 2*pi*sqrt(a^3/mu) with a = Re + h.  Reference: 500 km -> ~94.5 min.
    """
    if altitude_km <= -re:
        raise ValueError("altitude_km must keep the orbit radius positive")
    a = re + altitude_km
    return 2.0 * math.pi * math.sqrt(a ** 3 / mu) / SECONDS_PER_MINUTE


def eclipse_fraction(beta_deg: float, altitude_km: float, re: float = RE_KM) -> float:
    """Fraction of a circular orbit in Earth's shadow for a given beta angle.

    f = (1/pi) * arccos( sqrt(h^2 + 2*Re*h) / ((Re + h) * cos(beta)) )

    beta = 0 deg is the worst case: ~0.378 at 500 km, i.e. ~35.7 min of a
    94.5 min orbit. Returns 0.0 for geometries with no eclipse at all (covers a
    controlled edge case rather than crashing the caller). CubeTwin's simplified
    model instead takes eclipse duration as a direct input and always starts each
    orbit in sunlight.
    """
    if not -90.0 <= beta_deg <= 90.0:
        raise ValueError("beta_deg must lie within [-90, 90] degrees")
    numerator = math.sqrt(altitude_km ** 2 + 2.0 * re * altitude_km)
    denominator = (re + altitude_km) * math.cos(math.radians(beta_deg))
    if denominator <= 0 or numerator / denominator >= 1.0:
        return 0.0      # permanent sunlight for this geometry
    return math.acos(numerator / denominator) / math.pi


# ---------------------------------------------------------------------------
# 2. Solar generation and PMAD
# ---------------------------------------------------------------------------

def solar_power_w(
    g_w_m2: float = SOLAR_CONSTANT_W_M2,
    area_m2: float = 0.0583,   # tuned so the reference case peaks at 20 W
    cell_efficiency: float = 0.28,
    derating: float = 0.9,
    incidence_deg: float = 0.0,
    pmad_efficiency: float = 0.90,
) -> tuple[float, float]:
    """Return (array peak power, delivered power after PMAD) in W.

    Psolar      = G * A * eta_cell * derating * max(0, cos theta)
    P_delivered = Psolar * eta_pmad

    Reference case: 20 W peak, 90% PMAD -> 18 W delivered to the bus.
    """
    for name, value in (
        ("area_m2", area_m2), ("cell_efficiency", cell_efficiency),
        ("derating", derating), ("pmad_efficiency", pmad_efficiency),
    ):
        if value < 0.0:
            raise ValueError(f"{name} must be non-negative")
    cos_theta = max(0.0, math.cos(math.radians(incidence_deg)))
    peak_w = g_w_m2 * area_m2 * cell_efficiency * derating * cos_theta
    return peak_w, peak_w * pmad_efficiency


# ---------------------------------------------------------------------------
# 3. Battery model
# ---------------------------------------------------------------------------

# Illustrative 2S Li-ion pack OCV(SOC) lookup [V]. CubeTwin: "OCV is an
# illustrative editable pack lookup"; this table sits near 8.22 V at 80% SOC,
# matching their published bus-voltage example. Not a cell datasheet.
OCV_TABLE: tuple[tuple[float, float], ...] = (
    (0.00, 6.00), (0.10, 6.90), (0.20, 7.20), (0.30, 7.36), (0.40, 7.48),
    (0.50, 7.64), (0.60, 7.84), (0.70, 8.04), (0.80, 8.22), (0.90, 8.32),
    (1.00, 8.40),
)


def ocv_from_soc(soc_fraction: float) -> float:
    """Piecewise-linear OCV(SOC) [V]."""
    soc = min(1.0, max(0.0, soc_fraction))
    for i in range(1, len(OCV_TABLE)):
        x0, y0 = OCV_TABLE[i - 1]
        x1, y1 = OCV_TABLE[i]
        if soc <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (soc - x0) / (x1 - x0)
    return OCV_TABLE[-1][1]


@dataclass
class Battery:
    """Energy-integrating battery: stored energy is the state, power is the input.

    Sign conventions (matching the CubeTwin glossary):
      * `net_power_w > 0` means surplus bus power available for CHARGING.
      * positive battery current means DISCHARGE, so terminal voltage sags under
        load and rises under charge.
    """
    capacity_wh: float = 40.0
    soc0: float = 0.80
    # 0.97 charge efficiency is INFERRED: it reproduces the 7.839 Wh charge +
    # discharge loss that CubeTwin publishes for the baseline run. Their charge
    # efficiency default is not exposed on the page; the published worked example
    # uses 95% DISCHARGE efficiency, which is the value used here for discharge.
    eta_charge: float = 0.97
    eta_discharge: float = 0.95
    r_internal_ohm: float = 0.12
    # controller thresholds (fractions of usable capacity)
    reserve_soc: float = 0.30
    safe_entry_soc: float = 0.20
    recovery_soc: float = 0.35
    recovery_dwell_s: float = 300.0
    # lumped thermal model (uncalibrated, educational)
    temp_c: float = 20.0
    bus_temp_c: float = 20.0
    c_th_j_per_k: float = 4000.0
    r_th_k_per_w: float = 2.0
    q_external_w: float = 0.90
    temp_enabled: bool = True

    # bookkeeping (reset by simulate(); used for the energy balance)
    energy_wh: float = field(init=False)
    rejected_wh: float = 0.0   # charge refused at 100% SOC
    loss_wh: float = 0.0       # charge + discharge conversion losses
    removed_wh: float = 0.0    # energy dropped by a capacity-fade fault

    def __post_init__(self) -> None:
        self.energy_wh = self.soc0 * self.capacity_wh

    # --- state ---------------------------------------------------------------
    @property
    def soc(self) -> float:
        return 0.0 if self.capacity_wh <= 0 else min(1.0, max(0.0, self.energy_wh / self.capacity_wh))

    @property
    def dod(self) -> float:
        return 1.0 - self.soc

    def terminal_voltage(self, discharge_power_w: float) -> float:
        """Vterm = OCV(SOC) - I*Rinternal with I = requested battery power / OCV.

        `discharge_power_w` is the power the battery must supply (>0 discharges).
        Diagnostic approximation, not a coupled electrical solver.
        """
        ocv = ocv_from_soc(self.soc)
        current_a = discharge_power_w / ocv if ocv > 0 else 0.0
        return ocv - current_a * self.r_internal_ohm

    # --- faults --------------------------------------------------------------
    def set_capacity(self, new_capacity_wh: float) -> None:
        """Capacity fade that never creates energy (no recovery inflation)."""
        self.capacity_wh = max(0.0, new_capacity_wh)
        if self.energy_wh > self.capacity_wh:
            self.removed_wh += self.energy_wh - self.capacity_wh
            self.energy_wh = self.capacity_wh

    def set_resistance(self, new_r_ohm: float) -> None:
        self.r_internal_ohm = max(0.0, new_r_ohm)

    # --- integration ---------------------------------------------------------
    def step(self, net_power_w: float, dt_s: float) -> tuple[float, float]:
        """Advance one time step. Returns (battery_energy_delivered_to_loads_wh,
        unmet_load_wh) so the caller can attribute served vs unmet demand.

        Charging    (net >= 0): E += eta_c * Pnet * dt/3600
        Discharging (net <  0): E += Pnet * dt/(3600 * eta_d)
        """
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")

        delivered_wh = 0.0
        unmet_wh = 0.0

        if net_power_w >= 0.0:
            energy_in = net_power_w * dt_s / SECONDS_PER_HOUR
            stored = energy_in * self.eta_charge
            self.loss_wh += energy_in - stored
            headroom = self.capacity_wh - self.energy_wh
            if stored > headroom:
                self.rejected_wh += stored - headroom   # record rejected charge
                stored = headroom
            self.energy_wh += stored
        else:
            deficit_wh = -net_power_w * dt_s / SECONDS_PER_HOUR   # energy the loads still need
            drawn_needed = deficit_wh / self.eta_discharge
            if drawn_needed <= self.energy_wh:
                drawn = drawn_needed
                delivered_wh = deficit_wh
            else:
                drawn = self.energy_wh                        # battery empties
                delivered_wh = drawn * self.eta_discharge
                unmet_wh = deficit_wh - delivered_wh
            self.loss_wh += drawn - (drawn * self.eta_discharge)
            self.energy_wh -= drawn

        self.energy_wh = min(self.capacity_wh, max(0.0, self.energy_wh))

        if self.temp_enabled:
            ocv = max(ocv_from_soc(self.soc), 1e-9)
            current_a = abs(net_power_w) / ocv
            heat_w = current_a ** 2 * self.r_internal_ohm
            cooled_w = (self.temp_c - self.bus_temp_c) / self.r_th_k_per_w
            self.temp_c += dt_s / self.c_th_j_per_k * (heat_w + self.q_external_w - cooled_w)

        return delivered_wh, unmet_wh


# ---------------------------------------------------------------------------
# 4. Scenario, schedule and faults
# ---------------------------------------------------------------------------

@dataclass
class Activity:
    """A scheduled mission activity. A deferred activity is skipped, not rescheduled."""
    name: str
    mode: str                 # boot | detumble | payload | downlink | ...
    start_s: float
    duration_s: float
    power_w: float            # bus load while this activity runs [W]
    critical: bool = False    # critical activities survive safe mode

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


@dataclass
class Fault:
    """A timed fault window: change one thing, measure the consequence."""
    kind: str                 # solar_degradation | capacity_fade | extra_load | resistance_rise
    start_s: float
    duration_s: float
    severity: float = 0.30    # fractional loss, extra watts, or new resistance [ohm]

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


@dataclass
class Scenario:
    """Complete set of mission inputs, schedule, faults and duration."""
    name: str = "Reference 3U LEO mission"
    altitude_km: float = 500.0
    inclination_deg: float = 51.6
    eclipse_minutes: float = 35.0
    duration_h: float = 24.0
    dt_s: float = 10.0

    peak_solar_w: float = 20.0      # array output at the cells, before PMAD
    pmad_efficiency: float = 0.90   # -> 18 W delivered
    nominal_load_w: float = 8.0
    essential_load_w: float = 3.0
    undervoltage_v: float = 6.8

    battery: Battery = field(default_factory=Battery)
    activities: list[Activity] = field(default_factory=list)
    faults: list[Fault] = field(default_factory=list)

    @staticmethod
    def reference() -> "Scenario":
        """The published CubeTwin reference mission (illustrative defaults)."""
        return Scenario(
            activities=[
                Activity("boot",       "boot",     0.0,           60.0,  3.0, True),
                Activity("detumble",   "detumble", 60.0,          240.0, 8.0),
                Activity("image-1",    "payload",  4 * 3600.0,    600.0, 18.0),
                Activity("downlink-1", "downlink", 5 * 3600.0,    480.0, 14.0),
            ],
            battery=Battery(capacity_wh=40.0, soc0=0.80, reserve_soc=0.30,
                            safe_entry_soc=0.20, recovery_soc=0.35),
        )


@dataclass
class TelemetrySample:
    t_s: float
    sunlight: bool
    truth_soc: float
    observed_soc: float        # NaN during a telemetry dropout
    solar_w: float
    load_w: float
    voltage_v: float
    temp_c: float
    mode: str


@dataclass
class RunResult:
    scenario: Scenario
    samples: list[TelemetrySample]
    events: list[tuple[float, str]]
    outcomes: dict[str, dict[str, float | bool]]
    metrics: dict[str, float]

    def csv(self) -> str:
        rows = ["t_s,sunlight,truth_soc_pct,observed_soc_pct,solar_w,load_w,voltage_v,temp_c,mode"]
        for s in self.samples:
            obs = "" if math.isnan(s.observed_soc) else f"{s.observed_soc * 100:.3f}"
            rows.append(f"{s.t_s:.1f},{int(s.sunlight)},{s.truth_soc * 100:.3f},{obs},"
                        f"{s.solar_w:.3f},{s.load_w:.3f},{s.voltage_v:.3f},{s.temp_c:.3f},{s.mode}")
        return "\n".join(rows)


# ---------------------------------------------------------------------------
# 5. Simulation engine
# ---------------------------------------------------------------------------

def _orbit_phase_windows(scenario: Scenario) -> tuple[float, float, float]:
    """CubeTwin's simplified shadow model: the LAST `eclipse_minutes` of each orbit.

    Returns (period_s, eclipse_start_s, eclipse_end_s). No seasonal geometry,
    no attitude dynamics, no perturbations.
    """
    period_s = orbital_period(scenario.altitude_km) * SECONDS_PER_MINUTE
    eclipse_s = min(scenario.eclipse_minutes * SECONDS_PER_MINUTE, period_s)
    return period_s, period_s - eclipse_s, period_s


def simulate(
    scenario: Scenario,
    *,
    soc_bias: float = 0.0,
    telemetry_dropout: tuple[float, float] | None = None,
) -> RunResult:
    """Integrate the mission forward deterministically.

    Controller rules (published):  safe_entry < reserve <= recovery <= max SOC.
      * SOC below `reserve`      -> defer non-critical payload/downlink.
      * SOC below `safe_entry`   -> enter safe mode (essential loads only).
      * Safe mode exits only after SOC holds above `recovery` for the dwell time.
    """
    bat = scenario.battery
    bat.energy_wh = bat.soc0 * bat.capacity_wh
    bat.rejected_wh = bat.loss_wh = bat.removed_wh = 0.0
    bat.temp_c = bat.bus_temp_c
    baseline_r = bat.r_internal_ohm
    baseline_capacity = bat.capacity_wh

    period_s, eclipse_start_s, eclipse_end_s = _orbit_phase_windows(scenario)
    total_s = scenario.duration_h * SECONDS_PER_HOUR
    dt = scenario.dt_s
    steps = int(round(total_s / dt))

    activities = sorted(scenario.activities, key=lambda a: a.start_s)
    served_s = {a.name: 0.0 for a in activities}

    def fault_at(kind: str, t: float) -> Fault | None:
        for f in scenario.faults:
            if f.kind == kind and f.start_s <= t < f.end_s:
                return f
        return None

    samples: list[TelemetrySample] = []
    events: list[tuple[float, str]] = []

    generated_wh = requested_wh = served_wh = unmet_wh_total = 0.0
    charge_stored_wh = discharge_delivered_wh = 0.0
    min_soc, max_soc = 1.0, 0.0
    min_voltage = math.inf
    below_reserve_s = 0.0
    brownout_s = 0.0
    brownout_intervals = 0
    in_brownout = False
    safe_entries = 0
    in_safe = False
    above_recovery_since: float | None = None
    mode = "boot"
    events.append((0.0, "initial -> boot"))

    for i in range(steps):
        t = i * dt
        phase = t % period_s
        sunlight = not (eclipse_start_s <= phase < eclipse_end_s)

        # --- fault windows ---------------------------------------------------
        solar_fault = fault_at("solar_degradation", t)
        load_fault = fault_at("extra_load", t)
        fade_fault = fault_at("capacity_fade", t)
        r_fault = fault_at("resistance_rise", t)
        bat.set_capacity(baseline_capacity * (1.0 - fade_fault.severity) if fade_fault else baseline_capacity)
        bat.set_resistance(r_fault.severity if r_fault else baseline_r)

        # --- generation ------------------------------------------------------
        solar_w = 0.0
        if sunlight:
            cell_w = scenario.peak_solar_w * (1.0 - solar_fault.severity if solar_fault else 1.0)
            solar_w = cell_w * scenario.pmad_efficiency
        generated_step_wh = solar_w * dt / SECONDS_PER_HOUR
        generated_wh += generated_step_wh

        # --- load: base load, one active activity, plus any fault load --------
        base_load_w = scenario.essential_load_w if in_safe else scenario.nominal_load_w
        running = next((a for a in activities if a.start_s <= t < a.end_s), None)
        serving = running is not None and (not in_safe or running.critical)
        load_w = max(base_load_w, running.power_w if serving else 0.0)
        if load_fault is not None:
            load_w += load_fault.severity          # e.g. a stuck-on heater
        load_step_wh = load_w * dt / SECONDS_PER_HOUR
        requested_wh += load_step_wh

        # --- battery integration ---------------------------------------------
        net_w = solar_w - load_w
        energy_before = bat.energy_wh
        delivered_wh, unmet_wh = bat.step(net_w, dt)
        served_step_wh = min(load_step_wh, generated_step_wh + delivered_wh)
        served_wh += served_step_wh
        unmet_wh_total += unmet_wh
        # Energy throughput = energy actually stored + energy actually delivered.
        # (Rejected charge never entered the battery, so it is excluded. This
        # definition reproduces CubeTwin's published 152.64 Wh / 1.908 EFC.)
        if net_w >= 0:
            charge_stored_wh += bat.energy_wh - energy_before
        discharge_delivered_wh += delivered_wh
        throughput_wh = charge_stored_wh + discharge_delivered_wh

        if serving:
            fraction = 1.0 if unmet_wh <= 0 else max(0.0, served_step_wh / load_step_wh)
            served_s[running.name] += dt * fraction

        # --- states and telemetry --------------------------------------------
        soc = bat.soc
        min_soc, max_soc = min(min_soc, soc), max(max_soc, soc)
        discharge_w = max(0.0, load_w - solar_w)
        voltage = bat.terminal_voltage(discharge_w)
        min_voltage = min(min_voltage, voltage)

        # --- mode control -----------------------------------------------------
        if soc < bat.reserve_soc:
            below_reserve_s += dt

        if not in_safe and soc < bat.safe_entry_soc:
            in_safe, safe_entries = True, safe_entries + 1
            above_recovery_since = None
            events.append((t, f"SAFE MODE entry at SOC {soc*100:.2f}% "
                              f"(entry threshold {bat.safe_entry_soc*100:.0f}%)"))
        elif in_safe:
            if soc > bat.recovery_soc:
                if above_recovery_since is None:
                    above_recovery_since = t
                elif t - above_recovery_since >= bat.recovery_dwell_s:
                    in_safe = False
                    events.append((t, f"SAFE MODE exit after holding above "
                                      f"{bat.recovery_soc*100:.0f}% for {bat.recovery_dwell_s/60:.0f} min"))
                    above_recovery_since = None
            else:
                above_recovery_since = None

        new_mode = ("safe" if in_safe
                    else running.mode if serving
                    else "deferred" if (running is not None and soc < bat.reserve_soc)
                    else "nominal")
        if new_mode != mode:
            events.append((t, f"{mode} -> {new_mode}"))
            mode = new_mode

        # --- brownout bookkeeping --------------------------------------------
        undervoltage = voltage < scenario.undervoltage_v or unmet_wh > 0
        if undervoltage:
            brownout_s += dt
            if not in_brownout:
                brownout_intervals += 1
                in_brownout = True
        else:
            in_brownout = False

        observed = float("nan") if (telemetry_dropout and telemetry_dropout[0] <= t < telemetry_dropout[1]) else soc + soc_bias
        samples.append(TelemetrySample(t, sunlight, soc, observed, solar_w, load_w,
                                       voltage, bat.temp_c, mode))

    # --- outcomes and closure --------------------------------------------------
    outcomes: dict[str, dict[str, float | bool]] = {}
    completed = 0
    for a in activities:
        served = min(a.duration_s, served_s[a.name])
        done = served >= a.duration_s - 1e-9
        completed += int(done)
        outcomes[a.name] = {"served_s": served, "requested_s": a.duration_s, "done": done}

    initial_energy = bat.soc0 * baseline_capacity
    residual = (initial_energy + generated_wh - served_wh - bat.rejected_wh
                - bat.loss_wh - bat.removed_wh - bat.energy_wh)

    metrics = {
        "final_soc_pct": bat.soc * 100.0,
        "min_soc_pct": min_soc * 100.0,
        "max_soc_pct": max_soc * 100.0,
        "max_dod_pct": (1.0 - min_soc) * 100.0,
        "generated_wh": generated_wh,
        "requested_wh": requested_wh,
        "served_wh": served_wh,
        "unmet_wh": unmet_wh_total,
        "rejected_wh": bat.rejected_wh,
        "loss_wh": bat.loss_wh,
        "capacity_removed_wh": bat.removed_wh,
        "final_stored_wh": bat.energy_wh,
        "energy_margin_wh": generated_wh - served_wh,
        "energy_balance_residual_wh": residual,
        "time_below_reserve_min": below_reserve_s / SECONDS_PER_MINUTE,
        "brownout_intervals": float(brownout_intervals),
        "brownout_min": brownout_s / SECONDS_PER_MINUTE,
        "min_voltage_v": min_voltage,
        "safe_mode_entries": float(safe_entries),
        "charge_stored_wh": charge_stored_wh,
        "discharge_delivered_wh": discharge_delivered_wh,
        "energy_throughput_wh": throughput_wh,
        "equivalent_full_cycles": throughput_wh / (2.0 * baseline_capacity),
        "completion_fraction": completed / len(activities) if activities else 1.0,
        "mission_complete": float(completed == len(activities) and unmet_wh_total <= 1e-9
                                  and brownout_intervals == 0),
        "temp_min_c": min(s.temp_c for s in samples),
        "temp_max_c": max(s.temp_c for s in samples),
    }
    return RunResult(scenario, samples, events, outcomes, metrics)


# ---------------------------------------------------------------------------
# 6. Monte Carlo uncertainty
# ---------------------------------------------------------------------------

def _wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (better than normal at small n)."""
    if trials == 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def monte_carlo(
    template: Scenario,
    *,
    trials: int = 100,
    uncertainty: float = 0.10,
    seed: int = 42,
    max_trials: int = 1000,
) -> dict[str, float]:
    """Seeded batch runner over uniform +/- `uncertainty` inputs.

    Sampled independently: battery capacity, peak solar output, subsystem loads,
    activity powers and internal resistance. Temperature and faults stay fixed.
    A trial succeeds when every activity completes with no unmet load and no
    undervoltage. With uncertainty = 0 the trials collapse to the deterministic
    result; the same seed always reproduces the same distribution.
    """
    trials = max(1, min(trials, max_trials))
    rng = random.Random(seed)
    successes = 0
    finals: list[float] = []

    for _ in range(trials):
        s = copy.deepcopy(template)
        jitter = lambda: 1.0 + rng.uniform(-uncertainty, uncertainty)  # noqa: E731
        s.peak_solar_w *= jitter()
        s.nominal_load_w *= jitter()
        s.essential_load_w *= jitter()
        for a in s.activities:
            a.power_w *= jitter()
        s.battery.capacity_wh *= jitter()
        s.battery.soc0 = template.battery.soc0      # keep the initial state fixed
        s.battery.r_internal_ohm *= jitter()
        result = simulate(s)
        successes += int(result.metrics["mission_complete"] == 1.0)
        finals.append(result.metrics["final_soc_pct"])

    lo, hi = _wilson_interval(successes, trials)
    return {
        "trials": float(trials),
        "successes": float(successes),
        "success_fraction": successes / trials,
        "ci95_low": lo,
        "ci95_high": hi,
        "final_soc_mean_pct": statistics.fmean(finals),
        "final_soc_stdev_pct": statistics.pstdev(finals),
    }


# ---------------------------------------------------------------------------
# 7. CLI: reference run plus the eight published workbook experiments
# ---------------------------------------------------------------------------

def _print_metrics(title: str, metrics: dict[str, float]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key in ("final_soc_pct", "min_soc_pct", "max_dod_pct", "generated_wh",
                "requested_wh", "served_wh", "unmet_wh", "rejected_wh", "loss_wh",
                "energy_margin_wh", "energy_balance_residual_wh", "min_voltage_v",
                "safe_mode_entries", "time_below_reserve_min", "brownout_intervals",
                "energy_throughput_wh", "equivalent_full_cycles",
                "completion_fraction", "temp_max_c"):
        print(f"  {key:<28} {metrics[key]:>12.4f}")


def main() -> None:
    print("CubeTwin reference model -- stdlib-only reimplementation")
    print("=" * 62)

    print("\nHand-checked analytical values")
    print(f"  T(500 km)                  = {orbital_period(500.0):.2f} min  (expect ~94.5)")
    print(f"  T(600 km)                  = {orbital_period(600.0):.2f} min  (expect ~96.5)")
    ef = eclipse_fraction(0.0, 500.0)
    print(f"  eclipse @ beta=0, 500 km   = {ef*100:.2f} % of orbit "
          f"= {ef*orbital_period(500.0):.2f} min")
    peak, delivered = solar_power_w()
    print(f"  array peak / delivered     = {peak:.1f} W / {delivered:.1f} W  (expect 20 / 18)")
    print(f"  8 W for 35 min             = {8*35/60:.3f} Wh "
          f"({8*35/60/0.95:.3f} Wh drawn at 95% discharge efficiency)")
    demo = Battery(capacity_wh=40.0, soc0=0.80)
    demo.step(-8.0, 3600.0)
    print(f"  40 Wh at 80% - 8 W x 1 h   = {demo.energy_wh:.3f} Wh  (SOC {demo.soc*100:.2f} %)")
    print(f"  1 A through 0.12 ohm       = 0.12 V sag")

    base = simulate(Scenario.reference())
    _print_metrics("Baseline reference mission (24 h, 10 s step)", base.metrics)
    print("  event log:")
    for t, msg in base.events:
        print(f"    {t/3600:6.3f} h  {msg}")

    print("\nExperiment 3: 35% solar degradation, hours 2-8")
    s = Scenario.reference()
    s.faults = [Fault("solar_degradation", 2 * 3600.0, 6 * 3600.0, 0.35)]
    degraded = simulate(s)
    print(f"  min SOC    : {degraded.metrics['min_soc_pct']:.2f} % "
          f"({degraded.metrics['min_soc_pct'] - base.metrics['min_soc_pct']:+.2f} pp vs baseline)")
    print(f"  margin     : {degraded.metrics['energy_margin_wh']:.2f} Wh "
          f"({degraded.metrics['energy_margin_wh'] - base.metrics['energy_margin_wh']:+.2f} Wh)")
    print(f"  completion : {degraded.metrics['completion_fraction']*100:.0f} %")

    print("\nStress case: 75% degradation all mission, starting from 50% SOC")
    s = Scenario.reference()
    s.battery.soc0 = 0.50
    s.faults = [Fault("solar_degradation", 0.0, 24 * 3600.0, 0.75)]
    stressed = simulate(s)
    _print_metrics("With 75% solar degradation from 50% SOC", stressed.metrics)
    for t, msg in stressed.events[:8]:
        print(f"    {t/3600:6.3f} h  {msg}")

    print("\nExperiment 4: move the downlink into a sunlight interval")
    s = Scenario.reference()
    s.activities[3].start_s = 2 * 3600.0        # inside sunlight, per orbit phase
    moved = simulate(s)
    print(f"  downlink outcome: {moved.outcomes['downlink-1']}")
    print(f"  min SOC {moved.metrics['min_soc_pct']:.2f} %  "
          f"final SOC {moved.metrics['final_soc_pct']:.2f} %")

    print("\nExperiment 6: +15 pp SOC sensor bias (affects decisions, not truth)")
    biased = simulate(Scenario.reference(), soc_bias=0.15)
    print(f"  truth min SOC    {biased.metrics['min_soc_pct']:.2f} %")
    print(f"  observed min SOC {min(x.observed_soc for x in biased.samples)*100:.2f} %")
    print("  -> a biased sensor can hide a reserve violation; real detection needs")
    print("     independent measurements, which is why the truth oracle is teaching-only.")

    print("\nExperiment 7: 100 Monte Carlo trials, +/-10% uncertainty, seed 42, run twice")
    for run in (1, 2):
        mc = monte_carlo(Scenario.reference(), trials=100, uncertainty=0.10, seed=42)
        print(f"  run {run}: success {mc['success_fraction']*100:5.1f} % "
              f"(95% Wilson CI {mc['ci95_low']*100:.1f}-{mc['ci95_high']*100:.1f} %), "
              f"final SOC {mc['final_soc_mean_pct']:.2f} +/- {mc['final_soc_stdev_pct']:.2f} %")
    deterministic = monte_carlo(Scenario.reference(), trials=10, uncertainty=0.0, seed=1)
    print(f"  uncertainty = 0 collapses to deterministic: "
          f"success {deterministic['success_fraction']*100:.0f} %, spread "
          f"{deterministic['final_soc_stdev_pct']:.3f} pp")

    print("\nExperiment 10: energy accounting closure")
    print(f"  residual = {base.metrics['energy_balance_residual_wh']:.3e} Wh")
    print(f"  telemetry samples exported: {len(base.samples)}")
    print("\nSimulation results are not flight evidence.")


if __name__ == "__main__":
    main()
