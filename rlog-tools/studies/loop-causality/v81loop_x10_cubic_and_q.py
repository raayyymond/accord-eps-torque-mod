#!/usr/bin/env python3
"""X10 -- independent check of r67-analyst's two corrections, both of which move MY numbers.

  (A) THE 5th HARMONIC.  I reported "textbook relay signature" off 3f/f = 0.36 with no 2f.
      🛑 A CUBIC GIVES 3f/f = 1/3 TOO.  For x = A cos(wt):
            relay (square wave):  harmonics 1/n for odd n  => 3f/f = 0.3333, 5f/f = 0.2000
            cubic y = x^3      :  x^3 = A^3 (3/4 cos wt + 1/4 cos 3wt)
                                  => 3f/f = (1/4)/(3/4) = 0.3333, 5f/f = EXACTLY 0
      So 3f/f alone CANNOT separate them and my attribution was underdetermined. The 5th decides.

      🛑 FOLDING IS DIFFERENT FOR THE 5th.  With fs = 100:
            3f0 = 82.6 = fs - 17.4  ->  appears at 17.4 with CONJUGATE phase  (psi = phi3 + 3*phi1)
            5f0 = 137.7 = fs + 37.7 ->  appears at 37.7 with PHASE PRESERVED  (psi = phi5 - 5*phi1)
      Using the conjugate form for the 5th would null a real harmonic. That is the trap here.

  (B) Q IS AMPLITUDE-DEPENDENT.  I used Q = 23.7 in the loop-gain bound. r67-analyst now reports
      that value was resolution-limited and that a ringdown gives Q ~ 7 at the operating amplitude,
      rising past 30 as it decays. Since my bound is LINEAR in Q, this is a headline number.
      ⚠ And the ringdown has a confound neither of us has stated: the engaged-only damper switches
      OFF at the disengage edge (mode 26 -> 24), so a post-disengage decay measures the DISENGAGED
      plant, not the engaged one the limit cycle actually lives in.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import CACHE, FS_NOM, lattice, resamp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EV = (38.0, 52.0)
F0 = 27.53
K_INTAKE = 3564.0 / 8192.0
FC_IIR = 4.97
SLEW = 123.0
CEILING = 4762.0


def dd(t, *v):
    t = np.asarray(t, float)
    k = np.ones(len(t), bool)
    k[1:] = np.diff(t) > 0
    return (t[k],) + tuple(np.asarray(x, float)[k] for x in v)


def bp(x, fs, fc, half):
    """Analytic signal restricted to [fc-half, fc+half]."""
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.fft(x - x.mean())
    f = np.fft.fftfreq(n, 1 / fs)
    Y = np.zeros(n, complex)
    m = (f >= fc - half) & (f <= fc + half)
    Y[m] = 2 * X[m]
    return np.fft.ifft(Y)


def fold(F, fs=100.0):
    """(observed frequency, conjugate?) for a real component at true frequency F."""
    k = round(F / fs)
    fa = F - k * fs
    return (abs(fa), fa < 0)


def amp_bin(x, fs, f0):
    """Single-FFT amplitude at f0 over the whole record (finest resolution available)."""
    n = len(x)
    w = np.hanning(n)
    X = np.fft.rfft((x - x.mean()) * w)
    f = np.fft.rfftfreq(n, 1 / fs)
    j = int(np.argmin(np.abs(f - f0)))
    return float(np.abs(X[j]) * 2 / w.sum()), float(f[j])


def main():
    N = np.load(CACHE / "v81loop_native_s8.npz")
    tau = lattice(*EV, FS_NOM)
    b = dd(N["b_t"], N["b_tq"])
    a = dd(N["a_t"], N["a_ang"])
    sc = dd(N["sc_t"], N["sc_v"])
    bar = resamp(tau, b[0], b[1])
    ang = resamp(tau, a[0], a[1])
    cmd = resamp(tau, sc[0], sc[1])

    print("=" * 100)
    print("X10-A  THE 5th HARMONIC -- relay vs cubic")
    print("=" * 100)
    print(f"  {'harmonic':>9} {'true Hz':>9} {'folds to':>9} {'conj?':>6} "
          f"{'bar amp':>10} {'ratio':>8}   relay / cubic prediction")
    preds = {1: ("1.0000", "1.0000"), 2: ("0", "0"), 3: ("0.3333", "0.3333"),
             5: ("0.2000", "0.0000"), 7: ("0.1429", "0.0000")}
    a1 = None
    got = {}
    for k in (1, 2, 3, 5, 7):
        F = k * F0
        fo, conj = fold(F)
        A, fbin = amp_bin(np.asarray(bar, float), FS_NOM, fo)
        if k == 1:
            a1 = A
        got[k] = (A, fo, conj)
        r, c = preds[k]
        print(f"  {k:>8}f {F:>9.2f} {fo:>9.2f} {str(conj):>6} {A:>10.2f} "
              f"{A / a1:>8.4f}   {r:>7} / {c:>7}")
    r5 = got[5][0] / a1
    r3 = got[3][0] / a1
    print(f"\n  measured 5f/3f = {r5 / r3:.4f}")
    print(f"    ideal relay predicts (1/5)/(1/3) = 0.6000  -> off by {0.6 / (r5 / r3):.1f}x")
    print(f"    cubic         predicts            0.0000")
    # is the 5f even above its own local floor?
    fo5 = got[5][1]
    nb = [amp_bin(np.asarray(bar, float), FS_NOM, fo5 + d)[0]
          for d in (-2.0, -1.5, -1.0, 1.0, 1.5, 2.0)]
    print(f"  5f bin amplitude {got[5][0]:.2f} vs local neighbourhood median "
          f"{np.median(nb):.2f}  => prominence {got[5][0] / np.median(nb):.2f}")

    print("\n  --- phase-locking, with the CORRECT fold convention per harmonic ---")
    rng = np.random.default_rng(5150)
    n = len(tau)
    blk = (np.arange(n) // 100).astype(int)
    z1 = bp(bar, FS_NOM, F0, 2.0)
    print(f"  {'harmonic':>9} {'obs Hz':>8} {'relation':>22} {'R':>7} {'surrogate p95':>14}"
          f" {'verdict':>14}")
    for k in (2, 3, 5):
        fo, conj = got[k][1], got[k][2]
        zk = bp(bar, FS_NOM, fo, 2.0)
        sign = +1 if conj else -1
        rel = f"phi{k} {'+' if conj else '-'} {k}*phi1"
        psi = np.angle(zk) + sign * k * np.angle(z1)
        R = abs(np.exp(1j * psi).mean())
        sur = []
        for _ in range(300):
            s = int(rng.integers(int(0.1 * n), int(0.9 * n)))
            sur.append(abs(np.exp(1j * (np.angle(np.roll(zk, s))
                                        + sign * k * np.angle(z1))).mean()))
        p95 = float(np.percentile(sur, 95))
        print(f"  {k:>8}f {fo:>8.2f} {rel:>22} {R:>7.3f} {p95:>14.3f} "
              f"{'LOCKED' if R > p95 else 'not locked':>14}")

    print()
    print("=" * 100)
    print("X10-B  RINGDOWN Q at the disengage edge -- my own fit")
    print("=" * 100)
    lt, lv = dd(N["lat_t"], N["lat_v"])
    edges = lt[1:][(lv[:-1] > 0.5) & (lv[1:] <= 0.5)]
    ed = [e for e in edges if 45.0 < e < 58.0]
    print(f"  latActive falling edges in 45-58 s: {[f'{e:.3f}' for e in ed]}")
    if not ed:
        print("  none found -- cannot do the ringdown")
        return
    t0 = ed[0]
    tw = lattice(t0 - 1.0, t0 + 2.5, FS_NOM)
    bw = resamp(tw, b[0], b[1])
    env = np.abs(bp(bw, FS_NOM, F0, 3.0))
    rel = tw - t0
    print(f"  edge at t = {t0:.3f} s; envelope just before = "
          f"{env[(rel > -0.3) & (rel < -0.02)].mean():.1f} ct")
    print(f"  {'interval':>14} {'env start':>10} {'env end':>9} {'tau (s)':>9} {'local Q':>9}")
    for lo, hi in ((0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6)):
        m = (rel >= lo) & (rel <= hi)
        if m.sum() < 5:
            continue
        e0, e1 = env[m][0], env[m][-1]
        if e1 <= 0 or e0 <= 0 or e1 >= e0:
            print(f"  {f'+{lo:.1f}->{hi:.1f}':>14} {e0:>10.1f} {e1:>9.1f} "
                  f"{'--':>9} {'(rising)':>9}")
            continue
        tau_ = (hi - lo) / np.log(e0 / e1)
        print(f"  {f'+{lo:.1f}->{hi:.1f}':>14} {e0:>10.1f} {e1:>9.1f} {tau_:>9.3f} "
              f"{np.pi * F0 * tau_:>9.1f}")
    print("  Q = pi * f0 * tau  (amplitude decay e^-t/tau)")
    print("  🛑 CONFOUND, unstated by either of us: the engaged-only damper switches OFF at this")
    print("     edge (mode 26 -> 24), so this is the DISENGAGED plant's damping, not the engaged")
    print("     plant the limit cycle lives in. If the engaged damper removes net damping, the")
    print("     ENGAGED Q is HIGHER than this, which pushes the bound back UP.")

    print()
    print("=" * 100)
    print("X10-C  THE LOOP-GAIN BOUND, redone as a function of Q")
    print("=" * 100)
    hiir = 1.0 / np.sqrt(1 + (F0 / FC_IIR) ** 2)
    w = np.hanning(len(tau))
    def amp(x, f):
        X = np.fft.rfft((np.asarray(x, float) - np.mean(x)) * w)
        ff = np.fft.rfftfreq(len(x), 1 / FS_NOM)
        return float(np.abs(X[int(np.argmin(np.abs(ff - f)))]) * 2 / w.sum())
    Acmd, Abar = amp(cmd, F0), amp(bar, F0)
    tri_fund = (8 / np.pi ** 2) * (SLEW * (FS_NOM / F0) / 2.0) / 2.0
    g_lo = amp(bar, 2.5) / (amp(cmd, 2.5) * K_INTAKE / np.sqrt(1 + (2.5 / FC_IIR) ** 2))
    now = Acmd * K_INTAKE * hiir
    mx = tri_fund * K_INTAKE * hiir
    print(f"  |cmd(f0)| {Acmd:.2f} ct -> internal {now:.2f} ct ; ceiling {tri_fund:.1f} ct "
          f"-> internal {mx:.2f} ct ; |bar(f0)| {Abar:.1f} ct ; g_lo {g_lo:.2f}")
    print(f"  {'Q':>6} {'as commanded':>16} {'at openpilot MAX':>18}   [% of the observed bar]")
    for Q in (7.0, 10.0, 13.0, 23.7, 40.0, 103.0):
        print(f"  {Q:>6.1f} {100 * now * g_lo * Q / Abar:>15.1f}% "
              f"{100 * mx * g_lo * Q / Abar:>17.1f}%")
    print("  My reported 93% used Q = 23.7. At the ringdown Q of ~7-13 the figure is far lower.")


if __name__ == "__main__":
    main()
