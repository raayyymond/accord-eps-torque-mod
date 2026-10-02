# -*- coding: utf-8 -*-
r"""rev_s2_row.py -- the DRIVE-1 composite scored as rows of the common S2 scorer (its groups TI / LH / OV / C2 unchanged;
engine = rev_common.load_s2, bit-exact to s2_time at the defaults).  ANALYSIS ONLY.
Rows:  V298 (flown) | A-rev1 (synthesis firmware + config A, takeover 0.4 after every release) | A-rev2 (two-level cap,
       same fork) | DRIVE-1 = A-rev2 + the takeover skipped after an O1 episode < 50 ms (the D11 rule).
Column definitions = syn_s2.py's (the synthesis' table), member r79F, median of seeds 1-3; [worst] over both members.
usage: python rev_s2_row.py   (4 groups in 4 processes; each < 30 s)"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC  # noqa: E402


def setup():
    S2 = RC.load_s2()
    G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
    S2.FK["A"] = dict(**G4)
    S2.FK["A5"] = dict(short_n=5.0, **G4)
    S2.FW["rev1"] = dict(thr=1229, sgn=0, asym=True)
    S2.FW["rev2"] = dict(RC.REV2_S2)
    S2.CANDS = {"V298": ("V298", "V298", "flown"), "A-rev1": ("rev1", "A", ""), "A-rev2": ("rev2", "A", ""),
                "DRIVE-1": ("rev2", "A5", "rev2 + config A + no takeover after < 50 ms O1")}
    S2.CIDS = tuple(S2.CANDS)
    return S2


def _job(g):
    S2 = setup()
    t0 = time.perf_counter()
    rows = S2.GROUPS[g]()
    return g, [S2._clean(r) for r in rows], time.perf_counter() - t0


def agg(rows, key, cid, v=None, x=None, member="r79F", seeds=(1, 2, 3), worst=False):
    sel = [r for r in rows if r["cid"] == cid and (v is None or r["v"] == v) and (x is None or r["x"] == x)
           and r.get(key) is not None]
    if worst:
        vals = [r[key] for r in sel if r["s"] in seeds]
        return max(vals) if vals else np.nan
    vals = [r[key] for r in sel if r["member"] == member and r["s"] in seeds]
    return float(np.median(vals)) if vals else np.nan


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(4) as p:
        res = p.map(_job, ["TI", "LH", "OV", "C2"])
    R = {g: rows for g, rows, _ in res}
    walls = {g: round(w, 1) for g, _, w in res}
    (RC.OUT / "rev_s2_row.json").write_text(json.dumps(R), encoding="utf-8")
    TI, LH, OV, C2 = R["TI"], R["LH"], R["OV"], R["C2"]
    L = ["| cand | t90 s 3/8 | w pk 3/8 | ovs [worst] | tap pk % [worst] | frz tog/s 3/8 | I kept 3/8 | hand-lost 3 | stall-surge 3/8 | O1 eps 3/8 | r4-8 3/8 | r1.6-3 3/8 | unwind under deg 3 [worst] | LH worst lurch | LH o5 median | OV t_O1 ms 5/15 | OV tap under hand % 5 | OV hand T 5 | OV release ovs worst | C2 slow e_rms 15/25 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in ("V298", "A-rev1", "A-rev2", "DRIVE-1"):
        a = lambda k, v, **kw: agg(TI, k, c, v, **kw)  # noqa: E731
        ss = [sum(int(r["ss"]) for r in TI if r["cid"] == c and r["member"] == "r79F" and r["s"] == 1 and r["v"] == v) for v in (3.0, 8.0)]
        o1 = [sum(int(r["o1_eps"]) for r in TI if r["cid"] == c and r["member"] == "r79F" and r["s"] == 1 and r["v"] == v) for v in (3.0, 8.0)]
        lh_w = max(r["lurch"] for r in LH if r["cid"] == c)
        L.append(f"| {c} | {a('t90',3.0):.2f}/{a('t90',8.0):.2f} | {a('wpk',3.0):.0f}/{a('wpk',8.0):.0f} | "
                 f"{max(a('ovs',3.0),a('ovs',8.0)):.1f} [{agg(TI,'ovs',c,worst=True):.1f}] | "
                 f"{100*max(a('tap_pk',3.0),a('tap_pk',8.0)):.0f} [{100*agg(TI,'tap_pk',c,worst=True):.0f}] | "
                 f"{a('hand_tog_s',3.0):.1f}/{a('hand_tog_s',8.0):.1f} | {a('kept',3.0):.2f}/{a('kept',8.0):.2f} | {a('hand_lost',3.0):.2f} | "
                 f"{ss[0]}/{ss[1]} | {o1[0]}/{o1[1]} | {a('r48',3.0):.1f}/{a('r48',8.0):.1f} | {a('r163',3.0):.1f}/{a('r163',8.0):.1f} | "
                 f"{a('under',3.0):.1f} [{agg(TI,'under',c,worst=True):.1f}] | {lh_w:.1f} | {agg(LH,'lurch',c,5.0,'o'):.1f} | "
                 f"{agg(OV,'t_o1_ms',c,5.0):.0f}/{agg(OV,'t_o1_ms',c,15.0):.0f} | {100*agg(OV,'ov_tap',c,5.0):.0f} | {agg(OV,'hf_hold',c,5.0):.0f} | "
                 f"{agg(OV,'rel_ovs',c,worst=True):.1f} | {agg(C2,'erms',c,15.0,'slow'):.2f}/{agg(C2,'erms',c,25.0,'slow'):.2f} |")
    L.append(f"\nwalls {walls}; total {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (RC.OUT / "rev_s2_row.md").write_text(txt, encoding="utf-8")
