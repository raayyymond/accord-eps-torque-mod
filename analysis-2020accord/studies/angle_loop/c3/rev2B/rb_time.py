# -*- coding: utf-8 -*-
r"""rb_time.py -- C3 rev2-B on the PANEL-2 COMMON TIME SCORER (panel2/score_time.py), imported unchanged.

The Ki/table question (F1 + N2): register C3B-P / C3B-F with the rev2-B tables (G >= 512) at Ki 20 / 24 / 28, THETA
bound (A3), fresh/held D.  Controls C3-P / E2-A3 / P2 must reproduce the published SCORE-TIME cells.  This isolates
whether turn-hold and tracking survive the lower Ki; the setpoint-bound (N1) is scored separately in rb_n1.py.

usage: python rb_time.py h1 | run [procs] | report
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "panel"))
sys.path.insert(0, str(AL / "c1"))
sys.path.insert(0, str(HERE))
import rb_table as T  # noqa: E402

_spec = importlib.util.spec_from_file_location("p2_score_time_rb", AL / "panel2" / "score_time.py")
ST = importlib.util.module_from_spec(_spec)
sys.modules["p2_score_time_rb"] = ST
_spec.loader.exec_module(ST)

SCR = AL.parents[2] / "_scratch" / "angle_loop" / "c3-rev2B"
ST.OUT = SCR / "grid"
ST.OUT.mkdir(parents=True, exist_ok=True)

C3P = str(AL / "c3" / "c3_cave_C3-P.hex")
C3F = str(AL / "c3" / "c3_cave_C3-F.hex")


def reg():
    rb = []
    for ki in (36, 40, 44, 48, 56):
        rb.append(ST.Cand(f"C3B-P-k{ki}", "RB", tuple(T.GB_P), "fresh", 48, ki=ki, icl=8192, arb=ST.ARB_A3,
                          hexsrc=("rows", C3P, tuple(T.GB_P)), cave_B="222", note=f"rev2B P, Ki {ki}, GB-P table"))
        rb.append(ST.Cand(f"C3B-F-k{ki}", "RB", tuple(T.GB_F), "held", 24, ki=ki, icl=8192, arb=ST.ARB_A3,
                          hexsrc=("rows", C3F, tuple(T.GB_F)), cave_B="204", note=f"rev2B F, Ki {ki}, GB-F table"))
    for c in rb:
        if c.id not in ST.CBYID:
            ST.CANDS.append(c)
            ST.CBYID[c.id] = c
    return [c.id for c in rb]


RBIDS = reg()
CTRL = ["P2", "E2-A3", "G-P48"]
IDS = CTRL + RBIDS


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "h1":
        for cid in RBIDS:
            r = ST.h1(ST.CBYID[cid], N=5000)
            print(f"{cid:12s} mism {r['bad']}/{r['n']}", flush=True)
    elif cmd == "run":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 14
        ST.run_grid(procs=procs, frame="vgr", scens=ST.SCENS, members=ST.MEMBERS, tag="rb_vgr2", cand_ids=IDS)
    elif cmd == "report":
        ST.CANDS[:] = [ST.CBYID[k] for k in IDS]
        S = ST.summarize("rb_vgr2")
        L = ST.tables(S, "rb_vgr2") + ST.r71b_detail("rb_vgr2")
        (HERE / "rb_score_time_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        print("\n".join(L[:70]))


if __name__ == "__main__":
    main()
