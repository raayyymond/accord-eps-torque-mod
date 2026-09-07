# Firmware Codepath Tracer — Memory Index

## 2026-09-06 - the addend at 0x2A1FC in FUN_00028ea6, for `shape`/`main`
- 🛑🛑★★★★★ [r11 at 0x2A1FC is (short)[gp-0x6b2c] on all 11 paths, and that cell is IDENTICALLY ZERO (Y table 0xC673E-44 all zeros + the r29>=32001 gate forces the above-range branch) - so gp-0x6b38 = clamp(-K6*r9>>15), NO bar-torque feedthrough, x6 multiplies only the PID](reference_accord_gp6b2c_addend_is_identically_zero.md)
- 🛑★★★★★ [0x2B422/0x2B57A are LIVE (jarl from 0x22530/0x22572) but undefined in Ghidra; 11 more gp-0x6b2c touches hide there - plus the CORRECTED Format-V jr/jarl mask (0x07FF, not 0x07C0, which also matches prepare)](reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers.md)


## 2026-09-05 — amplitude-nonlinearity / small-command shortfall brief, for `team-lead`
- 🛑🛑★★★★★ [Ki=0 (0xC63E6, byte-verified V282) makes the LKAS rate PID a friction-limited PD loop; the 0xC9A88 map is CONFIRMED LINEAR (Y/X=4.30, selector 7) so the loop itself is the amplitude-nonlinearity source, independently confirmed by the flown V283 Ki-A/B test](reference_accord_ki0_pd_loop_explains_amplitude_gain_curve.md)

