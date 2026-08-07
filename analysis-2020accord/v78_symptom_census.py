#!/usr/bin/env python3
"""DELIVERABLE 4 -- the exposure and speed census for route `5e` (V75, pre-fault) vs `5d` (V74).

🛑 THIS RUNS FIRST AND IT IS ALLOWED TO KILL THE REST. `memory/accord-averaged-spectrum-needs-
matched-speed-distributions.md` requires a per-window speed census beside any averaged spectrum,
and `memory/feedback-episodes-not-windows.md` requires the resampling unit to be counted before any
CI is quoted. If 5e's engaged creep exposure and episode count are far below 5d's, a "V75 vs V74"
band ratio is not a comparison and saying so is the correct answer.

Reported:
  * per-segment and per-arm engaged/manual seconds, windows, EPISODES and ~10 s blocks;
  * the per-window speed histogram on the kit's standard edges, with the tyre-order-1 dirty
    fraction (12.5-18.7 m/s, where 0.489*v sits inside 6-9 Hz) called out;
  * stop-and-go LAUNCH count -- an engaged transition from |v| < 0.3 m/s to |v| > 2.0 m/s inside
    10 s -- because route 5d had ZERO engaged stoplight stops and the fault fired on one.

Usage:  python v78_symptom_census.py   ->  writes _v78_census.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

V.install_fs()
OUT = {}
VE = [0, 0.5, 2, 4, 6.2, 9.4, 12.5, 18.7, 20, 25, 40]
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0]}


def raw(build):
    """Concatenated per-frame channels over the build's non-parked segments."""
    B = G.BUILDS[build]
    acc = {k: [] for k in ("t", "v", "lat", "tq", "rate", "seg")}
    for s in B["segs"]:
        if s in PARK.get(build, []):
            continue
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        acc["t"].append(np.asarray(d["t"], float))
        acc["v"].append(np.abs(np.asarray(d["cs_v"], float)))
        acc["lat"].append(np.asarray(d["cc_lat"], float) > 0.5)
        acc["tq"].append(np.asarray(d["tq"], float))
        acc["rate"].append(np.asarray(d["rate_c"], float))
        acc["seg"].append(np.full(len(d["t"]), s, float))
    return {k: np.concatenate(v) for k, v in acc.items()}


def launches(build):
    """Stop-and-go launches, and how many of them are LKAS-engaged on the way out.

    🛑 The handoff's "route 5d has ZERO engaged stoplight stops" is true only for the strictest
    reading -- engaged THROUGH the standstill. On BOTH routes openpilot's `latActive` is 0 at every
    standstill (measured: `lat_at_stop` = 0.00 for 100% of stops on 5d and 5e). The regime that
    actually exists, and the one the operator described, is an engaged LAUNCH: a stop of >= 1 s,
    then a ramp through 2.0 m/s within 15 s with `latActive` true over that ramp.
    """
    B = G.BUILDS[build]
    n = neng = 0
    detail = []
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        t = np.asarray(d["t"], float)
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        fs = G.fs_of(d)
        for a, b in C.runs_of(v < 0.3, t, int(1.0 * fs)):
            w = slice(b, min(b + int(15 * fs), len(v)))
            if w.start >= len(v):
                continue
            j = np.flatnonzero(v[w] > 2.0)
            if not len(j):
                continue
            n += 1
            ramp = slice(b, b + int(j[0]) + 1)
            fe = float(np.mean(lat[ramp])) if ramp.stop > ramp.start else 0.0
            if fe > 0.5:
                neng += 1
            detail.append(dict(seg=int(s), t=float(t[b]), stop_s=float((b - a) / fs),
                               ramp_s=float((ramp.stop - ramp.start) / fs), eng_ramp=fe,
                               lat_at_stop=float(np.mean(lat[a:b]))))
    return n, neng, detail


V.hdr("4a. PER-SEGMENT EXPOSURE -- route 5d (V74) and route 5e (V75, PRE-FAULT ONLY)")
seg_tab = {}
for b in ("V74/r5d", "V75/r5e"):
    B = G.BUILDS[b]
    print(f"\n  {b}   parked/excluded segments {PARK.get(b, [])}")
    tot_e = tot_m = 0.0
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, B["cache"], B["pfx"])
        t = np.asarray(d["t"], float)
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        fs = G.fs_of(d)
        e, m = float(lat.sum() / fs), float((~lat).sum() / fs)
        flag = "  [PARKED, excluded]" if s in PARK.get(b, []) else ""
        if not flag:
            tot_e += e
            tot_m += m
        seg_tab[f"{b}|{s}"] = dict(sec=len(t) / fs, eng=e, man=m, vmed=float(np.median(v)),
                                   vmax=float(v.max()), parked=bool(flag))
        print(f"    seg{s:<3} {len(t) / fs:6.1f} s   engaged {e:6.1f} s   manual {m:6.1f} s   "
              f"v med {np.median(v):5.2f} max {v.max():5.2f}{flag}")
    print(f"    {'TOTAL (non-parked)':<10}       engaged {tot_e:6.1f} s   manual {tot_m:6.1f} s")
    seg_tab[f"{b}|TOTAL"] = dict(eng=tot_e, man=tot_m)
OUT["segments"] = seg_tab

