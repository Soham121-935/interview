# Synopsis & written answers (the AICTE portal asks for a synopsis)

The listing states **"Synopsis required: Yes"**, and the interview itself is *"a short conversation or a take-home task"*. Written answers may be requested before, during, or after. These are written in your voice, aligned to CubeTwin's actual scope, and every claim is one you can defend.

Replace anything in `[square brackets]` before submitting.

---

## 1. Synopsis (≈250 words — the main one)

> **Proposed contribution to CubeTwin — CubeSat energy, mission and reliability analysis**
>
> CubeTwin models how orbital sunlight and eclipse, solar generation, subsystem loads, battery behaviour and faults determine whether a CubeSat can complete its mission. Its 12-week roadmap defines a clear path from a single verified function to a released engineering prototype, and the work I would most like to contribute to is the part that decides whether the model can be trusted: **verification, fault analysis and reliability reporting**.
>
> I work the way the roadmap is structured. I calculate by hand first — for example the circular-orbit period at 500 km, T = 2π√((Re+h)³/μ) = 94.47 minutes, and the energy needed for a 35-minute eclipse at 8 W, 4.67 Wh (4.91 Wh drawn from the pack at 95% discharge efficiency) — and then write a test that asserts the code reproduces the calculation within a stated tolerance. I have already implemented the platform's published equations (orbit and eclipse, solar generation through PMAD, energy-integrating battery with SOC limits, terminal voltage and I²R temperature, safe-mode hysteresis, fault injection, telemetry and Monte Carlo uncertainty) and verified my implementation against the published baseline run: 274.50 Wh generated against 274.51 Wh, 194.47 Wh consumed against 194.52 Wh, 80.07% minimum SOC against 80.0%, and an energy-accounting residual of 5 × 10⁻¹¹ Wh. Where I could not match exactly, I have documented the inference rather than hidden it.
>
> My background is Electronics & Telecommunication Engineering: energy-monitoring embedded systems (INA219 current/voltage/power sensing, load cells, ESP8266 telemetry to displays and dashboards) and a current project building an original 16-bit processor from instruction set through RTL and Simulink modelling to an FPGA and PCB. I also build web front-ends (React, Vite, Tailwind, Firebase), which is relevant to a browser-based simulator with charts, CSV/JSON export and accessible summaries.
>
> I would like to work on fault-scenario design and detection, the validation workbook with requirement-to-test traceability, and the accessible reporting layer — always with the platform's own discipline: simulated results are not flight evidence, and a model's limits should be stated as clearly as its results.

---

## 2. Short synopsis (≈90 words, if the field is small)

> I am an ENTC undergraduate with hands-on experience in energy monitoring (INA219 current, voltage and power sensing; load-cell instrumentation; ESP8266 telemetry) and in modelling systems before building them (a Simulink model of my custom SV-16 processor architecture, alongside RTL targeting a Lattice ECP5 FPGA). I have implemented CubeTwin's published equations from first principles and verified my version against its published baseline metrics, including energy-accounting closure. I want to contribute to fault-scenario analysis, verification and reliability reporting, and to the accessible, exportable reporting layer of the browser simulator.

---

## 3. "Why do you want this internship?" (≈120 words)

> Because it joins the two things I already do. I build energy-sensing hardware — my prototypes measure their own current, voltage and power with an INA219 and stream that telemetry to displays and dashboards — and I model systems before I build them: I have a Simulink model of the 16-bit processor architecture I am implementing in RTL and taking to an FPGA and PCB. CubeTwin is exactly that discipline applied to a spacecraft: sunlight and eclipse, generation through PMAD, loads, battery state of charge, safe modes, faults and reliability under uncertainty.
>
> I also value how the project is framed. It states plainly that it is an educational prototype, that simulated data is not flight evidence, and that verification is not validation. I would rather learn engineering under that standard, and I would like to contribute to the verification and fault-analysis side of the roadmap.

---

## 4. "What will you contribute in the first 4 weeks?" (≈120 words)

