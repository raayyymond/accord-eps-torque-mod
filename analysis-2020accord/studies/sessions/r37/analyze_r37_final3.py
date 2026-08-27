#!/usr/bin/env python3
"""Route-37 close-out: the three questions that survive a ~2.2x resolution floor.

  1. The two operator instants, characterised and compared. Waveform above all.
  2. Engaged-vs-manual gating, WITHIN route 37 segs 13/14 (a within-build, within-route contrast,
     so it is not exposed to the cross-route exposure weakness).
  3. Is anything at the instants OUTSIDE 6-12 and 18-22 Hz? Free 5-45 locate + presence test.

Everything is reported with n. Where the data cannot answer, it says so.
🛑 fs is 100.3-101.4 Hz, so every frequency here is indistinguishable from its aliases
(7.3 = 93.1, 21 = 79.5, 42 = 58.6 Hz). Stated once; true throughout.
"""
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
import sys
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact, skew

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402
import _r37_ratchet_lib as L  # noqa: E402

CACHE, PFX = C.ROOT / "_scratch/cache/r37", "r37s"
NF = 256


def hp(x, fs, fc=4.0):
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f < fc] = 0
    return np.fft.irfft(X, n=len(x))


# ==============================================================================================
def q1_waveform():
    print("=" * 118)
    print("1. THE TWO INSTANTS -- WAVEFORM")
    print("=" * 118)

    d = C.load(1, CACHE, PFX)
    fs = C.fs_of(d)
    m = (d["t"] >= 10.18) & (d["t"] <= 10.80)
    idx = np.flatnonzero(m)
    print(f"\nINSTANT 1 core, seg1 t 10.18-10.80 s (10:12:15), fs={fs:.2f}. RAW `tq`, counts.")
    print("  Every sample. d = change from previous sample (10 ms).")
    print(f"  {'t':>7s} {'tq':>7s} {'d':>7s}   waveform (-4096 .. +4096)")
    for i in idx:
        v = d["tq"][i]
        pos = int(round(30 + 29 * np.clip(v / 4096.0, -1, 1)))
        print(f"  {d['t'][i]:7.3f} {v:7.0f} {v - d['tq'][i-1]:7.0f}   |"
              + " " * pos + "*")

    print("\n  Sign-change count and dwell: a stick-slip sawtooth dwells long on one side and")
    print("  snaps back; a saturated resonance alternates with near-equal dwell either side.")
    for lab, s, t0, t1 in (("instant 1 core", 1, 10.20, 10.75),
                           ("instant 1 wide", 1, 8.00, 13.00),
                           ("instant 2 core", 12, 17.76, 19.09),
                           ("instant 2 wide", 12, 16.00, 21.00),
                           ("seg13 ratchet ref", 13, 0.00, 6.00)):
        dd = C.load(s, CACHE, PFX)
        ff = C.fs_of(dd)
        y = hp(dd["tq"][(dd["t"] >= t0) & (dd["t"] <= t1)], ff)
        sg = np.sign(y)
        pos = float(np.mean(sg > 0))
        # dwell lengths on each side
        runs, cur, sgn = [], 0, sg[0]
        for v in sg:
            if v == sgn:
                cur += 1
            else:
                runs.append((sgn, cur))
                sgn, cur = v, 1
        runs.append((sgn, cur))
        up = [n for s_, n in runs if s_ > 0]
        dn = [n for s_, n in runs if s_ < 0]
        dv = np.diff(y)
        print(f"    {lab:20s} n={len(y):4d} | frac>0 {pos:5.3f} | mean dwell +{np.mean(up):5.2f} "
              f"/ -{np.mean(dn):5.2f} samples (ratio {np.mean(up)/max(np.mean(dn),1e-9):5.2f}) | "
              f"skew(x) {skew(y):+6.2f} skew(dx) {skew(dv):+6.2f} | "
              f"max|d| {np.max(np.abs(dv)):6.0f}")

    print("\n  CALIBRATION (same metrics on synthetic signals at 7.4 Hz, fs=100.5):")
    t = np.arange(600) / 100.5
    for lab, sig in (("pure sine", np.sin(2 * np.pi * 7.4 * t)),
                     ("sawtooth (slow build/fast collapse)", 2 * ((7.4 * t) % 1.0) - 1),
                     ("hard-clipped sine (saturated)", np.clip(2.5 * np.sin(2 * np.pi * 7.4 * t),
                                                               -1, 1))):
        y = sig * 900
        sg = np.sign(y)
        runs, cur, sgn = [], 0, sg[0]
        for v in sg:
            if v == sgn:
                cur += 1
            else:
                runs.append((sgn, cur))
                sgn, cur = v, 1
        runs.append((sgn, cur))
        up = [n for s_, n in runs if s_ > 0]
        dn = [n for s_, n in runs if s_ < 0]
        dv = np.diff(y)
        print(f"    {lab:36s} frac>0 {np.mean(sg>0):5.3f} | dwell +{np.mean(up):5.2f}/"
              f"-{np.mean(dn):5.2f} (ratio {np.mean(up)/np.mean(dn):5.2f}) | "
              f"skew(x) {skew(y):+6.2f} skew(dx) {skew(dv):+6.2f}")


