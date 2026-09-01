# Firmware Codepath Tracer — Memory Index

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
