# -*- coding: utf-8 -*-
"""v293_ident_f.py -- PART D CORE: the numbers a retune needs, and the SPEED-vs-AMPLITUDE confound.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

Three jobs:
  F1  THE CONFOUND.  B3 found LAF ~ v^1.55 AND a 2.0-2.7x gain rise from the low to the high demand
      tercile.  The low-speed cells also carry the smallest demands, so "LAF falls at low speed" and
      "LAF falls at small demand" are not separated by the band tables.  Here the windows are binned
      on BOTH axes at once.
  F2  THE FEEDFORWARD THE PLANT WANTS, in openpilot's own units: torque per degree of steering angle
      (the spring), torque per deg/s (the damper), torque (the Coulomb friction).  Fitted directly on
      u_op so no counts->torque conversion enters.
  F3  WHAT THE FORK'S OWN ACCORD PLANT FEEDFORWARD WOULD DELIVER, and the scale it needs.  The fork
      already carries the right STRUCTURE (get_honda_accord_rate_plant_ff: hold = k(v)*angle/G(v),
      move = rate_gain*d(angle)/dt/G(v)) plus two Galaxy toggles whose stated purpose is exactly this
      ("let the tables be corrected from Galaxy after an EPS firmware change").
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
S_OP, S_TAP, S_ANG, S_RATE = -1.0, +1.0, -1.0, +1.0
CH = dict(u_op=S_OP * g["op_torque"], u_tap=S_TAP * g["T"], y_ang=S_ANG * g["ang"],
          y_rate=S_RATE * g["rate_dps"], y_la=g["la_act"], y_yaw=g["gyro_yaw"] * g["v"],
          z=g["des_curv"] * g["v"] ** 2)
NPER, STEP = 1024, 256
FLO, FHI, CMIN = 0.15, 1.5, 0.35

pr("=" * 110)
pr("V293 -- PART D CORE: the retune numbers, and the speed-vs-amplitude confound")
pr("=" * 110)

mask = L.clean_mask(g, hands_off=True, min_v=1.0)
strets = L.stretches(mask, NPER)
ALLW = []
for si, (a, b) in enumerate(strets):
    for s0 in range(a, b - NPER + 1, STEP):
        ALLW.append((s0, si, float(np.median(g["v"][s0:s0 + NPER])),
                     float(np.std(L.bandpass(CH["z"][s0:s0 + NPER], 0.1, 1.0)))))
pr("\n%d windows of %.2f s from %d clean stretches." % (len(ALLW), NPER * DT, len(strets)))
win = signal.get_window("hann", NPER)
sc = 1.0 / (L.FS * np.sum(win ** 2))
fr = np.fft.rfftfreq(NPER, DT)


def pooled(W, ukey, ykey):
    if not W:
        return None
    Szu = np.zeros(len(fr), complex); Szy = np.zeros(len(fr), complex)
    Pzz = np.zeros(len(fr)); Puu = np.zeros(len(fr)); Pyy = np.zeros(len(fr))
    n = 0
    for w in W:
        s0 = w[0]
        sl = slice(s0, s0 + NPER)
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
                czu=np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-300),
                czy=np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-300))


def fitK(R, flo=FLO, fhi=FHI, cmin=CMIN):
    coh = np.minimum(R["czu"], R["czy"])
    sel = (R["f"] >= flo) & (R["f"] <= fhi) & (coh > cmin) & np.isfinite(R["H"])
    if sel.sum() < 3:
        return None
    f, H, w = R["f"][sel], R["H"][sel], coh[sel]
    s = 2j * np.pi * f
    K0 = float(np.abs(H[0])); lim = 30 * abs(K0) + 1
    norm = float(np.sum(np.abs(H) ** 2 * w))
    best = None
    for T0 in (0.01, 0.15, 0.5):
        for d0 in (0.02, 0.15, 0.3):
            r = optimize.least_squares(
                lambda p: np.concatenate([
                    (((p[0] * np.exp(-s * p[2]) / (1 + s * p[1])) - H) * np.sqrt(w)).real,
                    (((p[0] * np.exp(-s * p[2]) / (1 + s * p[1])) - H) * np.sqrt(w)).imag]),
                [K0, T0, d0], bounds=([-lim, 0, 0], [lim, 8.0, 0.6]), max_nfev=3000)
            if best is None or r.cost < best.cost:
                best = r
    Hm = best.x[0] * np.exp(-s * best.x[2]) / (1 + s * best.x[1])
    return dict(K=float(best.x[0]), T=float(abs(best.x[1])), d=float(abs(best.x[2])),
                vaf=1 - float(np.sum(np.abs(Hm - H) ** 2 * w)) / norm, nf=int(sel.sum()),
                coh=float(np.mean(w)))


# ======================================================================================================
pr("\n" + "=" * 110)
pr("F1. SPEED OR AMPLITUDE?   windows binned on BOTH at once.  'amp' is the rms of the 0.1-1 Hz")
pr("    band-passed instrument (desiredCurvature*v^2) in the window, i.e. how hard the road is")
pr("    asking.  Cells with < 6 windows are not printed.")
pr("=" * 110)
amps = np.array([w[3] for w in ALLW])
AEDGES = [0, np.percentile(amps, 40), np.percentile(amps, 75), 1e9]
ANAMES = ["small", "mid", "large"]
pr("\n    amplitude bins (rms of the band-passed demand, m/s^2): small < %.3f < mid < %.3f < large"
   % (AEDGES[1], AEDGES[2]))
for ukey, ykey, lab, fmt in (("u_op", "y_la", "LAF  [m/s^2 per unit torque]", "%10.3f"),
                             ("u_op", "y_ang", "1/spring [deg per unit torque]", "%10.1f")):
    pr("\n    %s" % lab)
    pr("    %-8s %-8s %7s %7s %10s %8s %8s %7s" % ("band", "amp", "nwin", "vmed", "K", "T s", "d s", "VAF"))
    for k in range(len(L.BANDS)):
        lo, hi = L.BANDS[k]
        for ai in range(3):
            W = [w for w in ALLW if lo <= w[2] < hi and AEDGES[ai] <= w[3] < AEDGES[ai + 1]]
            if len(W) < 6:
                continue
            R = pooled(W, ukey, ykey)
            F = fitK(R) if R else None
            if F is None:
                continue
            pr("    %-8s %-8s %7d %7.1f " % (L.BANDNAME[k], ANAMES[ai], len(W),
                                             np.median([w[2] for w in W])) + fmt % F["K"]
               + " %8.3f %8.3f %7.2f" % (F["T"], F["d"], F["vaf"]))
            RES.setdefault("grid", {}).setdefault(lab, {})["%s/%s" % (L.BANDNAME[k], ANAMES[ai])] = F

pr("\n    the same cells, pooled ACROSS speed to isolate amplitude, and ACROSS amplitude to isolate speed:")
for ukey, ykey, lab in (("u_op", "y_la", "LAF [m/s^2 per unit torque]"),
                        ("u_op", "y_ang", "deg per unit torque")):
    pr("\n    %s" % lab)
    pr("      by AMPLITUDE, all speeds pooled:")
    for ai in range(3):
        W = [w for w in ALLW if AEDGES[ai] <= w[3] < AEDGES[ai + 1]]
        R = pooled(W, ukey, ykey); F = fitK(R) if R else None
        if F:
            pr("        %-8s n %4d  vmed %5.1f   K %9.3f   d %.3f s  VAF %.2f"
               % (ANAMES[ai], len(W), np.median([w[2] for w in W]), F["K"], F["d"], F["vaf"]))
    pr("      by SPEED, all amplitudes pooled:")
    for k in range(len(L.BANDS)):
        lo, hi = L.BANDS[k]
        W = [w for w in ALLW if lo <= w[2] < hi]
        R = pooled(W, ukey, ykey); F = fitK(R) if R else None
        if F:
            pr("        %-8s n %4d  vmed %5.1f   K %9.3f   d %.3f s  VAF %.2f  (amp p50 %.3f)"
               % (L.BANDNAME[k], len(W), np.median([w[2] for w in W]), F["K"], F["d"], F["vaf"],
                  np.median([w[3] for w in W])))

pr("\n    AMPLITUDE-MATCHED SPEED CONTRAST -- the only clean read of the speed law.  Each row uses")
pr("    ONLY the windows in one amplitude bin, so the speed comparison is like-for-like:")
for ukey, ykey, lab in (("u_op", "y_la", "LAF"), ("u_op", "y_ang", "deg per unit torque")):
    pr("      %s:" % lab)
    for ai in range(3):
        row = []
        for k in range(len(L.BANDS)):
            lo, hi = L.BANDS[k]
            W = [w for w in ALLW if lo <= w[2] < hi and AEDGES[ai] <= w[3] < AEDGES[ai + 1]]
            if len(W) < 6:
                row.append("    -   "); continue
            R = pooled(W, ukey, ykey); F = fitK(R) if R else None
            row.append("%8.3f" % F["K"] if F else "    -   ")
        pr("        %-8s " % ANAMES[ai] + "  ".join("%s=%s" % (L.BANDNAME[i], row[i])
                                                    for i in range(len(row))))

# ======================================================================================================
pr("\n" + "=" * 110)
pr("F2. THE FEEDFORWARD THE PLANT WANTS, in openpilot's own torque units")
pr("    fitted directly as  u_op = a*angle + b*d(angle)/dt + F*sign(d(angle)/dt) + u0")
pr("    on the 0.5 Hz low-passed clean data, so a is TORQUE PER DEGREE (the spring feedforward),")
pr("    b is TORQUE PER deg/s (the damper), F is the COULOMB FRICTION in torque units -- which is")
pr("    exactly SteerFriction's unit (get_friction returns friction*LAF in lat-accel space and the")
pr("    controller then divides by LAF, so the torque contribution is the toggle value itself).")
pr("=" * 110)
sos = signal.butter(4, 0.5, "lowpass", fs=L.FS, output="sos")
pr("\n    %-8s %8s %8s %13s %13s %11s %10s %8s"
   % ("band", "n s", "v med", "a torque/deg", "b torque/dps", "F torque", "u0", "R2"))
SPRING = {}
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    U, TH, TD = [], [], []
    for (a, b) in strets:
        idx = np.arange(a, b)
        sel = (g["v"][idx] >= lo) & (g["v"][idx] < hi)
        if sel.sum() < 400:
            continue
        uu = signal.sosfiltfilt(sos, CH["u_op"][a:b])
        th = signal.sosfiltfilt(sos, CH["y_ang"][a:b])
        td = np.gradient(th, DT)
        U.append(uu[sel]); TH.append(th[sel]); TD.append(td[sel])
    if not U:
        continue
    U, TH, TD = np.concatenate(U), np.concatenate(TH), np.concatenate(TD)
    s = np.abs(TD) > 0.3
    if s.sum() < 400:
        continue
    A = np.vstack([TH[s], TD[s], np.sign(TD[s]), np.ones(s.sum())]).T
    co, *_ = np.linalg.lstsq(A, U[s], rcond=None)
    vm = float(np.median(g["v"][(g["v"] >= lo) & (g["v"] < hi) & mask]))
    pr("    %-8s %8.0f %8.2f %13.5f %13.5f %11.5f %10.5f %8.3f"
       % (L.BANDNAME[k], s.sum() * DT, vm, co[0], co[1], co[2], co[3], L.r2(U[s], A @ co)))
    SPRING[L.BANDNAME[k]] = dict(a=float(co[0]), b=float(co[1]), F=float(co[2]), v=vm)
RES["spring"] = SPRING

pr("\n    the same spring coefficient from the FREQUENCY-DOMAIN IV fit (1 / the deg-per-torque DC")
pr("    gain of F1), which is closed-loop consistent where the time-domain fit above is not:")
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    W = [w for w in ALLW if lo <= w[2] < hi]
    R = pooled(W, "u_op", "y_ang"); F = fitK(R) if R else None
    if F and F["K"] != 0:
        pr("      %-8s  %.1f deg per unit torque  ->  a = %.5f torque/deg   (VAF %.2f, %d windows)"
           % (L.BANDNAME[k], F["K"], 1.0 / F["K"], F["vaf"], len(W)))
        if L.BANDNAME[k] in SPRING:
            SPRING[L.BANDNAME[k]]["a_iv"] = 1.0 / F["K"]

# ======================================================================================================
pr("\n" + "=" * 110)
pr("F3. WHAT THE FORK'S OWN ACCORD PLANT FEEDFORWARD DELIVERS, AND THE SCALE IT NEEDS")
pr("    get_honda_accord_rate_plant_ff:   hold = spring(v)*spring_scale * angle / (G(v)*gain_scale)")
pr("                                      move = rate_gain * d(angle)/dt / (G(v)*gain_scale)")
pr("    The tables were identified on the V280+ RATE loop (the docstring says so), i.e. on a plant")
pr("    V293 has removed.  They are constants in latcontrol_vehicle_tunes.py:")
pr("      HONDA_ACCORD_EPS_G_BP = [5.0, 12.5, 18.5, 28.5]      G_V = [120, 95, 85, 70]  deg/s per torque")
pr("      HONDA_ACCORD_EPS_K_BP = [4, 8, 12.5, 18.5, 28.5]     K_V = [0.17,0.28,0.35,0.45,0.50] 1/s")
pr("      HONDA_ACCORD_FF_RATE_GAIN = 0.5")
pr("=" * 110)
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [120.0, 95.0, 85.0, 70.0]
K_BP, K_V = [4.0, 8.0, 12.5, 18.5, 28.5], [0.17, 0.28, 0.35, 0.45, 0.50]
RATE_GAIN = 0.5
pr("\n    %-8s %8s %14s %14s %10s | %14s %14s %10s"
   % ("band", "v med", "fork hold", "measured a", "scale", "fork move", "measured b", "scale"))
scales = []
for nm, d in SPRING.items():
    v = d["v"]
    G = float(np.interp(v, G_BP, G_V)); K = float(np.interp(v, K_BP, K_V))
    hold = K / G
    move = RATE_GAIN / G
    a = d.get("a_iv", d["a"])
    pr("    %-8s %8.2f %14.5f %14.5f %10.2f | %14.5f %14.5f %10.2f"
       % (nm, v, hold, a, a / hold, move, d["b"], d["b"] / move))
    scales.append((nm, v, a / hold, d["b"] / move))
RES["fork_scale"] = [dict(band=s[0], v=s[1], spring_scale=s[2], rate_scale=s[3]) for s in scales]
if scales:
    sv = [s[2] for s in scales]
    pr("\n    => AccordEpsSpringScale needed: %.2f .. %.2f (median %.2f) with AccordEpsGainScale = 1.0"
       % (min(sv), max(sv), float(np.median(sv))))
    rv = [s[3] for s in scales]
    pr("       AccordFFRateGain needed:      %.2f .. %.2f (median %.2f)  [currently 0.5]"
       % (0.5 * min(rv), 0.5 * max(rv), 0.5 * float(np.median(rv))))
    pr("    NOTE the fork's hold term RISES with speed (0.0035 -> 0.0061) while the measured spring is")
    pr("    nearly FLAT, so one scale cannot fit every band: it is exact at the median band and off by")
    pr("    the spread above.  The exact fix is to replace HONDA_ACCORD_EPS_K_V / _G_V, which is code.")

pr("\n    what the CURRENT (route-70) configuration commands for a 1 degree steady angle, vs what the")
pr("    plant needs, per band -- the whole defect in one line:")
pr("    %-8s %8s %16s %16s %14s" % ("band", "v med", "V293 needs", "lat-accel FF gives", "ratio"))
for nm, d in SPRING.items():
    v = d["v"]
    a = d.get("a_iv", d["a"])
    # a 1 deg steady angle at speed v is a lat accel of angle/(SR*L)*v^2; the lat-accel FF then
    # commands that / 6.0 of torque.
    SR, WB = 16.88, 2.83
    la = np.radians(1.0) / (SR * WB) * v ** 2
    pr("    %-8s %8.2f %16.5f %16.5f %14.2f" % (nm, v, a, la / 6.0, a / (la / 6.0)))
pr("      (wheelbase 2.83 m, steer ratio 16.88 -- both from the fork; the lat-accel column ignores")
pr("       the understeer term, which makes it optimistic at speed, so the ratio is a lower bound)")

with open(os.path.join(L.SCRATCH, "v293_ident_f.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_f.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_f.txt / .json")
