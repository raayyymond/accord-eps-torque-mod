"""Apply the ii friction-bias correction to REAL data (trimmed grid: direct estimator, rate fit, 3 speed bins,
F = 0.01 and 0.02). One route at a time; nothing held between routes.

usage: python ii_real2.py route [route ...]
"""
import sys, json
from pathlib import Path
import numpy as np
import common as C, estimate as E, synth as Y, ii

OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
BINS = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0)]

if __name__ == "__main__":
    res = {}
    for route in sys.argv[1:]:
        R = C.load_route(route); mask = C.handsoff_mask(R)
        for lo, hi in BINS:
            for F in (0.01, 0.02):
                c = ii.corrected(R, mask, R, "sp", "direct", lo, hi, F=F)
                key = f"{route}|direct|v{lo:.0f}-{hi:.0f}|F{F}"
                res[key] = c
                if c.get("Dcorr") is None:
                    print(key, "n", c["n"], "FAIL", flush=True)
                else:
                    print(f"{key:44s} n{c['n']:3d} D0 {c['D0']*1e3:6.1f} D1 {c['D1']*1e3:6.1f} "
                          f"bias {c['bias']*1e3:+5.1f} Dcorr {c['Dcorr']*1e3:6.1f} "
                          f"J0 {c['J0']:.1e} b0 {c['b0']:.1e} k0 {c['k0']:.1e}", flush=True)
        del R, mask
        (OUT / "ii_real2.json").write_text(json.dumps(res, indent=1, default=float))
