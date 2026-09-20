# -*- coding: utf-8 -*-
"""REGIME B stage 8: the three checks that could still break the naming.

  C1  TRANSMISSION, done properly.  b4's wheel->yaw transfer was estimated on each build's own windows;
      V282's estimate is biased UP above ~1.5 Hz because its wheel barely moves there, so |P_AY|/P_AA is
      dominated by the yaw channel's own noise.  Redo with a COHERENCE-GATED transfer and with the
      torque-side transfer, and check both against the kinematic v^2/(SR*L) scale.
  C2  IS THE DEMAND ITSELF MORE INTERMITTENT on the torque routes?  Kurtosis of the band-passed demand,
      matched -- the null control for the kurtosis finding.  If the demand's own kurtosis matches, the
      wheel's does not come from the road/route selection.
  C3  IS THE STEERING-RATE RESIDUAL WHITE on torque mode and low-passed on V282?  Print the residual
      steering-rate PSD flatness (geometric/arithmetic mean over 0.45-3.3 Hz) with route-cluster CIs.

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python b8_checks.py > B8-OUT.txt
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

D = np.load(HERE / "b1_spec.npz", allow_pickle=True)
W = float(D["W"][0]); FR = np.arange(D["X"].shape[1]) / W
NRM1 = 16.0 / (3.0 * (W * 100.0) ** 2)
SPDN = ["0-8", "8-15", "15-22", "22+"]
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
GRP = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
       "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4", "00000074--2bf17ca67d": "T4",
       "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
       "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2"}
DSEL = {1: (0.004, 0.018), 2: (0.004, 0.026), 3: (0.008, 0.040)}
FB = [(0.30, 0.45), (0.45, 0.60), (0.60, 0.80), (0.80, 1.00), (1.00, 1.20), (1.20, 1.50), (1.80, 2.20)]
rng = np.random.default_rng(83)


def brms(C, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(C[:, s]) ** 2).sum(1) * NRM1)


def sel(i, mem):
    dlo, dhi = DSEL[i]; d = brms(D["X"], 0.6, 1.2)
    return np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], mem) &
                          (d >= dlo) & (d < dhi))


def inc(idx, ch):
    A = D["X"][idx]; B = D[ch][idx]
    Pxx = (np.abs(A) ** 2).sum(0); Pbb = (np.abs(B) ** 2).sum(0); Pxb = (np.conj(A) * B).sum(0)
    return np.maximum(Pbb - np.abs(Pxb) ** 2 / np.maximum(Pxx, 1e-300), 0) / len(idx) * NRM1


def c1():
    print("=" * 140)
    print("C1. WHEEL -> YAW TRANSMISSION.  G = |P_AY|/P_AA per bin; 'gated' keeps only bins whose A-Y")
    print("    coherence^2 exceeds 0.3 and weights by P_AA.  kinematic = v^2 * (pi/180) / (SteerRatio *")
    print("    wheelbase 2.83 m) at the cell's median speed and its own flown SteerRatio -- printed as a")
    print("    sanity scale, not used in the prediction.")
    print("=" * 140)
    for i in (1, 2, 3):
        ka, kb = sel(i, ["V282"]), sel(i, TORQ)
        vm = float(np.median(D["v"][kb]))
        kin = vm ** 2 * (np.pi / 180.0) / (16.5 * 2.83)
        print(f"\n  speed {SPDN[i]} (median v {vm:.1f} m/s; kinematic wheel->lat-accel {kin:.4f} (m/s^2)/deg)")
        print(f"   {'band Hz':>11s} {'G V282':>8s} {'coh2':>5s} {'G TORQ':>8s} {'coh2':>5s} "
              f"{'A excess':>9s} {'Y pred (V)':>11s} {'Y pred (T)':>11s} {'Y measured':>11s} {'meas/pred(T)':>13s}")
        for f1, f2 in FB:
            s = (FR >= f1) & (FR < f2)
            g = {}
            for nm, k in (("V", ka), ("T", kb)):
                A = D["A"][k][:, s]; Y = D["Y"][k][:, s]
                Paa = (np.abs(A) ** 2).sum(0); Pyy = (np.abs(Y) ** 2).sum(0); Pay = (np.conj(A) * Y).sum(0)
                c2 = np.abs(Pay) ** 2 / np.maximum(Paa * Pyy, 1e-300)
                g[nm] = (float(np.average(np.abs(Pay) / np.maximum(Paa, 1e-300), weights=Paa)),
                         float(np.average(c2, weights=Paa)))
            ia, ib = inc(ka, "A"), inc(kb, "A"); ya, yb = inc(ka, "Y"), inc(kb, "Y")
            dA = max(ib[s].sum() - ia[s].sum(), 0) ** .5
            dY = max(yb[s].sum() - ya[s].sum(), 0) ** .5
            pv, pt = g["V"][0] * dA, g["T"][0] * dA
            print(f"   {f1:.2f}-{f2:.2f}   {g['V'][0]:8.4f} {g['V'][1]:5.2f} {g['T'][0]:8.4f} {g['T'][1]:5.2f} "
                  f"{dA:9.4f} {pv:11.4f} {pt:11.4f} {dY:11.4f} {dY/max(pt,1e-9):13.2f}")


def bp(x, f1, f2):
    return sg.sosfiltfilt(sg.butter(3, [f1, f2], btype="band", fs=100.0, output="sos"), x)


def c2():
    print("\n" + "=" * 140)
    print("C2. NULL CONTROL: kurtosis of the band-passed DEMAND itself (0.3-4 Hz), same blocks, same")
    print("    matching.  If the torque routes' demand were itself more intermittent, the wheel's")
    print("    kurtosis 8 vs 4 would be route selection rather than the build.")
    print("=" * 140)
    rows = {}
    for rk, grp in GRP.items():
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            continue
        S = V.load(rk)
        ok = np.isfinite(S["sr"]) & np.isfinite(S["model"]) & np.isfinite(S["v"])
        m = S["active"] & ~S["pressed"] & ok
        n = 1024
        for a, b in V.runs(m, S["t"], min_s=12.0):
            xb3 = bp(np.nan_to_num(S["model"][a:b]), 0.3, 4.0)
            xb = bp(np.nan_to_num(S["model"][a:b]), 0.6, 1.2)
            rb = bp(np.nan_to_num(S["sr"][a:b]), 0.3, 4.0)
            ed = 200
            for k in range(a + ed, b - ed - n + 1, n // 2):
                sl = slice(k, k + n); rel = slice(k - a, k - a + n)
                vv = S["v"][sl]; vm = float(np.median(vv))
                i = next((q for q, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
                if i in (None, 0) or float(np.mean((vv >= SPD[i][0]) & (vv < SPD[i][1]))) < 0.8:
                    continue
                dlo, dhi = DSEL[i]
                dr = float(np.sqrt(np.mean(xb[rel] ** 2)))
                if not (dlo <= dr < dhi):
                    continue
                zx = xb3[rel] - xb3[rel].mean(); zr = rb[rel] - rb[rel].mean()
                if zx.std() < 1e-12 or zr.std() < 1e-12:
                    continue
                rows.setdefault((grp, i), []).append(
                    (rk, float((zx ** 4).mean() / zx.std() ** 4), float((zr ** 4).mean() / zr.std() ** 4),
                     float(np.percentile(np.abs(zr), 99.9) / zr.std())))
        del S
    print(f"\n   {'speed':7s} {'group':8s} {'nblk':>5s} {'kurt DEMAND':>12s} {'[95% CI]':>15s} "
          f"{'kurt RATE':>10s} {'[95% CI]':>15s}")
    for i in (1, 2, 3):
        for gname, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            acc = [r for g2 in mem for r in rows.get((g2, i), [])]
            if len(acc) < 8:
                continue
            rk_ = np.array([r[0] for r in acc]); kx = np.array([r[1] for r in acc]); kr = np.array([r[2] for r in acc])
            rts = sorted(set(rk_)); per = {r: np.flatnonzero(rk_ == r) for r in rts}
            bx, br = [], []
            for _ in range(400):
                kk = np.concatenate([per[r] for r in rng.choice(rts, len(rts))]) if len(rts) >= 2 else np.arange(len(acc))
                bx.append(np.median(kx[kk])); br.append(np.median(kr[kk]))
            cx = np.percentile(bx, [2.5, 97.5]); cr = np.percentile(br, [2.5, 97.5])
            print(f"   {SPDN[i]:7s} {gname:8s} {len(acc):5d} {np.median(kx):12.2f} [{cx[0]:6.2f},{cx[1]:6.2f}] "
                  f"{np.median(kr):10.2f} [{cr[0]:6.2f},{cr[1]:6.2f}]")


def c3():
    print("\n" + "=" * 140)
    print("C3. IS THE STEERING-RATE RESIDUAL WHITE?  Per-bin PSD of the demand-incoherent steering rate")
    print("    over 0.45-3.3 Hz, and its flatness = geometric mean / arithmetic mean (1.00 = white).")
    print("    Also the ratio PSD(0.45-0.6 Hz)/PSD(2.7-3.3 Hz): 1 for white, >>1 for a low-passed residual.")
    print("=" * 140)
    print(f"   {'speed':7s} {'group':8s} {'n':>4s} {'flatness':>9s} {'PSD .5Hz/PSD 3Hz':>18s} "
          f"{'angle-PSD log-log slope':>24s}")
    for i in (1, 2, 3):
        for gname, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            k = sel(i, mem)
            if len(k) < 6:
                continue
            m = (FR >= 0.45) & (FR <= 3.30)
            pr = inc(k, "R")[m] / (FR[1] - FR[0])
            flat = float(np.exp(np.mean(np.log(np.maximum(pr, 1e-30)))) / np.mean(pr))
            lo = inc(k, "R")[(FR >= 0.45) & (FR < 0.60)].mean()
            hi = inc(k, "R")[(FR >= 2.70) & (FR < 3.30)].mean()
            ma = (FR >= 0.39) & (FR <= 4.0)
            pa = inc(k, "A")[ma]
            sl = np.polyfit(np.log(FR[ma]), np.log(np.maximum(pa, 1e-30)), 1)[0]
            print(f"   {SPDN[i]:7s} {gname:8s} {len(k):4d} {flat:9.2f} {lo/max(hi,1e-30):18.2f} {sl:24.2f}")


if __name__ == "__main__":
    c1(); c2(); c3()
