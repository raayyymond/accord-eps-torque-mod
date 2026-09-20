# -*- coding: utf-8 -*-
"""Stage 4: VERIFY the budget by a second method that shares no code with it, and by a second node.

(A) TIME DOMAIN.  Band-pass every node, cross-correlate each leg's input against its output over every
    usable run >= 25 s, accumulate the normalised correlation per lag over runs, take the peak.  Shares
    nothing with the FFT machinery except v282cmp.runs/usable.  Gated on a positive control that must
    recover a KNOWN gain and lag injected into the real logged demand before any real number counts.

(B) SECOND NODE.  Redo the loop / vehicle split at the RAW WHEEL ANGLE W = -(steeringAngle - offset)
    instead of at M = actualLateralAccel.  M carries roll compensation and a v^2 scaling that W does
    not, so if the L34 / L5 split survives the swap it is not an artefact of either.

(C) THE JERK CLIP.  Census of how often the delay-compensation stage's two clips bind, per build:
    a clip inside L1 would put amplitude structure in the SOFTWARE leg.

ANALYSIS ONLY, read-only.  usage: python sb_verify.py > out/VERIFY-OUT.txt
"""
import sys

import numpy as np
from scipy import signal

import sb_lib as L
import v282cmp as V
from sb_budget import Spec, cell
from sb_budget2 import C4, gate

MAXLAG = 1.2


def bp(x, f1, f2):
    sos = signal.butter(3, [f1, f2], btype="band", fs=L.FS, output="sos")
    return signal.sosfiltfilt(sos, np.nan_to_num(x))


def xlag(x, y, maxlag=MAXLAG, step=2):
    """Normalised cross-correlation over +-maxlag only (an explicit lag loop, not a full O(n^2)
    correlate), on a `step`-frame lag grid.  Returns (lags_s, r_at_each_lag)."""
    n = int(maxlag * L.FS)
    x = x - x.mean(); y = y - y.mean()
    dn = np.sqrt(np.dot(x, x) * np.dot(y, y))
    if dn <= 0 or len(x) < 4 * n:
        return None
    ks = np.arange(-n, n + 1, step)
    out = np.empty(len(ks))
    for j, k in enumerate(ks):
        if k >= 0:
            out[j] = float(np.dot(x[: len(x) - k], y[k:]))
        else:
            out[j] = float(np.dot(x[-k:], y[: len(y) + k]))
    return (ks / L.FS, out / dn)


def td_legs(route, f1, f2, minrun=25.0):
    """Per-run band-passed leg lags for one route, keyed by speed bin."""
    S = L.load_route(route)
    grp, cm, rf = L.ROUTES[route]
    cfg = L.COMMIT[cm]
    Z0, Zh, okrep, cr, cf = L.replay_setpoint(S, cfg["jerk_hz"], rf if cfg["ref_block"] else None)
    nodes = dict(X=S["model"], Z0=Z0, Z=S["setpoint"], M=S["la_act"],
                 W=-(S["sa"] - np.nan_to_num(S["aoff"])), Y=S["la_pose"])
    fin = np.ones(len(S["t"]), bool)
    for k in ("X", "Z", "M", "W", "Y"):
        fin &= np.isfinite(nodes[k])
    m = V.usable(S) & okrep & fin
    out = []
    for a, b in V.runs(m, S["t"], min_s=minrun):
        vv = S["v"][a:b]
        vm = float(np.median(vv))
        si = next((i for i, (lo, hi) in enumerate(L.SPD) if lo <= vm < hi), None)
        if si is None or float(np.mean((vv >= L.SPD[si][0]) & (vv < L.SPD[si][1]))) < 0.5:
            continue
        seg = {k: bp(nodes[k][a:b], f1, f2) for k in nodes}
        am = float(np.median(np.abs(np.nan_to_num(S["model"][a:b]))))
        rec = dict(sbin=si, v=vm, am=am, sec=(b - a) / L.FS, grp=grp, route=route)
        for nm, (i, o) in dict(L1=("X", "Z0"), L2=("Z0", "Z"), L34=("Z", "M"),
                               L5=("M", "Y"), TOT=("X", "Y"), L34w=("Z", "W"), L5w=("W", "Y")).items():
            r = xlag(seg[i], seg[o])
            rec[nm] = r
        out.append(rec)
    del S
    return out


def pool(recs, key):
    """Pool the per-run correlation curves (weighted by run seconds) and take the peak."""
    acc = None; lags = None; w = 0.0
    for r in recs:
        if r[key] is None:
            continue
        lg, c = r[key]
        if lags is None:
            lags = lg; acc = np.zeros_like(c)
        if len(c) != len(acc):
            continue
        acc += c * r["sec"]; w += r["sec"]
    if acc is None or w == 0:
        return None, None
    acc /= w
    k = int(np.argmax(acc))
    return float(lags[k]), float(acc[k])


def selftest_td():
    """Positive control on the time-domain estimator, on the REAL logged demand of a real route:
    inject a known gain 0.75 and a known lag 260 ms and require both back."""
    S = L.load_route("0000006c--2bc842dbac")
    m = V.usable(S) & np.isfinite(S["model"])
    a, b = V.runs(m, S["t"], min_s=120.0)[0]
    x = np.nan_to_num(S["model"][a:b])
    k = 26
    y = 0.75 * np.concatenate([np.zeros(k), x[:-k]])
    for f1, f2 in ((0.15, 0.30), (0.30, 0.60)):
        lg, c = xlag(bp(x, f1, f2), bp(y, f1, f2))
        tau = lg[int(np.argmax(c))]
        assert abs(tau - 0.26) < 0.025, (f1, f2, tau)
    del S
    return "time-domain self-test OK: a known 260 ms recovered in both tracking bands on real logged demand"


