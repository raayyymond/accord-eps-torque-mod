# -*- coding: utf-8 -*-
"""d10_leak -- is the plant-alone (lp) hard-turn '1.6-3 Hz' excess of r2alt real 1.6-3 Hz motion, or LEAKAGE of the
low-frequency turning rate through the harness's 2nd-order band-pass (filtfilt gain -17 dB at 1.0 Hz, -12 dB at 1.2 Hz)?
Same frames as drive_metrics' hard16 (v 15-22, |plan| >= 1.5 or |ang| > 60, 1 s trimmed), nominal + light_b, lp + full,
real fork controller, paired noise.  Reads:
  hard16_h   the harness filter (as G8 / X9)
  hard16_s   a sharp 10th-order Butterworth band-pass 1.6-3 Hz (sos, filtfilt: <= -60 dB below 1.0 Hz)
  lo_h       0.2-1.2 Hz wheel-rate rms in the same frames (the turning motion that would leak)
  psd        Welch on whole-chunk rate restricted by a hard-frame mask weight: mean PSD in 1.6-3 Hz over the 15-22 m/s chunks"""
import os, sys, json
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import d4_drive as D4
import v295_harness as H

SOS = signal.butter(10, [1.6 / 50, 3.0 / 50], btype="band", output="sos")
SOSLO = signal.butter(4, [0.2 / 50, 1.2 / 50], btype="band", output="sos")
chunks = H.route_chunks()
L = []
P = lambda s: (print(s), L.append(s))  # noqa: E731
res = {}
for dist in ("lp", "full"):
    for cfg in ("V294+r1", "V295+r1", "V295+r2alt"):
        R = D4.run_config(cfg, ["nominal", "light_b"], dist, chunks, 0)
        for mi, m in enumerate(("nominal", "light_b")):
            rows = [mi * len(chunks) + k for k in range(len(chunks))]
            acc = {k: [] for k in ("h", "s", "lo")}
            for j in rows:
                n = R["lens"][j]
                v, r, pl, ang = R["v"][j, :n], R["rate18"][j, :n], R["la_plan"][j, :n], R["ang"][j, :n]
                mk = (v >= 15) & (v < 22)
                cut = np.zeros(n, bool); cut[100:-100] = True
                hard = mk & cut & ((np.abs(pl) >= 1.5) | (np.abs(ang) > 60))
                if not hard.any():
                    continue
                acc["h"].append(H._bp(r, 1.6, 3.0)[hard])
                acc["s"].append(signal.sosfiltfilt(SOS, r)[hard])
                acc["lo"].append(signal.sosfiltfilt(SOSLO, r)[hard])
            res[(dist, cfg, m)] = {k: float(np.sqrt(np.mean(np.concatenate(v) ** 2))) for k, v in acc.items()}
        print("done", dist, cfg, flush=True)
for dist in ("lp", "full"):
    for m in ("nominal", "light_b"):
        a, b, c = (res[(dist, k, m)] for k in ("V294+r1", "V295+r1", "V295+r2alt"))
        P("%-4s %-8s | hard16 harness filter: V294r1 %.3f V295r1 %.3f r2alt %.3f (x%.2f vs V295r1, x%.2f vs V294r1) | SHARP 1.6-3 Hz: "
          "%.3f %.3f %.3f (x%.2f, x%.2f) | 0.2-1.2 Hz turning rate: %.2f %.2f %.2f (x%.2f)" % (
              dist, m, a["h"], b["h"], c["h"], c["h"] / b["h"], c["h"] / a["h"], a["s"], b["s"], c["s"], c["s"] / b["s"],
              c["s"] / a["s"], a["lo"], b["lo"], c["lo"], c["lo"] / b["lo"]))
open(os.path.join(HERE, "out", "d10_leak_out.txt"), "w").write("\n".join(L) + "\n")
