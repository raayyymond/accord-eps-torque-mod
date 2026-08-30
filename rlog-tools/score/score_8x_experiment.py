# -*- coding: utf-8 -*-
"""THE PRE-REGISTERED SCORER for the V228 -> V222 8x experiment.

    python rlog-tools/score/score_8x_experiment.py --selftest
    python rlog-tools/score/score_8x_experiment.py <v228_route> <v222_route>

WRITTEN BEFORE EITHER BUILD FLEW. That is the point: a pre-registration is only binding if the code
that executes it exists before the data does. A scorer written afterwards, against real results, is a
scorer whose choices were shaped by the answer they produced.

The spec is docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md. This file implements it and nothing
else -- no extra bands, no alternative statistics, no post-hoc filters.

WHAT IT MEASURES. V228 and V222 differ in 0xC6CD0 and its clamps and in nothing else, so the notch and
Lever B cancel and the comparison isolates the forward gain. For each build:

    per 20 s engaged episode:  ratio = mean band power / mean control power   (30-40 Hz control)
    per build:                 median over episodes of log10(ratio)
    contrast:                  V222 / V228, CI by EPISODE-level bootstrap

EPISODES, NOT WINDOWS. The kit has a standing instruction: window-level bootstraps manufacture
significance because windows inside one episode are not independent. Episodes are the resampling unit
here, and the code refuses to run if either arm has fewer than MIN_EPISODES.

PRE-REGISTERED OUTCOMES at 22-26 Hz (the decisive band):

    ratio ~ 1.65, CI excludes 1.0   -> the m^1.74 dose law STANDS
    ratio ~ 1.33, CI excludes 1.0   -> the gain acts LINEARLY; the record's exponent is too steep
    ratio ~ 1.00, TIGHT CI          -> both models REFUTED
    CI spans 1.0                    -> NOTHING. Under-exposed. Do not report a direction.

The last row is the one that matters most, and the code prints it as a refusal rather than a result.
"""
import argparse
import os
import sys

import numpy as np
from scipy.signal import welch

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BANDS = [('22-26 DECISIVE', 22.0, 26.0), ('15-22 grind', 15.0, 22.0),
         ('9-12 mid', 9.0, 12.0), ('6-9 ratchet', 6.0, 9.0)]
CTL = (30.0, 40.0)
EPISODE_S = 20.0
MIN_EPISODES = 8
N_BOOT = 5000
RNG = np.random.default_rng(20260830)
REG_OK = True

# pre-registered predictions, fixed before any data
M = 7128.0 / 5346.0
PRED_LINEAR, PRED_POWER = M, M ** 1.74


def episode_ratios(t, rate, lat, v, fs):
    """One band/control ratio per contiguous 20 s engaged episode."""
    n = int(round(EPISODE_S * fs))
    m = (lat > 0.5) & (np.abs(v) > 0.3)
    idx = np.flatnonzero(m)
    out = {b[0]: [] for b in BANDS}
    if not len(idx):
        return out
    for e in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
        for k in range(0, len(e) - n + 1, n):
            w = e[k:k + n]
            x = rate[w]
            f, p = welch(x - x.mean(), fs=fs, nperseg=min(len(w), int(round(4 * fs))))
            c = p[(f >= CTL[0]) & (f < CTL[1])].mean()
            if not np.isfinite(c) or c <= 0:
                continue
            for name, lo, hi in BANDS:
                b = p[(f >= lo) & (f < hi)].mean()
                if np.isfinite(b) and b > 0:
                    out[name].append(np.log10(b / c))
    return out


