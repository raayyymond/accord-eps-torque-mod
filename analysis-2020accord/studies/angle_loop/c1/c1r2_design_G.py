# -*- coding: utf-8 -*-
"""c1r2_design_G.py -- size G(v) for C1 rev 2 on a 0.25 m/s grid (plus the plant knots 3.1/8.0/11.9/17.0/26.9 and the
b_q switch at 12.5), against EVERY member of c1r2_members by tier (A: PM >= 45; B: PM >= 30 -- every combined member
and every member with the hold aged to 20 ticks).  ANALYSIS ONLY.

Method (as c1_design_G, EVIDENCE when run): L(f; g) = g*A(f) + B(f) is linear in g = G/256; for each (member, v) PM(g)
is scanned UP on an 8-count G grid from 64 and G_max is the last G before the first failure (a scan that has no
crossover above 0.005 Hz counts as a pass: the crossover is then below 0.005 Hz with the integrator's -90 deg).
The envelope G_env(v) = min over the gating members.  Report-only members are tabulated, not gated.
usage: python c1r2_design_G.py <kd> <ki_base>      -> _scratch/angle_loop/c1/design_G_r2_kd<kd>_ki<ki>.json + .txt"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1r2_explore as X  # noqa: E402
import c1r2_members as M  # noqa: E402

SPEEDS = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))


def job(args):
    v, kd, ki = args
    out = {}
    for n in M.TIER_A + M.TIER_B + M.REPORT:
        out[n] = X.gmax(n, v, M.TIER_PM.get(n, 30.0), C.KP_BASE, ki, kd)
    return v, out


def envelope(res, names):
    return {v: min((r[n], n) for n in names) for v, r in res.items()}


def main():
    kd = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    ki = int(sys.argv[2]) if len(sys.argv) > 2 else C.KI_BASE
    t0 = time.time()
    with Pool(14) as pool:
        res = dict(pool.map(job, [(v, kd, ki) for v in SPEEDS]))
    tag = (f"kp{C.KP_BASE}_" if C.KP_BASE != 225 else "") + f"kd{kd}_ki{ki}"
    (C.OUT / f"design_G_r2_{tag}.json").write_text(json.dumps({str(v): r for v, r in res.items()}))
    eA = envelope(res, M.TIER_A)
    eB = envelope(res, M.TIER_B)
    lines = [f"# c1r2_design_G.py kd {kd} ki_base {ki} kp_base {C.KP_BASE}: G_max per member (Kp_eff = 225*G/256);"
             f" tier A PM >= 45, tier B PM >= 30 (incl. every +h10); 0 = fails at the first grid point",
             "    v    envA (binding)                envB (binding)                env  Kp_eff | " +
             " ".join(f"{m[:10]:>10s}" for m in M.REPORT)]
    for v in SPEEDS:
        ga, na = eA[v]
        gb, nb = eB[v]
        e = min(ga, gb)
        lines.append(f"{v:6.2f} {ga:5d} ({na:>20s})  {gb:5d} ({nb:>22s})  {e:5d} {C.KP_BASE * e / 256:6.0f} | " +
                     " ".join(f"{res[v][n]:10d}" for n in M.REPORT))
    txt = "\n".join(lines)
    (C.OUT / f"design_G_r2_{tag}.txt").write_text(txt)
    (HERE / f"design_G_r2_{tag}.txt").write_text(txt)
    print(txt)
    print(f"[{time.time() - t0:.0f} s]")


if __name__ == "__main__":
    main()
