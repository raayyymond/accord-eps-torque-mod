# -*- coding: utf-8 -*-
"""CLAUSES (b) ORDERING and (c) NO FALSE ALARM, on the jerk-lead statistic.

(b) BOTH positives (r71, r73) above ALL the prereg's clean routes, on >= 2 of 3 plants not taken
    from either positive's own log.    ->  min(R_r71, R_r73) > max(R over the cleans)
(c) rev 6.4's flown controller must not rank above either positive on ANY plant.

Statistic, modelling choice held fixed from clause (a):
    R = |L| at the FIRST -180 deg crossing in 1-8 Hz.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g2_lib as G  # noqa: E402

FG = np.arange(0.5, 12.0005, 0.002)
DPOINT, BPOINT = 0.065, 6.0e-4
DBR = [0.055, 0.065, 0.075]
BSW = [4.0e-4, 6.0e-4, 1.0e-3, 2.0e-3]
MIN_SECS, MIN_COH, MIN_WIN = 90.0, 0.80, 4
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd"]


def Rof(pl, p, D, b, jerk=True):
    return G.first_crossing(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], p, pl["A"], D, b, jerk))


def main():
    C = G.read_controllers()
    P = G.load_plants("22+")
    enough = [r for r in P if P[r]["secs"] >= MIN_SECS and P[r]["coh"] >= MIN_COH and P[r]["n_win"] >= MIN_WIN]
    v293_plants = [r for r in enough if r not in G.V282_ERA]

    print("=" * 132)
    print("TABLE 1 -- THE FLOWN CONTROLLERS, from each route's OWN initData and OWN commit (constants re-verified)")
    print(f"{'route':22s} {'label':22s} {'commit':10s} {'fric':>7s} {'hyst':>6s} {'guard':>5s} {'RELAY':>5s} "
          f"{'rate':>7s} {'rateRC':>6s} {'notchQ':>6s} {'notch f0@27':>11s} {'kp':>5s} {'LAF':>5s} {'ki':>5s}")
    for rt, p in sorted(C.items()):
        hy = "--" if p["hyst"] is None else f"{p['hyst']:.3f}"
        nq = "--" if not p["notch"] else f"{p['notch']:.2f}"
        f0 = "--" if not p["notch"] else f"{G.mode_hz(27.0, p['ktbl']):.3f} Hz"
        print(f"{rt:22s} {p['lbl']:22s} {p['commit']:10s} {p['fric_param']:7.4f} {hy:>6s} "
              f"{('yes' if p['guard'] else 'no'):>5s} {('LIVE' if p['relay'] else 'dead'):>5s} "
              f"{p['rate']:7.4f} {p['rate_rc']:6.2f} {nq:>6s} {f0:>11s} {p['kp']:5.2f} {p['laf']:5.1f} {p['ki']:5.2f}")
    print("\n  RE-VERIFIED CORRECTIONS to gate #1's constants (git show <commit>:selfdrive/controls/lib/...):")
    print("    HONDA_ACCORD_RATE_LOOP_RC = 0.03 at e8e62f0e1/08a5a7064, 0.01 only from e44b6cd31 (r2_stat used 0.01 for all)")
    print("    HONDA_ACCORD_HOLD_K_V[28 m/s] = 0.0134 at e8e62f0e1, 0.0160 from 08a5a7064 -> r72/r73 notched at")
    print("    2.06 Hz, not 2.21 Hz (r2_stat used 0.0160 for all).  The PLANT k(v) uses one table for every route.")
    print("    VERIFIED UNCHANGED: guard first at 08a5a7064; notch+rate loop first at e8e62f0e1; the bilinear")
    print("    notch coefficients; JERK_GAIN = 0.22 and the jerk-in-relay line present at EVERY flown commit.\n")

    ctrls = sorted(C.keys())
    grid = {}
    print("=" * 132)
    print(f"TABLE 2 -- PLANT x CONTROLLER, R = |L| at the first -180 crossing.   b = {BPOINT}, D = {DPOINT*1000:.0f} ms")
    print("  row = whose plant (identified from its own log), col = whose flown controller")
    hdr = f"{'plant':32s}" + "".join(f"{c.split('--')[0][-2:]:>7s}" for c in ctrls)
    print(hdr)
    for prt in enough:
        line = f"{prt.split('--')[0][-2:] + ' ' + C[prt]['lbl'][:28]:32s}"
        for crt in ctrls:
            r, f = Rof(P[prt], C[crt], DPOINT, BPOINT)
            grid[(prt, crt)] = (r, f)
            line += f"{r:7.2f}" if np.isfinite(r) else "    n/a"
        print(line)
    print("   -- crossing frequency, Hz --")
    for prt in enough:
        line = f"{prt.split('--')[0][-2:] + ' ' + C[prt]['lbl'][:28]:32s}"
        for crt in ctrls:
            f = grid[(prt, crt)][1]
            line += f"{f:7.2f}" if np.isfinite(f) else "    n/a"
        print(line)

    # ---------------- CLAUSE (b) ----------------
    print("\n" + "=" * 132)
    print("CLAUSE (b) ORDERING -- BOTH positives above ALL the clean routes, on >= 2 of 3 non-positive plants")
    print("=" * 132)
    CLEAN_SETS = {
        "prereg table as written (r72 + T64 x2 + V282 x3 @0.010)": [G.R72] + G.CLEAN_T64 + G.CLEAN_V282,
        "same but V282 = the 0.030 triple (V282old)": [G.R72] + G.CLEAN_T64 + G.CLEAN_V282_OLD,
        "every clean anchor in the table, both V282 triples (9)": [G.R72] + G.CLEAN_T64_ALL + G.CLEAN_V282 + G.CLEAN_V282_OLD,
    }
    bres = {}
    for name, cleans in CLEAN_SETS.items():
        print(f"\n  clean set = {name}")
        okp = 0
        for prt in G.PREREG_PLANTS:
            rp = {t: grid[(prt, t)][0] for t in G.POSITIVES}
            rc = {c: grid[(prt, c)][0] for c in cleans}
            worst_pos = min(rp.values())
            worst_clean_rt = max(rc, key=lambda k: rc[k])
            ok = worst_pos > rc[worst_clean_rt]
            okp += ok
            print(f"    plant {prt.split('--')[0][-2:]} {C[prt]['lbl'][:20]:22s}  "
                  f"r71 {rp[G.R71]:6.2f}  r73 {rp[G.R73]:6.2f}  | worst clean = "
                  f"{worst_clean_rt.split('--')[0][-2:]} {C[worst_clean_rt]['lbl'][:16]:18s} {rc[worst_clean_rt]:6.2f}"
                  f"   {'BOTH ABOVE' if ok else 'FAIL'}")
            print("        cleans: " + "  ".join(f"{c.split('--')[0][-2:]}:{rc[c]:.2f}" for c in cleans))
        bres[name] = okp
        print(f"    => both positives above all cleans on {okp} of 3 prereg plants   "
              f"({'PASS' if okp >= 2 else 'FAIL'})")
    B_PASS = all(v >= 2 for v in bres.values())
    print(f"\n  >>> CLAUSE (b) {'PASS' if B_PASS else 'FAIL'} <<<   (scored on the strictest reading of the clean set)")

    # ---------------- CLAUSE (c) ----------------
    print("\n" + "=" * 132)
    print("CLAUSE (c) NO FALSE ALARM -- rev 6.4's flown controller must not rank above EITHER positive on ANY plant")
    print("=" * 132)
    fa = []
    for prt in enough:
        worst_pos = min(grid[(prt, t)][0] for t in G.POSITIVES)
        line = (f"    plant {prt.split('--')[0][-2:]} {C[prt]['lbl'][:22]:24s} r71 {grid[(prt,G.R71)][0]:6.2f} "
                f"r73 {grid[(prt,G.R73)][0]:6.2f} | rev6.4: ")
        for c in T64:
            v = grid[(prt, c)][0]
            hit = v > worst_pos
            fa += [(prt, c)] if hit else []
            line += f"{c.split('--')[0][-2:]} {v:6.2f}{'!' if hit else ' '} "
        print(line)
    C_PASS = not fa
    print(f"    => {len(fa)} false alarms in {len(enough)*len(T64)} cells.   >>> CLAUSE (c) "
          f"{'PASS' if C_PASS else 'FAIL'} <<<")

    # ---------------- sensitivity ----------------
    print("\n" + "=" * 132)
    print("SENSITIVITY of (b) and (c) over the b sweep and the delay bracket")
    print("=" * 132)
    sens = []
    for b in BSW:
        for D in DBR:
            g = {}
            for prt in G.PREREG_PLANTS + [p for p in enough if p not in G.PREREG_PLANTS]:
                for crt in ctrls:
                    g[(prt, crt)] = Rof(P[prt], C[crt], D, b)[0]
            okp = 0
            for prt in G.PREREG_PLANTS:
                wp = min(g[(prt, t)] for t in G.POSITIVES)
                wc = max(g[(prt, c)] for c in CLEAN_SETS["every clean anchor in the table, both V282 triples (9)"])
                okp += wp > wc
            nfa = sum(1 for prt in enough for c in T64
                      if g[(prt, c)] > min(g[(prt, t)] for t in G.POSITIVES))
            sens.append((b, D, okp, nfa))
            print(f"    b={b:7.5f} D={D*1000:2.0f}ms   (b): {okp}/3 plants {'PASS' if okp >= 2 else 'FAIL'}"
                  f"    (c): {nfa} false alarms {'PASS' if nfa == 0 else 'FAIL'}")

    json.dump(dict(grid={f"{a}|{b}": list(v) for (a, b), v in grid.items()},
                   b_by_cleanset=bres, b_pass=bool(B_PASS), c_pass=bool(C_PASS),
                   false_alarms=[list(x) for x in fa], sens=[list(x) for x in sens]),
              open(HERE / "out" / "g2_bc.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
