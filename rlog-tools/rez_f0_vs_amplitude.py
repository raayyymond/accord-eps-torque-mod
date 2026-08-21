#!/usr/bin/env python3
r"""rez_f0_vs_amplitude.py -- DOES f0 MOVE WITH COMMAND AMPLITUDE AT FIXED GAIN?

`pole-hunt`'s question.  Across builds, f0 (the Re(Z) zero crossing) marches with the LKAS gain
cell: 21.90 / 23.61 / 24.90 Hz at 1x / 4x / 6x.  If that is an AMPLITUDE effect -- an observer LERP
whose local slope changes ~10x with signal amplitude, or a slew limiter behaving the same way --
then f0 must ALSO move with command amplitude WITHIN one build at fixed gain.  If f0 is
amplitude-invariant within a route, the amplitude mechanism is in trouble and a loop-phase/delay
story is favoured instead.

STRATIFYING VARIABLE: `e4tq`, openpilot's commanded torque on **0x0E4**.
  * It is the COMMAND in the ordinary sense and sits UPSTREAM of the ECU.
  * 🛑 ANTI-CIRCULARITY: Re(Z) is computed from `tq` x `rate_f`, both fields of **0x18F**.  0x0E4 is
    a different message, so the stratifying variable shares no quantisation with the estimate.
    Stratifying on `tq` itself would be circular -- `tq` is the Re(Z) numerator channel.

🛑 THE CONFOUND THAT GOVERNS THIS TEST: **f0 already varies with SPEED.**  On V102, Re(Z) at
   22-26 Hz is -134/-99 at 29-86 km/h but +80 [-60,+155] at 86-115 km/h.  Command amplitude
   correlates with speed and with cornering, so an unmatched amplitude split would return a SPEED
   contrast wearing an amplitude label.  Every split below is therefore taken INSIDE the endpoint's
   own 29-86 km/h band, and the per-stratum speed / wheel-rate census is printed so the reader can
   see whether the strata are actually matched.

TWO ESTIMATORS, because the split-into-thirds version is weak:
  A) f0 per amplitude stratum (interpretable, but ~17 windows per stratum on V102).
  B) per-window Re(Z) at a fixed band regressed on log|e4tq| (noisier per point, more power in
     aggregate).  A control band is carried in both.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L          # noqa: E402
import decode_v90_probe as P     # noqa: E402
import rez_crossover as X        # noqa: E402  -- reuse f0_of / FIT, unchanged

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(104_2026)
VLO, VHI = 8.0, 24.0
OUT = {}


def wins(route):
    """Engaged, hands-off, moving windows in 29-86 km/h, carrying the 0x0E4 command."""
    R = L.ROUTES[route]
    z = np.load(R["cache"] / ("r" + route + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    W = P._wins(lat & (~press) & (v > 0.5), t, P.NW_Z, P.HOP_Z,
                (np.asarray(z["rate_f"], float) * np.pi / 180.0,
                 np.asarray(z["tq"], float), v,
                 np.abs(np.asarray(z["e4tq"], float)),
                 np.abs(np.asarray(z["rate_c"], float))))
    W = [w for w in W if VLO <= float(np.median(w[2])) < VHI]
    return W, 1.0 / float(np.median(np.diff(t)))


def f0_ci(pairs, fs, nboot=250):
    pt = X.f0_of(pairs, fs)
    bs = [v for v in (X.f0_of([pairs[k] for k in RNG.integers(0, len(pairs), len(pairs))], fs)
                      for _ in range(nboot)) if np.isfinite(v)]
    if len(bs) < 20:
        return pt, np.nan, np.nan
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return pt, float(lo), float(hi)


def part_a(route, lab, nstrata=3):
    W, fs = wins(route)
    if len(W) < 3 * 8:
        print("\n  %-11s only %d windows -- NOT SCOREABLE for a %d-way split"
              % (lab, len(W), nstrata))
        return
    amp = np.array([float(np.median(w[3])) for w in W])
    qs = np.percentile(amp, np.linspace(0, 100, nstrata + 1))
    print("\n  --- %s : %d windows, split into %d strata by median |0x0E4 command| ---"
          % (lab, len(W), nstrata))
    print("      %-8s %5s %12s %10s %10s %10s   %s"
          % ("stratum", "n", "|cmd| p50", "v p50 m/s", "rate p50", "|tq| p50", "f0 [95% CI]"))
    rows = []
    for i in range(nstrata):
        lo_q, hi_q = qs[i], qs[i + 1]
        sel = [w for w, a in zip(W, amp) if (lo_q <= a <= hi_q if i == nstrata - 1
                                             else lo_q <= a < hi_q)]
        if len(sel) < 8:
            print("      %-8s %5d  -- too few" % ("s%d" % (i + 1), len(sel)))
            continue
        pairs = [(w[0], w[1]) for w in sel]
        pt, clo, chi = f0_ci(pairs, fs)
        vp = float(np.median([np.median(w[2]) for w in sel]))
        rp = float(np.median([np.median(w[4]) for w in sel]))
        tp = float(np.median([np.median(np.abs(w[1])) for w in sel]))
        ap = float(np.median([np.median(w[3]) for w in sel]))
        print("      %-8s %5d %12.0f %10.2f %10.2f %10.0f   %.2f [%.2f, %.2f]"
              % ("s%d" % (i + 1), len(sel), ap, vp, rp, tp, pt, clo, chi))
        rows.append(dict(stratum=i + 1, n=len(sel), cmd=ap, v=vp, rate=rp, tq=tp,
                         f0=pt, lo=clo, hi=chi))
    if len(rows) >= 2:
        d = rows[-1]["f0"] - rows[0]["f0"]
        disj = rows[-1]["lo"] > rows[0]["hi"] or rows[0]["lo"] > rows[-1]["hi"]
        print("      ==> HIGH - LOW = %+.2f Hz over a %.1fx command range   CIs %s"
              % (d, rows[-1]["cmd"] / max(rows[0]["cmd"], 1e-9),
                 "DISJOINT" if disj else "OVERLAP"))
        vr = rows[-1]["v"] / max(rows[0]["v"], 1e-9)
        print("      speed ratio across strata %.2fx  %s"
              % (vr, "(matched)" if 0.85 <= vr <= 1.18 else
                 "🛑 (NOT matched -- this split is partly a SPEED contrast)"))
    OUT.setdefault("A", {})[route] = dict(build=lab, strata=rows)


def part_b(route, lab):
    """Per-window Re(Z) regressed on log|command|.  More power than a 3-way split."""
    W, fs = wins(route)
    if len(W) < 16:
        return
    wn = np.hanning(P.NW_Z)
    _ = wn
    rows = []
    for w in W:
        r = P._band_transfer([(w[0], w[1])], fs, P.NW_Z,
                             [("t", 22.0, 26.0), ("c", 31.0, 35.0)])
        rows.append((float(np.median(w[3])), r["t"]["re_over_sxx"], r["c"]["re_over_sxx"],
                     float(np.median(w[2]))))
    a = np.array([x[0] for x in rows], float)
    good = a > 1.0
    a, t22, c31, vv = (np.array([x[0] for x in rows])[good],
                       np.array([x[1] for x in rows])[good],
                       np.array([x[2] for x in rows])[good],
                       np.array([x[3] for x in rows])[good])
    la = np.log(a)
    print("\n  --- %s : per-window Re(Z) regressed on log|command|, n=%d ---" % (lab, len(a)))
    for nm, y in (("22-26 (target)", t22), ("31-35 (control)", c31)):
        sl = np.polyfit(la, y, 1)[0]
        bs = []
        for _ in range(2000):
            j = RNG.integers(0, len(la), len(la))
            bs.append(np.polyfit(la[j], y[j], 1)[0])
        blo, bhi = np.percentile(bs, [2.5, 97.5])
        # partial out speed: regress both on log v first
        ry = y - np.polyval(np.polyfit(np.log(vv), y, 1), np.log(vv))
        rx = la - np.polyval(np.polyfit(np.log(vv), la, 1), np.log(vv))
        slp = np.polyfit(rx, ry, 1)[0]
        bsp = []
        for _ in range(2000):
            j = RNG.integers(0, len(rx), len(rx))
            bsp.append(np.polyfit(rx[j], ry[j], 1)[0])
        plo, phi = np.percentile(bsp, [2.5, 97.5])
        print("      %-16s slope %+9.0f [%+8.0f,%+8.0f] per e-fold of command"
              % (nm, sl, blo, bhi))
        print("      %-16s   speed-partialled  %+9.0f [%+8.0f,%+8.0f]   %s"
              % ("", slp, plo, phi, "SIGNIFICANT" if (plo > 0) == (phi > 0) else "n.s."))
        OUT.setdefault("B", {}).setdefault(route, {})[nm] = dict(
            slope=float(sl), lo=float(blo), hi=float(bhi),
            slope_partialled=float(slp), plo=float(plo), phi=float(phi))


if __name__ == "__main__":
    L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0,
                           bits="stock")
    L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3,
                           bits="v102")
    print("=" * 104)
    print("A -- f0 BY COMMAND-AMPLITUDE STRATUM, inside 29-86 km/h")
    print("=" * 104)
    for rt, lab, ns in (("96", "V102 6x", 3), ("96", "V102 6x (halves)", 2),
                        ("97", "STOCK 1x", 3), ("97", "STOCK 1x (halves)", 2),
                        ("85", "V100 4x (halves)", 2)):
        part_a(rt, lab, ns)
    print("\n" + "=" * 104)
    print("B -- PER-WINDOW Re(Z) vs log|command|, speed partialled out")
    print("=" * 104)
    for rt, lab in (("96", "V102 6x"), ("97", "STOCK 1x"), ("85", "V100 4x")):
        part_b(rt, lab)
    Path(__file__).with_name("_rez_f0_vs_amplitude.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _rez_f0_vs_amplitude.json")
