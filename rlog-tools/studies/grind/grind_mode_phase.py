# -*- coding: utf-8 -*-
"""studies/grind/grind_mode_phase.py -- SETTLE the bar-vs-rate phase dispute at 20 Hz, and with it the SIGN of
the engaged-only r24 twist-derivative lane in the CREEP grind stratum.

The dispute (routed to me by both 2026-09-03 deep analyses):
  creep20   (creep stratum, v 1-3 m/s, hands off): bar/rate at 20 Hz = -70 deg, coh 0.88-0.94  -> r24 PUMPS at 20 Hz
  7Hz agent (loaded high-angle, v 2-9 m/s, |ang|>30): bar/rate at 20 Hz = +114 deg, coh 0.94   -> r24 DAMPS at 20 Hz
184 deg apart.  Both cannot describe the same mechanical configuration.

HYPOTHESIS UNDER TEST: the torsion-bar / hand-wheel mode frequency depends on HANDS.  Hands off = free wheel
inertia only -> fn high; a hand on the rim adds inertia -> fn low.  bar/rate is a 2nd-order transfer that
ROTATES -180 deg through fn and PEAKS at fn.  So the same lane pumps below fn and damps above it, and each
symptom sits just BELOW its own stratum's fn.  Falsifiable: |bar/rate| must PEAK at different frequencies in
the two strata, and the peak must move DOWN as |bar| (the hands proxy) rises.

Everything is re-derived here from the caches; no constant is inherited from creep20_loop_id.py,
twist_taper_loop.py or r24_deembed.py.  bar and rate come from the SAME 0x18F frame, so sections A-C carry
NO inter-stream timing risk at all.

Sections
  A  |bar/rate| and its phase, 4-40 Hz, per stratum, on the 100 Hz 0x18F stream; the mode frequency per stratum.
  B  the hands test: mode frequency vs |bar| level (hands proxy) inside one speed stratum.
  C  r24's closed-form phase re the wheel rate and its damping fraction, per stratum, at 7 and 20 Hz.
Run: python grind_mode_phase.py
"""
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
ROUTES = ("r31", "r32", "r33", "r34")
FS = 100.0
OUT = []


def pr(s=""):
    print(s)
    OUT.append(s)


