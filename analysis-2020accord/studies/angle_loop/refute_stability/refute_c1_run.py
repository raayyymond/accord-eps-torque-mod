# -*- coding: utf-8 -*-
"""Validate the independent C1 model against design/refuter anchors, then attack C1."""
import math
import sys
import os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refute_c1_ind as R

def anchor():
    print("="*100)
    print("VALIDATION: independent model vs design/refuter published anchors")
    print("="*100)
    # C0 control: reproduce the refuter's J_hi@11.9 = 40.7 under C0 (G x1 C0 table, kp450 ki199)
    import c1_lib as CL
    # C0 table (not rebased): C0 uses G C0 (half of C0_TABLE_X2) with kp 450 ki 199
    C0_TBL = [(691,256,249),(1152,284,338),(1843,341,901),(2880,569,2332),(4378,1422,724),(5990,1707,0),(0xFFFF,1707,0)]
    def G0(v):
        return R.CL.cave_G(R.CL.spd_counts(v), C0_TBL)
    p = R.FAM["J_hi"].at(11.9)
    disc = R.rigid_disc(p.J, p.b, p.k)
    pm,gm = R.margins(G0(11.9), 450, 199, 16, disc, d=2)
    print(f"  C0 J_hi@11.9 PM = {pm:.1f} (refuter published 40.7)  Kp_eff_C0={450*G0(11.9)/256:.0f}")
    # C1 anchors
    checks = [("nominal", 1.0, 62.3), ("J_hi", 1.0, 46.5), ("b_lo", 1.0, 53.5), ("tau6", 1.0, 60.2),
              ("b_lo*J_hi", 10.0, 35.2), ("b_lo*J_hi*tau6", 10.0, 32.7), ("J1.0", 11.9, 32.0),
              ("b_q", 27.0, 32.8), ("J_hi2", 11.9, 39.8), ("J1.3", 11.9, 22.7), ("ms_free", 11.9, 7.6)]
    print("  C1 member anchors (my PM vs design page PM):")
    for nm, v, want in checks:
        pm,gm = R.pm_of(nm, v)
        print(f"    {nm:18s}@{v:5.1f}  mine {pm:6.1f}   design {want:6.1f}   d{pm-want:+.1f}")

def sweep_members(members, vgrid, bar, tag, extra_age=0):
    worst = {}
    fails = []
    for nm in members:
        best = (1e9, None)
        for v in vgrid:
            try:
                pm, gm = R.pm_of(nm, v, extra_age=extra_age)
            except Exception as e:
                continue
            if not math.isfinite(pm):
                continue
            if pm < best[0]:
                best = (pm, v)
            if pm < bar:
                fails.append((nm, v, pm, gm))
        worst[nm] = best
    print(f"\n--- {tag} (bar PM>={bar}) ---")
    for nm in members:
        pm, v = worst[nm]
        flag = " <<< BELOW BAR" if pm < bar else ""
        print(f"   {nm:20s} min PM {pm:6.1f} @ {v}{flag}")
    return fails

def fine_grid():
    # 0.25 m/s grid 1..32 plus the plant knots
    g = sorted(set([round(x,3) for x in np.arange(1.0, 32.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
    return g

if __name__ == "__main__":
    anchor()
    vg = fine_grid()
    print("\n"+"="*100+"\nATTACK 1: tier A (nominal must be >=45 everywhere; all single-corner credible)\n"+"="*100)
    fA = sweep_members(list(R.FAM.keys())[:0] + ["nominal","J_lo","J_hi","b_lo","b_hi","tau0","tau6","F_hi","F_lo"], vg, 45.0, "TIER A single-corner")
    print("\n"+"="*100+"\nATTACK 2: tier B combined members, age 0 (design claims all >=30)\n"+"="*100)
    comboB = ["b_lo*J_hi","b_lo*J_hi*tau6","b_lo*tau6","J_hi*tau6","b/1.9*J_hi","b_lo*J0.3","J_hi2","J1.0","b_q",
              "nominal+h10","b_lo+h10","J_hi+h10"]
    fB = sweep_members(comboB, vg, 30.0, "TIER B (design-gated)")
    print("\n"+"="*100+"\nATTACK 3: combined members WITH 10-tick hold aging (design gated +h10 ONLY on single members)\n"+"="*100)
    combo_h = ["b_lo*J_hi+hA","b_lo*J_hi*tau6+hA","J_hi2+hA","J1.0+hA","b_q+hA","b/1.9*J_hi+hA"]
    fH = sweep_members(combo_h, vg, 30.0, "combined + hold age 10 (UNGATED by C1)")
    print("\n"+"="*100+"\nATTACK 4: extra combined members the design did not gate\n"+"="*100)
    extra = ["b_q*J_hi","b_q*J1.0","b_q*tau6","J1.0*tau6","b_q0*J_hi"]
    fE = sweep_members(extra, vg, 30.0, "extra combos (UNGATED)")
    print("\n"+"="*100+"\nSUMMARY OF SUB-BAR POINTS\n"+"="*100)
    for tag, fl in [("A<45",fA),("B<30",fB),("comboB+h10<30",fH),("extra<30",fE)]:
        print(f"  {tag}: {len(fl)} points")
        # show the worst few per member
        bym = {}
        for nm,v,pm,gm in fl:
            bym.setdefault(nm,[]).append((pm,v))
        for nm,l in bym.items():
            l.sort()
            print(f"     {nm:22s} worst {l[0][0]:.1f}@{l[0][1]}  (n={len(l)}, span v {min(x[1] for x in l)}..{max(x[1] for x in l)})")