# ==============================================================================================
def q2_gating():
    print("\n" + "=" * 118)
    print("2. ENGAGED vs MANUAL, WITHIN ROUTE 37 segs 13/14 (within-build, within-route)")
    print("=" * 118)
    for lab, gears in (("all gears (drive+reverse+park)", None), ("DRIVE gear only", (2.0,))):
        print(f"\n  --- {lab} ---")
        res = {}
        for arm, want in (("ENGAGED", True), ("MANUAL", False)):
            def mk(d, want=want, gears=gears):
                lat = d["cc_lat"] > 0.5
                g = (np.isin(d["cs_gear"], list(gears)) if gears
                     else np.ones(len(d["t"]), bool))
                return (lat if want else ~lat) & g
            rs = L.collect(CACHE, PFX, [13, 14], mask_fn=mk)
            res[arm] = rs
            if not rs:
                print(f"    {arm:8s} nwin=0")
                continue
            eps = L.episodes(rs)
            pr = np.array([r["pr"] for r in rs])
            rms = np.array([r["rms_r"] for r in rs])
            pw = np.array([r["pow_r"] for r in rs])
            fr = np.array([r["fr"] for r in rs])
            hits = sum(1 for e in eps if np.nanmax([x["pr"] for x in e]) >= 10)
            print(f"    {arm:8s} nwin={len(rs):3d} nep={len(eps):2d} | f0 {np.nanmedian(fr):5.2f} "
                  f"sd {np.nanstd(fr):4.2f} | RMS {np.nanmedian(rms):7.1f} | "
                  f"power {np.nanmedian(pw):9.3g} | prom {np.nanmedian(pr):7.1f} | "
                  f"win>=10x {int((pr>=10).sum())}/{len(rs)} | ep>=10x {hits}/{len(eps)}")
        if res.get("ENGAGED") and res.get("MANUAL"):
            e, m = res["ENGAGED"], res["MANUAL"]
            pe = np.nanmedian([r["pow_r"] for r in e])
            pm = np.nanmedian([r["pow_r"] for r in m])
            re_ = np.nanmedian([r["rms_r"] for r in e])
            rm = np.nanmedian([r["rms_r"] for r in m])
            eh = sum(1 for x in L.episodes(e)
                     if np.nanmax([z["pr"] for z in x]) >= 10)
            mh = sum(1 for x in L.episodes(m)
                     if np.nanmax([z["pr"] for z in x]) >= 10)
            ne, nm_ = len(L.episodes(e)), len(L.episodes(m))
            odds, p = fisher_exact([[eh, ne - eh], [mh, nm_ - mh]])
            print(f"    RATIO eng/man: power {pe/max(pm,1e-30):8.1f}x   RMS "
                  f"{re_/max(rm,1e-9):6.1f}x")
            print(f"    Fisher on EPISODES {eh}/{ne} vs {mh}/{nm_}:  OR {odds:.1f}  p = {p:.3g}"
                  f"   {'(n too small to be decisive on its own)' if min(ne,nm_) < 6 else ''}")


# ==============================================================================================
def q3_outside():
    print("\n" + "=" * 118)
    print("3. IS ANYTHING AT THE INSTANTS OUTSIDE 6-12 AND 18-22 Hz?")
    print("=" * 118)
    print("  Free 5-45 Hz locate on the prominence spectrum; top 3 peaks per window; then the")
    print("  share of >4 Hz energy that falls OUTSIDE 6-12 U 18-22 Hz.\n")
    for s, t0, t1, lab in ((1, 9.0, 12.0, "INSTANT 1  seg1 t 9-12 (10:12:14-17)"),
                           (12, 17.0, 20.0, "INSTANT 2  seg12 t 17-20 (10:23:23-26)"),
                           (13, 0.0, 6.0, "REFERENCE seg13 parking ratchet t 0-6")):
        d = C.load(s, CACHE, PFX)
        fs = C.fs_of(d)
        m = (d["t"] >= t0) & (d["t"] <= t1)
        a = int(np.flatnonzero(m)[0])
        b = int(np.flatnonzero(m)[-1]) + 1
        f = np.fft.rfftfreq(NF, 1 / fs)
        print(f"  {lab}   fs={fs:.2f}")
        for i in range(0, b - a - NF + 1, 64):
            P = C.periodogram(d["tq"][a + i:a + i + NF], fs, NF)
            if P is None:
                continue
            R = L.prom_spectrum(f, P)
            cand = [(R[j], f[j]) for j in range(len(f))
                    if 5 <= f[j] <= 45 and np.isfinite(R[j])]
            cand.sort(reverse=True)
            # suppress neighbours within 1.5 Hz
            top = []
            for pv, fv in cand:
                if all(abs(fv - x[1]) > 1.5 for x in top):
                    top.append((pv, fv))
                if len(top) == 3:
                    break
            X = np.fft.rfft(d["tq"][a + i:a + i + NF] - np.mean(d["tq"][a + i:a + i + NF]))
            tot = float(np.sum(np.abs(X[f >= 4]) ** 2))
            ins = ((f >= 6) & (f < 12)) | ((f >= 18) & (f < 22))
            out = (f >= 4) & ~ins
            print(f"    t={d['t'][a+i]:6.2f} | " +
                  "  ".join(f"{fv:5.2f}Hz p{pv:7.1f}" for pv, fv in top) +
                  f"  | outside 6-12U18-22: {100*float(np.sum(np.abs(X[out])**2))/max(tot,1e-30):5.1f}%")
        print()


if __name__ == "__main__":
    q1_waveform()
    q2_gating()
    q3_outside()
