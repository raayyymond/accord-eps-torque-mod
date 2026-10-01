# -*- coding: utf-8 -*-
"""JUDGE GOAL (panel 2, 2026-10-01): score the GRAFTS the judge proposes on the COMMON time scorer, unchanged.
Imports analysis-2020accord/studies/angle_loop/panel2/score_time.py as is (no edit), registers graft columns as new
Cand rows (the scorer's own per-column switches: G table + Kd + D operand, ICL, E2's angle-referenced bound), and runs
the scorer's own run/summarize/tables on them with in-batch CONTROL columns (P2, E2-A3, G-P48, G-P44) whose numbers
must reproduce SCORE-TIME-2026-10-01.md.  Caches go to _scratch/angle_loop/judge-goal/grid (never the scorer's own cache); tables to this folder.
ANALYSIS ONLY: builds no image, flashes nothing, sends nothing.
usage: python judge_grafts.py h1 | run [procs] | report"""
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent                       # .../panel2/JUDGE-goal (scripts + small outputs)
_d = HERE
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
KIT = _d.parent                                              # repo root (analysis-2020accord carries .pkgroot)
P2D = KIT / "analysis-2020accord" / "studies" / "angle_loop" / "panel2"
SCR = KIT / "_scratch" / "angle_loop" / "judge-goal"         # grid caches + the summary json (gitignored)
SCR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(P2D))
import score_time as ST  # noqa: E402

ST.OUT = SCR / "grid"
ST.OUT.mkdir(parents=True, exist_ok=True)
E2D = P2D / "E2-integral-most-margin"
GD = P2D / "G-d-operand-and-margins"
gj = json.loads((GD / "g_impls_frozen.json").read_text())
gr = {k: tuple(tuple(r) for r in v["rows"]) for k, v in gj.items()}
A3HEX = E2D / "e2_cave_A3.hex"

GRAFTS = [
    # id, G rows, D operand, Kd, ICL, hexsrc (E2's A3 cave with the G table rows substituted; held D has no such hex)
    ("J-G48-A3", "G-P48", "fresh", 48, 8192, True),
    ("J-G48-A3-12k", "G-P48", "fresh", 48, 12288, True),
    ("J-G44-A3", "G-P44", "fresh", 44, 8192, True),
    ("J-G48d-A3", "G-P48d", "fresh", 48, 8192, True),
    ("J-F24-A3", "G-F24", "held", 24, 8192, False),
]
for gid, src, dop, kd, icl, hx in GRAFTS:
    c = ST.Cand(gid, "J", gr[src], dop, kd, icl=icl, arb=ST.ARB_A3,
                hexsrc=(("rows", A3HEX, gr[src]) if hx else None),
                cave_B=("222" if hx else "~204"), note=f"graft: {src} skeleton + E2-A3 policy, ICL {icl}")
    if gid not in ST.CBYID:
        ST.CANDS.append(c)
        ST.CBYID[gid] = c

CTRL = ["P2", "E2-A3", "G-P48", "G-P44"]
IDS = CTRL + [g[0] for g in GRAFTS]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "h1":
        for cid in IDS:
            r = ST.h1(ST.CBYID[cid], N=3000)
            print(cid, r.get("code_B"), "mismatches", r["bad"], "/", r["n"], r.get("first_bad") or "", flush=True)
        # negative control: the graft decision with the WRONG table on the right bytes must fail
        bad = replace(ST.CBYID["J-G48-A3"], id="NEG-wrongtable", rows=gr["rev2A-P2"])
        bad.hexsrc = ("rows", A3HEX, gr["G-P48"])
        r = ST.h1(bad, N=1500)
        print("NEG (P2 rows in the lane, G-P48 rows in the bytes): mismatches", r["bad"], "/", r["n"], flush=True)
    elif cmd == "run":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 12
        ST.run_grid(procs=procs, frame="vgr", scens=ST.SCENS, members=ST.MEMBERS, tag="judge_vgr", cand_ids=IDS)
    elif cmd == "bridge":                      # the refuter's / E2's 3 s-hold override bridge (ov3_*), frame vgr
        ST.run_grid(procs=12, frame="vgr", scens=("ov3_lt400", "ov3_lt511", "ov3_fm2400"), members=ST.MEMBERS,
                    tag="judge_vgr_ov3", cand_ids=IDS)
        D = ST.load_grid("judge_vgr_ov3")
        L = ["| cand | word 400: nom / bc / F_hi / b_lo*J_hi | word 511 | firm 2400 | (max over 8-30 m/s, deg) |",
             "|---|---|---|---|---|"]
        for cid in IDS:
            cells = [" / ".join(f"{ST.agg(D, sn, 'lurch', cid, 8.0, 30.0, 'max', members=(mb,)):.1f}"
                                for mb in ST.MEMBERS) for sn in ("ov3_lt400", "ov3_lt511", "ov3_fm2400")]
            lo = [f"{ST.agg(D, sn, 'lurch', cid, 0.0, 7.99, 'max'):.1f}" for sn in ("ov3_lt400", "ov3_fm2400")]
            L.append(f"| {cid} | " + " | ".join(cells) + f" | <8 m/s light/firm {lo[0]} / {lo[1]} |")
        txt = chr(10).join(L) + chr(10)
        (HERE / "judge_bridge_ov3.md").write_text(txt, encoding="utf-8")
        print(txt)
    elif cmd == "report":
        ST.CANDS[:] = [ST.CBYID[k] for k in IDS]
        S = ST.summarize("judge_vgr")
        L = ST.tables(S, "judge_vgr") + ST.r71b_detail("judge_vgr")
        (HERE / "judge_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        keep = {}
        for cid, row in S.items():
            keep[cid] = {k: (None if isinstance(v, float) and v != v else v) for k, v in row.items()
                         if not isinstance(v, dict)}
            for bn, _, _ in ST.SBANDS:
                keep[cid][bn] = {k: (v if not isinstance(v, float) or v == v else None)
                                 for k, v in row[bn].items() if k in ("th20", "th25", "g_s10_02", "g_s03_02",
                                                                     "lurch_light", "lurch_firm", "eng_droop",
                                                                     "cs_droop", "rn_thf", "c30_thf", "hunt_n",
                                                                     "tmos_dev", "sen_T50", "hard", "dj10", "fails")}
        (SCR / "judge_summary.json").write_text(json.dumps(keep, default=float, indent=1), encoding="utf-8")
        print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
