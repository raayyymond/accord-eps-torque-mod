# -*- coding: utf-8 -*-
r"""op_merge.py -- JUDGE OPERABILITY (panel 2, 2026-10-01): the GRAFT the frequency and time scorers point to, scored on
the panel-2 common time scorer: G's re-sized D + table (the only firmware-I skeletons that pass the R2 box) carrying E2's
angle-referenced I bound (A3) at ICL 8192 (the only policy that passes every decidable time criterion).

ANALYSIS ONLY.  Imports panel2/score_time.py by path and uses its columns(), scenario(), run(), metrics() UNCHANGED; the
merged columns are ordinary Cand rows (G's rows / Kd + E2's ARB_A3 + ICL), so they run through the identical lane
switches the scorer's own G-* and E2-A3 columns already exercise (both H1-checked against their hex there).
Same-batch references P2, E2-A3, G-P48d, G-P48 must reproduce the scorer's published cells (positive control).
BELIEF: no merged cave hex exists; its bytes would be E2-A3's code with G's table rows (+ the Kd record), unassembled.

usage: python op_merge.py [procs]  -> judge-operability/op_merge_out.txt, _scratch/angle_loop/judge-operability/merge.json
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np

HERE = Path(__file__).resolve().parent
P2D = HERE.parent
_spec = importlib.util.spec_from_file_location("p2_score_time", P2D / "score_time.py")
ST = importlib.util.module_from_spec(_spec)
sys.modules["p2_score_time"] = ST
_spec.loader.exec_module(ST)
KIT = P2D.parents[3]
OUTJ = KIT / "_scratch" / "angle_loop" / "judge-operability"
OUTJ.mkdir(parents=True, exist_ok=True)

# ---- the merged columns (G rows / Kd, E2's A3 bound, raised ICL)
_G = {k: ST.CBYID[k] for k in ("G-P48d", "G-P48", "G-P44d", "G-F24")}
MERGED = [
    replace(_G["G-P48d"], id="M-P48d-A3", fam="M", icl=8192, arb=ST.ARB_A3, hexsrc=None, cave_B="~222",
            note="G-P48d table/Kd 48 + E2-A3 bound, ICL 8192"),
    replace(_G["G-P48"], id="M-P48-A3", fam="M", icl=8192, arb=ST.ARB_A3, hexsrc=None, cave_B="~222",
            note="G-P48 table/Kd 48 + E2-A3 bound, ICL 8192"),
    replace(_G["G-P44d"], id="M-P44d-A3", fam="M", icl=8192, arb=ST.ARB_A3, hexsrc=None, cave_B="~222",
            note="G-P44d table/Kd 44 + E2-A3 bound, ICL 8192"),
    replace(_G["G-F24"], id="M-F24-A3", fam="M", icl=8192, arb=ST.ARB_A3, hexsrc=None, cave_B="~204",
            note="G-F24 table/held Kd 24 (pol-free) + E2-A3 bound, ICL 8192"),
]
for _c in MERGED:
    ST.CBYID[_c.id] = _c
REFS = ["P2", "E2-A3", "G-P48d", "G-P48"]
IDS = REFS + [c.id for c in MERGED]
ST.SPEEDS = (3.1, 5.0, 8.0, 9.0, 10.25, 11.0, 11.9, 12.5, 13.5, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 24.0,
             26.9, 30.0)
SCN = ("rr", "rrq", "th", "s10_02", "s03_02", "ov_lt400", "ov_lt1000", "ov_fm2400", "eng", "cs", "tmos", "hard",
       "st")
MEMBERS = ST.MEMBERS


def job(a):
    s, mb = a
    cands = [ST.CBYID[k] for k in IDS]
    cols = ST.columns(s, mb, cands)
    scn, meta = ST.scenario(s, cols)
    r = ST.run(cols, scn, frame="vgr")
    m = ST.metrics(s, meta, r, cols)
    keys = [dict(id=c["cand"].id, v=c["v"], alat=c.get("alat"), run=c.get("run")) for c in cols]
    out = dict(scn=s, member=mb, keys=keys)
    if s in ("rr", "rrq"):
        X, Y = m.pop("XY")
        m.pop("holds")
        R = ST.r71b_runs()
        out["band"] = [R[k["run"]]["band"] for k in keys]
        out["X"] = [x.tolist() for x in X]
        out["Y"] = [y.tolist() for y in Y]
    out["m"] = {k: np.asarray(x, float).tolist() for k, x in m.items()}
    return out


def slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    xm = x - x.mean()
    return float((xm * (y - y.mean())).sum() / (xm ** 2).sum())


BANDS = (("<8", 0, 7.99), ("8-10", 8, 10), ("10-12.5", 10.01, 12.5), ("12.5-15", 12.51, 15), ("15-22", 15.01, 22),
         (">22", 22.01, 99))
ROWS = (("turn-hold a<=2.0 (min)", "th", "hold", min, "le2"), ("turn-hold a 2.5 (min)", "th", "hold", min, 2.5),
        ("in-phase gain +-1 deg 0.2 Hz (min)", "s10_02", "gain", min, None),
        ("in-phase gain +-0.3 deg 0.2 Hz (min)", "s03_02", "gain", min, None),
        ("dwell-jump events +-1 deg 0.2 Hz (sum)", "s10_02", "dj", sum, None),
        ("light lurch word 400 (max)", "ov_lt400", "lurch", max, None),
        ("light lurch word 1000 (max)", "ov_lt1000", "lurch", max, None),
        ("firm lurch 2400 (max)", "ov_fm2400", "lurch", max, None),
        ("engage droop (max)", "eng", "droop", max, None), ("co-steer droop (max)", "cs", "droop", max, None),
        ("timeout mid-motion excursion (max)", "tmos", "exc", max, None),
        ("hard turn 1.6-3 Hz ratio (max)", "hard", "hard_ratio", max, None),
        ("step overshoot % (max)", "st", "ovs_pct", max, None))


def report(res):
    L = []
    P = L.append
    by = {}
    for r in res:
        by.setdefault(r["scn"], []).append(r)
    for s in ("rr", "rrq"):
        P(f"\n## tracking on r71b paths ({'clean' if s == 'rr' else 'r71b torque word replayed'}): "
          "worst member, 8-15 / 15-22 / >22")
        for cid in IDS:
            vals = []
            for band in ("8-15", "15-22", ">22"):
                w = []
                for r in by[s]:
                    xs = [x for k, x, b in zip(r["keys"], r["X"], r["band"]) if k["id"] == cid and b == band]
                    ys = [y for k, y, b in zip(r["keys"], r["Y"], r["band"]) if k["id"] == cid and b == band]
                    w.append(slope(np.concatenate(xs), np.concatenate(ys)))
                vals.append(min(w))
            P(f"| {cid} | " + " / ".join(f"{v:.3f}" for v in vals) + " |")
    for title, s, key, agg, al in ROWS:
        if s not in by:
            continue
        keys_avail = list(by[s][0]["m"].keys())
        if key not in keys_avail:
            P(f"\n## {title}: key '{key}' absent in {s}; available {keys_avail}")
            continue
        P(f"\n## {title}  [{s}.{key}]\n| cand | " + " | ".join(b[0] for b in BANDS) + " |\n|---|"
          + "---|" * len(BANDS))
        for cid in IDS:
            cells = []
            for nm, lo, hi in BANDS:
                v = []
                for r in by[s]:
                    for k, x in zip(r["keys"], r["m"][key]):
                        if k["id"] != cid or not (lo <= k["v"] <= hi):
                            continue
                        a = k.get("alat")
                        if al == "le2" and not (a in (None, 0.0) or a <= 2.0):
                            continue
                        if isinstance(al, float) and a != al:
                            continue
                        v.append(x)
                cells.append(f"{agg(v):.2f}" if v else "-")
            P(f"| {cid} | " + " | ".join(cells) + " |")
    return "\n".join(L)


if __name__ == "__main__":
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    jobs = [(s, mb) for s in SCN for mb in MEMBERS]
    jobs.sort(key=lambda j: -ST.DUR[j[0]])
    t0 = time.time()
    res = []
    with Pool(procs) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            res.append(r)
            print(f"{i + 1}/{len(jobs)} {r['scn']} {r['member']} {time.time() - t0:.0f} s", flush=True)
    (OUTJ / "merge.json").write_text(json.dumps(res))
    txt = report(res)
    (HERE / "op_merge_out.txt").write_text("# op_merge.py output (frame vgr; worst over members nominal / bc / F_hi / "
                                           "b_lo*J_hi; speeds = ST.SPEEDS above)\n" + txt + "\n", encoding="utf-8")
    print(txt)
