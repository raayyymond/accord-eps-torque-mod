#!/usr/bin/env python3
"""A4, done properly: can Lomb-Scargle separate 42.8 Hz from 57.1 Hz for a BURST, not a tone?

The first pass validated LS on a pure 3 s sinusoid at the real 0x18F arrival times and it PASSED
(41.64 -> 41.65, 58.86 -> 58.85; arrival jitter is 5.6% of the period, enough to break the fold for
a steady tone). But on the real data LS reported BOTH candidates with near-equal power --
42.80 Hz at 55.0x and 57.10 Hz at 48.5x, and 42.80 + 57.10 = 99.90 ~ fs. A tone validation is
therefore the WRONG validation: grind #2 is a 0.085 s burst, its spectrum is intrinsically ~12 Hz
wide, and that width swamps the jitter-induced asymmetry LS relies on.

So the validation is redone with a synthetic signal that has the REAL burst's amplitude envelope,
injected at each candidate frequency in turn, and the discriminant

    R = P_LS(f_low) / P_LS(f_high)

is measured for each. If R separates the two injections, the method works and R on the real data
picks the answer. If it does not, LS is dropped -- as pre-registered.

Usage:  python studies/grind2/analyze_grind2_alias_ls.py
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

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load  # noqa: E402
from analyze_grind2_alias import lombscargle, native_18f  # noqa: E402

OUTJSON = HERE / "_scratch/out/_grind2_alias_ls.json"
RNG = np.random.default_rng(20260801)
WINDOWS = [("V65/r3a", 3, 36.0, 40.0), ("V65/r3a", 4, 15.0, 18.0),
           ("V62/r37", 1, 9.5, 12.0), ("V65/r3b", 2, 1.0, 3.5)]
QUIET = [("V65/r3a", 3, 46.0, 50.0), ("V62/r37", 1, 30.0, 32.5)]
FREQS = np.arange(20.0, 95.0, 0.05)


def env_of(t, x, lo, hi):
    """Analytic envelope of (t,x) in [lo,hi], on a uniform resample, mapped back to t."""
    fs = 1.0 / np.median(np.diff(t))
    tu = np.arange(t[0], t[-1], 1 / fs)
    xu = np.interp(tu, t, x) - np.mean(x)
    X = np.fft.rfft(xu)
    f = np.fft.rfftfreq(len(xu), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    e = np.abs(np.fft.irfft(H, n=len(xu)))
    return np.interp(t, tu, e)


def peak_near(freqs, P, f0, halfw=1.5):
    m = np.abs(freqs - f0) <= halfw
    return float(P[m].max()) if m.any() else np.nan


def main():
    out = {"windows": []}
    G.hdr("A4 (redone).  LOMB-SCARGLE DISCRIMINANT for a BURST, at the true 0x18F arrival times.\n"
          "Discriminant R = P_LS(f_low) / P_LS(f_high), f_low + f_high = fs. R >> 1 favours the\n"
          "sub-Nyquist reading; R << 1 favours the first fold.")
    rows = []
    for build, s, a, b in WINDOWS + QUIET:
        B = G.BUILDS[build]
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        t18, x18 = native_18f(d)
        m = (t18 >= a) & (t18 < b)
        if m.sum() < 150:
            continue
        tt, xx = t18[m], x18[m].astype(float)
        # locate the observed peak, then its fold partner
        P = lombscargle(tt, xx - xx.mean(), FREQS)
        sub = (FREQS >= 38) & (FREQS <= 49.5)
        flo = float(FREQS[np.argmax(np.where(sub, P, -np.inf))])
        fhi = fs - flo
        env = env_of(tt, xx, 38.0, 49.5)
        quiet = (build, s, a, b) in QUIET

        # --- validation: inject the REAL envelope at each candidate, same timestamps -----------
        Rs = {}
        for nm, f0 in (("low", flo), ("high", fhi)):
            syn = env * np.sin(2 * np.pi * f0 * tt + RNG.uniform(0, 2 * np.pi))
            Ps = lombscargle(tt, syn - syn.mean(), FREQS)
            Rs[nm] = peak_near(FREQS, Ps, flo) / max(peak_near(FREQS, Ps, fhi), 1e-30)
        Rreal = peak_near(FREQS, P, flo) / max(peak_near(FREQS, P, fhi), 1e-30)
        sep = Rs["low"] / max(Rs["high"], 1e-30)
        rows.append(dict(build=build, seg=s, t0=a, t1=b, quiet=quiet, fs=fs, flo=flo, fhi=fhi,
                         R_inj_low=Rs["low"], R_inj_high=Rs["high"], R_real=Rreal, sep=sep))
        print(f"\n  {build} seg{s} t {a:.1f}-{b:.1f} s  {'(QUIET control)' if quiet else '(BURST)'}"
              f"  n={m.sum()}  fs={fs:.3f}")
        print(f"    candidate pair: {flo:.2f} Hz  vs  {fhi:.2f} Hz")
        print(f"    injected at {flo:.2f}: R = {Rs['low']:9.3f}    "
              f"injected at {fhi:.2f}: R = {Rs['high']:9.3f}    "
              f"separation {sep:8.2f}x")
        print(f"    REAL DATA:  R = {Rreal:9.3f}   -> "
              f"{'closer to the LOW injection' if abs(np.log(max(Rreal,1e-30)) - np.log(max(Rs['low'],1e-30))) < abs(np.log(max(Rreal,1e-30)) - np.log(max(Rs['high'],1e-30))) else 'closer to the HIGH injection'}")
    out["windows"] = rows

    G.hdr("VERDICT ON A4")
    bs = [r for r in rows if not r["quiet"]]
    seps = np.array([r["sep"] for r in bs])
    print(f"  Injection separation across the {len(bs)} burst windows: "
          f"{seps.min():.2f}x .. {seps.max():.2f}x (median {np.median(seps):.2f}x)")
    works = np.median(seps) > 3.0
    if not works:
        print("  🛑 THE DISCRIMINANT DOES NOT SEPARATE THE TWO INJECTIONS. Injecting a known")
        print("  41.6 Hz burst and a known 58.9 Hz burst at the SAME real timestamps produces")
        print("  nearly the same Lomb-Scargle discriminant, because a 0.085 s burst is ~12 Hz wide")
        print("  and that width swamps the jitter asymmetry LS depends on. The earlier PURE-TONE")
        print("  validation passed only because a 3 s tone is spectrally narrow -- it was the")
        print("  wrong validation for this signal.")
        print("  ⇒ A4 IS DROPPED, exactly as pre-registered. No frequency conclusion rests on it.")
    else:
        agree = [r for r in bs
                 if abs(np.log(r["R_real"]) - np.log(r["R_inj_low"])) <
                 abs(np.log(r["R_real"]) - np.log(r["R_inj_high"]))]
        print(f"  The discriminant works. {len(agree)}/{len(bs)} burst windows favour the LOW "
              f"(sub-Nyquist) reading.")
    out["verdict"] = "works" if works else "dropped"
    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
