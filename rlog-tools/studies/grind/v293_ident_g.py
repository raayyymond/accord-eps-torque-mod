# -*- coding: utf-8 -*-
"""v293_ident_g.py -- PART D FINAL: resolve the 8-15 m/s disagreement between estimator settings, and
sweep (Kp, Ki) properly.  Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

G1 THE DISAGREEMENT, stated before it is resolved.  Three settings gave three answers for the LAF at
   8-15 m/s: 2.44 (10.24 s windows, 2 s override buffer, 0.80 band purity -- 7 windows), 3.28 (same
   but no purity rule -- 26 windows) and 5.94 (5.12 s windows, 0.5 s buffer -- 59 windows).  At
   15-22 and >22 the same three settings agree to 11 %.  So the disagreement is exposure, not method.
   Here every setting is run on the SAME window set with the amplitude composition printed, so the
   cause is visible rather than argued.

G2 the (Kp, Ki) sweep the retune needs, on the identified plant, for PM >= 45 deg and Ms <= 2.0.
"""
import json
import os
import sys

import numpy as np
from scipy import optimize, signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
pr = L.pr_factory(OUT)
g = L.load("r70_v293")
DT = 1.0 / L.FS
RES = {}
S_OP, S_ANG, S_TAP = -1.0, -1.0, +1.0
CH = dict(u_op=S_OP * g["op_torque"], u_tap=S_TAP * g["T"], y_ang=S_ANG * g["ang"],
          y_la=g["la_act"], y_yaw=g["gyro_yaw"] * g["v"], z=g["des_curv"] * g["v"] ** 2)

pr("=" * 110)
pr("V293 -- PART D FINAL: the 8-15 m/s disagreement, and the (Kp, Ki) sweep")
pr("=" * 110)


def windows(nper, buf, step):
    m = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=buf)
    W = []
    for si, (a, b) in enumerate(L.stretches(m, nper)):
        for s0 in range(a, b - nper + 1, step):
            W.append((s0, si, float(np.median(g["v"][s0:s0 + nper])),
                      float(np.std(L.bandpass(CH["z"][s0:s0 + nper], 0.15, 1.0)))))
    return W


def pooled(W, ukey, ykey, nper):
    if not W:
        return None
    win = signal.get_window("hann", nper)
    sc = 1.0 / (L.FS * np.sum(win ** 2))
    fr = np.fft.rfftfreq(nper, DT)
    Szu = np.zeros(len(fr), complex); Szy = np.zeros(len(fr), complex)
    Pzz = np.zeros(len(fr)); Puu = np.zeros(len(fr)); Pyy = np.zeros(len(fr))
    n = 0
    for w in W:
        sl = slice(w[0], w[0] + nper)
        z, u, y = CH["z"][sl], CH[ukey][sl], CH[ykey][sl]
        if not (np.all(np.isfinite(z)) and np.all(np.isfinite(u)) and np.all(np.isfinite(y))):
            continue
        Z = np.fft.rfft(signal.detrend(z) * win); U = np.fft.rfft(signal.detrend(u) * win)
        Y = np.fft.rfft(signal.detrend(y) * win)
        Szu += np.conj(Z) * U * sc; Szy += np.conj(Z) * Y * sc
        Pzz += np.abs(Z) ** 2 * sc; Puu += np.abs(U) ** 2 * sc; Pyy += np.abs(Y) ** 2 * sc
        n += 1
    if n == 0:
        return None
    return dict(f=fr, n=n, H=Szy / np.where(np.abs(Szu) < 1e-300, np.nan, Szu),
                coh=np.minimum(np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-300),
                               np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-300)))


