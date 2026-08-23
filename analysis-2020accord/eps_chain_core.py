"""eps_chain_core.py -- SECTIONS 0-1 of the golden model: calibration constants, the signal/
state containers, and the shared integer helpers. Split out of `eps_lkas_chain_model.py` on
2026-08-12 to keep every mandatory-read file under the 256 KB `Read` cap. Code is VERBATIM; import
`eps_lkas_chain_model` for the full facade.

This module has NO intra-kit dependencies -- it is the bottom of the import graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional



# =====================================================================================================
# SECTION 0 -- CALIBRATION CONSTANTS
# -----------------------------------------------------------------------------------------------------
# Every field is a firmware calibration in the CRC-protected 0xC6000 block (unless noted); default is
# the stock (V9b) value, and build variants override a subset (see for_build()). Per-field tp/absolute
# addresses are noted in each field's own trailing comment below.
# =====================================================================================================

V9_FULL_SCALE_POSITIVE = (15360 * 891) >> 15
V9_FULL_SCALE_NEGATIVE = (-15360 * 891) >> 15
V9_FULL_SCALE_MIN_MAGNITUDE = min(abs(V9_FULL_SCALE_POSITIVE), abs(V9_FULL_SCALE_NEGATIVE))


@dataclass
class Calibration:
    # ---- LKAS reach (V14/V18 lineage, retained by V31 & V37) --------------------------------------
    lkas_output_gain: int = 891          # Q15 arb output gain. V31/V37=1782; V38=3564 (4x stock)
    # 0xC646C has 6 readers: 1 forward (this field), 1 dead, 4 feedback (shared_sensor_scale below).
    # V57 decouples the forward reader onto private cal 0xC6CD0, reverting 0xC646C to stock 891 for
    # the feedback readers only. Gain history is TWO doublings: 891 (V9) -> 1782 (V22-V37) -> 3564 (V38+).
    shared_sensor_scale: int = 891       # 0xC646C as seen by the 4 feedback readers; == lkas_output_gain
                                         # through V56, reverts to stock 891 on V57 (decoupled).
                                         # 🛑 3564 again on V76/V78/V79/V80 -- the V38 rebase silently
                                         # dropped V57's decouple (see the header block).
    arb_output_clamp: int = 512          # symmetric arb clamp. V31/V37=1024; V38=2048
    pack_output_clamp: int = 512         # symmetric limit&pack clamp. V31/V37=1024; V38=2048
    reengage_ramp_step: int = 0x11       # re-engage/debounce ramp ceiling (17). V31/V37 -> 0x1B (27)

    # ---- CAN setpoint shaping (CODE literals, shown as cals for readability) -----------------------
    setpoint_scale: int = -4             # STEER_TORQUE * -4  (sign + Q-shift), FUN_00052676
    setpoint_clamp: int = 0x4000         # +/- clamp on the scaled setpoint
    setpoint_fault_sentinel: int = 0x7FFF  # written on checksum/counter/timeout fault
    lkas_validity_timeout_ticks: int = 500  # STEER_TORQUE staleness timeout

    # ---- Gentle-EME STEER_STATUS debounce SM (V36/V37 disable these) -------------------------------
    # Signals: torque channel = min(|arb signal| >> 5, 255)  (a byte, <=255)
    #          rate   channel = angular-rate magnitude       (u16, <=65535)
    deb_torque_rise: int = 112           # torque > this (rise). V37 -> 255 (u8 max => never fires)
    deb_torque_hold: int = 96            # torque > this (hold). V37 -> 255
    deb_torque_and_hi: int = 64          # torque > this AND rate>deb_rate_and_hi. V37 -> 255
    deb_torque_and_lo: int = 54          # torque > this AND rate>deb_rate_and_lo. V37 -> 255
    deb_rate_primary: int = 1600         # rate > this (alone). V37 -> 65535 (u16 max => never fires)
    deb_rate_and_hi: int = 896           # combined tier A. V37 -> 65535
    deb_rate_and_lo: int = 1280          # combined tier B. V37 -> 65535
    deb_count_seed: int = 5              # counter starts at -5; fires after 5 sustained qualifying cyc
    deb_hold_seed: int = 100             # STEER_STATUS=4 hold length once fired

    # ---- DTC-0x49 fault counter (V37 disables via the gate) ----------------------------------------
    dtc49_torque_gate: int = 112         # counter B increments while torque > this. V37 -> 255 (off)
    dtc49_saturation: int = 100          # counter B trips DTC 0x49 after this many cycles (50+50)

    # ---- Engage/disengage decider gates (the "engage SM"; V33/V34/V35 tried these, none were it) ---
    dec_torque_max: int = 320            # voter MAX torque >= this -> refuse/leave (verdict 2)
    dec_angle_consensus: int = 4825      # angle deviation >= this -> verdict 4
    dec_rate_gate: int = 1600            # rate magnitude >= this -> refuse (verdict 5)
    dec_gate6: int = 4096                # gp-0x4f68 >= this -> refuse (verdict 6)
    dec_gate7: int = 3584               # gp-0x6ba4 >= this -> verdict 7

    # ---- Low-speed steer lockout: two-sided speed window at top of FUN_00028ea6. [VERIFIED] ---------
    # vs gp-0x6a5e (voted vehicle speed, 64.0625 counts/km/h); failing it is the ONLY writer of
    # STEER_STATUS=3, which gates STEER_CONTROL_ACTIVE + the authority ramp; each cal has exactly one
    # reader image-wide. The bypass gp-0x68b3 (set only at true standstill, FUN_0004d0d0) is a runtime
    # flag, not a field here -- see steer_status_low_speed_lockout(). resonance_lane_output_bound_q15
    # is FUN_0003a382's Q15 output-bound LERP Y[0]/Y[1] (0xC6AFC/FE): V54 measured it selecting unity
    # in 100% of normal frames; V56 zeroed it (muted the lane) and was later reverted.
    resonance_lane_output_bound_q15: int = 32768   # 0xC6AFC / 0xC6AFE. V56 -> 0
    speed_window_lo: int = 320           # tp+0x72ea (0xC62EA) = 4.995 km/h = 3.104 mph. V53 -> 0
    speed_window_hi: int = 12800         # tp+0x72e8 (0xC62E8) = 199.8 km/h. Never edited (0x7FFF SNA
                                         #   sentinel must keep failing this bound).

    # ---- Soft-EME windup shaper (V30 widens corridor; V31 adds the boost floor) --------------------
    corridor_upper: int = 1024           # corridor arm magnitude (driver-override arm). V31/V37 -> 4096
    corridor_lower: int = -1024          #                                               V31/V37 -> -4096
    boost_floor: int = 0                 # boost arm Y[0] (stock 0/1536/2048). V31/V37 -> flat 4096
    boost_y1: int = 1536                 # boost arm Y[1].                     V31/V37 -> 4096
    boost_y2: int = 2048                 # boost arm Y[2].                     V31/V37 -> 4096
    authority_scale: int = 1092          # authority = (|integrator>>15| * this) >> 10
    sm2_arm: int = 16384                 # authority threshold; entry also requires command and gate!=3
    sm3_clamp: int = 30720               # |integrator>>15| saturation threshold before SM3 dwell
    sm1_arm: int = 2048                  # SM1 (fast anti-runaway; velocity+opposition gated) -- untouched
    corridor_gate: int = 9216            # corridor arm forced off when |pos_err| <= this (hands-off)
    boost_latch_auth: int = 16384        # boost arm latched to 0 once authority > this ...
    boost_latch_dwell: int = 20          #   ... sustained this many cycles
    sm2_variant_gate: int = 3            # tp+0x74cc; 3 inhibits the SM2 authority-threshold entry
    sm3_dwell: int = 20                  # tp+0x7298; saturation dwell before factor becomes cal_7420
    sm3_cut_factor_q15: int = 0          # tp+0x7420; V38/V39 cut factor
    shaper_mode: int = 0                 # tp+0x74c8; selects gp-0x6acc preprocessing
    shaper_bias: int = 0                 # tp+0x71d4
    shaper_term_selector: int = 0        # tp+0x74c9; 0 selects computed r28 as final r20

    # ---- Downstream fixed clamps (CODE literals in the limit cascade) ------------------------------
    arb_setpoint_limit: int = 15360      # symmetric +/- clamp on the LKAS setpoint. [VERIFIED,
                                         # byte-dumped] a degenerate 9-point LERP, flat 15360 at every
                                         # breakpoint in all 28 records/5 banks; axis gp-0x6a5e (voted
                                         # VEHICLE SPEED) is moot since the Y row is flat. Selected by
                                         # gp-0x674e, static per part number (A160 -> selector 1, record
                                         # 0xE41A8). openpilot's torqueBP*4=16384 clips the top 6.25% at
                                         # 15360; raising is safe (no float twin). V38 patches all 8
                                         # reachable per-part-number records (72 halfwords total,
                                         # build_v38_tva.py, verifies 49/49).
    assist_ramp_ticks: int = 10          # tp+0x74d1 * 10; assist engage-ramp dwell per state (gp-0x68c8)
    distribute_lkas_lane_clamp: int = 0x2800   # LKAS rides the +/-0x2800 distributor lane
    mixer_gate_clamp: int = 0x2800       # gate: |x|<=0x2800 ? x : 0x7FFF-sentinel
    shaper_final_clamp: int = 0x2000     # shaper output final +/-0x2000 clamp
    runtime_governor: int = 4762         # NOMINAL CEILING of the computed runtime governor gp-0x4f64
                                          #   (cal 0xC6202). NOT a flat clamp -- see soft_eme_windup_shaper
                                          #   for the MIN(4762, adaptive LERP, unresolved budget B) schedule.
    governor_slew_step_normal: int = 512 # tp+0x7206 (0xC6206), before a Q15 step scale. V40 -> 0xFFFF
    governor_slew_step_alt: int = 205    # tp+0x7208 (0xC6208). V40 -> 0xFFFF
                                         # Selector gp-0x67f5 (0=normal else alt); FUN_00041eec forces
                                         # alt with no debounce on a >=65-count vote divergence, pinning
                                         # hard dynamic turns to the slow step.

    # ---- motor-rate adaptive torque cap (bank A, tp+0x620C/0x6224 records; slopes tp+0x6030/0x6038)
    # V40 flattens Y to the table max AND zeroes the slopes; a flat Y with live slopes still
    # interpolates. See rate_cap_binding_analysis() for why this matters only above stock reach.
    rate_cap_y: tuple = (5325, 3584, 2406, 1587, 512)
    rate_cap_slope_q13: tuple = (-21940, -12059, -5593, -22021)

    # ---- V39 experimental direct torque-rate guard (CODE literals / reused driver threshold) ------
    suppress_direct_torque_rate_assist: bool = False
    direct_rate_lkas_threshold: int = V9_FULL_SCALE_MIN_MAGNITUDE  # 417; includes +/- V9 full scale

    build: str = "V9"

    @staticmethod
    def for_build(name: str) -> "Calibration":
        """Return the calibration set for any modelled build (V9 .. V57)."""
        cal = Calibration(build=name)
        if name == "V9":
            return cal
        # --- V31: 2x reach + soft-EME fix (corridor x4 + boost floor 4096) --------------------------
        cal = replace(
            cal,
            lkas_output_gain=1782, shared_sensor_scale=1782,
            arb_output_clamp=1024, pack_output_clamp=1024, reengage_ramp_step=0x1B,
            corridor_upper=4096, corridor_lower=-4096, boost_floor=4096, boost_y1=4096, boost_y2=4096,
        )
        if name == "V31":
            return cal
        # --- V37 onward: gentle-EME debounce SM off + DTC-0x49 counter off -------------------------
        if name in ("V37", "V38", "V39", "V40", "V41", "V42", "V53", "V54", "V55", "V56", "V57"):
            cal = replace(
                cal,
                deb_torque_rise=255, deb_torque_hold=255, deb_torque_and_hi=255, deb_torque_and_lo=255,
                deb_rate_primary=65535, deb_rate_and_hi=65535, deb_rate_and_lo=65535,
                dtc49_torque_gate=255,
            )
            if name == "V37":
                return cal
            cal = replace(
                cal,
                lkas_output_gain=3564, shared_sensor_scale=3564,
                arb_output_clamp=2048, pack_output_clamp=2048,
                corridor_upper=5120, corridor_lower=-5120,
                boost_floor=5120, boost_y1=5120, boost_y2=5120,
                arb_setpoint_limit=16384,
            )
            if name == "V38":
                return cal
            # --- V53: V38 + FOURFRAME2 read-only telemetry cave + min steer speed 0. FLASHED; the
            # speed-window prediction below is CONFIRMED on-car (route 1a); the telemetry cave never
            # transmitted (uninterpretable null, does not affect this model). Cut from V38, so it does
            # NOT carry V42's ratchet fix.
            if name == "V53":
                return replace(cal, speed_window_lo=0)
            # --- V54: V38 + speed-window-0 + a report-only gp-0x6966 (soft-EME authority) probe on CAN
            # 0x14A byte4 bits 7:3. FLASHED, fault-free. MEASUREMENT (route 1b): authority stayed in
            # [0,127] (~0.39% of saturation) with zero variation -- V31's boost floor (5120, not the
            # memoried 4096) prevents windup, so authority is ~0 BY DESIGN on every V31+ build. The
            # 0xC6AF0 LERP therefore selects unity in ~100% of normal operation; GATE 2 (the lane's
            # damping sign) remains OPEN.
            if name == "V54":
                return replace(cal, speed_window_lo=0)
            # --- V55: V38 + speed-window-0 + a DUAL report-only probe on CAN 0x14A: damper-variant
            # index bit + a 4-bit window on gp-0x6b98 (final merged command). BUILT to PARTITION whether
            # the ~21 Hz mode is commanded or plant-only. FLASHED (route 1c): the mode IS in gp-0x6b98
            # (coherence 0.93 with the sensor); openpilot's own contribution is 8.7-38x too small to
            # explain it and is exactly 0 while railed yet the command still carries the mode, so the
            # loop closes INSIDE the EPS; the sensor->command transfer is flat across 1-21 Hz, ruling out
            # every 0xC646C-gated (filtered) lane; bit7=1 in 100% of frames confirms V44/V47 hit the live
            # damper tables. Direction (damping sign) is NOT settled by this closed-loop measurement --
            # that is V56's GATE 2.
            if name == "V55":
                return replace(cal, speed_window_lo=0)
            # --- V56: V55 + mute FUN_0003a382's residual lane (0xC6AF0 LERP Y[0]/Y[1] -> 0, both the
            # below-knot and interpolated paths). BUILT then FLASHED (route 24, first road drive with a
            # probe): 21 Hz UNCHANGED (786x engaged/disengaged, matching V55) -- gp-0x6ad4/FUN_0003a382
            # is ELIMINATED as the source, all three branches at once -- AND operator reports damping
            # removed, with a new sharp 8.69 Hz line appearing 15-20 m/s engaged+hands-off. REVERTED to
            # V55; a partial restore is not a candidate (0% and 100% authority gave the same 21 Hz).
            # Monitor/protection risk was and remains closed; the real cost was manual feel.
            if name == "V56":
                return replace(cal, speed_window_lo=0, resonance_lane_output_bound_q15=0)
            # --- V57: V55 (not V56) + (A) decouple 0xC646C's forward LKAS reader onto private cal
            # 0xC6CD0 (still 3564), reverting the shared cal to stock 891 for the 4 feedback readers
            # only -- expected NULL for the 20-25 Hz mode (<=0.28 dB at 22 Hz, the most attenuated
            # aggregator lane) and NULL for manual feel (operator has driven 891/1782/3564 and reports
            # no difference; disengaged, only the feedback readers are live). (B) a report-only
            # deadband-gate probe on CAN 0x14A (bit6 tests gp-0x6806==0 by exact equality, closing a
            # parity gap in the prior STEER_CONTROL_ACTIVE measurement); expected NEGATIVE.
            if name == "V57":
                return replace(cal, speed_window_lo=0, shared_sensor_scale=891)
            if name == "V39":
                return replace(cal, suppress_direct_torque_rate_assist=True)
            # --- V40: V38 baseline (NOT V39 -- the r24 guard is dropped entirely) + two cal edits.
            # 1. governor slew steps -> 0xFFFF, so recovery after a sign-crossing reset is immediate
            # 2. motor-rate cap flattened to the table max with zeroed slopes, so the taper never binds
            if name == "V40":
                return replace(
                    cal,
                    governor_slew_step_normal=0xFFFF, governor_slew_step_alt=0xFFFF,
                    rate_cap_y=(5325,) * 5, rate_cap_slope_q13=(0, 0, 0, 0),
                )
            # --- V41: V38 + the cap flatten ONLY. 0xC6000 untouched, so the slew stays stock.
            # FLASHED 2026-07-20: boots and drives cleanly, fixes NEITHER symptom. Falsifies the cap
            # as a root cause, and exonerates the cap flatten as V40's ignition-fault mechanism.
            if name == "V41":
                return replace(cal, rate_cap_y=(5325,) * 5, rate_cap_slope_q13=(0, 0, 0, 0))
            # --- V42: V38 + RAMP-TIME PARITY on the merged-governor slew. Steps scaled by the same 4x
            # V38 applied to reach, restoring stock's cycles-to-full-command. Cap left STOCK (V41
            # falsified it, so there is no reason to carry that edit). Targets the RATCHET only --
            # see gain_rescaling_invariance_analysis() for why it cannot touch the 5 mph vibration.
            if name == "V42":
                return replace(cal, governor_slew_step_normal=2048, governor_slew_step_alt=820)
        raise ValueError(
            f"unknown build {name!r} "
            f"(expected V9, V31, V37, V38, V39, V40, V41, V42, V53, V54, V55, V56, or V57)")


# =====================================================================================================
# SECTION 1 -- SIGNAL / STATE CONTAINERS
# =====================================================================================================

@dataclass
class CanSteeringControl:
    """[CONFIRMED] CAN 0xE4 STEERING_CONTROL from the comma (openpilot -> EPS). DLC 5.
    STEER_TORQUE = signed 16-bit, bytes[0:1] big-endian, range ~ +/-4096 (opendbc _bosch_2018.dbc).
    Also carries STEER_REQUEST / status bits in byte2/byte4 and a checksum+counter for validity."""
    steer_torque: int = 0        # signed16 BE, +/-4096  [CONFIRMED anchor #1]
    steer_request: bool = False  # request/enable bit (byte2/byte4)
    checksum_ok: bool = True     # comms-validity (intake gate; cannot cut on value)
    counter_ok: bool = True
    fresh: bool = True           # not stale (within lkas_validity_timeout_ticks)


@dataclass
class SensorInputs:
    """Physical plant sensors read by the EPS ADC / resolver each loop."""
    # [CONFIRMED anchor #2] steering-wheel (column) torque sensor -- 3 redundant channels read via the
    # hardware Timer Array Unit (TAUA0 capture regs @0xFFFFC400), float-scaled -- NOT raw ADC coils.
    column_torque_coils: tuple = (0, 0, 0)   # 3 raw torque channels (timer-capture, float-scaled)
    column_torque_refs: tuple = (0, 0, 0)    # 3 reference channels for plausibility
    column_torque_sensor_b: Optional[int] = None  # gp-0x4f60; explicit replay input when available
    column_torque_rate: Optional[int] = None      # gp-0x4f62; exact replay overrides local 4-sample model
    # [VERIFIED] derived plant signals used downstream:
    steering_angle: float = 0.0              # column angle
    steering_angle_rate: float = 0.0         # column angular velocity (deg/s-ish, signed)
    # [VERIFIED] two real speed consumers exist: FUN_00028ea6's low-speed window (cals 0xC62EA/0xC62E8,
    # gating STEER_CONTROL_ACTIVE + the authority ramp) and the G1 governor FUN_0004503c (cal 0xC6316
    # skips the slew limiter below ~10 km/h); no aggregator lane and no rate-adaptive table reads road
    # speed -- those are keyed on motor/resolver electrical-angle rate (gp-0x6ac0) instead.
    vehicle_speed: float = 0.0               # km/h; consumed by steer_status_low_speed_lockout()
    eps_temperature: float = 25.0            # thermal-gain compensation input
    foc_rotor_angle: float = 0.0             # resolver atan2 electrical angle
    foc_phase_currents: tuple = (0.0, 0.0)   # measured phase currents (FOC feedback)
    motor_rate_raw: int = 0                  # gp-0x6ac0, motor resolver electrical-angle rate

    # The normalization that maps gp-0x6ac0 to the governor table axis is only partly characterized.
    # None means "term not replayed; assume nonbinding", never "firmware computed exactly this value".
    governor_axis_z: Optional[int] = None
    governor_budget_limit: Optional[int] = None
    governor_motor_state: int = 1            # gp-0x4e5a; states 0/2 omit the unresolved budget minimum
    runtime_governor_override: Optional[int] = None  # observed gp-0x4f64, preferred for RAM replay
    governor_limit_scale_q15: int = 0x8000   # exact bank output can be supplied; identity by default
    governor_post_scale_q15: int = 0x8000
    governor_step_scale_q15: int = 0x8000
    governor_slew_alt: bool = False
    governor_substitution_state: int = 0  # gp-0x67fa; state 4 keeps the lower-magnitude held value
    # gp-0x6ad0: input to FUN_000456a4, a WRITE-ONLY telemetry mirror (no reader anywhere image-wide)
    # of a rate-vs-motor-rate compensation term (two 3-point LERPs, gate-threshold @0xC6830 falling,
    # min-clamp @0xC67D0 rising, gain cal 0xC6204=3072/1024=3 exact; ceiling 2560, not the previously
    # recorded 4762). [VERIFIED] The gate is a bare 2-instruction compare (no hysteresis/dwell) on
    # gp-0x6a10 vs LERP1(gp-0x6ac0) -- structurally sufficient for a 0->2560 one-cycle step -- but
    # gp-0x6a10 is NOT command-derived (a separate engage-SM producer chain from gp-0x6ac0's resolver
    # path), so the V38 invariance argument still holds here; all 11 cal cells have zero consumers
    # outside FUN_000456a4, making this the cleanest patch surface found to date if ever revisited.
    post_governor_compensation: int = 0

    # FUN_00042af8 has two distinct inputs: gp-0x6acc drives the integrator; gp-0x6afe + r20 drives
    # final gp-0x6b98. Unfinished producers are explicit replay controls rather than guessed aliases.
    secondary_mixer_command: int = 0          # gp-0x6afe
    shaper_upper_bound_override: Optional[int] = None  # r29 / gp-0x6af6
    shaper_lower_bound_override: Optional[int] = None  # r27 / gp-0x6b00
    shaper_term_r20_override: Optional[int] = None     # gp-0x6b04 when C64C9==0
    shaper_blend_q15: int = 0
    shaper_alternate_term: int = 0
    shaper_state_scale_q15_override: Optional[int] = None
    shaper_hands_off: bool = True

    # Unfinished assist producers remain explicit replay inputs rather than invented zero-labelled facts.
    assist_lane_overrides: dict = field(default_factory=dict)


@dataclass
class EpsState:
    """Persistent RAM the state machines carry between ticks. gp-relative address in each comment."""
    # ---- LKAS command pipeline stages ----
    lkas_setpoint: int = 0        # gp-0x69ae (0xFEDF1652) clamp(STEER_TORQUE*-4)
    arb_command: int = 0          # gp-0x6b3c (0xFEDF14C4) arbitration gated command
    mixed_command: int = 0        # gp-0x6b4c, LKAS-internal lane into the demand aggregator
    secondary_mixer_command: int = 0  # gp-0x6afe, separate lane consumed at final shaper output
    merged_command: int = 0       # gp-0x6b98 (0xFEDF1468) post-shaper command to the FOC loop
    q_current_ref: float = 0.0    # FOC q-axis current reference (the actual "motor torque" demand)

    # ---- Driver-torque voter outputs ----
    col_torque_max: int = 0       # gp-0x6a62 (0xFEDF159E) MAX voter (0xFFFF = invalid-sensor sentinel)
    # ✅ RENAMED 2026-08-03 from `col_torque_avg`. gp-0x6a5e is voted VEHICLE SPEED (voter
    # FUN_00041eec, settled 2026-07-29), never column torque; the old name predated that
    # reclassification and read as evidence of a role it never had. All 8 call sites moved together.
    speed_voted: int = 0          # gp-0x6a5e (0xFEDF15A2) AVG voter -- VOTED VEHICLE SPEED
    col_rate_mag: int = 0         # gp-0x6a60 (0xFEDF15A0) angular-RATE magnitude (NOT torque)

    # ---- Engage/disengage decider ----
    engage_state: int = 0         # gp-0x67DC (0xFEDF1824) dispatcher state
    decider_verdict: int = 0      # r12: 0=pass 2=torqueMAX 4=angle 5=rate 6/7=other refusals
    enable_fsm: int = 0           # gp-0x67a4 (0xFEDF185C) ENABLE gate; LKAS passes only in {2,3}

    # ---- STEER_STATUS debounce SM (gentle EME) ----
    steer_status: int = 0         # gp-0x6807 (0xFEDF17F9) 4=NO_TORQUE_ALERT_2 (gentle EME), 7=fault
    deb_counter: int = 0          # gp-0x6757 signed; starts at -deb_count_seed, fires at >=0
    dtc49_counter: int = 0        # gp-0x6758 DTC-0x49 fail counter (interlocked to STEER_STATUS=4)

    # ---- Soft-EME windup shaper (SM2/SM3) ----
    soft_eme_integrator_q15: int = 0  # gp-0x3570 (0xFEDF4A90), signed32 Q15
    iir_envelope: int = 0         # gp-0x3574 column-velocity IIR envelope arm
    boost_latch_state: int = 1    # gp-0x3562; state 2 suppresses boost until authority returns to zero
    boost_latch_counter: int = 0  # gp-0x355c
    boost_latched_off: bool = False  # derived compatibility view used by the monitor abstraction
    authority: int = 0            # gp-0x6966 = (|integrator>>15| * authority_scale) >> 10
    sm2_state: int = 1            # gp-0x355e
    sm2_factor_q15: int = 0x8000  # gp-0x6962; recovery/ramp internals remain an explicit abstraction
    sm2_entry_seen: bool = False
    sm3_state: int = 2            # gp-0x355f
    sm3_counter: int = 0          # gp-0x3568
    sm3_factor_q15: int = 0x8000
    lkas_authority_cut: bool = False  # true when the consolidated modeled state factor reaches zero
    shaper_internal_command: int = 0  # gp-0x6b08, sanitized/preprocessed gp-0x6acc
    shaper_term_r20: int = 0      # gp-0x6b04 on V38/V39 (C64C9==0)

    # ---- Base driver assist (Section 3B) ----
    assist_mode: int = 26         # gp+0x63fd (0xFEDFE3FD) POSITIVE displacement; assist curve select
                                  #   0..33. NOT static (2026-08-05): V73's probe read it live over 104,061
                                  #   frames, switching on EVERY LKAS engagement edge (1.02s on rise, 2.08s
                                  #   on fall, 18/18 transitions, 99.09% lag-matched).
                                  #   🛑 The probe field is 4 BITS and DROPS BIT 4, so its {8,10} readings mean
                                  #   true in {8,24} and {10,26}. Raw 8 is in NO row of 0xCD000 => manual = 24;
                                  #   only row 11 'TVCA4' holds 24 and all four columns come from one row =>
                                  #   engaged = 26 (this default). The car is TVCA4, NOT TVAA1.
                                  #   Writer = FUN_00042746, see below.
    assist_substate: int = 1      # gp-0x67fe EPS assist substate; assist valid only in {1,2}
    plausibility_ok: bool = True  # gp-0x67f4 == 1, converge/plausible flag from the voter FUN_00041eec
    col_torque_sensor_b: int = 0  # gp-0x4f60 (0xFEDF30A0) SENSOR-B (TAS) column torque -- the signal
                                  #   packed to CAN 399 STEER_TORQUE_SENSOR. NOT vehicle speed, and NOT
                                   #   angular velocity (both labels appear in older notes and are wrong).
    col_torque_rate: int = 0       # gp-0x4f62: 4-sample finite difference of Sensor-B torque
    col_torque_history: list = field(default_factory=list)
    motor_rate_raw: int = 0        # gp-0x6ac0: motor resolver electrical-angle rate
    assist_ramp_state: int = 0    # gp-0x682e 4-state assist engage ramp {0,1,2,3}
    assist_ramp_timer: int = 0    # gp-0x68c8 ramp timer vs (tp+0x74d1 * 10)
    assist_rate_state: int = 0    # gp-0x6bb2/4/6/8 cross-tick integrity WATCHDOG (NOT a rate limiter)
    # 🛑🛑 KNOWN DEFECT, 2026-08-23 -- THIS DEFAULT IS WRONG AND IS DELIBERATELY LEFT WRONG.
    #   The real cell is gp-0x6752 = **-1** (accord-gp6752-is-negative-one, verified 3 ways incl.
    #   on-car).  NOTHING in the kit overrides this field, so every _demo()/_self_check() run uses
    #   the PRE-RETRACTION sign, and the 3 call sites in eps_chain_lanes.py inherit it.
    #   ⚠ It is NOT fixed here because _self_check()'s expected values were themselves computed at
    #   +1 (e.g. `_inline_torque_rate_b(st) == 1533` @eps_chain_delivery.py) and flipping the
    #   default breaks them.  Re-deriving those expectations FROM THE FIRMWARE is the fix; editing
    #   them to match the model's new output would make the test agree with the code by
    #   construction and destroy its value.  That is a scoped task, not a one-line change.
    #   ⇒ Until then: READ THE SIGN FROM THE MEMORY, NOT FROM THIS MODEL.
    #   gp-0x6752 is the DRIVER-FRAME <-> AGGREGATOR-FRAME CONVERTER, applied at exactly the 7
    #   sites a signal crosses between frames: 0x3B92E, 0x3B91C, 0x381EE, 0x3668E, 0x358C2,
    #   0x3AB78, 0x3A71A.  🛑 Reason about it by counting FRAME CROSSINGS, never negations.
    assist_polarity: int = 1      # gp-0x6752 assist polarity (-1/0/+1) -- SEE THE DEFECT NOTE ABOVE
    assist_lane: int = 0          # gp-0x6bbe (0xFEDF1442) the base-assist aggregator lane
    boost_fir_out: int = 0        # gp-0x6b9a, signed FUN_0003b66a output; gp-0x6ba6 is its magnitude
    # ★★★ RESOLVED 2026-07-31: gp-0x671a is an OSCILLATION DETECTOR -- a hard-REVERSAL COUNTER, latched.
    # FUN_000428d4 @1 kHz, FSM {neutral, +latched, -latched} at gp-0x67df, dwell gp-0x6759, raw count
    # gp-0x357c. NEUTRAL zeroes dwell AND raw count EVERY tick (0x428FE/0x42906) and exits only if
    # |gp-0x6c2c| > T; a crossing of the OPPOSITE threshold increments; HYST=50 quiet ticks -> neutral.
    #   T = 12800 (0xC620A, ld.h) · HYST = 50 (0xC64DD, ld.bu) · CEIL = 5 (0xC64FA, ld.bu)
    # => reads 0 during smooth steering; `>= 5` means AN OSCILLATION IS HAPPENING.
    # 🛑🛑 MEASURED ON-CAR 2026-07-31 (V64, route 35): IT NEVER ARMS. gp-0x671a and gp-0x67df read ZERO
    # on all 14,980 frames of a 149.8 s all-creep drive with the grinding present throughout, through
    # 1,158 steering-rate sign reversals. The struck prediction below was wrong:
    #   ~~"Arms in ~125-150 ms at 18-21 Hz (half-period 24-28 ms, inside the 50 ms dwell timeout)"~~
    # It reasoned from the DWELL timeout only and never checked whether the INPUT reaches T at all.
    # It does not: |gp-0x6c2c| never crossed 12800 once. => V63/V64's oscillation-gated cal edits
    # (0xC6440, 0xC643E) are INERT on this firmware. Detector-gated damping is CLOSED at this threshold.
    # gp-0x6c2c is filtered motor ACCELERATION, not rate and not torque -- see detector_input_6c2c().
    # ⚠ AND EVEN IF ARMED THE RISE IS SMALL: at the hands-off-creep LERP axis (X=0) the DEFAULT arms are
    # r24 2305 (0xD2AEC) and r26 3072 (gain_A rec0/rec1), vs osc arms 2048 and 1536 -- i.e. Honda's
    # oscillation arms are gain REDUCTIONS. V64 delivers r24 x1.78 and r26 x1.00 (a no-op) against
    # V62's clean x2 on both lanes under every arm.
    # 🛑 THE OUTPUT IS A ONE-WAY LATCH WITH A 5 s HOLD (output stage 0x429A0-0x42A12, the sole st.b to
    # gp-0x671a is 0x42A12): once the held value reaches CEIL it is RE-PINNED to CEIL every tick. The
    # only way down is 5000 consecutive ticks (cal 0xC6270) with gp-0x6a5e >= 640 (cal 0xC62DE) AND
    # raw count == 0.
    # ⚠ CORRECTED 2026-08-03: gp-0x6a5e is VOTED VEHICLE SPEED, not driver torque (voter FUN_00041eec,
    # settled 2026-07-29 -- the same reclassification that invalidated V44/V47's rationale).
    # ✅ CONFIRMED from fresh disassembly (0x429a0-0x429d8): `bh`@0x429A8 RELOADS the hold timer (latch
    # held) iff gp-0x6a5e < 0xC62DE=640=10.0 km/h OR a fresh reversal this tick; ABOVE 10 km/h with no
    # reversal the timer decrements and the latch releases to EXACTLY 0 the tick it hits zero -- a clean
    # 5.0 s timeout, not a probabilistic reload. The old "torque dips every direction change" reading is
    # retired: at highway speed this is a real, self-clearing event flag, not a permanently-reloaded one.
    # Also confirmed (0x429da-0x429f0, `mov r14,r8` fallthrough): the held value passes through 1,2,3,4
    # before saturating at CEIL=5 -- `>=1` is genuinely more sensitive than `>=5`, not a relabel only.
    # ✅ The latch is PROTECTIVE: a per-tick-gated gain would modulate AT the mode frequency, i.e. a
    # parametric pump -- the exact failure mode V58/V59/V60 chased for three builds.
    # 🛑 NOT private to r24/r26 -- also read by FUN_0003a382, FUN_000352b4, FUN_00035b20, FUN_00036c12.
    # Irrelevant to raising the two arm cals; DECISIVE against ever moving T/HYST/CEIL. FUN_0003a382 uses
    # it as a CONTINUOUS LERP INDEX (not a gate) shaping the live P/I/D lane gp-0x6ad4, and FUN_00036c12's
    # friction-comp lane gp-0x6b26 sums into the SAME aggregator. => lowering T changes FIVE things at
    # once, four uncontrolled, one a shape parameter on a lane already known to be load-bearing (V56).
    # By contrast gp-0x67df is CLEAN (2 hits, both inside FUN_000428d4) and T has 4 readers, all inside
    # the detector. CEIL (0xC64FA) is NOT private -- 3 external readers.
    # 🛑 The whole detector body is gated on FUN_00046ea6(5)==0 (bit 5 of gp-0x18d0|gp-0x18d4). If set,
    # FUN_000428d4 jumps 0x428E2 -> 0x42A76 and NEITHER cell is written -- indistinguishable from "T never
    # crossed" on a bus log. RULED OUT as the cause of the V64 null: raw byte scan of all 47 jarl sites
    # (Ghidra's search finds only 44 -- the documented undercount) shows bit 5 has exactly ONE caller
    # image-wide, the detector itself @0x428DA; the only dynamic indices are cals 0xB9A14-16 = 0,2,6.
    # The mask is DTC-driven (tp-0x72c4, stride 28, u32 at +8) and self-clearing (gp-0x18d4 is rebuilt by
    # plain assignment each active-fault sweep); gp-0x18d0 is OR-only but written only on the rare
    # "8+ simultaneous faults, evict oldest" overflow path.
    # The arm selection below is CORRECT as written and was verified in Ghidra 2026-07-31; a subagent's
    # prose summary claimed the opposite polarity and was wrong.
    assist_state_671a: int = 0
    assist_gate_671d: int = 0      # r24's HIGHER-priority override; live (2 writers: 0x3BD2A, 0x41EC6)
    assist_gate_683c: int = 0      # DEAD -- zero st.b writers image-wide, so the 512 arms are unreachable
    assist_gate_6b5e: int = 0      # LERP output on axis gp-0x6bda, tested only as a boolean.
                                  # ★★ RESOLVED 2026-08-04, and it REVERSES the old reading:
                                  # gp-0x6b5e = ((LERP(gp-0x6bda)*0xC63C2)>>10)*polarity, producer
                                  # FUN_000361c8 @0x36256/0x36264 (shadow pair gp-0x4cd8). Trapezoid
                                  # @0xC66CC: X=[-384,-128,128,294,384] Y=[0,4762,4762,717,0],
                                  # 0xC63C2 = 1024 (Q10 unity). r26 == 0 IFF gp-0x6b5e != 0, so r26
                                  # is killed only where the LERP is ZERO -- i.e. |gp-0x6bda| >= 384.
                                  # AND gp-0x6bda is a MARGIN TO A PEAK-HOLD ENVELOPE of driver
                                  # assist torque gp-0x6bf0 (FUN_00036022 @0x36068-0x3608C; envelope
                                  # gp-0x6bd8/gp-0x6bd6 from FUN_00035d38, half-width never < 9390;
                                  # 0xC614A = +-10048, margin cal 0xC614C = 128). HANDS-OFF the
                                  # margin is ~9262 = 24x the threshold.
                                  # => THE GATE DOES NOT KILL r26 IN ORDINARY DRIVING, and least of
                                  # all hands-off at creep. The kill window is a ~512-count sliver at
                                  # the DRIVER-OVERRIDE end (cf. 0xC6156 = 9216).
    assist_slope_q10: Optional[int] = None  # gp-0x69a4; producer RESOLVED @0x355c6 (FUN_000352b4) --
                                  # the local SLOPE of a 10-segment curve, gated |gp-0x4f60| <= 25600.
                                  # 🛑 ~ZERO ON THIS CALIBRATION: FUN_00039702 shows the RAM array
                                  # gp-0x641E..gp-0x6444 is an ADJUSTMENT added in Q10 float to a fixed
                                  # cal base at tp+0x7564, and 0xC6564-0xC658C byte-reads as 40 bytes of
                                  # EXACT ZERO with no writer found for the RAM side (10 of 18 cells
                                  # checked). => r26 contributes ~nothing; r24 carries the lane.
                                  # [BELIEF, not proof: live RAM is unreadable, 8 cells unchecked.]
    previous_assist_slope_q10: int = 0
    assist_slope_history_valid: bool = False
    assist_inline_a: int = 0       # r26 in FUN_0003aa2c, Sensor-B torque-rate x gp-0x69a4
    assist_inline_b_raw: int = 0   # r24 before the optional V39 guard
    assist_inline_b: int = 0       # r24 in FUN_0003aa2c, direct Sensor-B torque-rate lane
    direct_rate_guard_fired: bool = False
    aggregator_reduced_mode: bool = False  # gp-0x67ac==1; dormant with A160 source-mode table
    non_lkas_sum: int = 0
    demand_sum: int = 0           # gp-0x6b94 (0xFEDF146C) aggregator output, lockstep gp-0x4ce0

    # ---- Runtime governor chain ----
    runtime_governor_value: int = 4762  # gp-0x4f64
    governed_demand: int = 0             # gp-0x6ace, after FUN_0004503c clamp/Q15/slew (via FUN_00049a90);
                                         # its ONLY readers are FUN_000456a4/FUN_00045a20, both
                                         # hard-shutdown monitors -- NOT a forward path to the motor.
    governor_initialized: bool = False    # gp-0x1388
    governor_held: int = 0                # gp-0x138a
    post_governor_compensation: int = 0  # gp-0x6ad0
    post_governor_command: int = 0       # gp-0x6acc, shaper/integrator input

    # ---- diagnostics ----
    dtc_0x49_set: bool = False    # DTC 0x49 latched (dash lights + openpilot steerFaultPermanent)
    dtc_0xF00049_set: bool = False  # hard-DTC lockstep (int/float twin divergence) -> motor off


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _div_trunc_zero(numerator: int, denominator: int) -> int:
    """Integer division with V850 `divq` signed truncation toward zero."""
    if denominator == 0:
        raise ZeroDivisionError("firmware model divisor must be nonzero")
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def _range_gate(value: int, limit: int) -> int:
    """Aggregator idiom: an out-of-window lane contributes zero; it is not endpoint-clipped."""
    return value if -limit <= value <= limit else 0


def _signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value

