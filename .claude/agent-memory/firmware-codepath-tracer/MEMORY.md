# Firmware Codepath Tracer - Memory Index

## 2026-08-20 the f0 dose-floor: is ANY non-gain lever big enough? (`damphunt round 4`)
- [🛑🛑★★★★★ f0 linear-in-gain retrodiction OVER-predicts 5-8x (direction right, magnitude wrong); governor=nonlinear slew limiter, comp-add=static LERP, NEITHER a tunable filter; working synthesis: gain's power is that it's the only lever changing PHYSICAL torque amplitude, re-linearizing multiple amplitude-dependent nonlinearities at once — a fixed single-branch filter structurally can't replicate that](reference_accord_f0_dose_floor_and_common_path_structure_search.md)

## 2026-08-20 V103 probe build spec, TRUE FINAL (`damphunt round 3` cont'd, msg 984096da)
- [★★★★★ TRUE FINAL bit map — **b3**=sign(gp-0x3680) (D's sign, NEW), b7/b6/b5/b4 ALL unchanged from V102 (only 1 bit changes total). Identity: b3 now TOGGLES where V101/V102 pinned it constant — better than duty-comparison, scorer MUST require b3 to vary. `ld.w -0x3680,gp,r6`=`24 37 81 c9` cave-verified.](reference_accord_v103_probe_bitmap_final_and_identity_exhaustion.md)

## 2026-08-20 D-term/pump-hunt + driver-side inertia, V103 ratchet half (`damphunt round 3`, `ratchet-inertia`)
- [🛑🛑★★★★★ SETTLED (2 corrections, both in-file): gp-0x6752 = −1, not +1. GATE2 uses a NON-canonical sign convention (verified vs actual Re(Z) code) — combining both flips recovers GATE2's ORIGINAL finding: D PUMPS, P/I DAMP at 6-9Hz. r24/r26 pumping (ratchet-inertia, correct convention throughout) UNAFFECTED, stands.](reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal.md)
- [★★★★★ D pumps/P+I damp/net damping IS CORRECT (an intermediate same-day reversal was itself wrong, now retracted) — provenance-chase stands: "D damps 16-35Hz" (STATE §8.2) traces to a GATE2 table that explicitly declines the grinding bands, still unsourced for 16-35Hz.](reference_accord_dterm_grindband_unresolved_and_pid_net_damping.md)
- [★★★★ r24/r26 phase-lever CLOSED (no filter structure exists, verified 3-way) but NOT exonerated as source; comparator probe candidates (gp-0x3680 D_state, gp-0x6ada/6adc mirrors, gp-0x6806) GATE-1-clean.](reference_accord_pump_hunt_comparator_probe_candidates.md)
- [🛑 RETRACTED: P is the DOMINANT DAMPER, not the pump (see gp6752 file's 2nd correction). Structural fact that survives: P is 0° own-phase, the most RELIABLE classification of the three terms.](reference_accord_pterm_is_the_most_reliable_pump_and_needs_no_new_probe_state.md)
- [🛑🛑★★★★★ gp-0x6b26 REFUTED as actionable: real+live but wrong-signed (dissipative), too small (~15-18%), CLOSED both directions on-car (V94 abort).](reference_accord_driver_side_inertia_hypothesis_refuted_synthesis.md)
- [🛑★★★★ r24/r26 = the ACTUAL driver-torque candidate; Re(Z) est. now resolved PUMPING (−431..−1294ct) now gp-0x6752 is known −1 — see the resolution entry above.](reference_accord_r24r26_driver_torque_lane_reZ_estimate.md)

## 2026-08-20 V101/V102 ~20-23Hz resonance hunt (`damphunt round 2`)
- [⭐🛑★★★★★ REQUEST does NOT echo the LKAS command (FUN_00026c80/FUN_00025c32, different param_1 field); mechanism pinned on gp-0x4f60 re-linearizing f' + FUN_000352b4's LERP at once; dead biquad beats 0xC63AC's kill](reference_accord_v101_v102_resonance_mechanism_and_biquad_direction.md)

## 2026-08-19 Kd priced + damping-lever hunt (`pidtrace`, `damphunt`)
- [🛑★★★★★ Header-vs-Y[0] SETTLED; full D-branch instruction trace + dual-method freq response; Re(Z) contradicts "D damps 16-35Hz"; Kd likely affects MANUAL steering too](reference_accord_kd_pid_dterm_priced_and_manual_gate.md)
- [🛑🛑★★★★★ FULL-LOOP Bode sum on 0xC63AC: raising it predicts Q/\|L\| WORSE — reverses same-day #1-bet ranking](reference_accord_c63ac_full_loop_bode_sum_net_negative.md)
- [🛑🛑★★★★★ Dead biquad in FUN_000352b4: ζ≈0.65, ~42.3Hz@1kHz, virgin, armed by SAME reversal-counter threshold (gp-0x671a≥5) as 18-21Hz ringing](reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md)
- [★★★★ CLOSES gp-0x6abe live/pinned 3-way contradiction (LIVE); gp-0x6a5e="driver torque" flagged SUPERSEDED (voted SPEED)](reference_accord_gp6abe_live_triple_confirmed_and_gp6a5e_mislabel_flag.md)
- [🛑🛑★★★★★ gp-0x6b26/0xCBE74 CLOSED BOTH DIRECTIONS — V93/V94 DOWN aborted ("vibrated the entire car"); +518/+565ct REAL damping removed. V101 runs V92's x1.5-engaged config](reference_accord_gp6b26_closed_both_directions_v94_aborted.md)

## 2026-08-13 V100/PID tables/rack/6ad6 terms (`tracer-6ad6-terms`, `builder-v100`, `tracer-rack-ratio`, `tracer-c63ae`, `tracer-arms`, `tracer-fprime`)
- [🛑🛑★★★★★ V100's RUNG A/D′ correctly coded ⇒ `d(b5)=d(b6)=0` is a null on the HYPOTHESIS, not the gate](reference_accord_v100_rungs_proven_and_pid_gain_tables.md) · [⭐ `tp`/`gp` set by ONE idiom @`0x140C4`–`0x140D6` ⇒ tp as live as gp](reference_accord_tp_init_and_gp6b94_shadow.md)
- [🛑🛑★★★★★ `0xC6200`=8192 clamps `gp-0x6ad6` INSIDE the PID ⇒ zeroes P/I/D sensitivity to `gp-0x6b70`](reference_accord_c6200_clamps_gp6ad6_inside_the_pid.md) · [★★★★★ `iVar6` REGISTER-ONLY, fixed 1kHz call order ⇒ ZERO-SKEW](reference_accord_ivar6_register_only_and_the_1khz_call_order.md)
- [🛑🛑★★★★★ `0xC63AE` "+28%" is a LEVEL shift vs an AC-calibrated bracket — below V85's not-felt 1.088](reference_accord_c63ae_dose_is_a_level_not_an_ac_change.md) · [Aggregator = 10 add, ZERO multiplies; 427 RECTIFIED understates 6-9Hz 4.86×](reference_accord_aggregator_is_unweighted_and_427_rectification_costs_4.9x.md)
- [⭐⭐★★★★★ Stock `0xC40D0`/`0xC63AC` BIT-IDENTICAL α (0.099609375) — V97 BROKE IT](reference_accord_c40d0_c63ac_exact_alpha_match_v97_broke_it.md) · [🛑 `0xC40BC` is a RATE KNEE, not relay hardness](reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness.md)
- [🛑🛑★★★★★ REQUEST arm ZERO cal cells + ACTIVE SHADOW-LOCKSTEP @`gp-0x4cfa`](reference_accord_request_arm_shadow_lockstep_and_no_cal_cells.md) · [★★★★★ `0xC63AE` only ARM-AGNOSTIC lever, VIRGIN](reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap.md)
- [🛑🛑★★★★★ THREE of 8 `gp-0x6ad6` terms ≡0; budget 17,152 = 2.09×, not ~12×](reference_accord_gp6ad6_eight_terms_and_the_reachability_budget.md) · [🛑🛑★★★★★ NO symmetric notch table; `0xC6B64-C6B98` IS partial rack-ratio compensation; `gp-0x6a10` = ABSOLUTE ANGLE](reference_accord_rack_ratio_c6b64_is_absolute_angle_and_no_notch_exists.md)
- [🛑🛑★★★★★ 4× reaches `gp-0x6b4c` ONLY (r0 into term 0 @`0x2b52a`); UNSATURATED end to end](reference_accord_4x_gain_feeds_6b4c_not_term0_and_the_struct_offset_map.md)
- [⭐🛑★★★★★ Stage-2 knot edit ("H2") = exactly `g` on segs 5→6/6→7/7→8, 1.000 below X[5], every speed 0-120km/h; no step, PROVEN](reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever.md)

## 2026-08-12 the 6-9Hz loop, PID phase, gates, V97 (`fw-loop`, `fw-levers`, `fw-return`, `lane-weights-6bf`, `c63a6-gate-trace`, `LerpKnots`, `close-the-sign`)
- [🛑🛑★★★★★ PATH-2 BRACKET: enters as `B=1+Q`, not in series; inversion iff \|Q\|<1 AND cos(arg Q)<−\|Q\|](reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop.md) · [🛑🛑★★★★★ 6-9Hz loop IS the PID torque-tracking servo; firmware phase only −3..+10° ⇒ NOT a firmware pole](reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget.md)
- [🛑🛑★★★★★ EVERY rate limit on LKAS→motor path — `0xC6194` real, dead only bc partition `0xC4118` all-1](reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale.md) · [★★★★★ `0xC63AC` only PURE-LEAD lever: DC gain 1.0 ⇒ a POLE not a GAIN](reference_accord_c63ac_is_the_pure_lead_pole_lever.md)
- [🛑🛑★★★★★ lane↔weight map for FUN_00038148; `0xC63A0` INERT](reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation.md) · [🛑🛑★★★★ `0xC64DE` a BYTE + relaxation-oscillator HALF-PERIOD, not ramp ceiling](reference_accord_c64de_is_a_byte_oscillator_halfperiod.md)
- [🛑🛑★★★★★ REFUTED "PID lane is sole actuation route" — LKAS's lane is mode 0, never sees AUTH](reference_accord_two_lkas_routes_gp6b4c_bypasses_auth.md) · [🛑🛑★★★★★ NEW TRAP: `ep`-relative short-format aliasing — tool-zero w/ healthy nonzero count](reference_v850_ep_relative_short_format_aliasing_trap.md)
- [🛑🛑★★★★★ "return-centre" lane = RACK END-STOP CUSHION, STALL-armed, needs \|gp-0x6bf0\|>8878](reference_accord_return_centre_is_an_end_stop_cushion_not_centring.md) · [🛑🛑★★★★★ CORRECTS: dwell arms on \|gp-0x6b64\| > 1024](reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record.md)
- [★★★★★ NOTHING dissipates in micro regime — all 3 viscous terms gated off, explains Re(Z)<0 @6-9Hz](reference_accord_micro_regime_has_no_scheduled_dissipation.md) · [★★★★ Aggregator zero-reject window map — 8/11 lanes, widths DIFFER](reference_accord_aggregator_zero_reject_window_map.md)
- [★★★★★ NO-GO `0xC63A6` — Q3 splits open-loop sign vs unmeasured closed-loop L](reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split.md) · [tp-relative xref false-zero + `ld.hu` parity trap](reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12.md)
- [★★★★★ PID recomputed at 6-9Hz — P 3-5× less dominant, phase lag 3-5× larger than at 21Hz](reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan.md) — 🛑 RETRACTED, see [[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]]
- [★★★★★ `gp-0x6806` gate is CAN-command domain, not torque sensor](reference_accord_gp6806_gate_is_can_domain_not_torque_sensor.md) · [🛑 CORRECTS gp69b0: `FUN_0002a93a` DEAD CODE + live engagement-gate catalog](reference_accord_fun2a93a_dead_code_correction_and_engagement_gate_catalog.md)
- [★★★★★ `gp-0x6b70` probe spec — EXCLUSIVELY Path-2 (1W/1R)](reference_accord_gp6b70_probe_spec_path_separation_and_gate1.md) · [🛑🛑★★★★★ Six Path-2 lane weights censused — SIGN UNRESOLVED (blocking)](reference_accord_fun38148_six_weight_v95_candidate_census.md) · [★★★★★ `gp-0x67ac` resolved zero](reference_accord_gp67ac_resolved_zero_and_path1_always_live.md)
- [🛑🛑★★★★★ Stage-2 LERP NO runtime rescale ⇒ f′ swing 1.000×, not ≥10×](reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md) · [🛑🛑★★★★★ "RAM" LERP 100% FLASH-derived; f′≥0 ENFORCED at 3 ungated sites](reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg.md) · [`FUN_0003b8f6` cals = 3 floats+6 u16 Q-format, FIR is IDENTITY](reference_accord_fun3b8f6_cal_types_iir_phase_and_v86_gate_decode.md)

## 2026-08-11 V92/dampaxis, return-centre, PID anti-damper, V90 cave (`fw-dampaxis`, `fw-return`, `fw-driver-model`)
- [★★★★★ `gp-0x6abc`=raw motor rate; `gp-0x6bf0` CORRECTED (15+ readers)](reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication.md) · [openpilot DBC clearance: 330 live, never repoint](reference_accord_openpilot_dbc_repoint_clearance_2026-08-11.md)
- 🛑 [CORRECTS above: openpilot clearance ≠ bus clearance](reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md) — its "D damps 16-35Hz" line has NO SOURCE, see [[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]]
- 🛑🛑★★★★★ [NO LKAS-magnitude gate on return-centre; limiter = motor-rate-adaptive governor `0xC520C`](reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md) — ⚠ PARTLY SUPERSEDED [dual-term sign + dwell relay](reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization.md)
- 🛑🛑★★★★★ [`FUN_0003a382` D-term sole pumping term @7.79Hz per +1-assumed polarity](reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction.md) — 🛑 polarity assumption WRONG, see [[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]]. GATE-2 on `0xCBE74`/`6b26`: positive clearance. `docs/GATE2-2026-08-11-cbe74-independent.md`.
- 🛑🛑★★★★★ [`gp-0x6b4a`=2nd direct ungated LKAS term into `6ad6`; CORRECTS V41 "0xC6194 inert"](reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md) · [🛑🛑✅✅★★★★★ `0xCBE74` dose CANNOT trip DTC-0x1d while `0xC407E`=511](reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered.md)
- 🛑🛑★★★★★ [CRC blocks are a LINKED LIST — one `0xC4FFC` trailer covers all app code](reference_accord_crc_block_lookup_and_cave_hook_template.md) · 🛑🛑 [OWN DEFECT: cave payload shipped BIG-endian; register-indirect `clr1` writers Ghidra misses](reference_accord_v90_cave_gate1_census_and_hook_critical_section.md)
- [🛑🛑★★★★★ `FUN_0003b8f6` gate-FAIL zeros stale-not-fresh; polarity 0 passes silently](reference_accord_fun3b8f6_gatefail_stale_and_gp6c00_exact_flag.md)

## 2026-08-09/10 damping-axis, HF-selectivity, filter/cave band-pass arc
- 🛑🛑★★★★★ FactorB indexes rate not torque; torque arm DEAD. HF-selectivity: `0xC64C8` mode-2 PROVABLE NO-OP; NO disabled r24/r26 filter; `FUN_00038148` 6 lanes + `6a10`=abs angle. Grep `*factorb_index_selector*` / `*c64c8*` / `*r24_r26_pole*`.
- [🛑🛑★★★★★ `0xC63B4`=51 ⇒ BANDPASS 8.14Hz Q0.501; 3-tap FIR cannot notch](reference_accord_c63b4_8hz_bandpass_in_fun3b66a.md) · [🛑🛑★★★★★ Float twin blocks filter insertion at/below `gp-0x6b08`](reference_accord_shaper_float_twin_blocks_filter_insertion.md) · [choke point](reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor.md)
- [★★★★ `FUN_00041d56` 3×3 observer, ζ=0.975, not live](reference_accord_fun41d56_state_space_complex_poles.md) · [`gp-0x671a`=0 at creep ⇒ `gp-0x6abc`=4.7121ct/°/s](reference_accord_gp671a_creep_value_and_friction_lane_schedule.md) · [★★★★★ At creep both dampers OFF, r24/r26 gain MAX](reference_accord_creep_damping_dead_rate_gain_max.md)
- Mature, grep only: `0xC63B8` live-not-a-damper `*fun3b66a*`/`*c63b8*` · FOC bridge `ep`-relative + low-speed friction 5× `*foc_bridge_is_ep*`/`*lowspeed_gate_census*`

## 🛑 Own errors, corrected
- [Read a stock cal byte, reported as built-image value](feedback_own_error_stock_read_attributed_to_built_image.md).

## V87 lever census / V86 prep / FactorD / V83 telemetry
- [🛑🛑★★★★★ `andi` masks are STATE bitmasks not phase dividers — one 1kHz rate](reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md) · [★★★★★ `0xC63AC` 2nd phase-lag pole α≈0.0996, −23.63°@7.79Hz](reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table.md)
- [★★★★★ `0xC6C42`=4 real torque-RATE window, 1kHz](reference_accord_gp4f62_torque_rate_producer_and_c6c42_window.md) · [Lever A `sar` sites outside LKAS gate](reference_accord_lever_a_gate_structure_and_cal_double_equivalence.md)
- [🛑🛑★★★★★ `gp-0x6a10`=\|raw column angle\|; FactorD unreachable <35km/h](reference_accord_factord_six_family_map_and_1khz_lane_v84.md) · [`FUN_0003b8f6` REFUTED as biquad: dead 3-tap FIR; FRICTION relay + INERTIA damper](reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps.md)
- Mature, grep only: V81 engaged-only FactorC/E + mode24≡mode26 stock `*v81_engagement_impedance*`/`*mode24_mode26_stock*`

## How I must work
- 🛑 [SendMessage not plain text](feedback_use_sendmessage_not_plain_text.md) · [Grep build_v*_tva.py before any cal](feedback_check_build_scripts_before_proposing_cal_edit.md) · [Check own memory first + variable-reuse trap](feedback_check_own_memory_before_retracing_and_variable_reuse_trap.md)

## Accord TVA-A160 — MATURE, grep only (≈130 memories; topic → grep patterns)
- Friction/seed/angle/RAM/FOC (17): `*friction_lane*` `*gp6bd0_seed*` `*gp6408*` `*gp63fd_full*` `*mode10_inert*` `*gp69a4*` `*angle_position_scale*` `*smooth_angle_gain*` …
- Damper FactorC/E + r24/r26 (6): `*factorc_e*` `*fun34350*` `*task5_100hz*` `*gp6b26_friction*` `*near_centre*` — `FUN_00034350` axis = SPEED, 8 km/h dead zone.
- Motor control (7): `reference_accord_pwm_*` `*fun757a2*` `*gp6ab*` `*gp67a*` `*gp69b0*` — PWM 4 kHz; `gp-0x6abe` = 4.7121× col °/s.
- 7.5 Hz ratchet (6): `reference_accord_ratchet_*` `*fun36388*` `*gp68ad*` `*v72_levera*` `*rate_lane*` `*detector_gate*` — 7.793 Hz.
- Boost-amp (9): `reference_accord_boost_*` `*r24_gainb*` `*fun456a4*` `*common_mode_rate*` `*four_unprobed*` — blend RISING only.
- Angle/return-centre (4): `reference_accord_can_angle_*` `*gp6bbe*` `*gp6b9a*` `*rate_limiter_enum*`.
- `FUN_0003a382` (6): `reference_accord_fun3a382_*` `*c646c*` `*gp6b98_aggregator*` — PID real, resonance unfiltered. 🛑 polarity assumption in these files needs the gp6752 correction applied.
- Aggregator/arb (7): `reference_accord_aggregator_*` `*fun28ea6*` `*gp6ad4*` `*deadband_signgate*` `*gp6806*` `*r24_no_lkas*` `*gp683c*` — `6AF0` mutes `6ad4`.
- CAN RX/speed (10): `reference_accord_can_rx_*` `*low_speed_lockout*` `*c62ee*` `*gp6a5e*` `*steerstatus3*` `*d0xxx*` `*no_vehicle_speed*` — `gp-0x6a5e` = 64 ct/km/h voted speed.
- Timing/sensor (8): `reference_accord_state4_*` `*task5_rate*` `*pclk_40mhz*` `*dtc18*` `*torque_sensor_zero*` `*a160_sid30*` `*gp6a5e_voter*` `*gp67ac_agg*` — TASK5 100 Hz, …
- Damping/notch (6): `reference_accord_damping_*` `*notch_biquad*` `*r26_adaptive*` `*v61_taps*` `*governor_energy*` `*fun352b4*` — notch NEGATIVE.
- Cmd/clamps/shaper (15): `reference_accord_*shaper*` `*governor*` `*eme*` `*clamp*` `*lkas_path*` — shaper ±0x2000, governor max 4762.
- Decider/engage SM (11): `reference_accord_decider_*` `*engage_sm*` `*trampoline*` · CAN TX/UDS (14): `reference_accord_can_*` `*uds*` `*a160_*`. 🛑🛑 **`gp-0x1500` / `gp-0x14e0` ARE NOT FREE RAM — DO NOT USE THEM AS CAVE STATE.** This line previously advertised them as free; that was WRONG and is corrected 2026-08-20. Both are live slots in the 40-slot×8B I/O-mailbox registry at `0xb7260`, written via **table-dispatched pointers no static disp16/disp23/literal scan can see**. `gp-0x1500` is the CAN `0x326` RX buffer and **FAILED on-car** (V50P probe: nonzero 99.47 % of the drive) after passing BOTH static clearance methods; `gp-0x14fa` in the same registry **BRICKED V48B** — its high byte aliased a live monitor/DTC bitfield, slamming the wheel side to side on a parked car. `gp-0x1700` is unsafe too (caught only by the disp23 form). ⇒ **Static clearance is NOT sufficient for this region.** Use the scalar-bound method in `reference_accord_gate1_movea_gp_array_blindspot_and_scalar_bound.md` and probe any candidate live. Vetted alternatives: the write-only diag taps in `FUN_0003b66a` (`gp-0x6d08`/`gp-0x6d04`/`gp-0x6d00`/`gp-0x6de8`/`gp-0x6de4`), `gp-0x1100`, `gp-0x1300`, `gp-0x683c`. See [[reference-accord-b7260-io-mailbox-array]] and [[reference-accord-v48b-flashed-catastrophic-ram-collision]].
- `gp-0x4f60` V48B/50/52 (6): `reference_accord_gp4f60_*` `*v48b_*` `*v50_gp4f60*` `*fun2eda8*` `*v52_9lane*` · Misc (6): `*gain_a_*` `*a_ladder*` `*7hz_divider*` …

## C120/A030/TVA UDS+SA
- [TVA/Accord bootloader map+delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
