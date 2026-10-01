# -*- coding: utf-8 -*-
r"""c3_score_freq.py -- score the C3 implementations on the PANEL-2 COMMON FREQUENCY SCORER, imported unchanged.

ANALYSIS ONLY.  Imports panel2/score_freq.py by path; replaces its build_cands() with one that returns the C3 specs
plus the controls the scorer's validate() needs (P2, F2, D2a, B0r, H-A) and the two skeletons C3 inherits (G-P48,
G-F24, G-P48d, G-P44).  The linear loop is unchanged by the integral policy, so C3-P's PID row IS G-P48's and C3-F's
IS G-F24's BY CONSTRUCTION; this run is the EVIDENCE that the common scorer agrees.  Every number is the scorer's own.

The C3 policy block acts only through FREEZE states = the scorer's I-frozen ("PD") loop, which it already computes.
usage: python c3_score_freq.py    (full run; tables + summary in _scratch/angle_loop/panel2-score, same as the scorer)
       python c3_score_freq.py quick
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3_common as CC  # noqa: E402

_spec = importlib.util.spec_from_file_location("p2_score_freq_c3", CC.P2D / "score_freq.py")
SF = importlib.util.module_from_spec(_spec)
sys.modules["p2_score_freq_c3"] = SF
_spec.loader.exec_module(SF)

_orig_build = SF.build_cands


def build_cands_c3():
    cands = _orig_build()
    byid = {c.cid: c for c in cands}
    # validate()/report() reference these by id: keep them all, plus the two skeletons C3 inherits
    keep = ["P2", "F2", "D2a", "B0r", "H-A", "H-B", "G-A22", "E2-K0", "G-P48", "G-F24", "G-P48d", "G-P44"]
    base = [byid[k] for k in keep if k in byid]
    Spec = SF.Spec
    c3 = []
    for cid, spec in CC.IMPLS.items():
        dk = "held" if spec["dop"] == "held" else "fresh"
        c3.append(Spec(cid, "C3", list(CC.GROWS[spec["src"]]), spec["kd"], ki=56, dkind=dk,
                       src=f"c3_cave_{cid}.hex", note=spec["note"]))
    return base + c3


SF.build_cands = build_cands_c3
SF.OUT = CC.SCR / "freq"                      # my own dir: never overwrite the shared panel-2 frequency cache
SF.OUT.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    SF.run(quick=(cmd == "quick"))
