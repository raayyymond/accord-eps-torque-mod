# -*- coding: utf-8 -*-
"""GATE #2 ADVERSARY, part 4 -- robustness of the (b) kill, and a structured null for clause (d)."""
import json
from math import comb, factorial
from pathlib import Path

import numpy as np

import adv_jerk_mechanism as M

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
R1 = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/retrodict/repair/out/r1_ident.json")
P = print
F = M.F

S = json.load(open(R1))
plants = {}
for key, d in S["cells"].items():
    wu = np.array(d["wSwu_re"]) + 1j * np.array(d["wSwu_im"])
    wy = np.array(d["wSwy_re"]) + 1j * np.array(d["wSwy_im"])
    plants[key] = dict(route=d["route"], bin=d["bin"], v=d["v"], c=d["c"], secs=d["secs"], n_run=d["n_run"],
                       alpha=abs(np.mean(wy.mean(0) / wu.mean(0))) * M.k_of(d["v"]))

P("=" * 112)
P("C1.  IS THE CLAUSE (b) FAILURE ROBUST?  both speed bins x all eligible plants x 3 delays")
P("     x jerk in-loop/exogenous x two readings of the V282 anchor trio.")
P("=" * 112)
V282_SETS = {"V282 trio = the three 0.010 routes (64/65/6c)": ["V282 clean"],
             "V282 trio spans 0.010-0.030 as the prereg's table says": ["V282 clean", "V282old cln"]}
fails, tot, detail = 0, 0, []
for vname, vcfgs in V282_SETS.items():
    cleans = ["r72 clean", "rev6.4 cln"] + vcfgs
    for binname in ("22+", "15-22"):
        elig = [k for k, p in plants.items()
                if p["bin"] == binname and p["route"] not in ("00000071--f2c9d073a3", "00000073--79fd149dd8")
                and p["secs"] >= 80 and not p["route"].startswith(("00000039", "0000003a", "0000003c",
                                                                  "00000064", "00000065", "0000006c--2bc"))]
        for D in (0.055, 0.065, 0.075):
            for jl in (False, True):
                for pk in elig:
                    pl = plants[pk]
                    sc = {}
                    for nm in ["r71  POS", "r73  POS"] + cleans:
                        L = M.L_of(F, pl["v"], pl["alpha"], pl["c"], M.CTRL[nm], D, 0.0006, 1.0, jl)
                        cs = M.crossings(F, L)
                        sc[nm] = cs[0][1] if cs else np.nan
                    worst = max(cleans, key=lambda c: sc[c])
                    ok = sc["r71  POS"] > sc[worst] and sc["r73  POS"] > sc[worst]
                    tot += 1
                    fails += (not ok)
                    detail.append(dict(vset=vname, bin=binname, D=D, jerk=jl, plant=pl["route"],
                                       passed=bool(ok), worst_clean=worst,
                                       sc={k: float(v) for k, v in sc.items()}))
        P(f"  [{vname[:46]:46s}] bin {binname:6s} plants {len(elig)}")
P(f"\n  clause (b) evaluated in {tot} (V282-reading x bin x delay x jerk-reading x plant) cells")
P(f"  FAILED in {fails} of {tot}  ({100 * fails / tot:.1f} %)")
byw = {}
for d in detail:
    if not d["passed"]:
        byw[d["worst_clean"]] = byw.get(d["worst_clean"], 0) + 1
P(f"  the clean that beats a positive: {byw}")
P("  (a single cell PASSES only if BOTH positives beat EVERY clean in it.)")

P("\n" + "=" * 112)
P("C2.  CLAUSE (d), FINAL.  Two nulls: (i) uniform random ranking, (ii) a STRUCTURED null --")
P("     a statistic that is an arbitrary monotone combination of the controller's own numbers")
P("     but knows nothing about the labels.")
P("=" * 112)
# how many DISTINCT values does the kit's own statistic see among the 5 clean routes?
# r2_stat's controller vector is (kp, laf, ki, notch, fric, rate, dob) -- SteerRatio is NOT in it.
P("  distinct clean VALUES for a statistic built on (kp, LAF, ki, notch, SteerFriction, rateloop):")
P("    r72  (0.85, 14, 0.60, Q1, 0.000, 6e-4)        -> 1")
P("    rev6.4 x2 routes (1.00, 14, 0.30, Q1, 0, 1e-3)-> 1  (both routes identical)")
P("    V282 x3 routes (0.90, 6.0, 0.30, --, 0.010, 0)-> 1  (SteerRatio differs, statistic ignores it)")
P("    => 3 distinct clean values, not 5.  Clause (b)'s 'ALL FIVE clean routes' is 3 draws.")
for ncv in (3, 4, 5):
    P(f"    P(both positives top-2 | random ranking, {ncv} clean values) = 1/C({ncv + 2},2) = {1 / comb(ncv + 2, 2):.4f}")
