# -*- coding: utf-8 -*-
"""b2_stab.py -- EXACT 10-tick periodic monodromy for B2 (FRESH-rate D).  A copy of stab_lin.phase_mats with ONE change:
the D term uses the CURRENT plant angular velocity w_now (fresh 1 kHz) instead of the slot-4 held register.  The P/I
angle path stays on the 100 Hz hold, exactly as the in-place edits leave it.  Gives spectral radius (stability),
least-damped poles, and exact GM by bisection -- the independent stability proof the FRF PM/Ms cannot give alone.
ANALYSIS ONLY."""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "refute_stability"))
import stab_lin as S  # noqa: E402


def phase_mats_fresh(ctl, plant, gain=1.0):
    A, B, Ct, Cw = plant
    Ad, Bd = S.c2d(A, B); npl = Ad.shape[0]; d = ctl.d
    # NO held-rate register: fresh D reads the current plant omega every tick.  (A disconnected held register would be a
    # spurious eigenvalue-1 state and make rho == 1 for every loop.)
    ip = 0; iu = npl; io = npl + d; isp = io + 1; iI = isp + 1; ith = iI + 1
    ea = ctl.extra_age
    iea_t = ith + 1; N = iea_t + ea
    g = ctl.G / 256
    mats = []
    for p in range(10):
        M = np.zeros((N, N))
        def row(): return np.zeros(N)
        th_h = row(); th_h[ith] = 1
        s_prev = row(); s_prev[isp] = 1
        E = -80 * (th_h + s_prev)
        Ep = g * E
        I_new = row(); I_new[iI] = 1; I_new = I_new + Ep * ctl.ki / 32768
        P = Ep * ctl.kp / 256
        w_now = row(); w_now[ip:ip + npl] = Cw[0]        # FRESH rate (current plant omega), no hold register
        D = -ctl.kd * w_now
        Sx = P + I_new + D
        Sf = ctl.fade * Sx
        o_new = row(); o_new[io] = S.OA / 1024; o_new = o_new + (S.OB / 1024) * Sf
        o_prev = row(); o_prev[io] = 1
        y = (o_prev + o_new) / 32
        ucmd = gain * S.FWD * y
        if d == 0:
            uin = ucmd
        else:
            uin = row(); uin[iu + d - 1] = 1
        M[ip:ip + npl, ip:ip + npl] = Ad
        M[ip:ip + npl, :] += np.outer(Bd[:, 0], uin)
        if d > 0:
            M[iu, :] = ucmd
            for i in range(1, d):
                M[iu + i, iu + i - 1] = 1
        M[io, :] = o_new
        M[isp, :] = th_h
        M[iI, :] = I_new
        th_now = np.zeros(N); th_now[ip:ip + npl] = Ct[0]
        w_src = np.zeros(N); w_src[ip:ip + npl] = Cw[0]
        if ea > 0:
            M[iea_t, :] = th_now
            for i in range(1, ea):
                M[iea_t + i, iea_t + i - 1] = 1
            src_t = np.zeros(N); src_t[iea_t + ea - 1] = 1
        else:
            src_t = th_now
        if p == S.HOLD_PHASE:
            M[ith, :] = src_t          # the P/I angle hold register (slot-4); D does NOT use it
        else:
            M[ith, ith] = 1
        mats.append(M)
    return mats


def _rho(ctl, plant, gain=1.0):
    Phi = np.eye(phase_mats_fresh(ctl, plant, gain)[0].shape[0])
    for Mx in phase_mats_fresh(ctl, plant, gain):
        Phi = Mx @ Phi
    return float(np.max(np.abs(np.linalg.eigvals(Phi))))


def exact_fresh(ctl, plant):
    Phi = np.eye(phase_mats_fresh(ctl, plant)[0].shape[0])
    for Mx in phase_mats_fresh(ctl, plant):
        Phi = Mx @ Phi
    lam = np.linalg.eigvals(Phi); rho = float(np.max(np.abs(lam)))
    poles = []
    for l in lam:
        if abs(l) < 1e-9:
            continue
        s = np.log(l) / (10 * S.TS); fhz = abs(s.imag) / (2 * np.pi)
        if fhz < 0.3:
            continue
        poles.append((fhz, -s.real / abs(s)))
    poles.sort(key=lambda t: t[1])
    return rho, poles


def exact_gm_fresh(ctl, plant):
    if _rho(ctl, plant, 1.0) >= 1:
        lo, hi = 1e-3, 1.0
        for _ in range(50):
            m = math.sqrt(lo * hi)
            if _rho(ctl, plant, m) >= 1:
                hi = m
            else:
                lo = m
        return 20 * math.log10(lo)
    lo, hi = 1.0, 1.0
    while _rho(ctl, plant, hi) < 1 and hi < 1e4:
        lo, hi = hi, hi * 2
    for _ in range(50):
        m = math.sqrt(lo * hi)
        if _rho(ctl, plant, m) < 1:
            lo = m
        else:
            hi = m
    return 20 * math.log10(lo)


