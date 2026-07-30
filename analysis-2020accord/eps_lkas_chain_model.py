"""
eps_lkas_chain_model.py
=======================================================================================================
Executable PSEUDOCODE model of the 2020 Honda Accord EPS LKAS logic chain, from the openpilot/comma
CAN steering command through to motor torque (3-phase PWM) output.

Platform : 2020 Honda Accord Touring, EPS part 39990-TVA-A160, Renesas V850E2 (little-endian, 1 MB).
Purpose  : a single readable reference for our current understanding of how a CAN STEER_TORQUE request
           becomes motor current -- driver torque sensor path, vehicle speed, the arbitration/limit
           cascade, and every state machine that can gate or cut the LKAS term (engage decider,
           STEER_STATUS gentle-EME debounce, DTC-0x49 counter, soft-EME windup shaper, hard-DTC
           lockstep monitor). It is a MODEL: arithmetic-faithful where we have byte evidence, labelled
           where inferred. Durable findings and session narrative live in docs/HANDOFF-*.md,
           docs/STATE.md, docs/BUILD-LINEAGE.md and memory/ -- not here.

-------------------------------------------------------------------------------------------------------
CONFIDENCE LEGEND
-------------------------------------------------------------------------------------------------------
  [CONFIRMED]  On-car / DBC ground truth: (1) the LKAS torque command on CAN 0xE4, (2) the physical
               steering-wheel torque sensor readings.
  [VERIFIED]   Byte-verified in Ghidra against stock code.bin. Static, not dynamically observed.
  [INFERRED]   Structurally reasoned from disassembly but not pinned instruction-for-instruction.
  [OPEN]       Explicitly unknown / unlocated.

-------------------------------------------------------------------------------------------------------
ADDRESS CONVENTION
-------------------------------------------------------------------------------------------------------
  Ghidra program : code.bin (flat base 0, file-offset == address).
  gp (r4) = 0xFEDF8000  ->  "gp-0xNNNN" is absolute 0xFEDF8000 - 0xNNNN
  tp (r5) = 0xBF000      ->  "tp+0x7NNN" is absolute 0xBF000 + 0x7NNN (e.g. tp+0x746c == 0xC646C)

  CORRECTION OF RECORD: 0xC646C is NOT "the LKAS output gain" -- it is the firmware's single shared
  Q15 sensor-to-command-domain scale, with 6 readers: ONE forward (0x2a1ee, the LKAS setpoint path,
  modelled by lkas_output_gain), ONE dead (0x2a904), and FOUR feedback (0x2b656, 0x2c488, 0x36686,
  0x3684a, modelled by shared_sensor_scale). V38's 891->3564 raised the gain on the feedback paths
  too; V57 decouples the forward reader onto its own cal cell (0xC6CD0) and reverts 0xC646C to stock
  891 for the feedback readers only. See memory/reference-accord-c646c-shared-gain-not-lkas-only.md.

-------------------------------------------------------------------------------------------------------
BUILDS THIS MODEL PARAMETERISES  (Calibration.for_build(...))
-------------------------------------------------------------------------------------------------------
  V9  = reconstructed STOCK baseline (flashed, confirmed-correct reference).
  V31 = V9 + 2x LKAS reach + soft-EME fix (corridor x4, boost floor 4096). FLASHED.
  V37 = V31 + gentle-EME debounce-SM disable + DTC-0x49 gate raise. FLASHED, RESOLVED gentle EME.
  V38 = V37 + 4x-stock LKAS reach (gain 3564) + matched corridor/boost + setpoint limit 16384. FLASHED,
        fault-free; hard turns showed an authority feedback limit (later root-caused, see V42).
  V39 = V38 + experimental suppression of the direct Sensor-B torque-rate lane r24. FLASHED, FALSIFIED
        (fixed neither the ratchet nor the vibration).
  V40 = V38 + governor slew steps -> 0xFFFF + motor-rate cap flattened. FLASHED -> EPS lamp + no power
        steering at ignition. Do not repeat the slew-step edit.
  V41 = V38 + motor-rate cap flattened only (slew untouched). FLASHED, boots clean, FALSIFIED as a
        vibration/ratchet cause; isolates V40's fault to the slew-step edit.
  V42 = V38 + (1) one-byte governor state-4 substitution disable (0x454fe) + (2) r26 adaptive gain
        zeroed. FLASHED: (1) CONFIRMED root cause, fixed the hard-turn ratchet, kept in all later
        builds; (2) FALSIFIED, no effect on the vibration.
  V53 = V38 + FOURFRAME2 read-only telemetry cave + min steer speed 0 (0xC62EA -> 0). FLASHED: speed
        window prediction CONFIRMED on-car; the telemetry cave never transmitted (uninterpretable null).
  V54 = V38 + speed-window-0 + a report-only gp-0x6966 (soft-EME authority) probe on CAN 0x14A. FLASHED:
        authority measured ~0 by design (V31's boost floor prevents windup) on every V31+ build.
  V55 = V38 + speed-window-0 + a report-only probe on gp-0x6b98 (final merged command). FLASHED: proved
        the ~21 Hz mode IS in the command and closes inside the EPS, not commanded by openpilot.
  V56 = V55 + mute the FUN_0003a382 residual lane (0xC6AF0 LERP -> 0). FLASHED: FALSIFIED (21 Hz
        unchanged) and cost hands-off damping -- REVERTED.
  V57 = V55 (not V56) + (A) decouple 0xC646C's forward LKAS reader onto a private cal cell, reverting
        the shared cal to stock 891 for the 4 feedback readers, and (B) a report-only deadband-gate
        probe on CAN 0x14A. Current candidate.

-------------------------------------------------------------------------------------------------------
EXECUTION MODEL
-------------------------------------------------------------------------------------------------------
  BASE TICK    : OSTM0 timer, compare 79999 -> ~80000-cycle period; strong-inference 1 kHz at 80 MHz,
                 not independently confirmed. [VERIFIED: OSTM0 reload | INFERRED: 1 ms]
  STEERING TASK: w_steer_control_task (FUN_0002214a), RTOS task. Gate masks are ECU STATE-MACHINE
                 masks (gp-0x67fa), NOT phase/duty-cycle counters -- arbitration/aggregator/governor/
                 shaper/monitors all run in lockstep at the full task rate whenever the ECU state
                 qualifies (states {4,5,8,10,11} span the group; 0xd30 is a superset of 0xc30).
                 [VERIFIED] State 4 sits inside all three masks and is where the governor's ratchet
                 substitution (fixed in V42) used to fire.
  TASK RATE    : UNRESOLVED in absolute Hz -- w_steer_control_task has no direct JARL callers found;
                 it is reached through a runtime-loaded RTOS TCB table walker not yet located. Cycle
                 counts in this model are exact; milliseconds are deliberately not asserted.
  SENSOR-B RATE: FUN_0007f3f8/FUN_0007e74a produce gp-0x4f62 (torque-rate) with delay cal tp+0x7c42=4
                 producer samples; consumer/producer share the same state-mask phase, so no rate
                 mismatch exists. [VERIFIED functions/delay | OPEN wall-clock Hz]
  DECIDER TASK : engage decider + deliver-commit run on a sibling RTOS task FUN_00022ca0. [VERIFIED]
  FOC + PWM    : shared EI trampoline FUN_0001492a dispatches by EIIC cause: 0x600 -> ADC-complete ->
                 FOC (FUN_00071272); 0x970 -> FUN_00061614 -> TSG20 PWM compare write (the motor).
                 [VERIFIED dispatch | OPEN carrier Hz]
  CAN RX       : hardware mailbox ISR stages STEER_TORQUE into the routed buffer; exact ISR entry not
                 located. [OPEN]
=======================================================================================================
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
                                         # driver torque) is moot since the Y row is flat. Selected by
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
    col_torque_avg: int = 0       # gp-0x6a5e (0xFEDF15A2) AVG voter
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
    assist_mode: int = 10         # gp+0x63fd (0xFEDFE3FD) POSITIVE displacement; assist curve select
                                  #   0..33. =10 for THIS car (ECU-ID slot 2, col tp+0xE012)
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
    assist_polarity: int = 1      # gp-0x6752 assist polarity (-1/0/+1)
    assist_lane: int = 0          # gp-0x6bbe (0xFEDF1442) the base-assist aggregator lane
    boost_fir_out: int = 0        # gp-0x6b9a, signed FUN_0003b66a output; gp-0x6ba6 is its magnitude
    assist_state_671a: int = 0     # exact branch input; physical state label unresolved
    assist_gate_671d: int = 0
    assist_gate_683c: int = 0
    assist_gate_6b5e: int = 0
    assist_slope_q10: Optional[int] = None  # gp-0x69a4; unresolved producer, replay when captured
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
    governed_demand: int = 0             # gp-0x6ace, after FUN_0004503c clamp/Q15/slew
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


# =====================================================================================================
# SECTION 2 -- CAN INTAKE + LKAS SETPOINT
# =====================================================================================================

def can_rx_stage_steer_torque(frame: CanSteeringControl) -> Optional[int]:
    """
    Stage the incoming CAN 0xE4 STEER_TORQUE into the routed LKAS buffer. [VERIFIED] CAN mailbox RX ISR
    (mailbox 0x36) -> FUN_0001cf30/FUN_0001ce68/FUN_0001ddd0 -> FUN_00021724, landing in routed buffer
    0xFEDF6BD8 (int16 BE); exact ISR entry/rate not located. [CONFIRMED] the 0xE4 payload itself.

    The 5 intake gates modelled here (checksum/counter/status/timeout) are comms-validity only -- they
    cannot cut LKAS on a torque/rate value. The separate low-speed steer lockout (cal 0xC62EA, two-sided
    window on voted vehicle speed gp-0x6a5e) is modelled in steer_status_low_speed_lockout() below; it
    IS authority-bearing (gates STEER_CONTROL_ACTIVE + the authority ramp), was flashed as V53 (LO bound
    -> 0), and was confirmed on-car (route 1a: STEER_STATUS=3 never fires; 226 low-speed engaged frames
    appear that are empty on V38). Vehicle speed also gates the G1 governor's slew-limiter skip below
    ~10 km/h, so "no vehicle-speed input in the command path" is a retired claim, not current.
    """
    if not (frame.checksum_ok and frame.counter_ok and frame.fresh):
        return None  # invalid frame -> downstream will use the fault sentinel
    return frame.steer_torque  # signed16, big-endian, as decoded from bytes[0:1]


COUNTS_PER_KMH = 64.0625   # FUN_000522fe implements x41>>6 on a 0.01 km/h raw value (NOT a clean 64)


def steer_status_low_speed_lockout(sensors: "SensorInputs", cal: Calibration) -> bool:
    """True when the speed window FAILS, i.e. firmware writes STEER_STATUS=3 (LOW_SPEED_LOCKOUT).
    [VERIFIED] FUN_00028ea6 (m_steer_torque_arbitration, the live ~1kHz arbitration; FUN_0002a30e is a
    dead copy): compares voted vehicle speed gp-0x6a5e against cal 0xC62EA (LO, tp+0x72ea) and 0xC62E8
    (HI, tp+0x72e8), each with exactly one reader image-wide; bypassed at true standstill via gp-0x68b3
    (set only when gp-0x6a62==0). Failing the window is the ONLY writer of STEER_STATUS=3, which gates
    STEER_CONTROL_ACTIVE and the authority ramp -- authority-bearing, not report-only. [CONFIRMED]
    on-car: ST=3 is 100% below 2 mph and 0% above 4 mph (98,053 frames). Models the SPEED CONJUNCT ONLY:
    the real bVar2 is a 5-way AND, so False here means "the speed window passed", not "STEER_STATUS <=
    2" (e.g. gp-0x69aa==0x8000 "derate" shares the same ST=3 write).
    """
    counts = int(sensors.vehicle_speed * COUNTS_PER_KMH)
    if counts == 0:
        # gp-0x68b3 bypass: FUN_0004d0d0 sets it only when the voted speed cell is EXACTLY 0.
        return False
    return not (cal.speed_window_lo <= counts <= cal.speed_window_hi)


def lkas_process_steer_cmd(steer_torque: Optional[int], st: EpsState, cal: Calibration) -> int:
    """
    Convert the raw CAN STEER_TORQUE into the internal LKAS setpoint. [VERIFIED] FUN_00052676
    (s_lkas_process_steer_cmd): `x*-4` then clamp(+/-0x4000), writing gp-0x69ae (0xFEDF1652); a
    checksum/counter/timeout fault instead writes sentinel 0x7FFF. The -4 flips openpilot's sign
    convention to the EPS motor convention with a Q2 up-shift; full-scale input (4096) lands exactly
    on the -0x4000 wall.
    """
    if steer_torque is None:
        st.lkas_setpoint = cal.setpoint_fault_sentinel  # 0x7FFF, an out-of-range flag consumed later
        return st.lkas_setpoint
    scaled = steer_torque * cal.setpoint_scale                    # * -4
    st.lkas_setpoint = _clamp(scaled, -cal.setpoint_clamp, cal.setpoint_clamp)  # +/-0x4000
    return st.lkas_setpoint


# =====================================================================================================
# SECTION 3 -- DRIVER STEERING-TORQUE SENSOR + VOTER  (the physical steering-wheel torque path)
# =====================================================================================================

def read_column_torque_voter(sensors: SensorInputs, st: EpsState, cal: Calibration) -> None:
    """
    Turn the redundant torque-sensor coil ADC channels into the voted column-torque signals and derive
    the angular-rate magnitude the decider/debounce gates compare against. [VERIFIED] 3 channels from
    TAUA0 capture regs -> FUN_00061ca0/FUN_0006195e (gp-0x4e8c/8a/88 + refs gp-0x4e94/92/90);
    plausibility FUN_00062948; voter FUN_00041eec -> MAX gp-0x6a62 (0xFFFF sentinel on quorum loss) /
    AVG gp-0x6a5e; rate FUN_0003f776 -> gp-0x6a56 then gp-0x6a60 = |gp-0x6a56|. [CONFIRMED] the
    3-channel readings are the physical wheel-torque source. KEY FACT: gp-0x6a60 is a RATE magnitude,
    NOT a torque, and its rising edge is unfiltered (only a fall-limiter), so no debounce exists in the
    rising voter chain.
    🛑 2026-07-30: gp-0x6a56 -- what the EPS transmits as STEER_ANGLE_RATE on 0x14A[2:4]/0x18F[2:4] --
    is NOT independently sensed. FUN_0003f776 (its sole producer, 4 st.h, all inside it) computes
    gp-0x6a56 = clamp(polarity(gp-0x6752) * ((gp-0x6abe * 48 * cal(tp+0x713a)) >> 15), +-12000),
    i.e. a fixed Q15 scale of the MOTOR/resolver electrical rate. The +-12000 is a MAGNITUDE clamp
    recomputed fresh each tick, not a rate/slew limit, and gp-0x6a60 just mirrors its magnitude
    (the min-vs-65535 at 0x3f7f6 never binds). CONSEQUENCE: STEER_ANGLE_RATE is opendbc-named but is
    NOT an independent angle sensor, so "996x on rate vs 877x on torque" is two EPS-internal
    derivations, not independent corroboration -- and because gp-0x6bbe's `baseline` is ALSO
    gp-0x6abe-derived, `rate_error = baseline - angle_rate` may partially cancel. That is why the
    lane's damping sign is UNRESOLVED and why V58 measures its phase on-car instead.
    """
    coils = sensors.column_torque_coils
    valid = sum(1 for c in coils if c is not None)
    if valid < 3:  # cal 0xC6501 = 3-of-4 quorum
        st.col_torque_max = 0xFFFF  # invalid-sensor sentinel (a distinct decider path, kept in V37)
        st.col_torque_avg = 0xFFFF
    else:
        st.col_torque_max = max(abs(c) for c in coils)
        st.col_torque_avg = sum(abs(c) for c in coils) // valid
    st.col_rate_mag = min(abs(int(sensors.steering_angle_rate)), 12000)  # rate magnitude, clamp +/-12000

    # Sensor-B is a signed, independently processed TAS torque channel (gp-0x4f60). During synthetic
    # runs only, fall back to the signed mean of the available coils; RAM/log replay should provide it.
    valid_coils = [int(c) for c in coils if c is not None]
    st.col_torque_sensor_b = (int(sensors.column_torque_sensor_b)
                              if sensors.column_torque_sensor_b is not None
                              else (_div_trunc_zero(sum(valid_coils), len(valid_coils)) if valid_coils else 0))

    # FUN_0007f3f8 calls FUN_0007e74a, which keeps a ring and writes lockstep gp-0x4f62/gp-0x4488:
    # 2*(current-delayed)/wrapped_sample_delta, with delay cal tp+0x7c42=4. It runs on phase mask 0xD30
    # while the aggregator consumes on 0xC30. The actual RAM value is the preferred replay input. The
    # local fallback assumes one producer sample per model tick and therefore dt=4.
    if sensors.column_torque_rate is not None:
        st.col_torque_rate = int(sensors.column_torque_rate)
    else:
        st.col_torque_history.append(st.col_torque_sensor_b)
        if len(st.col_torque_history) > 5:
            st.col_torque_history.pop(0)
        st.col_torque_rate = (_div_trunc_zero(2 * (st.col_torque_history[-1] - st.col_torque_history[0]), 4)
                              if len(st.col_torque_history) == 5 else 0)
    st.motor_rate_raw = int(sensors.motor_rate_raw)


# -----------------------------------------------------------------------------------------------------
# SECTION 3B -- BASE DRIVER ASSIST (normal power steering)
# -----------------------------------------------------------------------------------------------------
# Assist is not one term: the demand aggregator (FUN_0003aa2c) sums the boost curve, five sibling lanes,
# two inline Sensor-B torque-rate lanes, and one filtered Sensor-B term:
#     FUN_00034a72 -> gp-0x6bbe   the boost curve proper (the "assist" everyone means)
#     FUN_00034350 -> gp-0x6bd0   5 multiplied gain factors, sign forced opposite gp-0x6abe [damping]
#     FUN_00036c12 -> gp-0x6b26   curve x gp-0x6c2e angle term                   [friction comp]
#     FUN_0003a382 -> gp-0x6ad4   UNFILTERED residual lane (2 passthroughs + a raw derivative)
#     FUN_00036388 -> gp-0x6b62   slow +/-1/tick accumulator w/ hysteresis       [return-to-centre]
#     FUN_000352b4 -> gp-0x6b86 + gp-0x69a4                                      [friction magnitude]
#     inline r24   <- gp-0x4f62 x generated Q10 gain                              [VERIFIED torque-rate]
#     inline r26   <- gp-0x4f62 x avg(gp-0x69a4) x generated Q10 gain             [VERIFIED torque-rate]
#     FUN_00036682 -> filtered Sensor-B term, final slow IIR (6/1024)              [role OPEN]
# Bracketed roles are [INFERRED] from structure; addresses/plumbing are [VERIFIED].
# -----------------------------------------------------------------------------------------------------

# [VERIFIED, byte-dumped] mode-indexed assist tables, selector = byte at gp+0x63fd (0xFEDFE3FD, NOT the
# LKAS setpoint-limit mode gp-0x674e), range 0..33; written only by factory/diagnostic paths (no CAN RX
# reaches it). Our A160 = ECU-ID slot 2 -> gp+0x63fd = 10 -> curve @0xD2834.
ASSIST_BOOST_X_RISING = (0, 640, 2560, 5120, 8960, 12800)   # the "rising" family (high top-end assist)
ASSIST_BOOST_X_FALLING = (0, 640, 2560, 5120, 7808, 10240)  # the "falling" family -- what THIS car runs
ASSIST_BOOST_CURVE = {                         # pointer array @0xCA154, 6-point LERP, indices 0..33
    #  idx: (X row,                Y row,                              table addr)
    0:  (ASSIST_BOOST_X_RISING,  (612, 787, 992, 1141, 1211, 1238)),   # 0xCE578 (the sensor-A memory's curve)
    4:  (ASSIST_BOOST_X_FALLING, (529, 632, 645, 546, 438, 438)),      # 0xD0834
    6:  (ASSIST_BOOST_X_RISING,  (607, 718, 943, 1145, 1258, 1284)),   # 0xD086C
    10: (ASSIST_BOOST_X_FALLING, (541, 639, 653, 551, 439, 439)),      # 0xD2834  <<< OUR CAR
    11: (ASSIST_BOOST_X_FALLING, (547, 645, 659, 557, 445, 445)),      # 0xD2850  <<< our failover partner
    28: (ASSIST_BOOST_X_FALLING, (568, 635, 647, 540, 438, 438)),      # 0xD8834 (TWA parts)
    33: (ASSIST_BOOST_X_FALLING, (526, 629, 646, 436, 351, 351)),      # 0xD986C (lightest assist in image)
}   # (representative subset; indices 1-3,5,7-9,12-27,29-32 are duplicates/near-duplicates of the above)

# [CONFIRMED] SPORT MODE is NOT implemented by this ECU: all 3 writers of gp+0x63fd were traced and
# none reads a CAN RX buffer (FUN_00042692 boot-latch, FUN_00042746 sensor-fault failover reselector,
# FUN_0004a798 UDS/PasCom bench command only); A160 = ID-table slot 2 "TVAA1" (gp-0x674e=1, gp+0x63fd=10)
# via FUN_00057f8e's own-HW-ID match (the HW-ID itself is programmed at manufacture, not in code.bin).
# Every real TVAA* slot yields the same FALLING assist family and a flat-15360 setpoint record, so
# whatever tightens the wheel in Sport is not this firmware.
# Safety-ceiling curve, pointer array @0xC7970, keyed on the MAX voter. In THIS image every mode is a
# FLAT 512 -- it is a constant ceiling, not a shaped curve. Default fallback tp+0x715a (0xC615A) = 512
# is used when the key is >= 0x7d01 (saturated / the 0xFFFF invalid-sensor sentinel). [VERIFIED]
ASSIST_CEILING_X = (0, 640, 2560, 5760, 6400)
ASSIST_CEILING_Y = (512, 512, 512, 512, 512)
ASSIST_CEILING_DEFAULT = 512                   # tp+0x715a
ASSIST_SENTINEL = 0x7d01                       # >= this => invalid/saturated sensor path
# 🛑 0x3638 is NOT a rate step. FUN_0004613e only snapshots its params into log cells and calls
# FUN_00016de6(0x1c,...) -- a fault LOGGER; 13880 is a diagnostic TAG (the same callee takes 0x38c7
# elsewhere). Its call site @0x34a94 is a cross-tick computation-integrity WATCHDOG on gp-0x6bb2/4/6/8
# re-verifying the SAME +-512 ceiling, with no forward path into any control signal. Corrected 2026-07-30.
ASSIST_RATE_STEP = 0x3638                      # diagnostic tag, kept only so the watchdog is modelled


def _lerp_flat(x: int, xs, ys) -> int:
    """Piecewise-linear interpolation with FLAT extrapolation outside the breakpoints.

    This is the firmware's LERP idiom, byte-confirmed at the setpoint-limit site 0x28fc8-0x29044:
    below xs[0] it returns ys[0] (early exit @0x28fec), above xs[-1] it returns ys[-1] (early exit
    @0x29002), and in between it does (dy * (x - x0)) / dx via `mul` @0x29026 + `divq` @0x2902c.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            span = xs[i + 1] - xs[i]
            return ys[i] + _div_trunc_zero((ys[i + 1] - ys[i]) * (x - xs[i]), span)
    return ys[-1]


