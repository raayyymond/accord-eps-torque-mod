#!/usr/bin/env python3
r"""studies/impedance/rez_band_tracking.py -- DOES THE ANTI-DAMPING TRACK THE MODE, OR SIT IN A FIXED BAND?

`route-v102` raised the failure mode that matters for a SIGN endpoint: Re(Z) is a ratio of a
cross-spectrum to an auto-spectrum over the same bins, so it stays well-CONDITIONED under a
bandwidth change -- but if the mode MIGRATES OUT of the evaluation band, a well-conditioned
estimate simply measures the damping somewhere the physics no longer is.  That is a FALSE PASS,
not a null, and it is the dangerous direction for a "did the sign flip back?" endpoint.

The migration is real and measured by `route-v102`: +0.157 Hz/(m/s) and ~+1 Hz per gain doubling.

This file answers it by measurement rather than argument: slide a narrow band across 16-36 Hz and
plot the SIGN of Re(Z) against frequency, on each arm.  If V102's negative region is a localised
notch sitting on its mode, the evaluation band MUST track the mode.  If V102 is negative across a
wide swathe, a fixed 22-26 Hz window is safe.

Estimator imported read-only from `decode_v90_probe`; `studies/impedance/rez_control.py` pins it to 0.00 % against
`_scratch/logs/v92_rez.log`.  Engaged, hands-off, moving, 29-86 km/h -- the endpoint's own conditioning.
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L          # noqa: E402
import decode_v90_probe as P     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0, bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")
ARMS = [("97", "STOCK 1x"), ("85", "V100 4x"), ("96", "V102 6x")]
DEG2RAD = np.pi / 180.0
RNG = np.random.default_rng(103_2026)
VLO, VHI = 8.0, 24.0          # m/s == 29-86 km/h
OUT = {}


def wins(route):
    R = L.ROUTES[route]
    z = np.load(R["cache"] / ("r" + route + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    W = P._wins(lat & (~press) & (v > 0.5), t, P.NW_Z, P.HOP_Z,
                (np.asarray(z["rate_f"], float) * DEG2RAD, np.asarray(z["tq"], float), v))
    return ([w for w in W if VLO <= float(np.median(w[2])) < VHI],
            1.0 / float(np.median(np.diff(t))))


def main():
    print("\n" + "=" * 104)
    print("Re(Z) SIGN vs FREQUENCY -- sliding 2 Hz band, 1 Hz step, engaged hands-off 29-86 km/h")
    print("=" * 104)
    lo_edges = np.arange(16.0, 35.0, 1.0)
    for rt, lab in ARMS:
        W, fs = wins(rt)
        if len(W) < 8:
            print("\n  %-11s only %d windows -- skipped" % (lab, len(W)))
            continue
        pairs = [(w[0], w[1]) for w in W]
        print("\n  --- %s, %d windows ---" % (lab, len(W)))
        rows = []
        for lo in lo_edges:
            hi = lo + 2.0
            r = P._band_transfer(pairs, fs, P.NW_Z, [("b", lo, hi)])["b"]
            bs = [P._band_transfer([pairs[k] for k in RNG.integers(0, len(pairs), len(pairs))],
                                   fs, P.NW_Z, [("b", lo, hi)])["b"]["re_over_sxx"]
                  for _ in range(150)]
            blo, bhi = np.percentile(bs, [2.5, 97.5])
            sig = "NEG" if bhi < 0 else ("POS" if blo > 0 else " . ")
            rows.append(dict(lo=float(lo), hi=float(hi), re_z=float(r["re_over_sxx"]),
                             lo_ci=float(blo), hi_ci=float(bhi), coh2=float(r["coh2"]), sig=sig))
        print("      %-11s %10s %20s %8s  %s" % ("band Hz", "Re(Z)", "95% CI", "coh2", "sign"))
        for x in rows:
            print("      %4.0f-%-6.0f %10.0f  [%8.0f,%8.0f] %8.3f  %s"
                  % (x["lo"], x["hi"], x["re_z"], x["lo_ci"], x["hi_ci"], x["coh2"], x["sig"]))
        neg = [x for x in rows if x["sig"] == "NEG"]
        if neg:
            print("      => SIGNIFICANTLY NEGATIVE from %.0f to %.0f Hz  (%d of %d bands)"
                  % (min(x["lo"] for x in neg), max(x["hi"] for x in neg), len(neg), len(rows)))
        else:
            print("      => NO band is significantly negative in 16-36 Hz")
        OUT[rt] = dict(build=lab, n=len(W), rows=rows)

    a, b = OUT.get("97"), OUT.get("96")
    if a and b:
        print("\n  SIGN MAP (N = CI entirely below 0, P = entirely above, . = straddles):")
        print("      %-11s %s" % ("Hz", "".join("%4.0f" % x["lo"] for x in a["rows"])))
        for k, d in (("STOCK", a), ("V102", b)):
            print("      %-11s %s"
                  % (k, "".join("%4s" % x["sig"].strip()[:1].replace("N", "N").replace("P", "P")
                                or "." for x in d["rows"])))


if __name__ == "__main__":
    main()
    Path(__file__).with_name("_scratch/out/_rez_band_tracking.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_rez_band_tracking.json")
