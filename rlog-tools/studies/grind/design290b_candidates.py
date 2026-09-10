# -*- coding: utf-8 -*-
"""studies/grind/design290b_candidates.py -- V290 second-round design under the TWO-POLE constraint.
DESIGN STUDY: builds nothing, flashes nothing, sends nothing.

AUTHORSHIP.  Agent `design290b` (2026-09-09) wrote this file and completed the PLANT-FAMILY stage; it was killed by a
machine restart before anything downstream ran.  Agent `design290d` (same day) RE-RAN the family stage from scratch and
reproduced `_scratch/design290b_family.json` character-for-character (only the two timing lines differ), independently
re-derived both measured pole anchors by a different method (`design290d_anchors.py`: Welch peak + Hilbert free-decay on
the wheel rate), and then completed the rest of the brief IN THIS FILE so the record carries one design lineage:
  * the OUTPUT-LAG pole rows (0xC63EC/EE at 8 / 12 / 20 Hz, DC held) -- brief row 3, the 2026-09-08 strike re-derived;
  * the LEAD / lead-lag rows on the sum node -- brief row 5;
  * fb pole 50 Hz, Kp 128, Kp 200 + notch;
  * exact gain-crossover / PHASE MARGIN / gain-margin / time-to-90 % columns in `metrics` (`crossover()`);
  * `search_row9` extended to the brief's row 10 (PM >= 40 deg OR zeta >= 0.08 under the authority gates), with the lag
    pole and the leads as search axes;
  * `frontier()` -- the (Kd, fb pole) authority frontier, the one region the full search left unresolved.
Memo: `docs/specs/design/DESIGN-V290B-2026-09-09.md`.  Part C (limit cycle vs linear mode) is `design290d_nonlinear.py`.
NOTE: `Pool` here has deadlocked on this machine after an earlier run was killed; `D290_NPROC` sets the worker count and
the frontier stage runs acceptably serially (~4 min) if it hangs.

A. PLANT FAMILY.  Every plant (smooth / pure mode / weakly-coupled mode; g0, integer-tick tau, f1, fp, zp, kappa) whose
   EXACT closed-loop pole (root-finding 1 + L(z) = 0, adv_v290_physics machinery, byte-read electronics) reproduces BOTH
   measured poles: V282 electronics -> 20.0 Hz, zeta 0.012-0.045 (wire free-decay median 0.027) and V289 electronics
   (integer notch 20.036 Hz Q3 + fb pole 875/2301) -> 15.6-17.3 Hz (pooled 16.4-17.0, census 15.96 [15.39-16.82]),
   zeta -0.06..0.12 (V289 events decay with zeta_eff 0.02-0.13; the sub-family with zeta < 0 is the limit-cycle branch and
   is reported separately).  Soft checks reported per fit: the Kp 696 datum (r31-r34: f +0.4 Hz, stable, zeta 0.019) and the
   off-line V282 plant estimate (creep20 / loopshape20 G_282, 3.9 ms stream offset removed).
B. CANDIDATE TABLE on the whole family (worst case and median): pole f/zeta 8-30 Hz, Ms, min|1+L|, 7 Hz gate, 3.9 Hz phase,
   |dL| below 5 Hz, linear + integer-mirror capped-step pkR/pkA, DC authority, HF noise into the motor, new-peak check
   10-14 / 22-30 Hz, stability, bytes changed.  Rows 1-9 of the brief, incl. the re-centre iteration, the joint
   (notch, Q, fb pole) solve, wide notch / roll-off, the opposite-sign post-lag term (dose sweep, spring regime), Kd 96,
   Kp 200/160, and the constrained search for zeta >= 0.08 with pkR >= 0.95 and gate <= 1.01 on the WORST fit.

Conventions (adv_v290_physics): x = gp-0x6a56 = -wire rate; R = T per raw count of x (negative feedback), L = R*CPD*Gd(z);
the post-lag n term: bracket = Hlag*N - g*(1-N)  (g > 0 = the first memo's sign, g < 0 = the OPPOSITE sign);
Kp/Kd/fb pole/lag pole from the c dict (byte-read V289 image; V282 = fb 923/1560, no notch).

Run:  python design290b_candidates.py family     -> _scratch/design290b_family.json + design290b_family.txt
      python design290b_candidates.py cands      -> _scratch/design290b_cands.txt (+ design290b_cands.json)
      python design290b_candidates.py all
"""
import json
import os
import sys
import time
from multiprocessing import Pool

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
from scipy import signal

NPROC = int(os.environ.get("D290_NPROC", "5"))

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                  # noqa: E402  (Blocks, Plant, poles, mode_pole, pmul, padd, pev, LS73/LR73)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = A.TS, A.FS, A.CPD
OUT = []
# measured targets (EVIDENCE: adv_v290_relocation / loopshape20_mode_nature / V289 marks)
F282 = (19.7, 20.4); Z282 = (0.012, 0.045); F289 = (15.6, 17.3); Z289 = (-0.06, 0.12); Z289_STABLE = 0.005
# off-line V282 plant, |G| x1e-3 deg/s per T count, RAW angle (loopshape20 G_282), stream offset 3.9 ms to remove
G_282 = {10.2: (27.0, -79.0), 15.6: (40.8, -63.0), 18.0: (39.0, -73.0), 20.3: (47.6, -72.0), 22.7: (44.6, -69.0), 24.2: (18.8, -41.0)}
TAU_STREAM = 0.0039
STEP_SP = 33          # one capped 0xE4 frame (123 raw) through the LINEAR.TO6X map ~ 33 setpoint counts = 1056 E counts


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# ---------------------------------------------------------------------------------------------------------- helpers
def rbj(kind, fc, Q, q14=True):
    """RBJ biquad (notch / lpf / bpf) at fc, Q, fs 1 kHz, as (b, a) ascending in z^-1; Q14 integers rounded exactly as
    the V289 build did (b0 = round(16384 * b0/a0), a0 = 16384) -- returns floats scaled back to a0 = 1."""
    w0 = 2 * np.pi * fc / FS; al = np.sin(w0) / (2 * Q); c = np.cos(w0); a0 = 1 + al
    if kind == "notch":
        b = np.array([1.0, -2 * c, 1.0]); a = np.array([a0, -2 * c, 1 - al])
    elif kind == "lpf":
        b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2]); a = np.array([a0, -2 * c, 1 - al])
    elif kind == "bpf":                                  # constant 0 dB peak
        b = np.array([al, 0.0, -al]); a = np.array([a0, -2 * c, 1 - al])
    else:
        raise ValueError(kind)
    b, a = b / a0, a / a0
    if q14:
        bi = np.round(b * 16384); ai = np.round(a * 16384); ai[0] = 16384
        return bi / 16384.0, ai / 16384.0, (bi.astype(int).tolist(), ai.astype(int).tolist())
    return b, a, None


def dc_held_pole(f_hz, dc=30.891):
    """fb one-pole a/b integers with the two-sample-sum DC held (LM.dc_held_pole)."""
    a = int(round(1024 * np.exp(-2 * np.pi * f_hz / FS)))
    b = int(round(dc * (1024 - a) / 2.0))
    return a, b


def dc_held_lag(f_hz, dc=0.990234375):
    """OUTPUT-lag one-pole a/b integers (0xC63EC/EE), readout (s + s')>>5, DC held at the stock 1014/1024/... = 0.990234.
    Stock 992/507 -> 5.05 Hz.  b = dc * 32 * (1024 - a) / 2."""
    a = int(round(1024 * np.exp(-2 * np.pi * f_hz / FS)))
    b = int(round(dc * 32.0 * (1024 - a) / 2.0))
    return a, b


def q14(b, a):
    """(b, a) floats ascending in z^-1, a[0] == 1 -> Q14 integer 3-tap ([b0,b1,b2], [16384,a1,a2]) for BiquadInt."""
    bb = np.zeros(3); aa = np.zeros(3)
    bb[:len(b)] = b; aa[:len(a)] = a
    bi = np.round(bb * 16384).astype(int); ai = np.round(aa * 16384).astype(int); ai[0] = 16384
    return bi.tolist(), ai.tolist()


def leadlag(fz, fp, fhf=None):
    """first-order lead (1 + s/wz)/(1 + s/wp), bilinear at fs 1 kHz, unity DC; optional first-order LPF at fhf to pull the
    HF gain back toward 1.  Returns (b, a) ascending in z^-1."""
    wz, wp = 2 * np.pi * fz, 2 * np.pi * fp
    b, a = signal.bilinear([1.0 / wz, 1.0], [1.0 / wp, 1.0], fs=FS)
    if fhf:
        wh = 2 * np.pi * fhf
        b2, a2 = signal.bilinear([1.0], [1.0 / wh, 1.0], fs=FS)
        b, a = np.convolve(b, b2), np.convolve(a, a2)
    b, a = np.asarray(b, float) / a[0], np.asarray(a, float) / a[0]
    return b, a


