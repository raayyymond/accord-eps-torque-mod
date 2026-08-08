#!/usr/bin/env python3
"""T4 (the highway instability), T5 (the two grinding scenarios) and T7 (coverage) for route 67.

Operator report being explained:
  1. Grinding audible in (a) turning AND braking -- slow right turn at stops, and
     (b) highway lane change.
  2. ALL grinding stopped the INSTANT LKAS was disengaged; the highway grind persisted for
     multiple seconds while engaged; adding hand mass did NOT help.
  3. Highway instability was the WORST part of the drive.

Everything spectral reuses the kit's own instrument: `_grind2_lib.win_env` (p99 analytic band
envelope, linear-detrend + Hann + central 60% with the taper divided back out), `_grind2_lib.locate`
(prominence argmax, sub-bin refined) and `_r31_common.periodogram`. NFFT 256 / hop 128 as everywhere
else. CIs resample EPISODES; every ratio is quoted against a SPLIT-HALF NULL.

🛑 ALIASING. fs = 100.49 Hz on route 67, so Nyquist is 50.2 Hz and a line at f is indistinguishable
from 100.49 - f and 100.49 + f. Stated on every identification, never silently.
🛑 MATCHED SPEED. A wheel order moves with speed, so an "only on route X" line can be manufactured
by an unmatched speed distribution. Every cross-route band comparison here carries a PER-WINDOW
speed census, not just a band-centre check.

Usage:  python r67_v81_t4t5.py [t4|t5|t7|all]
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G  # noqa: E402
import _r31_common as C31  # noqa: E402

KMH = 1.0 / 3.6
NFFT, HOP = G.NFFT, G.HOP
CIRC = 2.0805                 # tyre circumference, m -- the kit's own value (order 1 = v / CIRC)
RNG = np.random.default_rng(674)
OUT = {}

ROUTES = {
    "V81/r67": (ROOT / "_cache_r67x", "r67xs", list(range(14)), [13]),
    "V80/r66": (ROOT / "_cache_r66x", "r66xs", list(range(15)), []),
    "V76/r65": (ROOT / "_cache_r65", "r65s", list(range(11)), [0, 10]),
    "V75/r5e": (ROOT / "_cache_r5e_sym", "r5es", [0, 1, 2, 3, 4], [0]),
}
ORDER = ["V76/r65", "V75/r5e", "V81/r67", "V80/r66"]
BANDS = {"6-9": (6.0, 9.0), "18-22": (18.0, 22.0), "26-31": (26.0, 31.0),
         "32-38": (32.0, 38.0), "40-49": (40.0, 49.0), "5-49": (5.0, 49.0)}
HWY = 80 * KMH


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108, flush=True)


def segs(build):
    cache, pfx, ss, parked = ROUTES[build]
    for s in ss:
        p = cache / f"{pfx}{s}.npz"
        if p.exists() and s not in parked:
            yield s, {k: v for k, v in np.load(p).items()}


def lowpass(x, fs, fc=3.0):
    y = np.asarray(x, float).copy()
    bad = ~np.isfinite(y)
    if bad.all() or len(y) < 8:
        return y
    if bad.any():
        y[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), y[~bad])
    mu = y.mean()
    X = np.fft.rfft(y - mu)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    X[f > fc] = 0.0
    return np.fft.irfft(X, n=len(y)) + mu


def env(x, fs, lo, hi):
    """Continuous analytic band envelope -- for edge traces, where a window grid is too coarse."""
    y = np.asarray(x, float).copy()
    bad = ~np.isfinite(y)
    if bad.all() or len(y) < 16:
        return np.full(len(y), np.nan)
    if bad.any():
        y[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), y[~bad])
    X = np.fft.rfft(y - y.mean())
    f = np.fft.rfftfreq(len(y), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(y)))


def runs_of(sel):
    s = np.asarray(sel, bool)
    if not s.any():
        return []
    e = np.diff(np.concatenate(([0], s.view(np.int8), [0])))
    return list(zip(np.flatnonzero(e > 0), np.flatnonzero(e < 0)))


def windows(build, chan="tq", extra=()):
    """Window records cut inside contiguous runs of the ENGAGEMENT mask -- the same rule as
    `_grind2_lib.wrecs`, with the covariates T4/T5 need and the periodogram kept."""
    out = []
    for s, d in segs(build):
        fs = C31.fs_of(d)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        taper = np.hanning(NFFT) + 1e-3
        cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
        lat = d["cc_lat"] > 0.5
        tq_lf = lowpass(d["tq"], fs)
        ang_lf = lowpass(d["ang"], fs)
        rate_lf = np.gradient(ang_lf) * fs
        x = np.asarray(d[chan], float)
        for eng, mask in ((1, lat), (0, ~lat)):
            for a, b in C31.runs_of(mask, d["t"], NFFT):
                nwin = 0
                for i in range(a, b - NFFT + 1, HOP):
                    xw = x[i:i + NFFT]
                    if not np.all(np.isfinite(xw)):
                        continue
                    P = C31.periodogram(xw, fs, NFFT, True)
                    if P is None:
                        continue
                    R = G.prom_spectrum(f, P)
                    sl = slice(i, i + NFFT)
                    r = dict(build=build, seg=int(s), eng=eng, fs=fs, t0=float(d["t"][i]),
                             ep=(build, int(s), int(a), int(b)),
                             blk=(build, int(s), int(a), int(b), nwin // 8))
                    for k, (lo, hi) in BANDS.items():
                        r["e_" + k] = G.win_env(xw, fs, lo, hi, taper, cw)
                    r["f0"], r["prom0"] = G.locate(f, P, 12.0, 35.0, R=R)
                    r["f0w"], r["prom0w"] = G.locate(f, P, 5.0, 49.0, R=R)
                    r["Q0"] = G.q_of(f, P, r["f0"])
                    r["v"] = float(np.mean(np.abs(d["cs_v"][sl])))
                    r["vsd"] = float(np.std(np.abs(d["cs_v"][sl])))
                    r["vmin"] = float(np.min(np.abs(d["cs_v"][sl])))
                    r["vmax"] = float(np.max(np.abs(d["cs_v"][sl])))
                    r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
                    r["angs"] = float(np.mean(d["ang"][sl]))
                    r["eff"] = float(np.mean(np.abs(tq_lf[sl])))
                    r["rate"] = float(np.mean(np.abs(rate_lf[sl])))
                    r["e4"] = float(np.mean(np.abs(d["e4tq"][sl])))
                    r["press"] = float(np.mean(d["cs_press"][sl] > 0.5)) \
                        if "cs_press" in d else np.nan
                    r["lchg"] = float(np.max(d["cs_lchg"][sl])) if "cs_lchg" in d else np.nan
                    r["brake"] = float(np.mean(d["cs_brake"][sl] > 0.5)) \
                        if "cs_brake" in d else np.nan
                    r["accel"] = float((np.abs(d["cs_v"][sl])[-1] - np.abs(d["cs_v"][sl])[0])
                                       / (NFFT / fs))
                    r["imu"] = (G.win_env(np.asarray(d["imu_vert"][sl], float), fs, 18.0, 30.0,
                                          taper, cw)
                                if "imu_vert" in d and np.all(np.isfinite(d["imu_vert"][sl]))
                                else np.nan)
                    r["e4hf"] = G.win_env(np.asarray(d["e4tq"][sl], float), fs, 18.0, 30.0,
                                          taper, cw)
                    r["anghf"] = G.win_env(np.asarray(d["ang"][sl], float), fs, 18.0, 30.0,
                                           taper, cw)
                    for k in extra:
                        r[k] = float(np.mean(d[k][sl])) if k in d else np.nan
                    r["w1"] = r["v"] / CIRC
                    r["w2"] = 2 * r["v"] / CIRC
                    nwin += 1
                    out.append(r)
    return out


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def ep_boot(rs, key, stat=np.median, nboot=1500, unit="blk"):
    grp = {}
    for r in rs:
        v = r[key]
        if np.isfinite(v):
            grp.setdefault(r[unit], []).append(v)
    per = [np.array(v) for v in grp.values()]
    if not per:
        return np.nan, np.nan, np.nan, 0
    allv = np.concatenate(per)
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        v = np.concatenate([per[j] for j in RNG.integers(0, len(per), len(per))])
        dr[b] = stat(v)
    return (float(stat(allv)), float(np.nanpercentile(dr, 2.5)),
            float(np.nanpercentile(dr, 97.5)), len(per))


def ratio_null(rsA, rsB, key, unit="blk", nboot=1200):
    """(ratio, lo, hi) of medians + the split-half null of pool A, both block-resampled."""
    def pools(rs):
        g = {}
        for r in rs:
            v = r[key]
            if np.isfinite(v):
                g.setdefault(r[unit], []).append(v)
        return [np.array(v) for v in g.values()]
    pa, pb = pools(rsA), pools(rsB)
    if not pa or not pb:
        return (np.nan,) * 3, (np.nan,) * 3
    ma, mb = np.median(np.concatenate(pa)), np.median(np.concatenate(pb))
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        a = np.concatenate([pa[j] for j in RNG.integers(0, len(pa), len(pa))])
        c = np.concatenate([pb[j] for j in RNG.integers(0, len(pb), len(pb))])
        if np.median(c) > 0:
            dr[b] = np.median(a) / np.median(c)
    nulls = []
    for _ in range(300):
        idx = RNG.permutation(len(pa))
        h = len(pa) // 2
        if h < 2:
            break
        u = np.concatenate([pa[i] for i in idx[:h]])
        w = np.concatenate([pa[i] for i in idx[h:]])
        if np.median(w) > 0:
            nulls.append(np.median(u) / np.median(w))
    nulls = np.array(nulls, float)
    nl = ((float(np.median(nulls)), float(np.percentile(nulls, 2.5)),
           float(np.percentile(nulls, 97.5))) if len(nulls) else (np.nan,) * 3)
    return ((ma / mb if mb else np.nan, float(np.nanpercentile(dr, 2.5)),
             float(np.nanpercentile(dr, 97.5))), nl)


def theil_sen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 3:
        return np.nan
    sl = []
    for i in range(len(x)):
        dx, dy = x[i + 1:] - x[i], y[i + 1:] - y[i]
        ok = dx != 0
        sl.append(dy[ok] / dx[ok])
    sl = np.concatenate(sl) if sl else np.array([])
    return float(np.median(sl)) if len(sl) else np.nan


def ts_boot(rs, xk, yk, nboot=600, unit="blk"):
    grp = {}
    for r in rs:
        grp.setdefault(r[unit], []).append(r)
    per = list(grp.values())
    pt = theil_sen(col(rs, xk), col(rs, yk))
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        rr = [r for j in RNG.integers(0, len(per), len(per)) for r in per[j]]
        dr[b] = theil_sen(col(rr, xk), col(rr, yk))
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def medspec(rs, build, lo_f=2.0, hi_f=50.0):
    """Median periodogram + median prominence spectrum over a set of window records, re-sliced
    from each window's own cache at its own t0 -- so it cannot drift from the band table."""
    cache, pfx, _, _ = ROUTES[build]
    by = {}
    for r in rs:
        by.setdefault(r["seg"], []).append(r)
    Ps, Rs, fref = [], [], None
    for s, group in by.items():
        d = {k: v for k, v in np.load(cache / f"{pfx}{s}.npz").items()}
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        tq = np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        for r in group:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            xw = tq[i0:i0 + NFFT]
            if len(xw) < NFFT or not np.all(np.isfinite(xw)):
                continue
            P = C31.periodogram(xw, fs, NFFT, True)
            if P is None:
                continue
            Ps.append(P)
            Rs.append(G.prom_spectrum(f, P))
            fref = f
    if not Ps:
        return None, None, None
    P = np.nanmedian(np.array(Ps), axis=0)
    R = np.nanmedian(np.array(Rs), axis=0)
    m = (fref >= lo_f) & (fref <= hi_f)
    return fref[m], P[m], R[m]


