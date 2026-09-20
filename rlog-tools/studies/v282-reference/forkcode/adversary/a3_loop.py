# -*- coding: utf-8 -*-
"""a3 -- the loop the closure was computed on is NOT the loop the car runs, and the anchors.

(1) CORRECT THE LOOP.  The frontier sets L0 = P * C_pid and L1 = L0 * K.  Measured, the whole
    measurement -> command path is |Ky| = 1.4-2.7x |C_pid| (a2).  The extra path (100 Hz rate loop
    on steeringRateDeg + the disturbance observer) is FIXED when SteerKP moves.  The right algebra
    is therefore
        L0_true = L_tot                      L1_true = L_tot + L_pid * (K - 1)
    not L1 = L_tot * K (what f7's 'Lbase=tot' robustness row did) and not L1 = L_pid * K.
    Re-run the closure and the cost on all three.

(2) THE ANCHORS.  Re-measure, my own way, the two flown V293 routes the safety case rests on:
    r71 (2.34 Hz limit cycle, kp 0.85 LAF 14, no notch) and r72 (flew clean, same kp/LAF, no notch).

(3) WHERE THE CASE AGAINST SteerKP > 3 BECOMES DECISIVE.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

OUT = HERE / "out"
FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)
R71, R72, R73, R70 = ("00000071--f2c9d073a3", "00000072--8001fc3048",
                      "00000073--79fd149dd8", "00000070--717f5a7866")


def Ky_of(W, sel=None):
    """Complex WHOLE measurement->command feedback, exogenous instrument X projected out."""
    s = np.ones(len(W["v"]), bool) if sel is None else sel
    X, U, M = W["X"][s], W["U"][s], W["M"][s]
    px = np.maximum(np.mean(np.abs(X) ** 2, axis=0), 1e-300)
    Up = U - (np.mean(np.conj(X) * U, axis=0) / px)[None, :] * X
    Mp = M - (np.mean(np.conj(X) * M, axis=0) / px)[None, :] * X
    pm = np.maximum(np.mean(np.abs(Mp) ** 2, axis=0), 1e-300)
    Ky = np.mean(np.conj(Mp) * Up, axis=0) / pm
    c = (np.abs(np.mean(np.conj(Mp) * Up, axis=0)) ** 2
         / np.maximum(pm * np.mean(np.abs(Up) ** 2, axis=0), 1e-300))
    return Ky, c


def run(W, P, kp, laf, ki, q, mode, Ky=None, ref=0.4705, flown_J=None):
    f, v = W["f"], W["v"]
    C0 = A.C_fb(f, v, **FLOWN)
    C1 = A.C_fb(f, v, kp, laf, ki, q)
    K = C1 / C0
    Lpid = P[None, :] * C0
    if mode == "pid":
        L0, L1 = Lpid, Lpid * K
    elif mode == "tot_scaled":
        Lt = -P[None, :] * Ky[None, :]
        L0, L1 = Lt, Lt * K
    elif mode == "tot_correct":
        Lt = -P[None, :] * Ky[None, :]
        L0, L1 = Lt, Lt + Lpid * (K - 1.0)
    rho = (1.0 + L0) / (1.0 + L1)
    ident_V = np.mean(np.conj(W["M"]) * W["Y"], axis=0) / np.maximum(np.mean(np.abs(W["M"]) ** 2, axis=0), 1e-300)
    E1 = (W["X"] - W["Y"]) + ident_V[None, :] * (W["Z"] - W["M"]) * (rho - 1.0)
    b = (f >= A.BAND[0]) & (f <= A.BAND[1])
    px = float(np.sum(np.abs(W["X"][:, b]) ** 2))
    J = float(np.sum(np.abs(E1[:, b]) ** 2)) / px
    U1 = W["UFF"] + W["UFB"] * K * rho
    shk = (f >= A.SHAKE[0]) & (f <= A.SHAKE[1])
    cmd = float(np.sqrt(np.sum(np.abs(U1[:, shk]) ** 2) / np.sum(np.abs(W["U"][:, shk]) ** 2)))
    Jf = flown_J if flown_J is not None else A.metric(W)
    return dict(J=J, closure=(Jf - J) / (Jf - ref), cmd=cmd,
                Lshk=float(np.mean(np.abs(L1[:, shk]))), L0shk=float(np.mean(np.abs(L0[:, shk]))),
                Ms=float(np.max(np.abs(1.0 / (1.0 + np.mean(L1, axis=0)))[(f >= 0.1) & (f <= 2.5)])))


def main():
    Wt = A.cat([A.extract(r, nps=1024) for r in A.T64])
    f = Wt["f"]
    shk = (f >= A.SHAKE[0]) & (f <= A.SHAKE[1])
    Pm = A.identify(Wt, inst="X")["P"]
    Ky, cKy = Ky_of(Wt)
    Jf = A.metric(Wt)
    Wv = A.cat([A.extract(r, nps=1024) for r in A.V282])
    Jv = A.metric(Wv)
    del Wv
    print("=" * 112)
    print(f"reference: J_flown {Jf:.4f}, J_V282 {Jv:.4f} (my own, nps 1024)")
    print()
    print("1. THE SAME DOSES ON THREE LOOP MODELS")
    print("   pid         = the frontier's:  L0 = P*C_pid,            L1 = L0*K     (misses 1.4-2.7x of the loop)")
    print("   tot_scaled  = f7's robustness row: L0 = L_tot,          L1 = L_tot*K  (scales feedback SteerKP cannot move)")
    print("   tot_correct = measured total loop, PID part scaled only: L1 = L_tot + L_pid*(K-1)")
    print()
    print(f"{'config':24s} | " + " | ".join(f"{m:^28s}" for m in ("pid", "tot_scaled", "tot_correct")))
    print(f"{'':24s} | " + " | ".join(f"{'J':>7s}{'clos%':>7s}{'|L|shk':>7s}{'Ms':>7s}" for _ in range(3)))
    rows = {}
    for lbl, kp, q in (("as flown KP1.0 Q1.0", 1.0, 1.0), ("ARM-KP   KP2.0 Q1.0", 2.0, 1.0),
                       ("KP3.0 Q1.0", 3.0, 1.0), ("ARM-KP2  KP3.0 Q0.6", 3.0, 0.6),
                       ("KP4.0 Q0.6", 4.0, 0.6), ("KP5.0 Q0.6", 5.0, 0.6),
                       ("KP6.0 Q0.6", 6.0, 0.6), ("KP8.0 Q0.6", 8.0, 0.6),
                       ("KP12.0 Q0.6", 12.0, 0.6), ("KP 1e4 (asymptote)", 1e4, 0.6)):
        cells, rr = [], {}
        for mode in ("pid", "tot_scaled", "tot_correct"):
            r = run(Wt, Pm, kp, 14.0, 0.30, q, mode, Ky=Ky, ref=Jv, flown_J=Jf)
            cells.append(f"{r['J']:7.3f}{r['closure']*100:7.1f}{r['Lshk']:7.3f}{r['Ms']:7.2f}")
            rr[mode] = r
        rows[lbl] = rr
        print(f"{lbl:24s} | " + " | ".join(cells))
    print()
    print(f"   measured |Ky|/|C_pid| by band: " + "  ".join(
        f"{n} {float(np.mean(np.abs(Ky[(f>=lo)&(f<=hi)])))/float(np.mean(np.abs(A.C_fb(f,Wt['v'],**FLOWN)),axis=0)[(f>=lo)&(f<=hi)].mean()):.2f}"
        for n, lo, hi in (("0.15-0.6", .15, .6), ("0.6-1.2", .6, 1.2), ("1.8-3.5", 1.8, 3.5))))
    print(f"   coherence of that regression:  " + "  ".join(
        f"{n} {float(np.mean(cKy[(f>=lo)&(f<=hi)])):.2f}"
        for n, lo, hi in (("0.15-0.6", .15, .6), ("0.6-1.2", .6, 1.2), ("1.8-3.5", 1.8, 3.5))))

    print()
    print("=" * 112)
    print("2. THE FLOWN ANCHORS, RE-MEASURED.  r71 limit-cycled at 2.34 Hz; r72 flew clean; identical")
    print("   SteerKP 0.85 / SteerLatAccel 14 / no notch.  T64 = rev 6.4 (SteerKP 1.0, notch Q 1.0).")
    print()
    print(f"{'route':22s} {'grp':6s} {'n':>4s} {'kp/LAF':>7s} {'SRrms 1.8-3.5':>14s} {'|L|shk':>7s} "
          f"{'|L|shk hi|X|':>13s} {'|P|shk':>8s} {'peak line':>10s}")
    anch = {}
    for route, grp, kp, laf, q in ((R71, "r71 LC", 0.85, 14.0, None), (R72, "r72 ok", 0.85, 14.0, None),
                                   (R73, "r73", 0.85, 14.0, None), (R70, "r70", 0.30, 6.0, None),
                                   (A.T64[0], "T64 6c", 1.0, 14.0, 1.0), (A.T64[1], "T64 6d", 1.0, 14.0, 1.0)):
        W = A.extract(route, nps=1024)
        if len(W["v"]) < 4:
            print(f"{route:22s} {grp:6s} {len(W['v']):4d}   -- too few windows at >=15 m/s")
            continue
        idn = A.identify(W, inst="X")
        C = A.C_fb(W["f"], W["v"], kp, laf, 0.30, q)
        L = idn["P"][None, :] * C
        hi = W["amp"] > np.quantile(W["amp"], 2 / 3)
        idh = A.identify(W, inst="X", vsel=hi)
        Lh = idh["P"][None, :] * C[hi]
        srr = float(np.sqrt(np.mean(np.sum(np.abs(W["SR"][:, shk]) ** 2, axis=1))))
        # narrow-line statistic: peak bin power in 1.8-3.5 Hz over the band median
        pw = np.mean(np.abs(W["SR"][:, shk]) ** 2, axis=0)
        line = float(pw.max() / np.median(pw))
        print(f"{route:22s} {grp:6s} {len(W['v']):4d} {kp/laf:7.4f} {srr:14.1f} "
              f"{float(np.mean(np.abs(L[:, shk]))):7.3f} {float(np.mean(np.abs(Lh[:, shk]))):13.3f} "
              f"{float(np.mean(np.abs(idn['P'][shk]))):8.3f} {line:10.1f}")
        anch[route] = dict(grp=grp, n=len(W["v"]), srrms=srr, Lshk=float(np.mean(np.abs(L[:, shk]))),
                           Lshk_hi=float(np.mean(np.abs(Lh[:, shk]))), line=line)
        del W

    print()
    print("=" * 112)
    print("3. WHERE THE CASE AGAINST SteerKP > 3.0 BECOMES DECISIVE.")
    print("   Pooled AND high-demand |L| in 1.8-3.5 Hz on the tot_correct loop, against r71's own")
    print("   re-measured value.  kp/LAF flown on THIS EPS: 0.0500 (r70) .. 0.0714 (T64).")
    q23 = np.quantile(Wt["amp"], 2 / 3)
    hiw = Wt["amp"] > q23
    Wh = {k: (v[hiw] if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(Wt["v"]) else v)
          for k, v in Wt.items()}
    Wh["f"] = f
    Ph = A.identify(Wt, inst="X", vsel=hiw)["P"]
    Kyh, _ = Ky_of(Wt, sel=hiw)
    r71L = anch.get(R71, {}).get("Lshk_hi", np.nan)
    print()
    print(f"{'SteerKP':>8s} {'Q':>5s} {'kp/LAF':>7s} {'x flown max':>11s} {'clos%':>7s} {'|L|shk pool':>12s} "
          f"{'|L|shk hi|X|':>13s} {'% of r71 hi':>12s} {'Ms hi':>7s} {'cmd shake':>10s}")
    tab = []
    for kp in (1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0):
        q = 0.6 if kp > 1.0 else 1.0
        rp = run(Wt, Pm, kp, 14.0, 0.30, q, "tot_correct", Ky=Ky, ref=Jv, flown_J=Jf)
        rh = run(Wh, Ph, kp, 14.0, 0.30, q, "tot_correct", Ky=Kyh, ref=Jv, flown_J=Jf)
        print(f"{kp:8.1f} {q:5.2f} {kp/14:7.4f} {kp/14/0.0714:11.2f} {rp['closure']*100:7.1f} "
              f"{rp['Lshk']:12.3f} {rh['Lshk']:13.3f} {rh['Lshk']/r71L*100:12.0f} {rh['Ms']:7.2f} {rp['cmd']:10.3f}")
        tab.append(dict(kp=kp, q=q, closure=rp["closure"], Lpool=rp["Lshk"], Lhi=rh["Lshk"],
                        pct_r71=rh["Lshk"] / r71L, Ms_hi=rh["Ms"], cmd=rp["cmd"]))
    json.dump(dict(anchors=anch, ladder=tab, r71_hi=r71L), open(OUT / "a3_loop.json", "w"), indent=1)


if __name__ == "__main__":
    main()
