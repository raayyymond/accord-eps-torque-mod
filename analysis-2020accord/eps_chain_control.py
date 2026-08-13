"""eps_chain_control.py -- SECTIONS 4-6 of the golden model: the engage/disengage decider, steer
torque arbitration, the limit/pack -> distribute -> mixer -> gate cascade, the motor torque demand
aggregator, the motor-rate adaptive governor, and the standalone analysis functions. Split out of
`eps_lkas_chain_model.py` on 2026-08-12 to keep every mandatory-read file under the 256 KB `Read`
cap. Code is VERBATIM; import `eps_lkas_chain_model` for the full facade.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from eps_chain_core import (
    Calibration,
    EpsState,
    SensorInputs,
    _clamp,
    _range_gate,
    _signed16,
)

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

    # 1b) NOT MODELLED NUMERICALLY HERE, but real: a 1-pole IIR sits between the curve-clamp and the
    #     Q15 gain below (decompile ~0x28ea6+1216-1229, state gp-0x3d3c). s[n]=a*s[n-1]+b*x[n],
    #     y[n]=(s[n-1]+s[n])>>5, a=cal(0xC63EC)/1024=992/1024=0.96875, b=cal(0xC63EE)/1024=507/1024=
    #     0.49512, fs=1kHz. [VERIFIED, byte-read+disasm 2026-08-11] -0.17dB/-11.2deg @1Hz ->
    #     -5.29dB/-57.0deg @7.79Hz -> -15.03dB/-79.8deg @28Hz. Believed to be, but NOT proven identical
    #     to, the reader behind the "LKAS lane is a ~1-5Hz low-pass" finding elsewhere in this file --
    #     not cross-checked.

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
#
# ═══ REGIME LIVENESS: {6-20 km/h, ENGAGED, HANDS-ON, RETURNING TO CENTRE} -- 2026-08-12 ═══════════════
# The operator's crux regime. Cals byte-read from the image ON THE CAR (_v96_..._plain_image.bin); on-car
# fractions over his own elicitation episodes n ENGAGED = 90.5 s / 9,145 fr (r7e 50.9 + r7f 39.6), both
# drives fault-free. Full table: analysis-2020accord/_v97/chain_liveness.md.
#   DEAD    gp-0x6bd0 damper  -- FactorC X[0]=2240 ct = 34.97 km/h, Y[0]=0, byte-STOCK m24 AND m26 on V96.
#           ★ OPEN ON 0.00% OF 9,145 FRAMES. Strengthens "95.91% of engaged frames" to 100% of HIS time.
#           ⚠ FactorE's gate (>60 ct = 12.73 deg/s) is open 67-84% here => FactorC is the SOLE binding
#           gate, and opening FactorE alone buys nothing.
#           🛑 Max monotone lift FactorC Y[0]:=Y[3]=908 still delivers EXACTLY 0 at <=13 deg/s (FactorE's
#           own dead zone), 12 at 20 deg/s, 29 at 30 deg/s. No FactorC-only rung reaches the micro band.
#   DEAD    gp-0x6b62 return-centre (0/75,227 engaged) · gp-0x6bda · gp-0x6a10/FactorD (FactorC is
#           upstream) · gp-0x6ade (0 writers).
#   PARTIAL FUN_00036682 filtered term -- IIR alpha 0xC63D2 = 6 => |H(7.8 Hz)| = 0.119 (-18.5 dB), -81.8 deg.
#   LIVE    gp-0x6ad4 resonance PID -- ★ the most reachable authority of any gated lane HERE: its ceiling
#           LERP 0xC67C2 (X=[128,1280,3200] Y=[0,1024,1024] on voted speed) reads p50 395-558 / p90 ~830,
#           i.e. 2-3x the 164-341 quoted elsewhere, because 6-20 km/h is FASTER than the 4.9-8.0 km/h
#           ratchet episodes that number came from. 🛑 V56's mute of this lane was scored at ~21 Hz -- the
#           lane has NEVER been scored at 6-9 Hz, so it is OPEN, not eliminated.
#   LIVE    gp-0x6b26 friction · r24/r26 @1 kHz (Lever B 0xC6446=5244) · gp-0x6bbe (rate-derived) ·
#           gp-0x6b86 · gp-0x67fa state gate (state 5) · gp-0x674e < 28 (V96 b3, 100.00%).
#   NO GATE 0xC62EA = 0 on V96 (V53's edit carried; stock 320 ct ~ 5 km/h) => sstat==3 fires 0.00%.
#
# ★ WHERE THE RETURN-TO-CENTRE AUTHORITY COMES FROM [EVIDENCE, on-car]: openpilot supplies it. During
# the return the LKAS command acts TOWARD centre 88.7%/91.6% and is RAILED at +-4096 on 69.9%/52.1%,
# while the driver has relaxed to |tq| p50 826/811 (vs 2463/2417 while winding) and is roughly neutral.
# 🛑🛑 CONSEQUENCE: for 52-70% of the return the LKAS lane is a DC CONSTANT, yet the 6-9 Hz |tq| envelope
# is unchanged (railed 121.6/378.5 vs unrailed 125.5/277.4). A constant cannot carry 7.8 Hz => THE
# RINGING ENTERS THROUGH A SENSOR-FED LANE, NOT THE COMMAND LANE. Excludes every command-side lever and
# leaves {r24/r26, gp-0x6ad4, gp-0x6b26, gp-0x6bbe, the V89 plant-model path}.
# ⚠ AND THE OPERATOR IS RIGHT THAT THE ENGAGED RETURN IS NOT FASTER -- it is SLOWER, but state it
# stratified: speed x angle matched, r7e 0.367 [0.247, 0.550] (excludes 1), r7f 0.624 [0.266, 1.176]
# (does NOT clear). Unstratified 0.302/0.471 OVERSTATES it. The effect is ANGLE-DEPENDENT: 0.164-0.309
# in 4 of 4 cells at |ang| 50-120 deg; every reversal is at |ang| 10-25 deg. [BELIEF, mechanism] under
# LKAS the wheel converges to openpilot's TARGET with the loop's time constant rather than returning to
# centre on caster -- slower than free return, and ringing in the loop's lightly-damped 6-9 Hz mode.
# ⚠ RUN THE CONTROL: 6-9 Hz engaged/manual replicates at 9.1x/22.4x, but the 15-22 Hz NEGATIVE CONTROL
# also moves (3.8x/5.5x). The contrast is band-PREFERENTIAL (2.4x/4.1x above control), NOT band-exclusive.
# ⚠ HIS BAND IS NOT THE MICRO BAND: over elicitation time |wheel rate| is 1-13 deg/s 23/28%, 13-50 deg/s
# 49/43%, >=50 deg/s 26/24%; in the RETURNING subset 13-50 deg/s is 60-61% and micro only 16%.
#
# 🛑 e4tq IS SIGN-INVERTED vs `ang` and `rate`, and it has been got wrong: corr(cmd[n], d(ang) over the
# next 50-100 ms) = -0.82/-0.71 hands-off engaged (positive control: manual corr(tq,rate) = +0.67/+0.64).
# Establish the polarity causally before any toward/away claim rests on it.
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def motor_torque_demand_aggregator(st: EpsState, lanes: dict, cal: Calibration) -> int:
    """
    Sum every torque-demand lane -- LKAS and base assist alike -- into the single shared command.
    [VERIFIED] FUN_0003aa2c (0x3aa2c-0x3ad70) reads gp-0x6b62 (return-centre), gp-0x6b4c (LKAS,
    +/-0x2800), gp-0x6ade (dead, 0 writers image-wide), gp-0x6ad4 (resonance), gp-0x6b26 (friction),
    gp-0x6bbe (boost assist), gp-0x6bd0 (damping), gp-0x6b86 (magnitude), inline r26/r24 (torque-rate),
    and FUN_00036682's filtered term. Eight of these are ZERO-type range gates (out-of-window
    contributes 0, not clipped): 6b62 +/-0x2000, 6b4c +/-0x2800, 6ade +/-0x400, 6b86 +/-0x3000, 6bbe
    +/-0x800, 6bd0 +/-0x800, 6b26 +/-0x400, 6ad4 +/-0x2800 (@0x3aa38-0x3acc4).
    🛑 ALL EIGHT ARE STRUCTURALLY VACUOUS -- MEASURED 2026-08-04, every ceiling byte-read. Each gate
    is capped by its OWN PRODUCER's ceiling at or inside its gate window, on every drive, every
    build: boost 512 vs 2048 · damping <=512 (the gp-0x6ac2 ceiling floor) vs 2048 -- ⚠ the old
    "EXACTLY 0 at creep (FactorC Y[0]=0)" holds for stock and V44-V73 but NOT for V74, which opened
    both dead zones and measured 67.4% duty at engaged creep; the gate stays vacuous either way
    because 388 is the surface max at creep · friction 511 vs 1024 · magnitude +/-0x3000 ==
    window exactly (inclusive) · LKAS +/-0x2800 == window exactly · gp-0x6ade 0 writers · resonance
    max 1024 (164-341 at the ratchet's speeds) vs 2800 · return-centre gp-0x6b62 max 5786 vs 8192.
    ⇒ THE AGGREGATOR STAGE CONTAINS NO REACHABLE HARD NONLINEARITY, joining the aggregator SUM
    (V65, 120,049 frames). The relay / limit-cycle framing for the aggregator is REFUTED -- do not
    re-propose it. [EVIDENCE] ★ FUN_00036388's own counters give ~20-40 ms or ~1 s periods, nowhere
    near 7.8 Hz ⇒ it INHERITS the ratchet, it does not GENERATE it.
    ★★★ AND THE RATCHET'S Q IS NOW MEASURED: Q ~= 40 at f0 = 7.793 Hz (route 50, one 12.81 s
    provoked episode), confirmed by a WINDOW-CAP INVARIANCE TEST -- 39.0 at cap 54, 40.0 at cap 111,
    where a window-limited estimate would have doubled. ⇒ zeta ~= 0.0125, ~3x more lightly damped
    than the 21 Hz mode. ✅ Q ~= 40 CONFIRMS the record's Q ~= 36; the ONLY thing superseded is
    "Q is not measurable at NFFT 256" -- the claim it could not be measured, not the value.
    ✅ And it is measured on the RIGHT data: the episode reconciles with the transition trace below
    (2 x 2,452 = 4,904 ~= 4,894; speed span = the post-engagement window, NOT the operator's
    cranking), so it is not contaminated by driver input. ⚠ ONE episode, and f0 drift inside the
    window would DEFLATE it ⇒ 40 is a LOWER BOUND.
    ★★★★ THE RATCHET IS ENGAGEMENT-**REQUIRED**, AND NO BUILD IN THIS KIT HAS EVER MOVED IT.
    [EVIDENCE 2026-08-04] Grip confound removed (BOTH arms hands-off, |lowpass(tq,3Hz)| <= 300, creep
    < 4 m/s), pooled over four routes/builds: engaged hands-off 73/88 = 83.0% vs manual hands-off
    0/118 = 0.0%, Fisher p = 3.8e-41 -- ZERO hits in 118 manual hands-off creep windows / 302 s.
    Per-build rate 80/81/79/94% (V70/V69/V62/V59) => BUILD-INDEPENDENT. This SUPERSEDES the earlier
    "engagement-conditional, 44/46 windows" statement.
    ★ Converse: a hand on the wheel SUPPRESSES it while engaged (V59 94->14%, p=3.5e-4; V69 81->37%,
    p=4.5e-3). ★★ Transition trace at constant speed (6-9 Hz Butterworth, sosfiltfilt): lat 0.06 /
    effort 320 -> 134 counts, then lat 0.31 / effort 441 -> 1,179 counts -- 8.8x in 0.7 s with speed
    FALLING 1.75 -> 1.60 m/s; the death is effort 1,548 -> 2,129 over 0.6 s collapsing 910 -> 273.
    🛑 CORRECTION TO THE OPERATOR'S FRAMING, and it corroborates rather than contradicts him: his hard
    MANUAL provocation produced NO ratchet at all (6-9 Hz p-p 422-797, prominence 1-6). The manoeuvres
    SET UP the condition (creep, loaded wheel, LKAS about to take over); the ratchet fires WHEN LKAS
    ENGAGES AND HE LETS GO. Both parts of his account are right; the causal order is reversed.
    ★★ Two consequences: 0x454FE is a GENUINELY UNTESTED lever for the ratchet (absent from all four
    measurements -- V59/V62/V69/V70 are post-V53 and stock there); and engagement-required +
    hands-off-conditional + Q ~= 40 + base-assist damping exactly ZERO below ~35 km/h fuse into
    "AT CREEP THE DRIVER'S HAND IS THE ONLY DAMPING IN THE SYSTEM".
    ⚠ THE LEVER THIS RE-OPENS: base-assist damping is EXACTLY ZERO below ~35 km/h (the FactorC row
    above) while the ratchet lives at 4.9-8.0 km/h with Q ~= 40 -- and V47 raised FactorC AND FactorE
    together and reported "marginally quieter at 5 mph", filed null against the 21 Hz vibration.
    That positive whisper has never been evaluated against the RATCHET. Deferred to V72.
    ⚠ Note the overlap with GATE 3: the resonance row (164-341 reachable vs a 2800 window) is the
    same arithmetic that made V69's bit4 vacuous. A gate's width says what the CONSUMER accepts; it
    says nothing about what the PRODUCER can emit.
    r24/r26 are instead
    SATURATING CLIPS to +/-0x2000 (`cmovle`, @0x3ab82-94/@0x3ac42-54), summed ungated -- the lowest
    discontinuity risk of the group, consistent with V39's r24 suppression not moving the on-car
    vibration. Add order @0x3acc8-0x3ace6: r26+r24 -> +6b86 -> +6bd0 -> +6bbe -> +6b26 -> +[6b62/6ade]
    -> +6ad4 -> +filtered (FUN_00036682). The output clamp @0x3acf0-0x3ad2a is a true SATURATING clamp
    (not a zeroing gate) to +/-0x2800, lockstep-checked at gp-0x4ce0 on all three paths (mismatch, not
    saturation, trips FUN_0006b9fa) -- so the aggregator output is not itself a chatter source.
    [VERIFIED 2026-08-04] ** BOTH INLINE LANES ARE MIRRORED TO RAM, POST-CLAMP, AND NOTHING READS
    THEM: ** st.h r26 -> gp-0x6adc @0x3AD4E and st.h r24 -> gp-0x6ada @0x3AD5A, each 0 readers /
    1 writer image-wide (V64.gp_access_census, two decoders). They are free, blast-radius-zero
    telemetry taps on the exact quantity the rate-lane builds scale -- V69's probe reads gp-0x6ada.
    Note the ld.h/st.h one-bit trap: gp-0x6ada's only real instance IS the st.h form (opcode 0x3B)
    and carries the same displacement halfword as the ld.h (0x39) a probe must emit. A
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
    🛑 CORRECTED 2026-08-08: gp-0x67f5 IS VOTED VEHICLE SPEED, NOT hands-off/hands-on. The governor's
    per-cycle slew STEP is selected by gp-0x67f5 (written only by FUN_00041eec, the SPEED voter):
    voted speed >= cal 0xC531E (1062 = 16.6 km/h) for cal 0xC64E7 (10, a BYTE) cycles selects the SLOW
    step (205, more damped); below that, or on reset, selects FAST (512, less damped) -- so the car runs
    ~2.5x wider governor bandwidth BELOW 16.6 km/h than above it. Every "hands-off vs hands-on" label on
    0xC6206/0xC6208 in the build scripts and BUILD-LINEAGE is wrong for the same reason.
    [VERIFIED] the selector, cals, debounce, and step
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
        "selector_var": "gp-0x67f5 (written only by FUN_00041eec, the VEHICLE-SPEED voter producer)",
        "selector_threshold_cal": {"addr": "0xC531E", "value": 1062, "domain": "voted vehicle speed",
                                   "km_h": 16.6},
        "selector_debounce_cal": {"addr": "0xC64E7", "cycles": 10, "width": "byte"},
        "step_below_16_6_kmh_fast": fast,
        "step_above_16_6_kmh_slow": slow,
        "step_ratio": round(fast / slow, 3),
        "cycles_to_full_command": {
            "below_16_6_kmh": -(-command_counts // fast),
            "above_16_6_kmh": -(-command_counts // slow),
        },
        "corner_hz_at_full_command": {
            "below_16_6_kmh": round(corner_hz(fast, command_counts), 1),
            "above_16_6_kmh": round(corner_hz(slow, command_counts), 1),
        },
        # The decisive number: ripple amplitude transmitted at the symptom frequency.
        "max_ripple_counts_at_30hz": {
            "below_16_6_kmh": round(max_ripple(fast, 30.0)),
            "above_16_6_kmh": round(max_ripple(slow, 30.0)),
        },
        "tick_hz_assumed": tick_hz,
        "status": "[VERIFIED] transmission path gated by VOTED SPEED; [INFERRED] as the cause",
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
    target, whose STEP is VOTED-SPEED-gated (see governor_step_selector_bandwidth()) -- this
    survives the gain-rescaling invariance argument because it is sourced from a PHYSICAL sensor
    reacting to REAL delivered torque (which scales 4x with V38), not a digital replay. ROOT CAUSE
    [🛑 CORRECTED 2026-08-06: this read "[CONFIRMED, V44 restored damping]" and that is VOID under RULE 7
    -- V44 and V47 wrote modes 10/11 on a modes-24/26 car, so neither table was ever read and neither
    restored anything; they are INERT BY TABLE SELECTION, not falsified, and the FactorC/FactorE approach
    was not actually tested until V74]: the base-assist DAMPING lane FUN_00034350->gp-0x6bd0 is
    multiplied by a Q10 factor that is exactly ZERO below 2240 counts of driver torque (hands-off), and
    the firmware has no notch filter anywhere, so the resonance rings undamped hands-off and is damped
    hands-on -- V44 targeted that floor and V47 additionally targeted a second independent hands-off
    deadzone (motor-rate Factor E), both at the wrong mode. Eliminated as causes, on-car: r24 (V39), r26 (V42), the dirty-derivative
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
        "voided_candidate_v44_v47": {
            "name": "base-assist DAMPING lane FUN_00034350 -> gp-0x6bd0, BOTH hands-off deadzones "
                     "(Factor C driver-torque LERP Y[0], Factor E motor-rate LERP Y[0])",
            "edit": "V44 opened only Factor C (0xD27C6/0xD27DA 0->235/234); V47 additionally raised "
                    "Factor E's low breakpoints (0xD2802/04/06 mode 10, 0xD2816/18/1A mode 11 -> "
                    "700/750/800) -- both MODE 10/11 records on a modes-24/26 car",
            "status": "🛑 VOID UNDER RULE 7 (2026-08-06): this entry used to read 'leading_candidate' "
                      "with V47 as the current candidate. Neither V44 nor V47 was ever read by the car "
                      "-- INERT BY TABLE SELECTION, not falsified. The FactorC/FactorE approach was "
                      "first genuinely tested at V74 (engaged columns of all 16 rows), which measured "
                      "the damper live (67.4% duty at engaged creep) and then HARD-FAULTED in MANUAL, "
                      "where its records are byte-stock -- see SECTION 3B",
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
    Accord). [VERIFIED against opendbc]
    ★★★ BOTH RAILS ARE NOW MEASURED, NOT MODELLED (2026-08-06). The slew rail reads 123 counts/frame with
    ZERO frames exceeding it, which is exactly this function's 0.03*STEER_MAX term; and the AMPLITUDE rail
    is matched EXACTLY to the firmware intake FUN_00052676 = clamp(req * -4, +/-0x4000), since
    4096 * 4 = 0x4000. => RAISING STEER_MAX ALONE BUYS ZERO -- the intake clamp removes every extra count,
    so amplitude work must move both sides and the firmware side binds. 16.07% of engaged time sits against
    one rail or the other, slew dominating at highway speed. ⚠ Sibling-agent measurement, not replicated
    here; the 4096*4 identity is arithmetic. Not a licence to edit openpilot (it stays an instrument).
    Quartering the PID restored the loop GAIN but left the command
    SLEW RATE untouched: the slew ceiling in firmware lane counts is (0.03*STEER_MAX*4*gain)>>15, so it
    scales with the FIRMWARE gain -- stock 13.4 counts/10ms tick vs V38 53.5 (4x faster, uncompensated),
    cutting the time to full physical torque from ~170ms to ~42ms and crossing INSIDE openpilot's
    100ms steerActuatorDelay (stock's slow slew dominated and damped the loop; V38's fast slew lets
    the delay dominate instead -- a classic limit-cycle recipe). This is a comma-side scaling gap, not
    a firmware defect, and fits the on-car evidence (V38 onset, engaged-only, absent hands-on, worst
    at low speed, immune to firmware-only V39/V41).
    🛑🛑 THE r26 "AMPLIFIER" COUPLING BELOW IS FALSIFIED ON-CAR BY V61, 2026-07-31. It used to read:
    "It couples to r26 (the adaptive Sensor-B derivative lane) as excitation-to-amplifier: faster slew ->
    bigger column-torque derivative -> bigger r26 -> more motor torque -> more column motion -> repeat",
    and it predicted that KILLING r26 helps. V61 killed BOTH rate taps unconditionally and the grinding
    got WORSE with LKAS on AND appeared in manual driving (worst in reverse) where there was none.
    r24/r26 are +Kd*d(T_bar)/dt added IN PHASE with assist (polarity gp-0x6752 is one load @0x3AB78
    shared by both lanes and by FUN_0003a382's P-term, so it cancels; the combine chain 0x3ACC8-0x3ACDA
    is ten `add`s, no `sub`). In the closed loop that is VISCOUS DAMPING ACROSS THE TORSION BAR: for the
    wheel-inertia-on-bar mode, phi'' + (Kd*k/J_c)*phi' + k*(1/J_w + (1+K)/J_c)*phi = T_road/J_c, so the
    phi' coefficient is positive and LINEAR in Kd. At Kd=0 the mode has no damping term at all.
    ⇒ the lane is the mode's DAMPER, not its amplifier, and the direction of interest is RAISING it.
    V62 doubles it via two `sar 0xa`->`sar 0x9` immediates (0x3AC20, 0x3AB76).
    ★★★★ V62 FLASHED 2026-07-31, DRIVEN route 37 -- THE GRINDING IS FIXED. Engaged creep, speed-
    standardised, episode-clustered bootstrap: 18-22 Hz V62/V59 = 0.124 [0.036, 0.387] (8x), and
    0.024 [0.016, 0.234] at |rate| 16-32 deg/s (42x), with a 30-40 Hz negative control at ~1.0 so the
    effect is band-specific. Transient rates 0.793/0.486/0.338 at >200/>500/>1000. The kit's first
    measured fix, and it confirms the V61 gradient.

    🛑🛑🛑 AND IT IS ALSO THE CAUSE OF "GRIND #2" -- ESTABLISHED 2026-08-01 ON V65 ROUTES 3a/3b.
    The "30-40 Hz negative control at ~1.0" above is a MEAN statistic and it is blind to the
    phenomenon: the matched q99 threshold is 317 while the events are 3000-4000. Corner-conditioned
    EXTREME-TAIL maxima (creep AND |driver torque| >= 1200 AND |angle| >= 100 deg), Kd=1x vs Kd=2x,
    219 blocks:
        1-4 Hz  1.01 | 6-9  1.20 | 10-16  0.80 | 18-22  0.35 | 24-28  2.66 | 30-40  2.98
        40-49 Hz  11.71   (p = 0.0003)
    A MONOTONE FREQUENCY RESPONSE WITH A CROSSOVER AT 22-24 Hz, driver band flat as a control =>
    NOT generic roughness. ONE KNOB CUT GRIND #1 BY 2.9x AND RAISED GRIND #2 BY 11.7x.
    Reproduced independently on the COMMA IMU (40-49 Hz p95 6.27x, max 6.71x; 1-4 Hz 0.76).
    WHY: gp-0x4f62 is a 4-SAMPLE FINITE DIFFERENCE at 1 kHz (2*(x[n]-x[n-4])/4, delay cal 0xC6C42 = 4),
    so its gain RISES with frequency -- 1.93x at 41.6 Hz vs 20.9 Hz. V62's x2 is FLAT in frequency, so
    it raised the high band harder, in absolute terms, than the mode it fixed. V62's own note computed
    selectivity only against the DRIVER (1 Hz, 14.6:1) and never against a HIGHER mode.
    🛑 A FILTER CANNOT FIX IT: differentiator +20 dB/dec vs one real pole -20 dB/dec is FLAT above the
    corner, so one pole drives the 41.6/20.9 selectivity toward 1.0 and never below; two poles low
    enough to bite by 42 Hz cost -92 deg at 20.9 Hz and destroy the lead. Raising 0xC6C42 fails the
    same way (D=24 zeroes 41.7 Hz but leaves -0.3 deg at 20.9 Hz = a pure spring). Confirmed
    structurally: FUN_0007e74a has NO EMA/IIR anywhere, and gp-0x4f60 is a SINGLE physical measurement
    of driver + motor-reaction torque, so no V57-style cal fork exists either.
    => the separation must come from an OPERATING CONDITION. Driver torque separates the two symptoms
    >8x (grind #1 hands-off; grind #2 at tq_avg 1600-2700); LKAS engagement separates only grind #1
    (100% vs a 54.7% base rate, p99 6.63x, against grind #2's 84.5% and 1.33x).
    See analysis-2020accord/rate_lane_frequency_response.py and docs/V66-V67-DESIGN.md.

    ★★ THE FIX: V67 = V66 + the grind #1 fix GATED ON LKAS. Two edits, no cave:
        0x3AA96  c5 -> fb    ld.bu -0x683c[gp],r15 -> ld.bu -0x6806[gp],r15   ONE BYTE
        0xC6446  512 -> 5244                                                  ONE HALFWORD
      with BOTH sar sites left at STOCK 0xa. gp-0x683c has ONE access and ZERO writers image-wide,
      and its flag `lp` already selects cal 0xC6446 for r24 (and 0xC6444 for r26) -- so the firmware
      already HAS a conditional-gain arm and it is merely wired to a dead cell. Repointing it makes
      the gain conditional with no code cave, this kit's only bricking class.
        gate FALSE (LKAS off) -> the LERP, unchanged  => byte-for-byte STOCK base steering
        gate TRUE  (LKAS on)  -> flat 5244 = 2.00x the LERP at grind #1's operating point
                                 (creep 7.2 km/h, 128 deg/s, LERP 2622)
      Arithmetic: 5120*5244 = 26.8M = 1.25% of INT32_MAX; lane saturates at |dtorque| >= 1599 vs a
      measured 123-839. GATE 1 vacuous (read-only load displacement, no RAM claimed).
      GATE 2: the lane is a DERIVATIVE => DC-neutral, so a gain step at engagement is not a torque
      step; and the gate itself is measured below.

    ✅✅ THE GATE IS VALIDATED ON-CAR, from V57's own probe (which flew routes 28/29 in July and had
    never been correlated). `analysis-2020accord/validate_gp6806_gate.py`:
        route 29   7,924 frames /  79.2 s   99.90% agreement with latActive   0.0505 transitions/s
        route 28  29,990 frames / 299.9 s   99.94% agreement                  0.0300 transitions/s
      => gp-0x6806 != 0 IS "LKAS is applying"; it does NOT drop out during steady engaged holding
      (the one ambiguity static analysis could not close, since it is a ramp-FSM phase flag whose
      "settled" phases 5/6/7 could not be ruled out); and it toggles THREE ORDERS OF MAGNITUDE below
      the 21/45 Hz modes, so it cannot parametrically pump.

    ★★★★ V67 FLASHED AND DRIVEN 2026-08-02, route 47 (26 segs, 150,327 frames, 1,495 s, an ordinary
    street->highway->street->parking-lot commute). IT IS THE BEST BUILD THIS KIT HAS MEASURED.
      ✅ PROBE LIVE: byte4 = {0x87, 0xC7} only; bit6 == carControl.latActive in 150,302/150,327 =
         99.983% (the 25 disagreements are single-frame transition edges) => the gate is CONFIRMED
         on-car; bit5 (gp-0x671d, the masking risk that pins the gain to 1024 BELOW stock) = 0 in
         EVERY frame, as is bit4 => the arm was a clean binary. FLIGHT-CLEAN: ST==4 = 0/150,327.
      ★★ GRIND #1 FIXED, and route 47 is the FIRST route to contain BOTH doses with the arm state
         recorded per frame, so the contrast is WITHIN-ROUTE and needs no cross-route comparison:
         18-22 Hz engaged creep, cell-stratified, episode-clustered --
             ENGAGED arm     0.524 [0.337, 0.804] vs Kd=1   (1.183 [0.773, 1.617] vs Kd=2)
             DISENGAGED arm  1.055 [0.669, 1.354] vs Kd=1
         => suppression in ONE ARM ONLY, which is V67's conditional design and which no other built
         artifact produces (it is also the first evidence ever to separate V66 from V67).
         Independent orchestrator pass agrees: 0.55 [0.35, 0.65] on a monotone four-point ladder
         1.50 (Kd=0) / 1.00 / 0.55 (V67) / 0.39 (Kd=2), split-half null [0.90, 1.12].
      ★★ CREEP GRIND #2 ELIMINATED: 40-49 Hz bursts (window envelope p99 > 500; V62/V65 bursts ran
         2000-4000) -- V67 0 in 22 s engaged and 0 in 91 s manual, max 83.5/48.8, against Kd=2x's
         18 and 6 with max 1830.7/1469.6. 🛑 The arms are NOT equally supported: manual expects 3.91
         bursts, P(0) = 0.020 (solid); engaged expects 1.04, P(0) = 0.35 => UNRESOLVED. Needs a
         parking lot, not a build.

    🛑🛑 THE PREDICTED HIGHWAY COST DID NOT MATERIALISE, AND THE PREDICTION IS WITHDRAWN.
    The line that stood here read: "Grind #2 SURVIVES under LKAS, at 2.21x". The delivered multiplier
    is real and is worse than that (2.44x at highway, V67's maximum, 22% above V62's flat 2.00x --
    see ASSIST_RATE_B_RECORDS note 3). But the SYMPTOM does not follow it. With route 2b (V58,
    Kd=1.00x, 227 s of highway -- a baseline two sessions assumed did not exist) brought in, the
    three-dose highway comparison is NULL: 40-49 Hz ratios 0.970 [0.787, 1.154] and 0.938 [0.764,
    1.184] against a split-half null of [0.73, 1.37], no dose ordering, and the corpus-max highway
    envelope (851.5) is on the STOCK Kd=1.00 lane.
    🛑 CORRECTED 2026-08-03. This paragraph read "0.98 [0.71, 1.63] and 0.77 [0.56, 1.44] against a
    split-half null of [0.53, 1.86] ... and ZERO burst windows at any dose across ~1,400 s". Those came
    from an estimator that skipped the detrend + Hann taper and ran 1.4-1.9x LOW. Corrected values above.
    ✅ INDEPENDENTLY CORROBORATED: an event-RATE re-test (a different statistic, blind to the pooled
    level's weakness for rare threshold events) reaches the SAME null -- 0.855 [0.432, 1.702] and
    1.152 [0.496, 2.690] vs split-half null [0.36, 2.50], min detectable ratio 1.61x -- with BOTH
    positive controls firing: wheel order 1 at prominence 79, and grind #1's event rate falling
    monotonically with dose, 0.319 [0.130, 0.661]. Two statistics, same answer.
    Identity settled by amplitude: creep grind #2 runs f0 43-45 Hz at prominence
    48-1062x and envelope 2000-4000; the highway population runs f0 45-47 Hz at prominence ~6x and
    envelope 155-370 => NOT grind #2. What IS real at highway is BROADBAND: 21 maneuvers vs 21
    MATCHED straight-line controls give 6-9 Hz 2.78x and 40-49 Hz 2.13x -- 6-9 rises MORE.
    🛑 BOTH VIBRATION INSTRUMENTS ARE BLIND ABOVE ~50 Hz: CAN is 100.000 Hz EXACTLY (Nyquist 50.00)
    and the comma IMU is 101.02 Hz (Nyquist 50.51) -- 0.51 Hz of headroom, not usable. (An earlier
    figure of 99.9-100.5 Hz for the IMU came from the dt MEAN; ~1% of samples are dropped, so use the
    MEDIAN. Settled by a lattice fit, 77 us vs 2889 us, and a synthetic fold test where 7 of 7 known
    tones fold per 101.02 Hz.) ⇒ every highway null on THESE channels is silent about a >50 Hz event,
    and IMU/CAN agreement carries NO information about the alias -- the discriminant is a 1.021 Hz
    apparent-peak difference against a measured sem of 0.856, so it needs a log at a different IMU
    ODR (208/416 Hz).
    ⚠ THE COMMA MICROPHONE has no FREQUENCY ceiling but bears VERY LITTLE WEIGHT on a TACTILE event,
    and the operator reports FEELING rather than hearing. 🛑 CORRECTED 2026-08-03: `soundPressure` is
    ONE RMS over 1600 samples of 16 kHz PCM => 0-8000 Hz ANALYSED, level at 10.000 Hz -- this line
    previously said "audio at 16-48 kHz". The correction is load-bearing in the direction that WEAKENS
    the null: the 26.4 dB bandwidth penalty vs the ear's ~1/3-octave critical bands (18.5 Hz at 80 Hz),
    which is what downgrades this instrument, DEPENDS on the band being 0-8 kHz. Anyone reading the old
    figure will OVER-weight the null. It reads 4.14x un-weighted p95 / +9.7 dB(A) on the creep grind #2
    and ~1.0x on highway manoeuvres, but that sole positive control sits 64x above the smallest event
    the highway null excludes (25.3% excess power), and it was validated at CREEP where the floor is
    9.9x lower in power. 🛑 A-weighting is the trap (-30 dB at 50 Hz): use the UN-weighted channel.
    ⚠ Also: `_grind2_lib.fs_of()` is biased +0.5-1.4% route-dependently, so grind #2's long-quoted
    "44.9 Hz" is 44.6 Hz.
    🛑🛑 RETIRED 2026-08-03 -- this line read "at highway 40-49 Hz is WHEEL ORDER 3, 10-16 Hz is ORDER 1
    -- peak-finding in 40-49 on a highway log finds a tyre, not the mode." The order-3 half is an
    ESTIMATOR TAUTOLOGY: order = f0*CIRC/v returns ~3.00 BY ARITHMETIC whenever a band-limited argmax
    sits near the centre of 30-49.5 Hz at ~28 m/s. The order-2 figure (1.995 for 26-32 Hz) has the
    IDENTICAL defect -- band centre 29 Hz at 28-30 m/s -- so the two are one tautology counted twice,
    not mutual corroboration. THERE IS NO LINE AT ALL in 30-49.5 Hz at highway: averaged-periodogram
    prominence 1.23-3.83 against a >4 criterion, on every route, build and channel.
    ⇒ Do NOT let this discourage looking there. ✅ SURVIVING: 10-16 Hz ORDER 1 is real (prominence up
    to 79, order 1.00-1.02 per bin) and the general "do not mistake a wheel order for a firmware
    effect" warning stands, better founded. GENERAL RULE: a matching order is evidence only when the
    band is WIDE relative to the order spacing, or when the order is TRACKED ACROSS A SPEED SWEEP.
    And: AVERAGE THE PERIODOGRAMS, THEN PEAK-FIND -- a median-of-per-window-argmax estimator
    manufactures a line at band centre when none exists, and did so this session at ΔBIC 249-460.
    ⇒ KEEP V67. No control-path change is supported by this evidence.
    Reproduce: analysis-2020accord/r47_orchestrator_checks.py.

    ★★★ SUPERSEDED 2026-08-04 BY V69 -- and by a symptom this chain now explains. Routes 4c/4e
    captured the operator's highway lane-change vibration: 4e seg 33 t=51.3 s, an ALC right lane
    change at 25.93 m/s -- bar 1468 counts p-p, 26-30 Hz envelope 614 (20x the route median), lines
    at 28.12/28.51 Hz at prominence 100-107, while 40-49 Hz reads 69 IN THE SAME WINDOW. Not wheel
    order 2 (24.93) or 3 (37.40); not engine order 1 (26.10) or 2 (52.20). And "only when engaged"
    is REFUTED at 40-49 Hz (maneuver/control 2.516 [1.561,3.701] engaged vs 2.558 [1.469,3.747]
    manual) -- the engagement-conditional part is at 18-28 Hz, not grind #2's band.

    V69 (BUILT 2026-08-04, RE-CUT to x4, FLASHED, DRIVEN route 4f--61171e660d 2026-08-04) removed
    the mechanism named at item 3 above rather than trimming it. The gate branch 0x3AC04-0x3AC0C is
    cmp(2)+be(2)+ld.hu(4)+br(2) = 10 bytes with ZERO SLACK, and it REPLACES the LERP rather than
    scaling it -- so speed shaping can reach the engaged lane ONLY if the gate is off. Hence:

        0x3AA96  fb -> c5      gate REVERTS to the dead gp-0x683c (0 writers image-wide)
        0xC6446  5244 -> 512   the now-unreachable arm returns to stock
        0xD2A7E/0xD2A80  3072 -> 12288   mode-10 gain_B  0 km/h record Y[0..1]   (x4 as SHIPPED)
        0xD2ABA/0xD2ABC  2561 -> 10244   mode-10 gain_B 10 km/h record Y[0..1]   (x4 as SHIPPED)

    Delivered multiplier: 4.000x to 10 km/h -> 3.658 @15 -> 3.307 @20 -> 2.578 @30 -> 1.808 @40 ->
    EXACTLY 1.000x at and above 50 km/h, in BOTH arms. ⚠ THE x2 FIGURES THAT STOOD HERE
    (6144/5122, "2.000x ... 1.270 @40") WERE THE SPEC, NOT THE SHIP. Corrected 2026-08-04.

    ★★★★ V69 FLEW AND GRIND #1 CAME BACK -- AT CREEP, NOT AT SPEED. Route 4f, 481.7 s, 8 segs,
    flight-clean (ST==4 0/47,996 and ST==3 0, gridded AND raw 0x18F). Engaged pooled 18-22 Hz
    f0 20.42 Hz prominence 13.47 (criterion >4), f0 IDENTICAL across all 8 search bands, manual 1.25
    = no line. Order veto cleared by the engaged-vs-manual WITHIN-ROUTE speed-matched contrast --
    4.726 [1.082, 18.20] vs null [0.36, 3.24] -- which no tyre or engine order can survive.
        creep <20 km/h vs V62/r37   2.244 [1.438, 3.191] blk, 2.235 [1.533, 3.429] ep  (BOTH units)
        >= 50 km/h vs stock          1.066 [0.690, 1.677] INSIDE NULL  => LANDS ON STOCK
    ⚠ the ALL-SPEEDS headline (1.381 [1.026, 1.724] vs Kd2) loses its CI under the conservative
    episode unit; the CREEP result does not.

    ★★★ THE DOSE-RESPONSE IS NON-MONOTONE, and this is the finding:
        0x (V61) 2501 | 1x stock 879 | 2x (V62/V65) 168 | 2x gated (V67/V68) 109 | 4x (V69) 746
    median e_18-22, engaged creep. THE MINIMUM IS AROUND 2x AND V69's 4x OVERSHOT IT.
    ⚠ cross-route medians without covariate matching -- read beside the matched contrasts above.

    ★★ AND THE EFFECT IS ENGAGEMENT-CONDITIONAL THOUGH THE DOSE IS NOT. V69's 4x applies identically
    in both arms (the gate is dead), yet manual at 4x is INDISTINGUISHABLE FROM STOCK (1.070
    [0.383, 1.396], inside null) while engaged is 2.244x. => the mechanism is inside the CLOSED LKAS
    LOOP, not open-loop damping quality.

    🛑 SATURATION IS ELIMINATED AS THE CAUSE, two independent ways. (a) MEASURED: |dtorque| max
    633.9 on 4f, 0.0000% above V69's 683 rail => >=99.9% of engaged time received the FULL 4.000x;
    it is not a partially-delivered dose. (b) ARITHMETIC: stock and V69 share the SAME +-8192 clip,
    and N(A) is monotone increasing in K, so V69/stock decays toward 1.0 FROM ABOVE and never
    crosses -- minimum 1.049x over the entire reachable input domain. A rail cannot produce
    sub-stock damping. See analysis-2020accord/v70_rail_describing_function.py.

    ⚠ MECHANISM NOT UNIQUELY DETERMINED [BELIEF]. Two candidates fit the dose-response equally:
      (a) a plain derivative-feedback optimum, overshot;
      (b) PARAMETRIC GAIN COLLAPSE -- gp-0x6ac0 is loaded `ld.hu` (UNSIGNED) @0x3AAC4, so the gain
          index is a MAGNITUDE that sweeps 0 -> peak -> 0 TWICE PER CYCLE. V69 turned Honda's 2.00x
          rate rolloff into 8.00x (Y[0]/Y[1] raised, Y[2]/Y[3] left stock), making the damper
          STRONGEST at the zero-crossing and WEAKEST at peak velocity. Modulation depth within one
          cycle at A_rk 1927: stock/V62 1.49x, V69 5.96x, and V67's scalar arm EXACTLY 1.00x -- the
          arm does not merely raise the gain, it LINEARISES it, a virtue never articulated at the
          time. Effective-gain crossover below V62 at A_rk ~1300 (two independent derivations).
          See v70_parametric_gain_collapse.py and v70_surface_vs_rate.py.
    The dose-response is the EVIDENCE; the mechanism is BELIEF.

    🛑🛑 V69's OWN STATED PURPOSE FAILED. The ~26-30 Hz lane-change transient is DOSE-INDEPENDENT:
    it survived (2599 and 4094 counts p-p vs V68's 1468) and runs at FULL amplitude on the STOCK
    rate lane -- V59/r2c at dose 1.000x carries the corpus's LARGEST p-p, 3283 @27.07 Hz. Pooled
    speed-matched 2.000x/1.000x = 1.176 [0.641, 2.320] inside null; route-level Theil-Sen slope on
    dose +5.736 [-25.432, +34.934], 0 inside. ★ The live candidate is EXCITATION, not gain: within
    dose = 1.000x exactly, ALC vs driver-commanded = 2.389 [1.453, 4.898]. Holding excitation fixed
    collapsed the 2.403x contrast 2.849 -> 2.013 with its CI crossing 1 -- an excitation contrast
    wearing a dose label. => DO NOT CHASE THE RATE LANE FOR THIS SYMPTOM.

    🛑 EDIT-ORDER INVARIANT, and it INVERTS for V70: V69 asserts arm == 512 => gate byte == 0xc5.
    V70 restores the gate, so it must assert gate == 0xfb => arm == 5244. Shipping 0xfb with 512
    pins the engaged lane ~5x BELOW stock everywhere -- worse than V61, which measured worse on-car.
    🛑 NEIGHBOUR TRAP: mode 11/12's 0 km/h records are BYTE-IDENTICAL to mode 10's, so the target
    pattern occurs 3x within 40 bytes; address absolutely, never by pattern.
    See docs/V69-DESIGN.md and docs/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md.

    For the record, the pre-drive separation table (measured on V65's creep windows):
        LKAS active   98.7% / 15.7%      driver torque  96.8% / 50.5%     steering rate  81.1% / 48.5%
    ⚠ An earlier claim that driver torque separates them ">8x" is WITHDRAWN -- it compared grind #2's
    measured torque against the DEFINITION of hands-off, not against grind #1's measured
    distribution. The real figure is 1.70x (1268 vs 2158), with heavy overlap.
    🛑 gp-0x671d OUTRANKS the arm and is LIVE. If it fires, the gain is pinned to 0xC6442 = 1024,
    BELOW the stock default, and V67 becomes worse than V66. V67's probe bit5 measures it.
    🛑🛑 "0x3AB76 WAS A NO-OP / r26 IS STRUCTURALLY INERT" -- DOWNGRADED TO BELIEF 2026-08-04, AND
    HALF OF ITS ARGUMENT IS NOW REVERSED. The claim rested on TWO legs. Separate them:
      LEG 1, the GATE -- REVERSED. r26 == 0 iff gp-0x6b5e != 0, and gp-0x6b5e is a trapezoid LERP on
        gp-0x6bda, which is a MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque. Hands-off the
        margin sits ~24x above the kill threshold => THE GATE LEAVES r26 LIVE in ordinary driving and
        most strongly live in hands-off creep -- exactly where the grinds and the ratchet occur.
        See assist_gate_6b5e above for the full byte-level derivation.
      LEG 2, the MAGNITUDE -- STILL BELIEF, unresolved either way. avg's cal base 0xC6564 byte-reads
        as 40 bytes of EXACT ZERO, and no writer was found for the RAM adjustment at
        gp-0x641E..gp-0x6444 (10 of 18 cells checked) => stage1 ~ 0 IF that cal base is really what
        feeds gp-0x69a4. ⚠ THAT LINK WAS NEVER VERIFIED; gp-0x69a4's actual producer is a LIVE
        runtime 10-segment LERP at 0x355C6 in FUN_000352b4, 1 writer / 3 readers (0x355A4, 0x3575A,
        and 0x3AB3A = the aggregator).
    => "r24 carries the ENTIRE lane" is a BELIEF resting on LEG 2 alone. It may still be right, and
    one indirect argument says it is: the measured dose-response is only self-consistent if
    a = gp-0x69a4/1024 is SMALL, because at a ~ 1 the V67/V68 gate (which forces gain_A 3072 -> 512,
    a 6.00x CUT) would put their engaged TOTAL at ~0.94x stock -- essentially ON stock -- yet they
    measured the best grind #1 result in the kit (109 vs stock's 879).
    🛑 CONSEQUENCE FOR ANY GATE-RESTORING BUILD: 0xC6444 = 512 is carried by every build including
    V69, so restoring the V67 gate also restores a 6x r26 cut whenever LKAS applies.
    🛑🛑 STRUCK 2026-08-04 -- 0xC6444 IS A NULL BY CONSTRUCTION, NOT AN UNTESTED LEVER. [EVIDENCE] it
    is read ONLY at 0x3AB5E, and only when lp != 0. On every GATELESS build -- stock, V62, V65, V69,
    V70, V71 -- the gate 0x3AA96 is 0xc5, so lp derives from gp-0x683c, which has 0 WRITERS
    image-wide => that load NEVER EXECUTES. Raising it changes NOTHING unless 0x3AA96 is also
    repointed, which reintroduces the V67/V68 control path the operator rejected. => it is reachable
    only on a build whose control path is already ruled out, and THERE IS NO SINGLE-VARIABLE r26 TEST
    ON THE CURRENT TOPOLOGY. The old "genuinely untested upward (V42 tested it downward, 512 -> 0,
    FALSIFIED)" framing was correct arithmetic about the wrong question. Blast radius, kept for the
    record: 1 reader / 0 writers, no float mirror, same CRC block #48 as 0xC6446, ceiling <= 6553.
    ★ MEASURE IT, DO NOT ARGUE IT: gp-0x6adc is r26's post-clamp mirror (st.h @0x3AD4E, 0 readers /
    1 writer image-wide), the same blast-radius-free class as gp-0x6ada. Because r24 and r26 share
    ONE polarity load (ld.b -0x6752[gp],r14 @0x3AB78, reused at 0x3AB7E for r26 and 0x3AC3E for r24)
    they ALWAYS carry the same sign -- so sign(gp-0x6adc) vs sign(gp-0x6ada) is a matched pair:
    bit4 pinned at 1 while bit3 toggles => r26 is zero; bit4 tracking bit3 => r26 is live. V70 flies
    exactly that pair. This re-attribution of V42/V61/V62 stands only if LEG 2 holds.
    ⚠ The pre-committed r24 saturation caveat did NOT bind: measured dtorque is 123-839 (the route's
    most violent transient implies 739) against a clamp that needs 1820 under V62.
    🛑🛑 STRUCK 2026-08-08 -- ~~V63/V64 do it BETTER by raising only the state>=5 arms 0xC6440
    2048->4096 and 0xC643E 1536->3072~~. gp-0x671a is the OSCILLATION DETECTOR's debounced authority
    level (FUN_000428d4, ONE writer image-wide `st.b r7,-0x671a[gp]` @0x42A12, sourced from gp-0x67df
    and the raw count gp-0x357c), and gp-0x67df has NEVER been non-zero in this kit (0/53,991 on V68,
    0/186,321 on V67, 0/14,980 on V64) => the state>=5 arms are DEAD IN PRACTICE, not merely rare, and
    a cell spent on either buys nothing. The latch description below is correct but moot.
    ⚠ NOT "only while oscillating": the counter is a ONE-WAY LATCH with a 5 s hold, so once tripped it
    carries into subsequent manual steering. V63/V64 is "V62, but only after an oscillation has happened".
    V64 = V63 + the cave probe repointed at the detector (0x14A byte4: bit6 state>=5, bit5 state!=0,
    bit4 FSM left neutral, bit3 r24 override), so a null is interpretable instead of ambiguous.
    See rate_lane_damping_model.py, build_v62_tva.py, build_v63_tva.py, build_v64_tva.py. Motor ripple is ruled out (hand steering
    delivers comparable torque through the same smooth output stage), which leaves the LKAS-only
    segment upstream of the aggregator -- see lkas_iir_quantization_analysis() for the standout
    stateful element there (gp-0x3d3c). PROPOSED TEST, in order: comma-side STEER_DELTA_UP/DOWN
    3->0.75 first (reversible, no flash/brick risk) before building any firmware image; if the symptom
    only softens, ~~the r26 cal kill attacks the amplifier~~ 🛑 STRUCK 2026-07-31: the r26 kill was flown
    (V42 alone, then V61 with r24) and made the grinding WORSE -- r26 is a damper, see above; the
    remaining lever on this lane is RAISING it (V62). [CONFIRMED] the PID rescale and engaged-only
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
    governor_step_selector_bandwidth()): 🛑 CORRECTED 2026-08-08 -- the fast 512 step applies BELOW
    16.6 km/h of VOTED SPEED, not "when the driver holds steady", so ordinary road speed pins the slow
    205 step and creep does not -- combined with V38's ~4x
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

