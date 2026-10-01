# -*- coding: utf-8 -*-
"""b_env.py -- parallel full-factorial envelope G(v) for an implementation (dmode, kd, ki).  FRF-only gmax (fast); the
final tables are stability-checked by the exact monodromy in b_gate.py.  ANALYSIS ONLY.
usage: python b_env.py <dmode:held|fresh> <kd> <ki> [tag]  -> _scratch/.../B-robust-margins/env_<tag>.json + .txt"""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b_lib as B
import c1r2_members as M
KIT = HERE.parents[3]
OUT = KIT / "_scratch" / "angle_loop" / "B-robust-margins"
OUT.mkdir(parents=True, exist_ok=True)
SPEEDS = sorted(set([round(x,2) for x in np.arange(1.0,35.01,0.25)] + [3.1,8.0,11.9,17.0,26.9]))
NAMES = [(n,45.0) for n in M.TIER_A] + [(n,30.0) for n in M.TIER_B]
def job(args):
    v,dmode,kd,ki=args
    out={}
    for n,thr in NAMES:
        out[n]=B.gmax(n,v,thr,112,ki,kd,dmode=dmode,exact=False)
    return v,out
def main():
    DMODE=sys.argv[1]; KD=int(sys.argv[2]); KI=int(sys.argv[3])
    tag=sys.argv[4] if len(sys.argv)>4 else f"{DMODE}_kd{KD}_ki{KI}"
    t0=time.time()
    with Pool(14) as pool:
        res=dict(pool.map(job,[(v,DMODE,KD,KI) for v in SPEEDS]))
    (OUT/f"env_{tag}.json").write_text(json.dumps({str(v):r for v,r in res.items()}))
    lines=[f"# env {tag}: dmode {DMODE} kd {KD} ki {KI} kp 112; env=min gated gmax; Kp_eff=112*G/256"]
    for v in SPEEDS:
        r=res[v]
        eA=min((r[n],n) for n,_ in NAMES if n in M.TIER_A)
        eB=min((r[n],n) for n,_ in NAMES if n in M.TIER_B)
        e=min(eA[0],eB[0])
        lines.append(f"{v:6.2f} envA {eA[0]:5d}({eA[1]:>22s}) envB {eB[0]:5d}({eB[1]:>22s}) env {e:5d} Kp_eff {112*e/256:6.0f}")
    (OUT/f"env_{tag}.txt").write_text("\n".join(lines))
    print("\n".join(lines[:1]+[lines[i] for i in range(1,len(lines)) if abs(SPEEDS[i-1]-round(SPEEDS[i-1]))<0.01 and SPEEDS[i-1] in (1,3,5,8,10,11,12,13,15,17,19,22,26,27,30)]))
    print(f"[{time.time()-t0:.0f} s] -> env_{tag}.json")
if __name__=="__main__":
    main()
