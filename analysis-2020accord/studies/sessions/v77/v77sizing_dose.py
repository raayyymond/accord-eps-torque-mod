#!/usr/bin/env python3
"""T5 -- extends `studies/sessions/v78/v78_symptom_dose.py`'s damper dose-response ladder with V76/r65 (k=1.3866).

Method is COPIED, not reinvented, from `studies/sessions/v78/v78_symptom_dose.py` DELIVERABLE 2/3 (the log-linear fit of
ln(band-relative-excess) vs damper ramp-gain `k`, CI propagated by resampling each point's own
episode-bootstrap and refitting) -- this file only adds the fifth point and re-runs the identical
fit. V72/V73/V74/V75 come out of `v78_symptom_lib.records()` UNCHANGED (read-only); V76 comes out
of `v77sizing_lib.records()`, this session's own extract.

★ WHY V76 IS THE DECISIVE POINT, NOT JUST A FIFTH DOT: k=1.3866 sits BETWEEN V74 (0.5799) and V75
(1.5798), not beyond V75. A monotone dose-response model makes a SHARP, falsifiable prediction for
where V76 must land relative to the other two -- unlike V75, which only ever extended a 2-point
ladder in one direction.

Usage:  python studies/sessions/v77/v77sizing_dose.py  ->  writes _scratch/out/_v77sizing_dose.json, plots/v77sizing_dose_response.png
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

import v77sizing_lib as V76LIB  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(783003 + 76)
OUT = {}
V.install_fs()
BASE = V.records()                              # V59..V75, READ-ONLY
MINE = V76LIB.records()                          # V76/r65 alone
R = dict(BASE)
R.update(MINE)

PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0], "V76/r65": [0, 10]}
VB = [(0.5, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
LADDER = [("V72/r59", 0.0), ("V73/r5a", 0.0), ("V74/r5d", 0.5799), ("V75/r5e", 1.5798),
          ("V76/r65", V76LIB.K_RAMP_V76)]
CONTEXT = [("V59/r2c", 0.0), ("V62/r37", 0.0), ("V67/r47", 0.0), ("V71C/r58", 0.0)]


def rel_pairs(b, key, eng=1, vhi=12.5):
    o = []
    for r in R[b]:
        if r["seg"] in PARK.get(b, []) or r["eng"] != eng or not (0.5 <= r["v"] < vhi):
            continue
        if r.get("e_24-28", 0) > 0 and np.isfinite(r[key]):
            o.append((r[key] / r["e_24-28"], r["v"], r["ep"]))
    return o


def boot_point(xs, nb=3000):
    """Speed-bin-weighted median of a build's relative excess, episode-resampled."""
    def strat(a):
        num = den = 0.0
        for lo, hi in VB:
            v = [x for x, vv, _ in a if lo <= vv < hi]
            if len(v) < 5:
                continue
            m = np.median(v)
            if m <= 0:
                continue
            num += len(v) * np.log(m)
            den += len(v)
        return np.exp(num / den) if den else np.nan
    ep = {}
    for x in xs:
        ep.setdefault(x[2], []).append(x)
    ks = list(ep)
    if len(ks) < 2:
        return (np.nan,) * 3
    d = np.full(nb, np.nan)
    for i in range(nb):
        d[i] = strat([x for j in RNG.integers(0, len(ks), len(ks)) for x in ep[ks[j]]])
    return float(strat(xs)), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


# ================================================== 1. THE POINTS =================================
V.hdr("T5.1 -- THE EXTENDED DOSE LADDER, both bands, every point with its own episode-bootstrap CI")
print(f"  {'build':<10} {'k':>7} " + f"{'6-9 rel (ratchet)':>26}{'18-22 rel (grind1)':>26}")
pts = {}
for b, k in LADDER + CONTEXT:
    row = dict(k=k, fitted=(b, k) in LADDER)
    cells = []
    for key in ("e_6-9", "e_18-22"):
        row["rel_" + key] = boot_point(rel_pairs(b, key))
        cells.append(f"{row['rel_' + key][0]:6.2f}[{row['rel_' + key][1]:5.2f},"
                     f"{row['rel_' + key][2]:6.2f}]")
    pts[b] = row
    tag = "" if (b, k) in LADDER else "   (context: k=0, different rate lane -- not fitted)"
    print(f"  {b:<10} {k:>7.4f} " + f"{cells[0]:>26}{cells[1]:>26}" + tag)
OUT["points"] = {b: {k: (list(v) if isinstance(v, tuple) else v) for k, v in r.items()}
                 for b, r in pts.items()}

# ================================================== 2. THE FIT ====================================
V.hdr("T5.2 -- LOG-LINEAR FIT  ln(rel.excess) = a + b*k  over the FIVE fitted builds (4 distinct doses)")
print("  Uncertainty is propagated by resampling each point's own bootstrap distribution and")
print("  refitting. V72/V73 (k=0) give the fit its FIRST within-dose replicate; V74/V75/V76 are")
print("  still one route each, so intervals remain optimistic lower bounds on the true uncertainty.\n")


