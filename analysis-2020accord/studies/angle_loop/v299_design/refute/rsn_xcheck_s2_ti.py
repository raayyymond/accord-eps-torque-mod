# -*- coding: utf-8 -*-
"""rsn_xcheck_s2_ti.py -- second engine (S2, unchanged) for the A-vs-B turn-in question and the X3 via-hard census:
V298, SYN-A (D1c fw + G4/lead0/take, cap 120, clip x1.0) and SYN-250 (= config B) at 3/5/6.5/8 m/s, 60 deg, the S2
manoeuvre, seeds 0-3 x both S2 members.  Via-hard = an O1 entry on a frame whose fork-seen |word|/1.024 > 1200
(re-derived from S2's recorded word at the fork's i-2 wire sample).  ANALYSIS ONLY."""
import importlib.util, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("s2_time_x2", HERE.parent / "scores" / "S2-time-nonlinear" / "s2_time.py")
S2 = importlib.util.module_from_spec(_s); sys.modules["s2_time_x2"] = S2; _s.loader.exec_module(S2)
G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
S2.FK["SYN250"] = dict(cap_v=(2.5, 2.5), clip=(27.2, 24.8, 31.2, 27.2, 8.5, 4.5), **G4)
S2.FK["SYNA"] = dict(**G4)
S2.CANDS.update({"SYN-250": ("D1c", "SYN250", "B"), "SYN-A": ("D1c", "SYNA", "A")})
CIDS = ("V298", "SYN-A", "SYN-250")


def job(v):
    A = 60.0
    cols = [dict(cid=c, member=m, v=v, x="ti", s=s) for c in CIDS for m in S2.MEMBERS for s in (0, 1, 2, 3)]
    B = len(cols); Rt = S2.plan_rate(v); t0 = 0.5; ta = t0 + A / Rt; tu = ta + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A)  # noqa
    R = S2.run(cols, tu + 0.3, plan, np.zeros(B))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float); i0, iu = int(t0 * 1000), int(tu * 1000)
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
        o1 = R["o1"][i0 // 10:iu // 10, j]
        ent = np.flatnonzero(o1[1:] & ~o1[:-1]) + 1 + i0 // 10
        w100 = np.abs(R["word"][4::10, j]) / 1.024                       # the wire samples (n % 10 == 4)
        vh = sum(1 for e in ent if e - 2 >= 0 and w100[e - 2] > 1200.0)
        m = S2.common_metrics(R, j, i0, iu)
        out.append(dict(cid=c["cid"], v=v, t90=hit[0] / 1000 if len(hit) else np.nan, ovs=float(th[i0:iu].max() - A),
                        o1=len(ent), vh=vh, ss=m["ss"], r48=m["r48"], wp99=m["w_p99"]))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(4) as p:
        res = sum(p.map(job, (3.0, 5.0, 6.5, 8.0)), [])
    print("| S2 engine | v | t90 median [range] | overshoot med [max] | O1 entries/turn med | turns with via-hard O1 | stall-surge mean | r4-8 med | word p99 med |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in CIDS:
        for v in (3.0, 5.0, 6.5, 8.0):
            L = [r for r in res if r["cid"] == c and r["v"] == v]; f = lambda q: np.array([x[q] for x in L], float)  # noqa
            print(f"| {c} | {v} | {np.nanmedian(f('t90')):.2f} [{np.nanmin(f('t90')):.2f}-{np.nanmax(f('t90')):.2f}] | {np.median(f('ovs')):.1f} [{f('ovs').max():.1f}] | "
                  f"{np.median(f('o1')):.1f} | {int((f('vh')>0).sum())}/{len(L)} | {f('ss').mean():.1f} | {np.median(f('r48')):.1f} | {np.median(f('wp99')):.0f} |")
    print(f"wall {time.perf_counter()-T0:.1f} s")
