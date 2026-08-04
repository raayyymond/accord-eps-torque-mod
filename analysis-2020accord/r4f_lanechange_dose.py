#!/usr/bin/env python3
"""Is the ~26-30 Hz LANE-CHANGE TRANSIENT dose-dependent? — the whole corpus on one dose axis.

THE QUESTION. V68 captured a 28 Hz lane-change burst; route `4f` shows the phenomenon SURVIVED V69
and ran LARGER in peak-to-peak (2599 / 4094 counts vs V68's 1468). V69's stated mechanism is the r24
rate lane, and V69 cut the highway dose from V68's 2.00x to EXACTLY 1.000x (byte-identical to stock:
>= 50 km/h reads only rec2/rec3 and V69 edited only the 0 and 10 km/h records). **If the transient is
dose-INDEPENDENT across the whole corpus, V69's mechanism is dead for this symptom and V70 must not
chase it.**

WHY A CROSS-ROUTE DESIGN IS NEEDED AND WHAT IT COSTS. No single route carries two doses at highway:
V67/V68's gate is 1:1 with LKAS engagement above 8 m/s, and V62/V65/V69 are unconditional. So the
dose axis is assembled ACROSS routes, which confounds dose with road, day, tyre and traffic.
⚠ Two defences, both mandatory here and both from the kit's own retraction record:
  ×MEDIAN-FLOOR   Every window is divided by ITS OWN ROUTE's median 26-30 Hz envelope over engaged
                  highway. A raw envelope is not comparable across routes; the ×floor ratio is. This
                  is the quantity the route-4f pass already identified as the comparable one.
  SPEED MATCHING  An averaged/pooled comparison of two routes is only legitimate if the speed
                  distributions overlap -- a moving wheel order concentrates in a narrow-speed route
                  and smears in a wide one (HANDOFF-2026-08-03 method note 1). Per-pool speed
                  distributions are printed, and every headline is repeated on a common window.
  EPISODES        Bootstrap over ~10.2 s blocks, never windows. SPLIT-HALF NULL beside every ratio.

DOSE IS COMPUTED FROM THE IMAGE BYTES, per route, not quoted:
  V58/V59/V64 stock lane                      1.000x
  V62/V65     `sar 0xa`->`sar 0x9`            2.000x flat, every speed and rate
  V67/V68     gate + 0xC6446 = 5244 SUBSTITUTES for the LERP while LKAS applies  (~2.40x at highway)
  V69         surface rec0/rec1 only          1.000x at highway -- STRUCTURALLY stock
★ At highway the MANEUVER rate axis sits inside the FLAT [0, 400]-count segment of `gp-0x6ac0`
  (19-60 deg/s = 90-283 counts), so the rate shaping does not bite here and the dose is the speed
  record's value. Asserted numerically in §1 rather than assumed.

Usage:  python r4f_lanechange_dose.py [--rebuild]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                       # noqa: E402
import _r4f_lib as L                                          # noqa: E402
from _r31_common import load, periodogram, runs_of, sustained  # noqa: E402
from r4f_rate_axis_grind2 import CPS, IMAGES, delivered, gain_b, IMG  # noqa: E402

G.BANDS["26-30"] = (26.0, 30.0)
BANDS_RPT = ["1-4", "18-22", "24-28", "26-30", "30-40", "40-49"]
NFFT, HOP = G.NFFT, G.HOP
HWY = 20.0
MV_HI = 19.0                       # V68's absolute maneuver cut, reused unchanged
KMH_COUNTS = 64.0625               # 0xC6010's scale
PKL = ROOT / "_cache_lanechange_dose.pkl"

# route -> cache, prefix, build image key, and whether the ENGAGED arm is the dosed one
ROUTES = {
    "r2b/V58": ("_cache_r2b", "r2bs", "V58", True),
    "r2c/V59": ("_cache_r2c", "r2cs", "V59", True),
    "r35/V64": ("_cache_r35", "r35s", "V64", True),
    "r31/V61": ("_cache_r31", "r31s", "V61", True),
    "r37/V62": ("_cache_r37", "r37s", "V62", True),
    "r3a/V65": ("_cache_r3a", "r3as", "V65", True),
    "r3b/V65": ("_cache_r3b", "r3bs", "V65", True),
    "r47/V67": ("_cache_r47", "r47s", "V67", True),
    "r4a/V67": ("_cache_r4a", "r4as", "V67", True),
    "4e/V68":  ("_cache_v68", "4es", "V68", True),
    "4c/V68":  ("_cache_v68", "4cs", "V68", True),
    "4f/V69":  ("_cache_r4f", "r4fs", "V69", True),
}
for k in ("V58", "V59", "V61", "V64", "V65", "V68"):
    IMAGES.setdefault(k, Path(str(IMAGES["V69"]).replace("_v69_", f"_{k.lower()}_")))
    if k not in IMG and IMAGES[k].exists():
        IMG[k] = IMAGES[k].read_bytes()


def hdr(s):
    print(f"\n{'=' * 116}\n{s}\n{'=' * 116}")


def segs_of(cache, pfx):
    out = []
    for p in sorted(glob.glob(str(ROOT / cache / f"{pfx}*.npz"))):
        b = os.path.basename(p)
        if any(t in b for t in ("_imu", "_rpm", "_snd", "_events")):
            continue
        tail = b[len(pfx):-4]
        if tail.isdigit():
            out.append(int(tail))
    return sorted(out)


def wrecs(tag):
    cache, pfx, img, _ = ROUTES[tag]
    out = []
    for s in segs_of(cache, pfx):
        d = load(s, ROOT / cache, pfx)
        if "cs_v" not in d or "tq" not in d or "rate_c" not in d:
            continue
        fs = L.fs_lattice(d)
        if not 95 < fs < 105:
            continue
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        taper = np.hanning(NFFT) + 1e-3
        cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
        le = np.asarray(d["cc_lat"], float) > 0.5
        for eng, mask in ((1, le), (0, ~le)):
            for a, b in runs_of(mask, d["t"], NFFT):
                x = np.asarray(d["tq"][a:b], float)
                nwin = 0
                for i in range(0, len(x) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    v = float(np.mean(np.abs(d["cs_v"][sl])))
                    if v < HWY:                      # highway only -- this script's whole subject
                        nwin += 1
                        continue
                    P = periodogram(x[i:i + NFFT], fs, NFFT, True)
                    if P is None:
                        continue
                    R = G.prom_spectrum(f, P)
                    xw = x[i:i + NFFT]
                    r = dict(route=tag, img=img, seg=int(s), eng=eng, v=v,
                             ep=(tag, int(s), int(a), int(b)), t0=float(d["t"][a + i]))
                    for k in BANDS_RPT:
                        lo, hi = G.BANDS[k]
                        r["e_" + k] = G.win_env(xw, fs, lo, hi, taper, cw)
                    r["f_2630"], r["p_2630"] = G.locate(f, P, 26.0, 30.0, R=R)
                    r["pp"] = float(xw.max() - xw.min())
                    rate = np.abs(np.asarray(d["rate_c"][sl], float))
                    r["ratepk"] = float(np.max(rate))
                    r["r50"] = float(np.median(rate))
                    r["eff"] = float(np.mean(np.abs(sustained(d["tq"][sl], fs))))
                    r["blk"] = r["ep"] + (nwin // 8,)
                    nwin += 1
                    out.append(r)
    return out


def records(rebuild=False):
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            st = pickle.load(fh)
        if set(st) >= set(ROUTES):
            return st
    st = {}
    for t in ROUTES:
        st[t] = wrecs(t)
        print(f"   {t}: {len(st[t])} highway windows "
              f"({sum(1 for r in st[t] if r['eng'])} engaged)")
    with open(PKL, "wb") as fh:
        pickle.dump(st, fh)
    return st


def dose_at(imgkey, v_ms, rate_degs, engaged):
    """The delivered r24 multiplier vs stock at one operating point, from that build's bytes."""
    if imgkey not in IMG:
        return np.nan
    return delivered(imgkey, IMG[imgkey], int(round(v_ms * 3.6 * KMH_COUNTS)),
                     int(round(rate_degs * CPS)), engaged)


