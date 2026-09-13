# -*- coding: utf-8 -*-
"""Driver for b_iv_kappa / _biv_part2.  Run:  python _biv_run.py"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import b_iv_kappa as M      # noqa: E402
import _biv_part2 as P2     # noqa: E402
import bof_v282 as BF       # noqa: E402
from v282_r24_tap_read import read_cells   # noqa: E402

SCR = os.path.join(HERE, "_scratch")


def run():
    M.pr("=" * 150)
    M.pr("B_IV AND KAPPA -- Q1 the closed-loop bias of B(f) and the 10-14 Hz gap;")
    M.pr("                  Q2 the +-3 post-gain deadband vs the 0.45 arm")
    M.pr("  subagent `biv`, 2026-09-13.  ANALYSIS ONLY -- builds nothing, flashes nothing, sends nothing.")
    M.pr("=" * 150)
    cells = read_cells(BF.V282_IMG)
    cells280 = read_cells(BF.V280R2_IMG)

    gc = {}
    for t in BF.CTRL_ROUTES:
        print("loading control %s ..." % t, flush=True)
        gc[t] = BF.load(t, cells280)
    P2.controls(gc)
    del gc

    G = {}
    for t in BF.V282_ROUTES:
        print("loading %s ..." % t, flush=True)
        G[t] = BF.load(t, cells)
    M.J["routes"] = {t: dict(secs=float(G[t]["tr"][-1]), eng=float(G[t]["eng"].sum() / M.FS))
                     for t in G}
    M.pr("")
    for t in BF.V282_ROUTES:
        M.pr("  %-5s  %.1f s total, %.1f s engaged-lateral" % (t, G[t]["tr"][-1], G[t]["eng"].sum() / M.FS))

    POOLS = P2.q1_tables(G)
    P2.instrument_diag(G, POOLS)
    P2.q2_deadband(G)
    P2.q2_tscale(G)

    with open(os.path.join(SCR, "b_iv_kappa.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(M.OUT) + "\n")
    with open(os.path.join(SCR, "b_iv_kappa.json"), "w", encoding="utf-8") as fh:
        json.dump(M.J, fh, indent=1, default=float)
    print("\nwrote _scratch/b_iv_kappa.{txt,json}")


if __name__ == "__main__":
    run()
