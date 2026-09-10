# -*- coding: utf-8 -*-
"""studies/grind/adv_v290_physics.py -- ADVERSARIAL re-derivation of the V290 (ii-c) claim: "subtracting n>>3 (n = the
V289 notch's removed component) from the OUTPUT-LAG result adds damping to the 20 Hz plant mode".  Agent advphys,
2026-09-09.  Analysis only: builds nothing, flashes nothing, sends nothing.

INDEPENDENT of design290_candidates.py for the crux: every electronic block is re-read from the V289 IMAGE bytes here
(cal cells, Kp/Kd records, gain redirect, the notch cave's movea immediates) and the closed-loop poles are found by
ROOT-FINDING the characteristic polynomial 1 + L(z) = 0 (exact for the model), NOT by the sensitivity-peak width the
design used.  The plant fits are the record's (_scratch/loopshape20_plants.json) -- the brief asks for those -- but
they are re-discretised here with an exact ZOH (scipy cont2discrete) and an integer-tick delay.

Sign chain, from the listing (0x28F4C-0x28FAC fb filter, 0x2A174-0x2A1FE lag / ramp / gain), feedback side only:
   x = gp-0x6a56 = -(0x18F wire rate)         E = 32 sp - F x  = -F x
   S = fade * C * E                            (fade 254/256; C = Kp/256 + (Kd/8)(1 - z^-1))
   y_n = N S      (V289 cave; n = S - y_n = (1 - N) S)
   y   = Hlag y_n (0x2A178-0x2A1AC; y = (s + s')>>5, s' = (992 s>>10) + (507 S>>10))
   y'  = y - g n  (the V290 term at 0x2A1B0, BEFORE the ramp multiply at 0x2A1E6)
   T   = -K y' ramp  (0x2A1E6 mul r14 ; 0x2A1F2 ld.b -0x6752 = -1 ; 0x2A1EE gain 0xC6CD0 = 5346, K = 5346/32768)
   => T = +K fade C F [Hlag N - g (1 - N)] x      and  x = -wire,  wire = CPD * G(s) * T  (G > 0 per the fits)
   => T = -R wire  with  R = K fade C F [Hlag N - g(1-N)] z^-1 ;  characteristic  1 + R * CPD * Gd(z) = 0.
   The design's ret() has exactly this bracket (npost: -g (1-N) F C fade, no Hlag) -- the model and the code AGREE on the
   sign of the term; what this script tests is whether that term DAMPS the mode on the plant fits, by exact poles.

Run:  python adv_v290_physics.py     (writes _scratch/adv_v290_physics.txt beside it)
"""
import glob
import json
import os
import struct
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = 1e-3, 1000.0, 8.0
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# ---------------------------------------------------------------------------------------------------------------- bytes
def read_v289():
    p = glob.glob(FW + "_v289_*_plain_image.bin")[0]
    b = open(p, "rb").read()
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]
    s16 = lambda a: struct.unpack_from("<h", b, a)[0]
    u32 = lambda a: struct.unpack_from("<I", b, a)[0]
    c = {}
    c["path"] = os.path.basename(p)
    c["fb_a"], c["fb_b"] = s16(0xC63E8), u16(0xC63EA)          # ld.h (signed) @0x28F8A, ld.hu @0x28F86
    c["lag_a"], c["lag_b"] = s16(0xC63EC), u16(0xC63EE)        # ld.h @0x2A184, ld.hu @0x2A174 (displaced into the cave @0xC4C84)
    c["gain_addr"] = 0xBF000 + u16(0x2A1F0); c["gain"] = s16(c["gain_addr"])
    c["neg1"] = None                                             # gp-0x6752 is RAM (.data -1 per the record) -- not in the image
    base = u32(0xCB994 + 4 * 7); c["kp_Y"] = [u16(base + 2 + 10 + 2 * i) for i in range(5)]
    base = u32(0xCB7D4 + 4 * 7); c["kd_Y"] = [u16(base + 2 + 8 + 2 * i) for i in range(4)]
    c["sum_clamp"], c["t_clamp"], c["d_clamp"], c["p_clamp"] = u16(0xC61BE), u16(0xC61B4), u16(0xC61B6), u16(0xC61BC)
    c["fb_clamp"] = u16(0xC62E6); c["deadband"] = u16(0xC61B8); c["r16flag"] = b[0xC64A3]
    # notch immediates: movea 0x3eb0,r0,r13 @0xC4C0E (b0), movea 0x3d60 @0xC4C26 (a2), movea -0x7c62 @0xC4C3C (b1 == a1)
    c["b0"], c["a2"], c["b1"] = s16(0xC4C10), s16(0xC4C28), s16(0xC4C3E)
    c["a1"], c["a0"] = c["b1"], 1 << 14
    assert b[0xC4C1C:0xC4C1E] == bytes.fromhex("ae32"), "sar 0xe,r6 (Q14) expected at 0xC4C1C"
    assert b[0x2A174:0x2A178] == bytes.fromhex("89078caa"), "hook jr expected at 0x2A174"
    assert b[0x2A1AC:0x2A1B6] == bytes.fromhex("a54a6182643fc5c29a1d"), "sar 5,r9 ; cmp 1,r16 ; st.w r7,-0x3d3c ; bne expected"
    assert b[0x2A1E6:0x2A1EE] == bytes.fromhex("ee4f2002af4ae900"), "mul r14,r9 ; sar 0xf ; sxh expected at 0x2A1E6"
    return c, b


