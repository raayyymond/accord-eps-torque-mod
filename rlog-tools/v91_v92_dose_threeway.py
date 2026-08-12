#!/usr/bin/env python3
r"""THE THREE-WAY DOSE TEST -- route 77 (V90, UNDOSED) vs route 78 (V91) vs route 79 (V92),
on ONE statistic that all three routes can produce, cell-stratified and episode-bootstrapped.

===================================================================================================
WHY A SECOND SCRIPT.  Two defects in `v91_v92_dose_in_force.py` had to be fixed before the engaged
arm could be believed, and both are the kind that produce a CONFIDENT WRONG ANSWER:
===================================================================================================
1. 🛑 THE GEOMETRIC MEAN COLLAPSED ON A ZERO MEDIAN.  `|gp-0x6b26|` is quantised at 1.6 counts/LSB
   and its engaged median sits at 1-3 LSB, so a bootstrap draw can hand a cell a median of exactly
   0.0 -> log(0) = -inf -> the whole weighted geometric mean goes to 0.  That is what produced the
   degenerate CI lower bound of 0.0000.  Fixed by dropping non-positive cells from the estimator
   and REPORTING how many were dropped, never by silently flooring them.
2. 🛑 THE MEDIAN IS THE WRONG STATISTIC HERE, and §10.1 says so itself: *"the p50 sits at only ~3
   wire LSB, so p75/p90/p95 are the load-bearing statistics; p50 is quantisation-coarse."*  This
   script runs p50/p75/p90/mean and reports all four -- a dose that is real must move ALL of them.

===================================================================================================
THE COMMON STATISTIC:  duty = P( |gp-0x6b26| >= 15 counts ), cell by cell
===================================================================================================
Route 79 lost the continuous 427 channel (it was repointed to gp-0x6bbe), so the ONLY thing all
three routes can report about the dosed cell is that one threshold crossing:

    route 77 / 78 : from 427,  wire = (|b26| * 5) >> 3   =>  |b26| >= 15  <=>  wire >= 9.375
    route 79      : from the cave rung byte7 b7, which tests |b26| >= 15 EXACTLY, at 1 kHz

🛑 THE THRESHOLD DOES NOT LAND ON A WIRE LSB, so 427 can only BRACKET it, and both sides are
   reported rather than one being picked:
       wire >= 9   <=>  |b26| >= 14.4   (slightly OVER-counts -- upper bracket)
       wire >= 10  <=>  |b26| >= 16.0   (slightly UNDER-counts -- lower bracket)
   The true duty lies between them.  A dose claim that survives only inside the bracket is not a
   claim.

⊕ WHY THIS TEST IS DECISIVE WHERE THE r78 ARM ALONE IS NOT.  V91 is telemetry-identical to V90, so
  route 78 alone cannot prove WHICH of the two was flashed.  **Route 79 can: V92's identity is
  proven single-frame (0x14A byte7[7:6] != 0, impossible on every build V53-V91), and the V92 image
  on disk carries the x1.5 row at 0xD7A5C/0xD7A6C -- verified from the image in this session.**
  So on route 79 the dose is ON THE CAR BY CONSTRUCTION, and any null there is a null on the LEVER,
  not on the flash.

PREDICTION, derived by pushing route 77's OWN samples through the dose and the same threshold --
no model, no assumed distribution:
    predicted duty(cell) = P( 1.5 * |b26_77(cell)| >= 15 )  =  P( |b26_77(cell)| >= 10 )

Usage:  python v91_v92_dose_threeway.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = ROOT / "analysis-2020accord"

RNG = np.random.default_rng(20260811)
NBOOT = 4000
SPEED_BINS = [(0.0, 5.0), (5.0, 20.0), (20.0, 50.0), (50.0, 80.0), (80.0, 1e9)]
RATE_BINS = [(0.0, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0), (13.0, 25.0), (25.0, 50.0),
             (50.0, 1e9)]
MIN_CELL = 40
W2C = 8.0 / 5.0
DOSE = 1.5
T = 15.0


def load(route, stem):
    z = np.load(CACHE / f"_cache_r{route}" / f"{stem}.npz", allow_pickle=True)
    rt = np.asarray(z["t"], float)
    v = np.abs(np.asarray(z["cs_v"], float))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(rt)
    dt[dt <= 0] = np.median(dt[dt > 0]) if (dt > 0).any() else 0.01
    rate = np.abs(np.gradient(ang) / dt)
    return z, rt, v, lat, rate


def on(t, rt, a, b=False):
    return np.interp(t, rt, a.astype(float)) > 0.5 if b else np.interp(t, rt, a)


def wire_route(route, stem):
    z, rt, v, lat, rate = load(route, stem)
    t = np.asarray(z["ab_t1ab"], float)
    w = np.asarray(z["ab_mt"], int)
    return dict(tag=f"r{route}", t=t, wire=w, counts=w * W2C,
                lat=on(t, rt, lat, True), v=on(t, rt, v) * 3.6, rate=on(t, rt, rate))


def rung_route(route, stem):
    z, rt, v, lat, rate = load(route, stem)
    t = np.asarray(z["raw14_t"], float)
    return dict(tag=f"r{route}", t=t, hit=(np.asarray(z["raw14_b7"], int) & 0x80) != 0,
                lat=on(t, rt, lat, True), v=on(t, rt, v) * 3.6, rate=on(t, rt, rate))


def cells(v, rate):
    sb = np.full(len(v), -1, int)
    for i, (lo, hi) in enumerate(SPEED_BINS):
        sb[(v >= lo) & (v < hi)] = i
    rb = np.full(len(rate), -1, int)
    for i, (lo, hi) in enumerate(RATE_BINS):
        rb[(rate >= lo) & (rate < hi)] = i
    return np.where((sb >= 0) & (rb >= 0), sb * len(RATE_BINS) + rb, -1)


def cname(c):
    s, r = divmod(c, len(RATE_BINS))
    a, b = SPEED_BINS[s]
    x, y = RATE_BINS[r]
    return f"v{a:.0f}-{'+' if b > 1e8 else f'{b:.0f}'} r{x:.0f}-{'+' if y > 1e8 else f'{y:.0f}'}"


def episodes(mask):
    e = np.full(len(mask), -1, int)
    k, run = 0, False
    for i, x in enumerate(mask):
        if x:
            if not run:
                k += 1
                run = True
            e[i] = k - 1
        else:
            run = False
    return e


# ======================================================================================
def ratio_stat(av, ac, bv, bc, fn):
    """Weighted geometric mean of per-cell ratios.  NON-POSITIVE cells are DROPPED and counted."""
    num, wt, dropped, rows = [], [], 0, []
    for c in np.unique(ac[ac >= 0]):
        sa, sb = av[ac == c], bv[bc == c]
        if len(sa) < MIN_CELL or len(sb) < MIN_CELL:
            continue
        ma, mb = fn(sa), fn(sb)
        if not (ma > 0 and mb > 0):
            dropped += 1
            continue
        w = float(min(len(sa), len(sb)))
        num.append(np.log(ma / mb)); wt.append(w)
        rows.append((int(c), len(sa), len(sb), float(ma), float(mb), float(ma / mb)))
    if not num:
        return float("nan"), rows, dropped
    return float(np.exp(np.sum(np.array(wt) * np.array(num)) / np.sum(wt))), rows, dropped


def boot(av, ac, ae, bv, bc, be, fn, nboot=NBOOT):
    ua, ub = np.unique(ae), np.unique(be)
    ia = {e: np.flatnonzero(ae == e) for e in ua}
    ib = {e: np.flatnonzero(be == e) for e in ub}
    out = []
    for _ in range(nboot):
        pa = np.concatenate([ia[e] for e in RNG.choice(ua, len(ua), replace=True)])
        pb = np.concatenate([ib[e] for e in RNG.choice(ub, len(ub), replace=True)])
        r, _, _ = ratio_stat(av[pa], ac[pa], bv[pb], bc[pb], fn)
        if np.isfinite(r):
            out.append(r)
    out = np.array(out)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(out)


STATS = [("p50", lambda x: float(np.median(x))),
         ("p75", lambda x: float(np.percentile(x, 75))),
         ("p90", lambda x: float(np.percentile(x, 90))),
         ("mean", lambda x: float(np.mean(x)))]


def continuous_arm(tag, A, B, sa, sb):
    print(f"\n  --- {tag} ---")
    print(f"      test frames {sa.sum():,}   baseline frames {sb.sum():,}")
    ac, bc = cells(A["v"], A["rate"])[sa], cells(B["v"], B["rate"])[sb]
    av, bv = A["counts"][sa], B["counts"][sb]
    ae, be = episodes(sa)[sa], episodes(sb)[sb]
    res = {}
    print(f"      {'stat':<6} {'ratio':>8}  {'95 % CI':>20}  cells  dropped")
    for nm, fn in STATS:
        r, rows, dr = ratio_stat(av, ac, bv, bc, fn)
        lo, hi = boot(av, ac, ae, bv, bc, be, fn)[:2]
        res[nm] = dict(ratio=r, ci=[lo, hi], n_cells=len(rows), dropped=dr)
        star = "✅" if lo > 1.275 else ("🛑" if lo <= 1.0 <= hi else "⚠")
        print(f"   {star} {nm:<6} {r:>8.4f}  [{lo:>7.4f}, {hi:>7.4f}]  {len(rows):>5}  {dr:>7}")
    return res


# ======================================================================================
def duty_of(A, sel, thr_wire):
    return (A["wire"][sel] >= thr_wire).astype(float)


def duty_arm(rows_by_route, ep_by_route, cid_by_route, label):
    """Cell-stratified duty, three routes, common cells only."""
    common = None
    for k, cid in cid_by_route.items():
        u = {int(c) for c in np.unique(cid) if c >= 0
             and (cid == c).sum() >= MIN_CELL}
        common = u if common is None else (common & u)
    common = sorted(common)
    print(f"\n  --- {label}: {len(common)} cells populated on ALL THREE routes ---")
    hdr = f"    {'cell':<16} " + " ".join(f"{k:>16}" for k in rows_by_route)
    print(hdr)
    tot = {k: [] for k in rows_by_route}
    wts = []
    for c in common:
        line = f"    {cname(c):<16} "
        w = min(int((cid_by_route[k] == c).sum()) for k in rows_by_route)
        wts.append(w)
        for k in rows_by_route:
            m = cid_by_route[k] == c
            d = float(rows_by_route[k][m].mean())
            tot[k].append(d)
            line += f" {d:>7.3f}(n={int(m.sum()):>5,})"
        print(line)
    wts = np.array(wts, float)
    print(f"\n    {'weighted mean duty':<24}" +
          "".join(f"  {k}: {np.sum(wts*np.array(tot[k]))/wts.sum():.4f}" for k in rows_by_route))
    return {k: dict(per_cell=tot[k],
                    weighted=float(np.sum(wts * np.array(tot[k])) / wts.sum()))
            for k in rows_by_route}, common, wts


# ======================================================================================
def main():
    R77 = wire_route("77", "r77")
    R78 = wire_route("78", "r78")
    R79 = rung_route("79", "r79")
    out = {}

    print("=" * 100)
    print(" PART 1 — ROUTE 78 (V91) vs ROUTE 77 (V90), CONTINUOUS |gp-0x6b26| FROM 427")
    print("=" * 100)
    out["v91_engaged"] = continuous_arm(
        "ENGAGED, cell-stratified (PRE-REGISTERED expectation: 1.50, window [1.275, 1.725])",
        R78, R77, R78["lat"], R77["lat"])
    out["v91_manual"] = continuous_arm(
        "MANUAL negative control, cell-stratified (expectation: 1.00 — mode 24 was NOT edited)",
        R78, R77, ~R78["lat"], ~R77["lat"])

    print("\n" + "=" * 100)
    print(" PART 2 — ALL THREE ROUTES ON THE ONE STATISTIC V92 CAN STILL REPORT")
    print("         duty = P(|gp-0x6b26| >= 15 counts), cell-stratified, ENGAGED")
    print("=" * 100)
    for thr, brack in ((9, "wire>=9  <=> |b26|>=14.4  (UPPER bracket — over-counts)"),
                       (10, "wire>=10 <=> |b26|>=16.0  (LOWER bracket — under-counts)")):
        e77, e78, e79 = R77["lat"], R78["lat"], R79["lat"]
        rows = {"r77 V90 undosed": duty_of(R77, e77, thr),
                "r78 V91": duty_of(R78, e78, thr),
                "r79 V92 (rung)": R79["hit"][e79].astype(float)}
        cid = {"r77 V90 undosed": cells(R77["v"], R77["rate"])[e77],
               "r78 V91": cells(R78["v"], R78["rate"])[e78],
               "r79 V92 (rung)": cells(R79["v"], R79["rate"])[e79]}
        print(f"\n  🛑 427 BRACKET: {brack}")
        d, common, wts = duty_arm(rows, None, cid, f"DUTY, threshold wire>={thr}")
        # predicted duty for the dosed routes, from r77's own samples
        pred = []
        for c in common:
            m = cid["r77 V90 undosed"] == c
            sub = R77["counts"][e77][m]
            pred.append(float(np.mean(DOSE * sub >= T)))
        pw = float(np.sum(wts * np.array(pred)) / wts.sum())
        print(f"    {'PREDICTED at ×1.5':<24}  from r77's own samples: {pw:.4f}")
        print(f"    ⇒ lift needed: {pw / d['r77 V90 undosed']['weighted']:.3f}×   "
              f"observed r78 {d['r78 V91']['weighted'] / d['r77 V90 undosed']['weighted']:.3f}×   "
              f"observed r79 {d['r79 V92 (rung)']['weighted'] / d['r77 V90 undosed']['weighted']:.3f}×")
        out[f"duty_thr{thr}"] = dict(routes=d, predicted_weighted=pw,
                                     cells=[cname(c) for c in common])

    (CACHE / "_cache_r78" / "dose_threeway.json").write_text(json.dumps(out, indent=1,
                                                                       default=float))
    print("\n  wrote analysis-2020accord/_cache_r78/dose_threeway.json")


if __name__ == "__main__":
    main()
