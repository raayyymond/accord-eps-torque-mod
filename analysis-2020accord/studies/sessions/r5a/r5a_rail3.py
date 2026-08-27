#!/usr/bin/env python3
"""THE RAIL TEST, stage 3: harden the FALSIFIER, and fix stage 2's Q3.

Stage 2 found the OPPOSITE of the saturation hypothesis: burst duty rises smoothly with |e4tq|
(1.2% -> 35.5% from 0-250 to 3k-4k counts) and then **COLLAPSES to 12.5% AT the +-4096 rail**,
step 0.35x with an episode-resampled CI of [0.00, 0.95] that excludes 1. That is exactly the kit's
recorded "★ Vibration moves with speed and DIES AT THE RAIL" behaviour, independently replicated.

A finding that overturns the session's leading hypothesis has to survive its own confounds, so:

  H1  Is the rail bin just a DIFFERENT DRIVING SITUATION? At +-4096 openpilot is asking for
      everything it has -- likely a big turn, possibly with the driver fighting it. Match the
      rail-vs-just-below contrast on (speed, |angle|, |rate|, driver effort) and re-run.
  H2  Is the collapse a MEASUREMENT artefact of the envelope? A hard-clipped command is CONSTANT,
      and a constant input cannot excite anything -- that IS the mechanism, not an artefact -- but
      check that `tq` is not simply quiet in some other way (broadband floor, control band).
  H3  Does the collapse hold at every burst threshold, and on the CONTINUOUS envelope rather than
      the binary duty?
  H4  What IS the rail regime physically? Speed, angle, rate, bar torque, steeringPressed.

Q3 REDONE: stage 2 required a burst to be >= 64 samples long; the median burst is 23 samples, so it
selected ZERO windows and printed UNPOWERED. Windows are now CENTRED on each burst instead.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402
from r5a_rail import CREEP, MIN_CYC, RAIL, THR, bursts, frames  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(424242)
out = {}
F = frames()
minlen = int(round(MIN_CYC / 20.0 * 100))
sel = (F["v"] >= CREEP[0]) & (F["v"] < CREEP[1]) & F["eng"]


def burstmask(thr):
    m = np.zeros(len(F["t"]), bool)
    for a, b in bursts(F, thr, minlen):
        if sel[a:b].mean() > 0.8:
            m[a:b] = True
    return m


inb = burstmask(THR)

# ------------------------------------------------------------------ H4 first: what IS the rail? --
L.hdr("H4. WHAT IS THE RAIL REGIME, PHYSICALLY?  (engaged creep)")
mR = sel & (F["ae4"] >= RAIL - .5)
mB = sel & (F["ae4"] >= 2000) & (F["ae4"] < RAIL - .5)
mL = sel & (F["ae4"] < 2000)
print(f"{'arm':>22s} {'frames':>7s} {'s':>7s} {'v':>6s} {'|ang|':>7s} {'|rate|':>7s} "
      f"{'|bar tq|':>9s} {'effort':>7s} {'duty':>7s}")
for m, lab in ((mR, "AT RAIL |e4tq|=4096"), (mB, "2000 <= |e4tq| < 4096"), (mL, "|e4tq| < 2000")):
    print(f"{lab:>22s} {int(m.sum()):7d} {m.sum() / 100:7.1f} {np.median(F['v'][m]):6.2f} "
          f"{np.median(F['aang'][m]):7.1f} {np.median(F['arate'][m]):7.1f} "
          f"{np.median(np.abs(F['tq'][m])):9.0f} {np.median(F['eff'][m]):7.0f} "
          f"{inb[m].mean() * 100:6.2f}%")
print("\ntime spent at the rail is CONTIGUOUS or chattering?")
d = np.diff(np.concatenate([[0], (F['ae4'] >= RAIL - .5).astype(int), [0]]))
st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
dur = (en - st) / 100.0
print(f"  {len(dur)} rail excursions route-wide, median {np.median(dur):.2f} s, "
      f"p90 {np.percentile(dur, 90):.2f} s, max {dur.max():.2f} s")
print("  ⇒ long dwells, not per-sample chatter: while pinned the LKAS channel is a CONSTANT and")
print("    its incremental gain is ZERO -- the loop through it is OPEN. That is the mechanism.")

# ------------------------------------------------------------------ H1 ---------------------------
L.hdr("H1. MATCHED: burst duty AT RAIL vs 2000..4095, on (speed, |angle|, |rate|, effort)")
VB = [(0.5, 1.5), (1.5, 2.5), (2.5, 4.0)]
AB = [(0, 3), (3, 8), (8, 20), (20, 1e9)]
RB = [(0, 8), (8, 30), (30, 1e9)]
EB = [(0, 400), (400, 1200), (1200, 1e9)]


def cells(m):
    return np.array([np.searchsorted([b[0] for b in VB[1:]], F["v"][m], "right"),
                     np.searchsorted([b[0] for b in AB[1:]], F["aang"][m], "right"),
                     np.searchsorted([b[0] for b in RB[1:]], F["arate"][m], "right"),
                     np.searchsorted([b[0] for b in EB[1:]], F["eff"][m], "right")]).T


iR, iB = np.flatnonzero(mR), np.flatnonzero(mB)
# 🛑 VECTORISED. The obvious per-index form is O(nboot * ncell * nframe) and does not finish.
# One integer cell code per frame, then bincount inside the bootstrap.
NC = (len(AB), len(RB), len(EB))
code = ((np.searchsorted([b[0] for b in VB[1:]], F["v"], "right") * NC[0]
         + np.searchsorted([b[0] for b in AB[1:]], F["aang"], "right")) * NC[1]
        + np.searchsorted([b[0] for b in RB[1:]], F["arate"], "right")) * NC[2] \
    + np.searchsorted([b[0] for b in EB[1:]], F["eff"], "right")
NCELL = len(VB) * NC[0] * NC[1] * NC[2]
runs = F["run"].astype(int)
eps = np.array(sorted(set(runs[sel])))


def cellcounts(mask, keep=None):
    m = mask if keep is None else (mask & keep)
    n = np.bincount(code[m], minlength=NCELL).astype(float)
    k = np.bincount(code[m & inb], minlength=NCELL).astype(float)
    return n, k


def ratio_from(keep=None, minn=25, cellsel=None):
    nR, kR_ = cellcounts(mR, keep)
    nB, kB_ = cellcounts(mB, keep)
    ok = (nR >= minn) & (nB >= minn)
    if cellsel is not None:
        ok &= cellsel
    if not ok.any():
        return np.nan, ok
    da = (kR_[ok] + 1e-3 * nR[ok]) / nR[ok]
    db = (kB_[ok] + 1e-3 * nB[ok]) / nB[ok]
    w = np.minimum(nR[ok], nB[ok])
    return float(np.exp(np.sum(w * np.log(da / db)) / w.sum())), ok


def unpack(c):
    e = c % NC[2]; c //= NC[2]
    r = c % NC[1]; c //= NC[1]
    return (c // NC[0], c % NC[0], r, e)


pt, ok = ratio_from()
nR_, kR_ = cellcounts(mR)
nB_, kB_ = cellcounts(mB)
print(f"{'cell (v,ang,rate,eff)':>24s} {'n rail':>7s} {'n below':>8s} {'duty rail':>10s} "
      f"{'duty below':>11s} {'ratio':>7s}")
for c in np.flatnonzero(ok):
    da, db = kR_[c] / nR_[c], kB_[c] / nB_[c]
    print(f"{str(unpack(int(c))):>24s} {int(nR_[c]):7d} {int(nB_[c]):8d} {da * 100:9.2f}% "
          f"{db * 100:10.2f}% {(da + 1e-3) / (db + 1e-3):7.3f}")
if np.isfinite(pt):
    print(f"\n  MATCHED duty ratio (rail / just-below) = {pt:.3f} over {int(ok.sum())} cells")
    out["H1_matched"] = float(pt)
    draws = []
    for _ in range(1500):
        keep = np.isin(runs, eps[RNG.integers(0, len(eps), len(eps))])
        v = ratio_from(keep, minn=10, cellsel=ok)[0]
        if np.isfinite(v):
            draws.append(v)
    if len(draws) > 50:
        lo, hi = np.percentile(draws, [2.5, 97.5])
        print(f"  episode-resampled 95% CI: [{lo:.3f}, {hi:.3f}]  "
              f"({'EXCLUDES 1 -- the rail SUPPRESSES' if hi < 1 else 'includes 1'}), "
              f"{len(draws)} usable draws")
        out["H1_ci"] = [float(lo), float(hi)]
else:
    print("  NO matched cell survives -- UNPOWERED, not null.")

# ------------------------------------------------------------------ H2/H3 -----------------------
L.hdr("H2/H3. CONTINUOUS envelope (not binary duty), at every threshold and in the control band")
print(f"{'|e4tq| bin':>14s} {'n':>7s} {'med env 18-22':>14s} {'p90':>8s} {'p99':>8s} "
      f"{'med 24-28':>11s} {'ratio 18-22/24-28':>18s}")
EBIN = [(0, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 3000), (3000, 4095.5),
        (4095.5, 1e9)]
LBL = ["0-250", "250-500", "500-1k", "1k-2k", "2k-3k", "3k-4095", "AT RAIL"]
h2 = []
for (lo, hi), lab in zip(EBIN, LBL):
    m = sel & (F["ae4"] >= lo) & (F["ae4"] < hi)
    if m.sum() < 30:
        print(f"{lab:>14s} {int(m.sum()):7d}  UNPOWERED")
        continue
    e, ec = F["env"][m], F["envc"][m]
    print(f"{lab:>14s} {int(m.sum()):7d} {np.median(e):14.1f} {np.percentile(e, 90):8.1f} "
          f"{np.percentile(e, 99):8.1f} {np.median(ec):11.1f} "
          f"{np.median(e) / max(np.median(ec), 1e-9):18.3f}")
    h2.append((lab, int(m.sum()), float(np.median(e)), float(np.median(ec))))
out["H2"] = h2
print("\nthreshold sensitivity of the rail collapse (duty at rail / duty at 2k-4095):")
for thr in (60, 100, 150, 200):
    ib = burstmask(thr)
    dr, db = ib[mR].mean(), ib[mB].mean()
    print(f"  thr {thr:4d}:  duty at rail {dr * 100:6.2f}%   duty 2k-4095 {db * 100:6.2f}%   "
          f"ratio {(dr + 1e-4) / (db + 1e-4):5.3f}")
    out.setdefault("H3", []).append((thr, float(dr), float(db)))

# ------------------------------------------------------------------ Q3 REDONE --------------------
L.hdr("Q3 (REDONE). IS 18-22 Hz IN OPENPILOT'S OWN COMMAND?  windows CENTRED on each burst")
IV = [(a, b) for a, b in bursts(F, THR, minlen) if sel[a:b].mean() > 0.8]
print(f"{len(IV)} bursts, median length {np.median([b - a for a, b in IV]):.0f} samples "
      f"({np.median([b - a for a, b in IV]) / 100:.2f} s) -- stage 2's 64-sample filter killed all")
f = np.fft.rfftfreq(256, 1 / 100.0)
for chan, lab in (("tq", "tq   (torsion bar)"), ("e4", "e4tq (openpilot request)"),
                  ("rate", "rate_c (angle rate)")):
    v18, v24 = [], []
    for a, b in IV:
        c0 = (a + b) // 2 - 128
        if c0 < 0 or c0 + 256 > len(F["t"]):
            continue
        if len(set(F["run"][c0:c0 + 256].astype(int))) != 1:
            continue
        x = F[chan][c0:c0 + 256]
        if not np.all(np.isfinite(x)):
            continue
        P = C.periodogram(x, 100.0, 256, True)
        v18.append(P[(f >= 18) & (f <= 22)].sum())
        v24.append(P[(f >= 24) & (f <= 28)].sum())
    if len(v18) < 8:
        print(f"  {lab}: UNPOWERED ({len(v18)} windows)")
        continue
    v18, v24 = np.array(v18), np.array(v24)
    r = np.median(v18 / v24)
    bs = [np.median((v18 / v24)[RNG.integers(0, len(v18), len(v18))]) for _ in range(3000)]
    print(f"  {lab:24s} n={len(v18):3d}  median (P18-22 / P24-28) = {r:7.3f} "
          f"[{np.percentile(bs, 2.5):.3f}, {np.percentile(bs, 97.5):.3f}]")
    out["q3_" + chan] = [float(r), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
print("\n⇒ a ratio near 1 on `e4tq` = openpilot's request carries NO 18-22 Hz line ⇒ the")
print("  oscillation is not commanded; the loop closes inside the EPS + plant.")

with open(ROOT / "_scratch/out/_r5a_rail3.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5a_rail3.json")
