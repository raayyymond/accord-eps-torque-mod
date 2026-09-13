# Firmware Codepath Tracer — Memory Index

One line per entry. Detail lives in the linked file; open it before relying on any claim here.

## The LKAS rate PID — `FUN_00028ea6`, body `0x28EA6–0x2A30D`

- 🛑🛑★★★★★ [Full decode: PID on steering-rate error, setpoint from CAN-0xE4 via a variant table, Ki ships ZERO; driver override is two mechanisms, both unsatisfiable on V112/V268](reference_accord_fun28ea6_lkas_rate_pid_full_decode.md)
- 🛑🛑★★★★★ [CORRECTS the record: at `0x29F18` r2 is the INTEGRATOR>>7, r9 is P, r8 is D; P = (E·Kp)>>8 clamp 0xC61BC; I deadband 0xC62E4 + I clamp 0xC61BA; taper is never unity (×254/256 ⇒ rail 2462)](reference_accord_lkas_pid_register_map_and_taper.md)
- 🛑🛑★★★★★ [TORQUE MODE = one halfword, `0xC62E6 := 0` (the clamp, not the gain); already built as V279 and NEVER FLOWN; steady-state surface unchanged, motion response increases](reference_accord_v279_is_the_built_never_flown_torque_mode.md)
- 🛑🛑★★★★★ [`0x2A0C6` is a second damper MODE, not "SKIP 3"; `gp-0x680a` has zero writers and boots 0 ⇒ unreachable. Plus the `.data` copy loop that makes every boot value EVIDENCE](reference_accord_0x2a0c6_is_a_damper_mode_and_data_boot_values.md)
- 🛑🛑★★★★★ [Ki=0 (0xC63E6) makes it a friction-limited PD loop; the 0xC9A88 map is LINEAR (Y/X 4.30, selector 7) so the loop is the amplitude-nonlinearity source](reference_accord_ki0_pd_loop_explains_amplitude_gain_curve.md)
- 🛑🛑★★★★★ [Publishes S/P/D/output to gp-0x6b2e/32/34/36, orphan-safe; raw dE is register-only, never published, and D's clamp hides magnitude where a Kd sweep needs it](reference_accord_fun28ea6_publishes_p_d_sum_output_orphan_safe.md)
- 🛑🛑★★★★★ [`lp` is reused as scratch, live 0x29A2C→0x2A29A; 0x29EE4 is a same-length `jr` swap site; 168+ free flash at 0xC4BD8; gp-0x683c has zero references](reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site.md)
- 🛑🛑★★★★★ [The r11 addend at 0x2A1FC is (short)[gp-0x6b2c] on all 11 paths and is IDENTICALLY ZERO — no bar-torque feedthrough; ×6 multiplies only the PID](reference_accord_gp6b2c_addend_is_identically_zero.md)
- 🛑🛑★★★★★ [`gp-0x6807` gates whether gp-0x69b0 can advance — corrects "STEER_STATUS=4 is report-only"; Ghidra mis-bounds the function at a mid-function dispose](reference_accord_gp6807_gates_gp69b0_engagement_ramp.md)
- 🛑★★★★★ [gp-0x6a34 publishes rectified |fb| into a gp-0x680a==1 lane via a third LERP; self-caught error — the knot-walk after rectification is keyed by speed, not this value](reference_accord_gp6a34_publishes_rectified_fb_to_a_gated_lane.md)

## The feedback lag filter — `0x28F4C–0x28FBE`, cells `0xC63E8`/`0xC63EA`

- 🛑🛑★★★★★ [Byte-exact: state gp-0x3d30 is 32-BIT, `a` is `ld.h` SIGNED (cap 32767), two SEPARATE `sar 0xa` floors; GATE 1 passes by Ghidra AND a controlled byte scan, empty set-difference](reference_accord_fb_lag_filter_bytes_and_gate1_private.md)
- 🛑🛑★★★★★ [Reset is the gp-0x3d2c SENTINEL, not the disengage route; the filter runs EVERY tick incl. disengaged so `s` is never stale; lowering `b` opens an asymmetric sar-floor dead zone](reference_accord_fb_filter_sentinel_reset_runs_disengaged_and_deadzone.md)
- 🛑🛑★★★★★ [The two floors give a CONSTANT −32-count DC offset at every amplitude (−20 on V282) = +32 counts of phantom error; scales as 1/(1024−a); fix = carry the residue, `t & 0x3FF`](reference_accord_fb_filter_floor_bias_is_32_counts_of_phantom_error.md)
- 🛑🛑★★★★★ [Both PID filters are a one-pole IIR on an INCREMENT whose output is the TWO-SAMPLE SUM; the lag has >>5 (DC 0.990), the feedback EMA does NOT (DC 30.89); FUN_000428d4 is a live >10 Hz reversal detector](reference_accord_lkas_pid_filter_form_two_sample_sum_and_oscillation_detector.md)
- 🛑🛑★★★★★ [GATE 1 for the output-lag poles 0xC63EC/EE: 0x2A504 is `dispose …,lp`, a RETURN, so the duplicate block is unreachable — the residual caveat is CLOSED](reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return.md)
- 🛑🛑★★★★★ [Pole-cell GATE-1 census: fb poles PRIVATE; output-lag poles private-in-effect; the 2nd reader at 0x2A892/2A8A2 is in a duplicate orphan; Kd slot 7 is FLAT](reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader.md)

## Hooks and caves on this path

- 🛑🛑★★★★★ [`0x28F8E` is the zero-new-liveness hook (V292's): writes {r7,r9,r13,r14} before reading, sits AFTER the ±12000 bail so a cave needs no clamp; 0xC4C00–0xC4FF0 is 1008 B of 0xFF on V291](reference_accord_0x28f8e_zero_liveness_hook_in_the_fb_filter.md)
- 🛑🛑★★★★★ [`0x28F4C` runs EVERY tick (above the engagement guard), 11 free scratch regs, no PSW hazard — but Honda's ±12000 bail tests r7, so a cave MUST clamp](reference_accord_0x28f4c_rate_operand_hook_runs_every_tick.md)
- 🛑🛑★★★★★ [`0x29D72` is the fb-operand hook, flag-safe, byte-stock in V289 — but it is SKIPPED once the ramp hits 0, so seed on gp-0x6cf8==0x7FFFFFFF](reference_accord_0x29d72_is_the_feedback_operand_hook_flagsafe.md)
- 🛑🛑★★★★★ [cal 0xC62E6=46080 clamps r26 before any hook and the rail IS reached on the wire; a V289-style Q14 notch OVERFLOWS int32 there; no add-with-carry on V850, `satadd` exists](reference_accord_fb_operand_clamp_46080_overflows_a_q14_notch.md)
- 🛑🛑★★★★★ [r26 (fb) is callee-saved and dormant 0x28FBE→0x29D78 with zero intermediate readers](reference_accord_r26_feedback_hook_cleanest_at_v288_cave_entry.md)
- 🛑🛑★★★★★ [Sum-S notch hook: 0x2A174 is the ONLY convergence point of the 4 paths forming the clamped PID sum; scratch r6/r7/r9/r13 free](reference_accord_sum_S_notch_hook_0x2a174_convergence_point.md)
- 🛑🛑★★★★★ [0x2A1E6's multiply is y (output-lag result) × gp-0x69b0 (engagement ramp), not the rectified fb magnitude — corrects V287's doc](reference_accord_2a1e6_multiply_is_outputlag_y_times_engagement_ramp.md)
- ★★★★ [Importing a built image: auto-analysis finds ZERO functions, create_function required, body_size doubles as a desync check; never save_all_programs on shared state](reference_accord_importing_a_built_image_into_ghidra.md)

## The demand / setpoint side

- 🛑🛑★★★★★ [The Kp/Kd schedule X axis is the demand index, 1 LSB = 16.1257 wire counts EXACTLY; X[0] is at rec+0x02; Kd unschedulable above idx 32; both slot-7 records share CRC page 0xE5000](reference_accord_kp_kd_schedule_axis_is_the_demand_index.md)
- 🛑🛑★★★★★ [MEASURED idx p50 = 5, p90 = 58 — 91 % of engaged time sits in Kp's FIRST segment, so its non-zero knots are all above p90; Kd's knots straddle the busy zone](reference_accord_demand_index_distribution_on_the_wire.md)
- 🛑🛑★★★★★ [gp-0x69ae = clamp(−4·signed 0xE4 STEER_TORQUE, ±0x4000); the −4 is `shl`+`subr`, NOT a `mul`; gp-0x6803 = SET_ME_X00 bits 3:2, which openpilot packs 0](reference_accord_0e4_handler_x4_verified_and_gp6803_is_set_me_x00.md)
- 🛑🛑★★★★★ [gp-0x69ae has exactly 3 readers; motor torque is generated internally and scaled by the gp-0x69b0 ramp at 0x2a1e6](reference_accord_op_0e4_steer_command_full_path.md)
- 🛑🛑★★★★★ [Variant record table at 0xCD012 dumped whole (16 rows, 9 numeric classes); V273's docstring pairs 1-based names with 0-based values](reference_accord_variant_record_table_0xcd012_full_dump.md)
- 🛑★★★★★ [gp-0x674E ≤ 9 in every coded variant — bank slots 10–27 are dead calibration](reference_accord_variant_selector_max_is_nine.md)

## Delivery, aggregator and the r24 lane

- [0x2A30E–0x2B421 is an UNCALLED TWIN island; gp-0x6b4c carries LKAS, gp-0x6ad4 is a torque tracker; 0x2B41C is the DEAD copy, the live forward is 0x2A2EA](reference_accord_2a30e_2b421_is_an_uncalled_twin_island_and_6b4c_carries_lkas.md)
- 🛑🛑★★★★★ [The gp-0x671d arm INVERTS r24 on V280+ (5244→1024 collapses it ×0.195); a first-strike saturating Schmitt latch cleared only by FUN_0003bcb2 — model r24 as BIMODAL](reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict.md)
- 🛑🛑★★★★★ [Honda's 55 Hz biquad IS live and engaged-only on V280; r24 is the top structural candidate for the 18–22 Hz creep grind; 0xC40DC is NOT virgin](reference_accord_v280_engaged_gates_census_biquad_confirmed_live.md)
- 🛑🛑★★★★★ [Reconciles "Lever B unreachable" with "V280's r24 gain is live" — V104→V280 repointed the SAME `ld.bu` from gp-0x683c to gp-0x6806; the gate's SOURCE was swapped](reference_accord_r24_gate_repoint_reconciles_lever_b_dead_vs_v280_live.md)
- 🛑🛑★★★★★ [gp-0x4f62's Δt is a DMA torque-sensor rolling-counter tick (SVD-confirmed), not CPU-ms; the Q-format chain is bug-free on V283](reference_accord_gp4f62_dt_is_dma_sensor_tick_not_cpu_ms.md)
- 🛑🛑★★★★★ [0xC61BE (the post-gain sum clamp), not D's own 0xC61B6, starves D — and is the secret binding constraint on peak torque, with a sign-extension defect on its positive branch](reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation.md)
- 🛑🛑★★★★★ [V36 gentle-EME debounce re-verified: 12 reader addresses, 0xFFFF through V110, NOT the ratchet/grind cause](reference_accord_v36_gentle_eme_debounce_full_mechanism.md)
- 🛑★★★★★ [Clamp helpers: Ghidra's `in_r10` in FUN_00049a90/78/5a is a cmov artefact; FUN_00055d80 saves r6/r7/r8 and never restores — dead scratch](reference_accord_clamp_helpers_and_packer_scratch.md)

## Interlocks — the sustained-effort question

- 🛑🛑★★★★★ [The ONLY integrate-and-trip on sustained effort is the soft-EME integrator gp-0x3570: `I += (cmd−bound)<<15` per 1 kHz tick, SM2 at |I>>15| ≥ 15361 = 154 ms at 100 counts; governor/FUN_0004595a/FUN_000456a4 carry none; the energy budget is unreachable because gp-0x4f64 ≤ 5325, the cap table's own max](reference_accord_soft_eme_integrator_is_the_only_sustained_effort_trip.md)

## RAM and flash ownership

- 🛑🛑★★★★★ [Full raw-byte census: gp-0x6a2a, gp-0x683c, gp-0x6ab0/6aaa, gp-0x68b0/68aa, gp-0x6c44..6c3a are free — multiple free 32-bit words exist](reference_accord_gp6a2c_to_6a5e_neighborhood_saturated_gp6a2a_is_free.md)
- 🛑★★★★★ [0x2B422/0x2B57A are LIVE (jarl from 0x22530/0x22572); the CORRECTED Format-V jr/jarl mask is 0x07FF, not 0x07C0](reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers.md)
- ⚠ STALE-METHOD NOTE: the falsification of `gp-0x6ab0` cited "occupied by my scan"; an independent 9-form scan finds zero gp hits — the real reason is its NON-ZERO boot value 0x02880288. Verdict stands, method does not.

## CAN telemetry

- 🛑🛑★★★★★ [CAN 427 tap field is 10 bits (byte1 + byte0[1:0]); `ld.h` cannot address an odd gp displacement so gp-0x674B needs `ld.bu`; gp-0x674B has 2 writers, 0 readers](reference_accord_can427_packer_tap_field_full_decode.md)
- 🛑🛑★★★★★ [All 7 EPS outbound frames censused; FUN_000561b0/0x660 writing 7 bytes to zero is a TRAP; only 0x14A/0x18F/0x1AB cross](reference_accord_eps_outbound_frame_census_and_free_bits.md)
- 🛑★★★★★ [CAN 427's opendbc def matches the firmware's own byte-writer census bit-for-bit; 4 spare bits found — and undefined ≠ unwritten](reference_accord_can427_dbc_confirms_4_spare_bits_and_undefined_neq_unwritten.md)
- 🛑🛑★★★★★ [Crossover threshold tabulated in raw counts K=1..6; K=2 clears it at zero peak-torque cost; the 427 packer RECTIFIES so it cannot carry sign(E)](reference_accord_v276_crossover_threshold_and_packer_rectifies_sign.md)

## V850 / Ghidra traps

- 🛑🛑★★★★★ [TWO opcode-field COLLISIONS: 0x3C/0x3D (jr/jarl vs the 6-byte load) and 0x3F (ld.hu vs mul vs setfcc) — BOTH disambiguate on hw2 bit 0 (loads = 1)](reference_accord_v850_opcode_collisions_3c3d_jr_and_3f_mul_disambiguated_by_hw2_bit0.md)
- 🛑★★★★★ [`prepare` COLLIDES with jr/jarl on the Format-V opcode test, inventing false branch targets out of every prologue — filter on TARGET PARITY](reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans.md)
- 🛑★★★★★ [ld.hu is opcode 0x3E/0x3F, not 0x3C/0x3D — a ld.bu-only scanner gives false zeros on halfword cals](reference_accord_v850_load_opcode_map_ldhu_0x3e.md)
- 🛑★★★★ [An operand-text hit on a displacement can land on a different physical byte when a function uses its own non-gp base register — check the base register, not just the displacement](reference_accord_operand_text_search_false_positive_wrong_base_register.md)

## Process feedback

- 🛑★★★★★ [Grep kit memory for the address BEFORE calling a function dead — a passing scanner control proves the scanner, not the claim](feedback_check_kit_memory_before_calling_a_function_dead.md)
- 🛑★★★★★ [Verify TCB "stack pointer/base" labels against the boot disasm, not against each other — the real stack is gp-0xC000..gp-0x86E4](feedback_verify_tcb_stack_labels_against_boot_disasm_not_each_other.md)

## 🛑 THIS INDEX IS A CURATED SLICE, NOT THE STORE

The directory holds **~400 more `reference_accord_*` / `feedback_*` files** than are listed above —
earlier sessions wrote them without indexing. **Before concluding that something has not been traced,
grep the directory**, e.g. `Grep(pattern="gp-0x6b26", path=".claude/agent-memory/firmware-codepath-tracer")`.
The filenames are descriptive and searchable. Index only what a future session would not think to grep for.
(Corrected 2026-09-13: five index links used hyphens where the files use underscores, and the earlier
"STALE LINK" note about `reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells.md` was wrong —
that file does exist on disk.)
