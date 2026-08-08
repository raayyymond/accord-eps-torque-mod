---
name: v56-flashed-mute-null-and-costs-damping
description: "V56 FLASHED 2026-07-29 (route 24, first ROAD drive with a probe) — the 0xC6AF0 mute bought NOTHING for the 20-25 Hz mode ⇒ revert to V55; gp-0x6ad4/FUN_0003a382 eliminated as its driver, all three branches at once. The few-Hz resonance turned out to be WHEEL ORDER 1 (tyre imbalance, 2.088 m circumference), not a firmware effect."
metadata: 
  node_type: memory
  type: project
  originSessionId: 596df10f-7827-4cf9-8d92-4190a417047f
  modified: 2026-07-29T06:45:20.111Z
---

**V56 = V55 + `0xC6AFC`/`0xC6AFE` 32768→0** (mutes the whole `FUN_0003a382` → `gp-0x6ad4` residual lane
via its output bound, so it is branch-agnostic where V43/V46/V48A each killed one branch).

**Result — pre-registered outcome (iii): nothing moved.** Speed-matched creep (vEgo ≤1.6 m/s),
engaged + hands-off, full 16-bit CAN `0x18F`: P[15-26 Hz] engaged **1.28e8** vs disengaged **1.63e5** =
**786×**, against V55's recorded 877×. The command's 21 Hz did not drop either (probe field P[15-26] 182
vs V55's 22 at matched creep; transition rate 23.9/s vs 21.9/s).
⇒ 🛑 **`gp-0x6ad4` / `FUN_0003a382` is ELIMINATED as the driver of the 20-25 Hz mode.** Do not re-propose
the lane. Independent replication: 1,878× on torque / 5,524× on rate at 0.5-3.0 m/s.

**★★ The few-Hz resonance the operator felt is WHEEL ORDER 1, not V56's doing.** Found on the independent
`STEER_ANGLE_RATE` channel (`0x18F` bytes[2:4] BE signed × **−0.1** deg/s — the 10× finer copy of what
openpilot reads at `0x14A[2:4]`): `f = 0.4890·v − 0.186 Hz`, **r = +0.9970**, residual 0.037 Hz,
**intercept ≈ 0 (through the origin)**, implied rolling circumference **2.088 m** against 2.05-2.11 m for a
235/45R18 Accord ⇒ **one line per wheel revolution = tyre/wheel imbalance, non-uniformity or runout.**
Firmware-independent; invisible on prior routes because at 1.5 m/s wheel order 1 is 0.7 Hz.
⇒ **Get a wheel balance / road-force check.** Burst-like: worst window Q=55, 1608× the local floor.

★ **A separate FIXED ~7-8 Hz resonance exists on EVERY build** (V56 7.81, V55 7.03, V54 8.59, V53 7.03,
R13 7.42 Hz at creep, where wheel order is only 0.3-0.8 Hz). **At 15-20 m/s the wheel-order line sweeps UP
THROUGH it** — the recipe for an intermittent low-frequency shake that only appears on the road.

⚠ **"V56 removed damping" is NOT supported by the data, but is NOT closable.** Matched creep, 1-10 Hz band
variance: V56 9.75e3 vs V55 5.70e4 (**0.17×**), V53 0.10×, R13 0.24×, V54 1.32×; envelope-decay Q V56 3.6
vs V55 7.4, V53 14.1, R13 3.5 — V56 is not the least damped. 🛑 **But all of that is CREEP data and the
operator felt it at ROAD speed, where no prior build has any data.** Do not use it to dismiss the report.

⚠ **Control gaps:** V56 has **zero disengaged windows above 3 m/s**, and **no pre-V56 road baseline
exists** (route 13 has only segs 12-15 on disk, creep, vEgo max 2.73 m/s).

🛑 **Stop calling the mode "21 Hz":** `f = 0.177·v + 20.48` (r=+0.650), **24.61 Hz at 19-21 m/s, 25.00 at
21.3**, Q = 160-228 in the worst events. And **steering angle shifts it ~2 Hz within one firmware**
(0-2° → 23.44 Hz, 5-20° → 21.48 Hz), which **confounds every cross-route frequency comparison** — V56's
creep is near-straight (0.5°) while all prior builds' creep is wheel-turned (V55 26.9°, V53 42.2°).

**Why:** revert to V55 (SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf`) — already
built, driven, fault-free, keeps the probe. 🛑 A 50% partial restore (`Y=16384`) is **not** a candidate:
the lane at 0% and 100% already agree, so intermediate authority is bounded between two agreeing
measurements.

**How to apply:** the mode enters `gp-0x6b98` through one of the **other eight** additive aggregator
lanes — all confirmed plain-`add` at `FUN_0003aa2c`: `gp-0x6b62`, `-0x6b4c`, `-0x6ade`, `-0x6b26`
(friction), `-0x6bbe` (boost), `-0x6bd0` (damping), `-0x6b86`, plus `FUN_00036682`'s return. Rank by
attenuation at 21 Hz. On the next drive after reverting, confirm the 8.69 Hz line disappears — that is
also the best available proof the mute was genuinely live. See [[v54-flashed-authority-measured]] and
[[accord-probe-underranges-to-one-bit-comparator]].
