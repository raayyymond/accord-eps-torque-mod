---
name: reference-accord-gain-rescaling-invariance-partition
description: "With openpilot's PID rescaled to match a firmware gain raise, every stage DOWNSTREAM of the gain sees stock-identical counts - so a symptom inside stock's torque range cannot be caused downstream. Partitions symptoms by stage before any tracing."
metadata:
  node_type: memory
  type: reference
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-20T02:41:33.976Z
---

**The single most useful analytical tool found in this project. It costs nothing and it eliminates whole classes of hypothesis before any disassembly.**

V38 raised the arbitration gain `0xC646C` 891 → 3564 (4×). The operator correspondingly quartered openpilot's lateral PID (kp 0.6→0.15, ki 0.18→0.045). Now follow the units through `C (CAN) → setpoint = C×−4 → lane = (setpoint × gain) >> 15 → everything`:

- For **the same physical torque at the wheel**, the comma sends C/4 and the gain multiplies by 4 ⇒ **lane counts are IDENTICAL to stock** ⇒ every stage downstream of the gain replays stock's exact count sequence, and no downstream absolute-count limit can behave differently than it did on stock.
- But the **setpoint** is 4× SMALLER ⇒ every stage **upstream** of the gain operates 4× closer to zero, so a fixed absolute threshold there occupies 4× more of the working range.
- The **one** downstream exception: torque ABOVE what stock could ever produce. Stock's max LKAS lane was **417 counts**. The band 418–1782 never existed before, so downstream limits calibrated around stock's range are newly reachable there.

**The partition this forces:**

| Symptom regime | Where the cause must be |
|---|---|
| Large command, above 417 counts | downstream of the gain — genuinely new territory |
| Small command, inside stock's range | **upstream of the gain**, or keyed on C/setpoint rather than lane counts, or **not in the firmware at all** |

**Why:** it retro-explained two failed builds instantly. V39 (r24 derivative lane) and V41 (motor-rate cap) were both aimed at the small-command vibration and both sit downstream of the gain — **neither could ever have moved it**, which is exactly what the road showed. Two flash cycles that this argument would have saved.

**It also predicted where the real mechanisms were, before the traces ran.** The ratchet was assigned "downstream, >417 counts" and turned out to be the state-4 governor substitution ([[reference-accord-state4-governor-ratchet]]). The vibration was assigned "upstream of the gain" and a fixed 102-count deadband was found immediately before the gain multiply ([[reference-accord-pregain-deadband-c61b8]]).

**How to apply:** before proposing any fix for a gain-raised build, ask *which side of the gain is this stage on, and is the symptom inside or outside stock's reachable range?* If a candidate is downstream and the symptom is inside stock's range, drop it without tracing. ⚠ **Check the compensation is actually complete first** — a rescaled PID restores loop *gain* but not command *slew rate*, which is a real hole ([[openpilot-steer-delta-not-rescaled-for-gain]]). Implemented as `gain_rescaling_invariance_analysis()` in `analysis-2020accord/model/eps_lkas_chain_model.py`.
