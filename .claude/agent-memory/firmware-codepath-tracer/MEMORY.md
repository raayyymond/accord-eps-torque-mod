# Firmware Codepath Tracer — Memory Index

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
