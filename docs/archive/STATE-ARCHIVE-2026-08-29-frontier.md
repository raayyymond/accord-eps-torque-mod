# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔ **THE BACKLASH BAND IS CAL-REACHABLE — AND CLOSED BY THE LIMIT-CYCLE EXCLUSION**
`gp-0x6b44` has **exactly 1 reader (`0x36760`) and 1 writer (`0x36BB0`, in `FUN_00036828`)**, and the
writer is pure calibration arithmetic — so the band width IS cal-reachable, contrary to the previous
"RAM cell, no lever" note:
```
   sVar23 = (uVar20 - cal 0xC61A8[=102])  if uVar20 > 102 else 0,  scaled by cal 0xC63CE[=1024] >> 10
   clamp:  >= cal 0xC619E [=307]  ->  307          (upper)
           <  cal 0xC61A0 [=123]  ->  123          (LOWER FLOOR)
   fault path (bit 0x800000)      ->  cal 0xC619A [=102]
   gp-0x6b44 = sVar23   then  half-width = (gp-0x6b44 * uVar7) >> 15  in FUN_00036682
```
✅ **[EVIDENCE] the hysteresis half-width NEVER narrows below 123 counts**, even at zero excitation.
✅ **[EVIDENCE] all five cals are VIRGIN across all 163 build images.**
⭐ On the control-theory reading this looked like a real lever: a backlash's describing function has
**phase lag that is WORST at small input amplitude** — precisely the creep/micro regime — and narrowing
the band *reduces* lag rather than adding gain, so it does not repeat the V162 error.

### ⛔ WHY IT IS CLOSED ANYWAY
The kit's strongest ratchet characterisation settles it:
> *"The ratchet is a lightly-damped **RESONANCE**, Q 14–29 — ring-down ζ 0.017–0.036, the only
> estimator that passes its control; **limit cycle EXCLUDED**; motor/rack-side."*

**A backlash-driven oscillation IS a limit cycle.** The ring-down evidence excludes one, so the
backlash is **not generating the ratchet**; narrowing it would mainly admit more small-signal noise
(which is what a hysteresis band is FOR), and the lane is attenuated **8x** at 7.8 Hz by the following
0.93 Hz low-pass regardless. ⛔ **NOT a ratchet lever. Recorded so it is not re-proposed.**
⊕ The counter-risk is real and symmetric: a deadband exists to reject small-signal chatter, so
narrowing it can *increase* stutter. With the limit-cycle route excluded there is no argument that the
benefit outweighs that risk.

