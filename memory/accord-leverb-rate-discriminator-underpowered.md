---
name: accord-leverb-rate-discriminator-underpowered
description: The Lever-B x rate discriminator was run and its CI is 2.4x the effect it tests — r24's engaged arm is NOT exonerated, and the binding constraint on V89 is EXPOSURE, not analysis.
metadata:
  type: project
---

[[accord-ratchet-scales-with-wheel-rate]] filters candidate levers structurally: the culprit must be
**engagement-gated AND rate-driven**. Exactly one known thing is both — **Lever B**, which repoints
r24's gain gate to `gp-0x6806` ("LKAS applying") and swaps the gain 2622 → **5244** while it holds.
r24 is a 4-sample backward difference of column torque, i.e. a rate derivative.
**Every build has pushed r24 UP. The rate result says test it DOWN.**

## The test, and the result
`analysis-2020accord/v89_a6_leverb_discriminator.py`. Both flags **byte-derived from each build's own
image**, never quoted:
- **Lever B** = (`0x3AA96` == `FB` ∧ `0xC6446` == 5244)
- **damper**  = (FactorC mode-26 `Y[0]` ≠ 0), carried as its own interaction because the two co-occur
  (**corr = −0.499**)

| build | Lever B | damper `Y[0]` |
|---|---|---|
| V75 · V74 · V80 · V81 · V83a | no | 566 / 429 / 566 / 566 / 566 armed |
| V87 | no | 0 Honda |
| V76 · V86B | **YES** | 429 / 908 armed |
| V84 · V85 · V86 · V88 | **YES** | 0 Honda |

400 windows / 12 routes / 93 episode blocks, a clean 6-vs-6 route split.
`eng × log|rate| × LeverB`, band contrast vs the 32–38 Hz control: **−0.101 [−0.381, +0.298]**.

## 🛑 The verdict is INCONCLUSIVE, not a null
**The CI half-width (0.340) is 2.4× the effect being tested (+0.144).** It cannot distinguish *"no
modulation"* from *"modulation as large as the entire effect"*.
⇒ **r24's engaged arm is NOT exonerated, and no build may be justified on this either way.**
The script's verdict logic now refuses to print "exonerated" unless the CI is narrower than the
effect — [[feedback-a-falsifier-only-fires-if-it-could-have-fired]] applied to the instrument, caught
before write-up this time.

## What would close it — and it is an EXPOSURE problem
Roughly **4× the episode blocks (93 → ~370)**: matched **ENGAGED and MANUAL** exposure at matched
**WHEEL RATE**, on both a Lever-B and a non-Lever-B build. The corpus cannot supply it because the
two arms barely overlap — engaged |rate| p50 = 16 °/s against manual 52 °/s, and engaged `hands`
p50 = 193 counts against manual 2005.

⇒ **Design the next drive around deliberate slow-and-fast wheel sweeps, engaged and manual, at the
SAME vehicle speed** — not a route flown for distance. This is now the binding constraint on V89.

## Route → build map used (documentation-derived; the weak link)
`r5e`=V75 · `r61`=V74 · `r65`=V76 · `r66`=V80 · `r67`=V81 · `r68`=V83a · `r6d`=V84 · `r6e`=V85 ·
`r6f`=V86 · `r70`=V86B · `r71`=V87 · `r73`=V88. Each cache's `probe_build` agrees on all 12.
🛑 **An rlog cannot identify its build from the version string** — every build reports
`fw='39990-TVA,A160'`.
🛑 **`_cache_r66` and `_cache_r66x` are the SAME route** — load one cache per route.
