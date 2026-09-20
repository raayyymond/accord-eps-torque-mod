# -*- coding: utf-8 -*-
"""ADV9: if the shake band is the binding constraint, price the levers AGAINST THAT CONSTRAINT.

The gap lives at 0.15-0.60 Hz; the constraint lives at 1.8-3.5 Hz.  SteerKP raises both.  The integral
path cannot reach the shake band at all (|1/jw| is 12-19x smaller there than at 0.2 Hz), so it is the
one shaped lever the fork already exposes.  Bounds read from source:
   SteerKP            max steerKp*STEER_KP_MAX_MULT = 0.6*5.0 = 3.00   (starpilot_variables.py:459/811)
   AccordTorqueKiHigh min 0.0 max 6.0, currently 0 on rev 6.4          (starpilot_variables.py:838)
Everything is priced on the SAME identity as the gain sweep, and on the HIGH-amplitude plant as well as
the pooled one, because ADV8 showed those differ by 1.87x in the shake band.
"""
import json
import sys

import numpy as np

import advlib as A
from adv4_loop import C_of, NPS, SHAKE
from adv7_verdict import T64, V282, pack, asym


def main():
    fr, sp, vs, rkl, am = pack(T64, NPS)
    frV, spV, *_ = pack(V282, NPS)
    JV, _ = asym(frV, spV)
    del spV
    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    E, D = X - Y, Z - M
    sel = A.bandsel(fr)
    ssh = (fr >= SHAKE[0]) & (fr < SHAKE[1])
    slo = (fr >= 0.15) & (fr < 0.60)
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    J0 = float(np.sum(np.abs(E[:, sel]) ** 2) / den)
    Vh = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    Ares = E - Vh[None, :] * D
    metas = {rk: A.FLOWN[rk] for rk in T64}
    wl = np.abs(X) ** 2
    q2 = np.percentile(am, 66.7)
    hi = am > q2
    P_pool = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    P_hi = np.sum(np.conj(X[hi]) * M[hi], 0) / np.sum(np.conj(X[hi]) * U[hi], 0)

    def cfg(kpm, kihi):
        return [dict(metas[rk], kp=metas[rk]["kp"] * kpm, ki_hi=kihi) for rk in rkl]

    def evaluate(kpm, kihi):
        Cw = np.array([C_of(fr, v, c) for v, c in zip(vs, cfg(kpm, kihi))])
        L = P_pool[None, :] * Cw
        L1 = P_pool[None, :] * np.array([C_of(fr, v, metas[rk]) for v, rk in zip(vs, rkl)])
        Ek = Ares + Vh[None, :] * (D * (1 + L1) / (1 + L))
        J = float(np.sum(np.abs(Ek[:, sel]) ** 2) / den)
        Lh = P_hi[None, :] * Cw[hi]
        return dict(J=J, clos=100 * (J0 - J) / (J0 - JV),
                    Llo=float(np.average(np.abs(L[:, slo]), weights=wl[:, slo])),
                    Lsh=float(np.average(np.abs(L[:, ssh]), weights=wl[:, ssh])),
                    Lsh_hi=float(np.average(np.abs(Lh[:, ssh]), weights=wl[hi][:, ssh])),
                    Ms=float(np.max(np.abs(1 / (1 + L))[:, sel])),
                    Ms_hi=float(np.max(np.abs(1 / (1 + Lh))[:, sel])),
                    Mslo=float(np.max(np.abs(1 / (1 + L))[:, slo])))

    print("PRICED AGAINST THE BINDING CONSTRAINT.  Anchors: r71 limit-cycled at shake-band |L| 0.46;")
    print("Ms > 2 is the classical robustness boundary; today's build runs Ms 1.27 / 1.33 (pooled / high-|X|).")
    print(f"\n  {'SteerKP':>8s} {'KiHigh':>7s} {'J':>6s} {'clos %':>7s} {'|L| .15-.6':>11s} "
          f"{'|L| shake':>10s} {'|L| shk hi|X|':>13s} {'% of r71':>9s} {'Ms':>6s} {'Ms hi|X|':>9s}")
    out = []
    for kpm, kihi in [(1.0, 0.0), (1.0, 0.6), (1.0, 1.0), (1.0, 1.5), (1.0, 2.5), (1.0, 4.0), (1.0, 6.0),
                      (1.5, 0.0), (1.5, 2.5), (1.5, 6.0),
                      (2.0, 0.0), (2.0, 1.5), (2.0, 2.5), (2.0, 6.0),
                      (2.5, 0.0), (2.5, 2.5), (3.0, 0.0), (3.0, 2.5), (3.0, 6.0)]:
        r = evaluate(kpm, kihi); r.update(kp=kpm, kihi=kihi); out.append(r)
        print(f"  {kpm:8.1f} {kihi:7.1f} {r['J']:6.3f} {r['clos']:7.1f} {r['Llo']:11.3f} {r['Lsh']:10.3f} "
              f"{r['Lsh_hi']:13.3f} {100*r['Lsh_hi']/0.46:8.0f}% {r['Ms']:6.2f} {r['Ms_hi']:9.2f}")
    json.dump(dict(J0=J0, JV=JV, rows=out), open(A.OUT / "adv9_shaped.json", "w"), indent=1)

    print("\nTHE FRONTIER UNDER THE CONSTRAINT 'shake-band |L| on high-demand windows <= 0.46 (r71) and Ms_hi <= 2.0':")
    ok = [r for r in out if r["Lsh_hi"] <= 0.46 and r["Ms_hi"] <= 2.0]
    ok.sort(key=lambda r: -r["clos"])
    for r in ok[:6]:
        print(f"    SteerKP {r['kp']:.1f} + KiHigh {r['kihi']:.1f}: closure {r['clos']:5.1f} % "
              f"(|L|shake hi|X| {r['Lsh_hi']:.3f}, Ms_hi {r['Ms_hi']:.2f})")
    print("\nWHY THE INTEGRAL PATH DOES NOT REACH THE SHAKE BAND (pure algebra, |1/(j2pi f)|):")
    for f in (0.2, 0.4, 0.6, 2.0, 2.6, 3.5):
        print(f"    {f:4.2f} Hz: integral weight {1/(2*np.pi*f):.4f}  "
              f"({(1/(2*np.pi*0.2))/(1/(2*np.pi*f)):.1f}x smaller than at 0.20 Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
