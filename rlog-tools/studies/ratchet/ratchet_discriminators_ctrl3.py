#!/usr/bin/env python3
"""RATCHET DISCRIMINATORS -- PART 4.  Line width, since CTRL-1 showed `C31.q_of` reads ~29 on
PURE NOISE and is therefore unusable.

W1  ENSEMBLE half-power width of the speed-matched mean PROMINENCE spectrum around the line.
    This conflates the true mode bandwidth with window-to-window frequency wander, so it is an
    UPPER bound on the bandwidth -> a LOWER bound on Q.  Calibrated against a fixed-frequency
    injection (which has zero true bandwidth and zero wander) so the instrument's own smearing
    is subtracted rather than assumed.

W2  WINDOW-TO-WINDOW DISPERSION of f_free among detected engaged windows -- how much the line
    actually wanders, which TEST A says should track load.

W3  the 6d / 67 caveat: their 8.5-8.7 Hz "line" sits at a detection rate barely above the
    false-positive floor, so it may not be the same object.  Quantified, not asserted.

usage:  python studies/ratchet/ratchet_discriminators_ctrl3.py
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G          # noqa: E402,F401
import _r31_common as C31        # noqa: E402,F401
import v86_freq_test as V86      # noqa: E402
import ratchet_discriminators as RD           # noqa: E402
import ratchet_discriminators_ctrl as RC      # noqa: E402

OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def ens_width(rs, lo=5.0, hi=12.0):
    """Half-power width of the ensemble-mean PROMINENCE spectrum's peak in [lo,hi]."""
    f = rs[0]["f"]
    S = np.nanmean([r["R"] for r in rs], axis=0)
    m = (f >= lo) & (f <= hi) & np.isfinite(S)
    if not m.any():
        return np.nan, np.nan, np.nan
    idx = np.flatnonzero(m)
    j = idx[int(np.argmax(S[m]))]
    pk = S[j]
    base = float(np.nanmedian(S[m]))
    half = base + 0.5 * (pk - base)
    a = j
    while a > idx[0] and S[a] > half:
        a -= 1
    b = j
    while b < idx[-1] and S[b] > half:
        b += 1
    return float(f[j]), float(f[b] - f[a]), float(pk)


def main():
    hdr("BUILD POOLS")
    ENG, MAN, ALLV, POOL, POOL_MAN = RC.build_pools()
    PF = json.loads((ROOT / "_scratch/cache/r6f" / "ratchet_discriminators.json")
                    .read_text(encoding="utf-8"))["p_free_floor"]
    det = [r for r in POOL if np.isfinite(r["f_free"]) and r["p_free"] >= PF]
    print(f"  POOLED n={len(POOL)}  detected n={len(det)}  floor p_free>={PF:.2f}")

    hdr("W1  ENSEMBLE LINE WIDTH  (upper bound on bandwidth -> lower bound on Q)")
    f0 = float(np.median([r["f_free"] for r in det]))
    fc, bw, pk = ens_width(det)
    print(f"  engaged, detected      peak {fc:.3f} Hz   half-power width {bw:.3f} Hz  "
          f"(peak prom {pk:.1f})   ⇒ Q_lower = {fc / bw if bw else float('nan'):.2f}")
    fcm, bwm, pkm = ens_width([r for r in POOL_MAN if np.isfinite(r["f_free"])])
    print(f"  disengaged (control)   peak {fcm:.3f} Hz   half-power width {bwm:.3f} Hz  "
          f"(peak prom {pkm:.1f})")
    # instrument smearing: a fixed-frequency injection has ZERO true width and ZERO wander
    inj = RC.inject_fixed(POOL, f0, 250.0, f0, rng=np.random.default_rng(4242))
    fci, bwi, pki = ens_width(inj)
    print(f"  fixed-f injection      peak {fci:.3f} Hz   half-power width {bwi:.3f} Hz  "
          f"(peak prom {pki:.1f})   <- the instrument's own smearing")
    OUT["W1"] = dict(engaged=dict(fc=fc, bw=bw, peak=pk, Q_lower=fc / bw if bw else None),
                     disengaged=dict(fc=fcm, bw=bwm, peak=pkm),
                     injected_fixed=dict(fc=fci, bw=bwi, peak=pki),
                     note="engaged width includes window-to-window wander => Q_lower is a LOWER "
                          "bound on Q; injection row is the instrument floor")

    hdr("W2  WINDOW-TO-WINDOW DISPERSION of f_free")
    for name, sel in (("engaged detected", det),
                      ("engaged all", [r for r in POOL if np.isfinite(r["f_free"])]),
                      ("disengaged", [r for r in POOL_MAN if np.isfinite(r["f_free"])]),
                      ("fixed-f injection", [r for r in inj if np.isfinite(r["f_free"])])):
        v = np.array([r["f_free"] for r in sel], float)
        e = dict(n=len(v), med=float(np.median(v)), sd=float(v.std(ddof=1)),
                 iqr=[float(np.percentile(v, 25)), float(np.percentile(v, 75))],
                 p5=float(np.percentile(v, 5)), p95=float(np.percentile(v, 95)))
        OUT.setdefault("W2", {})[name] = e
        print(f"  {name:20s} n={len(v):3d}  med={e['med']:.3f}  sd={e['sd']:.3f} Hz  "
              f"IQR[{e['iqr'][0]:.3f},{e['iqr'][1]:.3f}]  p5-p95[{e['p5']:.3f},{e['p95']:.3f}]")

    hdr("W3  ARE 6d / 67's 8.5-8.7 Hz LINES THE SAME OBJECT?  (they are NOT scored either way)")
    OUT["W3"] = {}
    for route in RD.THIN + RD.SCORED:
        rs = [r for r in ALLV[route] if np.isfinite(r["f_free"])]
        pe = np.array([r["p_free"] for r in rs], float)
        d = float(np.mean(pe >= PF))
        b = RD.boot_blocks(rs, lambda z: float(np.median([q["f_free"] for q in z])), nboot=2000)
        hi = [r for r in rs if r["v"] >= 5.0]
        lo = [r for r in rs if r["v"] < 5.0]
        OUT["W3"][route] = dict(n=len(rs), det_rate=d, f_med=b["pt"], lo=b["lo"], hi=b["hi"],
                                n_lowspeed=len(lo), n_highspeed=len(hi),
                                f_lowspeed=(float(np.median([r["f_free"] for r in lo]))
                                            if len(lo) >= 5 else None),
                                f_highspeed=(float(np.median([r["f_free"] for r in hi]))
                                             if len(hi) >= 5 else None))
        e = OUT["W3"][route]
        print(f"  {route:10s} n={len(rs):3d}  det={d:.3f} (false-pos floor ~0.10)  "
              f"f={b['pt']:.3f}[{b['lo']:.3f},{b['hi']:.3f}]  "
              f"f(v<5)={e['f_lowspeed']}  f(v>=5)={e['f_highspeed']}  "
              f"n(lo/hi)={len(lo)}/{len(hi)}")

    hdr("MERGE")
    p = ROOT / "_scratch/cache/r6f" / "ratchet_discriminators.json"
    D = json.loads(p.read_text(encoding="utf-8"))
    D["linewidth"] = OUT
    p.write_text(json.dumps(D, indent=1, default=lambda o: None), encoding="utf-8")
    print(f"  wrote {p}")


if __name__ == "__main__":
    main()
