# -*- coding: utf-8 -*-
"""Stage 2: THE STAGE BUDGET.  Every leg between the model and the road, per band x speed, both builds.

METHOD.  Every leg is referenced to the SAME exogenous input X (the model's desired lateral accel):

    T_s(f) = Pxs(f) / Pxx(f)                       s in {Z0, Z, U, M, W, Y}
    leg gain      g_i(f) = |T_i(f) / T_{i-1}(f)|           (T_0 == 1)
    leg lag       tau_i(f) = -angle(T_i/T_{i-1}) / (2 pi f)

so the legs TELESCOPE: prod_i g_i == |T_Y| and sum_i tau_i == tau_end-to-end, per bin, exactly.
Band values are power-weighted means over the band's bins with the SAME weights for every leg, so the
closure survives the averaging for the lags (a weighted mean is linear) but NOT for the gains (a
product of means is not the mean of products).  Both closure errors are printed.

Referencing every leg to X is what makes this legitimate in a CLOSED LOOP: the part of each node that
the road, the roll or the sensor noise drives is incoherent with X and drops out of Pxs.  What is
being measured is where the demand-coherent phase and gain accumulate along the physical chain.  It
is NOT an open-loop identification of each block -- leg 3 in particular is the closed-loop
sensitivity of the command to the setpoint, not the controller's own transfer.  MEASUREMENT, not
prediction.

Legs:
  L1 canceller+jerk   X  -> Z0    fork software (delay compensation + jerk LP), replay-validated
  L2 ref filter       Z0 -> Z     fork software (two cascaded FirstOrderFilters at AccordRefFilter)
  L3 controller       Z  -> U     setpoint to command: FF + P/I + notch + observer, closed loop
  L4 EPS + rack       U  -> M     command to WHEEL ANGLE (in demand units).  The firmware lives here.
  L5 vehicle          M  -> Y     wheel angle to achieved yaw.  Build-independent => the CONTROL.

ANALYSIS ONLY, read-only.  usage: python sb_budget.py > out/BUDGET-OUT.txt
"""
import sys

import numpy as np

import sb_lib as L

CHAIN = ["Z0", "Z", "U", "M", "Y"]
LEGN = ["L1 canc+jerk X->Z0", "L2 ref filter Z0->Z", "L3 controller Z->U",
        "L4 EPS+rack   U->M", "L5 vehicle    M->Y"]
LEGS = ["L1", "L2", "L3", "L4", "L5"]
POOL = {"TORQ": L.TORQ, "TQ_J12": L.TORQ_J12, "T64F": ["T64", "T64B"]}
rng = np.random.default_rng(11)
NB = 400


class Spec:
    def __init__(self, W):
        d = np.load(L.HERE / "out" / f"spec_{W:.2f}.npz", allow_pickle=True)
        self.W = W
        self.fr = np.arange(d["X"].shape[1]) / W
        self.d = {k: d[k] for k in ("X", "Z0", "Z", "U", "M", "W", "Y", "T")}
        self.route = d["route"]; self.group = d["group"]; self.sbin = d["sbin"]; self.v = d["v"]
        self.am = d["am_med"]; self.ap95 = d["am_p95"]; self.rail = d["rail"]
        self.lagD = d["lagD"]; self.clipraw = d["clipraw"]

    def sel(self, grp, sb=None, acut=None):
        gs = POOL.get(grp, [grp])
        m = np.isin(self.group, gs)
        if sb is not None:
            m &= (self.sbin == sb)
        if acut is not None:
            m &= (self.am >= acut[0]) & (self.am < acut[1])
        return np.where(m)[0]


def accum(S, idx, nodes=CHAIN):
    X = S.d["X"][idx]
    Pxx = np.sum(np.abs(X) ** 2, 0)
    out = {"Pxx": Pxx}
    for nd in nodes:
        A = S.d[nd][idx]
        out["Px" + nd] = np.sum(np.conj(X) * A, 0)
        out["P" + nd] = np.sum(np.abs(A) ** 2, 0)
    return out


def legs_from(acc, sl, nodes=CHAIN):
    """Per-bin leg gain and leg lag inside the band slice, plus the end-to-end transfer."""
    w = acc["Pxx"][sl]
    T = [np.ones(w.shape, complex)]
    for nd in nodes:
        T.append(acc["Px" + nd][sl] / np.maximum(acc["Pxx"][sl], 1e-300))
    f = acc["_fr"][sl]
    g, tau = [], []
    for i in range(1, len(T)):
        r = T[i] / np.where(np.abs(T[i - 1]) < 1e-300, 1e-300, T[i - 1])
        g.append(np.abs(r))
        tau.append(-np.unwrap(np.angle(r)) / (2 * np.pi * f))
    return w, np.array(g), np.array(tau), T, f


