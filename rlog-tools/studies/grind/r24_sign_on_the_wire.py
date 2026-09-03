# -*- coding: utf-8 -*-
"""studies/grind/r24_sign_on_the_wire.py -- MEASURE the r24 twist-derivative lane's phase against the wheel
rate, from drives ALREADY TAKEN.  No build, no drive.

The V280 rev 2 code cave (0xC4B34, hash d3bb75d8, unchanged since V105) publishes
    0x14A byte 4 bit 4 = (gp-0x6ada < 0)      = the SIGN of the r24 lane output
    0x14A byte 4 bit 7 = (gp-0x6b4c < 0)      = the SIGN of the 11-slot assist sum (carries the LKAS lane)
at 100 Hz.  For a sinusoid, sign(x) is a square wave with the SAME phase as x and a fundamental of 4/pi
times its amplitude, so a cross-spectrum of the mapped bit against the wheel rate returns the lane's PHASE
directly.  Amplitude is not recoverable from a sign bit -- phase is, and phase is the load-bearing quantity.

THE CONTROL (the probe-design law: never a bare threshold, always a deliberately-designed control).
bit 7 rides the same frame, the same 100 Hz cadence and the same sign-of-a-signal transform as bit 4, and
its subject -- the assist sum that carries the LKAS lane -- is ALREADY on the wire independently, as the
CAN-427 delivered-torque tap T.  So bit 7 measures a quantity whose phase is separately known.  Any
constant 0x14A-vs-0x18F stream offset, and any bias the sign transform introduces, shows up as the
disagreement between bit 7 and T, and is then removed from bit 4 by the same amount.  If bit 7 does NOT
reproduce T's phase, the method has failed and bit 4's answer is worth nothing.

What is being adjudicated (both 2026-09-03 deep analyses routed it here):
    closed form, from the decompile + the measured bar/rate:  ph(r24) re rate = ang(bar/rate) + ang(D4)
      -> 7 Hz  in the loaded high-angle stratum: -96 + 85 = -11 deg  => PUMPING
      -> 20 Hz in the creep stratum:            +114 + 75 = -171 deg => DAMPING (in the naive convention)
    This script tests those two numbers against the wire.
Run: python r24_sign_on_the_wire.py
"""
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
V280 = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
ROUTES = ("r34", "r33", "r32", "r31")
FS = 100.0
OUT = []


def pr(s=""):
    print(s)
    OUT.append(s)


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
    f = os.path.join(SCR, "r24sign_" + tag + ".npz")
    if not os.path.exists(f):
        return None
    D = dict(np.load(f))
    k18, P18, tn18 = dejitter(D["t18"], 0.01, 100)
    k14, P14, tn14 = dejitter(D["t14"], 0.01, 100)
    ke4, Pe4, tne4 = dejitter(D["te4"], 0.01, 100)
    K = int(k18[-1])
    g = dict(tag=tag)
    g["t"] = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18
    g["bar"], have = grid_from(k18, D["tq"] * 1.024, K)
    g["rate"], _ = grid_from(k18, D["rate"], K)
    g["sca"], _ = grid_from(k18, D["sca"], K)
    b4 = D["b4"].astype(int)
    # sign convention: the bit is 1 when the cell is NEGATIVE, so s = +1 when the cell is >= 0.
    for bit, nm in ((4, "s_r24"), (7, "s_b4c"), (3, "s_3680"), (5, "s_cmp5")):
        v = 1.0 - 2.0 * ((b4 >> bit) & 1).astype(float)
        g[nm] = np.interp(g["t"], tn14, v)
    g["req"] = np.interp(g["t"], tne4, D["req"]) > 0.5
    g["cmd"] = np.interp(g["t"], tne4, D["cmd"])
    g["vego"] = np.interp(g["t"], D["tcs"], D["vego"])
    g["ang"] = np.interp(g["t"], D["tcs"], D["angcs"])
    g["eng"] = (g["sca"] > 0.5) & g["req"] & have
    # the 427 tap, for the CONTROL, from the existing v280 cache (same route, same drive)
    C = dict(np.load(os.path.join(V280, tag + ".npz")))
    k1ab, P1ab, tn1ab = dejitter(C["t1ab"], 0.02, 50)
    fld = ((C["b0"].astype(int) & 3) << 8) | C["b1"].astype(int)
    Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8.0
    g["T"] = np.interp(g["t"], tn1ab, Tm)
    g["s_T"] = np.sign(np.interp(g["t"], tn1ab, Tm))
    return g


