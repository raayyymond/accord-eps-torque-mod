# -*- coding: utf-8 -*-
"""as1_repro.py -- R1..R4: my own lane vs the golden model; K_alpha, T/omega, |P/x|, restart pulse, int32 margin."""
import os, sys
from dataclasses import replace
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "model"))
import advlib as A

c294 = A.read_cells("V294")
c282 = A.read_cells("V282")
cA = dict(c294); cA["b"] = 1106
print("V294 cells:", {k: c294[k] for k in ("a", "b", "C", "op", "sh", "kpY", "kdY", "dcl", "ki", "pcl", "scl", "tcl", "la", "lb", "gain")})
print("V294 map Y:", c294["mapY"], "X:", c294["mapX"])
print("V282 cells:", {k: c282[k] for k in ("a", "b", "C", "op", "sh", "kpY", "kdY", "dcl", "ki", "la", "lb", "gain")})

# ---------------- R1: my lane == golden model, V294 and A, random ticks
import eps_lkas_chain_model as M
def gcal(c):
    base = M.Calibration()
    return replace(base, fb_clamp=c["C"], fb_lag_a=c["a"], fb_lag_b=c["b"], kp_x=tuple(c["kpX"]), kp_y=tuple(c["kpY"]),
                   kd_x=tuple(c["kdX"]), kd_y=tuple(c["kdY"]), pid_d_clamp=c["dcl"], pid_p_clamp=c["pcl"],
                   sum_clamp=c["scl"], out_clamp=c["tcl"], out_lag_a=c["la"], out_lag_b=c["lb"], lkas_forward_gain=c["gain"],
                   pid_ki=c["ki"], assist_map_x=tuple(c["mapX"]), assist_map_y=tuple(c["mapY"]), e_shift=c["sh"], fb_op=c["op"])