def cell(S, idx, f1, f2, nodes=CHAIN):
    if len(idx) == 0:
        return None
    acc = accum(S, idx, nodes)
    acc["_fr"] = S.fr
    sl = (S.fr >= f1) & (S.fr < f2)
    if sl.sum() < 2:
        return None
    w, g, tau, T, f = legs_from(acc, sl, nodes)
    ws = w.sum()
    gb = (g * w).sum(1) / ws
    tb = (tau * w).sum(1) / ws
    Tend = T[-1]
    g_end = float((np.abs(Tend) * w).sum() / ws)
    t_end = float((-np.unwrap(np.angle(Tend)) / (2 * np.pi * f) * w).sum() / ws)
    coh = {}
    for nd in nodes:
        c = np.abs(acc["Px" + nd][sl]) ** 2 / np.maximum(acc["Pxx"][sl] * acc["P" + nd][sl], 1e-300)
        coh[nd] = float((c * w).sum() / ws)
    nind = max(int(round(len(idx) * 0.25)), 1)
    flr = 1.0 - 0.05 ** (1.0 / max(nind - 1, 1))
    return dict(n=len(idx), nind=nind, g=gb, tau=tb, g_end=g_end, t_end=t_end,
                coh=coh, flr=flr, f=float((f * w).sum() / ws),
                v=float(np.median(S.v[idx])), am=float(np.median(S.am[idx])),
                rail=float(np.mean(S.rail[idx])), clip=float(np.mean(S.clipraw[idx])),
                D=float(np.median(S.lagD[idx])), nroute=len(set(S.route[idx].tolist())),
                inrms=float(np.sqrt(w.sum() / len(idx))))


def boot(S, idx, f1, f2, stat, nb=NB, nodes=CHAIN):
    """Route-cluster bootstrap CI: resample the cell's ROUTES with replacement."""
    rs = np.array(sorted(set(S.route[idx].tolist())))
    if len(rs) < 2:
        return None
    byr = {r: idx[S.route[idx] == r] for r in rs}
    vals = []
    for _ in range(nb):
        pick = rng.choice(len(rs), len(rs), replace=True)
        jj = np.concatenate([byr[rs[k]] for k in pick])
        c = cell(S, jj, f1, f2, nodes)
        if c:
            vals.append(stat(c))
    if not vals:
        return None
    a = np.array(vals)
    return np.percentile(a, 2.5, axis=0), np.percentile(a, 97.5, axis=0)


def fmt_cell(c):
    return (f"n{c['n']:>4d}/{c['nroute']}r v{c['v']:5.1f} A{c['am']:.4f} "
            f"coh " + "/".join(f"{c['coh'][k]:.2f}" for k in CHAIN) + f" flr{c['flr']:.2f}")


