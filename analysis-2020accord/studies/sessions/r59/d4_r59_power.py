#!/usr/bin/env python3
"""D4 -- the HONEST P(0) for route 59's grind-#2 zero, and the highway contrast.

🛑 WHY THE POOLED-CREEP P(0) IS NOT THE ANSWER. Bursts are ~68x commoner in the HIGH-RATE cell than
on the plateau (V62/V65 engaged: 17 bursts / 147.2 s vs 2 / 1180.2 s). So a route whose creep is
GENTLER than the reference's creep gets a flattering pooled expectation. Route 59's creep is exactly
that (34% corner-lite windows vs V62/V65's 65%). §1 therefore computes the expectation STRATIFIED on
the rate-index cell -- sum_c (ref rate in cell c) x (route seconds in cell c) -- which is the same
Poisson test with the covariate distribution matched instead of pooled.

§2 does the highway 40-49 Hz level contrast that no build in the corpus has ever cleared.

Writes `_scratch/out/_d4_r59_power.json`.
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
from scipy.stats import poisson

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import d4_lib as L  # noqa: E402

R = L.rows()
OUT = {}
RNG = np.random.default_rng(20260805)

# ================================================================ §1 STRATIFIED P(0) ==============
L.hdr("§1  STRATIFIED P(0) -- expectation matched on the RATE-INDEX cell, not pooled.\n"
      "    ref = V62/V65's own per-cell burst rate; exposure = the audited route's own seconds.")
ref = R[L.REF]
for scope, sel in (("creep 0.3-4 m/s", lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1]),
                   ("ALL speeds", lambda r: True)):
    print(f"\n   --- scope: {scope}")
    print(f"   {'route':42s} {'arm':>8s} | " +
          " ".join(f"{n + ' s/rate':>18s}" for n in L.RNAMES) +
          f" | {'E[bursts]':>9s} {'obs':>4s} {'P(0)':>8s}  pooled P(0)")
    st = {}
    for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
        rr = [r for r in ref if sel(r) and amf(r)]
        rate = []
        for i in range(3):
            c = [r for r in rr if r["rb"] == i]
            rate.append(L.bursts(c) / L.secs(c) if c else np.nan)
        pooled_rate = L.bursts(rr) / L.secs(rr) if rr else np.nan
        print(f"   {'[reference V62/V65]':42s} {arm:>8s} | " +
              " ".join(f"{L.secs([r for r in rr if r['rb'] == i]):9.1f}/"
                       f"{rate[i]:<8.4f}" for i in range(3)) +
              f" | {'--':>9s} {L.bursts(rr):>4d} {'--':>8s}  ref rate {pooled_rate:.4f}/s")
        for name in ("V72 r59  BOTH lanes UNGATED  ***", "V71C r58  both arms GATED",
                     "V71B r54  r26 x2 UNGATED", "Kd=gated (V67 r47 + V68 r4e)",
                     "Kd=4x<50 (V69 r4f)", "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)"):
            s = [r for r in R[name] if sel(r) and amf(r)]
            ss = [L.secs([r for r in s if r["rb"] == i]) for i in range(3)]
            exp = float(np.nansum([ss[i] * rate[i] for i in range(3)
                                   if np.isfinite(rate[i])]))
            obs = L.bursts(s)
            p0 = float(poisson.pmf(0, exp))
            p0p = float(poisson.pmf(0, pooled_rate * L.secs(s))) if np.isfinite(pooled_rate) \
                else np.nan
            st[f"{scope}|{name}|{arm}"] = dict(secs=ss, expected=exp, obs=obs, p0=p0,
                                               p0_pooled=p0p, total_s=L.secs(s))
            print(f"   {name:42s} {arm:>8s} | " +
                  " ".join(f"{ss[i]:9.1f}{'':9s}" for i in range(3)) +
                  f" | {exp:>9.2f} {obs:>4d} {p0:>8.4f}  {p0p:.4f}")
    OUT[scope] = st

# ================================================================ §2 minimum detectable ============
L.hdr("§2  WHAT ROUTE 59 COULD HAVE DETECTED. Given its exposure, the smallest burst rate whose\n"
      "    absence it rules out at 95% -- expressed as a fraction of V62/V65's rate in that cell.")
print(f"   {'cell':34s} {'arm':>8s} {'secs':>7s} {'ref rate/s':>11s} {'E[b]':>7s} "
      f"{'P(0)':>7s} {'min detectable':>15s}")
md = {}
CELLS = {"creep": lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1],
         "creep & HIGH-RATE": lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1] and r["rb"] == 2,
         "creep & |ang|>=100": lambda r: L.CREEP[0] <= r["v"] < L.CREEP[1] and r["ang"] >= 100,
         "highway >=14 m/s": lambda r: r["v"] >= L.HWY,
         "ALL": lambda r: True}
for cn, sel in CELLS.items():
    for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
        rr = [r for r in ref if sel(r) and amf(r)]
        s = [r for r in R[L.NEW] if sel(r) and amf(r)]
        if not rr or not s:
            continue
        rate = L.bursts(rr) / L.secs(rr)
        ss = L.secs(s)
        exp = rate * ss
        p0 = float(poisson.pmf(0, exp))
        # smallest lambda_total with P(0) <= 0.05 is 2.996; express as a fraction of ref
        frac = (2.996 / ss) / rate if rate > 0 else np.inf
        md[f"{cn}|{arm}"] = dict(secs=ss, rate=rate, exp=exp, p0=p0, min_frac=frac)
        print(f"   {cn:34s} {arm:>8s} {ss:>7.1f} {rate:>11.4f} {exp:>7.2f} {p0:>7.4f} "
              f"{('rules out >= ' + f'{frac:.2f}x the ref rate') if np.isfinite(frac) else '--':>15s}")
OUT["min_detectable"] = md

# ================================================================ §3 highway level contrast =======
L.hdr("§3  HIGHWAY 40-49 Hz LEVEL -- route 59 vs 54/58 and vs the stock rate lane.\n"
      "    p90 of the window envelope p99, ratio bootstrapped over ~10 s EPISODE blocks, quoted\n"
      "    against a SPLIT-HALF null computed inside the pooled pair with the identical estimator.")


def boot_ratio(a, aep, b, bep, q=90, nb=4000, rng=None):
    rng = rng or np.random.default_rng(20260805)
    ua, ub = np.unique(aep), np.unique(bep)
    if len(ua) < 2 or len(ub) < 2:
        return np.nan, np.nan, np.nan
    pa = [a[aep == e] for e in ua]
    pb = [b[bep == e] for e in ub]
    dr = np.empty(nb)
    for i in range(nb):
        sa = np.concatenate([pa[k] for k in rng.integers(0, len(pa), len(pa))])
        sb = np.concatenate([pb[k] for k in rng.integers(0, len(pb), len(pb))])
        dr[i] = np.percentile(sa, q) / max(np.percentile(sb, q), 1e-9)
    return (float(np.percentile(a, q) / max(np.percentile(b, q), 1e-9)),
            float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5)))


def split_null(v, ep, q=90, nb=800, rng=None):
    rng = rng or np.random.default_rng(20260806)
    u = np.unique(ep)
    if len(u) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nb):
        p = rng.permutation(len(u))
        h = len(u) // 2
        s1 = np.concatenate([v[ep == e] for e in u[p[:h]]])
        s2 = np.concatenate([v[ep == e] for e in u[p[h:2 * h]]])
        out.append(np.percentile(s1, q) / max(np.percentile(s2, q), 1e-9))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


# 🛑 SPEED MATCHING. A moving wheel order concentrates in a narrow-speed route. Restrict every
# highway comparison to the OVERLAP band and print the per-window speed census.
VLO, VHI = 16.0, 26.0
hi = {}
print(f"   speed-matched band {VLO}-{VHI} m/s\n")
print(f"   {'pair':70s} {'ratio(p90)':>10s} {'95% CI':>20s} {'null':>18s}  verdict")
for band in ("40-49", "24-28", "18-22", "1-4"):
    print(f"\n   --- band {band} Hz")
    for other in ("V71C r58  both arms GATED", "V71B r54  r26 x2 UNGATED",
                  "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)", "Kd=2.00  (V62 r37 + V65 r3a/r3b)",
                  "Kd=gated (V67 r47 + V68 r4e)"):
        A = [r for r in R[L.NEW] if VLO <= r["v"] < VHI and r["lat"] > 0.5]
        B = [r for r in R[other] if VLO <= r["v"] < VHI and r["lat"] > 0.5]
        if len(A) < 5 or len(B) < 5:
            print(f"   {'V72 r59 / ' + other:70s}   n too few (A={len(A)}, B={len(B)})")
            continue
        a = np.array([r[band] for r in A], float)
        b = np.array([r[band] for r in B], float)
        aep = np.array([str(r["ep"]) for r in A])
        bep = np.array([str(r["ep"]) for r in B])
        pt, lo, up = boot_ratio(a, aep, b, bep)
        nl = split_null(np.concatenate([a, b]), np.concatenate([aep, bep]))
        tag = ("" if not np.isfinite(nl[0]) else
               ("inside null" if nl[0] <= pt <= nl[1] else "*** OUTSIDE NULL"))
        hi[f"{band}|{other}"] = dict(ratio=pt, lo=lo, hi=up, null=list(nl), nA=len(A), nB=len(B),
                                     vA=float(np.mean([r["v"] for r in A])),
                                     vB=float(np.mean([r["v"] for r in B])),
                                     p90A=float(np.percentile(a, 90)),
                                     p90B=float(np.percentile(b, 90)))
        print(f"   {'V72 r59 / ' + other:70s} {pt:>10.3f} [{lo:>8.3f},{up:>9.3f}] "
              f"[{nl[0]:>7.2f},{nl[1]:>7.2f}]  {tag}  "
              f"(vA {np.mean([r['v'] for r in A]):.1f} vB {np.mean([r['v'] for r in B]):.1f}, "
              f"nA {len(A)} nB {len(B)})")
OUT["highway_matched"] = hi

(ROOT / "_scratch/out/_d4_r59_power.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_power.json'}")
