#!/usr/bin/env python3
r"""RING-DOWN ON REAL EDGES, with the estimator that PASSED its control -- and the maneuver's
excitation spectrum.

PART A re-runs the kit's ring-down on every latActive falling edge with **E3 (matrix pencil)** from
`studies/damping-q/ringdown_validate.py`, the only one of four estimators that ordered zeta over 0.005-0.200
(Spearman +1.000, dynamic range 41x) and refused all three nulls (0/40 white noise, 0/40 perfect
step, 0/40 phase-randomised real data).  E1 (`studies/stock-baseline/stock_r97_ringdown.py`) and E2 (`studies/damping-q/r67_ringdown_q2.py`)
are carried BESIDE it, not instead of it, so the disagreement is visible.
🛑 Every disengage-edge number is of the **DISENGAGED** plant (`accord-ringdown-q-needs-a-step-
control`): the engaged-only damper switches off at that instant.

PART B answers the question that decides whether the lateral-maneuver drive is worth taking:
**how much energy does the maneuver actually put into 6-14 Hz?**  The maneuver commands a step in
lateral acceleration, but `selfdrive/controls/lib/drive_helpers.py:clip_curvature` slews the
desired curvature at `MAX_LATERAL_JERK = 5.0 m/s^3`, so what the car sees is a RAMP, and a ramp of
duration T has spectral NULLS at f = n/T.  This part simulates the exact chain and prints where
those nulls land.
"""
from __future__ import annotations
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L                                    # noqa: E402
from ringdown_validate import e1_hilbert_env, e2_demod, e3_pencil   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.FS
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}
MAX_LATERAL_JERK = 5.0          # m/s^3   drive_helpers.py:13
MPH = 0.44704


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, LAB.get(rt, rt), gain=0, clamp=0, leverB=False, idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 106); print(s); print("=" * 106, flush=True)


def peak_f0(x, lo=5.0, hi=13.0):
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft((x - x.mean()) * w))
    f = np.fft.rfftfreq(len(x), 1 / FS)
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(X[m])]) if m.any() else np.nan


def part_a(routes):
    hdr("A.  RING-DOWN ON EVERY CLEAN latActive FALLING EDGE -- three estimators side by side")
    print("    Gate: 3 s continuously engaged before, 3 s continuously disengaged after, v > 1 m/s.")
    print("    E3 returns NaN when the mode explains < 35 %% of the segment -- that REFUSAL is the")
    print("    result, not a failure.  E1/E2 always return something; that is their defect.")
    print("\n    %-11s %4s %8s %6s %7s %8s %8s %10s %8s"
          % ("route", "seg", "t_e s", "v m/s", "f0 pre", "E1 zeta", "E2 zeta", "E3 f,zeta", "E3 Q"))
    rows = []
    for rt in routes:
        for blk in L.all_blocks(rt):
            t = blk["t"]
            lat = np.asarray(blk["cc_lat"], float) > 0.5
            x = np.asarray(blk["tq"], float)
            v = np.abs(np.asarray(blk.get("v_rear", blk["cs_v"]), float))
            g = int(3 * FS)
            for i in np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1:
                if i - g < 0 or i + g >= len(t):
                    continue
                if not (lat[i - g:i].mean() > 0.95 and lat[i:i + g].mean() < 0.05):
                    continue
                if v[i] < 1.0:
                    continue
                pre = x[max(i - int(4 * FS), 0):i]
                f0 = peak_f0(pre) if len(pre) > 256 else 7.8
                post = x[i:i + int(3.0 * FS)]
                _, z1 = e1_hilbert_env(post, FS, f0, fit_s=1.0)
                _, z2 = e2_demod(post, FS, f0, fit_s=1.0)
                f3, z3 = e3_pencil(post[:int(1.5 * FS)], FS, f_lo=4.0, f_hi=14.0)
                rows.append(dict(rt=rt, seg=int(blk["_seg"]), t=float(t[i]), v=float(v[i]),
                                 f0=f0, z1=z1, z2=z2, f3=f3, z3=z3))
                print("    %-11s %4d %8.1f %6.2f %7.2f %8s %8s %10s %8s"
                      % (LAB.get(rt, rt), blk["_seg"], t[i], v[i], f0,
                         "%.4f" % z1 if np.isfinite(z1) else "--",
                         "%.4f" % z2 if np.isfinite(z2) else "--",
                         "%.1f,%.3f" % (f3, z3) if np.isfinite(z3) else "REFUSED",
                         "%.1f" % (1 / (2 * z3)) if np.isfinite(z3) else "--"))
    n3 = [r for r in rows if np.isfinite(r["z3"])]
    print("\n    TOTALS: %d clean edges.  E1 returned a number on %d, E2 on %d, "
          "**E3 on %d**." % (len(rows), sum(np.isfinite(r["z1"]) for r in rows),
                             sum(np.isfinite(r["z2"]) for r in rows), len(n3)))
    if n3:
        z = np.array([r["z3"] for r in n3]); f = np.array([r["f3"] for r in n3])
        print("    E3 accepted edges: f = %.2f-%.2f Hz (med %.2f) · zeta = %.3f-%.3f (med %.3f) "
              "· Q = %.1f-%.1f" % (f.min(), f.max(), np.median(f), z.min(), z.max(),
                                   np.median(z), 1 / (2 * z.max()), 1 / (2 * z.min())))
    else:
        print("    🛑 E3 accepted ZERO edges.  Under a validated estimator there is NO measurable")
        print("       ring-down at 4-14 Hz on any disengage edge in the corpus.  Read with")
        print("       `accord-ringdown-q-needs-a-step-control`: 'the ring does not ring down --")
        print("       it STOPS'.  E1/E2 numbers on these same edges are therefore not damping.")
    return rows


