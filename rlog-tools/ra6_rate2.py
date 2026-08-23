r"""ROUTE `a6` -- Q6 PART 2 (THE ONSET TRANSIENT, DONE PROPERLY) AND THE Q-RATCHET FIX.

🛑 SELF-CORRECTION 4.  `ra6_rate.py` section 4 found **ZERO onset events on all four routes**.
   That is my detector, not the data: it demanded |e4tq| < 300 for a CONTINUOUS 0.5 s immediately
   before crossing 800.  openpilot's command RAMPS, so it spends that half-second climbing through
   300-800 and the pre-window is never all-below.  Replaced with a **quantile-relative** onset:
   |e4tq| crosses that route's own 75th engaged percentile after a 0.4 s window whose MEAN is
   below its own 40th -- so the definition is calibrated inside each drive and does not import a
   count scale across routes with different command distributions.

🛑 SELF-CORRECTION 5.  `ra6_line.py` section 3's partial correlation is DEFECTIVE.  `LINE` is
   background-subtracted and clipped at 0, so a large share of windows are EXACTLY zero; taking
   `log(clip(LINE, 1e-9))` maps every one of them to -20.7 and those outliers dominate the
   Pearson correlation.  That is why it reported partial = +0.025 while the rate-stratified table
   right above it showed LINE(HIGH) > LINE(low) in BOTH available strata.  **Redone with SPEARMAN
   rank partial correlation**, which is invariant to the floor.

⭐ ADDITION.  Route a6 is 79.7 % engaged in only **7 contiguous episodes**, so an episode
   bootstrap has 7 units and its nulls span [0.06, 25.8].  Where a within-drive contrast is the
   estimand, this file uses a **30 s contiguous-BLOCK bootstrap** instead.  That is NOT a window
   bootstrap -- blocks are contiguous, non-overlapping and much longer than the 5 s window -- and
   it is disclosed wherever used.

Usage:  python ra6_rate2.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
NAMES = {'r73': 'V88  (route 73)', 'ra4': 'V104 (route a4)', 'ra5': 'V105 (route a5)',
         'ra6': 'V106 (route a6)'}
TAGS = ('r73', 'ra4', 'ra5', 'ra6')
OUT = {}


def load(tag):
    if tag == 'r73':
        d = dict(np.load(os.path.join(ROOT, '_cache_r73', 'r73.npz'), allow_pickle=True))
    else:
        d = dict(L.load(tag))
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    return (d, e, v, np.asarray(d['rate_c'], float), np.abs(np.asarray(d['e4tq'], float)),
            np.abs(np.asarray(d['tq'], float)))


DAT = {t: load(t) for t in TAGS}

# ================================================================== 1. onsets, fixed
print("=" * 124)
print("1.  ⭐⭐ THE ONSET TRANSIENT -- QUANTILE-RELATIVE DEFINITION (the fixed detector).")
print("    Onset = |e4tq| crosses that route's OWN engaged p75 after 0.4 s whose MEAN is below")
print("    its OWN engaged p40.  Engaged throughout.  Profiles are the MEDIAN |rate_c| across")
print("    events, so one big event cannot carry the row.")
print("=" * 124)
GN = int(1.5 * FS)


def onsets(e, dem, hi, lo, pre=0.4):
    npre = int(pre * FS)
    above = dem >= hi
    k = np.ones(npre) / npre
    pre_mean = np.convolve(dem, k, 'full')[:len(dem)]           # mean of the PRECEDING npre
    out = []
    for i in np.flatnonzero(above[1:] & ~above[:-1]) + 1:
        if i - npre < 0 or i + GN >= len(dem):
            continue
        if pre_mean[i - 1] >= lo:
            continue
        if not e[i - npre:i + GN].all():
            continue
        out.append(int(i))
    return out


print("%18s %9s %9s %9s" % ('build', 'p40 eng', 'p75 eng', 'events')
      + "".join("%8s" % ("%.2fs" % (g / FS)) for g in range(0, GN, 12)))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    lo, hi = np.percentile(dem[e], 40), np.percentile(dem[e], 75)
    ev = onsets(e, dem, hi, lo)
    if len(ev) < 8:
        print("%18s %9.0f %9.0f %9d   -- too few onset events --" % (NAMES[t], lo, hi, len(ev)))
        continue
    M = np.array([np.abs(rc[i:i + GN]) for i in ev])
    prof = np.median(M, 0)
    print("%18s %9.0f %9.0f %9d" % (NAMES[t], lo, hi, len(ev))
          + "".join("%8.2f" % prof[g] for g in range(0, GN, 12)))
    OUT.setdefault('onset', {})[NAMES[t]] = dict(
        n=int(len(ev)), p40=float(lo), p75=float(hi),
        t=[float(g / FS) for g in range(GN)], median_rate=[float(x) for x in prof],
        rise=float(prof[:int(0.30 * FS)].mean()), plateau=float(prof[int(1.0 * FS):].mean()))
print()
print("%18s %14s %16s %14s" % ('build', 'rise 0-0.30 s', 'plateau 1.0-1.5 s', 'rise/plateau'))
for t in TAGS:
    r = OUT.get('onset', {}).get(NAMES[t])
    if r:
        print("%18s %14.2f %16.2f %14.3f"
              % (NAMES[t], r['rise'], r['plateau'],
                 r['rise'] / r['plateau'] if r['plateau'] else np.nan))
print("  ⇒ H-ACC (acceleration penalty): rise/plateau FALLS, plateau roughly held.")
print("    H-RATE (slew ceiling):        the PLATEAU itself falls.")

# ================================================================== 2. sustained, stratified
print()
print("=" * 124)
print("2.  ⭐ THE SUSTAINED-DEMAND RATE, **SPEED-STRATIFIED** -- `ra6_rate.py` section 5 pooled")
print("    over speed, and route a6 is far more highway-heavy than a5, so the pooled row was")
print("    confounded.  Frames where |e4tq| >= that route's own engaged p75 for >= 0.4 s.")
print("=" * 124)
VE = [0, 16, 40, 70, 1e9]
VL = ['<16', '16-40', '40-70', '70+']
print("%18s %8s %9s %9s %9s %9s %9s"
      % ('build', 'speed', 'n', 'p50', 'p90', 'p99', 'MAX'))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    hi = np.percentile(dem[e], 75)
    k = int(0.4 * FS)
    held = np.convolve((dem >= hi).astype(float), np.ones(k), 'same') >= k - 0.5
    for i, s in enumerate(VL):
        m = e & held & (v >= VE[i]) & (v < VE[i + 1])
        if m.sum() < 200:
            continue
        x = np.abs(rc[m])
        print("%18s %8s %9d %9.1f %9.1f %9.1f %9.1f"
              % (NAMES[t], s, int(m.sum()), *[np.percentile(x, p) for p in (50, 90, 99)], x.max()))
        OUT.setdefault('sustained_by_speed', {}).setdefault(NAMES[t], {})[s] = dict(
            n=int(m.sum()), mx=float(x.max()),
            **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})

# ================================================================== 3. rate ACCELERATION
print()
print("=" * 124)
print("3.  THE STEERING-WHEEL ACCELERATION UNDER DEMAND -- the quantity `gp-0x6b26` actually")
print("    opposes.  |d(rate_c)/dt| in deg/s^2, engaged, at HIGH demand (>= own p75).")
print("    H-ACC predicts THIS is what fell, while the rate itself is roughly held.")
print("=" * 124)
print("%18s %8s %9s %9s %9s %9s" % ('build', 'speed', 'n', 'p50', 'p90', 'p99'))
for t in TAGS:
    d, e, v, rc, dem, tq = DAT[t]
    acc = np.abs(np.gradient(rc) * FS)
    hi = np.percentile(dem[e], 75)
    for i, s in enumerate(VL):
        m = e & (dem >= hi) & (v >= VE[i]) & (v < VE[i + 1])
        if m.sum() < 200:
            continue
        x = acc[m]
        print("%18s %8s %9d %9.1f %9.1f %9.1f"
              % (NAMES[t], s, int(m.sum()), *[np.percentile(x, p) for p in (50, 90, 99)]))
        OUT.setdefault('wheel_accel', {}).setdefault(NAMES[t], {})[s] = dict(
            n=int(m.sum()), **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99)})

# ================================================================== 4. ratchet, fixed
print()
print("=" * 124)
print("4.  ⭐ Q-RATCHET, THE FIX -- SPEARMAN RANK partial correlation (invariant to the zero")
print("    floor that broke `ra6_line.py` section 3), plus a 30 s contiguous-BLOCK bootstrap")
print("    because route a6 has only 7 engaged episodes.")
print("=" * 124)
NPER = 512
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
kl = (FB >= 7.4) & (FB <= 8.6)
ks = ((FB >= 5.5) & (FB <= 7.0)) | ((FB >= 9.0) & (FB <= 10.5))
kc = (FB >= 21.0) & (FB <= 28.0)
kp = (FB >= 32.0) & (FB <= 38.0)

d6, e6, v6, rc6, dem6, tq6 = DAT['ra6']
rf6 = np.asarray(d6['rate_f'], float)
LN, CA, PL, DE, RC, VV, BLK = [], [], [], [], [], [], []
idx = np.flatnonzero(np.diff(e6.astype(np.int8)) != 0) + 1
bnd = np.concatenate(([0], idx, [len(e6)]))
blk_id = 0
for a, c in zip(bnd[:-1], bnd[1:]):
    if not (e6[a] and (c - a) >= NPER):
        continue
    for s in range(0, (c - a) - NPER + 1, NPER // 2):
        seg = rf6[a + s:a + s + NPER]
        X = np.fft.rfft((seg - seg.mean()) * WIN)
        S = (X.conj() * X).real / (FS * UU)
        bg = np.median(S[ks])
        LN.append(max(S[kl].sum() - bg * kl.sum(), 0) * DF)
        CA.append(S[kc].sum() * DF)
        PL.append(S[kp].sum() * DF)
        DE.append(float(np.mean(dem6[a + s:a + s + NPER])))
        RC.append(float(np.mean(np.abs(rc6[a + s:a + s + NPER]))))
        VV.append(float(np.mean(v6[a + s:a + s + NPER])))
        BLK.append(int((a + s) // int(30 * FS)))
LN, CA, PL = np.array(LN), np.array(CA), np.array(PL)
DE, RC, VV, BLK = np.array(DE), np.array(RC), np.array(VV), np.array(BLK)
ub = np.unique(BLK)
print("  %d windows, %d contiguous 30 s blocks, LINE == 0 in %.1f %% of windows"
      % (len(LN), len(ub), 100 * np.mean(LN == 0)))


def rank(x):
    o = np.argsort(np.argsort(x))
    return (o - o.mean()) / (o.std() + 1e-12)


def sp_partial(a, b, c):
    ra, rb, rc_ = rank(a), rank(b), rank(c)
    ra = ra - rc_ * np.dot(ra, rc_) / np.dot(rc_, rc_)
    rb = rb - rc_ * np.dot(rb, rc_) / np.dot(rc_, rc_)
    return float(np.dot(ra, rb) / (np.linalg.norm(ra) * np.linalg.norm(rb) + 1e-12))


rg = np.random.default_rng(2718)
res = {}
for nm, Y in (('LINE', LN), ('CARRIER', CA), ('PLACEBO (32-38)', PL)):
    raw = float(np.corrcoef(rank(Y), rank(DE))[0, 1])
    par = sp_partial(Y, DE, RC)
    par2 = sp_partial(Y, DE, VV)
    bs = []
    for _ in range(2000):
        pick = rg.choice(ub, len(ub))
        sel = np.concatenate([np.flatnonzero(BLK == j) for j in pick])
        bs.append(sp_partial(Y[sel], DE[sel], RC[sel]))
    q = np.percentile(bs, [2.5, 97.5])
    res[nm] = dict(spearman_raw=raw, partial_given_rate=par, partial_ci=[float(q[0]), float(q[1])],
                   partial_given_speed=par2)
    print("  %-16s  rho(demand) %+.4f   PARTIAL|rate %+.4f [%+.4f, %+.4f]   PARTIAL|speed %+.4f"
          % (nm, raw, par, q[0], q[1], par2))
print("  rho(LINE, |motor rate|) = %+.4f   rho(demand, |motor rate|) = %+.4f"
      % (np.corrcoef(rank(LN), rank(RC))[0, 1], np.corrcoef(rank(DE), rank(RC))[0, 1]))
OUT['ratchet_spearman'] = res

print()
print("  LINE by demand tertile INSIDE each motor-rate stratum (the stratified version, with")
print("  a block bootstrap on the HIGH/low LINE ratio):")
RE = [0, 5, 15, 40, 1e9]
RL = ['0-5', '5-15', '15-40', '40+']
print("%12s %8s %8s %10s %10s %10s %22s"
      % ('rate band', 'n low', 'n HIGH', 'LINE low', 'LINE HIGH', 'PLACEBO r', 'LINE HIGH/low CI'))
for i, rl in enumerate(RL):
    mr = (RC >= RE[i]) & (RC < RE[i + 1])
    if mr.sum() < 40:
        continue
    qq = np.percentile(DE[mr], [33.3, 66.7])
    ml = mr & (DE < qq[0])
    mh = mr & (DE >= qq[1])
    if ml.sum() < 12 or mh.sum() < 12:
        continue
    lo_, hi_ = LN[ml].mean(), LN[mh].mean()
    pr = PL[mh].mean() / PL[ml].mean() if PL[ml].mean() > 0 else np.nan
    bs = []
    for _ in range(2000):
        pick = rg.choice(ub, len(ub))
        sel = np.concatenate([np.flatnonzero(BLK == j) for j in pick])
        a_ = LN[sel][(RC[sel] >= RE[i]) & (RC[sel] < RE[i + 1]) & (DE[sel] >= qq[1])]
        b_ = LN[sel][(RC[sel] >= RE[i]) & (RC[sel] < RE[i + 1]) & (DE[sel] < qq[0])]
        if len(a_) >= 5 and len(b_) >= 5 and b_.mean() > 0:
            bs.append(a_.mean() / b_.mean())
    q = np.percentile(bs, [2.5, 97.5]) if len(bs) > 100 else [np.nan] * 2
    print("%12s %8d %8d %10.4f %10.4f %10.2f %22s"
          % (rl, int(ml.sum()), int(mh.sum()), lo_, hi_, pr,
             "[%.2f, %.2f]" % (q[0], q[1]) if np.isfinite(q[0]) else "-- b_.mean()==0 --"))
    OUT.setdefault('ratchet_stratified', {})[rl] = dict(
        n_low=int(ml.sum()), n_high=int(mh.sum()), line_low=float(lo_), line_high=float(hi_),
        placebo_ratio=float(pr), ratio_ci=[float(q[0]), float(q[1])])

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_ra6_rate2.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_ra6_rate2.json")
