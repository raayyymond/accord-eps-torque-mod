# Firmware Codepath Tracer - Memory Index

## 2026-08-12 0xC63A6 GATE trace, NO-GO verdict (`c63a6-gate-trace`)
- [★★★★★ NO-GO on 0xC63A6 — Q1/Q5 closed clean (sole reader, flat non-mode scalar); Q3 splits into a determinate open-loop sign (reinforcing, new derivation) vs an unmeasured closed-loop gain L that the sibling 0xC63A0 precedent shows can invert](reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split.md) — reusable across all six FUN_00038148 lane weights; both blockers (FUN_0003b8f6 cascade, FUN_000389ec LERP table) unread by two independent sessions now.
- [tp-relative get_xrefs_to false-zero + ld.hu bit0/parity trap addressing the neighbour cell, both confirmed this session](reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12.md) — corroborate with search_instructions + a both-parity raw byte scan before trusting any tp-relative reader/writer count.

## 2026-08-11 PID phase @6-9Hz + GATE-1 movhi scan (`lane-weights-6bf`)
- [★★★★★ PID recomputed at 6-9Hz from fresh decompile (not extrapolated) — P is 3-5x less dominant, net phase lag 3-5x larger than the existing 21Hz figure](reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan.md) — the 32x P/D-vs-I asymmetry discovered; whole-image movhi/0xfedf scan clean (0 hits), GATE-1 closed.

