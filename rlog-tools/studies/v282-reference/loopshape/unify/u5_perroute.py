# -*- coding: utf-8 -*-
"""PER-ROUTE loop metrics -- because the torque revs differ in exactly the terms the attribution
implicated, and the labels do not: every configuration below is read from that route's own initData.

The decisive contrasts available inside the torque family:
  route 70 : AccordRatePlantFF = 0  -> the plant feedforward is OFF; no ref filter, no friction
             hysteresis, no observer.  The feedforward is then the generic lat-accel term, which is
             a near-static gain on the shaped setpoint.  If the extra lag is the fork's feedforward
             machinery, route 70 should not have it.  If it is the EPS, route 70 should.
  71       : plant FF on, no ref filter, no observer.
  72/73/75 : ref filter 0.12, friction hysteresis, rate loop 6e-4, observer OFF.
  6c/6d/6e : ref filter 0.06, rate loop 1e-3, observer 0.6 Hz ON.
  76       : ref filter 0.12, rate loop 1e-3, observer 0.6 Hz ON.

out: U5-<TAG>-OUT.txt, u5_<tag>.json
"""
import json
import sys
import numpy as np
import ulib as U

TAG = sys.argv[1] if len(sys.argv) > 1 else "hi1k"
B = (0.15, 0.30)
BANDS = [(0.08, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40), (2.40, 4.00)]
D = np.load(f"spec_{TAG}.npz", allow_pickle=True)
f = D["f"]
fam, route, sec, vv = D["fam"], D["route"], D["sec"], D["v"]
MEM = {k[2:]: np.asarray(D[k]) for k in D.files if k.startswith("S_")}


def pooled(idx):
    w = sec[idx]
    return {k: np.tensordot(w, v[idx], axes=(0, 0)) / w.sum() for k, v in MEM.items()}


def gp(S, a, b):
    sgn = (-1.0 if a == "sa" else 1.0) * (-1.0 if b == "sa" else 1.0)
    return sgn * (S[f"{a}_{b}"] if f"{a}_{b}" in S else np.conj(S[f"{b}_{a}"]))


def row(idx):
    S = pooled(idx)
    Prr = np.maximum(np.real(gp(S, "r", "r")), 1e-30)
    C = U.smooth_c(gp(S, "e", "ufb") / np.maximum(np.real(gp(S, "e", "e")), 1e-30), 3)
    P = U.smooth_c(gp(S, "r", "y") / gp(S, "r", "u"), 5)
    F = U.smooth_c(gp(S, "r", "uff") / Prr, 3)
    Z = U.smooth_c(gp(S, "r", "sa") / Prr, 3)
    T = U.smooth_c(gp(S, "r", "y") / Prr, 3)
    Psa = U.smooth_c(gp(S, "r", "sa") / gp(S, "r", "u"), 5)
    L = U.smooth_c(C * P, 3)
    Sen = 1.0 / (1.0 + L)
    d = dict(sec=float(sec[idx].sum()), n=len(idx), v=float(np.median(vv[idx])))
    fc, pm = U.crossover(f, L, 0.06, 4.0)
    d["fc"], d["pm"] = fc, pm
    sb = U.band(f, 0.06, 4.0)
    d["Ms"] = float(np.max(np.abs(Sen)[sb]))
    d["fMs"] = float(f[sb][np.argmax(np.abs(Sen)[sb])])
    for b1, b2 in BANDS:
        t = f"{b1:.2f}"
        d["L" + t] = U.bandavg_mag(f, L, b1, b2, Prr)
        d["C" + t] = U.bandavg_mag(f, C, b1, b2, Prr)
        d["P" + t] = U.bandavg_mag(f, P, b1, b2, Prr)
        d["F" + t] = U.bandavg_mag(f, F, b1, b2, Prr)
        d["Fdly" + t] = U.group_delay_ms(f, F, b1, b2)
        d["Zdly" + t] = U.group_delay_ms(f, Z, b1, b2)
        d["Tdly" + t] = U.group_delay_ms(f, T, b1, b2)
        d["Psa" + t] = U.bandavg_mag(f, Psa, b1, b2, Prr)
        d["Psadly" + t] = U.group_delay_ms(f, Psa, b1, b2)
        d["S" + t] = U.bandavg_mag(f, Sen, b1, b2, Prr)
    return d