def top_lines(f, R, n=6, minsep=1.5):
    idx = np.argsort(np.where(np.isfinite(R), R, -np.inf))[::-1]
    picked = []
    for j in idx:
        if not np.isfinite(R[j]):
            continue
        if all(abs(f[j] - f[k]) > minsep for k in picked):
            picked.append(j)
        if len(picked) >= n:
            break
    return [(float(f[j]), float(R[j])) for j in sorted(picked, key=lambda j: -R[j])]


# =================================================================================================
def t4(W):
    hdr("T4a  THE HIGHWAY BAND (>80 km/h, ENGAGED) -- median prominence spectrum per build.\n"
        "     🛑 fs = 100.5 Hz => a line at f is indistinguishable from 100.5 - f. Every f below\n"
        "     also reads as its alias; the kit's 27.4 / 28 / 40-49 Hz claims carry the same caveat.")
    OUT["t4a"] = {}
    for b in ORDER:
        hw = [r for r in W[b] if r["eng"] == 1 and r["v"] >= HWY]
        if len(hw) < 5:
            print(f"  {b:10s} -- only {len(hw)} engaged windows above 80 km/h")
            OUT["t4a"][b] = dict(n=len(hw))
            continue
        f, P, R = medspec(hw, b)
        lines = top_lines(f, R)
        vs = col(hw, "v")
        print(f"\n  ---- {b}  n={len(hw)} windows ({len(hw) * 1.28:.0f} s), "
              f"v {np.percentile(vs,5)*3.6:.1f}-{np.percentile(vs,95)*3.6:.1f} km/h "
              f"(median {np.median(vs)*3.6:.1f}) ----")
        print("     top prominence lines (Hz, prom): "
              + "  ".join(f"{a:5.2f} ({p:5.2f})" for a, p in lines))
        print(f"     wheel order 1 at median v = {np.median(vs) / CIRC:5.2f} Hz, "
              f"order 2 = {2 * np.median(vs) / CIRC:5.2f} Hz, order 3 = "
              f"{3 * np.median(vs) / CIRC:5.2f} Hz")
        row = {}
        for k in BANDS:
            e = ep_boot(hw, "e_" + k)
            row[k] = list(e)
            print(f"     e_{k:6s} {e[0]:9.1f} [{e[1]:8.1f},{e[2]:8.1f}]  blk={e[3]}")
        f0 = ep_boot(hw, "f0")
        q0 = ep_boot(hw, "Q0")
        print(f"     f0 (free 12-35 Hz argmax) {f0[0]:6.2f} [{f0[1]:5.2f},{f0[2]:5.2f}] Hz   "
              f"Q {q0[0]:5.2f} [{q0[1]:5.2f},{q0[2]:5.2f}]")
        OUT["t4a"][b] = dict(n=len(hw), lines=lines, bands=row, f0=list(f0), Q=list(q0),
                             v_med=float(np.median(vs)))

    hdr("T4a2  THE SAME BANDS, V81 vs each other build, >80 km/h ENGAGED only, with the\n"
        "      SPLIT-HALF NULL of V81's own pool beside each ratio.")
    hw81 = [r for r in W["V81/r67"] if r["eng"] == 1 and r["v"] >= HWY]
    OUT["t4a2"] = {}
    for b in ORDER:
        if b == "V81/r67":
            continue
        other = [r for r in W[b] if r["eng"] == 1 and r["v"] >= HWY]
        if len(other) < 8:
            print(f"  V81/{b.split('/')[0]:4s}  -- other build has only {len(other)} windows")
            continue
        for k in ("18-22", "26-31", "32-38", "40-49"):
            (ra, lo, hi), nl = ratio_null(hw81, other, "e_" + k)
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (ra < nl[1] or ra > nl[2]))
                 else "inside null")
            print(f"  {k:6s} V81/{b.split('/')[0]:4s} {ra:7.3f} [{lo:7.3f},{hi:7.3f}]  "
                  f"null [{nl[1]:6.3f},{nl[2]:6.3f}]  {v}")
            OUT["t4a2"][f"{k}|{b}"] = dict(ratio=[ra, lo, hi], null=list(nl))
        vA, vB = col(hw81, "v") * 3.6, col(other, "v") * 3.6
        print(f"     per-window speed census  V81 p5/p50/p95 = {np.percentile(vA,5):.1f}/"
              f"{np.percentile(vA,50):.1f}/{np.percentile(vA,95):.1f} km/h   "
              f"{b.split('/')[0]} = {np.percentile(vB,5):.1f}/{np.percentile(vB,50):.1f}/"
              f"{np.percentile(vB,95):.1f}")

    hdr("T4b  ENGAGEMENT EDGES -- does the oscillation die the INSTANT LKAS goes off?\n"
        "     4 s before vs 4 s after every latActive falling edge, and the mirror for rising.\n"
        "     ⚠ CONFOUND, reported not assumed: a disengagement is usually the driver grabbing\n"
        "     the wheel, so |tq_lf| and speed are reported across the same edge.")
    OUT["t4b"] = {}
    for b in ORDER:
        pre, post, taus, dtq, dv, nedge = [], [], [], [], [], 0
        prehw, posthw = [], []
        for s, d in segs(b):
            fs = C31.fs_of(d)
            n = len(d["t"])
            lat = d["cc_lat"] > 0.5
            e18 = env(d["tq"], fs, 18.0, 31.0)
            tq_lf = np.abs(lowpass(d["tq"], fs))
            W4 = int(4 * fs)
            edges = np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1
            for i in edges:
                if i - W4 < 0 or i + W4 >= n:
                    continue
                if lat[max(0, i - W4):i].mean() < 0.95 or lat[i:i + W4].mean() > 0.05:
                    continue
                a0 = float(np.percentile(e18[i - W4:i], 90))
                a1 = float(np.percentile(e18[i:i + W4], 90))
                pre.append(a0); post.append(a1); nedge += 1
                dtq.append(float(np.median(tq_lf[i:i + W4]) - np.median(tq_lf[i - W4:i])))
                dv.append(float(np.mean(np.abs(d["cs_v"][i:i + W4]))
                                - np.mean(np.abs(d["cs_v"][i - W4:i]))))
                if np.mean(np.abs(d["cs_v"][i - W4:i])) >= HWY:
                    prehw.append(a0); posthw.append(a1)
                # decay time: first sample after the edge where the envelope drops below
                # half its pre-edge p90 and stays there for 0.2 s
                thr = 0.5 * a0
                seg_ = e18[i:i + W4]
                below = seg_ < thr
                tau = np.nan
                for j in range(len(below) - int(0.2 * fs)):
                    if below[j:j + int(0.2 * fs)].all():
                        tau = j / fs
                        break
                taus.append(tau)
        if nedge == 0:
            print(f"  {b:10s} -- no clean falling edge with 4 s either side")
            continue
        pre, post = np.array(pre), np.array(post)
        rat = post / np.maximum(pre, 1e-9)
        print(f"  {b:10s} {nedge} clean falling edges | 18-31 Hz p90 envelope  "
              f"pre {np.median(pre):8.1f}  post {np.median(post):8.1f}  "
              f"median post/pre {np.median(rat):6.3f}  "
              f"[{np.percentile(rat,25):.3f}, {np.percentile(rat,75):.3f}]")
        tt = np.array(taus, float)
        print(f"             decay to half: median {np.nanmedian(tt):5.2f} s  "
              f"({int(np.sum(np.isfinite(tt)))}/{nedge} edges ever reached half)   "
              f"driver |tq_lf| change {np.median(dtq):+7.0f} ct   "
              f"speed change {np.median(dv):+5.2f} m/s")
        if prehw:
            ph, qh = np.array(prehw), np.array(posthw)
            print(f"             of which >80 km/h: {len(ph)} edges, pre {np.median(ph):8.1f} "
                  f"post {np.median(qh):8.1f} ratio {np.median(qh / np.maximum(ph,1e-9)):6.3f}")
        OUT["t4b"][b] = dict(n=nedge, pre=float(np.median(pre)), post=float(np.median(post)),
                             ratio=float(np.median(rat)),
                             tau=float(np.nanmedian(tt)),
                             tau_n=int(np.sum(np.isfinite(tt))),
                             dtq=float(np.median(dtq)), dv=float(np.median(dv)),
                             hw_n=len(prehw))

    hdr("T4c  DOES HAND MASS HELP?  ENGAGED windows split by driver effort.  A mechanical\n"
        "     resonance is damped by added mass/impedance; a control-loop limit cycle is not.")
    OUT["t4c"] = {}
    for b in ORDER:
        for tag, sel in (("ALL engaged", lambda r: r["eng"] == 1),
                         (">80 km/h", lambda r: r["eng"] == 1 and r["v"] >= HWY)):
            rs = [r for r in W[b] if sel(r)]
            lo_ = [r for r in rs if r["eff"] < 200]
            hi_ = [r for r in rs if r["eff"] > 800]
            if len(lo_) < 8 or len(hi_) < 8:
                print(f"  {b:10s} {tag:12s} -- n hands-off {len(lo_)}, hands-on {len(hi_)}")
                continue
            (ra, l_, h_), nl = ratio_null(hi_, lo_, "e_18-22")
            (rb, l2, h2), nl2 = ratio_null(hi_, lo_, "e_26-31")
            print(f"  {b:10s} {tag:12s} handsON/handsOFF  18-22 {ra:6.3f} [{l_:6.3f},{h_:6.3f}] "
                  f"null [{nl[1]:5.3f},{nl[2]:5.3f}] | 26-31 {rb:6.3f} [{l2:6.3f},{h2:6.3f}] "
                  f"null [{nl2[1]:5.3f},{nl2[2]:5.3f}]  n {len(hi_)}/{len(lo_)}")
            OUT["t4c"][f"{b}|{tag}"] = dict(r18=[ra, l_, h_], null18=list(nl),
                                            r26=[rb, l2, h2], n=[len(hi_), len(lo_)])

    hdr("T4d  FALSIFIERS.  (i) wheel order: d f0 / d v against +0.481 (order 1) and +0.961\n"
        "     (order 2) Hz per m/s.  (ii) IMU vertical 18-30 Hz -- a rougher road.  (iii) the\n"
        "     0x0E4 COMMAND's own 18-30 Hz content -- is the line being commanded?")
    OUT["t4d"] = {}
    for b in ORDER:
        rs = [r for r in W[b] if r["eng"] == 1 and np.isfinite(r["f0"])]
        if len(rs) < 20:
            continue
        sv = ts_boot(rs, "v", "f0")
        print(f"\n  {b:10s} d f0/d v = {sv[0]:+7.4f} [{sv[1]:+7.4f},{sv[2]:+7.4f}] Hz/(m/s)   "
              f"order1 {'EXCLUDED' if (sv[2] < 0.481 or sv[1] > 0.481) else 'not excluded'}   "
              f"order2 {'EXCLUDED' if (sv[2] < 0.961 or sv[1] > 0.961) else 'not excluded'}")
        for k, lab in (("imu", "IMU vert 18-30"), ("e4hf", "0x0E4 cmd 18-30"),
                       ("anghf", "angle 18-30")):
            x, y = col(rs, k), col(rs, "e_18-22")
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 20:
                continue
            c = float(np.corrcoef(np.log(np.maximum(x[m], 1e-9)),
                                  np.log(np.maximum(y[m], 1e-9)))[0, 1])
            print(f"             {lab:16s} median {np.nanmedian(x):10.4f}   "
                  f"log-log corr with e_18-22 = {c:+.3f}")
            OUT["t4d"].setdefault(b, {})[k] = dict(med=float(np.nanmedian(x)), corr=c)
        OUT["t4d"].setdefault(b, {})["slope_v"] = list(sv)
        hw = [r for r in rs if r["v"] >= HWY]
        if len(hw) >= 10:
            print(f"             >80 km/h only: IMU {np.nanmedian(col(hw,'imu')):10.4f}  "
                  f"cmd18-30 {np.nanmedian(col(hw,'e4hf')):8.2f}  "
                  f"tq18-22 {np.nanmedian(col(hw,'e_18-22')):8.1f}  "
                  f"tq26-31 {np.nanmedian(col(hw,'e_26-31')):8.1f}")

    hdr("T4e  LANE-CHANGE WINDOWS on V81 (blinker up while engaged) vs engaged non-lane-change\n"
        "     at MATCHED speed (>= 40 km/h).")
    rs = [r for r in W["V81/r67"] if r["eng"] == 1 and r["v"] >= 40 * KMH]
    lc = [r for r in rs if r["lchg"] > 0.5]
    nl_ = [r for r in rs if r["lchg"] <= 0.5]
    print(f"  lane-change windows {len(lc)} ({len(lc) * 1.28:.0f} s)   "
          f"other {len(nl_)} ({len(nl_) * 1.28:.0f} s)")
    if len(lc) >= 8:
        vA, vB = col(lc, "v") * 3.6, col(nl_, "v") * 3.6
        print(f"  speed census  LC p5/p50/p95 {np.percentile(vA,5):.1f}/"
              f"{np.percentile(vA,50):.1f}/{np.percentile(vA,95):.1f}  vs other "
              f"{np.percentile(vB,5):.1f}/{np.percentile(vB,50):.1f}/{np.percentile(vB,95):.1f}")
        for k in ("6-9", "18-22", "26-31", "32-38", "40-49"):
            (ra, l_, h_), nl = ratio_null(lc, nl_, "e_" + k)
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (ra < nl[1] or ra > nl[2]))
                 else "inside null")
            print(f"    {k:6s} LC/other {ra:6.3f} [{l_:6.3f},{h_:6.3f}]  "
                  f"null [{nl[1]:6.3f},{nl[2]:6.3f}]  {v}")
            OUT.setdefault("t4e", {})[k] = dict(ratio=[ra, l_, h_], null=list(nl))
        f, P, R = medspec(lc, "V81/r67")
        if f is not None:
            print("    lane-change top lines: "
                  + "  ".join(f"{a:5.2f} ({p:5.2f})" for a, p in top_lines(f, R)))


