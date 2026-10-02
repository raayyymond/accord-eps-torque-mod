# -*- coding: utf-8 -*-
"""rr_t2b_s2hands.py -- S2 cross-check of the outward/centre-ward light co-steer release swing on the NO-OVERRIDE fork
(R2) vs V298, at TWO hold angles: S2's own 0.5*A_turn(v) and the larger curve angles of rr_t2 (5:30 8:20 10:15 12.5:10
15:8 25:4 deg), hold ages 1 / 2 / 4 s, words 550 / 1150.  Swing = max excursion past the setpoint away from the hand side
in the 1.5 s after release.  usage: python rr_t2b_s2hands.py (< 30 s).  ANALYSIS ONLY."""
import json, sys, time, collections
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R
HOLD = {5.0: 30.0, 8.0: 20.0, 10.0: 15.0, 12.5: 10.0, 15.0: 8.0, 25.0: 4.0}


def job(v):
    S2 = R.load_s2()
    S2.CIDS = ("V298", "R2")
    cols = [dict(cid=c, member=m, v=v, x=d, s=1, W=w, age=a, ang=an) for c in S2.CIDS for m in S2.MEMBERS for d in ("c", "o")
            for w in (550.0, 1150.0) for a in (1.0, 2.0, 4.0) for an in ("s2", "big")]
    B = len(cols)
    Ah = np.array([0.5 * S2.A_turn(v) if c["ang"] == "s2" else HOLD[v] for c in cols])
    dn = np.array([-1.0 if c["x"] == "c" else 1.0 for c in cols]); W = np.array([c["W"] for c in cols])
    age = np.array([c["age"] for c in cols]); tg = 2.0; trel = tg + 0.3 + age
    thh = Ah + dn * 0.3 * Ah

    def hand(t):
        on = (t >= tg) & (t < trel); rel = (t >= trel) & (t < trel + 0.03)
        if not (on.any() or rel.any()):
            return None
        fr = np.clip((t - tg) / 0.3, 0, 1)
        w = np.where(on, dn * W * fr, np.where(rel, dn * W * (1 - (t - trel) / 0.03), 0.0))
        return np.where(on, 2000.0, 0.0), np.where(on, 30.0, 0.0), Ah + fr * (thh - Ah), w
    Rr = S2.run(cols, float(trel.max() + 2.0), lambda t: Ah * np.ones_like(t), Ah.copy(), hand=hand)
    out = []
    for j, c in enumerate(cols):
        th = Rr["th"][:, j].astype(float); ir = int(trel[j] * 1000)
        sp = np.repeat(Rr["sp"][:, j].astype(float), 10)[:len(th)]
        out.append(dict(sys=c["cid"], member=c["member"], v=v, x=c["x"], W=c["W"], age=c["age"], ang=c["ang"], A=float(Ah[j]),
                        swing=float(max(((th[ir:ir + 1500] - sp[ir:ir + 1500]) * -dn[j]).max(), 0.0))))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(6) as p:
        res = sum(p.map(job, list(HOLD)), [])
    (R.OUT / "rr_t2b_s2hands.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["x"], d["v"], d["ang"], d["member"], d["sys"])].append(d)
    print("| dir | v | hold | member | V298 swing max by age 1/2/4 | R2 swing max by age 1/2/4 |")
    print("|---|---|---|---|---|---|")
    for k in sorted({k[:4] for k in g}):
        cells = []
        for s in ("V298", "R2"):
            X = g[k + (s,)]
            cells.append(" / ".join(f"{max(d['swing'] for d in X if d['age'] == a):.1f}" for a in (1.0, 2.0, 4.0)) + f" (A {X[0]['A']:.1f})")
        print(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | " + " | ".join(cells) + " |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
