# Skills Reframing — making your real experience line up with their keyword list

**Goal:** present your existing skills so that a reader scanning for *Satellite Engineering, CubeSat, Digital Twin, Energy, Battery, Solar Energy* immediately finds evidence — **without inventing a single thing you can't defend in an interview.**

**The rule:** every claim below is either (a) something you have already built, or (b) something you are learning right now and will label as learning. Items marked `[confirm]` are things `me` didn't state — fill in or delete them yourself.

---

## 1. Their keyword list vs what you actually have

| Their skill | Do you have it? | Your real evidence (use this, don't fake it) |
|---|---|---|
| **Satellite Engineering** | Foundational, learning | You know the 3U reference mission, LEO geometry and the EPS end-to-end from first principles: orbital period, eclipse fraction, solar generation through PMAD, load scheduling, battery state, safe modes. Say: *"No flight experience — I've built the fundamentals and can do the calculations by hand."* |
| **CubeSat** | Foundational, learning | 1U/3U form factors, ~1.33 kg per U and ~4 kg for 3U per the Cal Poly CDS, subsystem naming (EPS, OBC, C&DH, ADCS, TT&C), dispenser/deliverable interfaces, LEO constraints. |
| **Rocketry** | ❌ No | **Do not claim it.** Bridge honestly: *"My interest is the spacecraft side, not the launch vehicle — the rocket's job ends at deployment, and then power, energy and reliability decide whether the mission works."* |
| **Rocket Science** | ❌ No | Same bridge. Do not bluff propulsion or launch-window talk. |
| **Space Station** | Contextual | You read the ISHAVASYAM.ORG six research frontiers. Two map onto you directly: **Power & Energy** (PV sizing, energy storage through eclipse, PMAD, load scheduling and shedding, thermal, energy balance across orbit and beta angle) and **Autonomous Systems & Station Health** (telemetry health monitoring, anomaly detection, fault isolation). Say that — it shows you read the initiative, not just the listing. |
| **Space Systems Engineering** | ✅ Yes, genuinely | **SV-16 is systems engineering.** You defined an architecture against requirements, defined interfaces (memory bus, register file, status system), ran trade-offs (reliability over compactness, buildability over optimisation, no BGA, obtainable components), and drive it through a full V: architecture → RTL → simulation → synthesis → bitstream → PCB → assembly → test → documentation. Plus budget engineering: cost, availability, removing non-essential components. |
| **Digital Twin** | ✅ Yes — and you sharpened it today | (1) You built a Simulink model of the SV-16 datapath/register bank — a model of a physical system you intend to build. (2) You implemented CubeTwin's own published equations as a working, unit-tested model and verified it against their published metrics (`code/`). (3) You can state the distinction correctly: a simulation becomes a *twin* only when connected to traceable data from a specific physical system — which is why CubeTwin calls itself an educational prototype until calibrated. |
| **Energy** | ✅ Yes, hands-on | INA219 current/voltage/power monitoring in two projects; load-cell sensing; local display + remote dashboards (Blynk, Telegram) — i.e. generation/consumption sensing and telemetry. You now also do the maths: W vs Wh, per-orbit energy margins, accounting closure, losses and rejected charge. |
| **Battery** | ✅ Yes, hands-on + theory | Rechargeable battery pack powering an MSP430 + ESP8266 + INA219 + OLED + motor node. Theory and implementation you can now defend: capacity, energy capacity, SOC, DoD, OCV lookup, internal resistance, voltage sag, I²R heating, charge/discharge efficiency, C-rate, throughput, equivalent full cycles, capacity fade. **And this is the parent company's commercial speciality** — capacity fade, internal-resistance rise, SOH/RUL, thermal runaway. Say that link out loud. |
| **Solar Energy** | ✅ Adjacent + theory | Solar cell I–V behaviour, cell efficiency, incidence angle (cos θ), derating, BOL/EOL degradation, array sizing and PMAD losses from your analog-electronics base; you implemented `Psolar = G·A·η·derating·max(0, cos θ)` and verified 20 W peak → 18 W delivered. |

**Desired attributes**, evidence you already own:

| Attribute | Your evidence |
|---|---|
| Communication (verbal & written) | Workshop organising, event hosting, documentation of SV-16, GATE-level subject explanations |
| Presentation | Technovation head, college presentations, project demos |
| Management / Time management | Technovation 2K25 Head of Event; SY Class Representative; club + publicity team; running SV-16 to a milestone date |
| Team work | SV-16 with a second member owning the PCB; event teams; workshop teams |
| Learning ability | Diploma → direct second-year entry at 92.47%; self-taught FPGA/RTL, Simulink, React/Vite/Tailwind/Firebase, Git |
| Research oriented | SV-16 architecture study; surveying components for cost/availability/import duty; reading the CubeTwin model assumptions and references (NASA CubeSat 101, Cal Poly CDS, ECSS Li-ion handbook, GMAT, Orekit) |
| Hands-on experience | PCB fabrication, soldering, hardware debugging, Aptron Technologies internship (PCB, Arduino, hardware implementation) |
| Startup experience | You've worked with/around early-stage ventures and evaluated internship offers critically — frame as *practical exposure*, keep it light |
| Out-of-box thinking | An original processor architecture rather than copying an existing CPU; a ₹1,350 redesign of a ₹1,700 medical-device prototype |
| Problem solving | INA219 availability/cost problem; Simulink register/MUX/data-type debugging; Vite/Firebase build and deployment failures |
| Coding skills | C/C++ (Arduino, Energia, MSP430), MATLAB/Simulink & scripting, RTL design `[confirm: Verilog or VHDL]`, JavaScript/React/Vite/Tailwind/Firebase, Git/GitHub, HTML/CSS |
| Entrepreneurial skills | Cost-engineered prototypes, BOM decisions, evaluating whether an opportunity is actually worth the time |

---

## 2. Copy-paste skills blocks

### Resume / CV — "Technical Skills" (grouped, keyword-front-loaded)

> **Space & Satellite Systems** — CubeSat fundamentals (1U/3U, subsystem architecture: EPS, PMAD, OBC, ADCS, TT&C), LEO orbit and eclipse geometry, energy-balance and battery-sizing calculations, mission modes and safe-mode hysteresis, FDIR concepts.
>
> **Modelling, Simulation & Digital Twins** — MATLAB/Simulink system modelling (datapath/register-level model of a custom processor), energy-integration battery models (SOC/DoD, OCV, internal resistance, charge/discharge efficiency, capacity fade), fault injection and Monte Carlo uncertainty analysis, verification by hand calculation, unit testing and energy-accounting closure.
>
> **Embedded Systems & Electronics** — Arduino, ESP8266, ESP32, MSP430, STM32 `[confirm: only if you have actually used it]`; sensors (INA219, HX711, MPU6050, hall-effect, GPS, load cells); I²C, OLED/LCD displays, motors and servos; PCB design, fabrication and soldering; circuit design, measurement and hardware troubleshooting.
>
> **Energy & Power** — power/energy budgeting, current-voltage-power sensing, battery pack integration, DC power rails, PMAD and conversion losses, analog electronics (op-amps, ADC/DAC, feedback, signal conditioning).
>
> **Digital Design & FPGA** — RTL design and simulation, digital logic design, processor microarchitecture, FPGA targeting (Lattice ECP5 family), verification with test cases.
>
> **Software & Web** — C/C++, Python (learning — see note below), MATLAB, JavaScript, React, Vite, Tailwind CSS, Firebase, npm, Git/GitHub, IoT dashboards (Blynk), Telegram bot integration, AI-assisted development workflows.

⚠️ **Two honesty rules for that block:**
1. **Python** — only write "Python (foundational)" if you spend the time in section 4 tonight/this week. Otherwise write "Python (learning)". The single most likely technical follow-up question in this interview is *"can you code in Python or JavaScript?"*, and the worst outcome is a claim you can't back up live.
2. **STM32/ARM** — `me` says you are *interested in learning* it, not that you use it. Leave it off the CV for this application, or mark it "(learning)". HDL language: state the one you actually write.

### AICTE portal — "Relevant Skills" / keyword field
> CubeSat systems · Digital twin simulation · Electrical power systems and energy-balance analysis · Battery state-of-charge modelling · Solar energy & power budgeting · Modelling & simulation (MATLAB/Simulink) · Embedded systems & microcontrollers · Sensor integration & telemetry · Circuit & PCB design · Verification & unit testing · Python, C/C++, JavaScript · Git/GitHub · Data visualisation & reporting

### Short bio (≈50 words)
> ENTC undergraduate (B.Tech, third year) with a hands-on record in embedded systems, energy monitoring and digital design. Modelling an original 16-bit processor in Simulink and RTL for FPGA implementation. Currently extending that modelling discipline into spacecraft power systems: CubeSat energy balance, battery state-of-charge behaviour, fault scenarios and reliability analysis.

### LinkedIn / portfolio About (≈150 words)
> I'm an Electronics & Telecommunication engineering student at KIT's College of Engineering, Kolhapur, interested in the place where energy, embedded systems and modelling meet.
>
> My main project is **SV-16** — an original 16-bit processor architecture, from instruction set and datapath through RTL and simulation to a Lattice ECP5 FPGA target and a PCB. Building it taught me the habit I care most about: model the system first, then verify the model against a hand calculation, a test, or the hardware itself.
>
> Alongside that I build energy-monitoring hardware — current/voltage/power sensing with INA219, load-cell instrumentation, OLED and dashboard telemetry over ESP8266.
>
> I'm now applying that same discipline to **spacecraft power systems**: CubeSat orbital and eclipse geometry, solar generation through PMAD, battery state-of-charge modelling, safe-mode logic, fault injection and reliability analysis under uncertainty. Open to research-oriented work in satellite systems, digital-twin simulation and energy modelling.

---

## 3. Your three-tier honesty framework

Use this whenever you describe a skill. Interviewers read tier discipline as maturity.

| Tier | Phrase to use | Examples (yours) |
|---|---|---|
| **Demonstrated** (you have built it and it works) | "I've built…", "I implemented…", "I've verified…" | PCB fabrication, ESP8266/INA219 telemetry, Simulink register/ALU model, unit-tested CubeTwin reimplementation, React/Vite/Tailwind front ends |
| **Working knowledge** (you can use it with a reference) | "I work in…", "I'm comfortable with…" | MATLAB/Simulink, Arduino IDE/Energia, Git/GitHub, soldering, C/C++ |
| **Learning** (be explicit, and cite a plan) | "I'm learning X — I'm at Y, and my next step is Z" | Aerospace domain specifics, Python, STK/Orekit/GMAT, formal requirements traceability |

**Example of doing this well, in one breath:**
> "Demonstrated: I can model a battery's energy behaviour and verify it against hand calculations — I did exactly that with your published equations, 60 unit tests, and it reproduces your 274.5 Wh generated and 80% minimum SOC. Working knowledge: embedded C and MATLAB/Simulink. Learning: aerospace-specific tooling like Orekit and GMAT, and Python — which is the first thing I'd fix in week one if you hire me."

---

## 4. Closing the gaps it exposes — a real plan (say this if asked)

**Tonight / this week (2 hours):**
1. Python basics for simulation: variables and types, `for` loops, functions, `math`, lists and dicts, `print(f"...")`, writing and running a `.py` file. Then run `code/cubetwin_model.py`, change the altitude to 600 km, and print the new period. That single exercise covers the "can you code?" question with evidence.
2. Be able to state the eight equations from memory (cheat sheet).
3. Know the reference mission defaults (500 km, 94.5 min, 20/18 W, 40 Wh, 80%, 30%/20%, 8/3 W, payload 18 W × 10 min @ 4 h, downlink 14 W × 8 min @ 5 h, 24 h at 10 s).

**Week 1–2 of the internship, if selected (mirror their own roadmap):**
| Their week | What you'd do to catch up |
|---|---|
| 1 — mission definition, CubeSat basics | Read NASA **CubeSat 101** (the first reference on their own page) and the **Cal Poly CDS**; write the assumptions register; do the 500/600 km period calculation |
| 2 — power budget, sunlight/eclipse | Build the power budget table and mission-mode table; compute eclipse energy by hand, then in code |
| 3 — battery MVP | Energy-integrating loop with SOC limits, reserve warning, unmet-load accounting; prove losses have the correct direction and that the same scenario + seed reproduces identical output |
| 4 — voltage, temperature, Stage Gate 1 | OCV lookup, terminal-voltage estimate, I²R lumped thermal model; then write down explicitly what verification *cannot* tell you (validation needs data) |

**Domain reading (their own reference list — quote it, don't invent sources):** NASA *CubeSat 101*; Cal Poly *CubeSat Design Specification*; NASA *Small Spacecraft Power Systems* (State-of-the-Art); ECSS *Li-ion Battery Testing Handbook* (ECSS-E-HB-20-02A); NASA GMAT and Orekit as future higher-fidelity comparisons.

---

## 5. What **not** to write or say

- ❌ "Satellite engineer" / "aerospace experience" — you have none yet, and this company's own page is built on *not* overclaiming. One bluff here costs you the whole interview.
- ❌ "Digital twin developer" without the qualification that separates models from calibrated twins.
- ❌ Rocketry, propulsion, launch, or orbit-determination jargon you can't derive.
- ❌ "Expert in Python/JavaScript" if you can't write a function live.
- ❌ Buzzword salads. Their site is unusually precise; match its register. Short, specific, evidence-backed sentences.
- ❌ Anything you'd have to walk back when they ask "show me the repository."

**The sentence that maximises your chances, if you use only one:**
> "I reimplemented your published equations — orbital period, solar through PMAD, battery integration, voltage, thermal, safe-mode hysteresis, faults and Monte Carlo — and verified my implementation against your published run: 274.50 Wh generated against your 274.51, 80.07% minimum SOC against your 80.0, and the energy-accounting residual closes. Where I don't match — my final SOC is 96.95% against your 91.81% — I had to infer your charge-efficiency default, and I'd rather tell you that than pretend it lines up."
