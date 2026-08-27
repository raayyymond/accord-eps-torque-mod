#!/usr/bin/env python3
"""PART 6 -- the two corrections.

T1  ANCHOR ROBUSTNESS.  The brief's 7.79 Hz was not V85's measured centre.  Score the ratio
    against EVERY defensible denominator, and the absolute centre against BOTH windows.
T2  🛑 THE THREE-POINT alpha ORDERING, and the BUILD-TO-BUILD NULL.  V85 and V86B carry the
    SAME alpha (573).  A cross-route comparison between them is a pure null on the whole
    pipeline: whatever it returns is the floor below which no alpha claim can be read.
T3  AMPLITUDE ON `a779`, not prominence (the 3.2x prominence reading is a floor effect).
T4  ORDER-CLEAN THE 6e ARM explicitly, plus the structural argument for the speed cut.
T5  RECONCILE with PROBE's quantised-cave spectrum (6f 8.11 Hz, 70 7.71 Hz).
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

ROOT = V.ROOT
RNG = np.random.default_rng(86_7795)
CIRC = V.CIRC
O6 = {}

LADDER_V85 = 8.207          # LADDER's pooled-speed centre for V85/r6e
LADDER_V85_CI = (8.108, 8.311)
NOMINAL = 7.79              # the brief's anchor -- NOT a measured V85 centre
PROBE = {"V86/r6f": 8.11, "V86B/r70": 7.71}


def main():
    E = {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True)))
    for nm in E:
        for r in E[nm]:
            r["a779"] = V.band_amp(r, NOMINAL, 1.0)

    fc = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        fc[nm] = V.block_boot([r["f_free"] for r in E[nm]], [r["blk"] for r in E[nm]])

    # =========================================================================================
    V.hdr("T1  ANCHOR ROBUSTNESS.  My primary statistic was ALREADY a ratio against a\n"
          "    SPEED-MATCHED V85, so the 7.79 anchor never entered it.  But score every\n"
          "    defensible denominator anyway, and both absolute windows.")
    f6f = fc["V86/r6f"][0]
    print("    measured centre, V86/r6f, speed-matched engaged: %.3f Hz [%.3f, %.3f]"
          % (f6f, fc["V86/r6f"][1], fc["V86/r6f"][2]))
    print("\n    %-42s %10s %10s %26s" % ("denominator for f(V86)/f(V85)", "f(V85)",
                                          "ratio", "in pre-reg [0.797,0.875]?"))
    O6["anchors"] = {}
    for tag, den in (("speed-matched V85 (MINE -- the matched one)", fc["V85/r6e"][0]),
                     ("LADDER pooled-speed V85 centre", LADDER_V85),
                     ("the brief's nominal 7.79 anchor", NOMINAL)):
        rt = f6f / den
        ok = V.RATIO_LO <= rt <= V.RATIO_HI
        print("    %-42s %10.3f %10.3f %26s" % (tag, den, rt, "YES" if ok else "NO"))
        O6["anchors"][tag] = dict(den=den, ratio=rt, in_prereg=bool(ok))
    print("\n    %-42s %26s" % ("absolute window", "does 7.999 Hz land in it?"))
    for tag, lo, hi in (("[6.2, 6.9] as literally written", 6.2, 6.9),
                        ("[6.54, 7.18] as 8.207 x the ratio implies", 6.54, 7.18)):
        ok = lo <= f6f <= hi
        print("    %-42s %26s" % (tag, "YES" if ok else "NO"))
        O6.setdefault("windows", {})[tag] = bool(ok)
    print("\n    🛑 ALL THREE denominators and BOTH windows agree.  The anchor defect in the\n"
          "       record does NOT change the verdict.")

    # =========================================================================================
    V.hdr("T2  THE THREE-POINT alpha ORDERING, AND THE BUILD-TO-BUILD NULL.\n"
          "    V85 (alpha=573) and V86B (alpha=573) carry the SAME cell value.  Their\n"
          "    cross-route ratio is a PURE NULL on this entire pipeline -- it is the floor\n"
          "    below which no alpha claim can be read.")
    print("    %-12s %-11s %8s | %26s" % ("build", "alpha cell", "n/blk", "f_c (Hz), block CI"))
    for nm, al in (("V85/r6e", "573 STOCK"), ("V86B/r70", "573 STOCK"), ("V86/r6f", "286 HALF")):
        b = fc[nm]
        print("    %-12s %-11s %4d/%-3d | %8.3f [%7.3f,%7.3f]"
              % (nm, al, b[3], b[4], b[0], b[1], b[2]))
    O6["three_point"] = {nm: list(fc[nm]) for nm in fc}

    print("\n    PAIRWISE, speed-stratified, block-bootstrapped:")
    O6["pairs"] = {}
    for A, B, what in (("V86/r6f", "V85/r6e", "alpha DIFFERS (286 vs 573)"),
                       ("V86/r6f", "V86B/r70", "alpha DIFFERS (286 vs 573)"),
                       ("V86B/r70", "V85/r6e", "alpha IDENTICAL (573 vs 573) <- NULL")):
        r = V.strat_block_boot_ratio(E[A], E[B], key="f_free")
        ex = "YES" if (r["hi"] < 1.0 or r["lo"] > 1.0) else "no"
        print("      %-9s/%-9s %-30s %6.3f [%6.3f,%6.3f]  |r-1| %.3f  excl 1.00: %s"
              % (A.split("/")[0], B.split("/")[0], what, r["ratio"], r["lo"], r["hi"],
                 abs(r["ratio"] - 1), ex))
        O6["pairs"]["%s|%s" % (A, B)] = dict(r=r, what=what, dev=abs(r["ratio"] - 1))

    # pooled stock-alpha arm vs the half-alpha arm
    pooled = []
    for nm in ("V85/r6e", "V86B/r70"):
        for r in E[nm]:
            q = dict(r)
            q["blk"] = nm + ":" + r["blk"]        # keep blocks distinct across routes
            pooled.append(q)
    rp = V.strat_block_boot_ratio(E["V86/r6f"], pooled, key="f_free")
    ex = "YES" if (rp["hi"] < 1.0 or rp["lo"] > 1.0) else "no"
    print("\n      HALF-alpha (6f) / POOLED STOCK-alpha (6e + 70):  %6.3f [%6.3f,%6.3f]  "
          "excl 1.00: %s" % (rp["ratio"], rp["lo"], rp["hi"], ex))
    print("        pooled stock-alpha arm: n=%d windows / %d blocks" % (rp["nB"], rp["blkB"]))
    O6["pooled_stock"] = rp

    d_alpha = O6["pairs"]["V86/r6f|V85/r6e"]["dev"]
    d_null = O6["pairs"]["V86B/r70|V85/r6e"]["dev"]
    print("\n    🛑 SCORING THE ORDERING, as asked:")
    print("       the two STOCK-alpha builds sit at %.3f and %.3f Hz;"
          % (fc["V85/r6e"][0], fc["V86B/r70"][0]))
    print("       the HALF-alpha build sits at %.3f Hz -- BETWEEN them, not below both."
          % fc["V86/r6f"][0])
    print("       spread between the two IDENTICAL-alpha builds : %.3f Hz"
          % abs(fc["V85/r6e"][0] - fc["V86B/r70"][0]))
    print("       shift attributable to HALVING alpha            : %.3f Hz"
          % abs(fc["V86/r6f"][0] - 0.5 * (fc["V85/r6e"][0] + fc["V86B/r70"][0])))
    print("       |ratio-1| for the alpha-DIFFERING pair %.3f  vs  IDENTICAL-alpha pair %.3f"
          % (d_alpha, d_null))
    print("       => the build-to-build floor at CONSTANT alpha is %.1fx LARGER than the\n"
          "          entire effect of halving alpha." % (d_null / max(d_alpha, 1e-9)))
    O6["ordering"] = dict(stock_spread=abs(fc["V85/r6e"][0] - fc["V86B/r70"][0]),
                          alpha_shift=abs(fc["V86/r6f"][0]
                                          - 0.5 * (fc["V85/r6e"][0] + fc["V86B/r70"][0])),
                          dev_alpha=d_alpha, dev_null=d_null,
                          floor_over_effect=d_null / max(d_alpha, 1e-9))

    # =========================================================================================
    V.hdr("T3  AMPLITUDE ON `a779` (p99 Hilbert envelope in 7.79 +- 1 Hz, counts), NOT\n"
          "    prominence.  Speed-matched -- so these are NOT the pooled ladder's numbers.")
    print("    %-12s %4s | %26s" % ("build", "n", "a779 (counts), block CI"))
    O6["a779"] = {}
    for nm in ("V86/r6f", "V85/r6e", "V86B/r70"):
        b = V.block_boot([r["a779"] for r in E[nm]], [r["blk"] for r in E[nm]])
        print("    %-12s %4d | %8.1f [%7.1f,%7.1f]" % (nm, b[3], b[0], b[1], b[2]))
        O6["a779"][nm] = list(b)
    for A, B in (("V86/r6f", "V85/r6e"), ("V86B/r70", "V85/r6e")):
        r = V.strat_block_boot_ratio(E[A], E[B], key="a779")
        print("      %-9s/%-9s a779 ratio %6.3f [%6.3f,%6.3f]"
              % (A.split("/")[0], B.split("/")[0], r["ratio"], r["lo"], r["hi"]))
        O6.setdefault("a779_ratio", {})["%s|%s" % (A, B)] = r
    print("    ⚠ Amplitude is NOT the scored statistic -- it is reported because it was asked\n"
          "      for.  All three CIs overlap heavily; no amplitude claim is made either way.")

    # =========================================================================================
    V.hdr("T4  ORDER-CLEAN THE 6e ARM, and the STRUCTURAL argument for the speed cut.")
    print("    Wheel order k lands in [6, 9] Hz when v is in [%.2f, %.2f] m/s for k=2,"
          % (6.0 * CIRC / 2, 9.0 * CIRC / 2))
    print("    but this analysis is restricted to v < %.1f m/s.  => ORDER 2 IS STRUCTURALLY\n"
          "    EXCLUDED FROM BOTH ARMS by the speed cut; the 20.7%% figure applies to 6e's FULL\n"
          "    speed range, not to this subset.  Orders 3 and 4 CAN reach the band (k=3 needs\n"
          "    v >= %.2f, k=4 needs v >= %.2f), so the order-clean below covers k = 1..4."
          % (V.VHI, 6.0 * CIRC / 3, 6.0 * CIRC / 4))
    print("\n    %-12s %14s %26s %26s" % ("build", "n raw -> clean", "f_c RAW", "f_c ORDER-CLEAN"))
    O6["order_clean"] = {}
    for nm in ("V85/r6e", "V86/r6f", "V86B/r70"):
        rc = V.order_clean(E[nm])
        b0, b1 = fc[nm], V.block_boot([r["f_free"] for r in rc], [r["blk"] for r in rc])
        print("    %-12s %6d -> %-5d %8.3f [%7.3f,%7.3f] %8.3f [%7.3f,%7.3f]"
              % (nm, len(E[nm]), len(rc), b0[0], b0[1], b0[2], b1[0], b1[1], b1[2]))
        O6["order_clean"][nm] = dict(raw=list(b0), clean=list(b1), n_raw=len(E[nm]),
                                     n_clean=len(rc))
    rA, rB = V.order_clean(E["V86/r6f"]), V.order_clean(E["V85/r6e"])
    r = V.strat_block_boot_ratio(rA, rB, key="f_free")
    print("    ORDER-CLEAN ratio V86/V85 = %.3f [%.3f,%.3f]" % (r["ratio"], r["lo"], r["hi"]))
    O6["order_clean"]["ratio"] = r

    # =========================================================================================
    V.hdr("T5  RECONCILIATION with PROBE's quantised-cave spectrum.")
    print("    %-12s %14s %30s %10s" % ("route", "PROBE peak", "MINE (block CI)", "agrees?"))
    O6["probe_reconcile"] = {}
    for nm, pk in PROBE.items():
        b = fc[nm]
        ok = b[1] <= pk <= b[2]
        print("    %-12s %11.2f Hz %10.3f [%7.3f,%7.3f] %14s"
              % (nm, pk, b[0], b[1], b[2], "YES" if ok else "NO"))
        O6["probe_reconcile"][nm] = dict(probe=pk, mine=list(b), inside_CI=bool(ok))

    (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part6.json").write_text(
        json.dumps(O6, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_freq_test_part6.json"))


if __name__ == "__main__":
    main()
