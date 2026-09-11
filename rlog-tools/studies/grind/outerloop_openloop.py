# -*- coding: utf-8 -*-
"""outerloop_openloop.py -- the LATERAL-DISENGAGED natural experiment at REAL statistical power, plus
the wire-to-wire delay reconciliation.  Subagent `echoloop`, 2026-09-10.  ANALYSIS ONLY.

WHY A SECOND FILE: `outerloop_id.py` and its results have already been reported; this adds to them
without touching them.

PART A -- OPEN LOOP.  outerloop_id.py section 7 ran the engaged-vs-lateral-disengaged comparison on the
five routes it had extracted and found NO POWER above 8 m/s (0-1 disengaged windows per route per bin).
Every route already sitting in analysis-2020accord/_scratch/cache/v280 carries the same four fields the
test needs (0x18F bar/rate/SCA, 0xE4 cmd/STEER_REQUEST, carState vEgo), so the test runs over 18 routes
with no new rlog reads.  Two gates are scored side by side, because the kit's record on the
engaged/manual confound says a LEVEL gate is confounded by how much the wheel is moving at all:
    LEVEL gate  prominence >= 8 AND bar band amplitude (f0 +- 2 Hz) >= 40 raw   (the census rule)
    SHAPE gate  prominence >= 8 only                                            (level-free)
and the disengaged windows are additionally LOAD-MATCHED to the engaged interquartile range of
driver-torque rms and wheel-rate rms inside each speed bin, so an unmatched stratum cannot pass as a null.

PART B -- DELAY RECONCILIATION.  `slewburst` measured the 0x14A -> 0xE4 cross-phase at f0 as ~0 ms;
outerloop_id.py section 6 measured the same path decomposed through openpilot's own messages as
+21 to +26 ms.  A phase read AT ONE FREQUENCY is ambiguous modulo 360 deg (21 ms at 16-20 Hz is
121-190 deg); a coherence-weighted phase SLOPE over a band is not.  Both are computed here on the same
windows so the two numbers can be reconciled instead of left standing side by side.

Run: python rlog-tools/studies/grind/outerloop_openloop.py [A] [B]
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
import _grind2_lib as G2                      # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import outerloop_id as O                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
W, STEP = 200, 50
FLO, FHI = 12.0, 26.0
BINS = ((0, 4), (4, 8), (8, 13), (13, 18), (18, 25), (25, 40))
BUILD = {"r22": "V112", "r23": "V112", "r2e": "V255-ish", "r31": "V278 r3", "r32": "V280 r2",
         "r33": "V280 r2", "r34": "V280 r2", "r35": "V281 r3", "r36": "V282", "r37": "V282",
         "r38": "V282", "r39": "V282", "r3a": "V282", "r3c": "V282",
         "r5e_v288": "V288 r2", "r62_v289": "V289 r1", "r63_v289": "V289 r1", "r97": "stock"}
ROUTES = tuple(BUILD)
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def save(name):
    with open(os.path.join(SCR, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


def line_of(x, lo=FLO, hi=FHI, nfft=1024):
    f, P = signal.periodogram(x - x.mean(), fs=FS, window="hann", nfft=nfft)
    sl = (f >= 4.0) & (f <= 34.0)
    R = G2.prom_spectrum(f[sl], P[sl], 6.0, 1.5)
    return G2.locate(f[sl], P[sl], lo, hi, R=R)


def scan(tag):
    """every 2 s window of the route, labelled ENGAGED / LATERAL-OFF, with its operating point."""
    g = C20.load(tag)
    eng = g["eng"]
    n = len(g["t"])
    rows = []
    for a in range(0, n - W, STEP):
        b = a + W
        e = eng[a:b]
        if e.all():
            lab = 1
        elif not e.any():
            lab = 0
        else:
            continue
        bar = g["bar"][a:b]
        f0, prom = line_of(bar - bar.mean())
        if not np.isfinite(f0):
            continue
        A = GI.band(bar - bar.mean(), f0 - 2, f0 + 2, FS)
        rows.append(dict(tag=tag, eng=lab, f0=float(f0), prom=float(prom), A=float(A),
                         v=float(np.median(g["vego"][a:b])),
                         barrms=float(np.std(bar)),
                         raterms=float(np.std(g["wire"][a:b])),
                         idx=float(np.median(g["idx"][a:b]))))
    return rows


def secA():
    import pickle
    fp = os.path.join(SCR, "outerloop_openloop_rows.pkl")
    if os.path.exists(fp):
        rows = pickle.load(open(fp, "rb"))
    else:
        rows = []
        for t in ROUTES:
            try:
                r = scan(t)
            except Exception as e:
                pr("  %s SKIPPED: %s" % (t, str(e)[:70])); continue
            pr("  scanned %-10s %-9s  engaged %5d  lateral-OFF %5d"
               % (t, BUILD[t], sum(x["eng"] for x in r), sum(1 - x["eng"] for x in r)))
            rows += r
        pickle.dump(rows, open(fp, "wb"))
    pr("=" * 112)
    pr("PART A -- DOES THE RING APPEAR WITH LATERAL DISENGAGED?  18 ROUTES, 6 BUILDS + STOCK")
    pr("=" * 112)
    pr("Windows: 2 s / 0.5 s step on the 0x18F dejittered frame axis, ENTIRELY engaged or ENTIRELY not.")
    pr("'Lateral engaged' = 0x18F STEER_CONTROL_ACTIVE AND 0xE4 STEER_REQUEST (creep20_loop_id.load's")
    pr("own mask -- the kit's canonical definition; longitudinal-only time counts as OFF, per")
    pr("memory/feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference).")
    pr("LEVEL gate = prominence >= 8 AND bar band amplitude >= 40 raw.  SHAPE gate = prominence >= 8 only.")
    pr()
    E = [r for r in rows if r["eng"]]
    D = [r for r in rows if not r["eng"]]
    pr("TOTAL EXPOSURE: %d engaged windows, %d lateral-OFF windows, over %d routes"
       % (len(E), len(D), len(set(r["tag"] for r in rows))))
    pr()
    pr("A1 -- RAW, speed-stratified (pooled over all 18 routes)")
    pr("  %-10s | %7s %8s %8s %7s | %7s %8s %8s %7s | %s"
       % ("speed m/s", "n_eng", "lvl rate", "shp rate", "f0", "n_OFF", "lvl rate", "shp rate", "f0",
          "95% UB off (level)"))
    for lo, hi in BINS:
        e = [r for r in E if lo <= r["v"] < hi]
        d = [r for r in D if lo <= r["v"] < hi]
        el = [r for r in e if r["prom"] >= 8 and r["A"] >= 40]
        es = [r for r in e if r["prom"] >= 8]
        dl = [r for r in d if r["prom"] >= 8 and r["A"] >= 40]
        ds = [r for r in d if r["prom"] >= 8]
        ub = ("%.4f" % (3.0 / len(d))) if (d and not dl) else ("%.4f" % (len(dl) / len(d)) if d else "-")
        pr("  %4.0f-%-5.0f | %7d %8.4f %8.4f %7.1f | %7d %8.4f %8.4f %7.1f | %s"
           % (lo, hi, len(e), len(el) / max(1, len(e)), len(es) / max(1, len(e)),
              float(np.median([r["f0"] for r in el])) if el else float("nan"),
              len(d), len(dl) / max(1, len(d)), len(ds) / max(1, len(d)),
              float(np.median([r["f0"] for r in dl])) if dl else float("nan"), ub))
    pr()
    pr("A2 -- LOAD-MATCHED: lateral-OFF windows restricted, inside each speed bin, to the ENGAGED")
    pr("      interquartile range of BOTH driver-torque rms and wheel-rate rms.  This is the stratum")
    pr("      the engaged/manual confound record demands; the operating point is printed so an")
    pr("      unmatched bin is visible rather than hidden.")
    pr("  %-10s | %6s %7s %7s %7s | %6s %7s %7s %7s | %s"
       % ("speed m/s", "n_eng", "lvl", "barRMS", "rateRMS", "n_OFF", "lvl", "barRMS", "rateRMS",
          "95% UB off"))
    for lo, hi in BINS:
        e = [r for r in E if lo <= r["v"] < hi]
        d = [r for r in D if lo <= r["v"] < hi]
        if not e or not d:
            pr("  %4.0f-%-5.0f | %6d %7s %7s %7s | %6d %7s %7s %7s | %s"
               % (lo, hi, len(e), "-", "-", "-", len(d), "-", "-", "-", "no exposure"))
            continue
        bq = np.percentile([r["barrms"] for r in e], [25, 75])
        rq = np.percentile([r["raterms"] for r in e], [25, 75])
        dm = [r for r in d if bq[0] <= r["barrms"] <= bq[1] and rq[0] <= r["raterms"] <= rq[1]]
        el = [r for r in e if r["prom"] >= 8 and r["A"] >= 40]
        dl = [r for r in dm if r["prom"] >= 8 and r["A"] >= 40]
        ub = ("%.4f" % (3.0 / len(dm))) if (dm and not dl) else ("%.4f" % (len(dl) / len(dm)) if dm else "no exposure")
        pr("  %4.0f-%-5.0f | %6d %7.4f %7.1f %7.1f | %6d %7s %7s %7s | %s"
           % (lo, hi, len(e), len(el) / len(e),
              float(np.median([r["barrms"] for r in e])), float(np.median([r["raterms"] for r in e])),
              len(dm),
              ("%.4f" % (len(dl) / len(dm))) if dm else "-",
              ("%.1f" % np.median([r["barrms"] for r in dm])) if dm else "-",
              ("%.1f" % np.median([r["raterms"] for r in dm])) if dm else "-", ub))
    pr()
    pr("A3 -- per route, so a single route cannot carry the pooled result")
    pr("  %-10s %-9s | %6s %7s | %6s %7s %7s | %s"
       % ("route", "build", "n_eng", "lvl", "n_OFF", "lvl", "shp", "max OFF speed (m/s)"))
    for t in ROUTES:
        e = [r for r in E if r["tag"] == t]
        d = [r for r in D if r["tag"] == t]
        if not e and not d:
            continue
        el = [r for r in e if r["prom"] >= 8 and r["A"] >= 40]
        dl = [r for r in d if r["prom"] >= 8 and r["A"] >= 40]
        ds = [r for r in d if r["prom"] >= 8]
        pr("  %-10s %-9s | %6d %7.4f | %6d %7.4f %7.4f | %.1f"
           % (t, BUILD[t], len(e), len(el) / max(1, len(e)), len(d),
              len(dl) / max(1, len(d)), len(ds) / max(1, len(d)),
              max([r["v"] for r in d]) if d else float("nan")))
    pr()
    pr("A4 -- the HIGH-DEMAND engaged stratum (idx >= 20), which is the grinding mode, against the")
    pr("      lateral-OFF windows at the same speed.  Demand cannot be matched (there is no demand")
    pr("      with lateral off), so this is an upper-vs-null comparison, not a matched one.")
    pr("  %-10s | %7s %8s %7s | %7s %8s | %s" % ("speed m/s", "n_hi", "lvl rate", "f0", "n_OFF",
                                                 "lvl rate", "ratio"))
    for lo, hi in BINS:
        e = [r for r in E if lo <= r["v"] < hi and r["idx"] >= 20]
        d = [r for r in D if lo <= r["v"] < hi]
        el = [r for r in e if r["prom"] >= 8 and r["A"] >= 40]
        dl = [r for r in d if r["prom"] >= 8 and r["A"] >= 40]
        re_ = len(el) / max(1, len(e))
        rd = len(dl) / max(1, len(d))
        pr("  %4.0f-%-5.0f | %7d %8.4f %7.1f | %7d %8.4f | %s"
           % (lo, hi, len(e), re_, float(np.median([r["f0"] for r in el])) if el else float("nan"),
              len(d), rd, ("%.1fx" % (re_ / rd)) if rd > 0 else (">= %.0fx" % (re_ * len(d) / 3.0)
                                                                if d and re_ > 0 else "-")))


def secB():
    pr("=" * 112)
    pr("PART B -- RECONCILING THE TWO 0x14A -> 0xE4 DELAY NUMBERS")
    pr("=" * 112)
    pr("`slewburst`: cross-phase AT f0 ~ 0 ms.  outerloop_id.py section 6: +21 to +26 ms, from a")
    pr("coherence-weighted phase SLOPE over 13-25 Hz through openpilot's own messages.  Both are")
    pr("computed below on the SAME grinding windows of the same routes.  A phase at one frequency is")
    pr("ambiguous modulo 360 deg -- 21-26 ms is 121-190 deg at 16-20 Hz -- and a slope is not.")
    pr()
    pr("  %-5s %-9s %-7s %6s | %8s %8s | %9s %9s | %8s"
       % ("route", "build", "stratum", "f0", "phase@f0", "-> ms", "slope ms", "coh@f0", "meanCoh"))
    for tag, gate, lab in [(t, (lambda r: r["present"]), "pooled") for t in O.ROUTES] +                           [(t, (lambda r: r["present"] and r["idx"] >= 20), "hi-dmd") for t in O.ROUTES]:
        g = O.G(tag)
        rs = [r for r in O.cen(tag) if gate(r)]
        if len(rs) < 12:
            continue
        keys = ["wire_ang", "cmd"]
        f, Xs = O.xspec(g, rs, keys)
        S = O.pool(Xs, keys)
        f0 = float(np.median([r["f0"] for r in rs]))
        sel = (f >= 13.0) & (f <= 25.0)
        X = S[("cmd", "wire_ang")]
        ph0 = np.degrees(np.angle(O.atf(f, X, f0)))
        co = np.abs(S[("wire_ang", "cmd")]) ** 2 / (S[("wire_ang", "wire_ang")].real
                                                    * S[("cmd", "cmd")].real)
        A = np.polyfit(2 * np.pi * f[sel], np.unwrap(np.angle(X[sel])), 1, w=co[sel])
        pr("  %-5s %-9s %-7s %6.2f | %+8.1f %8.2f | %+9.2f %9.3f | %8.3f  n=%d"
           % (tag, O.BUILD[tag], lab, f0, ph0, -ph0 / 360.0 / f0 * 1e3, -A[0] * 1e3,
              float(np.interp(f0, f, co)), float(co[sel].mean()), len(rs)))
    pr()
    pr("  'phase@f0 -> ms' is the single-frequency reading with NO unwrapping -- what a phase-at-f0")
    pr("  method returns.  'slope ms' is the group delay.  Where they disagree by ~ one cycle of f0")
    pr("  (60-77 ms at 13-16 Hz, 50 ms at 20 Hz) the single-frequency number has wrapped.")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["A", "B"]):
        globals()["sec%s" % s]()
    save("outerloop_openloop.txt")
