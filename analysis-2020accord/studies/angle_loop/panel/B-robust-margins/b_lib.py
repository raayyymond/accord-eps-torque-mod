# -*- coding: utf-8 -*-
"""b_lib.py (panel B-robust-margins, 2026-10-01) -- loop models + GATE-2 primitives for the three robust implementations.
  B1  held-rate D (edit E5, gp-0x6a56) + I freeze on hand torque -- rev-2 class, independently re-sized, minimal knots
  B2  FRESH-rate D in the cave (1 kHz rate, not the 100 Hz hold) -> no 20 Hz anti-damping ceiling on Kd -> larger Kd
      damps the 1.3-2.3 Hz ring -> PM>=30 at a HIGHER highway Kp (more tracking) for the same margin
  B3  no firmware integrator (Ki=0): pure P (+held D); the fork's slow outer integral (tau_o>=1 s) carries DC
Built on the stability refuter's INDEPENDENT stab_lin (frf, exact monodromy, exact GM) and the full factorial
c1r2_members.  ANALYSIS ONLY.  The ONLY model change for B2 is the D operand's hold (see frf, dmode)."""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
for p in (HERE.parents[1] / "refute_stability", HERE.parents[1] / "c1", HERE.parents[2] / "v295" / "plant"):
    sys.path.insert(0, str(p))
import stab_lin as S            # noqa: E402
import c1r2_members as M        # noqa: E402
import c1_lib as C              # noqa: E402

TS = S.TS


def frf(ctl, plant, f, dmode="held", ema_hz=None):
    A, B, Ct, Cw = plant
    Ad, Bd = S.c2d(A, B)
    z = np.exp(1j * 2 * np.pi * np.asarray(f) * TS); zi = 1 / z
    # vectorised 2x2 resolvent (zI-Ad)^-1 Bd for the rigid plant (Ct=[1,0], Cw=[0,1])
    a, b2, c2, d2 = Ad[0, 0], Ad[0, 1], Ad[1, 0], Ad[1, 1]
    det = (z - a) * (z - d2) - b2 * c2
    Pt = ((z - d2) * Bd[0, 0] + b2 * Bd[1, 0]) / det
    Pw = (c2 * Bd[0, 0] + (z - a) * Bd[1, 0]) / det
    hold = sum(zi ** (a + ctl.extra_age) for a in range(1, 11)) / 10
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = ctl.fade * S.FWD * Hout * zi ** ctl.d
    g = ctl.G / 256
    PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - zi)
    Ctheta = g * PI * 80 * (1 + zi) * hold
    if dmode == "held":
        Comega = ctl.kd * hold
    elif dmode == "fresh":
        Comega = ctl.kd * np.ones_like(zi)
    elif dmode == "fresh_ema":
        a = math.exp(-2 * math.pi * ema_hz * TS)
        Comega = ctl.kd * (1 - a) / (1 - a * zi)
    else:
        raise ValueError(dmode)
    L = K * (Ctheta * Pt + Comega * Pw)
    return L, K * Ctheta, K * Comega, Pt, Pw


def margins(ctl, plant, dmode="held", ema_hz=None, fmin=0.02, fmax=499.0, npts=4000):
    f = np.logspace(math.log10(fmin), math.log10(fmax), npts)
    L = frf(ctl, plant, f, dmode, ema_hz)[0]
    mag = np.abs(L); ph = np.unwrap(np.angle(L)) * 180 / np.pi
    pms = []
    for i in range(len(f) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i]); p = ph[i] + t * (ph[i + 1] - ph[i])
            pms.append(((p + 180) + 180) % 360 - 180)
    gms = []
    for i in range(len(f) - 1):
        if math.floor((ph[i] + 180) / 360) != math.floor((ph[i + 1] + 180) / 360):
            gms.append(-20 * math.log10(max(mag[i], 1e-12)))
    Scl = 1 / (1 + L); band = (f >= 5) & (f <= 30)
    return dict(pm=min(pms) if pms else float('nan'), n_cross=len(pms),
                gm=min([g for g in gms if g > 0], default=float('inf')),
                Ms=float(np.max(np.abs(Scl))),
                Tpk530=float(np.max(np.abs(L[band] * Scl[band]))))


def re_t_over_w(kp_base, ki_base, kd, G, f, d=2, age=0, dmode="held", ema_hz=None):
    """Re(T/omega) in T counts per deg/s (the controller-output impedance, member independent), > 0 damps."""
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** (a + age) for a in range(1, 11)) / 10.0
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** d
    PI = kp_base / 256.0 + (ki_base / 32768.0) / (1 - zi)
    if dmode == "held":
        Cw = kd * hold
    elif dmode == "fresh":
        Cw = kd
    else:
        a = math.exp(-2 * math.pi * ema_hz * TS); Cw = kd * (1 - a) / (1 - a * zi)
    w = 2 * math.pi * f
    return (K * ((G / 256) * PI * 80 * (1 + zi) * hold / (1j * w) + Cw)).real


def ctl_at(v, tbl, kp_base, ki_base, kd, d=2, extra_age=0, G=None):
    return S.Ctl(v, kp=kp_base, ki=ki_base, kd=kd, d=d, extra_age=extra_age,
                 G=C.G_at(v, tbl) if G is None else G)


def gmax(name, v, thr, kp_base, ki_base, kd, dmode="held", ema_hz=None, Gmax=6000, step=16, Ms_bar=2.0, exact=True):
    J, b, k, dtau, ea = M.params(name, v)
    plant = S.rigid(J, b, k)
    best = 0
    for G in range(64, Gmax + 1, step):
        c = ctl_at(v, None, kp_base, ki_base, kd, d=dtau, extra_age=ea, G=G)
        m = margins(c, plant, dmode, ema_hz)
        ok = (m["Ms"] <= Ms_bar) and (m["gm"] >= 6.0) and (math.isnan(m["pm"]) or m["pm"] >= thr)
        if ok and exact and dmode == "held":
            ok = S.exact(c, plant)[0] < 1.0
        if not ok:
            break
        best = G
    return best
