# -*- coding: utf-8 -*-
"""as7_modeA.py -- (d)(e) MY OWN nonlinear byte-exact replay: r71b's recorded 0xE4 (21 hands-off chunks, 608 s) ->
my integer demand chain -> MY lane (== golden model) -> MY plant integrator (written here: semi-implicit Euler, Karnopp
stick-slip, spring saturation, optional collocated two-mass, 3 ms rate former, integer transport delay) with the drive's
own residual replayed (dist lp / full, from the harness's chunk_c0 = data) and COMMON RANDOM NUMBERS (x noise 1.93).
Builds: V294, A (and V282 as the HF POSITIVE CONTROL on record-calibrated two-mass plants from as3).
Reads: C-clamp and P-clamp binding shares (all ticks and in hard turns), peak |T|, 13-25 / 17-23 Hz wheel-rate rms and
delivered-torque rms, hard-turn 1.6-3 Hz and 1-3 Hz wheel rate, restart bails."""
import os, sys, json, time
import numpy as np
from dataclasses import replace
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import v295_harness as H

c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106; c282 = A.read_cells("V282")
fam = H.family()
d = H.route()
chunks = H.route_chunks()
MAPLUT = {}


def demand(c, wire):
    key = id(c)
    if key not in MAPLUT:
        MAPLUT[key] = np.array([A.lerp_int(c["mapX"], c["mapY"], i) for i in range(256)], np.int64)
    S = np.clip(-4 * np.asarray(np.round(wire), np.int64), -0x4000, 0x4000)
    v6 = np.clip(((65025 * S) >> 16) >> 6, -240, 240)
    idx = np.abs(v6)
    return idx, -np.where(v6 < 0, -1, 1) * MAPLUT[key][idx], np.full(len(idx), 254, np.int64)


class MyPlant:
    def __init__(self, members, th0, om0, seed, noise):
        self.m = members
        B = len(members)
        self.th = th0.astype(float).copy(); self.om = om0.astype(float).copy()
        self.thw = self.th.copy(); self.omw = self.om.copy()
        self.tau = np.array([int(m.tau_ms) for m in members]); self.TL = int(self.tau.max()) + 1
        self.Tq = np.zeros((B, self.TL)); self.tp = 0
        self.hist = self.th[:, None] - self.om[:, None] * (3 - np.arange(3))[None, :] * 1e-3               # (B, 3)
        self.hp = 0
        self.rng = np.random.default_rng(seed); self.noise = noise
        self.f2 = np.array([m.f2 for m in members]); self.two = self.f2 > 0
        self.z2 = np.array([m.zeta2 for m in members]); self.r2 = np.array([m.r2 for m in members])

    def set_speed(self, v):
        J = np.zeros(len(self.m)); b = J.copy(); k = J.copy(); Fc = J.copy(); Fs = J.copy(); sat = J.copy()
        for i, m in enumerate(self.m):
            a = m.arrays_at(np.array([v[i]]))
            J[i], b[i], k[i], Fc[i], Fs[i], sat[i] = a["J"][0], a["b"][0], a["k"][0], a["Fc"][0], a["Fs"][0], a["sat"][0]
        self.J, self.b, self.k, self.Fc, self.Fs, self.sat = J, b, k, Fc, Fs, sat
        self.Jw = np.where(self.two, J * self.r2, 1.0); self.Jm = np.where(self.two, J * (1 - self.r2), J)
        mu = np.where(self.two, self.Jm * self.Jw / J, 1.0)
        self.K = np.where(self.two, (2 * np.pi * self.f2) ** 2 * mu, 0.0)
        self.cc = np.where(self.two, 2 * self.z2 * np.sqrt(self.K * mu), 0.0)

    def sense(self):
        xr = 8.0 * (self.th - self.hist[:, self.hp]) / 3e-3
        if self.noise:
            xr = xr + self.rng.normal(0, self.noise, len(xr))
        return np.clip(np.round(xr), -12000, 12000).astype(np.int64)

    def step(self, T, dist):
        B = len(T)
        rows = np.arange(B)
        # the torque written tau ticks ago: ring buffer per row
        self.Tq[:, self.tp] = T
        idx = (self.tp - self.tau) % self.TL
        u = -self.Tq[rows, idx] + dist
        self.tp = (self.tp + 1) % self.TL
        th, om = self.th, self.om
        f = u - self.k * self.sat * np.tanh(th / self.sat) - self.b * om - self.K * (th - self.thw) - self.cc * (om - self.omw)
        stuck = (om == 0.0) & (np.abs(f) <= self.Fs)
        sgn = np.where(om != 0.0, np.sign(om), np.sign(f))
        om2 = om + np.where(stuck, 0.0, (f - self.Fc * sgn) / self.Jm) * 1e-3
        om2[stuck | ((om != 0.0) & (np.sign(om2) != np.sign(om)))] = 0.0
        if self.two.any():
            self.omw = np.where(self.two, self.omw + (self.K * (th - self.thw) + self.cc * (om - self.omw)) / self.Jw * 1e-3, 0.0)
            self.thw = np.where(self.two, self.thw + self.omw * 1e-3, self.thw)
        self.hist[:, self.hp] = th
        self.hp = (self.hp + 1) % 3
        self.om = om2
        self.th = th + om2 * 1e-3


