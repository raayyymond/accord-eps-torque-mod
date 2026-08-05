# Firmware Codepath Tracer — Memory Index

- [🛑🛑★★★★★★ Mode-selector FUN_00042746 mapped: engagement-linked (VERIFIED), confined to {10,11} for TVAA1 IF that key is ever set](reference_accord_mode_selector_fun42746_closed_confined_to_10_11.md) — SUPERSEDED-AS-SETTLED by the entry below, its own conclusion is now conditional.
- [🛑🛑🛑 gp+0x6408 config-key: ONLY writer is a UDS request (5 methods), NOT the ID string; cell is .bss/never boot-populated in any path found ⇒ live mode may be row-0 {0,1,2,3} not 10/11, on ANY build incl. stock — NOT closed, boot-loop computed-pointer path not ruled out](reference_accord_config_key_gp6408_udsonly_writer_bss_no_boot_populator.md).

## How I must work
- [🛑 Use SendMessage, not plain text](feedback_use_sendmessage_not_plain_text.md) — invisible to the lead otherwise.
- [🛑 Grep build_v*_tva.py before proposing ANY cal](feedback_check_build_scripts_before_proposing_cal_edit.md) — 0xC6450 re-proposed after flashed/falsified.

## Accord TVA-A160 (current project)
### Friction lane FUN_00036c12 — stick-slip hypothesis (2026-08-04)
- [🛑★★★ Smooth signed multiply, NO sign()/hysteresis, CANNOT stick-slip](reference_accord_friction_lane_fun36c12_smooth_no_stickslip.md) — corrects golden model (gp-0x6c2c not 6c2e; axis=speed); resonance LIVE on V72.
### gp-0x6bd0 null round 2 + engagement gates (2026-08-05)
- [🛑🛑 "FactorA"=seed CLOSED: all 11 channels pinned 1024 stock+V72; null UNRESOLVED; 2 NEW engagement gates](reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found.md) — converges w/ [2nd derivation](reference_accord_damper_seed_gp61e8_boot_image_and_gp617c_distinct_array.md); supersedes gp698a entry.
- [🛑🛑 mode gp+0x63fd struct CONFIRMED (HW-ID failover→{10,11}, boots 0) but V72 telemetry EXCLUDES 10/11 (bit4 0/87940 incl. highway); settled by V73 probe not statics](reference_accord_mode_selector_gp63fd_hwid_failover_not_engagement_flag.md).
### Base-assist damper (FactorC/E) + r24/r26 (2026-08-04)
- [🛑★★★ FUN_00034350 mapped; FactorC axis=SPEED; r24/r26 separate](reference_accord_factorc_e_damper_full_trace_r24r26_parallel.md) — creep hard-zero; GATE-2 phase@7.79Hz 14-28°.
### Task-rate census + 21Hz damping-authority hunt (2026-08-04/05, F3)
- [🛑🛑 task1=1kHz/task5=100Hz LIVE; FUN_00041464 fs_eff CORRECTED 312.5→1000Hz; FactorC/E cos≈0.52@20.9Hz, cos≈0.93@7.79Hz](reference_accord_task5_100hz_live_verified_full_producer_census.md) — 3 rounds self-correction on record.
- [★★★ gp-0x6b26 friction lane LEVER SIZED — 0xD2A44 x1.5-2.0 + 0xC407E→850-1024; GATE2 clean; RULE-4 virgin×67; feel=transient parking-speed](reference_accord_gp6b26_friction_lane_damping_candidate.md).
### Near-centre / small-signal hunt for grind #1 (2026-08-04/05, F1)
- [🛑★★★ gp-0x6CC4→6a10 creep-band FLAT ZERO; 0xC61B8 RE-DERIVED still inert on V72 (gate bypassed+wiring-isolated)](reference_accord_near_centre_structure_hunt_angle_tracking_chain_found.md).
- [gp-0x69a4("a") slew decoded: floor-0+snap-cal(0xC6178)](reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected.md). [Angle scale gp-0x69ca=0.1deg/ct SETTLED](reference_accord_angle_position_scale_0p1_deg_per_count_settled.md).
- [🛑🛑 HUNT CLOSED: 0xC6B64 virgin but REJECTED (3.8% vs needed 3.2x); PLANT property, reopen bar >2x over 0-45° absolute angle](reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles.md).
### Motor-control layer (FOC/PWM/resolver) (2026-08-04)
- [🛑★★★ Carrier=4.000kHz (was ~8kHz)](reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected.md). [★★★ FUN_000757a2 1kHz torque model→CAN427](reference_accord_fun757a2_torque_model_and_lerp6_cluster.md).
- [🛑🛑★★★ gp-0x6abe=4.7121×column_degps SETTLED](reference_accord_gp6abe_column_degps_scale_settled.md) — first pass (0.589014) RETRACTED.
- [🛑★★★ 6-LERP cluster = creep/highway gain sched for FOC Iq/Id PI+FF, not ripple](reference_accord_fun757a2_iqid_gainschedule_bridge_resolved.md) — index=gp-0x4ac; all 12 tables in CRC-skipped [0xC5000,0xC5FFC) ⇒ no lever.
### gp-0x67ac aggregator gate (2026-08-04)
- [🛑🛑★★★ ALWAYS 0 — REDUCED-sum branch UNREACHABLE](reference_accord_gp67ac_reduced_branch_unreachable.md) — V72 safe.
### LKAS engagement → torque route enumeration (2026-08-04)
- [🛑★★★ gp-0x67fa 33w decoupled from engagement](reference_accord_gp67fa_writer_census_decoupled_from_engagement.md). [🛑★★★ PATH-A(arb) LIVE](reference_accord_patha_arb_is_live_not_inert_correction.md). [★★★ gp-0x69b0 gates FUN_0002a93a](reference_accord_gp69b0_authority_gate_and_fun42746_table_selector.md).
### 7.5 Hz ratchet loop-element hunt (2026-08-04)
- [★★★ Time-constant inventory @7.793Hz](reference_accord_ratchet_time_constant_inventory_and_factorce_lever.md). [🛑🛑★★★ FUN_00036388 dwell-relay=unconditional BRAKE](reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive.md). [🛑★★★ gp-0x68ad DEAD](reference_accord_gp68ad_field_dead_and_gp6d78_bit15_one_way_state4_cycle_refuted.md).
- [🛑★★★ V72 Lever A red-team: r24 3.41× exceeds V62's regression trigger](reference_accord_v72_levera_high_rate_redteam.md).
### Rate lane V62→V69 cross-build arc (2026-08-04)
- [🛑★★★ V66 reverted V62's sar-doubling; V69 different mechanism; r26 LIVE](reference_accord_rate_lane_v62_to_v69_gain_arc.md).
### 1 kHz oscillation detector (2026-08-03)
- [★★★ Gate self-clears, input live, gp-0x6c2c bypasses gate](reference_accord_detector_gate_input_liveness_verified.md).
### RAM ownership / code-cave GATE 1 (2026-08-02)
- [🛑★★★ APP RAM MAP SOLVED](reference_accord_app_ram_layout_and_boot_init_loops.md). [★★★ GATE-1 gp-0x683c clear](reference_accord_gate1_gp683c_ram_ownership_audit.md).
### Boost-amplitude index producer chain (2026-07-30 s2)
- [🛑★★★ Both curves reach gp-0x6bbe, not series](reference_accord_boost_amp_series_question_corrected.md). [★★★ Blend slows RISING only](reference_accord_boost_amp_blend_direction_and_d2000_block.md). [★★★ r24 gain_B priority gate](reference_accord_r24_gainb_table_structure_and_priority_gate.md).
- [★★★ gp-0x6abc=MOTOR RESOLVER RATE not torque](reference_accord_boost_index_input_is_resolver_rate_not_torque.md). [★★★ tp+0x73ba ~0.3dB atten@21Hz](reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping.md).
### Common-mode motor-rate bus, FUN_000456a4 (2026-07-30)
- [★★★ gp-0x6abe/6ac0 ONE signal, net −40.4°](reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain.md). [★★★ gp-0x6ad0 live, step FALSIFIED](reference_accord_fun456a4_gp6ad0_resolved_live_damping_no_step.md). [★★★ 4 lanes SOLVED, net −27dB](reference_accord_four_unprobed_lanes_abcd_solved.md).
### Steering-angle / return-to-centre (2026-07-29/30)
- [🛑 EPS transmits angle via CAN 0x14A not 0x156](reference_accord_can_angle_producer_and_no_angle_correction.md). [★★★ gp-0x6bbe unfiltered, NET DAMPING](reference_accord_gp6bbe_angle_rate_path_traced_net_damping.md). [★★★ BASELINE SOLVED, LERP struct](reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved.md).
- [⚠ gp-0x6b9a gate-only 2x IIR](reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism.md). [★★★ Rate-limiter enum: fault-tag only](reference_accord_rate_limiter_enumeration_gp6bb2_cluster_and_angle_rate_producer.md).
### Engagement-gated feedback loop (2026-07-26→29, 08-01)
- [FUN_0003a382 gp-0x6ad6 4× LKAS gain](reference_accord_fun3a382_engagement_gated_residual_loop.md) ⚠0xC6450/0xC644A falsified. [0xC646C 6-reader feedback](reference_accord_c646c_gain_feedback_vs_forward_classification.md). [★ 11-lane table](reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md).
- [No angle/angle-rate lane exists (pre-F1)](reference_accord_aggregator_domain_audit_no_angle_lane_found.md). [★★★ FUN_00028ea6 ramp SM](reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded.md). [0xC6AF0 mute zeroes gp-0x6ad4](reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math.md).
- [V56: FUN_0003a382 real P/I/D](reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md). [gp-0x6ad6 CLOSED](reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md). [★★★ Deadband 0xC61B8/0xC64A3 inert](reference_accord_deadband_signgate_c61b8_c64a3_routes_to_diagnostics_not_motor.md).
- [★★★ gp-0x6806=f(phase gp-0x679f)](reference_accord_gp6806_phase_flag_and_dead_writer_split.md). [🛑★★★ NO LKAS fork for r24/r26](reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain.md). [🛑★★★ gp-0x683c zero-writers RE-CONFIRMED](reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule.md).
### CAN RX / vehicle speed / creep grinding (2026-07-20→24)
- [SOLVED: window cal 0xC62EA=320](reference_accord_low_speed_lockout_window_c62ea.md). [CAN RX table 0xBB550+speed→gp-0x6a46](reference_accord_can_rx_descriptor_table_and_vehicle_speed.md). [disp23 SOLVED](reference_v850e2_extended_disp23_encoding_solved.md). [2nd gate 0xC62EE](reference_accord_c62ee_second_320_gate_is_can_commanded_assist_shutdown.md).
- [★★★ gp-0x6a5e producer + damping ZERO<35km/h](reference_accord_gp6a5e_producer_chain_and_creep_zero_damping.md). [gp-0x6a5e=VOTED SPEED(64cts/km/h)](reference_accord_gp6a5e_is_voted_vehicle_speed.md). [ST=3 speed-gated, gp-0x6807 REPORT-ONLY](reference_accord_steerstatus3_speed_gated_but_report_only.md).
- [CAN RX @0xBB5A0](reference_accord_can_rx_descriptor_table_bb5a0.md). [accept filter @0xB733C](reference_accord_can_rx_acceptance_filter_id_table_decoded.md). [0xC6518/34 readers, THERMAL?](reference_accord_c6518_lerp_readers_found_likely_thermal.md). [0xD0xxx LERP bank; "speed axis" FALSIFIED](reference_accord_d0xxx_lerp_bank_layout_and_pointer_indirection.md). [🛑 arb zero speed reads FALSE](reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md).
### Task-rate / timing
- [Sign source 1kHz; damping rate NOT proven](reference_accord_sign_source_rate_not_divided.md). [ST=4 dwell D=100](reference_accord_steerstatus4_dwell_constant_D.md). [gp-0x67fa STATE MACHINE](reference_accord_state4_ratchet_and_gp67fa_state_graph.md).
- [★★★ RTOS SOLVED: mod-100 divider](reference_accord_rtos_task_table_and_rate_scheduler.md). [🛑★★★ TASK5=100Hz](reference_accord_task5_rate_resolved_and_feedforward_insertion_point.md). [★★★ PCLK=40MHz⇒OSTM0=500Hz](reference_accord_pclk_40mhz_and_ostm0_is_500hz.md).
- [★★★ 0x930/c30/d30=state masks](reference_accord_0x930_masks_are_state_not_phase_settled.md). [★★★ DTC-0x18 watchdog](reference_accord_dtc18_cadence_watchdog.md). [FUN_00041464 phase, fs_eff 312.5Hz — SUPERSEDED, see task5 census above](reference_accord_fun41464_sign_filter_phase_response.md).
### Torque sensor / steering-angle ownership (2026-07-23)
- [Resolver/CORDIC, zero-ref+bias gp-0x6b66](reference_accord_torque_sensor_zero_and_assist_bias_mechanism.md). [No persistent neutral routine](reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map.md).
### Hands-on/off discriminator sweep (21Hz vibration)
- [gp-0x6a5e voter bandwidth insufficient for 21Hz](reference_accord_gp6a5e_voter_bandwidth_insufficient_for_21hz.md). [gp-0x6a5e MAGNITUDE, no CAN bridge](reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge.md). [gp-0x67ac suppression gate](reference_accord_gp67ac_aggregator_lane_suppression_gate.md).
- [Damping/friction/return-centre gates (pre-08-04)](reference_accord_damping_friction_returncentre_torque_gates.md). [Notch/biquad search negative](reference_accord_notch_biquad_search_negative_result.md). [r26 trace+sign; V39 falsified](reference_accord_r26_adaptive_lane_full_trace_and_sign.md).
- [🛑★★★ V61 taps confirmed, sign polarity-independent](reference_accord_v61_taps_gain_priority_and_sign_apples_to_apples.md). [FUN_0003a382 resonance UNFILTERED](reference_accord_fun3a382_resonance_lane_unfiltered_correction.md).
- [FUN_00034350 damping live+gated, V44 built from this](reference_accord_fun34350_damping_term_live_and_gated.md). [Governor energy-budget UNREACHABLE](reference_accord_governor_energy_budget_and_step_selector.md).
- [FUN_000352b4 untested carrier+dead biquad ⚠partly superseded](reference_accord_fun352b4_untested_carrier_and_dead_biquad.md). [gp-0x6b86 peak-hold correction](reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole.md). [FUN_00043e44 no float twin](reference_accord_fun43e44_no_assist_chain_float_twin.md).
### Torque command path / clamps / shaper
- [G1 governor clamps TOTAL not LKAS-only](reference_accord_g1_governor_total_scope_verdict.md). [gp-0x6809 dead gate](reference_accord_gp6809_zero_writers_confirmed_dead_gate.md). [Shaper FUN_00042af8 ±0x2000](reference_accord_shaper_fun42af8.md).
- [Governor branches, branch-1 max=4762](reference_accord_governor_gp0x184_chain.md). [gp-0x4f64 governor ≤4762](reference_accord_gp4f64_three_consumers.md). [Mixer LKAS, tp+0x71b2=512](reference_accord_mixer_lkas_source_chain.md). [gp-0x6b4c lane chain](reference_accord_gp6b4c_lane_chain.md).
- [FUN_000456a4 gate mechanics ⚠superseded](reference_accord_fun456a4_gate_no_hysteresis_and_index_identity.md). [Generic math helpers](reference_accord_generic_math_helpers_49a5a_49a78_49a90.md). [Slew limiter/EME amplifier](reference_accord_slew_limiter.md).
- [Arb+input cluster (28 vars)](reference_accord_arb_input_cluster.md). [Governor zeroing/EME dropout](reference_accord_governor_zeroing_mechanisms.md). [gp-0x6af8 ROAD fight trigger](reference_accord_gp6af8_fight_trigger.md). [Integrator form+V21 fault](reference_accord_integrator_update_form.md).
- [EME bit32 float monitor(V18)](reference_accord_eme_bit32_float_monitor.md). [0xC6664 LERP_B envelope](reference_c6664_lerp_b_envelope.md). [Consistency monitor hard-shutdown](reference_accord_consistency_monitor_hardshutdown.md). [Arb bVar1: 9 gates](reference_accord_arb_bvar1_full_enumeration.md).
- [TVA downstream chain](reference_accord_tva_downstream_chain.md). [LKAS PATH-A vs PATH-B](reference_accord_lkas_path_wiring.md). V14 FLASHED+ROAD-TESTED 2026-05-26.
### Decider / engage state machine / STEER_STATUS
- [FUN_0002a30e=real ST=4 producer](reference_accord_fun2a30e_steerstatus_debounce_statemachine.md). [Decider hook 0x40e64 sees real fire](reference_accord_decider_0x40e64_hook_confirmed_sees_real_fire.md). [FUN_0003d04c case-4 — superseded](reference_accord_fun3d04c_case4_and_arb_gp6809_forwarding.md).
- [Decider trampoline anchors](reference_accord_decider_shared_epilogue_trampoline_anchors.md). [FUN_0003c7fc anchor](reference_accord_fun3c7fc_trampoline_anchor.md). [Gate5/7 anchor audit](reference_accord_deliver_commit_gate5_gate7_trampoline_anchors.md).
- [Engage-SM dispatcher+trump-exits](reference_accord_engage_sm_full_dispatcher_and_trump_exits.md). [Caller enum+V34](reference_accord_engage_sm_caller_enumeration_v34.md). [gp-0x35B5 reader](reference_accord_gp35b5_reader_found.md). [gp-0x6CC4 tracking pipeline, root of F1's angle chain](reference_accord_gp6cc4_tracking_pipeline.md). [Disengage trigger V33](reference_accord_lkas_engage_sm_disengage_trigger.md).
### CAN TX / RDBI / UDS
- [Mailbox-16 free-check+encodings](reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings.md). [Boot mailbox init](reference_accord_can_mailbox_boot_init_fun1cf30_free_pool.md). [18-slot table+ID formula](reference_accord_can_tx_full_table_decode_and_new_id_recipe.md).
- [FUN_0003d4a2 phase-disable dispatcher](reference_accord_fun3d4a2_hardware_phase_disable_dispatcher.md). [CAN427 source gp-0x4f74](reference_accord_can427_source_is_gp4f74_not_gp6b98.md). [399/427 bitmap](reference_accord_can_tx_399_427_bitmap.md). [0x14A bytemap, no free byte](reference_accord_can_tx_frame_0x14a_bytemap.md). [330 spare bits dead](reference_accord_can_frame_330_deadbits_wholeimage_confirmed.md).
- [Free RAM gp-0x1500/14E0](reference_accord_free_ram_candidates_gp1500_gp14e0.md). [Code cave 0xC4B34-0xC4FEF=1212B](reference_accord_codecave_c4b34_c4fef_larger_than_documented.md). [RDBI handler_ptr live](reference_accord_a160_rdbi_handlerptr_live_dispatch.md). [App-UDS session-gate](reference_accord_a160_app_uds_session_gate_and_egress.md).
- [WHY car-facing vs internal frames](reference_accord_why_car_facing_vs_internal_2026-07-07.md). [CAN TX synthesis](reference_accord_can_tx_synthesis_2026-07-07.md). [Internal-ID lifecycle](reference_accord_internal_id_lifecycle.md). [🛑 TVA HW-ID gp+0x6408: UDS-write-only, NOT string-parsed — build ID-marker edit cannot break mode match](reference_accord_tva_hw_id_provenance.md).
### FOC inner current loop (2026-07-22)
- [ISR chain+PWM timer map](reference_accord_foc_inner_current_loop_architecture.md). [★★★ Below gp-0x6b98 SWEPT: 45-site map](reference_accord_below_gp6b98_foc_delivery_path_swept.md).
### V48B/V50/V52 gp-0x4f60 notch/filter feasibility (2026-07-21→24)
- [Shadow-lockstep pair, filters a COPY](reference_accord_gp4f60_notch_filter_feasibility_v48b.md). [V48B reader closure](reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass.md). [V48B asymmetry SAFE](reference_accord_v48b_repoint_asymmetry_review.md).
- [V50 carryover resolved](reference_accord_v50_gp4f60_repoint_asymmetry_carryover_and_completeness_gap.md). [FUN_0002eda8 lane9 raw path](reference_accord_fun2eda8_lane9_raw_torque_command_path.md). [V52 9-lane audit SAFE](reference_accord_v52_9lane_monitor_asymmetry_audit_clean.md).

### V73 hypothesis: gain_A `a`-weight index + record-addressing correction (2026-08-05)
- [🛑★★★ `a` LERP index = abs(gp-0x4f60 + gp-0x6b4a); "a~ZERO via 0xC6564" causal link BROKEN; leak capped below two-lane-rule threshold](reference_accord_gain_a_index_and_leak_v73.md) — corrects [[reference_accord_r24_gainb_table_structure_and_priority_gate]] array-to-speed mapping in-place.
- [🛑🛑★★★ NO `a` makes the 8-build ladder monotone ⇒ kills scalar rate-lane-authority model; V61's edit is a register-field zero not gain surface; V67/V68/V71C bypass LERP records entirely when engaged](reference_accord_a_ladder_fit_negative_and_v61_gate_traps.md).

## C120/A030/TVA UDS+SA surface (cross-platform)
- [TVA/Accord bootloader map+delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
