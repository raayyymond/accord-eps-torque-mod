#!/usr/bin/env python3
"""DELIVERABLE 1 (continued) -- V75 on V74's OWN pre-registered falsifiers, like for like.

Same code path as `studies/sessions/r5d/r5d_falsifiers.py` / `studies/sessions/r5d/r5d_tracking_test.py` / `studies/sessions/r5d/r5d_3xf0_check.py`, thirteen
builds instead of eleven, route 5e restricted to its pre-fault slice.

🛑 FALSIFIERS B AND C WERE RETIRED IN THEIR ANCHORED FORM at V74
(`memory/reference/measurement/reference-accord-falsifier-b-anchored-search-presupposes-answer.md`): an anchored search can
only ever confirm its own prediction. They are computed here for CONTINUITY with the corpus table --
so V75 has a number in the same column as the other twelve -- and the UN-ANCHORED replacement (a
33-47 Hz wideband peak search, regressed across builds against 5*f0 and against 2*f_grind1) is
computed beside them and is the one that carries the verdict.

Usage:  python studies/sessions/v78/v78_symptom_falsifiers.py   ->  writes _scratch/out/_v78_falsifiers.json
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import d6_events as D  # noqa: E402
import v78_symptom_lib as V  # noqa: E402
from d6b_events_fixed import bursts  # noqa: E402

RNG = np.random.default_rng(880505)
OUT = {}
V.install_fs()
BUILDS = [b for b in V.CORPUS if b != "V68/r4e"]
WIDEBAND, GRIND1, RATCHET = (33.0, 47.0), (18.0, 22.0), (6.0, 9.0)


def load_runs(build, vhi=12.5, engaged=True):
    out = []
    for _, s, a, b, d, fs in D.runs(build, 0.0, vhi, engaged, 512):
        out.append(dict(run=(build, s, a), x=np.asarray(d["tq"][a:b], float), fs=fs,
                        v=float(np.mean(np.abs(d["cs_v"][a:b])))))
    return out


RUNS = {b: load_runs(b) for b in BUILDS}
RUNS_CREEP = {b: load_runs(b, 4.0) for b in BUILDS}


def avg_spec(runs, nfft):
    acc, K, fr = None, 0, None
    for r in runs:
        x, fs = r["x"], r["fs"]
        for i in range(0, len(x) - nfft + 1, nfft // 2):
            P = C.periodogram(x[i:i + nfft], fs, nfft, True)
            if P is None:
                continue
            fr = np.fft.rfftfreq(nfft, 1 / fs) if fr is None else fr
            acc = P.copy() if acc is None else acc + P
            K += 1
    return (fr, acc / K, K) if K else (None, None, 0)


def harm5(runs, nfft):
    fr, P, K = avg_spec(runs, nfft)
    if P is None or K < 2:
        return (np.nan,) * 4 + (K,)
    R = G.prom_spectrum(fr, P)
    f0, p0 = G.locate(fr, P, 6, 9, R=R)
    j = int(np.argmin(np.abs(fr - 5 * f0)))
    w = slice(max(0, j - 4), j + 5)
    k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
    return float(f0), float(p0), float(fr[k]), float(R[k]), K


# ================================================================== B ============================
V.hdr("FALSIFIER B (RETIRED FORM, for corpus continuity) -- anchored 5 x f0 prominence")
print(f"  {'build':<10} {'K':>4} {'f0':>6} {'5xf0 Hz':>8} {'prom(5xf0)':>10} {'95% CI':>18}  "
      f"vs 3.0")
b5 = {}
for b in BUILDS:
    rs = RUNS[b]
    if len(rs) < 3:
        print(f"  {b:<10}  -- fewer than 3 runs")
        continue
    f0, p0, f5, p5, K = harm5(rs, 2048)
    dr = np.full(400, np.nan)
    for i in range(400):
        samp = [rs[j] for j in RNG.integers(0, len(rs), len(rs))]
        dr[i] = harm5(samp, 2048)[3]
    lo, hi = np.nanpercentile(dr, [2.5, 97.5])
    vd = "ABORT" if p5 > 3.0 else ("clear" if hi <= 3.0 else "clear (CI touches 3.0)")
    b5[b] = dict(f0=f0, prom_f0=p0, f5=f5, prom5=p5, lo=float(lo), hi=float(hi), K=K)
    print(f"  {b:<10} {K:>4} {f0:>6.2f} {f5:>8.2f} {p5:>10.2f} [{lo:>7.2f}, {hi:>7.2f}]  {vd}")
OUT["falsifier_B"] = b5
p5s = [v["prom5"] for v in b5.values()]
print(f"\n  CORPUS SPREAD {min(p5s):.2f} .. {max(p5s):.2f}, median {np.median(p5s):.2f}.  "
      f"at/above 3.0: {[k for k, v in b5.items() if v['prom5'] >= 3.0] or 'none'}")

V.hdr("FALSIFIER B, K-FREE SECOND METHOD -- per-window prominence at 5 x f0")
pw5 = {}
for b in BUILDS:
    vals, un = [], []
    for r in RUNS[b]:
        x, fs = r["x"], r["fs"]
        f = np.fft.rfftfreq(512, 1 / fs)
        for i in range(0, len(x) - 512 + 1, 256):
            P = C.periodogram(x[i:i + 512], fs, 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            f0, p0 = G.locate(f, P, 6, 9, R=R)
            if not np.isfinite(f0) or p0 < 3.0:
                continue
            j = int(np.argmin(np.abs(f - 5 * f0)))
            w = slice(max(0, j - 2), j + 3)
            k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
            vals.append(float(R[k]))
            un.append(r["run"])
    if len(vals) < 10:
        print(f"  {b:<10}  -- {len(vals)} windows, underpowered")
        continue
    per = {}
    for v_, u in zip(vals, un):
        per.setdefault(u, []).append(v_)
    ks = list(per)
    dr = np.array([np.median(np.concatenate([per[ks[j]] for j in RNG.integers(0, len(ks), len(ks))]))
                   for _ in range(2000)])
    lo, hi = np.nanpercentile(dr, [2.5, 97.5])
    pw5[b] = dict(med=float(np.median(vals)), lo=float(lo), hi=float(hi), n=len(vals))
    print(f"  {b:<10} n={len(vals):>4}  median prominence at 5xf0 {np.median(vals):>5.2f} "
          f"[{lo:.2f}, {hi:.2f}]")
OUT["falsifier_B_perwindow"] = pw5

# ================================================================== A ============================
V.hdr("FALSIFIER A -- duty ratio > 1.2 AND prominence ratio > 1.3, BOTH required")
duty, prom = {}, {}
for b in BUILDS:
    dv, du, pv, pu = [], [], [], []
    for r in RUNS[b]:
        env = np.abs(D.analytic(D.bp(r["x"], r["fs"], *D.RATCHET)))
        bs = bursts(env, r["fs"])
        dv.append(float(sum(j - i for i, j, _ in bs) / max(len(env), 1)))
        du.append(r["run"])
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            _, pp = G.locate(f, P, 6.0, 9.0)
            if np.isfinite(pp):
                pv.append(pp)
                pu.append(r["run"])
    duty[b] = (dv, du)
    prom[b] = (pv, pu)


def rr(av, au, bv, bu, nb=2000):
    pa, pb = {}, {}
    for v_, u in zip(av, au):
        pa.setdefault(u, []).append(v_)
    for v_, u in zip(bv, bu):
        pb.setdefault(u, []).append(v_)
    ka, kb = list(pa), list(pb)
    if len(ka) < 2 or len(kb) < 2:
        return (np.nan,) * 3
    dr = np.full(nb, np.nan)
    for i in range(nb):
        x = np.median(np.concatenate([pa[ka[j]] for j in RNG.integers(0, len(ka), len(ka))]))
        y = np.median(np.concatenate([pb[kb[j]] for j in RNG.integers(0, len(kb), len(kb))]))
        dr[i] = x / y if y else np.nan
    obs = (np.median(np.concatenate([pa[k] for k in ka]))
           / np.median(np.concatenate([pb[k] for k in kb])))
    return float(obs), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


print(f"  {'V75 vs':<10} {'duty ratio':>22} {'prominence ratio':>22}   FALSIFIER A")
for b in ("V74/r5d", "V73/r5a", "V72/r59", "V59/r2c", "V58/r2b"):
    d_ = rr(*duty["V75/r5e"], *duty[b])
    p_ = rr(*prom["V75/r5e"], *prom[b])
    fired = "FIRES" if (d_[0] > 1.2 and p_[0] > 1.3) else "clear"
    print(f"  {b:<10} {d_[0]:6.3f} [{d_[1]:5.2f},{d_[2]:6.2f}] {p_[0]:6.3f} "
          f"[{p_[1]:5.2f},{p_[2]:6.2f}]   {fired}")
    OUT.setdefault("falsifier_A", {})[b] = dict(duty=list(d_), prom=list(p_), fires=fired)

# ================================================================== C ============================
V.hdr("FALSIFIER C -- delta f0, raw and SPEED-MATCHED")
VBI = [(0.0, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
f0w = {}
for b in BUILDS:
    rows = []
    for r in RUNS[b]:
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            ff, pp = G.locate(f, P, 5, 12, R=R)
            if np.isfinite(ff) and pp >= 3.0:
                rows.append((ff, r["v"], r["run"]))
    f0w[b] = rows
print(f"  {'build':<10} " + " ".join(f"{lo:.0f}-{hi:.1f}".rjust(11) for lo, hi in VBI) + "   overall")
for b in BUILDS:
    cells = []
    for lo, hi in VBI:
        v_ = [x for x, vv, _ in f0w[b] if lo <= vv < hi]
        cells.append(f"{np.median(v_):>6.2f}({len(v_):>3})" if len(v_) >= 8 else f"{'--':>11}")
    allv = [x for x, _, _ in f0w[b]]
    print(f"  {b:<10} " + " ".join(c.rjust(11) for c in cells)
          + (f"   {np.median(allv):.2f}" if allv else ""))
    OUT.setdefault("f0", {})[b] = float(np.median(allv)) if allv else np.nan
for b in ("V74/r5d", "V73/r5a"):
    ds, ws = [], []
    for lo, hi in VBI:
        a = [x for x, vv, _ in f0w["V75/r5e"] if lo <= vv < hi]
        c = [x for x, vv, _ in f0w[b] if lo <= vv < hi]
        if len(a) >= 8 and len(c) >= 8:
            ds.append(np.median(a) - np.median(c))
            ws.append(1.0 / (1.0 / len(a) + 1.0 / len(c)))
    if ds:
        md = float(np.average(ds, weights=ws))
        print(f"\n  SPEED-MATCHED delta-f0(V75 - {b}) = {md:+.3f} Hz over {len(ds)} shared bins   "
              f"=> |d| <= 0.3 {'PASS' if abs(md) <= 0.3 else 'FAIL'} · "
              f"> 0.5 {'ABORT' if abs(md) > 0.5 else 'clear'}")
        OUT.setdefault("falsifier_C", {})[b] = dict(matched=md, nbins=len(ds))
    else:
        print(f"\n  SPEED-MATCHED delta-f0(V75 - {b}): no shared speed bin with >= 8 windows both")

# ================================================================== WIDEBAND =====================
V.hdr("THE UN-ANCHORED REPLACEMENT -- 33-47 Hz wideband peak, and where it sits vs 5*f0 / 2*grind1")
print("  A genuine relay harmonic MOVES with f0. A pre-existing line does not. The anchored search")
print("  cannot tell them apart; this one can.\n")
print(f"  {'build':<10} {'f0':>6} {'5xf0':>7} {'fgrind1':>8} {'2xg1':>7} {'peak':>7} {'prom':>7} "
      f"{'|peak-5f0|':>10} {'|peak-2g1|':>10}")
wb = {}
for b in BUILDS:
    fr, P, K = avg_spec(RUNS[b], 2048)
    if P is None or K < 2:
        continue
    R = G.prom_spectrum(fr, P)
    f0 = G.locate(fr, P, *RATCHET, R=R)[0]
    fg = G.locate(fr, P, *GRIND1, R=R)[0]
    m = (fr >= WIDEBAND[0]) & (fr <= WIDEBAND[1]) & np.isfinite(R)
    j = int(np.argmax(np.where(m, R, -np.inf)))
    wb[b] = dict(f0=f0, fg=fg, peak=float(fr[j]), prom=float(R[j]), K=K)
    print(f"  {b:<10} {f0:>6.2f} {5 * f0:>7.2f} {fg:>8.2f} {2 * fg:>7.2f} {fr[j]:>7.2f} "
          f"{R[j]:>7.2f} {abs(fr[j] - 5 * f0):>10.2f} {abs(fr[j] - 2 * fg):>10.2f}")
OUT["wideband"] = wb


def ts(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    sl = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(len(x)) for j in range(i + 1, len(x))
          if x[j] != x[i]]
    sl = np.array(sl)
    return float(np.median(sl)), float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5))


ks = list(wb)
pk = [wb[b]["peak"] for b in ks]
print(f"\n  Theil-Sen slope(peak vs 5*f0)      = "
      + "%.3f [%.3f, %.3f]" % ts([5 * wb[b]["f0"] for b in ks], pk))
print(f"  Theil-Sen slope(peak vs 2*f_grind1)= "
      + "%.3f [%.3f, %.3f]" % ts([2 * wb[b]["fg"] for b in ks], pk))
OUT["tracking"] = dict(vs_5f0=ts([5 * wb[b]["f0"] for b in ks], pk),
                       vs_2g1=ts([2 * wb[b]["fg"] for b in ks], pk))

V.hdr("ODD-SERIES COMPLETENESS -- 3 x f0, with its own confound distance to that build's grind #1")
print(f"  {'build':<10} {'f0':>6} {'3xf0':>7} {'prom(3xf0)':>11} {'fgrind1':>8} {'gap':>6}")
for b in BUILDS:
    if b not in wb:
        continue
    fr, P, K = avg_spec(RUNS[b], 2048)
    R = G.prom_spectrum(fr, P)
    f0, fg = wb[b]["f0"], wb[b]["fg"]
    j = int(np.argmin(np.abs(fr - 3 * f0)))
    w = slice(max(0, j - 4), j + 5)
    k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
    OUT.setdefault("h3", {})[b] = dict(f=float(fr[k]), prom=float(R[k]), gap=float(abs(3 * f0 - fg)))
    print(f"  {b:<10} {f0:>6.2f} {3 * f0:>7.2f} {R[k]:>11.2f} {fg:>8.2f} {abs(3 * f0 - fg):>6.2f}"
          + ("   <- 3xf0 within 1 Hz of its OWN grind #1: CONFOUNDED"
             if abs(3 * f0 - fg) < 1.0 else ""))

with open(ROOT / "_scratch/out/_v78_falsifiers.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_v78_falsifiers.json")
