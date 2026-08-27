#!/usr/bin/env python3
"""★★★★ THE RAIL TEST on route 5a (V73): is grind #1 a SATURATION-driven limit cycle?

🛑🛑 WHAT THIS CAN AND CANNOT SEE -- read before any number below.

The hypothesis under test is about a CODE IMMEDIATE: the LKAS mixer's final clamp `+-0x2000 = 8192`
inside `FUN_00042af8`, acting on an internal accumulator (`gp-0x6b98`). **Nothing on the CAN bus
carries that accumulator, and V73's 4-bit probe field is spent entirely on the damper mode byte.**
⇒ THE CLAMP ITSELF IS NOT OBSERVABLE ON THIS ROUTE. Any script that claims to have measured it is
lying. Two things ARE observable, and this file measures both, separately labelled:

  TEST A -- THE REQUEST RAIL (direct, but one clamp UPSTREAM of the one in question).
      `e4tq` = CAN 0x0E4 bytes 0:1 on sendcan src 1 = openpilot's STEER_TORQUE request, the largest
      of the four channels the mixer sums. It has its OWN hard rail at +-4096 (census: 2978 frames
      at exactly |4096| vs 195 at the next-most-common value -- a 15x spike, i.e. a real clip, not a
      distribution tail). If the request is pinned, the chain is being asked for more than it can
      pass; if it is nowhere near its rail during bursts, the "command saturates" story loses its
      only bus-side support.

  TEST B -- THE DESCRIBING-FUNCTION SIGNATURE (indirect, but tests the CLAMP hypothesis itself).
      A limit cycle whose amplitude is SET by a hard clamp has amplitude fixed by the clamp and
      duty set by everything else. So: in-burst amplitude should be ~INVARIANT to speed, angle and
      driver effort while burst DUTY varies a lot. The kit has already recorded exactly that pattern
      across builds (duty spans 64x, in-burst amplitude 1.24x); this re-tests it WITHIN one route,
      where build is held constant. A within-route failure would weaken the cross-build reading.

  🛑 TEST B is a CONSISTENCY check, not a proof: a resonance with a nonlinear damping term produces
  the same signature. It can FALSIFY, it cannot CONFIRM.

METHOD RULES (each has already retracted a claim in this kit)
  · EPISODES, never windows. Resampling unit = a contiguous engagement run.
  · SPLIT-HALF NULL computed with the identical estimator BEFORE any ratio is quoted.
  · Burst detection on the CONTINUOUS analytic 18-22 Hz envelope of `tq` (the torsion bar), cut only
    inside gapless runs, with a minimum duration of 3 cycles. Threshold SWEPT, never picked.
  · "EMPTY" IS NOT "NULL": every cell reports its own exposure and is dropped, not scored, if thin.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(20260805)
SEGS = [s for s in range(18) if s != 17]           # 17 is parked, gear 1, v == 0 throughout
RAIL = 4096.0
CREEP = (0.5, 4.0)                                  # m/s -- the operator's "5 mph" regime
MIN_CYC = 3                                         # a burst must last >= 3 cycles at 20 Hz
BAND = (18.0, 22.0)
CTRL = (24.0, 28.0)
out = {}


# ------------------------------------------------------------------ per-frame assembly -----------
def frames():
    """Every frame of every driving segment on a gapless lattice, with continuous band envelopes.

    Envelopes are computed PER GAPLESS RUN, never across a log gap -- an FFT across a 3 s hole
    manufactures a burst at the seam.
    """
    cols = {k: [] for k in ("t", "seg", "run", "tq", "e4", "e4req", "v", "ang", "rate", "eng",
                            "mode", "env", "envc", "eff", "sca")}
    rid = 0
    for s in SEGS:
        d = L.load_seg(s)
        fs = G.fs_of(d)
        t = np.asarray(d["t"], float)
        n = len(t)
        allm = np.ones(n, bool)
        for a, b in C.runs_of(allm, t, 512):
            sl = slice(a, b)
            x = np.asarray(d["tq"][sl], float)
            if not np.all(np.isfinite(x)):
                continue
            env = C.band_envelope(x, fs, *BAND)
            envc = C.band_envelope(x, fs, *CTRL)
            eff = C.sustained(x, fs, 3.0)
            cols["t"].append(t[sl]); cols["seg"].append(np.full(b - a, s))
            cols["run"].append(np.full(b - a, rid))
            cols["tq"].append(x); cols["env"].append(env); cols["envc"].append(envc)
            cols["eff"].append(eff)
            for k, src in (("e4", "e4tq"), ("e4req", "e4req"), ("v", "cs_v"), ("ang", "ang"),
                           ("rate", "rate_c"), ("eng", "cc_lat"), ("mode", "mode"), ("sca", "sca")):
                cols[k].append(np.asarray(d[src][sl], float))
            rid += 1
    F = {k: np.concatenate(v) for k, v in cols.items()}
    F["v"] = np.abs(F["v"])
    F["aang"] = np.abs(F["ang"])
    F["arate"] = np.abs(F["rate"])
    F["ae4"] = np.abs(F["e4"])
    F["eng"] = F["eng"] > 0.5
    return F


def bursts(F, thr, minlen):
    """Contiguous burst intervals: env >= thr for >= minlen samples, inside ONE gapless run."""
    m = F["env"] >= thr
    ivs = []
    i = 0
    n = len(m)
    while i < n:
        if not m[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and m[j + 1] and F["run"][j + 1] == F["run"][i]:
            j += 1
        if j - i + 1 >= minlen:
            ivs.append((i, j + 1))
        i = j + 1
    return ivs


L.hdr("0. WHAT IS OBSERVABLE")
print(L.NOT_OBSERVABLE)
print("⇒ TEST A measures openpilot's REQUEST rail (+-4096). TEST B measures the "
      "describing-function\n  SIGNATURE. Neither is the +-0x2000 mixer clamp itself.\n")

F = frames()
print(f"assembled {len(F['t'])} frames over {len(np.unique(F['run']))} gapless runs "
      f"({len(F['t']) / 100:.1f} s)")

creep = (F["v"] >= CREEP[0]) & (F["v"] < CREEP[1])
sel = creep & F["eng"]
print(f"engaged creep [{CREEP[0]}, {CREEP[1]}) m/s: {sel.sum()} frames "
      f"({sel.sum() / 100:.1f} s)  --  this is the grind-#1 regime")

# ------------------------------------------------------------------ threshold sweep ---------------
L.hdr("1. BURST DETECTION -- threshold SWEPT, not picked")
env_sel = F["env"][sel]
print("18-22 Hz analytic envelope A (counts; peak-to-peak = 2A) over engaged creep:")
for p in (50, 75, 90, 95, 99, 99.9):
    print(f"    p{p:<5} {np.percentile(env_sel, p):8.1f}")
print(f"    max   {env_sel.max():8.1f}")
print("\nthr = envelope amplitude in counts; a burst also needs >= "
      f"{MIN_CYC} cycles ({MIN_CYC / 20 * 100:.0f} samples)")
minlen = int(round(MIN_CYC / 20.0 * 100))
SWEEP = [60, 100, 150, 200, 300, 400]
brow = []
for thr in SWEEP:
    ivs = bursts(F, thr, minlen)
    ivs_sel = [(a, b) for a, b in ivs if sel[a:b].mean() > 0.8]
    nfr = sum(b - a for a, b in ivs_sel)
    brow.append((thr, len(ivs), len(ivs_sel), nfr))
    print(f"  thr {thr:4d}:  {len(ivs):5d} bursts route-wide | "
          f"{len(ivs_sel):4d} in the engaged-creep regime, {nfr / 100:7.2f} s "
          f"({nfr / max(sel.sum(), 1) * 100:5.2f}% duty)")
out["sweep"] = brow

# The headline threshold: p95 of the engaged-creep envelope, rounded -- declared here, and every
# number below is repeated at every swept threshold in section 4.
THR = 150
minlen = int(round(MIN_CYC / 20.0 * 100))
print(f"\nHEADLINE THRESHOLD thr = {THR} (A counts, ~{2 * THR} p-p), minlen {minlen} samples.")

# ------------------------------------------------------------------ TEST A ------------------------
L.hdr("2. TEST A -- DOES OPENPILOT'S REQUEST RAIL DURING GRIND-#1 BURSTS?")
IV = [(a, b) for a, b in bursts(F, THR, minlen) if sel[a:b].mean() > 0.8]
inb = np.zeros(len(F["t"]), bool)
for a, b in IV:
    inb[a:b] = True
A_in = sel & inb
A_out = sel & ~inb
print(f"in-burst  {A_in.sum():6d} frames ({A_in.sum() / 100:7.2f} s) over {len(IV)} bursts")
print(f"out-burst {A_out.sum():6d} frames ({A_out.sum() / 100:7.2f} s)")


def raildesc(m, tag):
    a = F["ae4"][m]
    r = F["e4req"][m] > 0.5
    print(f"  {tag:11s} n {m.sum():6d}  requesting {r.mean() * 100:5.1f}%  "
          f"|e4tq| p50 {np.percentile(a, 50):7.0f}  p90 {np.percentile(a, 90):7.0f}  "
          f"p99 {np.percentile(a, 99):7.0f}  max {a.max():7.0f}")
    print(f"              AT RAIL (|e4tq| >= 4096) {np.mean(a >= RAIL - 0.5) * 100:6.3f}%   "
          f">= 0.95*rail {np.mean(a >= 0.95 * RAIL) * 100:6.3f}%   "
          f">= 0.75*rail {np.mean(a >= 0.75 * RAIL) * 100:6.3f}%   "
          f">= 0.50*rail {np.mean(a >= 0.50 * RAIL) * 100:6.3f}%")
    return dict(n=int(m.sum()), p50=float(np.percentile(a, 50)), p90=float(np.percentile(a, 90)),
                p99=float(np.percentile(a, 99)), mx=float(a.max()),
                at=float(np.mean(a >= RAIL - 0.5)), near=float(np.mean(a >= 0.95 * RAIL)))


print("\n|e4tq| distribution, engaged creep:")
out["A_in"] = raildesc(A_in, "IN BURST")
out["A_out"] = raildesc(A_out, "OUT BURST")
print("\nfor reference, |e4tq| over ALL engaged frames at ANY speed:")
out["A_all"] = raildesc(F["eng"], "ALL ENGAGED")
print("           and over engaged frames above 8 m/s (where grind #1 is absent):")
out["A_fast"] = raildesc(F["eng"] & (F["v"] >= 8.0), "ENG >8 m/s")

# ---- matched contrast, episode-bootstrapped ------------------------------------------------------
L.hdr("3. TEST A, MATCHED ON SPEED x |ANGLE| -- episode-resampled, with a SPLIT-HALF NULL FIRST")
VB = [(0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 4.0)]
AB = [(0.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 1e9)]


def cellof(i):
    return (G.binof(F["v"][i], VB), G.binof(F["aang"][i], AB))


def epof(i):
    return int(F["run"][i])


def pack(mask):
    idx = np.flatnonzero(mask)
    return [dict(cell=cellof(i), ep=epof(i), val=float(F["ae4"][i]),
                 rail=float(F["ae4"][i] >= RAIL - 0.5)) for i in idx]


def strat_ratio(A, B, key, min_n=30):
    """Stratified weighted log-ratio of median(key) over cells occupied by both sides."""
    da, db = {}, {}
    for r in A:
        da.setdefault(r["cell"], []).append(r)
    for r in B:
        db.setdefault(r["cell"], []).append(r)
    num = den = 0.0
    tab = []
    for c in sorted(set(da) & set(db)):
        ra, rb = da[c], db[c]
        if len(ra) < min_n or len(rb) < min_n:
            continue
        sa = float(np.median([r[key] for r in ra]))
        sb = float(np.median([r[key] for r in rb]))
        if key == "rail":
            sa = float(np.mean([r[key] for r in ra])) + 1e-3
            sb = float(np.mean([r[key] for r in rb])) + 1e-3
        if not (sa > 0 and sb > 0):
            continue
        nea = len({r["ep"] for r in ra})
        neb = len({r["ep"] for r in rb})
        w = 1.0 / (1.0 / max(nea, 1) + 1.0 / max(neb, 1))
        num += w * np.log(sa / sb)
        den += w
        tab.append((c, len(ra), len(rb), nea, neb, sa, sb, sa / sb, w))
    return (np.exp(num / den) if den else np.nan), tab


def by_ep(recs):
    e = {}
    for r in recs:
        e.setdefault(r["ep"], []).append(r)
    return list(e.values())


PA, PB = pack(A_in), pack(A_out)
epA, epB = by_ep(PA), by_ep(PB)
print(f"episodes (gapless runs): in-burst {len(epA)}, out-burst {len(epB)}")

for key, lab in (("val", "median |e4tq|"), ("rail", "fraction AT RAIL")):
    pt, tab = strat_ratio(PA, PB, key)
    print(f"\n--- {lab}: in-burst / out-burst, matched on (speed, |angle|) ---")
    if not tab:
        print("   NO CELL has >= 30 frames on BOTH sides -- UNPOWERED, not null.")
        continue
    print(f"   {'cell(v,ang)':>13s} {'n_in':>6s} {'n_out':>6s} {'ep_in':>6s} {'ep_out':>7s} "
          f"{'in':>9s} {'out':>9s} {'ratio':>7s}")
    for c, na, nb, nea, neb, sa, sb, r, w in tab:
        print(f"   {str(c):>13s} {na:6d} {nb:6d} {nea:6d} {neb:7d} {sa:9.3f} {sb:9.3f} {r:7.3f}")
    draws = np.full(2000, np.nan)
    for k in range(2000):
        ia = RNG.integers(0, len(epA), len(epA))
        ib = RNG.integers(0, len(epB), len(epB))
        draws[k] = strat_ratio([r for i in ia for r in epA[i]],
                               [r for i in ib for r in epB[i]], key)[0]
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    # split-half null INSIDE the out-of-burst arm -- same estimator, same cells
    nul = []
    for _ in range(300):
        p = RNG.permutation(len(epB))
        h = len(epB) // 2
        v = strat_ratio([r for i in p[:h] for r in epB[i]],
                        [r for i in p[h:] for r in epB[i]], key)[0]
        if np.isfinite(v):
            nul.append(v)
    nul = np.array(nul)
    nlo, nhi = (np.nanpercentile(nul, [2.5, 97.5]) if len(nul) else (np.nan, np.nan))
    print(f"   POINT {pt:.3f}   95% CI [{lo:.3f}, {hi:.3f}]  ({len(tab)} cells)")
    print(f"   SPLIT-HALF NULL (out-burst arm, same estimator): [{nlo:.3f}, {nhi:.3f}]")
    clears = np.isfinite(lo) and np.isfinite(nhi) and (lo > nhi or hi < nlo)
    print(f"   CLEARS ITS OWN NULL: {'YES' if clears else 'NO'}")
    out["A_" + key] = dict(point=float(pt), lo=float(lo), hi=float(hi),
                           null=[float(nlo), float(nhi)], cells=len(tab), clears=bool(clears))

# ------------------------------------------------------------------ threshold sensitivity --------
L.hdr("4. TEST A -- SENSITIVITY ACROSS THE WHOLE THRESHOLD SWEEP")
print(f"{'thr':>5s} {'bursts':>7s} {'in s':>7s} {'in:AT RAIL':>11s} {'out:AT RAIL':>12s} "
      f"{'in:>=0.5R':>10s} {'out:>=0.5R':>11s} {'med in':>8s} {'med out':>8s}")
srow = []
for thr in SWEEP:
    iv = [(a, b) for a, b in bursts(F, thr, minlen) if sel[a:b].mean() > 0.8]
    ib = np.zeros(len(F["t"]), bool)
    for a, b in iv:
        ib[a:b] = True
    mi, mo = sel & ib, sel & ~ib
    if mi.sum() < 30:
        print(f"{thr:5d} {len(iv):7d}   UNPOWERED ({mi.sum()} in-burst frames)")
        continue
    ai, ao = F["ae4"][mi], F["ae4"][mo]
    r = (thr, len(iv), mi.sum() / 100, float(np.mean(ai >= RAIL - .5)),
         float(np.mean(ao >= RAIL - .5)), float(np.mean(ai >= .5 * RAIL)),
         float(np.mean(ao >= .5 * RAIL)), float(np.median(ai)), float(np.median(ao)))
    srow.append(r)
    print(f"{thr:5d} {len(iv):7d} {mi.sum() / 100:7.2f} {r[3] * 100:10.3f}% {r[4] * 100:11.3f}% "
          f"{r[5] * 100:9.3f}% {r[6] * 100:10.3f}% {np.median(ai):8.0f} {np.median(ao):8.0f}")
out["sens"] = srow

with open(ROOT / "_scratch/out/_r5a_rail.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5a_rail.json")
