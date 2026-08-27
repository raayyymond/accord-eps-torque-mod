#!/usr/bin/env python3
"""DIFFERENCE-IN-DIFFERENCES.  Fixes a defect in my own N3 rule.

N3 marked a quantity "readable" when the alpha-DIFFERING ratio excluded 1.00 and the SAME-alpha
null happened to include it.  That is wrong when the two point estimates are nearly equal --
amplitude read 0.661 [0.524, 0.990] against a null of 0.701 [0.561, 1.046], i.e. two builds
SHARING alpha reproduced the whole "effect".

The correct test is the ratio-of-ratios, (V86/V85) / (V86B/V85).  With V85 shared it collapses
algebraically to V86/V86B -- which is also the best-matched pair available (both parking-lot,
same session, same protocol).  A quantity is only attributable to alpha if THAT excludes 1.00.
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
from v86_hf_power import prep       # noqa: E402

ROOT = V.ROOT
O = {}
KEYS = [("f_hf", "frequency (argmax)"), ("l_f0", "frequency (Lorentzian f0)"),
        ("e_exc", "ENERGY (excess 18-27)"), ("a_hf", "amplitude (p99 env)"),
        ("hp_Q", "Q (half-power)"), ("l_Q", "Q (Lorentzian)")]


def main():
    E = {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = prep(V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True))))

    V.hdr("D1  DIFFERENCE-IN-DIFFERENCES = V86 / V86B (the shared V85 reference cancels).\n"
          "    Both arms are parking-lot, same session, same protocol; they differ in alpha\n"
          "    (286 vs 573) and in FactorC.  A quantity is attributable to alpha only if THIS\n"
          "    excludes 1.00.")
    print("    %-26s | %24s | %24s | %s"
          % ("quantity", "vs V85 (alpha differs)", "V86/V86B (DiD)", "attributable to alpha?"))
    for key, lab in KEYS:
        re = V.strat_block_boot_ratio(E["V86/r6f"], E["V85/r6e"], key=key)
        dd = V.strat_block_boot_ratio(E["V86/r6f"], E["V86B/r70"], key=key)
        ex = dd["hi"] < 1.0 or dd["lo"] > 1.0
        print("    %-26s | %6.3f [%6.3f,%6.3f] | %6.3f [%6.3f,%6.3f] | %s"
              % (lab, re["ratio"], re["lo"], re["hi"], dd["ratio"], dd["lo"], dd["hi"],
                 "YES" if ex else "no -- NOT SEPARABLE FROM FLOOR"))
        O[key] = dict(label=lab, vs_V85=re, did=dd, attributable=bool(ex))

    V.hdr("D2  WHAT SURVIVES.  Only quantities that clear D1 may be quoted as alpha effects.")
    keep = [O[k]["label"] for k, _ in KEYS if O[k]["attributable"]]
    drop = [O[k]["label"] for k, _ in KEYS if not O[k]["attributable"]]
    print("    ATTRIBUTABLE TO alpha : %s" % (", ".join(keep) or "none"))
    print("    NOT SEPARABLE         : %s" % (", ".join(drop) or "none"))
    O["_keep"], O["_drop"] = keep, drop

    (ROOT / "_scratch/cache/r6f" / "v86_hf_did.json").write_text(json.dumps(O, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_hf_did.json"))


if __name__ == "__main__":
    main()
