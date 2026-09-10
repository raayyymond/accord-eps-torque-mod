# -*- coding: utf-8 -*-
"""studies/grind/design290d_nonlinear.py -- PART C of the V290 brief: is the ring a LINEAR marginally-stable mode, or a
CLAMP-LIMITED LIMIT CYCLE?  Agent design290d, 2026-09-09.  Reads caches only; builds nothing, sends nothing.

The bursts re-fire every 1.5-2 s at a held angle, hands off, with no slew-cap hits -- limit-cycle-shaped.  Five
discriminating tests, each with the answer a LINEAR mode would give written down first:

  C1 amplitude-frequency dependence.  LINEAR: f independent of burst amplitude.  LIMIT CYCLE through a saturation:
     also f nearly independent (a saturation is memoryless, its describing function is REAL) -- so this test alone
     cannot separate them; it CAN kill a backlash / hysteresis cycle (f falls with amplitude) or a Duffing spring
     (f rises with amplitude).  Reported as Spearman rho(f, log A) with a block bootstrap CI.
  C2 harmonic content.  LINEAR: P(2f)/P(f) and P(3f)/P(f) inside bursts equal to the engaged non-burst baseline.
     SATURATED CYCLE: the third harmonic rises (a symmetric saturation makes odd harmonics; 3f/f ~ 1/9 at hard clip).
  C3 drive independence.  LINEAR: burst peak amplitude tracks the exogenous drive that rang it.  LIMIT CYCLE: the
     peak amplitude is set by the loop, not by the drive -- rho(A_peak, drive) ~ 0.
  C4 CLAMP CENSUS AT THE MEASURED AMPLITUDE.  The decisive one, and it is arithmetic, not statistics: convert the
     measured burst wheel-rate amplitude into E, P, D, S and T counts through the byte-exact chain and ask whether
     ANY of P 15360 / D 10240 / sum 15360 / out 3072 is reached.  A clamp that never binds cannot limit a cycle.
  C5 describing function.  If a clamp does bind, solve 1 + N(A) L(jw) = 0 on the surviving plant family for the
     predicted cycle amplitude and frequency, and compare with the measured ones.

Run: python design290d_nonlinear.py       -> _scratch/design290d_nonlinear.txt
"""
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache")
FS = 100.0
CPD = 8.0                     # raw counts of x per deg/s (measured)
OUT = []
ROUTES = [("r39", "V282", 20.0), ("r5e_v288", "V288 rev 2", 20.1), ("r62_v289", "V289 rev 1", 16.9), ("r63_v289", "V289 rev 1", 16.5)]
# byte-read clamps (V282 == V289, cal-identical here): 0xC61BC P, 0xC61B6 D, 0xC61BE sum, 0xC61B4 out
P_CLAMP, D_CLAMP, SUM_CLAMP, T_CLAMP = 15360, 10240, 15360, 3072
KP, KD, FADE, GAIN = 248.0, 128.0, 254.0 / 256.0, 5346.0 / 32768.0


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def load(key):
    d = np.load(os.path.join(CACHE, key, key + ".npz"), allow_pickle=True)
    return {k: np.asarray(d[k], float) for k in ("t", "cs_rate", "cs_ang", "cs_tq", "cs_v", "cc_lat", "sca", "e4tq", "tq", "imu_vert", "imu_lat")}


def runs(mask, minlen):
    m = np.concatenate(([False], mask, [False])).astype(np.int8)
    e = np.diff(m)
    return [(i, j) for i, j in zip(np.where(e == 1)[0], np.where(e == -1)[0]) if j - i >= minlen]


def Fmag(f, fb_a, fb_b):
    """|F| = |two-sample sum * one-pole|, raw E counts per raw count of x, at f Hz (1 kHz tick)."""
    z = np.exp(2j * np.pi * f / 1000.0)
    return float(np.abs((fb_b / 1024.0) * (1 + 1 / z) / (1 - (fb_a / 1024.0) / z)))