def fit(key, nb=4000):
    ks = np.array([pts[b]["k"] for b, _ in LADDER], float)
    obs = np.array([pts[b][f"rel_{key}"][0] for b, _ in LADDER], float)
    los = np.array([pts[b][f"rel_{key}"][1] for b, _ in LADDER], float)
    his = np.array([pts[b][f"rel_{key}"][2] for b, _ in LADDER], float)
    ok = np.isfinite(obs) & (obs > 0)
    if ok.sum() < 3:
        return None
    sd = (np.log(np.maximum(his, 1e-6)) - np.log(np.maximum(los, 1e-6))) / 3.92
    sd = np.where(np.isfinite(sd) & (sd > 0), sd, 0.5)
    A = np.vstack([np.ones(ok.sum()), ks[ok]]).T
    b0 = np.linalg.lstsq(A, np.log(obs[ok]), rcond=None)[0]
    draws = np.full((nb, 2), np.nan)
    for i in range(nb):
        y = np.log(obs[ok]) + RNG.normal(0, sd[ok])
        draws[i] = np.linalg.lstsq(A, y, rcond=None)[0]
    return dict(a=float(b0[0]), b=float(b0[1]),
                b_lo=float(np.percentile(draws[:, 1], 2.5)),
                b_hi=float(np.percentile(draws[:, 1], 97.5)),
                draws=draws, ks=ks[ok], obs=obs[ok], sd=sd[ok])


fits = {}
print(f"  {'band':<12} {'slope d ln(y)/dk':>28} {'per-unit-k factor':>22}  {'dB per unit k':>14}"
      f"  {'slope CI contains 0?':>22}")
for key, lab in (("e_6-9", "6-9 (ratchet)"), ("e_18-22", "18-22 (grind1)")):
    f = fit(key)
    if f is None:
        print(f"  {lab:<12}   -- not enough finite points")
        continue
    fits[key] = {kk: vv for kk, vv in f.items() if kk not in ("draws", "ks", "obs", "sd")}
    fits[key]["ks"] = [float(x) for x in f["ks"]]
    fits[key]["obs"] = [float(x) for x in f["obs"]]
    zero_in = f["b_lo"] <= 0.0 <= f["b_hi"]
    print(f"  {lab:<12} {f['b']:9.3f} [{f['b_lo']:8.3f}, {f['b_hi']:8.3f}] "
          f"{np.exp(f['b']):>10.3f}x/unit        {20 * np.log10(np.exp(f['b'])):>8.2f} dB"
          f"  {'YES -- ' + ('' if zero_in else '') + str(zero_in):>22}")
    fits[key]["_draws"] = f["draws"]
OUT["fits"] = {k: {kk: vv for kk, vv in v.items() if kk != "_draws"} for k, v in fits.items()}

# ================================================== 3. GOODNESS OF FIT AT V76 =======================
V.hdr("T5.3 -- ★★★ DOES V76 SIT WHERE A MONOTONE DOSE MODEL PREDICTS?  (k=1.3866, BETWEEN V74 and V75)")
print("  If the creep symptom is DOSE-LIMITED, V76's point must land between V74's and V75's, close")
print("  to the V74-V75 straight-line interpolation at k=1.3866. If it does NOT -- if V76 is worse")
print("  than V75 despite a LOWER k, or no better than V74 despite a HIGHER k -- the residual is")
print("  dose-independent at this k, and more dose (V77's plan) will not obviously help.\n")
resid = {}
for key, lab in (("e_6-9", "MICRO RATCHET (6-9 Hz)"), ("e_18-22", "GRIND #1 (18-22 Hz)")):
    v74 = pts["V74/r5d"][f"rel_{key}"][0]
    v75 = pts["V75/r5e"][f"rel_{key}"][0]
    v76 = pts["V76/r65"][f"rel_{key}"]
    k74, k75, k76 = 0.5799, 1.5798, V76LIB.K_RAMP_V76
    # straight-line (in log space) interpolation between the two flown endpoints, evaluated at k76
    if v74 > 0 and v75 > 0:
        frac = (k76 - k74) / (k75 - k74)
        pred_log = np.log(v74) + frac * (np.log(v75) - np.log(v74))
        pred = float(np.exp(pred_log))
    else:
        pred = np.nan
    print(f"  {lab}")
    print(f"     V74 (k={k74})  {v74:7.3f}")
    print(f"     V75 (k={k75})  {v75:7.3f}")
    print(f"     V76 (k={k76:.4f})  OBSERVED {v76[0]:7.3f} [{v76[1]:.3f}, {v76[2]:.3f}]   "
          f"MONOTONE-INTERPOLATION PREDICTS {pred:7.3f}")
    if np.isfinite(pred):
        off_db = 20 * np.log10(v76[0] / pred) if pred > 0 else np.nan
        verdict = ("CONSISTENT with a monotone dose model" if v76[1] <= pred <= v76[2]
                   else "INCONSISTENT -- the monotone interpolation falls OUTSIDE V76's own CI")
        print(f"     offset from prediction: {off_db:+.2f} dB   ⇒ {verdict}")
        resid[key] = dict(v74=v74, v75=v75, v76_obs=list(v76), v76_pred=pred, offset_db=off_db,
                          consistent=bool(v76[1] <= pred <= v76[2]))
    print()
