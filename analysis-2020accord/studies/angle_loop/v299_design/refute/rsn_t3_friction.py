# -*- coding: utf-8 -*-
"""rsn_t3_friction.py -- T3: friction limit cycles / hunting in hands-off holds and slow tracking, V298 vs V299-A
(V299-B is A above 11.75 m/s and differs below only by cap/clip, which a hold never binds).  Scenarios: hold at
0 / 2 / 6 deg after a 1 deg step; slow drift 1.33 deg/s (r79's dwell drift) for 4 s; members r79F, r79F_hiFs
(Fs 1.6 Fc), ms_free_r79F, b_lo*J_hi; twist residual on.  Reads: sustained cycles (sign changes of theta - plan with
half-cycle peak >= 0.3 deg) in the last 4 s, 1-10 Hz wheel-rate rms, stuck fraction, |err| p95.  MY engine.
ANALYSIS ONLY."""
import json, sys, time, collections
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E
import rsn_common as C

SPEEDS = (3.0, 5.0, 8.0, 12.0, 17.5, 25.0)
MEMBERS = ("r79F", "r79F_hiFs", "ms_free_r79F", "b_lo*J_hi")
SCN = ("h0", "h2", "h6", "drift")


def job(args):
    v, scn = args
    cols = [dict(sys=s, rule=C.SYS[s][0], fork=C.SYS[s][1], member=m, v=v) for s in ("V298", "V299A") for m in MEMBERS]
    B = len(cols); dur = 9.0
    if scn == "drift":
        plan = lambda t: np.full(B, np.clip((t - 2.0) * 1.33, 0, 5.3) + 1.0)  # noqa
        th0 = 1.0
    else:
        a = {"h0": 0.0, "h2": 2.0, "h6": 6.0}[scn]
        plan = lambda t, a=a: np.full(B, a + (1.0 if t >= 1.0 else 0.0))  # noqa
        th0 = a
    R = E.run(cols, dur, plan, th0=th0, seed=55, rec=("th", "om", "T", "I", "frz"))
    out = []
    i0 = 5000
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float); om = R["om"][:, j].astype(float)
        pl = np.repeat(R["plan"][:, j], 10)[:len(th)].astype(float)
        e = pl[i0:] - th[i0:]
        out.append(dict(sys=c["sys"], member=c["member"], v=v, scn=scn, cyc=C.limit_cycle(e, 0.3),
                        r110=float(np.sqrt(np.mean(C.bp(om, 1.0, 10.0)[i0:] ** 2))), stuck=float(np.mean(om[i0:] == 0.0)),
                        e95=float(np.percentile(np.abs(e), 95)), Tpp=float(np.ptp(R["T"][i0:, j]))))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(16) as p:
        res = sum(p.map(job, [(v, s) for v in SPEEDS for s in SCN]), [])
    (E.OUT / "t3_friction.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(dict)
    for d in res:
        g[(d["v"], d["scn"], d["member"])][d["sys"]] = d
    print("| v | scn | member | cycles>=0.3deg V298/V299 | r1-10 Hz deg/s V298/V299 | stuck frac V298/V299 | |e| p95 V298/V299 | T p-p V298/V299 |")
    print("|---|---|---|---|---|---|---|---|")
    for k in sorted(g):
        a, b = g[k]["V298"], g[k]["V299A"]
        flag = " **" if b["cyc"] >= 3 and b["cyc"] > a["cyc"] + 2 else ""
        print(f"| {k[0]} | {k[1]} | {k[2]} | {a['cyc']}/{b['cyc']}{flag} | {a['r110']:.2f}/{b['r110']:.2f} | {a['stuck']:.2f}/{b['stuck']:.2f} | {a['e95']:.2f}/{b['e95']:.2f} | {a['Tpp']:.0f}/{b['Tpp']:.0f} |")
    print(f"wall {time.perf_counter()-T0:.1f} s")
