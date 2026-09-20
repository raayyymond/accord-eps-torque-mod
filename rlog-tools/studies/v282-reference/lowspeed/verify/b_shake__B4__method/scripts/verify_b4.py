"""Independent re-derivation of B4 (8-15 m/s shake energy source).
Does NOT import bs.py or reuse b02/b07's accumulator code. Reads the same raw
inputs (fill_texturetermd/out/red_<route>.npz, b_shake/out/obs_<route>.npz)
directly, re-implements the band-pass + lagged energy-transfer estimator and
a whole-run Welch coherence check, from scratch, in a single flat pass
(no 500-sample chunking, no per-window v-selection) to see if the published
numbers are robust to implementation choice.

b_eq(tau) = -<T(t-tau), rate(t)> / <rate,rate>, both 1.5-3.5 Hz band-passed
(zero-phase Butterworth), restricted to samples where usable>0.5, v in bin,
and (for tau>0) samples with a valid look-back within the same contiguous
usable run (we do NOT special-case run boundaries the way b02 does --
run-boundary leakage is itself one of the things being checked).
"""
import json
import numpy as np
from scipy import signal

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/'
RED = BASE + 'fill_texturetermd/out/red_{rk}.npz'
OBS = BASE + 'lowspeed/b_shake/out/obs_{rk}.npz'
FS = 100.0

TORQUE = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
          '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4'}
V282 = {'00000064--ce6b0b0ebb': 'V282', '00000065--b9f78988bd': 'V282', '0000006c--2bc842dbac': 'V282'}

SOS = signal.butter(4, [1.5, 3.5], btype='band', fs=FS, output='sos')


def bp(x):
    return signal.sosfiltfilt(SOS, np.asarray(x, dtype=np.float64))


def load(rk):
    D = dict(np.load(RED.format(rk=rk)))
    D = {k: np.asarray(v, dtype=np.float64) for k, v in D.items()}
    try:
        O = np.load(OBS.format(rk=rk))
        if len(O['t']):
            D['dob_log'] = -np.interp(D['t'], O['t'], O['obs_logged'])
    except FileNotFoundError:
        D['dob_log'] = np.zeros_like(D['t'])
    return D


def beq_flat(term_bp, rate_bp, mask, tau_samp):
    """Flat (whole-run) lagged energy-transfer estimator, no chunking.
    mask selects samples at time t (the 'now' side, where rate is read)."""
    idx = np.where(mask)[0]
    idx = idx[idx - tau_samp >= 0]
    r = rate_bp[idx]
    t = term_bp[idx - tau_samp]
    rr = float(r @ r)
    if rr < 1e-9:
        return np.nan, 0
    return -float(t @ r) / rr, len(idx)


def block_bootstrap(term_bp, rate_bp, mask, tau_samp, block_s=5.0, n_boot=1000, seed=0):
    """5s contiguous blocks over the full timeline (not per-route pooling tricks),
    resample blocks with replacement, recompute the pooled ratio each time."""
    idx = np.where(mask)[0]
    idx = idx[idx - tau_samp >= 0]
    if len(idx) < 50:
        return np.nan, np.nan
    bs_len = int(block_s * FS)
    # group contiguous idx into blocks of ~bs_len raw samples (by position, not by idx value)
    n = len(idx)
    starts = list(range(0, n, bs_len))
    blocks = [idx[s:s + bs_len] for s in starts if len(idx[s:s + bs_len]) > 5]
    rng = np.random.default_rng(seed)
    ests = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(blocks), len(blocks))
        sel = np.concatenate([blocks[p] for p in pick])
        r = rate_bp[sel]
        t = term_bp[sel - tau_samp]
        rr = float(r @ r)
        if rr < 1e-9:
            continue
        ests.append(-float(t @ r) / rr)
    if not ests:
        return np.nan, np.nan
    return float(np.percentile(ests, 2.5)), float(np.percentile(ests, 97.5))


def positive_control(D):
    """Sanity: ctrl = -1e-3*sr must read exactly +1.000e-3 at tau=0 for ANY mask."""
    sr_bp = bp(D['sr'])
    ctrl_bp = -1e-3 * sr_bp
    mask = np.isfinite(D['sr'])
    val, n = beq_flat(ctrl_bp, sr_bp, mask, 0)
    return val, n


