"""Adversarial SCOPE verification of s2_jerk finding 'texture-not-event-triggered-ring'.

Question: did the original analysis look where the effect would live -- v3-8 m/s (where large-angle,
large-rate transients concentrate per the established regime map), angle-magnitude strata independent
of speed, and at finer frequency resolution than the 0.78 Hz Welch bins the finding itself flagged as
a caveat?

Read-only reuse of s2_jerk/_out/events_*.npz (already-built event tables); writes only under this
verify folder.
"""
import sys, json
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all, vbin, VBINS

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__texturenotev__scope'

rows, tr = load_all()
TQ_GROUPS = ('T64', 'T64B', 'T5', 'T4')


def D(r):
    return max(abs(r['a1'] - r['a0']), 1e-3)


# ---------- 1) v3-8 m/s: group-level (unpaired) sr_ring pre/post, no caliper-matching data loss ----------
print('=== v3-8 m/s stratum (vbin 0), group-level (unmatched) ===')
res = {}
for gset, label in ((('V282',), 'V282'), (TQ_GROUPS, 'torque(all)'), (('T64', 'T64B'), 'T64+T64B')):
    R = [r for r in rows if r['group'] in gset and r['vb'] == 0]
    if len(R) < 2:
        print(f'{label:14s} n={len(R)} -- too few, skip')
        continue
    pre = np.array([r['sr_ring_pre'] for r in R])
    post = np.array([r['sr_ring_post'] for r in R])
    ratio = post / np.maximum(pre, 1e-6)
    routes = sorted(set(r['route'] for r in R))
    print(f'{label:14s} n={len(R):3d} routes={routes} sr_ring_pre med {np.median(pre):.3f} post med {np.median(post):.3f} '
          f'ratio med {np.median(ratio):.3f} (range {ratio.min():.2f}-{ratio.max():.2f})')
    res[label] = dict(n=len(R), routes=routes, pre_med=float(np.median(pre)), post_med=float(np.median(post)),
                       ratio_med=float(np.median(ratio)), ratio_vals=ratio.tolist())

# bootstrap CI on V282 vs torque(all) difference in ratio (unpaired, route-cluster where possible)
def boot_unpaired(a, ra, b, rb, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(a); b = np.asarray(b)
    out = []
    for _ in range(n):
        aa = a[rng.integers(0, len(a), len(a))]
        bb = b[rng.integers(0, len(b), len(b))]
        out.append(np.median(bb) - np.median(aa))
    return float(np.median(out)), tuple(np.percentile(out, [2.5, 97.5]))

Rv = [r for r in rows if r['group'] == 'V282' and r['vb'] == 0]
Rt = [r for r in rows if r['group'] in TQ_GROUPS and r['vb'] == 0]
if len(Rv) >= 2 and len(Rt) >= 2:
    rv = [r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6) for r in Rv]
    rt = [r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6) for r in Rt]
    med, ci = boot_unpaired(rv, None, rt, None)
    print(f'v3-8 ratio diff (torque - V282), event-level bootstrap: {med:+.3f} CI [{ci[0]:+.3f},{ci[1]:+.3f}] '
          f'(n_v282={len(Rv)} from routes {sorted(set(r["route"] for r in Rv))}, n_torque={len(Rt)} from routes {sorted(set(r["route"] for r in Rt))})')
    res['v3-8_ratio_diff_bootstrap'] = dict(med=med, ci=list(ci), n_v282=len(Rv), n_torque=len(Rt))

# ---------- 2) angle-magnitude strata, independent of speed bin ----------
print('\n=== angle-magnitude terciles (peak |sa| in post window, ALL speeds pooled), sr_ring_post ===')
sa_tr = tr['sa']  # (n_events, 350), index by uid; NPRE=100
def peak_angle(u):
    return float(np.max(np.abs(sa_tr[u, 100:])))

for r in rows:
    r['_peak_angle'] = peak_angle(r['uid'])

V282r = [r for r in rows if r['group'] == 'V282']
TQr = [r for r in rows if r['group'] in TQ_GROUPS]
allang = np.array([r['_peak_angle'] for r in rows if r['group'] in ('V282',) + TQ_GROUPS])
terciles = np.percentile(allang, [33.3, 66.7])
print(f'angle terciles (deg, pooled V282+torque): {terciles}')

