"""ALTMETHOD verification of 's4_texture/rate-limiter-is-not-the-jerk'.

Original method: pooled fraction of frames with |d(e4)| >= 120 counts, binned by speed x angle cell
(threshold/mean method), plus per-event binary "any frame in the whole [-1.5,+3]s window limited".

This script runs FOUR different estimators, looking for a false negative the pooled-mean/binary method
could hide:
  (A) TAIL, not mean: full percentile ladder (p50/90/95/99/99.9) of |d(e4)|, same strata as the finding's
      table, plus a "near-miss" band (90-119 counts, just under the 122.9-count physical limit) that a
      binary >=120 test cannot see at all.
  (B) EVENT-LOCAL, not whole-window: restrict the "does the limiter bind near the excitation" test to a
      tight +-0.3 s window around the jerk peak / accel-event onset (where a rate-limiter cause would have
      to act), instead of diluting over the whole 4.5 s event window the original per-event binary used.
  (C) CONTINUOUS CORRELATION, not binned incidence: block-level Spearman correlation of slew_hit vs
      mode_rms (the 1.8-3.0 Hz wheel-mode band RMS), per group -- does limiter binding covary with the
      texture even where absolute levels are low.
  (D) EVENT-TRIGGERED CROSS-CORRELATION, nonlinear/causal, not a static ratio: lagged correlation between
      a limiter-hit indicator and 2-3 Hz mode power around jerk events, to see if hits systematically
      PRECEDE a burst of ringing in torque mode specifically (a mechanism the pooled tests cannot see).

All numbers computed fresh from the already-built per-route caches (s4_texture/data/*.npz has FR, rows,
EV; independent of the original finding's s4_events.py aggregation code, which is NOT reused here).
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__ratelimiteri__altmethod'
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}
rng = np.random.default_rng(7)
ANB = [(0, 5), (5, 15), (15, 45), (45, 1e9)]

cache = {}
for g in GROUPS:
    for rk in routes[g]:
        D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
        keys = [str(k) for k in D['keys']]
        cache[rk] = dict(rows={k: D['rows'][:, i] for i, k in enumerate(keys)}, FR=D['FR'],
                          EV=json.loads(str(D['EV'])))

res = {}

# ---------- (A) TAIL LADDER + NEAR-MISS BAND, <15 m/s, by angle cell ----------
tail = {}
for g in GROUPS:
    tg = {}
    for (a0, a1) in ANB:
        de4_all, v_all = [], []
        per_route_nearmiss, per_route_hard, per_route_n = [], [], []
        for rk in routes[g]:
            F = cache[rk]['FR']  # v, |sa|, |de4|, |e4|, |sr|
            m = (F[0] < 15) & (F[1] >= a0) & (F[1] < a1)
            de4_all.append(F[2][m])
            per_route_nearmiss.append(np.sum((F[2][m] >= 90) & (F[2][m] < 120)))
            per_route_hard.append(np.sum(F[2][m] >= 120))
            per_route_n.append(int(m.sum()))
        X = np.concatenate(de4_all) if de4_all else np.array([])
        n = int(sum(per_route_n))
        if n < 30:
            tg[f'a{a0}-{int(min(a1,999))}'] = dict(n=n)
            continue
        # route-cluster bootstrap on hard-limit and near-miss RATES
        def boot(nums):
            nums = np.array(nums, float); dens = np.array(per_route_n, float)
            est = nums.sum() / max(dens.sum(), 1e-9)
            reps = []
            for _ in range(2000):
                k = rng.integers(0, len(nums), len(nums))
                reps.append(nums[k].sum() / max(dens[k].sum(), 1e-9))
            return float(est), [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]
        hard_est, hard_ci = boot(per_route_hard)
        near_est, near_ci = boot(per_route_nearmiss)
        tg[f'a{a0}-{int(min(a1,999))}'] = dict(
            n=n, n_routes=len(routes[g]),
            p50=float(np.percentile(X, 50)), p90=float(np.percentile(X, 90)),
            p95=float(np.percentile(X, 95)), p99=float(np.percentile(X, 99)),
            p999=float(np.percentile(X, 99.9)), pmax=float(X.max()),
            hard_pct=hard_est * 100, hard_ci=[c * 100 for c in hard_ci],
            nearmiss_pct=near_est * 100, nearmiss_ci=[c * 100 for c in near_ci])
    tail[g] = tg
res['A_tail_and_nearmiss'] = tail

# ---------- (B) EVENT-LOCAL binding in a tight +-0.3s window around jerk peak (<15 m/s) ----------
# EV entries store kind, v, jerk, ang_max, ... but not raw traces -> recompute from route directly,
# tight window, for jerk08/jerk04 events only (peak-anchored; acc10 has no single peak instant).
evloc = {}
FS = V.FS
for g in GROUPS:
    per_kind = {'jerk04': [], 'jerk08': []}
    for rk in routes[g]:
        S = V.load(rk)
        e4 = np.nan_to_num(S['e4'])
        for thr, kind in [(0.4, 'jerk04'), (0.8, 'jerk08')]:
            ev, _ = V.jerk_events(S, jerk_thr=thr, vmin=0.0)
            for e in ev:
                if e['v'] >= 15:
                    continue
                k = e['idx']
                a, b = k - int(0.3 * FS), k + int(0.3 * FS)
                if a < 0 or b >= len(e4):
                    continue
                de4 = np.abs(np.diff(e4[a:b]))
                per_kind[kind].append(dict(route=rk, v=e['v'], jerk=abs(e['jerk_peak']),
                                            tight_hit=float(np.mean(de4 >= 120)),
                                            tight_near=float(np.mean((de4 >= 90) & (de4 < 120))),
                                            tight_peak=float(de4.max()) if len(de4) else 0.0))
        del S
    o = {}
    for kind, E in per_kind.items():
        if not E:
            o[kind] = dict(n=0); continue
        rks = np.array([e['route'] for e in E])
        arr = lambda k: np.array([e[k] for e in E], float)
        def bmed(x):
            x = np.asarray(x); ur = np.unique(rks); reps = []
            for _ in range(1000):
                pick = rng.choice(ur, len(ur))
                xs = np.concatenate([x[rks == r] for r in pick])
                if len(xs): reps.append(np.median(xs))
            return float(np.median(x)), [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]
        o[kind] = dict(n=len(E), n_routes=int(len(np.unique(rks))),
                        tight_hit_med=bmed(arr('tight_hit')), tight_near_med=bmed(arr('tight_near')),
                        tight_peak_med=bmed(arr('tight_peak')),
                        frac_events_any_tight_hit=float(np.mean(arr('tight_hit') > 0)),
                        frac_events_any_tight_near=float(np.mean(arr('tight_near') > 0)))
    evloc[g] = o
res['B_event_local_tight_window'] = evloc

# ---------- (C) block-level Spearman correlation: slew_hit vs mode_rms, per group ----------
from scipy.stats import spearmanr
corrC = {}
for g in GROUPS:
    sh_all, mr_all, rk_lab = [], [], []
    for rk in routes[g]:
        r = cache[rk]['rows']
        sh_all.append(r['slew_hit']); mr_all.append(r['mode_rms']); rk_lab.append(np.full(len(r['slew_hit']), rk))
    sh = np.concatenate(sh_all); mr = np.concatenate(mr_all)
    ok = np.isfinite(sh) & np.isfinite(mr)
    rho, p = spearmanr(sh[ok], mr[ok])
    # also: mean mode_rms in blocks with ANY limiter hit vs none
    hi = sh[ok] > 0
    corrC[g] = dict(n=int(ok.sum()), spearman_rho=float(rho), p=float(p),
                     mode_rms_when_hit=float(mr[ok][hi].mean()) if hi.sum() >= 5 else None,
                     mode_rms_when_none=float(mr[ok][~hi].mean()) if (~hi).sum() >= 5 else None,
                     n_hit_blocks=int(hi.sum()), n_blocks=int(ok.sum()))
res['C_block_spearman_slewhit_vs_moderms'] = corrC

# ---------- (D) event-triggered cross-correlation: limiter-hit indicator vs 2-3Hz mode power, lagged ----------
from scipy import signal
def bp(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)

xcorrD = {}
LAGS = np.arange(-50, 51)  # +-0.5 s at 100 Hz
for g in GROUPS:
    stacks = []
    for rk in routes[g]:
        S = V.load(rk)
        u = V.usable(S, 0, 15)
        e4 = np.nan_to_num(S['e4']); sr = np.nan_to_num(S['sr']); t = S['t']
        for a, b in V.runs(u, t, min_s=5.0):
            de4 = np.abs(np.diff(e4[a:b], prepend=e4[a]))
            hit = (de4 >= 120).astype(float)
            if hit.sum() < 2:
                continue
            md = bp(sr[a:b], 1.8, 3.0)
            modepow = md ** 2
            hit_c = hit - hit.mean()
            mp_c = modepow - modepow.mean()
            if hit_c.std() < 1e-9 or mp_c.std() < 1e-9:
                continue
            xc = signal.correlate(mp_c, hit_c, mode='full') / (len(hit_c) * hit_c.std() * mp_c.std())
            mid = len(hit_c) - 1
            seg = xc[mid - 50: mid + 51]
            if len(seg) == 101:
                stacks.append(seg)
        del S
    if stacks:
        M = np.array(stacks)
        xcorrD[g] = dict(n_runs=len(stacks),
                          peak_lag_s=float(LAGS[np.argmax(np.abs(M.mean(0)))]) / FS,
                          peak_val=float(M.mean(0)[np.argmax(np.abs(M.mean(0)))]),
                          val_at_0=float(M.mean(0)[50]),
                          val_at_plus_0p1=float(M.mean(0)[60]),  # mode power 0.1s AFTER a hit
                          val_at_minus_0p1=float(M.mean(0)[40]))  # mode power 0.1s BEFORE a hit
    else:
        xcorrD[g] = dict(n_runs=0)
res['D_event_triggered_xcorr_hit_vs_modepower'] = xcorrD

json.dump(res, open(f'{OUT}/altmethod_results.json', 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=float)[:6000])
