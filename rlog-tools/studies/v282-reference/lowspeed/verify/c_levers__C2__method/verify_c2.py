"""Independent re-derivation of finding C2 (AccordRateLoopGain is the only term that damps 1.8-3.5 Hz
wheel-shake at low speed; the whole command minus rate_t is negative <8 m/s; untapered <12 m/s).

Method, deliberately NOT a straight re-run of cl_reach.py:
  - Reuse cl_recon.reconstruct() for the per-term decomposition (already checked line-by-line against
    latcontrol_torque.py @84766cdc / latcontrol_vehicle_tunes.py for sign; see verify notes below), but
    write a FRESH, differently-windowed b_eq estimator: per-run OLS slope of band-passed term on
    band-passed steering rate (single design-matrix regression, not the pooled-dot-product estimator
    cl_reach.py uses), at lag 0/3/6 samples, then pool runs by inverse-variance-free simple mean +
    route-level bootstrap CI (resampling RUNS, not frames, so autocorrelation does not inflate the CI).
  - Recompute untapered-below-12-m/s and DOB-fade-3-to-6 directly from the fork's own constants
    (HONDA_ACCORD_RATE_LOOP_TAPER_V, HONDA_ACCORD_DOB_FADE_V_BP), not from cl_recon's copy of them.
  - Recompute the dwell/overshoot fraction with an independently written event detector (different
    smoothing window and pre/post travel thresholds) on T64 (observer on) vs T4 (observer off, dob=0.0).

One route loaded at a time; reduced arrays kept, raw route dict deleted before moving to the next.
"""
import sys, gc, json
from pathlib import Path
import numpy as np
from scipy import signal

BASE = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, str(BASE / 'lowspeed' / 'c_levers'))
sys.path.insert(0, str(BASE))
import cl_recon as C
V = C.V
HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
FS = 100.0
rng = np.random.default_rng(7)

# ---- fork constants, read directly (independent of cl_recon's copies) ----
FORK = Path('C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py')
src = FORK.read_text(encoding='utf-8', errors='replace')
def const(name):
    for line in src.splitlines():
        line = line.strip()
        if line.startswith(name + ' ') or line.startswith(name + '='):
            rhs = line.split('=', 1)[1].split('#')[0].strip()
            return eval(rhs)
    raise KeyError(name)
TAPER_V = const('HONDA_ACCORD_RATE_LOOP_TAPER_V')
DOB_FADE_BP = const('HONDA_ACCORD_DOB_FADE_V_BP')
print(f"[const] HONDA_ACCORD_RATE_LOOP_TAPER_V = {TAPER_V}  (claim: untapered below 12 m/s)")
print(f"[const] HONDA_ACCORD_DOB_FADE_V_BP = {DOB_FADE_BP}  (claim: fade 3 -> 6 m/s, full at 6)")
assert TAPER_V == 12.0
assert DOB_FADE_BP == [3.0, 6.0]


