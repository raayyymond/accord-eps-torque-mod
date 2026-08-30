#!/usr/bin/env python3
r"""HOW STRONG IS THE RULE THAT FORBIDS THE ONLY BAND WORTH FILTERING?

The torque spectrum says engagement's dominant effect is at 6-10 Hz, and that is the one band a notch
could usefully attack in the domain it acts on.  One claim forbids it, in as many words: "place a notch
only where the lane PUMPS.  Never notch 6-15 Hz on this lane."  That rule condemned V238 and V240, and
it is now the single thing standing between the kit and the strongest lever the data points to.

It rests on ONE measurement: `gp-0x6b86` phase against wheel rate, three routes (ra4/ra5/ra6), all
V104-V106, coherence-gated at 0.30.  The record labels its own limits: "3 routes, all V104-V106,
era-confounded ... the pump/damp SIGN per band is claimed; the magnitudes are not."

A rule that blocks the best available lever deserves to be re-derived properly before it is obeyed
again.  This does that, adding what the original lacked:
  * SPEED MATCHING -- the corpus's engaged/manual arms differ in speed, which this session measured
  * a ROUTE-CLUSTERED BOOTSTRAP -- the record's own rule is that the ROUTE is the bootstrap unit when
    arms differ by build; episode-level CIs are too narrow and can flip a sign
  * the sign convention stated and asserted, not assumed

\U0001f6d1 THE CONVENTION, WRITTEN DOWN BECAUSE THIS KIT HAS INVERTED IT TWICE.
`scipy.csd(x, y)` returns `arg(Y) - arg(X)`.  To get the phase of the LANE relative to WHEEL RATE we
therefore pass `csd(rate, lane)`.  The sign mapping is the kit's own, fixed by the b26 result --
"+137/+139 deg vs wheel rate, |cos| 0.73, i.e. +518/+565 counts of POSITIVE Re(Z)" for a lane it calls
"a REAL 6-9 Hz DAMPER" => **cos < 0 is DAMPING, cos > 0 is PUMPING**.

READING IT
  * cos clearly negative at 6-15 Hz with a CI excluding 0  => the rule stands, the bind is real, and
    the 6-10 Hz band must stay untouched.
  * cos marginal or CI spanning 0                          => the rule is weaker than the record
    treats it, and the strongest lever available is being blocked by an under-powered measurement.

WHAT THIS CANNOT FIX.  `gp-0x6b86` reached CAN 427 only on V104-V106, and 427 carries a different
variable per build, so no additional routes exist.  This can strengthen or weaken the claim on the data
that exists; it cannot break the era confound.

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
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROUTES = ('ra4', 'ra5', 'ra6')
BANDS = [(6, 9), (9, 12), (12, 15), (15, 22), (22, 30), (30, 40)]
COH_MIN = 0.30
SPD_BIN = 5.0
NPERSEG = 512
N_BOOT = 4000


def segments():
    out = []
    for r in ROUTES:
        for pat in (os.path.join(REPO, '_scratch', 'cache', r, r + '*.npz'),
                    os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', r, r + '*.npz')):
            for p in sorted(glob.glob(pat)):
                if p.endswith('_imu.npz') or p.endswith('_spec.npz') or p.endswith('_audio.npz'):
                    continue
                out.append((r, p))
    return out


def per_segment():
    """-> [(route, band_index, cos_phi, weight)] over speed-matched engaged frames"""
    rows = []
    for route, p in segments():
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not {'mag427', 'rate_f', 'cc_lat', 'cs_v', 't'} <= set(z.files):
            continue
        t = np.asarray(z['t'], float)
        lane = np.asarray(z['mag427'], float)
        rate = np.asarray(z['rate_f'], float)
        eng = np.asarray(z['cc_lat'], float) > 0.5
        vv = np.abs(np.asarray(z['cs_v'], float)) * 3.6
        n = min(len(t), len(lane), len(rate), len(eng), len(vv))
        if n < 4 * NPERSEG:
            continue
        t, lane, rate, eng, vv = t[:n], lane[:n], rate[:n], eng[:n], vv[:n]
        fs = 1.0 / np.median(np.diff(t))
        # SPEED-MATCHED: only the bins the manual arm also occupies
        bins = np.floor(vv / SPD_BIN).astype(int)
        if (~eng).sum() > 100:
            shared = np.intersect1d(np.unique(bins[eng]), np.unique(bins[~eng]))
            if len(shared):
                eng = eng & np.isin(bins, shared)
        if eng.sum() < 2 * NPERSEG:
            continue
        x, y = rate[eng], lane[eng]
        # csd(rate, lane) = arg(LANE) - arg(RATE): the phase of the lane relative to wheel rate
        f, Pxy = signal.csd(x, y, fs, nperseg=NPERSEG)
        _, Pxx = signal.welch(x, fs, nperseg=NPERSEG)
        _, Pyy = signal.welch(y, fs, nperseg=NPERSEG)
        coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
        for bi, (lo, hi) in enumerate(BANDS):
            m = (f >= lo) & (f < hi) & (coh >= COH_MIN)
            if m.sum() < 3:
                continue
            # power-weighted mean direction inside the band
            c = float(np.sum(np.real(Pxy[m])) / max(np.sum(np.abs(Pxy[m])), 1e-30))
            rows.append((route, bi, c, float(m.sum())))
    return rows


def main():
    rows = per_segment()
    print('=' * 92)
    print('  PUMP/DAMP RE-CHECK -- speed-matched, route-clustered bootstrap')
    print('=' * 92)
    if not rows:
        print('  no segment carried mag427 + rate_f + cc_lat + cs_v.')
        print('  \U0001f6d1 EMPTY INPUT, not a null result.')
        return
    routes = sorted({r for r, _, _, _ in rows})
    print('  %d segments across %d routes (%s)' % (len(rows), len(routes), ', '.join(routes)))
    print('  convention: csd(rate, lane) => arg(lane) - arg(rate);  cos < 0 = DAMPING')
    print()
    print('  %-10s %6s %9s %9s %22s %s' %
          ('band', 'segs', 'cos', 'record', '95% CI (route cluster)', 'verdict'))
    print('  ' + '-' * 84)
    REC = {0: -0.918, 1: -0.989, 2: -0.629, 3: +0.551, 4: +0.936, 5: +0.821}
    rng = np.random.default_rng(0)
    for bi, (lo, hi) in enumerate(BANDS):
        sub = [(r, c) for r, b, c, _ in rows if b == bi]
        if len(sub) < 3:
            continue
        vals = np.array([c for _, c in sub])
        keys = np.array([r for r, _ in sub])
        uniq = np.unique(keys)
        boots = []
        for _ in range(N_BOOT):
            drawn = rng.choice(uniq, len(uniq), True)
            pool = np.concatenate([vals[keys == k] for k in drawn])
            boots.append(np.median(pool))
        lo_ci, hi_ci = np.percentile(boots, [2.5, 97.5])
        med = float(np.median(vals))
        rec = REC.get(bi, float('nan'))
        agree = (med < 0) == (rec < 0)
        excl = (lo_ci > 0) or (hi_ci < 0)
        verdict = ('DAMPING' if med < 0 else 'PUMPING') + ('' if excl else '  (CI SPANS 0)')
        if not agree:
            verdict += '  <- SIGN DISAGREES WITH THE RECORD'
        print('  %-10s %6d %9.3f %9.3f   [%+.3f, %+.3f]   %s'
              % ('%d-%d' % (lo, hi), len(sub), med, rec, lo_ci, hi_ci, verdict))
    print('  ' + '-' * 84)
    print()
    print('  \U0001f6d1 gp-0x6b86 reached CAN 427 only on V104-V106, and 427 carries a different')
    print('     variable per build, so no additional routes exist. This can strengthen or weaken')
    print('     the claim on the data that exists; it cannot break the era confound.')


if __name__ == '__main__':
    main()
