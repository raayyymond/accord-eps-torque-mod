"""ADVERSARIAL VERIFIER, lens ALTMETHOD, finding F4 (a_stickslip): "2F/k does not describe typical jumps."

Independent re-implementation, deliberately NOT reusing ss_extract.py's episode pipeline:
  - quiescence detector: TRAILING ROLLING STD of the (5 Hz lowpassed) angle over a fixed window, not the
    original's low-pass-rate-magnitude + explicit min/max-span while-loop.
  - jump size: FORWARD ROLLING MAX/MIN range from the onset frame (dense, window-based), not the original's
    "travel until |rate lp| < 1 deg/s or reversal, capped 1.5 s" event-tracking loop.
  - "onset" = last frame of a maximal quiescent run (no explicit "breakaway within 0.5 s of a 0.3 deg move"
    requirement) -> admits borderline/creeping cases the original's stricter breakaway logic could discard.
  - reports TAIL (p90/p95/p99, frac >= 2F/k) alongside p50, and a sensitivity grid over the free parameters
    (std threshold, min quiescent run length, forward window length) instead of one fixed setting.
  - adds one genuinely SPECTRAL cross-check: band-limited (0.2-3 Hz) RMS of the angle signal in the same
    hands-off/low-speed/demand-moving data, converted to an implied peak-to-peak swing, independent of any
    event detector at all.

F = 0.020 (the finding's headline F), k(v) = sslib.k_of_v (fork HOLD_K_V, no level scaling below 12.5 m/s,
same as the original). Route-cluster bootstrap, one route loaded/dropped at a time (RAM budget).
"""
import sys, os, json, gc
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy import ndimage, signal

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE); sys.path.insert(0, BASE + '/s3_accel'); sys.path.insert(0, BASE + '/lowspeed/a_stickslip')
import v282cmp as V
import s3turns as T
from sslib import k_of_v

OUTDIR = os.path.dirname(os.path.abspath(__file__))
F = 0.020
TQ_ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
             '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
TQ_GROUP = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
            '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4'}


def trailing_std(x, K):
    """std of x over the trailing K-sample window ending at i (inclusive). NaN for i < K-1."""
    n = len(x)
    c1 = np.concatenate(([0.0], np.cumsum(x, dtype=np.float64)))
    c2 = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2)))
    s1 = c1[K:] - c1[:-K]; s2 = c2[K:] - c2[:-K]
    mean = s1 / K; var = np.maximum(s2 / K - mean ** 2, 0.0)
    out = np.full(n, np.nan); out[K - 1:] = np.sqrt(var)
    return out


def trailing_all(mask, K):
    """True at i iff mask[i-K+1..i] are all True."""
    n = len(mask)
    c = np.concatenate(([0], np.cumsum(mask.astype(np.int64))))
    s = c[K:] - c[:-K]
    out = np.zeros(n, bool); out[K - 1:] = s == K
    return out


def forward_max_min(x, J):
    """max/min of x over the forward J-sample window starting at i (i..i+J-1). NaN tail (last J-1 frames)."""
    n = len(x)
    if n < J:
        return np.full(n, np.nan), np.full(n, np.nan)
    w = sliding_window_view(x, J)
    mx = w.max(axis=1); mn = w.min(axis=1)
    mxf = np.full(n, np.nan); mnf = np.full(n, np.nan)
    mxf[:n - J + 1] = mx; mnf[:n - J + 1] = mn
    return mxf, mnf


def runs_bool(mask):
    """[(start,end_excl), ...] of maximal True runs."""
    idx = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return list(zip(idx[0::2], idx[1::2]))


