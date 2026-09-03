---
name: accord-the-override-taper-arm-is-selected-by-a-0xe4-field-openpilot-sends-0-the-live-post-pid-fade-is-0xcbbc4
description: 2026-09-03 (twistloop, rlog-tools/studies/osc-highangle/TWIST-TAPER-LOOP-2026-09-03.md; wire crux verified by the orchestrator). The driver-torque arm selector gp-0x6803 is NOT an ECU mode -- FUN_00052676 @0x526ac stores 0xE4 byte2 bits 3:2 into it; openpilot sends byte2 & 0x7F == 0 on 100 % of frames (11972/11972 on r34 seg 5), the stock camera sends 1. So the "cliff at 2240-2560 raw" taper (0xCBA74) and the "inert second gate" the kit modelled are NEVER selected under openpilot. LIVE: setpoint-stage taper 0xCB924/0xCB8B4 (slot 7 @0xE52FC/0xE5284) flat 255 to 2560 raw, linear to 0 at 3584; post-PID multiplier 0xCBC34 (grab byte gp-0x6830) x 0xCBBC4 (|tq|>>5; slot 7 record 0xE564C: X 16,26,38,48,64,96 / Y 255,243,218,179,77,77 = fades from 512 raw, floor 0.30 at 2048), applied at 0x2a0c2 to (P+D) BEFORE the lag and the x6 gain. With the live arms the chain mirror matches the tap at corr 0.955 (was 0.888) and slope 0.86-0.90 -- the "~0.5 post-sum multiplier" every earlier mirror saw IS this fade. In the 7 Hz strong-turn episodes the fade carries only 0.10 of |T|; do NOT flatten it (x2.9 push against a hand at 1216-2560 raw).
metadata:
  type: reference
---

# The override-taper arm is a 0xE4 field (openpilot sends 0); the live post-PID fade is 0xCBBC4 -- 2026-09-03

Corrections of record (reports, to be applied): `accord-override-taper-is-a-cliff-not-a-taper` describes the UNSELECTED arm (the live cliff is 2560 -> 3584 raw);
`reference-accord-second-driver-torque-gate-cbae4-cbbc4` ("inert") read the wrong arm -- 0xCBBC4 is live; every mirror assuming post m = 254 over-predicts |T| by ~1/0.7
wherever a hand is on the wheel; the "cliff duty 2-11 %" columns in the high-angle tables were computed on the 2240 knee -- live taper duty in those episodes ~0.
Related: [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]], [[accord-grind-happens-hands-off-the-bar-signal-is-twist-and-the-engaged-rate-lane-gate-is-live]].
