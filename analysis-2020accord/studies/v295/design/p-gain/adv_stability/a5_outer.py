# -*- coding: utf-8 -*-
"""a5 -- (c) the OUTER loop, my own linearisation (adv_outer), in three steps:
  1. method check: my L_out vs the harness's outer_frf at small angle (same assumptions) and vs the designer's s12 rows;
  2. ANCHORS against the on-car record, with the spring linearised at the hold angle (k*sech^2):
     (A) r71-old = V293 (no trim) + fork rev 2 (Kp 0.85, Ki 0.30, LAF 14, friction 0.011 relay live) LIMIT-CYCLED at 2.34 Hz
         +-6 deg on every sustained curve > 20 m/s (21.8 m/s, angle 16-29 deg) -> a faithful world must put it at GM <~ 1;
     (B) r71b = V294 + r1 did NOT limit-cycle there (P4 not fired), with a rate-only 1.95 Hz +10.3 dB line on hard
         curves > 15 m/s -> stable but lightly damped;
     (C) r71b at > 20 m/s: NO 1-4 Hz prominence in angle (-1.40 dB) or command (-1.98 dB) -> no strong resonance;
  3. the candidate vs V294 at the drive's operating points (same HOLD TORQUE -> each build's own idx) and on a grid of
     (v, theta0), every member, relay on/off, pipe 22/33/44 ms, kappa 1.0/1.15."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lin as AL  # noqa: E402
import adv_outer as AO  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a5_outer_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")


sf = np.load(os.path.join(HERE, "a1_surface.npz"))
S294, Sc = sf["S294"].astype(float), sf["Sc"].astype(float)
KP294 = np.full(256, 960)
import adv_lib as A  # noqa: E402
KPC = A.table(A.CAND_X, A.CAND_Y)
R1 = dict(kp=0.9, ki=0.3, laf=14.0, fric=0.011)
REV2 = dict(kp=0.85, ki=0.3, laf=14.0, fric=0.011)
F = np.concatenate([np.linspace(0.05, 1.0, 40), np.geomspace(1.0, 45.0, 700)[1:]])
fam = VP.family()


def mg(L):
    m = AL.margins(F, L)
    return m["Ms"], m["GM"], m["f_GM"], m["f_Ms"]


def member_at(nm, v):
    p = fam[nm].at(v)
    return p.J, p.b, p.k, AO.sat_prior(v)


# ---------------- 1. method check against the harness's outer_frf (small angle, idx 60 flat surface = V294 slope)
P("1. METHOD CHECK: my L_out vs the harness outer_frf (theta0 = 0, k small-angle, V294, relay on, pipe 22)")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H  # noqa: E402
c294 = H.Cells.v294()
for nm in ("nominal", "light_b"):
    for v in (3.1, 8.0, 17.0, 26.9):
        p = fam[nm].at(v)
        Lh = H.outer_frf(c294, p, v, F, relay=True, pipe_ms=22, idx_op=60)
        J, b, k, sat = member_at(nm, v)
        Lm = AO.outer_L(F, v, 0.0, J, b, k, sat, 960.0, AO.slope_at(S294, 60), R1, pipe_ms=22, tau=p.tau_ms, k_loc=k)
        a, bb = mg(Lh), mg(Lm)
        P("  %-8s v %4.1f: harness Ms %.3f GM %.3f@%.2f | mine Ms %.3f GM %.3f@%.2f | max |Lm/Lh - 1| %.3f" % (
            nm, v, a[0], a[1], a[2], bb[0], bb[1], bb[2], float(np.max(np.abs(Lm / Lh - 1)))))

# ---------------- designer's s12 rows (same idx both builds, small-angle k), my numbers
P("\n   designer's s12 op points, MY linearisation, small-angle k, same idx for both builds (their convention):")
ops = [("low-speed st", 3.1, 14), ("low-speed tu", 3.1, 62), ("hold 5-10", 8.0, 50), ("hard 5-10", 8.0, 75),
       ("hold 10-15", 12.0, 36), ("straight 10+", 17.0, 6), ("hold 15-22", 17.0, 34), ("hard 15-22", 17.0, 50),
       ("hold 22+", 26.9, 18), ("straight 22+", 26.9, 6)]
for nm in ("nominal", "b_lo", "J_hi", "light_b"):
    for lab, v, i0 in ops:
        J, b, k, sat = member_at(nm, v)
        r = []
        for S, KP in ((S294, KP294), (Sc, KPC)):
            L = AO.outer_L(F, v, 0.0, J, b, k, sat, float(KP[i0]), AO.slope_at(S, i0), R1, k_loc=k)
            r.append(mg(L))
        P("  %-8s %-13s v %4.1f i %3d: V294 Ms %.2f GM %.2f | cand Ms %.2f GM %.2f" % (nm, lab, v, i0, r[0][0], r[0][1], r[1][0], r[1][1]))

# ---------------- 2. anchors
P("\n2. ANCHORS (spring linearised at theta0: k_loc = k sech^2(theta0/sat))")
P("(A) r71-old: V293 (no trim, FF slope = V294's) + fork rev 2, v 21.8, sustained curve 16-29 deg -- the car LIMIT-CYCLED at 2.34 Hz")
for nm in ("light_b", "nominal", "b_lo", "J_hi", "J_hi2", "ms_free"):
    J, b, k, sat = member_at(nm, 21.8)
    row = []
    for th0 in (16.0, 22.0, 29.0):
        T0 = k * sat * np.tanh(th0 / sat)
        i0 = AO.idx_for_torque(S294, T0)
        L = AO.outer_L(F, 21.8, th0, J, b, k, sat, 0.0, AO.slope_at(S294, i0), REV2, trim=False)
        L0 = AO.outer_L(F, 21.8, th0, J, b, k, sat, 0.0, AO.slope_at(S294, i0), REV2, trim=False, k_loc=k)
        a, a0 = mg(L), mg(L0)
        row.append("th %2.0f (T %4.0f idx %3d): GM %.2f@%.2fHz Ms %.1f [small-angle k: GM %.2f@%.2f]" % (th0, T0, i0, a[1], a[2], a[0], a0[1], a0[2]))
    P("   %-8s %s" % (nm, " | ".join(row)))
P("(B) r71b V294 + r1 on its sustained curves (drive medians: 15-19 m/s 18.4 deg idx 38 ; 19-22 9.8 deg idx 38 ; 22+ 11.0 deg idx 33) -- no limit cycle; rate-only 1.95 Hz line")
P("(C) r71b V294 + r1 straights (idx < 9, angle ~1 deg) at > 20 m/s -- no 1-4 Hz prominence")
drive_ops = [("curve 15-19", 17.0, 18.4, 38), ("curve 19-22", 20.5, 9.8, 38), ("curve 22+", 26.9, 11.0, 33),
             ("straight 22+", 26.9, 0.6, 5), ("straight 15-22", 17.0, 0.6, 5), ("straight 10-15", 12.0, 0.6, 5),
             ("straight 5-10", 8.0, 1.2, 5), ("straight 0-5", 3.1, 1.5, 5),
             ("hold 10-15", 12.0, 9.6, 36), ("hold 5-10", 8.0, 27.0, 45), ("hard 5-10", 8.0, 76.0, 75),
             ("low-speed turn", 3.1, 161.0, 80)]
rows = []
for nm in ("light_b", "nominal", "b_lo", "b_hi", "J_lo", "J_hi", "J_hi2", "ms_free", "tau6"):
    for lab, v, th0, i294 in drive_ops:
        J, b, k, sat = member_at(nm, v)
        tau = fam[nm].tau_ms
        T0 = S294[i294]                                   # the torque V294 delivered there on the drive
        ic = AO.idx_for_torque(Sc, T0)                    # the candidate's idx for the same hold torque
        res = dict(member=nm, op=lab, v=v, th0=th0, i294=i294, icand=ic, T0=T0)
        for tag, S, KP, ii in (("V294", S294, KP294, i294), ("cand", Sc, KPC, ic), ("cand_same_idx", Sc, KPC, i294)):
            for relay in (True, False):
                for pipe in (22.0, 33.0, 44.0):
                    for kap in (1.0, 1.15):
                        if (not relay or kap != 1.0) and pipe != 22.0:
                            continue
                        L = AO.outer_L(F, v, th0, J, b, k, sat, float(KP[ii]), AO.slope_at(S, ii), R1, pipe_ms=pipe,
                                       tau=tau, relay=relay, kappa=kap)
                        res["%s_r%d_p%d_k%.2f" % (tag, relay, pipe, kap)] = mg(L)
        rows.append(res)
for r in rows:
    a, c, cs = r["V294_r1_p22_k1.00"], r["cand_r1_p22_k1.00"], r["cand_same_idx_r1_p22_k1.00"]
    a3, c3 = r["V294_r1_p33_k1.00"], r["cand_r1_p33_k1.00"]
    ak, ck = r["V294_r1_p22_k1.15"], r["cand_r1_p22_k1.15"]
    P("  %-8s %-15s v %4.1f th %5.1f idx %3d->%3d: V294 Ms %.2f GM %.2f@%.2f | cand Ms %.2f GM %.2f@%.2f (same-idx %.2f/%.2f) | pipe33 GM %.2f->%.2f | kappa1.15 GM %.2f->%.2f" % (
        r["member"], r["op"], r["v"], r["th0"], r["i294"], r["icand"], a[0], a[1], a[2], c[0], c[1], c[2], cs[0], cs[1],
        a3[1], c3[1], ak[1], ck[1]))
json.dump(rows, open(os.path.join(HERE, "a5_outer.json"), "w"), default=float)

# ---------------- 3. grid: every member, speed, hold angle (T0 = the member's static hold at theta0)
P("\n3. GRID: worst candidate margin vs V294 over theta0 0..30 deg (T0 = member's static hold), relay on, pipe 22")
grid = []
for nm in ("light_b", "nominal", "b_lo", "b_hi", "J_lo", "J_hi", "J_hi2", "ms_free", "tau6", "tau0"):
    for v in (3.1, 5.0, 8.0, 12.0, 17.0, 21.8, 26.9):
        J, b, k, sat = member_at(nm, v)
        for th0 in (0.0, 1.0, 2.0, 5.0, 8.0, 11.0, 15.0, 20.0, 25.0, 30.0):
            T0 = k * sat * np.tanh(th0 / sat)
            if T0 > S294[238]:
                continue
            i294 = AO.idx_for_torque(S294, T0)
            ic = AO.idx_for_torque(Sc, T0)
            L0 = AO.outer_L(F, v, th0, J, b, k, sat, 960.0, AO.slope_at(S294, i294), R1, tau=fam[nm].tau_ms)
            L1 = AO.outer_L(F, v, th0, J, b, k, sat, float(KPC[ic]), AO.slope_at(Sc, ic), R1, tau=fam[nm].tau_ms)
            a, c = mg(L0), mg(L1)
            grid.append((nm, v, th0, i294, ic, a[0], a[1], c[0], c[1], a[2], c[2]))
for nm in sorted({g[0] for g in grid}):
    G = [g for g in grid if g[0] == nm]
    wgm = min(G, key=lambda g: g[8])
    wr = min(G, key=lambda g: g[8] / g[6])
    wms = max(G, key=lambda g: g[7])
    P("  %-8s min cand GM %.2f (V294 %.2f) at v %.1f th %.0f idx %d->%d | worst GM ratio %.3f at v %.1f th %.0f (%.2f->%.2f) | max cand Ms %.2f (V294 %.2f) at v %.1f th %.0f" % (
        nm, wgm[8], wgm[6], wgm[1], wgm[2], wgm[3], wgm[4], wr[8] / wr[6], wr[1], wr[2], wr[6], wr[8], wms[7], wms[5], wms[1], wms[2]))
    P("           cand GM < 1.5: %d of %d ; cand GM < V294 GM where V294 GM < 2: %s" % (
        sum(g[8] < 1.5 for g in G), len(G), [(g[1], g[2], round(g[6], 2), round(g[8], 2)) for g in G if g[6] < 2 and g[8] < g[6]][:12]))
json.dump(grid, open(os.path.join(HERE, "a5_grid.json"), "w"), default=float)
out.close()