# =================================================================================================
def t5(W):
    hdr("T5a  TURNING + BRAKING AT LOW SPEED (operator scenario a).  ENGAGED, v < 15 km/h,\n"
        "     the driver/LKAS actually turning (|angle rate| >= 3 deg/s).  Brake vs no brake.")
    rs = [r for r in W["V81/r67"] if r["eng"] == 1 and r["v"] < 15 * KMH and r["rate"] >= 3.0]
    br = [r for r in rs if r["brake"] > 0.5]
    nb = [r for r in rs if r["brake"] < 0.1]
    print(f"  low-speed turning ENGAGED windows: {len(rs)}   brake {len(br)}   no-brake {len(nb)}")
    OUT["t5a"] = {}
    if len(br) >= 8 and len(nb) >= 8:
        print(f"  speed census   brake p50 {np.median(col(br,'v'))*3.6:.1f} km/h   "
              f"no-brake p50 {np.median(col(nb,'v'))*3.6:.1f} km/h")
        print(f"  effort census  brake p50 {np.median(col(br,'eff')):.0f} ct   "
              f"no-brake p50 {np.median(col(nb,'eff')):.0f} ct")
        for k in ("6-9", "18-22", "26-31", "32-38", "40-49"):
            (ra, l_, h_), nl = ratio_null(br, nb, "e_" + k)
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (ra < nl[1] or ra > nl[2]))
                 else "inside null")
            print(f"    {k:6s} brake/no-brake {ra:6.3f} [{l_:6.3f},{h_:6.3f}]  "
                  f"null [{nl[1]:6.3f},{nl[2]:6.3f}]  {v}   "
                  f"med brake {np.nanmedian(col(br,'e_'+k)):8.1f} / "
                  f"no-brake {np.nanmedian(col(nb,'e_'+k)):8.1f}")
            OUT["t5a"][k] = dict(ratio=[ra, l_, h_], null=list(nl))
        f, P, R = medspec(br, "V81/r67")
        if f is not None:
            print("  brake-while-turning top lines: "
                  + "  ".join(f"{a:5.2f} ({p:5.2f})" for a, p in top_lines(f, R)))
        f, P, R = medspec(nb, "V81/r67")
        if f is not None:
            print("  no-brake  turning top lines: "
                  + "  ".join(f"{a:5.2f} ({p:5.2f})" for a, p in top_lines(f, R)))

    hdr("T5b  SIGN ASYMMETRY -- is it right-turn specific?  Sign convention checked against\n"
        "     yawRate, not assumed.")
    d0 = {k: v for k, v in np.load(ROUTES["V81/r67"][0] / "r67xs5.npz").items()}
    c = float(np.corrcoef(d0["ang"], d0["cs_yaw"])[0, 1])
    print(f"  corr(steering angle, yawRate) on seg5 = {c:+.4f}  => positive angle is a "
          f"{'LEFT' if c > 0 else 'RIGHT'} turn")
    LEFT = 1.0 if c > 0 else -1.0
    for lab, sel in (("low-speed turning", lambda r: r["v"] < 15 * KMH and r["rate"] >= 3.0),
                     ("all engaged", lambda r: True)):
        rs = [r for r in W["V81/r67"] if r["eng"] == 1 and sel(r) and abs(r["angs"]) > 2]
        L = [r for r in rs if LEFT * r["angs"] > 0]
        Rt = [r for r in rs if LEFT * r["angs"] < 0]
        if len(L) < 8 or len(Rt) < 8:
            print(f"  {lab:20s} -- L {len(L)} R {len(Rt)}: too few")
            continue
        print(f"  {lab:20s} n left {len(L)}  right {len(Rt)}")
        for k in ("18-22", "26-31", "40-49"):
            (ra, l_, h_), nl = ratio_null(Rt, L, "e_" + k)
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (ra < nl[1] or ra > nl[2]))
                 else "inside null")
            print(f"    {k:6s} RIGHT/LEFT {ra:6.3f} [{l_:6.3f},{h_:6.3f}]  "
                  f"null [{nl[1]:6.3f},{nl[2]:6.3f}]  {v}")
            OUT.setdefault("t5b", {})[f"{lab}|{k}"] = dict(ratio=[ra, l_, h_], null=list(nl))

    hdr("T5c  DECELERATION as a brake proxy, so the other three routes can be compared.\n"
        "     ENGAGED, v < 15 km/h, |angle rate| >= 3 deg/s, decelerating < -0.4 m/s^2 vs not.")
    OUT["t5c"] = {}
    for b in ORDER:
        rs = [r for r in W[b] if r["eng"] == 1 and r["v"] < 15 * KMH and r["rate"] >= 3.0]
        dec = [r for r in rs if r["accel"] < -0.4]
        oth = [r for r in rs if r["accel"] >= -0.4]
        if len(dec) < 8 or len(oth) < 8:
            print(f"  {b:10s} -- decel {len(dec)}, other {len(oth)}: too few")
            continue
        (ra, l_, h_), nl = ratio_null(dec, oth, "e_18-22")
        (rb, l2, h2), nl2 = ratio_null(dec, oth, "e_26-31")
        print(f"  {b:10s} decel/steady  18-22 {ra:6.3f} [{l_:6.3f},{h_:6.3f}] "
              f"null [{nl[1]:5.3f},{nl[2]:5.3f}] | 26-31 {rb:6.3f} [{l2:6.3f},{h2:6.3f}] "
              f"null [{nl2[1]:5.3f},{nl2[2]:5.3f}]   n {len(dec)}/{len(oth)}")
        OUT["t5c"][b] = dict(r18=[ra, l_, h_], null18=list(nl), n=[len(dec), len(oth)])


