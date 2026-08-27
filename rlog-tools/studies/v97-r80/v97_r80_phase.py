#!/usr/bin/env python3
r"""Route 80 (V97) vs 7e/7f (V96): the DECISIVE measurement -- the phase of the 427 lane
(`gp-0x6b70`, the PID reference) relative to 0x18F STEER_TORQUE_SENSOR, in a matched creep regime,
plus rate-stratified band levels.

🛑 SIGN CONVENTION: `angle(scipy.signal.csd(x, y)) = arg(Y) - arg(X)`.  Positive => y LEADS x.
   Self-checked against a known lag in `studies/v97-r80/v97_r80_vs_v96.py`; re-asserted here.

🛑 WHAT THE POLE PREDICTS.  `gp-0x374c += ((target - gp-0x374c) * A) >> 10` at 1 kHz is a one-pole
IIR `H(z) = a / (1 - (1-a) z^-1)`, a = A/1024.  Mirrored in integer Python in `pole_phase()`.
   A = 102 -> arg H(7.79 Hz) = -23.64 deg
   A = 150 -> arg H(7.79 Hz) = -15.81 deg      => V97 - V96 = +7.83 deg of LEAD.
This is the whole claim of the build.  `gp-0x374c` enters `gp-0x6b70` only through the
`-(gp-0x374c>>4)` term of iVar6, so the lead observable on the 427 lane is DILUTED by that term's
share of iVar6 -- +7.83 deg is an UPPER BOUND on what can appear here.

🛑 CAN-JOIN CAVEAT, stated before the numbers.  The 427 magnitude is 50 Hz; its sign bit lives on
0x14A at 100 Hz.  De-rectifying joins them with up to 10 ms of alignment error = **28 deg at
7.79 Hz** -- 3.6x the effect being tested.  That bias is a route-level constant only if the CAN
cadence phase is stable, in which case it CANCELS in a build-to-build difference.  It is NOT
assumed to cancel: the |1AB|-only (rectified) arm is reported alongside as a bias-free control.
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
from v97_r80_vs_v96 import ROUTES, load, episodes, band_rms, _phase_selfcheck  # noqa: E402

FS427 = 50.0
F0 = 7.79
RNG = np.random.default_rng(20260812)


def pole_phase(A, f, fs=1000.0):
    """arg H(f) for y += ((x-y)*A)>>10 -- the exact linearisation of the integer recursion."""
    a = A / 1024.0
    w = 2 * np.pi * f / fs
    H = a / (1 - (1 - a) * np.exp(-1j * w))
    return float(np.degrees(np.angle(H)))


def welch_phase(x, y, fs, nperseg, lo, hi):
    """Coherence-weighted mean phase and mean coherence over [lo, hi]."""
    x = np.asarray(x, float) - np.mean(x)
    y = np.asarray(y, float) - np.mean(y)
    if len(x) < nperseg:
        return float("nan"), float("nan")
    f, Pxy = signal.csd(x, y, fs=fs, nperseg=nperseg)
    _, Cxy = signal.coherence(x, y, fs=fs, nperseg=nperseg)
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return float("nan"), float("nan")
    w = Cxy[m]
    z = np.sum(w * Pxy[m] / np.abs(Pxy[m] + 1e-30))
    return float(np.degrees(np.angle(z))), float(np.mean(Cxy[m]))


def circ_mean(deg):
    deg = np.asarray(deg, float)
    deg = deg[np.isfinite(deg)]
    if not len(deg):
        return float("nan")
    return float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(deg))))))


def boot_circ(deg, n=4000):
    deg = np.asarray(deg, float)
    deg = deg[np.isfinite(deg)]
    if len(deg) < 2:
        return float("nan"), float("nan")
    b = [circ_mean(RNG.choice(deg, len(deg), replace=True)) for _ in range(n)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def main():
    out = {"sign_convention": "angle(csd(x,y)) = arg(Y) - arg(X); positive => y LEADS x"}
    out["selfcheck"] = _phase_selfcheck()

    print("\n=== WHAT THE POLE PREDICTS (integer recursion, mirrored) ===")
    pp = {}
    for f in (6.0, 7.79, 9.0, 21.0):
        p102, p150 = pole_phase(102, f), pole_phase(150, f)
        pp[f] = dict(A102=p102, A150=p150, lead=p150 - p102)
        print(f"  {f:5.2f} Hz:  A=102 {p102:+7.2f} deg   A=150 {p150:+7.2f} deg   "
              f"V97 lead {p150-p102:+6.2f} deg")
    out["pole_prediction"] = pp

    D = {r: load(r) for r in ROUTES}
    VHI = 7.0

    # ================= RATE-STRATIFIED BANDS =================
    print("\n=== RATE-STRATIFIED BANDS, engaged creep (speed < 7 km/h), 2.56 s windows ===")
    print("    (0x18F STEER_TORQUE_SENSOR, 100 Hz.  Windows are stratified by median |rate|.)")
    RB = [(0, 5), (5, 20), (20, 60), (60, 1e9)]
    BANDS = {"6-9": (6.0, 9.0), "15-22": (15.0, 22.0), "18-28": (18.0, 28.0)}
    strat = {}
    for r, d in D.items():
        sel = (d["v"] < VHI) & d["eng"]
        eps = episodes(sel, d["t"], 2.56)
        for ei, (a, b) in enumerate(eps):
            for s in range(a, b - 256, 128):
                seg = slice(s, s + 256)
                mr = float(np.median(np.abs(d["rate"][seg])))
                bin_i = next(i for i, (lo, hi) in enumerate(RB) if lo <= mr < hi)
                key = (r, bin_i)
                strat.setdefault(key, {"eps": [], **{k: [] for k in BANDS}})
                strat[key]["eps"].append(ei)
                for k, (lo, hi) in BANDS.items():
                    strat[key][k].append(band_rms(d["tq"][seg], 100.0, lo, hi, 256))
    out["rate_stratified"] = {}
    print(f"    {'route':6s} {'|rate| bin':14s} {'win':>4s} {'eps':>4s}  " +
          "  ".join(f"{k:>10s}" for k in BANDS))
    for bin_i, (lo, hi) in enumerate(RB):
        for r in ROUTES:
            v = strat.get((r, bin_i))
            if not v:
                continue
            nep = len(set(v["eps"]))
            med = {k: float(np.median(v[k])) for k in BANDS}
            out["rate_stratified"][f"{r}_bin{bin_i}"] = dict(
                build=D[r]["build"], rate_lo=lo, rate_hi=(hi if hi < 1e8 else None),
                windows=len(v["eps"]), episodes=nep, median=med)
            print(f"    r{r:5s} {f'{lo}-{hi if hi<1e8 else 'inf'} deg/s':14s} "
                  f"{len(v['eps']):4d} {nep:4d}  " + "  ".join(f"{med[k]:10.2f}" for k in BANDS))

    # ================= THE PHASE MEASUREMENT =================
    print(f"\n=== PHASE: 0x18F torque -> 427 lane (gp-0x6b70), 6-9 Hz, engaged creep ===")
    print("    positive = the 427 lane LEADS the torque sensor")
    out["phase"] = {}
    for arm, use_sign in (("SIGNED (de-rectified, +-28 deg join bias)", True),
                          ("RECTIFIED |1AB| only (bias-free control)", False)):
        print(f"  -- {arm}")
        for r, d in D.items():
            sel = (d["ab_v"] < VHI) & d["ab_eng"]
            eps = episodes(sel, d["ab_t"], 2.56)
            y = d["ab_signed"] if use_sign else d["ab_counts"]
            # torque resampled onto the 427 grid (ZOH-free: linear interp, both are slow vs 6-9 Hz
            # ONLY in the join sense; the 100 Hz source is oversampled 2x so interp is legitimate)
            x_all = np.interp(d["ab_t"], d["t"], d["tq"])
            ph, co, epi = [], [], []
            for ei, (a, b) in enumerate(eps):
                for s in range(a, b - 128, 64):
                    sl = slice(s, s + 128)
                    p, c = welch_phase(x_all[sl], y[sl], FS427, 128, 6.0, 9.0)
                    if np.isfinite(p):
                        ph.append(p); co.append(c); epi.append(ei)
            if not ph:
                print(f"     r{r} ({d['build']}): no windows")
                continue
            m = circ_mean(ph)
            lo, hi = boot_circ(ph)
            key = f"{'signed' if use_sign else 'rect'}_{r}"
            out["phase"][key] = dict(build=d["build"], windows=len(ph),
                                     episodes=len(set(epi)), phase_deg=m,
                                     ci=[lo, hi], mean_coherence=float(np.mean(co)))
            print(f"     r{r} ({d['build']:3s}): {len(ph):4d} windows / {len(set(epi)):2d} episodes"
                  f"   phase {m:+7.2f} deg  CI [{lo:+7.2f}, {hi:+7.2f}]  "
                  f"width {hi-lo:6.2f} deg   coh {np.mean(co):.3f}")

    # ---- the cross-build contrast, the thing V97's claim actually predicts
    print("\n=== CROSS-BUILD CONTRAST  (V97 route 80) - (V96 routes 7e/7f) ===")
    print(f"    PREDICTED by the pole: +{pp[7.79]['lead']:.2f} deg (UPPER BOUND; diluted in "
          f"gp-0x6b70)")
    for arm in ("signed", "rect"):
        a = out["phase"].get(f"{arm}_80")
        if not a:
            continue
        for r in ("7e", "7f"):
            b = out["phase"].get(f"{arm}_{r}")
            if not b:
                continue
            d_ = a["phase_deg"] - b["phase_deg"]
            # conservative CI: add the two half-widths
            hw = (a["ci"][1] - a["ci"][0]) / 2 + (b["ci"][1] - b["ci"][0]) / 2
            fold = hw * 2 / abs(pp[7.79]["lead"])
            out.setdefault("contrast", {})[f"{arm}_80_vs_{r}"] = dict(
                delta_deg=float(d_), ci_halfwidth_deg=float(hw),
                fold_width_vs_prediction=float(fold))
            print(f"    {arm:7s} 80 vs {r}: {d_:+7.2f} deg  +-{hw:.2f}  "
                  f"=> CI fold-width vs the +7.83 deg prediction: {fold:.1f}x  "
                  f"{'UNDERPOWERED' if fold > 1.0 else 'powered'}")

    (AN / "_scratch/cache/r80" / "r80_phase.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {AN/'_scratch/cache/r80'/'r80_phase.json'}")


if __name__ == "__main__":
    main()