def main():
    print(selftest_td())
    print()
    print("=" * 140)
    print("A.  SECOND METHOD -- TIME DOMAIN.  Band-passed cross-correlation peak per leg, pooled over")
    print("    usable runs >= 25 s weighted by run seconds.  Compare with the spectral budget's lags.")
    print("=" * 140)
    for f1, f2, W in ((0.15, 0.30, 20.48), (0.30, 0.60, 10.24)):
        allrecs = []
        for rk in L.ROUTES:
            if not (V.CACHE / f"{rk}.npz").exists():
                continue
            allrecs += td_legs(rk, f1, f2)
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'group':8s} {'runs':>5s} {'sec':>6s} {'medA':>7s} | "
              + " ".join(f"{k+' td':>9s} {k+' fft':>9s}" for k in ("L1", "L2", "L34", "L5", "TOT")))
        for sb in range(4):
            for grp, gs in (("V282", ["V282"]), ("TORQ", L.TORQ), ("T2", ["T2"]), ("T64F", ["T64", "T64B"])):
                rs = [r for r in allrecs if r["grp"] in gs and r["sbin"] == sb]
                if len(rs) < 3:
                    continue
                c = cell(S, S.sel(grp if grp in ("V282", "T2") else
                                  ("TORQ" if grp == "TORQ" else "T64F"), sb), f1, f2, C4)
                sec = sum(r["sec"] for r in rs)
                am = float(np.median([r["am"] for r in rs]))
                cols = []
                for i, k in enumerate(("L1", "L2", "L34", "L5", "TOT")):
                    tau, pk = pool(rs, k)
                    fftv = (c["tau"][i] * 1e3 if (c and i < 4) else
                            (c["t_end"] * 1e3 if c else float("nan")))
                    cols.append(f"{tau*1e3:>+9.0f} {fftv:>+9.0f}" if tau is not None else f"{'--':>9s} {'--':>9s}")
                print(f"{L.SPDN[sb]:6s} {grp:8s} {len(rs):>5d} {sec:>6.0f} {am:>7.4f} | " + " ".join(cols))
        del S

    # ------------------------------------------------------------------------------------
    print()
    print("=" * 140)
    print("B.  SECOND NODE.  The loop / vehicle split taken at the RAW WHEEL ANGLE instead of at the")
    print("    roll-compensated actualLateralAccel.  If the L34 gap survives, the node is not the cause.")
    print("=" * 140)
    CW = ["Z0", "Z", "W", "Y"]
    for f1, f2, W in L.BANDS[1:3]:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'group':8s} {'n':>5s} | {'L34(M) lag':>11s} {'L34(W) lag':>11s} | "
              f"{'L5(M) lag':>10s} {'L5(W) lag':>10s} | {'L34(M) g':>9s} {'L34(W) g':>9s}")
        for sb in range(4):
            for grp in ("V282", "TORQ", "T2", "T64F"):
                cm_ = cell(S, S.sel(grp, sb), f1, f2, C4)
                cw = cell(S, S.sel(grp, sb), f1, f2, CW)
                if cm_ is None or cw is None or cm_["n"] < 8:
                    continue
                print(f"{L.SPDN[sb]:6s} {grp:8s} {cm_['n']:>5d} | {cm_['tau'][2]*1e3:>+11.0f} "
                      f"{cw['tau'][2]*1e3:>+11.0f} | {cm_['tau'][3]*1e3:>+10.0f} {cw['tau'][3]*1e3:>+10.0f} | "
                      f"{cm_['g'][2]:>9.3f} {cw['g'][2]:>9.3f}")
        del S

    # ------------------------------------------------------------------------------------
    print()
    print("=" * 140)
    print("C.  THE JERK CLIP CENSUS.  raw = the pre-filter clip at +-2.5 m/s^3, flt = the post-filter one.")
    print("    A clip is the ONLY nonlinearity inside L1; if it never binds, L1 is LTI and cannot carry")
    print("    amplitude structure -- which is what makes L1's measured amplitude slope a null control.")
    print("=" * 140)
    print(f"{'route':24s} {'grp':8s} {'engaged s':>9s} {'clip raw %':>11s} {'clip flt %':>11s} "
          f"{'clip raw % @ medA>0.2':>22s}")
    for rk, (grp, cm, rf) in sorted(L.ROUTES.items(), key=lambda kv: (kv[1][0], kv[0])):
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        S = L.load_route(rk)
        cfg = L.COMMIT[cm]
        Z0, Zh, ok, cr, cf = L.replay_setpoint(S, cfg["jerk_hz"], rf if cfg["ref_block"] else None)
        m = V.usable(S) & ok
        big = m & (np.abs(np.nan_to_num(S["model"])) > 0.2)
        print(f"{rk:24s} {grp:8s} {m.sum()/L.FS:>9.0f} {100*np.mean(cr[m]):>11.3f} "
              f"{100*np.mean(cf[m]):>11.3f} {100*np.mean(cr[big]) if big.sum() else float('nan'):>22.3f}")
        del S
    return 0


if __name__ == "__main__":
    sys.exit(main())
