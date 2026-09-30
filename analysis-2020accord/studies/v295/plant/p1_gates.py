# -*- coding: utf-8 -*-
"""p1_gates.py -- instrument gates G1/G2 of CRITERIA-plant.md, the physical sign of the trim, and the torque alignment
cross-check.  python p1_gates.py  -> p1_gates_out.txt

G1  tap vs the byte-exact live march (hands-off engaged, by band); and vs the null march (the trim's contribution)
G2  d(th)/dt vs om (slope, lag, phase)
SIGN  the trim must OPPOSE wheel acceleration: T_trim (+ = right) must correlate POSITIVELY with al (+ = left accel)
ALIGN the tap tick offset fitted three ways: live march / null march on low-|al| frames / (record) V293 FF-only = -4 ms
"""
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plib as P  # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def main():
    d = P.load()
    j = d["j100"]
    tt = d["tick_tap"]
    ho_tap = d["ho"][j]
    eng_tap = d["eng"][j]
    Tq_live = P.quant(d["T1k_live"][tt])
    Tq_null = P.quant(d["T1k_null"][tt])
    pr("G1. tap vs byte-exact march (tick offset %+d ms, sign %+d), rms counts" % (d["dms"], d["sg"]))
    pr("    %-8s %8s %10s %10s %10s %8s" % ("band", "tap s", "live", "null", "tap rms", "R2 live"))
    for nm, lo, hi in (("all",) + (0, 99),) + P.BANDS:
        mm = ho_tap & (d["v"][j] >= lo) & (d["v"][j] < hi)
        if mm.sum() < 100:
            continue
        rl = np.sqrt(np.mean((d["T_tap"] - Tq_live)[mm] ** 2))
        rn = np.sqrt(np.mean((d["T_tap"] - Tq_null)[mm] ** 2))
        y = d["T_tap"][mm]
        r2 = 1 - np.sum((y - Tq_live[mm]) ** 2) / np.sum((y - y.mean()) ** 2)
        pr("    %-8s %8.0f %10.2f %10.2f %10.1f %8.4f" % (nm, mm.sum() / 50, rl, rn, np.sqrt(np.mean(y ** 2)), r2))
    pr("    G1 %s (criterion: live rms <= 10 counts hands-off engaged)" % ("PASS" if d["tap_resid_rms_ho"] <= 10 else "FAIL"))
    # alignment cross-check: null march on low-acceleration frames
    alf = np.abs(P.lp1(d["al"], 5.0))[j]
    low = ho_tap & (alf < 10)
    best = None
    for dd in range(-20, 21):
        tk = np.clip(10 * j + d["sub"] + dd, 0, len(d["T1k_null"]) - 1)
        v = np.var((d["T_tap"] - P.quant(d["T1k_null"][tk]))[low])
        if best is None or v < best[0]:
            best = (v, dd)
    pr("ALIGN. tick offset: live march (all hands-off) %+d ms ; null march on |al|<10 deg/s^2 frames %+d ms (n %d) ;"
       " record V293 FF-only -4 ms" % (d["dms"], best[1], low.sum()))
    # G2
    m = d["ho"]
    dth = np.gradient(d["th"]) * 100
    k = np.polyfit(d["om"][m], dth[m], 1)
    f, Pxy = signal.csd(np.nan_to_num(d["om"]), np.nan_to_num(dth), fs=100, nperseg=1024)
    _, Pxx = signal.welch(np.nan_to_num(d["om"]), fs=100, nperseg=1024)
    ph = {ff: np.degrees(np.angle(Pxy[np.argmin(abs(f - ff))] / Pxx[np.argmin(abs(f - ff))])) for ff in (0.5, 1, 2, 5)}
    pr("G2. d(th)/dt = %.4f*om %+.3f on hands-off engaged frames ; phase(dth/om) %s deg -> %s" % (
        k[0], k[1], {a: round(b, 1) for a, b in ph.items()}, "PASS" if abs(k[0] - 1) < 0.02 else "FAIL"))
    # SIGN of the trim vs acceleration (model trim at 100 Hz)
    tr = d["T_trim"]
    for lag in (0, 2, 5, 10):
        c = np.corrcoef(tr[m][lag:], d["al"][m][:len(tr[m]) - lag])[0, 1]
        pr("SIGN. corr(T_trim[k], al[k-%d]) on hands-off engaged: %+.3f" % (lag, c))
    # the same from the MEASURED residual (tap - null) at the tap instants
    res = d["T_tap"] - Tq_null
    alt = d["al"][j]
    pr("SIGN. corr(tap - null march, al) at the tap instants, hands-off engaged: %+.3f  (+ = trim opposes acceleration)" % (
        np.corrcoef(res[ho_tap], alt[ho_tap])[0, 1]))
    # clamp binding
    r26 = d["r26_1k"]
    eng1k = np.repeat(d["eng"], 10)[:len(r26)]
    ho1k = np.repeat(d["ho"], 10)[:len(r26)]
    pr("CLAMP. |r26| == 1024 on %.4f %% of engaged ticks (%d ticks), %.4f %% of hands-off engaged ; max |r26| engaged %d ;"
       " p99.9 |r26| %.0f" % (100 * np.mean(np.abs(r26[eng1k]) >= 1024), np.sum(np.abs(r26[eng1k]) >= 1024),
                               100 * np.mean(np.abs(r26[ho1k]) >= 1024), np.max(np.abs(r26[eng1k])),
                               np.percentile(np.abs(r26[eng1k]), 99.9)))
    Pp = d["P_1k"]
    pr("CLAMP. |P| == 15360 (P clamp) on %.4f %% of engaged ticks" % (100 * np.mean(np.abs(Pp[eng1k]) >= 15360)))
    # where does the clamp bind (speed, pressed)
    bind = np.flatnonzero(eng1k & (np.abs(r26) >= 1024)) // 10
    if len(bind):
        pr("CLAMP. binding frames: v p50 %.1f m/s, pressed share %.2f, hands-off share %.2f, |om| p50 %.0f deg/s" % (
            np.median(d["v"][bind]), np.mean(d["pressed"][bind]), np.mean(d["ho"][bind]), np.median(np.abs(d["om"][bind]))))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p1_gates_out.txt"), "w", encoding="utf-8").write(
        "\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
