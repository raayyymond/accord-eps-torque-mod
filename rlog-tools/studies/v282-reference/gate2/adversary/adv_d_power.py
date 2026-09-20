# -*- coding: utf-8 -*-
"""GATE #2 ADVERSARY -- clause (d) POWER, computed explicitly and first.

P(pass | statistic with NO discriminating content) on the pre-registered anchor set.

Enumerated exactly where exact enumeration is possible, Monte-Carlo where it is not.
Nothing here reads the repair stream's result.
"""
import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
PARAMS = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/hsurface/surface/params_all.json")

J = 8e-5
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]

rep = []
P = print


def mode_hz(v):
    return float(np.sqrt(float(np.interp(v, HOLD_V_BP, HOLD_K_V)) / J) / (2 * np.pi))


# ------------------------------------------------------------------ (a) the frequency windows
P("=" * 110)
P("CLAUSE (a) -- ARE THE FREQUENCY WINDOWS DISCRIMINATING?  (the trap the brief names)")
P("=" * 110)
w71 = (2.34 * 0.75, 2.34 * 1.25)
# 'within +/-25% of the 4.0-6.5 Hz band' -- read in the widest admissible sense (favours the repair)
w73_wide = (4.0 * 0.75, 6.5 * 1.25)
w73_narrow = (4.0, 6.5)
P(f"  r71 window (+/-25% of 2.34 Hz)          : [{w71[0]:.3f}, {w71[1]:.3f}] Hz")
P(f"  r73 window, widest reading              : [{w73_wide[0]:.3f}, {w73_wide[1]:.3f}] Hz")
P(f"  r73 window, band itself                 : [{w73_narrow[0]:.3f}, {w73_narrow[1]:.3f}] Hz")

P("\n  The plant mode sqrt(k(v)/J)/2pi over the speeds the anchors actually flew:")
vs = np.arange(15.0, 30.01, 0.5)
m = np.array([mode_hz(v) for v in vs])
inside = ((m >= w71[0]) & (m <= w71[1])).mean()
P(f"    v = 15..30 m/s  ->  mode = {m.min():.3f} .. {m.max():.3f} Hz")
P(f"    fraction of that speed range whose PLANT MODE falls inside r71's window : {inside * 100:.1f} %")
# the anchors' own bin speeds, from gate #1's TABLE 2
anchor_v = dict(r71_lo=17.4, r71_hi=28.5, r72=26.5, r73_lo=18.1, r73_hi=26.9, T64=26.9, V282=30.0, V293=18.9)
P("    at each anchor's own mean speed:")
for k, v in anchor_v.items():
    P(f"      {k:8s} v={v:5.1f}  mode={mode_hz(v):.3f} Hz   inside r71 window: {w71[0] <= mode_hz(v) <= w71[1]}")

P("\n  => VERDICT ON r71's FREQUENCY CLAUSE: any model whose -180 crossing sits at or near the plant")
P("     mode passes it automatically.  Gate #1 ALREADY passed it (2.26-2.60 Hz on every plant) with")
P("     NO jerk term.  It carries ~zero information.  P(a-r71 | no content) is taken as ~1.")

# ------------------------------------------------------------------ distinct controller configs
P("\n" + "=" * 110)
P("HOW MANY DISTINCT SCORES DOES THE RANKING ACTUALLY CONTAIN?  (this sets clause (b)'s power)")
P("=" * 110)
PA = json.load(open(PARAMS))


def cfg(rt):
    d = PA[rt]
    g = lambda k, dflt: (dflt if d.get(k) in (None, "ABSENT") else float(d[k]))
    return (d["GitCommit"][:9], g("SteerKP", 1.0), g("SteerLatAccel", 1.689), g("AccordTorqueKi", .3),
            g("AccordRateLoopGain", 0.0), g("SteerFriction", .212), g("AccordFrictionHyst", -1.0))


anchors = {
    "r71  POSITIVE": "00000071--f2c9d073a3",
    "r73  POSITIVE": "00000073--79fd149dd8",
    "r72  clean": "00000072--8001fc3048",
    "rev6.4 clean #1": "0000006c--68c6e94b17",
    "rev6.4 clean #2": "0000006e--6ca3e014fd",
    "V282 clean #1": "00000064--ce6b0b0ebb",
    "V282 clean #2": "00000065--b9f78988bd",
    "V282 clean #3": "0000006c--2bc842dbac",
}
seen = {}
for nm, rt in anchors.items():
    c = cfg(rt)
    seen.setdefault(c, []).append(nm)
    P(f"  {nm:16s} {rt}  commit={c[0]}  kp={c[1]:.2f} LAF={c[2]:.2f} ki={c[3]:.2f} rate={c[4]:.4f} SF={c[5]:.4f} hyst={c[6]}")
