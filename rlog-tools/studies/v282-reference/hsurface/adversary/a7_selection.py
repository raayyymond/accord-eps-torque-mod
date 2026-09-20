"""ADVERSARY A7 - selection bias, amplitude confounding, exposure weighting, and a test for a contaminated INPUT.

Five attacks, in order of how much they could change a ranking:

 A. AMPLITUDE IS CONFOUNDED WITH THE BUILD. The in-band demand RMS is not matched between the groups (A2:
    0.161 for V282 vs 0.090 for T64 at 0.08-0.25 Hz). The torque routes also flew a 14% lower learned
    `CalibratedLateralAcceleration` (2.21-2.35 vs 2.67-2.69), which is the curve-speed controller's own lateral
    budget, so they planned smaller corners. On a plant with saturation and Coulomb friction |H| is amplitude
    dependent, so a between-group |H| difference and an amplitude-dependence claim are not separable in this
    route set unless the groups overlap in amplitude. Measured here: stratify by amplitude and re-compare.
 B. COHERENCE GATING. With one periodogram per window, per-window coherence is identically 1, so a gate can only
    act at the RUN level. Measure what a run-level coh gate actually selects (does it prefer high-amplitude runs?)
    and how much it moves each group's |H|.
 C. EXPOSURE WEIGHTING / leave-one-route-out.
 D. SPLIT-HALF noise floor per group.
 E. IS THE INPUT CHANNEL CONTAMINATED BY THE OUTPUT? Lane centering adds a correction computed from the camera's
    view of the car's own position (bounded +/-0.0012 curvature = 0.75 m/s^2 at 25 m/s), so the logged demand
    can respond to the achieved motion. A feedforward-only chain has cross-covariance only at x LEADING y;
    contamination shows as anti-causal energy. Same statistic both groups.

usage: python a7_selection.py
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import load_route, my_runs, windows, band_stats, GROUP, FS

NPS = 4096
f = np.fft.rfftfreq(NPS, 1 / FS)
BANDS = [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]

runs_db = []     # one record per RUN: its windows, amplitude, coherence
wins_db = []     # one record per WINDOW
xcor = {}

for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    x_all, y_all = np.nan_to_num(S["x_model"]), np.nan_to_num(S["y_pose"])
    for a, b in my_runs(m, S["t"], 41.0):
        Ws = [dict(pxx=p1, pyy=p2, pxy=p3, s=s) for p1, p2, p3, s in windows(x_all[a:b], y_all[a:b], NPS, NPS // 2)]
        if not Ws:
            continue
        rec = dict(route=r, group=g, nwin=len(Ws), dur=(b - a) / FS,
                   v=float(np.median(S["v"][a:b])), ang=float(np.median(np.abs(S["sa"][a:b]))))
        for f1, f2 in BANDS:
            st = band_stats(Ws, f, f1, f2)
            rec[f"H{f1}"] = st["H_mag"]; rec[f"coh{f1}"] = st["coh"]; rec[f"in{f1}"] = st["in_rms"]
        rec["W"] = Ws
        runs_db.append(rec)
        for w in Ws:
            wr = dict(route=r, group=g, W=[w])
            for f1, f2 in BANDS:
                st = band_stats([w], f, f1, f2)
                wr[f"in{f1}"] = st["in_rms"]
            wins_db.append(wr)
    # E: anti-causal energy, 0.15-0.60 Hz band-passed, normalised cross-covariance
    sos = signal.butter(4, [0.15, 0.60], btype="band", fs=FS, output="sos")
    num = np.zeros(161); den = 0.0
    for a, b in my_runs(m, S["t"], 41.0):
        xb = signal.sosfiltfilt(sos, x_all[a:b]); yb = signal.sosfiltfilt(sos, y_all[a:b])
        nrm = np.sqrt(np.dot(xb, xb) * np.dot(yb, yb))
        for i, L in enumerate(range(-80, 81)):
            if L >= 0:
                c = np.dot(xb[:len(xb) - L], yb[L:])
            else:
                c = np.dot(xb[-L:], yb[:len(yb) + L])
            num[i] += c / max(nrm, 1e-12)
        den += 1
    if den:
        xcor[r] = (num / den, g)
    del S

print("=== A. amplitude stratification: pooled |H| per group in terciles of the WINDOW's in-band demand RMS ===")
for f1, f2 in BANDS:
    amps = sorted(w[f"in{f1}"] for w in wins_db)
    q1, q2 = np.percentile(amps, [33.3, 66.7])
    print(f"  band {f1}-{f2} Hz   global terciles at {q1:.4f} / {q2:.4f} m/s^2 in-band RMS")
    for g in GROUPS:
        line = f"    {g:8s}"
        for lab, lo, hi in (("low ", -1, q1), ("mid ", q1, q2), ("high", q2, 1e9)):
            Ws = [w["W"][0] for w in wins_db if w["group"] == g and lo <= w[f"in{f1}"] < hi]
            st = band_stats(Ws, f, f1, f2)
            line += f"  {lab} n{len(Ws):3d} " + (f"H {st['H_mag']:5.3f} coh {st['coh']:.2f}" if st else "H   --      ")
        print(line)
    print()

print("=== A2. the same gap inside the OVERLAP: windows whose demand RMS lies in the range both groups populate ===")
for f1, f2 in BANDS:
    va = [w[f"in{f1}"] for w in wins_db if w["group"] == "V282"]
    ta = [w[f"in{f1}"] for w in wins_db if w["group"] in ("T64",)]
    lo, hi = max(min(va), min(ta)), min(max(va), max(ta))
    out = {}
    for g in ("V282", "T64"):
        Ws = [w["W"][0] for w in wins_db if w["group"] == g and lo <= w[f"in{f1}"] <= hi]
        st = band_stats(Ws, f, f1, f2)
        out[g] = (st, len(Ws))
    a, b = out["V282"], out["T64"]
    print(f"  band {f1}-{f2}: overlap [{lo:.4f},{hi:.4f}]  V282 n{a[1]:3d} H {a[0]['H_mag']:.3f}  "
          f"T64 n{b[1]:3d} H {b[0]['H_mag']:.3f}   gap {b[0]['H_mag']-a[0]['H_mag']:+.3f}   "
          f"(all-window gap was computed in A2)")
    print(f"      V282 demand RMS median {np.median(va):.4f} (n{len(va)}), T64 {np.median(ta):.4f} (n{len(ta)})")

print("\n=== B. run-level coherence gate: what does it select, and what does it move? ===")
for f1, f2 in BANDS:
    rr = [r for r in runs_db if r["nwin"] >= 2]
    c = np.array([r[f"coh{f1}"] for r in rr]); am = np.array([r[f"in{f1}"] for r in rr])
    print(f"  band {f1}-{f2}: corr(run coherence, run demand RMS) = {np.corrcoef(c, np.log(am))[0,1]:+.3f} "
          f"over {len(rr)} runs with >=2 windows;  Spearman "
          f"{np.corrcoef(np.argsort(np.argsort(c)), np.argsort(np.argsort(am)))[0,1]:+.3f}")
    for g in GROUPS:
        allW = [w for r in runs_db if r["group"] == g for w in r["W"]]
        gateW = [w for r in runs_db if r["group"] == g and (r["nwin"] < 2 or r[f"coh{f1}"] >= 0.90) for w in r["W"]]
        s0 = band_stats(allW, f, f1, f2); s1 = band_stats(gateW, f, f1, f2)
        if s0 and s1:
            keptamp = np.median([r[f"in{f1}"] for r in runs_db if r["group"] == g
                                 and (r["nwin"] < 2 or r[f"coh{f1}"] >= 0.90)] or [np.nan])
            allamp = np.median([r[f"in{f1}"] for r in runs_db if r["group"] == g])
            print(f"    {g:8s} ungated n{len(allW):3d} H {s0['H_mag']:5.3f} | coh>=0.90 n{len(gateW):3d} "
                  f"H {s1['H_mag']:5.3f}  dH {s1['H_mag']-s0['H_mag']:+.3f}  "
                  f"median demand RMS {allamp:.4f} -> {keptamp:.4f}")
    print()

print("=== C. leave-one-route-out on each group's pooled |H| ===")
for f1, f2 in BANDS:
    for g in GROUPS:
        routes = sorted({r["route"] for r in runs_db if r["group"] == g})
        base = band_stats([w for r in runs_db if r["group"] == g for w in r["W"]], f, f1, f2)
        loo = []
        for drop in routes:
            Ws = [w for r in runs_db if r["group"] == g and r["route"] != drop for w in r["W"]]
            st = band_stats(Ws, f, f1, f2)
            loo.append(st["H_mag"] if st else np.nan)
        print(f"  {f1}-{f2} {g:8s} all {base['H_mag']:.3f}  LORO {[f'{x:.3f}' for x in loo]}  "
              f"spread {np.nanmax(loo)-np.nanmin(loo):.3f}")
    print()

print("=== D. split-half noise floor (alternate windows, per group) ===")
for f1, f2 in BANDS:
    for g in GROUPS:
        Ws = [w for r in runs_db if r["group"] == g for w in r["W"]]
        a = band_stats(Ws[0::2], f, f1, f2); b = band_stats(Ws[1::2], f, f1, f2)
        if a and b:
            print(f"  {f1}-{f2} {g:8s} halves {a['H_mag']:.3f} / {b['H_mag']:.3f}  |diff| {abs(a['H_mag']-b['H_mag']):.3f}")
    print()

print("=== E. anti-causal test: normalised cross-covariance of demand vs achieved, 0.15-0.60 Hz ===")
print("    (x LEADS y at positive lag; a feedforward-only chain has near-zero weight at negative lag)")
lags = np.arange(-80, 81) * 10
for g in GROUPS:
    rs = [r for r, (c, gg) in xcor.items() if gg == g]
    if not rs:
        continue
    C = np.mean([xcor[r][0] for r in rs], axis=0)
    neg = C[lags < 0].sum(); pos = C[lags > 0].sum()
    print(f"  {g:8s} peak at {lags[np.argmax(C)]:+5d} ms (r {C.max():+.3f})   "
          f"sum(lag<0)/sum(lag>0) = {neg/max(pos,1e-9):+.3f}   C(-500 ms) {C[lags==-500][0]:+.3f}  "
          f"C(+500 ms) {C[lags==+500][0]:+.3f}")
json.dump({r: list(map(float, c)) for r, (c, g) in xcor.items()}, open(HERE / "a7_xcorr.json", "w"))
