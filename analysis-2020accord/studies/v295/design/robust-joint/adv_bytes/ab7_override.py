# -*- coding: utf-8 -*-
"""ab7_override.py -- the trim under DRIVER TORQUE on r71b (engaged & steeringPressed or |bar|>=400): how much more does A
oppose the driver than V294?  |T_A - T_V294| and the trim itself (T - FF) on those frames, 1 kHz, my lane.  ANALYSIS ONLY."""
import numpy as np
KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
d = np.load(KIT + "/analysis-2020accord/studies/v295/plant/_scratch/cache/plant_r71b_v294.npz")
r = np.load("_scratch_ab2_route.npz")
sg = int(d["sg"])
n = len(r["T294"])
eng = np.repeat(d["eng"], 10)[:n]
hon = np.repeat((d["cs_pressed"] > 0.5) | (np.abs(d["bar"]) >= 400), 10)[:n] & eng
ff = (d["T1k_null"] * sg).astype(np.int64)                      # my lane == plib (ab2 [7]); plib null used for FF
tr294 = r["T294"] - ff
trA = r["TA"] - ff
for nm, m in (("hands-on engaged", hon), ("hands-off engaged", eng & ~hon)):
    print("%-18s %6.1f s: |trim| p50/p99/max  V294 %5.1f/%5.1f/%4d   A %5.1f/%5.1f/%4d ; |A-V294| p99 %.1f max %d"
          % (nm, m.sum() / 1000.0, np.percentile(np.abs(tr294[m]), 50), np.percentile(np.abs(tr294[m]), 99), np.abs(tr294[m]).max(),
             np.percentile(np.abs(trA[m]), 50), np.percentile(np.abs(trA[m]), 99), np.abs(trA[m]).max(),
             np.percentile(np.abs(trA[m] - tr294[m]), 99), np.abs(trA[m] - tr294[m]).max()))
