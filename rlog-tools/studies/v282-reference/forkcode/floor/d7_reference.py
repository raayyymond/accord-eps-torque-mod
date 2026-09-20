# -*- coding: utf-8 -*-
"""d7 -- HOW MUCH OF THE GAP IS A REFERENCE PROBLEM, and the consolidated reachability budget.

WHY THIS MATTERS.  latcontrol_torque.py:639 -- curv_des = (setpoint - latAccelOffset*fade)/v^2 --
so the rate-plant FEEDFORWARD, which carries 1.00-1.05 of the command, is driven by the SHAPED
SETPOINT Z, not by the raw demand.  A reference change therefore reaches the wheel through an
OPEN-LOOP path and is NOT limited by the complementary sensitivity.  That is measured here as
H_ZM = S_ZM/S_ZZ, the actual reference -> wheel-angle transfer.

THE REFERENCE-CLASS BOUND.  The fork can put any LTI filter W(f) on the setpoint.  Then
    M' = M + H_ZM (W-1) Z ,   Y' = Y + V H_ZM (W-1) Z ,   E' = E - V H_ZM (W-1) Z
Per FFT bin, minimising sum|E'|^2 over the free complex (W-1) is a projection: the best any
reference prefilter can do is remove the part of E that is COHERENT WITH Z.  That is an UPPER
bound on the class (the optimum need not be causal), and it is computed on measured objects only.

CONSOLIDATED BUDGET: what each class of fork change can buy, on the same denominator.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
sys.path.insert(0, str(HERE.parents[1] / "shapedgain" / "frontier"))
import lp_lib as LP                          # noqa: E402
from f5_frontier import Engine, C_of, FLOWN  # noqa: E402

BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
TAU_I = 0.102
JREF, JFLOWN = 0.442, 1.3512


def gather(routes):
    cols = {k: [] for k in ("X", "Y", "Z", "M", "U", "UFB", "UFF")}
    f = None
    for r in routes:
        D = np.load(FRONT / f"f1_{r}.npz")
        f = D["f"]
        for k in cols:
            cols[k].append(D[k])
        del D
    return dict(f=f, **{k: np.concatenate(v) for k, v in cols.items()})


def screened_V(fgrid, boots=False):
    D = np.load(OUT / "d3_broadV.npz")
    f, H1, bb = D["f"], D["H1"], D["boots"]
    o = lambda H: np.interp(fgrid, f, np.abs(H)) * np.exp(1j * np.interp(fgrid, f, np.unwrap(np.angle(H))))
    return (o(H1), np.array([o(b) for b in bb])) if boots else o(H1)


def part_a():
    print("=" * 108)
    print("A. REFERENCE AUTHORITY.  H_ZM = shaped setpoint -> wheel-angle measurement, measured.")
    print("   If the reference only acted through the feedback it would be bounded by |T| = |L/(1+L)|,")
    print("   which is 0.24-0.28 in band.  The feedforward is what makes it near unity.")
    print(f"   {'band Hz':12s} {'|H_ZM|':>7s} {'arg deg':>8s} {'coh':>6s} {'|T| = |L/(1+L)|':>17s}")
    eng = Engine()
    W = gather(T64)
    f = W["f"]
    Z, M = W["Z"], W["M"]
    H = np.sum(np.conj(Z) * M, 0) / np.sum(np.abs(Z) ** 2, 0)
    coh = np.abs(np.sum(np.conj(Z) * M, 0)) ** 2 / (np.sum(np.abs(Z) ** 2, 0) * np.sum(np.abs(M) ** 2, 0))
    Lm = np.mean(eng.L0, 0)
    T = np.abs(Lm / (1.0 + Lm))
    wz = np.sum(np.abs(Z) ** 2, 0)
    rec = {}
    for lo, hi in SUB:
        s = (f >= lo) & (f < hi)
        h = float(np.average(np.abs(H[s]), weights=wz[s]))
        print(f"   {lo:5.2f}-{hi:4.2f}   {h:7.3f} {np.degrees(np.angle(np.sum(np.conj(Z[:, s])*M[:, s]))):8.1f} "
              f"{float(np.average(coh[s], weights=wz[s])):6.3f} {float(np.average(T[s], weights=wz[s])):17.3f}")
        rec[f"{lo}-{hi}"] = h
    print("   => the reference path has ~unity authority over the wheel.  b_setpoint IS reachable,")
    print("      by reference-path code -- and NOT by gain (d4 part 4 shows it identical at every KP).")
    del W
    return rec


def part_b():
    print("\n" + "=" * 108)
    print("B. THE REFERENCE-CLASS BOUND: the best any LTI setpoint prefilter can do, per bin.")
    eng = Engine()
    res = {}
    for lab, routes in (("T64", T64), ("V282", V282R)):
        W = gather(routes)
        f = W["f"]
        Vf = screened_V(f)
        ph = np.exp(2j * np.pi * f * TAU_I)[None, :]
        Vc = Vf[None, :] * ph
        sel = (f >= BAND[0]) & (f <= BAND[1])
        px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
        Z, M, X, Y = W["Z"], W["M"], W["X"], W["Y"]
        E = X - Y
        H = (np.sum(np.conj(Z) * M, 0) / np.sum(np.abs(Z) ** 2, 0))[None, :]
        G = Vc * H * Z                                   # the direction a reference change moves E
        num = np.sum(np.conj(G) * E, 0)
        den = np.sum(np.abs(G) ** 2, 0)
        k = (num / np.maximum(den, 1e-300))[None, :]
        Eref = E - k * G
        Jr = float(np.sum(np.abs(Eref[:, sel]) ** 2)) / px
        # and with the loop ALSO at infinite gain
        D = Z - M
        Einf = E - Vc * D
        num2 = np.sum(np.conj(G) * Einf, 0)
        k2 = (num2 / np.maximum(den, 1e-300))[None, :]
        Jb = float(np.sum(np.abs((Einf - k2 * G)[:, sel]) ** 2)) / px
        J0 = float(np.sum(np.abs(E[:, sel]) ** 2)) / px
        Ji = float(np.sum(np.abs(Einf[:, sel]) ** 2)) / px
        print(f"\n   {lab}:  J as flown {J0:.4f}")
        print(f"     best LTI reference prefilter, loop AS FLOWN        J {Jr:.4f}  "
              f"closure {(JFLOWN-Jr)/(JFLOWN-JREF)*100:5.1f}%" if lab == "T64" else
              f"     best LTI reference prefilter, loop AS FLOWN        J {Jr:.4f}")
        print(f"     infinite loop gain, reference AS FLOWN             J {Ji:.4f}"
              + (f"  closure {(JFLOWN-Ji)/(JFLOWN-JREF)*100:5.1f}%" if lab == "T64" else ""))
        print(f"     BOTH (infinite gain + best prefilter)              J {Jb:.4f}"
              + (f"  closure {(JFLOWN-Jb)/(JFLOWN-JREF)*100:5.1f}%" if lab == "T64" else ""))
        res[lab] = dict(J=J0, J_ref=Jr, J_inf=Ji, J_both=Jb)
        del W
    return res


def part_c():
    print("\n" + "=" * 108)
    print("C. CONSOLIDATED REACHABILITY BUDGET for the torque build (T64, rev 6.4 as flown).")
    print("   Every row is J on the same denominator; 'gap' is measured against the brief's V282 0.442.")
    eng = Engine()
    W = gather(T64)
    f = W["f"]
    Vf, Vb = screened_V(f, boots=True)
    ph = np.exp(2j * np.pi * f * TAU_I)[None, :]
    Vc = Vf[None, :] * ph
    sel = (f >= BAND[0]) & (f <= BAND[1])
    px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
    X, Y, Z, M = W["X"], W["Y"], W["Z"], W["M"]
    E = X - Y
    D = Z - M
    H = (np.sum(np.conj(Z) * M, 0) / np.sum(np.abs(Z) ** 2, 0))[None, :]
    G = Vc * H * Z
    inv = np.conj(ph)
    rc = Y * ph - Vc * M

    def J(e):
        return float(np.sum(np.abs(e[:, sel]) ** 2)) / px

    def proj_out(e):
        k = (np.sum(np.conj(G) * e, 0) / np.maximum(np.sum(np.abs(G) ** 2, 0), 1e-300))[None, :]
        return e - k * G

    rows = []
    def add(name, j, note):
        rows.append(dict(name=name, J=j, gap_closed=(JFLOWN - j) / (JFLOWN - JREF), note=note))

    add("as flown (rev 6.4)", J(E), "-")
    for nm, kp, q in (("ARM-KP2  KP 3.0 Q 0.60 (toggle ceiling)", 3.0, 0.60),
                      ("SteerKP 6.0  (needs STEER_KP_MAX_MULT)", 6.0, 0.60),
                      ("SteerKP 12.0 (needs STEER_KP_MAX_MULT)", 12.0, 0.60)):
        C1 = C_of(f, eng.v, kp, 14.0, FLOWN["ki"], 0.0, q)
        L1 = eng.L0 * (C1 / eng.C0)
        rho = (1.0 + eng.L0) / (1.0 + L1)
        add(nm, J(E + Vc * D * (rho - 1.0)), "loop gain only")
    add("best LTI reference prefilter, loop as flown", J(proj_out(E)), "reference code only")
    add("delay-limited ideal loop, 65 ms, PM 45 deg", 0.4877, "from d4 part 3")
    add("infinite loop gain (algebraic limit)", J(E - Vc * D), "no fork can exceed")
    add("infinite gain + best prefilter", J(proj_out(E - Vc * D)), "both classes maxed")
    add("PERFECT car: only the 102 ms instrument", J(X * (1.0 - inv)), "not reachable by anything")
    print(f"   {'configuration':45s} {'J':>8s} {'gap closed':>11s}   note")
    for r in rows:
        print(f"   {r['name']:45s} {r['J']:8.4f} {r['gap_closed']*100:10.1f}%   {r['note']}")
    print(f"\n   V282 reference: brief {JREF:.4f} | this kit's own re-derivation on the same windows 0.4705")
    # CI on the two floors
    ji, jb = [], []
    for Vx in Vb[:300]:
        Vcx = Vx[None, :] * ph
        Gx = Vcx * H * Z
        Ex = E - Vcx * D
        kx = (np.sum(np.conj(Gx) * Ex, 0) / np.maximum(np.sum(np.abs(Gx) ** 2, 0), 1e-300))[None, :]
        ji.append(J(Ex))
        jb.append(J(Ex - kx * Gx))
    print(f"   95% CI over the V bootstrap:  infinite gain [{np.percentile(ji,2.5):.4f}, "
          f"{np.percentile(ji,97.5):.4f}]   infinite gain + prefilter [{np.percentile(jb,2.5):.4f}, "
          f"{np.percentile(jb,97.5):.4f}]")
    del W
    return rows, [float(np.percentile(ji, 2.5)), float(np.percentile(ji, 97.5))], \
        [float(np.percentile(jb, 2.5)), float(np.percentile(jb, 97.5))]


def part_d():
    print("\n" + "=" * 108)
    print("D. ARM-KP2 re-priced on BOTH V's, so it is comparable to the brief's 33.3 %")
    eng = Engine()
    W = gather(T64)
    f = W["f"]
    Vs = screened_V(f) [None, :] * np.exp(2j * np.pi * f * TAU_I)[None, :]
    sel = (f >= BAND[0]) & (f <= BAND[1])
    px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
    E = W["X"] - W["Y"]
    D = W["Z"] - W["M"]
    print(f"   {'config':28s} {'V = frontier V_h1':>19s} {'V = screened (d3)':>19s}")
    for nm, kp, q in (("as flown", 1.0, 1.00), ("ARM-KP 2.0", 2.0, 1.00),
                      ("ARM-KP2 3.0 + Q0.60", 3.0, 0.60), ("infinite gain", None, None)):
        out = []
        for Vv in (eng.V, Vs):
            if kp is None:
                rho = np.zeros_like(E)
            else:
                C1 = C_of(f, eng.v, kp, 14.0, FLOWN["ki"], 0.0, q)
                rho = (1.0 + eng.L0) / (1.0 + eng.L0 * (C1 / eng.C0))
            j = float(np.sum(np.abs((E + Vv * D * (rho - 1.0))[:, sel]) ** 2)) / px
            out.append((j, (JFLOWN - j) / (JFLOWN - JREF) * 100))
        print(f"   {nm:28s}   J {out[0][0]:6.4f} ({out[0][1]:5.1f}%)   J {out[1][0]:6.4f} ({out[1][1]:5.1f}%)")
    print("   The brief's ARM-KP2 = J 1.058 / 33.3 %.  The frontier's V_h1 column reproduces it;")
    print("   the screened V moves it because V_h1 over-reads |V| above 1 Hz (d3).")
    del W


if __name__ == "__main__":
    o = {}
    o["Hzm"] = part_a()
    o["refbound"] = part_b()
    rows, ci_i, ci_b = part_c()
    o["budget"] = rows
    o["ci_inf"] = ci_i
    o["ci_both"] = ci_b
    part_d()
    json.dump(o, open(OUT / "d7.json", "w"), indent=1, default=float)
    print("\nwrote out/d7.json")
