# ONE-PAGE CHEAT SHEET — CubeTwin interview

**Read this in the morning. Nothing else. Keep it beside you during the call.**

---

## Their reference mission (3U, LEO, 500 km)
`94.5 min orbit` · `59.5 min sunlight / 35 min eclipse` · `20 W array → 18 W delivered (90% PMAD)` · `40 Wh battery` · `80% initial SOC` · `reserve 30% / safe entry 20%` · `nominal 8 W / essential 3 W` · `payload 18 W × 10 min at 4 h` · `downlink 14 W × 8 min at 5 h` · `24 h at 10 s step` · `bus temperature 20 °C`

## The eight formulas
```
T      = 2*pi*sqrt((Re+h)^3/mu)     Re=6371 km  mu=398600.4418 km^3/s^2   -> 94.47 min @500 km
Psolar = G*A*eta_cell*derating*max(0,cos θ)        G=1361 W/m^2          -> 20 W -> 18 W
Pnet   = Psolar_delivered - Pload
E     += eta_c*Pnet*dt/3600          (charging)
E     += Pnet*dt/(3600*eta_d)        (discharging)          eta_d = 0.95
SOC    = 100*E/capacity ;  DoD = 100 - SOC
Vterm  = OCV(SOC) - I*Rinternal      -> 1 A × 0.12 Ω = 0.12 V sag
dT     = dt/C_th*(I^2*R + Q_ext - (T - T_bus)/R_th)
CONTROLLER:  safe_entry(20%) < reserve(30%) <= recovery(35%) <= max SOC  + recovery dwell
```

## Numbers to say without hesitating
| Ask | Answer |
|---|---|
| Period at 500 km | **94.47 min** (say "about 94.5") |
| Period at 600 km | **96.54 min** — higher orbit, longer period |
| Eclipse at β = 0, 500 km | **37.8% of orbit ≈ 35.7 min** (β = 0 is worst case) |
| 8 W for 35 min | **4.67 Wh**; **4.91 Wh** drawn at 95% |
| 40 Wh at 80%, 8 W for 1 h | **23.58 Wh → 58.95% SOC** |
| Baseline delivered solar | 20 W × 0.90 = **18 W** |
| Equivalent full cycles | 152.64 Wh ÷ (2 × 40) = **1.908** |
| 6 W heater for 2 h | 12 Wh, and **more than 12 Wh** drawn through the discharge path |

## Five things that make you the strongest candidate in the room
1. **"I calculate by hand, then assert the code matches within a tolerance."**
2. **Verification ≠ validation.** Verification = did we build the model right (code vs equations, tests, hand calculation). Validation = did we build the right model (equations vs reality, calibration against measured data). Their own words.
3. **Digital twin ≠ simulation.** A twin is connected to the state and history of a *particular* physical system; CubeTwin is a simulation until it's calibrated with traceable data. They say this themselves — agreeing precisely is the winning move.
4. **Truth vs observed vs detected.** Physical truth ≠ telemetry ≠ detector output. A +15 pp SOC bias makes the spacecraft look healthy while it's actually below reserve. Their bias detector uses truth as a *teaching oracle*; real detection needs independent measurements.
5. **Fault injection is not proof of detection.** Say it before they do.

## Your three strongest cards (and the link)
- **SV-16** (own 16-bit ISA, ~80% RTL tested, Simulink model, ECP5 FPGA + PCB) → *"a model of a system I intend to build, verified against hand calcs and hardware."*
- **Saline monitoring system** (INA219 current/voltage/power sensing, HX711 + 3 load cells, ESP8266, OLED, Blynk + Telegram, ₹1,700/₹1,350) → *"a miniature EPS with telemetry and cost engineering."*
- **Web work** (React/Vite/Tailwind/Firebase) → *"the platform is half physics engine, half interface — I can work on both."*

## If you blank
> "I don't know that off the top of my head. I'd start from [formula/source] and check it against [hand calc / their metric]. May I reason it out loud with you?"

## Two questions to ask (of the nine in the brief)
1. "Your 12-week workbook runs 14 Sept – 6 Dec, but the listing start date is 31 Dec — how do Batch 1 interns fit into a roadmap that's already mid-flight?"
2. "Week 3 mentions an 'ISAST-ready PDF' with a ~30 September submission — which submission is that, and is it still open?"

## Logistics
Camera at eye level · light in front · headset tested · hotspot ready · CV + cheat sheet + GitHub open · notebook for live calculation · water · join 2 min early · **do not overclaim anything**.

## One closing line to leave them with
> "I know what a model can and cannot tell you, I document the difference, and I'll do the hand calculation before I trust the code."
