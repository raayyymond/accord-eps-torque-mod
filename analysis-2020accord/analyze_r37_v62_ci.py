#!/usr/bin/env python3
"""V62 route `37` -- the claims under proper statistics: episode-level n, CIs, and order tracking.

This answers the four revised deliverables. Nothing here re-derives flight health (done elsewhere).

  C1/C2  Is the grinding reduction real?  Episode-clustered bootstrap CIs on the band-power ratio
         against BOTH controls, plus a distribution-free effect size. Windows inside one engagement
         episode are strongly correlated, so a bootstrap over WINDOWS would understate the interval
         by roughly sqrt(windows/episodes) -- 2-4x here. Every resample is over EPISODES.
  C3     ORDER TRACKING. Wheel order 1 is f = 0.489*v (measured, wheel circumference 2.073-2.088 m).
         Order k lands inside [lo,hi] Hz for v in [lo/(0.489k), hi/(0.489k)]. Stated, then TESTED
         against the data rather than assumed, because only order 1 is on the record as real.
  C4     The ratchet, speed-restricted below the contamination threshold and binned by driver
         effort, with ABSOLUTE POWER and the local floor printed beside every prominence -- a pure
         tone in a quiet window inflates prominence without carrying more energy, and that is
         exactly the failure mode that makes a 9172x number untrustworthy on its own.
  C5     The omega_n^2-linear-in-Kd prediction, with bootstrap error bars on both modes.
  C6/C7  LKAS gating corroboration, and the manual/reverse arm WITH seg 0.

🛑 SEG 0 IS INCLUDED throughout (real driving; only its `clocks` RTC is stale).
"""
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

from _r31_common import NFFT, fs_of, load, peak_prom, periodogram, runs_of, sustained  # noqa: E402
from analyze_r37_v62_creep import (BUILDS, GRIND, ORDER, RATCH, bandpower,  # noqa: E402
                                   col, hdr, wrecs)
from analyze_r37_v62_ratchet import LOT_37, ROAD_37  # noqa: E402
from analyze_r37_v62_harmonic import notched_peak  # noqa: E402

RNG = np.random.default_rng(20260731)
NBOOT = 4000
ORDER1 = 0.489          # Hz per m/s, wheel order 1 -- measured, not assumed
G1822 = (18.0, 22.0)    # the orchestrator's grinding band
G1826 = (18.0, 26.0)    # the kit's strict grinding band
R612 = (6.0, 12.0)      # the orchestrator's ratchet band
EFFORT_BINS = [(0, 200), (200, 500), (500, 1000), (1000, 2000), (2000, 10 ** 9)]


# ------------------------------------------------------------------ bootstrap ------------------
def episodes(recs):
    """Group window records into their parent engagement episodes."""
    out = {}
    for r in recs:
        out.setdefault((r["seg"], r["run"]), []).append(r)
    return list(out.values())


def boot_median(recs, value_fn, nboot=NBOOT):
    """(point, lo, hi) for the median of value_fn, resampling EPISODES with replacement."""
    eps = episodes(recs)
    if not eps:
        return np.nan, np.nan, np.nan
    per = [np.array([value_fn(r) for r in e], float) for e in eps]
    allv = np.concatenate(per)
    allv = allv[np.isfinite(allv)]
    if not len(allv):
        return np.nan, np.nan, np.nan
    point = float(np.median(allv))
    draws = np.empty(nboot)
    n = len(per)
    for b in range(nboot):
        idx = RNG.integers(0, n, n)
        v = np.concatenate([per[i] for i in idx])
        v = v[np.isfinite(v)]
        draws[b] = np.median(v) if len(v) else np.nan
    return point, float(np.nanpercentile(draws, 2.5)), float(np.nanpercentile(draws, 97.5))


