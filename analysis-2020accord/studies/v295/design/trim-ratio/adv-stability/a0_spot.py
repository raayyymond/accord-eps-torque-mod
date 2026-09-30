# -*- coding: utf-8 -*-
"""a0_spot.py -- reproduction gate R1-R4 with MY code, plus the harness spot-check (lane tick vs golden model, one
retrodiction row).  Output: a0_spot_out.txt"""
import sys
import os
import time
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402

out = open(os.path.join(HERE, "a0_spot_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


V294 = A.read_cells("V294")
V282 = A.read_cells("V282")
V293 = A.read_cells("V293")
B964 = A.with_b(V294, 964)
P("V294 sha", V294["sha"])
for c in (V294, V282, V293):
    P(c["name"], {k: c[k] for k in ("fb_a", "fb_b", "fb_clamp", "fb_op", "e_shift", "kp_y", "kd_y", "d_clamp", "ki", "p_clamp",
                                    "sum_clamp", "lag_a", "lag_b", "gain", "t_clamp")})

# ---------------- golden model vs my IntLane, random ticks
import eps_lkas_chain_model as M  # noqa: E402


def cal_of(c):
    return replace(M.Calibration(), fb_lag_a=c["fb_a"], fb_lag_b=c["fb_b"], fb_clamp=c["fb_clamp"], fb_op=c["fb_op"],
                   e_shift=c["e_shift"], kp_x=tuple(c["kp_x"]), kp_y=tuple(c["kp_y"]), kd_x=tuple(c["kd_x"]),
                   kd_y=tuple(c["kd_y"]), pid_d_clamp=c["d_clamp"], pid_ki=c["ki"], pid_err_deadband=c["deadband"],
                   pid_i_clamp=c["i_clamp"], pid_p_clamp=c["p_clamp"], sum_clamp=c["sum_clamp"], out_lag_a=c["lag_a"],
                   out_lag_b=c["lag_b"], lkas_forward_gain=c["gain"], out_clamp=c["t_clamp"],
                   assist_map_x=tuple(c["map_x"]), assist_map_y=tuple(c["map_y"]), sum_notch=None)


rng = np.random.default_rng(1)
for c in (V294, B964, V282, A.with_b(V294, 2301, "b2301")):
    cal = cal_of(c)
    st = M.EpsState()
    L = A.IntLane([c])
    mism = 0
    n = 20000
    x = np.cumsum(rng.normal(0, 40, n)).astype(int)
    x = np.clip(x, -11000, 11000)
    msk = rng.random(n) < 0.02
    x[msk] = rng.integers(-12000, 12001, int(msk.sum()))
    idx = np.clip(np.abs(np.cumsum(rng.integers(-3, 4, n))), 0, 240)
    sgn = np.where(rng.random(n) < 0.5, 1, -1)
    for i in range(n):
        k = int(idx[i])
        sp = int(sgn[i]) * A.lerp(c["map_x"], c["map_y"], k)
        fb = M.lkas_fb_lag(int(x[i]), st, cal)
        r = M.lkas_rate_pid_tick(sp, fb, k, st, cal, pol=1, taper=254)
        T = L.tick(int(x[i]), sp, k, 254)
        if int(T[0]) != r["T"] or int(L.last["r26"][0]) != fb:
            mism += 1
    P("golden vs IntLane", c["name"], "ticks", n, "mismatches", mism, "maxabs", L.maxabs)

# ---------------- R1 / R2 : |P/x| at 20 Hz, K_alpha, HF ratio (my FRF), and a time-domain sinusoid march (2nd method)
f = np.array([20.0])
for c in (V294, B964, V282):
    Px = A.ctrl_frf(c, f, part="P")[0]
    P("|P/x| @20 Hz", c["name"], "%.4f" % abs(Px), "phase(P/x_in) %.1f" % np.degrees(np.angle(-Px)),
      "| T/x @20: %.4f  phase(T re -x_in) %.1f" % (abs(A.ctrl_frf(c, f)[0]), np.degrees(np.angle(-A.ctrl_frf(c, f)[0]))))
# K_alpha: low-frequency T per (deg/s^2): T/x_in ~ -K * j w as w -> 0 ; x_in = -8 om  -> T per om' = 8 * |T/x_in| / w
fl = np.array([0.01])
for c in (V294, B964):
    H = A.ctrl_frf(c, fl)[0]
    Ka = 8 * abs(H) / (2 * np.pi * 0.01)
    Hhf = np.array([abs(A.ctrl_frf(c, np.array([ff]))[0]) for ff in (10.0, 15.0, 20.0, 25.0)])
    P("K_alpha", c["name"], "%.4f T per deg/s^2" % Ka, "|T/x| 10/15/20/25 Hz", np.round(Hhf, 5))
r = np.array([abs(A.ctrl_frf(B964, np.array([ff]))[0]) / abs(A.ctrl_frf(V294, np.array([ff]))[0]) for ff in (1, 2, 5, 10, 20)])
P("HF ratio b964/V294 at 1/2/5/10/20 Hz", np.round(r, 4))
# time-domain: sinusoid x through IntLane at 20 Hz, amplitude 400, idx 60, sp 0
for c in (V294, B964):
    L = A.IntLane([c])
    n = 4000
    t = np.arange(n) * 1e-3
    xs = np.round(400 * np.sin(2 * np.pi * 20 * t)).astype(int)
    P_ = np.zeros(n)
    for i in range(n):
        L.tick(xs[i], 0, 60)
        P_[i] = L.last["P"][0]
    ss = slice(2000, 4000)
    Z = np.exp(-2j * np.pi * 20 * t[ss])
    amp = 2 * abs(np.mean(P_[ss] * Z)) / 400.0
    P("time-domain |P/x| @20 Hz", c["name"], "%.4f" % amp)
# ramp march for K_alpha (constant acceleration in x_in): x_in = -8*al*t, al = 200 deg/s^2
for c in (V294, B964):
    L = A.IntLane([c])
    n = 3000
    al = 200.0
    Ts = np.zeros(n)
    for i in range(n):
        xin = int(round(-8 * al * i * 1e-3))
        Ts[i] = L.tick(xin, 0, 60)[0]
    P("ramp march K_alpha", c["name"], "%.4f" % (np.mean(Ts[2000:3000]) / al), "(T per deg/s^2, sign + = opposes?)")

# ---------------- R4 : int32 margin a*s at |x| = 12000, restart pulse
for c in (V294, B964):
    s_ss = c["fb_b"] * 12000 / (1024 - c["fb_a"])
    P("int32 a*s margin", c["name"], "%.3f" % (2 ** 31 / (c["fb_a"] * s_ss)), "b_max %.1f" % (2 ** 31 * (1024 - c["fb_a"]) / (12000 * c["fb_a"])))
    pk = []
    for rate in (10, 30, 100, 300):
        L = A.IntLane([c])
        # wheel held (x = 0) after a restart from s = 0 with the wheel moving at `rate`: firmware restart = s from 0,
        # x = 8*rate -> r26 = s_new - 0 = b x >> 10 in one tick (the restart pulse), then hold x constant
        Tm = []
        for i in range(1500):
            T = L.tick(int(8 * rate), 0, 60)
            Tm.append(abs(int(T[0])))
        pk.append(max(Tm))
    P("restart pulse (x const from s=0) peaks 10/30/100/300", c["name"], pk)

# ---------------- harness spot check: its Lane vs golden, its lane_ctf vs mine
HP = os.path.join(A.KIT, "analysis-2020accord", "studies", "v295", "design", "harness")
sys.path.insert(0, HP)
import v295_harness as H  # noqa: E402
hc = H.Cells.v294()
hb = hc.replace(fb_b=964, name="b964")
HL = H.Lane([hc, hb], guard=True)
myL = A.IntLane([V294, B964])
mism = 0
x = np.clip(np.cumsum(rng.normal(0, 60, 20000)).astype(int), -11000, 11000)
for i in range(20000):
    k = int(i // 97 % 200)
    sp = A.lerp(V294["map_x"], V294["map_y"], k) * (1 if (i // 1000) % 2 else -1)
    t1, _ = HL.tick(np.array([x[i], x[i]]), np.array([sp, sp]), np.array([k, k]), np.array([254, 254]))
    t2 = myL.tick(x[i], sp, k, 254)
    mism += int(np.any(t1 != t2))
P("harness Lane vs my IntLane (V294, b964), 20000 ticks, mismatches", mism)
ff = np.array([1.0, 2.0, 5.0, 13.0, 20.0, 25.0])
for c, h in ((V294, hc), (B964, hb)):
    mine = A.ctrl_frf(c, ff)
    hv = H.lane_ctf(h, ff, kind="T")
    P("lane FRF mine vs harness", c["name"], np.round(np.abs(mine), 5), np.round(np.abs(hv), 5),
      "phase diff deg", np.round(np.degrees(np.angle(mine / hv)), 2))
out.close()