> In week 1, the orbital-period function with unit tests against a hand calculation, plus the assumptions register. In week 2, the power budget and mission-mode tables, an eclipse-energy calculation, and the first SOC-versus-time plot with units on every axis. In week 3, the energy-integrating battery loop: SOC limits, reserve warning, unmet-load accounting, rejected-charge reporting, and proof that losses have the correct direction and that the same scenario and seed give identical output. In week 4, the OCV lookup and terminal-voltage estimate with undervoltage warnings, the optional lumped thermal model, and a written statement of what the model still cannot claim.
>
> Alongside that I can work on the interface: chart labelling, CSV/JSON export with units and metadata, print stylesheet and accessible chart summaries.

---

## 5. "Availability and commitment"

> Available for the full three-month duration, remote, with approximately 10–12 structured hours per week (two weekday evenings plus a weekend block) and attendance at scheduled reviews and workshops. I have reviewed the timeline — Batch 1 (1 October – 30 December 2026) or Batch 2 (1 January – 30 March 2027) — and `[state which batch you can commit to]`. My academic commitments are predictable through this period, and I will confirm any college-side credit or approval requirement before the start date.

*(Batch 1 begins three days after this interview — if you're offered it and can start, say so explicitly; it removes a reason to prefer someone else.)*

---

## 6. If they ask for a project statement (≈100 words)

> **Project:** verification and fault analysis for CubeTwin.
> **Objective:** make the simulated mission outcome trustworthy and explainable.
> **Method:** hand-calculated reference values → unit tests with explicit units and tolerances → energy-accounting closure → fault scenarios with baseline-versus-experiment comparison → seeded Monte Carlo with stated uncertainty → published limitations.
> **Deliverables:** verification test set, assumptions register, fault-scenario library with detector expectations, validation workbook pages, and a plain-language summary of what the model does and does not prove.
> **Success criterion:** an independent reader can reproduce every headline number from the documentation alone.

---

## 7. Pre-written answers to the likeliest written screening questions

**Q: Describe your most relevant project.**
> **SV-16 — an original 16-bit processor architecture.** I defined the instruction set and encoding, the datapath, register file and status system, the memory interface and the control concept, then implemented it in RTL (roughly 80% complete and tested) with a Simulink model for architecture-level work. The target is a Lattice ECP5 FPGA on a custom PCB, with the goal of programming the device and running test programs for hardware validation. The project is deliberately constrained: reliability over compactness, simplicity over unnecessary features, and buildability over theoretical optimisation, using easily obtainable parts.
>
> It is the most relevant project for this internship because it forced me to work in the order the CubeTwin roadmap uses — architecture, model, simulation, verification, then hardware.

**Q: What is your experience with batteries and power?**
> I have built battery-powered embedded nodes: an MSP430 LaunchPad with an ESP8266, INA219, OLED and DC motor on a rechargeable pack, and an ESP8266-based system that measures its own current, voltage and power with an INA219 alongside load-cell instrumentation. On the modelling side I have implemented a battery as an energy-integration state — SOC and DoD, charge and discharge efficiency, an OCV(SOC) lookup, internal-resistance voltage sag, I²R heating against a bus temperature, capacity fade that never creates energy, rejected charge at full, and unmet demand when empty. I understand why eclipse sizing drives capacity, why a reserve exists, and why depth of discharge is a cycle-life decision.

**Q: Are you comfortable working remotely and documenting your work weekly?**
> Yes. I already work this way on SV-16 — version control, dated progress notes, and decisions recorded so a collaborator can pick up the work. The weekly "results, evidence, assumptions and one next improvement" structure in your roadmap is the documentation format I would choose anyway.

**Q: What is your greatest weakness?**
> Depth of formal domain experience — I have no aerospace coursework and I have not used orbit-determination tools such as Orekit or GMAT. I have compensated by going to primary sources: your published model assumptions, NASA CubeSat 101, the Cal Poly specification, and the ECSS battery handbook from your reference list. I'd rather say what I don't know and show how fast I close it than claim experience I don't have.

**Q: Anything you'd like to ask us?**
> Use questions 1–6 from `01-interview-brief.md` section 10. Pick the ISAST-submission question and the roadmap-alignment question if you only ask two — both prove you read the roadmap properly.