def boot_ratio(a, b, value_fn, nboot=NBOOT):
    """(ratio of medians, lo, hi) resampling episodes independently in both arms."""
    ea, eb = episodes(a), episodes(b)
    if not ea or not eb:
        return np.nan, np.nan, np.nan
    pa = [np.array([value_fn(r) for r in e], float) for e in ea]
    pb = [np.array([value_fn(r) for r in e], float) for e in eb]
    ma = np.median(np.concatenate(pa))
    mb = np.median(np.concatenate(pb))
    draws = np.empty(nboot)
    for k in range(nboot):
        va = np.concatenate([pa[i] for i in RNG.integers(0, len(pa), len(pa))])
        vb = np.concatenate([pb[i] for i in RNG.integers(0, len(pb), len(pb))])
        draws[k] = np.median(va) / max(np.median(vb), 1e-300)
    return float(ma / mb), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def boot_cles(a, b, value_fn, nboot=NBOOT):
    """P(random V62 window < random control window), episode-clustered. 0.5 = no effect."""
    ea, eb = episodes(a), episodes(b)
    if not ea or not eb:
        return np.nan, np.nan, np.nan
    pa = [np.array([value_fn(r) for r in e], float) for e in ea]
    pb = [np.array([value_fn(r) for r in e], float) for e in eb]

    def cles(x, y):
        return float(np.mean(x[:, None] < y[None, :]) + 0.5 * np.mean(x[:, None] == y[None, :]))

    point = cles(np.concatenate(pa), np.concatenate(pb))
    draws = np.empty(nboot)
    for k in range(nboot):
        va = np.concatenate([pa[i] for i in RNG.integers(0, len(pa), len(pa))])
        vb = np.concatenate([pb[i] for i in RNG.integers(0, len(pb), len(pb))])
        draws[k] = cles(va, vb)
    return point, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def bp(lo, hi):
    return lambda r: float(r["P"][(r["f"] >= lo) & (r["f"] <= hi)].sum())


def prom_detail(r, lo, hi):
    """(f0, prominence, peak power, local floor) -- so a high ratio on a tiny peak is visible."""
    f, P = r["f"], r["P"]
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan, np.nan, np.nan
    j = int(np.argmax(np.where(m, P, -np.inf)))
    near = (np.abs(f - f[j]) <= 6.0) & (np.abs(f - f[j]) > 1.5) & (f > 0.3)
    floor = float(np.median(P[near])) if near.sum() >= 5 else np.nan
    f0, pr = peak_prom(f, P, lo, hi)
    return f0, pr, float(P[j]), floor


# ------------------------------------------------------------------ arms -----------------------
def arm(build, segs=None, vlo=0.3, vhi=5.35, eff=None, engaged=True, nfft=NFFT, vsel=None,
        esel=None):
    """Engaged (or manual) windows. `eff` = (lo,hi) on sustained |lowpass(tq,3Hz)|.

    🛑 SPEED BINNING IS CUT-THEN-SELECT. Runs are cut over the WHOLE arm [vlo,vhi] and windows are
    then kept on their own mean |v| via `vsel`. Narrowing the mask BEFORE cutting destroys the
    2.56 s contiguity requirement and returns fake nulls -- it cost route 2c its entire creep arm
    once already (analyze_r31_matched.py M1).

    TWO effort gates, and the difference matters:
      `eff`  -- per-sample, applied BEFORE cutting. The kit's hands-off construction. Correct for a
                sustained state like hands-off; but a NARROW bin (200-500) fragments every run
                below 2.56 s and returns n=0, which is a window-length null, not a physical one.
      `esel` -- on the window's own MEAN effort, applied after cutting. Correct for effort BINNING.
                Effort is already a 3 Hz low-pass, so its window mean is representative.
    """
    B = BUILDS[build]
    out = []
    for s in (B["segs"] if segs is None else segs):
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        e = np.abs(sustained(d["tq"], fs))
        v = np.abs(d["cs_v"])
        lat = d["cc_lat"] > 0.5
        m = (lat if engaged else ~lat) & (v >= vlo) & (v <= vhi)
        if eff is not None:
            m &= (e >= eff[0]) & (e < eff[1])
        if not m.any():
            continue
        f = np.fft.rfftfreq(nfft, 1 / fs)
        for a, b in runs_of(m, d["t"], nfft):
            x = d["tq"][a:b]
            for i in range(0, len(x) - nfft + 1, nfft):
                P = periodogram(x[i:i + nfft], fs, nfft, True)
                if P is None:
                    continue
                sl = slice(a + i, a + i + nfft)
                f0g, prg = peak_prom(f, P, *GRIND)
                f0r, prr = peak_prom(f, P, *RATCH)
                vw = float(np.mean(v[sl]))
                if vsel is not None and not (vsel[0] <= vw < vsel[1]):
                    continue
                ew = float(np.mean(e[sl]))
                if esel is not None and not (esel[0] <= ew < esel[1]):
                    continue
                out.append(dict(f=f, P=P, f0=f0g, prom=prg, fr=f0r, promr=prr,
                                v=vw, eff=ew,
                                ang=float(np.mean(np.abs(d["ang"][sl]))),
                                seg=int(s), run=(int(a), int(b)), t0=float(d["t"][a + i])))
    return out


