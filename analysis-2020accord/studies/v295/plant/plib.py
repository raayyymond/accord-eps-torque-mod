# -*- coding: utf-8 -*-
"""plib.py -- data library for the V294 PLANT identification on route 75604b0a432fdc89_00000071--a7b8ba5d9d (r71b_v294).

    import sys; sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
    import plib as P
    d = P.load()          # builds the cache on first call (~1 min), then loads it

UNITS AND SIGNS (every one positive-controlled in p1_* or the loader's selftest; EVIDENCE unless marked):
  th     deg, + = LEFT        = 0x14A angle (== carState.steeringAngleDeg), kit grid, 100 Hz, 0.1 deg steps
  om     deg/s, + = LEFT      = -wire/8 = x_fw/8 (0x18F, 0.125 deg/s steps).  d(th)/dt on om: slope 1.0004 (G2 PASS)
  x      COUNTS               = 8 * om  (the firmware operand's unit; x = 8.00 counts per deg/s, EVIDENCE in the record)
  T      T counts, + = steer RIGHT = the delivered lane torque gp-0x6b38 (427 tap unit; rail 2461)
  u      = -T  (T counts, + = LEFT) -- the plant input in the left-positive frame of th/om
  plant  J*al + b*om + k*th + F*sgn(om) = u + d        (J in T counts per deg/s^2, b per deg/s, k per deg, F in counts)
         to the PID's x unit: J_x = J/8 T counts per (count/s), b_x = b/8 T counts per count.

THE TORQUE SERIES.  The 427 tap is 50 Hz and quantised to 8 counts.  The byte-exact 1 kHz march of the V294 lane
(FF from the route's own 0xE4 command + the acceleration trim from the route's own 0x18F rate, every constant read from
the V294 IMAGE) reproduces it to a few counts rms (gate G1, p1_gates.py), so the plant input is taken from the march:
  T_live  (1 kHz, and 100 Hz block means centred on each 0x18F frame)   the delivered torque
  T_null  the same march with the trim OFF (fb operand forced 0) = the FEEDFORWARD part = f(command) only
  T_trim  = T_live - T_null
The march conventions (sp sign = -demand sign, x = +wire) are the attribution's (r71b_attribution.march), calibrated by
its sign control; the output is multiplied by the fitted tap sign `sg` so every T here is in the TAP's sign.

ANALYSIS ONLY.  Reads caches and the V294 image; sends nothing, flashes nothing.
"""
import contextlib
import io
import math
import os
import sys

import numpy as np
from scipy import signal

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "_scratch", "cache")
CACHE = os.path.join(CACHE_DIR, "plant_r71b_v294.npz")
for p in (os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"),
          os.path.join(KIT, "rlog-tools", "studies", "grind"),
          os.path.join(KIT, "analysis-2020accord", "model")):
    if p not in sys.path:
        sys.path.insert(0, p)

import r71b_cache as RC  # noqa: E402

BANDS = (("0-5", 0.0, 5.0), ("5-10", 5.0, 10.0), ("10-15", 10.0, 15.0), ("15-22", 15.0, 22.0), ("22+", 22.0, 99.0))
T_PER_U = 2625.4   # T counts per openpilot torque unit at the V293/V294 surface slope (redo physics report; BELIEF-free
#                    arithmetic: 10.336 T per idx * 4096 / 16.125736) -- used ONLY to quote priors in T counts.


def _fr():
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_flight_read as FR
    return FR


