# -*- coding: utf-8 -*-
"""panel_time.py -- the time-domain gates for Designer A (fewest bytes), A1 and A2, on the nominal and bc plants.
Built on harness_time (the exact 1 kHz sim, byte-exact LaneVec, Coulomb/stiction plant, 100 Hz holds, quantisers).
ANALYSIS ONLY.  Fixed seeds.

A1 = re-key (Kp(v), Kd(v) speed-keyed records) + flat Ki.
A2 = A1 + a speed-scheduled Ki (delivered per-speed; the cave supplies Ki(v)).

bc = the credible-set friction world: b_lo's damping with Coulomb x2 (x1.3 at 8 m/s), per c1_members' bc definition.

Gates (per speed band): stick-slip events, dwell-then-jump, dead zone, tracking 0.2/0.5 Hz, turn-hold, override release
lurch (light hand |tq|<=1000 AND firm hand), engage droop / ramp-in, sentinel pulse, 5-30 Hz texture.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1]), str(HERE.parents[2] / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import panel_schedules as PS   # noqa: E402
import harness_time as HT      # noqa: E402
import v294_plant as VP        # noqa: E402

OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "panel" / "A-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)
SPEEDS = (3.0, 8.0, 12.5, 17.0, 26.0)        # one per band (low / <8 edge / mid / highway-low / highway)
FAM = VP.family()


class _BC:
    """bc member: b_lo plant with Coulomb x2 (x1.3 at 8 m/s), per the credible set."""
    def at(self, v):
        import dataclasses
        p = FAM["b_lo"].at(float(v))
        sc = 1.3 if abs(v - 8.0) < 0.6 else 2.0
        return dataclasses.replace(p, Fc=p.Fc * sc, Fs=p.Fs * sc)


BC = _BC()


def rows_for(v):
    """two configs at this speed: A1 (full Kp, flat Ki 80) and A2 (0.72x Kp, Ki(v)=0.5 Kp).  Both speed-keyed Kp(v)
    and Kd(v) (the re-key), guard A2 (ramp!=0 AND request) on."""
    kx = PS.KP_X
    dx = PS.KD_X
    a1 = HT.row(0, kpX=kx, kpY=PS.KP_Y, kdX=dx, kdY=PS.KD_SCHED, key="speed", Ki=PS.ki_of(v, "A1"),
                ICL=4096, DB=0, label="A1 re-key flatKi")
    a1["guard_and"] = True
    a2 = HT.row(0, kpX=kx, kpY=PS.KP_Y_A2, kdX=dx, kdY=PS.KD_SCHED, key="speed", Ki=PS.ki_of(v, "A2"),
                ICL=4096, DB=0, label="A2 re-key Ki(v)")
    a2["guard_and"] = True
    return [a1, a2]


def score(member, tag):
    SC = ("rh", "s02", "s05", "ssm", "ov_fade")
    results = {}
    for v in SPEEDS:
        cfg = HT.Cfg(rows_for(v))
        for nm in SC:
            scn = HT.scenario(nm, v)
            r = HT.run(scn, cfg, member, v, seed=11)
            results[(nm, v)] = HT.metrics(nm, scn, r, v)
        print(f"  [{tag} v={v} done]", flush=True)
    # assemble the per-speed gate view (the two columns are A1, A2)
    print("\n" + "=" * 112)
    print(f"  TIME GATES on the {tag} plant   (col 0 = A1 flat Ki, col 1 = A2 Ki(v))")
    print("=" * 112)
    hdr = (f"{'v':>5} | {'impl':>4} | {'dj(02/05/ssm)':>13} {'slips(rh)':>9} | {'ess_turn':>8} {'ssm_fit':>7} | "
           f"{'tg02':>5} {'tg05':>5} {'hold':>5} | {'ovLurchT':>8} {'ovSwing':>7} | {'texP2P/line':>11} | {'sen_T':>6}")
    print(hdr)
    rows_out = {}
    for v in SPEEDS:
        for j, impl in enumerate(("A1", "A2")):
            rh = results[("rh", v)]; st = results[("st", v)]
            s02 = results[("s02", v)]; s05 = results[("s05", v)]; ssm = results[("ssm", v)]
            ov = results[("ov_fade", v)]; sen = results[("sen_L16", v)]
            dj = int(s02["dj_events"][j] + s05["dj_events"][j] + ssm["dj_events"][j])
            slips = int(rh["hold_slips"][j])
            ess = float(rh["ess_turn"][j]); fit = float(ssm["fit_gain"][j])
            tg02 = float(s02["track_gain"][j]); tg05 = float(s05["track_gain"][j])
            hold = float(rh["hold_ratio"][j])
            ovT = float(ov["lurch_peakT"][j]); ovS = float(ov["lurch_swing"][j])
            tex = float(max(s02["T_hf"][j], s05["T_hf"][j], ssm["T_hf"][j]))
            senT = float(sen["sen_peakT"][j])
            print(f"{v:5.1f} | {impl:>4} | {dj:13d} {slips:9d} | {ess:8.2f} {fit:7.2f} | "
                  f"{tg02:5.2f} {tg05:5.2f} {hold:5.2f} | {ovT:8.0f} {ovS:7.2f} | {tex:11.2f} | {senT:6.0f}")
            rows_out[(v, impl)] = dict(dj=dj, slips=slips, ess=ess, fit=fit, tg02=tg02, tg05=tg05, hold=hold,
                                       ovT=ovT, ovS=ovS, tex=tex, senT=senT, peakT=float(rh["peakT"][j]))
    return rows_out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    allout = {}
    if which in ("nominal", "both"):
        allout["nominal"] = score(FAM["nominal"], "nominal")
    if which in ("bc", "both"):
        allout["bc"] = score(BC, "bc")
    (OUT / "time_gates.json").write_text(json.dumps({f"{k}|{vv}|{ii}": d for k, rr in allout.items()
                                                     for (vv, ii), d in rr.items()}, default=float))
    print("\nwrote", OUT / "time_gates.json")
