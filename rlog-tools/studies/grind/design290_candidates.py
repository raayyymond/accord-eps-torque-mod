# -*- coding: utf-8 -*-
"""studies/grind/design290_candidates.py -- the V290 design study: what damping the 20 Hz plant mode NEEDS, and which
in-loop candidate can supply it.   Subagent design290, 2026-09-09.  Analysis only: builds nothing, flashes nothing.

Re-uses the loop model of loopshape20_loop_model.py (electronics byte-read from the V282 / V289 images, the four plant
fits in _scratch/loopshape20_plants.json) and extends it with the two V290 classes:

  (ii-a) OVER-NOTCH  y' = y - g*n = S * ((1+g) N(z) - g)      -- the V289 cave's own removed component n = S - y, fed back
         with gain g: at the notch centre the loop's action is INVERTED (x -g) instead of removed (x 0); unity and
         zero-phase below ~13 Hz and above ~30 Hz.  Zero new RAM (n is already in r9 at 0xC4C3A).
  (ii-b) RATE BAND-PASS  T_add = k * BP(z; fc, Q) * x, x = gp-0x6a56 (raw rate counts, the fb filter's own input),
         injected either PRE-LAG (added to S at 0x2A174, pays the output lag's -76 deg at 20 Hz) or POST-LAG (added to the
         lag output y before the ramp multiply at 0x2A1E6; needs a second hook and two new state words).
  plus the reference rows: V282 as-built, V289 as-built (integer notch + fb pole 875/2301), notch alone.

Scores (per plant fit): closed-loop pole f/zeta (S-peak width) and zeta_TD (impulse-response decay 12-30 Hz), Ms, vector
margin, |L| and angle at 3.9 / 7.3 / 20.3 Hz, the 7 Hz strong-turn gate |Ls R73 + Lr| (ratio convention of the record),
|dL| below 5 Hz, linear capped-step peak rate / accel / t90 vs as-built (the B3 criterion), HF noise gain rate -> T over
30-500 Hz relative to as-built, Nyquist stability; and an integer closed-loop mirror (V850 sar floors, clamps, the notch
as the golden model's lkas_sum_notch arithmetic) for the capped-frame step (B3, mirror-exact).

Run:  python design290_candidates.py     (writes _scratch/design290_candidates.txt beside it)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import loopshape20_loop_model as LM            # noqa: E402
LG = LM.LG

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = LM.TS, LM.FS, LM.CPD
zf = LM.zf
OUT = []
IMG282 = LM.IMG
IMG289 = LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
F_MODE = 20.3
# V289 notch integers, as decoded from the image by adversaries A / B / lerps (movea immediates 0xC4C0E / 0xC4C26 / 0xC4C3C)
NC289 = dict(b0=16048, b1=-31842, a1=-31842, a2=15712, a0=16384)


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def notch_int_H(nc, f):
    z = zf(f)
    return (nc["b0"] + nc["b1"] / z + nc["b0"] / z ** 2) / (nc["a0"] + nc["a1"] / z + nc["a2"] / z ** 2)


def bp_coefs(fc, Q):
    """RBJ constant-0-dB-peak band-pass at fc, Q, fs 1 kHz: b = [alpha, 0, -alpha]/a0, a = [1, -2cos, 1-alpha]/a0."""
    w0 = 2 * np.pi * fc / FS
    alpha = np.sin(w0) / (2 * Q)
    a0 = 1 + alpha
    return np.array([alpha, 0.0, -alpha]) / a0, np.array([1.0, -2 * np.cos(w0) / a0, (1 - alpha) / a0])


def bp_z(f, fc, Q):
    b, a = bp_coefs(fc, Q)
    z = zf(f)
    return (b[0] + b[1] / z + b[2] / z ** 2) / (a[0] + a[1] / z + a[2] / z ** 2)


def bp_q14(fc, Q):
    b, a = bp_coefs(fc, Q)
    return [int(round(v * 16384)) for v in b], [int(round(v * 16384)) for v in a]


def bp_int_H(B, A, f):
    z = zf(f)
    return (B[0] + B[1] / z + B[2] / z ** 2) / (A[0] + A[1] / z + A[2] / z ** 2)


class Elec290(LM.Elec):
    """V282 electronics + the V289 notch (integer) + the two V290 classes."""

    def __init__(self, c):
        super().__init__(c)
        self.nc = None          # integer notch on S (V289) -- dict or None
        self.over_g = 0.0       # (ii-a): y' = y - g n
        self.bp = None          # (ii-b): dict(fc, Q, k, where='pre'|'post', sign=+1/-1, ints=(B, A) or None)
        self.gd = 0.0           # (ii-d): pre-lag  S' = y - gd * (n - n_prev)  (derivative of the notched-out component)

    # the sum-node filter H_sum(z): S -> what the lag receives
    def Hsum(self, f):
        if self.nc is None:
            return np.ones_like(np.asarray(f, float), dtype=complex)
        N = notch_int_H(self.nc, f)
        if self.over_g:
            return (1 + self.over_g) * N - self.over_g
        if self.gd:
            return N - self.gd * (1 - 1 / zf(f)) * (1 - N)
        return N

    def bpH(self, f):
        """the added term in S-count units per raw rate count; bp['kT'] is its peak gain in T counts per rate count."""
        if self.bp is None or self.bp["where"] == "recentre":
            return 0.0
        kS = self.bp["kT"] * 32768.0 / self.gain
        if self.bp["where"] == "npost":          # -g * n, n = (1 - N) * S, injected after the lag
            N = notch_int_H(self.nc, f)
            return -self.bp["g"] * (1 - N) * self.F(f) * self.C(f) * self.fade
        if self.bp.get("ints"):
            B, A = self.bp["ints"]; H = bp_int_H(B, A, f); H20 = bp_int_H(B, A, F_MODE)
        else:
            H = bp_z(f, self.bp["fc"], self.bp["Q"]); H20 = bp_z(F_MODE, self.bp["fc"], self.bp["Q"])
        if self.bp.get("diff"):
            H = H * (1 - 1 / zf(f)); H20 = H20 * (1 - 1 / zf(F_MODE))
        kS = kS / abs(H20)                       # normalise: |added term at the T node| = kT at 20.3 Hz
        if self.bp["where"] == "pre":
            kS = kS / abs(self.Hlag(F_MODE))
        return self.bp["sign"] * kS * H

    def fwd(self, f):
        """T per count of E (setpoint side), incl. one tick latency; the rate-fed term does not appear here."""
        Hs = self.Hsum(f)
        if self.bp is not None and self.bp.get("where") == "recentre":
            N = LM.notch_z(f, self.bp["fc_model"], 3.0); Hs = (1 + self.over_g) * N - self.over_g
        return self.C(f) * self.fade * Hs * self.Hlag(f) * (self.gain / 32768.0) / zf(f)

    def ret(self, f):
        """T per raw rate count x (negative-feedback convention of the record)."""
        base = self.F(f) * self.C(f) * self.fade * self.Hsum(f)          # S counts per x count, at the sum node
        if self.bp is not None and self.bp.get("where") == "recentre":    # re-centred float notch (model-mode variant)
            N = LM.notch_z(f, self.bp["fc_model"], 3.0)
            base = self.F(f) * self.C(f) * self.fade * ((1 + self.over_g) * N - self.over_g)
        tail = self.Hlag(f) * (self.gain / 32768.0) / zf(f)
        R = base * tail
        if self.bp is not None and self.bp["where"] != "recentre":
            if self.bp["where"] == "pre":
                R = R + self.bpH(f) * tail
            else:
                R = R + self.bpH(f) * (self.gain / 32768.0) / zf(f)
        return R


def Lof(el, pl, f):
    return el.ret(f) * CPD * pl.Gd(f)


# ---------------------------------------------------------------------------------------------------------------------
# scoring (mirrors loopshape20's columns; recomputed here so the extended ret()/fwd() are used everywhere)
# ---------------------------------------------------------------------------------------------------------------------
FGRID = np.arange(0.5, 120.0, 0.02)


def margins(el, pl, lo=3.0, hi=80.0):
    f = FGRID[(FGRID >= lo) & (FGRID <= hi)]
    L = Lof(el, pl, f)
    S = 1 / np.abs(1 + L)
    k = int(np.argmax(S))
    half = S[k] / np.sqrt(2); i0 = k; i1 = k
    while i0 > 0 and S[i0] > half:
        i0 -= 1
    while i1 < len(S) - 1 and S[i1] > half:
        i1 += 1
    zcl = (f[i1] - f[i0]) / (2 * f[k]) if S[k] > 1.5 else np.nan
    return dict(Ms=float(S[k]), fMs=float(f[k]), z_cl=float(zcl), vm=float(np.min(np.abs(1 + L))), fvm=float(f[int(np.argmin(np.abs(1 + L)))]))


def unstable(el, pl):
    f = np.concatenate([np.arange(0.02, 60.0, 0.01), np.arange(60.0, 500.0, 0.25)])
    L = Lof(el, pl, f)
    ph = np.unwrap(np.angle(1 + L))
    return int(round(2 * (ph[-1] - ph[0]) / (2 * np.pi))) != 0


def cl_pole_td(el, pl, n=6000):
    N = 2 ** 16
    f = np.fft.rfftfreq(N, TS); f[0] = 1e-6
    L = Lof(el, pl, f)
    Tcl = (el.fwd(f) * CPD * pl.Gd(f)) / (1 + L)
    h = np.fft.irfft(Tcl, n=N)[:n]
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


def step_response(el, pl, n=1500):
    N = 2 ** 15
    f = np.fft.rfftfreq(N, TS); f[0] = 1e-6
    L = Lof(el, pl, f)
    Tcl = (el.fwd(f) * CPD * pl.Gd(f)) / (1 + L)
    h = np.fft.irfft(Tcl, n=N)[:n]
    y = np.cumsum(h) * 1056.0 / CPD
    acc = np.gradient(y, TS)
    yss = y[-200:].mean()
    t90 = TS * int(np.argmax(y >= 0.9 * yss)) if yss > 0 else np.nan
    return dict(peak_rate=float(y.max()), ss=float(yss), peak_acc=float(acc.max()), t90=t90)


def noise_T(el, lo=30.0, hi=499.0):
    """rms |rate -> T| over lo..hi: the HF noise the motor sees per unit white rate noise (relative units)."""
    f = np.arange(lo, hi, 0.5)
    return float(np.sqrt(np.mean(np.abs(el.ret(f)) ** 2)))


def score(el, el0, pl):
    m = margins(el, pl); st = step_response(el, pl); st0 = step_response(el0, pl)
    ftd, ztd = cl_pole_td(el, pl)
    R73 = (el.ret(7.3) / el0.ret(7.3))
    gate = abs(LM.LS73 * R73 + LM.LR73)
    flo = np.arange(0.5, 5.01, 0.25)
    dlo = float(np.max(np.abs(Lof(el, pl, flo) / Lof(el0, pl, flo) - 1)))
    d39 = float(np.degrees(np.angle(Lof(el, pl, 3.9) / Lof(el0, pl, 3.9))))
    L20 = Lof(el, pl, F_MODE); L39 = Lof(el, pl, 3.9); L73 = Lof(el, pl, 7.3)
    return dict(m=m, st=st, st0=st0, ftd=ftd, ztd=ztd, R73=R73, gate=gate, dlo=dlo, d39=d39, L20=L20, L39=L39, L73=L73,
                noise=noise_T(el) / noise_T(el0), uns=unstable(el, pl))


HDR = ("  %-44s | %5s %6s %6s | %5s %5s | %4s %5s %6s | %6s %5s | %5s %5s %4s | %5s | %s" % (
    "candidate", "fS", "zS", "zTD", "Ms", "vm", "dL<5", "d3.9", "gate73", "|L20|", "ang20", "pkR", "pkA", "t90", "noise", "stab"))


def row(name, sc):
    m, st, st0 = sc["m"], sc["st"], sc["st0"]
    return "  %-44s | %5.1f %6.3f %6.3f | %5.2f %5.2f | %3.0f%% %+5.1f %6.3f | %6.2f %+5.0f | %5.2f %5.2f %4.0f | %5.2f | %s" % (
        name[:44], m["fMs"], m["z_cl"], sc["ztd"], m["Ms"], m["vm"], 100 * sc["dlo"], sc["d39"], sc["gate"],
        abs(sc["L20"]), np.degrees(np.angle(sc["L20"])), st["peak_rate"] / st0["peak_rate"], st["peak_acc"] / st0["peak_acc"],
        1000 * st["t90"], sc["noise"], "UNSTABLE" if sc["uns"] else "ok")


# ---------------------------------------------------------------------------------------------------------------------
# integer closed-loop mirror (the record's Controller, extended with the over-notch; V850 sar floors; 32-bit wraps ignored
# because every term is inside the adversary-A bounds for |S| <= 15360)
# ---------------------------------------------------------------------------------------------------------------------
def sar(v, k):
    return v >> k


def clampi(v, lim):
    return max(-lim, min(lim, v))


class NotchInt:
    """lkas_sum_notch arithmetic (golden model SECTION 5C) + optional over-notch g (Q8: y' = y - (g8*n >> 8))."""

    def __init__(self, nc, g8=0):
        self.nc, self.g8 = nc, g8
        self.s1 = 0; self.s2 = 0; self.e = 0; self.n = 0; self.y = 0

    def tick(self, x, clamp):
        nc = self.nc
        acc = nc["b0"] * x + self.s1 + self.e
        y = sar(acc, 14); self.e = acc & 0x3FFF
        s2n = nc["b0"] * x - nc["a2"] * y
        n = x - y
        self.s1 = nc["b1"] * n + self.s2; self.s2 = s2n
        self.n, self.y = n, y
        out = y - sar(self.g8 * n, 8) if self.g8 else y
        return clampi(out, clamp)


class NotchIntD(NotchInt):
    """(ii-d): the V289 notch plus  out = y - ((n - n_prev) << sh), pre-clamp; n_prev one halfword (stored n >> 1 in the build)."""

    def __init__(self, nc, sh):
        super().__init__(nc, 0); self.sh = sh; self.n_prev = 0

    def tick(self, x, clamp):
        nc = self.nc
        acc = nc["b0"] * x + self.s1 + self.e
        y = sar(acc, 14); self.e = acc & 0x3FFF
        s2n = nc["b0"] * x - nc["a2"] * y
        n = x - y
        self.s1 = nc["b1"] * n + self.s2; self.s2 = s2n
        out = y - ((n - self.n_prev) << self.sh)
        self.n_prev = n; self.n, self.y = n, y
        return clampi(out, clamp)


class BPInt:
    """Q14 TDF-II band-pass on the raw rate x with first-order error feedback (remainder word, as V289's notch), output
    sign * (k8 * y >> 8) in S counts.  Without the error feedback the sar floor biases y by ~ -a0/(2 A(1)) counts at DC."""

    def __init__(self, B, A, k8, sign):
        self.B, self.A, self.k8, self.sign = B, A, k8, sign
        self.s1 = 0; self.s2 = 0; self.e = 0

    def tick(self, x):
        B, A = self.B, self.A
        acc = B[0] * x + self.s1 + self.e
        y = sar(acc, 14); self.e = acc & 0x3FFF
        self.s1 = B[1] * x - A[1] * y + self.s2
        self.s2 = B[2] * x - A[2] * y
        return self.sign * sar(self.k8 * y, 8)


class Controller:
    def __init__(self, c, notch=None, bp=None, where="pre", npost_g8=0):
        self.c = c; self.s_fb = 0; self.s_lag = 0; self.E_prev = None
        self.notch, self.bp, self.where, self.npost_g8 = notch, bp, where, npost_g8
        self.kp = int(c["kp_Y"][0]); self.kd = int(c["kd_Y"][0])

    def tick(self, sp, x):
        c = self.c
        x = clampi(int(x), 12000)
        s_new = sar(int(c["fb_a"]) * self.s_fb, 10) + sar(int(c["fb_b"]) * x, 10)
        fb = clampi(self.s_fb + s_new, int(c["fb_clamp"])); self.s_fb = s_new
        E = 32 * int(sp) - fb
        P = clampi(sar(E * self.kp, 8), int(c["p_clamp"]))
        dE = 0 if self.E_prev is None else (E - self.E_prev)
        self.E_prev = E
        D = clampi(sar(dE * self.kd, 3), int(c["d_clamp"]))
        S = clampi(sar(254 * (P + D), 8), int(c["sum_clamp"]))
        if self.notch is not None:
            S = self.notch.tick(S, int(c["sum_clamp"]))
        add = self.bp.tick(x) if self.bp is not None else 0
        if self.bp is not None and self.where == "pre":
            S = clampi(S + add, int(c["sum_clamp"]))
        s_new2 = sar(int(c["lag_a"]) * self.s_lag, 10) + sar(int(c["lag_b"]) * S, 10)
        y = sar(self.s_lag + s_new2, 5); self.s_lag = s_new2
        if self.bp is not None and self.where == "post":
            y = clampi(y + add, int(c["sum_clamp"]))
        if self.npost_g8 and self.notch is not None:
            y = clampi(y - sar(self.npost_g8 * self.notch.n, 8), int(c["sum_clamp"]))
        y = sar(y * 0x8000, 15)
        y = ((y + 0x8000) & 0xFFFF) - 0x8000
        T = clampi(sar(y * int(c["gain"]), 15), int(c["t_clamp"]))
        return T


def plant_discrete(pl):
    w1 = 2 * np.pi * pl.f1
    num, den = [pl.g0 * w1], [1.0, w1]
    if pl.fp:
        wp = 2 * np.pi * pl.fp
        mnum, mden = [wp ** 2], [1.0, 2 * pl.zp * wp, wp ** 2]
        if pl.kappa is not None:
            mnum = np.polyadd((1 - pl.kappa) * np.array(mden), pl.kappa * np.array(mnum))
        num = np.polymul(num, mnum); den = np.polymul(den, mden)
    bz, az, _ = signal.cont2discrete((num, den), TS, method="zoh")
    nd = int(round(pl.tau / TS))
    return np.atleast_1d(np.squeeze(bz)), np.atleast_1d(np.squeeze(az)), nd


def mirror_step(c, pl, sp_step, notch=None, bp=None, where="pre", n=1500, npost_g8=0):
    bz, az, nd = plant_discrete(pl)
    ctl = Controller(c, notch, bp, where, npost_g8)
    Th = np.zeros(n + nd + 8); rate = np.zeros(n); T = np.zeros(n)
    zi = signal.lfilter_zi(bz, az) * 0.0
    x = 0
    for k in range(n):
        Tk = ctl.tick(sp_step if k >= 5 else 0, x)
        T[k] = Tk; Th[k + nd] = Tk
        yk, zi = signal.lfilter(bz, az, [Th[k]], zi=zi)
        rate[k] = yk[0]
        x = int(round(CPD * rate[k]))
    acc = np.gradient(rate, TS)
    # ring decay of the 12-30 Hz component after the step
    sos = signal.butter(4, (12.0, 30.0), btype="bandpass", fs=FS, output="sos")
    yb = signal.sosfilt(sos, rate); env = np.abs(signal.hilbert(yb))
    k0 = int(np.argmax(env[:400])); seg = slice(k0 + 40, k0 + 400)
    ok = env[seg] > 1e-3 * env[k0]
    zr = np.nan
    if ok.sum() > 50:
        t = np.arange(n) * TS
        sl = np.polyfit(t[seg][ok], np.log(env[seg][ok]), 1)[0]
        zr = -sl / (2 * np.pi * 20.3)
    return dict(peak_rate=float(np.max(np.abs(rate))), peak_acc=float(np.max(np.abs(acc))), ss=float(np.mean(rate[-200:])),
                peak_T=float(np.max(np.abs(T))), ring_z=float(zr), rate=rate)


# ---------------------------------------------------------------------------------------------------------------------
def main():
    c282 = LG.read_build(IMG282); c289 = LG.read_build(IMG289)
    pr("design290_candidates -- images: V282 %s ; V289 %s" % (os.path.basename(IMG282)[:40], os.path.basename(IMG289)[:40]))
    pr("cells V282: Kp %s Kd %s fb %d/%d lag %d/%d gain %d clamps D %d sum %d T %d" % (
        c282["kp_Y"].astype(int).tolist(), c282["kd_Y"].astype(int).tolist(), c282["fb_a"], c282["fb_b"], c282["lag_a"], c282["lag_b"], c282["gain"], c282["d_clamp"], c282["sum_clamp"], c282["t_clamp"]))
    pr("cells V289: fb %d/%d (the only cal difference), notch ints %s" % (c289["fb_a"], c289["fb_b"], NC289))
    plants = {k: LM.Plant(d["g0"], d["tau"], d["f1"], d["fp"], d["zp"], d["label"], d.get("kappa")) for k, d in json.load(open(os.path.join(SCR, "loopshape20_plants.json"))).items()}

    # =================================================================================================================
    pr("\n" + "=" * 150)
    pr("1. THE PHYSICS BUDGET -- what zeta buys, for a 20.3 Hz mode (period 49.3 ms)")
    pr("=" * 150)
    pr("  amplitude after n cycles = exp(-2 pi zeta n); e-fold cycles = 1/(2 pi zeta); 10 %% cycles = ln10/(2 pi zeta);")
    pr("  steady amplitude under continuous on-resonance excitation ~ 1/(2 zeta) (relative to the census median 0.027)")
    pr("  %-8s %-10s %-10s %-12s %-12s %-14s %s" % ("zeta", "e-fold cyc", "e-fold ms", "to 10% cyc", "to 10% ms", "driven amp rel", "where it sits"))
    notes = {0.013: "V288 marks p50 (hands-off, driven)", 0.019: "census fit, Kp 248 (model)", 0.027: "V282 free-decay median (wire)",
             0.036: "Kp 240-320 bin (wire)", 0.05: "plant alone, zeta_p (loop neutral) = class (i) CEILING", 0.08: "",
             0.10: "ring < 0.2 s", 0.16: "e-fold in ONE cycle", 0.25: "", 0.37: "10 % in one cycle"}
    for zt in (0.013, 0.019, 0.027, 0.036, 0.05, 0.08, 0.10, 0.16, 0.25, 0.37):
        ef = 1 / (2 * np.pi * zt); tf = np.log(10) / (2 * np.pi * zt)
        pr("  %-8.3f %-10.1f %-10.0f %-12.1f %-12.0f %-14.2f %s" % (zt, ef, ef * 1000 / F_MODE, tf, tf * 1000 / F_MODE, 0.027 / zt, notes.get(zt, "")))

    # =================================================================================================================
    pr("\n" + "=" * 150)
    pr("2. WHICH PHASE ADDS DAMPING -- an idealised narrow rate-feedback term dR = k e^{j phi} BP(20.3 Hz, Q3) added to the")
    pr("   return ratio (T per raw rate count), on the census plant (iv) and fit (iii); k = 1.0 T count per raw rate count")
    pr("   (as-built |R(20.3)| = 1.74 V282 / see below V289). zeta from the sensitivity-peak width; a larger zeta = more damping.")
    pr("=" * 150)
    el282 = Elec290(c282); el289 = Elec290(c289); el289.nc = NC289
    for pk in ("weak-mode", "smooth+mode"):
        d = plants[pk]; best = None
        for sc_ in np.arange(0.85, 1.005, 0.01):
            plw = LM.Plant(d.g0, d.tau, d.f1, d.fp * sc_, d.zp, "%s fp->%.2f WIRE-CENTRED" % (pk, d.fp * sc_), d.kappa)
            m = margins(el282, plw)
            if best is None or abs(m["fMs"] - 20.05) < abs(best[0] - 20.05):
                best = (m["fMs"], plw, sc_)
        plants[pk + "-w"] = best[1]
        pr("  wire-centred %s: fp x%.2f -> as-built S-peak %.2f Hz (was %.2f)" % (pk, best[2], best[0], margins(el282, d)["fMs"]))
    for nm, el in (("V282", el282), ("V289", el289)):
        R = el.ret(F_MODE)
        pr("  %s return ratio at %.1f Hz: |R| %.3f T/count, angle %+.1f deg ; sum-node F*C*fade = %.2f S-counts per rate count, angle %+.1f deg" % (
            nm, F_MODE, abs(R), np.degrees(np.angle(R)), abs(el.F(F_MODE) * el.C(F_MODE) * el.fade), np.degrees(np.angle(el.F(F_MODE) * el.C(F_MODE) * el.fade))))

    class Ideal(Elec290):
        def __init__(self, c, base_nc, k, phi):
            super().__init__(c); self.nc = base_nc; self.k, self.phi = k, phi

        def ret(self, f):
            return super().ret(f) + self.k * np.exp(1j * np.radians(self.phi)) * bp_z(f, F_MODE, 3.0)

    for pk in ("weak-mode-w", "smooth+mode-w", "weak-mode", "smooth+mode"):
        pl = plants[pk]
        for basenm, cc, bnc, kk in (("V282 base", c282, None, 1.0), ("V289 base", c289, NC289, 0.5), ("V289 base", c289, NC289, 1.0), ("V289 base", c289, NC289, 2.0)):
            b = Elec290(cc); b.nc = bnc
            m0 = margins(b, pl)
            line = "  %-12s %-10s k %.1f as-built zeta %.3f Ms %.2f | phi:" % (pk, basenm, kk, m0["z_cl"], m0["Ms"])
            best = (None, -1)
            for phi in range(0, 360, 30):
                e = Ideal(cc, bnc, kk, phi)
                m = margins(e, pl)
                u = unstable(e, pl)
                z = m["z_cl"] if not u else -1
                line += " %3d:%s" % (phi, ("%.3f" % m["z_cl"]) if not u else "UNST")
                if z > best[1]:
                    best = (phi, z)
            pr(line)
            pr("      -> best phi %s deg (zeta %.3f); the damping quadrant is centred there. Plant angle at 20.3 Hz: %+.0f deg" % (best[0], best[1], np.degrees(np.angle(pl.Gs(F_MODE)))))

    # =================================================================================================================
    pr("\n" + "=" * 150)
    pr("3. CANDIDATES on the mode plants (census fit iv first, then fit iii) and, for the revert branch, the smooth fit (i)")
    pr("   columns: fS/zS = S-peak pole; zTD = 12-30 Hz impulse decay; gate73 <= 1.01 passes; pkR/pkA/t90 = linear capped step vs")
    pr("   as-built V282; noise = rms rate->T 30-500 Hz vs V282; ang20 = loop phase at 20.3 Hz")
    pr("=" * 150)

    def mk(cc, nc=None, g=0.0, bp=None, label="", gd=0.0):
        e = Elec290(cc); e.nc = nc; e.over_g = g; e.bp = bp; e.label = label; e.gd = gd
        return e

    cands = []
    cands.append(("as-built V282", mk(c282)))
    cands.append(("V289 as-built (int notch + fb 875/2301)", mk(c289, NC289)))
    cands.append(("notch alone (V282 cells)", mk(c282, NC289)))
    for g in (0.5, 1.0):
        cands.append(("(ii-a) V289 + over-notch g=%.1f" % g, mk(c289, NC289, g)))
    cands.append(("(ii-a') V289 recentred over-notch g=1.0", mk(c289, NC289, 1.0, dict(where="recentre", kT=0, g=1.0, fc_model=20.05))))
    for g in (0.05, 0.1, 0.125, 0.15, 0.2, 0.25):
        cands.append(("(ii-c) V289 + n POST-lag g=%.3f" % g, mk(c289, NC289, 0.0, dict(where="npost", kT=0, g=g))))
    cands.append(("(ii-c) V282cells+notch + n POST-lag g=0.125", mk(c282, NC289, 0.0, dict(where="npost", kT=0, g=0.125))))
    for gd in (2.0, 3.0, 4.0, 6.0):
        cands.append(("(ii-d) V289 + pre-lag -%g*(n-n_prev)" % gd, mk(c289, NC289, gd=gd)))
    cands.append(("(ii-d) V289 + pre-lag +4*(n-n_prev) (sign ctl)", mk(c289, NC289, gd=-4.0)))
    cands.append(("(ii-d) V282cells+notch + pre-lag -4*(n-n_prev)", mk(c282, NC289, gd=4.0)))

    def bpc(nm, cc, nc, fc, Q, kT, where, sgn=-1, diff=False):
        cands.append((nm, mk(cc, nc, 0.0, dict(fc=fc, Q=Q, kT=kT, where=where, sign=sgn, g=0, diff=diff))))
    # POST-lag BP on x (second hook after 0x2A1AC), kT = |added T per rate count| at 20.3 Hz
    for fc, Q in ((15.0, 2.0), (17.0, 2.0), (17.0, 3.0), (20.3, 2.0), (20.3, 3.0), (20.3, 4.0), (22.0, 3.0)):
        for kT in (0.5, 0.75, 1.0, 1.5):
            bpc("(ii-b) V289+BP post fc%g Q%g kT%.2f -" % (fc, Q, kT), c289, NC289, fc, Q, kT, "post")
    bpc("(ii-b) V289+BP post fc20.3 Q3 kT1.00 + (sign ctl)", c289, NC289, 20.3, 3.0, 1.0, "post", +1)
    # PRE-lag BP on x (inside the existing 0x2A174 cave, added to r12 before the clamp)
    for fc, Q in ((22.0, 3.0), (24.0, 3.0), (24.0, 4.0), (26.0, 3.0), (26.0, 2.0), (30.0, 2.0)):
        for kT in (0.5, 0.75, 1.0, 1.5):
            bpc("(ii-b) V289+BP pre fc%g Q%g kT%.2f -" % (fc, Q, kT), c289, NC289, fc, Q, kT, "pre")
    bpc("(ii-b) V289+BP pre fc24 Q3 kT1.00 + (sign ctl)", c289, NC289, 24.0, 3.0, 1.0, "pre", +1)
    for fc, Q in ((20.3, 3.0), (18.0, 3.0)):
        bpc("(ii-b) V289+BPD pre fc%g Q%g kT1.00 -" % (fc, Q), c289, NC289, fc, Q, 1.0, "pre", -1, True)
    # without the notch / without the fb pole
    bpc("(ii-b) V282 + BP post fc20.3 Q3 kT1.00 - (no notch)", c282, None, 20.3, 3.0, 1.0, "post")
    bpc("(ii-b) V282 + BP pre fc24 Q3 kT1.00 - (no notch)", c282, None, 24.0, 3.0, 1.0, "pre")
    bpc("(ii-b) fbpole25 + BP post fc20.3 Q3 kT1.00 - (no notch)", c289, None, 20.3, 3.0, 1.0, "post")
    bpc("(ii-b) V282cells+notch + BP post fc20.3 Q3 kT1.00 -", c282, NC289, 20.3, 3.0, 1.0, "post")
    bpc("(ii-b) V282cells+notch + BP pre fc24 Q3 kT1.00 -", c282, NC289, 24.0, 3.0, 1.0, "pre")
    el0 = mk(c282)
    keep = {}
    for pk in ("weak-mode", "smooth+mode"):
        d = plants[pk]; best = None
        for sc_ in np.arange(0.85, 1.005, 0.01):
            plw = LM.Plant(d.g0, d.tau, d.f1, d.fp * sc_, d.zp, "%s fp->%.2f WIRE-CENTRED" % (pk, d.fp * sc_), d.kappa)
            m = margins(el0, plw)
            if best is None or abs(m["fMs"] - 20.05) < abs(best[0] - 20.05):
                best = (m["fMs"], plw, sc_)
        plants[pk + "-w"] = best[1]
        pr("  wire-centred %s: fp x%.2f -> as-built S-peak %.2f Hz (was %.2f)" % (pk, best[2], best[0], margins(el0, d)["fMs"]))
    for pk in ("weak-mode-w", "smooth+mode-w", "weak-mode", "smooth+mode", "smooth"):
        pl = plants[pk]
        pr("\n  --- plant: %s ---" % pl.label)
        pr(HDR)
        fcm = margins(el0, pl)["fMs"]
        for name, el in cands:
            if el.bp is not None and el.bp.get("where") == "recentre":
                el.bp["fc_model"] = fcm
            sc = score(el, el0, pl)
            keep.setdefault(name, {})[pk] = sc
            pr(row(name, sc))

    # =================================================================================================================
    pr("\n" + "=" * 150)
    pr("4. THE SHORT LIST -- robust on BOTH wire-centred mode fits, gate73 <= 1.01, |dL|<5 <= 5 %, not unstable on either mode fit")
    pr("=" * 150)
    short = []
    for name, d in keep.items():
        a, b = d["weak-mode-w"], d["smooth+mode-w"]
        okk = (not a["uns"]) and (not b["uns"]) and a["gate"] <= 1.01 and a["dlo"] <= 0.05
        zmin = min(a["m"]["z_cl"] if np.isfinite(a["m"]["z_cl"]) else 9, b["m"]["z_cl"] if np.isfinite(b["m"]["z_cl"]) else 9)
        if okk:
            short.append((zmin, name, a, b))
    short.sort(key=lambda t: -t[0])
    pr("  %-44s | %7s %7s | %6s %6s | %6s | %5s %5s | %5s | %s" % ("candidate", "z(iv)", "z(iii)", "Ms(iv)", "Ms(iii)", "gate73", "pkR", "pkA", "noise", "smooth-fit"))
    for zmin, name, a, b in short:
        pr("  %-44s | %7.3f %7.3f | %6.2f %6.2f | %6.3f | %5.2f %5.2f | %5.2f | %s" % (
            name[:44], a["m"]["z_cl"], b["m"]["z_cl"], a["m"]["Ms"], b["m"]["Ms"], a["gate"], a["st"]["peak_rate"] / a["st0"]["peak_rate"],
            a["st"]["peak_acc"] / a["st0"]["peak_acc"], a["noise"], "UNSTABLE" if keep[name]["smooth"]["uns"] else "stable"))

    # =================================================================================================================
    pr("\n" + "=" * 150)
    pr("5. OVER-NOTCH transfer H = (1+g) N - g, from the V289 integer coefficients, and the b5 (sign n) phase vs the rate")
    pr("=" * 150)
    fl = (3.9, 7.3, 10.0, 13.5, 15.0, 17.0, 18.0, 19.0, 20.036, 21.0, 22.0, 23.0, 25.0, 30.0, 40.0)
    pr("  %-6s | %-16s | %-16s | %-16s | %-16s" % ("f Hz", "N (V289)", "g=1", "g=2", "g=3"))
    for f in fl:
        N = notch_int_H(NC289, f)
        cells = ["%.3f %+6.1f" % (abs(N), np.degrees(np.angle(N)))]
        for g in (1.0, 2.0, 3.0):
            H = (1 + g) * N - g
            cells.append("%.3f %+6.1f" % (abs(H), np.degrees(np.angle(H))))
        pr("  %-6.2f | %-16s | %-16s | %-16s | %-16s" % (f, *cells))
    # n relative to the rate operand x: n = (1-N) * S ; S = F*C*fade * x on the feedback path (setpoint side ignored)
    for nm, el in (("V282 cells", el282), ("V289 cells", el289)):
        for f in (18.0, 20.036, 22.0):
            N = notch_int_H(NC289, f)
            Hn = (1 - N) * el.F(f) * el.C(f) * el.fade
            pr("  %s: n per raw rate count at %.2f Hz: |.| %.2f, angle %+.1f deg  (x = -wire rate; sign(n) vs sign(x) at the line = this angle)" % (nm, f, abs(Hn), np.degrees(np.angle(Hn))))

    # =================================================================================================================
    pr("\n" + "=" * 150)
    pr("6. INTEGER MIRROR -- capped-frame step (33 sp counts) and full scale (1032), census plant; ring zeta of the 12-30 Hz component")
    pr("=" * 150)
    pl = plants["weak-mode-w"]
    pr("  plant: %s" % pl.label)
    rows = [("V282", c282, None, 0, None, "pre"), ("V289", c289, NC289, 0, None, "pre")]
    for g8 in (128, 256, 512, 768):
        rows.append(("V289 + over g8=%d (g=%.2f)" % (g8, g8 / 256), c289, NC289, g8, None, "pre"))
    base33 = None
    for sp in (33, 1032):
        base = None
        pr("  step %d:" % sp)
        for nm, cc, nc, g8, bp, where in rows:
            r = mirror_step(cc, pl, sp, NotchInt(nc, g8) if nc else None, bp, where)
            if base is None:
                base = r
                if sp == 33:
                    base33 = r
            pr("    %-34s peak rate %6.2f (x%.3f)  peak acc %7.1f (x%.3f)  ss %6.2f  peak|T| %5.0f  ring zeta %.3f" % (
                nm, r["peak_rate"], r["peak_rate"] / base["peak_rate"], r["peak_acc"], r["peak_acc"] / base["peak_acc"], r["ss"], r["peak_T"], r["ring_z"]))
    for sh in (1, 2):
        for spv, bb in ((33, base33), (1032, base)):
            r = mirror_step(c289, pl, spv, NotchIntD(NC289, sh))
            pr("  (ii-d) pre-lag -(n-n_prev)<<%d step %4d: peak rate x%.3f  peak acc x%.3f  ss %.2f  ring zeta %.3f  peak|T| %.0f" % (
                sh, spv, r["peak_rate"] / bb["peak_rate"], r["peak_acc"] / bb["peak_acc"], r["ss"], r["ring_z"], r["peak_T"]))
    for g8 in (13, 26, 32, 38, 51):
        r = mirror_step(c289, pl, 33, NotchInt(NC289, 0), None, "pre", npost_g8=g8)
        pr("  (ii-c) n POST-lag g8=%d (g=%.3f) step 33: peak rate x%.3f  peak acc x%.3f  ss %.2f  ring zeta %.3f  peak|T| %.0f" % (
            g8, g8 / 256, r["peak_rate"] / base33["peak_rate"], r["peak_acc"] / base33["peak_acc"], r["ss"], r["ring_z"], r["peak_T"]))
    for fc, Q, kT, sgn, where in ((20.3, 3.0, 1.0, -1, "post"), (20.3, 3.0, 1.0, +1, "post"), (17.0, 3.0, 1.0, -1, "post"), (20.3, 3.0, 1.5, -1, "post"),
                                  (24.0, 3.0, 1.0, -1, "pre"), (24.0, 3.0, 1.0, +1, "pre"), (24.0, 3.0, 1.5, -1, "pre")):
        B, A = bp_q14(fc, Q)
        h20 = abs(bp_int_H(B, A, F_MODE))
        kS = kT * 32768.0 / c289["gain"] / h20
        if where == "pre":
            kS = kS / abs(Elec290(c289).Hlag(F_MODE))
        k8 = int(round(kS * 256))
        pr("  BP %s fc %g Q %g Q14 b=%s a=%s ; |BP(20.3)| %.3f ; kT %.2f -> k8 %d (%.2f S counts per rate count) sign %+d" % (where, fc, Q, B, A, h20, kT, k8, k8 / 256, sgn))
        for spv, bb in ((33, base33), (1032, base)):
            r = mirror_step(c289, pl, spv, NotchInt(NC289, 0), BPInt(B, A, k8, sgn), where)
            pr("    step %4d: peak rate x%.3f  peak acc x%.3f  ss %.2f  ring zeta %.3f  peak|T| %.0f" % (
                spv, r["peak_rate"] / bb["peak_rate"], r["peak_acc"] / bb["peak_acc"], r["ss"], r["ring_z"], r["peak_T"]))
    # DC check of the integer BP: constant x for 3000 ticks must give exactly 0 after settling
    B, A = bp_q14(20.3, 3.0); bpi = BPInt(B, A, 256, -1)
    ys = [bpi.tick(800) for _ in range(3000)]
    pr("  integer BP DC check: x = 800 const, output over the last 500 ticks min %d max %d (must be 0)" % (min(ys[-500:]), max(ys[-500:])))
    pr("")
    pr("=" * 150)
    pr("7. PLANT-INDEPENDENT: return ratio R (T counts per raw rate count) at 3.9 / 7.3 / 13.5 / 17 / 20.3 / 23 / 30 Hz, survivors vs V282 / V289")
    pr("=" * 150)
    surv = [("V282", mk(c282)), ("V289", mk(c289, NC289)), ("(ii-d) gd 3", mk(c289, NC289, gd=3.0)), ("(ii-d) gd 4", mk(c289, NC289, gd=4.0)),
            ("(ii-c) g 1/8", mk(c289, NC289, 0.0, dict(where="npost", kT=0, g=0.125))),
            ("(ii-b) BPD pre 20.3 Q3 kT1", mk(c289, NC289, 0.0, dict(fc=20.3, Q=3.0, kT=1.0, where="pre", sign=-1, g=0, diff=True))),
            ("(ii-b) BP post 20.3 Q3 kT1", mk(c289, NC289, 0.0, dict(fc=20.3, Q=3.0, kT=1.0, where="post", sign=-1, g=0)))]
    FQ = (3.9, 7.3, 13.5, 17.0, 20.3, 23.0, 30.0)
    r282 = surv[0][1]
    for nm, e in surv:
        cells = ["%5.1fHz %.3f/%+4.0f" % (fq, abs(e.ret(fq)), np.degrees(np.angle(e.ret(fq)))) for fq in FQ]
        pr("  %-28s R: " % nm + "  ".join(cells))
    for nm, e in surv[1:]:
        cells = ["%4.1fHz x%.3f %+.1fdeg" % (fq, abs(e.ret(fq) / r282.ret(fq)), np.degrees(np.angle(e.ret(fq) / r282.ret(fq)))) for fq in (3.9, 7.3, 20.3)]
        R73 = e.ret(7.3) / r282.ret(7.3)
        pr("  %-28s vs V282: " % nm + "  ".join(cells) + "  | 7 Hz gate %.3f | fwd(3.9) x%.3f %+.1fdeg | fwd(20.3) x%.3f" % (
            abs(LM.LS73 * R73 + LM.LR73), abs(e.fwd(3.9) / r282.fwd(3.9)), np.degrees(np.angle(e.fwd(3.9) / r282.fwd(3.9))), abs(e.fwd(20.3) / r282.fwd(20.3))))
    open(os.path.join(SCR, "design290_candidates.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote %s" % os.path.join(SCR, "design290_candidates.txt"))


if __name__ == "__main__":
    main()
