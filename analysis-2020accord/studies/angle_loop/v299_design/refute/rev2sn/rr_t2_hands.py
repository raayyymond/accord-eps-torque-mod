# -*- coding: utf-8 -*-
"""rr_t2_hands.py -- RE/RC: hands on the NO-OVERRIDE fork (ruling (i)) vs V298, MY engine.  Hold at the speed's curve
angle, a hand ramps on over 0.3 s, holds AGE s, releases over 30 ms.  Hand models: 'pos' = stiff hand (Kh 2000 T/deg,
Bh 30; S2's form) displacing the wheel 30 % toward centre (c) / outward (o) or dragging it to centre (ov); 'frc' = a
constant force 0.29 T/word (BELIEF) toward centre (c) / outward (o).  Words (raw gp-0x4f68): 300..1150 = the band no
freeze covers; 1500/2500 above Honda's 1229.  Reads, per the design's OWN criterion text:
  F3lit  = max |theta - sp_sent| in the 1.5 s after release (> 8 deg at >= 8 m/s fires F3 as written)
  swing  = max excursion PAST the setpoint away from the hand side, 1.5 s after release (the page's 'lurch')
  F5lit  = (sp - theta) toward centre at the episode END, 'c' episodes 300 < word < 1229 (> 4 deg fires F5 as written)
  droop  = |theta - A| 1.5 s after release (the page's metric)
  F7b    = longest run of |wire| > 600 & word <= 1229 & tap >= 40 % rail opposing the hand (> 0.3 s fires)
  tapopp = max / last-0.5 s mean of the opposing lane torque, % of rail; handT = hand force at the end (pos only)
usage: python rr_t2_hands.py  (< 30 s).  ANALYSIS ONLY."""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R

HOLD = {5.0: 30.0, 8.0: 20.0, 10.0: 15.0, 12.5: 10.0, 15.0: 8.0, 25.0: 4.0}
AGES = (1.0, 4.0)
WORDS = (300.0, 550.0, 800.0, 1150.0, 1500.0, 2500.0)
CW = 0.29
TON = 2.0


def job(args):
    v, model = args
    E = R.E
    A = HOLD[v]
    dirs = ("c", "o", "ov") if model == "pos" else ("c", "o")
    cols = [R.col(s, m, v, age_h=a, wd=w, dirn=d) for s in ("V298", "R2") for m in ("r79F", "b_lo*J_hi")
            for a in AGES for w in WORDS for d in dirs]
    B = len(cols)
    age = np.array([c["age_h"] for c in cols]); wd = np.array([c["wd"] for c in cols])
    dn = np.array([{"c": -1.0, "o": 1.0, "ov": -1.0}[c["dirn"]] for c in cols])
    frac = np.array([1.0 if c["dirn"] == "ov" else 0.3 for c in cols])
    toff = TON + 0.3 + age
    dur = float(toff.max() + 2.0)
    thh = A + dn * frac * A
    Kh = np.full(B, 2000.0); Bh = np.full(B, 30.0)

    def ramp_of(t):
        up = np.clip((t - TON) / 0.3, 0, 1)
        down = np.clip(1 - (t - toff) / 0.03, 0, 1)
        return np.where(t < toff, up, down) * (t >= TON)

    def hand(t):
        r = ramp_of(t)
        if not np.any(r > 0):
            return None
        held = (t >= TON) & (t < toff)
        w = dn * wd * r
        if model == "pos":
            return (np.where(held, Kh, 0.0), np.where(held, Bh, 0.0), A + r * (thh - A), w)
        return (np.zeros(B), np.zeros(B), thh, w)

    uext = (lambda t: dn * CW * wd * ramp_of(t)) if model == "frc" else None
    Rr = E.run(cols, dur, lambda t: np.full(B, A), th0=A, hand=hand, uext=uext, seed=91, rec=("th", "om", "T", "w"))
    out = []
    for j, c in enumerate(cols):
        th = Rr["th"][:, j].astype(float); T = Rr["T"][:, j].astype(float); w = Rr["w"][:, j].astype(float)
        ih, ir = int((TON + 0.3) * 1000), int(toff[j] * 1000)
        sp = np.repeat(Rr["sp"][:, j].astype(float), 10)[:len(th)]
        win = slice(ir, ir + 1500)
        f3 = float(np.abs(th[win] - sp[win]).max())
        swing = float(max(((th[win] - sp[win]) * -dn[j]).max(), 0.0))     # past the setpoint, away from the hand side
        f5 = float((sp[ir - 1] - th[ir - 1]) * np.sign(A)) if c["dirn"] == "c" else 0.0
        droop = float(abs(th[ir + 1500] - A))
        opp = (T[ih:ir] * dn[j] > 0)                                       # lane torque (u = -T) against the hand
        fr = np.abs(T[ih:ir]) / 2461.0
        aw = np.abs(w[ih:ir])
        m7b = opp & (fr >= 0.4) & (aw / 1.024 > 600) & (aw <= 1229)
        runs = R.C.runs(m7b, 1)
        f7b = int(max((b - a for a, b in runs), default=0))
        handT = float(np.abs(Kh[j] * (thh[j] - th[ir - 500:ir])).mean()) if model == "pos" else float(CW * wd[j])
        out.append(dict(sys=c["sys"], model=model, v=v, A=A, member=c["member"], age=c["age_h"], wd=c["wd"],
                        dirn=c["dirn"], F3lit=f3, swing=swing, F5lit=f5, droop=droop, f7b_ms=f7b,
                        tapopp=float((fr * opp).max()), tapres=float((fr * opp)[-500:].mean()), handT=handT,
                        dev_rel=float(abs(th[ir - 1] - sp[ir - 1]))))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(12) as p:
        res = sum(p.map(job, [(v, m) for v in HOLD for m in ("pos", "frc")]), [])
    (R.OUT / "rr_t2_hands.json").write_text(json.dumps(res), encoding="utf-8")
    print(f"{len(res)} rows, wall {time.perf_counter() - T0:.1f} s")
