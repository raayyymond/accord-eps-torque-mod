#!/usr/bin/env python3
r"""v102_torque_intermittency.py -- the WITHIN-BUILD test `pole-hunt` asked for.

THE QUESTION.  Does driver torque suppress the 21.5-25.5 Hz resonance, and does it make the line
INTERMITTENT?  The cross-build comparison cannot answer it -- V101 (|tq| p50 871 ct) has the
STEADY line and V102 (154 ct) the bursty one, which is the wrong way round -- but that comparison
confounds grip with gain.  **Within one build the gain is fixed, so grip is the only thing moving.**

DESIGN
  * 1 s engaged windows, band POWER in 21.5-25.5 Hz and in the 2.5-4.5 Hz control band.
  * Stratified by the window's own median |driver torque|.
  * 🛑 CONDITIONED ON SPEED **AND** WHEEL RATE, because driver torque is not applied at random --
    it goes up in curves, which is also where excitation goes up.  An unconditioned torque trend
    would measure "curves", not "grip".  Cells are (speed x |wheel rate|); the torque trend is
    computed WITHIN each cell and pooled by min-n weighting.
  * TWO readouts per stratum: MEDIAN band power (does grip suppress?) and p90/p50 of band power
    (does grip make it bursty?).
  * STOCK is the NEGATIVE CONTROL: it has no resonance (peak prominence 2.3 vs V102's 75.7), so a
    torque trend there would indict the method rather than support the mechanism.

🛑 WHAT THIS CANNOT DO.  `steeringPressed` toggles inside most V101 windows (route-stock: 2 pure
   hands-off and 3 pure hands-on windows out of 103), so V101 is reported for completeness but its
   torque strata are not clean.  V102 and STOCK are the interpretable arms.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import score_v102_full as F  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ARMS = [("97", "STOCK 1x"), ("85", "V100 4x"), ("96", "V102 6x"), ("95", "V101 8x")]
TQBINS = [(0, 100), (100, 250), (250, 500), (500, 1000), (1000, 1e9)]
VCELL = [(5, 35), (35, 65), (65, 200)]
RCELL = [(0, 3), (3, 13), (13, 1e9)]


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def table(route):
    """1 s engaged windows with band POWER, speed, |wheel rate|, |driver torque|, episode."""
    z = dict(np.load(ROOT / "analysis-2020accord" / F.NPZ[route], allow_pickle=True))
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    vk = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    dtq = np.abs(np.asarray(z["cs_tq"], float))
    rate = np.abs(np.asarray(z["rate_c"], float))
    WL = int(round(1.0 * FS))
    rows = []
    for ep, (a, b) in enumerate(F.runs_break(lat, t, WL)):
        n_ = F.bp(np.asarray(z["tq"], float), a, b, FS, 21.5, 25.5)
        d_ = F.bp(np.asarray(z["tq"], float), a, b, FS, 2.5, 4.5)
        for i in range(0, (b - a) - WL + 1, WL):
            sl = slice(i, i + WL)
            rows.append(dict(epi=ep, P=float(np.mean(n_[sl] ** 2)),
                             Pc=float(np.mean(d_[sl] ** 2)),
                             v=float(np.median(vk[a:b][sl])),
                             r=float(np.median(rate[a:b][sl])),
                             q=float(np.median(dtq[a:b][sl]))))
    return {k: np.array([r[k] for r in rows], float) for k in rows[0]}


def trend(T, key="P"):
    """min-n-weighted mean of per-cell log(high-torque / low-torque), cells = speed x wheel rate."""
    num = den = 0.0
    cells = 0
    for vlo, vhi in VCELL:
        for rlo, rhi in RCELL:
            m = (T["v"] >= vlo) & (T["v"] < vhi) & (T["r"] >= rlo) & (T["r"] < rhi)
            lo = m & (T["q"] < 250)
            hi = m & (T["q"] >= 500)
            if lo.sum() >= 8 and hi.sum() >= 8:
                w = min(lo.sum(), hi.sum())
                num += w * np.log(np.median(T[key][hi]) / np.median(T[key][lo]))
                den += w
                cells += 1
    return (float(np.exp(num / den)) if den else np.nan), cells


if __name__ == "__main__":
    TAB = {r: table(r) for r, _ in ARMS}

    hdr("1 -- RAW STRATA (not yet conditioned).  Median band POWER 21.5-25.5 Hz by driver torque,\n"
        "     and p90/p50 of that power = INTERMITTENCY.  Higher p90/p50 = burstier.")
    for r, lab in ARMS:
        T = TAB[r]
        print("\n   %s   (engaged 1 s windows: %d)" % (lab, len(T["v"])))
        print("      %-14s %6s %12s %10s %10s %10s"
              % ("|driver tq| ct", "n", "med power", "p90/p50", "med shape", "med v km/h"))
        for lo, hi in TQBINS:
            m = (T["q"] >= lo) & (T["q"] < hi)
            if m.sum() < 8:
                print("      %-14s %6d   -- too thin" % ("%d-%g" % (lo, min(hi, 9999)), m.sum()))
                continue
            P = T["P"][m]
            q = np.percentile(P, [50, 90])
            print("      %-14s %6d %12.4g %10.2f %10.3f %10.1f"
                  % ("%d-%g" % (lo, min(hi, 9999)), m.sum(), q[0], q[1] / max(q[0], 1e-30),
                     np.median(np.sqrt(P / np.maximum(T["Pc"][m], 1e-30))), np.median(T["v"][m])))

    hdr("2 -- 🛑 THE TEST, CONDITIONED ON SPEED x WHEEL RATE.\n"
        "     ratio = (band power at |tq| >= 500) / (band power at |tq| < 250), within cells.\n"
        "     < 1 => driver torque SUPPRESSES the resonance.  > 1 => it EXCITES it.")
    print("   %-11s %14s %10s %14s %10s   %s"
          % ("arm", "POWER ratio", "cells", "SHAPE ratio", "cells", "reading"))
    rng = np.random.default_rng(5)
    for r, lab in ARMS:
        T = TAB[r]
        T2 = dict(T)
        T2["S"] = T["P"] / np.maximum(T["Pc"], 1e-30)
        tp, cp = trend(T, "P")
        ts, cs = trend(T2, "S")
        if not np.isfinite(tp):
            print("   %-11s   no cells" % lab)
            continue
        bs = []
        for _ in range(2000):
            keys = np.unique(T["epi"])
            sel = np.concatenate([np.nonzero(T["epi"] == keys[j])[0]
                                  for j in rng.integers(0, len(keys), len(keys))])
            Tb = {k: v[sel] for k, v in T.items()}
            b, _ = trend(Tb, "P")
            if np.isfinite(b):
                bs.append(b)
        lo95, hi95 = np.percentile(bs, [2.5, 97.5]) if len(bs) > 50 else (np.nan, np.nan)
        rd = "SUPPRESSES" if hi95 < 1 else ("EXCITES" if lo95 > 1 else "not separated from 1")
        print("   %-11s %6.3f [%.2f,%.2f] %10d %14.3f %10d   %s"
              % (lab, tp, lo95, hi95, cp, ts, cs, rd))

    hdr("3 -- DOES GRIP CHANGE THE CHARACTER?  p90/p50 of band power, low vs high torque,\n"
        "     pooled within the same speed x wheel-rate cells.")
    print("   %-11s %16s %16s %10s   %s"
          % ("arm", "p90/p50 lo-tq", "p90/p50 hi-tq", "cells", "reading"))
    for r, lab in ARMS:
        T = TAB[r]
        L, H, c = [], [], 0
        for vlo, vhi in VCELL:
            for rlo, rhi in RCELL:
                m = (T["v"] >= vlo) & (T["v"] < vhi) & (T["r"] >= rlo) & (T["r"] < rhi)
                lo = m & (T["q"] < 250)
                hi = m & (T["q"] >= 500)
                if lo.sum() >= 8 and hi.sum() >= 8:
                    for arr, dst in ((T["P"][lo], L), (T["P"][hi], H)):
                        p = np.percentile(arr, [50, 90])
                        dst.append(p[1] / max(p[0], 1e-30))
                    c += 1
        if not c:
            print("   %-11s   no cells" % lab)
            continue
        ml, mh = float(np.median(L)), float(np.median(H))
        print("   %-11s %16.2f %16.2f %10d   %s"
              % (lab, ml, mh, c,
                 "grip makes it BURSTIER" if mh > 1.3 * ml else
                 "grip makes it STEADIER" if ml > 1.3 * mh else "no character change"))