# =================================================================================================
def t7(W):
    hdr("T7  COVERAGE -- did route 5e (V75) ever reach the conditions route 67 exercised?\n"
        "    🛑 If 5e never drove engaged at highway speed, 'V75 fixed the grinding' was never\n"
        "    tested there and the V75-vs-V81 contrast is an EXPOSURE difference, not a build one.")
    OUT["t7"] = {}
    print(f"  {'build':10s} {'tot s':>7s} {'eng s':>7s} {'eng%':>5s} | "
          f"{'creep':>10s} {'10-40':>10s} {'40-80':>10s} {'>80':>10s} | "
          f"{'vmax kmh':>8s} {'LC wins':>7s} {'lowturn':>7s} {'decel-turn':>10s}")
    for b in ORDER:
        allw = W[b]
        e = [r for r in allw if r["eng"] == 1]
        cells = []
        for lo, hi in ((0, 10 * KMH), (10 * KMH, 40 * KMH), (40 * KMH, 80 * KMH), (HWY, 1e9)):
            s = [r for r in e if lo <= r["v"] < hi]
            cells.append(f"{len(s) * 1.28:8.0f}s")
        lt = [r for r in e if r["v"] < 15 * KMH and r["rate"] >= 3.0]
        dt = [r for r in lt if r["accel"] < -0.4]
        lc = [r for r in e if np.isfinite(r["lchg"]) and r["lchg"] > 0.5]
        vmax = max((r["vmax"] for r in allw), default=np.nan)
        print(f"  {b:10s} {len(allw) * 1.28:7.0f} {len(e) * 1.28:7.0f} "
              f"{100 * len(e) / max(len(allw),1):5.1f} | " + " ".join(f"{c:>10s}" for c in cells)
              + f" | {vmax * 3.6:8.1f} {len(lc):7d} {len(lt):7d} {len(dt):10d}")
        OUT["t7"][b] = dict(tot=len(allw) * 1.28, eng=len(e) * 1.28,
                            strata=[c.strip() for c in cells], vmax=float(vmax),
                            lc=len(lc), lowturn=len(lt), decelturn=len(dt))
    print("\n  ⚠ `LC wins` counts windows with the blinker up. The r5e / r65 / r66 caches carry\n"
          "    cs_lblink/cs_rblink, so the count is comparable; `decel-turn` is the brake proxy.")


# =================================================================================================
def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("  cutting windows (NFFT 256 / hop 128, engagement-run contiguous) ...", flush=True)
    W = {b: windows(b) for b in ORDER}
    for b in ORDER:
        print(f"    {b:10s} {len(W[b]):5d} windows, engaged "
              f"{sum(1 for r in W[b] if r['eng'] == 1):5d}", flush=True)
    if which in ("all", "t4"):
        t4(W)
    if which in ("all", "t5"):
        t5(W)
    if which in ("all", "t7"):
        t7(W)
    (ROOT / "_cache_r67x" / "r67_t4t5t7.json").write_text(
        json.dumps(OUT, indent=1, default=lambda o: str(o)))
    print(f"\nwrote {ROOT / '_cache_r67x' / 'r67_t4t5t7.json'}")


if __name__ == "__main__":
    main()
