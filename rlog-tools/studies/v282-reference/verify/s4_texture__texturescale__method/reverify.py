"""Independent re-derivation of the s4_texture 'texture-scales-with-angle-and-transient-size' finding.
Does NOT import s4_compare.matched_effect -- recomputes the matched-cell ratio from scratch, straight
from the block-level npz files, to catch any bug baked into the shared pipeline itself.
Also independently recomputes the jerk-event md_post medians+CIs straight from the EV JSON blobs
stored in the same npz files, without importing s4_extra.py or s4_events.py.
"""
import json
import numpy as np

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'

ROUTES = {
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64",
    "0000006e--6ca3e014fd": "T64B",
    "00000076--d0b7ea7e4d": "T5",
    "00000075--6c8687d5bd": "T4",
}

def load_blocks(rk):
    D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
    keys = [str(k) for k in D['keys']]
    rows = D['rows']
    return {k: rows[:, i] for i, k in enumerate(keys)}, json.loads(str(D['EV']))

BLK = {}
EV = {}
for rk in ROUTES:
    BLK[rk], EV[rk] = load_blocks(rk)

# ---------- (A) matched-cell ratio, independent implementation ----------
SPD = [0, 8, 15, 22, 40]; ANG = [0, 5, 15, 45, 1e9]; ACT = [0, 1.0, 3.0, 10.0, 1e9]
MIN_PER_CELL = 3

def cellid(v, ang90, act):
    s = np.digitize(v, SPD) - 1
    a = np.digitize(ang90, ANG) - 1
    m = np.digitize(act, ACT) - 1
    return s * 100 + a * 10 + m

def group_blocks(group, sel_fn):
    """Returns dict route -> (cellid array, metric array) for blocks passing sel_fn(cols)."""
    out = {}
    for rk, g in ROUTES.items():
        if g != group:
            continue
        c = BLK[rk]
        sel = sel_fn(c)
        cid = cellid(c['v'][sel], c['ang90'][sel], c['act'][sel])
        out[rk] = (cid, c['mode_rms'][sel])
    return out

def matched_ratio(Gd, Vd, verbose_label=None):
    gc = np.concatenate([x[0] for x in Gd.values()]); gm = np.concatenate([x[1] for x in Gd.values()])
    vc = np.concatenate([x[0] for x in Vd.values()]); vm = np.concatenate([x[1] for x in Vd.values()])
    num = den = 0.0
    cellrows = []
    for c in np.intersect1d(np.unique(gc), np.unique(vc)):
        a = gm[gc == c]; b = vm[vc == c]
        a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
        if len(a) < MIN_PER_CELL or len(b) < MIN_PER_CELL:
            continue
        ma, mb = np.median(a), np.median(b)
        w = min(len(a), len(b))
        num += w * (np.log(ma + 1e-3) - np.log(mb + 1e-3))
        den += w
        cellrows.append((c, len(a), len(b), ma, mb, ma / mb))
    if verbose_label:
        print(f'-- {verbose_label} matched cells --')
        for c, na, nb, ma, mb, r in cellrows:
            print(f'  cell {c:4d}  n_G={na:3d} n_V={nb:3d}  med_G={ma:.3f} med_V={mb:.3f}  ratio={r:.3f}')
    if den == 0:
        return np.nan, 0
    return float(np.exp(num / den)), int(den)

