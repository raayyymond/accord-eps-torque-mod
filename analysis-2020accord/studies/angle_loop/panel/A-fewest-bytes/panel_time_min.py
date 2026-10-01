# -*- coding: utf-8 -*-
"""panel_time_min.py -- minimal nonlinear time gates for A1/A2 that complete under CPU contention.
nominal + bc, speeds 3 (low-speed friction) / 12.5 (mid) / 17 (highway turn-hold), scenarios rh/s02/ov_fade.
ANALYSIS ONLY, fixed seed.  Prints per (plant, speed, impl) and writes JSON."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1]), str(HERE.parents[2] / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import panel_schedules as PS   # noqa
import harness_time as HT      # noqa
import v294_plant as VP        # noqa
import dataclasses
OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "panel" / "A-fewest-bytes"
FAM = VP.family()
SPEEDS = (3.0, 12.5, 19.0)        # low-speed friction / mid / highway (all in harness_time.A_TURN)


class BC:
    def at(self, v):
        p = FAM["b_lo"].at(float(v))
        sc = 1.3 if abs(v - 8.0) < 0.6 else 2.0
        return dataclasses.replace(p, Fc=p.Fc * sc, Fs=p.Fs * sc)


def rows_for(v):
    kx, dx = PS.KP_X, PS.KD_X
    a1 = HT.row(0, kpX=kx, kpY=PS.KP_Y, kdX=dx, kdY=PS.KD_SCHED, key="speed", Ki=PS.ki_of(v, "A1"), ICL=4096, DB=0)
    a2 = HT.row(0, kpX=kx, kpY=PS.KP_Y_A2, kdX=dx, kdY=PS.KD_SCHED, key="speed", Ki=PS.ki_of(v, "A2"), ICL=4096, DB=0)
    a1["guard_and"] = a2["guard_and"] = True
    return [a1, a2]


def go(member, tag):
    out = {}
    for v in SPEEDS:
        cfg = HT.Cfg(rows_for(v))
        res = {}
        for nm in ("rh", "s02", "ov_fade"):
            scn = HT.scenario(nm, v)
            res[nm] = HT.metrics(nm, scn, HT.run(scn, cfg, member, v, seed=11), v)
        for j, impl in enumerate(("A1", "A2")):
            rh, s02, ov = res["rh"], res["s02"], res["ov_fade"]
            d = dict(hold=float(rh["hold_ratio"][j]), ess_turn=float(rh["ess_turn"][j]),
                     dj=int(s02["dj_events"][j]), slips=int(rh["hold_slips"][j]),
                     stick_pct=float(s02["stick_pct"][j]), tg02=float(s02["track_gain"][j]),
                     hard16=float(rh["hard16"][j]), hard16_ref=float(rh["hard16_ref"][j]),
                     tex=float(max(s02["T_hf"][j], rh["T_hf"][j])), ovT=float(ov["lurch_peakT"][j]),
                     ovSwing=float(ov["lurch_swing"][j]), peakT=float(rh["peakT"][j]))
            out[f"{tag}|{v}|{impl}"] = d
            print(f"  {tag} v{v:5.1f} {impl}: hold {d['hold']:.2f} ess {d['ess_turn']:.2f} dj {d['dj']} slips {d['slips']} "
                  f"stick% {d['stick_pct']:.1f} tg02 {d['tg02']:.2f} hard16 {d['hard16']:.2f}/{d['hard16_ref']:.2f} "
                  f"tex {d['tex']:.2f} ovT {d['ovT']:.0f} ovSwing {d['ovSwing']:.2f}", flush=True)
    return out


if __name__ == "__main__":
    allout = {}
    allout.update(go(FAM["nominal"], "nom"))
    allout.update(go(BC(), "bc"))
    (OUT / "time_min.json").write_text(json.dumps(allout, default=float))
    print("wrote", OUT / "time_min.json", flush=True)
