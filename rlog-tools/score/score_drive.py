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
import re
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
        print('  ** PRE-REGISTERED: b5 scales with the INERTIA DOSE the build carried **')
        print('     V105 measured 0.2798 at 1.000x the dose. From the V105->V106 single-cell')
        print('     pair, DOUBLING the dose moved b5 by -0.0891, CI [-0.1328, -0.0200], with')
        print('     both sign rungs as null controls.')
        # A route tag does NOT encode the build -- 'ra5' and 'r80' contain no version at all --
        # so matching tag against a build list was wrong in concept, not merely stale. The b5
        # prediction depends on ONE thing: the inertia dose the flown build carried. So take the
        # build explicitly and READ that dose out of its image. Nothing here can rot.
        build = None
        for _x in sys.argv[1:]:
            if re.match(r'^--build=?', _x):
                build = _x.split('=', 1)[1] if '=' in _x else None
            elif build is None and re.match(r'^[Vv]\d+[A-Za-z]?$', _x):
                build = _x
        dose = None
        if build:
            import glob as _g
            import struct as _st
            _root = os.environ.get('ACCORD_FIRMWARE_ROOT',
                                   'C:/Users/dudei/Desktop/Projects/accord-firmwares')
            _hits = [f for f in _g.glob(os.path.join(_root, 'analysis-2020accord',
                                                     '_%s_*plain_image.bin' % build.lower()))
                     if 'SUPERSEDED' not in os.path.basename(f)]
            if _hits:
                _b = open(_hits[0], 'rb').read()
                _y = [_st.unpack_from('<h', _b, 0xD7A5C + 2 * _i)[0] for _i in range(3)]
                # V105 flew mean|Y| = 8765 at 1.000x and measured b5 = 0.2798
                dose = (sum(abs(v) for v in _y) / 3.0) / 8765.0
        if dose is None:
            print(f'     b5 = {b5:.4f}  -- pass the build to interpret this, e.g.')
            print('       python rlog-tools/score/score_drive.py <tag> V209')
            print('     The prediction depends on the INERTIA DOSE the flown build carried, and a')
            print('     route tag does not encode the build. Without it this number is just a number.')
        else:
            # b5 moved -0.0891 per DOUBLING of the dose (V105->V106, CI [-0.1328, -0.0200])
            import math as _m
            _exp = 0.2798 + (-0.0891) * _m.log2(dose) if dose > 0 else float('nan')
            _lo = 0.2798 + (-0.1328) * _m.log2(dose)
            _hi = 0.2798 + (-0.0200) * _m.log2(dose)
            _lo, _hi = min(_lo, _hi), max(_lo, _hi)
            print(f'     {build.upper()} carries inertia dose {dose:.3f}x (read from its image);')
            print('     the BUILD is taken on trust from your argument -- a route tag does not')
            print('     encode it, so name the build you actually flashed.')
            print(f'     => predicted b5 {_exp:.2f}, CI-propagated range {_lo:.2f}-{_hi:.2f}')
            if b5 in (0.0, 1.0):
                print(f'     b5 = {b5:.6f} DEGENERATE -> uninterpretable, NOT a null.')
            elif dose < 1.0 and b5 <= 0.2798:
                print(f'     b5 = {b5:.4f} <= 0.2798 (the 1.000x reference) ** THE REDUCED INERTIA')
                print('     IS NOT REACHING THE CAR ** -- that retires the ratchet lever.')
            elif _lo <= b5 <= _hi:
                print(f'     b5 = {b5:.4f}  INSIDE the predicted range -- the lever reaches the car.')
            else:
                print(f'     b5 = {b5:.4f}  outside [{_lo:.2f}, {_hi:.2f}] -- report it as measured;')
                print('     do not re-fit the prediction after the fact.')
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
    # ---- the 30-49 Hz band: V213's ONE stated residual risk ------------------------------
    hdr('30-49 Hz CONTROL BAND  --  where the notch gives NOTHING back')
    # The V208/V212/V213 notch attenuates 3.59x at 22-26 Hz but its skirt runs out: break-even
    # against a gain raise is 29.5 Hz, and above that a 6x->8x step (V211/V213) raises loop
    # gain 1.65x unopposed.  The scorer previously looked ONLY at 15-25 Hz, so the one band
    # that build could plausibly make WORSE was the one band nothing measured.
    #
    # This is also where grind #2 lived: 40-49 Hz corner tail 11.71x (p=0.0003), IMU p95 6.27x,
    # acoustic +9.7 dB(A) -- created by V62's rate-lane x2.  V212/V213 are byte-stock at
    # 0x3AB76/0x3AC20 so that lever is ABSENT, which is a prediction this band can check.
    #
    # !! Everything in the cache is resampled to 100 Hz, so Nyquist is 50 Hz. 30-40 Hz is
    # comfortable; 40-49 Hz sits at 80-98% of Nyquist and is the noisiest part of this readout.
    # The kit's own grind-#2 result came off these same 100 Hz caches, so it is established
    # practice -- but treat a 40-49 Hz move as weaker evidence than a 30-40 Hz one.
    if ch is None or len(eps) == 0:
        print('  no channel or no engaged episodes')
    else:
        try:
            from scipy import signal as _sg
        except Exception:
            print('  scipy unavailable')
            _sg = None
        if _sg is not None:
            for _cn in ('cs_rate', 'imu_vert', 'imu_lat'):
                if _cn not in have:
                    continue
                _x = np.asarray(z[_cn]).astype(float)[:n]
                _lo, _mid, _hi, _ref = [], [], [], []
                for _a, _b in eps:
                    _seg = _x[_a:_b]
                    if len(_seg) < 256:
                        continue
                    _f, _P = _sg.welch(_seg - _seg.mean(), 100.0, nperseg=min(256, len(_seg)))
                    _ref.append(_P[(_f >= 15) & (_f <= 25)].sum())
                    _mid.append(_P[(_f >= 30) & (_f < 40)].sum())
                    _hi.append(_P[(_f >= 40) & (_f <= 49)].sum())
                if not _ref:
                    continue
                _ref = float(np.sum(_ref)); _m = float(np.sum(_mid)); _h = float(np.sum(_hi))
                if _ref <= 0:
                    print(f'  {_cn:9s} 15-25 Hz energy is zero -- ratios undefined')
                    continue
                print(f'  {_cn:9s} 30-40 Hz / grind = {_m / _ref:7.4f}    40-49 Hz / grind = {_h / _ref:7.4f}')
            print()
            print()
            # CORPUS BASELINE, cs_rate, 23 cached routes, computed 2026-08-29.
            #   30-40/grind  median 0.0365  IQR 0.0275-0.0561
            #   40-49/grind  median 0.0212  IQR 0.0138-0.0344
            # r7d is a real outlier at 10.16 (278x the median) with mid-range 15-25 energy,
            # i.e. a genuine large 30-40 Hz event, not a small-denominator artefact. Medians
            # and IQRs above are robust to it. UNEXPLAINED -- worth a look if it recurs.
            print('  CORPUS BASELINE (cs_rate, 23 routes, pre-notch):')
            print('     30-40 Hz / grind   median 0.0365   IQR 0.0275-0.0561')
            print('     40-49 Hz / grind   median 0.0212   IQR 0.0138-0.0344')
            print()
            print('  These are RATIOS to this drive\'s own 15-25 Hz energy, so they are')
            print('  self-normalising. But the notch REMOVES 15-25 Hz energy -- corpus-wide')
            print('  14.9x -- so on ANY notch build the ratio RISES ~15x with the upper band')
            print('  completely unchanged. Expected on a clean notch drive:')
            print('     30-40 Hz / grind  ~0.54       40-49 Hz / grind  ~0.32')
            print()
            print('  !! WHAT THIS CAN AND CANNOT SETTLE, stated up front:')
            print('  V213 raises loop gain 1.65x above 29.5 Hz vs V212. That would move the')
            print('  30-40 ratio 0.54 -> 0.90. But the corpus IQR spans a factor of 2.0, which')
            print('  is WIDER than the 1.65x effect. So ONE drive CANNOT resolve whether the')
            print('  gain step costs anything here. Do not claim it either way from one route.')
            print()
            print('  What ONE drive CAN settle: a grind-#2-scale event. That was 11.71x, and')
            print('  r7d shows the band does register such things (10.16 vs 0.0365 median).')
            print('  So read this band as a LARGE-EXCURSION DETECTOR:')
            print('     30-40 ratio  <~2      nothing broke -- the gain step is safe to keep')
            print('     30-40 ratio  >~5      something broke at 30-40 Hz -- fall back to V212')
            print('  and treat anything between as UNRESOLVED, needing a matched V212 drive.')
            print()
            print('  40-49 Hz sits at 80-98% of the 100 Hz Nyquist and is the noisiest part')
            print('  of this readout -- weight a 30-40 Hz move above a 40-49 Hz one.')

    print()
    print('  Everything above is measured or explicitly absent. Nothing here is a symptom score --')
    print('  bands are instruments; only the operator scores grinding, ratcheting and stuttering.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python rlog-tools/score/score_drive.py <route-tag>')
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
