---
name: accord-the-return-to-centre-crux-and-what-died-for-it
description: The operator renamed the target — the LKAS return-to-centre trajectory should be as smooth as the manual return AND faster. Seven levers died against it in one session, including the pre-declared V97 and the whole return-to-centre lane.
metadata:
  type: project
---

**The operator, 2026-08-12, after seeing time-domain captures:**
> *"there is ringing in the driver torque, and a wiggle in the steering angle as it returns to center.
> Normally, without LKAS engaged, there is no ringing and no wiggle. The 2nd case is how the LKAS
> return to center should look, AND it should be faster than with LKAS disengaged. THIS is the crux of
> micro-ratcheting and grinding."*
> …and, on the instrument: *"take the derivative — the wiggles should look like **wiggles/spikes on
> top of a raised flat section**."*
> …and, on the mechanism: *"it feels like effectively a **steer angle rate limit for LKAS engaged**."*

## THE REGIME — and it invalidated the kit's own mask
🛑 **HANDS ARE OFF during the return** (operator, direct answer). Wind = hands ON, return = hands OFF.
**The kit's `|tq| > 1200` mask selects the WIND phase and excludes the RETURN almost by construction**
— every 6–9 Hz number produced before this session is about the wind phase.
⊕ Also answered: **no left/right difference** (so `0xC63F8`/`0xC63FC`'s 10× asymmetry is deprioritised)
and **he does NOT feel the ~0.5–1 Hz surge** (so the virgin authority-collapse curve is OFF the table).

## WHAT IS MEASURED [EVIDENCE]
- **Ring: 3.5–6.5×** engaged vs LKAS-off, robust across every detector setting, placebo floor ~2.0.
- **Wiggle (angle): 1.94–2.76×** against a 1.70–1.88 placebo floor — **marginal**.
- 🛑 **Return SLOWNESS is NOT ESTABLISHED.** Raw medians differ (24.8 vs 67.0 °/s) but `p_placebo` =
  0.459 and the ratio **flips sign with the detector**. At 11 engaged / 7 LKAS-off episodes the CI
  fold-width on duration is **3.27×** against an observed ~2.7× — **underpowered.**
  ⚠ An earlier "2.25× slower" report was **retracted** on these controls.
- The ring **persists hands-off** (138/265 ct vs 33/28) ⇒ not a driver-arm artefact.
- The LKAS command is a **DC constant for 52–70 % of the return and rings at full amplitude anyway**
  ⇒ **the excitation is SENSOR-FED; every command-side lever is excluded.**

## ☠ SEVEN LEVERS DIED — each before a build was cut
| lever | how it died |
|---|---|
| **pre-declared V97** `gp-0x6b4c`/`gp-0x6b4e` | `gp-0x6b4e` **provably ≡ 0**; §A5 priced gate WIDTH when the failure mode is the signal never being non-zero — that IS the V64 null. Array is `gp-0x62c8[]` not `gp-0x62f8[]`, and they are **two different arrays 0x18 apart** |
| **the return-to-centre lane** | 🛑 it is a **RACK END-STOP CUSHION** — arms on `\|gp-0x6b98\|>4096` AND motor rate `<200` (a STALL detector), splits by sign into left/right stop enums, **no angle term anywhere**, gate needs `\|gp-0x6bf0\|>8878`. **~99.3 % dead in MANUAL too** ⇒ its absence cannot explain the engaged/manual difference. **Do not arm it** |
| `0xC520C` governor ceiling | `gp-0x6ac0` = **4.7121 ct per column °/s** ⇒ first knot **222.8 °/s**; measured returns max **528 ct vs a 1050 knot, 0.00 %** reach it |
| `0xC6194` LKAS slew limiter | **real and calibrated** (3 ct/tick = 1.37 s full scale) but its partition `0xC4118` is **all-1** ⇒ 100 % bypasses it. 🛑 the record's *"output ×0"* reason is WRONG — that is `0xC6196`. **Arming it goes the wrong way** |
| **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]**, CI excludes the predicted +1 — **and** `gp-0x6b4c` is a second LKAS route that never sees AUTH. ⚠ the table header is **`0xC67BE`**; `0xC67C8` is its `Y[0]` |
| PID Ki `0xC6B12` | **INERT** — at 6–10 km/h the P term alone (16,000 at e=2000) exceeds the anti-windup bound (7,264); the integrator is pinned |
| `0xC63A6` / `0xC63A4` | `0xC63A6` is **a cliff edge, not a lever**; `0xC63A4`'s lane carries **~1.1 ct of a 342 ct signal** |

🛑 **CLAUSE 2 HAS NO MECHANISM.** Three candidates for the slow return died and nothing replaced them.
**V97 does not address it and must not be scored as if it did.**

## WHAT THE NEXT DRIVE NEEDS
Matched engaged/disengaged **hands-off returns from similar starting angles**, many more of them —
11 vs 7 episodes cannot resolve a 2.7× effect. Scoring config is machine-readable in
`analysis-2020accord/sessions/v97/rtc_measure.json` → `config`; scorer is `rlog-tools/studies/ratchet/v97_return_to_centre.py`.

Links: [[accord-v97-is-a-loop-pole-and-the-direction-is-measured]] ·
[[feedback-episodes-not-windows]] · [[accord-damper-cannot-reach-micro-regime]]
