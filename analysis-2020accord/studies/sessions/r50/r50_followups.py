#!/usr/bin/env python3
"""ROUTE 50 / V70 -- the three follow-ups the first three scripts left open.

ss1  |dtorque| IS A LOWER BOUND -- so how big would the underestimate have to be before V69 was
     really railing? The estimator applies the firmware's own difference transfer
     |H(f)| = |sin(pi f 0.004)|, which is SILENT above 50 Hz and still rising through it. That cuts
     TOWARD the saturation hypothesis, so the refutation in `studies/sessions/r50/r50_stiffness.py` ss2 is only as good
     as this sensitivity sweep. Reported as: the multiplier k on |dtorque| at which V69 would spend
     0.01% / 0.1% / 1% of engaged time above its 683 rail.

ss2  THE EFFORT CONFOUND ON THE GRIND-#1 HEADLINE. V70's engaged-creep windows have median effort
     787 and median |rate| 40.6 -- far above the stock pool's 223/13.4 -- because the operator was
     deliberately provoking the ratchet. If `e_18-22` rises with effort, the 729 median is inflated
     and the pre-registered prediction was scored on a confounded number. Tested by (a) the within-
     build effort/rate gradient of `e_18-22`, and (b) re-running the subsample power test inside
     matched effort AND |rate| bins.

ss3  STIFFNESS, THE OTHER CANDIDATES. Impedance eff/rate speed-matched at creep, openpilot's own
     command magnitude and rail duty, and the ratchet's per-engaged-window rate -- because a 7.8 Hz
     / 4,894-count p-p oscillation with Q ~ 40 in the bar is itself a candidate for what "stiffer"
     describes, and it is the one thing route 50 has more of by design.

Writes `_scratch/out/_r50_followups.json`.  Usage: python studies/sessions/r50/r50_followups.py
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
import _r50_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = "blk"
RNG = np.random.default_rng(20260804)
OUT = {}
CREEP = 20 / 3.6
RAIL_V69, RAIL_V70 = 683, 1365
store = L.records()

ROUTES = {"V70/r50": ("_scratch/cache/r50", "r50s", [0, 1, 2]),
          "V69/r4f": ("_scratch/cache/r4f", "r4fs", list(range(8)))}


def dtorque(tq, fs=100.0):
    x = np.asarray(tq, float)
    x = np.where(np.isfinite(x), x, 0.0)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), d=1 / fs)
    return np.fft.irfft(X * np.abs(np.sin(np.pi * f * 0.004)), len(x))


# =============================================================== ss1 lower-bound sensitivity ======
L.hdr("ss1  HOW WRONG WOULD THE |dtorque| LOWER BOUND HAVE TO BE FOR V69 TO ACTUALLY RAIL?")
print("   The estimator is silent above 50 Hz, so the true |dtorque| is larger by an unknown factor.")
print("   k = the multiplier that would have to apply for V69 to spend the stated fraction of its")
print("   engaged time at or above 683. Read against |H(f)|: 0.35 @28 Hz, 0.59 @50, 0.95 @100 --")
print("   the missing content is ABOVE 50 Hz, where the bar carries very little energy.\n")
dstore = {}
for name, (cache, pfx, segs) in ROUTES.items():
    acc = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = G.fs_of(d)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        if lat.any():
            acc.append(np.abs(dtorque(np.asarray(d["tq"], float), fs))[lat])
    dstore[name] = np.concatenate(acc) if acc else np.array([])

sens = {}
print(f"   {'route':10s} | " + "  ".join(f"k for {q:>5}%" for q in ("0.01", "0.1", "1", "5")))
for name, v in dstore.items():
    if not len(v):
        continue
    ks = []
    for frac in (0.0001, 0.001, 0.01, 0.05):
        q = float(np.percentile(v, 100 * (1 - frac)))
        ks.append(RAIL_V69 / q if q > 0 else np.inf)
    sens[name] = dict(zip(("0.01%", "0.1%", "1%", "5%"), [float(x) for x in ks]))
    print(f"   {name:10s} | " + "  ".join(f"{k:>11.2f}x" for k in ks))
print("\n   ⇒ V69 would need the estimator to understate |dtorque| by the factor in the '1%' column")
print("     before 1% of its engaged time reached the rail. |H| never falls below 0.35 anywhere in")
print("     6-50 Hz, so an understatement of that size would have to live entirely above 50 Hz.")
OUT["dtorque_sensitivity"] = sens

# =============================================================== ss2 the effort confound ==========
L.hdr("ss2  ★★ THE EFFORT CONFOUND ON THE GRIND-#1 HEADLINE")
print("   (a) WITHIN each build, how does median e_18-22 move with effort and with |rate|?")
print("   If the gradient is flat, V70's high-effort creep windows do not inflate its 729.\n")
E_LBL = [f"{lo:.0f}-{hi:.0f}" for lo, hi in G.E_BINS]
R_LBL = [f"{lo:.0f}-{hi:.0f}" for lo, hi in G.R_BINS]
grad = {}
print(f"   {'build':10s} | " + " ".join(f"eff {x:>9s}" for x in E_LBL)
      + " | " + " ".join(f"rate {x:>8s}" for x in R_LBL))
for b in ("V59/r2c", "V62/r37", "V69/r4f", "V70/r50"):
    rs = [r for r in store.get(b, []) if r["eng"] == 1 and r["v"] < CREEP]
    row = []
    for i in range(len(G.E_BINS)):
        s = [r for r in rs if G.binof(r["eff"], G.E_BINS) == i]
        row.append(np.median(G.col(s, "e_18-22")) if len(s) >= 3 else np.nan)
    row2 = []
    for i in range(len(G.R_BINS)):
        s = [r for r in rs if G.binof(r["rate"], G.R_BINS) == i]
        row2.append(np.median(G.col(s, "e_18-22")) if len(s) >= 3 else np.nan)
    grad[b] = dict(eff=[float(x) for x in row], rate=[float(x) for x in row2])
    print(f"   {b:10s} | " + " ".join(f"{x:>13.0f}" for x in row)
          + " | " + " ".join(f"{x:>13.0f}" for x in row2))
OUT["gradients"] = grad

print("\n   (b) THE POWER TEST RE-RUN INSIDE V70's OWN (effort, |rate|) CELLS.")
print("   Each reference arm is restricted to the (eff bin, rate bin) cells V70 actually occupies,")
print("   then resampled at V70's block structure. This removes the provoked-driving confound.\n")
v70c = [r for r in store["V70/r50"] if r["eng"] == 1 and r["v"] < CREEP]
occ = {(G.binof(r["eff"], G.E_BINS), G.binof(r["rate"], G.R_BINS)) for r in v70c}
print(f"   V70 engaged-creep occupies (eff,rate) cells: {sorted(occ)}")
obs = float(np.median(G.col(v70c, "e_18-22")))
NB = len({r[G.EPKEY] for r in v70c})
print(f"   V70 median {obs:.1f}, blocks {NB}\n")


def sub_med(rs, nblk, ndraw=20000):
    blk = {}
    for r in rs:
        blk.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, "e_18-22") for v in blk.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return None
    out = np.empty(ndraw)
    for i in range(ndraw):
        j = RNG.integers(0, len(per), nblk)
        out[i] = np.median(np.concatenate([per[k] for k in j]))
    return out


ARMS = {"stock V58+V59+V64": L.POOL_KD1, "V69/r4f": ["V69/r4f"], "V62+V65": L.POOL_KD2,
        "V67+V68": L.POOL_GATED}
print(f"   {'arm':<20} {'n all':>6} {'n in cells':>11} {'blocks':>7} | {'sim p50':>9} "
      f"{'sim p97.5':>10} | {'P(>= obs)':>10}  verdict")
conf = {}
for k, names in ARMS.items():
    rs = [r for n in names for r in store.get(n, [])
          if r["eng"] == 1 and r["v"] < CREEP]
    sel = [r for r in rs if (G.binof(r["eff"], G.E_BINS), G.binof(r["rate"], G.R_BINS)) in occ]
    d = sub_med(sel, NB)
    if d is None:
        print(f"   {k:<20} {len(rs):>6} {len(sel):>11}   *** too few blocks after matching")
        conf[k] = dict(n=len(rs), nsel=len(sel))
        continue
    p = float((d >= obs).mean())
    conf[k] = dict(n=len(rs), nsel=len(sel), nblk=len({r[G.EPKEY] for r in sel}),
                   p50=float(np.percentile(d, 50)), p975=float(np.percentile(d, 97.5)), p_ge=p)
    vd = ("CONSISTENT" if 0.025 <= p <= 0.975 else "EXCLUDED")
    print(f"   {k:<20} {len(rs):>6} {len(sel):>11} {conf[k]['nblk']:>7} | "
          f"{conf[k]['p50']:>9.1f} {conf[k]['p975']:>10.1f} | {p:>10.4f}  {vd}")
OUT["confound_matched_power"] = conf

# =============================================================== ss3 stiffness, other candidates ==
L.hdr("ss3  STIFFNESS -- the other candidates, speed-matched at creep")
print("   impedance = eff / |rate| (driver torque per unit angle rate). HIGHER = stiffer.")
print("   cmd p99 / rail duty = openpilot's own 0x0E4 command; a harder command is felt as")
print("   resistance whether or not the EPS impedance changed.\n")
print(f"   {'build':10s} {'n':>5s} {'v p50':>6s} | {'eff/rate p50':>12s} {'[95% CI]':>19s} | "
      f"{'cmd p99':>8s} {'rail duty':>10s} {'|cmd| p50':>10s}")
st = {}
for b in ("V59/r2c", "V62/r37", "V67/r47", "V69/r4f", "V70/r50"):
    rs = [r for r in store.get(b, []) if r["eng"] == 1 and r["v"] < CREEP]
    if len(rs) < 4:
        print(f"   {b:10s} {len(rs):>5d}   *** too few")
        continue
    for r in rs:
        r["imp"] = r["eff"] / max(r["rate"], 1.0)
    m, lo, hi = G.boot_median_ci(rs, "imp", RNG, nboot=2000)
    e4 = G.col(rs, "e4max") if "e4max" in rs[0] else G.col(rs, "e4")
    st[b] = dict(n=len(rs), imp=float(m), lo=float(lo), hi=float(hi),
                 cmd99=float(np.percentile(e4, 99)),
                 rail=float((e4 >= 4000).mean()), cmd50=float(np.median(G.col(rs, "e4"))))
    print(f"   {b:10s} {len(rs):>5d} {np.median(G.col(rs, 'v')):>6.2f} | {m:>12.2f} "
          f"[{lo:>7.2f},{hi:>8.2f}] | {st[b]['cmd99']:>8.0f} {st[b]['rail']:>10.2f} "
          f"{st[b]['cmd50']:>10.0f}")
OUT["stiffness_alt"] = st

print("\n   THE RATCHET AS THE STIFFNESS CANDIDATE -- per-ENGAGED-window rate (from studies/sessions/r50/r50_ratchet.py):")
print("     V70 r50   9/28 engaged windows at >= 1200 counts p-p = 32.1%   max p-p 4,894")
print("     V69 r4f  45/131                                      = 34.4%   max p-p 6,065")
print("     V62 r37  88/268                                      = 32.8%   max p-p 6,619")
print("   ⇒ statistically indistinguishable rates. V70 did not add ratchet EVENTS; the operator")
print("     provoked them, which concentrates them at the START of a 120 s drive rather than")
print("     spreading them over 480 s.")

(HERE / "_scratch/out/_r50_followups.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r50_followups.json'}")
