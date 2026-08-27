---
name: feedback-operator-lived-experience-overrides-analyst-recs
description: "When Joey reports lived driving experience, that's ground truth that overrides abstract analyst-agent recommendations. Don't recite risk mitigation against his confirmed observations."
metadata: 
  node_type: memory
  type: feedback
  source: user
  originSessionId: cd9f261f-6467-4ec6-949f-d60d43c08113
---

**Rule:** When Joey describes lived driving experience ("I already did the craziest drive I would ever do"), treat that as **ground truth that overrides abstract analyst recommendations**.

**Why:** Joey corrected me 2026-05-22 when I recommended an empty-parking-lot probe to "raise confidence on cols 7-8 stability from MEDIUM to HIGH" — citing Σ_oscillation's 9-10 sec strict-regime dwell figure. Joey pushed back: he'd driven his realistic envelope, the car was smooth, the 9-10 sec figure isn't a gap in PROPER's coverage — it's a fact about real driving rarely producing sustained >200°/s commanded rate at all. Openpilot's rate ceiling and Joey's driving simply don't generate that regime; testing a regime he doesn't drive in is testing something not load-bearing for him.

I had been reciting Spec C's recommendation without weighing it against the operator's ground truth.

**How to apply:**

1. **When operator confirms behavior**, trust the confirmation over abstract dwell-time / sample-size concerns from analysis agents. Operator-in-the-loop data ≠ analyst-in-the-sandbox data.

2. **Surface the math behind the framing** so the conversation converges. Don't just repeat the recommendation. ("The 9-10 sec figure isn't about coverage — it's about whether your realistic envelope ever exercises that regime.")

3. **Distinguish "I haven't measured X" from "X is risky"**. The former is a coverage gap; the latter is a verdict. Analyst agents often produce the former and Claude should not promote it to the latter without operator buy-in.

4. **When agents recommend additional data collection** ("do a parking-lot probe", "extend the drive", "log more telemetry"), check whether the data would meaningfully change what the operator can already report from real use. If not, surface the operator's existing data as the better signal.

5. **The car is the validator, not the report.** Reports describe data; the car describes physics. When they disagree, default to the car.

## ★★★★ 2026-08-04 — THE STRONGEST INSTANCE YET, AND IT COST A BUILD

A V70 was **built** on the recommendation *"restore V67/V68's control path"*. The operator overrode it:
*"V70 just reverts back to V68, which has the high-speed grind #2 issue. This needs to change. V70 needs
to try to fix all grind issues."* **He was right, and the build was superseded.**

**Why the recommendation was wrong — and this is the transferable part.** It optimised for the two
symptoms our instruments can measure and **dismissed his high-speed report because there is no line in
30–49.5 Hz.** That inference is invalid on its own terms: **CAN's Nyquist is 50.00 Hz and the comma
IMU's is 50.51, so BOTH vibration instruments are BLIND above 50 Hz**, and the acoustic inversion
independently places the excess at a centroid of **63.5 Hz [54, 80]**.

> 🛑 **RULE: an instrument null inside a band the instrument cannot resolve is not evidence of absence.**
> Before treating a null as informative, state the band the instrument can actually see, and check that
> the operator's report is inside it.

⇒ **The operator is the only instrument this kit has above 50 Hz, and his reports there are a
DOSE–RESPONSE, not an anecdote:** the high-speed grind is present on V67/V68 (**2.44×** at highway) and
he reported it **gone** on V69 (**1.000×** = stock at highway). It was being weighed as uninformative.

★ **The arithmetic then agreed with him**, which is what settled it: a scalar arm **replaces** a surface
Honda rolls off 3072 → 2151, so `arm/LERP` **rises with speed and peaks at highway** — and the rate lane
is a differentiator whose gain climbs with frequency. **The scalar arm is the worst-shaped lever in the
kit for that symptom.**

🛑 **The kit already knew this and did not apply it.** Two recorded results say the same thing from the
other side — [[accord-highway-acoustic-budget-bound]] (a highway acoustic null is uninformative; the
κ-predicted signal sits 2–9× *below* the mic's own floor) and
[[accord-mic-negative-carries-almost-nothing]] (grind #1 read **1.061**, inside its null, on a large real
oscillation). **Both were on the record. Neither was reached for.**
See also [[accord-both-instruments-blind-above-50hz]].

## Cross-refs

- [[feedback-rigorous-validation]] — Joey's rigor on the build side (full byte diffs, ghidra cross-checks) — complementary, not contradictory. Be rigorous about what's verifiable in the firmware; trust the operator on what's verifiable from the wheel.
- [[feedback_no_premature_disproven]] — same family: absence of a detection is not a disproof.
