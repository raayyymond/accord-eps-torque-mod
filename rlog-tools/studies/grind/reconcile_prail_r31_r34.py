# -*- coding: utf-8 -*-
"""studies/grind/reconcile_prail_r31_r34.py -- TASK 3 of the V290 reconciliation.  Agent `reconcile`, 2026-09-09.
READ-ONLY on caches that already exist.  Builds nothing, flashes nothing, sends nothing.

THE OPEN ITEM (design290d, DESIGN-V290B-2026-09-09.md): all 304 plant fits go Nyquist-UNSTABLE at Kp 696, yet routes
r31-r34 FLEW Kp 696 stable with the ring at zeta 0.019 and f pinned within +0.4 Hz.  design290d's BELIEF is a
LARGE-SIGNAL P-RAIL: a railed proportional term has zero incremental gain for a small superimposed ring, which would
both pin f across a Kp change and make every worst-case-over-the-family zeta in the decision table too pessimistic.

THE TEST.  Replay Honda's OWN arithmetic (design290b's byte-exact `Controller`, whose cells are read from the flown
images) on the MEASURED inputs of each route:
  x  = 8 * wire rate (0x18F), zero-order-held onto the 1 kHz loop grid -- which is what the ECU actually sees between
       CAN frames, so this is a MIRROR of the computation, not a simulation of the plant.
  sp = the rate setpoint the assist map produces from the 0xE4 torque request.
and count, engaged-only, how often each clamp BINDS: P (0xC61BC), D (0xC61B6), the sum clamp (0xC61BE) and the
feedback clamp (0xC62E6).

MAP SLOPE.  The one quantity not read directly off the wire.  Anchors, both from the record:
  * stock's map tops out at Y = 172 setpoint counts at full command (idx 240) -- the retraction memory
    `accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440`;
  * design290b's STEP_SP: one capped 0xE4 frame (123 raw) -> ~33 setpoint counts, i.e. 0.2683 counts per raw unit,
    which at the 4096 rail gives 1099 counts ~ 6 x 172 -- consistent with LINEAR.TO6X.
The duty is MONOTONE in the slope, so it is swept and the whole curve reported: the verdict must not rest on one
assumed constant.
"""
import glob
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
FW = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CDIR = os.path.join(ROOT, "analysis-2020accord", "_scratch", "cache")

import design290b_candidates as D    # noqa: E402  (Controller, clampi, sar -- the byte-exact mirror)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


IMG = {"V278": "_v278_V278R3-*_plain_image.bin",
       "V280": "_v280_V280R2-*_plain_image.bin",
       "V282": "_v282_V282-*_plain_image.bin"}


def read_cells(pat):
    p = glob.glob(FW + pat)[0]
    b = open(p, "rb").read()
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]
    s16 = lambda a: struct.unpack_from("<h", b, a)[0]
    u32 = lambda a: struct.unpack_from("<I", b, a)[0]
    c = dict(path=os.path.basename(p))
    c["fb_a"], c["fb_b"] = s16(0xC63E8), u16(0xC63EA)
    c["lag_a"], c["lag_b"] = s16(0xC63EC), u16(0xC63EE)
    c["gain"] = s16(0xBF000 + u16(0x2A1F0))
    kb = u32(0xCB994 + 4 * 7); db = u32(0xCB7D4 + 4 * 7)
    c["kp_X"] = [u16(kb + 2 + 2 * i) for i in range(5)]
    c["kp_Y"] = [u16(kb + 12 + 2 * i) for i in range(5)]
    c["kd_X"] = [u16(db + 2 + 2 * i) for i in range(4)]
    c["kd_Y"] = [u16(db + 10 + 2 * i) for i in range(4)]
    c["sum_clamp"], c["t_clamp"] = u16(0xC61BE), u16(0xC61B4)
    c["d_clamp"], c["p_clamp"] = u16(0xC61B6), u16(0xC61BC)
    c["fb_clamp"] = u16(0xC62E6)
    c["b0"] = c["b1"] = c["a2"] = 0
    return c


def fb_chain(x, fb_a, fb_b):
    """Honda's feedback filter, byte-exact, VERBATIM from `Controller.tick` (design290b_candidates.py):
        s_new = (fb_a*s_fb >> 10) + (fb_b*x >> 10) ; fb_raw = s_fb + s_new ; s_fb = s_new.
    The only recursion in the whole P/D/sum chain, so it is the only part that has to be a loop; `>>` on a Python int
    is an arithmetic shift, which is what V850's `sar` does."""
    n = len(x)
    fb_raw = np.empty(n, np.int64)
    s = 0
    xl = x.tolist()
    for k in range(n):
        s_new = ((fb_a * s) >> 10) + ((fb_b * xl[k]) >> 10)
        fb_raw[k] = s + s_new
        s = s_new
    return fb_raw


def zoh(t_src, v_src, t_dst):
    i = np.searchsorted(t_src, t_dst, side="right") - 1
    i = np.clip(i, 0, len(v_src) - 1)
    return v_src[i]


