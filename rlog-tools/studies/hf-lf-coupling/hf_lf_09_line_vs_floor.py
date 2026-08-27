#!/usr/bin/env python3
r"""O1 + O2 -- DOES THE 6-12 Hz BAND SPLIT INTO A GAIN-DRIVEN LINE AND A GAIN-BLIND FLOOR?

O1 -- WHY.  `hf_lf_08` measured a cross-build elasticity  E = log(ratchet ratio)/log(carrier ratio)
  with a placebo-corrected MEDIAN OF 0.406 -- reliably above 0, reliably below 1.  Reading the peak
  locations afterwards showed why that may be a MIXTURE rather than a mechanism:

    every 6x build puts the ratchet peak at 7.62-8.40 Hz in ALL SIXTEEN arms (spread 0.78 Hz)
    while its carrier swings 7.03 Hz (a5: 26.76 hwy -> 20.12 micro);
    STOCK has no such line at all -- its 5.5-12.5 Hz argmax lands on the WINDOW EDGES
    (12.30 / 12.30 / 5.86 Hz in 3 of 4 arms), i.e. an argmax riding a 1/f slope.

  ⇒ the 6-12 Hz band plausibly holds TWO things: a broadband FLOOR that stock also has, and a
  narrow ~8 Hz LINE that arrives with the gain.  A band-RMS statistic pools them, and a mixture of
  an E~1 component and an E~0 component produces exactly a partial elasticity.

  🛑 PRE-REGISTERED BEFORE RUNNING, and already stated to the orchestrator in those words:
        LINE  E ~ 1        FLOOR  E ~ 0
  If it holds, "partial coupling" dissolves and V106's target narrows to the line.  If it fails --
  if the line's elasticity is also ~0.4, or the floor's is also ~1 -- the mixture explanation is
  WRONG and E = 0.406 is a real partial coupling.  Both outcomes are reported.

  DECOMPOSITION, fixed in advance so no frequency is chosen after seeing an answer:
    LINE WINDOW  7.4-8.6 Hz -- FIXED, not per-route.  It is the smallest symmetric window that
        contains ALL SIXTEEN observed 6x peaks (7.62 ... 8.40).  🛑 A per-route argmax would compare
        DIFFERENT SPECTRAL FEATURES across builds -- on stock it would land on a window edge -- and
        the whole point is to measure the SAME feature on every build.
    BACKGROUND   median PSD over 6-12 Hz EXCLUDING 7.0-9.0 Hz (a wider exclusion than the line
        window, so the line's own skirts cannot inflate its background).
    P_line  = max(0, sum(PSD over the line window) - background x n_bins_in_window)   <- EXCESS
    P_floor = background x n_bins_in_6_12                                             <- BROADBAND
  Reported as RMS-equivalents (sqrt of power) so they are directly comparable to `hf_lf_08`'s
  band RMS numbers.

O2 -- ADD ROUTE 95 (V101, 8x).  `hf_lf_08` used 97/85/96/9e/a4/a5 and left the 8x point out, so
  every elasticity there is a TWO-POINT ratio against stock.  With 95 the ladder is
  1x / 4x / 6x / 8x and the elasticity becomes a DOSE-RESPONSE SLOPE:
        beta_band = d log(band power) / d log(gain)   fitted across routes within a matched cell
        E_dose    = beta_band / beta_carrier
  A slope over four doses is far harder to fake than a ratio over two, and 95 is also one of the
  only two routes where 427 carries the real `gp-0x6b94` sum.

CONTROLS -- unchanged from `hf_lf_08` and all still in force
  * cells matched on SPEED ARM x |rate_c| BIN; per-cell speed and rate census printed.
  * CTRL 32-38 Hz carried through every computation as the PLACEBO (⚠ overlaps wheel order 3).
  * EPISODE bootstrap for every CI; no window bootstrap anywhere.
  * `tq` (0x18F) only.  Never 427 for a magnitude.
  🛑 NOT re-run here because they already passed and nothing in this file changes them: the AM
  injection ladder (m < 0.05), the false-alarm envelope null, the three-model T3 calibration.

WINDOW LENGTH.  512 samples (5.12 s, 0.1953 Hz bins) rather than `hf_lf_08`'s 256, because the
line window is +-0.6 Hz: at 0.39 Hz bins that is 3 bins and the decomposition is meaningless.
Fewer windows per episode; the episode bootstrap absorbs it.

OUTPUT `rlog-tools/_scratch/out/_hf_lf_linefloor.json`
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
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402
from hf_lf_06_envelope_discriminator import (CARRIER, CTRL1, FS, NSEG, RATCHET,  # noqa: E402
                                             band_rms, episodes, hdr, reg)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = ["97", "85", "96", "9e", "a4", "a5", "95"]
GAIN = {"97": 1.0, "85": 4.0, "96": 6.0, "9e": 6.0, "a4": 6.0, "a5": 6.0, "95": 8.0}
LABEL = {"97": "STOCK 1x", "85": "V100 4x", "96": "V102 6x", "9e": "V103 6x",
         "a4": "V104 6x", "a5": "V105 6x", "95": "V101 8x"}
ARMS = [("hwy", 70.0, 200.0), ("mid", 40.0, 70.0), ("low", 16.0, 40.0), ("micro", 0.0, 16.0)]
RATE_BINS = [(0.0, 5.0), (5.0, 15.0), (15.0, 40.0), (40.0, 1e9)]

LINE_WIN = (7.4, 8.6)        # FIXED -- contains all 16 observed 6x ratchet peaks
LINE_EXCL = (7.0, 9.0)       # excluded when estimating the background
WSEG, WHOP = 512, 256
KMH = 3.6
RNG0 = 1357911
NBOOT = 2000

_W = np.hanning(WSEG)
_R = np.arange(WSEG, dtype=float)
_SCALE = float(np.mean(_W ** 2))
FQ = np.fft.rfftfreq(WSEG, 1.0 / FS)
DF = float(FQ[1] - FQ[0])

_M_LINE = (FQ >= LINE_WIN[0]) & (FQ <= LINE_WIN[1])
_M_BAND = (FQ >= RATCHET[0]) & (FQ < RATCHET[1])
_M_BG = _M_BAND & ~((FQ >= LINE_EXCL[0]) & (FQ <= LINE_EXCL[1]))
N_LINE, N_BAND = int(_M_LINE.sum()), int(_M_BAND.sum())


def psd(y):
    c = np.polyfit(_R, y, 1)
    X = np.fft.rfft((y - (c[0] * _R + c[1])) * _W)
    P = (np.abs(X) ** 2) * 2.0 / (WSEG ** 2) / _SCALE
    P[0] /= 2.0
    P[-1] /= 2.0
    return P


def decompose(y):
    """(line RMS-equivalent, floor RMS-equivalent) for one window."""
    P = psd(y)
    bg = float(np.median(P[_M_BG]))
    p_line = max(0.0, float(P[_M_LINE].sum()) - bg * N_LINE)
    p_floor = bg * N_BAND
    return float(np.sqrt(p_line)), float(np.sqrt(p_floor))


def windows(eps):
    rows = []
    for ei, e in enumerate(eps):
        x = np.asarray(e["tq"], float)
        v = np.asarray(e["_vall"], float)
        rc = np.abs(np.asarray(e.get("rate_c", np.zeros_like(x)), float))
        for s in range(0, len(x) - WSEG + 1, WHOP):
            y = x[s:s + WSEG]
            ln, fl = decompose(y)
            rows.append(dict(ep=ei, line=ln, floor=fl,
                             car=band_rms(y, *CARRIER), rat=band_rms(y, *RATCHET),
                             ctl=band_rms(y, *CTRL1),
                             v=float(np.median(v[s:s + WSEG])),
                             rate=float(np.median(rc[s:s + WSEG]))))
    return rows


def by_ep(rows, key):
    d = {}
    for r in rows:
        d.setdefault(r["ep"], []).append(r[key])
    return d


def boot_ratio(a_rows, b_rows, key, rng, n=NBOOT):
    A, B = by_ep(a_rows, key), by_ep(b_rows, key)
    ka, kb = list(A), list(B)
    if not ka or not kb:
        return np.nan, (np.nan, np.nan)
    obs = (float(np.median([r[key] for r in a_rows]))
           / max(float(np.median([r[key] for r in b_rows])), 1e-12))
    bs = []
    for _ in range(n):
        va = [v for k in rng.choice(ka, size=len(ka), replace=True) for v in A[k]]
        vb = [v for k in rng.choice(kb, size=len(kb), replace=True) for v in B[k]]
        if va and vb:
            bs.append(float(np.median(va)) / max(float(np.median(vb)), 1e-12))
    if not bs:
        return obs, (np.nan, np.nan)
    return obs, (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def dose_slope(cell_rows, key, rng, n=600):
    """beta = d log(median band power) / d log(gain), fitted across the routes present in a cell.
    CI by resampling EPISODES within each route."""
    rts = [rt for rt in cell_rows if len(cell_rows[rt]) >= 4]
    if len(rts) < 3:
        return None
    g = np.log([GAIN[rt] for rt in rts])
    if np.ptp(g) < 0.3:
        return None
    y = np.log([max(float(np.median([r[key] for r in cell_rows[rt]])), 1e-9) for rt in rts])
    obs = float(np.polyfit(g, y, 1)[0])
    per = {rt: by_ep(cell_rows[rt], key) for rt in rts}
    bs = []
    for _ in range(n):
        yy = []
        for rt in rts:
            ks = list(per[rt])
            vals = [v for k in rng.choice(ks, size=len(ks), replace=True) for v in per[rt][k]]
            yy.append(np.log(max(float(np.median(vals)), 1e-9)) if vals else np.nan)
        yy = np.asarray(yy)
        if np.all(np.isfinite(yy)):
            bs.append(float(np.polyfit(g, yy, 1)[0]))
    return dict(beta=obs, n_routes=len(rts), routes=rts,
                ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else None)


def main():
    rng = np.random.default_rng(RNG0)
    out = {"line_win": LINE_WIN, "line_excl": LINE_EXCL, "gain": GAIN,
           "n_bins_line": N_LINE, "n_bins_band": N_BAND, "df_hz": DF,
           "cells": {}, "elasticity": {}, "dose": {}}

    W = {}
    for rt in ROUTES:
        if not reg(rt):
            print("  route %s: no segments" % rt)
            continue
        for arm, vlo, vhi in ARMS:
            eps = episodes(rt, engaged=True, vlo=vlo, vhi=vhi, minlen=WSEG)
            if not eps:
                continue
            rows = windows(eps)
            for lo, hi in RATE_BINS:
                sub = [r for r in rows if lo <= r["rate"] < hi]
                if len(sub) >= 4:
                    W[(rt, arm, lo)] = sub
            if len(rows) >= 4:
                W[(rt, arm, None)] = rows

    hdr("O1 DECOMPOSITION -- line window %.1f-%.1f Hz (%d bins of %.4f Hz), background = median "
        "PSD over 6-12 Hz excluding %.1f-%.1f Hz, floor = background x %d bins"
        % (LINE_WIN[0], LINE_WIN[1], N_LINE, DF, LINE_EXCL[0], LINE_EXCL[1], N_BAND))
    print("  %-4s %-6s %-6s %5s %4s %7s %7s | %8s %8s %8s | %8s %8s"
          % ("rt", "arm", "rate", "nwin", "nep", "v", "|rate|", "LINE", "FLOOR", "line/fl",
             "CARRIER", "CTRL"))
    for (rt, arm, lo), rows in sorted(W.items(), key=lambda kv: (kv[0][1], kv[0][2] is None,
                                                                 kv[0][2] or -1, kv[0][0])):
        nep = len({r["ep"] for r in rows})
        ln = float(np.median([r["line"] for r in rows]))
        fl = float(np.median([r["floor"] for r in rows]))
        ca = float(np.median([r["car"] for r in rows]))
        ct = float(np.median([r["ctl"] for r in rows]))
        out["cells"]["%s|%s|%s" % (rt, arm, lo)] = dict(
            rt=rt, arm=arm, rate_lo=lo, n_win=len(rows), n_ep=nep, line=ln, floor=fl, car=ca,
            ctl=ct, v=float(np.median([r["v"] for r in rows])),
            rate=float(np.median([r["rate"] for r in rows])))
        print("  %-4s %-6s %-6s %5d %4d %7.1f %7.1f | %8.3g %8.3g %8.2f | %8.3g %8.3g"
              % (rt, arm, "ALL" if lo is None else "%.0f+" % lo, len(rows), nep,
                 np.median([r["v"] for r in rows]), np.median([r["rate"] for r in rows]),
                 ln, fl, ln / max(fl, 1e-9), ca, ct))

    hdr("⭐ O1 -- ELASTICITY SEPARATELY FOR LINE AND FLOOR, 6x/8x vs STOCK, matched on speed arm "
        "AND |rate_c| bin.   PRE-REGISTERED PREDICTION: E_line ~ 1, E_floor ~ 0")
    print("  %-4s %-6s %-6s | %-20s %-20s %-20s %-16s | %7s %7s %7s"
          % ("rt", "arm", "rate", "CARRIER x stock", "LINE x stock", "FLOOR x stock",
             "CTRL x stock", "E_car", "E_line", "E_floor"))
    agg = {"line": [], "floor": [], "rat": []}
    for rt in ROUTES:
        if rt == "97":
            continue
        for arm, _, _ in ARMS:
            for lo in [b[0] for b in RATE_BINS] + [None]:
                a, s = W.get((rt, arm, lo)), W.get(("97", arm, lo))
                if not a or not s:
                    continue
                cr, cci = boot_ratio(a, s, "car", rng)
                lr, lci = boot_ratio(a, s, "line", rng)
                fr, fci = boot_ratio(a, s, "floor", rng)
                xr, xci = boot_ratio(a, s, "ctl", rng)
                rr, _ = boot_ratio(a, s, "rat", rng)
                if not (np.isfinite(cr) and cr > 3 and xr > 0):
                    continue
                lc = np.log(cr / xr)
                if abs(lc) < 0.2:
                    continue
                E = lambda v: float(np.log(max(v, 1e-9) / xr) / lc)  # noqa: E731
                e_l, e_f, e_r = E(lr), E(fr), E(rr)
                agg["line"].append(e_l)
                agg["floor"].append(e_f)
                agg["rat"].append(e_r)
                out["elasticity"]["%s|%s|%s" % (rt, arm, lo)] = dict(
                    car=cr, car_ci=cci, line=lr, line_ci=lci, floor=fr, floor_ci=fci,
                    ctl=xr, ctl_ci=xci, rat=rr, E_line=e_l, E_floor=e_f, E_rat=e_r)
                print("  %-4s %-6s %-6s | %6.2f [%5.2f,%6.2f] %6.2f [%5.2f,%6.2f] "
                      "%6.2f [%5.2f,%6.2f] %5.2f [%4.2f,%5.2f] | %7s %+7.3f %+7.3f"
                      % (rt, arm, "ALL" if lo is None else "%.0f+" % lo,
                         cr, cci[0], cci[1], lr, lci[0], lci[1], fr, fci[0], fci[1],
                         xr, xci[0], xci[1], "1.000", e_l, e_f))
    if agg["line"]:
        out["summary"] = {k: dict(n=len(v), median=float(np.median(v)),
                                  lo=float(np.min(v)), hi=float(np.max(v)),
                                  frac_gt_07=float(np.mean(np.asarray(v) > 0.7)),
                                  frac_lt_03=float(np.mean(np.asarray(v) < 0.3)))
                          for k, v in agg.items()}
        print("\n  ⭐ SUMMARY over %d cells where the carrier moved >3x:" % len(agg["line"]))
        for k, nm in (("rat", "WHOLE BAND 6-12 (hf_lf_08's statistic)"), ("line", "LINE 7.4-8.6"),
                      ("floor", "FLOOR (broadband)")):
            v = np.asarray(agg[k])
            print("     E_%-6s %-38s median %+0.3f   [%+0.3f, %+0.3f]   frac>0.7 %.2f   "
                  "frac<0.3 %.2f" % (k, nm, np.median(v), v.min(), v.max(),
                                     np.mean(v > 0.7), np.mean(v < 0.3)))

    hdr("⭐ O2 -- DOSE-RESPONSE SLOPE  beta = d log(power) / d log(gain)  across the 1x/4x/6x/8x "
        "ladder (route 95 = V101 8x now included).  E_dose = beta_band / beta_carrier")
    print("  %-6s %-6s %5s | %-24s %-24s %-24s %-24s | %8s %8s"
          % ("arm", "rate", "nroutes", "beta CARRIER", "beta LINE", "beta FLOOR", "beta CTRL",
             "E_line", "E_floor"))
    for arm, _, _ in ARMS:
        for lo in [b[0] for b in RATE_BINS] + [None]:
            cell = {rt: W[(rt, arm, lo)] for rt in ROUTES if (rt, arm, lo) in W}
            if len(cell) < 3:
                continue
            bc = dose_slope(cell, "car", rng)
            bl = dose_slope(cell, "line", rng)
            bf = dose_slope(cell, "floor", rng)
            bx = dose_slope(cell, "ctl", rng)
            if not (bc and bl and bf and bx):
                continue
            key = "%s|%s" % (arm, "ALL" if lo is None else "%.0f+" % lo)
            el = (bl["beta"] - bx["beta"]) / (bc["beta"] - bx["beta"]) \
                if abs(bc["beta"] - bx["beta"]) > 0.15 else np.nan
            ef = (bf["beta"] - bx["beta"]) / (bc["beta"] - bx["beta"]) \
                if abs(bc["beta"] - bx["beta"]) > 0.15 else np.nan
            out["dose"][key] = dict(car=bc, line=bl, floor=bf, ctl=bx,
                                    E_line=float(el), E_floor=float(ef),
                                    routes=bc["routes"])
            f = lambda b: "%+6.3f [%+.3f,%+.3f]" % (b["beta"], b["ci"][0], b["ci"][1])  # noqa
            print("  %-6s %-6s %5d | %-24s %-24s %-24s %-24s | %+8.3f %+8.3f"
                  % (arm, "ALL" if lo is None else "%.0f+" % lo, bc["n_routes"],
                     f(bc), f(bl), f(bf), f(bx), el, ef))
            print("         routes in this cell: %s"
                  % "  ".join("%s(%gx)" % (r, GAIN[r]) for r in bc["routes"]))

    (HERE / "_scratch/out/_hf_lf_linefloor.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote", HERE / "_scratch/out/_hf_lf_linefloor.json")


if __name__ == "__main__":
    main()
