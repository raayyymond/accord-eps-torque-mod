#!/usr/bin/env python3
"""Pull ENGINE_RPM out of the V68 rlogs and test the fixed ~28 Hz line against an ENGINE ORDER.

WHY. The averaged periodogram of engaged highway driving carries a line at 28.13 Hz that
  - survives the band-centre artefact test (fixed as the search band sweeps 24-30 ... 15-45 Hz),
  - does NOT track road speed (Theil-Sen -0.0665 Hz per m/s vs wheel order 2's +0.9616),
  - appears on V68/`4e` (prom 18.8), V67/`r47` (27.4) and V65/`r3b` (54.4) but not on V58/`r2b`
    or V62/`r37`, i.e. it is NOT a build or dose effect,
  - and STRENGTHENS in lane-change windows (prom 40.4).

28.13 Hz x 60 = 1688 rpm, which is exactly ordinary CVT cruise rpm for this car, so ENGINE ORDER 1
is the leading non-steering explanation. The Accord's CVT holds rpm near-constant at cruise -- the
prior session measured corr(rpm, v) = +0.270 only -- so an engine order LOOKS like a fixed mode
against road speed. That is precisely the trap that would make an engine line read as a chassis
mode.

THE TEST. Order n predicts f0 = n * rpm / 60. Regress the per-window line frequency on rpm:
    engine order 1  =>  slope +1/60 = +0.01667 Hz per rpm
    engine order 2  =>  slope +0.03333
    a fixed MODE    =>  slope  0.00000
The prior session used exactly this estimator to kill an engine-order-2 reading of the withdrawn
42 Hz mode (required -0.0333, measured -0.00071 [-0.00251, +0.00084]).

🛑 Signal per the prior session's own extraction: ENGINE_RPM = 0x17C bytes 2:3, BIG-ENDIAN, src 1.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
OUT = ROOT / "_cache_v68"
ROUTES = {
    "4c": ("75604b0a432fdc89_0000004c--d0ea3c14b4", [4, 5, 6, 7, 8]),
    "4e": ("75604b0a432fdc89_0000004e--11f5b814b6", [31, 32, 33, 34]),
}


def main():
    for tag, (route, segs) in ROUTES.items():
        for s in segs:
            dst = OUT / f"{tag}s{s}_rpm.npz"
            if dst.exists():
                continue
            t, rpm = [], []
            for evt in read_messages(RLOGDIR / f"{route}--{s}--rlog.zst"):
                try:
                    if evt.which() != "can":
                        continue
                except Exception:
                    continue
                tm = evt.logMonoTime * 1e-9
                for m in evt.can:
                    if int(m.src) == 1 and int(m.address) == 0x17C:
                        d = bytes(m.dat)
                        if len(d) >= 4:
                            t.append(tm)
                            rpm.append((d[2] << 8) | d[3])
            base = np.load(OUT / f"{tag}s{s}.npz")["t0_mono"][0]
            t = np.array(t, float) - base
            rpm = np.array(rpm, float)
            np.savez_compressed(dst, t=t, rpm=rpm)
            ok = (rpm > 400) & (rpm < 7000)
            print(f"  {tag}s{s}: {len(rpm)} 0x17C frames  rpm "
                  f"{np.percentile(rpm[ok], 5):.0f}..{np.percentile(rpm[ok], 95):.0f} "
                  f"(median {np.median(rpm[ok]):.0f})  plausible {100 * ok.mean():.1f}%")


if __name__ == "__main__":
    main()
