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

---

## 🛑 UPGRADE 2026-09-09 — `gp-0x6803` selector is now EVIDENCE on BOTH halves, not half-believed

Independently re-confirmed and closed: `gp-0x6803 = (byte2 << 0x1c) >> 0x1e` = **0xE4 byte 2, bits 3:2**,
which the STARPILOT-FORK DBC (`honda_accord_2017_can_ext_generated.dbc`) names `SET_ME_X00` (`22|7@0+`,
byte 2 bits 6:0). `create_steering_control` in `opendbc/car/honda/hondacan.py` on the operator's fork packs
**only** `STEER_TORQUE` and `STEER_TORQUE_REQUEST` into that frame — `SET_ME_X00` is never set, so it is
packed as **0** on every frame openpilot sends. `gp-0x6803` (bits 3:2 of that field) is therefore **0 on
every frame**, and the cliff taper arms `0xCBA04`/`0xCBA74` (selected only on `gp-0x6803 == 2`) are
**UNREACHABLE under openpilot** — now EVIDENCE on both the firmware side (the bit-field derivation) and
the fork side (the packer), not memory carried forward as belief. Source:
`docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md` §"This also CLOSES `reqaxis`'s open question §7.5".
See [[accord-kp-kd-schedule-x-axis-is-demand-index-16-125736-per-lsb]] (same trace, the demand-index axis
these taper arms feed into).
