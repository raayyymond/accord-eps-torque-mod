# -*- coding: utf-8 -*-
"""c1_members.py -- the C1 GATE 2 member set, by tier, built from the r71b family (v294_plant.family) and the
stability refuter's own combination definitions (refute_stability/stab_scan.combo, re-used verbatim).

TIER A (PM >= 45 deg, the C0 H2 bar kept): the single-factor credible family
    nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6
TIER B (PM >= 30 deg, the combined / stated-uncertainty members the refuters added):
    b_lo*J_hi, b_lo*J_hi*tau6, b_lo*tau6, J_hi*tau6, b/1.9*J_hi, b_lo*J0.3      (stab_scan.combo, the refuter's own)
    J_hi2 (= the J 0.8 profile refit), J1.0 (the 0.8/1.3 refits interpolated at J 1.0, BELIEF on the interpolation)
    hold+10: nominal / b_lo / J_hi with slot 4 late by 10 whole ticks (hold ages 11..20)
    b_q: nominal with b x 0.25 at >= 12.5 m/s (the stability refuter's F4 fix (b): PM >= 30 down to b ~ 0.25 x fitted)
    bc: linear part = b_lo (the bias-corrected friction lives in the time domain only)
REPORT ONLY (not gating; stated why on the page): J1.3 refit, tau10, b_lo*tau10, ms_free (J 2.08 at 11.9 m/s), light_b.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib  # noqa: E402,F401  (sets sys.path)
import stab_lin as S  # noqa: E402
import v294_plant as VP  # noqa: E402

FAM = VP.family()
_ROWS = VP._profile_rows(os.path.join(os.path.dirname(VP.__file__), "_scratch", "p5c.json"))


def _refit(Jr):
    if Jr in _ROWS:
        b, k, F, Fs = _ROWS[Jr]
        return VP.PlantFamilyMember(f"J{Jr}", J=np.full(5, Jr), b=b, k=k, Fc=F, Fs=Fs, tau_ms=2)
    # linear interpolation between the bracketing refits (BELIEF: the refits are not linear in J)
    js = sorted(_ROWS)
    lo = max(j for j in js if j < Jr)
    hi = min(j for j in js if j > Jr)
    w = (Jr - lo) / (hi - lo)
    arr = [(1 - w) * a + w * b for a, b in zip(_ROWS[lo], _ROWS[hi])]
    return VP.PlantFamilyMember(f"J{Jr}", J=np.full(5, Jr), b=arr[0], k=arr[1], Fc=arr[2], Fs=arr[3], tau_ms=2)


REFIT = {0.8: _refit(0.8), 1.0: _refit(1.0), 1.3: _refit(1.3)}


def combo(name, v):
    """the stability refuter's stab_scan.combo, copied verbatim (so its members mean exactly what the refuter ran)."""
    fam = FAM
    if name == "b_lo*J_hi":
        p = fam["J_hi"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 2
    if name == "b_lo*J_hi*tau6":
        p = fam["J_hi"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 6
    if name == "b_lo*tau6":
        p = fam["b_lo"].at(v); return p, S.rigid(p.J, p.b, p.k), 6
    if name == "J_hi*tau6":
        p = fam["J_hi"].at(v); return p, S.rigid(p.J, p.b, p.k), 6
    if name == "b/1.9 (G3a top)":
        p = fam["nominal"].at(v); bs = 1 / 1.9 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 2
    if name == "b/1.9*J_hi":
        p = fam["J_hi"].at(v); bs = 1 / 1.9 if v >= 10 else 0.7
        return p, S.rigid(p.J, p.b * bs, p.k), 2
    if name == "b_lo*J0.3":
        p = fam["nominal"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7
        return p, S.rigid(0.3, p.b * bs, p.k), 2
    if name == "tau10":
        p = fam["nominal"].at(v); return p, S.rigid(p.J, p.b, p.k), 10
    if name == "b_lo*tau10":
        p = fam["b_lo"].at(v); return p, S.rigid(p.J, p.b, p.k), 10
    raise KeyError(name)


TIER_A = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6")
COMBOS_B = ("b_lo*J_hi", "b_lo*J_hi*tau6", "b_lo*tau6", "J_hi*tau6", "b/1.9*J_hi", "b_lo*J0.3")
TIER_B = COMBOS_B + ("J_hi2", "J1.0", "nominal+h10", "b_lo+h10", "J_hi+h10", "b_q")
REPORT = ("J1.3", "tau10", "b_lo*tau10", "ms_free", "light_b", "b/1.9 (G3a top)", "b_q0")
B_FLOOR = 0.7 * 4.94
TIER_PM = {**{m: 45.0 for m in TIER_A}, **{m: 30.0 for m in TIER_B}}


def member(name, v):
    """-> (plant tuple for stab_lin, transport d ticks, extra hold age ticks, params J/b/k)"""
    if name in FAM:
        p = FAM[name].at(v)
        return S.rigid(p.J, p.b, p.k), p.tau_ms, 0, (p.J, p.b, p.k)
    if name.endswith("+h10"):
        base = name[:-4]
        p = FAM[base].at(v)
        return S.rigid(p.J, p.b, p.k), p.tau_ms, 10, (p.J, p.b, p.k)
    if name in ("b_q", "b_q0"):
        # the stability refuter's F4 fix (b): PM >= 30 with the 3-5 Hz damping at 0.25 x the fit, at >= 12.5 m/s.
        # b_q floors it at B_FLOOR = b_lo's identified low-speed b (0.7 x 4.94 = 3.46; the steering's own damping,
        # identified at 0-8 m/s, is not lumped vehicle dynamics -- BELIEF); b_q0 is the unfloored 0.25 x (report).
        p = FAM["nominal"].at(v)
        if v >= 12.5:
            bq = 0.25 * p.b if name == "b_q0" else max(0.25 * p.b, B_FLOOR)
        else:
            bq = p.b
        return S.rigid(p.J, bq, p.k), 2, 0, (p.J, bq, p.k)
    if name in ("J1.0", "J1.3", "J_hi2"):
        Jr = {"J1.0": 1.0, "J1.3": 1.3, "J_hi2": 0.8}[name]
        p = REFIT[Jr].at(v)
        return S.rigid(p.J, p.b, p.k), 2, 0, (p.J, p.b, p.k)
    p, pl, tau = combo(name, v)
    A = pl[0]
    J = 1.0 / pl[1][1, 0]
    return pl, tau, 0, (J, -A[1, 1] * J, -A[1, 0] * J)


def hf_plant(name, v):
    """the same member as a harness_freq.Plant (rigid); returns (Plant, extra_age)."""
    import harness_freq as HF
    pl, tau, ea, (J, b, k) = member(name, v)
    return HF.Plant(J=J, b=b, k=k, tau=tau, name=f"{name}@{v:g}"), ea
