# -*- coding: utf-8 -*-
"""
IS gp-0x6b70 A RELAY?

FUN_00038148 ends by mapping the residual magnitude through a LERP and multiplying by sgn(resid):

    uVar7 = (|resid| * cal(0xC63AE)) >> 10          cal = 1024, so uVar7 = |resid|
    sVar8 = LERP(uVar7)  over X at gp-0x64b6.., Y at gp-0x641c..
    gp-0x6b70 = sgn(resid) * sVar8,  clamped to +-cal(0xC6200) = 8192

If that LERP saturates early, the stage is a SIGNED CONSTANT -- i.e. a relay -- and the record blames
the ratchet on exactly that: "Engagement amplifies 6-9 Hz 2.8x via a COMMAND-PROPORTIONAL COULOMB
RELAY".  The LERP's knots live in RAM two hops from any cal, so read the OUTPUT instead: V96-V99 all
carried the CAN 427 tap on gp-0x6b70 (V100's changelog repoints it AWAY from gp-0x6b70, which dates
the earlier builds' target unambiguously).

SHAPE IS SCALE-INVARIANT, so this needs no decode scaling -- a relay piles its mass at the rails.
And per the standing rule, the control runs FIRST: cs_tq is a smooth analogue channel on the same
frames; if the statistic calls IT saturated too, the statistic is broken, not the signal.
"""
import glob
import sys

import numpy as np

C = 'analysis-2020accord/_scratch/cache'


def is_continuous(x, min_levels=64):
    """A shape statistic on a BIT-FIELD is meaningless.  This caught a real error: r80/r81/r82's
    `probe` and `field` take only 4-6 distinct values spaced 64 and 16 apart -- the cave's packed
    boolean rungs, not a magnitude -- and a rail-mass computed on them looked like a finding.
    Refuse rather than report."""
    x = x[np.isfinite(x)]
    return np.unique(x).size >= min_levels


def rails(x, lo=0.10):
    """Fraction of mass within lo of either extreme, after normalising to [0,1]."""
    x = x[np.isfinite(x)]
    if x.size < 200:
        return float('nan')
    a, b = np.nanpercentile(x, 0.5), np.nanpercentile(x, 99.5)
    if b <= a:
        return float('nan')
    u = np.clip((x - a) / (b - a), 0, 1)
    return float(((u <= lo) | (u >= 1 - lo)).mean())


print('=' * 92)
print('  IS gp-0x6b70 A RELAY?  rail-mass = fraction within 10 % of either extreme')
print('  a relay piles mass at the rails; a smooth LERP output does not')
print('=' * 92)
print('  route   frames   engaged   PROBE (gp-0x6b70)   cs_tq CONTROL   cs_rate CONTROL')
print('  ' + '-' * 84)
for r in ('r80', 'r81', 'r82'):
    f = glob.glob(f'{C}/{r}/{r}.npz')
    if not f:
        continue
    d = np.load(f[0], allow_pickle=True)
    eng = np.asarray(d['cc_lat']).astype(float) > 0.5
    pr = np.asarray(d['probe']).astype(float)
    tq = np.asarray(d['cs_tq']).astype(float)
    rc = np.asarray(d['cs_rate']).astype(float)
    n = min(len(pr), len(tq), len(rc), len(eng))
    eng, pr, tq, rc = eng[:n], pr[:n], tq[:n], rc[:n]
    if eng.sum() < 200:
        print(f'  {r}     {n:6d}   {int(eng.sum()):6d}   (too little engaged exposure)')
        continue
    if not is_continuous(pr[eng]):
        lv = np.unique(pr[eng][np.isfinite(pr[eng])])
        print('  %-6s  %6d   %6d      REFUSED -- probe takes only %d distinct values %s'
              % (r, n, int(eng.sum()), lv.size,
                 '[' + ' '.join('%g' % v for v in lv[:8]) + ']'))
        print('           that is a packed BOOLEAN RUNG byte, not a magnitude. A shape statistic')
        print('           on it is meaningless. Fly a build with a magnitude tap (V205).')
        continue
    print('  %-6s  %6d   %6d      %8.3f          %8.3f        %8.3f'
          % (r, n, int(eng.sum()), rails(pr[eng]), rails(tq[eng]), rails(rc[eng])))

print()
print('  DECILES of the probe on engaged frames -- a relay is U-shaped, a LERP output is not')
for r in ('r80', 'r81', 'r82'):
    f = glob.glob(f'{C}/{r}/{r}.npz')
    if not f:
        continue
    d = np.load(f[0], allow_pickle=True)
    eng = np.asarray(d['cc_lat']).astype(float) > 0.5
    pr = np.asarray(d['probe']).astype(float)
    n = min(len(pr), len(eng))
    pr, eng = pr[:n], eng[:n]
    if eng.sum() < 200:
        continue
    if not is_continuous(pr[eng]):
        print('  %-5s  REFUSED (discrete rung byte)' % r)
        continue
    x = pr[eng]
    a, b = np.nanpercentile(x, 0.5), np.nanpercentile(x, 99.5)
    u = np.clip((x - a) / max(b - a, 1e-9), 0, 1)
    h, _ = np.histogram(u, bins=10, range=(0, 1))
    h = 100.0 * h / h.sum()
    print('  %-5s  ' % r + ' '.join('%4.1f' % v for v in h) + '   %%')
