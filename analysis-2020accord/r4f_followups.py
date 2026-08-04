#!/usr/bin/env python3
"""Route `4f` follow-ups the first two passes forced.

A. THE POSITIVE CONTROL, DONE PROPERLY. `r4f_highway_bands.py` reports the 8-30 Hz peak as the
   estimator's positive control, but a free 8-30 Hz argmax can land on grind #1 or on wheel order 2
   instead of order 1 and then reads as a failed control when the instrument is fine. Redone as a
   TARGETED search in a +-2 Hz window around the order-1 prediction, with the free argmax printed
   beside it.

B. IS THERE A FIXED ~28 Hz LINE ON 4f AT ALL? V68's lane-change burst was 28.12/28.51 Hz at 25.94
   m/s, where wheel order 2 predicts 24.94 -- 3.57 Hz away, which is what made it a MODE rather than
   a tyre. 4f's loudest highway burst is 26.17/26.95 Hz at 27.98 m/s, where order 2 predicts 26.90
   -- 0.05 Hz away from the second line. So the two bursts may not be the same phenomenon at all.
   The discriminating test is the SPEED SWEEP: a mode stays put, an order rides n*v/CIRC. Run per
   narrow speed bin on both routes, with a Theil-Sen slope.
   🛑 The order-2 slope is +0.9613 Hz per m/s (CIRC = 2.0805 m); a fixed mode is 0.000.

C. THE CREEP MANEUVER CONTRAST. Section 4 of `r4f_highway_bands.py` returned ZERO control windows
   because it reused the HIGHWAY cut pair (|rate|pk >= 19 / <= 11 deg/s) at creep, where parking-lot
   steering puts essentially every window above 19. The |rate|pk distribution is printed here and an
   absolute creep pair is chosen from the POOLED (4f + prior-route) distribution -- pooled so the
   cut is not tuned to 4f's own spread.

Usage:  python r4f_followups.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                          # noqa: E402
import _r4f_lib as L                                             # noqa: E402
from _r31_common import load, periodogram, runs_of               # noqa: E402
from r4f_highway_bands import (BANDORDER, CIRC_HI, CIRC_LO, HWY, NFFT, HOP,  # noqa: E402
                               ROUTES, boot_ratio, hdr, segs_of, split_null, wrecs)

CIRC = (CIRC_LO + CIRC_HI) / 2
RES: dict = {}


def theil_sen(x, y):
    """Median pairwise slope + a bootstrap-free 95% interval from the pairwise slope quantiles."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3:
        return np.nan, np.nan, np.nan
    s = [(y[j] - y[i]) / (x[j] - x[i])
         for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i]]
    if not s:
        return np.nan, np.nan, np.nan
    s = np.array(s)
    return float(np.median(s)), float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def binspec(route, vlo, vhi, eng=True, only=None):
    """Averaged periodogram for one speed bin. `only` optionally restricts to a window predicate."""
    acc, n, fref, vs, rp = None, 0, None, [], []
    for s, d in segs_of(route):
        fs = L.fs_lattice(d)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        le = d["cc_lat"] > 0.5
        for a, b in runs_of(le if eng else ~le, d["t"], NFFT):
            for i in range(a, b - NFFT + 1, HOP):
                sl = slice(i, i + NFFT)
                v = float(np.mean(np.abs(d["cs_v"][sl])))
                if not (vlo <= v < vhi):
                    continue
                if only is not None and not only(d, sl):
                    continue
                P = periodogram(d["tq"][sl], fs, NFFT, True)
                if P is None:
                    continue
                if acc is None:
                    acc, fref = np.zeros_like(P), f
                if len(P) != len(acc):
                    continue
                acc += P; n += 1; vs.append(v)
                rp.append(float(np.mean(d["rpm"][sl])) if "rpm" in d else np.nan)
    if not n:
        return None
    return dict(f=fref, P=acc / n, n=n, v=float(np.mean(vs)),
                rpm=float(np.nanmean(rp)) if np.isfinite(rp).any() else np.nan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "_r4f_followups.json"))
    a = ap.parse_args()
    rng = np.random.default_rng(20260804)
    G.EPKEY = "blk"

    # ---------------------------------------------------------------- A -------------------------
    hdr("A. THE ESTIMATOR'S POSITIVE CONTROL -- TARGETED at wheel order 1, not a free argmax")
    print(f"   order 1 = v / CIRC, CIRC = {CIRC:.4f} m.  Searched in a +-2.0 Hz window around the")
    print("   prediction; the free 8-30 Hz argmax is printed beside it so both are visible.\n")
    print(f"   {'route':8s} {'v bin':8s} {'n':>5s} {'v':>6s} {'ord1 pred':>10s} "
          f"{'targeted f0':>12s} {'prom':>7s} {'delta':>7s} {'free 8-30 f0':>13s} {'prom':>7s}")
    RES["posctl"] = {}
    for route in ROUTES:
        for vlo, vhi in ((20, 23), (23, 26), (26, 32)):
            o = binspec(route, vlo, vhi)
            if not o:
                continue
            R = G.prom_spectrum(o["f"], o["P"])
            pred = o["v"] / CIRC
            ft, pt = G.locate(o["f"], o["P"], pred - 2.0, pred + 2.0, R=R)
            ff, pf = G.locate(o["f"], o["P"], 8.0, 30.0, R=R)
            RES["posctl"][f"{route}_{vlo}-{vhi}"] = dict(n=o["n"], v=o["v"], pred=pred,
                                                         f_targeted=ft, prom_targeted=pt,
                                                         f_free=ff, prom_free=pf)
            print(f"   {route:8s} {f'{vlo}-{vhi}':8s} {o['n']:5d} {o['v']:6.2f} {pred:10.2f} "
                  f"{ft:12.2f} {pt:7.2f} {ft - pred:+7.2f} {ff:13.2f} {pf:7.2f}"
                  + ("   *** order 1 RECOVERED" if pt > 4 and abs(ft - pred) < 0.6 else ""))
        print()

    # ---------------------------------------------------------------- B -------------------------
    hdr("B. DOES 4f CARRY A FIXED ~28 Hz LINE? -- track the 24-32 Hz peak across a speed sweep")
    print("   a MODE stays put (slope 0.000 Hz per m/s); wheel order 2 rides "
          f"+{2 / CIRC:.4f} Hz per m/s.")
    print("   ⚠ Engine order 1 = rpm/60; the Accord's CVT holds rpm near-constant at cruise, so an")
    print("     engine order also LOOKS fixed against road speed -- rpm is printed for that reason.\n")
    RES["line28"] = {}
    for route in ROUTES:
        print(f"   --- {route} ENGAGED ---")
        print(f"   {'v bin':9s} {'n':>5s} {'v':>6s} {'rpm':>6s} {'24-32 f0':>9s} {'prom':>7s} "
              f"{'ord2':>7s} {'d(ord2)':>8s} {'eng1':>7s} {'d(eng1)':>8s}")
        pts = []
        for vlo, vhi in ((19, 21), (21, 23), (23, 25), (25, 27), (27, 29), (29, 32)):
            o = binspec(route, vlo, vhi)
            if not o or o["n"] < 4:
                if o:
                    print(f"   {f'{vlo}-{vhi}':9s} {o['n']:5d}   -- too few windows")
                continue
            R = G.prom_spectrum(o["f"], o["P"])
            f0, pr = G.locate(o["f"], o["P"], 24.0, 32.0, R=R)
            o2 = 2 * o["v"] / CIRC
            e1 = o["rpm"] / 60.0 if np.isfinite(o["rpm"]) else np.nan
            pts.append((o["v"], f0, pr, o["n"]))
            print(f"   {f'{vlo}-{vhi}':9s} {o['n']:5d} {o['v']:6.2f} {o['rpm']:6.0f} "
                  f"{f0:9.2f} {pr:7.2f} {o2:7.2f} {f0 - o2:+8.2f} {e1:7.2f} {f0 - e1:+8.2f}")
        if len(pts) >= 3:
            sl, lo, hi = theil_sen([p[0] for p in pts], [p[1] for p in pts])
            RES["line28"][route] = dict(pts=pts, slope=sl, lo=lo, hi=hi)
            print(f"   Theil-Sen slope of the 24-32 Hz peak vs speed: "
                  f"{sl:+.4f} [{lo:+.4f}, {hi:+.4f}] Hz per m/s")
            print(f"      wheel order 2 requires {2 / CIRC:+.4f}; a fixed mode requires +0.0000")
        else:
            print("   too few speed bins for a slope")
        print()

    # ---------------------------------------------------------------- C -------------------------
    hdr("C. THE CREEP MANEUVER CONTRAST -- an ABSOLUTE cut pair chosen for creep, not for highway")
    W = {r: wrecs(r) for r in ROUTES}
    crF = [w for w in W["4f/V69"] if w["eng"] and 0.3 < w["v"] < 4.0]
    crD = [w for w in W["4f/V69"] if not w["eng"] and 0.3 < w["v"] < 4.0]
    print("   |rate|pk distribution at creep (deg/s), the reason the highway pair failed:")
    for nm, arm in (("4f engaged creep", crF), ("4f disengaged creep", crD)):
        if arm:
            q = np.percentile(G.col(arm, "ratepk"), [10, 25, 50, 75, 90])
            print(f"     {nm:22s} n={len(arm):4d}  p10/p25/p50/p75/p90 = {q.round(1)}")
    pooled = G.col(crF + crD, "ratepk")
    HI = float(np.percentile(pooled, 75))
    LO = float(np.percentile(pooled, 25))
    print(f"\n   ABSOLUTE creep pair from the POOLED (engaged + disengaged) distribution:")
    print(f"     maneuver |rate|pk >= {HI:.1f} deg/s, control <= {LO:.1f} deg/s")
    print("   🛑 Pooled deliberately: a per-arm quantile cut is the mistake HANDOFF-2026-08-03 §6c")
    print("     records, and a cut tuned to one arm's spread is a confound with the arm.\n")
    RES["creep_maneuver"] = dict(hi=HI, lo=LO)
    for nm, arm in (("ENGAGED", crF), ("DISENGAGED", crD)):
        mv = [w for w in arm if w["ratepk"] >= HI]
        ct = [w for w in arm if w["ratepk"] <= LO]
        print(f"   --- 4f {nm} creep: {len(mv)} maneuver ({len(G.episodes(mv))} blk) / "
              f"{len(ct)} control ({len(G.episodes(ct))} blk) ---")
        if len(mv) < 5 or len(ct) < 5:
            print("       too few windows for an episode bootstrap")
            continue
        RES["creep_maneuver"][nm] = {}
        print(f"       {'band':8s} {'mv med':>9s} {'ct med':>9s} {'ratio':>8s} {'[95% CI]':>20s} "
              f"{'null(ct)':>16s}")
        for band in BANDORDER:
            k = "e_" + band
            pt, ci = boot_ratio(mv, ct, k, rng)
            nl = split_null(ct, k, rng)
            RES["creep_maneuver"][nm][band] = dict(ratio=pt, ci=ci, null=nl,
                                                   n_mv=len(mv), n_ct=len(ct))
            print(f"       {band:8s} {np.median(G.col(mv, k)):9.1f} "
                  f"{np.median(G.col(ct, k)):9.1f} {pt:8.3f} [{ci[0]:8.3f}, {ci[1]:8.3f}] "
                  f"[{nl[0]:6.2f},{nl[1]:6.2f}]"
                  + ("  *** clears" if np.isfinite(ci[0]) and np.isfinite(nl[1])
                     and ci[0] > nl[1] else ""))
        print()

    Path(a.json).write_text(json.dumps(RES, indent=1, default=str))
    print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
