# -*- coding: utf-8 -*-
"""studies/grind/adv_v289_b_loop.py -- ADVERSARY B, GATE 2 for V289 rev 1, rebuilt from the IMAGE (not from the design):
the LKAS rate loop L(z) element by element with every constant byte-read from the V282 and V289 images, the notch as the
integer coefficients recovered by adv_v289_b_cave.decode, scored on the design's four plant fits (loopshape20_plants.json,
INCLUDING the smooth fit the census rejected), plus a byte-exact 1 kHz CLOSED-LOOP time-domain mirror (integer controller,
the cave executed by the interpreter, plant ZOH-discretised) for the authority steps (B3).   Subagent advB, 2026-09-08.
Analysis only.  Writes _scratch/adv_v289_b_loop.txt beside it.

Pre-registered FAIL criteria (docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md sec B):
  B1 fb DC 2b/(1024-a) departs from 30.89 by > 0.5 %, or the cell widths wrong
  B2 |L| below 5 Hz changed > 5 %; 7 Hz gate |Ls R + Lr| > 1.02; phase at 3.9 Hz worse than -5 deg
  B3 capped-frame step peak rate or peak accel < 0.95x V282
"""
import json
import os
import struct
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v289_b_cave as CV   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = 1e-3, 1000.0, 8.0
OUT = []
LS73, LR73 = 0.55 * np.exp(1j * np.radians(96.0)), 1.19 * np.exp(1j * np.radians(-27.0))   # the record's 7 Hz split (LOOPSHAPE-LAGPOLE-KD sec 4)
LTOT73 = (0.944, 0.976, 0.990)


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def zf(f):
    return np.exp(2j * np.pi * np.asarray(f, float) * TS)


# ---------------------------------------------------------------------------------------------------------------------
# cells, from the images, with the widths the LOADS use (decoded by adv_v289_b_cave.decode at the load sites)
# ---------------------------------------------------------------------------------------------------------------------
def cells(img):
    c = {}
    # widths: decode the actual loads
    ld = {ad: txt for ad, n, txt, op in CV.decode(img, 0x28F86, 0x28F8E)}
    assert ld[0x28F86].startswith("ld.hu 29674[tp]") and ld[0x28F8A].startswith("ld.h 29672[tp]"), ld
    c["fb_b"] = u16(img, CV.TP + 29674)          # 0xC63EA unsigned
    c["fb_a"] = s16(img, CV.TP + 29672)          # 0xC63E8 signed
    ld2 = {ad: txt for ad, n, txt, op in CV.decode(img, 0x2A174, 0x2A1B4) if txt.startswith("ld.h")}
    # 0x2A174 is the hook in V289 (jr); the displaced load is replicated in the cave as ld.hu 29678[tp]
    c["lag_b"] = u16(img, CV.TP + 29678)         # 0xC63EE unsigned
    c["lag_a"] = s16(img, CV.TP + 29676)         # 0xC63EC signed (ld.h @0x2A184)
    assert any(t.startswith("ld.h 29676[tp]") for t in ld2.values())
    c["fb_clamp"] = u16(img, 0xC62E6); c["p_clamp"] = u16(img, 0xC61BC); c["d_clamp"] = u16(img, 0xC61B6)
    c["sum_clamp"] = u16(img, 0xC61BE); c["t_clamp"] = u16(img, 0xC61B4)
    disp = u16(img, 0x2A1F0); c["gain"] = s16(img, CV.TP + disp); c["gain_addr"] = CV.TP + disp
    # Kp / Kd slot 7 LERP Y knots
    def lerp_rec(base, n):
        X = [u16(img, base + 2 + 2 * i) for i in range(n)]; Y = [u16(img, base + 2 + 2 * n + 2 * i) for i in range(n)]
        return np.array(X, float), np.array(Y, float)
    c["kp_X"], c["kp_Y"] = lerp_rec(struct.unpack_from("<I", img, 0xCB994 + 4 * 7)[0], 5)
    c["kd_X"], c["kd_Y"] = lerp_rec(struct.unpack_from("<I", img, 0xCB7D4 + 4 * 7)[0], 4)
    c["map_X"], c["map_Y"] = lerp_rec(struct.unpack_from("<I", img, 0xC9A88 + 4 * 7)[0], 10)
    c["ki"] = u16(img, 0xC63E6)
    return c


