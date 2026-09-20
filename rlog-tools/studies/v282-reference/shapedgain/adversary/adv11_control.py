# -*- coding: utf-8 -*-
"""ADV11: the extrapolation has never been checked against a flown gain change.  Check it.

The closure numbers are produced by ONE recipe: take a base route's measured A and D, scale D by the
sensitivity ratio (1+L)/(1+kL), re-integrate the metric.  Nothing in the programme has ever put that
recipe against a route that actually flew a different gain.

There is exactly one flown gain ladder on ONE EPS build: the three V282-EPS 'V282old' routes at
kp/LAF 0.200, 0.222 and 0.379 against the three V282 routes at 0.150.  The recipe is run forward from
the 0.150 base and compared with what those routes MEASURED.  The confounds are real and are printed
with the result -- but a recipe that cannot survive its only available control is not a measurement.
"""
import sys

import numpy as np

import advlib as A
from adv4_loop import C_of, NPS, SHAKE
from adv7_verdict import pack

BASE = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]     # kp/LAF 0.150
LADDER = {"0000003a--283a39a1d6": 0.2000, "0000003c--927965c2b4": 0.2222, "00000039--f56039af87": 0.3791}


def main():
    fr, sp, vs, rkl, am = pack(BASE, NPS)
    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    E, D = X - Y, Z - M
    sel = A.bandsel(fr)
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    J0 = float(np.sum(np.abs(E[:, sel]) ** 2) / den)
    P = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    Vh = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    Ares = E - Vh[None, :] * D
    metas = {rk: A.FLOWN[rk] for rk in BASE}
    L1 = P[None, :] * np.array([C_of(fr, v, metas[rk]) for v, rk in zip(vs, rkl)])

    def predict(k):
        L2 = P[None, :] * np.array([C_of(fr, v, dict(metas[rk], kp=metas[rk]["kp"] * k))
                                    for v, rk in zip(vs, rkl)])
        Ek = Ares + Vh[None, :] * (D * (1 + L1) / (1 + L2))
        return float(np.sum(np.abs(Ek[:, sel]) ** 2) / den)

    print(f"BASE: three V282 routes at kp/LAF 0.1500, pooled J = {J0:.3f}")
    print(f"\n  {'route':>9s} {'kp/LAF':>7s} {'k vs base':>10s} {'J PREDICTED':>12s} {'J MEASURED':>11s} {'error':>8s}")
    for rk, kpl in LADDER.items():
        k = kpl / 0.1500
        jp = predict(k)
        fr2, sp2, *_ = pack([rk], NPS)
        sel2 = A.bandsel(fr2)
        jm = float(np.sum(np.abs((sp2["X"] - sp2["Y"])[:, sel2]) ** 2) / np.sum(np.abs(sp2["X"][:, sel2]) ** 2))
        print(f"  {rk[:8]:>9s} {kpl:7.4f} {k:10.2f} {jp:12.3f} {jm:11.3f} {jm/jp:7.2f}x")
        del sp2
    print("\n  CONFOUNDS, stated: different roads, different fork commits (the V282old feedforward differs),")
    print("  and n=3 routes a side.  What survives them is the SIGN: the recipe predicts the metric FALLS")
    print("  monotonically with gain, and on the only flown gain ladder that exists it RISES.")
    print("\n  Same test in the direction the programme is proposing (gain UP from the torque base) has")
    print("  no flown ladder at all: the torque-EPS routes span kp/LAF 0.0500-0.0714 only (1.43x).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
