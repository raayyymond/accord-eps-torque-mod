"""V109 lever pricing: rail duty under a candidate cal(0xC40DC) (alpha2).

Run order is the kit's rule -- CONTROL FIRST, then the measurement, then the
prediction. Nothing here is fitted to the number it predicts.
"""
import sys, os
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_KIT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, os.path.join(_KIT, 'model'))
from eps_closed_loop_sim import (           # noqa: E402
    Calibration, ColumnPlant, analytic_H, ratio_filter, rail_duty,
    duty_by_bin, episode_bootstrap, self_check, FS, WIRE_RAIL)

FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                    'C:/Users/dudei/Desktop/Projects/accord-firmwares')
IMG = FW + '/analysis-2020accord/'
V107 = IMG + '_v107_V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3_plain_image.bin'
V108 = IMG + '_v108_V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5_plain_image.bin'
CACHE = os.path.join(_KIT, '_scratch', 'cache')
BINS = ((0, 10), (10, 25), (24, 40), (40, 64), (65, 999))


def load(route):
    d = np.load(os.path.join(CACHE, route, route + '.npz'), allow_pickle=True)
    m = np.isfinite(d['x6c2c_mag']) & (d['cc_lat'] > 0.5)
    return (d['x6c2c_mag'][m], d['cs_v'][m] * 3.6, d['seg'][m],
            str(d['probe_build'][0]))


def duty_bounds(c2c, v, cal, scale=1.0):
    """Two-sided bounds on P(rail) with the 1636.8 wire censoring handled.

    lower: censored samples are worth exactly WIRE_RAIL
    upper: censored samples are worth +inf (they always rail)
    """
    thr = np.array([cal.rail_threshold(x) for x in v])
    cen = c2c >= WIRE_RAIL - 1e-6
    lo = np.mean(np.where(cen, WIRE_RAIL * scale >= thr, c2c * scale >= thr))
    hi = np.mean(np.where(cen, True, c2c * scale >= thr))
    return float(lo), float(hi), float(cen.mean())


print('=' * 78)
print('CONTROL FIRST -- eps_closed_loop_sim.self_check()')
print('=' * 78)
assert self_check(), 'self_check FAILED -- no number below is usable'

cal107 = Calibration.from_image(V107, 'V107')
cal108 = Calibration.from_image(V108, 'V108')
plant = ColumnPlant()

print('\n' + '=' * 78)
print('THE STRUCTURAL PROBLEM: where the lever acts vs where the plant is known')
print('=' * 78)
info = plant.lane_band_is_outside(cal107)
print(f"  lane peak                        {info['peak_hz']:.1f} Hz")
print(f"  lane -3 dB span                  {info['minus3db'][0]:.1f} - "
      f"{info['minus3db'][1]:.1f} Hz")
print(f"  plant identified band            {info['plant_valid'][0]:.0f} - "
      f"{info['plant_valid'][1]:.0f} Hz   (column corner {plant.corner_hz:.2f} Hz)")
print(f"  lane band above plant ceiling    "
      f"{100*info['fraction_of_lane_band_above_plant_ceiling']:.1f} %")
print(f"  lane PEAK outside plant band     {info['peak_is_outside']}")
print('  CAN-427 tap Nyquist              24.9 Hz  (marginal unbiased, spectrum not)')

print('\n' + '=' * 78)
print('MEASUREMENT -- route 1e, V107. Predicted by nothing; this is the anchor.')
print('=' * 78)
c2c, v, seg, build = load('r1e')
print(f'  route 1e  build {build}  engaged {len(c2c)} samples '
      f'({len(c2c)*0.0099:.1f} s)  episodes {len(np.unique(seg))}')
kit = {(0, 10): 1.68, (10, 25): 32.32, (24, 40): 21.27, (40, 64): 4.27,
       (65, 999): 0.23}
print('\n  bin       n     thr_ct  cens%    duty      kit(record)   agree?')
for row in duty_by_bin(c2c, v, cal107, BINS):
    if not row['n']:
        continue
    lo, hi = row['bin']
    m = (v >= lo) & (v < hi)
    dlo, dhi, cf = duty_bounds(c2c[m], v[m], cal107)
    k = kit[(lo, hi)]
    ok = 'YES' if (dlo - 0.02) <= k / 100 <= (dhi + 0.02) else 'no'
    print(f'  {lo:3d}-{hi:<4d}{row["n"]:7d} {row["threshold"]:8.0f} '
          f'{100*cf:6.2f}  [{100*dlo:5.2f},{100*dhi:5.2f}]%   {k:6.2f}%       {ok}')

