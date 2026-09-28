# Interview prep — CubeTwin Satellite Engineering Internship (iTelematics / AICTE)

Interview: **29 September 2026**. Role: **CubeTwin — CubeSat Digital Twin Simulation** intern.
Everything here is built from the [AICTE listing](https://internship.aicte-india.org/internships/1-INTERNSHIP_17905981966aba5c345b49e), the [CubeTwin platform documentation](https://aerospace.ishavasyam.org/space/cubesat), ishavasyam.org, itelematics.com and your profile in `me`.

## Files

| File | What it is | When to read it |
|---|---|---|
| **[01-interview-brief.md](01-interview-brief.md)** | The main pack: who they are, what they'll ask, 33 likely questions with answer shapes, your project pitches, questions to ask them, red flags, logistics | Tonight, sections 1 + 9 |
| **[02-skills-mapping.md](02-skills-mapping.md)** | Your real experience mapped to their 10 keywords + 15 desired attributes, plus copy-paste résumé/portal/LinkedIn skills blocks | Tonight, 15 minutes |
| **[03-synopsis-and-written-answers.md](03-synopsis-and-written-answers.md)** | The synopsis the portal asks for, plus pre-written answers for screening questions | Tonight if they ask in writing |
| **[04-cheatsheet.md](04-cheatsheet.md)** | One page: formulas, numbers, five killer points, two questions | Tomorrow morning |
| **[code/](code/)** | A working, unit-tested reimplementation of CubeTwin's published equations — your evidence if they set a take-home task | Tonight, skim; run it once |
| **[pdf/](pdf/)** | Print/phone-ready PDFs of all four documents — see below | Whenever you want it offline |

## PDFs

Everything above is also rendered to PDF, so you can read it on your phone tonight or print the cheat sheet:

| PDF | Pages | Use it for |
|---|---|---|
| `pdf/CubeTwin-Interview-Pack.pdf` | 23 | The whole pack in one file — cover page, clickable contents, running chapter headers, page numbers |
| `pdf/01-interview-brief.pdf` | 11 | The main brief on its own |
| `pdf/02-skills-mapping.pdf` | 5 | Skills reframing and copy-paste blocks |
| `pdf/03-synopsis-and-written-answers.pdf` | 4 | Synopsis and written answers to paste into the portal |
| `pdf/04-cheatsheet.pdf` | 2 | **Print this one** and keep it beside you during the call |

Regenerate them after editing any markdown:

```bash
python3 tools/md_to_pdf.py       # needs: pip3 install reportlab fonttools
```

## Do these three things in the next hour
1. Read `01-interview-brief.md` **section 1** (60-second version) and **section 5** (the numbers).
2. Open [aerospace.ishavasyam.org/space/cubesat](https://aerospace.ishavasyam.org/space/cubesat), run the baseline simulation, then change altitude to 600 km and watch the period move to ~96.5 min. That's a real observation you can describe.
3. Run the model:
   ```bash
   cd interview-prep/code
   python3 cubetwin_model.py          # reference run + workbook experiments
   python3 -m unittest test_cubetwin_model.py   # 60 tests, all passing
   ```

## The one paragraph that matters most
> iTelematics is a small Bangalore R&D company whose commercial work is **EV telematics and battery intelligence** (capacity fade, internal resistance rise, SOH/RUL, thermal runaway). CubeTwin is its **space** education-and-research project under EV Society™ / EV.ENGINEER™ and ISHAVASYAM.ORG. The internship is remote, 3 months, **unpaid**, 13 academic credits, and follows a published 12-week roadmap: orbital-period function → power budget → battery MVP → voltage/temperature → mission modes → fault injection → telemetry/reliability → 3D → Monte Carlo → validation workbook → release. They care overwhelmingly about **verification, documented assumptions and not overclaiming**. Match that register and you will sound like one of them.

## Honesty note
Nothing in this pack invents experience. Where you lack something (aerospace domain, Python, rocketry), the documents give you an honest bridge statement instead of a bluff. That is deliberate — this employer's entire public platform is built on stating limits clearly, and a bluff would be the fastest way to lose the interview.