def replay(cells_list, members, dist="full", cmd_zero=False, seed=0, pipe=22):
    combos = [(ci, mi, ki) for ci in range(len(cells_list)) for mi in range(len(members)) for ki in range(len(chunks))]
    B = len(combos)
    lens = np.array([chunks[k][1] - chunks[k][0] for _, _, k in combos]); NF = int(lens.max())
    a0 = np.array([chunks[k][0] for _, _, k in combos])
    Dd = np.zeros((B, NF)); V = np.zeros((B, NF)); CMD = np.zeros((B, NF)); PLAN = np.zeros((B, NF))
    for j, (ci, mi, ki) in enumerate(combos):
        a, b = chunks[ki]
        s = H.chunk_c0(members[mi], a, b, dist=dist)
        Dd[j, :len(s)] = s; Dd[j, len(s):] = s[-1]
        for arr, key in ((V, "cs_vego_f"), (CMD, "e4_f")):
            x = d[key][a:b]; arr[j, :len(x)] = x; arr[j, len(x):] = x[-1]
        pl = d["ctl_des_curv_f"][a:b] * d["v"][a:b] ** 2; PLAN[j, :len(pl)] = pl; PLAN[j, len(pl):] = pl[-1]
    if cmd_zero:
        CMD[:] = 0.0
    # lanes: one MyLane per cells, rows grouped
    groups = {}
    for j, (ci, _, _) in enumerate(combos):
        groups.setdefault(ci, []).append(j)
    lanes = {ci: A.MyLane(cells_list[ci], len(r)) for ci, r in groups.items()}
    # warm-up each lane on the recorded 0x18F rate + recorded command, 1.5 s
    x1k = d["x1k"]
    for ci, r in groups.items():
        r = np.array(r)
        for kk in range(150, 0, -1):
            fr = a0[r] - kk
            idx, sp, m = demand(cells_list[ci], (np.zeros(len(r)) if cmd_zero else d["e4_f"][fr]))
            for t_ in range(10):
                lanes[ci].tick(np.clip(np.round(x1k[fr * 10 + t_]), -12000, 12000).astype(np.int64), sp, idx, m)
    plant = MyPlant([members[mi] for _, mi, _ in combos], d["th"][a0], d["om"][a0], seed, 1.93)
    OUT = {k: np.zeros((B, NF * 10), np.float32) for k in ("x", "T")}
    Ccl = np.zeros((B, NF * 10), bool); Pcl = np.zeros((B, NF * 10), bool)
    ANG = np.zeros((B, NF))
    idx = {ci: None for ci in groups}; sp = dict(idx); mm = dict(idx)
    for ci, r in groups.items():
        idx[ci], sp[ci], mm[ci] = demand(cells_list[ci], CMD[np.array(r), 0])
    T = np.zeros(B, np.int64)
    t0 = time.time()
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            plant.set_speed(V[:, k]); ANG[:, k] = np.where(plant.two, plant.thw, plant.th)
        if (n - pipe) >= 0 and (n - pipe) % 10 == 0:
            kc = (n - pipe) // 10
            for ci, r in groups.items():
                idx[ci], sp[ci], mm[ci] = demand(cells_list[ci], CMD[np.array(r), kc])
        x = plant.sense()
        for ci, r in groups.items():
            r = np.array(r)
            Tg, r26, P = lanes[ci].tick(-x[r], sp[ci], idx[ci], mm[ci])
            T[r] = Tg
            Ccl[r, n] = np.abs(r26) >= lanes[ci].C
            Pcl[r, n] = np.abs(P) >= lanes[ci].pcl
        plant.step(T.astype(float), Dd[:, k])
        OUT["x"][:, n] = x; OUT["T"][:, n] = T
    return dict(combos=combos, lens=lens, V=V, PLAN=PLAN, ANG=ANG, Ccl=Ccl, Pcl=Pcl, runtime=time.time() - t0, **OUT)


