# -*- coding: utf-8 -*-
r"""c3_score_time.py -- score the C3 implementations on the PANEL-2 COMMON TIME SCORER, imported unchanged.

ANALYSIS ONLY: builds no image, flashes nothing, sends nothing.  Imports panel2/score_time.py by path, registers the C3
caves as ordinary Cand rows (G's table rows + Kd + E2's ARB policy + ICL 8192) that run through the identical lane
switches the scorer's own G-* and E2-A3 columns already exercise, and runs the scorer's own run/metrics on them.  The
same-batch controls P2, E2-A3, G-P48, G-F24 must reproduce the published SCORE-TIME cells (positive control).  The C3
cave HEX is executed by the scorer's own interpreter (h1) against CandLane.cave_stage -- the function the grid runs.

Caches go to _scratch/angle_loop/c3-synthesis/grid (never the scorer's own cache); the table to this folder.
usage: python c3_score_time.py h1 | run [procs] | report
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3_common as CC  # noqa: E402

_spec = importlib.util.spec_from_file_location("p2_score_time_c3", CC.P2D / "score_time.py")
ST = importlib.util.module_from_spec(_spec)
sys.modules["p2_score_time_c3"] = ST
_spec.loader.exec_module(ST)

ST.OUT = CC.SCR / "grid"
ST.OUT.mkdir(parents=True, exist_ok=True)

ARB = {"A3": ST.ARB_A3, "A2": ST.ARB_A2}
POLNAME = {id(CC.POL_A3): "A3", id(CC.POL_A2): "A2"}
for cid, spec in CC.IMPLS.items():
    arb = ST.ARB_A3 if spec["pol"] is CC.POL_A3 else ST.ARB_A2
    c = ST.Cand(cid, "C3", CC.GROWS[spec["src"]], spec["dop"], spec["kd"], ki=56, icl=spec["icl"], arb=arb,
                hexsrc=str(CC.hexpath(cid)), cave_B=str(len(bytes.fromhex(CC.hexpath(cid).read_text().replace("\n", " ")))),
                note=spec["note"])
    if cid not in ST.CBYID:
        ST.CANDS.append(c)
        ST.CBYID[cid] = c

CTRL = ["P2", "E2-A3", "G-P48", "G-F24"]
IDS = CTRL + list(CC.IMPLS)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "h1":
        for cid in list(CC.IMPLS) + CTRL:
            r = ST.h1(ST.CBYID[cid], N=6000)
            print(f"{cid:8s} code {r.get('code_B')}  mismatches {r['bad']} / {r['n']}  {r.get('first_bad') or ''}",
                  flush=True)
        # negative control: C3-P lane with the WRONG (P2) table in the bytes must mismatch
        gj = json.loads((CC.GD / "g_impls_frozen.json").read_text())
        p2rows = tuple(tuple(r) for r in gj["rev2A-P2"]["rows"])
        bad = replace(ST.CBYID["C3-P"], id="NEG", rows=p2rows)
        bad.hexsrc = ("rows", str(CC.hexpath("C3-P")), CC.GROWS["G-P48"])  # bytes carry G-P48, lane runs P2 rows
        r = ST.h1(bad, N=1500)
        print(f"NEG (P2 rows in the lane, G-P48 rows in the bytes): mismatches {r['bad']} / {r['n']}", flush=True)
    elif cmd == "run":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 12
        ST.run_grid(procs=procs, frame="vgr", scens=ST.SCENS, members=ST.MEMBERS, tag="c3_vgr", cand_ids=IDS)
    elif cmd == "report":
        ST.CANDS[:] = [ST.CBYID[k] for k in IDS]
        S = ST.summarize("c3_vgr")
        L = ST.tables(S, "c3_vgr") + ST.r71b_detail("c3_vgr")
        (HERE / "c3_score_time_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        keep = {}
        for cid, row in S.items():
            keep[cid] = {k: (None if isinstance(v, float) and v != v else v) for k, v in row.items()
                         if not isinstance(v, dict)}
            for bn, _, _ in ST.SBANDS:
                keep[cid][bn] = {k: (v if not isinstance(v, float) or v == v else None) for k, v in row[bn].items()}
        (CC.SCR / "c3_time_summary.json").write_text(json.dumps(keep, default=float, indent=1), encoding="utf-8")
        print("\n".join(L[:60]))


if __name__ == "__main__":
    main()
