# -*- coding: utf-8 -*-
"""THE LOOP, IDENTIFIED FROM THE LOGS.  L(jw), crossover, phase margin, Ms -- per family.

WHAT IS MEASURED AND WHAT IS ALGEBRA
  C(jw) = U_fb / E        e = r - y, u_fb = (p+i)/LAF.   DETERMINISTIC map (the PID plus the
                          low-speed-factor inflation plus the torque builds' error notch), so the
                          direct least-squares estimate is exact, not statistical.
  P(jw) = Y / U           the PHYSICAL plant: commanded torque -> measured lateral accel, through
                          the EPS (which is the thing that changed) and the car.  Estimated with
                          the reference r as an INSTRUMENT (unbiased when the road disturbance is
                          uncorrelated with the reference); the biased direct estimate is printed
                          beside it so the reader can see the size of the feedback bias.
  L = C * P,  S = 1/(1+L),  T_meas = Y/R   (measured directly -- no model).
  Crossover / phase margin / Ms are then ALGEBRA on those measured transfers.

THREAT TO VALIDITY, stated up front: r is the planner's shaped setpoint, which is itself derived
from vision and therefore is not perfectly exogenous with respect to road disturbance.  The IV/direct
contrast bounds how much that matters.

usage: python u2_loop.py [tag] [--match]
out:   u2_<tag>.json, U2-<TAG>-OUT.txt
"""
import json
import sys
import numpy as np
import ulib as U

TAG = sys.argv[1] if len(sys.argv) > 1 else "hi"
MATCH = "--match" in sys.argv
BANDS = [(0.08, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40), (2.40, 4.00)]
D = np.load(f"spec_{TAG}.npz", allow_pickle=True)
f = D["f"]
fam = D["fam"]
route = D["route"]
nblk = D["nblk"].astype(float)
sec = D["sec"]
rrms, arms = D["rrms"], D["arms"]
KEYS = [k for k in D.files if k.startswith("S_")]
MEM = {k[2:]: np.asarray(D[k]) for k in KEYS}   # decompress ONCE (NpzFile re-inflates on every get)


def pooled(idx):
    """Pool the selected windows' spectra, weighted by seconds."""
    w = sec[idx]
    return {k: np.tensordot(w, v[idx], axes=(0, 0)) / w.sum() for k, v in MEM.items()}


def gp(S, a, b):
    """Cross-spectrum getter.  `sa` is NEGATED here: the loop's measurement is
    -calc_curvature(steeringAngleDeg)*v^2, so +y corresponds to -steeringAngleDeg.  Without the flip
    every steering-angle transfer carries a spurious 180 deg and its 'delay' is meaningless."""
    sgn = (-1.0 if a == "sa" else 1.0) * (-1.0 if b == "sa" else 1.0)
    k = f"{a}_{b}"
    if k in S:
        return sgn * S[k]
    return sgn * np.conj(S[f"{b}_{a}"])


def transfers(S):
    C = U.smooth_c(gp(S, "e", "ufb") / np.maximum(np.real(gp(S, "e", "e")), 1e-30), 3)
    Piv = U.smooth_c(gp(S, "r", "y") / gp(S, "r", "u"), 5)
    Pdir = U.smooth_c(gp(S, "u", "y") / np.maximum(np.real(gp(S, "u", "u")), 1e-30), 5)
    L = U.smooth_c(C * Piv, 3)
    T = U.smooth_c(gp(S, "r", "y") / np.maximum(np.real(gp(S, "r", "r")), 1e-30), 3)
    ER = U.smooth_c(gp(S, "r", "e") / np.maximum(np.real(gp(S, "r", "r")), 1e-30), 3)
    Psa = U.smooth_c(gp(S, "r", "sa") / gp(S, "r", "u"), 5)          # torque -> wheel angle (IV)
    Psad = U.smooth_c(gp(S, "u", "sa") / np.maximum(np.real(gp(S, "u", "u")), 1e-30), 5)  # direct
    Zsa = U.smooth_c(gp(S, "r", "sa") / np.maximum(np.real(gp(S, "r", "r")), 1e-30), 3)  # setpoint -> wheel angle
    Sens = 1.0 / (1.0 + L)
    PF = U.smooth_c(Piv * gp(S, "r", "uff") / np.maximum(np.real(gp(S, "r", "r")), 1e-30), 3)  # the FF leg
    Typ = U.smooth_c(gp(S, "r", "yp") / np.maximum(np.real(gp(S, "r", "r")), 1e-30), 3)   # setpoint -> real yaw
    Gyy = U.smooth_c(gp(S, "y", "yp") / np.maximum(np.real(gp(S, "y", "y")), 1e-30), 3)   # angle-loop -> real yaw
    Txx = U.smooth_c(gp(S, "x", "yp") / np.maximum(np.real(gp(S, "x", "x")), 1e-30), 3)   # MODEL demand -> real yaw
    ch = lambda a, b: np.abs(gp(S, a, b)) ** 2 / np.maximum(np.real(gp(S, a, a) * gp(S, b, b)), 1e-30)
    return dict(C=C, P=Piv, Pdir=Pdir, L=L, T=T, ER=ER, S=Sens, Psa=Psa, Psad=Psad, Zsa=Zsa, PF=PF,
                Typ=Typ, Gyy=Gyy, Txx=Txx,
                coh_ru=ch("r", "u"), coh_ry=ch("r", "y"), coh_rsa=ch("r", "sa"),
                coh_ryp=ch("r", "yp"), coh_yyp=ch("y", "yp"), coh_xyp=ch("x", "yp"),
                Prr=np.real(gp(S, "r", "r")), Pyy=np.real(gp(S, "y", "y")),
                Psrsr=np.real(gp(S, "sr", "sr")), Pxx=np.real(gp(S, "x", "x")))