OUT["v76_vs_interpolation"] = resid

# ================================================== 4. THE OPERATOR'S QUESTION, DIRECTLY ============
V.hdr("T5.4 -- ★★★★ IS THE CREEP SYMPTOM DOSE-LIMITED OR DOSE-INDEPENDENT?  (the decisive question)")
for key, lab in (("e_6-9", "MICRO RATCHET"), ("e_18-22", "GRIND #1")):
    f = fits.get(key)
    if f is None:
        continue
    zero_in = f["b_lo"] <= 0.0 <= f["b_hi"]
    print(f"  {lab:<16}  fitted slope d ln(rel)/dk = {f['b']:+.3f} [{f['b_lo']:+.3f}, {f['b_hi']:+.3f}]")
    if zero_in:
        print(f"    🛑 THE SLOPE'S CI CONTAINS ZERO. Across the fitted ladder (k=0, 0, 0.58, 1.58, "
              f"{V76LIB.K_RAMP_V76:.2f}), there is NO statistically resolved trend with dose.")
        print(f"    ⇒ On this evidence, MORE DAMPER DOSE IS NOT SHOWN TO HELP {lab} at creep.")
    else:
        direction = "DECREASES" if f["b"] < 0 else "INCREASES"
        print(f"    The slope is resolved (CI excludes 0): rel.excess {direction} with k.")
    OUT.setdefault("verdict", {})[key] = dict(slope=f["b"], lo=f["b_lo"], hi=f["b_hi"],
                                              zero_in_ci=bool(zero_in))
print("\n  ⚠ Read this WITH T5.3 above, not instead of it: a flat fitted slope across 5 points that")
print("  spans two different builds' worth of route noise is a WEAK dose-response test on its own.")
print("  The V76-vs-interpolation residual (T5.3) is the sharper, single-point falsification: V76's")
print("  k sits BETWEEN V74 and V75, so if it does not land between their measured values, that one")
print("  comparison is doing more work than the 5-point regression's wide CI can show.")

# ================================================== 5. PLOT ========================================
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    (ROOT / "analysis-2020accord" / "plots").mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
    for i, (key, klab, col) in enumerate((("e_6-9", "MICRO RATCHET 6-9 Hz", "#c2410c"),
                                          ("e_18-22", "GRIND #1 18-22 Hz", "#1d4ed8"))):
        ax = axs[i]
        for b, k in LADDER:
            p, lo, hi = pts[b][f"rel_{key}"]
            ax.errorbar(k, p, yerr=[[max(p - lo, 0)], [max(hi - p, 0)]], fmt="o", color=col,
                        capsize=3, ms=6)
            ax.annotate(b.split("/")[0], (k, p), textcoords="offset points", xytext=(6, 6),
                       fontsize=8)
        for b, k in CONTEXT:
            p = pts[b][f"rel_{key}"][0]
            if np.isfinite(p):
                ax.plot(k, p, "x", color="#9ca3af", ms=6)
        f = fits.get(key)
        if f is not None:
            xs = np.linspace(0, 1.8, 60)
            ax.plot(xs, np.exp(f["a"] + f["b"] * xs), "-", color=col, lw=1.2, alpha=0.8)
            dr = f["_draws"]
            band = np.array([np.percentile(np.exp(dr[:, 0] + dr[:, 1] * x), [2.5, 97.5]) for x in xs])
            ax.fill_between(xs, band[:, 0], band[:, 1], color=col, alpha=0.12)
        ax.axvline(0.5799, ls=":", c="#16a34a", lw=1)
        ax.axvline(1.5798, ls=":", c="#dc2626", lw=1)
        ax.axvline(V76LIB.K_RAMP_V76, ls="--", c="#7c3aed", lw=1.4)
        ax.set_yscale("log")
        ax.set_xlabel("damper ramp gain  k")
        ax.set_ylabel("band / 24-28 Hz control")
        ax.set_title(f"{klab}", fontsize=9)
        ax.grid(alpha=0.25, which="both")
    fig.suptitle("V76 dose-response check.  green=V74 (0.58)  red=V75 (1.58, FAULTED)  "
                "purple=V76 (1.39, BETWEEN them)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(ROOT / "analysis-2020accord" / "plots" / "v77sizing_dose_response.png", dpi=130)
    print("\nwrote plots/v77sizing_dose_response.png")
except Exception as e:                                            # noqa: BLE001
    print(f"(plot skipped: {e})")

with open(ROOT / "_scratch/out/_v77sizing_dose.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("wrote _scratch/out/_v77sizing_dose.json")