def bursts(key, f0, bw=3.0):
    """band-passed wheel-rate envelope -> bursts.  Returns per-burst dicts with peak amplitude (deg/s, envelope),
    instantaneous frequency at the peak, decay zeta, and the exogenous-drive proxies in the preceding 300 ms."""
    d = load(key)
    r, ang = d["cs_rate"], d["cs_ang"]
    eng = (d["cc_lat"] > 0.5) & (d["sca"] > 0.5) & (d["cs_v"] > 3.0)
    sos = signal.butter(4, [(f0 - bw) / (FS / 2), (f0 + bw) / (FS / 2)], btype="band", output="sos")
    B = []
    cmd = d["e4tq"]
    for a, b in runs(eng, 400):
        y = signal.sosfiltfilt(sos, signal.detrend(r[a:b]))
        an = signal.hilbert(y)
        env = np.abs(an)
        ph = np.unwrap(np.angle(an))
        fi = np.gradient(ph) * FS / (2 * np.pi)
        thr = np.percentile(env, 85)
        pk, _ = signal.find_peaks(env, height=thr, distance=int(0.15 * FS))
        dc = np.abs(np.diff(cmd[a:b], prepend=cmd[a]))
        # the command carries an ECHO of the ring itself (openpilot measures the wheel at 100 Hz, unfiltered),
        # so |dcmd| is confounded.  A < 8 Hz command proxy cannot contain the 16-20 Hz line.
        slo = signal.butter(4, 8.0 / (FS / 2), btype="low", output="sos")
        dclo = np.abs(np.diff(signal.sosfiltfilt(slo, cmd[a:b]), prepend=0.0))
        iv = d["imu_vert"][a:b]
        if np.any(iv):
            sr = signal.butter(4, [1.0 / (FS / 2), 10.0 / (FS / 2)], btype="band", output="sos")
            ivb = signal.sosfiltfilt(sr, signal.detrend(iv))
        else:
            ivb = np.zeros(b - a)
        for p in pk:
            if p < 40 or p + 26 >= len(env):
                continue
            seg = env[p + 6: p + 26]
            if seg.min() <= 0:
                continue
            sl = np.polyfit(np.arange(len(seg)) / FS, np.log(seg), 1)[0]
            B.append(dict(A=float(env[p]), f=float(np.median(fi[p - 3:p + 4])), z=float(-sl / (2 * np.pi * f0)),
                          drive_cmd=float(np.sqrt(np.mean(dc[max(0, p - 30):p] ** 2))),
                          drive_cmd_lf=float(np.sqrt(np.mean(dclo[max(0, p - 30):p] ** 2))),
                          drive_road=float(np.std(ivb[max(0, p - 30):p])) if np.any(ivb) else np.nan,
                          ang=float(np.abs(ang[a + p])), tq=float(np.abs(d["cs_tq"][a + p]))))
    return B, d


def rho_ci(x, y, nb=2000, seed=0):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 12:
        return np.nan, (np.nan, np.nan), len(x)
    r = stats.spearmanr(x, y).correlation
    rng = np.random.default_rng(seed)
    bs = [stats.spearmanr(x[i], y[i]).correlation for i in (rng.integers(0, len(x), len(x)) for _ in range(nb))]
    return float(r), tuple(np.percentile(bs, (2.5, 97.5))), len(x)