V.hdr("4b. ★★ THE ARM CENSUS -- seconds, windows and RESAMPLING UNITS per arm")
print("  🛑 `ep` (contiguous engagement run) is the resampling unit every CI in this session uses.")
print("  A ratio's power is set by `ep`, not by seconds and never by windows.\n")
R = V.records()
ARMS = [("engaged, ALL speed", dict(eng=1)),
        ("engaged, CREEP 0.5-4 m/s", dict(eng=1, vlo=0.5, vhi=4.0)),
        ("engaged, < 12.5 m/s (PRIMARY)", dict(eng=1, vhi=12.5)),
        ("engaged, 9.4-12.5 (tyre-CLEAN)", dict(eng=1, vlo=9.4, vhi=12.5)),
        ("engaged, 12.5-18.7 (order-1 DIRTY)", dict(eng=1, vlo=12.5, vhi=18.7)),
        ("engaged, >= 20 (tyre-CLEAN)", dict(eng=1, vlo=20.0)),
        ("manual, ALL speed", dict(eng=0)),
        ("manual, CREEP 0.5-4 m/s", dict(eng=0, vlo=0.5, vhi=4.0))]


def sub(rs, eng=None, vlo=None, vhi=None):
    o = rs
    if eng is not None:
        o = [r for r in o if r["eng"] == eng]
    if vlo is not None:
        o = [r for r in o if r["v"] >= vlo]
    if vhi is not None:
        o = [r for r in o if r["v"] < vhi]
    return o


arm = {}
print(f"  {'arm':<36} " + "".join(f"{b:>26}" for b in ("V74/r5d", "V75/r5e")))
for lab, kw in ARMS:
    cells = []
    for b in ("V74/r5d", "V75/r5e"):
        rs = sub([r for r in R[b] if r["seg"] not in PARK[b]], **kw)
        ep = len({r["ep"] for r in rs})
        bl = len({r["blk"] for r in rs})
        arm[f"{b}|{lab}"] = dict(n=len(rs), sec=len(rs) * 1.28, ep=ep, blk=bl)
        cells.append(f"n={len(rs):>4} {len(rs) * 1.28:>6.0f}s ep={ep:>3} blk={bl:>3}")
    print(f"  {lab:<36} " + "".join(f"{c:>26}" for c in cells))
OUT["arms"] = arm

V.hdr("4c. PER-WINDOW SPEED HISTOGRAM (engaged) -- the necessary-but-not-sufficient wheel-order check")
print("  Tyre order 1 = 0.489*v Hz sits INSIDE 6-9 Hz for 12.5-18.7 m/s. A route that spends its")
print("  engaged time there contaminates the micro-ratchet band with a wheel line.\n")
sp = {}
for b in ("V74/r5d", "V75/r5e", "V73/r5a", "V72/r59"):
    rs = sub([r for r in R[b] if r["seg"] not in PARK.get(b, [])], eng=1)
    v = np.array([r["v"] for r in rs], float)
    if not len(v):
        continue
    h = np.histogram(v, bins=VE)[0]
    d1 = float(np.mean((v >= 12.5) & (v < 18.7)))
    sp[b] = dict(n=len(v), hist=[int(x) for x in h], vmed=float(np.median(v)), dirty=d1)
    print(f"  {b:<10} n={len(v):>5} v_med={np.median(v):>5.2f}  order-1-dirty {100 * d1:>5.1f}%   "
          + " ".join(f"{x:>4d}" for x in h))
print("  " + " " * 44 + "bins " + " ".join(f"{e:>4g}" for e in VE[1:]))
OUT["speed_hist"] = sp

print("\n  ★ Two-sample KS on the engaged per-window speed distributions, V74 vs V75:")
a = np.array([r["v"] for r in sub([r for r in R["V74/r5d"] if r["seg"] not in PARK["V74/r5d"]],
                                  eng=1)], float)
c = np.array([r["v"] for r in sub([r for r in R["V75/r5e"] if r["seg"] not in PARK["V75/r5e"]],
                                  eng=1)], float)
gr = np.sort(np.concatenate([a, c]))
D_ = float(np.max(np.abs(np.searchsorted(np.sort(a), gr, "right") / len(a)
                         - np.searchsorted(np.sort(c), gr, "right") / len(c))))
print(f"     D = {D_:.3f}   (windows are not independent, so this is DESCRIPTIVE -- read it as")
print("     'how differently the two routes were driven', not as a p-value.)")
OUT["ks_D_speed"] = D_

V.hdr("4d. ★★ ENGAGED STOP-AND-GO LAUNCHES -- the regime route 5d structurally did not contain")
lt = {}
for b in ("V74/r5d", "V75/r5e", "V73/r5a", "V72/r59"):
    n, neng, det = launches(b)
    lt[b] = dict(n=n, n_eng=neng, detail=det[:40])
    print(f"  {b:<10} {n:>3} launches, of which {neng:>3} have an LKAS-ENGAGED ramp   "
          f"(latActive at the standstill itself: "
          f"{100 * np.mean([x['lat_at_stop'] for x in det]) if det else float('nan'):.1f}%)")
    for x in det[:12]:
        print(f"       seg{x['seg']:<3} t={x['t']:7.1f} s   stopped {x['stop_s']:5.1f} s   "
              f"ramp {x['ramp_s']:5.1f} s   engaged over ramp {x['eng_ramp']:.2f}")
OUT["launches"] = lt

with open(ROOT / "_v78_census.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _v78_census.json")
