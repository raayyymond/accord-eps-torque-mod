---
name: accord-v298-angle-loop-built-not-flown-four-lenses-pass-with-defects
description: "V298 BUILT 2026-10-01, NOT FLOWN: the first firmware ANGLE loop (C3-rev2-P: E = 16(theta_sp - theta) on the held EPS angle, G(v) speed cave 260 B at 0xC4C00 with 0 RAM, Ki 40 / ICL 8192 / A3 integral bound + opposing-hand freeze, fresh-rate D Kd 48 guarded, Kp 112 flat, op-skip to Honda's epilogue on an invalid rate, guards A2/B2, camera interlock gp-0x6803 == 2 with the dir-2 fade record matched to stock, version string A16A); image sha 177abf04..., rwd 1a69b927...; 325 B vs V295; CRC 50/50; H1 0/40000 on the FLIGHT bytes; four adversarial lenses PASS_WITH_DEFECTS, no flash-blocker; revert = re-headered V295/V294 rwd (A16A listed). V296/V297 not built. Flight prerequisites: camera byte-2 field re-measured on bus 2 + camera LKAS off; pol = -1 re-proved; fork sends bits 3:2 = 2 every frame, accepts fwVersion A16A, no angle integral. Declared misses: low-speed stick-slip < 8 m/s, ms_free ring (R3*), outward-hand lurch, 11-12.5 m/s dip."
metadata:
  type: reference
---

Design `docs/specs/design/DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md`; build `analysis-2020accord/builds/v108_plus/build_v298_tva.py`
(docstring = the full cell table); adversarial reports `analysis-2020accord/studies/angle_loop/v298/adversarial/`; drive card
`docs/scoring/DRIVE-CARD-V296-angle-loop-2026-10-01.md`; reader `rlog-tools/studies/angle_loop/angle_loop_drive_read.py`.
**Process record:** the design came from two judge-panel rounds (operator ruling: never one agent -> one solution); roughly a
third of the agents across the rounds were interrupted by an automated safety classifier and several declined to continue;
the orchestrator's own page write was also stopped. The close-out page and the PART6/handoff entries are the open gaps.
Related: [[project-the-goal-2026-09-30-angle-loop-cave-tight-smooth-silent]], [[feedback-v298-camera-interlock-is-the-candidate-no-fork-angle-integral-for-drive-1]].
