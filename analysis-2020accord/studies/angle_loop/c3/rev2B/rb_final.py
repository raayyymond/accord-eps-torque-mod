# -*- coding: utf-8 -*-
r"""rb_final.py -- the FINAL C3 rev2-B design (C3B-P primary, C3B-F fallback) on the PANEL-2 COMMON scorers, imported
unchanged.  Ki 40, GB tables (G >= 512), A3 bound + opposing-hand freeze sgn 300.  (The op-skip is inert in every goal
scenario, so the _score cave is scored; the flight cave adds the +2-byte op-skip, Ghidra-decoded.)

Scorers are loaded at MODULE level so the multiprocessing Pool workers (spawn) can re-import them.

usage:
  python rb_final.py h1          -- the _score cave bytes vs the common TIME scorer's cave_stage (fresh + held)
  python rb_final.py time [p]    -- the goal time grid
  python rb_final.py timereport
  python rb_final.py freq        -- the common FREQUENCY GATE-2 scorer (R2 box, M20, Re(T/w))
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "panel"))
sys.path.insert(0, str(AL / "c1"))
sys.path.insert(0, str(HERE))
import rb_table as T  # noqa: E402

SCR = AL.parents[2] / "_scratch" / "angle_loop" / "c3-rev2B"
PSC = str(HERE / "c3b_cave_C3B-P_score.hex")
FSC = str(HERE / "c3b_cave_C3B-F_score.hex")
KI = 40

# ---- load the common TIME scorer at module level ----
_st = importlib.util.spec_from_file_location("p2_st_rbf", AL / "panel2" / "score_time.py")
ST = importlib.util.module_from_spec(_st)
sys.modules["p2_st_rbf"] = ST
_st.loader.exec_module(ST)
ST.OUT = SCR / "grid"
ST.OUT.mkdir(parents=True, exist_ok=True)
for _c in [
    ST.Cand("C3B-P", "RBF", tuple(T.GB_P), "fresh", 48, ki=KI, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
            hexsrc=PSC, cave_B="240", note="rev2B primary: Ki40, GB-P, A3+sgn300 (flight +2B op-skip)"),
    ST.Cand("C3B-F", "RBF", tuple(T.GB_F), "held", 24, ki=KI, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
            hexsrc=FSC, cave_B="220", note="rev2B fallback: Ki40, GB-F, A3+sgn300, held D (F3 declared)"),
]:
    if _c.id not in ST.CBYID:
        ST.CANDS.append(_c)
        ST.CBYID[_c.id] = _c

# ---- load the common FREQUENCY scorer at module level, with C3B specs ----
_sf = importlib.util.spec_from_file_location("p2_sf_rbf", AL / "panel2" / "score_freq.py")
SF = importlib.util.module_from_spec(_sf)
sys.modules["p2_sf_rbf"] = SF
_sf.loader.exec_module(SF)
SF.OUT = SCR / "freq"
SF.OUT.mkdir(parents=True, exist_ok=True)
_orig_build = SF.build_cands


def _build_cands():
    base = _orig_build()
    keep = [c for c in base if c.cid in ("P2", "F2", "D2a", "B0r", "H-A", "H-B", "G-A22", "E2-K0", "G-P48", "G-F24")]
    Spec = SF.Spec
    return keep + [
        Spec("C3B-P", "RBF", list(T.GB_P), 48, ki=KI, dkind="fresh", src="c3b_cave_C3B-P.hex", note="rev2B primary"),
        Spec("C3B-F", "RBF", list(T.GB_F), 24, ki=KI, dkind="held", src="c3b_cave_C3B-F.hex", note="rev2B fallback"),
    ]


SF.build_cands = _build_cands
TIME_IDS = ["P2", "E2-A3", "C3B-P", "C3B-F"]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "h1"
    if cmd == "h1":
        for cid in ("C3B-P", "C3B-F"):
            r = ST.h1(ST.CBYID[cid], N=8000)
            print(f"{cid}: h1 {r['bad']}/{r['n']} code {r.get('code_B')}", flush=True)
    elif cmd == "time":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 12
        ST.run_grid(procs=procs, frame="vgr", scens=ST.SCENS, members=ST.MEMBERS, tag="rbf", cand_ids=TIME_IDS)
    elif cmd == "timereport":
        ST.CANDS[:] = [ST.CBYID[k] for k in TIME_IDS]
        S = ST.summarize("rbf")
        L = ST.tables(S, "rbf") + ST.r71b_detail("rbf")
        (HERE / "rbf_score_time_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        print("\n".join(L[:62]))
    elif cmd == "freq":
        SF.run(quick=False)


if __name__ == "__main__":
    main()