def run_group(routes, label):
    print(f'--- {label} : routes {routes} ---')
    all_D = {}
    for rk in routes:
        all_D[rk] = load(rk)

    # positive control per route
    for rk in routes:
        val, n = positive_control(all_D[rk])
        print(f'  positive control {rk[:8]}: ctrl b_eq(tau=0) = {val*1e4:+.3f}e-4  (want +10.00e-4)  n={n}')

    results = {}
    for term in ['u_e4', 'dob_log']:
        per_route = {}
        pooled_num = {0: 0.0, 3: 0.0, 6: 0.0}
        pooled_den = {0: 0.0, 3: 0.0, 6: 0.0}
        # also collect for pooled bootstrap: concatenate bp'd arrays with route offset markers
        cat_term = {0: [], 3: [], 6: []}
        cat_rate = {0: [], 3: [], 6: []}
        for rk in routes:
            D = all_D[rk]
            fin = np.isfinite(D['sr']) & np.isfinite(D['v']) & np.isfinite(D['usable']) & np.isfinite(D[term])
            mask = fin & (D['usable'] > 0.5) & (D['v'] >= 8) & (D['v'] < 15)
            n_samp = int(mask.sum())
            if n_samp < 50:
                per_route[rk] = None
                continue
            sr_bp = bp(D['sr'])
            term_bp = bp(D[term])
            vals = {}
            for tau_samp, tau_ms in [(0, 0), (3, 30), (6, 60)]:
                val, n = beq_flat(term_bp, sr_bp, mask, tau_samp)
                vals[tau_ms] = val
                idx = np.where(mask)[0]
                idx = idx[idx - tau_samp >= 0]
                pooled_num[tau_samp] += float(term_bp[idx - tau_samp] @ sr_bp[idx])
                pooled_den[tau_samp] += float(sr_bp[idx] @ sr_bp[idx])
            per_route[rk] = dict(vals=vals, n=n_samp, secs=n_samp / FS)
            print(f'  {term} {rk[:8]} ({label}): n={n_samp} ({n_samp/FS:.0f}s)  '
                  f'@0 {vals[0]*1e4:+.2f}  @30 {vals[30]*1e4:+.2f}  @60 {vals[60]*1e4:+.2f}')
        pooled = {tau_ms: (-pooled_num[tau_samp] / pooled_den[tau_samp] if pooled_den[tau_samp] > 1e-9 else np.nan)
                  for tau_samp, tau_ms in [(0, 0), (3, 30), (6, 60)]}
        # CI via block bootstrap on concatenated (route-tagged) samples -- pool all routes then block-bootstrap
        # build a combined per-route timeline concatenation for tau=30 CI
        term_cat = np.concatenate([bp(all_D[rk][term]) for rk in routes if per_route.get(rk) is not None])
        rate_cat = np.concatenate([bp(all_D[rk]['sr']) for rk in routes if per_route.get(rk) is not None])
        mask_cat = np.concatenate([
            (np.isfinite(all_D[rk]['sr']) & np.isfinite(all_D[rk]['v']) & np.isfinite(all_D[rk]['usable']) &
             np.isfinite(all_D[rk][term]) & (all_D[rk]['usable'] > 0.5) & (all_D[rk]['v'] >= 8) & (all_D[rk]['v'] < 15))
            for rk in routes if per_route.get(rk) is not None])
        lo, hi = block_bootstrap(term_cat, rate_cat, mask_cat, 3, block_s=5.0, n_boot=1000, seed=1)
        print(f'  {term} POOLED ({label}): @0 {pooled[0]*1e4:+.2f}  @30 {pooled[30]*1e4:+.2f} '
              f'[{lo*1e4:+.2f},{hi*1e4:+.2f}]  @60 {pooled[60]*1e4:+.2f}')
        results[term] = dict(per_route={rk: (per_route[rk]['vals'] if per_route[rk] else None) for rk in routes},
                              pooled=pooled, ci30=[lo, hi])
    return results


