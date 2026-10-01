# -*- coding: utf-8 -*-
r"""r2a_env.py -- the speed-gain ENVELOPE (largest G at every grid speed that passes the brief's GATED credible set at
PM >= 45 / 30, LTI GM >= 6 dB, plus the 20 Hz rules M20 / Re(T/w)20 vs V295 at hold ages 0 and 10, and L20 <= V295's on
every tier-A member) for the structures this reviser adds (fresh-rate D at Kd 41 and Kd 48), and a REPRODUCIBILITY
CONTROL: the Kd-34 fresh-rate structure (D2a) re-derived from scratch and compared to the D designer's cached envelope.
Machinery: ds_gate2.envelope (the D designer's, validated in its page section 1.3 against the refuter's stab_lin to 0.000 deg).
ANALYSIS ONLY.   usage:  python r2a_env.py [fresh41 fresh48 control]"""
from __future__ import annotations

import json
import sys
import time

import r2a_common as R

import ds_gate2 as G2  # noqa: E402


def run(key):
    des = R.STRUCT[key]
    t0 = time.time()
    e = G2.envelope(des, members=G2.GATED, grid=G2.GRID)
    (R.OUT / f"env_{key}.json").write_text(json.dumps(dict(env=e["env"], bind=e["bind"]), default=float))
    print(f"{key}: envelope {time.time() - t0:.0f} s", flush=True)
    return e


def control():
    e = run("fresh34")
    ref = json.loads((R.DS_OUT / "final_env.json").read_text())["D2a"]
    mine = e["env"]
    dif = [abs(float(mine[v]) - float(ref["env"][str(v)] if str(v) in ref["env"] else ref["env"][repr(v)]))
           for v in mine]
    nb = sum(1 for v in mine if e["bind"][v] != ref["bind"].get(str(v), ref["bind"].get(repr(v))))
    msg = (f"CONTROL fresh34 (D2a structure) re-derived vs the D designer's cached envelope: max |dG| = {max(dif):.1f} "
           f"over {len(dif)} speeds; binding-member disagreements {nb}  -> {'REPRODUCED' if max(dif) == 0 else 'DIFFERS'}")
    print(msg)
    (R.HERE / "r2a_env_control.txt").write_text(msg + "\n", encoding="utf-8")


if __name__ == "__main__":
    which = sys.argv[1:] or ["fresh41", "fresh48", "control"]
    for w in which:
        if w == "control":
            control()
        else:
            run(w)
