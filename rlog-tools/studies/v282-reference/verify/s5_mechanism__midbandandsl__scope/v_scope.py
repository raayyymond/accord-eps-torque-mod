"""SCOPE re-test of finding s5_mechanism/mid-band-and-slow-weave-not-explained-by-dynamics.

The finding tested sim vs meas at 0.15-0.30 / 0.30-0.60 / 0.60-1.20 Hz, >=15 m/s only, using la_act as the
sole achieved-signal definition, and concluded the sim (dynamics-only) cannot explain the T64B/T4 > T64
over-delivery ranking there, so it "explains note 2" (the operator's 5-10 s weave).

Scope questions:
 (A) A literal 5-10 s weave is 0.10-0.20 Hz, mostly BELOW the lowest band the closed-loop validation tested
     (0.15-0.30 Hz). Re-test the sim-vs-meas ranking failure AT the literal weave band.
 (B) The measured side used la_act only. Recompute the measured ranking with la_yaw (independent,
     carState yaw rate x v) to check the ranking premise isn't an achieved-signal-definition artifact,
     given T64/T64B/T5/T4 run three DIFFERENT fork commits (84766cdc, e44b6cd3, 08a5a706) whose
     actualLateralAccel definition could differ.
 (C) Was the >=15 m/s-only scope actually where the weave lives? Check band power vs speed stratum to see
     if restricting to highway misses part of it (note 2 is asserted "highway" in the parent README without
     a speed-resolved check).

Uses the SAME nominal sim (s5_mechanism/_sim_nominal_<route>.npz, PLANT_NOMINAL) already computed and
cached by s5_05_closedloop_validate.py -- does not re-run the simulator.
"""
import json
import sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V  # noqa: E402

S5DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'
GROUPS = {
    'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
    'T64B': ['0000006e--6ca3e014fd'],
    'T5': ['00000076--d0b7ea7e4d'],
    'T4': ['00000075--6c8687d5bd'],
}
STRATA = [(3.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]

OUT = {}

# ---------- (A) + (B): band_H at the literal weave band and at the tested band, la_act AND la_yaw, meas AND sim ----
BANDS = {
    'weave_010_020': (0.10, 0.20),   # literal 5-10s period
    'weave_007_015': (0.07, 0.15),   # 6.7-14.3s period, a looser reading of "5-10 s"
    'tested_015_030': (0.15, 0.30),
    'tested_030_060': (0.30, 0.60),
}

for g, routes in GROUPS.items():
    OUT[g] = {}
    for rk in routes:
        S = V.load(rk)
        sim = np.load(S5DIR + f'_sim_nominal_{rk}.npz')
        mask = V.usable(S, 15.0) & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['model']) & np.isfinite(sim['la'])
        row = {}
        # la_yaw is all-zero in this cache build (cs_yaw not populated) -- use la_pose (livePose yaw x v),
        # the other independent achieved-signal definition v282cmp carries, instead.
        for bn, (f1, f2) in BANDS.items():
            segs_act, segs_pose, segs_sim = [], [], []
            for a, b in V.runs(mask, S['t'], min_s=30):
                x = np.nan_to_num(S['model'][a:b])
                segs_act.append((x, S['la_act'][a:b]))
                segs_pose.append((x, S['la_pose'][a:b]))
                segs_sim.append((x, sim['la'][a:b]))
            hm_act = V.band_H(segs_act, f1, f2)
            hm_pose = V.band_H(segs_pose, f1, f2)
            hm_sim = V.band_H(segs_sim, f1, f2)
            row[bn] = dict(
                meas_la_act=hm_act and round(hm_act['H'], 3), coh_act=hm_act and round(hm_act['coh'], 2),
                meas_la_pose=hm_pose and round(hm_pose['H'], 3), coh_pose=hm_pose and round(hm_pose['coh'], 2),
                sim=hm_sim and round(hm_sim['H'], 3), coh_sim=hm_sim and round(hm_sim['coh'], 2),
                sec=hm_act and round(hm_act['sec'], 1),
            )
        OUT[g][rk] = row
        del S, sim

# ---------- (C): where does the literal weave band's POWER actually live, by speed stratum? ----------
POWER = {}
for g, routes in GROUPS.items():
    POWER[g] = {}
    for rk in routes:
        S = V.load(rk)
        base = V.usable(S, 0.0, 99.0) & np.isfinite(S['sa']) & np.isfinite(S['model'])
        row = {}
        for lo, hi in STRATA:
            m = base & (S['v'] >= lo) & (S['v'] < hi)
            segs = [(np.nan_to_num(S['model'][a:b]), S['la_act'][a:b]) for a, b in V.runs(m, S['t'], min_s=20)]
            r = V.band_H(segs, 0.10, 0.20)
            row[f'{lo:.0f}-{hi:.0f}'] = dict(H=r and round(r['H'], 3), coh=r and round(r['coh'], 2), sec=r and round(r['sec'], 1))
        POWER[g][rk] = row
        del S

OUT['_power_by_speed_weaveband_010_020'] = POWER

json.dump(OUT, open(S5DIR.replace('s5_mechanism', 'verify/s5_mechanism__midbandandsl__scope') + 'v_scope_results.json', 'w'), indent=1)
print(json.dumps(OUT, indent=1))
