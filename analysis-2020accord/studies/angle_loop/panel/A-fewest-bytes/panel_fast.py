# -*- coding: utf-8 -*-
"""panel_fast.py -- a VECTORISED copy of stab_lin's LTI loop FRF + margins for the re-key operating point (G=256),
validated against stab_lin.margins.  ANALYSIS ONLY.  Only the python-loop FRF is replaced; the maths is identical
(stab_lin.frf: Ctheta = g*PI*80*(1+z^-1)*hold ; Comega = kd*hold ; K = FADE*FWD*Hout*z^-d).
"""
from __future__ import annotations
import math, os, sys
from pathlib import Path
import numpy as np
from scipy import signal, linalg as sla

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1]), str(HERE.parents[1] / "c1"),
           str(HERE.parents[1] / "refute_stability"), str(HERE.parents[2] / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("C1_VARIANT", "r2")
import stab_lin as S   # noqa: E402  (FADE, FWD, OA, OB, TS, rigid, c2d, Ctl)

TS = S.TS
_F = np.logspace(math.log10(0.02), math.log10(499.0), 4000)
_ZI = np.exp(-1j * 2 * np.pi * _F * TS)
_Z = 1.0 / _ZI
_HOLD_BASE = np.array([_ZI ** a for a in range(1, 11)])          # (10, NF)
_HOUT = (S.OB / 1024) * (1 + _ZI) / (32 * (1 - (S.OA / 1024) * _ZI))


def _tf(Ad, Bd, C):
    num, den = signal.ss2tf(Ad, Bd, C, np.zeros((1, 1)))
    return num[0], den


def loop_frf(ctl, plant):
    A, B, Ct, Cw = plant
    Ad, Bd = S.c2d(A, B)
    nt, den = _tf(Ad, Bd, Ct)
    nw, _ = _tf(Ad, Bd, Cw)
    Pt = np.polyval(nt, _Z) / np.polyval(den, _Z)
    Pw = np.polyval(nw, _Z) / np.polyval(den, _Z)
    hold = _HOLD_BASE
    if ctl.extra_age:
        hold = hold * (_ZI ** ctl.extra_age)
    hold = hold.mean(axis=0)
    K = ctl.fade * S.FWD * _HOUT * (_ZI ** ctl.d)
    g = ctl.G / 256
    PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - _ZI)
    Ctheta = g * PI * 80 * (1 + _ZI) * hold
    Comega = ctl.kd * hold
    L = K * (Ctheta * Pt + Comega * Pw)
    return L


def margins(ctl, plant):
    L = loop_frf(ctl, plant)
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    f = _F
    # |L|=1 crossings -> PM = min over crossings
    cr = np.where((mag[:-1] - 1) * (mag[1:] - 1) <= 0)[0]
    pms = []
    for i in cr:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        pms.append(((p + 180) + 180) % 360 - 180)
    pm = min(pms) if pms else float("nan")
    # gain margin (LTI): |L| at the -180 deg phase crossing(s)
    im = L.imag
    jx = np.where((np.sign(im[:-1]) != np.sign(im[1:])) & (L.real[:-1] < 0))[0]
    Lneg = [abs(L[j]) for j in jx]
    gm_db = (20 * math.log10(1.0 / max(Lneg))) if Lneg else float("inf")
    # Ms and the 5-30 Hz closed-loop peak of |T_c| = |L/(1+L)|
    S_ = 1.0 / (1.0 + L)
    Tc = L * S_
    band = (f >= 5) & (f <= 30)
    return dict(pm=pm, gm_db=gm_db, Ms=float(np.abs(S_).max()), Tc530_db=20 * math.log10(float(np.abs(Tc[band]).max())),
                S530_db=20 * math.log10(float(np.abs(S_[band]).max())), L=L)


def re_tpr(ctl, f):
    """Re(T/omega): T counts per deg/s at f (stab_hf.torque_per_rate for a stab_lin.Ctl)."""
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** a for a in range(1, 11)) / 10
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** ctl.d
    w = 2 * np.pi * f
    g = ctl.G / 256
    PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - zi)
    Cth = g * PI * 80 * (1 + zi) * hold
    Cw = ctl.kd * hold
    return complex(K * (Cth / (1j * w) + Cw))


def m20(ctl):
    f = 20.0
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** a for a in range(1, 11)) / 10
    g = ctl.G / 256
    PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - zi)
    Cth = g * PI * 80 * (1 + zi) * hold
    return float(abs(Cth / (8 * 2 * np.pi * f)))


if __name__ == "__main__":
    import panel_schedules as PS
    import c1r2_members as M
    print("validate panel_fast.margins vs stab_lin.margins (should agree within ~1 deg):")
    for n, v in (("nominal", 8.0), ("b/1.9*J1.0*tau6+h10", 11.0), ("b_q*J1.0", 17.0), ("J_hi", 3.0)):
        pl, tau, bea, jbk = M.member(n, v)
        c = S.Ctl(v, kp=PS.kp_of(v), ki=PS.ki_of(v, "A2"), kd=20, d=tau, extra_age=bea, G=256)
        a = margins(c, pl)["pm"]
        b = S.margins(c, pl, npts=4000)["pm"]
        print(f"  {n:28s}@{v:5.1f}: fast {a:7.2f}  stab_lin {b:7.2f}  d {abs(a-b):.2f}")
