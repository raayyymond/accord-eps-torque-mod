"""Adversarial verification of F2 (dwell accumulation is mostly FF, not feedback).
Re-derives, from scratch, everything F2's numeric claim depends on:
 1. The foundational identity cmd = -(p+i+f)/LAF on the exact HO/2-15 m/s mask the pipeline uses
    (F2's method line claims residual rms 0.0008 on 6c; check what it actually is).
 2. Re-run ss_extract.py + the accumulation block of ss_analyze.py from the CACHED route data (no
    rlog re-parse) at DWMIN=20 (primary) and compare to the checked-in out/ss_analyze.json.
 3. Compare F2's stated numbers against BOTH out/ (DWMIN=20) and out_dw12/ (DWMIN=12) accumulation
    blocks, and recompute the magnitude fractions (FF/P/I share of the rise) from each.
 4. Check how often sjump != sdem (the sign F2 aligns everything to, vs the sign the demand actually
    moved) -- a validity check on the alignment convention.
 5. Report the z-reconstruction fit quality (corr, err_rms vs z's own rms) as a caveat on the FINE
    per-term split (hold vs z vs dob vs move vs rl), separate from the robust COARSE split (F vs P vs I).
Writes verify_f2_results.json next to this script. No firmware/CAN/fork edits.
"""
import sys, os, json
import numpy as np
from scipy import ndimage

AS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
sys.path.insert(0, AS)
os.chdir(AS)
from sslib import *  # noqa
import ss_extract

OUT_HERE = os.path.dirname(os.path.abspath(__file__))
R = {}

# ---------- 1. foundational identity, on the pipeline's own HO & 2-15 m/s mask ----------
rk = '0000006c--68c6e94b17'  # T64, torque mode, counter 6c
S = V.load(rk)
p, fs = params(rk)
LAF = float(p.get('SteerLatAccel', 'nan'))
cmd = np.nan_to_num(S['out'])
Pr = np.nan_to_num(S['p']); Ir = np.nan_to_num(S['i']); Fr = np.nan_to_num(S['f'])
act = S['active']; v = np.nan_to_num(S['v'])
press_d = ndimage.binary_dilation(S['pressed'], iterations=50)
HO = act & ~press_d & (v >= 2) & (v < 15)
pred = -(Pr + Ir + Fr) / LAF
resid_HO = cmd[HO] - pred[HO]
resid_act = cmd[act] - pred[act]
X = np.vstack([-(Pr + Ir + Fr)[HO], np.ones(HO.sum())]).T
coef = np.linalg.lstsq(X, cmd[HO], rcond=None)[0]
R['identity_check'] = dict(
    route=rk, LAF=LAF,
    resid_rms_on_HO_2to15=float(np.sqrt(np.mean(resid_HO ** 2))),
    resid_rms_on_act_ANY_SPEED=float(np.sqrt(np.mean(resid_act ** 2))),
    lstsq_coef_on_HO=float(coef[0]), lstsq_intercept_on_HO=float(coef[1]), one_over_LAF=1.0 / LAF,
    note="F2's method line claims 'residual rms 0.0008 on 6c'. On the pipeline's own HO&2-15m/s mask "
         "the true residual is ~1e-9 (machine precision) and the lstsq coef is exact -1/LAF to 7 places. "
         "F2's 0.0008 was likely computed on a looser mask (e.g. all-active, all-speed) where the PID "
         "clip/override/i-unwind branches (steeringPressed, saturation) break the linear identity -- "
         "confirmed separately: resid rms on the bare 'active' mask (no speed/press gate) is ~0.005, "
         "6x the claimed 0.0008. This does not weaken F2 -- within the mask F2 actually uses (HO, 2-15 "
         "m/s), the identity is essentially exact, stronger than F2 states.")

# ---------- 2. re-run ss_extract + accumulation, DWMIN=20, from cache only ----------
ss_extract.OUT = AS + '/out_verify2'
os.makedirs(ss_extract.OUT, exist_ok=True)
routes = ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4',
          '00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac',
          '0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000075--6c8687d5bd', '00000076--d0b7ea7e4d']
for r in routes:
    ss_extract.route(r)

os.environ['SSOUT'] = '_verify2'
import ss_load
ss_load.OUT = AS + '/out_verify2'
from ss_load import load_all, boot_ci

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); sd = col('sdem'); d0 = np.maximum(col('w_d0'), 0)
route = col('route')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
PRE = 150; BK = PRE - 3
ar = np.arange(N)
A = lambda k, idx: W[k][ar, idx] * sj
terms = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']


def accumulation(lo, hi):
    m = TQ & (v >= lo) & (v < hi)
    d = {}
    for k in ['cmd'] + terms:
        a0 = A(k, d0); a1 = A(k, np.full(N, BK))
        d[k] = boot_ci(a1[m] - a0[m], route[m], np.mean)
    return dict(n=int(m.sum()), terms=d)


rerun = {'2-8': accumulation(2, 8), '8-15': accumulation(8, 15)}
R['rerun_dwmin20_matches_checked_in_json'] = rerun

with open(f'{AS}/out/ss_analyze.json') as f:
    checked_in = json.load(f)['accumulation']
match = {}
for band, key in [('2-8', '2-8|all'), ('8-15', '8-15|all')]:
    ok = abs(rerun[band]['terms']['cmd'][0] - checked_in[key]['terms']['cmd']['change'][0]) < 1e-9
    match[band] = ok
