# -*- coding: utf-8 -*-
r"""c3nl_aged.py -- the common scorer's OWN scenario definitions (ST.scenario, imported unchanged) run on my loop at
BOTH sensor ages: native (ages 1-10, = the scorer, bit-exact per c3nl_control K4) and +h10 (the gp-0x6a00 / gp-0x6a56
sample delivered 10 ticks late = ages 11-20, the brief's 'hold ages 1-20').  The scorer runs native only.
Scenarios: ov_lt400 / ov_lt511 / ov_lt1000 / ov_fm2400 (release lurch), th (a_lat 2.0 / 2.5 turn-hold), s10_02 and
s03_02 (in-phase gain, dwell-then-jump), eng (engage droop), cs (co-steer), tmos (510 ms timeout mid-motion).
ANALYSIS ONLY.  usage: python c3nl_aged.py"""
from __future__ import annotations

import importlib.util
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402

AL = HERE.parent
sys.path.insert(0, str(AL / "c3"))
_spec = importlib.util.spec_from_file_location("c3st_aged", AL / "c3" / "c3_score_time.py")
C3ST = importlib.util.module_from_spec(_spec)
sys.modules["c3st_aged"] = C3ST
_spec.loader.exec_module(C3ST)
ST = C3ST.ST

SCNS = ("ov_lt400", "ov_lt511", "ov_lt1000", "ov_fm2400", "th", "s10_02", "s03_02", "eng", "cs", "tmos")
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
IMPLS = ("C3-P", "C3-F")
SPEEDS = tuple(v for v in ST.SPEEDS if v >= 8.0)


def _conv(s):
    tq = (lambda t, th, om, hf, f=s.tq: f(t, th, om)) if s.tq is not None else None
    return S.Scn(dur=s.dur, ref=s.ref, tq=tq, hand=s.hand, uext=s.uext, events=s.events, mode0=s.mode0, th0=s.th0,
                 sp_meas_until=s.sp_meas_until, sp_hold_from=s.sp_hold_from)


def job(args):
    scn, mb, age = args
    cols_st = []
    for v in SPEEDS:
        for a in ((2.0, 2.5) if scn == "th" else (None,)):
            for cid in IMPLS:
                d = dict(cand=ST.CBYID[cid], member=mb, v=v)
                if a is not None:
                    d["alat"] = a
                cols_st.append(d)
    s, meta = ST.scenario(scn, cols_st)
    cols = [dict(impl=c["cand"].id, member=mb, v=c["v"], age=age) for c in cols_st]
    r = S.run(cols, _conv(s))
    r2 = dict(th=r["th"], om=r["om"], T=r["T"].astype(np.int16), plan=r["plan"], wire=r["wire"], wraps=r["wraps"],
              I=r["I"].astype(np.int16), frz_duty=r["frz"].mean(0))
    m = ST.metrics(scn, meta, r2, cols_st)
    keep = {k: np.asarray(x, float).tolist() for k, x in m.items() if k not in ("XY", "holds")}
    return dict(scn=scn, member=mb, age=age, keys=[dict(impl=c["impl"], v=c["v"], alat=cs.get("alat"))
                                                   for c, cs in zip(cols, cols_st)], m=keep)


BANDS = (("8-10", 8, 10), ("10-12.5", 10, 12.5), ("12.5-15", 12.5, 15), ("15-22", 15, 22), (">=22", 22, 99))
SHOW = {"ov_lt400": ("lurch", "max"), "ov_lt511": ("lurch", "max"), "ov_lt1000": ("lurch", "max"),
        "ov_fm2400": ("lurch", "max"), "th": ("hold", "min"), "s10_02": ("gain", "min"), "s03_02": ("gain", "min"),
        "eng": ("droop", "max"), "cs": ("droop", "max"), "tmos": ("exc", "max")}


def main():
    jobs = [(s, mb, age) for s in SCNS for mb in MEMBERS for age in (0, 10)]
    res = []
    with Pool(14) as pool:
        for r in pool.imap_unordered(job, jobs):
            res.append(r)
    (S.OUT / "aged.json").write_text(json.dumps(res))
    L = ["# the common scorer's own scenarios at native age (0) and +h10 (ages 11-20), worst over the 4 members", ""]
    for scn in SCNS:
        key, agg = SHOW[scn]
        for a in ((2.0, 2.5) if scn == "th" else (None,)):
            L.append(f"### {scn}{'' if a is None else f' a_lat {a}'}: {key} ({agg})")
            L.append("")
            L.append("| impl | age | " + " | ".join(b[0] for b in BANDS) + " |")
            L.append("|---|---|" + "---|" * len(BANDS))
            for im in IMPLS:
                for age in (0, 10):
                    cells = []
                    for bn, lo, hi in BANDS:
                        vals = []
                        for r in res:
                            if r["scn"] != scn or r["age"] != age:
                                continue
                            arr = np.array(r["m"][key])
                            for j, k in enumerate(r["keys"]):
                                if k["impl"] == im and lo <= k["v"] < hi and (a is None or k["alat"] == a):
                                    vals.append(arr[j])
                        cells.append(f"{(max(vals) if agg == 'max' else min(vals)):.3f}" if vals else "-")
                    L.append(f"| {im} | {'+h10' if age else 'native'} | " + " | ".join(cells) + " |")
            L.append("")
        if scn in ("s10_02", "s03_02"):
            L.append(f"### {scn}: dwell-then-jump events (sum) / largest snap")
            L.append("")
            L.append("| impl | age | " + " | ".join(b[0] for b in BANDS) + " |")
            L.append("|---|---|" + "---|" * len(BANDS))
            for im in IMPLS:
                for age in (0, 10):
                    cells = []
                    for bn, lo, hi in BANDS:
                        ev, mx = 0.0, 0.0
                        for r in res:
                            if r["scn"] != scn or r["age"] != age:
                                continue
                            for j, k in enumerate(r["keys"]):
                                if k["impl"] == im and lo <= k["v"] < hi:
                                    ev += r["m"]["dj"][j]
                                    mx = max(mx, r["m"]["dj_max"][j])
                        cells.append(f"{ev:.0f} ({mx:.2f})")
                    L.append(f"| {im} | {'+h10' if age else 'native'} | " + " | ".join(cells) + " |")
            L.append("")
    txt = "\n".join(L) + "\n"
    (HERE / "out" / "aged_report.md").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