def notch_ints(img):
    """The three distinct coefficients, recovered from the movea immediates in the cave, in the order the code uses them."""
    ops = CV.decode(img, CV.CAVE, CV.CAVE_END)
    imm = [op["imm"] for ad, n, txt, op in ops if op["k"] == "movea"]
    b0, a2, b1 = imm            # 0xC4C0E (b0*x), 0xC4C26 (a2*y), 0xC4C3C (b1*(x-y))
    shifts = [op["imm"] for ad, n, txt, op in ops if op["k"] == "sar_i"]
    assert shifts == [14], shifts
    return dict(b0=b0, b1=b1, a1=b1, a2=a2, a0=1 << 14)


def notch_H(nc, f):
    z = zf(f)
    return (nc["b0"] + nc["b1"] / z + nc["b0"] / z ** 2) / (nc["a0"] + nc["a1"] / z + nc["a2"] / z ** 2)


# ---------------------------------------------------------------------------------------------------------------------
# the loop elements (z-domain) -- every constant from cells(); NEGATIVE feedback, one tick of latency
# ---------------------------------------------------------------------------------------------------------------------
class Loop:
    def __init__(self, c, notch=None, label=""):
        self.c, self.nc, self.label = c, notch, label
        self.kp = float(c["kp_Y"][0]); self.kd = float(c["kd_Y"][0])
        assert np.all(c["kp_Y"] == self.kp) and np.all(c["kd_Y"] == self.kd), "Kp/Kd not flat"

    def F(self, f):        # fb two-sample sum: (s + s'), s' = (a s + b x)>>10
        z = zf(f); c = self.c
        return (c["fb_b"] / 1024.0) * (1 + 1 / z) / (1 - (c["fb_a"] / 1024.0) / z)

    def C(self, f):        # P = E*Kp>>8 ; D = dE*Kd>>3
        z = zf(f)
        return self.kp / 256.0 + (self.kd / 8.0) * (1 - 1 / z)

    def N(self, f):
        return notch_H(self.nc, f) if self.nc else np.ones_like(np.asarray(f, float), dtype=complex)

    def Hlag(self, f):     # y = (s + s')>>5, s' = (a2 s + b2 S)>>10
        z = zf(f); c = self.c
        return (c["lag_b"] / 1024.0) * (1 + 1 / z) / (1 - (c["lag_a"] / 1024.0) / z) / 32.0

    def fwd(self, f):      # T per count of E: C * fade * N * Hlag * gain/2^15 * z^-1   (ramp = 1 engaged)
        return self.C(f) * (254.0 / 256.0) * self.N(f) * self.Hlag(f) * (self.c["gain"] / 32768.0) / zf(f)

    def ret(self, f):      # T per raw rate count
        return self.F(f) * self.fwd(f)


class Plant:
    def __init__(self, d):
        self.g0, self.tau, self.f1, self.fp, self.zp, self.kappa, self.label = d["g0"], d["tau"], d["f1"], d.get("fp"), d.get("zp"), d.get("kappa"), d["label"]

    def Gs(self, f):
        s = 2j * np.pi * np.asarray(f, float)
        G = self.g0 * np.exp(-s * self.tau) / (1 + s / (2 * np.pi * self.f1))
        if self.fp:
            wp = 2 * np.pi * self.fp
            M = wp ** 2 / (s ** 2 + 2 * self.zp * wp * s + wp ** 2)
            G = G * ((1 + self.kappa * (M - 1)) if self.kappa is not None else M)
        return G

    def Gd(self, f):
        w = 2 * np.pi * np.asarray(f, float)
        zoh = np.where(w == 0, 1.0, (1 - np.exp(-1j * w * TS)) / (1j * w * TS))
        return self.Gs(f) * zoh

    def discrete(self):
        """exact ZOH discretisation of the rational part; the delay is an integer number of ticks (all four fits are)."""
        w1 = 2 * np.pi * self.f1
        num, den = [self.g0 * w1], [1.0, w1]
        if self.fp:
            wp = 2 * np.pi * self.fp
            mnum, mden = [wp ** 2], [1.0, 2 * self.zp * wp, wp ** 2]
            if self.kappa is not None:       # 1 + k(M-1) = ((1-k) mden + k mnum)/mden
                mnum = np.polyadd((1 - self.kappa) * np.array(mden), self.kappa * np.array(mnum))
            num = np.polymul(num, mnum); den = np.polymul(den, mden)
        bz, az, _ = signal.cont2discrete((num, den), TS, method="zoh")
        nd = int(round(self.tau / TS)); assert abs(nd * TS - self.tau) < 1e-9
        return np.atleast_1d(np.squeeze(bz)), np.atleast_1d(np.squeeze(az)), nd


def L_of(lp, pl, f):
    return lp.ret(f) * CPD * pl.Gd(f)


FGRID = np.arange(0.5, 120.0, 0.01)


