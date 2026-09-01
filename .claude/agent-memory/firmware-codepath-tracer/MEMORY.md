# Firmware Codepath Tracer — Memory Index

## 2026-09-01 — V276 reference back-off costing + telemetry design, for `team-lead`
🛑🛑★★★★★ **Crossover threshold (E<0 requires feedback_lag_out > 32*setpoint) tabulated in RAW COUNTS
across K=1..6, resolving a team discrepancy about absolute deg/s (both were right, different points in
the same unclosed unit chain). K=2 recommended (threshold 11008, required `0xC62E6`=15360) — clears the
BELIEF median-achieved-rate crossover with zero peak-torque cost. Also: the CAN-427 packer RECTIFIES
(calls abs()) so it CANNOT carry sign(E) without a real restructure, not just an edit-site change.**:
[[reference_accord_v276_crossover_threshold_and_packer_rectifies_sign]]

## 2026-09-01 — V276 2-4Hz oscillation census, for `team-lead`
🛑🛑★★★★★ **`0xC61BE` (post-gain PID-sum clamp, 15360) — not D's own clamp `0xC61B6` — is what starves
the D term: P alone already fills it at low driver-override index, so D is discarded whenever it
matters. Also `0xC61BE` (not `0xC61B4`) is the SECRET binding constraint on peak torque today (2505
actual vs 3072 nominal), and it has a sign-extension defect on its POSITIVE branch (`ld.h` @0x2a146,
must stay <32768). Single-cell V278 fix identified that restores D's authority AND closes the 18%
torque shortfall with zero authority given back.**: [[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]]

## 2026-09-01 — V274 telemetry design, for `main`
🛑🛑★★★★★ **The rate PID ALREADY publishes 9 of its internals to gp cells nothing reads — so every
clamp flag is FREE (exact equality to the cal) and any term reaches CAN 427 in a 3-BYTE edit.
CORRECTS STATE.md twice: `0xC61B2` is NOT a clamp in this loop (it lives in `FUN_0002b422`), and the
`ld.h` sign-extension defect exists on `0xC61B4`/`0xC61B2` too, not only `0xC61BE`.**:
[[reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells]]
🛑🛑★★★★★ **Variant record table at 0xCD012 dumped whole (16 rows, only 9 distinct numeric classes).
`gp-0x674d`=0 everywhere so V273's `ld.h` premise HOLDS — but V273's docstring pairs record NAMES
(1-based) with record VALUES (0-based), so its "wire 5 vs 35" may really be "0 vs 30", and 0 reads
exactly like a dead channel. One-byte fix at 0x55E0E.**:
[[reference_accord_variant_record_table_0xcd012_full_dump]]

## 2026-08-31 — `FUN_00028ea6` control block 0x29D6C–0x2A190, for the orchestrator
🛑🛑★★★★★ **It is a PID on STEERING-RATE ERROR: setpoint = CAN-0xE4 LKAS torque command mapped through a
variant table; feedback = first-order lag of `gp-0x6a56` (column angular rate). Ki (`0xC63E6`) is ZERO on
stock AND V112, so the integrator is inert. `gp-0x674e` is a STATIC variant/table-set index (28-entry
pointer-array bank); `gp-0x682f` = `|gp-0x4f60|>>5`, the driver-torque override index. `FUN_0002a93a`
is a dead twin of the same block (positive-controlled jarl scan).**:
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]]
🛑🛑★★★★★ **UPDATED 2026-09-01 — the driver override is TWO mechanisms: the Y taper AND a `0xC64B4`-`B7`
+ `0xC61C0/C2/C4` debounce writing `gp-0x6807 = 4`. On STOCK the debounce binds FIRST (raw 1728, below
the taper knees); on a V112/V268 base ALL EIGHT cals are 255/0xFFFF so BOTH are unsatisfiable. Taper X is
a zero-extended byte, ceiling 255, 1 count = 32 raw counts. `0xC6974` is 4-knot FLAT and inert
(correction). Also carries the decoded 6-byte extended-displacement gp-relative encoding.**:
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]]

