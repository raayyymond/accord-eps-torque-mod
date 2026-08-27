#!/usr/bin/env python3
"""ROUTE 50 / V70 -- the operator's NEW report: *"steering felt STIFFER during LKAS engagement"*.

TWO THINGS ARE TESTED, and they are different questions.

ss1-ss2  THE ORCHESTRATOR'S CANDIDATE MECHANISM, stated for refutation: *V69's peak gain 12288
         rails the r24 lane at |dtorque| = 683 against a flight max of 633.9, so V69 was operating
         just under saturation and soft-compressed at large excursions; V70's rail is 1365 and is
         never reached, so V70's lane is FULLY LINEAR and could feel stiffer at large inputs
         despite a lower small-signal gain.*
         🛑 THE CLAMP AT 0x3AC42 IS A HARD `clamp(., -0x2000, +0x2000)`, not a soft compressor. It
         is EXACTLY linear below the rail. So the mechanism requires V69 to have ACTUALLY REACHED
         683, and "just under" is not "at". ss1 measures the fraction of engaged time above each
         rail on both routes; ss2 measures what a rail would have cost had it been hit.
         |dtorque| here is `v69_surface_math.measured_dtorque`'s estimator UNCHANGED -- the
         firmware cell gp-0x4f62 = (x[n]-x[n-4])/2 at 1 kHz, applied to the 100 Hz bus as its exact
         transfer |H(f)| = |sin(pi f 0.004)|. 🛑 SILENT above 50 Hz and still rising through it, so
         EVERY |dtorque| number in this kit is a LOWER BOUND. That cuts toward the hypothesis and
         is stated at every table.

ss3-ss5  WHAT "STIFF" ACTUALLY MEANS TO A DRIVER: more bar torque for the same steering action.
         Instruments, all speed-matched and episode-bootstrapped:
           eff        sustained |lowpass(tq, 3 Hz)| -- the driver's own push, counts.
           eff/rate   torque per unit angle rate -- a VISCOUS stiffness proxy.
           eff/|ang|  torque per unit angle -- a SPRING stiffness proxy.
           press      `cs_press` duty (openpilot's steeringPressed).
         🛑 The operator's comparison is WITHIN ONE DRIVE (engaged vs manual), so that contrast is
         the primary one; cross-build is secondary and cross-route medians are never quoted alone.

Writes `_scratch/out/_r50_stiffness.json`.  Usage: python studies/sessions/r50/r50_stiffness.py
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
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r50_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = "blk"
RNG = np.random.default_rng(20260804)
OUT = {}

RAIL_V69 = 683       # V69 peak gain 12288 -> 8192*1024/12288
RAIL_V70 = 1365      # V70 peak gain  6144 -> 8192*1024/6144
RAIL_V62 = 1365      # V62/V65 `sar 0x9` on the stock LERP: same 2x, same rail at creep
CREEP = 20 / 3.6

ROUTES = {"V70/r50": ("_scratch/cache/r50", "r50s", [0, 1, 2]),
          "V69/r4f": ("_scratch/cache/r4f", "r4fs", list(range(8))),
          "V68/r4e": ("_scratch/cache/v68", "4es", [31, 32, 33, 34]),
          "V67/r47": ("_scratch/cache/r47", "r47s", list(range(26))),
          "V62/r37": ("_scratch/cache/r37", "r37s", list(range(15))),
          "V59/r2c": ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12])}
ROOT = HERE.parent


def dtorque(tq, fs=100.0):
    """gp-0x4f62's magnitude via the firmware's own difference transfer function. LOWER BOUND."""
    x = np.asarray(tq, float)
    x = np.where(np.isfinite(x), x, 0.0)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), d=1 / fs)
    return np.fft.irfft(X * np.abs(np.sin(np.pi * f * 0.004)), len(x))


# =============================================================== ss1 |dtorque| ====================
L.hdr("ss1  ★ |dtorque| ON THE WIRE -- does either build ever REACH its rail?")
print(f"   V69 rails at |dtorque| >= {RAIL_V69}; V70 and V62/V65 at >= {RAIL_V70}.")
print("   🛑 The clamp is HARD, not a soft compressor -- below the rail the lane is EXACTLY linear,")
print("      so 'operating just under saturation' costs nothing. The mechanism needs the rail HIT.")
print("   🛑 Every |dtorque| figure is a LOWER BOUND (|H| is silent above 50 Hz, still rising).\n")
print(f"   {'route':10s} {'arm':>8s} {'secs':>7s} | {'p50':>7s} {'p99':>7s} {'p99.9':>7s} "
      f"{'max':>7s} | {'% > 683':>8s} {'% > 1365':>9s} | {'|tq| max':>8s}")
dtab, dstore = {}, {}
for name, (cache, pfx, segs) in ROUTES.items():
    for arm in ("ENGAGED", "manual", "all"):
        acc, secs, tqmax = [], 0.0, 0.0
        for s in segs:
            p = ROOT / cache / f"{pfx}{s}.npz"
            if not p.exists():
                continue
            d = C.load(s, ROOT / cache, pfx)
            fs = G.fs_of(d)
            tq = np.asarray(d["tq"], float)
            dt = np.abs(dtorque(tq, fs))
            lat = np.asarray(d["cc_lat"], float) > 0.5
            m = lat if arm == "ENGAGED" else (~lat if arm == "manual" else np.ones(len(lat), bool))
            if not m.any():
                continue
            acc.append(dt[m])
            secs += m.sum() / fs
            tqmax = max(tqmax, float(np.max(np.abs(tq[m]))))
        if not acc:
            print(f"   {name:10s} {arm:>8s}    (none)")
            continue
        v = np.concatenate(acc)
        if arm == "ENGAGED":
            dstore[name] = v
        row = dict(secs=secs, p50=float(np.percentile(v, 50)), p99=float(np.percentile(v, 99)),
                   p999=float(np.percentile(v, 99.9)), mx=float(v.max()),
                   f683=float((v > RAIL_V69).mean()), f1365=float((v > RAIL_V70).mean()),
                   tqmax=tqmax)
        dtab[f"{name}|{arm}"] = row
        print(f"   {name:10s} {arm:>8s} {secs:>7.1f} | {row['p50']:>7.1f} {row['p99']:>7.1f} "
              f"{row['p999']:>7.1f} {row['mx']:>7.1f} | {100 * row['f683']:>7.4f}% "
              f"{100 * row['f1365']:>8.4f}% | {tqmax:>8.0f}")
    print()
OUT["dtorque"] = dtab

# =============================================================== ss2 the linear-range question ====
L.hdr("ss2  WHAT FRACTION OF V69's ENGAGED TIME SAT ABOVE V70's LINEAR RANGE? -- the brief's "
      "exact question")
v69 = dstore.get("V69/r4f")
v70 = dstore.get("V70/r50")
lin = {}
if v69 is not None and v70 is not None:
    for lbl, thr in (("V69's own rail 683", RAIL_V69), ("V70's rail 1365", RAIL_V70)):
        a = float((v69 > thr).mean())
        b = float((v70 > thr).mean())
        lin[lbl] = dict(v69=a, v70=b)
        print(f"   above {lbl:<22} V69 engaged {100 * a:9.5f}%   V70 engaged {100 * b:9.5f}%")
    print(f"\n   V69 engaged |dtorque| max = {v69.max():.1f}  vs its rail {RAIL_V69}  "
          f"⇒ margin {RAIL_V69 / max(v69.max(), 1e-9):.3f}x")
    print(f"   V70 engaged |dtorque| max = {v70.max():.1f}  vs its rail {RAIL_V70}  "
          f"⇒ margin {RAIL_V70 / max(v70.max(), 1e-9):.3f}x")
    hit69 = float((v69 > RAIL_V69).mean())
    print(f"\n   ⇒ VERDICT ON THE MECHANISM: V69 spent {100 * hit69:.5f}% of engaged time at or "
          f"above its rail.")
    print("     The clamp is exact-linear below it, so a rail that is never reached cannot compress")
    print("     anything. Read ss1's `% > 683` column, not the margin.")
OUT["linear_range"] = lin

# =============================================================== ss3 driver effort ================
L.hdr("ss3  ★★ DRIVER EFFORT -- what a driver would actually call 'stiff'")
store = L.records()
print("   eff = mean sustained |lowpass(tq, 3 Hz)| over the window, in torque-sensor counts.")
print("   Two derived stiffness proxies: eff/rate (viscous) and eff/|ang| (spring).")
print("   🛑 Cross-route medians are NOT covariate-matched -- ss4 does the matched contrast.\n")


def derive(rs):
    out = []
    for r in rs:
        q = dict(r)
        q["eff_rate"] = r["eff"] / max(r["rate"], 1.0)
        q["eff_ang"] = r["eff"] / max(r["ang"], 1.0)
        out.append(q)
    return out


ALL = {k: derive(v) for k, v in store.items()}
print(f"   {'build':10s} {'arm':>8s} {'n':>5s} {'v p50':>6s} {'rate p50':>9s} | {'eff p50':>8s} "
      f"{'[95% CI]':>19s} {'eff p90':>8s} | {'eff/rate':>9s} {'eff/|ang|':>10s} {'press':>6s}")
eff = {}
for b in ("V59/r2c", "V62/r37", "V67/r47", "V68/r4e", "V69/r4f", "V70/r50"):
    for arm, e in (("ENGAGED", 1), ("manual", 0)):
        rs = [r for r in ALL.get(b, []) if r["eng"] == e]
        if len(rs) < 4:
            print(f"   {b:10s} {arm:>8s} {len(rs):>5d}   *** too few")
            continue
        m, lo, hi = G.boot_median_ci(rs, "eff", RNG, nboot=2000)
        pr = np.array([r.get("press", np.nan) for r in rs], float)
        eff[f"{b}|{arm}"] = dict(n=len(rs), eff=float(m), lo=float(lo), hi=float(hi),
                                 effp90=float(np.percentile(G.col(rs, "eff"), 90)),
                                 eff_rate=float(np.median(G.col(rs, "eff_rate"))),
                                 eff_ang=float(np.median(G.col(rs, "eff_ang"))),
                                 press=float(np.nanmean(pr)))
        x = eff[f"{b}|{arm}"]
        print(f"   {b:10s} {arm:>8s} {len(rs):>5d} {np.median(G.col(rs, 'v')):>6.2f} "
              f"{np.median(G.col(rs, 'rate')):>9.1f} | {m:>8.0f} [{lo:>7.0f},{hi:>8.0f}] "
              f"{x['effp90']:>8.0f} | {x['eff_rate']:>9.2f} {x['eff_ang']:>10.2f} "
              f"{x['press']:>6.2f}")
    print()
OUT["effort"] = eff

# =============================================================== ss4 within-route matched =========
L.hdr("ss4  ★★★ THE OPERATOR'S OWN COMPARISON -- ENGAGED vs MANUAL *within each route*, "
      "speed+rate matched")
print("   Cells are (speed bin, |rate| bin) with the ENGAGEMENT dimension REMOVED, because")
print("   engagement is the contrast. Effort is the OUTCOME, so it is never a matching dimension.")
print("   ratio > 1 = MORE driver effort while LKAS is engaged = 'stiffer'.\n")


def recell(rs, dims=("v", "rate")):
    out = []
    for r in rs:
        c = []
        if "v" in dims:
            c.append(G.binof(r["v"], G.V_BINS))
        if "rate" in dims:
            c.append(G.binof(r["rate"], G.R_BINS))
        q = dict(r)
        q["cell"] = tuple(c)
        out.append(q)
    return out


print(f"   {'build':10s} {'key':<11s} {'ratio eng/man':>13s} {'[95% CI]':>19s} {'cells':>6s} "
      f"{'null [2.5,97.5]':>20s}  verdict")
wr = {}
for b in ("V59/r2c", "V62/r37", "V67/r47", "V69/r4f", "V70/r50"):
    rs = ALL.get(b, [])
    A = recell([r for r in rs if r["eng"] == 1])
    B = recell([r for r in rs if r["eng"] == 0])
    if len(A) < 8 or len(B) < 8:
        print(f"   {b:10s} *** too few (eng {len(A)}, man {len(B)})")
        continue
    nl = G.split_half_null(A + B, "eff", RNG, nrep=200, min_ep=2, min_win=4)
    for key in ("eff", "eff_rate", "eff_ang"):
        r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=2000,
                                                        min_ep=2, min_win=4)
        ns = (f"[{nl[1]:.3f}, {nl[2]:.3f}]" if np.isfinite(nl[1]) else "n/a")
        vd = ""
        if key == "eff" and np.isfinite(r) and np.isfinite(nl[1]):
            vd = "INSIDE NULL" if nl[1] <= r <= nl[2] else "*** OUTSIDE NULL"
        wr[f"{b}|{key}"] = dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                                null=[float(x) for x in nl])
        print(f"   {b:10s} {key:<11s} {r:>13.3f} [{lo:>7.3f},{hi:>8.3f}] {nc:>6d} {ns:>20s}  {vd}")
    print()
OUT["within_route"] = wr

# =============================================================== ss5 cross-build matched ==========
L.hdr("ss5  CROSS-BUILD, ENGAGED ONLY, speed+rate matched -- is V70 stiffer than its predecessors?")
print("   ratio > 1 = MORE driver effort on V70 than on the comparison build, at matched speed and")
print("   matched angle rate.  ⚠ Route 50's 28.9 s of engaged creep makes every CI here wide; the")
print("   number to read is whether the CI EXCLUDES 1, not the point estimate.\n")
print(f"   {'vs':10s} {'key':<11s} {'ratio V70/other':>15s} {'[95% CI]':>19s} {'cells':>6s} "
      f"{'null':>20s}")
xb = {}
A70 = recell([r for r in ALL["V70/r50"] if r["eng"] == 1])
for b in ("V59/r2c", "V62/r37", "V67/r47", "V69/r4f"):
    B = recell([r for r in ALL.get(b, []) if r["eng"] == 1])
    nl = G.split_half_null(B, "eff", RNG, nrep=200, min_ep=2, min_win=4)
    for key in ("eff", "eff_rate", "eff_ang"):
        r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A70, B, key, RNG, nboot=2000,
                                                        min_ep=2, min_win=4)
        ns = (f"[{nl[1]:.3f}, {nl[2]:.3f}]" if np.isfinite(nl[1]) else "n/a")
        xb[f"{b}|{key}"] = dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                                null=[float(x) for x in nl])
        print(f"   {b:10s} {key:<11s} {r:>15.3f} [{lo:>7.3f},{hi:>8.3f}] {nc:>6d} {ns:>20s}")
    print()
OUT["cross_build"] = xb

(HERE / "_scratch/out/_r50_stiffness.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r50_stiffness.json'}")
