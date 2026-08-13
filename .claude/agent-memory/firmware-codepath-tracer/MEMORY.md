# Firmware Codepath Tracer - Memory Index

## 2026-08-12 Stage-2 LERP knots (`LerpKnots`)
- [🛑🛑★★★★★ The Stage-2 LERP has NO runtime rescale — `gp-0x6982`/`gp-0x6984` have **ZERO writers** (3 methods + a working positive control) and boot to **1024** from `.data` ⇒ `f′` swing is **1.000×, not ≥10×**; the knots ARE the flash record](reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound.md) — creep knots for modes 24/26 + inversion: route 80's `|gp-0x6b70|` ⇒ **`|iVar6| ≤ ~6,900`, p50 ~130**, 2.9× tighter than the ±20,000 writer clamp. 🛑 bounds `|iVar6|` NOT `|gp-0x6bfe|` alone. ⊕ the speed-scheduled **X-axis cap** (`0xC669A`/`0xC66A8`) drops 12,000→7,000 above 50 km/h ⇒ creep numbers do NOT travel to highway.

## 2026-08-12 closing the sign (`close-the-sign`)
- [🛑🛑★★★★★ STATE.md §A6b FALSE — the "RAM" LERP is 100% FLASH-derived, and **`f′ ≥ 0` is ENFORCED IN CODE at 3 ungated sites** ⇒ any cal/mode/build; MEMORYLESS + SIGN-PRESERVING, cannot invert at any frequency](reference_accord_ram_lerp_is_flash_derived_and_fprime_nonneg.md) — closes the OPEN-loop sign only (cf `B=1+Q`). Residual = **1 bit**: `gp-0x6752` is a ±1 EEPROM CONFIG constant ⇒ not in the image. ⊕ MEASURED `gp-0x6b70` **−100.4°** vs rate (coh² 0.507) ⇒ INERTIA + weakly ANTI-DAMPING; ⇒ raising `0xC63AC` REDUCES it. 🛑 **`scipy.signal.csd(x,y)` = `arg(Y)−arg(X)`** — I reported this sign inverted first; validate cross-spectral phase against a synthetic known lag.
- [🛑🛑★★★★★ "8 float coefficients of `FUN_0003b8f6`" is WRONG — **3 floats + 6 u16 Q-format**, and the FIR is an **IDENTITY** (taps 1,0,0)](reference_accord_fun3b8f6_cal_types_iir_phase_and_v86_gate_decode.md) — rate **1 kHz PROVEN 2 ways**; **`0xC40D6`=246 dominant phase (fc 9.86 Hz, −73.9°), VIRGIN 92/92**; **`0xC40D8` a −0.6° NO-OP**. 🛑 V86's null was NOT a gating null (its own probe: gate 1.0000) ⇒ closed-loop suppression ⇒ lane-weight builds need a LARGE dose scored on the ring. ⊕ `gp-0x6bfe`/`6bfa` REAL.

## 2026-08-12 the 6-9 Hz loop, end to end (`fw-loop`)
- [🛑🛑★★★★★ THE PATH-2 BRACKET — Path 2 enters as `B = 1 + Q`, NOT in series ⇒ raising `0xC63AC` adds lead only if `sign(|Q| + cos(arg Q)) > 0`; **inversion iff `|Q|<1` AND `cos(arg Q) < −|Q|`**. `f′ ≥ 0` closes the OPEN-loop sign only; `arg L(7.79)` is open ⇒ **V96's S2, not S1, is the gate**](reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop.md) — applies to ALL six weights AND the pole. ⊕ α sweep: exchange rate FLAT at 0.33°/% @21 Hz (no sweet spot); but 1.38× is a **Path-2** figure — Path 1 dilutes it to **+4..+22 % on the command** (V88's 0.549 CI survives). ⊕ `gp-0x6b46` identity CORRECTED: a backlash-gated **RESIDUAL** servo (0.0272× torque), not filtered torque.
- [🛑🛑★★★★★ The 6-9 Hz loop is the PID DRIVER-TORQUE-TRACKING servo, not base-assist; total firmware phase at 6-9 Hz is only −3 to +10° ⇒ 7.8 Hz CANNOT be a firmware pole (frequency = PLANT, damping = firmware); CORRECTS STATE.md §A6b — the PID **LEADS** +8.2° at 7.79 Hz, it does not lag −11..−27°](reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget.md) — + task-1 ordering (Path 2 is ONE TICK STALE vs Path 1), the 32× P/D-vs-I asymmetry pinned to exactly three `shl 0x5` sites, the PID authority clamp (**227 ct at 6 km/h**) that makes the lane a RELAY, and six **VIRGIN** phase cells (`0xC6AE6`/`0xC6B12`/`0xC6B26`/`0xC63AC`/`0xC63D2`/`0xC67C8` — invariant-asserted only, never written). ⊕ Independently reproduces `fw-levers`' lane↔weight map. Model: `analysis-2020accord/_v97/loop_phase_model.py`.

