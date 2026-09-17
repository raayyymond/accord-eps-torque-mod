"""Cross-check the MEASURED band-gain numbers the finding leans on against an independent achieved-lateral
signal.  la_yaw (S['la_yaw'], carState yaw rate * v) turns out to be IDENTICALLY ZERO in every route's
cache here (cs_yaw not populated) -- a data-availability finding in its own right, reported separately.
Fall back to la_pose (livePose yaw * v, device frame) as the independent check instead.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V  # noqa: E402

ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']

out = {}
for rk in ROUTES:
    S = V.load(rk)
    mask = V.usable(S, 3.0) & np.isfinite(S['sa']) & np.isfinite(S['model'])
    bands = {}
    for nm, f1, f2 in (('b015', 0.15, 0.30), ('b030', 0.30, 0.60), ('b060', 0.60, 1.20)):
        seg_act, seg_pose = [], []
        for a, b in V.runs(mask & (S['v'] >= 15), S['t'], min_s=30):
            x = np.nan_to_num(S['model'][a:b])
            seg_act.append((x, S['la_act'][a:b]))
            seg_pose.append((x, np.nan_to_num(S['la_pose'][a:b])))
        ha, hp = V.band_H(seg_act, f1, f2), V.band_H(seg_pose, f1, f2)
        bands[nm] = dict(act=ha and round(ha['H'], 3), pose=hp and round(hp['H'], 3),
                         coh_act=ha and round(ha['coh'], 2), coh_pose=hp and round(hp['coh'], 2))
    out[rk] = dict(group=S['meta'].get('group'), la_yaw_finite_std=float(np.nanstd(S['la_yaw'])), bands=bands)
    print(rk, S['meta'].get('group'), json.dumps(bands), flush=True)
    del S

json.dump(out, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__closedloopsi__confound/v_layaw_crosscheck_results.json', 'w'), indent=1)
print('DONE')
