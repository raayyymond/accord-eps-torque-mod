# -*- coding: utf-8 -*-
r"""rev_takeover.py -- the fork-safety refuter's D11: does the 0.4 s takeover ramp (rate AND clip x since/T) self-inflict a
stall-surge after a SHORT O1 episode (a reaction-twist trip on a hands-off turn-in), and what does each fix cost on a REAL
hand release?  Config A fork on the rev-2 firmware.  Variants:
   T0.4      the synthesis' rule (ramp after every O1 release)
   T0.4+s5   no ramp after an O1 episode shorter than 5 frames (< 50 ms); ramp after every longer episode
   T0.2      ramp 0.2 s after every release
(1) RSN engine: hands-off turn-ins 60 / 90 deg at 3 / 5 / 6.5 / 8 m/s, twist alpha-scale ka 1.0 and 1.3, 2 members x
    3 seeds: O1 entries, episodes < 50 ms, stall-surges per turn, stall-surges within 0.5 s after an O1 release, t90, overshoot.
(2) S2 engine: real-hand releases (words 800 / 1150 / 1500, co-steer c / o and drag-to-centre ov, 5 / 8 / 15 m/s):
    release lurch, release overshoot, tap peak in the 0.6 s after release.
usage: python rev_takeover.py   (< 30 s)"""
import collections
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC  # noqa: E402

VAR = {"T0.4": "A", "T0.4+s5": "A_s5", "T0.2": "A_T02"}


def cap2(v):
    return dict(capv=2880, capval=4096 if int(round(v * 230.4)) <= 1382 else 6144)