- [🛑🛑★★★★★ EVERY rate limit on the LKAS→motor path — `0xC6194` IS a real 3 ct/ms slew limiter, dead ONLY because its partition is empty (mode bytes `0xC4118` all = 1); the kit memory's "output ×0" reason is WRONG (that is `0xC6196`)](reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale.md) — `gp-0x6ac0` = |LPF(gp-0x4f50)|, ×0x400 and >>10 cancel ⇒ **4.7121 ct per column °/s**; `0xC520C` knots = **222.8–870.1 °/s** ⇒ dead below 223 °/s, −25 % at 330; clamp applied to the **SUM** (`FUN_00049a90` 3-arg clamp @`0x453fe`); governor slew 512/tick @1 kHz cannot bind. ⊕ `0xC63CC`=0 ⇒ `gp-0x6b4c` does NOT carry the LKAS command.

## 2026-08-12 V97 cell ledger (`fw-levers`)
- [★★★★★ `0xC63AC` = the only PURE-LEAD lever: DC gain 1.000000 at every value ⇒ a POLE not a GAIN, so it ESCAPES the sign problem that disqualifies all 6 lane weights](reference_accord_c63ac_is_the_pure_lead_pole_lever.md) — 102→205 = +12.6° margin @7.79Hz AND 2.13× faster return; VIRGIN/89, 1R+0W. 🛑 1.38× @21Hz may undo V62. ⊕ arith `>>` dead zone. `0xC644A` has no headroom.
- [🛑🛑★★★★★ THE lane↔weight map for FUN_00038148 — no kit doc said which lane each weight multiplies; that gap let a DEAD lane's result be imported as a live precedent](reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation.md) — reconciles 0xC63A0 INERT (weights `gp-0x6bd0`, measured ~0 ⇒ V64-class null); refutes STATE §A5 (`gp-0x6b4e`≡0 ⇒ `0xC63A8` unfliable; array is `gp-0x62c8`; gates are ZERO-REJECT). 5/6 weights VIRGIN.
- [🛑🛑★★★★ `0xC64DE` is a BYTE (17→27), not halfword 25617/25627 — and a relaxation-oscillator HALF-PERIOD (29.4→18.5Hz), not a ramp ceiling](reference_accord_c64de_is_a_byte_oscillator_halfperiod.md) — `ld.bu` parity trap merged it with `0xC64DF`; 8 of 16 readers sit in a region Ghidra never analysed ⇒ tool zero.

## 2026-08-12 V97 sole-route test (`fw-return`)
- [🛑🛑★★★★★ REFUTED "PID lane is the sole actuation route" — LKAS's lane is mode 0, so REQ_B flows gp-0x62f8→gp-0x62b0→gp-0x3d88→gp-0x6b4c→aggregator, NEVER seeing AUTH](reference_accord_two_lkas_routes_gp6b4c_bypasses_auth.md) — full 10-caller lane map; ALL CAN-RX lanes (0,1,3,8) are mode 0, all mode-5 lanes are internal assist. AUTH ramp real (header `0xC67BE` **not** 0xC67C8) but not exclusive. Independently matched by team-lead's regression (log(AUTH) beta −0.013 [−0.344,+0.319]).
- [🛑🛑★★★★★ NEW TRAP CLASS: `ep`-relative short-format aliasing — the tool-zero that returns a HEALTHY NON-ZERO COUNT](reference_v850_ep_relative_short_format_aliasing_trap.md) — `movea <off>,gp,ep` then `sld/sst` off ep ⇒ operand search finds base setups and 0 real accesses. Recipe + 254-byte reachability bound. ⊕ filtered-zero and "no direct reader ≠ dead cal" siblings.

## 2026-08-12 V97 return-to-centre crux (`fw-return`)
- [🛑🛑★★★★★ The "return-centre" lane is a RACK END-STOP CUSHION](reference_accord_return_centre_is_an_end_stop_cushion_not_centring.md) — STALL-armed, needs |gp-0x6bf0|>8878; no LKAS gate; Honda's, frozen stock all 7 images. Don't re-arm.
- [🛑🛑★★★★★ CORRECTS the two 2026-08-11 entries below: dwell arms on |gp-0x6b64| **>** 1024](reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record.md) — asm+decompile+V92 duties; EXONERATES the `byte7 b6` rung; "flat −1024 bias" never occurs.
- [★★★★★ NOTHING dissipates in the micro regime — all 3 viscous terms gated off](reference_accord_micro_regime_has_no_scheduled_dissipation.md) — explains Re(Z)<0 @6-9Hz; crux = MISSING VISCOUS TERM, not a muted lane.
- [★★★★ Aggregator zero-reject window map — 8 of 11 lanes, widths DIFFER; gp-0x6b4c vacuous by EXACTLY zero margin](reference_accord_aggregator_zero_reject_window_map.md) — 🛑 only 2 of 8 ceilings verified ⇒ "all eight vacuous" NOT closed; V850 CY is carry-OUT.

## 2026-08-12 0xC63A6 GATE trace, NO-GO verdict (`c63a6-gate-trace`)
- [★★★★★ NO-GO on 0xC63A6 — Q1/Q5 clean; Q3 splits open-loop sign (reinforcing) vs unmeasured closed-loop gain L that 0xC63A0 shows can invert](reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split.md) — reusable across all six FUN_00038148 weights.
- [tp-relative `get_xrefs_to` false-zero + `ld.hu` bit0/parity trap hitting the neighbour cell](reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12.md) — corroborate with a both-parity raw byte scan.

## 2026-08-11/12 lane weights, PID phase, engagement gates (`lane-weights-6bf`)
- [★★★★★ PID recomputed at 6-9Hz from fresh decompile — P 3-5x less dominant, phase lag 3-5x larger than the 21Hz figure; 32x P/D-vs-I asymmetry; GATE-1 movhi scan clean](reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan.md)
- [★★★★★ gp-0x6806's gate is CAN-command domain, not the torque sensor](reference_accord_gp6806_gate_is_can_domain_not_torque_sensor.md) — cal 0xC64A3=1 arms both halves, never touched; 0xC6AF0/gp-0x6966 struck.
- [🛑 CORRECTS gp69b0 memory: FUN_0002a93a is DEAD CODE + catalog of confirmed-live engagement gates](reference_accord_fun2a93a_dead_code_correction_and_engagement_gate_catalog.md)
- [★★★★★ gp-0x6b70 probe spec — EXCLUSIVELY Path-2 (1W/1R), isolates 0xC63A2 from Path-1](reference_accord_gp6b70_probe_spec_path_separation_and_gate1.md) — time-share 427/0x1AB, no new hook.
- [🛑🛑★★★★★ Six Path-2 lane weights censused — all stock, no overflow, SIGN UNRESOLVED (blocking)](reference_accord_fun38148_six_weight_v95_candidate_census.md) — `0xC63A2` best structurally, inherits 0xC63A0's inversion risk.
- [★★★★★ gp-0x67ac resolved zero — Path 1's full unweighted sum always live](reference_accord_gp67ac_resolved_zero_and_path1_always_live.md)

## 2026-08-11 V92 allocation + telemetry budget (`fw-dampaxis`)
- [★★★★★ gp-0x6abc CONFIRMED raw motor rate; gp-0x6bf0 CORRECTED (separate function, 15+ readers incl. shaper); 7-bit allocation fits in 0x14A](reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication.md)
- [★★★★★ openpilot DBC clearance: 330 STEER_ANGLE/RATE + TORQUE_SENSOR live, never repoint](reference_accord_openpilot_dbc_repoint_clearance_2026-08-11.md) — DBC is Civic-named.
- 🛑 [CORRECTS above: openpilot clearance ≠ bus clearance; Kd cut killed (D damps 16-35Hz); probe re-aimed](reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md) — spec `docs/SPEC-2026-08-11-telemetry-budget.md`, D-term at gp-0x3680.

## 2026-08-11 return-to-centre gate hunt (`fw-return`)
- 🛑🛑★★★★★ [NO LKAS-magnitude gate on return-centre; real limiter = MOTOR-RATE-ADAPTIVE governor ceiling (0xC520C) shared w/ LKAS's gp-0x6b4c, amplified by our own 0xC6CD0 4x gain](reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md) — both hard-gate candidates (67ac,67fa) closed.
- 🛑🛑★★★★★ [NO LKAS-magnitude gate on return-centre; real limiter = MOTOR-RATE-ADAPTIVE governor ceiling `0xC520C`, shared w/ `gp-0x6b4c`](reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md) — both hard-gate candidates (67ac,67fa) closed.
- ⚠ PARTLY SUPERSEDED 2026-08-12 (`x−UPPER` → `UPPER−x`) [Return-centre's 2 terms: term2 sign=`-sign(gp-0x6bf0)`; cal 0xC627E=20 virgin](reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization.md) — `62EA`/`64DE` live in arbitration not aggregator.
- ⚠ PARTLY SUPERSEDED 2026-08-12 [return-centre 2 terms; term2 sign=`-sign(gp-0x6bf0)`; `0xC627E`=20 virgin](reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization.md) — `62EA`/`64DE` in arbitration.
## 2026-08-11 PID anti-damper hunt / GATE-2 (`fw-driver-model`)
- 🛑🛑★★★★★ [`FUN_0003a382`'s D-term (Kd=2.000, unfiltered) sole pumping term at 7.79Hz](reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction.md) — corrects V43 lineage (32 not 64); `671a` LERP=1.0 no-op; Kd cut is a lever.
- GATE-2 on `0xCBE74`/`6b26` (m26/27 ×2-2.5): positive clearance, dissipative 2-35Hz. `docs/GATE2-2026-08-11-cbe74-independent.md`.

## 2026-08-10 driver-reference vs LKAS (`fw-driver-model`)
- 🛑🛑★★★★★ [`gp-0x6b4a`=2nd, direct, ungated LKAS term into `6ad6`; CORRECTS V41/`BUILD-LINEAGE:705` "0xC6194 inert" (true only for sibling `6b4c`)](reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md) — arb pole −57°@7.79Hz.
- 🛑🛑★★★★★ [`gp-0x6b4a` = 2nd, direct, ungated LKAS term into `6ad6`; CORRECTS `BUILD-LINEAGE:705` "0xC6194 inert" (true only for sibling `6b4c`)](reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md) — arb pole −57°@7.79Hz.

## 2026-08-10 DampAxis sizing+safety (`fw-dampaxis`)
- [🛑🛑✅✅★★★★★ `0xCBE74` dose CANNOT trip DTC-0x1d while `0xC407E`=511; `6b26` has OWN Path1; `646E`(INERTIA) shares sign-inv observer ⇒ raising it LIGHTENS the wheel](reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered.md).

## 2026-08-10 V90 cave spec (`CaveSpec`)
- 🛑🛑★★★★★ [CRC blocks are a LINKED LIST not 4KB pages — one `0xC4FFC` trailer covers all app code](reference_accord_crc_block_lookup_and_cave_hook_template.md).
- 🛑🛑 [OWN DEFECT: cave payload shipped BIG-endian; GATE-1 register-indirect `clr1` writers Ghidra misses](reference_accord_v90_cave_gate1_census_and_hook_critical_section.md) — `subr r0,rN`=`8031` not `3080`.
- [🛑🛑★★★★★ `FUN_0003b8f6` gate-FAIL zeros stale-not-fresh; polarity 0 passes gate silently](reference_accord_fun3b8f6_gatefail_stale_and_gp6c00_exact_flag.md).

## 2026-08-10 damping-axis (`DampAxis`) + 2026-08-09 HF-selectivity (`lever-hf`)
- 🛑🛑★★★★★ FactorB indexes rate not torque; torque arm DEAD. Grep `*factorb_index_selector*`.
- HF-selectivity (3, mature): `0xC64C8` mode-2 PROVABLE NO-OP; NO disabled r24/r26 filter exists; `FUN_00038148` 6 lanes + `6a10`=abs angle. Grep `*c64c8*` / `*r24_r26_pole*` / `*six_lane_identity*`.

## 2026-08-09 filter/cave (multi-agent) — `0xC63B4`/`0xC63B8` band-pass arc
- [🛑🛑★★★★★ `0xC63B4`=51 ⇒ BANDPASS 8.14Hz Q0.501; 3-tap FIR cannot notch](reference_accord_c63b4_8hz_bandpass_in_fun3b66a.md).
- 🛑🛑★★★★★ `0xC63B8` LIVE but NOT a damper (4, mature): rectified · boost cutback · value path dead · blast radius. Grep `*fun3b66a*` / `*c63b8*`.
- [★★★★ `FUN_00041d56` 3×3 observer, ζ=0.975, fault detector not live](reference_accord_fun41d56_state_space_complex_poles.md).
- [★★★★ `gp-0x671a`=0 at creep; derives `gp-0x6abc`=4.7121 ct/°/s](reference_accord_gp671a_creep_value_and_friction_lane_schedule.md).
- [🛑🛑★★★★★ Float twin blocks filter insertion at/below `gp-0x6b08` — cave path closed](reference_accord_shaper_float_twin_blocks_filter_insertion.md).
- FOC/misc (2, mature): FOC bridge is `ep`-relative; low-speed friction 5x at 0 vs 90km/h. Grep `*foc_bridge_is_ep*` / `*lowspeed_gate_census*`.
- [★★★★★ At creep both dampers OFF, r24/r26 gain MAX; V62's doubling HELPED](reference_accord_creep_damping_dead_rate_gain_max.md).
- [★★★★★ `gp-0x6b08` narrowest node; reader#2 forbids amplification](reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor.md).
- GATE-1 RAM (2, mature): movea/gp array-base blindspot; 1W+0R write-only diag taps beat virgin RAM. Grep `*gate1_movea*` / `*gate1_write_only*`.
- Cave/opcode (3, mature): CRC-block/jarl/cave template; gp opcode map (`ld.hu`=0x3F); `0xC6CD0` Path1≠Path2. Grep `*crc_block_lookup*` / `*gp_relative_opcode*` / `*path1_path2*`.

## 🛑 Own errors, corrected
- [Read a stock cal byte, reported as built-image value](feedback_own_error_stock_read_attributed_to_built_image.md).

## V87 lever census (`fw-lever-census`)
- [🛑🛑★★★★★ `andi` masks are STATE bitmasks not phase dividers — one 1kHz rate](reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md).
- [★★★★★ `0xC6C42`=4 real, torque-RATE window, 1kHz](reference_accord_gp4f62_torque_rate_producer_and_c6c42_window.md).
- [🛑🛑★★★★★ RAM LERP Y[0]=0, corrects build_v86's relay claim](reference_accord_ram_lerp_y0_zero_corrects_v86_relay_claim.md).
- ★★★★★ [`0xC63AC` 2nd phase-lag pole, α≈0.0996, −23.63°@7.79Hz — CONFIRMS the V97 figure cross-session; ⊕ add ≈2.8°/tick transport, which raising α does NOT remove](reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table.md); 2 dead lanes `gp-0x6bce`/`6bbc`.
- [★★★★★ Lever A `sar` sites outside LKAS gate; `0xC6446`/`0xC6444` doubling bit-exact](reference_accord_lever_a_gate_structure_and_cal_double_equivalence.md).

## V86 prep / FactorD / engagement asymmetry
- [🛑🛑★★★★★ `gp-0x6a10`=|raw column angle|; FactorD unreachable <35km/h; live 1kHz Path-2 lane](reference_accord_factord_six_family_map_and_1khz_lane_v84.md).
- [★★★★★ `FUN_0003b8f6` REFUTED as biquad: dead 3-tap FIR; FRICTION relay + INERTIA damper inside](reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps.md).
- ★★★★★ V81 engaged-only FactorC/E dose = only asymmetric mechanism; 🛑🛑 mode24≡mode26 on stock. Grep `*v81_engagement_impedance*` / `*mode24_mode26_stock*`.
- V86 prep (2, mature): plant-model inventory + `0xC64C8/9` + boost LERP2 closed; 🛑 GhidraMCP tools can silently fail to register. Grep `*v86_prep*` / `*feedback_ghidra_tool_registration*`.

## V83 telemetry design
- V83 telemetry (2, mature): V83a spec 8 bits, splice `0x14A`+hook `0x18F`, RAM `gp-0x1500`; MOTOR_TORQUE=0 ⇒ `gp-0x4f74` is live FOC output. Grep `*v83a_telemetry*` / `*motor_torque_zero*`.
- Mode/hook (3, mature): `gp-0x67fa`≠mode-24/26 (`gp+0x63fd` is); `FUN_0003aa2c`=`gp-0x6b94` writer; CAN 399/427 hook sites. Grep `*gp67fa_vs_gp63fd*` / `*fun3aa2c_is_gp6b94*` / `*can_tx_399_427*`.

## V75 stoplight-launch — CLOSED, superseded by [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]
- 17 sub-memories on file — grep `reference_accord_*v75*` / `*gp6b26*` / `*path2*`.

## How I must work
- 🛑 [SendMessage not plain text](feedback_use_sendmessage_not_plain_text.md) · [Grep build_v*_tva.py before any cal](feedback_check_build_scripts_before_proposing_cal_edit.md) · [Check own memory first + variable-reuse trap](feedback_check_own_memory_before_retracing_and_variable_reuse_trap.md).

## Accord TVA-A160
- Friction/seed/angle/RAM/FOC (17, mature): `FUN_00036c12` smooth signed multiply + `0xC407E` census closed · "FactorA"=seed closed, 11ch pinned 1024, `gp+0x6408` UDS-only, `gp+0x63fd` enumerated, live modes 24/26 not 8/10 · `gp-0x69a4` slew floor-0+snap, angle 0.1°/ct, `0xC6B64` rejected · App RAM map, `683c` clear · FOC ISR+PWM map, below `gp-0x6b98` swept. Grep `*friction_lane*` / `*gp6bd0_seed*` / `*gp6408*` / `*gp63fd_full*` / `*mode10_inert*` / `*gp69a4*` / `*angle_position_scale*` / `*smooth_angle_gain*` / `*app_ram_layout*` / `*gate1_gp683c*` / `*foc_inner*` / `*below_gp6b98*`.
- Damper FactorC/E+r24/r26 (6, mature): `FUN_00034350` axis=SPEED; 5-factor product+sign relay, 8km/h dead zone; damping live+gated; task1=1kHz; `gp-0x6b26` sized; near-centre flat zero. Grep `*factorc_e*` / `*fun34350*` / `*task5_100hz*` / `*gp6b26_friction*` / `*near_centre*`.
- Motor-control (7 memories, mature): PWM=4kHz, `FUN_000757a2`->CAN427, `gp-0x6abe`=4.7121x col_degps, 6-LERP FOC, `gp-0x67ac`/`gp-0x67fa` closed, `gp-0x69b0` gate. Grep `reference_accord_pwm_*` / `*fun757a2*` / `*gp6ab*` / `*gp67a*` / `*gp69b0*`.
- 7.5Hz ratchet (6 memories, mature): 7.793Hz; `FUN_00036388` brake; `68ad` dead; rate lane V62-V69; detector live. Grep `reference_accord_ratchet_*` / `*fun36388*` / `*gp68ad*` / `*v72_levera*` / `*rate_lane*` / `*detector_gate*`.
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
- V48B/50/52 `gp-0x4f60` (6 memories, mature): feasibility; reader closure; asymmetry; V50 carryover; lane9; V52 clean. Grep `reference_accord_gp4f60_*` / `*v48b_*` / `*v50_gp4f60*` / `*fun2eda8*` / `*v52_9lane*`.
- Misc (6 memories): V73 gain_A index; ladder monotone; no 7.8Hz divider; mixer 4x falsified; `gp-0x6c2c` TF; shaper rail guard. Grep `reference_accord_gain_a_*` / `*a_ladder*` / `*7hz_divider*` / `*mixer_channels*` / `*gp6c2c*` / `*shaper_rail*`.

## C120/A030/TVA UDS+SA
- [TVA/Accord bootloader map+delta](reference_tva_accord_bootloader_map.md) — BL=0-0xFFFF, SA uses HW RNG, algo unresolved.
