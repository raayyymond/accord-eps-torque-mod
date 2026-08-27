#!/usr/bin/env python3
"""D4 -- AUDIT OF FIX 1: is route 59's (V72) grind-#2 zero a RESULT or a SHARED ZERO?

🛑 THE TRAP THIS FILE EXISTS TO AVOID, from the kit's own record: "'V67/V68 showed zero creep
grind #2' is a SHARED ZERO, not a result -- every non-V62 build in the corpus reads 0.0, including
stock." So every zero below is printed WITH its exposure in seconds and P(observe 0) under the
reference build's own measured burst rate.

INSTRUMENT: `r47_orchestrator_checks._windows` UNCHANGED -- 2.56 s window, butter+hilbert band
envelope, p99, 500-count burst threshold, 50% overlap => secs = nwin * 2.56 / 2. Same estimator that
produced every prior route's burst count. The tapered `_grind2_lib.win_env` is NOT substituted
(they differ 1.4-1.9x; cross-comparing them is a recorded error).

RATE INDEX: 4.7121 counts per column deg/s applied to each window's PEAK |rate_c| (`ratemax`), the
kit's own pricing -- `gp-0x6ac0` is |rate| so the gain index sweeps 0 -> peak -> 0 twice per cycle.
Bins are the design's breakpoints: [0,400) plateau, [400,1400) knee, [1400,inf) HIGH RATE.

Writes `_scratch/out/_d4_r59_grind2.json`.
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
import _r31_common as C  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r31_common import sustained  # noqa: E402

CPD = 4.7121
CREEP = (0.3, 4.0)
HWY = 14.0
CORNER_ANG = 100.0
HARD_ANG, HARD_EFF = 150.0, 1600.0
OUT = {}

POOLS = {
    "Kd=0     (V61 r31)":                     ["_scratch/cache/r31"],
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_scratch/cache/r2b", "_scratch/cache/r2c", "_scratch/cache/r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
    "Kd=gated (V67 r47 + V68 r4e)":           ["_scratch/cache/r47", "_scratch/cache/v68"],
    "Kd=4x<50 (V69 r4f)":                     ["_scratch/cache/r4f"],
    "Kd=2x<50 (V70 r50)":                     ["_scratch/cache/r50"],
    "V71B r54  r26 x2 UNGATED":               ["_scratch/cache/r54"],
    "V71C r58  both arms GATED":              ["_scratch/cache/r58"],
    "V72 r59  BOTH lanes UNGATED  ***":       ["_scratch/cache/r59"],
}
REF = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
NEW = "V72 r59  BOTH lanes UNGATED  ***"
SKIP = {"_scratch/cache/r54": ("r54s10", "r54s11"),
        "_scratch/cache/r58": ("r58s12", "r58s13", "r58s14", "r58s15"),
        "_scratch/cache/r50": ("r50s0",),
        "_scratch/cache/r59": ("r59s12", "r59s13", "r59s14")}


def hdr(s):
    print("\n" + "=" * 120 + f"\n{s}\n" + "=" * 120)


# ============================================================ §1  EXPOSURE, from raw frames =======
hdr("§1  EXPOSURE IN SECONDS from raw frames, per pool. fs = fs_lattice per segment. Parked "
    "segments dropped.")
CACHES = {c for v in POOLS.values() for c in v}
PFX = {"_scratch/cache/r31": "r31s", "_scratch/cache/r2b": "r2bs", "_scratch/cache/r2c": "r2cs", "_scratch/cache/r35": "r35s",
       "_scratch/cache/r37": "r37s", "_scratch/cache/r3a": "r3as", "_scratch/cache/r3b": "r3bs", "_scratch/cache/r47": "r47s",
       "_scratch/cache/v68": "4es", "_scratch/cache/r4f": "r4fs", "_scratch/cache/r50": "r50s", "_scratch/cache/r54": "r54s",
       "_scratch/cache/r58": "r58s", "_scratch/cache/r59": "r59s"}


def seg_exposure(path):
    d = {k: v for k, v in np.load(path).items()}
    if "cs_v" not in d or "tq" not in d:
        return None
    fs = R4F.fs_lattice(d)
    dt = 1.0 / fs
    v = np.abs(np.asarray(d["cs_v"], float))
    ang = np.abs(np.asarray(d["ang"], float))
    eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
    eng = np.asarray(d.get("cc_lat", np.zeros_like(v)), float) > 0.5
    idx = CPD * np.abs(np.asarray(d["rate_c"], float))
    cr = (v >= CREEP[0]) & (v < CREEP[1])
    co = cr & (ang >= CORNER_ANG)
    hd = cr & (ang >= HARD_ANG) & (eff >= HARD_EFF)
    hi = idx >= 1400.0
    out = {}
    for nm, m in (("total", np.ones(len(v), bool)),
                  ("creep", cr), ("creep_eng", cr & eng), ("creep_man", cr & ~eng),
                  ("corner", co), ("corner_eng", co & eng), ("corner_man", co & ~eng),
                  ("hard", hd), ("hard_eng", hd & eng), ("hard_man", hd & ~eng),
                  ("hirate", hi), ("hirate_eng", hi & eng), ("hirate_man", hi & ~eng),
                  ("creep_hirate", cr & hi), ("creep_hirate_eng", cr & hi & eng),
                  ("creep_hirate_man", cr & hi & ~eng),
                  ("hwy", v >= HWY), ("hwy_eng", (v >= HWY) & eng),
                  ("hwy_man", (v >= HWY) & ~eng)):
        out[nm] = float(m.sum() * dt)
    return out


expo = {}
for name, caches in POOLS.items():
    a = {}
    for c in caches:
        for p in sorted((ROOT / c).glob("*.npz")):
            if "_imu" in p.name or "_rpm" in p.name or any(s in p.name for s in SKIP.get(c, ())):
                continue
            e = seg_exposure(p)
            if e is None:
                continue
            for k, v in e.items():
                a[k] = a.get(k, 0.0) + v
    expo[name] = a
ks = ["total", "creep", "creep_eng", "creep_man", "corner_eng", "corner_man", "hard_eng",
      "hard_man", "creep_hirate_eng", "creep_hirate_man", "hwy_eng", "hwy_man"]
print(f"   {'pool':42s} " + " ".join(f"{k:>9s}" for k in ks))
for name in POOLS:
    print(f"   {name:42s} " + " ".join(f"{expo[name].get(k, 0):9.1f}" for k in ks))
OUT["exposure_s"] = expo

# ============================================================ §2  WINDOWS + BURST CENSUS ==========
hdr("§2  THE BURST CENSUS -- 40-49 Hz envelope p99 > 500 counts. Every zero carries its exposure.")
rows = {}
for name, caches in POOLS.items():
    r = []
    for c in caches:
        rr = R47._windows(c, name, lambda v: True)
        r += [x for x in rr if not any(s in str(x["ep"][0]) for s in SKIP.get(c, ()))]
    for x in r:
        x["idx"] = CPD * x["ratemax"]
        x["eff"] = float(np.median(np.abs(sustained(np.asarray(x["raw"], float), x["fs"]))))
    rows[name] = r
    print(f"   {name:42s} {len(r):>6d} windows")

CELLS = {
    "creep 0.3-4 m/s": lambda r: CREEP[0] <= r["v"] < CREEP[1],
    "corner-lite (creep & |ang|>=100)": lambda r: CREEP[0] <= r["v"] < CREEP[1] and r["ang"] >= 100,
    "HARD corner (creep & |ang|>=150 & eff>=1600)":
        lambda r: CREEP[0] <= r["v"] < CREEP[1] and r["ang"] >= HARD_ANG and r["eff"] >= HARD_EFF,
    "★ HIGH-RATE creep (creep & idx>=1400)":
        lambda r: CREEP[0] <= r["v"] < CREEP[1] and r["idx"] >= 1400,
    "★ HIGH-RATE any speed (idx>=1400)": lambda r: r["idx"] >= 1400,
    "highway >=14 m/s": lambda r: r["v"] >= HWY,
    "ALL": lambda r: True,
}


def census(sel, label):
    print(f"\n   --- {label}")
    print(f"   {'pool':42s} {'arm':>8s} {'n':>5s} {'secs':>7s} {'max':>9s} {'p90':>8s} "
          f"{'p99':>8s} {'bursts':>7s} {'rate/s':>8s}")
    tab = {}
    for name in POOLS:
        for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5),
                         ("manual", lambda r: r["lat"] <= 0.5)):
            s = [r for r in rows[name] if sel(r) and amf(r)]
            if not s:
                tab[f"{name}|{arm}"] = dict(n=0, secs=0.0, bursts=0, rate=np.nan, mx=np.nan)
                print(f"   {name:42s} {arm:>8s} {0:>5d} {0.0:>7.1f} {'--':>9s} {'--':>8s} "
                      f"{'--':>8s} {0:>7d} {'--':>8s}")
                continue
            v = np.array([r["40-49"] for r in s], float)
            secs = len(s) * R47.WIN_S / 2.0
            b = int((v > R47.BURST).sum())
            tab[f"{name}|{arm}"] = dict(n=len(s), secs=float(secs), mx=float(v.max()),
                                        p90=float(np.percentile(v, 90)),
                                        p99=float(np.percentile(v, 99)), bursts=b,
                                        rate=float(b / secs) if secs else np.nan)
            print(f"   {name:42s} {arm:>8s} {len(s):>5d} {secs:>7.1f} {v.max():>9.1f} "
                  f"{np.percentile(v, 90):>8.1f} {np.percentile(v, 99):>8.1f} {b:>7d} "
                  f"{b / secs:>8.4f}")
    return tab


cells = {k: census(v, k) for k, v in CELLS.items()}
OUT["census"] = cells

# ============================================================ §3  POWER ===========================
hdr("§3  🛑 POWER. P(0) at the REFERENCE pool's own measured burst rate in the SAME cell/arm.\n"
    "    A zero with a large P(0) is exposure, not a fix.")
pw = {}
for cellname, tab in cells.items():
    print(f"\n   --- cell: {cellname}   (reference = {REF})")
    print(f"   {'route':42s} {'arm':>8s} {'ref rate/s':>11s} {'secs':>8s} {'obs':>5s} "
          f"{'expected':>9s} {'P(0)':>8s}   verdict")
    for name in ["V72 r59  BOTH lanes UNGATED  ***", "V71C r58  both arms GATED",
                 "V71B r54  r26 x2 UNGATED", "Kd=gated (V67 r47 + V68 r4e)"]:
        for arm in ("ENGAGED", "manual"):
            rate = tab.get(f"{REF}|{arm}", {}).get("rate", np.nan)
            cur = tab.get(f"{name}|{arm}", {})
            secs, obs = cur.get("secs", 0.0), cur.get("bursts", 0)
            if not np.isfinite(rate) or secs <= 0:
                print(f"   {name:42s} {arm:>8s} {'--':>11s} {secs:>8.1f} {obs:>5d} "
                      f"{'--':>9s} {'--':>8s}   NO EXPOSURE / NO REF RATE")
                continue
            exp = rate * secs
            p0 = float(poisson.pmf(0, exp))
            need = float("inf") if rate <= 0 else -np.log(0.05) / rate
            verd = ("RESOLVED: gone at ref rate (P(0) < 0.05)" if (p0 < 0.05 and obs == 0)
                    else "PRESENT (bursts observed)" if obs > 0
                    else f"🛑 UNDERPOWERED -- need {need:.0f} s for P(0) < 0.05")
            pw[f"{cellname}|{name}|{arm}"] = dict(rate=float(rate), secs=float(secs), obs=int(obs),
                                                  expected=float(exp), p0=p0, need_s=need)
            print(f"   {name:42s} {arm:>8s} {rate:>11.4f} {secs:>8.1f} {obs:>5d} "
                  f"{exp:>9.2f} {p0:>8.4f}   {verd}")
OUT["power"] = pw

# ============================================================ §4  WHERE THE BURSTS ACTUALLY ARE ===
hdr("§4  WHERE EVERY BURST IN THE CORPUS LIVES -- the burst-producing cell, verified not assumed.")
print(f"   {'pool':42s} {'arm':>8s} {'plateau':>9s} {'knee':>9s} {'HIGH-RATE':>10s} "
      f"| {'sec plat':>9s} {'sec knee':>9s} {'sec high':>9s}")
where = {}
RB = [(0.0, 400.0), (400.0, 1400.0), (1400.0, 1e9)]
for name in POOLS:
    for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
        s = [r for r in rows[name] if amf(r)]
        bs, ss = [], []
        for lo, hi in RB:
            t = [r for r in s if lo <= r["idx"] < hi]
            bs.append(sum(1 for r in t if r["40-49"] > R47.BURST))
            ss.append(len(t) * R47.WIN_S / 2.0)
        where[f"{name}|{arm}"] = dict(bursts=bs, secs=ss)
        print(f"   {name:42s} {arm:>8s} {bs[0]:>9d} {bs[1]:>9d} {bs[2]:>10d} | "
              f"{ss[0]:>9.1f} {ss[1]:>9.1f} {ss[2]:>9.1f}")
OUT["where"] = where

# ============================================================ §5  HIGHWAY LEVELS ==================
hdr("§5  HIGHWAY 40-49 Hz -- a LEVEL comparison (no bursts exist at highway on ANY build).\n"
    "    Ratio to the 24-28 Hz pre-declared negative control, so a route-wide level offset cancels.")
print(f"   {'pool':42s} {'arm':>8s} {'n':>5s} {'secs':>7s} {'40-49 p90':>10s} {'[95% CI]':>21s} "
      f"{'24-28 p90':>10s} {'ratio':>7s} {'v mean':>7s} {'max':>8s}")


def bootp(v, ep, q=90, nb=4000, rng=None):
    rng = rng or np.random.default_rng(20260806)
    u = np.unique(ep)
    if len(u) < 2:
        return float(np.percentile(v, q)), np.nan, np.nan
    per = [v[ep == e] for e in u]
    dr = np.empty(nb)
    for i in range(nb):
        j = rng.integers(0, len(per), len(per))
        dr[i] = np.percentile(np.concatenate([per[k] for k in j]), q)
    return (float(np.percentile(v, q)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)))


hw = {}
for name in POOLS:
    for arm, amf in (("ENGAGED", lambda r: r["lat"] > 0.5), ("manual", lambda r: r["lat"] <= 0.5)):
        s = [r for r in rows[name] if r["v"] >= HWY and amf(r)]
        if len(s) < 4:
            continue
        v = np.array([r["40-49"] for r in s], float)
        w = np.array([r["24-28"] for r in s], float)
        ep = np.array([str(r["ep"]) for r in s])
        m, lo, hi = bootp(v, ep)
        p2428 = float(np.percentile(w, 90))
        hw[f"{name}|{arm}"] = dict(n=len(s), secs=len(s) * R47.WIN_S / 2, p90=m, lo=lo, hi=hi,
                                   p90_2428=p2428, ratio=m / max(p2428, 1e-9),
                                   v=float(np.mean([r["v"] for r in s])), mx=float(v.max()))
        print(f"   {name:42s} {arm:>8s} {len(s):>5d} {len(s) * R47.WIN_S / 2:>7.1f} {m:>10.1f} "
              f"[{lo:>9.1f},{hi:>10.1f}] {p2428:>10.1f} {m / max(p2428, 1e-9):>7.2f} "
              f"{np.mean([r['v'] for r in s]):>7.2f} {v.max():>8.1f}")
OUT["highway"] = hw

(ROOT / "_scratch/out/_d4_r59_grind2.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_grind2.json'}")
