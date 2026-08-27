#!/usr/bin/env python3
"""T4 -- THE POWER BUDGET, SPEED-MATCHED, AND WHAT THE DATA CANNOT DECIDE.

Three things, in order of how load-bearing they are:

  1. SPEED-MATCHED per-build coherence.  T1 found the 26-31 Hz cmd<->bar coherence is a V80
     phenomenon (g2 0.78) and is AT THE NULL FLOOR on V81 and V83a (0.03-0.04).  Four routes with
     different speed distributions cannot be compared raw --
     `memory/accord-averaged-spectrum-needs-matched-speed-distributions`: a moving wheel order
     manufactures an "only on route X" line, and the band-centre test is NOT sufficient.  So the
     comparison is redone on a COMMON speed support with a per-episode census printed.

  2. THE COHERENT / INCOHERENT SPLIT.  g2*Syy is the bar power linearly predictable from the
     command; (1-g2)*Syy is the part NO openpilot-side story can explain, whichever way the arrow
     points.  That second number is the one a firmware fix has to address.

  3. 🛑 WHAT THIS DATA CANNOT DECIDE, stated explicitly rather than papered over.
     The forward path G (command -> bar) is NOT IDENTIFIABLE from closed-loop data when the
     disturbance dominates: H1 -> 1/C, and every attempt to read G off it returns the controller's
     inverse instead.  The low-frequency band does not rescue it either -- measured g2(cmd->bar) =
     0.011 and g2(cmd->ang) = 0.033 at 0.4-2 Hz, i.e. the loop is TIGHT there and H1 is 1/C at low
     frequency too.  Identifying G requires an EXOGENOUS excitation uncorrelated with the bar --
     a dither.  openpilot may not be modified (`memory/feedback-no-openpilot-side-modifications`),
     so the only admissible version is a FIRMWARE-side dither, which is a separate build.

Writes `_scratch/cache/loop_op/t4_budget.json`.
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

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VBINS = [(1.0, 8.0), (8.0, 16.0), (16.0, 24.0), (24.0, 32.0)]
SHOW = ["6-9", "18-22", "26-31", "40-49"]


def main():
    out = {"per_route": {}, "speed_matched": {}, "budget": {}}
    segs_all = {r: L.load_route(r) for r in L.ROUTES}
    recs = {r: L.collect_native(r, L.mask_engaged, xch="cmd", ych="bar", segs=segs_all[r])
            for r in L.ROUTES}

    # ------------------------------------------------------------------ 1. speed census ---------
    print("=== SPEED CENSUS of the engaged episodes (m/s), per build")
    print(f"  {'build':>10} {'K':>4} " + " ".join(f"{a:.0f}-{b:.0f}".rjust(8) for a, b in VBINS)
          + f" {'v_p50':>7}")
    for r in L.ROUTES:
        v = np.array([x["v_mean"] for x in recs[r]])
        cells = [f"{int(np.sum((v >= a) & (v < b))):8d}" for a, b in VBINS]
        print(f"  {r:>10} {len(v):4d} " + " ".join(cells) + f" {np.median(v):7.2f}")
        out["per_route"][r] = dict(K=len(v), v_p50=float(np.median(v)),
                                   census={f"{a:.0f}-{b:.0f}": int(np.sum((v >= a) & (v < b)))
                                           for a, b in VBINS})

    # ------------------------------------------------------------------ 2. raw per-build --------
    print("\n=== RAW per-build (all engaged episodes)")
    hdr = f"  {'build':>10} {'K':>4} {'g2crit':>7} " + " ".join(
        f"{b:>22}" for b in SHOW)
    print(hdr)
    print(" " * 25 + " ".join(f"{'g2 | barRMS | tau_ms':>22}" for _ in SHOW))
    for r in L.ROUTES:
        f, Sxx, Syy, Sxy, K = L.stack(recs[r])
        cells, row = [], {}
        for bn in SHOW:
            lo, hi = L.BANDS[bn]
            s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
            row[bn] = s
            cells.append(f"{s['g2']:6.3f}|{s['rms_y']:7.0f}|{s['tau_ms']:7.1f}")
        print(f"  {r:>10} {K:4d} {L.g2_crit(K):7.4f} " + " ".join(f"{c:>22}" for c in cells))
        out["per_route"][r]["bands"] = row

    # ------------------------------------------------------------------ 3. speed matched -------
    print("\n=== SPEED-MATCHED per-build, per speed bin (only bins with K >= 4 are quotable)")
    for a, b in VBINS:
        print(f"\n  --- v in [{a:.0f}, {b:.0f}) m/s")
        print(f"    {'build':>10} {'K':>3} {'g2crit':>7} " +
              " ".join(f"{bn:>26}" for bn in ("18-22", "26-31")))
        for r in L.ROUTES:
            sub = [x for x in recs[r] if a <= x["v_mean"] < b]
            if len(sub) < 2:
                print(f"    {r:>10} {len(sub):3d}   -- too few episodes")
                continue
            f, Sxx, Syy, Sxy, K = L.stack(sub)
            cells = []
            for bn in ("18-22", "26-31"):
                lo, hi = L.BANDS[bn]
                s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
                ok = "" if s["g2"] > L.g2_crit(K) else " ns"
                cells.append(f"g2 {s['g2']:5.3f}{ok:3s} bar {s['rms_y']:6.0f} "
                             f"tau {s['tau_ms']:+6.1f}")
                out["speed_matched"].setdefault(f"{a:.0f}-{b:.0f}", {}).setdefault(r, {})[bn] = s
            print(f"    {r:>10} {K:3d} {L.g2_crit(K):7.4f} " +
                  " ".join(f"{c:>26}" for c in cells))

    # ------------------------------------------------------------------ 4. power budget ---------
    print("\n\n=== POWER BUDGET.  How much of the bar's band power is SHARED with the command,")
    print("    and how much is not explainable by ANY openpilot-side story, either direction?")
    allrec = [x for r in L.ROUTES for x in recs[r]]
    f, Sxx, Syy, Sxy, K = L.stack(allrec)
    print(f"  {'band':>8} {'g2':>7} {'bar rms':>9} {'cmd rms':>9} {'coherent':>9} "
          f"{'INCOHERENT':>11} {'incoh %':>8}")
    for bn in ("6-9", "10-16", "18-22", "26-31", "32-38", "40-49"):
        lo, hi = L.BANDS[bn]
        s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
        coh_rms = s["rms_y"] * np.sqrt(max(s["g2"], 0))
        inc_rms = s["rms_y"] * np.sqrt(max(1 - s["g2"], 0))
        print(f"  {bn:>8} {s['g2']:7.4f} {s['rms_y']:9.0f} {s['rms_x']:9.0f} {coh_rms:9.0f} "
              f"{inc_rms:11.0f} {100*(1-s['g2']):8.1f}")
        out["budget"][bn] = dict(g2=s["g2"], bar=s["rms_y"], cmd=s["rms_x"],
                                 coherent=float(coh_rms), incoherent=float(inc_rms),
                                 incoh_pct=float(100 * (1 - s["g2"])), K=K)
    print("  (rms in the Hann-periodogram units of `band_stats`; only RATIOS within a row are used)")

    # ------------------------------------------------------------------ 5. the LKAS-lane bound --
    print("\n=== CAN THE COMMAND'S OWN HF CONTENT EVEN REACH THE MOTOR?")
    print("    Standing kit EVIDENCE: the EPS LKAS lane is a ~1-5 Hz low-pass, pole 5.05 Hz")
    print("    (`memory/accord-lkas-lane-is-a-lowpass`).  A single pole at 5.05 Hz attenuates:")
    for fq in (7.79, 20.5, 27.5, 45.0):
        att = 5.05 / np.sqrt(5.05 ** 2 + fq ** 2)
        print(f"      {fq:5.2f} Hz -> x{att:.4f}  ({20*np.log10(att):+.1f} dB), "
              f"phase {-np.degrees(np.arctan2(fq, 5.05)):+.1f} deg")
    print("    ⚠ [BELIEF] this bound is inherited, not re-measured here.  It is the reason the "
          "record\n      called the 27 Hz command an echo in the first place, and this session "
          "does not test it.")
    out["lkas_pole_bound"] = {str(fq): float(5.05 / np.sqrt(5.05 ** 2 + fq ** 2))
                              for fq in (7.79, 20.5, 27.5, 45.0)}

    (L.CACHE / "t4_budget.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\n-> {L.CACHE / 't4_budget.json'}")


if __name__ == "__main__":
    main()
