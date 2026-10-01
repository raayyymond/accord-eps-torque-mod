# -*- coding: utf-8 -*-
"""c2r2_frame.py -- the gp-0x6a00 / motor-frame ratio (1.155 for |theta| < 30 deg; EVIDENCE: FUN_0003e6d8/FUN_0003e600
correction slope, and r71b 0x14A d(theta)/dt on x/8 = 1.155/1.162/1.158/1.154 in the 0-5/5-10/10-20/20-30 deg bins)
under BOTH readings of which frame the identified plant lives in:
  FA  plant in the gp-0x6a00 frame (th):  D operand x/8 = theta_dot/1.155  -> Kd x 0.866                 (= c2r2_sens S1)
  FB  plant in the motor frame (om = x/8): P/I on theta = 1.155 phi       -> G x 1.155, spring k x 1.155, D x 1
and at large angle (|theta| > 90 deg, ratio 0.964): FA' Kd x 1.037 ; FB' G x 0.964, k x 0.964.
Gated set (brief), 0.25 m/s grid + knots, LTI PM/GM + exact rho.  ANALYSIS ONLY."""
import json, sys, time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M
import c2r2_sweep as SW
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
VARS = {"FA_centre": (0.866, 1.0, 1.0), "FB_centre": (1.0, 1.155, 1.155), "FA_outward": (1.037, 1.0, 1.0),
        "FB_outward": (1.0, 0.964, 0.964)}
_D = {}
class GDes(M.Design):
    pass
def init():
    _D.update(M.load_designs())
def one(a):
    dn, var, m, tier, v = a
    kd, gs, ks = VARS[var]
    des = _D[dn]
    G0 = des.G(v)
    d2 = replace(des)
    d2.G = (lambda vv, G0=G0, gs=gs: G0 * gs)
    pl = M.member(m, v)
    pl.k = pl.k * ks
    r, _ = M.lti_metrics(d2, pl, v, kd_scale=kd)
    rho, z, f, _ = M.Periodic(d2, pl, v, kd_scale=kd).rho_poles()
    return dict(d=dn, var=var, m=m, tier=tier, v=v, pm=r["pm"], fc=r["fc"], gm=r["gm_up"], rho=rho, z=z, f=f,
                pk=max(r["Tc530"], r["Tr530"]))
if __name__ == "__main__":
    mem = [(m, "A") for m in SW.SINGLE] + [(m + "+h10", "B") for m in SW.SINGLE] + \
          [(m, "B") for m in SW.COMBINED] + [(m + "+h10", "B") for m in SW.COMBINED]
    jobs = [(dn, var, m, t, v) for dn in ("P2", "F2", "D2a", "B0r") for var in VARS for m, t in mem for v in GRID]
    t0 = time.time()
    with Pool(12, initializer=init) as p:
        res = p.map(one, jobs, chunksize=64)
    json.dump(res, open(SW.OUT / "frame.json", "w"))
    print(f"{len(res)} points [{time.time() - t0:.0f}s]")
    from collections import defaultdict
    for dn in ("P2", "F2", "D2a", "B0r"):
        for var in VARS:
            rr = [r for r in res if r["d"] == dn and r["var"] == var]
            agg = defaultdict(list)
            for r in rr:
                bar = 45 if r["tier"] == "A" else 30
                if (np.isfinite(r["pm"]) and r["pm"] < bar) or r["gm"] < 6 or r["rho"] >= 1 or r["pk"] > 3:
                    agg[r["m"]].append(r)
            wa = min((r for r in rr if r["tier"] == "A" and np.isfinite(r["pm"])), key=lambda r: r["pm"])
            wb = min((r for r in rr if r["tier"] == "B" and np.isfinite(r["pm"])), key=lambda r: r["pm"])
            print(f"{dn:4s} {var:11s} tierA min {wa['pm']:5.1f} ({wa['m']}@{wa['v']})  tierB min {wb['pm']:5.1f} "
                  f"({wb['m']}@{wb['v']}, ring {wb['f']:.2f} Hz z {wb['z']:.3f})  max rho {max(r['rho'] for r in rr):.4f}  "
                  f"failing members {len(agg)}")
            for m, L in agg.items():
                w = min(L, key=lambda r: r["pm"]); vs = [r["v"] for r in L]
                print(f"      {m:22s} v {min(vs):5.2f}-{max(vs):5.2f} ({len(L)} pts) minPM {w['pm']:.1f} @{w['v']} "
                      f"GM {min(r['gm'] for r in L):.1f} ring {w['f']:.2f} Hz z {w['z']:.3f}")
