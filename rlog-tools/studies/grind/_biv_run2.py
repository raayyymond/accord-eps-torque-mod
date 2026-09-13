# -*- coding: utf-8 -*-
"""Driver for the part-3 diagnostics.  Run: python _biv_run2.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import b_iv_kappa as M
import _biv_part3 as P3
import bof_v282 as BF
from v282_r24_tap_read import read_cells
SCR = os.path.join(HERE, "_scratch")

def run():
    M.pr("=" * 150)
    M.pr("B_IV AND KAPPA -- PART 3: the 10-14 Hz identification gap, and the V291 cut's incremental arithmetic")
    M.pr("=" * 150)
    cells = read_cells(BF.V282_IMG)
    G = {}
    for t in BF.V282_ROUTES:
        print("loading %s ..." % t, flush=True)
        G[t] = BF.load(t, cells)
    P3.arm_selector(G)
    P3.v291_increment(G)
    P3.coh_scan(G)
    with open(os.path.join(SCR, "b_iv_kappa_p3.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(M.OUT) + "\n")
    with open(os.path.join(SCR, "b_iv_kappa_p3.json"), "w", encoding="utf-8") as fh:
        json.dump(M.J, fh, indent=1, default=float)
    print("\nwrote _scratch/b_iv_kappa_p3.{txt,json}")

if __name__ == "__main__":
    run()
