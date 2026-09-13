# Firmware Codepath Tracer — Memory Index

## 2026-09-13 — V292 error-feedback fb-lag cave design, for `main` (agent `cavedesign`)
- 🛑🛑★★★★★ [The fb filter's TWO `sar 0xa` floors give the feedback a CONSTANT -32-count DC offset at EVERY amplitude on V291 (-20 on V282), measured against the exact linear filter — that is +32 counts of PHANTOM ERROR on E = 32*sp - fb, one whole extra setpoint count forever, and it is the real mechanism behind ADV-V291-B's B4, NOT the 1.07-count quantum; it scales as 1/(1024-a) so EVERY lower pole pays more (a 2 Hz pole would cost -157). Fix = carry the residue; `t & 0x3FF` IS the floor remainder exactly, for either sign](reference_accord_fb_filter_floor_bias_is_32_counts_of_phantom_error.md)
- 🛑🛑★★★★★ [0x28F8E is a ZERO-NEW-LIVENESS-CLAIM hook: its straight-line span unconditionally WRITES {r7,r9,r13,r14} before reading them, and it sits AFTER the ±12000 bail so a cave needs no clamp (the decisive edge over 0x28F4C); plus 6 reusable gp-base encoding controls, and the correction that 0xC4C00-0xC4FF0 is 1008 B of 0xFF on V291 — the record's "868 B at 0xC4C90" was read from the V289 image](reference_accord_0x28f8e_zero_liveness_hook_in_the_fb_filter.md)

## 2026-09-13 — V291 adversarial pass, surface D (interlocks/downstream), for `main` (agent `advD`)
- 🛑🛑★★★★★ [TWO V850E2 opcode-field COLLISIONS: `0x3C/0x3D` is shared by Format-V `jr`/`jarl` AND the 6-byte extended-disp23 load; `0x3F` is shared by `ld.hu`, `mul` (hw2=0x0220) and `setfcc`. BOTH disambiguate on **hw2 bit 0** (loads=1). A decoder without these reads `jr` as a load and `mul` as `ld.hu` — a phantom cal reader at a phantom address. Caught by scoring a hand decoder against Ghidra's own 60-instruction listing on LENGTH](reference_accord_v850_opcode_collisions_3c3d_jr_and_3f_mul_disambiguated_by_hw2_bit0.md)

## 2026-09-13 — r24 lane form / gain arms / delivery chain, for `r24lane`/`main`
- 🛑🛑★★★★★ [The `gp-0x671d` arm's sign is INVERTED between stock and V280+: stock 512->1024 DOUBLES r24, V280+ 5244->1024 COLLAPSES it to x0.195 — a first-strike saturating Schmitt latch (SET 5530 / RELEASE 1024) cleared only by FUN_0003bcb2, so ONE event removes 80% of the lane for the rest of the drive; model r24 as BIMODAL. Also flags an UNRESOLVED conflict between two existing memories over gp-0x6b4c vs gp-0x6ad4 as the LKAS aggregator term (my evidence favours gp-0x6ad4; neither file edited)](reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict.md)


## 2026-09-08 — rate-loop lags, D-hook, RAM/flash census, Q0/Q7-Q9 for `loopshape`/`team-lead`
- 🛑🛑★★★★★ [UPDATED: full raw-byte census (all ld/st widths+parities, gp bit-ops, absolute-pointer, movhi/movea) verifies gp-0x6a2a, gp-0x683c, gp-0x6ab0/6aaa (free 2-word run), gp-0x68b0/68aa (free 2-word run), gp-0x6c44..6c3a (free 3-word/12B run) -- YES, multiple free 32-bit words exist; a st.b opcode hand-arithmetic error of mine was caught & fixed mid-census](reference_accord_gp6a2c_to_6a5e_neighborhood_saturated_gp6a2a_is_free.md)
- 🛑🛑★★★★★ [Sum-S notch hook: 0x2A174 is the ONLY convergence point of 4 paths forming the clamped PID sum (r12); r12=S engaged, r12=0 confirmed on the 0x2A164 disengage route (0x2A0C6's own route also reaches the hook but its S value is unconfirmed); scratch r6/r7/r9/r13 free, r16/r22/r24/r27/r29 must be preserved](reference_accord_sum_S_notch_hook_0x2a174_convergence_point.md)
- 🛑🛑★★★★★ [0x2A1E6's multiply is y (output-lag filter result) × gp-0x69b0 (engagement ramp) — NOT the rectified fb magnitude V287's doc assumed; corrects the doc, confirms 5 tracer memories on r14 only, couples the output-lag pole to this stage](reference_accord_2a1e6_multiply_is_outputlag_y_times_engagement_ramp.md)
- 🛑★★★★★ [gp-0x6a34 publishes rectified |fb|, consumed only in a narrow gp-0x680a==1 lane via a THIRD LERP table — self-caught tracing error: the knot-walk right after rectification is keyed by gp-0x6a5e (speed), not this value](reference_accord_gp6a34_publishes_rectified_fb_to_a_gated_lane.md)
- 🛑🛑★★★★★ [r26 (fb) is callee-saved, dormant 0x28FBE→0x29D78 with zero intermediate readers; the V288 cave's own entry (0xC4C00) already has r26 live and unread downstream — the cleanest feedback-filter hook, no new swap site needed](reference_accord_r26_feedback_hook_cleanest_at_v288_cave_entry.md)
- 🛑🛑★★★★★ [raw-Python re-census RE-CONFIRMS gp-0x6a2a/gp-0x683c free (2nd method); a TCB "stack pointer/base" label from TRACE-2026-09-06 is SUSPECT — it would swallow gp-0x6a32 — the real stack (from boot disasm) is gp-0xC000..gp-0x86E4, never overlapping any disp16-reachable cell](feedback_verify_tcb_stack_labels_against_boot_disasm_not_each_other.md)

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

## 2026-09-09 — V290 feedback-operand hook, for `main` (agent `fbhook`)
- 🛑🛑★★★★★ [`0x29D72` (`st.h r16,-0x6a32,gp`, `64 87 ce 95`) is THE fb-operand hook: r26 untouched 0x28FBE→0x29D78, byte-STOCK in V289 (V288's cave is NOT in this base), **NO PSW hazard** unlike 0x2A1B0, r7 dead scratch — but it is SKIPPED once the ramp hits 0, so seed on gp-0x6cf8==0x7FFFFFFF](reference_accord_0x29d72_is_the_feedback_operand_hook_flagsafe.md)
- 🛑🛑★★★★★ [cal 0xC62E6=46080 clamps r26 BEFORE any hook and the rail IS reached on the wire (0.2 %/0.97 %); a V289-style Q14 notch OVERFLOWS int32 there (×0.37 vs V289's own ×1.10) — `sar 3`/`shl 3` restores ×2.93 for 0.032 deg/s; V850 `mul` gives 64 bits but there is NO add-with-carry, `satadd` exists](reference_accord_fb_operand_clamp_46080_overflows_a_q14_notch.md)
- ⚠ STALE-METHOD NOTE: the prior trace's falsification of `gp-0x6ab0` cited "occupied by my scan" — an independent 9-form scan finds **zero gp hits** there; the real reason is its NON-ZERO boot value (0x02880288). Verdict stands, method does not. `gp-0x6D74..gp-0x6D2D` (72 B) re-verified free by 6 methods incl. an `ep`-window adjudication of all 9 overlapping bases.
- 🛑🛑★★★★★ [**0x28F4C** (ld.h -0x6a56,gp,r7) BEATS 0x29D72: it is ABOVE the engagement guard so it runs EVERY tick (no freeze, no gp-0x6cf8 seeding), 11 free scratch regs, no PSW hazard, Q14 fits int32 at x1.405 with NO pre-shift — but Hondas +-12000 plausibility BAIL at 0x28F50 tests r7, so the cave MUST clamp to +-12000; and all 25 reads of gp-0x6a56 are ld.h, so "the only signed read" is FALSE](reference_accord_0x28f4c_rate_operand_hook_runs_every_tick.md)

## 2026-09-09 - the Kp/Kd SCHEDULE X AXIS (0xE5378 / 0xE511C), for `main` / V290
- 🛑🛑★★★★★ [Both schedules are indexed by the SAME demand index the assist map uses: idx = |clamp((G*clamp(-4*cmd,+-LIM))>>22, +-240)|, 1 LSB = 16.1257 wire 0xE4 counts EXACTLY; record layout is X[0] at rec+0x02 (the naive u32-header split fits the bytes and is WRONG); Kd is unschedulable above idx 32; both slot-7 records share ONE CRC page 0xE5000](reference_accord_kp_kd_schedule_axis_is_the_demand_index.md)
- 🛑🛑★★★★★ [MEASURED on r62/r63/r5e: idx p50 = 5, p90 = 58 -- 91 % of engaged time and 100 % of cruise sit in the Kp record's FIRST segment [0,68), so its four non-zero knots are all above p90; Kd's knots straddle the busy zone instead; capped-step and full-lock bookmarks are p50 74-123, a different population from the grinding episodes (p50 8-46)](reference_accord_demand_index_distribution_on_the_wire.md)
- 🛑🛑★★★★★ [VERIFIED FROM BYTES: gp-0x69ae = clamp(-4*signed 0xE4 STEER_TORQUE, +-0x4000) -- the -4 is shl 0x2 + subr r0, NOT a mul (mul-operand searches false-zero on it); scale 16.125736 wire counts per idx LSB EXACT; gp-0x6803 = SET_ME_X00 bits 3:2, openpilot packs 0 so the cliff taper arms are unreachable](reference_accord_0e4_handler_x4_verified_and_gp6803_is_set_me_x00.md)

## 2026-09-13 — the fb-lag filter byte-exact + GATE 1, for `main` (task `tracer`)
- 🛑🛑★★★★★ [Filter decoded byte-exact: state gp-0x3d30 is 32-BIT, `a` is `ld.h` SIGNED so CAPPED AT 32767, the two `sar 0xa` are SEPARATE floors (not one floor of the sum), and 0xC63E8/0xC63EA have EXACTLY ONE reader each with the state cell exactly TWO accesses image-wide — GATE 1 passes by Ghidra AND a controlled two-encoding byte scan, empty set-difference](reference_accord_fb_lag_filter_bytes_and_gate1_private.md)
- 🛑🛑★★★★★ [Reset is the gp-0x3d2c SENTINEL (1=normal, 2=bailed), NOT the 0x2A164 disengage route which never touches the state; the filter runs EVERY tick incl. disengaged so `s` is never stale on re-engage; r25 couples them (a filter bail FORCES skip 2); and lowering `b` opens an asymmetric sar-floor DEAD ZONE of 1024/b counts — 7.7x wider at 2 Hz](reference_accord_fb_filter_sentinel_reset_runs_disengaged_and_deadzone.md)
- [0x2A30E-0x2B421 is an UNCALLED TWIN island; gp-0x6b4c carries LKAS, gp-0x6ad4 is a torque tracker](reference_accord_2a30e_2b421_is_an_uncalled_twin_island_and_6b4c_carries_lkas.md) — 0x2B41C is the DEAD copy; the live forward is 0x2A2EA
