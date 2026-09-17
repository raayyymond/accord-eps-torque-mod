"""fill_lowspeedlarg -- HANDS-OFF low-speed (2.5-15 m/s) large-angle / rate-transient reference, one route at a time.

Own module (v282cmp.py and s3turns.py are imported, not edited).

HANDS-OFF MASK (frame level, not event rejection):
  HO  = V.usable active & ~dilate(steeringPressed, +/-0.5 s) & 2.5 <= v < 15 & inside a gap-free run
  HO2 = HO & ~dilate(|steeringTorque| > 700, +/-0.5 s)       (stricter sensitivity; 700 ~ between unpressed p99 ~1000
        and unpressed p90 ~300-500; NOTE the column torque sensor also sees motor/inertia torque, so HO2 is mode-biased)

DEMAND (group-identical reference, s3turns): ad = model curvature as steering-wheel-angle equivalent, fixed opendbc Accord
  bicycle model, sR 16.33, no roll.  adl = ad lowpassed 1 Hz (inside runs).  adr = d/dt(ad lowpassed 2 Hz), deg/s.
ACHIEVED: aa = steeringAngleDeg - liveParameters angleOffset ; sr = carState steeringRateDeg ; ap = livePose-curvature angle.

Cells are DEMAND-defined (|adl| bin, |adr| bin) so a group cannot select itself into a cell by its own outcome; the
census is also reported on ACHIEVED bins (|aa|, |sr lp2|).

Output per route: data/<route>.npz with census arrays, 1.28 s blocks, dwell-jumps, turn events, rate-transient events.
"""
import sys, json
import numpy as np
from scipy import signal, ndimage

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE); sys.path.insert(0, BASE + '/s3_accel')
import v282cmp as V
import s3turns as T

OUT = BASE + '/fill_lowspeedlarg/data'
FS = V.FS
NB = 128
VB = [2.5, 5.0, 8.0, 15.0]
AB = [0, 15, 45, 90, 1e9]
RB = [0, 10, 40, 1e9]
TQ_STRICT = 700.0


