# Firmware Codepath Tracer — Memory Index

## How I must work
- [🛑 Use SendMessage, not plain text — stop on failed anchor](feedback_use_sendmessage_not_plain_text.md) — plain text is invisible to the lead.
- [🛑 Grep build_v*_tva.py before proposing ANY cal address](feedback_check_build_scripts_before_proposing_cal_edit.md) — 0xC6450 was re-proposed after already being flashed/falsified as V46.

## Accord TVA-A160 (current project)

### Steering-angle anchor / return-to-center investigation (2026-07-29/30)
- [🛑 CORRECTION: EPS DOES transmit steering angle, on CAN 0x14A (330), not 0x156](reference_accord_can_angle_producer_and_no_angle_correction.md) — retracts no_steering_angle_tx's bottom line. Chain: FUN_00040a50 <- gp-0x6a00(FUN_0003e6d8) <- gp-0x6cc4 + resolver baseline gp+0x6470; rate gp-0x6a56 shared by 0x14A/0x18F, CAN-TX-only, but gp-0x6a56 itself has 15+ control-path readers.
- [🛑 gp-0x6bbe reads angle RATE gp-0x6a56 unfiltered — flagged vs domain audit](reference_accord_gp6bbe_rate_error_speed_scheduled_lane.md) — see full trace below, superseded.
- [★★★★★ gp-0x6bbe FULL trace: torque EMA is only an AMPLITUDE scale, core = unfiltered angle-rate error — NET DAMPING not reinforcing](reference_accord_gp6bbe_angle_rate_path_traced_net_damping.md) — corrects my own aggregator-table framing; 2 speed tables decoded (gp-0x6a5e=gain hump@40km/h, gp-0x6a62=flat 512 no-op); 4 static-gain levers in the pre-existing DAMP_BLOCK, none overlap V44/V47.
- [★★★★★★ BASELINE SOLVED: torque/motor-rate only, angle-washout FALSIFIED; LERP struct format + K1-vs-ceiling order + 2 new tables](reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved.md) — corrects "rate-keyed" label on 0xCA4F4/0xCA23C (really keyed by gp-0x6ba6, a torque+motor-rate composite from FUN_0003b66a); FSM gates baseline to 0 vs fresh-each-tick, no state-holding lag; task-rate for FUN_00022ca0 still open (found its dispatch table @0xBB9E8, period field undecoded).
- [★★★★★★ gp-0x6b9a is a GATE INPUT only, never an index; 0xD28DC unreachable via 0xca23c; FUN_0003b66a fault-sentinel protocol found](reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism.md) — corrects build_v58_tva.py's "FIR chain indexing 0xD28DC via gp-0x6b9a" on both counts (r9=gp-0x6ba6 indexes, not gp-0x6b9a; 0xD28DC lives at 0xca4f4 not 0xca23c which resolves to 0xD2888); r21 = 5-way |x|<=25600/32000 plausibility AND; FUN_0003b66a is 2x cascaded IIR (one float biquad), NOT FIR, outputs +32767/-1 fault sentinels on bad input that r21 exists to catch.
- [★★★★★ Rate-limiter enum: FUN_0004613e/13880 is NOT a limiter (fault-tag only); gp-0x6a56 SOLE producer FUN_0003f776 derives it ENTIRELY from gp-0x6abe motor-rate](reference_accord_rate_limiter_enumeration_gp6bb2_cluster_and_angle_rate_producer.md) — gp-0x6a60=abs(gp-0x6a56) only; the ONE real disabled rate limiter is shaper FUN_00042af8's tp+0x71d6=0xC61D6=0 (byte-confirmed), already proposed in OLD old_tools/build_v16_tva.py with unknown on-car result — not in current BUILD-LINEAGE.md.

