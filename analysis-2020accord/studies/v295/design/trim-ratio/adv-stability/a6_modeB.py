# -*- coding: utf-8 -*-
"""a6_modeB.py -- (c)/(e) closed-loop replay with the (bit-verified) fork port on the members the designer did NOT run
in mode B (the stress members mode13 / mode20 / mode20_lo, tau9, J_0.3) plus nominal / light_b / tau6 / b_lo anchors,
V294 and b964 in ONE batch, dist lp and full.  Also: harness spot check = V294 nominal lp tracking gain per band vs
the harness report (0.840 / 0.865 / 0.586 / 0.764 / 0.917).  Delivered-torque HF bands from the 1 kHz trace, and a
13-25 Hz wheel-rate line search on the 1 kHz x.  Output: a6_modeB_out.txt, a6_modeB.json"""
import json
import os
import sys
import time

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import v295_harness as H  # noqa: E402

out = open(os.path.join(HERE, "a6_modeB_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


BASE = H.Cells.v294()
CAND = BASE.replace(fb_b=964, name="b964")
fam = H.family()
PLANTS = ("nominal", "light_b", "tau6", "tau9", "b_lo", "J_0.3", "mode13", "mode20", "mode20_lo")
members = [fam[p] for p in PLANTS]
chunks = H.route_chunks()
P("chunks", len(chunks), "seconds", sum(b - a for a, b in chunks) / 100.0)
res = {}
BANDS_HF = ((5, 9), (9, 13), (13, 17), (17, 23), (23, 30))
for dist in ("lp", "full"):
    t0 = time.time()
    R = H.simulate([BASE, CAND], members, chunks, H.SimOpts(mode="B", dist=dist), record_1k=True)
    P("dist", dist, "sim %.0f s" % (time.time() - t0), "bails", int(R["n_bail"].sum()))
    nM, nK = len(members), len(chunks)
    for ci, c in enumerate((BASE, CAND)):
        for mi, p in enumerate(PLANTS):
            rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
            dm = H.drive_metrics(H.drive_series_sim(R, rows))
            dm["limit_cycle"] = H.limit_cycle_peak(R, rows)
            # HF delivered torque (1 kHz) and a 12-26 Hz wheel-rate line (100 Hz x)
            hf = np.zeros(len(BANDS_HF))
            Pw, fw = 0, None
            for j in rows:
                n = R["lens"][j] * 10
                T = R["T1k"][j, :n].astype(float)
                for bi, (lo, hi) in enumerate(BANDS_HF):
                    b_, a_ = signal.butter(2, [lo / 500.0, hi / 500.0], btype="band")
                    y = signal.filtfilt(b_, a_, T - T.mean())[500:-500]
                    hf[bi] += np.sum(y ** 2)
                xr = R["x"][j, :R["lens"][j]] / 8.0
                if len(xr) > 1100:
                    fw, pw = signal.welch(xr - xr.mean(), fs=100.0, nperseg=512)
                    Pw = Pw + pw
            tot = sum((R["lens"][j] * 10 - 1000) for j in rows)
            dm["hf"] = list(np.sqrt(hf / tot))
            m = (fw >= 12) & (fw <= 26)
            k = np.flatnonzero(m)[int(np.argmax(Pw[m]))]
            sh = ((fw >= 8) & (fw < 12)) | ((fw > 26) & (fw <= 34))
            cf = np.polyfit(np.log(fw[sh]), np.log(Pw[sh] + 1e-30), 1)
            dm["hfline"] = dict(f=float(fw[k]), dB=float(10 * np.log10(Pw[k] / np.exp(np.polyval(cf, np.log(fw[k]))))),
                                rms1226=float(np.sqrt(np.trapezoid(Pw[m], fw[m]) / nK)))
            res[(dist, c.name, p)] = dm
    del R
json.dump({"|".join(k): v for k, v in res.items()}, open(os.path.join(HERE, "a6_modeB.json"), "w"), default=float)

P()
P("SPOT CHECK (harness retrodiction row): V294 nominal lp tracking gain per band:",
  [round(res[("lp", "V294", "nominal")][b]["track_gain"], 4) for b in ("0-5", "5-10", "10-15", "15-22", "22+")],
  " report: 0.840 / 0.865 / 0.586 / 0.764 / 0.917")
BN = ("0-5", "5-10", "10-15", "15-22", "22+")
RATIO = ("hard16", "r_lo", "r_mid", "r_hi", "J_err", "cmd_rms")
DIFF = ("track_gain", "turn_hold", "straight_delivery", "i_share")
for dist in ("lp", "full"):
    P()
    P("=== dist %s : b964 vs V294 per member (ratio for rates/errors, difference for outer metrics)" % dist)
    for p in PLANTS:
        a, b = res[(dist, "V294", p)], res[(dist, "b964", p)]
        line = []
        for key in RATIO + DIFF:
            cells = []
            for bn in BN:
                if bn in a and bn in b and np.isfinite(a[bn][key]) and np.isfinite(b[bn][key]):
                    v = b[bn][key] / a[bn][key] if key in RATIO else b[bn][key] - a[bn][key]
                    cells.append(("%.2f" if key in RATIO else "%+.3f") % v)
                else:
                    cells.append(" n/t ")
            line.append("%s %s" % (key, "/".join(cells)))
        P("  %-10s " % p + " | ".join(line))
        P("  %-10s limit-cycle 1-5 Hz: V294 %.2f Hz %+.1f dB rms %.3f -> b964 %.2f Hz %+.1f dB rms %.3f ;  12-26 Hz line: "
          "V294 %.1f Hz %+.1f dB rms %.3f -> b964 %.1f Hz %+.1f dB rms %.3f ; HF T 5-9/9-13/13-17/17-23/23-30 x %s" % (
              "", a["limit_cycle"]["f"], a["limit_cycle"]["dB"], a["limit_cycle"]["rms"], b["limit_cycle"]["f"],
              b["limit_cycle"]["dB"], b["limit_cycle"]["rms"], a["hfline"]["f"], a["hfline"]["dB"], a["hfline"]["rms1226"],
              b["hfline"]["f"], b["hfline"]["dB"], b["hfline"]["rms1226"],
              "/".join("%.2f" % (x1 / max(x0, 1e-9)) for x0, x1 in zip(a["hf"], b["hf"]))))
out.close()
