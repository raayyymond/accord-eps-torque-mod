# -*- coding: utf-8 -*-
"""studies/grind/adv_v290_linecheck.py -- the ONE measurement that decides which plant fit is live, and therefore whether
the V290 (ii-c) sign is right: where is the line on the V289 routes?   Agent advphys, 2026-09-09.  Analysis only.

The design's own revert branch is the SMOOTH plant fit (i).  On that fit my exact-pole model says (a) V289 is already
UNSTABLE at 16.3 Hz and (b) the (ii-c) term with the proposed sign makes it WORSE (zeta -0.016 -> -0.082), while the
OPPOSITE sign helps.  On every mode-bearing fit the proposed sign damps.  So the smooth fit is the only place the V290
sign is wrong, and V289 has already flown: if r62/r63 show no new 14-17 Hz line and the line stays pinned near 20 Hz,
the smooth fit is falsified BY THE CAR and the sign question is settled in the design's favour.

Census recipe = the record's (grind1_census / loopshape20_mode_nature): 2 s windows, 0.5 s step, engaged lateral,
present = bar 15-26 Hz prominence >= 8 AND bar 18-22 >= 40 raw.  Also a WIDE line search (10-30 Hz) so a relocated line
cannot hide outside the census band, and the deadband hazard census the hook at 0x2A1B0 needs.
Run: python adv_v290_linecheck.py   (writes _scratch/adv_v290_linecheck.txt beside it)
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
import grind_incident_r35 as GI               # noqa: E402
import _grind2_lib as G2                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, W, STEP = 100.0, 200, 50
ROUTES = (("r39", "V282"), ("r3a", "V282"), ("r3c", "V282"), ("r5e_v288", "V288r2"), ("r62_v289", "V289"), ("r63_v289", "V289"))
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def wide_line(x, fs, lo=10.0, hi=30.0, nfft=4096):
    f, P = signal.periodogram(np.asarray(x, float) - np.mean(x), fs=fs, window="hann", nfft=nfft)
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    m = (f >= lo) & (f <= hi)
    k = int(np.argmax(Rp[m]))
    return float(f[m][k]), float(Rp[m][k])


def main():
    pr("adv_v290_linecheck -- WHERE IS THE LINE on the V289 routes?  (decides the smooth-fit revert branch)")
    rows = []
    for tag, build in ROUTES:
        try:
            g = C20.load(tag)
        except Exception as e:  # noqa: BLE001
            pr("FAILED %s: %r" % (tag, e)); continue
        n_w = n_p = 0
        for aa, bb in C20.runs(g["eng"], W):
            for s in range(aa, bb - W + 1, STEP):
                seg = g["bar"][s:s + W]
                f0, prom, _, _ = GI.line_of(seg, FS)
                fw, pw = wide_line(seg, FS)
                amp = GI.band(seg, 18, 22)
                a16 = GI.band(seg, 14, 17)
                n_w += 1
                pres = np.isfinite(f0) and prom >= 8 and amp >= 40
                n_p += int(pres)
                rows.append(dict(tag=tag, build=build, f0=f0 if np.isfinite(f0) else np.nan, prom=prom, fw=fw, pw=pw,
                                 amp=amp, a16=a16, pres=pres, tq=float(np.median(np.abs(seg))),
                                 v=float(g["vego"][s:s + W].mean())))
        pr("  %-9s %-7s windows %5d, present %4d (%.1f %%)" % (tag, build, n_w, n_p, 100.0 * n_p / max(1, n_w)))
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    np.savez(os.path.join(SCR, "adv_v290_linecheck.npz"), **R)

    def q(x):
        return "%.2f [%.2f-%.2f] n=%d" % (np.median(x), np.percentile(x, 25), np.percentile(x, 75), len(x)) if len(x) >= 5 else "(n=%d)" % len(x)

    pr("\n1. CENSUS-BAND line f0 (15-26 Hz estimator), present windows, by build:")
    for b in ("V282", "V288r2", "V289"):
        m = R["pres"] & (R["build"] == b)
        pr("   %-7s f0 %s   amp 18-22 %s" % (b, q(R["f0"][m]), q(R["amp"][m])))
    pr("\n2. WIDE line (10-30 Hz estimator, no band prior) on ALL engaged windows, by build -- a relocated line cannot hide:")
    for b in ("V282", "V288r2", "V289"):
        m = (R["build"] == b) & (R["pw"] >= 8)
        pr("   %-7s wide-line f %s  (windows with prom >= 8: %d of %d = %.1f %%)" % (
            b, q(R["fw"][m]), m.sum(), (R["build"] == b).sum(), 100.0 * m.sum() / max(1, (R["build"] == b).sum())))
        h, e = np.histogram(R["fw"][m], bins=np.arange(10, 30.5, 1.0))
        pr("           histogram 10-30 Hz (1 Hz bins): " + " ".join("%d:%d" % (int(e[i]), h[i]) for i in range(len(h)) if h[i] > 0))
    pr("\n3. THE REVERT SIGNATURE the V289 prereg named: a NEW 14-17 Hz line.  14-17 Hz bar band power, ALL engaged windows:")
    for b in ("V282", "V288r2", "V289"):
        m = R["build"] == b
        pr("   %-7s band 14-17 %s   band 18-22 %s   ratio(14-17 / 18-22) median %.3f" % (
            b, q(R["a16"][m]), q(R["amp"][m]), np.median(R["a16"][m] / np.maximum(R["amp"][m], 1e-9))))
    pr("\n   windows whose WIDE line falls in 14-17.5 Hz with prominence >= 8 (the revert signature), per build:")
    for b in ("V282", "V288r2", "V289"):
        m = (R["build"] == b) & (R["pw"] >= 8)
        m16 = m & (R["fw"] >= 14) & (R["fw"] <= 17.5)
        pr("   %-7s %4d of %5d engaged windows = %.2f %%   (20 Hz band 18.5-22: %.2f %%)" % (
            b, m16.sum(), (R["build"] == b).sum(), 100.0 * m16.sum() / max(1, (R["build"] == b).sum()),
            100.0 * (m & (R["fw"] >= 18.5) & (R["fw"] <= 22)).sum() / max(1, (R["build"] == b).sum())))
    with open(os.path.join(SCR, "adv_v290_linecheck.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/adv_v290_linecheck.txt")


if __name__ == "__main__":
    main()
