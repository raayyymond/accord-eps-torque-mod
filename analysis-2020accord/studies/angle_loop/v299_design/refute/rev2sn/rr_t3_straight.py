# -*- coding: utf-8 -*-
"""rr_t3_straight.py -- F3's straight clause ("a swing > 5 deg past the setpoint on a straight") under the NO-OVERRIDE
fork: lane keeping on a straight (plan 0), a light hand nudges the wheel to X deg (stiff 'pos' hand, or a constant
force 'frc' = 0.29 T/word) for AGE s, then releases.  With no override the setpoint stays at 0 (clip permitting) and the
I winds AGAINST the hand to the asymmetric bound B = 1250 S (sign(theta) != sign(E')); release then swings past centre.
Speeds 8 / 15 / 25 m/s, X 1/2/4/8 deg, words 300/550/800/1150 (no freeze), ages 1/2/4 s, members r79F, b_lo*J_hi;
V298 vs R2.  MY engine.  usage: python rr_t3_straight.py (< 30 s).  ANALYSIS ONLY."""
import json, sys, time, collections
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R

AGES = (1.0, 2.0, 4.0)
TON = 1.5


def job(args):
    v, model = args
    E = R.E
    if model == "pos":
        par = [(X, w) for X in (1.0, 2.0, 4.0, 8.0) for w in (300.0, 550.0, 800.0, 1150.0)]
    else:
        par = [(0.0, w) for w in (300.0, 550.0, 800.0, 1150.0)]
    cols = [R.col(s, m, v, age_h=a, X=X, wd=w) for s in ("V298", "R2") for m in ("r79F", "b_lo*J_hi") for a in AGES
            for X, w in par]
    B = len(cols)
    age = np.array([c["age_h"] for c in cols]); X = np.array([c["X"] for c in cols]); wd = np.array([c["wd"] for c in cols])
    toff = TON + 0.3 + age

    def rmp(t):
        return np.where(t < toff, np.clip((t - TON) / 0.3, 0, 1), np.clip(1 - (t - toff) / 0.03, 0, 1)) * (t >= TON)

    def hand(t):
        r = rmp(t)
        if not np.any(r > 0):
            return None
        held = (t >= TON) & (t < toff)
        if model == "pos":
            return (np.where(held, 2000.0, 0.0), np.where(held, 30.0, 0.0), r * X, wd * r)
        return (np.zeros(B), np.zeros(B), X, wd * r)
    uext = (lambda t: 0.29 * wd * rmp(t)) if model == "frc" else None
    Rr = E.run(cols, float(toff.max() + 2.5), lambda t: np.zeros(B), th0=0.0, hand=hand, uext=uext, seed=55,
               rec=("th", "T", "I"))
    out = []
    for j, c in enumerate(cols):
        th = Rr["th"][:, j].astype(float); ir = int(toff[j] * 1000)
        sp = np.repeat(Rr["sp"][:, j].astype(float), 10)[:len(th)]
        held_at = float(th[ir - 1])
        sgn = np.sign(held_at) if held_at != 0 else 1.0
        swing = float(max(-(th[ir:ir + 1500] * sgn).min(), 0.0))            # past centre, the far side
        out.append(dict(sys=c["sys"], v=v, model=model, member=c["member"], age=c["age_h"], X=c["X"], wd=c["wd"],
                        held=held_at, sp_rel=float(sp[ir - 1]), swing=swing, I_rel=float(Rr["I"][ir - 1, j])))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(6) as p:
        res = sum(p.map(job, [(v, m) for v in (8.0, 15.0, 25.0) for m in ("pos", "frc")]), [])
    (R.OUT / "rr_t3_straight.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["model"], d["v"], d["X"], d["wd"], d["sys"], d["member"])].append(d)
    print("| hand | v | X deg | word | member | V298 swing past centre by age 1/2/4 (held deg; I at release S) | R2 same |")
    print("|---|---|---|---|---|---|---|")
    for k in sorted({k[:4] + (k[5],) for k in g}):
        cells = []
        for s in ("V298", "R2"):
            Xs = sorted(g[k[:4] + (s, k[4])], key=lambda d: d["age"])
            cells.append(" / ".join(f"{d['swing']:.1f}" for d in Xs) + f" (held {Xs[-1]['held']:.1f}; I {Xs[-1]['I_rel']:.0f})")
        print(f"| {k[0]} | {k[1]} | {k[2]} | {int(k[3])} | {k[4]} | " + " | ".join(cells) + " |")
    for s in ("V298", "R2"):
        Y = [d for d in res if d["sys"] == s]
        print(f"{s}: F3 straight clause (swing > 5 past centre) {sum(d['swing'] > 5 for d in Y)}/{len(Y)}; > 3: {sum(d['swing'] > 3 for d in Y)}; "
              f"max {max(d['swing'] for d in Y):.1f}; age<=2 s max {max(d['swing'] for d in Y if d['age'] <= 2):.1f}")
    print(f"wall {time.perf_counter() - T0:.1f} s")