def harmonics(key, f0):
    d = load(key)
    eng = (d["cc_lat"] > 0.5) & (d["sca"] > 0.5) & (d["cs_v"] > 3.0)
    sos = signal.butter(4, [(f0 - 3) / (FS / 2), (f0 + 3) / (FS / 2)], btype="band", output="sos")
    inb, out = [], []
    for a, b in runs(eng, 400):
        y = signal.sosfiltfilt(sos, signal.detrend(d["cs_rate"][a:b]))
        env = np.abs(signal.hilbert(y))
        thr = np.percentile(env, 90)
        x = signal.detrend(d["cs_rate"][a:b])
        W = 128
        for s in range(0, len(x) - W, W // 2):
            (inb if env[s:s + W].max() >= thr else out).append(x[s:s + W])

    def hr(chunks):
        if len(chunks) < 5:
            return (np.nan,) * 3
        P = None
        for ch in chunks:
            f, p = signal.welch(ch, FS, nperseg=len(ch))
            P = p if P is None else P + p
        P /= len(chunks)

        def at(fx):
            i = int(np.argmin(np.abs(f - fx))); return float(P[max(0, i - 1):i + 2].max())
        p1 = at(f0)
        # 2f0 and 3f0 alias about 50 Hz at 100 Hz sampling: 2*16.5 = 33.0 (in band), 3*16.5 = 49.5 (in band);
        # 2*20 = 40.0 (in band), 3*20 = 60 -> ALIASES to 40.0.  Flag the alias case.
        f2, f3 = 2 * f0, 3 * f0
        a2 = f2 if f2 < 50 else 100 - f2
        a3 = f3 if f3 < 50 else 100 - f3
        return p1, at(a2) / p1, at(a3) / p1
    p1i, r2i, r3i = hr(inb)
    p1o, r2o, r3o = hr(out)
    return dict(n_in=len(inb), n_out=len(out), r2_in=r2i, r3_in=r3i, r2_out=r2o, r3_out=r3o,
                f2_alias=2 * f0 >= 50, f3_alias=3 * f0 >= 50)


def clamp_census(A_degs, f0, fb_a, fb_b, label):
    """C4: push a pure sinusoidal wheel ring of envelope amplitude A_degs at f0 through the byte-exact chain and report
    the peak counts at each node against its clamp.  Setpoint held (hands-off, held angle) so E = -F x."""
    x = A_degs * CPD                                   # raw counts of x, amplitude
    F = Fmag(f0, fb_a, fb_b)
    E = F * x
    P = KP / 256.0 * E
    dE = E * 2 * np.sin(np.pi * f0 / 1000.0)           # |1 - z^-1| at f0, 1 kHz tick
    D = KD / 8.0 * dE
    PD = np.hypot(P, D)                                # P and D are 90 deg apart on a sinusoid
    S = FADE * PD
    Hlag = abs((507 / 1024.0 / 32) * (1 + np.exp(-2j * np.pi * f0 / 1000.0)) / (1 - (992 / 1024.0) * np.exp(-2j * np.pi * f0 / 1000.0)))
    T = GAIN * Hlag * min(S, SUM_CLAMP)
    pr("    %-26s A %5.1f deg/s @ %.1f Hz | |F| %5.2f | E %8.0f | P %7.0f /%5d %s | D %7.0f /%5d %s | S %7.0f /%5d %s | T %6.0f /%4d %s" % (
        label, A_degs, f0, F, E, P, P_CLAMP, "BIND" if P >= P_CLAMP else "    ", D, D_CLAMP, "BIND" if D >= D_CLAMP else "    ",
        S, SUM_CLAMP, "BIND" if S >= SUM_CLAMP else "    ", T, T_CLAMP, "BIND" if T >= T_CLAMP else "    "))
    return dict(E=E, P=P, D=D, S=S, T=T, bindP=P >= P_CLAMP, bindD=D >= D_CLAMP, bindS=S >= SUM_CLAMP, bindT=T >= T_CLAMP)


def sat_df(A, lim):
    """describing function of a symmetric saturation for a sinusoid of amplitude A (real, <= 1)."""
    if A <= lim:
        return 1.0
    d = lim / A
    return float((2 / np.pi) * (np.arcsin(d) + d * np.sqrt(1 - d * d)))


def main():
    pr("design290d_nonlinear -- PART C: linear marginal mode vs clamp-limited limit cycle")
    pr("clamps (byte-read, identical V282/V288/V289): P %d (0xC61BC)  D %d (0xC61B6)  sum %d (0xC61BE)  out %d (0xC61B4)" % (
        P_CLAMP, D_CLAMP, SUM_CLAMP, T_CLAMP))
    pr("")
    ALL = {}
    pr("C1/C3. BURST STATISTICS (band-passed wheel-rate envelope, engaged, v > 3 m/s)")
    pr("  %-12s %-11s | %5s | %-24s | %-24s | %-21s | %-21s | %-21s | %-21s" % ("route", "build", "n", "peak amp A deg/s p50 [p5-p95]", "inst. freq at peak p50 [p5-p95]", "rho(f, log A) [95% CI]", "rho(A, |dcmd|) [95% CI]", "rho(A, |dcmd|<8Hz)", "rho(A, road IMU 1-10)"))
    for key, build, f0 in ROUTES:
        B, d = bursts(key, f0)
        ALL[key] = (B, build, f0)
        A = np.array([b["A"] for b in B]); F = np.array([b["f"] for b in B])
        r1, c1, n1 = rho_ci(np.log(np.maximum(A, 1e-6)), F)
        r2, c2, n2 = rho_ci([b["drive_cmd"] for b in B], A)
        r3, c3, n3 = rho_ci([b["drive_cmd_lf"] for b in B], A)
        r4, c4, n4 = rho_ci([b["drive_road"] for b in B], A)
        pr("  %-12s %-11s | %5d | %6.2f [%5.2f %6.2f]        | %6.2f [%5.2f %6.2f]        | %+5.2f [%+5.2f %+5.2f]    | %+5.2f [%+5.2f %+5.2f]    | %+5.2f [%+5.2f %+5.2f]    | %+5.2f [%+5.2f %+5.2f]" % (
            key, build, len(B), np.median(A), *np.percentile(A, (5, 95)), np.median(F), *np.percentile(F, (5, 95)), r1, *c1, r2, *c2, r3, *c3, r4, *c4))
    pr("  READ: rho(f, log A) ~ 0 kills backlash (rho < 0) and a hardening spring (rho > 0); it does NOT by itself")
    pr("        separate a saturation cycle from a linear mode -- C2 and C4 do that.")
    pr("        rho(A, drive) ~ 0 = amplitude set by the loop (limit cycle); rho >> 0 = amplitude set by the drive (linear).")
    pr("")
    pr("C2. HARMONIC CONTENT inside bursts vs engaged non-burst windows (Welch, 1.28 s windows)")
    pr("  %-12s %-11s | %6s %6s | %8s %8s | %8s %8s | %s" % ("route", "build", "n_in", "n_out", "2f/f in", "2f/f out", "3f/f in", "3f/f out", "alias?"))
    for key, build, f0 in ROUTES:
        h = harmonics(key, f0)
        pr("  %-12s %-11s | %6d %6d | %8.4f %8.4f | %8.4f %8.4f | %s" % (
            key, build, h["n_in"], h["n_out"], h["r2_in"], h["r2_out"], h["r3_in"], h["r3_out"],
            ("3f ALIASED to %.1f Hz" % (100 - 3 * f0)) if h["f3_alias"] else "no"))
    pr("  READ: a symmetric hard clip puts 3f/f ~ 0.11 into the signal.  Note 3f is above 50 Hz for the 20 Hz line and")
    pr("        ALIASES at the 100 Hz CAN sample rate -- for those routes the 3f column is not evidence either way.")
    pr("")
    pr("C4. CLAMP CENSUS AT THE MEASURED BURST AMPLITUDE (byte-exact chain, hands-off held angle so E = -F x)")
    for key, build, f0 in ROUTES:
        B, _, _ = ALL[key]
        A = np.array([b["A"] for b in B])
        fb = (923, 1560) if build != "V289 rev 1" else (875, 2301)
        for lab, a in (("median burst", np.median(A)), ("p95 burst", np.percentile(A, 95)), ("max burst", A.max())):
            clamp_census(a, f0, fb[0], fb[1], "%s %s" % (key, lab))
    pr("  and the amplitudes at which each clamp WOULD first bind, for reference:")
    for key, build, f0 in ROUTES[:1] + ROUTES[2:3]:
        fb = (923, 1560) if build != "V289 rev 1" else (875, 2301)
        F = Fmag(f0, *fb)
        dfac = 2 * np.sin(np.pi * f0 / 1000.0)
        aP = P_CLAMP * 256.0 / KP / F / CPD
        aD = D_CLAMP * 8.0 / KD / dfac / F / CPD
        aS = SUM_CLAMP / FADE / np.hypot(KP / 256.0, KD / 8.0 * dfac) / F / CPD
        pr("    %-12s %-11s f %.1f Hz: P clamp at %7.1f deg/s | D clamp at %7.1f deg/s | sum clamp at %7.1f deg/s" % (key, build, f0, aP, aD, aS))
    pr("")
    pr("C5. DESCRIBING FUNCTION.  A saturation's N(A) is REAL and <= 1: it can only REDUCE |L|, never rotate it.")
    pr("    A limit cycle needs |N(A) L(jw)| = 1 with arg L = -180 deg, i.e. the LINEAR loop must be UNSTABLE at that")
    pr("    frequency and the clamp must pull the gain back to the -180 crossing.  Sizing:")
    for f0, lab in ((16.5, "V289 line"), (20.0, "V282 line")):
        for GM in (0.85, 1.0, 1.2, 1.5):
            need = GM              # N(A) must equal 1/|L(-180)| = GM for the cycle to close
            if need >= 1.0:
                pr("      %-10s |L| at -180 = %.2f (GM %.2f) -> linear loop is STABLE there; NO saturation amplitude can" % (lab, 1 / GM, GM))
                pr("                 create a cycle (N <= 1 only makes |NL| smaller).  A cycle here must come from the PLANT.")
                continue
            r = np.linspace(1.0001, 50, 200000)
            k = np.array([sat_df(x, 1.0) for x in r])
            i = int(np.argmin(np.abs(k - need)))
            pr("      %-10s |L| at -180 = %.2f (GM %.2f) -> N must be %.3f -> cycle amplitude = %.2f x the binding clamp" % (lab, 1 / GM, GM, need, r[i]))
    open(os.path.join(SCR, "design290d_nonlinear.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/design290d_nonlinear.txt")


if __name__ == "__main__":
    main()
