# -*- coding: utf-8 -*-
"""ds_final.py -- the D-structure CANDIDATES (one source of truth for their parameters), and the pipeline that scores
every one of them the same way.  ANALYSIS ONLY.  Fixed seeds.

  python ds_final.py env      full-grid gated envelope (the brief's credible set + the 20 Hz rules) per candidate
  python ds_final.py fit      the integer cave table per candidate (>= 4 % under its own envelope, the C1 knot speeds)
  python ds_final.py gate     GATE 2 on the full grid, every member (gated + report), exact GM on the gated members
  python ds_final.py retw     Re(T/w) 5-25 Hz worst over 1-35 m/s, hold age 0 and 10, vs V294 / V295 / V282
  python ds_final.py track    the goal's own tracking metric (c1r2_trackmetric weights) + 0.2/0.5 Hz proxies
  python ds_final.py time     the time harness on nominal and bc (ds_time), every candidate in one batch
  python ds_final.py all
Outputs: _scratch/angle_loop/D-structure/*.json and panel/D-structure/final_<step>.txt"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace, asdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as M  # noqa: E402
import ds_gate2 as G2  # noqa: E402
import c1_lib as C  # noqa: E402

KNOTS = [3.1, 8.0, 10.0, 11.75, 15.5, 17.5, 26.9]          # the C1 lib knot speeds (comparable tables)

CANDS = {
    "B0": M.Des("B0 = C1r2 structure (P+I on angle, D on HELD rate, Kd 20), C1 lib table"),
    "B0r": M.Des("B0r = the C1r2 structure REFITTED to the brief's credible set (its own envelope, the same knots)"),
    "D1a": M.Des("D1a = stock D on the angle error (cal-only D), Kd_E 256", dsrc="E", kd=256),
    "D1b": M.Des("D1b = D on the 1 kHz motor-accumulator difference (gp-0x6cc4), K_D 20", dsrc="op", dop="fine",
                 kd=72, dop_k=8),
    "D1c": M.Des("D1c = D on the held-angle difference through a 21 Hz low-pass, K_D 20", dsrc="op", dop="held_lp",
                 kd=250, dop_k=8, lp_beta=1 / 8),
    "D2a": M.Des("D2a = D on the FRESH 1 kHz motor-rate EMA (gp-0x6abe), K_D 20", dsrc="op", dop="fresh_rate", kd=34),
    "D2b": M.Des("D2b = D2a + FORWARD-path output-lag lead (zero 5.2 Hz, pole 10.3 Hz) on E' for P", lead="fwd",
                 lead_beta=1 / 16, lead_kh=1, dsrc="op", dop="fresh_rate", kd=34),
    "D2c": M.Des("D2c = D2a + FEEDBACK-path output-lag lead (same filter) on r26", lead="fb", lead_beta=1 / 16,
                 lead_kh=1, dsrc="op", dop="fresh_rate", kd=34),
    "D3a": M.Des("D3a = cascade: V282-style HELD rate loop inside (fb 923/1560, Kp 24, Ki 12), angle outside", kind="cascade",
                 kp=24, ki=12, ka=4.0, dsrc="none"),
    "D3b": M.Des("D3b = cascade: FRESH rate loop inside (gp-0x6abe via E1', fb 923/1560, Kp 46, Ki 12), angle outside",
                 kind="cascade", kp=46, ki=12, ka=4.0, dsrc="none", cop="fresh"),
}
B0_TABLE = C.c1_table()                                       # c1_lib default ('r2' lib, 7 knots)


def tables():
    p = G2.OUT / "final_tables.json"
    return {k: [tuple(r) for r in v] for k, v in json.loads(p.read_text()).items()} if p.exists() else {}


def P_(lines):
    def P(s=""):
        print(s, flush=True)
        lines.append(s)
    return P


def step_env(redo=False):
    out = {}
    for k, des in CANDS.items():
        f = G2.OUT / f"env_final_{k}.json"
        if f.exists() and not redo:
            d = json.loads(f.read_text())
            out[k] = dict(env=d["env"], bind=d["bind"])
            continue
        t0 = time.time()
        e = G2.envelope(des, members=G2.GATED, grid=G2.GRID, tag=f"final_{k}")
        out[k] = dict(env=e["env"], bind=e["bind"])
        print(f"{k}: envelope {time.time() - t0:.0f} s", flush=True)
    (G2.OUT / "final_env.json").write_text(json.dumps(out))


def step_fit():
    env = json.loads((G2.OUT / "final_env.json").read_text())
    lines = []
    P = P_(lines)
    tb = {}
    for k in CANDS:
        e = {float(v): g for v, g in env[k]["env"].items()}
        if k == "B0":
            tb[k] = B0_TABLE
        else:
            tbl, Gk = G2.fit_table(e, KNOTS)
            tb[k] = tbl
        P(f"{k}: table {tb[k]}")
        P("   v:  " + " ".join(f"{v:5.2f}" for v in (3.1, 5, 8, 10, 11.75, 12.5, 15, 17, 19, 22, 26.9, 30)))
        P("   G:  " + " ".join(f"{G2.G_at(v, tb[k]):5d}" for v in (3.1, 5, 8, 10, 11.75, 12.5, 15, 17, 19, 22, 26.9, 30)))
        P("   env:" + " ".join(f"{e[min(e, key=lambda q: abs(q - v))]:5.0f}" for v in (3.1, 5, 8, 10, 11.75, 12.5, 15, 17,
                                                                                      19, 22, 26.9, 30)))
        worst = min(e[v] / max(G2.G_at(v, tb[k]), 1) for v in G2.GRID)
        P(f"   min envelope/G over the grid {worst:.3f}" + ("   (B0: the C1 lib table, NOT refitted)" if k == "B0" else ""))
    (G2.OUT / "final_tables.json").write_text(json.dumps({k: [list(r) for r in v] for k, v in tb.items()}))
    (HERE / "final_fit.txt").write_text("\n".join(lines), encoding="utf-8")


def step_gate(only=None):
    tb = tables()
    lines = []
    P = P_(lines)
    allfails = {}
    for k, des in CANDS.items():
        if only and k not in only:
            continue
        res, sec = G2.full_gate(des, tb[k], tag=f"final_{k}")
        fl = G2.fails(res)
        allfails[k] = fl
        P("=" * 150)
        P(f"{k}: {des.name}   [{sec:.0f} s, {len(res)} points]  GATED FAILS: {len(fl)}")
        for f in fl[:30]:
            P(f"   FAIL {f}")
        G2.summarize(res, P)
    tag = "_".join(only) if only else "all"
    (HERE / f"final_gate_{tag}.txt").write_text("\n".join(lines), encoding="utf-8")  # final_gate.txt = all tags joined
    (G2.OUT / f"final_fails_{tag}.json").write_text(json.dumps(allfails, default=str))


def step_retw():
    tb = tables()
    lines = []
    P = P_(lines)
    fr = (5, 7, 10, 13, 15, 17, 20, 25)
    out = {}
    for k, des in CANDS.items():
        r = G2.re_tw_table(des, tb[k], freqs=fr)
        out[k] = r
        for ea in (0, 10):
            if k == "B0":
                for nm in ("V294", "V295", "V282"):
                    P(f"{nm:5s} age {ea:2d}         " + "".join(f"{x:+8.2f}" for x in r[ea][nm]))
            P(f"{k:5s} age {ea:2d} worst   " + "".join(f"{x:+8.2f}" for x in r[ea]["worst"]) + "   at v " +
              " ".join(f"{x:g}" for x in r[ea]["at_v"]))
    P("Hz:                 " + "".join(f"{f:8d}" for f in fr))
    (HERE / "final_retw.txt").write_text("\n".join(lines), encoding="utf-8")
    (G2.OUT / "final_retw.json").write_text(json.dumps(out))


def step_track():
    import c1r2_trackmetric as TM
    tb = tables()
    lines = []
    P = P_(lines)
    mems = ("nominal", "b_lo", "b_hi", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi", "ms_free")
    P("goal tracking factor (the kit scorer's slope through the r71b-weighted inner T_ref) per member; then 0.2 / 0.5 Hz "
      "|T_ref|<phase and the 1.6-3 Hz |T_ref| peak, nominal")
    for k, des in CANDS.items():
        P(f"--- {k}: {des.name}")
        for v in (8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0):
            G = float(G2.G_at(v, tb[k]))
            vals = []
            for m in mems:
                pl, d, ea, _ = G2.member(m, v)
                dd = replace(des, G=G, d=d, extra_age=ea)

                def Tf(f, dd=dd, pl=pl):
                    return M.loop_frf(dd, pl, np.asarray(f, float))["Tr"]
                vals.append(TM.slope(Tf, v))
            pl, d, ea, _ = G2.member("nominal", v)
            r = M.loop_frf(replace(des, G=G, d=d), pl, np.array([0.2, 0.5]))["Tr"]
            r163 = M.metrics(replace(des, G=G, d=d), pl)["Tr163"]
            P(f"  v {v:5.1f} G {int(G):5d}: " + " ".join(f"{m[:9]}={x:.3f}" for m, x in zip(mems, vals)) +
              f" | min {min(vals):.3f} | 0.2Hz {abs(r[0]):.2f}<{np.degrees(np.angle(r[0])):+.0f} 0.5Hz "
              f"{abs(r[1]):.2f}<{np.degrees(np.angle(r[1])):+.0f} | Tr1.6-3 {r163:.2f}")
    (HERE / "final_track.txt").write_text("\n".join(lines), encoding="utf-8")


def lane_cfgs():
    import ds_selftest as ST
    tb = tables()
    cfgs, labels = [], []
    for k, des in CANDS.items():
        c = ST.lane_cfg(des, tb[k])
        cfgs.append(c)
        labels.append(k)
    return cfgs, labels


def step_time(members=("nominal", "bc"), speeds=(3.0, 5.0, 8.0, 10.0, 12.5, 15.0, 19.0, 26.0, 30.0)):
    import ds_time as DT
    cfgs, labels = lane_cfgs()
    scens = ("rh", "s02", "s05", "ssm", "st", "ov_fade", "ov_latch", "ov_light400", "ov_light1000", "sen_L16",
             "sen_R16", "dis_meas", "dis_zero", "eng_load")
    DT.run_suite(cfgs, labels, members, speeds, scens, tag="final")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "gate" and len(sys.argv) > 2:
        step_gate(sys.argv[2].split(","))
        sys.exit(0)
    for s_, fn in (("env", step_env), ("fit", step_fit), ("gate", step_gate), ("retw", step_retw),
                   ("track", step_track), ("time", step_time)):
        if which in (s_, "all"):
            t0 = time.time()
            fn()
            print(f"[{s_}: {time.time() - t0:.0f} s]", flush=True)
