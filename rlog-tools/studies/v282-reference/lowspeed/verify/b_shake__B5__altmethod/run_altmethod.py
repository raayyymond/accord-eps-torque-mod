"""ADVERSARIAL VERIFICATION of finding B5 (lens: ALTMETHOD).

B5 claim: neither the rate loop's MEASURED-rate part (rl_fb) nor friction-hysteresis switching (hyst)
feeds the 1.5-3.5 Hz wheel-shake mode at the logged latency. rl_fb damps everywhere (+8e-4 @30ms);
hyst feeds only slightly (-0.39e-4 [-0.58,-0.13] below 8 m/s, <5% of rl_fb's magnitude).

B5's own method (b02/b07): b_eq = -<term_bp(t-tau), rate_bp(t)> / <rate_bp,rate_bp>, computed on
sliding 500-sample (5 s) blocks inside a v-bin, summed with weight = each block's own rate energy.
That is an ENERGY-WEIGHTED MEAN over essentially all time in the bin (quiet stretches contribute near
nothing because their rr~0, but the estimator still pools ALL samples uniformly by construction).

This script asks: does a genuinely different estimator -- (A) EVENT/episode-conditioned (only the
actual sustained shake episodes, not all time) and (B) TAIL vs REST (top-quartile instantaneous
envelope amplitude vs the remaining 75%) -- change which terms look like feeders? If hyst or rl_fb
only feed during the big events and that is washed out by averaging over everything else, the mean
estimator could report a false null.

Independent re-derivation: reads the SAME underlying per-sample term arrays (fill_texturetermd/out/
red_<route>.npz + b_shake/out/obs_<route>.npz) as b02, but computes its own envelope, its own episode
segmentation, its own quantile split, and its own weighted linear-projection estimator with its own
bootstrap. Does not import or reuse bs.py's block-scan (b02) or the b07 aggregator.
"""
import sys, json
import numpy as np
from scipy import signal

BS_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/b_shake'
sys.path.insert(0, BS_DIR)
import bs  # noqa  (route registry + bs.load_torque only -- NOT bs.bp's caller pipeline, NOT b02/b07 code)

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/b_shake__B5__altmethod/out/'

FS = 100.0
SOS_RATE = signal.butter(4, [1.5, 3.5], btype='band', fs=FS, output='sos')   # same band as b02, independently built
SOS_ENV = signal.butter(4, [1.8, 3.5], btype='band', fs=FS, output='sos')    # same envelope band as b04 (independent re-derivation)
TAUS_S = [0.00, 0.03, 0.06]
TAUS_N = [int(round(t * FS)) for t in TAUS_S]

TERMS = ['hyst', 'rl_fb', 'rl_ff', 'p_meas', 'dob_log', 'p_sp', 'move', 'hold', 'ctrl']

E = 100  # edge buffer samples (matches b02's e=100, needed so shifted-index lookups stay in-range)
BINS = [(0, 3, '<3'), (3, 6, '3-6'), (6, 8, '6-8'), (8, 15, '8-15')]
MERGED = {'<8': [(0, 8, '<8')], '8-15': [(8, 15, '8-15')]}


def bp(x, sos):
    return signal.sosfiltfilt(sos, x)


def load_route(rk):
    D = bs.load_torque(rk)
    D['ctrl'] = -1e-3 * D['sr']
    if 'dob_log' not in D:
        D['dob_log'] = np.zeros_like(D['t'])
    fin = np.ones(len(D['t']), bool)
    need = TERMS + ['sr', 'v', 'usable']
    for k in need:
        fin &= np.isfinite(D[k])
    m = (D['usable'] > 0.5) & fin & (D['v'] < 15)
    return D, m


def weighted_est(rate_bp, term_bp_by_k, idx, taus_n=TAUS_N):
    """idx: sample indices (into the full arrays) to include, all satisfying E <= idx < n-E.
    Returns dict term -> [b_eq at tau0, tau1, tau2], plus rr (total rate energy) for weighting."""
    r = rate_bp[idx]
    rr = float(r @ r)
    if rr <= 0:
        return None, 0.0
    out = {}
    for k, tb in term_bp_by_k.items():
        out[k] = [-float(tb[idx - tau] @ r) / rr for tau in taus_n]
    return out, rr


def pool(ests_rrs, TERMS_LOCAL=TERMS):
    """ests_rrs: list of (dict term->[3], rr). Energy-weighted pooled mean, same convention as b07.est()."""
    tot = sum(rr for _, rr in ests_rrs)
    if tot <= 0:
        return None
    pooled = {}
    for k in TERMS_LOCAL:
        pooled[k] = [sum(e[k][i] * rr for e, rr in ests_rrs) / tot for i in range(3)]
    return pooled


def bootstrap_ci(items, n_boot=1000, seed=1):
    """items: list of (est_dict, rr) at the finest granularity (episode or block). Resample with
    replacement at that granularity, energy-weighted pool each resample, percentile CI at tau[1]=30ms."""
    rng = np.random.default_rng(seed)
    n = len(items)
    if n < 3:
        return None
    boots = []
    for _ in range(n_boot):
        pick = rng.integers(0, n, n)
        sub = [items[i] for i in pick]
        p = pool(sub)
        if p is not None:
            boots.append(p)
    ci = {}
    for k in TERMS:
        vals = [b[k][1] for b in boots]
        ci[k] = [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]
    return ci