# --------------------------------------------------------------------------------------------- polynomials in w = z^-1
def pmul(*ps):
    out = np.array([1.0])
    for p in ps:
        out = np.convolve(out, np.asarray(p, float))
    return out


def padd(a, b):
    n = max(len(a), len(b)); out = np.zeros(n); out[:len(a)] += a; out[:len(b)] += b
    return out


def pev(p, f):
    w = np.exp(-2j * np.pi * np.asarray(f, float) * TS)
    return sum(c * w ** k for k, c in enumerate(p))


class Blocks:
    """every block as (num, den) in w = z^-1, byte-read constants."""

    def __init__(self, c, notch=True, g=0.0, kp=None):
        self.c = c
        kp = float(c["kp_Y"][0] if kp is None else kp); kd = float(c["kd_Y"][0])
        self.F = (np.array([c["fb_b"] / 1024.0, c["fb_b"] / 1024.0]), np.array([1.0, -c["fb_a"] / 1024.0]))
        self.C = (np.array([kp / 256.0 + kd / 8.0, -kd / 8.0]), np.array([1.0]))
        self.fade = 254.0 / 256.0
        self.Hlag = (np.array([c["lag_b"] / 1024.0 / 32.0] * 2), np.array([1.0, -c["lag_a"] / 1024.0]))
        self.K = c["gain"] / 32768.0
        if notch:
            self.N = (np.array([c["b0"], c["b1"], c["b0"]], float) / c["a0"], np.array([c["a0"], c["a1"], c["a2"]], float) / c["a0"])
        else:
            self.N = (np.array([1.0]), np.array([1.0]))
        self.oneMinusN = (padd(self.N[1], -self.N[0]), self.N[1])
        self.g = g

    def bracket(self):
        """Hlag N - g (1 - N)  over the common denominator Hlag_den * N_den"""
        hn, hd = self.Hlag; nn, nd = self.N; mn, _ = self.oneMinusN
        num = padd(pmul(hn, nn), -self.g * pmul(mn, hd))
        return num, pmul(hd, nd)

    def R(self):
        """T per raw count of x (the record's negative-feedback convention): K fade C F bracket z^-1"""
        bn, bd = self.bracket()
        num = pmul([0.0, 1.0], self.F[0], self.C[0], bn) * self.K * self.fade
        den = pmul(self.F[1], self.C[1], bd)
        return num, den

    def Rf(self, f):
        n, d = self.R(); return pev(n, f) / pev(d, f)

    def fwd(self):
        """T per count of E (setpoint side): K fade C bracket z^-1 (no F)"""
        bn, bd = self.bracket()
        return pmul([0.0, 1.0], self.C[0], bn) * self.K * self.fade, pmul(self.C[1], bd)