## 2026-08-12 driver-override sign-guard relay (`lane-weights-6bf`)
- [★★★★★ gp-0x6806's gate traced to CAN-command domain, not the torque sensor — no firmware path from driver torque to the arb's deadband+sign-guard relay](reference_accord_gp6806_gate_is_can_domain_not_torque_sensor.md) — cal 0xC64A3=1 confirmed the single-byte arm for BOTH halves, never touched by any build; 0xC6AF0/gp-0x6966 struck (permanently wide open, per kit's own v54-flashed-authority-measured).

## 2026-08-12 engagement-gate enumeration (`lane-weights-6bf`)
- [🛑 CORRECTS reference_accord_gp69b0_authority_gate_and_fun42746_table_selector: FUN_0002a93a is DEAD CODE (0 callers/xrefs, 2 methods) — caught via citation-check before relaying, not after](reference_accord_fun2a93a_dead_code_correction_and_engagement_gate_catalog.md) — plus a full catalog of confirmed-live engagement gates (mode-table FUN_00042746, arb ramp gain, authority output-clamp collapse) for team-lead's Q2/Q3.

## 2026-08-11 gp-0x6b70 probe spec (`lane-weights-6bf`)
- [★★★★★ Probe spec closing Q5 empirically: gp-0x6b70 is EXCLUSIVELY Path-2 (GATE-1: 1W/1R), isolates 0xC63A2's marginal effect from Path-1's independent contribution](reference_accord_gp6b70_probe_spec_path_separation_and_gate1.md) — proposes time-sharing 427/0x1AB rather than a new hook; task5=100Hz has a free corroboration route via gp-0x6bbe's own step response.

## 2026-08-11 task-5 rate + FUN_000389ec (`lane-weights-6bf`) — 🛑🛑 RETRACTED 2026-08-12
- [🛑🛑 RETRACTED: Task 5 = 100Hz CONTRADICTED by gp-0x6bbe's own flown data (route 79 freq/step/phase) — task 1=1kHz unaffected, task 5's true rate OPEN](reference_accord_task5_rate_resolved_100hz_and_fun389ec_structure.md) — do NOT use the −5.8/−7.5/−8.6dB figures this produced; RAM-LERP structural facts (9-pt, Y[0]=0) still stand, the "10Hz effective" framing does not. Q5 sign STILL not closed regardless.

## 2026-08-11 FUN_00038148 six-weight V95 census (`lane-weights-6bf`)
- [🛑🛑★★★★★ Full Q1-Q5 census of the six Path-2 lane weights for the 6-9Hz micro-ratchet target — all frozen at stock, no overflow risk, SIGN UNRESOLVED (blocking gate)](reference_accord_fun38148_six_weight_v95_candidate_census.md) — `0xC63A2`(boost) best candidate structurally but inherits `0xC63A0`'s documented inversion-risk precedent.
- [★★★★★ `gp-0x67ac` resolved zero — Path 1's full unweighted sum (gp-0x6bd0/6bbe/6b26/6ad4/6b86) always live](reference_accord_gp67ac_resolved_zero_and_path1_always_live.md) — parallels the established gp-0x67ab=0 finding.

## 2026-08-11 V92 final allocation (`fw-dampaxis`)
- [★★★★★ Adjudicated a cross-agent claim myself: gp-0x6abc CONFIRMED raw/unfiltered motor rate (Term 1 structural form matches); gp-0x6bf0 CORRECTED — not inside the return-centre functions, lives in a separate function with 15+ readers incl. the shaper. Final 7-bit allocation fits entirely in 0x14A (boost mag+sign, return-centre 2-sign-bit test, dose-in-force |gp-0x6b26|≥15), ~106B cave estimate](reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication.md)

## 2026-08-11 telemetry budget audit (`fw-dampaxis`)
- [★★★★★ openpilot DBC clearance: STEER_ANGLE/RATE(330)/TORQUE_SENSOR live, never repoint; STEER_WHEEL_ANGLE+399's own rate code-unused](reference_accord_openpilot_dbc_repoint_clearance_2026-08-11.md) — DBC is Civic-named.
- 🛑 [CORRECTS above: openpilot clearance ≠ bus clearance; STEER_WHEEL_ANGLE CANDIDATE-BLOCKED. Kd cut killed (D damps 16-35Hz); probe re-aimed r24/r26/gp-0x6bbe](reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md).
- T1-T3 spec (`docs/SPEC-2026-08-11-telemetry-budget.md`): D-term output at gp-0x3680; 100Hz tick confirmed; telemeter gp-0x6ad6 before any Kd-cut.

## 2026-08-11 return-to-centre gate hunt (`fw-return`)
- 🛑🛑★★★★★ [NO LKAS-magnitude gate on return-centre; real limiter = MOTOR-RATE-ADAPTIVE governor ceiling (0xC520C) shared w/ LKAS's gp-0x6b4c, amplified by our own 0xC6CD0 4x gain](reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md) — both hard-gate candidates (67ac,67fa) closed.
- 🛑🛑★★★★★ [`gp-0x6afe`/`6b4e` — "LKAS overlay" signal — PROVABLY ALWAYS ZERO](reference_accord_gp6afe_gp6b4e_provably_zero_correction.md) — corrects `accord-aggregator-reaches-motor-via-gp6acc-bridge.md`; no 2nd LKAS injection at shaper.
- 🛑🛑★★★★★ [Return-centre's 2 terms re-derived: term2 sign=`-sign(gp-0x6bf0)` not "polarity" (corrects sibling memory); dwell-relay NO true hysteresis, cal 0xC627E=20 virgin](reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization.md) — anti-damping Qn -> ONE unresolved link (6bf0 vs 6abc sign); `62EA`/`64DE` live in arbitration not aggregator; team-lead's addrs off-by-one.
- 🛑🛑★★★★★ [Cross-agent polarity contradiction SETTLED via decompile: window opens on SMALL |gp-0x6b64| (detent reading confirmed, not saturation); but likely a FLAT −1024 CONSTANT at hands-off (gp-0x6bda≈9262 far outside its window) — clean-kill risk, unresolved for active steering](reference_accord_dwell_relay_polarity_settled_and_detent_likely_dead_at_handsoff.md).
- Writeup: `docs/TRACE-2026-08-11-return-to-centre-gate.md`.

## 2026-08-11 PID anti-damper hunt / GATE-2 (`fw-driver-model`)
- 🛑🛑★★★★★ [`FUN_0003a382`'s D-term (Kd=2.000, unfiltered) sole pumping term at 7.79Hz among P/I/D](reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction.md) — corrects V43 lineage (32 not 64); `671a` LERP=1.0 no-op; new lever (Kd cut).
- Independent GATE-2 on `0xCBE74`/`6b26` (modes 26/27 ×2-2.5): positive clearance — dissipative 2-35Hz. Appendix: `docs/GATE2-2026-08-11-cbe74-independent.md`.

## 2026-08-10 driver-reference vs LKAS (`fw-driver-model`)
- 🛑🛑★★★★★ [`gp-0x6b4a`=2nd, direct, ungated LKAS term into `6ad6`; CORRECTS V41/`BUILD-LINEAGE:705` "0xC6194 inert" (true only for sibling `6b4c`)](reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md) — arb pole −57°@7.79Hz.
- [🛑 `gp-0x4f60` producer traced, no EMA/IIR; identity CONFLICT torque-vs-velocity](reference_accord_gp4f60_identity_conflict_and_producer_traced.md). Writeup: `docs/TRACE-2026-08-10-driver-reference-vs-lkas.md`.

## 2026-08-10 DampAxis sizing+safety (`fw-dampaxis`)
- [🛑🛑✅✅★★★★★ `0xCBE74` dose CANNOT trip DTC-0x1d while `0xC407E`=511; `6b26` has OWN Path1; `646E`(INERTIA) shares sign-inv observer ⇒ raising it LIGHTENS the wheel](reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered.md).

## 2026-08-10 V90 cave spec (`CaveSpec`)
- 🛑🛑★★★★★ [CRC blocks are a LINKED LIST not 4KB pages — one `0xC4FFC` trailer covers all app code](reference_accord_crc_block_lookup_and_cave_hook_template.md).
- 🛑🛑 [OWN DEFECT: cave payload shipped BIG-endian; GATE-1 register-indirect `clr1` writers Ghidra misses](reference_accord_v90_cave_gate1_census_and_hook_critical_section.md) — `subr r0,rN`=`8031` not `3080`.
- [🛑🛑★★★★★ `FUN_0003b8f6` gate-FAIL zeros stale-not-fresh; polarity 0 passes gate silently](reference_accord_fun3b8f6_gatefail_stale_and_gp6c00_exact_flag.md).

## 2026-08-10 torque/current damping-axis (`DampAxis`, V89-era)
- [🛑🛑★★★★★ FactorB indexes rate not torque; torque arm DEAD](reference_accord_factorb_index_selector_c6498_and_torque_axis_census.md).
- [★★★★★ `gp-0x6b26` sign=DISSIPATIVE 14-21% of ±511; ±1024 zero-reject unreachable](reference_accord_fun36c12_sign_settled_dissipative.md).

## 2026-08-09 HF-selectivity (`lever-hf`, V88-era)
- [🛑🛑★★★★★ `0xC64C8` mode-2 PROVABLE NO-OP](reference_accord_c64c8_float_twin_mode_mirror_and_mode2_noop.md); [★★★★★ NO disabled filter r24/r26](reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists.md); [★★★★★ `FUN_00038148` 6 lanes; `6a10`=abs angle](reference_accord_fun38148_six_lane_identity_and_gp6a10_producer.md).

## 2026-08-09 filter/cave (multi-agent) — `0xC63B4`/`0xC63B8` band-pass arc
- [🛑🛑★★★★★ `0xC63B4`=51 ⇒ BANDPASS 8.14Hz Q0.501; 3-tap FIR cannot notch](reference_accord_c63b4_8hz_bandpass_in_fun3b66a.md).
- 🛑🛑★★★★★ `0xC63B8` LIVE but NOT a damper: [rectified](reference_accord_fun3b66a_8hz_bandpass_is_rectified_not_a_damper.md) · [boost cutback](reference_accord_fun3b66a_bandpass_is_boost_gain_modulator.md) · [value path dead](reference_accord_c63b8_is_a_boost_index_dgain_not_a_damper.md) · [blast radius](reference_accord_c63b8_bandpass_lane_blast_radius.md).
- [★★★★ `FUN_00041d56` 3×3 observer, ζ=0.975, fault detector not live](reference_accord_fun41d56_state_space_complex_poles.md).
- [★★★★ `gp-0x671a`=0 at creep; derives `gp-0x6abc`=4.7121 ct/°/s](reference_accord_gp671a_creep_value_and_friction_lane_schedule.md).
- [🛑🛑★★★★★ Float twin blocks filter insertion at/below `gp-0x6b08` — cave path closed](reference_accord_shaper_float_twin_blocks_filter_insertion.md).
- [★★★★★ FOC bridge is `ep`-relative](reference_accord_foc_bridge_is_ep_relative_not_gp.md); [friction 5× at 0 vs 90km/h](reference_accord_lowspeed_gate_census_and_friction_5x_schedule.md).
- [★★★★★ At creep both dampers OFF, r24/r26 gain MAX; V62's doubling HELPED](reference_accord_creep_damping_dead_rate_gain_max.md).
- [★★★★★ `gp-0x6b08` narrowest node; reader#2 forbids amplification](reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor.md).
- GATE-1 RAM: [array-base blindspot](reference_accord_gate1_movea_gp_array_blindspot_and_scalar_bound.md); [1W+0R beats virgin RAM](reference_accord_gate1_write_only_diag_taps_are_the_best_cave_ram.md).
- [★★★★★ CRC-block/jarl/cave template](reference_accord_crc_block_lookup_and_cave_hook_template.md); [gp opcode map, `ld.hu`=0x3F](reference_v850_gp_relative_opcode_field_map_validated.md); [`0xC6CD0` Path1≠Path2](reference_accord_path1_path2_structural_decoupling_and_damping_dose_tables.md).

## 🛑 Own errors, corrected
- [Read a stock cal byte, reported as built-image value](feedback_own_error_stock_read_attributed_to_built_image.md).

## V87 lever census (`fw-lever-census`)
- [🛑🛑★★★★★ `andi` masks are STATE bitmasks not phase dividers — one 1kHz rate](reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md).
- [★★★★★ `0xC6C42`=4 real, torque-RATE window, 1kHz](reference_accord_gp4f62_torque_rate_producer_and_c6c42_window.md).
- [🛑🛑★★★★★ RAM LERP Y[0]=0, corrects build_v86's relay claim](reference_accord_ram_lerp_y0_zero_corrects_v86_relay_claim.md).
- [★★★★★ `0xC63AC` 2nd phase-lag α≈0.0996](reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table.md); [2 dead lanes gp-0x6bce/6bbc](reference_accord_fun38148_fun37fe6_channel_census_and_dead_lanes.md).
- [★★★★★ Lever A `sar` sites outside LKAS gate; `0xC6446`/`0xC6444` doubling bit-exact](reference_accord_lever_a_gate_structure_and_cal_double_equivalence.md).

## V86 prep / FactorD / engagement asymmetry
- [🛑🛑★★★★★ `gp-0x6a10`=|raw column angle|; FactorD unreachable <35km/h; live 1kHz Path-2 lane](reference_accord_factord_six_family_map_and_1khz_lane_v84.md).
- [★★★★★ `FUN_0003b8f6` REFUTED as biquad: dead 3-tap FIR; FRICTION relay + INERTIA damper inside](reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps.md).
- [★★★★★ V81 engaged-only FactorC/E dose = only asymmetric mechanism](reference_accord_v81_engagement_impedance_factorce_dominant_mechanism.md); [🛑🛑 mode24≡mode26 on stock](reference_accord_mode24_mode26_stock_boost_friction_gainb_identical.md).
- [Plant-model inventory + `0xC64C8/9` + boost LERP2 closed](reference_accord_v86_prep_plantmodel_c64c8_boost_lerp2_closed.md); [🛑 GhidraMCP tools can silently fail to register](feedback_ghidra_tool_registration_can_silently_fail.md).

## V83 telemetry design
- [★★★★★ V83a spec: 8 bits, splice `0x14A`+hook `0x18F`, RAM `gp-0x1500`](reference_accord_v83a_telemetry_spec_final.md); [MOTOR_TORQUE=0: `gp-0x4f74` is live FOC output](reference_accord_motor_torque_zero_investigation_two_hypotheses_refuted.md).
- [🛑 `gp-0x67fa`≠mode-24/26, `gp+0x63fd` is](reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered.md); [`FUN_0003aa2c`=gp-0x6b94 writer](reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate.md); [CAN 399/427 hook sites](reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget.md).

## V75 stoplight-launch — CLOSED, superseded by [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]
- 17 sub-memories on file — grep `reference_accord_*v75*` / `*gp6b26*` / `*path2*`.

## How I must work
- [🛑 Use SendMessage, not plain text](feedback_use_sendmessage_not_plain_text.md); [🛑 Grep build_v*_tva.py before proposing any cal](feedback_check_build_scripts_before_proposing_cal_edit.md); [🛑 Check own memory before retracing + variable-slot-reuse trap](feedback_check_own_memory_before_retracing_and_variable_reuse_trap.md).

## Accord TVA-A160
- Friction `FUN_00036c12`: [smooth signed multiply, no stick-slip](reference_accord_friction_lane_fun36c12_smooth_no_stickslip.md); [`0xC407E` census closed](reference_accord_friction_lane_c407e_census_and_mode26_record_identity.md).
- [🛑🛑 "FactorA"=seed closed, 11ch pinned 1024](reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found.md); [`gp+0x6408` UDS-only writer](reference_accord_config_key_gp6408_udsonly_writer_bss_no_boot_populator.md); [`gp+0x63fd` enumeration](reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays.md); [🛑🛑 live modes=24/26 not 8/10](reference_accord_r24_gainb_mode10_inert_and_24v26_array_diff.md).
- Damper FactorC/E+r24/r26: [`FUN_00034350` mapped, axis=SPEED](reference_accord_factorc_e_damper_full_trace_r24r26_parallel.md); [5-factor product, sign relay, 8km/h dead zone](reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm.md); [damping live+gated](reference_accord_fun34350_damping_term_live_and_gated.md); [🛑🛑 task1=1kHz/task5=100Hz live](reference_accord_task5_100hz_live_verified_full_producer_census.md); [gp-0x6b26 sized](reference_accord_gp6b26_friction_lane_damping_candidate.md); [near-centre flat zero](reference_accord_near_centre_structure_hunt_angle_tracking_chain_found.md).
- [`gp-0x69a4` slew floor-0+snap](reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected.md); [angle scale 0.1deg/ct](reference_accord_angle_position_scale_0p1_deg_per_count_settled.md); [🛑🛑 `0xC6B64` rejected](reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles.md).
- Motor-control (7 memories, mature): PWM=4kHz, `FUN_000757a2`->CAN427, `gp-0x6abe`=4.7121x col_degps, 6-LERP FOC, `gp-0x67ac`/`gp-0x67fa` closed, `gp-0x69b0` gate. Grep `reference_accord_pwm_*` / `*fun757a2*` / `*gp6ab*` / `*gp67a*` / `*gp69b0*`.
- 7.5Hz ratchet (6 memories, mature): 7.793Hz; `FUN_00036388` brake; `68ad` dead; rate lane V62-V69; detector live. Grep `reference_accord_ratchet_*` / `*fun36388*` / `*gp68ad*` / `*v72_levera*` / `*rate_lane*` / `*detector_gate*`.
- RAM/cave GATE1: [App RAM map](reference_accord_app_ram_layout_and_boot_init_loops.md); [`683c` clear](reference_accord_gate1_gp683c_ram_ownership_audit.md).
- Boost-amp (9 memories, mature): curves->6bbe, blend RISING only, r24 gate, `6abc`=resolver rate, 73ba atten@21Hz; `FUN_000456a4` 4 lanes solved, no-hysteresis. Grep `reference_accord_boost_*` / `*r24_gainb*` / `*fun456a4*` / `*common_mode_rate*` / `*four_unprobed*`.
- Angle/return-centre (4 memories): CAN 0x14A; `6bbe` baseline/LERP; `6b9a` r21 gate+sentinels; rate-limiter=fault-tag. Grep `reference_accord_can_angle_*` / `*gp6bbe*` / `*gp6b9a*` / `*rate_limiter_enum*`.
- `FUN_0003a382` (6 memories, mature): `gp-0x6ad6` 4x; `0xC646C`; 11-lane table; PID real; resonance unfiltered. Grep `reference_accord_fun3a382_*` / `*c646c*` / `*gp6b98_aggregator*`.
- Aggregator/arb (7 memories, mature): no angle lane; ramp SM; `6AF0` mutes 6ad4; deadband->diag; `6806`; no LKAS fork; `683c` repoint. Grep `reference_accord_aggregator_*` / `*fun28ea6*` / `*gp6ad4*` / `*deadband_signgate*` / `*gp6806*` / `*r24_no_lkas*` / `*gp683c*`.
- CAN RX/speed (10 memories, mature): `C62EA`=320; BB550/BB5A0 desc tables; disp23; `C62EE`; `6a5e`=64ct/kmh voted speed; ST3; accept filter; D0xxx LERP; arb no-speed. Grep `reference_accord_can_rx_*` / `*low_speed_lockout*` / `*c62ee*` / `*gp6a5e*` / `*steerstatus3*` / `*d0xxx*` / `*no_vehicle_speed*`.
- Timing/sensor (8 memories, mature): ST=4 dwell; TASK5=100Hz; OSTM0=500Hz; DTC-0x18; resolver zero+bias; no neutral routine; `6a5e` BW<21Hz; `67ac` suppression. Grep `reference_accord_state4_*` / `*task5_rate*` / `*pclk_40mhz*` / `*dtc18*` / `*torque_sensor_zero*` / `*a160_sid30*` / `*gp6a5e_voter*` / `*gp67ac_agg*`.
- Damping/notch (6 memories, mature): gates; notch NEGATIVE; r26 trace; V61 taps; gov budget; 6b86 peak-hold. Grep `reference_accord_damping_*` / `*notch_biquad*` / `*r26_adaptive*` / `*v61_taps*` / `*governor_energy*` / `*fun352b4*`.
- Cmd/clamps/shaper (15 memories, mature): shaper clamp ±0x2000, governor max 4762, mixer=512, `gp-0x6809` dead. Grep `reference_accord_*shaper*` / `*governor*` / `*eme*` / `*clamp*` / `*lkas_path*`.
- Decider/engage SM (11 memories, mature): `FUN_0002a30e`=ST4 debounce; hook `0x40e64` live. Grep `reference_accord_decider_*` / `*engage_sm*` / `*trampoline*`.
- CAN TX/UDS (14 memories, mature): 18-slot TX table, `0x14A` bytemap, CAN427=`gp-0x4f74`, cave `0xC4B34`, free RAM `gp-0x1500`/`gp-0x14e0`. Grep `reference_accord_can_*` / `*uds*` / `*a160_*`.
- FOC: [ISR+PWM map](reference_accord_foc_inner_current_loop_architecture.md); [below gp-0x6b98 swept](reference_accord_below_gp6b98_foc_delivery_path_swept.md).
- V48B/50/52 `gp-0x4f60` (6 memories, mature): feasibility; reader closure; asymmetry; V50 carryover; lane9; V52 clean. Grep `reference_accord_gp4f60_*` / `*v48b_*` / `*v50_gp4f60*` / `*fun2eda8*` / `*v52_9lane*`.
- Misc (6 memories): V73 gain_A index; ladder monotone; no 7.8Hz divider; mixer 4x falsified; `gp-0x6c2c` TF; shaper rail guard. Grep `reference_accord_gain_a_*` / `*a_ladder*` / `*7hz_divider*` / `*mixer_channels*` / `*gp6c2c*` / `*shaper_rail*`.

## C120/A030/TVA UDS+SA
- [TVA/Accord bootloader map+delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
