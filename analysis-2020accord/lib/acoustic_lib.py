r"""ACOUSTIC ANALYSIS LIBRARY -- speed-matched, episode-bootstrapped band contrasts.

WHY THIS EXISTS SEPARATELY from a one-shot script: every number in the acoustic workstream has to
survive the same four controls, and they are easy to get subtly wrong once per script.

THE FOUR THINGS THIS FILE ENFORCES
  1. SPEED MATCHING BY RE-WEIGHTING, not by regression.  Road/tyre/wind noise scales hard with
     speed and the engaged <16 km/h speed distributions are NOT equal across routes
     (`ra4` p50 9.46 km/h vs `r97` 7.32).  A band mean is therefore computed per 2 km/h speed bin
     and recombined under a COMMON weight vector, so two routes are compared at the same speed
     mixture by construction.  Bins where either route has < MIN_BIN frames are DROPPED and the
     dropped mass is reported.
  2. EPISODE BOOTSTRAP, never windows.  An episode is a contiguous run of the mask >= MIN_EP s.
     Windows inside an episode are ~fully correlated at 62.5 Hz / 64 ms; bootstrapping them
     manufactures significance.  [feedback-episodes-not-windows]
  3. A WITHIN-ROUTE SPLIT-HALF NULL, run BEFORE any between-route ratio is quoted.  It answers
     "what ratio does this machinery return when the truth is 1.0?".
  4. THE MANUAL ARM IS FILTERED TO ROLLING (v >= V_ROLL).  73-83 % of every route's manual
     <16 km/h time is PARKED (v<1 km/h) -- no tyre noise, no suspension excitation, different
     engine load.  A parked manual arm is not exchangeable with a rolling engaged one.

UNITS.  `v_rear` and `cs_v` are m/s -- verified against each other, x3.6 here, once.
`tob` / `wide` are raw FFT power sums (arbitrary units); only RATIOS travel.  Amplitude ratio is
sqrt(power ratio); dB is 10*log10(power ratio).
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KPH = 3.6
FR = 62.5                    # acoustic feature rate, Hz
DT = 1.0 / FR
MIN_EP = 2.0                 # s, minimum episode length
V_ROLL = 2.0                 # km/h, below this the "manual" arm is a parked car
SPEED_BIN = 2.0              # km/h
MIN_BIN = 30                 # frames (0.48 s) required in a bin on BOTH sides

NAMES = {'r97': 'STOCK 1x', 'r85': 'V100 4x', 'r96': 'V102 6x',
         'r9e': 'V103 6x', 'ra4': 'V104 6x', 'r95': 'V101 8x*'}
GAIN = {'r97': 1.0, 'r85': 4.0, 'r96': 6.0, 'r9e': 6.0, 'ra4': 6.0, 'r95': 8.0}


def load(tag):
    """Audio features on the acoustic frame grid, with engagement / speed / wheel-rate carried over."""
    a = np.load(os.path.join(HERE, '_cache_%s' % tag, '%s_audio.npz' % tag))
    c = np.load(os.path.join(HERE, '_cache_%s' % tag, '%s.npz' % tag), allow_pickle=True)
    ta = a['t'].astype(float)
    tc = c['t'].astype(float)
    eng = np.interp(ta, tc, (c['cc_lat'].astype(float) > 0.5).astype(float)) > 0.5
    v = np.interp(ta, tc, c['v_rear'].astype(float)) * KPH
    return dict(tag=tag, t=ta, tob=a['tob'].astype(float), tob_f=a['tob_f'].astype(float),
                wide=a['wide'].astype(float), wide_lab=[str(x) for x in a['wide_lab']],
                rms=a['rms'].astype(float), eng=eng, v=v, meta=a['meta'],
                sp_t=a['sp_t'].astype(float), sp_db=a['sp_db'].astype(float),
                sp=a['sp'].astype(float),
                can_t=tc, rate_f=c['rate_f'].astype(float), tq=c['tq'].astype(float),
                can_eng=(c['cc_lat'].astype(float) > 0.5), can_v=c['v_rear'].astype(float) * KPH)


def mask(R, engaged=True, vlo=0.0, vhi=16.0, rolling_manual=True):
    """The analysis mask.  MANUAL is forced ROLLING unless explicitly disabled."""
    m = (R['eng'] if engaged else ~R['eng']) & (R['v'] >= vlo) & (R['v'] < vhi)
    if (not engaged) and rolling_manual:
        m = m & (R['v'] >= V_ROLL)
    return m


def episodes(m, min_s=MIN_EP):
    """Contiguous runs of `m` at least `min_s` long, as (start, stop) index pairs."""
    m = np.asarray(m, bool)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    return [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1)
            if m[b[i]] and (b[i + 1] - b[i]) * DT >= min_s]


BLOCK_S = 5.0                # s, resampling block inside a long episode


def _ep_frames(R, eps, col, arr, block_s=None):
    """Per-episode (power, speed) arrays for one band column.

    If `block_s` is set, each episode is further cut into contiguous blocks of that length.
    🛑 THIS IS A WEAKER RESAMPLING UNIT THAN AN EPISODE and is used ONLY where an arm has too
    few episodes to bootstrap at all -- notably `r97`'s rolling-manual arm, which is 63.5 s in
    exactly TWO contiguous stretches.  Two episodes cannot be bootstrapped; two episodes cut into
    5 s blocks can.  Wherever it is used it is LABELLED, and the split-half null is re-run under
    the SAME scheme so the calibration matches the estimator.
    """
    if arr == 'env':
        parts = [(R['env'][s:e], R['v'][s:e]) for s, e in eps]
    else:
        parts = [(R[arr][s:e, col], R['v'][s:e]) for s, e in eps]
    if not block_s:
        return parts
    nb = max(int(round(block_s * FR)), 8)
    out = []
    for p, v in parts:
        for s in range(0, len(p) - nb // 2, nb):
            if len(p[s:s + nb]) >= nb // 2:
                out.append((p[s:s + nb], v[s:s + nb]))
    return out


def _binned(parts, edges):
    """Sum of power and count per speed bin, over a list of (power, speed) episode parts."""
    nb = len(edges) - 1
    sp = np.zeros(nb)
    cn = np.zeros(nb, int)
    for p, v in parts:
        j = np.clip(np.digitize(v, edges) - 1, 0, nb - 1)
        np.add.at(sp, j, p)
        np.add.at(cn, j, 1)
    return sp, cn


def _wmean(s, c, w):
    mu = np.where(c > 0, s / np.maximum(c, 1), 0.0)
    return float(np.nansum(w * mu))


def speed_matched_ratio(Ra, Rb, ma, mb, col, arr='tob', vlo=0.0, vhi=16.0,
                        nboot=2000, seed=11, min_bin=MIN_BIN, block_s=None):
    """AMPLITUDE ratio B/A at a COMMON speed mixture, with an episode bootstrap CI.

    The common weight is the per-bin MINIMUM occupancy of the two routes, normalised -- the
    mixture both routes can actually support.  Weights are FIXED at the point estimate so the
    bootstrap measures sampling noise, not weight churn.  Returns None if unmatched.
    """
    edges = np.arange(vlo, vhi + SPEED_BIN, SPEED_BIN)
    ea, eb = episodes(ma), episodes(mb)
    if (len(ea) < 3 or len(eb) < 3) and not block_s:
        return None
    if not ea or not eb:
        return None
    pa = _ep_frames(Ra, ea, col, arr, block_s)
    pb = _ep_frames(Rb, eb, col, arr, block_s)
    if len(pa) < 3 or len(pb) < 3:
        return None
    sa, ca = _binned(pa, edges)
    sb, cb = _binned(pb, edges)
    ok = (ca >= min_bin) & (cb >= min_bin)
    if not ok.any():
        return None
    w = np.minimum(ca, cb).astype(float) * ok
    w = w / w.sum()
    drop_a = 1.0 - ca[ok].sum() / max(ca.sum(), 1)
    drop_b = 1.0 - cb[ok].sum() / max(cb.sum(), 1)
    pt = np.sqrt(_wmean(sb, cb, w) / max(_wmean(sa, ca, w), 1e-300))
    rg = np.random.default_rng(seed)
    out = np.empty(nboot)
    for i in range(nboot):
        qa = [pa[j] for j in rg.integers(0, len(pa), len(pa))]
        qb = [pb[j] for j in rg.integers(0, len(pb), len(pb))]
        s1, c1 = _binned(qa, edges)
        s2, c2 = _binned(qb, edges)
        out[i] = np.sqrt(_wmean(s2, c2, w) / max(_wmean(s1, c1, w), 1e-300))
    g = np.isfinite(out)
    lo, hi = np.percentile(out[g], [2.5, 97.5])
    return dict(ratio=pt, lo=float(lo), hi=float(hi), n_ep_a=len(ea), n_ep_b=len(eb),
                n_unit_a=len(pa), n_unit_b=len(pb), blocked=bool(block_s),
                sec_a=sum(len(p) for p, _ in pa) * DT, sec_b=sum(len(p) for p, _ in pb) * DT,
                bins=int(ok.sum()), drop_a=float(drop_a), drop_b=float(drop_b), draws=out)


def split_half_null(R, m, col, arr='tob', vlo=0.0, vhi=16.0, ndraw=600, seed=5, min_bin=15,
                    block_s=None):
    """THE NULL.  Randomly halve one route's OWN episodes and run the same speed-matched
    estimator on the two halves.  Its spread is the ratio this machinery returns when the
    truth is exactly 1.0.  Anything inside it is not evidence of anything."""
    edges = np.arange(vlo, vhi + SPEED_BIN, SPEED_BIN)
    eps = episodes(m)
    if not eps:
        return None
    parts = _ep_frames(R, eps, col, arr, block_s)
    if len(parts) < 6:
        return None
    rg = np.random.default_rng(seed)
    out = []
    for _ in range(ndraw):
        pm = rg.permutation(len(parts))
        A = [parts[j] for j in pm[:len(parts) // 2]]
        B = [parts[j] for j in pm[len(parts) // 2:]]
        sa, ca = _binned(A, edges)
        sb, cb = _binned(B, edges)
        ok = (ca >= min_bin) & (cb >= min_bin)
        if not ok.any():
            continue
        w = np.minimum(ca, cb).astype(float) * ok
        w = w / w.sum()
        out.append(np.sqrt(_wmean(sb, cb, w) / max(_wmean(sa, ca, w), 1e-300)))
    if len(out) < 50:
        return None
    out = np.array(out)
    return dict(p2_5=float(np.percentile(out, 2.5)), p50=float(np.median(out)),
                p97_5=float(np.percentile(out, 97.5)), n=len(out),
                spread=float(np.percentile(out, 97.5) / np.percentile(out, 2.5)))