# ----------------------------------------------------------------------------------------------------------------
# timing (only to put the 0x18F stream back on its own frame counter; bar and rate ride the SAME frame)
# ----------------------------------------------------------------------------------------------------------------
def rolling_low(x, half, q=2.0):
    n = len(x)
    cen = np.arange(0, n, max(1, half // 2))
    v = np.array([np.percentile(x[max(0, c - half):min(n, c + half + 1)], q) for c in cen])
    return np.interp(np.arange(n), cen, v)


def dejitter(t, P0, half):
    n = len(t)
    i = np.arange(n)
    r = t - i * P0
    env = rolling_low(r, half)
    step = np.r_[0.0, np.diff(env)]
    drops = np.round(np.cumsum(np.where(np.abs(step) > 0.6 * P0, step, 0.0)) / P0).astype(int)
    k = i + drops
    r2 = t - k * P0
    env2 = rolling_low(r2, half)
    P = P0 + (env2[-1] - env2[0]) / max(1, (k[-1] - k[0]))
    r3 = t - k * P
    env3 = rolling_low(r3, half)
    return k, P, k * P + env3


def grid_from(k, x, kmax):
    g = np.full(kmax + 1, np.nan)
    g[k] = x
    have = ~np.isnan(g)
    g[~have] = np.interp(np.flatnonzero(~have), np.flatnonzero(have), g[have])
    return g, have


def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    k18, P18, tn18 = dejitter(D["t18"], 0.01, 100)
    K = int(k18[-1])
    g = dict(tag=tag, P18=P18)
    g["t"] = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18
    # SIGN CONVENTION, stated once and used everywhere below:
    #   bar  = the 0x18F driver torque as logged, x1.024 -> raw counts.  gp-0x4f60 = -bar  (FUN_00055c42 negates)
    #   rate = the 0x18F wheel rate as logged, raw counts (8 per deg/s). gp-0x6a56 = -rate (same builder)
    #   Both internal cells are negated by the SAME builder, so bar/rate is identical in wire and internal sign.
    g["bar"], have = grid_from(k18, D["tq"].astype(float) * 1.024, K)
    g["rate"], _ = grid_from(k18, D["rate"].astype(float), K)
    g["sca"], _ = grid_from(k18, D["sca"].astype(float), K)
    g["have"] = have
    ke4, Pe4, tne4 = dejitter(D["te4"], 0.01, 100)
    g["req"] = np.interp(g["t"], tne4, D["req"].astype(float)) > 0.5
    g["cmd"] = np.interp(g["t"], tne4, D["cmd"].astype(float))
    g["ang"] = np.interp(g["t"], D["t14"], D["ang"].astype(float))
    g["vego"] = np.interp(g["t"], D["tcs"], D["vego"].astype(float))
    g["eng"] = (g["sca"] > 0.5) & g["req"] & have
    return g


def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


# ----------------------------------------------------------------------------------------------------------------
# pooled cross-spectrum
# ----------------------------------------------------------------------------------------------------------------
class Pool:
    def __init__(self, fs, nps):
        self.fs, self.nps, self.f, self.S, self.n = fs, nps, None, {}, 0

    def add(self, sigs):
        n = len(next(iter(sigs.values())))
        if n < self.nps:
            return 0
        nw = max(1, (n - self.nps // 2) // (self.nps // 2))
        keys = list(sigs)
        for i, a in enumerate(keys):
            for b in keys[i:]:
                f, P = signal.csd(sigs[a], sigs[b], fs=self.fs, nperseg=self.nps, detrend="constant")
                self.f = f
                self.S[(a, b)] = self.S.get((a, b), 0) + nw * P
        self.n += nw
        return nw

    def s(self, a, b):
        return self.S[(a, b)] / self.n if (a, b) in self.S else np.conj(self.S[(b, a)]) / self.n

    def coh(self, a, b):
        return np.abs(self.s(a, b)) ** 2 / (np.real(self.s(a, a)) * np.real(self.s(b, b)))

    def tf(self, u, y):
        return self.s(u, y) / np.real(self.s(u, u))


# ----------------------------------------------------------------------------------------------------------------
# the r24 lane, in closed form from the decompiled arithmetic
# ----------------------------------------------------------------------------------------------------------------
def D4(f, N=4, fs1k=1000.0):
    """gp-0x4f62 = 0.5*(gp4f60[n] - gp4f60[n-N]) at 1 kHz -> 0.5*(1 - exp(-j w N/fs))."""
    return 0.5 * (1.0 - np.exp(-2j * np.pi * np.asarray(f, dtype=float) * N / fs1k))


STRATA = [
    ("creep engaged, hands off (v 1-3, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
    ("creep engaged, hands off (v 1-6, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
    ("creep engaged, HAND ON (v 1-6, |bar|>800)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) > 800)),
    ("creep MANUAL / disengaged (v 1-6)",
     lambda g: (~g["eng"]) & (g["vego"] >= 1.0) & (g["vego"] < 6.0)),
    ("loaded high-angle engaged (v 2-9, |ang|>30)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30)),
    ("loaded high-angle, hands off (|bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (np.abs(g["bar"]) < 400)),
    ("loaded high-angle, HAND ON (|bar|>800)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (np.abs(g["bar"]) > 800)),
    ("highway engaged (v > 15)",
     lambda g: g["eng"] & (g["vego"] > 15.0)),
]


def main():
    gs = {t: load(t) for t in ROUTES}
    pr("=" * 124)
    pr("A. |bar/rate| AND ITS PHASE, 100 Hz 0x18F stream (bar and rate ride the SAME frame -> no inter-stream timing)")
    pr("   convention: bar = logged 0x18F torque x1.024; rate = logged 0x18F rate (8 ct per deg/s).  Both internal")
    pr("   cells are negated by the SAME frame builder, so the RATIO is convention-free.")
    pr("=" * 124)
    NPS = 128
    SHOW = [3.9, 5.5, 7.0, 8.6, 10.2, 11.7, 13.3, 14.8, 16.4, 18.0, 19.5, 21.1, 22.7, 25.0, 28.1, 31.3, 35.2, 39.1]
    results = []
    for name, fn in STRATA:
        P = Pool(FS, NPS)
        secs = 0.0
        for t in ROUTES:
            g = gs[t]
            m = fn(g)
            for a, b in runs(m, NPS):
                if P.add({"bar": g["bar"][a:b], "rate": g["rate"][a:b]}):
                    secs += (b - a) / FS
        if P.n == 0:
            pr("\n  %-46s  NO DATA" % name)
            continue
        f = P.f
        B = P.tf("rate", "bar")
        C = P.coh("rate", "bar")
        results.append((name, f, B, C, secs, P.n))
        pr("\n  %-46s  %5.1f s, %d Welch windows" % (name, secs, P.n))
        idx = [int(np.argmin(np.abs(f - x))) for x in SHOW]
        pr("    f Hz   :" + "".join("%7.1f" % f[i] for i in idx))
        pr("    |B|    :" + "".join("%7.2f" % abs(B[i]) for i in idx))
        pr("    ph B   :" + "".join("%7.0f" % np.degrees(np.angle(B[i])) for i in idx))
        pr("    coh    :" + "".join("%7.2f" % C[i] for i in idx))
        sel = (f >= 4) & (f <= 40) & (C > 0.30)
        if sel.sum():
            fm = f[sel][int(np.argmax(np.abs(B[sel])))]
            pr("    -> |B| PEAK (the hand-wheel / torsion-bar mode) at %.1f Hz  (coherence-gated > 0.30)" % fm)

    pr()
    pr("=" * 124)
    pr("B. THE HANDS TEST -- mode frequency vs |bar| level (hands proxy), one speed stratum (v 1-9, engaged)")
    pr("=" * 124)
    pr("  |bar| raw        s     nW   |B| peak Hz   ph(B)@20Hz  coh@20    ph(B)@7Hz  coh@7")
    for lo, hi in [(0, 200), (200, 400), (400, 800), (800, 1600), (1600, 4000)]:
        P = Pool(FS, NPS)
        secs = 0.0
        for t in ROUTES:
            g = gs[t]
            m = (g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 9.0)
                 & (np.abs(g["bar"]) >= lo) & (np.abs(g["bar"]) < hi))
            for a, b in runs(m, NPS):
                if P.add({"bar": g["bar"][a:b], "rate": g["rate"][a:b]}):
                    secs += (b - a) / FS
        if P.n == 0:
            pr("  %5d-%-5d     NO DATA" % (lo, hi))
            continue
        f, B, C = P.f, P.tf("rate", "bar"), P.coh("rate", "bar")
        sel = (f >= 4) & (f <= 40) & (C > 0.30)
        fm = f[sel][int(np.argmax(np.abs(B[sel])))] if sel.sum() else float("nan")
        i20 = int(np.argmin(np.abs(f - 20.0)))
        i7 = int(np.argmin(np.abs(f - 7.0)))
        pr("  %5d-%-5d %7.1f %6d   %9.1f   %10.0f %7.2f %12.0f %6.2f"
           % (lo, hi, secs, P.n, fm, np.degrees(np.angle(B[i20])), C[i20],
              np.degrees(np.angle(B[i7])), C[i7]))

    pr()
    pr("=" * 124)
    pr("C. r24 PHASE RE THE WHEEL RATE AND ITS DAMPING FRACTION, per stratum")
    pr("   r24 = (0xC6446/1024) * D4(f) * bar_wire ;  phase re rate = ang(B) + ang(D4)")
    pr("   DAMPING convention: a lane DAMPS if its phasor opposes the rate, cos(phase re rate) < 0.")
    pr("   Anchor: the LKAS lane T measures +115 deg re rate = cos -0.42 = damping (twistloop, 18 episodes).")
    pr("=" * 124)
    pr("  %-46s %6s %8s %8s %8s %7s %9s %6s" %
       ("stratum", "f Hz", "ph(B)", "ph(D4)", "ph(r24)", "cos", "verdict", "coh"))
    for name, f, B, C, secs, nw in results:
        for k, ftest in enumerate((7.0, 20.0)):
            i = int(np.argmin(np.abs(f - ftest)))
            pd4 = np.degrees(np.angle(D4(f[i])))
            ph = (np.degrees(np.angle(B[i])) + pd4 + 180) % 360 - 180
            c = np.cos(np.radians(ph))
            pr("  %-46s %6.1f %8.0f %8.1f %8.0f %7.2f %9s %6.2f"
               % (name if k == 0 else "", f[i], np.degrees(np.angle(B[i])), pd4, ph, c,
                  "PUMP" if c > 0.20 else ("DAMP" if c < -0.20 else "~neutral"), C[i]))

    with open(os.path.join(HERE, "_scratch", "grind_mode_phase.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


main()
