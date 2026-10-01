import sys, os
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
sys.path.insert(0, r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile")
import numpy as np, math
from rec_joint import freq_eval
import harness_freq as HF
GRID = {3.0:(400,500,600,700,800,900,1000,1100,1200), 5.0:(400,500,600,700,800,900,1000,1200), 8.0:(500,600,700,800,900,1000,1200),
        12.5:(700,800,900,1000,1100,1200,1300,1500), 19.0:(1200,1500,1800,2000,2500,3000), 26.0:(1500,2000,2500,3000,3500), 30.0:(1500,2000,2500,3000,3500)}
for kd in (16, 20, 24):
    for fi in (0.3, 0.45, 0.6):
        cells=[]
        for v,G in GRID.items():
            best=None
            for kp in G:
                f=freq_eval(kp, HF.ki_for(kp,fi), kd, v)
                if f["safe"]: best=(kp,f)
            if best: cells.append(f"{v:g}:{best[0]}(wPM{best[1]['worst_pm']:.0f},wTr{best[1]['worst_Tr163']:.2f})")
            else: cells.append(f"{v:g}:none")
        print(f"Kd {kd} fI {fi}: max credible-safe Kp | "+" ".join(cells))
