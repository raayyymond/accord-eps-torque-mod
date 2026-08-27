#!/usr/bin/env python3
r"""V89 flight -- H2/H3 REDONE against a PLACEBO-PAIR NULL, on the order-clean highway stratum,
plus `LeakDose`'s magnitude-vs-rate regression re-run as a third instrument.

🛑 THE METHODOLOGICAL CORRECTION THIS FILE APPLIES.  `LeakDose` measured, over 213 constant-alpha
   route pairs, that the CROSS-BUILD floor of this kit's band contrast has **sd 1.03**, against
   episode-block-bootstrap half-widths of ~0.37 -- block bootstraps understate cross-build
   uncertainty by ~2.8x here.  Every V89-vs-V88 number therefore gets a placebo-pair null beside it.

   THE PLACEBO CONSTRUCTED HERE IS THE ONE THIS FLIGHT CAN BUILD, AND IT IS THE RIGHT SHAPE:
   routes 75 and 76 are **two different drives on the SAME build**.  Random disjoint segment
   partitions of {r75 segs} U {r76 segs} are therefore genuine constant-build "cross-drive" pairs,
   scored with the IDENTICAL estimator, and their spread IS the floor that a V89-vs-V88 contrast
   must clear.  ⊕ The single cleanest placebo -- whole r75 vs whole r76 -- is reported separately.

🛑 THE WHEEL-ORDER VETO IS ASYMMETRIC (`LeakDose` defect #2): orders 1-6 never reach 32-38 Hz at
   parking-lot speed while orders 3-4 hit 6-9 Hz constantly, so the band and its own control are
   screened differently.  The fix available on THESE routes is exposure: above ~67.7 km/h
   (18.8 m/s) NO order 1-6 can reach 6-9 Hz at all -- order 1 is already at 9.0 Hz -- so that
   stratum is INTRINSICALLY order-clean and needs no veto on either band.
   Order 1 = v/2.0805 Hz:  13.9 m/s -> 6.68 Hz (IN BAND) · 18.8 -> 9.03 · 22.2 -> 10.68 · 30 -> 14.4
   ⇒ "engaged >= 50 km/h" is NOT clean.  The clean cut is >= 18.8 m/s, and it is reported as such.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import pickle
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))

import _grind2_lib as G          # noqa: E402
import _r31_common as C31        # noqa: E402
import _r4f_lib as R4F           # noqa: E402
import compare_v75_v76_v80_grind as M   # noqa: E402  -- installs BANDS_EXT
from v89_e2_h2h3 import BUILDS, ARMS, eng, order_hit, nblk  # noqa: E402
from v89_e3_contrast import strat_multi, boot_contrast      # noqa: E402
from v89_e4_inertia import NFFT, HOP, fs_of, ols            # noqa: E402

R4F.install_fs()
RNG = np.random.default_rng(89_8888)
PKL = ROOT / "_scratch/cache/r75" / "records_v89_score.pkl"
OUTJ = ROOT / "_scratch/cache/r75" / "v89_e8_placebo.json"
V_CLEAN = 18.8       # m/s == 67.7 km/h; above this NO wheel order 1-6 reaches 6-9 Hz
SUBJ, CTRL = "e_6-9", "e_32-38"
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + f"\n{s}\n" + "=" * 112, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def pct_of(x, dist):
    d = np.asarray(dist, float)
    d = d[np.isfinite(d)]
    return float(np.mean(d <= x) * 100) if len(d) else np.nan


# =================================================================================================
def placebo_null(pool, nrep=400, tag=""):
    """Random disjoint SEGMENT partitions of a constant-build pool -> the estimator's own
    cross-drive floor.  Segments, not episodes: a drive's manoeuvre mix is a segment-level
    property, and that heterogeneity is exactly what a block bootstrap misses."""
    segs = sorted({(r["build"], r["seg"]) for r in pool})
    by = {}
    for r in pool:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    con, rat = [], []
    for _ in range(nrep):
        p = RNG.permutation(len(segs))
        h = len(segs) // 2
        A = [r for i in p[:h] for r in by[segs[i]]]
        B = [r for i in p[h:] for r in by[segs[i]]]
        v, nc = strat_multi(G.episodes(A), G.episodes(B), [SUBJ, CTRL])
        if nc and np.isfinite(v[SUBJ]) and np.isfinite(v[CTRL]):
            con.append(v[SUBJ] - v[CTRL])
            rat.append(v[SUBJ])
    con, rat = np.array(con), np.array(rat)
    if not len(con):
        print(f"    {tag}: no usable placebo partition")
        return None
    print(f"    {tag}: {len(con)}/{nrep} usable partitions of {len(segs)} segments")
    print(f"      CONTRAST (6-9 minus 32-38)  sd(log) {con.std():.3f}   "
          f"95 % [{np.exp(np.percentile(con,2.5)):.3f}, {np.exp(np.percentile(con,97.5)):.3f}]   "
          f"median {np.exp(np.median(con)):.3f}")
    print(f"      RAW e_6-9 ratio             sd(log) {rat.std():.3f}   "
          f"95 % [{np.exp(np.percentile(rat,2.5)):.3f}, {np.exp(np.percentile(rat,97.5)):.3f}]")
    return dict(contrast=con, ratio=rat,
                sd_contrast=float(con.std()), sd_ratio=float(rat.std()),
                lo=float(np.exp(np.percentile(con, 2.5))),
                hi=float(np.exp(np.percentile(con, 97.5))))


def measured(A, B, tag):
    pt, D, nc, na, nb = boot_contrast(A, B, [SUBJ, CTRL], nboot=1500)
    if not (np.isfinite(pt[SUBJ]) and np.isfinite(pt[CTRL])):
        print(f"    {tag}: no common cell -- NOT SCOREABLE")
        return None
    d = D[SUBJ] - D[CTRL]
    r = dict(ratio=float(np.exp(pt[SUBJ])),
             ratio_ci=[float(np.exp(np.nanpercentile(D[SUBJ], 2.5))),
                       float(np.exp(np.nanpercentile(D[SUBJ], 97.5)))],
             contrast=float(np.exp(pt[SUBJ] - pt[CTRL])),
             contrast_ci=[float(np.exp(np.nanpercentile(d, 2.5))),
                          float(np.exp(np.nanpercentile(d, 97.5)))],
             log_contrast=float(pt[SUBJ] - pt[CTRL]), cells=nc, epA=na, epB=nb)
    print(f"    {tag}: e_6-9 {r['ratio']:.3f} [{r['ratio_ci'][0]:.3f},{r['ratio_ci'][1]:.3f}]   "
          f"CONTRAST {r['contrast']:.3f} [{r['contrast_ci'][0]:.3f},{r['contrast_ci'][1]:.3f}]   "
          f"cells {nc}  ep {na}/{nb}")
    return r


def part_a(R):
    hdr("A  THE PLACEBO-PAIR NULL -- the floor a V89-vs-V88 contrast has to clear\n"
        "   Constructed from routes 75 and 76: TWO DIFFERENT DRIVES ON THE SAME BUILD.")
    E = {b: eng(R[b], b) for b in ARMS}
    V89POOL = E["V89/r75"] + E["V89/r76"]
    OUT["placebo"] = {}
    sub("CONSTANT-BUILD placebo partitions (the null), and route 73's own for comparison")
    pA = placebo_null(V89POOL, tag="V89 pool (r75+r76), 29 segments")
    pB = placebo_null(E["V88/r73"], tag="V88 r73 alone, 11 segments")
    for k, p in (("v89_pool", pA), ("v88_r73", pB)):
        if p:
            OUT["placebo"][k] = {x: p[x] for x in ("sd_contrast", "sd_ratio", "lo", "hi")}

    sub("★ THE SINGLE CLEANEST PLACEBO -- whole r75 vs whole r76, same build, different drives")
    pp = measured(E["V89/r75"], E["V89/r76"], "r75 / r76 (SAME BUILD)")
    OUT["placebo"]["r75_vs_r76"] = pp

    sub("THE MEASUREMENT, against that floor")
    m = measured(V89POOL, E["V88/r73"], "V89 pooled / V88 r73")
    OUT["placebo"]["measured_all"] = m
    if m and pA:
        print(f"\n      measured log-contrast {m['log_contrast']:+.3f}  vs placebo sd "
              f"{pA['sd_contrast']:.3f}  =>  {abs(m['log_contrast'])/pA['sd_contrast']:.2f} sigma, "
              f"percentile {pct_of(m['log_contrast'], pA['contrast']):.1f}")
        print(f"      placebo 95 % band on the contrast: "
              f"[{pA['lo']:.3f}, {pA['hi']:.3f}]   measured {m['contrast']:.3f}   "
              f"{'OUTSIDE' if not (pA['lo'] <= m['contrast'] <= pA['hi']) else 'INSIDE — NOT RESOLVABLE'}")
        OUT["placebo"]["sigma"] = float(abs(m["log_contrast"]) / pA["sd_contrast"])
        OUT["placebo"]["percentile"] = pct_of(m["log_contrast"], pA["contrast"])


# =================================================================================================
def part_b(R):
    hdr(f"B  THE INTRINSICALLY ORDER-CLEAN STRATUM -- v >= {V_CLEAN} m/s ({V_CLEAN*3.6:.1f} km/h),\n"
        "   where wheel order 1 has already climbed above 9 Hz so NO order 1-6 can reach 6-9 Hz.\n"
        "   No veto is applied on EITHER band, which removes the asymmetric-screening defect.")
    E = {b: eng(R[b], b) for b in ARMS}
    H = {b: [r for r in E[b] if r["v"] >= V_CLEAN] for b in ARMS}
    Cr = {b: [r for r in E[b] if r["v"] < 2.78] for b in ARMS}
    OUT["clean"] = {}
    for b in ARMS:
        n = len(H[b])
        hit = sum(order_hit(r["f_6-9"], r["v"]) for r in H[b])
        print(f"    {b:10s} highway n={n:4d} blk={nblk(H[b]):3d}  v med "
              f"{np.median([r['v'] for r in H[b]]) if n else float('nan'):5.1f} m/s   "
              f"order-veto would drop {hit}/{n}  ⇒ {'CLEAN' if hit == 0 else 'NOT clean'}    "
              f"| creep <10 km/h n={len(Cr[b])} blk={nblk(Cr[b])}")
        OUT["clean"][f"census/{b}"] = dict(n_highway=n, order_hits=hit, n_creep=len(Cr[b]))

    sub("placebo floor ON THIS STRATUM (same-build partitions, highway windows only)")
    pH = placebo_null(H["V89/r75"] + H["V89/r76"], nrep=300, tag="V89 pool, highway")
    if pH:
        OUT["clean"]["placebo"] = {x: pH[x] for x in ("sd_contrast", "sd_ratio", "lo", "hi")}

    sub("the measurement on the order-clean highway stratum")
    mh = measured(H["V89/r75"] + H["V89/r76"], H["V88/r73"], "V89 pooled / V88, v>=18.8 m/s")
    OUT["clean"]["measured"] = mh
    if mh and pH:
        print(f"      => {abs(mh['log_contrast'])/pH['sd_contrast']:.2f} sigma of the placebo floor,"
              f" percentile {pct_of(mh['log_contrast'], pH['contrast']):.1f}")

    sub("and the CREEP stratum, stated for what it can and cannot support")
    mc = measured(Cr["V89/r75"] + Cr["V89/r76"], Cr["V88/r73"], "V89 pooled / V88, v<2.78 m/s")
    OUT["clean"]["creep"] = mc
    print(f"      creep exposure: V88 {len(Cr['V88/r73'])} windows / {nblk(Cr['V88/r73'])} blocks,")
    print(f"      V89 {len(Cr['V89/r75'])+len(Cr['V89/r76'])} / "
          f"{nblk(Cr['V89/r75']+Cr['V89/r76'])}.  The order veto removes 10/36 of V88's creep")
    print("      windows and the band's own control is NEVER vetoed at this speed "
          "(order 1 < 2.51 Hz),")
    print("      so the creep arm carries the asymmetric screening and cannot settle a 6-9 Hz claim.")


# =================================================================================================
def part_c():
    hdr("C  `LeakDose`'s MAGNITUDE-vs-RATE REGRESSION, RE-RUN ON 75/76 AS A THIRD INSTRUMENT\n"
        "   Their result on two other routes: command magnitude +1.074 [+0.812, +1.445] with a\n"
        "   +0.950 band contrast over 32-38 Hz; wheel rate only +0.100 [+0.021, +0.220].")
    W = []
    for name, (cache, pfx, segs) in {k: (BUILDS[k]["cache"], BUILDS[k]["pfx"], BUILDS[k]["segs"])
                                     for k in ARMS}.items():
        for s in segs:
            if not (cache / f"{pfx}{s}.npz").exists():
                continue
            d = C31.load(s, cache, pfx)
            fs = fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            e4 = np.asarray(d["e4tq"], float)
            tq = np.asarray(d["tq"], float)
            taper = np.hanning(NFFT) + 1e-3
            cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
            for a, b in C31.runs_of(lat, d["t"], NFFT):
                nwin = 0
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(a + i, a + i + NFFT)
                    W.append(dict(build=name, blk=(name, s, a, nwin // 8),
                                  e69=G.win_env(tq[sl], fs, 6.0, 9.0, taper, cw),
                                  e3238=G.win_env(tq[sl], fs, 32.0, 38.0, taper, cw),
                                  cmd=float(np.mean(np.abs(e4[sl]))),
                                  rate=float(np.mean(np.abs(d["rate_f"][sl]))),
                                  v=float(np.mean(np.abs(d["cs_v"][sl])))))
                    nwin += 1
    W = [r for r in W if all(np.isfinite(r[k]) and r[k] > 0
                             for k in ("e69", "e3238", "cmd", "rate", "v"))]
    print(f"    {len(W)} engaged windows, all three routes")
    print(f"    command range: |0x0E4| p5 {np.percentile([r['cmd'] for r in W],5):.0f} .. p95 "
          f"{np.percentile([r['cmd'] for r in W],95):.0f} ct  "
          f"({np.percentile([r['cmd'] for r in W],95)/max(np.percentile([r['cmd'] for r in W],5),1):.1f}x)")
    lc = np.log([r["cmd"] for r in W])
    lr = np.log([r["rate"] for r in W])
    lv = np.log([np.maximum(r["v"], 0.05) for r in W])
    dum = [np.array([1.0 if r["build"] == n else 0.0 for r in W]) for n in ARMS]
    y69 = np.log([r["e69"] for r in W])
    yc = np.log([r["e3238"] for r in W])
    blks = np.array([str(r["blk"]) for r in W])
    ub = np.unique(blks)
    idxof = {b: np.where(blks == b)[0] for b in ub}

    for tag, cols, nm in ((f"LeakDose spec: log|cmd| + log|rate| + route FE", [lc, lr],
                           ["log|cmd|", "log|rate|"]),
                          (f"+ log v (speed is the kit's standing confounder)", [lc, lr, lv],
                           ["log|cmd|", "log|rate|", "log v"])):
        sub(tag)
        X = np.column_stack(dum + cols)
        k0 = len(dum)
        b69, bc = ols(y69, X)[k0:], ols(yc, X)[k0:]
        nb = 3000
        D = np.empty((nb, len(cols), 2))
        for i in range(nb):
            pick = np.concatenate([idxof[ub[j]] for j in RNG.integers(0, len(ub), len(ub))])
            Xp = X[pick]
            D[i, :, 0] = ols(y69[pick], Xp)[k0:]
            D[i, :, 1] = ols(yc[pick], Xp)[k0:]
        print(f"      {'term':12s} {'6-9 Hz':>24s} {'32-38 control':>24s} "
              f"{'BAND CONTRAST':>24s}  excl 0?")
        for j, n_ in enumerate(nm):
            la, ha = np.percentile(D[:, j, 0], [2.5, 97.5])
            lb, hb = np.percentile(D[:, j, 1], [2.5, 97.5])
            d = D[:, j, 0] - D[:, j, 1]
            lo, hi = np.percentile(d, [2.5, 97.5])
            print(f"      {n_:12s} {b69[j]:+8.3f} [{la:+6.3f},{ha:+6.3f}] "
                  f"{bc[j]:+8.3f} [{lb:+6.3f},{hb:+6.3f}] "
                  f"{b69[j]-bc[j]:+8.3f} [{lo:+6.3f},{hi:+6.3f}]  "
                  f"{'YES' if lo > 0 or hi < 0 else 'no'}")
            OUT.setdefault("dose", {})[f"{tag}/{n_}"] = dict(
                b69=float(b69[j]), b69_ci=[float(la), float(ha)],
                bctl=float(bc[j]), bctl_ci=[float(lb), float(hb)],
                contrast=float(b69[j] - bc[j]), contrast_ci=[float(lo), float(hi)])

    sub("🛑 the same fit RESTRICTED to the order-clean highway stratum (v >= 18.8 m/s)")
    Wh = [r for r in W if r["v"] >= V_CLEAN]
    print(f"      {len(Wh)} windows")
    if len(Wh) > 100:
        lch = np.log([r["cmd"] for r in Wh])
        lrh = np.log([r["rate"] for r in Wh])
        dh = [np.array([1.0 if r["build"] == n else 0.0 for r in Wh]) for n in ARMS]
        Xh = np.column_stack(dh + [lch, lrh])
        k0 = len(dh)
        y1 = np.log([r["e69"] for r in Wh])
        y2 = np.log([r["e3238"] for r in Wh])
        bl = np.array([str(r["blk"]) for r in Wh])
        u2 = np.unique(bl)
        ix = {b: np.where(bl == b)[0] for b in u2}
        b1, b2 = ols(y1, Xh)[k0:], ols(y2, Xh)[k0:]
        D = np.empty((2000, 2, 2))
        for i in range(2000):
            pick = np.concatenate([ix[u2[j]] for j in RNG.integers(0, len(u2), len(u2))])
            D[i, :, 0] = ols(y1[pick], Xh[pick])[k0:]
            D[i, :, 1] = ols(y2[pick], Xh[pick])[k0:]
        for j, n_ in enumerate(["log|cmd|", "log|rate|"]):
            d = D[:, j, 0] - D[:, j, 1]
            lo, hi = np.percentile(d, [2.5, 97.5])
            print(f"      {n_:12s} 6-9 {b1[j]:+.3f}   ctl {b2[j]:+.3f}   "
                  f"CONTRAST {b1[j]-b2[j]:+.3f} [{lo:+.3f},{hi:+.3f}]  "
                  f"{'YES' if lo > 0 or hi < 0 else 'no'}")
            OUT.setdefault("dose_highway", {})[n_] = dict(
                b69=float(b1[j]), bctl=float(b2[j]), contrast=float(b1[j] - b2[j]),
                contrast_ci=[float(lo), float(hi)])


if __name__ == "__main__":
    R = {k: v for k, v in pickle.load(open(PKL, "rb")).items() if not k.startswith("__")}
    part_a(R)
    part_b(R)
    part_c()
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