def bp(x, f1, f2, order=2):
    return signal.sosfiltfilt(signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos'), x)


def ols_slope(x, y):
    """y = b*x + resid, x,y already band-passed & zero-mean-ish; returns b, or nan if x has ~no energy."""
    xx = float(np.dot(x, x))
    if xx < 1e-9:
        return np.nan
    return float(np.dot(x, y) / xx)


def dil(m, n=50):
    from scipy import ndimage
    return ndimage.binary_dilation(m, structure=np.ones(2 * n + 1, bool))


TERMS = ['P', 'rate_t', 'out']
VBINS = [(2.5, 5.0), (5.0, 8.0), (8.0, 15.0)]


def route_runs_beq(rk):
    D = C.reconstruct(rk)
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & ~dil(D['pressed']) & (v >= 2.5) & (v < 15.0)
    rows = []
    for a, b in V.runs(HO, t, min_s=2.0):
        if b - a < 256:
            continue
        vb = float(np.median(v[a:b]))
        binidx = None
        for k, (lo, hi) in enumerate(VBINS):
            if lo <= vb < hi:
                binidx = k
        if binidx is None:
            continue
        sr_b = bp(D['sr'][a:b], 1.8, 3.5)
        row = dict(rk=rk, bin=binidx, n=b - a, sec=(b - a) / FS)
        for x in TERMS:
            xb = bp(D[x][a:b], 1.8, 3.5)
            for tau, tname in ((0, 't0'), (3, 't3'), (6, 't6')):
                # b_eq = -<term(t-tau), rate(t)> / <rate(t), rate(t)> : term LEADS rate by tau samples
                # (term now -> rate response tau later). Regress TERM (dependent) on RATE (independent),
                # matching docstring's -<T,rate>/<rate,rate>: slope = <rate,term>/<rate,rate>, b_eq = -slope.
                xs = xb[: len(xb) - tau] if tau else xb           # term, earlier window
                ys = sr_b[tau:] if tau else sr_b                  # rate, later window (same length as xs)
                slope = ols_slope(ys, xs)          # term per unit rate (independent var = rate)
                row[f'{x}_{tname}'] = -slope if np.isfinite(slope) else np.nan   # >0 damps convention
        rows.append(row)
    del D
    gc.collect()
    return rows


print("\n=== re-derivation: per-run OLS b_eq, 1.8-3.5 Hz, route T64 (0000006c--68c6e94b17) ===")
rows64 = route_runs_beq('0000006c--68c6e94b17')
rows64d = route_runs_beq('0000006d--05e83bb04f')
allrows = rows64 + rows64d
for k, (lo, hi) in enumerate(VBINS):
    R = [r for r in allrows if r['bin'] == k]
    if not R:
        continue
    sec = sum(r['sec'] for r in R)
    for x in TERMS:
        vals = np.array([r[f'{x}_t3'] for r in R])
        w = np.array([r['sec'] for r in R])
        wavg = float(np.average(vals, weights=w))
        # bootstrap over RUNS (not frames)
        bs = []
        idx = np.arange(len(R))
        for _ in range(3000):
            pick = rng.choice(idx, len(idx), replace=True)
            wv = w[pick]
            bs.append(np.average(vals[pick], weights=wv))
        lo_ci, hi_ci = np.percentile(bs, [2.5, 97.5])
        print(f"  {lo:.1f}-{hi:.1f} m/s  n_runs={len(R):3d} sec={sec:6.0f}  {x:7s} b30 (run-OLS, weighted mean) "
              f"{wavg*1e4:+.2f}  [95% CI {lo_ci*1e4:+.2f},{hi_ci*1e4:+.2f}] x1e-4")
    out_minus_rate = np.array([r['out_t3'] - r['rate_t_t3'] for r in R])
    w = np.array([r['sec'] for r in R])
    print(f"    -> command WITHOUT rate loop (out - rate_t), weighted mean: {np.average(out_minus_rate, weights=w)*1e4:+.2f} x1e-4")

print("\n=== overshoot fraction, independent event detector: dwell smoothing window 6 (not 10), pre/post travel 0.4 deg (not 0.5) ===")


def overshoot_indep(rk, label):
    D = C.reconstruct(rk)
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & ~D['pressed'] & (v >= 2.5) & (v < 15.0)
    over1 = tot = 0
    overs = []
    for a, b in V.runs(HO, t, min_s=2.0):
        m_ = b - a
        rsm = np.convolve(np.abs(D['sr'][a:b]), np.ones(6) / 6, 'same')
        low = rsm < 0.8
        aa = D['sa'][a:b]
        i = 0
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            if j - i + 1 >= 10 and i - 40 >= 0 and j + 80 < m_:
                pre = aa[i] - aa[i - 40]; post = aa[min(j + 40, m_ - 1)] - aa[j]
                if abs(pre) >= 0.4 and abs(post) >= 0.4 and np.sign(pre) == np.sign(post):
                    s = np.sign(post); g = a + j
                    e = s * (D['angle_des'][g:g + 81] - D['sa'][g:g + 81])
                    ov = max(0.0, -float(e.min()))
                    overs.append(ov)
                    tot += 1
                    if ov > 1.0:
                        over1 += 1
            i = j + 1
    frac = over1 / tot if tot else float('nan')
    print(f"  {label:28s} n={tot:4d}  overshoot>1deg frac {frac:.2f}  median {np.median(overs) if overs else float('nan'):.2f} deg")
    del D
    gc.collect()
    return frac, tot


f_on1, n_on1 = overshoot_indep('0000006c--68c6e94b17', 'T64 (observer on)')
f_on2, n_on2 = overshoot_indep('0000006d--05e83bb04f', 'T64 (observer on) rd')
f_off, n_off = overshoot_indep('00000075--6c8687d5bd', 'T4 (observer off, dob=0.0)')

print(f"\n  pooled T64 observer-on: n={n_on1+n_on2}  T4 observer-off: n={n_off}")


print("\n=== 3.5-6 Hz 'pumping band' b_eq for rate_t, independent per-run OLS, tau 3/6, T64 pooled (2.5-15 m/s combined) ===")


def route_runs_beq_pump(rk):
    D = C.reconstruct(rk)
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & ~dil(D['pressed']) & (v >= 2.5) & (v < 15.0)
    rows = []
    for a, b in V.runs(HO, t, min_s=2.0):
        if b - a < 256:
            continue
        sr_b = bp(D['sr'][a:b], 3.5, 6.0)
        xb = bp(D['rate_t'][a:b], 3.5, 6.0)
        row = dict(sec=(b - a) / FS)
        for tau, tname in ((3, 't3'), (6, 't6')):
            xs = xb[: len(xb) - tau]; ys = sr_b[tau:]
            slope = ols_slope(ys, xs)
            row[tname] = -slope if np.isfinite(slope) else np.nan
        rows.append(row)
    del D; gc.collect()
    return rows


pr = route_runs_beq_pump('0000006c--68c6e94b17') + route_runs_beq_pump('0000006d--05e83bb04f')
w = np.array([r['sec'] for r in pr])
for tname in ('t3', 't6'):
    vals = np.array([r[tname] for r in pr])
    print(f"  rate_t b{tname[1:]}0ms (weighted mean over {len(pr)} runs): {np.average(vals, weights=w)*1e4:+.2f} x1e-4")

