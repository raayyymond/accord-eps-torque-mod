"""model/eps_chain_delivery.py -- SECTIONS 7-10 of the golden model: the soft-EME windup shaper, the
hard-DTC lockstep monitor, delivery / FOC / motor PWM, the `control_task` orchestration, the
`_self_check` / `_demo` harnesses, and the plant-model disturbance observer. Split out of
`model/eps_lkas_chain_model.py` on 2026-08-12 to keep every mandatory-read file under the 256 KB `Read`
cap. Code is VERBATIM; import `eps_lkas_chain_model` for the full facade.
"""

from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------

from dataclasses import dataclass, field, replace
from typing import Optional

from eps_chain_core import (
    Calibration,
    CanSteeringControl,
    EpsState,
    SensorInputs,
    V9_FULL_SCALE_MIN_MAGNITUDE,
    V9_FULL_SCALE_NEGATIVE,
    V9_FULL_SCALE_POSITIVE,
    _clamp,
    _range_gate,
    _signed16,
)
from eps_chain_lanes import (
    _inline_torque_rate_b,
    assist_shaping_lanes,
    base_driver_assist_lane,
    can_rx_stage_steer_torque,
    lkas_process_steer_cmd,
    read_column_torque_voter,
)
from eps_chain_control import (
    GOVERNOR_RATE_SLOPE_Q13,
    a160_governor_rate_cap,
    computed_runtime_governor,
    engage_decider,
    limit_distribute_mixer_gate,
    motor_torque_demand_aggregator,
    motor_torque_governor,
    rate_cap_binding_analysis,
    slew_ramp_time_analysis,
    steer_torque_arbitration,
)

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

    # 🛑 CORRECTED 2026-08-08: gp-0x6acc drives the integrator through a SYMMETRIC +/-0x2000 zero-gate --
    # the decompile is (x + 0x2000U) < 0x4001 (@0x431c4-0x431d8), an unsigned-wrap range test, NOT the
    # one-sided x<=8192 this comment used to claim; the "chatter can only appear on the POSITIVE side"
    # corollary is WITHDRAWN. Mode selector cal 0xC64C8=0 confirms the default path below is live.
    # [VERIFIED] max|gp-0x6ace|=4762 (Q15 bank seeded at exact unity, no amplifying op on that path) +
    # max|gp-0x6ad0|=2560 (LERP2 ceilings at INDEX>=4150, no extrapolation) = 7322 < 8192, an 870-count
    # margin that now bounds BOTH sides, so the gate is unreached in either direction on this envelope.
    _gated = _signed16(st.post_governor_command)
    sanitized = _gated if -0x2000 <= _gated <= 0x2000 else 0
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

    st = EpsState(speed_voted=0, col_torque_rate=512, motor_rate_raw=0)
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


# ===================================================================================================
#  THE PLANT-MODEL DISTURBANCE OBSERVER -- added 2026-08-09 (V89). Ghidra-verified this session,
#  decompile first then assembly, on stock code.bin.
#
#  This branch had never been in the golden model. It is NOT the LKAS command path: nothing here
#  sums into the command. It is a model of the steering plant whose disagreement with the assist
#  actually produced drives a correction. Every build V38..V88 moved the command or a lane feeding
#  it; V89 is the first to move THIS.
#
#      FUN_0003b8f6  -> gp-0x6bfc -> FUN_0003bc20 -> gp-0x6bfe -> FUN_00038148 -> gp-0x6b70
#                                                                 -> FUN_00037fe6 -> gp-0x6ad6 -> PID
#
#  MEASURED, 30 routes / 284 min / 235 episode blocks (v89_c2, v89_c3):
#    * engaging LKAS multiplies 6-9 Hz column energy 2.8x, band-specifically vs a 32-38 Hz control
#      (+0.413 [+0.146, +0.667]) and NOT more at higher wheel rate (+0.022 [-0.070, +0.116]);
#    * `0xC40BC` 600 (more friction) 2.89x vs 6000 (less) 6.58x  => LESS friction, MORE ratchet;
#    * driver grip damps the same band (-0.655 vs control -0.266, CIs disjoint).
# ===================================================================================================

FRICTION_CLAMP = 10.0            # 0x3BB32 movhi 0x4120 (10.0f) / 0x3BB42 movhi -0x3ee0 (-10.0f)
MODEL_OUT_CLAMP = 20000          # 0x3BBCE addi -0x4e20


def plant_model_friction(model, g6abc, polarity, state, k1=102, k0=0, alpha=408, gate=600):
    """`FUN_0003b8f6`'s Coulomb friction term. Mirrors the float ops, address by address.

    k1 = cal[0xC40D2] (0x3BAFE)   k0 = cal[0xC4080] (0x3BAF6, the NEVER-RAISE pure-relay arm)
    alpha = cal[0xC40D0] (0x3BB22)   gate = cal[0xC40BC] (0x3BAB4)
    Returns (friction, new_state). V89 sets k1 = 204.
    """
    ratio = (polarity * g6abc * 12) / gate if gate else 0.0    # 0x3BAAE..0x3BAD0
    ratio = max(-1.0, min(1.0, ratio))                         # 0x3BAD4..0x3BAE4
    raw = abs(model) * ratio * k1 / 1024.0 + ratio * k0 / 1024.0   # 0x3BB02..0x3BB16
    state = state + (raw - state) * alpha / 4096.0             # 0x3BB1E..0x3BB2E  (gp-0x362c)
    return max(-FRICTION_CLAMP, min(FRICTION_CLAMP, state)), state


def plant_model_output(model, friction, damping, gain=2639):
    """0x3BBBE..0x3BBE0. `gain` = cal[0xC6468] -- SHARED, five readers, do not edit."""
    out = int((model - (friction + damping)) * gain)
    return max(-MODEL_OUT_CLAMP, min(MODEL_OUT_CLAMP, out))


def observer_residual(model_out, actual_aggregate, extra=0):
    """`FUN_00038148` @0x38218: residual = MODEL - ACTUAL. `gp-0x6b70 = sign(res)*LERP(|res|)`.

    ACTUAL is an EMA of six aggregator lanes (gp-0x6b4e/6b4c/6b26/6b46/6bd0/6bbe), each with its own
    cal gain at 0xC73a0..0xC73ac; gp-0x6bd0 is the base-assist damper, so the damper feeds the
    ACTUAL side. `FUN_0003bc20` sentinels the model to 0x7fff outside +-20000 first.
    """
    if abs(model_out) > MODEL_OUT_CLAMP:
        return None                                   # 0x7fff sentinel -> gp-0x6b70 = 0x7fff
    return model_out - (actual_aggregate >> 4) + extra


if __name__ == "__main__":
    _self_check()
    _demo()

