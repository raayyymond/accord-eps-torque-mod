# -*- coding: utf-8 -*-
"""D8 -- robustness of the dose numbers, and how the dose self-tapers with speed.

(a) SPLIT-HALF: identify the plant on the odd and the even runs of each route separately and
    re-derive |S| at the flown gain and at SteerKP x2.  If the two halves disagree, the dose is not
    sized.
(b) SPEED TAPER: SteerKP enters the loop as (kp + low_speed_factor(v)).  The low-speed factor is
    large below 15 m/s, so the SAME toggle change is a much smaller gain change there.  This is an
    exact property of the fork's own arithmetic, not a model.
(c) The 8-15 m/s band: the flown |S| and the x2 dose, on the routes that have runs there.
"""
import json
import numpy as np
import dlib as D
from d1_ident import k_tot, segs_for

FMAX, COH, NPS = 1.2, 0.50, 1024


def ident(S, vlo, vhi, pick=None):
    sg, m = segs_for(S, vlo, vhi)
    if pick is not None:
        sg = sg[pick::2]
    if not sg:
        return None
    R = D.iv_transfer(sg, nperseg=NPS)
    if R is None:
        return None
    P = D.smooth_c(R["P"].real) + 1j * D.smooth_c(R["P"].imag)
    valid = (D.smooth_c(R["coh_ry"]) > COH) & (D.smooth_c(R["coh_ru"]) > 0.30)
    return R["f"], P, valid, float(np.median(S["v"][m])), D.k_m_measured(S, m), R["sec"], len(sg)


def main():
    print("(a) SPLIT-HALF on the rev 5 / rev 6.4 routes, >=15 m/s\n")
    print(f"{'route':22s} {'half':>5s} {'runs':>5s} {'sec':>5s} | "
          f"{'S.15-.3':>8s} {'S.3-.6':>7s} {'S.6-1.2':>8s} | at SteerKP x2: "
          f"{'S.15-.3':>8s} {'S.3-.6':>7s} {'S.6-1.2':>8s}")
    for rt in [k for k, v in D.ROUTES.items() if v["g"] in ("T5", "T64", "T64B", "V282")]:
        S = D.load(rt)
        for lab, pick in (("all", None), ("odd", 0), ("even", 1)):
            r = ident(S, 15.0, 99.0, pick)
            if r is None:
                continue
            f, P, valid, v, km, sec, n = r
            m1 = D.loop_metrics(f, k_tot(f, D.ROUTES[rt], v, km) * P, valid, fmax=FMAX)
            m2 = D.loop_metrics(f, k_tot(f, D.ROUTES[rt], v, km, kp_mult=2.0) * P, valid, fmax=FMAX)
            if not m1 or not m2:
                continue
            print(f"{rt if lab=='all' else '':22s} {lab:>5s} {n:5d} {sec:5.0f} | "
                  + " ".join(f"{m1[k]:8.3f}" for k in ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2"))
                  + " |                " + " ".join(f"{m2[k]:8.3f}" for k in
                                                    ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2")))
        del S

    print("\n(b) SPEED TAPER of the SteerKP toggle -- exact fork arithmetic")
    print("    P gain into the loop = kp + low_speed_factor(v);  low_speed_factor = "
          "(interp(v,[0,10,20,30],[12,10.5,8,5]) / max(v,0.3))^2")
    print(f"{'v m/s':>6s} {'lsf':>7s} {'kp_eff @1.0':>12s} {'@2.0':>7s} {'@2.5':>7s} "
          f"{'x at 2.0':>9s} {'x at 2.5':>9s}")
    for v in (4, 6, 8, 10, 12, 15, 18, 20, 25, 30):
        lsf = D.low_speed_factor(float(v))
        a, b, c = 1.0 + lsf, 2.0 + lsf, 2.5 + lsf
        print(f"{v:6.0f} {lsf:7.3f} {a:12.3f} {b:7.3f} {c:7.3f} {b/a:9.3f} {c/a:9.3f}")

    print("\n(c) 8-15 m/s band: flown |S| and the x2 dose (routes with >=1 usable run)")
    print(f"{'route':22s} {'grp':8s} {'runs':>5s} {'sec':>5s} {'v':>5s} | "
          f"{'S.15-.3':>8s} {'S.3-.6':>7s} {'S.6-1.2':>8s} | x2: {'S.15-.3':>8s} {'S.3-.6':>7s} "
          f"{'S.6-1.2':>8s}")
    for rt, cfg in D.ROUTES.items():
        S = D.load(rt)
        r = ident(S, 8.0, 15.0)
        del S
        if r is None:
            continue
        f, P, valid, v, km, sec, n = r
        m1 = D.loop_metrics(f, k_tot(f, cfg, v, km) * P, valid, fmax=FMAX)
        m2 = D.loop_metrics(f, k_tot(f, cfg, v, km, kp_mult=2.0) * P, valid, fmax=FMAX)
        if not m1 or not m2:
            print(f"{rt:22s} {cfg['g']:8s} {n:5d} {sec:5.0f} {v:5.1f} |  (no valid band)")
            continue
        print(f"{rt:22s} {cfg['g']:8s} {n:5d} {sec:5.0f} {v:5.1f} | "
              + " ".join(f"{m1[k]:8.3f}" for k in ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2"))
              + " |     " + " ".join(f"{m2[k]:8.3f}" for k in
                                     ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2")))


if __name__ == "__main__":
    main()
