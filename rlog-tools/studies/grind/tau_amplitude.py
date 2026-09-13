# -*- coding: utf-8 -*-
"""tau_amplitude.py -- is tau AMPLITUDE-dependent?  Subagent taumeasure, 2026-09-13.
Analysis only: builds nothing, sends nothing, flashes nothing, commits nothing.

WHY THIS MATTERS TO THE VERDICT.  The adversary's outer-loop stability check uses a SINGLE lumped tau.
That is only legitimate if the command->response path is approximately linear over the amplitudes the
loop actually visits.  If the apparent lag grows with demand amplitude, the mechanism is not a transport
delay at all but RATE- or TORQUE-LIMITING (the fork runs SteerLatAccel 6.0, which cuts P/I torque
authority ~2.5x -- project-starpilot-fork-lateral-state-2026-09-10), and then a fixed-tau linear margin
is optimistic exactly where the margin is being spent.  So: measure tau in amplitude terciles.

Also splits by |steering angle| (the static-friction / high-angle regime the operator reports as the
high-angle stutter) and reports the delivered gain |H| at 1 Hz per tercile, because a falling gain with
rising amplitude is the signature of limiting rather than of delay.

Run: python rlog-tools/studies/grind/tau_amplitude.py
Writes _scratch/tau_amplitude.{txt,json}
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")
sys.path.insert(0, HERE)
from tau_identify import (load, runs, bandpass, pooled_ncc, group_delay, boot,  # noqa: E402
                          MINSTRETCH, FS, MAX_LAG, MIN_LAG2)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANDS = [(3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0)]
ROUTES = [("r39", "V282"), ("r6c", "V282"), ("r6d_v292", "V292"), ("r6e_v292", "V292"),
          ("r6f_v292", "V292"), ("r35", "V281r3")]
OUT, RESULTS = [], []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def cell(tag, build, band, lab, segs, stat):
    bp = [(bandpass(u), bandpass(y)) for u, y in segs]
    l1, c1 = pooled_ncc(bp, 0.0, MAX_LAG)
    ci = boot(bp, lambda S: pooled_ncc(S, 0.0, MAX_LAG)[0], nboot=400)
    gd = group_delay(list(segs)) or {}
    tot = sum(len(u) for u, _ in segs) / FS
    pr("        %-26s n=%2d %6.1f s | demand rms %7.2e 1/m | NCC %6.1f ms (r %.3f) CI[%5.0f,%5.0f] | GD %6.1f ms | |H|@1Hz %.3f coh %.2f"
       % (lab, len(segs), tot, stat, 1e3 * l1, c1, 1e3 * ci[0], 1e3 * ci[1],
          1e3 * gd.get("tau", float("nan")), gd.get("mag1", float("nan")), gd.get("coh1", float("nan"))))
    RESULTS.append(dict(route=tag, build=build, band=band, stratum=lab, n=len(segs), seconds=tot,
                        demand_rms=float(stat), ncc_lag=l1, ncc_corr=c1, ncc_ci=ci,
                        gd_tau=gd.get("tau"), mag1=gd.get("mag1"), coh1=gd.get("coh1")))


def main():
    pr("=" * 146)
    pr("IS tau AMPLITUDE-DEPENDENT?  u = desiredCurvature, y = steering-angle curvature (the EPS actuator channel).")
    pr("  Stretches are split into terciles by the rms of the BAND-PASSED demand (0.2-2 Hz).  A tau that GROWS with")
    pr("  amplitude while |H| FALLS is rate/torque limiting, not a transport delay -- and a fixed-tau linear margin")
    pr("  would then be optimistic exactly where the loop spends it.")
    pr("=" * 146)
    for tag, build in ROUTES:
        if not os.path.exists(os.path.join(CACHE, tag + "_lat.npz")):
            continue
        g = load(tag)
        pr("")
        pr("-" * 146)
        pr("ROUTE %-9s build %-8s" % (tag, build))
        for lo, hi in BANDS:
            m = g["ok"] & (g["v"] >= lo) & (g["v"] < hi)
            rr = runs(m, MINSTRETCH)
            if len(rr) < 3:
                pr("   v %2.0f-%-2.0f m/s : %6.1f s, %d stretches -- too few to split" % (lo, hi, m.sum() / FS, len(rr)))
                continue
            segs = [(g["u_curv"][a:b], g["y_steer"][a:b]) for a, b in rr]
            amp = np.array([np.std(bandpass(u)) for u, _ in segs])
            pr("   v %2.0f-%-2.0f m/s   %d stretches" % (lo, hi, len(rr)))
            q1, q2 = np.percentile(amp, [33.3, 66.7])
            for lab, sel in (("LOW demand tercile", amp <= q1),
                             ("MID demand tercile", (amp > q1) & (amp <= q2)),
                             ("HIGH demand tercile", amp > q2)):
                s = [x for x, k in zip(segs, sel) if k]
                if len(s) >= 2:
                    cell(tag, build, "%g-%g" % (lo, hi), lab, s, float(np.mean(amp[sel])))
    with open(os.path.join(HERE, "_scratch", "tau_amplitude.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    with open(os.path.join(HERE, "_scratch", "tau_amplitude.json"), "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=1, default=float)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
