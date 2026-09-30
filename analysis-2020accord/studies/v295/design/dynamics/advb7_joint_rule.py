"""ADV-bytes step 7: the design's pre-registered sentences applied AS WRITTEN, per window, to (a) a synthetic A1017 flight
and (b) the real V294 flight (the null), on the windows one short drive supplies.
  LIVE        : beta >= 0.5 AND |K|(0.3-1 Hz) >= 0.28
  NOT A1017   : beta <= 0.3 (and |K| near 0.19)
  STOP-ARITH  : |K|(0.3-1 Hz) > 0.45 OR phase shift < -30 deg (vs the V294 pooled phase +157)
  otherwise   : AMBIGUOUS
beta from the exact-model regression on the plib grid (hands-off engaged tap frames of the window); |K| from the metric
agent's own band signals + least squares on its grid (hands-off frames of the same window, same time span).
Also: the same with a minimum-footprint gate (sum r^2 large enough for SE(beta) <= 0.1 predicted) and pooled reads."""
import contextlib, io, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(V295, "plant"), os.path.join(V295, "lib"), os.path.join(V295, "metric")):
    sys.path.insert(0, p)
import plib as P  # noqa: E402
from scipy import signal as S  # noqa: E402
OUT = []
def pr(*a):
    s = " ".join(str(v) for v in a); print(s, flush=True); OUT.append(s)
d = P.load()
z = np.load(os.path.join(HERE, "_scratch", "advb6_march.npz")); T0, T1 = z["T0"], z["T1"]
sg = d["sg"]; tt = d["tick_tap"]; tap = d["T_tap"].astype(float); j = d["j100"]
q0, q1 = P.quant(sg * T0[tt]), P.quant(sg * T1[tt]); r = (sg * (T1 - T0)[tt]).astype(float); e = tap - q0
y = {"A1017 synthetic": q1 - q0 + e, "V294 real (null)": e}
ho = d["eng"][j].astype(bool) & (np.abs(d["bar"][j]) < 400) & ~d["pressed"][j]
t_tap = d["t_tap"]
with contextlib.redirect_stdout(io.StringIO()):
    import accel_tracking_metric as M
g = M.build_grid("r71b_v294")
g_syn = dict(g); g_syn["T"] = g["T"] - np.interp(g["t"], t_tap, q1 - q0)
BK = {}
for nm, gg in (("V294 real (null)", g), ("A1017 synthetic", g_syn)):
    B, valid = M.band_signals(gg, 0.3, 1.0, ["T", "Tff", "alpha_w"], hilb=("T", "Tff", "alpha_w"))
    BK[nm] = (B, valid & gg["HO"])
PH0 = 157.0

def K_in(nm, t_lo, t_hi):
    B, sel = BK[nm]
    s2 = sel & (g["t"] >= t_lo) & (g["t"] < t_hi)
    if s2.sum() < 500:
        return np.nan, np.nan
    X = np.column_stack([B["Tff"], B["HTff"], B["alpha_w"], B["Halpha_w"]])[s2]
    cc = np.linalg.lstsq(X, B["T"][s2], rcond=None)[0]
    return float(np.hypot(cc[2], cc[3])), float(np.degrees(np.arctan2(-cc[3], cc[2])))

def classify(b_, K, ph):
    if np.isfinite(K) and (K > 0.45 or ((ph - PH0 + 180) % 360 - 180) < -30):
        return "STOP-ARITH"
    if b_ >= 0.5 and np.isfinite(K) and K >= 0.28:
        return "LIVE"
    if b_ <= 0.3:
        return "NOT-A1017"
    return "AMBIGUOUS"

def run(label, spans, gate=False):
    tallies = {}
    for nm in y:
        cnt = {}
        for (t_lo, t_hi) in spans:
            w = np.flatnonzero(ho & (t_tap >= t_lo) & (t_tap < t_hi))
            if len(w) < 300:
                continue
            den = np.sum(r[w] ** 2)
            if gate and den < (3.64 ** 2) / 0.1 ** 2 * 5:      # predicted SE(beta) with ~5-frame correlation <= 0.1
                cnt["GATED-OUT"] = cnt.get("GATED-OUT", 0) + 1
                continue
            b_ = float(np.sum(y[nm][w] * r[w]) / den)
            K, ph = K_in(nm, t_lo, t_hi)
            cl = classify(b_, K, ph)
            cnt[cl] = cnt.get(cl, 0) + 1
        tallies[nm] = cnt
    pr("  %-52s %s" % (label, " || ".join("%s: %s" % (nm, ", ".join("%s %d" % kv for kv in sorted(c.items()))) for nm, c in tallies.items())))

t0 = d["t"][0]; t1 = d["t"][-1]
for Ws in (30.0, 15.0):
    spans = [(a, a + Ws) for a in np.arange(t0, t1 - Ws, Ws)]
    run("contiguous %2.0f s windows, as written" % Ws, spans)
    run("contiguous %2.0f s windows, footprint-gated" % Ws, spans, gate=True)
# symptomatic windows (5-15 m/s, top 1.6-3 Hz wheel-rate energy), as advb6 A3
om = np.nan_to_num(d["om"]); sos = S.butter(2, [1.6, 3.0], "bandpass", fs=100, output="sos"); eb = S.sosfiltfilt(sos, om) ** 2
for Ws in (30.0, 15.0):
    n100 = int(Ws * 100); cand = []
    for s0 in range(0, len(om) - n100, n100 // 2):
        sl = slice(s0, s0 + n100)
        if d["eng"][sl].mean() >= 0.8 and 5.0 <= d["v"][sl].mean() < 15.0:
            cand.append((float(eb[sl].mean()), s0))
    cand.sort(reverse=True); ch = []
    for en, s0 in cand:
        if all(abs(s0 - c0) >= n100 for c0 in ch):
            ch.append(s0)
        if len(ch) >= 12:
            break
    run("symptomatic %2.0f s x%d, as written" % (Ws, len(ch)), [(d["t"][s0], d["t"][s0] + Ws) for s0 in ch])
# pooled whole-drive read
w = np.flatnonzero(ho)
for nm in y:
    b_ = float(np.sum(y[nm][w] * r[w]) / np.sum(r[w] ** 2))
    K, ph = K_in(nm, t0, t1 + 1)
    pr("  pooled whole drive (%.0f s hands-off engaged): %-18s beta %.3f |K| %.3f phase %+.0f -> %s" % (
        len(w) / 50, nm, b_, K, ph, classify(b_, K, ph)))
open(os.path.join(HERE, "advb7_joint_rule_out.txt"), "w").write("\n".join(OUT) + "\n")
