# -*- coding: utf-8 -*-
r"""e1_track.py -- the GOAL'S TRACKING METRIC on the operator's own r71b angle paths, for each E1 policy, using the
nonlinear refuter's own reference set (nl_realref.runs()) and the controlled E1 engine (e1_control.run_e1 -- == nl_sim
at baseline).  The metric is the OLS slope (angle space, 0.5 Hz LPF) of the simulated wheel angle on the r71b reference,
per goal band (8-15 / 15-22 / >22 m/s).  Bar: 0.95-1.05.  ANALYSIS ONLY."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_control as EC
import e1_lane as E1
import e1_policies as EP
import nl_realref as RR
import nl_sim as NS

OUT = E1.KIT / "_scratch" / "angle_loop" / "E1-integral-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)
POLS = ("P2base", "E1a", "E1a_fz384", "E1a_fz320", "E1b", "E1d")
MEMBERS = ("nominal", "b_lo*J_hi")
IMPLS = ("P2", "F2")


def reaction_tq(B, seed=7):
    """hands-off REACTION torque telegraph: |tq| word bursts landing in the bleed band (256-512), with the a6 duty by
    |omega| (<10 deg/s 1.3 %, 10-30 25 %, 30-60 48 %, >60 60 %), bursts 50-300 ms, magnitude ~350 (a6 p90-p95 at speed).
    This tests whether a bleed/freeze at 256-512 would drain I during hands-off holds (BELIEF transfer to this build)."""
    rng = np.random.default_rng(seed)
    left = np.zeros(B, int)

    def tq(t, th, om):
        a = np.abs(om)
        d = np.where(a < 10, 0.013, np.where(a < 30, 0.25, np.where(a < 60, 0.48, 0.60)))
        haz = d / ((1 - d) * 175.0)
        start = (left <= 0) & (rng.random(B) < haz)
        left[start] = rng.integers(50, 301, int(start.sum()))
        res = np.where(left > 0, 350.0, 0.0)
        left[left > 0] -= 1
        return res
    return tq


def main(pols=POLS, members=MEMBERS, frz=False):
    R = RR.runs()
    sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
    tag = "_frz" if frz else ""
    lines = [f"# E1 goal tracking metric (angle space, 0.5 Hz LPF, OLS slope) on r71b's own paths; bar 0.95-1.05"
             f"{' + hands-off reaction-torque telegraph (a6 duty, BELIEF)' if frz else ''}"]
    res = {}
    t0 = time.time()
    for lo, hi, nm in RR.BANDS:
        rr = R[nm]
        if not rr:
            continue
        for mem in members:
            cols, refs, keys = [], [], []
            for (tr, sa, vm) in rr:
                for pname in pols:
                    pol = EP.POLICIES[pname]
                    for im in IMPLS:
                        cols.append(dict(impl=im, member=mem, v=vm, age=0, pol=pol))
                        refs.append((tr, sa))
                        keys.append((pname, im))
            dur = max(tr[-1] for tr, _ in refs) + 0.5
            fr_t = np.arange(0, dur, 0.01)
            REF = np.stack([np.interp(fr_t, tr, sa, right=sa[-1]) for tr, sa in refs], 1)
            th0 = REF[0].copy()

            def ref(t, REF=REF):
                return REF[min(int(round(t * 100)), REF.shape[0] - 1)]
            tqf = reaction_tq(len(cols)) if frz else None
            scn = NS.Scn(dur=dur, ref=ref, th0=th0, tq=tqf)
            r = EC.run_e1(cols, scn)
            th100 = r["th"][::10].astype(float)
            ncols = len(pols) * len(IMPLS)
            for ci, (pname, im) in enumerate([(p, i) for p in pols for i in IMPLS]):
                X, Y = [], []
                for q, (tr, sa, vm) in enumerate(rr):
                    j = q * ncols + ci
                    nlen = int(tr[-1] * 100)
                    X.append(signal.sosfiltfilt(sos, REF[:nlen, j])[400:])
                    Y.append(signal.sosfiltfilt(sos, th100[:nlen, j])[400:])
                X, Y = np.concatenate(X), np.concatenate(Y)
                b = np.linalg.lstsq(np.vstack([X, np.ones_like(X)]).T, Y, rcond=None)[0][0]
                res[(nm, mem, pname, im)] = float(b)
            lines.append(f"band {nm:>5s} {mem:11s} " + "  ".join(f"{p}:{res[(nm, mem, p, 'P2')]:.3f}" for p in pols))
            print(lines[-1], flush=True)
    json.dump({"|".join(map(str, k)): v for k, v in res.items()}, open(OUT / f"track{tag}.json", "w"))
    (OUT / f"track{tag}_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"done {time.time()-t0:.0f}s")


if __name__ == "__main__":
    frz = len(sys.argv) > 1 and sys.argv[1] == "frz"
    main(pols=("P2base", "E1a", "E1d"), members=("nominal",), frz=frz)