CFG = {}
for rt in U.FAMILY:
    p = U.PARAMS[rt]
    g = lambda k, dflt="-": (p[k] if p[k] != "ABSENT" else dflt)
    CFG[rt] = (f"pFF {g('AccordRatePlantFF','?')} rf {g('AccordRefFilter','0')} "
               f"hyst {g('AccordFrictionHyst','0')} rl {g('AccordRateLoopGain','0')} "
               f"dob {g('AccordDobHz','0')} ki {g('AccordTorqueKi','-')}/{g('AccordTorqueKiHigh','-')}")

rows = {}
for rt in sorted(set(route)):
    idx = np.where(route == rt)[0]
    if len(idx) == 0:
        continue
    rows[rt] = row(idx)
    rows[rt]["fam"] = U.FAMILY[rt]
    rows[rt]["cfg"] = CFG[rt]

L = [f"PER-ROUTE LOOP METRICS -- tag {TAG}, engaged hands-off, >=15 m/s.  Config from each route's own initData.", ""]
L.append(f"{'route':<9}{'fam':<8}{'s':>5}{'v':>5}{'kp/LAF':>7}  {'|L|.15':>7}{'|C|.15':>7}{'|P|.15':>7}"
         f"{'|F|.15':>7}{'F ms':>7}{'Z ms':>7}{'T ms':>7}{'f_c':>7}{'PM':>6}{'Ms':>6}{'fMs':>6}  config")
for rt, d in rows.items():
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}{d['sec']:>5.0f}{d['v']:>5.1f}"
             f"{U.kp(rt)/U.laf(rt):>7.4f}  {d['L0.15']:>7.3f}{d['C0.15']:>7.3f}{d['P0.15']:>7.2f}"
             f"{d['F0.15']:>7.3f}{d['Fdly0.15']:>7.0f}{d['Zdly0.15']:>7.0f}{d['Tdly0.15']:>7.0f}"
             f"{d['fc']:>7.3f}{d['pm']:>6.0f}{d['Ms']:>6.2f}{d['fMs']:>6.2f}  {d['cfg']}")
L.append("")
L.append("PLANT SHAPE -- |Psa| = wheel angle (deg) per unit commanded torque, by band.  A high-gain")
L.append("inner RATE servo makes this fall like 1/f (a velocity command); a pure torque map makes it")
L.append("flat below the steering mode and peak at it.")
L.append(f"{'route':<9}{'fam':<8}" + "".join(f"{b1:>9.2f}" for b1, _ in BANDS) + "   slope dec/dec 0.08-1.2")
for rt, d in rows.items():
    v = [d[f"Psa{b1:.2f}"] for b1, _ in BANDS]
    fc_ = np.array([np.sqrt(b1 * b2) for b1, b2 in BANDS])
    s4 = slice(0, 4)
    sl = np.polyfit(np.log10(fc_[s4]), np.log10(np.array(v)[s4]), 1)[0]
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}" + "".join(f"{x:>9.1f}" for x in v) + f"        {sl:>+6.2f}")
L.append("")
L.append("PLANT PHASE as an equivalent lag (ms) -- an integrator reads as -90 deg (a lag that halves")
L.append("with each doubling of frequency); a spring-like torque map reads as much less.")
L.append(f"{'route':<9}{'fam':<8}" + "".join(f"{b1:>9.2f}" for b1, _ in BANDS))
for rt, d in rows.items():
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}" + "".join(f"{d[f'Psadly{b1:.2f}']:>9.0f}" for b1, _ in BANDS))
L.append("")
L.append("PLANT PHASE in DEGREES at the band centre (the same numbers, read as phase):")
L.append(f"{'route':<9}{'fam':<8}" + "".join(f"{b1:>9.2f}" for b1, _ in BANDS))
for rt, d in rows.items():
    cells = []
    for b1, b2 in BANDS:
        fcx = np.sqrt(b1 * b2)
        cells.append(f"{-d[f'Psadly{b1:.2f}']/1000.0*360.0*fcx:>9.0f}")
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}" + "".join(cells))
json.dump(rows, open(f"u5_{TAG}.json", "w"), indent=1, default=float)
txt = "\n".join(L)
open(f"U5-{TAG.upper()}-OUT.txt", "w").write(txt)
print(txt)
