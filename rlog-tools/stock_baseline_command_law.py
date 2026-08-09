#!/usr/bin/env python3
"""DOES THE RATCHET SCALE WITH THE COMMAND?  -- the only stock-baseline proxy in existing data.

`0xC6CD0` = 3564 (V57+) is a FORWARD-ONLY LKAS gain: V57's `0x2A1F0` repoint left the four feedback
readers on Honda's 891.  So on this car a given openpilot command produces ~4x the column torque a
STOCK ECU would produce for the same command, while the EPS-internal feedback path is Honda's.

If the ~7.79 Hz line is a LINEAR resonance driven by applied torque, then a779 is proportional to
the drive level, and a stock ECU (1/4 the delivered torque for the same command) would ring ~4x
smaller -- we amplified an existing mode.  If a779 is INDEPENDENT of the drive level, it is a limit
cycle and a stock ECU would ring the same -- we did not cause it.

Instrument: `ratchet_line_ladder_v87.load` verbatim.  Drive level = |openpilot LKAS command| on CAN
0xE4 (`sc_tq`, sendcan), median over the window.  Resampling unit `blk`.

🛑 This is an OBSERVATIONAL slope, not an intervention.  Command magnitude co-varies with curvature,
speed and driver input; the speed control below is partial, nothing controls curvature.  Read it as
a discriminator between "slope ~ 1" and "slope ~ 0", not as a calibrated stock prediction.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _r31_common as C31            # noqa: E402
import ratchet_line_ladder_v87 as L  # noqa: E402

RNG = np.random.default_rng(87_0809)
OUT = {}


def hdr(s):
    print("\n" + "=" * 104 + f"\n{s}\n" + "=" * 104, flush=True)


def stamp_cmd(recs, cache, pfx):
    """Attach the median |sc_tq| over each window's own sample span."""
    cols = {}
    for r in recs:
        s = r["seg"]
        if s not in cols:
            d = C31.load(s, ROOT / cache, pfx)
            cols[s] = (np.asarray(d["t"], float), np.abs(np.asarray(d["sc_tq"], float)),
                       np.abs(np.asarray(d["cs_tq"], float)))
        t, c, bar = cols[s]
        n = len(r["x"])
        j0 = int(np.argmin(np.abs(t - r["t0"])))
        sl = slice(j0, j0 + n)
        r["cmd"] = float(np.median(c[sl])) if len(c[sl]) else np.nan
        r["cmd_p90"] = float(np.percentile(c[sl], 90)) if len(c[sl]) else np.nan
        r["bar"] = float(np.median(bar[sl])) if len(bar[sl]) else np.nan
    return recs


def loglog_slope(recs, xkey, floor=1.0, nboot=2000):
    x = np.array([r[xkey] for r in recs], float)
    y = np.array([r["a779"] for r in recs], float)
    u = np.array([r["blk"] for r in recs])
    ok = np.isfinite(x) & np.isfinite(y) & (x > floor) & (y > 0)
    x, y, u = np.log(x[ok]), np.log(y[ok]), u[ok]
    if len(x) < 8:
        return None
    groups = {}
    for i, k in enumerate(u):
        groups.setdefault(k, []).append(i)
    keys = list(groups)
    full = np.polyfit(x, y, 1)[0]
    d = []
    for _ in range(nboot):
        idx = np.concatenate([groups[keys[i]] for i in RNG.integers(0, len(keys), len(keys))])
        if len(set(np.round(x[idx], 3))) < 4:
            continue
        d.append(np.polyfit(x[idx], y[idx], 1)[0])
    if len(d) < 50:
        return dict(slope=float(full), lo=np.nan, hi=np.nan, n=int(len(x)))
    return dict(slope=float(full), lo=float(np.percentile(d, 2.5)),
                hi=float(np.percentile(d, 97.5)), n=int(len(x)))


