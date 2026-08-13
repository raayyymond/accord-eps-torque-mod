# Memory Index

<!-- ONE SHORT LINE PER ENTRY (<~200 chars). Detail belongs in the topic file — do NOT re-expand here.
     This index passed its 24.4KB read limit on 2026-08-12 and its tail was silently invisible to readers. -->

## V850 / Ghidra method and encoding
- [★★★ v850-instruction-twin-catalogue](reference_accord_v850_instruction_twin_catalogue.md) — Ghidra-certified whole-instruction twins for caves; `cmp rA,rB` = rB−rA settled 3 ways; `mov` flag-transparent, `add`/`sar` are NOT; ld.h vs ld.w = hw2 bit0.
- [**!** v850-6byte-disp-decoder-corrected](reference_accord_v850_6byte_disp_decoder_corrected.md) — the 6-byte gp-disp formula applies to the 2nd/3rd halfwords, base reg 4; misapplying it yields clean FALSE NULLS. Proves neither Ghidra nor Python alone is complete.
- [★ v48b-freeram-and-v850-encoding-formulas](reference_accord_v48b_freeram_and_v850_encoding_formulas.md) — bit-derived encodings for mulhi/add/sar/movea/cmp/addi/ld/st/Bcond/jr/jarl; ★ cave site gp-0x7F00..0x7FFF; corrects the "gp-0x14E0 = 4 free bytes" claim.
- [★ v50-ram-audit-gp1500-gp14e0-and-status-table](reference_accord_v50_ram_audit_gp1500_gp14e0_and_status_table.md) — gp-0x1500 bytes 2-3 are LIVE (3rd reproduction of "zero xref ≠ dead"); reusable byte0-opcode-family table for exhaustive gp scans.
- [★★ v98-gate1-four-cells-and-span-scanner](reference_accord_v98_gate1_four_cells_and_span_scanner.md) — GATE 1 for gp-0x6bfe/6bfa/6752/374c: span-overlap scanner, Ghidra 55 vs Python 56 on gp-0x6752, SVD proves no peripheral in the gp page, flown cave writes exactly 2 cells.

## The observer / mixer group (FUN_00038148, FUN_0003b8f6, FUN_00026c80)
- [★★★ fun38148-task-gate-and-c63ac-pole](reference_accord_fun38148_task_gate_and_c63ac_pole.md) — THE liveness argument: FUN_0002214a is an RTOS task entry; its gp-0x67fa guard wraps mixer + observer identically ⇒ dead means no assist. Residual is a DIFFERENCE OF TWO ESTIMATES; f' unpinnable statically.
- [★★★ observer-filter-mismatch-leaks-the-command](reference_accord_observer_filter_mismatch_leaks_the_command.md) — full observer arithmetic, every cal byte-read. 🛑 Its headline leak hypothesis is DEAD (killed on-car 2026-08-10). Do NOT propose 0xC63AC or 0xC40D4 off this file.
- [★★★ observer-gate-tautology-and-term-mismatch](reference_accord_observer_gate_tautology_and_term_mismatch.md) — the |gp-0x6b98| gate is TAUTOLOGICAL; four exact equivalent gate tests; gp-0x6bf6 is never stale and gives |model| free. The two-filters "leak" is EXONERATED.
- [★★★ residual-lerp-gp3714-runtime-adaptive](reference_accord_residual_lerp_gp3714_runtime_adaptive.md) — residual LERP passes through the ORIGIN (Y[0]=X[0]=0) ⇒ no creep deadband; slope runtime gain-scheduled ⇒ GATE 2 empirical-only; 0xC63AC sits in the PLANT loop.
- [★★★ k1-friction-dose-and-clamp-relay](reference_accord_k1_friction_dose_and_clamp_relay.md) — K1 (0xC40D2) is STRUCTURALLY the wrong lever: bilinear not a relay, fundamental gain 1 at every K1. 0xC40BC is also a ~3.8× friction-GAIN knob ⇒ the flown 600-vs-6000 result is CONFOUNDED.
- [★★★ assist-channel-framework-lkas-is-channel1](reference_accord_assist_channel_framework_lkas_is_channel1.md) — 11-slot assist framework; LKAS is CHANNEL 1; routing table 0xC4124; both destinations are observer lanes at unity gain. Channel arrays are register-indirect-only.
- [★★ gp6b70-chain-terminates-at-falsified-c6af0](reference_accord_gp6b70_chain_terminates_at_falsified_c6af0.md) — gp-0x6b70's chain terminates at cal 0xC6AF0: already flashed by V56, null, reverted V57/V58. All chain weights unity/stock.

