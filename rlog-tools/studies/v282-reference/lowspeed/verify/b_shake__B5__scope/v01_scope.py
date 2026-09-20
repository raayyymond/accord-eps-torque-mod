"""B5 SCOPE verifier: false-negative hunt for a hyst/rl_fb feed hidden by block-averaging.
1) Event-local b_eq: restrict the same b_eq estimator to samples inside [-0.3,+0.8]s around each
   dwell-then-jump event (b06 definition, reused verbatim), separately for <3, 3-8, 8-15 m/s.
2) Amplitude-split b_eq: restrict to samples where |steering angle| is in the top tercile per route
   (large-angle regime), all speeds <15.
3) <3 m/s dedicated re-check across ALL torque routes (b07 used pooled <3 only implicitly via BINS;
   confirm hyst/rl_fb sign and CI does not flip with more data / a different windowing).
Uses the SAME band-pass (1.5-3.5 Hz Butterworth zero-phase) and SAME b_eq definition as b02/b07:
b_eq(tau) = <T(t-tau), rate(t)> / <rate,rate> * -1e3 (units 1e-4 per deg/s, matches b07 printed scale)
NOTE: sign convention matches b02: ctrl = -1e-3*sr must read +10.00 at tau=0 (positive control).
"""
import sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/b_shake')
import bs

TAU_MS = 30
TAU = 3  # samples at 100 Hz = 30 ms, matches b02's TAUS=[0,3,6]
OUTDIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/b_shake__B5__scope/'


