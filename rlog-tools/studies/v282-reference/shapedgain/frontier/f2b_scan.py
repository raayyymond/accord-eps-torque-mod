# -*- coding: utf-8 -*-
"""f2b -- scan metric definitions to find the one that reproduces the brief's anchors
(rev 6.4 as flown 1.350, V282 0.442, ratio 3.05).  Read-only; decides nothing by itself."""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import v282cmp as V   # noqa: E402
import lp_lib as LP   # noqa: E402

SETS = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
        "T64": ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]}
BAND = (0.15, 2.4)


def collect(route, ykey, vmin, run_s):
    S = V.load(route)
    m = (S["active"] & ~S["pressed"] & (S["v"] >= vmin)
         & np.isfinite(S["setpoint"]) & np.isfinite(S["la_act"]) & np.isfinite(S["la_pose"]) & np.isfinite(S["model"]))
    segs = [(np.nan_to_num(S["model"][a:b]), np.nan_to_num(S[ykey][a:b])) for a, b in V.runs(m, S["t"], min_s=run_s)]
    del S
    return segs


def metric(segs, nps, det, band=BAND):
    pe = px = 0.0
    w = signal.get_window("hann", nps)
    for x, y in segs:
        for s in range(0, len(x) - nps + 1, nps // 2):
            xx, yy = x[s:s + nps], y[s:s + nps]
            if det:
                xx, yy = signal.detrend(xx), signal.detrend(yy)
            else:
                xx, yy = xx - xx.mean(), yy - yy.mean()
            f = np.fft.rfftfreq(nps, 1 / V.FS)
            b = (f >= band[0]) & (f <= band[1])
            Xf = np.fft.rfft(xx * w); Ef = np.fft.rfft((xx - yy) * w)
            pe += float(np.sum(np.abs(Ef[b]) ** 2)); px += float(np.sum(np.abs(Xf[b]) ** 2))
    return pe / max(px, 1e-30), pe, px


if __name__ == "__main__":
    for ykey in ("la_pose", "la_act"):
        for vmin, run_s in ((15.0, 30.0), (15.0, 41.0)):
            store = {g: [s for r in rs for s in collect(r, ykey, vmin, run_s)] for g, rs in SETS.items()}
            for nps in (1024, 2048, 4096):
                for det in (True, False):
                    res = {}
                    for g, segs in store.items():
                        if not segs or max(len(x) for x, _ in segs) < nps:
                            res[g] = np.nan
                            continue
                        res[g] = metric([s for s in segs if len(s[0]) >= nps], nps, det)[0]
                    print(f"y={ykey:8s} vmin{vmin:4.0f} run{run_s:4.0f} nps{nps:5d} det{int(det)} "
                          f" T64 {res['T64']:6.3f}  V282 {res['V282']:6.3f}  ratio {res['T64']/max(res['V282'],1e-9):5.2f}")
