# -*- coding: utf-8 -*-
"""as4_outer.py -- (c) the OUTER loop with the UNCHANGED fork law (r1: Kp 0.9, Ki 0.3, LAF 14, friction 0.011, thr 0.30),
MY OWN linearisation written from latcontrol_torque.py @20d24ab79 (the extract; lines 338-345, 600-606, 686-698) and
pid.py, NOT from the harness outer_frf (which is used only as a cross-check at the end).

  meas = cf(v) * v^2 * rad(theta) / sR                     (-VM.calc_curvature * v^2; theta = 0x14A angle, deg)
  err_lsf = (setpoint - meas) * (1 + lsf / Kp),  lsf = (interp(v,[0,10,20,30],[12,10.5,8,5]) / max(v, 1))^2
  out_la = Kp*err_lsf + Ki*dt*sum(err_lsf) + interp(err_lsf + 0.22 fj, [-thr,thr], [-fr*LAF, fr*LAF]) + ff(setpoint)
  wire = 4096 * out_la / LAF   (Honda: apply_torque = -lim*4096; the sign closes negative feedback)
  -> 100 Hz ZOH + pipe delay -> lane FF (map slope, shl 2, Kp 960, taper 254, output lag, gain) -> plant with the
     inner trim loop closed -> theta.
Relay: its small-signal slope fr*LAF/thr (worst case, amplitude <= thr) and OFF (saturated, large amplitude); plus the
describing function at intermediate amplitudes.  sR incremental-gain factor 1.0 (centre) and 1.4 (the Accord SR map's
slope at 100-250 deg: d(theta/sR)/d theta)."""
import os, sys, json, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import v294_plant as VP
import v295_harness as H

c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106
fam = VP.family()
VMc = H._vm_consts()
print("VM consts (read from the fork's CarParams via fork_real):", VMc)
KP, KI, LAF, FR, THR = 0.9, 0.3, 14.0, float(np.float32(0.011)), 0.30
SR0 = 16.84
WIRE_PER_IDX = 2 ** 22 / (4 * 65025)
# the incremental sR gain on the Accord map (my own derivative of theta/sR(theta))
SR_BP = np.array([0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0])
SR_V = np.array([16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68, 14.45, 14.09, 14.25, 12.98, 12.31]) * (16.84 / 16.88)
th = np.linspace(0, 370, 3701)
inc = np.gradient(th / np.interp(th, SR_BP, SR_V), th) * SR0
print("incremental sR gain d(theta/sR)/dtheta x 16.84 at 0/50/100/150/200/250/300/350 deg:",
      np.round(np.interp([0, 50, 100, 150, 200, 250, 300, 350], th, inc), 3), " max %.3f" % inc.max())


def ff_lane(c, f):
    """wire count -> T (tap), small signal, linear map (4.30 sp/idx everywhere below idx 240)."""
    zi = np.exp(-2j * np.pi * np.asarray(f) * 1e-3)
    slope = (c["mapY"][-1] - c["mapY"][0]) / (c["mapX"][-1] - c["mapX"][0])     # sp per idx (the map is linear)
    sp_w = slope / WIRE_PER_IDX
    S = (254 / 256.0) * (c["kpY"][0] / 256.0) * (2 ** c["sh"]) * sp_w
    y = (c["lb"] / 1024.0) * (1 + zi) / (32 * (1 - (c["la"] / 1024.0) * zi)) * S
    return y * c["gain"] / 32768.0


def outer_L(c, p, v, f, relay=1.0, pipe_ms=22.0, srg=1.0):
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    Lin = A.inner_L(c, p, f)
    zoh1k = np.exp(-1j * np.pi * f * 1e-3) * np.sinc(f * 1e-3)
    Pcl = A.plant_theta_per_u(p, f) * zoh1k / (1 + Lin)                    # theta per (-T_ff)
    z100 = np.exp(s * 0.01)
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
    Cf = (KP + KI * 0.01 / (1 - 1 / z100) + relay * FR * LAF / THR) * (1 + lsf / KP)
    cf = (1 - VMc["chi"]) / (1 - VMc["sf"] * v ** 2) / VMc["l"]
    kla = cf * v ** 2 * np.pi / 180.0 / SR0 * srg
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    return kla * Cf * (4096.0 / LAF) * zoh100 * np.exp(-s * pipe_ms * 1e-3) * ff_lane(c, f) * Pcl


F = np.logspace(np.log10(0.02), np.log10(49.9), 4000)
# cross-check vs the harness outer_frf (different author) at one point
p = fam["nominal"].at(12.0)
pd_ = dict(J=p.J, b=p.b, k=p.k, tau_ms=p.tau_ms, w=3)
Lm = outer_L(c294, pd_, 12.0, np.array([0.1, 0.5, 1.0, 2.0, 5.0]))
Lh = H.outer_frf(H.Cells.v294(), p, 12.0, np.array([0.1, 0.5, 1.0, 2.0, 5.0]))
print("cross-check vs harness outer_frf (nominal, 12 m/s): mine", np.round(Lm, 4), "\n                                                   harness", np.round(Lh, 4))

res = []
members = ["nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_hi", "F_lo", "tau6", "ms_free", "light_b"]
extra = [("nominal", 0.5, 1.0), ("nominal", 2.5, 1.0), ("light_b", 0.5, 1.0), ("light_b", 2.5, 1.0), ("light_b", 1.0, 1 / 1.8),
         ("light_b", 1.0, 1.5)]
