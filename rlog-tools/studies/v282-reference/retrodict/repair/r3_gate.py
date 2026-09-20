# -*- coding: utf-8 -*-
"""r3 -- run the PRE-REGISTERED GATE on the repaired statistic.  Verdict printed at the end, numbers first.

alpha (the identified plant gain) is a PURE SCALAR on L, so the -180 crossing frequency does not depend
on it and R scales exactly linearly with alpha.  The route-cluster bootstrap is therefore exact and cheap.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r2_stat as R  # noqa: E402

OUT = HERE / "out"
FGRID = np.arange(0.5, 8.0005, 0.002)
DPOINT = 0.065
DBRACKET = [0.055, 0.065, 0.075]
R71 = "00000071--f2c9d073a3"
R72 = "00000072--8001fc3048"
R73 = "00000073--79fd149dd8"
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd"]
T64P = "0000006c--68c6e94b17"
V282_ERA = ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
            "00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
# PREREG's named non-r71 plants
PREREG_PLANTS = [R72, R73, T64P]
MIN_SECS, MIN_COH, MIN_WIN = 90.0, 0.80, 4


def cell(pl, p, D, A=None, alpha=None):
    A = pl["A"] if A is None else A
    al = pl["alpha"] if alpha is None else alpha
    return R.crossing(FGRID, R.L_of(FGRID, pl["v"], al, pl["c"], p, A, D))


def main():
    binname = sys.argv[1] if len(sys.argv) > 1 else "22+"
    C = R.read_controllers()
    P = R.load_plants(binname)
    rng = np.random.default_rng(20260920)
    v293 = [r for r in P if r not in V282_ERA]
    enough = [r for r in v293 if P[r]["secs"] >= MIN_SECS and P[r]["coh"] >= MIN_COH
              and P[r]["n_win"] >= MIN_WIN]

    print("=" * 128)
    print("REPAIRED STATISTIC   R = |L| at the first -180 deg crossing (1-8 Hz).   R >= 1 => limit cycle predicted there.")
    print(f"speed bin {binname}    delay point {DPOINT*1000:.0f} ms (measured bracket {DBRACKET[0]*1000:.0f}-{DBRACKET[-1]*1000:.0f} ms)")
    print("=" * 128, "\n")

    print("TABLE 1 -- THE RELAY GUARD, from each route's OWN initData and OWN flown commit")
    print(f"{'route':22s} {'label':26s} {'commit':10s} {'SteerFriction':>13s} {'FricHyst':>9s} "
          f"{'guard?':>7s} {'RELAY':>6s} {'rateloop':>9s} {'notchQ':>7s} {'kp':>5s} {'LAF':>5s} {'ki':>5s}")
    for rt, p in C.items():
        g = "yes" if R.COMMIT[[k for k in R.COMMIT if k.startswith(p["commit"][:9])][0]][2] else "no"
        hy = "--" if p["hyst"] is None else f"{p['hyst']:.3f}"
        nq = "--" if not p["notch"] else f"{p['notch']:.2f}"
        print(f"{rt:22s} {p['lbl']:26s} {p['commit']:10s} {p['fric_param']:13.4f} {hy:>9s} "
              f"{g:>7s} {('LIVE' if p['relay'] else 'dead'):>6s} {p['rate']:9.4f} {nq:>7s} "
              f"{p['kp']:5.2f} {p['laf']:5.1f} {p['ki']:5.2f}")
    print("\n  guard = that commit carries `friction_torque = 0.0 if friction_hyst > 0.0` (added at 08a5a7064).")
    print("  r72/r73 flew e8e62f0e1: hysteresis term present, GUARD NOT PRESENT -- so r73's back-filled")
    print("  stock 0.2120 RAN as an error relay, while 6d's and 75's identical 0.2120 did not.\n")

    print("TABLE 2 -- THE IDENTIFIED PLANTS (this speed bin).  alpha = |H_iv|(0.15-0.30 Hz) * k(v)")
    print(f"{'plant':22s} {'label':26s} {'nrun':>4s} {'secs':>6s} {'v':>5s} {'|H|0.2':>7s} "
          f"{'phase':>6s} {'coh':>5s} {'k(v)':>7s} {'alpha':>6s} {'c':>7s} {'A':>6s} {'modeHz':>7s} {'use?':>5s}")
    for rt, pl in P.items():
        use = "YES" if rt in enough else ("-V282" if rt in V282_ERA else "thin")
        print(f"{rt:22s} {C[rt]['lbl']:26s} {pl['n_run']:4d} {pl['secs']:6.0f} {pl['v']:5.1f} "
              f"{pl['alpha']/R.k_of(pl['v']):7.2f} {pl['ph']:6.1f} {pl['coh']:5.3f} {R.k_of(pl['v']):7.4f} "
              f"{pl['alpha']:6.3f} {pl['c']:7.4f} {pl['A']:6.3f} {R.mode_hz(pl['v']):7.2f} {use:>5s}")
    print("\n  V282-era routes are EXCLUDED as plants and as controllers: the fork's J/b/k(v) model is")
    print("  explicitly the V293 torque-mode plant.  Their measured 0.2 Hz phase (-50 to -63 deg) differs")
    print("  from the V293 routes' (-25 to -41 deg), which is what a rate-servo EPS should look like.")
    print("  They are reported in TABLE 4b, not used for the gate.\n")

    print("TABLE 3 -- RETRODICTION OF r71 ON ITS OWN PLANT (the one labelled test)")
    pl71 = P[R71]
    for name, p in (("r71 as flown, relay ON  ", C[R71]),
                    ("r71 with the relay OFF  ", dict(C[R71], fric=0.0)),
                    ("r72's controller        ", C[R72]),
                    ("rev 6.4's controller    ", C[T64P])):
        print(f"   {name}  " + "   ".join(f"{cell(pl71, p, D)[0]:5.2f} @ {cell(pl71, p, D)[1]:4.2f} Hz"
                                          for D in DBRACKET))
    print("   OBSERVED on r71: a limit cycle at 2.34 Hz.")
    # limit-cycle amplitude prediction: A* where R(A*) = 1
    Agrid = np.linspace(0.02, 4.0, 400)
    Rv = np.array([cell(pl71, C[R71], DPOINT, A=a)[0] for a in Agrid])
    star = Agrid[np.argmin(np.abs(Rv - 1.0))] if np.nanmin(Rv) < 1.0 < np.nanmax(Rv) else np.nan
    print(f"   DF limit-cycle amplitude (R(A)=1 at 65 ms): error amplitude A* = {star:.3f} m/s^2"
          f"  => wheel amplitude {star/pl71['c']:.1f} deg  (reported: +/-6 deg)\n")

    ctrls = [R71, R72, R73, T64P, "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
             "00000076--d0b7ea7e4d", "00000075--6c8687d5bd", "00000070--717f5a7866"]
    ctrls = [c for c in ctrls if c in C]

    def table(rows, title):
        print(title)
        hdr = f"{'plant \\ controller':30s}" + "".join(f"{c.split('--')[0][-2:]:>8s}" for c in ctrls)
        print(hdr)
        G = {}
        for prt in rows:
            pl = P[prt]
            line = f"{prt.split('--')[0][-2:] + ' ' + C[prt]['lbl'][:26]:30s}"
            for crt in ctrls:
                Rv, fx = cell(pl, C[crt], DPOINT)
                G[(prt, crt)] = (Rv, fx)
                line += f"{Rv:8.2f}" if np.isfinite(Rv) else "     n/a"
            print(line)
        print("   -- crossing frequency, Hz --")
        for prt in rows:
            line = f"{prt.split('--')[0][-2:] + ' ' + C[prt]['lbl'][:26]:30s}"
            for crt in ctrls:
                line += f"{G[(prt,crt)][1]:8.2f}" if np.isfinite(G[(prt, crt)][1]) else "     n/a"
            print(line)
        print()
        return G

    G = table(enough, "TABLE 4 -- PLANT x CONTROLLER CROSS-TABLE of R  (row = whose plant, col = whose controller)")
    Gv = table([r for r in P if r in V282_ERA],
               "TABLE 4b -- the V282-era plants, OUT OF MODEL DOMAIN, reported not used")
    G.update(Gv)

    print("TABLE 5 -- ROUTE-CLUSTER BOOTSTRAP of the plant anchor (2000 draws, resampling contiguous runs)")
    print("   alpha is a pure scalar on L, so R scales exactly with it and the crossing frequency is fixed.")
    ci = {}
    for prt in enough:
        ab = R.alpha_boot(P[prt], rng)
        r = ab / P[prt]["alpha"]
        lo, hi = np.percentile(r, [2.5, 97.5])
        line = f"   plant {prt.split('--')[0][-2:]} {C[prt]['lbl'][:18]:20s} alpha x[{lo:.3f},{hi:.3f}] :"
        for crt in (R71, R72, R73, T64P):
            v = G[(prt, crt)][0]
            ci[(prt, crt)] = (v * lo, v * hi)
            line += f"  {crt.split('--')[0][-2:]}:{v:5.2f}[{v*lo:4.2f},{v*hi:4.2f}]"
        print(line)
    print()

    json.dump(dict(grid={f"{a}|{b}": list(v) for (a, b), v in G.items()},
                   ci={f"{a}|{b}": list(v) for (a, b), v in ci.items()},
                   plants={k: dict(v=v["v"], alpha=v["alpha"], c=v["c"], A=v["A"], coh=v["coh"],
                                   secs=v["secs"], n_run=v["n_run"], ph=v["ph"]) for k, v in P.items()},
                   ctrl={k: {kk: vv for kk, vv in v.items()} for k, v in C.items()}),
              open(OUT / f"r3_grid_{binname}.json", "w"), indent=1)

    print("=" * 128)
    print("THE PRE-REGISTERED GATE  (PREREG_retrodiction_gate.md, committed 74a7e9d before any of this ran)")
    print("=" * 128)
    print("\n(a) RANK -- r71's controller must be the RISKIEST on >= 2 of the 3 non-r71 plants with enough data")
    ok = 0
    for prt in PREREG_PLANTS:
        vals = {c: G[(prt, c)][0] for c in ctrls if np.isfinite(G[(prt, c)][0])}
        order = sorted(vals.items(), key=lambda kv: -kv[1])
        win = order[0][0] == R71
        ok += win
        print(f"    plant {prt.split('--')[0][-2:]} {C[prt]['lbl'][:20]:22s} ranking: "
              + " > ".join(f"{k.split('--')[0][-2:]} {v:.2f}" for k, v in order[:4])
              + ("   <== r71 top" if win else "   r71 NOT top"))
    print(f"    => r71 riskiest on {ok} of {len(PREREG_PLANTS)} pre-registered non-r71 plants")
    allp = [p for p in enough if p != R71]
    ok_all = sum(1 for prt in allp
                 if max(((c, G[(prt, c)][0]) for c in ctrls if np.isfinite(G[(prt, c)][0])),
                        key=lambda kv: kv[1])[0] == R71)
    print(f"    => on ALL {len(allp)} non-r71 V293 plants: r71 riskiest on {ok_all}")
    A_RANK = ok >= 2
    print(f"    (a) {'PASS' if A_RANK else 'FAIL'}")

    print("\n(b) SEPARATION -- r71's controller vs r72's, bootstrap CIs must not overlap")
    sep = []
    for prt in PREREG_PLANTS:
        a, b = ci[(prt, R71)], ci[(prt, R72)]
        nonov = a[0] > b[1] or b[0] > a[1]
        sep.append(nonov)
        print(f"    plant {prt.split('--')[0][-2:]}: r71 {G[(prt,R71)][0]:5.2f} [{a[0]:.2f},{a[1]:.2f}]  "
              f"r72 {G[(prt,R72)][0]:5.2f} [{b[0]:.2f},{b[1]:.2f}]  ratio "
              f"{G[(prt,R71)][0]/G[(prt,R72)][0]:5.2f}x  {'SEPARATED' if nonov else 'OVERLAP'}")
    B_SEP = all(sep)
    print(f"    (b) {'PASS' if B_SEP else 'FAIL'}   (the failed engine's separation was 0.29%)")

    print("\n(c) NO FALSE ALARM -- rev 6.4's flown controller must not rank riskier than r71's on any plant")
    fa = [(p, c) for p in enough for c in T64 if c in C and G[(p, c)][0] > G[(p, R71)][0]]
    for prt in enough:
        print(f"    plant {prt.split('--')[0][-2:]}: r71 {G[(prt,R71)][0]:5.2f}   "
              + "  ".join(f"{c.split('--')[0][-2:]} {G[(prt,c)][0]:5.2f}" for c in T64 if c in C))
    C_FA = not fa
    print(f"    => {len(fa)} false alarms.   (c) {'PASS' if C_FA else 'FAIL'}")

    print("\n" + "=" * 128)
    print(f"GATE VERDICT:  (a) RANK {'PASS' if A_RANK else 'FAIL'}   "
          f"(b) SEPARATION {'PASS' if B_SEP else 'FAIL'}   (c) NO FALSE ALARM {'PASS' if C_FA else 'FAIL'}")
    print("=" * 128)


if __name__ == "__main__":
    main()
