"""s2_jerk stage 4: from the stored event traces, per event --
  conc   : share of the |d angle| over [-0.5, +2.0] s carried by the fastest 15% of samples (angle 5 Hz lowpassed).
           A smooth ramp reads low; dwell-then-jump (stick-slip) reads high.  Positive/negative controls asserted.
  dwell  : fraction of [-0.3, +1.0] s with |steer rate (5 Hz lp)| < 1 deg/s while the demand is moving (|model slope| > 0.15 step/s).
  pre    : mean (achieved - demand)/step over [-0.6, -0.1] s (wrong-way excursion before the jerk peak).
  kick   : command (out, 3 Hz lp) peak over [0, +0.8] s divided by its mean over [+1.5, +2.5] s  (ensemble, bootstrap).
Matched pairs V282 vs each torque rev (same matcher as s2_analyze), paired median difference + event / route bootstrap."""
import json, numpy as np, warnings
warnings.filterwarnings('ignore')
from scipy import signal
from s2_common import *

rows, tr = load_all()
sos5 = signal.butter(2, 5.0, fs=100, output='sos'); sos3 = signal.butter(2, 3.0, fs=100, output='sos')


def conc_of(sa):
    x = signal.sosfiltfilt(sos5, sa)[50:300]
    d = np.abs(np.diff(x)); tot = d.sum()
    if tot < 0.5:          # < 0.5 deg total travel: sensor LSB dominates
        return np.nan
    k = max(1, int(0.15 * len(d)))
    return float(np.sort(d)[-k:].sum() / tot)


def _controls():
    t = np.arange(350) / 100
    ramp = 10 * np.clip((t - 1.0) / 1.5, 0, 1)
    steps = 10 * (np.floor(np.clip((t - 1.0) / 1.5, 0, 0.999) * 4) / 4 + 0.25 * (t > 2.5 - 1e-9))
    c_r, c_s = conc_of(ramp + 0.0), conc_of(steps)
    assert c_r < 0.30 and c_s > 0.6, (c_r, c_s)
    return dict(ramp=c_r, staircase=c_s)


print('controls (ramp low, staircase high):', _controls())
for r in rows:
    u = r['uid']; Dd = max(abs(r['a1'] - r['a0']), 1e-3)
    r['conc'] = conc_of(tr['sa'][u])
    sr5 = signal.sosfiltfilt(sos5, tr['sr'][u]); m = tr['model'][u] / Dd
    ms = np.abs(np.gradient(m) * 100)
    w = slice(70, 200); moving = ms[w] > 0.15
    r['dwell'] = float(np.mean(np.abs(sr5[w][moving]) < 1.0)) if moving.sum() > 20 else np.nan
    a = signal.sosfiltfilt(sos3, tr['la_act'][u]) / Dd
    r['pre'] = float(np.mean((a - m)[40:90])) if Dd >= 0.2 else np.nan
REF = [r for r in rows if r['group'] == 'V282']
out = {}
for g in ['T64', 'T64B', 'T5', 'T4']:
    P = match(REF, [r for r in rows if r['group'] == g])
    for sn, vbs in (('8-15', [1]), ('>=15', [2, 3]), ('<15', [0, 1])):
        PP = [p for p in P if p[1]['vb'] in vbs]
        d = {}
        for k in ('conc', 'dwell', 'pre'):
            b = boot_diff(PP, k)
            d[k] = dict(ref=float(np.nanmedian([p[0][k] for p in PP])) if PP else None,
                        tq=float(np.nanmedian([p[1][k] for p in PP])) if PP else None, **b)
        # command kick ratio, ensemble bootstrap over matched events
        rng = np.random.default_rng(3); kk = {}
        for side, nm in ((0, 'V282'), (1, g)):
            U = np.array([p[side]['uid'] for p in PP if max(abs(p[side]['a1'] - p[side]['a0']), 0) >= 0.2])
            if len(U) < 4:
                continue
            O = signal.sosfiltfilt(sos3, tr['out'][U], axis=-1)
            def kick(ix):
                e = O[ix].mean(0); late = np.mean(e[250:350])
                return float(np.max(e[100:180] * np.sign(late)) / abs(late)) if abs(late) > 1e-6 else np.nan
            bs = [kick(rng.integers(0, len(U), len(U))) for _ in range(1000)]
            kk[nm] = dict(n=int(len(U)), kick=kick(np.arange(len(U))), ci=tuple(np.nanpercentile(bs, [2.5, 97.5])))
        d['cmd_kick'] = kk; d['n_pairs'] = len(PP)
        out[f'V282_vs_{g}|{sn}'] = d
json.dump(out, open(f'{OUT}/s2_stickslip.json', 'w'), indent=1, default=float)
for k, v in out.items():
    print(k, 'pairs', v['n_pairs'])
    for m in ('conc', 'dwell', 'pre'):
        x = v[m]
        print(f"   {m:6s} ref {x['ref']}  tq {x['tq']}  d {x['med']:+.3f} ev[{x['ci_ev'][0]:+.3f},{x['ci_ev'][1]:+.3f}] rt[{x['ci_rt'][0]:+.3f},{x['ci_rt'][1]:+.3f}] n={x['n']}")
    print('   kick', v['cmd_kick'])