## 2026-08-27 — `blanked` task, for `team-lead` (V36-blanked cells 0xC61C0/C2/C4)
🛑🛑★★★★★ **V36 debounce SM fully re-verified fresh (GhidraMCP, not r2): 12 exact reader addresses across
`FUN_00028ea6`+`FUN_0002a30e`, byte-confirmed 0xFFFF through V110, NOT the ratchet/grind cause** (level-
debounce, not periodic; different signal path than `gp-0x6b26`): [[reference_accord_v36_gentle_eme_debounce_full_mechanism]]
🛑🛑★★★★★ **CORRECTS "STEER_STATUS=4 is report-only" (2026-07-14 record): a state dispatcher tail-appended
to `FUN_0002a30e` (Ghidra mis-bounds the function at a mid-function `dispose`, invisible to
`get_function_by_address`/`search_instructions`) gates whether `gp-0x69b0` (BELIEF: the LKAS engagement-ramp
Q15 multiplier, per other kit memory) can advance. STEER_STATUS ∉{0,1,2} blocks the increment — a real
gating effect, not just a report.** Also a concrete reproduction of the search_instructions
function-unbound-code blind spot: [[reference_accord_gp6807_gates_gp69b0_engagement_ramp]]

## 2026-08-31 — openpilot 0x0E4 command path
🛑🛑★★★★★ **`gp-0x69ae` (the openpilot STEER_TORQUE) has EXACTLY 3 readers; both in-control uses are
GATES, not summands. The torque that reaches the motor is generated internally and scaled by the
`gp-0x69b0` engagement ramp at 0x2a1e6 — NOT at 0x2a194.**: [[reference-accord-op-0e4-steer-command-full-path]]

## 2026-09-01 — CAN 427 telemetry-tap packer, for `main` (V277 design)
🛑🛑★★★★★ **The 427 tap field is 10 BITS (ceiling 1023), not 8 — byte1 + byte0[1:0] of `0x1AB`. And
`ld.h` CANNOT address an ODD gp displacement (disp bit0 selects ld.h/ld.w), so `gp-0x674B` is
unreachable by the current load; it needs `ld.bu` (opcode 0x3C even / 0x3D odd, `hw2 = disp|1`).
`gp-0x674B` has 2 writers and ZERO readers — a free publish cell.**:
[[reference_accord_can427_packer_tap_field_full_decode]]
🛑🛑★★★★★ **ALL 7 EPS outbound frames censused. `FUN_000561b0`/0x660 writes SEVEN payload bytes to
literal zero — and is a TRAP: gateway-filtered, the kit already built AND flashed this exact repurpose
(TIER1, 2026-07-08) and saw nothing. Only 0x14A/0x18F/0x1AB cross, and NONE has a free contiguous byte
(~21 scattered bits). Way out: the 427 tap chain has ~20 bytes of dead slack for bit-packing two
signals.** Also: `or` opcode is 0x08 not 0x04, and `jarl` disp22 splits 6/16:
[[reference_accord_eps_outbound_frame_census_and_free_bits]]

## 2026-09-01 — V277 adversarial pass (interlocks & consumers)
🛑🛑★★★★★ **`gp-0x674E` is <= 9 in every coded variant (`FUN_00057f8e` loops `while (uVar2 < 0x10)`;
byte +8 of records 0..15 maxes at 9), so bank slots 10-27 are DEAD CALIBRATION and the
`(32,48,64,112)` taper shape is never used. Resolves the "record 2 vs record 11" open question:
neither.**: [[reference-accord-variant-selector-max-is-nine]]
🛑★★★★★ **`ld.hu` is opcode 0x3E/0x3F, NOT 0x3C/0x3D — a ld.bu-only disp16 scanner returns FALSE
ZEROS on halfword cal cells (cost me a bogus "0 readers" on `0xC62E6`, true answer 3). Full
load/store + jarl + `mov imm32` decoder table here.**:
[[reference-accord-v850-load-opcode-map-ldhu-0x3e]]
🛑★★★★★ **Ghidra's `in_r10` in `FUN_00049a90`/`49a78`/`49a5a` is a `cmov` ARTEFACT — cmov always
writes its dest, so the clamp helper needs no incoming r10. And `FUN_00055d80` saves r6/r7/r8 but
NEVER restores them: dead scratch, free to clobber in an in-place packer rewrite.**:
[[reference-accord-clamp-helpers-and-packer-scratch]]
★★★★ **Importing a built image: auto-analysis returns ZERO functions (raw binary, no entry points) —
`create_function` is required, and its `body_size` doubles as a desync check. And NEVER use
`save_all_programs` to work around a locked save: it commits every open shared program.**:
[[reference-accord-importing-a-built-image-into-ghidra]]