def run_route(tag, c, kp, slope, engmask="sca", fbcache=None):
    z = np.load(os.path.join(CDIR, tag, tag + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    rate = np.asarray(z["rate_f"], float)
    e4 = np.asarray(z["e4tq"], float)
    eng = np.asarray(z[engmask], float) > 0.5
    good = np.isfinite(t) & np.isfinite(rate) & np.isfinite(e4)
    t, rate, e4, eng = t[good], rate[good], e4[good], eng[good]
    tg = np.arange(t[0], t[-1], 1e-3)
    # SIGN, resolved empirically and consistent with adv_v290_physics' header (x = gp-0x6a56 = -(0x18F wire rate)):
    # x = -8*rate with sp = +slope*e4tq is the only pairing that makes 32*sp and fb POSITIVELY correlated (+0.377 on
    # r34) and halves the median |E| (1209 vs 2544 counts) -- i.e. the only pairing in which the loop TRACKS.
    xg = np.round(-8.0 * zoh(t, rate, tg)).astype(int)         # CPD = 8 counts per deg/s
    spg = np.round(slope * zoh(t, e4, tg)).astype(int)
    eg = zoh(t, eng.astype(float), tg) > 0.5
    kd = int(c["kd_Y"][0])
    xg = np.clip(xg, -12000, 12000).astype(np.int64)
    spg = np.where(eg, spg, 0).astype(np.int64)
    if fbcache is None:
        fbcache = fb_chain(xg, int(c["fb_a"]), int(c["fb_b"]))
    fb = np.clip(fbcache, -int(c["fb_clamp"]), int(c["fb_clamp"]))
    E = 32 * spg - fb
    P_raw = (E * int(kp)) >> 8
    P = np.clip(P_raw, -int(c["p_clamp"]), int(c["p_clamp"]))
    dE = np.empty_like(E); dE[0] = 0; dE[1:] = E[1:] - E[:-1]
    D_raw = (dE * kd) >> 3
    Dt = np.clip(D_raw, -int(c["d_clamp"]), int(c["d_clamp"]))
    S_raw = (254 * (P + Dt)) >> 8
    m = eg
    if m.sum() == 0:
        return None, fbcache
    return dict(tag=tag, n=int(m.sum()), kp=int(kp), slope=slope,
                p=float((np.abs(P_raw) >= c["p_clamp"])[m].mean()),
                d=float((np.abs(D_raw) >= c["d_clamp"])[m].mean()),
                s=float((np.abs(S_raw) >= c["sum_clamp"])[m].mean()),
                fb=float((np.abs(fbcache) >= c["fb_clamp"])[m].mean()),
                E_p50=float(np.percentile(np.abs(E[m]), 50)),
                E_p99=float(np.percentile(np.abs(E[m]), 99)), E_max=float(np.max(np.abs(E[m]))),
                E_rail=c["p_clamp"] * 256.0 / kp, sp_p99=float(np.percentile(np.abs(spg[m]), 99))), fbcache


def main():
    pr("reconcile_prail_r31_r34 -- P/D/sum/fb clamp BIND DUTY from the byte-exact firmware mirror on measured inputs")
    cells = {k: read_cells(v) for k, v in IMG.items()}
    for k, c in cells.items():
        pr("  %s cells: Kp Y %s  Kd Y %s  clamps P %d D %d S %d T %d fb %d  fb pole %d/%d  gain %d" % (
            k, c["kp_Y"], c["kd_Y"], c["p_clamp"], c["d_clamp"], c["sum_clamp"], c["t_clamp"], c["fb_clamp"],
            c["fb_a"], c["fb_b"], c["gain"]))
    pr("  P rails at |E| = p_clamp*256/Kp: %.0f at Kp 248, %.0f at Kp 696  (E is 32 counts per setpoint count;"
       % (15360 * 256 / 248, 15360 * 256 / 696))
    pr("   the feedback side is ~247 counts per deg/s, so those are ~64 and ~22.9 deg/s of RATE ERROR)")

    ROUTES = [("r31", "V278"), ("r32", "V280"), ("r33", "V280"), ("r34", "V280"), ("r39", "V282")]
    SLOPES = [0.0671, 0.1342, 0.2683, 0.4025]      # x1.5 / x3 / x6 (LINEAR.TO6X) / x9 of stock's 172-count ceiling
    KPS = [248, 696]
    res = []
    pr("")
    pr("  route build   Kp   map slope | engaged ms |  P bind   D bind   S bind  fb bind | |E| p50  |E| p99  rail@ | |sp| p99")
    for tag, bld in ROUTES:
        fbc = None
        for kp in KPS:
            for sl in SLOPES:
                r, fbc = run_route(tag, cells[bld], kp, sl, fbcache=fbc)
                if r is None:
                    continue
                r["build"] = bld
                res.append(r)
                pr("  %-5s %-6s %4d  x%.1f (%.4f) | %10d | %7.4f %8.4f %8.4f %8.4f | %8.0f %8.0f %6.0f | %8.0f" % (
                    tag, bld, kp, sl / 0.0447, sl, r["n"], r["p"], r["d"], r["s"], r["fb"],
                    r["E_p50"], r["E_p99"], r["E_rail"], r["sp_p99"]))
    json.dump(res, open(os.path.join(SCR, "reconcile_prail.json"), "w"), indent=0, default=float)
    open(os.path.join(SCR, "reconcile_prail.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/reconcile_prail.txt")


if __name__ == "__main__":
    main()