def boot_ratio(A, B, key, rng, nboot=4000, agg=np.median):
    epA, epB = G.episodes(A), G.episodes(B)
    if not epA or not epB:
        return np.nan, (np.nan, np.nan)
    pt = agg(G.col(A, key)) / agg(G.col(B, key))
    out = []
    for _ in range(nboot):
        a = np.concatenate([G.col(epA[i], key) for i in rng.integers(0, len(epA), len(epA))])
        b = np.concatenate([G.col(epB[i], key) for i in rng.integers(0, len(epB), len(epB))])
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    if not out:
        return float(pt), (np.nan, np.nan)
    return float(pt), (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def split_null(rs, key, rng, nrep=800, agg=np.median):
    ep = G.episodes(rs)
    if len(ep) < 4:
        return (np.nan, np.nan)
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(ep))
        h = len(ep) // 2
        a = np.concatenate([G.col(ep[i], key) for i in idx[:h]])
        b = np.concatenate([G.col(ep[i], key) for i in idx[h:]])
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    return ((float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out
            else (np.nan, np.nan))


def theil_sen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    s = [(y[j] - y[i]) / (x[j] - x[i])
         for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i]]
    if not s:
        return np.nan, np.nan, np.nan
    s = np.array(s)
    return float(np.median(s)), float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