def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


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


def D4(f, N=4.0):
    return 0.5 * (1.0 - np.exp(-2j * np.pi * np.asarray(f, dtype=float) * N * 1e-3))


STRATA = [
    ("creep engaged hands-off (v 1-3, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
    ("creep engaged hands-off (v 1-6, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
    ("loaded high-angle engaged (v 2-9, |ang|>30)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30)),
    ("highway engaged (v > 15)",
     lambda g: g["eng"] & (g["vego"] > 15.0)),
]
SHOW = [3.9, 5.5, 7.0, 8.6, 10.9, 13.3, 15.6, 18.0, 19.5, 21.1, 22.7, 25.0]


def main():
    gs = {}
    for t in ROUTES:
        g = load(t)
        if g is not None:
            gs[t] = g
    pr("routes loaded: " + ", ".join(gs))
    NPS = 128
    for name, fn in STRATA:
        P = Pool(FS, NPS)
        secs = 0.0
        for t in gs:
            g = gs[t]
            for a, b in runs(fn(g), NPS):
                if P.add({"rate": g["rate"][a:b], "bar": g["bar"][a:b], "T": g["T"][a:b],
                          "sT": g["s_T"][a:b], "sR": g["s_r24"][a:b], "sB": g["s_b4c"][a:b],
                          "sbar": np.sign(g["bar"][a:b] - g["bar"][a:b].mean())}):
                    secs += (b - a) / FS
        if P.n == 0:
            pr("\n  %-44s NO DATA" % name)
            continue
        f = P.f
        idx = [int(np.argmin(np.abs(f - x))) for x in SHOW]
        B = P.tf("rate", "bar")
        HT = P.tf("rate", "T")
        HsT = P.tf("rate", "sT")
        HsB = P.tf("rate", "sB")
        HsR = P.tf("rate", "sR")
        pr("\n" + "=" * 122)
        pr("  %s      %.1f s, %d Welch windows" % (name, secs, P.n))
        pr("=" * 122)
        pr("    f Hz              :" + "".join("%8.1f" % f[i] for i in idx))
        pr("    ph(bar/rate)      :" + "".join("%8.0f" % np.degrees(np.angle(B[i])) for i in idx)
           + "   coh " + " ".join("%.2f" % P.coh("rate", "bar")[i] for i in idx[:1]))
        pr("    ph(T/rate)  427   :" + "".join("%8.0f" % np.degrees(np.angle(HT[i])) for i in idx))
        pr("      coh rate,T      :" + "".join("%8.2f" % P.coh("rate", "T")[i] for i in idx))
        pr("    ph(sign T /rate)  :" + "".join("%8.0f" % np.degrees(np.angle(HsT[i])) for i in idx)
           + "   <- sign() transform, applied to a signal we HAVE: bias check")
        pr("    ph(bit7 = sign gp-0x6b4c) :" + "".join("%8.0f" % np.degrees(np.angle(HsB[i])) for i in idx))
        pr("      coh rate,bit7   :" + "".join("%8.2f" % P.coh("rate", "sB")[i] for i in idx))
        pr("    *** ph(bit4 = sign gp-0x6ada = r24) ***")
        pr("      measured        :" + "".join("%8.0f" % np.degrees(np.angle(HsR[i])) for i in idx))
        pr("      coh rate,bit4   :" + "".join("%8.2f" % P.coh("rate", "sR")[i] for i in idx))
        # CLOSED FORM, corrected: the 0x18F frame builder NEGATES both bar and rate
        # (FUN_00055c42: wire = -(gp-0x4f60*125>>7) and -gp-0x6a56) and the kit caches negate them BACK,
        # so `bar` and `rate` here carry the SAME sign as gp-0x4f60 and gp-0x6a56 respectively.  Hence
        #     r24 = gp-0x6752 * k * d/dt(gp-0x4f60) = gp-0x6752 * k * d/dt(bar),  k > 0
        # and with gp-0x6752 = -1 the phase is ang(bar/rate) + ang(D4) + 180 deg.
        # (twistloop's "gp-0x4f60 = -(cache torque)" is wrong: the cache already negates.)
        pred = np.angle(-B * D4(f))
        pr("      CLOSED FORM     :" + "".join("%8.0f" % np.degrees(pred[i]) for i in idx)
           + "   <- ang(bar/rate) + ang(D4), the number under dispute")
        resid = np.degrees(np.angle(HsR * np.exp(-1j * pred)))
        pr("      measured - pred :" + "".join("%8.0f" % resid[i] for i in idx))
        # the CONTROL: does bit7 reproduce the 427 tap's phase?
        ctrl = np.degrees(np.angle(HsB * np.conj(HT) / np.abs(HT)))
        pr("    CONTROL bit7 - T  :" + "".join("%8.0f" % ctrl[i] for i in idx)
           + "   <- must be ~0 for the method to be trusted")
        # DAMPING CONVENTION, anchored on Honda's own damper.  gp-0x6bd0 = -sign(gp-0x6abe)*M with
        # gp-0x6abe proportional to -gp-0x6a56 = -rate(here), so Honda's damper is IN PHASE with `rate`
        # as defined here.  Therefore, in THIS script's variables, a lane DAMPS when cos(phase re rate) > 0
        # and PUMPS when it is < 0 -- the opposite of the wire-sign convention twistloop used.
        cosr = np.cos(np.angle(HsR))
        pr("    cos(ph r24 re rate) measured :" + "".join("%8.2f" % cosr[i] for i in idx))
        pr("      verdict         :" + "".join("%8s" % ("DAMP" if cosr[i] > 0.2 else
                                                        ("PUMP" if cosr[i] < -0.2 else "~neut"))
                                               for i in idx))
        # CONTROL 1 -- the sign() transform preserves phase.  Apply it to `bar`, a signal we HAVE, in the
        # SAME frame as `rate`, so there is no timing term at all: ang(sign(bar)/rate) must equal
        # ang(bar/rate).
        sb = np.degrees(np.angle(P.tf("rate", "sbar") * np.conj(B) / np.abs(B)))
        pr("    CONTROL 1  ang(sign bar) - ang(bar) :" + "".join("%8.0f" % sb[i] for i in idx)
           + "   must be ~0")
        # CONTROL 2 -- no 0x14A-vs-0x18F timing offset.  A constant inter-frame offset tau would make the
        # residual (measured - closed form) RAMP with frequency at 360*tau deg/Hz; one whole 100 Hz frame
        # is 3.6 deg/Hz, i.e. 58 deg across 7->23 Hz.  Regress the residual on f over 13-23 Hz.
        sel = (f >= 13.0) & (f <= 23.5)
        rr = np.degrees(np.unwrap(np.angle(HsR[sel] * np.exp(-1j * pred[sel]))))
        A = np.polyfit(f[sel], rr, 1)
        pr("    CONTROL 2  residual vs f, 13-23 Hz : slope %+.2f deg/Hz  (one 100 Hz frame = 3.60)"
           % A[0] + "   intercept %+.0f deg" % A[1])
        pr("               implied 0x14A-vs-0x18F offset %+.2f ms" % (A[0] / 0.36))
    with open(os.path.join(SCR, "r24_sign_on_the_wire.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


main()
