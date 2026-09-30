# -*- coding: utf-8 -*-
"""h6_sensitivity.py -- sensitivity of the retrodiction to the harness's own BELIEF-grade settings:
  pipe_ms  (0x14A sample -> 0xE4 effective at the EPS; 20 ms measured to the bus + an unmeasured EPS-internal part)
  x_noise  (the rate operand's white noise, 1.93 counts rms measured at standstill)
Under disturbance replay the right pipeline delay should MAXIMISE the reproduction of the drive (a wrong delay changes
the fork's reaction, so the replayed trajectory drifts) -- that turns the BELIEF into a measurement."""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402


def r2(y, yh):
    return 1 - np.sum((y - yh) ** 2) / np.sum((y - y.mean()) ** 2)


def main():
    fam = H.family()
    ch = H.route_chunks()
    d = H.route()
    meas = H.drive_metrics(H.drive_series_measured(ch))
    print("H6 SENSITIVITY  (V294 cells, nominal plant, %d chunks)" % len(ch))
    print("  measured: track %s | hard16 %s | dwell %s | slew share %s" % (
        " ".join("%.3f" % meas[b]["track_gain"] for b in meas), " ".join("%.2f" % meas[b]["hard16"] for b in meas),
        " ".join("%.1f" % meas[b]["dwell_per_min"] for b in meas), " ".join("%.4f" % meas[b]["slew_share"] for b in meas)))
    for dist in ("full", "lp"):
        for pipe in (2, 12, 17, 22, 27, 32, 42, 62):
            t0 = time.time()
            R = H.simulate([H.Cells.v294()], [fam["nominal"]], ch, H.SimOpts(mode="B", dist=dist, pipe_ms=pipe))
            ra, rr, rc = [], [], []
            for j, (a, b) in enumerate(ch):
                n = b - a
                ra.append(r2(d["th"][a:b], R["ang"][j, :n]))
                rr.append(r2(d["x18_f"][a:b] / 8.0, R["rate18"][j, :n]))
                rc.append(r2(d["e4_f"][a:b], R["cmd"][j, :n]))
            sm = H.drive_metrics(H.drive_series_sim(R, list(range(len(ch)))))
            lc = H.limit_cycle_peak(R, list(range(len(ch))))
            print("  dist %-4s pipe %2d ms: angle R2 %.4f rate R2 %.4f cmd R2 %.4f | track %s | hard16 %s | slew %s | lc %.2f Hz %+.1f dB (%.0f s)"
                  % (dist, pipe, np.median(ra), np.median(rr), np.median(rc), " ".join("%.3f" % sm[b]["track_gain"] for b in sm),
                     " ".join("%.2f" % sm[b]["hard16"] for b in sm), " ".join("%.4f" % sm[b]["slew_share"] for b in sm),
                     lc["f"], lc["dB"], time.time() - t0))
    for xn in (0.0, 1.93, 4.0):
        R = H.simulate([H.Cells.v294()], [fam["nominal"]], ch, H.SimOpts(mode="B", dist="full", x_noise=xn))
        sm = H.drive_metrics(H.drive_series_sim(R, list(range(len(ch)))))
        print("  dist full x_noise %.2f: dwell/min %s  r_hi %s" % (xn, " ".join("%.1f" % sm[b]["dwell_per_min"] for b in sm),
                                                               " ".join("%.2f" % sm[b]["r_hi"] for b in sm)))


if __name__ == "__main__":
    main()
