# -*- coding: utf-8 -*-
"""aw5_metric_scatter.py -- ADV "wiring+observability", W10: the design's EXPECTED band values come from the harness's
H.drive_metrics (f13), but its one-drive SCATTER (+-0.06 tracking, +-0.12-0.15 turn-hold) is quoted from ADV-B b7, a
different implementation (10-15 m/s r71b tracking 0.583 in f13 vs 0.691 in b7).  This measures the scatter of the SAME
metric the expectations use: drive-vs-drive (d-v-d) differences between two pseudo-drives built by resampling r71b's
harness chunks until the band holds E seconds.  Within-route resampling = a LOWER bound on real scatter.
ANALYSIS ONLY.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "fork-config"))
import fc_lib as F  # noqa: E402

H = F.H
LOG = []


def pr(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


ch = H.route_chunks()
S = H.drive_series_measured(ch)
full = H.drive_metrics(S, band_list=F.BANDS_X)
pr("harness chunks: %d, lengths s p50 %.0f max %.0f" % (len(ch), np.median([(b - a) / 100 for a, b in ch]),
                                                      max((b - a) / 100 for a, b in ch)))
bands = {nm: (lo, hi) for nm, lo, hi in F.BANDS_X}
rng = np.random.default_rng(7)
PRED = {"15-22": dict(track_gain=(0.087, 0.103), turn_hold=(0.074, 0.157)),
        "8-22": dict(track_gain=(0.057, 0.068), turn_hold=(0.047, 0.112)),
        "22+": dict(track_gain=(0.032, 0.045), turn_hold=(0.020, 0.045)),
        "10-15": dict(track_gain=(0.042, 0.063), turn_hold=(0.000, 0.048))}


def sec_in(j, lo, hi):
    v = S["v"][j]
    return float(((v >= lo) & (v < hi)).sum()) / 100.0


def pseudo(nm, E):
    lo, hi = bands[nm]
    el = [j for j in range(len(ch)) if sec_in(j, lo, hi) >= 1.0]
    pick, t = [], 0.0
    while t < E:
        j = el[rng.integers(0, len(el))]
        pick.append(j)
        t += sec_in(j, lo, hi)
    sub = {k: [S[k][j] for j in pick] for k in S}
    m = H.drive_metrics(sub, band_list=[(nm, lo, hi)])
    return m.get(nm, {})


for nm in ("10-15", "15-22", "22+", "8-22"):
    for E in (60, 120):
        d = {"track_gain": [], "turn_hold": []}
        for _ in range(300):
            a, b = pseudo(nm, E), pseudo(nm, E)
            for k in d:
                if k in a and k in b and np.isfinite(a[k]) and np.isfinite(b[k]):
                    d[k].append(b[k] - a[k])
        row = []
        for k in ("track_gain", "turn_hold"):
            x = np.array(d[k])
            if len(x) < 50:
                row.append("%s: n/a (%d)" % (k, len(x)))
                continue
            lo90, hi90 = np.percentile(x, [5, 95])
            plo, phi = PRED[nm][k]
            # P(one drive shows a rise > the 95th pct of no-change) if the true effect is the predicted lower / upper end
            pw = [float(np.mean(x + eff > hi90)) for eff in (plo, phi)]
            row.append("%s d-v-d 90%% [%+.3f, %+.3f] (n %d) ; predicted %+.3f..%+.3f -> power %.2f..%.2f"
                       % (k, lo90, hi90, len(x), plo, phi, pw[0], pw[1]))
        pr("   %-6s E %3d s | r71b %.3f / %.3f | %s" % (nm, E, full[nm]["track_gain"], full[nm]["turn_hold"], " | ".join(row)))
open(os.path.join(HERE, "out", "aw5_metric_scatter_out.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