def nyquist_unstable(lp, pl):
    f = np.concatenate([np.arange(0.02, 60.0, 0.005), np.arange(60.0, 500.0, 0.1)])
    L = L_of(lp, pl, f)
    ph = np.unwrap(np.angle(1 + L))
    return int(round(2 * (ph[-1] - ph[0]) / (2 * np.pi))) != 0


def sens(lp, pl, lo=3.0, hi=80.0):
    f = FGRID[(FGRID >= lo) & (FGRID <= hi)]
    L = L_of(lp, pl, f)
    S = 1 / np.abs(1 + L)
    k = int(np.argmax(S))
    half = S[k] / np.sqrt(2); i0 = k; i1 = k
    while i0 > 0 and S[i0] > half:
        i0 -= 1
    while i1 < len(S) - 1 and S[i1] > half:
        i1 += 1
    zcl = (f[i1] - f[i0]) / (2 * f[k]) if S[k] > 1.5 else np.nan
    return dict(Ms=float(S[k]), fMs=float(f[k]), zcl=float(zcl), vm=float(np.min(np.abs(1 + L))), fvm=float(f[int(np.argmin(np.abs(1 + L)))]))


def cl_pole_td(lp, pl):
    """closed-loop pole from the impulse response of rate/ref (inverse FFT of the exact frequency response), 12-30 Hz band."""
    N = 2 ** 16
    f = np.fft.rfftfreq(N, TS); f[0] = 1e-6
    L = L_of(lp, pl, f)
    Tcl = (lp.fwd(f) * CPD * pl.Gd(f)) / (1 + L)
    h = np.fft.irfft(Tcl, n=N)[:6000]
    sos = signal.butter(4, (12.0, 30.0), btype="bandpass", fs=FS, output="sos")
    y = signal.sosfilt(sos, h); env = np.abs(signal.hilbert(y))
    k = int(np.argmax(env[:800])); seg = slice(k + 60, k + 700)
    ok = env[seg] > 1e-4 * env[k]
    if ok.sum() < 100:
        return np.nan, np.nan
    t = np.arange(len(h)) * TS
    sl = np.polyfit(t[seg][ok], np.log(env[seg][ok]), 1)[0]
    ph = np.unwrap(np.angle(signal.hilbert(y)))
    fi = float(np.median(np.gradient(ph[seg]) * FS / (2 * np.pi)))
    return fi, float(-sl / (2 * np.pi * fi))


# ---------------------------------------------------------------------------------------------------------------------
# byte-exact 1 kHz closed-loop mirror: integer controller (V850 sar floors, 32-bit mul), the cave via the interpreter
# ---------------------------------------------------------------------------------------------------------------------
def sar(v, k):
    return v >> k          # Python >> on int floors, as V850 sar


def clampi(v, lim):
    return max(-lim, min(lim, v))


class Controller:
    def __init__(self, c, img=None, use_cave=False, first_tick_sentinel=True):
        self.c = c; self.s_fb = 0; self.s_lag = 0; self.E_prev = None
        self.cave = CV.Cave(img) if use_cave else None
        self.kp = int(c["kp_Y"][0]); self.kd = int(c["kd_Y"][0])
        self.last = {}

    def tick(self, sp, x):
        """sp = setpoint (map output counts), x = gp-0x6a56 raw rate counts (the sign the PID sees).  Returns T."""
        c = self.c
        x = clampi(int(x), 12000)
        s_new = sar(c["fb_a"] * self.s_fb, 10) + sar(c["fb_b"] * x, 10)
        fb = clampi(self.s_fb + s_new, c["fb_clamp"]); self.s_fb = s_new
        E = 32 * int(sp) - fb
        P = clampi(sar(E * self.kp, 8), c["p_clamp"])
        dE = 0 if self.E_prev is None else (E - self.E_prev)      # Honda's first-tick guard: no D kick on the first tick
        self.E_prev = E
        D = clampi(sar(dE * self.kd, 3), c["d_clamp"])
        S = clampi(sar(254 * (P + D), 8), c["sum_clamp"])
        S_pre = S
        if self.cave is not None:
            S = self.cave.tick(S)
        s_new2 = sar(c["lag_a"] * self.s_lag, 10) + sar(c["lag_b"] * S, 10)
        y = sar(self.s_lag + s_new2, 5); self.s_lag = s_new2
        y = sar(y * 0x8000, 15)                                       # ramp = 1.0 engaged (Q15)
        y = ((y + 0x8000) & 0xFFFF) - 0x8000                          # sxh
        T = clampi(sar(-(-1) * y * c["gain"], 15), c["t_clamp"])      # gp-0x6752 = -1 and the (-1) of the formula cancel
        self.last = dict(E=E, P=P, D=D, S_pre=S_pre, S=S, y=y, T=T, fb=fb)
        return T


