#!/usr/bin/env python3
"""Route-37 wall-clock model: unix epoch <-> (segment, offset).

logMonoTime is a single continuous boot clock across all 15 segments (t0_mono runs 53.09 s ->
894.81 s), so ONE offset covers the whole route. `clocks.wallTimeNanos` supplies it.

🛑 Segment 0 straddles the NTP sync. 349 of its 351 clocks samples carry the stale RTC
(1751465120.. = 2025-07-02, a year off) and only the last two carry the synced value. Taking a
median per segment -- the obvious thing -- returns the STALE cluster for segment 0 and a wall_t0
that is wrong by 34,052,791 s. Post-sync samples are selected by clustering, not by trusting any
single segment.

Usage:  python studies/sessions/r37/r37_wallclock.py [HH:MM:SS ...]
"""
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
CACHE = Path(__import__("os").environ.get("R37_CACHE", ROOT / "_scratch/cache/r37"))
SEGS = list(range(15))


def anchors():
    """(t0_mono, duration) per segment, plus every clocks sample on the absolute mono clock."""
    seg = {}
    mono, wall = [], []
    for s in SEGS:
        d = np.load(CACHE / f"r37s{s}.npz")
        t0 = float(d["t0_mono"][0])
        seg[s] = (t0, float(d["t"][-1]), len(d["t"]))
        if len(d["clk_wall"]):
            mono.append(np.asarray(d["clk_mono"], float) + t0)
            wall.append(np.asarray(d["clk_wall"], float))
    mono = np.concatenate(mono)
    wall = np.concatenate(wall)
    return seg, mono, wall


def fit(mono, wall):
    """Constant offset over the post-sync cluster + a drift check. Returns (off, sd, n, slope)."""
    off = wall - mono
    # the synced cluster is the LATE one; split on the largest gap in sorted offsets
    o = np.sort(off)
    gap = int(np.argmax(np.diff(o)))
    thresh = 0.5 * (o[gap] + o[gap + 1]) if o[gap + 1] - o[gap] > 1.0 else -np.inf
    good = off > thresh
    m, w = mono[good], wall[good]
    a = np.polyfit(m, w - m, 1)          # drift ppm check
    return float(np.median(w - m)), float(np.std(w - m, ddof=1)), int(good.sum()), float(a[0])


def main():
    seg, mono, wall = anchors()
    off, sd, n, slope = fit(mono, wall)
    print(f"post-sync clocks samples: {n} / {len(wall)}   offset = {off:.4f} s   "
          f"sd = {sd:.4f} s   drift = {slope * 1e6:+.1f} ppm")
    print(f"route t=0 (seg0 first probe frame) -> "
          f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(seg[0][0] + off))} local  "
          f"/ {time.strftime('%H:%M:%S', time.gmtime(seg[0][0] + off))} UTC")
    print(f"\n{'seg':>3s} {'t0_mono':>9s} {'wall start':>12s} {'wall end':>12s} "
          f"{'dur':>7s} {'n':>6s}")
    for s in SEGS:
        t0, dur, n_ = seg[s]
        print(f"{s:3d} {t0:9.3f} {time.strftime('%H:%M:%S', time.localtime(t0 + off)):>12s} "
              f"{time.strftime('%H:%M:%S', time.localtime(t0 + off + dur)):>12s} "
              f"{dur:7.2f} {n_:6d}")

    for q in sys.argv[1:]:
        hh, mm, ss = (int(x) for x in q.split(":"))
        base = time.localtime(seg[0][0] + off)
        tgt = time.mktime((base.tm_year, base.tm_mon, base.tm_mday, hh, mm, ss, 0, 0, -1))
        m = tgt - off                       # target on the mono clock
        hit = [(s, m - seg[s][0]) for s in SEGS if seg[s][0] <= m <= seg[s][0] + seg[s][1]]
        if hit:
            s, o = hit[0]
            print(f"\n{q} -> segment {s}, offset {o:.2f} s  (+/- {sd:.2f} s clock residual)")
        else:
            nearest = min(SEGS, key=lambda s: abs(m - seg[s][0]))
            print(f"\n{q} -> NOT inside any segment; nearest seg {nearest} "
                  f"t0 {m - seg[nearest][0]:+.2f} s")


if __name__ == "__main__":
    main()