## Signal identities — CHECK HERE BEFORE ASSERTING ONE (three have been wrong)
- [★★★ gp4f50-is-a-rate-not-an-angle](reference_accord_gp4f50_is_a_rate_not_an_angle.md) — SETTLES a standing conflict: gp-0x4f50 is a RATE (wrap-corrected first difference, FUN_00068f52); the ANGLE is gp-0x29c2. 0xC646E's "damper" label survives.
- [★★★ fun36c12-negative-accel-feedback](reference_accord_fun36c12_negative_accel_feedback.md) — gp-0x6b26 = −k·(motor accel) ⇒ ADDS apparent inertia, is NOT inertia comp. 🛑 Its index gp-0x6a5e is VOTED VEHICLE SPEED — the kit's 3rd signal-ID error.
- [dual-torque-sensor-architecture](reference_accord_dual_torque_sensor_architecture.md) — two independent column-torque sensors A vs B. 🛑 "Sensor A = driver torque" is RETIRED; gp-0x6a5e/6a62/6a64 are voted vehicle speed. File needs a sweep.
- [can399-torque-vs-voter-scale](reference_accord_can399_torque_vs_voter_scale.md) — gp-0x6a62 and CAN STEER_TORQUE_SENSOR (gp-0x4f60) are DIFFERENT sensors; "~1:1" was wrong; no static bridge ⇒ live RAM read needed.
- [polarity-gp6752-static-boot-config](reference_accord_polarity_gp6752_static_boot_config.md) — gp-0x6752 is a boot-time static constant {−1,0,1}, not a live signal — clean negative for sign-chattering.
- [★★ state671a-is-oscillation-reversal-counter](reference_accord_state671a_is_oscillation_reversal_counter.md) — gp-0x671a RISES on reversals of gp-0x6c2c, saturates ≥5 in ~125-150 ms of 18-21 Hz oscillation; r26's arm is gate-free and safe to raise alone.

## Gates, monitors and safety clearances
- [★★★ factorc-lockstep-gate-clear-ceiling-only](reference_accord_factorc_lockstep_gate_clear_ceiling_only.md) — FactorC is referenced nowhere outside FUN_00034350 (4 methods); the DTC-0x1c/0x1d float lockstep is ceiling-only ⇒ a FactorC edit cannot trip either hard-shutdown monitor.
- [consistency-monitor-hardshutdown](reference_accord_consistency_monitor_hardshutdown.md) — the ONLY live hard-shutdown chain is Monitor 1 (FUN_00042af8 → FUN_0004613e → DTC 0x1c). Monitor 2 is permanently gated by cal 0xC74A4.
- [★ v48b-monitor1-dtc1c-notch-safety-closed](reference_accord_v48b_monitor1_dtc1c_notch_safety_closed.md) — the DTC-0x1c trip is a matched int/float SHADOW-COMPUTATION lockstep on the same cell via the same cal gate — not a magnitude gate. Verdict SAFE.
- [★ v48b-repoint-asymmetry-review](reference_accord_v48b_repoint_asymmetry_review.md) — V48B's 7-site gp-0x4f60 repoint has no raw-vs-filtered lockstep-divergence risk at any consumer checked.
- [★★ gp6ac2-ceiling-only-and-no-motor-command-feedforward](reference_accord_gp6ac2_ceiling_only_and_no_motor_command_feedforward.md) — gp-0x6ac2 is ceiling-only in all 4 consumers; ZERO gp-0x6b98 feedforward upstream of the boost curve. Full loop map + gains.
- [gp6b6c-full-reader-map-fun4fbde-diagnostic-only](reference_accord_gp6b6c_full_reader_map_fun4fbde_diagnostic_only.md) — gp-0x6b6c: 1 writer / 3 reader instructions; FUN_0004fbde is diagnostic-gated ⇒ SAFE for the gp-0x4f60 low-pass repoint.
- [★ fun43e44-report-only-and-gp6acc-slew-limiter](reference_accord_fun43e44_report_only_and_gp6acc_slew_limiter.md) — FUN_00043e44 is REPORT-ONLY; the real per-cycle slew limiter is on gp-0x6ace (cals 0xC6206/0xC6208), NOT 0xC64DE.
- [lkas-column-torque-cut-trigger](reference_accord_lkas_column_torque_cut_trigger.md) — ⚠ SUPERSEDED root model; kept for its RULED-OUT list (bVar1 32000 health gate, plausibility, zero-LERP). The real cut is the engage-SM disengage at cal 0xC6312=320.