cases = [(m, 1.0, 1.0) for m in members] + extra
for (name, Jx, bx), v, relay, pipe, srg in itertools.product(cases, (1.5, 3.1, 5.0, 8.0, 11.9, 17.0, 22.0, 26.9, 30.0),
                                                           (1.0, 0.0), (22.0, 40.0, 62.0), (1.0, 1.4)):
    a = fam[name].arrays_at(np.array([v]))
    p = dict(J=float(a["J"][0]) * Jx, b=float(a["b"][0]) * bx, k=float(a["k"][0]), tau_ms=fam[name].tau_ms, w=3)
    mV = A.margins(F, outer_L(c294, p, v, F, relay, pipe, srg))
    mA = A.margins(F, outer_L(cA, p, v, F, relay, pipe, srg))
    res.append(dict(case="%s Jx%.1f bx%.2f" % (name, Jx, bx), v=v, relay=relay, pipe=pipe, srg=srg,
                    V=dict(GM=mV["GM"], PM=mV["PM"], Ms=mV["Ms"], fMs=mV["fMs"]), A=dict(GM=mA["GM"], PM=mA["PM"], Ms=mA["Ms"], fMs=mA["fMs"])))
print("outer cases:", len(res))
fail = [r for r in res if r["A"]["GM"] < 0.95 * min(r["V"]["GM"], 2.0) or r["A"]["Ms"] > max(1.1 * r["V"]["Ms"], 1.5)]
print("F-OUT-1 hits (A GM < 0.95 min(GM_V294, 2) or A Ms > max(1.1 Ms_V294, 1.5)): %d" % len(fail))
for r in sorted(fail, key=lambda r: r["A"]["GM"])[:20]:
    print("   %-24s v%4.1f relay %.0f pipe %2.0f srg %.1f | V294 GM %.2f PM %.0f Ms %.2f | A GM %.2f PM %.0f Ms %.2f @%.2f Hz" % (
        r["case"], r["v"], r["relay"], r["pipe"], r["srg"], r["V"]["GM"], r["V"]["PM"], r["V"]["Ms"], r["A"]["GM"], r["A"]["PM"], r["A"]["Ms"], r["A"]["fMs"]))
# A worse than V294 at all (GM lower or Ms higher)?
worse = [r for r in res if r["A"]["GM"] < r["V"]["GM"] * 0.999 or r["A"]["Ms"] > r["V"]["Ms"] * 1.001]
print("cases where A's outer margin is WORSE than V294's at all: %d of %d" % (len(worse), len(res)))
for r in sorted(worse, key=lambda r: r["A"]["GM"] / r["V"]["GM"])[:15]:
    print("   %-24s v%4.1f relay %.0f pipe %2.0f srg %.1f | V294 GM %.2f PM %.0f Ms %.3f | A GM %.2f PM %.0f Ms %.3f" % (
        r["case"], r["v"], r["relay"], r["pipe"], r["srg"], r["V"]["GM"], r["V"]["PM"], r["V"]["Ms"], r["A"]["GM"], r["A"]["PM"], r["A"]["Ms"]))
# per speed band table for the nominal and light_b, relay on, pipe 22, srg 1
print("\nper speed (relay on, pipe 22 ms, srg 1.0): V294 -> A   GM / PM / Ms")
for name in ("nominal Jx1.0 bx1.00", "b_lo Jx1.0 bx1.00", "F_hi Jx1.0 bx1.00", "J_hi2 Jx1.0 bx1.00", "light_b Jx1.0 bx1.00"):
    line = []
    for v in (1.5, 3.1, 5.0, 8.0, 11.9, 17.0, 22.0, 26.9, 30.0):
        r = [q for q in res if q["case"] == name and q["v"] == v and q["relay"] == 1.0 and q["pipe"] == 22.0 and q["srg"] == 1.0][0]
        line.append("%.0f: %.2f/%.0f/%.2f->%.2f/%.0f/%.2f" % (v, r["V"]["GM"], r["V"]["PM"], r["V"]["Ms"], r["A"]["GM"], r["A"]["PM"], r["A"]["Ms"]))
    print("  %-22s %s" % (name.split()[0], " | ".join(line)))
# worst overall per build
wv = min(res, key=lambda r: r["V"]["GM"]); wa = min(res, key=lambda r: r["A"]["GM"])
print("worst GM overall: V294 %.2f (%s v%.1f relay %.0f pipe %.0f srg %.1f) ; A %.2f (%s v%.1f relay %.0f pipe %.0f srg %.1f)" % (
    wv["V"]["GM"], wv["case"], wv["v"], wv["relay"], wv["pipe"], wv["srg"], wa["A"]["GM"], wa["case"], wa["v"], wa["relay"], wa["pipe"], wa["srg"]))
wv = max(res, key=lambda r: r["V"]["Ms"]); wa = max(res, key=lambda r: r["A"]["Ms"])
print("worst Ms overall: V294 %.2f (%s v%.1f relay %.0f pipe %.0f srg %.1f) ; A %.2f (%s v%.1f relay %.0f pipe %.0f srg %.1f)" % (
    wv["V"]["Ms"], wv["case"], wv["v"], wv["relay"], wv["pipe"], wv["srg"], wa["A"]["Ms"], wa["case"], wa["v"], wa["relay"], wa["pipe"], wa["srg"]))
json.dump(res, open(os.path.join(HERE, "as4_outer.json"), "w"), default=float)
