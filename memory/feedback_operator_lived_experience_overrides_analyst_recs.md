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

## Cross-refs

- [[feedback-rigorous-validation]] — Joey's rigor on the build side (full byte diffs, ghidra cross-checks) — complementary, not contradictory. Be rigorous about what's verifiable in the firmware; trust the operator on what's verifiable from the wheel.
