"""Orchestrator's own check of the synthesis' decision-bearing claims.

1. Texture separator: 1.8-3.5 Hz steering-rate RMS in matched speed x |angle| cells, 10 s blocks, route-cluster bootstrap.
2. Instrument facts: cs_yaw identically 0? la_pose sign vs la_act.
3. Highway band |H| model -> la_pose, V282 vs T64 vs T4 (observer OFF) vs T5 (observer ON): does the observer raise or lower
   in-band gain in closed loop?
4. Actuation+sensing delay: lag from the sent 0xE4 command to steering ACCELERATION (J*acc responds to torque with no plant
   phase), by cross-correlation of 1-6 Hz band-passed signals on the torque-mode routes.
"""
import sys, math
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v282cmp as V

GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
SPD = [(0, 8), (8, 15), (15, 22), (22, 40)]
ANG = [(0, 5), (5, 15), (15, 45), (45, 999)]
BLK = int(10 * V.FS)
sos_tex = signal.butter(4, [1.8, 3.5], btype="band", fs=V.FS, output="sos")
rng = np.random.default_rng(1)

blocks = []          # (group, route, sbin, abin, rms)
band = {}            # (group, route) -> list of (x, y) segments >15 m/s
fact = {}
delay = {}
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    g = meta["group"]
    u = V.usable(S)
    fact[rk] = (float(np.nanmax(np.abs(S["la_yaw"]))),
                float(np.corrcoef(np.nan_to_num(S["la_pose"][u]), np.nan_to_num(S["la_act"][u]))[0, 1]))
    for a, b in V.runs(u, S["t"], min_s=12.0):
        x = signal.sosfiltfilt(sos_tex, np.nan_to_num(S["sr"][a:b]))
        for k in range(a + 100, b - 100 - BLK, BLK):   # skip filter edges
            sl = slice(k, k + BLK)
            vv = float(np.median(S["v"][k:k + BLK])); aa = float(np.median(np.abs(S["sa"][k:k + BLK])))
            si = next((i for i, (lo, hi) in enumerate(SPD) if lo <= vv < hi), None)
            ai = next((i for i, (lo, hi) in enumerate(ANG) if lo <= aa < hi), None)
            if si is None or ai is None:
                continue
            blocks.append((g, rk, si, ai, float(np.sqrt(np.mean(x[k - a:k - a + BLK] ** 2)))))
    band[(g, rk)] = [(np.nan_to_num(S["model"][a:b]), np.nan_to_num(S["la_pose"][a:b]))
                     for a, b in V.runs(V.usable(S, 15.0), S["t"], min_s=41.0)]
    if meta["eps"] == "V293":
        # command in +left torque units: e4 ~ -4089*cs_out, and cs_out = -output_torque, so +e4 = +output_torque frame;
        # take sign empirically from the correlation with steering acceleration.
        acc = V.deriv(np.nan_to_num(S["sr"]))
        sos = signal.butter(4, [1.0, 6.0], btype="band", fs=V.FS, output="sos")
        num = {}; cnt = 0
        for a, b in V.runs(u & (S["v"] > 3.0), S["t"], min_s=30.0):
            c = signal.sosfiltfilt(sos, np.nan_to_num(S["e4"][a:b])); y = signal.sosfiltfilt(sos, acc[a:b])
            for L in range(-5, 26):
                ca, ya = (c[:len(c) - L], y[L:]) if L >= 0 else (c[-L:], y[:len(y) + L])
                num[L] = num.get(L, 0.0) + float(np.dot(ca, ya)) / math.sqrt(float(np.dot(ca, ca) * np.dot(ya, ya)) + 1e-12)
            cnt += 1
        if cnt:
            Ls = sorted(num); vals = np.array([num[L] / cnt for L in Ls])
            ib = int(np.argmax(np.abs(vals)))
            delay[rk] = (Ls[ib] * 10, float(vals[ib]), cnt)
    del S

print("1) cs_yaw max |.| and corr(la_pose, la_act) on usable frames")
for rk, (ymax, c) in fact.items():
    print(f"   {rk:24s} {V.ROUTES[rk]['group']:8s} max|la_yaw| {ymax:.3g}   corr(pose, act) {c:+.3f}")

print("\n2) 1.8-3.5 Hz steering-rate RMS (deg/s), median of 10 s blocks; ratio to V282 with route-cluster bootstrap 95% CI")
B = blocks
for si, (slo, shi) in enumerate(SPD):
    for ai, (alo, ahi) in enumerate(ANG):
        cell = [(g, r, x) for g, r, s, a, x in B if s == si and a == ai]
        ref = [x for g, r, x in cell if g == "V282"]
        if len(ref) < 6:
            continue
        line = f"   v {slo:>2}-{shi:<3} |ang| {alo:>2}-{ahi:<3}  V282 {np.median(ref):5.2f} (n{len(ref):4d})"
        for g in GROUPS[1:]:
            xs = [(r, x) for gg, r, x in cell if gg == g]
            if len(xs) < 6:
                line += f"  {g}: --     "
                continue
            rs = sorted(set(r for r, _ in xs)); rr = sorted(set(r for gg, r, _ in cell if gg == "V282"))
            boots = []
            for _ in range(400):
                pick = rng.choice(rs, len(rs)); pr = rng.choice(rr, len(rr))
                a1 = [x for r in pick for rr_, x in xs if rr_ == r]
                a0 = [x for r in pr for gg, rr_, x in cell if gg == "V282" and rr_ == r]
                if a1 and a0:
                    boots.append(np.median(a1) / max(np.median(a0), 1e-6))
            lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
            line += f"  {g}: x{np.median([x for _, x in xs]) / max(np.median(ref), 1e-6):4.1f}[{lo:4.1f},{hi:4.1f}](n{len(xs)})"
        print(line)

print("\n3) Highway (>=15 m/s, runs >=41 s) band |H| model -> la_pose, pooled per group (per-route in brackets)")
for f1, f2 in [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]:
    line = f"   {f1:.2f}-{f2:.2f} Hz"
    for g in GROUPS:
        segs = [s for (gg, r), ss in band.items() if gg == g for s in ss]
        res = V.band_H(segs, f1, f2)
        per = [V.band_H(ss, f1, f2) for (gg, r), ss in band.items() if gg == g]
        per = [p["H"] for p in per if p]
        line += f"  {g} {res['H']:.2f}/coh{res['coh']:.2f}[{','.join(f'{p:.2f}' for p in per)}]" if res else f"  {g} --"
    print(line)

print("\n4) Lag from sent 0xE4 command to steering acceleration (1-6 Hz), torque-mode routes (ms, peak normalised corr, runs)")
for rk, (ms, c, n) in delay.items():
    print(f"   {rk:24s} {V.ROUTES[rk]['group']:5s} lag {ms:4d} ms   corr {c:+.3f}   runs {n}")
