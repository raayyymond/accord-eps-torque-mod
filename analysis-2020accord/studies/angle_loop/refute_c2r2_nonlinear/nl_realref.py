# -*- coding: utf-8 -*-
r"""nl_realref.py -- THE GOAL'S TRACKING METRIC WITH FRICTION, at REALISTIC amplitudes (nonlinear lens, C2 rev 2).
The reference is the r71b route's own measured steering-wheel angle (carState.steeringAngleDeg, engaged, hands not
pressed, runs >= 15 s) per goal band (8-15 / 15-22 / >22 m/s): the angle path a car actually needed on that road.
Each run is one column, simulated at the run's median speed on nl_sim (lane = the listed instructions, cave = the
bytes), and the goal's metric is applied in ANGLE space: OLS slope (with intercept) of the wheel angle on the
reference, both low-passed by a zero-phase 4th-order 0.5 Hz Butterworth, runs concatenated, scored from 4 s into
each run.  Members nominal / bc / F_hi / b_lo*J_hi, and each member's friction-free twin (_nf) as the LINEAR control
(the difference is the nonlinear loss).  Optional: 'frz' = the hands-off torque-word telegraph from route a6
(BELIEF transfer).  ANALYSIS ONLY.
usage: python nl_realref.py [frz]"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_sim as S  # noqa: E402

KIT = HERE.parents[3]
SRC = KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz"
OUT = KIT / "_scratch" / "angle_loop" / "refute-c2r2-nonlinear"
BANDS = ((8.0, 15.0, "8-15"), (15.0, 22.0, "15-22"), (22.0, 99.0, ">22"))
IMPLS = ("P2", "F2", "D2a", "B0r")
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi", "nominal_nf", "bc_nf", "b_lo*J_hi_nf")


def runs():
    d = np.load(SRC)
    t, v, sa, sp = d["t_cst"], d["vego"], d["sa_deg"], d["spress"]
    act = np.interp(t, d["t_cs"], d["cs_active"]) > 0.5
    fs = 1 / np.median(np.diff(t))
    out = {}
    for lo, hi, nm in BANDS:
        m = act & (v >= lo) & (v < hi) & (sp < 0.5)
        e = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
        rr = [(a, b) for a, b in zip(e[::2], e[1::2]) if b - a >= 15 * fs]
        out[nm] = [(t[a:b] - t[a], sa[a:b].copy(), float(np.median(v[a:b]))) for a, b in rr]
    return out


def telegraph_tq(B, seed=7):
    """hands-off torque-word bursts (word 700 = freeze on) with duty by |omega| from route a6 (c1_handsoff_torque):
    <10 deg/s 1.3 %, 10-30 25 %, 30-60 48 %, >60 60 %; bursts U(50, 300) ms.  BELIEF: transfer to this build."""
    rng = np.random.default_rng(seed)
    left = np.zeros(B, int)

    def tq(t, th, om):
        a = np.abs(om)
        d = np.where(a < 10, 0.013, np.where(a < 30, 0.25, np.where(a < 60, 0.48, 0.60)))
        haz = d / ((1 - d) * 175.0)
        on = left > 0
        start = (~on) & (rng.random(B) < haz)
        left[start] = rng.integers(50, 301, int(start.sum()))
        res = np.where(left > 0, 700.0, 0.0)
        left[left > 0] -= 1
        return res
    return tq


def main(frz=False):
    R = runs()
    sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
    lines = [f"# nl_realref: goal tracking metric (angle space, 0.5 Hz LPF, OLS slope) on r71b's own angle paths"
             f"{' + hands-off freeze telegraph (BELIEF)' if frz else ''}"]
    res = {}
    for lo, hi, nm in BANDS:
        rr = R[nm]
        for mem in MEMBERS:
            cols, refs = [], []
            for (tr, sa, vm) in rr:
                for im in IMPLS:
                    cols.append(dict(impl=im, member=mem, v=vm, age=0))
                    refs.append((tr, sa))
            dur = max(tr[-1] for tr, _ in refs) + 0.5
            fr_t = np.arange(0, dur, 0.01)
            REF = np.stack([np.interp(fr_t, tr, sa, right=sa[-1]) for tr, sa in refs], 1)
            th0 = REF[0].copy()

            def ref(t, REF=REF):
                return REF[min(int(round(t * 100)), REF.shape[0] - 1)]
            scn = S.Scn(dur=dur, ref=ref, th0=th0, tq=(telegraph_tq(len(cols)) if frz else None))
            t0 = time.time()
            r = S.run(cols, scn)
            th100 = r["th"][::10].astype(float)
            for ii, im in enumerate(IMPLS):
                X, Y = [], []
                for q, (tr, sa) in enumerate([x[:2] for x in rr]):
                    j = q * len(IMPLS) + ii
                    nlen = int(tr[-1] * 100)
                    x = signal.sosfiltfilt(sos, REF[:nlen, j])
                    y = signal.sosfiltfilt(sos, th100[:nlen, j])
                    X.append(x[400:]), Y.append(y[400:])
                X, Y = np.concatenate(X), np.concatenate(Y)
                b = np.linalg.lstsq(np.vstack([X, np.ones_like(X)]).T, Y, rcond=None)[0]
                res[(nm, mem, im)] = float(b[0])
            lines.append(f"band {nm:>5s} {mem:14s} " + " ".join(f"{im} {res[(nm, mem, im)]:.3f}" for im in IMPLS)
                         + f"   ({len(rr)} runs, {sum(x[0][-1] for x in rr):.0f} s, sim {time.time() - t0:.0f} s)")
            print(lines[-1], flush=True)
    txt = "\n".join(lines) + "\n"
    (OUT / f"realref{'_frz' if frz else ''}.txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main(frz=len(sys.argv) > 1 and sys.argv[1] == "frz")
