# -*- coding: utf-8 -*-
"""tune_v282_crux.py -- the two crux checks the (A)/(B) answer rests on.

I. IS THE INTEGRATOR UNSATURATED?  The whole "gain cannot move the DC equilibrium" argument is
   that the integrator drives `error` to zero *while it has headroom*.  Its limits are
   +-lateral_accel_from_torque(+-1.0) = +-latAccelFactor = +-2.11 (latcontrol_torque.update_limits).
   If |i| lives far from that bound and `saturated` is rare, the loop is integral-closed and the
   equilibrium is set by the MEASUREMENT, not by kp / LAF / friction.  If it is pinned, gain matters.

J. IS THERE A DISCRETE 3.9 Hz RESONANCE ON V282-CLASS ROUTES?  The 2026-09-02 back-calc prescribed
   cutting loop gain for one.  A prescription needs a target.  Discriminators:
     - peak PICKING on the engaged PSD (a resonance is a local maximum, not a shelf)
     - ENGAGED vs MANUAL on the same route (a closed-loop resonance must be engagement-gated)
   Instrument: the SR-free road lateral accel, v*yaw_cal - g sin(roll).

Run: python rlog-tools/studies/optune-v282/tune_v282_crux.py
"""
import os
import sys

import numpy as np
from scipy import signal as sg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tune_v282 as T  # noqa: E402

OUT = os.path.join(HERE, "_scratch")
_LINES = []


def pr(s=""):
    print(s)
    _LINES.append(s)


def manual(g, vmin=15.0):
    """Moving, calibrated, but lateral NOT engaged -- the control arm for engagement gating."""
    return ((g["lat"] < 0.5) & (g["cal_ok"] > 0.5) & (g["v"] > vmin) & np.isfinite(g["pose"]))


