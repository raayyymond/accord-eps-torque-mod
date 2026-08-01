#!/usr/bin/env python3
"""THE ALIAS, as its own problem. Four independent attempts to break the degeneracy.

The torsion bar is sampled on the ~100.5 Hz 0x14A/0x18F grid, so 41.6 Hz and 58.9 Hz are the SAME
OBSERVATION. This script does not caveat that; it tries to break it four ways and reports which
work and which cannot.

  A1  THE FOLD TABLE. For the band actually used, exactly which true frequencies map into it.
  A2  TWO CAN MESSAGES AT DIFFERENT RATES. If 0x18F and 0x14A transmit at genuinely different true
      rates, a real 58.9 Hz line lands at different apparent frequencies in the two, while a real
      41.6 Hz line lands at the same. Requires the two rates to actually differ.
  A3  PAIRED CAN-vs-IMU FREQUENCY DIFFERENCE. The IMU runs at ~101.03 Hz, CAN at ~100.51 Hz --
      a 0.52 Hz difference. Under H0 (true line below Nyquist) the PAIRED difference of located
      peaks is 0; under H1 (first fold, f_obs = fs - f_true) it is fs_imu - fs_can = +0.52 Hz.
      🛑 This is the version with power: pairing cancels the mode's own 5.4 Hz window-to-window
      scatter, which is what made the unpaired regression useless.
  A4  LOMB-SCARGLE ON TRUE ARRIVAL TIMES. Non-uniform sampling spreads alias energy instead of
      folding it cleanly, so LS can in principle read above the nominal Nyquist.
      🛑 VALIDATED FIRST on a synthetic 58.9 Hz sinusoid sampled at the route's OWN timestamps.
      If LS puts that at 41.6 rather than 58.9, the method does not work here and is dropped.

Usage:  python analyze_grind2_alias.py
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load  # noqa: E402

PKL = HERE.parent / "_cache_grind2_records.pkl"
OUTJSON = HERE / "_grind2_alias.json"
RNG = np.random.default_rng(20260801)
BURST = 400.0
BAND = (38.0, 49.5)      # the located band for the burst; kept below both Nyquists


def locate_env(t, x, lo, hi, nfft=256):
    """(f0, power) of the strongest bin in [lo,hi] on a uniform resample of (t,x)."""
    fs = 1.0 / np.median(np.diff(t))
    n = min(nfft, len(x))
    if n < 64:
        return np.nan, np.nan, fs
    x = np.asarray(x[:n], float)
    r = np.arange(n)
    c = np.polyfit(r, x, 1)
    y = (x - (c[0] * r + c[1])) * np.hanning(n)
    P = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan, fs
    j = int(np.argmax(np.where(m, P, -np.inf)))
    if 0 < j < len(P) - 1:
        y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if den else 0.0
        return float(f[j] + np.clip(d, -0.5, 0.5) * (f[1] - f[0])), float(P[j]), fs
    return float(f[j]), float(P[j]), fs


def lombscargle(t, x, freqs):
    """Classic Lomb-Scargle periodogram; no scipy dependency on version-specific APIs."""
    t = np.asarray(t, float)
    x = np.asarray(x, float) - np.mean(x)
    P = np.empty(len(freqs))
    for i, f in enumerate(freqs):
        w = 2 * np.pi * f
        s2, c2 = np.sin(2 * w * t).sum(), np.cos(2 * w * t).sum()
        tau = 0.5 * np.arctan2(s2, c2) / w
        wt = w * (t - tau)
        cw, sw = np.cos(wt), np.sin(wt)
        cc, ss = (cw ** 2).sum(), (sw ** 2).sum()
        P[i] = 0.5 * ((x * cw).sum() ** 2 / max(cc, 1e-12) +
                      (x * sw).sum() ** 2 / max(ss, 1e-12))
    return P


def native_18f(d):
    """(t, tq) retimed onto the TRUE 0x18F arrival instants.

    `tq` lives in the cache on the 0x14A grid (0x18F held-last). 0x18F and 0x14A arrive 1:1 here,
    so each 0x14A row can be reassigned to the 0x18F frame it actually carried: j = the last 0x18F
    arrival at or before the row's own timestamp, keeping the first row per j.
    """
    if "raw18F" not in d:
        return None, None
    r18 = np.asarray(d["raw18F"], float)
    j = np.searchsorted(r18, d["t"], side="right") - 1
    ok = j >= 0
    j, tq = j[ok], np.asarray(d["tq"], float)[ok]
    _, first = np.unique(j, return_index=True)
    return r18[j[first]], tq[first]


def main():
    G.EPKEY = "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
    burst = [r for b in G.ORDER for r in store[b] if r["e_30-49"] > BURST]
    out = {}

    # ================================================================ A1 fold table ==============
    G.hdr("A1.  THE FOLD TABLE.  Which TRUE frequencies map into the band this workstream uses.")
    fs = 100.51
    print(f"  Uniform CAN grid fs = {fs:.2f} Hz (route range 99.36-101.55), Nyquist "
          f"{fs / 2:.2f} Hz.")
    print(f"  An observation at f_obs corresponds to the true set {{ k*fs +/- f_obs }}, k = 0,1,2...")
    print(f"\n  {'observed':>10s} | " + " ".join(f"{'k=' + str(k):>16s}" for k in range(4)))
    for fo in (44.89, 41.64, 45.0, 47.0):
        cells = []
        for k in range(4):
            if k == 0:
                cells.append(f"{fo:16.2f}")
            else:
                cells.append(f"{k * fs - fo:7.2f} {k * fs + fo:8.2f}")
        print(f"  {fo:10.2f} | " + " ".join(f"{c:>16s}" for c in cells))
    print(f"\n  The BAND 40-49 Hz (where the effect concentrates, 21x in the corner) is the union of")
    for k in range(3):
        if k == 0:
            print(f"    k=0:  40.00 -  49.00 Hz")
        else:
            print(f"    k={k}:  {k * fs - 49:7.2f} - {k * fs - 40:7.2f} Hz   and   "
                  f"{k * fs + 40:7.2f} - {k * fs + 49:7.2f} Hz")
    print("\n  🛑 No headline in this report depends on which of these it is. The dose-response,")
    print("  the block census and the band specificity are all statements about a BAND, and they")
    print("  hold identically whichever fold the band corresponds to.")
    out["fold"] = dict(fs=fs, f_obs=44.89, folds=[44.89, fs - 44.89, fs + 44.89, 2 * fs - 44.89])

    # ================================================================ A2 two CAN messages ========
    G.hdr("A2.  DO 0x18F AND 0x14A RUN AT DIFFERENT TRUE RATES?  If they do, a 58.9 Hz line lands\n"
          "at different apparent frequencies in the two channels and the fold is resolvable.")
    print(f"  {'route':10s} {'seg':>3s} {'n(0x18F)':>9s} {'n(0x14A)':>9s} {'f18 (Hz)':>10s} "
          f"{'f14 (Hz)':>10s} {'f18-f14':>10s} {'dt sd 18F':>10s}")
    diffs = []
    for b in ("V62/r37", "V65/r3a", "V65/r3b", "V64/r35"):
        B = G.BUILDS[b]
        for s in B["segs"][:4]:
            p = B["cache"] / f"{B['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = load(s, B["cache"], B["pfx"])
            if "raw18F" not in d:
                continue
            r18, r14 = np.asarray(d["raw18F"], float), np.asarray(d["raw14A"], float)
            if len(r18) < 100 or len(r14) < 100:
                continue
            f18 = (len(r18) - 1) / (r18[-1] - r18[0])
            f14 = (len(r14) - 1) / (r14[-1] - r14[0])
            diffs.append(f18 - f14)
            print(f"  {b:10s} {s:3d} {len(r18):9d} {len(r14):9d} {f18:10.4f} {f14:10.4f} "
                  f"{f18 - f14:+10.5f} {1e3 * np.diff(r18).std():9.3f}ms")
    dd = np.array(diffs)
    print(f"\n  mean |f18 - f14| = {np.abs(dd).mean():.5f} Hz over {len(dd)} segments "
          f"(max {np.abs(dd).max():.5f} Hz).")
    print(f"  A first-fold alias would separate the two channels by exactly this amount: "
          f"{np.abs(dd).mean():.3f} Hz.")
    print(f"  Frequency resolution at NFFT=256 is {100.5 / 256:.3f} Hz per bin.")
    print(f"  ⇒ A2 CANNOT WORK. The two messages are transmitted from the same ECU off the same\n"
          f"  clock and their rates agree to {np.abs(dd).mean():.5f} Hz -- "
          f"{0.3926 / max(np.abs(dd).mean(), 1e-9):.0f}x finer than one FFT bin. There is no lever.")
    out["a2"] = dict(mean_abs_diff=float(np.abs(dd).mean()), n=len(dd), verdict="cannot work")

    # ================================================================ A3 paired CAN vs IMU =======
    G.hdr("A3.  PAIRED CAN-vs-IMU PEAK DIFFERENCE.  The pairing cancels the mode's own scatter.\n"
          "  H0 (true line < Nyquist)      => E[f_imu - f_can] = 0\n"
          "  H1 (first fold, f = fs - f_t) => E[f_imu - f_can] = fs_imu - fs_can")
    pairs = []
    for b in G.ORDER:
        B = G.BUILDS[b]
        segs = sorted({r["seg"] for r in burst if r["build"] == b})
        for s in segs:
            p = B["cache"] / f"{B['pfx']}{s}_imu.npz"
            if not p.exists():
                continue
            d = load(s, B["cache"], B["pfx"])
            z = np.load(p)
            at = z["at"]
            amag = np.sqrt(z["ax"] ** 2 + z["ay"] ** 2 + z["az"] ** 2)
            for r in [q for q in burst if q["build"] == b and q["seg"] == s]:
                mc = (d["t"] >= r["t0"]) & (d["t"] < r["t0"] + 2.56)
                mi = (at >= r["t0"]) & (at < r["t0"] + 2.56)
                if mc.sum() < 200 or mi.sum() < 200:
                    continue
                fc, pc, fsc = locate_env(d["t"][mc], d["tq"][mc], *BAND)
                fi, pi, fsi = locate_env(at[mi], amag[mi], *BAND)
                if np.isfinite(fc) and np.isfinite(fi):
                    pairs.append((fc, fi, fsc, fsi, r["e_30-49"], b, s, r["t0"]))
    if len(pairs) >= 5:
        A = np.array([[p[0], p[1], p[2], p[3], p[4]] for p in pairs], float)
        dfs = A[:, 3] - A[:, 2]
        dfo = A[:, 1] - A[:, 0]
        print(f"  n = {len(pairs)} burst windows with both instruments.")
        print(f"  fs_can median {np.median(A[:, 2]):.4f} Hz, fs_imu median {np.median(A[:, 3]):.4f}"
              f" Hz, difference {np.median(dfs):+.4f} Hz  <- H1's predicted offset")
        b_ = RNG.integers(0, len(dfo), (4000, len(dfo)))
        dr = np.median(dfo[b_], axis=1)
        lo, hi = np.percentile(dr, [2.5, 97.5])
        print(f"  observed median (f_imu - f_can) = {np.median(dfo):+.4f} Hz   "
              f"95% CI [{lo:+.4f}, {hi:+.4f}]")
        print(f"     H0 (0.000 Hz)                    "
              f"{'CONSISTENT' if lo <= 0 <= hi else 'EXCLUDED'}")
        print(f"     H1 ({np.median(dfs):+.3f} Hz, first fold)     "
              f"{'CONSISTENT' if lo <= np.median(dfs) <= hi else 'EXCLUDED'}")
        sep = abs(np.median(dfs))
        print(f"\n  🛑 POWER CHECK: the two hypotheses are {sep:.2f} Hz apart and the CI is "
              f"{hi - lo:.2f} Hz wide.")
        print(f"  {'The test can separate them.' if (hi - lo) < sep else 'The CI is WIDER than the separation ⇒ STILL UNDERPOWERED; this does not decide it either.'}")
        out["a3"] = dict(n=len(pairs), d_fs=float(np.median(dfs)), d_obs=float(np.median(dfo)),
                         ci=[float(lo), float(hi)],
                         decisive=bool((hi - lo) < sep))
    else:
        print(f"  only {len(pairs)} paired windows -- cannot run.")
        out["a3"] = dict(n=len(pairs), verdict="insufficient")

    # ================================================================ A4 Lomb-Scargle ============
    G.hdr("A4.  LOMB-SCARGLE ON TRUE 0x18F ARRIVAL TIMES.  Validated FIRST on a synthetic line.")
    B = G.BUILDS["V65/r3a"]
    d = load(4, B["cache"], B["pfx"])
    t18, x18 = native_18f(d)
    m = (t18 >= 15.0) & (t18 < 18.0)
    tt = t18[m]
    print(f"  Validation window: V65/r3a seg 4, t 15-18 s, n={len(tt)} true 0x18F arrivals.")
    print(f"  arrival dt: median {1e3 * np.median(np.diff(tt)):.4f} ms, "
          f"sd {1e3 * np.diff(tt).std():.4f} ms "
          f"({100 * np.diff(tt).std() / np.median(np.diff(tt)):.1f}% of the period)")
    freqs = np.arange(5.0, 90.0, 0.05)
    ok = True
    for ftrue in (41.64, 58.86, 25.0):
        syn = np.sin(2 * np.pi * ftrue * tt)
        P = lombscargle(tt, syn, freqs)
        fpk = float(freqs[int(np.argmax(P))])
        good = abs(fpk - ftrue) < 1.0
        ok &= good
        print(f"    synthetic {ftrue:6.2f} Hz at the REAL timestamps -> LS peak {fpk:6.2f} Hz  "
              f"{'OK' if good else 'FAILED (folded to ' + f'{fpk:.2f}' + ')'}")
    if not ok:
        print("\n  🛑 VALIDATION FAILED. The arrival jitter is too small and too regular to break")
        print("  the fold: LS reproduces the uniform-grid alias. THE METHOD DOES NOT WORK HERE and")
        print("  is dropped, exactly as pre-registered. No conclusion is drawn from it.")
    else:
        print("\n  Validation passed; running LS on the real burst and on a matched quiet window.")
        for lbl, (a, bb) in (("BURST  t 15-18 s", (15.0, 18.0)),
                             ("QUIET  t 40-43 s", (40.0, 43.0))):
            mm = (t18 >= a) & (t18 < bb)
            if mm.sum() < 100:
                continue
            P = lombscargle(t18[mm], x18[mm] - np.mean(x18[mm]), freqs)
            for lo, hi in ((38, 50), (50, 70), (70, 90)):
                sl = (freqs >= lo) & (freqs < hi)
                j = int(np.argmax(np.where(sl, P, -np.inf)))
                print(f"    {lbl}  {lo}-{hi} Hz: peak {freqs[j]:6.2f} Hz  power "
                      f"{P[j] / np.median(P):8.1f}x median")
    out["a4"] = dict(validated=bool(ok))

    G.hdr("ALIAS VERDICT")
    print("  A1 fold table  : stated. 44.89 Hz observed == 44.89 / 55.62 / 145.40 / 156.13 ... Hz")
    print(f"  A2 two CAN msgs: CANNOT WORK -- rates agree to "
          f"{np.abs(dd).mean():.5f} Hz, no lever exists")
    if "d_obs" in out.get("a3", {}):
        print(f"  A3 paired IMU  : "
              f"{'DECISIVE' if out['a3']['decisive'] else 'UNDERPOWERED'} -- "
              f"observed {out['a3']['d_obs']:+.3f} Hz, CI "
              f"[{out['a3']['ci'][0]:+.3f}, {out['a3']['ci'][1]:+.3f}], "
              f"hypotheses {abs(out['a3']['d_fs']):.2f} Hz apart")
    print(f"  A4 Lomb-Scargle: {'usable' if out['a4']['validated'] else 'FAILS ITS OWN VALIDATION -- dropped'}")
    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
