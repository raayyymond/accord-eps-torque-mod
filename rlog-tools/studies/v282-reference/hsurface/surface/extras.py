# -*- coding: utf-8 -*-
"""Stage 3: the three things the surface table cannot say by itself.

A. WHERE THE DEMAND ACTUALLY LIVES. The in-band RMS of the model's desired lateral accel, per speed bin,
   per band, both builds. A band the plan never asks for cannot be a tracking failure, and |H| there is
   not a tracking measurement -- it is the planner echoing the car (desiredCurvature is computed from the
   measured state). Shown with the DIRECTION test that proves it: the sign of the cross-correlation lag.

B. AMPLITUDE DEPENDENCE, two ways. (1) the surface's own A1/A2/A3 strata (p95 |model| operating point),
   trended per band; (2) terciles of the window's IN-BAND demand RMS -- the describing-function amplitude
   -- with the cut values shared between builds. A saturating actuator must show |H| falling with
   amplitude; this is the direct test of that mechanism.

C. THE SHAKE BAND, DONE CORRECTLY. Above ~1 Hz the demand carries almost nothing, so the honest statistic
   is the OUTPUT power ratio at matched speed and amplitude, not |H|.

ANALYSIS ONLY, read-only.  usage: python extras.py > EXTRAS-OUT.txt
"""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

SPDN = ["0-8", "8-15", "15-22", "22+"]
ACUT = [(0.0, 0.3), (0.3, 1.0), (1.0, 99.0)]
ACUTN = ["A1 <0.3", "A2 .3-1", "A3 >=1"]
BANDS = [(0.06, 0.15, 40.96), (0.15, 0.30, 20.48), (0.30, 0.60, 10.24),
         (0.60, 1.20, 10.24), (1.20, 2.40, 5.12), (2.40, 4.00, 5.12)]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
GR = {"V282": ["V282"], "V282old": ["V282old"], "TORQ": TORQ, "T64F": ["T64", "T64B"]}


def rmsscale(W, n):
    """Hann one-sided band-RMS scale: rms^2 = sum|X|^2 * 16/(3 N^2 nwin). Verified on a known sine to 0.06%."""
    return 16.0 / (3.0 * (W * 100.0) ** 2 * n)


print("=" * 150)
print("A. WHERE THE DEMAND LIVES: in-band RMS of the MODEL's desired lateral accel (m/s^2), and of the achieved")
print("   Also |H| and the implied lag. A band where in-RMS is a thousandth of a m/s^2 is asking for nothing.")
print("=" * 150)
print(f"{'band Hz':10s} {'speed':6s} {'group':8s} {'n':>4s} {'inRMS':>8s} {'ouRMS':>8s} {'ou/in':>6s} {'|H|':>6s} "
      f"{'coh':>5s} {'lag_ms':>7s} {'gd_ms':>7s}")
for f1, f2, W in BANDS:
    D = np.load(HERE / f"spec_{W:.2f}.npz", allow_pickle=True)
    fr = np.arange(D["X"].shape[1]) / W
    sel = (fr >= f1) & (fr < f2)
    fb = fr[sel]
    Xb, Yb = D["X"][:, sel], D["Y"][:, sel]
    g_, sb_ = D["group"], D["sbin"]
    for i in range(4):
        for gn, mem in GR.items():
            idx = np.flatnonzero((sb_ == i) & np.isin(g_, mem))
            if len(idx) < 6:
                continue
            Pxx = (np.abs(Xb[idx]) ** 2).sum(0); Pyy = (np.abs(Yb[idx]) ** 2).sum(0)
            Pxy = (np.conj(Xb[idx]) * Yb[idx]).sum(0)
            sc = rmsscale(W, len(idx))
            Hb = Pxy / np.maximum(Pxx, 1e-300)
            H = float(np.average(np.abs(Hb), weights=Pxx))
            coh = float(np.average(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-300), weights=Pxx))
            fc = float(np.average(fb, weights=Pxx)); phc = float(np.angle((Pxy * Pxx).sum()))
            gd = float("nan")
            if len(fb) >= 4:
                ww = Pxx
                sol = np.linalg.lstsq(np.vstack([2 * np.pi * fb, np.ones_like(fb)]).T * ww[:, None] ** .5,
                                      np.unwrap(np.angle(Hb)) * ww ** .5, rcond=None)[0]
                gd = -sol[0] * 1000
            ir = math.sqrt(Pxx.sum() * sc); orm = math.sqrt(Pyy.sum() * sc)
            print(f"{f1:.2f}-{f2:.2f}  {SPDN[i]:6s} {gn:8s} {len(idx):4d} {ir:8.5f} {orm:8.5f} "
                  f"{orm/max(ir,1e-12):6.2f} {H:6.3f} {coh:5.2f} {-math.degrees(phc)/360/max(fc,1e-9)*1000:7.0f} {gd:7.0f}")
    del D
    print("")

