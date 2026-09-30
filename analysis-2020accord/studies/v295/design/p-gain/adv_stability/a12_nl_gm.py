# -*- coding: utf-8 -*-
"""a12 -- a NONLINEAR gain margin: in the record-consistent worlds where the positive control WORKS (a10: V293 + rev 2
sustains a 2.7 Hz +-5 deg cycle after a kick, like r71-old), scale the fork's SteerKP by g and find, for V294 vs the
candidate, the smallest g at which a kicked cycle SUSTAINS.  The candidate's margin cost = g*_cand / g*_V294.
Op points: highway straight (26.9 m/s, 0.6 deg), highway curve (26.9 m/s 11 deg), 21.8 m/s 16 deg, 17 m/s 18.4 deg,
12 m/s straight.  Worlds: light_b dynamics with the identified friction x2 (F_hi), (beta, gamma) = (0.75, 0.5), (1, 1),
(1, 0.5)."""
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

out = open(os.path.join(HERE, "a12_nl_gm_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.write(s + "\n")
    out.flush()


b294, _ = A.load(A.IMG_V294, A.SHA_V294)
C294 = A.cells(b294)
CC = A.cells(A.write_candidate(b294))
TG = H.route()["toggles"]
fam = VP.family()
NS = 60.0
nfr, ntk = int(NS * 100), int(NS * 1000)


def fork_curv(theta, v):
    fp = H.ForkPort(1, TG)
    return float(fp.curvature(np.array([theta]), np.array([v]), 0.0)[0])


def bandnoise(nsamp, fs, lo, hi, rms, seed):
    r = np.random.default_rng(seed)
    bb, aa = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    z = signal.lfilter(bb, aa, r.normal(size=nsamp))
    return z * rms / max(np.std(z), 1e-12)


ops = [(26.9, 0.6), (26.9, 11.0), (21.8, 16.0), (17.0, 18.4), (12.0, 0.6)]
worlds = [(0.75, 0.5), (1.0, 1.0), (1.0, 0.5)]
gs = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
res = []
for g in gs:
    tg = dict(TG, steerKp=[[0], [0.9 * g]])
    cases = []
    for v, th in ops:
        kk = fork_curv(th, v) if th > 1 else 0.0
        t = np.arange(nfr) / 100.0
        kick_amp = 0.4 * (fork_curv(11.0, v) if th <= 1 else kk)
        des = np.full(nfr, kk) + np.where((t >= 20) & (t < 23), kick_amp * np.sin(2 * np.pi * 2.3 * t), 0.0)
        for beta, gamma in worlds:
            p = fam["light_b"].at(v)
            q = fam["F_hi"].at(v)
            par = dict(J=p.J * gamma, b=p.b * beta, k=p.k, sat=float(AO.sat_prior(v)), Fc=q.Fc, Fs=q.Fs)
            for bn, cl in (("V294", C294), ("cand", CC)):
                cases.append(dict(v=v, th=th, beta=beta, gamma=gamma, build=bn, cells=cl, par=par, des=des,
                                  dist=bandnoise(ntk, 1000.0, 0.5, 5.0, 5.0, 23)))
    par = {k: np.array([c["par"][k] for c in cases]) for k in ("J", "b", "k", "sat", "Fc", "Fs")}
    par["tau"] = 2
    rec = SIM.run([c["cells"] for c in cases], par, np.array([c["v"] for c in cases]), np.stack([c["des"] for c in cases]),
                  np.stack([c["dist"] for c in cases]), NS, tg, th0=np.array([c["th"] for c in cases]), seed=9)
    for j, c in enumerate(cases):
        post = rec["om"][j, 3000:]
        f, pw = signal.welch(signal.detrend(post), fs=100.0, nperseg=1024)
        band = (f >= 1.0) & (f <= 5.0)
        k = np.flatnonzero(band)[int(np.argmax(pw[band]))]
        res.append(dict(g=g, v=c["v"], th=c["th"], beta=c["beta"], gamma=c["gamma"], build=c["build"],
                        post_rms=float(np.std(post)), f=float(f[k]), ang_pp=float(np.ptp(rec["ang"][j, 3000:]))))
    P("g %.2f done" % g)
json.dump(res, open(os.path.join(HERE, "a12_nl_gm.json"), "w"))
P("\nsmallest SteerKP multiplier g at which a kicked cycle SUSTAINS (post rms > 3 deg/s), V294 vs candidate:")
for v, th in ops:
    for beta, gamma in worlds:
        row = []
        gstar = {}
        for bn in ("V294", "cand"):
            rr = sorted([r for r in res if r["v"] == v and r["th"] == th and r["beta"] == beta and r["gamma"] == gamma
                         and r["build"] == bn], key=lambda r: r["g"])
            s = [r for r in rr if r["post_rms"] > 3.0]
            gstar[bn] = s[0]["g"] if s else float("inf")
            row.append("%s g* %s (%s)" % (bn, ("%.2f @%.2fHz" % (s[0]["g"], s[0]["f"])) if s else ">3",
                                          " ".join("%.1f" % r["post_rms"] for r in rr)))
        P("  v %4.1f th %4.1f b x%.2f J x%.2f: %s | ratio %.2f" % (v, th, beta, gamma, " | ".join(row),
                                                                  gstar["cand"] / gstar["V294"] if np.isfinite(gstar["V294"]) else float("nan")))
out.close()
