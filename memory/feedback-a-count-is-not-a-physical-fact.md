---
name: feedback-a-count-is-not-a-physical-fact
description: "NAMED TRAP, four instances in one session — acting on a COUNT or an INDEX RELATION as if it were the physical quantity it stands for. Before acting on either, name the physical quantity and measure THAT."
metadata:
  type: feedback
---

🛑 **NAMED TRAP, 2026-08-10: a COUNT or an INDEX RELATION is not a PHYSICAL FACT.** Four instances in one
session, each of which nearly moved a decision:

| # | the count / index relation | what was read into it | the physical truth |
|---|---|---|---|
| 1 | route **r76's row↔frame index shift drifts −1 → −4**, frame counts differ by 2 | *"r76 has drifting TIMING — exclude the route"* | **bookkeeping, not timing.** Payload *age* is flat at 9.93 ms and r76's tails are the **cleanest** of the three routes (rows >12 ms: 4.61 %). Excluding it would have cost 10.95 engaged minutes at the corpus's highest engaged fraction |
| 2 | a **`gp-0x6752` writer census** returning "3 stores" | *"the writer set is closed"* | a **disp16-only scan is blind to the 6-byte extended-displacement form** — the census undercounted. A count from an encoding-incomplete scan is not a census |
| 3 | **V86's probe rung map applied to V89** | *"b5/b6 mean what they meant on V86"* | **V86B swapped b5/b6, and V87–V89 all inherit V86B's constants.** The bit index is an index; the *predicate* is the physical fact |
| 4 | **"payload age vs the most recent `0x18F`" = 0.000 ms** | *"the rows are not stale — skew refuted"* | the metric **assumes its own conclusion** (that the row holds the newest frame). Measured properly, `0x14A` precedes `0x18F` on **91.28 %** of 51,691 co-logged events ⇒ ~9.15 ms effective, a **mixture** `H(f) = 0.9128·e^{−j2πf·0.01} + 0.0872`, not a pure delay |

**Why:** an index, a bit position, a store count and a derived "age" all *look* like measurements. They
are bookkeeping over a representation. Each one is separated from the physical quantity by an assumption
— that indices track time, that the scan saw every encoding, that a bit means what it meant last build,
that the newest frame is the one held — and every one of those assumptions has been false in this kit.
The failure is quiet: the number is real, arithmetically correct, and points the wrong way.

**How to apply — before acting on any count or index relation:**
1. **Name the physical quantity it is standing in for.** Timing? Then say *seconds*. A writer set? Then
   say *stores that can change this cell*. A predicate? Then say *the comparison and its constant*.
2. **Measure that quantity directly, by a route that does not go through the index.** Timestamps, not row
   offsets. Both an encoding-complete byte scan **and** Ghidra
   ([[feedback-neither-ghidra-nor-python-alone-is-complete]]). The rung's constant read out of the built
   image, not out of the previous build's spec.
3. **Ask what the metric assumes.** If the answer to the question is an input to the metric, it is not a
   discriminator — it is a restatement. (Three discriminators died this way in one dispute: `sstat`,
   `raw18_b4 → sca`, and payload-age.)
4. **A count is only load-bearing with a second, independent method** — and a null count doubly so
   ([[feedback-verify-with-ghidra-and-bytes-both]]).

⊕ Same family, already on record: `band_envelope` is peak-to-peak *scale*, not amplitude · `rate_f` runs
~25 % low · a ring-down through a bandpass must be quoted against a step control through the identical
filter ([[feedback-run-the-control-before-the-measurement]]) ·
[[accord-raw14-offbyone-in-every-cache]] is instance zero of exactly this trap.
