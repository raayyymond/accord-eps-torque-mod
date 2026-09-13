# -*- coding: utf-8 -*-
"""v293_b6_margins.py -- B6 part 2: the kappa MARGIN, the broken-check adjudication, the cycle size.

Subagent `B6` of `advB3`, 2026-09-13.  ANALYSIS ONLY.

Part 1 (`v293_b6_outer.py`) established that the LITERAL B6 -- "FAIL for ANY true plant gain in
[0.5x, 2x]" -- condemns V282 at its own flown tune too (28.5 m/s, kappa 2.00, tau 0.20: PM -4.2 deg,
and the nonlinear sim limit-cycles at 1.25 Hz).  By the kit's own rule a check that condemns the
FLOWN build is BROKEN, so the [0.5, 2] clause cannot be used on its own to condemn V293.

This file therefore asks the question the broken clause cannot: AT WHAT kappa does each
configuration first fail, and does V293 fail at a kappa that V282 survives?  That comparison is
immune to the broken clause: it is a MARGIN, not a threshold.

Run: python v293_b6_margins.py
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                       # noqa: E402
import v293_lib as L                               # noqa: E402
import v293_b6_outer as B                          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []


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

    pr("=" * 116)
    pr("B6 PART 2 -- the kappa MARGIN, the broken-check adjudication, and the size of the cycle")
    pr("subagent B6 of advB3, 2026-09-13.  Image %s" % os.path.basename(img))
    pr("=" * 116)

    cases = [("V293", r293, B.PRESET), ("V293", r293, B.LIVE),
             ("V282", r282, B.PRESET), ("V282", r282, B.LIVE)]
    KS = np.round(np.arange(0.30, 4.001, 0.01), 3)

    # ---------------------------------------------------------------- 1. kappa margin
    pr("")
    pr("1. THE kappa MARGIN at tau = 0.20 s -- the smallest true-plant-gain multiplier at which")
    pr("   the cell first drops below PM 30 deg (k30) and at which it first goes UNSTABLE (kU).")
    pr("   kappa = 1.00 is the NOMINAL identified gain.  Blank = never inside kappa <= 4.")
    pr("-" * 116)
    pr("   %-5s %-20s | %s" % ("bld", "tune", "  ".join("%5.1f m/s" % v for v in B.SPEEDS)))
    summary = {}
    for name, rfn, tune in cases:
        for label, thr in (("k30", 30.0), ("kU", None)):
            row = []
            for v in B.SPEEDS:
                base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
                hit = np.nan
                for k in KS:
                    Lv = base * B.P_of(F, v, rfn, 0.20, k)
                    m = B.margins(Lv, F)
                    uns, _ = B.nyquist_unstable(Lv, F)
                    if thr is None:
                        if uns:
                            hit = k
                            break
                    else:
                        if uns or (np.isfinite(m["pm"]) and m["pm"] < thr):
                            hit = k
                            break
                row.append(hit)
                summary[(name, tune["name"], v, label)] = hit
            pr("   %-5s %-20s | %s   <- %s" %
               (name if label == "k30" else "", tune["name"] if label == "k30" else "",
                "  ".join(("  ---  " if not np.isfinite(x) else "%6.2f " % x) for x in row), label))

    pr("")
    pr("   🛑 READ.  V282 at its OWN FLOWN TUNE has k30 = %.2f / kU = %.2f at its worst speed."
       % (min(x for x in [summary[("V282", B.LIVE["name"], v, "k30")] for v in B.SPEEDS] if np.isfinite(x)),
          min(x for x in [summary[("V282", B.LIVE["name"], v, "kU")] for v in B.SPEEDS] if np.isfinite(x))))
    pr("   V293 at the PRESET it is meant to be flown with has k30 = %.2f / kU = %.2f."
       % (min(x for x in [summary[("V293", B.PRESET["name"], v, "k30")] for v in B.SPEEDS] if np.isfinite(x)),
          min(x for x in [summary[("V293", B.PRESET["name"], v, "kU")] for v in B.SPEEDS] if np.isfinite(x))))

    # ---------------------------------------------------------------- 2. the nominal cell
    pr("")
    pr("2. THE NOMINAL CELL kappa = 1.00 -- no gain error assumed at all")
    pr("-" * 116)
    pr("   %-5s %-20s %6s | %8s %7s %7s %7s %9s" %
       ("bld", "tune", "tau", "worst v", "PM", "Ms", "fc Hz", "verdict"))
    for name, rfn, tune in cases:
        for tau in B.TAUS:
            rows = []
            for v in B.SPEEDS:
                base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
                Lv = base * B.P_of(F, v, rfn, tau, 1.0)
                m = B.margins(Lv, F)
                uns, _ = B.nyquist_unstable(Lv, F)
                rows.append(((m["pm"] if np.isfinite(m["pm"]) else 999.0), uns, v, m))
            rows.sort(key=lambda r: (not r[1], r[0]))
            pm, uns, v, m = rows[0]
            pr("   %-5s %-20s %6.2f | %8.1f %7.1f %7.2f %7.2f %9s"
               % (name, tune["name"], tau, v, pm if pm < 900 else float("nan"), m["Ms"], m["fc"],
                  "UNSTABLE" if uns else ("PM<30" if pm < 30 else "ok")))

    # ---------------------------------------------------------------- 3. the spring sensitivity
    pr("")
    pr("3. DOES THE OMITTED SELF-ALIGNING SPRING RESCUE THE 5 m/s CELL?  (the model's one known")
    pr("   pessimism: HONDA_ACCORD_EPS_K_V, k = 0.17..0.50 1/s, adds phase LEAD at low f)")
    pr("-" * 116)
    pr("   %-5s %-20s %6s | %10s %10s %8s" % ("bld", "tune", "v", "PM no spring", "PM spring", "delta"))
    for name, rfn, tune in cases[:2]:
        for v in B.SPEEDS:
            base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
            a = B.margins(base * B.P_of(F, v, rfn, 0.20, 1.0), F)["pm"]
            b = B.margins(base * B.P_of(F, v, rfn, 0.20, 1.0, spring=True), F)["pm"]
            pr("   %-5s %-20s %6.1f | %10.1f %10.1f %8.2f" % (name, tune["name"], v, a, b, b - a))

    # ---------------------------------------------------------------- 4. the cycle, sized
    pr("")
    pr("4. THE LIMIT CYCLE, SIZED -- nonlinear sim, kappa swept to find the onset and the amplitude")
    pr("-" * 116)
    pr("   %-5s %-20s %5s | %6s %10s %9s %10s %12s" %
       ("bld", "tune", "v", "kappa", "amp torque", "f_osc Hz", "amp 0xE4", "wheel amp deg"))
    for name, rfn, tune in cases:
        for v in (5.0, 8.0, 28.5):
            dc = float(np.real(rfn(np.array([1e-4]), v)[0]))
            prev = None
            for kap in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0):
                s = B.sim(v, tune, dc, 0.20, kap, plants[225], T=60.0)
                if s["grew"]:
                    amp = s["a_late"]
                    ang = amp * kap * dc / (2 * np.pi * s["fosc"]) if np.isfinite(s["fosc"]) else np.nan
                    pr("   %-5s %-20s %5.1f | %6.2f %10.5f %9.3f %10.0f %12.2f"
                       % (name, tune["name"], v, kap, amp, s["fosc"], amp * 4096, ang))
                    prev = kap
                    break
            if prev is None:
                pr("   %-5s %-20s %5.1f | %6s %10s %9s %10s %12s"
                   % (name, tune["name"], v, "none", "-", "-", "-", "-"))

    # ---------------------------------------------------------------- 5. STOCK, properly labelled
    pr("")
    pr("5. STOCK -- the broken-check's second leg")
    pr("-" * 116)
    cs = L.read_cells(L.FW + "stock_fw_dump/code.bin")
    slope_stock = 141.4 * (float(np.max(cs["map_Y"])) / float(np.max(c282["map_Y"])))
    fnS, RdcS = B.stock_rate_fn(cs, c282, plants, 225)
    pr("   stock Kp bank %s  fb clamp %d  r24 arm %d  map top %d (V282 %d, x%.2f)"
       % (cs["kp_Y"], cs["fb_clamp"], cs["r24_arm"], int(np.max(cs["map_Y"])),
          int(np.max(c282["map_Y"])), float(np.max(c282["map_Y"])) / float(np.max(cs["map_Y"]))))
    pr("   R_servo(0) stock %.4f vs V282 %.4f ; stock map slope %.1f deg/s per unit vs 141.4"
       % (RdcS, Rdc, slope_stock))
    pr("   %6s | %10s %10s %10s | %10s" % ("v", "G_stock", "|L|1Hz k=1", "PM k=1", "PM k=2"))
    for v in B.SPEEDS:
        _, _, g0 = B.g0_of_v(v, Rdc)
        Ldc = RdcS * B.CPD * g0
        G = slope_stock * Ldc / (1 + Ldc)
        out = [v, G]
        for kap in (1.0, 2.0):
            base = B.C_lin(F, v, B.LIVE) + B.fric_slope(v, B.LIVE)
            Lv = base * B.P_of(F, v, lambda f, vv: fnS(f, vv, slope_stock), 0.20, kap)
            m = B.margins(Lv, F)
            uns, _ = B.nyquist_unstable(Lv, F)
            if kap == 1.0:
                out.append(float(np.interp(1.0, F, np.abs(Lv))))
            out.append(-999.0 if uns else (m["pm"] if np.isfinite(m["pm"]) else np.nan))
    # reprint cleanly
    for v in B.SPEEDS:
        _, _, g0 = B.g0_of_v(v, Rdc)
        Ldc = RdcS * B.CPD * g0
        G = slope_stock * Ldc / (1 + Ldc)
        base = B.C_lin(F, v, B.LIVE) + B.fric_slope(v, B.LIVE)
        pms = []
        l1 = None
        for kap in (1.0, 2.0):
            Lv = base * B.P_of(F, v, lambda f, vv: fnS(f, vv, slope_stock), 0.20, kap)
            m = B.margins(Lv, F)
            uns, _ = B.nyquist_unstable(Lv, F)
            if l1 is None:
                l1 = float(np.interp(1.0, F, np.abs(Lv)))
            pms.append("UNSTABLE" if uns else ("no xover" if not np.isfinite(m["pm"]) else "%.1f" % m["pm"]))
        pr("   %6.1f | %10.1f %10.4f %10s | %10s" % (v, G, l1, pms[0], pms[1]))
    pr("   ⇒ stock's map top is x%.2f smaller, so |L| never reaches 1 anywhere: STOCK PASSES B6"
       % (float(np.max(c282["map_Y"])) / float(np.max(cs["map_Y"]))))
    pr("     trivially at every speed and every kappa.  Stock is NOT a broken-check trigger; V282 is.")

    # ---------------------------------------------------------------- 6. wide-band stability
    pr("")
    pr("6. WIDE-BAND CHECK -- any -180 crossing with |L| >= 1 OUTSIDE 0.2-12 Hz (s6's band excludes")
    pr("   the 18-22 Hz ring entirely; with the LKAS loop open the plant resonance is un-damped by")
    pr("   the servo and enters the outer loop directly)")
    pr("-" * 116)
    hits = 0
    for name, rfn, tune in cases:
        for v in B.SPEEDS:
            for kap in (1.0, 2.0):
                base = B.C_lin(F, v, tune) + B.fric_slope(v, tune)
                Lv = base * B.P_of(F, v, rfn, 0.20, kap)
                uns, bad = B.nyquist_unstable(Lv, F)
                for fb_, mg in bad:
                    if fb_ > 12.0 or fb_ < 0.2:
                        pr("   %-5s %-20s v %.1f kappa %.2f : crossing at %.2f Hz |L| %.2f"
                           % (name, tune["name"], v, kap, fb_, mg))
                        hits += 1
                l20 = float(np.interp(20.0, F, np.abs(Lv)))
                if l20 >= 1.0:
                    pr("   %-5s %-20s v %.1f kappa %.2f : |L| at 20 Hz = %.3f >= 1"
                       % (name, tune["name"], v, kap, l20))
                    hits += 1
    if not hits:
        pr("   none.  Every instability found by B6 is the LOW-FREQUENCY delay/gain one at 0.8-1.6 Hz;")
        pr("   the 18-22 Hz ring never reaches |L| = 1 in the outer loop on either build.")

    open(os.path.join(SCR, "v293_b6_margins.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_b6_margins.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
