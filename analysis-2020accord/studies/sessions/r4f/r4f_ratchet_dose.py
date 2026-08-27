#!/usr/bin/env python3
"""studies/sessions/r4f/r4f_ratchet_dose.py -- is the ~7.5 Hz RATCHET dose-responsive in the r24 torque-rate lane?

THE QUESTION. Every build since V39 has moved the same lane. The kit has a four-point dose ladder
for GRIND #1 (18-22 Hz: 1.50 at Kd=0 / 1.00 / 0.55 at V67 / 0.39 at Kd=2) and has never built one
for the RATCHET. V69 adds a fifth rung -- 4x at creep -- so the ladder is now:

    build / route   engaged-creep r24 multiplier            what moved it
    V61 / r31       0.00x   (lane KILLED at both taps)      0x3AB6C + 0x3AC16 reg1 -> r0
    V59 / r2c       1.00x   (stock)                         --
    V64 / r35       1.00x   (V59's cals; detector never armed)
    V62 / r37       2.00x   ungated, manual too             sar 0xa -> 0x9
    V65 / r3a       2.00x   ungated, manual too             carries V62's sar
    V67 / r47       2.00x   ENGAGED only (LKAS-gated)       0x3AA96 repoint + 0xC6446 = 5244
    V68 / r4c,r4e   2.00x   ENGAGED only (V67's path, byte-identical)
    V69 / r4f       4.00x   ungated, rolls to 1.000x >= 50 km/h    gain_B rec0/rec1 x4

🛑 THE CONFOUND THIS FILE EXISTS TO CONTROL. On route 4f the 6-9 Hz line is overwhelmingly a
LARGE-COMMAND phenomenon: engaged windows carrying the line have openpilot's |command| p99 at its
+/-4096 rail with a median rail duty of 0.285, against 840 counts and 0.000 for engaged windows
without it (`studies/sessions/r4f/r4f_ratchet_conditions.py`, C2). Routes differ enormously in how much railed-command
creep they contain, so an unmatched build comparison measures ROUTE CONTENT, not dose. Every
comparison here is nearest-neighbour matched on (|v|, command-rail duty) and reports the achieved
match quality.

🛑 METHOD. Episode-clustered bootstrap (episodes = contiguous window blocks within a segment),
never window bootstrap. A split-half null is computed from the REFERENCE arm alone, first. A
24-27 Hz negative-control band is carried through every comparison: it must stay near 1.0 or the
result is broadband, not a ratchet effect.
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
import glob
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
CTRL = (24.0, 27.0)
RAIL = 4000
CREEP = 4.0
HANDS_OFF = 300.0

ARMS = [
    ("V61 r31  Kd 0.00x", "_scratch/cache/r31", "r31s", 0.00),
    ("V59 r2c  Kd 1.00x", "_scratch/cache/r2c", "r2cs", 1.00),
    ("V64 r35  Kd 1.00x", "_scratch/cache/r35", "r35s", 1.00),
    ("V62 r37  Kd 2.00x", "_scratch/cache/r37", "r37s", 2.00),
    ("V65 r3a  Kd 2.00x", "_scratch/cache/r3a", "r3as", 2.00),
    ("V65 r3b  Kd 2.00x", "_scratch/cache/r3b", "r3bs", 2.00),
    ("V67 r47  Kd 2.00x", "_scratch/cache/r47", "r47s", 2.00),
    ("V68 r4c  Kd 2.00x", "_scratch/cache/v68", "4cs", 2.00),
    ("V68 r4e  Kd 2.00x", "_scratch/cache/v68", "4es", 2.00),
    ("V69 r4f  Kd 4.00x", "_scratch/cache/r4f", "r4fs", 4.00),
]


def hdr(s):
    print("\n" + "=" * 102)
    print(s)
    print("=" * 102)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def cell(name, cache, pfx, dose):
    """Engaged-creep hands-off windows for one route, with the command co-factor."""
    out = []
    for p in sorted(glob.glob(str(ROOT / cache / f"{pfx}*.npz"))):
        stem = Path(p).stem
        if not stem[len(pfx):].isdigit():
            continue
        seg = int(stem[len(pfx):])
        d = {k: v for k, v in np.load(p).items()}
        if "tq" not in d or "e4tq" not in d or len(d["t"]) < 2 * NFFT:
            continue
        t = d["t"]
        fs = (len(t) - 1) / (t[-1] - t[0])
        eff = np.abs(sustained(d["tq"], fs))
        sel = (d["cc_lat"] > 0.5) & (np.abs(d["cs_v"]) <= CREEP) & (eff < HANDS_OFF)
        idx = np.flatnonzero(sel)
        if not len(idx):
            continue
        runs, a = [], idx[0]
        for i in range(1, len(idx)):
            if idx[i] != idx[i - 1] + 1:
                runs.append((a, idx[i - 1] + 1))
                a = idx[i]
        runs.append((a, idx[-1] + 1))
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = band_envelope(d["tq"], fs, *RATCH)
        envc = band_envelope(d["tq"], fs, *CTRL)
        for ri, (a, b) in enumerate(runs):
            for i in range(a, b - NFFT + 1, NFFT):
                P = periodogram(d["tq"][i:i + NFFT], fs, NFFT)
                if P is None:
                    continue
                fb, pb = peak_prom(f, P, *RATCH)
                _, pc = peak_prom(f, P, *CTRL)
                w = slice(i, i + NFFT)
                out.append(dict(tag=name, dose=dose, ep=(seg, ri),
                                fb=fb, pb=pb, pc=pc,
                                env=float(np.percentile(env[w], 99)),
                                envc=float(np.percentile(envc[w], 99)),
                                v=float(np.abs(d["cs_v"][w]).mean()),
                                rail=float(np.mean(np.abs(d["e4tq"][w]) >= RAIL)),
                                e4=float(np.percentile(np.abs(d["e4tq"][w]), 99)),
                                eff=float(np.median(eff[w]))))
    return out


def groups(rs):
    g = {}
    for r in rs:
        g.setdefault((r["tag"], r["ep"]), []).append(r)
    return list(g.values())


def boot_pairs(pairs, key, n=4000):
    """Episode-clustered bootstrap of median(A)/median(B) over matched pairs.

    Resampling is on the TEST arm's episodes; each drawn test window carries its own matched
    control, so the pairing survives the resample.
    """
    g = {}
    for a, b in pairs:
        g.setdefault(a["ep"], []).append((a, b))
    ks = list(g)
    if len(ks) < 2:
        return np.nan, np.nan, np.nan
    vals = []
    for _ in range(n):
        pick = [x for j in np.random.randint(0, len(ks), len(ks)) for x in g[ks[j]]]
        A = [p[0][key] for p in pick if np.isfinite(p[0][key])]
        B = [p[1][key] for p in pick if np.isfinite(p[1][key])]
        if A and B and np.median(B) > 0:
            vals.append(np.median(A) / np.median(B))
    obs = np.median([p[0][key] for p in pairs]) / max(np.median([p[1][key] for p in pairs]), 1e-9)
    return obs, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def split_half(rs, key, n=4000):
    eps = [e for e in groups(rs) if len(e) >= 2]
    if len(eps) < 2:
        return np.nan, np.nan
    vals = []
    for _ in range(n):
        A, B = [], []
        for j in np.random.randint(0, len(eps), len(eps)):
            e = eps[j]
            m = len(e) // 2
            A += [x[key] for x in e[:m]]
            B += [x[key] for x in e[m:]]
        A = [x for x in A if np.isfinite(x)]
        B = [x for x in B if np.isfinite(x)]
        if A and B and np.median(B) > 0:
            vals.append(np.median(A) / np.median(B))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def match(A, B, dv=0.7, drail=0.15):
    """Nearest neighbour in (|v|, rail duty). Unmatched test windows are DROPPED and counted."""
    vb, rb = col(B, "v"), col(B, "rail")
    pairs, drop = [], 0
    for a in A:
        c = ((vb - a["v"]) / dv) ** 2 + ((rb - a["rail"]) / drail) ** 2
        j = int(np.argmin(c))
        if abs(vb[j] - a["v"]) <= dv and abs(rb[j] - a["rail"]) <= drail:
            pairs.append((a, B[j]))
        else:
            drop += 1
    return pairs, drop


def main():
    np.random.seed(20260804)
    print(__doc__)
    data = {}
    hdr("D1.  EXPOSURE -- engaged + |v| <= 4 m/s + hands-off, per route. Read this FIRST.")
    print(f"   {'arm':20s} {'eps':>4s} {'win':>5s} {'secs':>6s} {'|v| p50':>8s} "
          f"{'rail p50':>9s} {'rail mean':>10s} {'|cmd|p99 p50':>13s} {'6-9 env p50':>12s} "
          f"{'24-27 env p50':>14s}")
    for name, cache, pfx, dose in ARMS:
        r = cell(name, cache, pfx, dose)
        data[name] = r
        if not r:
            print(f"   {name:20s}   -- no cell windows")
            continue
        print(f"   {name:20s} {len(groups(r)):4d} {len(r):5d} {len(r) * 2.56:6.1f} "
              f"{np.median(col(r, 'v')):8.2f} {np.median(col(r, 'rail')):9.3f} "
              f"{np.mean(col(r, 'rail')):10.3f} {np.median(col(r, 'e4')):13.0f} "
              f"{np.median(col(r, 'env')):12.0f} {np.median(col(r, 'envc')):14.0f}")
    print("\n   🛑 The rail columns are the confound. Routes with little railed-command creep")
    print("      cannot express the phenomenon at all, whatever their dose.")

    ref = [x for n in ("V59 r2c  Kd 1.00x", "V64 r35  Kd 1.00x") for x in data.get(n, [])]
    for r in ref:
        r = r
    hdr("D2.  MATCHED DOSE LADDER -- every arm against the pooled Kd = 1.00x reference")
    print(f"   reference = V59 r2c + V64 r35, {len(ref)} windows, "
          f"{len(groups(ref))} episodes, {len(ref) * 2.56:.0f} s")
    nl, nh = split_half(ref, "env")
    print(f"   SPLIT-HALF NULL from the reference arm alone: [{nl:.2f}, {nh:.2f}]")
    print("   ⇒ any ratio whose CI overlaps that interval is NOT an established effect.\n")
    print(f"   {'arm':20s} {'dose':>5s} {'pairs':>6s} {'drop':>5s} {'|dv|':>5s} {'|drail|':>7s} "
          f"{'6-9 ratio':>10s} {'CI':>18s} {'24-27 ratio':>12s} {'CI':>18s}")
    for name, cache, pfx, dose in ARMS:
        A = data.get(name)
        if not A or name in ("V59 r2c  Kd 1.00x", "V64 r35  Kd 1.00x"):
            continue
        pairs, drop = match(A, ref)
        if len(pairs) < 4:
            print(f"   {name:20s} {dose:5.2f} {len(pairs):6d} {drop:5d}   "
                  "(too few matched pairs)")
            continue
        dv = np.median([abs(a["v"] - b["v"]) for a, b in pairs])
        dr = np.median([abs(a["rail"] - b["rail"]) for a, b in pairs])
        o, l, h = boot_pairs(pairs, "env")
        oc, lc, hc = boot_pairs(pairs, "envc")
        print(f"   {name:20s} {dose:5.2f} {len(pairs):6d} {drop:5d} {dv:5.2f} {dr:7.3f} "
              f"{o:10.2f} [{l:7.2f},{h:8.2f}] {oc:12.2f} [{lc:7.2f},{hc:8.2f}]")
    print("\n   6-9 ratio = this arm's 6-9 Hz envelope p99 / the matched Kd=1 windows'.")
    print("   24-27 ratio is the NEGATIVE CONTROL: a band-specific effect keeps it near 1.0.")

    hdr("D3.  THE SAME LADDER, RESTRICTED TO RAILED-COMMAND WINDOWS (rail duty >= 0.10)")
    print("   This is the regime where the ratchet actually lives. It costs most of the")
    print("   exposure, which is exactly why D2 is reported first and this second.\n")
    refR = [r for r in ref if r["rail"] >= 0.10]
    print(f"   reference (Kd = 1.00x, railed): {len(refR)} windows, "
          f"{len(groups(refR))} episodes, {len(refR) * 2.56:.0f} s")
    if len(refR) >= 4:
        nl2, nh2 = split_half(refR, "env")
        print(f"   split-half null: [{nl2:.2f}, {nh2:.2f}]\n")
        print(f"   {'arm':20s} {'dose':>5s} {'win':>5s} {'pairs':>6s} {'6-9 ratio':>10s} "
              f"{'CI':>18s} {'24-27 ratio':>12s}")
        for name, cache, pfx, dose in ARMS:
            A = [r for r in data.get(name, []) if r["rail"] >= 0.10]
            if name in ("V59 r2c  Kd 1.00x", "V64 r35  Kd 1.00x") or not A:
                continue
            pairs, drop = match(A, refR)
            if len(pairs) < 4:
                print(f"   {name:20s} {dose:5.2f} {len(A):5d} {len(pairs):6d}   "
                      "(too few matched pairs)")
                continue
            o, l, h = boot_pairs(pairs, "env")
            oc, _, _ = boot_pairs(pairs, "envc")
            print(f"   {name:20s} {dose:5.2f} {len(A):5d} {len(pairs):6d} {o:10.2f} "
                  f"[{l:7.2f},{h:8.2f}] {oc:12.2f}")
    else:
        print("   🛑 THE Kd = 1.00x REFERENCE HAS NO RAILED-COMMAND CREEP WINDOWS.")
        print("      ⇒ THE DOSE LADDER CANNOT BE BUILT IN THE REGIME WHERE THE RATCHET LIVES.")
        print("      Any ladder computed outside it is comparing quiet windows and will read ~1.")
        print("      Per-arm railed-window exposure, so the gap is visible rather than asserted:")
        for name, cache, pfx, dose in ARMS:
            A = [r for r in data.get(name, []) if r["rail"] >= 0.10]
            tot = data.get(name, [])
            print(f"      {name:20s} dose {dose:4.2f}   railed {len(A):4d} / {len(tot):4d} "
                  f"windows = {len(A) * 2.56:6.1f} s   "
                  f"6-9 env p50 {np.median(col(A, 'env')) if A else float('nan'):7.0f}")

    hdr("D4.  WITHIN-ROUTE 4f -- V69's OWN speed-shaped dose is a ladder, but a confounded one")
    print("   V69's multiplier: 4.000x to 10 km/h, 3.307 @20, 2.578 @30, 1.808 @40, 1.000x")
    print("   at and above 50 km/h. Speed therefore IS dose on this route -- and speed is also")
    print("   plant, command size and rail duty, so this is reported as a description, NOT as a")
    print("   dose-response. It cannot separate the lane from the regime.")
    r4f = cell("V69 r4f  Kd 4.00x", "_scratch/cache/r4f", "r4fs", 4.0)
    # recompute over ALL engaged windows, not just creep, to see the whole speed axis
    print(f"\n   {'|v| m/s':>10s} {'V69 mult':>9s} {'n':>4s} {'rail p50':>9s} "
          f"{'6-9 env p50':>12s} {'6-9 prom p50':>13s} {'24-27 env p50':>14s}")
    allw = []
    for p in sorted(glob.glob(str(ROOT / "_scratch/cache/r4f" / "r4fs*.npz"))):
        if not Path(p).stem[4:].isdigit():
            continue
        d = {k: v for k, v in np.load(p).items()}
        t = d["t"]
        fs = (len(t) - 1) / (t[-1] - t[0])
        eff = np.abs(sustained(d["tq"], fs))
        lat = d["cc_lat"] > 0.5
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = band_envelope(d["tq"], fs, *RATCH)
        envc = band_envelope(d["tq"], fs, *CTRL)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            if lat[w].mean() < 0.9:
                continue
            P = periodogram(d["tq"][w], fs, NFFT)
            if P is None:
                continue
            _, pb = peak_prom(f, P, *RATCH)
            allw.append(dict(v=float(np.abs(d["cs_v"][w]).mean()), pb=pb,
                             env=float(np.percentile(env[w], 99)),
                             envc=float(np.percentile(envc[w], 99)),
                             rail=float(np.mean(np.abs(d["e4tq"][w]) >= RAIL)),
                             eff=float(np.median(eff[w]))))
    mult = [(0, 2.78, 4.00), (2.78, 5.56, 3.31), (5.56, 8.33, 2.58), (8.33, 11.1, 1.81),
            (11.1, 13.9, 1.40), (13.9, 40.0, 1.00)]
    for lo, hi, m in mult:
        g = [r for r in allw if lo <= r["v"] < hi]
        if not g:
            continue
        print(f"   {lo:4.1f}-{hi:<5.1f} {m:9.2f} {len(g):4d} {np.median(col(g, 'rail')):9.3f} "
              f"{np.median(col(g, 'env')):12.0f} {np.nanmedian(col(g, 'pb')):13.1f} "
              f"{np.median(col(g, 'envc')):14.0f}")
    print("\n   ⇒ the 6-9 Hz level FALLS monotonically with speed while V69's damping dose ALSO")
    print("     falls. That is the WRONG sign for 'more damping suppresses it', but rail duty")
    print("     and command size fall with speed too, so the comparison is uninterpretable as a")
    print("     dose test. Stated, not spun.")


if __name__ == "__main__":
    main()