def part_b():
    hdr("B.  WHAT THE LATERAL MANEUVER ACTUALLY EXCITES -- the jerk limit turns the step into a RAMP")
    print("    Chain simulated: lateral_maneuversd commands a STEP in lateral accel (np.interp on a")
    print("    single breakpoint = a true step), converted to desiredCurvature = a/v^2, then")
    print("    controlsd applies `clip_curvature` with MAX_LATERAL_JERK = %.1f m/s^3."
          % MAX_LATERAL_JERK)
    print("    ⇒ ramp duration T = |delta a| / MAX_LATERAL_JERK, INDEPENDENT of speed.")
    print("    A ramp of duration T has |sinc(fT)| spectrum: NULLS at f = n/T.")
    print("\n    %-28s %8s %9s %10s %10s %12s"
          % ("maneuver edge", "|da|", "ramp T s", "1st null", "nulls<15Hz", "atten @8 Hz"))
    OUT = {}
    for name, da in (("step onset  (0 -> 0.5)", 0.5),
                     ("step REVERSAL (+.5->-.5)", 1.0),
                     ("release  (-0.5 -> 0)", 0.5)):
        T = da / MAX_LATERAL_JERK
        nulls = [n / T for n in range(1, 20) if n / T <= 15]
        at8 = abs(np.sinc(8.0 * T))
        print("    %-28s %8.2f %9.3f %10.2f %10s %12s"
              % (name, da, T, 1 / T, ",".join("%.1f" % x for x in nulls) or "-",
                 "%.1f dB" % (20 * np.log10(max(at8, 1e-9)))))
        OUT[name] = dict(da=da, T=T, first_null=1 / T, atten8_db=float(20 * np.log10(max(at8, 1e-9))))

    print("\n    RELATIVE EXCITATION over 6-14 Hz, normalised to an ideal step (=0 dB):")
    print("    %-28s %s" % ("edge", "".join("%9s" % ("%gHz" % f) for f in (6, 7, 8, 9, 10, 12, 14))))
    for name, da in (("step onset", 0.5), ("step REVERSAL", 1.0)):
        T = da / MAX_LATERAL_JERK
        cells = ["%9s" % ("%.1f dB" % (20 * np.log10(max(abs(np.sinc(f * T)), 1e-9))))
                 for f in (6, 7, 8, 9, 10, 12, 14)]
        print("    %-28s %s" % (name, "".join(cells)))

    print("\n    🛑 READ THIS BEFORE COMMITTING THE DRIVE:")
    print("      * the 0.5 m/s^2 edges ramp over 0.100 s -> first null at 10.0 Hz, -12.6 dB at 8 Hz;")
    print("      * the REVERSAL ramps over 0.200 s -> nulls at 5.0 and 10.0 Hz, -18.6 dB at 8 Hz.")
    print("      ⇒ the maneuver DOES excite 6-14 Hz, but 12-19 dB down on an ideal step, and it is")
    print("        BLIND at exactly 10.0 Hz (both edges) and 5.0 Hz (the reversal).")
    print("      ⇒ Two consequences for the analysis, both cheap:")
    print("        1. The input is LOGGED (`lateralManeuverPlan.desiredCurvature` at 20 Hz), so use")
    print("           a TRANSFER-FUNCTION estimate H = T_bar/u, NOT a bare output spectrum.  A sinc")
    print("           null divides out of a ratio everywhere except AT the null.")
    print("        2. Pre-declare 10.0 +/- 0.5 Hz and 5.0 +/- 0.5 Hz as EXCLUDED bins.  Reporting a")
    print("           dip there would be reporting openpilot's jerk limiter.")
    print("      ⚠ `lateralManeuverPlan` is published at 20 Hz (cereal/services.py) => its own")
    print("        Nyquist is 10 Hz.  The COMMAND channel cannot resolve the band we care about;")
    print("        the input must be reconstructed from the 100 Hz `carControl`/`carOutput`")
    print("        actuator record, or from `controlsState.desiredCurvature`, not from the plan msg.")
    return OUT


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    a = part_a(routes)
    b = part_b()
    (HERE / "_scratch/out/_ringdown_real.json").write_text(json.dumps(dict(edges=a, maneuver=b), indent=1,
                                                         default=float))
    print("\nwrote %s" % (HERE / "_scratch/out/_ringdown_real.json"))


if __name__ == "__main__":
    main()
