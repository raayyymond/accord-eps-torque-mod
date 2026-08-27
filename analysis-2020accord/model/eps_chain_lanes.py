"""model/eps_chain_lanes.py -- SECTIONS 2-3 of the golden model: CAN intake and the LKAS setpoint, the
driver torque sensor and voter, base driver assist, the boost index, and the assist-shaping rate
lanes. Split out of `model/eps_lkas_chain_model.py` on 2026-08-12 to keep every mandatory-read file under
the 256 KB `Read` cap. Code is VERBATIM; import `eps_lkas_chain_model` for the full facade.
"""

from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

from dataclasses import dataclass, field, replace
from typing import Optional

from eps_chain_core import (
    Calibration,
    CanSteeringControl,
    EpsState,
    SensorInputs,
    _clamp,
    _div_trunc_zero,
)

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
        st.speed_voted = 0xFFFF
    else:
        st.col_torque_max = max(abs(c) for c in coils)
        st.speed_voted = sum(abs(c) for c in coils) // valid
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
# 🛑 MEASURED CORRECTION 2026-08-12: gp-0x6bbe AS DELIVERED IS RATE-DERIVED, NOT "the base-assist
#   output". bbe<-tq is 0.01 ct/ct at +144 deg -- fully explained by BOTH channels being driven by
#   omega -- while bbe<-omega is FLAT 87-92 ct/(rad/s) across 2-12 Hz at +18 deg (6-9 Hz), i.e. it is
#   source-side. This CONTRADICTS the earlier "viscous + DC pedestal / base-assist output" reading and
#   the "same-signed as the torque sensor => REINFORCING" flag that once justified a telemetry bit.
#   DEAD AS A LEVER: 9-15 % of Re(Z), and its rate part is 4-9 % of a 73-80 ct DC assist pedestal.
#   => memory/reference/firmware/reference-accord-gp6bbe-is-rate-derived-not-base-assist.md
#     FUN_00034350 -> gp-0x6bd0   5 multiplied gain factors, sign forced opposite gp-0x6abe [damping]
# 🛑🛑 ALL FIVE DAMPING FACTORS ARE MODE-TABLE SELECTED (2026-08-05). FUN_00034350 (sole caller
# FUN_00022ca0) picks B/C/D/E AND the ceiling through pointer arrays indexed by mode*4,
# mode = *(byte)(gp+0x63fd), 13 variants:
#     FactorB 0xC9CCC[m]  FactorC 0xC9E9C[m]  FactorD 0xC9DB4[m]  FactorE 0xC9F84[m]  ceiling 0xC77A0[m]
# ★ RECORD LAYOUT (byte-verified on modes 24/26, 2026-08-07): [npt][X x npt][Y x npt] -- u16 n@+0,
# i16 X[]@+2 (🛑 NOT +4 -- that misread yields [X1,X2,X3,Y0]), i16 Y[] Q10 at base + 2 + 2*npt, i.e.
# 🛑 +0x0A for a 4-point record and +0x0C for 5-point FactorD; u16 terminator 0x0000 @+2+4n.
# Below X[0] clamps to
# Y[0] (STRICT <=, so idx==X[0] clamps too); above X[n-1] clamps to Y[n-1]; else truncating LERP.
# 🛑🛑 n IS NEVER READ BY THE EVALUATOR: each factor's `while(X[i]<=idx) i++` loop is real, but its
# length is PINNED by hardcoded immediates -- FactorB/C/E n=4, FactorD n=5, ceiling n=2, confirmed
# against every shipped record (friction n=3, same mechanism). => adding a breakpoint is a CODE edit;
# relocating a same-size record is cal-only (one u32 pointer-array write).
# The product carries NO signal magnitude -- it is five Q10 GAINS; rate enters via FactorE's LERP index
# and speed via FactorC's, and the SIGN comes from gp-0x6abe.
# ✅ RESOLVED 2026-08-07 -- gp-0x6abe IS THE SIGNED TWIN OF gp-0x6ac0. Both are filtered from gp-0x4f50
# in FUN_00041464 and stored at 0x41b56: gp-0x6abe = (short)(uVar16 >> 10) SIGNED, gp-0x6ac0 =
# |uVar16| >> 10 RECTIFIED. So the damper's index and its sign are the SAME motor-rate signal, and
# sign(gp-0x6bd0) = -sign(motor rate) exactly (applied at 0x3469E-0x346A2, `cmp r0,r11 / ble /
# subr r0,r8`). [EVIDENCE] ⇒ gp-0x6bd0 is -sign(rate) x M(|rate|): a viscous damper when M is
# proportional to |rate|, a COULOMB RELAY when M is flat. seed = gp-0x698a (the "FactorA" long sought
# as a separate table) is MIN-clamped to <=1024 -- corrected 2026-08-07, it is NOT "pinned"; an
# unclamped seed below 1024 passes through, matching the "MIN-clamped seed" phrase already used in
# assist_shaping_lanes' docstring, which this line previously contradicted.
# ★★★★★ THE LIVE MODE IS SETTLED (2026-08-05, V73's probe, 104,061 frames): the car is row 11 'TVCA4' and
# runs mode 24 DISENGAGED / 26 ENGAGED -- the mode TOGGLES with engagement (gp-0x67f6 picks e012 when
# settled-disengaged, e014 when settled-engaged). Forced by the MANUAL arm: the 4-bit probe field drops
# bit 4, so observed 8 means true in {8,24}, and raw 8 appears in NO row of 0xCD000 => manual = 24; only
# row 11 holds 24, and all four columns come from one row => engaged = 26. The engaged reading of 10
# alone would NOT have closed it (rows 2/3/6/7 all carry raw 10).
# => V72 edited modes 10/11 on the ASSUMPTION that 39990-TVA-A160 -> row 2 'TVAA1'. That was wrong, and
# V44, V47, V72's Levers B/C and BOTH of V73's levers were INERT BY TABLE SELECTION -- uninterpretable,
# not falsified. RULE 7 (docs/BUILD-LINEAGE.md): a lever is mode-proof, or it is a bet.
# ★ Engaged (e014/e015) and disengaged (e012/e013) column sets are DISJOINT across all 16 rows, so dosing
# the engaged columns delivers whatever row is live while leaving manual byte-stock.
#
# 🛑🛑 THERE ARE TWO DEAD ZONES, ON DIFFERENT AXES, AND TOGETHER THEY ARE WHY CREEP HAS NEVER HAD DAMPING:
#     FactorC 0xC9E9C[m]  axis = SPEED gp-0x6a5e   X[0] = 2240 = 35.0 km/h on the live modes   Y[0] = 0
#     FactorE 0xC9F84[m]  axis = RATE  gp-0x6ac0   X[0] = 60                                   Y[0] = 0
# A LERP clamps flat to Y[0] below X[0], and zero x anything = 0, so the speed factor alone forces the
# damper to exactly zero at creep. ⚠ The speed onset is MODE-DEPENDENT: X[0] = 1280 (20 km/h) on modes
# 0-3, 1920 (30 km/h) on 4/5, 2240 (35 km/h) on 10-15 and 22-27. Never quote "35 km/h" without the mode.
# 🛑 CONSEQUENCE FOR SIZING: because both Y[0] are zero, SCALING a record by any k is structurally vacuous
# at creep (k x 0 = 0); only lifting Y[0] delivers, and Y[0] := Y[1] is the largest monotone lift of Y[0]
# alone. Raising FactorC costs NO rate-proportionality (it is speed-indexed); FactorE's shape IS the
# rate-proportionality.
# ★★★★ MEASURED OPERATING POINT: gp-0x6ac0 in-burst = 99 counts [94, 113] -- INSIDE FactorE's dead zone,
# on its first rising segment. Priced there against a requirement of ~43 [30,60]: stock 0; FactorC
# Y[0]:=Y[2] alone 6; FactorC Y[0]:=Y[3] alone 14; BOTH dead zones opened ~50. => NO FactorC rung alone
# reaches it. The lever is FactorC Y[0]:=Y[2] + FactorE X[0]: 60 -> 12 + FactorE Y[1]:=Y[2], on the 13
# ENGAGED modes. ★ It OPENS THE RATE DEAD ZONE rather than raising a gain, so the damper becomes genuinely
# rate-proportional in the symptom's range -- the OPPOSITE of V72's flatten-to-relay error, not a larger
# version of it. 🛑 Always price a damper rung at the symptom's OWN measured rate: 330 vs 99 inverted the
# recommendation here.
# 🛑 X[0] IS 12, NOT 6, AND THE REASONING MUST SURVIVE (a bare "12" invites re-optimising it down):
#   (1) a firmware review flagged X0 < 30 with Y1 > 300 as the zone it would not fly without telemetry;
#       12 is the TOP of its own 6-12 band and halves that concern for a ~6% dose cost (53 -> ~50).
#   (2) the rate conversion is rigid-body and biased LOW through a resonance -- measured at the COLUMN,
#       indexed at the MOTOR, and 18-22 Hz is TORSIONAL, so the true dose is HIGHER than computed.
#       Erring low is the correct side of that error.
# ⚠ GATE 2 NOTE: V72 set mode 10's FactorE Y[0..2] -> 927, i.e. FLAT across the whole rate axis, turning a
# rate-proportional damper into a near-BANG-BANG RELAY (magnitude ~constant, sign = -sgn(gp-0x6abe)). A
# relay in a loop at a lightly-damped resonance is a limit-cycle GENERATOR. Had it been delivered it could
# have made the ratchet WORSE. V73 instead sets Y[0] := that record's own Y[1], preserving proportionality.
# ⚠ Both this lane and the friction lane below are gated by the SAME andi 0x830 state mask on gp-0x67fa
# (damper via FUN_00022ca0; friction via FUN_0002214a @0x228cc) => if the live state is outside {4,5,11},
# NEITHER delivers. 0x830 is a SUBSET of 0xc30, so no state runs the aggregator without the damper.
# ✅ SETTLED ON-CAR (route 5d, 101,118 frames): gp-0x67fa reads 5 on 101,117 and 4 on 1 (the last frame,
# in PARK), and FUN_0002214a's guard is literally `uVar2 = 1 << (gp-0x67fa & 0xf)` then `uVar2 & MASK`, so
# state 5 => 0x20 clears 0x830 / 0x930 / 0xc30 / 0xd30 / 0xd38 / 0xdfa / 0x83a / 0x820 -- the whole chain
# ran on every frame, and gp-0x67fa == 4 is dead (third replication; 0x454FE never executes).
# 🛑 TWO MORE GATES, INSIDE FactorC/FactorE THEMSELVES, byte+decompile confirmed 2026-08-07:
#   FactorC: if (gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1) -> FC forced to UNITY (0x400), bypassing the
#     LERP and its speed dead zone entirely. [OPEN] gp-0x67f4 != 1 (voter implausible) forcing UNITY
#     rather than a fail-safe zero has never been probed on this car.
#   FactorE: if !((gp-0x6ac0 < 0x32c9) && (gp-0x6abe + 13000 <= 0x6590)) -> the WHOLE damper term is 0,
#     not just FactorE -- a second validity/kickback window layered on top of the rate dead zone above.
#
# 🛑🛑 THE OUTPUT CEILING IS EFFECTIVELY A CONSTANT 512, NOT A DYNAMIC 512..1024 (2026-08-06).
# ceiling = LERP(gp-0x6ac2, 0xC77A0[mode*4]), and all 26 modes carry an identical X=[300,800] Y=[512,1024]
# (byte-verified on modes 24/26 too, 2026-08-07). gp-0x6ac2 is NOT a rate: FUN_00041464 sets it to
# |motor rate| >> 10 only when sign(motor rate) differs from sign(gp-0x6b98), and to 0 otherwise -- a
# SIGN-GATED BACK-DRIVE (kickback) DETECTOR. In ordinary same-sign driving the index is 0, the LERP
# clamps flat to Y[0], and the ceiling sits on its 512 floor.
# => SIZE EVERY DAMPER LEVER AGAINST 512. The build-time rule (FactorC x FactorE[3]) >> 10 <= 512 is the
# real constraint, not a conservative one.
# ✅ RESOLVED 2026-08-07 (was: "ld.h or ld.hu, floors to -1 or rails to 65535, one bit, opposite
# answers"). There is a THIRD path AHEAD of the LERP: `if gp-0x6ac2 >= 0x32c9: uVar10 = *(u16*)0xC6158`
# (=512, byte-verified) BEFORE the LERP runs. The 0x41852 validity bypass's 0xFFFF sentinel is >= 0x32c9
# under either a signed or unsigned read, so it lands on this SAFE LOW override, not on the LERP's own
# Y[n-1]=1024 -- the ld.h/ld.hu question is moot either way.
# gp-0x6bd0 = clamp(product, -uVar10, +uVar10), symmetric, and is itself int/int lockstep-shadowed at
# gp-0x4cf2 (`if cur == shadow: store both; else FUN_0006b9fa(gp-0x4cf2)`) -- distinct from the ceiling
# LERP's own int/float lockstep at cal 0xC6554/58/5C/60 noted at assist_shaping_lanes below.
#
# ★★★★ FIRST EMPIRICAL ANCHOR ON gp-0x6bd0 (V74, route 5d, 101,118 frames -- the kit's first positive
# control on the damper). bit7 = (gp-0x6bd0 != 0) fired on 23,603 frames = 23.342%: ENGAGED 39.927%,
# ENGAGED CREEP <=4 m/s 67.443% vs MANUAL CREEP 0.292% (230.7x). V72's probe on the same cell read
# 0/87,940. All 943 manual bit7 frames lie within 5 s of a disengagement and 0 of 40,398 beyond it, which
# confirms the engaged-column-only design AND re-measures the 2.08 s mode fall lag on a different cell.
# Delivered dose at the ratchet's own 99 counts = exactly 50 (design target); stock 0 at every creep
# speed; 0 frames reached the ceiling. 🛑 The ~43 requirement is TORSION-BAR counts and this is AGGREGATOR
# counts -- still unconverted. ⚠ A (speed, column-rate) model reproduces bit7 on 91.240% of frames with a
# one-way residual (under-predicts), so every modelled dose is a LOWER BOUND.
#
# 🛑🛑🛑 AND V74 HARD-FAULTED (2026-08-06): a latched total loss of power steering, LKAS DISENGAGED, over
# a bump -- and these edits were NOT IN FORCE when it did. [EVIDENCE, verified two ways] disengaged is
# MODE 24, and all five mode-24 damper records are BYTE-IDENTICAL TO STOCK on V74 and V75 (FactorC
# 0xD67E4, FactorE 0xD6820, FactorB 0xD6760, FactorD 0xD67A4, ceiling 0xD60B4), and 0 of the 54 non-CRC
# V73->V74 diff runs lands inside a mode-24 record. ⇒ a MANUAL fault can only come from the MODE-PROOF
# residue, not from this lane's dose, and on V74 that residue included 0xC63A0 = 2048 (end of section).
# 🛑 k* in (0.580, 1.580] is VOID: it was fitted from "V74 flew clean" + "V75 faulted", and V74 did not
# fly clean. No build in the current lineage has demonstrated safety. V75 then hard-faulted too.
# ★★★★ DOSE-RESPONSE over V72 (k=0) / V73 (k=0) / V74 (k=0.5799) / V75 (k=1.5798): the 18-22 Hz slope is
# -0.599 [-0.856, -0.348] = -5.20 dB per unit k, CI EXCLUDES ZERO, while the 6-9 Hz slope is
# -0.089 [-0.350, +0.163], CI INCLUDES ZERO -- FLAT.
# 🛑🛑 THE 18-22 Hz LEG IS RETRACTED 2026-08-07 -- see "GRIND #1 IS INERT TO THE DAMPER DOSE" below.
# On one instrument across k = 0.58 -> 4.16 every grind-#1 point sits inside its own split-half null.
# The 6-9 Hz leg SURVIVES and is EXTENDED: it does move, but only at V80's k = 4.16.
# ⇒ THE DAMPER FIXES THE GRIND AND CANNOT FIX THE MICRO-RATCHET: the ratchet needs k = 4.2-13.5 against
# the 1.5798 that faulted, so stop sizing this lane for it.
#
# ★ DOSE AXIS, for consistency with the build scripts: dose(v,r) = min((C(v)*E(r))>>10, ceiling), with
# FactorB and FactorD byte-read flat 1024 (inert unity) in BOTH modes 24 and 26 on this car (confirmed
# 2026-08-07), so it collapses to just C x E, ceiling-clamped.
# 🛑🛑 FactorD IS ALSO STRUCTURALLY INERT WHERE THE SYMPTOMS LIVE, not merely flat -- 2026-08-09.
#   FactorC multiplies in BEFORE FactorD and has X[0] = 2240 counts = 34.97 km/h with Y[0] = 0, in ALL
#   FOUR of this car's modes, so the product is exactly zero below ~35 km/h whatever FactorD holds.
#   A third gp-0x6a10 consumer -- the boost LERP2 in FUN_00034a72 -- is ALSO flat-zero in band0
#   (0-8 km/h) in all four modes. Three independent confirmations. [EVIDENCE]
#   ⇒ ch0 = gp-0x6bd0 is exactly ZERO on 98.8% of engaged frames on route 6e (p50 AND p90 both 0.00
#   counts against a +-25600 clamp) ⇒ 0xC63A0 1024 -> 2048 is INERT, V72/V73's correlation with it has
#   NO mechanism (they carried Honda's damper too), and V84's own 0xC63A0 revert was itself inert.
#   ⚠ Ledger: 0xC63A0 was reverted at V83a (not V84); V76g also carried 2048; V76 and V80 are 1024.
# 🛑🛑 AND gp-0x6a10 IS ABSOLUTE STEERING ANGLE, NOT AN ANGLE-TRACKING ERROR -- 2026-08-09. V84's b4
#   rung is reproduced by the pure predicate |steering angle| >= 0.85 deg at 99.94%, the step sits on the
#   threshold's own numeric value, and the relation holds in the MANUAL arm where a tracking error is not
#   even defined. ⇒ the 13-point LERP 0xC6B66/0xC6B80 in FUN_0003b8f6 is DEAD as a shaped lever: 88.6%
#   of engaged driving sits in its flat first segment, so it delivers a near-constant 0.878x BROADBAND
#   trim. 🛑 This REFUTES "FactorD is the only frequency-selective lever in this firmware" -- THIS
#   FIRMWARE HAS NONE -- which also removes the argument that FactorE cannot do what FactorD can. Reference rate R_OP = 99 counts =
# 21.0 deg/s (in-burst p50 for grind #1). SPEED_CTS_PER_KMH = 64.0625 (== COUNTS_PER_KMH above);
# RATE_CTS_PER_DEGS = 4.7121 (== gp-0x6ac0's scale, cited above). On the ramp segment, incremental gain
# k = ((C_Y0 * E_Y1) >> 10) / (E_X1 - E_X0), and dose(r) = k * (r - E_X0) exactly (r on [E_X0, E_X1]).
# Flown creep doses at r=99, all from the build scripts, not re-derived here: stock/V38 = 0 ·
# V74 (C_Y0=429, E_X0=12, E_X1=400, E_Y1=539) = 50, k=0.5799 · V75 (E_X0 carried at 12, EX1 dropped) =
# 137, k=1.5798 (this is the pair the slope fit above uses) · V76 (mode 26 only, C_Y0=566, E_X0=0
# (operator-authorised override of V74's own E_X0_MIN_SAFE=12 guard -- E_Y0 stays 0, so no torque at
# zero rate), E_X1=119, E_Y1=300) = 137, k=1.3866 -- same dose as V75 off a shallower ramp starting at
# zero. ✅ FLOWN 2026-08-07 (route 65, 636 s / 63,477 frames, clean) and IS in the slope fit above --
# it sits BETWEEN V74 and V75, so the monotone model made a falsifiable POINT prediction: grind #1
# observed 1.577 vs predicted 1.613 (held to 0.19 dB) => DOSE-LIMITED, slope -0.614 [-0.810, -0.416];
# ratchet observed 3.877 vs predicted 3.906 => DOSE-INDEPENDENT, slope -0.094 [-0.291, +0.098].
#
# ═══ V80 FLEW 2026-08-07 AND THE DAMPER SURFACE IS A RELAY. THE SINGLE MOST IMPORTANT DAMPER RESULT. ═══
# Route 66 (75604b0a432fdc89|00000066), 901.71 s / 89,997 frames, engaged 33.62%. Operator's verdict:
# THE WORST GRINDING THE CAR HAS EVER PRODUCED -- ~90% of engaged time, both low and high speed, with
# noticeable vehicle instability. 🛑 IT DID NOT FAULT (0x1AB DTC-active 0 transitions, 0.000% duty,
# 0 sentinels) ⇒ a STABILITY failure, not a fault-class failure. [EVIDENCE]
# k (small-signal loop gain, = ((C_Y0*E_Y1)>>10)/(E_X1-E_X0)):  V74 0.5799 · V76 1.3866 · V75 1.5798 ·
# V80 4.1597 (2.63x V75; V81 == V75's 1.5798 exactly, it does not touch the surface).
# Damper dose vs motor rate at 5 km/h, mode 26, from the shipped plain images (identical at EVERY speed
# on V80 -- its FactorC is flat):
#   rate ct     20   40   99  119  150  255  530 1000 1941 4000     (4.7121 ct per deg/s)
#   V75         12   44  137  169  218  297  297  297  297  512
#   V80         82  166  412  495  495  495  496  498  501  512
# ⇒ V80 emits a CONSTANT 495 counts -- 3.4% variation over a 34x rate range -- at 97% of the 512 ceiling,
#   above only ~25 deg/s. That is -sign(rate) x const: a Coulomb RELAY, not a viscous damper.
# 🛑🛑 WHY EVERY BUILD-TIME GATE WAS BLIND: they all test `product > ceiling`. V80's supremum is
#   (566*927)>>10 = 512 = the ceiling EXACTLY, so it clips 0.00% and passes. The relay was not removed by
#   the flat-FactorC edit, it was MOVED from the ceiling clamp to FactorE's OWN KNEE, 17 counts under the
#   rail (slope drops ~1200x at X[1]=119). "DOES NOT CLIP" AND "IS NOT A RELAY" ARE DIFFERENT
#   STATEMENTS, AND ONLY THE FIRST WAS EVER CHECKED. [EVIDENCE]
# Describing function N(R) of force = -sign(rate)*M(|rate|) (constant N = viscous = stabilising; N rising
# as amplitude falls = relay = limit-cycle generator), numerically integrated:
#   R ct         25     50     99    150    250    500   1000
#   V75 creep  0.580  1.065  1.319  1.410  1.317  0.734  0.375
#   V80 creep  4.007  4.087  4.127  3.698  2.421  1.250  0.632
#   relay-ness N(50)/N(500):  V75 1.45x (creep) / 1.43x (60 km/h);  V80 3.27x at BOTH.
# ★ MEASURED, by both builds' own cave probes -- the cleanest statement of the root cause:
#   |gp-0x6bd0| >= 448 counts, engaged:  V75 (route 5e, 28,317 pre-fault frames) 0.000%, never above 128
#   counts at all over 40 km/h;  V80 (route 66) 19.4% overall, 32.7% above 15 m/s, 71% through the worst
#   29 s event. V75's level census L0 56.8 / L1 25.3 / L2 9.3 / L3 8.6 / L4 0.000% ⇒ V75's damper never
#   entered its saturated regime; V80's LIVES there. [EVIDENCE]
# ★ WHAT V80 DID ON THE ROAD: a broadband HF FLOOR LIFT, not a new peak -- median engaged periodogram
#   V80-V76 is ~0 dB through 22 Hz and +8..+11 dB from 34 Hz up; cell-stratified 30-49 Hz 2.09x
#   [1.46, 2.70] with a pre-declared 32-38 Hz negative control failing identically (2.035). IMU vertical
#   20-49 Hz 1.07 [0.92, 1.33] ⇒ not a rougher road. FFT-free confirmation: engaged windows containing a
#   sample-to-sample reversal of |step| > 800 counts -- V75 0.0% · V74 0.5% · V76 0.6% · V80 23.3% --
#   exactly the near-Nyquist chatter a bang-bang relay injects.
# ★ AND A SUSTAINED ~27.4 Hz LIMIT CYCLE NO OTHER BUILD PRODUCES: 26-31 Hz envelope > 1000 counts in
#   32/215 engaged windows (V74 0/413, V76 0/328, V75 0/133); worst event ~30 s unbroken at 99-104 km/h,
#   27.56 Hz at x92 over the in-band median (manual x3.1 at the same speed), bar 6,830 counts p-p,
#   Q ~ 140, crest 1.838 (near-sinusoidal), damper >= 448 duty 71%, no fault and no lockout throughout.
#   NOT wheel order 2 (measured df/dv = -0.131 [-0.231, -0.016] Hz per m/s where order 2 needs +0.961);
#   frequency pinned across a 20x speed range while amplitude explodes with speed. ⚠ It is the kit's
#   own ~28 Hz line AMPLIFIED (~2.7x, f0 down 1-2 Hz), not a new mode. ⚠ fs ~ 100 Hz, so 27.34 Hz aliases
#   with 72.66/127.34 -- identical on all four routes, so it cannot affect the contrast.
# 🛑 MODELLING NOTE: k is a FREQUENCY-INDEPENDENT scalar on the whole damper path, so it is the loop gain
#   at every frequency -- no plant model is needed to compare two builds that differ only in k, and a
#   phase argument is only needed when a filter, delay or sample point moves.
#
# 🛑🛑 RETRACTION -- GRIND #1 IS INERT TO THE DAMPER DOSE (2026-08-07, four builds on ONE instrument,
# rlog-tools/studies/grind/compare_v75_v76_v80_grind.py, NFFT 256, p99 analytic band envelope, ~10.2 s bootstrap blocks
# nested inside engagement runs; ratio to V76):
#   band            V74 k=0.58        V76 k=1.39   V75 k=1.58        V80 k=4.16
#   18-22 grind #1  1.166 [.98,1.41]  1.000 ref    0.735 [.50,1.22]  0.835 [0.64,1.07]
#   6-9 ratchet     0.818 [.70,1.09]  1.000 ref    0.821 [.66,1.09]  0.418 [0.33,0.61]
#   40-49 grind #2  0.810 [.70,0.97]  1.000 ref    0.961 [.77,1.24]  2.017 [1.32,2.83]
#   30-49 HF floor  0.820 [.73,1.01]  1.000 ref    0.953 [.81,1.26]  2.091 [1.46,2.70]
#   32-38 neg ctrl  0.865 [.76,1.03]  1.000 ref    0.959 [.82,1.22]  2.035 [1.45,2.57]
# Split-half null for 18-22 Hz is [0.63, 1.60]: EVERY grind-#1 point lies inside its own noise floor over
# k = 0.58 -> 4.16. ⇒ V80 did NOT "overshoot an optimum" on grind #1; grind #1 never responded to k at
# all, and V75-vs-V76's apparent difference is a creep-EXPOSURE difference (V76's creep windows carry
# 3.4x V75's steering effort). ★ The operationally useful statement: k in [1.39, 1.58] buys most of the
# ratchet benefit at ZERO HF cost, and something switches on between 1.58 and 4.16 that costs 2x
# broadband HF plus a limit cycle -- WHERE in that gap it switches on is UNMEASURED. The micro-ratchet is
# the one band that improves with k and is best at V80's dose (0.418), consistent with the older
# "the ratchet needs k = 4.2-13.5" estimate.
# ⚠ DO NOT READ V80's CREEP NUMBERS: its engaged creep windows have median sustained effort 173 counts
# and |angle rate| 1.3 deg/s against V74/V76/V75's 685/588/1113 and 33/33/48 -- ZERO matched cells. The
# 10-40 and 40-80 km/h strata are well matched and carry the load; >80 km/h is 1 engagement run on V80
# and never reached on V75.
#     FUN_00036c12 -> gp-0x6b26   speed-LERP x gp-0x6c2c motor ACCELERATION, LINEAR [friction comp]
#         🛑 gp-0x6c2c is ACCELERATION (two cascaded IIRs on the one-cycle delta of the filtered rate,
#         FUN_00041464), so this lane is ~0 under steady motion and fires only on oscillation.
#         🛑🛑 THE 2026-08-11 "PURE INERTIA" CONSEQUENCE IS REFUTED BY THE V94 FLIGHT (2026-08-12).
#         It read: "an acceleration term is 90 deg out of phase with velocity -- it STORES energy and
#         DISSIPATES NONE ... raising K RAISES APPARENT INERTIA ... It cannot damp anything." V93/V94
#         LOWERED the lane on that reasoning; on-car the operator judged V94 unsafe to drive and
#         stopped (motor accel 3-7x up above 9 Hz; 18-31 Hz coherence the corpus maximum).
#         MEASURED, two independent drives, omega-partialled vs a shuffled control: the DELIVERED lane
#         is +137 deg / +139 deg vs WHEEL rate at 6-9 Hz => |cos| = 0.73 => +518 / +565 counts of
#         POSITIVE Re(Z). IT IS A REAL 6-9 Hz DAMPER. The producer's identity (an acceleration) does
#         NOT determine the delivered lane's phase at the wheel: two EMA poles (0xC643C = 37>>7,
#         0xC40DC = 22>>6) plus the plant sit in between. A desk recomputation that got +75 deg /
#         "26 % dissipative" was ALSO wrong -- it phased the PRODUCER against MOTOR rate.
#         => RULE: measure the DELIVERED lane against WHEEL rate. Never price a lane from its
#         producer's transfer function. See memory/accord/builds/accord-v94-flew-and-the-lane-is-a-damper.md and
#         memory/accord/signals/accord-gp6b26-is-a-real-6to9hz-damper.md.
#         ⊕ Direction is now MEASURED and it is UP, not down. But UP has been tried 13 times without
#         fixing anything, AND the 427 instrument cannot see its own dose: gp-0x6b26 = K*alpha where
#         alpha is what K damps, so in a stable closed loop the PRODUCT IS INVARIANT TO K (V91/V92's
#         x1.5 measured 0.99). Measure the INPUT (gp-0x6c2c) or a symptom -- never the product.
#         ⊕ x1.5 is already ~94 % of the lever's entire range (int32 wraparound at 1.6005x), so
#         0xCBE74 is EXHAUSTED as a lever in the UP direction.
#         🛑 THE GAIN HAS THREE SOURCES, and only one is the per-mode record (0x36C1E..0x36CB4):
#             gp-0x671a >= 0xFF or gp-0x67f4 != 1  -> flat cal(0xC640C) = -3277   [FALLBACK-1]
#             gp-0x671a >= cal(0xC64FD) = 5        -> flat cal(0xC640A) = -8192   [FALLBACK-2]
#             else                                 -> LERP(0xCBE74[mode]) over gp-0x6a5e
#         Both fallbacks are MODE-INDEPENDENT, so a build that writes only the records can be bypassed
#         entirely. Both were stock-virgin until V93/V94. gp-0x67f4 is the vehicle-speed VALID/SETTLED
#         flag (FUN_00041eec: set once any wheel source is valid and the vote settles, cleared only
#         when ALL sources go invalid) => it is 1 in normal driving, so neither fallback should fire.
#     FUN_0003a382 -> gp-0x6ad4   UNFILTERED residual lane (2 passthroughs + a raw derivative)
#     FUN_00036388 -> gp-0x6b62   slow +/-1/tick accumulator w/ hysteresis       [return-to-centre]
#     FUN_000352b4 -> gp-0x6b86 + gp-0x69a4                                      [friction magnitude]
#     inline r24   <- gp-0x4f62 x generated Q10 gain                              [VERIFIED torque-rate]
#     inline r26   <- gp-0x4f62 x avg(gp-0x69a4) x generated Q10 gain             [VERIFIED torque-rate]
#     FUN_00036682 -> filtered Sensor-B term, final slow IIR (6/1024)              [role OPEN]
# Bracketed roles are [INFERRED] from structure; addresses/plumbing are [VERIFIED].
#
# ═══ THE HARD-FAULT MECHANISM: 0xC407E IS THE WHOLE STORY (Ghidra-confirmed 2026-08-07) ═══════════════
# 0xC407E = tp+0x507E (anchor 0xBF000+0x507E -- the off-by-0x1000 trap avoided).
#   MONITOR FUN_00036d74, from the 1 kHz task FUN_0002214a @0x2290A:
#       fVar3 = gp-0x6b26 * 0.0009765625;  if |fVar3| > *(float*)(tp+0x5004) -> FUN_000462e6(0x39bc,..)
#       -> FUN_00016de6(0x1d,..) = DTC 0x1d, LATCHED TOTAL LOSS OF ASSIST.
#   0xC4004 bytes 0000003f = f32 0.5 ⇒ trips at 512 counts. Symmetric, NO debounce. The caller's
#   gp-0x67fa in {4,5,11} gate is the SAME gate that wraps the producer's call ⇒ unconditional
#   RELATIVE TO THE PRODUCER: no path writes gp-0x6b26 without the monitor checking it that cycle.
#   SOLE WRITER of gp-0x6b26: st.h r6,-0x6b26[gp] @0x36CF0 in FUN_00036c12 -- exactly ONE writer
#   image-wide (Ghidra + a raw Python LE scan of disp16, the 6-byte disp23 form, LE32 address literals
#   and movhi/movea pairs: 0 hits on all three alternatives). The stored value is ALREADY clamped to
#   +-0xC407E (clamp arms 0x36CCC-0x36CE2). 0xC407E itself: 0 writers, 3 readers, all ld.h SIGNED, all
#   three INSIDE FUN_00036c12 ⇒ the cell's entire blast radius is one lane's clamp magnitude.
#   MARGINS: stock/V38/V76/V78/V79/V80/V81 = 511 ⇒ +1, UNTRIPPABLE BY CONSTRUCTION (the only value that
#   can reach the cell is already clamped below the trip, whatever the plant or mode does).
#   V73/V74/V75 = 850 ⇒ -338, TRIPPABLE. [EVIDENCE] 🛑 0xC407E is a DO-NOT-RAISE cell.
#   ⚠ The ×1.5 friction table was introduced by V73, NOT V74 (verified across the lineage:
#   stock/V70/V71c/V72 carry Honda's row; V73/V74/V75 carry ×1.5, and V73 also raised 0xC407E).
# 🛑 AND 0xC63A0 IS EXONERATED. The standing directive "do not double 0xC63A0, that is what was causing
#   hard faults" rests on a FALSE PREMISE. 0xC63A0 = tp+0x73A0 has exactly ONE reader (ld.hu @0x381AC),
#   0 writers, 0 disp23 hits; its reader FUN_00038148 writes exactly two cells -- gp-0x374c (its own
#   accumulator) and gp-0x6b70 (its output) -- and NEVER gp-0x6b26, gp-0x6c2c or gp-0x6a5e. gp-0x6c2c's
#   two writers are both inside FUN_00041464 (0x4184E, 0x41AC2). NO FIRMWARE DATA PATH from 0xC63A0 to
#   the faulting monitor. A physical path exists (aggregator -> motor -> plant -> motor rate ->
#   gp-0x6c2c) and is IRRELEVANT, because the clamp acts BEFORE the store. [EVIDENCE]
#   ⇒ Keep the two questions apart: 0xC63A0 DOES move delivered torque (Path 2, above) and CANNOT move
#   what any monitor compares. Raising it is a GATE 2 loop-gain question, not a fault question.
# ★ V75's FAULT WAS NOT THE DAMPER: in the last 5 s the damper was identically ZERO for 4.98 s and
#   reached only level 2 (128-288) 19 ms before the trip. The car was stationary T-5..T-1 s then launched
#   (0 -> 7.6 km/h); column rate reversed sign twice in the final 150 ms (+55, +31, -38 deg/s) and PEAK
#   JERK hit 7,154 deg/s^2 = 4.3x that route's own p99.9 and the route maximum -- exactly what the
#   0xC407E mechanism predicts. [EVIDENCE] ⚠ "0xC407E=850 caused BOTH faults" is still [BELIEF]: the DTC
#   number was never confirmed on-car. EVIDENCE is that the mechanism exists, is single-frame, is
#   mode-proof, and the build history lines up exactly.
#
# ★★★★ gp-0x6bd0 REACHES THE MOTOR TWO WAYS, AND ONLY ONE OF THEM DELIVERS THE DAMPING (2026-08-06).
#   PATH 1 = FUN_0003aa2c, the aggregator above: UNITY weight, ZERO phase -- this is the damping.
#   PATH 2 = FUN_00038148 stage 1: six gated terms, plain ADD, each (x * gate * w) >> 10, with weights
#     tp+0x73a0/a2/a4/a6/a8/aa == 0xC63A0/A2/A4/A6/A8/AA.
#   The gates are ZEROING, not clamping (out of window contributes 0); gp-0x6bd0's is |x| <= 2048.
# ★★★★★ THE SIX WEIGHTS, AND WHY NONE OF THEM CAN BE MOVED YET (2026-08-12, GhidraMCP + Python).
#   Gate widths from a fresh decompile -- with all six weights at 1024 a lane's contribution to sum6
#   is (x*gate*1024)>>10 == x, so THE GATE WIDTH *IS* THE LANE'S REACHABLE CEILING:
#       gp-0x6b4c (0xC63AA) +-10240 | gp-0x6b4e (0xC63A8) +-10240      <- 5x and 10x the others
#       gp-0x6bd0 (0xC63A0) +-2048  | gp-0x6b46 (0xC63A4) +-1024
#   ⊕ gp-0x6b4e and gp-0x6b4c are DISJOINT PARTITION SUMS of the same 11-slot request array
#     gp-0x62f8[], split by the per-slot mode bytes at 0xC4124 (= 00 00 05 00 05 05 00 00 00 05 00):
#         gp-0x6b4e = clamp(sum of slots {2,4,5,9},        +-10240)   the mode-5 slots
#         gp-0x6b4c = clamp(sum of slots {0,1,3,6,7,8,10}, +-10240)   the mode-0 slots
#     i.e. the two halves of the EPS's own internal torque-request bus. Neither ever observed.
#   ⊕ gp-0x6b4c is ALSO a direct unity-weight aggregator summand (0x3AA3E, same +-10240 gate, in BOTH
#     branches) => it reaches the motor by Path 1 AND Path 2. gp-0x6b4e reaches only Path 2.
#   ⊕ Both producers are called from FUN_0002214a = the 1 kHz task, so the stage-1 IIR (a=102/1024,
#     fc ~= 16 Hz) passes 6-9 Hz at |H| ~= 0.90. At 100 Hz it would have been 0.21. Task 5's rate is
#     RETRACTED-OPEN, so this matters: these lanes CAN carry 6-9 Hz into gp-0x6b70.
#   ⊕ Both gates are STRUCTURALLY ALWAYS OPEN -- the producer (FUN_00026c80) clamps each cell to
#     exactly +-10240 and the FUN_00038148 gate passes -10240..+10240 INCLUSIVE => the V64-class
#     "gate never armed" null is EXCLUDED BY ARITHMETIC, not by a duty measurement.
# 🛑🛑 BUT NO WEIGHT MAY BE MOVED: gp-0x6b70 is a PID *REFERENCE* THAT GETS SUBTRACTED, not an
#   aggregator addend, so a weight change's SIGN is not determined by the forward path alone.
#   (a) The open-loop part IS determinate: gp-0x6b70 = sign(iVar6)*f(|iVar6|) is the odd continuation
#       of f, so the two sign(iVar6) factors in the chain rule SQUARE TO +1 AND CANCEL -- the unknown
#       sign of iVar6 does NOT matter open-loop. With 0xC64B0=1 and NO negation on this term in
#       FUN_00037fe6 (unlike the sibling gp-0x6b4a term, which IS negated), the open-loop sign is
#       +sign(gp-0x6b26) => it would REINFORCE Path 1, IF f' >= 0 (unconfirmed) and polarity is +1.
#   (b) 🛑 Path 2 IS A REAL CLOSED LOOP: gp-0x6b98[n-1] -> FUN_0003b8f6 -> gp-0x6bfc -> FUN_0003bc20
#       -> gp-0x6bfe, 1 kHz with one sample of delay. Its loop gain lives in EIGHT float coefficients
#       at tp+0x50d4/0x50d8/0x504c/0x5050/0x50bc/0x50d0/0x50d2/0x50d6 -- NEVER BYTE-READ BY ANY
#       SESSION -- crossed with the RAM LERP's local slope, which two attempts at FUN_000389ec have
#       failed to extract. => GATE 2 CANNOT BE CERTIFIED. 0xC63A6 was struck on exactly this.
#   ⊕ The +-1024 gate on gp-0x6b26 is evaluated on the RAW pre-weight value, so a weight change cannot
#     interact with it -- no gate-based clip risk, only unmeasured downstream headroom to +-8192.
#   ⊕ RULE 7 is satisfied for these weights: they are FLAT, non-mode-indexed scalars. And note
#     FUN_00038148's caller gate (uVar2 & 0x830) is a gp-0x67fa STATE gate, NOT a gp+0x63fd MODE gate.
#   => memory/accord/firmware/accord-fun38148-weights-have-an-unresolved-sign.md
# ★★★★★ THE LKAS AUTHORITY COLLAPSE CURVE -- VIRGIN, AND THE OPERATOR DRIVES ON ITS KNEE (2026-08-12).
#   Mode index gp-0x674e = 7 (single writer st.b @0x4272A <- variant table 0xCD000, stride 0x24, col
#   +0x08; car is row 11, forced by V73's on-car probe). Records at mode 7:
#       0xE547C / 0xE5404  primary (sign>=0 / sign<0)  X = 70, 72, 78, 80   Y = 254, 234, 12, 0
#       0xE52FC / 0xE5284  blend   (sign>=0 / sign<0)  X = 32, 42, 80, 112  Y = 255, 255, 255, 0
#   Authority goes 254 -> 0 between RAW TORQUE 2240 and 2560. All four VIRGIN on all 90 images.
#   🛑 The measured MEDIAN OVERRIDE TORQUE is 2235 = byte 69, ONE COUNT below X[0] = 70.
#   ⊕ 0xC64B8 (V37, 112 -> 0xFF) gates a hard authority kill at byte >= 113, but at mode 7 BOTH arms
#     deliver 0 there => stock and V37 are BIT-IDENTICAL on this car. The gate is DEAD; the CURVE is
#     the live mechanism. (Modes 28-39 have Y[last]=51, so this is a property of mode 7, not the code.)
#   🛑 NOT a 6-9 Hz lever -- refuted five ways; it drives the ~0.5-1 Hz SURGE.
#   🛑🛑 Honda collapses authority BECAUSE the driver is pushing. Any change must be MONOTONE-
#     NON-INCREASING: never more authority than stock at any torque.
#   => memory/accord/calibration/accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee.md
#   Stage 1's sum is then x polarity x tp+0x7468 (0xC6468 = 2639) >> 10, then a 1 kHz IIR with
#   tp+0x73ac (0xC63AC = 102) => corner 16.70 Hz, then stage 2 -> gp-0x6b70 -> FUN_00037fe6 ->
#   gp-0x6ad6 -> FUN_0003a382 -> gp-0x6ad4 -> the aggregator.
# 🛑🛑 THREE CORRECTIONS TO THIS CHAIN, 2026-08-07 -- the line above USED to end "-> gp-0x6b98":
#   (a) THE AGGREGATOR DOES NOT FEED gp-0x6b98. FUN_0003aa2c's sum output is gp-0x6b94 (+shadow
#       gp-0x4ce0). FUN_00042af8 -- the governor that actually WRITES gp-0x6b98 -- never references
#       gp-0x6b94 in its 1,424-line body; it runs on gp-0x6afe / gp-0x6b08 / gp-0x4f64. [EVIDENCE,
#       full decompile] => there is AT LEAST ONE UNRESOLVED HOP here. gp-0x6b94's 4 unchecked
#       readers: FUN_00036bec, FUN_0004503c, FUN_0004595a, FUN_0007ff08.  [OPEN]
#       🛑 STILL OPEN 2026-08-07, and NARROWED, not closed. New node: gp-0x6ace = the GOVERNOR-CLAMPED
#       form of gp-0x6b94 (written by FUN_0004503c via FUN_00049a90), and its ONLY readers are
#       FUN_000456a4 / FUN_00045a20 -- both HARD-SHUTDOWN MONITORS, not a forward path. Both of
#       FUN_00042af8's documented external inputs are now RULED OUT as the bridge: gp-0x6b08 is
#       self-referential, and gp-0x6afe's sole writer FUN_00042ac6 is fed by FUN_00026c80, an
#       independent Sensor-B lane that runs BEFORE FUN_0003aa2c in the same tick. ⇒ A MISSING LINK,
#       NOT A DISCOVERED INVERSION. Next: a raw LE scan for the 6-byte extended-disp encoding of
#       gp-0x6ace/6b94/6afe/6b08 (a disp16 scan is blind to it), plus a full decompile of
#       FUN_00042af8 -- its "no gp-0x6b94 reference" characterisation was inherited, never re-verified.
#   (b) FUN_0003a382 IS A GAIN-SCHEDULED PID -- the model's original wording was RIGHT.
#       🛑 A subagent claimed this round that "gp-0x6ad6 is a GATE input only, never a DATA input,
#       therefore 0xC63A0 changes delivered damping by 0.00 dB". THAT IS FALSE and was caught by the
#       orchestrator reading the decompile. gp-0x6ad6 appears THREE times in FUN_0003a382:
#         1. the entry gate    if (|gp-0x6ad6| > 0x6400 || |gp-0x4f60| > 0x6400) -> bVar1 = false
#                              (plus gp-0x2588/gp-0x2584 bit 27, and gp-0x6ac0 < 0x32c9);
#                              when bVar1 is false the function returns gp-0x6ad4 = 0 unconditionally.
#         2. uVar19 = (uint)*(short *)(gp - 0x6ad6)     <-- A DATA READ
#         3. its sign bit, for the symmetric-clamp comparison.
#       uVar19 is clamped to +/-(tp+0x7200) into uVar24, then  iVar30 = gp-0x4f60 - uVar24  forms the
#       ERROR, clamped to +/-0x2800 as iVar31, which drives three gain-scheduled lanes that sum into
#       gp-0x6ad4:
#         P: iVar14 = IIR((iVar31 * LERP_uVar20) >> 10 * 0x20, tp+0x7450)      state gp-0x367c
#         I: iVar18 = ((LERP_uVar16 * iVar31) >> 10) + gp-0x3688               state gp-0x3688
#         D: iVar29 = ((iVar31 - gp-0x3684) * LERP_uVar12) >> 10               state gp-0x3684
#       final: gp-0x6ad4 = (((I + D + P) >> 5) * LERP_uVar27) >> 10 * polarity gp-0x6752, then a
#       symmetric magnitude clamp against iVar10 (the feedforward term).
#       => gp-0x6ad6 IS the PID's FEEDBACK term. Path 2 therefore DOES reach gp-0x6ad4 proportionally,
#          and 0xC63A0's effect on delivered command is REAL, not 0.00 dB.
#       LERP index sources: gp-0x6ac0 (P/I/D gains), gp-0x671a, gp-0x6a5e, gp-0x6966, gp-0x6bda.
#   (c) FUN_00037fe6 is EXACTLY UNITY: all 7 term weights tp+0x74ad..0x74b3 read 1 in stock/V74/V77,
#       and the LERP(gp-0x69aa) table 0xC6ABA-0xC6AD8 is a constant 1024/1024 across its domain.
# 🛑 PATH 2 IS A CLOSED LOOP INSIDE THE FIRMWARE -- but it is a SUBTRACTION, not positive feedback.
#   The re-entry closes through gp-0x6bfc alone -> FUN_0003bc20 (0x3bc20 @0x22416, pure identity
#   passthrough) -> gp-0x6bfe -> FUN_00038148 @0x38218 reads iVar5 = gp-0x6bfe - (iVar4 >> 4), where
#   iVar4 is Path 2's OWN forward six-term sum. 0xC63A0 scales BOTH operands of that subtraction.
#   gp-0x6bf6 / gp-0x6c00 / gp-0x6ae0 / gp-0x6ae2 have ZERO readers anywhere -- write-only telemetry.
#   🛑🛑 CORRECTED 2026-08-09 -- this line used to read: "The 'B' input branch (gp-0x4f60) is DEAD
#   CODE in every build: its combine coefficients 0xC4048 / 0xC404C / 0xC4050 are all 0x0000."
#   THAT IS FALSE, AND THE ERROR IS A WIDTH TRAP. Those three cells are 32-bit FLOATS, not u16.
#   Orchestrator byte-read, stock AND V84, identical: 0xC4048..0xC4053 = 00 00 80 3f | 00 00 00 00 |
#   00 00 00 00  =>  c1 = 1.0f, c2 = 0.0f, c0 = 0.0f.  A u16 read of a float 1.0 returns 0x0000,
#   which is where "all zero => dead" came from. [EVIDENCE]
#   ⇒ THE STRUCTURE IS  y[n] = c1*x[n] + c2*x[n-1] + c0*x[n-2]  -- a 3-tap FIR (2 zeros, 0 poles;
#   no feedback path exists, so it can never ring, whatever the coefficients) sitting at an IDENTITY
#   PASS-THROUGH of the torque sensor. The branch is LIVE, not dead.
#   ⇒ CONSEQUENCE: gp-0x6bfc IS SENSOR-DERIVED, so FUN_0003b8f6 is a genuine command-vs-measurement
#   disturbance observer, not a command-vs-command residual. This RESOLVES OPEN #1 of
#   docs/research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md in the affirmative and makes that doc's §2.1
#   ("no compensation, decoupling or cancellation term anywhere") INCOMPLETE -- one exists.
#   ⚠ SIZE IT BEFORE BELIEVING IT: at DC the command branch outweighs the sensor branch ~27-32:1
#   per equal-magnitude count (cmd x 1/1024 vs sens x (1159/32768) x (1/1024) x LERP 0.878-1.059),
#   so the observer is command-dominated and the sensor content is a minority contributor.
#   ⚠ The sibling FIR at 0xC4018 / 0xC401C / 0xC4020 is byte-identical (also c1 = 1.0f).
#   builds/v50_v79/build_v58_tva.py's phrase "dead AS A LEVER" was correct (0 poles => unusable as a notch) and is
#   the likely source of the conflation with "outputs zero". Do not repeat it.
#
# ★★★★★ FUN_0003b8f6 @0x3b8f6 -- THE PLANT-MODEL OBSERVER. Added 2026-08-09; it was absent from this
#   model and from every handoff, despite being called at 1 kHz (sole caller FUN_0002214a @0x2240e,
#   immediately before FUN_0003bc20 @0x22416). Orchestrator-verified at the decompile level.
#
#   ENABLE GATE (all must hold, else the function writes the 0x7FFF INVALID SENTINEL and the whole
#   lane drops out):
#       |gp-0x6b98| <= 0x2000 (8192)   <-- the DELIVERED MOTOR COMMAND.
#         🛑🛑 CORRECTED 2026-08-10: THIS GATE IS A TAUTOLOGY AND CAN NEVER TRIP. The old note here
#         ("A COMMAND-CONDITIONAL DISCONTINUITY: under strong command Path 2 goes invalid") is FALSE
#         and was load-bearing for two dead hypotheses. The producer clamps gp-0x6b98 to EXACTLY
#         +-0x2000 four instructions before the store (0x43b0e-0x43b20 `cmovle r6,r14,r21`, then
#         `st.h r8,-0x6b98,gp` @0x43b52), and the test `x + 0x2000U < 0x4001` is inclusive at both
#         rails (8192+8192 = 16384 < 16385) => AT THE RAIL THE GATE PASSES. Census agreed two ways:
#         GhidraMCP 45 hits; raw LE scan of BOTH encodings 33+12 = 45. Only the two limp-mode writers
#         (0x6e104/0x6e1dc) could ever exceed, inherited max 5325 < 8192 [BELIEF, not re-derived].
#         ⊕ Same Honda idiom one hop down: FUN_00038148's sentinel |gp-0x6bfe| <= 20000 against a
#         producer clamped to exactly +-20000. Sentinel bound == producer clamp, both unreachable.
#       |gp-0x4f60| <= 0x6400 (25600)  ·  |gp-0x6abc| <= 13000  ·  gp-0x6752 in {-1,0,1}
#
#   model    = EMA2(gp-0x6b98 * polarity / 1024, a = 0xC40D4 = 573/4096)              # command branch
#            + clamp(FIR(EMA2(gp-0x4f60/1024, a = 0xC40D8 = 3686/4096) * 0xC613A/32768), +-15)
#              * LERP(gp-0x6a10, X 0xC6B66 / Y 0xC6B80) / 1024                        # sensor branch
#   iVar20   = polarity * gp-0x6abc * 12                                       @0x3bab0
#   ratio    = clamp(iVar20 / cal(0xC40BC), +-1.0)                             @0x3bab4  <-- RELAY
#   FRICTION = clamp(EMA(|model| * ratio * 0xC40D2/1024 + 0xC4080/1024 * ratio,
#                        a = 0xC40D0 = 408/4096), +-10)          -> gp-0x6ae2 = FRICTION * 1024
#   INERTIA  = clamp(EMA2(d/dt(iVar20) * 0.5 * 17.453293, a = 0xC40D6 = 246/4096)
#                    * 0xC646E * 2^-24, +-10)                    -> gp-0x6ae0 = INERTIA  * 1024
#   gp-0x6bfc = clamp(0xC6468(=2639) * (model - FRICTION - INERTIA), +-20000)
#               🛑 0xC6468 is a RAW FLOAT MULTIPLIER here but Q10 (>>10) in FUN_00038148's stage-1
#               sum. SAME CAL CELL, TWO SCALING CONVENTIONS. Using the wrong one is a 1024x error.
#
#   🛑🛑 `ratio` IS A COULOMB RELAY, NOT A PROPORTIONAL GAIN. It saturates at |gp-0x6abc| = cal/12
#   = 600/12 = 50 counts, against this function's own enable gate of 13000 => it is pinned at +-1
#   across 99.62% of its valid input range, i.e. it is sign(motor rate). Describing-function relay
#   index N(50)/N(500): 7.87 at the shipped 600. For scale: Honda's viscous damper 1.00, V75 1.45,
#   and V80's bang-bang damper -- the build that produced the WORST GRINDING IN THIS KIT'S HISTORY --
#   3.27. And FRICTION's magnitude is proportional to |model|, i.e. TO THE DELIVERED COMMAND, which
#   makes it engagement-scaled with no engagement flag anywhere. [EVIDENCE]
#   Reproduce: analysis-2020accord/studies/models/fun3b8f6_friction_relay.py
#   ⚠ INERTIA is NOT inertia compensation as delivered: its real part stays positive vs RATE across
#   7.79-28.5 Hz (+14.7 deg at 7.79, -36.2 at 21.09, -45.6 at 27.4) => a LAGGED VELOCITY DAMPER. It
#   runs at ~1-6% of its +-10 clamp, so it is not a relay.
#   ⚠ 0xC40BC / 0xC40D0 / 0xC40D2 / 0xC4080 / 0xC40D4 / 0xC40D6 / 0xC40D8 / 0xC646E are byte-identical
#   on STOCK / V38 / V67 / V81 / V84 and appear in ZERO of the 84 build scripts. 0xC40BC has EXACTLY
#   1 reader (ld.hu 0x50BC[tp],r16 @0x3BAB4) and 0 writers image-wide -- confirmed two ways, GhidraMCP
#   plus a raw LE byte scan of both encodings. 🛑 NOTE THE ENCODING: the halfword on the instruction
#   is 0x50BD (the disp|1 form); a scan for 0x50BC finds NOTHING.
#   ⊕ gp-0x6bf6 / gp-0x6c00 / gp-0x6ae0 / gp-0x6ae2 are 1-writer / 0-reader => FREE, BLAST-RADIUS-ZERO
#   TELEMETRY TAPS (gp-0x6ae0/6ae2 are written on the success path only and hold STALE values when the
#   gate fails, so they are only interpretable alongside a gate rung).
#   The re-entry is NOT a bare z^-1 -- the 2-pole LPF (0xC40D4 = 573/4096) gives:
#       7.79 Hz: -0.87 dB, -36.06 deg   |   21.09 Hz: -4.96 dB, -82.84 deg (incl. 1-tick transport)
#   vs Path 2's own iVar4 IIR: -0.85 dB/-23.63 deg and -4.13 dB/-47.90 deg.
#   => the two operands sit ~12 deg apart at 7.79 Hz but ~35 deg apart at 21 Hz, so they cancel best
#      at low frequency and WORST near the resonance.
# ★ 0xC63A0 ACTS ON PATH 2 ONLY. Path 1 (gp-0x6bd0 unity-weighted straight into FUN_0003aa2c's sum,
#   unweighted and gate-only) is untouched by it. And gp-0x6ad4 is the ONLY thing this whole branch
#   feeds, so when bVar1 is off the entire Path-2 loop is DISCONNECTED from the motor command, not
#   merely attenuated. [OPEN] what sets gp-0x2588/gp-0x2584 bit 27 -- so whether bVar1 was off at
#   V74's fault is NOT established, and given the 2.5 s mode lag it plausibly was still ON.
# ★★ 0xC63A0 IS THE DAMPER'S PATH-2 WEIGHT: stock 1024, V72 set 2048, and NO build reverted it until V77
#   (V77/V77B -> 1024 = -6.02 dB, zero phase, zero cost to Path 1).
#   It is MODE-PROOF -- a bare tp scalar reached without an index -- so it is live in MANUAL as well as
#   ENGAGED (RULE 7), and it has 1 reader (0x381AC), 0 writers, no monitor and no float mirror.
#   It is the odd one out of the six siblings (all stock 1024) and the only one any build ever moved.
#   ⚠ It was only FUNCTIONALLY ARMED AT V74: gp-0x6bd0 was 0 at creep on every build through V73 and
#   2 x 0 = 0, so V74 -- which opened both dead zones -- is the first build whose doubled weight carried
#   signal, and the first to hard-fault. [EVIDENCE: plumbing, byte lineage, arming | BELIEF: causal link]
#
# ★★★ 0xC63A0's BLAST RADIUS IS A STRICT SINGLE-FILE CHAIN (orchestrator, 2026-08-07, reg1==gp-validated
#   byte scan + decompiles). Every hop has exactly ONE functional consumer -- no branch, no telemetry tap:
#     0xC63A0        1 reader  0x381AC (FUN_00038148)
#     FUN_00038148   stores gp-0x6b70 (out) and gp-0x374c (its OWN IIR state; 2 refs, both internal)
#     gp-0x6b70      2 refs = the store + ONE read @0x38006 in FUN_00037fe6
#     FUN_00037fe6   1 store -> gp-0x6ad6      (7-lane sum; its byte weights 0xC64AD..0xC64B3 are ALL 1,
#                    and the tp+0x7aba LERP is flat 1024 => a UNITY-GAIN adder on stock)
#     gp-0x6ad6      2 real refs, BOTH inside FUN_0003a382 (the PID)
#     FUN_0003a382   1 store -> gp-0x6ad4
#     gp-0x6ad4      1 real ref @0x3ACA8 in FUN_0003aa2c (the aggregator)
#   ⚠ 3 raw byte hits discarded as FALSE POSITIVES: 0x767a8 / 0x767b2 land INSIDE 4-byte `mulf.s`
#   instructions (not on an instruction boundary), and 0xBCC52 / 0xBDF92 sit in data with no function.
#   => not even UDS telemetry reads this chain. ⚠ disp16 gp/tp only; extended-disp and ep-relative
#   forms were not swept image-wide (ep was refuted by decompile for FUN_00026c80/42af8/36682 only).
#   🛑 0xC63A0 scales ONE SUMMAND, not a signal: FUN_00038148 sums 6 weighted inputs and FUN_00037fe6
#   sums 7, so the friction / main-command / boost terms on the same wires are untouched by it.
#
# ★★★ FUN_0003a382 IS A REAL THREE-TERM CONTROLLER -- a TORQUE-TRACKING SERVO (decompiled 2026-08-07):
#     feedback = clamp(gp-0x6ad6, +/- tp+0x7200)          # Path 2 arrives HERE, as the FEEDBACK term
#     err      = clamp(gp-0x4f60 - feedback, +/- 0x2800)  # setpoint = driver torsion-bar torque
#     filtP: gp-0x367c += ((K_p*err*32) - gp-0x367c) * (tp+0x7450) >> 10      # first-order lag
#     integ: gp-0x3688 += (K_i*err) >> 10, CLAMPED into a window built from the authority limit (anti-windup)
#     deriv: gp-0x3684 holds err_prev; (err-err_prev)*K_d, clamp +/-0x2800, then low-passed into
#            gp-0x3680 with alpha = tp+0x744a                                # a DIRTY DERIVATIVE
#     out = ((D + I + P) >> 5) * LERP(gp-0x671a) * polarity(gp-0x6752), clamped to +/- authority
#     authority soft-starts via gp-0x3678 (up tp+0x744e / down tp+0x744c), scaled by LERP(gp-0x6966)
#     HARD GATE -> output 0 unless |gp-0x6ad6| <= 0x6400 AND |gp-0x4f60| <= 0x6400 AND gp-0x6ac0 < 0x32c9
#   🛑🛑 ALL THREE LANE GAINS ARE LERPs INDEXED ON gp-0x6ac0 (tables tp+0x7b1e / tp+0x7b0a / tp+0x7ade)
#   -- the SAME rectified motor rate that indexes FactorE. So a FactorE slope change and this PID's own
#   gain schedule move on ONE axis; they are NOT independent. That is the mechanism behind the recorded
#   +41.8..+55.0 deg phase lead at 21 Hz with |D| ~ |P|: at the grind frequency this loop is
#   derivative-dominated, exactly where a rate-scheduled gain on a RECTIFIED index (which sweeps at 2f)
#   interacts with the parametric pump. [GATE 2 -- size any FactorE edit against this, not just dose.]
#   ✅ RESOLVED 2026-08-07 -- THE DAMPER'S NET SIGN IS DISSIPATIVE AT gp-0x6b94, AND PATH 2 IS
#   NON-INVERTING. Was [OPEN] here for four sessions. The Stage-2 subtraction in FUN_00038148 and the
#   PID's own err = setpoint - feedback CANCEL, and the two polarity(gp-0x6752) multiplications cancel
#   whatever that value is: (-P)(+1)(-1)(+P) = P^2 = +1. FUN_00037fe6 is a genuine UNITY adder (all 7
#   weights tp+0x74ad..0x74b3 read 01). So Path 1 (bare, unity) and Path 2 (via the PID) both enter
#   FUN_0003aa2c with unity weight and REINFORCE -- they do not fight. Combined with
#   sign(gp-0x6bd0) = -sign(motor rate) above ⇒ DISSIPATIVE BY CONSTRUCTION at gp-0x6b94. [EVIDENCE]
#   ⚠ This was a sign result at gp-0x6b94, NOT at the motor. The 100 Hz zero-order hold still costs
#   37.6/75.2 deg of phase at 21 Hz on top.
#
#   ✅✅ RESOLVED 2026-08-08 -- THE gp-0x6b94 -> MOTOR HOP IS FOUND. Was [OPEN] for five sessions and
#   survived ELEVEN independent static methods returning the same wrong null. The bridge is two hops
#   past where every check stopped, and every hop is instruction-verified:
#
#     gp-0x6b94  (FUN_0003aa2c, 1 kHz: damper gp-0x6bd0 + friction + boost + r24/r26, clamp +/-0x2800)
#       -> FUN_0004503c  GOVERNOR, slew step 0xC6206 (512, <16.6 km/h) / 0xC6208 (205, >)  -> gp-0x6ace
#       -> FUN_000456a4  comp-add:  st.h r8,-0x6acc,gp @0x45932                            -> gp-0x6acc
#       -> FUN_00042af8  SHAPER: ld.h -0x6acc,gp @0x431C4 (bytes 244f3495), validity gate |x|<=0x2000,
#                        mode cal 0xC64C8 (=0 on stock and EVERY build => pass-through)
#                        st.h r11,-0x6b08,gp @0x43206 (bytes 645ff894)                     -> gp-0x6b08
#       -> Q15 blend (mux 0xC64C9=0, scale 0xC61DA=1092, integrator gp-0x3570)
#       -> ADD to gp-0x6afe -> clamp vs gp-0x4f64 -> hard clamp +/-0x2000                  -> gp-0x6b98
#       -> FUN_000757a2 (1 kHz) -> Iq_ref/Id_ref -> FOC PI+FF (4 kHz) -> SVPWM -> duty regs
#
#   ADDITIVE, SAME-SIGNED, NO SIGN FLIP. The delivered command is the CAN-arbitrated term PLUS a scaled
#   copy of the aggregator's governor-and-comp-added contribution. [EVIDENCE -- orchestrator byte-verified
#   the crux independently: predicted encodings 244f3495 / 645ff894 both MATCH.]
#
#   🛑 WHY ELEVEN METHODS MISSED IT: every one asked "does the shaper reference gp-0x6b94?" -- it does
#   not, and that is true. NOBODY ASKED ABOUT gp-0x6acc. And gp-0x6b08's "self-referential ramp state,
#   one writer inside the function itself" characterisation was individually true and collectively
#   misleading: it asked whether anything OUTSIDE reads it and stopped, never whether the function's own
#   next instructions consume it. They do, at 0x4320a.
#   📋 RULE: trace a FUNCTION'S OUTPUTS forward hop by hop. Do not enumerate one cell's readers and stop
#   when they look like monitors. A "monitor-only" output two hops from the motor is a red flag.
#
#   ⇒ EXPLAINS V40's brick mechanistically (0xFFFF removes the governor slew => gp-0x6ace snaps to
#   target => unbounded step into the SM2/SM3 integrator with a divergence monitor downstream), and the
#   graded V74->V81 damper dose-response (dose in, dose out, every cycle). The DTC-0x1d side-channel
#   hypothesis is SUPERSEDED, not merely abandoned.
#   🛑 0xC64C8 is a PURE BUILD-TIME CAL (0 runtime writers, 1 static reader @0x431CC): mode 1 DISCARDS
#   the entire aggregator contribution for a static cal tp+0x71d4; mode 2 blends it, clamp +/-0x3000.
#   UNTESTED, zero hits in any build script. Clean experimental control; equally dangerous.
#   ⚠ Not reduced to a single scalar: the aggregator-leg gain from gp-0x6b08 to gp-0x6b98 (near
#   0xC61DA/1024 = 1.066 x the integrator's settled ratio at nominal blend).
#   See memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md.
#
# ★★★★ THE PLANT-MODEL -> RESIDUAL -> ASSIST-AGGREGATOR CHAIN, END TO END (traced 2026-08-09).
#   Every hop below is instruction-anchored; the censuses are dual-encoding (disp16 + 6-byte extended).
#
#     FUN_0003b8f6 @0x3b8f6   1 kHz plant-model estimator (gate + arithmetic above)
#       gp-0x6bfc = clamp(0xC6468(=2639) * (model - FRICTION - INERTIA), +-20000)      st @0x3BC1A
#     FUN_0003bc20 @0x3bc20   plausibility |x| < 20000 -> gp-0x6bfe, status gp-0x695c (0x400 ok / 0xFFFF bad)
#     FUN_00038148 @0x38148   resid = gp-0x6bfe
#                                   - (EMA(SUM_6ch(x * w[0xC63A0..0xC63AA]), coeff 0xC63AC=102) >> 4)
#                                   + gp-0x6bfa
#                             gp-0x6b70 = clamp(SIGN(resid) * LERP_RAM(|resid| * 0xC63AE >> 10),
#                                               +-0xC6200=8192)                        st @0x382D2
#     FUN_00037fe6 @0x37fe6   ASSIST AGGREGATOR
#                             sum = -gp-0x6b4a + SUM(term * BYTE enable 0xC64AD..0xC64B3, all 0x01)
#                             gate: the six optional terms are summed whenever gp-0x67ab != 1
#                             gp-0x6ad6 = clamp(sum * speedLERP(gp-0x69aa)/1024, +-25600)  st @0x38142
#     -> FUN_0003a382 (PID; gp-0x6ad6 is its FEEDBACK/bias term) -> gp-0x6ad4 -> FUN_0003aa2c
#        -> governor -> gp-0x6acc bridge -> gp-0x6b98 -> FOC -> PWM
#
#   Censuses [EVIDENCE]: gp-0x6bfc 2 hits, gp-0x6bfe 2, gp-0x6b70 2, gp-0x6ad6 3, gp-0x67ab 3 (the
#   0x37FE6 hit is a genuine ld.bu -- the aggregator's entry read).
#   0xC64AD..0xC64B3 are 0/1 ENABLE FLAGS, not gains, and 0xC64B0 is the one gating gp-0x6b70.
#   The aggregator's speed LERP is flat 1024 across its domain.
#   ⚠ 0xC6200 has 15 readers; the governor cals 0xC6202/04/06/08 cluster disjointly at 0x045410-0x0457de,
#   so 0xC6200 is NOT governor-shared (confirmed twice; V40 wrote 0xFFFF to 0xC6206/0xC6208 and left
#   0xC6200 untouched). 3 of the 15 readers are still unidentified => the RULE 11 census is incomplete.
#   ⚠ Y[0] of the RAM LERP is UNRESOLVED: Y[0] = *(u16*)(gp-0x3714) via movea -0x3714,gp,ep @0x39508 +
#   sld.hu 0x0,ep,r11 @0x3950C -> st.h r11,-0x641c,gp @0x39522, inside FUN_000389ec. The only
#   ordinary-addressing access image-wide is a store-zero @0x38D22 -- a lead, not an answer; the block is
#   ep-relative and invisible to a displacement scan.
#
# ★★★★★ gp-0x6b98 MEASURED ON-CAR, 2026-08-09 -- V87's 427 probe, route 71. [EVIDENCE]
#   V87 repointed the 427 (0x1AB) TX packer's source load (0x55DF2 e893->6894), so MOTOR_TORQUE now
#   carries Honda's own clamp(|gp-0x6b98| * 5 >> 3, 0, 0x3FF) at 49.81 Hz: 1.6 counts/LSB, rail 1637.
#     engaged  median 208 counts, p90 966, railed (>=1637) 2.35%   [was ASSUMED ~120 counts p-p]
#     6-9 Hz ripple engaged  rms 29.0 counts, p-p 162   ⇒ the assumption was LOW BY 1.35x, not 5x.
#   THE FORK, on rectification-transparent unclipped engaged windows (white-noise p95 floor 10.5):
#     column torque 0x18F  6-9 Hz prominence 12.86 [5.73, 16.68], above floor in 50.0% of windows
#     DELIVERED gp-0x6b98                      4.03 [3.54,  6.22],                      7.1% = chance
#     openpilot 0x0E4                          2.96 [2.36,  4.01],                      7.1%
#   ⇒ the ~7.8 Hz mode is NOT a tone this chain commands. But the link is real and selective:
#     coherence(|gp-0x6b98|, column) = 0.439 at 7.79 Hz vs a SHUFFLED-PAIRS control of 0.178
#     (background 0.03-0.16, null 1/n = 0.071), and corr(column line, command line) = +0.62 per window.
#   ⇒ A LIGHTLY-DAMPED PLANT MODE DRIVEN BY BROADBAND COMMAND CONTENT. The lever class is "less
#     broadband HF in the delivered command", NOT a notch -- there is no tone in the command to notch.
#   ★ Engagement's effect on the delivered command, SPEED-MATCHED at 2-4 m/s (the raw ratio is void:
#     59% of manual frames are parked): 0.5-3 Hz 0.42x · 3-6 0.73x · 6-9 1.73x · 9-12 1.76x ·
#     12-15 1.79x · 15-22 Hz 3.37x (the ONLY row with disjoint CIs). Engagement REMOVES LF command
#     motion and ADDS HF, most of all in grind #1's band.
#   🛑 TWO INSTRUMENT LIMITS. (1) abs() is transparent only while the sign holds: 0 of 42 windows at
#     10.28 s, 14 of 37 at 5.14 s, so a 7.79 Hz oscillation about zero folds to 15.58 Hz. V88 adds
#     b7 = sign(gp-0x6b98) at 100 Hz (cave 0xC4B38 -> 6894) to close this. (2) 49.81 Hz sampling ⇒
#     NOTHING above ~15 Hz is claimable from 427; a 28 Hz object aliases to 21.8 Hz.
#   🛑 TWO READINGS RETRACTED BY THEIR CONTROLS: a "differentiator" op-cmd->delivered transfer rising
#     9x with f was exactly sqrt(Pyy/Pxx)/sqrt(n_avg), the ZERO-COHERENCE null, in all seven bands
#     (coh 0.035-0.077 vs a 0.043 null); and a phase-randomised surrogate PRESERVES |X(f)|, so it is
#     near-tautological as a "no line" control for a single-window periodogram.
#
# ★★★★★ THE FORK CLOSED, 2026-08-09 -- V88's SIGN bit, route 73. [EVIDENCE]
#   V88's cave b7 gives sign(gp-0x6b98) at 100 Hz, so the SIGNED delivered command was reconstructed and
#   V87's rectification screen DROPPED: 75 unclipped engaged windows vs V87's 14 screened.
#   Controls ran first: the sign bit flips at median |cmd| 36.8 counts = the 22.9th percentile (a noise
#   bit sits at the 50th); corr(0.2-3 Hz signed cmd, column) = -0.671 where the RECTIFIED magnitude
#   gives +0.030 -- rectification was destroying a real relationship.
#     column torque 0x18F  6-9 Hz prominence 11.17 [7.85, 16.30], above the p95 floor in 52.0%
#     SIGNED gp-0x6b98                        5.46 [5.12,  5.94],                          13.3%
#     rectified |gp-0x6b98| (V87's view)      5.62 [5.10,  6.80],                          12.0%
#   ⇒ SIGNED ~= RECTIFIED: rectification was NOT hiding a line, so V87's null was CORRECT. The worry
#     that 7.79 Hz folds to 15.58 Hz is dead. THE RATCHETING IS NOT A TONE THE EPS COMMANDS --
#     no notch, and no phase lever at 7.79 Hz. Reproduced at nw=256 and on the 100 Hz cave grid.
#   ★ AND THE GATE-2 HAZARD MOVED. Signed-cmd<->column coherence^2 vs a shuffled-pairs control of
#     0.009 [0.001, 0.061]:  2-4 Hz 0.038 · 6-9 0.123 · 9-12 0.090 · 12-18 0.133 · 18-24 Hz 0.310.
#     The loop is TIGHTEST in grind #1's band, not the ratchet's ⇒ any future filter's phase cost
#     lands at ~21 Hz. (At 7.79 Hz: coh^2 0.343, |tq/cmd| 6.24, phase -30.9 deg; the rectified channel
#     returns 0.009 = EXACTLY the control, so V87's 0.439-vs-0.178 was measured through a rectifier.)
#
# ★★★★★ LEVER B's MECHANISM, MEASURED -- V88 vs V87, single-variable, 5 changed bytes. [EVIDENCE]
#   Speed-matched 2-4 m/s, engaged, unclipped, episode-bootstrapped (orchestrator's independent crude
#   estimator in brackets):
#     0.5-3 Hz 1.192 [0.780, 1.812] NULL [1.121]  <- the peak effective LKAS command, UNTOUCHED
#     3-6 1.165 · 6-9 0.859 [0.720] · 9-12 0.604 [0.465, 0.943] · 15-22 Hz 0.549 [0.407, 0.844] [0.625]
#   Aliasing excluded on two 100 Hz channels: 15-22 Hz 0.33x/0.31x while 28-35 Hz is FLAT 1.13x/0.94x.
#   ⇒ MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING = LESS HF EVERYWHERE, at zero LF cost.
#   🛑 The orchestrator predicted the OPPOSITE (a 15-22 Hz RISE) by treating r24 as feedforward. It is
#     rate FEEDBACK inside the loop and gp-0x6b98 is the loop's OUTPUT. V87's engaged spectrum rising
#     with frequency (29/29/52 ct rms) against a FLAT manual arm (~9) is the signature of an
#     UNDER-DAMPED CLOSED LOOP at stock derivative gain, not of a feedforward differentiator.
#   ⊕ CO-MOVEMENT, not trade-off: within V88, corr(log 15-22 Hz cmd rms, log 6-9 Hz column prominence)
#     = +0.364 (+0.263 speed-partialled, block-permutation p = 0.016).
#   🛑 The cross-build 6-9 Hz comparison inherits route 71's [0.18, 5.51] split-half null ⇒ it CANNOT
#     RESOLVE a ratchet change under ~3-5x. "Unchanged" is not supported; "cannot resolve" is.
#
# ★★★ THE r24 LANE'S CLAMPS ARE IMMEDIATES, AND THE BUDGET IS SHARED. [EVIDENCE, disassembled 2026-08-09]
#   r24's own rail is FOUR 16-bit immediates, not a calibration -- contrast the deadband three
#   instructions earlier, which Honda DID make a cal (`ld.hu 0x71f6,tp`):
#       0x3ac42  addi  -0x2000,r6,r0     0x3ac46  movea  0x2000,r0,r24     0x3ac4a  bgt 0x3ac58
#       0x3ac4c  addi   0x2000,r6,r0     0x3ac50  movea -0x2000,r0,r10     0x3ac54  cmovle r10,r6,r24
#   ⇒ raising it is a 4-halfword IN-PLACE edit (the V42/V57/V87 safe class), NOT a cave.
#   🛑 BUT THE TEN-LANE AGGREGATOR SUM IS CLIPPED TO +-10240 IN THE SAME FUNCTION:
#       0x3acf6  movea  0x2800,r0,r12  -> 0x3acfa  st.h r12,-0x6b94,gp     (railed high)
#       0x3ad0e  movea -0x2800,r0,r12  -> 0x3ad12  st.h r12,-0x6b94,gp     (railed low)
#   ⇒ r24 ALONE is already allowed 8192 = 80% of the entire output budget. The +-8192 was never sized
#     against r24's own dynamics; it stops ONE derivative lane running away with the whole aggregator.
#   ⇒ the record lists the LKAS term gp-0x6b4c among the lanes in that same sum, so raising r24's rail
#     lets a derivative lane eat the headroom the LKAS command needs -- the one change in this path that
#     could REDUCE peak effective LKAS steering. ⚠ That last step is inherited, not freshly decompiled.
#   ⊕ Measured: gp-0x6b94 never comes within 20% of its own +-10240 clip.
#   ⊕ A clamp on a DERIVATIVE lane also bounds the response to an impulse (pothole, curb, sensor glitch);
#     V65's 123-839 counts is normal driving, which is not where a differentiator spikes.
#
# 🛑 INSTRUMENT DEFECT, kit-wide, found 2026-08-09: z["t"] == z["raw14_t"][1:] and
#   z["probe"] == z["raw14_b4"][1:] in ALL 13 caches (_scratch/cache/r5e.._cache_r73). extract() appends
#   raw14_* on every 0x14A frame but a ROW only after the first 0x18F. Pairing t with raw14_b4 reads
#   the cave byte ~10 ms early = 28 deg at 7.79 Hz. Safe pairs: (t, probe) or (raw14_t, raw14_b4).
#   Audit: analysis-2020accord/verify/audit_raw14_offbyone.py.
#
# 🛑 0xC646E (INERTIA gain, 1428) is FROZEN across ALL 21 images from V38 to V88 -- the best remaining
#   damping candidate has never been written, and its "1-6% of clamp" sizing is still an ESTIMATE.
#
# 🛑🛑 REFRAME 2026-08-09 -- FUN_0003b8f6's PATHOLOGY WAS *PARAMETRICALLY SWITCHED DAMPING*, NOT
#   "HARMONIC INJECTION". At cal(0xC40BC) = 600 the damping switched FULLY OFF on 87% of 6-9 Hz and 96%
#   of 18-22 Hz symptom frames. V85 (cal 6000) cut relay saturation 33.3% -> 4.6% engaged (7.21x) on
#   route 6e, hitting both pre-registered duty predictions. [EVIDENCE]
#   🛑 0xC40BC IS NOW FROZEN AT 6000, and the reason is NOT that N(A) is flat there: the single-input
#   describing function cannot settle it because the ring rides on a BIAS 5-10x its own amplitude
#   (|B| p50 35 / p90 228 counts vs ring amplitudes A p50 4-7). The BIASED DF reads top-decile pinning
#   at cal 6000 of 0.0000 (18-22 Hz) and 0.043 (6-9 Hz), after a delivered 20.3x reduction.
#   ⊕ The gp-0x6abc scale is confirmed independently two ways: 4.923 and 4.697 ct/(deg/s) bracket the
#   inherited 4.7121; reachable envelope +-1,930 counts.
#
# 🛑🛑🛑 THREE FLATTEN-A-CURVE-INTO-A-RELAY HAZARDS IN THIS CHAIN -- the V72/V80 error, one family over.
#   V80 is the recorded cost of making it once: the worst grinding in this car's history.
#     0xC4080 = 0    NEVER RAISE. FRICTION += cal/1024 * ratio has NO |model| factor => raising it arms a
#                    PURE COULOMB RELAY: amplitude-independent, unbounded in index.
#     0xC63AE = 1024 NEVER -> 0. The LERP index becomes identically 0 => output == +-Y[0], a constant =>
#                    a pure relay at full authority.
#     0xC6200 = 8192 NEVER LOWER. 🛑 CORRECTED 2026-08-10: the old wording "NEVER BELOW Y[0]" is
#                    VACUOUS -- Y[0] is 0 (st.h r0,-0x3714,gp @0x38D22, and the build loop starts at
#                    index 1, so index 0 is never rewritten). The real mechanism is the OTHER END:
#                    0xC6200 is read as tp+0x7200 inside FUN_000389ec's table-build loop and CAPS the
#                    Y entries as they are built (if (uVar51 < uVar57) Y[i] = 0xC6200). Lowering it
#                    caps several upper Y entries to the SAME value => flattens the top of the LERP
#                    into a plateau => a relay. Same V80 class, opposite end of the table.
#
# 🛑 gp-0x67fa's REACHABLE SET IS EFFECTIVELY {11} ALONE (measured 2026-08-09): state 5 structurally dead,
#   state 10 0.0000%, state 4 0/123,277 driving frames. => V42's 0x454FE is present on V85 (0xB5) and
#   MEASURED INERT -- keep the byte (lost silently three times, costs nothing) but never justify a build
#   on it. ⊕ gp-0x671a is RULED OUT as a lever axis: stuck at 0 across 1,158 reversals on V64.
#
# ★★★ THE ~7.79 Hz RATCHETING IS A LINEAR LOOP OSCILLATION, NOT A RELAY AND NOT A PLANT RESONANCE.
#   NOT a relay [EVIDENCE]: odd/even harmonic comb 0.858 [0.739, 1.000] against a positive control
#   reading 1.204 [1.147, 1.566] at just 15% injection; 3:1 phase-locking PLV z <= 1.05; switching-surface
#   time-locking -0.0375; a second method finds no third harmonic => <15% of the ~8 Hz bar content can be
#   relay-generated. NOT a plant resonance [EVIDENCE]: the wheel-on-torsion-bar mode is 12.8 Hz
#   [12.1, 13.6], ABOVE the ratchet, and 7.79 Hz is unreachable through the plant alone (12.65 Hz floor).
#   => [BELIEF, the only surviving hypothesis] a LINEAR loop oscillation whose frequency is set by
#   ACCUMULATED ESTIMATOR LAG. It fits every recorded property: sinusoidal, speed-invariant (slope
#   +0.074 / +0.049 / -0.004 Hz per m/s vs wheel-order-2's predicted +0.961), engaged-only, present in the
#   bar and in angle rate but NOT in openpilot's command.
#   ⇒ THE LEVER CLASS IS PHASE/LAG, NOT NONLINEARITY -- new since V38. V86 tests it with ONE cell:
#   0xC40D4 573 -> 286 (the command-branch EMA, alpha 0.1399 -> 0.0698), predicted to move the -180deg
#   crossing 7.79 -> 6.2-6.9 Hz, pre-registered as the RATIO f(V86)/f(V85) in [0.797, 0.875].
#   🛑 AN EMA CANNOT LIMIT MAX LKAS ANGLE RATE: |H(0)| = alpha / (1 - (1 - alpha)) = 1 EXACTLY for every
#   alpha (verified numerically at alpha in {0.0349 ... 0.9998} -> 1.000000000000). Only transient
#   tracking changes. 0xC40D4 is mode-proof: 573 appears exactly once in [0xC4000, 0xC4200) and no stride
#   S in [2, 0x400) repeats it.
# -----------------------------------------------------------------------------------------------------

