#!/usr/bin/env python3
"""PART 5 -- the 18-27 Hz mode.  The full-band scan says V85's ~21 Hz line sits at ~23.8 Hz on
V86.  That is a frequency MOVE, in a band the pre-registration did not name, in the WRONG
DIRECTION (up, not down).  Before it is reported it needs the same discipline as the primary:
speed matching, a block CI, the V86B control (alpha UNCHANGED), and an engaged/manual arm.

🛑 This is EXPLORATORY.  It was not pre-registered.  It is reported as a candidate, not a result.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
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
import _grind2_lib as G             # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_7794)
O5 = {}
HFLO, HFHI = 18.0, 27.0


def add_hf(recs):
    for r in recs:
        f, R = r["f"], r["R"]
        m = (f >= HFLO) & (f <= HFHI) & np.isfinite(R)
        r["f_hf"] = float(f[np.argmax(np.where(m, R, -np.inf))]) if m.any() else np.nan
        r["p_hf"] = float(np.nanmax(np.where(m, R, np.nan))) if m.any() else np.nan
        w = np.clip(R[m] - 1.0, 0.0, None)
        r["c_hf"] = float(np.sum(f[m] * w) / np.sum(w)) if np.sum(w) > 0 else np.nan
        r["a21"] = V.band_amp(r, 21.0, 1.5)
        r["a24"] = V.band_amp(r, 23.8, 1.5)
    return recs


def main():
    E, M = {}, {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = add_hf(V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True))))
        M[name] = add_hf(V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=False))))

    V.hdr("R1  THE 18-27 Hz MODE -- free argmax, speed-matched engaged, block CI.\n"
          "    On record the engaged-only vibration is 21.09 Hz.  EXPLORATORY, not pre-registered.")
    print("    %-10s %4s %4s | %26s | %24s | %22s"
          % ("build", "n", "blk", "argmax 18-27 Hz", "centroid 18-27", "prominence"))
    O5["hf"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        rs = E[nm]
        fc = V.block_boot([r["f_hf"] for r in rs], [r["blk"] for r in rs])
        ct = V.block_boot([r["c_hf"] for r in rs], [r["blk"] for r in rs])
        pr = V.block_boot([r["p_hf"] for r in rs], [r["blk"] for r in rs])
        print("    %-10s %4d %4d | %8.3f [%7.3f,%7.3f] | %7.3f [%6.3f,%6.3f] | %6.2f [%5.2f,%5.2f]"
              % (nm, fc[3], fc[4], fc[0], fc[1], fc[2], ct[0], ct[1], ct[2], pr[0], pr[1], pr[2]))
        O5["hf"][nm] = dict(argmax=list(fc), centroid=list(ct), prom=list(pr))

    print("\n    RATIOS, speed-stratified, both arms block-bootstrapped:")
    for A, B in (("V86/r6f", "V85/r6e"), ("V86B/r70", "V85/r6e"), ("V86/r6f", "V86B/r70")):
        for key, tag in (("f_hf", "argmax"), ("c_hf", "centroid")):
            r = V.strat_block_boot_ratio(E[A], E[B], key=key)
            ex = "YES" if (r["hi"] < 1.0 or r["lo"] > 1.0) else "no"
            print("      %-9s/%-9s %-9s %6.3f [%6.3f,%6.3f]  fA %6.2f fB %6.2f  excl 1.00: %s"
                  % (A.split("/")[0], B.split("/")[0], tag, r["ratio"], r["lo"], r["hi"],
                     r["fA"], r["fB"], ex))
            O5.setdefault("hf_ratio", {})["%s|%s|%s" % (A, B, key)] = r

    V.hdr("R2  IS IT THE SAME MODE, MOVED?  Amplitude in 21+-1.5 Hz vs 23.8+-1.5 Hz.\n"
          "    A MOVE trades one for the other; a DEATH kills 21 without filling 23.8.")
    print("    %-10s | %24s | %24s | %10s" % ("build", "p99 env 21+-1.5 Hz",
                                              "p99 env 23.8+-1.5 Hz", "24/21"))
    O5["amp"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        rs = E[nm]
        u = [r["blk"] for r in rs]
        a1 = V.block_boot([r["a21"] for r in rs], u)
        a2 = V.block_boot([r["a24"] for r in rs], u)
        print("    %-10s | %8.1f [%6.1f,%6.1f] | %8.1f [%6.1f,%6.1f] | %10.3f"
              % (nm, a1[0], a1[1], a1[2], a2[0], a2[1], a2[2], a2[0] / a1[0]))
        O5["amp"][nm] = dict(a21=list(a1), a24=list(a2), ratio=a2[0] / a1[0])
    for A, B in (("V86/r6f", "V85/r6e"), ("V86B/r70", "V85/r6e")):
        for key in ("a21", "a24"):
            r = V.strat_block_boot_ratio(E[A], E[B], key=key)
            print("      %-9s/%-9s %s  %6.3f [%6.3f,%6.3f]"
                  % (A.split("/")[0], B.split("/")[0], key, r["ratio"], r["lo"], r["hi"]))
            O5.setdefault("amp_ratio", {})["%s|%s|%s" % (A, B, key)] = r

    V.hdr("R3  ENGAGED vs MANUAL within each route -- the 18-27 Hz mode is engaged-only on record")
    O5["eng_man"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        row = {}
        for arm, rs in (("eng", E[nm]), ("man", M[nm])):
            if len(rs) < 4:
                row[arm] = None
                continue
            u = [r["blk"] for r in rs]
            a1 = V.block_boot([r["a21"] for r in rs], u)
            a2 = V.block_boot([r["a24"] for r in rs], u)
            fc = V.block_boot([r["f_hf"] for r in rs], u)
            row[arm] = dict(a21=list(a1), a24=list(a2), f=list(fc), n=len(rs))
            print("    %-10s %-4s n=%3d  a21 %7.1f [%6.1f,%6.1f]  a23.8 %7.1f [%6.1f,%6.1f]  "
                  "argmax %6.2f" % (nm, arm, len(rs), a1[0], a1[1], a1[2],
                                    a2[0], a2[1], a2[2], fc[0]))
        if row.get("eng") and row.get("man"):
            print("    %-10s      ENG/MAN  a21 %6.2f   a23.8 %6.2f"
                  % ("", row["eng"]["a21"][0] / row["man"]["a21"][0],
                     row["eng"]["a24"][0] / row["man"]["a24"][0]))
        O5["eng_man"][nm] = row

    V.hdr("R4  MEAN SPECTRUM 16-32 Hz, speed-matched -- read the move directly")
    VB = V.VBINS
    cA = np.array([sum(1 for r in E["V86/r6f"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    cB = np.array([sum(1 for r in E["V85/r6e"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    c70 = np.array([sum(1 for r in E["V86B/r70"] if lo <= r["v"] < hi) for lo, hi in VB], float)
    w = np.minimum(cA, cB)
    f, S6f = V.matched_mean_spectrum(E["V86/r6f"], w, "R")
    _, S6e = V.matched_mean_spectrum(E["V85/r6e"], w, "R")
    _, S70 = V.matched_mean_spectrum(E["V86B/r70"], np.minimum(cA, c70), "R")
    print("    %6s %10s %10s %10s" % ("Hz", "V86/6f", "V85/6e", "V86B/70"))
    rows = []
    for j in np.flatnonzero((f >= 16.0) & (f <= 32.0)):
        if j % 2:
            continue
        print("    %6.2f %10.2f %10.2f %10.2f" % (f[j], S6f[j], S6e[j], S70[j]))
        rows.append([float(f[j]), float(S6f[j]), float(S6e[j]), float(S70[j])])
    O5["spectrum_16_32"] = rows

    (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part5.json").write_text(
        json.dumps(O5, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part5.json"))


if __name__ == "__main__":
    main()
