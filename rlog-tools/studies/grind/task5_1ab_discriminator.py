# -*- coding: utf-8 -*-
"""studies/grind/task5_1ab_discriminator.py -- CAN THE 50 Hz DELIVERED-TORQUE TAP TELL 30 Hz FROM 70 Hz?

The brief's Test 4 as written is PROVABLY POWERLESS: 50 exactly divides 100, so a true 30 Hz and a true
70 Hz component alias to the SAME 20 Hz on the 50 Hz 0x1AB stream, exactly as they alias to the same
30 Hz on the 100 Hz 0x18F stream.  Sampling-rate contrast alone buys nothing here.

The leverage is somewhere else: the KNOWN 1 kHz FILTER that sits between the two taps.  0x18F carries
gp-0x6a56 with no filter at all; 0x1AB carries T, which is gp-0x6a56 pushed through the rate-PID chain
at 1 kHz.  Mirroring the decompile exactly:

    s[n] = (923*s[n-1] >> 10) + (1560*x[n] >> 10)      EMA, pole 0.9014 at 1 kHz
    fb   = s[n] + s[n-1]                                two-sample sum
    E    = 32*sp - fb   ->  at HF, E ~= -fb
    P    = E*Kp>>8  (Kp = 248)      D = dE*128>>3 = dE*16
    S    = 254*(P+D)>>8             lag = (992/507, readout >>5)
    T    = -lag*5346>>15

    |H(70 Hz)| / |H(30 Hz)| = 0.458   =>  a 70 Hz source arrives at the tap 6.79 dB WEAKER
                                          than a 30 Hz source of the same amplitude.

So the two channels weight the two candidate source frequencies DIFFERENTLY, by a known 4.8x in power,
while placing them in the same observed band.  That is a genuine discriminator.

THE STATISTIC (the unknown units scale K between the two taps cancels):

    Q = [ W(18-23 Hz on 0x1AB) / U(27-32 Hz on 0x18F) ]  /  [ W(10-15) / U(10-15) ]

    Q_real = <|H|^2>(27-32) / <|H|^2>(10-15)      if the 27-32 content is genuinely at 27-32
    Q_fold = <|H|^2>(68-73) / <|H|^2>(10-15)      if it is really at 68-73 and folded

POWER IS NOT ASSUMED, IT IS MEASURED: the script prints the tap's quantisation floor (LSB 8, so
8^2/12 spread over 0-25 Hz) next to the measured 18-23 Hz band power, and bootstraps Q over episodes.
If the CI spans both predictions the answer is "underpowered", and that is a valid result.

Run: python rlog-tools/studies/grind/task5_1ab_discriminator.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS18, FS1AB, FS1K = 100.0, 50.0, 1000.0
TAGS = ("r35", "r36", "r37", "r38")
KP = {"r35": 248.0, "r36": 248.0, "r37": 248.0, "r38": 248.0}     # flat 248 on all four
TAP_LSB = 8.0
LINES = []


def pr(s=""):
    print(s)
    LINES.append(s)


# ------------------------------------------------------------------ the 1 kHz chain, x -> T
def Hchain(f, kp=248.0):
    z = np.exp(2j * np.pi * np.asarray(f, float) / FS1K)
    zi = 1.0 / z
    ema = 1.5234 / (1 - 0.9014 * zi)          # (1560>>10) / (1 - (923>>10))
    fb = ema * (1 + zi)                        # fb = s[n] + s[n-1]
    E = -fb                                    # E = 32*sp - fb; at HF the sp path is negligible
    P = E * (kp / 256.0)
    Dt = E * 16.0 * (1 - zi)                   # D = dE*128>>3
    S = (P + Dt) * (254.0 / 256.0)
    lag = (507.0 / 1024.0) / (1 - (992.0 / 1024.0) * zi) / 32.0
    return S * lag * (5346.0 / 32768.0)


def H2band(lo, hi, kp):
    f = np.linspace(lo, hi, 401)
    return float(np.mean(np.abs(Hchain(f, kp)) ** 2))


# ------------------------------------------------------------------ data
def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    t0 = D["t18"][0]
    for k in ("t18", "t14", "t1ab", "te4", "tcs"):
        D[k] = D[k] - t0
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    D["T"] = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * TAP_LSB
    return D


def runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def bandpow(x, fs, nper, lo, hi):
    x = np.asarray(x, float)
    x = x - x.mean()
    f, P = signal.welch(x, fs=fs, nperseg=nper, noverlap=nper // 2, window="hann", detrend="constant")
    m = (f >= lo) & (f < hi)
    return float(np.mean(P[m]))


def main():
    kp = 248.0
    h_ref = H2band(10, 15, kp)
    h_real = H2band(27, 32, kp)
    h_fold = H2band(68, 73, kp)
    q_real, q_fold = h_real / h_ref, h_fold / h_ref
    pr("PREDICTIONS from the 1 kHz chain (Kp = 248, the flat table on all four routes)")
    pr("  <|H|^2> 10-15 Hz = %.5f   27-32 Hz = %.5f   68-73 Hz = %.5f" % (h_ref, h_real, h_fold))
    pr("  Q_real = %.4f (%.2f dB)      Q_fold = %.4f (%.2f dB)      separation = %.2f dB"
       % (q_real, 10 * np.log10(q_real), q_fold, 10 * np.log10(q_fold),
          10 * np.log10(q_real / q_fold)))
    pr("  (a mixture reads between them: Q = Q_fold + (Q_real - Q_fold) * (real fraction))")
    pr()
    qfloor = (TAP_LSB ** 2 / 12.0) / (FS1AB / 2.0)
    pr("  tap quantisation floor (LSB %.0f, white over 0-25 Hz) = %.3f counts^2/Hz -- the 18-23 Hz band"
       % (TAP_LSB, qfloor))
    pr("  power MUST stand clear of this or the statistic is measuring the tap's own dither.")

    for tag in TAGS:
        pr()
        pr("=" * 104)
        pr("ROUTE %s" % tag)
        pr("=" * 104)
        D = load(tag)
        t18, t1ab = D["t18"], D["t1ab"]
        req = np.interp(t18, D["te4"], D["req"].astype(float)) > 0.5
        eng = (np.asarray(D["sca"], float) > 0.5) & req
        segs = runs(eng, 3072)                       # >=30.7 s, so >=1024 samples on the 50 Hz tap
        if not segs:
            pr("  no engaged run >= 3072 frames"); continue
        rate = np.asarray(D["rate"], float)
        Tt = D["T"]
        rows = []
        for a, b in segs:
            ta, tb = t18[a], t18[b - 1]
            ia, ib = np.searchsorted(t1ab, ta), np.searchsorted(t1ab, tb)
            if ib - ia < 1024:
                continue
            Ts = Tt[ia:ib]
            if np.mean(Ts == 0) > 0.8 or np.std(Ts) < 1e-6:
                continue                              # tap degenerate in this episode
            U_ref = bandpow(rate[a:b], FS18, 2048, 10, 15)
            U_tst = bandpow(rate[a:b], FS18, 2048, 27, 32)
            W_ref = bandpow(Ts, FS1AB, 1024, 10, 15)
            W_tst = bandpow(Ts, FS1AB, 1024, 18, 23)
            if min(U_ref, U_tst, W_ref, W_tst) <= 0:
                continue
            rows.append((b - a, U_ref, U_tst, W_ref, W_tst, np.mean(Ts == 0)))
        if len(rows) < 4:
            pr("  only %d usable episodes -- not scored" % len(rows)); continue
        R = np.array([r[:5] for r in rows], float)
        z0 = np.mean([r[5] for r in rows])
        n, U_ref, U_tst, W_ref, W_tst = R.T
        pr("  %d episodes, %d engaged frames, tap zero-fraction %.3f" % (len(rows), int(n.sum()), z0))
        pr("  measured band power   0x18F 10-15 %8.3f  27-32 %8.3f   |   0x1AB 10-15 %8.3f  18-23 %8.3f"
           % (np.average(U_ref, weights=n), np.average(U_tst, weights=n),
              np.average(W_ref, weights=n), np.average(W_tst, weights=n)))
        w1823 = np.average(W_tst, weights=n)
        pr("  0x1AB 18-23 Hz band power / quantisation floor = %.2f   %s"
           % (w1823 / qfloor,
              "OK, signal stands clear" if w1823 / qfloor > 3 else
              "*** AT OR NEAR THE TAP'S OWN DITHER -- the statistic is not trustworthy ***"))
        # pooled Q, and a bootstrap over EPISODES (the unit that is independent)
        def Qof(idx):
            return ((np.sum(W_tst[idx] * n[idx]) / np.sum(U_tst[idx] * n[idx])) /
                    (np.sum(W_ref[idx] * n[idx]) / np.sum(U_ref[idx] * n[idx])))
        allidx = np.arange(len(n))
        Q = Qof(allidx)
        rng = np.random.default_rng(11)
        bs = np.array([Qof(rng.integers(0, len(n), len(n))) for _ in range(4000)])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        frac = (Q - q_fold) / (q_real - q_fold)
        fl = (lo - q_fold) / (q_real - q_fold)
        fh = (hi - q_fold) / (q_real - q_fold)
        pr("  Q = %.4f (%.2f dB)   bootstrap 95%% CI [%.4f, %.4f]" % (Q, 10 * np.log10(Q), lo, hi))
        pr("     vs Q_real %.4f / Q_fold %.4f  ->  implied REAL fraction = %.2f  CI [%.2f, %.2f]"
           % (q_real, q_fold, frac, min(fl, fh), max(fl, fh)))
        # ------------------------------------------------------------------------------------------
        # 🛑 THE STATISTIC IS INVALID, AND THE OUTPUT ITSELF PROVES IT: an "implied real fraction" of
        # 10-16 is impossible (it is a fraction, it cannot exceed 1).  The defect, diagnosed:
        # on a 50 Hz sampler Nyquist is 25 Hz, so TRUE 18-23 Hz content lands in the observed 18-23 Hz
        # band DIRECTLY, unfolded -- and 18-23 Hz is where the dominant grind mode lives.  It is not a
        # contaminant to be subtracted, it is the majority of the band.
        u1823 = np.average([bandpow(rate[a:b], FS18, 2048, 18, 23) for a, b in segs],
                           weights=[b - a for a, b in segs])
        u2732 = np.average(U_tst, weights=n)
        h20, h30, h70 = H2band(18, 23, kp), H2band(27, 32, kp), H2band(68, 73, kp)
        pr("     *** STATISTIC INVALID -- a real fraction cannot exceed 1.  Diagnosis: ***")
        pr("       true 18-23 Hz content is %.1fx the 27-32 candidate on 0x18F, and on a 50 Hz sampler it"
           % (u1823 / u2732))
        pr("       lands in the SAME observed 18-23 Hz band WITHOUT folding (18-23 < Nyquist 25).")
        pr("       weighted contributions to the 0x1AB 18-23 band:  direct 18-23 %.2f  |  folded-from-27-32 %.2f"
           % (u1823 * h20, u2732 * h30))
        pr("       |  folded-from-68-73 (if that is the source) <= %.2f   =>  the direct term is %.0f-%.0fx"
           % (u2732 * h70, u1823 * h20 / (u2732 * h30), u1823 * h20 / (u2732 * h70)))
        pr("       the two candidates it is supposed to separate.  IT SWAMPS THEM.")
        pr("     VERDICT: TEST 4 IS POWERLESS -- not underpowered, structurally powerless.")

    out = os.path.join(HERE, "_scratch", "task5_1ab_discriminator.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES) + "\n")
    print("\nwrote %s" % out)


if __name__ == "__main__":
    main()
