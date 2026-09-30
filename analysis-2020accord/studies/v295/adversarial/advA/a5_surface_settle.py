# -*- coding: utf-8 -*-
"""ADV-A a5: (1) delivered surface at r26 = 0 (golden lkas_rate_pid_surface AND my mirror's march) at 241 idx x 2 signs,
V294 vs V295; rail; zero-command torque.  (2) static delivered T at CONSTANT x from many initial states (cold boot,
restart, the extreme reachable s, random s), x in a grid incl. +-12000: r26 must settle to exactly 0 and T must equal
V294's.  (3) DC bias of r26 / T under zero-mean noise (white and 20 Hz-coloured), incl. at the rail (P-clamp
rectification), V294 vs V295."""
import json, os, sys, random
from dataclasses import replace
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
import advA_lane as A  # noqa: E402
import advA_vec as V  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402
from a2_mirror_vs_golden import golden_cal  # noqa: E402  (module body re-runs its 140k-tick check: fine)

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
c4, c5 = J["v294"], J["v295"]
g4, g5 = golden_cal(c4), golden_cal(c5)

# (1) golden surface, both signs (pol +-1 as the golden function exposes it)
nd = 0; rail = {}
for pol in (1, -1):
    for i in range(241):
        a = M.lkas_rate_pid_surface(i, g5, pol=pol); b = M.lkas_rate_pid_surface(i, g4, pol=pol)
        if (a["T"], a["T_lo"], a["T_hi"], a["P"], a["S"]) != (b["T"], b["T_lo"], b["T_hi"], b["P"], b["S"]):
            nd += 1
        if i == 240:
            rail[pol] = (a["T"], a["T_lo"], a["T_hi"])
print("golden surface V295 vs V294, 241 idx x pol +-1: cells differing = %d ; rail (T, T_lo, T_hi) pol+1 %s pol-1 %s"
      % (nd, rail[1], rail[-1]))
print("zero command idx 0: V295 T = %d, V294 T = %d" % (M.lkas_rate_pid_surface(0, g5)["T"], M.lkas_rate_pid_surface(0, g4)["T"]))

# my mirror, demand sign +-1 (the firmware's own sign path: sp = mulh(sign, map)), x = 0, cold boot, 3000 ticks
B = 482
li = np.repeat(np.arange(241), 2); ls = np.tile([1, -1], 241)
out = {}
for nm, c in (("v294", c4), ("v295", c5)):
    VL = V.VecLane(c, B)
    sp = ls * VL.map_tab[li]
    for _ in range(3000):
        T = VL.tick(np.zeros(B, np.int64), sp, li)
    out[nm] = T.copy()
print("mirror surface (demand sign +-1, x = 0): differing %d ; V295 extremes %d / %d ; slope check T(120)=%d"
      % (int(np.sum(out["v294"] != out["v295"])), out["v295"].max(), out["v295"].min(), out["v295"][240]))

# (2) static T at constant x from many initial states
xs = [0, 1, -1, 7, -7, 80, -80, 800, -800, 2400, -2400, 8000, -8000, 11999, -11999, 12000, -12000]
idxs = [0, 1, 60, 120, 180, 230, 238, 240]
rng = random.Random(3)
starts = ["boot", "restart", "smax", "smin", "rand", "rand", "rand", "rand"]
lanes = [(x, i, sg, st) for x in xs for i in idxs for sg in (1, -1) for st in starts]
NL = len(lanes)
res = {}
for nm, c in (("v294", c4), ("v295", c5)):
    VL = V.VecLane(c, NL)
    lx = np.array([l[0] for l in lanes], np.int64); li2 = np.array([l[1] for l in lanes]); ls2 = np.array([l[2] for l in lanes])
    s0 = []
    for l in lanes:
        st = l[3]
        s0.append(0 if st in ("boot", "restart") else (969098 if st == "smax" else (-969256 if st == "smin" else rng.randint(-969256, 969098))))
    rng.seed(3)
    VL.s = np.array(s0, np.int64)
    VL.sent = np.array([0 if l[3] in ("boot", "restart") else 1 for l in lanes], np.int64)
    sp = ls2 * VL.map_tab[li2]
    Ts = []
    for k in range(8000):
        T = VL.tick(lx, sp, li2)
        if k >= 7500:
            Ts.append(T.copy())
    Ts = np.array(Ts)
    res[nm] = dict(T=Ts[-1], const=np.all(Ts == Ts[-1], axis=0), r26=VL.last["r26"].copy(), maxp=dict(VL.maxp))
