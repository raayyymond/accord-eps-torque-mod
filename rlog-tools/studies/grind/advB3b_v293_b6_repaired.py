# -*- coding: utf-8 -*-
"""advB3b_v293_b6_repaired.py -- ADVERSARY B, criterion B6 re-scored at the REPAIRED preset.

agent `advB3b`, 2026-09-13.  ANALYSIS ONLY.

The prior adversary B (`advB3`) found B6 FAILING on the build+preset pair AS SHIPPED, because
StarPilot feeds `error_with_lsf` into `get_friction`, so the friction term's small-signal gain is
(friction/0.30)*(1 + lsf/kp) -- large at kp 0.3.  The repair applied in the fork is
HONDA_ACCORD_TORQUE_MODE_FRICTION 0.01 -> 0.00.

This file re-scores B6 at that REPAIRED preset, over tau {0.10, 0.15, 0.20, 0.30} and true plant
gain kappa in [0.5, 2.0], and runs V282 and STOCK through the identical function in the identical
cells so the broken-check is decidable.

Run: python advB3b_v293_b6_repaired.py
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
TAUS = [0.10, 0.15, 0.20, 0.30]
RES = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


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
    REPAIRED["name"] = "PRESET REPAIRED fric0"
    SHIPPED = dict(B.PRESET)
    SHIPPED["name"] = "PRESET AS SHIPPED f.01"

    pr("=" * 122)
    pr("ADVERSARY B -- B6 RE-SCORED AT THE REPAIRED PRESET.   agent advB3b, 2026-09-13.  ANALYSIS ONLY")
    pr("image: %s" % os.path.basename(img))
    pr("=" * 122)
    pr("REPAIRED preset: LAF %.1f  Kp %.2f  Ki %.2f  friction %.2f  rate-plant FF OFF"
       % (REPAIRED["laf"], REPAIRED["kp"], REPAIRED["ki"], REPAIRED["fric"]))
    pr("B6 FAIL = unstable, or PM < 30 deg, or a 1-4 Hz limit cycle, for ANY true plant gain in")
    pr("[0.5x, 2.0x].  BROKEN-CHECK: V282 at its own FLOWN tune is run through the identical cells.")
    pr()

    cases = [("V293", r293, REPAIRED), ("V293", r293, SHIPPED), ("V293", r293, B.LIVE),
             ("V282", r282, REPAIRED), ("V282", r282, B.LIVE)]

    # ------------------------------------------------------------- 1. the nominal cell, all taus
    pr("-" * 122)
    pr("1. THE NOMINAL CELL kappa = 1.00 -- worst speed of the five, at each tau")
    pr("-" * 122)
    pr("   %-5s %-24s %5s | %7s %7s %7s %7s  %s" % ("bld", "tune", "tau", "worst v", "PM", "Ms", "fc Hz", "verdict"))
    for name, rfn, tune in cases:
        for tau in TAUS:
            worst = None
            for v in B.SPEEDS:
                Lv = (B.C_lin(F, v, tune) + B.fric_slope(v, tune)) * B.P_of(F, v, rfn, tau, 1.0)
                m = B.margins(Lv, F)
                uns, _ = B.nyquist_unstable(Lv, F)
                key = (-1e9 if uns else (m["pm"] if np.isfinite(m["pm"]) else 1e9))
                if worst is None or key < worst[0]:
                    worst = (key, v, m, uns)
            _, v, m, uns = worst
            vd = "UNSTABLE" if uns else ("PM<30" if (np.isfinite(m["pm"]) and m["pm"] < 30) else "ok")
            pr("   %-5s %-24s %5.2f | %7.1f %7.1f %7.2f %7.2f  %s"
               % (name, tune["name"], tau, v, m["pm"], m["Ms"], m["fc"], vd))
            RES["nom|%s|%s|%.2f" % (name, tune["name"], tau)] = dict(
                v=v, pm=float(m["pm"]), ms=float(m["Ms"]), fc=float(m["fc"]), unstable=bool(uns))
    pr()

    # ------------------------------------------------------------- 2. the kappa margin
    KS = np.round(np.arange(0.30, 4.001, 0.01), 3)
    for tau in TAUS:
        pr("-" * 122)
        pr("2. THE kappa MARGIN at tau = %.2f s  (k30 = first kappa with PM < 30; kU = first unstable;"
           " '---' = never inside kappa <= 4)" % tau)
        pr("-" * 122)
        pr("   %-5s %-24s | %s" % ("bld", "tune", "  ".join("%5.1f m/s" % v for v in B.SPEEDS)))
        for name, rfn, tune in cases:
            for label, thr in (("k30", 30.0), ("kU", None)):
                row = []
                for v in B.SPEEDS:
                    base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
                    hit = np.nan
                    for k in KS:
                        Lv = base * B.P_of(F, v, rfn, tau, k)
                        m = B.margins(Lv, F)
                        uns, _ = B.nyquist_unstable(Lv, F)
                        if thr is None:
                            if uns:
                                hit = k
                                break
                        elif uns or (np.isfinite(m["pm"]) and m["pm"] < thr):
                            hit = k
                            break
                    row.append(hit)
                    RES["k|%s|%s|%.2f|%.1f|%s" % (name, tune["name"], tau, v, label)] = (
                        None if not np.isfinite(hit) else float(hit))
                pr("   %-5s %-24s | %s   <- %s" %
                   (name if label == "k30" else "", tune["name"] if label == "k30" else "",
                    "  ".join(("  ---  " if not np.isfinite(x) else "%6.2f " % x) for x in row), label))
        pr()

    # ------------------------------------------------------------- 3. inside [0.5, 2.0] explicitly
    pr("-" * 122)
    pr("3. THE CLAUSE AS WRITTEN: does ANY kappa in [0.5, 2.0] break the cell?  (tau on rows)")
    pr("-" * 122)
    pr("   %-5s %-24s %5s | %s" % ("bld", "tune", "tau", "worst PM over kappa in [0.5,2.0] x 5 speeds, and where"))
    for name, rfn, tune in cases:
        for tau in TAUS:
            worst = (1e9, None, None, False)
            for v in B.SPEEDS:
                base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
                for k in np.round(np.arange(0.50, 2.001, 0.02), 3):
                    Lv = base * B.P_of(F, v, rfn, tau, k)
                    m = B.margins(Lv, F)
                    uns, _ = B.nyquist_unstable(Lv, F)
                    key = -1e9 if uns else (m["pm"] if np.isfinite(m["pm"]) else 1e9)
                    if key < worst[0]:
                        worst = (key, v, k, uns)
            _, v, k, uns = worst
            pm = worst[0]
            vd = "UNSTABLE" if uns else ("FAIL PM<30" if pm < 30 else "PASS")
            pr("   %-5s %-24s %5.2f | %s  at v %.1f m/s, kappa %.2f   -> %s"
               % (name, tune["name"], tau,
                  ("unstable" if uns else "PM %6.1f deg" % pm), v, k, vd))
            RES["clause|%s|%s|%.2f" % (name, tune["name"], tau)] = dict(
                pm=(None if uns else float(pm)), v=float(v), kappa=float(k), unstable=bool(uns), verdict=vd)
    pr()
    pr("=" * 122)
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "b6_repaired.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    json.dump(RES, open(os.path.join(OUTDIR, "b6_repaired.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
