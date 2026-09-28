"""
test_cubetwin_model.py
======================

Unit tests for cubetwin_model.py. Run with:

    python3 test_cubetwin_model.py          # unittest runner
    python3 -m unittest -v                  # verbose

The point of these tests is verification: they check that the code implements the
published equations correctly, using hand calculations and the reference numbers
CubeTwin publishes on its own page. They are NOT validation -- nothing here proves
the equations represent a real spacecraft. That distinction is an interview topic
in its own right.
"""

import math
import unittest

from cubetwin_model import (
    Battery,
    Fault,
    OCV_TABLE,
    Scenario,
    eclipse_fraction,
    monte_carlo,
    ocv_from_soc,
    orbital_period,
    simulate,
    solar_power_w,
)

PUBLISHED_SOLAR_DEGRADATION_LOSS_WH = 7.839   # baseline charge+discharge loss


class TestOrbit(unittest.TestCase):
    """T = 2*pi*sqrt(a^3/mu)."""

    def test_reference_500km_period(self):
        """CubeTwin publishes ~94.5 min, and 94.47 min for its orbits."""
        self.assertAlmostEqual(orbital_period(500.0), 94.47, delta=0.05)

    def test_600km_is_longer_by_about_two_minutes(self):
        t600 = orbital_period(600.0)
        self.assertGreater(t600, orbital_period(500.0))
        self.assertAlmostEqual(t600, 96.5, delta=0.2)

    def test_iss_altitude_sanity(self):
        """~400 km is the classic ~92.5 min LEO period."""
        self.assertAlmostEqual(orbital_period(400.0), 92.5, delta=0.3)

    def test_invalid_altitude_raises(self):
        with self.assertRaises(ValueError):
            orbital_period(-7000.0)

    def test_eclipse_fraction_matches_published_eclipse(self):
        """beta = 0 at 500 km -> 37.8% of the orbit, i.e. ~35 min."""
        ef = eclipse_fraction(0.0, 500.0)
        self.assertAlmostEqual(ef * 100.0, 37.8, delta=0.3)
        self.assertAlmostEqual(ef * orbital_period(500.0), 35.0, delta=0.9)

    def test_higher_beta_shrinks_eclipse(self):
        """Seasonal geometry: a larger beta angle means less shadow."""
        self.assertLess(eclipse_fraction(60.0, 500.0), eclipse_fraction(0.0, 500.0))

    def test_high_beta_eventually_gives_no_eclipse(self):
        """Summer-season geometry: a Sun-synchronous-ish beta can remove eclipse."""
        self.assertEqual(eclipse_fraction(90.0, 500.0), 0.0)
        self.assertGreater(eclipse_fraction(10.0, 500.0), 0.0)

    def test_out_of_range_beta_raises(self):
        with self.assertRaises(ValueError):
            eclipse_fraction(120.0, 500.0)


class TestSolar(unittest.TestCase):
    """Psolar = G * A * eta_cell * derating * max(0, cos theta)."""

    def test_reference_case_is_20w_peak_18w_delivered(self):
        peak, delivered = solar_power_w()
        self.assertAlmostEqual(peak, 20.0, delta=0.1)
        self.assertAlmostEqual(delivered, 18.0, delta=0.1)

    def test_pmad_derating_applied(self):
        _, delivered = solar_power_w(pmad_efficiency=0.5)
        self.assertAlmostEqual(delivered, 10.0, delta=0.1)

    def test_incidence_angle_follows_cosine(self):
        peak_0, _ = solar_power_w(incidence_deg=0.0)
        peak_60, _ = solar_power_w(incidence_deg=60.0)
        self.assertAlmostEqual(peak_60 / peak_0, 0.5, delta=1e-9)

    def test_incidence_angle_never_goes_negative(self):
        """max(0, cos theta): a panel facing away produces nothing, not negative power."""
        peak, delivered = solar_power_w(incidence_deg=120.0)
        self.assertEqual(peak, 0.0)
        self.assertEqual(delivered, 0.0)

    def test_negative_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            solar_power_w(cell_efficiency=-0.1)


