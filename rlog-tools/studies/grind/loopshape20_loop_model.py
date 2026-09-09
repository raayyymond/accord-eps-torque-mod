# -*- coding: utf-8 -*-
"""studies/grind/loopshape20_loop_model.py -- the LKAS rate loop at 20 Hz: a model that must reproduce the MEASURED
closed-loop pole (f ~ 20.3 Hz, zeta ~ 0.02-0.05) and the measured frequency pinning against Kp, then every in-loop filter
candidate scored on it.   Subagent loopshape, 2026-09-08.  Analysis only: builds nothing, flashes nothing, sends nothing.

ELECTRONICS (byte-exact z-domain, T = 1 ms; every constant read from the V282 image by lowcmd_loopgain.read_build):
  x   = gp-0x6a56 = -(0x18F wire rate), CPD = 8 raw counts per deg/s
  F(z)   = (b/1024)(1+z^-1)/(1-(a/1024)z^-1)            fb two-sample sum, a/b = 0xC63E8/EA = 923/1560, DC 30.89
  E      = 32*sp - F*x
  C(z)   = Kp/256 + (Kd/8)(1 - z^-1)                     Kp 248 flat, Kd 128 flat (slot 7)
  S      = (254/256)(P + D)                              fade at hands-off
  Hlag(z)= (b2/1024)(1+z^-1)/(1-(a2/1024)z^-1)/32       0xC63EC/EE = 992/507, DC 0.990
  T      = -(-1) * Hlag * S * K6/32768, K6 = 0xC6CD0 = 5346, times the engagement ramp gp-0x69b0 = 1.0 (0x2A1E6)
  one tick of compute latency z^-1 (the operand read this tick acts on the motor next tick).
PLANT G(s) = wheel rate (deg/s) per T count, fitted in TWO families:
  (i)  SMOOTH   : g0 e^{-s tau} / (1 + s/w1)                                   (delay + rigid-body roll-off)
  (ii) RESONANT : g0 e^{-s tau} / (1 + s/w1) * wp^2/(s^2 + 2 zp wp s + wp^2)    (+ a lightly damped mechanical mode)
  discretised with a ZOH at 1 kHz; the loop L(z) = F * C * fade * Hlag * K6/32768 * CPD * z^-1 * Gd(z), NEGATIVE feedback.
  Fit targets (from loopshape20_mode_nature.py and creep20 §1.1 with the 3.9 ms stream offset removed):
  the closed-loop dominant pole f_cl, zeta_cl at Kp 248; the off-line |G| and angle(G) at 10/15/18 Hz; the pole shift
  for Kp 248 -> 696 (measured +0.3..+0.6 Hz on r31-r34).
CANDIDATES (all in-loop, none touches Kp/Kd/the P,D clamps/the DC gain):
  (a) fb pole 16.5 -> 25 / 33 / 50 Hz, DC held (cal-only)           (b) output lag 5 -> 10 / 15 Hz, DC held (cal-only)
  (c) first-order filter on the D term, 40 / 60 / 80 Hz (cave)      (d) notch at f_cl, Q 2/3/4, on the fb operand or on the PID sum (cave)
  (e) lead on the PID sum (zero fz, pole fp)                        (f) combinations with |dL| < 3 % below 5 Hz
  plus, for reference only (the operator rejects them): Kd 96, D clamp 7680 (V287, invisible to the linear loop).
Scores: closed-loop pole (f, zeta); PM/GM/Ms 3-80 Hz; |L| and angle at 3.9 Hz (outer loop), 7.3 Hz (servo arm R(7.3) and the
7 Hz gate |Ls R + Lr| of LOOPSHAPE-LAGPOLE-KD §4, ratio only); |L| change below 5 Hz; HF noise gain rate -> D (rms 30-500 Hz);
linear closed-loop step response of the wheel rate to a capped-frame reference step (peak rate, peak accel, t90); integer mirrors.
Run: python loopshape20_loop_model.py   (writes _scratch/loopshape20_loop_model.txt beside it)
"""
import os
import sys
import struct

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS = 1e-3
FS = 1000.0
CPD = 8.0
IMG = LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
OUT = []
# targets (loopshape20_mode_nature.py, this session) -- overwritten by the CLI if given
F_CL, Z_CL = 20.3, 0.035
DF_KP = 0.5                         # Hz, pole shift for Kp 248 -> 696 (r31-r34 present windows: +0.3..+0.6)
# off-line plant, creep20 §1.1 direct estimator, |G| x1e-3 deg/s per T count, RAW angle; corrected = raw - 360 f tau
TAU_STREAM = 0.0039
G_OFF = {10: (42.9, -35.0), 15: (41.4, -42.0), 18: (54.5, -56.0), 22: (34.8, -65.0)}          # creep20 §1.1 direct (r31-r34)
G_282 = {10.2: (27.0, -79.0), 15.6: (40.8, -63.0), 18.0: (39.0, -73.0), 20.3: (47.6, -72.0), 22.7: (44.6, -69.0), 24.2: (18.8, -41.0)}   # this session, V282 pooled
LS73, LR73 = 0.55 * np.exp(1j * np.radians(96.0)), 1.19 * np.exp(1j * np.radians(-27.0))   # LOOPSHAPE-LAGPOLE-KD §4 pooled split
LTOT73 = (0.944, 0.976, 0.990)
REQUIRE_STABLE_696 = True     # r31-r34 flew Kp up to 696 with a BOUNDED line; set False to allow a friction-limited linear instability


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def zf(f):
    return np.exp(2j * np.pi * np.asarray(f, float) * TS)


