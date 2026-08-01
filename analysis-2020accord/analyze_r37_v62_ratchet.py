#!/usr/bin/env python3
"""V62 route `37` supplement -- the three things the headline script leaves open.

  1. ROUTE CONTENT. Route 37 is a commute (segs 1-12) PLUS a deliberate end-of-route parking-lot
     test (segs 13-14). Route 2c (V59) and route 35 (V64) are commutes with no lot. Pooling the lot
     into route 37's engaged-creep arm therefore compares route SHAPES, not builds. Everything is
     re-run split road/lot.
  2. EFFORT. V62's creep windows sit at different driver effort from V59's, and on this platform
     the mode is LOUDEST hands-off -- so an effort mismatch can flatter or damn either build.
     Nearest-neighbour matching on (|v|, effort), the method of analyze_r31_matched.py.
  3. WHAT THE 6-9 Hz LINE ACTUALLY IS on route 37, where prominence reaches 5.2e4x. A number that
     large is either a very pure tone or an artifact, and it must be looked at in the time domain
     before it is reported as "the ratchet".

Read with analyze_r37_v62_creep.py; conventions are imported from _r31_common, not restated.
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

from _r31_common import (NFFT, band_envelope, fs_of, load, peak_prom,  # noqa: E402
                         periodogram, runs_of, sustained)
from analyze_r37_v62_creep import (BUILDS, GRIND, HALF, ORDER, PRESENCE, RATCH,  # noqa: E402
                                   SPEED_CAP, bandpower, col, hdr, msd, nrun, pooled_f0,
                                   track_prom, wrecs)

ROAD_37 = list(range(0, 13))     # seg 0 INCLUDED -- real driving, see analyze_r37_v62_creep.py
LOT_37 = [13, 14]


def summarise(lbl, r, f0, extra=""):
    if not r:
        print(f"   {lbl:34s}   -- n=0 windows")
        return
    f0m, f0s = msd(col(r, "f0"))
    pf, pt = col(r, "prom"), track_prom(r, f0)
    ok = np.isfinite(pt)
    Pt, P69 = bandpower(r, f0 - HALF, f0 + HALF), bandpower(r, *RATCH)
    print(f"   {lbl:34s} {nrun(r):3d} ep {len(r):4d} win | f0 {f0m:6.2f} sd {f0s:4.2f} "
          f"promFREE {np.nanmedian(pf):8.1f} promTRK {np.nanmedian(pt):8.1f} "
          f"pres {100 * np.mean(pt[ok] >= PRESENCE) if ok.any() else float('nan'):5.1f}% | "
          f"env99 {np.median(col(r, 'env')):7.1f} P(trk) {np.median(Pt):9.3g} "
          f"P(6-9) {np.median(P69):9.3g} | v {np.median(col(r, 'v')):4.2f} "
          f"eff {np.median(col(r, 'eff')):5.0f}{extra}")


def road_vs_lot():
    hdr("R1.  ROUTE CONTENT -- route 37's commute (segs 1-12) vs its parking lot (segs 13-14)")
    print("   V59/V64 have NO parking-lot arm, so the commute rows are the like-for-like comparison")
    print("   and the lot rows are route-37-only. Engaged creep 0.3-%.2f m/s, all-hands." % SPEED_CAP)
    f0b = {b: pooled_f0(wrecs(b))[0] for b in ORDER}
    print()
    for b in ORDER:
        summarise(f"{b}  whole route", wrecs(b, band=(f0b[b] - HALF, f0b[b] + HALF)), f0b[b])
    print()
    summarise("V62 r37  COMMUTE segs 1-12",
              wrecs("V62 r37", band=(f0b["V62 r37"] - HALF, f0b["V62 r37"] + HALF), segs=ROAD_37),
              f0b["V62 r37"])
    summarise("V62 r37  LOT segs 13-14",
              wrecs("V62 r37", band=(f0b["V62 r37"] - HALF, f0b["V62 r37"] + HALF), segs=LOT_37),
              f0b["V62 r37"])
    print("\n   -- and measured in V59's band instead, so the two builds share one ruler --")
    fv = f0b["V59 r2c"]
    for b in ORDER:
        summarise(f"{b}  in V59 band", wrecs(b, band=(fv - HALF, fv + HALF)), fv)
    summarise("V62 COMMUTE in V59 band",
              wrecs("V62 r37", band=(fv - HALF, fv + HALF), segs=ROAD_37), fv)
    summarise("V62 LOT     in V59 band",
              wrecs("V62 r37", band=(fv - HALF, fv + HALF), segs=LOT_37), fv)


def effort_matched():
    hdr("R2.  SPEED- AND EFFORT-MATCHED -- nearest neighbour on (|v|, effort), V62 -> control")
    print("   On this platform the mode is LOUDEST hands-off (damping product is zero below 2240")
    print("   counts hands-off), so a V62 arm sitting at LOWER effort than its control is being")
    print("   compared under conditions that historically make the mode WORSE, not better.\n")
    f0b = {b: pooled_f0(wrecs(b))[0] for b in ORDER}
    fv = f0b["V59 r2c"]
    tgt = {b: wrecs(b, band=(fv - HALF, fv + HALF)) for b in ORDER}
    tgt["V62 commute"] = wrecs("V62 r37", band=(fv - HALF, fv + HALF), segs=ROAD_37)

    print(f"   effort distribution of each engaged-creep arm (sustained |lowpass(tq,3Hz)|):")
    for b in list(ORDER) + ["V62 commute"]:
        e = col(tgt[b], "eff")
        v = col(tgt[b], "v")
        print(f"     {b:14s} n={len(e):3d}  eff p10/p50/p90 {np.percentile(e,10):5.0f}/"
              f"{np.percentile(e,50):5.0f}/{np.percentile(e,90):5.0f}   "
              f"|v| p10/p50/p90 {np.percentile(v,10):4.2f}/{np.percentile(v,50):4.2f}/"
              f"{np.percentile(v,90):4.2f}")

    print("\n   pairwise, all measured in V59's 21.13 +/- 1.5 Hz band (P = power, env = amplitude):")
    for a, bse in (("V62 r37", "V59 r2c"), ("V62 commute", "V59 r2c"), ("V62 r37", "V64 r35"),
                   ("V62 commute", "V64 r35"), ("V64 r35", "V59 r2c")):
        A, B = tgt[a], tgt[bse]
        if not A or not B:
            continue
        va, ea = col(A, "v"), col(A, "eff")
        vb, eb = col(B, "v"), col(B, "eff")
        PA = bandpower(A, fv - HALF, fv + HALF)
        PB = bandpower(B, fv - HALF, fv + HALF)
        EA, EB = col(A, "env"), col(B, "env")
        rp, re, dv, de = [], [], [], []
        for i in range(len(A)):
            j = int(np.argmin(((va[i] - vb) / 0.5) ** 2 + ((ea[i] - eb) / 400.0) ** 2))
            rp.append(PA[i] / max(PB[j], 1e-12))
            re.append(EA[i] / max(EB[j], 1e-12))
            dv.append(abs(va[i] - vb[j])); de.append(abs(ea[i] - eb[j]))
        rp, re = np.array(rp), np.array(re)
        print(f"     {a:12s} / {bse:8s} n={len(rp):3d} pairs | P ratio med {np.median(rp):7.3f}x "
              f"[p25 {np.percentile(rp,25):6.3f}, p75 {np.percentile(rp,75):7.3f}]  "
              f"{int((rp<1).sum())}/{len(rp)} pairs < 1 | env ratio med {np.median(re):6.3f}x | "
              f"match |dv| {np.median(dv):.2f} m/s |deff| {np.median(de):.0f}")


def ratchet_detail():
    hdr("R3.  WHAT IS THE 6-9 Hz LINE ON ROUTE 37?  prominence reaches 5.2e4x -- look at it")
    r = wrecs("V62 r37")
    r.sort(key=lambda x: -(x["promr"] if np.isfinite(x["promr"]) else 0))
    print(f"   top 12 engaged-creep windows by 6-9 Hz prominence, route 37")
    print(f"   {'seg':>4s} {'t0':>7s} {'|v|':>5s} {'|ang|':>7s} {'eff':>6s} {'f 6-9':>6s} "
          f"{'prom':>10s} {'P(6-9)':>10s} {'f 12-30':>8s} {'prom':>8s} {'P(12-30)':>10s}")
    for x in r[:12]:
        P69 = x["P"][(x["f"] >= 6) & (x["f"] <= 9)].sum()
        P12 = x["P"][(x["f"] >= 12) & (x["f"] <= 30)].sum()
        print(f"   {x['seg']:4d} {x['t0']:7.2f} {x['v']:5.2f} {x['ang']:7.1f} {x['eff']:6.0f} "
              f"{x['fr']:6.2f} {x['promr']:10.1f} {P69:10.3g} {x['f0']:8.2f} {x['prom']:8.1f} "
              f"{P12:10.3g}")

    print("\n   -- time-domain look at the single loudest window (no rfft bin index involved) --")
    x = r[0]
    d = load(x["seg"], BUILDS["V62 r37"]["cache"], "r37s")
    fs = fs_of(d)
    i0 = int(np.argmin(np.abs(d["t"] - x["t0"])))
    sl = slice(i0, i0 + NFFT)
    y = d["tq"][sl]
    yb = band_envelope(y, fs, *RATCH)
    print(f"   seg{x['seg']} t={x['t0']:.2f}-{x['t0'] + NFFT / fs:.2f}s  raw tq: "
          f"min {y.min():.0f} max {y.max():.0f} pp {y.max() - y.min():.0f} sd {y.std():.0f}")
    print(f"   6-9 Hz envelope: med {np.median(yb):.0f} p99 {np.percentile(yb, 99):.0f} "
          f"(=> pp {2 * np.percentile(yb, 99):.0f} counts)")
    z = y - y.mean()
    Z = np.fft.rfft(z * np.hanning(len(z)))
    ff = np.fft.rfftfreq(len(z), 1 / fs)
    s = np.argsort(-np.abs(Z) ** 2)[:6]
    print("   strongest bins: " + "  ".join(f"{ff[k]:.2f} Hz {np.abs(Z[k])**2:.2e}"
                                            for k in sorted(s, key=lambda q: -np.abs(Z[q]))))
    # upward zero crossings of the band-passed signal -- an independent period estimate
    X = np.fft.rfft(z)
    X[(ff < RATCH[0]) | (ff > RATCH[1])] = 0
    bp = np.fft.irfft(X, n=len(z))
    sgn = np.signbit(bp)
    idx = np.flatnonzero(sgn[:-1] & ~sgn[1:])
    if len(idx) >= 3:
        frac = -bp[idx] / (bp[idx + 1] - bp[idx])
        tcr = (idx + frac) / fs
        print(f"   zero-crossing period estimate: {1 / np.mean(np.diff(tcr)):.2f} Hz "
              f"({len(idx)} crossings, sd of spacing {np.std(np.diff(tcr)) * 1000:.1f} ms)")

    print("\n   -- 6-9 Hz on route 37, split road vs lot, engaged creep --")
    for lbl, segs in (("COMMUTE segs 1-12", ROAD_37), ("LOT segs 13-14", LOT_37)):
        rr = wrecs("V62 r37", segs=segs)
        if not rr:
            print(f"   {lbl}: n=0")
            continue
        pr = col(rr, "promr")
        ok = np.isfinite(pr)
        print(f"   {lbl:22s} {nrun(rr):3d} ep {len(rr):3d} win  f0 {np.nanmedian(col(rr,'fr')):5.2f} "
              f"sd {np.nanstd(col(rr,'fr'), ddof=1):4.2f}  prom med {np.nanmedian(pr):8.1f} "
              f"p90 {np.nanpercentile(pr,90):9.1f} max {np.nanmax(pr):9.1f}  "
              f"P(6-9) med {np.median(bandpower(rr, *RATCH)):9.3g}  "
              f"pres {100 * np.mean(pr[ok] >= PRESENCE):5.1f}%")

    print("\n   -- the same 6-9 Hz statistic on the CONTROLS' engaged creep (commutes, no lot) --")
    for b in ("V59 r2c", "V64 r35", "V61 r31"):
        rr = wrecs(b)
        pr = col(rr, "promr")
        ok = np.isfinite(pr)
        print(f"   {b:22s} {nrun(rr):3d} ep {len(rr):3d} win  f0 {np.nanmedian(col(rr,'fr')):5.2f} "
              f"sd {np.nanstd(col(rr,'fr'), ddof=1):4.2f}  prom med {np.nanmedian(pr):8.1f} "
              f"p90 {np.nanpercentile(pr,90):9.1f} max {np.nanmax(pr):9.1f}  "
              f"P(6-9) med {np.median(bandpower(rr, *RATCH)):9.3g}  "
              f"pres {100 * np.mean(pr[ok] >= PRESENCE):5.1f}%")


def lot_inventory():
    hdr("R4.  ROUTE 37 PARKING LOT (segs 13-14) -- what the operator was doing during the test")
    for s in LOT_37:
        d = load(s, BUILDS["V62 r37"]["cache"], "r37s")
        fs = fs_of(d)
        lat = d["cc_lat"] > 0.5
        g = d["cs_gear"]
        eff = np.abs(sustained(d["tq"], fs))
        print(f"\n   seg{s}: {len(d['t'])} frames {d['t'][-1]:.1f}s  |v| {np.abs(d['cs_v']).min():.2f}"
              f"..{np.abs(d['cs_v']).max():.2f}  latActive {100 * lat.mean():.1f}%  "
              f"|ang| med {np.median(np.abs(d['ang'])):.0f} max {np.abs(d['ang']).max():.0f} deg")
        print(f"        gear frames: " + "  ".join(
            f"{['unk','park','drive','neut','rev','sport','low','brake','eco','manu'][int(k)]}:{int((g==k).sum())}"
            for k in np.unique(g)))
        print(f"        |tq| p50 {np.percentile(np.abs(d['tq']),50):.0f} p99 "
              f"{np.percentile(np.abs(d['tq']),99):.0f} max {np.abs(d['tq']).max():.0f}   "
              f"effort p50 {np.median(eff):.0f} p99 {np.percentile(eff,99):.0f}")
        for a, b in runs_of(lat, d["t"], 100):
            print(f"        engaged {d['t'][a]:6.1f}-{d['t'][b-1]:6.1f}s ({(b-a)/fs:5.1f}s) "
                  f"|v| {np.abs(d['cs_v'][a:b]).min():.2f}-{np.abs(d['cs_v'][a:b]).max():.2f}  "
                  f"|ang| {np.abs(d['ang'][a:b]).min():.0f}-{np.abs(d['ang'][a:b]).max():.0f} deg")


def band_sweep():
    hdr("R5.  FULL-BAND POWER LEDGER, engaged creep -- absolute, so nothing hides in a ratio")
    print(f"   {'build':14s} {'win':>4s} " + "".join(
        f"{lo}-{hi}Hz".rjust(12) for lo, hi in
        [(3, 6), (6, 9), (9, 12), (12, 18), (18, 26), (26, 34), (34, 46)]))
    for b in list(ORDER):
        r = wrecs(b)
        if not r:
            continue
        cells = "".join(f"{np.median(bandpower(r, lo, hi)):12.3g}" for lo, hi in
                        [(3, 6), (6, 9), (9, 12), (12, 18), (18, 26), (26, 34), (34, 46)])
        print(f"   {b:14s} {len(r):4d} {cells}")
    for lbl, segs in (("V62 commute", ROAD_37), ("V62 lot", LOT_37)):
        r = wrecs("V62 r37", segs=segs)
        cells = "".join(f"{np.median(bandpower(r, lo, hi)):12.3g}" for lo, hi in
                        [(3, 6), (6, 9), (9, 12), (12, 18), (18, 26), (26, 34), (34, 46)])
        print(f"   {lbl:14s} {len(r):4d} {cells}")
    print("\n   (medians over windows, so this is the TYPICAL window, not the sum of the arm)")


def main():
    road_vs_lot()
    effort_matched()
    ratchet_detail()
    lot_inventory()
    band_sweep()


if __name__ == "__main__":
    main()
