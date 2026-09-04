# -*- coding: utf-8 -*-
"""studies/grind/task5_imu_crosscheck.py -- THE DECISIVE TEST.

The device IMU samples at ~104 Hz nominal (accel/gyro), a rate NOT commensurate with the EPS frame's
exactly-100 Hz.  That is the whole leverage:

    a component TRULY at 27-32 Hz   -> below both Nyquists -> appears at 27-32 Hz on BOTH instruments
    a component TRULY at 68-73 Hz   -> folds to 27-32 Hz on the 100 Hz EPS frame
                                    -> folds to |68..73 - 104| = 31-36 Hz on a 104 Hz IMU
                                       (and to 18-23 Hz if the effective IMU rate is ~91 Hz)

So the two instruments put a 68-73 Hz source in DIFFERENT places, and a 27-32 Hz source in the SAME
place.  Coincidence at 27-32 Hz is evidence the band is REAL; an EPS bump at 27-32 with the IMU energy
displaced instead to the fold-partner band is evidence of FOLDING.

Sections
  0  IMU CADENCE      native ODR from the HARDWARE timestamps, drop census, and the grid we analyse on.
                      (logMonoTime is batch-jittered like CAN; the hw timestamp is the sample clock.)
  1  FINE SPECTRA     EPS rate 25-50 Hz at ~1 Hz resolution: is the near-Nyquist rise a RAMP (folding)
                      or a PEAK (a real ~48 Hz mode)?  And is 27-32 a bump above the shelf?
  2  IMU SENSITIVITY  POSITIVE CONTROL.  Can the IMU see EPS-band lines at all?  Scored on the bands the
                      kit has already established as real on this channel (7 Hz stutter, 20.3 Hz grind).
                      An absence at 27-32 Hz is only interpretable if these are PRESENT.
  3  ADJUDICATION     EPS 27-32 excess vs IMU 27-32 excess vs IMU fold-partner-band excess.

Run: python rlog-tools/studies/grind/task5_imu_crosscheck.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SC = os.path.join(HERE, "_scratch")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
TAGS = ("r35", "r36", "r37", "r38")
LINES = []


def pr(s=""):
    print(s)
    LINES.append(s)


def load(tag):
    return dict(np.load(os.path.join(SC, "imu_%s.npz" % tag)))


def runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


# ==================================================================================== 0: IMU cadence
def cadence(t_hw, name):
    dt = np.diff(t_hw)
    dt = dt[(dt > 0) & (dt < 1.0)]
    med = float(np.median(dt))
    odr = 1.0 / med
    # how many samples are one-ODR-period apart vs longer (true drops)
    k = np.round(dt / med)
    pr("        %-12s n=%7d  hw dt median=%.6f s -> ODR %.3f Hz   frac k==1 %.4f  k>=2 %.4f  implied drops %.2f%%"
       % (name, len(t_hw) + 1, med, odr, np.mean(k == 1), np.mean(k >= 2),
          100.0 * np.sum(np.maximum(k - 1, 0)) / (len(t_hw) + np.sum(np.maximum(k - 1, 0)))))
    return odr, med


def grid_on_hw(t_hw, v, odr):
    """Place samples on the TRUE sample clock: index = round((t-t0)*odr).  Gaps stay as NaN, and only
    contiguous NaN-free runs are analysed.  Interpolating onto a different rate would destroy exactly
    the alias structure this test depends on, so nothing is interpolated."""
    idx = np.round((t_hw - t_hw[0]) * odr).astype(np.int64)
    n = int(idx[-1]) + 1
    out = np.full((n, v.shape[1]), np.nan)
    out[idx] = v
    ok = np.isfinite(out[:, 0])
    return out, ok, idx


# ==================================================================================== spectra helpers
def welch_runs(x, segs, fs, nper):
    Ps, ntot = [], 0
    for a, b in segs:
        if b - a < nper:
            continue
        xx = x[a:b]
        xx = xx - np.mean(xx)
        f, P = signal.welch(xx, fs=fs, nperseg=nper, noverlap=nper // 2, window="hann", detrend="constant")
        Ps.append(P * (b - a)); ntot += b - a
    if not Ps:
        return None, None, 0
    return f, np.sum(Ps, 0) / ntot, ntot


def bm(f, P, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.mean(P[m])) if m.any() else np.nan


# ==================================================================================== 1: fine spectra
def sec1(D, tag):
    t18 = D["t18"]
    n = len(t18)
    req = np.interp(t18, D["te4"], D["req"].astype(float)) > 0.5
    eng = (np.asarray(D["sca"], float) > 0.5) & req
    segs = runs(eng, 4096)
    x = np.asarray(D["rate"], float)
    f, P, nt = welch_runs(x, segs, FS, 4096)
    if P is None:
        pr("        (no engaged run)"); return None, None, None
    ref = bm(f, P, 10, 15)
    pr("        EPS 0x18F rate, engaged, n=%d.  PSD/ref(10-15Hz), 1 Hz bins:" % nt)
    s = "        "
    for lo in range(25, 50):
        s += "%4d:%6.3f " % (lo, bm(f, P, lo, lo + 1) / ref)
        if lo % 5 == 4:
            pr(s); s = "        "
    if s.strip():
        pr(s)
    return f, P, (eng, t18)


# ==================================================================================== 2/3: IMU
AXN = ("x", "y", "z")


def sec23(D, tag, engt):
    eng, t18 = engt
    out = {}
    for kind, tk, vk in (("accel", "ahw", "av"), ("gyro", "ghw", "gv")):
        thw, v, tmono = D[tk], D[vk], D[tk[0] + "t"]
        if len(thw) < 1000:
            pr("        %s: absent" % kind); continue
        odr, med = cadence(thw, kind)
        G, ok, idx = grid_on_hw(thw, v, odr)
        # engagement on the IMU grid, via the monotime<->hw offset (both clocks are monotonic here)
        off = np.median(tmono - thw)
        tg = thw[0] + np.arange(len(G)) / odr + off
        e = np.interp(tg, t18, eng.astype(float)) > 0.5
        segs = runs(ok & e, 2048)
        for ax in range(3):
            f, P, nt = welch_runs(G[:, ax], segs, odr, 2048)
            if P is None:
                continue
            out[(kind, AXN[ax])] = (f, P, nt, odr)
    return out


def excess(f, P, lo, hi, flo, fhi):
    """band mean divided by the LOCAL FLOOR (the quietest neighbouring shelf) -- a bump measure that
    does not depend on the channel's absolute units or on a common normalisation."""
    return bm(f, P, lo, hi) / bm(f, P, flo, fhi)


