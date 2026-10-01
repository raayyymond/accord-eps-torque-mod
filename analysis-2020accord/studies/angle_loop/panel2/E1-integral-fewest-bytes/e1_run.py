# -*- coding: utf-8 -*-
r"""e1_run.py -- run the E1 integral-policy implementations through the controlled nonlinear engine, with every policy x
impl x member as a COLUMN in one simulation per (scenario, speed, a_lat) (E1Lane is vectorised over per-column policies;
CONTROL e1_control: == nl_sim at the baseline policy).

Scenarios:
  turnhold  hold ratio over the last 2 s of an 8 s hold; curve theta = a*L*SR/v^2 (L 2.83, SR 16).
  lurch     override: a stiff hand grabs at 2.5 s, pulls the wheel 0.5*hold off over 0.3 s, holds 1 s, releases.
            word 400 (LIGHT, below the 512 freeze -> I winds) and 2400 (FIRM, above freeze -> frozen/reset).
            metric = max overshoot past the setpoint after release (deg).
  engage    engage while the driver holds a curve (fork sends measured angle, hand lets go) -> droop.

usage: python e1_run.py turnhold | lurch | engage | all
ANALYSIS ONLY."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_control as EC
import e1_lane as E1
import e1_policies as EP
import nl_sim as NS

OUT = E1.KIT / "_scratch" / "angle_loop" / "E1-integral-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)
L, SR = 2.83, 16.0

POLS = ("P2base", "E1a", "E1a_6k", "E1a_noreset", "E1b", "E1b_noreset", "E1c", "E1d")
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
IMPLS = ("P2", "F2")


def grid(members, v):
    """build the column list (policy x impl x member) for one speed; returns (cols, keys)."""
    cols, keys = [], []
    for pname in POLS:
        pol = EP.POLICIES[pname]
        for mem in members:
            for im in IMPLS:
                cols.append(dict(impl=im, member=mem, v=v, age=0, pol=pol))
                keys.append((pname, mem, im))
    return cols, keys


def turnhold(speeds, alats=(1.0, 1.5, 2.0), members=MEMBERS):
    res = {}
    for v in speeds:
        cols, keys = grid(members, v)
        for a in alats:
            tgt = a * L * SR / v ** 2 * 180 / np.pi
            scn = NS.Scn(dur=11.0, ref=lambda t, tg=tgt: tg * np.interp(t, [0, 0.5, 2.0, 99], [0, 0, 1, 1]))
            r = EC.run_e1(cols, scn)
            th = r["th"].astype(float)
            tt = np.arange(th.shape[0]) * 1e-3
            w = (tt >= 9.0) & (tt < 11.0)
            ratio = th[w].mean(0) / tgt
            for j, k in enumerate(keys):
                res["|".join(map(str, k + (v, a)))] = float(ratio[j])
        print(f"  turnhold v{v} done", flush=True)
    json.dump(res, open(OUT / "turnhold.json", "w"))
    return res


def lurch(speeds, members=MEMBERS, words=(400, 2400)):
    res = {}
    for v in speeds:
        a = 1.5
        Ah = a * L * SR / v ** 2 * 180 / np.pi
        tg, tramp, thold = 2.5, 0.3, 1.0
        trel = tg + tramp + thold
        cols, keys = grid(members, v)
        B = len(cols)
        for word in words:
            def ref(t, Ah=Ah, B=B):
                return Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1]) * np.ones(B)

            def hand(t, Ah=Ah, tg=tg, tramp=tramp, trel=trel, B=B):
                # a firm override that pulls the wheel from the hold fully off (toward 0), the refuter's ov delta = -Ah
                if t < tg or t >= trel:
                    return None
                fr = min(1.0, (t - tg) / tramp)
                target = Ah - fr * Ah
                return (np.full(B, 2000.0), np.full(B, 30.0), np.full(B, target))

            def tq(t, th, om, word=word, tg=tg, trel=trel, tramp=tramp, B=B):
                if tg <= t < trel:
                    return np.full(B, float(word) * min(1.0, (t - tg) / tramp))
                if trel <= t < trel + 0.03:
                    return np.full(B, float(word) * (1 - (t - trel) / 0.03))
                return np.zeros(B)

            scn = NS.Scn(dur=trel + 3.0, ref=ref, hand=hand, tq=tq)
            r = EC.run_e1(cols, scn)
            th = r["th"].astype(float)
            sp = r["sp"].astype(float) / 40.0
            tt = np.arange(th.shape[0]) * 1e-3
            w = tt >= trel
            over = np.max((th[w] - sp[w]) * np.sign(Ah), axis=0)
            for j, k in enumerate(keys):
                res["|".join(map(str, k + (v, word)))] = float(over[j])
        print(f"  lurch v{v} done", flush=True)
    json.dump(res, open(OUT / "lurch.json", "w"))
    return res


def engage(speeds, members=MEMBERS):
    res = {}
    th0map = {5.0: 25.0, 8.0: 15.0, 10.0: 10.0, 11.9: 7.0, 12.5: 6.0, 15.0: 4.0, 17.0: 3.5, 19.0: 2.5, 22.0: 2.0,
              26.9: 1.5, 30.0: 1.2}
    for v in speeds:
        th0 = th0map.get(v, 5.0)
        TE, lag = 2.0, 0.3
        cols, keys = grid(members, v)
        B = len(cols)

        def hand(t, th0=th0, TE=TE, lag=lag, B=B):
            if t < TE + lag:
                return (np.full(B, 2000.0), np.full(B, 30.0), np.full(B, th0))
            fr = min(1.0, (t - TE - lag) / 0.2)
            if fr >= 1.0:
                return None
            return (np.full(B, 2000.0 * (1 - fr)), np.full(B, 30.0 * (1 - fr)), np.full(B, th0))

        scn = NS.Scn(dur=TE + 5.0, ref=lambda t: 0.0, hand=hand, th0=np.full(B, th0), mode0="off",
                     events=[(TE, "engage")], sp_meas_until=TE + 0.011, sp_hold_from=TE + 0.011)
        r = EC.run_e1(cols, scn)
        th = r["th"].astype(float)
        sp = r["sp"].astype(float) / 40.0
        tt = np.arange(th.shape[0]) * 1e-3
        w = tt >= TE
        droop = np.max((sp[w] - th[w]) * np.sign(th0), axis=0)
        for j, k in enumerate(keys):
            res["|".join(map(str, k + (v,)))] = float(droop[j])
        print(f"  engage v{v} done", flush=True)
    json.dump(res, open(OUT / "engage.json", "w"))
    return res


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    sp_th = (8.0, 10.0, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9)
    if w in ("turnhold", "all"):
        turnhold(sp_th)
        print(f"turnhold done {time.time()-t0:.0f}s", flush=True)
    if w in ("lurch", "all"):
        lurch((8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0))
        print(f"lurch done {time.time()-t0:.0f}s", flush=True)
    if w in ("engage", "all"):
        engage((8.0, 10.0, 12.5, 17.0, 26.9))
        print(f"engage done {time.time()-t0:.0f}s", flush=True)