res['angle_terciles_deg'] = terciles.tolist()
for lo, hi, lbl in ((0, terciles[0], 'small'), (terciles[0], terciles[1], 'mid'), (terciles[1], 1e9, 'large')):
    Rv = [r for r in V282r if lo <= r['_peak_angle'] < hi]
    Rt = [r for r in TQr if lo <= r['_peak_angle'] < hi]
    if len(Rv) < 2 or len(Rt) < 2:
        print(f'  {lbl:6s} angle [{lo:.1f},{hi:.1f}) deg: n_v282={len(Rv)} n_tq={len(Rt)} -- too few')
        continue
    pre_v = np.median([r['sr_ring_pre'] for r in Rv]); post_v = np.median([r['sr_ring_post'] for r in Rv])
    pre_t = np.median([r['sr_ring_pre'] for r in Rt]); post_t = np.median([r['sr_ring_post'] for r in Rt])
    ratio_v = np.median([r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6) for r in Rv])
    ratio_t = np.median([r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6) for r in Rt])
    v_med = np.median([r['v'] for r in Rv]); t_med = np.median([r['v'] for r in Rt])
    print(f'  {lbl:6s} angle [{lo:.1f},{hi:.1f}) deg: n_v282={len(Rv):3d}(v~{v_med:.0f}) n_tq={len(Rt):3d}(v~{t_med:.0f})  '
          f'pre {pre_v:.2f}->{pre_t:.2f}  post {post_v:.2f}->{post_t:.2f}  ratio {ratio_v:.2f}->{ratio_t:.2f}')
    res[f'angle_{lbl}'] = dict(n_v282=len(Rv), n_tq=len(Rt), v_med_v282=float(v_med), v_med_tq=float(t_med),
                                pre_v282=float(pre_v), pre_tq=float(pre_t), post_v282=float(post_v), post_tq=float(post_t),
                                ratio_v282=float(ratio_v), ratio_tq=float(ratio_t))

# ---------- 3) finer-resolution spectrum: single-window periodogram over the full 2.5s post segment (Rayleigh 0.4 Hz)
#              vs the finding's Welch nperseg=128 (0.78 Hz), for v3-8, v8-15, and >=15 m/s, both achieved defs' proxy (sr)
print('\n=== finer-resolution PSD (single Hann window, 2.5s post, Rayleigh limit 0.4 Hz) ===')
psd_res = {}
for vb, vlabel in ((0, 'v3-8'), (1, 'v8-15'), ((2, 3), 'v15+')):
    vbs = vb if isinstance(vb, tuple) else (vb,)
    for gset, glabel in ((('V282',), 'V282'), (TQ_GROUPS, 'torque(all)')):
        U = [r['uid'] for r in rows if r['group'] in gset and r['vb'] in vbs and D(r) >= 0.2]
        if len(U) < 3:
            print(f'{vlabel:6s} {glabel:14s} n={len(U)} -- too few, skip')
            continue
        x = tr['sr'][U, 100:]  # post-jerk-peak segment, 250 samples = 2.5s
        x = signal.detrend(x, axis=-1)
        f, p = signal.periodogram(x, fs=100.0, window='hann', axis=-1)
        pm = p.mean(0)
        band = (f >= 1.0) & (f <= 4.5)
        # find local peaks in-band
        pk_idx = signal.argrelmax(pm[band])[0]
        peaks = [(float(f[band][i]), float(pm[band][i])) for i in pk_idx]
        peaks.sort(key=lambda x: -x[1])
        top3 = peaks[:3]
        from scipy.integrate import trapezoid
        e_1p5_3p5 = float(trapezoid(pm[(f >= 1.5) & (f <= 3.5)], f[(f >= 1.5) & (f <= 3.5)]))
        e_2_2p7 = float(trapezoid(pm[(f >= 2.0) & (f <= 2.7)], f[(f >= 2.0) & (f <= 2.7)])) if np.any((f >= 2.0) & (f <= 2.7)) else float('nan')
        print(f'{vlabel:6s} {glabel:14s} n={len(U):3d}  freq_res={f[1]-f[0]:.3f}Hz  top-3 in-band peaks (Hz,power) {top3}  '
              f'E[1.5-3.5]={e_1p5_3p5:.2f} E[2.0-2.7]={e_2_2p7:.2f}')
        psd_res[f'{vlabel}|{glabel}'] = dict(n=len(U), freq_res=float(f[1] - f[0]), top3_peaks=top3,
                                              E_1p5_3p5=e_1p5_3p5, E_2p0_2p7=e_2_2p7)

json.dump(dict(v3_8_group_level=res, psd_fine=psd_res), open(f'{OUT}/scope_results.json', 'w'), indent=1, default=float)
print('\nwrote', f'{OUT}/scope_results.json')
