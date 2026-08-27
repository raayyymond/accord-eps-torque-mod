#!/usr/bin/env python3
"""studies/identification/selfint_harmonics.py -- RELAY TEST: is the engaged torsion-bar signal richer in ODD harmonics
than the manual signal at MATCHED fundamental amplitude?

WHY.  A Coulomb / sign(rate) relay generates a square-wave-like odd-harmonic series; a linear
resonance does not.  For an ideal symmetric relay the AMPLITUDE ratios are
        |A3|/|A1| = 1/3 = 0.333        |A5|/|A3| = 3/5 = 0.600
(the kit already uses the 5f/3f form -- the ring measured 0.023 against a relay's 0.600).

🛑 FEASIBILITY, stated before the numbers.  fs is 100 Hz, so only a fundamental below 50/5 = 10 Hz
has BOTH its 3rd and 5th inside Nyquist:
    f0 = 7.79 Hz  ->  3f = 23.4 Hz, 5f = 39.0 Hz     BOTH CLEAN -- the test is valid
    f0 = 20.5 Hz  ->  3f = 61.5 Hz aliases to 38.5,  5f = 102.5 aliases to 2.5  NOT TESTABLE
    f0 = 27.5 Hz  ->  3f = 82.5 aliases to 17.5,     5f = 137.5 aliases to 37.5 NOT TESTABLE
⇒ this script REFUSES the S1 and ring bands and reports only S2.  Reporting an aliased 3f as a
harmonic would be exactly the manufactured-line failure this kit has already retracted once.

METHOD.  Per EPISODE (the bootstrap unit, never a window): Welch bar spectrum; the fundamental is
the argmax in 6-9 Hz; harmonic power is summed in a +/-2.5% fractional band about n*f0 with the
local median floor of a 1.5-3x wider shoulder subtracted, so broadband level cannot masquerade as
a harmonic.  Episodes whose fundamental fails a 3x prominence test are dropped and counted.

Usage: python studies/identification/selfint_harmonics.py
Writes: _scratch/cache/selfint/selfint_harmonics.json
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
import selfint_lib as S  # noqa: E402
import selfint_transfer as T  # noqa: E402

RNG = np.random.default_rng(7979)
NBOOT = 4000
F_LO, F_HI = 6.0, 9.0
PROM = 3.0


def harm(f, P, f0, n, frac=0.025, sh=(1.5, 3.0)):
    """Local-floor-subtracted amplitude at n*f0.  Returns nan if the band is off the grid."""
    fc = n * f0
    if fc > f[-1] * 0.96:
        return np.nan
    core = (f >= fc * (1 - frac)) & (f <= fc * (1 + frac))
    shoul = ((f >= fc * (1 - sh[1] * frac)) & (f <= fc * (1 + sh[1] * frac))
             & ~((f >= fc * (1 - sh[0] * frac)) & (f <= fc * (1 + sh[0] * frac))))
    if core.sum() < 1 or shoul.sum() < 2:
        return np.nan
    floor = float(np.median(P[shoul]))
    p = float(np.sum(np.maximum(P[core] - floor, 0.0)))
    return float(np.sqrt(p))


def rows(route, cond_name, mask_fn):
    out = []
    for rec in S.collect(route, mask_fn, ep_max=1024):
        f, P = rec["f"], rec["Syy"]
        sel = (f >= F_LO) & (f <= F_HI)
        if not sel.any():
            continue
        j = np.flatnonzero(sel)[int(np.argmax(P[sel]))]
        f0 = float(f[j])
        side = ((f >= F_LO - 3) & (f <= F_HI + 3)) & ~((f >= f0 * 0.93) & (f <= f0 * 1.07))
        if not side.any() or P[j] < PROM * float(np.median(P[side])):
            out.append(dict(route=route, cond=cond_name, f0=f0, ok=False))
            continue
        a1, a3, a5 = (harm(f, P, f0, n) for n in (1, 3, 5))
        if not (np.isfinite(a1) and a1 > 0):
            out.append(dict(route=route, cond=cond_name, f0=f0, ok=False))
            continue
        out.append(dict(route=route, cond=cond_name, f0=f0, ok=True, a1=a1, a3=a3, a5=a5,
                        r31=a3 / a1 if np.isfinite(a3) else np.nan,
                        r53=a5 / a3 if (np.isfinite(a5) and np.isfinite(a3) and a3 > 0)
                        else np.nan,
                        v=rec["v_mean"]))
    return out


def boot_med(x, nb=NBOOT):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 4:
        return np.nan, (np.nan, np.nan), len(x)
    bs = [np.median(RNG.choice(x, len(x), replace=True)) for _ in range(nb)]
    return float(np.median(x)), (float(np.percentile(bs, 2.5)),
                                 float(np.percentile(bs, 97.5))), len(x)


def main():
    print("=" * 100)
    print("RELAY TEST -- odd-harmonic content of the torsion bar at the S2 fundamental (6-9 Hz).")
    print("=" * 100)
    print("\n  IDEAL SYMMETRIC RELAY:  |A3|/|A1| = 0.333   |A5|/|A3| = 0.600")
    print("  PURE LINEAR RESONANCE:  both -> 0 (only the broadband floor, which is subtracted).")
    print("  🛑 Only the 6-9 Hz fundamental is testable at fs = 100 Hz -- see the module docstring.")

    for lbl, spec in T.MANUAL_EXTRA.items():
        S.ROUTES.setdefault(lbl, spec)
    eng, man = [], []
    for rt in T.MAIN:
        eng += rows(rt, "engaged", S.mask_engaged)
    for rt in list(T.MAIN) + list(T.MANUAL_EXTRA):
        try:
            man += rows(rt, "manual", S.mask_manual)
        except Exception:
            continue

    out = {}
    print(f"\n  {'arm':10s} {'K total':>8} {'K usable':>9} {'f0 p50':>7} {'|A1| p50':>10} "
          f"{'|A3|/|A1|':>26} {'|A5|/|A3|':>26}")
    arms = {"engaged": eng, "manual": man}
    for nm, rs in arms.items():
        ok = [r for r in rs if r["ok"]]
        m31, c31, n31 = boot_med([r["r31"] for r in ok])
        m53, c53, n53 = boot_med([r["r53"] for r in ok])
        out[nm] = dict(K=len(rs), K_ok=len(ok), r31=m31, ci31=c31, n31=n31,
                       r53=m53, ci53=c53, n53=n53,
                       f0=float(np.median([r["f0"] for r in ok])) if ok else np.nan,
                       a1=float(np.median([r["a1"] for r in ok])) if ok else np.nan)
        print(f"  {nm:10s} {len(rs):8d} {len(ok):9d} {out[nm]['f0']:7.2f} {out[nm]['a1']:10.0f} "
              f"{S.fmt_ci(m31, c31):>26} {S.fmt_ci(m53, c53):>26}")

    # ---- matched on fundamental amplitude ----------------------------------------------------
    print("\n  MATCHED on |A1| (the fundamental's own amplitude), overlap decile window, so a\n"
          "  louder engaged fundamental cannot by itself lift the harmonic ratios.")
    oe = [r for r in eng if r["ok"]]
    om = [r for r in man if r["ok"]]
    if len(oe) >= 4 and len(om) >= 4:
        lo = max(np.percentile([r["a1"] for r in oe], 10), np.percentile([r["a1"] for r in om], 10))
        hi = min(np.percentile([r["a1"] for r in oe], 90), np.percentile([r["a1"] for r in om], 90))
        me = [r for r in oe if lo <= r["a1"] <= hi]
        mm = [r for r in om if lo <= r["a1"] <= hi]
        print(f"  |A1| window {lo:.0f}-{hi:.0f} counts   K engaged {len(me)}  K manual {len(mm)}")
        print(f"  {'arm':10s} {'K':>4} {'|A1| p50':>10} {'|A3|/|A1|':>26} {'|A5|/|A3|':>26}")
        for nm, rs in (("engaged", me), ("manual", mm)):
            m31, c31, _ = boot_med([r["r31"] for r in rs])
            m53, c53, _ = boot_med([r["r53"] for r in rs])
            out["matched_" + nm] = dict(K=len(rs), r31=m31, ci31=c31, r53=m53, ci53=c53,
                                        window=[float(lo), float(hi)])
            a1m = float(np.median([r["a1"] for r in rs])) if rs else np.nan
            print(f"  {nm:10s} {len(rs):4d} {a1m:10.0f} {S.fmt_ci(m31, c31):>26} "
                  f"{S.fmt_ci(m53, c53):>26}")
        if len(me) >= 4 and len(mm) >= 4:
            e31 = np.array([r["r31"] for r in me if np.isfinite(r["r31"])])
            g31 = np.array([r["r31"] for r in mm if np.isfinite(r["r31"])])
            bs = [np.median(RNG.choice(e31, len(e31), True)) / np.median(RNG.choice(g31, len(g31),
                                                                                   True))
                  for _ in range(NBOOT)]
            rat = float(np.median(e31) / np.median(g31))
            out["ratio_31_eng_over_man"] = dict(
                ratio=rat, ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                K_eng=len(e31), K_man=len(g31))
            print(f"\n  |A3|/|A1| ENGAGED / MANUAL at matched fundamental = "
                  f"{S.fmt_ci(rat, (np.percentile(bs, 2.5), np.percentile(bs, 97.5)))}"
                  f"   (K {len(e31)} vs {len(g31)})")

    # ---- split-half null ----------------------------------------------------------------------
    print("\n  SPLIT-HALF NULL on the engaged |A3|/|A1| (episodes by parity) -- the floor any\n"
          "  engaged-vs-manual difference has to clear:")
    v = [r["r31"] for r in oe if np.isfinite(r["r31"])]
    if len(v) >= 8:
        a, b = float(np.median(v[0::2])), float(np.median(v[1::2]))
        out["splithalf_31"] = dict(A=a, B=b, absdiff=abs(a - b))
        print(f"    half A {a:.4f}   half B {b:.4f}   |A-B| {abs(a - b):.4f}")

    print("\n  🛑 REFUSED, and why: no relay test is possible at 20.5 Hz or 27.5 Hz on a 100 Hz\n"
          "  instrument.  3*20.5 = 61.5 Hz folds to 38.5 Hz and 5*20.5 folds to 2.5 Hz, so any\n"
          "  'harmonic' measured there is an alias of unknown provenance sitting on top of real\n"
          "  in-band content.  Settling the relay question at S1 needs a build-side probe (a cave\n"
          "  bit on the sign term itself), not more rlog analysis.")
    (ROOT / "_scratch/cache/selfint").mkdir(exist_ok=True)

    def san(o):
        if isinstance(o, dict):
            return {k: san(x) for k, x in o.items()}
        if isinstance(o, (list, tuple)):
            return [san(x) for x in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(float(o)) else round(float(o), 6)
        if isinstance(o, (np.integer, int)):
            return int(o)
        return o
    (ROOT / "_scratch/cache/selfint" / "selfint_harmonics.json").write_text(json.dumps(san(out), indent=1))
    print("\nwrote _scratch/cache/selfint/selfint_harmonics.json")


if __name__ == "__main__":
    main()
