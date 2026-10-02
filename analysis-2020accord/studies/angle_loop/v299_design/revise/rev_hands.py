# -*- coding: utf-8 -*-
r"""rev_hands.py -- V299 rev 2, the hand rows on the common S2 engine (rev_common.load_s2, bit-exact to s2_time at the
defaults): the light hand (400 words) and the UN-YIELDED MODERATE BAND the fork-safety refuter named (D3): words 550 /
800 / 1150 (wire 537 / 781 / 1123: below Honda's pressed level 1200 wire and the 1229-word firmware freeze), each as a
co-steer hold 30 % toward centre (c) or outward (o), and as a drag to centre (ov); speeds 5 / 8 / 15 / 25 m/s; both
members; seeds 1-2.  Hand model = S2's (stiff position hand Kh 2000, Bh 30; word ramps in 0.3 s, held 2 s, released in
30 ms) -- BELIEF.  Firmware: V298 | rev1 (synthesis) | rev2 (the two-level cap).  Fork: V298 | config A.
Per column: t_O1 after the grab; lane tap max under the hand (% rail) and opposing the hand's force; F7b (|wire| > 600
for > 0.3 s with the tap >= 40 % of rail opposing); mean hand force over the last 0.5 s of the hold (T); residual lane
torque; firmware freeze duty; the release lurch (swing past the setpoint in 2 s) and droop at +1.5 s.
usage: python rev_hands.py   (< 30 s)"""
import collections
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC  # noqa: E402

SPEEDS = (5.0, 8.0, 15.0, 25.0)
CONDS = [(400.0, "c"), (400.0, "o")] + [(w, x) for w in (550.0, 800.0, 1150.0) for x in ("c", "o", "ov")]
CANDS = ("V298", "A-rev1", "A-rev2")


def setup(S2):
    S2.FK["SYNA"] = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
    S2.FW["rev1"] = dict(thr=1229, sgn=0, asym=True)
    S2.CANDS = {"V298": ("V298", "V298", ""), "A-rev1": ("rev1", "SYNA", "")}


def job(v):
    S2 = RC.load_s2()
    setup(S2)
    vw = int(round(v * 230.4))
    S2.FW["rev2"] = dict(thr=1229, sgn=0, asym=True, capv=2880, capval=(4096 if vw <= 1382 else 6144))
    S2.CANDS["A-rev2"] = ("rev2", "SYNA", "")
    cols = [dict(cid=c, member=m, v=v, x=x, W=W, s=s) for (W, x) in CONDS for m in S2.MEMBERS for s in (1, 2) for c in CANDS]
    B = len(cols)
    tg, thold = 3.0, 2.0
    trel = tg + 0.3 + thold
    Ah = np.array([0.5 * S2.A_turn(c["v"]) for c in cols])
    sg = np.sign(Ah)
    dirn = np.array([{"c": -1.0, "o": 1.0, "ov": -1.0}[c["x"]] for c in cols])
    frac = np.array([1.0 if c["x"] == "ov" else 0.3 for c in cols])
    W = np.array([c["W"] for c in cols])
    thh_end = Ah + dirn * frac * Ah
    Kh, Bh = np.full(B, 2000.0), np.full(B, 30.0)

    def hand(t):
        if tg <= t < trel:
            fr = min(1.0, (t - tg) / 0.3)
            return Kh, Bh, Ah + fr * (thh_end - Ah), dirn * sg * W * fr
        if trel <= t < trel + 0.03:
            return np.zeros(B), np.zeros(B), Ah, dirn * sg * W * (1 - (t - trel) / 0.03)
        return None

    R = S2.run(cols, trel + 2.3, lambda t: Ah * np.ones_like(t), Ah.copy(), hand=hand)
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        T = R["T"][:, j].astype(float)
        hf = R["hf"][:, j].astype(float)
        ig, ih, ir = int(tg * 1000), int((tg + 0.3) * 1000), int(trel * 1000)
        o1 = R["o1"][ig // 10:ir // 10, j]
        t_o1 = float(np.flatnonzero(o1)[0] * 10) if o1.any() else None
        lane_on_wheel = -T                                    # the plant receives u = -T (S2 convention)
        opp = (lane_on_wheel[ih:ir] * hf[ih:ir] < 0) & (np.abs(hf[ih:ir]) > 1.0)
        big = np.abs(T[ih:ir]) / 2461.0 >= 0.40
        wire = np.abs(R["word"][ih:ir, j]) / 1.024 > 600.0
        f7b_run = 0
        for a_, b_ in S2._runs(opp & big & wire, 1):
            f7b_run = max(f7b_run, b_ - a_)
        after = (th[ir:ir + 2000] - Ah[j]) * sg[j] * -dirn[j]
        out.append(dict(cid=c["cid"], member=c["member"], v=v, x=c["x"], W=c["W"], s=c["s"], t_o1=t_o1,
                        tap_under=float(np.abs(T[ih:ir]).max() / 2461.0),
                        tap_opp=float((np.abs(T[ih:ir]) * opp).max() / 2461.0),
                        f7b_ms=int(f7b_run), hf=float(np.abs(hf[ir - 500:ir]).mean()),
                        Tres=float(np.abs(T[ir - 500:ir]).mean() / 2461.0),
                        frz=float(R["frz"][ih:ir, j].mean()), lurch=float(max(after.max(), 0.0)),
                        droop=float(abs(th[ir + 1500] - Ah[j]))))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(len(SPEEDS)) as p:
        res = sum(p.map(job, SPEEDS), [])
    (RC.OUT / "rev_hands.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["W"], d["x"], d["v"], d["cid"])].append(d)
    L = ["| word (wire) | hand | v | system | t_O1 ms med | tap under hand max % | tap opposing max % | F7b longest ms (fires > 300) "
         "| hand force T med | residual lane % med | fw freeze duty med | release lurch med [max] deg | droop @1.5 s max |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (W, x) in CONDS:
        for v in SPEEDS:
            for c in CANDS:
                X = g[(W, x, v, c)]
                f = lambda k: np.array([q[k] if q[k] is not None else np.nan for q in X], float)  # noqa: E731
                to1 = f("t_o1")
                L.append(f"| {W:.0f} ({W/1.024:.0f}) | {x} | {v:.0f} | {c} | {('%.0f' % np.nanmedian(to1)) if np.isfinite(to1).any() else 'none'} | "
                         f"{100*f('tap_under').max():.0f} | {100*f('tap_opp').max():.0f} | {int(f('f7b_ms').max())} | {np.median(f('hf')):.0f} | "
                         f"{100*np.median(f('Tres')):.0f} | {np.median(f('frz')):.2f} | {np.median(f('lurch')):.1f} [{f('lurch').max():.1f}] | {f('droop').max():.1f} |")
    L.append(f"wall {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (RC.OUT / "rev_hands.md").write_text(txt, encoding="utf-8")