print("constant-x settle, %d lanes (x grid %s, idx %s, sign +-1, 8 start states), 8000 ticks:" % (NL, xs, idxs))
for nm in ("v294", "v295"):
    print("   %s: r26 == 0 on %d/%d lanes ; T constant over last 500 ticks on %d/%d ; max products %s"
          % (nm, int(np.sum(res[nm]["r26"] == 0)), NL, int(np.sum(res[nm]["const"])), NL, res[nm]["maxp"]))
d = res["v295"]["T"] - res["v294"]["T"]
print("   settled T V295 - V294: lanes differing %d, max |diff| %d" % (int(np.sum(d != 0)), int(np.abs(d).max())))
# T vs the r26 = 0 surface (x-independence of the static surface)
surf = {(i, s): out["v295"][2 * i + (0 if s == 1 else 1)] for i in range(241) for s in (1, -1)}
dev = [abs(int(res["v295"]["T"][j]) - int(surf[(l[1], l[2])])) for j, l in enumerate(lanes)]
print("   settled T at constant x vs the x = 0 surface: max |diff| = %d (fixed-point interval of the output lag: <= 1 expected)" % max(dev))

# (3) DC bias under zero-mean noise
N = 200000
rng2 = np.random.default_rng(11)
cases = []
for sig in (2.0, 20.0, 200.0):
    cases.append(("white sd %g" % sig, np.round(rng2.normal(0, sig, N)).astype(np.int64)))
t = np.arange(N) / 1000.0
for amp in (100, 400):
    cases.append(("20 Hz sine amp %d + white 2" % amp, np.round(amp * np.sin(2 * np.pi * 20 * t) + rng2.normal(0, 2, N)).astype(np.int64)))
for amp in (400, 1500):
    cases.append(("2.4 Hz sine amp %d" % amp, np.round(amp * np.sin(2 * np.pi * 2.4 * t)).astype(np.int64)))
idx_b = [0, 120, 238, 240]
print("DC bias under zero-mean x (N = %d ticks, after a 5000-tick settle), mean T minus the no-noise T, per idx:" % N)
for nm_case, xn in cases:
    row = []
    for nm, c in (("v294", c4), ("v295", c5)):
        VL = V.VecLane(c, 2 * len(idx_b))
        li3 = np.repeat(idx_b, 2); ls3 = np.tile([1, -1], len(idx_b))
        sp = ls3 * VL.map_tab[li3]
        acc = np.zeros(2 * len(idx_b)); r26sum = np.zeros(2 * len(idx_b)); smax = 0
        for k in range(5000):
            VL.tick(np.zeros(2 * len(idx_b), np.int64), sp, li3)
        T0 = VL.tick(np.zeros(2 * len(idx_b), np.int64), sp, li3).astype(float)
        s_start = VL.s.copy()
        for k in range(N):
            T = VL.tick(np.full(2 * len(idx_b), xn[k]), sp, li3)
            acc += T; r26sum += VL.last["r26"]
        smax = max(smax, int(np.abs(VL.s).max()))
        bias = acc / N - T0
        row.append((nm, bias, r26sum / N, (VL.s - s_start)))
    b4, b5 = row[0][1], row[1][1]
    tel = [int(np.max(np.abs(np.round(r[2] * N).astype(np.int64) - r[3]))) for r in row]
    print("  %-26s mean r26 V294 %+.5f V295 %+.5f | max |sum r26 - (s_end - s_start)| V294 %d V295 %d (0 = telescopes exactly)" %
          (nm_case, row[0][2].mean(), row[1][2].mean(), tel[0], tel[1]))
    for j, i in enumerate(idx_b):
        print("       idx %3d  dT V294 (+,-) %+7.2f %+7.2f | V295 %+7.2f %+7.2f" % (i, b4[2 * j], b4[2 * j + 1], b5[2 * j], b5[2 * j + 1]))
