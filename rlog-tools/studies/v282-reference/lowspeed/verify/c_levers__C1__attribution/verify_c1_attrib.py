"""C1 attribution-lens independent check: recompute the overshoot-vs-observer table straight from
dwellpost.json (independent recount, no re-derivation of the reconstruction itself -- that part is
independently confirmed against the fork source code, see notes.txt), and check for a simpler
explanation (e.g. friction z, hold, P) that tracks overshoot as well as or better than dob does."""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CL = HERE.parent.parent / 'c_levers'
rows = json.load(open(CL / 'out' / 'dwellpost.json'))
TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob']
rng = np.random.default_rng(7)

def boot_frac(x, nb=3000):
    x = np.asarray(x, float)
    if len(x) < 3:
        return (np.nan, np.nan, np.nan)
    m = np.mean(x)
    bs = [np.mean(x[rng.integers(0, len(x), len(x))]) for _ in range(nb)]
    return (float(m), *np.percentile(bs, [2.5, 97.5]))

print("=== reproduce overshoot_summary.txt from dwellpost.json directly ===")
for lo, hi in [(2.5, 6.0), (6.0, 8.0), (6.0, 15.0), (8.0, 15.0)]:
    for tag, gs in [('observer on', ('T64', 'T64B', 'T5')), ('T64 only', ('T64',)), ('T4 no observer', ('T4',))]:
        R = [r for r in rows if r['g'] in gs and lo <= r['v'] < hi]
        if len(R) < 5:
            continue
        ov1 = boot_frac([r['over'] > 1.0 for r in R])
        print(f"{lo}-{hi} {tag:20s} n={len(R):3d} over>1deg {ov1[0]:.2f} [{ov1[1]:.2f},{ov1[2]:.2f}]  "
              f"over p50 {np.median([r['over'] for r in R]):.2f}  err0 p50 {np.median([r['err0'] for r in R]):+.2f}  "
              f"dob_rise p50 {np.median([r['post_dob'] for r in R]):+.4f}")

print("\n=== ATTRIBUTION CHECK: does overshoot correlate BETTER with some other term's build than with dob? ===")
print("(Spearman corr of dwell build b_X against overshoot magnitude, observer-on routes, 6-15 m/s)")
from scipy import stats
R = [r for r in rows if r['g'] in ('T64', 'T64B', 'T5') and 6.0 <= r['v'] < 15.0]
print(f"n={len(R)}")
over = [r['over'] for r in R]
for x in TERMS:
    b = [r['b_' + x] for r in R]
    rho, p = stats.spearmanr(b, over)
    rho2, p2 = stats.spearmanr([r['post_' + x] for r in R], over)
    print(f"  {x:7s} corr(build,over) {rho:+.2f} (p={p:.3f})   corr(post-jump change,over) {rho2:+.2f} (p={p2:.3f})")

print("\n=== simpler explanation check: does jump size ALONE predict overshoot as well as dob does? ===")
jump = [r['jump'] for r in R]
rho_j, p_j = stats.spearmanr(jump, over)
print(f"  jump size vs overshoot: corr {rho_j:+.2f} (p={p_j:.3f})")
dobr = [r['post_dob'] for r in R]
rho_d, p_d = stats.spearmanr(dobr, over)
print(f"  dob post-jump rise vs overshoot: corr {rho_d:+.2f} (p={p_d:.3f})")
# partial: does dob explain overshoot BEYOND jump size?
import numpy.polynomial.polynomial as P
resid_over = np.array(over) - np.polyval(np.polyfit(jump, over, 1), jump)
resid_dob = np.array(dobr) - np.polyval(np.polyfit(jump, dobr, 1), jump)
rho_partial, p_partial = stats.spearmanr(resid_dob, resid_over)
print(f"  dob rise vs overshoot AFTER removing jump-size trend from both (partial corr): {rho_partial:+.2f} (p={p_partial:.3f})")

print("\n=== T4 vs T64/T64B/T5: are jump sizes themselves comparable (confound check)? ===")
for tag, gs in [('T64', ('T64',)), ('T64B', ('T64B',)), ('T5', ('T5',)), ('T4', ('T4',))]:
    R2 = [r for r in rows if r['g'] in gs and 6.0 <= r['v'] < 15.0]
    if len(R2) < 5:
        continue
    print(f"  {tag:6s} n={len(R2):3d} jump p50 {np.median([r['jump'] for r in R2]):.2f} p90 {np.percentile([r['jump'] for r in R2],90):.2f}  "
          f"dwell_s p50 {np.median([r['dwell'] for r in R2]):.2f}  ang p50 {np.median([r['ang'] for r in R2]):.1f}")
