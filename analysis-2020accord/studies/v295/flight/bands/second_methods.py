# -*- coding: utf-8 -*-
"""second_methods.py -- second, independent methods for the load-bearing numbers of the bands read.
Subagent "bands", 2026-09-30.  ANALYSIS ONLY.

  M1  RAW-RLOG SPOT CHECK of the extract agent's loader (the brief asked for one before trusting it): decode segment 5 of
      the route straight from the .rlog.zst with the kit's stock cereal (the `can` service is stock schema), take
      0x14A byte 4 and 0x18F rate on bus 1, and compare frame-for-frame with r71b_cache.load().
  M2  0x14A byte-4 cave duties on engaged frames from the extract agent's loader (0xE4 req on bus 129 & 0x18F SCA,
      ZOH onto the 0x14A clock) -- a second method for the scorer's section-6 table (which uses the kit v280 cache,
      a dejittered grid and np.interp masks).
  M3  J by an INDEPENDENT implementation and an INDEPENDENT achieved-accel sensor: the raw gyroscope yaw rate x v
      (v293_ident_lib's gyro_yaw, the negated x axis, verified slope -1.0046 vs the calibrated yaw) instead of
      livePose; own run finder and windowing (1024-sample Hann, hop 512, linear detrend, 0.15-2.4 Hz, one denominator,
      engaged & torqueState.active & not pressed & v >= 15 & not saturated, runs >= 30 s).  Run on r71b, r75, r76
      whose f1/f2 J is known (0.4168 / 1.0151 / 1.1780); the ORDERING and rough size must agree.
"""
import glob
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def m1():
    import zstandard
    from cereal import log as clog
    import r71b_cache as RC
    D = RC.load()
    p = glob.glob(os.path.join(KIT, "analysis-2020accord", "rlogs", RC.ROUTE + "--5--rlog.zst"))[0]
    data = zstandard.ZstdDecompressor().stream_reader(open(p, "rb")).read()
    t14, b4, t18, rr = [], [], [], []
    for evt in clog.Event.read_multiple_bytes(data):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        for m in evt.can:
            if m.src != 1:
                continue
            d = bytes(m.dat)
            if m.address == 0x14A and len(d) >= 5:
                t14.append(tm); b4.append(d[4])
            elif m.address == 0x18F and len(d) >= 4:
                v = (d[2] << 8) | d[3]
                t18.append(tm); rr.append(v - 65536 if v >= 32768 else v)
    t14 = np.array(t14); b4 = np.array(b4); t18 = np.array(t18); rr = np.array(rr)
    # compare as ORDERED SEQUENCES over the segment's span: 2.4-2.6 % of CAN events carry two frames of the same
    # address at one logMonoTime, so a timestamp lookup mis-pairs them (a first version of this check did, and read
    # 0.981 -- an artefact of the check, not of the loader).
    s1 = (D["s14_t"] >= t14[0] - 1e-9) & (D["s14_t"] <= t14[-1] + 1e-9)
    L14 = D["s14_b4"][s1].astype(int)
    ok14 = len(L14) == len(b4) and bool(np.all(L14 == b4))
    s2 = (D["s18_t"] >= t18[0] - 1e-9) & (D["s18_t"] <= t18[-1] + 1e-9)
    L18 = D["s18_rate_raw"][s2].astype(int)
    ok18 = len(L18) == len(rr) and bool(np.all(L18 == rr))
    pr("M1 raw-rlog spot check, segment 5: 0x14A byte 4, %d raw frames vs %d loader frames -> sequence identical %s;  "
       "0x18F rate raw, %d vs %d -> identical %s   (duplicate-timestamp share in the raw: %.3f / %.3f)"
       % (len(b4), len(L14), ok14, len(rr), len(L18), ok18, np.mean(np.diff(t14) == 0), np.mean(np.diff(t18) == 0)))
    return D


def m2(D):
    t = D["s14_t"]
    def zoh(ts, ys):
        j = np.searchsorted(ts, t, side="right") - 1
        o = np.zeros(len(t)); okk = j >= 0; o[okk] = np.asarray(ys, float)[j[okk]]; return o
    eng = (zoh(D["e4_t"], D["e4_req"]) > 0.5) & (zoh(D["s18_t"], D["s18_sca"]) > 0.5)
    b4 = D["s14_b4"].astype(int)
    pr("M2 0x14A byte-4 duties, engaged frames (n %d), extract loader:  " % eng.sum()
       + "  ".join("b%d %.3f" % (n, ((b4 >> n) & 1)[eng].mean()) for n in range(7, -1, -1)))
    pr("   SCA=0 frames (n %d): " % (~(zoh(D["s18_t"], D["s18_sca"]) > 0.5)).sum()
       + "  ".join("b%d %.3f" % (n, ((b4 >> n) & 1)[~(zoh(D["s18_t"], D["s18_sca"]) > 0.5)].mean()) for n in range(7, 2, -1)))


def m3():
    import v293_ident_lib as L
    FS = 100.0
    for tag in ("r71b_v294", "r75_v293r4", "r76_v293r5"):
        g = L.load(tag)
        v = g["v"]
        cs = g["cs_active"] > 0.5
        m = g["eng"] & cs & (g["press"] < 0.5) & (v >= 15) & (g["sat"] < 0.5)
        X_all = np.nan_to_num(g["des_curv"] * v ** 2)
        Y_all = np.nan_to_num(g["gyro_yaw"] * v)
        Yp_all = np.nan_to_num(g["pose_yaw"] * v)
        m &= np.isfinite(g["gyro_yaw"]) & np.isfinite(g["des_curv"])
        runs = [(a, b) for a, b in L.stretches(m, int(30 * FS))]
        w = signal.get_window("hann", 1024)
        f = np.fft.rfftfreq(1024, 1 / FS)
        bsel = (f >= 0.15) & (f <= 2.4)
        pe = px = pep = 0.0; nw = 0
        for a, b in runs:
            for s in range(a, b - 1024 + 1, 512):
                x = signal.detrend(X_all[s:s + 1024]) * w
                y = signal.detrend(Y_all[s:s + 1024]) * w
                yp = signal.detrend(Yp_all[s:s + 1024]) * w
                Xf, Yf, Ypf = np.fft.rfft(x), np.fft.rfft(y), np.fft.rfft(yp)
                pe += np.sum(np.abs(Xf[bsel] - Yf[bsel]) ** 2); px += np.sum(np.abs(Xf[bsel]) ** 2)
                pep += np.sum(np.abs(Xf[bsel] - Ypf[bsel]) ** 2); nw += 1
        pr("M3 %-11s runs >= 30 s: %d, windows %d:  J(gyro x v) = %.4f   J(livePose via ident cache) = %.4f"
           % (tag, len(runs), nw, pe / px if px else np.nan, pep / px if px else np.nan))


if __name__ == "__main__":
    D = m1()
    m2(D)
    m3()
    open(os.path.join(HERE, "second_methods_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
