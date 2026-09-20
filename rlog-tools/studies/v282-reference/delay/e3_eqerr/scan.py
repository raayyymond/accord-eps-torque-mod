"""Landscape diagnostic: the SSE(D) curve itself, on a WIDE grid and several bands, for the real routes.

The first real-data run put argmin at the grid edge (115 ms), so the question is whether SSE(D) has a
genuine interior minimum at all, how deep it is, and which band carries the delay information.  A delay
is identified by PHASE per ms: 1 ms is 0.36 deg at 1 Hz but 2.9 deg at 8 Hz, so a band that stops at
8 Hz has little leverage -- but the 1 deg/s rate LSB puts a noise floor up there.  Printed per band:
the interior local minima of SSE(D), their depth relative to the curve's max, and R2.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eqerr as E

DG = np.arange(-60, 401, 2)
BANDS = [(0.3, 8.0), (0.5, 4.0), (1.0, 6.0), (2.0, 10.0), (3.0, 12.0), (1.5, 20.0), (0.3, 20.0)]
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0)]
TORQUE = E.TORQUE
out = {}
for band in BANDS:
    E.BAND = band
    sos = E.make_L(band)
    allb = []
    for rk in TORQUE:
        allb += E.route_blocks(rk, sos, dwell=2.0, band=band, dgrid=DG, spring="hold")
    print(f"\nband {band[0]}-{band[1]} Hz   blocks {len(allb)}  rows {sum(b['nrow'] for b in allb)}", flush=True)
    for lo, hi in SPD + [(0.0, 99.0)]:
        sel = [b for b in allb if lo <= b["v"] < hi]
        sse, beta = E.sse_curve(sel)
        if sse is None:
            continue
        UU = sum(b["UU"] for b in sel)
        R2 = 1 - sse / UU
        rng = sse.max() - sse.min()
        loc = [i for i in range(1, len(sse) - 1) if sse[i] < sse[i - 1] and sse[i] < sse[i + 1]]
        loc = sorted(loc, key=lambda i: sse[i])[:4]
        g = int(np.argmin(np.abs(DG - 40)))          # R2 at a nominal 40 ms, for reference
        print(f"  v {lo:4.0f}-{hi:<4.0f} n{len(sel):4d} argmin {DG[int(np.argmin(sse))]:+5d} ms "
              f"R2max {R2.max():.3f} (R2 at 40ms {R2[g]:.3f})  local minima: "
              + ", ".join(f"{DG[i]:+4d}ms(depth {(sse.max()-sse[i])/rng:.2f},R2 {R2[i]:.3f})" for i in loc), flush=True)
        out[f"{band}_{lo}_{hi}"] = dict(D=DG.tolist(), sse=sse.tolist(), R2=R2.tolist(),
                                        beta=beta.tolist(), n=len(sel))
    del allb
Path(Path(__file__).resolve().parent / "scan.json").write_text(json.dumps(out, default=float))