CACHE = {}


def A(build, **kw):
    key = (build, tuple(sorted((k, tuple(v) if isinstance(v, (list, tuple)) else v)
                               for k, v in kw.items())))
    if key not in CACHE:
        CACHE[key] = arm(build, **kw)
    return CACHE[key]


# ------------------------------------------------------------------ C1/C2 ----------------------
def c1_grinding():
    hdr("C1.  THE GRINDING REDUCTION -- episode-clustered bootstrap CIs, both controls")
    print("   Engaged creep. Three effort selections so the result cannot rest on one gate:")
    print("   the kit's hands-off (<=200), the orchestrator's hands-light (<300), and UNGATED.")
    print("   n is reported as EPISODES (independent engagement runs) and windows.\n")
    for elab, eff in (("hands-off  eff<=200", (0, 200)), ("hands-light eff<300", (0, 300)),
                      ("UNGATED", None)):
        print(f"   ---- {elab}, |v| 1-4 m/s ----")
        arms = {b: A(b, vsel=(1.0, 4.0), eff=eff) for b in ORDER}
        for band, blab in ((G1822, "18-22 Hz"), (G1826, "18-26 Hz"), (RATCH, "6-9 Hz")):
            print(f"     {blab}")
            for b in ORDER:
                r = arms[b]
                if not r:
                    print(f"       {b:9s}  ep=0")
                    continue
                p, lo, hi = boot_median(r, bp(*band))
                print(f"       {b:9s} ep={len(episodes(r)):3d} win={len(r):3d}  "
                      f"median power {p:9.3g}  [95% CI {lo:9.3g}, {hi:9.3g}]")
            for ctl in ("V59 r2c", "V64 r35"):
                if not arms["V62 r37"] or not arms[ctl]:
                    continue
                rr, rlo, rhi = boot_ratio(arms["V62 r37"], arms[ctl], bp(*band))
                cl, clo, chi = boot_cles(arms["V62 r37"], arms[ctl], bp(*band))
                print(f"       V62/{ctl.split()[0]}  ratio {rr:7.4f}x  [95% CI {rlo:.4f}, {rhi:.4f}]"
                      f"   =>  {1 / rr:6.1f}x reduction   |  P(V62 win < ctl win) "
                      f"{cl:.3f} [{clo:.3f}, {chi:.3f}]")
            print()
        print()