def onsets_for_route(rk, std_thr, minrun, J):
    """Independent event extraction for one route. Returns dict of arrays: v, ratio, jump, twoFk, kind."""
    S = V.load(rk)
    v = np.nan_to_num(S['v'])
    act = S['active']
    press_d = ndimage.binary_dilation(S['pressed'], iterations=50)
    HO = act & ~press_d
    aa = V.lowpass(np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff']), 5.0)
    vv = np.maximum(v, 1.0)
    ad = T.curv_to_angle(np.nan_to_num(S['model']) / vv ** 2, v)
    adl = V.lowpass(ad, 2.0)
    t = S['t']
    inband_lo = HO & (v >= 2.0) & (v < 8.0)
    inband_hi = HO & (v >= 8.0) & (v < 15.0)
    inband = inband_lo | inband_hi
    K = 15  # 150 ms trailing quiescence window (fixed; std_thr/minrun/J are the swept parameters)

    out = {'lo': {'ratio': [], 'jump': [], 'v': []}, 'hi': {'ratio': [], 'jump': [], 'v': []}}
    for a, b in V.runs(inband, t, min_s=1.0):
        n = b - a
        if n < K + J + 5:
            continue
        seg_aa = aa[a:b]; seg_v = v[a:b]; seg_inb_lo = inband_lo[a:b]; seg_inb_hi = inband_hi[a:b]
        std_t = trailing_std(seg_aa, K)
        allband_lo = trailing_all(seg_inb_lo, K)
        allband_hi = trailing_all(seg_inb_hi, K)
        stuck = (std_t <= std_thr) & (allband_lo | allband_hi)
        stuck = np.nan_to_num(stuck, nan=False).astype(bool)
        mx, mn = forward_max_min(seg_aa, J)
        for s0, s1 in runs_bool(stuck):
            L = s1 - s0
            if L < minrun:
                continue
            e = s1 - 1  # last quiescent frame = onset
            if e + J - 1 >= n:
                continue
            if not np.isfinite(mx[e]):
                continue
            pre = max(e - K, 0)
            dem = adl[a + e + J - 1] - adl[a + pre]
            if abs(dem) < 0.5:
                continue
            jump = max(mx[e] - seg_aa[e], seg_aa[e] - mn[e])
            ve = seg_v[e]
            band = 'lo' if seg_inb_lo[e] else ('hi' if seg_inb_hi[e] else None)
            if band is None:
                continue
            out[band]['ratio'].append(float(jump * k_of_v(ve) / (2 * F)))
            out[band]['jump'].append(float(jump))
            out[band]['v'].append(float(ve))
    n_lo, n_hi = len(out['lo']['ratio']), len(out['hi']['ratio'])
    print(f'  {rk} std_thr={std_thr} minrun={minrun} J={J}: n_lo={n_lo} n_hi={n_hi}', flush=True)
    del S, aa, ad, adl, act, press_d, HO
    gc.collect()
    return out


def boot_ci(vals, route_of, fn, nb=1500, seed=0):
    vals = np.asarray(vals, float); route_of = np.asarray(route_of)
    u = np.unique(route_of); rng = np.random.default_rng(seed)
    idx = {c: np.where(route_of == c)[0] for c in u}
    if len(vals) == 0:
        return None
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[c] for c in pick]) if len(u) else np.array([], int)
        if len(ii) > 3:
            bs.append(fn(vals[ii]))
    return dict(est=float(fn(vals)), ci=np.percentile(bs, [2.5, 97.5]).tolist() if bs else None, n=len(vals))


