#!/usr/bin/env python3
"""studies/sessions/r4f/r4a_orchestrator_checks.py -- extraction audit + exposure + grind #1/#2 statistics for route `4a`.

Route `75604b0a432fdc89_0000004a--346bf31d97`, segments 20-25 only, flown on V67. The operator's
description: "mostly parking-lot level driving and testing of grind #1, which I was not really able
to introduce."

WHY THIS ROUTE EXISTS. Route 47 (the first V67 route, 150,327 frames) left ONE hole: only 22 s of
ENGAGED-CREEP exposure. That made the grind-#2 elimination claim asymmetric -- the MANUAL arm was
solid at P(0 bursts | Kd=2 rate) = 0.020, but the ENGAGED arm expected only 1.04 bursts, so its
zero-burst result had P(0) = 0.35 and proved nothing. Route 4a was driven to close that.

Sections, each runnable alone:
    identity   0x14A byte4 payload census -- V67 vs V68 from the LOG, not the filename
    probe      liveness / gate-vs-latActive / mask / third arm / arm ladder, frames and seconds
    flight     STEER_STATUS census (two independent ways), onroadEvents, CAN grid rate
    exposure   wall time, speed bands, engagement crossed with speed, the grind-#2 corner
    grind1     18-22 Hz engaged-creep dose table + the within-route arm-matched 2x2
    grind2     40-49 Hz burst census + the Poisson power calculation that is the point of the route
    anomaly    free spectral search + wheel-order screen

Usage:  python studies/sessions/r4f/r4a_orchestrator_checks.py [section ...]      (default: all)

METHOD RULES, each of which has retracted a claim in this kit:
  EPISODES   ratios bootstrap over EPISODES, never windows. A window bootstrap shrinks the CI by
             ~sqrt(windows/episode) and manufactures significance.
  NULL       every ratio is quoted against a SPLIT-HALF null computed with the identical estimator.
  ENVELOPE   `_grind2_lib.win_env` -- linear detrend + Hann taper + central 60% with the taper
             divided back out. A hand-rolled envelope without the taper ran 1.4-1.9x LOW here.
  MEAN+TAIL  reported together; they have disagreed in SIGN on this data.
  SECOND METHOD  any load-bearing count is taken twice: once off the 0x14A grid, once off the raw
             src-1 frames as they arrived.
"""
from __future__ import annotations
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

import glob
import json
import pickle
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import poisson

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:                                    # Windows consoles default to cp1252 and die on the emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                            # noqa: E402
import r47_orchestrator_checks as R47                              # noqa: E402
from _r31_common import fs_of, load, sustained                     # noqa: E402

C4A = ROOT / "_scratch/cache/r4a"
SEGS = [20, 21, 22, 23, 24, 25]
PFX = "r4as"
RNG = np.random.default_rng(20260802)
OUTJSON = HERE / "_scratch/out/_r4a_results.json"

# Register route 4a as a build for `_grind2_lib`. kd=2.5 is V67's LABEL ("2 when gated"), not a dose.
G.BUILDS["V67/r4a"] = dict(cache=C4A, pfx=PFX, segs=SEGS, kd=2.5)

V67_47 = "V67/r47"
GATE47 = "V67/r47@gate"
GATE4A = "V67/r4a@gate"
KD1 = ["V59/r2c", "V64/r35"]
KD2 = ["V62/r37", "V65/r3a", "V65/r3b"]
CREEP_AB = (0.3, 5.35)        # the arm-matched A/B's creep window (route 31's max engaged speed)
HEADLINE = "e_18-22"
BANDORDER = ["1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49"]
CV = [(0.0, 2.0), (2.0, 4.0), (4.0, 5.36)]
CE = [(0.0, 200.0), (200.0, 800.0), (800.0, 1e9)]
CR = [(0.0, 8.0), (8.0, 32.0), (32.0, 1e9)]
CA = [(0.0, 15.0), (15.0, 90.0), (90.0, 1e9)]

TYRE_C = 2.075          # m, measured circumference (V56 2.090 / V57 2.073-2.080)
RESULTS: dict = {}


def hdr(s):
    print(f"\n{'=' * 108}\n{s}\n{'=' * 108}")


def segs4a():
    for s in SEGS:
        yield s, load(s, C4A, PFX)


