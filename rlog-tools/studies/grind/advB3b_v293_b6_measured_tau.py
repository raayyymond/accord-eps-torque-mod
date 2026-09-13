# -*- coding: utf-8 -*-
"""advB3b_v293_b6_measured_tau.py -- B6 at the MEASURED tau(v), not the record's assumed 0.20 s.

agent `advB3b`, 2026-09-13.  ANALYSIS ONLY.

`TAU-ACTUATOR-DELAY-2026-09-13.md` (subagent `taumeasure`) landed after the B6 re-score and it puts the
controller-loop delay ABOVE the assumed 0.20 s in exactly the speed band where every V293 B6 failure
lives.  Its table, tau_EPS (the channel the openpilot torque controller closes on):

    25+  m/s : 0.14 - 0.22 s        8-15 m/s : 0.19 - 0.27 s
    15-25 m/s: 0.18 - 0.24 s        3-8  m/s : 0.23 - 0.25 s      (path loop at 3-8: 0.20 - 0.34 s)

So B6 is re-scored PER SPEED at that speed's own measured tau interval, low end and high end, plus the
path-loop worst case, with V282 at the tune it is actually flown with in the identical cells.

Run: python advB3b_v293_b6_measured_tau.py
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\advB3b"
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v293_b6_outer as B                          # noqa: E402
import v293_lib as L                               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
RES = {}
# speed -> (tau_EPS low, tau_EPS high, tau_path worst), straight off the measurement's own table
TAU_V = {5.0: (0.23, 0.25, 0.34), 8.0: (0.19, 0.27, 0.33), 12.5: (0.19, 0.27, 0.33),
         18.5: (0.18, 0.24, 0.30), 28.5: (0.14, 0.22, 0.30)}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def cell(rfn, tune, v, tau, F):
    base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
    out = {}
    Lv = base * B.P_of(F, v, rfn, tau, 1.0)
    m = B.margins(Lv, F)
    uns, _ = B.nyquist_unstable(Lv, F)
    out["pm1"], out["ms1"], out["uns1"] = float(m["pm"]), float(m["Ms"]), bool(uns)
    k30 = kU = np.nan
    for k in np.round(np.arange(0.30, 4.001, 0.01), 3):
        Lk = base * B.P_of(F, v, rfn, tau, k)
        mk = B.margins(Lk, F)
        uk, _ = B.nyquist_unstable(Lk, F)
        if not np.isfinite(k30) and (uk or (np.isfinite(mk["pm"]) and mk["pm"] < 30.0)):
            k30 = k
        if not np.isfinite(kU) and uk:
            kU = k
            break
    out["k30"], out["kU"] = k30, kU
    return out


def main():
    c282 = L.read_cells(L.IMG282)
    img = sorted(glob.glob(L.FW + "_v293_*_plain_image.bin"))[-1]
    c293 = L.read_cells(img)
    import design290b_candidates as D
    import v292_replay_s2 as S2
    fam, _, _ = S2.load_family()
    byid = {f["id"]: f for f in fam}
    plants = {i: D.mkplant(byid[i]) for i in B.NAMED}
    r282, r293, kmap, Rdc = B.make_rate_fns(c282, c293, plants, 225)
    F = B.F
    REPAIRED = dict(B.PRESET)
    REPAIRED["fric"] = 0.00
    REPAIRED["name"] = "V293 preset REPAIRED"

    pr("=" * 122)
    pr("ADVERSARY B -- B6 AT THE MEASURED tau(v).   agent advB3b, 2026-09-13.  ANALYSIS ONLY")
    pr("tau from TAU-ACTUATOR-DELAY-2026-09-13.md (subagent taumeasure), controller-loop channel,")
    pr("with the path-loop worst case as a third column.  The record's assumed 0.20 s is NOT used.")
    pr("=" * 122)
    pr("  k30 = first true-plant-gain multiplier with PM < 30 deg ; kU = first unstable.")
    pr("  The prereg's clause fails if EITHER lands inside [0.5, 2.0].")
    pr()
    for name, rfn, tune in (("V293", r293, REPAIRED), ("V282", r282, B.LIVE)):
        pr("-" * 122)
        pr("  %s  --  %s   (LAF %.1f Kp %.2f Ki %.2f friction %.2f)"
           % (name, tune["name"], tune["laf"], tune["kp"], tune["ki"], tune["fric"]))
        pr("-" * 122)
        pr("      v |  tau_lo  PM@k1  k30    kU  |  tau_hi  PM@k1  k30    kU  | tau_path PM@k1  k30    kU")
        for v, (tlo, thi, tp) in TAU_V.items():
            row = []
            for t in (tlo, thi, tp):
                o = cell(rfn, tune, v, t, F)
                row.append(o)
                RES["%s|%.1f|%.2f" % (name, v, t)] = {k: (None if isinstance(x, float) and not np.isfinite(x)
                                                          else x) for k, x in o.items()}
            fmt = lambda t, o: "  %5.2f %6s %5s %5s" % (                       # noqa: E731
                t, ("unst" if o["uns1"] else "%6.1f" % o["pm1"]),
                ("---" if not np.isfinite(o["k30"]) else "%.2f" % o["k30"]),
                ("---" if not np.isfinite(o["kU"]) else "%.2f" % o["kU"]))
            pr("  %5.1f |%s |%s |%s" % (v, fmt(tlo, row[0]), fmt(thi, row[1]), fmt(tp, row[2])))
        pr()
    pr("=" * 122)
    pr("VERDICT ARITHMETIC: a cell BREAKS the prereg's clause if k30 <= 2.00 (PM < 30 somewhere in")
    pr("[0.5, 2.0]).  Count the broken cells for each build, controller-loop columns only:")
    for name in ("V293", "V282"):
        n = tot = 0
        for key, o in RES.items():
            b, vs, ts = key.split("|")
            if b != name or float(ts) > 0.28:      # drop the path-loop column
                continue
            tot += 1
            if o["k30"] is not None and o["k30"] <= 2.00:
                n += 1
        pr("   %-5s : %d of %d controller-loop cells break the clause" % (name, n, tot))
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "b6_measured_tau.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    json.dump(RES, open(os.path.join(OUTDIR, "b6_measured_tau.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