# =================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--json", default=str(HERE / "_r4f_lanechange_dose.json"))
    a = ap.parse_args()
    rng = np.random.default_rng(20260804)
    G.EPKEY = "blk"
    RES: dict = {}

    hdr("0.  BUILDING THE CORPUS — engaged highway windows on every route that has any")
    st = records(a.rebuild)

    hdr("1.  THE DOSE AXIS, FROM THE IMAGE BYTES — and the check that rate shaping does not bite")
    print("   ★ At highway a maneuver's rate is 19-60 deg/s = 90-283 counts on `gp-0x6ac0`, INSIDE")
    print("     the flat [0, 400] segment. Verified numerically: the delivered multiplier is")
    print("     evaluated at both ends of that range and must agree.\n")
    print(f"   {'route':10s} {'build':6s} {'n eng hwy':>10s} {'blocks':>7s} {'v p10/p50/p90':>20s} "
          f"{'dose @25 m/s':>13s} {'@19 deg/s':>10s} {'@60 deg/s':>10s}  arm")
    pools = {}
    for t, (cache, pfx, img, _) in ROUTES.items():
        rs = [r for r in st[t] if r["eng"] and r["v"] >= HWY]
        man = [r for r in st[t] if not r["eng"] and r["v"] >= HWY]
        for lab, arr, eng in (("ENGAGED", rs, True), ("manual", man, False)):
            if len(arr) < 8:
                continue
            v = G.col(arr, "v")
            d19 = dose_at(img, 25.0, 19.0, eng)
            d60 = dose_at(img, 25.0, 60.0, eng)
            print(f"   {t:10s} {img:6s} {len(arr):10d} {len(G.episodes(arr)):7d} "
                  f"{str(np.percentile(v, [10, 50, 90]).round(1)):>20s} "
                  f"{d19:13.3f} {d19:10.3f} {d60:10.3f}  {lab}")
            assert not np.isfinite(d19) or abs(d19 - d60) < 1e-9, \
                f"{t}: rate shaping DOES bite at highway ({d19:.3f} vs {d60:.3f}) -- re-cut the design"
            pools[(t, lab)] = dict(recs=arr, dose=float(d19), img=img, eng=eng)
    print("\n   ✅ every route's @19 and @60 deg/s doses agree ⇒ the rate axis is flat here and the")
    print("     dose is the SPEED record's value. The design is a clean 1-D dose axis at highway.")

    # ---------------------------------------------------------------- 2 -------------------------
    hdr("2.  ×MEDIAN-FLOOR — the only cross-route comparable quantity")
    print("   Each window's 26-30 Hz envelope divided by ITS OWN ROUTE-ARM's median over engaged")
    print("   highway. Maneuver = |rate|pk >= 19.0 deg/s (V68's absolute cut, unchanged).\n")
    for k, p in pools.items():
        floor = float(np.median(G.col(p["recs"], "e_26-30")))
        p["floor"] = floor
        for r in p["recs"]:
            r["xfloor"] = r["e_26-30"] / floor
            r["xfloor_4049"] = r["e_40-49"] / max(float(np.median(G.col(p["recs"], "e_40-49"))), 1e-9)
    print(f"   {'route/arm':18s} {'dose':>6s} {'floor':>7s} {'n mv':>5s} {'blk':>4s} "
          f"{'xfloor med':>10s} {'p90':>7s} {'MAX':>7s} {'pp MAX':>7s} {'f0 of max':>10s}")
    rows = []
    for (t, lab), p in sorted(pools.items(), key=lambda kv: kv[1]["dose"]):
        mv = [r for r in p["recs"] if r["ratepk"] >= MV_HI]
        if len(mv) < 4:
            print(f"   {t + '/' + lab:18s} {p['dose']:6.3f} {p['floor']:7.1f} {len(mv):5d}   "
                  f"-- too few maneuver windows")
            continue
        xf = G.col(mv, "xfloor")
        top = max(mv, key=lambda r: r["xfloor"])
        print(f"   {t + '/' + lab:18s} {p['dose']:6.3f} {p['floor']:7.1f} {len(mv):5d} "
              f"{len(G.episodes(mv)):4d} {np.median(xf):10.2f} {np.percentile(xf, 90):7.2f} "
              f"{xf.max():7.2f} {top['pp']:7.0f} {top['f_2630']:10.2f}")
        rows.append(dict(route=t, arm=lab, dose=p["dose"], n=len(mv),
                         blk=len(G.episodes(mv)), med=float(np.median(xf)),
                         p90=float(np.percentile(xf, 90)), mx=float(xf.max()),
                         ppmax=float(top["pp"]), recs=mv))
    RES["per_route"] = [{k: v for k, v in r.items() if k != "recs"} for r in rows]

    # ---------------------------------------------------------------- 3 -------------------------
    hdr("3.  POOLED BY DOSE — is ×median-floor dose-dependent?")
    DOSE_POOLS = {"1.000x (stock lane)": lambda d: d < 1.2,
                  "2.000x (V62/V65 flat)": lambda d: 1.8 <= d < 2.2,
                  "~2.40x (V67/V68 arm)": lambda d: d >= 2.2}
    P = {}
    for nm, sel in DOSE_POOLS.items():
        mv = [r for row in rows if sel(row["dose"]) for r in row["recs"]]
        P[nm] = mv
        if not mv:
            print(f"   {nm:24s} -- empty")
            continue
        xf = G.col(mv, "xfloor")
        v = G.col(mv, "v")
        print(f"   {nm:24s} n={len(mv):4d} blocks={len(G.episodes(mv)):3d}  "
              f"xfloor med {np.median(xf):5.2f}  p90 {np.percentile(xf, 90):5.2f}  "
              f"max {xf.max():6.2f}   v p10/p50/p90 {np.percentile(v, [10, 50, 90]).round(1)}   "
              f"routes {sorted(set(r['route'] for r in mv))}")
    lo = max(np.percentile(G.col(v_, "v"), 5) for v_ in P.values() if v_)
    hi = min(np.percentile(G.col(v_, "v"), 95) for v_ in P.values() if v_)
    print(f"\n   🛑 SPEED-MATCHED window common to all pools: {lo:.2f} - {hi:.2f} m/s")
    RES["dose_pools"] = {}
    for tag, sel in (("ALL windows", lambda r: True),
                     (f"MATCHED {lo:.1f}-{hi:.1f} m/s", lambda r: lo <= r["v"] <= hi)):
        print(f"\n   --- {tag} ---")
        print(f"   {'contrast':38s} {'ratio':>7s} {'[95% CI]':>20s} {'split-half null':>20s}  verdict")
        base = [r for r in P["1.000x (stock lane)"] if sel(r)]
        RES["dose_pools"][tag] = {}
        for nm in ("2.000x (V62/V65 flat)", "~2.40x (V67/V68 arm)"):
            arm = [r for r in P[nm] if sel(r)]
            if len(arm) < 4 or len(base) < 4:
                print(f"   {nm + ' / 1.000x':38s}  -- too few windows")
                continue
            pt, ci = boot_ratio(arm, base, "xfloor", rng)
            nl = split_null(arm + base, "xfloor", rng)
            verd = ("CLEARS null" if np.isfinite(ci[0]) and np.isfinite(nl[1]) and ci[0] > nl[1]
                    else "inside null ⇒ NO dose effect")
            RES["dose_pools"][tag][nm] = dict(ratio=pt, ci=ci, null=nl,
                                              n_arm=len(arm), n_base=len(base))
            print(f"   {nm + ' / 1.000x':38s} {pt:7.3f} [{ci[0]:8.3f}, {ci[1]:8.3f}] "
                  f"[{nl[0]:8.2f}, {nl[1]:8.2f}]  {verd}")
        # the pre-declared negative control: 40-49 Hz on the same windows
        for nm in ("2.000x (V62/V65 flat)", "~2.40x (V67/V68 arm)"):
            arm = [r for r in P[nm] if sel(r)]
            if len(arm) < 4 or len(base) < 4:
                continue
            pt, ci = boot_ratio(arm, base, "xfloor_4049", rng)
            nl = split_null(arm + base, "xfloor_4049", rng)
            print(f"   {'  [neg ctl 40-49] ' + nm.split()[0]:38s} {pt:7.3f} "
                  f"[{ci[0]:8.3f}, {ci[1]:8.3f}] [{nl[0]:8.2f}, {nl[1]:8.2f}]")

    # ---------------------------------------------------------------- 4 -------------------------
    hdr("4.  THE DOSE-RESPONSE SLOPE — per-route point estimates against dose")
    print("   One point per route/arm, so route (not window) is the unit and the cross-route")
    print("   confound is at least visible. Theil-Sen slope of xfloor p90 on dose.\n")
    use = [r for r in rows if r["blk"] >= 2]
    print(f"   {'route/arm':18s} {'dose':>6s} {'xfloor p90':>10s} {'xfloor MAX':>10s} {'blk':>4s}")
    for r in sorted(use, key=lambda z: z["dose"]):
        print(f"   {r['route'] + '/' + r['arm']:18s} {r['dose']:6.3f} {r['p90']:10.2f} "
              f"{r['mx']:10.2f} {r['blk']:4d}")
    for stat in ("p90", "mx"):
        sl, l, h = theil_sen([r["dose"] for r in use], [r[stat] for r in use])
        RES[f"slope_{stat}"] = dict(slope=sl, lo=l, hi=h, n=len(use))
        print(f"   Theil-Sen slope of xfloor {stat} on dose: {sl:+.3f} [{l:+.3f}, {h:+.3f}] "
              f"per 1.0x   (n = {len(use)} route-arms)"
              + ("   ⇒ 0 is INSIDE ⇒ no dose response" if l <= 0 <= h else "   ⇒ excludes 0"))

    addendum()
    Path(a.json).write_text(json.dumps(RES, indent=1, default=str))
    print(f"\nwrote {a.json}")




