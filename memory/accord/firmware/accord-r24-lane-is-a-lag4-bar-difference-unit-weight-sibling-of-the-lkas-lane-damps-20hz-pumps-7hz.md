---
name: accord-r24-lane-is-a-lag4-bar-difference-unit-weight-sibling-of-the-lkas-lane-damps-20hz-pumps-7hz
description: "🛑🛑⭐⭐⭐⭐⭐ TRACED 2026-09-13: r24 = −clip(deadband(trunc(clip(0.5·(bar[n]−bar[n−4]), ±5120)·[0xC6446]/1024), ±[0xC61F6]=3), ±8192), 1 kHz, from the torsion-bar torque gp-0x4f60 (gp-0x6ada is a write-only output mirror); it enters the aggregator gp-0x6b94 with UNIT weight beside the LKAS lane (gp-0x6b4c) and shares one path to the motor ⇒ r24 : LKAS = 1 : 1. On the wire (B(f) = bar/rate, r39+r6c) it is a pure PUMP at 3–7 Hz (∠+170…−178°) and a near-pure DAMPER at 18–22 Hz (∠+9…+15°), supplying 73–86 % of the electronic 20 Hz damping; the effective arm reads ≈2353 = 0.45× the cal (κ dispute 0.45–1.45 open); the gp-0x671d fault latch that would collapse it ×0.195 is UNARMED (its 5530 SET threshold never reached on 4,653 s)."
metadata:
  node_type: memory
  type: project
---

Agents `r24lane`, its tracer and `bof`, 2026-09-13. Files: `rlog-tools/studies/grind/B-OF-F-V282-2026-09-13.md`,
`b_of_f_v282.py`, `r24_lane_transfer.py`; the tracer's store file
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict.md`.

**The lane, from the bytes [EVIDENCE, GhidraMCP decompile + LE cal reads]:** producer FUN_0007e74a — an 8-deep
ring of the bar torque with a measured sensor-tick time base, `u = 2·(x[n]−x[n−N])/dt`, N = [0xC6C42] = 4
(guard N ≥ 8 → 0) → gp-0x4f62 (+ lockstep twin gp-0x4488). Consumer FUN_0003aa2c @0x3AA9C: clip ±5120 →
gain select FIRST MATCH: gp-0x671d ≠ 0 → [0xC6442] = 1024 · STEER_CONTROL_ACTIVE (byte 0x3AA96 = fb since
V104) → **[0xC6446] = 5244 engaged (stock 512)** · gp-0x671a ≥ 5 → [0xC6440] = 2048 · else a speed LERP;
`mul` + `sar 0xa` (Q10, 5244 = ×5.121) → symmetric deadband [0xC61F6] = 3 (post-gain; a Coulomb-friction
tax, disqualified as a lever by the operator's no-added-friction rule) → × polarity gp-0x6752 (±1) →
clip ±0x2000 → `add r24,r6` into the plain unit-coefficient sum → gp-0x6b94 (clamp ±0x2800, twin gp-0x4ce0)
→ governor FUN_0004503c → gp-0x6ace → comp FUN_000456a4 → gp-0x6acc → shaper FUN_00042af8 → gp-0x6b08 →
**gp-0x6b98 the FOC command**. A kill switch gp-0x67ac == 1 drops r24/r26 from the sum. **No filter of its
own exists on r24** — shaping it by frequency needs a cave (hook candidates 0x3AC18 `mul r10,r8,r0`,
0x3AC3E; 6–8 dead scratch registers; free flash 0xC5788–0xC5FF0 2,152 B).

**Its transfer on the wire [EVIDENCE, `bof`]:** B = bar/rate pooled over r39 + r6c (4,016 s engaged;
positive control reproduces the record's +114° / coh 0.94 at 20.3 Hz to 1°). R_r24 = −(g/1024)·D4·B with
D4 = 0.5·(1 − e^{−j2πf·0.004}). Per raw count of x = −rate, aggregator counts: 7.3 Hz **4.3∠+170°** (pump),
10 Hz 10.4∠+112°, 20.3 Hz **3.25∠+9…+15°** (damping; the servo's own arm is 1.74∠−72.6°). Damping share is
plant-free because both lanes act through one aggregator: Re(R_r24)/Re(R_servo) at 20.3 Hz = 6.0 (κ 1) or
2.7 (κ 0.45) ⇒ **r24 supplies 73–86 % of the electronic damping at the ring.** The cave's bit-4 phase confirms
the model on the wire (+1° measured vs +5° predicted at 20.3 Hz creep; +176° vs +174° at 7.3 Hz loaded).
🛑 **10–14 Hz is NOT identified in any stratum (coh 0.28–0.50)** — exactly where the bar-to-rate phase
transitions through a ~9.3 Hz mode (ζ 0.14 loaded / 0.20 creep) — and the highway stratum is unusable at
20.3 Hz (coh 0.39).

**The 7.3 Hz gate is monotone in the r24 gain:** gate73(k) = 1.003 (k 1.0) → 0.787 (0.75) → 0.596 (0.50)
→ 0.520 (0.39, Honda's own 2048 arm) → 0.415 (0.10). Every cut improves the strong-turn ring; the cost is
the 20 Hz damping the same lane supplies (the memory
[[accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways]] stands;
`grind_loop_shape.py` §G's "5244→512 improves both bands" is the one that is wrong).

**Three corrections of record:** (1) the bar-to-rate phase swing is DOWNWARD ~130–150° through the ~9.4 Hz
mode, not upward 210°; (2) the record's creep-vs-loaded 7 Hz difference was a SELECTION artefact of gating on
instantaneous |bar| < 400 (a 1 s median gate moves ∠B(7.3) by 19° and lifts coherence 0.63 → 0.88);
(3) the gp-0x671d / 1024 arm is NOT live on V282 (b6 duty 2.0–2.4× the 1024 prediction; no persistent
step-down over 4,016 s at a ×0.94 floor; no lane quantity ever reaches the 5530 SET threshold) — but it is a
first-strike Schmitt latch (SET |x| ≥ [0xC61FA] = 5530, RELEASE < [0xC61F8] = 1024, saturating counter,
cleared only by FUN_0003bcb2) that on every V280+ image would collapse r24 5244 → 1024 (×0.195) for the
rest of the drive; on stock it doubles it. Its monitored quantity gp-0x6ad8 is write-only — an inert tap
would settle its input.

**The open dispute:** the cave's |r24| ≥ |T| comparator inverts to an effective arm 2268–2747 (median 2353,
κ 0.45), replicating the record's s = 0.37–0.52; the record's 7.3 Hz split LS73/LR73 implies κ ≈ 1.45. The
on-car argument favours 0.45 (at κ 0.45 the net 7.3 Hz damping on V282 is ≈ neutral, matching V281r3's
measured cycle-gone; at κ 1 it should have survived). A refit of the plant grid with r24 explicitly in the
loop fits BOTH the V282 and V289 poles in 0 cases at either sign/κ (173 without r24) — either B carries a
road/driver input that is not motor-driven (no command-IV estimator was run) or the existing family's G
silently absorbed r24. **Unresolved; the 10–14 Hz identification gap is the named next measurement.**

Related: [[accord-fb-pole-down-class-does-everything-but-fails-the-7hz-gate-r24-arm-is-the-blocker]] ·
[[accord-v291-c10-built-fb-pole-10hz-plus-r24-cut-loop-opening-class]] ·
[[accord-gp6b4c-carries-the-lkas-lane-gp6ad4-is-a-driver-torque-pid-and-0x2a30e-0x2b421-is-a-dead-twin-island]]
