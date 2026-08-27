---
name: v39-flashed-no-improvement
description: "V39 was flashed and fixed neither the low-speed grinding/vibration nor the hard-turn ratchet, falsifying the direct Sensor-B torque-rate lane r24 as the cause of either."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-19T20:32:31.991Z
---

**2026-07-19:** V39 (`39990-TVA,A160-V39-LKAS-4x-V38guards-direct-rate-off417-driver320`) was FLASHED and road-tested. It changed **neither** symptom:

- low-speed grinding/vibration (tens of Hz, worst ~5 mph) — unchanged
- ratcheting on hard turns at higher speed (several Hz) — unchanged

V39's only functional change was zeroing the direct Sensor-B torque-rate aggregator lane `r24` for both signs at `|LKAS lane| >= 417` with voted driver torque `< 320`. That lane is therefore **falsified** as the source of either symptom, and by the V39 handoff's own pre-registered scoring it also did not produce the "new overshoot / reduced damping" outcome — so `r24` appears to matter less than its ±8192 clamp suggested.

**Why:** this closes off the leading V38 follow-up hypothesis and redirects the search. Per the V39 handoff's own decision table, "vibration remains" points next at adaptive lane `r26`, then `gp-0x6bd0`/`gp-0x6ad4` — but the falsification of an entire ±8192 lane also raises the prior on a **shared downstream cliff** (the `gp-0x6acc` ±8192 sanitize-to-zero, the aggregator per-lane zeroing range gates, the soft-EME bound/latch loop, or the governor's asymmetric slew) over any single lane.

**How to apply:** V40 baselines on **V38**, not V39 — drop the `r24` guard and its code cave entirely. Do not re-test single aggregator lanes without first ruling out the shared post-aggregator stages. See [[v38_flashed_hard_turn_feedback_v39]] and [[eps-lkas-chain-model-is-the-live-golden-reference]].
