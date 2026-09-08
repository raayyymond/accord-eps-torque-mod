---
name: accord-golden-model-lacks-the-lkas-rate-pid-stage-contract-is-88-symbols
description: "The golden model does NOT contain the LKAS rate PID stage at all (no E = 32·sp − fb, no Kp/Kd banks 0xCB994/0xCB7D4, no 0xC61B6 D clamp; the 10240 in SECTION 6B is a different PID). `steer_torque_arbitration` = FUN_00028ea6 stops before the error former. V288's `lkas_setpoint_prefilter` (SECTION 5B) is an exact standalone mirror with no caller yet. Contract since 2026-09-07: 88 symbols, hash 740f4bcd… unchanged."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4fb8c05d-08ba-46ea-96e0-19a3b1899a03
  modified: 2026-09-08T05:31:35.182Z
---

# Golden model gap: the LKAS rate PID stage is missing; the contract is now 88 symbols (2026-09-07)

- Added: `Calibration.spfilt_k` (None = V282 and earlier, 4 = V288), `EpsState.sp_filter_y` (gp-0x6a32),
  `EpsState.pid_prev_err_cell` (gp-0x6cf8, defaults to the 0x7FFFFFFF sentinel), `lkas_setpoint_prefilter(sp, st, cal)`,
  `_self_check_v288()` (asserts only, called from `_self_check()`). `_golden_contract_syms.json` lists 88 names.
  Stdout hash and 2,512-byte length unchanged. Equivalence vs the build script's arithmetic: 705,894 cases, 0 mismatches.
- Gap: the whole rate PID (error former, P/I/D on E, clamps, the Kp/Kd banks indexed by the raw command) must be added before
  the prefilter has a caller. That is the next model task, ahead of the governor 7-slot MIN-fold and the oscillation detector
  (still exogenous / absent).

**How to apply:** do not cite the golden model as evidence for anything about the rate PID's arithmetic; use the 2026-09-06
trace, ADV-V288-B and build_v288_tva.py's mirror. CLAUDE.md's contract line must say "exactly 88 symbols".
