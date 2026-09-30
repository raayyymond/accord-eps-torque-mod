# -*- coding: utf-8 -*-
"""s5_score.py -- the shared harness score() on this lens's candidate(s), V294 in the same batch (default plants + stress
members in M_LOOP / M_HF), written to s5_score_<name>.json and s5_score_<name>_out.txt.
usage: python s5_score.py b1134 | g3sh1 | a1017g2 | b1701"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

BASE = H.Cells.v294()
CANDS = {
    "b1134": BASE.replace(name="V295tr_b1134", fb_b=1134),                                          # G 2.0, cal-only
    "g3sh1": BASE.replace(name="V295tr_G3_sh1", fb_b=850, e_shift=1, kp_y=(1920,) * 5, fb_clamp=512),  # G 3.0, shl 1
    "a1017g2": BASE.replace(name="V295tr_a1017_G2_sh1", fb_a=1017, fb_b=567, e_shift=1, kp_y=(1920,) * 5, fb_clamp=512),
    "b1701": BASE.replace(name="V295tr_b1701", fb_b=1701),                                          # G 3.0, cal-only, margin 1.35
    "b964": BASE.replace(name="V295tr_b964", fb_b=964),                                             # G 1.70, cal-only (THE PICK)
}

if __name__ == "__main__":
    key = sys.argv[1]
    c = CANDS[key]
    r = H.score(c, plants=("nominal", "b_lo", "F_hi", "J_hi", "light_b", "tau6"))
    json.dump(H.to_jsonable(r), open(os.path.join(HERE, "s5_score_%s.json" % key), "w"))
    with open(os.path.join(HERE, "s5_score_%s_out.txt" % key), "w") as f:
        H.print_score(r, file=f)
    print("done", key, r["meta"]["runtime_s"])
