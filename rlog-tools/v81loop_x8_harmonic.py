#!/usr/bin/env python3
"""X8 -- is the 17.4 Hz content the FOLDED 3rd HARMONIC of the 27.53 Hz line, or an independent
mode that merely lands there?

X7.6 measured, in the torsion bar, 3f/f = 0.3605 with 2f/f = 0.0233.  An ideal relay gives exactly
1/3 and 0.  That is a textbook odd-symmetric-nonlinearity signature and it would be strong support
for hypothesis C -- EXCEPT that 3*27.53 = 82.59 Hz is above the 50 Hz Nyquist and folds to
|100 - 82.59| = 17.41 Hz, which is the low edge of the band where this kit has independently
recorded GRIND #1 (18-22 Hz).  So the amplitude ratio alone cannot tell a harmonic from a
coincidence, and reporting 0.3605 as "a relay" without this test would be exactly the kind of
confident-wrong attribution the record warns about.

THE TEST.  A genuine harmonic is PHASE-LOCKED to its fundamental; an independent mode is not.
Sampling folds a real component at 82.59 Hz into bin 17.41 with the CONJUGATE phase, so

    phi_obs(17.41)  =  -( 3 * phi(27.53) + const )
    =>  psi(t) = phi_obs(17.41) + 3 * phi(27.53)  is CONSTANT if it is the folded 3rd harmonic.

Concentration R = |mean(exp(i psi))| over the event: R -> 1 phase-locked, R -> 0 independent.
Quoted against a circular-shift surrogate null and bootstrapped over ~1 s BLOCKS, never windows.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v81loop_lib import CACHE, FS_NOM, lattice, resamp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EV = (38.0, 52.0)
F0 = 27.53


def dd(t, *v):
    t = np.asarray(t, float)
    k = np.ones(len(t), bool)
    k[1:] = np.diff(t) > 0
    return (t[k],) + tuple(np.asarray(x, float)[k] for x in v)


def analytic(x, fs, fc, half):
    """Complex analytic signal restricted to [fc-half, fc+half]."""
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= fc - half) & (f <= fc + half)
    H[m] = 2 * X[m]
    return np.fft.irfft(H, n=len(x)) + 1j * np.imag(
        np.fft.ifft(np.concatenate([H, np.zeros(len(x) - len(H), complex)]), n=len(x)) * len(x)) * 0


def bp_analytic(x, fs, fc, half):
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.fft(x - x.mean())
    f = np.fft.fftfreq(n, 1 / fs)
    Y = np.zeros(n, complex)
    m = (f >= fc - half) & (f <= fc + half)
    Y[m] = 2 * X[m]                      # keep positive freqs only -> analytic signal
    return np.fft.ifft(Y)


def concentration(psi, blk, rng, nboot=4000):
    z = np.exp(1j * psi)
    R = abs(z.mean())
    ub = np.unique(blk)
    bs = []
    for _ in range(nboot):
        pick = rng.choice(ub, len(ub))
        idx = np.concatenate([np.flatnonzero(blk == u) for u in pick])
        bs.append(abs(z[idx].mean()))
    return R, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    N = np.load(CACHE / "v81loop_native_s8.npz")
    tau = lattice(*EV, FS_NOM)
    b = dd(N["b_t"], N["b_tq"])
    a = dd(N["a_t"], N["a_ang"])
    sc = dd(N["sc_t"], N["sc_v"])
    chans = dict(bar=resamp(tau, b[0], b[1]), angle=resamp(tau, a[0], a[1]),
                 cmd=resamp(tau, sc[0], sc[1]))
    f3 = abs(3 * F0 - 100.0)
    f2 = abs(2 * F0 - 100.0)
    print("=" * 100)
    print(f"X8  PHASE-LOCKING TEST.  f0 = {F0} Hz;  3f0 = {3 * F0:.2f} -> folds to {f3:.2f} Hz;"
          f"  2f0 = {2 * F0:.2f} -> folds to {f2:.2f} Hz")
    print("=" * 100)
    rng = np.random.default_rng(20260807)
    n = len(tau)
    blk = (np.arange(n) // 100).astype(int)          # ~1 s blocks
    print(f"  {'channel':>8} {'pair':>18} {'R':>7} {'95% CI':>16} {'surrogate p95':>14} "
          f"{'verdict':>14}")
    for nm, x in chans.items():
        z1 = bp_analytic(x, FS_NOM, F0, 2.0)
        for lab, fx, k, sign in ((f"3f0 -> {f3:.1f}", f3, 3, +1), (f"2f0 -> {f2:.1f}", f2, 2, +1)):
            zx = bp_analytic(x, FS_NOM, fx, 2.0)
            psi = np.angle(zx) + sign * k * np.angle(z1)      # folded => conjugate => ADD
            R, lo, hi = concentration(psi, blk, rng)
            sur = []
            for _ in range(300):
                s = int(rng.integers(int(0.1 * n), int(0.9 * n)))
                sur.append(abs(np.exp(1j * (np.angle(np.roll(zx, s))
                                            + sign * k * np.angle(z1))).mean()))
            p95 = float(np.percentile(sur, 95))
            v = "PHASE-LOCKED" if lo > p95 else ("marginal" if R > p95 else "INDEPENDENT")
            print(f"  {nm:>8} {lab:>18} {R:>7.3f} [{lo:>6.3f},{hi:>6.3f}] {p95:>14.3f} {v:>14}")
    print()
    print("  Controls -- pairs that MUST come out independent if the statistic is working:")
    for nm, x in list(chans.items())[:1]:
        z1 = bp_analytic(x, FS_NOM, F0, 2.0)
        for fx, k in ((11.0, 3), (21.0, 3), (f3, 2)):
            zx = bp_analytic(x, FS_NOM, fx, 2.0)
            psi = np.angle(zx) + k * np.angle(z1)
            R, lo, hi = concentration(psi, blk, rng, 1500)
            print(f"  {nm:>8} {'f=' + f'{fx:.1f}, k={k}':>18} {R:>7.3f} [{lo:>6.3f},{hi:>6.3f}]")

    print()
    print("=" * 100)
    print("X8b  DOES THE 17.4 Hz CONTENT TRACK THE 27.5 Hz ENVELOPE IN TIME?")
    print("=" * 100)
    print("  A harmonic's amplitude is slaved to its fundamental's; an independent mode's is not.")
    for nm, x in chans.items():
        e1 = np.abs(bp_analytic(x, FS_NOM, F0, 2.0))
        e3 = np.abs(bp_analytic(x, FS_NOM, f3, 2.0))
        e2 = np.abs(bp_analytic(x, FS_NOM, f2, 2.0))
        # smooth to 0.5 s so we compare ENVELOPES, not the carriers
        k = np.ones(50) / 50
        s1, s3, s2 = (np.convolve(e, k, "same") for e in (e1, e3, e2))
        print(f"  {nm:>8}  corr(env f0, env 3f0) = {np.corrcoef(s1, s3)[0, 1]:+.3f}   "
              f"corr(env f0, env 2f0) = {np.corrcoef(s1, s2)[0, 1]:+.3f}")
    print("  🛑 Envelope correlation alone is weak evidence -- both rise when the car is excited.")
    print("     The phase-locking test above is the one that decides.")


if __name__ == "__main__":
    main()