# ------------------------------------------------------------------ C3 -------------------------
def c3_orders():
    hdr("C3.  ORDER TRACKING -- where wheel order k = 0.489*k*v enters each band")
    print("   Wheel order 1 measured at f = 0.489*v (circumference 2.073-2.088 m, V56/V57).")
    print("   Order k occupies [lo,hi] Hz for v in [lo/(0.489k), hi/(0.489k)]:\n")
    print(f"   {'band':10s} " + "".join(f"{'order ' + str(k):>22s}" for k in (1, 2, 3, 4)))
    for lo, hi, lab in ((6, 9, "6-9 Hz"), (6, 12, "6-12 Hz"), (18, 22, "18-22 Hz"),
                        (18, 26, "18-26 Hz"), (12, 30, "12-30 Hz")):
        cells = []
        for k in (1, 2, 3, 4):
            cells.append(f"v {lo / (ORDER1 * k):5.2f}-{hi / (ORDER1 * k):5.2f} m/s")
        print(f"   {lab:10s} " + "".join(f"{c:>22s}" for c in cells))
    print(f"\n   => the 6-9 Hz band is order-1 contaminated above {6 / ORDER1:.2f} m/s "
          f"({6 / ORDER1 * 2.237:.1f} mph), the 6-12 Hz band above the same speed.")
    print(f"   => order 2 reaches 6 Hz at {6 / (2 * ORDER1):.2f} m/s and order 3 at "
          f"{6 / (3 * ORDER1):.2f} m/s, so a STRICTLY order-free 6-9 Hz claim needs "
          f"|v| < {6 / (3 * ORDER1):.2f} m/s.")

    print("\n   -- but only order 1 is ON THE RECORD as real. TESTING which orders actually exist,")
    print("      route 37, engaged, pooled run-averaged spectrum per speed bin. A peak is tagged")
    print("      'kX' when it lands within 0.4 Hz of 0.489*k*v_med. --\n")
    for vlo, vhi in [(0.3, 2), (2, 4), (4, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 22),
                     (22, 26), (26, 29)]:
        r = A("V62 r37", vlo=0.3, vhi=30.0, vsel=(vlo, vhi))
        if len(r) < 3:
            print(f"   |v| {vlo:4.1f}-{vhi:<4.1f}  {len(r)} windows -- too few")
            continue
        f = r[0]["f"]
        P = np.mean([x["P"] for x in r], axis=0)
        vm = float(np.median(col(r, "v")))
        pk = []
        for j in range(1, len(P) - 1):
            if not (3.0 <= f[j] <= 46.0) or not (P[j] > P[j - 1] and P[j] >= P[j + 1]):
                continue
            near = (np.abs(f - f[j]) <= 6.0) & (np.abs(f - f[j]) > 1.5) & (f > 0.3)
            if near.sum() < 5:
                continue
            fl = float(np.median(P[near]))
            pk.append((f[j], P[j] / fl if fl > 0 else np.inf))
        pk.sort(key=lambda z: -z[1])
        tags = []
        for f0, pr in pk[:5]:
            k = ""
            for kk in (1, 2, 3, 4):
                if abs(f0 - ORDER1 * kk * vm) <= 0.4:
                    k = f" k{kk}"
            tags.append(f"{f0:5.2f}Hz {pr:6.1f}x{k}")
        print(f"   |v| {vlo:4.1f}-{vhi:<4.1f} n={len(r):3d} ep={len(episodes(r)):2d} vmed={vm:5.2f}"
              f"  order1={ORDER1 * vm:5.2f}Hz  peaks: " + "  ".join(tags))
    print("\n   (an order line is the ONLY peak that must move as 0.489*k*v; a mode does not)")

    print("\n   -- does the 6-9 Hz line itself track an order? its f0 vs speed, engaged --")
    print(f"   {'|v| bin':>10s} {'ep':>3s} {'win':>4s} {'v med':>6s} {'f0 6-9':>7s} {'sd':>5s} "
          f"{'0.489v':>7s} {'0.978v':>7s} {'1.467v':>7s}")
    for vlo, vhi in [(0.3, 1), (1, 2), (2, 3), (3, 4), (4, 5.35)]:
        r = A("V62 r37", vsel=(vlo, vhi))
        if len(r) < 2:
            continue
        pr = col(r, "promr")
        fr = col(r, "fr")[np.isfinite(pr) & (pr >= 10)]
        vm = float(np.median(col(r, "v")))
        if not len(fr):
            continue
        print(f"   {vlo:4.1f}-{vhi:<4.1f} {len(episodes(r)):3d} {len(r):4d} {vm:6.2f} "
              f"{np.median(fr):7.2f} {fr.std(ddof=1) if len(fr) > 1 else 0:5.2f} "
              f"{ORDER1 * vm:7.2f} {2 * ORDER1 * vm:7.2f} {3 * ORDER1 * vm:7.2f}")
    print("   (f0 rises ~7.2 -> 8.2 Hz over a 3x speed change; every order line would rise 3x)")