# ---------------------------------------------------------------------------------------------------------------------
# electronics
# ---------------------------------------------------------------------------------------------------------------------
class Elec:
    def __init__(self, c):
        self.kp, self.kd = float(c["kp_Y"][0]), float(c["kd_Y"][0])
        self.fa, self.fb = float(c["fb_a"]), float(c["fb_b"])
        self.la, self.lb = float(c["lag_a"]), float(c["lag_b"])
        self.gain = float(c["gain"]); self.fade = 254.0 / 256.0
        self.dfilt = None      # (a,) first-order on D: Hd = (1-a)/(1-a z^-1)   -- implemented as y += (x-y)>>k, a = 1-2^-k
        self.notch_fb = None   # (f0, Q)
        self.notch_out = None
        self.lead_out = None   # (fz, fp)
        self.lead_fb = None
        self.label = "as-built"

    def F(self, f):
        z = zf(f)
        H = (self.fb / 1024.0) * (1 + 1 / z) / (1 - (self.fa / 1024.0) / z)
        if self.notch_fb:
            H = H * notch_z(f, *self.notch_fb)
        if self.lead_fb:
            H = H * lead_z(f, *self.lead_fb)
        return H

    def C(self, f):
        z = zf(f)
        D = (self.kd / 8.0) * (1 - 1 / z)
        if self.dfilt:
            a = self.dfilt[0]
            D = D * (1 - a) / (1 - a / z)
        return self.kp / 256.0 + D

    def Hlag(self, f):
        z = zf(f)
        H = (self.lb / 1024.0) * (1 + 1 / z) / (1 - (self.la / 1024.0) / z) / 32.0
        if self.notch_out:
            H = H * notch_z(f, *self.notch_out)
        if self.lead_out:
            H = H * lead_z(f, *self.lead_out)
        return H

    def fwd(self, f):
        """T counts per count of E (setpoint side), incl. one tick latency."""
        return self.C(f) * self.fade * self.Hlag(f) * (self.gain / 32768.0) / zf(f)

    def ret(self, f):
        """T counts per raw rate count x (feedback side): F * C * fade * Hlag * gain/32768 * z^-1."""
        return self.F(f) * self.fwd(f)


def notch_z(f, f0, Q):
    """RBJ notch at f0 with quality Q, sampled at 1 kHz (bilinear with frequency pre-warp), unity DC and Nyquist."""
    w0 = 2 * np.pi * f0 / FS
    alpha = np.sin(w0) / (2 * Q)
    b0, b1, b2 = 1.0, -2 * np.cos(w0), 1.0
    a0, a1, a2 = 1 + alpha, -2 * np.cos(w0), 1 - alpha
    z = zf(f)
    return (b0 + b1 / z + b2 / z ** 2) / (a0 + a1 / z + a2 / z ** 2)


def notch_coefs(f0, Q):
    w0 = 2 * np.pi * f0 / FS
    alpha = np.sin(w0) / (2 * Q)
    a0 = 1 + alpha
    return np.array([1.0, -2 * np.cos(w0), 1.0]) / a0, np.array([1.0, -2 * np.cos(w0) / a0, (1 - alpha) / a0])


def lead_z(f, fz, fp):
    """(1 + s/wz)/(1 + s/wp) discretised as x + K*(x - LP(x)), LP a one-pole at fp (the cave form): DC 1, HF gain fp/fz."""
    K = fp / fz - 1.0
    a = np.exp(-2 * np.pi * fp / FS)
    z = zf(f)
    LP = (1 - a) / (1 - a / z)
    return 1 + K * (1 - LP)


# ---------------------------------------------------------------------------------------------------------------------
# plant
# ---------------------------------------------------------------------------------------------------------------------
class Plant:
    def __init__(self, g0, tau, f1, fp=None, zp=None, label="", kappa=None):
        self.g0, self.tau, self.f1, self.fp, self.zp, self.label, self.kappa = g0, tau, f1, fp, zp, label, kappa

    def Gs(self, f):
        s = 2j * np.pi * np.asarray(f, float)
        G = self.g0 * np.exp(-s * self.tau) / (1 + s / (2 * np.pi * self.f1))
        if self.fp:
            wp = 2 * np.pi * self.fp
            M = wp ** 2 / (s ** 2 + 2 * self.zp * wp * s + wp ** 2)
            G = G * ((1 + self.kappa * (M - 1)) if self.kappa is not None else M)   # kappa: weakly coupled mode (residue share)
        return G

    def Gd(self, f):
        """ZOH-sampled response at 1 kHz: the ZOH adds sinc magnitude and a half-tick delay; the pure delay is kept continuous."""
        w = 2 * np.pi * np.asarray(f, float)
        zoh = np.where(w == 0, 1.0, (1 - np.exp(-1j * w * TS)) / (1j * w * TS))
        return self.Gs(f) * zoh


def L_of(el, pl, f):
    return el.ret(f) * CPD * pl.Gd(f)