def band_rms(x, lo, hi, fs):
    b, a = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return signal.filtfilt(b, a, x)


def metrics(R, j):
    n = R["lens"][j]; n1 = n * 10
    x = R["x"][j, :n1].astype(float) / 8.0; T = R["T"][j, :n1].astype(float)
    cut = slice(1000, n1 - 1000)
    out = dict(C=float(R["Ccl"][j, :n1].mean()), P=float(R["Pcl"][j, :n1].mean()), Tpk=float(np.abs(T).max()))
    for lo, hi in ((13, 25), (17, 23)):
        out["w%d_%d" % (lo, hi)] = float(np.sqrt(np.mean(band_rms(x, lo, hi, 1000.0)[cut] ** 2)))
        out["T%d_%d" % (lo, hi)] = float(np.sqrt(np.mean(band_rms(T - T.mean(), lo, hi, 1000.0)[cut] ** 2)))
    r100 = x[5::10][:n]
    cut2 = slice(100, n - 100)
    out["r13"] = float(np.sqrt(np.mean(band_rms(r100, 1.0, 3.0, 100.0)[cut2] ** 2)))
    hard = (np.abs(R["PLAN"][j, :n]) >= 1.5) | (np.abs(R["ANG"][j, :n]) > 60)
    hm = np.zeros(n, bool); hm[cut2] = True; hm &= hard
    out["hard_n"] = int(hm.sum())
    out["hard16"] = float(np.sqrt(np.mean(band_rms(r100, 1.6, 3.0, 100.0)[hm] ** 2))) if hm.sum() > 100 else float("nan")
    hk = np.repeat(hard, 10)[:n1]
    out["C_hard"] = float(R["Ccl"][j, :n1][hk].mean()) if hk.any() else float("nan")
    out["P_hard"] = float(R["Pcl"][j, :n1][hk].mean()) if hk.any() else float("nan")
    return out


# record-calibrated two-mass members (as3: V282 zeta 0.010-0.035 at 19-21.5 Hz from zeta_open >= 0.05)
cal = json.load(open(os.path.join(HERE, "as3_hf20.json")))
pick = []
for tau in (3, 4, 6, 9):
    s = [t for t in cal if t["tau"] == tau]
    if s:
        w = min(s, key=lambda t: t["zA"] / t["zo"])
        pick.append(w)
calm = []
for t in pick:
    m = replace(fam[t["base"]], name="cal_%s_f%d_z%.2f_r%.2f_t%d" % (t["base"], t["f2"], t["z2"], t["r2"], t["tau"]),
                f2=float(t["f2"]), zeta2=float(t["z2"]), r2=float(t["r2"]), tau_ms=int(t["tau"]))
    m.kappa = False
    calm.append(m)
    print("calibrated member %s: open %.2f Hz zeta %.4f ; V282 %.2f Hz zeta %.4f ; V294 %.4f ; A %.4f (linear, at v %.1f)" % (
        m.name, t["fo"], t["zo"], t["f282"], t["z282"], t["zV"], t["zA"], t["v"]))

MEM = [fam[k] for k in ("nominal", "light_b", "F_hi", "b_lo", "J_hi2", "tau6", "mode20_lo")]
res = {}
for dist in ("full", "lp"):
    R = replay([c294, cA], MEM, dist=dist)
    print("replay %s: %d rows, %.0f s" % (dist, len(R["combos"]), R["runtime"]))
    res[dist] = R