def contrast(a, b):
    """b/a as a ratio, with an episode-level bootstrap CI."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    point = 10 ** (np.median(b) - np.median(a))
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        ra = RNG.choice(a, size=len(a), replace=True)
        rb = RNG.choice(b, size=len(b), replace=True)
        boot[i] = np.median(rb) - np.median(ra)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, 10 ** lo, 10 ** hi


def verdict(point, lo, hi, registered=True):
    if not registered:
        return 'ratio only -- NOT the registered pair, no verdict is licensed'
    if lo <= 1.0 <= hi:
        return 'NOTHING -- CI spans 1.0, under-exposed. Do NOT report a direction.'
    near = lambda x, y: abs(np.log10(x / y)) < 0.06
    if near(point, PRED_POWER):
        return 'the m^1.74 dose law STANDS'
    if near(point, PRED_LINEAR):
        return 'the gain acts LINEARLY -- the record exponent is too steep'
    if point < 1.0:
        return 'BOTH MODELS REFUTED -- V222 is not worse; the m^1.74 law needs retracting'
    return 'a real effect, but at neither predicted value -- report the number, not a model'


REGISTERED = ('V228', 'V222')          # the pre-registration is about THIS pair and no other


def load(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        raise SystemExit('  no cache for %s at %s' % (tag, p))
    z = np.load(p, allow_pickle=True)
    t = np.asarray(z['t']).astype(float)
    fs = 1.0 / np.median(np.diff(t))
    build = str(z['probe_build'][0]) if 'probe_build' in z.files else '?'
    return (t, np.asarray(z['cs_rate']).astype(float), np.asarray(z['cc_lat']).astype(float),
            np.asarray(z['cs_v']).astype(float), fs), build


def report(name_a, ra, name_b, rb):
    global REG_OK
    print('  %-16s %8s %8s %10s %18s   %s'
          % ('band', 'n(228)', 'n(222)', 'ratio', '95% CI', 'licenses'))
    ok = True
    for name, _, _ in BANDS:
        a, b = ra[name], rb[name]
        if len(a) < MIN_EPISODES or len(b) < MIN_EPISODES:
            print('  %-16s %8d %8d   -- fewer than %d episodes, REFUSING to score'
                  % (name, len(a), len(b), MIN_EPISODES))
            ok = False
            continue
        pt, lo, hi = contrast(a, b)
        print('  %-16s %8d %8d %10.3f  [%6.3f, %6.3f]   %s'
              % (name, len(a), len(b), pt, lo, hi, verdict(pt, lo, hi, REG_OK)))
    return ok


def selftest():
    """Inject KNOWN ratios and confirm recovery. The scorer must pass before it sees real data."""
    print('=' * 96)
    print('  SELF-TEST -- synthetic data with known answers')
    print('=' * 96)
    fs = 100.0
    n = int(600 * fs)
    t = np.arange(n) / fs
    lat = np.ones(n)
    v = np.full(n, 10.0)

    def synth(gain_22_26):
        x = RNG.normal(0, 1.0, n)                       # broadband, sets the 30-40 control
        x += gain_22_26 * 2.0 * np.sin(2 * np.pi * 24.0 * t + RNG.uniform(0, 6.28))
        return x

    fails = 0
    for truth in (1.0, PRED_LINEAR, PRED_POWER, 2.5):
        # power ratio `truth` in the band => amplitude ratio sqrt(truth)
        a = episode_ratios(t, synth(1.0), lat, v, fs)
        b = episode_ratios(t, synth(np.sqrt(truth)), lat, v, fs)
        pt, lo, hi = contrast(a['22-26 DECISIVE'], b['22-26 DECISIVE'])
        good = lo <= truth <= hi
        fails += (not good)
        print('  injected %5.3f  ->  recovered %6.3f  [%6.3f, %6.3f]   %s'
              % (truth, pt, lo, hi, 'OK' if good else 'FAIL -- truth outside CI'))
    print()
    a = episode_ratios(t, synth(1.0), lat, v, fs)
    b = episode_ratios(t, synth(1.0), lat, v, fs)
    pt, lo, hi = contrast(a['22-26 DECISIVE'], b['22-26 DECISIVE'])
    null_ok = lo <= 1.0 <= hi
    print('  NULL control: two identical builds -> %.3f [%.3f, %.3f]  %s'
          % (pt, lo, hi, 'OK, CI spans 1.0' if null_ok else 'FAIL -- false positive'))
    print('  and its verdict reads: %s' % verdict(pt, lo, hi))
    fails += (not null_ok)

    assert fails == 0, '%d self-test failures -- do NOT score a real drive with this' % fails
    print()
    print('  [OK] the scorer recovers injected ratios and does not manufacture an effect from noise.')


# ---------------------------------------------------------------------------------------------
# AUDIO ARM -- added 2026-08-30. NOT the better instrument: an efficiency advantage was claimed and
# then WITHDRAWN -- like-for-like, every CI spans 1.0. It is kept because it is a DIFFERENT physical
# observable and alias-free at 16 kHz, where CAN's
# 30-49 Hz is not interpretable at all. CAN is PRIMARY on validity; audio is the cross-check.
# ---------------------------------------------------------------------------------------------
AUDIO_CTL = (30.0, 40.0)
AUDIO_CTL_HI = (50.0, 60.0)          # for bands that overlap the 30-40 control


def audio_episode_ratios(tag):
    """One band/control ratio per 20 s ENGAGED episode, from the *_grind.npz spectra.

    Engaged-gating is not optional: it is worth 1.5-2.4x on its own (r24: sd 0.478 -> 0.286 at
    6-9 Hz, 0.308 -> 0.131 at 15-22). The audio frames carry no engagement flag, so each is mapped
    to the nearest CAN sample.
    """
    ap = 'analysis-2020accord/_scratch/cache/%s/%s_grind.npz' % (tag, tag)
    cp = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not (os.path.exists(ap) and os.path.exists(cp)):
        return None
    g = np.load(ap, allow_pickle=True)
    z = np.load(cp, allow_pickle=True)
    if 'sp' not in g.files or 't_sp' not in g.files:
        return None
    sp = np.asarray(g['sp']).astype(float)
    f = np.asarray(g['sp_f']).astype(float)
    ta = np.asarray(g['t_sp']).astype(float)
    tc = np.asarray(z['t']).astype(float)
    lat = np.asarray(z['cc_lat']).astype(float)
    sl = lat[np.clip(np.searchsorted(tc, ta), 0, len(tc) - 1)]
    fr = 1.0 / np.median(np.diff(ta))
    n = max(2, int(round(EPISODE_S * fr)))
    out = {}
    for name, lo, hi in BANDS:
        b = (f >= lo) & (f < hi)
        c = ((f >= AUDIO_CTL[0]) & (f < AUDIO_CTL[1])) if hi <= AUDIO_CTL[0] else             ((f >= AUDIO_CTL_HI[0]) & (f < AUDIO_CTL_HI[1]))
        r = np.log10(sp[:, b].mean(axis=1) / np.maximum(sp[:, c].mean(axis=1), 1e-30))
        m = np.isfinite(r) & (sl > 0.5)
        r = r[m]
        out[name] = [float(r[i:i + n].mean()) for i in range(0, len(r) - n + 1, n)]
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('routes', nargs='*', help='<v228_route> <v222_route>')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest or not args.routes:
        selftest()
        if not args.routes:
            print()
            print('  usage: score_8x_experiment.py <v228_route> <v222_route>')
            print('  spec : docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md')
            raise SystemExit(0)

    if len(args.routes) != 2:
        raise SystemExit('  need exactly two routes: <v228_route> <v222_route>')
    ta, tb = args.routes
    print('=' * 96)
    print('  8x EXPERIMENT -- V228 (%s) vs V222 (%s), scored to the pre-registration' % (ta, tb))
    print('=' * 96)
    print('  predictions fixed in advance: linear %.3f | m^1.74 %.3f' % (PRED_LINEAR, PRED_POWER))
    print()
    da, ba = load(ta)
    db, bb = load(tb)
    REG_OK = (ba.upper().startswith(REGISTERED[0]) and bb.upper().startswith(REGISTERED[1]))
    globals()['REG_OK'] = REG_OK
    print('  route %s carries build %s   (registered: %s)' % (ta, ba, REGISTERED[0]))
    print('  route %s carries build %s   (registered: %s)' % (tb, bb, REGISTERED[1]))
    if not REG_OK:
        print()
        print('  🛑 THESE ARE NOT THE REGISTERED PAIR. Ratios are printed; NO verdict is')
        print('     licensed, because the pre-registration is about V228 vs V222 and nothing else.')
        print('     Two builds differing in something OTHER than the gain will still produce')
        print('     large ratios -- they just say nothing about the dose law.')
    print()
    aa, ab = audio_episode_ratios(ta), audio_episode_ratios(tb)
    if aa and ab:
        print('  AUDIO  (a DIFFERENT observable, alias-free at 16 kHz. NO efficiency advantage is')
        print('         established -- that claim was withdrawn 2026-08-30, CI spans 1.0.)')
        report(ta, aa, tb, ab)
        print()
    else:
        print('  AUDIO  no *_grind.npz cache for one or both routes -- extract it, audio is the')
        print('         BETTER readout (2.3-7x). rlog-tools/decode/extract_audio_grind.py')
        print()
    print('  CAN    (cross-check)')
    ra = episode_ratios(*da)
    rb = episode_ratios(*db)
    report(ta, ra, tb, rb)
    print()
    print('  [LIMIT] 30-49 Hz is NOT scored here and must not be: 52-71 Hz folds into it.')
    print('  [LIMIT] the ratchet row needs 38-116 min/arm; at normal exposure it will refuse.')
    print('  [LIMIT] the operator symptom verdict is a separate instrument and outranks this table.')
