# -*- coding: utf-8 -*-
"""nl_report.py -- tables from the nl_lens caches (worst value per impl x member x age x speed band, with the speed).
ANALYSIS ONLY.  usage: python nl_report.py > lens_report.txt"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_lens as L  # noqa: E402

BANDS = ((3.0, 3.2, "3.1"), (4.9, 5.1, "5"), (8.0, 10.0, "8-10"), (10.0, 12.51, "10-12.5"), (12.75, 15.0, "12.75-15"),
         (15.25, 19.0, "15.25-19"), (19.25, 22.0, "19.25-22"), (22.25, 30.0, "22.25-30"))
COLS = {m: L.cols_for(m) for m in L.MEMBERS}


def load(scn, mem):
    p = L.OUT / f"lens_{scn}_{mem.replace('*', 'x')}.npz"
    return dict(np.load(p)) if p.exists() else None


def table(scn, key, agg="max", fmt="{:.2f}", members=L.MEMBERS, impls=L.IMPLS, note=""):
    print(f"\n### {scn} : {key} ({agg} over the band; [speed of the worst]) {note}")
    hdr = "| impl | member | age | " + " | ".join(b[2] for b in BANDS) + " |"
    print(hdr)
    print("|" + "---|" * (3 + len(BANDS)))
    for mem in members:
        d = load(scn, mem)
        if d is None or key not in d:
            continue
        cols = COLS[mem]
        for im in impls:
            for age in L.AGES:
                cells = []
                for lo, hi, nm in BANDS:
                    idx = [j for j, c in enumerate(cols) if c["impl"] == im and c["age"] == age and lo <= c["v"] <= hi]
                    x = d[key][idx]
                    vs = [cols[j]["v"] for j in idx]
                    if agg == "max":
                        k = int(np.argmax(x))
                    elif agg == "min":
                        k = int(np.argmin(x))
                    else:
                        cells.append(fmt.format(float(np.sum(x))))
                        continue
                    cells.append(fmt.format(float(x[k])) + f" [{vs[k]:g}]")
                print(f"| {im} | {mem} | {'+h10' if age else '1-10'} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    table("rh", "hold", "min", note="(turn-hold, goal >= 0.90 at >= 8 m/s)")
    table("rh", "slips", "sum", "{:.0f}", note="(hold slips summed over the band's speeds; 3 holds per speed)")
    table("rh", "slips_max_hold", "max", "{:.0f}", note="(max slips in one hold)")
    table("rh", "rev", "max", "{:.0f}", note="(omega reversals > 0.2 deg/s in the last 1.5 s of a hold = hunting)")
    table("rh", "T_hf", "max", note="(T 5-30 Hz rms in holds, counts; bar 2.0)")
    for s in ("s02", "s05", "mic03", "mic05", "mic10"):
        table(s, "gain", "min", "{:.3f}", note="(wire regression gain)")
        table(s, "dj", "sum", "{:.0f}", note="(dwell-then-jump events summed over the band)")
    table("mic03", "stick_pct", "max", "{:.0f}", note="(% of moving-reference frames with the wheel stuck)")
    table("db", "db_lag", "max", note="(creep lag deg)")
    for s in ("ov_firm", "ov_lt400", "ov_lt511", "ov_src", "ov_srcF"):
        table(s, "lurch", "max", note="(overshoot past the setpoint after release, deg)")
    for s in ("ov_co400", "ov_co700"):
        table(s, "droop", "max", note="(droop behind the setpoint after a co-steer release, deg)")
        table(s, "lurch", "max", note="(overshoot past the setpoint after a co-steer release, deg)")
    table("eng", "droop", "max", note="(engage-under-load droop, deg)")
    table("eng", "ovs", "max", note="(engage overshoot, deg)")
    table("tmo", "hold_dev", "max", note="(deviation during the 510 ms timeout hold, deg)")
    table("tmo", "T_after", "max", "{:.0f}", note="(|T| after sentinel + 0.25 s, counts)")
    table("tmos", "hold_dev", "max", note="(fork stops mid-sinusoid: deviation over the 510 ms hold, deg)")
    table("tmos", "T_after", "max", "{:.0f}")
    table("sen", "sen_peakT_after_50ms", "max", "{:.0f}")
    table("dis", "dis_T_after_150ms", "max", "{:.0f}")
    for s in L.SCENS:
        for mem in L.MEMBERS:
            d = load(s, mem)
            if d is not None and float(d["wraps"].max()) > 0:
                print(f"INT32 WRAPS in {s} {mem}: {d['wraps'].max()}")