# ======================================================================================================================
# the byte-exact 1 kHz march of the V294 lane (every constant from the image cells c)
# ======================================================================================================================
def march(sgn, idx, m, c, x1k=None, trim=False, fb_a=None, fb_b=None, fb_clamp=None, kp=None, e_shift=None,
          want=False):
    """r71b_attribution.march (== rp7b_dynamic_pred.march) generalised: optional overrides of the fb pole/gain/clamp,
    the flat Kp and the error shift; want=True also returns r26 and P at 1 kHz.

    Per 1 ms tick i (k = i // 10 is the 100 Hz frame, ZOH command):
        sp    = sgn[k] * LERP(map, idx[k])
        s_new = ((a*s) >> 10) + ((b*x) >> 10)          0x28F8E..0x28FA2
        r26   = clamp(s_new - s, +-C)                  0x28FA4 subr ; clamp 0xC62E6
        P     = clamp(((sp << e_shift) - r26) * Kp >> 8, +-Pcl)       0x29D76 shl ; 0x29E36 mul ; 0x29E3E sar 8
        S     = clamp((m[k] * P) >> 8, +-Scl)          taper/fade 0x2A0BE ; sum clamp
        o'    = ((la*o) >> 10) + ((S*lb) >> 10) ; y = (o + o') >> 5 ; o = o'     output lag 0x2A174..
        T     = clamp((y * gain) >> 15, +-Tcl)
    Ki = Kd = 0 on V294 (asserted from the image cells)."""
    LERP = np.array([int(np.interp(i, c["map_X"], c["map_Y"])) for i in range(241)])
    kp = int(c["kp_Y"][0]) if kp is None else int(kp)
    sh = int(c["e_shift"]) if e_shift is None else int(e_shift)
    fa = int(c["fb_a"]) if fb_a is None else int(fb_a)
    fb = int(c["fb_b"]) if fb_b is None else int(fb_b)
    fcl = int(c["fb_clamp"]) if fb_clamp is None else int(fb_clamp)
    pcl, scl, tcl = int(c["p_clamp"]), int(c["sum_clamp"]), int(c["t_clamp"])
    la, lb, gain = int(c["lag_a"]), int(c["lag_b"]), int(c["gain"])
    assert all(int(y) == int(c["kp_Y"][0]) for y in c["kp_Y"]) and all(int(y) == 0 for y in c["kd_Y"]) and int(c["ki"]) == 0
    assert c["fb_op"] == "diff"
    n = len(idx) * 10
    T = np.zeros(n)
    R26 = np.zeros(n, dtype=np.int32) if want else None
    PP = np.zeros(n, dtype=np.int32) if want else None
    SF = np.zeros(len(idx), dtype=np.int64) if want else None     # lane states ENTERING tick 10k (frame k)
    OL = np.zeros(len(idx), dtype=np.int64) if want else None
    s_fb = 0
    o = 0
    sp_k = (np.asarray(sgn, int) * LERP[np.asarray(idx, int)]).tolist()
    m_k = np.asarray(m, int).tolist()
    xl = None if x1k is None else np.clip(np.round(x1k), -12000, 12000).astype(int).tolist()
    for i in range(n):
        k = i // 10
        if want and i % 10 == 0:
            SF[k] = s_fb
            OL[k] = o
        sp = sp_k[k]
        r26 = 0
        if trim:
            s_new = ((fa * s_fb) >> 10) + ((fb * xl[i]) >> 10)
            r26 = s_new - s_fb
            r26 = fcl if r26 > fcl else (-fcl if r26 < -fcl else r26)
            s_fb = s_new
        P = (((sp << sh) - r26) * kp) >> 8
        P = pcl if P > pcl else (-pcl if P < -pcl else P)
        S = (m_k[k] * P) >> 8
        S = scl if S > scl else (-scl if S < -scl else S)
        o2 = ((la * o) >> 10) + ((S * lb) >> 10)
        y = (o + o2) >> 5
        o = o2
        v = (y * gain) >> 15
        T[i] = tcl if v > tcl else (-tcl if v < -tcl else v)
        if want:
            R26[i] = r26
            PP[i] = P
    if want:
        return T, R26, PP, SF, OL
    return T


def quant(T):
    return np.sign(T) * (np.abs(T).astype(np.int64) >> 3) * 8.0


def block_mean_1k(T1k, n100, off=0):
    """100 Hz value at frame k = mean of 1 kHz ticks 10k-5+off .. 10k+4+off (centred on the frame instant)."""
    T = np.r_[np.full(5, T1k[0]), T1k, np.full(15, T1k[-1])]
    i0 = np.arange(n100) * 10 + off                      # index into padded: tick 10k-5+off -> 10k+off
    cs = np.r_[0.0, np.cumsum(T)]
    lo = np.clip(i0, 0, len(T) - 10)
    return (cs[lo + 10] - cs[lo]) / 10.0