tot = 0
for tag, c in (("V294", c294), ("A", cA)):
    cal = gcal(c)
    rng = np.random.default_rng(11 if tag == "V294" else 12)
    B, N = 4, 6000
    L = A.MyLane(c, B)
    sts = [M.EpsState() for _ in range(B)]
    idx = rng.integers(0, 241, (B, N // 10))
    sgn = rng.choice([-1, 1], (B, N // 10))
    x = np.cumsum(rng.integers(-60, 61, (B, N)), axis=1).clip(-12000, 12000)
    mism = 0
    for n in range(N):
        fr = n // 10
        sp = sgn[:, fr] * L.mapLUT[idx[:, fr]]
        T, r26, P = L.tick(x[:, n], sp, idx[:, fr])
        for bi in range(B):
            fb = M.lkas_fb_lag(int(x[bi, n]), sts[bi], cal)
            r = M.lkas_rate_pid_tick(int(sp[bi]), fb, int(idx[bi, fr]), sts[bi], cal, pol=1, taper=254)
            mism += int(r["T"] != T[bi]) + int(fb != r26[bi])
    tot += B * N
    print("R1 %-5s my lane vs golden: %d mismatches (T and r26) over %d ticks  %s" % (tag, mism, B * N, "PASS" if mism == 0 else "FAIL"))

# harness Lane spot check: one tick sequence
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import v295_harness as H
hb = H.Cells.v294(); hA = hb.replace(fb_b=1106, name="A")
HL = H.Lane([hb, hA], guard=True)
ML = [A.MyLane(c294, 1), A.MyLane(cA, 1)]
rng = np.random.default_rng(5)
mm = 0
for n in range(3000):
    wire = int(rng.integers(-3000, 3000)) if n % 10 == 0 else wire
    idx_, sp_, m_ = HL.demand(np.array([wire, wire]))
    xx = int(rng.integers(-2000, 2000))
    out = HL.tick(np.array([xx, xx], np.int64), sp_, idx_, m_)
    Th = out[0] if isinstance(out, tuple) else out
    for j in range(2):
        Tm, _, _ = ML[j].tick(np.array([xx]), np.array([int(sp_[j])]), np.array([int(idx_[j])]), int(m_[j]))
        mm += int(int(Tm[0]) != int(np.asarray(Th)[j]))
print("R1 harness Lane vs my lane (V294, A), 3000 ticks, random x & wire: %d mismatches  %s" % (mm, "PASS" if mm == 0 else "FAIL"))

# ---------------- R2/R3: linear
f = np.array([0.5, 1.0, 2.0, 2.5, 3.0, 5.0, 10.0, 13.0, 15.0, 20.0, 25.0, 28.0, 30.0])
for tag, c in (("V294", c294), ("A", cA)):
    To = A.opposing_T_per_omega(c, f)
    print("R2 %-5s opposing T/omega:" % tag, "  ".join("%g Hz %.2f @%+.0f" % (ff, abs(t), np.degrees(np.angle(t))) for ff, t in zip(f, To)))
Ka = lambda c: (c["kpY"][0] / 256) * 8 * 1e-3 * c["b"] / (1024 - c["a"]) * (c["gain"] / 32768) * (254 / 256) * (2 * c["lb"] / ((1024 - c["la"]) * 32))
print("R2 K_alpha (closed form, T per deg/s^2): V294 %.4f  A %.4f  ratio %.4f" % (Ka(c294), Ka(cA), Ka(cA) / Ka(c294)))
# numeric K_alpha from the transfer: opposing T / (j w omega) at 0.05 Hz
fl = np.array([0.02])
for tag, c in (("V294", c294), ("A", cA)):
    To = A.opposing_T_per_omega(c, fl)
    print("R2 %-5s K_alpha numeric at 0.02 Hz: %.4f T/(deg/s^2)" % (tag, abs(To[0]) / (2 * np.pi * 0.02)))
for tag, c, kd in (("V294", c294, None), ("A", cA, None), ("V282", c282, c282["kdY"][0] if c282["dcl"] else None)):
    _, PD = A.lane_T_per_x(c, np.array([13.0, 16.0, 20.0, 25.0]), kd=kd)
    print("R3 %-5s |P/x| (P+D per x count) at 13/16/20/25 Hz: %s" % (tag, np.round(np.abs(PD), 3)))

# ---------------- R4: restart pulse and int32 margin, integer lane
def restart(c, dps, pre=3000, post=600):
    L = A.MyLane(c, 1)
    x = int(round(8 * dps))
    for n in range(pre):
        L.tick(np.array([x]), np.array([0]), np.array([0]))
    L.tick(np.array([x]), np.array([0]), np.array([0]), bail=np.array([True]))
    Ts = []
    for n in range(post):
        T, r26, P = L.tick(np.array([x]), np.array([0]), np.array([0]))
        Ts.append(int(T[0]))
    Ts = np.abs(np.array(Ts))
    return int(Ts.max()), int(np.sum(Ts > 50)), L.maxabs
for tag, c in (("V294", c294), ("A", cA), ("b1134", dict(c294, b=1134))):
    rr = [restart(c, d) for d in (10, 30, 100, 300)]
    print("R4 %-5s restart pulse peak |T| at 10/30/100/300 deg/s: %s ; ms > 50 T: %s" % (tag, [r[0] for r in rr], [r[1] for r in rr]))
for tag, c in (("V294", c294), ("A", cA)):
    s_max = c["b"] * 12000 / (1024 - c["a"])
    print("R4 %-5s int32: s at |x|=12000 steady %.0f ; a*s %.4g ; margin 2^31/(a*s) %.3f ; b*x %.4g margin %.1f ; b_max %.1f" % (
        tag, s_max, c["a"] * s_max, 2 ** 31 / (c["a"] * s_max), c["b"] * 12000, 2 ** 31 / (c["b"] * 12000),
        2 ** 31 * (1024 - c["a"]) / (12000 * c["a"])))
# a*s at the int level: march x = 12000 steady with my lane and read the tracked max
L = A.MyLane(cA, 1)
for n in range(3000):
    L.tick(np.array([12000]), np.array([0]), np.array([0]))
print("R4 A integer march at x=12000: max |a*s| %d margin %.3f ; max |b*x| %d" % (L.maxabs["a*s"], 2 ** 31 / L.maxabs["a*s"], L.maxabs["b*x"]))