# ------------------------------------------------------------------------------------------------------------ plant
class Plant:
    def __init__(self, d, fp_scale=1.0, label=None):
        self.g0, self.tau, self.f1, self.fp, self.zp, self.kappa = d["g0"], d["tau"], d["f1"], d["fp"], d["zp"], d.get("kappa")
        if self.fp:
            self.fp = self.fp * fp_scale
        self.label = label or d["label"]
        self.nd = int(round(self.tau / TS))
        assert abs(self.nd * TS - self.tau) < 1e-9, "delay must be an integer number of ticks"
        w1 = 2 * np.pi * self.f1
        num, den = np.array([self.g0 * w1]), np.array([1.0, w1])
        if self.fp:
            wp = 2 * np.pi * self.fp
            mden = np.array([1.0, 2 * self.zp * wp, wp ** 2]); mnum = np.array([wp ** 2])
            if self.kappa is not None:
                mnum = np.polyadd((1 - self.kappa) * mden, self.kappa * mnum)
            num, den = np.polymul(num, mnum), np.polymul(den, mden)
        bz, az, _ = signal.cont2discrete((num, den), TS, method="zoh")
        bz = np.atleast_1d(np.squeeze(bz)); az = np.atleast_1d(np.squeeze(az))
        # cont2discrete returns descending powers of z; the same coefficient list read ascending is in w = z^-1 after
        # multiplying num and den by z^-deg: G(z) = sum b_k z^{-k} / sum a_k z^{-k} (deg(bz) == deg(az) as returned)
        assert len(bz) == len(az)
        self.num = np.concatenate([np.zeros(self.nd), bz])   # * z^-nd
        self.den = az.copy()

    def Gf(self, f):
        return pev(self.num, f) / pev(self.den, f)

    def Gs(self, f):
        s = 2j * np.pi * np.asarray(f, float)
        G = self.g0 * np.exp(-s * self.tau) / (1 + s / (2 * np.pi * self.f1))
        if self.fp:
            wp = 2 * np.pi * self.fp
            M = wp ** 2 / (s ** 2 + 2 * self.zp * wp * s + wp ** 2)
            G = G * ((1 + self.kappa * (M - 1)) if self.kappa is not None else M)
        return G


def loop(el, pl):
    rn, rd = el.R()
    return pmul(rn, pl.num) * CPD, pmul(rd, pl.den)


def Lf(el, pl, f):
    n, d = loop(el, pl); return pev(n, f) / pev(d, f)


def poles(el, pl):
    n, d = loop(el, pl)
    ch = padd(d, n)                         # 1 + L = 0  <=>  d + n = 0   (polynomial in w)
    w = np.roots(ch[::-1])                  # np.roots wants highest power first
    w = w[np.abs(w) > 1e-12]
    z = 1.0 / w
    s = np.log(z) * FS
    f = np.abs(s.imag) / (2 * np.pi)
    zeta = -s.real / np.abs(s)
    return f, zeta, z


def mode_pole(el, pl, lo=12.0, hi=32.0):
    f, zeta, z = poles(el, pl)
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan
    k = np.argmin(zeta[m])                  # the least-damped pole in the band
    return float(f[m][k]), float(zeta[m][k])


def all_poles_str(el, pl, lo=2.0, hi=60.0):
    f, zeta, z = poles(el, pl)
    m = (f >= lo) & (f <= hi) & (zeta < 0.7)
    o = np.argsort(f[m])
    return " ".join("%.1fHz/%.3f" % (a, b) for a, b in zip(f[m][o], zeta[m][o]))


def Ms(el, pl):
    f = np.arange(3.0, 80.0, 0.02)
    S = 1 / np.abs(1 + Lf(el, pl, f)); k = int(np.argmax(S))
    return float(S[k]), float(f[k])


def unstable(el, pl):
    f, zeta, z = poles(el, pl)
    return bool(np.any(np.abs(z) >= 1.0))


