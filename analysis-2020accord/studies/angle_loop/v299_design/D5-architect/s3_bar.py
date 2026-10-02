# -*- coding: utf-8 -*-
r"""s3_bar.py -- D5-architect.  Note 3 (the torque bar): what the proposed angle-mode bar -- the EPS's own lane torque
from 0x1AB STEER_MOTOR_TORQUE / the 2461 T lane rail, through the UI's 0.1 s first-order filter, sampled the way the
fork would see it (50 Hz frame, carState latency 10-20 ms) -- would have shown on route 79, against the current bar.
EVIDENCE base: the 0x1AB frame is a VALID Honda frame on V298 (s6_check_1ab.py: checksum 100 %, counter 100 %).
Metrics: |corr| with the delivered |tap|, pinned share (|bar| >= 0.95), sign agreement with err (theta_sp - theta) on
frames with |tap| > 25 LSB, P(bar >= 0.9 | tap < 25 LSB).  Vectorised.  Wall printed.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "v298_flight"))
import m3_lane as M  # noqa: E402

OUT = M.KIT / "_scratch" / "out" / "v299_D5"
W = M.load_wire()
t, eng = W["t"], W["eng"]
TT, Tt = W["T_t"], W["T"]                         # 0x1AB tap, T counts (signed), 50 Hz
ok = np.isfinite(Tt)
TT, Tt = TT[ok], Tt[ok]
RAIL = 2461.0
res = {}
for lat_ms in (10, 20, 40):
    j = np.clip(np.searchsorted(TT, t - lat_ms / 1000.0, side="right") - 1, 0, len(TT) - 1)
    raw = np.clip(-Tt[j] / RAIL, -1, 1)              # sign: T_left = -T (s2: replay/err correlation sign -1)
    a = 1 - np.exp(-0.01 / 0.1)                      # UI FirstOrderFilter rc 0.1 s at 100 Hz
    from scipy.signal import lfilter
    bar = lfilter([a], [1, -(1 - a)], raw)
    j0 = np.clip(np.searchsorted(TT, t, side="right") - 1, 0, len(TT) - 1)
    tap = np.abs(Tt[j0]) / 8.0
    m = eng
    err = np.nan_to_num(W["err"])
    big = m & (tap > 25)
    res[lat_ms] = dict(corr=float(np.corrcoef(np.abs(bar[m]), tap[m])[0, 1]),
                       pinned=float((np.abs(bar[m]) >= 0.95).mean()),
                       sign_agree=float((np.sign(bar[big]) == np.sign(err[big])).mean()),
                       p_full_given_small=float((np.abs(bar[m & (tap < 25)]) >= 0.9).mean()),
                       bar_p50=float(np.percentile(np.abs(bar[m]), 50)), bar_p99=float(np.percentile(np.abs(bar[m]), 99)))
print("s3 -- proposed angle-mode bar = -0x1AB lane torque / 2461 T, UI 0.1 s filter (route 79, engaged %.1f s)" % (eng.sum() / 100))
print("  current bar (drive read / refutes, EVIDENCE): |corr| 0.135, pinned 59.7 %, P(bar>=0.9 | tap<25) 0.60")
for k, r in res.items():
    print("  latency %2d ms: |corr| %.3f  pinned %.2f %%  sign==sign(err) %.3f  P(bar>=0.9|tap<25) %.3f  |bar| p50 %.3f p99 %.3f" % (
        k, r["corr"], 100 * r["pinned"], r["sign_agree"], r["p_full_given_small"], r["bar_p50"], r["bar_p99"]))
res["wall_s"] = time.time() - T0
print("wall %.1f s" % res["wall_s"])
(OUT / "s3_bar.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
