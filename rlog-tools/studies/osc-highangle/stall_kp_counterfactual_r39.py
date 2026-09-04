# -*- coding: utf-8 -*-
"""stall_kp_counterfactual_r39.py -- the Kp-cut deadband counterfactual at r39's OPERATING POINT.

r39's cache (`analysis-2020accord/_scratch/cache/r39/r39.npz`, 91 fields) is a DIFFERENT schema from
the V.Route caches used by stall_kp_counterfactual.py -- it carries no `ref` and no demand `idx`, so
the rate/ref stall definition cannot be evaluated on it without reconstructing the map chain.  This
script therefore uses `dec39`'s OWN ref-free window definition verbatim, which is what produced the
published "r39: 17 windows, longest 2.69 s":

    engaged (sca==1 & e4req==1) & |bar torque| < 400 & |wheel rate| < 2 deg/s
    & |0xE4 cmd| > 100 & v > 0.5 m/s & constant cmd sign, runs >= 0.6 s

THE COUNTERFACTUAL.  With Ki = 0 the DC chain is a static gain proportional to Kp.  A frame whose
measured rate/ref = x maps to x' = k*x/(1 - x + k*x), k = Kp'/248.  Inside a stall window x is small
(rate < 2 deg/s against a reference of tens), so to first order x' -> k*x and the delivered rate
scales by k.  A frame that WILL read < 2 deg/s at Kp' is therefore one that reads < 2/k today.
==> re-run the identical window detector with the rate threshold widened to 2/k.

  [EVIDENCE] the Kp-linearity of the DC chain, byte-exact with Ki = 0.
  [BELIEF]   that the road load and the openpilot demand are unchanged -- as on r35, this makes the
             result a LOWER bound (openpilot would wind the command up, not down).
  [EVIDENCE] the small-x limit: at x <= 0.1 the exact map and k*x differ by under 4 %.

Run: python rlog-tools/studies/osc-highangle/stall_kp_counterfactual_r39.py
Subagent znback, 2026-09-04.
"""
import os

import numpy as np

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "..", "analysis-2020accord", "_scratch", "cache", "r39", "r39.npz")
KPS = (248, 200, 176, 148, 128, 100)


def runs_of(mask, nmin):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= nmin]


def main():
    out = []

    def pr(s=""):
        print(s, flush=True)
        out.append(s)

    D = dict(np.load(os.path.normpath(CACHE)))
    t = D["t"]
    FS = 1.0 / float(np.median(np.diff(t)))
    eng = (D["sca"] == 1) & (D["e4req"] == 1)
    bar = np.abs(D["cs_tq"])
    rate = np.abs(D["cs_rate"])
    cmd = D["e4tq"]
    v = D["cs_v"]
    sgn = np.sign(cmd)

    pr("=" * 140)
    pr("r39 DEADBAND COUNTERFACTUAL -- the Kp cut at r39's OWN operating point (V282, Ki 0, +1.70x outer authority)")
    pr("=" * 140)
    pr("  cache %s : fs %.2f Hz, %d frames, %.1f s total, %.1f s engaged"
       % (os.path.basename(os.path.normpath(CACHE)), FS, len(t), t[-1] - t[0], eng.sum() / FS))
    pr("  detector = dec39's: engaged & |bar|<400 & |rate|<THR & |cmd|>100 & v>0.5 & constant cmd sign, run >= 0.6 s")
    pr("  counterfactual: THR widened from 2.0 to 2.0/k, k = Kp'/248  (small-x limit of the DC map)")
    pr("")
    base_ctx = eng & (bar < 400) & (np.abs(cmd) > 100) & (v > 0.5)
    pr("  eligible context (before the rate gate): %.1f s" % (base_ctx.sum() / FS))
    pr("")
    pr("  %6s %8s %10s %12s %13s %13s %13s %14s"
       % ("Kp", "k", "THR deg/s", "windows", "total secs", "LONGEST", "mean len", "vs Kp 248"))
    res = {}
    for kp in KPS:
        k = kp / 248.0
        thr = 2.0 / k
        m = base_ctx & (rate < thr)
        # constant command sign within a run: split runs at sign changes
        segs = []
        for a, b in runs_of(m, 1):
            s = sgn[a:b]
            cut = np.flatnonzero(np.diff(s) != 0) + 1
            for a2, b2 in zip(np.r_[0, cut], np.r_[cut, b - a]):
                if b2 - a2 >= int(round(0.6 * FS)):
                    segs.append((a + a2, a + b2))
        lens = np.array([(b - a) / FS for a, b in segs]) if segs else np.array([])
        res[kp] = (len(segs), lens.sum(), lens.max() if len(lens) else 0.0)
        pr("  %6d %8.3f %10.2f %12d %11.1f s %11.2f s %11.2f s %13s"
           % (kp, k, thr, len(segs), lens.sum(), lens.max() if len(lens) else 0.0,
              lens.mean() if len(lens) else 0.0,
              "baseline" if kp == 248 else "%.2fx runs" % (len(segs) / max(res[248][0], 1))))
    pr("")
    pr("  BASELINE CHECK: dec39 published r39 = 17 windows, longest 2.69 s.  This script reproduces")
    pr("  %d windows, longest %.2f s at Kp 248." % (res[248][0], res[248][2]))
    pr("")
    pr("  THE QUESTION team-lead ASKED: on r35 the Kp cut added marginal runs WITHOUT deepening the")
    pr("  worst one (3.4 s at every Kp).  At r39's operating point:")
    pr("     longest run: " + " | ".join("Kp %3d: %.2f s" % (kp, res[kp][2]) for kp in KPS))
    d = res[148][2] - res[248][2]
    pr("     Kp 248 -> 148 moves the worst run by %+.2f s (%+.0f %%)  ==> %s"
       % (d, 100 * d / max(res[248][2], 1e-9),
          "the worst case DOES deepen" if d > 0.3 else "the r35 finding HOLDS -- marginal runs only"))
    pr("")
    pr("  r35 comparison (rate/ref metric, from stall_kp_counterfactual.py):")
    pr("     Kp 248: 7 runs / 14.8 s, longest 3.4 s   ->   Kp 148: 9 runs / 18.9 s, longest 3.4 s")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "STALL-KP-COUNTERFACTUAL-R39.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
