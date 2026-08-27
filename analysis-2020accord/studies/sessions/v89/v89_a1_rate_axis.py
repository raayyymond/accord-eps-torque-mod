#!/usr/bin/env python3
"""studies/sessions/v89/v89_a1_rate_axis.py -- test the OPERATOR'S OWN AXIS for micro-ratcheting / ratcheting.

Operator, 2026-08-09:
    "micro-ratcheting  = LKAS engaged and spinning the wheel AT ALL
     ratcheting        = LKAS engaged and spinning the wheel QUICKLY
     macro-ratcheting  = on LARGE steering angle transients"

Every ratchet measurement in this kit has been stratified by VEHICLE SPEED. The operator says
the axis is STEERING-WHEEL RATE. Those two are strongly anti-correlated in the corpus (you spin
the wheel in a car park, not at 116 km/h), so D5's headline -- "amplitude decays 4.8x from creep
to highway" -- may be a RATE effect misread as a SPEED effect.

This script runs the discriminating test on route 73 (V88), which is the only route in the corpus
carrying both a car park and a highway.

METHOD
    windows of nw samples, 50% overlap, on the 100 Hz grid
    per window:  |rate| stats (deg/s), speed stats, angle excursion (macro axis),
                 band rms of the COLUMN TORQUE (tq), engaged/manual purity
    bands:  6-9 Hz  = the ratchet          18-22 Hz = grind #1 (fixed by V88)
            32-38 Hz = NEGATIVE CONTROL    (must NOT track the axis if the axis is causal)
    wheel-order veto: orders 1..6 from the mean wheel speed, circumference swept 2.073-2.088 m;
                      a window is vetoed for a band if any order lands inside it.

CONTROLS (run BEFORE the headline -- feedback-run-the-control-before-the-measurement)
    C1  negative control band 32-38 Hz on the same windows and the same regression
    C2  manual (disengaged) arm at MATCHED rate -- the ratchet is claimed engaged-only
    C3  speed-partialled regression, and the reverse (rate-partialled speed slope)
    C4  block-permutation p-value on the rate slope (episode blocks, not windows)

Bootstraps are over EPISODES (contiguous engaged runs), never windows.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3].parent
CACHE = ROOT / "_scratch/cache/r73" / "r73.npz"
OUT = ROOT / "_scratch/cache/r73" / "v89_a1_rate_axis.json"

NW = 256                      # 2.53 s at 101.06 Hz
HOP = NW // 2
BANDS = {"e_6-9": (6.0, 9.0), "e_18-22": (18.0, 22.0), "negctrl_32-38": (32.0, 38.0)}
CIRC_LO, CIRC_HI = 2.073, 2.088      # m, swept (accord-v57-confirms-wheel-order-tyre-line)
RNG = np.random.default_rng(20260809)


# --------------------------------------------------------------------------- helpers
def band_rms(x: np.ndarray, fs: float, lo: float, hi: float) -> float:
    """rms of x restricted to [lo, hi) Hz. Hann-windowed periodogram, mean removed."""
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    # Parseval-consistent power, corrected for the window's power loss
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    m = (f >= lo) & (f < hi)
    df = f[1] - f[0]
    return float(np.sqrt(np.sum(p[m]) * df))


def order_hits(v_ms: float, lo: float, hi: float, nmax: int = 6) -> bool:
    """True if any wheel order 1..nmax can land inside [lo, hi) at this speed."""
    if v_ms <= 0.05:
        return False
    for circ in (CIRC_LO, CIRC_HI):
        f1 = v_ms / circ
        for n in range(1, nmax + 1):
            if lo <= n * f1 < hi:
                return True
    return False


def ols(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Least squares with an intercept column already in X."""
    return np.linalg.lstsq(X, y, rcond=None)[0]