def base_driver_assist_lane(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    The base power-steering boost curve: driver column torque -> motor assist demand (lane gp-0x6bbe).
    [VERIFIED] FUN_00034a72, scheduled from w_steer_control_task (phase-mask gating unconfirmed); mode
    select ld.bu gp+0x63fd (0..33); primary key gp-0x6a5e (AVG voter), ceiling key gp-0x6a62 (MAX
    voter); tables: boost @0xCA154, ceiling @0xC7970 (both byte-dumped), plus 4 undumped scaling tables
    [OPEN] (gain-scalar 0xCA324, rate-keyed LERP 0xCA4F4, clamp 0xC7A58, gp-0x69ba LERP 0xCA23C);
    polarity gp-0x6752; gp-0x6bb2/4/6/8 is a cross-tick integrity WATCHDOG, NOT a rate limiter
    (corrected 2026-07-30 -- FUN_0004613e is a fault logger and 0x3638 is its diagnostic tag);
    its own 4-state ramp SM
    (gp-0x682e, timer gp-0x68c8 vs tp+0x74d1*10), separate from the LKAS engage SM; writes gp-0x6bbe,
    lockstep-shadowed at gp-0x4cf0. [OPEN, not yet adopted] a 2026-07-25 trace argues
    gp-0x6a5e/gp-0x6a62/gp-0x6a64 are actually a 5-channel VOTED VEHICLE SPEED (not voted driver torque
    as labelled here) -- supported by unit math (cals 0xC62EA/0xC62E8 divide exactly to 5/200 km/h) but
    not yet verification-passed; if adopted it would reclassify this curve's keys and the V44/V47
    damper mechanism.
    """
    mode = st.assist_mode                             # gp+0x63fd, range 0..33 (NOT 0..7)

    # --- validity gate ("bVar10"): ALL of these must hold or the lane collapses to the ramp-down path
    valid = (st.assist_substate in (1, 2)             # gp-0x67fe  EPS assist substate
             and st.plausibility_ok                    # gp-0x67f4 == 1, from the voter FUN_00041eec
             and st.col_torque_avg < ASSIST_SENTINEL   # gp-0x6a5e not invalid/saturated
             and abs(st.col_torque_sensor_b) <= 25600) # gp-0x4f60 plausibility window (same +/-25600
                                                       #   window the arb hard-bail uses @0x28f30)

    # --- 4-state ramp SM (gp-0x682e), timer gp-0x68c8 vs tp+0x74d1*10 -----------------------------
    if not valid:
        st.assist_ramp_state = 0
        st.assist_ramp_timer = 0
    elif st.assist_ramp_state < 3:
        st.assist_ramp_timer += 1
        if st.assist_ramp_timer >= cal.assist_ramp_ticks:
            st.assist_ramp_state += 1
            st.assist_ramp_timer = 0
    ramp_scale = st.assist_ramp_state / 3.0           # 0 -> 1 over the 4 states

    # --- the boost curve proper: AVG driver torque -> raw assist -----------------------------------
    key_avg = min(abs(st.col_torque_avg), 0xFFFF)
    xs, ys = ASSIST_BOOST_CURVE.get(mode, ASSIST_BOOST_CURVE[10])   # default = this car's curve
    raw = _lerp_flat(key_avg, xs, ys)

    # --- NO rate limiter here. 🛑 Corrected 2026-07-30: the gp-0x6bb2/4/6/8 cluster is a cross-tick
    # WATCHDOG (FUN_00035154 re-derives this lane's ceiling in float and stores a +-5-count tolerance
    # for FUN_00034a72 to check next tick), not a limiter -- it has no forward path into gp-0x6bbe.
    # The model previously clamped `delta` to +-0x3638 here, which limited nothing (0x3638 = 13880
    # against a lane clamped to +-512) and mis-taught the chain. Pass through.
    st.assist_rate_state = raw

    # --- safety ceiling, keyed on the MAX voter (flat 512 in this image) ---------------------------
    key_max = abs(st.col_torque_max)
    ceiling = (ASSIST_CEILING_DEFAULT if key_max >= ASSIST_SENTINEL
               else _lerp_flat(key_max, ASSIST_CEILING_X, ASSIST_CEILING_Y))

    # --- gain modulation, polarity, and the final clamp against the ceiling ------------------------
    # [SIMPLIFIED -- flagged] 0xCA324 (gain scalar) and 0xC7A58 (clamp) still fold in as unmodelled
    # multiplicative factors; this is the one place this function is NOT literal.
    # 0xCA4F4 and 0xCA23C are now DUMPED (2026-07-30): both are pointer tables indexed by mode*4,
    # resolving at mode 10 to the two boost AMPLITUDE curves below. Both are indexed by
    # `boost_amplitude_index` == gp-0x6ba6, applied as `(term * Y) >> 14`.
    amp = boost_amplitude_index(st)
    y1 = _lerp_flat(amp, BOOST_AMP1_X, BOOST_AMP1_Y)      # 0xD28DC via 0xCA4F4
    y4 = _lerp_flat(amp, BOOST_AMP4_X, BOOST_AMP4_Y)      # 0xD2888 via 0xCA23C
    scaled = (int(st.assist_rate_state * ramp_scale) * y1) >> 14
    scaled = (scaled * y4) >> 14
    signed = scaled * st.assist_polarity                                   # gp-0x6752
    return _clamp(signed, -ceiling, ceiling)                               # -> gp-0x6bbe


# --- the boost AMPLITUDE index and its two curves -------------------------------------------------
# 🛑 gp-0x6ba6 == abs(gp-0x6b9a). FUN_0003b66a writes both from one r28: `cmp r0,r28 / mov r28,r13 /
# bge 0x3b886 / subr r0,r13` @0x3b874-87c, then st.h @0x3b892 (gp-0x6ba6) and @0x3b8b0 (gp-0x6b9a).
# Sole writer each, byte-scanned for both gp-relative encodings.
# gp-0x6b9a itself indexes NOTHING: its only live consumer is a 5-input plausibility gate
# (|x| <= 25600 @0x34c9c-cb4 -> r21 -> zeroes r24 @0x34fc8), so its SIGN has no output effect, and two
# of its three reads in FUN_00034a72 are dead (tp+0x7499 == 1 takes the branch @0x34b3c).
# ⇒ V58 measured the SIGNED sibling crossing zero at 20.93 Hz only when LKAS applies, so this index is
# that signal RECTIFIED -- a minimum at every zero crossing, sweeping both curves at ~2x the mode
# frequency on the BASE ASSIST path. Depth is UNMEASURED until V59 flies: below X1 = 512 the
# coefficient is pinned at 16384 and nothing modulates.
BOOST_AMP1_X = (0, 512, 1490, 2529, 3645, 5120)     # 0xD28DC, byte-verified
BOOST_AMP1_Y = (16384, 14657, 11672, 9365, 8244, 8187)
BOOST_AMP4_X = (0, 307, 1024, 1741, 3072, 6144)     # 0xD2888, byte-verified
BOOST_AMP4_Y = (16384, 14392, 10265, 8997, 8176, 8176)

FAULT_SENTINEL_6BA6 = 0xFFFF    # FUN_0003b66a input-gate failure; > 25600 so r21 catches it
FAULT_SENTINEL_6B9A = 0x7FFF


def boost_amplitude_index(st: EpsState) -> int:
    """gp-0x6ba6, the index into both boost amplitude curves; the magnitude of gp-0x6b9a."""
    return abs(st.boost_fir_out)


ASSIST_RATE_CROSS_X = (0, 640, 3200, 6400)  # gp-0x6a5e AVG-voted torque magnitude

# FUN_0003ad74 cross-interpolates each X/Y element across the four AVG-torque records, producing the
# runtime arrays consumed by FUN_0003aa2c. Y is Q10 (1024 == 1.0); every value is byte-verified.
ASSIST_RATE_B_RECORDS = (
    ((0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),
    ((0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),
    ((0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),
    ((0, 400, 1500, 3000), (2151, 2151, 2049, 1947)),
)
ASSIST_RATE_A_RECORDS = (
    ((0, 400, 1600, 3000), (3072, 3072, 2434, 2048)),
    ((0, 250, 1200, 3000), (3072, 3072, 2488, 1536)),
    ((0, 400, 1250, 3000), (2664, 2664, 2243, 1436)),
    ((0, 400, 1250, 3000), (2560, 2560, 2145, 1331)),
)
ASSIST_TORQUE_RATE_CLAMP = 5120             # aggregator input clamp on gp-0x4f62
ASSIST_TORQUE_RATE_DEADZONE = 3              # tp+0x71f6 (0xC61F6)
ASSIST_TORQUE_RATE_OUTPUT_CLAMP = 8192


def _generated_assist_rate_curve(avg_torque: int, records) -> tuple:
    """Reproduce FUN_0003ad74's element-by-element cross-interpolation."""
    key = _clamp(avg_torque, ASSIST_RATE_CROSS_X[0], ASSIST_RATE_CROSS_X[-1])
    xs = tuple(_lerp_flat(key, ASSIST_RATE_CROSS_X, tuple(record[0][i] for record in records))
               for i in range(4))
    ys = tuple(_lerp_flat(key, ASSIST_RATE_CROSS_X, tuple(record[1][i] for record in records))
               for i in range(4))
    return xs, ys


def _assist_rate_gain_q10(st: EpsState, records) -> int:
    # Invalid voter path substitutes tp+0x7314=5120 for the AVG cross-axis.
    avg_key = abs(st.col_torque_avg) if st.plausibility_ok else 5120
    xs, ys = _generated_assist_rate_curve(avg_key, records)
    # Firmware folds an out-of-domain motor rate >=13001 back to zero before the LERP.
    rate_key = st.motor_rate_raw if 0 <= st.motor_rate_raw < 13001 else 0
    return _lerp_flat(rate_key, xs, ys)


def _inline_torque_rate_b(st: EpsState) -> int:
    """FUN_0003aa2c r24: the direct, inertia-sensitive Sensor-B torque-rate assist lane."""
    gain_q10 = _assist_rate_gain_q10(st, ASSIST_RATE_B_RECORDS)
    if st.assist_gate_671d != 0:
        gain_q10 = 1024                              # tp+0x7442 (0xC6442)
    elif st.assist_gate_683c != 0:
        gain_q10 = 512                               # tp+0x7446 (0xC6446)
    elif st.assist_state_671a >= 5:
        gain_q10 = 2048                              # tp+0x7440 (0xC6440)

    dtorque = _clamp(st.col_torque_rate, -ASSIST_TORQUE_RATE_CLAMP, ASSIST_TORQUE_RATE_CLAMP)
    scaled = (dtorque * gain_q10) >> 10              # V850 `sar`: floor for negative products
    if scaled > ASSIST_TORQUE_RATE_DEADZONE:
        shaped = scaled - ASSIST_TORQUE_RATE_DEADZONE
    elif scaled < -ASSIST_TORQUE_RATE_DEADZONE:
        shaped = scaled + ASSIST_TORQUE_RATE_DEADZONE
    else:
        shaped = 0
    return _clamp(st.assist_polarity * shaped,
                  -ASSIST_TORQUE_RATE_OUTPUT_CLAMP, ASSIST_TORQUE_RATE_OUTPUT_CLAMP)


def _inline_torque_rate_a(st: EpsState) -> int:
    """
    FUN_0003aa2c r26 -- the ADAPTIVE Sensor-B torque-rate lane. Returns zero until gp-0x69a4 is
    replay-supplied. [VERIFIED] r26 = clamp(polarity * ((dtorque * avg(gp-0x69a4)) >> 10 * gain_A) >>
    10, +/-0x2000), dtorque = clamp(gp-0x4f62, +/-5120) -- the same dtorque and the same single
    polarity read (gp-0x6752 @0x3ab78) as r24, so r24 and r26 always carry the SAME sign (gp-0x69a4 is
    an unsigned magnitude at both ends); V39 zeroing r24 therefore removed half of a same-signed pair,
    not a counterweight. r24 applies a +/-3 deadzone (cal 0xC61F6) before its polarity multiply; r26
    has none, so near zero dtorque r26 is the only live derivative lane -- V39 predicted a no-op for
    the ~5 mph small-command regime independent of the invariance argument. r26 also has a persisted
    2-sample rolling average and a hard zero-force gate (gp-0x6b5e!=0 AND assist_state_671a < cal
    0xC64FA) that r24 lacks. GAIN_A is a 4-point flat LERP over motor-rate gp-0x6ac0 (zeroed >= 13001)
    against a table FUN_0003ad74 rebuilds each cycle from 4 ROM records on the AVG-torque axis
    (ASSIST_RATE_A_RECORDS, cals 0xC6A68/7C/90/A4); the cal-only kill surface is 18 halfwords (16 Y
    values 0xC6A72-B4, overrides 0xC6444/0xC643E), all single-reader, no float mirror. [OPEN] r26's
    realistic magnitude (clips only if avg(gp-0x69a4) > ~546); the mechanical loop sign
    (positive-feedback vs feedforward, needs live telemetry, not disassembly); gp-0x6752's concrete
    runtime value.
    """
    if st.assist_slope_q10 is None:
        return 0

    state_lt_5 = st.assist_state_671a < 5
    selected_state_value = 1 if state_lt_5 else 0     # C6138=1 / C6136=0
    if st.assist_gate_6b5e != 0 and selected_state_value == 1:
        pre_polarity = 0
    else:
        current = int(st.assist_slope_q10) & 0xFFFF
        previous = st.previous_assist_slope_q10 if st.assist_slope_history_valid else current
        st.previous_assist_slope_q10 = current
        st.assist_slope_history_valid = True
        avg_slope_q10 = (current + previous) >> 1

        gain_q10 = _assist_rate_gain_q10(st, ASSIST_RATE_A_RECORDS)
        if st.assist_gate_683c != 0:
            gain_q10 = 512                           # tp+0x7444 (0xC6444)
        elif not state_lt_5:
            gain_q10 = 1536                          # tp+0x743e (0xC643E)

        dtorque = _clamp(st.col_torque_rate, -ASSIST_TORQUE_RATE_CLAMP, ASSIST_TORQUE_RATE_CLAMP)
        stage1 = (dtorque * avg_slope_q10) >> 10
        pre_polarity = (stage1 * gain_q10) >> 10

    return _clamp(st.assist_polarity * pre_polarity,
                  -ASSIST_TORQUE_RATE_OUTPUT_CLAMP, ASSIST_TORQUE_RATE_OUTPUT_CLAMP)


def assist_shaping_lanes(sensors: SensorInputs, st: EpsState) -> dict:
    """
    The five sibling assist-shaping lanes (Section 3B), each writing its own aggregator lane rather than
    applying in series to the boost curve; all read gp-0x6a5e (AVG torque) directly. [VERIFIED
    addresses; INFERRED role labels] FUN_00034350 -> gp-0x6bd0 (damping) is the product of 5
    mode-indexed LERP gain factors (a MIN-clamped seed, a flat driver-torque table, an angle-deviation
    term, |motor rate| gp-0x6ac0, and gp-0x6ac2), sign forced opposite gp-0x6abe; two independent
    hands-off deadzones exist (Factor C's Y[0]=0 below 2240 counts driver torque, mode 10/11
    @0xD27BC/D27D0, raised by V44/V47; Factor E's Y[0]=0 below 60 counts motor rate, @0xD27F8/D280C,
    raised only by V47), and its output clamp is a dynamic LERP keyed on gp-0x6ac2 (@0xD209C/D20A8)
    with a float-mirror lockstep at cal 0xC6554/58/5C/60 (DTC-0x1d no-debounce hard shutdown on
    divergence -- any edit to the int clamp table needs a bit-exact float twin). FUN_00036c12 ->
    gp-0x6b26 (friction comp) is LERP(AVG torque, @0xCBE74) x gp-0x6c2e, range-limited. FUN_0003a382 ->
    gp-0x6ad4 (resonance lane) is a genuine discrete PID on ERR = clamp(gp-0x4f60 - bias, +/-0x2800):
    P = (LERP(motor_rate)*ERR>>10)*32, I = accumulate(98*ERR>>10), D = clamp((ERR-ERR_prev)*2048>>10,
    +/-0x2800)*32, summed and rescaled to +/-ceiling; both of its smoothing EMAs (cals 0xC6450, 0xC644A)
    are Q10 unity (defeated passthroughs, not lags) -- V43/V46 each re-introduced one pole and both were
    flashed null, and V56's mute of this lane's output bound also left the ~21 Hz mode unchanged,
    eliminating this lane as the sole source (it enters gp-0x6b98 through one of the other eight
    aggregator lanes). FUN_00036388 -> gp-0x6b62 (return-to-centre) is a slow +/-1/tick accumulator
    with hysteresis. FUN_000352b4 -> gp-0x6b86 + gp-0x69a4 (friction magnitude) zeroes only OUTSIDE the
    +/-25600 Sensor-B plausibility window; its adaptive 10-segment magnitude is [OPEN]. inline r24/r26
    are the Sensor-B torque-rate lanes modelled by _inline_torque_rate_b/_a above.
    """
    supplied = sensors.assist_lane_overrides
    st.assist_inline_a = _inline_torque_rate_a(st)
    st.assist_inline_b_raw = _inline_torque_rate_b(st)
    st.assist_inline_b = st.assist_inline_b_raw

    sensor_b_valid = -25600 <= st.col_torque_sensor_b <= 25600
    magnitude = int(supplied.get("magnitude_6b86", 0)) if sensor_b_valid else 0
    magnitude = _clamp(magnitude, -0x3000, 0x3000)  # producer's verified final bound

    # The remaining role names are structural inference. Their values stay explicit replay inputs.
    return {
        "inline_a": st.assist_inline_a,
        "inline_b": st.assist_inline_b,
        "magnitude_6b86": magnitude,
        "damping_6bd0": int(supplied.get("damping_6bd0", 0)),
        "friction_6b26": int(supplied.get("friction_6b26", 0)),
        "resonance_6ad4": int(supplied.get("resonance_6ad4", 0)),
        "return_centre_6b62": int(supplied.get("return_centre_6b62", 0)),
        "filtered_36682": int(supplied.get("filtered_36682", 0)),
    }


# =====================================================================================================
# SECTION 4 -- ENGAGE / DISENGAGE DECIDER STATE MACHINE  (the "engage SM")
# =====================================================================================================

def engage_decider(st: EpsState, cal: Calibration) -> int:
    """
    Decide whether LKAS is allowed to deliver this tick, and (if not) why. [VERIFIED] Dispatcher
    FUN_000413ae (state gp-0x67DC) via sibling RTOS task FUN_00022ca0; decider FUN_00040d58 -> verdict
    r12 (disengage hook @0x40e64); consensus helper FUN_000406ae (gp-0x6cc4). Verdict codes: 0=pass,
    2=torque-MAX gate (dec_torque_max, stock 320), 4=angle-consensus, 5=rate gate (dec_rate_gate,
    1600), 6=gate6 (4096), 7=gate7 (3584). The torque-MAX gate (verdict 2) fires ~10 Hz BENIGN and is
    NOT the gentle-EME trigger (V33's raise of dec_torque_max chased the wrong gate) -- the felt gentle
    cut is produced by the debounce SM (Section 5), not here. [OPEN] gp-0x6809 is dead code (0
    writers), so which verdict actually zeroes the motor term is unlocated.
    """
    if st.col_torque_max == 0xFFFF:
        st.decider_verdict = 2        # invalid-sensor sentinel (kept live in V37)
    elif st.col_torque_max >= cal.dec_torque_max:
        st.decider_verdict = 2        # torque-MAX refusal (benign ~10 Hz; NOT the felt cut)
    elif st.col_rate_mag >= cal.dec_rate_gate:
        st.decider_verdict = 5        # rate refusal
    else:
        st.decider_verdict = 0        # pass
    return st.decider_verdict


# =====================================================================================================
# SECTION 5 -- STEER TORQUE ARBITRATION  (setpoint limit + LKAS gain)  with the two inlined SMs
# -----------------------------------------------------------------------------------------------------
# This one function is the crossroads: it limits the LKAS setpoint by a mode/gear LERP curve, applies
# the LKAS gain+clamp in Q15, and inline hosts two counters off the same torque channel -- the
# STEER_STATUS debounce SM (gentle EME, fixed V37) and the DTC-0x49 fail counter (dash lights, fixed
# V37). Driver-assist is NOT summed here; it merges downstream as a separate mixer source (Section 6).
# =====================================================================================================

def steer_status_debounce_sm(arb_torque_byte: int, rate_mag: int, st: EpsState, cal: Calibration) -> None:
    """
    The GENTLE-EME producer: a 5-cycle debounce that raises STEER_STATUS=4 (NO_TORQUE_ALERT_2).
    [VERIFIED] Inlined in m_steer_torque_arbitration (~0x29120-0x2931e); FUN_0002a30e/FUN_0002a93a are
    dead out-of-line copies, never executed. Signals: arb_torque_byte = gp-0x682f = min(|arb
    signal|>>5, 255) (@0x29068); rate_mag = clamped angular-rate magnitude (<=65535). Counter gp-0x6757
    (signed) seeded at -deb_count_seed(5), fires STEER_STATUS=4 after 5 sustained qualifying cycles,
    holds deb_hold_seed(100) cycles; all compares are unsigned `cmp;bh`. The qualifying envelope (any
    of 7 tiers true) approximates "moderate torque AND moderate rate together are dangerous even if
    neither is extreme alone"; V37 raises all 7 thresholds to unsigned max so no tier can ever fire,
    and this cut STOPPED on-car (operator-confirmed 2026-07-14).
    """
    qualifies = (
        arb_torque_byte > cal.deb_torque_rise                                             # torque alone (rise)
        or rate_mag > cal.deb_rate_primary                                                # rate alone
        or (arb_torque_byte > cal.deb_torque_and_hi and rate_mag > cal.deb_rate_and_hi)   # combined tier A
        or (arb_torque_byte > cal.deb_torque_and_lo and rate_mag > cal.deb_rate_and_lo)   # combined tier B
    )
    # hold tier uses deb_torque_hold(96) hysteresis once already firing -- folded in here for the model
    if st.steer_status == 4:
        qualifies = qualifies or arb_torque_byte > cal.deb_torque_hold

    if qualifies:
        st.deb_counter += 1
        if st.deb_counter >= 0:                # started at -5; reaches 0 after 5 sustained cycles
            st.steer_status = 4                # gentle EME: openpilot sees NO_TORQUE_ALERT_2 on CAN 399
            st.deb_counter = min(st.deb_counter, cal.deb_hold_seed)
            # ---- IN-CODE INTERLOCK (the V36 regression, the V37 fix's reason to exist) ----
            # Every STEER_STATUS=4 branch also zeroes the DTC-0x49 counter. In stock this is the ONLY
            # thing that keeps the DTC counter from saturating on a hard loaded curve.
            st.dtc49_counter = 0
    else:
        st.deb_counter = -cal.deb_count_seed   # reset the debounce
        if st.steer_status == 4:
            st.steer_status = 0


def dtc49_fault_counter(arb_torque_byte: int, st: EpsState, cal: Calibration) -> None:
    """
    The SECOND counter on the same torque channel: the DTC-0x49 fail counter (dash-lights path).
    [VERIFIED] Inlined in m_steer_torque_arbitration (gate reads @0x2920a/0x2921c, fire @0x291b8 ->
    jarl FUN_00016de6(0x49) + STEER_STATUS=7); counter gp-0x6758 increments while torque >
    dtc49_torque_gate(112), saturating at dtc49_saturation(100 = 50+50 cyc, ~1s @ ~100Hz); interlocked
    to zero by every STEER_STATUS=4 branch (see steer_status_debounce_sm). V36 raised the debounce
    thresholds so STEER_STATUS=4 never fired, so the interlock never ran and this counter free-ran to
    DTC 0x49 + STEER_STATUS=7 (dash lights, openpilot drops LKAS) -- V37's fix raises
    dtc49_torque_gate 112->255 so the counter can never increment.
    """
    if arb_torque_byte > cal.dtc49_torque_gate:
        st.dtc49_counter += 1
        if st.dtc49_counter >= cal.dtc49_saturation:
            st.dtc_0x49_set = True     # FUN_00016de6(0x49) -- confirmed DTC, dash MIL
            st.steer_status = 7        # openpilot treats 7 as steerFaultPermanent -> LKAS drops
    else:
        # NOTE: no decrement here -- stock relies on the STEER_STATUS=4 interlock to reset it.
        pass


def steer_torque_arbitration(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    Limit the LKAS setpoint, apply the Q15 gain/clamp, and run the two inlined SMs (driver assist is
    NOT merged here -- it joins downstream, Section 6). [VERIFIED] FUN_00028ea6 /
    m_steer_torque_arbitration, called from w_steer_control_task @0x22522, state-gated (andi 0x930,
    states {4,5,8,11}); limits setpoint gp-0x69ae via mode/gear LERP curves (0xC9A88..0xCBC34 ->
    0xE4xxx); applies gain tp+0x746c(0xC646C)=891 and clamp tp+0x71b4(0xC61B4)=512 as (term * gain) >>
    15 (Q15, not Q10 -- a real >>10 nearby belongs to an unrelated IIR blend); a high-torque branch
    @0x29a78 swaps in a cutoff above the same 112 gate V37 raises; writes gp-0x6b3c multiplicatively
    gated by mode gp-0x67a4 in {2,3}; feeds gp-0x682f to both inlined counters. No driver-assist term
    is added here (disasm-confirmed): the two adds feeding the store are both internal
    setpoint-descended terms.
    """
    # 1) mode/gear LERP limit on the LKAS setpoint. [VERIFIED @0x28fc8-0x29044] index=gp-0x674e into
    #    pointer array 0xCB844 -> curve @0xE4180; mode-0 value row is CONSTANT 15360, so the full-scale
    #    setpoint (0x4000=16384) IS clipped ~6% at the top end. (Only mode 0 byte-dumped; other modes
    #    open.) Modelled as the flat mode-0 limit.
    limited = _clamp(st.lkas_setpoint, -cal.arb_setpoint_limit, cal.arb_setpoint_limit)

    # 2) apply the LKAS output gain in Q15 (>>15), then a symmetric +/-arb_output_clamp. [VERIFIED] At
    #    full scale V850 `sar` yields +417/-418, both below 512, so stock never hits the clamp (an
    #    earlier >>10 reading was ~13370, 26x over the clamp, and was wrong).
    lkas_term = (limited * cal.lkas_output_gain) >> 15
    lkas_term = _clamp(lkas_term, -cal.arb_output_clamp, cal.arb_output_clamp)

    # 3) the arb command is a STANDALONE LKAS-descended signal -- NO driver-assist add here [VERIFIED,
    #    REFUTED the old `+ assist`]. Assist merges as a separate mixer source downstream (Section 6).
    arb_signal = lkas_term

    # 4) the internal torque channel the two inlined SMs watch: gp-0x682f = min(|arb signal|>>5, 255)
    arb_torque_byte = min(abs(arb_signal) >> 5, 255)

    # 5) high-torque arbitration branch (@0x29a78): a cutoff above the same 112 gate V37 raises
    if arb_torque_byte > cal.dtc49_torque_gate:
        arb_signal = arb_signal            # (V9/V31: high-torque CUTOFF taken here; V37: full interp)

    # 6) run BOTH inlined state machines on this tick's torque byte (order as in the firmware)
    steer_status_debounce_sm(arb_torque_byte, st.col_rate_mag, st, cal)  # gentle EME
    dtc49_fault_counter(arb_torque_byte, st, cal)                        # DTC-0x49

    st.arb_command = arb_signal            # -> gp-0x6b3c (0xFEDF14C4)
    return st.arb_command


# =====================================================================================================
# SECTION 6 -- LIMIT/PACK -> DISTRIBUTE/CLAMP -> MIXER -> GATE  (the fixed-clamp cascade)
# =====================================================================================================

def limit_distribute_mixer_gate(st: EpsState, cal: Calibration) -> int:
    """
    Carry the arbitration command through the per-lane clamp cascade to the LKAS lane output.
    [VERIFIED] limit_and_pack FUN_0002b422 (clamp +/-tp+0x71b2/0xC61B2) -> distribute FUN_00025c32
    (per-lane clamps +/-0x4000/0x2800/0x384/0x4E20, LKAS rides +/-0x2800) -> mixer FUN_00026c80
    (cross-lane sum into gp-0x3d70..3d98, LKAS final clamp +/-0x2800 -> gp-0x6b4c) -> gate
    FUN_00042ac6 (|x|<=0x2800 ? x : 0x7FFF sentinel -> gp-0x6afe). This whole stage stays
    LKAS-internal: the mixer sums ~11 LKAS-internal distribute sources (LKAS itself is source index 1)
    into gp-0x6b4c; base driver-assist joins ONE STAGE LATER, at the demand aggregator FUN_0003aa2c
    (Section 6B), where gp-0x6b4c is summed with gp-0x6bbe and ~8 sibling lanes into gp-0x6b94. The
    gate's 0x7FFF sentinel is deliberately out-of-range so the shaper's own range-check later
    collapses it to 0.
    """
    packed = _clamp(st.arb_command, -cal.pack_output_clamp, cal.pack_output_clamp)   # limit_and_pack (LKAS=idx 1)
    # distribute + mixer: the LKAS lane accumulates its ~11 LKAS-INTERNAL channels only (NO base
    # assist here), then the lane is clamped to +/-0x2800 before the gate.
    lkas_lane = _clamp(packed, -cal.distribute_lkas_lane_clamp, cal.distribute_lkas_lane_clamp)
    # gate: pass within the window, else emit the 0x7FFF sentinel
    if abs(lkas_lane) <= cal.mixer_gate_clamp:
        st.mixed_command = lkas_lane
    else:
        st.mixed_command = 0x7FFF            # sentinel -> shaper will zero it
    return st.mixed_command                  # -> gp-0x6b4c, the LKAS lane into the aggregator


# -----------------------------------------------------------------------------------------------------
# SECTION 6B -- MOTOR TORQUE DEMAND AGGREGATOR  (where LKAS and BASE ASSIST finally meet)
# -----------------------------------------------------------------------------------------------------

def motor_torque_demand_aggregator(st: EpsState, lanes: dict, cal: Calibration) -> int:
    """
    Sum every torque-demand lane -- LKAS and base assist alike -- into the single shared command.
    [VERIFIED] FUN_0003aa2c (0x3aa2c-0x3ad70) reads gp-0x6b62 (return-centre), gp-0x6b4c (LKAS,
    +/-0x2800), gp-0x6ade (dead, 0 writers image-wide), gp-0x6ad4 (resonance), gp-0x6b26 (friction),
    gp-0x6bbe (boost assist), gp-0x6bd0 (damping), gp-0x6b86 (magnitude), inline r26/r24 (torque-rate),
    and FUN_00036682's filtered term. Eight of these are ZERO-type range gates (out-of-window
    contributes 0, not clipped): 6b62 +/-0x2000, 6b4c +/-0x2800, 6ade +/-0x400, 6b86 +/-0x3000, 6bbe
    +/-0x800, 6bd0 +/-0x800, 6b26 +/-0x400, 6ad4 +/-0x2800 (@0x3aa38-0x3acc4). r24/r26 are instead
    SATURATING CLIPS to +/-0x2000 (`cmovle`, @0x3ab82-94/@0x3ac42-54), summed ungated -- the lowest
    discontinuity risk of the group, consistent with V39's r24 suppression not moving the on-car
    vibration. Add order @0x3acc8-0x3ace6: r26+r24 -> +6b86 -> +6bd0 -> +6bbe -> +6b26 -> +[6b62/6ade]
    -> +6ad4 -> +filtered (FUN_00036682). The output clamp @0x3acf0-0x3ad2a is a true SATURATING clamp
    (not a zeroing gate) to +/-0x2800, lockstep-checked at gp-0x4ce0 on all three paths (mismatch, not
    saturation, trips FUN_0006b9fa) -- so the aggregator output is not itself a chatter source. A
    REDUCED mode exists (gp-0x67ac==1 selects LKAS+s62 only, skipping 6 sibling lanes + r24/r26 + the
    filtered term) but is UNREACHABLE on the A160: its selector traces to distribute's per-source TYPE
    array gp-0x61a0 (mirrors cal tp+0x5124/0xC4124), which on this ROM is (0,0,5,0,5,5,0,0,0,5,0) and
    never matches the qualifying literals {2,3,4} -- so gp-0x67ac is always 0 and the FULL path always
    runs; keep the 0xC4124 guard in every build regardless. Scheduled from w_steer_control_task
    @0x2291e, state-gated (andi 0xc30, states {4,5,10,11}). Writes sum -> clamp -> gp-0x6b94,
    lockstep-shadowed at gp-0x4ce0 -- the same variable the governor chain consumes. LOAD-BEARING
    CONSEQUENCE: every base-assist lane joins LKAS here, before the first governor/compensation/shaper
    stage, so a soft-EME event can feel like broad power-assist loss, not just LKAS easing.
    """
    s62 = _range_gate(lanes["return_centre_6b62"], 0x2000)
    lkas = _range_gate(st.mixed_command, 0x2800)
    dead = 0                                             # gp-0x6ade: no writers image-wide

    st.direct_rate_guard_fired = False
    if st.aggregator_reduced_mode:
        total = lkas + dead + s62
    else:
        inline_a = _clamp(lanes["inline_a"], -0x2000, 0x2000)
        inline_b = _clamp(lanes["inline_b"], -0x2000, 0x2000)

        # V39 experimental patch: suppress the verified direct derivative lane for both signs. The
        # strong-driver check fails open on the 0xFFFF invalid-voter sentinel. r26 and every downstream
        # governor/shaper/protection path remain live; this is a narrow high-frequency-ripple experiment.
        # Firmware hook: 0x3ac78 -> cave 0xc4b34..0xc4b5f -> return 0x3ac7c.
        if (cal.suppress_direct_torque_rate_assist
                and st.col_torque_max < cal.dec_torque_max
                and abs(lkas) >= cal.direct_rate_lkas_threshold):
            st.direct_rate_guard_fired = inline_b != 0
            inline_b = 0
        st.assist_inline_b = inline_b

        magnitude = _range_gate(lanes["magnitude_6b86"], 0x3000)
        damping = _range_gate(lanes["damping_6bd0"], 0x0800)
        boost = _range_gate(st.assist_lane, 0x0800)
        friction = _range_gate(lanes["friction_6b26"], 0x0400)
        # The 0xC6AF0 LERP scales the lane's own output ceiling BEFORE the aggregator's range gate.
        # Modelled as a Q15 scale on the lane value, which is equivalent for the mute case that
        # matters (bound 0 -> lane 0) and for the unity case that is live on every build to date.
        resonance = (lanes["resonance_6ad4"] * cal.resonance_lane_output_bound_q15) >> 15
        resonance = _range_gate(resonance, 0x2800)
        filtered = lanes["filtered_36682"]

        # Exact instruction order at 0x3acc8..0x3ace6.
        total = inline_a
        total += inline_b
        total += magnitude
        total += damping
        total += boost
        total += friction
        total += s62
        total += resonance
        total += lkas
        total += dead
        total += filtered

    st.non_lkas_sum = total - lkas
    st.demand_sum = _clamp(total, -cal.distribute_lkas_lane_clamp, cal.distribute_lkas_lane_clamp)
    return st.demand_sum                     # -> gp-0x6b94, then governor -> shaper -> gp-0x6b98


# -----------------------------------------------------------------------------------------------------
# SECTION 6C -- MOTOR-RATE ADAPTIVE GOVERNOR  (gp-0x6b94 -> gp-0x6ace -> gp-0x6acc)
# -----------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------
# MOTOR-RATE ADAPTIVE CAP -- exact byte layout. [VERIFIED against _v38_plain_image.bin]
# Bank A (the tp-addressable one the app reads): header+X+Y at tp+0x620C/0xC520C (22 bytes: u16
# count=5, X[5], Y[5]), Q13 slopes at tp+0x6030/0xC5030 (8 bytes), shift tp+0x6160/0xC5160=13; a
# byte-identical second copy at 0xC5224/0xC5038. Two further byte-identical banks exist (B @0xF9E0C/
# 0xF9C30, C @0xFAA0C/0xFA830) but are NOT reachable from app tp -- role [OPEN].
# The two bank-A copies are a PURE DUPLICATE STORE, not independent recomputations (FUN_0007b022
# stores one locally-computed register to both copies back-to-back, same opcode halfword) -- hard-
# fault index 0x17 can only fire on cross-cycle RAM divergence, never from a calibration edit to
# either copy. Bank A sits inside the CRC chain's one gap [0xC5000,0xC6000), so it needs NO CRC
# recompute; banks B/C are inside the untouched [0xF9000,0xFCFFC) block. No float mirror exists for
# any of these values.
# ---------------------------------------------------------------------------------------------------
GOVERNOR_RATE_X = (1050, 1700, 2500, 3700, 4100)
GOVERNOR_RATE_Y = (5325, 3584, 2406, 1587, 512)
GOVERNOR_RATE_SLOPE_Q13 = (-21940, -12059, -5593, -22021)
GOVERNOR_RATE_SHIFT = 13                     # tp+0x6160 (0xC5160)


def a160_governor_rate_cap(axis_z: int, ys=None, slopes=None) -> int:
    """Exact fixed-point A160 adaptive-cap table used by FUN_0007b022.

    `ys`/`slopes` default to the stock table. Pass a build's own rows to model a flattened cap --
    note the firmware evaluates Y[i] + ((z - X[i]) * slope >> 13), so a flat Y with non-zero slopes
    would STILL interpolate. V40 therefore zeroes both.
    """
    ys = GOVERNOR_RATE_Y if ys is None else tuple(ys)
    slopes = GOVERNOR_RATE_SLOPE_Q13 if slopes is None else tuple(slopes)
    z = int(axis_z)
    if z <= GOVERNOR_RATE_X[0]:
        return ys[0]
    if z <= GOVERNOR_RATE_X[1]:
        i = 0
    elif z <= GOVERNOR_RATE_X[2]:
        i = 1
    elif z <= GOVERNOR_RATE_X[3]:
        i = 2
    elif z < GOVERNOR_RATE_X[4]:
        i = 3
    else:
        return ys[-1]
    value = ys[i] + (((z - GOVERNOR_RATE_X[i]) * slopes[i]) >> GOVERNOR_RATE_SHIFT)
    return _clamp(value, -32767, 32767)


def rate_cap_binding_analysis(cal: Calibration, assist_counts: int = 0) -> dict:
    """
    Does the motor-RATE adaptive cap bind on the LKAS path for this build, and from what rate?
    [VERIFIED] The cap's axis is motor resolver electrical-angle rate (not road speed), falling
    5325->512 over z = 1050-4100 with a 512 floor. Stock V9's max LKAS demand (417) sits below that
    floor and can never be capped; V31 (835) binds from z~3980, V38 (1782) binds from z~3414 (with
    base assist in the aggregate, z~2229). Because the aggregate is capped before the motor responds,
    raised-reach builds close a relaxation-oscillator loop (torque applied -> motor accelerates -> z
    rises -> cap falls -> torque cut -> motor decelerates -> z falls -> cap rises -> torque restored
    -> repeat), whose signature (moving-only, worst on fast steering motion, road-speed-independent,
    absent when the driver supplies the torque) matched the on-car ratchet report -- V38 is the first
    build whose LKAS-path demand clears the 512 floor by a wide margin, explaining why no prior build
    showed it. [INFERRED] that the loop actually oscillates on-car at the observed frequency (needs
    plant inertia this model lacks). CALIBRATION WARNING: this cap is a genuine motor thermal/
    mechanical protection, rate-scheduled (not thermal-triggered) -- any change must be a measured
    raise of the taper's low end, never a wholesale flattening, and must be scored against motor
    thermal behaviour.
    """
    lkas_max = min((cal.arb_setpoint_limit * cal.lkas_output_gain) >> 15, cal.arb_output_clamp)
    demand = lkas_max + int(assist_counts)
    binds_from = next(
        (z for z in range(0, 9000)
         if a160_governor_rate_cap(z, cal.rate_cap_y, cal.rate_cap_slope_q13) < demand),
        None,
    )
    return {
        "build": cal.build,
        "lkas_max_counts": lkas_max,
        "demand_counts": demand,
        "cap_floor": cal.rate_cap_y[-1],
        "binds_from_motor_rate": binds_from,       # None => this build can never be rate-capped
        "can_be_rate_capped": binds_from is not None,
    }


def slew_ramp_time_analysis(cal: Calibration, assist_counts: int = 1024) -> dict:
    """
    How many governor cycles does each build need to ramp from zero to its own full demand?
    [VERIFIED] The governor's away-from-zero slew step is an ABSOLUTE count (cal 0xC6206=512 fast /
    0xC6208=205 slow), and the SLOW step is selected during a hard dynamic turn (gp-0x67f5 forced via
    the gp-0x67f4/gp-0x67f5 selector logic whenever raw driver torque diverges from the vote by >=65
    counts, or voted |torque|>=640). V38 raised the LKAS target ~4x while leaving both step cals at
    stock, so ramp time (target/step) got ~4x longer while the sign-crossing reset (zeroing the held
    value outright) stayed instantaneous -- slow build + instant collapse = a ratchet; the invariant
    V38 broke is RAMP TIME (cycles to full command), not step size. This was the leading ratchet
    hypothesis and was later CONFIRMED as a real contributor, though the state-4 governor substitution
    (V42 Change 1) is the root-cause fix that actually resolved it on-car. [OPEN] the wall-clock
    conversion (task rate contested); cycle counts here are exact, milliseconds are deliberately not
    computed.
    """
    lkas_max = min((cal.arb_setpoint_limit * cal.lkas_output_gain) >> 15, cal.arb_output_clamp)
    target = min(lkas_max + int(assist_counts), cal.distribute_lkas_lane_clamp)
    fast = cal.governor_slew_step_normal
    slow = cal.governor_slew_step_alt
    return {
        "build": cal.build,
        "target_counts": target,
        "fast_step": fast,
        "slow_step": slow,
        "cycles_at_fast_step": -(-target // fast),   # ceil
        "cycles_at_slow_step": -(-target // slow),   # the hard-turn case
    }


def gain_rescaling_invariance_analysis(cal: Calibration, op_pid_scale: float = 0.25) -> dict:
    """
    Central units argument: V38 raised the arbitration gain 0xC646C 891->3564 (4x) while the operator
    correspondingly quartered openpilot's lateral PID, restoring stock's closed-loop gain. Following
    units through setpoint=C*-4 -> lane=(setpoint*gain)>>15 -> everything downstream (calibrated in
    absolute lane counts): for the SAME physical torque, every stage DOWNSTREAM of the gain sees the
    identical stock count sequence (so no downstream absolute-count limit can bind differently than
    stock), while every stage UPSTREAM of the gain sees counts 4x closer to zero -- EXCEPT torque above
    stock's 417-count ceiling, which enters a regime that never existed before and makes downstream
    limits newly reachable. This partitions the RATCHET (large commanded torque, genuinely
    downstream-novel; the governor slew survives as a candidate, later confirmed root cause via V42;
    the motor-rate cap was falsified by V41) from the VIBRATION. [CORRECTED 2026-07-21] the vibration
    was originally assumed near-zero/upstream, but the operator reports it occurs during LARGE
    pure-LKAS commands (near V38's ceiling) and vanishes when the driver shares torque -- so it in fact
    lives in the SAME downstream-novel regime as the ratchet, not a near-zero upstream deadband; the
    earlier upstream eliminations are downgraded to UNTESTED, not re-opened as leading candidates. V39
    (r24 suppression) and V41 (motor-rate cap) are both downstream levers and both were flashed with no
    effect on the vibration regardless. [VERIFIED] the gain/setpoint arithmetic and stage ordering;
    [CONFIRMED] the PID rescale and engaged-only vibration character; [INFERRED] the partition itself,
    a units argument assuming the gain is the only V38 change relevant near zero (the source clamps,
    corridor/boost walls, and setpoint limit also moved, but none binds near zero).
    """
    stock = Calibration.for_build("V9")
    stock_max_lane = min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15, stock.arb_output_clamp)
    build_max_lane = min((cal.arb_setpoint_limit * cal.lkas_output_gain) >> 15, cal.arb_output_clamp)
    return {
        "build": cal.build,
        "gain_ratio_vs_stock": cal.lkas_output_gain / stock.lkas_output_gain,
        "op_pid_scale_applied": op_pid_scale,
        "loop_gain_vs_stock": (cal.lkas_output_gain / stock.lkas_output_gain) * op_pid_scale,
        "stock_max_lane_counts": stock_max_lane,
        "build_max_lane_counts": build_max_lane,
        # Below this lane count the downstream chain is replaying stock's own count sequence.
        "downstream_novel_above_lane_counts": stock_max_lane,
        "setpoint_shrink_factor_upstream": op_pid_scale,
        # Corrected 2026-07-21: the vibration occurs during pure-LKAS TURNING (a LARGE command), so it
        # sits in the same >stock-ceiling downstream regime as the ratchet, not upstream of the gain.
        "vibration_stage": "DOWNSTREAM of gain, above %d lane counts (same novel regime as the ratchet)"
                           % stock_max_lane,
        "ratchet_stage": "DOWNSTREAM of gain, and only above %d lane counts -- SOLVED by V42 Change 1"
                         % stock_max_lane,
        "downstream_candidates_falsified_on_car": [
            "r24 direct derivative lane (V39)",
            "r26 adaptive derivative lane (V42) -- with r24, the WHOLE Sensor-B rate family is out",
            "motor-rate adaptive cap (V41)",
        ],
        "confirmed_root_causes": ["state-4 governor substitution ratchet (V42 Change 1, fixed on-car)"],
    }


def governor_step_selector_bandwidth(cal: Calibration, tick_hz: float = 1000.0,
                                     command_counts: int = 4342) -> dict:
    """
    The governor's per-cycle slew STEP is selected by gp-0x67f5 (written only by FUN_00041eec, the
    column-torque voter): sustained driver column torque >= cal 0xC531E (1062) for cal 0xC64E7 (10)
    cycles selects the SLOW step (205, more damped); below that, or on reset, selects FAST (512, less
    damped) -- so hands-off runs ~2.5x wider bandwidth than hands-on, matching the operator's
    hands-off/hands-on discriminator direction. [VERIFIED] the selector, cals, debounce, and step
    ratio. A per-cycle slew limit is a bandwidth gate (ripple amplitude passed at frequency f is
    A_max = STEP*tick/(2*pi*f)), so this is a genuine TRANSMISSION PATH for tens-of-Hz content -- but
    [INFERRED, not established] that anything actually oscillates in that band upstream (the
    voting-loop channels feeding the slew target are OPEN). V45 (narrowing the hands-off step, cal
    0xC6206 512->205) was FLASHED and had NO EFFECT on the vibration, so this bandwidth-narrowing lever
    is now falsified as a fix, though the mechanism description stands. [OPEN] every Hz figure here
    scales with the unconfirmed 1 kHz tick assumption; cycle counts and the 2.5x ratio are
    tick-independent.
    """
    import math
    fast, slow = cal.governor_slew_step_normal, cal.governor_slew_step_alt

    def corner_hz(step, amplitude):
        return step * tick_hz / (2.0 * math.pi * amplitude)

    def max_ripple(step, f):
        return step * tick_hz / (2.0 * math.pi * f)

    return {
        "build": cal.build,
        "selector_var": "gp-0x67f5 (written only by FUN_00041eec, the column-torque voter producer)",
        "selector_threshold_cal": {"addr": "0xC531E", "value": 1062, "domain": "driver column torque"},
        "selector_debounce_cal": {"addr": "0xC64E7", "cycles": 10},
        "step_hands_off_fast": fast,
        "step_hands_on_slow": slow,
        "step_ratio": round(fast / slow, 3),
        "cycles_to_full_command": {
            "hands_off": -(-command_counts // fast),
            "hands_on": -(-command_counts // slow),
        },
        "corner_hz_at_full_command": {
            "hands_off": round(corner_hz(fast, command_counts), 1),
            "hands_on": round(corner_hz(slow, command_counts), 1),
        },
        # The decisive number: ripple amplitude transmitted at the symptom frequency.
        "max_ripple_counts_at_30hz": {
            "hands_off": round(max_ripple(fast, 30.0)),
            "hands_on": round(max_ripple(slow, 30.0)),
        },
        "tick_hz_assumed": tick_hz,
        "status": "[VERIFIED] transmission path gated by driver torque; [INFERRED] as the cause",
    }


def dirty_derivative_pole_analysis(gain: int = 64, tick_hz: float = 1000.0) -> dict:
    """
    Models the V43 edit: cal 0xC644A (tp+0x744a) 1024->64, restoring the disabled EMA pole immediately
    downstream of FUN_0003a382's raw one-sample difference (the "dirty derivative" on state gp-0x3680,
    distinct from the flat/passthrough proportional branch at 0xC6450). [VERIFIED] state_new =
    state_prev + (((target*32) - state_prev)*GAIN)>>10 has unity DC gain in real arithmetic; V850
    `sar` floors toward -infinity, so the integer fixed point is a bounded, ONE-SIDED residual of
    ~32/GAIN counts (sub-count at GAIN>=64; degenerate and must never be used at GAIN=0). No shadow/
    lockstep exists on this cal (pure-leaf function, zero jarl, no -0x4c displacement) and no float
    mirror exists (FUN_0003a382 has zero floating-point instructions); the nearby weight-32
    hard-shutdown monitor's input gp-0x6dac was traced to an independent sensor-plausibility watchdog
    (FUN_00027b0a) with no dependency on this lane, so it cannot be tripped by this edit. V43 (this
    exact cal) was FLASHED 2026-07-21 and fixed neither symptom -- the mechanism is confirmed SAFE but
    the dirty-derivative pole is FALSIFIED as the vibration's cause.
    """
    import math
    alpha = gain / 1024.0
    tau_exact = -1.0 / math.log(1.0 - alpha) if 0 < alpha < 1 else float("inf")
    fc_cycles = alpha / (2.0 * math.pi)
    deadband_state = (1024 // gain) - 1 if gain else None
    return {
        "cal": "0xC644A (tp+0x744a)",
        "stock_value": 1024,
        "proposed_value": gain,
        "alpha": round(alpha, 5),
        "tau_cycles_exact": round(tau_exact, 2),
        "corner_cycles_inverse": round(fc_cycles, 5),
        "corner_hz_if_tick_1khz": round(fc_cycles * tick_hz, 2),
        "truncation_deadband_state_counts": deadband_state,
        "truncation_deadband_target_counts": round(deadband_state / 32.0, 3),
        "dc_gain_preserved": True,
        "shadow_or_lockstep": "none in FUN_0003a382 (no -0x4c displacement; pure leaf, zero jarl)",
        "degenerate_value_never_use": 0,
    }


def vibration_hands_off_analysis(cal: Calibration) -> dict:
    """
    Computes the vibration-investigation headroom/discriminator dict as of the V42-V47 era: the LKAS
    lane is a ~1-5 Hz low-pass (gp-0x3d3c IIR) so a tens-of-Hz mode cannot be COMMANDED through it
    (constraint C1); downstream of the gain V38 replays stock's exact count sequence except above
    stock's 417-count ceiling, which pure-LKAS turning reaches (C2, see
    gain_rescaling_invariance_analysis()); and something must differ hands-off vs hands-on (C3) -- the
    soft-EME corridor arm gates off at |gp-0x6bf0|<=cal 0xC6156 (9216). [CONFIRMED, on-car, route b9]
    the mode is a lightly-damped mechanical resonance, 21.4 Hz, Q=13.6 (not a digital limit cycle: Q
    this low and ~0.23s coherence rule that out), a measured V38 regression (64x in the 20-30 Hz band
    vs pre-V38 routes, 75-314x hands-off vs assisting at matched speed), present at every speed but
    ~10x stronger at low speed. [VERIFIED] the mechanism chain gp-0x4f60 (raw Sensor-B torque) ->
    FUN_0003a382's model-vs-reality residual (a genuine PID, not cascaded lags -- see
    assist_shaping_lanes()) -> gp-0x6ad4 -> the aggregator -> gp-0x6b94, which IS the governor's slew
    target, whose STEP is driver-torque-gated (see governor_step_selector_bandwidth()) -- this
    survives the gain-rescaling invariance argument because it is sourced from a PHYSICAL sensor
    reacting to REAL delivered torque (which scales 4x with V38), not a digital replay. ROOT CAUSE
    [CONFIRMED, V44 restored damping]: the base-assist DAMPING lane FUN_00034350->gp-0x6bd0 is
    multiplied by a Q10 factor that is exactly ZERO below 2240 counts of driver torque (hands-off), and
    the firmware has no notch filter anywhere, so the resonance rings undamped hands-off and is damped
    hands-on -- V44 raises that floor; V47 additionally raises a second independent hands-off deadzone
    (motor-rate Factor E). Eliminated as causes, on-car: r24 (V39), r26 (V42), the dirty-derivative
    pole (V43), the governor slew-step selector (V45), and the FUN_0003a382 Stage A carrier filter
    (V46). Eliminated analytically: the soft-EME wall/boost-latch oscillator (cannot bootstrap under
    LKAS-alone) and the governor's thermal/energy budget term (structurally unreachable). NOTE this
    thread continued past V47 -- see the module docstring's build lineage for V55/V56/V57, which
    established the mode is genuinely commanded and that muting FUN_0003a382 entirely (V56) did not
    remove it.
    """
    stock = Calibration.for_build("V9")
    v31 = Calibration.for_build("V31")

    def max_cmd(c):
        lane = min((c.arb_setpoint_limit * c.lkas_output_gain) >> 15, c.arb_output_clamp)
        return lane + 2560   # + the post-governor compensation ceiling

    return {
        "build": cal.build,
        "constraints": {
            "C1_fast": "tens of Hz; LKAS lane is a ~1-5 Hz low-pass, so NOT commandable via LKAS",
            "C2_v38_onset": "only loophole is command above stock's %d-count ceiling"
                            % min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15,
                                  stock.arb_output_clamp),
            "C3_hands_off": "corridor arm gated off when |gp-0x6bf0| <= 9216 (cal 0xC6156)",
        },
        "governor_headroom_counts": {
            "V31": v31.runtime_governor - max_cmd(v31),
            cal.build: cal.runtime_governor - max_cmd(cal),
        },
        "surviving_structures": {
            "a_marginal_downstream_limit": "a limit V38 sits against, chattered by a dynamic MIN term",
            "b_mechanical_resonance": "hands-off torsion-bar/wheel-inertia mode, excited 4x harder",
        },
        "falsified_on_car": [
            "r24 (V39)", "motor-rate cap (V41)", "r26 (V42)", "dirty-derivative pole (V43)",
            "governor slew-STEP selector gp-0x67f5 (V45, cal 0xC6206 512->205 -- narrowed bandwidth, "
            "flashed 2026-07-21, no effect)",
            "FUN_0003a382 Stage A reinforcing-carrier filter (V46, cal 0xC6450 1024->32 -- "
            "'lever A', flashed 2026-07-21, no effect)",
        ],
        "falsified_analytically": [
            "soft-EME wall / boost-latch relaxation oscillator -- wall 5120 vs command 4342-4608, "
            "cannot bootstrap under LKAS-alone (2026-07-21)",
            "governor energy/thermal budget -- threshold 5325 > structural max delivered 4762, "
            "provably unreachable (2026-07-21); RELABELED motor-rate-adaptive total-command ceiling, "
            "does not bind at the resonance's own ~139-count amplitude",
        ],
        "leading_candidate": {
            "name": "base-assist DAMPING lane FUN_00034350 -> gp-0x6bd0, BOTH hands-off deadzones "
                     "(Factor C driver-torque LERP Y[0], Factor E motor-rate LERP Y[0])",
            "edit": "V44 opened only Factor C (0xD27C6/0xD27DA 0->235/234); V47 additionally raises "
                    "Factor E's low breakpoints (0xD2802/04/06 mode 10, 0xD2816/18/1A mode 11 -> "
                    "700/750/800) so the damper is live at low motor rate too, not just high driver "
                    "torque -- see assist_shaping_lanes()'s FUN_00034350 factor breakdown",
            "status": "[VERIFIED] both deadzones + table contents; [INFERRED] as sufficient cause; "
                      "V47 BUILT + verified, UNFLASHED (current candidate, 2026-07-21)",
            "see": "assist_shaping_lanes()",
        },
        "elimination_downgraded": "motor torque ripple -- the damping confound, see docstring",
    }


def arb_deadband_relative_width(cal: Calibration, op_pid_scale: float = 0.25,
                                deadband_ivar34: int = 102) -> dict:
    """
    Models the PRE-GAIN deadband + sign-consistency gate inside arbitration (FUN_00028ea6,
    0x2a1ae-0x2a206, before the polarity*gain multiply): if cal 0xC64A3==1 (sole reader) AND
    gp-0x6806==0, values with |iVar34|<=cal 0xC61B8 (=102, MIXED ld.h/ld.hu read -- keep any edit in
    0..32767) are forced to 0, and a sign-mismatch vs the previous cycle (gp-0x6b30, 2 refs
    image-wide) also forces 0; the result is then scaled by ramp-gain gp-0x69b0 (a separate 0..0x8000
    fade-in SM, NOT a torque-error integrator -- distinct from the gp-0x3d3c IIR filter, resolving a
    long-standing two-variable confusion). [VERIFIED] L=102 is a FIXED absolute threshold in the
    pre-gain domain; with the PID quartered to compensate the 4x gain, the same physical torque sits
    4x closer to zero, so the deadband occupies ~4x more of the working range -- the invariance
    argument's own predicted mechanism. The apparent self-latch (once iVar34 stores 0, does the next
    test also force 0?) is RESOLVED: the gate is enabled only during the LKAS engage ramp
    (gp-0x6806==0), and steady engaged driving holds gp-0x6806==1, making the gate INERT in steady
    state. STEER_STATUS 4 and 7 are separately proven unreachable on V37/V38, leaving ST=3 (the
    low-speed lockout, releasing at ~3 mph, CONFIRMED sustained not chattering across 98k frames) as
    the only surviving trigger -- so this candidate is either DEAD (if the felt vibration is sustained
    at a steady speed, gate inert) or ALIVE (if it is transient just after pulling away, when the
    ~993-cycle ramp-up holds the gate open through the 4-6 mph window). [OPEN] which of the two the
    operator's report actually is -- the single question that decides this candidate. Separately,
    gp-0x6752 (assist polarity) is confirmed a static per-variant boot constant, refuting a
    "chattering sign multiplier" hypothesis.
    """
    stock = Calibration.for_build("V9")
    # Illustrative only: assumes iVar34 scales linearly with the setpoint, which is plausible for a
    # LERP-blend + linear IIR but is NOT verified. Do not quote as a firmware fact.
    stock_span = stock.arb_setpoint_limit
    build_span = cal.arb_setpoint_limit * op_pid_scale
    return {
        "build": cal.build,
        "deadband_ivar34_counts": deadband_ivar34,
        "enable_cal": "0xC64A3 = 1 (sole reader image-wide)",
        "threshold_cal": "0xC61B8 = 102 (MIXED ld.h / ld.hu -- keep any edit in 0..32767)",
        "stock_effective_setpoint_span": stock_span,
        "build_effective_setpoint_span": build_span,
        "relative_deadband_widening": round(stock_span / build_span, 2),
        "predicted_by": "gain_rescaling_invariance_analysis()",
        "blocking_question": "(A) inert / (B) pure deadband / (C) relaxation oscillator",
    }


def lkas_iir_quantization_analysis(cal: Calibration, pole_q10: int = 992, deadband_lsb: int = None,
                                   ramp_gain_q15: int = 0x8000) -> dict:
    """
    Tests whether the one-pole IIR at gp-0x3d3c inside arbitration FUN_00028ea6 (@0x2a174-0x2a1b0:
    term1=floor(507*x/1024) cal 0xC63EE, term2=floor(992*s_prev/1024) cal 0xC63EC, s=term1+term2,
    iVar34=floor((s_prev+s)/32)) can produce a limit cycle or a perceptible dead-band/stick-slip
    artifact. [VERIFIED, HYPOTHESIS DEAD] structurally no limit cycle is possible (a monotone affine
    map with 0<pole<1 cannot overshoot or oscillate; simulation confirms the internal state can enter a
    period-2 orbit but the >>5 output stage is constant through it), and the dead-band/stick-slip
    variant is also dead by enumeration + simulation (the quantisation is ordinary input rounding, not
    a pathological recursive artifact, and even the most aggressive tested ramp yields <=2 motor
    counts on V38, ~0.05% of full scale). THE REAL FINDING kept from this trace: pole 0.96875 makes
    the ENTIRE LKAS command lane a ~1-5 Hz low-pass (tau=31.5 cycles, ~unity DC gain), so a
    tens-of-Hz component CANNOT be commanded through the LKAS lane at all -- everything upstream of
    this IIR (CAN intake, setpoint, LERP cascade, openpilot's own command dynamics) is band-limited
    before reaching the gain, which eliminates an entire half of the search space and weakens (but
    does not kill -- see openpilot_command_slew_invariance()'s closed-loop-instability argument, a
    different mechanism) the STEER_DELTA hypothesis for a fast symptom. What survives: a fast
    vibration must arise DOWNSTREAM of this IIR and still be LKAS-conditional -- the standout is the
    r26 adaptive Sensor-B torque-rate lane (a derivative, so it passes exactly the band this filter
    blocks, with no deadzone unlike r24).
    """
    stock = Calibration.for_build("V9")
    pole = pole_q10 / 1024.0
    band = deadband_lsb if deadband_lsb is not None else round(1.0 / (1.0 - pole))

    def at_motor(gain):
        return band * (ramp_gain_q15 / 0x8000) * gain / 32768.0

    # UNITS TRAP: measure against a FIXED PHYSICAL TORQUE, not each build's own full scale (V38's is
    # itself 4x stock's, so dividing by it would cancel the effect being measured). With the PID
    # quartered, the same physical torque is the same lane count in both builds, so the reference is
    # held at stock's own full-scale command (417 counts).
    reference_counts = min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15,
                           stock.arb_output_clamp)
    return {
        "build": cal.build,
        "pole": round(pole, 5),
        "time_constant_cycles": round(1.0 / (1.0 - pole), 1),
        "deadband_ivar34_lsb": band,
        "step_at_motor_stock": round(at_motor(stock.lkas_output_gain), 2),
        "step_at_motor_build": round(at_motor(cal.lkas_output_gain), 2),
        "regression_factor": round(cal.lkas_output_gain / stock.lkas_output_gain, 2),
        # Ripple-to-signal at the SAME physical torque -- the only comparison that means anything.
        "reference_physical_torque_counts": reference_counts,
        "ripple_pct_at_ref_stock": round(100 * at_motor(stock.lkas_output_gain) / reference_counts, 3),
        "ripple_pct_at_ref_build": round(100 * at_motor(cal.lkas_output_gain) / reference_counts, 3),
        "survives_only_if": "the step is large enough to feel; see the docstring's kill criterion",
    }


def openpilot_command_slew_invariance(cal: Calibration, steer_delta: float = 3.0,
                                      dt_ctrl: float = 0.01, steer_max: int = 4096) -> dict:
    """
    openpilot rate-limits the steering command in NORMALIZED units, upstream of both STEER_MAX and the
    firmware gain (STEER_DELTA_UP/DOWN=3, DT_CTRL=0.01, STEER_MAX=4096, identity lookup for the
    Accord). [VERIFIED against opendbc] Quartering the PID restored the loop GAIN but left the command
    SLEW RATE untouched: the slew ceiling in firmware lane counts is (0.03*STEER_MAX*4*gain)>>15, so it
    scales with the FIRMWARE gain -- stock 13.4 counts/10ms tick vs V38 53.5 (4x faster, uncompensated),
    cutting the time to full physical torque from ~170ms to ~42ms and crossing INSIDE openpilot's
    100ms steerActuatorDelay (stock's slow slew dominated and damped the loop; V38's fast slew lets
    the delay dominate instead -- a classic limit-cycle recipe). This is a comma-side scaling gap, not
    a firmware defect, and fits the on-car evidence (V38 onset, engaged-only, absent hands-on, worst
    at low speed, immune to firmware-only V39/V41). It couples to r26 (the adaptive Sensor-B derivative
    lane) as excitation-to-amplifier: faster slew -> bigger column-torque derivative -> bigger r26 ->
    more motor torque -> more column motion -> repeat. Motor ripple is ruled out (hand steering
    delivers comparable torque through the same smooth output stage), which leaves the LKAS-only
    segment upstream of the aggregator -- see lkas_iir_quantization_analysis() for the standout
    stateful element there (gp-0x3d3c). PROPOSED TEST, in order: comma-side STEER_DELTA_UP/DOWN
    3->0.75 first (reversible, no flash/brick risk) before building any firmware image; if the symptom
    only softens, the r26 cal kill attacks the amplifier. [CONFIRMED] the PID rescale and engaged-only
    character; [INFERRED] that this loosening causes the felt vibration (a control-theory prediction,
    not yet road-tested in isolation).
    """
    stock = Calibration.for_build("V9")
    per_tick_norm = steer_delta * dt_ctrl

    def lane_per_tick(gain):
        return per_tick_norm * steer_max * abs(stock.setpoint_scale) * gain / 32768.0

    stock_rate = lane_per_tick(stock.lkas_output_gain)
    build_rate = lane_per_tick(cal.lkas_output_gain)
    stock_max_lane = min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15, stock.arb_output_clamp)
    return {
        "build": cal.build,
        "normalized_step_per_tick": per_tick_norm,
        "stock_lane_counts_per_tick": round(stock_rate, 1),
        "build_lane_counts_per_tick": round(build_rate, 1),
        "slew_loosening_factor": round(build_rate / stock_rate, 2),
        "ms_to_stock_full_scale_stock": round(1000 * dt_ctrl * stock_max_lane / stock_rate),
        "ms_to_stock_full_scale_build": round(1000 * dt_ctrl * stock_max_lane / build_rate),
        "steer_actuator_delay_ms": 100,
        "rate_limiter_still_dominant": (1000 * dt_ctrl * stock_max_lane / build_rate) > 100,
        "compensating_steer_delta": round(steer_delta * stock.lkas_output_gain / cal.lkas_output_gain, 3),
    }


def governor_slew_0xffff_postmortem() -> dict:
    """
    Why V40 (V38 + slew cals 0xC6206/0xC6208 -> 0xFFFF) lost all power steering at ignition, while V41
    (V38 + only the cap flatten, slew untouched) boots and drives cleanly -- isolating the fault to the
    0xFFFF slew write. [VERIFIED, byte-level] Both refuted mechanisms (a signed-load -1, a signed-16
    overflow) are ruled out: the cals are `ld.hu` (unsigned, 0xFFFF=65535) and the product is provably
    bounded below 0x80000000, so no wraparound is possible. What 0xFFFF actually did: it made the slew
    guard never fire, snapping the command to target every cycle -- complete removal of rate limiting,
    not a sign error. [INFERRED] fault path: with zero filtering, at ignition the target is sensor
    noise around zero and the command chases it at full bandwidth, tripping the hard-fault-eligible,
    no-debounce monitors FUN_0004595a/FUN_00045a20 (same 0xd30 state gate as the governor) -> motor off
    + power-cycle. The defect is the MAGNITUDE of the edit, not its direction -- a moderate raise
    preserves protection. The principled value is RAMP-TIME PARITY: scale both step cals by the same
    4x V38 applied to reach (512->2048, 205->820), which V42 uses; this addresses the RATCHET only and,
    per gain_rescaling_invariance_analysis(), cannot touch the speed-independent vibration.
    """
    return {
        "v40_fault": "EPS lamp + total loss of assist at ignition",
        "attributed_to": "0xC6206/0xC6208 <- 0xFFFF",
        "exonerated_by_v41": ["motor-rate cap flatten", "stale 0xC5FFC CRC"],
        "refuted_mechanisms": ["signed load -> -1 (cals are ld.hu)",
                               "signed-16 overflow (guard is self-bounded; product < 0x80000000)"],
        "actual_effect_of_0xffff": "guard never fires -> snap-to-target -> zero rate limiting",
        "inferred_fault_path": "unfiltered command -> FUN_0004595a / FUN_00045a20 (same 0xd30 state "
                               "gate as the governor) -> FUN_00016de6(0x1d) -> hard-eligible, no "
                               "debounce -> motor off",
        "cal_readers_image_wide": {"0xC6206": 1, "0xC6208": 1},
        "arithmetically_safe_range": "0..65535 (no wrap possible); the limit is BEHAVIOURAL",
        "snap_to_target_threshold": "step approaching TARGET magnitude (~4762) collapses to 1 cycle",
        "ramp_time_parity_steps": {"0xC6206": 512 * 4, "0xC6208": 205 * 4},
        # A slew raise cannot touch the vibration: that symptom is speed-independent and sits
        # DOWNSTREAM of the LKAS-lane low-pass, which this cal is upstream of.
        "addresses_symptom": "hard-turn ratchet only",
        "caveat": "ratchet attribution now depends on the UNRESOLVED task rate -- see EXECUTION MODEL",
    }


def computed_runtime_governor(sensors: SensorInputs, cal: Calibration) -> int:
    """Model gp-0x4f64 without inventing the still-unresolved axis normalization or budget formula."""
    if sensors.runtime_governor_override is not None:
        return _clamp(int(sensors.runtime_governor_override), 0, 0xFFFF)

    adaptive = cal.runtime_governor
    if sensors.governor_axis_z is not None:
        adaptive = min(adaptive, max(0, a160_governor_rate_cap(
            sensors.governor_axis_z, cal.rate_cap_y, cal.rate_cap_slope_q13)))

    # Motor states 0 and 2 use the nominal-capped adaptive result. Other states add the B minimum.
    if sensors.governor_motor_state in (0, 2):
        return adaptive
    budget = (cal.runtime_governor if sensors.governor_budget_limit is None
              else max(0, int(sensors.governor_budget_limit)))
    return min(cal.runtime_governor, adaptive, budget)


def motor_torque_governor(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    Applies FUN_0004503c (Q15-scaled symmetric clamp + second Q15 scale + 512/205-calibrated
    asymmetric slew, writing gp-0x6ace) then FUN_000456a4 (adds gp-0x6ad0, writes gp-0x6acc, read by
    the shaper). [VERIFIED] Motion away from zero is capped to HELD+/-STEP; motion toward zero, or a
    sign-crossing, is immediate (a sign-crossing also zeroes HELD). STEP is selected by gp-0x67f5 (see
    governor_step_selector_bandwidth()): the fast 512 step applies only when the driver holds steady
    AND below 640 counts, so a hard dynamic turn pins the slow 205 step -- combined with V38's ~4x
    larger target, ramp time (target/step) grew ~4x while the sign-crossing reset stayed instant,
    producing a ratchet (see slew_ramp_time_analysis()). ROOT CAUSE, CONFIRMED ON-CAR (V42 Change 1):
    while gp-0x67fa (ECU state) == 4, FUN_0004503c substitutes the fresh governed value with a
    rate-shaped version of the PERSISTED previous value (gp-0x138a) whenever |fresh| > |previous|,
    then unconditionally writes the (possibly suppressed) result back as next cycle's baseline -- a
    genuine, cumulative, self-sustaining ratchet, not a one-shot clamp. State 4 is reachable mid-drive
    (non-diagnostically, via two ordinary 5->4 and 10->4 transitions gated on torque/plausibility
    flags) and no calibration-only fix exists (the branch reads no cal; the decision is unconditional
    once state==4). The fix is a single condition-code nibble at 0x454fe (`bne`->`br`), unconditionally
    skipping the substitution; PROVED SAFE BY CONSTRUCTION because the slew's asymmetric structure
    guarantees |output|<=|target| with matching sign in every branch regardless of HELD, so the
    hard-fault monitor FUN_0004595a cannot trip. [VERIFIED] the control task FUN_0002214a runs at
    ~1000 Hz (OSTM0 79999-count reload at ~80 MHz, cross-checked by the STEER_STATUS=4 dwell cal
    0xC64DF=100 measuring 100.00 ms on the bus); the separate assist-shaping task FUN_00022ca0
    (boost/damping producer) runs at an unresolved rate, an efficacy question only (the V44 damper
    stays net-dissipative at either rate).
    """
    raw_demand = _signed16(st.demand_sum)
    if not st.governor_initialized:
        st.governor_held = raw_demand
        st.governor_initialized = True

    st.runtime_governor_value = computed_runtime_governor(sensors, cal)
    limit = (st.runtime_governor_value * sensors.governor_limit_scale_q15) >> 15
    clamped = _clamp(raw_demand, -limit, limit)
    target = (clamped * sensors.governor_post_scale_q15) >> 15

    step_cal = cal.governor_slew_step_alt if sensors.governor_slew_alt else cal.governor_slew_step_normal
    step = max(0, (step_cal * sensors.governor_step_scale_q15) >> 15)
    previous = _signed16(st.governor_held)

    # Zero or a sign crossing resets the held value. Slew limits only motion AWAY from zero; motion
    # toward zero is accepted immediately. This is not a symmetric delta clamp.
    if (target >= 0 and previous < 0) or (target <= 0 and previous > 0):
        previous = 0
        st.governor_held = 0

    if target > previous:
        if target <= 0:
            governed = target
        else:
            candidate = previous + step
            governed = target if target <= candidate else candidate
    elif target < previous:
        if target >= 0:
            governed = target
        else:
            candidate = previous - step
            governed = target if target >= candidate else candidate
    else:
        governed = target

    governed = _signed16(governed)
    if (sensors.governor_substitution_state == 4
            and abs(governed) > abs(_signed16(st.governor_held))):
        governed = _signed16(st.governor_held)         # state 4 keeps the lower-magnitude held value

    st.governed_demand = governed                      # gp-0x6ace
    st.governor_held = governed

    st.post_governor_compensation = int(sensors.post_governor_compensation)
    st.post_governor_command = _signed16(st.governed_demand + st.post_governor_compensation)  # gp-0x6acc
    return st.post_governor_command


# =====================================================================================================
# SECTION 7 -- SOFT-EME WINDUP SHAPER  (SM2 / SM3)  -- the mechanism V31 neutralises
# -----------------------------------------------------------------------------------------------------
# A different cut class from the gentle EME. gp-0x6acc drives a Q15 integrator against upper/lower
# bounds; sustained saturation enters the SM3 dwell before its factor becomes zero. V31's boost floor
# fixed the observed soft EME, but the later-discovered assist-inclusive gp-0x6acc envelope means this
# model does not claim the floor contains every static combination.
# =====================================================================================================

def soft_eme_windup_shaper(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    Rate-shape the merged command and run the slow-windup soft-EME cut (SM2/SM3). [VERIFIED]
    FUN_00042af8: integrator gp-0x3570 winds on (gp-0x6acc command - bound), where bound is the 3-way
    MAX of a corridor arm (cal 0xC674E, gated OFF hands-off when |gp-0x6bf0|<=corridor_gate 9216), an
    IIR arm (gp-0x3574>>8, ceiling 12288 -- can exceed the 5120 boost floor while the column is
    actively rotating), and a boost arm (cal 0xC6768, authority-latched to 0 once authority>16384 for
    20 cycles via an EXACT-ZERO recovery test). Authority = (|integrator>>15| * 1092)>>10. SM2 entry
    needs command!=0, authority>=16384, AND cal tp+0x74cc!=3 -- V38/V39 carry 3, inhibiting this
    transition. SM3 enters a dwell at |integrator>>15|>=30720, going to a zero Q15 factor after 20
    sustained cycles; the decay branches clamp with max(0,.)/min(0,.), so the integrator snaps to
    EXACTLY 0 on the crossing cycle (not a measure-zero target), making SM3 the only LIVE cut and
    recovery easier than previously modelled -- the ratchet's real cause is the separate state-4
    governor substitution (fixed in V42), not this shaper. [CONTESTED, unresolved] a re-trace argues
    SM1/SM2 are PERMANENTLY blocked on every build including stock by gates 0xC64CD/0xC64CC=3,
    contradicting an older memory; re-verify against raw disassembly before editing 0xC6422 or
    0xC61DE on the strength of either claim. The governor input (gp-0x4f64, motor-rate-adaptive, NOT
    road-speed) is fully described in motor_torque_governor()/rate_cap_binding_analysis(); it is
    applied here as clamp(demand, +/-gov) followed by a separate static +/-0x2000 clamp, output ->
    gp-0x6b98, lockstep-shadowed at gp-0x4ce2. V31's boost floor fixed the observed soft EME on-car;
    the conservative assist-inclusive envelope (4762 governor + 2560 compensation = 7322) exceeds the
    5120 floor, so this model does not claim every combination is contained.
    """
    # Boost-latch logic consumes the PREVIOUS authority before this invocation computes the next value.
    previous_authority = st.authority
    if st.boost_latch_state == 1:
        if previous_authority > cal.boost_latch_auth:
            if st.boost_latch_counter >= cal.boost_latch_dwell:
                st.boost_latch_state = 2
            else:
                st.boost_latch_counter += 1
        else:
            st.boost_latch_counter = 0
    elif st.boost_latch_state == 2:
        if previous_authority == 0:
            st.boost_latch_counter = 0
            st.boost_latch_state = 1
    else:
        st.boost_latch_counter = 0
        st.boost_latch_state = 1
    st.boost_latched_off = st.boost_latch_state == 2 and previous_authority != 0

    # gp-0x6acc drives the integrator through a ONE-SIDED zero-gate (NOT symmetric +/-8192): the
    # condition is the plain inequality x<=8192 (@0x431c4-0x431d8), so the entire negative range passes
    # unchanged and only x>+8192 is zeroed -- any chatter riding this gate could only appear on the
    # POSITIVE command side. Mode selector cal 0xC64C8=0 confirms the default path below is live.
    # [VERIFIED] max|gp-0x6ace|=4762 (Q15 bank seeded at exact unity, no amplifying op on that path) +
    # max|gp-0x6ad0|=2560 (LERP2 ceilings at INDEX>=4150, no extrapolation) = 7322 < 8192, an 870-count
    # margin that genuinely holds; excursions past -8192 hit the separate SATURATING +/-0x2000 clamp
    # near the function's end instead, a smooth clamp with no chatter mechanism.
    sanitized = 0 if _signed16(st.post_governor_command) > 0x2000 else _signed16(st.post_governor_command)
    if cal.shaper_mode == 1:
        command = cal.shaper_bias
    elif cal.shaper_mode == 2:
        command = _clamp(sanitized + cal.shaper_bias, -0x3000, 0x3000)
    else:
        command = sanitized
    st.shaper_internal_command = _signed16(command)     # gp-0x6b08

    corridor_arm = 0 if sensors.shaper_hands_off else cal.corridor_upper
    iir_arm = st.iir_envelope >> 8
    boost_arm = 0 if st.boost_latched_off else cal.boost_floor
    default_bound = max(corridor_arm, iir_arm, boost_arm)
    upper = (default_bound if sensors.shaper_upper_bound_override is None
             else int(sensors.shaper_upper_bound_override))
    lower = (-default_bound if sensors.shaper_lower_bound_override is None
             else int(sensors.shaper_lower_bound_override))

    def q15_delta(a_q15, b_q15):
        return ((a_q15 >> 2) - (b_q15 >> 2)) << 2

    command_q15 = st.shaper_internal_command << 15
    upper_q15 = _signed16(upper) << 15
    lower_q15 = _signed16(lower) << 15
    integrator = st.soft_eme_integrator_q15
    if command_q15 > upper_q15:
        integrator += q15_delta(command_q15, upper_q15)
    elif command_q15 < lower_q15:
        integrator += q15_delta(command_q15, lower_q15)
    elif integrator > 0:
        integrator = max(0, integrator + q15_delta(command_q15, upper_q15))
    elif integrator < 0:
        integrator = min(0, integrator + q15_delta(command_q15, lower_q15))
    else:
        integrator = 0
    integrator_limit_q15 = cal.sm3_clamp << 15
    st.soft_eme_integrator_q15 = _clamp(integrator, -integrator_limit_q15, integrator_limit_q15)
    integrator_magnitude = abs(st.soft_eme_integrator_q15 >> 15)
    st.authority = (integrator_magnitude * cal.authority_scale) >> 10

    # V38/V39's variant gate (3) inhibits this SM2 authority-threshold entry. The downstream SM2
    # recovery/ramp is not reconstructed; its Q15 factor remains replayable state.
    if (st.sm2_state == 1 and st.shaper_internal_command != 0
            and st.authority >= cal.sm2_arm and cal.sm2_variant_gate != 3):
        st.sm2_state = 3
        st.sm2_entry_seen = True

    # SM3 requires sustained saturation before selecting the zero factor.
    if st.sm3_state == 2:
        st.sm3_factor_q15 = 0x8000
        if integrator_magnitude >= cal.sm3_clamp:
            st.sm3_state = 4
            st.sm3_counter = 1
    elif st.sm3_state == 4:
        if integrator_magnitude < cal.sm3_clamp:
            st.sm3_counter = 0
            st.sm3_state = 2
            st.sm3_factor_q15 = 0x8000
        elif st.sm3_counter < cal.sm3_dwell:
            st.sm3_counter += 1
            st.sm3_factor_q15 = 0x8000
        else:
            st.sm3_counter = 0
            st.sm3_state = 3
            st.sm3_factor_q15 = cal.sm3_cut_factor_q15
    elif st.sm3_state == 3:
        if integrator_magnitude == 0:
            st.sm3_counter = 0
            st.sm3_state = 1
            st.sm3_factor_q15 = 0x8000
        else:
            st.sm3_factor_q15 = cal.sm3_cut_factor_q15
    else:
        st.sm3_factor_q15 = 0x8000  # state-1 recovery details remain outside this model

    state_scale = (min(st.sm2_factor_q15, st.sm3_factor_q15)
                   if sensors.shaper_state_scale_q15_override is None
                   else int(sensors.shaper_state_scale_q15_override))
    blend = _clamp(int(sensors.shaper_blend_q15), 0, 0x8000)
    inverse_blend = 0x8000 - blend
    part_a = ((st.shaper_internal_command * inverse_blend) << 2) >> 17
    part_b = (blend * int(sensors.shaper_alternate_term)) >> 15
    r28 = ((part_a + part_b) * state_scale) >> 15
    st.shaper_term_r20 = (int(sensors.shaper_term_r20_override)
                          if sensors.shaper_term_r20_override is not None
                          else (r28 if cal.shaper_term_selector == 0 else st.shaper_internal_command))

    # Final gp-0x6b98 is a SEPARATE path: range_gate(gp-0x6afe) + r20, then the second governor and
    # static +/-0x2000 clamp. It is not gp-0x6acc passed through another clamp.
    st.secondary_mixer_command = _signed16(sensors.secondary_mixer_command)
    gated_secondary = _range_gate(st.secondary_mixer_command, 0x2800)
    pre_governor_output = gated_secondary + st.shaper_term_r20
    governor_limit = st.runtime_governor_value if st.runtime_governor_value <= 0x2800 else 0
    second_governed = _clamp(pre_governor_output, -governor_limit, governor_limit)
    st.merged_command = _clamp(second_governed, -cal.shaper_final_clamp, cal.shaper_final_clamp)
    st.lkas_authority_cut = state_scale == 0
    return st.merged_command                 # -> gp-0x6b98 (0xFEDF1468), the FOC demand


# =====================================================================================================
# SECTION 8 -- HARD-DTC LOCKSTEP MONITOR  (int wall vs float twin)  -- the hardest cut class
# =====================================================================================================

def hard_dtc_lockstep_monitor(st: EpsState, cal: Calibration) -> None:
    """
    The ASIL cross-check: an independent float twin recomputes the same shaper bound; if the int wall
    and the float twin diverge beyond tolerance, latch DTC 0xF00049 and kill the motor. [VERIFIED]
    FUN_00043e44 mirrors the corridor (0xC6598..) and boost (0xC65C4..) arms in float (float Y = int
    Y/1024), tolerant to +/-5 LSB (@0x44640); this is the class the V25-V27 builds tripped (int/float
    desync -> hard fault) -- V31 keeps the twin matched exactly (boost float 4.0 == int 4096/1024), so
    the monitor delta stays 0 and every soft-EME edit must move int AND float in lockstep.
    """
    # Modelled as: the matched builds never diverge; an UNMATCHED edit would set the DTC.
    int_wall = max(0 if True else cal.corridor_upper, st.iir_envelope >> 8,
                   0 if st.boost_latched_off else cal.boost_floor)
    float_twin = int_wall  # matched by construction in V9/V31/V37/V38/V39
    if abs(int_wall - float_twin) > 5:
        st.dtc_0xF00049_set = True   # hard EME: latched motor-off


# =====================================================================================================
# SECTION 9 -- DELIVERY / FOC CURRENT LOOP / MOTOR PWM OUTPUT  (the ISR side)
# =====================================================================================================

def enable_fsm_producer(st: EpsState) -> None:
    """
    Produce the ENABLE/mode byte gp-0x67a4. [VERIFIED] FUN_0002b422 (~0x2b422-0x2b51e, an 8-state
    handshake producer FSM) writes gp-0x67a4 in {0,1,2,3,4,5} from gp-0x67a1/a2/a3/a7 + prior state
    gp-0x3d28. [OPEN] the previously-assumed "{2,3} else LKAS=0" consumer gate is NOT substantiated --
    a Ghidra xref sweep found ZERO readers of gp-0x67a4, the same dead-gate pattern as gp-0x6809; do
    not model an ENABLE cut here until a reader is located (an ep-relative/computed-base read could be
    missed by the xref index).
    """
    # Modelled as a passthrough producer; no confirmed consumer gate exists, so it does not cut here.
    st.enable_fsm = 2 if st.decider_verdict == 0 else 0


def foc_current_loop(sensors: SensorInputs, st: EpsState) -> float:
    """
    Field-oriented control inner loop: turn the merged command into a q-axis current reference and
    drive the PI/SVPWM voltage computation. [VERIFIED] shared EI trampoline FUN_0001492a, EIIC 0x600
    -> FUN_0006404c (ADC-complete) -> phase currents -> FUN_00065afe (resolver sin/cos atan2 rotor
    angle) -> FUN_00068f52 (rotor-speed estimator) -> ASIL sum self-checks -> FUN_00071272 (Park/Clarke
    + PI current regulator + SVPWM, duties x51200.0). This is where "command" finally becomes "motor
    torque": q-axis current is proportional to torque. [OPEN] the exact RAM var handing mixer/shaper
    output into the q-ref is not pinned (may route off-die over CSIG0); the on-chip FOC->PWM chain
    itself is verified, and the carrier's absolute Hz is open.
    """
    # abstract: q-current reference tracks the merged command (torque ~ Iq), gated by FOC enable/fault
    st.q_current_ref = float(st.merged_command)   # proportional stand-in for the Park/PI result
    return st.q_current_ref


def motor_pwm_output(st: EpsState) -> tuple:
    """
    Emit the 3-phase PWM compare values that actually move the motor. [VERIFIED] shared EI trampoline
    FUN_0001492a, EIIC 0x970 -> FUN_00061614 (TSG20) -> FUN_0006c5ce (Park/inverse -> duty compute),
    writing TSG20 CMPU/CMPV/CMPW (0xFFFFCCB0/B4/B8, /51200.0, period-clamped) -- the physical motor
    output endpoint; commutation table at tp-0x2d40 (0xF52C0). [OPEN] the PWM carrier frequency
    (TSG20 clock not confirmed; init writes period 5000 / compares 5160).
    """
    duty = st.q_current_ref / 51200.0
    return (duty, duty, duty)   # CMPU/CMPV/CMPW (3-phase commutation applied in the real emitter)


# =====================================================================================================
# SECTION 10 -- EXECUTION MODEL / ORCHESTRATION
# -----------------------------------------------------------------------------------------------------
# Two clocks drive everything: (1) the RTOS steering task (w_steer_control_task, FUN_0002214a) on the
# OSTM0 base tick (~1 ms), running the command pipeline (arbitration + its inlined SMs are state-gated,
# not phase-gated -- see the module docstring's EXECUTION MODEL); and (2) fast interrupts via the
# shared EI trampoline FUN_0001492a (EIIC 0x600 = ADC-complete/FOC inner loop, EIIC 0x970 = TSG20 PWM
# output) plus the CAN-RX mailbox ISR that stages the command. This function shows the ORDER.
# =====================================================================================================

def control_task(frame: CanSteeringControl, sensors: SensorInputs, st: EpsState, cal: Calibration) -> tuple:
    """
    One tick of the periodic steering control task: CAN command -> motor PWM. [VERIFIED] Task root
    FUN_0002214a (w_steer_control_task, an RTOS task in the ~0xbb900 TCB table) plus sibling task
    FUN_00022ca0 (decider); scheduled off the OSTM0 base tick (compare 0x1387F=79999 => ~1 ms @ 80 MHz,
    likely 1 kHz though the OSTM0 clock is not independently confirmed), with arbitration phase-gated
    within it. This Python runs the whole chain sequentially per call for readability; in the firmware
    the FOC/PWM ISRs (EIIC 0x600/0x970) run asynchronously and far faster than this steering-task tick.
    """
    # -- interrupt-staged input (runs asynchronously in the CAN-RX ISR; shown here for order) --
    steer_torque = can_rx_stage_steer_torque(frame)

    # -- RTOS steering-task body, in firmware order (arbitration block is phase-gated in HW) --
    read_column_torque_voter(sensors, st, cal)                 # driver-torque voter (slot-3 task)
    st.assist_lane = base_driver_assist_lane(sensors, st, cal) # base assist boost curve -> gp-0x6bbe
    shaping = assist_shaping_lanes(sensors, st)                # the 5 sibling assist lanes
    lkas_process_steer_cmd(steer_torque, st, cal)              # CAN setpoint -> gp-0x69ae
    engage_decider(st, cal)                                    # engage/disengage verdict
    steer_torque_arbitration(sensors, st, cal)                 # limit + Q15 gain (+ debounce SM + DTC-49)
    limit_distribute_mixer_gate(st, cal)                       # LKAS-only clamp cascade -> gp-0x6b4c
    motor_torque_demand_aggregator(st, shaping, cal)           # LKAS + assist + 8 lanes -> gp-0x6b94
    motor_torque_governor(sensors, st, cal)                    # adaptive cap/slew + comp -> gp-0x6acc
    soft_eme_windup_shaper(sensors, st, cal)                   # SM2/SM3 + gp-0x6afe/r20 -> gp-0x6b98
    hard_dtc_lockstep_monitor(st, cal)                         # int/float lockstep (hard EME)
    enable_fsm_producer(st)                                    # ENABLE byte producer (no confirmed gate)

    # -- fast ISRs consume the merged command and drive the motor --
    foc_current_loop(sensors, st)                              # ADC-complete ISR (fast inner loop)
    duties = motor_pwm_output(st)                              # TSG20 carrier-valley ISR -> motor

    return duties, st


# =====================================================================================================
# DEMO -- show the five modeled builds across the two historical failure regimes
# =====================================================================================================

def _self_check():
    assert (V9_FULL_SCALE_POSITIVE, V9_FULL_SCALE_NEGATIVE, V9_FULL_SCALE_MIN_MAGNITUDE) == (417, -418, 417)
    expected_governors = {
        0: 5325, 1050: 5325, 1260: 4762, 1318: 4607, 1417: 4342,
        1700: 3584, 2500: 2406, 3700: 1586, 4100: 512, 5000: 512,
    }
    assert {z: a160_governor_rate_cap(z) for z in expected_governors} == expected_governors

    st = EpsState(col_torque_avg=0, col_torque_rate=512, motor_rate_raw=0)
    assert _inline_torque_rate_b(st) == 1533
    st.col_torque_rate = -512
    assert _inline_torque_rate_b(st) == -1533

    # V38 setpoint raise must actually be represented; this was missing before the 2026-07-18 update.
    assert Calibration.for_build("V38").arb_setpoint_limit == 16384
    assert Calibration.for_build("V39").suppress_direct_torque_rate_assist

    lanes = {
        "inline_a": 0, "inline_b": 1533, "magnitude_6b86": 0, "damping_6bd0": 0,
        "friction_6b26": 0, "resonance_6ad4": 0, "return_centre_6b62": 0,
        "filtered_36682": 0,
    }
    v38 = EpsState(mixed_command=-1782, col_torque_max=100)
    v39 = EpsState(mixed_command=-1782, col_torque_max=100)
    assert motor_torque_demand_aggregator(v38, lanes, Calibration.for_build("V38")) == -249
    assert motor_torque_demand_aggregator(v39, lanes, Calibration.for_build("V39")) == -1782
    assert v39.direct_rate_guard_fired

    strong_driver = EpsState(mixed_command=-1782, col_torque_max=320)
    assert motor_torque_demand_aggregator(strong_driver, lanes, Calibration.for_build("V39")) == -249
    assert not strong_driver.direct_rate_guard_fired

    def guard_result(lkas, inline_b, driver, reduced=False):
        case_lanes = dict(lanes, inline_b=inline_b)
        state = EpsState(mixed_command=lkas, col_torque_max=driver, aggregator_reduced_mode=reduced)
        result = motor_torque_demand_aggregator(state, case_lanes, Calibration.for_build("V39"))
        return result, state

    assert not guard_result(-416, 100, 319)[1].direct_rate_guard_fired
    assert guard_result(-417, 100, 319)[1].direct_rate_guard_fired
    assert guard_result(417, -100, 319)[1].direct_rate_guard_fired
    same_sign_result, same_sign = guard_result(417, 100, 319)
    assert same_sign_result == 417 and same_sign.direct_rate_guard_fired
    assert not guard_result(417, 0, 319)[1].direct_rate_guard_fired
    assert not guard_result(417, -100, 320)[1].direct_rate_guard_fired
    assert not guard_result(417, -100, 0xFFFF)[1].direct_rate_guard_fired
    assert not guard_result(417, -100, 0, reduced=True)[1].direct_rate_guard_fired

    # V39 intentionally leaves the adaptive r26 derivative lane untouched.
    adaptive_lanes = dict(lanes, inline_a=200, inline_b=-100)
    adaptive = EpsState(mixed_command=417, col_torque_max=319)
    assert motor_torque_demand_aggregator(adaptive, adaptive_lanes, Calibration.for_build("V39")) == 617
    assert adaptive.direct_rate_guard_fired

    # FUN_0004503c limits only movement away from zero; zero/toward-zero changes are immediate.
    governor_cal = Calibration.for_build("V38")
    toward_zero = EpsState(demand_sum=1000, governor_initialized=True, governor_held=2000)
    assert motor_torque_governor(SensorInputs(), toward_zero, governor_cal) == 1000
    to_zero = EpsState(demand_sum=0, governor_initialized=True, governor_held=2000)
    assert motor_torque_governor(SensorInputs(), to_zero, governor_cal) == 0
    away = EpsState(demand_sum=1000, governor_initialized=True, governor_held=0)
    assert motor_torque_governor(SensorInputs(), away, governor_cal) == 512
    zero_step = EpsState(demand_sum=1000, governor_initialized=True, governor_held=0)
    assert motor_torque_governor(SensorInputs(governor_step_scale_q15=0), zero_step, governor_cal) == 0
    state4 = EpsState(demand_sum=1000, governor_initialized=True, governor_held=500)
    assert motor_torque_governor(SensorInputs(governor_substitution_state=4), state4, governor_cal) == 500

    # RAMP TIME is the invariant V38 broke: same absolute slew steps, ~4x the target. On a hard turn
    # the step is pinned to the SLOW 205 cal, so V38 needs ~14 cycles where stock needed ~3.
    v9_ramp = slew_ramp_time_analysis(Calibration.for_build("V9"))
    v38_ramp = slew_ramp_time_analysis(Calibration.for_build("V38"))
    assert v9_ramp["target_counts"] == 1441 and v38_ramp["target_counts"] == 2806
    assert v9_ramp["cycles_at_slow_step"] == 8 and v38_ramp["cycles_at_slow_step"] == 14
    # LKAS-only (no assist) is the starker comparison: stock reaches full command in 3 slow cycles.
    assert slew_ramp_time_analysis(Calibration.for_build("V9"), 0)["cycles_at_slow_step"] == 3
    assert slew_ramp_time_analysis(Calibration.for_build("V38"), 0)["cycles_at_slow_step"] == 9
    # Both step cals are stock in every build to date -- nothing has ever compensated for the raise.
    for _b in ("V9", "V31", "V37", "V38", "V39"):  # V40 deliberately excluded: it moves them
        _c = Calibration.for_build(_b)
        assert (_c.governor_slew_step_normal, _c.governor_slew_step_alt) == (512, 205)

    # ---- V40: the two cal edits, and what each is supposed to buy ---------------------------------
    v40 = Calibration.for_build("V40")
    # It baselines on V38, NOT V39 -- the r24 guard is dropped entirely.
    assert not v40.suppress_direct_torque_rate_assist
    assert (v40.lkas_output_gain, v40.arb_output_clamp, v40.arb_setpoint_limit) == (3564, 2048, 16384)
    assert v40.boost_floor == 5120 and v40.corridor_upper == 5120
    assert v40.runtime_governor == 4762, "V40 must leave the governor nominal at stock"
    # Edit 1: the slew can never bind, so a sign-crossing reset recovers in a single cycle.
    assert (v40.governor_slew_step_normal, v40.governor_slew_step_alt) == (0xFFFF, 0xFFFF)
    assert slew_ramp_time_analysis(v40)["cycles_at_slow_step"] == 1
    assert slew_ramp_time_analysis(v40, 0)["cycles_at_slow_step"] == 1
    # A step of 0xFFFF exceeds the largest possible demand swing (2 * 0x2800), so it cannot bind.
    assert v40.governor_slew_step_alt > 2 * v40.distribute_lkas_lane_clamp
    # Edit 2: the cap is flat at the table max and can never bind on any build.
    assert v40.rate_cap_y == (5325,) * 5 and v40.rate_cap_slope_q13 == (0, 0, 0, 0)
    assert not rate_cap_binding_analysis(v40)["can_be_rate_capped"]
    assert not rate_cap_binding_analysis(v40, 1024)["can_be_rate_capped"]
    # Flattening does NOT raise the ceiling: MIN(4762 nominal, flat 5325) == 4762 at every rate,
    # which is exactly what the motor already sees at low rate under stock.
    for z in (0, 1050, 1700, 2500, 3700, 4100, 6000):
        flat = a160_governor_rate_cap(z, v40.rate_cap_y, v40.rate_cap_slope_q13)
        assert flat == 5325, f"flat cap not flat at z={z}: {flat}"
        assert min(v40.runtime_governor, flat) == 4762
        assert computed_runtime_governor(SensorInputs(governor_axis_z=z), v40) == 4762
    # Under V38 the same sweep tapers hard -- this is the difference V40 is buying.
    v38_cal = Calibration.for_build("V38")
    assert computed_runtime_governor(SensorInputs(governor_axis_z=4100), v38_cal) == 512
    assert computed_runtime_governor(SensorInputs(governor_axis_z=1050), v38_cal) == 4762
    # A flat Y with LIVE slopes would still interpolate -- the trap V40's slope-zeroing avoids.
    assert a160_governor_rate_cap(4000, (5325,) * 5, GOVERNOR_RATE_SLOPE_Q13) != 5325

    # The motor-rate cap cannot bind on stock LKAS (417 < the 512 cap floor) but does on V31/V38.
    # This is the numeric core of the V38 ratchet hypothesis -- see rate_cap_binding_analysis().
    assert rate_cap_binding_analysis(Calibration.for_build("V9"))["can_be_rate_capped"] is False
    assert rate_cap_binding_analysis(Calibration.for_build("V9"))["lkas_max_counts"] == 417
    v31_cap = rate_cap_binding_analysis(Calibration.for_build("V31"))
    v38_cap = rate_cap_binding_analysis(Calibration.for_build("V38"))
    assert v31_cap["binds_from_motor_rate"] == 3980
    assert v38_cap["binds_from_motor_rate"] == 3414
    assert v38_cap["lkas_max_counts"] == 1782
    # Base assist in the aggregate pulls the binding rate substantially lower still.
    assert rate_cap_binding_analysis(Calibration.for_build("V38"), 1024)["binds_from_motor_rate"] == 2229

    # gp-0x6acc and gp-0x6afe+r20 are distinct paths. The integrator stores Q15, while final output uses
    # the secondary lane and replayed r20 through the second governor.
    shaper = EpsState(post_governor_command=1000, runtime_governor_value=400)
    shaper_inputs = SensorInputs(secondary_mixer_command=200, shaper_term_r20_override=300)
    assert soft_eme_windup_shaper(shaper_inputs, shaper, Calibration.for_build("V38")) == 400
    assert shaper.shaper_internal_command == 1000
    assert shaper.soft_eme_integrator_q15 == 0  # V38 boost floor 5120 contains this command

    q15 = EpsState(post_governor_command=1000, runtime_governor_value=4762)
    assert soft_eme_windup_shaper(SensorInputs(), q15, Calibration.for_build("V9")) == 1000
    assert q15.soft_eme_integrator_q15 == 1000 << 15
    assert q15.authority == (1000 * 1092) >> 10


def _demo():
    print("build |  scenario                         | STEER_STATUS | DTC0x49 | soft-cut | guard | merged_cmd")
    print("-" * 102)
    scenarios = {
        "hard sustained hands-off turn (soft EME)": SensorInputs(
            column_torque_coils=(120, 118, 121), steering_angle=180.0, steering_angle_rate=2.0,
            vehicle_speed=45.0),
        "loaded curve + bump (gentle EME / DTC49)": SensorInputs(
            column_torque_coils=(2100, 2080, 2110), steering_angle=90.0, steering_angle_rate=1700.0,
            vehicle_speed=55.0),
    }
    for build in ("V9", "V31", "V37", "V38", "V39", "V40"):
        cal = Calibration.for_build(build)
        for name, sensors in scenarios.items():
            st = EpsState()
            frame = CanSteeringControl(steer_torque=1000, steer_request=True)
            # run ~1.5 s worth of sustained ticks to let the debounce/DTC/windup counters evolve
            for _ in range(150):
                control_task(frame, sensors, st, cal)
            print(f" {build:4} | {name:33} |     {st.steer_status:1}        |   {int(st.dtc_0x49_set)}     "
                  f"|    {int(st.lkas_authority_cut)}     |   {int(st.direct_rate_guard_fired)}   "
                  f"| {st.merged_command:6}")
        print("-" * 102)

    print("\nV38/V39 discriminating synthetic: saturated LKAS + direct Sensor-B torque-rate impulse")
    print("build | LKAS lane | inline r24 | guard | pre-governor sum | final command")
    print("-" * 78)
    impulse = SensorInputs(
        column_torque_coils=(100, 98, 102), column_torque_sensor_b=100, column_torque_rate=512,
        steering_angle=90.0, steering_angle_rate=100.0, motor_rate_raw=0,
    )
    for build in ("V38", "V39"):
        st = EpsState()
        frame = CanSteeringControl(steer_torque=4096, steer_request=True)
        for _ in range(50):
            control_task(frame, impulse, st, Calibration.for_build(build))
        print(f" {build:4} | {st.mixed_command:9d} | {st.assist_inline_b:10d} |"
              f"   {int(st.direct_rate_guard_fired)}   | {st.demand_sum:16d} | {st.merged_command:13d}")
    print("-" * 78)


if __name__ == "__main__":
    _self_check()
    _demo()

