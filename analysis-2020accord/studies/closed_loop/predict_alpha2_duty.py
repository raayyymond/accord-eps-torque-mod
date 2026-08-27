"""Rail duty above the 1636.8-count wire censor, by censored-MLE tail fitting.

The bracket in run_v108_alpha2.py collapses because lowering alpha2 pushes the
rail threshold past the CAN-427 wire rail, where the measured |gp-0x6c2c| is
right-censored. This script fits a tail to the UNCENSORED part and extrapolates.

THE CONTROL COMES FIRST AND IT IS A REAL ONE: refit with the censor moved down
to 1400 counts -- throwing away data that is actually observed -- then predict
P(|c2c| >= 1636.8) and compare against the directly measured value. A tail model
that cannot recover a censoring fraction it was not shown does not get to
extrapolate past it.
"""
import sys, os
import numpy as np
from scipy import optimize, stats

_HERE = os.path.dirname(os.path.abspath(__file__))
_KIT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, os.path.join(_KIT, 'model'))
from eps_closed_loop_sim import (Calibration, ratio_filter, WIRE_RAIL)  # noqa: E402

FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                    'C:/Users/dudei/Desktop/Projects/accord-firmwares')
IMG = FW + '/analysis-2020accord/'
V107 = IMG + '_v107_V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3_plain_image.bin'
V108 = IMG + '_v108_V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5_plain_image.bin'
CACHE = os.path.join(_KIT, '_scratch', 'cache')
U = 900.0                      # tail threshold, well inside the observed range


def load(route):
    d = np.load(os.path.join(CACHE, route, route + '.npz'), allow_pickle=True)
    m = np.isfinite(d['x6c2c_mag']) & (d['cc_lat'] > 0.5)
    return d['x6c2c_mag'][m], d['cs_v'][m] * 3.6, d['seg'][m]


# --------------------------------------------------------------------------
# censored MLE for the exceedance tail
# --------------------------------------------------------------------------
def fit_tail(x, u, censor, family='gpd'):
    """x: all samples. Exceedances over u, right-censored at `censor`."""
    exc = x[x >= u]
    if len(exc) < 50:
        return None
    y = exc - u
    obs = y[exc < censor - 1e-6]
    ncen = int((exc >= censor - 1e-6).sum())
    ycen = censor - u

    if family == 'gpd':
        def nll(p):
            xi, sig = p
            if sig <= 0:
                return 1e12
            def logsf(t):
                if abs(xi) < 1e-8:
                    return -t / sig
                z = 1 + xi * t / sig
                if np.any(z <= 0):
                    return -np.inf
                return -np.log(z) / xi
            z = 1 + xi * obs / sig
            if np.any(z <= 0):
                return 1e12
            ll = np.sum(-np.log(sig) - (1 + 1 / xi) * np.log(z)) if abs(xi) > 1e-8 \
                else np.sum(-np.log(sig) - obs / sig)
            s = logsf(ycen)
            if not np.isfinite(s):
                return 1e12
            return -(ll + ncen * s)
        r = optimize.minimize(nll, [0.1, np.std(obs) + 1], method='Nelder-Mead',
                              options={'maxiter': 4000, 'xatol': 1e-6, 'fatol': 1e-6})
        xi, sig = r.x

        def sf(t):
            t = np.maximum(np.asarray(t, float) - u, 0)
            if abs(xi) < 1e-8:
                return np.exp(-t / sig)
            z = np.maximum(1 + xi * t / sig, 1e-300)
            return z ** (-1 / xi)
        return sf

    if family in ('lognorm', 'weibull'):
        def nll(p):
            a, b = p
            if b <= 0:
                return 1e12
            if family == 'lognorm':
                d = stats.lognorm(s=b, scale=np.exp(a))
            else:
                d = stats.weibull_min(c=np.exp(a), scale=b)
            ll = np.sum(d.logpdf(np.maximum(obs, 1e-9)))
            s = d.sf(ycen)
            if not np.isfinite(ll) or s <= 0:
                return 1e12
            return -(ll + ncen * np.log(s))
        p0 = [np.log(np.mean(obs) + 1), 1.0] if family == 'lognorm' else \
             [0.0, np.mean(obs) + 1]
        r = optimize.minimize(nll, p0, method='Nelder-Mead',
                              options={'maxiter': 4000})
        a, b = r.x
        d = stats.lognorm(s=b, scale=np.exp(a)) if family == 'lognorm' else \
            stats.weibull_min(c=np.exp(a), scale=b)

        def sf(t):
            return d.sf(np.maximum(np.asarray(t, float) - u, 0))
        return sf
    raise ValueError(family)


