#!/usr/bin/env python3
"""ROUTE 59 (V72) IN THE NEAR-CENTRE FRAME -- the arm on which the conditional was ATTESTED.

Route 59 is the only route where the operator actually MADE the near-centre observation, so it is
the arm where the effect should be strongest. The corpus work says whether it is structural; this
says whether it is present where it was reported.

★ THE DECOMPOSITION, restated because everything below depends on it. `|angle|` cannot be tested
directly: for a 2.56 s window whose angle never leaves +/-A deg, mean |rate| is bounded by
~0.78*A deg/s, and the measured p95 tracks that bound to within 20%. So `|angle|` and `|rate|` are
the SAME measurement at this window length. The separable pair is
    span = a_max - a_min                    how much the wheel MOVED  (this carries the rate)
    mid  = (a_max + a_min)/2 - c            WHERE on the angle axis   (this carries "near centre")
with `c` the route's own sensor zero from its straight-ahead highway cruise.

ss1  V72 in the span ladder and the |mid| contrast, against the corpus.
ss2  ★ DID THE SPEED CEILING MOVE?  V72 is the first build in the kit with base-assist damping
     below 35.0 km/h (FactorC Y[0],Y[1] 0 -> 430; FactorE Y[0..2] -> 927). Stock and every prior
     build have EXACTLY ZERO base damping below that breakpoint, and grind #1's reported ceiling
     (~25 mph = 40 km/h) sits close to it. If damping sets the ceiling, V72's should have MOVED.
     🛑 Measured with excursion HELD FIXED, because the marginal speed ladder is dominated by the
     fact that you cannot move the wheel 25 deg in 2.5 s at highway speed (span >= 25 deg occurs in
     81.0% of engaged windows at 0-2 m/s and 0.1% at 18+ m/s).
ss3  ★ THE "COMMANDING TORQUE" CONDITIONAL.  The operator says grind #1 needs openpilot engaged AND
     actively commanding. The kit has separated those before (commanding into a dead lockout did
     nothing; commanding AND applying gave 14,750x). Within ENGAGED creep only -- so engagement is
     held constant by construction -- does e_18-22 track the COMMAND?
ss4  The V67/V68 sub-18 Hz inventory that `D3-microratchet` asked for, with its exposure.

Usage: python studies/nearcentre/nearcentre_v72.py [ep|blk] -> writes _scratch/out/_nearcentre_v72.json
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r59_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260805)
NBOOT = 3000
OUT = {"epkey": G.EPKEY}

SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
SPN = ["0-2", "2-8", "8-25", "25-75", "75-200", "200+"]
MDN = ["0-5", "5-15", "15-45", "45-120", "120+"]
MD = [(0.0, 5.0), (5.0, 15.0), (15.0, 45.0), (45.0, 120.0), (120.0, 1e9)]

store = N.records()
ZERO = {}
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    ZERO[b] = c
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["amid"] = abs(0.5 * (r["a_max"] + r["a_min"]) - c)
        r["sb"] = G.binof(r["span"], SP)
        r["mb"] = G.binof(r["amid"], MD)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]
PRIOR = [b for b in N.LADDER if b != "V72/r59"]


def bootratio(A, B, key="e_18-22", nb=NBOOT):
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        eb.setdefault(r[G.EPKEY], []).append(r)
    pa, pb = list(ea.values()), list(eb.values())
    if len(pa) < 2 or len(pb) < 2:
        return (np.nan,) * 3
    d = np.full(nb, np.nan)
    for i in range(nb):
        va = np.concatenate([G.col(pa[j], key) for j in RNG.integers(0, len(pa), len(pa))])
        vb = np.concatenate([G.col(pb[j], key) for j in RNG.integers(0, len(pb), len(pb))])
        va, vb = va[np.isfinite(va)], vb[np.isfinite(vb)]
        if len(va) and len(vb) and np.median(vb) > 0:
            d[i] = np.median(va) / np.median(vb)
    a, b = G.col(A, key), G.col(B, key)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    pt = float(np.median(a) / np.median(b)) if len(a) and len(b) and np.median(b) > 0 else np.nan
    return pt, float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


# ------------------------------------------------------------------ ss1 V72 in the frame ----------
N.hdr("ss1  ★★★ V72 / ROUTE 59 IN THE NEAR-CENTRE FRAME")
print("  (a) THE SPAN LADDER -- the wheel must MOVE. Median e_18-22, engaged creep.\n")
print(f"  {'arm':<12} " + " ".join(f"{n:>15}" for n in SPN) + f"{'peak/floor':>11}")
sl = {}
for k in ["POOLED", "V72/r59"] + [x for x in N.ARMS if x != "V72/r59"]:
    row, cells = [], []
    for j in range(len(SPN)):
        c = [r for r in ARM[k] if r["sb"] == j]
        nb = len({r[G.EPKEY] for r in c})
        v = G.col(c, "e_18-22")
        v = v[np.isfinite(v)]
        thin = len(c) < 8 or nb < 3
        m = float(np.median(v)) if len(v) else np.nan
        row.append(dict(n=len(c), nb=nb, med=m, thin=thin))
        cells.append(f"{'EMPTY':>15}" if not len(v)
                     else (f"{m:>6.0f}~n{len(c):<3}" if thin else f"{m:>7.0f}n{len(c):<3}").rjust(15))
    ok = [d["med"] for d in row if not d["thin"] and np.isfinite(d["med"])]
    pf = max(ok) / min(ok) if len(ok) >= 2 and min(ok) > 0 else np.nan
    sl[k] = dict(bins=row, peak_over_floor=float(pf))
    star = "  <-- ROUTE 59" if k == "V72/r59" else ""
    print(f"  {k:<12} " + " ".join(cells)
          + (f"{pf:>11.2f}" if np.isfinite(pf) else f"{'--':>11}") + star)
OUT["span_ladder"] = sl

print("\n  (b) THE |mid| CONTRAST -- near the sensor zero vs far, WITHIN span 25-200 deg.")
print("      ratio > 1 = MORE grind #1 near centre at matched wheel movement.\n")
print(f"  {'arm':<12} {'nA':>4} {'nB':>4} {'uA':>3} {'uB':>3} {'medA':>8} {'medB':>8} "
      f"{'ratio':>7} {'[95% CI]':>18} {'prom ratio':>11}")
mc = {}
for k in ["POOLED", "V72/r59"] + [x for x in N.ARMS if x != "V72/r59"]:
    rs = [r for r in ARM[k] if r["sb"] in (3, 4)]
    A = [r for r in rs if r["amid"] < 15.0]
    B = [r for r in rs if r["amid"] >= 45.0]
    uA, uB = len({r[G.EPKEY] for r in A}), len({r[G.EPKEY] for r in B})
    if len(A) < 5 or len(B) < 5:
        print(f"  {k:<12} {len(A):>4} {len(B):>4} {uA:>3} {uB:>3}   *** EMPTY / UNDERPOWERED")
        mc[k] = dict(nA=len(A), nB=len(B), uA=uA, uB=uB, underpowered=True)
        continue
    pt, lo, hi = bootratio(A, B)
    pb = G.col(B, "p_18-22")
    pb = pb[np.isfinite(pb)]
    pa = G.col(A, "p_18-22")
    pa = pa[np.isfinite(pa)]
    pr = float(np.median(pa) / np.median(pb)) if len(pb) and np.median(pb) > 0 else np.nan
    mc[k] = dict(nA=len(A), nB=len(B), uA=uA, uB=uB, ratio=pt, lo=lo, hi=hi, promratio=pr,
                 medA=float(np.median(G.col(A, "e_18-22"))),
                 medB=float(np.median(G.col(B, "e_18-22"))))
    star = "  <-- ROUTE 59" if k == "V72/r59" else ""
    print(f"  {k:<12} {len(A):>4} {len(B):>4} {uA:>3} {uB:>3} "
          f"{np.median(G.col(A, 'e_18-22')):>8.0f} {np.median(G.col(B, 'e_18-22')):>8.0f} "
          f"{pt:>7.2f} [{lo:>7.2f},{hi:>8.2f}] {pr:>11.2f}{star}")
OUT["mid_contrast"] = mc

# ------------------------------------------------------------------ ss2 did the ceiling move ------
N.hdr("ss2  ★★★ DID THE SPEED CEILING MOVE ON V72?  (the FactorC / base-damping question)")
print("  V72 is the FIRST build in this kit with non-zero base-assist damping below 35.0 km/h")
print("  (9.72 m/s). Stock and every prior build are EXACTLY zero there. If the base damper sets")
print("  grind #1's speed ceiling, V72's ladder must differ from the prior corpus ACROSS that")
print("  breakpoint. Excursion is held fixed, because the marginal ladder is an exposure artefact.\n")
VE = [0, 3.5, 5.556, 7.5, 9.72, 11.18, 14, 1e9]
VN = ["0-3.5", "3.5-5.6", "5.6-7.5", "7.5-9.7", "9.7-11.2", "11.2-14", "14+"]
ALLENG = {b: [r for r in store[b] if r["eng"] == 1] for b in N.LADDER}
sc = {}
for slab, ss in (("span 8-25", [2]), ("span 25-75", [3]), ("span 8-75", [2, 3])):
    print(f"  --- {slab} deg per 2.56 s")
    print(f"      {'arm':<14} " + " ".join(f"{n:>13}" for n in VN))
    for k, names in (("V72/r59", ["V72/r59"]), ("prior corpus", PRIOR),
                     ("V67+V68", ["V67/r47", "V68/r4e"]), ("stock pool", N.ARMS["stock pool"])):
        rs = [r for n in names for r in ALLENG[n] if r["sb"] in ss]
        cells, row = [], []
        for i in range(len(VN)):
            c = [r for r in rs if VE[i] <= r["v"] < VE[i + 1]]
            nb = len({r[G.EPKEY] for r in c})
            v = G.col(c, "e_18-22")
            v = v[np.isfinite(v)]
            m = float(np.median(v)) if len(v) else np.nan
            row.append(dict(n=len(c), nb=nb, med=m))
            cells.append(f"{'EMPTY':>13}" if not len(v)
                         else (f"{m:>6.0f}~n{len(c):<3}" if len(c) < 8 or nb < 3
                               else f"{m:>7.0f}n{len(c):<3}").rjust(13))
        sc[f"{slab}|{k}"] = row
        print(f"      {k:<14} " + " ".join(cells))
    print()
OUT["ceiling"] = sc

print("  --- THE BREAKPOINT TEST: (below 9.72 m/s) / (above 9.72 m/s), span 8-75, "
      "episode-bootstrap")
print(f"      {'arm':<14} {'n below':>8} {'n above':>8} {'med below':>10} {'med above':>10} "
      f"{'ratio':>7} {'[95% CI]':>18}")
bp = {}
for k, names in (("V72/r59", ["V72/r59"]), ("prior corpus", PRIOR),
                 ("V67+V68", ["V67/r47", "V68/r4e"]), ("stock pool", N.ARMS["stock pool"]),
                 ("V62+V65", N.ARMS["V62+V65"])):
    rs = [r for n in names for r in ALLENG[n] if r["sb"] in (2, 3)]
    A = [r for r in rs if r["v"] < 9.72]
    B = [r for r in rs if r["v"] >= 9.72]
    if len(A) < 5 or len(B) < 5:
        print(f"      {k:<14} {len(A):>8} {len(B):>8}   *** EMPTY / UNDERPOWERED")
        bp[k] = dict(nA=len(A), nB=len(B), underpowered=True)
        continue
    pt, lo, hi = bootratio(A, B)
    bp[k] = dict(nA=len(A), nB=len(B), ratio=pt, lo=lo, hi=hi,
                 medA=float(np.median(G.col(A, "e_18-22"))),
                 medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"      {k:<14} {len(A):>8} {len(B):>8} {np.median(G.col(A, 'e_18-22')):>10.0f} "
          f"{np.median(G.col(B, 'e_18-22')):>10.0f} {pt:>7.2f} [{lo:>7.2f},{hi:>8.2f}]")
OUT["breakpoint"] = bp

# ------------------------------------------------------------------ ss3 commanding torque ---------
N.hdr("ss3  ★★★ THE 'COMMANDING STEERING TORQUE' CONDITIONAL -- inside ENGAGED creep only")
print("  Engagement is held CONSTANT by construction here, so anything this finds is about the")
print("  COMMAND, not about latActive. Channels, all per-window over the same 2.56 s slice:")
print("    e4   = mean |0x0E4 STEER_TORQUE| -- what the EPS was actually asked for, off the wire")
print("    req  = mean |carControl.actuators.torque| -- openpilot's own request, pre-wire")
print("    e4max = max |0x0E4| in the window ; dreq = mean |d(req)/dt| -- the command's SLEW\n")
CMD = [("e4", "|0x0E4| mean"), ("e4max", "|0x0E4| max"), ("req", "|cc_req| mean"),
       ("dreq", "|d cc_req/dt|")]
print(f"  {'arm':<12} {'channel':<16} {'quartile medians of e_18-22 (Q1 low cmd -> Q4 high)':<52}"
      f"{'Q4/Q1':>8} {'[95% CI]':>18}")
cmdout = {}
for k in ["POOLED", "V72/r59", "V67+V68", "stock pool", "V62+V65"]:
    rs = [r for r in ARM[k] if np.isfinite(r.get("e4", np.nan))]
    if len(rs) < 20:
        print(f"  {k:<12} *** UNDERPOWERED n={len(rs)}")
        continue
    for ch, lab in CMD:
        v = G.col(rs, ch)
        ok = [r for r, x in zip(rs, v) if np.isfinite(x)]
        v = v[np.isfinite(v)]
        if len(ok) < 20:
            continue
        q = np.percentile(v, [25, 50, 75])
        grp = [[r for r in ok if r[ch] < q[0]],
               [r for r in ok if q[0] <= r[ch] < q[1]],
               [r for r in ok if q[1] <= r[ch] < q[2]],
               [r for r in ok if r[ch] >= q[2]]]
        meds = [float(np.median(G.col(g, "e_18-22"))) if g else np.nan for g in grp]
        pt, lo, hi = bootratio(grp[3], grp[0])
        cmdout[f"{k}|{ch}"] = dict(meds=meds, ns=[len(g) for g in grp], ratio=pt, lo=lo, hi=hi,
                                   cuts=[float(x) for x in q])
        print(f"  {k:<12} {lab:<16} "
              + "  ".join(f"{m:>7.0f}(n{len(g)})" for m, g in zip(meds, grp)).ljust(52)
              + f"{pt:>8.2f} [{lo:>7.2f},{hi:>8.2f}]")
    print()
OUT["command"] = cmdout

print("  --- COMMAND vs MOVEMENT: does the command add anything once `span` is held fixed?")
print("      Rank-partial (Spearman on ranks, episode-cluster bootstrap, shuffled-pairing null).\n")


def rk(x):
    o = np.argsort(np.argsort(np.asarray(x, float)))
    return (o - o.mean()) / (o.std() + 1e-12)


def partial(rs, metric, pred, ctrl):
    y, x = rk(G.col(rs, metric)), rk(G.col(rs, pred))
    if not ctrl:
        return float(np.mean(y * x))
    Z = np.column_stack([rk(G.col(rs, c)) for c in ctrl] + [np.ones(len(rs))])
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    s = ry.std() * rx.std()
    return float(np.mean(ry * rx) / s) if s > 0 else np.nan


def bp_ci(rs, metric, pred, ctrl, nb=800):
    eps = {}
    for r in rs:
        eps.setdefault(r[G.EPKEY], []).append(r)
    ep = list(eps.values())
    d = np.full(nb, np.nan)
    for i in range(nb):
        s = [r for j in RNG.integers(0, len(ep), len(ep)) for r in ep[j]]
        if len(s) > len(ctrl) + 4:
            d[i] = partial(s, metric, pred, ctrl)
    return (partial(rs, metric, pred, ctrl), float(np.nanpercentile(d, 2.5)),
            float(np.nanpercentile(d, 97.5)))


def shuf(rs, metric, pred, ctrl, nrep=200):
    eps = {}
    for r in rs:
        eps.setdefault(r[G.EPKEY], []).append(r)
    out = []
    for _ in range(nrep):
        s = []
        for e in eps.values():
            v = G.col(e, metric)
            RNG.shuffle(v)
            for r, vv in zip(e, v):
                q = dict(r)
                q[metric] = vv
                s.append(q)
        out.append(partial(s, metric, pred, ctrl))
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))


print(f"  {'arm':<12} {'predictor':<10} {'controls':<22} {'rho':>7} {'[95% CI]':>17} "
      f"{'shuffled null':>18}")
pr = {}
for k in ["POOLED", "V72/r59"]:
    rs = [r for r in ARM[k] if np.isfinite(r.get("e4", np.nan)) and np.isfinite(r["span"])]
    for pred, ctrl, lab in (("e4", [], "none"), ("e4", ["span"], "span"),
                            ("e4", ["span", "v", "amid"], "span, v, |mid|"),
                            ("span", [], "none"), ("span", ["e4"], "|0x0E4|"),
                            ("span", ["e4", "v", "amid"], "|0x0E4|, v, |mid|"),
                            ("amid", ["span", "e4", "v"], "span, |0x0E4|, v")):
        pt, lo, hi = bp_ci(rs, "e_18-22", pred, ctrl)
        nl = shuf(rs, "e_18-22", pred, ctrl)
        pr[f"{k}|{pred}|{lab}"] = dict(rho=pt, lo=lo, hi=hi, null=list(nl), n=len(rs))
        print(f"  {k:<12} {pred:<10} {lab:<22} {pt:>7.3f} [{lo:>7.3f},{hi:>8.3f}] "
              f"[{nl[0]:>7.3f},{nl[1]:>7.3f}]")
    print()
OUT["partials"] = pr

# ------------------------------------------------------------------ ss4 for D3 --------------------
N.hdr("ss4  THE V67/V68 SUB-18 Hz INVENTORY -- for `D3-microratchet`")
print("  6-9 Hz p-p = 2 * e_6-9 (e_6-9 is the p99 of the analytic 6-9 Hz envelope, i.e. the")
print("  amplitude). Two speed cuts: the kit's standard creep (< 20 km/h, includes v == 0) and")
print("  D3's MOVING creep 0.3-4 m/s, so the numbers are directly comparable to theirs.\n")
d3 = {}
for cut, lab in ((lambda r: r["v"] < N.CREEP, "creep < 20 km/h"),
                 (lambda r: 0.3 <= r["v"] <= 4.0, "moving creep 0.3-4 m/s")):
    print(f"  --- {lab}")
    print(f"  {'arm':<12} {'mask':<9} {'n':>5} {'blk':>4} {'6-9 p-p p50':>12} {'p90':>8} "
          f"{'hit >=1200':>11} {'18-22 p-p p50':>14}")
    for k, names in (("V67/r47", ["V67/r47"]), ("V68/r4e", ["V68/r4e"]),
                     ("V67+V68", ["V67/r47", "V68/r4e"]), ("V72/r59", ["V72/r59"]),
                     ("stock pool", N.ARMS["stock pool"]), ("V62+V65", N.ARMS["V62+V65"])):
        for mlab, m in (("engaged", 1), ("manual", 0)):
            rs = [r for n in names for r in store[n] if r["eng"] == m and cut(r)]
            if not rs:
                print(f"  {k:<12} {mlab:<9} {0:>5}   *** EMPTY")
                continue
            pp = 2 * G.col(rs, "e_6-9")
            pp = pp[np.isfinite(pp)]
            p18 = 2 * G.col(rs, "e_18-22")
            p18 = p18[np.isfinite(p18)]
            hit = float(np.mean(pp >= 1200)) if len(pp) else np.nan
            d3[f"{lab}|{k}|{mlab}"] = dict(n=len(rs), pp50=float(np.median(pp)),
                                           pp90=float(np.percentile(pp, 90)), hit=hit,
                                           pp18=float(np.median(p18)))
            print(f"  {k:<12} {mlab:<9} {len(rs):>5} {len({r[G.EPKEY] for r in rs}):>4} "
                  f"{np.median(pp):>12.0f} {np.percentile(pp, 90):>8.0f} "
                  f"{100 * hit:>10.0f}% {np.median(p18):>14.0f}")
    print()
OUT["d3"] = d3

(HERE.parent / "_scratch/out/_nearcentre_v72.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_v72.json'}")
