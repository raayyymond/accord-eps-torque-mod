import sys, os, math, json
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
sys.path.insert(0, r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
import numpy as np
import harness_freq as HF
from dataclasses import replace
C0 = dict(zip(HF.SPEEDS, (450,500,600,1000,2500,3000,3000)))
rows=[]; n_unst={'C0':0,'V295':0,'V282':0}; n=0; dz=[]
for v in (3.0, 8.0, 12.5, 19.0, 26.0):
    base = HF.plant_at("nominal", v)
    for f2 in (13.0, 16.0, 20.0, 24.0):
        for r2 in (0.2, 0.5):
            for z2 in (0.02, 0.05):
                p = replace(base, f2=f2, r2=r2, zeta2=z2)
                c = HF.Ctl(kp=C0[v], ki=HF.ki_for(C0[v],0.55), kd=16)
                out={}
                for nm,cc in (('C0',c),('V295',HF.V295),('V282',HF.V282)):
                    r = HF.metrics(cc, p, exact=True)
                    out[nm]=(r['stable'], r['hfmode'])
                    if not r['stable']: n_unst[nm]+=1
                n+=1
                # open-plant flexible-mode zeta: the plant's own pole near f2
                A,B,C,D = p.ss(); ev=np.linalg.eigvals(A); 
                fl=[(abs(e)/(2*np.pi), -e.real/abs(e)) for e in ev if abs(e)/(2*np.pi)>5]
                zo=min(fl,key=lambda t:t[1]) if fl else (float('nan'),float('nan'))
                dz.append(out['C0'][1][1]-zo[1] if out['C0'][0] else float('nan'))
                rows.append(f"v {v:4g} f2 {f2:4g} r2 {r2} z2 {z2}: open {zo[0]:.1f}Hz z{zo[1]:.3f} | C0 {'ok' if out['C0'][0] else 'UNSTABLE'} {out['C0'][1][0]:.1f}Hz z{out['C0'][1][1]:.3f} | V295 {'ok' if out['V295'][0] else 'UNSTABLE'} z{out['V295'][1][1]:.3f} | V282 {'ok' if out['V282'][0] else 'UNSTABLE'} z{out['V282'][1][1]:.3f}")
print("\n".join(rows))
print("rows", n, "unstable:", n_unst, "C0 zeta shift vs open (min,max):", np.nanmin(dz), np.nanmax(dz))
