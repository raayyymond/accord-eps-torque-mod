# -*- coding: utf-8 -*-
"""a6 -- CAN ONE DRIVE READ IT?  and what the pair actually does below the metric's floor.

(1) THE NOISE FLOOR OF THE METRIC ITSELF.  The predicted move is J 1.351 -> 1.058, a factor 1.28.
    Two routes flown on the IDENTICAL rev 6.4 config read 1.290 and 1.492 (1.16x apart).  Bootstrap
    the metric by RUN (not by window -- windows inside a run are not independent) and report the
    spread a single new drive would have to beat.

(2) THE LOW-SPEED AUTHORITY THE PAIR ACTUALLY DELIVERS.  Combine, at each speed, the three things
    SteerKP 1->3 + Q 1.0->0.6 do to the feedback path:  P gain (kp+lsf), I gain (1+lsf/kp), and the
    notch's own gain at the frequency low-speed steering lives at.  The metric scores none of it.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

OUT = HERE / "out"
FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)
RNG = np.random.default_rng(20260920)


def per_run_windows(route, nps=1024, vmin=15.0, run_s=30.0):
    """Same window set as adv_core.extract, but tagged with the run each window came from."""
    S = A.V.load(route)
    with np.errstate(divide="ignore", invalid="ignore"):
        laff = np.where(np.abs(S["out"]) > 5e-3, -(S["p"] + S["i"] + S["f"]) / S["out"], np.nan)
    laf = float(np.nanmedian(laff[S["active"]]))
    m = (S["active"] & ~S["pressed"] & (S["v"] >= vmin)
         & np.isfinite(S["setpoint"]) & np.isfinite(S["la_act"]) & np.isfinite(S["la_pose"])
         & np.isfinite(S["model"]) & np.isfinite(S["out"]))
    from scipy import signal as sg
    w = sg.get_window("hann", nps)
    X = np.nan_to_num(S["model"]); Y = np.nan_to_num(S["la_pose"])
    pe, px, tag = [], [], []
    f = np.fft.rfftfreq(nps, A.DT)
    b = (f >= A.BAND[0]) & (f <= A.BAND[1])
    for ri, (a, bb) in enumerate(A.V.runs(m, S["t"], min_s=run_s)):
        for s in range(a, bb - nps + 1, nps // 2):
            e = s + nps
            if float(np.mean(S["sat"][s:e])) > 0.02 or not np.isfinite(S["v"][s:e]).all():
                continue
            ex = np.fft.rfft(sg.detrend(X[s:e]) * w)
            ey = np.fft.rfft(sg.detrend(Y[s:e]) * w)
            pe.append(float(np.sum(np.abs((ex - ey)[b]) ** 2)))
            px.append(float(np.sum(np.abs(ex[b]) ** 2)))
            tag.append(f"{route}|{ri}")
    del S
    return np.array(pe), np.array(px), np.array(tag)


def boot(pe, px, tag, n=4000):
    runs = np.unique(tag)
    idx = {r: np.where(tag == r)[0] for r in runs}
    out = []
    for _ in range(n):
        pick = RNG.choice(runs, size=len(runs), replace=True)
        ii = np.concatenate([idx[r] for r in pick])
        out.append(pe[ii].sum() / px[ii].sum())
    return np.array(out)


def main():
    print("=" * 112)
    print("1. THE NOISE FLOOR.  Metric per route and per run, and a run-cluster bootstrap.")
    allpe, allpx, alltag = [], [], []
    print(f"{'route':22s} {'runs':>5s} {'win':>4s} {'J':>7s}   per-run J")
    for r in A.T64 + [A.V282[0]]:
        pe, px, tag = per_run_windows(r)
        runs = np.unique(tag)
        pr = [pe[tag == q].sum() / px[tag == q].sum() for q in runs]
        print(f"{r:22s} {len(runs):5d} {len(pe):4d} {pe.sum()/px.sum():7.3f}   " +
              " ".join(f"{x:.2f}" for x in pr))
        if r in A.T64:
            allpe.append(pe); allpx.append(px); alltag.append(tag)
    pe = np.concatenate(allpe); px = np.concatenate(allpx); tag = np.concatenate(alltag)
    bs = boot(pe, px, tag)
    lo, hi = np.quantile(bs, [0.025, 0.975])
    print()
    print(f"   T64 pooled J = {pe.sum()/px.sum():.4f}   run-cluster bootstrap 95 % CI [{lo:.3f}, {hi:.3f}]"
          f"   (width {hi-lo:.3f} = {(hi-lo)/(pe.sum()/px.sum())*100:.0f} % of J)")
    print(f"   predicted ARM-KP2 J = 1.058.   Is it outside the CI of the BASELINE?  "
          f"{'YES' if 1.058 < lo else 'NO'}")
    print()
    print("   AND THE DRIVE THAT WOULD READ IT BACK.  A new drive is ONE route; simulate a single")
    print("   route by resampling n runs from the pool and ask how often its J lands below 1.16")
    print("   (the config's own PASS gate) and below 1.30 (its FAIL gate) with NO change made.")
    runs = np.unique(tag)
    for nruns in (2, 3, 4, 6, 8):
        if nruns > len(runs):
            continue
        sims = []
        for _ in range(4000):
            pick = RNG.choice(runs, size=nruns, replace=True)
            ii = np.concatenate([np.where(tag == q)[0] for q in pick])
            sims.append(pe[ii].sum() / px[ii].sum())
        sims = np.array(sims)
        print(f"      a {nruns}-run drive, NOTHING CHANGED:  P(J <= 1.16) = {np.mean(sims<=1.16)*100:5.1f} %"
              f"   P(J >= 1.30) = {np.mean(sims>=1.30)*100:5.1f} %   median {np.median(sims):.3f}"
              f"   5-95 % [{np.quantile(sims,0.05):.2f}, {np.quantile(sims,0.95):.2f}]")
    print(f"   (the pool has {len(runs)} runs across the two rev 6.4 routes; "
          f"a typical single route contributed {len(runs)/2:.0f})")

    print()
    print("=" * 112)
    print("2. WHAT THE PAIR DOES BELOW THE METRIC'S FLOOR.  Feedback-path authority vs the flown")
    print("   config, at the frequency low-speed steering actually uses.")
    print(f"{'v m/s':>6s} {'notch f0':>9s} {'f used':>7s} | {'P x':>6s} {'I x':>6s} {'notch x':>8s} "
          f"{'net P x':>8s} {'net I x':>8s} | {'with Ki 0.6 repair':>19s}")
    rows = []
    for v, fu in ((2.0, 0.30), (4.0, 0.30), (6.0, 0.40), (8.0, 0.40), (12.0, 0.50),
                  (17.0, 0.50), (22.0, 0.50), (28.0, 0.50)):
        l = float(A.lsf_of(np.array([v]))[0])
        f0 = A.mode_hz(np.array([v]))
        n0 = abs(A.notch_H(np.array([fu]), f0, 1.0)[0, 0])
        n1 = abs(A.notch_H(np.array([fu]), f0, 0.6)[0, 0])
        Px = (3.0 + l) / (1.0 + l)
        Ix = (1 + l / 3.0) / (1 + l / 1.0)
        print(f"{v:6.1f} {float(f0[0]):9.3f} {fu:7.2f} | {Px:6.3f} {Ix:6.3f} {n1/n0:8.3f} "
              f"{Px*n1/n0:8.3f} {Ix*n1/n0:8.3f} | {Ix*n1/n0*2.0:19.3f}")
        rows.append(dict(v=v, f=fu, P=Px, I=Ix, notch=n1 / n0, netP=Px * n1 / n0, netI=Ix * n1 / n0))
    print()
    print("   The low-speed outward deficit that REPORT.md measured (+0.0231 torque at 0.6-2.5 deg)")
    print("   is carried by whichever integrator is enabled -- the PID's I when the observer is off,")
    print("   the observer otherwise.  This table is what SteerKP 3.0 + Q 0.6 does to that carrier.")

    print()
    print("=" * 112)
    print("3. AND THE PART OF THE DRIVE THE METRIC NEVER SEES, AS A SHARE OF THE WHOLE")
    tot = {}
    for r in A.T64:
        S = A.V.load(r)
        act = S["active"] & ~S["pressed"]
        for lo_, hi_ in ((0, 8), (8, 15), (15, 99)):
            tot[(lo_, hi_)] = tot.get((lo_, hi_), 0) + int((act & (S["v"] >= lo_) & (S["v"] < hi_)).sum())
        del S
    n = sum(tot.values())
    for k, vv in tot.items():
        print(f"      {k[0]:2d}-{k[1]:2d} m/s : {vv/n*100:5.1f} %  ({vv/100.0:6.0f} s)   "
              f"{'SCORED' if k[0] >= 15 else 'NOT SCORED by the metric'}")
    json.dump(dict(lowspeed=rows, ci=[float(lo), float(hi)]), open(OUT / "a6_power.json", "w"), indent=1)


if __name__ == "__main__":
    main()
