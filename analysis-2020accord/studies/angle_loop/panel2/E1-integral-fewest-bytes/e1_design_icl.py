# -*- coding: utf-8 -*-
r"""e1_design_icl.py -- SIZE the integral clamp from the identified spring load (the F1 cause).

For a hands-off hold at lateral acceleration a_lat and speed v:
    theta_sw = a_lat * L * SR / v^2   (deg)        L 2.83 m, SR 16 (BELIEF: centre ratio, no understeer)
    load_T   = k(v) * sat(v) * tanh(theta_sw / sat(v))   (T counts, from the r71b plant family)
The integral alone can hold the whole curve iff T_I(ICL) >= load_T.  T_I(ICL) = t_from_I_contrib(ICL) (e1_lane,
EVIDENCE: the mirror steady state).  So ICL_needed(v, a) = load_T / (T_I(1)).

This script prints, per speed and per member (nominal, b_lo*J_hi, bc, F_hi), the load at a_lat in {1.0, 1.5, 2.0} and
the ICL that would let I carry it.  It then proposes:
  * a FLAT ICL (E1a) = the max over the credible curve set (>= 8 m/s) at the design a_lat;
  * a SPEED-SCHEDULED ICL table (E1b), low where the lurch is worst (10-12.5 m/s), peaking at 15-19 m/s.
ANALYSIS ONLY."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_lane as E1
import v294_plant as VP

OUT = E1.KIT / "_scratch" / "angle_loop" / "E1-integral-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)

L, SR = 2.83, 16.0
FAM = VP.family()
TI1 = E1.t_from_I_contrib(10000) / 10000.0   # delivered T per unit of I-branch (ICL), hands off (avoid int floor)
SPEEDS = [8, 10, 11.9, 12.5, 13, 15, 16, 17, 18, 19, 20, 22, 24, 26.9, 30]
ALATS = [1.0, 1.5, 2.0]
MEMBERS = ["nominal", "b_lo*J_hi", "bc", "F_hi"]


def params(member, v):
    return E1.NS.params(member, v) if hasattr(E1.NS, "params") else None


def member_params(member, v):
    # nl_sim.params returns (J, b, k, sat, Fc, Fs, tau)
    import nl_sim as NS
    return NS.params(member, v)


def load_T(member, v, a):
    J, b, k, sat, Fc, Fs, tau = member_params(member, v)
    theta = a * L * SR / v ** 2 * 180.0 / np.pi
    return k * sat * np.tanh(theta / sat), theta


def main():
    lines = [f"# ICL sizing from the spring load.  T per unit ICL (hands off) = {TI1:.5f} T.  ICL 4096 -> {4096*TI1:.0f} T.",
             f"# theta_sw = a_lat * {L} * {SR} / v^2 (deg); load = k*sat*tanh(theta/sat) from the r71b family.", ""]
    design = {}
    for a in ALATS:
        lines.append(f"=== a_lat {a:.1f} m/s^2 ===")
        lines.append(f"{'v':>6} " + " ".join(f"{m:>22}" for m in MEMBERS))
        for v in SPEEDS:
            cells = []
            for m in MEMBERS:
                lt, th = load_T(m, v, a)
                icln = lt / TI1
                cells.append(f"{th:5.1f}d {lt:5.0f}T icl{icln:6.0f}")
            lines.append(f"{v:>6} " + " ".join(f"{c:>22}" for c in cells))
            design[(a, v)] = {m: load_T(m, v, a)[0] / TI1 for m in MEMBERS}
        lines.append("")
    # FLAT ICL (E1a): cover nominal at a design a_lat over >=8 m/s, but capped at a value that keeps the lurch bounded.
    for a in ALATS:
        need_nom = max(design[(a, v)]["nominal"] for v in SPEEDS if v >= 8)
        need_blo = max(design[(a, v)]["b_lo*J_hi"] for v in SPEEDS if v >= 8)
        lines.append(f"FLAT ICL to carry a_lat {a:.1f}: nominal needs {need_nom:.0f}, b_lo*J_hi needs {need_blo:.0f}")
    # the worst speed band for each member at 2.0
    lines.append("")
    for m in MEMBERS:
        worst = max(SPEEDS, key=lambda v: design[(2.0, v)][m] if v >= 8 else -1)
        lines.append(f"worst-ICL speed (a 2.0) for {m}: {worst} m/s, needs ICL {design[(2.0, worst)][m]:.0f}")
    # SPEED-SCHEDULED ICL table (E1b): per plant knot, from nominal at a_lat 1.75 (between the harness 0.6 and the 2.0 stress)
    lines.append("")
    a_sched = 1.75
    knots = [3.1, 8.0, 10.0, 11.75, 15.5, 17.5, 26.9]        # the C1 lib knots (same X as G table)
    rows = []
    for vk in knots:
        icln = load_T("nominal", max(vk, 3.1), a_sched)[0] / TI1
        icl = int(min(max(round(icln / 256) * 256, 2048), 12288))   # quantise, floor 2048, cap 12288
        Xc = int(round(vk * 3.6 * 64))
        rows.append((Xc, icl))
    rows.append((0xFFFF, rows[-1][1]))
    lines.append(f"SCHEDULED ICL table (a_lat {a_sched}, nominal, quantised 256, floor 2048, cap 12288):")
    for (X, icl) in rows:
        v = X / 230.4 if X != 0xFFFF else float("inf")
        lines.append(f"  X {X:5d} ({v:5.1f} m/s)  ICL {icl:5d}  -> T_I {icl*TI1:5.0f} T")
    json.dump({"flat": {str(a): max(design[(a, v)]["nominal"] for v in SPEEDS if v >= 8) for a in ALATS},
               "sched_rows": rows, "TI1": TI1}, open(OUT / "icl_design.json", "w"))
    out = "\n".join(lines)
    print(out)
    (OUT / "icl_design_out.txt").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