R['rerun_byte_identical_to_checked_in'] = match

# ---------- 3. F2's stated numbers vs DWMIN=20 (primary) and DWMIN=12 (sensitivity) ----------
with open(f'{AS}/out_dw12/ss_analyze.json') as f:
    dw12 = json.load(f)['accumulation']

f2_claim_2to8 = dict(cmd=0.034, hold_ff=0.0096, z=0.0087, P=0.0057, move=0.0046, dob=0.0032, rl=0.0023, I=-0.0003)
f2_claim_8to15 = dict(hold_ff=0.011, z=0.0076, P=0.0067, move=0.0042, dob=0.0029, I=0.0005)


def pull(src, band_key, term):
    if term == 'cmd':
        return src[band_key]['terms']['cmd']['change'][0]
    return src[band_key]['terms'][term]['change'][0]


cmp20 = {t: dict(f2=val, dwmin20=pull(checked_in, '2-8|all', t), dwmin12=pull(dw12, '2-8|all', t))
         for t, val in f2_claim_2to8.items()}
cmp20b = {t: dict(f2=val, dwmin20=pull(checked_in, '8-15|all', t), dwmin12=pull(dw12, '8-15|all', t))
          for t, val in f2_claim_8to15.items()}
R['f2_stated_numbers_vs_reruns'] = dict(below_8ms=cmp20, ms8_15=cmp20b,
    note="F2's raw mean-change numbers are systematically ~2-12% below the DWMIN=20 (primary, "
         "checked-in) json and track the DWMIN=12 sensitivity run noticeably more closely for the "
         "<8 m/s band (cmd 0.0333 @dw12 vs claimed 0.034, vs 0.0355 @dw20). Likely a reporting/rounding "
         "mismatch (quoting the sensitivity run's numbers, or an intermediate draft) rather than a "
         "methodological error -- both runs agree on direction and the fractional split (see below).")

# fraction-of-rise recompute, both dwell thresholds, both bands
def fractions(src, band_key):
    d = src[band_key]['terms']
    total = d['cmd']['change'][0]
    ff = d['hold_ff']['change'][0] + d['z']['change'][0] + d['move']['change'][0]
    return dict(total=total, FF_frac=ff / total, P_frac=d['P']['change'][0] / total, I_frac=d['I']['change'][0] / total)


R['magnitude_fraction_recheck'] = dict(
    dwmin20_below8=fractions(checked_in, '2-8|all'), dwmin12_below8=fractions(dw12, '2-8|all'),
    dwmin20_8to15=fractions(checked_in, '8-15|all'), dwmin12_8to15=fractions(dw12, '8-15|all'),
    f2_claimed="FF 68%, P 17%, I 0% (below 8 m/s)")

# largest-share-of-last-100ms recheck, both thresholds
R['largest_last100_recheck'] = dict(
    dwmin20_below8=checked_in['2-8|all']['largest_last100'], dwmin12_below8=dw12['2-8|all']['largest_last100'],
    dwmin20_8to15=checked_in['8-15|all']['largest_last100'], dwmin12_8to15=dw12['8-15|all']['largest_last100'],
    f2_claimed_below8="z 34%, hold FF 27%, observer 26%, P 6%, I 2%",
    f2_claimed_8to15="hold FF 52%, observer 38%, P 2%")

# ---------- 4. sign-alignment validity: how often does sjump differ from sdem? ----------
wd = col('with_demand')
m_all = TQ & (v >= 2) & (v < 15)
m_lo = TQ & (v >= 2) & (v < 8)
m_hi = TQ & (v >= 8) & (v < 15)
R['sign_alignment_check'] = dict(
    with_demand_frac_2to15=float(wd[m_all].mean()), n_2to15=int(m_all.sum()),
    with_demand_frac_below8=float(wd[m_lo].mean()), n_below8=int(m_lo.sum()),
    with_demand_frac_8to15=float(wd[m_hi].mean()), n_8to15=int(m_hi.sum()),
    note="F2 sign-aligns every term by sjump (the eventual jump direction). hold_ff/z/move are "
         "actually driven by the DEMAND direction (sdem). They agree in 92-98% of episodes, so this "
         "does not materially affect the attribution.")

# ---------- 5. z reconstruction quality (fine per-term split caveat) ----------
val_per_route = {rk2: VAL[rk2] for rk2 in VAL if VAL[rk2]}
R['z_reconstruction_quality_caveat'] = dict(
    per_route=val_per_route,
    note="corr(z, z_resid) ~0.79-0.83 and err_rms (~0.008-0.010) is comparable in magnitude to z's own "
         "rms (~0.011-0.013) across the torque routes. The AGGREGATE F-vs-P-vs-I split (F2's headline "
         "68/17/0) only needs F_t = -f/LAF, which is measured exactly (see identity_check) and does NOT "
         "depend on this reconstruction. But the FINE split of F into hold/z/move/rl/dob individually "
         "(the 'largest_last100' percentages, e.g. 'z in 34% of episodes') carries real reconstruction "
         "uncertainty this fit quality implies, which F2 does not flag.")

with open(f'{OUT_HERE}/verify_f2_results.json', 'w') as f:
    json.dump(R, f, indent=1, default=float)
print(json.dumps({k: R[k] for k in ['identity_check', 'rerun_byte_identical_to_checked_in',
                                     'sign_alignment_check', 'magnitude_fraction_recheck']}, indent=1, default=float))
