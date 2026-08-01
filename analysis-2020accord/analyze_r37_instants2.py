#!/usr/bin/env python3
"""Which band carries the energy at the two operator instants -- and are they one phenomenon?

Deliverable 4, and the crux the orchestrator flagged: instant 1 is at 2.4 m/s (5.4 mph) and
instant 2 at 7.3 m/s (16.3 mph), yet instant 1 carries the route's most violent transient.

Method: partition the >4 Hz energy of the raw bar into disjoint bands and report each as a
percentage of the total plus an absolute RMS in counts. Percentages alone would let a tiny
absolute signal look dominant; counts alone would hide the partition. Both are given.

Also the pooled engaged-vs-manual gating statistic across every cached build, at episode
granularity, which is the bulletproof form of the gating claim.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402
import _r37_ratchet_lib as L  # noqa: E402

BANDS = [("4-5.5", 4.0, 5.5), ("5.5-12 RATCHET", 5.5, 12.0), ("12-17", 12.0, 17.0),
         ("17-26 GRIND", 17.0, 26.0), ("26-36", 26.0, 36.0), ("36-48", 36.0, 48.0)]


def decompose(x, fs, lab):
    y = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    tot = float(np.sum(np.abs(X[f >= 4.0]) ** 2))
    print(f"  {lab}")
    print(f"      {'band':>16s} {'RMS counts':>11s} {'% of >4Hz energy':>18s}")
    for nm, lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        p = float(np.sum(np.abs(X[m]) ** 2))
        Z = np.zeros(len(f), complex)
        Z[m] = X[m]
        rms = float(np.sqrt(np.mean(np.fft.irfft(Z, n=len(y)) ** 2)))
        print(f"      {nm:>16s} {rms:11.1f} {100*p/max(tot,1e-30):17.1f}%")
    hpz = np.zeros(len(f), complex)
    hpz[f >= 4.0] = X[f >= 4.0]
    print(f"      {'TOTAL >4 Hz':>16s} "
          f"{np.sqrt(np.mean(np.fft.irfft(hpz, n=len(y))**2)):11.1f} {100.0:17.1f}%")


def main():
    cache, pfx = C.ROOT / "_cache_r37", "r37s"
    print("=" * 100)
    print("A. BAND DECOMPOSITION AT THE TWO INSTANTS")
    print("=" * 100)
    for s, t0, t1, lab in (
            (1, 10.24, 11.17, "INSTANT 1  seg1 t 10.24-11.17 (10:12:15), v 2.4 m/s = 5.4 mph"),
            (1, 8.00, 13.00, "instant 1 widened, t 8-13"),
            (12, 17.76, 19.09, "INSTANT 2  seg12 t 17.76-19.09 (10:23:24), v 7.3 m/s = 16.3 mph"),
            (12, 16.00, 21.00, "instant 2 widened, t 16-21"),
            (13, 0.00, 6.00, "reference: seg13 parking-lot ratchet, t 0-6")):
        d = C.load(s, cache, pfx)
        decompose(d["tq"][(d["t"] >= t0) & (d["t"] <= t1)], C.fs_of(d), lab)
        print()

    # ---- context around each instant, +/- 30 s -----------------------------------------------
    print("=" * 100)
    print("B. CONTEXT +/- 30 s, ratchet band RMS and grinding band RMS per 2.56 s window")
    print("=" * 100)
    for s, tc, lab in ((1, 9.67, "instant 1 (10:12:15)"), (12, 18.63, "instant 2 (10:23:24)")):
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        lo, hi = max(tc - 30, float(d["t"][0])), min(tc + 30, float(d["t"][-1]))
        m = (d["t"] >= lo) & (d["t"] <= hi)
        a = int(np.flatnonzero(m)[0])
        b = int(np.flatnonzero(m)[-1]) + 1
        x = d["tq"][a:b]
        br = L.bandpass(x, fs, 5.5, 12.0)
        bg = L.bandpass(x, fs, 17.0, 26.0)
        f = np.fft.rfftfreq(256, 1 / fs)
        print(f"\n  seg{s} {lab}: t {lo:.1f}..{hi:.1f}")
        print(f"    {'t0':>7s} {'ratchet RMS':>12s} {'f0':>6s} {'prom':>8s} | "
              f"{'grind RMS':>10s} {'f0':>6s} {'prom':>7s} | {'vEgo':>6s} {'|ang|':>7s} "
              f"{'eff':>6s} {'|e4|':>6s} {'lat':>4s}")
        for i in range(0, len(x) - 256 + 1, 64):
            P = C.periodogram(x[i:i + 256], fs, 256)
            if P is None:
                continue
            sl = slice(a + i, a + i + 256)
            fr, pr = L.locate(f, P, 5.0, 12.0)
            fg, pg = L.locate(f, P, 17.0, 26.0)
            mark = "  <<" if abs(d["t"][a + i] + 1.28 - tc) < 1.5 else ""
            print(f"    {d['t'][a+i]:7.2f} {np.sqrt(np.mean(br[i:i+256]**2)):12.1f} {fr:6.2f} "
                  f"{pr:8.1f} | {np.sqrt(np.mean(bg[i:i+256]**2)):10.1f} {fg:6.2f} {pg:7.1f} | "
                  f"{np.mean(d['cs_v'][sl]):6.2f} {np.mean(np.abs(d['ang'][sl])):7.1f} "
                  f"{np.mean(np.abs(C.sustained(d['tq'][sl], fs))):6.0f} "
                  f"{np.mean(np.abs(d['e4tq'][sl])):6.0f} "
                  f"{np.mean(d['cc_lat'][sl] > 0.5):4.2f}{mark}")

    # ---- pooled gating ------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("C. POOLED ENGAGED-vs-MANUAL GATING, every cached build, creep 0.3-2.5 m/s, drive gear")
    print("=" * 100)
    tot = {"eng": [], "man": []}
    for nm, ca, pf, sg in L.ROUTES:
        for arm, want in (("eng", True), ("man", False)):
            def mk(d, want=want):
                g = (d["cs_gear"] == 2.0) if "cs_gear" in d else np.ones(len(d["t"]), bool)
                lat = d["cc_lat"] > 0.5
                return ((lat if want else ~lat) & g & (d["cs_v"] > 0.3) & (d["cs_v"] < 2.5))
            rs = L.collect(ca, pf, sg, mask_fn=mk)
            tot[arm] += rs
    for arm in ("eng", "man"):
        rs = tot[arm]
        eps = L.episodes(rs)
        pr = np.array([r["pr"] for r in rs])
        rms = np.array([r["rms_r"] for r in rs])
        ep_hit = sum(1 for e in eps if np.nanmax([x["pr"] for x in e]) >= 10)
        print(f"  {arm.upper():8s} nwin={len(rs):4d} nep={len(eps):3d} | "
              f"windows with prominence>=10: {int((pr>=10).sum()):4d}/{len(rs)} "
              f"({100*np.mean(pr>=10):5.1f}%) | episodes with any window >=10: {ep_hit}/{len(eps)}"
              f" | RMS median {np.nanmedian(rms):7.1f}  p90 {np.nanpercentile(rms,90):7.1f}")

    # ---- health -------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("D. HEALTH, route 37 segs 0-14")
    print("=" * 100)
    n4 = n3 = nz = tot_n = 0
    names = {}
    for s in range(15):
        d = C.load(s, cache, pfx)
        n4 += int((d["sstat"] == 4).sum())
        n3 += int((d["sstat"] == 3).sum())
        nz += int((d["sstat"] != 0).sum())
        tot_n += len(d["sstat"])
        for e in json.loads((cache / f"r37s{s}_events.json").read_text()):
            if e["name"] in ("steerSaturated", "controlsMismatch", "steerUnavailable",
                             "steerTempUnavailable", "commIssue", "selfdriveLagging"):
                names.setdefault(e["name"], []).append((s, e["t"]))
    print(f"  frames {tot_n} | ST==4 (gentle-EME fault) {n4} | ST==3 {n3} | any nonzero {nz}")
    for k, v in names.items():
        print(f"  {k}: n={len(v)}  {v[:6]}")


if __name__ == "__main__":
    main()
