# -*- coding: utf-8 -*-
"""c4: (a) the D lever's DOSE -- exact discrete algebra of the stage swept over D and over the jerk cutoff,
weighted by the measured in-band input power of the real routes; (b) a second, better-conditioned estimate of
the true model->achieved group delay per build, from the band phase at >=15 m/s.

(a) is arithmetic on the stage's own transfer, not a prediction of the car.
(b) is a MEASUREMENT of a closed-loop transfer from a logged input and a logged output.

usage: python c4_dose.py
"""
import json, os, sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
import v282cmp as V  # noqa: E402
from c2_stage import CFG, LAT_SMOOTH, DT, H_stage, H_canc, segs_for, band_stats, reconstruct  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]
GROUPS = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
          "T64": ["0000006c--68c6e94b17", "0000006d--05e83bb04f"],
          "T5/T4": ["00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]}


def flat_weights(f1, f2, npts=200):
    """Band weights: the measured input spectra are near-flat inside these narrow bands, so a uniform grid
    reproduces the power-weighted average to <1 ms (checked against c2's own weights)."""
    f = np.linspace(f1, f2, npts)
    return f, np.ones_like(f)


def summarise(f, w, H):
    lag = -np.angle(H) / (2 * np.pi * f)
    return float(np.average(np.abs(H), weights=w)), float(np.average(lag, weights=w) * 1e3)


def main():
    print("=" * 124)
    print("A. DOSE OF THE `SteerDelay` TOGGLE.  D = SteerDelay + 0.1.  Exact discrete algebra of the stage.")
    print("   Rows are the flown configurations; columns sweep D.  |H| / lag_ms of the CANCELLER ALONE")
    print("   (the ref filter is a separate, already-named lever and multiplies on top unchanged).")
    print("=" * 124)
    Ds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.50]
    for fc in (1.2, 4.0, 8.0, 1e6):
        lbl = "F_j == 1 (ideal)" if fc > 1e5 else "jerk cutoff %.1f Hz" % fc
        print("\n   %s" % lbl)
        print("      band Hz    " + "".join("     D=%.2f    " % d for d in Ds))
        print("                 " + "".join("  |H|   lag_ms " for d in Ds))
        for (f1, f2) in BANDS:
            f, w = flat_weights(f1, f2)
            row = "      %.2f-%.2f  " % (f1, f2)
            for d in Ds:
                n = int(d / DT + 1e-9)
                h, l = summarise(f, w, H_canc(f, n, fc))
                row += " %5.3f %6.1f  " % (h, l)
            print(row)

    print()
    print("=" * 124)
    print("B. DOSE OF `HONDA_ACCORD_JERK_LP_HZ` (code constant -- NO toggle exists; AccordJerkLpHz is ABSENT")
    print("   from all 15 routes' initData).  At each build's own flown D.  fc -> inf is the ideal canceller.")
    print("=" * 124)
    for lbl, D in (("V282 flown D=0.300", 0.300), ("rev 6.4 flown D=0.399", 0.399), ("rev 5 flown D=0.386", 0.386)):
        print("\n   %s" % lbl)
        print("      band Hz    " + "".join("   fc=%-5s  " % ("%.1f" % c if c < 1e5 else "inf") for c in (1.2, 2.0, 4.0, 8.0, 16.0, 1e6)))
        for (f1, f2) in BANDS:
            f, w = flat_weights(f1, f2)
            row = "      %.2f-%.2f  " % (f1, f2)
            for c in (1.2, 2.0, 4.0, 8.0, 16.0, 1e6):
                n = int(D / DT + 1e-9)
                h, l = summarise(f, w, H_canc(f, n, c))
                row += " %5.3f %5.1f  " % (h, l)
            print(row)

    print()
    print("=" * 124)
    print("C. THE WHOLE STAGE as flown, and the two counterfactuals that need no code change:")
    print("   (i) AccordRefFilter -> 0.0 ;  (ii) SteerDelay pinned to 0.2 (D = 0.300, what V282 flew).")
    print("=" * 124)
    cases = [("V282 as flown        ", 0.300, 1.2, 0.00),
             ("rev 6.4 as flown     ", 0.399, 4.0, 0.06),
             ("rev 6.4, RefFilter 0 ", 0.399, 4.0, 0.00),
             ("rev 6.4, RF0 + D=0.30", 0.300, 4.0, 0.00),
             ("rev 5 as flown       ", 0.386, 1.2, 0.12),
             ("rev 5, RefFilter 0   ", 0.386, 1.2, 0.00)]
    print("      case                     " + "".join("   %.2f-%.2f Hz   " % b for b in BANDS))
    print("                               " + "".join("   |H|   lag_ms  " for b in BANDS))
    for name, D, fc, rf in cases:
        row = "      %-24s " % name
        for (f1, f2) in BANDS:
            f, w = flat_weights(f1, f2)
            n = int(D / DT + 1e-9)
            h, l = summarise(f, w, H_stage(f, n, fc, rf))
            row += "  %5.3f %6.1f   " % (h, l)
        print(row)

    print()
    print("=" * 124)
    print("D. SECOND ESTIMATE of the true model->achieved group delay, from the BAND PHASE at >=15 m/s")
    print("   (runs >=60 s, coherence printed).  This is the quantity the learner is trying to estimate.")
    print("   err = D_flown - this.  NEGATIVE = the canceller's D UNDER-states the real lag.")
    print("=" * 124)
    out = {}
    print("      %-22s %-7s %-8s" % ("route", "group", "D_flown") +
          "".join("   %.2f-%.2f Hz        " % b for b in BANDS))
    print("      %-22s %-7s %-8s" % ("", "", "") + "".join("  lag_ms  coh  err_ms " for b in BANDS))
    for r in CFG:
        S = V.load(r)
        R = reconstruct(S, CFG[r])
        Dfl = float(np.median(np.nan_to_num(S["lat_delay"], nan=0.2))) + LAT_SMOOTH
        R["y"] = np.nan_to_num(S["la_pose"])
        row = "      %-22s %-7s %8.3f" % (r, CFG[r]["g"], Dfl)
        rec = {}
        for (f1, f2) in BANDS:
            nps = 4096 if f2 <= 0.30 else (2048 if f2 <= 0.60 else 1024)
            sg = segs_for(S, R, "u", "y", vmin=15.0, min_s=60.0)
            bs = band_stats(sg, f1, f2, nps)
            if bs is None:
                row += "     --    --     --  "
                continue
            row += "  %6.1f %5.2f %+6.0f " % (bs["lag_ms"], bs["coh"], (Dfl * 1e3 - bs["lag_ms"]))
            rec["%.2f-%.2f" % (f1, f2)] = dict(lag_ms=bs["lag_ms"], coh=bs["coh"], sec=bs["sec"],
                                               err_ms=Dfl * 1e3 - bs["lag_ms"])
        print(row)
        out[r] = dict(group=CFG[r]["g"], D_flown=Dfl, bands=rec)
        del S, R
    with open(os.path.join(HERE, "c4_xy_delay.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print()
    for g in ("V282", "V282old", "T64", "T64B", "T5", "T4", "T6?", "V293a"):
        rs = [r for r in out if out[r]["group"] == g]
        for b in ("0.15-0.30", "0.30-0.60"):
            vals = [out[r]["bands"][b]["lag_ms"] for r in rs if b in out[r]["bands"]]
            if vals:
                print("   group %-8s band %s   mean X->Y lag %6.1f ms over %d routes   mean D_flown %.3f" %
                      (g, b, float(np.mean(vals)), len(vals), float(np.mean([out[r]["D_flown"] for r in rs]))))


if __name__ == "__main__":
    main()
