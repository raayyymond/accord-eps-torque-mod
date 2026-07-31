#!/usr/bin/env python3
"""V61 route `31` -- the MATCHED cross-build and cross-arm comparisons.

Two problems the raw arm summaries cannot answer:

  1. Route 31 is a pure parking-lot creep route (engaged |v| 0.8-1.8 m/s only); routes 2c and 2b
     are commutes. Comparing their engaged arms unmatched compares route shapes.
  2. THE MODE HAS MOVED. Route 31's line is at 18.3 Hz, routes 2b/2c at 20.9 Hz. A fixed
     18-26 Hz band is then measuring the two builds at different points on their own curves --
     and 18.3 Hz sits ON the band edge, where the Hann skirt loses part of the peak. So every
     amplitude comparison is ALSO reported in a MODE-TRACKING band (each route's own measured
     f0 +/- 1.5 Hz), which is the like-for-like statistic.

  *** The mode-tracking band is legitimate here ONLY because this is creep: the ratchet is at
  6.5-7.5 Hz, so its 2nd harmonic is 13-15 Hz and cannot leak into 16.8-19.8 Hz. At road speed
  it could, and the strict-band rule would have to stand. Stated, not assumed.

Usage:  python analyze_r31_matched.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from _r31_common import (BAND, CACHE_2B, CACHE_2C, NFFT, SEGS_2B, SEGS_2C,  # noqa: E402
                         SEGS_31, band_envelope, fs_of, load, peak_prom, periodogram,
                         runs_of, sustained)
from analyze_r31_spectra import arm_mask, peaks  # noqa: E402

MODE_F = {"V61 r31": 18.26, "V59 r2c": 20.93, "V58 r2b": 20.84}
HALF = 1.5


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def win_records(segs, arm, cache=None, pfx="r31s", f_mode=None, **kw):
    """Per-window record with BOTH band powers plus the covariates used for matching."""
    out = []
    for s in segs:
        d = load(s, cache, pfx) if cache is not None else load(s)
        m = arm_mask(d, arm, **kw)
        if not m.any():
            continue
        fs = fs_of(d)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        strict = (f >= BAND[0]) & (f <= BAND[1])
        track = (f >= f_mode - HALF) & (f <= f_mode + HALF) if f_mode else strict
        for a, b in runs_of(m, d["t"], NFFT):
            x = d["tq"][a:b]
            env = band_envelope(x, fs, f_mode - HALF, f_mode + HALF) if f_mode \
                else band_envelope(x, fs)
            for i in range(0, len(x) - NFFT + 1, NFFT):
                P = periodogram(x[i:i + NFFT], fs)
                if P is None:
                    continue
                f0, pr = peak_prom(f, P, *BAND)
                pk = peaks(f, P, f_mode - 3.0, f_mode + 3.0, min_prom=0.0) if f_mode else []
                # FREE argmax over 12-30 Hz: wide enough to find a line that moved off the strict
                # band, narrow enough that the ratchet's 2nd harmonic (13-15 Hz at creep) is the
                # only contaminant and shows up as a distinguishable frequency rather than a shift.
                pw = peaks(f, P, 12.0, 30.0, min_prom=0.0)
                sl = slice(a + i, a + i + NFFT)
                out.append(dict(
                    Pstrict=float(P[strict].sum()), Ptrack=float(P[track].sum()),
                    f0=f0, prom=pr,
                    f0w=pw[0][0] if pw else np.nan, promw=pw[0][1] if pw else np.nan,
                    f0t=pk[0][0] if pk else np.nan, promt=pk[0][1] if pk else np.nan,
                    env=float(np.percentile(env[i:i + NFFT], 99)),
                    v=float(np.mean(np.abs(d["cs_v"][sl]))),
                    ang=float(np.mean(np.abs(d["ang"][sl]))),
                    angrate=float(np.mean(np.abs(np.diff(d["ang"][sl]) * fs))),
                    eff=float(np.mean(np.abs(sustained(d["tq"][sl], fs)))),
                    seg=s, t0=float(d["t"][a + i])))
    return out


def col(recs, k):
    return np.array([r[k] for r in recs], float)


def main():
    routes = [(None, "r31s", SEGS_31, "V61 r31"), (CACHE_2C, "r2cs", SEGS_2C, "V59 r2c"),
              (CACHE_2B, "r2bs", SEGS_2B, "V58 r2b")]

    hdr("M1. ENGAGED CREEP, SPEED-MATCHED to route 31's engaged span (|v| 0.8-1.8 m/s)")
    print("   Route 31 engaged exists only in this band, so this is the only honest cross-build")
    print("   comparison. 'strict' = 18-26 Hz; 'track' = each route's OWN f0 +/- 1.5 Hz.")
    print("   *** Windows are cut over the WHOLE creep arm (0.3-5 m/s) and then selected on the")
    print("   window's own mean |v|. Masking the speed band BEFORE cutting windows destroys the")
    print("   2.56 s contiguity requirement and returned n=0 for route 2c -- a fake null.\n")
    print(f"   {'route':10s} {'n':>4s} {'ep':>3s} {'med|v|':>7s} {'med eff':>8s} {'med|ang|':>9s} "
          f"{'P strict':>11s} {'P track':>11s} {'envp99':>8s} {'prom(strict)':>13s} {'f0':>6s}")
    eng, eng_all = {}, {}
    for cache, pfx, segs, name in routes:
        allw = win_records(segs, "any_eng", cache=cache, pfx=pfx, f_mode=MODE_F[name],
                           vmin=0.3, vmax=5.0)
        eng_all[name] = allw
        r = [x for x in allw if 0.8 <= x["v"] <= 1.8]
        eng[name] = r
        if not r:
            print(f"   {name:10s} n=0")
            continue
        neps = len({(x["seg"], int(x["t0"] // 30)) for x in r})
        print(f"   {name:10s} {len(r):4d} {neps:3d} {np.median(col(r,'v')):7.2f} "
              f"{np.median(col(r,'eff')):8.0f} {np.median(col(r,'ang')):9.1f} "
              f"{np.median(col(r,'Pstrict')):11.3e} {np.median(col(r,'Ptrack')):11.3e} "
              f"{np.median(col(r,'env')):8.1f} {np.nanmedian(col(r,'prom')):13.1f} "
              f"{np.nanmedian(col(r,'f0t')):6.2f}")
    print("\n   -- the same, WHOLE creep arm 0.3-5.0 m/s (route shape differs; caveat, not a match) --")
    for name in ("V61 r31", "V59 r2c", "V58 r2b"):
        r = eng_all.get(name) or []
        if not r:
            continue
        print(f"   {name:10s} {len(r):4d}     {np.median(col(r,'v')):7.2f} "
              f"{np.median(col(r,'eff')):8.0f} {np.median(col(r,'ang')):9.1f} "
              f"{np.median(col(r,'Pstrict')):11.3e} {np.median(col(r,'Ptrack')):11.3e} "
              f"{np.median(col(r,'env')):8.1f} {np.nanmedian(col(r,'prom')):13.1f} "
              f"{np.nanmedian(col(r,'f0t')):6.2f}")

    print("\n   -- ratios, V61 vs each predecessor (medians; envelope is amplitude, P is power) --")
    for base in ("V59 r2c", "V58 r2b"):
        if not eng.get(base) or not eng.get("V61 r31"):
            continue
        a, b = eng["V61 r31"], eng[base]
        print(f"   V61 / {base}:  P_strict {np.median(col(a,'Pstrict'))/np.median(col(b,'Pstrict')):6.2f}x"
              f"   P_track {np.median(col(a,'Ptrack'))/np.median(col(b,'Ptrack')):6.2f}x"
              f"   envp99 {np.median(col(a,'env'))/np.median(col(b,'env')):6.2f}x"
              f"   (amplitude ratio = sqrt(P) = "
              f"{np.sqrt(np.median(col(a,'Ptrack'))/np.median(col(b,'Ptrack'))):.2f}x)")

    print("\n   -- speed + effort matched (nearest-neighbour on (|v|, effort), V61 window -> "
          "closest predecessor window) --")
    for base in ("V59 r2c", "V58 r2b"):
        a, b = eng.get("V61 r31"), eng.get(base)
        if not a or not b:
            continue
        va, ea = col(a, "v"), col(a, "eff")
        vb, eb = col(b, "v"), col(b, "eff")
        ratios, dv, de = [], [], []
        for i in range(len(a)):
            dist = ((va[i] - vb) / 0.5) ** 2 + ((ea[i] - eb) / 400.0) ** 2
            j = int(np.argmin(dist))
            ratios.append(a[i]["Ptrack"] / max(b[j]["Ptrack"], 1e-12))
            dv.append(abs(va[i] - vb[j])); de.append(abs(ea[i] - eb[j]))
        ratios = np.array(ratios)
        print(f"   V61 / {base}: n={len(ratios)} pairs  median {np.median(ratios):8.2f}x  "
              f"[p25 {np.percentile(ratios,25):7.2f}, p75 {np.percentile(ratios,75):8.2f}]  "
              f"{int((ratios>1).sum())}/{len(ratios)} pairs > 1   "
              f"match |dv| med {np.median(dv):.2f} m/s, |deff| med {np.median(de):.0f}")

    hdr("M2. THE FREQUENCY SHIFT -- is 18.3 Hz vs 20.9 Hz real, or a speed/effort confound?")
    print("   Route 2c/2b engaged restricted to route 31's exact speed band. If their line stays")
    print("   at ~20.9 Hz there, the shift belongs to the BUILD, not the operating point.")
    print("   f0 is the 12-30 Hz per-window argmax so an 18 Hz answer is not forced by the band.\n")
    for name in ("V61 r31", "V59 r2c", "V58 r2b"):
        for vlo, vhi in [(0.8, 1.8), (0.3, 2.5), (0.3, 5.0)]:
            r = [x for x in eng_all[name] if vlo <= x["v"] <= vhi]
            pr, f0 = col(r, "promw"), col(r, "f0w")
            m = np.isfinite(pr) & (pr >= 10)
            if m.sum() < 2:
                print(f"   {name:10s} |v| {vlo}-{vhi}: n={int(m.sum())} windows with prom>=10x "
                      f"(of {len(r)})")
                continue
            print(f"   {name:10s} |v| {vlo:3.1f}-{vhi:3.1f}: n={int(m.sum()):3d}/{len(r):3d}  "
                  f"f0 = {np.median(f0[m]):5.2f} Hz "
                  f"(sd {f0[m].std(ddof=1):4.2f}, range {f0[m].min():5.2f}-{f0[m].max():5.2f})")
        print()

    hdr("M3. ROUTE 31 INTERNAL -- reverse vs manual-forward, matched on |steering angle|")
    print("   Reverse's confound is huge (med |ang| 307 deg vs 54 deg forward). A driver cranking")
    print("   a wheel makes BROADBAND noise, so the discriminators are prominence and Q, not power;")
    print("   but the angle-matched cells are shown so the reader can see the overlap is thin.\n")
    r31 = {a: win_records(SEGS_31, a, f_mode=MODE_F["V61 r31"]) for a in
           ("eng_fwd", "man_fwd", "man_rev")}
    print(f"   {'arm':16s} {'n':>3s} {'med|ang|':>9s} {'med|angrate|':>13s} {'med eff':>8s} "
          f"{'P track':>11s} {'envp99':>8s} {'prom':>8s} {'f0(track)':>10s}")
    for a, lbl in [("eng_fwd", "engaged FWD"), ("man_fwd", "manual FWD"), ("man_rev", "manual REV")]:
        r = r31[a]
        print(f"   {lbl:16s} {len(r):3d} {np.median(col(r,'ang')):9.1f} "
              f"{np.median(col(r,'angrate')):13.1f} {np.median(col(r,'eff')):8.0f} "
              f"{np.median(col(r,'Ptrack')):11.3e} {np.median(col(r,'env')):8.1f} "
              f"{np.nanmedian(col(r,'promt')):8.1f} {np.nanmedian(col(r,'f0t')):10.2f}")

    print("\n   -- |ang| cells --")
    print(f"   {'|ang| bin':>12s} " + "  ".join(f"{k:>26s}" for k in
                                                ("manual FWD", "manual REV")))
    for lo, hi in [(0, 30), (30, 90), (90, 180), (180, 300), (300, 600)]:
        row = []
        for a in ("man_fwd", "man_rev"):
            sel = [x for x in r31[a] if lo <= x["ang"] < hi]
            row.append(f"n={len(sel):<2d} P {np.median([x['Ptrack'] for x in sel]):.2e} "
                       f"prom {np.nanmedian([x['promt'] for x in sel]):6.1f}" if sel
                       else f"{'-':>26s}")
        print(f"   {lo:5d}-{hi:<5d} " + "  ".join(f"{c:>26s}" for c in row))

    hdr("M4. MANUAL-FORWARD: is the new line tied to TURNING? (operator: 'in some scenarios "
        "when turning the wheel')")
    r = r31["man_fwd"]
    pr = col(r, "promt")
    ar = col(r, "angrate")
    ok = np.isfinite(pr)
    if ok.sum() > 3:
        rho = np.corrcoef(np.argsort(np.argsort(ar[ok])), np.argsort(np.argsort(pr[ok])))[0, 1]
        print(f"   spearman(|angle rate|, mode-band prominence) = {rho:+.3f}  n={int(ok.sum())}")
        hi = ar[ok] >= np.median(ar[ok])
        print(f"   high |angle rate| half: prom med {np.median(pr[ok][hi]):6.1f}  "
              f"P med {np.median(col(r,'Ptrack')[ok][hi]):.3e}  n={int(hi.sum())}")
        print(f"   low  |angle rate| half: prom med {np.median(pr[ok][~hi]):6.1f}  "
              f"P med {np.median(col(r,'Ptrack')[ok][~hi]):.3e}  n={int((~hi).sum())}")
    print("\n   -- the same test on the predecessor routes' manual arms (control) --")
    for cache, pfx, segs, name in routes[1:]:
        rr = win_records(segs, "any_man", cache=cache, pfx=pfx, f_mode=MODE_F[name])
        p = col(rr, "promt")
        o = np.isfinite(p)
        if o.sum() > 3:
            print(f"   {name}: manual n={int(o.sum())}  mode-band prom med {np.median(p[o]):6.1f}"
                  f"  p90 {np.percentile(p[o],90):6.1f}  max {p[o].max():7.1f}  "
                  f"P med {np.median(col(rr,'Ptrack')[o]):.3e}")
    rr = r31["man_fwd"]
    p = col(rr, "promt")
    o = np.isfinite(p)
    print(f"   V61 r31: manual FWD n={int(o.sum())}  mode-band prom med {np.median(p[o]):6.1f}"
          f"  p90 {np.percentile(p[o],90):6.1f}  max {p[o].max():7.1f}  "
          f"P med {np.median(col(rr,'Ptrack')[o]):.3e}")
    rr = r31["man_rev"]
    p = col(rr, "promt")
    o = np.isfinite(p)
    print(f"   V61 r31: manual REV n={int(o.sum())}  mode-band prom med {np.median(p[o]):6.1f}"
          f"  p90 {np.percentile(p[o],90):6.1f}  max {p[o].max():7.1f}  "
          f"P med {np.median(col(rr,'Ptrack')[o]):.3e}")

    hdr("M5. REVERSE, WINDOW BY WINDOW -- n is small, so show every one")
    print("   Also relaxes the |v|>=0.3 gate: the operator reports the grinding WHILE reversing,")
    print("   and reverse spends much of its time below 0.3 m/s (creeping off the brake).\n")
    for vmin, lbl in [(0.3, "moving, |v| >= 0.3"), (0.0, "all reverse frames")]:
        rec = win_records(SEGS_31, "man_rev", f_mode=MODE_F["V61 r31"], vmin=vmin, vmax=5.0)
        print(f"   -- {lbl}: {len(rec)} windows --")
        print(f"   {'seg':>4s} {'t0':>7s} {'|v|':>6s} {'|ang|':>7s} {'eff':>7s} "
              f"{'f0(12-30)':>10s} {'prom':>9s} {'f0(strict)':>11s} {'promS':>8s} {'envp99':>8s}")
        for x in rec:
            print(f"   {x['seg']:4d} {x['t0']:7.2f} {x['v']:6.2f} {x['ang']:7.1f} {x['eff']:7.0f} "
                  f"{x['f0w']:10.2f} {x['promw']:9.1f} {x['f0']:11.2f} {x['prom']:8.1f} "
                  f"{x['env']:8.1f}")
        print()
    print("   -- manual FORWARD, every window with strict-band prominence >= 10x --")
    print(f"   {'seg':>4s} {'t0':>7s} {'|v|':>6s} {'|ang|':>7s} {'|angrate|':>10s} {'eff':>7s} "
          f"{'f0(12-30)':>10s} {'prom':>9s} {'envp99':>8s}")
    for x in sorted(r31["man_fwd"], key=lambda z: -(z["prom"] if np.isfinite(z["prom"]) else 0)):
        if np.isfinite(x["prom"]) and x["prom"] >= 10:
            print(f"   {x['seg']:4d} {x['t0']:7.2f} {x['v']:6.2f} {x['ang']:7.1f} "
                  f"{x['angrate']:10.1f} {x['eff']:7.0f} {x['f0w']:10.2f} {x['prom']:9.1f} "
                  f"{x['env']:8.1f}")


if __name__ == "__main__":
    main()
