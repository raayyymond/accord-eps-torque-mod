# -*- coding: utf-8 -*-
"""rj_lin.py -- lens robust-joint: the FAST LINEAR SCORER (stage 1 of the search).

Built from the shared harness's own primitives (v295_harness: lane transfer, plant FRF, rate former, the outer-loop
formula, margins, closed_loop_modes), restructured so every plant FRF is computed ONCE and a candidate costs ~0.1-0.3 s.
Every function below is checked against the harness's own function on V294 and a candidate (rj_lin.selftest()).

Differences from the harness functions, each deliberate:
  * the lane transfer takes an idx (Kp/Kd read at that demand index), so a Kp SCHEDULE is scored where it acts;
  * the feed-forward transfer uses the INCREMENTAL slope of the static surface Kp(i)*(map(i) << e)/256 at idx_op (for a
    flat Kp this is exactly the harness's ff_tf; for a schedule it is the slope the outer loop actually sees);
  * HF and inner-stability checks use the MAX Kp over idx (worst case); tracking/outer checks use idx 10 and 40.
Linear = friction off, floors off, clamps off: DIRECTIONS and MARGINS, not magnitudes where the harness says NOT FIT.
ANALYSIS ONLY."""
import math
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import v295_harness as H  # noqa: E402

DT = 1e-3
F_IN = np.logspace(-1, np.log10(45.0), 700)
F_OUT = np.logspace(-2, np.log10(20.0), 600)
F_HF = np.linspace(10.0, 25.0, 31)
SPEEDS = (3.1, 5.0, 8.0, 12.0, 17.0, 26.9)
M_INNER = ("nominal", "J_lo", "J_hi", "J_hi2", "J_0.3", "b_lo", "b_hi", "tau0", "tau6", "tau9", "light_b", "ms_free",
           "nominal_kappa")
M_OUTER = ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "tau6", "light_b", "ms_free")
M_STRESS = (("mode13", (8, 20)), ("mode20", (14, 30)), ("mode20_lo", (14, 30)))
V_STRESS = (5.0, 12.0, 25.0)
DC294 = 2 * 507 / ((1024 - 992) * 32.0)       # 0.990234375, the output-lag DC as built


def lag_pair(f_hz, dc=DC294):
    """output-lag cells for a corner f (Hz) with the DC held at <= V294's (so the rail cannot rise)."""
    a = int(round(1024 * math.exp(-2 * math.pi * f_hz * DT)))
    b = int(math.floor(dc * 16 * (1024 - a)))
    return a, b


def fb_a_for(f_hz):
    return int(round(1024 * math.exp(-2 * math.pi * f_hz * DT)))


def pole_hz(a):
    return -math.log(a / 1024.0) / (2 * math.pi * DT)


# ------------------------------------------------------------------------------------------------------ lane transfers
def _tab(X, Y):
    return H.lerp_table(X, Y)


class LaneTF:
    """linear transfers of one Cells (tables cached)."""

    def __init__(self, c):
        self.c = c
        self.kp = _tab(c.kp_x, c.kp_y)
        self.kd = _tab(c.kd_x, c.kd_y) if c.d_clamp else np.zeros(256, np.int64)
        self.mp = _tab(c.map_x, c.map_y)

    def ct(self, f, idx, m=254, kind="T", kp=None):
        """x (lane operand counts) -> T (tap sign) or -> P+D before the taper; Kp/Kd at idx (or kp given)."""
        c = self.c
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        zi = 1.0 / z
        a, b = c.fb_a / 1024.0, c.fb_b / 1024.0
        if c.fb_clamp == 0:
            R = 0.0 * z
        else:
            R = b * ((1 - zi) if c.fb_op == "diff" else (1 + zi)) / (1 - a * zi)
        E = -R
        kpv = float(self.kp[idx]) if kp is None else float(kp)
        kdv = float(self.kd[idx])
        PID = kpv / 256.0 * E + kdv / 8.0 * (1 - zi) * E
        if kind == "P":
            return PID
        S = m / 256.0 * PID
        la, lb = c.lag_a / 1024.0, c.lag_b / 1024.0
        y = lb * (1 + zi) / (32.0 * (1 - la * zi)) * S
        return y * c.gain / 32768.0

    def ff(self, f, idx_op, m=254):
        """wire count -> T (tap sign), incremental at idx_op (the static surface's local slope + the Kd kick)."""
        c = self.c
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        zi = 1.0 / z
        i0, i1 = max(idx_op - 8, 0), min(idx_op + 8, c.idx_clamp)
        Ppre = self.kp[:c.idx_clamp + 1].astype(float) * (self.mp[:c.idx_clamp + 1].astype(float) * 2 ** c.e_shift) / 256.0
        slopeP = (Ppre[i1] - Ppre[i0]) / float(i1 - i0) / H.WIRE_PER_IDX          # P counts per wire
        mslope = (self.mp[i1] - self.mp[i0]) / float(i1 - i0) / H.WIRE_PER_IDX     # sp counts per wire
        PID = slopeP + float(self.kd[idx_op]) / 8.0 * (1 - zi) * (2 ** c.e_shift) * mslope
        S = m / 256.0 * PID
        y = (c.lag_b / 1024.0) * (1 + zi) / (32.0 * (1 - (c.lag_a / 1024.0) * zi)) * S
        return y * c.gain / 32768.0

    def kp_max(self):
        return int(self.kp[:self.c.idx_clamp + 1].max())