def coherence_check(routes, label, nps=256):
    """Coherence between band-limited wheel rate and setpoint-desired-angle rate, 8-15 m/s
    bin. FIRST ATTEMPT (kept as a cautionary log below) averaged scipy.signal.coherence()
    PER RUN then averaged those coherence values across runs -- for short runs (256-500
    samples) that call gets only 1-2 Welch segments, and coherence computed from a single
    segment is trivially 1.0 by construction (degenerate-averaging upward bias), which
    inflated the group number. This version instead POOLS cross/auto spectra (Pxx,Pyy,Pxy)
    across ALL segments from ALL runs of ALL routes in the group -- the same estimator
    structure as v282cmp.band_H / b04 -- then computes one coherence curve from the pooled
    spectra, so no single short run can dominate."""
    import sys
    sys.path.insert(0, BASE)
    import v282cmp as V
    L_, SF = 2.83, -7.0e-4
    Pxx = Pyy = Pxy = None; fr = None; tot_w = 0.0; n_seg = 0; n_runs = 0; n_samp = 0
    for rk in routes:
        S = V.load(rk)
        v = S['v']; sp = np.nan_to_num(S['setpoint']); sR = np.nan_to_num(S['sR'], nan=16.5)
        sa_des = np.degrees((-sp / np.maximum(v * v, 1.0)) * sR * L_ * (1 - SF * v * v))
        adr = np.gradient(sa_des) * FS
        sr = S['sr']
        m = V.usable(S, 8, 15) & np.isfinite(sr) & np.isfinite(adr)
        n_samp += int(m.sum())
        for a, b in V.runs(m, S['t'], min_s=4.0):
            n = b - a
            if n < nps:
                continue
            n_runs += 1
            x = sr[a:b] - sr[a:b].mean(); y = adr[a:b] - adr[a:b].mean()
            f, pxx = signal.welch(x, FS, nperseg=nps, noverlap=nps // 2)
            _, pyy = signal.welch(y, FS, nperseg=nps, noverlap=nps // 2)
            _, pxy = signal.csd(x, y, FS, nperseg=nps, noverlap=nps // 2)
            nsegs = 1 + (n - nps) // (nps // 2)
            n_seg += max(nsegs, 1)
            w = n
            Pxx = pxx * w if Pxx is None else Pxx + pxx * w
            Pyy = pyy * w if Pyy is None else Pyy + pyy * w
            Pxy = pxy * w if Pxy is None else Pxy + pxy * w
            fr = f; tot_w += w
    if Pxx is None:
        return None
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
    band = (fr >= 1.5) & (fr <= 3.5)
    coh_mean = float(np.average(coh[band], weights=Pxx[band]))
    return dict(label=label, coh=coh_mean, n_runs=n_runs, n_seg=n_seg, n_samp=n_samp, secs=n_samp / FS)


if __name__ == '__main__':
    rev64_routes = [rk for rk, g in TORQUE.items() if g in ('T64', 'T64B')]
    obson_routes = [rk for rk, g in TORQUE.items() if g in ('T64', 'T64B', 'T5')]
    v282_routes = list(V282.keys())

    out = {}
    out['rev64'] = run_group(sorted(rev64_routes), 'rev64 (T64+T64B)')
    out['obs-on'] = run_group(sorted(obson_routes), 'obs-on (T64+T64B+T5)')

    print('\n--- coherence sanity, POOLED cross-spectra (band_H-style estimator) ---')
    r1 = coherence_check(sorted(rev64_routes), 'rev64 8-15')
    r2 = coherence_check(sorted(v282_routes), 'V282 8-15')
    for r in (r1, r2):
        if r:
            print(f"  {r['label']:12s} coh(rate,adr) 1.5-3.5Hz = {r['coh']:.3f}  "
                  f"n_runs={r['n_runs']} n_welch_segs={r['n_seg']} secs={r['secs']:.0f}")

    json.dump(out, open(BASE + 'lowspeed/verify/b_shake__B4__method/out/per_route_raw.json', 'w'),
              indent=1, default=str)
    print('\ndone')