def bp(x, f1, f2, order=4):
    return signal.sosfiltfilt(signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos'), x)


def lp(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)


def dil(m, n=50):
    return ndimage.binary_dilation(m, structure=np.ones(2 * n + 1, bool))


def binidx(x, edges):
    return np.clip(np.searchsorted(edges, x, side='right') - 1, 0, len(edges) - 2)


def smooth(x, n=10):
    return np.convolve(x, np.ones(n) / n, 'same')


def xcorr_lag(x, y, ok, maxlag=80):
    """lag (frames, + = y lags x) maximising the correlation of x(t) and y(t+k) over frames where ok(t)&ok(t+k)."""
    best, bl = -np.inf, np.nan
    n = len(x)
    for k in range(0, maxlag + 1):
        m = ok[:n - k] & ok[k:]
        if m.sum() < 30:
            continue
        a, b = x[:n - k][m], y[k:][m]
        if np.std(a) < 1e-6 or np.std(b) < 1e-6:
            continue
        c = np.corrcoef(a, b)[0, 1]
        if c > best:
            best, bl = c, k
    return bl, best


def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 10 or np.std(x[m]) < 1e-3:
        return np.nan
    return float(np.polyfit(x[m], y[m], 1)[0])


def cross_time(y, level, i0, i1, rising=True, last=False):
    """first (or last) index in [i0,i1) where y crosses level in the given direction; linear-interpolated, frames."""
    i0 = max(i0, 1); i1 = min(i1, len(y))
    seg = y[i0 - 1:i1]
    if rising:
        c = np.where((seg[:-1] < level) & (seg[1:] >= level))[0]
    else:
        c = np.where((seg[:-1] > level) & (seg[1:] <= level))[0]
    if not len(c):
        return np.nan
    k = c[-1] if last else c[0]
    y0, y1 = seg[k], seg[k + 1]
    fr = (level - y0) / (y1 - y0) if y1 != y0 else 0.0
    return float(i0 - 1 + k + fr)


def route(rk):
    S = V.load(rk)
    grp = S['meta']['group']
    t = S['t']; v = np.nan_to_num(S['v']); n = len(t)
    act = S['active'] & np.isfinite(S['v'])
    pressed = S['pressed']
    storque = np.nan_to_num(S['storque'])
    aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    sr = np.nan_to_num(S['sr'])
    model = np.nan_to_num(S['model'])
    vv = np.maximum(v, 0.5)
    ad = T.curv_to_angle(model / vv ** 2, v)
    curv = model / vv ** 2
    ap = T.curv_to_angle(np.nan_to_num(S['la_pose']) / vv ** 2, v)
    ap = np.where(v >= 2.5, ap, np.nan)
    d_route = float(np.nanmedian(S['lat_delay']))
    sR_med = float(np.nanmedian(S['sR'][act & (v < 15)]))
    out_ = np.nan_to_num(S['out']); e4 = np.nan_to_num(S['e4'])
    del S

    # --- filtered signals, computed inside gap-free ACTIVE runs with v>=2 (never across a gap / disengagement)
    adl = np.zeros(n); adr = np.zeros(n); adl2 = np.zeros(n); srl2 = np.zeros(n); srl1 = np.zeros(n)
    aal5 = np.zeros(n); srl5 = np.zeros(n)
    ad_hf = np.zeros(n); curv_hf = np.zeros(n); curv_lf = np.zeros(n)
    base = act & (v >= 2.0)
    for a, b in V.runs(base, t, min_s=1.0):
        if b - a < 60:
            continue
        adl[a:b] = lp(ad[a:b], 1.0); adl2[a:b] = lp(ad[a:b], 2.0); adr[a:b] = V.deriv(adl2[a:b])
        srl2[a:b] = lp(sr[a:b], 2.0); srl1[a:b] = lp(sr[a:b], 1.0); aal5[a:b] = lp(aa[a:b], 5.0); srl5[a:b] = lp(sr[a:b], 5.0)
        ad_hf[a:b] = bp(ad[a:b], 1.0, 5.0, 2); curv_hf[a:b] = bp(curv[a:b], 1.0, 5.0, 2); curv_lf[a:b] = lp(curv[a:b], 1.0)
    guard = dil(pressed)
    guard2 = guard | dil(np.abs(storque) > TQ_STRICT)
    inv = (v >= VB[0]) & (v < VB[-1])
    HO = base & ~guard & inv
    HO2 = base & ~guard2 & inv
    RAW = base & ~pressed & inv          # V.usable-equivalent (no guard band)

    # --- census: seconds per mask x speed x angle x rate, demand bins and achieved bins
    sb = binidx(v, VB)
    cen = {}
    for mname, M in (('raw', RAW), ('ho', HO), ('ho2', HO2)):
        for kind, A, R_ in (('dem', np.abs(adl), np.abs(adr)), ('ach', np.abs(aa), np.abs(srl2))):
            H = np.zeros((3, 4, 3))
            np.add.at(H, (sb[M], binidx(A[M], AB), binidx(R_[M], RB)), 1.0 / FS)
            cen[f'{mname}_{kind}'] = H

    # --- blocks (1.28 s) inside HO runs; run-level filtering, 0.3 s trimmed at each run edge
    BL = []
    DJ = []
    for a, b in V.runs(HO, t, min_s=(NB + 60) / FS):
        if b - a < NB + 60:
            continue
        s_sr = sr[a:b]; s_aa = aa[a:b]
        md = bp(s_sr, 1.8, 3.0); hf = bp(s_sr, 2.0, 10.0); lf = lp(s_sr, 1.0); lf05 = lp(s_sr, 0.5)
        rsm = smooth(np.abs(s_sr), 10)
        # dwell-then-jump (s4 definition) on this HO run
        low = rsm < 0.75; i = 0; m_ = b - a
        djend = []
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            L = j - i + 1
            if L >= 12 and i - 50 >= 0 and j + 50 < m_:
                pre = s_aa[i] - s_aa[i - 50]; post = s_aa[j + 50] - s_aa[j]
                if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                    g = a + j
                    DJ.append((v[g], abs(adl[g]), abs(adr[g]), abs(aa[g]), L / FS, abs(s_aa[j + 30] - s_aa[j]), a + j))
                    djend.append(a + j)
            i = j + 1
        djend = np.array(djend)
        for k0 in range(30, m_ - NB - 30 + 1, NB):
            g = slice(a + k0, a + k0 + NB); l = slice(k0, k0 + NB)
            dth = np.abs(np.diff(s_aa[l])); rsl = rsm[l][1:]
            conc = float(dth[rsl >= np.percentile(rsl, 90)].sum() / dth.sum()) if dth.sum() > 0.5 else np.nan
            mv = np.abs(lf05[l]) >= 3.0
            BL.append(dict(
                i0=a + k0, v=float(np.median(v[g])),
                dang=float(np.median(np.abs(adl[g]))), drate=float(np.median(np.abs(adr[g]))),
                aang=float(np.median(np.abs(aa[g]))), arate=float(np.median(np.abs(srl2[g]))),
                dang_max=float(np.max(np.abs(adl[g]))), drate_max=float(np.max(np.abs(adr[g]))),
                mode_rms=float(np.sqrt(np.mean(md[l] ** 2))), hf_rms=float(np.sqrt(np.mean(hf[l] ** 2))),
                lf_rms=float(np.sqrt(np.mean(lf[l] ** 2))), conc=conc, travel=float(dth.sum()),
                stall=float(np.mean(rsm[l][mv] < 0.5)) if mv.sum() >= 30 else np.nan,
                n_dj=int(((djend >= g.start) & (djend < g.stop)).sum()) if len(djend) else 0,
                curv_hf=float(np.sqrt(np.mean(curv_hf[g] ** 2))), curv_lf=float(np.sqrt(np.mean(curv_lf[g] ** 2))),
                curv_lfabs=float(np.mean(np.abs(curv_lf[g]))),
                ad_hf=float(np.sqrt(np.mean(ad_hf[g] ** 2))), ad_lf=float(np.sqrt(np.mean(adl[g] ** 2))),
                ho2=float(HO2[g].mean()), tq_rms=float(np.sqrt(np.mean(storque[g] ** 2))),
                e4_rms=float(np.sqrt(np.mean(e4[g] ** 2)))))

    # --- frame-level texture segments (more data than 1.28 s blocks): per HO run >= 1 s, band-filter the steer rate AND the
    # derivative of the measured angle (independent second measure), trim 0.2 s at run edges, then cut contiguous
    # in-cell stretches (>= 10 frames) per demand cell x frame speed bin.  Stored as sums so any rms can be rebuilt.
    FCELLS = [('A0', lambda i: (np.abs(adl[i]) < 15) & (np.abs(adr[i]) < 10)), ('A15', lambda i: np.abs(adl[i]) >= 15),
              ('A45', lambda i: np.abs(adl[i]) >= 45), ('A90', lambda i: np.abs(adl[i]) >= 90),
              ('R10', lambda i: (np.abs(adr[i]) >= 10) & (np.abs(adr[i]) < 40)), ('R40', lambda i: np.abs(adr[i]) >= 40)]
    FSEG = []
    for a, b in V.runs(HO, t, min_s=1.0):
        if b - a < 100:
            continue
        s_sr = sr[a:b]; arate = V.deriv(aa[a:b])
        md = bp(s_sr, 1.8, 3.0); hf = bp(s_sr, 2.0, 10.0); lf = lp(s_sr, 1.0)
        mda = bp(arate, 1.8, 3.0); hfa = bp(arate, 2.0, 10.0)
        idx = np.arange(a + 20, b - 20)
        if len(idx) < 10:
            continue
        o = idx - a
        for ci, (cn, fnc) in enumerate(FCELLS):
            inc = fnc(idx)
            for sbk in range(3):
                mm = inc & (sb[idx] == sbk)
                for r0, r1 in V.runs(mm, t[idx], min_s=0.0):
                    if r1 - r0 < 10:
                        continue
                    oo = o[r0:r1]
                    FSEG.append((ci, sbk, r1 - r0, float(np.sum(md[oo] ** 2)), float(np.sum(hf[oo] ** 2)), float(np.sum(lf[oo] ** 2)),
                                 float(np.sum(mda[oo] ** 2)), float(np.sum(hfa[oo] ** 2)), float(np.sum(np.abs(np.diff(aa[a + oo]))))))

    # --- turn events (s3 detector, peak_min 15 deg of DEMAND), metrics on HO frames only
    R = dict(rk=rk, group=grp, t=t, v=v, ad=ad, aa=aa, ap=ap, sr=sr, hf=np.zeros(n), out=out_, p=np.zeros(n), i=np.zeros(n),
             f=np.zeros(n), active=base, pressed=guard, d=d_route, model=model, storque=storque)
    evs, rej = T.find_turns(R, peak_min=15.0, vmin=2.5, vmax=15.0)
    TE = []
    okf = HO.copy()
    aa_m = np.where(okf, aal5, np.nan)
    for e in evs:
        s, P = e['s'], e['P']
        i, h0, h1, j, k = e['i'], e['h0'], e['h1'], e['j'], e['k']
        D = s * adl; A = s * aa_m; Apose = s * np.where(okf, ap, np.nan)
        r = dict(v=e['v'], P=P, peak_dem_rate=float(np.max(np.abs(adr[i:j]))), t=e['t'],
                 cov_build=float(okf[i:h0].mean()) if h0 > i else np.nan, cov_hold=float(okf[h0:h1].mean()) if h1 > h0 else np.nan,
                 cov_unwind=float(okf[h1:j].mean()) if j > h1 else np.nan,
                 cov_ret=float(okf[j:j + 300].mean()), cov_all=float(okf[i:j + 300].mean()),
                 hold_s=(h1 - h0) / FS, build_s=(h0 - i) / FS, unwind_s=(j - h1) / FS)
        # crossing-time lag at 50 % of P, build and unwind, both crossings must be hands-off within +/-0.3 s
        half = 0.5 * P
        tdb = cross_time(D, half, i, k + 1, rising=True)
        tab = cross_time(np.nan_to_num(A, nan=-1e9), half, i - 50, k + 200, rising=True)
        tdu = cross_time(D, half, k, j + 1, rising=False, last=True)
        tau = cross_time(np.nan_to_num(A, nan=1e9), half, h1 - 50, j + 300, rising=False, last=True)

        def okat(x):
            return np.isfinite(x) and okf[max(0, int(x) - 30):int(x) + 30].all()
        r['lag_build'] = (tab - tdb) / FS if (okat(tdb) and okat(tab)) else np.nan
        r['lag_unwind'] = (tau - tdu) / FS if (okat(tdu) and okat(tau)) else np.nan
        # incremental gain, lag-aligned by that phase's own crossing lag (fallback: route delay)
        for ph, (p0, p1), lg in (('build', (i, h0), r['lag_build']), ('unwind', (h1, j), r['lag_unwind'])):
            L = int(round((lg if np.isfinite(lg) else d_route) * FS)); L = max(0, min(L, 100))
            if p1 - p0 >= 10 and p1 + L < n:
                x = D[p0:p1]; y = A[p0 + L:p1 + L]
                r[f'gain_{ph}'] = slope(x, y) if np.isfinite(y).mean() >= 0.7 else np.nan
                yp = Apose[p0 + L:p1 + L]
                r[f'gainpose_{ph}'] = slope(x, yp) if np.isfinite(yp).mean() >= 0.7 else np.nan
            else:
                r[f'gain_{ph}'] = np.nan; r[f'gainpose_{ph}'] = np.nan
            # un-aligned mean error / P (for the symmetric caster bias; lag cancels between build and unwind)
            if p1 - p0 >= 5 and np.isfinite(A[p0:p1]).mean() >= 0.7:
                r[f'err_{ph}'] = float(np.nanmean(A[p0:p1] - D[p0:p1]) / P)
                r[f'errpose_{ph}'] = float(np.nanmean(Apose[p0:p1] - D[p0:p1]) / P) if np.isfinite(Apose[p0:p1]).mean() >= 0.7 else np.nan
            else:
                r[f'err_{ph}'] = np.nan; r[f'errpose_{ph}'] = np.nan
        r['caster_bias'] = 0.5 * (r['err_build'] + r['err_unwind'])
        r['caster_bias_pose'] = 0.5 * (r['errpose_build'] + r['errpose_unwind'])
        # hold: gain lag-free (quasi-static) and error
        if h1 - h0 >= 10 and np.isfinite(A[h0:h1]).mean() >= 0.7:
            r['gain_hold'] = float(np.nanmean(A[h0:h1]) / np.mean(D[h0:h1]))
            r['gainpose_hold'] = float(np.nanmean(Apose[h0:h1]) / np.mean(D[h0:h1])) if np.isfinite(Apose[h0:h1]).mean() >= 0.7 else np.nan
        else:
            r['gain_hold'] = np.nan; r['gainpose_hold'] = np.nan
        # return to centre: overshoot past the demand's own excursion, and settle time (tol max(0.1P,3 deg)), 0-3 s after j
        r0, r1 = j, j + 300
        if r1 < n and np.isfinite(A[r0:r1]).mean() >= 0.7:
            ovd = max(0.0, float(np.max(-D[r0:r1])))
            r['ret_over_deg'] = float(max(0.0, np.nanmax(-A[r0:r1])) - ovd)
            r['ret_over'] = r['ret_over_deg'] / P
            tol = max(0.1 * P, 3.0)
            L = int(round((r['lag_unwind'] if np.isfinite(r['lag_unwind']) else d_route) * FS)); L = max(0, min(L, 100))
            ee = A[h1 + L:r1] - D[h1:r1 - L]
            bad = ~(np.abs(ee) < tol)
            idx = np.where(bad)[0]
            r['settle_s'] = float((idx[-1] + 1 + h1 - j) / FS) if len(idx) else 0.0
            r['settle_trunc'] = bool(len(idx) and idx[-1] >= len(ee) - 30)
        else:
            r['ret_over_deg'] = r['ret_over'] = r['settle_s'] = np.nan; r['settle_trunc'] = False
        # texture over the turn (HO frames), and dwell-jumps inside
        seg = sr[i:j + 300]; ok = okf[i:j + 300]
        if len(seg) > 128 and ok.mean() >= 0.7:
            hfx = bp(seg, 2.0, 10.0); mdx = bp(seg, 1.8, 3.0)
            r['hf_rms'] = float(np.sqrt(np.mean(hfx[ok] ** 2))); r['mode_rms'] = float(np.sqrt(np.mean(mdx[ok] ** 2)))
        else:
            r['hf_rms'] = r['mode_rms'] = np.nan
        dth = np.abs(np.diff(aa[i:j + 300]))
        r['travel'] = float(dth[ok[1:]].sum())
        TE.append(r)

    # --- rate-transient events: peaks of |demand rate| >= 10 deg/s, window [-1, +2] s
    RT = []
    pk, _ = signal.find_peaks(np.abs(adr) * (base & inv), height=10.0, prominence=5.0, distance=int(1.5 * FS))
    for k in pk:
        w0, w1 = k - 100, k + 200
        if w0 < 0 or w1 + 100 >= n or not base[w0:w1].all() or np.any(np.diff(t[w0:w1]) > 4.0 / FS):
            continue
        if not (VB[0] <= v[k] < VB[-1]):
            continue
        ok = okf[w0:w1 + 80]
        s = float(np.sign(adr[k])); pr = abs(adr[k])
        r = dict(v=float(v[k]), peak_rate=float(pr), ang_at=float(abs(adl[k])), cov=float(okf[w0:w1].mean()), t=float(t[k]))
        x = s * adr[w0:w1 + 80]; y = s * srl5[w0:w1 + 80]
        lagk, cc = xcorr_lag(x, y, ok, 80)
        r['rate_lag'] = lagk / FS if np.isfinite(lagk) else np.nan; r['rate_cc'] = cc
        if np.isfinite(lagk) and okf[w0:w1].mean() >= 0.7:
            L = int(lagk)
            xx = s * adr[w0:w1]; yy = np.where(okf[w0 + L:w1 + L], s * srl5[w0 + L:w1 + L], np.nan)
            r['rate_gain'] = slope(xx, yy)
            r['rate_peak_ratio'] = float(np.nanmax(yy) / pr)
            # angle travel ratio across the transient, lag aligned
            da = s * (aal5[w1 + L - 1] - aal5[w0 + L]); dd = s * (adl[w1 - 1] - adl[w0])
            r['travel_ratio'] = float(da / dd) if abs(dd) > 3 and okf[w1 + L - 1] and okf[w0 + L] else np.nan
            # overshoot of the achieved rate AFTER the demanded rate has fallen below 25 % of peak (unwanted continuation)
            post = np.where(x[100:] < 0.25 * pr)[0]
            if len(post):
                p0 = w0 + 100 + post[0] + L
                yy2 = np.where(okf[p0:p0 + 80], s * srl5[p0:p0 + 80], np.nan)
                xx2 = s * adr[p0 - L:p0 - L + 80]
                r['rate_overrun'] = float(np.nanmax(yy2 - xx2) / pr) if np.isfinite(yy2).mean() > 0.7 else np.nan
            else:
                r['rate_overrun'] = np.nan
        else:
            r['rate_gain'] = r['rate_peak_ratio'] = r['travel_ratio'] = r['rate_overrun'] = np.nan
        seg = sr[w0:w1]; okw = okf[w0:w1]
        if okw.mean() >= 0.7:
            hfx = bp(seg, 2.0, 10.0); mdx = bp(seg, 1.8, 3.0)
            r['hf_rms'] = float(np.sqrt(np.mean(hfx[okw] ** 2))); r['mode_rms'] = float(np.sqrt(np.mean(mdx[okw] ** 2)))
            # smoothness: rms of achieved rate minus lag-aligned demanded rate, 1-5 Hz, per unit peak rate
            if np.isfinite(lagk):
                L = int(lagk)
                dif = bp(sr[w0 + L:w1 + L] - adr[w0:w1], 1.0, 5.0, 2)
                r['rough'] = float(np.sqrt(np.mean(dif[okw] ** 2)) / pr)
            else:
                r['rough'] = np.nan
            rsm = smooth(np.abs(seg), 10)
            dth = np.abs(np.diff(aa[w0:w1]))
            r['conc'] = float(dth[rsm[1:] >= np.percentile(rsm[1:], 90)].sum() / dth.sum()) if dth.sum() > 0.5 else np.nan
            r['travel'] = float(dth[okw[1:]].sum())
        else:
            r['hf_rms'] = r['mode_rms'] = r['rough'] = r['conc'] = r['travel'] = np.nan
        RT.append(r)

    np.savez_compressed(f'{OUT}/{rk}.npz', **{f'cen_{k}': vv_ for k, vv_ in cen.items()},
                        meta=json.dumps(dict(rk=rk, group=grp, d=d_route, sR=sR_med, rej=rej,
                                             ho_s=float(HO.sum() / FS), raw_s=float(RAW.sum() / FS), ho2_s=float(HO2.sum() / FS))),
                        BL=json.dumps(BL), FSEG=np.array(FSEG, float).reshape(-1, 9), DJ=np.array(DJ, float).reshape(-1, 7), TE=json.dumps(TE, default=float), RT=json.dumps(RT, default=float))
    print(rk, grp, f'raw {RAW.sum()/FS:.0f}s HO {HO.sum()/FS:.0f}s HO2 {HO2.sum()/FS:.0f}s blocks {len(BL)} fseg {len(FSEG)} dj {len(DJ)} turns {len(TE)} '
          f'rate-events {len(RT)} sR {sR_med:.2f} d {d_route:.3f}', flush=True)


if __name__ == '__main__':
    import os
    os.makedirs(OUT, exist_ok=True)
    for rk in (sys.argv[1:] or list(V.ROUTES)):
        route(rk)