def episodes_of(mask: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous [start, stop) runs of True."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def boot_ci(vals: np.ndarray, groups: np.ndarray, n: int = 2000, stat=np.median):
    """Bootstrap CI resampling GROUPS (episodes), not rows."""
    uniq = np.unique(groups)
    if len(uniq) < 2:
        return float(stat(vals)), float("nan"), float("nan")
    idx_by_g = {g: np.where(groups == g)[0] for g in uniq}
    draws = []
    for _ in range(n):
        pick = RNG.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([idx_by_g[g] for g in pick])
        draws.append(stat(vals[sel]))
    return float(stat(vals)), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


# --------------------------------------------------------------------------- windowing
def build_windows(z) -> dict:
    t = z["t"]
    fs = 1.0 / float(np.median(np.diff(t)))
    tq = z["tq"].astype(float)
    ang = z["ang"].astype(float)
    rate = z["rate_c"].astype(float)          # coarse steering rate, deg/s, 0x14A b2:4
    v = z["cs_v"].astype(float)
    eng = z["cc_lat"].astype(float) > 0.5     # latActive -- the correct engagement signal
    sstat = z["sstat"].astype(float)
    seg = z["seg"].astype(int)

    rows = []
    for s in range(0, len(t) - NW + 1, HOP):
        sl = slice(s, s + NW)
        e = eng[sl]
        pure_eng = e.mean() > 0.98
        pure_man = e.mean() < 0.02
        if not (pure_eng or pure_man):
            continue
        if not np.isfinite(tq[sl]).all():
            continue
        if (sstat[sl] != 0).any():            # keep only fault-free windows
            continue
        r = np.abs(rate[sl])
        a = ang[sl]
        vv = v[sl]
        row = {
            "i0": s,
            "t0": float(t[s]),
            "seg": int(np.median(seg[sl])),
            "engaged": bool(pure_eng),
            "v_med": float(np.median(vv)),
            "v_max": float(np.max(vv)),
            "rate_med": float(np.median(r)),
            "rate_p90": float(np.percentile(r, 90)),
            "rate_rms": float(np.sqrt(np.mean(r ** 2))),
            "ang_ptp": float(np.ptp(a)),          # the MACRO axis
            "ang_absmed": float(np.median(np.abs(a))),
        }
        for name, (lo, hi) in BANDS.items():
            row[name] = band_rms(tq[sl], fs, lo, hi)
            row[name + "_ordveto"] = order_hits(row["v_med"], lo, hi)
        rows.append(row)
    return {"fs": fs, "rows": rows}


# --------------------------------------------------------------------------- regression
def rate_slope(rows, band, use_veto=True, engaged=True, partial_speed=True):
    """d(log band rms) / d(log rate), optionally partialling out log speed.

    Returns dict with slope, episode-bootstrap CI, n, and the speed slope for comparison.
    """
    sel = [r for r in rows if r["engaged"] == engaged]
    if use_veto:
        sel = [r for r in sel if not r[band + "_ordveto"]]
    # a rate axis needs the wheel to actually move; and a speed covariate needs motion
    sel = [r for r in sel if r["rate_med"] > 0.5 and r["v_med"] > 0.3 and r[band] > 0]
    if len(sel) < 12:
        return {"n": len(sel), "slope": None}

    y = np.log(np.array([r[band] for r in sel]))
    lr = np.log(np.array([r["rate_med"] for r in sel]))
    lv = np.log(np.array([r["v_med"] for r in sel]))
    one = np.ones_like(y)

    X = np.column_stack([one, lr, lv]) if partial_speed else np.column_stack([one, lr])
    b = ols(y, X)

    # episode blocks: contiguous windows in the same segment separated by < 2 windows
    blocks, cur, last = [], 0, None
    for r in sel:
        if last is not None and (r["seg"] != last["seg"] or r["i0"] - last["i0"] > 3 * HOP):
            cur += 1
        blocks.append(cur)
        last = r
    blocks = np.array(blocks)

    uniq = np.unique(blocks)
    draws_r, draws_v = [], []
    for _ in range(2000):
        pick = RNG.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([np.where(blocks == g)[0] for g in pick])
        try:
            bb = ols(y[idx], X[idx])
        except np.linalg.LinAlgError:
            continue
        draws_r.append(bb[1])
        if partial_speed:
            draws_v.append(bb[2])

    out = {
        "n": len(sel), "n_blocks": int(len(uniq)),
        "slope_rate": float(b[1]),
        "ci_rate": [float(np.percentile(draws_r, 2.5)), float(np.percentile(draws_r, 97.5))],
        "corr_rate": float(np.corrcoef(lr, y)[0, 1]),
        "corr_speed": float(np.corrcoef(lv, y)[0, 1]),
        "corr_rate_speed": float(np.corrcoef(lr, lv)[0, 1]),
    }
    if partial_speed:
        out["slope_speed"] = float(b[2])
        out["ci_speed"] = [float(np.percentile(draws_v, 2.5)), float(np.percentile(draws_v, 97.5))]

    # C4 -- block permutation on the rate slope
    perm = []
    for _ in range(2000):
        pr = RNG.permutation(uniq)
        remap = {g: pr[i] for i, g in enumerate(uniq)}
        # permute the rate column BETWEEN blocks, preserving within-block structure
        lr_p = lr.copy()
        for g in uniq:
            src = np.where(blocks == remap[g])[0]
            dst = np.where(blocks == g)[0]
            take = src[:len(dst)] if len(src) >= len(dst) else np.resize(src, len(dst))
            lr_p[dst] = lr[take]
        Xp = np.column_stack([one, lr_p, lv]) if partial_speed else np.column_stack([one, lr_p])
        try:
            perm.append(ols(y, Xp)[1])
        except np.linalg.LinAlgError:
            pass
    perm = np.array(perm)
    out["perm_p"] = float((np.abs(perm) >= abs(b[1])).mean())
    return out


def main():
    z = np.load(CACHE, allow_pickle=True)
    W = build_windows(z)
    rows, fs = W["rows"], W["fs"]
    eng_rows = [r for r in rows if r["engaged"]]
    man_rows = [r for r in rows if not r["engaged"]]

    rep = {"fs": fs, "nw": NW, "n_windows": len(rows),
           "n_engaged": len(eng_rows), "n_manual": len(man_rows)}

    print(f"fs = {fs:.3f} Hz   windows: {len(rows)}  "
          f"(engaged {len(eng_rows)}, manual {len(man_rows)})")

    # ---- how strongly are rate and speed confounded in this corpus? -------------
    lr = np.log([r["rate_med"] for r in eng_rows if r["rate_med"] > 0.5 and r["v_med"] > 0.3])
    lv = np.log([r["v_med"] for r in eng_rows if r["rate_med"] > 0.5 and r["v_med"] > 0.3])
    rep["confound_corr_lograte_logspeed"] = float(np.corrcoef(lr, lv)[0, 1])
    print(f"\nCONFOUND  corr(log rate, log speed) engaged = "
          f"{rep['confound_corr_lograte_logspeed']:+.3f}   (n={len(lr)})")

    # ---- C1/C3/C4: the regression, every band, with and without the speed partial
    print("\n" + "=" * 78)
    print("REGRESSION  d(log column band rms) / d(log |steer rate|)   ENGAGED, order-vetoed")
    print("=" * 78)
    rep["regression"] = {}
    for band in BANDS:
        r_p = rate_slope(eng_rows, band, partial_speed=True)
        r_n = rate_slope(eng_rows, band, partial_speed=False)
        rep["regression"][band] = {"partialled": r_p, "raw": r_n}
        if r_p.get("slope_rate") is None:
            print(f"  {band:14s} n={r_p['n']} -- too few windows")
            continue
        ci = r_p["ci_rate"]
        print(f"  {band:14s} n={r_p['n']:3d} blk={r_p['n_blocks']:2d}  "
              f"rate slope {r_p['slope_rate']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}]  "
              f"perm p={r_p['perm_p']:.4f}   "
              f"speed slope {r_p['slope_speed']:+.3f} "
              f"[{r_p['ci_speed'][0]:+.3f}, {r_p['ci_speed'][1]:+.3f}]")

    # ---- rate deciles: the DOSE CURVE the operator's three tiers predict --------
    print("\n" + "=" * 78)
    print("DOSE CURVE -- engaged, order-vetoed, e_6-9 by |steer rate| bin")
    print("=" * 78)
    sel = [r for r in eng_rows if not r["e_6-9_ordveto"] and r["v_med"] > 0.3]
    sel.sort(key=lambda r: r["rate_med"])
    edges = [0, 2, 5, 10, 20, 40, 80, 1e9]
    rep["dose"] = []
    print(f"  {'|rate| deg/s':>16s} {'n':>4s} {'v med':>7s} {'e_6-9':>9s} "
          f"{'e_18-22':>9s} {'negctrl':>9s} {'ang ptp':>8s}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        b = [r for r in sel if lo <= r["rate_med"] < hi]
        if len(b) < 3:
            continue
        e69 = np.median([r["e_6-9"] for r in b])
        e18 = np.median([r["e_18-22"] for r in b])
        enc = np.median([r["negctrl_32-38"] for r in b])
        lab = f"{lo:.0f}-{hi:.0f}" if hi < 1e8 else f"{lo:.0f}+"
        print(f"  {lab:>16s} {len(b):4d} {np.median([r['v_med'] for r in b]):7.2f} "
              f"{e69:9.1f} {e18:9.1f} {enc:9.1f} "
              f"{np.median([r['ang_ptp'] for r in b]):8.1f}")
        rep["dose"].append({"lo": lo, "hi": hi, "n": len(b),
                            "v_med": float(np.median([r["v_med"] for r in b])),
                            "e_6-9": float(e69), "e_18-22": float(e18),
                            "negctrl": float(enc),
                            "ang_ptp": float(np.median([r["ang_ptp"] for r in b]))})

    # ---- C2: the manual arm at MATCHED rate ------------------------------------
    print("\n" + "=" * 78)
    print("C2  ENGAGED vs MANUAL at MATCHED |steer rate| (and matched speed band)")
    print("=" * 78)
    rep["engaged_vs_manual"] = []
    for lo, hi in [(2, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 1e9)]:
        e = [r for r in eng_rows if lo <= r["rate_med"] < hi and 0.3 < r["v_med"] < 6.0
             and not r["e_6-9_ordveto"]]
        m = [r for r in man_rows if lo <= r["rate_med"] < hi and 0.3 < r["v_med"] < 6.0
             and not r["e_6-9_ordveto"]]
        if len(e) < 3 or len(m) < 3:
            print(f"  rate {lo:3.0f}-{hi if hi<1e8 else 999:3.0f}: "
                  f"engaged n={len(e):3d}  manual n={len(m):3d}  -- insufficient")
            rep["engaged_vs_manual"].append({"lo": lo, "hi": hi, "n_eng": len(e),
                                             "n_man": len(m), "ratio": None})
            continue
        ee = np.median([r["e_6-9"] for r in e])
        mm = np.median([r["e_6-9"] for r in m])
        print(f"  rate {lo:3.0f}-{hi if hi<1e8 else 999:3.0f}: "
              f"engaged n={len(e):3d} e_6-9={ee:8.1f}   "
              f"manual n={len(m):3d} e_6-9={mm:8.1f}   ratio={ee/mm:6.2f}x")
        rep["engaged_vs_manual"].append({"lo": lo, "hi": hi, "n_eng": len(e), "n_man": len(m),
                                         "eng": float(ee), "man": float(mm),
                                         "ratio": float(ee / mm)})

    # ---- does RATE explain D5's creep->highway decay? --------------------------
    print("\n" + "=" * 78)
    print("D5 RE-READ -- is the 4.8x creep->highway decay a SPEED effect or a RATE effect?")
    print("=" * 78)
    strata = [("creep <10 km/h", 0.3, 2.78), ("10-40", 2.78, 11.11),
              ("40-80", 11.11, 22.22), (">80 km/h", 22.22, 99.0)]
    rep["d5_reread"] = []
    for name, vlo, vhi in strata:
        b = [r for r in eng_rows if vlo <= r["v_med"] < vhi and not r["e_6-9_ordveto"]]
        if len(b) < 3:
            continue
        print(f"  {name:16s} n={len(b):3d}  |rate| med={np.median([r['rate_med'] for r in b]):7.2f} "
              f"deg/s   e_6-9={np.median([r['e_6-9'] for r in b]):8.1f}")
        rep["d5_reread"].append({"stratum": name, "n": len(b),
                                 "rate_med": float(np.median([r["rate_med"] for r in b])),
                                 "e_6-9": float(np.median([r["e_6-9"] for r in b]))})

    # rate-matched speed contrast: hold |rate| in one bin, compare speed strata
    print("\n  RATE-MATCHED speed contrast (the discriminating cut):")
    rep["rate_matched_speed"] = []
    for rlo, rhi in [(2, 10), (10, 40)]:
        row = []
        for name, vlo, vhi in strata:
            b = [r for r in eng_rows if vlo <= r["v_med"] < vhi
                 and rlo <= r["rate_med"] < rhi and not r["e_6-9_ordveto"]]
            row.append((name, len(b), np.median([r["e_6-9"] for r in b]) if len(b) >= 3 else None))
        txt = "  ".join(f"{n}:{('%.0f' % v) if v else '--':>5s}(n={c})" for n, c, v in row)
        print(f"    |rate| {rlo}-{rhi} deg/s :  {txt}")
        rep["rate_matched_speed"].append({"rate_lo": rlo, "rate_hi": rhi,
                                          "rows": [{"stratum": n, "n": c, "e_6-9": v}
                                                   for n, c, v in row]})

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
