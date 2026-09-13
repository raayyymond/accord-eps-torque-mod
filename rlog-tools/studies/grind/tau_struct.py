# -*- coding: utf-8 -*-
"""tau_struct.py -- STRUCTURE of the cmd -> wheel path, 0.1-10 Hz, before any tau number is quoted.
Subagent taumeasure, 2026-09-13.  Analysis only: builds nothing, sends nothing, flashes nothing.

Why this exists.  The brief asks for a cross-correlation lag of cmd(0xE4) against the 0x18F RATE.  A
correlation lag is only a transport delay if the path between the two is a GAIN over the band used.  If
cmd -> rate is a differentiator (torque-in / angle-out spring: rate leads cmd by +90 deg) the correlation
peak sits at a NEGATIVE lag for reasons that have nothing to do with delay.  So: measure |H| and phase
first, pick the band and the output channel afterwards.

Also fixes the hands-off definition.  `bar` is the TORSION BAR, which carries road + assist reaction even
with the driver's hands off (engaged, not-pressed p50 |bar| = 139 raw), so an instantaneous |bar| cut is
not a hands-off test and it shreds the stretches.  Here: rolling max of |bar| over +-0.3 s, plus
carState.steeringPressed dilated +-0.5 s where the cache carries it.

Outputs _scratch/tau_struct.txt.   Run: python rlog-tools/studies/grind/tau_struct.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20   # noqa: E402
import v280_map_profiles as V   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
FS = 100.0
ROUTES = [("r6c", "V282"), ("r39", "V282"), ("r35", "V281r3"),
          ("r6d_v292", "V292"), ("r6e_v292", "V292"), ("r6f_v292", "V292")]
BANDS = [(0.0, 3.0), (3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0)]
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def roll_max(x, half):
    """rolling max of |x| over +-half samples, via a maximum filter."""
    from scipy.ndimage import maximum_filter1d
    return maximum_filter1d(np.abs(x), size=2 * half + 1, mode="nearest")


def dilate(m, half):
    from scipy.ndimage import maximum_filter1d
    return maximum_filter1d(m.astype(np.uint8), size=2 * half + 1, mode="nearest") > 0


def handsoff(g, tag, barmax=800.0):
    """engaged AND rolling-max |bar| < barmax AND (not steeringPressed, dilated) where available."""
    m = g["eng"] & (roll_max(g["bar"], 30) < barmax)
    raw = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    if "cs_press" in raw:
        p = np.interp(g["t"], raw["tcs"], raw["cs_press"].astype(float)) > 0.5
        m &= ~dilate(p, 50)
    return m


def xspec(u, y, fs=FS, nper=2048):
    """Welch cross-spectrum on a list of (u,y) segment pairs; returns f, H=Puy/Puu, coh."""
    nov = nper // 2
    Puu = Pyy = Puy = None
    nseg = 0
    for uu, yy in zip(u, y):
        if len(uu) < nper:
            continue
        f, p_uu = signal.welch(uu, fs, nperseg=nper, noverlap=nov, detrend="linear")
        _, p_yy = signal.welch(yy, fs, nperseg=nper, noverlap=nov, detrend="linear")
        _, p_uy = signal.csd(uu, yy, fs, nperseg=nper, noverlap=nov, detrend="linear")
        w = len(uu)
        Puu = p_uu * w if Puu is None else Puu + p_uu * w
        Pyy = p_yy * w if Pyy is None else Pyy + p_yy * w
        Puy = p_uy * w if Puy is None else Puy + p_uy * w
        nseg += 1
    if Puu is None:
        return None
    H = Puy / Puu
    coh = np.abs(Puy) ** 2 / (Puu * Pyy)
    return f, H, coh, nseg


def report(tag, lab, pairs, fs=FS, nper=2048, flist=(0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0)):
    r = xspec([a for a, _ in pairs], [b for _, b in pairs], fs, nper)
    if r is None:
        pr("      %-22s  no segment long enough (%d samples)" % (lab, nper)); return
    f, H, coh, nseg = r
    pr("      %-22s  (%d segments, %.1f s)" % (lab, nseg, sum(len(a) for a, _ in pairs) / fs))
    hdr = "          f Hz   " + "".join("%8.2f" % x for x in flist)
    pr(hdr)
    for nm, arr, fmt in (("|H|", np.abs(H), "%8.3f"), ("ang deg", np.degrees(np.angle(H)), "%8.1f"),
                         ("coh", coh, "%8.3f")):
        vals = [np.interp(x, f, arr) for x in flist]
        pr("          %-7s" % nm + "".join(fmt % v for v in vals))


def main():
    pr("=" * 126)
    pr("TAU STRUCTURE PROBE -- is cmd -> rate a GAIN or a DIFFERENTIATOR over the outer-loop band?")
    pr("  u = cmd (0xE4 b0-1 raw).  y1 = rate_x (deg/s) = -wire/%.1f.  y2 = ang (deg).  y3 = bar (raw*1.024)." % V.CPD)
    pr("  A pure delay tau shows as phase = -360*tau*f (deg) with FLAT |H|.  A differentiator adds +90 deg,")
    pr("  an integrator -90 deg.  Read the phase SLOPE, not the intercept.")
    pr("=" * 126)

    for tag, build in ROUTES:
        g = C20.load(tag)
        ho = handsoff(g, tag)
        pr("")
        pr("-" * 126)
        pr("ROUTE %-9s %-8s   engaged %.1f%%   engaged+hands-off %.1f%% (%.0f s)"
           % (tag, build, 100 * g["eng"].mean(), 100 * ho.mean(), ho.sum() / FS))
        for lo, hi in BANDS:
            m = ho & (g["vego"] >= lo) & (g["vego"] < hi)
            rr = runs(m, 1024)
            if not rr:
                pr("   v %2.0f-%-2.0f m/s : %6.1f s total, no stretch >= 10.2 s" % (lo, hi, m.sum() / FS))
                continue
            pr("   v %2.0f-%-2.0f m/s : %6.1f s total | %d stretches >=10.2 s, sum %.1f s"
               % (lo, hi, m.sum() / FS, len(rr), sum(b - a for a, b in rr) / FS))
            cm = [g["cmd"][a:b] for a, b in rr]
            report(tag, "cmd -> rate_x", list(zip(cm, [g["rate_x"][a:b] for a, b in rr])))
            report(tag, "cmd -> ang", list(zip(cm, [g["ang"][a:b] for a, b in rr])))
            report(tag, "cmd -> bar", list(zip(cm, [g["bar"][a:b] for a, b in rr])))

    with open(os.path.join(HERE, "_scratch", "tau_struct.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
