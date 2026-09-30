"""ADV-bytes (p-gain) step 6: are the design's null-sentence thresholds decidable with r71b's OWN sampling spread?
 (2) 8-22 m/s turn-hold <= 0.72 (V294 0.67-0.69; predicted 0.75-0.78) and 22+ tracking <= 0.95 (V294 0.924; pred ~0.98)
 (3) the 5-10 m/s matched hard-turn 1.6-3 Hz cell > x1.10 vs r71b -> revert
Method: resample r71b's own episodes/stretches with replacement (block bootstrap) and report the 95 % interval of each
statistic, i.e. how far a V294 drive of the same exposure could land from r71b by sampling alone.  My own simple
turn-hold / tracking-gain definitions (desired vs actual lateral accel from the controller's log), not the bands
agent's scorer, so the SPREAD is what is used, not the level."""
import contextlib, io, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (HERE, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant"),
          os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"), os.path.join(KIT, "rlog-tools", "studies", "grind")):
    sys.path.insert(0, p)
import plib as P
rng = np.random.default_rng(7)
d = P.load()
v, la_d, la_a = d["v"], d["ctl_la_des"], d["ctl_la_act"]
eng = d["eng"].astype(bool) & (d["cc_lat_active"] > 0.5)


def boot(vals, w, n=4000):
    vals, w = np.asarray(vals, float), np.asarray(w, float)
    k = len(vals)
    out = []
    for _ in range(n):
        s = rng.integers(0, k, k)
        out.append(np.sum(vals[s] * w[s]) / np.sum(w[s]))
    return np.percentile(out, [2.5, 50, 97.5])


print("TURN-HOLD (|la_des| 0.8-1.5 m/s^2 holds >= 1 s, act/des per episode, weighted by duration), r71b:")
for lo, hi in ((8, 15), (15, 22), (22, 99)):
    m = eng & (v >= lo) & (v < hi) & (np.abs(la_d) >= 0.8) & (np.abs(la_d) <= 1.5)
    runs = P.runs(m, 100)
    if len(runs) < 3:
        print("  %d-%d: %d episodes -- too few" % (lo, hi, len(runs))); continue
    r = [np.mean(la_a[a:b] * np.sign(la_d[a:b])) / np.mean(np.abs(la_d[a:b])) for a, b in runs]
    wts = [b - a for a, b in runs]
    ci = boot(r, wts)
    print("  %2d-%2d m/s: %2d episodes, %4.0f s: point %.3f  95%% bootstrap [%.3f, %.3f]  (half-width %.3f)"
          % (lo, hi, len(runs), sum(wts) / 100, np.sum(np.array(r) * wts) / np.sum(wts), ci[0], ci[2], (ci[2] - ci[0]) / 2))

print("\nTRACKING GAIN (slope of la_act on la_des, engaged, block bootstrap over 20 s blocks), r71b:")
blk = (np.arange(len(v)) // 2000)
for lo, hi in ((8, 15), (15, 22), (22, 99)):
    m = eng & (v >= lo) & (v < hi) & np.isfinite(la_a) & np.isfinite(la_d)
    ub = np.unique(blk[m])
    Sxx = np.array([np.sum(la_d[m & (blk == u)] ** 2) for u in ub])
    Sxy = np.array([np.sum(la_d[m & (blk == u)] * la_a[m & (blk == u)]) for u in ub])
    pt = Sxy.sum() / Sxx.sum()
    bs = []
    for _ in range(4000):
        s = rng.integers(0, len(ub), len(ub))
        bs.append(Sxy[s].sum() / Sxx[s].sum())
    ci = np.percentile(bs, [2.5, 97.5])
    print("  %2d-%2d m/s: %3d blocks (%4.0f s): gain %.3f  95%% [%.3f, %.3f]  (half-width %.3f)"
          % (lo, hi, len(ub), m.sum() / 100, pt, ci[0], ci[1], (ci[1] - ci[0]) / 2))

# the matched hard-turn cell: bands agent's own masks (hardturn_matched), bootstrap over its >= 2 s stretches
with contextlib.redirect_stdout(io.StringIO()):
    import v293_ident_lib as L
    import v293r3_read as R3
    g = R3.load_plus("r71b_v294")
FS = 100.0
vv = g["v"]
rate = np.nan_to_num(g["rate_dps"])
e2 = g["eng"] & (g["cs_active"] > 0.5) & np.isfinite(vv)
w = int(0.5 * FS)
pb = np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
D = np.abs(np.nan_to_num(g["des_curv"] * vv ** 2))
print("\nMATCHED HARD-TURN CELL r16 (1.6-3 Hz wheel-rate rms), bootstrap over the cell's own >= 2 s stretches, r71b:")
for strat, base in (("hands-off", e2 & ~pb), ("engaged", e2)):
    for lo, hi in ((5, 10), (15, 22)):
        m = base & (vv >= lo) & (vv < hi) & (D >= 1.5)
        st = L.stretches(m, int(2 * FS))
        if not st:
            continue
        ss = [np.sum(L.bandpass(rate[a:b], 1.6, 3.0) ** 2) for a, b in st]
        nn = [b - a for a, b in st]
        pt = np.sqrt(np.sum(ss) / np.sum(nn))
        bs = []
        for _ in range(4000):
            s = rng.integers(0, len(st), len(st))
            bs.append(np.sqrt(np.sum(np.array(ss)[s]) / np.sum(np.array(nn)[s])))
        ci = np.percentile(bs, [2.5, 97.5])
        print("  %-9s %2d-%2d |D|>=1.5: %d stretches, %4.1f s: r16 %.2f deg/s  95%% [%.2f, %.2f]  = x%.2f .. x%.2f of the point"
              % (strat, lo, hi, len(st), sum(nn) / FS, pt, ci[0], ci[1], ci[0] / pt, ci[1] / pt))