# =================================================================================================
# 5. ADDENDUM -- separating EXCITATION from DOSE (added after the first pass; see the report)
# =================================================================================================
def addendum():
    """The 1.000x pool mixes ALC-commanded and driver-commanded maneuvers, and those are not the
    same excitation (HANDOFF-2026-08-03 §7's own caveat). Two contrasts settle which variable the
    transient tracks:
      A. WITHIN dose 1.000x: ENGAGED (ALC) vs MANUAL. Dose is held EXACTLY fixed -- both are the
         stock rate lane, byte-identical -- so any difference is excitation, not firmware.
      B. The dose contrasts recomputed with the base restricted to ENGAGED routes only, so
         excitation is held fixed and only dose varies.
    """
    rng = np.random.default_rng(20260805)
    G.EPKEY = "blk"
    st = records(False)
    pools = {}
    for t, (cache, pfx, img, _) in ROUTES.items():
        for lab, eng in (("ENGAGED", True), ("manual", False)):
            arr = [r for r in st[t] if bool(r["eng"]) == eng and r["v"] >= HWY]
            if len(arr) < 8:
                continue
            floor = float(np.median(G.col(arr, "e_26-30")))
            for r in arr:
                r["xfloor"] = r["e_26-30"] / floor
            pools[(t, lab)] = dict(recs=arr, dose=float(dose_at(img, 25.0, 19.0, eng)), eng=eng)

    def mv(sel):
        return [r for k, p in pools.items() if sel(k, p)
                for r in p["recs"] if r["ratepk"] >= MV_HI]

    hdr("5A. WITHIN dose = 1.000x EXACTLY: ALC-commanded vs DRIVER-commanded maneuvers")
    print("   Both arms run the STOCK rate lane -- byte-identical firmware behaviour -- so this")
    print("   contrast holds DOSE fixed and varies only who commanded the maneuver.\n")
    alc = mv(lambda k, p: p["dose"] < 1.2 and p["eng"])
    man = mv(lambda k, p: p["dose"] < 1.2 and not p["eng"])
    print(f"   ALC    (r2b/V58 + r2c/V59 + 4f/V69): n={len(alc):3d}  blocks={len(G.episodes(alc)):3d}"
          f"  xfloor med {np.median(G.col(alc, 'xfloor')):5.2f}  "
          f"p90 {np.percentile(G.col(alc, 'xfloor'), 90):5.2f}")
    print(f"   MANUAL (4c/V68)                    : n={len(man):3d}  blocks={len(G.episodes(man)):3d}"
          f"  xfloor med {np.median(G.col(man, 'xfloor')):5.2f}  "
          f"p90 {np.percentile(G.col(man, 'xfloor'), 90):5.2f}")
    pt, ci = boot_ratio(alc, man, "xfloor", rng)
    nl = split_null(alc + man, "xfloor", rng)
    print(f"\n   ALC / MANUAL  =  {pt:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]   split-half null "
          f"[{nl[0]:.2f}, {nl[1]:.2f}]   "
          f"{'*** CLEARS ITS NULL' if ci[0] > nl[1] else 'inside null'}")

    hdr("5B. THE DOSE CONTRASTS WITH EXCITATION HELD FIXED — engaged (ALC) routes only")
    base = mv(lambda k, p: p["dose"] < 1.2 and p["eng"])
    for nm, sel in (("2.000x (V62/V65)", lambda k, p: 1.8 <= p["dose"] < 2.2 and p["eng"]),
                    ("~2.40x (V67/V68)", lambda k, p: p["dose"] >= 2.2 and p["eng"])):
        arm = mv(sel)
        pt, ci = boot_ratio(arm, base, "xfloor", rng)
        nl = split_null(arm + base, "xfloor", rng)
        print(f"   {nm + ' / 1.000x (ALC only)':38s} {pt:7.3f} [{ci[0]:8.3f}, {ci[1]:8.3f}] "
              f"null [{nl[0]:6.2f}, {nl[1]:6.2f}]  "
              f"{'CLEARS' if ci[0] > nl[1] else 'inside null ⇒ NO dose effect'}")
    print("\n   🛑 Compare against §3: if removing the ONE manual route from the base collapses the")
    print("     ~2.40x contrast, then §3's apparent trend was an EXCITATION contrast wearing a")
    print("     dose label — which is the same class of error as the withdrawn 28 Hz 'mode'.")


if __name__ == "__main__":
    main()
