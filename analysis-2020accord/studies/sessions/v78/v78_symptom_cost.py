#!/usr/bin/env python3
"""DELIVERABLE 5 -- the COST side: can the added steering heaviness be measured on-car?

The firmware side is settled: sustained opposing torque at 20 deg/s is stock 0 · V74 47 · V75 129 ·
new cut 62 counts (`docs/handoffs/2026-08/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md` §4). Those are
AGGREGATOR counts. 🛑 The torsion-bar-to-aggregator unit conversion DOES NOT EXIST (same handoff §7,
the one attempt had coherence 0.072 and was refused), so no predicted bar-count effect size can be
stated and none is invented here. What CAN be done is a like-for-like on-car contrast.

THREE MEASUREMENTS, in increasing directness:
  N  the MANUAL arm -- a NEGATIVE CONTROL that must come back null. V74 and V75 write the engaged
     column only (mode 26); mode 24 is byte-identical between them, and `0xC407E` 511->850 has been
     in force since V73 in BOTH. So any manual difference is route/driver, not the lever.
  A  ENGAGED: sustained bar torque |lowpass(tq, 3 Hz)| inside matched (speed, manoeuvre-rate) cells.
     More opposing damper torque at a given rate has to appear somewhere; the bar is the only
     mechanical channel logged.
  B  ENGAGED: the plant ADMITTANCE, achieved manoeuvre rate per unit of openpilot command
     (|rate_lp| / |e4tq|), in matched speed cells. A heavier rack turns slower for the same demand.
     🛑 CONFOUNDED BY THE CONTROLLER: openpilot is a closed loop, so a slower rack also changes the
     command it asks for. Read B as a description of what the loop delivered, not as a plant gain.

`rate_lp` (mean |lowpass(rate_c, 3 Hz)|) is used throughout, never raw |rate_c| -- the raw channel
contains the oscillation itself and a rate axis built on it partly measures its own outcome
(`_nearcentre_lib.augment_angle`).

Usage:  python studies/sessions/v78/v78_symptom_cost.py   ->  writes _scratch/out/_v78_cost.json
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(78555)
OUT = {}
G.EPKEY = "blk"
V.install_fs()
VB = [(0.5, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
RB = [(0.0, 4.0), (4.0, 10.0), (10.0, 20.0), (20.0, 40.0), (40.0, 1e9)]

with open(ROOT / "_scratch/data/_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)
with open(ROOT / "_scratch/data/_cache_r5e_sym_nearcentre.pkl", "rb") as fh:
    store.update(pickle.load(fh))


def arm(b, eng):
    return [r for r in store[b] if r["eng"] == eng and 0.5 <= r["v"] < 12.5
            and np.isfinite(r.get("rate_lp", np.nan))]


def matched(A, B, keyfn, cells, nb=3000, minn=5):
    """Cell-stratified log-ratio of medians, episode(block)-resampled on both arms."""
    def strat(a, b):
        num = den = 0.0
        nc = 0
        for c in cells:
            xa = [keyfn(r) for r in a if c(r)]
            xb = [keyfn(r) for r in b if c(r)]
            xa = [x for x in xa if np.isfinite(x) and x > 0]
            xb = [x for x in xb if np.isfinite(x) and x > 0]
            if len(xa) < minn or len(xb) < minn:
                continue
            w = 1.0 / (1.0 / len(xa) + 1.0 / len(xb))
            num += w * np.log(np.median(xa) / np.median(xb))
            den += w
            nc += 1
        return (np.exp(num / den) if den else np.nan), nc
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        eb.setdefault(r[G.EPKEY], []).append(r)
    ka, kb = list(ea), list(eb)
    if len(ka) < 2 or len(kb) < 2:
        return np.nan, np.nan, np.nan, 0
    pt, nc = strat(A, B)
    d = np.full(nb, np.nan)
    for i in range(nb):
        aa = [r for j in RNG.integers(0, len(ka), len(ka)) for r in ea[ka[j]]]
        bb = [r for j in RNG.integers(0, len(kb), len(kb)) for r in eb[kb[j]]]
        d[i] = strat(aa, bb)[0]
    return (float(pt), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5)), nc)


CELLS_VR = [(lambda r, v=v, rr=rr: v[0] <= r["v"] < v[1] and rr[0] <= r["rate_lp"] < rr[1])
            for v in VB for rr in RB]
CELLS_V = [(lambda r, v=v: v[0] <= r["v"] < v[1]) for v in VB]

V.hdr("5N. NEGATIVE CONTROL -- the MANUAL arm. Mode 24 is BYTE-IDENTICAL on V74 and V75.")
print("  Anything other than 1.0 here is route/driver, and calibrates how much of the engaged")
print("  contrast below could be the same thing.\n")
for lab, keyfn, cells in (("sustained |bar torque|", lambda r: r["eff"], CELLS_VR),
                          ("manoeuvre rate |rate_lp|", lambda r: r["rate_lp"], CELLS_V)):
    p, lo, hi, nc = matched(arm("V75/r5e", 0), arm("V74/r5d", 0), keyfn, cells)
    OUT[f"manual|{lab}"] = [p, lo, hi, nc]
    print(f"  V75/V74 manual, {lab:<26} {p:7.3f} [{lo:6.3f}, {hi:6.3f}]  {nc} cells"
          + ("   (0 cells -- route 5e has only 26 manual windows / 3 blocks under 12.5 m/s: "
             "THE NEGATIVE CONTROL IS UNPOWERED)" if nc == 0 else ""))
print(f"\n  exposure: V75 manual n={len(arm('V75/r5e', 0))} windows / "
      f"{len({r[G.EPKEY] for r in arm('V75/r5e', 0)})} blocks · "
      f"V74 manual n={len(arm('V74/r5d', 0))} / "
      f"{len({r[G.EPKEY] for r in arm('V74/r5d', 0)})} blocks")

V.hdr("5A. ENGAGED -- sustained bar torque at MATCHED speed and manoeuvre rate")
print("  If the damper's extra opposition is felt, it has to show as more bar torque for the same")
print("  rate at the same speed. Cells are (5 speed bins x 5 rate bins); only cells with >= 5")
print("  windows on BOTH sides enter.\n")
res = {}
for a, b in (("V75/r5e", "V74/r5d"), ("V75/r5e", "V73/r5a"), ("V74/r5d", "V73/r5a"),
             ("V75/r5e", "V72/r59")):
    p, lo, hi, nc = matched(arm(a, 1), arm(b, 1), lambda r: r["eff"], CELLS_VR)
    res[f"{a}/{b}"] = [p, lo, hi, nc]
    print(f"  {a.split('/')[0]:>4} / {b.split('/')[0]:<5} bar torque ratio {p:7.3f} "
          f"[{lo:6.3f}, {hi:6.3f}]   {nc} matched cells")
OUT["engaged_bar_torque"] = res

V.hdr("5B. ENGAGED -- plant ADMITTANCE: achieved manoeuvre rate per unit openpilot command")
print("  |rate_lp| / |e4tq|, matched on speed only (rate is the numerator, so it cannot also be a")
print("  matching variable). 🛑 openpilot is a closed loop: a slower rack changes the command too,")
print("  so this describes what the loop DELIVERED, not a plant gain.\n")
res2 = {}
for a, b in (("V75/r5e", "V74/r5d"), ("V75/r5e", "V73/r5a"), ("V74/r5d", "V73/r5a")):
    for lab, keyfn in (("admittance rate/cmd", lambda r: r["rate_lp"] / max(r["e4"], 1e-6)),
                       ("command |e4tq|", lambda r: r["e4"]),
                       ("rate |rate_lp|", lambda r: r["rate_lp"])):
        p, lo, hi, nc = matched(arm(a, 1), arm(b, 1), keyfn, CELLS_V)
        res2[f"{a}/{b}|{lab}"] = [p, lo, hi, nc]
        print(f"  {a.split('/')[0]:>4} / {b.split('/')[0]:<5} {lab:<22} {p:7.3f} "
              f"[{lo:6.3f}, {hi:6.3f}]   {nc} cells")
    print()
OUT["engaged_admittance"] = res2

V.hdr("5C. THE FIRMWARE-SIDE COST, restated -- and what the logs can and cannot confirm")
print("  sustained opposing torque at 20 deg/s, byte-derived (aggregator counts):")
print("      stock 0   ·   V74 47   ·   V75 129   ·   new cut (C_Y0 566, E_X1 400) 62")
print("  ratios: V75/V74 = 2.74x   ·   new cut / V74 = 1.32x   ·   new cut / V75 = 0.48x")
print("  🛑 There is no bar-count conversion, so 'V75 should feel 2.74x heavier' is NOT a")
print("  supported statement -- 2.74x is the ratio of an internal aggregator quantity.")
OUT["firmware_cost"] = dict(stock=0, v74=47, v75=129, newcut=62,
                            ratio_v75_v74=129 / 47, ratio_new_v74=62 / 47, ratio_new_v75=62 / 129)

with open(ROOT / "_scratch/out/_v78_cost.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_v78_cost.json")
