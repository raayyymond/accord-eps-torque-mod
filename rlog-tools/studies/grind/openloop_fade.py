# -*- coding: utf-8 -*-
"""openloop_fade.py -- SECOND AND THIRD METHODS FOR zeta_p, and one that FAILED.
Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

The lateral-disengaged stratum (openloop_ring.py section C) is the natural experiment, but it opens
the loop by removing the LKAS command entirely, so it also removes the excitation.  These are three
ways to vary the LOOP GAIN while the loop is still being driven.

M1  THE POST-PID FADE.  FAILED, reported because a failed method is a result.  m = ((255*B)&0xFFFF)>>8
    with B = lerp(fadeB, |bar|//32) multiplies the whole LKAS output, so it is a loop-gain knob --
    but on the wire it is effectively BINARY: m = 254 for >75 % of engaged creep samples on every
    route and 76 at the 1st and 5th percentiles, with almost nothing between.  There is no continuum
    to regress on.  Measured below and abandoned.

M2  THE ACTING Kp.  On the Kp-LERP builds (V278 rev 3, V280 rev 2) the acting Kp runs 248 -> 696 with
    the live demand index; on V281r3/V282/V288/V289 it is pinned flat at 248 (KP.FLAT.Y0), so those
    routes contribute one point each.  zeta_eff against acting Kp, extrapolated to Kp = 0.
    🛑 CONFOUND, already on the record (STATE correction 6): acting Kp is confounded with demand
    index, so this is NOT a clean gain sweep.  Reported with the confound named, not as a clean number.

M3  ⭐ V289'S OWN NOTCH IS AN IN-SITU LOOP-OPENING AT 20 Hz.  V289 rev 1 put a Q14 TDF-II notch at
    20.036 Hz, Q 3.0, on the CLAMPED LKAS RATE-LOOP OUTPUT (hook 0x2A174 -> cave 0xC4C00).  At 20 Hz
    the loop's own return path is therefore cut, while the plant, the excitation, the driver and the
    speed are all unchanged -- which is exactly the configuration the proposed build approximates,
    but WITH the car still being driven by LKAS.  So the 18-22 Hz line's width on r62/r63 measures
    the mode's damping with the loop open AT THAT FREQUENCY.  This is the closest thing on the car to
    a direct zeta_p, and it has already been flown.

Run: python openloop_fade.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import openloop_lib as L                       # noqa: E402
import openloop_zeta as Z                      # noqa: E402
import fvlc_lib as F                           # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
NPER = 1024
OUT = []
ROUTES = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r5e_v288": "V288",
          "r62_v289": "V289", "r63_v289": "V289", "r35": "V281r3",
          "r32": "V280r2", "r33": "V280r2", "r34": "V280r2", "r31": "V278r3"}
KPLERP = ("r31", "r32", "r33", "r34")


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def parts(tag):
    g = L.load(tag)
    c = F.cells(ROUTES[tag])
    B = np.interp(np.abs(g["bar"]) // 32, c["fadeB"][0], c["fadeB"][1])
    m = (((255.0 * B).astype(np.int64) & 0xFFFF) >> 8).astype(float)
    kp = np.interp(g["idx"], c["kp_X"], c["kp_Y"])
    return g, m, kp


def zrow(lab, segs_, flo, fhi, extra="", nboot=150):
    if len(segs_) < 4:
        pr("  %-30s | %6s %4d | insufficient exposure" % (lab, "-", len(segs_)))
        return None
    r = Z.zeta_line(segs_, flo, fhi, NPER, nboot=nboot, seed=5)
    line = (r["bump"] >= 1.8) and (r["prom_data"] >= 1.8) and (not r["edge"])
    pr("  %-30s | %6.0f %4d | %6.3f %8.4f [%6.4f %6.4f] %6.2f %6.2f %8s %s"
       % (lab, r["secs"], r["nseg"], r["f0"], r["z"], r["lo"], r["hi"],
          min(r["bump"], 999.0), min(r["prom_data"], 999.0), "LINE" if line else "NO LINE", extra))
    return r


def hdr():
    pr("  %-30s | %6s %4s | %6s %8s %-15s %6s %6s %8s" %
       ("stratum", "secs", "nseg", "f0", "E3b z", "[95% CI]", "bump", "prom", "verdict"))
    pr("-" * 126)


def main():
    pr("=" * 126)
    pr("SECOND AND THIRD METHODS FOR zeta_p -- AND ONE THAT FAILED")
    pr("=" * 126)
    P = {t: parts(t) for t in ROUTES}

    pr()
    pr("M1 -- THE POST-PID FADE: FAILED, NO LEVERAGE [reported because a failed method is a result]")
    pr("-" * 126)
    pr("  %-10s %-8s | %-42s | %s" % ("route", "build", "fade m, engaged 0-8 m/s (p1/p5/p25/p50/p75/p95)",
                                      "frac of samples at m = 254"))
    for t, b in ROUTES.items():
        g, m, kp = P[t]
        msk = g["eng"] & g["have"] & (g["vego"] < 8)
        if msk.sum() < 100:
            continue
        mm = m[msk]
        pr("  %-10s %-8s | %-42s | %.4f"
           % (t, b, " ".join("%6.1f" % x for x in np.percentile(mm, [1, 5, 25, 50, 75, 95])),
              float(np.mean(mm >= 253.5))))
    pr("  ⇒ m is effectively BINARY (254 or 76) with 75-95 %% of engaged creep at 254.  There is no")
    pr("  continuum of loop gain to regress zeta against.  M1 is abandoned, not reported as a number.")

    pr()
    pr("M2 -- THE ACTING Kp AXIS (Kp-LERP builds only: V278r3, V280r2; 248 -> 696)")
    pr("-" * 126)
    pr("  🛑 CONFOUNDED with demand index by construction [STATE correction 6].  Read as a trend, not")
    pr("  a clean gain sweep.  Engaged, 0-8 m/s, hands-off; segments >= %.2f s." % (NPER / FS))
    hdr()
    pts = []
    kall = np.concatenate([P[t][2][P[t][0]["eng"] & (P[t][0]["vego"] < 8)] for t in KPLERP])
    edges = np.percentile(kall, [0, 33, 66, 100])
    for i in range(3):
        klo, khi = edges[i], edges[i + 1]
        segs_, kms = [], []
        for t in KPLERP:
            g, m, kp = P[t]
            msk = (g["eng"] & g["have"] & (g["vego"] < 8) & (g["press"] <= 0.5)
                   & (kp >= klo) & ((kp < khi) if i < 2 else (kp <= khi)))
            for a, b in L.runs(msk, NPER):
                segs_.append(g["bar"][a:b] - np.mean(g["bar"][a:b]))
                kms.append(float(np.median(kp[a:b])))
        r = zrow("Kp %.0f-%.0f" % (klo, khi), segs_, 16.0, 26.0,
                 extra="med Kp %.0f" % (np.median(kms) if kms else np.nan))
        if r and np.isfinite(r["z"]) and kms:
            pts.append((float(np.median(kms)), r["z"], r["lo"], r["hi"]))
    pr()
    pr("  PER BUILD, one point each at that build's median acting Kp (engaged 0-8 m/s, hands-off):")
    hdr()
    per = []
    for b, ts in (("V278r3", ["r31"]), ("V280r2", ["r32", "r33", "r34"]), ("V281r3", ["r35"]),
                  ("V282", ["r39", "r3a", "r3c"]), ("V288", ["r5e_v288"])):
        segs_, kms = [], []
        for t in ts:
            g, m, kp = P[t]
            msk = g["eng"] & g["have"] & (g["vego"] < 8) & (g["press"] <= 0.5)
            for a, bb in L.runs(msk, NPER):
                segs_.append(g["bar"][a:bb] - np.mean(g["bar"][a:bb]))
                kms.append(float(np.median(kp[a:bb])))
        r = zrow(b, segs_, 16.0, 26.0, extra="med Kp %.0f" % (np.median(kms) if kms else np.nan))
        if r and np.isfinite(r["z"]) and kms:
            per.append((float(np.median(kms)), r["z"], r["lo"], r["hi"]))
    for nm, pp in (("Kp terciles", pts), ("per build", per)):
        if len(pp) >= 3:
            A = np.polyfit([p[0] for p in pp], [p[1] for p in pp], 1)
            pr("  %-12s linear fit zeta = %.5g + %.3e * Kp  ->  intercept at Kp = 0 : %.4f"
               % (nm, A[1], A[0], np.polyval(A, 0.0)))

    pr()
    pr("M3 -- ⭐ V289's NOTCH AS AN IN-SITU LOOP-OPENING AT 20 Hz")
    pr("-" * 126)
    pr("  V289 rev 1 = V282 + a Q14 TDF-II notch at 20.036 Hz, Q 3.0, on the CLAMPED LKAS rate-loop")
    pr("  OUTPUT (hook 0x2A174 -> cave 0xC4C00) + the fb lag pole 16.5 -> 25 Hz.  At 20 Hz the loop's")
    pr("  return path is cut while plant, excitation, driver and speed are unchanged.  So the residual")
    pr("  18-22 Hz line on r62/r63 is the mode WITH THE LOOP OPEN AT THAT FREQUENCY -- and unlike the")
    pr("  lateral-disengaged stratum, LKAS is still driving the car.")
    pr("  ⚠ The notch is Q 3.0, so it is not a perfect open: at 18 and 22 Hz it is well off the notch")
    pr("  centre and the loop is only partly cut.  Reported per sub-band so that is visible.")
    hdr()
    for lab, ts, flo, fhi in (("V282  16-26 Hz (loop CLOSED)", ["r39", "r3a", "r3c"], 16.0, 26.0),
                              ("V282  19-21 Hz (loop CLOSED)", ["r39", "r3a", "r3c"], 18.0, 23.0),
                              ("V289  16-26 Hz (notch @20.04)", ["r62_v289", "r63_v289"], 16.0, 26.0),
                              ("V289  18-23 Hz (notch @20.04)", ["r62_v289", "r63_v289"], 18.0, 23.0),
                              ("V289  12-18 Hz (relocated ring)", ["r62_v289", "r63_v289"], 12.0, 18.0),
                              ("V288  16-26 Hz (loop CLOSED)", ["r5e_v288"], 16.0, 26.0),
                              ("V288  18-23 Hz (loop CLOSED)", ["r5e_v288"], 18.0, 23.0)):
        segs_ = []
        for t in ts:
            g, m, kp = P[t]
            msk = g["eng"] & g["have"] & (g["vego"] < 8)
            segs_ += [g["bar"][a:b] - np.mean(g["bar"][a:b]) for a, b in L.runs(msk, NPER)]
        zrow(lab, segs_, flo, fhi)
    pr()
    with open(os.path.join(L.SCR, "openloop_fade.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote _scratch/openloop_fade.txt")


if __name__ == "__main__":
    main()