class Elec(A.Blocks):
    """A.Blocks + generic sum-node filter cascade, a post-lag S-band-pass term, an x-fed post-lag band-pass, Kp/Kd/fb via c."""

    def __init__(self, c, sumfilt=None, g=0.0, sbp=None, xbp=None, label="", prefilter=None, notch289=False):
        super().__init__(c, notch=notch289, g=g, kp=c["kp_Y"][0])
        self.label = label
        if sumfilt:                                       # list of (b, a) ascending in w
            num, den = np.array([1.0]), np.array([1.0])
            for b, a in sumfilt:
                num, den = np.convolve(num, b), np.convolve(den, a)
            if notch289:
                num, den = np.convolve(num, self.N[0]), np.convolve(den, self.N[1])
            self.N = (num, den)
            self.oneMinusN = (A.padd(den, -num), den)
        self.sbp = sbp            # (gS, (b, a)): y' = y + gS * BP(S)   (post-lag, S-fed)
        self.xbp = xbp            # (kx, (b, a)): added to R: K*fade*kx*BP*z^-1 per count of x (post-lag, x-fed)
        self.prefilter = prefilter  # (b, a) on the setpoint (V288's 10.3 Hz one-pole), forward path only

    def bracket(self):
        hn, hd = self.Hlag; nn, nd = self.N; mn, _ = self.oneMinusN
        num = A.padd(A.pmul(hn, nn), -self.g * A.pmul(mn, hd))
        den = A.pmul(hd, nd)
        if self.sbp:
            gS, (b, a) = self.sbp
            num = A.padd(A.pmul(num, a), gS * A.pmul(b, den)); den = A.pmul(den, a)
        return num, den

    def R(self):
        bn, bd = self.bracket()
        num = A.pmul([0.0, 1.0], self.F[0], self.C[0], bn) * self.K * self.fade
        den = A.pmul(self.F[1], self.C[1], bd)
        if self.xbp:
            kx, (b, a) = self.xbp
            t = A.pmul([0.0, 1.0], b) * self.K * self.fade * kx
            num = A.padd(A.pmul(num, a), A.pmul(t, den)); den = A.pmul(den, a)
        return num, den

    def fwd(self):
        bn, bd = self.bracket()
        num = A.pmul([0.0, 1.0], self.C[0], bn) * self.K * self.fade; den = A.pmul(self.C[1], bd)
        if self.prefilter:
            num, den = A.pmul(num, self.prefilter[0]), A.pmul(den, self.prefilter[1])
        return num, den


def Lpoly(el, pl):
    rn, rd = el.R()
    return A.pmul(rn, pl.num) * CPD, A.pmul(rd, pl.den)


def poles_of(el, pl):
    n, d = Lpoly(el, pl)
    ch = A.padd(d, n); w = np.roots(ch[::-1]); w = w[np.abs(w) > 1e-12]
    z = 1.0 / w; s = np.log(z) * FS
    return np.abs(s.imag) / (2 * np.pi), -s.real / np.abs(s), z


def least_damped(f, zeta, lo, hi):
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan
    k = int(np.argmin(zeta[m])); return float(f[m][k]), float(zeta[m][k])


def Sfun(el, pl, f):
    n, d = Lpoly(el, pl)
    L = A.pev(n, f) / A.pev(d, f)
    return 1 / np.abs(1 + L), L


FG = np.arange(3.0, 80.0, 0.05)


def crossover(L):
    """HIGHEST gain crossover of |L| on FG, its phase margin, and the gain margin at the first -180 deg crossing above it.
    L is the return ratio (characteristic 1 + L = 0), so PM = 180 + arg(L(wc))."""
    m = np.abs(L)
    idx = np.where((m[:-1] >= 1.0) & (m[1:] < 1.0))[0]
    if len(idx) == 0:
        return (np.nan, np.nan, np.nan) if m[-1] >= 1.0 else (0.0, 180.0, np.inf)
    i = idx[-1]
    r = (m[i] - 1.0) / (m[i] - m[i + 1]) if m[i] != m[i + 1] else 0.0
    wc = float(FG[i] + r * (FG[1] - FG[0]))
    ph = np.unwrap(np.angle(L))
    pm = float(np.degrees(ph[i] + r * (ph[i + 1] - ph[i]))) + 180.0
    while pm > 180.0:
        pm -= 360.0
    while pm < -180.0:
        pm += 360.0
    # gain margin: first crossing of arg(L) through -180 deg (mod 360) above wc
    gm = np.inf
    tgt = np.degrees(ph)
    for k in range(i, len(FG) - 1):
        for n in (-1, -3, 1):
            t = 180.0 * n
            if (tgt[k] - t) * (tgt[k + 1] - t) < 0:
                rr = (t - tgt[k]) / (tgt[k + 1] - tgt[k])
                g = m[k] + rr * (m[k + 1] - m[k])
                gm = min(gm, float(1.0 / g) if g > 0 else np.inf)
        if np.isfinite(gm):
            break
    return wc, pm, gm


def metrics(el, pl, el0=None, want_step=True):
    """per (candidate, plant): pole 8-30 (f, zeta), all poles, Ms, vm, S-peaks 10-14 / 22-30, stability, DC authority, linear step."""
    f, zeta, z = poles_of(el, pl)
    fm, zm = least_damped(f, zeta, 8.0, 30.0)
    S, L = Sfun(el, pl, FG)
    wc, pm, gm = crossover(L)
    out = dict(wc=wc, pm=pm, gm=gm, f=fm, z=zm, Ms=float(S.max()), fMs=float(FG[int(np.argmax(S))]), vm=float(np.min(np.abs(1 + L))),
               S1014=float(S[(FG >= 10) & (FG <= 14)].max()), S2230=float(S[(FG >= 22) & (FG <= 30)].max()),
               unst=bool(np.any(np.abs(z) >= 1.0)),
               poles=[(float(a), float(b)) for a, b in zip(f, zeta) if 5 <= a <= 40 and b < 0.5])
    # DC authority: closed-loop rate per setpoint count at DC, relative to el0 on the same plant
    fn, fd = el.fwd(); ln, ld = Lpoly(el, pl)
    dc = (A.pev(fn, 1e-6) / A.pev(fd, 1e-6)) * CPD * A.pev(pl.num, 1e-6) / A.pev(pl.den, 1e-6) / (1 + A.pev(ln, 1e-6) / A.pev(ld, 1e-6))
    out["dc"] = float(np.real(dc))
    if want_step:
        out.update(step_lin(el, pl))
    return out


def step_lin(el, pl, n=1500):
    """linear closed-loop wheel-rate response to a capped-frame reference step (STEP_SP counts -> 32*STEP_SP E counts)."""
    N = 2 ** 15
    f = np.fft.rfftfreq(N, TS); f[0] = 1e-6
    fn, fd = el.fwd(); ln, ld = Lpoly(el, pl)
    L = A.pev(ln, f) / A.pev(ld, f)
    Tcl = (A.pev(fn, f) / A.pev(fd, f)) * CPD * (A.pev(pl.num, f) / A.pev(pl.den, f)) / (1 + L)
    h = np.fft.irfft(Tcl, n=N)[:n]
    y = np.cumsum(h) * 32.0 * STEP_SP / CPD
    acc = np.gradient(y, TS)
    ss = float(y[-200:].mean())
    k = np.where(y >= 0.9 * ss)[0] if ss > 0 else np.array([], int)
    t90 = float(k[0] * TS * 1e3) if len(k) else np.nan       # ms to 90 % of the steady rate
    return dict(pkR=float(y.max()), pkA=float(acc.max()), ss=ss, t90=t90)


def gate73(el, el0):
    R73 = el.Rf(7.3) / el0.Rf(7.3)
    return float(abs(A.LS73 * R73 + A.LR73))


def plant_free(el, el0):
    """plant-independent columns: gate73, d3.9 (deg), |dL|<5 (max over 0.5-5 Hz), HF noise rms|R| 30-500 Hz vs el0."""
    flo = np.arange(0.5, 5.01, 0.25)
    dlo = float(np.max(np.abs(el.Rf(flo) / el0.Rf(flo) - 1)))
    d39 = float(np.degrees(np.angle(el.Rf(3.9) / el0.Rf(3.9))))
    fh = np.arange(30.0, 499.0, 0.5)
    noise = float(np.sqrt(np.mean(np.abs(el.Rf(fh)) ** 2)) / np.sqrt(np.mean(np.abs(el0.Rf(fh)) ** 2)))
    return dict(gate=gate73(el, el0), d39=d39, dlo=dlo, noise=noise)


# ---------------------------------------------------------------------------------------------------- integer mirror
def sar(v, k):
    return v >> k


def clampi(v, lim):
    return max(-lim, min(lim, v))


class BiquadInt:
    """Q14 TDF-II with first-order error feedback (the V289 cave's arithmetic; for the notch b1 == a1 so it reduces to
    the cave's  s1' = b1*n + s2  form).  Keeps n = x - y for the post-lag term."""

    def __init__(self, ints):
        self.B, self.A = ints; self.s1 = 0; self.s2 = 0; self.e = 0; self.n = 0; self.y = 0

    def tick(self, x):
        B, Aa = self.B, self.A
        acc = B[0] * x + self.s1 + self.e
        y = sar(acc, 14); self.e = acc & 0x3FFF
        self.s1 = B[1] * x - Aa[1] * y + self.s2
        self.s2 = B[2] * x - Aa[2] * y
        self.n = x - y; self.y = y
        return y