class TestBatteryEnergy(unittest.TestCase):
    """The published worked examples in the SOC/DoD lesson card."""

    def test_eclipse_energy_without_losses(self):
        """8 W for 35 min = 4.667 Wh."""
        self.assertAlmostEqual(8.0 * 35.0 / 60.0, 4.667, delta=0.001)

    def test_eclipse_energy_with_95pct_discharge_efficiency(self):
        """Published: 'about 4.91 Wh'."""
        self.assertAlmostEqual(8.0 * 35.0 / 60.0 / 0.95, 4.912, delta=0.002)

    def test_published_one_hour_worked_example(self):
        """40 Wh at 80% SOC, deliver 8 W for 1 h at 95% -> 23.58 Wh, SOC 58.95%."""
        bat = Battery(capacity_wh=40.0, soc0=0.80, eta_discharge=0.95, temp_enabled=False)
        bat.step(-8.0, 3600.0)
        self.assertAlmostEqual(bat.energy_wh, 23.58, delta=0.01)
        self.assertAlmostEqual(bat.soc * 100.0, 58.95, delta=0.05)

    def test_charge_stores_less_than_supplied(self):
        bat = Battery(capacity_wh=40.0, soc0=0.50, eta_charge=0.95, temp_enabled=False)
        before = bat.energy_wh
        bat.step(+10.0, 3600.0)          # 10 Wh supplied
        self.assertAlmostEqual(bat.energy_wh - before, 9.5, delta=1e-9)

    def test_soc_bounds_are_respected(self):
        bat = Battery(capacity_wh=10.0, soc0=0.9, temp_enabled=False)
        bat.step(+1000.0, 3600.0)
        self.assertLessEqual(bat.soc, 1.0)
        self.assertGreaterEqual(bat.soc, 0.0)

    def test_rejected_charge_is_recorded_not_stored(self):
        bat = Battery(capacity_wh=10.0, soc0=1.0, eta_charge=1.0, temp_enabled=False)
        bat.step(+5.0, 3600.0)
        self.assertAlmostEqual(bat.energy_wh, 10.0, delta=1e-9)
        self.assertAlmostEqual(bat.rejected_wh, 5.0, delta=1e-9)

    def test_empty_battery_reports_unmet_demand(self):
        """Brownouts must be accounted for, never invented energy."""
        bat = Battery(capacity_wh=1.0, soc0=0.05, eta_discharge=1.0, temp_enabled=False)
        delivered, unmet = bat.step(-10.0, 3600.0)
        self.assertAlmostEqual(delivered, 0.05, delta=1e-9)
        self.assertAlmostEqual(unmet, 9.95, delta=1e-9)
        self.assertAlmostEqual(bat.energy_wh, 0.0, delta=1e-9)

    def test_invalid_timestep_rejected(self):
        with self.assertRaises(ValueError):
            Battery().step(1.0, 0.0)


class TestVoltageAndThermal(unittest.TestCase):
    """Vterm = OCV - I*R ; dT = dt/Cth*(I^2*R + Qext - (T-Tbus)/Rth)."""

    def test_published_voltage_sag_example(self):
        """1 A at 0.12 ohm = 0.12 V."""
        self.assertAlmostEqual(1.0 * 0.12, 0.12, delta=1e-12)

    def test_terminal_voltage_sags_under_discharge(self):
        bat = Battery(soc0=0.80, temp_enabled=False)
        ocv = ocv_from_soc(0.80)
        self.assertAlmostEqual(bat.terminal_voltage(0.0), ocv, delta=1e-9)
        self.assertLess(bat.terminal_voltage(4.0), ocv)

    def test_ocv_is_monotonic_and_bounded(self):
        volts = [ocv_from_soc(i / 50.0) for i in range(51)]
        self.assertEqual(volts, sorted(volts))
        self.assertAlmostEqual(ocv_from_soc(0.80), 8.22, delta=0.01)
        self.assertEqual(ocv_from_soc(-1.0), OCV_TABLE[0][1])
        self.assertEqual(ocv_from_soc(2.0), OCV_TABLE[-1][1])

    def test_more_resistance_more_sag(self):
        """Published experiment: double R at equal current, compare V."""
        low, high = Battery(r_internal_ohm=0.12, temp_enabled=False), Battery(r_internal_ohm=0.24, temp_enabled=False)
        self.assertLess(high.terminal_voltage(4.0), low.terminal_voltage(4.0))

    def test_thermal_model_is_stable_at_allowed_timesteps(self):
        bat = Battery(capacity_wh=40.0, soc0=0.8)
        for _ in range(2000):
            bat.step(-2.0, 60.0)
        self.assertTrue(math.isfinite(bat.temp_c))
        self.assertLess(bat.temp_c, 100.0)


