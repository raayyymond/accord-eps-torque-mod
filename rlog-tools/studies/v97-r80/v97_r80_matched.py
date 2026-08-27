#!/usr/bin/env python3
r"""Route 80 (V97) vs 7e/7f (V96): where -- if anywhere -- a MATCHED regime exists, and what the
bands and the 427-lane phase say inside it.

Fixes two defects in the first pass (`studies/v97-r80/v97_r80_phase.py`), both found by running the control first:
  1. `nperseg == len(window)` gives ONE Welch segment => coherence is identically 1.000 by
     construction.  Here every window carries >= 6 averages and the coherence is reported as a
     real number, with a SHUFFLED control alongside.
  2. Matching on speed alone is not matching.  Route 80's engaged frames sit at 5-60 deg/s of
     wheel rate; 7e/7f's engaged creep sits at 0-5 deg/s.  This file grids on BOTH axes and
     prints the joint occupancy, so a cell with no overlap is visible rather than averaged over.

🛑 SIGN CONVENTION: angle(csd(x, y)) = arg(Y) - arg(X); positive => y LEADS x.  Self-checked.
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
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v97_r80_vs_v96 import ROUTES, load, band_rms, _phase_selfcheck  # noqa: E402
from v97_r80_phase import pole_phase, circ_mean, boot_circ  # noqa: E402

RNG = np.random.default_rng(20260812)
VB = [(0, 7), (7, 15), (15, 30), (30, 60), (60, 200)]        # km/h
RB = [(0, 5), (5, 20), (20, 60), (60, 1e9)]                  # deg/s, median |steeringRate|
#  🛑 WINDOW LENGTH IS LOAD-BEARING AND WAS WRONG ONCE.  At 5.12 s this analysis reported ZERO
#  matched cells; a frame-level second method showed ~5 s of matched engaged exposure per arm on
#  BOTH sides.  The 5.12 s cut, not the data, produced the null.  2.56 s is the shortest window
#  that still gives >= 6 Welch averages at nperseg 64 (100 Hz) / 32 (50 Hz).
WIN100, HOP100 = int(sys.argv[1]) if len(sys.argv) > 1 else 256, 128
WIN427, HOP427 = WIN100 // 2, HOP100 // 2
NPS100, NPS427 = 64, 32
BANDS = {"6-9": (6.0, 9.0), "15-22": (15.0, 22.0), "18-28": (18.0, 28.0), "26-31": (26.0, 31.0)}


def cells(d, on100=True):
    """Yield (vi, ri, slice, episode_id) for every homogeneous window."""
    t = d["t"] if on100 else d["ab_t"]
    v = d["v"] if on100 else d["ab_v"]
    rate = d["rate"] if on100 else d["ab_rate"]
    eng = d["eng"] if on100 else d["ab_eng"]
    W, H = (WIN100, HOP100) if on100 else (WIN427, HOP427)
    for s in range(0, len(t) - W, H):
        sl = slice(s, s + W)
        if not eng[sl].all():
            continue
        if t[s + W - 1] - t[s] > 1.5 * W / (100.0 if on100 else 50.0):
            continue                                   # spans a segment join / gap
        mv, mr = float(np.median(v[sl])), float(np.median(np.abs(rate[sl])))
        try:
            vi = next(i for i, (lo, hi) in enumerate(VB) if lo <= mv < hi)
            ri = next(i for i, (lo, hi) in enumerate(RB) if lo <= mr < hi)
        except StopIteration:
            continue
        yield vi, ri, sl, int(t[s] // 30)               # episode id = 30 s block


def welch_phase(x, y, fs, lo, hi, nperseg=NPS427):
    x = np.asarray(x, float) - np.mean(x)
    y = np.asarray(y, float) - np.mean(y)
    f, Pxy = signal.csd(x, y, fs=fs, nperseg=nperseg)
    _, Cxy = signal.coherence(x, y, fs=fs, nperseg=nperseg)
    m = (f >= lo) & (f <= hi)
    w = Cxy[m]
    z = np.sum(w * Pxy[m] / np.abs(Pxy[m] + 1e-30))
    return float(np.degrees(np.angle(z))), float(np.mean(Cxy[m]))


def main():
    out = {"sign_convention": "angle(csd(x,y)) = arg(Y)-arg(X); positive => y LEADS x",
           "window_s": WIN100 / 100.0, "welch_nperseg": [NPS100, NPS427],
           "pole_prediction_deg": {str(f): pole_phase(150, f) - pole_phase(102, f)
                                   for f in (6.0, 7.79, 9.0, 21.0)}}
    out["selfcheck"] = _phase_selfcheck()
    D = {r: load(r) for r in ROUTES}

    # ================= JOINT OCCUPANCY =================
    print("\n=== JOINT (speed x wheel-rate) OCCUPANCY OF ENGAGED 5.12 s WINDOWS ===")
    occ = {}
    for r, d in D.items():
        for vi, ri, _sl, _e in cells(d, True):
            occ[(r, vi, ri)] = occ.get((r, vi, ri), 0) + 1
    hdr = "  " + "speed km/h".ljust(12) + "".join(
        f"{f'{lo}-{hi if hi<1e8 else 'inf'}':>12s}" for lo, hi in RB)
    print(hdr + "   <- median |wheel rate| deg/s")
    for vi, (vlo, vhi) in enumerate(VB):
        row = f"  {f'{vlo}-{vhi}':12s}"
        for ri in range(len(RB)):
            cell = "/".join(str(occ.get((r, vi, ri), 0)) for r in ("80", "7e", "7f"))
            row += f"{cell:>12s}"
        print(row + ("   <- r80/r7e/r7f" if vi == 0 else ""))
    out["occupancy"] = {f"{r}_v{vi}_r{ri}": n for (r, vi, ri), n in occ.items()}

    overlap = [(vi, ri) for vi in range(len(VB)) for ri in range(len(RB))
               if occ.get(("80", vi, ri), 0) >= 2
               and (occ.get(("7e", vi, ri), 0) + occ.get(("7f", vi, ri), 0)) >= 2]
    out["overlap_cells"] = [dict(speed=VB[vi], rate=RB[ri][:2],
                                 n80=occ.get(("80", vi, ri), 0),
                                 n7e=occ.get(("7e", vi, ri), 0),
                                 n7f=occ.get(("7f", vi, ri), 0)) for vi, ri in overlap]
    print(f"\n  CELLS WITH >=2 WINDOWS ON BOTH SIDES: {len(overlap)}")
    for vi, ri in overlap:
        print(f"    speed {VB[vi]} km/h  x  |rate| {RB[ri][0]}-{RB[ri][1]} deg/s   "
              f"r80 {occ.get(('80',vi,ri),0)}  r7e {occ.get(('7e',vi,ri),0)}  "
              f"r7f {occ.get(('7f',vi,ri),0)}")

    # ================= BANDS PER CELL =================
    print("\n=== BAND RMS (0x18F torque, 100 Hz), per matched cell, median over windows ===")
    bands = {}
    for r, d in D.items():
        for vi, ri, sl, e in cells(d, True):
            k = (r, vi, ri)
            bands.setdefault(k, {"eps": [], **{b: [] for b in BANDS}})
            bands[k]["eps"].append(e)
            for b, (lo, hi) in BANDS.items():
                bands[k][b].append(band_rms(d["tq"][sl], 100.0, lo, hi, NPS100))
    out["bands"] = {}
    for vi, ri in overlap:
        print(f"  -- speed {VB[vi]} km/h, |rate| {RB[ri][0]}-{RB[ri][1]} deg/s")
        for r in ("80", "7e", "7f"):
            v = bands.get((r, vi, ri))
            if not v:
                continue
            med = {b: float(np.median(v[b])) for b in BANDS}
            out["bands"][f"{r}_v{vi}_r{ri}"] = dict(build=D[r]["build"], windows=len(v["eps"]),
                                                    episodes=len(set(v["eps"])), median=med)
            print(f"     r{r} ({D[r]['build']:3s}) n={len(v['eps']):3d} win / "
                  f"{len(set(v['eps'])):2d} eps:  " +
                  "  ".join(f"{b} {med[b]:8.2f}" for b in BANDS))

    # ================= PHASE PER CELL, WITH A SHUFFLED CONTROL =================
    print("\n=== PHASE 0x18F torque -> 427 lane (gp-0x6b70), 6-9 Hz, per matched cell ===")
    print("    positive = 427 lane LEADS torque.  CONTROL = phase against a time-reversed torque")
    print("    trace (destroys the causal relation, preserves the spectrum).")
    ph = {}
    for r, d in D.items():
        x_all = np.interp(d["ab_t"], d["t"], d["tq"])
        for vi, ri, sl, e in cells(d, False):
            k = (r, vi, ri)
            ph.setdefault(k, {"p": [], "c": [], "pc": [], "cc": [], "eps": []})
            p, c = welch_phase(x_all[sl], d["ab_signed"][sl], 50.0, 6.0, 9.0)
            pc, cc = welch_phase(x_all[sl][::-1], d["ab_signed"][sl], 50.0, 6.0, 9.0)
            ph[k]["p"].append(p); ph[k]["c"].append(c)
            ph[k]["pc"].append(pc); ph[k]["cc"].append(cc)
            ph[k]["eps"].append(e)
    out["phase"] = {}
    for vi, ri in overlap:
        print(f"  -- speed {VB[vi]} km/h, |rate| {RB[ri][0]}-{RB[ri][1]} deg/s")
        for r in ("80", "7e", "7f"):
            v = ph.get((r, vi, ri))
            if not v or len(v["p"]) < 1:
                continue
            m = circ_mean(v["p"])
            lo, hi = boot_circ(v["p"])
            mc = circ_mean(v["pc"])
            out["phase"][f"{r}_v{vi}_r{ri}"] = dict(
                build=D[r]["build"], windows=len(v["p"]), episodes=len(set(v["eps"])),
                phase_deg=m, ci=[lo, hi], coherence=float(np.mean(v["c"])),
                control_phase_deg=mc, control_coherence=float(np.mean(v["cc"])))
            print(f"     r{r} ({D[r]['build']:3s}) {len(v['p']):3d} win / {len(set(v['eps'])):2d} "
                  f"eps:  phase {m:+7.2f} deg  CI [{lo:+7.2f},{hi:+7.2f}]  coh "
                  f"{np.mean(v['c']):.3f}   || CONTROL phase {mc:+7.2f}  coh "
                  f"{np.mean(v['cc']):.3f}")

    (AN / "_scratch/cache/r80" / "r80_matched.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {AN/'_scratch/cache/r80'/'r80_matched.json'}")


if __name__ == "__main__":
    main()