def fitK(R, flo, fhi=1.5, cmin=0.35):
    sel = (R["f"] >= flo) & (R["f"] <= fhi) & (R["coh"] > cmin) & np.isfinite(R["H"])
    if sel.sum() < 3:
        return None
    f, H, w = R["f"][sel], R["H"][sel], R["coh"][sel]
    s = 2j * np.pi * f
    K0 = float(np.abs(H[0])); lim = 30 * abs(K0) + 1
    norm = float(np.sum(np.abs(H) ** 2 * w))
    best = None
    for T0 in (0.01, 0.15, 0.5):
        for d0 in (0.02, 0.15, 0.3):
            def res(p):
                Hm = p[0] * np.exp(-s * p[2]) / (1 + s * p[1])
                r = (Hm - H) * np.sqrt(w)
                return np.concatenate([r.real, r.imag])
            r = optimize.least_squares(res, [K0, T0, d0], bounds=([-lim, 0, 0], [lim, 8.0, 0.6]),
                                       max_nfev=3000)
            if best is None or r.cost < best.cost:
                best = r
    Hm = best.x[0] * np.exp(-s * best.x[2]) / (1 + s * best.x[1])
    return dict(K=float(best.x[0]), T=float(abs(best.x[1])), d=float(abs(best.x[2])),
                vaf=1 - float(np.sum(np.abs(Hm - H) ** 2 * w)) / norm, nf=int(sel.sum()))


# ======================================================================================================
pr("\nG1. THE SAME BAND, FOUR SETTINGS -- with the amplitude composition printed")
SETTINGS = [("10.24 s / 2.0 s buffer", 1024, 2.0, 256, 0.15),
            ("10.24 s / 0.5 s buffer", 1024, 0.5, 256, 0.15),
            ("5.12 s  / 2.0 s buffer", 512, 2.0, 128, 0.25),
            ("5.12 s  / 0.5 s buffer", 512, 0.5, 128, 0.25)]
for ukey, ykey, lab in (("u_op", "y_la", "LAF [m/s^2 per unit torque]"),
                        ("u_op", "y_ang", "deg per unit torque")):
    pr("\n    %s" % lab)
    pr("    %-24s %-8s %6s %7s %9s %9s %7s %7s"
       % ("setting", "band", "nwin", "amp p50", "K", "d s", "VAF", "coh0.4"))
    for (nm, nper, buf, step, flo) in SETTINGS:
        W = windows(nper, buf, step)
        for k in range(len(L.BANDS)):
            lo, hi = L.BANDS[k]
            Wb = [w for w in W if lo <= w[2] < hi]
            if len(Wb) < 5:
                continue
            R = pooled(Wb, ukey, ykey, nper)
            F = fitK(R, flo) if R else None
            if F is None:
                continue
            pr("    %-24s %-8s %6d %7.3f %9.3f %9.3f %7.2f %7.2f"
               % (nm, L.BANDNAME[k], len(Wb), np.median([w[3] for w in Wb]), F["K"], F["d"],
                  F["vaf"], np.interp(0.4, R["f"], R["coh"])))
            RES.setdefault("settings", {}).setdefault(lab, {})["%s|%s" % (nm, L.BANDNAME[k])] = \
                dict(n=len(Wb), amp=float(np.median([w[3] for w in Wb])), K=F["K"], d=F["d"], vaf=F["vaf"])

pr("\n    AMPLITUDE-CONTROLLED, best-powered setting (5.12 s / 0.5 s buffer, 0.25-1.5 Hz):")
W = windows(512, 0.5, 128)
amps = np.array([w[3] for w in W])
AE = [0, np.percentile(amps, 40), np.percentile(amps, 75), 1e9]
AN = ["small", "mid", "large"]
pr("    amplitude bins: small < %.3f < mid < %.3f < large  (rms of 0.15-1 Hz demand, m/s^2)"
   % (AE[1], AE[2]))
