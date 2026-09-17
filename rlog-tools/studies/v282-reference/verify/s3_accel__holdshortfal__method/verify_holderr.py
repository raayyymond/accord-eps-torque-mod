"""Independent re-derivation of the 'hold-shortfall' finding (s3_accel), NOT importing s3turns.py.
Own turn/hold detector, own hold-window rule (contiguous |ad|>=0.85*peak, distinct from s3turns' 0.8*P
edge-walk), fixed 0.25 s lag applied via simple np.interp shift (not FFT/cross-corr), aa (wheel) and
ap (pose/yaw) both checked, sign/units re-derived from scratch. Reports per-route AND pooled numbers,
one route in RAM at a time.
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__holdshortfal__method/'

# opendbc Accord bicycle model constants, re-typed independently from opendbc_repo honda/values.py + car/__init__.py
# (same physical model s3turns.py uses -- re-deriving the formula itself, not importing it)
M = 3279 * 0.45359237 + 136.0
WB = 2.83
AF = 0.39 * WB
AR = WB - AF
TSF = 0.8467
M0, WB0 = 1326. + 136., 2.70
AF0 = WB0 * 0.4
AR0 = WB0 - AF0
CF = 192150 * TSF * M / M0 * (AR / WB) / (AR0 / WB0)
CR = 202500 * TSF * M / M0 * (AF / WB) / (AF0 / WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR = 16.33


def curv_to_angle(k, v):
    return -np.degrees(k * SR * WB * (1.0 - SF * v ** 2))


def lag_shift(x, t, lag_s):
    """x(t+lag): simple interpolation shift, independent of s3turns.shift's integer-sample slicing."""
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
    # own peak finder: different distance/prominence than s3turns (3s / 0.6*peak_min there; here 2.5s / 8 deg)
    pk, props = signal.find_peaks(a, height=25.0, prominence=8.0, distance=int(2.5 * V.FS))
    ok = active & ~pressed
    n = len(t)
    events_this_route = 0
    for kk in pk:
        P = a[kk]; s = float(np.sign(adl[kk]))
        vm = float(np.median(v[max(0, kk - 50):kk + 50]))
        if not (2.5 <= vm < 15.0):
            continue
        # hold window: contiguous region straddling kk where s*adl >= 0.85*P (own rule, independent of s3turns)
        thr = 0.85 * P
        i = kk
        while i > 0 and s * adl[i] >= thr:
            i -= 1
        j = kk
        while j < n - 1 and s * adl[j] >= thr:
            j += 1
        i += 1  # first index inside the hold band
        if j - i < 30:  # need >=0.3 s of hold
            continue
        if i < 0 or j >= n:
            continue
        if not ok[i:j].all():
            continue  # require fully engaged, hands-off through the hold
        if np.any(np.diff(t[i:j]) > 4.0 / V.FS):
            continue
        events_this_route += 1
        for key, arr in (("aa", aa), ("ap", ap)):
            src = np.where(pressed, np.nan, arr)
            ach = s * lag_shift(src, t, LAG)
            err = (ach - s * ad)[i:j] / P
            rows.append(dict(rk=rk, group=meta["group"], key=key, v=vm, P=float(P),
                              err=float(np.nanmean(err)), n_frames=int(np.isfinite(err).sum())))
    print(rk, meta["group"], "peaks", len(pk), "kept-events", events_this_route, flush=True)
    del S

json.dump(rows, open(OUT + "verify_rows.json", "w"), indent=1)

GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
rng = np.random.default_rng(42)


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


print(f"\n=== independent hold-window re-derivation, fixed lag {LAG}s, own peak/hold rule ===")
for key in ("aa", "ap"):
    print(f"-- {key} --")
    for G in ("V282", "V282old", "TQ"):
        sub = [r for r in rows if GM[r["group"]] == G and r["key"] == key]
        if len(sub) < 3:
            print(f"  {G:8s} n<3 ({len(sub)})"); continue
        est, lo, hi, n, nr = cl_boot(sub)
        print(f"  {G:8s} mean {est:+.4f} [{lo:+.4f},{hi:+.4f}]  n={n} routes={nr}")
    A = [r for r in rows if GM[r["group"]] == "V282" and r["key"] == key]
    B = [r for r in rows if GM[r["group"]] == "TQ" and r["key"] == key]
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
    print(f"  UNSTRATIFIED TQ-V282 diff {diff0:+.4f} [{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}]"
          f"  nA={len(xa)} nB={len(xb)}")