print('\n  HELD-OUT ROUTE r1b (a different drive, same build/instrument):')
c2cb, vb, segb, buildb = load('r1b')
print(f'    build {buildb}  engaged {len(c2cb)} samples ({len(c2cb)*0.0099:.1f} s)')
for lo, hi in ((10, 25), (24, 40), (40, 64)):
    m = (vb >= lo) & (vb < hi)
    if m.sum() < 50:
        print(f'    {lo:3d}-{hi:<4d} n={m.sum()} -- too few, no claim')
        continue
    dlo, dhi, cf = duty_bounds(c2cb[m], vb[m], cal107)
    print(f'    {lo:3d}-{hi:<4d} n={m.sum():5d}  duty [{100*dlo:5.2f},{100*dhi:5.2f}]%')

print('\n' + '=' * 78)
print('THE RESHAPING FACTOR |G| = |H_new/H_old| -- exact as a filter identity')
print('=' * 78)
f = np.linspace(0.5, 499.5, 100000)
band = (f >= 25.1) & (f <= 153.0)
print('  a2   |G|@DC  |G|@21.7  |G|@61  |G|@100  |G|@250   min|G|   '
      'min|G| in the -3dB band')
GBRACKET = {}
for a2 in (22, 16, 14, 12, 11):
    cnew = cal108.replace(alpha2=a2)
    G = np.abs(ratio_filter(f, cal108, cnew))
    g = lambda x: abs(ratio_filter(x, cal108, cnew))
    GBRACKET[a2] = (float(G[band].min()), float(G.max()))
    print(f'  {a2:3d}  {g(0.5):6.3f}  {g(21.73):8.3f}  {g(61.1):6.3f}  '
          f'{g(100.):7.3f}  {g(250.):7.3f}  {G.min():7.3f}   '
          f'[{G[band].min():.3f}, {G[band].max():.3f}]')
print('\n  NOTE |G|->1 at DC for every a2 (both EMAs are unit-DC-gain), so the')
print('  bracket is [min|G| over the energy-bearing band, 1.0]. Where the c2c')
print('  energy actually sits above 24.9 Hz is UNMEASURED -- that is the gap.')

print('\n' + '=' * 78)
print('PREDICTED RAIL DUTY, V108 Y row (-29490,-17202,-16000), by alpha2')
print('=' * 78)
print('  Reported as a BRACKET over the scale factor s = |G| applied to the')
print('  MEASURED route-1e |c2c| marginal. s=1.0 is the no-reshaping pessimum;')
print('  s=min|G| assumes ALL c2c energy sits in the -3 dB band.')
print('\n  bin      a2=22(V108)     a2=16          a2=14          a2=12          a2=11')
for lo, hi in BINS:
    m = (v >= lo) & (v < hi)
    if m.sum() < 50:
        continue
    cells = []
    for a2 in (22, 16, 14, 12, 11):
        cnew = cal108.replace(alpha2=a2)
        smin = GBRACKET[a2][0]
        d_pess = duty_bounds(c2c[m], v[m], cnew, 1.0)
        d_opt = duty_bounds(c2c[m], v[m], cnew, smin)
        cells.append(f'{100*d_opt[0]:5.1f}-{100*d_pess[1]:<5.1f}')
    print(f'  {lo:3d}-{hi:<4d} ' + ' '.join(f'{c:>14s}' for c in cells))
print('\n  (each cell = [optimistic, pessimistic] % rail duty; the width IS the')
print('   unmeasured-band uncertainty, not a confidence interval)')

print('\n' + '=' * 78)
print('Y-ROW GRID at alpha2 = 14')
print('=' * 78)
rows = [(-29490, -17202, -16000), (-29490, -17202, -12000),
        (-24000, -17202, -16000), (-24000, -14000, -12000),
        (-20000, -14000, -12000), (-16000, -12000, -10000)]
print('  Y row                        10-25 km/h     24-40         40-64')
for Yr in rows:
    cnew = cal108.replace(alpha2=14, Y=Yr)
    smin = GBRACKET[14][0]
    out = []
    for lo, hi in ((10, 25), (24, 40), (40, 64)):
        m = (v >= lo) & (v < hi)
        d_pess = duty_bounds(c2c[m], v[m], cnew, 1.0)
        d_opt = duty_bounds(c2c[m], v[m], cnew, smin)
        out.append(f'{100*d_opt[0]:5.1f}-{100*d_pess[1]:<5.1f}')
    print(f'  {str(Yr):28s} ' + ' '.join(f'{o:>13s}' for o in out))

print('\n' + '=' * 78)
print('EPISODE BOOTSTRAP on the anchor (V107/route 1e), 3000 resamples')
print('=' * 78)
for lo, hi in ((0, 10), (10, 25), (24, 40), (40, 64)):
    ci = episode_bootstrap(c2c, v, seg, cal107, lo, hi)
    if ci:
        print(f'  {lo:3d}-{hi:<4d}  95% CI [{100*ci[0]:5.2f}, {100*ci[1]:5.2f}] %')
