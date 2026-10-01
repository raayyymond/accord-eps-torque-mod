# -*- coding: utf-8 -*-
"""panel_explore2.py -- FAST parallel tuning on the binding members only.  ANALYSIS ONLY."""
from __future__ import annotations
import os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1]), str(HERE.parents[1] / "c1"),
           str(HERE.parents[1] / "refute_stability"), str(HERE.parents[2] / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("C1_VARIANT", "r2")
import panel_schedules as PS   # noqa
import c1r2_members as M       # noqa
import stab_lin as S           # noqa

BIND = ['nominal', 'J_hi', 'b_lo', 'b_hi', 'b_q*J1.0+h10', 'b/1.9*J1.0*tau6+h10', 'b_lo*J_hi*tau6+h10',
        'J1.0*tau6+h10', 'b_q*J_hi', 'b_q*J1.0', 'J_hi*1.0']
BIND = [n for n in BIND if n in (M.TIER_A + M.TIER_B)]
SP = [2, 3.1, 5, 8, 10, 11, 11.9, 12.5, 15, 17, 19, 22, 26.9]


def ev(args):
    impl, scale, r, kiflat, kd = args
    wa = (999, None); wb = (999, None); nun = 0
    for n in BIND:
        tier = "A" if n in M.TIER_A else "B"
        for v in SP:
            pl, tau, bea, (J, b, k) = M.member(n, v)
            kp = int(round(PS.kp_of(v) * scale))
            ki = kiflat if impl == "flat" else int(round(r * kp))
            for ea in (0, 10):
                c = S.Ctl(v, kp=kp, ki=ki, kd=kd, d=tau, extra_age=bea + ea, G=256)
                pm = S.margins(c, pl, npts=900)["pm"]
                rho = S.exact(c, pl)[0]
                if rho >= 1 or not np.isfinite(pm):
                    nun += 1; pm = -1.0
                if tier == "A":
                    if pm < wa[0]: wa = (round(pm, 1), (n, v, ea))
                else:
                    if pm < wb[0]: wb = (round(pm, 1), (n, v, ea))
    return (impl, scale, r, kiflat, kd, wa, wb, nun)


if __name__ == "__main__":
    jobs = []
    for sc in (1.0, 0.85, 0.72, 0.62, 0.55):
        for r in (0.5, 0.4):
            jobs.append(("sched", sc, r, 0, 20))
    for sc in (1.0, 0.72, 0.55):
        for ki in (300, 150, 80, 40):
            jobs.append(("flat", sc, 0, ki, 20))
    with Pool(10) as p:
        res = p.map(ev, jobs)
    print("A2 (Ki(v) = r*Kp):")
    for impl, sc, r, ki, kd, wa, wb, nun in res:
        if impl == "sched":
            print(f"  sc {sc:.2f} r {r:.2f}: A {wa[0]:6.1f} {wa[1]}  B {wb[0]:6.1f} {wb[1]}  unst {nun}")
    print("A1 (flat Ki):")
    for impl, sc, r, ki, kd, wa, wb, nun in res:
        if impl == "flat":
            print(f"  sc {sc:.2f} Ki {ki:4d}: A {wa[0]:6.1f} {wa[1]}  B {wb[0]:6.1f} {wb[1]}  unst {nun}")
