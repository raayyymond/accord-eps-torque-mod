"""Extract turn events + phase-aligned ensembles for every route (one route in RAM at a time)."""
import sys, json, pickle
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
rows, rejs, ens = [], {}, []
GRID = np.arange(-3.0, 6.0, 0.01)
for rk in V.ROUTES:
    R = T.prep(rk)
    evs, rej = T.find_turns(R)
    rejs[rk] = dict(rej, kept=len(evs), group=R["group"], lat_delay=R["d"])
    n = len(R["t"])
    for e in evs:
        m = T.metrics(R, e)
        m0 = T.metrics(R, e, lag_s=0.0)
        m.update({k + "_nolag": v for k, v in m0.items() if k.startswith(("aa_", "ap_"))})
        rows.append(m)
        s, P, ds = e["s"], e["P"], int(round(R["d"] * V.FS))
        tr = {}
        for anchor in ("i", "h1", "j"):
            idx = e[anchor] + np.round(GRID * V.FS).astype(int)
            inwin = (idx >= e["w0"]) & (idx < e["w1"])
            idx = np.clip(idx, 0, n - 1 - ds)

            def g(x, sh=0, norm=True):
                y = (s * x[idx + sh] / (P if norm else 1.0)).astype(np.float32)
                y[~inwin] = np.nan
                return y
            tr[anchor] = dict(ad=g(R["ad"]), aa=g(R["aa"], ds), ap=g(R["ap"], ds), sr=g(R["sr"], 0, False),
                              out=g(-R["out"], 0, False), f=g(-R["f"], 0, False), pi=g(-(R["p"] + R["i"]), 0, False))
        ens.append(dict(group=R["group"], rk=rk, v=e["v"], P=P, tr=tr, strata=T.strata(m),
                        dur=dict(build=(e["h0"] - e["i"]) / V.FS, hold=(e["h1"] - e["h0"]) / V.FS, unwind=(e["j"] - e["h1"]) / V.FS)))
    print(rk, R["group"], rejs[rk], flush=True)
    del R
json.dump(dict(rows=rows, rejects=rejs), open(OUT + 'turn_events.json', 'w'), indent=1, default=float)
pickle.dump(dict(grid=GRID, ens=ens), open(OUT + 'ensemble.pkl', 'wb'))
print("events", len(rows))