if __name__ == "__main__":
    import b_lib as B
    import c1_lib as C
    import c1r2_members as M
    tbl = C.c1_table()
    print("B2 fresh-D exact monodromy sanity (Kp112 Ki56 Kd28, r2 table) on the binding members:")
    for n in ("nominal", "b_q*J1.0", "b_q*J1.0+h10", "b_q*J_hi"):
        for v in (12.5, 17.0, 26.9):
            J, b, k, dt, ea = M.params(n, v); pl = S.rigid(J, b, k)
            c = B.ctl_at(v, tbl, 112, 56, 28, d=dt, extra_age=ea, G=C.G_at(v, tbl))
            rho, poles = exact_fresh(c, pl)
            gm = exact_gm_fresh(c, pl)
            print(f"  {n:14s} v{v:5.1f} rho {rho:.4f} GM {gm:5.1f} dB  least-damped {poles[:2]}")


def phase_mats_gen(ctl, plant, dmode="held", with_I=True, gain=1.0):
    """general 10-tick monodromy: dmode 'held'|'fresh' for D; with_I False drops the integrator state entirely (Ki=0,
    so the stock I register is dead and would be a spurious eigenvalue-1 state)."""
    A, B, Ct, Cw = plant
    Ad, Bd = S.c2d(A, B); npl = Ad.shape[0]; d = ctl.d
    ip = 0; iu = npl; io = npl + d; isp = io + 1
    iI = (isp + 1) if with_I else None
    ith = (iI + 1) if with_I else (isp + 1)
    ea = ctl.extra_age
    iw = (ith + 1) if dmode == "held" else None
    iea_t = (iw + 1) if dmode == "held" else (ith + 1)
    N = iea_t + ea
    g = ctl.G / 256
    mats = []
    for p in range(10):
        M = np.zeros((N, N))
        def row(): return np.zeros(N)
        th_h = row(); th_h[ith] = 1
        s_prev = row(); s_prev[isp] = 1
        E = -80 * (th_h + s_prev)
        Ep = g * E
        if with_I:
            I_new = row(); I_new[iI] = 1; I_new = I_new + Ep * ctl.ki / 32768
        else:
            I_new = row()
        P = Ep * ctl.kp / 256
        if dmode == "held":
            w_used = row(); w_used[iw] = 1
        else:
            w_used = row(); w_used[ip:ip + npl] = Cw[0]
        D = -ctl.kd * w_used
        Sx = P + I_new + D
        Sf = ctl.fade * Sx
        o_new = row(); o_new[io] = S.OA / 1024; o_new = o_new + (S.OB / 1024) * Sf
        o_prev = row(); o_prev[io] = 1
        y = (o_prev + o_new) / 32
        ucmd = gain * S.FWD * y
        if d == 0:
            uin = ucmd
        else:
            uin = row(); uin[iu + d - 1] = 1
        M[ip:ip + npl, ip:ip + npl] = Ad
        M[ip:ip + npl, :] += np.outer(Bd[:, 0], uin)
        if d > 0:
            M[iu, :] = ucmd
            for i in range(1, d):
                M[iu + i, iu + i - 1] = 1
        M[io, :] = o_new
        M[isp, :] = th_h
        if with_I:
            M[iI, :] = I_new
        th_now = np.zeros(N); th_now[ip:ip + npl] = Ct[0]
        w_now = np.zeros(N); w_now[ip:ip + npl] = Cw[0]
        if ea > 0:
            M[iea_t, :] = th_now
            for i in range(1, ea):
                M[iea_t + i, iea_t + i - 1] = 1
            src_t = np.zeros(N); src_t[iea_t + ea - 1] = 1
        else:
            src_t = th_now
        if p == S.HOLD_PHASE:
            M[ith, :] = src_t
            if dmode == "held":
                M[iw, :] = w_now
        else:
            M[ith, ith] = 1
            if dmode == "held":
                M[iw, iw] = 1
        mats.append(M)
    return mats


def rho_gen(ctl, plant, dmode="held", with_I=True, gain=1.0):
    Phi = np.eye(phase_mats_gen(ctl, plant, dmode, with_I, gain)[0].shape[0])
    for Mx in phase_mats_gen(ctl, plant, dmode, with_I, gain):
        Phi = Mx @ Phi
    lam = np.linalg.eigvals(Phi)
    return float(np.max(np.abs(lam)))


def exact_gm_gen(ctl, plant, dmode="held", with_I=True):
    if rho_gen(ctl, plant, dmode, with_I, 1.0) >= 1:
        lo, hi = 1e-3, 1.0
        for _ in range(48):
            m = math.sqrt(lo * hi)
            if rho_gen(ctl, plant, dmode, with_I, m) >= 1: hi = m
            else: lo = m
        return 20 * math.log10(lo)
    lo, hi = 1.0, 1.0
    while rho_gen(ctl, plant, dmode, with_I, hi) < 1 and hi < 1e4:
        lo, hi = hi, hi * 2
    for _ in range(48):
        m = math.sqrt(lo * hi)
        if rho_gen(ctl, plant, dmode, with_I, m) < 1: lo = m
        else: hi = m
    return 20 * math.log10(lo)