# ------------------------------------------------------------------------------------------------------ the context
class Ctx:
    """plant FRFs precomputed on the inner and outer grids for every (member, speed); the fork constants."""

    def __init__(self):
        self.fam = H.family()
        d = H.route()
        tg = d["toggles"]
        self.kp_f = float(tg["steerKp"][1][0])
        self.ki_f = float(tg["accord_torque_ki"])
        self.laf = float(tg["latAccelFactor"])
        self.fric = float(np.float32(tg["friction"]))
        vm = H._vm_consts()
        self.vm = vm
        self.P_in, self.P_out, self.p = {}, {}, {}
        for nm in set(M_INNER) | set(M_OUTER):
            for v in SPEEDS:
                p = self.fam[nm].at(v)
                self.p[(nm, v)] = p
                self.P_in[(nm, v)] = H.plant_theta_frf(p, F_IN)
                self.P_out[(nm, v)] = H.plant_theta_frf(p, F_OUT)
        self.RFz = {}
        for F, key in ((F_IN, "in"), (F_OUT, "out")):
            z = np.exp(2j * np.pi * F * DT)
            w = 3
            self.RFz[key] = (1 - z ** (-w)) / (w * DT) * np.exp(-1j * np.pi * F * DT) * np.sinc(F * DT)
        s = 2j * np.pi * F_OUT
        self.zoh100 = np.exp(-1j * np.pi * F_OUT * 0.01) * np.sinc(F_OUT * 0.01)
        self.pipe = np.exp(-s * 22e-3)
        z100 = np.exp(s * 0.01)
        self.I_f = self.ki_f * 0.01 / (1 - 1 / z100)
        self.s_out = s
        psd = np.load(os.path.join(HERE, "rj1_cmd_psd.npz"))
        self.W = np.interp(F_OUT, psd["f"], psd["P"])

    def kla(self, v):
        cf = (1. - self.vm["chi"]) / (1. - self.vm["sf"] * v ** 2) / self.vm["l"]
        return cf / (16.88 * (16.84 / 16.88)) * v ** 2 * np.pi / 180.0

    def Cf(self, v, relay):
        lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
        return (self.kp_f + self.I_f + (self.fric * self.laf / 0.30 if relay else 0.0)) * (1 + lsf / self.kp_f)


def inner_L(ctx, lt, nm, v, grid="in", idx=0, kp=None):
    P = ctx.P_in[(nm, v)] if grid == "in" else ctx.P_out[(nm, v)]
    F = F_IN if grid == "in" else F_OUT
    return -8.0 * lt.ct(F, idx, kp=kp) * ctx.RFz[grid] * P


def outer_parts(ctx, lt, nm, v, idx_op, relay=True):
    """(L_in, G, L_o) on F_OUT: G = the fork FF path (plan -> act), L_o = the outer return ratio."""
    Lin = inner_L(ctx, lt, nm, v, "out", idx=idx_op)
    Pcl = ctx.P_out[(nm, v)] / (1 + Lin)
    G = ctx.kla(v) * Pcl * lt.ff(F_OUT, idx_op) * ctx.zoh100 * ctx.pipe * 4096.0 / ctx.laf
    Lo = G * ctx.Cf(v, relay)
    return Lin, G, Lo


