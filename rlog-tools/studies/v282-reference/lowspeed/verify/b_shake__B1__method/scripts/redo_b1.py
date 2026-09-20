"""Independent re-derivation of B1 (b_shake observer feed attribution), written fresh from the
source .npz files -- NOT importing bs.py / b02_beq.py / b07_rank.py. Goal: cross-check
- sign convention of b_eq and of dob_log (logged observer negated)
- the 30ms b_eq values for dob_log, ffwd, hyst, ctrl positive-control, and their bin energy shares
- the "13% of total feed" arithmetic
- the 6-8 m/s per-route exception (6c/6d observer >= setpoint-driven terms)
for the rev64 group (T64=6c,6d; T64B=6e) at v<15.
"""
import numpy as np
from scipy import signal

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/'
ROUTES = {
    '0000006c--68c6e94b17': 'T64',
    '0000006d--05e83bb04f': 'T64',
    '0000006e--6ca3e014fd': 'T64B',
}
FS = 100.0
SOS = signal.butter(4, [1.5, 3.5], btype='band', fs=FS, output='sos')
BINS = [(0, 3, '<3'), (3, 6, '3-6'), (6, 8, '6-8'), (8, 15, '8-15')]
TAU_MS = 30
TAU_SAMPLES = round(TAU_MS / 1000 * FS)  # 3


def bp(x):
    return signal.sosfiltfilt(SOS, x)


def load(rk):
    D = dict(np.load(BASE + f'fill_texturetermd/out/red_{rk}.npz'))
    D = {k: np.asarray(v, dtype=np.float64) for k, v in D.items()}
    O = np.load(BASE + f'lowspeed/b_shake/out/obs_{rk}.npz')
    # independent negation + interpolation of logged observer onto red's time base
    dob_log = -np.interp(D['t'], O['t'], O['obs_logged'])
    D['dob_log'] = dob_log
    D['ffwd'] = D['hold'] + D['move'] + D['hyst'] + D['rl_ff'] + D['p_sp']
    D['ctrl'] = -1e-3 * D['sr']
    return D


def runs_from_mask(mask, min_samples=400):
    """contiguous True runs of length >= min_samples (4s at 100Hz)"""
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [len(idx) - 1]))
    out = []
    for s, e in zip(starts, ends):
        a, b = idx[s], idx[e] + 1
        if b - a >= min_samples:
            out.append((a, b))
    return out


TERMS = ['dob_log', 'ffwd', 'hyst', 'ctrl', 'hold', 'move', 'rl_ff', 'p_sp', 'sr']

# accumulate per (group, bin): numerator sums and rr sums, plus per-route
acc = {}  # (grp,label) -> {'num':{term:0}, 'rr':0}
per_route = {}  # (route,label) -> {'num':{term:0}, 'rr':0}

for rk, grp in ROUTES.items():
    D = load(rk)
    fin = np.ones(len(D['t']), bool)
    for k in TERMS + ['v', 'usable']:
        fin &= np.isfinite(D[k])
    mask = (D['usable'] > 0.5) & fin & (D['v'] < 15)
    for (a, b) in runs_from_mask(mask):
        n = b - a
        edge = 100  # trim 1s each side post band-pass (matches b02's e=100)
        if n - 2 * edge < 100:
            continue
        v = D['v'][a:b]
        Bf = {k: bp(D[k][a:b]) for k in TERMS}
        for j0 in range(edge, n - edge, 500):
            j1 = min(j0 + 500, n - edge)
            if j1 - j0 < 100:
                continue
            for lo, hi, lab in BINS:
                sel = np.arange(j0, j1)[(v[j0:j1] >= lo) & (v[j0:j1] < hi)]
                if len(sel) < 20:
                    continue
                r = Bf['sr'][sel]  # independent band-passed steering rate, NOT derived from ctrl
                rr = float(r @ r)
                key = (grp, lab)
                if key not in acc:
                    acc[key] = {'num': {k: 0.0 for k in TERMS}, 'rr': 0.0}
                rkey = (rk, lab)
                if rkey not in per_route:
                    per_route[rkey] = {'num': {k: 0.0 for k in TERMS}, 'rr': 0.0}
                for k in TERMS:
                    shifted = Bf[k][sel - TAU_SAMPLES]
                    num = float(shifted @ r)
                    acc[key]['num'][k] += num
                    per_route[rkey]['num'][k] += num
                    if k == 'ctrl':
                        # also record tau=0 for the positive-control sign check
                        num0 = float(Bf[k][sel] @ r)
                        acc[key].setdefault('num0_ctrl', 0.0)
                        acc[key]['num0_ctrl'] += num0
                acc[key]['rr'] += rr
                per_route[rkey]['rr'] += rr
    del D

