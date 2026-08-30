#!/usr/bin/env python3
r"""IS THE RATCHET A LINEAR RESONANCE, OR A STICK-SLIP LIMIT CYCLE?  Asked of the AUDIO.

The record calls the ratchet "a lightly-damped RESONANCE, Q 14-29", from ring-down zeta 0.017-0.036 on
CAN.  That reading has driven the whole arc: every build has tried to add damping to a resonance.  But
a resonance and a stick-slip limit cycle look nearly identical in a ring-down, and they call for
opposite fixes -- damping for the first, breaking the friction nonlinearity for the second.

**HARMONICS DISCRIMINATE THEM.**  A linear resonance excited by broadband road input radiates at f0 and
nothing else.  A stick-slip / limit-cycle oscillation is a relaxation process: it radiates at f0 AND at
2*f0, 3*f0, 4*f0, because the waveform is not a sinusoid.

The 16 kHz audio spectra are the right instrument: alias-free to 2 kHz, so 2f, 3f and 4f of a 7.8 Hz
fundamental (15.6 / 23.4 / 31.2 Hz) are all observed directly rather than folded.  The CAN channel
cannot do this -- 3f and 4f sit in the band the record shows is contaminated from 52-71 Hz.

METHOD
  * align each `_spec` audio cache to its CAN cache on time, to get the engaged mask
  * contrast ENGAGED against MANUAL power at f0 and its harmonics (the ratchet is engaged-only:
    engaged clears its null 7/7, manual 0/7)
  * a CONTROL comb at non-harmonic offsets, so "everything is louder when engaged" cannot pass as
    harmonic structure

READING IT
  * harmonics elevated engaged, control comb flat  => STICK-SLIP.  The arc's premise is wrong and the
    fix is friction, not damping.
  * only f0 elevated, harmonics flat               => LINEAR RESONANCE, as the record has it.
  * everything elevated including the control      => the contrast is broadband loudness, not the
    ratchet, and the test says nothing.

WHAT THIS IS NOT.  Audio is what the car RADIATES; the ratchet is felt in the wheel.  A radiated
harmonic is evidence about the oscillation's waveform, not proof it is the same event the operator
feels.  And the `_spec` caches bin at 3.9 Hz, so this resolves a comb, not a line.

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
F0 = 7.8                       # the ratchet fundamental, 7.79-8.64 Hz in the record
HARM = [1, 2, 3, 4]
CTRL = [1.5, 2.5, 3.5]         # non-harmonic control comb -- same loudness, wrong frequencies
MIN_FRAMES = 200


def band(P, f, fc, half):
    m = (f >= fc - half) & (f <= fc + half)
    return float(P[m].mean()) if m.any() else float('nan')


def pair_for(spec):
    """find the CAN cache for the same route, wherever it lives"""
    route = os.path.basename(spec).replace('_spec.npz', '')
    for pat in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
                os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route, route + '.npz')):
        if os.path.exists(pat):
            return pat
    g = glob.glob(os.path.join(REPO, '**', '_scratch', 'cache', route, route + '.npz'),
                  recursive=True)
    return g[0] if g else None


def main():
    specs = sorted(glob.glob(os.path.join(REPO, '**', '*_spec.npz'), recursive=True))
    print('=' * 96)
    print('  RATCHET HARMONICS IN THE AUDIO   f0 = %.1f Hz, engaged vs manual' % F0)
    print('=' * 96)
    print('  %-7s %7s %7s %8s %8s %8s %8s %9s' %
          ('route', 'eng', 'man', 'f0', '2f0', '3f0', '4f0', 'ctrl'))
    print('  (each column is ENGAGED/MANUAL power ratio; ctrl is the non-harmonic comb)')
    print('  ' + '-' * 74)

    rows = []
    for sp in specs:
        can = pair_for(sp)
        if not can:
            continue
        try:
            zs = np.load(sp, allow_pickle=True)
            zc = np.load(can, allow_pickle=True)
        except Exception:
            continue
        if not {'S', 'f', 't'} <= set(zs.files) or 'cc_lat' not in zc.files or 't' not in zc.files:
            continue
        f = np.asarray(zs['f'], float)
        S = np.asarray(zs['S'], float)
        ts = np.asarray(zs['t'], float)
        tc = np.asarray(zc['t'], float)
        eng = np.asarray(zc['cc_lat'], float) > 0.5
        n = min(len(tc), len(eng))
        tc, eng = tc[:n], eng[:n]
        if S.ndim != 2 or len(ts) != S.shape[0]:
            continue
        # nearest-neighbour align the audio windows onto the CAN engaged mask
        idx = np.searchsorted(tc, ts)
        idx = np.clip(idx, 0, len(eng) - 1)
        em = eng[idx]
        if em.sum() < MIN_FRAMES or (~em).sum() < MIN_FRAMES:
            continue
        half = float(np.median(np.diff(f))) * 0.75
        Pe = S[em].mean(axis=0)
        Pm = S[~em].mean(axis=0)
        h = [band(Pe, f, F0 * k, half) / max(band(Pm, f, F0 * k, half), 1e-30) for k in HARM]
        c = [band(Pe, f, F0 * k, half) / max(band(Pm, f, F0 * k, half), 1e-30) for k in CTRL]
        rows.append((os.path.basename(sp).replace('_spec.npz', ''),
                     int(em.sum()), int((~em).sum()), h[0], h[1], h[2], h[3],
                     float(np.median(c))))
    for r in rows:
        print('  %-7s %7d %7d %8.3f %8.3f %8.3f %8.3f %9.3f' % r)

    if rows:
        A = np.array([[r[3], r[4], r[5], r[6], r[7]] for r in rows])
        med = np.median(A, axis=0)
        print('  ' + '-' * 74)
        print('  %-7s %7s %7s %8.3f %8.3f %8.3f %8.3f %9.3f'
              % ('MEDIAN', '', '', med[0], med[1], med[2], med[3], med[4]))
        print()
        harm_over_ctrl = med[:4] / max(med[4], 1e-30)
        print('  harmonics relative to the CONTROL comb:  %s'
              % np.round(harm_over_ctrl, 3).tolist())
        print()
        print('  READING IT:')
        print('   * harmonics >> control  => STICK-SLIP.  The arc has been adding damping to')
        print('     something that is not a linear resonance, and the fix is friction, not damping.')
        print('   * only f0 above control => LINEAR RESONANCE, as the record has it.')
        print('   * all ~= control        => broadband loudness, the test says nothing.')
        print()
        print('  🛑 audio is what the car RADIATES, and these caches bin at %.2f Hz -- '
              'this resolves a COMB, not a line.' % float(np.median(np.diff(f))))
        print('  🛑 AND THE CONTROL IS CONTAMINATED: the comb at 1.5/2.5/3.5 f0 = '
              '11.7/19.5/27.3 Hz sits INSIDE bands the record shows are themselves')
        print('     engagement-elevated (grinding 15-22, pumping 22-30). It is NOT a neutral')
        print('     baseline, so the harmonic/control ratios UNDERSTATE any real excess -- and')
        print('     2f0 = 15.6 Hz cannot be separated from the grinding band at all.')
        print('     Read the RAW engaged/manual columns, not the ratio.')
    else:
        print('  no route had BOTH an audio spectrum and a CAN cache with an engagement mask.')
        print('  \U0001f6d1 that is an EMPTY INPUT, not a null result.')


if __name__ == '__main__':
    main()
