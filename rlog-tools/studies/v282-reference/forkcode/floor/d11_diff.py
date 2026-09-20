# -*- coding: utf-8 -*-
"""d11 -- the EXACT setpoint chain, a positive control on it, and the minimal fork diff priced.

THE CHAIN, written out from the source at the flown commit 84766cdc (latcontrol_torque.py:303-329):
    expected   = X(t - D)                                        D = lat_delay, flown 0.299 s (T64)
    raw_jerk   = (X(t) - X(t-D)) / D
    jerk       = Fj(raw_jerk)                                    Fj = FirstOrderFilter, rc = 1/(2 pi * 4.0)
    setpoint   = expected + jerk * D
    Z          = RF(RF(setpoint))                                RF = FirstOrderFilter, rc = 0.06 (flown)
  =>  Z/X = [ e^{-jwD} + Fj(w) (1 - e^{-jwD}) ] * RF(w)^2
  With Fj == 1 the bracket is IDENTICALLY 1 at every frequency: the delay canceller provides NO LEAD.
  All of the chain's net lag is (a) the jerk filter reverting the bracket toward e^{-jwD} above 4 Hz
  and (b) the two reference-filter poles, 2*RC = 119 ms.

POSITIVE CONTROL: this written-out transfer must reproduce the MEASURED Z/X (gain and group delay).

THE MINIMAL DIFF.  One term, one constant, using machinery already in the function:
    setpoint = expected_lateral_accel + desired_lateral_jerk * (lat_delay + HONDA_ACCORD_SETPOINT_LEAD)
  =>  Z/X = [ e^{-jwD} + Fj(w) (1 - e^{-jwD}) (D+L)/D ] * RF(w)^2
It is a first-order forward extrapolation on the jerk the function already computes and filters.
Priced below at unity DC magnitude, with its shake-band command cost.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "shapedgain" / "frontier"))
from d8_refladder import Ref, T64, V282R, JREF, JFLOWN  # noqa: E402
from f5_frontier import Engine, C_of, FLOWN             # noqa: E402

DT = 0.01
D_T64, D_V282 = 0.299, 0.200
RC_JERK = 1.0 / (2.0 * np.pi * 4.0)
RC_REF = 0.06


def fo(f, rc, dt=DT):
    """EXACT discrete FirstOrderFilter: x = (1-a) x + a u, a = dt/(rc+dt)."""
    a = dt / (rc + dt)
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return a / (1.0 - (1.0 - a) * z)


def chain(f, D, lead=0.0, rc_ref=RC_REF):
    e = np.exp(-2j * np.pi * f * D)
    Fj = fo(f, RC_JERK)
    br = e + Fj * (1.0 - e) * (D + lead) / D
    RF = fo(f, rc_ref) ** 2 if rc_ref > 0 else 1.0
    return br * RF


def grp(f, H, lo, hi, w):
    s = (f >= lo) & (f <= hi)
    ph = np.unwrap(np.angle(H))[s]
    return -float(np.average(ph / (2 * np.pi * np.maximum(f[s], 1e-9)), weights=w[s])) * 1000


if __name__ == "__main__":
    print("=" * 104)
    print("POSITIVE CONTROL: the written-out chain vs the MEASURED Z/X")
    print(f"   {'build':7s} {'source |Z/X| 0.15-0.6':>22s} {'measured':>10s} | "
          f"{'source lag ms':>14s} {'measured':>10s}")
    for lab, routes, D, rc in (("T64", T64, D_T64, RC_REF), ("V282", V282R, D_V282, 0.0)):
        R = Ref(routes, corrected=False)
        f = R.f
        w = np.sum(np.abs(R.X) ** 2, 0)
        s = (f >= 0.15) & (f <= 0.6)
        Hm = np.sum(np.conj(R.X) * R.Z, 0) / np.sum(np.abs(R.X) ** 2, 0)
        Hs = chain(f, D, 0.0, rc)
        print(f"   {lab:7s} {float(np.average(np.abs(Hs[s]), weights=w[s])):22.3f} "
              f"{float(np.average(np.abs(Hm[s]), weights=w[s])):10.3f} | "
              f"{grp(f, Hs, 0.15, 0.6, w):14.0f} {grp(f, Hm, 0.15, 0.6, w):10.0f}")
        del R
    print("   (V282's fork carries no reference filter -- AccordRefFilter ABSENT in its initData.)")

    print("\n" + "=" * 104)
    print("THE MINIMAL DIFF, PRICED.  W = chain(D, lead) / chain(D, 0) applied to the flown setpoint.")
    R = Ref(T64, corrected=False)
    Rc = Ref(T64, corrected=True)
    f = R.f
    base = chain(f, D_T64, 0.0)
    print(f"   {'HONDA_ACCORD_SETPOINT_LEAD':28s} {'J':>8s} {'closure':>8s} {'J corr':>8s} "
          f"{'cmd shake':>10s} {'|W| 0.15-0.6':>13s} {'|W| @2.5Hz':>11s} {'net Z lag ms':>13s}")
    rows = []
    for L in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
        W = chain(f, D_T64, L) / base
        J, sh = R.apply(W)
        Jc, _ = Rc.apply(W)
        w = np.sum(np.abs(R.X) ** 2, 0)
        s = (f >= 0.15) & (f <= 0.6)
        print(f"   {L:28.2f} {J:8.4f} {(JFLOWN-J)/(JFLOWN-JREF)*100:7.1f}% {Jc:8.4f} {sh:10.3f} "
              f"{float(np.average(np.abs(W[s]), weights=w[s])):13.3f} "
              f"{abs(W[int(np.argmin(abs(f-2.5)))]):11.2f} "
              f"{grp(f, chain(f, D_T64, L), 0.15, 0.6, w):13.0f}")
        rows.append(dict(lead=L, J=J, Jc=Jc, shake=sh,
                         closure=(JFLOWN - J) / (JFLOWN - JREF)))

    print("\n   and composed with the toggle ceiling ARM-KP2 (SteerKP 3.0, AccordErrorNotchQ 0.60):")
    eng = Engine()
    D = R.Z - R.M
    C1 = C_of(f, eng.v, 3.0, 14.0, FLOWN["ki"], 0.0, 0.60)
    rho = (1.0 + eng.L0) / (1.0 + eng.L0 * (C1 / eng.C0))
    E1 = R.E + R.V * D * (rho - 1.0)
    print(f"   {'lead + ARM-KP2':28s} {'J':>8s} {'closure':>8s}")
    comp = []
    for L in (0.0, 0.05, 0.10, 0.15, 0.20):
        W = chain(f, D_T64, L) / base
        d = (W - 1.0)[None, :]
        J = float(np.sum(np.abs((E1 - d * R.G)[:, R.sel]) ** 2)) / R.px
        print(f"   {L:28.2f} {J:8.4f} {(JFLOWN-J)/(JFLOWN-JREF)*100:7.1f}%")
        comp.append(dict(lead=L, J=J, closure=(JFLOWN - J) / (JFLOWN - JREF)))

    print("\n" + "=" * 104)
    print("THE ALTERNATIVE NAMED IN THE BRIEF, priced on the same denominator:")
    print("   STEER_KP_MAX_MULT 5.0 -> higher, i.e. SteerKP past 3.00 (one constant, starpilot_variables.py:459)")
    print(f"   {'SteerKP':>10s} {'J':>8s} {'closure':>8s} {'shake-band |L|':>15s} {'vs r71 (0.515)':>15s}")
    for kp in (3.0, 4.0, 6.0, 9.0, 12.0):
        C1 = C_of(f, eng.v, kp, 14.0, FLOWN["ki"], 0.0, 0.60)
        L1 = eng.L0 * (C1 / eng.C0)
        rho = (1.0 + eng.L0) / (1.0 + L1)
        J = float(np.sum(np.abs((R.E + R.V * D * (rho - 1.0))[:, R.sel]) ** 2)) / R.px
        sl = float(np.mean(np.abs(L1[:, eng.shj])))
        print(f"   {kp:10.1f} {J:8.4f} {(JFLOWN-J)/(JFLOWN-JREF)*100:7.1f}% {sl:15.3f} {sl/0.515:14.2f}x")
    json.dump(dict(lead=rows, composed=comp), open(OUT / "d11.json", "w"), indent=1, default=float)
    print("\nwrote out/d11.json")
