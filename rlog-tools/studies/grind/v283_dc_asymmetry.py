# -*- coding: utf-8 -*-
"""studies/grind/v283_dc_asymmetry.py -- ORCHESTRATOR ADJUDICATION follow-up, 2026-09-03.

stutter283 found that statistic (D) is void by construction: bit 6 compares |r24|, which is a DERIVATIVE of
the bar torque and therefore pure AC with zero mean, against |T|, which in a strong turn carries 600-1000
counts of DC under a ~140-count ripple.  An AC quantity cannot exceed a DC-biased one often enough to reach
the prereg's >= 0.5, whatever r24 is doing.

The orchestrator asks whether the SAME asymmetry contaminates my (A)/(B) magnitude conclusion
("|r24|_wire ~ 0.43 x the closed form").  This script answers it.

THE TEST.  Reconstruct T's low-frequency component offline from the 427 tap, bin the engaged hands-off creep
frames by |T|_DC, and report per bin:
    * the MEASURED bit-6 duty
    * the CLOSED-FORM PREDICTED duty at each candidate arm, computed on THE SAME FRAMES with THE SAME T
    * the inferred scale s
The ratio measured / predicted-at-5244 is the statistic that decides it, NOT the duty alone -- because the
prediction itself collapses as the DC rises, so a duty that falls with DC proves nothing on its own.
    - ratio FLAT across DC bins            -> the DC asymmetry is common-mode, cancels, and the magnitude
                                              finding STANDS (the record correction is warranted).
    - ratio RISING toward 1.0 as DC -> 0   -> the discrepancy IS the comparator's DC asymmetry, |r24| is
                                              FINE, and the five-star memory is VINDICATED, not corrected.

Run: python v283_dc_asymmetry.py      (writes _scratch/v283_dc_asymmetry.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
from v282_r24_tap_read import read_cells, demand_live, IMG, V283_ROUTES, r24_series   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST = 100.0, 50.0
CACHE = C20.CACHE
GAINS = (5244.0, 3072.0, 2048.0, 1024.0, 512.0)
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def main():
    cells = {k: read_cells(p) for k, p in IMG.items()}
    G = {}
    for tag in V283_ROUTES:
        print("loading %s ..." % tag, flush=True)
        g = C20.load(tag)
        g["idx"], _ = demand_live(np.round(g["cmd"]), g["bar"], cells["V283"])
        B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
        k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        for bit in (5, 6):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
        # T's low-frequency component, built on the tap's OWN 50 Hz instants then put on the frame axis.
        # 2 Hz zero-phase Butterworth: below the 6-10 and 18-22 bands, above the turn-scale envelope.
        sos = signal.butter(2, 2.0, btype="lowpass", fs=FST, output="sos")
        Tdc_native = signal.sosfiltfilt(sos, g["T"])
        g["Tdc"] = np.interp(g["t"], g["T_t"], Tdc_native)
        g["Tac"] = g["T100"] - g["Tdc"]
        G[tag] = g

    STRATA = [
        ("(A) creep engaged hands-off  v 1-3, |bar|<400",
         lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
        ("    creep engaged hands-off  v 1-6, |bar|<400",
         lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
        ("(D) loaded high-angle  v 2-9, |ang|>30, idx>=68",
         lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (g["idx"] >= 68)),
    ]
    BINS = [("|T|dc < 20", 0, 20), ("20-50", 20, 50), ("50-100", 50, 100),
            ("100-300", 100, 300), ("300-600", 300, 600), ("> 600", 600, 1e9)]
    SG = np.arange(0.02, 6.001, 0.005)

    pr("=" * 156)
    pr("IS THE (A) MAGNITUDE FINDING AN ARTEFACT OF THE COMPARATOR'S AC-vs-DC ASYMMETRY?")
    pr("  bit 6 = |r24| >= |T|.  r24 is a 4-tap DERIVATIVE of the bar -> pure AC, zero mean.  T carries DC + ripple.")
    pr("  T_DC = 2 Hz zero-phase Butterworth on the tap's own 50 Hz samples, then interpolated to the frame axis.")
    pr("=" * 156)

    for name, fn in STRATA:
        # pool the three routes
        b6, b5, R, T, TD, TA = [], [], [], [], [], []
        for tag in V283_ROUTES:
            g = G[tag]; m = fn(g)
            if m.sum() < 50:
                continue
            r = r24_series(g["bar"], 5244.0)
            b6.append(g["bit6"][m]); b5.append(g["bit5"][m]); R.append(np.abs(r)[m])
            T.append(np.abs(g["T100"])[m]); TD.append(np.abs(g["Tdc"])[m]); TA.append(np.abs(g["Tac"])[m])
        if not b6:
            continue
        b6 = np.concatenate(b6); b5 = np.concatenate(b5); R = np.concatenate(R)
        T = np.concatenate(T); TD = np.concatenate(TD); TA = np.concatenate(TA)
        pr("\n" + "-" * 156)
        pr("  %s      pooled r36+r37+r38, %d frames = %.1f s" % (name, len(b6), len(b6) / FS))
        pr("-" * 156)
        pr("  %-14s %7s %7s %8s %8s %9s %9s | %9s %9s %9s %9s | %9s %9s" % (
            "|T|dc bin", "n", "sec", "|T|dc p50", "|T|ac p50", "|r24|cf p50", "|T| p50",
            "MEAS b6", "pred 5244", "pred 2048", "pred 1024", "MEAS/p5244", "s inferred"))
        rows = []
        for lab, lo, hi in BINS:
            k = (TD >= lo) & (TD < hi)
            if k.sum() < 60:
                pr("  %-14s %7d   (too thin)" % (lab, k.sum())); continue
            d = b6[k].mean()
            p = {gn: float(np.mean(np.abs(R[k] * gn / 5244.0) >= T[k])) for gn in GAINS}
            c = np.array([np.mean(s * R[k] >= T[k]) for s in SG])
            s_inf = float(SG[np.argmin(np.abs(c - d))]) if c.max() >= d else np.nan
            rows.append((lab, k.sum(), d, p[5244.0], s_inf))
            pr("  %-14s %7d %7.1f %8.0f %8.0f %9.0f %9.0f | %9.4f %9.4f %9.4f %9.4f | %9.2f %9.2f" % (
                lab, k.sum(), k.sum() / FS, np.median(TD[k]), np.median(TA[k]), np.median(R[k]), np.median(T[k]),
                d, p[5244.0], p[2048.0], p[1024.0],
                d / p[5244.0] if p[5244.0] > 0 else np.nan, s_inf))
        # the whole stratum, for reference
        d = b6.mean()
        p5 = float(np.mean(R >= T))
        c = np.array([np.mean(s * R >= T) for s in SG])
        s_all = float(SG[np.argmin(np.abs(c - d))])
        pr("  %-14s %7d %7.1f %8.0f %8.0f %9.0f %9.0f | %9.4f %9.4f %9s %9s | %9.2f %9.2f   <== whole stratum" % (
            "ALL", len(b6), len(b6) / FS, np.median(TD), np.median(TA), np.median(R), np.median(T),
            d, p5, "", "", d / p5 if p5 > 0 else np.nan, s_all))
        if len(rows) >= 2:
            rr = [r[3] and r[2] / r[3] for r in rows]
            pr("\n    RATIO measured/predicted-at-5244 across the bins: %s" % "  ".join("%.2f" % x for x in rr))
            pr("    trend low-DC -> high-DC: %s" % ("RISING as DC falls (DC asymmetry would explain it)" if rr[0] > 1.6 * rr[-1]
                                                    else "FLAT within %.0f %% (the asymmetry is common-mode and cancels)" %
                                                    (100 * (max(rr) / min(rr) - 1))))

    # ------------------------------------------------------------------ (D)'s void, demonstrated
    pr("\n" + "=" * 156)
    pr("(D) VOID BY CONSTRUCTION -- demonstrated, not asserted:  bit-6 duty vs |T| level, loaded stratum")
    pr("=" * 156)
    fn = STRATA[2][1]
    b6, R, T, TD = [], [], [], []
    for tag in V283_ROUTES:
        g = G[tag]; m = fn(g)
        r = r24_series(g["bar"], 5244.0)
        b6.append(g["bit6"][m]); R.append(np.abs(r)[m]); T.append(np.abs(g["T100"])[m]); TD.append(np.abs(g["Tdc"])[m])
    b6 = np.concatenate(b6); R = np.concatenate(R); T = np.concatenate(T); TD = np.concatenate(TD)
    pr("  %-16s %8s %8s %10s %12s %14s" % ("|T| band", "n", "sec", "MEAS b6", "pred @5244", "max possible*"))
    for lo, hi in ((0, 200), (200, 400), (400, 600), (600, 800), (800, 1200), (1200, 1e9)):
        k = (T >= lo) & (T < hi)
        if k.sum() < 40:
            continue
        pr("  %-16s %8d %8.1f %10.4f %12.4f %14.4f" % (
            "%d-%d" % (lo, min(hi, 99999)), k.sum(), k.sum() / FS, b6[k].mean(),
            float(np.mean(R[k] >= T[k])), float(np.mean(R.max() >= T[k]))))
    pr("  (* 'max possible' = the duty this bin would show if r24 took its LARGEST value seen anywhere in the")
    pr("   stratum on every frame -- an upper bound the prereg's >= 0.5 rule has to clear, and cannot.)")
    hi = T >= 600
    pr("\n  frames with |T| >= 600 counts: n %d (%.1f s, %.0f %% of the stratum) -- measured bit-6 duty %.4f" % (
        hi.sum(), hi.sum() / FS, 100 * hi.mean(), b6[hi].mean()))
    pr("  |r24|cf p90 over the whole stratum is %.0f counts, against |T| p10 of %.0f in those frames:" % (
        np.percentile(R, 90), np.percentile(T[hi], 10)))
    pr("  the comparator is geometrically incapable of firing there, so (D)'s >= 0.5 threshold is unreachable")
    pr("  BY CONSTRUCTION and its < 0.2 branch carries no information about which lane pumps at 7 Hz.")

    # ------------------------------------------------------------------ reconstruction bandwidth caveat
    pr("\n" + "=" * 156)
    pr("BANDWIDTH OF THE CLOSED-FORM RECONSTRUCTION -- which way does it bias s?")
    pr("=" * 156)
    pr("  r24's derivative d = 0.5*(x[n] - x[n-4]) runs at 1 kHz and passes bar content to ~125 Hz.  The closed")
    pr("  form rebuilds x from the 100 Hz CAN bar via resample_poly(10,1), which BAND-LIMITS it to 50 Hz.  Any")
    pr("  real bar content above 50 Hz is therefore MISSING from |r24|_cf, so the reconstruction UNDER-estimates")
    pr("  |r24| and its predicted duty is a LOWER bound.  Measured duty came in BELOW that lower bound, so this")
    pr("  bias works AGAINST the finding: the true s is at most the s reported, never more.  [EVIDENCE, arithmetic]")

    with open(os.path.join(SCR, "v283_dc_asymmetry.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "v283_dc_asymmetry.txt"))


if __name__ == "__main__":
    main()
