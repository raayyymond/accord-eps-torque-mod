# -*- coding: utf-8 -*-
"""studies/grind/grind_loop_shape.py -- the 20 Hz creep grind: de-embed the r24 twist-derivative lane from the
tap-identified plant, then shape the LKAS rate loop to kill the 18-22 Hz peak WITHOUT giving up the 7-9 Hz
margin or the DC authority.

Depends on the settled result in grind_mode_phase.py (same folder): bar/rate is -139 deg at 7 Hz and +114 deg
at 20 Hz in EVERY hands-off stratum, coherence 0.73-0.96, measured on the SAME 0x18F frame (no inter-stream
timing).  The mechanical mode (|bar/rate| peak) is at 7.8-8.6 Hz.  So the r24 lane PUMPS at 7 Hz (-54 deg re
the wheel rate) and is a near-ideal DAMPER at 20 Hz (-171 deg, cos -0.99).

Loop algebra, cut at the 1 kHz aggregator sum u (all lanes enter with unit coefficients -- verified in
FUN_0003aa2c: iVar19 = ... + iVar21 + iVar16, clamp +-0x2800 -> gp-0x6b94):
    rate = G0 * u ;  bar = B * rate ;  r24 = R * bar ;  T = C * rate ;  u = T + r24 + d
    => return ratio  L = (C + R*B) * G0 ,  sensitivity S = 1/(1 - L) ,  critical point L = +1
The tap identifies G_meas = rate/T with r24 ALREADY CLOSED, so the bare plant is
    G0 = G_meas / (1 + R*B*G_meas)
and every prior margin computed against G_meas is the margin of a loop that already contains the r24 pump.

Sections
  D  the firmware controller C(f) from the decompiled arithmetic, validated in phase against the tap
  E  the measured plant G_meas = rate/T per stratum, and the de-embedded bare plant G0
  F  return ratios and margins as-built, per stratum
  G  candidate loop shapes: margins, the 18-22 Hz and 7-9 Hz closed-loop peaks, and the authority cost
Run: python grind_loop_shape.py
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
FS, FST = 100.0, 50.0
OUT = []


def pr(s=""):
    print(s)
    OUT.append(s)


# ---------------------------------------------------------------------------------------------------------
# loading / timing  (identical de-jitter to grind_mode_phase.py; re-stated so this file is standalone)
# ---------------------------------------------------------------------------------------------------------
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
    k1ab, P1ab, tn1ab = dejitter(D["t1ab"], 0.02, 50)
    ke4, Pe4, tne4 = dejitter(D["te4"], 0.01, 100)
    K = int(k18[-1])
    g = dict(tag=tag)
    g["t"] = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18
    g["bar"], have = grid_from(k18, D["tq"].astype(float) * 1.024, K)
    g["rate"], _ = grid_from(k18, D["rate"].astype(float), K)
    g["sca"], _ = grid_from(k18, D["sca"].astype(float), K)
    g["req"] = np.interp(g["t"], tne4, D["req"].astype(float)) > 0.5
    g["cmd"] = np.interp(g["t"], tne4, D["cmd"].astype(float))
    g["ang"] = np.interp(g["t"], D["t14"], D["ang"].astype(float))
    g["vego"] = np.interp(g["t"], D["tcs"], D["vego"].astype(float))
    g["eng"] = (g["sca"] > 0.5) & g["req"] & have
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    g["T_t"] = tn1ab
    g["T"] = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8.0
    # the tap's own instants, and the 0x18F signals resampled onto them (magnitudes are timing-robust;
    # the +-4 ms inter-stream offset is reported and corrected explicitly where a phase is used)
    g["bar_T"] = np.interp(tn1ab, g["t"], g["bar"])
    g["rate_T"] = np.interp(tn1ab, g["t"], g["rate"])
    g["eng_T"] = np.interp(tn1ab, g["t"], g["eng"].astype(float)) > 0.99
    g["v_T"] = np.interp(tn1ab, g["t"], g["vego"])
    g["ang_T"] = np.interp(tn1ab, g["t"], g["ang"])
    g["cmd_T"] = np.interp(tn1ab, g["t"], g["cmd"])
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


# ---------------------------------------------------------------------------------------------------------
# D. the firmware controller, from the decompiled arithmetic (FUN_00028ea6)
# ---------------------------------------------------------------------------------------------------------
TS = 1e-3          # 1 kHz tick (kit BELIEF; every prior mirror that closed on the tap used it)


def z(f, k=1):
    return np.exp(-2j * np.pi * np.asarray(f, dtype=float) * TS * k)


def H_fb(f, a=923.0, b=1560.0):
    """fb = x[n-1] + x[n], x[n] = (a*x[n-1] + b*u)>>10, u = gp-0x6a56 = -rate_wire.  DC = 2b/(1024-a) = 30.89."""
    zz = z(f)
    X = (b / 1024.0) / (1.0 - (a / 1024.0) * zz)
    return X * (1.0 + zz)


def H_lag(f, a=992.0, b=507.0):
    """y[n] = (a*y[n-1] + b*u)>>10 ; out = (y[n-1] + y[n])>>5.  DC = (2b/(1024-a))/32 = 0.990."""
    zz = z(f)
    Y = (b / 1024.0) / (1.0 - (a / 1024.0) * zz)
    return Y * (1.0 + zz) / 32.0


def D4(f, N=4.0):
    return 0.5 * (1.0 - np.exp(-2j * np.pi * np.asarray(f, dtype=float) * N * TS))


def C_lkas(f, kp=295.0, kd=128.0, m=178.0, gain=5346.0, fb=(923.0, 1560.0), lag=(992.0, 507.0)):
    """T (tap counts) per WIRE rate count, small-signal, setpoint held.
       E = 32*sp - fb ; fb = H_fb * (-rate_wire) so dE/d(rate) = +H_fb
       P = E*kp/256 ; D = (E - E[n-1])*kd/8 = E*(1 - z)*kd/8
       sum = m/256 * (P + D) ; T = -(sum) * H_lag * gain/32768   [the final gp-0x6752 = -1 and the
       feedback's own -1 are BOTH in the chain; the net sign is fixed by the validation below]"""
    E_per_rate = H_fb(f, *fb)
    ctrl = kp / 256.0 + (kd / 8.0) * (1.0 - z(f))
    # NO extra -1 here: see C_sign_note().  dE/d(rate) = -H_fb and the final gp-0x6752 = -1 cancel.
    return E_per_rate * ctrl * (m / 256.0) * H_lag(f, *lag) * (gain / 32768.0)


# ---------------------------------------------------------------------------------------------------------
def R_r24(f, gain=5244.0, N=4.0):
    """r24 aggregator counts per bar count, in THIS file's sign convention.

    SIGN, settled on the wire by r24_sign_on_the_wire.py (cave bit 0x14A b4.4 = sign(gp-0x6ada), four
    routes, residual -5..-16 deg over 7-23 Hz):  r24 = gp-0x6752 * k * d/dt(gp-0x4f60), k > 0, and
    `bar` here carries the SAME sign as gp-0x4f60 (the 0x18F builder negates, the cache negates back).
    With gp-0x6752 = -1 -- now CONFIRMED on the wire, not inherited -- the transfer is NEGATIVE:"""
    return -(gain / 1024.0) * D4(f, N)


def C_sign_note():
    """`rate` here = gp-0x6a56 (the cache negates the builder's negation), so the fb filter input IS
    `rate` and dE/d(rate) = -H_fb; the final stage carries gp-0x6752 = -1; the two cancel.  So C_lkas
    must NOT carry an extra -1 in this convention."""


STRATA = [
    ("creep  (engaged, v 1-3, |bar|<400, hands off)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400),
     lambda g: g["eng_T"] & (g["v_T"] >= 1.0) & (g["v_T"] < 3.0) & (np.abs(g["bar_T"]) < 400)),
    ("creep wide (engaged, v 1-6, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400),
     lambda g: g["eng_T"] & (g["v_T"] >= 1.0) & (g["v_T"] < 6.0) & (np.abs(g["bar_T"]) < 400)),
    ("loaded high-angle (engaged, v 2-9, |ang|>30)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30),
     lambda g: g["eng_T"] & (g["v_T"] >= 2.0) & (g["v_T"] < 9.0) & (np.abs(g["ang_T"]) > 30)),
    ("highway (engaged, v > 15)",
     lambda g: g["eng"] & (g["vego"] > 15.0),
     lambda g: g["eng_T"] & (g["v_T"] > 15.0)),
]

FGRID = np.arange(1.0, 24.6, 0.25)
KP = {"creep  (engaged, v 1-3, |bar|<400, hands off)": 295.0,
      "creep wide (engaged, v 1-6, |bar|<400)": 295.0,
      "loaded high-angle (engaged, v 2-9, |ang|>30)": 664.0,
      "highway (engaged, v > 15)": 470.0}


TAU = 3.9e-3   # measured inter-stream offset: the 50 Hz tap reads ~3.9 ms after the 0x18F snapshot it
               # responds to (creep20 sec 1.0: a CONSTANT +23..+33 deg on T_sim vs T_meas at 20 Hz, every
               # window of every route).  Applied to every tap-vs-0x18F PHASE below; magnitudes are unaffected.


def dejit_phase(f):
    return np.exp(2j * np.pi * np.asarray(f, dtype=float) * TAU)


def smooth_c(f, X, coh, w=3, cmin=0.20):
    """coherence-weighted moving average of a complex transfer -- the creep pools are 28-80 s and the
    per-bin scatter is +-40 % off the line.  Bins below cmin get weight 0."""
    wt = np.where(coh >= cmin, coh, 0.0)
    num = np.zeros_like(X)
    den = np.zeros(len(X))
    for d in range(-w, w + 1):
        s = np.roll(X * wt, d)
        t = np.roll(wt, d)
        if d > 0:
            s[:d] = 0
            t[:d] = 0
        elif d < 0:
            s[d:] = 0
            t[d:] = 0
        num += s
        den += t
    return np.where(den > 0, num / np.maximum(den, 1e-12), X)


def band_peak(f, S, lo, hi):
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return float("nan"), float("nan")
    i = int(np.argmax(np.abs(S[m])))
    return float(np.abs(S[m][i])), float(f[m][i])


def margins(f, L):
    """L is the return ratio with critical point +1.  Convert to the textbook convention Lc = -L so the
    critical point is -1, then read gain/phase margin off Lc."""
    Lc = -L
    mag = np.abs(Lc)
    ph = np.unwrap(np.angle(Lc))
    pm = gm = fc = float("nan")
    for i in range(len(f) - 1):
        if (mag[i] - 1.0) * (mag[i + 1] - 1.0) < 0:
            w = (1.0 - mag[i]) / (mag[i + 1] - mag[i])
            fc = f[i] + w * (f[i + 1] - f[i])
            p = np.degrees(ph[i] + w * (ph[i + 1] - ph[i]))
            pm = ((p + 180.0) % 360.0) - 180.0 + 180.0
            pm = ((pm + 180.0) % 360.0) - 180.0
            pm = 180.0 + np.degrees(ph[i] + w * (ph[i + 1] - ph[i]))
            pm = ((pm + 180.0) % 360.0) - 180.0
            break
    S = 1.0 / (1.0 - L)
    ms, fms = band_peak(f, S, 1.0, 24.5)
    return fc, pm, ms, fms


def main():
    gs = {t: load(t) for t in ROUTES}

    pr("=" * 126)
    pr("D. THE FIRMWARE CONTROLLER C(f) = T per WIRE rate count, from the decompiled arithmetic, and the tap check")
    pr("=" * 126)
    pr("   f Hz :" + "".join("%9.1f" % x for x in (3.9, 7.0, 10.0, 13.0, 16.0, 18.0, 20.0, 22.0)))
    for kp, lbl in ((295.0, "Kp 295 (creep p50)"), (664.0, "Kp 664 (high-angle p50)")):
        Cv = C_lkas(np.array([3.9, 7.0, 10.0, 13.0, 16.0, 18.0, 20.0, 22.0]), kp=kp)
        pr("   |C|  :" + "".join("%9.2f" % abs(x) for x in Cv) + "   <- %s" % lbl)
        pr("   ph C :" + "".join("%9.0f" % np.degrees(np.angle(x)) for x in Cv))
    pr("   ANCHOR: the 7 Hz deep analysis measured T re the wire rate at +115.6 deg (median, 18 episodes) and its")
    pr("   independent chain model predicted +114.5 deg.  My C above must land on the same value at 7 Hz.")

    pr()
    pr("=" * 126)
    pr("E. MEASURED PLANT G_meas = rate/T (tap instants, 50 Hz), AND THE DE-EMBEDDED BARE PLANT G0")
    pr("   G0 = G_meas / (1 + R*B*G_meas)   with R = r24 per bar count, B = bar/rate (from the 100 Hz frame)")
    pr("=" * 126)
    SHOW = [3.9, 5.9, 7.8, 9.8, 11.7, 13.7, 15.6, 17.6, 19.5, 21.5, 23.4]
    store = {}
    for name, mfn, mfnT in STRATA:
        # B(f) on the 100 Hz frame
        PB = Pool(FS, 128)
        for t in ROUTES:
            g = gs[t]
            for a, b in runs(mfn(g), 128):
                PB.add({"bar": g["bar"][a:b], "rate": g["rate"][a:b]})
        # G(f) on the tap's own 50 Hz instants
        PG = Pool(FST, 64)
        secs = 0.0
        for t in ROUTES:
            g = gs[t]
            for a, b in runs(mfnT(g), 64):
                if PG.add({"T": g["T"][a:b], "rate": g["rate_T"][a:b], "bar": g["bar_T"][a:b]}):
                    secs += (b - a) / FST
        if PB.n == 0 or PG.n == 0:
            pr("\n  %-46s  NO DATA" % name)
            continue
        fB, B, cB = PB.f, PB.tf("rate", "bar"), PB.coh("rate", "bar")
        fG = PG.f
        cG = PG.coh("T", "rate")
        # G = rate/T and C_meas = T/rate, both on the tap's own instants; the tap-vs-0x18F offset TAU is
        # removed from each (it enters G as a lag and C_meas as a lead).
        G = PG.tf("T", "rate") * np.conj(dejit_phase(fG)) ** 0  # placeholder, corrected below
        G = PG.tf("T", "rate") / dejit_phase(fG)
        Cm = PG.tf("rate", "T") * dejit_phase(fG)
        Bi = smooth_c(fB, B, cB)
        Bi = np.interp(FGRID, fB, Bi.real) + 1j * np.interp(FGRID, fB, Bi.imag)
        Gs = smooth_c(fG, G, cG)
        Gi = np.interp(FGRID, fG, Gs.real) + 1j * np.interp(FGRID, fG, Gs.imag)
        Cms = smooth_c(fG, Cm, cG)
        Cmi = np.interp(FGRID, fG, Cms.real) + 1j * np.interp(FGRID, fG, Cms.imag)
        cGi = np.interp(FGRID, fG, cG)
        cBi = np.interp(FGRID, fB, cB)
        R = R_r24(FGRID)
        G0 = Gi / (1.0 + R * Bi * Gi)
        store[name] = dict(f=FGRID, B=Bi, G=Gi, G0=G0, Cm=Cmi, cG=cGi, cB=cBi, secs=secs)
        idx = [int(np.argmin(np.abs(FGRID - x))) for x in SHOW]
        kp0 = {"creep  (engaged, v 1-3, |bar|<400, hands off)": 295.0,
               "creep wide (engaged, v 1-6, |bar|<400)": 295.0,
               "loaded high-angle (engaged, v 2-9, |ang|>30)": 664.0,
               "highway (engaged, v > 15)": 470.0}[name]
        Cmod = C_lkas(FGRID, kp=kp0)
        pr("\n  %-46s  %5.1f s of tap frames   (Kp %.0f)" % (name, secs, kp0))
        pr("    f Hz       :" + "".join("%8.1f" % FGRID[i] for i in idx))
        pr("    |G| x1e3   :" + "".join("%8.1f" % (abs(Gi[i]) * 1e3) for i in idx))
        pr("    ph G       :" + "".join("%8.0f" % np.degrees(np.angle(Gi[i])) for i in idx))
        pr("    coh T,rate :" + "".join("%8.2f" % cGi[i] for i in idx))
        pr("    |C| meas   :" + "".join("%8.2f" % abs(Cmi[i]) for i in idx) + "   <- T per rate ct, MEASURED")
        pr("    ph C meas  :" + "".join("%8.0f" % np.degrees(np.angle(Cmi[i])) for i in idx))
        pr("    |C| model  :" + "".join("%8.2f" % abs(Cmod[i]) for i in idx) + "   <- from the decompile")
        pr("    ph C model :" + "".join("%8.0f" % np.degrees(np.angle(Cmod[i])) for i in idx))
        pr("    |R*B| r24  :" + "".join("%8.2f" % abs(R[i] * Bi[i]) for i in idx) + "   <- r24 ct per rate ct")
        pr("    ph R*B     :" + "".join("%8.0f" % np.degrees(np.angle(R[i] * Bi[i])) for i in idx))
        pr("    r24 / LKAS :" + "".join("%8.2f" % (abs(R[i] * Bi[i]) / max(abs(Cmi[i]), 1e-9)) for i in idx))
        pr("    |G0|x1e3   :" + "".join("%8.1f" % (abs(G0[i]) * 1e3) for i in idx))
        pr("    ph G0      :" + "".join("%8.0f" % np.degrees(np.angle(G0[i])) for i in idx))

    pr()
    pr("=" * 126)
    pr("F. THE AGGREGATOR'S 20 Hz DAMPING BUDGET -- PLANT-FREE.  Every lane enters the 1 kHz sum with a")
    pr("   unit coefficient (FUN_0003aa2c), so the lanes' phasors add directly and NO plant, sign")
    pr("   convention or unit conversion is needed to compare them.")
    pr("   DAMPING = the component IN PHASE with `rate` (anchored on Honda's own damper gp-0x6bd0,")
    pr("   which is -sign(gp-0x6abe)*M with gp-0x6abe proportional to -gp-0x6a56 = -rate here).")
    pr("=" * 126)
    for name in store:
        st = store[name]
        f, B, Cm = st["f"], st["B"], st["Cm"]
        kp0 = KP[name]
        C = C_lkas(f, kp=kp0)
        for ftest in (7.0, 20.0):
            i = int(np.argmin(np.abs(f - ftest)))
            pr("")
            pr("  %s   at %.1f Hz   (Kp %.0f, coh T-rate %.2f)" % (name, f[i], kp0, st["cG"][i]))
            pr("    %-26s %9s %9s %11s %11s" % ("lane", "|.|/rate", "ph deg", "Re (damp)", "Im"))
            Tp = abs(Cm[i]) * np.exp(1j * np.angle(C[i]))   # magnitude MEASURED, phase MODELLED
            for lbl, gain in (("r24 @ 5244 (as built)", 5244.0), ("r24 @ 512", 512.0),
                              ("r24 @ 2048 (stock arm)", 2048.0), ("r24 @ 3072 (Honda LERP)", 3072.0),
                              ("r24 @ 7866 (x1.5)", 7866.0), ("r24 @ 10488 (x2)", 10488.0)):
                v = R_r24(f[i], gain=gain) * B[i]
                if gain == 5244.0:
                    pr("    %-26s %9.2f %9.0f %11.2f %11.2f" %
                       ("LKAS lane T", abs(Tp), np.degrees(np.angle(Tp)), Tp.real, Tp.imag))
                pr("    %-26s %9.2f %9.0f %11.2f %11.2f" %
                   (lbl, abs(v), np.degrees(np.angle(v)), v.real, v.imag))
            pr("    %-26s %9s %9s %11s %11s" % ("--- SUM T + r24 ---", "", "", "", ""))
            for lbl, gain in (("as built (5244)", 5244.0), ("0xC6446 -> 512", 512.0),
                              ("0xC6446 -> 2048", 2048.0), ("0xC6446 -> 7866", 7866.0),
                              ("0xC6446 -> 10488", 10488.0)):
                v = Tp + R_r24(f[i], gain=gain) * B[i]
                base = Tp + R_r24(f[i], gain=5244.0) * B[i]
                pr("    %-26s %9.2f %9.0f %11.2f %11.2f    damping x%.2f" %
                   (lbl, abs(v), np.degrees(np.angle(v)), v.real, v.imag, v.real / base.real))
    pr()
    pr("=" * 126)
    pr("F2. CANDIDATE SHAPES RANKED BY THE AGGREGATOR DAMPING BUDGET Re(T + r24) -- the plant-free objective.")
    pr("    |T| is MEASURED (the 427 tap) and re-scaled by the modelled |C| ratio of the shape; its phase is")
    pr("    modelled from the decompile.  Re > 0 = net damping.  The 7-9 Hz stutter needs Re > 0 in the loaded")
    pr("    high-angle stratum; the 18-22 Hz grind wants Re as LARGE as possible at 20 Hz.")
    pr("=" * 126)
    SH2 = [
        ("as-built V280 rev 2", dict()),
        ("V281 rev 3: Kp flat 248", dict(kp=248.0)),
        ("0xC6446 5244 -> 2048 (Honda arm)", dict(r24=2048.0)),
        ("0xC6446 5244 -> 512 (7 Hz proposal)", dict(r24=512.0)),
        ("0xC6446 5244 -> 7866 (x1.5)", dict(r24=7866.0)),
        ("out-lag pole 5.0 -> 15 Hz (DC held)", dict(lag=(932.0, 1457.0))),
        ("out-lag pole 5.0 -> 10 Hz (DC held)", dict(lag=(963.0, 986.0))),
        ("out-lag pole 5.0 -> 2.5 Hz (DC held)", dict(lag=(1008.0, 253.0))),
        ("fb pole 16.5 -> 33 Hz (DC held)", dict(fb=(842.0, 2814.0))),
        ("fb pole 16.5 -> 8 Hz (DC held)", dict(fb=(953.0, 1090.0))),
        ("Kd 128 -> 64", dict(kd=64.0)),
        ("Kd 128 -> 192", dict(kd=192.0)),
        ("out-lag 15 Hz + 0xC6446 2048", dict(lag=(932.0, 1457.0), r24=2048.0)),
        ("out-lag 15 Hz + Kp flat 248", dict(lag=(932.0, 1457.0), kp=248.0)),
    ]
    for name in store:
        st = store[name]
        f, B, Cm = st["f"], st["B"], st["Cm"]
        kp0 = KP[name]
        i7 = int(np.argmin(np.abs(f - 7.0)))
        i20 = int(np.argmin(np.abs(f - 20.0)))
        C0 = C_lkas(f, kp=kp0)
        pr("")
        pr("  %s   (Kp %.0f)" % (name, kp0))
        pr("    %-38s %9s %9s %9s %9s %9s" %
           ("shape", "Re@7Hz", "x base", "Re@20Hz", "x base", "|C| 20Hz"))
        base7 = base20 = None
        for lbl, kw in SH2:
            kp = kw.get("kp", kp0)
            kd = kw.get("kd", 128.0)
            fb = kw.get("fb", (923.0, 1560.0))
            lag = kw.get("lag", (992.0, 507.0))
            rg = kw.get("r24", 5244.0)
            C = C_lkas(f, kp=kp, kd=kd, fb=fb, lag=lag)
            out = []
            for i in (i7, i20):
                # |T| measured, re-scaled by the model's own |C| change; phase from the model
                Tp = abs(Cm[i]) * (abs(C[i]) / abs(C0[i])) * np.exp(1j * np.angle(C[i]))
                out.append((Tp + R_r24(f[i], gain=rg) * B[i]).real)
            if base7 is None:
                base7, base20 = out
            Cn = abs(C_lkas(f[i20], kp=kp, kd=kd, fb=fb, lag=lag))
            pr("    %-38s %9.2f %9.2f %9.2f %9.2f %9.2f"
               % (lbl, out[0], out[0] / base7, out[1], out[1] / base20, Cn))

    pr()
    pr("=" * 126)
    pr("G. LOOP SHAPES.  L = (C + R*B) * G0, critical point +1.  Ms = max|1/(1-L)| over 1-24.5 Hz.")
    pr("     'peak 18-22' and 'peak 7-9' are |S| = |1/(1-L)| maxima in those bands: the closed-loop")
    pr("     amplification of broadband disturbance, i.e. what rings.")
    pr("=" * 126)

    SHAPES = [
        ("as-built V280 rev 2", dict()),
        ("V281 rev 3: Kp flat 248", dict(kp=248.0)),
        ("Kd 128 -> 64", dict(kd=64.0)),
        ("Kd 128 -> 0", dict(kd=0.0)),
        ("fb pole 16.5 -> 8.0 Hz (DC held)", dict(fb=(953.0, 1090.0))),
        ("fb pole 16.5 -> 5.0 Hz (DC held)", dict(fb=(994.0, 690.0))),
        ("out-lag 5.0 -> 2.5 Hz (DC held)", dict(lag=(1008.0, 253.0))),
        ("out-lag 5.0 -> 3.3 Hz (DC held)", dict(lag=(1003.0, 332.0))),
        ("r24 gain 5244 -> 512", dict(r24=512.0)),
        ("r24 gain 5244 -> 7866 (x1.5)", dict(r24=7866.0)),
        ("out-lag 3.3 Hz + Kd 96", dict(lag=(1003.0, 332.0), kd=96.0)),
        ("fb pole 8 Hz + Kd 96", dict(fb=(953.0, 1090.0), kd=96.0)),
    ]
    for name in store:
        st = store[name]
        f, B, G0 = st["f"], st["B"], st["G0"]
        kp0 = KP[name]
        C0 = C_lkas(f, kp=kp0)
        R0 = R_r24(f)
        L0 = (C0 + R0 * B) * G0
        pr("\n  %s   (Kp %.0f)" % (name, kp0))
        ii = [int(np.argmin(np.abs(f - x))) for x in
              (2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 19.0, 20.0, 21.0, 22.0, 24.0)]
        pr("    L(f) as-built   f :" + "".join("%7.1f" % f[i] for i in ii))
        pr("                  |L| :" + "".join("%7.2f" % abs(L0[i]) for i in ii))
        pr("                  ph  :" + "".join("%7.0f" % np.degrees(np.angle(L0[i])) for i in ii))
        pr("             |S|=|1/(1-L)| :" + "".join("%7.2f" % abs(1.0 / (1.0 - L0[i])) for i in ii))
        pr("    %-36s %8s %8s %7s %7s %10s %10s %8s" %
           ("shape", "f_c Hz", "PM deg", "Ms", "@f Hz", "peak 18-22", "peak 7-9", "|L|@20"))
        base = None
        for lbl, kw in SHAPES:
            kp = kw.get("kp", kp0)
            kd = kw.get("kd", 128.0)
            fb = kw.get("fb", (923.0, 1560.0))
            lag = kw.get("lag", (992.0, 507.0))
            rg = kw.get("r24", 5244.0)
            C = C_lkas(f, kp=kp, kd=kd, fb=fb, lag=lag)
            R = R_r24(f, gain=rg)
            L = (C + R * B) * G0
            fc, pm, ms, fms = margins(f, L)
            S = 1.0 / (1.0 - L)
            p1822, _ = band_peak(f, S, 18.0, 22.0)
            p79, _ = band_peak(f, S, 7.0, 9.0)
            i20 = int(np.argmin(np.abs(f - 20.0)))
            row = (fc, pm, ms, fms, p1822, p79, abs(L[i20]))
            if base is None:
                base = row
            pr("    %-36s %8.1f %8.0f %7.2f %7.1f %10.2f %10.2f %8.2f"
               % ((lbl,) + row))
        pr("    (ratios vs as-built: peak 18-22 and peak 7-9)")
        for lbl, kw in SHAPES:
            kp = kw.get("kp", kp0)
            kd = kw.get("kd", 128.0)
            fb = kw.get("fb", (923.0, 1560.0))
            lag = kw.get("lag", (992.0, 507.0))
            rg = kw.get("r24", 5244.0)
            C = C_lkas(f, kp=kp, kd=kd, fb=fb, lag=lag)
            R = R_r24(f, gain=rg)
            S = 1.0 / (1.0 - (C + R * B) * G0)
            p1822, _ = band_peak(f, S, 18.0, 22.0)
            p79, _ = band_peak(f, S, 7.0, 9.0)
            pr("      %-36s  18-22 x%.2f    7-9 x%.2f" % (lbl, p1822 / base[4], p79 / base[5]))

    with open(os.path.join(HERE, "_scratch", "grind_loop_shape.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


main()
