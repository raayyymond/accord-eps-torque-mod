# -*- coding: utf-8 -*-
"""TEST 1 -- does the measured loop shape ACCOUNT for the measured extra lag, arithmetically?

The budget measured leg L34 (shaped setpoint Z -> wheel angle M) at 0.15-0.30 Hz as
V282 107.7 ms vs torque 305.0 ms, a gap of +197.2 ms.  Here that leg is re-measured from the
cross-spectral phase (a different estimator on the same logs), and then the measured difference is
DECOMPOSED into the three measured transfers that make it:

    C(jw) = U_fb/E              the feedback controller (kp/LAF + ki/(LAF jw), x lsf, x notch)
    P(jw) = Y/U   (IV)          the plant: commanded torque -> the loop's measurement
    F(jw) = U_ff/R              the feedforward path (plant FF + friction + inner rate loop + DOB)
    T     = (C P + P F)/(1 + C P) = Y/R             -- an IDENTITY given those three (checked below)

Swapping one measured transfer at a time between the families and re-evaluating T is ALGEBRA ON
MEASURED TRANSFERS.  It attributes a measured difference; it is NOT a prediction of how any car
would behave with a changed parameter, and nothing here is offered as a dose.

CAN THIS FAIL?  Yes, in two ways that are checked and reported:
  (i) the re-measured leg could disagree with the budget's +197 ms (different estimator, same logs);
  (ii) the C-swap could account for only a small part of the gap, which would REFUTE the
       "it is the loop gain" half of the hypothesis and hand it to the plant instead.

usage: python u3_decomp.py [tag] [--v=lo,hi]
out:   u3_<tag>.json, U3-<TAG>-OUT.txt
"""
import itertools
import json
import sys
import numpy as np
import ulib as U

