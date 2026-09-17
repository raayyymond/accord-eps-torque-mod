"""Recompute act.slag directly from V.load() for the events stored in events_<route>.npz, and diff against the
stored 'act.slag' field, for ONE V282 route and ONE T64 route (RAM discipline: one route loaded at a time)."""
import sys, json, gc
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

FS = V.FS
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk/_out'
THR, VMIN, PRE, POST = 0.4, 3.0, 1.0, 2.5
NPRE, NPOST = int(PRE * FS), int(POST * FS)

def fixed_lag(x, y, i0, i1, lo=-50, hi=80):
    yy = y[i0:i1] - y[i0:i1].mean(); best = (-2, 0, 0)
    for L in range(lo, hi + 1):
        xx = x[i0 - L:i1 - L]; xx = xx - xx.mean()
        den = np.sqrt(np.dot(xx, xx) * np.dot(yy, yy))
        c = np.dot(xx, yy) / den if den > 0 else 0
        if c > best[0]:
            best = (c, L, np.dot(xx, yy) / max(np.dot(xx, xx), 1e-12))
    return best[1] / FS, float(best[2]), float(best[0])

for rk in ("00000064--ce6b0b0ebb", "0000006c--68c6e94b17"):
    D = np.load(f'{OUT}/events_{rk}.npz', allow_pickle=True)
    rows = json.loads(str(D['rows']))
    S = V.load(rk)
    mlp = V.lowpass(np.nan_to_num(S['model']), 2.0)
    alp = V.lowpass(np.nan_to_num(S['la_act']), 3.0)
    ev, j = V.jerk_events(S, jerk_thr=THR, vmin=VMIN, pre=PRE, post=POST, min_sep=2.0)
    # match events by idx k, since jerk_events is deterministic given same inputs
    idx_to_row = {r['k']: r for r in rows}
    diffs = []
    n_checked = 0
    for e in ev:
        k = e['idx']
        r = idx_to_row.get(k)
        if r is None:
            continue
        i0, i1 = k - NPRE, k + NPOST
        if i0 - 100 < 0 or i1 + 100 > len(mlp):
            continue
        L, g, c = fixed_lag(mlp, alp, i0, i1)
        n_checked += 1
        d = L - r['act.slag']
        diffs.append(d)
        if abs(d) > 1e-6:
            print(f"  MISMATCH route={rk} k={k}: mine={L:.4f} stored={r['act.slag']:.4f} (gain mine={g:.4f} stored={r['act.sgain']:.4f})")
    print(f"{rk}: checked {n_checked}/{len(rows)} events, max|diff|={max(abs(x) for x in diffs) if diffs else None}")
    del S, mlp, alp, ev, j, D
    gc.collect()
