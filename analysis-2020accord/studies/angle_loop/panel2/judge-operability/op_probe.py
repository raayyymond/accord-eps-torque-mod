# -*- coding: utf-8 -*-
r"""op_probe.py -- JUDGE OPERABILITY (panel 2, 2026-10-01): operability scenarios the two common scorers did not run.

ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.  It IMPORTS the panel-2 common time scorer
(panel2/score_time.py) by path and reuses its runner, lane (CandLane), plant members, sensors, frame ('vgr') and the
candidate definitions (CBYID) UNCHANGED -- only new scenarios are defined here.  Positive control first: the scorer's
own ov_lt400 / ov_fm2400 are re-run through this script and must reproduce the scorer's published lurch cells.

Scenarios (all in the scorer's conventions: Ah = 0.5 * A_TURN(v), stiff hand 2000 T/deg + 30 T/(deg/s), SIGNED word):
  ctl_lt400 / ctl_fm2400   the scorer's own override (hand takes the wheel Ah -> 0), 1 s hold   [POSITIVE CONTROL]
  xc_lt400  / xc_fm2400    CROSS-CENTRE override: the hand takes the wheel Ah -> -Ah (an evasive move AGAINST the
                           planned curve) over 0.3 s, holds 1 s, releases.  lurch = overshoot past +Ah after release.
  xc3_lt400                the same with a 3 s hold
  crown_<d>                theta_sp = 0 (a straight), a constant road torque d T counts (crown / crosswind) from 1 s,
                           no hand; steady error = mean |theta| over the last 4 s of 16 s; I at the end
  cam30                    wrong-payload (the stock camera's 0xE4 read as an angle on a relay close): theta_sp steps
                           0 -> 30 deg at 1.0 s with request held 1; wheel angle at +0.25 / +0.5 / +1.0 s

usage: python op_probe.py [scn,...]      writes _scratch/angle_loop/judge-operability/op_probe.json
       python op_report.py               then writes judge-operability/op_probe_out.txt from the JSON caches"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np

HERE = Path(__file__).resolve().parent
P2D = HERE.parent
spec = importlib.util.spec_from_file_location("p2_score_time", P2D / "score_time.py")
ST = importlib.util.module_from_spec(spec)
sys.modules["p2_score_time"] = ST
spec.loader.exec_module(ST)

KIT = P2D.parents[3]
OUTJ = KIT / "_scratch" / "angle_loop" / "judge-operability"
OUTJ.mkdir(parents=True, exist_ok=True)

CANDS = ["P2", "F2", "D2a", "B0r", "E1-reset", "E1-cal", "E1-freeze", "E1-bleed", "E2-R1", "E2-S", "E2-A2",
         "E2-A3", "E2-A3-12k", "E2-A2-X", "E2-L", "G-P48d", "G-P44d", "G-P48", "G-F24", "G-A22", "H-A", "H-B"]
MEMBERS = ("nominal", "b_lo*J_hi")
SPEEDS = (3.1, 5.0, 8.0, 10.25, 11.9, 13.0, 15.0, 17.0, 19.0, 22.0, 26.9)


def cols_for(cands, members, speeds):
    return [dict(cand=ST.CBYID[c], cid=c, member=m, v=v) for m in members for v in speeds for c in cands]


def hold_ref_fn(Ah):
    return lambda t: Ah * np.interp(t, [0, 0.5, 1.5, 999], [0, 0, 1, 1])


def ovr_scn(cols, w, target, thold):
    """the scorer's ov_* form, generalised: hand target theta_h = Ah - fr * (Ah - target*Ah)."""
    B = len(cols)
    v = np.array([c["v"] for c in cols])
    Ah = 0.5 * np.array([ST.A_turn(x) for x in v])
    sg = np.sign(Ah)
    tg, tr = 2.5, 0.3
    trel = tg + tr + thold

    def tq(t, th, om):
        if tg <= t < trel:
            return -sg * w * min(1.0, (t - tg) / tr)
        if trel <= t < trel + 0.03:
            return -sg * w * (1 - (t - trel) / 0.03)
        return 0.0 * sg

    def hand(t):
        if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
            return None
        fr = min(1.0, (t - tg) / tr)
        return (np.full(B, 2000.0), np.full(B, 30.0), Ah - fr * (Ah - target * Ah))
    scn = ST.Scn(dur=trel + 3.5, ref=hold_ref_fn(Ah), tq=tq, hand=hand, rec_I=True)
    return scn, dict(t_rel=trel, Ah=Ah)