TAG = sys.argv[1] if len(sys.argv) > 1 else "hi"
BANDS = [(0.08, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]
D = np.load(f"spec_{TAG}.npz", allow_pickle=True)
f = D["f"]
fam, route, sec = D["fam"], D["route"], D["sec"]
MEM = {k[2:]: np.asarray(D[k]) for k in D.files if k.startswith("S_")}
sel = np.ones(len(fam), bool)
note = "all windows"
VW = [a for a in sys.argv if a.startswith("--v=")]
if VW:
    lo, hi = (float(x) for x in VW[0][4:].split(","))
    sel &= (D["v"] >= lo) & (D["v"] < hi)
    note = f"window median speed in [{lo},{hi}) m/s"


def pooled(idx):
    w = sec[idx]
    return {k: np.tensordot(w, v[idx], axes=(0, 0)) / w.sum() for k, v in MEM.items()}


def gp(S, a, b):
    sgn = (-1.0 if a == "sa" else 1.0) * (-1.0 if b == "sa" else 1.0)
    return sgn * (S[f"{a}_{b}"] if f"{a}_{b}" in S else np.conj(S[f"{b}_{a}"]))


def CPF(S):
    Prr = np.maximum(np.real(gp(S, "r", "r")), 1e-30)
    C = U.smooth_c(gp(S, "e", "ufb") / np.maximum(np.real(gp(S, "e", "e")), 1e-30), 3)
    P = U.smooth_c(gp(S, "r", "y") / gp(S, "r", "u"), 5)
    F = U.smooth_c(gp(S, "r", "uff") / Prr, 3)
    Tm = U.smooth_c(gp(S, "r", "y") / Prr, 3)
    Zsa = U.smooth_c(gp(S, "r", "sa") / Prr, 3)
    return C, P, F, Tm, Zsa, Prr


def Tof(C, P, F):
    return (C * P + P * F) / (1.0 + C * P)


def lag_ms(H, Prr, b1, b2):
    return U.group_delay_ms(f, H, b1, b2)


iV = np.where((fam == "V282") & sel)[0]
iT = np.where((fam == "TORQ") & sel)[0]
CV, PV, FV, TmV, ZV, PrrV = CPF(pooled(iV))
CT, PT, FT, TmT, ZT, PrrT = CPF(pooled(iT))
W = (PrrV + PrrT) / 2.0

lines = [f"TEST 1 -- IS THE EXTRA LAG THE LOOP SHAPE?   tag {TAG}   {note}", ""]
lines.append("(a) IDENTITY CHECK.  T built from the three measured transfers vs T measured directly.")
lines.append("    This is algebraically exact when P is the IV estimate, so it only catches coding")
lines.append("    errors -- it is NOT evidence for the structure.  Printed so nobody reads it as such.")
for nm, (C, P, F, Tm) in (("V282", (CV, PV, FV, TmV)), ("TORQ", (CT, PT, FT, TmT))):
    r = Tof(C, P, F) - Tm
    s = U.band(f, 0.08, 1.2)
    lines.append(f"    {nm}: max |T_built - T_meas| over 0.08-1.2 Hz = {np.max(np.abs(r[s])):.2e}")
lines.append("")

lines.append("(b) THE LEG, RE-MEASURED (cross-spectral phase of the shaped setpoint -> wheel angle),")
lines.append("    beside the study's five-leg budget number for L34.")
lines.append(f"    {'band':<12}{'V282 ms':>10}{'TORQ ms':>10}{'gap ms':>10}   (budget L34 at 0.15-0.30: "
             f"107.7 / 305.0 / +197.2)")
for b1, b2 in BANDS:
    a, b = lag_ms(ZV, PrrV, b1, b2), lag_ms(ZT, PrrT, b1, b2)
    lines.append(f"    {b1:.2f}-{b2:.2f}   {a:>10.0f}{b:>10.0f}{b-a:>10.0f}")
lines.append("")
lines.append("    Same, on the loop's own output Y (the angle through the kinematic model):")
for b1, b2 in BANDS:
    a, b = lag_ms(TmV, PrrV, b1, b2), lag_ms(TmT, PrrT, b1, b2)
    lines.append(f"    {b1:.2f}-{b2:.2f}   {a:>10.0f}{b:>10.0f}{b-a:>10.0f}")
lines.append("")

# ---- Shapley attribution of the lag gap over the three measured transfers ----------------------
FACT = ["C", "P", "F"]
SRC = {"C": (CV, CT), "P": (PV, PT), "F": (FV, FT)}


def lag_combo(which, b1, b2):
    """which: dict factor -> 0 (V282's measured transfer) or 1 (the torque family's)."""
    C, P, F = (SRC[k][which[k]] for k in FACT)
    return lag_ms(Tof(C, P, F), W, b1, b2)


def shapley(b1, b2):
    base = {k: 0 for k in FACT}
    tot = lag_combo({k: 1 for k in FACT}, b1, b2) - lag_combo(base, b1, b2)
    phi = {k: 0.0 for k in FACT}
    for order in itertools.permutations(FACT):
        st = dict(base)
        prev = lag_combo(st, b1, b2)
        for k in order:
            st[k] = 1
            cur = lag_combo(st, b1, b2)
            phi[k] += (cur - prev) / 6.0
            prev = cur
    return tot, phi


lines.append("(c) ATTRIBUTION of the measured lag gap (Shapley over the 6 orderings of the three")
lines.append("    measured transfers).  'C' = the fork's feedback gain (kp/LAF and ki), 'P' = the")
lines.append("    PLANT (the EPS change), 'F' = the feedforward path (plant FF, ref filter, the")
lines.append("    torque builds' inner rate loop and observer).")
lines.append(f"    {'band':<12}{'gap ms':>9}{'C ms':>9}{'P ms':>9}{'F ms':>9}     |L| V282 -> TORQ")
res = {}
for b1, b2 in BANDS:
    tot, phi = shapley(b1, b2)
    lv = U.bandavg_mag(f, CV * PV, b1, b2, W)
    lt = U.bandavg_mag(f, CT * PT, b1, b2, W)
    res[f"{b1}-{b2}"] = dict(gap=tot, **phi, L_V282=lv, L_TORQ=lt)
    lines.append(f"    {b1:.2f}-{b2:.2f}   {tot:>9.0f}{phi['C']:>9.0f}{phi['P']:>9.0f}{phi['F']:>9.0f}"
                 f"        {lv:.3f} -> {lt:.3f}")
lines.append("")

# ---- one-at-a-time counterfactual transfers (the same algebra, shown plainly) -------------------
lines.append("(d) ONE FACTOR AT A TIME, from the V282 baseline (lag of T, ms).  Algebra on measured")
lines.append("    transfers -- read as attribution of a measured difference, not as a dose.")
lines.append(f"    {'band':<12}{'V282':>9}{'+C only':>9}{'+P only':>9}{'+F only':>9}{'all three':>11}")
for b1, b2 in BANDS:
    base = lag_combo({"C": 0, "P": 0, "F": 0}, b1, b2)
    cc = lag_combo({"C": 1, "P": 0, "F": 0}, b1, b2)
    pp = lag_combo({"C": 0, "P": 1, "F": 0}, b1, b2)
    ff = lag_combo({"C": 0, "P": 0, "F": 1}, b1, b2)
    al = lag_combo({"C": 1, "P": 1, "F": 1}, b1, b2)
    lines.append(f"    {b1:.2f}-{b2:.2f}   {base:>9.0f}{cc:>9.0f}{pp:>9.0f}{ff:>9.0f}{al:>11.0f}")
lines.append("")

# ---- route-cluster bootstrap on the attribution -------------------------------------------------
rng = np.random.default_rng(5)
rv = sorted(set(route[iV])); rt = sorted(set(route[iT]))
B = {b: {k: [] for k in ["gap"] + FACT} for b in [f"{a}-{c}" for a, c in BANDS]}
for _ in range(300):
    pv = np.concatenate([np.where((route == p) & (fam == "V282") & sel)[0] for p in rng.choice(rv, len(rv))])
    pt = np.concatenate([np.where((route == p) & (fam == "TORQ") & sel)[0] for p in rng.choice(rt, len(rt))])
    CV, PV, FV, TmV, ZV, _ = CPF(pooled(pv))
    CT, PT, FT, TmT, ZT, _ = CPF(pooled(pt))
    SRC = {"C": (CV, CT), "P": (PV, PT), "F": (FV, FT)}
    for b1, b2 in BANDS:
        t, ph = shapley(b1, b2)
        B[f"{b1}-{b2}"]["gap"].append(t)
        for k in FACT:
            B[f"{b1}-{b2}"][k].append(ph[k])
lines.append("(e) ROUTE-CLUSTER BOOTSTRAP (300 draws, routes resampled within family), 5-95%:")
lines.append(f"    {'band':<12}{'gap ms':>20}{'C ms':>20}{'P ms':>20}{'F ms':>20}")
for b1, b2 in BANDS:
    k = f"{b1}-{b2}"
    cell = lambda z: f"[{np.nanpercentile(B[k][z],5):6.0f},{np.nanpercentile(B[k][z],95):6.0f}]"
    lines.append(f"    {b1:.2f}-{b2:.2f}   {cell('gap'):>17}{cell('C'):>20}{cell('P'):>20}{cell('F'):>20}")
    res[k]["ci"] = {z: [float(np.nanpercentile(B[k][z], 5)), float(np.nanpercentile(B[k][z], 95))] for z in ["gap"] + FACT}

json.dump(dict(tag=TAG, note=note, res=res), open(f"u3_{TAG}.json", "w"), indent=1, default=float)
txt = "\n".join(lines)
open(f"U3-{TAG.upper()}-OUT.txt", "w").write(txt)
print(txt)
