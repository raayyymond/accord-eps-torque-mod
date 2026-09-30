# -*- coding: utf-8 -*-
"""as6_synth.py -- (c)(d) synthetic closed-loop scenarios with the fork law UNCHANGED in the loop:
  fork = harness ForkPort (the r1 LatControlTorque port, bit-identical to the real code, gate H3b) + Honda limiter,
  lane = MY integer lane (advlib.MyLane, == golden model), plant = harness PlantBatch (== v294_plant.simulate, gate H2a),
  pipe 22 ms, angle quantised 0.1 deg, x noise 1.93 counts with COMMON RANDOM NUMBERS (same seed, same rows) V294 vs A.
Scenarios: (i) on-centre hold with a road-crown torque and a small planner wander, 5/12/25 m/s;
           (ii) hard-turn step (planner ramp at 2.5 m/s^3 to 2.0-2.5 m/s^2, hold 6 s, unwind), 8/12/16/20 m/s;
           (iii) slow ramp (0.05 m/s^3) for stick-slip counting.
Reads: rate 0.5-5 Hz rms and PSD-peak prominence (limit cycles), overshoot, hold-phase residual oscillation, stick-slip
events (|rate| runs < 0.25 deg/s >= 0.2 s followed by a jump), P-clamp and C-clamp binding shares, peak |T|."""
import os, sys, json, time
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import v295_harness as H

c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106
fam = H.family()
TOG = H.route()["toggles"]
MEM = ["nominal", "light_b", "F_hi", "F_lo", "b_lo", "J_lo", "J_hi", "J_hi2", "tau6", "mode20_lo"]
MAPLUT = np.array([A.lerp_int(c294["mapX"], c294["mapY"], i) for i in range(256)], np.int64)


def demand(wire):
    S = np.clip(-4 * np.asarray(wire, np.int64), -0x4000, 0x4000)
    prod = (65025 * S) >> 16
    v6 = np.clip(prod >> 6, -240, 240)
    idx = np.abs(v6)
    sgn = np.where(v6 < 0, -1, 1)
    return idx, -sgn * MAPLUT[idx], np.full(len(idx), 254, np.int64)


