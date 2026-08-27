#!/usr/bin/env python3
"""DELIVERABLE 3 -- the damper dose-response in `k`, and the `k` the ratchet target would need.

`k = (FactorC_Y[0] * FactorE_Y[1] >> 10) / (E_X1 - E_X0)` is the damper's ramp-regime incremental
gain: a frequency-independent scalar on the whole damper path, so it is the only defensible dose
axis (`docs/handoffs/2026-08/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md` §3).

🛑🛑 THE LADDER HAS THREE DISTINCT DOSES AND TWO OF THEM ARE n = 1 ROUTE.
    k = 0.0000   V72/r59, V73/r5a          (damper present but mode-indexed inert -- RULE 7)
    k = 0.5799   V74/r5d                   n = 1 route, 19 engagement episodes
    k = 1.5798   V75/r5e                   n = 1 route,  6 engagement episodes, pre-fault only
    (the pre-V72 corpus is ALSO k = 0 but differs in the RATE lane, so it is plotted and NOT fitted --
     mixing it in would attribute rate-lane differences to the damper.)
A two-parameter fit through three doses with one route each is the weakest form of evidence this kit
uses. Every number below carries that. The inverted design `k` is reported as an INTERVAL and, where
the slope's own interval contains zero, as UNBOUNDED -- which is a real answer, not a failure.

Two response axes, because they disagree and the disagreement is the finding:
  * band-relative excess over the 24-28 Hz control, speed-matched  -- the AMPLITUDE axis;
  * limit-cycle DUTY at T = 600 counts, engaged creep, span 8-200  -- the ONSET axis, which
    `studies/sessions/r5d/r5d_duty.py` established is the right headline for grind #1 (duty spans 64x, in-burst 1.24x).

Usage:  python studies/sessions/v78/v78_symptom_dose.py   ->  writes _scratch/out/_v78_dose.json, plots/v78_dose_response.png
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(783003)
OUT = {}
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0]}
VB = [(0.5, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
LADDER = [("V72/r59", 0.0), ("V73/r5a", 0.0), ("V74/r5d", 0.5799), ("V75/r5e", 1.5798)]
CONTEXT = [("V59/r2c", 0.0), ("V62/r37", 0.0), ("V67/r47", 0.0), ("V71C/r58", 0.0)]
V.install_fs()
R = V.records()


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


# ------------------------------------------------------------------ the duty axis ----------------
G.EPKEY = "blk"
SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
with open(ROOT / "_scratch/data/_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)
with open(ROOT / "_scratch/data/_cache_r5e_sym_nearcentre.pkl", "rb") as fh:
    store.update(pickle.load(fh))
for b in store:
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["sb"] = G.binof(r["span"], SP)
ACT = {b: [r for r in N.eng_creep(store[b]) if r["sb"] in (2, 3, 4)] for b in store}
T = 600.0


def duty_point(b, key, nb=3000):
    rs = ACT.get(b, [])
    ep = {}
    for r in rs:
        ep.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, key) for v in ep.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return (np.nan,) * 3
    allv = np.concatenate(per)
    d = np.full(nb, np.nan)
    for i in range(nb):
        v = np.concatenate([per[j] for j in RNG.integers(0, len(per), len(per))])
        d[i] = float(np.mean(v >= T))
    return (float(np.mean(allv >= T)), float(np.nanpercentile(d, 2.5)),
            float(np.nanpercentile(d, 97.5)))


# ================================================== 1. THE POINTS =================================
V.hdr("1. THE DOSE LADDER -- both response axes, every point with its own episode-bootstrap CI")
print(f"  {'build':<10} {'k':>7} " + f"{'6-9 rel':>24}{'18-22 rel':>24}"
      f"{'6-9 duty':>22}{'18-22 duty':>22}")
pts = {}
for b, k in LADDER + CONTEXT:
    row = dict(k=k, fitted=(b, k) in LADDER)
    cells = []
    for key in ("e_6-9", "e_18-22"):
        row["rel_" + key] = boot_point(rel_pairs(b, key))
        cells.append(f"{row['rel_' + key][0]:6.2f}[{row['rel_' + key][1]:5.2f},"
                     f"{row['rel_' + key][2]:6.2f}]")
    for key in ("e_6-9", "e_18-22"):
        row["duty_" + key] = duty_point(b, key)
        cells.append(f"{row['duty_' + key][0]:6.3f}[{row['duty_' + key][1]:5.3f},"
                     f"{row['duty_' + key][2]:6.3f}]")
    pts[b] = row
    tag = "" if (b, k) in LADDER else "   (context: k=0 but a DIFFERENT rate lane -- not fitted)"
    print(f"  {b:<10} {k:>7.4f} " + f"{cells[0]:>24}{cells[1]:>24}{cells[2]:>22}{cells[3]:>22}"
          + tag)
OUT["points"] = {b: {k: (list(v) if isinstance(v, tuple) else v) for k, v in r.items()}
                 for b, r in pts.items()}

# ================================================== 2. THE FIT ====================================
V.hdr("2. LOG-LINEAR FIT  ln(response) = a + b*k  over the FOUR fitted builds (3 distinct doses)")
print("  🛑 Uncertainty is propagated by resampling each build's own bootstrap distribution and")
print("  refitting -- so the slope's interval carries the per-route CIs, but NOT route-to-route")
print("  variance at a given dose, because at k = 0.58 and k = 1.58 there is only ONE route each.")
print("  ⇒ the intervals below are LOWER BOUNDS on the true uncertainty. Treat them as optimistic.\n")


def fit(axis, key, nb=4000):
    ks = np.array([pts[b]["k"] for b, _ in LADDER], float)
    obs = np.array([pts[b][f"{axis}_{key}"][0] for b, _ in LADDER], float)
    los = np.array([pts[b][f"{axis}_{key}"][1] for b, _ in LADDER], float)
    his = np.array([pts[b][f"{axis}_{key}"][2] for b, _ in LADDER], float)
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
print(f"  {'axis':<10} {'band':<10} {'slope d ln(y)/dk':>28} {'per-unit-k factor':>22}  "
      f"{'dB per unit k':>14}")
for axis in ("rel", "duty"):
    for key in ("e_6-9", "e_18-22"):
        f = fit(axis, key)
        if f is None:
            print(f"  {axis:<10} {key:<10}   -- not enough finite points")
            continue
        fits[f"{axis}|{key}"] = {kk: vv for kk, vv in f.items()
                                 if kk not in ("draws", "ks", "obs", "sd")}
        fits[f"{axis}|{key}"]["ks"] = [float(x) for x in f["ks"]]
        fits[f"{axis}|{key}"]["obs"] = [float(x) for x in f["obs"]]
        print(f"  {axis:<10} {key:<10} {f['b']:9.3f} [{f['b_lo']:8.3f}, {f['b_hi']:8.3f}] "
              f"{np.exp(f['b']):>10.3f}x/unit        {20 * np.log10(np.exp(f['b'])):>8.2f} dB")
        fits[f"{axis}|{key}"]["_draws"] = f["draws"]
OUT["fits"] = {k: {kk: vv for kk, vv in v.items() if kk != "_draws"} for k, v in fits.items()}

# ================================================== 3. THE INVERSION ==============================
V.hdr("3. ★★ THE DESIGN NUMBER -- the `k` that would bring the ratchet to the target, and its CI")
print("  TARGET, and it is an ASSUMPTION [BELIEF]: the level at which the operator declared a band")
print("  imperceptible is V75's own 18-22 Hz reading. On the amplitude axis that is a relative")
print("  excess of 1.53; on the duty axis it is 0.034. The assumption is that the same numerical")
print("  level means 'gone' at 7.8 Hz as at 21 Hz. It is NOT calibrated -- 21 Hz is audible and")
print("  7.8 Hz is felt, and their thresholds could differ in either direction.\n")
inv = {}
for axis, tgt_key, lab in (("rel", "e_18-22", "relative excess"), ("duty", "e_18-22", "duty")):
    f = fits.get(f"{axis}|e_6-9")
    if f is None:
        continue
    tgt = pts["V75/r5e"][f"{axis}_{tgt_key}"][0]
    cur = pts["V75/r5e"][f"{axis}_e_6-9"][0]
    need_db = 20 * np.log10(cur / tgt)
    dr = f["_draws"]
    kneed = (np.log(tgt) - dr[:, 0]) / np.where(np.abs(dr[:, 1]) > 1e-9, dr[:, 1], np.nan)
    kneed = np.where(dr[:, 1] < 0, kneed, np.nan)          # a POSITIVE slope cannot reach the target
    frac_bad = float(np.mean(~np.isfinite(kneed)))
    kk = kneed[np.isfinite(kneed)]
    lo, hi = (np.percentile(kk, [2.5, 97.5]) if len(kk) > 50 else (np.nan, np.nan))
    kpt = (np.log(tgt) - f["a"]) / f["b"] if f["b"] < 0 else np.inf
    inv[axis] = dict(target=float(tgt), current=float(cur), need_db=float(need_db),
                     k_point=float(kpt), k_lo=float(lo), k_hi=float(hi), frac_unreachable=frac_bad)
    print(f"  --- {lab} axis ---")
    print(f"     ratchet on V75      {cur:8.3f}")
    print(f"     target (V75's 18-22){tgt:8.3f}")
    print(f"     further attenuation needed: {need_db:+.2f} dB  "
          f"({cur / tgt:.2f}x)")
    print(f"     fitted slope d ln(6-9)/dk = {f['b']:+.3f} [{f['b_lo']:+.3f}, {f['b_hi']:+.3f}]")
    print(f"     ⇒ k required = {kpt:8.3f}   95% interval [{lo:8.3f}, {hi:8.3f}]")
    print(f"     🛑 {100 * frac_bad:.1f}% of the refits have a slope that is ZERO OR POSITIVE, i.e."
          f" they never reach the target at ANY k.")
    print(f"     for scale: V74 k = 0.5799 (flew clean), V75 k = 1.5798 (FAULTED), "
          f"new cut k = {V.K_NEWCUT}.")
    print(f"     the stability bracket from the two flights is k* in (0.580, 1.580].\n")
OUT["inversion"] = inv

# ================================================== 3b. THE BUILT NEW CUT =========================
V.hdr("3b. ★★ WHAT THE FIT PREDICTS FOR THE BUILT, UNFLASHED NEW CUT  (C_Y0 566, E_X1 400, k=0.7655)")
print("  This is an interpolation between two flown points, not an extrapolation, so it is the")
print("  strongest prediction the ladder supports. It still rests on n = 1 route at each endpoint.")
print("  ⚠ AND ON ONE MORE THING: `k` conflates the two edits V74->V75 made. V75 raised C_Y0")
print("  429->566 AND lowered E_X1 400->200, which also widened the bang-bang relay band from")
print("  85-531 to 42-531 deg/s. The new cut keeps E_X1 = 400, so it moves only the first. If any")
print("  part of V75's grind result came from the relay band rather than from k, the prediction")
print("  below is optimistic.\n")
pred = {}
for axis, band, lab in (("rel", "e_18-22", "GRIND #1 relative excess"),
                        ("rel", "e_6-9", "MICRO RATCHET relative excess"),
                        ("duty", "e_18-22", "GRIND #1 creep duty"),
                        ("duty", "e_6-9", "MICRO RATCHET creep duty")):
    f = fits.get(f"{axis}|{band}")
    if f is None:
        continue
    vals = {kk: float(np.exp(f["a"] + f["b"] * kk))
            for kk in (0.0, 0.5799, V.K_NEWCUT, 1.5798)}
    d = V.K_NEWCUT - 1.5798
    fac = float(np.exp(f["b"] * d))
    flo, fhi = float(np.exp(f["b_hi"] * d)), float(np.exp(f["b_lo"] * d))
    pred[f"{axis}|{band}"] = dict(vals=vals, vs_v75=fac, vs_v75_lo=min(flo, fhi),
                                  vs_v75_hi=max(flo, fhi))
    print(f"  {lab:<30} k=0 {vals[0.0]:7.3f} · V74 {vals[0.5799]:7.3f} · "
          f"NEW {vals[V.K_NEWCUT]:7.3f} · V75 {vals[1.5798]:7.3f}")
    print(f"  {'':<30} ⇒ new cut is {fac:5.2f}x [{min(flo, fhi):.2f}, {max(flo, fhi):.2f}] "
          f"V75's level (>1 = worse)")
OUT["newcut_prediction"] = pred

# ================================================== 4. PLOT =======================================
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    (ROOT / "analysis-2020accord" / "plots").mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.2))
    for j, (axis, alab) in enumerate((("rel", "band / 24-28 Hz control"),
                                      ("duty", "limit-cycle duty (T=600)"))):
        for i, (key, klab, col) in enumerate(((
                "e_6-9", "MICRO RATCHET 6-9 Hz", "#c2410c"),
                ("e_18-22", "GRIND #1 18-22 Hz", "#1d4ed8"))):
            ax = axs[i][j]
            for b, k in LADDER:
                p, lo, hi = pts[b][f"{axis}_{key}"]
                ax.errorbar(k, p, yerr=[[max(p - lo, 0)], [max(hi - p, 0)]], fmt="o", color=col,
                            capsize=3, ms=6)
                ax.annotate(b.split("/")[0], (k, p), textcoords="offset points",
                            xytext=(6, 6), fontsize=8)
            for b, k in CONTEXT:
                p = pts[b][f"{axis}_{key}"][0]
                if np.isfinite(p):
                    ax.plot(k, p, "x", color="#9ca3af", ms=6)
            f = fits.get(f"{axis}|{key}")
            if f is not None:
                xs = np.linspace(0, 3.4, 60)
                ax.plot(xs, np.exp(f["a"] + f["b"] * xs), "-", color=col, lw=1.2, alpha=0.8)
                dr = f["_draws"]
                band = np.array([np.percentile(np.exp(dr[:, 0] + dr[:, 1] * x), [2.5, 97.5])
                                 for x in xs])
                ax.fill_between(xs, band[:, 0], band[:, 1], color=col, alpha=0.12)
            ax.axvline(0.5799, ls=":", c="#16a34a", lw=1)
            ax.axvline(1.5798, ls=":", c="#dc2626", lw=1)
            ax.axvline(V.K_NEWCUT, ls="--", c="#6b7280", lw=1)
            ax.set_yscale("log")
            if axis == "duty":
                ax.set_ylim(8e-3, 1.6)     # duty is a fraction; CIs touching 0 destroy a log axis
            ax.set_xlabel("damper ramp gain  k")
            ax.set_ylabel(alab)
            ax.set_title(f"{klab}  --  {alab}", fontsize=9)
            ax.grid(alpha=0.25, which="both")
    fig.suptitle("V78 -- damper dose-response.  3 distinct doses, n=1 route at k=0.58 and k=1.58.\n"
                 "green = V74 (flew clean)   red = V75 (FAULTED)   dashed = new cut k=0.766",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(ROOT / "analysis-2020accord" / "plots" / "v78_dose_response.png", dpi=130)
    print("wrote plots/v78_dose_response.png")
except Exception as e:                                            # noqa: BLE001
    print(f"(plot skipped: {e})")

with open(ROOT / "_scratch/out/_v78_dose.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("wrote _scratch/out/_v78_dose.json")