P(f"\n  distinct CONTROLLER CONFIGS among the 8 anchor routes: {len(seen)}")
for c, nms in seen.items():
    P(f"    {nms}")
n_clean_cfg = len(set(cfg(rt) for nm, rt in anchors.items() if "POSITIVE" not in nm))
n_tot_cfg = len(seen)
P(f"  distinct clean configs = {n_clean_cfg}; total distinct configs in the ranking = {n_tot_cfg}")
P("  (routes that share a commit AND every flown toggle get IDENTICAL scores from any controller-only")
P("   statistic, so they are ONE draw, not three.  Clause (b)'s '5 clean routes' is really")
P(f"   {n_clean_cfg} clean values.)")

# ------------------------------------------------------------------ (b)+(c) combinatorics
P("\n" + "=" * 110)
P("CLAUSES (b)+(c) -- EXACT COMBINATORICS FOR A CONTENT-FREE STATISTIC")
P("=" * 110)


def p_both_top2(n_clean_values):
    """P(both positives above ALL clean values) for a uniformly random ranking of
    2 positives + n_clean_values distinct clean values."""
    n = 2 + n_clean_values
    from math import comb
    return 1.0 / comb(n, 2)


for ncv in (3, 4, 5):
    P(f"  n distinct clean values = {ncv}:  P(both positives top-2, one plant) = 1/C({ncv + 2},2) = {p_both_top2(ncv):.4f}")

P("\n  Clause (c) is ENTAILED by clause (b): rev6.4 is one of the cleans, so if both positives")
P("  outrank every clean, rev6.4 cannot outrank either positive.  (c) adds ZERO power.")
P("  [verify by exhaustion over all orderings, below]")
ncv = n_clean_cfg
labels = ["P1", "P2"] + [f"C{i}" for i in range(ncv)]  # C0 := rev6.4
nb = nc = nbc = 0
for perm in itertools.permutations(range(len(labels))):
    rank = {labels[i]: perm[i] for i in range(len(labels))}  # 0 = riskiest
    b = max(rank["P1"], rank["P2"]) < min(rank[f"C{i}"] for i in range(ncv))
    c = rank["C0"] > min(rank["P1"], rank["P2"]) and rank["C0"] > max(rank["P1"], rank["P2"])
    nb += b
    nc += c
    nbc += (b and c)
tot = np.math.factorial(len(labels)) if hasattr(np, "math") else __import__("math").factorial(len(labels))
P(f"  exhaustive over {tot} orderings:  P(b) = {nb / tot:.4f}   P(c) = {nc / tot:.4f}   P(b and c) = {nbc / tot:.4f}")
P(f"  => P(b and c) == P(b) : {abs(nb - nbc) == 0}")

# plant correlation
P("\n  '>= 2 of 3 plants' -- does it multiply the power down?  Only if the plants disagree.")
P("  In gate #1's own cross-table (GATE_22plus.txt TABLE 4) the CONTROLLER ORDERING IS IDENTICAL")
P("  on all 7 plants, because the plant enters the statistic ONLY as the scalar alpha (r2_stat.py:")
P("  L = C_e * c * P, alpha a pure multiplier; TABLE 5 says so in as many words).  A pure positive")
P("  scalar cannot reorder a ranking.  So the 3 plants are ONE test, not three.")
rho_cases = {"plants perfectly correlated (what gate #1 actually shows)": "corr",
             "plants independent (the generous reading)": "indep"}
p1 = p_both_top2(ncv)
from math import comb
p_indep = sum(comb(3, k) * p1 ** k * (1 - p1) ** (3 - k) for k in (2, 3))
P(f"    perfectly correlated : P(b on >=2 of 3) = P(b on one) = {p1:.4f}")
P(f"    independent          : P(b on >=2 of 3) = {p_indep:.4f}")

