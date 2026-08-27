#!/usr/bin/env python3
r"""FINAL measurement of the 2020 Accord's steering ratio vs steering-wheel angle.

🛑🛑 THE PRE-REGISTERED POSITIVE CONTROL -- "the ratio must come out FLAT beyond 120 deg" --
     FAILS, AND WHAT IT REFUTES IS ITS OWN PREMISE, NOT THE INSTRUMENT.
     The rack does NOT stop quickening at 120 deg.  Four estimators with DISJOINT physical
     dependencies all show the local ratio still falling from ~13.8 at 120 deg to ~11.3 at 380 deg;
     the ONLY estimator that returns a flat plateau is the one built on openpilot's `vEgo`, and
     `vEgo` is a FOUR-WHEEL average whose front pair runs at v/cos(delta) -- a bias that grows with
     steering angle and is therefore exactly shaped to FAKE a plateau.

     THE FOUR ESTIMATORS AND WHAT EACH ONE NEEDS:
       A  delta = atan(yaw_IMU * L / v_rear)          IMU yaw  +  REAR wheel pair
       D  delta = asin(yaw_IMU * L / v_front)         IMU yaw  +  FRONT wheel pair   (no rear)
       C  delta = acos(v_rear / v_front)              wheel speeds ONLY -- no IMU, no yaw, no L,
                                                      no track, no vEgo.  Valid only |theta| >~ 60.
       B  delta = atan(yaw_rear_diff * L / v_rear)    rear differential yaw (no IMU at all)
     A and D share no wheel pair.  C shares no yaw source with A/B/D.  They agree to 0.3-3 %.

     ⊕ INDEPENDENT ANCHOR ON THE ABSOLUTE SCALE.  Extrapolating the measured curve to full lock
       (~450 deg) gives delta_max = 35.1 deg (A) / 36.4 deg (C).  The published 37.4 ft curb-to-curb
       turning circle implies delta_max ~ 35 deg.  The vEgo estimator gives 31.0 deg and misses it.
       [BELIEF -- the 37.4 ft figure is from the published spec, not measured here.]

⇒ Because there is NO plateau, the curve is normalised at 120 deg -- the angle at which the
  FIRMWARE's own table saturates -- so "measured vs firmware" is a like-for-like comparison.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import measure_steering_ratio as M  # noqa: E402
import ratio_lib as R  # noqa: E402

OUT = R.ROOT / "analysis-2020accord" / "_scratch/cache/ratio"
F = {}

FLOOR_LO, FLOOR_HI = 3.0, 50.0     # the measured FLAT FLOOR
REF_LO, REF_HI = 105.0, 165.0      # normalisation window, straddling the firmware's 120 deg knot
FWX = np.array([0, 34, 64, 85, 100, 120, 477.6])
FWY = np.array([899, 908, 981, 1060, 1083, 1084, 1084]) / 1084.0


def gamma_front_rear(A):
    """Front/rear wheel-radius calibration: v_front/v_rear on STRAIGHT driving, where it must
    be 1 by geometry.  Any departure is tyre-radius mismatch between the axles."""
    st = R.base_mask(A, vmin=8.0, vmax=40.0) & (np.abs(A["yawA0"]) < 0.01) & R.steady_mask(A)
    return float(np.median((A["v_front"] / A["v_ref"])[st]))


def deltas(A, gam):
    """All four road-wheel-angle estimators, signed, in degrees."""
    y, vr, vf = A["yawA0"], A["v_ref"], A["v_front"] / gam
    D = {}
    D["A"] = np.degrees(np.arctan(y * R.L_WB / vr))
    D["D"] = np.degrees(np.arcsin(np.clip(y * R.L_WB / vf, -1, 1)))
    D["B"] = np.degrees(np.arctan(A["yawB0"] * R.L_WB / vr))
    with np.errstate(invalid="ignore", divide="ignore"):
        D["C"] = np.sign(y) * np.degrees(np.arccos(np.clip(vr / vf, -1, 1)))
    D["vEgo_BIASED"] = np.degrees(np.arctan(y * R.L_WB / A["s_v"]))
    return D


def _blocks(blk):
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    b = np.searchsorted(inv[order], np.arange(len(ub) + 1))
    return [order[b[i]:b[i + 1]] for i in range(len(ub))]


def stats(th, loc):
    fl = np.nanmedian(loc[(th >= FLOOR_LO) & (th < FLOOR_HI)])
    rf = np.nanmedian(loc[(th >= REF_LO) & (th < REF_HI)])
    out = np.nanmedian(loc[th >= 320.0])
    return {"floor": float(fl), "ref120": float(rf), "outer": float(out),
            "swing_0_to_120": float(fl / rf),
            "droop_120_to_380": float(rf / out) if np.isfinite(out) else np.nan}


def boot(A, m, th0, dlt, nboot=1200, seed=101, extra=None):
    th_c = A["s_ang"][m] - th0
    d = dlt[m]
    by = _blocks(A["blk"][m])
    c = M.curve_from(th_c, d, M.BINS)
    pt = stats(c[0], c[2])
    if extra:
        pt |= extra(c[0], c[2])
    rng = np.random.default_rng(seed)
    acc = {k: [] for k in pt}
    for _ in range(nboot):
        sel = np.concatenate([by[p] for p in rng.integers(0, len(by), len(by))])
        cc = M.curve_from(th_c[sel], d[sel], M.BINS)
        s = stats(cc[0], cc[2])
        if extra:
            s |= extra(cc[0], cc[2])
        for k, x in s.items():
            if np.isfinite(x):
                acc[k].append(x)
    o = {k: {"point": float(pt[k]),
             "ci95": [float(np.percentile(acc[k], 2.5)), float(np.percentile(acc[k], 97.5))]}
         for k in pt if len(acc[k]) > 20}
    o["n_blocks"] = len(by); o["seconds"] = float(m.sum() * R.DT)
    return o


def curve(A, m, th0, dlt, nboot=800, seed=7):
    th_c = A["s_ang"][m] - th0
    d = dlt[m]
    by = _blocks(A["blk"][m])
    ta, sec, loc, nn = M.curve_from(th_c, d, M.BINS)
    ref = np.nanmedian(loc[(ta >= REF_LO) & (ta < REF_HI)])
    rng = np.random.default_rng(seed)
    LN = []
    for _ in range(nboot):
        sel = np.concatenate([by[p] for p in rng.integers(0, len(by), len(by))])
        t2, _, l2, _ = M.curve_from(th_c[sel], d[sel], M.BINS)
        LN.append(l2 / np.nanmedian(l2[(t2 >= REF_LO) & (t2 < REF_HI)]))
    LN = np.array(LN)
    with np.errstate(invalid="ignore"):
        lo, hi = np.nanpercentile(LN, 2.5, axis=0), np.nanpercentile(LN, 97.5, axis=0)
    return {"theta": ta.tolist(), "n_bin": nn.tolist(), "local": loc.tolist(),
            "secant": sec.tolist(), "ref120": float(ref),
            "local_norm": (loc / ref).tolist(),
            "local_norm_lo": lo.tolist(), "local_norm_hi": hi.tolist()}


def main():
    A = M.prep()
    M.qa(A)
    A["v_front"] = R.smooth_blocks(A, 0.5 * (A["ws_fl"] + A["ws_fr"]), 0.5)
    gam = gamma_front_rear(A)
    th0 = M.fit_theta0(A, "A")
    F["gamma_front_rear"] = gam
    F["theta0"] = th0
    print(f"\n  front/rear wheel-radius calibration gamma = {gam:.5f} (straight driving)")

    D = deltas(A, gam)
    prim = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A)

    print("\n" + "=" * 96)
    print("  ⭐ FOUR ESTIMATORS, DISJOINT DEPENDENCIES -- this replaces the failed flatness control")
    print("=" * 96)
    F["estimators"] = {}
    for k in ("A", "D", "B", "C", "vEgo_BIASED"):
        mm = prim if k not in ("C",) else (prim & (np.abs(A["s_ang"] - th0) >= 60))
        if k == "B":
            mm = prim & (A["v_ref"] > 2.0)
        b = boot(A, mm, th0, D[k], nboot=800, seed=101)
        F["estimators"][k] = b
        f = b.get("floor", {}); r = b["ref120"]; o = b["outer"]
        sw = b.get("swing_0_to_120"); dr = b["droop_120_to_380"]
        print(f"\n  {k:12s} {b['seconds']:6.0f} s / {b['n_blocks']} blocks")
        print(f"     ratio at 120 deg   = {r['point']:6.2f} [{r['ci95'][0]:.2f}, {r['ci95'][1]:.2f}]"
              f"      ratio at 320-400  = {o['point']:6.2f} "
              f"[{o['ci95'][0]:.2f}, {o['ci95'][1]:.2f}]")
        if sw:
            print(f"     floor(3-50)        = {f['point']:6.2f} "
                  f"[{f['ci95'][0]:.2f}, {f['ci95'][1]:.2f}]"
                  f"      SWING 0->120     = {sw['point']:6.3f} "
                  f"[{sw['ci95'][0]:.3f}, {sw['ci95'][1]:.3f}]")
        print(f"     further droop 120->380 = {dr['point']:.3f} "
              f"[{dr['ci95'][0]:.3f}, {dr['ci95'][1]:.3f}]   "
              f"(firmware says this is 1.000 -- FLAT)")

    print("\n=== THE CURVE (estimator A) vs THE FIRMWARE TABLE 0xC6B64 ===")
    c = curve(A, prim, th0, D["A"], nboot=800)
    F["curve"] = c
    fw = np.interp(np.array(c["theta"], float), FWX, 1.0 / FWY)
    print("   |th| deg      n   MEASURED ratio/ratio(120)  [95% CI]    FIRMWARE implied   fw-meas")
    for i, t in enumerate(c["theta"]):
        if not np.isfinite(t):
            continue
        print(f"  {t:8.1f} {c['n_bin'][i]:7d}      {c['local_norm'][i]:7.3f} "
              f"[{c['local_norm_lo'][i]:6.3f},{c['local_norm_hi'][i]:6.3f}]        "
              f"{fw[i]:7.3f}        {fw[i] - c['local_norm'][i]:+7.3f}")

    print("\n=== STRATA (swing 0->120, estimator A) ===")
    F["strata"] = {}
    for lab, mm in (("v 1.0-2.5", R.base_mask(A, vmin=1.0, vmax=2.5) & R.steady_mask(A)),
                    ("v 2.5-3.5", R.base_mask(A, vmin=2.5, vmax=3.5) & R.steady_mask(A)),
                    ("v 3.5-5.0", R.base_mask(A, vmin=3.5, vmax=5.0) & R.steady_mask(A)),
                    ("LEFT", prim & (A["s_ang"] - th0 > 0)),
                    ("RIGHT", prim & (A["s_ang"] - th0 < 0)),
                    ("ENGAGED", prim & (A["lat"] > 0.5)),
                    ("MANUAL", prim & (A["lat"] < 0.5)),
                    ("hands ON", prim & (A["press"] > 0.5)),
                    ("hands OFF", prim & (A["press"] < 0.5))):
        if mm.sum() < 1500:
            print(f"  {lab:12s}: {mm.sum() * R.DT:6.0f} s -- NO POWER")
            continue
        b = boot(A, mm, th0, D["A"], nboot=500, seed=103)
        F["strata"][lab] = b
        dr = (f"{b['droop_120_to_380']['point']:.3f}" if "droop_120_to_380" in b
              else "  n/a")   # some strata have no exposure beyond 320 deg
        print(f"  {lab:12s}: {b['seconds']:6.0f} s  floor {b['floor']['point']:6.2f}  "
              f"ref120 {b['ref120']['point']:6.2f}  swing {b['swing_0_to_120']['point']:.3f} "
              f"{np.round(b['swing_0_to_120']['ci95'], 3).tolist()}  droop120-380 {dr}")

    print("\n=== SENSITIVITY of swing(0->120), estimator A ===")
    F["sensitivity"] = {}
    for lab, t0, LL in (("theta0 -3.25", th0 + 1.0, R.L_WB), ("theta0 -5.25", th0 - 1.0, R.L_WB),
                        ("theta0  0.00", 0.0, R.L_WB), ("L = 2.75", th0, 2.75),
                        ("L = 2.91", th0, 2.91)):
        dd = np.degrees(np.arctan(A["yawA0"] * LL / A["v_ref"]))
        b = boot(A, prim, t0, dd, nboot=400, seed=31)
        F["sensitivity"][lab] = b
        print(f"  {lab:14s} swing {b['swing_0_to_120']['point']:.4f} "
              f"{np.round(b['swing_0_to_120']['ci95'], 4).tolist()}   droop "
              f"{b.get('droop_120_to_380', {}).get('point', float('nan')):.3f}")
    for rm, dm in ((10.0, 0.15), (60.0, 1.0)):
        mm = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A, rate_max=rm, dyaw_max=dm)
        b = boot(A, mm, th0, D["A"], nboot=400, seed=31)
        F["sensitivity"][f"rate<{rm}"] = b
        print(f"  steady rate<{rm:<4.0f}  swing {b['swing_0_to_120']['point']:.4f} "
              f"{np.round(b['swing_0_to_120']['ci95'], 4).tolist()}   droop "
              f"{b.get('droop_120_to_380', {}).get('point', float('nan')):.3f}   "
              f"({b['seconds']:.0f} s)")

    # ---- extrapolation to full lock, against the published turning circle
    ta = np.array(c["theta"], float); loc = np.array(c["local"], float)
    ok = np.isfinite(ta) & np.isfinite(loc)
    d_at_380 = np.interp(378.9, ta[ok], np.cumsum(np.r_[ta[ok][0] / c["secant"][0],
                                                        np.diff(ta[ok]) / loc[ok][1:]]))
    F["lock_extrapolation"] = {"theta_lock_deg": 450.0,
                               "delta_at_380": float(d_at_380),
                               "delta_at_lock": float(d_at_380 + (450 - 378.9) / loc[ok][-1]),
                               "turning_circle_implies_deg": 35.0,
                               "note": "37.4 ft curb-to-curb -> delta_max ~ 35 deg [BELIEF: "
                                       "published spec, not measured here]"}
    print(f"\n  extrapolated delta at full lock (450 deg) = "
          f"{F['lock_extrapolation']['delta_at_lock']:.1f} deg   "
          f"[turning circle implies ~35 deg]")

    (OUT / "final2.json").write_text(json.dumps(F, indent=1, default=float))
    print(f"\nwrote {OUT / 'final2.json'}")


if __name__ == "__main__":
    main()
