# -*- coding: utf-8 -*-
"""d4 -- THE FLOOR.  One asymptote with a CI, and the delay-limited floor underneath it.

FIVE-TERM EXACT DECOMPOSITION (each step algebra, no model):

    X - Y  =  [X - Yc]  +  [Yc - Y]
    Yc = Y * exp(+j w tau_i)   is Y with the INSTRUMENT lag taken out, so
    [Yc - Y] = Y (exp(j w tau_i) - 1)                                       (e) instrument
    [X - Yc] = (X - Z) + (1 - Vc) Z + Vc D - rc,   Vc = V exp(j w tau_i),   rc = Yc - Vc M
              ^ (b)      ^ (c)         ^ (a)        ^ (d)

tau_i is measured, not assumed: it is the group delay of the MEASURED wheel-angle -> yaw transfer
where its coherence is 0.80-0.99, and NO linear vehicle can have a constant ~100 ms group delay from
steering angle to yaw rate (the bicycle model's is -12 to +20 ms and it is a LEAD at low frequency,
from the m*a*v/(Cr*L) zero).  So it is the livePose publish latency, not the car.
  -> it is UNREACHABLE either way: V is outside the feedback loop.  The split only changes the LABEL.

THE FLOOR, three levels, each a different question:
  L1  infinite loop gain, any compensator                 -- the algebraic limit of the class
  L2  best realizable loop with the MEASURED 55-75 ms     -- what a fork-side redesign could reach
  L3  the fork's actual PI+notch structure, SteerKP free  -- what THIS controller can reach
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
import lp_lib as LP                         # noqa: E402
from f5_frontier import Engine, C_of, FLOWN  # noqa: E402

BAND = (0.15, 2.4)
GAPBAND = (0.15, 0.60)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
JREF = 0.442            # the brief's V282 reference
JREF_OWN = 0.4705       # this kit's own re-derivation on the same windows
JFLOWN = 1.3512


def gather(routes):
    cols = {k: [] for k in ("X", "Y", "Z", "M", "UFB", "UFF", "U")}
    vm, rid = [], []
    f = None
    for n, r in enumerate(routes):
        D = np.load(FRONT / f"f1_{r}.npz")
        f = D["f"]
        for k in cols:
            cols[k].append(D[k])
        vm.append(D["vmed"])
        rid.append(np.full(len(D["vmed"]), n))
        del D
    return dict(f=f, v=np.concatenate(vm), rid=np.concatenate(rid),
                **{k: np.concatenate(v) for k, v in cols.items()})


# ---------------------------------------------------------------- 1. the instrument lag on Y
def instrument_lag():
    D = np.load(OUT / "d3_broadV.npz")
    f, H1, coh, Smm, boots = D["f"], D["H1"], D["coh"], D["Smm"], D["boots"]
    s = (f >= 0.12) & (f <= 1.2) & (coh >= 0.60)
    w = Smm[s] * coh[s]
    ph = np.unwrap(np.angle(H1))[s]
    # weighted least squares of phase on frequency through the origin: slope = -2 pi tau
    tau = -float(np.sum(w * ph * f[s]) / np.sum(w * f[s] ** 2)) / (2 * np.pi)
    bt = []
    for b in boots:
        pb = np.unwrap(np.angle(b))[s]
        bt.append(-float(np.sum(w * pb * f[s]) / np.sum(w * f[s] ** 2)) / (2 * np.pi))
    ci = (float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5)))
    print("=" * 108)
    print("1. THE INSTRUMENT LAG ON Y (livePose yaw vs carState steering angle, both logMonoTime)")
    print(f"   group delay of the measured angle->yaw transfer, 0.12-1.2 Hz, coh >= 0.60:")
    print(f"     tau_i = {tau*1000:.1f} ms   95% CI [{ci[0]*1000:.1f}, {ci[1]*1000:.1f}]")
    print(f"   bicycle model's own group delay over the same band: -12 to +20 ms (a LEAD at low f).")
    print(f"   => {tau*1000:.0f} ms is the localiser's publish latency.  EVIDENCE (measurement + the")
    print(f"      physical impossibility of transport delay between a steering angle and a yaw rate).")
    return tau, ci


# ---------------------------------------------------------------- 2. the screened V
def screened_V(fgrid):
    """Interpolate the broad-window H1 (584 windows, 3738 s, 7x the metric's data) onto the metric grid."""
    D = np.load(OUT / "d3_broadV.npz")
    f, H1, boots = D["f"], D["H1"], D["boots"]
    def onto(H):
        mag = np.interp(fgrid, f, np.abs(H))
        pha = np.interp(fgrid, f, np.unwrap(np.angle(H)))
        return mag * np.exp(1j * pha)
    return onto(H1), np.array([onto(b) for b in boots])


def five_way(W, Vf, tau_i, sel, px):
    f = W["f"]
    X, Y, Z, M = W["X"], W["Y"], W["Z"], W["M"]
    E = X - Y
    ph = np.exp(2j * np.pi * f * tau_i)[None, :]
    Yc = Y * ph
    Vc = Vf[None, :] * ph
    T = {
        "a_loop": Vc * (Z - M),
        "b_setpoint": X - Z,
        "c_wheel2yaw": (1.0 - Vc) * Z,
        "d_incoh": -(Yc - Vc * M),
        "e_instrument": Yc - Y,
    }
    chk = sum(T.values()) - E
    pe = float(np.sum(np.abs(E[:, sel]) ** 2))
    acct = {}
    for k, A in T.items():
        acct[k] = dict(own=float(np.sum(np.abs(A[:, sel]) ** 2)) / px,
                       share=float(np.sum(np.real(np.conj(E[:, sel]) * A[:, sel]))) / pe)
    acct["_J"] = pe / px
    acct["_rel"] = float(np.sqrt(np.sum(np.abs(chk[:, sel]) ** 2) / pe))
    acct["_sum"] = sum(v["share"] for k, v in acct.items() if not k.startswith("_"))
    # the asymptote: kill a_loop
    A_inf = E - T["a_loop"]
    acct["_J_inf"] = float(np.sum(np.abs(A_inf[:, sel]) ** 2)) / px
    return acct, T, E


def part2(tau_i):
    print("\n" + "=" * 108)
    print("2. THE FIVE-WAY DECOMPOSITION, with the SCREENED V (broad-window H1) and the measured tau_i")
    res = {}
    for lab, routes in (("T64 (torque, rev 6.4)", T64), ("V282 (reference)", V282R)):
        W = gather(routes)
        f = W["f"]
        Vf, Vboots = screened_V(f)
        for tag, (lo, hi) in (("0.15-2.4 (the metric)", BAND), ("0.15-0.60 (98% of the gap)", GAPBAND)):
            sel = (f >= lo) & (f <= hi)
            px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
            acct, T, E = five_way(W, Vf, tau_i, sel, px)
            print(f"\n  {lab}   band {tag}   J {acct['_J']:.4f}   "
                  f"(identity rel {acct['_rel']:.1e}, shares sum {acct['_sum']:.6f})")
            print(f"    {'term':16s} {'reachable by':22s} {'own/|X|^2':>10s} {'SHARE':>8s} {'x J':>8s}")
            lbl = {"a_loop": "LOOP GAIN", "b_setpoint": "reference-path code only",
                   "c_wheel2yaw": "NOTHING (outside loop)", "d_incoh": "NOTHING (exogenous)",
                   "e_instrument": "NOTHING (not the car)"}
            for k in ("a_loop", "b_setpoint", "c_wheel2yaw", "d_incoh", "e_instrument"):
                a = acct[k]
                print(f"    {k:16s} {lbl[k]:22s} {a['own']:10.4f} {a['share']:8.3f} "
                      f"{a['share']*acct['_J']:8.4f}")
            res[f"{lab}|{tag}"] = acct
        # asymptote with a CI over the V bootstrap
        sel = (f >= BAND[0]) & (f <= BAND[1])
        px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
        jinf = []
        for Vb in Vboots[:300]:
            a, _, _ = five_way(W, Vb, tau_i, sel, px)
            jinf.append(a["_J_inf"])
        base, _, _ = five_way(W, Vf, tau_i, sel, px)
        print(f"\n  {lab}: J_inf (infinite loop gain) = {base['_J_inf']:.4f}  "
              f"95% CI over the V bootstrap [{np.percentile(jinf,2.5):.4f}, {np.percentile(jinf,97.5):.4f}]")
        res[f"{lab}|Jinf"] = dict(point=base["_J_inf"],
                                  ci=[float(np.percentile(jinf, 2.5)), float(np.percentile(jinf, 97.5))])
        del W
    return res


# ---------------------------------------------------------------- 3. the delay-limited floor
def part3(tau_i):
    print("\n" + "=" * 108)
    print("3. THE DELAY-LIMITED FLOOR.  The metric's a_loop term scales by rho = (1+L0)/(1+L1).")
    print("   L1 is swept over REALIZABLE loops: L1 = (wc/s) * exp(-s*Td) / (1 + s/wa), wa = 5.05 Hz")
    print("   (the firmware's own measured output-lag cell), Td the measured loop delay.  wc is set by")
    print("   the phase-margin budget.  This is the best ANY fork-side compensator can do at that delay.")
    W = gather(T64)
    f = W["f"]
    Vf, _ = screened_V(f)
    sel = (f >= BAND[0]) & (f <= BAND[1])
    px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
    eng = Engine()
    L0 = eng.L0                       # measured loop as flown, per window
    E = W["X"] - W["Y"]
    D = W["Z"] - W["M"]
    ph = np.exp(2j * np.pi * f * tau_i)[None, :]
    Vc = Vf[None, :] * ph
    s = 2j * np.pi * np.maximum(f, 1e-6)
    wa = 2 * np.pi * 5.05
    shk = (f >= 1.8) & (f <= 3.5)
    print(f"\n    {'Td ms':>6s} {'PM budget':>10s} {'wc Hz':>7s} {'J':>8s} {'closure vs 0.442':>17s} "
          f"{'|S| peak':>9s} {'|S| 1.8-3.5':>12s}")
    rows = []
    for Td in (0.0553, 0.065, 0.075):
        for pm in (60.0, 45.0, 30.0):
            # find wc: arg L1(wc) = -180 + pm
            lo, hi = 0.05, 20.0
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                w = 2 * np.pi * mid
                a = -90.0 - np.degrees(w * Td) - np.degrees(np.arctan(w / wa))
                if a > -180.0 + pm:
                    lo = mid
                else:
                    hi = mid
            wc = 0.5 * (lo + hi)
            L1 = (2 * np.pi * wc / s)[None, :] * np.exp(-s * Td)[None, :] / (1.0 + s / wa)[None, :]
            rho = (1.0 + L0) / (1.0 + L1)
            E1 = E + Vc * D * (rho - 1.0)
            J = float(np.sum(np.abs(E1[:, sel]) ** 2)) / px
            S1 = np.abs(1.0 / (1.0 + L1))
            rows.append(dict(Td=Td, pm=pm, wc=wc, J=J,
                             closure=(JFLOWN - J) / (JFLOWN - JREF),
                             Speak=float(np.max(np.mean(S1, 0)[(f >= 0.1) & (f <= 5.0)])),
                             Sshake=float(np.mean(np.mean(S1, 0)[shk]))))
            r = rows[-1]
            print(f"    {Td*1000:6.1f} {pm:10.0f} {wc:7.3f} {J:8.4f} {r['closure']*100:16.1f}% "
                  f"{r['Speak']:9.2f} {r['Sshake']:12.2f}")
    print("\n    (|S| > 1 in 1.8-3.5 Hz is the waterbed: every one of these loops AMPLIFIES the")
    print("     shake band, on a plant whose gain there is already 5.3-13x V282's.)")
    del W
    return rows


# ---------------------------------------------------------------- 4. what ARM-KP2 actually moves
def part4(tau_i):
    print("\n" + "=" * 108)
    print("4. WHAT ARM-KP2 (SteerKP 3.0 + AccordErrorNotchQ 0.60) ACTUALLY MOVES, term by term")
    eng = Engine()
    W = gather(T64)
    f = W["f"]
    Vf, _ = screened_V(f)
    ph = np.exp(2j * np.pi * f * tau_i)[None, :]
    Vc = Vf[None, :] * ph
    sel = (f >= BAND[0]) & (f <= BAND[1])
    px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
    E = W["X"] - W["Y"]
    D = W["Z"] - W["M"]
    print(f"    {'config':28s} {'J':>7s} {'clos%':>6s} | {'a_loop own':>11s} {'b own':>7s} "
          f"{'c own':>7s} {'d own':>7s} {'e own':>7s}")
    out = {}
    for name, kp, q in (("as flown (rev 6.4)", 1.0, 1.0), ("ARM-KP  SteerKP 2.0", 2.0, 1.0),
                        ("ARM-KP2 KP 3.0 + Q 0.60", 3.0, 0.60), ("SteerKP 6.0 (needs code)", 6.0, 0.60),
                        ("SteerKP 12.0 (needs code)", 12.0, 0.60), ("infinite gain", None, None)):
        if kp is None:
            rho = np.zeros_like(E)
        else:
            C1 = C_of(f, eng.v, kp, 14.0, FLOWN["ki"], 0.0, q)
            L1 = eng.L0 * (C1 / eng.C0)
            rho = (1.0 + eng.L0) / (1.0 + L1)
        E1 = E + Vc * D * (rho - 1.0)
        T = {"a": Vc * D * rho, "b": W["X"] - W["Z"], "c": (1.0 - Vc) * W["Z"],
             "d": -(W["Y"] * ph - Vc * W["M"]), "e": W["Y"] * ph - W["Y"]}
        J = float(np.sum(np.abs(E1[:, sel]) ** 2)) / px
        own = {k: float(np.sum(np.abs(v[:, sel]) ** 2)) / px for k, v in T.items()}
        print(f"    {name:28s} {J:7.4f} {(JFLOWN-J)/(JFLOWN-JREF)*100:6.1f} | "
              f"{own['a']:11.4f} {own['b']:7.4f} {own['c']:7.4f} {own['d']:7.4f} {own['e']:7.4f}")
        out[name] = dict(J=J, closure=(JFLOWN - J) / (JFLOWN - JREF), own=own)
    print("\n    b, c, d and e are IDENTICAL in every row -- by construction, no feedback gain touches them.")
    print("    Only a_loop moves, and it is bounded below by 0.")
    del W
    return out


if __name__ == "__main__":
    tau_i, ci = instrument_lag()
    r = {}
    r["tau_i"] = [tau_i, ci]
    r["decomp"] = part2(tau_i)
    r["floor"] = part3(tau_i)
    r["armkp2"] = part4(tau_i)
    json.dump(r, open(OUT / "d4_floor.json", "w"), indent=1, default=float)
    print("\nwrote out/d4_floor.json")