def closed_loop_step(c, img, use_cave, pl, sp_step, n=1500, open_loop=False):
    bz, az, nd = pl.discrete()
    ctl = Controller(c, img, use_cave)
    # plant state: direct-form on T history (deg/s), then rate raw = CPD * rate; the delay nd ticks
    Th = np.zeros(n + nd + 8); rate = np.zeros(n); T = np.zeros(n); S = np.zeros(n); Spre = np.zeros(n)
    zi = signal.lfilter_zi(bz, az) * 0.0
    x = 0
    for k in range(n):
        Tk = ctl.tick(sp_step if k >= 5 else 0, x)
        T[k] = Tk; S[k] = ctl.last["S"]; Spre[k] = ctl.last["S_pre"]
        Th[k + nd] = Tk
        # plant output at tick k+1 from T up to tick k (one tick of latency is in the controller read order: x used at
        # tick k is the rate produced by torque through tick k-1)
        yk, zi = signal.lfilter(bz, az, [Th[k]], zi=zi)
        rate[k] = yk[0]
        x = 0 if open_loop else int(round(CPD * rate[k]))
    acc = np.gradient(rate, TS)
    return dict(rate=rate, T=T, S=S, Spre=Spre, peak_rate=float(np.max(np.abs(rate))), peak_acc=float(np.max(np.abs(acc))),
                ss=float(np.mean(rate[-200:])), peak_T=float(np.max(np.abs(T))), peak_S=float(np.max(np.abs(S))), peak_Spre=float(np.max(np.abs(Spre))))


