# -*- coding: utf-8 -*-
"""c3r1_intlane_run.py -- integer-lane checks (stability lens): T1 ring vs the exact periodic linear model at the binding
points; T2 settled limit cycles with friction; T3 the A3 bound regime under a constant road torque at theta_sp = 0;
T4 the rate-invalid state (D off) on the worst PI.D0 points.  python c3r1_intlane_run.py [T1|T2|T3|T4|all]"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_intlane as IL  # noqa: E402

D = M.designs()
S_C = 1.155
FR = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0), "FB.83": (0.83, 1 / S_C), "FA1.155": (1.155, 1.0), "FB1.155": (1.155, 1 / S_C)}
out = []
P = lambda *a: (out.append(" ".join(str(x) for x in a)), print(out[-1], flush=True))  # noqa: E731


def ring(x, t0):
    """peaks of x after t0 (ms ticks): (f Hz, zeta) from the first two positive peaks of the error."""
    y = x[t0:]
    pk = [i for i in range(1, len(y) - 1) if y[i] > y[i - 1] and y[i] >= y[i + 1] and y[i] > 1e-4]
    if len(pk) < 2:
        return math.nan, math.nan, (y.max() if len(y) else math.nan)
    T = (pk[1] - pk[0]) * 1e-3
    d = math.log(max(y[pk[0]], 1e-9) / max(y[pk[1]], 1e-9))
    return 1 / T, d / math.sqrt(4 * math.pi ** 2 + d * d), y[pk[0]]


def settled(x, n_last=2000):
    y = x[-n_last:] - np.mean(x[-n_last:])
    Y = np.abs(np.fft.rfft(y * np.hanning(len(y))))
    f = np.fft.rfftfreq(len(y), 1e-3)
    j = int(np.argmax(Y[1:]) + 1)
    return float(np.ptp(x[-n_last:])), float(f[j])


def band_fric(v):
    Fc = np.interp(v, M.VC, [76.2, 13.49, 15.79, 7.86, 4.36])
    Fs = np.interp(v, M.VC, [94.7, 18.9, 18.6, 10.0, 5.6])
    return float(Fc), float(Fs / max(Fc, 1e-9))


def T1():
    P("T1 -- frictionless step response, integer lane vs the exact periodic linear model (least-damped pole)")
    pts = [("C3-P", "b_q*J1.0", 26.9, 10, "FB.83"), ("C3-P", "b_q*ms_free", 15.75, 10, "FA.83"),
           ("C3-P", "b_lo*ms_free", 9.0, 10, "FA.83"), ("C3-P", "J_hi", 1.0, 0, "FA.83"),
           ("C3-P", "nominal", 12.5, 0, "nom"), ("C3-P", "nominal", 26.9, 0, "nom"),
           ("C3-F", "b_q*J1.0", 27.0, 10, "FB.83"), ("C3-F", "b_lo*ms_free", 8.75, 10, "FB.83"),
           ("C3-F", "b_q*ms_free", 15.75, 10, "FB.83"), ("C3-F", "J_hi", 1.0, 0, "FA.83")]
    for dn, mem, v, e, fr in pts:
        kap, jb = FR[fr]
        pl = M.member(mem, v)
        rho, fl, zl, _ = M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb).rho_ring()
        for A in (0.3, 2.0):
            n = 6000
            r = IL.simulate(D[dn], pl, v, n, lambda k: np.full(1, A if k >= 200 else 0.0), e=e, kappa=kap, jb=jb)
            th = r["th"][0]
            f, z, p1 = ring(th - A, 200)
            pp, fs = settled(th)
            P(f"  {dn} {mem}@{v} e{e} {fr} step {A}: overshoot {100 * (th.max() - A) / A:5.1f}%  ring {f:.2f} Hz zeta {z:.3f}"
              f"  | linear rho {rho:.4f} pole {fl:.2f} Hz zeta {zl:.3f} | settled last 2 s pk-pk {pp:.4f} deg (f {fs:.2f} Hz)"
              f" T pk-pk {np.ptp(r['T'][0, -2000:]):.0f}")


def T2():
    P("T2 -- friction (Karnopp, ident Fc/Fs at the speed; x2 = F_hi), 2 deg step then hold 8 s: settled oscillation")
    pts = [("C3-P", "nominal", v, 0, "nom") for v in (3.1, 5.0, 8.0, 10.0, 12.5, 15.0, 20.0, 26.9)] + \
          [("C3-F", "nominal", v, 0, "nom") for v in (3.1, 8.0, 12.5, 20.0, 26.9)] + \
          [("C3-P", "b_q*J1.0", 26.9, 10, "FB.83"), ("C3-P", "b_q*ms_free", 15.75, 10, "FA.83"),
           ("C3-P", "b_lo*ms_free", 9.0, 10, "FA.83")]
    for dn, mem, v, e, fr in pts:
        kap, jb = FR[fr]
        pl = M.member(mem, v)
        Fc, rs = band_fric(v)
        for fm in (1.0, 2.0):
            n = 9000
            r = IL.simulate(D[dn], pl, v, n, lambda k: np.full(1, 2.0 if k >= 200 else 0.0), e=e, kappa=kap, jb=jb,
                            fric=Fc * fm, Fs_ratio=rs, record=("th", "T", "I", "frozen"))
            th = r["th"][0]
            pp, fs = settled(th, 3000)
            ppT, fT = settled(r["T"][0], 3000)
            P(f"  {dn} {mem}@{v} e{e} {fr} Fc {Fc * fm:5.1f}: settled (last 3 s) theta pk-pk {pp:.3f} deg (f {fs:.2f} Hz),"
              f" T pk-pk {ppT:.0f} (f {fT:.2f} Hz), final err {th[-1] - 2.0:+.3f} deg")


def T3():
    P("T3 -- the A3 bound regime: constant road torque at theta_sp = 0 (no friction / nominal friction), 12 s")
    for dn in ("C3-P", "C3-F"):
        for v in (5.0, 10.0, 13.5, 20.0, 26.9):
            for crown in (150.0, 300.0, 600.0):
                for fm in (0.0, 1.0):
                    pl = M.member("nominal", v)
                    Fc, rs = band_fric(v)
                    n = 12000
                    r = IL.simulate(D[dn], pl, v, n, lambda k: np.zeros(1), crown=crown, fric=Fc * fm, Fs_ratio=rs)
                    th = r["th"][0]
                    pp, fs = settled(th, 3000)
                    fz = r["frozen"][0, -3000:].mean()
                    P(f"  {dn} @{v} crown {crown:4.0f} T fric x{fm:.0f}: steady theta {th[-1]:+.3f} deg, I {r['I'][0, -1]:+.0f} S,"
                      f" settled pk-pk {pp:.4f} deg (f {fs:.2f} Hz), freeze duty {fz:.2f}, max |theta| {np.abs(th).max():.2f}")


def T4():
    P("T4 -- rate invalid (op := 0 for C3-P via Honda's guard; held cell 0 for C3-F): D off from t = 1 s, 2 deg hold")
    pts = [("C3-P", "nominal", v, 0, "nom") for v in (1.0, 3.1, 8.0, 12.5, 20.0, 26.9)] + \
          [("C3-F", "nominal", v, 0, "nom") for v in (1.0, 8.0, 26.9)] + \
          [("C3-P", "b_q*J1.0", 26.9, 10, "FB.83"), ("C3-P", "b_q*ms_free", 15.75, 10, "FA.83"),
           ("C3-P", "J_hi", 1.0, 0, "FA.83"), ("C3-P", "b_lo*J_hi", 8.0, 0, "nom")]
    for dn, mem, v, e, fr in pts:
        kap, jb = FR[fr]
        pl = M.member(mem, v)
        rho, fl, zl, _ = M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb, kd_scale=0.0).rho_ring()
        n = 6000
        r = IL.simulate(D[dn], pl, v, n, lambda k: np.full(1, 2.0 if k >= 200 else 0.0) + (0.5 if k >= 1500 else 0.0),
                        e=e, kappa=kap, jb=jb, invalid_after=1000)
        th = r["th"][0]
        f, z, p1 = ring(th - 2.5, 1500)
        P(f"  {dn} {mem}@{v} e{e} {fr}: D-off linear rho {rho:.4f} pole {fl:.2f} Hz zeta {zl:.3f} | integer: 0.5 deg step"
          f" under D-off: ring {f:.2f} Hz zeta {z:.3f}, max |err| after {np.abs(th[1500:] - 2.5).max():.3f} deg")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("T1", T1), ("T2", T2), ("T3", T3), ("T4", T4)):
        if which in (name, "all"):
            fn()
    (Path(M.OUT) / f"intlane_{which}.txt").write_text("\n".join(out), encoding="utf-8")
