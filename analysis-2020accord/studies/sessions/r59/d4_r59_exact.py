#!/usr/bin/env python3
"""D4 -- the EXACT tests, and the two ways route 59's grind-#2 zero can be broken.

§1  EXACT CONDITIONAL POISSON TEST, which needs no assumed reference rate. With x1 bursts in t1
    seconds on the audited route and x2 in t2 on the reference, under H0 (equal rates)
    x1 | (x1+x2) ~ Binomial(x1+x2, t1/(t1+t2)). For x1 = 0 the one-sided p is (t2/(t1+t2))^x2.
    🛑 This is STRICTLY more honest than P(0) at a plugged-in rate: it propagates the reference's
    own sampling error, which matters enormously when the reference is V71C's 3 bursts in 6.4 s.

§2  DID THE OPERATOR FLY THE INSTRUCTION? The flight card asked for ~90 s of deliberate ENGAGED
    HARD CORNERING AT CREEP. Census what route 59 actually contains against the same criterion on
    the four reference routes, so "he flew it" / "he did not" is a measurement.

§3  THE HIGHWAY COMPARISON, EXCITATION-MATCHED. §3 of studies/sessions/r59/d4_r59_power.py found route 59's highway
    1-4 Hz driver-input band is 5.6-5.9x the other routes' and OUTSIDE the split-half null, i.e.
    the pre-declared exposure-matching validity check FAILS. Every highway ratio is therefore
    recomputed inside 1-4 Hz strata, which is the kit's own remedy (it collapsed the V69 lane-change
    "dose" contrast 2.849 -> 2.013).

Writes `_scratch/out/_d4_r59_exact.json`.
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
from scipy.stats import binom

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import d4_lib as L  # noqa: E402
import r47_orchestrator_checks as R47  # noqa: E402

R = L.rows()
OUT = {}

# ================================================================ §1 exact conditional test =======
L.hdr("§1  EXACT CONDITIONAL POISSON TEST -- no plugged-in reference rate.\n"
      "    H0: route 59 and the reference produce grind-#2 bursts at the SAME rate per second.")
CELLS = {
    "creep 0.3-4":            lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1],
    "creep & HIGH-RATE":      lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1] and r["rb"] == 2,
    "creep & |ang|>=100":     lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1] and r["ang"] >= 100,
    "HIGH-RATE any speed":    lambda r: r["rb"] == 2,
    "highway >=14 m/s":       lambda r: r["v"] >= L.HWY,
    "ALL":                    lambda r: True,
}
REFS = {"V62/V65 (Kd=2 flat)": L.REF, "V71C r58 (the build before V72)": "V71C r58  both arms GATED"}
ex = {}
for cn, sel in CELLS.items():
    print(f"\n   --- cell: {cn}")
    print(f"   {'reference':32s} {'arm':>8s} | {'t59':>7s} {'x59':>4s} | {'tref':>7s} "
          f"{'xref':>5s} | {'rate59':>8s} {'rateRef':>8s} | {'exact p':>9s}  verdict")
    for rn, rk in REFS.items():
        for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5),
                         ("manual", lambda r: r["lat"] <= 0.5),
                         ("BOTH", lambda r: True)):
            a = [r for r in R[L.NEW] if sel(r) and amf(r)]
            b = [r for r in R[rk] if sel(r) and amf(r)]
            t1, t2 = L.secs(a), L.secs(b)
            x1, x2 = L.bursts(a), L.bursts(b)
            if t1 <= 0 or t2 <= 0 or (x1 + x2) == 0:
                print(f"   {rn:32s} {arm:>8s} | {t1:>7.1f} {x1:>4d} | {t2:>7.1f} {x2:>5d} | "
                      f"{'--':>8s} {'--':>8s} | {'--':>9s}  no events anywhere: NO TEST POSSIBLE")
                continue
            p = float(binom.cdf(x1, x1 + x2, t1 / (t1 + t2)))
            ex[f"{cn}|{rn}|{arm}"] = dict(t1=t1, x1=x1, t2=t2, x2=x2, p=p)
            print(f"   {rn:32s} {arm:>8s} | {t1:>7.1f} {x1:>4d} | {t2:>7.1f} {x2:>5d} | "
                  f"{x1 / t1:>8.4f} {x2 / t2:>8.4f} | {p:>9.4f}  "
                  f"{'*** LOWER than ref (p<0.05)' if p < 0.05 else 'not separable'}")
OUT["exact"] = ex

# ================================================================ §2 did he fly it? ===============
L.hdr("§2  DID THE OPERATOR FLY THE 90 s HARD-CORNERING CARD? Window census, engaged arm only.")
print("   The regime the card named: engaged, < 4 m/s, sustained driver torque ~1600-2700,")
print("   |angle| 150-265 deg. Reported in WINDOW-SECONDS (2.56 s windows, 50% overlap).\n")
DEFS = {
    "engaged creep (any)": lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1],
    "+ |ang| >= 100": lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1] and r["ang"] >= 100,
    "+ |ang| >= 150": lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1] and r["ang"] >= 150,
    "+ |ang| >= 150 & eff >= 1600": lambda r: (L.CREEP[0] <= r["v"] < L.CREEP[1]
                                               and r["ang"] >= 150 and r["eff"] >= 1600),
    "+ |ang| 150-265 & eff 1600-2700": lambda r: (L.CREEP[0] <= r["v"] < L.CREEP[1]
                                                  and 150 <= r["ang"] <= 265
                                                  and 1600 <= r["eff"] <= 2700),
    "+ HIGH-RATE (idx>=1400)": lambda r: (L.CREEP[0] <= r["v"] < L.CREEP[1] and r["rb"] == 2),
}
print(f"   {'definition':36s} " + " ".join(f"{n.split()[0][:9]:>9s}" for n in
                                           ["V72r59", "V71Cr58", "V71Br54", "V62/V65", "V67/V68",
                                            "V69r4f"]))
SHOW = [L.NEW, "V71C r58  both arms GATED", "V71B r54  r26 x2 UNGATED", L.REF,
        "Kd=gated (V67 r47 + V68 r4e)", "Kd=4x<50 (V69 r4f)"]
fly = {}
for dn, sel in DEFS.items():
    vals = [L.secs([r for r in R[k] if sel(r) and r["lat"] > 0.5]) for k in SHOW]
    fly[dn] = dict(zip(SHOW, vals))
    print(f"   {dn:36s} " + " ".join(f"{v:>9.1f}" for v in vals))
OUT["flight_card"] = fly

# ================================================================ §3 excitation-matched highway ===
L.hdr("§3  HIGHWAY, EXCITATION-MATCHED. The 1-4 Hz driver-input band is the pre-declared\n"
      "    exposure-matching validity check and it FAILS unmatched (route 59 is 5.6-5.9x the\n"
      "    others). Strata are 1-4 Hz quartiles of the POOLED pair; the ratio is the exposure-\n"
      "    weighted mean of the within-stratum log-ratios.")
VLO, VHI = 16.0, 26.0


def strat_ratio(A, B, band, nstrat=4, nb=3000, rng=None):
    """Ratio of p90(band) within 1-4 Hz strata, episode-bootstrapped, exposure weighted."""
    rng = rng or np.random.default_rng(20260807)
    x = np.concatenate([[r["1-4"] for r in A], [r["1-4"] for r in B]])
    edges = np.percentile(x, np.linspace(0, 100, nstrat + 1))
    edges[0], edges[-1] = -np.inf, np.inf

    def one(aa, bb):
        num = den = 0.0
        for i in range(nstrat):
            sa = [r for r in aa if edges[i] <= r["1-4"] < edges[i + 1]]
            sb = [r for r in bb if edges[i] <= r["1-4"] < edges[i + 1]]
            if len(sa) < 4 or len(sb) < 4:
                continue
            va = np.percentile([r[band] for r in sa], 90)
            vb = np.percentile([r[band] for r in sb], 90)
            if va <= 0 or vb <= 0:
                continue
            w = 1.0 / (1.0 / len(sa) + 1.0 / len(sb))
            num += w * np.log(va / vb)
            den += w
        return np.exp(num / den) if den else np.nan

    def eps(rs):
        e = {}
        for r in rs:
            e.setdefault(str(r["ep"]), []).append(r)
        return list(e.values())

    ea, eb = eps(A), eps(B)
    pt = one(A, B)
    dr = np.full(nb, np.nan)
    for i in range(nb):
        aa = [r for k in rng.integers(0, len(ea), len(ea)) for r in ea[k]]
        bb = [r for k in rng.integers(0, len(eb), len(eb)) for r in eb[k]]
        dr[i] = one(aa, bb)
    return (float(pt), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)))


def strat_null(pool, band, nstrat=4, nb=500, rng=None):
    rng = rng or np.random.default_rng(20260808)

    def eps(rs):
        e = {}
        for r in rs:
            e.setdefault(str(r["ep"]), []).append(r)
        return list(e.values())
    ee = eps(pool)
    if len(ee) < 6:
        return np.nan, np.nan
    out = []
    for _ in range(nb):
        p = rng.permutation(len(ee))
        h = len(ee) // 2
        A = [r for k in p[:h] for r in ee[k]]
        B = [r for k in p[h:2 * h] for r in ee[k]]
        v = strat_ratio(A, B, band, nstrat, nb=0)[0]
        if np.isfinite(v):
            out.append(v)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out \
        else (np.nan, np.nan)


hm = {}
print(f"\n   {'pair':56s} {'band':>6s} {'ratio':>8s} {'95% CI':>19s} {'null':>17s}  verdict")
for other in ("V71C r58  both arms GATED", "V71B r54  r26 x2 UNGATED",
              "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)", "Kd=gated (V67 r47 + V68 r4e)"):
    A = [r for r in R[L.NEW] if VLO <= r["v"] < VHI and r["lat"] > 0.5]
    B = [r for r in R[other] if VLO <= r["v"] < VHI and r["lat"] > 0.5]
    for band in ("40-49", "24-28", "1-4"):
        pt, lo, hi = strat_ratio(A, B, band)
        nl = strat_null(A + B, band)
        hm[f"{band}|{other}"] = dict(ratio=pt, lo=lo, hi=hi, null=list(nl))
        tag = ("" if not np.isfinite(nl[0]) else
               ("inside null" if nl[0] <= pt <= nl[1] else "*** OUTSIDE NULL"))
        print(f"   {'V72 r59 / ' + other:56s} {band:>6s} {pt:>8.3f} [{lo:>7.3f},{hi:>8.3f}] "
              f"[{nl[0]:>6.2f},{nl[1]:>7.2f}]  {tag}")
OUT["highway_excitation_matched"] = hm

(ROOT / "_scratch/out/_d4_r59_exact.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_exact.json'}")