# [VERIFIED, byte-dumped] mode-indexed assist tables, selector = byte at gp+0x63fd (0xFEDFE3FD, NOT the
# LKAS setpoint-limit mode gp-0x674e), range 0..33.
# 🛑 "gp+0x63fd = 10" AND "written only by factory/diagnostic paths (no CAN RX reaches it)" ARE BOTH
#   STALE -- CORRECTED 2026-08-05 and 2026-08-07. THIS CAR IS TVCA4: gp+0x63fd = 24 DISENGAGED /
#   26 ENGAGED, and the selector is REWRITTEN LIVE, every 100 Hz task-5 tick, by FUN_00042746 (sole
#   caller FUN_00022ca0), gated on (1 << (gp-0x67fa & 0xF)) & 0x30 == states {4,5}. It picks one of
#   four HW-ID column tables DAT_0000e012/13/14/15 via FUN_00057f8e(), selected by gp-0x67f6 in {0,1}
#   x gp-0x67e2 in {1,2}.  All five factor evaluators read it: 0x34470 / 0x34502 / 0x34592 / 0x34616
#   / 0x346b4.  [EVIDENCE, decompile + byte reads]
# ★★★★ THE MODE FALLS 26 -> 24 WITH A MULTI-SECOND LAG, AND THAT LAG IS LOAD-BEARING FOR SAFETY.
#   Measured on-car, two routes of V74 (61 and 5d): the engaged-column damper stays live for ~4 s
#   after openpilot drops lateral control, then is HARD ZERO -- 0 of 9,286 and 0 of 39,794 frames
#   beyond the band. V74's hard fault fired at 2.509 s past disengagement, i.e. STILL ON MODE 26.
#   => "disengaged" on the bus does NOT mean "mode 24 is active". Any argument of the form
#      "the operator was in manual, therefore the engaged-column edits were not in force" IS UNSOUND.
#      This exact inference produced a wrong EVIDENCE-marked conclusion on 2026-08-06.
#   [OPEN] the ROM mechanism for the multi-second hold. The only real debounce found is 0xC624E = 40
#   (=40 ms at 1 kHz; ~150 ms with the ramp-settle requirement) -- NOT 2.5 s. The candidate is the
#   gp-0x6733 == -1 "transitioning" sentinel written by FUN_000527da, which blocks the reselect from
#   even arming, but that function's callers resolve to null under both get_function_callers and
#   get_xrefs_to (register-indirect/RTOS dispatch). Closeable only with a live probe on gp+0x63fd
#   across a disengage event -- bytes alone will not get the number.
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

