"""ADV-bytes 13: the RE-WORDED primary read -- exact-model beta ALONE (LIVE >= 0.5, NOT <= 0.3, else AMBIGUOUS), on all
engaged frames (hands-on included) of each window, with and without a footprint gate (sum r^2 >= 5*(3.64/0.1)^2)."""
import os, sys
import numpy as np
from scipy import signal as S
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(V295, "plant"), os.path.join(V295, "lib")):
    sys.path.insert(0, p)
import plib as P
d = P.load(); z = np.load(os.path.join(HERE, "_scratch", "advb6_march.npz"))
sg = d["sg"]; tt = d["tick_tap"]; tap = d["T_tap"].astype(float); j = d["j100"]
q0, q1 = P.quant(sg * z["T0"][tt]), P.quant(sg * z["T1"][tt]); r = (sg * (z["T1"] - z["T0"])[tt]).astype(float); e = tap - q0
Y = {"A1017": q1 - q0 + e, "V294 null": e}
eng = d["eng"][j].astype(bool); ho = eng & (np.abs(d["bar"][j]) < 400) & ~d["pressed"][j]
t_tap = d["t_tap"]; GATE = 5 * (3.64 / 0.1) ** 2
def cls(b):
    return "LIVE" if b >= 0.5 else ("NOT" if b <= 0.3 else "AMB")
def run(label, spans, msk):
    for gate in (False, True):
        row = []
        for nm, y in Y.items():
            c = {}
            for a, b_ in spans:
                w = np.flatnonzero(msk & (t_tap >= a) & (t_tap < b_))
                if len(w) < 300: continue
                den = np.sum(r[w] ** 2)
                if gate and den < GATE:
                    c["gated"] = c.get("gated", 0) + 1; continue
                k = cls(np.sum(y[w] * r[w]) / den); c[k] = c.get(k, 0) + 1
            row.append("%s: %s" % (nm, ", ".join("%s %d" % kv for kv in sorted(c.items()))))
        print("  %-48s %-8s %s" % (label, "gated" if gate else "ungated", " || ".join(row)))
t0, t1 = d["t"][0], d["t"][-1]
for Ws in (30.0, 15.0):
    sp = [(a, a + Ws) for a in np.arange(t0, t1 - Ws, Ws)]
    run("contiguous %2.0f s, ALL engaged frames" % Ws, sp, eng)
    run("contiguous %2.0f s, hands-off frames" % Ws, sp, ho)
om = np.nan_to_num(d["om"]); sos = S.butter(2, [1.6, 3.0], "bandpass", fs=100, output="sos"); eb = S.sosfiltfilt(sos, om) ** 2
for Ws in (30.0, 15.0):
    n100 = int(Ws * 100); cand = []
    for s0 in range(0, len(om) - n100, n100 // 2):
        sl = slice(s0, s0 + n100)
        if d["eng"][sl].mean() >= 0.8 and 5.0 <= d["v"][sl].mean() < 15.0: cand.append((float(eb[sl].mean()), s0))
    cand.sort(reverse=True); ch = []
    for en, s0 in cand:
        if all(abs(s0 - c0) >= n100 for c0 in ch): ch.append(s0)
        if len(ch) >= 12: break
    run("symptomatic %2.0f s x%d, ALL engaged" % (Ws, len(ch)), [(d["t"][s0], d["t"][s0] + Ws) for s0 in ch], eng)
