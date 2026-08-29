# -*- coding: utf-8 -*-
"""THE ACOUSTIC ENDPOINT FOR V158 -- at CREEP, on the RATCHET band.

WHY NOT JUST RUN audio_engaged_vs_manual.py
--------------------------------------------
That tool works and is validated (16,364 blocks aligned on r24), but it answers a DIFFERENT
question.  Its comment says why:

    "the engaged/manual split is hopelessly speed-confounded on this route (52.8 vs 11.5 km/h
     median), which produces a uniform +10 dB across 20-2000 Hz.  Instead: within ENGAGED driving
     only, contrast windows with HIGH vs LOW 21-26 Hz steering-rate content, matched on speed."

That was the right call for r24.  But it leaves the analysis:
    * on 21-26 Hz -- the VIBRATION band, not the 6-9 Hz RATCHET that V158's damper targets;
    * speed-matched at 28-82 km/h -- and V158 is ARCHITECTURALLY INERT above ~35 km/h.
Run as-is on a V158 drive it would report on the wrong band at a speed where the build does nothing.

WHAT THIS DOES INSTEAD
-----------------------
PRIMARY   ENGAGED vs MANUAL, restricted to CREEP (1-24 km/h) and speed-matched.
          The r24 confound came from comparing engaged highway against manual creep.  The V158
          drive card demands a MATCHED MANUAL CREEP SEGMENT precisely so both arms sit in the same
          2-8 km/h band, which makes this contrast valid rather than confounded.
          It prints the speed medians of both arms and REFUSES if they differ by more than 2 km/h.

FALLBACK  within ENGAGED creep only, HIGH vs LOW 6-9 Hz steering-rate content, speed-matched.
          Used when the drive has engaged creep audio but no matched manual creep.  Weaker -- it
          cannot separate "the damper worked" from "less ratchet happened to occur" -- but it is
          the same design the kit already validated, retargeted to the ratchet band.

Both report 20-2000 Hz so no band is pre-committed, and both refuse loudly rather than guessing.

USAGE
    python rlog-tools/decode/audio_creep_v158.py r<N>
"""
import os
import sys

import numpy as np
from scipy import signal

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import audio_engaged_vs_manual as A                                        # noqa: E402

CACHE = A.CACHE
SR = A.SR
NF = 8192
CREEP = (1.0, 24.0)          # km/h -- V158 is inert above ~35
RATCHET = (6.0, 9.0)
FSC, NWC = 100.0, 256
BANDS = ((20, 50), (50, 60), (60, 80), (80, 120), (120, 200), (200, 300),
         (300, 800), (800, 2000), (2000, 5000))
MAX_SPEED_GAP = 2.0          # km/h between arm medians before the contrast is refused