print("=" * 150)
print("A2. DIRECTION TEST on the raw time series: cross-correlation of band-passed model demand against")
print("    achieved lateral accel, per band, pooled over the torque routes and over V282. A POSITIVE peak lag")
print("    means the car follows the plan; a NEGATIVE peak means the plan follows the car (planner echo).")
print("=" * 150)
BP = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40), (2.40, 4.00)]
acc = {(g, b): np.zeros(161) for g in ("V282", "TORQ") for b in range(len(BP))}
cnt = {(g, b): 0 for g in ("V282", "TORQ") for b in range(len(BP))}
routes = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
          "TORQ": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                   "00000076--d0b7ea7e4d", "00000075--6c8687d5bd", "00000072--8001fc3048",
                   "00000073--79fd149dd8", "00000070--717f5a7866", "00000071--f2c9d073a3"]}
for gn, rl in routes.items():
    for rk in rl:
        S = V.load(rk)
        u = V.usable(S) & np.isfinite(S["model"]) & np.isfinite(S["la_pose"])
        for b, (f1, f2) in enumerate(BP):
            sos = signal.butter(4, [f1, f2], btype="band", fs=V.FS, output="sos")
            for a, bb in V.runs(u, S["t"], min_s=20.0):
                x = signal.sosfiltfilt(sos, np.nan_to_num(S["model"][a:bb]))
                y = signal.sosfiltfilt(sos, np.nan_to_num(S["la_pose"][a:bb]))
                x = x[100:-100]; y = y[100:-100]
                if len(x) < 400:
                    continue
                nx = math.sqrt(float(np.dot(x, x) * np.dot(y, y))) + 1e-30
                for L in range(-80, 81):
                    xa, ya = (x[:len(x) - L], y[L:]) if L >= 0 else (x[-L:], y[:len(y) + L])
                    acc[(gn, b)][L + 80] += float(np.dot(xa, ya)) / nx
                cnt[(gn, b)] += 1
        del S
for b, (f1, f2) in enumerate(BP):
    for gn in ("V282", "TORQ"):
        if not cnt[(gn, b)]:
            continue
        c = acc[(gn, b)] / cnt[(gn, b)]
        k = int(np.argmax(c))
        print(f"   {f1:.2f}-{f2:.2f} Hz  {gn:6s} runs {cnt[(gn,b)]:4d}  peak corr {c[k]:+.3f} at lag "
              f"{(k-80)*10:+5d} ms   corr at 0 ms {c[80]:+.3f}   "
              f"{'car follows plan' if k>80 else 'PLAN FOLLOWS CAR (planner echo)'}")

print("\n" + "=" * 150)
print("B1. AMPLITUDE TREND across the surface's own strata (p95 |model| operating point). |H| (n windows).")
print("=" * 150)
S = json.load(open(HERE / "surface.json"))
for f1, f2, W in BANDS:
    tag = f"{f1:.2f}-{f2:.2f}Hz@{W:.2f}s"
    for i in range(4):
        line = f"   {f1:.2f}-{f2:.2f} {SPDN[i]:6s}"
        any_ = False
        for gn in ("V282", "TORQ"):
            line += f"   {gn:5s}"
            for j in range(3):
                c = S.get(f"{tag}|{SPDN[i]}|{ACUTN[j]}|{gn}")
                if c and c["nwin"] >= 6:
                    line += f" {ACUTN[j][:2]}:{c['H']:5.2f}(n{c['nwin']:3d})"; any_ = True
                else:
                    line += f" {ACUTN[j][:2]}:  --        "
        if any_:
            print(line)
    print("")

