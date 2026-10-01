# -*- coding: utf-8 -*-
"""b_gate.py -- the authoritative GATE 2 for a panel-B implementation, on the FULL FACTORIAL (c1r2_members: tier A thr45,
tier B thr30, incl. every b_q*J* combined member and every +h10 aged member).  Two independent linear methods:
  * b_lib.frf (LTI fundamental) -> PM (min over crossings), GM, Ms, |T| peak 5-30 Hz;
  * exact 10-tick periodic monodromy -> spectral radius (stability) and least-damped pole (stab_lin.exact for held D,
    b2_stab.exact_fresh for fresh D).
plus Re(T/w)20 vs V295 at hold age 0 and 10.  A FAIL (written before the run) = any tier-A PM<45 | any tier-B PM<30 |
GM<6 | rho>=1 | Ms>2.5 | |T|5-30 > +3 dB | Re(T/w)20 > V295's.  ANALYSIS ONLY.
usage: python b_gate.py <impl: B1|B2|B3>"""
import json, math, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parents[1]/'refute_stability', HERE.parents[1]/'c1', HERE.parents[2]/'v295'/'plant'):
    sys.path.insert(0, str(_p))
import b_lib as B
import b2_stab as B2S
import stab_lin as S
import c1r2_members as M
import c1_lib as C
OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "B-robust-margins"

IMPL = {
 "B1": dict(dmode="held", kd=20, ki=56, ema=None,
            knots=[(3.1,952),(8.0,1321),(10.0,855),(11.9,699),(15.5,1044),(26.9,2041)]),
 "B2": dict(dmode="fresh_ema", kd=24, ki=56, ema=40.0,
            knots=[(3.1,1106),(8.0,1475),(10.0,989),(11.9,826),(15.5,1213),(26.9,2241)]),
 "B3": dict(dmode="held", kd=20, ki=0, ema=None,
            knots=[(3.1,1690),(8.0,1805),(10.0,1357),(11.9,1162),(15.5,1366),(26.9,2765)]),
}
GRID = sorted(set([round(x,2) for x in np.arange(1.0,35.01,0.25)] + [3.1,8.0,11.9,17.0,26.9]))
V295_RE20_age = {0:-0.633, 10:-1.087}

def point(args):
    name, v, impl = args
    cfg = IMPL[impl]
    tbl = C.make_table(cfg["knots"])
    J,b,k,tau,ea = M.params(name, v)
    pl = S.rigid(J,b,k)
    G = C.G_at(v, tbl)
    c = B.ctl_at(v, tbl, 112, cfg["ki"], cfg["kd"], d=tau, extra_age=ea, G=G)
    dm = "fresh" if cfg["dmode"].startswith("fresh") else "held"
    m = B.margins(c, pl, dmode=cfg["dmode"], ema_hz=cfg["ema"])
    # stability via exact monodromy
    if dm == "held":
        rho, poles = S.exact(c, pl)
    else:
        rho, poles = B2S.exact_fresh(c, pl)      # ideal-fresh monodromy (upper bound on D-path HF gain -> conservative)
    low = [p for p in poles if 0.3 <= p[0] < 5.0]
    hf = [p for p in poles if 5.0 <= p[0] <= 50.0]
    return dict(member=name, v=v, G=int(G), kp_eff=112*G/256, pm=m["pm"], gm=m["gm"], Ms=m["Ms"],
                Tpk530=m["Tpk530"], rho=rho, n_cross=m["n_cross"],
                low=low[0] if low else (float('nan'),float('nan')),
                hf=hf[0] if hf else (float('nan'),float('nan')))

def main():
    impl = sys.argv[1]
    cfg = IMPL[impl]
    names = M.TIER_A + M.TIER_B
    jobs = [(n, v, impl) for n in names for v in GRID]
    t0 = time.time()
    with Pool(14) as pool:
        res = pool.map(point, jobs, chunksize=16)
    (OUT / f"gate_{impl}.json").write_text(json.dumps(res, default=float))
    by = {}
    for r in res: by.setdefault(r["member"], []).append(r)
    out = []
    P = lambda s="": out.append(s)
    P(f"# GATE 2 panel-{impl}: dmode {cfg['dmode']} kd {cfg['kd']} ki {cfg['ki']} ema {cfg['ema']} kp 112")
    P(f"# knots {cfg['knots']}  ({len(res)} points: {len(names)} members x {len(GRID)} speeds)")
    fails = []
    P(f"{'member':22s} {'tier':4s} {'minPM(v)':14s} PM<thr  {'minGM':6s} {'maxMs':6s} {'maxT530dB':9s} {'maxrho':7s}  worst-pole")
    for n in names:
        rr = by[n]; tier = M.tier(n); thr = 45.0 if tier=="A" else 30.0
        pmr = min(rr, key=lambda r: r["pm"] if np.isfinite(r["pm"]) else 999)
        nbad = sum(1 for r in rr if np.isfinite(r["pm"]) and r["pm"] < thr)
        gm = min(r["gm"] for r in rr)
        ms = max(r["Ms"] for r in rr)
        t530 = max(r["Tpk530"] for r in rr)
        mrho = max(r["rho"] for r in rr)
        wp = min((r for r in rr if np.isfinite(r["low"][1])), key=lambda r:r["low"][1], default=None)
        wps = f"{wp['low'][0]:.2f}Hz z{wp['low'][1]:.2f}@{wp['v']:.1f}" if wp else "-"
        P(f"{n:22s} {tier:4s} {pmr['pm']:6.1f}({pmr['v']:5.2f}) {nbad:4d}   {gm:6.1f} {ms:6.2f} {20*math.log10(max(t530,1e-9)):+8.1f}  {mrho:.4f}  {wps}")
        for r in rr:
            bad=[]
            if np.isfinite(r["pm"]) and r["pm"]<thr: bad.append(f"PM{thr:.0f}")
            if r["gm"]<6: bad.append("GM6")
            if r["rho"]>=1.0: bad.append("UNSTABLE")
            if r["Ms"]>2.5: bad.append("Ms2.5")
            if 20*math.log10(max(r["Tpk530"],1e-9))>3.0: bad.append("T530")
            if bad: fails.append((n, r["v"], bad, round(r["pm"],1)))
    P(f"\nGATE 2 ({impl}): {len(res)} points; FAILS {len(fails)}")
    for f in fails[:40]: P(f"   {f}")
    # Re(T/w)20 at highway G
    Ghw = C.G_at(30.0, C.make_table(cfg["knots"]))
    dm = "fresh" if cfg["dmode"].startswith("fresh") else "held"
    for age in (0,10):
        re20 = min(B.re_t_over_w(112, cfg["ki"], cfg["kd"], C.G_at(v, C.make_table(cfg["knots"])), 20, age=age, dmode=cfg["dmode"], ema_hz=cfg["ema"]) for v in GRID)
        P(f"Re(T/w)20 worst age {age}: {re20:+.3f}  vs V295 {V295_RE20_age[age]:+.3f}  -> {'PASS' if re20>=V295_RE20_age[age] else 'FAIL'} ({re20/V295_RE20_age[age]:.2f}x)")
    txt = "\n".join(out)
    (HERE / f"gate_{impl}.txt").write_text(txt, encoding="utf-8")
    print(txt[:4000]); print(f"...[{time.time()-t0:.0f} s]")

if __name__ == "__main__":
    main()
