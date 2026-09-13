# -*- coding: utf-8 -*-
"""tau_phase_table.py -- the EQUIVALENT DELAY AS A FUNCTION OF FREQUENCY, per route / speed band /
response channel.  Subagent taumeasure, 2026-09-13.
Analysis only: builds nothing, sends nothing, flashes nothing, commits nothing.

WHY THIS AND NOT ONE NUMBER.  The command->response path is NOT a pure delay: the measured phase is not
linear in frequency, so the correlation-peak lag, the phase-slope group delay and the phase at 1 Hz do
not agree (on r6c 25+ m/s they read 182, 288 and 210 ms).  A single lumped tau is therefore
under-specified, and which one is right depends on WHERE THE OUTER LOOP CROSSES OVER.

For a phase-margin argument the quantity that matters is the phase AT the crossover frequency, so the
honest deliverable is a table:

    tau_eq(f) = -phase(f) / (360 * f)      seconds

the delay a pure-delay model would need to reproduce the measured phase at that f.  Read the row at your
crossover.  |H| and coherence are printed beside it so a cell with no support can be discarded.

Run: python rlog-tools/studies/grind/tau_phase_table.py
Writes _scratch/tau_phase_table.{txt,json}
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")
sys.path.insert(0, HERE)
from tau_identify import load, runs, FS, MINSTRETCH  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FGRID = [0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]
BANDS = [(3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0)]
ROUTES = [("r39", "V282 (SR12.5 tune)"), ("r35", "V281r3 (SR12.5 tune)"), ("r6c", "V282 (SR16.8 tune)"),
          ("r6d_v292", "V292"), ("r6e_v292", "V292"), ("r6f_v292", "V292")]
CHANS = [("y_steer", "EPS actuator  (controller loop)"), ("y_yaw", "full lateral  (path loop, raw gyro)")]
OUT, RESULTS = [], []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def xfer(pairs, nper=1024):
    Puu = Pyy = Puy = None
    for u, y in pairs:
        if len(u) < nper:
            continue
        f, a = signal.welch(u, FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, b = signal.welch(y, FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, c = signal.csd(u, y, FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        w = len(u)
        Puu = a * w if Puu is None else Puu + a * w
        Pyy = b * w if Pyy is None else Pyy + b * w
        Puy = c * w if Puy is None else Puy + c * w
    if Puu is None:
        return None
    H = Puy / Puu
    coh = np.abs(Puy) ** 2 / (Puu * Pyy)
    return f, H, coh


def main():
    pr("=" * 136)
    pr("EQUIVALENT DELAY vs FREQUENCY.   tau_eq(f) = -phase(f) / (360 f)  [ms] -- the pure delay that would")
    pr("reproduce the MEASURED phase at that frequency.  Read the row at your outer-loop crossover.")
    pr("  u = controlsState.desiredCurvature.   Phase unwrapped from DC; coherence printed for every cell.")
    pr("  A cell with coherence < 0.5 is NOT usable and is marked with a '?'.")
    pr("=" * 136)
    for ck, clab in CHANS:
        pr("")
        pr("#" * 136)
        pr("### CHANNEL: %s" % clab)
        pr("#" * 136)
        pr("%-10s %-20s %-9s %6s | %s" % ("route", "build/tune", "band m/s", "secs",
                                          "".join("%13s" % ("%g Hz" % f) for f in FGRID)))
        for tag, build in ROUTES:
            if not os.path.exists(os.path.join(CACHE, tag + "_lat.npz")):
                continue
            g = load(tag)
            for lo, hi in BANDS:
                m = g["ok"] & (g["v"] >= lo) & (g["v"] < hi)
                rr = runs(m, MINSTRETCH)
                if not rr:
                    continue
                r = xfer([(g["u_curv"][a:b], g[ck][a:b]) for a, b in rr])
                if r is None:
                    continue
                f, H, coh = r
                phu = np.degrees(np.unwrap(np.angle(H)))
                cells, row = [], []
                for fq in FGRID:
                    ph = float(np.interp(fq, f, phu)); ch = float(np.interp(fq, f, coh))
                    mg = float(np.interp(fq, f, np.abs(H)))
                    te = -ph / (360.0 * fq)
                    row.append("%10.0f%s" % (1e3 * te, " ?" if ch < 0.5 else "  "))
                    cells.append(dict(f=fq, tau_eq_ms=1e3 * te, phase_deg=ph, coh=ch, mag=mg))
                pr("%-10s %-20s %-9s %6.0f | %s" % (tag, build, "%g-%g" % (lo, hi),
                                                    sum(b - a for a, b in rr) / FS, "".join("%13s" % c for c in row)))
                pr("%-10s %-20s %-9s %6s | %s" % ("", "  coherence", "", "",
                                                  "".join("%13s" % ("%.2f" % c["coh"]) for c in cells)))
                RESULTS.append(dict(route=tag, build=build, chan=ck, band="%g-%g" % (lo, hi),
                                    seconds=sum(b - a for a, b in rr) / FS, cells=cells))
    with open(os.path.join(HERE, "_scratch", "tau_phase_table.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    with open(os.path.join(HERE, "_scratch", "tau_phase_table.json"), "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=1, default=float)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
