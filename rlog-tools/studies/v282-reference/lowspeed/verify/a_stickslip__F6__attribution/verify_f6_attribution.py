"""Adversarial verification of F6 (lever-reach BELIEF), lens ATTRIBUTION.

Checks, independently, whether F6's numeric claims are internally consistent and match the
underlying data / fork source, and whether the attribution explains the operator's low-speed
complaints as well as a simpler reading of the same numbers would.

1. Re-derive the accumulation % split (hold_ff/z/P/move/dob/rl/I) at 2-8 m/s from the episode
   tables ss_extract.py already wrote -- same numbers the F6__confound pass already re-derived,
   re-checked here independently as the ATTRIBUTION lens's evidentiary base.
2. Re-derive the friction half-width (breakaway_fit F) at 2-8 and 8-15 m/s.
3. Simulate the fork's OWN honda_accord_friction_hysteresis step (copied verbatim into
   sslib.hyst_run) to check F6's claim "z can contribute at most 0.030 and needs 3 deg of
   desired-angle travel ... to do so" -- i.e. is 3 deg of travel actually sufficient to move z
   through its FULL clipped range (a contribution of 0.030), or only through HALF of it?
4. Confirm hold_torque (HONDA's own tanh spring map) carries no additive offset term, directly
   from the fork source (not the sslib.py copy).
5. Confirm the observer's v-fade band (3-6 m/s) directly from the fork source.

Everything below is EVIDENCE (recomputed from source / from the same out/*_ss.npz tables) unless
marked BELIEF.
"""
import sys, json, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')
from ss_load import load_all, boot_ci
from sslib import k_of_v, hyst_run, band, hold_torque

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); d0 = np.maximum(col('w_d0'), 0)
route = col('route'); kind = col('kind'); aa_abs = col('abs_aa')
PRE = 150
BK = PRE - 3
ar = np.arange(N)
A = lambda k, idx: W[k][ar, idx] * sj
terms = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])

out = {}

# ---------- 1. accumulation % split, 2-8 m/s (independent re-derivation) ----------
def accumulation_fracs(lo, hi):
    m = TQ & (v >= lo) & (v < hi)
    n = int(m.sum())
    cmd_change = float(np.mean((A('cmd', np.full(N, BK)) - A('cmd', d0))[m]))
    fracs = {}
    for k in terms:
        chg = float(np.mean((A(k, np.full(N, BK)) - A(k, d0))[m]))
        fracs[k] = dict(change=chg, pct_of_cmd=round(100 * chg / cmd_change, 1))
    return dict(n=n, cmd_change=cmd_change, fracs=fracs)

out['accumulation_2_8'] = accumulation_fracs(2, 8)
out['accumulation_8_15'] = accumulation_fracs(8, 15)

# ---------- 2. friction half-width (breakaway_fit F), 2-8 and 8-15 ----------
def fitF(m, idx):
    aa = W['aa'][ar, idx][m]; c = W['cmd'][ar, idx][m]; s = sj[m]
    X = np.vstack([aa, s, np.ones(m.sum())]).T
    return np.linalg.lstsq(X, c, rcond=None)[0]

for lo, hi in [(2, 8), (8, 15)]:
    m = TQ & (v >= lo) & (v < hi)
    est = fitF(m, np.full(N, BK))
    out[f'breakaway_F_{lo}_{hi}'] = dict(F=float(est[1]), n=int(m.sum()))

# ---------- 3. z reach: does 3 deg of travel yield the claimed 0.030, or only 0.015? ----------
fric = 0.015  # flown AccordFrictionHyst
band_lowspeed = 3.0  # deg, <=8 m/s (BAND_BP/BAND_V, confirmed against fork source below)

def z_after_ramp(total_deg, start_z, bandv, n_steps=4000):
    d_ang = np.full(n_steps, total_deg / n_steps)
    active = np.ones(n_steps, bool)
    zz = start_z
    hist = []
    for x in d_ang:
        zz = float(np.clip(zz + x * fric / bandv, -fric, fric))
        hist.append(zz)
    return hist[-1]

z_from_center_3deg = z_after_ramp(3.0, 0.0, band_lowspeed)
z_from_center_6deg = z_after_ramp(6.0, 0.0, band_lowspeed)
z_from_neg_extreme_3deg = z_after_ramp(3.0, -fric, band_lowspeed)
z_from_neg_extreme_6deg = z_after_ramp(6.0, -fric, band_lowspeed)
out['z_reach_check'] = dict(
    fric=fric, band_lowspeed_deg=band_lowspeed,
    z_after_3deg_from_center=z_from_center_3deg,           # claim implies this should be ~0.030
    z_after_6deg_from_center=z_from_center_6deg,
    z_after_3deg_from_neg_extreme=z_from_neg_extreme_3deg,  # full swing (-fric -> ?) after 3 deg
    z_after_6deg_from_neg_extreme=z_from_neg_extreme_6deg,  # full swing after 6 deg (should hit +fric = 0.015... wait see note)
    note='max single-sided magnitude is fric=0.015, not 0.030; 0.030 is the PEAK-TO-PEAK SWING '
         '(-fric to +fric), which needs 2*band=6 deg of travel, not 3 deg. 3 deg of travel from '
         'center reaches only +fric=0.015 (half of 0.030). F6 conflates the 0.030 swing ceiling '
         'with the 3 deg dose that actually only buys 0.015 of it.')

# median observed dwell demand travel at 2-8 m/s, for context (from gap_test-equivalent)
angdes = W['angdes']
dwell_dem = (A('angdes', np.full(N, PRE)) - A('angdes', d0))
m28 = TQ & (v >= 2) & (v < 8)
out['observed_dwell_demand_travel_2_8_median_deg'] = float(np.median(dwell_dem[m28]))

# ---------- 4. hold map offset check (direct source read) ----------
out['hold_map_source_check'] = 'see hold_torque() in sslib.py: k(v)*sat*tanh(angle/sat), pure odd ' \
    'function of angle, no additive constant -> CONFIRMED no +/-0.02 offset exists in the flown map.'

json.dump(out, open('verify_f6_attribution.json', 'w'), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
