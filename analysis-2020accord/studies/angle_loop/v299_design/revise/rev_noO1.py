# -*- coding: utf-8 -*-
r"""rev_noO1.py -- the operator's ruling of 2026-10-02 (memory: feedback-no-fork-override-in-the-angle-interface-rely-on-
the-eps-fade): NO fork-side override -- no O1 gate, lead, debounce or takeover ramp; the error clip is the only bound between
setpoint and hand; the EPS fade + the firmware freeze at raw 1229 are the override.  Fork "NoO1" = V298's limiter (cap 120,
clip x1.0) with O1 never firing.  Scored on the rev-2 firmware against V298 and DRIVE (rev 2 + config A).  ANALYSIS ONLY.
  python rev_noO1.py S2     -> the composite row (TI/LH/OV/C2 groups) + the hand rows (words 550..2500, c/o/ov, 5..25 m/s)
  python rev_noO1.py TI     -> the F4 grid (45/60/90 deg, 3..12.5 m/s) on both engines
Each call < 30 s."""
import collections
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else "S2"
NOO1_S2 = dict(inst=1e9, d600=0, hi_n=0, o1lead=0.0, take=0.0)


def s2_setup():
    S2 = RC.load_s2()
    S2.FK["A"] = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
    S2.FK["NoO1"] = dict(NOO1_S2)
    S2.FW["rev2"] = dict(RC.REV2_S2)
    S2.CANDS = {"V298": ("V298", "V298", ""), "DRIVE(A)": ("rev2", "A", ""), "rev2+NoO1": ("rev2", "NoO1", "")}
    S2.CIDS = tuple(S2.CANDS)
    return S2


HSPEEDS = (5.0, 8.0, 15.0, 25.0)


def grp(g):
    S2 = s2_setup()
    if g.startswith("HANDS"):
        global HSPEEDS
        HSPEEDS = {"HANDS_a": (5.0, 8.0), "HANDS_b": (15.0, 25.0)}[g]
    if not g.startswith("HANDS"):
        return g, [S2._clean(r) for r in S2.GROUPS[g]()]
    out = []
    conds = [(w, x) for w in (550.0, 800.0, 1150.0, 1500.0, 2500.0) for x in ("c", "o", "ov")]
    for v in HSPEEDS:
        cols = [dict(cid=c, member=m, v=v, x=x, W=W, s=1) for (W, x) in conds for m in S2.MEMBERS for c in S2.CIDS]
        B = len(cols)
        tg, thold = 3.0, 1.5
        trel = tg + 0.3 + thold
        Ah = np.array([0.5 * S2.A_turn(c["v"]) for c in cols])
        sg = np.sign(Ah)
        dirn = np.array([{"c": -1.0, "o": 1.0, "ov": -1.0}[c["x"]] for c in cols])
        frac = np.array([1.0 if c["x"] == "ov" else 0.3 for c in cols])
        W = np.array([c["W"] for c in cols])
        thh = Ah + dirn * frac * Ah
        Kh, Bh = np.full(B, 2000.0), np.full(B, 30.0)

        def hand(t):
            if tg <= t < trel:
                fr = min(1.0, (t - tg) / 0.3)
                return Kh, Bh, Ah + fr * (thh - Ah), dirn * sg * W * fr
            if trel <= t < trel + 0.03:
                return np.zeros(B), np.zeros(B), Ah, dirn * sg * W * (1 - (t - trel) / 0.03)
            return None
        R = S2.run(cols, trel + 2.2, lambda t: Ah * np.ones_like(t), Ah.copy(), hand=hand)
        for j, c in enumerate(cols):
            th = R["th"][:, j].astype(float)
            T = R["T"][:, j].astype(float)
            hf = R["hf"][:, j].astype(float)
            ih, ir = int((tg + 0.3) * 1000), int(trel * 1000)
            opp = (-T[ih:ir] * hf[ih:ir] < 0) & (np.abs(hf[ih:ir]) > 1.0)
            fr = np.abs(T[ih:ir]) / 2461.0
            wr = np.abs(R["word"][ih:ir, j])
            def longest(m):
                r = S2._runs(m, 1)
                return int(max((b - a for a, b in r), default=0))
            after = (th[ir:ir + 2000] - Ah[j]) * sg[j] * -dirn[j]
            back = np.flatnonzero(np.abs(th[ir:] - Ah[j]) <= 1.0)
            out.append(dict(cid=c["cid"], member=c["member"], v=v, x=c["x"], W=c["W"],
                            tap_opp=float((fr * opp).max()), tap_res=float((fr * opp)[-500:].mean()),
                            f7_ms=longest(opp & (fr >= 0.5) & (wr > 1229)), f7b_ms=longest(opp & (fr >= 0.4) & (wr / 1.024 > 600) & (wr <= 1229)),
                            hf=float(np.abs(hf[ir - 500:ir]).mean()), lurch=float(max(after.max(), 0.0)),
                            t_back=float(back[0] / 1000) if len(back) else None))
    return g, out


