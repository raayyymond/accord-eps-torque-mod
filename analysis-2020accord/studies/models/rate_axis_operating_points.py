#!/usr/bin/env python3
"""studies/models/rate_axis_operating_points.py -- put grind #1 and grind #2 on the SAME raw-count rate axis.

The question this answers: r24's gain is a LERP whose evaluation axis is a rate with breakpoints at
raw counts [0, 400, 1500, 3000]. If the two grinds sit at different points on that axis, the
breakpoints are calibration and the fix is cal-only.

🛑 UNITS. Raw counts, never deg/s. The caches store SCALED values (`rate_c` = 0x14A b2:3 x -1.0,
`rate_f` = 0x18F b2:3 x -0.1), so the raw signed count is recovered here as:
      0x14A raw = -rate_c      (|raw| == |rate_c|, the scale is unity)
      0x18F raw = -10 * rate_f
The two copies' ratio is MEASURED below rather than assumed, because the whole point of the exercise
is that both grinds land in the same units.

⚠ AND THE CAVEAT THAT DECIDES WHETHER ANY OF THIS TRANSFERS: this is a STEERING-COLUMN angle rate off
the CAN bus. r24's LERP axis is a MOTOR rate (see the gp-0x6c2c finding). They differ by the
column->motor gear ratio and by whatever filtering sits in front of the LERP. Treat these numbers as
the two grinds' RELATIVE positions on a monotone function of the axis -- which is what the
"same or different breakpoint segment" question actually needs -- not as absolute axis values.

Usage:  python studies/models/rate_axis_operating_points.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import time
from pathlib import Path

import numpy as np

from analyse_v65_routes import band_env, segs

ROOT = Path(__file__).resolve().parents[3]
BREAKPOINTS = [0, 400, 1500, 3000]
BAND2 = (30.0, 49.0)     # grind #2 candidate band
BAND1 = (18.0, 22.0)     # grind #1 band
WIN, HOP = 2.0, 0.5

# route 3b phases -- the operator drove to a parking lot, demonstrated, THEN did unrelated highway
# lateral-tuning work. Segment 2 is the demo (latActive 8.4%); 3-12 is the highway leg; 13 is arrival.
R3B_PARKING = set(range(0, 3))
R3B_HIGHWAY = set(range(3, 13))
R3B_ARRIVAL = {13}


def build(tag):
    """Per-window table with BOTH bands and BOTH raw-count rate copies."""
    rows = []
    for s, d in segs(tag):
        fs = 1.0 / np.median(np.diff(d["t"]))
        e2 = band_env(d["tq"], fs, *BAND2)
        e1 = band_env(d["tq"], fs, *BAND1)
        r14 = np.abs(d["rate_c"])          # 0x14A b2:3, raw counts (scale was -1.0)
        r18 = np.abs(d["rate_f"]) * 10.0   # 0x18F b2:3, raw counts (scale was -0.1)
        w0 = float(d["wall_t0"][0])
        nw, step = int(WIN * fs), max(1, int(HOP * fs))
        for i in range(0, len(d["t"]) - nw, step):
            sl = slice(i, i + nw)
            rows.append(dict(
                tag=tag, seg=int(s), t=float(d["t"][i]), wall=w0 + float(d["t"][i]),
                e2=float(np.percentile(e2[sl], 99)), e1=float(np.percentile(e1[sl], 99)),
                v=float(np.median(d["cs_v"][sl])),
                r14_med=float(np.median(r14[sl])), r14_p90=float(np.percentile(r14[sl], 90)),
                r14_max=float(r14[sl].max()),
                r18_med=float(np.median(r18[sl])), r18_p90=float(np.percentile(r18[sl], 90)),
                r18_max=float(r18[sl].max()),
                absang=float(np.abs(d["ang"][sl]).max()),
                tq_avg=float(np.abs(d["tq"][sl]).mean()), tq_max=float(np.abs(d["tq"][sl]).max()),
                lat=float((d["cc_lat"][sl] > 0.5).mean()),
            ))
    return rows


def copies_agree(tag, rows):
    """MEASURE the 0x14A : 0x18F ratio rather than taking 1.25x on faith."""
    a = np.array([r["r14_max"] for r in rows])
    b = np.array([r["r18_max"] for r in rows])
    k = b > 20
    ratio = a[k] / b[k]
    # slope through the origin is the right estimator for a pure scale difference
    slope = float(np.sum(a[k] * b[k]) / np.sum(b[k] ** 2))
    print(f"\n-- {tag.upper()}: 0x14A vs 0x18F rate copies, RAW COUNTS ({k.sum()} windows, |0x18F|>20) --")
    print(f"   per-window ratio 0x14A/0x18F : p10 {np.percentile(ratio, 10):.4f}  "
          f"med {np.median(ratio):.4f}  p90 {np.percentile(ratio, 90):.4f}  "
          f"sd {ratio.std():.4f}")
    print(f"   least-squares slope through origin : {slope:.4f}  =>  "
          f"0x18F raw counts are {1 / slope:.3f}x the 0x14A raw counts")
    print(f"   ⚠ THE 1.25x IS IN THE **SCALED** VALUES, NOT THE COUNTS. 0x14A's LSB is 1.0 and")
    print(f"     0x18F's is 0.1, so the 10x resolution difference multiplies the 1.25x unit")
    print(f"     discrepancy: scaled 0x14A = 1.25 x scaled 0x18F, but RAW 0x18F = 8 x RAW 0x14A.")
    print(f"     Which register the LERP axis reads therefore moves the operating point by 8x,")
    print(f"     which is more than the whole span of the [0,400,1500,3000] breakpoint ladder.")
    return float(np.median(ratio)), slope


def lerp_occupancy(top, key, label):
    b = np.searchsorted(BREAKPOINTS, [r[key] for r in top], side="right") - 1
    cells = []
    for i in range(len(BREAKPOINTS)):
        lab = (f"[{BREAKPOINTS[i]},{BREAKPOINTS[i + 1]})" if i + 1 < len(BREAKPOINTS)
               else f">={BREAKPOINTS[i]}")
        cells.append(f"seg{i} {lab} {int((b == i).sum()):2d}")
    print(f"      {label:26s} " + " | ".join(cells))


def stats(label, rows, key):
    if not rows:
        print(f"   {label:34s}      (no windows)")
        return
    x = np.array([r[key] for r in rows])
    print(f"   {label:34s} n={len(rows):4d}  p10 {np.percentile(x, 10):8.1f}  "
          f"med {np.median(x):8.1f}  p90 {np.percentile(x, 90):8.1f}  max {x.max():8.1f}")


def seg_of(r):
    return f"{r['tag']}s{r['seg']}"


def matched_quiet(rows, top, band_key, dv=0.5, dtq=0.25):
    """Windows at the SAME operating point (speed + driver effort) but WITHOUT the burst.

    A quiet baseline taken route-wide would be a speed contrast, not a burst contrast: the top
    windows are all creep + heavy effort, so anything route-wide differs on the axis being measured.
    """
    med = float(np.median([r[band_key] for r in rows]))
    topset = {(r["tag"], r["seg"], round(r["t"], 2)) for r in top}
    # exclude anything within +/- WIN of a top window in the same segment (overlap)
    near = [(r["seg"], r["t"]) for r in top]
    out = []
    for r in rows:
        if (r["tag"], r["seg"], round(r["t"], 2)) in topset:
            continue
        if any(r["seg"] == s and abs(r["t"] - t) < WIN for s, t in near):
            continue
        if r[band_key] >= med:
            continue
        for q in top:
            if abs(r["v"] - q["v"]) <= dv and abs(r["tq_avg"] - q["tq_avg"]) <= dtq * q["tq_avg"]:
                out.append(r)
                break
    return out, med


def table(title, top, band_key, other_key, hiway=None):
    print(f"\n-- {title} --")
    print(f"   {'seg':>5s} {'t':>7s} {'wall':>9s} {'vEgo':>5s} {'lat':>4s} {'|ang|':>6s} "
          f"{'|tq|av':>6s} | {'30-49':>7s} {'18-22':>7s} | "
          f"{'r14med':>6s} {'r14p90':>6s} {'r14max':>6s} | {'r18max':>6s} | {'seg#':>4s}")
    for r in top:
        hw = ""
        if hiway is not None:
            hw = "HWY" if r["seg"] in hiway else ("lot" if r["seg"] in R3B_PARKING else "arr")
        b = np.searchsorted(BREAKPOINTS, r["r14_p90"], side="right") - 1
        print(f"   {seg_of(r):>5s} {r['t']:6.2f}s "
              f"{time.strftime('%H:%M:%S', time.localtime(r['wall'])):>9s} {r['v']:5.2f} "
              f"{r['lat']:4.2f} {r['absang']:6.1f} {r['tq_avg']:6.0f} | "
              f"{r[band_key]:7.1f} {r[other_key]:7.1f} | "
              f"{r['r14_med']:6.0f} {r['r14_p90']:6.0f} {r['r14_max']:6.0f} | "
              f"{r['r18_max']:6.0f} | {b:>2d}{'  ' + hw if hw else ''}")


def run(tag, hiway=None):
    rows = build(tag)
    print(f"\n{'=' * 112}\n== {tag.upper()}  ({len(rows)} windows of {WIN:.0f}s / {HOP:.1f}s hop)\n{'=' * 112}")
    copies_agree(tag, rows)

    # 🛑 The two bands OVERLAP in time: the loudest 18-22 windows include the grind #2 bursts, whose
    # broadband content lights both. A top-20 that mixes them measures grind #2 twice, so each band
    # also gets a BAND-EXCLUSIVE list -- loudest in its own band while the OTHER band is quiet.
    p75_e2 = float(np.percentile([r["e2"] for r in rows], 75))
    p75_e1 = float(np.percentile([r["e1"] for r in rows], 75))
    for band_key, other_key, band, excl in (
            ("e2", "e1", BAND2, lambda r: r["e1"] < p75_e1),
            ("e1", "e2", BAND1, lambda r: r["e2"] < p75_e2)):
        nm = f"{band[0]:.0f}-{band[1]:.0f} Hz"
        for kind, pool in (("", rows), (" [BAND-EXCLUSIVE: other band below its route p75]",
                                        [r for r in rows if excl(r)])):
            top = sorted(pool, key=lambda q: -q[band_key])[:20]
            table(f"{tag.upper()} TOP 20 by {nm} envelope p99{kind}   "
                  f"[seg# = LERP seg for r14_p90 vs {BREAKPOINTS}]",
                  top, band_key, other_key, hiway)
            q, med = matched_quiet(rows, top, band_key)
            print(f"\n   RATE COUNTS ({nm}{kind} top-20 vs a MATCHED-QUIET baseline: same vEgo "
                  f"+/-0.5 m/s\n   and same |tq|avg +/-25%, but band envelope below the route "
                  f"median {med:.1f}):")
            print(f"   -- 0x14A raw counts (LSB = 1 unit) --")
            for key in ("r14_med", "r14_p90", "r14_max"):
                stats(f"top-20  {key}", top, key)
                stats(f"quiet   {key}", q, key)
            print(f"   -- 0x18F raw counts (LSB = 0.1 unit, i.e. 8x the 0x14A count) --")
            for key in ("r18_med", "r18_p90", "r18_max"):
                stats(f"top-20  {key}", top, key)
                stats(f"quiet   {key}", q, key)
            print(f"   LERP segment occupancy of the top-20 vs {BREAKPOINTS} -- BOTH copies, "
                  f"because the units decide it:")
            lerp_occupancy(top, "r14_p90", "if axis is 0x14A counts")
            lerp_occupancy(top, "r18_p90", "if axis is 0x18F counts")
    return rows


def phase_split(tag, rows):
    print(f"\n{'=' * 112}\n== {tag.upper()} PHASE SPLIT -- the highway leg is unrelated lateral-tuning "
          f"work and is EXCLUDED from\n== the parking-lot statistics, but kept as a high-speed "
          f"exposure sample.\n{'=' * 112}")
    phases = [("PARKING/SURFACE (segs 0-2)", lambda r: r["seg"] in R3B_PARKING),
              ("  of which the DEMO (seg 2)", lambda r: r["seg"] == 2),
              ("HIGHWAY LEG (segs 3-12)", lambda r: r["seg"] in R3B_HIGHWAY),
              ("  of which v >= 14 m/s", lambda r: r["seg"] in R3B_HIGHWAY and r["v"] >= 14),
              ("  of which v >= 25 m/s", lambda r: r["seg"] in R3B_HIGHWAY and r["v"] >= 25),
              ("ARRIVAL (seg 13)", lambda r: r["seg"] in R3B_ARRIVAL)]
    print(f"   {'phase':30s} {'n':>5s} | {'30-49 med':>9s} {'p95':>8s} {'max':>8s} | "
          f"{'18-22 med':>9s} {'p95':>8s} {'max':>8s} | {'r14 med':>8s} {'r14 p99':>8s}")
    for name, f in phases:
        sel = [r for r in rows if f(r)]
        if not sel:
            print(f"   {name:30s} {0:5d} |  (none)")
            continue
        a = np.array([r["e2"] for r in sel])
        b = np.array([r["e1"] for r in sel])
        c = np.array([r["r14_p90"] for r in sel])
        print(f"   {name:30s} {len(sel):5d} | {np.median(a):9.1f} {np.percentile(a, 95):8.1f} "
              f"{a.max():8.1f} | {np.median(b):9.1f} {np.percentile(b, 95):8.1f} {b.max():8.1f} | "
              f"{np.median(c):8.1f} {np.percentile(c, 99):8.1f}")


if __name__ == "__main__":
    ra = run("r3a")
    rb = run("r3b", hiway=R3B_HIGHWAY)
    phase_split("r3b", rb)
    for tag, rows in (("r3a", ra), ("r3b", rb)):
        (ROOT / f"_cache_{tag}" / f"{tag}_rate_axis.json").write_text(json.dumps(rows))
        print(f"\n   -> _cache_{tag}/{tag}_rate_axis.json")