def boot_ci(group, ref, sel_fn, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    Gd_all = group_blocks(group, sel_fn); Vd_all = group_blocks(ref, sel_fn)
    Gr = list(Gd_all.keys()); Vr = list(Vd_all.keys())
    reps = []
    for _ in range(B):
        gks = rng.choice(Gr, len(Gr), replace=True) if len(Gr) > 1 else Gr
        vks = rng.choice(Vr, len(Vr), replace=True) if len(Vr) > 1 else Vr
        Gd = {}
        for i, k in enumerate(gks):
            cid, m = Gd_all[k]
            idx = rng.integers(0, len(cid), len(cid))
            Gd[f'{k}_{i}'] = (cid[idx], m[idx])
        Vd = {}
        for i, k in enumerate(vks):
            cid, m = Vd_all[k]
            idx = rng.integers(0, len(cid), len(cid))
            Vd[f'{k}_{i}'] = (cid[idx], m[idx])
        e, _ = matched_ratio(Gd, Vd)
        if np.isfinite(e):
            reps.append(e)
    return [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]

sel_ang15 = lambda c: (c['v'] < 15) & (c['ang90'] >= 15)
sel_act3 = lambda c: (c['v'] < 15) & (c['act'] >= 3)

print("======== (A) matched-block mode_rms ratio, <15 m/s, |angle90| >= 15 deg ========")
for grp in ['T64', 'T64B', 'T4', 'T5']:
    Gd = group_blocks(grp, sel_ang15); Vd = group_blocks('V282', sel_ang15)
    est, w = matched_ratio(Gd, Vd, verbose_label=f'{grp} vs V282 (ang>=15)')
    ci = boot_ci(grp, 'V282', sel_ang15) if w > 0 else [np.nan, np.nan]
    print(f'{grp:5s} vs V282  est={est:.3f}  w={w}  ci={[round(x,3) for x in ci]}')

print()
print("======== (A2) matched-block mode_rms ratio, <15 m/s, activity >= 3 deg/s ========")
for grp in ['T64']:
    Gd = group_blocks(grp, sel_act3); Vd = group_blocks('V282', sel_act3)
    est, w = matched_ratio(Gd, Vd, verbose_label=f'{grp} vs V282 (act>=3)')
    ci = boot_ci(grp, 'V282', sel_act3) if w > 0 else [np.nan, np.nan]
    print(f'{grp:5s} vs V282  est={est:.3f}  w={w}  ci={[round(x,3) for x in ci]}')

# ---------- (B) event md_post medians, independent bootstrap ----------
print()
print("======== (B) desired-jerk event md_post (1.8-3.0 Hz wheel-rate rms, [0,+3s]) ========")

def events(groups, kind, s0, s1, r0, r1):
    out = []
    for rk, g in ROUTES.items():
        if g not in groups:
            continue
        for e in EV[rk]:
            if e['kind'] != kind:
                continue
            if not (s0 <= e['v'] < s1 and r0 <= e['rate_max'] < r1):
                continue
            out.append(dict(e, route=rk))
    return out

def bmed_2level(E, key, B=2000, seed=1):
    rng = np.random.default_rng(seed)
    rk = np.array([e['route'] for e in E]); x = np.array([e[key] for e in E], float)
    ur = np.unique(rk)
    med = float(np.median(x))
    reps = []
    for _ in range(B):
        pick = rng.choice(ur, len(ur), replace=True)
        xs = np.concatenate([rng.choice(x[rk == r], (rk == r).sum(), replace=True) for r in pick])
        reps.append(np.median(xs))
    ci = [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]
    return med, ci, len(E), len(ur)

bands = [(0, 15, 10, 40, 'jerk04'), (0, 15, 40, 1e9, 'jerk04'), (15, 40, 10, 1e9, 'jerk04'), (15, 40, 0, 10, 'jerk04')]
TOR = ['T64', 'T64B', 'T5', 'T4']
for s0, s1, r0, r1, kind in bands:
    Ev = events(['V282'], kind, s0, s1, r0, r1)
    Eo = events(['V282old'], kind, s0, s1, r0, r1)
    Et = events(['T64'], kind, s0, s1, r0, r1)
    Ea = events(TOR, kind, s0, s1, r0, r1)
    label = f'v{s0}-{s1} rate{r0}-{r1}'
    if Ev:
        m, ci, n, nr = bmed_2level(Ev, 'md_post'); print(f'  {label:22s} V282     md_post={m:.3f} ci={[round(x,3) for x in ci]} n={n} routes={nr}')
    if Eo:
        m, ci, n, nr = bmed_2level(Eo, 'md_post'); print(f'  {label:22s} V282old  md_post={m:.3f} ci={[round(x,3) for x in ci]} n={n} routes={nr}')
    if Et:
        m, ci, n, nr = bmed_2level(Et, 'md_post'); print(f'  {label:22s} T64      md_post={m:.3f} ci={[round(x,3) for x in ci]} n={n} routes={nr}')
    if Ea:
        m, ci, n, nr = bmed_2level(Ea, 'md_post'); print(f'  {label:22s} allTorq  md_post={m:.3f} ci={[round(x,3) for x in ci]} n={n} routes={nr}')

# ---------- (C) tracking gain in these events ----------
print()
print("======== (C) tracking gain in these matched events ========")
for s0, s1, r0, r1, kind in [(0, 15, 10, 40, 'jerk04')]:
    Ev = events(['V282'], kind, s0, s1, r0, r1); Et = events(TOR, kind, s0, s1, r0, r1)
    print('  V282 gain median', np.nanmedian([e['gain'] for e in Ev]), 'n', len(Ev))
    print('  allTorq gain median', np.nanmedian([e['gain'] for e in Et]), 'n', len(Et))

# ---------- (D) sanity: band definition, filter order, window length check ----------
print()
print("======== (D) sanity on estimator: block length vs filter settle time ========")
from scipy import signal
sos = signal.butter(4, [1.8, 3.0], btype='band', fs=100.0, output='sos')
print('sosfiltfilt default padlen for this filter (approx):', 3 * (2 * sos.shape[0] + 1), ' vs block NB=512, event window=450')
