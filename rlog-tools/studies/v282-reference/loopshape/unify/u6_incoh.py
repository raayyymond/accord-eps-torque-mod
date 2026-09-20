# -*- coding: utf-8 -*-
"""PER-ROUTE uncommanded (reference-incoherent) wheel motion -- the Regime B object, route by route.

The torque revs differ in exactly the terms that could inject it (ref filter, friction hysteresis,
100 Hz rate loop, disturbance observer), and route 70 flew with the plant feedforward OFF.  If the
excess is the fork's extra terms, it should track them.  If it is the plant, it should be there on
every torque route including the ones with none of them.

Each number is the RMS of the part of the steering angle that the shaped setpoint does NOT explain,
in octave bands, in degrees.  The COHERENT column beside it is how much steering the road actually
asked for, which is the fairest available control for "this route was on a curvier road".

out: U6-<TAG>-OUT.txt, u6_<tag>.json
"""
import json
import sys
import numpy as np
import ulib as U

TAG = sys.argv[1] if len(sys.argv) > 1 else "hi1k"
D = np.load(f"spec_{TAG}.npz", allow_pickle=True)
f = D["f"]
fam, route, sec, vv = D["fam"], D["route"], D["sec"], D["v"]
MEM = {k[2:]: np.asarray(D[k]) for k in D.files if k.startswith("S_")}
df = f[1] - f[0]
EDG = [(0.35, 0.60), (0.60, 1.20), (1.20, 2.40), (2.40, 4.00), (4.00, 8.00)]


def pooled(idx):
    w = sec[idx]
    return {k: np.tensordot(w, v[idx], axes=(0, 0)) / w.sum() for k, v in MEM.items()}


def split(idx):
    S = pooled(idx)
    gp = lambda a, b: (S[f"{a}_{b}"] if f"{a}_{b}" in S else np.conj(S[f"{b}_{a}"]))
    Pss = np.real(gp("sa", "sa"))
    Prr = np.maximum(np.real(gp("r", "r")), 1e-30)
    coh = np.abs(gp("r", "sa")) ** 2 / np.maximum(Prr * Pss, 1e-30)
    out = {}
    for a, b in EDG:
        s = (f >= a) & (f < b)
        out[f"inc{a}"] = float(np.sqrt(np.sum(Pss[s] * (1 - coh[s])) * df))
        out[f"coh{a}"] = float(np.sqrt(np.sum(Pss[s] * coh[s]) * df))
    return out


CFG = {}
for rt in U.FAMILY:
    p = U.PARAMS[rt]
    g = lambda k, d="0": (p[k] if p[k] != "ABSENT" else d)
    CFG[rt] = (f"pFF{g('AccordRatePlantFF','?'):>2} rf{g('AccordRefFilter'):>5} hyst{g('AccordFrictionHyst'):>6} "
               f"rl{g('AccordRateLoopGain'):>7} dob{g('AccordDobHz'):>4} SteerFric{g('SteerFriction','?'):>7}")

rows = {}
for rt in sorted(set(route)):
    idx = np.where(route == rt)[0]
    rows[rt] = dict(fam=U.FAMILY[rt], sec=float(sec[idx].sum()), v=float(np.median(vv[idx])),
                    **split(idx), cfg=CFG[rt])

L = [f"UNCOMMANDED WHEEL MOTION PER ROUTE -- tag {TAG}, engaged hands-off, >=15 m/s.",
     "inc = RMS of the steering angle NOT explained by the shaped setpoint (deg).",
     "coh = RMS of the part that IS explained (how much steering the road asked for).", ""]
hdr = f"{'route':<9}{'fam':<8}{'s':>5}{'v':>5}  " + "".join(f"{f'inc {a}-{b}':>12}" for a, b in EDG) + "  config"
L.append(hdr)
for rt, d in rows.items():
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}{d['sec']:>5.0f}{d['v']:>5.1f}  " +
             "".join(f"{d[f'inc{a}']:>12.4f}" for a, b in EDG) + f"  {d['cfg']}")
L.append("")
L.append("the same, NORMALISED by the commanded motion in the same band (inc/coh) -- removes most of")
L.append("the 'this route was on a curvier road' confound:")
L.append(f"{'route':<9}{'fam':<8}  " + "".join(f"{f'{a}-{b}':>12}" for a, b in EDG) + "   coh 0.35-0.60")
for rt, d in rows.items():
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}  " +
             "".join(f"{d[f'inc{a}']/max(d[f'coh{a}'],1e-9):>12.2f}" for a, b in EDG) +
             f"   {d['coh0.35']:>10.4f}")
L.append("")
for FM in ("V282", "V282old", "TORQ"):
    g = [d for d in rows.values() if d["fam"] == FM]
    L.append(f"{FM:<9} median inc: " + "  ".join(f"{a}-{b}: {np.median([d[f'inc{a}'] for d in g]):.4f}"
                                                 for a, b in EDG))
mv = {a: np.median([d[f"inc{a}"] for d in rows.values() if d["fam"] == "V282"]) for a, b in EDG}
mt = {a: np.median([d[f"inc{a}"] for d in rows.values() if d["fam"] == "TORQ"]) for a, b in EDG}
L.append("TORQ / V282 ratio of medians: " + "  ".join(f"{a}-{b}: {mt[a]/mv[a]:.2f}" for a, b in EDG))
L.append("")
L.append("RANGE WITHIN THE TORQUE FAMILY (min..max across the 9 routes) vs the V282 range:")
for a, b in EDG:
    t = [d[f"inc{a}"] for d in rows.values() if d["fam"] == "TORQ"]
    v = [d[f"inc{a}"] for d in rows.values() if d["fam"] == "V282"]
    L.append(f"   {a}-{b} Hz   TORQ {min(t):.4f}..{max(t):.4f}   V282 {min(v):.4f}..{max(v):.4f}   "
             f"{'SEPARATED' if min(t) > max(v) else 'OVERLAP'}")
json.dump(rows, open(f"u6_{TAG}.json", "w"), indent=1, default=float)
txt = "\n".join(L)
open(f"U6-{TAG.upper()}-OUT.txt", "w").write(txt)
print(txt)
