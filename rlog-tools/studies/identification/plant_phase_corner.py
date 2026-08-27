#!/usr/bin/env python3
r"""THE SCALE-FREE RESULT -- b_w/J_w from arg(Z) alone, and the Q it forces on any wheel mode.

WHY PHASE AND NOT MAGNITUDE
  `studies/identification/plant_fit_final.py` fitted |Z|^2 = J^2 w^2 + b^2 and got R^2 = 0.01-0.32 with arms dropping out:
  **the magnitude fit is NOT supported by these logs** and its J_w / f_n numbers are withdrawn.
  Two things poison the magnitude and neither touches the phase:
    * the deg/s SCALE is ambiguous (`rate_c` == 1.25 x `rate_f`), which multiplies J and b together;
    * something rolls |Z| off above ~13 Hz (`studies/identification/plant_zcurve.py` §1), un-modelled.
  A RATIO of the two terms is immune to both.  For a passive upper column, hands off,

        Z(jw) = -(J_w s + b_w)      =>      |arg Z| = 180deg - atan(J_w w / b_w)

  so  **tan(180 - |arg Z|) / w  =  J_w / b_w**, a pure TIME CONSTANT in seconds, independent of the
  counts scale, of the deg/s scale, and of any common gain on either channel.

WHAT IT DECIDES
  For the wheel-on-torsion-bar mode  J th'' + b th' + k th = k th_p:
        w_n = sqrt(k/J)        zeta = b/(2 sqrt(kJ)) = (b/J) / (2 w_n)        Q = 1/(2 zeta)
  So b/J and an ASSUMED f_n immediately give Q, with NO k and NO scale:
        Q(f_n) = 2 * 2pi * f_n / (2 * (b/J)) = 2pi f_n / (b/J)
  🛑 The kit's measured line is 8.16 Hz at Q ~ 10.  This file asks whether the column's own
  measured b/J can support Q = 10 at 8.16 Hz.

CONTROLS
  * the ratio must be CONSTANT in f across the band -- that constancy IS the model test, and it is
    printed per 1 Hz bin before any pooled number.
  * episode bootstrap (`feedback-episodes-not-windows`).
  * every route carried separately; a result that only appears on one build is not a plant result.
  * ENGAGED and MANUAL both attempted.  ⚠ Engaged, the assist loop contributes to the apparent
    `b_w`; since the kit measures the loop as ANTI-damping at 6-9 Hz, the engaged `b_w` is if
    anything an UNDER-estimate of the passive one, which makes the Q below an UPPER BOUND.
"""
from __future__ import annotations
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, NFFT = L.FS, 1024
F = np.fft.rfftfreq(NFFT, 1 / FS)
HOLD_OFF, HOLD_ON = 300.0, 1200.0
BINS = (4, 5, 6, 7, 8, 9, 10)
F_LO, F_HI, COH_MIN, NBOOT = 4.0, 10.5, 0.30, 3000
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, LAB.get(rt, rt), gain=0, clamp=0, leverB=False, idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 104); print(s); print("=" * 104, flush=True)