# ======================================================================================================================
# build / load
# ======================================================================================================================
def build():
    FR = _fr()
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route("r71b_v294", "V293")
    g = r.g
    c = RC.v294_cells()
    n = len(g["t"])
    m100 = FR.fade_multiplier(c, g["bar"], g["vego"], "bar")[:n]
    idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    idx = np.clip(np.round(idx100[:n]), 0, 240).astype(int)
    sgn = (-np.asarray(sgn100[:n])).astype(int)
    wire = np.nan_to_num(g["wire"][:n])
    x_up = signal.resample_poly(wire, 10, 1)[:n * 10]            # march convention: x = +wire (attribution s_x = +1)
    Tn = march(sgn, idx, m100, c)
    Tl, R26, PP, SF, OL = march(sgn, idx, m100, c, x1k=x_up, trim=True, want=True)
    # tap alignment: tick offset d and sign sg, fitted on hands-off engaged frames against the LIVE march
    t100 = g["t"][:n]
    t_tap, T_tap = g["T_t"], g["T"]
    keep = (t_tap > t100[0]) & (t_tap < t100[-1])
    t_tap, T_tap = t_tap[keep], T_tap[keep]
    j100 = np.clip(np.searchsorted(t100, t_tap, side="right") - 1, 0, n - 1)
    sub = np.clip(np.round((t_tap - t100[j100]) * 1000).astype(int), 0, 9)
    tick_of = lambda d: np.clip(10 * j100 + sub + d, 0, len(Tl) - 1)  # noqa: E731
    ho = g["eng"][:n][j100] & (np.abs(g["bar"][:n][j100]) < 400)
    best = None
    for d in range(-40, 41, 1):
        for sg in (+1, -1):
            v = np.var((T_tap - sg * quant(Tl[tick_of(d)]))[ho])
            if best is None or v < best[0]:
                best = (v, d, sg)
    _, dms, sg = best
    out = dict(
        t=t100, tr=t100 - t100[0], th=g["ang"][:n].astype(float), om=-wire / 8.0, wire=wire, bar=g["bar"][:n],
        v=g["vego"][:n], cmd=g["cmd"][:n], eng=g["eng"][:n], idx=idx, sgn=sgn, m=m100.astype(int),
        T1k_live=sg * Tl, T1k_null=sg * Tn, r26_1k=R26, P_1k=PP, x1k=x_up, lane_sfb=SF, lane_o=OL,
        T_live=block_mean_1k(sg * Tl, n, dms), T_null=block_mean_1k(sg * Tn, n, dms),
        t_tap=t_tap, T_tap=T_tap, j100=j100, sub=sub, tick_tap=tick_of(dms), dms=dms, sg=sg,
        tap_resid_rms_ho=float(np.sqrt(best[0])), have18=g["have18"][:n])
    # carState / controller streams on this grid
    D = RC.load(with_raw=False)
    for k in ("cs_pressed", "ctl_la_des", "ctl_la_act", "ctl_des_curv", "ctl_curv", "ctl_output", "ctl_p", "ctl_i",
              "ctl_f", "ctl_error", "cc_lat_active", "lpar_roll"):
        pre = k.split("_")[0]
        out[k] = np.interp(t100, D[pre + "_t"], np.asarray(D[k], float))
    out["mdl_des_curv"] = np.interp(t100, D["mdl_t"], D["mdl_des_curv"])
    out["pose_wz"] = np.interp(t100, D["pose_t"], D["pose_wz"])
    os.makedirs(CACHE_DIR, exist_ok=True)
    np.savez_compressed(CACHE, **out)
    return out


def load(rebuild=False):
    if rebuild or not os.path.exists(CACHE):
        build()
    d = dict(np.load(CACHE))
    for k in ("dms", "sg", "tap_resid_rms_ho"):
        d[k] = d[k].item()
    d["T_trim"] = d["T_live"] - d["T_null"]
    d["u"] = -d["T_live"]
    d["u_ff"] = -d["T_null"]
    d["x"] = 8.0 * d["om"]
    d["al"] = np.gradient(d["om"]) * 100.0                    # central difference, deg/s^2
    d["pressed"] = d["cs_pressed"] > 0.5
    d["ho"] = d["eng"] & (np.abs(d["bar"]) < 400) & ~d["pressed"]      # hands-off laterally engaged
    return d


def runs(mask, min_len=1):
    dd = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)) if b - a >= min_len]


def band_mask(d, lo, hi):
    return (d["v"] >= lo) & (d["v"] < hi)


def lp1(xs, fc, fs=100.0):
    a = math.exp(-2 * math.pi * fc / fs)
    return signal.lfilter([1 - a], [1, -a], xs, zi=[a * xs[0]])[0]


if __name__ == "__main__":
    d = load(rebuild="--rebuild" in sys.argv)
    print("frames", len(d["t"]), "tap dms", d["dms"], "sg", d["sg"], "tap resid rms (hands-off eng)", d["tap_resid_rms_ho"])