# ---------------------------------------------------------------------------------------------------------------------
# margins and the closed-loop pole (frequency-domain: S = 1/(1+L); pole from the S peak + phase slope)
# ---------------------------------------------------------------------------------------------------------------------
FGRID = np.arange(0.5, 120.0, 0.02)


def margins(el, pl, lo=3.0, hi=80.0):
    f = FGRID[(FGRID >= lo) & (FGRID <= hi)]
    L = L_of(el, pl, f)
    mag, ph = np.abs(L), np.degrees(np.unwrap(np.angle(L)))
    out = dict(pm=None, fc=None, gm=None, f180=None)
    for i in range(len(f) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1] and out["fc"] is None:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i]); out["fc"] = f[i] + t * (f[i + 1] - f[i]); out["pm"] = 180 + ph[i] + t * (ph[i + 1] - ph[i])
    # ALL unity crossings (a resonant plant can give several)
    xs = [f[i] for i in range(len(f) - 1) if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]]
    out["fc_all"] = xs
    for i in range(len(f) - 1):
        if (ph[i] + 180) * (ph[i + 1] + 180) <= 0 and ph[i] != ph[i + 1]:
            t = (-180 - ph[i]) / (ph[i + 1] - ph[i]); out["f180"] = f[i] + t * (f[i + 1] - f[i]); out["gm"] = 1 / (mag[i] + t * (mag[i + 1] - mag[i])); break
    S = 1 / np.abs(1 + L)
    k = int(np.argmax(S)); out["Ms"], out["fMs"] = float(S[k]), float(f[k])
    # closed-loop pole from the sensitivity peak: half-power bandwidth -> zeta = BW/(2 f)
    half = S[k] / np.sqrt(2)
    i0 = k
    while i0 > 0 and S[i0] > half:
        i0 -= 1
    i1 = k
    while i1 < len(S) - 1 and S[i1] > half:
        i1 += 1
    bw = f[i1] - f[i0]
    out["f_cl"], out["z_cl"] = float(f[k]), float(bw / (2 * f[k])) if S[k] > 1.5 else np.nan
    # minimum distance of L to -1 (the vector margin)
    out["vm"] = float(np.min(np.abs(1 + L)))
    return out


def cl_pole_td(el, pl, n=4000):
    """time-domain check: closed-loop impulse response of the rate to a reference kick via inverse FFT of T_cl; fit decay of the
    band-passed 15-26 Hz component -> f, zeta.  Uses the frequency response only (no state-space), so it is exact for the model."""
    N = 2 ** 15
    f = np.fft.rfftfreq(N, TS)
    f[0] = 1e-6
    L = L_of(el, pl, f)
    Tcl = (el.fwd(f) * CPD * pl.Gd(f)) / (1 + L)      # rate per count of 32*sp
    h = np.fft.irfft(Tcl, n=N)[:n]
    t = np.arange(n) * TS
    sos = signal.butter(4, (14.0, 27.0), btype="bandpass", fs=FS, output="sos")
    y = signal.sosfilt(sos, h)
    env = np.abs(signal.hilbert(y))
    k = int(np.argmax(env[:600]))
    seg = slice(k + 50, k + 450)
    ok = env[seg] > 1e-3 * env[k]
    if ok.sum() < 50:
        return np.nan, np.nan
    sl = np.polyfit(t[seg][ok], np.log(env[seg][ok]), 1)[0]
    ph = np.unwrap(np.angle(signal.hilbert(y)))
    fi = np.median(np.gradient(ph[seg]) * FS / (2 * np.pi))
    return float(fi), float(-sl / (2 * np.pi * fi))


def step_response(el, pl, n=1500):
    """linear closed-loop wheel-rate response to a reference step of 32*dsp (capped-frame size, 33 sp counts -> 1056 E counts)."""
    N = 2 ** 15
    f = np.fft.rfftfreq(N, TS); f[0] = 1e-6
    L = L_of(el, pl, f)
    Tcl = (el.fwd(f) * CPD * pl.Gd(f)) / (1 + L)
    h = np.fft.irfft(Tcl, n=N)[:n]
    y = np.cumsum(h) * 1056.0 / CPD          # deg/s per E count... rate = Tcl * E ; E = 1056; Tcl is raw counts per E count -> /CPD -> deg/s
    acc = np.gradient(y, TS)
    yss = y[-200:].mean()
    t90 = TS * int(np.argmax(y >= 0.9 * yss)) if yss > 0 else np.nan
    return dict(peak_rate=float(y.max()), ss=float(yss), overshoot=float(y.max() / yss - 1) if yss else np.nan, peak_acc=float(acc.max()), t90=t90)


def noise_gain(el, lo=30.0, hi=499.0):
    """rms |D-path| from raw rate to the D term over lo-hi (white noise gain into D), relative units."""
    f = np.arange(lo, hi, 0.5)
    z = zf(f)
    D = (el.kd / 8.0) * (1 - 1 / z)
    if el.dfilt:
        a = el.dfilt[0]; D = D * (1 - a) / (1 - a / z)
    H = el.F(f) * D
    return float(np.sqrt(np.mean(np.abs(H) ** 2)))


