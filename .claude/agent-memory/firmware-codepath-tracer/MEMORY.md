# Firmware Codepath Tracer - Memory Index

## 2026-08-21 assist-map ROM source found, forks off the Stage-2 LERP (`V104-design` assist-map trace)
- [🛑🛑★★★★★ `gp-0x37fc[]`/`gp-0x37e8[]` (Path-1/`magnitude_6b86`/`gp-0x6b86`) DOES have a static ROM source — forks off the SAME `gp-0x373c[]`/`gp-0x3714[]` inside `FUN_000389ec` that the Stage-2 LERP (Path-2/`gp-0x6b70`) copies directly, both landing on `FUN_000382d8`'s mode+speed ROM records (`0xD6158`m24/`0xD7130`m26). `0xC6564`=0 CONFIRMED 3rd time, resolved as a separate feedback/gate side-channel, NOT the knot source (and confirmed NOT the off-by-0x1000 trap). 🛑🛑 No edit is both Path-1-scoped AND mode-conditional at once — the shared-ROM edit (mode-26-only) hits BOTH Path-1 and Path-2 at once (corrects `stage2_knot_edit`'s "blast radius = Stage-2 alone"); the Path-1-only lever (`cal 0xC6468`/`0xC6178`) is NOT mode-indexed at all.](reference_accord_assist_map_rom_source_found_and_shares_stage2_fork.md)

## 2026-08-21 r24/r26 live gain path, exact mode24/26 tables, engagement-conditional option, phase contradiction (`V104-design` r24/r26 trace)
- [🛑🛑★★★★★ Live gain = the DEFAULT mode/speed/rate LERP table (closes O27); all 4 override cal cells confirmed dead/starved. Mode24≡mode26 r24 tables read exact, byte-identical content, PHYSICALLY SEPARATE addresses ⇒ r24-only/mode-26-only edit is a genuine cal-only ENGAGEMENT-CONDITIONAL lever (r26 has none). 🛑🛑 229° phase gap between "r24/r26 pumps" (139.1°) and a same-day loop-ID figure (0.1173∠−89.9°) is UNRESOLVED — do not pick a sign for this lane until it closes.](reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy.md)

