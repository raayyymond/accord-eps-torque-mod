---
name: operator-wants-live-general-capabilities
description: Operator prefers LIVE / general / reusable capabilities over one-off post-hoc workarounds, and challenges "impossible/can't" claims — expects an empirical on-car test, not a reasoned dismissal. Also: check prior handoffs before proposing an approach (things may already be ruled out).
metadata:
  node_type: memory
  type: feedback
  originSessionId: da1ed7ee-745a-43f9-a29b-a7b80b6ac40f
---

How the operator (Joey/Raymond) wants telemetry/capability work approached, learned 2026-07-12:

- **Prefers a LIVE, general, reusable capability over a narrow post-hoc workaround.** He rejected the Tier-2 firmware ring-buffer + park-and-read-out design ("I do not want Tier 2. I want to look at logs of RAM values. This capability would be very valuable for even more modifications in the future."). Bias toward a channel that streams RAM values into the drive log continuously and can be reused for future mods — not a one-shot capture.
- **Challenges "impossible / can't" claims and expects them settled empirically.** This session I twice over-claimed a hardware impossibility; he pushed back ("I don't buy...", "Does staying on OBD work for steering?"), and the on-car A1/A2 sweep + inventory resolved it far better than my armchair reasoning. When tempted to say "X can't work," instead design the cheap read-only on-car test that proves it, and state a prediction separate from the evidence.
- **Points back to prior work when context is missed.** I re-proposed a CAN broadcast that the 07-08 handoff had already ruled out (gateway-blocked). He caught it ("my understanding is that we ruled out CAN broadcast already"). READ the recent handoffs/memories for what's already been tried before proposing an approach.

**Why:** avoids wasted cycles on dead ends and false-impossibility calls; matches his engineering style (verify on the car, build reusable tools). Aligns with [[feedback_rigorous_validation]] and [[feedback_operator_lived_experience_overrides_analyst_recs]].

**How to apply:** default to proposing the live/general version of a capability; when something looks blocked, produce the read-only test that decides it (with a stated prediction) rather than declaring it impossible; and grep/read the latest handoffs before recommending a path. Related: [[comma4-eps-uds-poll-comma-vs-redpanda]].