# ------------------------------------------------------------------ C4 -------------------------
def c4_ratchet():
    hdr("C4.  THE RATCHET BY DRIVER EFFORT -- prominence WITH its power and its floor")
    print("   🛑 Restricted to |v| <= 4.09 m/s, below where wheel order 3 could reach 6 Hz. The")
    print("   orchestrator's 1-14 m/s arm spans 12.3-18.4 m/s, where order 1 IS inside 6-9 Hz.")
    print("   'floor' is the local +/-6 Hz median that prominence divides by: a big prominence on")
    print("   a small peak power means a quiet window, not more energy.\n")
    for band, blab in ((RATCH, "6-9 Hz"), (R612, "6-12 Hz"), (G1822, "18-22 Hz")):
        print(f"   ==== {blab} ====")
        print(f"   {'effort':12s} {'build':9s} {'ep':>3s} {'win':>4s} {'f0':>6s} {'prom med':>9s} "
              f"{'peakP med':>10s} {'floor med':>10s} {'bandP med':>10s} {'V62/V59':>9s}")
        for elo, ehi in EFFORT_BINS:
            arms = {b: A(b, vsel=(0.3, 4.09), esel=(elo, ehi)) for b in ORDER}
            # 🛑 the lot (segs 13-14) is a manoeuvre no control route has. Split it out or the
            # ratchet comparison is comparing route content.
            arms["V62 road"] = A("V62 r37", segs=tuple(ROAD_37), vsel=(0.3, 4.09),
                                 esel=(elo, ehi))
            arms["V62 lot"] = A("V62 r37", segs=tuple(LOT_37), vsel=(0.3, 4.09), esel=(elo, ehi))
            for b in list(ORDER) + ["V62 road", "V62 lot"]:
                r = arms[b]
                if not r:
                    continue
                det = np.array([prom_detail(x, *band) for x in r], float)
                bpw = np.array([bp(*band)(x) for x in r], float)
                rat = ""
                if b.startswith("V62") and arms["V59 r2c"]:
                    b59 = np.array([bp(*band)(x) for x in arms["V59 r2c"]], float)
                    rat = f"{np.median(bpw) / np.median(b59):9.3f}"
                elab = f"{elo}-{'inf' if ehi > 1e8 else ehi}"
                print(f"   {elab:12s} {b:9s} {len(episodes(r)):3d} {len(r):4d} "
                      f"{np.nanmedian(det[:, 0]):6.2f} {np.nanmedian(det[:, 1]):9.1f} "
                      f"{np.nanmedian(det[:, 2]):10.3g} {np.nanmedian(det[:, 3]):10.3g} "
                      f"{np.median(bpw):10.3g} {rat:>9s}")
            print()
        print()

    print("   -- THE SAME WITHOUT the speed restriction (|v| 1-14 m/s), to show what the tyre does --")
    print(f"   {'effort':12s} {'build':9s} {'ep':>3s} {'win':>4s} {'6-9 bandP':>10s} "
          f"{'V62/V59':>9s} {'%win v>12.3':>12s}")
    for elo, ehi in EFFORT_BINS:
        arms = {b: A(b, vlo=0.3, vhi=14.0, vsel=(1.0, 14.0), esel=(elo, ehi)) for b in ORDER}
        for b in ("V59 r2c", "V64 r35", "V62 r37"):
            r = arms[b]
            if not r:
                continue
            bpw = np.array([bp(*RATCH)(x) for x in r], float)
            rat = ""
            if b == "V62 r37" and arms["V59 r2c"]:
                b59 = np.array([bp(*RATCH)(x) for x in arms["V59 r2c"]], float)
                rat = f"{np.median(bpw) / np.median(b59):9.3f}"
            frac = 100 * np.mean(col(r, "v") > 6 / ORDER1)
            elab = f"{elo}-{'inf' if ehi > 1e8 else ehi}"
            print(f"   {elab:12s} {b:9s} {len(episodes(r)):3d} {len(r):4d} {np.median(bpw):10.3g} "
                  f"{rat:>9s} {frac:11.1f}%")
        print()


