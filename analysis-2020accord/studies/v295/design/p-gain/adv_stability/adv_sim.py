# -*- coding: utf-8 -*-
"""adv_sim.py -- MY OWN nonlinear closed-loop simulator for the adversarial pass:
   planner demand (synthetic scenario) -> the fork (the harness's ForkPort, proven bit-identical to the REAL
   LatControlTorque @20d24ab79 by the harness's gate H3b; used here only as 'the fork') -> Honda limiter (my code) ->
   22 ms pipe -> MY vectorised byte-exact lane (demand chain + fb lag + P + clamps + output lag + gain + lane clamp;
   spot-checked vs adv_lib.MyLane which is tick-exact vs the golden model) -> MY plant (Karnopp stick-slip,
   k*sat*tanh spring, viscous b, delay tau, 3 ms rate former, x noise; semi-implicit Euler at 1 kHz) -> angle (0.1 deg)
   back to the fork.  Everything per lane: cells, plant params, speed, scenario.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
if HARN not in sys.path:
    sys.path.insert(0, HARN)
import adv_lib as A  # noqa: E402


class VLane:
    """vectorised version of adv_lib.MyLane (P-only lanes: Ki = Kd = 0 asserted), per-lane Kp table and fb/clamp cells."""

    def __init__(self, cells_list):
        self.B = len(cells_list)
        g = lambda k: np.array([c[k] for c in cells_list], np.int64)  # noqa: E731
        for c in cells_list:
            assert c["ki"] == 0 and (c["d_clamp"] == 0 or all(y == 0 for y in c["kd_y"])) and c["fb_op"] == "diff"
        self.fa, self.fb, self.fcl = g("fb_a"), g("fb_b"), g("fb_clamp")
        self.esh, self.pcl, self.scl = g("e_shift"), g("p_clamp"), g("sum_clamp")
        self.la, self.lb, self.gain, self.tcl, self.icl = g("lag_a"), g("lag_b"), g("gain"), g("t_clamp"), g("idx_clamp")
        self.kp_t = np.stack([A.table(c["kp_x"], c["kp_y"]) for c in cells_list])
        self.map_t = np.stack([A.table(c["map_x"], c["map_y"]) for c in cells_list])
        self.rows = np.arange(self.B)
        self.s = np.zeros(self.B, np.int64)
        self.o = np.zeros(self.B, np.int64)
        self.restart = np.zeros(self.B, bool)

    def demand(self, wire):
        wire = np.asarray(wire, np.int64)
        S = np.clip(-4 * wire, -0x4000, 0x4000)
        prod = (65025 * S) >> 16
        v = np.clip(prod >> 6, -self.icl, self.icl)
        idx = np.abs(v)
        sgn = np.where(v < 0, -1, 1)
        return idx, -sgn * self.map_t[self.rows, idx]

    def tick(self, x, sp, idx, m=254):
        x = np.asarray(x, np.int64)
        bail = np.abs(x) > 12000
        s_old = np.where(self.restart, 0, self.s)
        s_new = ((self.fa * s_old) >> 10) + ((self.fb * np.where(bail, 0, x)) >> 10)
        r26 = np.clip(s_new - s_old, -self.fcl, self.fcl)
        self.s = np.where(bail, self.s, s_new)
        self.restart = bail
        r26 = np.where(bail, 0, r26)
        E = (sp << self.esh) - r26
        P = np.clip((E * self.kp_t[self.rows, idx]) >> 8, -self.pcl, self.pcl)
        S = np.clip((m * P) >> 8, -self.scl, self.scl)
        S = np.where(bail, 0, S)
        o2 = ((self.la * self.o) >> 10) + ((S * self.lb) >> 10)
        y = (self.o + o2) >> 5
        self.o = o2
        return np.clip((y * self.gain) >> 15, -self.tcl, self.tcl), P, r26


class VPlant:
    """my Karnopp plant, batch, 1 kHz semi-implicit Euler.  u = -T(tau) + d.  J th'' = u - b om - k sat tanh(th/sat) - F."""

    def __init__(self, J, b, k, sat, Fc, Fs, tau, th0, om0=0.0, w=3, x_noise=1.93, seed=0):
        self.J, self.b, self.k, self.sat, self.Fc, self.Fs = (np.asarray(a, float) for a in (J, b, k, sat, Fc, Fs))
        self.B = len(self.J)
        self.tau = int(tau)
        self.th = np.asarray(th0, float) * np.ones(self.B)
        self.om = np.asarray(om0, float) * np.ones(self.B)
        self.w = w
        self.hist = np.repeat(self.th[:, None], w, axis=1)
        self.hp = 0
        self.Tbuf = np.zeros((self.B, self.tau + 1))
        self.tp = 0
        self.xn = x_noise
        self.rng = np.random.default_rng(seed)
        self.stuck_run = np.zeros(self.B, int)
        self.breakaways = np.zeros(self.B, int)

    def sense(self):
        xr = 8.0 * (self.th - self.hist[:, self.hp]) / (self.w * 1e-3)
        if self.xn:
            xr = xr + self.rng.normal(0.0, self.xn, self.B)
        return np.clip(np.round(xr), -12000, 12000).astype(np.int64)

    def step(self, T, d):
        self.Tbuf[:, self.tp] = T
        self.tp = (self.tp + 1) % (self.tau + 1)
        u = -self.Tbuf[:, self.tp] + d
        fnet = u - self.k * self.sat * np.tanh(self.th / self.sat) - self.b * self.om
        was_stuck = self.om == 0.0
        stuck = was_stuck & (np.abs(fnet) <= self.Fs)
        fdir = np.where(self.om != 0.0, np.sign(self.om), np.sign(fnet))
        om_new = self.om + np.where(stuck, 0.0, (fnet - self.Fc * fdir) / self.J) * 1e-3
        om_new[stuck | ((self.om != 0.0) & (np.sign(om_new) != np.sign(self.om)))] = 0.0
        # breakaway = leaving a stick that lasted >= 20 ms
        self.breakaways += (om_new != 0.0) & (self.stuck_run >= 20)
        self.stuck_run = np.where(om_new == 0.0, self.stuck_run + 1, 0)
        self.hist[:, self.hp] = self.th
        self.hp = (self.hp + 1) % self.w
        self.om = om_new
        self.th = self.th + self.om * 1e-3


def honda_limiter(cmd, last, delta=0.03):
    lim = np.clip(cmd, last - delta, last + delta)
    can = np.trunc(np.clip(-lim * 4096.0, -4096, 4096)).astype(np.int64)
    return lim, can


def run(cells_list, plant_par, v, des_curv, dist, secs, toggles, pipe_ms=22, x_noise=1.93, seed=0, th0=None,
        i0=None, rec_1k=False):
    """cells_list, plant_par (dict of arrays J b k sat Fc Fs, tau int), v (B,), des_curv (B, n_frames), dist (B, n_ticks)
    torque disturbance (+left, T counts).  Returns 100 Hz records."""
    import v295_harness as H
    B = len(cells_list)
    NF = int(secs * 100)
    lane = VLane(cells_list)
    th0 = np.zeros(B) if th0 is None else th0
    pl = VPlant(plant_par["J"], plant_par["b"], plant_par["k"], plant_par["sat"], plant_par["Fc"], plant_par["Fs"],
                plant_par["tau"], th0, x_noise=x_noise, seed=seed)
    fork = H.ForkPort(B, toggles)
    if i0 is not None:
        fork.i = np.asarray(i0, float).copy()
    rec = {k: np.zeros((B, NF)) for k in ("ang", "om", "cmd", "T", "idx", "slew", "err", "i", "P")}
    last = np.zeros(B)
    steer_lim = np.zeros(B, bool)
    q = {}
    wire = np.zeros(B, np.int64)
    idx, sp = lane.demand(wire)
    lat_delay = 0.426
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            ang_q = np.round(pl.th / 0.1) * 0.1
            r = fork.step(np.ones(B, bool), v, ang_q, np.zeros(B, bool), 0.0, 0.0, des_curv[:, k], lat_delay, 0.0,
                          steer_lim)
            lim, can = honda_limiter(r["torque"], last)
            rec["slew"][:, k] = np.abs(lim - r["torque"]) > 1e-12
            steer_lim = np.abs(lim - r["torque"]) > 1e-2          # controlsd: |CC torque - CO torque| > 1e-2 (next frame)
            last = lim
            q[n + pipe_ms] = can
            rec["ang"][:, k] = ang_q
            rec["om"][:, k] = pl.om
            rec["err"][:, k] = r["error"]
            rec["i"][:, k] = r["i"]
        if n in q:
            wire = q.pop(n)
            idx, sp = lane.demand(wire)
        x = pl.sense()
        T, P, r26 = lane.tick(-x, sp, idx)
        pl.step(T.astype(float), dist[:, n])
        if n % 10 == 0:
            rec["cmd"][:, k] = wire
            rec["T"][:, k] = T
            rec["idx"][:, k] = idx
            rec["P"][:, k] = P
    rec["breakaways"] = pl.breakaways.copy()
    return rec
