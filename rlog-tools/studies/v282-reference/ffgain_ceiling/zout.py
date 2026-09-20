# -*- coding: utf-8 -*-
"""Does the proposed one-sided OUTWARD static-friction feedforward land on the railing episodes?

Candidate under test (NOT cut, NOT flown, NOT approved):
    s_a   = tanh(angle_des / 1.0 deg)
    s_r   = tanh(angle_des_rate / 2.0 deg/s)
    z_out = LEVEL * g(v) * max(0, s_a * s_r) * s_a          g = 1.0 at <=8 m/s -> 0.0 at >=12 m/s
added inside the Accord rate-plant-FF branch alongside the existing hysteresis z, i.e. it joins
`accord_friction_z`, which enters the command as  inner_torque = -(z + ...)  -- so in the TORQUE
frame the command gains  -z_out.

Because max(0, s_a*s_r) is a non-negative gate, the expression reduces exactly to
    z_out = LEVEL * g(v) * s_a^2 * s_r   when s_a*s_r > 0, else 0
so its sign is sign(angle_des) in the +left frame and its magnitude saturates at LEVEL * g(v).
The hold term also carries sign(angle_des), so at a held or growing angle the two are CO-SIGNED:
z_out pushes in the same direction as whatever the hold term is already driving.

EXACTNESS: as in sweep.py, only the perturbation is computed.  total(level) = (p+i+f)/LAF - z_out
holds P, I and the observer at their logged values -- a REACH estimate, BELIEF, not a closed-loop
prediction.  The |FF|-alone column |hold + move + z_out| is pure arithmetic, EVIDENCE.

ANALYSIS ONLY.  Run: python zout.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ffrecon as F                      # noqa: E402
import v282cmp as C                      # noqa: E402
from sweep import route_frames, FS, longest_run   # noqa: E402

routes = [(rk, cfg) for rk, cfg in F.ROUTECFG.items()
          if cfg["ff_live"] and (C.CACHE / f"{rk}.npz").exists()]
LEVELS = [0.005, 0.010, 0.015, 0.020, 0.030]
PROPOSED = 0.020
GATE_BP, GATE_V = [8.0, 12.0], [1.0, 0.0]
S_A_DEG, S_R_DPS = 1.0, 2.0
BANDS = [(2.0, 8.0, "2-8"), (8.0, 12.0, "8-12 (ramp)"), (12.0, 15.0, "12-15 (gated off)"),
         (15.0, 99.0, ">15")]
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


def zout(ad, adr, v, level):
    s_a = np.tanh(ad / S_A_DEG)
    s_r = np.tanh(adr / S_R_DPS)
    g = np.interp(v, GATE_BP, GATE_V)
    return level * g * np.maximum(0.0, s_a * s_r) * s_a


# =================================================================================================
pr("=" * 118)
pr("0  THE TERM ITSELF, on logged demand (flown gain 0.5, engaged hands-off)")
pr("=" * 118)
pr("z_out is ONE-SIDED: zero while the desired angle unwinds, saturating at LEVEL*g(v) while it grows.")
pr(f"s_r = tanh(rate/{S_R_DPS:.1f}) reaches 0.995 at only 6 deg/s of desired-angle rate (the 2-8 m/s")
pr("MEDIAN rate is 6.5 deg/s), and s_a = tanh(angle/1.0) is 1.000 beyond ~4 deg.  So the term is")
pr("effectively FULL-ON, not tapered, over almost the whole outward-moving population.")
pr("")
pr(f"{'band':>18s} {'sec':>7s} {'% active':>9s} {'mean |z|':>9s} {'p99 |z|':>8s} {'max |z|':>8s} "
   f"{'% at >=0.95 of full':>20s} | {'% co-signed with cmd':>21s}")
stats0 = {}
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    z = zout(D["ad"], D["adr"], D["v"], PROPOSED)
    for lo, hi, bn in BANDS:
        bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
        if bm.sum() < 200:
            continue
        gfull = PROPOSED * np.interp(D["v"], GATE_BP, GATE_V)
        a = stats0.setdefault(bn, dict(n=0, nact=0, sz=0.0, mx=0.0, nfull=0, ncos=0, h=np.zeros(4000)))
        a["n"] += int(bm.sum())
        act = bm & (np.abs(z) > 1e-9)
        a["nact"] += int(act.sum())
        a["sz"] += float(np.abs(z[bm]).sum())
        a["mx"] = max(a["mx"], float(np.abs(z[bm]).max()))
        a["nfull"] += int((bm & (np.abs(z) >= 0.95 * np.maximum(gfull, 1e-12))).sum())
        a["ncos"] += int((act & (np.sign(-z) == np.sign(D["u0"]))).sum())
        a["h"] += np.histogram(np.minimum(np.abs(z[bm]), 0.03999), bins=np.arange(0, 0.04001, 1e-5))[0]
    del D
eb = np.arange(0, 0.04001, 1e-5)
for lo, hi, bn in BANDS:
    a = stats0.get(bn)
    if not a:
        continue
    cdf = np.cumsum(a["h"]) / max(a["h"].sum(), 1)
    p99 = float(eb[min(int(np.searchsorted(cdf, 0.99)) + 1, len(eb) - 1)])
    pr(f"{bn:>18s} {a['n']/FS:7.0f} {100.0*a['nact']/a['n']:9.2f} {a['sz']/a['n']:9.5f} {p99:8.5f} "
       f"{a['mx']:8.5f} {100.0*a['nfull']/a['n']:20.2f} | "
       f"{(100.0*a['ncos']/a['nact'] if a['nact'] else float('nan')):21.1f}")
pr("")

# =================================================================================================
pr("=" * 118)
pr("1  THE RAILING EPISODES BELOW 8 m/s -- is the term ON them, and co-signed?")
pr("=" * 118)
pr("Frames with |(p+i+f)/LAF| >= 1.0 at the flown gain 0.5, 2-8 m/s (the 16 episodes / 0.65 s).")
pr("")
pr(f"{'route':6s} {'rail fr':>8s} {'z_out mean':>11s} {'min':>8s} {'max':>8s} {'% at full':>10s} "
   f"{'% co-signed':>12s} {'|angle_des| med':>16s} {'rate med':>10s}")
railrows = []
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    z = zout(D["ad"], D["adr"], D["v"], PROPOSED)
    bm = D["mask"] & (D["v"] >= 2.0) & (D["v"] < 8.0)
    rail = bm & (np.abs(D["u0"]) >= 1.0)
    if rail.sum() == 0:
        pr(f"{cfg['tag']:6s} {0:8d}   -- no railing frames below 8 m/s --")
        del D
        continue
    az = np.abs(z[rail])
    cos = float(np.mean(np.sign(-z[rail]) == np.sign(D["u0"][rail])))
    pr(f"{cfg['tag']:6s} {int(rail.sum()):8d} {az.mean():11.5f} {az.min():8.5f} {az.max():8.5f} "
       f"{100.0*np.mean(az >= 0.95*PROPOSED):10.1f} {100.0*cos:12.1f} "
       f"{np.median(np.abs(D['ad'][rail])):16.1f} {np.median(np.abs(D['adr'][rail])):10.1f}")
    railrows.append((cfg["tag"], int(rail.sum()), float(az.mean()), cos))
    del D
tot = sum(r[1] for r in railrows)
if tot:
    pr("")
    pr(f"POOLED: {tot} railing frames below 8 m/s, mean |z_out| "
       f"{sum(r[2]*r[1] for r in railrows)/tot:.5f} of a {PROPOSED:.3f} level "
       f"({100*sum(r[2]*r[1] for r in railrows)/tot/PROPOSED:.1f} % of full value), "
       f"co-signed with the command on {100*sum(r[3]*r[1] for r in railrows)/tot:.1f} % of them.")
pr("")

# =================================================================================================
pr("=" * 118)
pr("2  ADDED RAILING, by level -- seconds, episodes, and the LONGEST episode")
pr("=" * 118)
acc = {}
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    for lo, hi, bn in BANDS:
        bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
        if bm.sum() < 200:
            continue
        for L in [0.0] + LEVELS:
            z = zout(D["ad"], D["adr"], D["v"], L)
            u = np.abs(D["u0"] - z)
            ffa = np.abs(D["hold"] + D["mv0"] + z)
            r = bm & (u >= 1.0)
            a = acc.setdefault((bn, L), dict(n=0, sec=0.0, eps=0, longest=0.0, durs=[],
                                             maxu=0.0, maxff=0.0, near=0))
            a["n"] += int(bm.sum())
            a["sec"] += float(r.sum() / FS)
            a["maxu"] = max(a["maxu"], float(u[bm].max()))
            a["maxff"] = max(a["maxff"], float(ffa[bm].max()))
            a["near"] += int((bm & (u >= 0.98) & (u < 1.0)).sum())
            for i0, i1 in C.runs(r, D["t"], min_s=0.0):
                a["eps"] += 1
                a["durs"].append((i1 - i0) / FS)
            a["longest"] = max(a["longest"], longest_run(r, D["t"]))
    del D
for lo, hi, bn in BANDS:
    if (bn, 0.0) not in acc:
        continue
    b0 = acc[(bn, 0.0)]
    pr(f"--- {bn} m/s   ({b0['n']/FS:.0f} s engaged hands-off, gate g(v) = "
       f"{float(np.interp((lo+min(hi,14))/2, GATE_BP, GATE_V)):.2f} mid-band)")
    pr(f"{'level':>7s} {'s at rail':>10s} {'x base':>7s} {'episodes':>9s} {'longest s':>10s} "
       f"{'p90 s':>7s} {'max|TOT|':>9s} {'max|FF|':>8s} {'fr in [0.98,1)':>15s}")
    for L in [0.0] + LEVELS:
        a = acc[(bn, L)]
        d = np.array(a["durs"]) if a["durs"] else np.array([0.0])
        xb = (a["sec"] / b0["sec"]) if b0["sec"] > 0 else float("nan")
        pr(f"{L:7.3f} {a['sec']:10.3f} {xb:7.2f} {a['eps']:9d} {a['longest']:10.3f} "
           f"{np.percentile(d, 90):7.3f} {a['maxu']:9.3f} {a['maxff']:8.3f} {a['near']:15d}")
    pr("")

# =================================================================================================
pr("=" * 118)
pr("3  WHERE THE TERM IS LARGEST vs WHERE THE RAIL IS -- the s_a shape question")
pr("=" * 118)
pr("s_a = tanh(angle_des/1.0) makes z_out MAXIMAL at large angle.  Below is |TOT| headroom (1.0 -")
pr("|TOT|) against |angle_des|, at the flown gain 0.5 and 2-8 m/s, so the two shapes can be compared.")
pr("")
AB = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 120), (120, 200), (200, 300), (300, 400)]
hz = {}
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    z = zout(D["ad"], D["adr"], D["v"], PROPOSED)
    u = np.abs(D["u0"])
    bm = D["mask"] & (D["v"] >= 2.0) & (D["v"] < 8.0)
    aad = np.abs(D["ad"])
    for a0, a1 in AB:
        s = bm & (aad >= a0) & (aad < a1)
        if s.sum() == 0:
            continue
        h = hz.setdefault((a0, a1), dict(n=0, sumz=0.0, mxu=0.0, nrail=0, nnear=0, minhead=9.9))
        h["n"] += int(s.sum())
        h["sumz"] += float(np.abs(z[s]).sum())
        h["mxu"] = max(h["mxu"], float(u[s].max()))
        h["nrail"] += int((s & (u >= 1.0)).sum())
        h["nnear"] += int((s & (u >= 0.95)).sum())
        h["minhead"] = min(h["minhead"], float((1.0 - u[s]).min()))
    del D
pr(f"{'|angle_des| deg':>16s} {'sec':>8s} {'mean|z_out|':>12s} {'max|TOT|':>9s} "
   f"{'min headroom':>13s} {'rail frames':>12s} {'fr >=0.95':>10s}")
for a0, a1 in AB:
    h = hz.get((a0, a1))
    if not h:
        continue
    pr(f"{f'{a0}-{a1}':>16s} {h['n']/FS:8.1f} {h['sumz']/h['n']:12.5f} {h['mxu']:9.3f} "
       f"{h['minhead']:13.3f} {h['nrail']:12d} {h['nnear']:10d}")
pr("")

with open(os.path.join(HERE, "ZOUT-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