def phase_budget(el, pl, f0):
    z = zf(f0)
    items = [("fb one-pole (a=%d)" % el.fa, (1 / (1 - (el.fa / 1024.0) / z))), ("fb two-sample sum (1+z^-1)", 1 + 1 / z),
             ("PID C = Kp/256 + Kd/8 (1-z^-1)", el.C(f0)), ("output lag one-pole (a2=%d)" % el.la, 1 / (1 - (el.la / 1024.0) / z)),
             ("output lag (1+z^-1)", 1 + 1 / z), ("compute latency z^-1", 1 / z), ("ZOH half-tick", (1 - np.exp(-2j * np.pi * f0 * TS)) / (2j * np.pi * f0 * TS)),
             ("plant (fit) %s" % pl.label, pl.Gs(f0))]
    if el.notch_fb:
        items.append(("notch on fb", notch_z(f0, *el.notch_fb)))
    if el.notch_out:
        items.append(("notch on PID sum", notch_z(f0, *el.notch_out)))
    if el.lead_out:
        items.append(("lead on PID sum", lead_z(f0, *el.lead_out)))
    if el.lead_fb:
        items.append(("lead on fb", lead_z(f0, *el.lead_fb)))
    if el.dfilt:
        a = el.dfilt[0]; items.append(("D filter", (1 - a) / (1 - a / z)))
    return [(nm, np.degrees(np.angle(v)), abs(v)) for nm, v in items]


# ---------------------------------------------------------------------------------------------------------------------
# plant fit
# ---------------------------------------------------------------------------------------------------------------------
def fit_error(el, pl, kp_hi_el, targets, bump=False, el_mid=None):
    m = margins(el, pl)
    e = 0.0
    if not np.isfinite(m["z_cl"]):
        return 1e9
    e += ((m["f_cl"] - targets["f"]) / 0.5) ** 2 + ((np.log(m["z_cl"]) - np.log(targets["z"])) / 0.5) ** 2
    # off-line plant magnitude/phase (corrected), weight the two low points where the estimator is off the line
    for f0, (mag, phr) in G_OFF.items():
        if f0 >= 18:
            continue
        g = pl.Gs(f0) * 1e3
        phc = phr - 360 * f0 * TAU_STREAM
        e += 0.3 * ((np.log(abs(g)) - np.log(mag)) / 0.4) ** 2 + 0.3 * ((np.degrees(np.angle(g)) - phc) / 20.0) ** 2
    # Kp discriminator, and the loop must stay STABLE at Kp 696 (r31-r34 flew it with a bounded line)
    m2 = margins(kp_hi_el, pl)
    if np.isfinite(m2["f_cl"]):
        e += ((m2["f_cl"] - m["f_cl"] - targets["df"]) / 0.5) ** 2
    else:
        e += 4.0
    if REQUIRE_STABLE_696 and unstable(kp_hi_el, pl):
        e += 25.0
    if bump:
        # off-line |G| bump 18-21 over 10-15 Hz: 1.68 (V282), 1.81 (r31-r34), 1.14 (V288) this session; 1.3 creep20
        r = np.median(np.abs(pl.Gs(np.array([18.0, 19.0, 20.0, 21.0])))) / np.median(np.abs(pl.Gs(np.array([10.0, 12.0, 15.0]))))
        e += ((np.log(r) - np.log(1.6)) / 0.25) ** 2
        # corrected plant phase FLAT ~ -95 deg at 15.6 and 22 Hz (V282 pooled: -85/-93; r31-r34: -78/-92)
        for f0, ph in ((15.6, -85.0), (22.0, -93.0)):
            e += 0.5 * ((np.degrees(np.angle(pl.Gs(f0))) - ph) / 15.0) ** 2
    if el_mid is not None:
        # zeta falls with Kp but stays positive: census 0.036 (Kp 240-320) -> 0.019 (Kp 450-700)
        m3 = margins(el_mid, pl)
        if np.isfinite(m3["z_cl"]):
            e += ((np.log(m3["z_cl"]) - np.log(0.019)) / 0.5) ** 2
        else:
            e += 4.0
    return e


def unstable(el, pl):
    """Nyquist: the open loop has no unstable poles (stable filters, stable plant), so the closed loop is unstable iff
    L(e^{jw}) encircles -1.  Winding number of 1+L over the upper half circle, doubled (conjugate symmetry)."""
    f = np.concatenate([np.arange(0.02, 60.0, 0.01), np.arange(60.0, 500.0, 0.25)])
    L = L_of(el, pl, f)
    ph = np.unwrap(np.angle(1 + L))
    n = int(round(2 * (ph[-1] - ph[0]) / (2 * np.pi)))
    return n != 0