def p_exceed(x, u, sf, thr):
    """P(|c2c| >= thr) using the empirical body below u and the tail above."""
    thr = float(thr)
    if thr < u:
        return float(np.mean(x >= thr))
    return float(np.mean(x >= u)) * float(sf(thr))


FAMS = ('gpd', 'lognorm', 'weibull')
BINS = ((0, 10), (10, 25), (24, 40), (40, 64))
c2c, v, seg = load('r1e')

print('=' * 78)
print('CONTROL -- refit with the censor moved DOWN to 1400, then predict the')
print('           observed P(|c2c| >= 1636.8). The model is not shown that value.')
print('=' * 78)
print('  bin      n>=900   OBSERVED   gpd      lognorm   weibull')
ok_fams = {}
for lo, hi in BINS:
    m = (v >= lo) & (v < hi)
    x = c2c[m]
    if (x >= U).sum() < 50:
        continue
    obs = float(np.mean(x >= WIRE_RAIL - 1e-6))
    row, good = [], []
    for fam in FAMS:
        sf = fit_tail(x, U, 1400.0, fam)
        pred = p_exceed(x, U, sf, WIRE_RAIL) if sf else np.nan
        row.append(pred)
        good.append(np.isfinite(pred) and obs > 0
                    and 0.5 <= pred / obs <= 2.0)
    ok_fams[(lo, hi)] = [f for f, g in zip(FAMS, good) if g]
    print(f'  {lo:3d}-{hi:<4d} {int((x>=U).sum()):7d}  {100*obs:7.2f}%  ' +
          '  '.join(f'{100*p:7.2f}%' for p in row) +
          '   pass: ' + (','.join(ok_fams[(lo, hi)]) or 'NONE'))

print('\n  A family passes only if it recovers the held-out censoring fraction')
print('  within a factor of 2. Only passing families are used below.')

cal107 = Calibration.from_image(V107, 'V107')
cal108 = Calibration.from_image(V108, 'V108')

print('\n' + '=' * 78)
print('PREDICTED RAIL DUTY -- V108 Y row (-29490,-17202,-16000), by alpha2')
print('=' * 78)
print('  s = |G| applied to |c2c|. Two scale choices bracket where the c2c energy')
print('  sits: s_hi = |G| at 21.7 Hz (energy LOW, pessimistic), s_lo = min |G| in')
print('  the -3 dB band (energy HIGH, optimistic). Spread across passing tail')
print('  families is shown as [min, max].')
print('\n  bin      a2   s_lo   s_hi     duty @s_hi        duty @s_lo     vs V107 meas')
for lo, hi in BINS:
    m = (v >= lo) & (v < hi)
    x = c2c[m]
    fams = ok_fams.get((lo, hi), [])
    if not fams:
        print(f'  {lo:3d}-{hi:<4d}  -- no tail family passed the control, NO PREDICTION')
        continue
    sfs = [fit_tail(x, U, WIRE_RAIL, f) for f in fams]
    meas = float(np.mean([abs(cv) >= cal107.rail_threshold(vv)
                          for cv, vv in zip(x, v[m])]))
    f = np.linspace(0.5, 499.5, 40000)
    band = (f >= 25.1) & (f <= 153.0)
    for a2 in (22, 16, 14, 12, 11):
        cnew = cal108.replace(alpha2=a2)
        G = np.abs(ratio_filter(f, cal108, cnew))
        s_lo = float(G[band].min())
        s_hi = float(abs(ratio_filter(21.73, cal108, cnew)))
        out = []
        for s in (s_hi, s_lo):
            ps = [p_exceed(x, U, sf, np.median(
                [cnew.rail_threshold(vv) for vv in v[m]]) / s) for sf in sfs]
            out.append((min(ps), max(ps)))
        print(f'  {lo:3d}-{hi:<4d} {a2:3d}  {s_lo:.3f}  {s_hi:.3f}  '
              f'[{100*out[0][0]:5.2f},{100*out[0][1]:5.2f}]%  '
              f'[{100*out[1][0]:5.2f},{100*out[1][1]:5.2f}]%   {100*meas:6.2f}%')
    print()