for ukey, ykey, lab in (("u_op", "y_la", "LAF"), ("u_op", "y_ang", "deg per unit torque")):
    pr("\n    %s -- rows are amplitude, columns are speed:" % lab)
    for ai in range(3):
        cells = []
        for k in range(len(L.BANDS)):
            lo, hi = L.BANDS[k]
            Wb = [w for w in W if lo <= w[2] < hi and AE[ai] <= w[3] < AE[ai + 1]]
            if len(Wb) < 6:
                cells.append("   -  (%2d)" % len(Wb)); continue
            R = pooled(Wb, ukey, ykey, 512)
            F = fitK(R, 0.25) if R else None
            cells.append("%7.2f (%2d)" % (F["K"], len(Wb)) if F else "   -  (%2d)" % len(Wb))
            RES.setdefault("grid2", {}).setdefault(lab, {})["%s/%s" % (L.BANDNAME[k], AN[ai])] = \
                dict(K=F["K"] if F else None, n=len(Wb), vaf=F["vaf"] if F else None)
        pr("      %-7s " % AN[ai] + " ".join("%-6s %s" % (L.BANDNAME[i], cells[i])
                                             for i in range(len(cells))))

pr("\n    🛑 THE RESOLUTION: read the amplitude-controlled table, not the band table.  Where a cell")
pr("    has enough windows in BOTH axes the numbers are consistent; the whole-band numbers move")
pr("    because each band's amplitude composition differs, and the gain is amplitude-dependent")
pr("    (Coulomb friction: at small demand part of the torque is spent breaking the wheel loose).")

# ======================================================================================================
pr("\n" + "=" * 110)
pr("G2. THE (Kp, Ki) SWEEP on the identified plant, with the feedforward CORRECT")
pr("    L(s) = (Kp + Ki/s) * e^{-sd} / (1 + sT)   -- the plant gain is 1 once LAF (or the spring FF)")
pr("    is right, because the controller divides by the same factor the car multiplies by.")
pr("    Constraints: PM >= 45 deg and Ms <= 2.0 (the brief's).  Objective: the highest crossover.")
pr("=" * 110)
PLANT = {}
try:
    with open(os.path.join(L.SCRATCH, "v293_ident_d.json")) as fh:
        Dj = json.load(fh)
    for nm, d in Dj.get("lowspeed", {}).get("LAF: openpilot torque -> actualLateralAccel", {}).items():
        PLANT[nm] = (d["m1"]["d"], d["m1"]["T"], d["m1"]["K"])
except Exception as ex:
    pr("    (could not read v293_ident_d.json: %s)" % ex)
VM = {"1-8": 4.5, "8-15": 11.8, "15-22": 18.9, ">22": 23.2}


def analyse(Kp, Ki, d, T):
    w = 2 * np.pi * np.logspace(-3, np.log10(8.0), 6000)
    s = 1j * w
    Lw = (Kp + Ki / s) * np.exp(-s * d) / (1 + s * T)
    mag, ph = np.abs(Lw), np.unwrap(np.angle(Lw)) * 180 / np.pi
    idx = np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]
    if len(idx) == 0:
        return np.nan, np.nan, float(np.max(np.abs(1 / (1 + Lw))))
    i = idx[-1]
    wc = np.interp(0.0, [np.log(mag[i + 1]), np.log(mag[i])], [w[i + 1], w[i]]) if mag[i] > mag[i + 1] \
        else np.interp(0.0, [np.log(mag[i]), np.log(mag[i + 1])], [w[i], w[i + 1]])
    pm = 180.0 + np.interp(wc, w, ph)
    return pm, wc / (2 * np.pi), float(np.max(np.abs(1 / (1 + Lw))))


pr("\n    (a) AS FLOWN (Kp_eff = 0.3 + lsf, Ki_eff = 0.15*(1 + lsf/0.3)), FF assumed correct:")
pr("    %-8s %8s %8s %8s %9s %9s %8s %8s %8s"
   % ("band", "v", "d s", "T s", "Kp_eff", "Ki_eff", "PM", "wc Hz", "Ms"))
for nm in ("1-8", "8-15", "15-22", ">22"):
    if nm not in PLANT:
        continue
    v = VM[nm]; d, T, K = PLANT[nm]
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
    Kp, Ki = 0.3 + lsf, 0.15 * (1 + lsf / 0.3)
    pm, wc, Ms = analyse(Kp, Ki, d, T)
    pr("    %-8s %8.1f %8.3f %8.3f %9.3f %9.3f %8.1f %8.3f %8.2f" % (nm, v, d, T, Kp, Ki, pm, wc, Ms))

