---
name: feedback-a-falsifier-only-fires-if-it-could-have-fired
description: "Size every rung and every abort criterion against its own lane's reachable output and the route's real exposure; a falsifier that could not have fired is not evidence, in either direction."
metadata:
  node_type: memory
  type: feedback
---

🛑🛑 **A FALSIFIER ONLY FIRES IF IT COULD HAVE FIRED.** Two instances in one session, running in
**opposite** directions — both would have produced a wrong verdict.

**Instance A — a rung that read zero and was misread as a result.** V84's `b7`/`b6` tested
`|r24| ≥ 1024` on a lane whose input **never exceeded `|r1| = 201`**. They read **0.0 across 68,235
frames in BOTH arms**, and that was read as *"the lever was out of force."* **It was not** — the rung
could not have fired either way. [EVIDENCE: the 0.0000 duty and the independently recorded input bound
agree.]

**Instance B — an abort criterion that "passed" on no exposure.** V85's pre-registered damper abort
("any 26–31 Hz regression toward V81's 25.1% burst duty") did not fire on route `6e`. Route `6e` had
**22.4 s engaged ≥80 km/h** (V84 had 158.1). **That is not a pass.**

**Why:** this is **RULE 5** (*a null is only a null if the lever was in force*) applied to the
**INSTRUMENT** rather than to the lever — and the kit has now made the error at both ends. The prior
recorded instance is V69, which spent **all three** of its rungs this way and whose `b4` was
**structurally vacuous**.

**How to apply:**
1. Before choosing a threshold, compute the **producing lane's own reachable output range** at the
   operating point you care about — its clamp, its LERP ceiling, its index axis — and **state that
   number in the build note.** A downstream gate's width is not that number.
2. Before scoring **any** pre-registered falsifier or abort criterion, including one that comes back
   **clear**, state the **exposure** it had and show the criterion was reachable. If it was not, the
   correct verdict is **UNMEASURED**, not pass and not fail.
3. Prefer a prediction the instrument can actually resolve. Amplitude ratios have failed four builds
   running against a **[0.63, 1.50]** split-half null; that is why V86 pre-registers a **frequency
   ratio** with a declared **AMBIGUOUS** outcome distinct from a null.

Related: [[feedback-size-probe-rungs-against-lane-reachable-output]],
[[feedback-probe-the-gate-not-just-the-output]], [[feedback-episodes-not-windows]],
[[accord-v85-flew-lever-delivered-bands-are-null]], [[accord-v86-built-the-frequency-lever]].