p_b = 1 / comb(5, 2)

rng = np.random.default_rng(20260920)
feats = {}
for nm, p in M.CTRL.items():
    feats[nm] = np.array([p["kp"], p["laf"], p["ki"], p["fric"] + 1e-4, p["rate"] + 1e-5,
                          p["kp"] / p["laf"], 2.0 if p["notch"] else 1.0])
groups = {"r71  POS": "P", "r73  POS": "P", "r72 clean": "C", "rev6.4 cln": "C", "V282 clean": "C"}
names = list(groups)
X = np.log(np.array([feats[n] for n in names]))
X = (X - X.mean(0)) / (X.std(0) + 1e-12)
npass_b = npass_bc = 0
NMC = 200000
for _ in range(NMC):
    w = rng.normal(size=X.shape[1])
    s = X @ w
    pos = [s[i] for i, n in enumerate(names) if groups[n] == "P"]
    cln = [s[i] for i, n in enumerate(names) if groups[n] == "C"]
    b = min(pos) > max(cln)
    npass_b += b
    npass_bc += b  # (c) entailed by (b)
P(f"\n  STRUCTURED null (random weights on log controller features, {NMC} draws):")
P(f"    P(b and c) = {npass_b / NMC:.4f}   [uniform-ranking value would be {p_b:.4f}]")
P("    -- a statistic with structure but no label knowledge is NOT more likely to pass; the")
P("       anchor set's own geometry (V282 high-gain-and-relay-live, clean) works against it.")

pa73 = 0.667  # empirical, from gate #1's own 63 crossings landing in [3.0,8.125]
P(f"\n  P(a | r71) ~ 1.00   (window [1.755,2.925] brackets the plant mode 1.73-2.25 at 93.5% of speeds;")
P(f"                       gate #1 passed it on every plant with NO jerk term)")
P(f"  P(a | r73)  = {pa73:.3f} (empirical over gate #1's own crossings, WIDE reading [3.0,8.125])")
P(f"              = 0.000 (NARROW reading [4.0,6.5]: 0 of 42 crossings of this model family reach it)")
single = 1.0 * pa73 * p_b
P(f"\n  SINGLE-SHOT  P(pass a+b+c | no content) = 1.00 x {pa73:.3f} x {p_b:.4f} = {single:.4f}")
P(f"  bracket over the count of distinct clean values (3..5): "
  f"{1.0 * pa73 * (1 / comb(7, 2)):.4f} .. {1.0 * pa73 * (1 / comb(5, 2)):.4f}")
P(f"  and if P(a|r73) is also taken as ~1 (the window is wide and the analyst picks the crossing):"
  f" {1.0 * 1.0 * p_b:.4f}")
P("\n  MULTIPLICITY from the choices the PREREG LEAVES FREE (crossing index, b over 70x, D, speed bin,")
P("  plant subset).  These are not hypothetical: the ONLY way r73 clears clause (a) in this model")
P("  family is to switch from the FIRST crossing to the THIRD, which is exactly such a choice.")
for Meff in (1, 2, 3, 4):
    P(f"    M_eff={Meff}: P = 1-(1-{single:.4f})^{Meff} = {1 - (1 - single) ** Meff:.4f}"
      + ("   EXCEEDS 0.10" if 1 - (1 - single) ** Meff > 0.10 else "   <= 0.10"))

json.dump(dict(clause_b_cells=tot, clause_b_fails=fails, worst_clean_counts=byw,
               p_single=single, p_b=p_b, pa73=pa73,
               structured_null_p=float(npass_b / NMC), detail=detail[:400]),
          open(OUT / "final.json", "w"), indent=1)
P("\nwrote " + str(OUT / "final.json"))
