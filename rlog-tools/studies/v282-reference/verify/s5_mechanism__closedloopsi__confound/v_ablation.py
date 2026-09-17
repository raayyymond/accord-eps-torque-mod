"""CONFOUND check on finding s5_mechanism/closed-loop-sim-validation-status.

The finding's headline claim -- "it does NOT reproduce band gain differences between revisions" (hold
level, T64 vs T64B; observer/Ki, T64/T5 vs T4) -- rests on comparing the flown-controller sim result on
ONE route against the flown-controller sim result on a DIFFERENT route (different road, day, speed and
demand distribution). s5_05's within-route meas-vs-sim gaps are immune to that confound (sim is always
driven by that SAME route's own logged v/roll/setpoint), but a *cross-route* claim about "the sim gets
the revision effect's SIGN wrong" is not, because both routes bring their own road/demand along with the
controller config.

This script isolates the pure controller-parameter effect from the road/demand confound: for a FIXED
route (fixed road, fixed demand, fixed speed trace), run the closed-loop sim TWICE, swapping ONLY the
controller revision (hold_level True vs False; dob_hz 0.6 vs 0.0 + Ki schedule), with the plant held at
PLANT_NOMINAL throughout. If the within-route counterfactual delta has the same sign as the finding's
claimed "sim predicts X" / "sim underpredicts Y", the claim is not a cross-route confound artifact. If it
flips sign, the cross-route comparison was doing the work, not the controller model.

One route at a time; del the big S dict before moving on. Output: v_ablation_results.json
"""
import json, sys, gc
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import v282cmp as V   # noqa: E402
import s5lib as L     # noqa: E402
import s5ctl as C     # noqa: E402
import s5sim as SIM   # noqa: E402

OUTDIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__closedloopsi__confound/'

# route -> (flown rev, counterfactual rev), group label
CASES = [
    ('0000006e--6ca3e014fd', 'rev64B', 'rev64', 'T64B_road'),   # T64B's OWN road: flown (hold off) vs cf (hold on)
    ('0000006c--68c6e94b17', 'rev64', 'rev64B', 'T64_road_a'),  # T64's OWN road: flown (hold on) vs cf (hold off)
    ('0000006d--05e83bb04f', 'rev64', 'rev64B', 'T64_road_b'),
    # observer/Ki ablation (T4 vs T64/T5): rev4 (dob_hz=0, Ki sched) vs rev64 (dob_hz=0.6, flat Ki)
    ('00000075--6c8687d5bd', 'rev4', 'rev64', 'T4_road'),       # T4's OWN road: flown (no DOB) vs cf (DOB on)
    ('0000006c--68c6e94b17', 'rev64', 'rev4', 'T64_road_a_dob'),  # T64's OWN road: flown (DOB on) vs cf (no DOB, T4 Ki/kp)
]


def band_pair(S, la_a, la_b, mask):
    """b015/b030/b060 |H| model->la for two candidate 'la' series on the SAME frames (>=15 m/s, >=30s runs)."""
    out = {}
    for nm, f1, f2 in (('b015', 0.15, 0.30), ('b030', 0.30, 0.60), ('b060', 0.60, 1.20)):
        sa, sb = [], []
        for a, b in V.runs(mask & (S['v'] >= 15), S['t'], min_s=30):
            x = np.nan_to_num(S['model'][a:b])
            sa.append((x, la_a[a:b])); sb.append((x, la_b[a:b]))
        ha, hb = V.band_H(sa, f1, f2), V.band_H(sb, f1, f2)
        out[nm] = dict(A=ha and round(ha['H'], 3), B=hb and round(hb['H'], 3),
                       coh_A=ha and round(ha['coh'], 2), coh_B=hb and round(hb['coh'], 2),
                       sec=ha and round(ha['sec'], 1))
    return out


def run_case(rk, rev_flown, rev_cf, tag):
    S = V.load(rk)
    D = np.load(V.CACHE / f'{rk}.npz'); stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
    mask = V.usable(S, 3.0) & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['model'])
    P = dict(SIM.PLANT_NOMINAL)

    def mk(rev):
        def _mk(S_, j0, rev=rev):
            ad0 = C.angle_from_la(float(S_['setpoint'][j0]), float(S_['v'][j0]), float(np.nan_to_num(S_['roll'][j0])),
                                  float(np.nan_to_num(S_['sR'][j0], nan=16.84)), float(stiff[j0]))
            return C.Ctl(rev, rate0=float(S_['sr'][j0]), angle_des0=ad0)
        return _mk

    R_flown = SIM.simulate(S, stiff, mk(rev_flown), P, mask)
    R_cf = SIM.simulate(S, stiff, mk(rev_cf), P, mask)
    m2 = mask & np.isfinite(R_flown['th']) & np.isfinite(R_cf['th'])

    bands_sim = band_pair(S, R_flown['la'], R_cf['la'], m2)          # A = flown config, B = counterfactual config
    # also cross-check the MEASURED signal's own band gain on this route, both with la_act and the
    # independent la_yaw definition, so we can compare the sim's flown-config number to a definition-robust
    # measured number for the SAME road (not the finding's cross-route number).
    meas_act = {}
    meas_yaw = {}
    for nm, f1, f2 in (('b015', 0.15, 0.30), ('b030', 0.30, 0.60), ('b060', 0.60, 1.20)):
        segA, segY = [], []
        for a, b in V.runs(m2 & (S['v'] >= 15), S['t'], min_s=30):
            x = np.nan_to_num(S['model'][a:b])
            segA.append((x, S['la_act'][a:b]))
            segY.append((x, np.nan_to_num(S['la_yaw'][a:b])))
        hA, hY = V.band_H(segA, f1, f2), V.band_H(segY, f1, f2)
        meas_act[nm] = hA and round(hA['H'], 3)
        meas_yaw[nm] = hY and round(hY['H'], 3)

    hi = m2 & (S['v'] >= 15)
    n_sec = float(np.sum(hi) / 100.0)
    demand_rms = float(np.sqrt(np.mean(np.nan_to_num(S['model'][hi]) ** 2))) if np.any(hi) else float('nan')
    med_v = float(np.median(S['v'][m2])) if np.any(m2) else float('nan')

    out = dict(route=rk, tag=tag, rev_flown=rev_flown, rev_cf=rev_cf, n_sec_ge15=round(n_sec, 1),
              med_v_engaged=round(med_v, 2), demand_rms_ge15=round(demand_rms, 3),
              sim_bands=bands_sim, meas_la_act_bands=meas_act, meas_la_yaw_bands=meas_yaw)
    del S, R_flown, R_cf, m2, mask
    gc.collect()
    return out


if __name__ == '__main__':
    results = []
    for rk, flown, cf, tag in CASES:
        print('running', tag, rk, flown, 'vs', cf, flush=True)
        r = run_case(rk, flown, cf, tag)
        print(json.dumps(r), flush=True)
        results.append(r)
        gc.collect()
    json.dump(results, open(OUTDIR + 'v_ablation_results.json', 'w'), indent=1)
    print('DONE')