def fit_plants(c):
    el = Elec(c)
    el_hi = Elec(c); el_hi.kp = 696.0
    targets = dict(f=F_CL, z=Z_CL, df=DF_KP)
    best = {}
    # (i) smooth
    bi = (1e9, None)
    for tau in np.arange(0.002, 0.030, 0.001):
        for f1 in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0):
            for g0 in np.exp(np.linspace(np.log(0.005), np.log(0.4), 40)):
                pl = Plant(g0, tau, f1, label="smooth")
                e = fit_error(el, pl, el_hi, targets)
                if e < bi[0]:
                    bi = (e, pl)
    best["smooth"] = bi
    # (ii) resonant
    br = (1e9, None)
    for fp in np.arange(19.0, 24.01, 0.5):
        for zp in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
            for tau in (0.001, 0.002, 0.004, 0.006, 0.008, 0.012):
                for f1 in (2.0, 5.0, 12.0):
                    for g0 in np.exp(np.linspace(np.log(0.003), np.log(0.3), 18)):
                        pl = Plant(g0, tau, f1, fp, zp, label="resonant fp %.2f zp %.3f" % (fp, zp))
                        e = fit_error(el, pl, el_hi, targets)
                        if e < br[0]:
                            br = (e, pl)
    best["resonant"] = br
    # (iii) smooth + a MODERATELY damped mode (a resonance/anti-resonance-like bump of x1.3-2 at 18-21 Hz over 10-15 Hz)
    bm = (1e9, None)
    for fp in np.arange(18.0, 25.01, 0.5):
        for zp in (0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5):
            for tau in (0.002, 0.004, 0.006, 0.008, 0.010, 0.013):
                for f1 in (3.0, 8.0, 20.0):
                    for g0 in np.exp(np.linspace(np.log(0.01), np.log(0.3), 16)):
                        pl = Plant(g0, tau, f1, fp, zp, label="smooth+mode fp %.1f zp %.2f" % (fp, zp))
                        e = fit_error(el, pl, el_hi, targets, bump=True)
                        if e < bm[0]:
                            bm = (e, pl)
    best["smooth+mode"] = bm
    # (iv) smooth x (1 + kappa (M-1)): a WEAKLY COUPLED mode -- broad bump, flat phase, DC unchanged; fitted to the census
    bw = (1e9, None)
    el_mid = Elec(c); el_mid.kp = 560.0
    for fp in np.arange(19.0, 22.51, 0.25):
        for zp in (0.02, 0.03, 0.04, 0.05, 0.07, 0.10):
            for kappa in (0.3, 0.5, 0.8, 1.2, 1.8):
                for tau in (0.004, 0.007, 0.010, 0.013):
                    for f1 in (5.0, 12.0, 30.0):
                        for g0 in np.exp(np.linspace(np.log(0.02), np.log(0.12), 10)):
                            pl = Plant(g0, tau, f1, fp, zp, "weak-mode fp %.2f zp %.3f kappa %.1f" % (fp, zp, kappa), kappa=kappa)
                            e = fit_error(el, pl, el_hi, targets, bump=True, el_mid=el_mid)
                            if e < bw[0]:
                                bw = (e, pl)
    best["weak-mode"] = bw
    return el, best


# ---------------------------------------------------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------------------------------------------------
def dc_held_pole(f_hz, dc, div=1.0):
    a = int(round(1024 * np.exp(-2 * np.pi * f_hz / FS)))
    b = int(round(dc * div * (1024 - a) / 2.0))
    return a, b


def make_candidates(c, f_notch):
    C = []

    def base():
        return Elec(c)
    e = base(); C.append(("as-built V282", e))
    for fhz in (25.0, 33.0, 50.0):
        e = base(); e.fa, e.fb = dc_held_pole(fhz, 30.8911); e.label = "fb pole %g Hz (%d/%d)" % (fhz, e.fa, e.fb); C.append(("(a) " + e.label, e))
    for fhz in (10.0, 15.0):
        e = base(); e.la, e.lb = dc_held_pole(fhz, 0.990234, 32.0); e.label = "lag pole %g Hz (%d/%d)" % (fhz, e.la, e.lb); C.append(("(b) " + e.label, e))
    for k in (3, 4):
        e = base(); e.dfilt = (1 - 2.0 ** -k,); fc = -np.log(1 - 2.0 ** -k) * FS / (2 * np.pi); e.label = "D filter k=%d (%.0f Hz)" % (k, fc); C.append(("(c) " + e.label, e))
    for Q in (2.0, 3.0, 4.0):
        e = base(); e.notch_fb = (f_notch, Q); e.label = "notch fb %.1f Hz Q%g" % (f_notch, Q); C.append(("(d-fb) " + e.label, e))
    for Q in (2.0, 3.0, 4.0):
        e = base(); e.notch_out = (f_notch, Q); e.label = "notch PID-sum %.1f Hz Q%g" % (f_notch, Q); C.append(("(d-out) " + e.label, e))
    for fz, fp in ((10.0, 30.0), (14.0, 42.0), (20.0, 60.0)):
        e = base(); e.lead_out = (fz, fp); e.label = "lead PID-sum z%g/p%g" % (fz, fp); C.append(("(e) " + e.label, e))
    # (f) combinations
    e = base(); e.notch_out = (f_notch, 3.0); e.dfilt = (1 - 2.0 ** -3,); e.label = "notch out Q3 + D filter k3"; C.append(("(f) " + e.label, e))
    e = base(); e.notch_fb = (f_notch, 3.0); e.fa, e.fb = dc_held_pole(25.0, 30.8911); e.label = "notch fb Q3 + fb pole 25 Hz"; C.append(("(f) " + e.label, e))
    e = base(); e.notch_out = (f_notch, 3.0); e.lead_out = (14.0, 42.0); e.label = "notch out Q3 + lead 14/42"; C.append(("(f) " + e.label, e))
    for fl, k in ((8.0, 3), (10.0, 3), (10.0, 4)):
        e = base(); e.la, e.lb = dc_held_pole(fl, 0.990234, 32.0); e.dfilt = (1 - 2.0 ** -k,); e.label = "lag pole %g Hz + D filter k%d" % (fl, k); C.append(("(f) " + e.label, e))
    e = base(); e.fa, e.fb = dc_held_pole(25.0, 30.8911); e.dfilt = (1 - 2.0 ** -3,); e.label = "fb pole 25 Hz + D filter k3"; C.append(("(f) " + e.label, e))
    e = base(); e.fa, e.fb = dc_held_pole(33.0, 30.8911); e.dfilt = (1 - 2.0 ** -3,); e.label = "fb pole 33 Hz + D filter k3"; C.append(("(f) " + e.label, e))
    e = base(); e.notch_out = (f_notch, 3.0); e.fa, e.fb = dc_held_pole(33.0, 30.8911); e.dfilt = (1 - 2.0 ** -3,); e.label = "notch out Q3 + fb 33 + Dfilt k3"; C.append(("(f) " + e.label, e))
    # reference rows the operator rejects
    e = base(); e.kd = 96.0; e.label = "Kd 96 (REJECTED class)"; C.append(("(ref) " + e.label, e))
    return C


