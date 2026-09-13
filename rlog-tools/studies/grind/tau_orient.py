# -*- coding: utf-8 -*-
"""tau_orient.py -- ORIENTATION pass for the actuator-delay (tau) measurement, subagent taumeasure 2026-09-13.

Analysis only.  Builds nothing, sends nothing, flashes nothing.

Questions this pass answers BEFORE any tau estimator is trusted:
  Q1  sign / scale sanity: is rate_x (= -wire/CPD, deg/s) really d(ang)/dt?  (validates CPD=8.0 and the sign)
  Q2  what is the STRUCTURE of cmd -> rate over 0.1-5 Hz -- a gain (rate loop tracks the command)
      or a differentiator (torque -> angle spring, rate = +90 deg)?  The answer decides whether the
      correlation peak of cmd vs rate is even an unbiased read of a transport delay.
  Q3  hands-off threshold: what |bar| cut reproduces carState.steeringPressed == 0 (available on the
      V292 routes only)?
  Q4  how much engaged hands-off exposure is there, per route and per speed band?

Run: python rlog-tools/studies/grind/tau_orient.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20   # noqa: E402
import v280_map_profiles as V   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
FS = 100.0
ROUTES = [("r6c", "V282"), ("r39", "V282"), ("r35", "V281r3"),
          ("r6d_v292", "V292"), ("r6e_v292", "V292"), ("r6f_v292", "V292")]
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def main():
    pr("=" * 118)
    pr("TAU ORIENTATION -- cmd(0xE4) -> wheel response, 100 Hz dejittered grids (creep20_loop_id.load)")
    pr("  CPD = %.1f raw 0x18F counts per deg/s;  rate_x = -wire/CPD (deg/s, the sign the PID sees)" % V.CPD)
    pr("  ang = 0x14A b0-1 * -0.1 deg.   cmd = 0xE4 b0-1 raw (src 129, openpilot TX echo).")
    pr("=" * 118)

    for tag, build in ROUTES:
        g = C20.load(tag)
        n = len(g["t"])
        t = g["t"]
        dt = np.median(np.diff(t))
        eng = g["eng"]
        pr("")
        pr("-" * 118)
        pr("ROUTE %-9s build %-8s  n=%d frames  dt=%.5f s (%.2f Hz)  route %.0f s  engaged %.1f%%"
           % (tag, build, n, dt, 1 / dt, t[-1] - t[0], 100 * eng.mean()))

        # ---- Q1  rate_x vs d(ang)/dt -----------------------------------------------------------
        # ang is quantised at 0.1 deg; differentiate with a 5-point Savitzky-Golay to keep it honest.
        angd = signal.savgol_filter(g["ang"], 9, 2, deriv=1, delta=dt)
        sel = eng & (np.abs(g["rate_x"]) > 2.0)
        if sel.sum() > 1000:
            sl = np.polyfit(g["rate_x"][sel], angd[sel], 1)
            cc = np.corrcoef(g["rate_x"][sel], angd[sel])[0, 1]
            pr("  Q1 d(ang)/dt vs rate_x : slope %+.4f  corr %+.4f  (n %d)   [slope +1 => CPD and sign both right]"
               % (sl[0], cc, sel.sum()))

        # ---- Q3  hands-off threshold ----------------------------------------------------------
        raw = dict(np.load(os.path.join(CACHE, tag + ".npz")))
        if "cs_press" in raw:
            pressed = np.interp(t, raw["tcs"], raw["cs_press"].astype(float)) > 0.5
            for lab, m in (("PRESSED", eng & pressed), ("not pressed", eng & ~pressed)):
                if m.sum() > 100:
                    b = np.abs(g["bar"][m])
                    pr("  Q3 |bar| raw*1.024, engaged %-12s n=%7d  p50 %6.0f  p90 %6.0f  p99 %6.0f  frac>200 %.3f  frac>400 %.3f"
                       % (lab, m.sum(), np.percentile(b, 50), np.percentile(b, 90), np.percentile(b, 99),
                          (b > 200).mean(), (b > 400).mean()))
        else:
            b = np.abs(g["bar"][eng])
            pr("  Q3 no carState steeringPressed in this cache; engaged |bar| p50 %.0f p90 %.0f p99 %.0f"
               % (np.percentile(b, 50), np.percentile(b, 90), np.percentile(b, 99)))

        # ---- Q4  exposure -----------------------------------------------------------------------
        ho = eng & (np.abs(g["bar"]) < 200)
        pr("  Q4 engaged hands-off (|bar|<200) exposure by speed band, and longest contiguous stretch:")
        for lo, hi in ((0, 3), (3, 8), (8, 15), (15, 25), (25, 99)):
            m = ho & (g["vego"] >= lo) & (g["vego"] < hi)
            rr = runs(m, 300)
            tot = m.sum() / FS
            pr("       v %2d-%-2d m/s : %8.1f s total | %3d stretches >=3 s | longest %6.1f s | sum(>=3s) %8.1f s"
               % (lo, hi, tot, len(rr), (max([b - a for a, b in rr]) / FS if rr else 0.0),
                  sum(b - a for a, b in rr) / FS))

    pr("")
    with open(os.path.join(HERE, "_scratch", "tau_orient.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
