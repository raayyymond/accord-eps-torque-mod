# -*- coding: utf-8 -*-
"""rsn_t2_lighthand.py -- T2: light hands of increasing AGE (hold duration) in the band the V299 design leaves
unprotected (|word| 300-614: below the 1229 freeze AND below the fork's 600-raw G4 debounce), plus one G4-band level.
Two hand models: 'pos' = S2's stiff hand (Kh 2000 T/deg, Bh 30) displacing the wheel 30 % of the hold angle toward
centre (c) or outward (o); 'frc' = a constant hand FORCE c*word with c = 0.29 T/word (S2's OV: 1500 words ~ 435 T;
BELIEF) toward centre / outward.  Hold at the speed's typical turn angle, hand on at 2 s for AGE s, release; read the
1.5 s after release: max |theta - plan| (F3 bar 8 deg at >= 8 m/s), swing past the plan (5 deg), droop at release
(F5: > 4 deg behind toward centre).  MY engine.  ANALYSIS ONLY."""
import json, sys, time, collections
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E
import rsn_common as C

HOLD = {5.0: 30.0, 8.0: 20.0, 15.0: 8.0, 25.0: 4.0}
AGES = (1.0, 2.0, 4.0, 8.0)
WORDS = (400.0, 550.0, 900.0)
CW = 0.29


def job(args):
    v, model = args
    A = HOLD[v]
    cols = [dict(sys=s, rule=C.SYS[s][0], fork=C.SYS[s][1], member="r79F", v=v, age_h=a, wd=w, dirn=d)
            for s in C.SYS for a in AGES for w in WORDS for d in ("c", "o")]
    B = len(cols)
    age = np.array([c["age_h"] for c in cols]); wd = np.array([c["wd"] for c in cols])
    sgn = np.array([-1.0 if c["dirn"] == "c" else 1.0 for c in cols])          # hand direction (+ = left = outward)
    ton = 2.0; toff = ton + age; dur = float(toff.max() + 2.0)
    plan = lambda t: np.full(B, A)  # noqa
    Kh = np.full(B, 2000.0); Bh = np.full(B, 30.0); thh = A * (1 + 0.3 * sgn)

    def hand(t):
        on = (t >= ton) & (t < toff)
        if not on.any():
            return None
        w = np.where(on, sgn * wd, 0.0)
        if model == "pos":
            return (np.where(on, Kh, 0.0), np.where(on, Bh, 0.0), thh, w)
        return None if False else (np.zeros(B), np.zeros(B), thh, w)

    uext = (lambda t: np.where((t >= ton) & (t < toff), sgn * CW * wd, 0.0)) if model == "frc" else None
    R = E.run(cols, dur, plan, th0=A, hand=hand, uext=uext, seed=77, rec=("th", "om", "T", "I", "frz"))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float); i1 = int(toff[j] * 1000); w = slice(i1, i1 + 1500)
        dev = th[w] - A
        pre = th[i1 - 1] - A
        out.append(dict(sys=c["sys"], model=model, v=v, A=A, age=c["age_h"], wd=c["wd"], dirn=c["dirn"],
                        lurch=float(np.abs(dev).max()), swing=float(np.max(dev * -sgn[j])),
                        droop=float(-(pre) if c["dirn"] == "c" else 0.0), I_rel=float(R["I"][i1 - 1, j]),
                        I_pre=float(R["I"][int(ton * 1000) - 1, j]),
                        hand_T_end=float(abs(R["T"][i1 - 1, j]))))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(8) as p:
        res = sum(p.map(job, [(v, m) for v in HOLD for m in ("pos", "frc")]), [])
    (E.OUT / "t2_lighthand.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["model"], d["v"], d["wd"], d["dirn"], d["sys"])].append(d)
    print("| hand | v | word | dir | sys | lurch deg by age 1/2/4/8 s | swing past plan by age | I at release - I before (S) by age |")
    print("|---|---|---|---|---|---|---|---|")
    for k in sorted(g):
        L = sorted(g[k], key=lambda x: x["age"])
        print(f"| {k[0]} | {k[1]} | {k[2]:.0f} | {k[3]} | {k[4]} | " + "/".join(f"{x['lurch']:.1f}" for x in L) + " | " +
              "/".join(f"{x['swing']:.1f}" for x in L) + " | " + "/".join(f"{x['I_rel']-x['I_pre']:.0f}" for x in L) + " |")
    print(f"wall {time.perf_counter()-T0:.1f} s")