def main():
    img282 = open(CV.IMG282, "rb").read(); img289 = open(CV.IMG289, "rb").read()
    c282, c289 = cells(img282), cells(img289)
    nc = notch_ints(img289)
    pr("ADVERSARY B -- V289 rev 1 GATE 2 / units, rebuilt from the images")
    pr("cells V282: fb %d/%d lag %d/%d gain %d @0x%X clamps fb %d P %d D %d sum %d T %d Kp %s Kd %s ki %d" % (
        c282["fb_a"], c282["fb_b"], c282["lag_a"], c282["lag_b"], c282["gain"], c282["gain_addr"], c282["fb_clamp"], c282["p_clamp"], c282["d_clamp"], c282["sum_clamp"], c282["t_clamp"], c282["kp_Y"].astype(int).tolist(), c282["kd_Y"].astype(int).tolist(), c282["ki"]))
    pr("cells V289: fb %d/%d lag %d/%d gain %d @0x%X clamps fb %d P %d D %d sum %d T %d Kp %s Kd %s ki %d" % (
        c289["fb_a"], c289["fb_b"], c289["lag_a"], c289["lag_b"], c289["gain"], c289["gain_addr"], c289["fb_clamp"], c289["p_clamp"], c289["d_clamp"], c289["sum_clamp"], c289["t_clamp"], c289["kp_Y"].astype(int).tolist(), c289["kd_Y"].astype(int).tolist(), c289["ki"]))
    diff = [k for k in c282 if not np.array_equal(np.asarray(c282[k]), np.asarray(c289[k]))]
    pr("cells that differ V282 -> V289: %s" % diff)
    pr("notch integers recovered from the cave (movea immediates, in code order b0 / a2 / b1): %s" % nc)

    pr("\n== B1  fb filter, from the bytes")
    for nm, c in (("V282", c282), ("V289", c289)):
        dc = 2.0 * c["fb_b"] / (1024 - c["fb_a"]); fpole = -FS * np.log(c["fb_a"] / 1024.0) / (2 * np.pi)
        pr("  %s: a=%d (ld.h SIGNED @0x28F8A) b=%d (ld.hu UNSIGNED @0x28F86)  DC 2b/(1024-a) = %.4f  pole %.2f Hz  |x|max 12000 -> steady |s| %.0f, a*s %.3g, b*x %.3g (int32 %.3g)" % (
            nm, c["fb_a"], c["fb_b"], dc, fpole, c["fb_b"] * 12000 / (1024 - c["fb_a"]), c["fb_a"] * c["fb_b"] * 12000 / (1024 - c["fb_a"]), c["fb_b"] * 12000.0, 2.0 ** 31))
    dc282 = 2.0 * c282["fb_b"] / (1024 - c282["fb_a"]); dc289 = 2.0 * c289["fb_b"] / (1024 - c289["fb_a"])
    pr("  DC drift %+.4f %%  (FAIL if |.| > 0.5 %%) -> %s ; E bound: r26 clamp 0xC62E6 = %d in both (%s)" % (
        100 * (dc289 / dc282 - 1), "FAIL" if abs(dc289 / dc282 - 1) > 0.005 else "pass", c289["fb_clamp"], "identical" if c289["fb_clamp"] == c282["fb_clamp"] else "DIFFERENT"))
    # exact-integer DC check of the fb filter with the two-sample sum
    for c, nm in ((c282, "V282"), (c289, "V289")):
        for x in (1, 100, -100, 1000, -1000, 12000, -12000):
            s = 0
            for _ in range(3000):
                s_new = sar(c["fb_a"] * s, 10) + sar(c["fb_b"] * x, 10); fb = s + s_new; s = s_new
            pr("    %s exact int: x=%6d -> fb %7d  (float DC %.1f ; ratio %.4f)" % (nm, x, fb, x * (2.0 * c["fb_b"] / (1024 - c["fb_a"])), fb / (x * 2.0 * c["fb_b"] / (1024 - c["fb_a"]))))

    pr("\n== realised notch, from the integers (a0 = 2^14 implied by the sar 14)")
    f = np.arange(0.1, 500.0, 0.001)
    H = np.abs(notch_H(nc, f)); k = int(np.argmin(H)); f0 = f[k]
    lo = f[:k][np.where(H[:k] >= 1 / np.sqrt(2))[0][-1]]; hi = f[k:][np.where(H[k:] >= 1 / np.sqrt(2))[0][0]]
    pr("  DC = (b0+b1+b0)/(a0+a1+a2) = %d/%d = %s ; Nyquist = %d/%d" % (2 * nc["b0"] + nc["b1"], nc["a0"] + nc["a1"] + nc["a2"], "1 EXACT" if 2 * nc["b0"] + nc["b1"] == nc["a0"] + nc["a1"] + nc["a2"] else "NOT 1", 2 * nc["b0"] - nc["b1"], nc["a0"] - nc["a1"] + nc["a2"]))
    pr("  zero on the unit circle (b0 == b2): f0 = acos(-b1/(2 b0))/(2 pi) * fs = %.3f Hz ; grid min |H| = %.2e (%.1f dB) at %.3f Hz" % (np.degrees(np.arccos(-nc["b1"] / (2.0 * nc["b0"]))) / 360 * FS, H[k], 20 * np.log10(max(H[k], 1e-12)), f0))
    pr("  -3 dB band %.2f-%.2f Hz -> Q = f0/BW = %.3f ; |H| at 20.03/20.05/20.08 = %.4f/%.4f/%.4f" % (lo, hi, f0 / (hi - lo), *[abs(notch_H(nc, x)) for x in (20.03, 20.05, 20.08)]))
    for x in (1.0, 3.9, 5.0, 7.3, 10.0, 13.5, 15.0, 16.0, 17.0, 18.0, 23.0, 25.0, 30.0, 40.0, 50.0):
        h = notch_H(nc, x); pr("    %5.1f Hz  |H| %.4f  phase %+6.2f deg" % (x, abs(h), np.degrees(np.angle(h))))
    # exact sine test through the interpreter at four frequencies
    cv = CV.Cave(img289)
    for fx, A in ((20.036, 3000), (7.3, 3000), (3.9, 3000), (20.036, 15360)):
        cv = CV.Cave(img289); n = 3000; t = np.arange(n) * TS; x = np.round(A * np.sin(2 * np.pi * fx * t)).astype(int)
        y = np.array([cv.tick(int(v)) for v in x], float)
        seg = slice(1500, 3000); c1 = np.exp(-2j * np.pi * fx * t[seg])
        Hx = np.sum(y[seg] * c1) / np.sum(x[seg] * c1)
        pr("  interpreter sine %.3f Hz A=%d: |H| %.4f phase %+.2f deg (linear %.4f / %+.2f) ; peak |y| %d" % (fx, A, abs(Hx), np.degrees(np.angle(Hx)), abs(notch_H(nc, fx)), np.degrees(np.angle(notch_H(nc, fx))), int(np.max(np.abs(y)))))

    # ---- the loops
    plants = [Plant(d) for d in json.load(open(os.path.join(SCR, "loopshape20_plants.json"))).values()]
    L282 = Loop(c282, None, "V282 as-built")
    L289 = Loop(c289, nc, "V289 = notch + fb 875/2301")
    Lnot = Loop(c282, nc, "notch only (V282 cells)")
    Lfb = Loop(c289, None, "fb pole only (875/2301)")
    loops = [L282, L289, Lnot, Lfb]

    pr("\n== electronics only: return ratio R = F*C*fade*N*Hlag*gain/2^15*z^-1 (T per raw rate count), no plant")
    for fx in (3.9, 5.0, 7.3, 10.0, 13.5, 15.0, 16.0, 17.0, 20.04, 23.0, 25.0, 30.0, 40.0, 50.0):
        row = "  %6.2f Hz " % fx
        for lp in loops:
            R = lp.ret(fx); row += "| %-26s |R| %6.3f %+7.1f deg " % (lp.label[:26], abs(R), np.degrees(np.angle(R)))
        pr(row)
    pr("  ratio V289/V282 of |R| (= |L| ratio, plant-independent):")
    fl = np.arange(0.5, 5.01, 0.25); rl = np.abs(L289.ret(fl) / L282.ret(fl)); rn = np.abs(Lnot.ret(fl) / L282.ret(fl)); rf = np.abs(Lfb.ret(fl) / L282.ret(fl))
    pr("    below 5 Hz: V289 max |dL/L| %.2f %% (FAIL if > 5 %%) ; notch-only %.2f %% ; fb-only %.2f %%" % (100 * np.max(np.abs(rl - 1)), 100 * np.max(np.abs(rn - 1)), 100 * np.max(np.abs(rf - 1))))
    pr("    phase change at 3.9 Hz: V289 %+.2f deg (FAIL if < -5) ; notch-only %+.2f ; fb-only %+.2f" % tuple(np.degrees(np.angle(lp.ret(3.9) / L282.ret(3.9))) for lp in (L289, Lnot, Lfb)))
    for fx in (13.0, 14.0, 15.0, 16.0, 17.0):
        pr("    %4.1f Hz |L| ratio V289/V282 %.3f, phase %+.1f deg" % (fx, abs(L289.ret(fx) / L282.ret(fx)), np.degrees(np.angle(L289.ret(fx) / L282.ret(fx)))))
    fh = np.arange(25.0, 50.01, 0.5); pr("    25-50 Hz |L| ratio V289/V282: %.2f-%.2f" % (np.min(np.abs(L289.ret(fh) / L282.ret(fh))), np.max(np.abs(L289.ret(fh) / L282.ret(fh)))))
    fn = np.arange(30.0, 499.0, 0.5)
    def ng(lp):
        z = zf(fn); return float(np.sqrt(np.mean(np.abs(lp.F(fn) * (lp.kd / 8.0) * (1 - 1 / z)) ** 2)))
    pr("    rms rate->D gain 30-500 Hz: V289/V282 = %.3f" % (ng(L289) / ng(L282)))

    pr("\n== 7 Hz strong-turn gate |Ls*R73 + Lr| (record split Ls 0.55<96, Lr 1.19<-27 ; FAIL if > 1.02) -- from the bytes")
    for lp in loops:
        R73 = lp.ret(7.3) / L282.ret(7.3)
        g = abs(LS73 * R73 + LR73)
        pr("  %-28s R73 = %.4f < %+.2f deg -> gate %.4f  (x |Ltot| 0.944/0.976/0.990 -> %.3f/%.3f/%.3f)  %s" % (
            lp.label, abs(R73), np.degrees(np.angle(R73)), g, *(g / 1.003 * l for l in LTOT73), "FAIL" if g > 1.02 else "pass"))
    pr("  components at 7.3 Hz: notch |H| %.4f phase %+.2f deg ; fb pole V282 %+.2f deg -> V289 %+.2f deg (delta %+.2f deg, |.| ratio %.3f)" % (
        abs(notch_H(nc, 7.3)), np.degrees(np.angle(notch_H(nc, 7.3))), np.degrees(np.angle(L282.F(7.3))), np.degrees(np.angle(L289.F(7.3))), np.degrees(np.angle(L289.F(7.3) / L282.F(7.3))), abs(L289.F(7.3) / L282.F(7.3))))
    # sensitivity of the gate to the split: sweep the servo-arm share and angle
    pr("  gate sensitivity (V289) to the record's split: Ls share x0.5..x1.5, angle +-30 deg:")
    R73 = L289.ret(7.3) / L282.ret(7.3)
    for sc in (0.5, 0.75, 1.0, 1.25, 1.5):
        row = "    |Ls| x%.2f: " % sc
        for da in (-30, -15, 0, 15, 30):
            ls = LS73 * sc * np.exp(1j * np.radians(da)); lr = LR73
            row += " %+3d deg %.3f (as-built %.3f)" % (da, abs(ls * R73 + lr), abs(ls + lr))
        pr(row)

    pr("\n== B2  GATE 2 on the four plant fits (incl. the census-rejected SMOOTH): stability, S peak, pole, relocation")
    for pl in plants:
        pr("\n  PLANT %s  (g0 %.4f tau %.0f ms f1 %.0f)" % (pl.label, pl.g0, 1e3 * pl.tau, pl.f1))
        pr("    %-28s %-9s %6s %6s | %5s %6s | %5s %6s | %6s | %s" % ("loop", "nyquist", "Ms", "fMs", "z_cl", "vm", "f_vm", "|L|20", "fTD/zTD", "|L|,ang at 13/14/15/16/17/20/23 Hz"))
        for lp in loops:
            uns = nyquist_unstable(lp, pl); m = sens(lp, pl); ftd, ztd = cl_pole_td(lp, pl)
            band = " ".join("%.2f<%+.0f" % (abs(L_of(lp, pl, fx)), np.degrees(np.angle(L_of(lp, pl, fx)))) for fx in (13, 14, 15, 16, 17, 20.04, 23))
            pr("    %-28s %-9s %6.2f %6.2f | %5.3f %6.3f | %5.2f %6.3f | %5.1f/%.3f | %s" % (
                lp.label[:28], "UNSTABLE" if uns else "stable", m["Ms"], m["fMs"], m["zcl"], m["vm"], m["fvm"], abs(L_of(lp, pl, 20.04)), ftd, ztd, band))
        # closed-loop reference->rate |T_cl| peak location (does the ring move to 13-17 Hz?)
        for lp in (L282, L289, Lnot):
            fx = np.arange(5.0, 40.0, 0.01); L = L_of(lp, pl, fx); Tcl = np.abs(lp.fwd(fx) * CPD * pl.Gd(fx) / (1 + L))
            k = int(np.argmax(Tcl)); pr("    ref->rate |T_cl| peak: %-26s %.3f at %.2f Hz ; |T_cl| at 15 Hz %.3f, 20 Hz %.3f" % (lp.label[:26], Tcl[k], fx[k], Tcl[np.argmin(np.abs(fx - 15))], Tcl[np.argmin(np.abs(fx - 20))]))

    pr("\n== B3  authority: byte-exact 1 kHz closed-loop mirror (integer controller, cave via the interpreter), FAIL if peak rate or accel < 0.95x")
    pr("  steps applied at tick 5 from rest: capped-frame = 33 sp counts (E 1056); full-scale = 1032 sp counts (map ceiling, read from the image: max map_Y V289 = %d)" % int(c289["map_Y"].max()))
    for pl in plants:
        for sp in (33, 1032):
            a = closed_loop_step(c282, img282, False, pl, sp)
            b = closed_loop_step(c289, img289, True, pl, sp)
            pr("  %-40s sp %4d: peak rate %7.2f -> %7.2f deg/s (x%.3f)  peak acc %8.0f -> %8.0f deg/s2 (x%.3f)  ss %.2f -> %.2f  peak|T| %d -> %d  peak|S| pre/post notch %d/%d  %s" % (
                pl.label[:40], sp, a["peak_rate"], b["peak_rate"], b["peak_rate"] / a["peak_rate"], a["peak_acc"], b["peak_acc"], b["peak_acc"] / a["peak_acc"], a["ss"], b["ss"], int(a["peak_T"]), int(b["peak_T"]), int(b["peak_Spre"]), int(b["peak_S"]),
                "FAIL" if (b["peak_rate"] / a["peak_rate"] < 0.95 or b["peak_acc"] / a["peak_acc"] < 0.95) else "pass"))
    pr("  RECONCILIATION with the design's pkR/pkA = 1.00/1.00 for 'the pair': (i) LINEAR closed-loop step (the design's own method, no clamps),")
    pr("  (ii) the byte-exact mirror with the D/P/sum clamps opened (x100), (iii) the design's (f) row topology = notch on the FB OPERAND, not on the sum")
    class LoopFbNotch(Loop):
        def F(self, f):
            return Loop.F(self, f) * notch_H(self.nc, f)
        def N(self, f):
            return np.ones_like(np.asarray(f, float), dtype=complex)
    Lfbn = LoopFbNotch(c289, nc, "fb-NOTCH + fb pole (design f row)")
    def lin_step(lp, pl, E=1056.0, n=1500):
        N = 2 ** 15; f = np.fft.rfftfreq(N, TS); f[0] = 1e-6
        L = L_of(lp, pl, f); Tcl = (lp.fwd(f) * CPD * pl.Gd(f)) / (1 + L)
        h = np.fft.irfft(Tcl, n=N)[:n]; y = np.cumsum(h) * E / CPD; acc = np.gradient(y, TS)
        return float(np.max(np.abs(y))), float(np.max(np.abs(acc))), float(np.mean(y[-200:]))
    for pl in plants[2:]:
        r0 = lin_step(L282, pl)
        for lp in (L289, Lnot, Lfb, Lfbn):
            r = lin_step(lp, pl)
            pr("    LINEAR %-40s %-34s peak rate x%.3f  peak acc x%.3f  ss x%.3f" % (pl.label[:40], lp.label[:34], r[0] / r0[0], r[1] / r0[1], r[2] / r0[2]))
        cO = dict(c282); cO.update(p_clamp=c282["p_clamp"] * 100, d_clamp=c282["d_clamp"] * 100, sum_clamp=c282["sum_clamp"] * 100, t_clamp=c282["t_clamp"] * 100)
        cP = dict(c289); cP.update(p_clamp=c289["p_clamp"] * 100, d_clamp=c289["d_clamp"] * 100, sum_clamp=c289["sum_clamp"] * 100, t_clamp=c289["t_clamp"] * 100)
        a = closed_loop_step(cO, img282, False, pl, 33); b = closed_loop_step(cP, img289, True, pl, 33)
        pr("    MIRROR, clamps x100 %-30s sp 33: peak rate x%.3f  peak acc x%.3f  ss x%.3f   (as-built peak/ss %.2f, V289 %.2f)" % (pl.label[:30], b["peak_rate"] / a["peak_rate"], b["peak_acc"] / a["peak_acc"], b["ss"] / a["ss"], a["peak_rate"] / a["ss"], b["peak_rate"] / b["ss"]))
        a = closed_loop_step(c282, img282, False, pl, 33); b = closed_loop_step(c289, img289, True, pl, 33)
        pr("    MIRROR, byte-exact    %-30s sp 33: t90 %.0f -> %.0f ms ; overshoot %.1f %% -> %.1f %% ; D clamp binds on the step: |dE*Kd>>3| = %d vs clamp %d" % (
            pl.label[:30], 1e3 * TS * int(np.argmax(a["rate"] >= 0.9 * a["ss"])), 1e3 * TS * int(np.argmax(b["rate"] >= 0.9 * b["ss"])), 100 * (a["peak_rate"] / a["ss"] - 1), 100 * (b["peak_rate"] / b["ss"] - 1), 1056 * 128 >> 3, c282["d_clamp"]))
    pr("  OPEN-LOOP (rate held 0): torque T into the motor for the same steps -- the notch's overshoot question")
    for sp in (33, 100, 300, 1032):
        a = closed_loop_step(c282, img282, False, plants[0], sp, open_loop=True, n=600)
        b = closed_loop_step(c289, img289, True, plants[0], sp, open_loop=True, n=600)
        pr("    sp %4d: V282 peak|T| %4d (S %5d)  V289 peak|T| %4d (S pre-notch %5d, post %5d)  ratio T %.3f ; first 60 ms T V282 %s / V289 %s" % (
            sp, int(a["peak_T"]), int(a["peak_S"]), int(b["peak_T"]), int(b["peak_Spre"]), int(b["peak_S"]), b["peak_T"] / max(a["peak_T"], 1),
            [int(v) for v in a["T"][5:65:10]], [int(v) for v in b["T"][5:65:10]]))
    # sub-rail step where the notch overshoot is NOT clamped: S = 10000 constant step
    cvA = CV.Cave(img289); ys = [cvA.tick(10000) for _ in range(300)]
    pr("    cave alone, step 0 -> 10000: peak y %d (x%.3f) at tick %d, back within 1 %% after %d ticks ; step 0 -> 15360: peak y %d (clamped from linear %.0f)" % (
        max(ys), max(ys) / 10000.0, int(np.argmax(ys)), int(np.where(np.abs(np.array(ys) - 10000) > 100)[0][-1]) + 1,
        max(CV.Cave(img289).tick(15360) for _ in range(300)) if False else max([CV.Cave(img289)][0].tick(15360) for _ in range(1)) , 0.0))
    cvB = CV.Cave(img289); yb = [cvB.tick(15360) for _ in range(300)]
    pr("    cave alone, step 0 -> 15360 (rail): peak y %d = the 0xC61BE clamp (%s), linear peak would be %.0f (x%.3f)" % (
        max(yb), "clamp binds" if max(yb) == c289["sum_clamp"] else "clamp NOT binding", 15360 * 1.155, 1.155))
    # T excess through the lag for a 10000 step, open loop
    a = closed_loop_step(c282, img282, False, plants[0], 0, open_loop=True, n=10)
    with open(os.path.join(SCR, "adv_v289_b_loop.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/adv_v289_b_loop.txt")


if __name__ == "__main__":
    main()
