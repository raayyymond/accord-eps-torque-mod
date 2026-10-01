# -*- coding: utf-8 -*-
r"""e2_k0.py -- POLICY (iii): NO FIRMWARE I (Ki 0xC63E6 stays V295's 0; the cave's freeze block is deleted) with the DC
supplied by a FORK angle integral at tau_o >= 1 s (the refuters' stability floor), P = P2's.  The fork model: every
0xE4 frame (100 Hz) the fork sends theta_sp = theta_plan + acc, acc += (theta_plan - theta_meas) * 0.01 / tau_o, where
theta_meas is the 0x14A angle the fork saw 60 ms earlier (the measured round trip, STATE / the brief).  The integral is
frozen when |wire torque| > 1200 (BELIEF: the fork's steeringPressed threshold for this car is not re-read here) and is
otherwise free -- so a light hand winds it, as it would the firmware I.  One column per job (the reference depends on
the column's own angle).  On the common time scorer (score_time.run, the tq_cols hook records the angle).  ANALYSIS
ONLY.  This is FORK CODE beyond the angle interface; it is evaluated because the brief asks for it, not proposed.
usage: python e2_k0.py   (writes _scratch/.../exp_k0.json and e2_k0_out.txt)"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_exp as X  # noqa: E402
from e2_common import ST, OUT  # noqa: E402
import e2_lane as EL  # noqa: E402

DELAY = 6          # frames (60 ms)


class ForkInt:
    def __init__(self, plan, tau_o, word_fn=None, press=1200.0):
        self.plan, self.tau, self.word_fn, self.press = plan, tau_o, word_fn, press
        self.hist = []
        self.acc = 0.0
        self.th = 0.0

    def tq_cols(self, t, pl, tq, hh):
        self.th = float(pl.th[0])
        w = float(tq) if self.word_fn is None else float(self.word_fn(t, pl, hh))
        self.w = w
        return np.array([int(round(w))], np.int64)

    def ref(self, t):
        self.hist.append(self.th)
        meas = self.hist[max(len(self.hist) - 1 - DELAY, 0)]
        p = float(self.plan(t))
        if abs(getattr(self, "w", 0.0)) * 125 / 128 <= self.press:
            self.acc += (p - meas) * 0.01 / self.tau
        return p + self.acc


def k0_col():
    c = X.col(ki=0)
    return c


def job(args):
    kind, spec, tau, mem = args
    t0 = time.time()
    if kind == "th":
        v, tgt = spec
        base = X.scn_turnhold(v, tgt)
    elif kind == "rr":
        band, i = spec
        base = X.scn_realref(band, i, False)
        v = base["v"]
    elif kind == "lh":
        v, w = spec
        base = X.scn_light_word(v, w)
    else:
        raise KeyError(kind)
    v = base["v"]
    if tau is None:                                   # reference column: P2 itself, no fork integral
        scn = base
        cols = [X.col()]
    else:
        fi = ForkInt(base["ref"], tau, word_fn=(lambda t, pl, hh, f=base["tq"]: f(t)) if base.get("tq") else None)
        scn = dict(base, ref=fi.ref, tq_cols=fi.tq_cols)
        cols = [k0_col()]
    r = ST.run(scn, cols, [], mem, v, lane_cls=EL.E2Lane)
    th = r["th"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    out = dict(kind=kind, spec=list(spec), tau=tau, member=mem, sec=time.time() - t0)
    if kind == "th":
        w = (tt >= 9.0) & (tt < 11.0)
        out["hold"] = float(th[w, 0].mean() / spec[1])
        out["hold4"] = float(th[(tt >= 3.5) & (tt < 4.0), 0].mean() / spec[1])   # 2 s after the ramp ends
    elif kind == "rr":
        n = base["nlen"]
        sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
        out["x"] = signal.sosfiltfilt(sos, base["REF"][:n])[400:].tolist()
        out["y"] = signal.sosfiltfilt(sos, th[::10][:n, 0])[400:].tolist()
    elif kind == "lh":
        import harness_time as HT
        m = HT.metrics("ov_fade", base, r, v)
        out["lurch"] = float(np.asarray(m["lurch_overshoot"])[0])
    return out


def main():
    R = X.r71b_runs()
    jobs = []
    for mem in ("nominal", "b_lo*J_hi"):
        for tau in (None, 1.0, 2.0):
            for v in (8.0, 10.0, 11.75, 15.0, 17.0, 19.0, 22.0, 26.9):
                for a in (1.5, 2.5):
                    jobs.append(("th", (v, float(min(a * X.L_WB * X.SR_C / v ** 2 * 57.29578, 90.0))), tau, mem))
            for b in R:
                for i in range(len(R[b])):
                    jobs.append(("rr", (b, i), tau, mem))
            for v in (8.0, 11.75, 19.0, 26.9):
                jobs.append(("lh", (v, 400), tau, mem))
    t0 = time.time()
    res = []
    with Pool(3) as pool:
        for i, x in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            res.append(x)
            if (i + 1) % 20 == 0:
                print(f"  k0: {i + 1}/{len(jobs)} {time.time() - t0:.0f} s", flush=True)
    (OUT / "exp_k0.json").write_text(json.dumps(res))
    summarize(res)


def summarize(res=None):
    res = res or json.loads((OUT / "exp_k0.json").read_text())
    L = ["# e2_k0: policy (iii) Ki 0 + fork angle integral (tau_o); 'P2' = the reference (Ki 56, no fork integral)"]
    for mem in ("nominal", "b_lo*J_hi"):
        for tau in (None, 1.0, 2.0):
            lab = "P2" if tau is None else f"K0 tau_o {tau:.0f} s"
            th = [x for x in res if x["kind"] == "th" and x["member"] == mem and x["tau"] == tau]
            th.sort(key=lambda x: (x["spec"][1] > 0, x["spec"][0]))
            L.append(f"{mem:10s} {lab:12s} turn-hold (8 s hold, last 2 s) min {min(x['hold'] for x in th):.3f}; "
                     f"2 s after ramp min {min(x['hold4'] for x in th):.3f}")
            for band in ("8-15", "15-22", ">22"):
                rr = [x for x in res if x["kind"] == "rr" and x["member"] == mem and x["tau"] == tau and x["spec"][0] == band]
                if rr:
                    Xc = np.concatenate([x["x"] for x in rr])
                    Yc = np.concatenate([x["y"] for x in rr])
                    b = np.linalg.lstsq(np.vstack([Xc, np.ones_like(Xc)]).T, Yc, rcond=None)[0][0]
                    L.append(f"{'':10s} {lab:12s} r71b goal metric band {band:>5s}: {b:.3f}")
            lh = [x for x in res if x["kind"] == "lh" and x["member"] == mem and x["tau"] == tau]
            L.append(f"{'':10s} {lab:12s} light-hand (word 400, 3 s) lurch max {max(x['lurch'] for x in lh):.2f} deg "
                     + " ".join(f"{x['spec'][0]:g}:{x['lurch']:.2f}" for x in sorted(lh, key=lambda x: x['spec'][0])))
    txt = "\n".join(L)
    print(txt)
    (HERE / "e2_k0_out.txt").write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sum":
        summarize()
    else:
        main()
