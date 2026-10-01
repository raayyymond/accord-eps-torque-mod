# -*- coding: utf-8 -*-
"""CONTROL: my independent lane+plant (nl_sim) vs the designers' engine (rev2-A score_time.run = ds_time/DSLane/PlantVec)
on identical deterministic inputs (sensor noise 0 in both).  Agreement = my simulation is a faithful re-implementation;
disagreement = adjudicate.  ANALYSIS ONLY."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "c2" / "rev2A"))
import os
os.chdir(str(HERE.parent / "c2" / "rev2A"))
import r2a_common as R   # noqa
import importlib.util
_sp = importlib.util.spec_from_file_location('r2a_score_time', str(HERE.parent / 'c2' / 'rev2A' / 'score_time.py'))
ST = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(ST)  # rev2-A's common scorer
import ds_time as DT     # noqa
import harness_time as HT  # noqa
import nl_sim as S       # noqa
DT.N4F50 = 0.0
S.N4F50 = 0.0
tabs = R.tables()
impls = ["P2", "F2"]
cfgs = [R.lane_cfg(k, tabs[k]) for k in impls]
for (nm, v, mem) in (("rh", 11.9, "nominal"), ("s02", 17.0, "b_lo*J_hi"), ("ov_light400", 10.0, "bc"), ("tmo", 26.9, "F_hi")):
    scn = ST.scenario(nm, v)
    rD = ST.run(scn, cfgs, [], mem, v)
    A = HT.A_TURN[v]
    hand = scn.get("hand")
    tqf = scn.get("tq")
    cols = [dict(impl=k, member=mem, v=v) for k in impls]
    st_ = {}
    def handf(t, hand=hand, st_=st_):
        if hand is None:
            return None
        n = int(round(t * 1000))
        n0, nr, nramp = int(round(hand["t0"] * 1000)), int(round(hand["t_rel"] * 1000)), int(round(hand["tramp"] * 1000))
        if not (n0 <= n < nr):
            return None
        if n == n0:
            st_["g"] = st_["pl"].th.copy()
        fr = min(1.0, (n - n0) / nramp)
        return (np.full(2, hand["Kh"]), np.full(2, hand["Bh"]), st_["g"] + fr * hand["delta"])
    ev = []
    for (t, k) in scn.get("events", []):
        ev.append((t, {"fault": "fault"}.get(k, k)))
    if nm == "tmo":
        ev.append((scn["t_stop"], "stop"))
    sc = S.Scn(dur=scn["dur"], ref=lambda t, f=scn["ref"]: float(f(np.array(t))),
               tq=(None if tqf is None else (lambda t, th, om, f=tqf: float(f(np.array(t))))),
               hand=(handf if hand is not None else None), events=tuple(ev))
    # need the plant handle for the grab angle: wrap run
    orig = S.Plant.__init__
    def init(self, cols, orig=orig):
        orig(self, cols); st_["pl"] = self
    S.Plant.__init__ = init
    rM = S.run(cols, sc)
    S.Plant.__init__ = orig
    dth = np.abs(rM["th"] - rD["th"]).max(0)
    dT = np.abs(rM["T"].astype(int) - rD["T"].astype(int)).max(0)
    print(f"{nm:12s} v {v:5.1f} {mem:10s}: max|dtheta| {dth} deg, max|dT| {dT} counts")
