# -*- coding: utf-8 -*-
"""v293_lib.py -- TORQUE MODE (LKAS rate feedback forced to zero) scored on the record's own machinery.

Agent `tmdesign`, subagent of `main`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing,
sends nothing on any bus, edits no build script, writes no image.

WHAT TORQUE MODE IS, IN CELLS
    0xC62E6  (LKAS PID feedback saturation clamp, stored x256)   46080 -> 0   =>  r26 == 0 on every
             path  =>  E = 32*sp exactly.  This is V279 rev 2's lever, never flown.
    Kd bank  0xCB7D4 -> record slot 7 -> 0xE511C                 128x4 -> 0
    Kp bank  0xCB994 -> record slot 7 -> 0xE5378                 248x5 -> 119x5   (see WHY 119 below)
    0xC6446  (r24 engaged arm)                                   5244 -> ? -- the open question, scored here
    everything else V282.

WHY Kp 119.  With fb == 0,  P = (32*sp*Kp)>>8  and the P clamp is 15360.  At V282's map top sp = 1032
the linear-map surface reaches the clamp at Kp = 119 (=(32*1032*119)>>8 = 15351, 120 gives 15480 and
clips).  At V282's Kp 248 the surface rails at sp = 495.5 => demand index 115 => ~45 % of 0xE4 scale
and is FLAT above it.  So Kp 119 is what preserves BOTH the peak AND the shape of the delivered
torque-vs-command surface, which is the thing the operator has actually been driving.

WHAT IS BYTE-EXACT HERE
  * every cell is read from the IMAGES (V282 / V292 / V279 rev 2 plain images), never from a build
    script's docstring or constants;
  * `Elec` (inherited unchanged from `v292_replay_lib`) marches the integer chain: two `sar 0xa` floors
    in the feedback lag, the integer output lag, the motor-gain shift, every clamp.  Torque mode is
    reached by setting c["fb_clamp"] = 0, which is exactly what the cell does.
  * `BlocksTM` is the z-domain mirror with F == 0 for the linear/pole work.

CONVENTIONS INHERITED, DECLARED
  gate73 = |Ls*Rs + Lr*Rr|, Ls = 0.55<+96 deg, Lr = 1.19<-27 deg (adv_v290_physics.LS73/LR73);
  Rs, Rr = each arm's new/today ratio at 7.3 Hz.  TORQUE MODE HAS Rs == 0 EXACTLY (no feedback path at
  all), so gate73 = |Lr|*k = 1.19*k with k = 0xC6446/5244.  That is an EXTENSION of the record's gate
  in exactly the sense `r24_lane.py` declares (TRACE-2026-09-13-r24-lane-transfer section 7.1).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import adv_v290_physics as A              # noqa: E402
import v292_replay_lib as RL              # noqa: E402
import v280_map_profiles as V             # noqa: E402
import grind_incident_r35 as GI           # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402

FW = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG282 = FW + ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-"
               "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
IMG292 = FW + ("_v292_V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
               "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
IMG279 = FW + "_v279_V279-V268BASE-PURE.FEEDFORWARD.FB0.KD0.LINEAR.TORQUE.TAP_plain_image.bin"

# --- addresses, all from the record; every VALUE below is read from the image, never asserted --------
AD = dict(fb_clamp=0xC62E6, fb_a=0xC63E8, fb_b=0xC63EA, lag_a=0xC63EC, lag_b=0xC63EE,
          p_clamp=0xC61BC, sum_clamp=0xC61BE, d_clamp=0xC61B6, t_clamp=0xC61B4, pre_clamp=0xC61B2,
          ki=0xC63E6, r24_arm=0xC6446, r24_honda=0xC6440, r24_latch=0xC6442, r24_dead=0xC61F6,
          gain_disp=0x2A1F0, map_tab=0xC9A88, kp_tab=0xCB994, kd_tab=0xCB7D4, fadeB=0xCBBC4)
SEL = 7                                   # the live variant selector, MEASURED on the wire


def _u16(b, a):
    return int.from_bytes(b[a:a + 2], "little")


def _s16(b, a):
    return int.from_bytes(b[a:a + 2], "little", signed=True)


def _u32(b, a):
    return int.from_bytes(b[a:a + 4], "little")


def read_cells(path):
    """every cell of the LKAS rate lane, read little-endian from the image itself."""
    b = open(path, "rb").read()
    c = GI.read_cells(path)               # map_X/map_Y, kp_X/kp_Y, fb_a/fb_b, lag_a/lag_b, gain, ...
    c["img"] = path
    c["kd_Y"] = [_u16(b, _u32(b, AD["kd_tab"] + 4 * SEL) + 2 + 8 + 2 * i) for i in range(4)]
    c["kd_X"] = [_u16(b, _u32(b, AD["kd_tab"] + 4 * SEL) + 2 + 2 * i) for i in range(4)]
    for k in ("p_clamp", "sum_clamp", "d_clamp", "t_clamp", "pre_clamp", "ki",
              "r24_arm", "r24_honda", "r24_latch", "r24_dead"):
        c[k] = _u16(b, AD[k])
    c["fb_clamp"] = _u16(b, AD["fb_clamp"])
    c["gain_addr"] = 0xBF000 + _u16(b, AD["gain_disp"])
    c["gain"] = _s16(b, c["gain_addr"])
    return c


def torque_mode(c, kp=119, r24_arm=None):
    """the V293 cell set, derived from a V282 cell dict by the three (or four) cal edits."""
    t = dict(c)
    t["fb_clamp"] = 0                     # 0xC62E6 -> 0     the whole lever
    t["kd_Y"] = [0, 0, 0, 0]              # 0xE511C  Kd bank -> 0
    t["kp_Y"] = [int(kp)] * len(c["kp_Y"])
    if r24_arm is not None:
        t["r24_arm"] = int(r24_arm)
    t["tag"] = "V293 TM Kp%d r24:%d" % (kp, t["r24_arm"])
    return t


# ------------------------------------------------------------------------------------------------
# THE DELIVERED SURFACE, byte for byte
# ------------------------------------------------------------------------------------------------
def surface(c, idx, fb=0.0, kd=None, fade=254, engaged=True):
    """delivered torque T at the 427 tap, STEADY STATE, as an explicit integer march.

    Mirrors FUN_00028ea6 exactly:
        sp = LERP(map_X, map_Y, idx)                             assist map
        E  = 32*sp - clamp(fb, +-0xC62E6)
        P  = clamp( (E*Kp)>>8 , +-0xC61BC )                      [0x29DA6 mul ; sar 8]
        D  = clamp( (dE*Kd)>>3 , +-0xC61B6 )                     dE = 0 in steady state
        S  = clamp( (m*(P+D))>>8 , +-0xC61BE )                   m = fade multiplier
        y  = output lag steady state:  s_ss = S*lag_b/(1024-lag_a) ; y = (s+s')>>5 -> 2*s_ss/32
        T  = clamp( (-(y*gain))>>15 , +-0xC61B4 )
    The output lag is a DC-unity-ish two-sample sum exactly like the feedback lag: at steady state
    s = s' = S*b/(1024-a) and y = (s+s')>>5, so y = 2*S*b/((1024-a)*32).  For V282's 992/507 that is
    2*507/(32*32) = 0.990234375, i.e. the record's `dc_held_lag` constant.  Verified in v293_s1.
    """
    kp_arr = np.interp(np.asarray(idx, float), c["kp_X"], c["kp_Y"])
    sp = np.interp(np.asarray(idx, float), c["map_X"], c["map_Y"])
    fbv = np.clip(np.asarray(fb, float), -c["fb_clamp"], c["fb_clamp"]) if c["fb_clamp"] else 0.0 * np.asarray(sp)
    E = 32.0 * sp - fbv
    P = np.clip(np.floor(E * kp_arr / 256.0), -c["p_clamp"], c["p_clamp"])
    D = 0.0
    S = np.clip(np.floor(fade * (P + D) / 256.0), -c["sum_clamp"], c["sum_clamp"])
    if not engaged:
        S = np.zeros_like(S)
    s_ss = S * c["lag_b"] / (1024.0 - c["lag_a"])
    y = np.floor((2.0 * s_ss) / 32.0)
    # 0x2A1E6..: mul r14,r9 ; sar 0xf -- the ECU computes T = clamp( (-(y*gain)) >> 15 , +-0xC61B4 ).
    # `sar` on a negative value is an ARITHMETIC shift = floor division, so the negation must be INSIDE
    # the floor: floor(-y*g/32768), never -floor(y*g/32768).  (Getting this backwards costs 1 count.)
    T = np.clip(np.floor(-(y * c["gain"]) / 32768.0), -c["t_clamp"], c["t_clamp"])
    return dict(idx=np.asarray(idx, float), sp=sp, kp=kp_arr, E=E, P=P, S=S, y=y, T=T)


def surface_march(c, idx, fb=0.0, kd=0, fade=254, n=4000):
    """the same surface, but by MARCHING the byte-exact Elec to steady state -- an independent method.

    Returns the settled |T| for each idx.  This is the control on `surface`'s closed-form output lag.
    """
    idx = np.atleast_1d(np.asarray(idx, float))
    out = np.empty(len(idx))
    for j, ix in enumerate(idx):
        el = RL.Elec(c, fb=(c["fb_a"], c["fb_b"]), ef=False, two_floor=True, kd=float(kd))
        sp = float(np.interp(ix, c["map_X"], c["map_Y"]))
        kp = float(np.interp(ix, c["kp_X"], c["kp_Y"]))
        x = np.zeros(n, dtype=np.int64)
        if c["fb_clamp"]:
            x[:] = int(round(-fb * (1024.0 - c["fb_a"]) / (2.0 * c["fb_b"]))) if fb else 0
        S = el.run(x, np.full(n, sp), np.full(n, kp), np.full(n, float(fade)), np.ones(n, bool))
        out[j] = abs(S["T"][-1])
    return out


# ------------------------------------------------------------------------------------------------
# THE LINEAR MIRROR -- Blocks with the feedback path deleted
# ------------------------------------------------------------------------------------------------
class BlocksTM(A.Blocks):
    """adv_v290_physics.Blocks with F == 0 when the fb clamp is 0, and an explicit Kp/Kd override.

    Everything else -- fade, output lag, motor gain, the one-tick latency in R() -- is inherited
    unchanged, so `fwd()`, `Rf()`, `loop()`, `poles()`, `Ms()` and `gate73` all work on it.
    """

    def __init__(self, c, notch=False, g=0.0, kp=None, kd=None, fb_zero=None):
        kp = float(c["kp_Y"][0] if kp is None else kp)
        super().__init__(c, notch=notch, g=g, kp=kp)
        kdv = float(c["kd_Y"][0] if kd is None else kd)
        self.C = (np.array([kp / 256.0 + kdv / 8.0, -kdv / 8.0]), np.array([1.0]))
        self.kd = kdv
        self.kp = kp
        fbz = (c.get("fb_clamp", 1) == 0) if fb_zero is None else bool(fb_zero)
        self.fb_zero = fbz
        if fbz:
            self.F = (np.array([0.0]), np.array([1.0]))   # the clamp to +-0 kills the operand outright

    def Rf(self, f):
        if self.fb_zero:
            return np.zeros_like(np.asarray(f, float), dtype=complex)
        return super().Rf(f)


def gate73_tm(k_r24, Rs=0.0):
    """gate73 = |Ls*Rs + Lr*Rr| with Rr = k exactly (the lane is LINEAR in 0xC6446 -- r24lane 9.3).

    Torque mode has Rs = 0 EXACTLY: with 0xC62E6 = 0 the feedback operand is identically zero, so the
    servo contributes no 7.3 Hz return ratio at all.  Declared as an EXTENSION of the record's gate.
    """
    return float(abs(A.LS73 * Rs + A.LR73 * float(k_r24)))


def r24_arm_for_gate(gate=1.010, Rs=0.0):
    """the 0xC6446 value that puts gate73 at `gate` with the servo arm at ratio Rs."""
    from scipy.optimize import brentq
    f = lambda k: gate73_tm(k, Rs) - gate                      # noqa: E731
    lo, hi = 0.0, 3.0
    if f(lo) * f(hi) > 0:
        return np.nan
    k = brentq(f, lo, hi, xtol=1e-10)
    return k, k * 5244.0


# ------------------------------------------------------------------------------------------------
# r24 as a SECOND ARM of the same loop  (r24_lane's convention, unit-matched to Blocks.Rf)
# ------------------------------------------------------------------------------------------------
def R_r24_poly(fb_fit, arm=5244.0, kappa=0.45):
    """(num, den) in w = z^-1 of R_r24 = -kappa*(arm/1024)*D4(f)*B(f), 1 kHz.

    D4(f) = 0.5*(1 - z^-4)  -- the lag-4 BACKWARD DIFFERENCE at 1 kHz, >>1 (r24lane section 1).
    B(f) is the measured bar-per-rate transfer, as a rational fit in w (r24_lane_transfer.fit_B).
    The lane's output is NEGATED at 0x3AD5A, which is the minus sign.
    """
    import r24_lane_transfer as M
    n, d = M.R_r24_poly(fb_fit, kappa=kappa)
    return n * (float(arm) / 5244.0), d


def loop_two_arm(el, pl, r24=None):
    """L_tot = (R_servo + R_r24) * CPD * G, as (num, den) polynomials in w."""
    rn, rd = el.R()
    if r24 is not None:
        n24, d24 = r24
        rn, rd = A.padd(A.pmul(rn, d24), A.pmul(n24, rd)), A.pmul(rd, d24)
    return A.pmul(rn, pl.num) * A.CPD, A.pmul(rd, pl.den)


def poles_two_arm(el, pl, r24=None, lo=2.0, hi=60.0):
    n, d = loop_two_arm(el, pl, r24)
    ch = A.padd(d, n)
    w = np.roots(ch[::-1])
    w = w[np.abs(w) > 1e-12]
    z = 1.0 / w
    s = np.log(z) * A.FS
    f = np.abs(s.imag) / (2 * np.pi)
    zeta = -s.real / np.abs(s)
    m = (f >= lo) & (f <= hi)
    return f[m], zeta[m], z[m]


def mode_two_arm(el, pl, r24=None, lo=12.0, hi=32.0):
    f, z, _ = poles_two_arm(el, pl, r24, lo, hi)
    if not len(f):
        return np.nan, np.nan
    k = int(np.argmin(z))
    return float(f[k]), float(z[k])


def unstable_two_arm(el, pl, r24=None):
    _, _, z = poles_two_arm(el, pl, r24, 0.0, 500.0)
    return bool(np.any(np.abs(z) >= 1.0))