def impulse_zeta(el, pl, n=3000):
    """time-domain cross-check: closed-loop impulse response of the wheel rate to a reference kick, band 12-30 Hz decay."""
    fn, fd = el.fwd(); ln, ld = loop(el, pl)
    # Tcl = fwd * CPD * G / (1 + L) = (fn * CPD * pl.num / (fd * pl.den)) / ((ld + ln)/ld); ld == fd_part*... build directly
    num = pmul(fn, pl.num) * CPD; den = pmul(fd, pl.den)
    # 1 + L over ld: (ld + ln)/ld  with ld = pmul(rd, pl.den) where rd = pmul(F_den, C_den, bracket_den); fd = pmul(C_den, bracket_den)
    # => Tcl = num/den * ld/(ld+ln)
    Tn = pmul(num, ld); Td = pmul(den, padd(ld, ln))
    x = np.zeros(n); x[0] = 1.0
    h = signal.lfilter(Tn, Td, x)
    sos = signal.butter(4, (12.0, 30.0), btype="bandpass", fs=FS, output="sos")
    y = signal.sosfilt(sos, h); env = np.abs(signal.hilbert(y))
    k = int(np.argmax(env[:800])); seg = slice(k + 60, k + 700)
    ok = env[seg] > 1e-4 * env[k]
    if ok.sum() < 100:
        return np.nan, np.nan
    t = np.arange(n) * TS
    sl = np.polyfit(t[seg][ok], np.log(env[seg][ok]), 1)[0]
    ph = np.unwrap(np.angle(signal.hilbert(y)))
    fi = float(np.median(np.gradient(ph[seg]) * FS / (2 * np.pi)))
    return fi, float(-sl / (2 * np.pi * fi))


LS73, LR73 = 0.55 * np.exp(1j * np.radians(96.0)), 1.19 * np.exp(1j * np.radians(-27.0))


# ------------------------------------------------------------------------------------------------- integer mirrors
def sar(v, k):
    return v >> k


class NotchInt:
    def __init__(self, c):
        self.c = c; self.s1 = 0; self.s2 = 0; self.e = 0; self.n = 0; self.y = 0

    def tick(self, x):
        c = self.c
        acc = c["b0"] * x + self.s1 + self.e
        y = sar(acc, 14); self.e = acc & 0x3FFF
        s2n = c["b0"] * x - c["a2"] * y
        n = x - y
        self.s1 = c["b1"] * n + self.s2; self.s2 = s2n
        self.n, self.y = n, y
        return max(-c["sum_clamp"], min(c["sum_clamp"], y)), n, y


class LagInt:
    def __init__(self, c):
        self.c = c; self.s = 0

    def tick(self, u):
        c = self.c
        sn = sar(c["lag_a"] * self.s, 10) + sar(c["lag_b"] * u, 10)
        y = sar(self.s + sn, 5); self.s = sn
        return y