### Engagement-gated feedback loop / 21Hz-only-while-engaged (2026-07-26 → 2026-07-29)
- [FUN_0003a382 residual loop: gp-0x6ad6 carries 4× LKAS gain; gp-0x67a4 gate ≠ engagement switch](reference_accord_fun3a382_engagement_gated_residual_loop.md) — ⚠ 0xC6450/0xC644A already flashed as V46/V43, falsified.
- [0xC646C 6-reader enum: real feedback path, not the 21Hz driver](reference_accord_c646c_gain_feedback_vs_forward_classification.md) — slow(2.18Hz)/small-authority; free cal word 0xC6CD0 found.
- [Aggregator lane inventory (9-lane pass)](reference_accord_gp6b98_aggregator_full_lane_inventory.md) — ⚠ superseded by the definitive table below (11 lanes).
- [★ POST-V56 DEFINITIVE lane table: 11 summands, not 8/9](reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md) — r24/r26 (torque-RATE) TOP suspect: 0dB unfiltered 1kHz same-signed-reinforcing; boost(6bbe) 2nd, gated on FUN_00022ca0's unresolved rate; FUN_00036682 alpha=6 (not 14), dB=-46/-58.
- [Per-lane DOMAIN audit: no angle/angle-rate input found in any of the 11 lanes](reference_accord_aggregator_domain_audit_no_angle_lane_found.md) — return-centre = speed+motor-rate+assist-state-timing (FUN_0003bd7c); gp-0x67f4=speed-voter validity flag; no torque-threshold override gate in-scope (negative, not exhaustive).
- [★★★★★ FUN_00028ea6's ramp SM decoded: gate gp-0x6806 flips to 0 at FULL-SCALE ramp (0x8000), not a residual](reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded.md) — 9-state SM (gp-0x3d38); rules out a clean 20-25Hz chopper arithmetically (~99ms fastest decay); open = gp-0x1426 (CAN trigger byte, zero writers found); conflicts w/ 2 entries below, unreconciled.
- [DECISIVE: 0xC6AF0 mute unconditionally zeroes gp-0x6ad4's output](reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math.md) — branch-agnostic kill; gp-0x67fe==0 is EPS-assist-DOWN not OP-disengaged.
- [V56 task: FUN_0003a382 is a real P/I/D, gp-0x6ad4 proven ADDED not subtracted](reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md) — D grows to rival P by 21Hz; sole reader of 0xC6AF0 image-wide.
- [gp-0x6ad6 (reference model) CLOSED: reaches nowhere but FUN_0003a382](reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md) — retires the "hidden reference-model side-channel" hypothesis.
- [★★★★★ Deadband+sign-gate (0xC61B8/0xC64A3) inert on V53+, routes to diagnostics not gp-0x6b98](reference_accord_deadband_signgate_c61b8_c64a3_routes_to_diagnostics_not_motor.md) — claims gp-0x6806 stays 1 all engaged driving; ⚠ CONFLICTS with fun28ea6_ramp_statemachine below (independent derivation, not yet reconciled — team-lead adjudicating).

### gp-0x6806 phase flag / dead-writer split (2026-07-29)
- [★★★★★ gp-0x6806 = f(phase gp-0x679f); claims 8/16 writers dead in the unclaimed gap; boot value unresolved](reference_accord_gp6806_phase_flag_and_dead_writer_split.md) — ⚠ ALSO CONFLICTS with fun28ea6_ramp_statemachine's 21-hit whole-image scan (8 writes, all live, none in an unclaimed gap) — three independent derivations now on record for this variable, not reconciled.

### CAN RX plumbing / vehicle speed (2026-07-24)
- [SOLVED: low-speed lockout = speed WINDOW, cal 0xC62EA=320 (~5km/h)](reference_accord_low_speed_lockout_window_c62ea.md) — ST=3 kills STEER_CONTROL_ACTIVE + authority ramp.
- [CAN RX descriptor table 0xBB550 + vehicle speed from 0x158 → gp-0x6a46 (km/h×64)](reference_accord_can_rx_descriptor_table_and_vehicle_speed.md) — pins gp-0x1500 as the CAN 0x326 buffer.
- [V850E2 6-byte disp23 encoding SOLVED — exact byte scan, no over-match](reference_v850e2_extended_disp23_encoding_solved.md) — names the 4 methods a load-bearing xref answer needs.
- [2nd 320-gate 0xC62EE is CAN-commanded assist shutdown, not a lockout](reference_accord_c62ee_second_320_gate_is_can_commanded_assist_shutdown.md) — live via RTOS task table 0xBB9B8.

### Torque-sensor zero / assist-bias (2026-07-23)
- [Resolver/CORDIC sensor; zero-ref subtracted + separate additive bias gp-0x6b66](reference_accord_torque_sensor_zero_and_assist_bias_mechanism.md) — RID 0x48F6 is a dormant factory self-test.

### Task-rate / timing
- [Sign source confirmed 1kHz; damping-magnitude rate NOT proven](reference_accord_sign_source_rate_not_divided.md)
- [STEER_STATUS=4 dwell D=100 → 2nd independent 1kHz route](reference_accord_steerstatus4_dwell_constant_D.md)
- [gp-0x67fa is a STATE MACHINE not a phase counter](reference_accord_state4_ratchet_and_gp67fa_state_graph.md)
- [OSTM0 master tick ~1kHz — inferred not verified](reference_accord_ostm0_master_tick_rate_derivation.md)
- [FUN_00041464 sign-filter phase — verdict flips on task rate](reference_accord_fun41464_sign_filter_phase_response.md) — 5/16-phase-gated, fs_eff=312.5Hz off the 1kHz master.
- ⚠ FUN_00022ca0 (assist-shaping task, calls boost/damping producers) rate still UNRESOLVED — decisive for post-V56 lane ranking, see definitive lane table above.

### Vehicle-speed / 5mph grinding (2026-07-20 → 2026-07-24)
- ★ **RESOLVED 2026-07-24: firmware speed window EXISTS. The 3 🛑 entries below are FALSIFIED.**
- [gp-0x6a5e/0x6a62/0x6a64 ARE VOTED VEHICLE SPEED (64 counts/km/h), NOT driver torque](reference_accord_gp6a5e_is_voted_vehicle_speed.md) — reusable test: a speed axis has every X a multiple of 64; damper Factor C/E pointer-chase re-confirmed 2026-07-29 (0xD27BC/0xD27F8), gp-0x67f4=speed-valid flag added.
- [STEER_STATUS=3 IS speed-gated: cal 0xC62EA=320=5.0km/h — but gp-0x6807 is REPORT-ONLY](reference_accord_steerstatus3_speed_gated_but_report_only.md)
- [CAN RX descriptor table @0xBB5A0 decoded (handler + dest buffer per ID)](reference_accord_can_rx_descriptor_table_bb5a0.md)
- [CAN RX acceptance-filter DECODED: ID = word>>18 @0xB733C](reference_accord_can_rx_acceptance_filter_id_table_decoded.md) — EPS accepts 0x1D0 + 0x158.
- [0xC6518/0xC6534 readers FOUND (FUN_00039702 LERP) — axis probably THERMAL](reference_accord_c6518_lerp_readers_found_likely_thermal.md)
- [0xD0xxx LERP bank layout; 0xD07A4 "speed axis" FALSIFIED (it's a damper factor)](reference_accord_d0xxx_lerp_bank_layout_and_pointer_indirection.md)
- [🛑 FALSIFIED — "arbitration has ZERO speed reads"](reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md)
- [🛑 SUPERSEDED — "0x1D0 decoder unlocated"](reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder.md)
- [🛑 FALSIFIED — "No speed-dependent gain in the base-assist loop"](reference_accord_no_speed_gain_in_baseassist_feedback_loop.md)

### Steering-angle ownership (2026-07-23)
- [EPS transmits NO steering-angle CAN message](reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md) — RACKPOS DTC-names exist but never broadcast.
- [No persistent torque/angle-neutral routine anywhere (SID 0x30/0x31 + bootloader fully enumerated)](reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map.md)

### Hands-on/off discriminator sweep (21Hz vibration)
- [gp-0x6a5e voter bandwidth insufficient for 21Hz](reference_accord_gp6a5e_voter_bandwidth_insufficient_for_21hz.md)
- [gp-0x6a5e is a MAGNITUDE + NO CAN bridge exists](reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge.md) — pins gp-0x4f60<->CAN399 formula.
- [gp-0x67ac aggregator lane-suppression gate — trigger UNRESOLVED](reference_accord_gp67ac_aggregator_lane_suppression_gate.md)
- [Damping/friction/return-centre torque gates](reference_accord_damping_friction_returncentre_torque_gates.md)
- [Notch/biquad search — negative, not exhaustive](reference_accord_notch_biquad_search_negative_result.md)
- [r26 adaptive lane: full trace + sign proof + cal-only kill target](reference_accord_r26_adaptive_lane_full_trace_and_sign.md) — V39 theory falsified; see also definitive lane table above.
- [FUN_0003a382 "resonance" lane is UNFILTERED — prior gain=4 claim wrong](reference_accord_fun3a382_resonance_lane_unfiltered_correction.md)
- [FUN_00034350 damping vs gain-cut — RECOMMEND THE DAMPER](reference_accord_fun34350_damping_term_live_and_gated.md) — net-damps at 21.4Hz; V44 built from this.
- [Governor energy-budget UNREACHABLE + slew-STEP is driver-torque-linked](reference_accord_governor_energy_budget_and_step_selector.md)
- [FUN_000352b4 = untested carrier + cal-DEAD biquad](reference_accord_fun352b4_untested_carrier_and_dead_biquad.md) — ⚠ superseded in part, see next.
- [CORRECTION: gp-0x6b86 is a peak-hold + Stage A pole (0xC6450) strongest 21Hz carrier](reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole.md)
- [FUN_00043e44 has no float twin of the assist/aggregator chain](reference_accord_fun43e44_no_assist_chain_float_twin.md)

### Torque command path / clamps / shaper
- [G1 governor clamps TOTAL command, not LKAS-only](reference_accord_g1_governor_total_scope_verdict.md)
- [gp-0x6809 has ZERO writers — E1 gate structurally dead](reference_accord_gp6809_zero_writers_confirmed_dead_gate.md)
- [Shaper FUN_00042af8 clamp stack](reference_accord_shaper_fun42af8.md) — ceiling ±0x2000, input gate one-sided.
- [Governor all branches (gp+0x184)](reference_accord_governor_gp0x184_chain.md) — branch-1 max=4762, motor-RATE-adaptive.
- [gp-0x4f64 governor has 3 consumers](reference_accord_gp4f64_three_consumers.md) — output provably ≤4762.
- [Mixer LKAS source chain](reference_accord_mixer_lkas_source_chain.md) — tp+0x71b2=512 binding clamp.
- [gp-0x6b4c lane chain](reference_accord_gp6b4c_lane_chain.md) — LKAS upstream demand, full forward chain to gp-0x6b98.
- [Post-governor comp add FUN_000456a4](reference_accord_post_governor_comp_add.md) — speed-LERP correction.
- [FUN_000456a4 gate: real mechanics, deprioritized as V38 regression](reference_accord_fun456a4_gate_no_hysteresis_and_index_identity.md)
- [Generic math helpers abs/min/clamp](reference_accord_generic_math_helpers_49a5a_49a78_49a90.md)
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
- [FUN_0002a30e = real STEER_STATUS=4 producer, debounce+hold FSM](reference_accord_fun2a30e_steerstatus_debounce_statemachine.md)
- [Decider hook 0x40e64 confirmed to see the real ENGAGED torque-MAX fire](reference_accord_decider_0x40e64_hook_confirmed_sees_real_fire.md)
- [FUN_0003d04c case-4 + hidden 2nd gate](reference_accord_fun3d04c_case4_and_arb_gp6809_forwarding.md) — superseded by gp-0x6809 dead-gate.
- [Decider gate A/B trampoline anchors](reference_accord_decider_shared_epilogue_trampoline_anchors.md)
- [FUN_0003c7fc angle-deadband: clean branch-free anchor](reference_accord_fun3c7fc_trampoline_anchor.md)
- [Deliver-commit Gate5/Gate7 anchor audit](reference_accord_deliver_commit_gate5_gate7_trampoline_anchors.md)
- [Engage-SM full dispatcher + trump-exits](reference_accord_engage_sm_full_dispatcher_and_trump_exits.md) — gp-0x67FE==2 trump.
- [Engage-SM caller enum + V34 scope](reference_accord_engage_sm_caller_enumeration_v34.md)
- [gp-0x35B5 reader found](reference_accord_gp35b5_reader_found.md) — NOT write-only.
- [gp-0x6CC4 tracking pipeline + engage-SM 2nd gate](reference_accord_gp6cc4_tracking_pipeline.md)
- [LKAS engage-SM disengage trigger (gentle EME)](reference_accord_lkas_engage_sm_disengage_trigger.md) — V33 fix.

### CAN TX / RDBI / UDS
- [Mailbox-16 free-check + strobe cross-check + 2 new V850 encodings](reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings.md)
- [FUN_0001cf30 boot mailbox init — free pool 7-31, TX pool 57-63](reference_accord_can_mailbox_boot_init_fun1cf30_free_pool.md)
- [Full 18-slot table decode + ID formula + new-ID recipe](reference_accord_can_tx_full_table_decode_and_new_id_recipe.md) — all 7 known IDs share mailbox 6; real 330 rate 62.5Hz.
- [CAN 330/0x14A TX period](reference_accord_can330_tx_rate_unresolved.md) — ⚠ corrected by entry above.
- [FUN_0003d4a2 hardware phase-disable dispatcher — THE motor-off site](reference_accord_fun3d4a2_hardware_phase_disable_dispatcher.md)
- [CAN 427 source gp-0x6c18 is NOT gp-0x6b98](reference_accord_can427_source_is_gp4f74_not_gp6b98.md)
- [CAN 399/427 full byte/bit map](reference_accord_can_tx_399_427_bitmap.md)
- [CAN 0x14A (330) full byte/bit map — no free byte](reference_accord_can_tx_frame_0x14a_bytemap.md)
- [CAN 330 spare bits CONFIRMED dead whole-image](reference_accord_can_frame_330_deadbits_wholeimage_confirmed.md)
- [Free RAM candidates gp-0x1500/gp-0x14E0](reference_accord_free_ram_candidates_gp1500_gp14e0.md)
- [Code cave RE-MEASURED: 0xC4B34-0xC4FEF = 1212B](reference_accord_codecave_c4b34_c4fef_larger_than_documented.md)
- [RDBI dispatch off-by-one — "handler_ptr dead" RETRACTED, see next](reference_accord_a160_rdbi_dispatch_table_offbyone.md)
- [RDBI handler_ptr IS live dispatch, corrected patch spec](reference_accord_a160_rdbi_handlerptr_live_dispatch.md)
- [App-UDS session-gate + FCN0 egress](reference_accord_a160_app_uds_session_gate_and_egress.md)
- [WHY car-facing vs internal CAN frames — synthesis](reference_accord_why_car_facing_vs_internal_2026-07-07.md)
- [CAN TX subsystem synthesis (Seg A-D)](reference_accord_can_tx_synthesis_2026-07-07.md)
- [Internal-ID lifecycle / CAN init+pinmux topology](reference_accord_internal_id_lifecycle.md)
- [TVA HW-ID provenance](reference_accord_tva_hw_id_provenance.md) — UDS 0x84 handler only.

### FOC inner current-loop architecture (2026-07-22)
- [FOC ISR chain mapped + PWM timer map SVD-confirmed](reference_accord_foc_inner_current_loop_architecture.md) — gp-0x6b98 NOT read by FOC core; loop rate ~8-16kHz unverified.

### V48B/V50/V52 gp-0x4f60 notch/filter feasibility (2026-07-21 → 2026-07-24)
- [gp-0x4f60 is a SHADOW-LOCKSTEP pair — recommend FILTERED COPY not source-filter](reference_accord_gp4f60_notch_filter_feasibility_v48b.md)
- [V48B reader closure — true carriers FUN_0003b66a + FUN_0003b49a](reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass.md) — hook site corrected to 0x7feac.
- [V48B repoint asymmetry review — SAFE w/ 1 open item](reference_accord_v48b_repoint_asymmetry_review.md)
- [Monitor-1 DTC-0x1c closes the open item](reference_accord_v48b_monitor1_dtc1c_notch_safety_closed.md)
- [V50 carryover + completeness gap](reference_accord_v50_gp4f60_repoint_asymmetry_carryover_and_completeness_gap.md) — resolved by entry below.
- [FUN_0002eda8/2ec52 CLOSED — 2eda8 is a live "lane 9" command path](reference_accord_fun2eda8_lane9_raw_torque_command_path.md)
- [V52 9-lane monitor-asymmetry audit — ALL 9 SAFE](reference_accord_v52_9lane_monitor_asymmetry_audit_clean.md) — no raw-vs-filtered lockstep divergence.

## C120/A030/TVA UDS+SA surface (Civic/Accord platform, cross-referenced)
- [TVA/Accord bootloader map + delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.

## EPS SH-2A bootrom (39990-family, cross-vehicle)

## Radar 36802TBA (separate ADAS project)
