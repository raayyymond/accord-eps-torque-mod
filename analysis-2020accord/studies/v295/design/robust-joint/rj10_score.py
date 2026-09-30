# -*- coding: utf-8 -*-
"""rj10_score.py -- lens robust-joint, STAGE 3: the harness's full score() (M_SAFE, M_LOOP incl. stress members, M_HF,
M_TRACK closed form + mode A literal + probe + flatness, M_DRIVE outer + mode B lp/full) on the finalists, each with
V294 in the same batch.  Default plants (nominal, b_lo, F_hi, J_hi, light_b, tau6) + the stress members in M_LOOP/M_HF.
Writes rj10_score_<name>.json and rj10_score_<name>.txt (print_score).  ANALYSIS ONLY."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402


def main(which):
    spec = {"F1": (1.0, 1.95), "F3": (1.2, 1.95), "F2": (1.1, 1.95), "F6": (1.2, 2.5)}
    for nm in which:
        g, t = spec[nm]
        c = RC.make(g=g, t=t, name=nm, allow_opcode=False)
        r = H.score(c)
        json.dump(H.to_jsonable(r), open(os.path.join(HERE, "rj10_score_%s.json" % nm), "w"), indent=1)
        with open(os.path.join(HERE, "rj10_score_%s.txt" % nm), "w", encoding="utf-8") as f:
            H.print_score(r, file=f)
        print("done %s hash %s runtime %.0f s" % (nm, r["meta"]["hash"][:16], r["meta"]["runtime_s"]), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["F1", "F3"])