print("\nMODE A (recorded command), per member: V294 -> A.  C/P clamp share (all ticks | hard turns), peak |T|, wheel rate "
      "13-25 Hz, 17-23 Hz torque, 1-3 Hz rate, hard-turn 1.6-3 Hz")
nC = len(chunks)
summ = {}
for dist, R in res.items():
    for mi, m in enumerate(MEM):
        agg = {}
        for tag, ci in (("V294", 0), ("A", 1)):
            rows = [ci * len(MEM) * nC + mi * nC + k for k in range(nC)]
            ms = [metrics(R, j) for j in rows]
            w = np.array([R["lens"][j] for j in rows], float)
            agg[tag] = {k: (float(np.nansum([q[k] * wi for q, wi in zip(ms, w) if np.isfinite(q[k])]) /
                                  max(np.sum([wi for q, wi in zip(ms, w) if np.isfinite(q[k])]), 1e-9)) if k not in ("Tpk",) else
                            float(max(q[k] for q in ms))) for k in ms[0]}
        V_, A_ = agg["V294"], agg["A"]
        summ[(dist, m.name)] = agg
        print("  %-4s %-9s C %.4f%%|%.4f%% -> %.4f%%|%.4f%% ; P %.3f%%|%.3f%% -> %.3f%%|%.3f%% ; Tpk %.0f -> %.0f ; w13-25 %.3f -> %.3f (x%.2f) ; "
              "T17-23 %.2f -> %.2f ; r1-3 x%.2f ; hard16 x%.2f" % (
                  dist, m.name, 100 * V_["C"], 100 * V_["C_hard"], 100 * A_["C"], 100 * A_["C_hard"], 100 * V_["P"], 100 * V_["P_hard"],
                  100 * A_["P"], 100 * A_["P_hard"], V_["Tpk"], A_["Tpk"], V_["w13_25"], A_["w13_25"], A_["w13_25"] / max(V_["w13_25"], 1e-9),
                  V_["T17_23"], A_["T17_23"], A_["r13"] / max(V_["r13"], 1e-9), A_["hard16"] / max(V_["hard16"], 1e-9)))

# HF positive control: record-calibrated two-mass plants, command held at 0 (the lane's own loop + the replayed residual)
print("\nHF POSITIVE CONTROL: record-calibrated plants, command 0, dist full; wheel rate 17-23 Hz rms and 13-25 Hz (deg/s)")
Rc = replay([c282, c294, cA], calm, dist="full", cmd_zero=True)
for mi, m in enumerate(calm):
    line = []
    for tag, ci in (("V282", 0), ("V294", 1), ("A", 2)):
        rows = [ci * len(calm) * nC + mi * nC + k for k in range(nC)]
        ms = [metrics(Rc, j) for j in rows]
        line.append("%s w17-23 %.3f w13-25 %.3f C %.3f%%" % (tag, np.mean([q["w17_23"] for q in ms]), np.mean([q["w13_25"] for q in ms]),
                                                           100 * np.mean([q["C"] for q in ms])))
    print("  %-38s %s" % (m.name, " | ".join(line)))
print("  (and with the RECORDED command, V294 vs A on the same calibrated plants)")
Rd = replay([c294, cA], calm, dist="full")
for mi, m in enumerate(calm):
    line = []
    for tag, ci in (("V294", 0), ("A", 1)):
        rows = [ci * len(calm) * nC + mi * nC + k for k in range(nC)]
        ms = [metrics(Rd, j) for j in rows]
        line.append("%s w17-23 %.3f T17-23 %.2f r1-3 %.2f" % (tag, np.mean([q["w17_23"] for q in ms]), np.mean([q["T17_23"] for q in ms]),
                                                           np.mean([q["r13"] for q in ms])))
    print("  %-38s %s" % (m.name, " | ".join(line)))
json.dump({"%s|%s" % k: v for k, v in summ.items()}, open(os.path.join(HERE, "as7_modeA.json"), "w"), default=float)