def ovr_metrics(r, meta):
    th = r["th"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    trel, Ah = meta["t_rel"], meta["Ah"]
    w = tt >= trel
    i_r = int(trel * 1000)
    return dict(lurch=np.max((th[w] - Ah) * np.sign(Ah), 0), th_rel=th[i_r - 1],
                I_rel=r["I"][i_r - 2].astype(float))


def crown_scn(cols, d):
    B = len(cols)
    dd = np.full(B, float(d))
    scn = ST.Scn(dur=16.0, ref=lambda t: np.zeros(B), uext=lambda t: dd * min(1.0, max(0.0, (t - 1.0) / 0.5)),
                 rec_I=True)
    return scn, dict()


def crown_metrics(r, meta):
    th = r["th"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    w = tt >= 12.0
    return dict(err=np.abs(th[w].mean(0)), I_end=r["I"][-2].astype(float), T_end=r["T"][w].astype(float).mean(0))


def cam_scn(cols, amp):
    B = len(cols)
    scn = ST.Scn(dur=3.0, ref=lambda t: np.full(B, amp if t >= 1.0 else 0.0))
    return scn, dict(t0=1.0, amp=amp)


def cam_metrics(r, meta):
    th = r["th"].astype(float)
    T = r["T"].astype(float)
    t0 = int(meta["t0"] * 1000)
    return dict(th025=th[t0 + 250], th050=th[t0 + 500], th100=th[t0 + 1000],
                Tpk=np.abs(T[t0:t0 + 1000]).max(0))


def build(name):
    if name in ("ctl_lt400", "ctl_fm2400", "xc_lt400", "xc_fm2400", "xc3_lt400"):
        w = 400.0 if "lt400" in name else 2400.0
        target = 0.0 if name.startswith("ctl") else -1.0
        thold = 3.0 if name.startswith("xc3") else 1.0
        cols = cols_for(CANDS, MEMBERS, SPEEDS)
        scn, meta = ovr_scn(cols, w, target, thold)
        return cols, scn, meta, ovr_metrics
    if name.startswith("crown_"):
        d = float(name.split("_")[1])
        cols = cols_for(CANDS, ("nominal", "b_lo*J_hi"), (8.0, 11.9, 15.0, 19.0, 22.0, 26.9))
        scn, meta = crown_scn(cols, d)
        return cols, scn, meta, crown_metrics
    if name.startswith("cam"):
        amp = float(name[3:])
        cols = cols_for(CANDS, ("nominal",), (8.0, 12.5, 19.0, 26.9))
        scn, meta = cam_scn(cols, amp)
        return cols, scn, meta, cam_metrics
    raise KeyError(name)


def main(scns, tag="op_probe"):
    res = {}
    lines = []
    for name in scns:
        t0 = time.time()
        cols, scn, meta, mf = build(name)
        r = ST.run(cols, scn, frame="vgr")
        m = mf(r, meta)
        res[name] = [dict(cid=c["cid"], member=c["member"], v=c["v"], **{k: float(m[k][j]) for k in m})
                     for j, c in enumerate(cols)]
        lines.append(f"# {name}: {len(cols)} columns, {time.time() - t0:.0f} s")
        print(lines[-1], flush=True)
    (OUTJ / f"{tag}.json").write_text(json.dumps(res))
    return res


if __name__ == "__main__":
    scns = sys.argv[1].split(",") if len(sys.argv) > 1 else ["ctl_lt400", "ctl_fm2400", "xc_lt400", "xc_fm2400",
                                                             "xc3_lt400", "crown_150", "crown_300", "crown_450",
                                                             "cam30"]
    main(scns)
