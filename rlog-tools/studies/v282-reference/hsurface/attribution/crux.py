"""CRUX CHECKS I had to do myself before relaying anything, plus the two numbers the attribution turns on.

1  RAIL DUTY, second method (controlsState saturated flag) against my |output| >= 0.995 method, and the
   same measurement on the V282 REFERENCE -- which nobody had run.
2  IS THE SHAKE VISIBLE IN THE GOAL METRIC AT ALL?  1.8-3.5 Hz RMS of steering RATE vs of the achieved
   lateral accel, same frames.  If the ratio moves between builds, the goal metric is blind to the shake.
3  WORST REGIME, two ways: farthest from the V282 REFERENCE, and farthest from |H| = 1.
4  Low-speed instrument-A census: can the torque side be measured at 0.1-0.5 Hz below 8 m/s at all?
"""
import sys, json, math
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import SPD, OUT

sos = signal.butter(4, [1.8, 3.5], btype="band", fs=V.FS, output="sos")


def main():
    print("=" * 128)
    print("1  RAIL DUTY -- two methods, and the V282 reference measured the same way")
    print("   m1 = |controlsState.lateralControlState.output| >= 0.995 ;  m2 = the logged 'saturated' flag")
    print("=" * 128)
    print(f"{'route':24s} {'grp':8s} {'v':7s} {'sec':>7s} {'m1 s':>7s} {'m1 %':>7s} {'m2 s':>7s} {'m2 %':>7s}")
    shake = []
    tot = {}
    for rk in V.ROUTES:
        S = V.load(rk)
        g = S["meta"].get("group", "?")
        out = np.nan_to_num(S["out"]); sat = S["sat"]; u = V.usable(S)
        for lo, hi in SPD:
            m = u & (S["v"] >= lo) & (S["v"] < hi)
            if m.sum() < 200:
                continue
            r1 = (m & (np.abs(out) >= 0.995)).sum() / V.FS
            r2 = (m & sat).sum() / V.FS
            print(f"{rk:24s} {g:8s} {lo}-{hi:<4d} {m.sum()/V.FS:7.1f} {r1:7.2f} {100*r1*V.FS/m.sum():7.4f} "
                  f"{r2:7.2f} {100*r2*V.FS/m.sum():7.4f}")
            k = (g, lo)
            a = tot.get(k, np.zeros(3)); tot[k] = a + np.array([m.sum() / V.FS, r1, r2])
        # 2: shake in steering rate vs in the achieved lateral accel, same frames
        sr = signal.sosfiltfilt(sos, np.nan_to_num(S["sr"]))
        la = signal.sosfiltfilt(sos, np.nan_to_num(S["la_pose"]))
        for lo, hi in SPD:
            m = V.usable(S, lo, hi)
            if m.sum() < 2000:
                continue
            shake.append((g, rk, lo, float(np.sqrt(np.mean(sr[m] ** 2))), float(np.sqrt(np.mean(la[m] ** 2))),
                          m.sum() / V.FS))
        del S
    print("\n   pooled:  group x speed -> sec / m1 s / m1 %% / m2 s / m2 %%")
    for (g, lo), a in sorted(tot.items()):
        print(f"   {g:8s} v>={lo:<3d} {a[0]:8.1f} s   m1 {a[1]:7.2f} s {100*a[1]/a[0]:7.4f} %   "
              f"m2 {a[2]:7.2f} s {100*a[2]/a[0]:7.4f} %")

    print("\n" + "=" * 128)
    print("2  DOES THE GOAL METRIC SEE THE SHAKE?  1.8-3.5 Hz RMS, same frames, per group x speed.")
    print("   steering rate in deg/s;  achieved lateral accel in m/s^2;  ratio la/sr in (m/s^2)/(deg/s).")
    print("=" * 128)
    print(f"{'v':7s} {'grp':8s} {'sec':>7s} {'sr RMS':>8s} {'xV282':>6s} {'laPose RMS':>11s} {'xV282':>6s} {'la/sr':>9s}")
    for lo, hi in SPD:
        base = None
        for g in ["V282", "V282old", "T64", "T64B", "T5", "T4"]:
            sel = [s for s in shake if s[0] == g and s[2] == lo]
            if not sel:
                continue
            w = np.array([s[5] for s in sel]); sr = np.array([s[3] for s in sel]); la = np.array([s[4] for s in sel])
            srm = float(np.sqrt(np.average(sr ** 2, weights=w))); lam = float(np.sqrt(np.average(la ** 2, weights=w)))
            if g == "V282":
                base = (srm, lam)
            print(f"{lo}-{hi:<4d} {g:8s} {w.sum():7.0f} {srm:8.3f} {srm/base[0]:6.2f} {lam:11.5f} "
                  f"{lam/base[1]:6.2f} {lam/max(srm,1e-9):9.5f}")

    print("\n" + "=" * 128)
    print("3  WORST REGIME.  From out/pooled.json, ADMISSIBLE matched cells only (coh>=0.55, n>=8 both sides).")
    print("   'vs ref' = H_T/H_V282 (how far from what the operator calls good).")
    print("   'vs 1'   = |H_T-1| - |H_V282-1| (how much worse at matching the model than V282 is).")
    print("=" * 128)
    P = json.load(open(OUT / "pooled.json"))
    rows = []
    for k, cr in P.items():
        bn, si, ai = k.split("|"); si = int(si); ai = int(ai)
        r0 = cr.get("V282")
        if not r0 or not r0["adm"]:
            continue
        for g in ("TON", "TOFF"):
            r = cr.get(g)
            if not r or not r["adm"]:
                continue
            rows.append(dict(band=bn, v=f"{SPD[si][0]}-{SPD[si][1]}", ai=ai, amp=r0["amp"], g=g,
                             H0=r0["H"], H1=r["H"], ratio=r["H"] / r0["H"],
                             worse=abs(r["H"] - 1) - abs(r0["H"] - 1),
                             dlag=r["lag"] - r0["lag"], disj=bool(r["lo"] > r0["hi"] or r["hi"] < r0["lo"]),
                             n0=r0["n"], n1=r["n"], rail=r["rail"]))
    rows.sort(key=lambda r: -abs(math.log(r["ratio"])))
    print(f"{'band':11s} {'v':7s} {'ai':2s} {'A med':>7s} {'grp':5s} {'V282':>6s} {'torque':>7s} "
          f"{'vs ref':>7s} {'vs 1':>7s} {'d lag s':>8s} {'n0/n1':>8s} {'CIs disjoint':>13s}")
    for r in rows:
        print(f"{r['band']:11s} {r['v']:7s} {r['ai']:<2d} {r['amp']:7.4f} {r['g']:5s} {r['H0']:6.2f} "
              f"{r['H1']:7.2f} {r['ratio']:7.2f} {r['worse']:+7.2f} {r['dlag']:+8.2f} "
              f"{r['n0']:3d}/{r['n1']:<4d} {'YES' if r['disj'] else 'no':>13s}")
    if rows:
        rr = [r for r in rows if r["disj"]]
        print(f"\n   worst by 'vs ref' overall: {rows[0]['band']} Hz, {rows[0]['v']} m/s, A {rows[0]['amp']:.4f}: "
              f"{rows[0]['H0']:.2f} -> {rows[0]['H1']:.2f}  (x{rows[0]['ratio']:.2f})")
        if rr:
            print(f"   worst with DISJOINT CIs:   {rr[0]['band']} Hz, {rr[0]['v']} m/s, A {rr[0]['amp']:.4f}: "
                  f"{rr[0]['H0']:.2f} -> {rr[0]['H1']:.2f}  (x{rr[0]['ratio']:.2f})")
        w = max(rows, key=lambda r: r["worse"])
        print(f"   worst by 'vs 1' (worse at matching the MODEL than V282): {w['band']} Hz, {w['v']} m/s: "
              f"|{w['H1']:.2f}-1| - |{w['H0']:.2f}-1| = {w['worse']:+.2f}")
    json.dump(rows, open(OUT / "worst.json", "w"), indent=1)

    print("\n" + "=" * 128)
    print("4  CENSUS of the 20.48 s blocks (the only instrument that reaches 0.1 Hz), per route x speed.")
    print("   A regime with no blocks cannot be measured at 0.10-0.50 Hz on this route set, at any effort.")
    print("=" * 128)
    B = {}
    for rk in V.ROUTES:
        p = OUT / f"blocks_{rk}.npz"
        if not p.exists():
            continue
        d = np.load(p, allow_pickle=True)
        vv = d["A_v"]
        B[rk] = (str(d["group"][0]), [int(((vv >= lo) & (vv < hi)).sum()) for lo, hi in SPD])
    print(f"{'route':24s} {'grp':8s} " + "".join(f"{f'{lo}-{hi}':>9s}" for lo, hi in SPD))
    for rk, (g, c) in B.items():
        print(f"{rk:24s} {g:8s} " + "".join(f"{x:9d}" for x in c))
    print(f"{'POOLED torque (5 routes)':33s} " + "".join(
        f"{sum(c[i] for g, c in B.values() if g in ('T64','T64B','T5','T4')):9d}" for i in range(len(SPD))))
    print(f"{'POOLED V282 (3 routes)':33s} " + "".join(
        f"{sum(c[i] for g, c in B.values() if g == 'V282'):9d}" for i in range(len(SPD))))


if __name__ == "__main__":
    main()