def main():
    for tag in TAGS:
        pr()
        pr("=" * 112)
        pr("ROUTE %s" % tag)
        pr("=" * 112)
        D = load(tag)
        pr("-- 1  EPS rate fine spectrum 25-50 Hz (ratio to the 10-15 Hz band)")
        f, P, engt = sec1(D, tag)
        if P is None:
            continue
        pr("-- 0  IMU cadence (hardware clock)")
        S = sec23(D, tag, engt)
        pr("-- 2/3  IMU spectra: bump-over-floor at the bands that matter")
        pr("        %-12s %6s %7s | %8s %8s %8s | %8s %8s"
           % ("channel", "ODR", "n", "6-8Hz", "19-22Hz", "27-32Hz", "fold-lo", "fold-hi"))
        for (kind, ax), (fi, Pi, nt, odr) in sorted(S.items()):
            # where a TRUE 68-73 Hz source lands on THIS sampler
            fl = [abs(68.0 - odr), abs(73.0 - odr)]
            flo, fhi = min(fl), max(fl)
            if fhi > odr / 2:
                fhi = odr / 2 - 0.1
            base = (33.0, 38.0) if odr / 2 > 38 else (odr / 2 - 6, odr / 2 - 1)
            pr("        %-12s %6.2f %7d | %8.3f %8.3f %8.3f | %8.3f %8.3f  [fold band %.1f-%.1f Hz, floor %.0f-%.0f]"
               % (kind + "-" + ax, odr, nt,
                  excess(fi, Pi, 6, 8, *base), excess(fi, Pi, 19, 22, *base),
                  excess(fi, Pi, 27, 32, *base), excess(fi, Pi, flo, fhi, *base),
                  excess(fi, Pi, max(flo - 5, 1), max(flo - 1, 2), *base),
                  flo, fhi, base[0], base[1]))
        # the EPS numbers on the same scale
        pr("        %-12s %6.2f %7d | %8.3f %8.3f %8.3f |   (EPS: a 68-73 Hz source folds INTO 27-32)"
           % ("EPS rate", FS, 0, excess(f, P, 6, 8, 33, 38), excess(f, P, 19, 22, 33, 38),
              excess(f, P, 27, 32, 33, 38)))
    out = os.path.join(SC, "task5_imu_crosscheck.txt")
    open(out, "w", encoding="utf-8").write("\n".join(LINES) + "\n")
    print("\nwrote %s" % out)


if __name__ == "__main__":
    main()