def rsn_job(args):
    v, ka = args
    E = RC.load_rsn()
    sys.path.insert(0, str(RC.V299 / "refute"))
    import rsn_common as C
    cols = [dict(sys=k, rule="V299", fork=f, variant=cap2(v), member=m, v=v, A=A, ka=ka)
            for k, f in VAR.items() for A in (60.0, 90.0) for m in ("r79F", "b_lo*J_hi")]
    Av = np.array([c["A"] for c in cols])
    Rt = E.plan_rate(v)
    t0 = 0.5
    tu = t0 + Av / Rt + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa: E731
    out = []
    for sd in (1, 2, 3):
        R = E.run(cols, float(tu.max()) + 0.2, plan, seed=4000 + 10 * sd + int(ka * 10), rec=("th", "om"))
        for j, c in enumerate(cols):
            i0, iu = int(t0 * 1000), int(tu[j] * 1000)
            th = R["th"][:, j].astype(float)
            om = R["om"][:, j].astype(float)
            o1 = R["o1"][i0 // 10:iu // 10, j]
            d = np.diff(np.r_[0, o1.astype(np.int8), 0])
            st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
            short = int(np.sum((en - st) < 5))
            # stall-surges within 0.5 s after each O1 release (S2's definition on the 100 Hz wheel rate)
            om100 = om[::10][i0 // 10:iu // 10]
            ss_after = 0
            for e in en:
                seg = om100[max(0, e - 30):min(len(om100), e + 50)]
                if len(seg) > 60:
                    ss_after += C.stall_surge(seg)
            hit = np.flatnonzero(th[i0:iu] >= 0.9 * c["A"])
            out.append(dict(var=c["sys"], v=v, ka=ka, A=c["A"], member=c["member"], sd=sd, o1=len(st), short=short,
                            ss=C.stall_surge(om100), ss_after=ss_after, t90=hit[0] / 1000 if len(hit) else None,
                            ovs=float(th[i0:iu].max() - c["A"]),
                            viahard=int(R["viahard"][i0 // 10:iu // 10, j].sum())))
    return out


def s2_job(v):
    S2 = RC.load_s2()
    vw = int(round(v * 230.4))
    G4 = dict(inst=1200.0, d600=8, o1lead=0.0)
    S2.FK.update({"T0.4": dict(take=0.4, **G4), "T0.4+s5": dict(take=0.4, short_n=5.0, **G4), "T0.2": dict(take=0.2, **G4)})
    S2.FW["rev2"] = dict(thr=1229, sgn=0, asym=True, capv=2880, capval=(4096 if vw <= 1382 else 6144))
    S2.CANDS = {k: ("rev2", k, k) for k in VAR}
    conds = [(w, x) for w in (800.0, 1150.0, 1500.0) for x in ("c", "o", "ov")]
    cols = [dict(cid=c, member=m, v=v, x=x, W=W, s=s) for (W, x) in conds for m in S2.MEMBERS for s in (1, 2) for c in VAR]
    B = len(cols)
    tg, thold = 3.0, 1.5
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

    R = S2.run(cols, trel + 2.2, lambda t: Ah * np.ones_like(t), Ah.copy(), hand=hand)
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        T = np.abs(R["T"][:, j].astype(float))
        ir = int(trel * 1000)
        after = (th[ir:ir + 2000] - Ah[j]) * sg[j] * -dirn[j]
        hit = np.flatnonzero(np.abs(th[ir:] - Ah[j]) <= 0.1 * abs(Ah[j]) + 0.5)
        out.append(dict(var=c["cid"], v=v, W=c["W"], x=c["x"], member=c["member"], s=c["s"],
                        lurch=float(max(after.max(), 0.0)), rel_t=hit[0] / 1000 if len(hit) else None,
                        tap_rel=float(T[ir:ir + 600].max() / 2461.0)))
    return out


def job(a):
    return rsn_job(a[1]) if a[0] == "R" else s2_job(a[1])


if __name__ == "__main__":
    T0 = time.perf_counter()
    jobs = [("R", (v, ka)) for v in (3.0, 5.0, 6.5, 8.0) for ka in (1.0, 1.3)] + [("S", v) for v in (5.0, 8.0, 15.0)]
    with Pool(len(jobs)) as p:
        res = sum(p.map(job, jobs), [])
    (RC.OUT / "rev_takeover.json").write_text(json.dumps(res), encoding="utf-8")
    L = ["### (1) RSN, hands-off turn-ins 60/90 deg, rev-2 fw + config A; per turn means over 2 members x 3 seeds x 2 amps",
         "| takeover | ka | v | O1 entries/turn | O1 eps < 50 ms /turn | via-hard /turn | stall-surges/turn | stall-surges <= 0.5 s after an O1 release (total) | t90 med s | ovs max deg |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    g = collections.defaultdict(list)
    for d in res:
        if "ka" in d:
            g[(d["var"], d["ka"], d["v"])].append(d)
    for k in VAR:
        for ka in (1.0, 1.3):
            for v in (3.0, 5.0, 6.5, 8.0):
                X = g[(k, ka, v)]
                f = lambda q: np.array([x[q] if x[q] is not None else np.nan for x in X], float)  # noqa: E731
                L.append(f"| {k} | {ka} | {v} | {f('o1').mean():.2f} | {f('short').mean():.2f} | {f('viahard').mean():.2f} | "
                         f"{f('ss').mean():.2f} | {int(f('ss_after').sum())} | {np.nanmedian(f('t90')):.2f} | {f('ovs').max():.1f} |")
    L += ["", "### (2) S2, real-hand release (hold 1.5 s), rev-2 fw + config A; max over 2 members x 2 seeds",
          "| takeover | word | hand | v | release lurch med [max] deg | back within 10 % s med | tap peak 0.6 s after release max % |",
          "|---|---|---|---|---|---|---|"]
    g = collections.defaultdict(list)
    for d in res:
        if "W" in d:
            g[(d["var"], d["W"], d["x"], d["v"])].append(d)
    for k in VAR:
        for W in (800.0, 1150.0, 1500.0):
            for x in ("c", "o", "ov"):
                for v in (5.0, 8.0, 15.0):
                    X = g[(k, W, x, v)]
                    f = lambda q: np.array([y[q] if y[q] is not None else np.nan for y in X], float)  # noqa: E731
                    L.append(f"| {k} | {W:.0f} | {x} | {v:.0f} | {np.median(f('lurch')):.1f} [{f('lurch').max():.1f}] | "
                             f"{np.nanmedian(f('rel_t')):.2f} | {100*f('tap_rel').max():.0f} |")
    L.append(f"wall {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (RC.OUT / "rev_takeover.md").write_text(txt, encoding="utf-8")
