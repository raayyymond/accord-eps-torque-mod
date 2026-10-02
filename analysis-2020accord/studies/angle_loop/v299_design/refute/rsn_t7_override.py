# -*- coding: utf-8 -*-
"""rsn_t7_override.py -- T7: a firm hand override and its release, V298 vs V299-A vs V299-B.  From a hold at the
speed's turn angle, a hand (stiff, Kh 2000 T/deg, Bh 30) drags the wheel to centre while its word ramps to W in 0.3 s,
holds 1.5 s, then releases either SUDDENLY (word and grip to 0 in one tick) or SLOWLY (word and grip fall linearly
over 0.6 s, i.e. the word passes down through 1229 -> 600 -> 500 raw while the hand still guides the wheel).
Reads: time from hand onset to the I freeze / fork O1, lane torque under the hand (% rail), hand force, release
overshoot past the plan, release t90.  W = 1500 / 2500 words.  MY engine.  ANALYSIS ONLY."""
import collections
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E  # noqa: E402
import rsn_common as C  # noqa: E402

HOLD = {5.0: 30.0, 8.0: 20.0, 15.0: 8.0}


def job(v):
    A = HOLD[v]
    cols = [dict(sys=s, rule=C.SYS[s][0], fork=C.SYS[s][1], member=m, v=v, W=W, rel=rel)
            for s in C.SYS for W in (1500.0, 2500.0) for rel in ("sud", "slow") for m in ("r79F", "b_lo*J_hi")]
    B = len(cols)
    W = np.array([c["W"] for c in cols])
    slow = np.array([c["rel"] == "slow" for c in cols])
    ton, thold, toff = 2.0, 2.3, 3.8
    plan = lambda t: np.full(B, A)  # noqa: E731

    def hand(t):
        if t < ton:
            return None
        g = np.clip((t - ton) / 0.3, 0, 1)
        if t >= toff:
            g = np.where(slow, np.clip(1 - (t - toff) / 0.6, 0, 1), 0.0)
        if not np.any(g > 0):
            return None
        return (2000.0 * g, 30.0 * g, np.zeros(B), -W * g)        # drag to centre: word negative (pushes right)

    R = E.run(cols, toff + 3.0, plan, th0=A, hand=hand, seed=31, rec=("th", "om", "T", "I", "frz", "hard"))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        i_on, i_off = int(ton * 1000), int(toff * 1000)
        hd = np.flatnonzero(R["hard"][i_on:, j] > 0)
        o1 = np.flatnonzero(R["o1"][i_on // 10:, j])
        ir = i_off + (600 if c["rel"] == "slow" else 0)
        post = th[ir:ir + 2500]
        hit = np.flatnonzero(post >= A - 0.1 * A)
        out.append(dict(sys=c["sys"], v=v, W=c["W"], rel=c["rel"], member=c["member"],
                        t_frz=float(hd[0]) if len(hd) else np.nan, t_o1=float(o1[0] * 10) if len(o1) else np.nan,
                        tap_hand=float(np.abs(R["T"][i_off - 500:i_off, j]).mean() / E.RAIL_T),
                        ovs_rel=float(post.max() - A), t90_rel=float(hit[0] / 1000) if len(hit) else np.nan,
                        min_after=float(th[i_off:i_off + 3000].min())))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(3) as p:
        res = sum(p.map(job, tuple(HOLD)), [])
    (E.OUT / "t7_override.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["v"], d["W"], d["rel"], d["sys"])].append(d)
    print("| v | W | release | sys | t freeze ms | t O1 ms | lane tap under hand % rail | release overshoot deg max | release t90 s med |")
    print("|---|---|---|---|---|---|---|---|---|")
    for k in sorted(g, key=lambda k: (k[0], k[1], k[2], list(C.SYS).index(k[3]))):
        L = g[k]
        q = lambda f: np.array([x[f] for x in L], float)  # noqa: E731
        print(f"| {k[0]} | {k[1]:.0f} | {k[2]} | {k[3]} | {np.nanmedian(q('t_frz')):.0f} | {np.nanmedian(q('t_o1')):.0f} | "
              f"{100 * np.mean(q('tap_hand')):.0f} | {q('ovs_rel').max():.1f} | {np.nanmedian(q('t90_rel')):.2f} |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