## 2026-09-04 — V285/V286 telemetry costing (dE sign-change + r24 magnitude rungs), for `team-lead`
- 🛑🛑★★★★★ [FUN_00028ea6 publishes S/P/D/output to gp-0x6b2e/32/34/36, orphan-safe like the lag pole — but raw dE is register-only, never published; D's clamp hides magnitude exactly where a Kd sweep needs it](reference_accord_fun28ea6_publishes_p_d_sum_output_orphan_safe.md)
- 🛑🛑★★★★★ [lp is reused as scratch in FUN_00028ea6, CONFIRMED live 0x29A2C→0x2A29A (spans the dE tap point) — jarl there corrupts a live gate check; 0x29EE4 is a same-length jr swap site, r10 dead there, 168+ free flash bytes at 0xC4BD8, gp-0x683c has zero references at all](reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site.md)
- 🛑★★★★★ [CAN 427's opendbc def matches the firmware's own byte writer census bit-for-bit; gp-0x13CC b2/5/6 + gp-0x13CA b7 are DBC-undefined AND firmware-unwritten (top-tier spare) — but b3/b4 are DBC-undefined YET written, proof undefined≠unwritten](reference_accord_can427_dbc_confirms_4_spare_bits_and_undefined_neq_unwritten.md)
- 🛑★★★★ [search_instructions operand-text hit on a displacement can land on a different physical byte when a function uses its own non-gp base register (movhi) — check the base register, not just the displacement](reference_accord_operand_text_search_false_positive_wrong_base_register.md)

## 2026-09-03 — GATE-1 census of the LKAS rate-PID pole cells (V282), for `loopshape`
- 🛑🛑★★★★★ [Feedback-EMA poles are PRIVATE; output-lag poles 0xC63EC/EE are shared-in-code but PRIVATE-IN-EFFECT (GATE 1 now PASSES outright, see the 2026-09-06 entry) — 2nd reader at 0x2A892/2A8A2 is inside a duplicate compiled orphan with NO entry path (halfword 0xA892 occurs nowhere); Kd slot 7 is FLAT so its knot index can't move Kd at all](reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader.md)
- 🛑★★★★★ [Grep memory for the address BEFORE calling a function dead — a passing scanner control proves the scanner, not the claim (0x2A5xx retraction: FUN_0002a30e next door is LIVE)](feedback_check_kit_memory_before_calling_a_function_dead.md)

## 2026-09-03 — r24 dt/Q-format/gain-arm census, V283, for `team-lead`
- 🛑🛑★★★★★ [gp-0x4f62's Δt is a DMA torque-sensor rolling-counter tick (SVD-confirmed), not CPU-ms; Q-format chain re-verified bug-free on V283; gp-0x683c CONFIRMED dead by direct V283 byte read](reference_accord_gp4f62_dt_is_dma_sensor_tick_not_cpu_ms.md)

## 2026-09-01 — V276 reference back-off costing + telemetry design, for `team-lead`
- 🛑🛑★★★★★ [Crossover threshold tabulated in raw counts K=1..6; K=2 clears the crossover at zero peak-torque cost; the CAN-427 packer RECTIFIES so it cannot carry sign(E) without a restructure](reference_accord_v276_crossover_threshold_and_packer_rectifies_sign.md)

## 2026-09-01 — V276 2-4Hz oscillation census, for `team-lead`
- 🛑🛑★★★★★ [0xC61BE (post-gain sum clamp), not D's own 0xC61B6, starves D — and is the secret binding constraint on peak torque (2505 vs 3072 nominal), with a sign-extension defect on its positive branch](reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation.md)

## 2026-09-01 — V274 telemetry design, for `main`
- ⚠🛑🛑★★★★★ STALE LINK — the file `reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells` this entry pointed to does not exist on disk (confirmed 2026-09-04). The underlying claim (PID publishes internals to unread gp cells) is INDEPENDENTLY RE-CONFIRMED for 4 cells this session — see 2026-09-04 entry above, `reference_accord_fun28ea6_publishes_p_d_sum_output_orphan_safe.md`. Treat that file as the source now, not this line.
- 🛑🛑★★★★★ [Variant record table at 0xCD012 dumped whole (16 rows, 9 numeric classes); gp-0x674d=0 everywhere; V273's docstring pairs 1-based names with 0-based values, so "5 vs 35" may really be "0 vs 30"](reference_accord_variant_record_table_0xcd012_full_dump.md)

## 2026-08-31 — `FUN_00028ea6` control block 0x29D6C–0x2A190, for the orchestrator
- 🛑🛑★★★★★ [It's a PID on steering-rate error: setpoint = CAN-0xE4 mapped through a variant table, feedback = lag of gp-0x6a56; Ki is zero on stock/V112 so the integrator is inert; FUN_0002a93a is a dead twin](reference_accord_fun28ea6_lkas_rate_pid_full_decode.md)
- 🛑🛑★★★★★ [UPDATED 2026-09-01: driver override is TWO mechanisms (Y taper + a debounce writing gp-0x6807=4); on V112/V268 base all 8 cals are 255/0xFFFF so both are unsatisfiable; 6-byte extended gp-relative encoding decoded](reference_accord_fun28ea6_lkas_rate_pid_full_decode.md)

## 2026-08-27 — `blanked` task, for `team-lead` (V36-blanked cells 0xC61C0/C2/C4)
- 🛑🛑★★★★★ [V36 debounce SM re-verified fresh: 12 exact reader addresses, byte-confirmed 0xFFFF through V110, NOT the ratchet/grind cause (level-debounce, different path than gp-0x6b26)](reference_accord_v36_gentle_eme_debounce_full_mechanism.md)
- 🛑🛑★★★★★ [CORRECTS "STEER_STATUS=4 is report-only": a tail-appended state dispatcher (Ghidra mis-bounds the function at a mid-function dispose) gates whether gp-0x69b0 can advance — a real gating effect](reference_accord_gp6807_gates_gp69b0_engagement_ramp.md)

## 2026-08-31 — openpilot 0x0E4 command path
- 🛑🛑★★★★★ [gp-0x69ae (openpilot STEER_TORQUE) has exactly 3 readers, both GATES not summands; motor torque is generated internally, scaled by the gp-0x69b0 ramp at 0x2a1e6](reference-accord-op-0e4-steer-command-full-path.md)

## 2026-09-01 — CAN 427 telemetry-tap packer, for `main` (V277 design)
- 🛑🛑★★★★★ [427 tap field is 10 bits (byte1 + byte0[1:0]); ld.h cannot address an odd gp displacement so gp-0x674B needs ld.bu; gp-0x674B has 2 writers, 0 readers, a free publish cell](reference_accord_can427_packer_tap_field_full_decode.md)
- 🛑🛑★★★★★ [All 7 EPS outbound frames censused; FUN_000561b0/0x660 writing 7 bytes to zero is a TRAP (gateway-filtered, already tried); only 0x14A/0x18F/0x1AB cross, ~20 bytes dead slack in the 427 chain — SUPERSEDED for 0x1AB specifically by the 2026-09-04 DBC cross-check above, which found 4 clean bits there](reference_accord_eps_outbound_frame_census_and_free_bits.md)

## 2026-09-01 — V277 adversarial pass (interlocks & consumers)
- 🛑🛑★★★★★ [gp-0x674E <= 9 in every coded variant — bank slots 10-27 are dead calibration, resolves "record 2 vs 11" as neither](reference-accord-variant-selector-max-is-nine.md)
- 🛑★★★★★ [ld.hu is opcode 0x3E/0x3F not 0x3C/0x3D — a ld.bu-only scanner gives false zeros on halfword cals; full load/store+jarl+mov-imm32 decoder table](reference-accord-v850-load-opcode-map-ldhu-0x3e.md)
- 🛑★★★★★ [Ghidra's in_r10 in FUN_00049a90/78/5a is a cmov artefact, not a real param; FUN_00055d80 saves r6/r7/r8 but never restores — dead scratch, free to clobber](reference-accord-clamp-helpers-and-packer-scratch.md)
- ★★★★ [Importing a built image: auto-analysis finds ZERO functions, create_function required, body_size doubles as desync check; never save_all_programs on shared state](reference-accord-importing-a-built-image-into-ghidra.md)

## 2026-09-03 — V280 engaged-only 20Hz loop census, for `team-lead`
- 🛑🛑★★★★★ [Honda's 55Hz biquad IS live and engaged-only on V280; r24 confirmed the top structural candidate for the 18-22Hz creep grind — unfiltered differencer, gain rises ~linearly with f into the 1kHz sum; 0xC40DC is NOT virgin (V109's lever)](reference_accord_v280_engaged_gates_census_biquad_confirmed_live.md)

## 2026-09-03 — r24 "Lever B" reconciliation, for `team-lead`
- 🛑🛑★★★★★ [Reconciles "Lever B unreachable" with "V280's r24 gain is live": both true — V104-V280 repointed the SAME ld.bu from gp-0x683c to gp-0x6806, nothing was armed, the gate's SOURCE was swapped. Converting r24's gain to deg/s needs an unrecorded torsion-bar constant](reference_accord_r24_gate_repoint_reconciles_lever_b_dead_vs_v280_live.md)

## 2026-09-06 — lag/fb pole hostile census for the next build (V282), for `team-lead`
- 🛑🛑★★★★★ [BOTH PID filters are a one-pole IIR on an INCREMENT whose output is the TWO-SAMPLE SUM with `a` ADDED; the lag has >>5 (DC 0.990) but the feedback EMA has NO >>5 (DC 30.89, so the `/32` is wrong for it); no overflow on any candidate (>=8.9x); and FUN_000428d4 is a LIVE >10 Hz HIGH-PASS reversal detector with a 40% assist cut](reference_accord_lkas_pid_filter_form_two_sample_sum_and_oscillation_detector.md)

## 2026-09-06 - GATE 1 reachability proof for the lag poles (V282), for `team-lead`
- 🛑🛑★★★★★ [GATE 1 PASSES for 0xC63EC/EE: 0x2A504 is `dispose ..., lp`, a RETURN, so FUN_0002a30e never falls into the duplicate block; zero real branches enter it, no immediate can build 0x2A508/0x2A890 - the earlier census's residual caveat is CLOSED](reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return.md)
- 🛑★★★★★ [V850 `prepare` COLLIDES with jr/jarl on the Format-V opcode test, inventing false branch targets out of every function prologue - filter on TARGET PARITY; controls passing does NOT protect against an over-match](reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans.md)
