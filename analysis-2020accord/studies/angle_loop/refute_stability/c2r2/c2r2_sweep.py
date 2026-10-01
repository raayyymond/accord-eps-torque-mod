# -*- coding: utf-8 -*-
"""c2r2_sweep.py -- the full stability attack on the four C2 rev 2 implementations (P2, F2 = rev2-A; D2a, B0r = rev2-B).

For every (design, member, hold age, speed) on the 0.25 m/s grid 1..35 m/s + the plant knots + a 0.05 m/s fine grid
at 7..13.5 m/s (the steep G segment):
   averaged-hold LTI: PM (min over all crossings), fc, GM up/down, Ms, |Tc| and |Tref| 5-30 Hz peak, L20, Tr163, hold
   EXACT periodic:    rho, least-damped oscillatory pole (f, zeta), rho at gain x2 (= exact GM >= 6 dB), rho at the fade
                      floor x0.297 and with the integrator frozen (P+D only) at x1 / x0.297 / x0.05 (the ramp-in and the
                      hands-on-freeze loops)
Writes _scratch/angle_loop/refute-c2r2-stability/sweep_<design>.json.  ANALYSIS ONLY.
usage: python c2r2_sweep.py [designs...]"""
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M  # noqa: E402

OUT = M.KIT / "_scratch" / "angle_loop" / "refute-c2r2-stability"
OUT.mkdir(parents=True, exist_ok=True)
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]
                  + [round(x, 2) for x in np.arange(7.0, 13.51, 0.05)]))

SINGLE = ["nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free"]   # tier A (F_lo/F_hi = nominal, linear)
COMBINED = ["b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6", "b_lo*J_hi*tau6",
            "b_lo_knot", "b_lo_knot*tau6"]                                                                  # tier B (bc = b_lo)
# the C1 rev 2 full factorial cells not already above, + the record's report members, + products with ms_free
FACT = []
for d in ("", "b_lo", "b/1.9", "b_q"):
    for i in ("", "J_hi", "J_hi2", "J1.0"):
        for t in ("", "tau6"):
            nm = "*".join(x for x in (d, i, t) if x) or "nominal"
            if nm not in SINGLE + COMBINED:
                FACT.append(nm)
REPORT = FACT + ["J1.3", "b_lo*J1.3", "b_q*J1.3", "b_q0", "b_q0*J_hi", "bq10*J1.0", "bq10*J1.0*tau6", "tau10",
                 "b_lo*tau10", "b_lo*J0.3", "b_lo*ms_free", "b_q*ms_free", "ms_free*tau6", "b_lo*ms_free*tau6"]


def members():
    out = []
    for m in SINGLE:
        out += [(m, "A"), (m + "+h10", "B")]
    for m in COMBINED:
        out += [(m, "B"), (m + "+h10", "B")]
    for m in REPORT:
        out += [(m, "R"), (m + "+h10", "R")]
    return out


def one(args):
    dn, mname, tier, v = args
    des = M.load_designs()[dn] if dn not in _DES else _DES[dn]
    pl = M.member(mname, v)
    r, _ = M.lti_metrics(des, pl, v)
    per = M.Periodic(des, pl, v)
    rho, z, f, lam = per.rho_poles()
    rho2 = M.Periodic(des, pl, v, gain=2.0).rho_poles()[0]
    rho_fade = M.Periodic(des, pl, v, gain=0.297 / M.FADE).rho_poles()[0]
    rho_noI = max(M.Periodic(des, pl, v, gain=g, noI=True).rho_poles()[0] for g in (1.0, 0.297 / M.FADE, 0.05))
    out = dict(d=dn, m=mname, tier=tier, v=v, J=pl.J, b=pl.b, k=pl.k, tau=pl.d, ea=pl.ea, G=des.G(v), rho=rho, zeta=z,
               fpole=f, rho_x2=rho2, rho_fade=rho_fade, rho_noI=rho_noI)
    out.update({k: (float(x) if x is not None else None) for k, x in r.items()})
    return out


_DES = {}


def init():
    _DES.update(M.load_designs())


def run(designs):
    jobs = []
    mem = members()
    for dn in designs:
        for mname, tier in mem:
            for v in GRID:
                jobs.append((dn, mname, tier, v))
    t0 = time.time()
    print(f"{len(jobs)} points", flush=True)
    res = []
    with Pool(6, initializer=init) as pool:
        for i, r in enumerate(pool.imap_unordered(one, jobs, chunksize=64)):
            res.append(r)
            if i % 5000 == 0:
                print(f"  {i} [{time.time() - t0:.0f}s]", flush=True)
    for dn in designs:
        rr = [r for r in res if r["d"] == dn]
        (OUT / f"sweep_{dn}.json").write_text(json.dumps(rr, default=lambda x: None if x is None else float(x)))
    print(f"done [{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    ds = sys.argv[1:] or ["P2", "F2", "D2a", "B0r"]
    run(ds)
