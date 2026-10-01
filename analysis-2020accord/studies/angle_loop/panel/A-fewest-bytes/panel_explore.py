# -*- coding: utf-8 -*-
"""panel_explore.py -- fast tuning of Designer A's two implementations against the full credible set, using stab_lin
margins + exact rho ONLY (no exact_gm bisection), so a schedule can be iterated in ~1 min.  ANALYSIS ONLY.

Picks:
  A2: the Kp-envelope scale and Ki/Kp ratio that maximise the tier-B min PM while keeping tier A >= 45 deg.
  A1: the flat Ki (and Kp scale) that keeps the WHOLE credible set stable, and reports the tracking it then gives up.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1]), str(HERE.parents[1] / "c1"),
           str(HERE.parents[1] / "refute_stability"), str(HERE.parents[2] / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import os
os.environ.setdefault("C1_VARIANT", "r2")
import panel_schedules as PS   # noqa: E402
import c1r2_members as M       # noqa: E402
import stab_lin as S           # noqa: E402

GRID = sorted(set([round(x, 2) for x in np.arange(2.0, 28.01, 1.0)] + [3.1, 8.0, 11.0, 11.9, 12.5, 17.0, 26.9]))


def _lerp(X, Y, u):
    return PS._lerp_int(X, Y, u)


def kp_scaled(v, scale):
    return int(round(PS.kp_of(v) * scale))


def ctl(v, kp, ki, kd, d, ea):
    return S.Ctl(v, kp=kp, ki=ki, kd=kd, d=d, extra_age=ea, G=256)


def eval_set(kp_scale, ki_mode, ki_flat=300, ki_over_kp=0.5, kd=20, names=None):
    """min PM per tier + worst (unstable) count, over the member set at ages 0 and 10."""
    names = names or (M.TIER_A + M.TIER_B)
    worstA = (999, None); worstB = (999, None); nunstable = 0; nB_lt30 = 0; nA_lt45 = 0
    for n in names:
        tier = "A" if n in M.TIER_A else "B"
        for v in GRID:
            pl, tau, base_ea, (J, b, k) = M.member(n, v)
            kp = kp_scaled(v, kp_scale)
            ki = ki_flat if ki_mode == "flat" else int(round(ki_over_kp * kp))
            for ea_x in (0, 10):
                c = ctl(v, kp, ki, kd, tau, base_ea + ea_x)
                mg = S.margins(c, pl, npts=2500)
                rho = S.exact(c, pl)[0]
                pm = mg["pm"]
                if rho >= 1.0 or not np.isfinite(pm):
                    nunstable += 1
                    pm = -1.0
                if tier == "A":
                    if pm < 45:
                        nA_lt45 += 1
                    if pm < worstA[0]:
                        worstA = (pm, (n, v, ea_x))
                else:
                    if pm < 30:
                        nB_lt30 += 1
                    if pm < worstB[0]:
                        worstB = (pm, (n, v, ea_x))
    return dict(worstA=worstA, worstB=worstB, nunstable=nunstable, nA_lt45=nA_lt45, nB_lt30=nB_lt30)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "A2"
    if mode == "A2":
        print("A2 (Ki(v)=r*Kp): scan Kp-scale x Ki/Kp for tier-B min PM, tier A>=45")
        for scale in (1.0, 0.85, 0.72, 0.62):
            for r in (0.5, 0.4, 0.33):
                res = eval_set(scale, "sched", ki_over_kp=r, kd=20)
                print(f"  scale {scale:.2f} Ki/Kp {r:.2f}: tierA minPM {res['worstA'][0]:6.1f} {res['worstA'][1]}"
                      f" | tierB minPM {res['worstB'][0]:6.1f} {res['worstB'][1]} | unstable {res['nunstable']}"
                      f" A<45 {res['nA_lt45']} B<30 {res['nB_lt30']}")
    elif mode == "A1":
        print("A1 (flat Ki): scan Kp-scale x flat Ki for STABILITY and tier-A PM")
        for scale in (1.0, 0.72, 0.55):
            for ki in (300, 200, 120, 60, 30):
                res = eval_set(scale, "flat", ki_flat=ki, kd=20)
                print(f"  scale {scale:.2f} Ki {ki:4d}: tierA minPM {res['worstA'][0]:6.1f} {res['worstA'][1]}"
                      f" | tierB minPM {res['worstB'][0]:6.1f} {res['worstB'][1]} | unstable {res['nunstable']}"
                      f" A<45 {res['nA_lt45']} B<30 {res['nB_lt30']}")
    elif mode == "A2kd":
        print("A2 with Kd schedule (24/22/18/16): scan Kp-scale x Ki/Kp")
        # monkeypatch kd via per-speed: approximate with flat kd at the binding speed; use kd=18 as representative
        for scale in (0.72, 0.62):
            for r in (0.5, 0.4):
                res = eval_set(scale, "sched", ki_over_kp=r, kd=18)
                print(f"  scale {scale:.2f} Ki/Kp {r:.2f} kd18: tierB minPM {res['worstB'][0]:6.1f} {res['worstB'][1]}"
                      f" | unstable {res['nunstable']} A<45 {res['nA_lt45']} B<30 {res['nB_lt30']}")