def metrics(tr):
    fc, pm = U.crossover(f, tr["L"], 0.06, 4.0)
    sb = U.band(f, 0.06, 4.0)
    Ms = float(np.max(np.abs(tr["S"])[sb]))
    fms = float(f[sb][np.argmax(np.abs(tr["S"])[sb])])
    m = dict(fc=fc, pm=pm, Ms=Ms, f_Ms=fms)
    for b1, b2 in BANDS:
        tagb = f"{b1:.2f}-{b2:.2f}"
        m[f"L|{tagb}"] = U.bandavg_mag(f, tr["L"], b1, b2, tr["Prr"])
        m[f"Lph|{tagb}"] = U.bandavg_phase(f, tr["L"], b1, b2, tr["Prr"])
        m[f"P|{tagb}"] = U.bandavg_mag(f, tr["P"], b1, b2, tr["Prr"])
        m[f"Pdir|{tagb}"] = U.bandavg_mag(f, tr["Pdir"], b1, b2, tr["Prr"])
        m[f"Pdly|{tagb}"] = U.group_delay_ms(f, tr["P"], b1, b2)
        m[f"C|{tagb}"] = U.bandavg_mag(f, tr["C"], b1, b2, tr["Prr"])
        m[f"T|{tagb}"] = U.bandavg_mag(f, tr["T"], b1, b2, tr["Prr"])
        m[f"Tdly|{tagb}"] = U.group_delay_ms(f, tr["T"], b1, b2)
        m[f"S|{tagb}"] = U.bandavg_mag(f, tr["S"], b1, b2, tr["Prr"])
        m[f"ER|{tagb}"] = U.bandavg_mag(f, tr["ER"], b1, b2, tr["Prr"])
        m[f"Zsa|{tagb}"] = U.bandavg_mag(f, tr["Zsa"], b1, b2, tr["Prr"])
        m[f"Zsadly|{tagb}"] = U.group_delay_ms(f, tr["Zsa"], b1, b2)
        m[f"PF|{tagb}"] = U.bandavg_mag(f, tr["PF"], b1, b2, tr["Prr"])
        m[f"Psa|{tagb}"] = U.bandavg_mag(f, tr["Psa"], b1, b2, tr["Prr"])
        m[f"Psad|{tagb}"] = U.bandavg_mag(f, tr["Psad"], b1, b2, tr["Prr"])
        m[f"Psadly|{tagb}"] = U.group_delay_ms(f, tr["Psa"], b1, b2)
        m[f"Typ|{tagb}"] = U.bandavg_mag(f, tr["Typ"], b1, b2, tr["Prr"])
        m[f"Typdly|{tagb}"] = U.group_delay_ms(f, tr["Typ"], b1, b2)
        m[f"Gyy|{tagb}"] = U.bandavg_mag(f, tr["Gyy"], b1, b2, tr["Pyy"])
        m[f"Txx|{tagb}"] = U.bandavg_mag(f, tr["Txx"], b1, b2, tr["Pxx"])
        for c in ("coh_ru", "coh_ry", "coh_rsa", "coh_ryp", "coh_yyp", "coh_xyp"):
            m[f"{c}|{tagb}"] = float(np.mean(tr[c][U.band(f, b1, b2)]))
        # incoherent (not explained by the reference) wheel-angle and yaw power, per second
        s = U.band(f, b1, b2)
        df = f[1] - f[0]
        m[f"incohY|{tagb}"] = float(np.sqrt(np.sum(tr["Pyy"][s] * (1 - tr["coh_ry"][s])) * df))
        m[f"cohY|{tagb}"] = float(np.sqrt(np.sum(tr["Pyy"][s] * tr["coh_ry"][s]) * df))
        m[f"srRMS|{tagb}"] = float(np.sqrt(np.sum(tr["Psrsr"][s]) * df))
    return m


