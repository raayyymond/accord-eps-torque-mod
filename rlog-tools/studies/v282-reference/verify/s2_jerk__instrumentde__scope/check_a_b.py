import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
import numpy as np

for rk in V.ROUTES:
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        print(rk, "no cache"); continue
    S = V.load(rk)
    u = V.usable(S)
    yaw = np.nan_to_num(S['la_yaw'])
    nz = np.mean(np.abs(yaw[u]) > 1e-6) if u.sum() else float('nan')
    # (a) la_yaw zero fraction, and specifically at LOW SPEED / LARGE ANGLE (where notes 3-5 live)
    lo = u & (S['v'] < 8)
    big_angle = u & (np.abs(np.nan_to_num(S['sa'])) > 20)
    nz_lo = np.mean(np.abs(yaw[lo]) > 1e-6) if lo.sum() else float('nan')
    nz_ba = np.mean(np.abs(yaw[big_angle]) > 1e-6) if big_angle.sum() else float('nan')
    # (b) la_act vs curvature*v^2 identity, overall and at low speed / big angle
    la_act = np.nan_to_num(S['la_act'])
    lp = np.load(f, allow_pickle=True)
    # reconstruct curvature*v^2 directly from cache (cs_des_curv is model, but la_act itself IS the "achieved" -- check
    # against cs_cur if present, else against la_pose divergence in the regimes that matter)
    la_pose = np.nan_to_num(S['la_pose'])
    def corr_slope(mask):
        if mask.sum() < 50: return (np.nan, np.nan, int(mask.sum()))
        x, y = la_act[mask], la_pose[mask]
        if np.std(x) < 1e-9 or np.std(y) < 1e-9: return (np.nan, np.nan, int(mask.sum()))
        c = np.corrcoef(x, y)[0,1]
        sl = np.polyfit(x, y, 1)[0]
        return (float(c), float(sl), int(mask.sum()))
    c_all, sl_all, n_all = corr_slope(u)
    c_lo, sl_lo, n_lo = corr_slope(lo)
    c_ba, sl_ba, n_ba = corr_slope(big_angle)
    print(f"{rk:24s} yaw_nz all={nz:.3f} lo8={nz_lo:.3f}(n={int(lo.sum())}) bigangle={nz_ba:.3f}(n={int(big_angle.sum())})  "
          f"| act-vs-pose corr/slope all=({c_all:.3f},{sl_all:.3f},n={n_all}) lo8=({c_lo:.3f},{sl_lo:.3f},n={n_lo}) bigangle=({c_ba:.3f},{sl_ba:.3f},n={n_ba})")
