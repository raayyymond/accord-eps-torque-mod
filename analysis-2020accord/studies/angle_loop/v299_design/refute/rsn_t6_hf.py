# -*- coding: utf-8 -*-
"""rsn_t6_hf.py -- T6: 5-30 Hz content of the LANE TORQUE (the excitation the 13-17 / 18-22 Hz plant lines see) in
hands-off turn-ins + holds, V298 vs V299-A vs V299-B, MY engine (the r71b family has no 13-22 Hz mode, so the wheel
cannot ring here; the torque spectrum is the honest read).  Also a 15-s lane-keeping hold with the twist residual on
(the r79 'settled hands-off' regime).  ANALYSIS ONLY."""
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

BANDS = ((5.0, 10.0), (13.0, 17.0), (18.0, 22.0))


def job(args):
    v, scn, sd = args
    cols = [dict(sys=s, rule=C.SYS[s][0], fork=C.SYS[s][1], member=m, v=v) for s in C.SYS for m in ("r79F", "b_lo*J_hi")]
    B = len(cols)
    if scn == "ti":
        A = 60.0 if v <= 10 else 20.0
        Rt = E.plan_rate(v)
        t0 = 0.5
        tu = t0 + A / Rt + 2.5
        plan = lambda t: np.full(B, np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A))  # noqa: E731
        dur = tu + A / Rt + 1.5
    else:                                                       # lane keeping: 0.3 deg x 0.2 Hz + 0.15 deg x 0.7 Hz
        plan = lambda t: np.full(B, 2.0 + 0.3 * np.sin(2 * np.pi * 0.2 * t) + 0.15 * np.sin(2 * np.pi * 0.7 * t))  # noqa
        dur = 15.0
    R = E.run(cols, dur, plan, th0=0.0 if scn == "ti" else 2.0, seed=900 + sd, rec=("th", "om", "T", "frz"))
    out = []
    for j, c in enumerate(cols):
        T = R["T"][500:, j].astype(float)
        om = R["om"][500:, j].astype(float)
        d = dict(sys=c["sys"], member=c["member"], v=v, scn=scn, sd=sd)
        for lo, hi in BANDS:
            d[f"T{int(lo)}"] = float(np.sqrt(np.mean(C.bp(T, lo, hi) ** 2)))
            d[f"w{int(lo)}"] = float(np.sqrt(np.mean(C.bp(om, lo, hi) ** 2)))
        d["frz_tog"] = int(C.toggles(R["frz"][500:, j] > 0))
        out.append(d)
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    jobs = [(v, s, sd) for v in (3.0, 5.0, 8.0, 10.0, 15.0, 25.0) for s in ("ti", "lk") for sd in (1, 2)]
    with Pool(16) as p:
        res = sum(p.map(job, jobs), [])
    (E.OUT / "t6_hf.json").write_text(json.dumps(res), encoding="utf-8")
    print("| scn | v | band | lane-torque rms V298 / V299A / V299B (T) | ratio A/V298, B/V298 | wheel-rate rms V298/A/B deg/s |")
    print("|---|---|---|---|---|---|")
    for scn in ("ti", "lk"):
        for v in (3.0, 5.0, 8.0, 10.0, 15.0, 25.0):
            for lo, _ in BANDS:
                k = f"T{int(lo)}"
                kw = f"w{int(lo)}"
                m = {s: np.mean([d[k] for d in res if d["sys"] == s and d["v"] == v and d["scn"] == scn]) for s in C.SYS}
                mw = {s: np.mean([d[kw] for d in res if d["sys"] == s and d["v"] == v and d["scn"] == scn]) for s in C.SYS}
                print(f"| {scn} | {v} | {int(lo)} Hz | {m['V298']:.2f} / {m['V299A']:.2f} / {m['V299B']:.2f} | "
                      f"{m['V299A'] / max(m['V298'], 1e-9):.2f}, {m['V299B'] / max(m['V298'], 1e-9):.2f} | "
                      f"{mw['V298']:.2f}/{mw['V299A']:.2f}/{mw['V299B']:.2f} |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
