"""Synthesis-judge checks 2 (cache only, vectorised, < 5 s):
 H. the >22 m/s tracking FAIL: an approximate re-derivation of the goal form (0.5 Hz zero-phase LPF, first 4 s of each
    >= 15 s free run dropped, OLS slope with intercept), whole run vs the run with its last 1 s / 2 s cut
 I. the M-N6 stop band ("hands-off error > 1 deg on a straight >= 8 m/s -> REVERT"): |theta_sp - theta| distribution and
    the longest continuous stretch > 1 deg, hands-off, engaged, straight (|theta_sp| < 3 deg), v >= 8 m/s
"""
import time, json
import numpy as np
from scipy import signal
from pathlib import Path
T0 = time.time()
C = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
OUT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/out/r79/judge")
W = dict(np.load(C / "r79_a1f5d2_al.npz"))


def zoh(ts, x, t):
    j = np.searchsorted(ts, t, side="right") - 1
    return np.asarray(x)[np.clip(j, 0, len(x) - 1)]


def runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


te4 = W["te4"]
tg = np.arange(te4[0] + 1.0, te4[-1] - 1.0, 0.01)
th = zoh(W["t14"], W["ang"], tg)
sp = -zoh(te4, W["cmd"], tg) / 10.0
eng = (zoh(te4, W["req"], tg) > 0) & (zoh(W["t18"], W["sca"], tg) > 0)
v = zoh(W["tcs"], W["vego"], tg)
press = zoh(W["tcs"], W["cs_press"], tg) > 0
bar = zoh(W["t18"], W["tq"] * 1.024, tg)
sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
out = {}
lines = []
for nm, lo, hi in (("15-22", 15, 22), (">22", 22, 99), (">=25", 25, 99)):
    m = eng & ~press & (v >= lo) & (v < hi)
    res = {}
    for cut in (0, 100, 200):
        X, Y = [], []
        for a, b in runs(m, 1500):
            x = signal.sosfiltfilt(sos, sp[a:b])
            y = signal.sosfiltfilt(sos, th[a:b])
            e = len(x) - cut
            X.append(x[400:e]); Y.append(y[400:e])
        if not X:
            continue
        Xa, Ya = np.concatenate(X), np.concatenate(Y)
        res[f"cut{cut / 100:.0f}s"] = dict(slope=float(np.linalg.lstsq(np.c_[Xa, np.ones_like(Xa)], Ya, rcond=None)[0][0]), secs=len(Xa) / 100)
    out["track_" + nm] = res
    lines.append("H. tracking %-6s %s" % (nm, json.dumps(res)))
# I. M-N6
m = eng & ~press & (np.abs(bar) < 500) & (v >= 8) & (np.abs(sp) < 3.0)
err = np.abs(sp - th)
over = m & (err > 1.0)
rr = runs(over, 1)
longest = max((b - a for a, b in rr), default=0) / 100
n05 = sum(1 for a, b in rr if b - a >= 50)
out["MN6"] = dict(secs=float(m.sum() / 100), p50=float(np.percentile(err[m], 50)), p90=float(np.percentile(err[m], 90)),
                  p99=float(np.percentile(err[m], 99)), frac_gt1=float(over.sum() / max(m.sum(), 1)), longest_run_s=longest, runs_ge_0p5s=n05,
                  longest_at_t=float(tg[max(rr, key=lambda r: r[1] - r[0])[0]]) if rr else None)
lines.append("I. M-N6 straight hands-off >= 8 m/s: " + json.dumps(out["MN6"]))
out["wall_s"] = time.time() - T0
lines.append("wall %.2f s" % out["wall_s"])
print("\n".join(lines))
(OUT / "judge_verify2.json").write_text(json.dumps(out, indent=1))
(OUT / "judge_verify2.txt").write_text("\n".join(lines))

# I2. M-N6, steady form: 0.5 Hz zero-phase LPF of err on the 100 Hz grid, straight = |sp_lpf| < 1.5 deg and
#     |d sp_lpf/dt| < 1 deg/s, hands-off |bar| < 300 and not pressed, engaged >= 1.2 s, by band; runs of |err_lpf| > 1 deg
rise = np.where(np.r_[eng[0], eng[1:] & ~eng[:-1]], tg, -np.inf)
tse = tg - np.maximum.accumulate(rise)
e_l = signal.sosfiltfilt(sos, sp - th)
s_l = signal.sosfiltfilt(sos, sp)
ds = np.gradient(s_l, 0.01)
ho = eng & (tse >= 1.2) & ~press & (np.abs(bar) < 300)
st = ho & (np.abs(s_l) < 1.5) & (np.abs(ds) < 1.0)
lines2 = []
mn6 = {}
for nm, lo, hi in (("8-12.5", 8, 12.5), ("12.5-22", 12.5, 22), (">22", 22, 99)):
    m = st & (v >= lo) & (v < hi)
    ov = m & (np.abs(e_l) > 1.0)
    rr = runs(ov, 1)
    lr = sorted(((b - a) / 100, float(tg[a]), float(np.mean(e_l[a:b])), float(np.mean(th[a:b])), float(np.mean(v[a:b]))) for a, b in rr)[::-1][:3]
    mn6[nm] = dict(secs=float(m.sum() / 100), elpf_p50=float(np.percentile(np.abs(e_l[m]), 50)) if m.any() else None,
                   elpf_p90=float(np.percentile(np.abs(e_l[m]), 90)) if m.any() else None,
                   frac_gt1=float(ov.sum() / max(m.sum(), 1)), runs_ge_1s=sum(1 for a, b in rr if b - a >= 100),
                   longest3=[dict(dur_s=a, t=b, mean_err=c, mean_theta=d, v=e) for a, b, c, d, e in lr])
    lines2.append("I2. M-N6 steady %-8s %s" % (nm, json.dumps(mn6[nm])))
out["MN6_steady"] = mn6
print("\n".join(lines2))
(OUT / "judge_verify2.json").write_text(json.dumps(out, indent=1))
(OUT / "judge_verify2.txt").write_text("\n".join(lines + lines2))
