# -*- coding: utf-8 -*-
"""a8 -- (c)/(d) NONLINEAR closed-loop replay with my own lane + plant (adv_sim) and the fork port.
 part 0  VLane == adv_lib.MyLane (which == golden model) on random ticks.
 part 1  POSITIVE CONTROL: the r71-old anchor -- V293 (trim off, same FF) + fork rev 2 (Kp 0.85) on a sustained 16-29 deg
         curve at 21.8 m/s must LIMIT-CYCLE near 2.3 Hz in a record-consistent world, and V294 + r1 must not.
 part 2  V294 vs candidate: on-centre (crown 15/60 T), sustained curves at the drive's angles, hard-turn ramps, and a
         dither across the idx-100 kink, on the identified family + light_b + two record-calibrated worlds.
Metrics per lane over the analysis window: rate spectral peak excess (0.5-8 Hz), 1-3 / 3-8 Hz rate rms, breakaways/min,
slew share, overshoot / hard16 for ramps."""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lib as A  # noqa: E402
import adv_outer as AO  # noqa: E402
import adv_sim as SIM  # noqa: E402
import v294_plant as VP  # noqa: E402
import v295_harness as H  # noqa: E402

out = open(os.path.join(HERE, "a8_nlsim_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.write(s + "\n")
    out.flush()


b294, _ = A.load(A.IMG_V294, A.SHA_V294)
C294 = A.cells(b294)
CC = A.cells(A.write_candidate(b294))
C293 = dict(C294, fb_clamp=0)                      # V293 = V294's FF exactly (120<<5 == 960<<2), trim off
TG = H.route()["toggles"]
TG_REV2 = dict(TG, steerKp=[[0], [0.85]])

# ---------------- part 0
rng = np.random.default_rng(3)
L = SIM.VLane([C294, CC])
ref = [A.MyLane(C294), A.MyLane(CC)]
mism = 0
wire = np.zeros(2, np.int64)
x = np.zeros(2, np.int64)
for n in range(6000):
    if n % 10 == 0:
        wire = np.clip(wire + rng.integers(-150, 151, 2), -3900, 3900)
        idx, sp = L.demand(wire)
        rs = [r.demand(int(w)) for r, w in zip(ref, wire)]
        mism += int(any(int(idx[j]) != rs[j][0] or int(sp[j]) != rs[j][1] for j in range(2)))
    x = np.clip(x + rng.integers(-60, 61, 2), -11000, 11000)
    T, _, _ = L.tick(x, sp, idx)
    for j in range(2):
        t, _ = ref[j].tick(int(x[j]), int(sp[j]), int(idx[j]))
        mism += int(t != T[j])
P("part 0: VLane vs MyLane (tick-exact vs golden): %d mismatches over 6000 ticks x 2 lanes (demand + T)" % mism)

fam = VP.family()


def pp(nm, v, beta=1.0, gamma=1.0):
    base = "light_b" if nm.startswith("cw") else nm
    p = fam[base].at(v)
    return dict(J=p.J * gamma, b=p.b * beta, k=p.k, sat=float(AO.sat_prior(v)), Fc=p.Fc, Fs=p.Fs)


WORLDS = {"nominal": ("nominal", 1, 1), "b_lo": ("b_lo", 1, 1), "F_hi": ("F_hi", 1, 1), "J_hi2": ("J_hi2", 1, 1),
          "light_b": ("light_b", 1, 1), "cw_b1_J.5": ("cw", 1.0, 0.5), "cw_b1.25_J1": ("cw", 1.25, 1.0),
          "cw_b.75_J.5": ("cw", 0.75, 0.5)}


def bandnoise(nsamp, fs, lo, hi, rms, seed):
    r = np.random.default_rng(seed)
    bb, aa = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    z = signal.lfilter(bb, aa, r.normal(size=nsamp))
    return z * rms / max(np.std(z), 1e-12)


def fork_curv(theta, v):
    fp = H.ForkPort(1, TG)
    return float(fp.curvature(np.array([theta]), np.array([v]), 0.0)[0])


def excess_db(sig, lo=0.5, hi=8.0):
    f, p = signal.welch(signal.detrend(sig), fs=100.0, nperseg=512)
    fit = (f >= 0.3) & (f <= 12) & (p > 1e-20)
    if fit.sum() < 5 or not np.all(np.isfinite(p)):
        return float("nan"), float("nan")
    c = np.polyfit(np.log(f[fit]), np.log(p[fit]), 2)
    base = np.exp(np.polyval(c, np.log(np.maximum(f, 1e-3))))
    band = (f >= lo) & (f <= hi)
    ex = 10 * np.log10(p[band] / base[band])
    j = int(np.argmax(ex))
    return float(ex[j]), float(f[band][j])


def brms(sig, lo, hi):
    bb, aa = signal.butter(2, [lo / 50, hi / 50], btype="band")
    return float(np.std(signal.filtfilt(bb, aa, signal.detrend(sig))))


def run_cases(cases, secs, toggles, tag):
    """cases: list of dict(cells, world, v, theta_target, des (n_frames), dist (n_ticks), label)"""
    B = len(cases)
    par = {k: np.array([c["par"][k] for c in cases]) for k in ("J", "b", "k", "sat", "Fc", "Fs")}
    par["tau"] = 2
    v = np.array([c["v"] for c in cases])
    des = np.stack([c["des"] for c in cases])
    dist = np.stack([c["dist"] for c in cases])
    th0 = np.array([c.get("th0", 0.0) for c in cases])
    rec = SIM.run([c["cells"] for c in cases], par, v, des, dist, secs, toggles, th0=th0, seed=11)
    np.savez_compressed(os.path.join(HERE, "_scratch_%s.npz" % tag), **{k: rec[k] for k in ("ang", "om", "cmd", "T", "idx")})
    res = []
    for j, c in enumerate(cases):
        a0 = int(c.get("an0", 30) * 100)
        om = rec["om"][j, a0:]
        ang = rec["ang"][j, a0:]
        r = dict(label=c["label"], world=c["world"], build=c["build"], v=c["v"])
        r["rate_peak_db"], r["rate_peak_f"] = excess_db(om)
        r["cmd_peak_db"], r["cmd_peak_f"] = excess_db(rec["cmd"][j, a0:])
        r["rate13"] = brms(om, 1.0, 3.0)
        r["rate16_3"] = brms(om, 1.6, 3.0)
        r["rate38"] = brms(om, 3.0, 8.0)
        r["rate_rms"] = float(np.std(om))
        r["ang_mean"] = float(np.mean(ang))
        r["ang_pp"] = float(np.percentile(ang, 99) - np.percentile(ang, 1))
        r["slew"] = float(np.mean(rec["slew"][j, a0:]))
        r["brk_min"] = float(rec["breakaways"][j]) / (len(om) / 100.0 + a0 / 100.0) * 60.0
        r["idx_p50"] = float(np.median(rec["idx"][j, a0:]))
        r["dT_max"] = float(np.max(np.abs(np.diff(rec["T"][j, a0:]))))
        res.append(r)
    return res


os.makedirs(HERE, exist_ok=True)
NS = 80.0
nfr, ntk = int(NS * 100), int(NS * 1000)

# ---------------- part 1: positive control (r71-old anchor) at 21.8 m/s
P("\npart 1: POSITIVE CONTROL -- r71-old (V293 + rev 2) must limit-cycle ~2.3 Hz on a 16-29 deg curve at 21.8 m/s")
cases = []
for wn in ("light_b", "cw_b1_J.5", "cw_b1.25_J1", "cw_b.75_J.5", "nominal"):
    base, be, ga = WORLDS[wn]
    for th in (16.0, 22.0, 29.0):
        for bn, cl in (("V293", C293), ("V294", C294), ("cand", CC)):
            des = np.full(nfr, fork_curv(th, 21.8))
            cases.append(dict(cells=cl, world=wn, build=bn, v=21.8, par=pp(base if base != "cw" else "cw", 21.8, be, ga),
                              des=des, dist=bandnoise(ntk, 1000.0, 0.5, 5.0, 5.0, 7), th0=th, label="curve%.0f" % th))
for tg_name, tg in (("rev2", TG_REV2), ("r1", TG)):
    res = run_cases(cases, NS, tg, "p1_" + tg_name)
    P(" fork %s:" % tg_name)
    for r in res:
        P("   %-12s %-9s %-4s: rate peak %+5.1f dB @%.2f Hz | cmd peak %+5.1f @%.2f | rate 1-3 Hz %.2f deg/s | angle p-p %.1f deg (mean %.1f) | slew %.3f" % (
            r["world"], r["label"], r["build"], r["rate_peak_db"], r["rate_peak_f"], r["cmd_peak_db"], r["cmd_peak_f"], r["rate13"],
            r["ang_pp"], r["ang_mean"], r["slew"]))
    json.dump(res, open(os.path.join(HERE, "a8_part1_%s.json" % tg_name), "w"))

# ---------------- part 2
P("\npart 2: V294 vs candidate, fork r1, scenarios x worlds")
cases = []
seed = 100
for wn, (base, be, ga) in WORLDS.items():
    for bn, cl in (("V294", C294), ("cand", CC)):
        # S1 on-centre, crown 15 / 60 T, planner wander 0.05 m/s^2, road 0.5-5 Hz 3 T
        for v in (8.0, 12.0, 17.0, 22.0, 27.0):
            for crown in (15.0, 60.0):
                des = bandnoise(nfr, 100.0, 0.05, 1.0, 0.05 / v ** 2, seed + int(v))
                dist = crown + bandnoise(ntk, 1000.0, 0.5, 5.0, 3.0, seed + 1)
                cases.append(dict(cells=cl, world=wn, build=bn, v=v, par=pp(base, v, be, ga), des=des, dist=dist,
                                  th0=0.0, label="oncentre c%.0f" % crown))
        # S2 sustained curves at the drive's angles
        for v, th in ((12.0, 9.6), (17.0, 18.4), (21.8, 22.0), (26.9, 11.0)):
            des = np.full(nfr, fork_curv(th, v)) + bandnoise(nfr, 100.0, 0.05, 1.0, 0.03 / v ** 2, seed + 3)
            cases.append(dict(cells=cl, world=wn, build=bn, v=v, par=pp(base, v, be, ga), des=des,
                              dist=bandnoise(ntk, 1000.0, 0.5, 5.0, 5.0, seed + 4), th0=th, label="curve %.0fdeg" % th))
        # S3 hard-turn ramps (0 -> theta over 1.5 s, hold 4 s, back 1.5 s, straight 3 s), repeated
        for v, th in ((8.0, 76.0), (8.0, 120.0), (12.0, 52.0), (17.0, 22.0)):
            kk = fork_curv(th, v)
            prof = np.concatenate([np.linspace(0, 1, 150), np.ones(400), np.linspace(1, 0, 150), np.zeros(300)])
            des = np.tile(prof, nfr // len(prof) + 1)[:nfr] * kk
            cases.append(dict(cells=cl, world=wn, build=bn, v=v, par=pp(base, v, be, ga), des=des,
                              dist=bandnoise(ntk, 1000.0, 0.5, 5.0, 3.0, seed + 5), th0=0.0, label="ramp %.0fdeg" % th, an0=10))
        # S4 dither across the idx-100 kink at 8 m/s (hold ~ the V294 idx-100 angle, +-12 % at 1 Hz)
        th100 = 120.0
        des = fork_curv(th100, 8.0) * (1 + 0.12 * np.sin(2 * np.pi * 1.0 * np.arange(nfr) / 100.0))
        cases.append(dict(cells=cl, world=wn, build=bn, v=8.0, par=pp(base, 8.0, be, ga), des=des,
                          dist=bandnoise(ntk, 1000.0, 0.5, 5.0, 3.0, seed + 6), th0=th100, label="kink100 dither"))
P("  lanes: %d" % len(cases))
res = run_cases(cases, NS, TG, "p2")
json.dump(res, open(os.path.join(HERE, "a8_part2.json"), "w"))
# pair V294 vs cand
key = lambda r: (r["world"], r["label"], r["v"])  # noqa: E731
d294 = {key(r): r for r in res if r["build"] == "V294"}
dc = {key(r): r for r in res if r["build"] == "cand"}
P("  %-12s %-16s %5s | rate peak dB (V294 -> cand) | rate 1-3 Hz | hard 1.6-3 | 3-8 Hz | brk/min | angle mean | idx p50 | slew" % ("world", "scenario", "v"))
flags = []
for k in sorted(d294):
    a, c = d294[k], dc[k]
    P("  %-12s %-16s %5.1f | %+5.1f@%.1f -> %+5.1f@%.1f | %.2f -> %.2f | %.2f -> %.2f | %.2f -> %.2f | %5.1f -> %5.1f | %6.1f -> %6.1f | %3.0f -> %3.0f | %.3f -> %.3f" % (
        k[0], k[1], k[2], a["rate_peak_db"], a["rate_peak_f"], c["rate_peak_db"], c["rate_peak_f"], a["rate13"], c["rate13"],
        a["rate16_3"], c["rate16_3"], a["rate38"], c["rate38"], a["brk_min"], c["brk_min"], a["ang_mean"], c["ang_mean"],
        a["idx_p50"], c["idx_p50"], a["slew"], c["slew"]))
    if c["rate_peak_db"] > a["rate_peak_db"] + 6 and c["rate_peak_db"] > 10:
        flags.append(("D1 line", k))
    if c["rate13"] > 1.3 * a["rate13"] and c["rate13"] > 1.0:
        flags.append(("rate13 x1.3", k, a["rate13"], c["rate13"]))
    if a["brk_min"] > 0 and c["brk_min"] > 3 * a["brk_min"] and c["brk_min"] > 10:
        flags.append(("D4 brk x3", k, a["brk_min"], c["brk_min"]))
P("\nflags:", len(flags))
for f in flags:
    P("  ", f)
out.close()