# [CONFIRMED] SPORT MODE is NOT implemented by this ECU: no writer of gp+0x63fd reads a CAN RX buffer.
# 🛑🛑 CORRECTED 2026-08-05 (full enumeration, disp16 + disp23 + UDS-indirect, cross-validated by
# independent Python byte scan against search_instructions -- both agree exactly): 3 REAL runtime/boot
# writers (not "sensor-fault failover", ENGAGEMENT-linked, matches V73's {8,10} probe):
#   FUN_00042692 (1 write) -- BOOT-TIME populator, gated `gp-0x6d78 & 8 != 0`; resolves the row via
#     FUN_00057f8e (HW-ID match) and copies column tp+0xE012. Was previously "never boot-populated in
#     any path found" -- that gap is now closed.
#   FUN_00042746 (4 writes) -- the RUNTIME re-selector. Picks one of 4 HW-ID-row columns (tp+0xE012/13/
#     14/15) keyed on two 2-state flags (gp-0x67f6, gp-0x67e2); those flags' own transitions are driven
#     by gp-0x6806 (== latActive, 99.983% per prior memory) and gp-0x69b0 (engagement gate) crossing
#     sentinels -0x8000/0. This is the engagement-edge writer V73's probe found; NOT a fault failover in
#     the ordinary sense, though gp-0x67e2's branch also depends on a consistency check vs cal tp+0x7182.
#   FUN_0004a798 (1 write, extended disp23 encoding) -- UDS WDBI, request-ID case 1; bench-only, folded
#     into the same gp+0x63e8..0x6427 config cluster as gp+0x6408 (see [[reference_accord_tva_hw_id_provenance]]).
# Plus a UDS RDBI reader (FUN_0004a8ca, register-indirect `mov 0xfedfe3fd,r6`) and a diagnostics packer
# (FUN_000508e8, 2 reads) that reports the raw byte as telemetry -- neither is a torque-path consumer.
# A160 = ID-table slot 2 "TVAA1" (gp-0x674e=1, gp+0x63fd=10 when engaged, =8 manual) via FUN_00057f8e's
# own-HW-ID match (the HW-ID itself is programmed at manufacture, not in code.bin).
# Every real TVAA* slot yields the same FALLING assist family and a flat-15360 setpoint record, so
# whatever tightens the wheel in Sport is not this firmware.
# 🛑 READERS (13 total distinct pointer arrays confirmed this session, up from 2 previously mapped):
#   already known: FUN_00034350's 5 damping factors (0xC9CCC/0xC9E9C/0xC9DB4/0xC9F84/0xC77A0, see above),
#   FUN_00036c12 friction (0xCBE74), FUN_0003ad74 r24/r26 speed-blend coefficient sets (LAB_000cbf5c/
#   c044/c12c + tp+0xd214, keyed 0/10/50/100 km/h breakpoints at tp+0x7010).
#   NEW: FUN_00034a72 boost (PTR_DAT_000ca324, scalar per-mode cal); FUN_000348e0 angle-tracking blend
#   (5 arrays, already the gp-0x6a10 "flat zero at creep" chain); FUN_00035154 (PTR_DAT_000c7888, speed
#   gp-0x6a62-keyed float LERP); FUN_000382d8 (LAB_000cc9fc/PTR_DAT_000c7b40, speed gp-0x6a64-keyed
#   selector, same shape as FUN_0003ad74); FUN_0003b338 (0xC8198), FUN_0003b416 (0xCA5DC, speed
#   gp-0x6a5e-keyed), FUN_0003b49a (0xCBCA4, feeds gp-0x6b28) -- roles of these last 3 NOT resolved this
#   session (index variables / downstream consumers open).
# ⇒ Engagement re-indexes damping, friction, boost, and both rate lanes simultaneously -- wide reach, but
#   FactorC's Y[0]=0 floor holds at BOTH mode 8 (X0=1280=20km/h) and mode 10 (X0=2240=35km/h), so the
#   "damping architecturally zero at 8 km/h" finding is UNCHANGED by which mode is active. Whether any of
#   the 7 NEW arrays differ meaningfully between mode 8/10 at low speed is OPEN -- not checked this session.
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
    lockstep-shadowed at gp-0x4cf0.

    🛑 SETTLED 2026-07-30, and this function has NOT yet been migrated: gp-0x6a5e/0x6a62/0x6a64 are a
    5-channel VOTED VEHICLE SPEED, not voted driver torque. Producer chain FUN_00053216 ->
    FUN_000534da -> FUN_00041eec (the voter, sole writer of all three), scale 64.0625 counts/km/h.
    Independently corroborated here by byte-reading this very curve: mode 10 = 0xD2834 has
    X = (0, 640, 2560, 5120, 7808, 10240) which divides to (0, 10.0, 40.0, 79.9, 121.9, 159.8) km/h --
    textbook speed breakpoints that no torque axis would produce. See the agent memory
    `reference_accord_gp6a5e_producer_chain_and_creep_zero_damping.md`.
    ✅ THE RENAME HAS LANDED (2026-08-03): `col_torque_avg` -> `speed_voted`, all 8 call sites in one
    contained pass, module re-imported and every self-check re-run. The identifier no longer asserts a
    role the cell does not have. `col_torque_rate` is a DIFFERENT cell (gp-0x4f62, Sensor-B torque
    finite difference) and was deliberately NOT touched.
    ⚠ STILL OPEN, and it is a MODELLING issue rather than a naming one: the producer below is still
    written as averaging torque-sensor *coils*. The averaging STRUCTURE is right -- FUN_00041eec
    averages the agreeing channels -- but the local names and surrounding prose still describe those
    channels as torque. Re-word against the voter's real 5-channel speed inputs. Separate contained
    pass; it changes no numeric result.

    ★ Load-bearing consequence already byte-verified (all 34 mode tables, _v59_plain_image.bin):
    damper FactorC (0xc9e9c[mode], mode 10 = 0xD27BC, X=(2240,3840,5120,8960) Y=(0,235,430,877)) has
    Y[0] == 0 in EVERY mode, with X0 = 20/30/35 km/h. It is multiplicative and the LERP clamps to Y0
    below X0, so BASE-ASSIST DAMPING IS EXACTLY ZERO BELOW 35 km/h on this car.
    ⚠ But V59 shows that is NOT what suppresses the ~21 Hz grinding: engaged hands-off, speed-stable
    windows (n=159) give mode prominence 1521x / 935x / 91x / 6.0x at 1-2 / 2-3 / 4-6 / 6-9.72 m/s --
    the mode and the pump are BOTH already dead at 6 m/s, BELOW the 9.71 m/s FactorC onset. Raising
    FactorC would buy a base-assist feel change for nothing. Lever NOT supported by the data.
    ⚠ Also refuted: the speed-keyed boost curve does not concentrate assist at creep. It is nearly
    flat -- relative gain 0.856 / 0.979 / 0.987 / 0.997 / 0.903 at 0.5 / 3 / 6 / 10 / 18 m/s.
    """
    mode = st.assist_mode                             # gp+0x63fd, range 0..33 (NOT 0..7)

    # --- validity gate ("bVar10"): ALL of these must hold or the lane collapses to the ramp-down path
    valid = (st.assist_substate in (1, 2)             # gp-0x67fe  EPS assist substate
             and st.plausibility_ok                    # gp-0x67f4 == 1, from the voter FUN_00041eec
             and st.speed_voted < ASSIST_SENTINEL   # gp-0x6a5e not invalid/saturated
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
    key_avg = min(abs(st.speed_voted), 0xFFFF)
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
    # 🛑 CORRECTED 2026-07-30 from the decompile of FUN_00034a72 + a byte-level shift/multiply scan.
    # The previous rendering ("both curves multiply the same assist term in series, >>14 twice") was
    # WRONG about the structure. The two curves enter at DIFFERENT points and are separated by a
    # subtraction and two clamps, so they compose multiplicatively only while none of those bind:
    #
    #   y1 @0xD28DC (via 0xCA4F4[mode]) -> blended -> * clamp(gp-0x6986, 0x400) >>14  @0x34C26
    #        -> * 0xCA40C[mode] >>7 -> ... -> DIFFERENCED against gp-0x6a56 -> clamp +-12000
    #   then * 0xCA324[mode] >>7 -> * boost curve 0xCA154[mode] (keyed on SPEED gp-0x6a5e)
    #        -> clamp(>>10, +-0xC7A58[mode])
    #   y4 @0xD2888 (via 0xCA23C[mode]) -> blended -> * clamp(gp-0x6988, 0x400) >>10
    #        -> * (the above) >>14  @0x35008 -> * polarity (mulh @0x35010) -> clamp +-ceiling
    #
    # ⚠ A subagent argued y1 is a DEAD END (only 3 image-wide refs to its state cell gp-0x69bc, all
    # in this function). That argument is INVALID: a byte scan of the STATE CELL cannot show whether
    # the blended value is consumed in a REGISTER in the same tick -- which is exactly what a
    # slew-limited gain does. Byte scan of FUN_00034a72 finds exactly two `>>14` sites:
    # `shr 0xe,r28` @0x34C26 (the y1 multiply, before the subagent's trace start of 0x34F20) and
    # `sar 0xe,r13` @0x35008 (y4). Both curves are live. gp-0x6986 / gp-0x6988 are DIFFERENT adjacent
    # cells, one clamped companion per LERP -- the symmetric two-lane structure.
    #
    # ★★ AND BOTH LERP OUTPUTS ARE SLEW-BLENDED BEFORE USE -- previously unmodelled entirely:
    #   y1: blended toward persisted gp-0x69bc, rate cal 0xCA06C[mode] -> 0xD2006 -> 102 (Q10)
    #   y4: blended toward persisted gp-0x69ba, rate cal tp+0xB06C[mode] (same table)   -> 102
    # Both lockstep-shadowed (gp-0x4c6e / gp-0x4c6c). A 1-pole blend at 102/1024 passes only ~0.37 of
    # 42 Hz, so it ATTENUATES the parametric pump measured by V59. ⚠ The blend sits inside an `if`
    # (guard ~0x34BF0) => it is an ASYMMETRIC slew, direction unresolved; simulating the literal
    # integer arithmetic at 1 kHz gives eps 0.016-0.034 at median hands-off amplitude, 0.085-0.161 at
    # p90, 0.132-0.255 at p99, against a Mathieu threshold of ~2/Q = 0.147. ⇒ the pump is
    # SUB-THRESHOLD at typical amplitude and crosses only in the loudest bursts: an amplitude-gated
    # bootstrap, which is what makes the grinding bursty rather than continuous.
    # ⚠ gp-0x6986 / gp-0x6988 values are UNMEASURED; eps is not final until they are dumped.
    # [STILL SIMPLIFIED] the model below keeps the flat series form for continuity. It is a
    # first-order stand-in, NOT the literal chain -- see the sequence above before using it.
    amp = boost_amplitude_index(st)
    y1 = _lerp_flat(amp, BOOST_AMP1_X, BOOST_AMP1_Y)      # 0xD28DC via 0xCA4F4, then blended
    y4 = _lerp_flat(amp, BOOST_AMP4_X, BOOST_AMP4_Y)      # 0xD2888 via 0xCA23C, then blended
    scaled = (int(st.assist_rate_state * ramp_scale) * y1) >> 14
    scaled = (scaled * y4) >> 14
    signed = scaled * st.assist_polarity                                   # gp-0x6752
    return _clamp(signed, -ceiling, ceiling)                               # -> gp-0x6bbe


# Blend/slew rate applied to BOTH amplitude-LERP outputs before they multiply anything.
# 0xCA06C[mode 10] -> 0xD2006, first u16 = 102 (Q10 = 0.0996). Byte-verified on _v59_plain_image.bin.
# ⚠ 0xD2000 is a SHARED overlapping block: [666,666,666, 102,102,102, 43,43,43, 32896,128, 0,5,0...]
#   0xC7A58[10] -> 0xD2000 reads 666 (output clamp) | 0xCA06C[10] -> 0xD2006 reads 102 (this blend)
#   0xCA324[10] -> 0xD200C reads 43 (gain scalar).  Do NOT edit one offset without resolving what
#   else reads the block -- that check is OPEN and gates any build on this lever.
BOOST_AMP_BLEND_Q10 = 102


# --- the boost AMPLITUDE index and its two curves -------------------------------------------------
# 🛑 gp-0x6ba6 == abs(gp-0x6b9a). FUN_0003b66a writes both from one r28: `cmp r0,r28 / mov r28,r13 /
# bge 0x3b886 / subr r0,r13` @0x3b874-87c, then st.h @0x3b892 (gp-0x6ba6) and @0x3b8b0 (gp-0x6b9a).
# Sole writer each, byte-scanned for both gp-relative encodings.
# gp-0x6b9a itself indexes NOTHING: its only live consumer is a 5-input plausibility gate
# (|x| <= 25600 @0x34c9c-cb4 -> r21 -> zeroes r24 @0x34fc8), so its SIGN has no output effect, and two
# of its three reads in FUN_00034a72 are dead (tp+0x7499 == 1 takes the branch @0x34b3c).
# ⇒ V58 measured the SIGNED sibling crossing zero at 20.93 Hz only when LKAS applies, so this index is
# that signal RECTIFIED -- a minimum at every zero crossing, sweeping both curves at ~2x the mode
# frequency on the BASE ASSIST path.
#
# ★★ V59 FLEW 2026-07-30 (route 2c) AND MEASURED THE DEPTH. The mechanism is LIVE, not weak.
# Thermometer probe on gp-0x6ba6, 50,963 frames, 100% live / 100% monotonic / fault sentinel 0.000%.
# Conditioned on engaged + creep + SUSTAINED hands-off (|lowpass(tq,3Hz)| <= 200), 50.2 s, n=5016:
#     depth   76.93% <512 | 18.46% 512-1k | 4.57% 1k-2k | 0.04% >=2048
#             (disengaged + creep + hands-off, n=6944: 99.83% <512 -- the index barely leaves the pin)
#     the index's OWN spectrum peaks at 42.19 Hz = 2 x the 21.09 Hz mode, prominence 11.10x,
#     coherence 0.795 vs the torsion bar (K=30, periodograms averaged across 13 DISJOINT runs, never
#     spliced). The 18-26 Hz band shows only 1.23x. That is the full-wave-rectification signature.
#     Disengaged: bit5 NEVER toggles -- 0/4 runs, 61.2 s, K=90, prominence 0.00x. Pump absent.
# ⇒ a parametric gain pump at 2f into a mode at f. Depth epsilon = (1-g)/(1+g) from the swept range:
#     index 0..512 -> 0.162 | 0..1024 (p95) -> 0.333 | 0..2048 -> 0.490   [SERIES, see the >>14 pair
#     below -- HALVE these if only one curve applies; that block is flagged non-literal]
# 🛑 CAUSALITY IS NOT SETTLED AND CANNOT BE FROM THIS DATA. The index is |x| of a bar-derived signal,
# so "pump tracks mode" is partly guaranteed by rectification: a mode dying for its own reasons quiets
# the bar, pins the index, and produces identical numbers. Only an INTERVENTION (flatten the swept
# range, re-fly) separates drive from echo.
# ⚠ Blast radius, byte-verified on _v59_plain_image.bin: 0xD28DC and 0xD2888 are each referenced
# EXACTLY ONCE image-wide (0xca51c and 0xca264, mode slot 10 of their own pointer tables); all 34
# slots in both tables are distinct targets. Editing them touches mode 10 only. GATE 1 is clean;
# GATE 2 is NOT -- both sit on the base-assist path and change manual feel.
BOOST_AMP1_X = (0, 512, 1490, 2529, 3645, 5120)     # 0xD28DC, byte-verified
BOOST_AMP1_Y = (16384, 14657, 11672, 9365, 8244, 8187)
BOOST_AMP4_X = (0, 307, 1024, 1741, 3072, 6144)     # 0xD2888, byte-verified
BOOST_AMP4_Y = (16384, 14392, 10265, 8997, 8176, 8176)

FAULT_SENTINEL_6BA6 = 0xFFFF    # FUN_0003b66a input-gate failure; > 25600 so r21 catches it
FAULT_SENTINEL_6B9A = 0x7FFF


def boost_amplitude_index(st: EpsState) -> int:
    """gp-0x6ba6, the index into both boost amplitude curves; the magnitude of gp-0x6b9a."""
    return abs(st.boost_fir_out)


# tp+0x7010 = 0xC6010, byte-read [0, 640, 3200, 6400] = 0 / 9.99 / 49.95 / 99.9 km/h at 64.0625
# counts/km/h. The key is gp-0x6a5e (VOTED VEHICLE SPEED -- see the rename note in
# base_driver_assist_lane), substituting cal tp+0x7314 when gp-0x67f4 != 1.
ASSIST_RATE_CROSS_X = (0, 640, 3200, 6400)

# ★ RESOLVED 2026-08-01 from the FUN_0003ad74 decompile + byte reads (orchestrator, first-hand).
# The two halves of FUN_0003ad74 are NOT symmetric, and the record had this wrong in two ways:
#
#   gain_B (r24)  -- MODE-INDEXED, through FOUR SEPARATE POINTER ARRAYS, each indexed by mode*4:
#         0xCBF5C   0xCC044   0xCC12C   tp+0xD214 = 0xCC214
#     For OUR CAR (gp+0x63fd == 10) they resolve to records 0xD2A74 / 0xD2AB0 / 0xD2AEC / 0xD2B28.
#     ⚠ These are NOT four consecutive records at a stride -- reading them as consecutive from
#     0xD2AEC lands on modes 10/11's interleaved rows and gives a nearly FLAT surface (2305->1948),
#     understating the real rolloff by 2x. Records are PRIVATE per mode (mode 11 -> 0xD2A88/...).
#     ⚠ builds/v50_v79/build_v62_tva.py's GAIN_B_LERP_MODE10 tripwire watches only 0xD2AEC and 0xD2B28, so it is
#     blind to an edit landing on 0xD2A74 or 0xD2AB0. Widen it before any cal work on this lane.
#     Output: runtime X row -> gp-0x6e40, runtime Y row -> gp-0x6e38 (read by r24 @0x3AB9C-0x3ABF8).
#
#   gain_A (r26)  -- NOT mode-indexed at all. Four FIXED records at tp+0x7a68/0x7a7c/0x7a90/0x7aa4
#     = 0xC6A68 / 0xC6A7C / 0xC6A90 / 0xC6AA4, hard-coded in the instruction stream.
#     Output: runtime X row -> gp-0x6e30, runtime Y row -> gp-0x6e28.
#     (Moot in practice -- r26 is structurally inert, see assist_slope_q10.)
#
# Y is Q10 (1024 == 1.0); every value below byte-verified in _v65_plain_image.bin.
ASSIST_RATE_B_RECORDS = (
    ((0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),   # 0xD2A74  <- 0xCBF5C[10], speed 0 km/h
    ((0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),   # 0xD2AB0  <- 0xCC044[10], speed 10 km/h
    ((0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),   # 0xD2AEC  <- 0xCC12C[10], speed 50 km/h
    ((0, 400, 1500, 3000), (2151, 2151, 2049, 1947)),   # 0xD2B28  <- 0xCC214[10], speed 100 km/h
)
# ⇒ THE SURFACE, which matters for any lever on this lane: at CREEP the gain is 3072 and FLAT out to
# motor rate 400 counts (~85 deg/s at 4.7121 counts per deg/s), then falls to 1536 at 3000 (~637
# deg/s) -- a genuine 2x rolloff. At road speed it flattens (0.80x at 32 km/h). So Honda ALREADY
# de-escalates this lane when the wheel is moving fast, and only at low speed. The commonly-quoted
# "r24 default arm = 2305" is the 50 km/h record; at the hands-off-creep operating point it is 3072.
#
# ★★★★ RESOLVED 2026-08-02, orchestrator-verified from the images and from route 47:
#
#   1. THE RATE AXIS IS USABLE -- the three symptom populations sit at DIFFERENT points on it:
#          grind #1            ~128 deg/s -> gp-0x6ac0 ~ 603    [400,1400] ON the rolloff
#          grind #2 creep      ~256       ->           ~1206    [400,1400] further along the rolloff
#          grind #2 highway   30-42       ->         ~141-198   [0,400]    FLAT (Y0 == Y1)
#      X1 = 400 = 0x0190 EXACTLY, and Y0 == Y1 in every curve EXCEPT mode-10's 50 km/h
#      record 0xD2AEC, which is Y0 = 2305 / Y1 = 2304 (byte-verified `01 09` then `00 09`) -- a +1
#      cal-tool rounding artifact, 0.04%, behaviourally nil, but an exact Y0 == Y1 equality test
#      WILL break on it. The [0,400] segment is flat to within 1 count at every speed.
#      GATE 2 caution on any rate-axis edit: gp-0x6ac0 is a RECTIFIED filtered motor rate, so it
#      sweeps at 2x the mode frequency and a steeply rate-dependent gain modulates at 2f (the
#      parametric-pump failure mode V58/V59/V60 chased). Stock ALREADY has a rolloff there, so the
#      mechanism is not new and is tolerable at stock slope; any edit that STEEPENS it must state the
#      new slope and argue the pump margin. Quantitative caution, not a structural veto.
#
#   2. UNITS -- SETTLED EMPIRICALLY, after the orchestrator got this WRONG once on 2026-08-02.
#      The 0x14A rate field IS deg/s (factor 1): regressing `rate_c` on the differentiated ANGLE
#      channel (0x14A b0:1, factor -0.1 => degrees) gives slope 0.95-1.00 with r >= 0.985 on every
#      clean segment. And gp-0x6ac0 = 4.71210813 counts per deg/s, so the inner breakpoints
#      [0, 400, 1400/1500, 3000] are [0, 85, 297, 637] DEG/S -- which real driving reaches (|rate|
#      over 407,617 frames peaks at 521 deg/s, p99.9 = 408), whereas the erroneous 0.589 counts per
#      deg/s would put them at 679/2377/5093 where Honda's 2x rolloff could never engage at all.
#      RETRACTED: "bus counts = 8 x deg/s" and "V67's arm delivers 1.94x". V67's build note was
#      CORRECT -- LERP 2622 at grind #1's operating point, arm 5244 = exactly 2.00x. The error was
#      composing two UNVERIFIED structural relations (gp-0x6ac0 = |gp-0x6abe|, and
#      bus = (gp-0x6abe*48*1159)>>15) into a scale instead of MEASURING it against a channel already
#      in the cache. One of those two premises is wrong; which one is OPEN.
#
#   3. V67's FLAT ARM INVERTS HONDA'S OWN SCHEDULE. Because the surface rolls off with speed, a scalar
#      arm delivers its LARGEST multiplier where the stock design wanted the LEAST:
#          grind #1  creep 7.2 km/h   LERP 2622 -> 2.00x
#          grind #2  creep 5 km/h     LERP 2409 -> 2.18x
#          highway   100+ km/h        LERP 2151 -> 2.44x   <- the maximum
#      🛑 A flat arm is STRUCTURALLY INCAPABLE of fixing the highway: one degree of freedom, two
#      constraints. 1.00x at highway needs arm 2151, which is 0.80x at grind #1 (WORSE than stock);
#      2.00x at grind #1 needs arm 5408, which is 2.51x at highway.
#      ⚠ AND THE PREDICTED HIGHWAY COST DID NOT MATERIALISE -- see openpilot_command_slew_invariance().
#
#   4. BLAST RADIUS IS CLEAN for a cal-only speed schedule (raise Y[0]/Y[1] in the 0 and 10 km/h
#      records only): EXACTLY ONE pointer image-wide per record (0xCBF84 / 0xCC06C / 0xCC154 /
#      0xCC23C, full 32-bit LE scan), all four in ONE CRC block (0xD2000, 0xD2FFC), and a full-image
#      32-bit float scan finds NO float mirror for any Y value and no clustered mirror table => the
#      V27 int/float desync class does not apply. Buildable and safe -- but NOT recommended, because
#      the highway dose response it would target does not exist in the data.
#      Arithmetic + the edit's exact bytes: analysis-2020accord/studies/sessions/v68/v68_design_math.py.
ASSIST_RATE_A_RECORDS = (
    ((0, 400, 1600, 3000), (3072, 3072, 2434, 2048)),   # 0xC6A68
    ((0, 250, 1200, 3000), (3072, 3072, 2488, 1536)),   # 0xC6A7C
    ((0, 400, 1250, 3000), (2664, 2664, 2243, 1436)),   # 0xC6A90
    ((0, 400, 1250, 3000), (2560, 2560, 2145, 1331)),   # 0xC6AA4
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
    avg_key = abs(st.speed_voted) if st.plausibility_ok else 5120
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


def detector_input_6c2c(rate_raw: int, ema_old: int, state_fast: int) -> tuple:
    """
    FUN_00041464 @0x4184E -- produces gp-0x6c2c, the ONLY input to the oscillation detector's threshold
    test. [VERIFIED 2026-07-31, cals byte-read LE.] ★ It is FILTERED MOTOR ACCELERATION off gp-0x4f50
    (the resolver/motor ELECTRICAL rate) -- TWO CASCADED IIRs on the ONE-CYCLE DELTA of the filtered
    rate -- NOT torque and NOT rate: differencing kills DC, so a sustained large steering input cannot
    drive it and it needs the motor rate actively reversing. ⇒ the friction lane FUN_00036c12 ->
    gp-0x6b26, whose magnitude term is this same signal, outputs ~0 UNDER STEADY MOTION and responds
    only to oscillation.
    Returns (gp_0x6c2c, ema_new, state_fast_new). A slower sibling gp-0x6c2e takes the same `acc` through
    cal 0xC40DA = 3 (>>7).

    Sizing: a 21.3 Hz sinusoid needs |gp-0x4f50| ~= 1683 counts @1 kHz (1821 @100 Hz) to reach T = 12800,
    inside that signal's own +-13000 validity ceiling => the detector is NOT structurally blind to the
    ~21 Hz mode; route 35 was ~1.7-2x short. Cross-checked in the frequency domain (|1-H1| = 0.43041 x
    |H2| = 0.95375 => 7.5965*U => U = 1685), agreeing to 4 significant figures. The `acc` clamp bites at
    U ~= 4017, so T sits at ~42% of saturation and the response is linear there.
    🛑 Do NOT size T from bus torque -- gp-0x6c2c does not share the 0x18F torque LSB. [OPEN] gp-0x4f50's
    physical units (needs the ISR writing gp-0x29c4, or a probe).

    ✅ FULL 1-500 Hz SWEEP 2026-08-0x (integer-exact simulation, sanity-checked against the 1683/1682 trip
    pair above): it is a BAND-PASS, not a low-pass -- gain PEAKS at 61 Hz (1.61x the 21.09 Hz gain), stays
    >90% of that out to ~180 Hz, and rejects 1 Hz driver-band content ~30x for free. Trip amplitude
    (counts of gp-0x4f50) needs LESS at 45-100 Hz than at 21 Hz: 21.3->1683, 45->1104, 60->1056 (min),
    80->1092, 100->1186, 150->1478, 200->1735 -- all inside the +-13000 clamp, nothing here is untrippable.
    🛑 gp-0x4f50's deg/s scale is still [OPEN] -- do NOT borrow gp-0x6ac0's 4.7121 counts/deg-s here, a
    different internal signal; that composition is exactly what produced the retracted "bus=8x deg/s".
    ★ This makes gp-0x671a the kit's only above-50-Hz-capable instrument: CAN is Nyquist 50.00, the comma
    IMU 50.51.
    """
    K1, K2 = 37, 22                                   # cals 0xC643C (>>7), 0xC40DC (>>6)
    if abs(rate_raw) > 13000:                         # 0x415be-0x415ce plausibility gate
        return 0x7FFF, 0, 0                           # 0x41AC2 fault sentinel; both EMAs reset
    target = rate_raw * 1024                          # 0x415d0  Q10
    step = ((target - ema_old) * K1) >> 7             # 0x415e8  EMA #1 increment -- THE DIFFERENCE
    ema_new = ema_old + step
    acc = _clamp(step * 0x20, -0xFA0000, 0xFA0000)    # 0x41604-0x4161a  x32, clamp +-16,384,000
    state_fast = state_fast + (((acc - state_fast) * K2) >> 6)   # 0x41622  EMA #2
    return state_fast >> 9, ema_new, state_fast       # 0x4184a/0x4184e  range +-32,000; T = 40.0% of it


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
    values 0xC6A72-B4, overrides 0xC6444/0xC643E), all single-reader, no float mirror.

    ★★★★ r26 IS LIVE ON-CAR -- MEASURED 2026-08-04, route 50 (V70). [EVIDENCE, existence proof]
    V70's bit4/bit3 sign pair read gp-0x6adc (r26's post-clamp RAM mirror) STRICTLY NEGATIVE on
    1,644 of 18,010 frames. A cell pinned at zero can never clear a `>= 0` test, so r26 is not
    identically zero. ⇒ "r26 is inert / r24 carries the entire lane" is REFUTED, and every
    re-attribution of V42/V61/V62 that rested on it must be re-priced.
    ⚠ Magnitude still unmeasured -- the probe gives SIGN only, so `a = gp-0x69a4/1024` is bounded
    away from 0 but not otherwise known. NEW asymmetry the same-sign model does NOT predict, and it
    must be carried: `bit3 => bit4` STRICTLY (0/18,010 frames with r24 >= 0 while r26 < 0), which is
    explained by "r26 is ZERO part of the time and same-signed otherwise" -- a `>= 0` test cannot
    separate zero from positive. Same-sign-when-nonzero stands; "always the same sign" does not.

    🛑🛑 r24 AND r26 HAVE SEPARATE GAIN SELECTORS SHARING ONE GATE -- and every multiplier this kit
    has published is an r24-only number. [EVIDENCE, orchestrator disassembly 2026-08-04]
        r26 -> gain_A: 0x3AB5E ld.hu 0x7444,tp,r8 (0xC6444=512, taken when lp != 0)
                     ▸ 0x3AB68 0xC643E ▸ else gain_A's own LERP (3072 at creep)
        r24 -> gain_B: 0x3ABFE ld.hu 0x7442,tp,r10 (0xC6442=1024, gp-0x671d, OUTRANKS ALL)
                     ▸ 0x3AC08 0xC6446 (lp != 0) ▸ 0x3AC12 0xC6440=2048 ▸ else the mode-10 surface
    The SAME `lp` gates both, so V67/V68's one-byte gate repoint raises r24 AND cuts r26 6.00x
    (3072 -> 512) simultaneously. Net vs stock = (5244 + 512a)/(3072 + 3072a): 1.707x at a=0,
    PARITY at a=0.848, BELOW stock above it. V69/V70 edited the mode-10 gain_B records only, so they
    never touched r26 at all.
    🛑🛑 RETRACTED 2026-08-08 -- "ONE CLEAN SINGLE-VARIABLE SERIES SAYS r24 IS NEAR-INERT" IS VOID.
    Its entire basis was stock -> V70 -> V69 reading 879 -> 729 -> 746 with r24 stepped x1 -> x2 -> x4,
    but V69 and V70 wrote MODE-10 gain_B on a mode-24/26 car, so both were functionally BYTE-STOCK and
    the "4:1 dose range" was three copies of stock -- mutually overlapping CIs are what that predicts.
    See the corrected dose table below: r24 IS the grind-#1 actor.
    ★ Four supporting byte facts: (1) gain_A's records 0xC6A68/0xC6A7C/0xC6A90/0xC6AA4 are
    BYTE-IDENTICAL across all 11 images => V67/V68's /6.00 (= 512/3072) is EXACT and engaged-only;
    (2) the two LERPs live in separate RAM -- gp-0x6e40/gp-0x6e38 for gain_B, gp-0x6e30/gp-0x6e28 for
    gain_A -- filled by the two halves of FUN_0003ad74; (3) gain_B is filled from the MODE-INDEXED
    arrays and gain_A from FIXED, non-mode-indexed records, which is why V69/V70's mode-10 surface
    edit could not reach r26 even in principle; (4) there is NO gp-0x671d mask arm on the r26 side --
    gain_A is 2 arms + default, not 3.
    ✅✅ RESOLVED 2026-08-08 -- THE "r26 x2 AND r26 /6 BOTH HELPED" TENSION IS GONE: NEITHER HELPED.
    Delivered dose at grind #1's operating point (7 km/h, 128 deg/s, engaged), mode-10 builds EXCLUDED:
        build              r26 x    r24 x    grind #1 median e_18-22
        V61                0.000    0.000            2501
        stock/V69/V70      1.000    1.000       879 / 746 / 729   (V69/V70 = byte-stock, mode-10 writes)
        V72                0.177    1.000       unmoved (0.953)
        V62/V65            2.000    2.000             168
        V67/V68            0.177    1.994             109
    r24 is MONOTONE across x0 -> x1 -> x2, while r26 swings 11.3x at fixed r24 (V72 vs stock) without
    moving grind #1, and the two builds that fixed it sit at OPPOSITE r26 ends with the SAME r24.
    => r24 is the actor and r26 is the confound. The old "⚠ grind #1 is BLIND to r24 gain, so it cannot
    be used as an in-force check" line is RETRACTED with its premise -- it was measured across three
    byte-stock builds.
    ✅ V62/V65's `sar` route (0x3AB76 AND 0x3AC20, 0xa -> 0x9) is the ONLY encoding that is dose-exact
    independent of `a`, but it doses BOTH lanes; V67/V68 beat it (109 vs 168) with the r24 half alone.

    [OPEN] r26's realistic MAGNITUDE (clips only if avg(gp-0x69a4) > ~546); the mechanical loop sign
    (positive-feedback vs feedforward, needs live telemetry, not disassembly); gp-0x6752's concrete
    runtime value; and whether gain_A's LERP rolls off with rateKey the same way gain_B's does --
    if not, the a=0.848 parity point moves.
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
    applying in series to the boost curve; all read gp-0x6a5e (voted VEHICLE SPEED) directly. [VERIFIED
    addresses; INFERRED role labels] FUN_00034350 -> gp-0x6bd0 (damping) is the product of 5
    mode-indexed LERP gain factors (a MIN-clamped seed, a flat driver-torque table, an angle-deviation
    term, |motor rate| gp-0x6ac0, and gp-0x6ac2), sign forced opposite gp-0x6abe; two independent
    hands-off deadzones exist (Factor C's Y[0]=0 below 2240 counts driver torque, mode 10/11
    @0xD27BC/D27D0, raised by V44/V47; Factor E's Y[0]=0 below 60 counts motor rate, @0xD27F8/D280C,
    raised only by V47), and its output clamp is a dynamic LERP keyed on gp-0x6ac2 (@0xD209C/D20A8)
    with a float-mirror lockstep at cal 0xC6554/58/5C/60 (DTC-0x1d no-debounce hard shutdown on
    divergence -- any edit to the int clamp table needs a bit-exact float twin). FUN_00036c12 ->
    gp-0x6b26 (friction comp) is LERP(gp-0x6a5e voted VEHICLE SPEED, @0xCBE74, mode26@0xD7A54 -- the
    "mode10@0xD2A44" this line used to name is the PRE-V73 wrong-row error, see RULE 7) x
    gp-0x6c2c (motor-rate derivative), a plain signed multiply -- NO sign()/abs/hysteresis anywhere in
    the lane, so it is smooth and continuous through zero and cannot itself generate stick-slip; magnitude
    is LARGEST at 0 km/h (Y[0]=-9830) and falls ~5x by 90 km/h (Y[2]=-1966); self-clamps +/-511 (0xC407E)
    before the aggregator's own +/-0x400 gate -- and that 511, one count under FUN_00036d74's 512 trip, is
    Honda's HARD-FAULT INTERLOCK (raised to 850 by V73-V75, restored by V81; see Section 3B).
    [VERIFIED 2026-08-04, disasm 0x36c12-0x36cbe]. FUN_0003a382 ->
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