def sweep():
    """Primary setting + a small sensitivity grid over (std_thr, minrun, J)."""
    settings = [
        dict(name='primary', std_thr=0.10, minrun=20, J=150),   # matches original's DWMIN=20 (0.2s), slip cap 1.5s
        dict(name='j30', std_thr=0.10, minrun=20, J=30),        # matches original's j30 (300 ms window)
        dict(name='loose_minrun', std_thr=0.10, minrun=10, J=150),   # looser dwell gate (0.10 s) -> false-negative hunt
        dict(name='tight_std', std_thr=0.06, minrun=20, J=150),      # stricter quiescence
        dict(name='loose_std', std_thr=0.15, minrun=20, J=150),      # looser quiescence
    ]
    R = {}
    for st in settings:
        agg = {'lo': {'ratio': [], 'route': []}, 'hi': {'ratio': [], 'route': []}}
        for rk in TQ_ROUTES:
            o = onsets_for_route(rk, st['std_thr'], st['minrun'], st['J'])
            for band in ('lo', 'hi'):
                agg[band]['ratio'] += o[band]['ratio']
                agg[band]['route'] += [rk] * len(o[band]['ratio'])
        res = {}
        for band in ('lo', 'hi'):
            r = np.array(agg[band]['ratio']); rt = np.array(agg[band]['route'])
            if len(r) < 8:
                res[band] = dict(n=len(r), note='too few episodes')
                continue
            res[band] = dict(
                n=len(r),
                p50=boot_ci(r, rt, np.median),
                p90=boot_ci(r, rt, lambda x: np.percentile(x, 90)),
                p95=boot_ci(r, rt, lambda x: np.percentile(x, 95)),
                p99=boot_ci(r, rt, lambda x: np.percentile(x, 99)) if len(r) >= 20 else None,
                max=float(np.max(r)),
                frac_ge_1=float(np.mean(r >= 1.0)),
                frac_ge_05=float(np.mean(r >= 0.5)),
            )
        R[st['name']] = dict(params=st, result=res)
        print(json.dumps({st['name']: res}, indent=1, default=float), flush=True)
    return R


def spectral_crosscheck():
    """Genuinely different (non-event) estimator: band-limited (0.2-3 Hz) RMS of the hands-off, demand-moving,
    low-speed angle signal, converted to an implied peak-to-peak swing (2*sqrt(2)*RMS, i.e. treating the band
    power as if concentrated in one dominant sinusoid -- a rough scale, not a claim of a pure tone), compared
    to 2F/k at the band's median speed. No dwell/breakaway detector involved at all."""
    sos = signal.butter(4, [0.2, 3.0], btype='band', fs=V.FS, output='sos')
    res = {}
    for lo, hi, key in [(2, 8, 'lo'), (8, 15, 'hi')]:
        num = 0.0; den = 0; vs = []
        for rk in TQ_ROUTES:
            S = V.load(rk)
            v = np.nan_to_num(S['v']); act = S['active']
            press_d = ndimage.binary_dilation(S['pressed'], iterations=50)
            HO = act & ~press_d
            aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
            vv = np.maximum(v, 1.0)
            ad = T.curv_to_angle(np.nan_to_num(S['model']) / vv ** 2, v)
            adr = V.deriv(V.lowpass(ad, 2.0))
            m = HO & (v >= lo) & (v < hi) & (np.abs(adr) >= 1.0)
            for a, b in V.runs(m, S['t'], min_s=3.0):
                seg = aa[a:b] - np.mean(aa[a:b])
                if len(seg) < 300:
                    continue
                bp = signal.sosfiltfilt(sos, seg)
                num += float(np.sum(bp ** 2)); den += len(bp)
                vs.append(float(np.median(v[a:b])))
            del S, aa, ad, adr, act, press_d, HO
            gc.collect()
        if den < 500:
            res[key] = dict(note='insufficient moving hands-off data')
            continue
        rms = float(np.sqrt(num / den))
        vmed = float(np.median(vs)) if vs else (lo + hi) / 2
        kk = float(k_of_v(vmed))
        twoFk = 2 * F / kk
        pp_implied = 2 * np.sqrt(2) * rms
        res[key] = dict(band_rms_deg=rms, pp_implied_deg=pp_implied, v_median=vmed, k=kk,
                         twoF_over_k_deg=twoFk, ratio_pp_implied_to_2Fk=pp_implied / twoFk, sec=den / V.FS)
        print('spectral', key, res[key], flush=True)
    return res


if __name__ == '__main__':
    print('=== sweep: dense/continuous quiescence+forward-window estimator ===')
    R = sweep()
    print('=== spectral cross-check ===')
    RS = spectral_crosscheck()
    json.dump(dict(sweep=R, spectral=RS), open(OUTDIR + '/altmethod_results.json', 'w'), indent=1, default=float)
    print('wrote', OUTDIR + '/altmethod_results.json')