def episodes(rt):
    eps = []
    for blk in L.all_blocks(rt):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        tq, r = np.asarray(blk["tq"], float), np.asarray(blk["rate_f"], float)
        cuts = [0] + list(np.flatnonzero(np.diff(lat.astype(int))) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s >= NFFT:
                eps.append(dict(lat=bool(lat[s]), tq=tq[s:e], r=r[s:e]))
    return eps


def wins(ep, hold):
    w = np.hanning(NFFT)
    out = []
    for i in range(0, len(ep["tq"]) - NFFT, NFFT // 2):
        y = ep["tq"][i:i + NFFT]
        if hold == "off" and not (np.percentile(np.abs(y), 90) < HOLD_OFF):
            continue
        if hold == "on" and not (np.percentile(np.abs(y), 50) >= HOLD_ON):
            continue
        x = ep["r"][i:i + NFFT]
        X = np.fft.rfft((x - x.mean()) * w)
        Y = np.fft.rfft((y - y.mean()) * w)
        out.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
    return out


def pool(ws):
    return tuple(np.sum([w[i] for w in ws], axis=0) for i in range(3))


def tau_of(ws, f_lo=F_LO, f_hi=F_HI, coh_min=COH_MIN):
    """Coherence-weighted pooled J/b, in seconds, over the band."""
    Sxx, Sxy, Syy = pool(ws)
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    H = Sxy / np.maximum(Sxx, 1e-30)
    m = (F >= f_lo) & (F <= f_hi) & (ch >= coh_min)
    if m.sum() < 8:
        return np.nan
    a = 180.0 - np.abs(np.angle(H[m], deg=True))          # = atan(J w / b), degrees
    ok = (a > 3.0) & (a < 87.0)                            # outside this the ratio is unresolvable
    if ok.sum() < 6:
        return np.nan
    tau = np.tan(np.radians(a[ok])) / (2 * np.pi * F[m][ok])
    return float(np.average(tau, weights=ch[m][ok]))


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]

    hdr("1.  MODEL TEST -- tan(180 - |arg Z|)/w must be CONSTANT in f if the column is J s + b")
    print("    Value printed is J_w/b_w in MILLISECONDS.  ENGAGED, HANDS-OFF.  (coh) beside it.")
    print("    🛑 A resonance at 8 Hz would make this quantity swing wildly through 8 Hz.")
    print("\n    %-11s %5s %s" % ("route", "nep", "".join("%15s" % ("%g Hz" % f) for f in BINS)))
    percurve = {}
    for rt in routes:
        eps = [e for e in episodes(rt) if e["lat"]]
        per = [w for w in (wins(e, "off") for e in eps) if len(w) >= 1]
        if len(per) < 3:
            continue
        Sxx, Sxy, Syy = pool([w for p in per for w in p])
        ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
        cells, vals = [], []
        for f0 in BINS:
            m = (F >= f0 - 0.5) & (F < f0 + 0.5)
            h = Sxy[m].sum() / Sxx[m].sum()
            a = 180.0 - abs(np.angle(h, deg=True))
            c = float(np.median(ch[m]))
            if not (3 < a < 87) or c < 0.15:
                cells.append("%15s" % "--"); continue
            t = np.tan(np.radians(a)) / (2 * np.pi * f0)
            cells.append("%15s" % ("%.1f ms (%.2f)" % (t * 1000, c)))
            vals.append(t)
        print("    %-11s %5d %s" % (LAB.get(rt, rt), len(per), "".join(cells)))
        if len(vals) >= 4:
            percurve[rt] = dict(vals=[float(v) for v in vals],
                                cv=float(np.std(vals) / np.mean(vals)))
    print("\n    coefficient of variation of J/b ACROSS the 4-10 Hz bins (a resonance would blow "
          "this up):")
    for rt, d in percurve.items():
        print("      %-11s CV = %.3f   (%d bins, mean %.1f ms)"
              % (LAB.get(rt, rt), d["cv"], len(d["vals"]), 1000 * np.mean(d["vals"])))

    hdr("2.  POOLED J_w/b_w, EPISODE BOOTSTRAP -- and the Q it forces on an 8.16 Hz wheel mode")
    print("    Q(f_n) = 2 pi f_n / (b_w/J_w).  🛑 THE KIT'S LINE IS 8.16 Hz AT Q ~ 10.")
    print("\n    %-11s %-8s %-5s %4s %18s %16s %14s %16s"
          % ("route", "arm", "hold", "nep", "J/b [95% CI] ms", "b/J [CI] rad/s",
             "Q @8.16 Hz [CI]", "f_n for Q=10 Hz"))
    OUT = {}
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                eps = [e for e in episodes(rt) if e["lat"] == lat]
                per = [w for w in (wins(e, hold) for e in eps) if len(w) >= 1]
                if len(per) < 3:
                    continue
                t0 = tau_of([w for p in per for w in p])
                if not np.isfinite(t0):
                    continue
                rng = np.random.default_rng(2718)
                B = []
                for _ in range(NBOOT):
                    pk = rng.integers(0, len(per), len(per))
                    t = tau_of([w for i in pk for w in per[i]])
                    if np.isfinite(t) and t > 0:
                        B.append(t)
                if len(B) < 200:
                    continue
                lo, hi = np.percentile(B, 2.5), np.percentile(B, 97.5)
                q = lambda tt: 2 * np.pi * 8.16 * tt
                fq10 = lambda tt: 10.0 / (2 * np.pi * tt)
                print("    %-11s %-8s %-5s %4d %18s %16s %14s %16s"
                      % (LAB.get(rt, rt), latl, hold, len(per),
                         "%.1f [%.1f,%.1f]" % (t0 * 1e3, lo * 1e3, hi * 1e3),
                         "%.1f [%.1f,%.1f]" % (1 / t0, 1 / hi, 1 / lo),
                         "%.2f [%.2f,%.2f]" % (q(t0), q(lo), q(hi)),
                         "%.1f [%.1f,%.1f]" % (fq10(t0), fq10(hi), fq10(lo))))
                OUT["%s|%s|%s" % (rt, latl, hold)] = dict(
                    tau_ms=t0 * 1e3, ci_ms=[lo * 1e3, hi * 1e3], nep=len(per),
                    Q_at_816=q(t0), Q_ci=[q(lo), q(hi)], fn_for_Q10=fq10(t0))

    hdr("3.  THE CONCLUSION, STATED SO IT CAN BE FALSIFIED")
    eng = [v for k, v in OUT.items() if k.endswith("engaged|off")]
    if eng:
        qs = np.array([v["Q_at_816"] for v in eng])
        ts = np.array([v["tau_ms"] for v in eng])
        print("    engaged hands-off arms: n = %d routes, J/b = %.1f-%.1f ms"
              % (len(eng), ts.min(), ts.max()))
        print("    => a wheel-on-torsion-bar mode AT 8.16 Hz would have Q = %.2f - %.2f "
              "(zeta %.3f - %.3f)" % (qs.min(), qs.max(), 1 / (2 * qs.max()), 1 / (2 * qs.min())))
        print("    => for the column's own damping to permit Q = 10, the mode would have to sit at "
              "%.0f - %.0f Hz." % (min(v["fn_for_Q10"] for v in eng),
                                   max(v["fn_for_Q10"] for v in eng)))
        print("\n    🛑 FALSIFIERS, pre-registered:")
        print("      * a MANUAL (LKAS-off) hands-off arm with coh >= 0.30 at 4-10 Hz returning")
        print("        J/b more than ~3x larger than the engaged arms -- that would mean the")
        print("        engaged number is a loop artefact and the passive column is lightly damped.")
        print("      * arg(Z) swinging through 8 Hz (CV of the per-bin ratio > ~0.5) on a route")
        print("        with coh >= 0.5 -- that IS a passive resonance and this conclusion dies.")
        print("      * an independent k measurement placing sqrt(k/J)/2pi at 8.16 Hz WITH a")
        print("        measured zeta near 0.05 -- mutually inconsistent with J/b measured here.")
    (HERE / "_scratch/out/_plant_phase_corner.json").write_text(json.dumps(dict(fits=OUT, percurve=percurve),
                                                              indent=1, default=float))
    print("\nwrote %s" % (HERE / "_scratch/out/_plant_phase_corner.json"))


if __name__ == "__main__":
    main()