def find_episodes(env, v, sel_mask, min_s=1.5, thresh=4.0):
    """Contiguous stretches (within sel_mask, i.e. already restricted to E..n-E and to a v window)
    where env >= thresh, lasting >= min_s. Returns list of (a,b) sample-index pairs into env's own array
    (env is already the full-length array; sel_mask marks eligible samples)."""
    hi = (env >= thresh) & sel_mask
    eps = []
    n = len(hi)
    i = 0
    while i < n:
        if not hi[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and hi[j + 1]:
            j += 1
        if (j - i + 1) / FS >= min_s:
            eps.append((i, j + 1))
        i = j + 1
    return eps


def run_group(routes, label):
    print(f'\n=== {label} ({[r[:8] for r in routes]}) ===', flush=True)
    # accumulate per-route, per-bin: episode items, tail items, rest items
    EPI = {b: [] for b in ('<8', '8-15')}
    TAIL = {b: [] for b in ('<8', '8-15')}
    REST = {b: [] for b in ('<8', '8-15')}
    n_epi_total = {b: 0 for b in ('<8', '8-15')}
    epi_secs = {b: 0.0 for b in ('<8', '8-15')}
    for rk in routes:
        D, m = load_route(rk)
        v = D['v']
        # NB: filter PER USABLE RUN, sliced BEFORE filtfilt (matches b02's B = {k: bs.bp(D[k][a:b])}).
        # Filtering the whole-route array first is wrong here: hyst/rl_fb/rl_ff/p_meas carry NaN
        # outside usable stretches (confirmed: 19164/79924 samples on 6c), and sosfiltfilt is a
        # non-local IIR pass, so a single NaN region poisons the ENTIRE filtered array with NaN, not
        # just that region -- caught by this script's own numbers going all-NaN on first run.
        for a, b in bs.V.runs(m, D['t'], min_s=4.0):
            n = b - a
            if n - 2 * E < 100:
                continue
            rate_bp = bp(D['sr'][a:b], SOS_RATE)
            term_bp = {k: bp(D[k][a:b], SOS_RATE) for k in TERMS}
            env = np.abs(signal.hilbert(bp(D['sr'][a:b], SOS_ENV)))
            vv = v[a:b]
            eligible = np.zeros(n, bool)
            eligible[E:n - E] = True
            for lo, hi, lab_out in [(0, 8, '<8'), (8, 15, '8-15')]:
                selm = eligible & (vv >= lo) & (vv < hi)
                if selm.sum() < 50:
                    continue
                # --- (A) episode / event method ---
                eps = find_episodes(env, vv, selm, min_s=1.5, thresh=4.0)
                for i0, i1 in eps:
                    idx = np.arange(i0, i1)
                    est, rr = weighted_est(rate_bp, term_bp, idx)
                    if est is not None:
                        EPI[lab_out].append((est, rr))
                        n_epi_total[lab_out] += 1
                        epi_secs[lab_out] += (i1 - i0) / FS
                # --- (B) tail vs rest (top-quartile instantaneous envelope, within this run+bin) ---
                idx_sel = np.where(selm)[0]
                if len(idx_sel) < 50:
                    continue
                envs = env[idx_sel]
                q75 = np.percentile(envs, 75)
                tail_idx = idx_sel[envs >= q75]
                rest_idx = idx_sel[envs < q75]
                # chunk each into 5s (500-sample) pieces for a meaningful bootstrap granularity
                for grp, dst in ((tail_idx, TAIL), (rest_idx, REST)):
                    if len(grp) < 20:
                        continue
                    for c0 in range(0, len(grp), 500):
                        chunk = grp[c0:c0 + 500]
                        if len(chunk) < 20:
                            continue
                        est, rr = weighted_est(rate_bp, term_bp, chunk)
                        if est is not None:
                            dst[lab_out].append((est, rr))
        del D

    RES = {}
    for lab in ('<8', '8-15'):
        row = {}
        for name, items in (('episode', EPI[lab]), ('tail_q75', TAIL[lab]), ('rest_q75', REST[lab])):
            if not items:
                row[name] = None
                continue
            p = pool(items)
            ci = bootstrap_ci(items)
            row[name] = dict(est=p, ci30=ci, n=len(items),
                              secs=(epi_secs[lab] if name == 'episode' else None))
        row['n_episodes'] = n_epi_total[lab]
        row['episode_secs'] = epi_secs[lab]
        RES[lab] = row
        print(f'-- {lab}: {n_epi_total[lab]} episodes, {epi_secs[lab]:.1f}s', flush=True)
        for name in ('episode', 'tail_q75', 'rest_q75'):
            r = row[name]
            if r is None:
                print(f'   {name}: no data')
                continue
            parts = []
            for k in ('hyst', 'rl_fb', 'p_meas', 'dob_log', 'ctrl'):
                v3 = r['est'][k]
                ci = r['ci30'][k] if r['ci30'] else [float('nan')] * 2
                parts.append(f"{k}={v3[1]*1e4:+.2f}[{ci[0]*1e4:+.2f},{ci[1]*1e4:+.2f}]")
            print(f"   {name:10s} n={r['n']:4d} " + '  '.join(parts))
    return RES


if __name__ == '__main__':
    ROUTES_REV64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd']
    ROUTES_ALL_TORQUE = list(bs.TORQUE.keys())
    OUT_ALL = {}
    OUT_ALL['rev64'] = run_group(ROUTES_REV64, 'rev64 (T64,T64,T64B)')
    OUT_ALL['all_torque'] = run_group(ROUTES_ALL_TORQUE, 'all torque routes (rev64+T4+T5)')
    json.dump(OUT_ALL, open(OUT + 'altmethod_results.json', 'w'), indent=1)
    print('\nsaved', OUT + 'altmethod_results.json')