def run(cells, members, v, la_des, crown, seed=0, pipe=22, x_noise=1.93):
    """members: list (B); v, la_des: (B, NF) 100 Hz; crown (B,) T counts + left.  Returns 100 Hz records."""
    B, NF = la_des.shape
    fork = H.ForkPort(B, TOG)
    plant = H.PlantBatch(members, np.zeros(B), np.zeros(B), c0=crown, x_noise=x_noise, seed=seed)
    lane = A.MyLane(cells, B)
    last_tq = np.zeros(B); steer_lim = np.zeros(B, bool)
    qcmd = np.zeros((B, NF + 4)); wire_eff = np.zeros(B)
    idx, sp, m = demand(wire_eff)
    R = {k: np.zeros((B, NF)) for k in ("ang", "rate", "T", "cmd", "la_act", "Pcl", "Ccl")}
    pc = np.zeros(B); cc = np.zeros(B)
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            plant.set_speed(v[:, k])
            ang = np.round(plant.wheel_angle() / 0.1) * 0.1
            curv = la_des[:, k] / np.maximum(v[:, k], 1.0) ** 2
            r = fork.step(np.ones(B, bool), v[:, k], ang, np.zeros(B, bool), np.zeros(B), np.zeros(B), curv,
                          np.full(B, 0.426), np.zeros(B), steer_lim)
            lim, can = H.honda_limiter(r["torque"], last_tq)
            steer_lim = np.abs(r["torque"] - lim) > 1e-2
            last_tq = lim
            qcmd[:, k] = can
            R["ang"][:, k] = ang; R["la_act"][:, k] = r["la_act"]
        if (n - pipe) >= 0 and (n - pipe) % 10 == 0:
            wire_eff = qcmd[:, (n - pipe) // 10]
            idx, sp, m = demand(wire_eff)
        x = plant.sense()
        T, r26, P = lane.tick(-x, sp, idx, m)
        pc += (np.abs(P) >= lane.pcl); cc += (np.abs(r26) >= lane.C)
        plant.step(T.astype(float))
        if n % 10 == 9:
            R["T"][:, k] = T; R["cmd"][:, k] = wire_eff; R["rate"][:, k] = x / 8.0
    R["Pcl"] = pc / (NF * 10); R["Ccl"] = cc / (NF * 10)
    return R


def bp(x, lo, hi):
    b, a = signal.butter(2, [lo / 50.0, hi / 50.0], btype="band")
    return signal.filtfilt(b, a, x)


def peakprom(x):
    f, P = signal.welch(x - x.mean(), fs=100.0, nperseg=min(512, len(x)))
    band = (f >= 0.5) & (f <= 5.0)
    i = np.argmax(P[band])
    return float(f[band][i]), float(P[band][i] / np.median(P[band])), float(P[band][i])


def stickslip(rate, ang):
    """dwell-then-jump: a run of |rate| < 0.25 deg/s lasting >= 0.2 s, followed within 0.3 s by |d angle| >= 0.3 deg."""
    ar = np.convolve(np.abs(rate), np.ones(10) / 10, "same")
    low = ar < 0.25
    n = 0; jumps = []
    i = 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if j - i >= 20 and j + 30 < len(ang):
                dj = abs(ang[j + 30] - ang[j])
                if dj >= 0.3:
                    n += 1; jumps.append(dj)
            i = j
        else:
            i += 1
    return n, (float(np.mean(jumps)) if jumps else 0.0)


out = {}
t0 = time.time()
# ---------------- (i) on-centre hold
rng = np.random.default_rng(3)
secs = 40
NF = secs * 100
speeds = (5.0, 12.0, 25.0)
rows = [(m, v, cr) for m in MEM for v in speeds for cr in (15.0, -40.0)]
B = len(rows)
wander = np.zeros((B, NF))
bw, aw = signal.butter(1, 0.5 / 50.0)
for j in range(B):
    wander[j] = signal.lfilter(bw, aw, rng.normal(0, 1, NF)) * 0.0     # set below
w0 = signal.lfilter(bw, aw, rng.normal(0, 1, NF)); w0 = w0 / w0.std() * 0.03
wander[:] = w0
V = np.array([[v] * NF for _, v, _ in rows], float)
members = [fam[m] for m, _, _ in rows]
crown = np.array([cr for _, _, cr in rows])
for tag, c in (("V294", c294), ("A", cA)):
    out[("centre", tag)] = run(c, members, V, wander, crown, seed=5)
print("on-centre simulated %.0f s" % (time.time() - t0))
print("\n(i) ON-CENTRE HOLD (40 s, crown +15 / -40 T, planner wander 0.03 m/s^2): per row V294 -> A")
print("   member     v   crown | ang std | rate 0.5-5 Hz rms | PSD peak f / prominence | stick-slip n (mean jump deg) | cmd rms")
agg = []
for j, (m, v, cr) in enumerate(rows):
    s = slice(500, NF)
    RV, RA = out[("centre", "V294")], out[("centre", "A")]
    a1, a2 = RV["ang"][j, s].std(), RA["ang"][j, s].std()
    r1, r2 = np.sqrt(np.mean(bp(RV["rate"][j], 0.5, 5)[s] ** 2)), np.sqrt(np.mean(bp(RA["rate"][j], 0.5, 5)[s] ** 2))
    p1, p2 = peakprom(RV["rate"][j, s]), peakprom(RA["rate"][j, s])
    s1, s2 = stickslip(RV["rate"][j, s], RV["ang"][j, s]), stickslip(RA["rate"][j, s], RA["ang"][j, s])
    c1, c2 = np.sqrt(np.mean(RV["cmd"][j, s] ** 2)), np.sqrt(np.mean(RA["cmd"][j, s] ** 2))
    agg.append((m, v, cr, a2 / max(a1, 1e-9), r2 / max(r1, 1e-9), p1[1], p2[1], s1[0], s2[0], s1[1], s2[1]))
    print("   %-9s %4.0f %5.0f | %.3f->%.3f | %.3f->%.3f (x%.2f) | %.2f/%.1f -> %.2f/%.1f | %d (%.2f) -> %d (%.2f) | %.0f->%.0f" % (
        m, v, cr, a1, a2, r1, r2, r2 / max(r1, 1e-9), p1[0], p1[1], p2[0], p2[1], s1[0], s1[1], s2[0], s2[1], c1, c2))
print("   summary: rate 0.5-5 Hz ratio A/V294 min %.2f max %.2f ; stick-slip total V294 %d A %d ; mean jump V294 %.2f A %.2f" % (
    min(q[4] for q in agg), max(q[4] for q in agg), sum(q[7] for q in agg), sum(q[8] for q in agg),
    np.mean([q[9] for q in agg if q[7]]) if any(q[7] for q in agg) else 0, np.mean([q[10] for q in agg if q[8]]) if any(q[8] for q in agg) else 0))

# ---------------- (ii) hard-turn step
t0 = time.time()
secs = 16
NF = secs * 100
tt = np.arange(NF) / 100.0
rows2 = [(m, v, (2.0 if v < 10 else 2.5), sg) for m in MEM for v in (8.0, 12.0, 16.0, 20.0) for sg in (1, -1)]
B = len(rows2)
LA = np.zeros((B, NF))
for j, (m, v, la, sg) in enumerate(rows2):
    tr = la / 2.5
    prof = np.clip((tt - 1.0) / tr, 0, 1) - np.clip((tt - (1.0 + tr + 7.0)) / tr, 0, 1)
    LA[j] = sg * la * prof
V = np.array([[v] * NF for _, v, _, _ in rows2], float)
members = [fam[m] for m, _, _, _ in rows2]
for tag, c in (("V294", c294), ("A", cA)):
    out[("turn", tag)] = run(c, members, V, LA, np.zeros(B), seed=9)
print("\nhard-turn simulated %.0f s" % (time.time() - t0))
print("\n(ii) HARD-TURN STEP (ramp 2.5 m/s^3 to 2.0 (8 m/s) / 2.5 m/s^2, hold 7 s, unwind): V294 -> A")
print("   member     v  sg | la overshoot % | hold rate 0.5-5 Hz rms (last 4 s) | hold PSD peak f/prom | hold la_act/plan | P-clamp % | C-clamp % | peak |T|")
agg2 = []
for j, (m, v, la, sg) in enumerate(rows2):
    tr = la / 2.5
    h0, h1 = int((1.0 + tr + 3.0) * 100), int((1.0 + tr + 7.0) * 100)
    RV, RA = out[("turn", "V294")], out[("turn", "A")]
    los = []
    for Rr in (RV, RA):
        act = Rr["la_act"][j] * sg
        ovs = 100.0 * (act[int((1 + tr) * 100):h1].max() / la - 1.0)
        hr = np.sqrt(np.mean(bp(Rr["rate"][j], 0.5, 5)[h0:h1] ** 2))
        pk = peakprom(Rr["rate"][j, h0:h1])
        hold = float(np.mean(act[h0:h1]) / la)
        los.append((ovs, hr, pk, hold, 100 * Rr["Pcl"][j], 100 * Rr["Ccl"][j], float(np.abs(Rr["T"][j]).max())))
    agg2.append((m, v, sg, los[0], los[1]))
    print("   %-9s %4.0f %+d | %+5.1f -> %+5.1f | %.3f -> %.3f (x%.2f) | %.2f/%.1f -> %.2f/%.1f | %.3f -> %.3f | %.2f->%.2f | %.3f->%.3f | %.0f->%.0f" % (
        m, v, sg, los[0][0], los[1][0], los[0][1], los[1][1], los[1][1] / max(los[0][1], 1e-9), los[0][2][0], los[0][2][1],
        los[1][2][0], los[1][2][1], los[0][3], los[1][3], los[0][4], los[1][4], los[0][5], los[1][5], los[0][6], los[1][6]))
print("   summary: hold rate ratio A/V294 min %.2f max %.2f ; overshoot change max %+.1f pts ; hold la ratio change %+.3f..%+.3f ; max C-clamp share A %.3f %%" % (
    min(q[4][1] / max(q[3][1], 1e-9) for q in agg2), max(q[4][1] / max(q[3][1], 1e-9) for q in agg2),
    max(q[4][0] - q[3][0] for q in agg2), min(q[4][3] - q[3][3] for q in agg2), max(q[4][3] - q[3][3] for q in agg2),
    max(q[4][5] for q in agg2)))

# ---------------- (iii) slow ramp: stick-slip
t0 = time.time()
secs = 30
NF = secs * 100
tt = np.arange(NF) / 100.0
rows3 = [(m, v) for m in MEM for v in (3.0, 5.0, 8.0, 12.0)]
B = len(rows3)
LA = np.array([np.clip(0.05 * (tt - 2.0), 0, None) for _ in rows3])        # 0.05 m/s^3 slow build
V = np.array([[v] * NF for _, v in rows3], float)
members = [fam[m] for m, _ in rows3]
for nz in (0.0, 1.93):
    for tag, c in (("V294", c294), ("A", cA)):
        out[("ramp%.2f" % nz, tag)] = run(c, members, V, LA, np.zeros(B), seed=13, x_noise=nz)
print("\nslow-ramp simulated %.0f s" % (time.time() - t0))
print("\n(iii) SLOW RAMP 0.05 m/s^3 (stick-slip): events n (mean jump deg), V294 -> A, x noise 0 and 1.93 (CRN)")
tot = {}
for nz in (0.0, 1.93):
    RV, RA = out[("ramp%.2f" % nz, "V294")], out[("ramp%.2f" % nz, "A")]
    line = []
    for j, (m, v) in enumerate(rows3):
        s1 = stickslip(RV["rate"][j, 200:], RV["ang"][j, 200:]); s2 = stickslip(RA["rate"][j, 200:], RA["ang"][j, 200:])
        tot.setdefault(nz, [0, 0, [], []])
        tot[nz][0] += s1[0]; tot[nz][1] += s2[0]
        if s1[0]: tot[nz][2].append(s1[1])
        if s2[0]: tot[nz][3].append(s2[1])
        line.append("%s@%g %d(%.2f)->%d(%.2f)" % (m, v, s1[0], s1[1], s2[0], s2[1]))
    print("  noise %.2f: " % nz + " ; ".join(line))
    print("  noise %.2f TOTAL: V294 %d events (mean jump %.3f deg) ; A %d events (mean jump %.3f deg)" % (
        nz, tot[nz][0], np.mean(tot[nz][2]) if tot[nz][2] else 0, tot[nz][1], np.mean(tot[nz][3]) if tot[nz][3] else 0))
json.dump(dict(centre=[list(map(float, q[3:])) + list(q[:3]) for q in agg]), open(os.path.join(HERE, "as6_synth.json"), "w"), default=str)
