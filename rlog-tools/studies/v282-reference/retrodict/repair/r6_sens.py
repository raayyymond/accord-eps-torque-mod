# -*- coding: utf-8 -*-
"""r6 -- sensitivity of the verdict: the describing-function amplitude A, the delay, the plant b,
and what clause (a) does if r73's controller is removed from the comparison set (DIAGNOSTIC ONLY --
the prereg fixes the anchor set and this is not a re-run of the gate)."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r2_stat as R  # noqa: E402
from r3_gate import FGRID, DPOINT, R71, R72, R73, T64P, cell  # noqa: E402


def main():
    C = R.read_controllers()
    P = R.load_plants("22+")
    pl = P[R71]
    print("A-SENSITIVITY.  A is the amplitude the saturating friction element sees; the fork's own")
    print("shape is clip(x/0.30), whose DF is 1/0.30 for A <= 0.30 and -> 4/(pi A) above it.")
    print(f"r71's measured A = sqrt(2)*rms(pid_log.error) = {pl['A']:.3f} m/s^2; "
          f"{100*(1-pl['sat']):.0f}% of its frames are inside the 0.30 threshold.\n")
    print(f"{'A':>6s} {'N_DF':>7s} {'relay/P':>8s} | " + "".join(f"{f'R r71 D={d*1000:.0f}ms':>16s}" for d in (0.055, 0.065, 0.075)))
    for A in (0.10, 0.20, pl["A"], 0.30, 0.40, 0.60, 1.00, 2.00):
        p = C[R71]
        lsf = R.lsf_of(pl["v"])
        rel = p["fric"] * R.df_ramp(A) / ((p["kp"] + lsf) / p["laf"] / (1 + lsf / p["kp"]))
        row = "".join(f"{cell(pl, p, d, A=A)[0]:10.2f} @{cell(pl, p, d, A=A)[1]:4.2f}" for d in (0.055, 0.065, 0.075))
        print(f"{A:6.3f} {R.df_ramp(A):7.3f} {rel:8.2f} | {row}")
    print("\n  => the r71 retrodiction (R >= 1) survives for A up to ~0.35-0.5 depending on the delay.")
    print("     The ratio of any two relay controllers is INDEPENDENT of A (same N, different F),")
    print("     so no choice of A can reorder r73 vs r71: 0.2120/0.0110 = 19.3x at every A.\n")

    print("PLANT-DAMPING SENSITIVITY (the fork's b = 0.0006 is its own 'light b', zeta 0.2-0.35)")
    print(f"{'b':>8s} {'zeta':>6s} " + "".join(f"{c.split('--')[0][-2:]:>9s}" for c in (R71, R72, R73, T64P)))
    b0 = R.B_PLANT
    for b in (0.0003, 0.0006, 0.0012, 0.0024):
        R.B_PLANT = b
        z = b / (2 * np.sqrt(R.J * R.k_of(pl["v"])))
        print(f"{b:8.4f} {z:6.3f} " + "".join(f"{cell(pl, C[c], DPOINT)[0]:9.2f}" for c in (R71, R72, R73, T64P)))
    R.B_PLANT = b0

    print("\nDIAGNOSTIC (NOT a re-run of the gate -- the prereg fixes the anchor set):")
    print("  clause (a) with r73's controller REMOVED from the comparison set:")
    ctrls = [R71, R72, T64P, "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
             "00000076--d0b7ea7e4d", "00000075--6c8687d5bd", "00000070--717f5a7866"]
    for prt in (R72, R73, T64P):
        vals = {c: cell(P[prt], C[c], DPOINT)[0] for c in ctrls}
        order = sorted(vals.items(), key=lambda kv: -kv[1])
        print(f"    plant {prt.split('--')[0][-2:]}: " + " > ".join(f"{k.split('--')[0][-2:]} {v:.2f}" for k, v in order[:4])
              + ("   r71 top" if order[0][0] == R71 else "   r71 NOT top"))


if __name__ == "__main__":
    main()