# ------------------------------------------------------------------ C5 -------------------------
def c5_shift():
    hdr("C5.  THE omega_n^2-LINEAR-IN-Kd PREDICTION, with bootstrap error bars on both modes")
    print("   rate_lane_damping_model.py: omega_n^2 = A + B*Kd. V61 is Kd=0, V59/V64 are Kd=1,")
    print("   V62 is Kd=2, so  f(V62) = sqrt(2*f(V59)^2 - f(V61)^2).  V61's engaged arm exists ONLY")
    print("   at 1-2 m/s, so that is the only bin where the three-point fit can be made at all.\n")
    for vlo, vhi in ((1.0, 2.0), (2.0, 3.0), (3.0, 4.0)):
        print(f"   |v| {vlo}-{vhi} m/s")
        res = {}
        for b in ORDER:
            r = A(b, vsel=(vlo, vhi))
            if not r:
                continue
            keepR = [x for x in r if np.isfinite(x["promr"]) and x["promr"] >= 10]
            keepG = [x for x in r if np.isfinite(x["prom"]) and x["prom"] >= 10]
            nk = [(x, notched_peak(x, harmonics=(2, 3, 4))) for x in r]
            keepN = [x for x, (f0, pr) in nk if np.isfinite(pr) and pr >= 10]
            fN = {id(x): f0 for x, (f0, pr) in nk}
            res[b] = dict(
                R=boot_median(keepR, lambda x: x["fr"]) if keepR else (np.nan,) * 3,
                nR=len(keepR), epR=len(episodes(keepR)),
                G=boot_median(keepG, lambda x: x["f0"]) if keepG else (np.nan,) * 3,
                nG=len(keepG), epG=len(episodes(keepG)),
                N=boot_median(keepN, lambda x: fN[id(x)]) if keepN else (np.nan,) * 3,
                nN=len(keepN), epN=len(episodes(keepN)))
            x = res[b]
            print(f"     {b:9s} ratchet {x['R'][0]:6.2f} [{x['R'][1]:5.2f},{x['R'][2]:5.2f}] "
                  f"n={x['nR']:3d}/{x['epR']:2d}ep | grind {x['G'][0]:6.2f} "
                  f"[{x['G'][1]:5.2f},{x['G'][2]:5.2f}] n={x['nG']:3d}/{x['epG']:2d}ep | "
                  f"grind NOTCHED {x['N'][0]:6.2f} [{x['N'][1]:5.2f},{x['N'][2]:5.2f}] "
                  f"n={x['nN']:3d}/{x['epN']:2d}ep")
        if "V61 r31" in res and "V59 r2c" in res and "V62 r37" in res:
            for key, lab in (("R", "RATCHET"), ("G", "GRINDING (raw)"), ("N", "GRINDING (notched)")):
                f59, f61, f62 = (res["V59 r2c"][key][0], res["V61 r31"][key][0],
                                 res["V62 r37"][key][0])
                if not (np.isfinite(f59) and np.isfinite(f61)):
                    continue
                pred2 = 2 * f59 ** 2 - f61 ** 2
                pred = np.sqrt(pred2) if pred2 > 0 else np.nan
                ci = res["V62 r37"][key][1:]
                verdict = ("cannot test -- no measurable V62 line" if not np.isfinite(f62)
                           else "CONSISTENT" if ci[0] <= pred <= ci[1] else "FALSIFIED")
                print(f"       {lab:20s} V61 {f61:5.2f}  V59 {f59:5.2f}  => predicted V62 "
                      f"{pred:5.2f} Hz  |  measured {f62:5.2f} [{ci[0]:5.2f},{ci[1]:5.2f}]"
                      f"   {verdict}")
        print()
    print("   Also the DIRECTION-only test: V62 must be ABOVE V59 on every mode if Kd adds")
    print("   stiffness. Ratchet, speed-matched, V62/V59 with V64/V59 as the route-to-route null:")
    print(f"   {'bin':>10s} {'V59':>16s} {'V64':>16s} {'V62':>16s} {'V64/V59':>8s} {'V62/V59':>8s}")
    for vlo, vhi in ((1.0, 2.0), (2.0, 3.0), (3.0, 4.0)):
        vals = {}
        for b in ("V59 r2c", "V64 r35", "V62 r37"):
            r = [x for x in A(b, vsel=(vlo, vhi))
                 if np.isfinite(x["promr"]) and x["promr"] >= 10]
            vals[b] = boot_median(r, lambda x: x["fr"]) if r else (np.nan,) * 3
        c = lambda k: (f"{vals[k][0]:5.2f}[{vals[k][1]:4.1f},{vals[k][2]:4.1f}]"  # noqa: E731
                       if np.isfinite(vals[k][0]) else f"{'--':>16s}")
        r64 = vals["V64 r35"][0] / vals["V59 r2c"][0]
        r62 = vals["V62 r37"][0] / vals["V59 r2c"][0]
        print(f"   {vlo:4.1f}-{vhi:<4.1f} {c('V59 r2c'):>16s} {c('V64 r35'):>16s} "
              f"{c('V62 r37'):>16s} {r64:8.3f} {r62:8.3f}")


