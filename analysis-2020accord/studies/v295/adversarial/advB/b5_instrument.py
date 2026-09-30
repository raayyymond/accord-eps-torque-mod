"""b5_instrument.py -- ADV-B step 5: the pre-registered c1/c2 wire read, implemented on MY marches (b4), attacked.

  T_tap = c0 + c1*FF + c2*TRIM      per window, OLS, on 427-tap frames
  FF = N4 (V294 lane, r26 forced 0) at the tap tick ; TRIM = L4 - N4 (V294 live minus null) at the tap tick
Series scored (same frames, same regressors):
  NULL   the REAL r71b tap (V294 on the car)
  PA     real tap + quant(L5) - quant(L4)           (V295 march + the real residual)
  PB     quant(quant(N4) + 1.852*(tap - quant(N4)))  (STRESS: the whole non-FF content of the real tap scales with b)
  INV5   real tap + quant(I5) - quant(L4)           (V295 with the operand INVERTED)
  INV4   real tap + quant(I4) - quant(L4)           (V294 with the operand inverted)
Windows: HO15/HO30 = hands-off engaged tap frames in consecutive chunks of 15/30 s of exposure;
         ALL15/ALL30 = contiguous wall-clock windows (non-overlapping) with >= 90 % settled-engaged frames, all engaged
         frames (hands-on included); SLIDE15 = the same, 15 s, sliding by 2.5 s (for rates only: overlapping);
         HT = +-10 s around each 5-22 m/s hard-turn event, all engaged frames (and hands-off only).
Hands-off = settled engaged & NOT carState.steeringPressed dilated +-0.5 s.  Settled engaged = 0xE4 req & 0x18F SCA
held >= 2.0 s before and >= 0.3 s after the frame.
Rule under test: c2 > 1.45 => V295 live ; c2 < 1.45 => not live ; c2 < 0 => inverted.
Run: python b5_instrument.py > b5_instrument_out.txt
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/lib")
import r71b_cache as R  # noqa: E402

RATIO = 1050.0 / 567.0
THR = 1.45
rng = np.random.default_rng(20260930)


def quant(T):
    T = np.asarray(T, dtype=np.int64)
    return np.sign(T) * ((np.abs(T) >> 3) << 3)


def zoh_at(t_src, v_src, t_dst):
    j = np.clip(np.searchsorted(t_src, t_dst, side="right") - 1, 0, len(t_src) - 1)
    return np.asarray(v_src)[j]


def runs(mask):
    d = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


D = R.load(with_raw=False)
G = R.grid100(D)


def load_m(dms=0, xm="lin"):
    return dict(np.load(os.path.join(HERE, "_scratch", "marches_d%+d_%s.npz" % (dms, xm))))


M0 = load_m(0, "lin")
tap_t = M0["tap_t"]
tap = M0["tap_T"].astype(np.int64)
ntap = len(tap)
valid_tick = (M0["tap_tick"] >= 0) & (M0["tap_tick"] < len(M0["L4"]))

# ---- frame masks at tap instants ----
t100 = G["t"]
eng100 = np.asarray(G["eng"], bool)
eng_t = zoh_at(t100, eng100.astype(int), tap_t).astype(bool)
# settled: eng held >= 2 s before and >= 0.3 s after
settle = np.zeros(ntap, bool)
for a, b in runs(eng100):
    ta, tb = t100[a], t100[b - 1]
    settle |= (tap_t >= ta + 2.0) & (tap_t <= tb - 0.3)
pressed = zoh_at(D["cs_t"], D["cs_pressed"], tap_t) > 0.5
# dilate pressed +-0.5 s (at 50 Hz: 25 frames)
pr = np.convolve(pressed.astype(int), np.ones(51, int), "same") > 0
bar_t = zoh_at(D["s18_t"], D["s18_tq_raw"] * 1.024, tap_t)
v_t = zoh_at(D["cs_t"], D["cs_vego"], tap_t)
ang_t = zoh_at(D["cs_t"], D["cs_angle"], tap_t)
plan_t = zoh_at(D["ctl_t"], D["ctl_des_curv"], tap_t) * v_t ** 2
E_ok = settle & eng_t & valid_tick
HO = E_ok & ~pr
HO_bar = E_ok & (np.abs(bar_t) < 400)
print("tap frames %d ; settled engaged %.1f s ; hands-off (pressed-dilated) %.1f s ; hands-off |bar|<400 %.1f s"
      % (ntap, E_ok.sum() / 50, HO.sum() / 50, HO_bar.sum() / 50))


def series(M):
    tt = np.clip(M["tap_tick"], 0, len(M["L4"]) - 1)
    N4 = M["N4"].astype(np.int64)[tt]; L4 = M["L4"].astype(np.int64)[tt]; L5 = M["L5"].astype(np.int64)[tt]
    I5 = M["I5"].astype(np.int64)[tt]; I4 = M["I4"].astype(np.int64)[tt]
    FF = N4.astype(float); TRIM = (L4 - N4).astype(float)
    S = dict(NULL=tap.astype(float),
             PA=(tap + quant(L5) - quant(L4)).astype(float),
             PB=quant(np.round(quant(N4) + RATIO * (tap - quant(N4)))).astype(float),
             PB2=quant(np.round(L5 + RATIO * (tap + 4 * np.sign(tap) - L4))).astype(float),
             INV5=(tap + quant(I5) - quant(L4)).astype(float),
             INV4=(tap + quant(I4) - quant(L4)).astype(float))
    return FF, TRIM, S, dict(N4=N4, L4=L4, L5=L5, I5=I5, I4=I4)


def ols(y, FF, TR, extra=None):
    cols = [np.ones_like(FF), FF, TR] + ([] if extra is None else [extra])
    A = np.vstack(cols).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return coef


# ---------------------------------------------------------------------------------------------------------------
print("\n[I0] reproduction of the REAL tap by my V294 march, hands-off settled engaged frames (rms counts), by delta / x mode")
best = None
for dms, xm in ((-8, "lin"), (-4, "lin"), (0, "lin"), (2, "lin"), (4, "lin"), (6, "lin"), (8, "lin"), (0, "zoh"), (4, "zoh")):
    M = load_m(dms, xm)
    FF, TR, S, raw = series(M)
    r_live = np.sqrt(np.mean((tap - quant(raw["L4"]))[HO] ** 2))
    r_null = np.sqrt(np.mean((tap - quant(raw["N4"]))[HO] ** 2))
    r_inv = np.sqrt(np.mean((tap - quant(raw["I4"]))[HO] ** 2))
    r_all = np.sqrt(np.mean((tap - quant(raw["L4"]))[E_ok] ** 2))
    big = HO & (np.abs(raw["L4"] - raw["N4"]) >= 24)
    rb = [np.sqrt(np.mean((tap - quant(raw[k]))[big] ** 2)) for k in ("L4", "N4", "I4")]
    print("   delta %+d ms x %s: HO rms live %.2f | FF-only %.2f | inverted %.2f ; all-engaged live %.2f ;"
          " |trim|>=24 frames (%d): live %.1f FF-only %.1f inv %.1f"
          % (dms, xm, r_live, r_null, r_inv, r_all, big.sum(), *rb))
    if best is None or r_live < best[0]:
        best = (r_live, dms, xm)
print("   best alignment: delta %+d ms, x %s (HO rms %.2f)" % (best[1], best[2], best[0]))
DB, XB = best[1], best[2]


# ---------------------------------------------------------------------------------------------------------------
def windows_exposure(mask, secs):
    idx = np.flatnonzero(mask)
    n = int(secs * 50)
    return [idx[i:i + n] for i in range(0, len(idx) - n + 1, n)]


def windows_wallclock(secs, step=None, frac=0.9):
    step = secs if step is None else step
    out = []
    t = tap_t[0]
    while t + secs <= tap_t[-1]:
        m = (tap_t >= t) & (tap_t < t + secs)
        if m.sum() > 0 and E_ok[m].mean() >= frac:
            out.append(np.flatnonzero(m & E_ok))
        t += step
    return out


def hardturn_windows(half=10.0):
    cond = E_ok & (v_t >= 5) & (v_t < 22) & ((np.abs(plan_t) >= 1.5) | (np.abs(ang_t) > 60))
    ev = []
    last = -1e9
    for i in np.flatnonzero(cond):
        if tap_t[i] - last > 10.0:
            ev.append(i)
        last = tap_t[i]
    out_all, out_ho = [], []
    for i in ev:
        m = (tap_t >= tap_t[i] - half) & (tap_t < tap_t[i] + half)
        out_all.append(np.flatnonzero(m & E_ok))
        out_ho.append(np.flatnonzero(m & HO))
    return out_all, out_ho


def score(wins, FF, TR, S, min_frames=100, gate_trim_rms=None):
    rows = []
    for w in wins:
        if len(w) < min_frames:
            continue
        tr_rms = float(np.sqrt(np.mean(TR[w] ** 2)))
        if gate_trim_rms is not None and tr_rms < gate_trim_rms:
            continue
        row = dict(n=len(w), trim_rms=tr_rms)
        for k, y in S.items():
            c = ols(y[w], FF[w], TR[w])
            row[k] = (float(c[1]), float(c[2]))
        rows.append(row)
    return rows


def summarize(rows, label):
    if not rows:
        print("   %-26s no windows" % label)
        return {}
    out = {}
    s = "   %-26s n %3d | " % (label, len(rows))
    for k in ("NULL", "PA", "PB", "PB2", "INV5", "INV4"):
        c2 = np.array([r[k][1] for r in rows])
        c1 = np.array([r[k][0] for r in rows])
        if k == "NULL":
            err = np.mean(c2 > THR); what = "FA"
        elif k in ("PA", "PB", "PB2"):
            err = np.mean(c2 <= THR); what = "miss"
        else:
            err = np.mean(c2 >= 0); what = "c2>=0"
        out[k] = dict(c2_med=float(np.median(c2)), c2_p5=float(np.percentile(c2, 5)), c2_p95=float(np.percentile(c2, 95)),
                      c2_min=float(c2.min()), c2_max=float(c2.max()), c1_med=float(np.median(c1)),
                      c1_p5=float(np.percentile(c1, 5)), c1_p95=float(np.percentile(c1, 95)), err=float(err), what=what,
                      inv_gt_thr=float(np.mean(c2 > THR)))
        s += "%s c2 %.2f [%.2f,%.2f] %s %.3f | " % (k, np.median(c2), np.percentile(c2, 5), np.percentile(c2, 95), what, err)
    print(s)
    return out


results = {}
for dms, xm in ((DB, XB), (0, "lin"), (4, "lin"), (-4, "lin"), (8, "lin"), (0, "zoh")):
    M = load_m(dms, xm)
    FF, TR, S, raw = series(M)
    key = "d%+d_%s" % (dms, xm)
    print("\n[I1-I3, I6] per-window c1/c2, delta %+d ms, x %s   (FA = null c2 > %.2f ; miss = c2 <= %.2f ; inverted c2 >= 0)"
          % (dms, xm, THR, THR))
    results[key] = {}
    for label, wins in (("HO 15 s (exposure)", windows_exposure(HO, 15)), ("HO 30 s (exposure)", windows_exposure(HO, 30)),
                        ("HO|bar|<400 15 s", windows_exposure(HO_bar, 15)), ("HO|bar|<400 30 s", windows_exposure(HO_bar, 30)),
                        ("HO 10 s (exposure)", windows_exposure(HO, 10)), ("HO 5 s (exposure)", windows_exposure(HO, 5)),
                        ("ALL 15 s contiguous", windows_wallclock(15)), ("ALL 30 s contiguous", windows_wallclock(30)),
                        ("ALL 15 s sliding 2.5 s", windows_wallclock(15, 2.5))):
        results[key][label] = summarize(score(wins, FF, TR, S), label)
    ht_all, ht_ho = hardturn_windows()
    results[key]["HT +-10 s all engaged"] = summarize(score(ht_all, FF, TR, S), "HT +-10 s all engaged")
    results[key]["HT +-10 s hands-off"] = summarize(score(ht_ho, FF, TR, S, min_frames=200), "HT +-10 s hands-off (>=4 s)")
    # pooled, block bootstrap over 10 s blocks of hands-off frames
    idx = np.flatnonzero(HO)
    blocks = [idx[i:i + 500] for i in range(0, len(idx), 500)]
    pooled = {}
    for k, y in S.items():
        c = ols(y[idx], FF[idx], TR[idx])
        bs = []
        for _ in range(400):
            pick = rng.integers(0, len(blocks), len(blocks))
            ii = np.concatenate([blocks[p] for p in pick])
            bs.append(ols(y[ii], FF[ii], TR[ii])[2])
        pooled[k] = (float(c[1]), float(c[2]), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    print("   POOLED hands-off (%.0f s, 10 s block bootstrap): " % (len(idx) / 50) +
          " | ".join("%s c1 %.3f c2 %.3f [%.3f, %.3f]" % (k, *v) for k, v in pooled.items()))
    results[key]["pooled"] = pooled

# ---------------------------------------------------------------------------------------------------------------
print("\n[I4] alignment: does the -4 / 0 / +4 ms choice flip the call?  (HO 15 s windows, same frames)")
calls = {}
for dms in (-4, 0, 4, 8):
    M = load_m(dms, "lin")
    FF, TR, S, raw = series(M)
    rows = score(windows_exposure(HO, 15), FF, TR, S)
    calls[dms] = dict(NULL=np.array([r["NULL"][1] for r in rows]), PA=np.array([r["PA"][1] for r in rows]))
for a, b in ((-4, 0), (0, 4), (4, 8), (-4, 4)):
    for k in ("NULL", "PA"):
        fa, fb = calls[a][k], calls[b][k]
        flip = np.mean((fa > THR) != (fb > THR))
        print("   delta %+d vs %+d  %-4s: median c2 %.3f vs %.3f (diff %.3f), call flips on %.3f of %d windows, max |dc2| %.3f"
              % (a, b, k, np.median(fa), np.median(fb), np.median(fb) - np.median(fa), flip, len(fa), np.max(np.abs(fb - fa))))

# ---------------------------------------------------------------------------------------------------------------
print("\n[I3b] trim excitation vs c2 scatter (best alignment, HO 15 s): does a minimum-trim gate help?")
M = load_m(DB, XB)
FF, TR, S, raw = series(M)
rows = score(windows_exposure(HO, 15), FF, TR, S)
tr = np.array([r["trim_rms"] for r in rows])
for lo, hi in ((0, 4), (4, 6), (6, 10), (10, 100)):
    m = (tr >= lo) & (tr < hi)
    if m.sum():
        print("   trim rms %2d-%3d counts: n %2d  NULL c2 %s  PA c2 %s" % (
            lo, hi, m.sum(), np.round(np.array([r["NULL"][1] for r in rows])[m], 2),
            np.round(np.array([r["PA"][1] for r in rows])[m], 2)))

# quantised regressors and a truncation-bias term, pooled
idx = np.flatnonzero(HO)
FFq = quant(raw["N4"]).astype(float); TRq = (quant(raw["L4"]) - quant(raw["N4"])).astype(float)
for k in ("NULL", "PA", "INV5"):
    y = S[k]
    c_a = ols(y[idx], FF[idx], TR[idx])
    c_b = ols(y[idx], FFq[idx], TRq[idx])
    c_c = ols(y[idx], FF[idx], TR[idx], extra=np.sign(FF[idx]))
    print("   pooled HO %-5s: continuous regressors c1 %.3f c2 %.3f | quantised regressors c1 %.3f c2 %.3f | + sign(FF) term"
          " c1 %.3f c2 %.3f" % (k, c_a[1], c_a[2], c_b[1], c_b[2], c_c[1], c_c[2]))

print("\n[I3c] the same windows GATED on excitation: a window is scored only if rms(TRIM_V294 regressor) >= 4 counts"
      " (half a tap LSB); best alignment")
M = load_m(DB, XB)
FF, TR, S, raw = series(M)
for label, wins in (("HO 5 s gated", windows_exposure(HO, 5)), ("HO 10 s gated", windows_exposure(HO, 10)),
                    ("HO 15 s gated", windows_exposure(HO, 15)), ("HO 30 s gated", windows_exposure(HO, 30)),
                    ("ALL 15 s gated", windows_wallclock(15)), ("ALL 30 s gated", windows_wallclock(30)),
                    ("ALL 15 s sliding gated", windows_wallclock(15, 2.5))):
    nall = len([w for w in wins if len(w) >= 100])
    rows = score(wins, FF, TR, S, gate_trim_rms=4.0)
    print("   (%d of %d windows qualify)" % (len(rows), nall))
    results.setdefault("gated", {})[label] = summarize(rows, label)

print("\n[I3d] the C clamp: V295 r26 at +-C on r71b's recorded motion, and c2 on the top-trim frames")
from advb_lane import Lane, cells_from_image  # noqa: E402
c5 = cells_from_image("V295"); c4 = cells_from_image("V294")
xs = M["x"].astype(int).tolist()
for nm, c in (("V294", c4), ("V295", c5)):
    s_, sent, nclamp, nt = 0, 0, 0, 0
    for k, x in enumerate(xs):
        s_new = ((c["a"] * s_) >> 10) + ((x * c["b"]) >> 10)
        r = s_new - s_
        s_ = s_new
        if abs(r) >= c["C"]:
            nclamp += 1
    print("   %s: r26 at the clamp on %d of %d route ticks (%.5f %%)" % (nm, nclamp, len(xs), 100.0 * nclamp / len(xs)))
idx = np.flatnonzero(HO)
big = idx[np.abs(TR[idx]) >= np.percentile(np.abs(TR[idx]), 95)]
for k in ("NULL", "PA"):
    c = ols(S[k][big], FF[big], TR[big])
    print("   top-5 %% |TRIM| hands-off frames (%d): %s c1 %.3f c2 %.3f" % (len(big), k, c[1], c[2]))

json.dump(results, open(os.path.join(HERE, "b5_instrument_out.json"), "w"), indent=1)
np.savez_compressed(os.path.join(HERE, "_scratch", "b5_frames.npz"), HO=HO, E_ok=E_ok, tap_t=tap_t, v_t=v_t, pr=pr)
print("\nbest alignment used for [I3b]: delta %+d x %s" % (DB, XB))