def _band(F, X, lo, hi):
    m = (F >= lo) & (F <= hi)
    return X[m]


def evaluate(ctx, c, base_cache=None, idx_ops=(10, 40), fast=False):
    """the linear score of one candidate.  Returns a flat dict of metrics (worst over members where stated)."""
    lt = LaneTF(c)
    out = {}
    kpm = lt.kp_max()
    # ---------------- HF: |P/x| and |T/x| over 10-25 Hz at the max Kp (vs V294 at its Kp 960)
    Pp = np.abs(lt.ct(F_HF, 0, kind="P", kp=kpm))
    Tt = np.abs(lt.ct(F_HF, 0, kind="T", kp=kpm))
    out["P20"] = float(np.abs(lt.ct(np.array([20.0]), 0, kind="P", kp=kpm))[0])
    out["Pmax_10_25"] = float(Pp.max())
    out["Tmax_10_25"] = float(Tt.max())
    if base_cache is not None:
        out["HF_P_ratio"] = float(np.max(Pp / base_cache["Pp"]))
        out["HF_T_ratio"] = float(np.max(Tt / base_cache["Tt"]))
    # ---------------- inner loop, worst over members / speeds (max Kp), incl. delay x1.5
    Ms_w, GM_w, L13_w, L38_w = 0.0, np.inf, 0.0, 0.0
    for nm in M_INNER:
        for v in SPEEDS:
            L = inner_L(ctx, lt, nm, v, "in", kp=kpm)
            mg = H.margins(F_IN, L)
            Ms_w = max(Ms_w, mg["Ms"])
            GM_w = min(GM_w, mg["GM_min"])
            L13_w = max(L13_w, float(np.mean(np.abs(_band(F_IN, L, 1, 3)))))
            L38_w = max(L38_w, float(np.mean(np.abs(_band(F_IN, L, 3, 8)))))
    out.update(in_Ms=Ms_w, in_GM=GM_w, in_L13=L13_w, in_L38=L38_w)
    # delay x1.5 on the nominal / light_b / J_hi2 (tau 2 -> 3 is the family's own; tau9 member covers 6 -> 9)
    # ---------------- stress modes (closed-loop exact 1 kHz poles), max Kp
    cfl = c.replace(kp_y=(kpm,) * 5, name=c.name + "_kpmax")
    zmin_rel, zmin_abs = np.inf, np.inf
    st = {}
    if not fast:
        for nm, band in M_STRESS:
            for v in V_STRESS:
                p = ctx.fam[nm].at(v)
                (fz, zz), rho = H.stress_damping(cfl, p, band)
                ref = base_cache["stress"][(nm, v)] if base_cache is not None else None
                st[(nm, v)] = (fz, zz, rho)
                if ref is not None:
                    zref = min(ref["zeta_V294"], ref["zeta_open"])
                    zmin_rel = min(zmin_rel, zz / zref)
                zmin_abs = min(zmin_abs, zz)
    out["stress_zeta_min"] = zmin_abs
    out["stress_zeta_rel"] = zmin_rel
    out["stress"] = st
    # ---------------- outer loop: per (member, v, relay, idx) margins; jerk; loose; tracking
    outer = {}
    for nm in M_OUTER:
        for v in SPEEDS:
            for idx in idx_ops:
                for relay in (True, False):
                    Lin, G, Lo = outer_parts(ctx, lt, nm, v, idx, relay)
                    mg = H.margins(F_OUT, Lo)
                    S2 = 1.0 / ((1 + Lin) * (1 + Lo))
                    Tt_ = (G + Lo) / (1 + Lo)
                    mlow = (F_OUT >= 0.1) & (F_OUT <= 0.3)
                    mj = (F_OUT >= 1.6) & (F_OUT <= 3.0)
                    outer[(nm, v, idx, relay)] = dict(
                        GM=mg["GM_min"], Ms=mg["Ms"], fMs=mg["f_Ms"],
                        jerk=float(np.sqrt(np.mean(np.abs(S2[mj]) ** 2))),
                        track=float(np.mean(np.abs(Tt_[mlow]))), ffdel=float(np.mean(np.abs(G[mlow]))),
                        track05=float(np.abs(Tt_[np.argmin(np.abs(F_OUT - 0.5))])))
    out["outer"] = outer
    # ---------------- M_TRACK closed form: actuator branch alpha/cmd with the inner loop closed, per member at 8/12/17/26.9
    tr = {}
    for nm in ("nominal", "J_lo", "J_hi", "b_lo", "light_b"):
        for v in (5.0, 8.0, 12.0, 17.0, 26.9):
            Lin = inner_L(ctx, lt, nm, v, "out", idx=30)
            A = ctx.s_out ** 2 * ctx.P_out[(nm, v)] * lt.ff(F_OUT, 30) * ctx.zoh100 / (1 + Lin)
            m = (F_OUT >= 1.0) & (F_OUT <= 8.0)
            w = ctx.W[m]
            a = A[m]
            R2 = float(np.abs(np.sum(a * w)) ** 2 / (np.sum(np.abs(a) ** 2 * w) * np.sum(w)))
            lf = np.log(F_OUT[m])
            slope = float(np.polyfit(lf, np.log(np.abs(a)), 1)[0])
            ph = np.degrees(np.angle(A))
            tr[(nm, v)] = dict(R2=R2, slope=slope, G2=float(np.abs(A[np.argmin(np.abs(F_OUT - 2.0))])),
                               ph1=float(ph[np.argmin(np.abs(F_OUT - 1.0))]), ph3=float(ph[np.argmin(np.abs(F_OUT - 3.0))]),
                               ph8=float(ph[np.argmin(np.abs(F_OUT - 8.0))]))
    out["track_cf"] = tr
    return out


