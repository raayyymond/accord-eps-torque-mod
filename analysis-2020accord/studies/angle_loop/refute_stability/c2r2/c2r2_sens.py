# -*- coding: utf-8 -*-
"""c2r2_sens.py -- the GATED set re-run under two model facts the designs did not carry:
  S1  D gain in the plant's angle frame x0.866 (near centre) and x1.04 (outward): the rate operand is the LINEAR motor
      rate while P and the plant act on gp-0x6a00, whose correction C makes d(6a00)/d(lin) = 1.155 near centre .. 0.962
      outward (TRACE angle sec 2.1; MEASURED on r71b 0x14A this session: x per deg/s of the 6a00 frame = 6.63 at
      |theta| < 10 deg, 6.86 at 10-30, 7.57 at 30-90, 8.29 above 90; the designs assume 8.00 everywhere)
  S2  the rate former's own lag on the D operand: gp-0x4f50 is a 1 kHz snapshot of an ISR 2-sample mean of the resolver
      delta (FUN_00068f52 / FUN_00068fbe) -> +0.5 tick and +1 tick on the operand (bounds; the ISR period is BELIEF)
  S3  S1 x0.866 and S2 +0.5 together
Prints the min PM / any rho >= 1 / GM per gated member for each.  ANALYSIS ONLY."""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M  # noqa: E402
import c2r2_sweep as SW  # noqa: E402

GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
VARS = {"S1_kd0.866": dict(kd=0.866, dd=0.0), "S1_kd1.04": dict(kd=1.04, dd=0.0), "S2_rf+0.5": dict(kd=1.0, dd=0.5),
        "S2_rf+1": dict(kd=1.0, dd=1.0), "S3_kd0.866_rf+0.5": dict(kd=0.866, dd=0.5)}
_D = {}


def init():
    _D.update(M.load_designs())


def one(a):
    dn, var, m, tier, v = a
    kw = VARS[var]
    pl = M.member(m, v)
    pl.ddelay = kw["dd"]
    r, _ = M.lti_metrics(_D[dn], pl, v, kd_scale=kw["kd"])
    rho, z, f, _ = M.Periodic(_D[dn], pl, v, kd_scale=kw["kd"]).rho_poles()
    return dict(d=dn, var=var, m=m, tier=tier, v=v, pm=r["pm"], fc=r["fc"], gm=r["gm_up"], rho=rho, z=z, f=f,
                pk=max(r["Tc530"], r["Tr530"]))


if __name__ == "__main__":
    mem = [(m, "A") for m in SW.SINGLE] + [(m + "+h10", "B") for m in SW.SINGLE] + \
          [(m, "B") for m in SW.COMBINED] + [(m + "+h10", "B") for m in SW.COMBINED]
    jobs = [(dn, var, m, t, v) for dn in ("P2", "F2", "D2a", "B0r") for var in VARS for m, t in mem for v in GRID]
    t0 = time.time()
    with Pool(12, initializer=init) as p:
        res = p.map(one, jobs, chunksize=64)
    json.dump(res, open(SW.OUT / "sens.json", "w"))
    print(f"{len(res)} points [{time.time() - t0:.0f}s]")
    for dn in ("P2", "F2", "D2a", "B0r"):
        for var in VARS:
            rr = [r for r in res if r["d"] == dn and r["var"] == var]
            fails = [r for r in rr if (np.isfinite(r["pm"]) and r["pm"] < (45 if r["tier"] == "A" else 30))
                     or r["gm"] < 6 or r["rho"] >= 1 or r["pk"] > 3]
            wa = min((r for r in rr if r["tier"] == "A" and np.isfinite(r["pm"])), key=lambda r: r["pm"])
            wb = min((r for r in rr if r["tier"] == "B" and np.isfinite(r["pm"])), key=lambda r: r["pm"])
            print(f"{dn:4s} {var:18s} tierA min PM {wa['pm']:5.1f} ({wa['m']} @{wa['v']})  tierB min PM {wb['pm']:5.1f} "
                  f"({wb['m']} @{wb['v']}, ring {wb['f']:.2f} Hz z {wb['z']:.3f})  fails {len(fails)}  "
                  f"max rho {max(r['rho'] for r in rr):.4f}  max peak {max(r['pk'] for r in rr):+.1f} dB")
            for f in fails[:8]:
                print("      FAIL", f["m"], f["v"], round(f["pm"], 1), round(f["gm"], 1), round(f["rho"], 4), round(f["pk"], 1))