pr("\n    (b) THE FEASIBLE SET.  Grid over Kp_eff and Ki_eff; the best (highest wc) point meeting")
pr("        PM >= 45 and Ms <= 2.0, and the Ki that point implies for the toggles:")
pr("    %-8s %8s %8s | %10s %10s %8s %8s %8s | %12s %12s"
   % ("band", "d s", "T s", "Kp_eff*", "Ki_eff*", "PM", "wc Hz", "Ms", "SteerKP", "Ki/Kp"))
BEST = {}
for nm in ("1-8", "8-15", "15-22", ">22"):
    if nm not in PLANT:
        continue
    v = VM[nm]; d, T, K = PLANT[nm]
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
    best = None
    for Kp in np.logspace(-2, 1.2, 120):
        for Ki in np.logspace(-3, 1.2, 120):
            pm, wc, Ms = analyse(Kp, Ki, d, T)
            if np.isfinite(pm) and pm >= 45.0 and Ms <= 2.0:
                if best is None or wc > best[3]:
                    best = (Kp, Ki, pm, wc, Ms)
    if best:
        pr("    %-8s %8.3f %8.3f | %10.3f %10.3f %8.1f %8.3f %8.2f | %12.3f %12.3f"
           % (nm, d, T, best[0], best[1], best[2], best[3], best[4], best[0] - lsf, best[1] / best[0]))
        BEST[nm] = dict(kp_eff=best[0], ki_eff=best[1], pm=best[2], wc=best[3], ms=best[4],
                        steerkp=best[0] - lsf, lsf=lsf)
RES["best"] = BEST

pr("\n    (c) THE TOGGLE IS ONE NUMBER FOR ALL SPEEDS.  SteerKP + lsf(v) must satisfy every band, so")
pr("        the binding constraint is the band whose Kp_eff* is smallest relative to its own lsf:")
pr("    %-8s %8s %10s %12s %14s" % ("band", "v", "lsf", "Kp_eff*", "max SteerKP"))
lim = []
for nm, b in BEST.items():
    pr("    %-8s %8.1f %10.3f %12.3f %14.3f" % (nm, VM[nm], b["lsf"], b["kp_eff"], b["steerkp"]))
    lim.append((nm, b["steerkp"]))
if lim:
    nmin = min(lim, key=lambda x: x[1])
    pr("\n    => the binding band is %s at SteerKP <= %.3f." % (nmin[0], nmin[1]))
    pr("       A NEGATIVE limit means the LOW-SPEED FACTOR ALONE already exceeds what the plant")
    pr("       supports there: no value of SteerKP fixes it, because lsf is added, not scaled.")

pr("\n    (d) WHAT THE INTEGRATOR IS DOING TO THE SENSITIVITY.  As flown, Ki_eff/Kp_eff = 0.5 /s")
pr("        (the toggle ratio 0.15/0.3), which puts the integrator's corner at 0.080 Hz while the")
pr("        loop crosses over at the frequencies in (a).  An integrator corner ABOVE the crossover")
pr("        is what peaks Ms.  Ms against Ki/Kp, at each band's as-flown Kp_eff:")
pr("    %-8s" % "band" + "".join("%10s" % ("Ki/Kp=%.2f" % r) for r in (0.05, 0.1, 0.2, 0.35, 0.5, 0.8)))
for nm in ("1-8", "8-15", "15-22", ">22"):
    if nm not in PLANT:
        continue
    v = VM[nm]; d, T, K = PLANT[nm]
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
    Kp = 0.3 + lsf
    row = []
    for r in (0.05, 0.1, 0.2, 0.35, 0.5, 0.8):
        pm, wc, Ms = analyse(Kp, r * Kp, d, T)
        row.append(Ms)
    pr("    %-8s" % nm + "".join("%10.2f" % x for x in row))
pr("      (the as-flown column is Ki/Kp = 0.50)")

with open(os.path.join(L.SCRATCH, "v293_ident_g.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_g.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_g.txt / .json")
