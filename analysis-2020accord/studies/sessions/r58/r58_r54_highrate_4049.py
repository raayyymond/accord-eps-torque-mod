#!/usr/bin/env python3
"""★ THE V72 BUILD QUESTION: what did ROUTE 54 do to the 40-49 Hz band, split by RATE INDEX?

WHY ROUTE 54 IS THE ONLY DRIVE THAT CAN ANSWER IT -- byte-verified here, not assumed:

    gain_A (r26) records, X[4] / Y[4], stock vs V71B
      rec0 @0xC6A68  X [0, 400, 1600, 3000]  Y 3072/3072/2434/2048 -> 6144/6144/4868/4096  x2.0 ALL FOUR
      rec1 @0xC6A7C  X [0, 250, 1200, 3000]  Y 3072/3072/2488/1536 -> 6144/6144/4976/3072  x2.0 ALL FOUR
      rec2, rec3     UNTOUCHED
    gain_B (r24) records, stock vs V70
      rec0 @0xD2A74  X [0, 400, 1400, 3000]  Y 3072/3072/2322/1536 -> 6144/6144/2322/1536  Y[2],Y[3] STOCK
      rec1 @0xD2AB0  X [0, 400, 1500, 3000]  Y 2561/2561/2247/1947 -> 5122/5122/2247/1947  Y[2],Y[3] STOCK

⇒ V69/V70 are byte-identical to stock above rate index ~1400. **V71B is 2.000x at EVERY rate index**
  (swept: 2.0000 at rateKey 100 / 400 / 1126 / 2000 / 4000 at speeds <= 10 km/h). Route 54 is the
  corpus's ONLY high-rate dose, on either lane.

🛑 V71B IS UNGATED, so BOTH arms carry the dose. The engaged/manual split on route 54 is an
   ENGAGEMENT test, not a dose test; the dose test is cross-route against V70 and stock.

RATE INDEX = 4.7121 counts per column deg/s (the settled scale), applied to each window's own
p90 |rate_c|, which is what `r47_orchestrator_checks._windows` already records. Bins are the
DESIGN's own breakpoints: [0,400) plateau · [400,1400) knee · [1400,inf) high-rate.

INSTRUMENT unchanged: `r47_orchestrator_checks._windows` (butter+hilbert envelope p99, 2.56 s,
500-count burst threshold), so every count is comparable to every prior route.

Writes `_scratch/out/_r54_highrate_4049.json`.  Usage: python studies/sessions/r58/r58_r54_highrate_4049.py
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

import r47_orchestrator_checks as R47  # noqa: E402
from _r31_common import sustained  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

CPD = 4.7121                      # rate-index counts per column deg/s -- the settled scale
RBINS = [(0.0, 400.0), (400.0, 1400.0), (1400.0, 1e9)]
RNAMES = ["idx 0-400 (plateau)", "idx 400-1400 (knee)", "idx >=1400 (HIGH RATE)"]
CREEP = (0.3, 4.0)
CORNER_ANG, CORNER_EFF = 100.0, 1200.0
RNG = np.random.default_rng(20260804)
OUT = {"rate_scale_counts_per_degps": CPD}

POOLS = {
    "stock (V58+V59+V64)": ["_scratch/cache/r2b", "_scratch/cache/r2c", "_scratch/cache/r35"],
    "V70 r50 (r24 x2, plateau only)": ["_scratch/cache/r50"],
    "V69 r4f (r24 x4, plateau only)": ["_scratch/cache/r4f"],
    "V62+V65 (r24+r26 x2 flat)": ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
    "V71B r54 (r26 x2 ALL RATE) ***": ["_scratch/cache/r54"],
    "V71C r58 (gated flat arms)": ["_scratch/cache/r58"],
}
SKIP = {"_scratch/cache/r54": ("r54s10", "r54s11"), "_scratch/cache/r58": ("r58s12", "r58s13", "r58s14", "r58s15"),
        "_scratch/cache/r50": ("r50s0",)}
REF = "V62+V65 (r24+r26 x2 flat)"


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


rows = {}
for name, caches in POOLS.items():
    r = []
    for c in caches:
        rr = R47._windows(c, name, lambda v: True)
        r += [x for x in rr if not any(s in str(x["ep"][0]) for s in SKIP.get(c, ()))]
    for x in r:
        # 🛑 BIN ON THE PEAK, NOT THE p90. `gp-0x6ac0` is |rate|, so the gain index sweeps
        # 0 -> peak -> 0 twice per oscillation cycle and a damper acts in phase with velocity =>
        # the dose a burst actually received is the gain at PEAK VELOCITY (the kit's own pricing,
        # memory: accord-grind1-ladder-monotone-at-peak-velocity). On p90 the >=1400 cell holds
        # 7 engaged windows on route 54 and the question is unanswerable; on the peak it holds 87.
        x["idx"] = CPD * x["ratemax"]
        x["idx90"] = CPD * x["rate"]                   # kept for the sensitivity check
        # sustained driver effort on the SAME samples the window was cut from
        x["eff"] = float(np.median(np.abs(sustained(np.asarray(x["raw"], float), x["fs"]))))
    rows[name] = r
    print(f"   {name:34s} {len(r):>6d} windows")


def cell(rs, sel):
    return [r for r in rs if sel(r)]


def bootp90(v, ep, nb=4000):
    u = np.unique(ep)
    if len(u) < 2:
        return float(np.percentile(v, 90)), np.nan, np.nan
    per = [v[ep == e] for e in u]
    dr = np.array([np.percentile(np.concatenate([per[k] for k in
                                                 RNG.integers(0, len(per), len(per))]), 90)
                   for _ in range(nb)])
    return (float(np.percentile(v, 90)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)))


def split_null(v, ep, nb=800):
    u = np.unique(ep)
    if len(u) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nb):
        p = RNG.permutation(len(u))
        h = len(u) // 2
        s1 = np.concatenate([v[ep == e] for e in u[p[:h]]])
        s2 = np.concatenate([v[ep == e] for e in u[p[h:2 * h]]])
        out.append(np.percentile(s1, 90) / max(np.percentile(s2, 90), 1e-9))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def table(selname, sel, key="40-49"):
    hdr(f"§  {selname}   --   40-49 Hz by RATE INDEX ({CPD} counts per column deg/s)")
    print(f"   {'pool':34s} {'arm':>8s} {'rate cell':<24s} {'n':>5s} {'secs':>7s} {'p90':>8s} "
          f"{'[95% CI]':>20s} {'max':>8s} {'24-28 p90':>10s} {'ratio':>6s} {'bursts':>7s} "
          f"{'rate/s':>8s}")
    tab = {}
    for name in POOLS:
        for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5),
                         ("manual", lambda r: r["lat"] <= 0.5)):
            for bi, (lo, hi) in enumerate(RBINS):
                s = cell(rows[name], lambda r: sel(r) and amf(r) and lo <= r["idx"] < hi)
                k = f"{name}|{arm}|{RNAMES[bi]}"
                if len(s) < 2:
                    tab[k] = dict(n=len(s), secs=len(s) * R47.WIN_S / 2.0, bursts=0)
                    print(f"   {name:34s} {arm:>8s} {RNAMES[bi]:<24s} {len(s):>5d}  "
                          f"*** too few")
                    continue
                v = np.array([r[key] for r in s], float)
                w = np.array([r["24-28"] for r in s], float)
                ep = np.array([str(r["ep"]) for r in s])
                secs = len(s) * R47.WIN_S / 2.0
                b = int((v > R47.BURST).sum())
                m, clo, chi = bootp90(v, ep)
                tab[k] = dict(n=len(s), secs=float(secs), p90=m, lo=clo, hi=chi,
                              mx=float(v.max()), p90_2428=float(np.percentile(w, 90)),
                              bursts=b, rate=float(b / secs) if secs else np.nan,
                              idx=float(np.median([r["idx"] for r in s])),
                              v=float(np.mean([r["v"] for r in s])))
                print(f"   {name:34s} {arm:>8s} {RNAMES[bi]:<24s} {len(s):>5d} {secs:>7.1f} "
                      f"{m:>8.1f} [{clo:>8.1f},{chi:>9.1f}] {v.max():>8.1f} "
                      f"{np.percentile(w, 90):>10.1f} "
                      f"{m / max(np.percentile(w, 90), 1e-9):>6.2f} {b:>7d} "
                      f"{b / secs if secs else np.nan:>8.4f}")
        print()
    return tab


ALLC = table("ALL SPEEDS, ALL WINDOWS", lambda r: True)
OUT["all"] = ALLC
CREEPC = table(f"CREEP {CREEP[0]}-{CREEP[1]} m/s", lambda r: CREEP[0] <= r["v"] < CREEP[1])
OUT["creep"] = CREEPC
CORN = table(f"★ THE REGIME GRIND #2 LIVES IN: creep AND |driver tq| >= {CORNER_EFF:.0f} AND "
             f"|angle| >= {CORNER_ANG:.0f} deg",
             lambda r: (CREEP[0] <= r["v"] < CREEP[1] and r["eff"] >= CORNER_EFF
                        and r["ang"] >= CORNER_ANG))
OUT["corner"] = CORN

# ------------------------------------------------------------------ the dose contrast ------------
hdr("★★ THE DOSE CONTRAST -- route 54's HIGH-RATE cell against the un-dosed references")
print("   In `idx >= 1400`, V69/V70 are BYTE-IDENTICAL TO STOCK and V71B is 2.000x on r26. So a")
print("   difference here IS the high-rate r26 doubling; anywhere else it is confounded with the")
print("   plateau edits. Split-half null computed inside each reference with the same estimator.\n")
A = "V71B r54 (r26 x2 ALL RATE) ***"
dose = {}
for cellname, C in (("all speeds", ALLC), ("creep", CREEPC), ("corner regime", CORN)):
    print(f"   --- {cellname}")
    for arm in ("ENGAGED", "manual"):
        for bi in range(3):
            ka = f"{A}|{arm}|{RNAMES[bi]}"
            a = C.get(ka, {})
            if not a.get("n", 0) >= 4:
                continue
            for other in ("stock (V58+V59+V64)", "V70 r50 (r24 x2, plateau only)",
                          "V69 r4f (r24 x4, plateau only)", REF):
                kb = f"{other}|{arm}|{RNAMES[bi]}"
                b = C.get(kb, {})
                if not b.get("n", 0) >= 4:
                    continue
                ra = a["p90"] / max(b["p90"], 1e-9)
                # the same ratio on the NEGATIVE CONTROL band, so a floor shift cannot pass
                rc = a["p90_2428"] / max(b["p90_2428"], 1e-9)
                sb = [r for r in rows[other] if True]
                dose[f"{cellname}|{arm}|{RNAMES[bi]}|{other}"] = dict(
                    ratio=float(ra), ctrl=float(rc), excess=float(ra / rc) if rc else np.nan,
                    nA=a["n"], nB=b["n"], p90A=a["p90"], p90B=b["p90"])
                print(f"      {arm:>8s} {RNAMES[bi]:<24s} vs {other:<34s} "
                      f"40-49 p90 {a['p90']:>7.1f}/{b['p90']:>7.1f} = {ra:>6.3f}   "
                      f"24-28 ctrl {rc:>6.3f}   excess {ra / rc if rc else np.nan:>6.3f}")
        print()
OUT["dose_contrast"] = dose

# ------------------------------------------------------------------ the burst null ---------------
hdr("★ THE QUANTIFIED NULL -- P(0) for route 54's 40-49 bursts, per rate cell, at the V62/V65 rate")
print("   'no bursts' means nothing without this. Reference = the pool that DID produce grind #2.\n")
print(f"   {'arm':>8s} {'rate cell':<24s} {'r54 secs':>9s} {'r54 obs':>8s} {'ref rate/s':>11s} "
       f"{'expected':>9s} {'P(0)':>8s}   verdict")
pw = {}
for cellname, C in (("all speeds", ALLC), ("creep", CREEPC), ("corner regime", CORN)):
    print(f"   --- {cellname}")
    for arm in ("ENGAGED", "manual"):
        for bi in range(3):
            a = C.get(f"{A}|{arm}|{RNAMES[bi]}", {})
            b = C.get(f"{REF}|{arm}|{RNAMES[bi]}", {})
            secs, obs = a.get("secs", 0.0), a.get("bursts", 0)
            rate = b.get("rate", np.nan)
            if secs <= 0 or not np.isfinite(rate):
                print(f"   {arm:>8s} {RNAMES[bi]:<24s} {secs:>9.1f} {obs:>8d} "
                      f"{'--':>11s} {'--':>9s} {'--':>8s}   NO EXPOSURE / NO REF RATE")
                continue
            exp = rate * secs
            p0 = float(poisson.pmf(0, exp))
            need = float("inf") if rate <= 0 else -np.log(0.05) / rate
            verd = ("RESOLVED: absent at the reference rate" if (p0 < 0.05 and obs == 0)
                    else "PRESENT" if obs > 0
                    else f"🛑 UNDERPOWERED -- need {need:.0f} s")
            pw[f"{cellname}|{arm}|{RNAMES[bi]}"] = dict(secs=secs, obs=obs, rate=float(rate),
                                                        expected=float(exp), p0=p0, need=need)
            print(f"   {arm:>8s} {RNAMES[bi]:<24s} {secs:>9.1f} {obs:>8d} {rate:>11.4f} "
                  f"{exp:>9.2f} {p0:>8.4f}   {verd}")
    print()
OUT["power"] = pw

# ------------------------------------------------------------------ within-route eng/man ---------
hdr("WITHIN-ROUTE ENGAGED vs MANUAL on route 54 -- an ENGAGEMENT test (the dose is in both arms)")
print("   If the high-rate r26 doubling drives 40-49 Hz through the PLANT, both arms should move")
print("   together. If it needs the closed LKAS loop, only the engaged arm moves.\n")
em = {}
for cellname, C in (("all speeds", ALLC), ("creep", CREEPC)):
    for bi in range(3):
        a = C.get(f"{A}|ENGAGED|{RNAMES[bi]}", {})
        b = C.get(f"{A}|manual|{RNAMES[bi]}", {})
        if not (a.get("n", 0) >= 4 and b.get("n", 0) >= 4):
            continue
        s = [r for r in rows[A] if (True if cellname == "all speeds"
                                    else CREEP[0] <= r["v"] < CREEP[1])
             and RBINS[bi][0] <= r["idx"] < RBINS[bi][1]]
        se = [r for r in s if r["lat"] > 0.5]
        sm = [r for r in s if r["lat"] <= 0.5]
        v = np.concatenate([np.array([r["40-49"] for r in se]),
                            np.array([r["40-49"] for r in sm])])
        ep = np.concatenate([np.array([str(r["ep"]) for r in se]),
                             np.array([str(r["ep"]) for r in sm])])
        nl = split_null(v, ep)
        ra = a["p90"] / max(b["p90"], 1e-9)
        rc = a["p90_2428"] / max(b["p90_2428"], 1e-9)
        em[f"{cellname}|{RNAMES[bi]}"] = dict(ratio=float(ra), ctrl=float(rc),
                                              excess=float(ra / rc) if rc else np.nan,
                                              null=[nl[0], nl[1]], nA=a["n"], nB=b["n"])
        tag = ("" if not np.isfinite(nl[0]) else
               ("INSIDE NULL" if nl[0] <= ra <= nl[1] else "*** OUTSIDE"))
        print(f"   {cellname:<12s} {RNAMES[bi]:<24s} eng/man 40-49 p90 = {ra:>6.3f}  "
              f"(eng {a['p90']:>6.1f} n={a['n']:<4d} man {b['p90']:>6.1f} n={b['n']:<4d})  "
              f"24-28 ctrl {rc:>5.3f}  excess {ra / rc if rc else np.nan:>5.3f}  "
              f"null[{nl[0]:.2f},{nl[1]:.2f}] {tag}")
OUT["eng_vs_man"] = em

# ------------------------------------------------------------------ exposure census --------------
hdr("RATE-INDEX EXPOSURE CENSUS -- read every null above against this")
print(f"   {'pool':34s} {'arm':>8s} | " + " ".join(f"{n:>24s}" for n in RNAMES))
cen = {}
for name in POOLS:
    for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
        c = [len(cell(rows[name], lambda r: amf(r) and lo <= r["idx"] < hi))
             for lo, hi in RBINS]
        cen[f"{name}|{arm}"] = c
        print(f"   {name:34s} {arm:>8s} | " +
              " ".join(f"{f'{x} win / {x * 1.28:.0f} s':>24s}" for x in c))
OUT["census"] = cen

(ROOT / "_scratch/out/_r54_highrate_4049.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_r54_highrate_4049.json'}")
