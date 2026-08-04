# Firmware Codepath Tracer — Memory Index

## How I must work
- [🛑 Use SendMessage, not plain text](feedback_use_sendmessage_not_plain_text.md) — plain text is invisible to the lead.
- [🛑 Grep build_v*_tva.py before proposing ANY cal](feedback_check_build_scripts_before_proposing_cal_edit.md) — 0xC6450 was re-proposed after being flashed/falsified as V46.

## Accord TVA-A160 (current project)
### Rate lane V62→V69 cross-build arc (2026-08-04)
- [🛑★★★★★★ V66 REVERTED V62's `sar` doubling — V69 is a DIFFERENT mechanism, not a re-cut](reference_accord_rate_lane_v62_to_v69_gain_arc.md) — full speed×rate gain table vs stock; V69 = exactly 1.000× ≥50 km/h and 4.000× in MANUAL creep; rails at |dt| 683 vs repo max 839; saturation alone CANNOT make V69 weaker than V62 (DF monotone in K) — the rate-axis rolloff can. ⚠ r26 inertness is OPEN.
- ★★★★★★ Same file §7/§8: **FUN_0003ad74 rebuilds BOTH tables (first half IS gain_B)**, blend is STRICT 2-POINT ⇒ ≥50.000 km/h exact; and with the gate live the arm (engaged) and the surface (manual) are **provably independent knobs, cave-free** — but V69's edit-order invariant INVERTS.
- 🛑★★★★★★ Same file §6 (RESOLVED 2026-08-04): **r26 is LIVE — the "structurally inert / 0xC6564" memory is WRONG.** gp-0x6bda is a margin to a ≥±9390 peak-hold envelope of DRIVER ASSIST, so hands-off sits 24× clear of the ±384 kill window. ⇒ V67/V68's one-byte repoint **cut r26 6.00× engaged** and their total may be BELOW stock; measure `a = gp-0x69a4/1024` via a `gp-0x6adc` rung. 0xC6444 only ever tested downward; overflow ceiling 6553.
### 1 kHz oscillation detector gate/liveness (2026-08-03)
- [★★★★★ Detector gate self-clears, input is live ISR-fed, gp-0x6c2c bypasses the gate entirely](reference_accord_detector_gate_input_liveness_verified.md) — gp-0x67df exhaustively 2 accesses (1 writer); TCB table 0xBB858 re-derived via LE32 scan; recommends probing gp-0x6c2c directly to sidestep the DTC-gate ambiguity.
### RAM ownership / code-cave GATE 1 (2026-08-02)
- [🛑★★★★★★ APP RAM MAP SOLVED: gp/tp/sp DERIVED, and TWO boot writers no scan can see](reference_accord_app_ram_layout_and_boot_init_loops.md) — zero-clear 0xFEDEC000-0xFEDFFFFF @0x146C0; .data copy flash 0x86260-0x8AB18 → gp-0x6E50..gp-0x2598 @0x14766; stack tops at 0xFEDEF91C.
- [★★★★★★ GATE-1 audit of gp-0x683c: 7 access classes, all clear bar a named residual](reference_accord_gate1_gp683c_ram_ownership_audit.md) — 🛑 inverted heuristic: a LONG free run means ARRAY, not free RAM (69% of the gp window scans "free").
### Boost-amplitude index producer chain (2026-07-30, session 2)
- [🛑★★★★★★ BOTH curves reach gp-0x6bbe, not a clean series product](reference_accord_boost_amp_series_question_corrected.md) — y1 via nonlinear path (diff vs gp-0x6a56, clamp ±12000, ramp-SM gated); y4 separate.
- [★★★★★ Blend slows RISING only; 0xD2000 = modes 10/11/12 packed](reference_accord_boost_amp_blend_direction_and_d2000_block.md) — mode-10 edit isolated; task-5 rate now resolved (100Hz, see below).
- [★★★★★★ r24 gain_B table SOLVED: 1 array not 2, 4-way priority gate, mode table is DEFAULT not unconditional](reference_accord_r24_gainb_table_structure_and_priority_gate.md) — mode-10's 4 records blast-radius-private; gp-0x671a live/dead status open; gp-0x6ac0=4.7121 counts/deg/s exact + ≥13001 folds to MAX gain.
- [★★★★★★ gp-0x6abc = MOTOR RESOLVER RATE, not torque; sole producer FUN_00041464](reference_accord_boost_index_input_is_resolver_rate_not_torque.md) — chain to FUN_00065afe/FUN_00068f52.
- [★★★★★ tp+0x73ba: 2 reads in FUN_0003b66a, ~0.3dB atten@21Hz; no LKAS-only decoupling point](reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping.md) — gp-0x6bd0 sign=-sign(gp-0x6abe).
### Common-mode motor-rate bus, FUN_000456a4 (2026-07-30)
- [★★★★★★ gp-0x6abe/gp-0x6ac0 ONE signal, ONE producer, 15+ lanes IN PHASE](reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain.md) — differentiator→EMA α=37/128; net −40.4° vs velocity.
- [★★★★★ gp-0x6ad0 write-only YET live; "0→2560 step" FALSIFIED](reference_accord_fun456a4_gp6ad0_resolved_live_damping_no_step.md) — continuous damper, reaches gp-0x6b98 via gp-0x6acc→FUN_00042af8.
- [★★★★★★ ALL FOUR unprobed lanes A/B/C/D SOLVED: net-damping or −27dB](reference_accord_four_unprobed_lanes_abcd_solved.md) — lane A has ±0x2000 zero-gate.
### Steering-angle / return-to-centre (2026-07-29/30)
- [🛑 EPS DOES transmit steering angle, CAN 0x14A (330), not 0x156](reference_accord_can_angle_producer_and_no_angle_correction.md) — retracts no_steering_angle_tx.
- [★★★★★ gp-0x6bbe FULL trace: unfiltered angle-rate error, NET DAMPING](reference_accord_gp6bbe_angle_rate_path_traced_net_damping.md) — 4 static-gain levers, none overlap V44/47.
- [★★★★★★ BASELINE SOLVED: angle-washout FALSIFIED; LERP struct format](reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved.md) — FSM gates baseline 0 vs fresh-each-tick.
- [⚠ gp-0x6b9a "gate-only, 2x IIR" — real FIR stage exists upstream](reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism.md)
- [★★★★★ Rate-limiter enum: FUN_0004613e is fault-tag only](reference_accord_rate_limiter_enumeration_gp6bb2_cluster_and_angle_rate_producer.md) — disabled limiter: shaper tp+0x71d6=0.
### Engagement-gated feedback loop (2026-07-26→29, 08-01)
- [FUN_0003a382 residual loop: gp-0x6ad6 carries 4× LKAS gain](reference_accord_fun3a382_engagement_gated_residual_loop.md) — ⚠ 0xC6450/0xC644A flashed V46/V43, falsified.
- [0xC646C 6-reader enum: real feedback, not the 21Hz driver](reference_accord_c646c_gain_feedback_vs_forward_classification.md) — free cal 0xC6CD0 TAKEN (V57); gp-0x6b12 LIVE.
- [★ POST-V56 lane table: 11 summands, not 8/9](reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md) — r24/r26 top suspect; boost(6bbe) 2nd.
- [Per-lane DOMAIN audit: no angle/angle-rate lane exists](reference_accord_aggregator_domain_audit_no_angle_lane_found.md) — return-centre = speed+motor-rate+timing.
- [★★★★★ FUN_00028ea6 ramp SM: gp-0x6806→0 at FULL-SCALE ramp](reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded.md) — 9-state SM, rules out a clean chopper.
- [DECISIVE: 0xC6AF0 mute unconditionally zeroes gp-0x6ad4](reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math.md) — gp-0x67fe==0 is EPS-assist-DOWN.
- [V56: FUN_0003a382 real P/I/D, gp-0x6ad4 ADDED not subtracted](reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md) — D rivals P.
- [gp-0x6ad6 CLOSED: reaches nowhere but FUN_0003a382](reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md)
- [★★★★★ Deadband+sign-gate 0xC61B8/0xC64A3 inert on V53+](reference_accord_deadband_signgate_c61b8_c64a3_routes_to_diagnostics_not_motor.md) — ⚠ conflicts w/ ramp SM.
- [★★★★★ gp-0x6806 = f(phase gp-0x679f); 8/16 writers dead](reference_accord_gp6806_phase_flag_and_dead_writer_split.md) — ⚠ 3 derivations, unreconciled.
- [🛑★★★★★★ NO cal-only LKAS fork exists for r24/r26; gp-0x671d = RESOLVER domain](reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain.md) — only gp-0x6b4c is LKAS among FUN_0003aa2c inputs; gp-0x67fe/6806/69b0 fresh-before-aggregator but unread; gp-0x4f62 has no EMA.
- [🛑★★★★★★ gp-0x683c repoint: zero-writers RE-CONFIRMED; best candidate = gp-0x67fe](reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule.md) — ld.bu true disp LSB is in hw1 bit5, not hw2; 0xC6446/0xC6444 private; gp-0x67a4 real reader but saturation-dwell, rejected.
### CAN RX plumbing / vehicle speed / creep grinding (2026-07-20→24)
★ **RESOLVED 2026-07-24: firmware speed window EXISTS; the 🛑 entry below is FALSIFIED.**
- [SOLVED: low-speed lockout = speed WINDOW, cal 0xC62EA=320](reference_accord_low_speed_lockout_window_c62ea.md) — ST=3 kills STEER_CONTROL_ACTIVE + authority ramp.
- [CAN RX descriptor table 0xBB550 + speed from 0x158 → gp-0x6a46](reference_accord_can_rx_descriptor_table_and_vehicle_speed.md) — pins gp-0x1500 as 0x326 buffer.
- [V850E2 6-byte disp23 encoding SOLVED](reference_v850e2_extended_disp23_encoding_solved.md) — 4 methods a load-bearing xref answer needs.
- [2nd 320-gate 0xC62EE = CAN-commanded assist shutdown](reference_accord_c62ee_second_320_gate_is_can_commanded_assist_shutdown.md) — live via RTOS table 0xBB9B8.
- [★★★★★★ SETTLED: producer chain proven + damping ZERO below 35 km/h](reference_accord_gp6a5e_producer_chain_and_creep_zero_damping.md)
- [gp-0x6a5e/62/64 = VOTED VEHICLE SPEED (64 cts/km/h)](reference_accord_gp6a5e_is_voted_vehicle_speed.md) — test: speed axis has every X mult. of 64.
- [STEER_STATUS=3 speed-gated but gp-0x6807 REPORT-ONLY](reference_accord_steerstatus3_speed_gated_but_report_only.md)
- [CAN RX descriptor table @0xBB5A0 decoded](reference_accord_can_rx_descriptor_table_bb5a0.md)
- [CAN RX acceptance filter: ID=word>>18 @0xB733C](reference_accord_can_rx_acceptance_filter_id_table_decoded.md) — accepts 0x1D0+0x158.
- [0xC6518/0xC6534 readers FOUND — axis probably THERMAL](reference_accord_c6518_lerp_readers_found_likely_thermal.md)
- [0xD0xxx LERP bank layout; "speed axis" FALSIFIED](reference_accord_d0xxx_lerp_bank_layout_and_pointer_indirection.md)
- [🛑 FALSIFIED — "arbitration has ZERO speed reads"](reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md)
### Task-rate / timing
- [Sign source confirmed 1kHz; damping-magnitude rate NOT proven](reference_accord_sign_source_rate_not_divided.md)
- [STEER_STATUS=4 dwell D=100 → 2nd independent 1kHz route](reference_accord_steerstatus4_dwell_constant_D.md)
- [gp-0x67fa is a STATE MACHINE not a phase counter](reference_accord_state4_ratchet_and_gp67fa_state_graph.md)
- [★★★★★★ RTOS SOLVED: TCB has no period field; rates from FUN_00014be4 mod-100 divider](reference_accord_rtos_task_table_and_rate_scheduler.md) — TAUJ1I2 sole tick writer; OSTM0 is 500Hz not the tick.
- [🛑★★★★★★ TASK 5 = 100 Hz, via syscall8 FUN_000837c0 TCB-index arithmetic](reference_accord_task5_rate_resolved_and_feedforward_insertion_point.md) — FUN_0002c478/gp-0x6b12 is live anti-damping lane.
- [★★★★★ PCLK=40MHz ⇒ OSTM0=500Hz, not the control tick](reference_accord_pclk_40mhz_and_ostm0_is_500hz.md) — 1kHz conclusion survives on-car anchors.
- [★★★★★ SETTLED: 0x930/0xc30/0xd30 = one-hot ECU-STATE masks, NOT a phase counter](reference_accord_0x930_masks_are_state_not_phase_settled.md)
- [★★★★ DTC-0x18 watchdog: TAUA1I1 needs gp-0x68b7&0xF==0xF; 4 tasks set bits 0-3](reference_accord_dtc18_cadence_watchdog.md)
- [FUN_00041464 sign-filter phase](reference_accord_fun41464_sign_filter_phase_response.md) — 5/16-gated, fs_eff 312.5Hz; ⚠ corrected above.
### Torque sensor / steering-angle ownership (2026-07-23)
- [Resolver/CORDIC sensor; zero-ref + additive bias gp-0x6b66](reference_accord_torque_sensor_zero_and_assist_bias_mechanism.md) — RID 0x48F6 dormant self-test.
- [No persistent torque/angle-neutral routine anywhere](reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map.md) — SID 0x30/0x31 + bootloader enumerated.
### Hands-on/off discriminator sweep (21Hz vibration)
- [gp-0x6a5e voter bandwidth insufficient for 21Hz](reference_accord_gp6a5e_voter_bandwidth_insufficient_for_21hz.md)
- [gp-0x6a5e is a MAGNITUDE + NO CAN bridge](reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge.md) — pins gp-0x4f60↔CAN399.
- [gp-0x67ac lane-suppression gate — trigger UNRESOLVED](reference_accord_gp67ac_aggregator_lane_suppression_gate.md)
- [Damping/friction/return-centre torque gates](reference_accord_damping_friction_returncentre_torque_gates.md)
- [Notch/biquad search — negative, not exhaustive](reference_accord_notch_biquad_search_negative_result.md)
- [r26 adaptive lane: full trace + sign proof](reference_accord_r26_adaptive_lane_full_trace_and_sign.md) — V39 falsified; gp-0x6b5e reading imprecise, see V61.
- [🛑★★★★★★ V61 taps confirmed on stock; sign = polarity-INDEPENDENT lead-shape; gain-arm priority decoded](reference_accord_v61_taps_gain_priority_and_sign_apples_to_apples.md) — r24 ~7-22x headroom; r24 default arm MODE-INDEXED (gp+0x63fd); V62 doubles both via sar edits; 0xC6C42(D) held as V63 fallback.
- [FUN_0003a382 "resonance" lane is UNFILTERED](reference_accord_fun3a382_resonance_lane_unfiltered_correction.md) — prior gain=4 claim wrong.
- [FUN_00034350 damping vs gain-cut — RECOMMEND THE DAMPER](reference_accord_fun34350_damping_term_live_and_gated.md) — net-damps at 21.4Hz; V44 built from this.
- [Governor energy-budget UNREACHABLE; slew-STEP is driver-torque-linked](reference_accord_governor_energy_budget_and_step_selector.md)
- [FUN_000352b4 = untested carrier + cal-DEAD biquad](reference_accord_fun352b4_untested_carrier_and_dead_biquad.md) — ⚠ partly superseded.
- [CORRECTION: gp-0x6b86 is a peak-hold; 0xC6450 strongest 21Hz carrier](reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole.md)
- [FUN_00043e44 has no float twin of the chain](reference_accord_fun43e44_no_assist_chain_float_twin.md)
### Torque command path / clamps / shaper
- [G1 governor clamps TOTAL command, not LKAS-only](reference_accord_g1_governor_total_scope_verdict.md)
- [gp-0x6809 has ZERO writers — E1 gate structurally dead](reference_accord_gp6809_zero_writers_confirmed_dead_gate.md)
- [Shaper FUN_00042af8 clamp stack](reference_accord_shaper_fun42af8.md) — ceiling ±0x2000, one-sided input gate.
- [Governor all branches (gp+0x184)](reference_accord_governor_gp0x184_chain.md) — branch-1 max=4762, motor-RATE-adaptive.
- [gp-0x4f64 governor has 3 consumers](reference_accord_gp4f64_three_consumers.md) — output ≤4762.
- [Mixer LKAS source chain](reference_accord_mixer_lkas_source_chain.md) — tp+0x71b2=512 clamp.
- [gp-0x6b4c lane chain](reference_accord_gp6b4c_lane_chain.md) — LKAS demand → gp-0x6b98.
- [FUN_000456a4 gate mechanics + index identity](reference_accord_fun456a4_gate_no_hysteresis_and_index_identity.md) — ⚠ superseded by common-mode-rate-bus section.
- [Generic math helpers abs/min/clamp](reference_accord_generic_math_helpers_49a5a_49a78_49a90.md)
- [Slew limiter + shaper deadband dropout](reference_accord_slew_limiter.md) — step 0xC61D6=0 stock = EME amplifier.
- [Arb+input cluster inventory (28 vars)](reference_accord_arb_input_cluster.md)
- [Governor zeroing / assist-mode EME dropout](reference_accord_governor_zeroing_mechanisms.md)
- [gp-0x6af8 fight trigger](reference_accord_gp6af8_fight_trigger.md) — ROAD fight not driver fight.
- [Integrator update form + V21 startup fault](reference_accord_integrator_update_form.md)
- [EME bit32 float monitor (V18 root cause)](reference_accord_eme_bit32_float_monitor.md)
- [0xC6664 = LERP_B envelope, NOT corridor twin](reference_c6664_lerp_b_envelope.md)
- [Consistency monitor hard-shutdown (DTC 0xF00049)](reference_accord_consistency_monitor_hardshutdown.md)
- [Arb bVar1 full enumeration](reference_accord_arb_bvar1_full_enumeration.md) — 9 LKAS-zeroing gates.
- [TVA downstream chain: gp-0x6b98 motor output](reference_accord_tva_downstream_chain.md)
- [LKAS path wiring PATH-A vs PATH-B](reference_accord_lkas_path_wiring.md) — setpoint has 2 readers.
- V14 (arb gain 891→1782 + clamps 512→1024) FLASHED + ROAD-TESTED (2026-05-26).
### Decider / engage state machine / STEER_STATUS
- [FUN_0002a30e = real STEER_STATUS=4 producer, debounce+hold FSM](reference_accord_fun2a30e_steerstatus_debounce_statemachine.md)
- [Decider hook 0x40e64 sees the real ENGAGED torque-MAX fire](reference_accord_decider_0x40e64_hook_confirmed_sees_real_fire.md)
- [FUN_0003d04c case-4 + hidden 2nd gate](reference_accord_fun3d04c_case4_and_arb_gp6809_forwarding.md) — superseded by gp-0x6809.
- [Decider gate A/B trampoline anchors](reference_accord_decider_shared_epilogue_trampoline_anchors.md)
- [FUN_0003c7fc angle-deadband: clean branch-free anchor](reference_accord_fun3c7fc_trampoline_anchor.md)
- [Deliver-commit Gate5/Gate7 anchor audit](reference_accord_deliver_commit_gate5_gate7_trampoline_anchors.md)
- [Engage-SM full dispatcher + trump-exits](reference_accord_engage_sm_full_dispatcher_and_trump_exits.md) — gp-0x67FE==2 trump; producer FUN_0003bd7c confirmed (see r24-no-fork entry above).
- [Engage-SM caller enum + V34 scope](reference_accord_engage_sm_caller_enumeration_v34.md)
- [gp-0x35B5 reader found](reference_accord_gp35b5_reader_found.md) — NOT write-only.
- [gp-0x6CC4 tracking pipeline + engage-SM 2nd gate](reference_accord_gp6cc4_tracking_pipeline.md)
- [LKAS engage-SM disengage trigger (gentle EME)](reference_accord_lkas_engage_sm_disengage_trigger.md) — V33.
### CAN TX / RDBI / UDS
- [Mailbox-16 free-check + strobe cross-check + 2 V850 encodings](reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings.md)
- [FUN_0001cf30 boot mailbox init — free pool 7-31, TX 57-63](reference_accord_can_mailbox_boot_init_fun1cf30_free_pool.md)
- [Full 18-slot table decode + ID formula](reference_accord_can_tx_full_table_decode_and_new_id_recipe.md) — all 7 IDs share mailbox 6.
- [FUN_0003d4a2 hardware phase-disable dispatcher](reference_accord_fun3d4a2_hardware_phase_disable_dispatcher.md) — motor-off site.
- [CAN 427 source gp-0x6c18 is NOT gp-0x6b98](reference_accord_can427_source_is_gp4f74_not_gp6b98.md)
- [CAN 399/427 full byte/bit map](reference_accord_can_tx_399_427_bitmap.md)
- [CAN 0x14A (330) byte/bit map — no free byte](reference_accord_can_tx_frame_0x14a_bytemap.md)
- [CAN 330 spare bits CONFIRMED dead](reference_accord_can_frame_330_deadbits_wholeimage_confirmed.md)
- [Free RAM candidates gp-0x1500/gp-0x14E0](reference_accord_free_ram_candidates_gp1500_gp14e0.md)
- [Code cave RE-MEASURED: 0xC4B34-0xC4FEF = 1212B](reference_accord_codecave_c4b34_c4fef_larger_than_documented.md)
- [RDBI handler_ptr IS live dispatch](reference_accord_a160_rdbi_handlerptr_live_dispatch.md)
- [App-UDS session-gate + FCN0 egress](reference_accord_a160_app_uds_session_gate_and_egress.md)
- [WHY car-facing vs internal CAN frames](reference_accord_why_car_facing_vs_internal_2026-07-07.md)
- [CAN TX subsystem synthesis (Seg A-D)](reference_accord_can_tx_synthesis_2026-07-07.md)
- [Internal-ID lifecycle / CAN init+pinmux](reference_accord_internal_id_lifecycle.md)
- [TVA HW-ID provenance](reference_accord_tva_hw_id_provenance.md)
### FOC inner current loop (2026-07-22)
- [FOC ISR chain mapped + PWM timer map SVD-confirmed](reference_accord_foc_inner_current_loop_architecture.md) — gp-0x6b98 NOT read by FOC core.
- [★★★★★★ BELOW gp-0x6b98 SWEPT: 45-site map](reference_accord_below_gp6b98_foc_delivery_path_swept.md) — FOC core has only 3 external inputs.
### V48B/V50/V52 gp-0x4f60 notch/filter feasibility (2026-07-21→24)
- [gp-0x4f60 is a SHADOW-LOCKSTEP pair — filter a COPY, not the source](reference_accord_gp4f60_notch_filter_feasibility_v48b.md)
- [V48B reader closure — carriers FUN_0003b66a + FUN_0003b49a](reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass.md) — hook 0x7feac.
- [V48B repoint asymmetry — SAFE, closed by Monitor-1](reference_accord_v48b_repoint_asymmetry_review.md)
- [V50 carryover + completeness gap — resolved below](reference_accord_v50_gp4f60_repoint_asymmetry_carryover_and_completeness_gap.md)
- [FUN_0002eda8/2ec52 CLOSED — live "lane 9" command path](reference_accord_fun2eda8_lane9_raw_torque_command_path.md)
- [V52 9-lane monitor-asymmetry audit — ALL 9 SAFE](reference_accord_v52_9lane_monitor_asymmetry_audit_clean.md)

## C120/A030/TVA UDS+SA surface (cross-platform)
- [TVA/Accord bootloader map + delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
