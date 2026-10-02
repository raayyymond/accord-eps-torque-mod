# -*- coding: utf-8 -*-
"""rr_t5_vedge.py -- RB at the NEW cap edges: the cave's cap/shift is a pure function of the v-word with NO hysteresis
(1382 -> 4096 | 6144; 2880 -> 6144 | no cap, shl 4 | shl 6).  A curve hold at v = 6.0 / 12.5 m/s with the v-word
jittering +-2 counts at 100 Hz (BELIEF on the word's noise) vs the word fixed at each side; also a slow speed ramp
through each edge mid-curve (5.5 -> 6.5 and 12.0 -> 13.0 m/s and back).  Reads: wheel 1-10 Hz rate rms, freeze toggles/s,
|I| range, steady error.  The lane's vw is overwritten per 10 ms (Lane.G / sh / capon / capval recomputed); the plant is
held at the nominal speed's parameters.  MY engine.  ANALYSIS ONLY.  usage: python rr_t5_vedge.py (< 30 s)"""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R
E = R.E


class VLane(E.Lane):
    def set_vw(self, vw):
        self.vw = np.asarray(vw, np.int64)
        self.G = E.G_walk(self.vw)
        self.sh = np.where((self.vw & 0xFFFF) > 2880, 6, 4)
        self.capon = (self.vw & 0xFFFF) <= self.capv
        self.capval = np.where(self.is2, np.where((self.vw & 0xFFFF) <= 1382, 4096, 6144), self.capval0)


def job(args):
    vc, mode = args
    vw0 = R.vword(vc)
    members = ("r79F", "b_lo*J_hi", "ms_free_r79F")
    alats = (1.5, 2.5)
    cols = [R.col(s, m, vc, al=a) for s in ("V298", "R2") for m in members for a in alats]
    B = len(cols)
    A = np.array([float(E.steer_from_curv(c["al"] / vc ** 2, vc)) for c in cols])
    is2 = np.array([c["sys"] == "R2" for c in cols])
    orig = E.Lane
    rng = np.random.default_rng(17)

    def mk(rules, vw, variants=None):
        L = VLane(rules, vw, variants)
        L.is2 = is2; L.capval0 = L.capval.copy()
        holder["L"] = L
        return L
    holder = {}
    E.Lane = mk
    try:
        T = 14.0
        state = {"n": 0}
        old_tick = VLane.tick

        def tick(self, *a, **k):
            n = state["n"]; state["n"] += 1
            if n % 10 == 0:
                t = n / 1000.0
                if mode == "jit":
                    w = vw0 + rng.integers(-2, 3, B)
                elif mode == "lo":
                    w = np.full(B, vw0 - 3)
                elif mode == "hi":
                    w = np.full(B, vw0 + 3)
                else:   # ramp: -0.5 m/s -> +0.5 -> -0.5 over the run (triangle), 1 m/s per 5 s
                    dv = 0.5 - abs(((t - 2.0) % 10.0) / 5.0 - 1.0)
                    w = np.full(B, R.vword(vc + dv))
                self.set_vw(w)
            return old_tick(self, *a, **k)
        VLane.tick = tick
        Rr = E.run(cols, T, lambda t: A, th0=A, seed=3, rec=("th", "om", "frz", "I"))
        VLane.tick = old_tick
    finally:
        E.Lane = orig
    from rsn_common import bp
    out = []
    for j, c in enumerate(cols):
        om = Rr["om"][:, j].astype(float); fz = Rr["frz"][4000:, j] > 0
        out.append(dict(v=vc, mode=mode, sys=c["sys"], member=c["member"], al=c["al"],
                        r110=float(np.sqrt(np.mean(bp(om, 1.0, 10.0)[4000:] ** 2))),
                        tog=float(np.count_nonzero(fz[1:] != fz[:-1]) / ((len(fz)) / 1000)),
                        Imin=float(Rr["I"][4000:, j].min()), Imax=float(Rr["I"][4000:, j].max()),
                        err=float(A[j] - Rr["th"][-3000:, j].mean())))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(8) as p:
        res = sum(p.map(job, [(v, m) for v in (6.0, 12.5) for m in ("lo", "hi", "jit", "ramp")]), [])
    (R.OUT / "rr_t5_vedge.json").write_text(json.dumps(res), encoding="utf-8")
    print("| v | member | a_lat | sys | lo: r1-10 / tog/s / err | hi | jitter +-2 | ramp +-0.5 m/s |")
    print("|---|---|---|---|---|---|---|---|")
    for v in (6.0, 12.5):
        for m in ("r79F", "b_lo*J_hi", "ms_free_r79F"):
            for a in (1.5, 2.5):
                for s in ("V298", "R2"):
                    q = {d["mode"]: d for d in res if d["v"] == v and d["member"] == m and d["al"] == a and d["sys"] == s}
                    print(f"| {v} | {m} | {a} | {s} | " + " | ".join(f"{q[k]['r110']:.2f} / {q[k]['tog']:.1f} / {q[k]['err']:+.2f} (I {q[k]['Imin']:.0f}..{q[k]['Imax']:.0f})" for k in ("lo", "hi", "jit", "ramp")) + " |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
