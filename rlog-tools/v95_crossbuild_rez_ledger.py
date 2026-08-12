#!/usr/bin/env python3
r"""v95_crossbuild_rez_ledger.py -- the cross-build Re(Z) ledger, its detection floor, and the two
candidate-cell searches that came out of it.

Re(Z) had only ever been computed on routes 77/78/79.  Every cache back to r5e carries the two
channels it needs (`tq` and `rate_f`, fields of the SAME 0x18F frame), so the whole post-V74 flight
history can be re-scored on the metric -- a free retrospective dose-response across ~15 builds, and
the metric's own PLACEBO FLOOR.

🛑 EVERY ROW IS SPEED- AND RATE-MATCHED to a fixed window.  A route that cannot fill it is reported
   NOT SCOREABLE rather than compared at its own speed.  A moving speed distribution manufactures a
   build effect (`accord-averaged-spectrum-needs-matched-speed-distributions`).

WHAT IT ESTABLISHED, 2026-08-12
  * FIRST ON-CAR ANCHORING OF THE METRIC.  At 12-16 / 18-22 Hz the ledger ranks V80 (route 66) worst
    in the whole set (-8883 / -3581) against V83a best (-2753 / -427) -- 3.2x and 8.4x against a
    same-build floor of 195 / 156.  V80 is the build the operator called the worst grinding he has
    ever felt.  The metric and his lived report agree, independently.
  * THE FLOOR.  Tightly matched (10-20 m/s, |rate| 0.3-3.0 deg/s) the last four drives read
    -3288 / -3286 / -3280 / -3227 at 6-9 Hz -- four drives, three builds, spread 61 counts.  The one
    same-build replicate with thin exposure (V89 r75, 8 episodes) sits 645 away.
    => floor ~60 counts at >= 12 episodes in the matched cell; use 150 conservative.
    => 6-9 Hz has S/N ~ 2.5 across the whole 12-build range; 18-22 Hz has ~75.  18-22 is by far the
       better-conditioned endpoint and 6-9 Hz needs the exposure requirement enforced.
  * THE CELL SEARCH IS A NULL AT 6-9 Hz.  Of the 41 calibration halfwords that vary across the 12
    flown builds, ZERO give a clean two-group separation at 6-9 Hz.  Three do at 18-22 Hz
    (0xD780E / 0xD7810 / 0xD7818, one LERP record, mutually confounded) at p_exact 0.0025-0.0040
    against a Bonferroni bar of 1.2e-3 -- SUGGESTIVE, NOT SIGNIFICANT.
  * LEVER B IS CLEARED AT 6-9 Hz.  The ledger steps at the V84 boundary, where 0xC6446 (512->5244,
    Lever B armed) and 0xD77DA (566->0, mode-26 damper knot to Honda) flipped TOGETHER and no
    post-V74 build separates them.  Pre-V74 builds do: V67/V68/V71C carry Lever B armed with
    0xD77DA at stock 0.  Scored, V71C/ON -3169 [-3793,-2946] sits in the middle of the OFF arms
    (V69 -3239, V70 -3706, V71B -2916, V73 -3028).  ⇒ V88's grinding fix does NOT have to be traded
    away to chase micro-ratcheting.

Usage:  python v95_crossbuild_rez_ledger.py
"""
import glob
import math
import re
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from v95_rez_lib import (BANDS, BUILD, CACHES, DEG2RAD, FS, NEED, base, epwins,  # noqa: E402
                         hdr, load, transfer)

RNG = np.random.default_rng(950818)
IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
KEY = ("4-6", "6-9", "9-12", "12-16", "18-22", "26-31", "32-38")
ORDER = ["r5e", "r61", "r65", "r66", "r67x", "r68x", "r6d", "r6e", "r6f", "r70", "r71", "r73",
         "r75", "r76", "r77", "r78", "r79", "r7d"]
