# -*- coding: utf-8 -*-
"""rsn_xcheck_s2.py -- second engine: the S2 common scorer (s2_time.run, unchanged) on the turn-ins MY engine flags
(10 and 11.75 m/s, 60 deg; plus S2's own 8 m/s anchor).  Candidates: V298 and the synthesis' SYN-250 (= V299 config B)
and a config-A analogue (D1c fw + G4/lead0/take, cap 120 / clip x1.0).  ANALYSIS ONLY."""
import importlib.util, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("s2_time_x", HERE.parent / "scores" / "S2-time-nonlinear" / "s2_time.py")
S2 = importlib.util.module_from_spec(_s); sys.modules["s2_time_x"] = S2; _s.loader.exec_module(S2)
G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
S2.FK["SYN250"] = dict(cap_v=(2.5, 2.5), clip=(27.2, 24.8, 31.2, 27.2, 8.5, 4.5), **G4)
S2.FK["SYNA"] = dict(**G4)
S2.CANDS.update({"SYN-250": ("D1c", "SYN250", "B"), "SYN-A": ("D1c", "SYNA", "A")})
CIDS = ("V298", "SYN-A", "SYN-250")


def job(args):
    v, A = args
    cols = [dict(cid=c, member=m, v=v, x="ti", s=s) for c in CIDS for m in S2.MEMBERS for s in (1, 2)]
    B = len(cols); Rt = S2.plan_rate(v); t0 = 0.5; ta = t0 + A / Rt; tu = ta + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A)  # noqa
    R = S2.run(cols, tu + 0.3, plan, np.zeros(B))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float); i0, iu = int(t0 * 1000), int(tu * 1000)
        out.append((c["cid"], c["member"], v, A, c["s"], float(th[i0:iu].max() - A), float(R["I"][:iu, j].max())))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(3) as p:
        res = sum(p.map(job, [(8.0, 60.0), (10.0, 60.0), (11.75, 60.0)]), [])
    for cid in CIDS:
        for v in (8.0, 10.0, 11.75):
            o = [r[5] for r in res if r[0] == cid and r[2] == v]
            print(f"S2 engine | {cid:8s} | v {v:5.2f} | 60 deg | overshoot per col {[round(x,1) for x in o]} | median {np.median(o):.1f} | F4 (>6) {sum(x>6 for x in o)}/{len(o)}")
    print(f"wall {time.perf_counter()-T0:.1f} s")
