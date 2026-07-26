# Firmware Codepath Tracer — Memory Index

## How I must work
- [🛑 Use SendMessage, not plain text — and stop on a failed anchor](feedback_use_sendmessage_not_plain_text.md) — plain-text reports are invisible to the lead; cost 3 exchanges of duplicated work.

## Accord TVA-A160 (current project)

### CAN RX plumbing / vehicle speed (2026-07-24)
- [★★★★★ SOLVED: low-speed lockout = speed WINDOW, cal 0xC62EA=320 (4.995 km/h) lo / 0xC62E8=12800 hi](reference_accord_low_speed_lockout_window_c62ea.md) — 1 reader each, cal-only lever; ST=3 → kills STEER_CONTROL_ACTIVE + authority ramp; corrects the "report-only" verdict (consumer is intra-function).
- [★★★★★ CAN RX descriptor table 0xBB550 + vehicle speed from 0x158 → gp-0x6a46 in km/h×64](reference_accord_can_rx_descriptor_table_and_vehicle_speed.md) — 19 ID/buffer/handler records; pins gp-0x1500 as the CAN 0x326 buffer (V50 GATE-1 root cause); 0x1D0 decode present but wiring unestablished.
- [★★★★★ V850E2 6-byte disp23 encoding SOLVED — exact byte scans, no 7.6× over-match](reference_v850e2_extended_disp23_encoding_solved.md) — validated 3× vs Ghidra; names the 4 methods a load-bearing xref answer needs.
- [★★★★★ 2nd 320-gate 0xC62EE is NOT a lockout — CAN-commanded assist shutdown; 0xC62EA-only IS sufficient](reference_accord_c62ee_second_320_gate_is_can_commanded_assist_shutdown.md) — live via RTOS task table 0xBB9B8 (Ghidra gives FALSE DEAD 4 ways); Format-V jr/jarl encoding + its ld.bu collision; gp-0x680c = 5r/5w tri-state.

### Torque-sensor zero / assist-bias (2026-07-23)
- [★★★★ Resolver/CORDIC sensor; zero-ref subtracted + separate additive bias gp-0x6b66](reference_accord_torque_sensor_zero_and_assist_bias_mechanism.md) — 2 cal-record parsers; RID 0x48F6 traced to a dormant factory self-test, not the live path; data-flash link unestablished.

### Task-rate / timing
- [★★★ Sign source confirmed 1kHz; damping-magnitude rate NOT proven](reference_accord_sign_source_rate_not_divided.md)
- [★★★ STEER_STATUS=4 dwell D=100 → 2nd independent 1kHz route](reference_accord_steerstatus4_dwell_constant_D.md)
- [★★★ gp-0x67fa is a STATE MACHINE not a phase counter](reference_accord_state4_ratchet_and_gp67fa_state_graph.md)
- [★★ OSTM0 master tick ~1kHz — inferred not verified](reference_accord_ostm0_master_tick_rate_derivation.md)
- [★★★ FUN_00041464 sign-filter phase — verdict flips on unresolved task rate](reference_accord_fun41464_sign_filter_phase_response.md)

