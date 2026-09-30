# -*- coding: utf-8 -*-
"""a3_outer.py -- (c) the OUTER loop with the UNCHANGED r1 fork law (Kp 0.9, Ki 0.3, LAF 14, friction 0.011, relay
threshold 0.30, low-speed factor), linearised by MY code around MY inner closed loop, V294 vs b964, per member x speed x
pipeline delay, relay off / on (small-signal slope) + the relay describing function (stability for every relay factor n
in [0, 1]).  VM constants: the fork's own VehicleModel (sf, chi, l) and steerRatio 16.84 (r71b toggles), used as data.
Output: a3_outer_out.txt"""
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a3_outer_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


V294 = A.read_cells("V294")
B964 = A.with_b(V294, 964)
fam = VP.family()
VM = dict(sf=-0.0006999872680281922, chi=0.0, l=2.8299999237060547)
SR = 16.84
KP, KI, LAF, FRIC, THR = 0.9, 0.3, 14.0, float(np.float32(0.011)), 0.30
WIRE_PER_IDX = 2 ** 22 / (4 * 65025)


def ff_path(c, f, idx=60, m=254):
    """wire count -> T (tap sign) : map slope, e_shift, Kp, taper, output lag, gain.  My code."""
    z = np.exp(2j * np.pi * f * A.DT)
    zi = 1 / z
    sp_per_idx = (A.lerp(c["map_x"], c["map_y"], idx + 8) - A.lerp(c["map_x"], c["map_y"], idx - 8)) / 16.0
    E = (2 ** c["e_shift"]) * sp_per_idx / WIRE_PER_IDX
    Pp = E * A.lerp(c["kp_x"], c["kp_y"], idx) / 256.0
    S = (m / 256.0) * Pp
    OL = (c["lag_b"] / 1024.0) * (1 + zi) / (32.0 * (1 - (c["lag_a"] / 1024.0) * zi))
    return S * OL * c["gain"] / 32768.0


def outer_L(p, c, v, f, relay=1.0, pipe_ms=22.0):
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    z = np.exp(s * A.DT)
    tau = p.tau_ms
    Lin = A.inner_L(p, c, f)
    G = A.plant_frf_th(p, f)
    Pin = G * z ** (-tau) / (1 + Lin)                      # theta (deg) per T_ff, magnitude chain (sign closes negative)
    z100 = np.exp(s * 0.01)
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
    Cf = (KP + KI * 0.01 / (1 - 1 / z100) + relay * FRIC * LAF / THR) * (1 + lsf / KP)
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    pipe = np.exp(-s * pipe_ms * 1e-3)
    cf = (1. - VM["chi"]) / (1. - VM["sf"] * v ** 2) / VM["l"]
    kla = cf / SR * v ** 2 * np.pi / 180.0              # m/s^2 of lat accel per deg of wheel angle
    return kla * Pin * ff_path(c, f) * zoh100 * pipe * 4096.0 / LAF * Cf


f = np.concatenate([np.geomspace(0.01, 1.0, 400), np.linspace(1.0, 45.0, 3000)])
members = ["nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "tau0", "tau6", "ms_free", "light_b"]
mem = {k: fam[k] for k in members}
mem["tau9"] = replace(fam["nominal"], name="tau9", tau_ms=9)
mem["lb_J2.5"] = replace(fam["light_b"], name="lb_J2.5", J=fam["light_b"].J * 2.5)
mem["lb_b0.5"] = replace(fam["light_b"], name="lb_b0.5", b=fam["light_b"].b * 0.5)
speeds = (3.1, 5.0, 8.0, 12.0, 17.0, 22.0, 26.9)
P("check: L_o at 0.01 Hz (must be large, positive real part = negative feedback): nominal 12 m/s V294",
  np.round(outer_L(fam["nominal"].at(12.0), V294, 12.0, np.array([0.01]))[0], 3))
P()
P("member v pipe relay | V294 GM PM Ms f_Ms | b964 GM PM Ms f_Ms | ratio GM, dMs")
worst = []
for nm, mb in mem.items():
    for v in speeds:
        p = mb.at(v)
        for pipe in (12.0, 22.0, 42.0, 62.0):
            for rel in (0.0, 1.0):
                m0 = A.margins(f, outer_L(p, V294, v, f, rel, pipe))
                m1 = A.margins(f, outer_L(p, B964, v, f, rel, pipe))
                worst.append((nm, v, pipe, rel, m0, m1))
                flag = ""
                if m1["GM"] < 0.9 * m0["GM"] or m1["GM"] < 1.5:
                    flag += " !GM"
                if m1["Ms"] > 1.1 * m0["Ms"]:
                    flag += " !Ms"
                if pipe in (22.0, 62.0) or flag:
                    P("%-9s %5.1f %2.0f %d | %6.2f %6.1f %5.2f %5.2f | %6.2f %6.1f %5.2f %5.2f | %.3f %+.3f%s" % (
                        nm, v, pipe, rel, m0["GM"], m0["PM"], m0["Ms"], m0["f_Ms"], m1["GM"], m1["PM"], m1["Ms"], m1["f_Ms"],
                        m1["GM"] / m0["GM"], m1["Ms"] - m0["Ms"], flag))
P()
r = [(w[5]["GM"] / w[4]["GM"], w) for w in worst]
lo = min(r, key=lambda t: t[0])
P("min GM ratio b964/V294 over everything: %.3f at" % lo[0], lo[1][:4], "GM %.2f -> %.2f" % (lo[1][4]["GM"], lo[1][5]["GM"]))
hi = max(worst, key=lambda w: w[5]["Ms"] - w[4]["Ms"])
P("max Ms increase: %+.3f at" % (hi[5]["Ms"] - hi[4]["Ms"]), hi[:4], "Ms %.3f -> %.3f" % (hi[4]["Ms"], hi[5]["Ms"]))
lowgm = min(worst, key=lambda w: w[5]["GM"])
P("lowest b964 GM: %.2f (V294 %.2f) at" % (lowgm[5]["GM"], lowgm[4]["GM"]), lowgm[:4])
hims = max(worst, key=lambda w: w[5]["Ms"])
P("highest b964 Ms: %.3f (V294 %.3f) at" % (hims[5]["Ms"], hims[4]["Ms"]), hims[:4])

# relay describing function: stable for every relay factor n in [0,1]?  (a saturation's DF spans (0, slope])
P()
P("relay DF: min over n in [0,1] of GM, and whether any n has GM < 1 (a limit cycle exists at N(A) = n* slope)")
for nm in ("nominal", "b_lo", "tau6", "light_b", "lb_b0.5", "lb_J2.5"):
    for v in (3.1, 8.0, 17.0, 26.9):
        p = mem[nm].at(v)
        for pipe in (22.0, 62.0):
            res = []
            for c in (V294, B964):
                gms = [A.margins(f, outer_L(p, c, v, f, n, pipe))["GM"] for n in np.linspace(0, 1, 11)]
                res.append((min(gms), int(np.argmin(gms)) / 10.0))
            P("  %-8s %5.1f pipe %2.0f : V294 GMmin %.2f (n %.1f)  b964 GMmin %.2f (n %.1f)%s" % (
                nm, v, pipe, res[0][0], res[0][1], res[1][0], res[1][1], "  !! LIMIT CYCLE PREDICTED" if res[1][0] < 1 else ""))
out.close()
