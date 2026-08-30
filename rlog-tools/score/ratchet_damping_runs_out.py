#!/usr/bin/env python3
r"""🛑 RETRACTED HEADLINE -- the amplitude trend here is mostly REGRESSION DILUTION.

The conclusion this file was written for ("a protective damping term runs out above ~2 deg/s") DID NOT
SURVIVE its own control.  At small A the SNR is low and Re(Z)=CSD/PSD is biased toward zero, which
reproduces the -23 -> -65 shape with no mechanism.  Coherence per decile (see the sibling
`rez_dilution_control.py`) shows coherence climbing 0.292 -> 0.908 with A, and WITHIN the
high-coherence half Re(Z) is essentially FLAT: -54.6 at low A vs -57.8 at high A.

WHAT SURVIVES, and it is sharper:
  1. the 6-9 Hz anti-damping is AMPLITUDE-INDEPENDENT (~ -56) => LINEAR, not a nonlinearity;
  2. the genuine nonlinearity is at 22-30 Hz -- the GRINDING band -- where Re(Z) flips -16.9 -> +17.3
     and that DOES survive the coherence control.
The relay exclusion also stands: a relay would weaken as 1/A and nothing here strengthens that way.
See [[accord-ratchet-antidamping-is-linear]].  The original write-up follows.

ORIGINAL: a protective damping term runs out above ~2 deg/s.

THE SETUP.  Re(Z) = Re(CSD(rate,tq)/PSD(rate)) is negative at 6-9 Hz on 31/31 routes engaged
(`rez_nonrectified_replication.py`).  Both instruments are NON-RECTIFIED, so unlike every 427-derived
phase this sign is actually measured.  The open question was WHAT nonlinearity produces it, since no
set of damping LINEAR lanes can give an anti-damped system.

THE MEASUREMENT.  Bin engaged 2 s windows by A = the 6-9.5 Hz oscillation amplitude of `cs_rate`
(deg/s) and report the SIGNED median Re(Z) per decile.  Every window is kept -- an earlier log-log fit
regressed only Re(Z)<0 windows, which is a selection and a severe one in the mostly-positive control
band.

    6-9.5 Hz    A 0.25 -> -23.3   A 0.98 -> -58.6   A 3.73 -> -64.9   A 8.39 -> -62.0   rho -0.406
    22-30 Hz    A 0.30 ->  -6.2   A 1.13 -> + 1.4   A 5.35 -> +12.9   A 14.4 -> +16.1   rho +0.668

🛑 THE TWO BANDS MOVE IN OPPOSITE DIRECTIONS.  No method artefact -- filter leakage, the ratio
form, driver grip, speed -- moves two bands opposite ways, so the amplitude dependence is real and
band-specific.

WHAT THE SHAPE SAYS.  [EVIDENCE] the anti-damping DEEPENS with amplitude and PLATEAUS near -65.  That
rules the COULOMB RELAY out as the source: a relay's describing function N(A) = 4F/(pi A) makes its
contribution FALL as 1/A, so a relay source would WEAKEN with amplitude.  This strengthens.

[BELIEF, a decomposition consistent with the deciles and not the only one] read it as a FIXED anti-damper
near -65 that is partly MASKED at small amplitude by a protective damping term:

    Re(Z)(A) = -65 + D(A)/A

    A      0.245  0.353  0.454  0.573  0.743  0.983  1.359  2.061  3.732
    D(A)    10.2   10.9   10.7    8.2    8.5    6.3    6.1    3.5    0.4

D is roughly CONSTANT (~10.5) below A ~ 0.5 -- i.e. a COULOMB-like term, force not viscous, since a
viscous damper would give D proportional to A -- and then decays to nothing by A ~ 2-4 deg/s, which is
inside the record's 1-13 deg/s ratchet regime.

🛑 WHY THIS MATTERS AND HOW IT DIFFERS FROM EVERY LEVER TRIED.  If the ratchet is a protective
damping term RUNNING OUT rather than a source switching on, the fix is to EXTEND that term's range --
which ADDS damping at 6-9 Hz.  Every lever this arc has tried CUTS 6-9 Hz, which is what the standing
rule forbids and what condemned V238/V240.  This direction never touches that wall.

🛑 NOT DONE: WHICH cal sets that term.  The friction-lane saturation
([[accord-friction-lane-saturation-not-restored]]) is NOT it -- that one saturates at 250 counts of
gp-0x6abc and is 1.0x identical in the ratchet regime, by its own table.  Identifying the cell is the
next step, and nothing should be built until it is identified.

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
from scipy import signal, stats

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BAND = (6.0, 9.5)
CTL = (22.0, 30.0)
WIN_S = 2.0


def wins(t, q, r, eng, fs, band):
    lo, hi = band[0] / (fs / 2), band[1] / (fs / 2)
    if hi >= 1.0:
        return []
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = signal.hilbert(signal.filtfilt(b, a, q - q.mean()))
    ra = signal.hilbert(signal.filtfilt(b, a, r - r.mean()))
    n = int(WIN_S * fs)
    out = []
    for i in range(0, len(t) - n, n):
        sl = slice(i, i + n)
        if eng[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < 1e-6:
            continue
        out.append((float(np.sqrt(den)), float((np.mean(qq * np.conj(rr)) / den).real)))
    return out


def report(rows, label):
    if len(rows) < 200:
        print('  %s: too few windows (%d)' % (label, len(rows)))
        return
    A = np.array([a for a, _ in rows])
    Z = np.array([z for _, z in rows])
    q = np.quantile(A, np.linspace(0, 1, 11))
    print('\n  %s   %d windows, ALL kept (no sign selection)' % (label, len(rows)))
    print('  %-6s %11s %11s %11s %9s' % ('decile', 'A median', 'Re(Z) med', 'frac Re<0', 'n'))
    print('  ' + '-' * 54)
    for i in range(10):
        m = (A >= q[i]) & (A <= q[i + 1] if i == 9 else A < q[i + 1])
        if m.sum() < 5:
            continue
        print('  %-6d %11.4f %11.2f %11.3f %9d'
              % (i + 1, np.median(A[m]), np.median(Z[m]), (Z[m] < 0).mean(), m.sum()))
    print('  ' + '-' * 54)
    lr = stats.linregress(np.log(A), Z)
    rho = stats.spearmanr(A, Z)
    print('  signed Re(Z) vs log A : slope %+.2f  R2 %.3f  p %.2e' % (lr.slope, lr.rvalue ** 2, lr.pvalue))
    print('  Spearman rho(A, Re(Z)): %+.3f  p %.2e   (negative rho = anti-damping GROWS with amplitude)'
          % (rho.correlation, rho.pvalue))


def main():
    print('=' * 88)
    print('  AMPLITUDE DEPENDENCE OF Re(Z), SELECTION-FREE')
    print('=' * 88)
    print('\n  the log-log fit regressed only windows with Re(Z)<0 -- a selection, and a severe one in')
    print('  the mostly-POSITIVE 22-30 Hz control. Here every window is kept and the signed median is')
    print('  reported per amplitude decile, so the shape is visible without any fit assumption.')
    band, ctl = [], []
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not {'t', 'tq', 'cs_rate', 'cc_lat'} <= set(z.files):
            continue
        seen.add(r)
        t = np.asarray(z['t'], float)
        n = len(t)
        q = np.asarray(z['tq'], float)[:n]
        ra = np.asarray(z['cs_rate'], float)[:n]
        e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
        if len(q) < n or len(ra) < n:
            continue
        fs = 1.0 / np.median(np.diff(t))
        band += wins(t, q, ra, e, fs, BAND)
        ctl += wins(t, q, ra, e, fs, CTL)
    report(band, '6-9.5 Hz  (the ratchet band)')
    report(ctl, '22-30 Hz  (control -- engagement DAMPS here)')


if __name__ == '__main__':
    main()
