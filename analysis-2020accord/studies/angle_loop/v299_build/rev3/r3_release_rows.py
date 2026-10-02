# -*- coding: utf-8 -*-
r"""r3_release_rows.py -- V299 rev 3: the hand/release rows that F3/F5 (redefined RELATIVE TO THE RELEASE) are predicted
from, on BOTH engines.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

Systems (the re-refuter's rsn2 definitions): V298 = V298 rule + V298 fork (O1) ; R2 = V299 rev-2 rule (freeze 1229, no
opposing clause, asymmetric bound, two-level cap 4096 <= 1382 / 6144 <= 2880) + fork config A with NO override = THE DRIVE.
Hand = S2's stiff position hand (Kh 2000 T/deg, Bh 30; BELIEF), word ramps on in 0.3 s at t = 2 s, held AGE s, released
in 30 ms.  Directions: c = co-steer 30 % toward centre, o = 30 % outward, ov = drag to centre.  Holds = the realistic
curve angles (5:30, 8:20, 10:15, 12.5:10, 15:8, 25:4 deg) and S2's own 0.5*A_turn(v).
Metrics (the rev-3 criterion text, read on the SENT setpoint sp, as the drive read will):
  F3  = max over the 1.5 s after release of the swing PAST sp AWAY FROM THE HAND SIDE  = (th - sp) * (-dirn), >= 0
  F5  = (sp - th) toward centre (positive = wheel short of sp toward centre) at release + 1.5 s
  gap = |th - sp| at the release instant (what rev 2's literal F3 read; no wheel motion needed)
  F7b = longest run of |wire| > 600 with the lane tap >= 40 % rail opposing the hand's force (an OBSERVATION in rev 3)
  F7  = longest run (ms) of word > 1229 (pressed) with the tap >= 50 % rail opposing (rev 3 F7 fires > 500 ms)
usage: python r3_release_rows.py [S2|RSN]   (< 30 s each)"""
import collections
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
V299D = HERE.parents[1] / "v299_design"
sys.path.insert(0, str(V299D / "refute" / "rev2sn"))
import rsn2 as R  # noqa: E402

KIT = HERE.parents[4]
OUT = KIT / "_scratch" / "v299_REV3"
OUT.mkdir(parents=True, exist_ok=True)
HOLD = {5.0: 30.0, 8.0: 20.0, 10.0: 15.0, 12.5: 10.0, 15.0: 8.0, 25.0: 4.0}
AGES = (1.0, 2.0, 3.0, 4.0)
WORDS = (300.0, 550.0, 800.0, 1150.0, 1500.0, 2500.0)
DIRS = ("c", "o", "ov")
TG = 2.0


def metrics(th, sp, T, word, dn, ir, ih):
    win = slice(ir, ir + 1500)
    f3 = float(max(((th[win] - sp[win]) * -dn).max(), 0.0))
    f5 = float(sp[ir + 1500] - th[ir + 1500])          # A > 0 in every column: + = short toward centre
    gap = float(abs(th[ir - 1] - sp[ir - 1]))
    opp = (T[ih:ir] * dn > 0)                            # S2/RSN convention: plant gets u = -T; hand pushes along dn
    fr = np.abs(T[ih:ir]) / 2461.0
    aw = np.abs(word[ih:ir])
    m = opp & (fr >= 0.4) & (aw / 1.024 > 600)
    m7 = opp & (fr >= 0.5) & (aw > 1229)                 # F7: pressed (raw > 1229 = wire > 1200) and >= 50 % opposing
    best, run, b7, r7 = 0, 0, 0, 0
    for x, y in zip(m, m7):
        run = run + 1 if x else 0
        best = max(best, run)
        r7 = r7 + 1 if y else 0
        b7 = max(b7, r7)
    return f3, f5, gap, best, float((fr * opp).max()), float((fr * opp)[-500:].mean()), b7


def job_s2(v):
    S2 = R.load_s2()
    S2.CIDS = ("V298", "R2")
    cols = [dict(cid=c, member=m, v=v, x=d, s=1, W=w, age=a, ang=an) for c in S2.CIDS for m in S2.MEMBERS for d in DIRS
            for w in WORDS for a in AGES for an in ("s2", "big")]
    B = len(cols)
    Ah = np.array([0.5 * S2.A_turn(v) if c["ang"] == "s2" else HOLD[v] for c in cols])
    dn = np.array([{"c": -1.0, "o": 1.0, "ov": -1.0}[c["x"]] for c in cols])
    frac = np.array([1.0 if c["x"] == "ov" else 0.3 for c in cols])
    W = np.array([c["W"] for c in cols])
    age = np.array([c["age"] for c in cols])
    trel = TG + 0.3 + age
    thh = Ah + dn * frac * Ah

    def hand(t):
        on = (t >= TG) & (t < trel)
        rel = (t >= trel) & (t < trel + 0.03)
        if not (on.any() or rel.any()):
            return None
        fr = np.clip((t - TG) / 0.3, 0, 1)
        w = np.where(on, dn * W * fr, np.where(rel, dn * W * (1 - (t - trel) / 0.03), 0.0))
        return np.where(on, 2000.0, 0.0), np.where(on, 30.0, 0.0), Ah + fr * (thh - Ah), w
    Rr = S2.run(cols, float(trel.max() + 2.0), lambda t: Ah * np.ones_like(t), Ah.copy(), hand=hand)
    out = []
    for j, c in enumerate(cols):
        th = Rr["th"][:, j].astype(float)
        sp = np.repeat(Rr["sp"][:, j].astype(float), 10)[:len(th)]
        T = Rr["T"][:, j].astype(float)
        wd = Rr["word"][:, j].astype(float)
        ir, ih = int(trel[j] * 1000), int((TG + 0.3) * 1000)
        f3, f5, gap, f7b, tmax, tres, f7 = metrics(th, sp, T, wd, dn[j], ir, ih)
        out.append(dict(eng="S2", sys=c["cid"], member=c["member"], v=v, x=c["x"], W=c["W"], age=c["age"], ang=c["ang"],
                        A=float(Ah[j]), F3=f3, F5=f5, gap=gap, f7b=f7b, tapmax=tmax, tapres=tres, f7=f7))
    return out