def main():
    Gs = {t: T.load(t) for t, _l, _s, _k in T.ARMS}

    pr("=" * 104)
    pr("CRUX CHECKS behind the V282 tune recommendation")
    pr("=" * 104)
    pr("")
    pr("-" * 104)
    pr("I. INTEGRATOR HEADROOM -- is the loop integral-closed?")
    pr("-" * 104)
    pr("   PID limits are +-lateral_accel_from_torque(+-1.0) = +-latAccelFactor = +-2.110")
    pr("   (latcontrol_torque.update_limits).  'i at rail' = fraction of engaged frames with")
    pr("   |i| > 0.95*2.110.  'saturated' = controlsState.saturated.")
    pr("   If the integrator has headroom, `error` -> 0 and the DC equilibrium is MEASUREMENT-set:")
    pr("   no value of SteerKP / SteerLatAccel / SteerFriction can move it.")
    pr("")
    pr("   %-6s %9s %9s %9s %9s %10s %10s %9s" %
       ("route", "|i| p50", "|i| p90", "|i| p99", "max |i|", "i at rail", "saturated", "med err"))
    for tag, _l, _s, _k in T.ARMS:
        g = Gs[tag]
        b = T.eng(g)
        ai = np.abs(g["i"][b])
        pr("   %-6s %9.3f %9.3f %9.3f %9.3f %9.2f%% %9.2f%% %9.3f" %
           (tag, np.percentile(ai, 50), np.percentile(ai, 90), np.percentile(ai, 99), ai.max(),
            100.0 * np.mean(ai > 0.95 * 2.110), 100.0 * np.mean(g["saturated"][b] > 0.5),
            T.med(g["error"][b])))
    pr("")
    pr("   And the error itself, relative to what is being asked (engaged frames):")
    pr("   %-6s %11s %11s %11s %11s" % ("route", "med |err|", "med |f|", "|err|/|f|", "med signed err"))
    for tag, _l, _s, _k in T.ARMS:
        g = Gs[tag]
        b = T.eng(g)
        me, mf = T.med(np.abs(g["error"][b])), T.med(np.abs(g["f"][b]))
        pr("   %-6s %11.3f %11.3f %11.3f %11.3f" % (tag, me, mf, me / mf, T.med(g["error"][b])))
    pr("")

    pr("-" * 104)
    pr("J. IS THE 3.9 Hz LINE REAL ON V282-CLASS ROUTES?")
    pr("-" * 104)
    pr("   J1. peak picking on the ENGAGED PSD of the SR-free road lateral accel, 1-12 Hz.")
    pr("       A resonance is a LOCAL MAXIMUM with prominence over its own shoulders; a monotone")
    pr("       decay with no local max is a shelf, and a gain cut has no line to attack.")
    pr("")
    for tag, lab, _s, _k in T.ARMS:
        g = Gs[tag]
        b = T.eng(g)
        segs = T.runs_of(b, int(20 * T.FS))
        if not segs:
            continue
        y = np.concatenate([g["pose"][i:j + 1] for i, j in segs])
        f, P = sg.welch(y, T.FS, nperseg=2048)
        m = (f >= 1.0) & (f <= 12.0)
        fb, Pb = f[m], P[m]
        pk, props = sg.find_peaks(np.log(Pb), prominence=1.0)
        pr("   %-6s (%s)  %d s engaged in runs >= 20 s" % (tag, lab, len(y) / T.FS))
        if len(pk) == 0:
            pr("          NO peak with prominence > x2.7 over its shoulders, 1-12 Hz")
        else:
            order = np.argsort(props["prominences"])[::-1][:5]
            for k in order:
                pr("          peak %5.2f Hz   PSD %9.2e   x%.1f over shoulders%s" %
                   (fb[pk[k]], Pb[pk[k]], np.exp(props["prominences"][k]),
                    "   <-- dominant" if k == order[0] else ""))
        k39 = int(np.argmin(np.abs(fb - 3.9)))
        kmax = int(np.argmax(Pb))
        pr("          3.9 Hz PSD %9.2e = %.3f x the band's own maximum (%.2f Hz, %9.2e)" %
           (Pb[k39], Pb[k39] / Pb[kmax], fb[kmax], Pb[kmax]))
    pr("")
    pr("   J2. ENGAGED vs MANUAL on the same route -- a closed-loop resonance MUST be engagement-gated.")
    pr("       Ratio > 1 at a band means engagement puts energy there.")
    pr("")
    pr("   %-6s %9s %9s | %9s %9s %9s %9s %9s" %
       ("route", "eng s", "man s", "1.5Hz", "2.5Hz", "3.9Hz", "5Hz", "7Hz"))
    for tag, _l, _s, _k in T.ARMS:
        g = Gs[tag]
        be, bm = T.eng(g), manual(g)
        se = T.runs_of(be, int(20 * T.FS))
        sm = T.runs_of(bm, int(20 * T.FS))
        if not se or not sm:
            pr("   %-6s %9.0f %9.0f | (insufficient manual exposure for a control)" %
               (tag, be.sum() / T.FS, bm.sum() / T.FS))
            continue
        ye = np.concatenate([g["pose"][i:j + 1] for i, j in se])
        ym = np.concatenate([g["pose"][i:j + 1] for i, j in sm])
        f, Pe = sg.welch(ye, T.FS, nperseg=2048)
        _, Pm = sg.welch(ym, T.FS, nperseg=2048)
        cells = []
        for hz in (1.5, 2.5, 3.9, 5.0, 7.0):
            k = int(np.argmin(np.abs(f - hz)))
            cells.append(Pe[k] / Pm[k])
        pr("   %-6s %9.0f %9.0f | %9.2f %9.2f %9.2f %9.2f %9.2f" %
           (tag, len(ye) / T.FS, len(ym) / T.FS, *cells))
    pr("")
    pr("   J3. for scale: the 20 Hz creep grind and the 7 Hz strong-turn ring are the symptoms the")
    pr("       operator actually reports.  openpilot's command authority dies above ~1.5-2 Hz")
    pr("       (STEER_DELTA = 3 counts/frame = 0.33 s full-scale slew; jerk_filter at 1.2 Hz),")
    pr("       so nothing openpilot-side can put or remove energy at 3.9 Hz either way.")
    pr("")

    with open(os.path.join(OUT, "tune_v282_crux.txt"), "w") as fh:
        fh.write("\n".join(_LINES) + "\n")
    print("\nwrote %s" % os.path.join(OUT, "tune_v282_crux.txt"))


if __name__ == "__main__":
    main()