def main():
    print("=" * 155)
    print("THE STAGE BUDGET -- model desired lateral accel -> road, cut into five legs, both EPS builds.")
    print("  L1 canceller+jerk (X->Z0)  L2 ref filter (Z0->Z)  L3 controller (Z->U)  L4 EPS+rack (U->M)  L5 vehicle (M->Y)")
    print("  gain = power-weighted mean |leg|.  lag ms = power-weighted mean of -phase/(2 pi f), + = lags.")
    print("  CLOSURE: sum of leg lags vs the directly measured end-to-end lag; product of leg gains vs |H| end to end.")
    print("  U is a TORQUE request on the torque builds and a RATE request on V282, so L4's GAIN is not")
    print("  comparable between builds (its units differ); L4's LAG is.  L5 is the build-independent control.")
    print("=" * 155)

    GRPS = ["V282", "V282old", "TORQ", "TQ_J12", "T64F", "T5", "T4", "T3", "T2"]
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz   (window {W:.2f} s, "
              f"{int(((S.fr>=f1)&(S.fr<f2)).sum())} bins)")
        print(f"{'speed':6s} {'group':8s} {'n/routes':>10s} {'v':>5s} {'medA':>7s} | "
              + " ".join(f"{nm.split()[0]+' gain':>10s} {nm.split()[0]+' lag':>9s}" for nm in LEGN)
              + f" | {'TOT gain':>9s} {'TOT lag':>8s} | {'clos g':>7s} {'clos lag':>8s} | coh X->Z/U/M/Y")
        for sb in range(4):
            for grp in GRPS:
                idx = S.sel(grp, sb)
                c = cell(S, idx, f1, f2)
                if c is None or c["n"] < 6:
                    continue
                gp = float(np.prod(c["g"])); ts = float(np.sum(c["tau"]))
                print(f"{L.SPDN[sb]:6s} {grp:8s} {c['n']:>6d}/{c['nroute']}r {c['v']:>5.1f} {c['am']:>7.4f} | "
                      + " ".join(f"{c['g'][i]:>10.3f} {c['tau'][i]*1e3:>+9.0f}" for i in range(5))
                      + f" | {c['g_end']:>9.3f} {c['t_end']*1e3:>+8.0f} | "
                      f"{gp/max(c['g_end'],1e-9):>7.3f} {(ts-c['t_end'])*1e3:>+8.0f} | "
                      + "/".join(f"{c['coh'][k]:.2f}" for k in ("Z", "U", "M", "Y"))
                      + (f"  flr{c['flr']:.2f}" if c["coh"]["Y"] < c["flr"] + 0.1 else ""))
        del S

    # -----------------------------------------------------------------------------------------
    print()
    print("=" * 155)
    print("2.  THE GAP, LEG BY LEG.  d_lag = torque-mode leg lag minus V282's, same band and speed bin.")
    print("    'TQ_J12' = the torque revs that fly the SAME 1.2 Hz jerk filter as V282 (T5/T4/T3/T2):")
    print("    for those the L1 stage differs from V282 ONLY in the flown liveDelay.lateralDelay.")
    print("    Route-cluster bootstrap 95% CI on the leg d_lag where both sides have >=2 routes.")
    print("=" * 155)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'cmp':8s} | " + " ".join(f"{l+' dlag':>22s}" for l in LEGS)
              + f" | {'TOT dlag':>9s} {'sum legs':>9s}")
        for sb in range(4):
            cv = cell(S, S.sel("V282", sb), f1, f2)
            if cv is None or cv["n"] < 6:
                continue
            bv = boot(S, S.sel("V282", sb), f1, f2, lambda c: c["tau"])
            for grp in ("TORQ", "TQ_J12", "T64F"):
                ct = cell(S, S.sel(grp, sb), f1, f2)
                if ct is None or ct["n"] < 6:
                    continue
                bt = boot(S, S.sel(grp, sb), f1, f2, lambda c: c["tau"])
                d = (ct["tau"] - cv["tau"]) * 1e3
                cells = []
                for i in range(5):
                    s = f"{d[i]:+7.0f}"
                    if bt is not None and bv is not None:
                        lo = (bt[0][i] - bv[1][i]) * 1e3; hi = (bt[1][i] - bv[0][i]) * 1e3
                        s += f" [{lo:+5.0f},{hi:+5.0f}]"
                    cells.append(s)
                print(f"{L.SPDN[sb]:6s} {grp:8s} | " + " ".join(f"{s:>22s}" for s in cells)
                      + f" | {(ct['t_end']-cv['t_end'])*1e3:>+9.0f} {d.sum():>+9.0f}")
        del S

    # -----------------------------------------------------------------------------------------
    print()
    print("=" * 155)
    print("3.  THE GAIN GAP, LEG BY LEG (ratio torque/V282 of each leg's gain).  L4 is NOT comparable")
    print("    (different wire semantics); it is printed for completeness and marked.")
    print("=" * 155)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'cmp':8s} | " + " ".join(f"{l+' x':>9s}" for l in LEGS)
              + f" | {'TOT x':>7s} | V282 |H|  TQ |H|")
        for sb in range(4):
            cv = cell(S, S.sel("V282", sb), f1, f2)
            if cv is None or cv["n"] < 6:
                continue
            for grp in ("TORQ", "TQ_J12", "T64F"):
                ct = cell(S, S.sel(grp, sb), f1, f2)
                if ct is None or ct["n"] < 6:
                    continue
                r = ct["g"] / np.maximum(cv["g"], 1e-12)
                print(f"{L.SPDN[sb]:6s} {grp:8s} | " + " ".join(f"{r[i]:>9.3f}" for i in range(5))
                      + f" | {ct['g_end']/max(cv['g_end'],1e-9):>7.3f} | {cv['g_end']:8.3f} {ct['g_end']:8.3f}")
        del S
    return 0


if __name__ == "__main__":
    sys.exit(main())
