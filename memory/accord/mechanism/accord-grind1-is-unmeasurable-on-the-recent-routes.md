---
name: accord-grind1-is-unmeasurable-on-the-recent-routes
description: "Grind #1 was characterised at creep - the operator's words on V62 were 'original grinding at 2-5 mph is gone'. The recent routes contain essentially NO 2-5 mph engaged creep: r21 (V111), r22 and r23 (V112) yield zero creep windows, against 39 for r77 and 11 each for r85/r9e/ra5/r1e. So an all-speed 18-22 Hz statistic scores V112 WORST while the operator reports it the best build ever with grind #1 rare - the statistic is measuring a different phenomenon at a different speed. This explains every grind-#1 null and contradiction this session, and it means grind #1 cannot be measured on the current corpus at all."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 GRIND #1 IS **UNMEASURABLE** ON THE RECENT ROUTES — there is no creep exposure

## HOW IT SURFACED — my statistic contradicted the operator
I built a grind-#1 pipeline and **validated it against a known effect**: V101/V102/V103 accidentally
dropped Lever B, and the pipeline recovered its measured on-car effect — **OFF/ON = 2.32×
[1.62, 2.94]**, against the on-car **0.40 [0.27, 0.58]** ⇒ ≈2.5×. **The control passed.**
Then the hunt itself produced four predictors at p < 0.10 — and an ordering that is **flatly
contradicted by the operator**:
```
   r1e  V107   2.92   <- BEST on my statistic
   r21  V111   5.10
   r22  V112   7.33
   r23  V112   7.93   <- WORST on my statistic
```
🛑 The operator's report is the **opposite**: V112 is *"the best firmware ever… Grind #1 is now
rare."* All four "hits" were one collinear old-vs-new contrast. **Do not act on them.**

## ✅ THE CAUSE — THE RECENT ROUTES HAVE NO CREEP
Grind #1 was characterised at **creep**. The operator's own words on V62: *"Original grinding at
**2-5 mph** is gone!"* Engaged windows in that band:
```
   r77 (V90)  39      r85 (V100) 11     r9e (V103) 11
   ra5 (V105) 11      r1e (V107) 11
   r21 (V111)  0      r22 (V112)  0     r23 (V112)  0     <-- NONE
```
⇒ **The all-speed statistic was measuring 18-22 Hz at road speed on V111/V112 — a different
phenomenon from creep grind #1.** The contradiction dissolves, and the statistic is not wrong so much
as **pointed at the wrong regime**.
⊕ The creep-restricted positive control still recovers Lever B (**3.08×, expected ≈2.5×**) but on
**n = 1** OFF route, CI [1.93, 22.84] — directionally right, far too weak to hunt with.

## 🛑 WHAT THIS INVALIDATES
[[accord-knee-has-no-measured-dose-response-on-grind1]] pooled **all speeds** too ⇒ **that null is
about road-speed 18-22 Hz, NOT about creep grind #1.** Its conclusion (do not claim V121 fixes grind
#1) still stands, but for a **weaker** reason than stated: not "the dose-response fails" but
**"grind #1 was never measured."**

## ✅ WHAT WOULD UNBLOCK IT — and it is not a firmware change
Two options, either sufficient:
1. **A drive with real creep exposure** — several minutes of engaged 2-5 mph, the regime grind #1 was
   characterised in. The corpus simply has none on any post-V107 build.
2. **Operator timestamps.** The operator himself said *"I no longer have an understanding of the kinds
   of scenarios that elicit grind #1 because it is so rare."* ⇒ **a mark at the moment it happens**
   — even a horn tap or a spoken note — converts an unmeasurable symptom into a locatable one, exactly
   as the route-23 timestamp did for the peak-turn oscillation.
⇒ **This is now the SECOND gating measurement item**, alongside
`docs/scoring/DRIVE-CARD-manual-at-speed.md`. **No build, no flash.**
Tools: `analysis-2020accord/verify/grind1_pipeline_positive_control.py`,
`rlog-tools/studies/peakturn/grind_lever_hunt.py`.