print("=" * 150)
print("B2. AMPLITUDE TREND on the DESCRIBING-FUNCTION amplitude: terciles of each window's IN-BAND demand RMS,")
print("    cut values computed on the POOLED window set so both builds face identical cuts. A saturating")
print("    actuator must show |H| FALLING from T1 to T3.")
print("=" * 150)
for f1, f2, W in BANDS:
    D = np.load(HERE / f"spec_{W:.2f}.npz", allow_pickle=True)
    fr = np.arange(D["X"].shape[1]) / W
    sel = (fr >= f1) & (fr < f2)
    fb = fr[sel]
    Xb, Yb = D["X"][:, sel], D["Y"][:, sel]
    g_, sb_, rail_ = D["group"], D["sbin"], D["rail"]
    amp = np.sqrt((np.abs(Xb) ** 2).sum(1) * rmsscale(W, 1))
    for i in range(4):
        pool = np.flatnonzero((sb_ == i) & np.isin(g_, ["V282"] + TORQ))
        if len(pool) < 18:
            continue
        cuts = np.percentile(amp[pool], [33.3, 66.7])
        line = f"   {f1:.2f}-{f2:.2f} {SPDN[i]:6s} cuts {cuts[0]:.4f}/{cuts[1]:.4f} m/s^2 "
        for gn, mem in (("V282", ["V282"]), ("TORQ", TORQ)):
            line += f"  {gn:5s}"
            for t in range(3):
                lo = -1e9 if t == 0 else cuts[t - 1]
                hi = 1e9 if t == 2 else cuts[t]
                idx = np.flatnonzero((sb_ == i) & np.isin(g_, mem) & (amp > lo) & (amp <= hi))
                if len(idx) < 6:
                    line += f" T{t+1}:  --       "
                    continue
                Pxx = (np.abs(Xb[idx]) ** 2).sum(0); Pyy = (np.abs(Yb[idx]) ** 2).sum(0)
                Pxy = (np.conj(Xb[idx]) * Yb[idx]).sum(0)
                H = float(np.average(np.abs(Pxy) / np.maximum(Pxx, 1e-300), weights=Pxx))
                co = float(np.average(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-300), weights=Pxx))
                line += f" T{t+1}:{H:5.2f}/c{co:.2f}(n{len(idx):3d},rail{rail_[idx].mean():.3f})"
        print(line)
    del D
    print("")

print("=" * 150)
print("C. THE 1.2-4 Hz BANDS DONE AS AN OUTPUT-POWER RATIO (the demand asks for ~nothing there, so |H| is not")
print("   a tracking number). Achieved-lateral-accel in-band RMS, matched speed x amplitude stratum.")
print("=" * 150)
for f1, f2, W in [(1.20, 2.40, 5.12), (2.40, 4.00, 5.12)]:
    D = np.load(HERE / f"spec_{W:.2f}.npz", allow_pickle=True)
    fr = np.arange(D["X"].shape[1]) / W
    sel = (fr >= f1) & (fr < f2)
    Yb = D["Y"][:, sel]
    g_, sb_, ap_ = D["group"], D["sbin"], D["am_p95"]
    for i in range(4):
        for j, (alo, ahi) in enumerate(ACUT):
            vals = {}
            for gn, mem in GR.items():
                idx = np.flatnonzero((sb_ == i) & (ap_ >= alo) & (ap_ < ahi) & np.isin(g_, mem))
                if len(idx) >= 6:
                    vals[gn] = (math.sqrt((np.abs(Yb[idx]) ** 2).sum() * rmsscale(W, len(idx))), len(idx))
            if "V282" in vals and len(vals) > 1:
                ref = vals["V282"][0]
                print(f"   {f1:.2f}-{f2:.2f} {SPDN[i]:6s} {ACUTN[j]:8s} V282 {ref:.5f} m/s^2 (n{vals['V282'][1]:3d})  " +
                      "  ".join(f"{g} x{v[0]/ref:4.2f}(n{v[1]:3d})" for g, v in vals.items() if g != "V282"))
    del D
    print("")