def job_rsn(v):
    E = R.E
    A = HOLD[v]
    cols = [R.col(s, m, v, age_h=a, wd=w, dirn=d) for s in ("V298", "R2") for m in ("r79F", "b_lo*J_hi")
            for a in AGES for w in WORDS for d in DIRS]
    B = len(cols)
    age = np.array([c["age_h"] for c in cols])
    wd = np.array([c["wd"] for c in cols])
    dn = np.array([{"c": -1.0, "o": 1.0, "ov": -1.0}[c["dirn"]] for c in cols])
    frac = np.array([1.0 if c["dirn"] == "ov" else 0.3 for c in cols])
    toff = TG + 0.3 + age
    thh = A + dn * frac * A
    Kh, Bh = np.full(B, 2000.0), np.full(B, 30.0)

    def hand(t):
        up = np.clip((t - TG) / 0.3, 0, 1)
        down = np.clip(1 - (t - toff) / 0.03, 0, 1)
        r = np.where(t < toff, up, down) * (t >= TG)
        if not np.any(r > 0):
            return None
        held = (t >= TG) & (t < toff)
        return (np.where(held, Kh, 0.0), np.where(held, Bh, 0.0), A + r * (thh - A), dn * wd * r)
    Rr = E.run(cols, float(toff.max() + 2.0), lambda t: np.full(B, A), th0=A, hand=hand, seed=91, rec=("th", "om", "T", "w"))
    out = []
    for j, c in enumerate(cols):
        th = Rr["th"][:, j].astype(float)
        T = Rr["T"][:, j].astype(float)
        w = Rr["w"][:, j].astype(float)
        sp = np.repeat(Rr["sp"][:, j].astype(float), 10)[:len(th)]
        ir, ih = int(toff[j] * 1000), int((TG + 0.3) * 1000)
        f3, f5, gap, f7b, tmax, tres, f7 = metrics(th, sp, T, w, dn[j], ir, ih)
        out.append(dict(eng="RSN", sys=c["sys"], member=c["member"], v=v, x=c["dirn"], W=c["wd"], age=c["age_h"], ang="big",
                        A=A, F3=f3, F5=f5, gap=gap, f7b=f7b, tapmax=tmax, tapres=tres, f7=f7))
    return out


def report(res, eng):
    g = collections.defaultdict(list)
    for d in res:
        g[(d["x"], d["v"], d["ang"], d["member"], d["sys"])].append(d)
    L = [f"### {eng}: F3 (swing past sp away from the hand, 1.5 s) max over words 300-1150 | 1500-2500, by age 1/2/3/4 s; "
         f"F5 (sp - th toward centre @ +1.5 s) max over all words/ages; gap@release max; F7b ms max (words <= 1150)",
         "| dir | v | hold deg | member | V298 F3 light | R2 F3 light | R2 F3 firm (1500/2500) | V298 F5 | R2 F5 | R2 gap | R2 F7b ms |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in sorted({k[:4] for k in g}):
        cell = {}
        for s in ("V298", "R2"):
            X = g[k + (s,)]
            lt = [d for d in X if d["W"] <= 1150]
            fm = [d for d in X if d["W"] > 1150]
            cell[s] = dict(
                F3l=" / ".join(f"{max(d['F3'] for d in lt if d['age'] == a):.1f}" for a in AGES),
                F3f=" / ".join(f"{max(d['F3'] for d in fm if d['age'] == a):.1f}" for a in AGES),
                F5=max(d["F5"] for d in X), gap=max(d["gap"] for d in X), f7b=max(d["f7b"] for d in lt), A=X[0]["A"])
        L.append(f"| {k[0]} | {k[1]} | {cell['R2']['A']:.1f} | {k[3]} | {cell['V298']['F3l']} | {cell['R2']['F3l']} | {cell['R2']['F3f']} | "
                 f"{cell['V298']['F5']:.1f} | {cell['R2']['F5']:.1f} | {cell['R2']['gap']:.1f} | {cell['R2']['f7b']} |")
    return "\n".join(L)


if __name__ == "__main__":
    eng = sys.argv[1] if len(sys.argv) > 1 else "S2"
    T0 = time.perf_counter()
    with Pool(6) as p:
        res = sum(p.map(job_s2 if eng == "S2" else job_rsn, list(HOLD)), [])
    (OUT / f"r3_release_{eng}.json").write_text(json.dumps(res), encoding="utf-8")
    txt = report(res, eng) + f"\nwall {time.perf_counter() - T0:.1f} s"
    (OUT / f"r3_release_{eng}.md").write_text(txt, encoding="utf-8")
    print(txt)
