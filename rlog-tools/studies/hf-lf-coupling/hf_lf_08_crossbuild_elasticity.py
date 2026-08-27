#!/usr/bin/env python3
r"""THE TEST THAT SETTLES IT -- DOES THE RATCHET SCALE WITH THE CARRIER ACROSS BUILDS?

🛑 WHY THE WITHIN-DRIVE DISCRIMINATOR CANNOT DECIDE THIS, AND HOW `hf_lf_07` PROVED IT
  `hf_lf_07` calibrated the within-drive tercile discriminator against synthetic records built from
  each arm's OWN data -- a ONE-mechanism record whose 6-12 Hz content is a demodulation of the
  carrier, and a TWO-mechanism record whose 6-12 Hz content is independent.  On the 6x builds the
  real data matched ONE-mechanism and excluded TWO.  It then ran the SAME test on STOCK, where the
  21-28 Hz carrier is 1/16 of the 6x level and the kit has already shown it never sustains for one
  second -- and STOCK MATCHED ONE-MECHANISM TOO (real 0.259, ONE 0.282, TWO 0.584).
  ⇒ a carrier that is not there cannot be causing anything, so the pattern is produced by the
     COMMON DRIVER (steering activity), not by the carrier.  **The within-drive discriminator is
     therefore not diagnostic, and any verdict resting on it is void.**  This file replaces it.

THE TEST THAT IS DIAGNOSTIC -- CROSS-BUILD ELASTICITY
  `0xC6CD0` moves the carrier by a factor the kit has already measured at ~90x between stock and 6x
  (`HANDOFF-2026-08-22` s5.3; in-burst level 0.88 -> 14.9).  That is a controlled, deliberate,
  cross-build intervention on the CARRIER ALONE.
    IF the ratchet is the carrier's envelope / demodulation product, its amplitude is proportional
       to the carrier's -- an AM sideband pair scales as m x A, a rectified envelope as A.  Then
       ratchet(6x)/ratchet(stock) must be of the SAME ORDER as carrier(6x)/carrier(stock).
    IF the ratchet is its own mode, carrier(6x)/carrier(stock) >> ratchet(6x)/ratchet(stock) ~ 1.
  The elasticity  E = log[ratchet ratio] / log[carrier ratio]  is 1 for a pure by-product and 0 for
  an independent mode.  It needs no envelope estimator, no surrogate, and no assumption about the
  demodulating nonlinearity -- only that more carrier makes more by-product, which is true of every
  demodulation there is.

CONTROLS, ALL PRE-DECLARED AND ALL RUN BEFORE THE NUMBER IS READ
  K1 SPEED-MATCHED and RATE-MATCHED cells.  The carrier is a steering-RATE phenomenon
     (`HANDOFF-2026-08-22` s5.3), so every cell is (speed arm x |rate_c| bin) and the per-cell
     rate and speed census is printed.  A cross-build ratio taken over unmatched exposure is the
     failure mode `accord-averaged-spectrum-needs-matched-speed-distributions` was written for.
  K2 The 32-38 Hz CONTROL BAND carries the identical computation.  A drive-level offset -- `a4` is
     genuinely a quieter drive than `r9e` across 6-45 Hz (`HANDOFF-2026-08-22` s4.4) -- moves every
     band together, so the control band is subtracted as a PLACEBO before the elasticity is read.
  K3 EPISODE bootstrap for every CI (`feedback-episodes-not-windows`), plus a split-half episode
     null on each ratio.  No window bootstrap anywhere.
  K4 A BEAT CENSUS restricted to peak pairs BOTH above 15 Hz.  Two carrier-region lines separated
     by 6-12 Hz would produce a genuine 6-12 Hz envelope by beating -- a different mechanism from
     AM with the same felt result -- and it must be excluded rather than assumed away.
  K5 THE THREE-MODEL CALIBRATION, rebuilt.  `hf_lf_07`'s ONE-mechanism synthetic was contaminated:
     the analytic envelope of a 7 Hz-wide band carries almost nothing at 6-12 Hz, so its
     "demodulation" was mostly estimator noise.  Here M1 is  env_carrier(t) x an 8 Hz tone, which
     is the clean physical model, M2 is the COMMON-CAUSE model (independent 6-12 Hz noise whose
     amplitude follows smoothed |rate_c|, i.e. the shared driver with NO carrier involvement), and
     M3 is flat independent noise.  A partial regression separates them:
         log(rat) ~ b_car log(car) + b_ctrl log(ctrl) + b_rate log(|rate|) + b_v log(v)
     b_car is what survives after the common drivers are removed.  M1 must show b_car > 0; M2 must
     show b_car ~ 0 with b_rate > 0.  The real data is read against both.

OUTPUT `rlog-tools/_scratch/out/_hf_lf_elasticity.json`
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
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402
from hf_lf_06_envelope_discriminator import (CARRIER, CTRL1, FREQ, FS, NSEG, RATCHET,  # noqa: E402
                                             ROUTE_LABEL, WHOP, WSEG, analytic_env, band_rms,
                                             episodes, hdr, parts, reg, welch_P)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = ["97", "85", "96", "9e", "a4", "a5"]
GAIN = {"97": 1, "85": 4, "96": 6, "9e": 6, "a4": 6, "a5": 6}
ARMS = [("hwy", 70.0, 200.0), ("mid", 40.0, 70.0), ("low", 16.0, 40.0), ("micro", 0.0, 16.0)]
RATE_BINS = [(0.0, 5.0), (5.0, 15.0), (15.0, 40.0), (40.0, 1e9)]
RNG0 = 24680
NBOOT = 2000


def windows(eps):
    rows = []
    for ei, e in enumerate(eps):
        x = np.asarray(e["tq"], float)
        v = np.asarray(e["_vall"], float)
        rc = np.abs(np.asarray(e.get("rate_c", np.zeros_like(x)), float))
        for s in range(0, len(x) - WSEG + 1, WHOP):
            y = x[s:s + WSEG]
            rows.append(dict(ep=ei, car=band_rms(y, *CARRIER), rat=band_rms(y, *RATCHET),
                             ctl=band_rms(y, *CTRL1),
                             v=float(np.median(v[s:s + WSEG])),
                             rate=float(np.median(rc[s:s + WSEG]))))
    return rows


def boot_med(rows, key, rng, n=NBOOT):
    by = {}
    for r in rows:
        by.setdefault(r["ep"], []).append(r[key])
    ks = list(by)
    if not ks:
        return np.nan, (np.nan, np.nan)
    obs = float(np.median([r[key] for r in rows]))
    if len(ks) < 2:
        return obs, (np.nan, np.nan)
    bs = []
    for _ in range(n):
        pick = rng.choice(ks, size=len(ks), replace=True)
        bs.append(float(np.median([v for k in pick for v in by[k]])))
    return obs, (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def boot_ratio(a_rows, b_rows, key, rng, n=NBOOT):
    """Ratio of medians, EPISODE bootstrap on both sides independently."""
    def by(rs):
        d = {}
        for r in rs:
            d.setdefault(r["ep"], []).append(r[key])
        return d
    A, B = by(a_rows), by(b_rows)
    ka, kb = list(A), list(B)
    if not ka or not kb:
        return np.nan, (np.nan, np.nan)
    obs = (float(np.median([r[key] for r in a_rows]))
           / max(float(np.median([r[key] for r in b_rows])), 1e-12))
    bs = []
    for _ in range(n):
        pa = rng.choice(ka, size=len(ka), replace=True)
        pb = rng.choice(kb, size=len(kb), replace=True)
        va = [v for k in pa for v in A[k]]
        vb = [v for k in pb for v in B[k]]
        if va and vb:
            bs.append(float(np.median(va)) / max(float(np.median(vb)), 1e-12))
    if not bs:
        return obs, (np.nan, np.nan)
    return obs, (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def splithalf(rows, key, rng, n=400):
    by = {}
    for r in rows:
        by.setdefault(r["ep"], []).append(r[key])
    ks = list(by)
    if len(ks) < 4:
        return None
    h = len(ks) // 2
    out = []
    for _ in range(n):
        k = list(rng.permutation(ks))
        a = [v for kk in k[:h] for v in by[kk]]
        b = [v for kk in k[h:] for v in by[kk]]
        if a and b:
            out.append(float(np.median(a)) / max(float(np.median(b)), 1e-12))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))] if out else None


def beat_census(car):
    """K4 -- separations between spectral peaks BOTH above 15 Hz.  Only such a pair can beat into
    6-12 Hz; separations that involve the 6-12 Hz line itself are circular and are excluded."""
    P = welch_P(parts(car))
    m = (FREQ >= 15.0) & (FREQ <= 45.0)
    idx = np.flatnonzero(m)
    pk = [i for i in idx[1:-1] if P[i] > P[i - 1] and P[i] > P[i + 1]]
    pk.sort(key=lambda i: -P[i])
    top = []
    for i in pk[:6]:
        f0 = FREQ[i]
        bg = (np.abs(FREQ - f0) <= 2.0) & (np.abs(FREQ - f0) > 0.5)
        top.append((float(f0), float(P[i] / max(float(np.median(P[bg])), 1e-30))))
    seps = sorted({round(abs(a[0] - b[0]), 2) for a in top for b in top
                   if 6.0 <= abs(a[0] - b[0]) <= 12.0})
    return top, seps


# ----------------------------------------------------------- K5 three-model calibration ---------
def bandlimit(x, lo, hi):
    X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
    f = np.fft.rfftfreq(len(x), 1.0 / FS)
    return np.fft.irfft(np.where((f >= lo) & (f < hi), X, 0.0), n=len(x))


def replace_band(x, new):
    x = np.asarray(x, float)
    keep = x - bandlimit(x, *RATCHET)
    tgt = band_rms(x, *RATCHET)
    nb = bandlimit(new, *RATCHET)
    s = np.sqrt(np.mean(nb ** 2))
    return keep + (nb * (tgt / s) if s > 1e-12 else nb)


def smooth(x, n=100):
    k = np.ones(n) / n
    return np.convolve(np.asarray(x, float), k, mode="same")


def model_records(eps, rng):
    """M1 carrier demodulation · M2 common-cause (rate-driven) · M3 flat independent."""
    m1, m2, m3 = [], [], []
    for e in eps:
        x = np.asarray(e["tq"], float)
        t = np.arange(len(x)) / FS
        env = analytic_env(x, *CARRIER)
        rate = np.abs(np.asarray(e.get("rate_c", np.zeros_like(x)), float))
        drv = smooth(rate) + 1e-6
        drv = drv / max(float(np.median(drv)), 1e-9)
        n1 = env * np.cos(2 * np.pi * 8.0 * t)                       # amplitude = carrier envelope
        n2 = bandlimit(rng.standard_normal(len(x)), *RATCHET) * drv  # amplitude = the COMMON driver
        n3 = bandlimit(rng.standard_normal(len(x)), *RATCHET)        # amplitude = flat
        for dst, nn in ((m1, n1), (m2, n2), (m3, n3)):
            f = dict(e)
            f["tq"] = replace_band(x, nn)
            dst.append(f)
    return m1, m2, m3


def partial_reg(rows):
    """log(rat) ~ b_car log(car) + b_ctrl log(ctrl) + b_rate log(|rate|) + b_v log(v) + c."""
    if len(rows) < 24:
        return None
    lg = lambda k: np.log(np.maximum([r[k] for r in rows], 1e-6))  # noqa: E731
    A = np.column_stack([lg("car"), lg("ctl"), lg("rate"), lg("v"), np.ones(len(rows))])
    y = lg("rat")
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    return dict(b_car=float(b[0]), b_ctrl=float(b[1]), b_rate=float(b[2]), b_v=float(b[3]))


def partial_reg_ci(rows, rng, n=600):
    by = {}
    for r in rows:
        by.setdefault(r["ep"], []).append(r)
    ks = list(by)
    if len(ks) < 2:
        return None
    bs = []
    for _ in range(n):
        pick = rng.choice(ks, size=len(ks), replace=True)
        s = partial_reg([r for k in pick for r in by[k]])
        if s:
            bs.append(s["b_car"])
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else None


def main():
    out = {"gain": GAIN, "carrier": CARRIER, "ratchet": RATCHET, "ctrl": CTRL1, "cells": {},
           "elasticity": {}, "beats": {}, "models": {}}
    rng = np.random.default_rng(RNG0)

    # ------------------------------------------------------------------ the cells ---------------
    W = {}
    for rt in ROUTES:
        if not reg(rt):
            continue
        for arm, vlo, vhi in ARMS:
            eps = episodes(rt, engaged=True, vlo=vlo, vhi=vhi, minlen=NSEG)
            if not eps:
                continue
            rows = windows(eps)
            for lo, hi in RATE_BINS:
                sub = [r for r in rows if lo <= r["rate"] < hi]
                if len(sub) >= 6:
                    W[(rt, arm, lo)] = sub
            if len(rows) >= 6:
                W[(rt, arm, None)] = rows

    hdr("CELL CENSUS -- engaged, speed arm x |rate_c| bin.  n_win / n_ep / median speed / "
        "median |rate|, then band medians with EPISODE-bootstrap 95% CI")
    print("  %-4s %-6s %-9s %5s %4s %7s %7s | %-22s %-22s %-20s"
          % ("rt", "arm", "rate bin", "nwin", "nep", "v", "|rate|",
             "CARRIER 21-28", "RATCHET 6-12", "CTRL 32-38"))
    for (rt, arm, lo), rows in sorted(W.items(), key=lambda kv: (kv[0][1], kv[0][2] is None,
                                                                 kv[0][2] or -1, kv[0][0])):
        nep = len({r["ep"] for r in rows})
        c, cci = boot_med(rows, "car", rng)
        r_, rci = boot_med(rows, "rat", rng)
        x, xci = boot_med(rows, "ctl", rng)
        cell = dict(rt=rt, arm=arm, rate_lo=lo, n_win=len(rows), n_ep=nep,
                    v=float(np.median([q["v"] for q in rows])),
                    rate=float(np.median([q["rate"] for q in rows])),
                    car=c, car_ci=cci, rat=r_, rat_ci=rci, ctl=x, ctl_ci=xci)
        out["cells"]["%s|%s|%s" % (rt, arm, lo)] = cell
        print("  %-4s %-6s %-9s %5d %4d %7.1f %7.1f | %7.3g [%6.3g,%6.3g] %7.3g [%6.3g,%6.3g] "
              "%6.3g [%5.3g,%5.3g]"
              % (rt, arm, "ALL" if lo is None else "%.0f+" % lo, len(rows), nep, cell["v"],
                 cell["rate"], c, cci[0], cci[1], r_, rci[0], rci[1], x, xci[0], xci[1]))

    # ------------------------------------------------------------------ elasticity --------------
    hdr("⭐ THE ELASTICITY  E = log(ratchet ratio) / log(carrier ratio),  6x build vs STOCK (97), "
        "MATCHED on speed arm AND |rate_c| bin")
    print("  E = 1.00 -> the ratchet is a by-product of the carrier (an AM sideband scales as m*A, "
          "a rectified envelope as A)")
    print("  E = 0.00 -> the ratchet is its own mode and does not care what the carrier does")
    print("  🛑 the CTRL band's own ratio is the PLACEBO: a drive-level offset moves every band, so "
          "the placebo-corrected column is the one to read\n")
    print("  %-4s %-6s %-9s %6s %6s | %-24s %-24s %-16s | %-16s %s"
          % ("rt", "arm", "rate bin", "nep_a", "nep_s", "CARRIER x stock", "RATCHET x stock",
             "CTRL x stock", "E raw", "E placebo-corrected"))
    for rt in ROUTES:
        if rt == "97":
            continue
        for arm, _, _ in ARMS:
            for lo in [b[0] for b in RATE_BINS] + [None]:
                a = W.get((rt, arm, lo))
                s = W.get(("97", arm, lo))
                if not a or not s:
                    continue
                cr, cci = boot_ratio(a, s, "car", rng)
                rr, rci = boot_ratio(a, s, "rat", rng)
                xr, xci = boot_ratio(a, s, "ctl", rng)
                if not (np.isfinite(cr) and np.isfinite(rr) and cr > 0 and rr > 0):
                    continue
                E = np.log(rr) / np.log(cr) if abs(np.log(cr)) > 0.2 else np.nan
                # placebo: divide both by the control band's own cross-build ratio
                crp = cr / xr if xr > 0 else np.nan
                rrp = rr / xr if xr > 0 else np.nan
                Ep = (np.log(rrp) / np.log(crp)
                      if (np.isfinite(crp) and crp > 0 and abs(np.log(crp)) > 0.2) else np.nan)
                key = "%s|%s|%s" % (rt, arm, lo)
                out["elasticity"][key] = dict(car_ratio=cr, car_ci=cci, rat_ratio=rr, rat_ci=rci,
                                              ctl_ratio=xr, ctl_ci=xci, E=float(E),
                                              E_placebo=float(Ep),
                                              nep_a=len({q["ep"] for q in a}),
                                              nep_s=len({q["ep"] for q in s}))
                print("  %-4s %-6s %-9s %6d %6d | %7.2f [%6.2f,%7.2f] %7.2f [%6.2f,%7.2f] "
                      "%6.2f [%5.2f,%6.2f] | %+8.3f %+8.3f %s"
                      % (rt, arm, "ALL" if lo is None else "%.0f+" % lo,
                         len({q["ep"] for q in a}), len({q["ep"] for q in s}),
                         cr, cci[0], cci[1], rr, rci[0], rci[1], xr, xci[0], xci[1], E, Ep,
                         "<== carrier moved >3x" if cr > 3 else ""))

    # ------------------------------------------------------------------ K4 beats ----------------
    hdr("K4 BEAT CENSUS -- spectral peaks 15-45 Hz and the separations between them that fall in "
        "6-12 Hz.  A pair of carrier-region lines separated by ~8 Hz WOULD make a real ratchet.")
    for rt in ROUTES:
        if not reg(rt):
            continue
        for arm, vlo, vhi in ARMS:
            eps = episodes(rt, engaged=True, vlo=vlo, vhi=vhi, minlen=NSEG)
            if not eps:
                continue
            top, seps = beat_census([e["tq"] for e in eps])
            out["beats"]["%s|%s" % (rt, arm)] = dict(peaks=top, seps=seps)
            print("  %-4s %-6s peaks: %s" % (rt, arm,
                                             "  ".join("%.2f(%.1f)" % p for p in top)))
            print("        separations in 6-12 Hz: %s" % (seps if seps else "NONE"))

    # ------------------------------------------------------------------ K5 models ---------------
    hdr("K5 THREE-MODEL CALIBRATION -- partial regression  log(rat) ~ b_car log(car) + "
        "b_ctrl log(ctrl) + b_rate log(|rate|) + b_v log(v)")
    print("  M1 carrier demodulation (ratchet amplitude = the carrier's own analytic envelope)  "
          "=> b_car must be POSITIVE")
    print("  M2 COMMON CAUSE (independent 6-12 Hz noise whose amplitude follows smoothed |rate_c|, "
          "carrier not involved) => b_car ~ 0, b_rate > 0")
    print("  M3 flat independent noise => every coefficient ~ 0\n")
    print("  %-4s %-6s %-14s %8s %8s %8s %8s %s"
          % ("rt", "arm", "record", "b_car", "b_ctrl", "b_rate", "b_v", "b_car 95% CI (episodes)"))
    for rt in ROUTES:
        if not reg(rt):
            continue
        for arm, vlo, vhi in ARMS:
            eps = episodes(rt, engaged=True, vlo=vlo, vhi=vhi, minlen=NSEG)
            if len(eps) < 2:
                continue
            m1, m2, m3 = model_records(eps, rng)
            rec = {}
            for nm, ee in (("M1 demod", m1), ("M2 commoncause", m2), ("M3 independent", m3),
                           ("REAL", eps)):
                rows = windows(ee)
                st = partial_reg(rows)
                if not st:
                    continue
                ci = partial_reg_ci(rows, rng)
                rec[nm] = dict(st, b_car_ci=ci)
                print("  %-4s %-6s %-14s %+8.3f %+8.3f %+8.3f %+8.3f %s"
                      % (rt, arm, nm, st["b_car"], st["b_ctrl"], st["b_rate"], st["b_v"],
                         "" if not ci else "[%+.3f,%+.3f]" % tuple(ci)))
            out["models"]["%s|%s" % (rt, arm)] = rec
            print()

    (HERE / "_scratch/out/_hf_lf_elasticity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", HERE / "_scratch/out/_hf_lf_elasticity.json")


if __name__ == "__main__":
    main()