def dwell_jumps(sr, sa):
    rs = np.convolve(np.abs(sr), np.ones(10) / 10, 'same')
    low = rs < 0.75
    out = []
    n = len(sr)
    i = 0
    while i < n:
        if not low[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and low[j + 1]:
            j += 1
        if j - i + 1 >= 12 and i - 50 >= 0 and j + 50 < n:
            pre = sa[i] - sa[i - 50]
            post = sa[j + 50] - sa[j]
            if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                out.append(j)
        i = j + 1
    return out


def beq(term_bp, rate_bp, sel, tau):
    idx = sel - tau
    ok = (idx >= 0) & (idx < len(term_bp))
    idx = idx[ok]
    s2 = sel[ok]
    ok2 = np.isfinite(term_bp[idx]) & np.isfinite(rate_bp[s2])
    idx = idx[ok2]
    s2 = s2[ok2]
    if len(idx) < 20:
        return float('nan')
    num = float(term_bp[idx] @ rate_bp[s2])
    den = float(rate_bp[s2] @ rate_bp[s2])
    return -1e4 * num / max(den, 1e-9)  # sign/scale matches b02/b07 printed convention


def bootstrap_ci(term_bp, rate_bp, sel, tau, blocks=5.0, fs=100.0, n_boot=400, rng=None):
    if rng is None:
        rng = np.random.default_rng(0)
    bl = int(blocks * fs)
    idx = sel - tau
    ok = (idx >= 0) & (idx < len(term_bp))
    idx = idx[ok]
    s2 = sel[ok]
    ok2 = np.isfinite(term_bp[idx]) & np.isfinite(rate_bp[s2])
    idx = idx[ok2]
    s2 = s2[ok2]
    n = len(s2)
    if n < 50:
        return None, None
    nblk = max(1, n // bl)
    vals = []
    for _ in range(n_boot):
        picks = rng.integers(0, nblk, nblk)
        num = 0.0
        den = 0.0
        for p in picks:
            a = p * bl
            b = min(a + bl, n)
            num += float(term_bp[idx[a:b]] @ rate_bp[s2[a:b]])
            den += float(rate_bp[s2[a:b]] @ rate_bp[s2[a:b]])
        if den > 1e-9:
            vals.append(-1e4 * num / den)
    if not vals:
        return None, None
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


TERMS = ['hyst', 'rl_fb', 'ctrl']
results = {}

for rk, g in bs.TORQUE.items():
    D = bs.load_torque(rk)
    D['ctrl'] = -1e-3 * D['sr']
    fin = np.ones(len(D['t']), bool)
    for k in TERMS + ['sr', 'v', 'sa']:
        fin &= np.isfinite(D[k])
    m = (D['usable'] > 0.5) & fin & (D['v'] < 15)

    # Band-pass PER CONTIGUOUS RUN (never globally): matches b02's convention exactly and avoids
    # NaN leakage outside usable stretches poisoning the whole-array filtfilt output.
    n_all = len(D['t'])
    B = {k: np.full(n_all, np.nan) for k in TERMS}
    Bsr = np.full(n_all, np.nan)
    for a, b in bs.V.runs(m, D['t'], min_s=4.0):
        for k in TERMS:
            B[k][a:b] = bs.bp(D[k][a:b])
        Bsr[a:b] = bs.bp(D['sr'][a:b])
    valid = np.isfinite(Bsr)
    for k in TERMS:
        valid &= np.isfinite(B[k])

    route_res = {}

    # --- 1) event-local windows ---
    for a, b in bs.V.runs(m, D['t'], min_s=6.0):
        sr = D['sr'][a:b]
        sa = D['sa'][a:b]
        v = D['v'][a:b]
        dj = dwell_jumps(sr, sa)
        for j0 in dj:
            j = a + j0
            v_at = D['v'][j]
            speed_lab = '<3' if v_at < 3 else ('3-8' if v_at < 8 else '8-15')
            lo = max(j - 30, a)
            hi = min(j + 80, b)
            if hi - lo < 20:
                continue
            sel = np.arange(lo, hi)
            sel = sel[valid[sel]]
            if len(sel) < 20:
                continue
            key = ('event', speed_lab)
            route_res.setdefault(key, {'n_ev': 0, 'sel': []})
            route_res[key]['n_ev'] += 1
            route_res[key]['sel'].append(sel)

    for (kind, lab), d in list(route_res.items()):
        if kind != 'event':
            continue
        if not d['sel']:
            continue
        sel = np.concatenate(d['sel'])
        row = {'n_ev': d['n_ev'], 'n_samp': len(sel)}
        for term in TERMS:
            row[term] = round(beq(B[term], Bsr, sel, TAU), 3)
        lo_ci, hi_ci = bootstrap_ci(B['hyst'], Bsr, sel, TAU)
        row['hyst_ci'] = [round(lo_ci, 3), round(hi_ci, 3)] if lo_ci is not None else None
        results.setdefault(rk, {})[f'event_{lab}'] = row

    # --- 2) amplitude split (top tercile |sa|, all v<15) ---
    idxm = np.where(m & valid)[0]
    if len(idxm) > 300:
        amp = np.abs(D['sa'][idxm])
        thr = np.percentile(amp, 66.7)
        sel_hi = idxm[amp >= thr]
        sel_lo = idxm[amp < thr]
        for lab, sel in (('amp_hi', sel_hi), ('amp_lo', sel_lo)):
            if len(sel) < 200:
                continue
            row = {'n_samp': len(sel), 'amp_thr': round(float(thr), 2)}
            for term in TERMS:
                row[term] = round(beq(B[term], Bsr, sel, TAU), 3)
            lo_ci, hi_ci = bootstrap_ci(B['hyst'], Bsr, sel, TAU)
            row['hyst_ci'] = [round(lo_ci, 3), round(hi_ci, 3)] if lo_ci is not None else None
            results.setdefault(rk, {})[lab] = row

    # --- 3) dedicated <3 m/s re-check, per-route, wider CI ---
    sel3 = idxm[D['v'][idxm] < 3]
    if len(sel3) > 200:
        row = {'n_samp': len(sel3)}
        for term in TERMS:
            row[term] = round(beq(B[term], Bsr, sel3, TAU), 3)
        lo_ci, hi_ci = bootstrap_ci(B['hyst'], Bsr, sel3, TAU)
        row['hyst_ci'] = [round(lo_ci, 3), round(hi_ci, 3)] if lo_ci is not None else None
        lo2, hi2 = bootstrap_ci(B['rl_fb'], Bsr, sel3, TAU)
        row['rl_fb_ci'] = [round(lo2, 3), round(hi2, 3)] if lo2 is not None else None
        results.setdefault(rk, {})['lt3_dedicated'] = row

    print(rk, g, results.get(rk, {}), flush=True)
    del D

import json
json.dump(results, open(OUTDIR + 'v01_results.json', 'w'), indent=1)
print('DONE')