# ---- amplitude matching on the reference RMS in 0.15-1.2 Hz (the study's own rule) -------------
sel = np.ones(len(fam), bool)
note = "no amplitude matching"
VW = [a for a in sys.argv if a.startswith("--v=")]
if VW:
    lo, hi = (float(x) for x in VW[0][4:].split(","))
    sel &= (D["v"] >= lo) & (D["v"] < hi)
    note = f"speed-matched: window median speed in [{lo},{hi}) m/s"
if MATCH:
    amp = np.sqrt(rrms ** 2 + arms ** 2)
    lo = max(np.percentile(amp[(fam == "V282") & sel], 10), np.percentile(amp[(fam == "TORQ") & sel], 10))
    hi = min(np.percentile(amp[(fam == "V282") & sel], 90), np.percentile(amp[(fam == "TORQ") & sel], 90))
    sel &= (amp >= lo) & (amp <= hi)
    note += f" | amplitude-matched: reference RMS(0.15-1.2 Hz) in [{lo:.4f},{hi:.4f}] m/s^2"

OUT = {"tag": TAG, "note": note, "bands": BANDS, "df": float(f[1] - f[0])}
rng = np.random.default_rng(11)
lines = [f"LOOP IDENTIFICATION -- tag {TAG}   df {f[1]-f[0]:.4f} Hz   {note}", ""]
for FM in ("V282", "TORQ", "V282old"):
    idx = np.where((fam == FM) & sel)[0]
    if len(idx) == 0:
        continue
    tr = transfers(pooled(idx))
    m = metrics(tr)
    rts = sorted(set(route[idx]))
    # route-cluster bootstrap
    boot = []
    for _ in range(400):
        pick = rng.choice(rts, size=len(rts), replace=True)
        ii = np.concatenate([np.where((route == p) & (fam == FM) & sel)[0] for p in pick])
        try:
            boot.append(metrics(transfers(pooled(ii))))
        except Exception:
            pass
    OUT[FM] = dict(n_win=len(idx), n_route=len(rts), sec=float(sec[idx].sum()),
                   blocks=int(nblk[idx].sum()), routes=rts, m=m,
                   ci={k: [float(np.nanpercentile([b[k] for b in boot], 5)),
                           float(np.nanpercentile([b[k] for b in boot], 95))] for k in m})
    lines.append(f"[{FM}] {len(rts)} routes, {len(idx)} windows, {sec[idx].sum():.0f} s, "
                 f"{int(nblk[idx].sum())} Welch blocks")
    ci = OUT[FM]["ci"]
    lines.append(f"    crossover f_c = {m['fc']:.3f} Hz [{ci['fc'][0]:.3f},{ci['fc'][1]:.3f}]   "
                 f"phase margin = {m['pm']:.1f} deg [{ci['pm'][0]:.1f},{ci['pm'][1]:.1f}]   "
                 f"Ms = {m['Ms']:.2f} [{ci['Ms'][0]:.2f},{ci['Ms'][1]:.2f}] at {m['f_Ms']:.2f} Hz")
    lines.append("")
    cols = ["L", "Lph", "C", "P", "Pdir", "Pdly", "PF", "T", "Tdly", "S", "ER", "coh_ru", "coh_ry"]
    lines.append(f"    {'band Hz':<12}" + "".join(f"{h:>9}" for h in
                 ["|L|", "argL", "|C|", "|P|", "Pdir", "P lag", "|P*F|", "|T|", "T lag",
                  "|S|", "|E/R|", "coh ru", "coh ry"]))
    for b1, b2 in BANDS:
        t = f"{b1:.2f}-{b2:.2f}"
        lines.append(f"    {t:<12}" + "".join(f"{m[k+'|'+t]:>9.3f}" if 'dly' not in k else f"{m[k+'|'+t]:>9.0f}"
                                              for k in cols))
    lines.append("")
    cols2 = ["Psa", "Psad", "Psadly", "Zsa", "Zsadly", "Typ", "Typdly", "Gyy", "coh_ryp",
             "coh_yyp", "Txx", "cohY", "incohY", "srRMS"]
    lines.append(f"    {'band Hz':<12}" + "".join(f"{h:>10}" for h in
                 ["Psa IV", "Psa dir", "Psa ms", "Z->sa", "Z->sa ms", "Z->yaw", "yaw ms",
                  "y->yaw", "coh ryp", "coh yyp", "X->yaw", "cohY rms", "incohY", "sr rms"]))
    for b1, b2 in BANDS:
        t = f"{b1:.2f}-{b2:.2f}"
        lines.append(f"    {t:<12}" + "".join(f"{m[k+'|'+t]:>10.3f}" if 'dly' not in k else f"{m[k+'|'+t]:>10.0f}"
                                              for k in cols2))
    lines.append("")

SFX = TAG + ("_m" if MATCH else "") + "".join(a[4:].replace(",","-") for a in sys.argv if a.startswith("--v="))
json.dump(OUT, open(f"u2_{SFX}.json", "w"), indent=1, default=float)
txt = "\n".join(lines)
open(f"U2-{SFX.upper()}-OUT.txt", "w").write(txt)
print(txt)
