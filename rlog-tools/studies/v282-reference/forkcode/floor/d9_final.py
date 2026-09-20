# -*- coding: utf-8 -*-
"""d9 -- SEPARATE THE TWO THINGS THE REFERENCE LADDER WAS DOING, and close the budget.

d8 found the best setpoint prefilter reaching J 0.295-0.296 (116 % closure), surviving the
instrument correction.  But it does TWO things at once and only one of them is control:

  SHRINKAGE.  With incoherent motion present (Y = X + n), the error-power metric is minimised at
  a gain g* = |X|^2/(|X|^2 + |n|^2) < 1.  Delivering LESS lowers |E|^2 without tracking better.
  The free optimum's |W| falls to 0.22 at 0.59 Hz -- that is the pathology, not a lever.

  TIMING.  A pure LEAD costs no magnitude and is realizable: the fork already builds the setpoint
  from a plan buffer and a lat_delay compensation, so advancing it further is a code change of the
  same kind it already makes.

So every class below is refit with the GAIN LOCKED AT 1.0, which removes the shrinkage channel by
construction.  Whatever survives is timing and shape, not under-delivery.

Also here: the same levers composed with loop gain, and the closed budget.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import optimize

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
sys.path.insert(0, str(HERE.parents[1] / "shapedgain" / "frontier"))
import lp_lib as LP                          # noqa: E402
from f5_frontier import Engine, C_of, FLOWN  # noqa: E402
from d8_refladder import Ref, T64, V282R, TAU_I, JREF, JFLOWN, BAND, SHAKE  # noqa: E402


def lead_only(f, p):
    return np.exp(2j * np.pi * f * p[0])


def lead_lag(f, p):
    # unity DC gain, one lead and one first-order lag: no shrinkage channel at DC
    return np.exp(2j * np.pi * f * p[0]) / (1.0 + 2j * np.pi * f * max(p[1], 0.0))


def scan_lead(R, taus):
    return np.array([R.apply(np.exp(2j * np.pi * R.f * t)) for t in taus])


def part_a():
    print("=" * 108)
    print("A. GAIN LOCKED AT 1.0 -- what survives when the shrinkage channel is closed")
    out = {}
    for corrected in (False, True):
        for lab in ("T64", "V282"):
            R = Ref(T64 if lab == "T64" else V282R, corrected)
            taus = np.arange(0.0, 0.601, 0.005)
            sc = scan_lead(R, taus)
            i = int(np.argmin(sc[:, 0]))
            r2 = optimize.minimize(lambda p: R.apply(lead_lag(R.f, p))[0], [taus[i], 0.05],
                                   method="Nelder-Mead", options=dict(maxiter=3000))
            J2, s2 = R.apply(lead_lag(R.f, r2.x))
            tg = "corrected" if corrected else "raw      "
            print(f"\n  {lab:5s} {tg}  J as flown {R.J0:.4f}")
            print(f"    pure LEAD, best      {sc[i,0]:.4f}  closure "
                  f"{(JFLOWN-sc[i,0])/(JFLOWN-JREF)*100:6.1f}%  cmd shake x{sc[i,1]:.3f}"
                  f"   lead {taus[i]*1000:.0f} ms")
            print(f"    LEAD + first-order lag {J2:.4f}  closure "
                  f"{(JFLOWN-J2)/(JFLOWN-JREF)*100:6.1f}%  cmd shake x{s2:.3f}"
                  f"   lead {r2.x[0]*1000:.0f} ms, lag {max(r2.x[1],0)*1000:.0f} ms")
            print(f"    lead sweep (ms : J) " + " ".join(
                f"{t*1000:.0f}:{sc[int(round(t/0.005)),0]:.3f}" for t in (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50)))
            out[f"{lab}|{'corr' if corrected else 'raw'}"] = dict(
                J0=R.J0, lead_tau=float(taus[i]), lead_J=float(sc[i, 0]), lead_shake=float(sc[i, 1]),
                ll_J=float(J2), ll_shake=float(s2), ll_p=list(map(float, r2.x)))
            del R
    return out


def part_b():
    print("\n" + "=" * 108)
    print("B. THE LEVERS COMPOSED.  Loop gain (rho on D) x setpoint lead, on the metric as defined.")
    eng = Engine()
    R = Ref(T64, corrected=False)
    f = R.f
    D = R.Z - R.M
    print(f"    {'':22s} " + " ".join(f"{'lead ' + str(int(t*1000)) + 'ms':>11s}" for t in (0.0, 0.10, 0.20, 0.30, 0.40)))
    rows = {}
    for nm, kp, q in (("as flown          ", 1.0, 1.00), ("ARM-KP2 3.0 Q0.60 ", 3.0, 0.60),
                      ("SteerKP 6.0       ", 6.0, 0.60), ("infinite gain     ", None, None)):
        line = []
        for t in (0.0, 0.10, 0.20, 0.30, 0.40):
            if kp is None:
                rho = np.zeros_like(R.E)
            else:
                C1 = C_of(f, eng.v, kp, 14.0, FLOWN["ki"], 0.0, q)
                rho = (1.0 + eng.L0) / (1.0 + eng.L0 * (C1 / eng.C0))
            E1 = R.E + R.V * D * (rho - 1.0)
            d = (np.exp(2j * np.pi * f * t) - 1.0)[None, :]
            E2 = E1 - d * R.G
            J = float(np.sum(np.abs(E2[:, R.sel]) ** 2)) / R.px
            line.append(J)
        rows[nm.strip()] = line
        print(f"    {nm:22s} " + " ".join(f"{v:11.4f}" for v in line))
    print("    (closure %, same rows)")
    for nm, line in rows.items():
        print(f"    {nm:22s} " + " ".join(f"{(JFLOWN-v)/(JFLOWN-JREF)*100:10.1f}%" for v in line))
    del R
    return rows


def part_c():
    print("\n" + "=" * 108)
    print("C. IS THE LEAD ALREADY THERE?  The fork's own delay compensation, measured on the wire.")
    print("   Z is built as expected_lataccel(t - lat_delay) + jerk*lat_delay, then ref-filtered.")
    print("   The NET lead of Z over X is measurable: argmax_t Re(sum conj(X) Z e^{-j2 pi f t}).")
    for lab, routes in (("T64", T64), ("V282", V282R)):
        R = Ref(routes, corrected=False)
        f = R.f
        s = (f >= 0.15) & (f <= 1.0)
        Sxz = np.sum(np.conj(R.X[:, s]) * R.Z[:, s], 0)
        w = np.abs(Sxz)
        taus = np.arange(-0.4, 0.401, 0.002)
        sc = [np.sum(w * np.real(Sxz / np.abs(Sxz) * np.exp(-2j * np.pi * f[s] * t))) for t in taus]
        t0 = taus[int(np.argmax(sc))]
        g = float(np.abs(np.sum(np.conj(R.X[:, s]) * R.Z[:, s]) / np.sum(np.abs(R.X[:, s]) ** 2)))
        # and the net X -> Y lag as flown
        Sxy = np.sum(np.conj(R.X[:, s]) * R.Y[:, s], 0)
        w2 = np.abs(Sxy)
        sc2 = [np.sum(w2 * np.real(Sxy / np.abs(Sxy) * np.exp(+2j * np.pi * f[s] * t))) for t in taus]
        t1 = taus[int(np.argmax(sc2))]
        print(f"   {lab:6s}  Z leads X by {t0*1000:+6.0f} ms (gain {g:.3f})   |   "
              f"Y lags X by {t1*1000:+6.0f} ms as flown (includes the 102 ms instrument)")
        del R


def part_d():
    print("\n" + "=" * 108)
    print("D. THE ANSWER TABLE.  J, closure, and the shake the operator pays, all on one denominator.")
    R = Ref(T64, corrected=False)
    eng = Engine()
    f = R.f
    D = R.Z - R.M
    rows = []

    def add(name, J, shake, reach, note):
        rows.append(dict(name=name, J=J, closure=(JFLOWN - J) / (JFLOWN - JREF), shake=shake,
                         reach=reach, note=note))

    add("as flown (rev 6.4)", R.J0, 1.000, "-", "-")
    for nm, kp, q, sh in (("ARM-KP2 (toggle ceiling)", 3.0, 0.60, 1.148),):
        C1 = C_of(f, eng.v, kp, 14.0, FLOWN["ki"], 0.0, q)
        rho = (1.0 + eng.L0) / (1.0 + eng.L0 * (C1 / eng.C0))
        add(nm, float(np.sum(np.abs((R.E + R.V * D * (rho - 1.0))[:, R.sel]) ** 2)) / R.px, sh,
            "toggle", "brief: J 1.058 / 33.3 % on V_h1")
    for t, nm in ((0.10, "setpoint lead +100 ms"), (0.20, "setpoint lead +200 ms"),
                  (0.30, "setpoint lead +300 ms")):
        J, sh = R.apply(np.exp(2j * np.pi * f * t))
        add(nm, J, sh, "fork code (reference path)", "gain locked 1.0")
    C1 = C_of(f, eng.v, 3.0, 14.0, FLOWN["ki"], 0.0, 0.60)
    rho = (1.0 + eng.L0) / (1.0 + eng.L0 * (C1 / eng.C0))
    E1 = R.E + R.V * D * (rho - 1.0)
    d = (np.exp(2j * np.pi * f * 0.20) - 1.0)[None, :]
    add("ARM-KP2 + lead +200 ms", float(np.sum(np.abs((E1 - d * R.G)[:, R.sel]) ** 2)) / R.px,
        None, "toggle + fork code", "composed")
    add("infinite loop gain", float(np.sum(np.abs((R.E - R.V * D)[:, R.sel]) ** 2)) / R.px, None,
        "unreachable", "algebraic limit of the gain class")
    print(f"   {'configuration':30s} {'J':>8s} {'closure':>9s} {'cmd shake':>10s}  {'reachable by':26s} note")
    for r in rows:
        sh = "-" if r["shake"] is None else f"x{r['shake']:.3f}"
        print(f"   {r['name']:30s} {r['J']:8.4f} {r['closure']*100:8.1f}% {sh:>10s}  "
              f"{r['reach']:26s} {r['note']}")
    del R
    return rows


if __name__ == "__main__":
    o = {}
    o["locked"] = part_a()
    o["composed"] = part_b()
    part_c()
    o["answer"] = part_d()
    json.dump(o, open(OUT / "d9.json", "w"), indent=1, default=float)
    print("\nwrote out/d9.json")
