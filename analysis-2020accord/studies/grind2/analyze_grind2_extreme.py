#!/usr/bin/env python3
"""The EXTREME tail of grind #2: is the >400-count 30-49 Hz burst a build effect or exposure?

The censused fact that forced this script: on the matched-cell MEDIAN the 30-49 Hz band is not
elevated on Kd=2 at all -- but no window on any Kd<=1 route reaches 430 counts, while all three
Kd=2 routes carry windows at 2,800-4,000. A rare violent event does not move a median. The Kd=2
drives were also DELIBERATELY provoking the symptom, so they visited far more of the high-effort /
high-steering-rate creep regime. This script separates the two explanations.

Instruments (each chosen because a simpler one failed here):
  ZIGZAG   The FFT-free second method. Count of sign-alternating turning points with
           min(|d1|,|d2|) > 800 counts. 🛑 The obvious detector -- count of |d(tq)| > 1500 --
           is NOT frequency selective: V61's 18 Hz mode at +/-2000 counts has a max slew of
           ~2,260 counts/sample and tops that census on every build, which inverted the ranking.
           Requiring a sign REVERSAL on both sides makes it selective for content near fs/2.
  BLOCKS   The exact test counts ~10 s BLOCKS containing at least one burst, not windows. Windows
           inside one burst are the same physical event.
  HEADROOM What did each route actually visit? An effect that lives only beyond the control
           routes' exposure is UNTESTED, not established.
  CONTROL CHANNEL  `ang` (0x14A steering angle) is read in the same 30-49 Hz band. It is a
           different sensor on a different CAN message, so it separates a real mechanical
           oscillation from a torsion-bar / EPS telemetry artifact.

Usage:  python studies/grind2/analyze_grind2_extreme.py
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_grind2_records.pkl"
OUTJSON = HERE / "_scratch/out/_grind2_extreme.json"
RNG = np.random.default_rng(20260801)
BURST = 400.0        # counts of 30-49 Hz envelope p99 -- above every Kd<=1 window ever recorded
ZTHR = 8             # zigzag turning points per 2.56 s window


def fisher2x2(a, b, c, d):
    """Two-sided Fisher exact on [[a,b],[c,d]] by exact hypergeometric enumeration."""
    from math import comb
    n = a + b + c + d
    r1, c1 = a + b, a + c
    def pr(k):
        return comb(r1, k) * comb(n - r1, c1 - k) / comb(n, c1)
    p0 = pr(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return float(sum(pr(k) for k in range(lo, hi + 1) if pr(k) <= p0 * (1 + 1e-9)))


def block_table(rs, key, thr):
    """(blocks with >=1 exceedance, total blocks)."""
    blk = {}
    for r in rs:
        blk[r["blk"]] = blk.get(r["blk"], False) or (r[key] > thr)
    return sum(blk.values()), len(blk)


def main():
    G.EPKEY = "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
    out = {}

    # ================================================================ headroom ===================
    G.hdr("HEADROOM.  What did each route actually VISIT?")
    print(f"  {'build':10s} {'kd':>3s} {'nwin':>5s} | {'eff p50':>8s} {'p90':>7s} {'p99':>7s} "
          f"{'max':>7s} | {'rate p50':>8s} {'p90':>7s} {'p99':>7s} {'max':>7s} | "
          f"{'PROVOCATION cell n':>18s}")
    for b in G.ORDER:
        rs = store.get(b, [])
        e, ra = G.col(rs, "eff"), G.col(rs, "rate")
        n = sum(1 for r in rs if r["v"] < 4 and r["eff"] > 1500 and r["rate"] > 60)
        print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} {len(rs):5d} | "
              f"{np.percentile(e, 50):8.0f} {np.percentile(e, 90):7.0f} "
              f"{np.percentile(e, 99):7.0f} {e.max():7.0f} | "
              f"{np.percentile(ra, 50):8.1f} {np.percentile(ra, 90):7.1f} "
              f"{np.percentile(ra, 99):7.1f} {ra.max():7.1f} | {n:18d}")

    # ================================================================ census =====================
    G.hdr(f"CENSUS.  Whole-route, no operator recollection anywhere in it.\n"
          f"  BURST = 30-49 Hz leakage-controlled envelope p99 > {BURST:.0f} counts.\n"
          f"  ZIG   = >= {ZTHR} large sign-alternating turning points in the 2.56 s window "
          f"(FFT-free).")
    print(f"  {'build':10s} {'kd':>3s} {'nwin':>5s} {'nblk':>5s} | {'E30-49 p99':>10s} "
          f"{'max':>8s} | {'burst win':>10s} {'burst blk':>10s} | {'zig p99':>7s} {'zig max':>7s} "
          f"{'ZIG win':>8s}")
    cen = {}
    for b in G.ORDER:
        rs = store.get(b, [])
        e = G.col(rs, "e_30-49")
        z = G.col(rs, "zig800")
        nb, tb = block_table(rs, "e_30-49", BURST)
        cen[b] = dict(n=len(rs), nblk=tb, burst_win=int((e > BURST).sum()), burst_blk=nb,
                      mx=float(e.max()), zig=int((z >= ZTHR).sum()))
        print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} {len(rs):5d} {tb:5d} | "
              f"{np.percentile(e, 99):10.1f} {e.max():8.1f} | "
              f"{int((e > BURST).sum()):4d}/{len(rs):<5d} {nb:4d}/{tb:<5d} | "
              f"{np.percentile(z, 99):7.1f} {z.max():7.0f} {int((z >= ZTHR).sum()):4d}/{len(rs):<4d}")
    out["census"] = cen

    # ================================================================ exact tests ================
    G.hdr("EXACT TEST at the BLOCK level (a burst that spans 3 windows is ONE event).")
    for lbl, key, thr in (("30-49 envelope > 400", "e_30-49", BURST),
                          (f"zigzag >= {ZTHR} (FFT-free)", "zig800", ZTHR - 0.5)):
        print(f"\n  criterion: {lbl}")
        for arm, sel in (("WHOLE ROUTE", lambda r: True),
                         ("PROVOCATION  v<4, eff>=1500, rate>=60",
                          lambda r: r["v"] < 4 and r["eff"] >= 1500 and r["rate"] >= 60),
                         ("SOFT PROVOC. v<4, eff>=1000, rate>=40",
                          lambda r: r["v"] < 4 and r["eff"] >= 1000 and r["rate"] >= 40),
                         ("PROVOC. ENGAGED",
                          lambda r: r["eng"] == 1 and r["v"] < 4 and r["eff"] >= 1000
                          and r["rate"] >= 40),
                         ("PROVOC. MANUAL (LKAS OFF)",
                          lambda r: r["eng"] == 0 and r["v"] < 4 and r["eff"] >= 1000
                          and r["rate"] >= 40)):
            r1 = [r for b in G.DOSE[0.0] + G.DOSE[1.0] for r in store[b] if sel(r)]
            r2 = [r for b in G.DOSE[2.0] for r in store[b] if sel(r)]
            a1, n1 = block_table(r1, key, thr)
            a2, n2 = block_table(r2, key, thr)
            if min(n1, n2) < 3:
                print(f"    {arm:38s} too few blocks ({n1}/{n2})")
                continue
            p = fisher2x2(a2, n2 - a2, a1, n1 - a1)
            print(f"    {arm:38s} Kd<=1 {a1:3d}/{n1:3d} blocks   Kd=2 {a2:3d}/{n2:3d} blocks   "
                  f"Fisher p = {p:.4g}")

    # per-route, so no single route carries the result
    print("\n  per-route, PROVOCATION cell (v<4, eff>=1000, rate>=40), 30-49 env > 400:")
    print(f"    {'build':10s} {'kd':>3s} {'blocks':>7s} {'burst blk':>10s} {'burst win':>10s} "
          f"{'max env':>8s} {'max zig':>8s}")
    for b in G.ORDER:
        rs = [r for r in store[b] if r["v"] < 4 and r["eff"] >= 1000 and r["rate"] >= 40]
        if not rs:
            continue
        nb, tb = block_table(rs, "e_30-49", BURST)
        e = G.col(rs, "e_30-49")
        print(f"    {b:10s} {G.BUILDS[b]['kd']:3.0f} {tb:7d} {nb:10d} "
              f"{int((e > BURST).sum()):4d}/{len(rs):<5d} {e.max():8.1f} "
              f"{G.col(rs, 'zig800').max():8.0f}")

    # ================================================================ covariate curves ===========
    G.hdr("BURST INCIDENCE vs THE COVARIATE.  Curves that OVERLAY => exposure explains it.\n"
          "Curves that SEPARATE at matched covariate => firmware. '.' = fewer than 8 windows.")
    RATEB = [(0, 20), (20, 50), (50, 80), (80, 120), (120, 180), (180, 1e9)]
    EFFB = [(0, 500), (500, 1000), (1000, 1500), (1500, 2000), (2000, 2500), (2500, 1e9)]
    for nm, bins, key, extra in (("STEERING RATE (deg/s), v < 4 m/s", RATEB, "rate",
                                  lambda r: r["v"] < 4),
                                 ("DRIVER EFFORT (counts), v < 4 m/s", EFFB, "eff",
                                  lambda r: r["v"] < 4)):
        print(f"\n  P(30-49 env > {BURST:.0f}) by {nm}:")
        print(f"  {'build':10s} {'kd':>3s} | " +
              " ".join(f"{f'{lo:g}-{hi:g}':>14s}" for lo, hi in bins))
        for b in G.ORDER:
            cells = []
            for lo, hi in bins:
                rs = [r for r in store[b] if extra(r) and lo <= r[key] < hi]
                cells.append(f"{'.':>14s}" if len(rs) < 8 else
                             f"{np.mean(G.col(rs, 'e_30-49') > BURST):6.3f}(n{len(rs):4d})")
            print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} | " + " ".join(cells))

    # ================================================================ control channel ============
    G.hdr("CONTROL CHANNEL.  `ang` = 0x14A steering angle -- a DIFFERENT sensor on a DIFFERENT CAN\n"
          "message. If the burst is a torsion-bar/EPS telemetry artifact it cannot appear here.")
    bw = [r for b in G.DOSE[2.0] for r in store[b] if r["e_30-49"] > BURST]
    qw = [r for b in G.DOSE[2.0] for r in store[b] if r["e_30-49"] < 150]
    k1 = [r for b in G.DOSE[0.0] + G.DOSE[1.0] for r in store[b]]
    print(f"  {'population':38s} {'n':>5s} {'ang 30-49 med':>14s} {'p90':>8s} {'max':>8s} "
          f"{'ang 1-10 med':>13s}")
    for nm, rs in (("Kd=2 BURST windows (E30-49>400)", bw),
                   ("Kd=2 quiet windows (E30-49<150)", qw),
                   ("every Kd<=1 window", k1),
                   ("Kd<=1, top decile of its own E30-49",
                    sorted(k1, key=lambda r: -r["e_30-49"])[:max(1, len(k1) // 10)])):
        if not rs:
            continue
        a = G.col(rs, "ang_hf")
        print(f"  {nm:38s} {len(rs):5d} {np.median(a):14.3f} {np.percentile(a, 90):8.3f} "
              f"{a.max():8.3f} {np.median(G.col(rs, 'ang_lf')):13.2f}")
    print("\n  ang is quantised at 0.1 deg => a 30-49 Hz quantisation floor of ~0.03 deg. Anything")
    print("  above ~0.1 deg is real wheel motion, not sensor noise.")
    out["angctl"] = dict(burst_med=float(np.median(G.col(bw, "ang_hf"))) if bw else None,
                         kd1_med=float(np.median(G.col(k1, "ang_hf"))),
                         kd1_max=float(G.col(k1, "ang_hf").max()))

    # ================================================================ dose-response, tail ========
    G.hdr("DOSE-RESPONSE OF THE TAIL.  Kd = 0 / 1 / 2, inside the SOFT PROVOCATION cell\n"
          "(v<4, eff>=1000, rate>=40) which all three doses populate.")
    print(f"  {'dose':6s} {'routes':26s} {'nwin':>5s} {'nblk':>5s} {'E p50':>7s} {'p90':>8s} "
          f"{'p99':>8s} {'max':>8s} {'burst blk':>10s} {'zigmax':>7s}")
    dose = {}
    for k in (0.0, 1.0, 2.0):
        rs = [r for b in G.DOSE[k] for r in store[b]
              if r["v"] < 4 and r["eff"] >= 1000 and r["rate"] >= 40]
        e = G.col(rs, "e_30-49")
        nb, tb = block_table(rs, "e_30-49", BURST)
        dose[k] = dict(n=len(rs), nblk=tb, p90=float(np.percentile(e, 90)), mx=float(e.max()),
                       burst_blk=nb)
        print(f"  Kd={k:.0f}  {','.join(G.DOSE[k]):26s} {len(rs):5d} {tb:5d} "
              f"{np.median(e):7.1f} {np.percentile(e, 90):8.1f} {np.percentile(e, 99):8.1f} "
              f"{e.max():8.1f} {nb:4d}/{tb:<5d} {G.col(rs, 'zig800').max():7.0f}")
    out["dose_tail"] = dose

    # and the 18-22 Hz mode over the same three doses in the same cell, for the contrast
    print(f"\n  the SAME cell, 18-22 Hz (grind #1) for contrast:")
    print(f"  {'dose':6s} {'nwin':>5s} {'E p50':>8s} {'p90':>8s} {'max':>8s}")
    for k in (0.0, 1.0, 2.0):
        rs = [r for b in G.DOSE[k] for r in store[b]
              if r["v"] < 4 and r["eff"] >= 1000 and r["rate"] >= 40]
        e = G.col(rs, "e_18-22")
        print(f"  Kd={k:.0f}  {len(rs):5d} {np.median(e):8.1f} {np.percentile(e, 90):8.1f} "
              f"{e.max():8.1f}")

    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
