#!/usr/bin/env python3
"""PART 2 of the V86 frequency test: the falsifier's health, and whether the LEVER WAS IN FORCE.

A  GATE  -- V86's own probe says whether `gp-0x6b70` (the estimator residual) is live and whether
            the aggregator gate is open.  This is the V64 trap ("the null is on the GATE").
B  HF POSITIVE CONTROL -- the alpha change is PREDICTED to cut estimator HF gain to 0.650x at
            20 Hz / 0.585x at 28 Hz.  If NOTHING moves anywhere, the verdict is AMBIGUOUS.
C  CALIBRATED INJECTION -- inject at the amplitude that reproduces the MEASURED prominence
            (a pure sine at the measured p99 envelope is far too easy) and re-run the whole
            verdict pipeline, ratio and all.
D  ROBUSTNESS -- second signal (`rate_c`), second NFFT (512), pre-reg band occupancy.
E  IMPLIED LOOP BOUND -- what a null at this precision forbids.
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
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_7791)
VBINS = V.VBINS
O2 = {}

BANDS = [("1-4", 1.0, 4.0), ("4-6", 4.0, 6.0), ("6.2-6.9 PREREG", 6.2, 6.9),
         ("7.4-8.4 LINE", 7.4, 8.4), ("9-12", 9.0, 12.0), ("12-18", 12.0, 18.0),
         ("18-22", 18.0, 22.0), ("22-31", 22.0, 31.0), ("32-38", 32.0, 38.0),
         ("38-48", 38.0, 48.0)]


def band_pow(r, lo, hi):
    m = (r["f"] >= lo) & (r["f"] <= hi)
    return float(np.sum(r["P"][m]))


def ema_mag(alpha, f, T=1e-3):
    """|H(f)| of y += alpha*(x-y) at rate 1/T.  H(z) = alpha / (1 - (1-alpha) z^-1)."""
    z = np.exp(-2j * np.pi * f * T)
    return np.abs(alpha / (1.0 - (1.0 - alpha) * z))


def strat_ratio(A, B, key, nboot=4000):
    """Speed-stratified ratio of medians of r[key], block-bootstrapped in both arms."""
    def grp(rs):
        g = {}
        for r in rs:
            if np.isfinite(r[key]):
                g.setdefault(r["blk"], []).append(r)
        return g

    gA, gB = grp(A), grp(B)
    kA, kB = list(gA), list(gB)
    flatA = [r for k in kA for r in gA[k]]
    flatB = [r for k in kB for r in gB[k]]
    cA = np.array([sum(1 for r in flatA if lo <= r["v"] < hi) for lo, hi in VBINS], float)
    cB = np.array([sum(1 for r in flatB if lo <= r["v"] < hi) for lo, hi in VBINS], float)
    w = np.where((cA > 0) & (cB > 0), np.minimum(cA, cB), 0.0)

    def sm(rs):
        n = d = 0.0
        for i, (lo, hi) in enumerate(VBINS):
            m = [r[key] for r in rs if lo <= r["v"] < hi]
            if m and w[i]:
                n += w[i] * np.median(m); d += w[i]
        return n / d if d else np.nan

    pa, pb = sm(flatA), sm(flatB)
    dr = []
    for _ in range(nboot):
        ra = [r for i in RNG.integers(0, len(kA), len(kA)) for r in gA[kA[i]]]
        rb = [r for i in RNG.integers(0, len(kB), len(kB)) for r in gB[kB[i]]]
        a, b = sm(ra), sm(rb)
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            dr.append(a / b)
    dr = np.array(dr)
    return dict(a=pa, b=pb, ratio=pa / pb if pb else np.nan,
                lo=float(np.percentile(dr, 2.5)), hi=float(np.percentile(dr, 97.5)))


def main():
    E, M = {}, {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True)))
        M[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=False)))

    # =========================================================================================
    V.hdr("A  WAS THE LEVER IN FORCE?  V86's own probe on `0x14A` byte 4, ENGAGED, v in [0.5,5).\n"
          "   b7 = gp-0x6b70 < 0 . b6 = gp-0x6b70 != 0 . b5 = |gp-0x6b70| >= 512 .\n"
          "   b4 = gp-0x67ab < 2 (THE AGGREGATOR GATE) . b3 = fingerprint\n"
          "   `gp-0x6b70` is the residual FUN_00038148 builds FROM the estimator `0xC40D4` tunes.")
    O2["gate"] = {}
    for nm, (cache, pfx, segs) in (("V86/r6f", V.ROUTES["V86/r6f"]),
                                   ("V86B/r70", V.ROUTES["V86B/r70"])):
        tot = dict(n=0, b7=0.0, b6=0.0, b5=0.0, b4=0.0, b3=0.0)
        for s in segs:
            p = ROOT / cache / ("%s%d.npz" % (pfx, s))
            if not p.exists():
                continue
            d = C31.load(s, ROOT / cache, pfx)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            v = np.asarray(d["cs_v"], float)
            k = lat & (v >= V.VLO) & (v < V.VHI)
            if not k.any():
                continue
            q = np.asarray(d["probe"], float).astype(int)[k]
            tot["n"] += int(k.sum())
            for nmb, bit in (("b7", 0x80), ("b6", 0x40), ("b5", 0x20), ("b4", 0x10), ("b3", 0x08)):
                tot[nmb] += float(np.sum((q & bit) != 0))
        if tot["n"]:
            print("   %-10s n=%6d frames   b7 %.4f  b6 %.4f  b5 %.4f  b4 %.4f  b3 %.4f"
                  % (nm, tot["n"], tot["b7"] / tot["n"], tot["b6"] / tot["n"],
                     tot["b5"] / tot["n"], tot["b4"] / tot["n"], tot["b3"] / tot["n"]))
            O2["gate"][nm] = {k2: (tot[k2] / tot["n"] if k2 != "n" else tot["n"])
                              for k2 in tot}
    print("\n   READ: b6 ~ 1 => the residual is NON-ZERO essentially always; b5 => it is LARGE;\n"
          "         b4 = 1 => the aggregator gate is OPEN 100% of the time.  Contrast V64, where\n"
          "         the detector NEVER armed and the cal edits were never in force.")

    # =========================================================================================
    V.hdr("B  HF POSITIVE CONTROL.  The EMA `0xC40D4` 573->286 is alpha 0.1399 -> 0.0698 at 1 kHz.\n"
          "   |H(f)| = alpha / |1 - (1-alpha) e^-j2pi f T|.  Its HF-gain prediction is CHECKABLE.")
    a1, a0 = 573 / 4096.0, 286 / 4096.0
    print("   alpha(573) = %.6f   alpha(286) = %.6f" % (a1, a0))
    print("   %8s %10s %10s %8s" % ("f (Hz)", "|H| a=573", "|H| a=286", "ratio"))
    O2["ema"] = []
    for f in (0.0, 1.0, 5.0, 7.79, 8.0, 12.0, 20.0, 28.0, 40.0):
        h1, h0 = ema_mag(a1, f), ema_mag(a0, f)
        print("   %8.2f %10.6f %10.6f %8.4f" % (f, h1, h0, h0 / h1))
        O2["ema"].append([f, float(h1), float(h0), float(h0 / h1)])
    tau1 = -1e-3 / np.log(1 - a1)
    tau0 = -1e-3 / np.log(1 - a0)
    ph1 = np.degrees(np.arctan(2 * np.pi * 8.0 * tau1))
    ph0 = np.degrees(np.arctan(2 * np.pi * 8.0 * tau0))
    print("   tau: %.3f ms -> %.3f ms   phase lag at 8 Hz: %.2f deg -> %.2f deg  "
          "(ADDED LAG %.2f deg)" % (1e3 * tau1, 1e3 * tau0, ph1, ph0, ph0 - ph1))
    O2["tau_ms"] = [1e3 * tau1, 1e3 * tau0]
    O2["added_lag_deg_at_8Hz"] = float(ph0 - ph1)

    print("\n   BAND-BY-BAND, speed-matched engaged, ratio of median band power.  Does the lever\n"
          "   move ANYTHING?  V86/V85 isolates alpha; V86B/V85 isolates FactorC (alpha unchanged).")
    for nm in E:
        for r in E[nm]:
            for lab, lo, hi in BANDS:
                r["bp_" + lab] = band_pow(r, lo, hi)
    print("   %16s | %26s | %26s" % ("band (Hz)", "V86/V85  (alpha lever)",
                                     "V86B/V85 (FactorC lever)"))
    O2["bands"] = {}
    for lab, lo, hi in BANDS:
        r1 = strat_ratio(E["V86/r6f"], E["V85/r6e"], "bp_" + lab)
        r2 = strat_ratio(E["V86B/r70"], E["V85/r6e"], "bp_" + lab)
        print("   %16s | %8.3f [%7.3f,%7.3f] | %8.3f [%7.3f,%7.3f]"
              % (lab, r1["ratio"], r1["lo"], r1["hi"], r2["ratio"], r2["lo"], r2["hi"]))
        O2["bands"][lab] = dict(V86_V85=r1, V86B_V85=r2)

    # =========================================================================================
    V.hdr("C  CALIBRATED INJECTION.  A pure sine at the measured p99 ENVELOPE (770 ct) reads\n"
          "   prominence ~970, but the REAL line's prominence is ~30-39.  So calibrate the\n"
          "   injected amplitude to reproduce the MEASURED prominence, then run the WHOLE\n"
          "   verdict pipeline -- f_c, block CI and the stratified ratio against real 6e.")
    rs6f = E["V86/r6f"]
    f_meas = 7.999
    prom_target = 38.9                       # 6f's own measured line prominence
    f_V85 = 8.006
    f_pred = f_V85 * 0.843

    def inject(rs, ftgt, amp, notch_at=f_meas, jitter=0.15, rng=None):
        rng = rng or RNG
        out = []
        for r in rs:
            x = np.asarray(r["x"], float)
            bs = butter(2, [max(notch_at - 0.6, 0.4), notch_at + 0.6], btype="bandstop", fs=r["fs"])
            x = filtfilt(*bs, x)
            tt = np.arange(len(x)) / r["fs"]
            fi = ftgt * (1.0 + jitter * (rng.random() - 0.5))
            x = x + amp * np.sin(2 * np.pi * fi * tt + 2 * np.pi * rng.random())
            q = dict(x=x, fs=r["fs"], v=r["v"], blk=r["blk"], ep=r["ep"], t0=r["t0"])
            V.spectra([q])
            out.append(q)
        return out

    print("   calibrating injection amplitude to prominence %.1f ..." % prom_target)
    cal = None
    print("   %8s %10s %10s" % ("amp ct", "med prom", "hit rate"))
    for amp in (770.4, 385.2, 192.6, 120.0, 80.0, 55.0, 40.0, 30.0, 20.0):
        q = inject(rs6f, f_pred, amp)
        pm = float(np.nanmedian([r["p_free"] for r in q]))
        hr = float(np.mean([abs(r["f_free"] - f_pred) <= 0.4 for r in q]))
        print("   %8.1f %10.2f %9.1f%%" % (amp, pm, 100 * hr))
        O2.setdefault("cal", []).append([amp, pm, hr])
        if cal is None and pm <= prom_target:
            cal = amp
    cal = cal or 55.0
    print("   -> calibrated amplitude ~%.0f ct reproduces the measured prominence." % cal)

    print("\n   FULL PIPELINE on injected data (line moved to %.3f Hz at the MEASURED strength):"
          % f_pred)
    O2["injected_pipeline"] = {}
    for tag, ftgt, amp in (("MOVED to 0.843x, calibrated", f_pred, cal),
                           ("MOVED to 0.843x, 2x strength", f_pred, 2 * cal),
                           ("MOVED to 6.55 (pre-reg mid)", 6.55, cal),
                           ("NOT MOVED (control)", f_V85, cal)):
        q = inject(rs6f, ftgt, amp)
        fc = V.block_boot([r["f_free"] for r in q], [r["blk"] for r in q])
        rr = V.strat_block_boot_ratio(q, E["V85/r6e"], key="f_free")
        print("   %-30s f_c %6.3f [%5.3f,%5.3f]   ratio vs real 6e %6.3f [%5.3f,%5.3f]  "
              "excl 1.00: %s" % (tag, fc[0], fc[1], fc[2], rr["ratio"], rr["lo"], rr["hi"],
                                 "YES" if rr["hi"] < 1.0 or rr["lo"] > 1.0 else "no"))
        O2["injected_pipeline"][tag] = dict(f_c=list(fc), ratio=rr, amp=amp, f_target=ftgt)

    # =========================================================================================
    V.hdr("D  ROBUSTNESS -- second signal, second NFFT, and pre-reg band occupancy")
    print("   D1  SECOND SIGNAL: `rate_c` (column angle rate).  The ratchet is on record as being\n"
          "       in the BAR *and* in the ANGLE RATE.")
    O2["rate_c"] = {}
    Er = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        c, p, s = V.ROUTES[nm]
        Er[nm] = V.in_speed(V.spectra(V.windows(nm, c, p, s, engaged=True, sig="rate_c")))
        fc = V.block_boot([r["f_free"] for r in Er[nm]], [r["blk"] for r in Er[nm]])
        print("       %-10s n=%3d/%2dblk  f_c %7.3f [%6.3f,%6.3f]"
              % (nm, fc[3], fc[4], fc[0], fc[1], fc[2]))
        O2["rate_c"][nm] = list(fc)
    rr = V.strat_block_boot_ratio(Er["V86/r6f"], Er["V85/r6e"], key="f_free")
    print("       ratio V86/V85 on `rate_c` = %.3f [%.3f,%.3f]" % (rr["ratio"], rr["lo"], rr["hi"]))
    O2["rate_c"]["ratio"] = rr

    print("\n   D2  SECOND NFFT: 512 (5.07 s windows, 0.197 Hz bins) -- ~2x the windows.")
    O2["nfft512"] = {}
    E5 = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        c, p, s = V.ROUTES[nm]
        w = V.windows(nm, c, p, s, engaged=True, nw=512, hopw=256)
        for r in w:                       # 10.13 s blocks regardless of NFFT
            r["blk"] = "%d:%d" % (r["seg"], int(r["t0"] / 10.13))
        E5[nm] = V.in_speed(V.spectra(w, nw=512))
        fc = V.block_boot([r["f_free"] for r in E5[nm]], [r["blk"] for r in E5[nm]])
        print("       %-10s n=%3d/%2dblk  f_c %7.3f [%6.3f,%6.3f]"
              % (nm, fc[3], fc[4], fc[0], fc[1], fc[2]))
        O2["nfft512"][nm] = list(fc)
    rr = V.strat_block_boot_ratio(E5["V86/r6f"], E5["V85/r6e"], key="f_free")
    print("       ratio V86/V85 at NFFT 512 = %.3f [%.3f,%.3f]" % (rr["ratio"], rr["lo"], rr["hi"]))
    O2["nfft512"]["ratio"] = rr

    print("\n   D3  PRE-REG BAND OCCUPANCY: where does the 5-12 Hz prominence MASS sit?")
    print("       %-10s %14s %14s %14s %10s" % ("build", "mass 6.2-6.9", "mass 7.4-8.4",
                                                "mass 5-12", "6.2-6.9 %"))
    O2["mass"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        m1 = m2 = m3 = 0.0
        for r in E[nm]:
            w1 = np.clip(r["R"] - 1.0, 0, None)
            f = r["f"]
            m1 += float(np.nansum(w1[(f >= 6.2) & (f <= 6.9)]))
            m2 += float(np.nansum(w1[(f >= 7.4) & (f <= 8.4)]))
            m3 += float(np.nansum(w1[(f >= 5.0) & (f <= 12.0)]))
        print("       %-10s %14.1f %14.1f %14.1f %9.2f%%" % (nm, m1, m2, m3, 100 * m1 / m3))
        O2["mass"][nm] = dict(preg=m1, line=m2, all=m3, frac=m1 / m3)

    # =========================================================================================
    V.hdr("E  WHAT THE NULL FORBIDS.  Added lag at 8 Hz is %.2f deg [EVIDENCE: exact EMA algebra].\n"
          "   If a linear loop's -180 crossing sets the frequency, that lag MUST move it, by\n"
          "   df = -dphi / (dphi/df).  The measured |df/f| bound therefore bounds the loop's own\n"
          "   phase slope from below." % O2["added_lag_deg_at_8Hz"])
    ratio_hi = 1.060
    f0 = 8.006
    df_max = abs(ratio_hi - 1.0) * f0
    dphi = O2["added_lag_deg_at_8Hz"]
    slope_min = dphi / df_max
    td_min = slope_min / 360.0
    print("   measured ratio CI upper bound %.3f  =>  |df| <= %.3f Hz at f0 = %.3f Hz"
          % (ratio_hi, df_max, f0))
    print("   => loop phase slope |dphi/df| >= %.1f deg/Hz at 8 Hz" % slope_min)
    print("   => as a PURE DELAY that is T_d >= %.1f ms" % (1e3 * td_min))
    for Q in (2, 5, 10, 20, 40):
        # 2nd-order: phase slope at resonance = -2Q/f_n rad per (rad/s)/... -> deg/Hz below
        sl = 2 * Q / f0 * 180 / np.pi / 1.0 * (1 / 1.0)
        sl = (2 * Q / f0) * (180 / np.pi)
        print("       a 2nd-order mode of Q=%2d at %.1f Hz has slope %.1f deg/Hz" % (Q, f0, sl))
    O2["bound"] = dict(df_max=df_max, dphi=dphi, slope_min_deg_per_Hz=slope_min,
                       td_min_ms=1e3 * td_min)

    (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part2.json").write_text(
        json.dumps(O2, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part2.json"))


if __name__ == "__main__":
    main()