def base_cache(ctx, base):
    lt = LaneTF(base)
    bc = dict(Pp=np.abs(lt.ct(F_HF, 0, kind="P", kp=lt.kp_max())), Tt=np.abs(lt.ct(F_HF, 0, kind="T", kp=lt.kp_max())))
    st = {}
    for nm, band in M_STRESS:
        for v in V_STRESS:
            p = ctx.fam[nm].at(v)
            (fb_, zb), _ = H.stress_damping(base, p, band)
            (fo, zo), _ = H.stress_damping(base.replace(fb_clamp=0), p, band)
            st[(nm, v)] = dict(zeta_V294=zb, zeta_open=zo)
    bc["stress"] = st
    return bc


def selftest():
    """second method: my vectorised transfers == the harness's own functions on V294 and a candidate."""
    ctx = Ctx()
    base = H.Cells.v294()
    cand = base.replace(fb_b=1200, fb_a=1005, lag_a=980, lag_b=697, kp_y=(1100,) * 5, name="t")
    worst = 0.0
    for c in (base, cand):
        lt = LaneTF(c)
        worst = max(worst, float(np.max(np.abs(lt.ct(F_IN, 0) - H.lane_ctf(c, F_IN)))))
        worst = max(worst, float(np.max(np.abs(lt.ct(F_IN, 0, kind="P") - H.lane_ctf(c, F_IN, kind="P")))))
        for nm, v in (("nominal", 12.0), ("light_b", 26.9), ("J_hi", 3.1)):
            p = ctx.fam[nm].at(v)
            L1 = inner_L(ctx, lt, nm, v, "in")
            L2 = H.loop_frf(c, p, F_IN)
            worst = max(worst, float(np.max(np.abs(L1 - L2) / np.maximum(np.abs(L2), 1e-12))))
            for relay in (True, False):
                _, _, Lo1 = outer_parts(ctx, lt, nm, v, 60, relay)
                Lo2 = H.outer_frf(c, p, v, F_OUT, relay=relay, idx_op=60)
                worst = max(worst, float(np.max(np.abs(Lo1 - Lo2) / np.maximum(np.abs(Lo2), 1e-12))))
            ff1 = lt.ff(F_OUT, 60)
            ff2 = H.ff_tf(c, F_OUT, 60)
            worst = max(worst, float(np.max(np.abs(ff1 - ff2) / np.abs(ff2))))
    print("rj_lin selftest: worst relative deviation from the harness functions = %.3e -> %s"
          % (worst, "PASS" if worst < 1e-9 else "FAIL"))
    return worst


if __name__ == "__main__":
    selftest()