def main():
    c, img = read_v289()
    pr("adv_v290_physics -- image %s" % c["path"])
    pr("bytes: fb a/b %d/%d  lag a/b %d/%d  gain %d @0x%X  Kp %s  Kd %s  clamps P %d D %d sum %d T %d fb %d  deadband(0xC61B8) %d  r16 flag(0xC64A3) %d" % (
        c["fb_a"], c["fb_b"], c["lag_a"], c["lag_b"], c["gain"], c["gain_addr"], c["kp_Y"], c["kd_Y"], c["p_clamp"], c["d_clamp"], c["sum_clamp"], c["t_clamp"], c["fb_clamp"], c["deadband"], c["r16flag"]))
    pr("notch ints from the cave's movea immediates: b0=b2 %d  b1=a1 %d  a2 %d  a0 %d" % (c["b0"], c["b1"], c["a2"], c["a0"]))
    el289 = Blocks(c, notch=True)
    c282 = dict(c); c282["fb_a"], c282["fb_b"] = 923, 1560
    el282 = Blocks(c282, notch=False)
    mn, md = el289.oneMinusN
    pr("1 - N = (%s) / A(z)  -> numerator %s : a pure (1 - z^-2) band-pass, DC gain 0 and Nyquist gain 0 EXACTLY (numerator zeros at z = +-1)" % (
        np.round(mn * c["a0"]).astype(int).tolist(), "336/16384 * (1 - z^-2)" if abs(mn[0] * c["a0"] - 336) < 1e-6 and abs(mn[1]) < 1e-9 else "UNEXPECTED"))

    # ============================================================================================================
    pr("\n" + "=" * 140)
    pr("1. ELECTRONIC PHASES FROM THE BYTES (deg, |.|), V289 cells, at 15 / 18 / 20.3 / 22 / 25 Hz")
    pr("=" * 140)
    fl = np.array([15.0, 18.0, 20.036, 20.3, 22.0, 25.0, 7.3, 3.9])
    z = np.exp(2j * np.pi * fl * TS)
    items = [
        ("fb one-pole 1/(1-875/1024 z^-1)  [25.0 Hz]", 1 / (1 - (c["fb_a"] / 1024.0) / z)),
        ("fb two-sample sum (1+z^-1)", 1 + 1 / z),
        ("F total (DC %.2f)" % (2 * c["fb_b"] / (1024 - c["fb_a"])), pev(el289.F[0], fl) / pev(el289.F[1], fl)),
        ("C = Kp/256 + Kd/8 (1-z^-1)  [D lead]", pev(el289.C[0], fl)),
        ("F*C*fade  (S per count of x, sign dropped)", pev(el289.F[0], fl) / pev(el289.F[1], fl) * pev(el289.C[0], fl) * el289.fade),
        ("tick delay z^-1", 1 / z),
        ("output lag one-pole 1/(1-992/1024 z^-1) [5.05 Hz]", 1 / (1 - (c["lag_a"] / 1024.0) / z)),
        ("output lag (1+z^-1)", 1 + 1 / z),
        ("Hlag total (DC %.4f)" % (2 * c["lag_b"] / (1024 - c["lag_a"]) / 32), pev(el289.Hlag[0], fl) / pev(el289.Hlag[1], fl)),
        ("N (V289 integer notch)", pev(el289.N[0], fl) / pev(el289.N[1], fl)),
        ("1 - N  = n per count of S", pev(mn, fl) / pev(md, fl)),
        ("Hlag*N = y_post per count of S (V289)", pev(el289.Hlag[0], fl) / pev(el289.Hlag[1], fl) * pev(el289.N[0], fl) / pev(el289.N[1], fl)),
    ]
    for g in (1 / 16, 1 / 8, 1 / 4):
        e = Blocks(c, True, g); bn, bd = e.bracket()
        items.append(("Hlag*N - (1-N)/%g = y' per count of S" % (1 / g), pev(bn, fl) / pev(bd, fl)))
    items.append(("-(1-N)/8 alone (the added term per count of S)", -pev(mn, fl) / pev(md, fl) / 8))
    items.append(("R V282 = T per count of x", el282.Rf(fl)))
    items.append(("R V289", el289.Rf(fl)))
    items.append(("R V289 + (ii-c) g=1/8", Blocks(c, True, 1 / 8).Rf(fl)))
    items.append(("added term in R alone: -g(1-N) F C fade K z^-1, g=1/8", Blocks(c, True, 1 / 8).Rf(fl) - el289.Rf(fl)))
    pr("  %-52s" % "block" + " ".join("| %6.1f Hz       " % f for f in fl))
    for nm, v in items:
        pr("  %-52s" % nm + " ".join("| %+6.1f %8.3f" % (np.degrees(np.angle(x)), abs(x)) for x in v))
    Rt = Blocks(c, True, 1 / 8).Rf(fl) - el289.Rf(fl)
    pr("\n  the added term's return-ratio angle (deg): " + "  ".join("%.1f Hz: %+.0f" % (f, np.degrees(np.angle(x))) for f, x in zip(fl[:6], Rt[:6])))
    pr("  the as-built V282 action angle (deg):      " + "  ".join("%.1f Hz: %+.0f" % (f, np.degrees(np.angle(x))) for f, x in zip(fl[:6], el282.Rf(fl)[:6])))
    pr("  => at 20.3 Hz the term sits %.0f deg from V282's action; the design's '+120 deg' is NOT the term's own angle: the term's" % (
        np.degrees(np.angle(Rt[3] / el282.Rf(fl)[3]))))
    pr("     angle is 180 + angle(1-N) + angle(F C fade) - 7.3 (tick) = %+.0f deg at 20.3 Hz.  Whether that DAMPS depends on the plant angle." % np.degrees(np.angle(Rt[3])))

    # ============================================================================================================
    pr("\n" + "=" * 140)
    pr("2. CLOSED-LOOP POLES BY ROOT-FINDING 1 + L(z) = 0  (exact for the model; the design used the S-peak width)")
    pr("   plants: the record's four fits + wire-centred (fp scaled so the as-built V282 pole sits at ~20.05 Hz)")
    pr("=" * 140)
    P = json.load(open(os.path.join(SCR, "loopshape20_plants.json")))
    plants = []
    for k in ("weak-mode", "smooth+mode"):
        d = P[k]; best = None
        for sc in np.arange(0.85, 1.0001, 0.005):
            pl = Plant(d, sc, "%s fp x%.3f -> %.2f Hz WIRE-CENTRED" % (k, sc, d["fp"] * sc))
            f0, z0 = mode_pole(el282, pl)
            if best is None or abs(f0 - 20.05) < abs(best[1] - 20.05):
                best = (pl, f0, sc)
        plants.append(best[0])
        pr("  centring %-12s: fp x%.3f gives as-built V282 pole %.2f Hz (design used x0.93)" % (k, best[2], best[1]))
        plants.append(Plant(d, 0.93, "%s fp x0.93 (design's centring)" % k))
    for k in ("weak-mode", "smooth+mode", "resonant", "smooth"):
        plants.append(Plant(P[k], 1.0, P[k]["label"] + " (as fitted)"))

    cands = [("V282 as-built", Blocks(c282, False, 0.0)),
             ("V289 as-built (notch + fb 875/2301)", Blocks(c, True, 0.0)),
             ("V289 + (ii-c) g = 1/16", Blocks(c, True, 1 / 16)),
             ("V289 + (ii-c) g = 1/8   <- the claim", Blocks(c, True, 1 / 8)),
             ("V289 + (ii-c) g = 1/4", Blocks(c, True, 1 / 4)),
             ("V289 + (ii-c) OPPOSITE sign g = -1/8", Blocks(c, True, -1 / 8)),
             ("V289 + (ii-c) OPPOSITE sign g = -1/16", Blocks(c, True, -1 / 16)),
             ("V282 cells + notch + (ii-c) g = 1/8", Blocks(dict(c282, **{k: c[k] for k in ("b0", "b1", "a1", "a2", "a0")}), True, 1 / 8))]
    el0 = cands[0][1]
    summary = {}
    for pl in plants:
        pr("\n  --- plant: %s  (g0 %.4f, tau %.0f ms, f1 %.0f Hz%s)  plant angle at 20.3 Hz: Gs %+.0f deg, Gd(zoh) %+.0f deg" % (
            pl.label, pl.g0, 1e3 * pl.tau, pl.f1, (", fp %.2f zp %.3f%s" % (pl.fp, pl.zp, (" kappa %.1f" % pl.kappa) if pl.kappa else "")) if pl.fp else "",
            np.degrees(np.angle(pl.Gs(20.3))), np.degrees(np.angle(pl.Gf(20.3)))))
        pr("  %-40s | %6s %6s | %6s %6s | %5s %5s | %6s %6s %5s | %s" % ("candidate", "f_pole", "zeta", "f_TD", "z_TD", "Ms", "fMs", "gate73", "d3.9", "stab", "all poles 2-60 Hz (f/zeta)"))
        for nm, el in cands:
            f0, z0 = mode_pole(el, pl); ftd, ztd = impulse_zeta(el, pl); ms, fms = Ms(el, pl)
            R73 = el.Rf(7.3) / el0.Rf(7.3); gate = abs(LS73 * R73 + LR73)
            d39 = np.degrees(np.angle(Lf(el, pl, 3.9) / Lf(el0, pl, 3.9)))
            uns = unstable(el, pl)
            summary.setdefault(nm, {})[pl.label] = (f0, z0, ztd, uns)
            pr("  %-40s | %6.2f %6.3f | %6.2f %6.3f | %5.2f %5.1f | %6.3f %+5.1f | %-5s | %s" % (
                nm[:40], f0, z0, ftd, ztd, ms, fms, gate, d39, "UNST" if uns else "ok", all_poles_str(el, pl)))

    pr("\n  SUMMARY -- least-damped 12-32 Hz pole zeta (root-finding) per plant; '<' = LESS damped than V289 as-built")
    labels = [pl.label for pl in plants]
    pr("  %-40s " % "candidate" + " ".join("| %-9s" % (l[:9]) for l in labels))
    for nm, _ in cands:
        row = []
        for l in labels:
            z0 = summary[nm][l][1]; zb = summary["V289 as-built (notch + fb 875/2301)"][l][1]
            row.append("| %6.3f %s " % (z0, "<" if z0 < zb - 1e-4 else (" " if abs(z0 - zb) <= 1e-4 else ">")))
        pr("  %-40s " % nm[:40] + " ".join(row))

    # a fine sweep of g on both signs, wire-centred plants
    pr("\n  g sweep (both signs), least-damped 12-32 Hz pole, wire-centred plants + un-centred fits:")
    gs = [-0.25, -0.125, -0.0625, -0.03125, 0, 0.03125, 0.0625, 0.125, 0.1875, 0.25, 0.375, 0.5]
    pr("  %-44s " % "plant" + " ".join("| g=%+.3f" % g for g in gs))
    for pl in plants:
        row = []
        for g in gs:
            f0, z0 = mode_pole(Blocks(c, True, g), pl)
            row.append("| %5.3f@%4.1f" % (z0, f0))
        pr("  %-44s " % pl.label[:44] + " ".join(row))

    # perturbation view: where is the damping quadrant for an added term at 20.3 Hz on each plant?
    pr("\n  damping quadrant by exact poles: an idealised added return-ratio term k e^{j phi} BP(20.3, Q3), k = 1.0 T/count, on the V289 base;")
    pr("  zeta of the least-damped 12-32 Hz pole vs phi (deg); the term's actual angle at 20.3 Hz is %+.0f deg" % np.degrees(np.angle(Rt[3])))
    w0 = 2 * np.pi * 20.3 / FS; al = np.sin(w0) / 6.0
    bpn = np.array([al, 0, -al]) / (1 + al); bpd = np.array([1.0, -2 * np.cos(w0) / (1 + al), (1 - al) / (1 + al)])

    class Ideal(Blocks):
        def __init__(self, c, k, phi):
            super().__init__(c, True, 0.0); self.k, self.phi = k, phi

        def R(self):
            n, d = super().R()
            # add k e^{j phi} BP: complex coefficients -> poles come in non-conjugate pairs; evaluate with a real
            # equivalent instead: rotate by phi using a real all-pass is not exact, so use the complex polynomial and
            # take |zeta| of the root nearest 20 Hz (np.roots handles complex coefficients).
            term = self.k * np.exp(1j * np.radians(self.phi)) * bpn
            num = padd(pmul(n, bpd), pmul(term, d)); den = pmul(d, bpd)
            return num, den

    for pl in plants[:4]:
        line = "  %-44s" % pl.label[:44]
        for phi in range(0, 360, 30):
            e = Ideal(c, 1.0, phi)
            n, d = loop(e, pl); ch = padd(d, n); w = np.roots(ch[::-1]); w = w[np.abs(w) > 1e-12]; zz = 1 / w
            s = np.log(zz) * FS; f = s.imag / (2 * np.pi); ze = -s.real / np.abs(s)
            m = (f >= 12) & (f <= 32)          # complex coefficients: only the positive-frequency root is meaningful
            line += " %3d:%s" % (phi, ("%.3f" % np.min(ze[m])) if m.any() else "  nan")
        pr(line)

    # ============================================================================================================
    pr("\n" + "=" * 140)
    pr("3. HAZARDS (integer mirror of the V289 cave + the lag, byte-exact arithmetic; V850 sar floors)")
    pr("=" * 140)
    # (e) DC / low-frequency leakage of n
    for X in (0, 1, 7, 100, 1234, -1234, 15360, -15360):
        nt = NotchInt(c); ns = []
        for k in range(6000):
            _, n, y = nt.tick(X); ns.append(n)
        tail = np.array(ns[-3000:])
        pr("  const S=%6d: mean n over last 3000 ticks %+.4f  (min %d max %d)  mean(n>>3) %+.4f" % (X, tail.mean(), tail.min(), tail.max(), np.mean(tail >> 3)))
    # slow ramp
    nt = NotchInt(c); ns = []
    for k in range(20000):
        _, n, y = nt.tick(int(k * 15360 / 20000)); ns.append(n)
    ns = np.array(ns); pr("  ramp 0->15360 over 20 s: n mean %+.3f, |n| max %d  (linear prediction |1-N| at 0.05 Hz ~ %.2e)" % (ns[2000:].mean(), np.abs(ns[2000:]).max(), abs(pev(mn, 0.05) / pev(md, 0.05))))
    # (c) railed S: 20 Hz square wave +-15360 (P saturated) -> n, y', T
    for fsq in (20.0, 7.3):
        nt = NotchInt(c); lg = LagInt(c); rows = []
        for k in range(3000):
            S = c["sum_clamp"] if np.sin(2 * np.pi * fsq * k * TS) >= 0 else -c["sum_clamp"]
            yc, n, y = nt.tick(S); yl = lg.tick(yc)
            rows.append((S, n, y, yl))
        A = np.array(rows[1000:])
        for g8 in (16, 32, 64):
            yp = A[:, 3] - (A[:, 1] * g8 >> 8)
            T = np.clip((yp * c["gain"]) >> 15, -c["t_clamp"], c["t_clamp"])
            Tun = (yp * c["gain"]) >> 15
            pr("  S = +-15360 square at %4.1f Hz, g=%d/256: |n| max %5d  |y_lag| max %5d  |y'| max %5d (int16 ok: %s)  |T| max %4d, T-clamp binds %.1f %% of ticks (V289: |T| max %d)" % (
                fsq, g8, np.abs(A[:, 1]).max(), np.abs(A[:, 3]).max(), np.abs(yp).max(), np.abs(yp).max() < 32768, np.abs(T).max(), 100 * np.mean(np.abs(Tun) > c["t_clamp"]), np.abs((A[:, 3] * c["gain"]) >> 15).max()))
    # (a) after disengage: S ringing +-15360 at 20 Hz then S := 0 (the 0x2A164 route) -- what does the term inject?
    nt = NotchInt(c); lg = LagInt(c); tr = []
    for k in range(1500):
        S = int(15360 * np.sin(2 * np.pi * 20.3 * k * TS)) if k < 500 else 0
        yc, n, y = nt.tick(S); yl = lg.tick(yc); tr.append((n, yl))
    tr = np.array(tr); post = tr[500:]
    k10 = int(np.argmax(np.abs(post[:, 0]) < 0.1 * np.abs(post[:5, 0]).max()))
    pr("  S 20.3 Hz sine 15360 -> 0 at t0: |n| right after t0 %d, falls below 10 %% after %d ms; |y_lag| after t0 %d ; the term (n>>3) at t0 %d counts of y (T %d counts)" % (
        np.abs(post[:5, 0]).max(), k10, np.abs(post[:5, 1]).max(), np.abs(post[:5, 0]).max() >> 3, (np.abs(post[:5, 0]).max() >> 3) * c["gain"] >> 15))
    # (d) 7.3 / 3.9 Hz: the term's size relative to the main path
    for f0 in (3.9, 7.3, 10.0, 13.5):
        main_ = pev(el289.Hlag[0], f0) / pev(el289.Hlag[1], f0) * pev(el289.N[0], f0) / pev(el289.N[1], f0)
        term = -pev(mn, f0) / pev(md, f0) / 8
        pr("  %4.1f Hz: main path Hlag*N = %.4f %+.1f deg ; term -(1-N)/8 = %.4f %+.1f deg ; ratio %.3f -> forward path changes by %.1f %% in |.| and %+.1f deg" % (
            f0, abs(main_), np.degrees(np.angle(main_)), abs(term), np.degrees(np.angle(term)), abs(term / main_),
            100 * (abs(main_ + term) / abs(main_) - 1), np.degrees(np.angle((main_ + term) / main_))))
    pr("  (b) ramp: the hook at 0x2A1B0 precedes `mul r14,r9,r0` at 0x2A1E6 (r14 = gp-0x69b0 engagement ramp) -> y' = y - n>>3 IS multiplied by the ramp. EVIDENCE (listing).")
    pr("  (a') PSW: 0x2A1AE `cmp 0x1,r16` sets the flags that `bne 0x2A1E6` at 0x2A1B4 consumes; the displaced `st.w` at 0x2A1B0 sits BETWEEN them.")
    pr("       A cave at 0x2A1B0 that does sub/sar/mul destroys those flags -> it MUST re-issue `cmp 0x1,r16` (r16 is live, unchanged) before `jr 0x2A1B4`.")
    pr("       r16 = cal byte 0xC64A3 = %d on this image, so the bne is NOT taken; a clobbered Z flag would send disengaged ticks past the +-%d deadband. EVIDENCE (listing + byte)." % (c["r16flag"], c["deadband"]))
    with open(os.path.join(SCR, "adv_v290_physics.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/adv_v290_physics.txt")


if __name__ == "__main__":
    main()
