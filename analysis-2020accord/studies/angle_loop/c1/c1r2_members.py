# -*- coding: utf-8 -*-
"""c1r2_members.py -- the C1 rev 2 GATE 2 member set (2026-10-01): the FULL FACTORIAL of the stated corners.
ANALYSIS ONLY.

Why a factorial.  Round 2 (REFUTE-C1-r1-stability-2026-09-30.md) refuted rev 1 on a PRODUCT of two corners rev 1 had
gated only one at a time (b_q x J_hi, b_q x J1.0), and on hold aging applied only to single members.  A design that gates
a hand-picked list of products invites the next product.  So rev 2 gates EVERY combination of one corner per axis:

    damping  D in {nominal, b_lo, b/1.9, b_q}      b_lo  = b/1.8 at >= 10 m/s, x0.7 below (the G3a estimator bias)
                                                   b/1.9 = b/1.9 at >= 10 m/s, x0.7 below (the G3a top)
                                                   b_q   = max(0.25 b, 3.46) at >= 12.5 m/s (round-1 F4 fix; refuter's def.)
    inertia  I in {nominal J 0.2, J_hi 0.5, J_hi2 0.8, J1.0}   each the p5c profile REFIT at that J (J1.0 interpolated
                                                   between the 0.8 and 1.3 refits -- BELIEF on the interpolation)
    delay    T in {2 ms, 6 ms}
    age      A in {0, +10 ticks}                   slot 4 late by 10 whole ticks: hold ages 11..20

The damping corner is applied to the INERTIA REFIT's own b, exactly as the refuter's stab_scan.combo / refute_c1_ind
build b_lo*J_hi and b_q*J_hi.  Every name shared with the refuter's refute_c1_ind.member_params gives an identical
(J, b, k, d, age) -- selfcheck() asserts it.

Tiers (gates written before the run; the rev-2 design page's H2):
  A  PM >= 45, exact GM >= 6 dB, stable, no 5-50 Hz pole zeta < 0.2, M20/L20/T bars   the single-factor family:
     nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6                                      (unchanged since C0)
  B  PM >= 30, exact GM >= 6 dB, stable      every OTHER factorial cell (4 x 4 x 2 x 2 - 1 - 3 = 60) + the
     refuter-named b_lo*J0.3 (J overridden, not a refit) with and without +h10        -> 62 members
  report  tabulated, not gated, reason on the page: the J 1.3 refit and its products, tau10, b_lo*tau10, ms_free
     (J free per band), light_b (the prior world), b_q0 (unfloored), and "bq10" = b_q applied from 10 m/s (a stricter
     reading of the refuter's definition)
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_members as M1  # noqa: E402
import c1_lib  # noqa: E402,F401
import stab_lin as S  # noqa: E402

FAM = M1.FAM
REFIT = M1.REFIT
B_FLOOR = M1.B_FLOOR            # 0.7 * 4.94 = 3.46
BQ_V = 12.5                     # b_q applies at >= 12.5 m/s (the refuter's definition)

D_AX = ("", "b_lo", "b/1.9", "b_q")
I_AX = ("", "J_hi", "J_hi2", "J1.0")
T_AX = ("", "tau6")
A_AX = ("", "+h10")
TIER_A = M1.TIER_A               # nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6


def compose(d, i, t, a):
    parts = [x for x in (d, i, t) if x]
    base = "*".join(parts) if parts else "nominal"
    return base + a


FACTORIAL = tuple(compose(d, i, t, a) for d, i, t, a in itertools.product(D_AX, I_AX, T_AX, A_AX))
TIER_B = tuple(n for n in FACTORIAL if n not in TIER_A and n != "nominal") + ("b_lo*J0.3", "b_lo*J0.3+h10")
REPORT = ("J1.3", "b_lo*J1.3", "b_q*J1.3", "b_q*J1.3+h10", "tau10", "b_lo*tau10", "ms_free", "light_b", "b_q0",
          "b_q0*J_hi", "bq10*J1.0", "bq10*J1.0+h10", "bq10*J1.0*tau6+h10")
TIER_PM = {**{m: 45.0 for m in TIER_A}, **{m: 30.0 for m in TIER_B}}


def _dscale(d, b, v):
    if d == "":
        return b
    if d == "b_lo":
        return b * (1 / 1.8 if v >= 10 else 0.7)
    if d == "b/1.9":
        return b * (1 / 1.9 if v >= 10 else 0.7)
    if d in ("b_q", "b_q0", "bq10"):
        vq = 10.0 if d == "bq10" else BQ_V
        if v < vq:
            return b
        return 0.25 * b if d == "b_q0" else max(0.25 * b, B_FLOOR)
    raise KeyError(d)


def _inertia(i, v):
    if i == "":
        return FAM["nominal"].at(v)
    if i == "J_hi":
        return FAM["J_hi"].at(v)
    return REFIT[{"J_hi2": 0.8, "J1.0": 1.0, "J1.3": 1.3}[i]].at(v)


def params(name, v):
    """-> (J, b, k, tau_ms, extra_age)"""
    if name.endswith("+h10"):
        J, b, k, d, ea = params(name[:-4], v)
        return J, b, k, d, ea + 10
    if name in ("J_lo", "b_hi", "tau0", "ms_free", "light_b"):
        p = FAM[name].at(v)
        return p.J, p.b, p.k, p.tau_ms, 0
    if name == "b_lo*J0.3":                               # the refuter's own: nominal fit, J overridden to 0.3
        p = FAM["nominal"].at(v)
        return 0.3, _dscale("b_lo", p.b, v), p.k, 2, 0
    if name == "tau10":
        p = FAM["nominal"].at(v); return p.J, p.b, p.k, 10, 0
    if name == "b_lo*tau10":
        p = FAM["b_lo"].at(v); return p.J, p.b, p.k, 10, 0
    if name == "nominal":
        p = FAM["nominal"].at(v); return p.J, p.b, p.k, p.tau_ms, 0
    d, i, t = "", "", ""
    for part in name.split("*"):
        if part in ("b_lo", "b/1.9", "b_q", "b_q0", "bq10"):
            d = part
        elif part in ("J_hi", "J_hi2", "J1.0", "J1.3"):
            i = part
        elif part == "tau6":
            t = part
        else:
            raise KeyError(name)
    if d == "b_lo" and i == "":
        # the refuter's (and rev 1's) b_lo / b_lo*tau6 are v294_plant's FAM["b_lo"], whose x0.7 / 1/1.8 factors sit on
        # the V_CENTRES knots and are INTERPOLATED in speed (at 10 m/s: b 4.57, not the per-speed step's 4.20); the
        # products with an inertia refit use the per-speed step, as stab_scan.combo does.  Kept as each was defined.
        p = FAM["b_lo"].at(v)
        return p.J, p.b, p.k, (6 if t else 2), 0
    p = _inertia(i, v)
    return p.J, _dscale(d, p.b, v), p.k, (6 if t else 2), 0


def member(name, v):
    """the c1_members.member() interface: (stab_lin plant tuple, tau ticks, extra age, (J, b, k))."""
    J, b, k, d, ea = params(name, v)
    return S.rigid(J, b, k), d, ea, (J, b, k)


def tier(name):
    return "A" if name in TIER_A else ("B" if name in TIER_B else "report")


def selfcheck():
    """every name shared with the refuter's own member_params gives an identical (J, b, k, d, age); and the rev-1
    c1_members.member gives identical (J, b, k, tau, age) for every name the two share."""
    sys.path.insert(0, str(HERE.parent / "refute_stability"))
    import refute_c1_ind as R
    bad = n_ok = 0
    for n in TIER_A + TIER_B + REPORT:
        rn = n.replace("+h10", "+hA") if (n.endswith("+h10") and n[:-4] not in ("nominal", "b_lo", "J_hi")) else n
        for v in (3.1, 8.0, 10.0, 11.9, 12.25, 12.5, 15.0, 17.0, 19.0, 26.9, 30.0):
            for ref in (lambda: R.member_params(rn, v),
                        lambda: (lambda pl, tau, ea, jbk: (jbk[0], jbk[1], jbk[2], tau, ea))(*M1.member(n, v))):
                try:
                    r = ref()
                except (KeyError, AttributeError):
                    continue
                mine = params(n, v)
                if not np.allclose(r, mine, rtol=0, atol=1e-12):
                    bad += 1
                    print("MISMATCH", n, v, r, mine)
                else:
                    n_ok += 1
    print(f"c1r2_members.selfcheck: {n_ok} (name, v, reference) triples identical (the refuter's member_params and "
          f"rev 1's c1_members), {bad} mismatches; tier A {len(TIER_A)}, tier B {len(TIER_B)}, report {len(REPORT)}")
    return bad == 0


if __name__ == "__main__":
    selfcheck()
    print("TIER B:", TIER_B)
