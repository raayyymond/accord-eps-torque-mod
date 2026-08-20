# Firmware Codepath Tracer - Memory Index

## 2026-08-19 Kd priced; PID table header-vs-Y[0] settled (`pidtrace`)
- [🛑★★★★★ Header-vs-Y[0] SETTLED (both docs right); full D-branch instruction trace + dual-method freq response; Re(Z) contradicts "D damps 16-35Hz"; Kd likely affects MANUAL steering too (same gate as aggregator)](reference_accord_kd_pid_dterm_priced_and_manual_gate.md)

## 2026-08-19 V101 self-oscillation damping-lever hunt (`damphunt`)
- [🛑🛑★★★★★ FULL-LOOP Bode sum on 0xC63AC: raising it predicts Q/|L| moving WORSE not better, robust across attribution/anchor -- REVERSES this agent's own earlier same-day #1-bet ranking](reference_accord_c63ac_full_loop_bode_sum_net_negative.md)
- [🛑🛑★★★★★ A dead biquad in FUN_000352b4, pole/response computed: ζ≈0.65, ~42.3Hz @1kHz, virgin (grep-confirmed), armed by the SAME reversal-counter threshold (gp-0x671a≥5) that detects 18-21Hz ringing](reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md)
- [★★★★ CLOSES the gp-0x6abe live/pinned 3-way contradiction (3rd independent trace, all agree LIVE); flags gp-0x6a5e="driver torque" in the damping/friction/torque-gates file as SUPERSEDED (it's voted SPEED)](reference_accord_gp6abe_live_triple_confirmed_and_gp6a5e_mislabel_flag.md)
- [🛑🛑★★★★★ gp-0x6b26/0xCBE74 is CLOSED BOTH DIRECTIONS — V93/V94 tried DOWN, operator ABORTED the drive ("vibrated the entire car"); measured +518/+565ct REAL 6-9Hz damping removed. Current V101 runs V92's x1.5-engaged config, not stock](reference_accord_gp6b26_closed_both_directions_v94_aborted.md)

## 2026-08-13 V100 rungs PROVEN + the PID gain tables (`tracer-6ad6-terms`)
- [🛑🛑★★★★★ V100's RUNG A/D′ are correctly coded (nibble **0xE=GE**, 32-bit abs, no guard) ⇒ `d(b5)=d(b6)=0` is a null on the **HYPOTHESIS**, NOT the V64/V68 gate signature — controls share the same accumulator AND store](reference_accord_v100_rungs_proven_and_pid_gain_tables.md)

## 2026-08-13 `f′` IS a lever — the Stage-2 knot edit (`tracer-fprime`)
- [⭐🛑★★★★★ Cal-only knot edit ("H2", 84 B) = exactly `g` on segs 5→6/6→7/7→8, exactly 1.000 below `X[5]`, at EVERY speed 0-120 km/h; **no step, PROVEN**; split is AMPLITUDE, **no …

## 2026-08-13 ALL EIGHT terms into `gp-0x6ad6` (`tracer-6ad6-terms`)
- [🛑🛑★★★★★ **THREE of 8 terms ≡0** (`6b4a`; `6bbc`/`6bce` have **NO WRITER**, 3 methods); budget **17,152 = 2.09×**, not ~12× — sizing vs the zero-reject WINDOW is a GATE-3 error](reference_accord_gp6ad6_eight_terms_and_the_reachability_budget.md)

## 2026-08-13 the variable-ratio rack question (`tracer-rack-ratio`)
- [🛑🛑★★★★★ NO symmetric notch table exists (2 methods); `0xC6B64`-`0xC6B98` IS partial rack-ratio compensation; `gp-0x6a10` IS ABSOLUTE ANGLE (offset clamped ±13.0° by `0xC633A`=130 @`0x3fc36`)](reference_accord_rack_ratio_c6b64_is_absolute_angle_and_no_notch_exists.md)

## 2026-08-13 the 4× gain vs term 0 — EXONERATED, **TERM 0 ≡ 0** (`tracer-4x-to-term0`)
- [🛑🛑★★★★★ The 4× reaches **`gp-0x6b4c` ONLY** (hard `r0` into term 0 @`0x2b52a`); UNSATURATED end to end](reference_accord_4x_gain_feeds_6b4c_not_term0_and_the_struct_offset_map.md)

## 2026-08-13 V100 build certification (`builder-v100`)
- [⭐★★★★★ `tp`/`gp` set by ONE idiom at `0x140C4`–`0x140D6` ⇒ **tp is as live as gp**](reference_accord_tp_init_and_gp6b94_shadow.md) — 🛑 Ghidra never analysed `0x140CE`. ⊕ `gp-0x6b94` …

## 2026-08-13 the `gp-0x6ad6` saturation (`tracer-6ad6`)
- [🛑🛑★★★★★ `0xC6200`=8192 clamps **`gp-0x6ad6` INSIDE the PID** @`0x3a7a2` ⇒ `|ref|≥8192` zeroes P, I **and** D sensitivity to `gp-0x6b70`](reference_accord_c6200_clamps_gp6ad6_inside_the_pid.md)
- [★★★★★ `iVar6` REGISTER-ONLY; fixed 1 kHz call order `0x22416→0x225f6→0x22676→0x22696→0x226a0` ⇒ cave recompute is ZERO-SKEW](reference_accord_ivar6_register_only_and_the_1khz_call_order.md)

## 2026-08-13 `0xC63AE` priced end to end — NO-GO at 2048 (`tracer-c63ae`)
- [🛑🛑★★★★★ The "+28 %" is a **LEVEL** shift scored against an **AC-calibrated** bracket — delivered only 1.021–1.135, at/below V85's not-felt 1.088](reference_accord_c63ae_dose_is_a_level_not_an_ac_change.md)
- [🛑🛑★★★★★ Aggregator = **10 `add`, ZERO multiplies** ⇒ unweighted 11-term sum ⇒ φ = Path2/total; **427 RECTIFIED understates 6-9 Hz by 4.86×**](reference_accord_aggregator_is_unweighted_and_427_rectification_costs_4.9x.md)

## 2026-08-13 the MODEL↔ACTUAL mismatch (`tracer-arms`)
- [⭐⭐★★★★★ Stock encodes a **BIT-IDENTICAL α** between `0xC40D0` and `0xC63AC` (both 0.099609375) — and **V97 BROKE IT**](reference_accord_c40d0_c63ac_exact_alpha_match_v97_broke_it.md)
- [🛑★★★★★ `0xC40BC` is a **RATE KNEE**, not relay hardness — does NOT scale magnitude](reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness.md) — V85's 600→6000 moved the knee …

## 2026-08-13 V99 lever set, three observer arms (`tracer-arms`)
- [🛑🛑★★★★★ REQUEST arm has **ZERO cal cells** and an ACTIVE SHADOW-LOCKSTEP at `gp-0x4cfa`](reference_accord_request_arm_shadow_lockstep_and_no_cal_cells.md) — GATE-1 hazard; …
- [★★★★★ `0xC63AE` = the only **ARM-AGNOSTIC** lever, multiplies `|iVar6|` AFTER the difference](reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap.md) — VIRGIN, 1R/0W. 🛑 …

## 2026-08-12 Stage-2 LERP knots (`LerpKnots`)
- [🛑🛑★★★★★ Stage-2 LERP has NO runtime rescale ⇒ `f′` swing **1.000×, not ≥10×**](reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md) — route 80 ⇒ `|iVar6| ≤ ~6,900`, …

## 2026-08-12 closing the sign (`close-the-sign`)
- [🛑🛑★★★★★ The "RAM" LERP is 100% FLASH-derived; **`f′ ≥ 0` ENFORCED at 3 ungated sites**](reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg.md) — closes OPEN-loop sign …
- [🛑🛑★★★★★ `FUN_0003b8f6` cals = **3 floats + 6 u16 Q-format**, not "8 floats"; the FIR is an IDENTITY](reference_accord_fun3b8f6_cal_types_iir_phase_and_v86_gate_decode.md) — …

## 2026-08-12 the 6-9 Hz loop, end to end (`fw-loop`)
- [🛑🛑★★★★★ THE PATH-2 BRACKET — Path 2 enters as `B = 1 + Q`, NOT in series; inversion iff `|Q|<1` AND `cos(arg Q) < −|Q|`](reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop.md)
- [🛑🛑★★★★★ The 6-9 Hz loop is the PID torque-tracking servo; firmware phase only −3..+10° ⇒ 7.8 Hz CANNOT be a firmware pole](reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget.md)
- [🛑🛑★★★★★ EVERY rate limit on the LKAS→motor path — `0xC6194` IS real, dead only because partition `0xC4118` is all-1](reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale.md)

## 2026-08-12 V97 cell ledger (`fw-levers`)
- [★★★★★ `0xC63AC` = the only PURE-LEAD lever: DC gain 1.000000 ⇒ a POLE not a GAIN](reference_accord_c63ac_is_the_pure_lead_pole_lever.md) — 102→205 = +12.6° @7.79Hz; VIRGIN. 🛑 1.38× …
- [🛑🛑★★★★★ THE lane↔weight map for FUN_00038148](reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation.md) — reconciles `0xC63A0` INERT; `gp-0x6b4e`≡0 ⇒ `0xC63A8` …
- [🛑🛑★★★★ `0xC64DE` is a BYTE and a relaxation-oscillator HALF-PERIOD, not a ramp ceiling](reference_accord_c64de_is_a_byte_oscillator_halfperiod.md) — `ld.bu` parity trap; 8/16 …

## 2026-08-12 V97 sole-route test (`fw-return`)
- [🛑🛑★★★★★ REFUTED "PID lane is the sole actuation route" — LKAS's lane is mode 0, never sees AUTH](reference_accord_two_lkas_routes_gp6b4c_bypasses_auth.md) — AUTH ramp header is …
- [🛑🛑★★★★★ NEW TRAP CLASS: `ep`-relative short-format aliasing — a tool-zero with a HEALTHY NON-ZERO COUNT](reference_v850_ep_relative_short_format_aliasing_trap.md) — recipe + …

## 2026-08-12 V97 return-to-centre crux (`fw-return`)
- [🛑🛑★★★★★ The "return-centre" lane is a RACK END-STOP CUSHION](reference_accord_return_centre_is_an_end_stop_cushion_not_centring.md) — STALL-armed, needs |gp-0x6bf0|>8878; frozen …
- [🛑🛑★★★★★ CORRECTS 2026-08-11: dwell arms on |gp-0x6b64| **>** 1024](reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record.md) — EXONERATES the `byte7 b6` …
- [★★★★★ NOTHING dissipates in the micro regime — all 3 viscous terms gated off](reference_accord_micro_regime_has_no_scheduled_dissipation.md) — explains Re(Z)<0 @6-9Hz.
- [★★★★ Aggregator zero-reject window map — 8 of 11 lanes, widths DIFFER](reference_accord_aggregator_zero_reject_window_map.md) — 🛑 only 2 of 8 ceilings verified.

## 2026-08-12 0xC63A6 GATE trace, NO-GO (`c63a6-gate-trace`)
- [★★★★★ NO-GO on `0xC63A6` — Q3 splits open-loop sign vs unmeasured closed-loop `L`](reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split.md) — reusable across all six …
- [tp-relative `get_xrefs_to` false-zero + `ld.hu` parity trap on the neighbour cell](reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12.md) — use a both-parity raw …

## 2026-08-11/12 lane weights, PID phase, engagement gates (`lane-weights-6bf`)
- [★★★★★ PID recomputed at 6-9Hz — P 3-5× less dominant, phase lag 3-5× larger than at 21Hz](reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan.md)
- [★★★★★ `gp-0x6806`'s gate is CAN-command domain, not the torque sensor](reference_accord_gp6806_gate_is_can_domain_not_torque_sensor.md) — `0xC64A3`=1 arms both halves.
- [🛑 CORRECTS gp69b0: `FUN_0002a93a` is DEAD CODE + live engagement-gate catalog](reference_accord_fun2a93a_dead_code_correction_and_engagement_gate_catalog.md)
- [★★★★★ `gp-0x6b70` probe spec — EXCLUSIVELY Path-2 (1W/1R)](reference_accord_gp6b70_probe_spec_path_separation_and_gate1.md)
- [🛑🛑★★★★★ Six Path-2 lane weights censused — all stock, SIGN UNRESOLVED (blocking)](reference_accord_fun38148_six_weight_v95_candidate_census.md) — `0xC63A2` best structurally.
- [★★★★★ `gp-0x67ac` resolved zero — Path 1's unweighted sum always live](reference_accord_gp67ac_resolved_zero_and_path1_always_live.md)

## 2026-08-11 V92 allocation + telemetry budget (`fw-dampaxis`)
- [★★★★★ `gp-0x6abc` = raw motor rate; `gp-0x6bf0` CORRECTED (15+ readers incl. shaper)](reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication.md)
- [★★★★★ openpilot DBC clearance: 330 STEER_ANGLE/RATE + TORQUE_SENSOR live, never repoint](reference_accord_openpilot_dbc_repoint_clearance_2026-08-11.md) — DBC is Civic-named.
- 🛑 [CORRECTS above: openpilot clearance ≠ bus clearance; Kd cut killed (D damps 16-35Hz)](reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md) — D-term at …

## 2026-08-11 return-to-centre gate hunt (`fw-return`)
- 🛑🛑★★★★★ [NO LKAS-magnitude gate on return-centre; limiter = motor-rate-adaptive governor `0xC520C`](reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md)
- ⚠ PARTLY SUPERSEDED [Return-centre 2 terms: term2 sign = `-sign(gp-0x6bf0)`; `0xC627E`=20 virgin](reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization.md)

## 2026-08-11 PID anti-damper / GATE-2 (`fw-driver-model`)
- 🛑🛑★★★★★ [`FUN_0003a382`'s D-term (Kd=2.000, unfiltered) sole pumping term at 7.79Hz](reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction.md) — corrects V43 lineage; Kd …
- GATE-2 on `0xCBE74`/`6b26`: positive clearance, dissipative 2-35Hz. `docs/GATE2-2026-08-11-cbe74-independent.md`.

## 2026-08-10 driver-reference vs LKAS / DampAxis / V90 cave
- 🛑🛑★★★★★ [`gp-0x6b4a`=2nd direct ungated LKAS term into `6ad6`; CORRECTS V41 "0xC6194 inert"](reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md) — ⚠ superseded on …
- [🛑🛑✅✅★★★★★ `0xCBE74` dose CANNOT trip DTC-0x1d while `0xC407E`=511; `646E` INERTIA raising LIGHTENS the wheel](reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered.md)
- 🛑🛑★★★★★ [CRC blocks are a LINKED LIST, not 4KB pages — one `0xC4FFC` trailer covers all app code](reference_accord_crc_block_lookup_and_cave_hook_template.md)
- 🛑🛑 [OWN DEFECT: cave payload shipped BIG-endian; register-indirect `clr1` writers Ghidra misses](reference_accord_v90_cave_gate1_census_and_hook_critical_section.md) — `subr …
- [🛑🛑★★★★★ `FUN_0003b8f6` gate-FAIL zeros stale-not-fresh; polarity 0 passes silently](reference_accord_fun3b8f6_gatefail_stale_and_gp6c00_exact_flag.md)

## 2026-08-10 damping-axis (`DampAxis`) + 2026-08-09 HF-selectivity (`lever-hf`)
- 🛑🛑★★★★★ FactorB indexes rate not torque; torque arm DEAD. Grep `*factorb_index_selector*`.
- HF-selectivity (3, mature): `0xC64C8` mode-2 PROVABLE NO-OP; NO disabled r24/r26 filter exists; `FUN_00038148` 6 lanes + `6a10`=abs angle. Grep `*c64c8*` / `*r24_r26_pole*` / …

## 2026-08-09 filter/cave (multi-agent) — `0xC63B4`/`0xC63B8` band-pass arc
- [🛑🛑★★★★★ `0xC63B4`=51 ⇒ BANDPASS 8.14Hz Q0.501; 3-tap FIR cannot notch](reference_accord_c63b4_8hz_bandpass_in_fun3b66a.md)
- [🛑🛑★★★★★ Float twin blocks filter insertion at/below `gp-0x6b08` — cave path closed](reference_accord_shaper_float_twin_blocks_filter_insertion.md) · [`gp-0x6b08` narrowest node; reader#2 forbids amplification](reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor.md)
- [★★★★ `FUN_00041d56` 3×3 observer, ζ=0.975, fault detector not live](reference_accord_fun41d56_state_space_complex_poles.md) · [`gp-0x671a`=0 at creep ⇒ `gp-0x6abc`=4.7121 ct/°/s](reference_accord_gp671a_creep_value_and_friction_lane_schedule.md)
- [★★★★★ At creep both dampers OFF, r24/r26 gain MAX; V62's doubling HELPED](reference_accord_creep_damping_dead_rate_gain_max.md)
- Mature, grep only: `0xC63B8` live-not-a-damper (4) `*fun3b66a*`/`*c63b8*` · FOC bridge `ep`-relative + low-speed friction 5× `*foc_bridge_is_ep*`/`*lowspeed_gate_census*` · …

## 🛑 Own errors, corrected
- [Read a stock cal byte, reported as built-image value](feedback_own_error_stock_read_attributed_to_built_image.md).

## V87 lever census (`fw-lever-census`)
- [🛑🛑★★★★★ `andi` masks are STATE bitmasks not phase dividers — one 1kHz rate](reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md) · [RAM LERP Y[0]=0, corrects …
- [★★★★★ `0xC63AC` 2nd phase-lag pole α≈0.0996, −23.63°@7.79Hz; ⊕ ≈2.8°/tick transport that raising α does NOT remove](reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table.md)
- [★★★★★ `0xC6C42`=4 real, torque-RATE window, 1kHz](reference_accord_gp4f62_torque_rate_producer_and_c6c42_window.md) · [Lever A `sar` sites outside LKAS gate](reference_accord_lever_a_gate_structure_and_cal_double_equivalence.md)

## V86 prep / FactorD / V83 telemetry
- [🛑🛑★★★★★ `gp-0x6a10`=|raw column angle|; FactorD unreachable <35km/h; live 1kHz Path-2 lane](reference_accord_factord_six_family_map_and_1khz_lane_v84.md) · [`FUN_0003b8f6` REFUTED as biquad: dead 3-tap FIR; FRICTION relay + INERTIA damper](reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps.md)
- Mature, grep only: V81 engaged-only FactorC/E + mode24≡mode26 stock `*v81_engagement_impedance*`/`*mode24_mode26_stock*` · V86 prep …

## How I must work
- 🛑 [SendMessage not plain text](feedback_use_sendmessage_not_plain_text.md) · [Grep build_v*_tva.py before any cal](feedback_check_build_scripts_before_proposing_cal_edit.md) · [Check own memory first + variable-reuse trap](feedback_check_own_memory_before_retracing_and_variable_reuse_trap.md)

## Accord TVA-A160 — MATURE, grep only (≈130 memories; topic → grep patterns)
- Friction/seed/angle/RAM/FOC (17): `*friction_lane*` `*gp6bd0_seed*` `*gp6408*` `*gp63fd_full*` `*mode10_inert*` `*gp69a4*` `*angle_position_scale*` `*smooth_angle_gain*` …
- Damper FactorC/E + r24/r26 (6): `*factorc_e*` `*fun34350*` `*task5_100hz*` `*gp6b26_friction*` `*near_centre*` — `FUN_00034350` axis = SPEED, 8 km/h dead zone.
- Motor control (7): `reference_accord_pwm_*` `*fun757a2*` `*gp6ab*` `*gp67a*` `*gp69b0*` — PWM 4 kHz; `gp-0x6abe` = 4.7121× col °/s.
- 7.5 Hz ratchet (6): `reference_accord_ratchet_*` `*fun36388*` `*gp68ad*` `*v72_levera*` `*rate_lane*` `*detector_gate*` — 7.793 Hz.
- Boost-amp (9): `reference_accord_boost_*` `*r24_gainb*` `*fun456a4*` `*common_mode_rate*` `*four_unprobed*` — blend RISING only.
- Angle/return-centre (4): `reference_accord_can_angle_*` `*gp6bbe*` `*gp6b9a*` `*rate_limiter_enum*`.
- `FUN_0003a382` (6): `reference_accord_fun3a382_*` `*c646c*` `*gp6b98_aggregator*` — PID real, resonance unfiltered.
- Aggregator/arb (7): `reference_accord_aggregator_*` `*fun28ea6*` `*gp6ad4*` `*deadband_signgate*` `*gp6806*` `*r24_no_lkas*` `*gp683c*` — `6AF0` mutes `6ad4`.
- CAN RX/speed (10): `reference_accord_can_rx_*` `*low_speed_lockout*` `*c62ee*` `*gp6a5e*` `*steerstatus3*` `*d0xxx*` `*no_vehicle_speed*` — `gp-0x6a5e` = 64 ct/km/h voted speed.
- Timing/sensor (8): `reference_accord_state4_*` `*task5_rate*` `*pclk_40mhz*` `*dtc18*` `*torque_sensor_zero*` `*a160_sid30*` `*gp6a5e_voter*` `*gp67ac_agg*` — TASK5 100 Hz, …
- Damping/notch (6): `reference_accord_damping_*` `*notch_biquad*` `*r26_adaptive*` `*v61_taps*` `*governor_energy*` `*fun352b4*` — notch NEGATIVE.
- Cmd/clamps/shaper (15): `reference_accord_*shaper*` `*governor*` `*eme*` `*clamp*` `*lkas_path*` — shaper ±0x2000, governor max 4762.
- Decider/engage SM (11): `reference_accord_decider_*` `*engage_sm*` `*trampoline*` · CAN TX/UDS (14): `reference_accord_can_*` `*uds*` `*a160_*` — free RAM `gp-0x1500`/`gp-0x14e0`.
- `gp-0x4f60` V48B/50/52 (6): `reference_accord_gp4f60_*` `*v48b_*` `*v50_gp4f60*` `*fun2eda8*` `*v52_9lane*` · Misc (6): `*gain_a_*` `*a_ladder*` `*7hz_divider*` …

## C120/A030/TVA UDS+SA
- [TVA/Accord bootloader map+delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
