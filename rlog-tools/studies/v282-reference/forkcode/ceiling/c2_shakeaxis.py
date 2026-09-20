# -*- coding: utf-8 -*-
"""c2 -- CALIBRATE THE COST AXIS before spending it.

The inherited frontier prices every candidate on 'shake-band |L|' with three flown anchors:
rev 6.4 ~0.10, r72 0.19 (flew clean), r71 0.46 (LIMIT-CYCLED at 2.34 Hz).  f4's own positive
control (c) was written to test exactly that, and this script re-derives it from f4's stored
plant.  If the ordering of the anchors does not survive, the |L| ceiling is not a safety axis and
the frontier must be priced on the COMMAND SHAKE instead, which is directly logged.

Here I compute, straight from the f1 window spectra (logged command `out`, nothing modelled):
    P_shake(route) = mean over windows of sum |U|^2 over 1.8-3.5 Hz        [command^2, per window]
and report it in the brief's common units by the scale that puts rev 6.4 at 32.4.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                     # noqa: E402

OUT = FRONT / "out"
SHK = (1.8, 3.5)
BAND = (0.15, 2.4)
LBL = {"T64": "rev 6.4  (target, flew)", "T64B": "rev 6.4b", "T3": "r72  FLEW CLEAN",
       "T2": "r71  LIMIT-CYCLED 2.34Hz", "T3R": "r73 (hidden relay)", "T4": "r75 rev4",
       "T5": "r76 rev5", "RF00T": "r70 V293 open-loop", "V282": "V282 REFERENCE",
       "V282old": "V282 (older)"}
BRIEF = {"T64": 32.4, "T3": 19.4, "T2": 176.0}


def main():
    rows = []
    for route, fam in LP.GROUPS.items():
        p = OUT / f"f1_{route}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        f, U, v = D["f"], D["U"], D["vmed"]
        sel = v >= 15.0
        if sel.sum() == 0:
            continue
        s = (f >= SHK[0]) & (f <= SHK[1])
        b = (f >= BAND[0]) & (f <= BAND[1])
        Us = U[sel][:, s]
        pw = float(np.mean(np.sum(np.abs(Us) ** 2, axis=1)))
        rows.append(dict(route=route, fam=fam, n=int(sel.sum()), v=float(np.median(v[sel])),
                         shake=pw, inband=float(np.mean(np.sum(np.abs(U[sel][:, b]) ** 2, axis=1))),
                         rms=float(np.sqrt(np.mean(np.sum(np.abs(Us) ** 2, axis=1)))) ))
        del D
    # scale so rev 6.4 reads the brief's 32.4
    ref = np.mean([r["shake"] for r in rows if r["fam"] == "T64"])
    k = 32.4 / ref
    print("COMMAND SHAKE POWER 1.8-3.5 Hz, from the LOGGED command, metric windows only (>=15 m/s).")
    print("Scale chosen so rev 6.4 = 32.4, the brief's common-unit anchor.  Nothing is modelled here.")
    print(f"{'route':24s} {'fam':8s} {'n':>4s} {'v':>5s} {'shake (common u)':>17s} {'brief':>7s} "
          f"{'ratio to r72':>13s}")
    r72 = np.mean([r["shake"] for r in rows if r["fam"] == "T3"]) * k
    for r in sorted(rows, key=lambda r: -r["shake"]):
        bf = BRIEF.get(r["fam"])
        print(f"{r['route']:24s} {r['fam']:8s} {r['n']:4d} {r['v']:5.1f} {r['shake']*k:17.2f} "
              f"{(f'{bf:7.1f}' if bf else '      -')} {r['shake']*k/r72:13.2f}   {LBL.get(r['fam'],'')}")
    print()
    print("PER FAMILY (the axis the frontier must be priced on)")
    fams = {}
    for r in rows:
        fams.setdefault(r["fam"], []).append(r)
    for fam, rr in sorted(fams.items(), key=lambda kv: -np.mean([x["shake"] for x in kv[1]])):
        m = np.mean([x["shake"] for x in rr]) * k
        bf = BRIEF.get(fam)
        tag = f"   brief says {bf}" if bf else ""
        print(f"   {fam:8s} {m:9.2f}   {LBL.get(fam,''):28s}{tag}")
    json.dump({r["route"]: dict(fam=r["fam"], shake_common=r["shake"] * k, n=r["n"]) for r in rows},
              open(HERE / "out" / "c2_shake.json", "w"), indent=1)

    print()
    print("=" * 100)
    print("AND THE |L| AXIS THE FRONTIER ACTUALLY USES, re-derived two ways for the same anchors")
    S3 = json.load(open(OUT / "f3_ident.json"))
    S4 = json.load(open(OUT / "f4_plant.json"))
    print(f"{'fam':8s} {'|L|shake  IV plant (f3)':>24s} {'|L|shake  blended plant (f4)':>30s}   note")
    for fam in ("T64", "T3", "T2", "V282"):
        key = f"{fam}|15+"
        if key not in S4:
            continue
        D4, D3 = S4[key], S3.get(key)
        f = np.array(D4["f"])
        route = [r for r, g in LP.GROUPS.items() if g == fam][0]
        p = LP.FLOWN[route]
        v = D4["v"]
        C = LP.c_fb_analytic(f, p["kp"], float(LP.ki_of(v, p["ki"], p["ki_hi"])), D4["laf"],
                             float(LP.low_speed_factor(v)),
                             float(LP.mode_hz(v)) if p["notch"] else None, 1.0)
        j = [int(np.argmin(np.abs(f - q))) for q in (1.95, 2.54, 3.03)]
        P4 = np.array(D4["P"][0]) + 1j * np.array(D4["P"][1])
        a4 = float(np.mean(np.abs((P4 * C)[j])))
        a3 = np.nan
        if D3 is not None:
            P3 = np.array(D3["P"][0]) + 1j * np.array(D3["P"][1])
            a3 = float(np.mean(np.abs((P3 * C)[j])))
        print(f"{fam:8s} {a3:24.3f} {a4:30.3f}   {LBL.get(fam,'')}")


if __name__ == "__main__":
    (HERE / "out").mkdir(exist_ok=True)
    main()