# ------------------------------------------------------------------ C6/C7 ----------------------
def c6_gating_and_manual():
    hdr("C6.  IS THE RATCHET STILL LKAS-GATED?  route 37 lot (segs 13-14) and the whole route")
    print(f"   {'arm':34s} {'ep':>3s} {'win':>4s} {'f0':>6s} {'prom med':>9s} {'bandP med':>10s} "
          f"{'pres>=10x':>10s}")
    for lab, segs, vhi in (("LOT segs 13-14", LOT_37, 4.09), ("ROAD segs 0-12", ROAD_37, 4.09),
                           ("WHOLE ROUTE |v|<=4.09", None, 4.09)):
        for eng, elab in ((True, "ENGAGED"), (False, "MANUAL")):
            r = A("V62 r37", segs=segs, vsel=(0.3, vhi), engaged=eng)
            if not r:
                print(f"   {lab + ' ' + elab:34s}   0")
                continue
            pr = col(r, "promr")
            ok = np.isfinite(pr)
            print(f"   {lab + '  ' + elab:34s} {len(episodes(r)):3d} {len(r):4d} "
                  f"{np.nanmedian(col(r, 'fr')):6.2f} {np.nanmedian(pr):9.1f} "
                  f"{np.median([bp(*RATCH)(x) for x in r]):10.3g} "
                  f"{100 * np.mean(pr[ok] >= 10):9.1f}%")
        e = A("V62 r37", segs=segs, vsel=(0.3, vhi), engaged=True)
        m = A("V62 r37", segs=segs, vsel=(0.3, vhi), engaged=False)
        if e and m:
            rr, lo, hi = boot_ratio(e, m, bp(*RATCH))
            print(f"   {'   => engaged/manual band power':34s} {rr:10.1f}x  "
                  f"[95% CI {lo:.1f}, {hi:.1f}]\n")

    hdr("C7.  THE MANUAL / REVERSE ARM, WITH SEG 0 INCLUDED")
    print("   Seg 0 is 6,168 frames of near-stationary large-angle MANUAL creep -- the population")
    print("   this arm was thin on. Reported for the grinding band, which is what V61 broke.\n")
    print(f"   {'arm':30s} {'build':9s} {'ep':>3s} {'win':>4s} {'f0':>6s} {'prom med':>9s} "
          f"{'p90':>9s} {'P(18-26)':>10s} {'pres>=10x':>10s}")

    def line(lab, b, r):
        if not r:
            print(f"   {lab:30s} {b:9s}   0 windows")
            return
        pg = col(r, "prom")
        ok = np.isfinite(pg)
        print(f"   {lab:30s} {b:9s} {len(episodes(r)):3d} {len(r):4d} "
              f"{np.nanmedian(col(r, 'f0')):6.2f} {np.nanmedian(pg):9.1f} "
              f"{np.nanpercentile(pg, 90):9.1f} "
              f"{np.median([bp(*G1826)(x) for x in r]):10.3g} "
              f"{100 * np.mean(pg[ok] >= 10):9.1f}%")

    for b in ORDER:
        line("MANUAL |v| 0.3-5.35", b, A(b, vlo=0.3, vhi=5.35, engaged=False))
    print()
    for b in ORDER:
        line("MANUAL |v| 0.0-5.35 (all)", b, A(b, vlo=0.0, vhi=5.35, engaged=False))
    print()
    for b in ORDER:
        line("MANUAL near-stat |v|<=0.6", b, A(b, vlo=0.0, vhi=0.6, engaged=False, nfft=128))
    print()
    for b in ORDER:
        line("MANUAL hi-effort >=1000", b,
             A(b, vlo=0.0, vhi=5.35, engaged=False, eff=(1000, 10 ** 9), nfft=128))
    print()
    print("   -- route 37 only: seg 0's own contribution to the manual arm --")
    for lab, segs in (("seg 0 alone", [0]), ("segs 13-14 alone", LOT_37),
                      ("segs 1-12 alone", list(range(1, 13)))):
        line(lab, "V62 r37", A("V62 r37", segs=segs, vlo=0.0, vhi=5.35, engaged=False, nfft=128))