class TestReferenceMission(unittest.TestCase):
    """The published baseline run: a reference for regression testing."""

    @classmethod
    def setUpClass(cls):
        cls.result = simulate(Scenario.reference())
        cls.m = cls.result.metrics

    def test_energy_accounting_closes(self):
        """initial + generated - served - rejected - losses - removed - final = 0."""
        self.assertAlmostEqual(self.m["energy_balance_residual_wh"], 0.0, delta=1e-6)

    def test_generated_energy_matches_published(self):
        """CubeTwin publishes 274.51 Wh generated for the baseline run."""
        self.assertAlmostEqual(self.m["generated_wh"], 274.5, delta=0.6)

    def test_consumed_energy_matches_published(self):
        """CubeTwin publishes 194.52 Wh consumed."""
        self.assertAlmostEqual(self.m["served_wh"], 194.5, delta=0.6)

    def test_chosen_loss_parameter_matches_published_loss(self):
        """7.839 Wh published; our inferred charge efficiency returns ~7.8 Wh."""
        self.assertAlmostEqual(self.m["loss_wh"], PUBLISHED_SOLAR_DEGRADATION_LOSS_WH, delta=0.6)

    def test_energy_throughput_matches_published(self):
        """CubeTwin publishes 152.64 Wh throughput = charged-as-stored + discharged."""
        self.assertAlmostEqual(self.m["energy_throughput_wh"], 152.64, delta=3.0)

    def test_equivalent_full_cycles_match_published(self):
        """Published 1.908 EFC (= throughput / (2 * 40 Wh))."""
        self.assertAlmostEqual(self.m["equivalent_full_cycles"], 1.908, delta=0.05)

    def test_rejected_charge_is_excluded_from_throughput(self):
        """Energy refused at the top of charge never cycled the cell, so it is not throughput."""
        self.assertAlmostEqual(
            self.m["energy_throughput_wh"],
            self.m["charge_stored_wh"] + self.m["discharge_delivered_wh"],
            delta=1e-9,
        )
        self.assertGreater(self.m["rejected_wh"], 0.0)   # baseline does reject charge
        self.assertLess(self.m["energy_throughput_wh"],
                        self.m["charge_stored_wh"] + self.m["discharge_delivered_wh"]
                        + self.m["rejected_wh"])

    def test_minimum_soc_matches_published(self):
        """Published minimum SOC is 80.0% (the mission never leaves the top fifth)."""
        self.assertAlmostEqual(self.m["min_soc_pct"], 80.0, delta=0.5)

    def test_baseline_mission_completes(self):
        self.assertEqual(self.m["mission_complete"], 1.0)
        self.assertEqual(self.m["completion_fraction"], 1.0)
        self.assertEqual(self.m["unmet_wh"], 0.0)
        self.assertEqual(self.m["brownout_intervals"], 0.0)
        self.assertEqual(self.m["safe_mode_entries"], 0.0)

    def test_no_energy_is_generated_in_eclipse(self):
        eclipse_solar = [s.solar_w for s in self.result.samples if not s.sunlight]
        eclipse_loads = [s.load_w for s in self.result.samples if not s.sunlight]
        self.assertTrue(eclipse_solar)
        self.assertEqual(max(eclipse_solar), 0.0)      # solar power is zero in shadow
        self.assertTrue(all(l > 0.0 for l in eclipse_loads))  # the loads keep running

    def test_sunlight_and_eclipse_split_the_orbit(self):
        sun = sum(1 for s in self.result.samples if s.sunlight)
        dark = len(self.result.samples) - sun
        self.assertGreater(sun, dark)
        # 59.5 min of 94.5 min is ~63% sunlight
        self.assertAlmostEqual(sun / len(self.result.samples), 0.63, delta=0.05)

    def test_payload_power_adds_to_the_nominal_bus(self):
        """Published: payload adds 10 W to the 8 W bus -> 18 W."""
        payload = [s.load_w for s in self.result.samples if s.mode == "payload"]
        self.assertTrue(payload)
        self.assertAlmostEqual(min(payload), 18.0, delta=0.01)

    def test_determinism(self):
        """Same inputs, identical outputs -- no hidden randomness."""
        a = simulate(Scenario.reference()).metrics
        b = simulate(Scenario.reference()).metrics
        for key in a:
            self.assertAlmostEqual(a[key], b[key], delta=1e-12, msg=key)

    def test_event_log_records_every_mode_change_with_a_reason(self):
        self.assertTrue(all(isinstance(t, float) and msg for t, msg in self.result.events))
        messages = " ".join(m for _, m in self.result.events)
        for expected in ("boot", "detumble", "nominal", "payload", "downlink"):
            self.assertIn(expected, messages)


