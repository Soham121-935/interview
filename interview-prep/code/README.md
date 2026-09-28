# CubeTwin reference model (interview evidence / take-home insurance)

A **stdlib-only Python reimplementation of CubeTwin's published equations**, written because the interview can include *"a short conversation or a take-home task"*. Nothing here is copied from their codebase — every equation comes from the public lesson cards on [aerospace.ishavasyam.org/space/cubesat](https://aerospace.ishavasyam.org/space/cubesat), and every headline number is verified against the metrics they publish for their own baseline run.

## Run it

```bash
python3 cubetwin_model.py                     # reference mission + the workbook experiments
python3 -m unittest test_cubetwin_model.py    # 60 tests, no dependencies
```

Requires Python 3.8+ and nothing else — no NumPy, no installation.

## Verification results (this is the part worth quoting)

| Check | CubeTwin publishes | This model | Note |
|---|---|---|---|
| Orbital period at 500 km | 94.5 min (94.47 shown) | **94.47 min** | exact |
| Orbital period at 600 km | — | **96.54 min** | +2.07 min |
| Eclipse at β = 0, 500 km | ~35 min | **37.78% = 35.69 min** | geometry-consistent |
| Peak / delivered solar | 20 W / 18 W | **20.0 W / 18.0 W** | exact |
| Energy generated, 24 h baseline | 274.51 Wh | **274.50 Wh** | 0.004% |
| Energy consumed, baseline | 194.52 Wh | **194.47 Wh** | 0.03% |
| Minimum SOC | 80.0% | **80.07%** | 0.07 pp |
| Battery capacities for the worked examples | 4.91 Wh, 58.95% SOC, 0.12 V sag | **exact** | hand-checked |
| Energy-accounting residual | 4.82e-11 Wh | **5e-11 Wh** | closes numerically |
| Energy throughput | 152.64 Wh | **150.98 Wh** | 1.1% — same definition (stored + discharged) |
| Equivalent full cycles | 1.908 | **1.887** | 1.1% |
| Charge + discharge loss | 7.839 Wh | **8.21 Wh** | after inferring 0.97 charge efficiency |
| **Final SOC (baseline)** | **91.81%** | **96.95%** | ⚠️ **does not match — see below** |
| Monte Carlo, ±10%, seed 42, 100 trials | (repeatable) | **100% success, 95% Wilson CI 96.3–100%** | seed-reproducible |
| Determinism, same seed, twice | required | **identical** | verified |

### ⚠️ The honest discrepancy — say this before they find it
My final SOC is **96.95%** against their published **91.81%**, a difference of about 2 Wh out of ~275 Wh generated (≈0.7%). The cause: their **charge-efficiency default and rejected-charge accounting are not published**. I inferred 0.97 for charge efficiency because it reproduces their published 7.839 Wh loss figure, but the split between stored, rejected and lost energy still differs slightly. The right statement in the interview:

> "Generated and consumed match your published run almost exactly, the residual closes, and my minimum SOC matches. My final SOC doesn't, because I had to infer your charge-efficiency default from your loss figure. I'd rather flag the inference than hide it behind a number that looks like it agrees."

## What's implemented

- `orbital_period()` — `T = 2π√((Re+h)³/μ)`; 500 km → 94.47 min, with controlled errors on invalid altitude
- `eclipse_fraction()` — `(1/π)·arccos(√(h²+2Reh)/((Re+h)cos β))`; β = 0 gives the ~35 min worst case, high β returns no eclipse
- `solar_power_w()` — `G·A·η·derating·max(0, cos θ)`, then PMAD efficiency → 20 W / 18 W
- `Battery` — energy-integration state machine: SOC/DoD bounds, charge and discharge efficiency, rejected charge at 100%, unmet demand when empty (never invents energy), capacity fade with explicit energy-removal accounting, OCV(SOC) lookup, `Vterm = OCV − I·R`, I²R lumped thermal model
- `simulate()` — orbit phase, per-step load with one active activity, mode controller with hysteresis (`safe entry < reserve ≤ recovery ≤ max SOC` plus recovery dwell), safe mode, deferred activities, event log with reasons, brownout intervals, telemetry samples (truth / observed / NaN on dropout)
- `monte_carlo()` — seeded uniform uncertainty on capacity, solar, loads and resistance; success fraction with a Wilson score interval; zero uncertainty collapses to the deterministic result
- `RunResult.csv()` — telemetry export with units in every column name

## Design notes worth defending out loud

1. **Energy is the state variable, power is the input.** SOC is derived, never integrated separately.
2. **The residual is asserted, not assumed.** `initial + generated − served − rejected − losses − removed − final ≈ 0` (∥residual∥ < 1e-6 Wh) is a test, because silently creating or destroying energy is the classic failure mode of this kind of model.
3. **Every column name carries a unit** (`voltage_v`, `temp_c`, `truth_soc_pct`) — dimensional ambiguity is where simulation bugs hide.
4. **Fault windows are bounded in time and reversible**, and a capacity fade can only remove energy, never restore it.
5. **Determinism is a feature**: same scenario + same seed → identical output, so a result can be reproduced by someone else.
6. **Monte Carlo probabilities are labelled as simulated**, never as mission reliability.
7. **Verification only.** Nothing here is validated against a test article, and no result is flight evidence.

## If they set a take-home task

Reuse this, but write your own tests first and state your tolerance before you run anything. Their roadmap's verification style is: hand calculation → code → compare within a defined tolerance → record the result. If you present this file, you must be able to explain every line, so read it before you send it.