## 2026-08-20 FUN_00046ea6 DTC gate, PID's dead table, and the true `0xC64FA` census (`oscillation-detector` trace)
- [🛑🛑★★★★★ Verdict (a) not (b): FUN_00046ea6(5) tests bit5 of a DTC-confirmed-status OR-accumulator, reset periodically — NOT a permanent latch. PID's gainD_raw table CONFIRMED flat-at-1024 (resolves a prior flagged uncertainty) — zero effect from gp-0x671a at ANY value. NEW 4th consumer FUN_00035b20 feeds gp-0x69a0 straight into the dead-biquad function. 0xC64FA census: 18 real touches/5 functions (2 methods) incl. 10 in FUN_00025c32 that search_instructions completely missed — LANDMINE, wider than recorded.](reference_accord_fun46ea6_dtc_gate_pid_flat_table_and_c64fa_census.md)

## 2026-08-20 self-interference cancellation design + notch verdict (`self-interference-cancellation`)
- [★★★★★ Design: tap gp-0x6b98 (1-tick-old), inject in FUN_000352b4 @0x354d2, 2-pole resonator (ζ=0.0265) reusing dead-biquad state gp-0x3814/0x3818. **Verdict: notch is the better next build** — cancellation's selectivity is worth little, 7.79Hz is above neuromuscular bandwidth](reference_accord_selfinterference_cancellation_design_and_notch_verdict.md)
- [★★★★★ Fresh decompile FUN_000352b4/FUN_0003aa2c: NEW gp-0x6b82=biquad's raw input tap; 🛑 CORRECTS "clamp ±0x6400" — cal(0xC6200) SHARED w/ Path-2 PID ref clamp; full 8-lane aggregator zero-reject map; chain shares ONE 1kHz caller](reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp.md)
- [⚠ trap: `search_instructions` matches displacement TEXT not base register — adjudicate before any GATE-1 count](reference_v850_search_instructions_base_register_collision_trap.md)

## 2026-08-20 gp-0x671a gate / biquad-is-notch / V104 lag map / f0 dose-floor (`loop-lag-map`, `damphunt round 4`)
- [🛑🛑★★★★★ gp-0x671a ONE writer; dead-biquad arm AND r24/r26's third-arm gate on the SAME cal(0xC64FA)=5, read 0.000% true on V67/V68. CORRECTED same day: V103 repoints the arm to gp-0x6806 — biquad NOT starved, r24/r26 kill stands](reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26.md)
- [🛑🛑★★★★★ Biquad = NOTCH not low-pass; V103-as-flown (42.345Hz pole/55.225Hz zero) re-derived to 2dp; 23Hz/r=0.975 redesign VALIDATED; gp-0x381c LERP is FLAT (corner 1.56Hz, not 7Hz); q~0.1 pricing 10-80× below the bar](reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md)
- [🛑🛑★★★★★ Full 8/20/23/26Hz lag catalog; CORRECTS `FUN_00041464` 312.5Hz→1kHz; NEW live filter `0xC6382`/`gp-0x381c` gated near-inert; "speed up the tracker" TESTS BACKWARDS on the full-loop Bode sum](reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction.md)
- [🛑🛑★★★★★ f0-vs-gain retrodiction OVER-predicts 5-8×; governor/comp-add are NOT tunable filters; gain's power is being the ONLY lever that moves physical torque amplitude](reference_accord_f0_dose_floor_and_common_path_structure_search.md)

## 2026-08-20 D-term/pump-hunt, V103 ratchet+probe spec (`damphunt round 3`, `ratchet-inertia`)
- [🛑🛑★★★★★ SETTLED: gp-0x6752 = −1 not +1 — recovers GATE2's ORIGINAL finding: D PUMPS, P/I DAMP at 6-9Hz; r24/r26 pumping unaffected. (2 same-day reversals folded in/retracted, see file)](reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal.md)
- [★★★★★ TRUE FINAL V103 bit map — b3=sign(gp-0x3680), b7-b4 unchanged from V102 (1 bit changes); cave bytes verified](reference_accord_v103_probe_bitmap_final_and_identity_exhaustion.md)
- [★★★★ r24/r26 phase-lever CLOSED but not exonerated as source; probes GATE-1-clean](reference_accord_pump_hunt_comparator_probe_candidates.md) · [🛑🛑★★★★★ gp-0x6b26 REFUTED: wrong-signed, too small, CLOSED both directions (V94 abort)](reference_accord_driver_side_inertia_hypothesis_refuted_synthesis.md)
- [🛑★★★★ r24/r26 = the driver-torque candidate; Re(Z) PUMPING](reference_accord_r24r26_driver_torque_lane_reZ_estimate.md) · ["D damps 16-35Hz" traces to a GATE2 table declining the grinding bands — unsourced](reference_accord_dterm_grindband_unresolved_and_pid_net_damping.md)

## 2026-08-19/20 resonance hunt, Kd, dead biquad (`damphunt round 2`, `pidtrace`)
- [⭐🛑★★★★★ REQUEST does NOT echo the LKAS command; mechanism = gp-0x4f60 re-linearizing f' + FUN_000352b4's LERP at once](reference_accord_v101_v102_resonance_mechanism_and_biquad_direction.md)
- [🛑★★★★★ Header-vs-Y[0] SETTLED; Re(Z) contradicts "D damps 16-35Hz"; Kd likely affects MANUAL steering too](reference_accord_kd_pid_dterm_priced_and_manual_gate.md) · [🛑🛑★★★★★ FULL-LOOP Bode sum: raising 0xC63AC predicts WORSE](reference_accord_c63ac_full_loop_bode_sum_net_negative.md)
- [🛑🛑★★★★★ Dead biquad in FUN_000352b4: ζ≈0.65, ~42.3Hz@1kHz, virgin, armed by SAME gp-0x671a≥5 threshold as 18-21Hz ringing](reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md)
- [★★★★ CLOSES gp-0x6abe contradiction (LIVE); gp-0x6a5e "driver torque" SUPERSEDED](reference_accord_gp6abe_live_triple_confirmed_and_gp6a5e_mislabel_flag.md) · [🛑🛑★★★★★ gp-0x6b26/0xCBE74 CLOSED both directions — V93/V94 DOWN aborted](reference_accord_gp6b26_closed_both_directions_v94_aborted.md)

## 2026-08-13 V100/PID tables/rack/6ad6 terms (`tracer-6ad6-terms`, `builder-v100`, `tracer-rack-ratio`, `tracer-arms`, `tracer-fprime`)
- [🛑🛑★★★★★ V100's RUNG A/D′ correct ⇒ `d(b5)=d(b6)=0` is a null on the HYPOTHESIS not the gate](reference_accord_v100_rungs_proven_and_pid_gain_tables.md) · [⭐ `tp`/`gp` set by ONE idiom ⇒ tp as live as gp](reference_accord_tp_init_and_gp6b94_shadow.md)
- [🛑🛑★★★★★ `0xC6200`=8192 clamps `gp-0x6ad6` INSIDE the PID ⇒ zeroes P/I/D sensitivity](reference_accord_c6200_clamps_gp6ad6_inside_the_pid.md) · [★★★★★ `iVar6` REGISTER-ONLY, fixed 1kHz order ⇒ ZERO-SKEW](reference_accord_ivar6_register_only_and_the_1khz_call_order.md)
- [🛑🛑★★★★★ `0xC63AE` "+28%" is a LEVEL shift, below V85's not-felt bound](reference_accord_c63ae_dose_is_a_level_not_an_ac_change.md) · [Aggregator=10 add, ZERO multiplies; 427 RECTIFIED understates 6-9Hz 4.86×](reference_accord_aggregator_is_unweighted_and_427_rectification_costs_4.9x.md)
- [⭐⭐★★★★★ Stock `0xC40D0`/`0xC63AC` BIT-IDENTICAL α — V97 BROKE IT](reference_accord_c40d0_c63ac_exact_alpha_match_v97_broke_it.md) · [🛑 `0xC40BC` is a RATE KNEE not relay hardness](reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness.md)
- [🛑🛑★★★★★ REQUEST arm ZERO cal cells + ACTIVE SHADOW-LOCKSTEP](reference_accord_request_arm_shadow_lockstep_and_no_cal_cells.md) · [★★★★★ `0xC63AE` only ARM-AGNOSTIC lever, VIRGIN](reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap.md)
- [🛑🛑★★★★★ THREE of 8 `gp-0x6ad6` terms ≡0; budget 2.09×, not ~12×](reference_accord_gp6ad6_eight_terms_and_the_reachability_budget.md) · [🛑🛑★★★★★ NO symmetric notch table; `gp-0x6a10`=ABSOLUTE ANGLE](reference_accord_rack_ratio_c6b64_is_absolute_angle_and_no_notch_exists.md)
- [🛑🛑★★★★★ 4× reaches `gp-0x6b4c` ONLY; UNSATURATED end to end](reference_accord_4x_gain_feeds_6b4c_not_term0_and_the_struct_offset_map.md) · [⭐🛑★★★★★ Stage-2 "H2" = exactly `g` on segs 5-8, no step, PROVEN](reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever.md)

## 2026-08-12 the 6-9Hz loop, PID phase, gates, V97 (`fw-loop`, `fw-levers`, `fw-return`, `c63a6-gate-trace`, `LerpKnots`)
- [🛑🛑★★★★★ PATH-2 BRACKET enters as `B=1+Q` not in series; inversion iff \|Q\|<1 AND cos(arg Q)<−\|Q\|](reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop.md) · [🛑🛑★★★★★ 6-9Hz loop IS the PID torque servo; phase only −3..+10° ⇒ NOT a firmware pole](reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget.md)
- [🛑🛑★★★★★ EVERY rate limit on LKAS→motor — `0xC6194` real, dead only bc partition `0xC4118` all-1](reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale.md) · [★★★★★ `0xC63AC` PURE-LEAD lever: DC gain 1.0 ⇒ POLE not GAIN](reference_accord_c63ac_is_the_pure_lead_pole_lever.md)
- [🛑🛑★★★★★ lane↔weight map for FUN_00038148; `0xC63A0` INERT](reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation.md) · [🛑🛑★★★★ `0xC64DE` BYTE + relaxation-oscillator HALF-PERIOD](reference_accord_c64de_is_a_byte_oscillator_halfperiod.md)
- [🛑🛑★★★★★ REFUTED "PID lane is sole actuation route" — LKAS lane is mode 0, never sees AUTH](reference_accord_two_lkas_routes_gp6b4c_bypasses_auth.md) · [🛑🛑★★★★★ TRAP: `ep`-relative short-format aliasing — tool-zero w/ healthy nonzero count](reference_v850_ep_relative_short_format_aliasing_trap.md)
- [🛑🛑★★★★★ "return-centre" = RACK END-STOP CUSHION, STALL-armed](reference_accord_return_centre_is_an_end_stop_cushion_not_centring.md) · [🛑🛑★★★★★ CORRECTS: dwell arms on \|gp-0x6b64\|>1024](reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record.md)
- [★★★★★ NOTHING dissipates in micro regime — explains Re(Z)<0 @6-9Hz](reference_accord_micro_regime_has_no_scheduled_dissipation.md) · [★★★★ Aggregator zero-reject map — 8/11 lanes, widths DIFFER](reference_accord_aggregator_zero_reject_window_map.md) · [★★★★★ NO-GO `0xC63A6`](reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split.md)
- [★★★★★ PID recomputed at 6-9Hz — P less dominant, phase lag larger than 21Hz](reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan.md) — 🛑 RETRACTED, see [[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]]
- [★★★★★ `gp-0x6806` gate is CAN-command domain not torque sensor](reference_accord_gp6806_gate_is_can_domain_not_torque_sensor.md) · [🛑 CORRECTS gp69b0: `FUN_0002a93a` DEAD CODE](reference_accord_fun2a93a_dead_code_correction_and_engagement_gate_catalog.md)
- [★★★★★ `gp-0x6b70` probe spec, EXCLUSIVELY Path-2](reference_accord_gp6b70_probe_spec_path_separation_and_gate1.md) · [🛑🛑★★★★★ Six Path-2 lane weights censused — SIGN UNRESOLVED](reference_accord_fun38148_six_weight_v95_candidate_census.md) · [★★★★★ `gp-0x67ac` resolved zero](reference_accord_gp67ac_resolved_zero_and_path1_always_live.md)
- [🛑🛑★★★★★ Stage-2 LERP NO runtime rescale ⇒ f′ swing 1.000×](reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md) · [🛑🛑★★★★★ "RAM" LERP 100% FLASH-derived; f′≥0 ENFORCED](reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg.md)

## 2026-08-11 V92/dampaxis, return-centre, PID anti-damper, V90 cave (`fw-dampaxis`, `fw-return`, `fw-driver-model`)
- [★★★★★ `gp-0x6abc`=raw motor rate; `gp-0x6bf0` CORRECTED](reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication.md) — 🛑 openpilot DBC clearance ≠ bus clearance, see [[reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11]]
- [🛑🛑★★★★★ NO LKAS-magnitude gate on return-centre; limiter = motor-rate-adaptive governor `0xC520C`](reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md) — ⚠ PARTLY SUPERSEDED, see [[reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization]]
- [🛑🛑★★★★★ `FUN_0003a382` D-term sole pumping term @7.79Hz — polarity WRONG, superseded by gp6752 above. GATE-2 on `0xCBE74`/`6b26`: positive clearance](reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction.md)
- [🛑🛑★★★★★ `gp-0x6b4a`=2nd direct ungated LKAS term into `6ad6`; CORRECTS V41 "0xC6194 inert"](reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md) · [🛑🛑✅✅★★★★★ `0xCBE74` CANNOT trip DTC-0x1d while `0xC407E`=511](reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered.md)
- [🛑🛑★★★★★ CRC blocks are a LINKED LIST — one `0xC4FFC` trailer covers all app code](reference_accord_crc_block_lookup_and_cave_hook_template.md) · 🛑🛑 [OWN DEFECT: cave shipped BIG-endian; register-indirect `clr1` writers Ghidra misses](reference_accord_v90_cave_gate1_census_and_hook_critical_section.md)
- [🛑🛑★★★★★ `FUN_0003b8f6` gate-FAIL zeros stale-not-fresh; polarity 0 passes silently](reference_accord_fun3b8f6_gatefail_stale_and_gp6c00_exact_flag.md)

## 2026-08-09/10 damping-axis, HF-selectivity, filter/cave band-pass; V87 lever census / FactorD (V83)
- 🛑🛑★★★★★ FactorB indexes rate not torque; torque arm DEAD. `0xC64C8` mode-2 NO-OP; NO disabled r24/r26 filter. Grep `*factorb_index_selector*`/`*c64c8*`/`*r24_r26_pole*`.
- [🛑🛑★★★★★ `0xC63B4`=51 ⇒ BANDPASS 8.14Hz Q0.501; 3-tap FIR cannot notch](reference_accord_c63b4_8hz_bandpass_in_fun3b66a.md) · [🛑🛑★★★★★ Float twin blocks filter insertion at/below `gp-0x6b08`](reference_accord_shaper_float_twin_blocks_filter_insertion.md)
- [★★★★ `FUN_00041d56` 3×3 observer, ζ=0.975, not live](reference_accord_fun41d56_state_space_complex_poles.md) · [★★★★★ At creep both dampers OFF, r24/r26 gain MAX](reference_accord_creep_damping_dead_rate_gain_max.md)
- [🛑🛑★★★★★ `andi` masks are STATE bitmasks not phase dividers — one 1kHz rate](reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md) · [🛑🛑★★★★★ `gp-0x6a10`=\|raw column angle\|; FactorD unreachable <35km/h](reference_accord_factord_six_family_map_and_1khz_lane_v84.md)
- Mature, grep only: `0xC63B8`/FOC-`ep`/low-speed-friction `*fun3b66a*` `*foc_bridge_is_ep*` `*lowspeed_gate_census*`; `FUN_0003b8f6` refuted-biquad `*fun3b8f6*`; Lever A `sar` `*lever_a_gate*`; V81 FactorC/E+mode24≡26 `*v81_engagement_impedance*` `*mode24_mode26_stock*`

## Own errors, corrected / How I must work
- [Read a stock cal byte, reported as built-image value](feedback_own_error_stock_read_attributed_to_built_image.md).
- 🛑 [SendMessage not plain text](feedback_use_sendmessage_not_plain_text.md) · [Grep build_v*_tva.py before any cal](feedback_check_build_scripts_before_proposing_cal_edit.md) · [Check own memory first + variable-reuse trap](feedback_check_own_memory_before_retracing_and_variable_reuse_trap.md)

## Accord TVA-A160 — MATURE, grep only (≈130 memories; topic → grep patterns)
- Friction/seed/angle/RAM/FOC (17): `*friction_lane*` `*gp6bd0_seed*` `*gp6408*` `*gp63fd_full*` `*mode10_inert*` `*gp69a4*` `*angle_position_scale*` `*smooth_angle_gain*` …
- Damper FactorC/E + r24/r26 (6): `*factorc_e*` `*fun34350*` `*task5_100hz*` `*gp6b26_friction*` `*near_centre*` — `FUN_00034350` axis=SPEED, 8km/h dead zone.
- Motor control (7): `reference_accord_pwm_*` `*fun757a2*` `*gp6ab*` `*gp67a*` `*gp69b0*` — PWM 4kHz; `gp-0x6abe`=4.7121× col °/s.
- 7.5Hz ratchet (6): `reference_accord_ratchet_*` `*fun36388*` `*gp68ad*` `*v72_levera*` `*rate_lane*` `*detector_gate*` — 7.793Hz.
- Boost-amp (9): `reference_accord_boost_*` `*r24_gainb*` `*fun456a4*` `*common_mode_rate*` `*four_unprobed*` — blend RISING only.
- Angle/return-centre (4): `reference_accord_can_angle_*` `*gp6bbe*` `*gp6b9a*` `*rate_limiter_enum*`.
- `FUN_0003a382` (6): `reference_accord_fun3a382_*` `*c646c*` `*gp6b98_aggregator*` — PID real, resonance unfiltered. 🛑 polarity needs gp6752 correction applied.
- Aggregator/arb (7): `reference_accord_aggregator_*` `*fun28ea6*` `*gp6ad4*` `*deadband_signgate*` `*gp6806*` `*r24_no_lkas*` `*gp683c*` — `6AF0` mutes `6ad4`.
- CAN RX/speed (10): `reference_accord_can_rx_*` `*low_speed_lockout*` `*c62ee*` `*gp6a5e*` `*steerstatus3*` `*d0xxx*` `*no_vehicle_speed*` — `gp-0x6a5e`=64 ct/km/h voted speed.
- Timing/sensor (8): `reference_accord_state4_*` `*task5_rate*` `*pclk_40mhz*` `*dtc18*` `*torque_sensor_zero*` `*a160_sid30*` `*gp6a5e_voter*` `*gp67ac_agg*` — TASK5 100Hz.
- Damping/notch (6): `reference_accord_damping_*` `*notch_biquad*` `*r26_adaptive*` `*v61_taps*` `*governor_energy*` `*fun352b4*` — notch NEGATIVE.
- Cmd/clamps/shaper (15): `reference_accord_*shaper*` `*governor*` `*eme*` `*clamp*` `*lkas_path*` — shaper ±0x2000, governor max 4762.
- Decider/engage SM (11): `reference_accord_decider_*` `*engage_sm*` `*trampoline*` · CAN TX/UDS (14): `reference_accord_can_*` `*uds*` `*a160_*`.
- 🛑🛑 **`gp-0x1500`/`gp-0x14e0`/`gp-0x14fa`/`gp-0x1700` ARE POISON, NOT FREE RAM** — live I/O-mailbox slots at `0xb7260` (table-dispatched, invisible to static scans). `gp-0x1500` FAILED on-car (V50P) despite passing both static methods; `gp-0x14fa` BRICKED V48B (aliased a monitor/DTC bitfield). Use the scalar-bound method (`reference_accord_gate1_movea_gp_array_blindspot_and_scalar_bound.md`) + probe live. Alternatives: `FUN_0003b66a` write-only taps, `gp-0x1100`, `gp-0x1300`, `gp-0x683c`. See [[reference-accord-b7260-io-mailbox-array]], [[reference-accord-v48b-flashed-catastrophic-ram-collision]].
- `gp-0x4f60` V48B/50/52 (6): `reference_accord_gp4f60_*` `*v48b_*` `*v50_gp4f60*` `*fun2eda8*` `*v52_9lane*` · Misc (6): `*gain_a_*` `*a_ladder*` `*7hz_divider*` …

## C120/A030/TVA UDS+SA
- [TVA/Accord bootloader map+delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