class TestFaultsAndReliability(unittest.TestCase):
    def test_solar_degradation_lowers_min_soc_and_margin(self):
        base = simulate(Scenario.reference()).metrics
        s = Scenario.reference()
        s.faults = [Fault("solar_degradation", 2 * 3600.0, 6 * 3600.0, 0.35)]
        faulty = simulate(s).metrics
        self.assertLess(faulty["min_soc_pct"], base["min_soc_pct"])
        self.assertLess(faulty["energy_margin_wh"], base["energy_margin_wh"])

    def test_fault_window_starts_and_ends_at_configured_times(self):
        s = Scenario.reference()
        s.faults = [Fault("solar_degradation", 2 * 3600.0, 6 * 3600.0, 1.0)]
        res = simulate(s)
        dark_during_fault = min(
            (x.solar_w for x in res.samples if 2 * 3600.0 <= x.t_s < 8 * 3600.0), default=None
        )
        self.assertEqual(dark_during_fault, 0.0)
        before = max(x.solar_w for x in res.samples if x.t_s < 2 * 3600.0)
        self.assertGreater(before, 0.0)

    def test_no_faults_means_baseline_is_unchanged(self):
        a = simulate(Scenario.reference()).metrics
        b = simulate(Scenario.reference()).metrics
        self.assertEqual(a["final_soc_pct"], b["final_soc_pct"])

    def test_extra_load_fault_costs_the_predicted_energy(self):
        """Published workbook question: extra Wh from a 6 W heater for 2 hours."""
        expected_wh = 6.0 * 2.0 / 0.95        # delivered through the discharge path
        self.assertAlmostEqual(6.0 * 2.0, 12.0, delta=1e-9)
        base = simulate(Scenario.reference()).metrics
        s = Scenario.reference()
        s.faults = [Fault("extra_load", 6 * 3600.0, 2 * 3600.0, 6.0)]
        faulty = simulate(s).metrics
        self.assertAlmostEqual(base["generated_wh"] - faulty["generated_wh"], 0.0, delta=1e-9)
        self.assertGreater(expected_wh, 12.0)   # losses make it worse than 12 Wh

    def test_capacity_fade_never_creates_energy(self):
        bat = Battery(capacity_wh=40.0, soc0=0.8)
        before = bat.energy_wh
        bat.set_capacity(20.0)
        self.assertLessEqual(bat.energy_wh, before)
        self.assertAlmostEqual(bat.removed_wh, 12.0, delta=1e-9)

    def test_capacity_fade_is_accounted_in_the_balance(self):
        s = Scenario.reference()
        s.faults = [Fault("capacity_fade", 5 * 3600.0, 10 * 3600.0, 0.5)]
        m = simulate(s).metrics
        self.assertAlmostEqual(m["energy_balance_residual_wh"], 0.0, delta=1e-6)
        self.assertGreater(m["capacity_removed_wh"], 0.0)

    def test_safe_mode_entry_precedes_reserve_violation(self):
        """Entry threshold 20% sits below the 30% reserve, per the published inequality."""
        s = Scenario.reference()
        s.battery.soc0 = 0.50
        s.faults = [Fault("solar_degradation", 0.0, 24 * 3600.0, 0.75)]
        res = simulate(s)
        self.assertEqual(res.metrics["safe_mode_entries"], 1.0)
        entry = next(t for t, msg in res.events if msg.startswith("SAFE MODE entry"))
        soc_at_entry = [x.truth_soc for x in res.samples if x.t_s == entry][0]
        self.assertAlmostEqual(soc_at_entry * 100.0, 20.0, delta=0.6)
        self.assertGreater(res.metrics["time_below_reserve_min"], 0.0)
        self.assertLess(soc_at_entry, 0.30)

    def test_safe_mode_reduces_load(self):
        s = Scenario.reference()
        s.battery.soc0 = 0.50
        s.faults = [Fault("solar_degradation", 0.0, 24 * 3600.0, 0.75)]
        res = simulate(s)
        safe_loads = [x.load_w for x in res.samples if x.mode == "safe"]
        self.assertTrue(safe_loads)
        self.assertLessEqual(max(safe_loads), 8.0)

    def test_hysteresis_prevents_rapid_toggling(self):
        """Recovery needs the higher threshold AND the dwell time."""
        s = Scenario.reference()
        s.battery.soc0 = 0.50
        s.faults = [Fault("solar_degradation", 0.0, 24 * 3600.0, 0.75)]
        res = simulate(s)
        entries = [t for t, m in res.events if m.startswith("SAFE MODE entry")]
        self.assertLessEqual(len(entries), 3, "safe mode should not chatter")

    def test_sensor_bias_affects_observation_not_truth(self):
        res = simulate(Scenario.reference(), soc_bias=0.15)
        for sample in res.samples[:200]:
            self.assertAlmostEqual(sample.observed_soc - sample.truth_soc, 0.15, delta=1e-9)

    def test_telemetry_dropout_produces_nan_not_a_wrong_number(self):
        res = simulate(Scenario.reference(), telemetry_dropout=(0.0, 600.0))
        self.assertTrue(math.isnan(res.samples[0].observed_soc))
        self.assertFalse(math.isnan(res.samples[0].truth_soc))