def _windows(tag):
    blocks, bt = A.read_pcm_timed(A.ROUTES[tag])
    if not blocks:
        print('  no audio in %s' % tag)
        return None
    z = np.load(os.path.join(CACHE, tag, '%s.npz' % tag), allow_pickle=True)
    t = np.asarray(z['t']).astype(float)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    rate = np.asarray(z['cs_rate']).astype(float)
    t0 = float(np.asarray(z['t0_mono']).ravel()[0])
    at = bt - t0
    x_all = np.concatenate([b.astype(float) for b in blocks])
    n_per = np.array([len(b) for b in blocks])
    start = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    samp_t = np.interp(np.arange(len(x_all)), start, at)
    print('  %d audio blocks, span %.1f-%.1f s ; cache t span %.1f-%.1f s'
          % (len(blocks), at.min(), at.max(), t.min(), t.max()), flush=True)

    rows = []
    for a in range(0, len(x_all) - NF, NF // 2):
        i = int(np.searchsorted(t, samp_t[a + NF // 2]))
        if i <= NWC or i >= len(t) - NWC:
            continue
        sp = v[i] * 3.6
        if not (CREEP[0] <= sp < CREEP[1]):
            continue
        eng = lat[i] > 0.5
        seg_r = rate[i - NWC // 2:i + NWC // 2]
        if len(seg_r) < NWC or not np.isfinite(seg_r).all():
            continue
        fr, Pr = signal.welch(seg_r - seg_r.mean(), FSC, nperseg=NWC)
        g = (Pr[(fr >= RATCHET[0]) & (fr <= RATCHET[1])].sum()
             / max(Pr[(fr >= 1) & (fr <= 45)].sum(), 1e-30))
        seg = x_all[a:a + NF]
        f, P = signal.welch(seg - seg.mean(), SR, nperseg=NF)
        rows.append((eng, sp, g, P))
    return f, rows


def _report(f, hiP, loP, label):
    D = 10 * np.log10(np.median(hiP, 0) / np.maximum(np.median(loP, 0), 1e-30))
    print('\n  %s -- audio excess (dB):' % label)
    for lo, hi in BANDS:
        w = (f >= lo) & (f <= hi)
        print('     %5d-%5d Hz   %+6.2f dB' % (lo, hi, np.median(D[w])))
    w = (f >= 20) & (f <= 3000)
    ff, dd = f[w], D[w]
    top = np.argsort(dd)[::-1][:8]
    print('  strongest lines: %s'
          % ', '.join('%.0f Hz %+.1f' % (ff[k], dd[k]) for k in sorted(top, key=lambda k: ff[k])))


def run(tag):
    print('\n=== %s : CREEP acoustic endpoint for V158 ===' % tag, flush=True)
    got = _windows(tag)
    if got is None:
        return
    f, rows = got
    if len(rows) < 60:
        print('  ⛔ only %d creep audio windows -- NOT SCOREABLE.  The drive needs more time at'
              ' 1-24 km/h.' % len(rows))
        return
    eng = np.array([r[0] for r in rows])
    sp = np.array([r[1] for r in rows])
    g = np.array([r[2] for r in rows])
    P = np.array([r[3] for r in rows])
    print('  %d creep audio windows: %d engaged, %d manual' % (len(rows), eng.sum(), (~eng).sum()))

    # ---- PRIMARY: engaged vs manual at creep -------------------------------------------------
    if eng.sum() >= 30 and (~eng).sum() >= 30:
        lo = max(np.percentile(sp[eng], 15), np.percentile(sp[~eng], 15))
        hi = min(np.percentile(sp[eng], 85), np.percentile(sp[~eng], 85))
        me = eng & (sp >= lo) & (sp <= hi)
        mm = (~eng) & (sp >= lo) & (sp <= hi)
        if me.sum() >= 25 and mm.sum() >= 25:
            gap = abs(np.median(sp[me]) - np.median(sp[mm]))
            print('  speed-matched %.1f-%.1f km/h: engaged p50 %.1f (n=%d) vs manual p50 %.1f (n=%d),'
                  ' gap %.2f km/h' % (lo, hi, np.median(sp[me]), me.sum(),
                                      np.median(sp[mm]), mm.sum(), gap))
            if gap > MAX_SPEED_GAP:
                print('  ⛔ speed gap %.2f > %.1f km/h -- REFUSED.  This is exactly the confound that'
                      % (gap, MAX_SPEED_GAP))
                print('     produced a spurious uniform +10 dB on r24.  Falling back.')
            else:
                _report(f, P[me], P[mm], 'ENGAGED minus MANUAL at creep (PRIMARY)')
                print('  ✅ primary contrast ran speed-matched -- engine and road noise are common'
                      ' to both arms and cancel.')
                return
        else:
            print('  primary needs >=25 windows per arm after speed-matching (%d/%d) -- falling back.'
                  % (me.sum(), mm.sum()))
    else:
        print('  no matched manual creep audio (%d engaged / %d manual) -- falling back.'
              % (eng.sum(), (~eng).sum()))

    # ---- FALLBACK: within engaged creep, high vs low 6-9 Hz ----------------------------------
    e = eng
    if e.sum() < 60:
        print('  ⛔ fallback needs >=60 engaged creep windows, have %d.  NOT SCOREABLE.' % e.sum())
        return
    ge, spe, Pe = g[e], sp[e], P[e]
    hi_i = ge >= np.percentile(ge, 80)
    lo_i = ge <= np.percentile(ge, 40)
    band = (np.percentile(spe[hi_i], 20), np.percentile(spe[hi_i], 80))
    hm = hi_i & (spe >= band[0]) & (spe <= band[1])
    lm = lo_i & (spe >= band[0]) & (spe <= band[1])
    if hm.sum() < 20 or lm.sum() < 20:
        print('  ⛔ fallback arms too small after speed-matching (%d/%d).  NOT SCOREABLE.'
              % (hm.sum(), lm.sum()))
        return
    print('  FALLBACK, engaged creep only, speed-matched %.1f-%.1f km/h: %d high-ratchet vs %d low'
          % (band[0], band[1], hm.sum(), lm.sum()))
    _report(f, Pe[hm], Pe[lm], 'HIGH minus LOW 6-9 Hz steering-rate content (FALLBACK)')
    print('  ⚠ FALLBACK ONLY.  It cannot separate "the damper worked" from "less ratchet happened')
    print('    to occur".  The primary contrast needs a matched MANUAL creep segment.')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        print('  available: %s' % ' '.join(A.available()))
    else:
        for t in args:
            try:
                run(t)
            except KeyError as e:
                print('  %s' % e)
