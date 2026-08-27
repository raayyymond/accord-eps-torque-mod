#!/usr/bin/env python3
r"""FINAL consolidation of the measured steering-ratio study -- the numbers that get reported.

Everything here uses the FLOOR definition that survived the controls:
    swing = median LOCAL ratio over |theta| in [3, 50) deg   /   median LOCAL ratio |theta| >= 120
🛑 The 0-3 deg bin is excluded: at 1-5 m/s a 2 deg wheel angle is ~0.0012 rad/s of yaw, at or below
   the residual IMU bias (max 0.0007 rad/s per route).  Including it was what made the 1.0-2.5 m/s
   sub-band appear to disagree (1.027) with the rest; with the floor defined on bins that HAVE
   power, the three sub-bands read 1.100 / 1.113 / 1.162.

Also fits the two BREAKPOINTS of the notch (floor->flank, flank->plateau) so the measured angular
extent can be put next to the firmware table's 34 deg / 100 deg knots.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ratio_lib as R  # noqa: E402
import measure_steering_ratio as M  # noqa: E402
from ratio_controls import CENTRE_HI, CENTRE_LO, swing2  # noqa: E402

OUT = R.ROOT / "analysis-2020accord" / "_scratch/cache/ratio"
F = {}

# firmware table 0xC6B64, full X/Y as supplied by the orchestrator (Ghidra-verified, not by me)
FWX = np.array([0, 34, 64, 85, 100, 120, 477.6])
FWY = np.array([899, 908, 981, 1060, 1083, 1084, 1084]) / 1084.0


def _blocks(blk):
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    b = np.searchsorted(inv[order], np.arange(len(ub) + 1))
    return [order[b[i]:b[i + 1]] for i in range(len(ub))]


# --------- the notch's angular extent: a 3-piece (flat floor / linear flank / flat plateau) fit.
# Breakpoints are searched over BIN INDICES, not a fine angle grid -- the curve only has 19 bins,
# so a finer grid would be false precision, and the index search is ~170 candidates, not 4,750.
def breakpoints(th, ratio):
    th = np.asarray(th, float); r = np.asarray(ratio, float)
    ok = np.isfinite(th) & np.isfinite(r) & (th >= CENTRE_LO)
    th, r = th[ok], r[ok]
    n = len(th)
    if n < 8:
        return np.nan, np.nan
    best, out = np.inf, (np.nan, np.nan)
    for i in range(2, n - 3):
        f = np.median(r[:i])
        for j in range(i + 1, n - 1):
            p = np.median(r[j:])
            pred = np.empty(n)
            pred[:i] = f
            pred[j:] = p
            if j > i:
                pred[i:j] = f + (p - f) * (th[i:j] - th[i - 1]) / (th[j] - th[i - 1])
            e = float(np.sum((r - pred) ** 2))
            if e < best:
                best, out = e, (float(th[i - 1]), float(th[j]))
    return out


def _stats(th, loc):
    """ALL reported statistics of one curve, computed in ONE pass (breakpoints run once)."""
    b1, b2 = breakpoints(th, loc)
    return {"swing": swing2(th, loc),
            "floor": float(np.nanmedian(loc[(th >= CENTRE_LO) & (th < CENTRE_HI)])),
            "plateau": float(np.nanmedian(loc[th >= M.PLATEAU_LO])),
            "bp_lo": b1, "bp_hi": b2}


def road_wheel_deg(A, m, yawkey, ackermann=False):
    """delta in deg.  `ackermann=True` returns the AVERAGE OF THE TWO FRONT WHEEL ANGLES instead
    of the single-track (bicycle) equivalent -- the other defensible definition of 'road-wheel
    angle'.  It differs from the bicycle angle by +1.7 % at 30 deg and <0.1 % below 10 deg, so it
    shaves ~1.7 % off the swing; reported so the definition is not load-bearing."""
    yaw, v = A[yawkey][m], A["v_ref"][m]
    d = np.arctan(yaw * R.L_WB / v)
    if not ackermann:
        return d * R.RAD
    with np.errstate(divide="ignore", invalid="ignore"):
        Rt = np.where(np.abs(np.tan(d)) > 1e-9, R.L_WB / np.tan(d), np.inf)
    di = np.arctan(R.L_WB / (np.abs(Rt) - R.T_REAR / 2))
    do = np.arctan(R.L_WB / (np.abs(Rt) + R.T_REAR / 2))
    return np.sign(d) * 0.5 * (di + do) * R.RAD


def boot_curve_stat(A, m, th0, yawkey, fns=None, nboot=1500, seed=101, ackermann=False):
    """Block-bootstrap every curve statistic (`_stats`) at once."""
    th_c = A["s_ang"][m] - th0
    dlt = road_wheel_deg(A, m, yawkey, ackermann)
    by = _blocks(A["blk"][m])
    c = M.curve_from(th_c, dlt, M.BINS)
    pt = _stats(c[0], c[2])
    rng = np.random.default_rng(seed)
    acc = {k: [] for k in pt}
    for _ in range(nboot):
        sel = np.concatenate([by[p] for p in rng.integers(0, len(by), len(by))])
        cc = M.curve_from(th_c[sel], dlt[sel], M.BINS)
        s = _stats(cc[0], cc[2])
        for k, x in s.items():
            if np.isfinite(x):
                acc[k].append(x)
    return {k: {"point": float(pt[k]),
                "ci95": [float(np.percentile(acc[k], 2.5)), float(np.percentile(acc[k], 97.5))],
                "n_boot": len(acc[k])} for k in pt} | {"n_blocks": len(by),
                                                       "seconds": float(m.sum() * R.DT)}


def main():
    A = M.prep()
    M.qa(A)
    th0 = M.fit_theta0(A, "A")
    prim = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A)
    primB = prim & (A["v_ref"] > 2.0)

    FNS = None
    print("\n" + "=" * 92)
    print("  ⭐ HEADLINE -- LOCAL steering ratio, floor(3-50 deg) vs plateau(>=120 deg)")
    print("=" * 92)
    # METHOD B2 -- FULLY SCALE-FREE: yaw AND the reference speed both come from the rear wheel
    # pair, so the tyre-radius scale cancels identically.  Depends on L/T and NOTHING else.
    A["yawB2"] = A["yawB0"]
    F["headline"] = {}
    for tag, mm, yk in (("A_livePose_IMU", prim, "yawA0"),
                        ("B_rear_wheelspeed_SCALE_FREE", primB, "yawB0")):
        s = boot_curve_stat(A, mm, th0, yk, FNS, nboot=1200, seed=101)
        s["ackermann_variant"] = boot_curve_stat(A, mm, th0, yk, FNS, nboot=300, seed=101,
                                                 ackermann=True)["swing"]
        F["headline"][tag] = s
        print(f"\n  METHOD {tag}   ({s['seconds']:.0f} s, {s['n_blocks']} blocks)")
        for k in ("floor", "plateau", "swing", "bp_lo", "bp_hi"):
            print(f"    {k:9s} = {s[k]['point']:8.3f}  95% CI "
                  f"[{s[k]['ci95'][0]:.3f}, {s[k]['ci95'][1]:.3f}]")
        av = s["ackermann_variant"]
        print(f"    swing, ACKERMANN-average road-wheel angle instead of the bicycle angle: "
              f"{av['point']:.3f} [{av['ci95'][0]:.3f}, {av['ci95'][1]:.3f}]")
    a = F["headline"]["A_livePose_IMU"]["swing"]
    b = F["headline"]["B_rear_wheelspeed_SCALE_FREE"]["swing"]
    print(f"\n  A vs B swing: {a['point']:.4f} {np.round(a['ci95'], 3).tolist()}  vs  "
          f"{b['point']:.4f} {np.round(b['ci95'], 3).tolist()}   -> CIs OVERLAP: "
          f"{a['ci95'][0] <= b['ci95'][1] and b['ci95'][0] <= a['ci95'][1]}")
    print(f"  FIRMWARE TABLE 0xC6B64 swing = {1084 / 899:.4f}")

    # ---------- strata, all with the surviving floor definition
    print("\n=== STRATA (all with floor 3-50 deg) ===")
    F["strata"] = {}
    strata = [("v 1.0-2.5", R.base_mask(A, vmin=1.0, vmax=2.5) & R.steady_mask(A)),
              ("v 2.5-3.5", R.base_mask(A, vmin=2.5, vmax=3.5) & R.steady_mask(A)),
              ("v 3.5-5.0", R.base_mask(A, vmin=3.5, vmax=5.0) & R.steady_mask(A)),
              ("LEFT", prim & (A["s_ang"] - th0 > 0)),
              ("RIGHT", prim & (A["s_ang"] - th0 < 0)),
              ("ENGAGED (latActive)", prim & (A["lat"] > 0.5)),
              ("MANUAL", prim & (A["lat"] < 0.5)),
              ("hands ON wheel", prim & (A["press"] > 0.5)),
              ("hands OFF wheel", prim & (A["press"] < 0.5))]
    for lab, mm in strata:
        if mm.sum() < 1500:
            print(f"  {lab:22s}: {mm.sum() * R.DT:6.0f} s -- NO POWER")
            F["strata"][lab] = {"seconds": float(mm.sum() * R.DT), "verdict": "no power"}
            continue
        s = boot_curve_stat(A, mm, th0, "yawA0", FNS, nboot=600, seed=103)
        F["strata"][lab] = s
        print(f"  {lab:22s}: {s['seconds']:6.0f} s  floor {s['floor']['point']:6.2f}  "
              f"plateau {s['plateau']['point']:6.2f}  swing {s['swing']['point']:.3f} "
              f"{np.round(s['swing']['ci95'], 3).tolist()}  "
              f"knees {s['bp_lo']['point']:.0f}/{s['bp_hi']['point']:.0f} deg")

    # ---------- the curve next to the firmware table
    print("\n=== MEASURED ratio(theta)/ratio(plateau)  vs  FIRMWARE 1/(Y/Ymax) ===")
    c = M.curve_boot(A, prim, th0, "yawA0", nboot=1200, seed=107)
    F["curve_primary"] = c
    fw_at = np.interp(np.array(c["theta"], float), FWX, 1.0 / FWY)
    print("   |th| deg   MEASURED local/plateau  [95% CI]      FIRMWARE implied   ratio fw/meas")
    for i, th in enumerate(c["theta"]):
        if not np.isfinite(th):
            continue
        print(f"  {th:8.1f}      {c['local_norm'][i]:7.3f} "
              f"[{c['local_norm_lo'][i]:6.3f},{c['local_norm_hi'][i]:6.3f}]        "
              f"{fw_at[i]:7.3f}          {fw_at[i] / c['local_norm'][i]:6.3f}")
    F["firmware_compare"] = {
        "fw_swing": float(1084 / 899),
        "measured_swing_A": float(a["point"]), "measured_swing_A_ci": a["ci95"],
        "fw_over_measured": float((1084 / 899) / a["point"]),
        "fw_over_measured_ci": [float((1084 / 899) / a["ci95"][1]),
                                float((1084 / 899) / a["ci95"][0])],
        "fw_inside_measured_CI": bool(a["ci95"][0] <= 1084 / 899 <= a["ci95"][1])}
    fc = F["firmware_compare"]
    print(f"\n  firmware swing {fc['fw_swing']:.4f}  /  measured {fc['measured_swing_A']:.4f} "
          f"= {fc['fw_over_measured']:.4f}  [{fc['fw_over_measured_ci'][0]:.3f}, "
          f"{fc['fw_over_measured_ci'][1]:.3f}]")
    print(f"  is the firmware's 1.206 inside the measured 95% CI? "
          f"{fc['fw_inside_measured_CI']}")

    (OUT / "final.json").write_text(json.dumps(F, indent=1, default=float))
    print(f"\nwrote {OUT / 'final.json'}")


if __name__ == "__main__":
    main()
