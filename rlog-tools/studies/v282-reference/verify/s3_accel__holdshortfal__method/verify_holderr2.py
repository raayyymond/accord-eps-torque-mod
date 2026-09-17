"""Independent re-derivation, v2: fixes v1's over-strict hold-window-purity bug (rejecting any event with
even one pressed frame inside the hold window, which silently dropped most large-P V282 events -- V282's
median press_hold fraction is 0.28, so a full-purity gate is not a fair, independent replication of s3turns'
actual policy of NaN'ing individual pressed samples and gating engagement on ACTIVE only). This version:
require ACTIVE throughout hold (matches s3turns), tolerate PRESSED frames by NaN'ing them out of the mean
(matches s3turns), still uses its own distinct peak/hold parameters + interp-based lag shift.
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__holdshortfal__method/'

M = 3279 * 0.45359237 + 136.0; WB = 2.83; AF = 0.39 * WB; AR = WB - AF; TSF = 0.8467
M0, WB0 = 1326. + 136., 2.70; AF0 = WB0 * 0.4; AR0 = WB0 - AF0
CF = 192150 * TSF * M / M0 * (AR / WB) / (AR0 / WB0)
CR = 202500 * TSF * M / M0 * (AF / WB) / (AF0 / WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR = 16.33


def curv_to_angle(k, v):
    return -np.degrees(k * SR * WB * (1.0 - SF * v ** 2))


def lag_shift(x, t, lag_s):
    return np.interp(t + lag_s, t, x, left=np.nan, right=np.nan)


LAG = 0.25
rows = []
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    t = S["t"]; v = np.nan_to_num(S["v"]); vv = np.maximum(v, 0.5)
    active = S["active"]; pressed = S["pressed"]
    k_m = np.nan_to_num(S["model"]) / vv ** 2
    ad = curv_to_angle(k_m, v)
    aa = np.nan_to_num(S["sa"]) - np.nan_to_num(S["aoff"])
    k_p = np.nan_to_num(S["la_pose"]) / vv ** 2
    ap = curv_to_angle(k_p, v)
    ap = np.where(v >= 2.5, ap, np.nan)

    adl = V.lowpass(ad, 1.0)
    a = np.abs(adl)
    pk, props = signal.find_peaks(a, height=25.0, prominence=8.0, distance=int(2.5 * V.FS))
    n = len(t)
    kept = 0
    for kk in pk:
        P = a[kk]; s = float(np.sign(adl[kk]))
        if not (2.5 <= v[kk] < 15.0):
            continue
        thr = 0.85 * P
        i = kk
        while i > 0 and s * adl[i] >= thr:
            i -= 1
        j = kk
        while j < n - 1 and s * adl[j] >= thr:
            j += 1
        i += 1
        if j - i < 30 or i < 0 or j >= n:
            continue
        if not active[i:j].all():          # engagement required throughout (matches s3turns)
            continue
        if np.any(np.diff(t[i:j]) > 4.0 / V.FS):
            continue
        press_frac = float(pressed[i:j].mean())
        vm = float(np.median(v[i:j]))
        kept += 1
        for key, arr in (("aa", aa), ("ap", ap)):
            src = np.where(pressed, np.nan, arr)   # NaN pressed samples, don't reject the event (matches s3turns)
            ach = s * lag_shift(src, t, LAG)
            err = (ach - s * ad)[i:j] / P
            nvalid = int(np.isfinite(err).sum())
            if nvalid < 5:
                continue
            rows.append(dict(rk=rk, group=meta["group"], key=key, v=vm, P=float(P), press_frac=press_frac,
                              err=float(np.nanmean(err)), n_frames=nvalid))
    print(rk, meta["group"], "peaks", len(pk), "kept-events", kept, flush=True)
    del S

json.dump(rows, open(OUT + "verify_rows2.json", "w"), indent=1)

GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
rng = np.random.default_rng(99)


def pb(P):
    return 0 if P < 60 else (1 if P < 150 else 2)


for r in rows:
    r["pb"] = pb(r["P"]); r["G"] = GM[r["group"]]


def cl_boot(sub, NB=3000):
    x = np.array([r["err"] for r in sub], float)
    routes = sorted(set(r["rk"] for r in sub))
    byr = {q: np.array([r["err"] for r in sub if r["rk"] == q], float) for q in routes}
    bs = []
    for _ in range(NB):
        pick = rng.choice(routes, len(routes))
        z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
        bs.append(np.mean(z))
    return float(np.mean(x)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(x), len(routes)


def strat_diff(A, B, NB=3000):
    cells = {}
    for r in A:
        cells.setdefault(r["pb"], [[], []])[0].append(r["err"])
    for r in B:
        cells.setdefault(r["pb"], [[], []])[1].append(r["err"])
    use = {c: (np.array(a), np.array(b)) for c, (a, b) in cells.items() if len(a) >= 2 and len(b) >= 2}
    if not use:
        return None
    w = {c: min(len(a), len(b)) for c, (a, b) in use.items()}; W = sum(w.values())

    def est(sampler):
        return sum(w[c] * (np.mean(sampler(b)) - np.mean(sampler(a))) for c, (a, b) in use.items()) / W
    e0 = est(lambda x: x)
    bs = [est(lambda x: x[rng.integers(0, len(x), len(x))]) for _ in range(NB)]
    return e0, np.percentile(bs, 2.5), np.percentile(bs, 97.5), {c: (len(a), len(b)) for c, (a, b) in use.items()}, W


print(f"\n=== v2 (partial-press tolerant), fixed lag {LAG}s, own peak/hold rule ===")
for key in ("aa", "ap"):
    print(f"-- {key} --")
    for G in ("V282", "V282old", "TQ"):
        sub = [r for r in rows if r["G"] == G and r["key"] == key]
        if len(sub) < 3:
            print(f"  {G:8s} n<3 ({len(sub)})"); continue
        est, lo, hi, nn, nr = cl_boot(sub)
        print(f"  {G:8s} mean {est:+.4f} [{lo:+.4f},{hi:+.4f}]  n={nn} routes={nr}")
        cnt = {}
        for r in sub:
            cnt[r["pb"]] = cnt.get(r["pb"], 0) + 1
        print(f"           P-bin counts (0:<60,1:60-150,2:150+): {cnt}")
    A = [r for r in rows if r["G"] == "V282" and r["key"] == key]
    B = [r for r in rows if r["G"] == "TQ" and r["key"] == key]
    xa = np.array([r["err"] for r in A]); xb = np.array([r["err"] for r in B])
    diff0 = xb.mean() - xa.mean()
    routesA = sorted(set(r["rk"] for r in A)); routesB = sorted(set(r["rk"] for r in B))
    byrA = {q: np.array([r["err"] for r in A if r["rk"] == q]) for q in routesA}
    byrB = {q: np.array([r["err"] for r in B if r["rk"] == q]) for q in routesB}
    bs = []
    for _ in range(3000):
        za = np.concatenate([byrA[p][rng.integers(0, len(byrA[p]), len(byrA[p]))] for p in rng.choice(routesA, len(routesA))])
        zb = np.concatenate([byrB[p][rng.integers(0, len(byrB[p]), len(byrB[p]))] for p in rng.choice(routesB, len(routesB))])
        bs.append(zb.mean() - za.mean())
    print(f"  UNSTRATIFIED TQ-V282 diff {diff0:+.4f} [{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}] nA={len(xa)} nB={len(xb)}")
    sres = strat_diff(A, B)
    print(f"  P-BIN STRATIFIED TQ-V282 diff: {sres}")