## Segment gate maps (2026-07-06 sweep)
- [★ segmentE-arbitration-shaper-dtc-gate-table](reference_accord_segmentE_arbitration_shaper_dtc_gate_table.md) — 17-row gate map across FUN_00028ea6 / FUN_0002a30e / FUN_00042af8 / FUN_00043e44, every cal constant fresh-read.
- [★ segmentD-fun3d04c-full-gate-map](reference_accord_segmentD_fun3d04c_full_gate_map.md) — FUN_0003d04c's 7 pre-gates; gp-0x4f68 SOLVED = unsigned column angular velocity; a SECOND untouched angle-deadband gate downstream; the caller DISCARDS the return value.
- [★ segmentF-delivery-enable-motor-output-gate-table](reference_accord_segmentF_delivery_enable_motor_output_gate_table.md) — ⚠ CORRECTS segmentE's gp-0x67a4 address (0xFEDF185C). 8-state ENABLE-byte FSM in FUN_0002b422; distribute_clamp constants re-verified.
- [★ voter-ratelimit-and-vote-logic](reference_accord_voter_ratelimit_and_vote_logic.md) — FUN_00041eec's three independent limiters and the vote/average logic; gp-0x6a60 confirmed NOT produced here.
- [voter-0xffff-sentinel](reference_accord_voter_0xffff_sentinel.md) — the 0xFFFF sentinel trigger is channel-validity (cal 0xC6501=3), instantaneous, NOT an inter-channel-delta check.
- [can-e4-intake-gates](reference_accord_can_e4_intake_gates.md) — full CAN 0xE4 RX chain to LKAS setpoint gp-0x69ae; all 5 gates in FUN_00052676 are comms-health, NONE torque-magnitude.
- [★ state4-ratchet-and-gp67fa-state-graph](reference_accord_state4_ratchet_and_gp67fa_state_graph.md) — gp-0x67fa SM fully mapped; state 4 IS reachable mid-drive; the governor magnitude-ratchet writes back and is self-sustaining across cycles.
- [arb-neardeadband-sign-latch](reference_accord_arb_neardeadband_sign_latch.md) — deadband(102) + same-sign latch in FUN_00028ea6; inert during steady hold but with a real periodic-reset pathway via STEER_STATUS.

## Cal / table specifics
- [c6664-lerp-b-envelope](reference_c6664_lerp_b_envelope.md) — cal 0xC6664 is the LERP_B envelope; inline-check-A reads gp-0x6db0/gp-0x6db8, not 0xC6664.
- [v40-governor-slew-step-65535-no-overflow](reference_accord_v40_governor_slew_step_65535_no_overflow.md) — V40's STEP=65535 does not overflow; it makes the slew instantaneous, defeating rate limiting.
- [v40-adaptive-cap-flatten-shadow-and-limp-path](reference_accord_v40_adaptive_cap_flatten_shadow_and_limp_path.md) — flattening the cap table doesn't break the shadow check or the LERP, but pins the limp-mode paths to the table MAX.
