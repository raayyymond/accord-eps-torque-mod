"""Adversarial POWER check on s2_jerk finding 'texture-not-event-triggered-ring'.

Claim: 1.5-3.5 Hz steer-rate texture (sr_ring) is elevated in T64 (torque mode) vs V282, but the
POST/PRE ratio does not rise during the event above 15 m/s (diff -0.06 [-0.59,+0.23], n=48 matched
pairs), so it's "background texture, not an event-triggered ring".

This script:
 1. Reproduces the matched-pair sr_ring_ratio diff-of-ratios statistic (sanity check against s2_results.json).
 2. Computes a WITHIN-GROUP (T64 only) paired pre-vs-post test -- the direct test of "does T64's own
    texture rise during the event" -- which does not need a V282 comparison and should have materially
    more power than a between-group difference-of-ratios if the reported null is an artifact of a
    low-power statistic choice.
 3. Runs an effect-injection power simulation (route-cluster + event bootstrap, matching the study's own
    CI method) for BOTH statistics, at both strata (>=15 m/s n=48-56, 8-15 m/s n=10-12), to find the
    smallest multiplicative post-event amplification that would be detected at 80% power, alpha 0.05
    (two-sided, CI excludes null).
 4. Reports observed effect vs MDE for each statistic/stratum so the parent orchestrator can judge whether
    the reported null is genuinely resolved or just underpowered.

Uses raw per-event sr_ring_pre/sr_ring_post already computed in s2_extract's saved rows -- no new
extraction needed, no route rlogs reloaded (RAM-safe).
"""
import sys, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all, match, boot_diff, boot_group

OUTDIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__texturenotev__power'

rows, tr = load_all()
for r in rows:
    r['sr_ring_ratio'] = r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6)
    r['log_ring_ratio'] = np.log(r['sr_ring_ratio'])

REF = [r for r in rows if r['group'] == 'V282']
STRATA = {'hi>=15': [2, 3], 'v8-15': [1]}

results = {}

# ---------- 1. sanity: reproduce the published matched-pair diff-of-ratios statistic
print('=== 1. Reproduce published statistic (matched-pair diff of sr_ring_ratio) ===')
TQ = [r for r in rows if r['group'] == 'T64']
pairs_all = match(REF, TQ)
for sn, vbs in STRATA.items():
    P = [p for p in pairs_all if p[1]['vb'] in vbs]
    b = boot_diff(P, 'sr_ring_ratio')
    print(f'  {sn}: n_pairs={b["n"]} diff={b["med"]:+.3f} evCI={tuple(round(x,3) for x in b["ci_ev"])} rtCI={tuple(round(x,3) for x in b["ci_rt"])}')
    results.setdefault(sn, {})['published_diff_of_ratios'] = b

# ---------- 2. within-group (T64-only) paired pre/post test: the direct, higher-power test
print('\n=== 2. Within-group T64-only paired pre/post (log ratio), no V282 differencing ===')
for sn, vbs in STRATA.items():
    R = [r for r in rows if r['group'] == 'T64' and r['vb'] in vbs]
    b = boot_group(R, 'log_ring_ratio')
    ratio_med = float(np.exp(b['med'])); ci_ratio = tuple(float(np.exp(x)) for x in b['ci'])
    print(f'  {sn}: n={b["n"]} median log-ratio={b["med"]:+.3f} (ratio {ratio_med:.3f}) CI(log)={tuple(round(x,3) for x in b["ci"])} CI(ratio)=({ci_ratio[0]:.3f},{ci_ratio[1]:.3f})')
    results[sn]['within_T64_paired'] = dict(n=b['n'], log_med=b['med'], log_ci=b['ci'], ratio_med=ratio_med, ratio_ci=ci_ratio)
    # also unmatched V282-only, for reference (is V282's own post/pre also ~1?)
    RV = [r for r in rows if r['group'] == 'V282' and r['vb'] in vbs]
    bv = boot_group(RV, 'log_ring_ratio')
    print(f'    (V282-only for comparison: n={bv["n"]} ratio={np.exp(bv["med"]):.3f} CI=({np.exp(bv["ci"][0]):.3f},{np.exp(bv["ci"][1]):.3f}))')
    results[sn]['within_V282_paired'] = dict(n=bv['n'], ratio_med=float(np.exp(bv['med'])),
                                             ratio_ci=(float(np.exp(bv['ci'][0])), float(np.exp(bv['ci'][1]))))