# flown build -> plain image.  Read from the IMAGES, never from a build script's prose.
FLOWN = [
    ("V74", "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
    ("V75", "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
    ("V76", "_v76_v38base_relu_damper_plain_image.bin"),
    ("V80", "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin"),
    ("V81", "_v81_C407E.511-FRICTION.STOCK_plain_image.bin"),
    ("V83a", "_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin"),
    ("V84", "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin"),
    ("V85", "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin"),
    ("V88", "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256_plain_image.bin"),
    ("V89", "_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin"),
    ("V90", "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin"),
    ("V92", "_v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4_plain_image.bin"),
]
# 🛑 EXPLICIT, because inverting BUILD silently drops rows: "V76" != BUILD["r65"] == "V76-V38base",
# and V89 flew TWICE (r75, r76) so a dict inversion keeps only one of them.  Both mistakes cut the
# cell search from 12 builds to 10 and turned its 6-9 Hz NULL into 5 spurious "perfect" splits.
IMAGE_ROUTE = {"V74": "r61", "V75": "r5e", "V76": "r65", "V80": "r66", "V81": "r67x",
               "V83a": "r68x", "V84": "r6d", "V85": "r6e", "V88": "r73", "V89": "r75",
               "V90": "r77", "V92": "r79"}
CAL = [(0xC4000, 0xC5000), (0xC6000, 0xC7000), (0xC9000, 0xCC000), (0xD6000, 0xD8000)]
SKIP = [(0xC4B34, 0xC4C00)]          # the cave; CRC trailers are skipped by the 0xFF0 rule below
LEVERB = {"_v69": "OFF", "_v70": "OFF", "_v71b": "OFF", "_v71c": "ON", "_v72": "OFF", "_v73": "OFF"}
PREV74 = {"r4f": ("V69", "OFF"), "r50": ("V70", "OFF"), "r54": ("V71B", "OFF"),
          "r58": ("V71C", "ON"), "r5a": ("V73", "OFF"), "r5d": ("V74", "--")}


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def cal_offsets():
    for lo, hi in CAL:
        for off in range(lo, hi, 2):
            if any(s <= off < e for s, e in SKIP) or (off & 0xFFF) >= 0xFF0:
                continue
            yield off


def score_route(D, vlo, vhi, rlo, rhi, nboot=300):
    """D is a dict of concatenated channels.  Returns (result, windows) or ('few', n)."""
    W = epwins((D["cc_lat"] > 0.5) & (D["cs_press"] <= 0.5) & (np.abs(D["cs_v"]) > 0.5), D["t"],
               (D["rate_f"] * DEG2RAD, D["tq"], np.abs(D["cs_v"]), np.abs(D["rate_f"])))
    W = [w for w in W
         if vlo <= float(np.mean(np.abs(w[1][2]))) < vhi and rlo <= float(np.median(w[1][3])) < rhi]
    if len(W) < 10:
        return "few", len(W)
    return transfer(W, FS, BANDS, rng=RNG, nboot=nboot), W


def whole(route):
    z = load(route)
    if not NEED <= set(z.files):
        return None
    return {k: np.asarray(z[k], float) for k in NEED}


def segs(d, stem):
    """Concatenate a per-segment cache (the pre-r61 schema).  Ignores _rpm/_imu/_snd sidecars."""
    fs = [f for f in glob.glob(f"{d}/{stem}*.npz") if re.fullmatch(rf"{stem}\d+", Path(f).stem)]
    if not fs:
        return None
    fs.sort(key=lambda p: int(Path(p).stem[len(stem):]))
    out = {}
    for f in fs:
        z = np.load(f, allow_pickle=True)
        if not NEED <= set(z.files):
            return None
        for k in NEED:
            out.setdefault(k, []).append(np.asarray(z[k], float))
    return {k: np.concatenate(v) for k, v in out.items()}


def ledger(vlo, vhi, rlo, rhi, tag):
    hdr(f"CROSS-BUILD Re(Z) LEDGER -- engaged, hands-off, matched to {tag}")
    print(f"  {'route':6s} {'build':13s} {'nwin':>5s} {'nep':>4s} {'v50':>5s} {'r50':>5s} | " +
          "  ".join(f"{k:>16s}" for k in KEY))
    vals = {}
    for r in ORDER:
        if r not in CACHES:
            continue
        D = whole(r)
        if D is None:
            continue
        out = score_route(D, vlo, vhi, rlo, rhi)
        if out[0] == "few":
            print(f"  {r:6s} {BUILD.get(r,'?'):13s} {out[1]:5d}   -- NOT SCOREABLE")
            continue
        res, W = out
        vals[r] = res
        print(f"  {r:6s} {BUILD.get(r,'?'):13s} {len(W):5d} {len({w[0] for w in W}):4d} "
              f"{np.median([np.mean(np.abs(w[1][2])) for w in W]):5.1f} "
              f"{np.median([np.median(w[1][3]) for w in W]):5.2f} | " +
              "  ".join(f"{res[k]['re']:+7.0f}{'' if res[k]['trust'] else '?'}"
                        f"({res[k]['coh2']:.2f})" for k in KEY))
    return vals


def floor_panel():
    hdr("THE DETECTION FLOOR -- tightly matched 10-20 m/s, |rate| 0.3-3.0 deg/s")
    print("  Same-build replicates and the three calibration-identical drives.  This is the number a")
    print("  V95 pass/fail must clear, NOT the band-power placebo floors (1.37x etc.).")
    got = {}
    for r in ("r75", "r76", "r77", "r78", "r79"):
        if r not in CACHES:
            continue
        D = whole(r)
        out = score_route(D, 10, 20, 0.3, 3.0, nboot=400)
        if out[0] == "few":
            continue
        res, W = out
        got[r] = res
        print(f"  {r} {BUILD[r]:5s} n={len(W):4d}/{len({w[0] for w in W}):3d}ep | " +
              "  ".join(f"{k} {res[k]['re']:+6.0f}"
                        f"[{res[k].get('re_lo',float('nan')):+6.0f},"
                        f"{res[k].get('re_hi',float('nan')):+6.0f}]"
                        for k in ("6-9", "12-16", "18-22")))
    if {"r75", "r76"} <= set(got):
        print("\n  SAME-BUILD (V89) REPLICATE DIFFERENCE -- the honest floor at thin exposure:")
        for k in KEY:
            print(f"    {k:7s} r75 {got['r75'][k]['re']:+7.0f}  r76 {got['r76'][k]['re']:+7.0f}  "
                  f"diff {abs(got['r75'][k]['re']-got['r76'][k]['re']):7.0f}")


def cell_search(vals):
    hdr("CANDIDATE-CELL SEARCH -- every calibration halfword that varies across the flown builds")
    imgs = {}
    for lbl, f in FLOWN:
        p = IMG / f
        if p.exists():
            imgs[lbl] = p.read_bytes()
        else:
            print(f"  MISSING image for {lbl}: {f}")
    y, dropped = {}, []
    for b in imgs:
        r = IMAGE_ROUTE.get(b)
        if r and r in vals:
            y[b] = vals[r]
        else:
            dropped.append(f"{b}(route {r or '?'} not scoreable)")
    if dropped:
        print(f"  🛑 DROPPED from the search: {', '.join(dropped)} -- the partition below is over"
              f" the REMAINING builds only, and a dropped build can invent a perfect split.")
    ks = [b for b, _ in FLOWN if b in y]
    if len(ks) < 8:
        print(f"  only {len(ks)} builds have both an image and a scoreable row -- skipping")
        return
    varying = [(off, [s16(imgs[b], off) for b in ks]) for off in cal_offsets()]
    varying = [(o, v) for o, v in varying if len(set(v)) > 1]
    n = len(ks)
    print(f"  {len(varying)} halfwords vary across the {n} flown builds with a scoreable row.")
    print(f"  Bonferroni bar for {len(varying)} tests at alpha 0.05 = {0.05/max(len(varying),1):.2e}")
    for band in ("6-9", "12-16", "18-22", "9-12"):
        yy = [y[b][band]["re"] for b in ks]
        hits = []
        for off, v in varying:
            uv = sorted(set(v))
            for k in range(1, len(uv)):
                ia = [i for i, x in enumerate(v) if x < uv[k]]
                ib = [i for i, x in enumerate(v) if x >= uv[k]]
                if len(ia) < 3 or len(ib) < 3:
                    continue
                a, b_ = [yy[i] for i in ia], [yy[i] for i in ib]
                if max(a) < min(b_) or max(b_) < min(a):
                    hits.append((off, uv[k], np.mean(a), np.mean(b_), 2.0 / math.comb(n, len(ia)),
                                 [ks[i] for i in ia], [ks[i] for i in ib]))
                    break
        print(f"\n  band {band}: {len(hits)} of {len(varying)} cells give a PERFECT 2-group split")
        for h in sorted(hits, key=lambda x: x[4]):
            print(f"    0x{h[0]:06X} thr {h[1]:6d}  means {h[2]:+8.0f} / {h[3]:+8.0f}  "
                  f"p_exact {h[4]:.4f}{'  (clears Bonferroni)' if h[4] < 0.05/len(varying) else ''}"
                  f"\n      low: {','.join(h[5])}   high: {','.join(h[6])}")


def leverb():
    hdr("LEVER B, OUT OF THE V84 CONFOUND -- pre-V74 builds separate 0xC6446 from 0xD77DA")
    for k in LEVERB:
        p = IMG / f"{k}_plain_image.bin"
        if not p.exists():
            continue
        b = p.read_bytes()
        print(f"    {k:7s} 0xC6446={s16(b,0xC6446):6d}  gate 0x3AA96=0x{b[0x3AA96]:02x}  "
              f"0xD77DA={s16(b,0xD77DA):4d}   Lever B {LEVERB[k]}")
    print(f"\n  {'route':6s} {'build/LeverB':14s} {'nwin':>5s} {'nep':>4s} {'v50':>5s} {'r50':>5s} | "
          + "  ".join(f"{k:>16s}" for k in KEY))
    for r, (bd, st) in PREV74.items():
        D = segs(str(Path(__file__).resolve().parent.parent / f"_cache_{r}"), r + "s")
        if D is None:
            print(f"  {r:6s} {bd + '/' + st:14s}  -- schema missing")
            continue
        out = score_route(D, 5, 22, 0.0, 13.0)
        if out[0] == "few":
            print(f"  {r:6s} {bd + '/' + st:14s} {out[1]:5d}  -- NOT SCOREABLE")
            continue
        res, W = out
        print(f"  {r:6s} {bd + '/' + st:14s} {len(W):5d} {len({w[0] for w in W}):4d} "
              f"{np.median([np.mean(np.abs(w[1][2])) for w in W]):5.1f} "
              f"{np.median([np.median(w[1][3]) for w in W]):5.2f} | " +
              "  ".join(f"{res[k]['re']:+7.0f}{'' if res[k]['trust'] else '?'}"
                        f"({res[k]['coh2']:.2f})" for k in KEY))
    print("\n  READ: if Lever B were the 6-9 Hz culprit the ON row must be DEEPER than every OFF row.")


if __name__ == "__main__":
    vals = ledger(5, 22, 0.0, 13.0, "5-22 m/s, |rate| < 13 deg/s")
    ledger(5, 22, 1.0, 13.0, "5-22 m/s, MICRO 1-13 deg/s only")
    floor_panel()
    cell_search(vals)
    leverb()