### Vehicle-speed / 5mph grinding (2026-07-20 → 2026-07-24)
- ★★★★★ **RESOLVED 2026-07-24: a firmware speed window EXISTS. The three ★★★ entries at the bottom of this section are FALSIFIED — read these three first.**
- [★★★★★ gp-0x6a5e/0x6a62/0x6a64 ARE VOTED VEHICLE SPEED (64 counts per km/h), NOT driver torque](reference_accord_gp6a5e_is_voted_vehicle_speed.md) — CAN 0x1D0 → 4×15-bit → voter; 3 independent unit derivations. ✅ VERIFIED: V44/V47 "Factor C" axis 2240 = **35 km/h** (not driver torque) and stock Y=0 across the whole 3-8 m/s buzz regime; gentle-EME 320=5km/h; governor 640=10km/h. Reusable test: a speed axis has **every X a multiple of 64** (20/90 in 0xD0xxx, 12/52 in 0xD2xxx; assist gain is MAX at standstill).
- [★★★★★ STEER_STATUS=3 IS speed-gated: speed_clamp_lo = cal 0xC62EA = 320 = 5.0 km/h — BUT gp-0x6807 is REPORT-ONLY](reference_accord_steerstatus3_speed_gated_but_report_only.md) — full 20-writer table, both encodings; no torque-gating reader.
- [★★★★★ CAN RX descriptor table @0xBB5A0 decoded (handler + dest buffer per ID) — resolves the ID↔dest pairing flagged below; gp-0x1500 = the CAN 0x326 RX buffer](reference_accord_can_rx_descriptor_table_bb5a0.md)
- [★★★★★ CAN RX acceptance-filter DECODED: ID = word>>18 @0xB733C — EPS DOES accept 0x1D0 + 0x158](reference_accord_can_rx_acceptance_filter_id_table_decoded.md) — self-calibrated on LKAS 0xE4; ⚠ ID↔dest pairing now GIVEN by the 0xBB5A0 descriptor table above.
- [★★★★ 0xC6518/0xC6534 readers FOUND (FUN_00039702 LERP) — axis probably THERMAL not speed](reference_accord_c6518_lerp_readers_found_likely_thermal.md) — Ghidra reports zero xrefs on all 5 addrs; no speed-validity window found.
- [★★★★ 0xD0xxx LERP bank layout + pointer indirection; 0xD07A4 "speed axis" FALSIFIED (it's a damper factor)](reference_accord_d0xxx_lerp_bank_layout_and_pointer_indirection.md) — ptr targets COUNT; tp/mov32/xref liveness tests give FALSE dead for this whole bank.
- [🛑 FALSIFIED 2026-07-24 — "arbitration has ZERO speed reads; ST=3 is a torque fallback"](reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md) — it reads gp-0x6a5e = SPEED, and ST=3 IS the speed window.
- [🛑 SUPERSEDED 2026-07-24 — "0x1D0 decoder unlocated"; it is FUN_00052E32 (validity) + FUN_00021646-family/FUN_00053216 (values)](reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder.md)
- [🛑 FALSIFIED 2026-07-24 — "No speed-dependent gain in the base-assist loop"; gp-0x6a5e (speed) has 47 readers incl. the damper](reference_accord_no_speed_gain_in_baseassist_feedback_loop.md)

### Steering-angle ownership (2026-07-23)
- [★★★ EPS transmits NO steering-angle CAN message — doesn't own reported angle](reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md) — internal RACKPOS DTC-names exist but never broadcast; data-flash driver found, no angle/torque link.
- [★★★★★ No persistent torque/angle-neutral routine exists anywhere (SID 0x30/0x31 + bootloader fully enumerated)](reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map.md)

### Hands-on/off discriminator sweep (21Hz vibration)
- [★★★ gp-0x6a5e voter bandwidth insufficient for 21Hz](reference_accord_gp6a5e_voter_bandwidth_insufficient_for_21hz.md)
- [★★★ gp-0x6a5e is a MAGNITUDE + NO CAN bridge exists](reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge.md) — pins gp-0x4f60<->CAN399 formula.
- [★★★ gp-0x67ac aggregator lane-suppression gate — wholesale on/off, trigger UNRESOLVED](reference_accord_gp67ac_aggregator_lane_suppression_gate.md)
- [★★ Damping/friction/return-centre torque gates](reference_accord_damping_friction_returncentre_torque_gates.md)
- [★ Notch/biquad search — negative, not exhaustive](reference_accord_notch_biquad_search_negative_result.md)
- [★★★ r26 adaptive lane: full trace + sign proof + cal-only kill target](reference_accord_r26_adaptive_lane_full_trace_and_sign.md) — V39 theory falsified.
- [★★★ FUN_0003a382 "resonance" lane is UNFILTERED — prior gain=4 claim wrong](reference_accord_fun3a382_resonance_lane_unfiltered_correction.md)
- [★★★★★ FUN_00034350 damping vs gain-cut — RECOMMEND THE DAMPER](reference_accord_fun34350_damping_term_live_and_gated.md) — net-damps at 21.4Hz; V44 built from this.
- [★★ Governor energy-budget UNREACHABLE + slew-STEP is driver-torque-linked](reference_accord_governor_energy_budget_and_step_selector.md)
- [★★ FUN_000352b4 = untested carrier + cal-DEAD biquad](reference_accord_fun352b4_untested_carrier_and_dead_biquad.md) — ⚠ superseded in part, see next.
- [★★★ CORRECTION: gp-0x6b86 is a peak-hold + Stage A pole (0xC6450) pinned as strongest live 21Hz carrier](reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole.md)
- [★ FUN_00043e44 has no float twin of the assist/aggregator chain](reference_accord_fun43e44_no_assist_chain_float_twin.md)

### Torque command path / clamps / shaper
- [★★★★★ G1 governor clamps TOTAL command, not LKAS-only; "energy budget" not real thermal](reference_accord_g1_governor_total_scope_verdict.md)
- [★★★ gp-0x6809 has ZERO writers — E1 gate structurally dead](reference_accord_gp6809_zero_writers_confirmed_dead_gate.md)
- [Shaper FUN_00042af8 clamp stack](reference_accord_shaper_fun42af8.md) — ceiling ±0x2000, input gate one-sided.
- [Governor all branches (gp+0x184)](reference_accord_governor_gp0x184_chain.md) — branch-1 max=4762, motor-RATE-adaptive.
- [★★ gp-0x4f64 governor has 3 consumers](reference_accord_gp4f64_three_consumers.md) — output provably ≤4762.
- [Mixer LKAS source chain](reference_accord_mixer_lkas_source_chain.md) — tp+0x71b2=512 binding clamp.
- [gp-0x6b4c lane chain](reference_accord_gp6b4c_lane_chain.md) — LKAS upstream demand.
- [Post-governor comp add FUN_000456a4](reference_accord_post_governor_comp_add.md) — speed-LERP correction.
- [★★ FUN_000456a4 gate: real mechanics, deprioritized as V38 regression](reference_accord_fun456a4_gate_no_hysteresis_and_index_identity.md)
- [★ Generic math helpers abs/min/clamp (49a5a/49a78/49a90)](reference_accord_generic_math_helpers_49a5a_49a78_49a90.md)
- [Slew limiter + shaper deadband dropout](reference_accord_slew_limiter.md) — step 0xC61D6=0 stock = EME amplifier.
- [Arb+input cluster inventory (28 vars)](reference_accord_arb_input_cluster.md)
- [Governor zeroing / assist-mode EME dropout](reference_accord_governor_zeroing_mechanisms.md)
- [gp-0x6af8 fight trigger](reference_accord_gp6af8_fight_trigger.md) — fires on ROAD fight not driver fight.
- [Integrator update form + V21 startup fault](reference_accord_integrator_update_form.md)
- [EME bit32 float monitor (V18 root cause)](reference_accord_eme_bit32_float_monitor.md)
- [0xC6664 = LERP_B envelope, NOT corridor twin](reference_c6664_lerp_b_envelope.md)
- [Consistency monitor hard-shutdown (DTC 0xF00049)](reference_accord_consistency_monitor_hardshutdown.md)
- [Arb bVar1 full enumeration](reference_accord_arb_bvar1_full_enumeration.md) — 9 LKAS-zeroing gates.
- [TVA downstream chain: gp-0x6b98 motor output](reference_accord_tva_downstream_chain.md)
- [LKAS path wiring PATH-A vs PATH-B](reference_accord_lkas_path_wiring.md) — setpoint has only 2 readers.
- V14 (arb gain 891→1782 + clamps 512→1024) FLASHED+ROAD-TESTED, works (2026-05-26).

### Decider / engage state machine / STEER_STATUS
- [★★★ FUN_0002a30e = real STEER_STATUS=4 producer, debounce+hold FSM](reference_accord_fun2a30e_steerstatus_debounce_statemachine.md)
- [★★ Decider hook 0x40e64 confirmed to see the real ENGAGED torque-MAX fire](reference_accord_decider_0x40e64_hook_confirmed_sees_real_fire.md)
- [★★ FUN_0003d04c case-4 + hidden 2nd gate](reference_accord_fun3d04c_case4_and_arb_gp6809_forwarding.md) — superseded by gp-0x6809 dead-gate.
- [★★ Decider gate A/B trampoline anchors](reference_accord_decider_shared_epilogue_trampoline_anchors.md)
- [★★ FUN_0003c7fc angle-deadband: clean branch-free anchor](reference_accord_fun3c7fc_trampoline_anchor.md)
- [★ Deliver-commit Gate5/Gate7 anchor audit](reference_accord_deliver_commit_gate5_gate7_trampoline_anchors.md)
- [Engage-SM full dispatcher + trump-exits](reference_accord_engage_sm_full_dispatcher_and_trump_exits.md) — gp-0x67FE==2 trump.
- [Engage-SM caller enum + V34 scope](reference_accord_engage_sm_caller_enumeration_v34.md)
- [gp-0x35B5 reader found](reference_accord_gp35b5_reader_found.md) — NOT write-only.
- [gp-0x6CC4 tracking pipeline + engage-SM 2nd gate](reference_accord_gp6cc4_tracking_pipeline.md)
- [LKAS engage-SM disengage trigger (gentle EME)](reference_accord_lkas_engage_sm_disengage_trigger.md) — V33 fix.

### CAN TX / RDBI / UDS
- [★★ Mailbox-16 free-check + strobe cross-check + 2 new V850 encodings (2026-07-23)](reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings.md)
- [★★★★★ FUN_0001cf30 boot mailbox init — free pool 7-31, TX pool 57-63 (2026-07-24)](reference_accord_can_mailbox_boot_init_fun1cf30_free_pool.md)
- [★★★★★ Full 18-slot table decode + ID formula + new-ID recipe (2026-07-23)](reference_accord_can_tx_full_table_decode_and_new_id_recipe.md) — all 7 known IDs share mailbox 6; real 330 rate 62.5Hz.
- [★★ CAN 330/0x14A TX period — ⚠ corrected by entry above, real rate 62.5Hz](reference_accord_can330_tx_rate_unresolved.md)
- [★★★ FUN_0003d4a2 hardware phase-disable dispatcher — THE motor-off site](reference_accord_fun3d4a2_hardware_phase_disable_dispatcher.md)
- [★★ CAN 427 source gp-0x6c18 is NOT gp-0x6b98](reference_accord_can427_source_is_gp4f74_not_gp6b98.md)
- [★ CAN 399/427 full byte/bit map](reference_accord_can_tx_399_427_bitmap.md)
- [★ CAN 0x14A (330) full byte/bit map](reference_accord_can_tx_frame_0x14a_bytemap.md) — no free byte.
- [★★ CAN 330 spare bits CONFIRMED dead whole-image](reference_accord_can_frame_330_deadbits_wholeimage_confirmed.md)
- [★ Free RAM candidates gp-0x1500/gp-0x14E0](reference_accord_free_ram_candidates_gp1500_gp14e0.md)
- [★★ Code cave RE-MEASURED: 0xC4B34-0xC4FEF = 1212B](reference_accord_codecave_c4b34_c4fef_larger_than_documented.md)
- [★ RDBI dispatch off-by-one — "handler_ptr dead" RETRACTED, see next](reference_accord_a160_rdbi_dispatch_table_offbyone.md)
- [★★ RDBI handler_ptr IS live dispatch, corrected patch spec](reference_accord_a160_rdbi_handlerptr_live_dispatch.md)
- [App-UDS session-gate + FCN0 egress](reference_accord_a160_app_uds_session_gate_and_egress.md)
- [★ WHY car-facing vs internal CAN frames — synthesis](reference_accord_why_car_facing_vs_internal_2026-07-07.md)
- [CAN TX subsystem synthesis (Seg A-D)](reference_accord_can_tx_synthesis_2026-07-07.md)
- [Internal-ID lifecycle / CAN init+pinmux topology](reference_accord_internal_id_lifecycle.md)
- [TVA HW-ID provenance](reference_accord_tva_hw_id_provenance.md) — UDS 0x84 handler only.

### FOC inner current-loop architecture (2026-07-22)
- [★★★★ FOC ISR chain mapped + PWM timer map SVD-confirmed + gp-0x6b98 NOT read by FOC core](reference_accord_foc_inner_current_loop_architecture.md) — Kp/Ki not isolated; loop rate ~8-16kHz IF PCLK=80MHz (unverified).

### V48B/V50/V52 gp-0x4f60 notch/filter feasibility (2026-07-21 → 2026-07-24)
- [★★★★ gp-0x4f60 is a SHADOW-LOCKSTEP pair (fault idx 0x17) — recommend FILTERED COPY not source-filter](reference_accord_gp4f60_notch_filter_feasibility_v48b.md) — 74-hit reader classification.
- [★★★★★ V48B reader closure — 2/5 orig carriers MODE-GATED DORMANT; true carriers FUN_0003b66a + FUN_0003b49a](reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass.md) — hook site corrected to 0x7feac.
- [★★★★★ V48B repoint asymmetry review — SAFE w/ 1 open item](reference_accord_v48b_repoint_asymmetry_review.md) — type-8 lockstep FUN_00027b0a matched.
- [★★★★★ Monitor-1 DTC-0x1c closes the open item — matched int/float shadow, not a magnitude gate](reference_accord_v48b_monitor1_dtc1c_notch_safety_closed.md)
- [★★★★★ V50 carryover + completeness gap (2026-07-23)](reference_accord_v50_gp4f60_repoint_asymmetry_carryover_and_completeness_gap.md) — 3 readers never classified before; ⚠ resolved by entry below.
- [★★★★★ FUN_0002eda8/2ec52 CLOSED — 2eda8 is a live "lane 9" command path, 2ec52 is diagnostic-only](reference_accord_fun2eda8_lane9_raw_torque_command_path.md) — full chain to FUN_0003a382; no new DTC asymmetry.
- [★★★★★ V52 9-lane monitor-asymmetry audit — ALL 9 SAFE, no raw-vs-filtered lockstep divergence (2026-07-24)](reference_accord_v52_9lane_monitor_asymmetry_audit_clean.md) — gp-0x6a32 zero readers (triple-corroborated), gp-0x6b2c re-confirmed dead, every live comparison is vs literal/cal or self-state; DTC 0x18/0x23/0x49 checked, all unrelated.

## C120/A030/TVA UDS+SA surface (Civic/Accord platform, cross-referenced)
- [TVA/Accord bootloader map + delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.

## EPS SH-2A bootrom (39990-family, cross-vehicle)

## Radar 36802TBA (separate ADAS project)
