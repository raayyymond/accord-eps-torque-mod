# -*- coding: utf-8 -*-
"""a10 -- make the nonlinear sim's POSITIVE CONTROL work (a8 part 1 FAILED: from 5 T road noise nothing limit-cycles, the
light_b plant mostly sticks at Fs 52 T).  r71-old's cycle was +-6 deg, cmd +-300 counts: a LARGE-amplitude cycle, which
Coulomb/static friction can hide at small amplitude (hard excitation).  Test: kick every lane (a 3 s burst of 2.3 Hz
des_curv modulation, +-40 % of the curve, at t = 30 s) and read the LAST 30 s: does the cycle SUSTAIN?
Worlds: light_b dynamics with (i) the prior friction (Fc 31.5 / Fs 52.5 T) and (ii) the identified friction at speed x2
(F_hi: Fc ~12 / Fs ~16 T at 21.8 m/s), b x beta, J x gamma for the a7 record-consistent (beta, gamma).
Builds: V293 + fork rev 2 (the r71-old configuration: must SUSTAIN), V294 + r1 (r71b: must not), cand + r1."""
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

out = open(os.path.join(HERE, "a10_posctrl_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.write(s + "\n")
    out.flush()


b294, _ = A.load(A.IMG_V294, A.SHA_V294)
C294 = A.cells(b294)
CC = A.cells(A.write_candidate(b294))
C293 = dict(C294, fb_clamp=0)
TG = H.route()["toggles"]
TG_REV2 = dict(TG, steerKp=[[0], [0.85]])
fam = VP.family()
NS = 70.0
nfr, ntk = int(NS * 100), int(NS * 1000)


def fork_curv(theta, v):
    fp = H.ForkPort(1, TG)
    return float(fp.curvature(np.array([theta]), np.array([v]), 0.0)[0])


def bandnoise(nsamp, fs, lo, hi, rms, seed):
    r = np.random.default_rng(seed)
    bb, aa = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    z = signal.lfilter(bb, aa, r.normal(size=nsamp))
    return z * rms / max(np.std(z), 1e-12)


def line(sig):
    f, p = signal.welch(signal.detrend(sig), fs=100.0, nperseg=1024)
    band = (f >= 1.0) & (f <= 5.0)
    k = np.flatnonzero(band)[int(np.argmax(p[band]))]
    sh = ((f >= 0.5) & (f < 1.0)) | ((f > 5.0) & (f <= 8.0))
    c = np.polyfit(np.log(f[sh]), np.log(p[sh] + 1e-30), 1)
    return float(f[k]), float(10 * np.log10(p[k] / np.exp(np.polyval(c, np.log(f[k])))))


cases = []
for v, th in ((21.8, 22.0), (21.8, 16.0), (26.9, 11.0), (17.0, 18.4)):
    kk = fork_curv(th, v)
    t = np.arange(nfr) / 100.0
    kick = np.where((t >= 30) & (t < 33), 0.4 * np.sin(2 * np.pi * 2.3 * t), 0.0)
    des = kk * (1 + kick)
    for fric in ("prior", "idF_hi"):
        for beta, gamma in ((1.0, 1.0), (1.0, 0.5), (1.25, 1.0), (0.75, 0.5)):
            p = fam["light_b"].at(v)
            if fric == "prior":
                Fc, Fs = p.Fc, p.Fs
            else:
                q = fam["F_hi"].at(v)
                Fc, Fs = q.Fc, q.Fs
            par = dict(J=p.J * gamma, b=p.b * beta, k=p.k, sat=float(AO.sat_prior(v)), Fc=Fc, Fs=Fs)
            for bn, cl, tgn in (("V293+rev2", C293, "rev2"), ("V294+r1", C294, "r1"), ("cand+r1", CC, "r1"),
                                ("V294+rev2", C294, "rev2"), ("cand+rev2", CC, "rev2")):
                cases.append(dict(v=v, th=th, fric=fric, beta=beta, gamma=gamma, build=bn, cells=cl, tg=tgn, par=par,
                                  des=des, dist=bandnoise(ntk, 1000.0, 0.5, 5.0, 5.0, 17)))
res = []
for tgn, tg in (("rev2", TG_REV2), ("r1", TG)):
    sub = [c for c in cases if c["tg"] == tgn]
    par = {k: np.array([c["par"][k] for c in sub]) for k in ("J", "b", "k", "sat", "Fc", "Fs")}
    par["tau"] = 2
    rec = SIM.run([c["cells"] for c in sub], par, np.array([c["v"] for c in sub]), np.stack([c["des"] for c in sub]),
                  np.stack([c["dist"] for c in sub]), NS, tg, th0=np.array([c["th"] for c in sub]), seed=5)
    for j, c in enumerate(sub):
        om = rec["om"][j]
        post = om[4000:]                     # 40-70 s: 7 s after the kick ended
        pre = om[1500:3000]
        f1, db1 = line(post)
        r = dict(v=c["v"], th=c["th"], fric=c["fric"], beta=c["beta"], gamma=c["gamma"], build=c["build"],
                 pre_rms=float(np.std(pre)), post_rms=float(np.std(post)), post_f=f1, post_db=db1,
                 kick_rms=float(np.std(om[3000:3300])), ang_pp=float(np.ptp(rec["ang"][j, 4000:])),
                 cmd_pp=float(np.ptp(rec["cmd"][j, 4000:])))
        res.append(r)
json.dump(res, open(os.path.join(HERE, "a10_posctrl.json"), "w"))
P("sustained-after-kick test (post = 40-70 s; the kick ended at 33 s). SUSTAINED = post rate rms > 3 deg/s with a 1-5 Hz line")
for r in sorted(res, key=lambda r: (r["fric"], r["beta"], r["gamma"], r["v"], r["th"], r["build"])):
    sus = r["post_rms"] > 3.0 and r["post_db"] > 6
    P("  %-6s b x%.2f J x%.2f v %4.1f th %4.1f %-10s: pre %.2f | kick %.1f | post %.2f deg/s line %.2f Hz %+.1f dB | angle p-p %.1f | cmd p-p %.0f %s" % (
        r["fric"], r["beta"], r["gamma"], r["v"], r["th"], r["build"], r["pre_rms"], r["kick_rms"], r["post_rms"], r["post_f"],
        r["post_db"], r["ang_pp"], r["cmd_pp"], "SUSTAINED" if sus else ""))
out.close()