class Controller:
    def __init__(self, c, sumints=None, npost_g8=0, sbp=None, xbp=None, prefilter_k=None):
        self.c = c; self.s_fb = 0; self.s_lag = 0; self.E_prev = None
        self.sum = [BiquadInt(i) for i in (sumints or [])]
        self.npost_g8 = npost_g8
        self.sbp = (sbp[0], BiquadInt(sbp[1])) if sbp else None      # (g8, biquad) : y += g8*BP(S)>>8
        self.xbp = (xbp[0], BiquadInt(xbp[1])) if xbp else None      # (k8, biquad) : y += k8*BP(x)>>8
        self.pk = prefilter_k; self.spf = 0
        self.kp = int(c["kp_Y"][0]); self.kd = int(c["kd_Y"][0])

    def tick(self, sp, x):
        c = self.c
        if self.pk is not None:                     # V288's one-pole on the setpoint (kick/16 = k 4)
            self.spf += (sp - self.spf) >> self.pk; sp = self.spf
        x = clampi(int(x), 12000)
        s_new = sar(int(c["fb_a"]) * self.s_fb, 10) + sar(int(c["fb_b"]) * x, 10)
        fb = clampi(self.s_fb + s_new, int(c["fb_clamp"])); self.s_fb = s_new
        E = 32 * int(sp) - fb
        P = clampi(sar(E * self.kp, 8), int(c["p_clamp"]))
        dE = 0 if self.E_prev is None else (E - self.E_prev); self.E_prev = E
        D = clampi(sar(dE * self.kd, 3), int(c["d_clamp"]))
        S = clampi(sar(254 * (P + D), 8), int(c["sum_clamp"]))
        Sin = S; n = 0
        for bq in self.sum:
            S = bq.tick(S); n = bq.n
        S = clampi(S, int(c["sum_clamp"]))
        s_new2 = sar(int(c["lag_a"]) * self.s_lag, 10) + sar(int(c["lag_b"]) * S, 10)
        y = sar(self.s_lag + s_new2, 5); self.s_lag = s_new2
        if self.npost_g8:
            y = clampi(y - sar(self.npost_g8 * n, 8), int(c["sum_clamp"]))
        if self.sbp:
            g8, bq = self.sbp; y = clampi(y + sar(g8 * bq.tick(Sin), 8), int(c["sum_clamp"]))
        if self.xbp:
            k8, bq = self.xbp; y = clampi(y + sar(k8 * bq.tick(x), 8), int(c["sum_clamp"]))
        y = ((y + 0x8000) & 0xFFFF) - 0x8000
        return clampi(sar(y * int(c["gain"]), 15), int(c["t_clamp"]))


def mirror_step(c, pl, ctl_kw, sp_step=STEP_SP, n=1500):
    ctl = Controller(c, **ctl_kw)
    b, a = pl.num, pl.den
    xh = np.zeros(len(b)); yh = np.zeros(len(a))            # plant difference equation, ascending powers of z^-1
    rate = np.zeros(n); T = np.zeros(n); x = 0
    for k in range(n):
        Tk = ctl.tick(sp_step if k >= 5 else 0, x); T[k] = Tk
        xh = np.roll(xh, 1); xh[0] = Tk
        yk = (np.dot(b, xh) - np.dot(a[1:], yh[:-1])) / a[0]
        yh = np.roll(yh, 1); yh[0] = yk
        rate[k] = yk; x = int(round(CPD * yk))
    acc = np.gradient(rate, TS)
    return dict(pkR=float(np.max(np.abs(rate))), pkA=float(np.max(np.abs(acc))), ss=float(np.mean(rate[-200:])), pkT=float(np.max(np.abs(T))))


# ---------------------------------------------------------------------------------------------------- Part A: family
def cells():
    c, _ = A.read_v289()
    c282 = dict(c); c282["fb_a"], c282["fb_b"] = 923, 1560
    return c, c282


def mkplant(p):
    return A.Plant(dict(g0=p["g0"], tau=p["tau"], f1=p["f1"], fp=p["fp"], zp=p["zp"], kappa=p["kappa"], label="m"), 1.0, p.get("label", ""))


def _fam_worker(args):
    fp, zps, kaps, taus, f1s, g0s = args
    c, c282 = cells()
    el282 = A.Blocks(c282, False, 0.0); el289 = A.Blocks(c, True, 0.0)
    el696 = A.Blocks(c282, False, 0.0, kp=696)
    keep = []
    for zp in zps:
        for kap in kaps:
            if fp is None and (zp is not None or kap is not None):
                continue
            for tau in taus:
                for f1 in f1s:
                    for g0 in g0s:
                        p = dict(g0=float(g0), tau=float(tau), f1=float(f1), fp=fp, zp=zp, kappa=kap)
                        pl = mkplant(p)
                        f2, z2 = A.mode_pole(el282, pl, 10, 32)
                        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
                            continue
                        f9, z9 = A.mode_pole(el289, pl, 10, 32)
                        if not (np.isfinite(f9) and F289[0] <= f9 <= F289[1] and Z289[0] <= z9 <= Z289[1]):
                            continue
                        f6, z6 = A.mode_pole(el696, pl, 10, 32)
                        fr, zr, zz = poles_of(el696, pl)
                        p.update(f282=f2, z282=z2, f289=f9, z289=z9, f696=f6, z696=z6, unst696=bool(np.any(np.abs(zz) >= 1)))
                        # off-line plant check (V282 pooled, corrected phase)
                        err = []
                        for f0, (mag, phr) in G_282.items():
                            g = pl.Gs(f0) * 1e3; phc = phr - 360 * f0 * TAU_STREAM
                            err.append((float(np.log(abs(g) / mag)), float((np.degrees(np.angle(g)) - phc + 180) % 360 - 180)))
                        p["goff"] = err
                        keep.append(p)
    return keep


def family(nproc=NPROC):
    t0 = time.time()
    fps = [None] + list(np.arange(15.0, 28.01, 0.5))
    zps = (0.02, 0.04, 0.07, 0.12, 0.2, 0.35, 0.5, 0.7); kaps = (None, 0.15, 0.3, 0.6, 1.0)
    taus = (0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012); f1s = (3.0, 5.0, 12.0, 30.0)
    g0s = np.exp(np.linspace(np.log(0.006), np.log(0.5), 22))
    jobs = []
    for fp in fps:
        if fp is None:
            jobs.append((None, (None,), (None,), tuple(np.arange(0.001, 0.0161, 0.001)), (2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0), np.exp(np.linspace(np.log(0.006), np.log(0.5), 40))))
        else:
            jobs.append((float(fp), zps, kaps, taus, f1s, g0s))
    with Pool(nproc) as pool:
        res = pool.map(_fam_worker, jobs)
    fam = [p for r in res for p in r]
    for i, p in enumerate(fam):
        p["id"] = i
        p["label"] = ("smooth" if p["fp"] is None else "fp%.1f zp%.2f k%s" % (p["fp"], p["zp"], p["kappa"])) + " tau%.0f f1%.0f g0%.3f" % (1e3 * p["tau"], p["f1"], p["g0"])
    json.dump(fam, open(os.path.join(SCR, "design290b_family.json"), "w"), indent=0)
    pr("family: %d fits in %.0f s (grid %d shapes x g0)" % (len(fam), time.time() - t0, len(jobs)))
    return fam


def _refine_worker(args):
    seed, base = args
    rng = np.random.RandomState(seed)
    c, c282 = cells()
    el282 = A.Blocks(c282, False, 0.0); el289 = A.Blocks(c, True, 0.0); el696 = A.Blocks(c282, False, 0.0, kp=696)
    keep = []
    for _ in range(14):
        p = dict(base)
        if p["fp"] is not None:
            p["fp"] = float(p["fp"] * (1 + rng.uniform(-0.03, 0.03))); p["zp"] = float(p["zp"] * np.exp(rng.uniform(-0.35, 0.35)))
            if p["kappa"] is not None:
                p["kappa"] = float(p["kappa"] * np.exp(rng.uniform(-0.35, 0.35)))
        p["g0"] = float(p["g0"] * np.exp(rng.uniform(-0.15, 0.15)))
        p["tau"] = float(max(0.001, p["tau"] + rng.choice([-0.001, 0.0, 0.0, 0.001])))
        p["f1"] = float(p["f1"] * np.exp(rng.uniform(-0.3, 0.3)))
        pl = mkplant(p)
        f2, z2 = A.mode_pole(el282, pl, 10, 32)
        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
            continue
        f9, z9 = A.mode_pole(el289, pl, 10, 32)
        if not (np.isfinite(f9) and F289[0] <= f9 <= F289[1] and Z289[0] <= z9 <= Z289[1]):
            continue
        f6, z6 = A.mode_pole(el696, pl, 10, 32); fr, zr, zz = poles_of(el696, pl)
        p.update(f282=f2, z282=z2, f289=f9, z289=z9, f696=f6, z696=z6, unst696=bool(np.any(np.abs(zz) >= 1)))
        err = []
        for f0, (mag, phr) in G_282.items():
            g = pl.Gs(f0) * 1e3; phc = phr - 360 * f0 * TAU_STREAM
            err.append((float(np.log(abs(g) / mag)), float((np.degrees(np.angle(g)) - phc + 180) % 360 - 180)))
        p["goff"] = err; p["refined"] = True
        keep.append(p)
    return keep


def refine(fam, nproc=NPROC):
    t0 = time.time()
    with Pool(nproc) as pool:
        res = pool.map(_refine_worker, [(i, p) for i, p in enumerate(fam)])
    new = [p for r in res for p in r]
    fam = fam + new
    for i, p in enumerate(fam):
        p["id"] = i
        p["label"] = ("smooth" if p["fp"] is None else "fp%.1f zp%.2f k%s" % (p["fp"], p["zp"], ("%.2f" % p["kappa"]) if p["kappa"] is not None else "None")) + " tau%.0f f1%.0f g0%.3f" % (1e3 * p["tau"], p["f1"], p["g0"])
    json.dump(fam, open(os.path.join(SCR, "design290b_family.json"), "w"), indent=0)
    pr("refine: +%d fits by local perturbation of every grid fit (fp +-3 %%, zp/kappa x0.7-1.4, g0 x0.86-1.16, tau +-1 tick, f1 x0.74-1.35) -> %d in %.0f s" % (len(new), len(fam), time.time() - t0))
    return fam


