#!/usr/bin/env python3
"""PART 4 -- residuals the verdict must not leave open.

Q1  Sign-toggle rate with a CI (the alpha contrast in P2 was a bare point estimate).
Q2  Engaged-vs-manual on 6f with REVERSE GEAR EXCLUDED (30.2 s of 6f is in R, 100% manual,
    essentially all below 2 m/s -- the brief's `manual_*_FWD_s` constraint).
Q3  FULL-BAND scan 1-48 Hz: did the ratchet move somewhere the pre-registration did not look?
    A frequency lever that moved the line to 15 Hz would read as FALSIFIED on a 5-12 Hz search.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402
import _grind2_lib as G             # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_7793)
O4 = {}


def windows_gear(route, cache, pfx, segs, engaged, fwd_only=False):
    """V.windows plus a gear filter.  cs_gear: reverse is the value 6f spends 30.2 s in."""
    out = []
    for s in segs:
        p = ROOT / cache / ("%s%d.npz" % (pfx, s))
        if not p.exists():
            continue
        d = C31.load(s, ROOT / cache, pfx)
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        x = np.asarray(d["tq"], float)
        v = np.asarray(d["cs_v"], float)
        g = np.asarray(d["cs_gear"], float)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        mask = lat if engaged else ~lat
        if fwd_only:
            mask = mask & (g != REV)
        for a, b in C31.runs_of(mask, t, V.NW):
            for j0 in range(0, (b - a) - V.NW + 1, V.HOPW):
                sl = slice(j0, j0 + V.NW)
                seg = x[a:b][sl]
                if not np.all(np.isfinite(seg)):
                    continue
                out.append(dict(build=route, seg=int(s), t0=float(t[a:b][sl][0]),
                                blk="%d:%d:%d" % (s, a, j0 // (V.HOPW * 2)), ep="%d:%d" % (s, a),
                                v=float(np.median(v[a:b][sl])), fs=float(fs), x=seg,
                                gear=float(np.median(g[a:b][sl]))))
    return out


# find the reverse code from the gear histogram
def find_rev():
    d = C31.load(0, ROOT / "_scratch/cache/r6f", "r6fs")
    vals = {}
    for s in range(4):
        dd = C31.load(s, ROOT / "_scratch/cache/r6f", "r6fs")
        g = np.asarray(dd["cs_gear"], float)
        v = np.asarray(dd["cs_v"], float)
        for u in np.unique(g):
            vals.setdefault(float(u), [0, 0.0])
            vals[float(u)][0] += int(np.sum(g == u))
            vals[float(u)][1] = float(np.mean(v[g == u])) if np.any(g == u) else 0.0
    return vals


def main():
    global REV
    gh = find_rev()
    print("  6f `cs_gear` histogram (code: frames, mean speed):")
    for k in sorted(gh):
        print("     %6.1f : %6d frames, mean v %.2f m/s  (%.1f s)"
              % (k, gh[k][0], gh[k][1], gh[k][0] / 101.0))
    # reverse = 30.2 s per r6f_exposure.json -> pick the code whose duration matches
    exp = json.loads((ROOT / "_scratch/cache/r6f" / "r6f_exposure.json").read_text())
    target = exp["gear_s"]["reverse"]
    REV = min(gh, key=lambda k: abs(gh[k][0] / 101.0 - target))
    print("  -> reverse code = %.0f  (%.1f s vs exposure.json's %.1f s)"
          % (REV, gh[REV][0] / 101.0, target))
    O4["rev_code"] = float(REV)

    E = {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True)))

    # ---- Q1 toggle rate with a CI ------------------------------------------------------------
    V.hdr("Q1  SIGN-TOGGLE RATE of `gp-0x6b70` with a block CI.  A DIRECT 100 Hz observable of\n"
          "    the residual's own bandwidth.  alpha halved => slower estimator => the residual\n"
          "    should cross zero LESS often.  Routes 6f and 70 are both parking-lot.")
    O4["toggle"] = {}
    for nm in ("V86/r6f", "V86B/r70"):
        cache, pfx, segs = V.ROUTES[nm]
        rates, units = [], []
        for s in segs:
            p = ROOT / cache / ("%s%d.npz" % (pfx, s))
            if not p.exists():
                continue
            d = C31.load(s, ROOT / cache, pfx)
            t = np.asarray(d["t"], float)
            v = np.asarray(d["cs_v"], float)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            b7 = (np.asarray(d["probe"], float).astype(int) & 0x80) != 0
            k = lat & (v >= V.VLO) & (v < V.VHI)
            for a, b in C31.runs_of(k, t, 200):
                # split each run into ~5 s sub-blocks so the bootstrap has units
                n5 = int(5.0 * 101.0)
                for j in range(a, b - n5 + 1, n5):
                    sg = b7[j:j + n5].astype(int)
                    dur = t[j + n5 - 1] - t[j]
                    if dur > 1.0:
                        rates.append(np.sum(np.abs(np.diff(sg))) / dur)
                        units.append("%d:%d:%d" % (s, a, (j - a) // (2 * n5)))
        bb = V.block_boot(rates, units, stat=np.mean)
        print("    %-10s toggles/s = %6.3f [%6.3f,%6.3f]   n=%d sub-blocks / %d blocks"
              % (nm, bb[0], bb[1], bb[2], bb[3], bb[4]))
        O4["toggle"][nm] = dict(rate=list(bb), rates=rates, units=units)
    ra = np.array(O4["toggle"]["V86/r6f"]["rates"])
    rb = np.array(O4["toggle"]["V86B/r70"]["rates"])
    ua = O4["toggle"]["V86/r6f"]["units"]
    ub = O4["toggle"]["V86B/r70"]["units"]

    def bmean(vals, units, n=4000):
        g = {}
        for v2, u in zip(vals, units):
            g.setdefault(u, []).append(v2)
        ks = list(g)
        return np.array([np.mean(np.concatenate([g[ks[i]] for i in RNG.integers(0, len(ks),
                                                                                len(ks))]))
                         for _ in range(n)])
    da, db = bmean(ra, ua), bmean(rb, ub)
    rr = da / db
    print("    ratio V86/V86B = %.3f [%.3f,%.3f]   (alpha 286 vs 573; PREDICTED < 1)"
          % (np.mean(ra) / np.mean(rb), np.percentile(rr, 2.5), np.percentile(rr, 97.5)))
    O4["toggle"]["ratio"] = [float(np.mean(ra) / np.mean(rb)), float(np.percentile(rr, 2.5)),
                             float(np.percentile(rr, 97.5))]
    for k in ("V86/r6f", "V86B/r70"):
        O4["toggle"][k].pop("rates"); O4["toggle"][k].pop("units")

    # ---- Q2 engaged vs manual, reverse excluded ----------------------------------------------
    V.hdr("Q2  ENGAGED vs MANUAL on 6f, REVERSE EXCLUDED.  6f spends 30.2 s in R, 100% manual and\n"
          "    essentially all below 2 m/s, so an un-filtered manual arm is contaminated.")
    c, p, s = V.ROUTES["V86/r6f"]
    O4["eng_man_fwd"] = {}
    fc6f = 7.999
    for arm, en in (("engaged", True), ("manual FWD", False)):
        rs = V.in_speed(V.spectra(windows_gear("V86/r6f", c, p, s, en, fwd_only=not en)))
        if len(rs) < 4:
            print("    %-12s n=%d -- too few --" % (arm, len(rs)))
            continue
        for r in rs:
            r["a"] = V.band_amp(r, fc6f, 1.0)
        u = [r["blk"] for r in rs]
        fc = V.block_boot([r["f_free"] for r in rs], u)
        aa = V.block_boot([r["a"] for r in rs], u)
        pr = V.block_boot([r["p_free"] for r in rs], u)
        print("    %-12s n=%3d/%2dblk  f_c %6.3f [%5.3f,%5.3f]  amp@%.2fHz %7.1f [%6.1f,%6.1f]  "
              "prom %6.2f [%5.2f,%5.2f]"
              % (arm, len(rs), fc[4], fc[0], fc[1], fc[2], fc6f, aa[0], aa[1], aa[2],
                 pr[0], pr[1], pr[2]))
        O4["eng_man_fwd"][arm] = dict(f_c=list(fc), amp=list(aa), prom=list(pr), n=len(rs))
    if len(O4["eng_man_fwd"]) == 2:
        e, m = O4["eng_man_fwd"]["engaged"], O4["eng_man_fwd"]["manual FWD"]
        print("    ENG/MAN(FWD) amplitude ratio %.2f   prominence ratio %.2f"
              % (e["amp"][0] / m["amp"][0], e["prom"][0] / m["prom"][0]))
        O4["eng_man_fwd"]["amp_ratio"] = e["amp"][0] / m["amp"][0]

    # ---- Q3 full-band scan -------------------------------------------------------------------
    V.hdr("Q3  FULL-BAND 1-48 Hz.  Did the line move somewhere the 5-12 Hz search cannot see?\n"
          "    A frequency lever that pushed it to 3 Hz or 15 Hz would read FALSIFIED here too.")
    VB = V.VBINS
    cA = np.array([sum(1 for r in E["V86/r6f"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    cB = np.array([sum(1 for r in E["V85/r6e"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    w = np.minimum(cA, cB)
    f, S6f = V.matched_mean_spectrum(E["V86/r6f"], w, "R")
    _, S6e = V.matched_mean_spectrum(E["V85/r6e"], w, "R")
    m = (f >= 1.0) & (f <= 48.0)
    # peaks: local maxima of the mean prominence spectrum above 3
    print("    %-8s %10s %10s %10s   %s" % ("Hz", "V86/6f", "V85/6e", "V86-V85", "note"))
    peaks = []
    for j in np.flatnonzero(m):
        if j < 1 or j >= len(f) - 1:
            continue
        for S, nm in ((S6f, "V86"), (S6e, "V85")):
            if S[j] > 3.0 and S[j] >= S[j - 1] and S[j] >= S[j + 1]:
                peaks.append((float(f[j]), nm))
    seen = set()
    for fq, nm in sorted(peaks):
        key = round(fq, 1)
        if key in seen:
            continue
        seen.add(key)
        j = int(np.argmin(np.abs(f - fq)))
        note = ""
        if S6f[j] > 3 and S6e[j] > 3:
            note = "on BOTH"
        elif S6f[j] > 3:
            note = "<< V86 ONLY"
        else:
            note = ">> V85 ONLY"
        print("    %8.2f %10.2f %10.2f %10.2f   %s" % (f[j], S6f[j], S6e[j], S6f[j] - S6e[j], note))
        O4.setdefault("peaks", []).append([float(f[j]), float(S6f[j]), float(S6e[j]), note])
    for lo, hi, lab in ((1.0, 5.0, "1-5"), (5.0, 12.0, "5-12"), (12.0, 20.0, "12-20"),
                        (20.0, 32.0, "20-32"), (32.0, 48.0, "32-48")):
        k = (f >= lo) & (f <= hi)
        j6f = int(np.nanargmax(np.where(k, S6f, -np.inf)))
        j6e = int(np.nanargmax(np.where(k, S6e, -np.inf)))
        print("    band %-6s: V86 argmax %6.2f Hz (prom %6.2f)   V85 argmax %6.2f Hz (prom %6.2f)"
              % (lab, f[j6f], S6f[j6f], f[j6e], S6e[j6e]))
        O4.setdefault("band_argmax", {})[lab] = [float(f[j6f]), float(S6f[j6f]),
                                                 float(f[j6e]), float(S6e[j6e])]

    (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part4.json").write_text(
        json.dumps(O4, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part4.json"))


if __name__ == "__main__":
    main()