# ------------------------------------------------------------------ total
P("\n" + "=" * 110)
P("CLAUSE (d) -- THE NUMBER")
P("=" * 110)
# P(a) for r73 under a content-free frequency prior.  Crossings in this model family are searched
# over 1-8 Hz (r2_stat.crossing), so a content-free statistic puts r73's crossing somewhere in 1-8 Hz.
lo, hi = 1.0, 8.0
pa73_loguni = np.log(min(w73_wide[1], hi) / w73_wide[0]) / np.log(hi / lo)
pa73_uni = (min(w73_wide[1], hi) - w73_wide[0]) / (hi - lo)
pa73_emp = None
P(f"  P(a | r71)  ~ 1.00       (window brackets the plant mode; gate #1 passed it with no jerk term)")
P(f"  P(a | r73)  = {pa73_uni:.3f}  (uniform on the model's own 1-8 Hz crossing search)")
P(f"              = {pa73_loguni:.3f}  (log-uniform on 1-8 Hz)")
P("  Empirical prior from gate #1's OWN 63 (plant x controller) crossings, 22+ bin:")
g1 = [2.57, 3.64, 1.92, 3.72, 3.72, 3.72, 3.72, 3.58, 2.56,
      2.59, 3.62, 1.95, 3.70, 3.70, 3.70, 3.70, 3.55, 2.58,
      2.46, 3.58, 1.80, 3.67, 3.67, 3.67, 3.67, 3.52, 2.45,
      2.60, 3.61, 1.95, 3.69, 3.69, 3.69, 3.69, 3.54, 2.59,
      2.55, 3.63, 1.91, 3.72, 3.72, 3.72, 3.72, 3.57, 2.54,
      2.57, 3.63, 1.92, 3.71, 3.71, 3.71, 3.71, 3.56, 2.56,
      2.52, 3.62, 1.87, 3.71, 3.71, 3.71, 3.71, 3.55, 2.51]
g1 = np.array(g1)
pa73_emp = float(((g1 >= w73_wide[0]) & (g1 <= w73_wide[1])).mean())
pa71_emp = float(((g1 >= w71[0]) & (g1 <= w71[1])).mean())
P(f"    P(crossing in r73's window) = {pa73_emp:.3f}   P(crossing in r71's window) = {pa71_emp:.3f}")

for nm, pa71, pa73 in [("uniform 1-8 Hz prior", 1.0, pa73_uni),
                       ("log-uniform 1-8 Hz prior", 1.0, pa73_loguni),
                       ("empirical (gate #1's own crossings)", 1.0, pa73_emp),
                       ("empirical, r71 NOT free", pa71_emp, pa73_emp)]:
    for cn, pb in [("plants correlated", p1), ("plants independent", p_indep)]:
        P(f"  P(pass a+b+c) [{nm:36s} | {cn:18s}] = {pa71 * pa73 * pb:.4f}")

P("\n  MULTIPLICITY -- the prereg leaves these free, and each is a re-roll of the same dice:")
dofs = {"which of the THREE -180 crossings to score (the brief says 'state it')": 3,
        "which speed bin (15-22 / 22+)": 2,
        "b, open over ~70x (gate #1 used one value; nothing fixes it)": 3,
        "delay 55/65/75 ms": 3,
        "which 3 of the 6-7 available plants": 3}
M = 1
for k, v in dofs.items():
    P(f"    x{v}  {k}")
    M *= v
P(f"    naive product M = {M} configurations.  Effective independent tries is far less than M")
P("    (the choices are correlated), so report a BRACKET rather than the product:")
for Meff in (1, 2, 3, 5, 10):
    for cn, pb in [("correlated", p1), ("independent", p_indep)]:
        p_single = 1.0 * pa73_emp * pb
        P(f"    M_eff={Meff:2d} [{cn:11s}]  P(pass) = 1-(1-{p_single:.4f})^{Meff} = {1 - (1 - p_single) ** Meff:.4f}"
          + ("   >0.10  GATE TOO WEAK" if 1 - (1 - p_single) ** Meff > 0.10 else ""))

json.dump(dict(w71=w71, w73_wide=w73_wide, n_clean_cfg=n_clean_cfg, n_tot_cfg=n_tot_cfg,
               p_b_one_plant=p1, p_b_indep3=p_indep, pa73_uni=pa73_uni, pa73_log=pa73_loguni,
               pa73_emp=pa73_emp, pa71_emp=pa71_emp,
               p_single_corr=pa73_emp * p1, p_single_indep=pa73_emp * p_indep,
               mode_inside_r71_window_frac=float(inside)),
          open(OUT / "d_power.json", "w"), indent=1)
P("\nwrote " + str(OUT / "d_power.json"))