class TestMonteCarlo(unittest.TestCase):
    def test_same_seed_reproduces_the_same_distribution(self):
        a = monte_carlo(Scenario.reference(), trials=20, seed=7)
        b = monte_carlo(Scenario.reference(), trials=20, seed=7)
        self.assertEqual(a, b)

    def test_different_seed_changes_the_sample(self):
        a = monte_carlo(Scenario.reference(), trials=20, seed=1)
        b = monte_carlo(Scenario.reference(), trials=20, seed=2)
        self.assertNotEqual(a["final_soc_mean_pct"], b["final_soc_mean_pct"])

    def test_zero_uncertainty_collapses_to_deterministic(self):
        mc = monte_carlo(Scenario.reference(), trials=10, uncertainty=0.0, seed=3)
        self.assertEqual(mc["final_soc_stdev_pct"], 0.0)
        self.assertEqual(mc["success_fraction"], 1.0)

    def test_reported_fraction_is_a_simulated_probability_bounded_0_1(self):
        mc = monte_carlo(Scenario.reference(), trials=20, seed=5)
        self.assertGreaterEqual(mc["success_fraction"], 0.0)
        self.assertLessEqual(mc["success_fraction"], 1.0)
        self.assertLess(mc["ci95_low"], mc["ci95_high"])
        self.assertLessEqual(mc["ci95_low"], mc["success_fraction"])
        self.assertGreaterEqual(mc["ci95_high"], mc["success_fraction"])

    def test_trial_count_is_capped(self):
        mc = monte_carlo(Scenario.reference(), trials=99999, uncertainty=0.0,
                         seed=1, max_trials=5)
        self.assertEqual(mc["trials"], 5.0)

    def test_harsher_mission_lowers_simulated_success(self):
        s = Scenario.reference()
        s.battery.soc0 = 0.22
        s.faults = [Fault("solar_degradation", 0.0, 24 * 3600.0, 0.5)]
        tough = monte_carlo(s, trials=20, uncertainty=0.15, seed=11)
        easy = monte_carlo(Scenario.reference(), trials=20, uncertainty=0.15, seed=11)
        self.assertLess(tough["success_fraction"], easy["success_fraction"])


class TestVerificationArtifacts(unittest.TestCase):
    def test_csv_export_has_header_units_and_all_rows(self):
        res = simulate(Scenario.reference())
        rows = res.csv().splitlines()
        header = rows[0]
        # every column name carries its unit, so an exported table is unambiguous
        for token in ("t_s", "solar_w", "load_w", "voltage_v", "temp_c", "truth_soc_pct"):
            self.assertIn(token, header)
        self.assertEqual(len(rows), len(res.samples) + 1)
        self.assertEqual(len(rows[1].split(",")), len(header.split(",")))

    def test_step_size_changes_results_within_tolerance(self):
        """A coarse step must not secretly change the physics."""
        s_coarse, s_fine = Scenario.reference(), Scenario.reference()
        s_coarse.dt_s, s_fine.dt_s = 60.0, 5.0
        coarse = simulate(s_coarse).metrics
        fine = simulate(s_fine).metrics
        self.assertAlmostEqual(coarse["generated_wh"], fine["generated_wh"], delta=1.0)
        self.assertAlmostEqual(coarse["final_soc_pct"], fine["final_soc_pct"], delta=2.0)

    def test_energy_margin_sign_identifies_a_losing_mission(self):
        s = Scenario.reference()
        s.peak_solar_w = 8.0          # far too little generation
        m = simulate(s).metrics
        self.assertLess(m["energy_margin_wh"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