def score_all(el0, pl, cands):
    m0 = margins(el0, pl)
    st0 = step_response(el0, pl)
    ng0 = noise_gain(el0)
    L0_39 = L_of(el0, pl, 3.9); L0_73 = L_of(el0, pl, 7.3)
    flo = np.arange(0.5, 5.01, 0.25)
    L0_lo = L_of(el0, pl, flo)
    rows = []
    pr("  %-36s          | %6s %6s | %5s %6s | %5s %6s %5s | %4s %6s | %5s %6s %6s | %5s %5s %5s | %6s %5s %5s | %5s" % (
        "candidate", "f_cl", "z_cl", "PM", "fc", "GM", "f180", "Ms", "dL<5", "d3.9", "|R73|", "angR73", "gate73", "pkR", "pkA", "t90", "noise", "|L|20", "vm", "fTD"))
    for name, el in cands:
        m = margins(el, pl)
        st = step_response(el, pl)
        R73 = (el.C(7.3) * el.Hlag(7.3) * el.F(7.3)) / (el0.C(7.3) * el0.Hlag(7.3) * el0.F(7.3))
        gate = abs(LS73 * R73 + LR73)
        dlo = np.max(np.abs(L_of(el, pl, flo) / L0_lo - 1))
        L39 = L_of(el, pl, 3.9)
        d39 = np.degrees(np.angle(L39 / L0_39))
        ftd, ztd = cl_pole_td(el, pl)
        L20 = abs(L_of(el, pl, F_CL))
        uns = unstable(el, pl)
        rows.append(dict(name=name, m=m, st=st, R73=R73, gate=gate, dlo=dlo, d39=d39, ng=noise_gain(el) / ng0, ftd=ftd, ztd=ztd, unstable=uns))
        pr("  %-36s %s| %6.2f %6.3f | %5.0f %6.1f | %5.2f %6.1f %5.1f | %3.0f%% %+6.1f | %5.2f %+6.0f %6.3f | %5.2f %5.2f %5.0f | %6.2f %5.2f %5.2f | %5.1f/%.3f" % (
            name[:36], "UNSTABLE " if uns else "         ", m["f_cl"], m["z_cl"], m["pm"] if m["pm"] is not None else np.nan, m["fc"] if m["fc"] else np.nan,
            m["gm"] if m["gm"] else np.nan, m["f180"] if m["f180"] else np.nan, m["Ms"], 100 * dlo, d39,
            abs(R73), np.degrees(np.angle(R73)), gate, st["peak_rate"] / st0["peak_rate"], st["peak_acc"] / st0["peak_acc"], 1000 * st["t90"],
            noise_gain(el) / ng0, L20, m["vm"], ftd, ztd))
    return rows


def integer_mirrors(f_notch):
    pr("\n  INTEGER MIRRORS (what a cave would execute; V850 sar floors; checked against the float response)")
    # notch, Direct Form I, Q14 coefficients, 32-bit state
    bq, aq = notch_coefs(f_notch, 3.0)
    B = [int(round(v * 16384)) for v in bq]; A = [int(round(v * 16384)) for v in aq]
    pr("  notch %.1f Hz Q3, Q14: b = %s  a = %s   (a0 = 16384 implied)" % (f_notch, B, A))
    pr("    def notch_tick(x, st):                       # st = [x1, x2, y1, y2] int32; x = fb operand r26 (or the PID sum)")
    pr("        acc = %d*x + (%d)*st[0] + %d*st[1] - (%d)*st[2] - (%d)*st[3]" % (B[0], B[1], B[2], A[1], A[2]))
    pr("        y = acc >> 14                              # sar 14 (floors)")
    pr("        st[:] = [x, st[0], y, st[2]]; return y")
    # simulate integer vs float on a chirp
    n = 20000
    t = np.arange(n) * TS
    x = (3000 * np.sin(2 * np.pi * (5 + 40 * t / t[-1]) * t)).astype(np.int64)
    st = [0, 0, 0, 0]; y = np.zeros(n)
    for i in range(n):
        acc = B[0] * int(x[i]) + B[1] * st[0] + B[2] * st[1] - A[1] * st[2] - A[2] * st[3]
        yi = acc >> 14
        st = [int(x[i]), st[0], yi, st[2]]; y[i] = yi
    yf = signal.lfilter(bq, aq, x.astype(float))
    pr("    chirp 5-45 Hz, amplitude 3000: max |int - float| = %.1f counts, rms %.2f; 32-bit headroom on acc %.0fx" % (
        np.max(np.abs(y - yf)), np.sqrt(np.mean((y - yf) ** 2)), 2 ** 31 / (abs(B[0]) * 46080 * 4)))
    # D filter
    pr("  D filter k=3 (first-order on D, 21 Hz corner):  y += (D - y) >> 3  -- SAME stuck-LSB caveat as V288 (sar floors): add the +1 fix")
    pr("  lead on the PID sum (fz 14 / fp 42): y = S + 2*(S - lp) with lp += (S - lp) >> 4 (fp = 10.3 Hz for k=4; use k=2 for 42 Hz) -- DC gain exactly 1, HF gain 3")


