#!/usr/bin/env python3
r"""RESONANCE OR STICK-SLIP?  The harmonics test, done properly.

The first attempt (`ratchet_harmonics_audio.py`) could not discriminate, for two fixable reasons:
its control comb sat at 11.7/19.5/27.3 Hz -- INSIDE bands the record already shows are
engagement-elevated -- and the `_spec` caches bin at 3.91 Hz, too coarse to separate a 7.79 Hz
fundamental from its neighbours.  This fixes both.

  * RESOLUTION: re-extracted from the rlogs at NFFT 16384 / 16 kHz = **0.977 Hz bins**, alias-free
    to 8 kHz, with a per-window engagement flag in the same file (no cross-cache alignment).
  * CONTROL: instead of guessing which frequencies are neutral, fit a SMOOTH BASELINE to the
    engaged/manual ratio across 3-60 Hz and ask whether f0 and its harmonics sit ABOVE it.  Broadband
    engagement loudness is exactly what the baseline absorbs, so what survives is LOCAL EXCESS.

WHY IT MATTERS.  The record calls the ratchet "a lightly-damped RESONANCE, Q 14-29", and the whole arc
has tried to add damping to it.  A stick-slip limit cycle looks nearly identical in a ring-down and
calls for the OPPOSITE fix -- break the friction rather than add damping.  Harmonics separate them: a
linear resonance driven by broadband road input radiates at f0 alone; a relaxation oscillation radiates
a comb at 2f0, 3f0, 4f0 because its waveform is not a sinusoid.

READING IT
  * f0 AND its harmonics above the baseline        => STICK-SLIP; the arc's premise is wrong.
  * f0 alone above, harmonics at the baseline      => LINEAR RESONANCE, as the record has it.
  * nothing above the baseline                     => the excess was broadband loudness all along.

WHAT THIS IS NOT.  Audio is what the car RADIATES.  A radiated comb is evidence about the
oscillation's waveform; it is not proof that this is the same event the operator feels in the wheel.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import glob
import os
import sys

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F_LO, F_HI = 3.0, 60.0          # the fit window; well inside the audio's own band
F0_SEARCH = (6.5, 9.5)          # the record puts the ratchet at 7.79-8.64 Hz
HARM = [1, 2, 3, 4, 5]
SMOOTH_HZ = 6.0                 # baseline smoothing width -- wide enough to pass broadband loudness,
                                # narrow enough not to absorb a line


def smooth(y, x, width):
    """moving average in frequency, width in Hz -- the broadband baseline"""
    out = np.empty_like(y)
    for i, xi in enumerate(x):
        m = np.abs(x - xi) <= width / 2
        out[i] = np.median(y[m])
    return out


def analyse(path):
    z = np.load(path, allow_pickle=True)
    if not {'psd', 'cov', 'freq', 'cols'} <= set(z.files):
        return None
    f = np.asarray(z['freq'], float)
    P = np.asarray(z['psd'], float)
    cov = np.asarray(z['cov'], float)
    cols = [str(c) for c in np.asarray(z['cols'])]
    eng = cov[:, cols.index('eng')]
    ok = np.isfinite(eng)
    em = ok & (eng > 0.5)
    mm = ok & (eng < 0.5)
    if em.sum() < 50 or mm.sum() < 50:
        return None
    band = (f >= F_LO) & (f <= F_HI)
    fb = f[band]
    ratio = P[em][:, band].mean(axis=0) / np.maximum(P[mm][:, band].mean(axis=0), 1e-30)
    base = smooth(ratio, fb, SMOOTH_HZ)
    excess = ratio / np.maximum(base, 1e-30)
    # locate the fundamental as the largest LOCAL EXCESS in the search window
    sw = (fb >= F0_SEARCH[0]) & (fb <= F0_SEARCH[1])
    f0 = float(fb[sw][np.argmax(excess[sw])])
    df = float(np.median(np.diff(fb)))
    out = []
    for k in HARM:
        m = np.abs(fb - k * f0) <= max(df, 0.6)
        out.append(float(excess[m].max()) if m.any() else float('nan'))
    return dict(route=os.path.basename(path), eng=int(em.sum()), man=int(mm.sum()),
                df=df, f0=f0, exc=out,
                bmed=float(np.median(base)))


def main():
    caches = sorted(glob.glob(os.path.join(REPO, 'analysis-2020accord', '_audio_r*.npz')))
    if len(sys.argv) > 1:
        caches = [c for c in caches if any(a in c for a in sys.argv[1:])]
    rows = []
    for c in caches:
        try:
            r = analyse(c)
        except Exception as e:
            print('  (skip %s: %s)' % (os.path.basename(c), e))
            continue
        if r:
            rows.append(r)

    print('=' * 92)
    print('  RESONANCE OR STICK-SLIP?  local EXCESS over a smooth broadband baseline')
    print('=' * 92)
    if not rows:
        print('  no fine-resolution audio cache found.')
        print('  \U0001f6d1 that is an EMPTY INPUT, not a null result -- extract first:')
        print('     python analysis-2020accord/extract/extract_audio_cache.py a4 a5 a6 97')
        return
    print('  %-16s %6s %6s %6s %7s %7s %7s %7s %7s %7s' %
          ('route', 'eng', 'man', 'df', 'f0 Hz', 'f0', '2f0', '3f0', '4f0', '5f0'))
    print('  (each harmonic column is excess OVER the local broadband baseline; 1.0 = nothing there)')
    print('  ' + '-' * 84)
    for r in rows:
        print('  %-16s %6d %6d %6.3f %7.2f %7.2f %7.2f %7.2f %7.2f %7.2f'
              % (r['route'], r['eng'], r['man'], r['df'], r['f0'], *r['exc']))

    A = np.array([r['exc'] for r in rows])
    med = np.nanmedian(A, axis=0)
    print('  ' + '-' * 84)
    print('  %-16s %6s %6s %6s %7s %7.2f %7.2f %7.2f %7.2f %7.2f'
          % ('MEDIAN', '', '', '', '', *med))
    print()
    print('  READING IT:')
    print('   * f0 AND harmonics > 1  => STICK-SLIP. The arc has been adding damping to something')
    print('     that is not a linear resonance, and the fix is friction, not damping.')
    print('   * f0 alone > 1          => LINEAR RESONANCE, as the record has it.')
    print('   * nothing > 1           => the engaged/manual excess was broadband loudness.')
    print()
    print('  \U0001f6d1 audio is what the car RADIATES. A radiated comb is evidence about the')
    print('     oscillation WAVEFORM; it is not proof this is what the wheel feels.')


if __name__ == '__main__':
    main()
