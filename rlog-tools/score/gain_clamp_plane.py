#!/usr/bin/env python3
r"""THE (GAIN, CLAMP) PLANE -- find the operating point, do not guess it.

WHY.  The kit has been treating the forward gain as THE authority knob, and the clamp as something
that merely tracks it (`clamp = gain * 512 // 891` held exactly from V22 through V108).  That
tracking rule is a convention, not a constraint, and breaking it opens a two-dimensional space that
has never been searched.

The two dimensions do different things:

    gain   sets torque per unit of command BELOW the rail, and sets the loop gain around the
           21.4 Hz mechanical mode.  It is also the ratchet's anti-damping (~ -6.6 of Re(Z) per 1x,
           from the 3-dose median over 16 flown builds -- see gain_clamp_collinearity.py).
    clamp  sets PEAK delivered torque and the command at which the loop rails.  Believed to have no
           effect on Re(Z) -- but see the collinearity caveat below, which is why "believed".

So the gain is the only thing that costs ratchet, and the clamp is the only thing that sets peak.
Searching them jointly is the whole point.

MODEL, and its weak point stated up front:
    delivered = min(|cmd| * gain / 891, clamp)
    Re(Z)     = CAR_REZ + (gain/891 - 6.0) * SLOPE_PER_X
    "compensated" mean assumes openpilot winds up to hold the same lane error BELOW the rail, so
    only rail-clipped frames actually lose authority.

\U0001f6d1 [BELIEF] the compensation model is optimistic -- it assumes openpilot recovers the full gain
ratio below the rail, which holds only while its own authority and rate limits are not binding.  The
rail-duty column is the honest bound on how often that fails.
\U0001f6d1\U0001f6d1 THE SLOPE IS CONFOUNDED WITH THE CLAMP, NOT MERELY WITH ERA -- the serious caveat.
The tracking rule `clamp = gain * 512 // 891` was held EXACTLY on all 16 flown builds (4x->2048,
6x->3072, 8x->4096), so gain and clamp are PERFECTLY COLLINEAR in the corpus.  Nothing in the data
distinguishes "lower gain helps" from "lower clamp helps"; both fit all 16 exactly.  And they make
OPPOSITE predictions for every configuration ranked below, since all of them RAISE the clamp.
**V256 (clamp 4096 with the gain held at the car's 6x) is the first build ever to break the tracking,
so it is the disambiguating experiment.**  Run gain_clamp_collinearity.py before trusting this table.
\U0001f6d1 THE 5119 CAP HERE IS CONSERVATISM, NOT A STRUCTURAL LIMIT.  The old "the clamp must stay under
0xC674E = 5120" rule was settled UNFOUNDED 2026-08-27 three ways: disjoint reader sets, disjoint
dataflow (0xC674E's corridor is indexed by driver column torque), and the relation has already
diverged on-car -- 0xC674E frozen at 5120 while the clamps went 2048 -> 4096 -> 3072, with V101
flying a ratio of 1.25 without faulting.  The cap is kept only because no build has ever run a
clamp above 4096.  Do NOT abort a build on that rule -- but DO leave the mirrored INT/FLOAT quad
alone; that pair is what V27 hard-faulted on.

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

STOCK = 891.0
CAR_GAIN, CAR_CLAMP = 5346.0, 3072      # V112 / the car
CAR_REZ = -64.77
SLOPE_PER_X = -6.6      # CORRECTED 2026-08-30: 3-dose median over 16 flown builds
                        # (4x -55.37, 6x -68.49, 8x -84.06). The old -4.4 came from a single
                        # era-free contrast (V101->V102). See gain_clamp_collinearity.py.
EME_WALL = 5120                          # 0xC674E -- the clamp must stay strictly under this


def commands():
    out, seen = [], set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        seen.add(r)
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not {'co_tqcan', 'cc_lat'} <= set(z.files):
            continue
        c = np.abs(np.asarray(z['co_tqcan'], float))
        e = np.asarray(z['cc_lat'], float) > 0.5
        n = min(len(c), len(e))
        out.append(c[:n][e[:n]])
    return np.concatenate(out) if out else None


def row(cmd, mult, clamp):
    g = STOCK * mult
    thr = clamp * STOCK / g                       # command at which it rails
    rail = float((cmd >= thr).mean())
    # compensated: openpilot winds up to hold the same lane error below the rail
    comp = float(np.mean(np.minimum(cmd * CAR_GAIN / STOCK, clamp)))
    rez = CAR_REZ + (mult - 6.0) * SLOPE_PER_X
    return thr, rail, comp, clamp, rez


def main():
    print('=' * 94)
    print('  THE (GAIN, CLAMP) PLANE  --  the clamp/gain tracking rule is a convention, not a limit')
    print('=' * 94)
    cmd = commands()
    if cmd is None or len(cmd) < 1000:
        print('  no command data.')
        return
    print('\n  %d engaged frames of real openpilot command.' % len(cmd))
    print('  peak delivered torque IS the clamp.  The Re(Z) column MODELS the effect as')
    print('  gain-only -- which the flown corpus cannot verify. See the caveat below.\n')

    base = row(cmd, 6.0, CAR_CLAMP)
    print('  %-16s %7s %8s %9s %9s %8s %9s'
          % ('config', 'rail@cmd', 'rail%', 'mean tq', 'peak tq', 'Re(Z)', 'vs car'))
    print('  ' + '-' * 78)
    print('  %-16s %7.0f %7.1f%% %9.0f %9d %8.1f %9s'
          % ('THE CAR 6.0x/3072', base[0], 100 * base[1], base[2], base[3], base[4], '--'))
    print('  ' + '-' * 78)

    best = []
    for mult in (4.0, 4.5, 5.0, 5.5, 6.0):
        for clamp in (3072, 4096, 4608, 5119):
            if clamp >= EME_WALL:
                continue
            thr, rail, comp, pk, rez = row(cmd, mult, clamp)
            d_tq = 100 * (comp / base[2] - 1)
            d_pk = 100 * (pk / base[3] - 1)
            d_rez = rez - base[4]
            d_rail = 100 * (rail / base[1] - 1) if base[1] else 0.0
            # a configuration is only interesting if it beats the car on BOTH torque and ratchet
            win = d_tq > 0 and d_rez > 0 and d_rail < 0
            best.append((d_rez + d_tq / 5.0, mult, clamp, thr, rail, comp, pk, rez,
                         d_tq, d_pk, d_rez, d_rail, win))

    best.sort(reverse=True)
    print('\n  ALL CONFIGURATIONS THAT BEAT THE CAR ON TORQUE *AND* RATCHET *AND* RAIL TIME:')
    print('  %-13s %7s %8s %9s %9s %8s %8s'
          % ('gain/clamp', 'rail@', 'rail%', 'mean tq', 'peak tq', 'Re(Z)', 'built?'))
    print('  ' + '-' * 78)
    NAMED = {(6.0, 4096): 'V256', (5.0, 4096): 'V257', (6.0, 3072): 'the car'}
    any_win = False
    for sc, mult, clamp, thr, rail, comp, pk, rez, d_tq, d_pk, d_rez, d_rail, win in best:
        if not win:
            continue
        any_win = True
        print('  %-13s %7.0f %7.1f%% %+8.1f%% %+8.1f%% %+7.1f %8s'
              % ('%.1fx / %d' % (mult, clamp), thr, 100 * rail, d_tq, d_pk, d_rez,
                 NAMED.get((mult, clamp), '')))
    if not any_win:
        print('  (none)')
    print('  ' + '-' * 78)
    print('  columns after rail%% are DELTAS vs the car.  peak tq delta is the clamp ratio exactly.')
    print('\n  \U0001f6d1 clamp capped at %d here as CONSERVATISM, not a structural limit -- the'
          % 5119)
    print('     "must stay under 0xC674E = %d" rule was settled unfounded 2026-08-27.' % EME_WALL)
    print('     (Do still leave the mirrored INT/FLOAT quad alone: that is the V27 class.)')
    print('  \U0001f6d1\U0001f6d1 GAIN AND CLAMP ARE PERFECTLY COLLINEAR IN ALL 16 FLOWN BUILDS, so the')
    print('     Re(Z) column assumes the effect is the GAIN\'s. If it is the CLAMP\'s instead,')
    print('     every row above is WRONG IN SIGN -- they all RAISE the clamp. V256 settles it.')
    print('  \U0001f6d1 [BELIEF] the compensation model assumes openpilot winds up below the rail.')


if __name__ == '__main__':
    main()