def main():
    hdr("a779 vs OPENPILOT COMMAND  --  log-log slope, engaged arm, block bootstrap\n"
        "   slope ~ +1  =>  linear in drive level  =>  a stock ECU (1/4 delivered) rings ~4x smaller\n"
        "   slope ~  0  =>  limit cycle, drive-independent  =>  a stock ECU rings the SAME")
    per = {}
    for route, cache, pfx, segs in L.ROUTES:
        e = stamp_cmd(L.load(route, cache, pfx, segs, True), cache, pfx)
        per[route] = e
        c = np.array([r["cmd"] for r in e], float)
        c = c[np.isfinite(c)]
        print(f"  {route:10s} n={len(e):3d}  |cmd| p10/p50/p90 = "
              f"{np.percentile(c,10):6.0f}/{np.median(c):6.0f}/{np.percentile(c,90):6.0f} counts",
              flush=True)

    print(f"\n{'build':10s} {'n':>4s} | {'slope d log a779 / d log |cmd|':>34s} | "
          f"{'same, torsion-bar |tq| as x':>30s}")
    for route, _, _, _ in L.ROUTES:
        s1 = loglog_slope(per[route], "cmd", floor=1.0)
        s2 = loglog_slope(per[route], "bar", floor=1.0)
        OUT[route] = dict(cmd=s1, bar=s2)
        f = lambda s: (f"{s['slope']:+7.3f} [{s['lo']:+7.3f},{s['hi']:+7.3f}]" if s else "  n/a")
        print(f"{route:10s} {len(per[route]):4d} | {f(s1):>34s} | {f(s2):>30s}")

    hdr("POOLED across all four builds, with a per-build intercept (the build is absorbed)")
    xs, ys, us = [], [], []
    for route, _, _, _ in L.ROUTES:
        e = [r for r in per[route] if np.isfinite(r["cmd"]) and r["cmd"] > 1 and r["a779"] > 0]
        lx = np.log([r["cmd"] for r in e])
        ly = np.log([r["a779"] for r in e])
        xs.append(lx - lx.mean())
        ys.append(ly - ly.mean())
        us += [f"{route}:{r['blk']}" for r in e]
    X, Y, U = np.concatenate(xs), np.concatenate(ys), np.array(us)
    groups = {}
    for i, k in enumerate(U):
        groups.setdefault(k, []).append(i)
    keys = list(groups)
    full = np.polyfit(X, Y, 1)[0]
    d = []
    for _ in range(4000):
        idx = np.concatenate([groups[keys[i]] for i in RNG.integers(0, len(keys), len(keys))])
        d.append(np.polyfit(X[idx], Y[idx], 1)[0])
    lo, hi = np.percentile(d, [2.5, 97.5])
    print(f"  pooled within-build slope = {full:+.3f}  [{lo:+.3f}, {hi:+.3f}]   n = {len(X)} windows")
    print(f"  implied a779 at 1/4 the delivered torque:  x{4.0**-full:.2f} "
          f"[{4.0**-hi:.2f}, {4.0**-lo:.2f}]")
    OUT["pooled"] = dict(slope=float(full), lo=float(lo), hi=float(hi), n=int(len(X)),
                         implied_stock_factor=float(4.0 ** -full),
                         implied_lo=float(4.0 ** -hi), implied_hi=float(4.0 ** -lo))

    hdr("COMMAND-BINNED a779 -- the raw ladder the slope is fitted to")
    edges = [0, 200, 500, 1000, 2000, 4000, 100000]
    print(f"{'build':10s} | " + " ".join(f"{edges[i]}-{edges[i+1]:<6d}" for i in range(len(edges) - 1)))
    for route, _, _, _ in L.ROUTES:
        row = []
        for i in range(len(edges) - 1):
            g = [r["a779"] for r in per[route] if edges[i] <= r["cmd"] < edges[i + 1]]
            row.append(f"{np.median(g):6.0f}(n{len(g):<2d})" if len(g) >= 3 else f"{'--':>6s}(n{len(g):<2d})")
        print(f"{route:10s} | " + " ".join(row))
        OUT[route]["binned"] = [
            (edges[i], edges[i + 1],
             float(np.median([r["a779"] for r in per[route]
                              if edges[i] <= r["cmd"] < edges[i + 1]] or [np.nan])),
             sum(1 for r in per[route] if edges[i] <= r["cmd"] < edges[i + 1]))
            for i in range(len(edges) - 1)]

    dst = ROOT / "_cache_r6f" / "stock_baseline_search.json"
    prev = json.loads(dst.read_text()) if dst.exists() else {}
    prev["command_law"] = OUT
    dst.write_text(json.dumps(prev, indent=1, default=float))
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
