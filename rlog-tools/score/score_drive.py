# -*- coding: utf-8 -*-
"""
ONE COMMAND TO SCORE A DRIVE.   python rlog-tools/score/score_drive.py <route-tag>

The iteration doctrine requires every build to be interpretable from ONE short symptomatic drive.
That is not only a property of the build -- the ANALYSIS has to be runnable too, and it was not:
there are ~40 scoring tools in this directory and nothing says which to run or in what order.  This
runs every endpoint that is pre-registered for the current shelf, and prints each against the number
that was registered BEFORE the drive.

It never invents a value.  A channel that is absent, degenerate, or under-exposed is reported as
such and excluded, because a degenerate rung is an UNINTERPRETABLE reading, not a null -- a
distinction this kit has repeatedly got wrong.
"""
import glob
import math
import os
import sys

import numpy as np

C = 'analysis-2020accord/_scratch/cache'
BITS = (7, 6, 5, 4, 3)
RNG = np.random.default_rng(20260829)


def load(tag):
    p = glob.glob(f'{C}/{tag}/{tag}.npz')
    if not p:
        return None
    return np.load(p[0], allow_pickle=True)


def episodes(mask, minlen=100):
    out, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j < n and mask[j]:
            j += 1
        if j - i >= minlen:
            out.append((i, j))
        i = j
    return out


def hdr(s):
    print('\n' + '=' * 92)
    print('  ' + s)
    print('=' * 92)