def c3b_speed_sweep():
    hdr("C3b. IS THE FIX CREEP-SPECIFIC?  the 18-26 Hz line across the WHOLE speed range")
    print("   The order sweep above still shows a 21.5-21.6 Hz peak on V62 at 6-15 m/s, so the line")
    print("   is not annihilated everywhere -- the question is whether the REDUCTION is creep-only.")
    print("   ⚠ above ~12 m/s the 18-26 Hz band is nearly empty on BOTH builds (~5e6 vs ~5e8 at")
    print("   creep), so a ratio near 1 up there is two small numbers, not a failure to fix.")
    print("   Runs cut over the whole 0.3-30 m/s engaged arm, windows binned on their own |v|.\n")
    print(f"   {'|v| bin':>11s} {'build':9s} {'ep':>3s} {'win':>4s} {'f0(12-30)':>10s} {'sd':>5s} "
          f"{'prom med':>9s} {'P(18-26) med':>13s} {'pres>=10x':>10s}")
    for vlo, vhi in [(0.3, 2), (2, 4), (4, 6), (6, 9), (9, 12), (12, 16), (16, 20), (20, 25),
                     (25, 29)]:
        for b in ORDER:
            r = A(b, vlo=0.3, vhi=30.0, vsel=(vlo, vhi))
            if len(r) < 2:
                continue
            pg = col(r, "prom")
            ok = np.isfinite(pg)
            print(f"   {vlo:4.1f}-{vhi:<5.1f} {b:9s} {len(episodes(r)):3d} {len(r):4d} "
                  f"{np.nanmedian(col(r, 'f0')):10.2f} {np.nanstd(col(r, 'f0'), ddof=1):5.2f} "
                  f"{np.nanmedian(pg):9.1f} {np.median([bp(*G1826)(x) for x in r]):13.3g} "
                  f"{100 * np.mean(pg[ok] >= 10):9.1f}%")
        print()
    print("   -- V62/V59 ratio of median 18-26 Hz power by speed, with episode-bootstrap CI --")
    for vlo, vhi in [(0.3, 2), (2, 4), (4, 6), (6, 9), (9, 12), (12, 16), (16, 20), (20, 25)]:
        a = A("V62 r37", vlo=0.3, vhi=30.0, vsel=(vlo, vhi))
        c = A("V59 r2c", vlo=0.3, vhi=30.0, vsel=(vlo, vhi))
        if len(a) < 2 or len(c) < 2:
            print(f"   {vlo:4.1f}-{vhi:<5.1f}  n too small (V62 {len(a)}, V59 {len(c)})")
            continue
        rr, lo, hi = boot_ratio(a, c, bp(*G1826))
        print(f"   {vlo:4.1f}-{vhi:<5.1f}  V62 {len(episodes(a)):2d}ep/{len(a):3d}win  "
              f"V59 {len(episodes(c)):2d}ep/{len(c):3d}win   ratio {rr:8.4f}x  "
              f"[95% CI {lo:.4f}, {hi:.4f}]")


def main():
    c1_grinding()
    c3_orders()
    c3b_speed_sweep()
    c4_ratchet()
    c5_shift()
    c6_gating_and_manual()


if __name__ == "__main__":
    main()