def main():
    global F_CL, Z_CL, DF_KP
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.argv = [sys.argv[0]] + args + [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) >= 2:
        F_CL, Z_CL = float(args[0]), float(args[1])
    if len(args) >= 3:
        DF_KP = float(args[2])
    global REQUIRE_STABLE_696
    if len(args) >= 4:
        REQUIRE_STABLE_696 = args[3] not in ("0", "false", "False")
    b = open(IMG, "rb").read()
    c = LG.read_build(IMG)
    pr("image %s" % os.path.basename(IMG))
    pr("cells: Kp %s Kd %s fb %d/%d lag %d/%d gain %d (at 0x%X) fade 254/256; targets f_cl %.2f zeta %.3f dF(Kp 248->696) %+.2f Hz; require stable at Kp 696: %s" % (
        c["kp_Y"].astype(int).tolist(), c["kd_Y"].astype(int).tolist(), c["fb_a"], c["fb_b"], c["lag_a"], c["lag_b"], c["gain"], c["gain_addr"], F_CL, Z_CL, DF_KP, REQUIRE_STABLE_696))
    el0 = Elec(c)
    pr("\n" + "=" * 160)
    pr("1. THE ELECTRONICS ALONE at 20.3 Hz (no plant): magnitude and phase of every element, Kp 248 / Kd 128")
    pr("=" * 160)
    tot = 1.0 + 0j
    for nm, ph, mg in phase_budget(el0, Plant(1.0, 0.0, 1e9, label="none"), F_CL)[:-1]:
        pr("  %-34s  |.| %8.4f   phase %+7.1f deg" % (nm, mg, ph))
    R = el0.ret(F_CL)
    pr("  => return ratio F*C*fade*Hlag*K6/32768*z^-1 at %.1f Hz: %.3f T counts per raw rate count, phase %+.1f deg" % (F_CL, abs(R), np.degrees(np.angle(R))))
    pr("     (creep20 measured T/rate at the line = 15.0 T counts per deg/s = %.2f per raw count, phase -111 raw / ~-83 with the 3.9 ms offset removed)" % (15.0 / CPD))
    for kp in (248, 300, 470, 696):
        e = Elec(c); e.kp = float(kp); R = e.ret(F_CL)
        pr("     Kp %3d: |ret| %.3f  phase %+.1f deg  (D lead diluted as Kp rises)" % (kp, abs(R), np.degrees(np.angle(R))))

    pr("\n" + "=" * 160)
    pr("2. PLANT FIT -- two families, fitted to (f_cl, zeta_cl), the off-line |G|/angle at 10 and 15 Hz (offset-corrected) and the Kp shift")
    pr("=" * 160)
    import json
    cache = os.path.join(SCR, "loopshape20_plants%s.json" % ("" if REQUIRE_STABLE_696 else "_unconstrained"))
    if "--nofit" in sys.argv and os.path.exists(cache):
        el = Elec(c); best = {}
        for fam, d in json.load(open(cache)).items():
            best[fam] = (d["err"], Plant(d["g0"], d["tau"], d["f1"], d.get("fp"), d.get("zp"), d["label"], kappa=d.get("kappa")))
    else:
        el, best = fit_plants(c)
        json.dump({fam: dict(err=e, g0=pl.g0, tau=pl.tau, f1=pl.f1, fp=pl.fp, zp=pl.zp, label=pl.label, kappa=pl.kappa) for fam, (e, pl) in best.items()}, open(cache, "w"), indent=1)
    plants = []
    for fam in ("smooth", "resonant", "smooth+mode", "weak-mode"):
        e, pl = best[fam]
        plants.append(pl)
        m = margins(el, pl)
        eh = Elec(c); eh.kp = 696.0; mh = margins(eh, pl)
        em = Elec(c); em.kp = 470.0; mm = margins(em, pl)
        pr("\n  family %-9s fit error %.2f : g0 %.4f deg/s per count, tau %.1f ms, f1 %.1f Hz%s" % (
            fam, e, pl.g0, 1e3 * pl.tau, pl.f1, (", MODE fp %.2f Hz zp %.3f" % (pl.fp, pl.zp)) if pl.fp else ""))
        pr("    closed loop at Kp 248: f_cl %.2f Hz zeta %.3f | Ms %.1f @ %.1f | PM %s @ %s | GM %s @ %s | vector margin %.3f | unity crossings %s" % (
            m["f_cl"], m["z_cl"], m["Ms"], m["fMs"], "%.0f" % m["pm"] if m["pm"] is not None else "--", "%.1f" % m["fc"] if m["fc"] else "--",
            "%.2f" % m["gm"] if m["gm"] else "--", "%.1f" % m["f180"] if m["f180"] else "--", m["vm"], ["%.1f" % x for x in m["fc_all"]]))
        pr("    Kp 470: f_cl %.2f zeta %.3f Ms %.1f | Kp 696: f_cl %.2f zeta %.3f Ms %.1f  => df(248->696) = %+.2f Hz (measured %+.1f)" % (
            mm["f_cl"], mm["z_cl"], mm["Ms"], mh["f_cl"], mh["z_cl"], mh["Ms"], mh["f_cl"] - m["f_cl"], DF_KP))
        ftd, ztd = cl_pole_td(el, pl)
        pr("    time-domain check (impulse response, 15-26 Hz band): f %.2f Hz, zeta %.3f ; unstable at Kp 248/470/696: %s/%s/%s" % (
            ftd, ztd, unstable(el, pl), unstable(em, pl), unstable(eh, pl)))
        pr("    plant vs the off-line estimate (|G| x1e-3, angle corrected = raw - 360 f tau):")
        for f0, (mag, phr) in G_OFF.items():
            g = pl.Gs(f0) * 1e3
            pr("      %2d Hz  model |G| %5.1f ang %+6.0f  | measured |G| %5.1f ang(raw) %+5.0f ang(corr) %+5.0f" % (f0, abs(g), np.degrees(np.angle(g)), mag, phr, phr - 360 * f0 * TAU_STREAM))
        pr("    phase budget at %.1f Hz (each element, deg):" % F_CL)
        L = L_of(el, pl, F_CL)
        for nm, ph, mg in phase_budget(el, pl, F_CL):
            pr("      %-34s %+7.1f   (|.| %.3f)" % (nm, ph, mg))
        pr("      %-34s %+7.1f   |L| %.3f" % ("TOTAL L", np.degrees(np.angle(L)), abs(L)))
        pr("    |L| and phase across the band:")
        pr("      " + " ".join("%5.1f" % f0 for f0 in (3.9, 5, 7.3, 10, 13.5, 16, 18, 19, 20, 20.5, 21, 22, 24, 26, 28, 30, 35, 40, 50)))
        pr("      " + " ".join("%5.2f" % abs(L_of(el, pl, f0)) for f0 in (3.9, 5, 7.3, 10, 13.5, 16, 18, 19, 20, 20.5, 21, 22, 24, 26, 28, 30, 35, 40, 50)))
        pr("      " + " ".join("%+5.0f" % np.degrees(np.angle(L_of(el, pl, f0))) for f0 in (3.9, 5, 7.3, 10, 13.5, 16, 18, 19, 20, 20.5, 21, 22, 24, 26, 28, 30, 35, 40, 50)))

    pr("\n" + "=" * 160)
    pr("3. CANDIDATES on each fitted plant.  f_cl/z_cl = closed-loop pole from the |S| peak; PM/fc, GM/f180, Ms over 3-80 Hz; dL<5 = max |dL/L| below 5 Hz;")
    pr("   d3.9 = loop phase change at openpilot's 3.9 Hz crossover (deg); R73 = servo-arm ratio at 7.3 Hz; gate73 = |Ls R + Lr| (<= 1.000 passes, ratio only);")
    pr("   pkR/pkA = peak wheel rate / accel of the linear closed-loop response to a capped-frame reference step, relative to as-built; t90 ms;")
    pr("   noise = rms rate->D gain 30-500 Hz relative; |L|20 = loop gain at the mode; vm = min |1+L|; fTD = time-domain pole check f/zeta")
    pr("=" * 160)
    allrows = {}
    for pl in plants:
        pr("\n  PLANT: %s" % pl.label)
        cands = make_candidates(c, F_CL)
        allrows[pl.label] = score_all(el0, pl, cands)
    integer_mirrors(F_CL)
    # notch cal-table sanity: the notch on the fb operand also filters the P term's feedback; check DC and 0-5 Hz lag
    pr("\n  notch phase/gain below the mode (fb notch Q3): " + "  ".join("%g Hz %.3f/%+.1fdeg" % (f0, abs(notch_z(f0, F_CL, 3.0)), np.degrees(np.angle(notch_z(f0, F_CL, 3.0)))) for f0 in (1, 3.9, 5, 7.3, 10, 13.5, 16)))
    pr("  notch Q2: " + "  ".join("%g Hz %.3f/%+.1fdeg" % (f0, abs(notch_z(f0, F_CL, 2.0)), np.degrees(np.angle(notch_z(f0, F_CL, 2.0)))) for f0 in (1, 3.9, 5, 7.3, 10, 13.5, 16)))
    tag = "" if REQUIRE_STABLE_696 else "_unconstrained"
    with open(os.path.join(SCR, "loopshape20_loop_model%s.txt" % tag), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/loopshape20_loop_model.txt")


if __name__ == "__main__":
    main()