# ---------- 3. effect-injection power simulation
print('\n=== 3. Effect-injection power sim: smallest post-event amplification detected at 80% power, alpha 0.05 ===')
rng_global = np.random.default_rng(0)


def inject_and_test_within(R, factor, n_boot=1500, seed=0):
    """Inject a multiplicative bump of `factor` onto sr_ring_post for each row in R (simulating a TRUE
    event-triggered rise on top of the observed data), recompute log-ratio, bootstrap CI (route-cluster),
    return True if CI excludes 0 (i.e. the *baseline* null -- log-ratio==0 -- would be rejected).
    Uses the ACTUAL observed rows as the resampling universe (preserves real noise/skew/route clustering)."""
    Rj = []
    for r in R:
        rr = dict(r)
        rr['log_ring_ratio'] = np.log(factor * r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6))
        Rj.append(rr)
    b = boot_group(Rj, 'log_ring_ratio', n=n_boot, seed=seed)
    return not (b['ci'][0] <= 0 <= b['ci'][1])


def inject_and_test_diff(pairs, factor, n_boot=1500, seed=0):
    """Same injection but on the published between-group diff-of-ratios statistic: bump T64's post only."""
    Pj = []
    for r0, r1 in pairs:
        r1j = dict(r1)
        r1j['sr_ring_ratio'] = (factor * r1['sr_ring_post']) / max(r1['sr_ring_pre'], 1e-6)
        Pj.append((r0, r1j))
    b = boot_diff(Pj, 'sr_ring_ratio', n=n_boot, seed=seed)
    return not (b['ci_rt'][0] <= 0 <= b['ci_rt'][1])


FACTORS = [1.0, 1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.5, 3.0, 4.0]
N_REPS = 12  # repeat detection test with different bootstrap seeds to estimate power (fraction of seeds that reject)

for sn, vbs in STRATA.items():
    R = [r for r in rows if r['group'] == 'T64' and r['vb'] in vbs]
    P = [p for p in pairs_all if p[1]['vb'] in vbs]
    print(f'\n  -- {sn}: within-group n={len(R)}, matched-pairs n={len(P)}')
    mde_within, mde_diff = None, None
    for f in FACTORS:
        pw_within = np.mean([inject_and_test_within(R, f, seed=1000 + s) for s in range(N_REPS)])
        pw_diff = np.mean([inject_and_test_diff(P, f, seed=2000 + s) for s in range(N_REPS)])
        print(f'     factor {f:>4.1f}x post-only bump: power(within-T64)={pw_within:.2f}  power(published diff-of-ratios)={pw_diff:.2f}')
        if mde_within is None and pw_within >= 0.8:
            mde_within = f
        if mde_diff is None and pw_diff >= 0.8:
            mde_diff = f
    print(f'     => MDE @80% power: within-T64 test = {mde_within}x, published diff-of-ratios test = {mde_diff}x')
    results[sn]['mde_within_80pct'] = mde_within
    results[sn]['mde_diff_80pct'] = mde_diff

# ---------- 4. what does the finding's own "may double" scenario imply for the diff-of-ratios test
print('\n=== 4. Cross-check: finding says v8-15 "may double" during event -- test factor=2.0 explicitly ===')
for sn in ('v8-15', 'hi>=15'):
    print(f'  {sn}: MDE within-T64={results[sn]["mde_within_80pct"]}x, MDE published-diff={results[sn]["mde_diff_80pct"]}x, '
          f'observed within-T64 ratio median={results[sn]["within_T64_paired"]["ratio_med"]:.3f}')

json.dump(results, open(f'{OUTDIR}/power_results.json', 'w'), indent=1, default=float)
print('\nWrote', f'{OUTDIR}/power_results.json')
