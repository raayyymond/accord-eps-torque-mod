"""Stage 0: can I reconstruct the FF sub-terms inside the 230-frame windows?
(a) torque routes: window-local rebuild vs the extractor's stored hold_ff/move channels.
(b) V282 routes: which hold form (saturating map vs linear spring k(v)/G(v)) leaves the smaller
    residual in F, and is that residual the size of the SteerFriction 0.01 relay (<= 0.01/6.0)?
"""
import numpy as np, json
from rel_lib import *
from sslib import hold_torque

EP, W, P = load()
N = len(EP)
g = np.array([e['group'] for e in EP]); rt = np.array([e['route'] for e in EP])
TQ = np.isin(g, TQG); V2 = g == 'V282'
hold, move, resid = rebuild_v282_ff(W, EP, P)
R = {}

# (a) torque: rebuild vs stored
m = TQ
R['rebuild_vs_stored_torque'] = dict(
    n=int(m.sum()),
    hold_rms_err=float(np.sqrt(np.mean((hold[m] - W['hold_ff'][m]) ** 2))),
    hold_rms=float(np.sqrt(np.mean(W['hold_ff'][m] ** 2))),
    move_rms_err=float(np.sqrt(np.mean((move[m] - W['move'][m]) ** 2))),
    move_rms=float(np.sqrt(np.mean(W['move'][m] ** 2))),
    resid_vs_zrldob_rms=float(np.sqrt(np.mean((resid[m] - (W['z'] + W['rl'] + W['dob'])[m]) ** 2))),
    F_rms=float(np.sqrt(np.mean(W['F'][m] ** 2))))

# (b) V282: hold map vs linear spring
K_BP = [4.0, 8.0, 12.5, 18.5, 28.5]; K_V = [0.30, 1.00, 2.30, 2.77, 3.91]
lin = np.interp(W['v'], K_BP, K_V) * W['angdes'] / np.interp(W['v'], G_BP, G_V)
m = V2
out = {}
for name, h in (('hold_map_level0', hold), ('linear_spring', lin), ('none', np.zeros_like(hold))):
    r = W['F'] - h - move
    out[name] = dict(resid_rms=float(np.sqrt(np.mean(r[m] ** 2))),
                     resid_p95=float(np.percentile(np.abs(r[m]), 95)),
                     corr_resid_angdes=float(np.corrcoef(r[m].ravel(), W['angdes'][m].ravel())[0, 1]))
out['F_rms'] = float(np.sqrt(np.mean(W['F'][m] ** 2)))
out['relay_ceiling_torque'] = 0.01 / 6.0
R['v282_hold_form'] = out

# identity check: cmd == P + I + F ?
for nm, mm in (('torque', TQ), ('V282', V2)):
    e = W['cmd'][mm] - (W['P'] + W['I'] + W['F'])[mm]
    R.setdefault('cmd_identity', {})[nm] = dict(rms=float(np.sqrt(np.mean(e ** 2))),
                                                cmd_rms=float(np.sqrt(np.mean(W['cmd'][mm] ** 2))))
print(json.dumps(R, indent=1))
json.dump(R, open(OUT + '/r0_verify.json', 'w'), indent=1)