def bin3(x, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= x < hi:
            return i
    return len(bins) - 1


def recell(rs, keys=("v", "eff", "rate")):
    tbl = {"v": CV, "eff": CE, "rate": CR, "ang": CA}
    return [dict(r, cell=tuple(bin3(r[k], tbl[k]) for k in keys)) for r in rs]


def creep(rs, eng=1, vlo=CREEP_AB[0], vhi=CREEP_AB[1]):
    return [r for r in rs if r["eng"] == eng and vlo <= r["v"] <= vhi]


# =================================================================================================
def sec_identity():
    hdr("1.  BUILD IDENTITY FROM THE LOG -- V67 has bit3 CLEAR by construction, V68 sets it ALWAYS")
    print("   V68's cave loads `movea 0x88,r0,r7` (bit7 liveness + bit3 build-class marker), so on a")
    print("   V68 log EVERY legal frame has bit3 set and 0x87 can never appear. bit3 alone separates")
    print("   the two builds without trusting the filename.\n")
    grid, raw = Counter(), Counter()
    for s, d in segs4a():
        grid.update(d["probe"].astype(int).tolist())
        raw.update(np.asarray(d["raw14_b4"], int).tolist())
    ngrid, nraw = sum(grid.values()), sum(raw.values())
    print(f"   {'byte4':>7s} {'grid frames':>12s} {'%':>8s} {'RAW 0x14A src1':>15s} {'%':>8s}   bits")
    for v in sorted(set(grid) | set(raw)):
        b = f"b7={v >> 7 & 1} b6={v >> 6 & 1} b5={v >> 5 & 1} b4={v >> 4 & 1} b3={v >> 3 & 1} " \
            f"st={v & 7}"
        print(f"   0x{v:02X}   {grid[v]:12d} {100 * grid[v] / ngrid:7.3f}% {raw[v]:15d} "
              f"{100 * raw[v] / nraw:7.3f}%   {b}")
    b3 = sum(c for v, c in grid.items() if v & 0x08)
    b3r = sum(c for v, c in raw.items() if v & 0x08)
    live = sum(c for v, c in grid.items() if v & 0x80)
    print(f"\n   distinct byte4 values      : {sorted(f'0x{v:02X}' for v in grid)}")
    print(f"   frames with bit3 SET       : {b3} on the grid, {b3r} on the raw stream")
    print(f"   frames with bit7 LIVENESS  : {live}/{ngrid} ({100 * live / ngrid:.3f}%)")
    verdict = ("V67" if b3 == 0 and b3r == 0 and live == ngrid else
               "V68" if b3 == ngrid else "NEITHER -- MIXED / UNKNOWN")
    print(f"\n   ⇒ THE BUILD ON THE CAR FOR ROUTE 4a IS: **{verdict}**")
    if verdict != "V67":
        print("   🛑 STOP. Every downstream statistic in this file assumes V67's decoder.")
    RESULTS["identity"] = dict(byte4={f"0x{v:02X}": c for v, c in sorted(grid.items())},
                               byte4_raw={f"0x{v:02X}": c for v, c in sorted(raw.items())},
                               bit3_set=b3, bit3_set_raw=b3r, verdict=verdict, frames=ngrid)
    return verdict


# =================================================================================================
def sec_probe():
    hdr("2.  PROBE AUDIT -- liveness, the gate, the mask, the third arm, the arm ladder")
    tot = Counter()
    rows = []
    dds = []
    for s, d in segs4a():
        n = len(d["t"])
        dur = float(d["t"][-1] - d["t"][0])
        b6 = d["g6806"] > 0.5
        lat = d["cc_lat"] > 0.5
        sca = d["sca"] > 0.5
        agree = float((b6 == lat).mean())
        edges = np.flatnonzero(np.diff(b6.astype(np.int8)))
        for i in np.flatnonzero(b6 != lat):
            dds.append(int(np.min(np.abs(edges - i))) if len(edges) else 10 ** 9)
        rows.append((s, n, dur, int((d["field"] == 0).sum()), int(d["unused"].sum()),
                     int(d["illegal"].sum()), 100 * b6.mean(), 100 * lat.mean(), 100 * agree,
                     int(np.abs(np.diff(b6.astype(np.int8))).sum()),
                     int(d["g671d"].sum()), int(d["g671a"].sum()), 100 * (b6 == sca).mean()))
        tot["n"] += n; tot["dur"] += dur
        tot["void"] += int((d["field"] == 0).sum())
        tot["b3"] += int(d["unused"].sum())
        tot["ill"] += int(d["illegal"].sum())
        tot["b6"] += int(b6.sum()); tot["lat"] += int(lat.sum())
        tot["agree"] += int((b6 == lat).sum())
        tot["b5"] += int(d["g671d"].sum()); tot["b4"] += int(d["g671a"].sum())
        tot["trans"] += int(np.abs(np.diff(b6.astype(np.int8))).sum())
        for a, c in Counter(d["arm"].astype(int).tolist()).items():
            tot[f"arm{a}"] += c
    print(f"   {'seg':>4s} {'n':>6s} {'dur s':>7s} {'VOID':>5s} {'bit3':>5s} {'illeg':>6s} "
          f"{'b6duty':>8s} {'lat':>8s} {'agree':>9s} {'trans':>6s} {'b5':>4s} {'b4':>4s} "
          f"{'b6==sca':>8s}")
    for r in rows:
        print(f"   s{r[0]:<3d} {r[1]:6d} {r[2]:7.2f} {r[3]:5d} {r[4]:5d} {r[5]:6d} "
              f"{r[6]:7.3f}% {r[7]:7.3f}% {r[8]:8.4f}% {r[9]:6d} {r[10]:4d} {r[11]:4d} "
              f"{r[12]:7.3f}%")
    n = tot["n"]
    print(f"   {'ALL':>4s} {n:6d} {tot['dur']:7.2f} {tot['void']:5d} {tot['b3']:5d} "
          f"{tot['ill']:6d} {100 * tot['b6'] / n:7.3f}% {100 * tot['lat'] / n:7.3f}% "
          f"{100 * tot['agree'] / n:8.4f}% {tot['trans']:6d} {tot['b5']:4d} {tot['b4']:4d}")
    dis = n - tot["agree"]
    print(f"\n   bit7 liveness : VOID (field==0) frames = {tot['void']}  ⇒ "
          f"{'the cave fired in every frame' if not tot['void'] else '🛑 VOID FRAMES PRESENT'}")
    print(f"   bit6 vs carControl.latActive : {tot['agree']}/{n} = "
          f"{100 * tot['agree'] / n:.4f}%   ({dis} disagreeing frames = {dis / 100.0:.2f} s)")
    if dds:
        dd = np.array(dds)
        print(f"      distance of each disagreement to the nearest bit6 EDGE, in samples: "
              f"mean {dd.mean():.2f}  median {np.median(dd):.1f}  max {dd.max()}")
        print(f"      within 1 sample of an edge: {int((dd <= 1).sum())}/{len(dd)}   "
              f"within 3: {int((dd <= 3).sum())}/{len(dd)}")
        print("      ⇒ " + ("all disagreements are single-frame transition edges (log-vs-CAN "
                            "timing skew), as on route 47"
                            if (dd <= 3).all() else
                            "🛑 at least one disagreement is NOT at an edge -- a real gate dropout"))
    print(f"   bit5 gp-0x671d (THE MASK, outranks the arm) : {tot['b5']} frames  "
          f"({100 * tot['b5'] / n:.4f}% duty)  ⇒ "
          f"{'never fired, as on route 47' if not tot['b5'] else '🛑 FIRED'}")
    print(f"   bit4 gp-0x671a (third arm)                  : {tot['b4']} frames  "
          f"({100 * tot['b4'] / n:.4f}% duty)")
    print(f"   illegal (bit3 set OR bit7 clear)            : {tot['ill']}")
    print("\n   ARM LADDER (2 if bit5 | else 1 if bit6 | else 3 if bit4 | else 0 = stock LERP):")
    dt = tot["dur"] / n
    lab = {0: "0  stock mode-10 LERP (Kd=1)", 1: "1  V67 arm, cal 0xC6446=5244 (Kd=2.00x)",
           2: "2  MASK, cal 0xC6442=1024 (below stock)", 3: "3  third arm, cal 0xC6440=2048"}
    for a in (0, 1, 2, 3):
        c = tot.get(f"arm{a}", 0)
        print(f"      arm {lab[a]:44s} {c:7d} frames  {c * dt:8.1f} s  "
              f"{100 * c / n:7.3f}%")
    RESULTS["probe"] = dict(frames=n, seconds=tot["dur"], void=tot["void"], illegal=tot["ill"],
                            b6_duty=100 * tot["b6"] / n, lat_duty=100 * tot["lat"] / n,
                            gate_agree_pct=100 * tot["agree"] / n, b5=tot["b5"], b4=tot["b4"],
                            arm_frames={a: tot.get(f"arm{a}", 0) for a in range(4)},
                            arm_seconds={a: tot.get(f"arm{a}", 0) * dt for a in range(4)})


# =================================================================================================
def sec_flight():
    hdr("3.  FLIGHT-CLEAN AUDIT -- STEER_STATUS, onroadEvents, CAN grid rate")
    stg, stz = Counter(), Counter()
    ev = Counter()
    evdet = []
    st3ctx = []
    rate_rows = []
    for s, d in segs4a():
        stg.update(d["sstat"].astype(int).tolist())
        stz.update(np.asarray(d["raw18_st"], int).tolist())
        e = json.loads((C4A / f"{PFX}{s}_events.json").read_text())
        for x in e:
            ev[x["name"]] += 1
        for i in np.flatnonzero(d["sstat"].astype(int) == 3):
            st3ctx.append((s, float(d["t"][i]), float(d["cs_v"][i]), float(d["cc_lat"][i]),
                           float(d["ang"][i])))
        for addr in ("raw14A", "raw18F"):
            a = np.asarray(d[addr], float)
            span = a[-1] - a[0]
            # least-squares slope of index vs arrival time -- robust to a single late/early frame
            A = np.vstack([a, np.ones(len(a))]).T
            sl = np.linalg.lstsq(A, np.arange(len(a), dtype=float), rcond=None)[0][0]
            rate_rows.append((s, addr, len(a), span, (len(a) - 1) / span, sl,
                              1.0 / np.median(np.diff(a))))
        evdet.append((s, len(e)))
    print("   STEER_STATUS (0x18F byte4 bits 7:4) -- TWO INDEPENDENT COUNTS")
    print("     'grid' = held-last onto the 0x14A arrival grid (what every statistic here uses)")
    print("     'raw'  = every 0x18F src-1 frame as it arrived, no hold, no grid")
    print(f"   {'ST':>4s} {'grid frames':>12s} {'raw frames':>12s}")
    for k in sorted(set(stg) | set(stz)):
        print(f"   {k:4d} {stg[k]:12d} {stz[k]:12d}")
    print(f"\n   *** ST==4 (the V42 state-4 EME/governor state) : grid {stg.get(4, 0)}   "
          f"raw {stz.get(4, 0)}   ⇒ "
          f"{'CLEAN -- the zero-EME streak continues' if not (stg.get(4, 0) + stz.get(4, 0)) else '🛑 STATE 4 IS BACK'}")
    print(f"   ST==3 (low-speed steer lockout, cal 0xC62EA) : grid {stg.get(3, 0)}   "
          f"raw {stz.get(3, 0)}")
    if st3ctx:
        segs_ = Counter(x[0] for x in st3ctx)
        v = np.array([x[2] for x in st3ctx]); la = np.array([x[3] for x in st3ctx])
        print(f"      segments: {dict(sorted(segs_.items()))}")
        print(f"      speed at those frames: {v.min():.3f}..{v.max():.3f} m/s (median "
              f"{np.median(v):.3f});  latActive on {int((la > 0.5).sum())}/{len(la)} of them")
        print("      ⇒ consistent with the ~5 km/h low-speed lockout window, not a fault"
              if v.max() < 2.0 else "      ⚠ ST==3 seen ABOVE the lockout window -- inspect")
    print("\n   onroadEvents census over all 6 segments (raw event-message counts, not episodes):")
    watch = ("steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
             "immediateDisable", "steerSaturated", "wrongGear", "canBusMissing")
    for w in watch:
        print(f"      {w:24s} {ev.get(w, 0):7d}"
              + ("" if ev.get(w, 0) == 0 else "   🛑"))
    print("\n   all other event names present (context only):")
    other = {k: v for k, v in ev.items() if k not in watch}
    for k, v in sorted(other.items(), key=lambda kv: -kv[1]):
        print(f"      {k:34s} {v:7d}")
    print("\n   CAN GRID RATE -- confirmed, not assumed. Three estimators per stream:")
    print(f"   {'seg':>4s} {'stream':>8s} {'n':>7s} {'span s':>9s} {'(n-1)/span':>11s} "
          f"{'lstsq slope':>12s} {'1/median(dt)':>13s}")
    for r in rate_rows:
        print(f"   s{r[0]:<3d} {r[1]:>8s} {r[2]:7d} {r[3]:9.3f} {r[4]:11.4f} {r[5]:12.4f} "
              f"{r[6]:13.4f}")
    for addr in ("raw14A", "raw18F"):
        v = np.array([r[4] for r in rate_rows if r[1] == addr])
        m = np.array([r[6] for r in rate_rows if r[1] == addr])
        print(f"   ⇒ {addr}: (n-1)/span mean {v.mean():.4f} Hz  sd {v.std(ddof=1):.4f}   |   "
              f"1/median(dt) mean {m.mean():.4f} Hz")
    print("   🛑 1/median(dt) is BIASED HIGH by ~1.0-1.4% (log-timestamp quantisation); the kit's")
    print("      `fs_of()` uses it, so the band edges of every route sit ~1% high in TRUE Hz. That")
    print("      is near-common-mode across routes, so it moves the identification, not the ratios.")
    RESULTS["flight"] = dict(st_grid=dict(stg), st_raw=dict(stz), events=dict(ev),
                             grid_hz_14A=float(np.mean([r[4] for r in rate_rows
                                                        if r[1] == "raw14A"])))


# =================================================================================================
def sec_exposure():
    hdr("4.  EXPOSURE INVENTORY -- the reason this route was driven")
    tot = dict(wall=0.0)
    print(f"   {'seg':>4s} {'n':>6s} {'wall s':>8s} {'v min':>7s} {'v max':>7s} {'eng s':>8s} "
          f"{'creep s':>8s} {'eng creep':>10s} {'4-20 s':>8s} {'hwy s':>7s}")
    per = []
    for s, d in segs4a():
        n = len(d["t"])
        dur = float(d["t"][-1] - d["t"][0])
        dt = dur / (n - 1)
        v = d["cs_v"]; lat = d["cc_lat"] > 0.5
        cr = (v > 0.3) & (v < 4.0)
        mid = (v >= 4.0) & (v <= 20.0)
        hw = v > 20.0
        per.append(dict(seg=s, n=n, dur=dur, eng=float(lat.sum()) * dt,
                        creep=float(cr.sum()) * dt, engcreep=float((cr & lat).sum()) * dt,
                        mid=float(mid.sum()) * dt, hwy=float(hw.sum()) * dt,
                        vmax=float(v.max())))
        print(f"   s{s:<3d} {n:6d} {dur:8.2f} {v.min():7.2f} {v.max():7.2f} "
              f"{float(lat.sum()) * dt:8.1f} {float(cr.sum()) * dt:8.1f} "
              f"{float((cr & lat).sum()) * dt:10.1f} {float(mid.sum()) * dt:8.1f} "
              f"{float(hw.sum()) * dt:7.1f}")
    tt = sum(p["dur"] for p in per)
    print(f"   {'ALL':>4s} {sum(p['n'] for p in per):6d} {tt:8.2f} "
          f"{'':7s} {max(p['vmax'] for p in per):7.2f} "
          f"{sum(p['eng'] for p in per):8.1f} {sum(p['creep'] for p in per):8.1f} "
          f"{sum(p['engcreep'] for p in per):10.1f} {sum(p['mid'] for p in per):8.1f} "
          f"{sum(p['hwy'] for p in per):7.1f}")

    # ---- speed histogram + engagement cross ----------------------------------------------------
    edges = [0, 0.3, 0.5, 1, 2, 3, 4, 6, 8, 10, 14, 20, 30]
    hist = np.zeros((len(edges) - 1, 2))
    for s, d in segs4a():
        dt = float(d["t"][-1] - d["t"][0]) / (len(d["t"]) - 1)
        lat = d["cc_lat"] > 0.5
        idx = np.clip(np.searchsorted(edges, d["cs_v"], side="right") - 1, 0, len(edges) - 2)
        for k in range(len(edges) - 1):
            m = idx == k
            hist[k, 1] += float((m & lat).sum()) * dt
            hist[k, 0] += float((m & ~lat).sum()) * dt
    print(f"\n   SPEED HISTOGRAM x ENGAGEMENT, seconds "
          f"(engagement = carControl.latActive, never cruiseState)")
    print(f"   {'band m/s':>14s} {'disengaged':>11s} {'ENGAGED':>10s} {'total':>9s}")
    for k in range(len(edges) - 1):
        if hist[k].sum() < 0.05:
            continue
        print(f"   {f'{edges[k]:.1f}-{edges[k + 1]:.1f}':>14s} {hist[k, 0]:11.1f} "
              f"{hist[k, 1]:10.1f} {hist[k].sum():9.1f}")
    print(f"   {'TOTAL':>14s} {hist[:, 0].sum():11.1f} {hist[:, 1].sum():10.1f} "
          f"{hist.sum():9.1f}")
    print(f"\n   creep = 0.3 < v < 4.0 m/s -- the SAME definition studies/sessions/r47/r47_orchestrator_checks.py uses "
          f"(sec_creep / sec_exposure).")
    engc = sum(p["engcreep"] for p in per)
    print(f"   ENGAGED CREEP : {engc:.1f} s      (route 47 had 22 s -- the gap this route "
          f"was driven to close)")
    print(f"   HIGHWAY (v > 20 m/s) : {sum(p['hwy'] for p in per):.1f} s total, "
          f"{sum(p['hwy'] for p in per):.1f} s engaged   "
          f"⇒ route 4a contains NO highway driving at all "
          f"(route max speed {max(p['vmax'] for p in per):.2f} m/s)")

    # ---- within creep: angle + torque --------------------------------------------------------
    print(f"\n   WITHIN CREEP (0.3 < v < 4.0): |steering angle| and DRIVER TORQUE, by arm.")
    print("   'driver torque' = sustained |lowpass(tq, 3 Hz)| on the 0x18F torsion-bar channel --")
    print("   the kit's EFFORT convention. Raw |tq| is tripped by the oscillation itself.")
    acc = {}
    for s, d in segs4a():
        fs = fs_of(d)
        dt = float(d["t"][-1] - d["t"][0]) / (len(d["t"]) - 1)
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        v = d["cs_v"]; ang = np.abs(d["ang"])
        cr = (v > 0.3) & (v < 4.0)
        gm = d["g6806"] > 0.5
        for arm, gmask in (("gate=1 (Kd=2)", gm), ("gate=0 (Kd=1)", ~gm)):
            a = acc.setdefault(arm, Counter())
            a["creep"] += float((cr & gmask).sum()) * dt
            a["ang100"] += float((cr & gmask & (ang >= 100)).sum()) * dt
            a["tq1200"] += float((cr & gmask & (eff >= 1200)).sum()) * dt
            a["corner"] += float((cr & gmask & (ang >= 100) & (eff >= 1200)).sum()) * dt
            # the published corner uses |v| < 4 with NO lower bound -- reported both ways
            a["corner_nolo"] += float(((np.abs(v) < 4) & gmask & (ang >= 100)
                                       & (eff >= 1200)).sum()) * dt
            for q, lo in (("e0", 0), ("e200", 200), ("e800", 800), ("e1200", 1200),
                          ("e2000", 2000)):
                a[q] += float((cr & gmask & (eff >= lo)).sum()) * dt
    print(f"   {'arm':16s} {'creep s':>9s} {'|ang|>=100':>11s} {'eff>=1200':>10s} "
          f"{'CORNER':>8s} {'corner(|v|<4)':>14s}")
    for arm, a in acc.items():
        print(f"   {arm:16s} {a['creep']:9.1f} {a['ang100']:11.1f} {a['tq1200']:10.1f} "
              f"{a['corner']:8.1f} {a['corner_nolo']:14.1f}")
    print(f"\n   driver-torque distribution inside creep, seconds at or above each threshold:")
    print(f"   {'arm':16s} {'>=0':>8s} {'>=200':>8s} {'>=800':>8s} {'>=1200':>8s} {'>=2000':>8s}")
    for arm, a in acc.items():
        print(f"   {arm:16s} {a['e0']:8.1f} {a['e200']:8.1f} {a['e800']:8.1f} "
              f"{a['e1200']:8.1f} {a['e2000']:8.1f}")
    # 🛑 route 47's corner is RECOMPUTED here from its own cache, not quoted from the handoff.
    c47 = Counter()
    for s in range(26):
        p = ROOT / "_scratch/cache/r47" / f"r47s{s}.npz"
        if not p.exists():
            continue
        d = load(s, ROOT / "_scratch/cache/r47", "r47s")
        fs = fs_of(d)
        dt = float(d["t"][-1] - d["t"][0]) / (len(d["t"]) - 1)
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        c = (np.abs(d["cs_v"]) < 4) & (eff >= 1200) & (np.abs(d["ang"]) >= 100)
        gm = d["g6806"] > 0.5
        c47["g1"] += float((c & gm).sum()) * dt
        c47["g0"] += float((c & ~gm).sum()) * dt
    print(f"\n   ROUTE 47's corner, recomputed from its own cache (|v|<4, eff>=1200, |ang|>=100):")
    print(f"      gate=1 {c47['g1']:.1f} s      gate=0 {c47['g0']:.1f} s")
    print(f"   ⇒ route 4a multiplies V67's ARMED corner exposure by "
          f"{acc['gate=1 (Kd=2)']['corner_nolo'] / max(c47['g1'], 1e-9):.1f}x")
    print("   for comparison, ENGAGED corner seconds elsewhere (from the 2026-08-02 handoff):")
    print("   V65/r3a 97.9  V65/r3b 9.3  V62/r37 23.5  V59/r2c 11.8  V64/r35 8.0")
    RESULTS["exposure"] = dict(total_s=tt, per_seg=per,
                               eng_creep_s=engc, highway_s=sum(p["hwy"] for p in per),
                               corner={k: dict(v) for k, v in acc.items()})


# =================================================================================================
def _pools(vsel):
    """r47_orchestrator_checks._windows over every pool, plus route 4a and the pooled V67 row."""
    P = dict(R47.CREEP_POOLS)
    P["Kd=gated (V67 r4a)"] = ["_scratch/cache/r4a"]
    P["Kd=gated (V67 r47+r4a)"] = ["_scratch/cache/r47", "_scratch/cache/r4a"]
    return {k: sum([R47._windows(c, k, vsel) for c in v], []) for k, v in P.items()}


def _windows_eff(cache, tag, vsel):
    """`r47_orchestrator_checks._windows` with the EFFORT covariate added.

    Byte-for-byte the same envelope (4th-order butter + Hilbert on the whole segment, p99 inside
    the window) and the same window grid, so its `40-49` values are directly comparable with the
    dose table. The only addition is `eff` = mean |sustained(tq, 3 Hz)| over the window, which the
    grind-#2 CORNER definition needs and R47's version does not carry. Kept local rather than
    patched into R47 so the route-47 tables stay reproducible exactly as published.
    """
    rows = []
    for p in sorted(glob.glob(str(ROOT / cache / "*.npz"))):
        if "_imu" in p:
            continue
        d = dict(np.load(p))
        if "cs_v" not in d or "tq" not in d:
            continue
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        if not 95 < fs < 105:
            continue
        env = {k: R47._envelope(d["tq"], fs, *v) for k, v in R47.BANDS.items()}
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        n, hop = int(R47.WIN_S * fs), int(R47.WIN_S * fs) // 2
        lat = d["cc_lat"] > 0.5
        for i in range(0, len(t) - n, hop):
            sl = slice(i, i + n)
            v = float(np.median(d["cs_v"][sl]))
            if not vsel(v):
                continue
            rows.append(dict(tag=tag, ep=(p, i // (n * 4)), v=v, lat=float(lat[sl].mean()),
                             ang=float(np.abs(d["ang"][sl]).max()),
                             eff=float(np.median(eff[sl])), fs=fs,
                             **{k: float(np.percentile(env[k][sl], 99)) for k in R47.BANDS}))
    return rows


def sec_grind1():
    hdr("5.  GRIND #1 (18-22 Hz) AT ENGAGED CREEP -- route 4a added to the kit's dose table")
    print("   Statistic: p90 across windows of the per-window 40-49/18-22 envelope p99 "
          "(the kit's dose-table statistic).")
    print("   creep = 0.3 < v < 4.0 m/s; LKAS ON = latActive duty > 0.9, OFF = < 0.1.\n")
    D = _pools(lambda v: 0.3 < v < 4.0)
    print(f"   {'dose pool':42s} {'arm':8s} {'secs':>7s} {'n':>5s} {'18-22 p90':>10s} "
          f"{'18-22 MED':>10s} {'18-22 MAX':>10s} {'40-49 p90':>10s} {'40-49 MAX':>10s} "
          f"{'bursts':>7s}")
    for k, ss in D.items():
        for lab, sel in (("LKAS ON", lambda r: r["lat"] > 0.9),
                         ("LKAS OFF", lambda r: r["lat"] < 0.1)):
            s = [r for r in ss if sel(r)]
            if not s:
                print(f"   {k:42s} {lab:8s} {0:7.0f} {0:5d}")
                continue
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            print(f"   {k:42s} {lab:8s} {len(s) * R47.WIN_S / 2:7.0f} {len(s):5d} "
                  f"{np.percentile([r['18-22'] for r in s], 90):10.1f} "
                  f"{np.median([r['18-22'] for r in s]):10.1f} "
                  f"{max(r['18-22'] for r in s):10.1f} "
                  f"{np.percentile([r['40-49'] for r in s], 90):10.1f} "
                  f"{max(r['40-49'] for r in s):10.1f} {b:7d}")
        print()

    refkey = "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)"
    ref = [r for r in D[refkey] if r["lat"] > 0.9]
    be = np.array([hash(r["ep"]) for r in ref]); bv = np.array([r["18-22"] for r in ref])
    print("   GRIND #1 (18-22 Hz), ENGAGED CREEP, ratio vs the Kd=1.00 pool, EPISODE-bootstrapped:")
    tab = {}
    for k in ("Kd=0     (V61 r31)", "Kd=gated (V67 r47)", "Kd=gated (V67 r4a)",
              "Kd=gated (V67 r47+r4a)", "Kd=2.00  (V62 r37 + V65 r3a/r3b)"):
        s = [r for r in D[k] if r["lat"] > 0.9]
        if len(s) < 5:
            print(f"     {k:42s} n={len(s):4d}  -- too few windows")
            continue
        lo, md, hi = R47._boot_ratio(np.array([r["18-22"] for r in s]),
                                     np.array([hash(r["ep"]) for r in s]), bv, be)
        tab[k] = (len(s), len(s) * R47.WIN_S / 2,
                  float(np.percentile([r["18-22"] for r in s], 90)), md, lo, hi)
        print(f"     {k:42s} n={len(s):4d} secs={len(s) * R47.WIN_S / 2:6.0f}  "
              f"p90={np.percentile([r['18-22'] for r in s], 90):7.1f}  "
              f"{md:5.2f} [{lo:4.2f}, {hi:4.2f}]")
    nlo, nhi = R47._split_half_null(bv, be)
    print(f"     {'split-half NULL inside Kd=1.00':42s}                        "
          f"[{nlo:4.2f}, {nhi:4.2f}]")
    RESULTS["grind1_dose"] = dict(table=tab, null=[float(nlo), float(nhi)])

    # ---- MEAN as well as TAIL ------------------------------------------------------------------
    print("\n   🛑 MEAN AND TAIL TOGETHER (they have disagreed in sign on this data):")
    print(f"   {'pool':42s} {'p50 ratio':>18s} {'p90 ratio':>18s}")
    refm = np.array([r["18-22"] for r in ref])
    for k in ("Kd=gated (V67 r47)", "Kd=gated (V67 r4a)", "Kd=gated (V67 r47+r4a)",
              "Kd=2.00  (V62 r37 + V65 r3a/r3b)"):
        s = [r for r in D[k] if r["lat"] > 0.9]
        if len(s) < 5:
            continue
        a = np.array([r["18-22"] for r in s]); ae = np.array([hash(r["ep"]) for r in s])
        l5, m5, h5 = R47._boot_ratio(a, ae, refm, be, q=50)
        l9, m9, h9 = R47._boot_ratio(a, ae, refm, be, q=90)
        print(f"   {k:42s} {f'{m5:.2f} [{l5:.2f},{h5:.2f}]':>18s} "
              f"{f'{m9:.2f} [{l9:.2f},{h9:.2f}]':>18s}")

    # ---- within-route gate A/B ------------------------------------------------------------------
    hdr("5b. WITHIN-ROUTE ARM-MATCHED 2x2 on route 4a -- does it replicate r47's one-arm-only "
        "suppression?")
    print("   Route 47 gave: ENGAGED arm 0.524 [0.337, 0.804] vs the Kd=1 pool")
    print("                  DISENGAGED arm 1.055 [0.669, 1.354] vs the Kd=1 pool  (the PLACEBO)")
    print("   V67 runs Kd=2 ONLY in the engaged arm, so its disengaged arm is a BUILT-IN placebo:")
    print("   on that population V67 and a Kd=1 route are the same firmware. If the disengaged row")
    print("   lands where the engaged row does, the route is just a quieter drive and proves nothing.")
    print("   Partition is the FIRMWARE's own gate g6806, not openpilot's latActive.\n")
    st = _records()
    for epkey in ("ep", "blk"):
        G.EPKEY = epkey
        print(f"   ---- episode unit '{epkey}' (min_ep=1, min_win=2, creep 0.3-5.35 m/s) ----")
        print(f"   {'contrast':52s} {'ratio':>7s}  {'[95% CI]':>18s}  {'cells':>5s} "
              f"{'epA':>4s} {'epB':>4s}")
        for vlab, vkey in (("r47", GATE47), ("r4a", GATE4A), ("r47+r4a", "V67/pooled@gate")):
            for alab, eng, ctl in (("ENG / Kd=1 ENG   [Kd2 vs Kd1 = THE FIX]", 1, KD1),
                                   ("DIS / Kd=1 DIS   [Kd1 vs Kd1 = PLACEBO]", 0, KD1),
                                   ("ENG / Kd=2 ENG   [Kd2 vs Kd2 ~ 1?]", 1, KD2)):
                a = recell(creep(st[vkey], eng))
                b = recell([r for bd in ctl for r in creep(st[bd], eng)])
                if len(a) < 2 or len(b) < 2:
                    print(f"   V67/{vlab:8s} {alab:40s}   -- no windows")
                    continue
                pt, lo, hi, nc, na, nb, _, _ = G.boot_cellwise(a, b, HEADLINE, RNG, nboot=1500,
                                                               min_ep=1, min_win=2)
                print(f"   V67/{vlab:8s} {alab:40s} {pt:7.3f}  [{lo:7.3f}, {hi:7.3f}]  "
                      f"{nc:5d} {na:4d} {nb:4d}")
            n_, nl, nh = G.split_half_null(recell([r for bd in KD1 for r in creep(st[bd], 1)]),
                                           HEADLINE, RNG, nrep=200, min_ep=1, min_win=2)
            print(f"   {'   split-half null inside Kd=1 ENGAGED':52s} {n_:7.3f}  "
                  f"[{nl:7.3f}, {nh:7.3f}]")
            print()
    G.EPKEY = "ep"


_RECS = None


def _records():
    """Route 47's cached window records + route 4a's, both partitioned on the firmware gate."""
    global _RECS
    if _RECS is not None:
        return _RECS
    with open(ROOT / "_scratch/cache/r47" / "r47_grind1_records.pkl", "rb") as fh:
        st = pickle.load(fh)
    st[GATE4A] = G.wrecs("V67/r4a", maskkey="g6806")
    st["V67/r4a"] = G.wrecs("V67/r4a")
    st["V67/pooled@gate"] = st[GATE47] + st[GATE4A]
    _RECS = st
    return st


# =================================================================================================
def sec_grind2():
    hdr("6.  GRIND #2 (40-49 Hz) AT CREEP -- THE PRIMARY OPEN QUESTION")
    print(f"   burst = one {R47.WIN_S} s window whose 40-49 Hz envelope p99 exceeds {R47.BURST:.0f}.")
    print("   The V62/V65 creep bursts ran 2000-4000, so the threshold is far below the phenomenon.\n")
    D = _pools(lambda v: 0.3 < v < 4.0)
    K2 = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
    print(f"   {'pool':42s} {'arm':9s} {'secs':>7s} {'n':>5s} {'40-49 p50':>10s} "
          f"{'40-49 p90':>10s} {'40-49 MAX':>10s} {'bursts':>7s} {'rate/s':>9s}")
    rate = {}
    have = {}
    for k in (K2, "Kd=gated (V67 r47)", "Kd=gated (V67 r4a)", "Kd=gated (V67 r47+r4a)"):
        for lab, sel in (("LKAS ON", lambda r: r["lat"] > 0.9),
                         ("LKAS OFF", lambda r: r["lat"] < 0.1)):
            s = [r for r in D[k] if sel(r)]
            secs = len(s) * R47.WIN_S / 2
            if not s:
                print(f"   {k:42s} {lab:9s} {0.0:7.1f} {0:5d}")
                have[(k, lab)] = (0.0, 0)
                continue
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            print(f"   {k:42s} {lab:9s} {secs:7.1f} {len(s):5d} "
                  f"{np.median([r['40-49'] for r in s]):10.1f} "
                  f"{np.percentile([r['40-49'] for r in s], 90):10.1f} "
                  f"{max(r['40-49'] for r in s):10.1f} {b:7d} {b / max(secs, 1e-9):9.5f}")
            have[(k, lab)] = (secs, b)
            if k == K2:
                rate[lab] = b / secs
        print()
    print("   Kd=2.00 reference burst RATES, derived from the caches here (not quoted):")
    for lab in ("LKAS ON", "LKAS OFF"):
        s, b = have[(K2, lab)]
        print(f"      {lab:9s} {b} bursts / {s:.0f} s = {rate[lab]:.5f} /s")
    print("\n   POWER: P(0 bursts | the Kd=2.00 rate) for each V67 arm.")
    print(f"   {'route':22s} {'arm':9s} {'secs':>8s} {'observed':>9s} {'expected':>9s} "
          f"{'P(0)':>8s}   verdict")
    pw = {}
    for k, rl in (("Kd=gated (V67 r47)", "r47"), ("Kd=gated (V67 r4a)", "r4a"),
                  ("Kd=gated (V67 r47+r4a)", "r47+r4a POOLED")):
        for lab in ("LKAS ON", "LKAS OFF"):
            secs, obs = have[(k, lab)]
            exp = rate[lab] * secs
            p0 = float(poisson.pmf(0, exp))
            verd = ("RESOLVED (P(0) < 0.05)" if p0 < 0.05 and obs == 0 else
                    f"{obs} burst(s) OBSERVED" if obs else "UNDER-POWERED")
            need = 2.9957 / rate[lab]
            print(f"   {rl:22s} {lab:9s} {secs:8.1f} {obs:9d} {exp:9.2f} {p0:8.4f}   {verd}")
            pw[(rl, lab)] = dict(secs=secs, obs=obs, exp=exp, p0=p0, need_total_s=need,
                                 need_more_s=max(0.0, need - secs))
    print("\n   SECONDS STILL NEEDED for P(0) < 0.05 (i.e. expected >= -ln 0.05 = 2.996 bursts):")
    for lab in ("LKAS ON", "LKAS OFF"):
        need = 2.9957 / rate[lab]
        s47a = have[("Kd=gated (V67 r47+r4a)", lab)][0]
        print(f"      {lab:9s}: need {need:.0f} s of creep in that arm at the Kd=2 rate; "
              f"V67 now has {s47a:.0f} s ⇒ {max(0.0, need - s47a):.0f} s MORE required")
    RESULTS["grind2"] = {f"{a}|{b}": v for (a, b), v in pw.items()}
    RESULTS["grind2"]["kd2_rate_per_s"] = rate

    # ---- corner-conditioned power ---------------------------------------------------------------
    hdr("6b. CORNER-CONDITIONED POWER -- the stronger version of the same test")
    print("   Grind #2 did not live uniformly in creep; it lived in the corner creep ∧ |driver")
    print("   torque| >= 1200 ∧ |angle| >= 100 deg. Conditioning the RATE on that corner removes")
    print("   the assumption that route 4a's creep seconds are exchangeable with V62/V65's, which")
    print("   is the weakest link in §6. Window covariates: eff = median |sustained(tq,3Hz)|,")
    print("   ang = max |angle| in the window (R47's own convention).\n")
    CP = {"Kd=2.00 (V62 r37 + V65 r3a/r3b)": ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
          "Kd=gated (V67 r47)": ["_scratch/cache/r47"], "Kd=gated (V67 r4a)": ["_scratch/cache/r4a"],
          "Kd=gated (V67 r47+r4a)": ["_scratch/cache/r47", "_scratch/cache/r4a"]}
    W = {k: sum([_windows_eff(c, k, lambda v: 0.3 < v < 4.0) for c in v], []) for k, v in CP.items()}
    print(f"   {'pool':40s} {'arm':9s} {'corner s':>9s} {'n':>5s} {'40-49 MAX':>10s} "
          f"{'bursts':>7s} {'rate/s':>9s}")
    crate, chave = {}, {}
    for k, ss in W.items():
        for lab, sel in (("LKAS ON", lambda r: r["lat"] > 0.9),
                         ("LKAS OFF", lambda r: r["lat"] < 0.1)):
            s = [r for r in ss if sel(r) and r["eff"] >= 1200 and r["ang"] >= 100]
            secs = len(s) * R47.WIN_S / 2
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            mx = max((r["40-49"] for r in s), default=float("nan"))
            print(f"   {k:40s} {lab:9s} {secs:9.1f} {len(s):5d} {mx:10.1f} {b:7d} "
                  f"{b / max(secs, 1e-9):9.5f}")
            chave[(k, lab)] = (secs, b)
            if k.startswith("Kd=2.00"):
                crate[lab] = b / max(secs, 1e-9)
        print()
    print("   P(0 bursts | the Kd=2.00 CORNER rate):")
    print(f"   {'route':22s} {'arm':9s} {'corner s':>9s} {'observed':>9s} {'expected':>9s} "
          f"{'P(0)':>8s}")
    for k, rl in (("Kd=gated (V67 r47)", "r47"), ("Kd=gated (V67 r4a)", "r4a"),
                  ("Kd=gated (V67 r47+r4a)", "r47+r4a POOLED")):
        for lab in ("LKAS ON", "LKAS OFF"):
            secs, obs = chave[(k, lab)]
            exp = crate[lab] * secs
            print(f"   {rl:22s} {lab:9s} {secs:9.1f} {obs:9d} {exp:9.2f} "
                  f"{float(poisson.pmf(0, exp)):8.4f}")
    RESULTS["grind2_corner"] = {f"{a}|{b}": list(v) for (a, b), v in chave.items()}


# =================================================================================================
def sec_anomaly():
    hdr("7.  ANOMALY SCREEN -- free spectral search + wheel-order contamination check")
    st = _records()
    r4a = st["V67/r4a"]
    print(f"   route 4a window records: {len(r4a)}  "
          f"(engaged {sum(1 for r in r4a if r['eng'] == 1)}, "
          f"disengaged {sum(1 for r in r4a if r['eng'] == 0)})")
    print("\n   FREE 12-30 Hz LOCATE (argmax of the PROMINENCE spectrum, not of power), "
          "engaged creep:")
    for lab, rs in (("route 4a", [r for r in r4a if r["eng"] == 1 and 0.3 <= r["v"] <= 5.35]),
                    ("route 47", [r for r in st[V67_47]
                                  if r["eng"] == 1 and 0.3 <= r["v"] <= 5.35])):
        f0 = G.col(rs, "f_12-30"); pr = G.col(rs, "p_12-30")
        ok = np.isfinite(f0)
        if not ok.any():
            continue
        print(f"      {lab:10s} n={int(ok.sum()):4d}  f0 med {np.median(f0[ok]):5.2f} Hz  "
              f"sd {np.std(f0[ok]):4.2f}  prominence med {np.median(pr[ok]):5.2f}x  "
              f"p90 {np.percentile(pr[ok], 90):6.2f}x")
    print("\n   BAND-BY-BAND envelope p99 percentiles on route 4a (counts), engaged vs disengaged:")
    print(f"   {'band':>8s} " + " ".join(f"{x:>10s}" for x in
                                         ("ENG p50", "ENG p90", "ENG max",
                                          "DIS p50", "DIS p90", "DIS max")))
    for b in BANDORDER + ["30-49"]:
        e = G.col([r for r in r4a if r["eng"] == 1], "e_" + b)
        d = G.col([r for r in r4a if r["eng"] == 0], "e_" + b)
        print(f"   {b:>8s} " + " ".join(f"{x:10.1f}" for x in
                                        (np.percentile(e, 50), np.percentile(e, 90), e.max(),
                                         np.percentile(d, 50), np.percentile(d, 90), d.max())))
    print(f"\n   WHEEL-ORDER SCREEN. tyre circumference {TYRE_C:.3f} m ⇒ order k sits at "
          f"k*v/{TYRE_C:.3f} Hz.")
    print("   Route 4a's speed range makes this checkable in closed form:")
    vmax = max(float(np.max(load(s, C4A, PFX)["cs_v"])) for s in SEGS)
    for k in (1, 2, 3):
        print(f"      order {k}: creep (v<4) spans {k * 0.3 / TYRE_C:5.2f}-{k * 4 / TYRE_C:5.2f} Hz;"
              f"  whole route (v<={vmax:.2f}) tops out at {k * vmax / TYRE_C:5.2f} Hz")
    print("   ⇒ at CREEP every wheel order below 12 lies under 6 Hz, so neither 18-22 nor 40-49 Hz")
    print("     can be tyre order on this route's creep population.")
    print(f"   ⚠ the route's fastest windows ({vmax:.2f} m/s) put order 3 at "
          f"{3 * vmax / TYRE_C:.2f} Hz, INSIDE 18-22.")
    print("     The per-window check below is the one that matters: does a window's 18-22 Hz peak")
    print("     track k*v/C? A real mode is FIXED in hertz; an order is proportional to speed.")
    print("   Restrict to windows where the 18-22 line is actually PROMINENT (prom > 5), then ask")
    print("   whether f0 moves with speed. order k ⇒ f0 = k*v/C, so f0 vs v would be a straight")
    print("   line through the origin with slope k/C = k*0.482. A fixed mode has slope ~0.")
    pr = [r for r in r4a if np.isfinite(r["f_18-22"]) and r["p_18-22"] > 5]
    for lab, rs in (("all speeds  ", pr),
                    ("creep only  ", [r for r in pr if 0.3 <= r["v"] <= 4.0]),
                    ("v > 6 m/s   ", [r for r in pr if r["v"] > 6.0])):
        if len(rs) < 4:
            print(f"      {lab} n={len(rs)} -- too few")
            continue
        f0 = G.col(rs, "f_18-22"); v = G.col(rs, "v")
        sl, ic = np.polyfit(v, f0, 1)
        rho = float(np.corrcoef(v, f0)[0, 1])
        print(f"      {lab} n={len(rs):4d}  f0 med {np.median(f0):5.2f} Hz sd {np.std(f0):4.2f}  "
              f"slope d f0/d v = {sl:+.4f} Hz/(m/s)  (order 3 would be +1.446)  r={rho:+.3f}")
    print("      ⇒ a slope near 0 with f0 pinned near 20-21 Hz is a FIXED MODE, not a tyre order.")
    print("\n   NEW BURST POPULATIONS: windows whose 30-49 Hz envelope p99 exceeds 500 anywhere on")
    print("   the route (any speed, any arm):")
    big = sorted([r for r in r4a if r["e_30-49"] > 500], key=lambda r: -r["e_30-49"])
    print(f"      count {len(big)}")
    for r in big[:10]:
        print(f"      seg{r['seg']} t0={r['t0']:7.2f}s eng={r['eng']} v={r['v']:5.2f} "
              f"ang={r['ang']:7.1f} eff={r['eff']:7.1f} e30-49={r['e_30-49']:8.1f} "
              f"e40-49={r['e_40-49']:8.1f} f0={r['f_30-49']:5.2f}Hz prom={r['p_30-49']:5.2f}")
    print("\n   TOP 10 windows by 18-22 Hz envelope p99 (where grind #1 came closest to appearing):")
    for r in sorted(r4a, key=lambda r: -r["e_18-22"])[:10]:
        print(f"      seg{r['seg']} t0={r['t0']:7.2f}s eng={r['eng']} v={r['v']:5.2f} "
              f"ang={r['ang']:7.1f} eff={r['eff']:7.1f} rate={r['rate']:6.2f} "
              f"e18-22={r['e_18-22']:8.1f} f0={r['f_18-22']:5.2f}Hz prom={r['p_18-22']:5.2f}")


# =================================================================================================
def sec_burst():
    hdr("8.  🛑 THE ONE PLACE GRIND #1 DID APPEAR -- seg21, t ~ 17-20 s, ENGAGED, creep")
    print("   The operator's report was 'I was not really able to introduce grind #1'. That holds")
    print("   for the DISTRIBUTION (p90 328.7, at Kd=2 levels) but NOT for the route's maximum:")
    print("   one engaged creep episode carries an unmistakable 21.5 Hz oscillation. Documented")
    print("   here in raw counts so the claim does not rest on either envelope estimator.\n")
    from scipy.signal import butter, detrend, hilbert, sosfiltfilt

    d = load(21, C4A, PFX)
    t = d["t"]
    fs_bias = fs_of(d)
    fs_true = (len(t) - 1) / (t[-1] - t[0])
    i0 = int(np.searchsorted(t, 18.30))
    xw = np.asarray(d["tq"][i0:i0 + 256], float)
    print(f"   seg21 window t0 = {t[i0]:.2f} s, 256 samples (2.56 s)")
    print(f"      vEgo mean {d['cs_v'][i0:i0 + 256].mean():.2f} m/s   latActive "
          f"{d['cc_lat'][i0:i0 + 256].mean():.2f}   g6806 {d['g6806'][i0:i0 + 256].mean():.2f}   "
          f"|ang| mean {np.abs(d['ang'][i0:i0 + 256]).mean():.1f} deg")
    print(f"      RAW torsion-bar counts: peak-to-peak {np.ptp(xw):.0f}, sd {xw.std():.1f}")
    print(f"      first 24 samples: {np.round(xw[:24]).astype(int).tolist()}")
    print("      ⇒ the sign reverses every ~2.3 samples: ~21 Hz, visible without any transform.")
    taper = np.hanning(256) + 1e-3
    cw = slice(int(0.2 * 256), int(0.8 * 256))
    print(f"\n   {'fs used':>10s} {'win_env p99':>12s} {'butter+hilbert p99':>19s} "
          f"{'top 18-22 peaks':>34s}")
    for FS in (fs_bias, fs_true):
        e1 = G.win_env(xw, FS, 18, 22, taper, cw)
        sos = butter(4, [18 / (FS / 2), 22 / (FS / 2)], btype="band", output="sos")
        env = np.abs(hilbert(sosfiltfilt(sos, detrend(np.asarray(d["tq"], float)))))
        e2 = float(np.percentile(env[i0:i0 + 256], 99))
        P = np.abs(np.fft.rfft((xw - xw.mean()) * np.hanning(256))) ** 2
        f = np.fft.rfftfreq(256, 1 / FS)
        m = (f >= 14) & (f <= 28)
        top = np.argsort(-P[m])[:3]
        print(f"   {FS:10.3f} {e1:12.1f} {e2:19.1f} "
              + "  ".join(f"{f[m][j]:5.2f}Hz" for j in top))
    print("   🛑 THE TWO ENVELOPE ESTIMATORS DISAGREE BY 2.3x ON THIS WINDOW and neither is wrong:")
    print("      `_grind2_lib.win_env` (detrend + Hann + central 60%, taper divided out) reads")
    print("      ~1380; `r47_orchestrator_checks._windows` (4th-order butter + Hilbert) reads ~602.")
    print("      They are DIFFERENT STATISTICS. Every table here uses ONE of them throughout, and")
    print("      the dose table is the butter/Hilbert one, so 602 is the number that belongs in it.")
    print("      Do not compare a number from one table against a number from the other.")

    st = _records()
    r4a = st["V67/r4a"]
    r47 = st[V67_47]
    ec = lambda rs: [r for r in rs if r["eng"] == 1 and 0.3 <= r["v"] <= 5.35]      # noqa: E731
    a, b = G.col(ec(r4a), "e_18-22"), G.col(ec(r47), "e_18-22")
    print(f"\n   ENGAGED-CREEP 18-22 envelope p99 (win_env), route 4a n={len(a)} vs route 47 "
          f"n={len(b)}:")
    for q in (50, 75, 90, 95, 99):
        print(f"      p{q:<3d} 4a {np.percentile(a, q):8.1f}   47 {np.percentile(b, q):8.1f}")
    print(f"      max  4a {a.max():8.1f}   47 {b.max():8.1f}")
    print(f"      windows on 4a above route 47's engaged-creep MAX ({b.max():.0f}): "
          f"{int((a > b.max()).sum())}/{len(a)}")
    ep = Counter()
    for r in ec(r4a):
        if r["e_18-22"] > b.max():
            ep[(r["seg"], r["ep"])] += 1
    print(f"      those windows belong to {len(ep)} distinct engagement episode(s): "
          f"{[ (k[0], v) for k, v in ep.items() ]} (seg, n_windows)")
    print("   ⇒ n = 1 episode. A single burst is NOT an established regression -- it is one")
    print("     observation, and the same n=1 caution retracted the 'V62 new grinding' claim.")
    print("     What it DOES establish is that the route was not incapable of showing grind #1.")


SECTIONS = {"identity": sec_identity, "probe": sec_probe, "flight": sec_flight,
            "exposure": sec_exposure, "grind1": sec_grind1, "grind2": sec_grind2,
            "anomaly": sec_anomaly, "burst": sec_burst}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(SECTIONS)):
        SECTIONS[name]()
    try:
        OUTJSON.write_text(json.dumps(RESULTS, indent=1, default=float))
        print(f"\nwrote {OUTJSON}")
    except Exception as e:
        print(f"(json not written: {e})")
