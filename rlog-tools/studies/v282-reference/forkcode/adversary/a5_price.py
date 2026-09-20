# -*- coding: utf-8 -*-
"""a5 -- (1) has the recipe EVER been validated on THIS EPS?  (2) the notch's low-speed price.
        (3) where linear loop shaping stops being trustworthy.

(1) THE ONLY WITHIN-EPS CONTROL AVAILABLE.  r70 flew SteerKP 0.30 / SteerLatAccel 6.0 (kp/LAF 0.0500)
    and T64 flew 1.00 / 14.0 (0.0714) on the SAME V293 EPS.  Run the frontier's own recipe forward
    from r70's windows to T64's controller and compare the PREDICTED metric with T64's MEASURED one.
    Also r72/r73 (0.85/14, no notch, Ki 0.6) -> T64.  Confounded by road, so a pass is weak evidence
    and a large miss is strong evidence.

(2) THE NOTCH AT LOW SPEED.  Its centre is get_honda_accord_mode_hz(v) = sqrt(interp(v,HOLD_V_BP,
    HOLD_K_V)/8e-5)/2pi, which falls to 0.82 Hz at 2 m/s.  AccordErrorNotchQ is a SCALAR: the same Q
    is used at every speed.  Q 0.6 is a wide notch; at 2 m/s it sits on top of the band that carries
    low-speed steering.  The metric never scores below 15 m/s.

(3) COHERENCE / NONLINEARITY.  Coulomb friction + a demand-amplitude-dependent plant.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

OUT = HERE / "out"
R70, R72, R73 = "00000070--717f5a7866", "00000072--8001fc3048", "00000073--79fd149dd8"


def predict(Wsrc, src, dst):
    """Run the frontier recipe from a route's OWN flown controller to another's."""
    f, v = Wsrc["f"], Wsrc["v"]
    C0 = A.C_fb(f, v, **src)
    C1 = A.C_fb(f, v, **dst)
    P = A.identify(Wsrc, inst="X")["P"]
    K = C1 / C0
    L0 = P[None, :] * C0
    rho = (1.0 + L0) / (1.0 + L0 * K)
    Vh = np.mean(np.conj(Wsrc["M"]) * Wsrc["Y"], axis=0) / np.maximum(np.mean(np.abs(Wsrc["M"]) ** 2, axis=0), 1e-300)
    E1 = (Wsrc["X"] - Wsrc["Y"]) + Vh[None, :] * (Wsrc["Z"] - Wsrc["M"]) * (rho - 1.0)
    b = (f >= A.BAND[0]) & (f <= A.BAND[1])
    return float(np.sum(np.abs(E1[:, b]) ** 2) / np.sum(np.abs(Wsrc["X"][:, b]) ** 2))


def main():
    print("=" * 112)
    print("1. HAS THE RECIPE EVER BEEN VALIDATED ON THIS EPS?  Forward prediction between flown")
    print("   configs on the SAME V293 EPS.  'dose' = kp/LAF ratio applied.")
    T64cfg = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)
    srcs = [(R70, dict(kp=0.30, laf=6.0, ki=0.15, q=None), "r70  KP0.30 LAF6  no notch"),
            (R72, dict(kp=0.85, laf=14.0, ki=0.60, q=None), "r72  KP0.85 LAF14 no notch"),
            (R73, dict(kp=0.85, laf=14.0, ki=0.60, q=None), "r73  KP0.85 LAF14 no notch")]
    Wt = A.cat([A.extract(r, nps=1024) for r in A.T64])
    J_T64 = A.metric(Wt)
    print(f"   T64 MEASURED metric = {J_T64:.4f}  (n={len(Wt['v'])} windows)")
    print()
    print(f"{'source route':30s} {'n':>4s} {'J src meas':>11s} {'dose kp/LAF':>12s} "
          f"{'J pred at T64 cfg':>18s} {'vs T64 measured':>16s}")
    rows = []
    for r, cfg, lbl in srcs:
        W = A.extract(r, nps=1024)
        if len(W["v"]) < 6:
            print(f"{lbl:30s} {len(W['v']):4d}   too few windows")
            continue
        Js = A.metric(W)
        Jp = predict(W, cfg, T64cfg)
        dose = (T64cfg["kp"] / T64cfg["laf"]) / (cfg["kp"] / cfg["laf"])
        print(f"{lbl:30s} {len(W['v']):4d} {Js:11.4f} {dose:12.3f} {Jp:18.4f} {Jp/J_T64:16.2f}x")
        rows.append(dict(src=r, label=lbl, n=len(W["v"]), J_src=Js, dose=dose, J_pred=Jp, ratio=Jp / J_T64))
        del W
    print()
    print("   REVERSE: predict each source's own metric FROM T64 (dose < 1, the direction the recipe")
    print("   is actually used in reverse), and compare with that route's measured metric.")
    print(f"{'target':30s} {'J measured':>11s} {'J predicted from T64':>21s} {'ratio':>8s}")
    for r, cfg, lbl in srcs:
        W = A.extract(r, nps=1024)
        if len(W["v"]) < 6:
            continue
        Js = A.metric(W)
        Jp = predict(Wt, T64cfg, cfg)
        print(f"{lbl:30s} {Js:11.4f} {Jp:21.4f} {Jp/Js:8.2f}x")
        del W

    print()
    print("=" * 112)
    print("2. THE NOTCH AT LOW SPEED.  AccordErrorNotchQ is ONE scalar for every speed; the centre")
    print("   is scheduled, the width is not.  Gain and phase the P/I error actually sees.")
    fq = np.array([0.15, 0.20, 0.30, 0.40, 0.60, 0.80, 1.00, 1.50, 2.00, 3.00])
    print(f"{'v m/s':>6s} {'f0 Hz':>7s} {'Q':>5s} | " + " ".join(f"{x:>11.2f}" for x in fq))
    for v in (2.0, 4.0, 6.0, 8.0, 12.0, 17.0, 22.0, 28.0):
        f0 = A.mode_hz(np.array([v]))
        for q in (1.0, 0.6):
            H = A.notch_H(fq, f0, q)[0]
            print(f"{v:6.1f} {float(f0[0]):7.3f} {q:5.2f} | " +
                  " ".join(f"{abs(h):5.3f}/{np.degrees(np.angle(h)):+5.0f}" for h in H))
    print()
    print("   EXTRA lag and EXTRA attenuation that Q 0.6 costs vs the flown Q 1.0:")
    print(f"{'v m/s':>6s} {'f0':>6s} | " + " ".join(f"{x:>13.2f}" for x in (0.2, 0.3, 0.5, 0.8)))
    for v in (2.0, 4.0, 6.0, 8.0, 12.0, 17.0, 22.0, 28.0):
        f0 = A.mode_hz(np.array([v]))
        a = A.notch_H(np.array([0.2, 0.3, 0.5, 0.8]), f0, 1.0)[0]
        b = A.notch_H(np.array([0.2, 0.3, 0.5, 0.8]), f0, 0.6)[0]
        print(f"{v:6.1f} {float(f0[0]):6.3f} | " + " ".join(
            f"{abs(bb)/abs(aa):5.3f}x /{np.degrees(np.angle(bb))-np.degrees(np.angle(aa)):+5.1f}d"
            for aa, bb in zip(a, b)))

    print()
    print("   EXPOSURE -- how much of the drive the metric never scores:")
    for r in A.T64:
        S = A.V.load(r)
        act = S["active"] & ~S["pressed"]
        n = act.sum()
        for lo, hi in ((0, 8), (8, 15), (15, 22), (22, 99)):
            m = act & (S["v"] >= lo) & (S["v"] < hi)
            print(f"      {r[:12]}  {lo:2d}-{hi:2d} m/s  {m.sum()/max(n,1)*100:5.1f} % of engaged hands-off time "
                  f"({m.sum()/100.0:6.0f} s)")
        del S

    print()
    print("   THE LOW-SPEED P AND I THAT SteerKP 1->3 ACTUALLY DELIVERS  (error_with_lsf = e*(1+lsf/kp),")
    print("   so P gain = kp+lsf and I gain scales as (1+lsf/kp)):")
    print(f"{'v':>5s} {'lsf':>7s} {'P x':>7s} {'I x':>7s} {'notch f0':>9s}")
    for v in (2.0, 4.0, 6.0, 8.0, 12.0, 15.0, 20.0, 28.0):
        l = float(A.lsf_of(np.array([v]))[0])
        print(f"{v:5.1f} {l:7.3f} {(3.0+l)/(1.0+l):7.3f} {(1+l/3.0)/(1+l/1.0):7.3f} "
              f"{float(A.mode_hz(np.array([v]))[0]):9.3f}")

    print()
    print("=" * 112)
    print("3. WHERE LINEAR LOOP SHAPING STOPS BEING TRUSTWORTHY.")
    f = Wt["f"]
    ident = A.identify(Wt, inst="X")
    Eb = A.bands_of(Wt)
    Jt = A.metric(Wt)
    print(f"{'band':>12s} {'share of J':>11s} {'coh(X,U)':>9s} {'coh(X,M)':>9s} {'coh(M,Y)':>9s} "
          f"{'incoherent M':>13s} {'verdict':>28s}")
    for (lo, hi), share in zip(A.SUB, Eb):
        s = (f >= lo) & (f < hi)
        cxm = float(np.mean(ident["coh_im"][s]))
        v = ("linear model OK" if cxm > 0.6 else
             "MOSTLY UNEXPLAINED" if cxm < 0.3 else "marginal")
        print(f"{f'{lo:.2f}-{hi:.2f}':>12s} {share/Jt*100:10.1f}% {float(np.mean(ident['coh_iu'][s])):9.2f} "
              f"{cxm:9.2f} {float(np.mean(ident['coh_my'][s])):9.2f} {(1-cxm)*100:12.0f}% {v:>28s}")
    print()
    print("   Coulomb friction, in the units of the command (torque frame), measured against the")
    print("   command's own size in each band -- the smaller the signal, the more the friction rules.")
    for r in A.T64:
        S = A.V.load(r)
        m = S["active"] & ~S["pressed"] & (S["v"] >= 15)
        u = S["out"][m]
        print(f"      {r[:12]}  |cmd| median {np.median(np.abs(u)):.4f}  p90 {np.quantile(np.abs(u),0.9):.4f}"
              f"   Coulomb F (measured 0.011-0.030) = {0.011/np.median(np.abs(u))*100:.0f}-"
              f"{0.030/np.median(np.abs(u))*100:.0f} % of the median command")
        del S
    json.dump(rows, open(OUT / "a5_price.json", "w"), indent=1)


if __name__ == "__main__":
    main()