print('=== independent b_eq @ 30ms (x1e-4 output per deg/s), rev64 group, by bin ===')
merged = {'<3': ['<3'], '3-6': ['3-6'], '6-8': ['6-8'], '3-8': ['3-6', '6-8'], '<8': ['<3', '3-6', '6-8'], '8-15': ['8-15']}
allE = sum(acc[('T64', b)]['rr'] + acc[('T64B', b)]['rr'] for b in ['<3', '3-6', '6-8'] if ('T64', b) in acc)

for mb, labs in merged.items():
    num = {k: 0.0 for k in TERMS}
    rr = 0.0
    num0_ctrl = 0.0
    for lab in labs:
        for grp in ('T64', 'T64B'):
            key = (grp, lab)
            if key in acc:
                rr += acc[key]['rr']
                num0_ctrl += acc[key].get('num0_ctrl', 0.0)
                for k in TERMS:
                    num[k] += acc[key]['num'][k]
    beq = {k: -num[k] / rr for k in TERMS}
    beq_ctrl0 = -num0_ctrl / rr
    share = rr / allE if mb != '8-15' else float('nan')
    print(f"\n{mb}: rr={rr:.4g} energy_share_of_lt8={share:.3f}  ctrl@tau0(sign check,expect +10.00)={beq_ctrl0*1e4:+.3f}")
    for k in TERMS:
        print(f"  {k:8s} {beq[k]*1e4:+7.3f}")
    total_feed = beq['ffwd'] + beq['dob_log']  # ffwd already includes hyst
    total_feed_asreported = -(7.4) if False else None
    print(f"  -> setpoint-side(ffwd,incl hyst)+observer = {total_feed*1e4:+7.3f}e-4; observer share = {beq['dob_log']/total_feed*100:.1f}%")
    # also decomposition as the finding wrote it: ffwd, dob_log, hyst summed as three separate buckets (double counts hyst)
    triple = beq['ffwd'] + beq['dob_log'] + beq['hyst']
    print(f"  -> as finding wrote (ffwd + dob_log + hyst, hyst double-counted): {triple*1e4:+7.3f}e-4; observer share = {beq['dob_log']/triple*100:.1f}%")

print('\n=== per-route dob_log vs ffwd at 6-8 m/s (the claimed exception) ===')
for rk in ROUTES:
    key = (rk, '6-8')
    if key in per_route and per_route[key]['rr'] > 0:
        d = per_route[key]
        beq = {k: -d['num'][k] / d['rr'] for k in TERMS}
        print(f"  {rk[:8]}: dob_log={beq['dob_log']*1e4:+.2f}  ffwd(setpoint-side,incl hyst)={beq['ffwd']*1e4:+.2f}  secs~{d['rr']:.0f}(rr, not secs)")

print('\n=== 8-15 m/s observer check ===')
key8 = merged['8-15']
num = {k: 0.0 for k in TERMS}; rr = 0.0
for lab in key8:
    for grp in ('T64', 'T64B'):
        k2 = (grp, lab)
        if k2 in acc:
            rr += acc[k2]['rr']
            for k in TERMS:
                num[k] += acc[k2]['num'][k]
beq = {k: -num[k]/rr for k in TERMS}
print(f"  dob_log @30ms = {beq['dob_log']*1e4:+.3f}e-4  (paper claims -2.13 [-2.26,-1.99])")
print(f"  ctrl positive control @30ms = {beq['ctrl']*1e4:+.3f}e-4 (should read ~+10.00 at tau=0; at tau=30ms attenuated by the bandpass phase/mag, check separately)")
