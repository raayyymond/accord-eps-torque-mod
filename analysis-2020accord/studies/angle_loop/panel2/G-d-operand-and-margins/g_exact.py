# -*- coding: utf-8 -*-
r"""g_exact.py -- designer G's OWN exact periodic (1 kHz, 10-tick) model of the edited lane, independent of ds_model.Lifted
and of the refuter's c2r2_model (written here from the lane description; validated against ds_model.Lifted's rho on the
fresh / held structures in g_selftest2).  ANALYSIS ONLY.

Per tick n (phase p = n % 10), linear in the state, slot 4 (p == 4) refreshes the held registers AFTER the lane:
    r      = (1 - a) r + a w                                gp-0x6abe EMA (deg/s), a = 37/128, BEFORE the lane
    E'     = g (160 sp_h - 80 (th_h + th_hp))              E = 4 sp - r26 with r26 = 8 th_h[n] + 8 th_h[n-1] (counts)
    I     += (Ki / 32768) E'                                P = (Kp / 256) E'
    D      = fresh:  kappa (Kd/8) ABE r                     (ABE = -4.712 counts per deg/s)
             held:   -kappa Kd x_h                          (x_h = held 8 r / 8 = the slot-4 sample of r, deg/s)
             box10:  -(Kd/8) k_op 10 (th_h - th_hq)         (th_hq = the held angle before the last refresh)
    S      = I + P + D ; o' = (OA o + OB fade S)/1024 ; y = (o + o')/32 ; u = FWD y (transport d ticks)
    plant  ZOH (rigid J b k, or the brief's two-mass mu form), sensed angle and rate MOTOR side
Ages: ea = extra ticks the slot-4 sample is late (0 -> ages 1..10, 10 -> 11..20, 20 -> 21..30, -1 -> 0..9).
sp_h: the setpoint hold (only the reference path; irrelevant to rho).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402

DM = X.DM
ALPHA, ABE, FWD, OA, OB, FADE = DM.ALPHA, DM.ABE_PER, DM.FWD, DM.OA, DM.OB, DM.FADE


class Exact:
    def __init__(self, dkind, plant, d, ea, G, kp, ki, kd, kappa=1.0, dop_k=64.0):
        A, B, Ct, Cw = plant
        self.Ad, self.Bd = DM.c2d(A, B)
        self.Ct, self.Cw = np.asarray(Ct).ravel(), np.asarray(Cw).ravel()
        self.npl = self.Ad.shape[0]
        self.dkind, self.d, self.ea = dkind, int(d), int(ea)
        self.g, self.kp, self.ki, self.kd, self.kappa, self.dop_k = G / 256.0, kp / 256.0, ki / 32768.0, kd, kappa, dop_k
        names = [("xp", self.npl), ("r", 1), ("thh", 1), ("thhp", 1), ("thhq", 1), ("xh", 1), ("I", 1), ("o", 1),
                 ("ub", max(self.d, 1))]
        if self.ea > 0:
            names += [("bt", self.ea), ("br", self.ea)]
        self.ix, n = {}, 0
        for nm, k in names:
            self.ix[nm] = n
            n += k
        self.N = n

    def _phase(self, p, gain):
        N, ix = self.N, self.ix
        M = np.zeros((N, N))

        def e(nm, k=0):
            v = np.zeros(N)
            v[ix[nm] + k] = 1.0
            return v
        xp = np.array([e("xp", i) for i in range(self.npl)])
        th = self.Ct @ xp
        om = self.Cw @ xp
        r_new = (1 - ALPHA) * e("r") + ALPHA * om
        thh, thhp, thhq, xh = e("thh"), e("thhp"), e("thhq"), e("xh")
        slot = p == 4
        if slot and self.ea < 0:                     # ages 0..9: slot 4 BEFORE the lane on its tick
            thhq = thh
            thh = th
            xh = r_new
        Ep = self.g * (-80.0 * (thh + thhp))
        I_new = e("I") + self.ki * Ep
        P = self.kp * Ep
        if self.dkind == "fresh":
            D = self.kappa * (self.kd / 8.0) * ABE * r_new
        elif self.dkind == "held":
            D = -self.kappa * self.kd * xh
        else:
            D = -(self.kd / 8.0) * self.dop_k * 10.0 * (thh - thhq)
        S = (I_new if self.ki else 0 * I_new) + P + D
        o_new = (OA / 1024.0) * e("o") + (OB / 1024.0) * FADE * S
        y = (e("o") + o_new) / 32.0
        u = gain * FWD * y
        rows = {}
        rows["r"] = r_new
        rows["I"] = I_new if self.ki else 0 * I_new
        rows["o"] = o_new
        rows["thhp"] = thh
        # slot-4 refresh after the lane
        if self.ea > 0:
            src_t = e("bt", self.ea - 1)
            src_x = e("br", self.ea - 1)
        else:
            src_t, src_x = th, r_new
        if slot and self.ea >= 0:
            rows["thhq"] = thh
            rows["thh"] = src_t
            rows["xh"] = src_x
        else:
            rows["thhq"] = thhq
            rows["thh"] = thh
            rows["xh"] = xh
        if self.ea > 0:
            for i in range(self.ea):
                rows[("bt", i)] = th if i == 0 else e("bt", i - 1)
                rows[("br", i)] = r_new if i == 0 else e("br", i - 1)
        if self.d > 0:
            u_app = e("ub", self.d - 1)
            for i in range(self.d):
                rows[("ub", i)] = u if i == 0 else e("ub", i - 1)
        else:
            u_app = u
            rows[("ub", 0)] = 0 * u
        for i in range(self.npl):
            rows[("xp", i)] = self.Ad[i] @ xp + self.Bd[i, 0] * u_app
        for k, v in rows.items():
            if isinstance(k, tuple):
                M[ix[k[0]] + k[1]] = v
            else:
                M[ix[k]] = v
        return M

    def monodromy(self, gain=1.0):
        Phi = np.eye(self.N)
        for p in range(10):
            Phi = self._phase(p, gain) @ Phi
        return Phi

    def rho_pole(self, gain=1.0):
        lam = np.linalg.eigvals(self.monodromy(gain))
        rho = float(np.max(np.abs(lam)))
        best = (float("nan"), 9.0)
        for l in lam:
            if abs(l) < 1e-9:
                continue
            s = np.log(complex(l)) / 0.01
            f = abs(s.imag) / (2 * math.pi)
            z = -s.real / abs(s) if abs(s) > 0 else 1.0
            if 0.2 < f < 49.9 and z < best[1]:
                best = (f, z)
        return rho, best[0], best[1]


def exact_for(cand_kind, name, v, G, kp=112, ki=56, kd=34, dop_k=64.0):
    pl, d, ea, jbk, kappa = X.plant_ext(name, v)
    return Exact(cand_kind, pl, d, ea, G, kp, ki, kd, kappa=kappa, dop_k=dop_k)


def exact_gm(ex, hi=64.0):
    """smallest gain multiplier k > 1 with rho >= 1, in dB (inf if stable to hi)."""
    if ex.rho_pole(1.0)[0] >= 1:
        return -float("inf")
    lo, h = 1.0, None
    for k in (1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 16.0, 32.0, hi):
        if ex.rho_pole(k)[0] >= 1:
            h = k
            break
        lo = k
    if h is None:
        return float("inf")
    while h / lo > 1.01:
        m = math.sqrt(lo * h)
        if ex.rho_pole(m)[0] < 1:
            lo = m
        else:
            h = m
    return 20 * math.log10(lo)