def ti_job(a):
    eng, v = a
    amps = (45.0, 60.0, 90.0)
    if eng == "S2":
        S2 = s2_setup()
        amax = float(S2.D2C.vm_amax(np.array([v]))[0])
        cols = [dict(cid=c, member=m, v=v, x="ti", s=s, An=A, A=min(A, 0.9 * amax)) for c in S2.CIDS for A in amps
                for m in S2.MEMBERS for s in (1, 2)]
        B = len(cols); Av = np.array([c["A"] for c in cols]); Rt = S2.plan_rate(v); t0 = 0.5; ta = t0 + Av / Rt; tu = ta + 4.0
        plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa: E731
        R = S2.run(cols, float(tu.max() + Av.max() / Rt + 1.5), plan, np.zeros(B))
        names = [c["cid"] for c in cols]
    else:
        E = RC.load_rsn()
        E.FORKS["NoO1"] = dict(cap=120.0, clipx=1.0, on=1e9, hard=1e9, deb=0, off=500.0, lead=0.0, take=0.0)
        vw = int(round(v * 230.4))
        cap2 = dict(capv=2880, capval=4096 if vw <= 1382 else 6144)
        sysd = {"V298": ("V298", "V298", {}), "DRIVE(A)": ("V299", "A", cap2), "rev2+NoO1": ("V299", "NoO1", cap2)}
        cols = [dict(cid=k, rule=r, fork=f, variant=var, member=m, v=v, An=A, A=min(A, 0.9 * float(E.vm_amax(v))))
                for k, (r, f, var) in sysd.items() for A in amps for m in ("r79F", "b_lo*J_hi")]
        Av = np.array([c["A"] for c in cols]); Rt = E.plan_rate(v); t0 = 0.5; ta = t0 + Av / Rt; tu = ta + 4.0
        plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa: E731
        R = E.run(cols, float(tu.max() + Av.max() / Rt + 1.5), plan, seed=301, rec=("th", "om", "T"))
        names = [c["cid"] for c in cols]
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        i0, i25, iu = int(t0 * 1000), int((ta[j] + 2.5) * 1000), int(tu[j] * 1000)
        o1 = R["o1"][i0 // 10:iu // 10, j]
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * c["A"])
        ovs = float(th[i0:i25].max() - c["A"])
        out.append(dict(eng=eng, sys=names[j], v=v, An=c["An"], member=c["member"], ovs=ovs,
                        F4=bool(v <= 10 and (ovs > 6.0 or (c["An"] >= 45 and ovs > 0.15 * c["A"]))),
                        err=float(c["A"] - th[iu - 1]), t90=float(hit[0] / 1000) if len(hit) else None,
                        o1=int(np.count_nonzero(o1[1:] & ~o1[:-1]) + int(o1[0])), und=float(-th[iu:].min())))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    if MODE == "S2":
        with Pool(6) as p:
            res = dict(p.map(grp, ["TI", "LH", "OV", "C2", "HANDS_a", "HANDS_b"]))
        res["HANDS"] = res.pop("HANDS_a") + res.pop("HANDS_b")
        (RC.OUT / "rev_noO1_S2.json").write_text(json.dumps(res), encoding="utf-8")
        TI, LH, OV, C2 = res["TI"], res["LH"], res["OV"], res["C2"]
        med = lambda rows, k, c, v=None, x=None: float(np.median([r[k] for r in rows if r["cid"] == c and r["member"] == "r79F" and r["s"] in (1, 2, 3) and (v is None or r["v"] == v) and (x is None or r["x"] == x) and r.get(k) is not None]))  # noqa: E731,E501
        L = ["| cand | t90 3/8 | ovs 3/8 | tap pk % 3/8 | stall-surge 3/8 (r79F s1) | O1 3/8 | r4-8 3/8 | unwind @3 | LH worst lurch | LH o5 med | OV tap under hand % 5 | OV hand T 5 | OV release ovs worst | C2 slow 15/25 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in ("V298", "DRIVE(A)", "rev2+NoO1"):
            ss = [sum(int(r["ss"]) for r in TI if r["cid"] == c and r["member"] == "r79F" and r["s"] == 1 and r["v"] == v) for v in (3.0, 8.0)]
            o1 = [sum(int(r["o1_eps"]) for r in TI if r["cid"] == c and r["member"] == "r79F" and r["s"] == 1 and r["v"] == v) for v in (3.0, 8.0)]
            L.append(f"| {c} | {med(TI,'t90',c,3.0):.2f}/{med(TI,'t90',c,8.0):.2f} | {med(TI,'ovs',c,3.0):.1f}/{med(TI,'ovs',c,8.0):.1f} | "
                     f"{100*med(TI,'tap_pk',c,3.0):.0f}/{100*med(TI,'tap_pk',c,8.0):.0f} | {ss[0]}/{ss[1]} | {o1[0]}/{o1[1]} | "
                     f"{med(TI,'r48',c,3.0):.1f}/{med(TI,'r48',c,8.0):.1f} | {med(TI,'under',c,3.0):.1f} | {max(r['lurch'] for r in LH if r['cid'] == c):.1f} | "
                     f"{med(LH,'lurch',c,5.0,'o'):.1f} | {100*med(OV,'ov_tap',c,5.0):.0f} | {med(OV,'hf_hold',c,5.0):.0f} | "
                     f"{max(r['rel_ovs'] for r in OV if r['cid'] == c):.1f} | {med(C2,'erms',c,15.0,'slow'):.2f}/{med(C2,'erms',c,25.0,'slow'):.2f} |")
        L += ["", "| word (raw) | hand | v | system | tap opposing max % | residual opposing % (last 0.5 s) | F7 longest ms (>1229 raw, >=50 %) | F7b longest ms | hand force T | release lurch max | back within 1 deg s |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        g = collections.defaultdict(list)
        for r in res["HANDS"]:
            g[(r["W"], r["x"], r["v"], r["cid"])].append(r)
        for W in (550.0, 800.0, 1150.0, 1500.0, 2500.0):
            for x in ("c", "o", "ov"):
                for v in (5.0, 8.0, 15.0, 25.0):
                    for c in ("V298", "DRIVE(A)", "rev2+NoO1"):
                        X = g[(W, x, v, c)]
                        f = lambda k: np.array([q[k] if q[k] is not None else np.nan for q in X], float)  # noqa: E731
                        L.append(f"| {W:.0f} | {x} | {v:.0f} | {c} | {100*f('tap_opp').max():.0f} | {100*f('tap_res').max():.0f} | {int(f('f7_ms').max())} | "
                                 f"{int(f('f7b_ms').max())} | {np.median(f('hf')):.0f} | {f('lurch').max():.1f} | {np.nanmax(f('t_back')):.2f} |")
    else:
        with Pool(16) as p:
            res = sum(p.map(ti_job, [(e, v) for e in ("S2", "RSN") for v in (3.0, 5.0, 6.5, 8.0, 10.0, 11.75, 12.5)]), [])
        (RC.OUT / "rev_noO1_TI.json").write_text(json.dumps(res), encoding="utf-8")
        L = []
        for eng in ("S2", "RSN"):
            L.append(f"\n#### {eng}: overshoot max [F4 cols] / |hold err| @4 s max / O1 entries per turn max, per amplitude")
            L.append("| system | amp | 3 | 5 | 6.5 | 8 | 10 | 11.75 | 12.5 |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for c in ("V298", "DRIVE(A)", "rev2+NoO1"):
                for A in (45.0, 60.0, 90.0):
                    cells = []
                    for v in (3.0, 5.0, 6.5, 8.0, 10.0, 11.75, 12.5):
                        X = [r for r in res if r["eng"] == eng and r["sys"] == c and r["v"] == v and r["An"] == A]
                        cells.append(f"{max(r['ovs'] for r in X):.1f} [{sum(r['F4'] for r in X)}] / {max(abs(r['err']) for r in X):.1f} / {max(r['o1'] for r in X)}")
                    L.append(f"| {c} | {int(A)} | " + " | ".join(cells) + " |")
    L.append(f"wall {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (RC.OUT / f"rev_noO1_{MODE}.md").write_text(txt, encoding="utf-8")