def main(tag):
    z = load(tag)
    if z is None:
        print(f'no cache for {tag} -- expected {C}/{tag}/{tag}.npz')
        return 1
    have = set(z.files)
    lat = np.asarray(z['cc_lat']).astype(float) > 0.5 if 'cc_lat' in have else None
    if lat is None:
        print('no cc_lat -- cannot separate engaged frames; nothing here is interpretable')
        return 1
    n = len(lat)
    eps = episodes(lat)

    hdr(f'DRIVE {tag}  --  exposure first, because every endpoint below depends on it')
    print(f'  frames {n}   engaged {int(lat.sum())} ({100.0 * lat.mean():.1f} %)'
          f'   episodes >=100 frames: {len(eps)}')
    if 'cs_v' in have:
        v = np.asarray(z['cs_v']).astype(float)[:n][lat]
        if v.size:
            print('  engaged speed m/s   p10 %.2f  p50 %.2f  p90 %.2f  max %.2f'
                  % tuple(np.percentile(v, [10, 50, 90]).tolist() + [v.max()]))
    if int(lat.sum()) < 1500:
        print('  !! under 1500 engaged frames -- treat every number below as indicative only')
    if len(eps) < 3:
        print('  !! fewer than 3 engaged episodes -- no episode bootstrap is meaningful')

    # ---- the cave rungs, free on every shelf build (cave byte-identical v105..v202) --------
    hdr('CAVE RUNGS  --  free on every shelf build; the cave is byte-identical v105..v202')
    key = 'probe' if 'probe' in have else ('raw14_b4' if 'raw14_b4' in have else None)
    if key is None:
        print('  no probe byte in this cache')
    else:
        p = np.asarray(z[key]).astype(int)[:n][lat]
        lv = np.unique(p)
        print('  probe byte: %d distinct values engaged %s' % (lv.size, [int(v) for v in lv[:8]]))
        duty = {b: float(((p >> b) & 1).mean()) for b in BITS}
        MEAN = {7: 'sign rung', 6: 'b6 = |gp-0x6b94| >= |gp-0x4f64|  the GOVERNOR CLIP',
                5: 'b5 = |friction| >= |INERTIA|   THE RATCHET LEVER', 4: 'sign rung',
                3: 'identity -- must VARY or the run is INVALID'}
        for b in BITS:
            d = duty[b]
            tagd = ' DEGENERATE (uninterpretable, not a null)' if d in (0.0, 1.0) else ''
            print(f'   b{b}  {d:.6f}{tagd}   {MEAN[b]}')
        print()
        # b3: the recorded run-validity gate
        if duty[3] in (0.0, 1.0):
            print('  !! b3 IS CONSTANT -- the lineage calls this RUN-INVALIDATING, not a finding.')
        else:
            print('  b3 varies -> the cave is alive and the run is valid.')
        # b6: expected dead
        print('  b6 expected 0.000000 (measured dead on routes a5 and a6, 49k and 124k frames).'
              + ('  As expected.' if duty[6] == 0.0 else '  ** NON-ZERO -- that is NEW. **'))
        # b5: the pre-registered ratchet endpoint
        b5 = duty[5]
        print()
        print('  ** PRE-REGISTERED: b5 should read 0.42, plausible range 0.31-0.49 **')
        print('     (V105 measured 0.2798 at 1.000x the inertia dose; the shelf runs 0.333x.')
        print('      Derived from the V105->V106 pair: doubling the dose moved b5 -0.0891,')
        print('      CI [-0.1328, -0.0200], with both sign rungs as null controls.)')
        SHELF = {'v199','v202','v204','v205','v206'}
        known = tag.lower().lstrip('r') in SHELF or any(k in tag.lower() for k in SHELF)
        if not known:
            print(f'     b5 = {b5:.4f}  -- but this route is NOT a shelf build, so the')
            print('     prediction above DOES NOT APPLY to it. The 0.42 figure is for the 0.333x')
            print('     inertia dose the shelf carries; older routes ran other doses.')
        elif b5 in (0.0, 1.0):
            print(f'     b5 = {b5:.6f} DEGENERATE -> uninterpretable, NOT a null.')
        elif b5 <= 0.28:
            print(f'     b5 = {b5:.4f}  <= 0.28  ** THE HALVED INERTIA IS NOT REACHING THE CAR. **')
            print('     That retires the ratchet lever on the shelf -- the most useful null available.')
        elif 0.31 <= b5 <= 0.49:
            print(f'     b5 = {b5:.4f}  INSIDE the pre-registered range -- the lever reaches the car.')
        else:
            print(f'     b5 = {b5:.4f}  outside [0.31, 0.49] but above 0.28 -- direction right,')
            print('     magnitude off; report it, do not re-fit the prediction after the fact.')

    # ---- the 427 dose channel --------------------------------------------------------------
    hdr('CAN 427 DOSE CHANNEL')
    if 'ab_mt' not in have:
        print('  no ab_mt in this cache -- no 427 magnitude channel')
    else:
        mt = np.asarray(z['ab_mt']).astype(float)
        if 'ab_t1ab' in have and 't' in have:
            t427 = np.asarray(z['ab_t1ab']).astype(float)
            tb = np.asarray(z['t']).astype(float)
            m = min(len(tb), len(lat))
            k = min(len(mt), len(t427))
            e427 = np.interp(t427[:k], tb[:m], lat[:m].astype(float)) > 0.5
            mte = mt[:k][e427]
        else:
            mte = mt
            print('  (no 427 timebase -- engagement NOT aligned; treat as whole-drive)')
        if mte.size < 200:
            print(f'  only {mte.size} engaged 427 frames -- not interpretable')
        else:
            print(f'  {mte.size} engaged 427 frames   raw p50 {np.percentile(mte, 50):.0f}'
                  f'  p95 {np.percentile(mte, 95):.0f}  max {mte.max():.0f}  (10-bit field)')
            print('  !! the DECODE depends on which build flew -- run the matching decoder:')
            print('     V204 -> rlog-tools/probe/decode_v204_observer_lane.py   (gp-0x6b4e, sar 5)')
            print('     V205 -> rlog-tools/probe/decode_v205_observer_output.py (gp-0x6b70, sar 6)')
            print('     they refuse a route that is not theirs, which is the point.')

    # ---- the grind band, stratified by THIS drive's own peak --------------------------------
    hdr('GRIND BAND  --  stratified by this drive\'s own peak, never pooled')
    ch = 'cs_rate' if 'cs_rate' in have else None
    if ch is None:
        print('  no cs_rate channel')
    elif len(eps) == 0:
        print('  no engaged episodes long enough to spectrum')
    else:
        try:
            from scipy import signal
        except Exception:
            print('  scipy unavailable')
            return 0
        x = np.asarray(z[ch]).astype(float)[:n]
        FS = 100.0
        pk, pw = [], []
        for a, b in eps:
            seg = x[a:b]
            if len(seg) < 256:
                continue
            f, P = signal.welch(seg - seg.mean(), FS, nperseg=min(256, len(seg)))
            band = (f >= 15) & (f <= 25)
            if not band.any():
                continue
            pk.append(f[band][int(np.argmax(P[band]))])
            pw.append(P[band].sum())          # BAND ENERGY, not the peak height
        if not pk:
            print('  no episode long enough for a 15-25 Hz spectrum')
        else:
            pk, pw = np.array(pk), np.array(pw)
            # POWER-WEIGHT the peak. An unweighted median gives an episode with 1 % of the grind
            # the same vote as one with 20 %, and route r97 -- which has 0.01x the corpus median
            # band energy -- produced a confident 15.8 Hz "peak" that was argmax on a flat
            # spectrum. Weighting by band energy removes that class of artefact without a cutoff.
            o = np.argsort(pk)
            cw = np.cumsum(pw[o]) / pw.sum()
            wmed = float(np.interp(0.5, cw, pk[o]))
            print(f'  per-episode 15-25 Hz peak: median {np.median(pk):.2f} Hz'
                  f'  min {pk.min():.2f}  max {pk.max():.2f}   ({len(pk)} episodes)')
            print(f'  ** POWER-WEIGHTED median {wmed:.2f} Hz ** -- this is the one to trust;'
                  ' an episode votes by how much grind it actually has')
            share = np.sort(pw)[::-1]
            k = int(np.searchsorted(np.cumsum(share) / share.sum(), 0.5)) + 1
            print(f'  {k} of {len(pk)} episodes carry half this drive\'s band energy')
            if pw.max() < 1e-9:
                print('  !! this drive has essentially NO band energy -- the peak above is noise')
            print()
            print('  ** V208 notch at 20.50 Hz. Expected attenuation vs where this drive sat:')
            print('       16.5 Hz -> 2.1x     19.5 Hz ->  9.2x     21.5 Hz -> 10.3x')
            print('       18.0 Hz -> 3.4x     20.5 Hz -> the null   22.5 Hz ->  5.4x')
            print('     Corpus-wide V208 removes 14.9x of total band ENERGY. The per-episode')
            print('     figure varies because a single biquad is a point fix, and the corpus')
            print('     band spectrum peaks at 21.09 Hz with a shoulder out to 23.4.')
    print()
    print('  Everything above is measured or explicitly absent. Nothing here is a symptom score --')
    print('  bands are instruments; only the operator scores grinding, ratcheting and stuttering.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python rlog-tools/score/score_drive.py <route-tag>')
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
