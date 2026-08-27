---
name: accord-lane-change-transient-is-dose-independent
description: "★★ The ~28 Hz lane-change transient is DOSE-INDEPENDENT — it runs at full amplitude on the STOCK rate lane and is non-monotone in dose. Excitation (ALC vs driver-commanded), not gain, is the live candidate. V70 must not chase the rate lane for it."
metadata:
  type: reference
---

# ★★ THE LANE-CHANGE TRANSIENT IS DOSE-INDEPENDENT — V69's stated purpose FAILED

V69 was built to attenuate the ~28 Hz lane-change transient captured on V68
([[accord-v68-lane-change-is-28hz]]). **It did not.**

- The transient **survived and is LARGER in p-p on V69** — **2,599** and **4,094** counts, against
  V68's recorded **1,468**.
- **It runs at full amplitude on the STOCK rate lane.** V58/r2b at dose **1.000×**: ×floor p90
  **14.93**, max **22.76**, **2,389 counts p-p @ 27.59 Hz**. **V59/r2c at 1.000× carries the corpus's
  largest p-p — 3,283 @ 27.07 Hz.**
- **Non-monotone in dose** — V62 at 2.000× is *quieter* than V58 at 1.000×.

| contrast (pooled, speed-matched) | ratio | verdict |
|---|---|---|
| 2.000× / 1.000× | **1.176 [0.641, 2.320]** | inside null |
| 2.403× / 1.000× | **2.897 [1.271, 11.439]** | does **not** clear its null |
| route-level Theil-Sen slope on dose | **+5.736 [−25.432, +34.934]** | **0 inside** |

## ★ EXCITATION, NOT GAIN, IS THE LIVE CANDIDATE
Holding **dose = 1.000× exactly**, ALC vs driver-commanded lane changes = **2.389 [1.453, 4.898]**
against a null of [0.44, 2.26] — **does not clear**, and rests on **one manual route**.
But holding **excitation** fixed collapsed the 2.403× dose contrast **2.849 → 2.013** with the CI
crossing 1. ⇒ *"an excitation contrast wearing a dose label"* — **the same class of error as the
withdrawn 28 Hz "mode"**, and caught the same way
([[accord-averaged-spectrum-needs-matched-speed-distributions]]).

## ⇒ 🛑 V70 MUST NOT CHASE THE RATE LANE FOR THIS SYMPTOM
The rate-lane hypothesis for the lane-change transient is **closed on an intervention**, not on an
inference: the dose was fully delivered (0.0000% above the rail) and the symptom got *bigger*.
The next question is about **what excites it** — ALC's command shape vs a driver's — not about `Kd`.
⚠ The excitation result is **one route** and does not clear its own null. It is the *direction to look*,
not a finding.

See [[accord-v69-flew-dose-response-non-monotone]], [[accord-v69-built-speed-shaped-rate-lane]].