def report_family(fam):
    c, c282 = cells()
    el282 = A.Blocks(c282, False, 0.0); el289 = A.Blocks(c, True, 0.0)
    stab = [p for p in fam if p["z289"] >= Z289_STABLE]; unst = [p for p in fam if p["z289"] < Z289_STABLE]
    pr("=" * 150)
    pr("A. THE PLANT FAMILY consistent with BOTH measured poles (V282 %.1f-%.1f Hz zeta %.3f-%.3f ; V289 %.1f-%.1f Hz zeta %.2f..%.2f)" % (*F282, *Z282, *F289, *Z289))
    pr("=" * 150)
    pr("  %d fits total: %d linear-stable on V289 (zeta289 >= %.3f), %d Nyquist-unstable on V289 (the limit-cycle branch)" % (len(fam), len(stab), Z289_STABLE, len(unst)))
    sm = [p for p in fam if p["fp"] is None]; pm = [p for p in fam if p["fp"] is not None and p["kappa"] is None]; wm = [p for p in fam if p["kappa"] is not None]
    pr("  by family: smooth %d, pure mode %d, weakly-coupled mode (kappa) %d" % (len(sm), len(pm), len(wm)))

    def q(v, ps=(5, 50, 95)):
        return np.percentile(v, ps)
    for nm, grp in (("ALL", fam), ("stable-V289", stab), ("unstable-V289", unst)):
        if not grp:
            continue
        pr("\n  --- %s (n=%d) ---" % (nm, len(grp)))
        for key, lab in (("z282", "zeta V282"), ("f289", "f V289"), ("z289", "zeta V289"), ("f696", "f @Kp696"), ("z696", "zeta @Kp696"), ("tau", "tau s"), ("g0", "g0"), ("fp", "fp"), ("zp", "zp")):
            v = np.array([p[key] if p[key] is not None else np.nan for p in grp], float)
            v = v[np.isfinite(v)]
            if len(v):
                pr("    %-12s p5/p50/p95 %8.3f %8.3f %8.3f" % (lab, *q(v)))
        pr("    Kp 696 datum (measured: f +0.4 Hz, zeta 0.019, stable): unstable at 696 on %d of %d fits; df(696-282) p5/p50/p95 %+.2f %+.2f %+.2f Hz" % (
            sum(p["unst696"] for p in grp), len(grp), *q([p["f696"] - p["f282"] for p in grp if np.isfinite(p["f696"])])))
        # magnitude / phase bands of the plant itself at 10-25 Hz
        fl = (10.2, 12.0, 14.0, 15.6, 16.7, 18.0, 20.3, 22.7, 24.2)
        pr("    plant G(s) (with delay) across the group, |G| x1e-3 deg/s per T count p5/p50/p95 and angle p5/p50/p95 (deg):")
        for f0 in fl:
            G = np.array([mkplant(p).Gs(f0) for p in grp])
            pr("      %5.1f Hz  |G| %6.1f %6.1f %6.1f   ang %+6.0f %+6.0f %+6.0f%s" % (
                f0, *q(np.abs(G) * 1e3), *q(np.degrees(np.angle(G))),
                ("   off-line V282: |G| %.1f ang(corr) %+.0f" % (G_282[f0][0], G_282[f0][1] - 360 * f0 * TAU_STREAM)) if f0 in G_282 else ""))
        # loop L at the two poles and the damping AXIS for an added BP term at the V289 pole
        pr("    off-line fit quality: |log|G| err| median over the 6 points p5/p50/p95 %.2f %.2f %.2f ; |phase err| median %.0f %.0f %.0f deg" % (
            *q([np.median([abs(e[0]) for e in p["goff"]]) for p in grp]), *q([np.median([abs(e[1]) for e in p["goff"]]) for p in grp])))
    # picture classification
    pr("\n  PHYSICAL PICTURE per fit (stable sub-family): plant mode fp / zp vs the closed-loop poles")
    cls = {"plant mode pulled": 0, "crossover coloured": 0, "coupled": 0, "smooth crossover": 0}
    for p in stab:
        if p["fp"] is None:
            k = "smooth crossover"
        elif p["zp"] <= 0.15 and abs(p["fp"] - p["f282"]) / p["f282"] < 0.12:
            k = "plant mode pulled"
        elif p["zp"] >= 0.35:
            k = "crossover coloured"
        else:
            k = "coupled"
        cls[k] += 1; p["picture"] = k
    pr("    " + ", ".join("%s: %d" % kv for kv in cls.items()))
    # ideal added-term ceiling: k e^{j phi} BP(fpole, Q3) at the V289 pole, best phi, k = 0.3 / 0.6 / 1.0 T per count
    pr("\n  IDEAL CEILING: an added return-ratio term k e^{j phi} BP(f_pole289, Q3) on the V289 base; best zeta over phi (least-damped 8-30 Hz pole)")
    sub = stab[:: max(1, len(stab) // 40)]
    rows = []
    for p in sub:
        pl = mkplant(p); f0 = p["f289"]
        w0 = 2 * np.pi * f0 / FS; al = np.sin(w0) / 6.0
        bpn = np.array([al, 0, -al]) / (1 + al); bpd = np.array([1.0, -2 * np.cos(w0) / (1 + al), (1 - al) / (1 + al)])
        best = {}
        for k in (0.3, 0.6, 1.0):
            zs = []
            for phi in range(0, 360, 15):
                # exact: L' = (R + k e^{j phi} BP) * CPD * G ; characteristic  rd*bpd*den + (rn*bpd + rd*k e^{j phi} bpn)*num*CPD = 0
                rn, rd = el289.R()
                Ln = A.padd(A.pmul(A.pmul(rn, bpd), pl.num) * CPD, A.pmul(A.pmul(rd, k * np.exp(1j * np.radians(phi)) * bpn), pl.num) * CPD)
                Ld = A.pmul(A.pmul(rd, bpd), pl.den)
                ch = A.padd(Ld, Ln); w = np.roots(ch[::-1]); w = w[np.abs(w) > 1e-12]
                z = 1 / w; s = np.log(z) * FS; fq = s.imag / (2 * np.pi); ze = -s.real / np.abs(s)
                m = (fq >= 8) & (fq <= 30)
                zs.append(np.min(ze[m]) if m.any() else np.nan)
            zs = np.array(zs); i = int(np.nanargmax(zs))
            best[k] = (15 * i, float(zs[i]))
        rows.append((p["label"], p["z289"], best))
    for lab, z9, best in rows:
        pr("    %-46s as-built zeta289 %+.3f | k0.3: phi %3d zeta %.3f | k0.6: phi %3d zeta %.3f | k1.0: phi %3d zeta %.3f" % (
            lab[:46], z9, best[0.3][0], best[0.3][1], best[0.6][0], best[0.6][1], best[1.0][0], best[1.0][1]))
    ax = [b[1.0][0] for _, _, b in rows]
    pr("    damping-axis phi (k=1.0) across the sub-family: p5/p50/p95 %.0f / %.0f / %.0f deg ; best zeta p5/p50/p95 %.3f %.3f %.3f" % (
        *np.percentile(ax, (5, 50, 95)), *np.percentile([b[1.0][1] for _, _, b in rows], (5, 50, 95))))
    return stab, unst


# --------------------------------------------------------------------------------------------------- Part B: rows
def build_candidates(c, c282):
    C = []

    def add(name, el, bytes_, cls):
        el.label = name; el.bytes_ = bytes_; el.cls = cls; C.append(el)
    # V289 integer notch ints (byte-read) as a generic biquad for cascades
    n289 = (np.array([c["b0"], c["b1"], c["b0"]], float) / c["a0"], np.array([c["a0"], c["a1"], c["a2"]], float) / c["a0"])
    add("1  V282 (revert)", Elec(c282), "0 (revert)", "baseline")
    kpre = 4; a = 1 - 2.0 ** -kpre
    add("1  V288 rev 2 (V282 loop + 10.3 Hz sp prefilter)", Elec(c282, prefilter=(np.array([1 - a]), np.array([1.0, -a]))), "V288 cave", "baseline")
    add("1  V289 rev 1 (notch 20.04 Q3 + fb 25)", Elec(c, notch289=True), "V289", "baseline")
    add("2  V282 + fb pole 25 Hz only (875/2301)", Elec(c), "4 cal", "cal-only")
    for fh in (20.0, 30.0, 35.0, 50.0):
        cc = dict(c282); cc["fb_a"], cc["fb_b"] = dc_held_pole(fh)
        add("2  V282 + fb pole %.0f Hz only (%d/%d)" % (fh, cc["fb_a"], cc["fb_b"]), Elec(cc), "4 cal", "cal-only")
    # 2b. OUTPUT-LAG pole 0xC63EC/EE raised (stock 992/507 = 5.05 Hz), DC held; on the V282 base and on the V289 base.
    #     STRUCK 2026-09-08 on gain margin / |dL| below 5 Hz -- re-derived here under the crossover picture.
    for fl in (8.0, 12.0, 20.0):
        la, lb = dc_held_lag(fl)
        cc = dict(c282); cc["lag_a"], cc["lag_b"] = la, lb
        add("3  V282 + OUTPUT-lag pole %.0f Hz (%d/%d) [STRUCK 09-08]" % (fl, la, lb), Elec(cc), "4 cal", "lag-pole")
        cc = dict(c); cc["lag_a"], cc["lag_b"] = la, lb
        add("3  V289 + OUTPUT-lag pole %.0f Hz (%d/%d) [STRUCK 09-08]" % (fl, la, lb), Elec(cc, notch289=True), "V289 + 4 cal", "lag-pole")
        cc = dict(c); cc["lag_a"], cc["lag_b"] = la, lb
        b, aa, _ = rbj("notch", 16.7, 3.0)
        add("3  notch16.7Q3 + fb25 + OUTPUT-lag %.0f Hz" % fl, Elec(cc, sumfilt=[(b, aa)]), "cave + 8 cal", "lag-pole")
    # 4b. LEAD / lead-lag on the sum node (cave hook 0x2A174), phase added at 12-22 Hz
    for fz, fp, fhf in ((8.0, 40.0, None), (10.0, 50.0, None), (12.0, 36.0, None), (8.0, 40.0, 40.0), (10.0, 50.0, 50.0),
                        (6.0, 60.0, 60.0), (12.0, 36.0, 36.0)):
        b, aa = leadlag(fz, fp, fhf)
        nm = "4  lead %.0f/%.0f Hz%s on S + fb 25" % (fz, fp, (" + LPF %.0f" % fhf) if fhf else "")
        add(nm, Elec(c, sumfilt=[(b, aa)]), "cave + 4 cal", "lead")
        add(nm.replace("+ fb 25", "(V282 cells)"), Elec(c282, sumfilt=[(b, aa)]), "cave", "lead")
    # 3. re-centred notch (fb 25 kept), Q3 and Q2, plus the walk
    for fc in (16.0, 16.5, 17.0, 17.5, 18.0, 19.0):
        for Q in (3.0, 2.0):
            b, aa, ints = rbj("notch", fc, Q)
            add("3  notch %.1f Hz Q%g + fb 25 (re-centred)" % (fc, Q), Elec(c, sumfilt=[(b, aa)]), "cave ints + 4 cal", "re-aim")
    # 3b. two notches: keep 20 + add 16.7
    b, aa, _ = rbj("notch", 16.7, 3.0)
    add("3b notch 20.04 Q3 + notch 16.7 Q3 + fb 25", Elec(c, sumfilt=[(b, aa)], notch289=True), "cave (2 biquads) + 4 cal", "re-aim")
    b, aa, _ = rbj("notch", 16.7, 2.0)
    add("3b notch 20.04 Q3 + notch 16.7 Q2 + fb 25", Elec(c, sumfilt=[(b, aa)], notch289=True), "cave (2 biquads) + 4 cal", "re-aim")
    # 5. wide low-Q notch / 2nd-order roll-off on S
    for fc, Q in ((18.0, 1.0), (18.5, 1.5), (19.0, 1.0), (17.5, 1.0)):
        b, aa, _ = rbj("notch", fc, Q)
        add("5  wide notch %.1f Hz Q%g + fb 25" % (fc, Q), Elec(c, sumfilt=[(b, aa)]), "cave + 4 cal", "wide")
        add("5  wide notch %.1f Hz Q%g (V282 cells)" % (fc, Q), Elec(c282, sumfilt=[(b, aa)]), "cave", "wide")
    for fc in (12.0, 15.0, 18.0):
        b, aa, _ = rbj("lpf", fc, 0.7071)
        add("5  2nd-order LPF %.0f Hz on S + fb 25" % fc, Elec(c, sumfilt=[(b, aa)]), "cave + 4 cal", "roll-off")
        cc = dict(c282); cc["fb_a"], cc["fb_b"] = dc_held_pole(35.0)
        add("5  2nd-order LPF %.0f Hz on S + fb 35" % fc, Elec(cc, sumfilt=[(b, aa)]), "cave + 4 cal", "roll-off")
    # 6. post-lag n term, OPPOSITE sign (g < 0) on V289 topology; the first memo's sign for reference
    for g in (-1 / 16, -1 / 8, -1 / 4, -1 / 2):
        add("6  V289 + post-lag +n*%g (OPPOSITE sign)" % (-g), Elec(c, g=g, notch289=True), "V289 + 2nd hook 0x2A1B0", "add-term")
    add("6  V289 + post-lag -n/8 (first memo's sign)", Elec(c, g=1 / 8, notch289=True), "V289 + 2nd hook", "add-term")
    # 6b. re-centred notch + opposite-sign n
    b, aa, _ = rbj("notch", 16.7, 3.0)
    for g in (-1 / 8, -1 / 4):
        add("6  notch 16.7 Q3 + fb 25 + post-lag +n*%g" % (-g), Elec(c, sumfilt=[(b, aa)], g=g), "cave + 2nd hook", "add-term")
    # 6c. V282 topology: post-lag BP of S (no notch) at 16.7 / 20 Hz Q3, both signs
    for fc in (16.7, 20.0):
        b, aa, _ = rbj("bpf", fc, 3.0)
        for gS in (0.125, 0.25, 0.5, -0.25):
            add("6  V282 + post-lag %+g*BP_S(%.1f Q3)" % (gS, fc), Elec(c282, sbp=(gS, (b, aa))), "cave + hook 0x2A1B0 + 2 RAM words", "add-term")
    # 6d. V282 topology: x-fed BP post-lag (T counts per rate count at the centre, via K*fade*kx)
    for fc in (16.7, 20.0):
        b, aa, _ = rbj("bpf", fc, 3.0)
        for kT in (0.5, 1.0, 2.0, -1.0):
            kx = kT / (c["gain"] / 32768.0) / (254 / 256)          # S counts per x count so that the T-node term is kT at the centre
            add("6  V282 + post-lag x-BP(%.1f Q3) kT %+g" % (fc, kT), Elec(c282, xbp=(kx, (b, aa))), "cave + hook + 2 RAM words", "add-term")
    # 7. Kd 96 (+ fb 25)
    cc = dict(c282); cc["kd_Y"] = [96] * 4; add("7  Kd 128->96 (V282 cells) [REJECTED CLASS]", Elec(cc), "8 cal", "D-cut")
    cc = dict(c); cc["kd_Y"] = [96] * 4; add("7  Kd 128->96 + fb 25 [REJECTED CLASS]", Elec(cc), "12 cal", "D-cut")
    cc = dict(c); cc["kd_Y"] = [64] * 4; add("7  Kd 128->64 + fb 25 [REJECTED CLASS]", Elec(cc), "12 cal", "D-cut")
    # 8. Kp lower
    for kp in (200, 160, 128):
        cc = dict(c282); cc["kp_Y"] = [kp] * 5; add("8  Kp 248->%d (V282 cells) [GAIN CLASS]" % kp, Elec(cc), "10 cal", "gain-cut")
        cc = dict(c); cc["kp_Y"] = [kp] * 5; add("8  Kp 248->%d + fb 25 [GAIN CLASS]" % kp, Elec(cc), "14 cal", "gain-cut")
    cc = dict(c); cc["kp_Y"] = [200] * 5
    b, aa, _ = rbj("notch", 16.7, 3.0)
    add("8  Kp 200 + notch 16.7 Q3 + fb 25", Elec(cc, sumfilt=[(b, aa)]), "cave + 14 cal", "gain-cut")
    return C


def _score_worker(args):
    ci, fits, c, c282 = args
    C = build_candidates(c, c282); el = C[ci]; el0 = C[0]
    rows = []
    for p in fits:
        pl = mkplant(p)
        m = metrics(el, pl, el0); m0 = step_lin(el0, pl); d0 = metrics(el0, pl, None, want_step=False)
        m["pkR_r"] = m["pkR"] / m0["pkR"]; m["pkA_r"] = m["pkA"] / m0["pkA"]; m["dc_r"] = m["dc"] / d0["dc"]
        m["S1014_r"] = m["S1014"] / d0["S1014"]; m["S2230_r"] = m["S2230"] / d0["S2230"]
        m["id"] = p["id"]
        rows.append(m)
    return ci, rows


def summarise(rows):
    z = np.array([r["z"] for r in rows]); f = np.array([r["f"] for r in rows])
    ok = np.isfinite(z)
    pm = np.array([r["pm"] for r in rows], float); wc = np.array([r["wc"] for r in rows], float)
    gmv = np.array([r["gm"] for r in rows], float); t9 = np.array([r.get("t90", np.nan) for r in rows], float)
    return dict(pm_min=float(np.nanmin(pm)), pm_med=float(np.nanmedian(pm)), wc_med=float(np.nanmedian(wc)),
                gm_min=float(np.nanmin(gmv)), t90_med=float(np.nanmedian(t9)),
                z_min=float(np.nanmin(z)) if ok.any() else np.nan, z_med=float(np.nanmedian(z)) if ok.any() else np.nan,
                f_at_min=float(f[np.nanargmin(z)]) if ok.any() else np.nan, f_med=float(np.nanmedian(f)) if ok.any() else np.nan,
                Ms_max=float(max(r["Ms"] for r in rows)), Ms_med=float(np.median([r["Ms"] for r in rows])),
                vm_min=float(min(r["vm"] for r in rows)),
                pkR_min=float(min(r["pkR_r"] for r in rows)), pkR_med=float(np.median([r["pkR_r"] for r in rows])),
                pkA_min=float(min(r["pkA_r"] for r in rows)), pkA_med=float(np.median([r["pkA_r"] for r in rows])),
                dc_min=float(min(r["dc_r"] for r in rows)), dc_med=float(np.median([r["dc_r"] for r in rows])),
                S1014_max=float(max(r["S1014"] for r in rows)), S2230_max=float(max(r["S2230"] for r in rows)),
                S1014r_max=float(max(r["S1014_r"] for r in rows)), S2230r_max=float(max(r["S2230_r"] for r in rows)),
                n_unst=int(sum(r["unst"] for r in rows)), n=len(rows))


HDR = ("  %-50s | %5s %5s %5s | %6s %5s | %6s %5s | %5s %5s | %5s | %6s %5s %4s | %5s %5s | %5s %5s | %5s %5s | %5s %5s | %5s | %5s | %-5s | %s")


def hdr():
    pr(HDR % ("candidate", "wc_md", "PM_w", "PM_md", "z_min", "@f", "z_med", "@f", "Ms_mx", "Ms_md", "vm_mn", "gate73", "d3.9", "dL<5",
              "pkR_m", "pkR_w", "pkA_m", "pkA_w", "dc_md", "dc_mn", "S1014", "S2230", "noise", "t90ms", "unst", "bytes"))


def row(el, s, pf):
    return HDR % (el.label[:50], "%.1f" % s["wc_med"], "%+.0f" % s["pm_min"], "%+.0f" % s["pm_med"],
                  "%+.3f" % s["z_min"], "%.1f" % s["f_at_min"], "%+.3f" % s["z_med"], "%.1f" % s["f_med"], "%.2f" % s["Ms_max"], "%.2f" % s["Ms_med"], "%.2f" % s["vm_min"],
                  "%.3f" % pf["gate"], "%+.1f" % pf["d39"], "%.0f%%" % (100 * pf["dlo"]), "%.2f" % s["pkR_med"], "%.2f" % s["pkR_min"], "%.2f" % s["pkA_med"], "%.2f" % s["pkA_min"],
                  "%.3f" % s["dc_med"], "%.3f" % s["dc_min"], "%.1fx" % s["S1014r_max"], "%.1fx" % s["S2230r_max"], "%.2f" % pf["noise"],
                  "%.0f" % s["t90_med"], "%d/%d" % (s["n_unst"], s["n"]), el.bytes_)


def cands(fam, nproc=NPROC, cap=400):
    c, c282 = cells()
    stab = [p for p in fam if p["z289"] >= Z289_STABLE]
    rng = np.random.RandomState(1)
    if len(stab) > cap:
        idx = rng.choice(len(stab), cap, replace=False); fits = [stab[i] for i in sorted(idx)]
    else:
        fits = stab
    C = build_candidates(c, c282); el0 = C[0]
    pr("\n" + "=" * 150)
    pr("B. CANDIDATES on the linear-stable family (%d of %d fits%s); z = least-damped pole 8-30 Hz; _m = median over fits, _w = worst" % (
        len(fits), len(stab), ", random subsample" if len(stab) > cap else ""))
    pr("   gate73 <= 1.01 passes; pkR/pkA = capped-step peak rate/accel vs V282 on the same fit (linear); dc = DC authority vs V282;")
    pr("   S1014/S2230 = worst ratio of the max sensitivity in 10-14 / 22-30 Hz vs V282 (new-peak check); noise = rms|R| 30-500 Hz vs V282")
    pr("=" * 150)
    t0 = time.time()
    with Pool(nproc) as pool:
        res = pool.map(_score_worker, [(i, fits, c, c282) for i in range(len(C))])
    allrows = {ci: rows for ci, rows in res}
    pr("  scored %d candidates x %d fits in %.0f s" % (len(C), len(fits), time.time() - t0))
    hdr()
    summ = {}
    for ci, el in enumerate(C):
        s = summarise(allrows[ci]); pf = plant_free(el, el0); summ[el.label] = dict(s=s, pf=pf, bytes=el.bytes_, cls=el.cls)
        pr(row(el, s, pf))
    return C, fits, allrows, summ


def recentre_walk(fits, c, c282):
    """row 3 iteration: start the notch at 20.04 -> read the pole -> re-centre there -> ... ; per fit, then median/range."""
    pr("\n  --- 3. THE RE-AIM WALK: notch centre := median pole of the previous step (Q3, fb 25); per-fit poles ---")
    fc = 20.036; hist = []
    for it in range(6):
        b, aa, _ = (rbj("notch", fc, 3.0) if it else (None, None, None))
        el = Elec(c, notch289=True) if it == 0 else Elec(c, sumfilt=[(b, aa)])
        fs, zs = [], []
        for p in fits:
            m = least_damped(*poles_of(el, mkplant(p))[:2], 8.0, 30.0); fs.append(m[0]); zs.append(m[1])
        fs, zs = np.array(fs), np.array(zs)
        pr("    step %d: notch at %.2f Hz -> pole f p5/p50/p95 %.1f / %.1f / %.1f Hz, zeta p5/p50/p95 %+.3f / %+.3f / %+.3f, unstable on %d/%d" % (
            it, fc, *np.nanpercentile(fs, (5, 50, 95)), *np.nanpercentile(zs, (5, 50, 95)), int(np.sum(zs < 0)), len(zs)))
        hist.append((fc, float(np.nanmedian(fs))))
        fc_new = float(np.nanmedian(fs))
        if abs(fc_new - fc) < 0.15:
            pr("    fixed point: notch centre == pole at %.2f Hz" % fc_new); break
        fc = fc_new
    return hist


def joint_solve(fits, c, c282, nproc=NPROC):
    """row 4: (f_notch, Q, fb pole) grid; objective = worst-case zeta over fits s.t. gate<=1.01, median pkR>=0.95, stable."""
    pr("\n  --- 4. JOINT (notch f, Q, fb pole) SOLVE -- worst-case zeta over the family, constraints gate73 <= 1.01, pkR_med >= 0.95, no unstable fit ---")
    grid = []
    for fc in np.arange(15.0, 22.51, 0.5):
        for Q in (1.5, 2.0, 3.0, 4.0):
            for fh in (16.53, 20.0, 25.0, 30.0, 35.0, 40.0):
                grid.append((float(fc), float(Q), float(fh)))
    sub = fits[:: max(1, len(fits) // 120)]
    with Pool(nproc) as pool:
        res = pool.map(_joint_worker, [(g, sub) for g in grid])
    res = [r for r in res if r is not None]
    res.sort(key=lambda r: -r["z_min"])
    pr("    %-32s | %6s %6s | %6s | %6s %5s | %6s | %5s %5s | %s" % ("notch f / Q / fb pole", "z_min", "z_med", "PM_w", "f_med", "Ms", "gate73", "pkR", "dc", "unst"))
    for r in res[:14]:
        pr("    %5.1f Hz  Q%.1f  fb %4.1f Hz          | %6.3f %6.3f | %+6.1f | %6.1f %5.2f | %6.3f | %5.2f %5.3f | %d" % (
            r["fc"], r["Q"], r["fh"], r["z_min"], r["z_med"], r["pm_min"], r["f_med"], r["Ms_max"], r["gate"], r["pkR_med"], r["dc_med"], r["n_unst"]))
    ok = [r for r in res if r["gate"] <= 1.01 and r["pkR_med"] >= 0.95 and r["n_unst"] == 0]
    pr("    feasible (gate<=1.01, pkR_med>=0.95, all stable): %d of %d combos; best worst-case zeta %s" % (
        len(ok), len(res), ("%.3f at %.1f Hz Q%.1f fb %.1f" % (ok[0]["z_min"], ok[0]["fc"], ok[0]["Q"], ok[0]["fh"])) if ok else "NONE"))
    return res, ok


def _joint_worker(args):
    (fc, Q, fh), sub = args
    c, c282 = cells()
    cc = dict(c282); cc["fb_a"], cc["fb_b"] = dc_held_pole(fh)
    b, aa, _ = rbj("notch", fc, Q)
    el = Elec(cc, sumfilt=[(b, aa)]); el0 = Elec(c282)
    pf = plant_free(el, el0)
    zs, fs, ms, pk, dc, un, pms = [], [], [], [], [], 0, []
    for p in sub:
        pl = mkplant(p); m = metrics(el, pl, el0); m0 = step_lin(el0, pl); d0 = metrics(el0, pl, None, False)
        zs.append(m["z"]); fs.append(m["f"]); ms.append(m["Ms"]); pk.append(m["pkR"] / m0["pkR"]); dc.append(m["dc"] / d0["dc"]); un += m["unst"]
        pms.append(m["pm"])
    return dict(fc=fc, Q=Q, fh=fh, z_min=float(np.nanmin(zs)), z_med=float(np.nanmedian(zs)), f_med=float(np.nanmedian(fs)), Ms_max=float(np.max(ms)),
                pm_min=float(np.nanmin(pms)), gate=pf["gate"], pkR_med=float(np.median(pk)), dc_med=float(np.median(dc)), n_unst=int(un))


def dose_sweep(fits, c, c282):
    """row 6: the opposite-sign post-lag term, dose sweep, where it becomes a spring (pole f moves, zeta stops rising)."""
    pr("\n  --- 6. OPPOSITE-SIGN POST-LAG TERM, dose sweep (V289 topology: y' = y + g*n ; n = the notched-out component) ---")
    sub = fits[:: max(1, len(fits) // 60)]
    pr("    %-10s | %-40s | %-40s" % ("g", "pole f p5/p50/p95 Hz", "zeta p5/p50/p95  (unstable count)"))
    for g in (0.0, 1 / 32, 1 / 16, 1 / 8, 3 / 16, 1 / 4, 3 / 8, 1 / 2, 3 / 4, 1.0):
        el = Elec(c, g=-g, notch289=True)
        fs, zs = [], []
        for p in sub:
            f0, z0 = least_damped(*poles_of(el, mkplant(p))[:2], 8.0, 30.0); fs.append(f0); zs.append(z0)
        pr("    +n*%-6.4f | %5.1f / %5.1f / %5.1f                     | %+.3f / %+.3f / %+.3f  (%d)" % (
            g, *np.nanpercentile(fs, (5, 50, 95)), *np.nanpercentile(zs, (5, 50, 95)), int(np.sum(np.array(zs) < 0))))
    pr("    positive control (advphys): a constant rate-feedback term on a delay-free collocated plant gives zeta' = zeta/sqrt(1+k) -- a SPRING.")
    pr("    the regime where pole f moves by > 1 Hz while zeta stops rising is the spring regime; read it off the table above.")
    pr("\n    same term on the V282 topology (no notch): y' = y + gS*BP_S(fc, Q3), post-lag, S-fed")
    for fc in (16.7, 20.0):
        b, aa, _ = rbj("bpf", fc, 3.0)
        for gS in (0.0625, 0.125, 0.25, 0.5, 1.0):
            el = Elec(c282, sbp=(gS, (b, aa)))
            fs, zs = [], []
            for p in sub:
                f0, z0 = least_damped(*poles_of(el, mkplant(p))[:2], 8.0, 30.0); fs.append(f0); zs.append(z0)
            pr("    BP_S %.1f Hz gS %+.4f | f %5.1f / %5.1f / %5.1f | zeta %+.3f / %+.3f / %+.3f (%d unstable)" % (
                fc, gS, *np.nanpercentile(fs, (5, 50, 95)), *np.nanpercentile(zs, (5, 50, 95)), int(np.sum(np.array(zs) < 0))))


def search_row9(fits, c, c282, nproc=NPROC):
    """row 10 of the brief: the CONSTRAINED SEARCH over (Kp, Kd, notch, fb pole, OUTPUT-lag pole, lead, post-lag g) for
    PM >= 40 deg  OR  worst-fit zeta >= 0.08, with pkR_min >= 0.95 and 7 Hz gate <= 1.01 on the WORST fit."""
    pr("\n  --- 10. CONSTRAINED SEARCH: any combination with WORST-fit PM >= 40 deg (or zeta >= 0.08), pkR >= 0.95, gate73 <= 1.01, all stable? ---")
    LEADS = [None, (8.0, 40.0, None), (10.0, 50.0, None), (12.0, 36.0, None), (8.0, 40.0, 40.0), (10.0, 50.0, 50.0)]
    combos = []
    for kp in (248, 220, 200, 160):
        for kd in (128, 96):
            for nf in (None, (16.7, 3.0), (17.5, 2.0), (18.5, 1.5), (20.04, 3.0), (18.0, 1.0)):
                for fh in (16.53, 25.0, 35.0):
                    for fl in (5.05, 8.0, 12.0):
                        for ld in LEADS:
                            for g in (0.0, -1 / 8):
                                if nf is None and g != 0.0:
                                    continue
                                if ld is not None and (nf is not None or g != 0.0):
                                    continue         # keep the lead rows single-lever so the attribution is readable
                                combos.append((kp, kd, nf, fh, fl, ld, g))
    sub = fits[:: max(1, len(fits) // 60)]
    with Pool(nproc) as pool:
        res = pool.map(_r9_worker, [(cb, sub) for cb in combos])
    res = [r for r in res if r is not None]
    hard = [r for r in res if r["gate"] <= 1.01 and r["pkR_min"] >= 0.95 and r["n_unst"] == 0]
    feasPM = [r for r in hard if r["pm_min"] >= 40.0]
    feasZ = [r for r in hard if r["z_min"] >= 0.08]
    res.sort(key=lambda r: -r["pm_min"]); hard.sort(key=lambda r: -r["pm_min"])
    pr("    %d combos evaluated on %d fits.  Passing the AUTHORITY gates (pkR_min >= 0.95, gate73 <= 1.01, all stable): %d" % (len(res), len(sub), len(hard)))
    pr("    Of those, PM_worst >= 40 deg: %d      zeta_worst >= 0.08: %d" % (len(feasPM), len(feasZ)))
    HH = "    %-56s | %5s %6s %6s | %6s %6s | %5s | %6s | %5s %5s | %5s | %5s | %s"
    pr(HH % ("combo", "wc", "PM_w", "PM_md", "z_min", "z_med", "f_med", "gate73", "pkR_m", "pkR_w", "dc_md", "Ms", "unst"))
    pr("    -- best PM among the rows that PASS the authority gates --")
    for r in hard[:14]:
        pr(HH % (r["name"][:56], "%.1f" % r["wc_med"], "%+.1f" % r["pm_min"], "%+.1f" % r["pm_med"], "%+.3f" % r["z_min"], "%+.3f" % r["z_med"],
                 "%.1f" % r["f_med"], "%.3f" % r["gate"], "%.2f" % r["pkR_med"], "%.2f" % r["pkR_min"], "%.3f" % r["dc_med"], "%.2f" % r["Ms_max"], r["n_unst"]))
    pr("    -- best PM overall, IGNORING the authority gates (what the ceiling would cost) --")
    for r in res[:8]:
        pr(HH % (r["name"][:56], "%.1f" % r["wc_med"], "%+.1f" % r["pm_min"], "%+.1f" % r["pm_med"], "%+.3f" % r["z_min"], "%+.3f" % r["z_med"],
                 "%.1f" % r["f_med"], "%.3f" % r["gate"], "%.2f" % r["pkR_med"], "%.2f" % r["pkR_min"], "%.3f" % r["dc_med"], "%.2f" % r["Ms_max"], r["n_unst"]))
    bz = sorted(res, key=lambda r: -r["z_min"])
    pr("    -- best worst-case zeta overall, ignoring the authority gates --")
    for r in bz[:6]:
        pr(HH % (r["name"][:56], "%.1f" % r["wc_med"], "%+.1f" % r["pm_min"], "%+.1f" % r["pm_med"], "%+.3f" % r["z_min"], "%+.3f" % r["z_med"],
                 "%.1f" % r["f_med"], "%.3f" % r["gate"], "%.2f" % r["pkR_med"], "%.2f" % r["pkR_min"], "%.3f" % r["dc_med"], "%.2f" % r["Ms_max"], r["n_unst"]))
    pr("    HEADLINE: a combination meeting PM_worst >= 40 deg AND pkR_min >= 0.95 AND gate73 <= 1.01 %s" % (
        "EXISTS: " + feasPM[0]["name"] if feasPM else "DOES NOT EXIST in this space."))
    return res, hard


def _r9_worker(args):
    (kp, kd, nf, fh, fl, ld, g), sub = args
    c, c282 = cells()
    cc = dict(c282); cc["kp_Y"] = [kp] * 5; cc["kd_Y"] = [kd] * 4; cc["fb_a"], cc["fb_b"] = dc_held_pole(fh)
    if abs(fl - 5.05) > 0.01:
        cc["lag_a"], cc["lag_b"] = dc_held_lag(fl)
    sf = None
    if nf:
        b, aa, _ = rbj("notch", nf[0], nf[1]); sf = [(b, aa)]
    if ld:
        b, aa = leadlag(*ld); sf = [(b, aa)]
    el = Elec(cc, sumfilt=sf, g=g); el0 = Elec(c282)
    pf = plant_free(el, el0)
    zs, fs, ms, pk, dc, un, pms, wcs = [], [], [], [], [], 0, [], []
    for p in sub:
        pl = mkplant(p); m = metrics(el, pl, el0); m0 = step_lin(el0, pl); d0 = metrics(el0, pl, None, False)
        zs.append(m["z"]); fs.append(m["f"]); ms.append(m["Ms"]); pk.append(m["pkR"] / m0["pkR"]); dc.append(m["dc"] / d0["dc"]); un += m["unst"]
        pms.append(m["pm"]); wcs.append(m["wc"])
    name = "Kp%d Kd%d %s fb%.0f lag%.1f%s%s" % (kp, kd, ("nt%.1fQ%.1f" % nf) if nf else "no-notch", fh, fl,
                                                (" lead%.0f/%.0f%s" % (ld[0], ld[1], "+lpf" if ld[2] else "")) if ld else "",
                                                (" n*%+.3f" % (-g)) if g else "")
    return dict(name=name, z_min=float(np.nanmin(zs)), z_med=float(np.nanmedian(zs)), f_med=float(np.nanmedian(fs)), Ms_max=float(np.max(ms)),
                pm_min=float(np.nanmin(pms)), pm_med=float(np.nanmedian(pms)), wc_med=float(np.nanmedian(wcs)),
                gate=pf["gate"], pkR_med=float(np.median(pk)), pkR_min=float(np.min(pk)), dc_med=float(np.median(dc)), n_unst=int(un))


def mirror_rows(fits, allrows, C, c, c282):
    """integer mirror capped step on three fits: the median-zeta fit for V289, the worst fit, and a mode-pulled fit."""
    pr("\n  --- INTEGER MIRROR (byte-exact arithmetic, V850 sar floors): capped-frame step %d sp on 3 fits; pkR/pkA vs V282 on the same fit ---" % STEP_SP)
    z289 = np.array([p["z289"] for p in fits]); order = np.argsort(z289)
    picks = [("worst-zeta289 fit", fits[order[0]]), ("median-zeta289 fit", fits[order[len(order) // 2]]), ("best-zeta289 fit", fits[order[-1]])]
    n289 = ([c["b0"], c["b1"], c["b0"]], [c["a0"], c["a1"], c["a2"]])
    specs = [("V282", c282, {}), ("V288 rev 2 (prefilter k4)", c282, dict(prefilter_k=4)), ("V289", c, dict(sumints=[n289])),
             ("V282 + fb 25", c, {}),
             ("notch 16.7 Q3 + fb 25", c, dict(sumints=[rbj("notch", 16.7, 3.0)[2]])),
             ("notch 17.5 Q2 + fb 25", c, dict(sumints=[rbj("notch", 17.5, 2.0)[2]])),
             ("wide notch 18.5 Q1.5 + fb 25", c, dict(sumints=[rbj("notch", 18.5, 1.5)[2]])),
             ("V289 + post-lag +n/8", c, dict(sumints=[n289], npost_g8=-32)),
             ("V289 + post-lag +n/4", c, dict(sumints=[n289], npost_g8=-64)),
             ("V282 + BP_S 16.7 Q3 gS +1/4", c282, dict(sbp=(64, rbj("bpf", 16.7, 3.0)[2]))),
             ("Kd 96 + fb 25", dict(c, kd_Y=[96] * 4), {}),
             ("Kp 200 + fb 25", dict(c, kp_Y=[200] * 5), {}),
             ("Kp 160 + fb 25", dict(c, kp_Y=[160] * 5), {}),
             ("Kp 128 + fb 25", dict(c, kp_Y=[128] * 5), {}),
             ("Kp 200 Kd 96 + fb 25", dict(c, kp_Y=[200] * 5, kd_Y=[96] * 4), {}),
             ("V282 + OUTPUT-lag 8 Hz", dict(c282, lag_a=dc_held_lag(8.0)[0], lag_b=dc_held_lag(8.0)[1]), {}),
             ("V282 + OUTPUT-lag 12 Hz", dict(c282, lag_a=dc_held_lag(12.0)[0], lag_b=dc_held_lag(12.0)[1]), {}),
             ("V289 + OUTPUT-lag 12 Hz", dict(c, lag_a=dc_held_lag(12.0)[0], lag_b=dc_held_lag(12.0)[1]), dict(sumints=[n289])),
             ("lead 10/50 Hz on S + fb 25", c, dict(sumints=[q14(*leadlag(10.0, 50.0))])),
             ("lead 10/50+LPF50 on S + fb 25", c, dict(sumints=[q14(*leadlag(10.0, 50.0, 50.0))]))]
    for pn, p in picks:
        pl = mkplant(p)
        pr("    plant: %s -- %s (zeta289 %+.3f)" % (pn, p["label"], p["z289"]))
        base = None
        for nm, cc, kw in specs:
            r = mirror_step(cc, pl, kw)
            if base is None:
                base = r
            pr("      %-34s pkR %6.2f (x%.3f)  pkA %7.1f (x%.3f)  ss %6.2f (x%.3f)  pk|T| %4.0f" % (
                nm, r["pkR"], r["pkR"] / base["pkR"], r["pkA"], r["pkA"] / base["pkA"], r["ss"], r["ss"] / base["ss"] if base["ss"] else np.nan, r["pkT"]))


def frontier(fits, c, c282, nproc=NPROC):
    """The AUTHORITY FRONTIER in the only plane where the full search left a row unresolved: (Kd, fb pole).  Kd 96 alone
    passes the operator's authority floor (dc x1.000, pkR_med 0.94) but fails the 7 Hz gate at 1.073; adding fb 25 Hz
    buys the gate back (1.004) and spends pkR (0.88).  This sweeps the plane between them looking for any cell with
    gate73 <= 1.01 AND pkR_med >= 0.95 AND dc >= 0.995 AND zero unstable fits, and reports the best zeta there."""
    pr("")
    pr("  --- 10b. AUTHORITY FRONTIER in the (Kd, fb pole) plane -- the one region the full search left unresolved ---")
    pr("      constraints: 7 Hz gate <= 1.01, capped-step pkR_med >= 0.95, DC authority >= 0.995, no unstable fit over the family")
    grid = [(kd, fh) for kd in (128, 120, 112, 104, 96, 88, 80) for fh in (16.53, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 25.0, 28.0)]
    sub = fits[:: max(1, len(fits) // 80)]
    with Pool(nproc) as pool:
        res = pool.map(_front_worker, [(g, sub) for g in grid])
    pr("      %-22s | %6s %6s | %6s | %6s | %5s %5s | %6s | %5s | %5s | %s" % (
        "Kd / fb pole", "z_min", "z_med", "PM_w", "gate73", "pkR_m", "pkR_w", "dc_med", "Ms_mx", "noise", "FEASIBLE"))
    ok = []
    for r in res:
        f = (r["gate"] <= 1.01) and (r["pkR_med"] >= 0.95) and (r["dc_med"] >= 0.995) and r["n_unst"] == 0
        if f:
            ok.append(r)
        pr("      Kd %3d  fb %5.2f Hz    | %+6.3f %+6.3f | %+6.1f | %6.3f | %5.2f %5.2f | %6.3f | %5.2f | %5.2f | %s" % (
            r["kd"], r["fh"], r["z_min"], r["z_med"], r["pm_min"], r["gate"], r["pkR_med"], r["pkR_min"], r["dc_med"], r["Ms_max"], r["noise"],
            "YES" if f else ""))
    ok.sort(key=lambda r: -r["z_med"])
    if ok:
        b = ok[0]
        pr("      FEASIBLE CELLS: %d.  Best by median zeta: Kd %d, fb %.2f Hz -- zeta_med %+.3f (V282 %+.3f), zeta_worst %+.3f, gate %.3f, pkR %.2f, dc %.3f" % (
            len(ok), b["kd"], b["fh"], b["z_med"], res[0]["z_med"], b["z_min"], b["gate"], b["pkR_med"], b["dc_med"]))
    else:
        pr("      FEASIBLE CELLS: NONE.  The (Kd, fb pole) plane contains no point that improves damping inside the authority floor.")
    return res, ok


def _front_worker(args):
    (kd, fh), sub = args
    c, c282 = cells()
    cc = dict(c282); cc["kd_Y"] = [kd] * 4; cc["fb_a"], cc["fb_b"] = dc_held_pole(fh)
    el = Elec(cc); el0 = Elec(c282)
    pf = plant_free(el, el0)
    zs, ms, pk, dc, un, pms = [], [], [], [], 0, []
    for p in sub:
        pl = mkplant(p); m = metrics(el, pl, el0); m0 = step_lin(el0, pl); d0 = metrics(el0, pl, None, False)
        zs.append(m["z"]); ms.append(m["Ms"]); pk.append(m["pkR"] / m0["pkR"]); dc.append(m["dc"] / d0["dc"]); un += m["unst"]; pms.append(m["pm"])
    return dict(kd=kd, fh=fh, z_min=float(np.nanmin(zs)), z_med=float(np.nanmedian(zs)), pm_min=float(np.nanmin(pms)),
                Ms_max=float(np.max(ms)), gate=pf["gate"], noise=pf["noise"],
                pkR_med=float(np.median(pk)), pkR_min=float(np.min(pk)), dc_med=float(np.median(dc)), n_unst=int(un))


def ring_table(summ):
    pr("\n  --- E. RING LENGTH in the operator's terms, from zeta (worst / median over the family) at the candidate's own pole frequency ---")
    pr("    %-52s | %-26s | %-26s" % ("candidate", "WORST fit: cycles / ms to e-fold, to 10%", "MEDIAN fit: same"))
    for lab, d in summ.items():
        s = d["s"]
        def rl(z, f):
            if not np.isfinite(z) or z <= 0:
                return "does not decay (unstable)"
            ce = 1 / (2 * np.pi * z); c10 = np.log(10) / (2 * np.pi * z)
            return "%4.1f cyc %4.0f ms / %4.1f cyc %4.0f ms" % (ce, 1e3 * ce / f, c10, 1e3 * c10 / f)
        pr("    %-52s | %-26s | %-26s" % (lab[:52], rl(s["z_min"], s["f_at_min"]), rl(s["z_med"], s["f_med"])))


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    c, c282 = cells()
    pr("design290b_candidates -- image %s ; V289 cells fb %d/%d lag %d/%d gain %d Kp %s Kd %s ; notch ints b0 %d b1 %d a2 %d" % (
        c["path"][:50], c["fb_a"], c["fb_b"], c["lag_a"], c["lag_b"], c["gain"], c["kp_Y"], c["kd_Y"], c["b0"], c["b1"], c["a2"]))
    famp = os.path.join(SCR, "design290b_family.json")
    if what in ("family", "all") or not os.path.exists(famp):
        fam = family(); fam = refine(fam)
    else:
        fam = json.load(open(famp))
        if not any(p.get("refined") for p in fam):
            fam = refine(fam)
    stab, unst = report_family(fam)
    if what == "family":
        open(os.path.join(SCR, "design290b_family.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n"); return
    C, fits, allrows, summ = cands(fam)
    recentre_walk(fits[:: max(1, len(fits) // 80)], c, c282)
    jres, jok = joint_solve(fits, c, c282)
    dose_sweep(fits, c, c282)
    r9, feas = search_row9(fits, c, c282)
    fres, fok = frontier(fits, c, c282)
    mirror_rows(fits, allrows, C, c, c282)
    ring_table(summ)
    json.dump(dict(summary=summ, joint=jres[:40], row9=r9[:60], row9_feasible=feas[:40]), open(os.path.join(SCR, "design290b_cands.json"), "w"), indent=0, default=float)
    open(os.path.join(SCR, "design290b_cands.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/design290b_cands.txt")


if __name__ == "__main__":
    main()
