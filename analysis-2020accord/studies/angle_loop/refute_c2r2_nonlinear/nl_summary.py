# -*- coding: utf-8 -*-
"""nl_summary.py -- compact worst-case summary of the nl_lens caches at >= 8 m/s (and 3.1/5 for context)."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_lens as L  # noqa
COLS = {m: L.cols_for(m) for m in L.MEMBERS}
def worst(scn, key, agg, lo=8.0, hi=30.0, impls=L.IMPLS, members=L.MEMBERS, ages=L.AGES):
    out = {}
    for im in impls:
        best = None
        for mem in members:
            p = L.OUT / f"lens_{scn}_{mem.replace('*','x')}.npz"
            if not p.exists():
                continue
            d = np.load(p)
            if key not in d.files:
                continue
            for j, c in enumerate(COLS[mem]):
                if c["impl"] != im or c["age"] not in ages or not (lo <= c["v"] <= hi):
                    continue
                x = float(d[key][j])
                if best is None or (x > best[0] if agg == "max" else x < best[0]):
                    best = (x, mem, c["v"], c["age"])
        out[im] = best
    return out
def count(scn, key, lo, hi, thr=0.5, impls=L.IMPLS, members=L.MEMBERS, ages=L.AGES):
    out = {}
    for im in impls:
        tot, where = 0, []
        for mem in members:
            p = L.OUT / f"lens_{scn}_{mem.replace('*','x')}.npz"
            d = np.load(p)
            for j, c in enumerate(COLS[mem]):
                if c["impl"] == im and c["age"] in ages and lo <= c["v"] <= hi and d[key][j] >= thr:
                    tot += int(round(d[key][j])); where.append((mem, c["v"], c["age"], int(round(d[key][j]))))
        out[im] = (tot, where)
    return out
if __name__ == "__main__":
    fmt = lambda b: "n/a" if b is None else f"{b[0]:.3f} ({b[1]}, {b[2]:g} m/s, {'+h10' if b[3] else 'age1-10'})"
    for (scn, key, agg) in (("rh", "hold", "min"), ("rh", "ovs", "max"), ("rh", "rev", "max"), ("rh", "T_hf", "max"),
                            ("s02", "gain", "min"), ("s05", "gain", "min"), ("mic03", "gain", "min"), ("mic05", "gain", "min"),
                            ("mic10", "gain", "min"), ("mic03", "stick_pct", "max"), ("db", "db_lag", "max"),
                            ("ov_firm", "lurch", "max"), ("ov_lt400", "lurch", "max"), ("ov_lt511", "lurch", "max"),
                            ("ov_src", "lurch", "max"), ("ov_srcF", "lurch", "max"), ("ov_co400", "droop", "max"),
                            ("ov_co700", "droop", "max"), ("eng", "droop", "max"), ("tmo", "hold_dev", "max"),
                            ("tmo", "T_after", "max"), ("tmos", "hold_dev", "max"), ("tmos", "T_after", "max"),
                            ("sen", "sen_peakT_after_50ms", "max"), ("dis", "dis_T_after_150ms", "max")):
        for (lo, hi, tag) in ((8.0, 30.0, ">=8"), (3.0, 5.1, "3.1-5")):
            w = worst(scn, key, agg, lo, hi)
            print(f"{scn:9s} {key:22s} {agg} {tag:5s} | " + " | ".join(f"{im}: {fmt(w[im])}" for im in L.IMPLS))
