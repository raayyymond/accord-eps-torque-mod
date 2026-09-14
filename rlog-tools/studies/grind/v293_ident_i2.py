# -*- coding: utf-8 -*-
"""v293_ident_i2.py -- the 1-4 Hz object, with the SAME estimator run on the reference routes.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

🛑 WHY THIS EXISTS.  The flight-read scorer flags a "coherent 1-4 Hz line" in command and angle at
0-5 m/s (3.55 deg) and 10-20 m/s (0.56 deg) as its one fired revert trigger.  Amplitude in a band is
not the same question as "is there a LINE there".  My first prominence estimate used a flat baseline
over 0.5-8 Hz and returned 16-21 dB on every route and band -- which is the 1/f slope of the steering
spectrum being scored as a peak, not a peak.  The estimator here fits a straight line in log-log to
the SHOULDERS either side of the band (0.6-0.9 Hz and 4-7 Hz) and measures the peak above that line.

This script runs that estimator, and the band amplitude, identically on r70 and on three references,
so the orchestrator can see whether the elevation is a LINE or simply more steering activity.
The pre-registered band score remains the scorer's; this is the shape question, not the level.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V280 = os.path.join(L.KIT, "analysis-2020accord", "_scratch", "cache", "v280")
OUT = []
pr = L.pr_factory(OUT)
DT = 0.01
RES = {}
BANDS = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0)]
BNAME = ["0-5", "5-10", "10-20", ">20"]
ROUTES = [("r70_v293", "V293"), ("r6c", "V282"), ("r39", "V282"), ("r35", "V281r3")]


def load(tag):
    d = dict(np.load(os.path.join(V280, tag + ".npz")))
    t0 = d["t18"][0]
    t1 = min(d["t18"][-1], d["t14"][-1], d["te4"][-1], d["tcs"][-1])
    ta = np.arange(0.0, t1 - t0, DT) + t0
    return dict(ang=L.zoh(ta, d["t14"], d["ang"]), cmd=L.zoh(ta, d["te4"], d["cmd"]),
                v=L.zoh(ta, d["tcs"], d["vego"]), rate=L.zoh(ta, d["t18"], d["rate"]) / 8.0,
                eng=(L.zoh(ta, d["te4"], d["req"]) > 0.5) & (L.zoh(ta, d["t18"], d["sca"]) > 0.5))


pr("=" * 108)
pr("V293 -- IS THE 1-4 Hz OBJECT A LINE?  the same estimator on r70 and three references")
pr("=" * 108)
pr("\n    PROMINENCE = the 1-4 Hz peak above a log-log straight line fitted to the 0.6-0.9 Hz and")
pr("    4-7 Hz shoulders.  Under ~3 dB there is no peak: the band is just the tail of the steering")
pr("    spectrum.  Amplitude is the rms of the 1-4 Hz content, for comparison with the scorer's.")
pr("\n    %-10s %-8s %-8s %8s %9s %12s %12s %12s"
   % ("route", "build", "band", "sec", "peak Hz", "PROMINENCE", "ang 1-4 deg", "cmd 1-4 cnt"))
for tag, build in ROUTES:
    try:
        g = load(tag)
    except Exception as ex:
        pr("    %s: %s" % (tag, str(ex)[:60])); continue
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        m = g["eng"] & (g["v"] >= lo) & (g["v"] < hi)
        runs = L.stretches(m, 512)
        if not runs:
            continue
        Pa = Pc = None
        nn = 0
        for (a, b) in runs:
            f_, p1 = signal.welch(signal.detrend(g["ang"][a:b]), fs=100.0, nperseg=512, noverlap=256)
            _, p2 = signal.welch(signal.detrend(g["cmd"][a:b]), fs=100.0, nperseg=512, noverlap=256)
            w = b - a
            Pa = p1 * w if Pa is None else Pa + p1 * w
            Pc = p2 * w if Pc is None else Pc + p2 * w
            nn += w
        Pa /= nn; Pc /= nn
        sel = (f_ >= 1.0) & (f_ < 4.0)
        sh = ((f_ >= 0.6) & (f_ <= 0.9)) | ((f_ >= 4.0) & (f_ <= 7.0))
        A_ = np.vstack([np.log10(f_[sh]), np.ones(sh.sum())]).T
        cf = np.linalg.lstsq(A_, 10 * np.log10(Pa[sh] + 1e-30), rcond=None)[0]
        fpk = f_[sel][int(np.argmax(Pa[sel]))]
        prom = 10 * np.log10(Pa[sel].max() + 1e-30) - (cf[0] * np.log10(fpk) + cf[1])
        amp = np.sqrt(np.sum(Pa[sel]) * (f_[1] - f_[0]))
        ampc = np.sqrt(np.sum(Pc[sel]) * (f_[1] - f_[0]))
        pr("    %-10s %-8s %-8s %8.0f %9.2f %12.2f %12.4f %12.2f"
           % (tag, build, BNAME[k], nn * DT, fpk, prom, amp, ampc))
        RES.setdefault(tag, {})[BNAME[k]] = dict(sec=nn * DT, f=float(fpk), prom=float(prom),
                                                 amp=float(amp), ampc=float(ampc))

pr("\n    AND THE SAME BAND ON THE WHEEL RATE, where the 0.1 deg angle quantiser cannot reach:")
pr("    %-10s %-8s" % ("route", "build") + "".join("%14s" % b for b in BNAME))
for tag, build in ROUTES:
    try:
        g = load(tag)
    except Exception:
        continue
    row = []
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        m = g["eng"] & (g["v"] >= lo) & (g["v"] < hi)
        runs = L.stretches(m, 512)
        if not runs:
            row.append(np.nan); continue
        P = None; nn = 0
        for (a, b) in runs:
            f_, p = signal.welch(signal.detrend(g["rate"][a:b]), fs=100.0, nperseg=512, noverlap=256)
            P = p * (b - a) if P is None else P + p * (b - a)
            nn += (b - a)
        P /= nn
        sel = (f_ >= 1.0) & (f_ < 4.0)
        row.append(float(np.sqrt(np.sum(P[sel]) * (f_[1] - f_[0]))))
    pr("    %-10s %-8s" % (tag, build) + "".join("%14.4f" % x for x in row))

with open(os.path.join(L.SCRATCH, "v293_ident_i2.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_i2.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_i2.txt / .json")
