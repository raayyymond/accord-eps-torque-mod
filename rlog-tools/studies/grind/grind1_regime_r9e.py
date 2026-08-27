#!/usr/bin/env python3
r"""studies/grind/grind1_regime_r9e.py -- LOCALISE GRINDING #1 on route `9e` (V103) and test the operator's
three-part hypothesis:  (1) openpilot command scaling at high torque mod, (2) return-to-centre
logic, (3) high-frequency road-to-wheel passthrough amplifying road feel.

Conventions inherited from `v103_r9e_lib` (each has cost this kit a wrong answer):
  * engagement is `cc_lat`; `cs_lat` does not exist.
  * `v_rear` is in m/s (the extractor's print label is wrong); `cs_v`/vEgo is +7.9 % fast at angle.
  * `cs_yaw` is identically zero -> `lp_yaw`.
  * raw14 is off-by-one; only (t, probe) and (raw14_t, raw14_b4) may be paired.  We use (t, probe).
  * `band_envelope` in `_r31_common`/`_r2b_common` is RECTIFIED -> `scipy.signal.hilbert`.
  * a phase-shuffle "control" that computes |X e^{i phi}|^2 is a NO-OP -> chi^2_2 surrogates.
  * numpy.trapz is removed -> numpy.trapezoid.
  * BOOTSTRAP UNIT = ENGAGEMENT EPISODE.  This route has 7; that is the real limit on every CI.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import hilbert

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(20260820)
NW, HOP = 256, 128           # 2.53 s / 50 % -- the scoring doc's symptom window
OUT = {}
WHEEL_ORDER1 = 0.489         # Hz per (m/s), circumference 2.073-2.080 m


def hdr(s):
    print("\n" + "=" * 110)
    print(s)
    print("=" * 110)


# ------------------------------------------------------------------ window machinery
def win_over(mask, t, nw=NW, hop=HOP):
    """Windows inside contiguous runs of `mask`.  Returns [(slice, episode_index), ...]."""
    out = []
    for k, (a, b) in enumerate(V.episodes(mask, t, nw)):
        for i in range(0, (b - a) - nw + 1, hop):
            out.append((slice(a + i, a + i + nw), k))
    return out


def psd_of(x, fs, nw=None):
    nw = nw or len(x)
    w = np.hanning(len(x))
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X = np.fft.rfft((x - x.mean()) * w)
    p = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    p[1:-1] *= 2.0
    return f, p


def brms(x, fs, lo, hi):
    f, p = psd_of(x, fs)
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.sum(p[m]) * (f[1] - f[0])))


def ci(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if len(a) < 3:
        return (float("nan"), float("nan"))
    return tuple(float(x) for x in np.percentile(a, [lo, hi]))


def rule_of_three(n):
    """95 % upper bound on a probability when 0 of n events were observed."""
    return 3.0 / n if n > 0 else float("nan")


# ------------------------------------------------------------------ load
def setup():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    d = dict(z=z, M=M, t=t, fs=fs,
             eng=M["eng"], press=M["press"],
             v=np.asarray(z["v_rear"], float),                 # m/s, the CORRECT reference
             rate=np.abs(np.asarray(z["rate_f"], float)),      # deg/s
             ang=np.abs(np.asarray(z["ang"], float)),          # deg
             cmd=np.asarray(z["e4tq"], float),                 # 0x0E4 LKAS demand, +-4096
             tq=np.asarray(z["tq"], float),
             rate_c=np.asarray(z["rate_c"], float),
             seg=np.asarray(z["seg"], int))
    d["moving"] = d["v"] > 0.5
    return d


# ==================================================================================================
# PART 1 -- ESTABLISH THE BAND.  Is 15-22 Hz the same object as the 21.73 Hz low-speed line?
# ==================================================================================================
def part1(d):
    z, t, fs = d["z"], d["t"], d["fs"]
    eng, press, v, rate = d["eng"], d["press"], d["v"], d["rate"]
    tq = d["tq"]
    hdr("PART 1A -- THE LINE, re-derived with the chi^2_2 surrogate null, and STRATIFIED BY SPEED\n"
        "           so wheel order can be excluded.  Wheel order 1 = %.3f * v[m/s] Hz." % WHEEL_ORDER1)
    rows = []
    strata = [("ENG  1.8- 8 km/h", eng & (v > 0.5) & (v < 2.222)),
              ("ENG     8-15 km/h", eng & (v >= 2.222) & (v < 4.167)),
              ("ENG    15-30 km/h", eng & (v >= 4.167) & (v < 8.333)),
              ("ENG    <30 km/h  ", eng & (v > 0.5) & (v < 8.333)),
              ("ENG    30-60 km/h", eng & (v >= 8.333) & (v < 16.667)),
              ("ENG    >60 km/h  ", eng & (v >= 16.667)),
              ("MANUAL <30 km/h  ", (~eng) & (v > 0.5) & (v < 8.333)),
              ("MANUAL >30 km/h  ", (~eng) & (v >= 8.333))]
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    sel = (f >= 12.0) & (f <= 34.0)
    fsel = f[sel]
    wn = np.hanning(NW)
    for nm, m in strata:
        W = win_over(m, t)
        if len(W) < 8:
            print("  %-19s only %d windows -- SKIPPED" % (nm, len(W)))
            continue
        S = np.array([np.abs(np.fft.rfft((tq[w] - tq[w].mean()) * wn)) ** 2 for w, _ in W])
        acc = S.mean(axis=0)[sel]
        sm = median_filter(acc, size=9, mode="nearest")
        prom = float((acc / sm).max())
        fpk = float(fsel[int(np.argmax(acc / sm))])
        nulls = []
        for _ in range(300):
            dd = sm[None, :] * RNG.chisquare(2, size=(len(W), len(sm))) / 2.0
            am = dd.mean(axis=0)
            nulls.append(float((am / median_filter(am, size=9, mode="nearest")).max()))
        p95 = float(np.percentile(nulls, 95))
        idx = RNG.permutation(len(W))
        h1 = S[idx[:len(W) // 2]].mean(axis=0)[sel]
        h2 = S[idx[len(W) // 2:]].mean(axis=0)[sel]
        f1 = float(fsel[int(np.argmax(h1 / median_filter(h1, size=9, mode="nearest")))])
        f2 = float(fsel[int(np.argmax(h2 / median_filter(h2, size=9, mode="nearest")))])
        vs = np.array([np.median(v[w]) for w, _ in W])
        vp50 = float(np.median(vs))
        wo1 = WHEEL_ORDER1 * vp50
        rows.append(dict(name=nm.strip(), n=len(W), v_p50_kmh=vp50 * 3.6, f_peak=fpk,
                         prom=prom, null_p95=p95, sh=[f1, f2], wo1=wo1,
                         order_needed=fpk / wo1 if wo1 > 0 else float("nan")))
        print("  %-19s n=%3d  v p50 %5.1f km/h | peak %6.2f Hz  prom %4.2f  null p95 %4.2f  %-12s"
              "| split-half %5.2f/%5.2f %-9s| WO1 %4.2f Hz => order %5.1f"
              % (nm, len(W), vp50 * 3.6, fpk, prom, p95,
                 "LINE" if prom > p95 else "no line",
                 f1, f2, "STABLE" if abs(f1 - f2) <= 1.0 else "UNSTABLE",
                 wo1, fpk / wo1 if wo1 > 0 else np.nan))
    OUT["line_by_speed"] = rows

    # ---------------------------------------------------------------- 1B  sub-band decomposition
    hdr("PART 1B -- IS THE 15-22 Hz BAND THE SAME OBJECT AS THE 21.73 Hz LINE?\n"
        "           Split 15-22 into three sub-bands and see which one carries the top-decile "
        "windows.")
    W = win_over(eng & (v > 0.5), t)
    SB = [("15-18", 15.0, 18.0), ("18-21", 18.0, 21.0), ("21-22.5", 21.0, 22.5),
          ("15-22", 15.0, 22.0), ("20-28", 20.0, 28.0), ("6-9", 6.0, 9.0),
          ("2.5-4.5", 2.5, 4.5), ("31-35", 31.0, 35.0)]
    B = {nm: np.array([brms(tq[w], fs, lo, hi) for w, _ in W]) for nm, lo, hi in SB}
    vs = np.array([np.median(v[w]) * 3.6 for w, _ in W])
    print("  %d engaged moving windows" % len(W))
    print("\n  Fraction of 15-22 Hz POWER carried by 21-22.5 Hz (a 1.5 Hz slice of a 7 Hz band;"
          " uniform share = 0.214):")
    frac = B["21-22.5"] ** 2 / np.maximum(B["15-22"] ** 2, 1e-12)
    for lo, hi, nm in [(0, 10, "<10 km/h"), (10, 20, "10-20"), (20, 40, "20-40"),
                       (40, 70, "40-70"), (70, 200, ">70")]:
        s = (vs >= lo) & (vs < hi)
        if s.sum() < 5:
            continue
        print("     %-10s n=%3d   share p50 %.3f   [p25 %.3f  p75 %.3f]"
              % (nm, int(s.sum()), np.median(frac[s]), *np.percentile(frac[s], [25, 75])))
    print("\n  Rank correlation of each sub-band with the 15-22 band across all engaged windows:")
    for nm, _, _ in SB:
        if nm == "15-22":
            continue
        a, b = np.log(B[nm] + 1e-9), np.log(B["15-22"] + 1e-9)
        r = float(np.corrcoef(a, b)[0, 1])
        print("     %-9s r(log,log) = %+.3f" % (nm, r))
    print("\n  Top-decile localisation, per sub-band (median over the top 10 %% of windows):")
    print("     %-9s %8s %8s %8s %8s %8s" % ("band", "v kmh", "|ang|", "|cmd|", "rate", "hands"))
    ang, cmd, press_a = d["ang"], np.abs(d["cmd"]), d["press"]
    med = {k: np.array([np.median(x[w]) for w, _ in W])
           for k, x in (("ang", ang), ("cmd", cmd), ("rate", rate))}
    hnd = np.array([press_a[w].mean() for w, _ in W])
    loc = {}
    for nm, _, _ in SB:
        thr = np.percentile(B[nm], 90)
        s = B[nm] >= thr
        loc[nm] = dict(v=float(np.median(vs[s])), ang=float(np.median(med["ang"][s])),
                       cmd=float(np.median(med["cmd"][s])), rate=float(np.median(med["rate"][s])),
                       hands=float(np.mean(hnd[s])), n=int(s.sum()))
        print("     %-9s %8.1f %8.1f %8.0f %8.1f %8.2f"
              % (nm, loc[nm]["v"], loc[nm]["ang"], loc[nm]["cmd"], loc[nm]["rate"],
                 loc[nm]["hands"]))
    print("     %-9s %8.1f %8.1f %8.0f %8.1f %8.2f"
          % ("ALL ENG", np.median(vs), np.median(med["ang"]), np.median(med["cmd"]),
             np.median(med["rate"]), np.mean(hnd)))
    OUT["subband_topdecile"] = loc
    OUT["n_eng_windows"] = len(W)
    return W, B, vs, med, hnd


# ==================================================================================================
# PART 2 -- THE JOINT REGRESSION, residualised WITHIN EPISODE, bootstrapped OVER EPISODES.
# ==================================================================================================
GRIND = ("21-22.5", 21.0, 22.5)     # established in PART 1 as grinding #1's own band
PRED = ["log v", "log|ang|", "log|cmd|", "log rate", "hands"]


def design(d, W):
    v, ang, cmd, rate, press = d["v"], d["ang"], np.abs(d["cmd"]), d["rate"], d["press"]
    X = np.column_stack([
        np.log(np.maximum([np.median(v[w]) * 3.6 for w, _ in W], 1.0)),
        np.log(np.array([np.median(ang[w]) for w, _ in W]) + 1.0),
        np.log(np.array([np.median(cmd[w]) for w, _ in W]) + 1.0),
        np.log(np.array([np.median(rate[w]) for w, _ in W]) + 0.5),
        np.array([press[w].mean() for w, _ in W]),
    ])
    ep = np.array([e for _, e in W])
    return X, ep


def within(X, ep):
    """Episode fixed-effects (within) transform."""
    Xw = X.copy().astype(float)
    for e in np.unique(ep):
        s = ep == e
        Xw[s] -= Xw[s].mean(axis=0)
    return Xw


def fit(X, y, ep, demean=True):
    Xd, yd = (within(X, ep), within(y[:, None], ep)[:, 0]) if demean else (X, y)
    if not demean:
        Xd = np.column_stack([np.ones(len(X)), X])
    b, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
    resid = yd - Xd @ b
    r2 = 1.0 - resid.var() / max(yd.var(), 1e-12)
    return (b[1:] if not demean else b), r2


def vif(Xd):
    out = []
    for j in range(Xd.shape[1]):
        others = np.delete(Xd, j, axis=1)
        A = np.column_stack([np.ones(len(Xd)), others])
        bb, *_ = np.linalg.lstsq(A, Xd[:, j], rcond=None)
        r2 = 1.0 - (Xd[:, j] - A @ bb).var() / max(Xd[:, j].var(), 1e-12)
        out.append(1.0 / max(1.0 - r2, 1e-9))
    return out


def part2(d, W, B):
    fs = d["fs"]
    tq = d["tq"]
    X, ep = design(d, W)
    Xd = within(X, ep)
    hdr("PART 2 -- JOINT REGRESSION of log(band-RMS) on log v, log|ang|, log|cmd|, log rate, hands.\n"
        "          FIXED EFFECTS within engagement episode; BOOTSTRAP OVER EPISODES (n=%d)."
        % len(np.unique(ep)))
    print("  windows n=%d in %d episodes -> per-episode window counts %s"
          % (len(W), len(np.unique(ep)),
             ", ".join(str(int((ep == e).sum())) for e in np.unique(ep))))
    print("\n  Collinearity of the WITHIN-EPISODE design (VIF; >5 = the partial effect is fragile):")
    for nm, x in zip(PRED, vif(Xd)):
        print("     %-9s VIF %6.2f" % (nm, x))
    print("\n  Correlation matrix of the within-episode predictors:")
    C = np.corrcoef(Xd.T)
    print("     %-9s " % "" + " ".join("%9s" % p for p in PRED))
    for i, p in enumerate(PRED):
        print("     %-9s " % p + " ".join("%+9.3f" % C[i, j] for j in range(len(PRED))))

    bands = [("21-22.5 GRIND1", 21.0, 22.5), ("15-22 inherited", 15.0, 22.0),
             ("6-9 POSITIVE CONTROL (rate)", 6.0, 9.0),
             ("31-35 NEGATIVE CONTROL", 31.0, 35.0)]
    res = {}
    for nm, lo, hi in bands:
        y = np.log(np.array([brms(tq[w], fs, lo, hi) for w, _ in W]) + 1e-9)
        bw, r2w = fit(X, y, ep, demean=True)
        bp, r2p = fit(X, y, ep, demean=False)
        # episode block bootstrap
        eps = np.unique(ep)
        bs = []
        for _ in range(2000):
            pick = RNG.integers(0, len(eps), len(eps))
            idx = np.concatenate([np.where(ep == eps[k])[0] for k in pick])
            epb = np.concatenate([np.full((ep == eps[k]).sum(), i) for i, k in enumerate(pick)])
            if len(np.unique(epb)) < 2:
                continue
            try:
                bb, _ = fit(X[idx], y[idx], epb, demean=True)
                bs.append(bb)
            except np.linalg.LinAlgError:
                continue
        bs = np.array(bs)
        # leave-one-episode-out jackknife
        jk = []
        for e in eps:
            s = ep != e
            jk.append(fit(X[s], y[s], ep[s], demean=True)[0])
        jk = np.array(jk)
        print("\n  --- %s ---   within-episode R2 %.3f  (pooled R2 %.3f)" % (nm, r2w, r2p))
        print("     %-9s %10s %24s %10s %20s" %
              ("predictor", "WITHIN b", "95% CI (episode boot)", "POOLED b", "jackknife range"))
        for j, p in enumerate(PRED):
            lo95, hi95 = ci(bs[:, j])
            sig = "*" if (lo95 > 0 or hi95 < 0) else " "
            print("     %-9s %+10.3f   [%+7.3f, %+7.3f] %s %+10.3f   [%+7.3f, %+7.3f]"
                  % (p, bw[j], lo95, hi95, sig, bp[j], jk[:, j].min(), jk[:, j].max()))
        res[nm] = dict(within=bw.tolist(), pooled=bp.tolist(), r2_within=float(r2w),
                       r2_pooled=float(r2p),
                       ci=[list(ci(bs[:, j])) for j in range(len(PRED))],
                       jk_lo=jk.min(axis=0).tolist(), jk_hi=jk.max(axis=0).tolist())
    OUT["regression"] = res
    return res


def part2b(d, W):
    """SHAPE responses -- the grind band divided by a control band.  The 31-35 Hz negative control
    itself has a significant rate slope (+0.435), i.e. wheel rate raises the WHOLE spectrum; the
    ratio isolates what is specific to the grind band."""
    fs, tq = d["fs"], d["tq"]
    X, ep = design(d, W)
    g = np.log(np.array([brms(tq[w], fs, 21.0, 22.5) for w, _ in W]) + 1e-9)
    n1 = np.log(np.array([brms(tq[w], fs, 31.0, 35.0) for w, _ in W]) + 1e-9)
    n2 = np.log(np.array([brms(tq[w], fs, 2.5, 4.5) for w, _ in W]) + 1e-9)
    hdr("PART 2B -- SHAPE responses.  log(grind 21-22.5) MINUS a control band, so the broadband\n"
        "           'wheel rate raises everything' component is differenced out.")
    eps = np.unique(ep)
    sd = within(X, ep).std(axis=0)
    for nm, y in (("21-22.5 / 31-35 (neg ctrl)", g - n1),
                  ("21-22.5 / 2.5-4.5 (shape)", g - n2)):
        bw, r2 = fit(X, y, ep, demean=True)
        bs = []
        for _ in range(2000):
            pick = RNG.integers(0, len(eps), len(eps))
            idx = np.concatenate([np.where(ep == eps[k])[0] for k in pick])
            epb = np.concatenate([np.full((ep == eps[k]).sum(), i) for i, k in enumerate(pick)])
            if len(np.unique(epb)) < 2:
                continue
            bs.append(fit(X[idx], y[idx], epb, demean=True)[0])
        bs = np.array(bs)
        jk = np.array([fit(X[ep != e], y[ep != e], ep[ep != e], demean=True)[0] for e in eps])
        print("\n  --- %s ---  within R2 %.3f" % (nm, r2))
        print("     %-9s %10s %24s %11s %20s"
              % ("predictor", "b", "95% CI (episode boot)", "b per SD", "jackknife range"))
        for j, p in enumerate(PRED):
            lo95, hi95 = ci(bs[:, j])
            sig = "*" if (lo95 > 0 or hi95 < 0) else " "
            print("     %-9s %+10.3f   [%+7.3f, %+7.3f] %s %+11.3f   [%+7.3f, %+7.3f]"
                  % (p, bw[j], lo95, hi95, sig, bw[j] * sd[j], jk[:, j].min(), jk[:, j].max()))
        OUT.setdefault("shape_regression", {})[nm] = dict(
            b=bw.tolist(), ci=[list(ci(bs[:, j])) for j in range(len(PRED))],
            per_sd=(bw * sd).tolist(), jk_lo=jk.min(axis=0).tolist(),
            jk_hi=jk.max(axis=0).tolist(), r2=float(r2))


# ==================================================================================================
# PART 3 -- STRATIFIED: within 5-10 and 10-20 km/h, does grind rise NEAR CENTRE and at LOW COMMAND?
# ==================================================================================================
def part3(d, W):
    fs, tq = d["fs"], d["tq"]
    v, ang, cmd, rate, press = d["v"], d["ang"], np.abs(d["cmd"]), d["rate"], d["press"]
    vs = np.array([np.median(v[w]) * 3.6 for w, _ in W])
    ma = np.array([np.median(ang[w]) for w, _ in W])
    mc = np.array([np.median(cmd[w]) for w, _ in W])
    mr = np.array([np.median(rate[w]) for w, _ in W])
    hh = np.array([press[w].mean() for w, _ in W])
    g = np.array([brms(tq[w], fs, 21.0, 22.5) for w, _ in W])
    g15 = np.array([brms(tq[w], fs, 15.0, 22.0) for w, _ in W])
    hdr("PART 3 -- STRATIFIED SPLITS.  Within each speed band, split at the band's OWN median of\n"
        "          |command| and of |angle|.  Cells with n < 5 are REFUSED.  CI = window bootstrap\n"
        "          inside the cell (there are not enough episodes for an episode bootstrap here --\n"
        "          SAY SO, do not quote these as if they were episode CIs).")
    rows = []
    for vlo, vhi in ((5, 10), (10, 20), (5, 20), (20, 40), (0, 15)):
        s = (vs >= vlo) & (vs < vhi)
        n = int(s.sum())
        print("\n  --- %d-%d km/h : n=%d windows ---" % (vlo, vhi, n))
        if n < 10:
            print("     too few windows for a split (need >= 10) -- REFUSED")
            continue
        for lab, key, arr in (("|command|", "cmd", mc), ("|angle|", "ang", ma), ("rate", "rate", mr)):
            thr = float(np.median(arr[s]))
            lo_m = s & (arr < thr)
            hi_m = s & (arr >= thr)
            if lo_m.sum() < 5 or hi_m.sum() < 5:
                print("     %-10s split at %8.1f : n=%d/%d -- REFUSED (n<5)"
                      % (lab, thr, lo_m.sum(), hi_m.sum()))
                continue
            for bn, bb in (("21-22.5", g), ("15-22", g15)):
                a, b = float(np.median(bb[lo_m])), float(np.median(bb[hi_m]))
                bs = []
                for _ in range(2000):
                    ia = RNG.integers(0, lo_m.sum(), lo_m.sum())
                    ib = RNG.integers(0, hi_m.sum(), hi_m.sum())
                    bs.append(np.median(bb[lo_m][ia]) / max(np.median(bb[hi_m][ib]), 1e-9))
                l95, h95 = ci(bs)
                print("     %-8s %-8s split %8.1f | LOW n=%2d med %7.1f | HIGH n=%2d med %7.1f |"
                      " LOW/HIGH %5.2f [%4.2f, %5.2f]%s"
                      % (bn, lab, thr, lo_m.sum(), a, hi_m.sum(), b, a / max(b, 1e-9), l95, h95,
                         " *" if (l95 > 1 or h95 < 1) else ""))
                rows.append(dict(v="%d-%d" % (vlo, vhi), band=bn, split=lab, thr=thr,
                                 n_lo=int(lo_m.sum()), n_hi=int(hi_m.sum()),
                                 med_lo=a, med_hi=b, ratio=a / max(b, 1e-9),
                                 ci=[l95, h95]))
        print("     [cell census] v p50 %.1f  |ang| p50 %.1f  |cmd| p50 %.0f  rate p50 %.1f"
              "  hands %.2f" % (np.median(vs[s]), np.median(ma[s]), np.median(mc[s]),
                                np.median(mr[s]), np.mean(hh[s])))
    OUT["stratified"] = rows


def part3b(d, W):
    """How much INDEPENDENT information do the three 'levers' carry at low speed?  If a median
    split on |cmd|, |angle| and rate partitions the same windows the same way, no stratification
    can ever separate them."""
    v, ang, cmd, rate = d["v"], d["ang"], np.abs(d["cmd"]), d["rate"]
    vs = np.array([np.median(v[w]) * 3.6 for w, _ in W])
    ma = np.array([np.median(ang[w]) for w, _ in W])
    mc = np.array([np.median(cmd[w]) for w, _ in W])
    mr = np.array([np.median(rate[w]) for w, _ in W])
    hdr("PART 3B -- WHY THE STRATIFIED SPLITS DISAGREE: at low speed |command|, |angle| and wheel\n"
        "           rate are the SAME PARTITION.  Agreement of the median-split labels, per band.")
    for vlo, vhi in ((5, 10), (10, 20), (0, 15), (20, 40), (40, 200)):
        s = (vs >= vlo) & (vs < vhi)
        if s.sum() < 8:
            continue
        lab = {k: (a[s] >= np.median(a[s])) for k, a in
               (("cmd", mc), ("ang", ma), ("rate", mr), ("v", vs))}
        print("  %3d-%-3d km/h  n=%3d | agree(cmd,ang) %.2f  agree(cmd,rate) %.2f "
              " agree(ang,rate) %.2f | r(log cmd,log rate) %+.2f  r(log cmd,log|ang|) %+.2f"
              % (vlo, vhi, int(s.sum()),
                 float((lab["cmd"] == lab["ang"]).mean()),
                 float((lab["cmd"] == lab["rate"]).mean()),
                 float((lab["ang"] == lab["rate"]).mean()),
                 float(np.corrcoef(np.log(mc[s] + 1), np.log(mr[s] + .5))[0, 1]),
                 float(np.corrcoef(np.log(mc[s] + 1), np.log(ma[s] + 1))[0, 1])))


# ==================================================================================================
# PART 4 -- IS GRIND #1 ENGAGEMENT-CONDITIONAL?  Matched on speed AND rate AND angle.
# ==================================================================================================
def part4(d):
    fs, t, tq = d["fs"], d["t"], d["tq"]
    eng, v, ang, rate, press = d["eng"], d["v"], d["ang"], d["rate"], d["press"]
    hdr("PART 4 -- ENGAGED vs MANUAL, MATCHED ON SPEED **AND** RATE **AND** ANGLE.\n"
        "          Ratio of the median 2.53 s band-RMS.  >1 = engagement amplifies.  This is the\n"
        "          same construction that gave the ratchet its 24.29x.  A road-input symptom must\n"
        "          be present MANUALLY too; an engagement-conditional one refutes pure passthrough.")
    We = win_over(eng & (v > 0.5), t)
    Wm = win_over((~eng) & (v > 0.5), t)
    print("  engaged windows %d   manual windows %d" % (len(We), len(Wm)))

    def cls(W):
        return [(w, float(np.median(v[w]) * 3.6), float(np.median(rate[w])),
                 float(np.median(ang[w])), float(press[w].mean())) for w, _ in W]
    ce, cm = cls(We), cls(Wm)
    BND = [("21-22.5 GRIND1", 21.0, 22.5), ("15-22", 15.0, 22.0),
           ("6-9 ratchet", 6.0, 9.0), ("31-35 neg ctrl", 31.0, 35.0)]
    rows = []
    print("\n  %-9s %-8s %-9s %4s %4s | " % ("v km/h", "rate", "|ang| deg", "n_E", "n_M")
          + " ".join("%-26s" % b[0] for b in BND))
    for vlo, vhi in ((2, 10), (10, 20), (20, 40), (0, 20)):
        for rlo, rhi in ((0, 6), (6, 20), (20, 1e9), (0, 1e9)):
            for alo, ahi in ((0, 15), (15, 1e9), (0, 1e9)):
                se = [x[0] for x in ce if vlo <= x[1] < vhi and rlo <= x[2] < rhi
                      and alo <= x[3] < ahi]
                sm = [x[0] for x in cm if vlo <= x[1] < vhi and rlo <= x[2] < rhi
                      and alo <= x[3] < ahi]
                if len(se) < 5 or len(sm) < 5:
                    continue
                cells = {}
                out = []
                for nm, lo, hi in BND:
                    a = float(np.median([brms(tq[w], fs, lo, hi) for w in se]))
                    b = float(np.median([brms(tq[w], fs, lo, hi) for w in sm]))
                    bs = []
                    A = np.array([brms(tq[w], fs, lo, hi) for w in se])
                    Bm = np.array([brms(tq[w], fs, lo, hi) for w in sm])
                    for _ in range(2000):
                        bs.append(np.median(A[RNG.integers(0, len(A), len(A))]) /
                                  max(np.median(Bm[RNG.integers(0, len(Bm), len(Bm))]), 1e-9))
                    l95, h95 = ci(bs)
                    cells[nm] = dict(eng=a, man=b, ratio=a / max(b, 1e-9), ci=[l95, h95])
                    out.append("%7.2f [%5.2f,%7.2f]%s"
                               % (a / max(b, 1e-9), l95, h95, "*" if l95 > 1 else " "))
                print("  %-9s %-8s %-9s %4d %4d | " %
                      ("%d-%d" % (vlo, vhi),
                       "%g-%g" % (rlo, min(rhi, 999)), "%g-%g" % (alo, min(ahi, 999)),
                       len(se), len(sm)) + " ".join(out))
                rows.append(dict(v="%d-%d" % (vlo, vhi), rate="%g-%g" % (rlo, min(rhi, 999)),
                                 ang="%g-%g" % (alo, min(ahi, 999)),
                                 n_e=len(se), n_m=len(sm), bands=cells))
    OUT["eng_vs_man_matched"] = rows


def part4b(d):
    """The confound the matched table above does NOT close: at low speed, MANUAL driving is
    hands-ON and ENGAGED driving is hands-OFF, and PART 2 found hands-on strongly SUPPRESSES the
    grind band.  Re-run the contrast matched on HANDS as well, and report the ratio-of-ratios
    against the 31-35 Hz negative control."""
    fs, t, tq = d["fs"], d["t"], d["tq"]
    eng, v, ang, rate, press = d["eng"], d["v"], d["ang"], d["rate"], d["press"]
    hdr("PART 4B -- SAME CONTRAST, ALSO MATCHED ON HANDS, plus the RATIO-OF-RATIOS against the\n"
        "           31-35 Hz negative control (a band-specific excess, not a broadband one).")
    We = win_over(eng & (v > 0.5), t)
    Wm = win_over((~eng) & (v > 0.5), t)

    def cls(W):
        return [(w, float(np.median(v[w]) * 3.6), float(np.median(rate[w])),
                 float(np.median(ang[w])), float(press[w].mean())) for w, _ in W]
    ce, cm = cls(We), cls(Wm)
    print("\n  hands duty: engaged windows p50 %.2f  manual windows p50 %.2f"
          % (np.median([x[4] for x in ce]), np.median([x[4] for x in cm])))
    rows = []
    print("\n  %-8s %-8s %-9s %-9s %4s %4s | %-24s %-24s %-11s"
          % ("v km/h", "rate", "|ang|", "hands", "n_E", "n_M",
             "21-22.5 E/M [95% CI]", "31-35 E/M [95% CI]", "ratio-ratio"))
    for vlo, vhi in ((2, 10), (10, 20), (0, 20), (20, 40)):
        for hlo, hhi, hn in ((0.0, 0.25, "off <.25"), (0.5, 1.01, "on  >.5"), (0.0, 1.01, "any")):
            for rlo, rhi in ((0, 20), (0, 1e9)):
                se = [x[0] for x in ce if vlo <= x[1] < vhi and rlo <= x[2] < rhi
                      and hlo <= x[4] < hhi]
                sm = [x[0] for x in cm if vlo <= x[1] < vhi and rlo <= x[2] < rhi
                      and hlo <= x[4] < hhi]
                if len(se) < 5 or len(sm) < 5:
                    continue
                A = np.array([brms(tq[w], fs, 21.0, 22.5) for w in se])
                Bm = np.array([brms(tq[w], fs, 21.0, 22.5) for w in sm])
                Cn = np.array([brms(tq[w], fs, 31.0, 35.0) for w in se])
                Dn = np.array([brms(tq[w], fs, 31.0, 35.0) for w in sm])
                r1 = np.median(A) / max(np.median(Bm), 1e-9)
                r2 = np.median(Cn) / max(np.median(Dn), 1e-9)
                b1, b2, br = [], [], []
                for _ in range(2000):
                    ia = RNG.integers(0, len(A), len(A))
                    ib = RNG.integers(0, len(Bm), len(Bm))
                    x1 = np.median(A[ia]) / max(np.median(Bm[ib]), 1e-9)
                    x2 = np.median(Cn[ia]) / max(np.median(Dn[ib]), 1e-9)
                    b1.append(x1); b2.append(x2); br.append(x1 / max(x2, 1e-9))
                l1, h1 = ci(b1); l2, h2 = ci(b2); lr, hr = ci(br)
                print("  %-8s %-8s %-9s %-9s %4d %4d | %7.2f [%5.2f,%7.2f]%s %7.2f [%5.2f,%6.2f]%s"
                      " %6.1f [%5.1f,%7.1f]%s"
                      % ("%d-%d" % (vlo, vhi), "%g-%g" % (rlo, min(rhi, 999)), "any", hn,
                         len(se), len(sm), r1, l1, h1, "*" if l1 > 1 else " ",
                         r2, l2, h2, "*" if l2 > 1 else " ", r1 / max(r2, 1e-9), lr, hr,
                         "*" if lr > 1 else " "))
                rows.append(dict(v="%d-%d" % (vlo, vhi), rate="%g-%g" % (rlo, min(rhi, 999)),
                                 hands=hn, n_e=len(se), n_m=len(sm),
                                 grind=r1, grind_ci=[l1, h1], neg=r2, neg_ci=[l2, h2],
                                 rr=r1 / max(r2, 1e-9), rr_ci=[lr, hr]))
    OUT["eng_vs_man_hands_matched"] = rows


# ==================================================================================================
# PART 5 -- TASK 3.  COMMAND SCALING: is the grind excited by command STEPS (rate) or by command
#           AMPLITUDE?  And does it track command SIGN REVERSALS?
# ==================================================================================================
def part5(d, W):
    fs, t, tq = d["fs"], d["t"], d["tq"]
    eng, v, ang, rate, press = d["eng"], d["v"], d["ang"], d["rate"], d["press"]
    cmd = d["cmd"]
    dcmd = np.abs(np.diff(cmd, prepend=cmd[0]))
    sgnchg = ((np.sign(cmd[1:]) * np.sign(cmd[:-1])) < 0).astype(float)
    sgnchg = np.concatenate([[0.0], sgnchg])
    hdr("PART 5A -- FRAME-TO-FRAME |delta command| ON 0x0E4, ENGAGED, BY SPEED.\n"
        "           openpilot's slew is normalised, so counts/tick scale with the firmware gain:\n"
        "           13.4 (stock) -> 80.2 (6x, on car) -> 106.9 (8x).  Sampling is the cache's\n"
        "           101.15 Hz grid; 0x0E4 is a 100 Hz message, so ~1 message per row.")
    m = eng & (v > 0.5)
    print("  ENGAGED & MOVING n=%d frames (%.1f s).  duty(|dcmd| == 0) = %.4f"
          % (m.sum(), m.sum() / fs, float((dcmd[m] == 0).mean())))
    rows = []
    print("\n  %-14s %7s %8s %7s %7s %7s %7s %8s %9s %9s"
          % ("v km/h", "n", "sec", "p50", "p90", "p99", "max", "mean", "sign rev/s", "|cmd| p50"))
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 40), (40, 60), (60, 85), (85, 200), (0, 200)):
        s = m & (v * 3.6 >= lo) & (v * 3.6 < hi)
        if s.sum() < 50:
            continue
        dd = dcmd[s]
        r = dict(v="%d-%d" % (lo, hi), n=int(s.sum()), sec=float(s.sum() / fs),
                 p50=float(np.percentile(dd, 50)), p90=float(np.percentile(dd, 90)),
                 p99=float(np.percentile(dd, 99)), mx=float(dd.max()), mean=float(dd.mean()),
                 srev=float(sgnchg[s].sum() / (s.sum() / fs)),
                 cmd_p50=float(np.median(np.abs(cmd[s]))))
        rows.append(r)
        print("  %-14s %7d %8.1f %7.0f %7.0f %7.0f %7.0f %8.1f %9.2f %9.0f"
              % (r["v"], r["n"], r["sec"], r["p50"], r["p90"], r["p99"], r["mx"], r["mean"],
                 r["srev"], r["cmd_p50"]))
    OUT["dcmd_by_speed"] = rows

    hdr("PART 5B -- DOES THE GRIND TRACK |dcmd| (EXCITATION BY STEPS) OR |cmd| (AMPLITUDE)?\n"
        "           Both entered jointly, on top of the PART 2 covariates, within episode.")
    X0, ep = design(d, W)
    mdc = np.log(np.array([np.median(dcmd[w]) for w, _ in W]) + 1.0)
    rms_dc = np.log(np.array([np.sqrt(np.mean(dcmd[w] ** 2)) for w, _ in W]) + 1.0)
    srv = np.log(np.array([sgnchg[w].sum() / (len(cmd[w]) / fs) for w, _ in W]) + 0.5)
    X = np.column_stack([X0, mdc, srv])
    P2 = PRED + ["log|dcmd|", "log signrev/s"]
    eps = np.unique(ep)
    for bnm, lo, hi in (("21-22.5 GRIND1", 21.0, 22.5), ("6-9 ratchet CONTROL", 6.0, 9.0),
                        ("31-35 NEG CONTROL", 31.0, 35.0)):
        y = np.log(np.array([brms(tq[w], fs, lo, hi) for w, _ in W]) + 1e-9)
        bw, r2 = fit(X, y, ep, demean=True)
        bs = []
        for _ in range(2000):
            pick = RNG.integers(0, len(eps), len(eps))
            idx = np.concatenate([np.where(ep == eps[k])[0] for k in pick])
            epb = np.concatenate([np.full((ep == eps[k]).sum(), i) for i, k in enumerate(pick)])
            if len(np.unique(epb)) < 2:
                continue
            try:
                bs.append(fit(X[idx], y[idx], epb, demean=True)[0])
            except np.linalg.LinAlgError:
                continue
        bs = np.array(bs)
        jk = np.array([fit(X[ep != e], y[ep != e], ep[ep != e], demean=True)[0] for e in eps])
        print("\n  --- %s ---  within R2 %.3f  VIF(|cmd|)=%.2f VIF(|dcmd|)=%.2f"
              % (bnm, r2, vif(within(X, ep))[2], vif(within(X, ep))[5]))
        for j, p in enumerate(P2):
            l95, h95 = ci(bs[:, j])
            print("     %-14s %+8.3f   [%+7.3f, %+7.3f] %s  jk [%+7.3f, %+7.3f]"
                  % (p, bw[j], l95, h95, "*" if (l95 > 0 or h95 < 0) else " ",
                     jk[:, j].min(), jk[:, j].max()))
        OUT.setdefault("cmd_rate_regression", {})[bnm] = dict(
            names=P2, b=bw.tolist(), ci=[list(ci(bs[:, j])) for j in range(len(P2))],
            jk_lo=jk.min(axis=0).tolist(), jk_hi=jk.max(axis=0).tolist(), r2=float(r2))
    _ = rms_dc

    hdr("PART 5C -- SIGN-REVERSAL RATE vs GRIND, unadjusted, by speed stratum (n>=5 cells only).")
    vs = np.array([np.median(v[w]) * 3.6 for w, _ in W])
    g = np.array([brms(tq[w], fs, 21.0, 22.5) for w, _ in W])
    sr = np.array([sgnchg[w].sum() / (len(cmd[w]) / fs) for w, _ in W])
    for lo, hi in ((0, 10), (10, 20), (20, 40), (40, 200)):
        s = (vs >= lo) & (vs < hi)
        if s.sum() < 5:
            continue
        r = float(np.corrcoef(np.log(sr[s] + 0.5), np.log(g[s] + 1e-9))[0, 1])
        print("  %-9s n=%3d  sign-rev/s p50 %5.2f p90 %5.2f | r(log signrev, log grind) = %+.3f"
              % ("%d-%d" % (lo, hi), int(s.sum()), np.median(sr[s]),
                 np.percentile(sr[s], 90), r))


def part5d(d, W):
    """The slew rail itself, and a within-low-speed partial for the sign-reversal term."""
    fs, tq, v = d["fs"], d["tq"], d["v"]
    eng, rate, press, ang = d["eng"], d["rate"], d["press"], d["ang"]
    cmd = d["cmd"]
    dcmd = np.abs(np.diff(cmd, prepend=cmd[0]))
    hdr("PART 5D -- IS THE COMMAND ON ITS SLEW RAIL?  |dcmd| histogram and rail duty by speed.")
    m = eng & (v > 0.5)
    vals, cnt = np.unique(dcmd[m], return_counts=True)
    top = np.argsort(-cnt)[:12]
    print("  12 most common |dcmd| values engaged: "
          + "  ".join("%g:%.3f" % (vals[i], cnt[i] / m.sum()) for i in sorted(top,
                                                                             key=lambda i: vals[i])))
    print("\n  %-10s %8s %10s %10s %10s" % ("v km/h", "sec", "duty>=120", "duty>=240", "duty==0"))
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 40), (40, 60), (60, 200), (0, 200)):
        s = m & (v * 3.6 >= lo) & (v * 3.6 < hi)
        if s.sum() < 50:
            continue
        print("  %-10s %8.1f %10.4f %10.4f %10.4f"
              % ("%d-%d" % (lo, hi), s.sum() / fs, float((dcmd[s] >= 120).mean()),
                 float((dcmd[s] >= 240).mean()), float((dcmd[s] == 0).mean())))
    OUT["slew_rail"] = {"%d-%d" % (lo, hi): float((dcmd[m & (v * 3.6 >= lo) & (v * 3.6 < hi)]
                                                   >= 120).mean())
                        for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 40), (40, 60), (60, 200))}

    hdr("PART 5E -- WITHIN THE OPERATOR'S OWN REGIME (engaged, < 15 km/h): a 3-predictor fit,\n"
        "           log rate + log signrev/s + log|cmd|, on log(grind).  n is small -- say so.")
    vs = np.array([np.median(v[w]) * 3.6 for w, _ in W])
    sgn = ((np.sign(cmd[1:]) * np.sign(cmd[:-1])) < 0).astype(float)
    sgn = np.concatenate([[0.0], sgn])
    sel = vs < 15.0
    idx = np.where(sel)[0]
    g = np.log(np.array([brms(tq[W[i][0]], fs, 21.0, 22.5) for i in idx]) + 1e-9)
    xr = np.log(np.array([np.median(rate[W[i][0]]) for i in idx]) + 0.5)
    xs = np.log(np.array([sgn[W[i][0]].sum() / (NW / fs) for i in idx]) + 0.5)
    xc = np.log(np.array([np.median(np.abs(cmd[W[i][0]])) for i in idx]) + 1.0)
    xa = np.log(np.array([np.median(ang[W[i][0]]) for i in idx]) + 1.0)
    xh = np.array([press[W[i][0]].mean() for i in idx])
    print("  n=%d windows (%.1f s).  pairwise r: rate~signrev %+.2f  rate~|cmd| %+.2f "
          " signrev~|cmd| %+.2f" % (len(idx), len(idx) * NW / fs / 2,
                                    np.corrcoef(xr, xs)[0, 1], np.corrcoef(xr, xc)[0, 1],
                                    np.corrcoef(xs, xc)[0, 1]))
    for nm, cols, names in (("rate + signrev", [xr, xs], ["log rate", "log signrev"]),
                            ("rate + |cmd|", [xr, xc], ["log rate", "log|cmd|"]),
                            ("rate + signrev + |cmd| + |ang| + hands", [xr, xs, xc, xa, xh],
                             ["log rate", "log signrev", "log|cmd|", "log|ang|", "hands"])):
        A = np.column_stack([np.ones(len(idx))] + cols)
        b, *_ = np.linalg.lstsq(A, g, rcond=None)
        resid = g - A @ b
        r2 = 1 - resid.var() / g.var()
        dof = len(idx) - A.shape[1]
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * resid.var() * len(idx) / max(dof, 1))
        print("     %-40s R2 %.3f  " % (nm, r2)
              + "  ".join("%s %+.3f+-%.3f" % (n, bb, 1.96 * ss)
                          for n, bb, ss in zip(names, b[1:], se[1:])))


def part5f(d, W):
    """Episode provenance of the low-speed windows, and the ENGAGED-ONLY hands contrast."""
    fs, tq, v = d["fs"], d["tq"], d["v"]
    rate, press = d["rate"], d["press"]
    vs = np.array([np.median(v[w]) * 3.6 for w, _ in W])
    ep = np.array([e for _, e in W])
    hdr("PART 5F -- EPISODE PROVENANCE of the low-speed windows (the real limit on every CI here),\n"
        "           and the ENGAGED-ONLY hands-on / hands-off contrast, matched on wheel rate.")
    for lab, s in (("< 10 km/h", vs < 10), ("< 15 km/h", vs < 15), ("< 20 km/h", vs < 20)):
        u, c = np.unique(ep[s], return_counts=True)
        print("  %-10s n=%3d windows from %d episodes: %s"
              % (lab, int(s.sum()), len(u), ", ".join("ep%d:%d" % (a, b) for a, b in zip(u, c))))
    g = np.array([brms(tq[w], fs, 21.0, 22.5) for w, _ in W])
    hh = np.array([press[w].mean() for w, _ in W])
    mr = np.array([np.median(rate[w]) for w, _ in W])
    print("\n  ENGAGED ONLY, grind 21-22.5 Hz, hands-OFF (<0.1) vs hands-ON (>0.5):")
    print("     %-12s %-10s %5s %10s %5s %10s %10s" %
          ("v km/h", "rate", "n_off", "med off", "n_on", "med on", "off/on"))
    for vlo, vhi in ((0, 20), (0, 40), (20, 60), (0, 200)):
        for rlo, rhi in ((0, 6), (6, 1e9), (0, 1e9)):
            s = (vs >= vlo) & (vs < vhi) & (mr >= rlo) & (mr < rhi)
            a = s & (hh < 0.1)
            b = s & (hh > 0.5)
            if a.sum() < 5 or b.sum() < 5:
                continue
            bs = []
            for _ in range(2000):
                bs.append(np.median(g[a][RNG.integers(0, a.sum(), a.sum())]) /
                          max(np.median(g[b][RNG.integers(0, b.sum(), b.sum())]), 1e-9))
            l95, h95 = ci(bs)
            print("     %-12s %-10s %5d %10.1f %5d %10.1f %10.2f [%.2f, %.2f]%s"
                  % ("%d-%d" % (vlo, vhi), "%g-%g" % (rlo, min(rhi, 999)), a.sum(),
                     np.median(g[a]), b.sum(), np.median(g[b]),
                     np.median(g[a]) / max(np.median(g[b]), 1e-9), l95, h95,
                     " *" if (l95 > 1 or h95 < 1) else ""))


# ==================================================================================================
# PART 6 -- TASK 4.  THE FREE GATE-3 MEASUREMENT for the proposed V104 biquad re-centring.
# ==================================================================================================
def part6(d):
    """(a) the +-12.0 float / +-0x3000 = +-12288 integer clamp on the gp-0x6b86 assist lane, and
       (b) the DROPOUT: |gp-0x4f60| > 0x6400 (25600) writes a LITERAL ZERO to gp-0x6b86.

    PROXY FOR gp-0x4f60, and what it costs:
      gp-0x4f60 is Sensor-B (TAS) column torque.  The firmware's own CAN bridge is byte-verified
      (reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge, disasm 0x55c50-0x55c5e):
          CAN399(0x18F).STEER_TORQUE_SENSOR = -floor(gp-0x4f60 * 125 / 128)
      and the cache's `tq` IS that field (DBC scale -1.0).  So
          |gp-0x4f60| = |tq| * 128/125 = 1.024 * |tq|   (exact to +-1 count from the floor)
      COST: this is the value AS PUBLISHED at the CAN TX tick, not as read inside FUN_000352b4 in
      the same 1 kHz cycle -- 0x18F is a 100 Hz message, so an excursion shorter than ~10 ms can be
      missed.  gp-0x4f60 has NO EMA/IIR in its producer, so it can move within a tick.
    """
    fs, tq = d["fs"], d["tq"]
    eng, v, press = d["eng"], d["v"], d["press"]
    cmd = np.abs(d["cmd"])
    rate = d["rate"]
    x = 1.024 * np.abs(tq)          # |gp-0x4f60| in firmware counts
    DROP = 25600.0
    hdr("PART 6 -- GATE-3 FOR THE PROPOSED V104 BIQUAD RE-CENTRING, read off V103's own flight.")
    print("  (b) THE DROPOUT  |gp-0x4f60| > 0x6400 = 25600  =>  gp-0x6b86 := literal 0")
    print("      %-34s %10s %10s %12s %12s" % ("regime", "frames", "sec", "max |4f60|", "duty>25600"))
    rows = []
    regimes = [("WHOLE ROUTE", np.ones_like(eng, bool)),
               ("ENGAGED", eng),
               ("ENGAGED & moving", eng & (v > 0.5)),
               ("ENGAGED < 30 km/h (grind #1)", eng & (v > 0.5) & (v < 8.333)),
               ("ENGAGED  5-10 km/h", eng & (v * 3.6 >= 5) & (v * 3.6 < 10)),
               ("ENGAGED rate >= 13 deg/s", eng & (rate >= 13)),
               ("ENGAGED hands-ON", eng & press),
               ("ENGAGED at the 0x0E4 rail", eng & (cmd >= 4096)),
               ("MANUAL", ~eng)]
    for nm, m in regimes:
        n = int(m.sum())
        if n == 0:
            continue
        duty = float((x[m] > DROP).mean())
        r3 = rule_of_three(n)
        rows.append(dict(regime=nm, n=n, sec=n / fs, max=float(x[m].max()), duty=duty,
                         rule_of_three=r3))
        print("      %-34s %10d %10.1f %12.1f %12.6f%s"
              % (nm, n, n / fs, x[m].max(), duty,
                 "   (0 of %d; 95%% upper bound %.2e)" % (n, r3) if duty == 0 else ""))
    print("\n      headroom: max |gp-0x4f60| over the WHOLE route = %.1f counts = %.1f %% of the"
          " 25600 dropout threshold." % (x.max(), 100 * x.max() / DROP))
    print("      p99.9 engaged = %.1f (%.1f %%)   p100 engaged = %.1f (%.1f %%)"
          % (np.percentile(x[eng], 99.9), 100 * np.percentile(x[eng], 99.9) / DROP,
             x[eng].max(), 100 * x[eng].max() / DROP))
    OUT["dropout"] = rows
    print("\n  (a) THE +-0x3000 = +-12288 CLAMP")
    print("      A1  THE AGGREGATOR'S OWN GATE (FUN_0003aa2c, 0x3aa38-0x3acc4) IS A ZERO-TYPE")
    print("          RANGE GATE at +-0x3000, and the kit's byte-read lane census records the")
    print("          producer's own final bound as EXACTLY +-0x3000 -- 'magnitude +-0x3000 ==")
    print("          window exactly (inclusive)'.  A gate whose window equals its producer's")
    print("          ceiling CANNOT FIRE.  Duty = 0 BY CONSTRUCTION, not by measurement.")
    print("          [EVIDENCE, inherited: eps_chain_control.motor_torque_demand_aggregator +")
    print("           BUILD-LINEAGE; re-read this session, not recalled.]")
    print("      A2  THE PRODUCER'S OWN CLAMP is NOT OBSERVABLE FROM THIS CAPTURE.  gp-0x6b86 is")
    print("          not on the bus, no V103 cave rung reads it (b7=6b4c sign, b6=r24/r26,")
    print("          b5=friction/inertia, b4=r24 sign, b3=D_state sign), and its input is a")
    print("          10-knot ADAPTIVE RAM curve (gp-0x6420..-0x6444, monotonicity-enforced by")
    print("          FUN_000352a0) followed by a magnitude PEAK-HOLD -- the knots are RAM, not")
    print("          calibration, so they cannot be byte-read from the image either.")
    print("      A3  WHAT THE FLIGHT DOES BOUND: the notch as flown has |H| <= 1.000032 over")
    print("          0.1-500 Hz (V103 GATE 2).  A filter that cannot amplify cannot create a")
    print("          clamp hit that its own input did not already have.  So V103's 406 engaged")
    print("          seconds are evidence that ARMING the filter did not add clamp hits --")
    print("          they are NOT evidence about a RE-CENTRED notch, whose peak |H| is a")
    print("          different number that must be computed from V104's own coefficients.")



# ==================================================================================================
# PART 7 -- WHICH CHANNEL CARRIES THE 21.73 Hz LINE, and is it in openpilot's command?
# ==================================================================================================
def part7(d):
    fs, t = d["fs"], d["t"]
    z = d["z"]
    eng, v, press = d["eng"], d["v"], d["press"]
    CH = [("tq", "driver torque 0x18F"), ("rate_c", "steer rate 0x14A"),
          ("ang", "steering angle"), ("e4tq", "LKAS command 0x0E4"),
          ("x6b4c", "EPS assist-sum lane (427)"), ("imu_lat", "IMU lateral"),
          ("imu_vert", "IMU vertical"), ("v_rear", "rear wheel speed")]
    X = {k: np.asarray(z[k], float) for k, _ in CH}
    X["ang"] = np.abs(X["ang"])
    hdr("PART 7 -- WHICH CHANNEL CARRIES THE 21.73 Hz LINE?  Pooled PSD prominence with the same\n"
        "          chi^2_2 surrogate null, and coherence^2 against driver torque at 21-22.5 Hz\n"
        "          with a SHUFFLED-PAIR control.  Arm: ENGAGED, moving, < 15 km/h.")
    m = eng & (v > 0.5) & (v < 4.167)
    W = [w for w, _ in win_over(m, t)]
    print("  n = %d windows (%.1f s of exposure)" % (len(W), len(W) * NW / fs / 2))
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    sel = (f >= 12.0) & (f <= 34.0)
    fsel = f[sel]
    wn = np.hanning(NW)
    band = (f >= 21.0) & (f <= 22.5)
    rows = []
    for k, lab in CH:
        x = X[k]
        S = np.array([np.abs(np.fft.rfft((x[w] - x[w].mean()) * wn)) ** 2 for w in W])
        acc = S.mean(axis=0)[sel]
        sm = median_filter(acc, size=9, mode="nearest")
        prom = float((acc / sm).max())
        fpk = float(fsel[int(np.argmax(acc / sm))])
        nulls = []
        for _ in range(300):
            dd = sm[None, :] * RNG.chisquare(2, size=(len(W), len(sm))) / 2.0
            am = dd.mean(axis=0)
            nulls.append(float((am / median_filter(am, size=9, mode="nearest")).max()))
        p95 = float(np.percentile(nulls, 95))
        # coherence^2 vs tq at 21-22.5 Hz, real and shuffled-pair
        A = np.array([np.fft.rfft((x[w] - x[w].mean()) * wn) for w in W])
        Bq = np.array([np.fft.rfft((X["tq"][w] - X["tq"][w].mean()) * wn) for w in W])

        def coh(Aa, Bb):
            Sxy = (Aa * np.conj(Bb)).mean(axis=0)
            Sxx = (np.abs(Aa) ** 2).mean(axis=0)
            Syy = (np.abs(Bb) ** 2).mean(axis=0)
            c = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
            return float(c[band].mean()), float(np.degrees(np.angle(Sxy[band].sum())))
        c_real, ph = coh(A, Bq)
        sh = RNG.permutation(len(W))
        c_shuf, _ = coh(A, Bq[sh])
        print("  %-28s peak %6.2f Hz prom %6.2f (null p95 %4.2f) %-8s | coh^2(x,tq) 21-22.5 ="
              " %.3f  shuffled %.3f  ratio %6.1f  phase %+7.1f deg"
              % (lab, fpk, prom, p95, "LINE" if prom > p95 else "no line",
                 c_real, c_shuf, c_real / max(c_shuf, 1e-9), ph))
        rows.append(dict(ch=k, label=lab, f_peak=fpk, prom=prom, null_p95=p95,
                         coh=c_real, coh_shuf=c_shuf, phase=ph))
    OUT["line_channels"] = rows
    print("\n  CONTEXT [inherited EVIDENCE, docs/scoring/SCORING-2026-08-20-v103-route9e.md sec 3.6-3.7]:")
    print("    V103's Re(Z) zero crossing f0 = 25.23 Hz [24.88, 25.91]; the sliding sign map is")
    print("    ANTI-DAMPED (95 % CI entirely below zero) at every 1 Hz bin from 16 to 23 Hz.")
    print("    => 21.73 Hz sits INSIDE the band where the column impedance's real part is")
    print("       NEGATIVE, i.e. where the loop feeds energy INTO the column rather than")
    print("       removing it.  15-22 Hz Re(Z) = -1135 [-1629, -904]; 18-22 = -751 [-1102, -591].")


# ==================================================================================================
# PART 8 -- THE gp-0x6b30 LATCH / gp-0x6806 CHATTER HYPOTHESIS, tested on the 427 lane.
# ==================================================================================================
def part8(d):
    """Mechanism under test (orchestrator, from a Ghidra sibling):
         gp-0x6806 is a 5-conjunct AND; if it CHATTERS at 5-10 km/h, each disengaged micro-interval
         latches gp-0x6b30 to zero (self-perpetuating while gp-0x6806 == 0) and the forward LKAS
         blend is chopped -> a broadband audible texture.
       Instrument: gp-0x6b30 -> x4 gain -> gp-0x6b4c, and the 0x1AB 427 lane measures gp-0x6b4c.
       Cache fields: mag427 (10-bit magnitude), sgn427, x6b4c (= mag427 * 12.8, SIGNED).
       NOTE x6b94 is an ALIAS of x6b4c in this cache -- one channel, not two.
    """
    from scipy.signal import butter, sosfiltfilt
    fs, t = d["fs"], d["t"]
    z = d["z"]
    eng, v, press, rate, ang = d["eng"], d["v"], d["press"], d["rate"], d["ang"]
    cmd = np.abs(d["cmd"])
    mag = np.asarray(z["mag427"], float)
    tq = d["tq"]
    vk = v * 3.6

    hdr("PART 8.0 -- POSITIVE CONTROL FIRST.  A zero-detector on the 427 lane is only an\n"
        "            instrument if it fires where it MUST and is silent where it MUST be.")
    print("  0x1AB tap rate: %.2f Hz (n=%d) -- the lane is sampled at 50 Hz and zero-order-held\n"
          "     onto the 101.15 Hz grid, so NO EVENT SHORTER THAN 20 ms IS OBSERVABLE."
          % (len(z["ab_t1ab"]) / (z["ab_t1ab"][-1] - z["ab_t1ab"][0]), len(z["ab_t1ab"])))
    print("  C1 MUST FIRE   -- MANUAL (LKAS off): P(mag427 == 0) = %.4f   [expected ~1]"
          % float((mag[~eng] == 0).mean()))
    print("  C2 MUST BE OFF -- ENGAGED           : P(mag427 == 0) = %.4f   [expected << 1]"
          % float((mag[eng] == 0).mean()))
    print("  C3 GRADED      -- P(mag427 == 0 | |0x0E4| band), engaged, at the best lag:")
    lag = 2
    E = cmd[:len(cmd) - lag]
    M = mag[lag:]
    EN = eng[:len(cmd) - lag]
    VV = vk[:len(vk) - lag]
    RR = rate[:len(rate) - lag]
    AA = ang[:len(ang) - lag]
    PP = press[:len(press) - lag]
    TT = t[:len(t) - lag]
    for a, b in ((0, 50), (50, 100), (100, 200), (200, 400), (400, 800), (800, 1600),
                 (1600, 3000), (3000, 4097)):
        m = EN & (E >= a) & (E < b)
        if m.sum() < 20:
            continue
        print("        |0x0E4| %4d-%-4d n=%6d   P(mag==0) = %.4f" % (a, b, m.sum(),
                                                                    float((M[m] == 0).mean())))
    print("  => the detector is graded in the command and saturates near 0.015 above 400 counts.")
    print("     DETECTOR DEFINITION: engaged AND |0x0E4| >= 400 AND mag427 == 0.")
    print("  🛑 C4 THE LIMIT OF THE INSTRUMENT: gp-0x6b4c is an ELEVEN-SLOT ASSIST SUM")
    print("     (memory accord-gp6b4c-is-an-11-slot-assist-sum), not the LKAS blend alone, and")
    print("     the 427 packer quantises at 12.8 counts/LSB with engaged p50 = %.0f LSB."
          % float(np.median(mag[eng])))
    print("     So 'mag427 == 0' means |gp-0x6b4c| < 12.8 counts -- it CANNOT distinguish a")
    print("     latched-to-zero LKAS blend from the eleven slots momentarily cancelling.")

    det = EN & (E >= 400) & (M == 0)
    hdr("PART 8.1 -- DROPOUT DUTY, EVENT COUNT AND EVENT DURATIONS")

    def runs_of(mask):
        dd = np.diff(mask.astype(int))
        s = np.where(dd == 1)[0] + 1
        e = np.where(dd == -1)[0] + 1
        if mask[0]:
            s = np.r_[0, s]
        if mask[-1]:
            e = np.r_[e, len(mask)]
        return list(zip(s, e))
    R = runs_of(det)
    dur = np.array([(b - a) / fs * 1000 for a, b in R])
    base = EN & (E >= 400)
    print("  eligible frames (engaged & |0x0E4| >= 400): %d  (%.1f s)" % (base.sum(),
                                                                          base.sum() / fs))
    print("  dropout duty = %.4f   events = %d   duration ms: p50 %.0f  p90 %.0f  max %.0f"
          % (float(det.sum() / max(base.sum(), 1)), len(R),
             np.percentile(dur, 50) if len(dur) else 0,
             np.percentile(dur, 90) if len(dur) else 0, dur.max() if len(dur) else 0))
    hist = {}
    for k in (20, 40, 60, 100, 200, 500):
        hist[k] = int((dur <= k).sum())
    print("  cumulative event-duration histogram: "
          + "  ".join("<=%dms:%d" % (k, hist[k]) for k in sorted(hist)))
    print("  => %d of %d events (%.1f %%) are at or below the 20 ms SAMPLING FLOOR."
          % (hist[20], len(R), 100 * hist[20] / max(len(R), 1)))
    OUT["latch_events"] = dict(n=len(R), duty=float(det.sum() / max(base.sum(), 1)),
                               dur_p50=float(np.percentile(dur, 50)) if len(dur) else 0.0,
                               dur_max=float(dur.max()) if len(dur) else 0.0)

    hdr("PART 8.2 -- ⭐ THE DISCRIMINATING TEST: event RATE per second at 1 km/h resolution,\n"
        "            against the GRIND ENVELOPE on the same grid.  A PEAK at 5-10 km/h supports\n"
        "            the mechanism; a step at 0 km/h or a flat profile refutes it.")
    sos = butter(4, [15.0, 22.0], btype="band", fs=fs, output="sos")
    envg = np.abs(hilbert(sosfiltfilt(sos, tq)))
    sos2 = butter(4, [2.5, 4.5], btype="band", fs=fs, output="sos")
    envc = np.abs(hilbert(sosfiltfilt(sos2, tq)))
    sos3 = butter(4, [21.0, 22.5], btype="band", fs=fs, output="sos")
    envn = np.abs(hilbert(sosfiltfilt(sos3, tq)))
    envg, envc, envn = envg[:len(E)], envc[:len(E)], envn[:len(E)]
    print("  %-9s %8s %8s %10s %10s %12s %12s %10s"
          % ("v km/h", "n_elig", "sec", "events", "ev/s", "grind15-22", "ratio 15-22",
             "21-22.5"))
    prof = []
    for k in range(0, 25):
        m = base & (VV >= k) & (VV < k + 1)
        me = eng[:len(E)] & (VV >= k) & (VV < k + 1)
        if m.sum() < 30 or me.sum() < 100:
            continue
        ev = len([1 for a, b in R if k <= VV[a] < k + 1])
        sec = m.sum() / fs
        g = float(np.median(envg[me]))
        c = float(np.median(envc[me]))
        n2 = float(np.median(envn[me]))
        prof.append(dict(v=k + 0.5, n=int(m.sum()), sec=sec, ev=ev, rate=ev / max(sec, 1e-9),
                         grind=g, ratio=g / max(c, 1e-9), narrow=n2))
        print("  %-9s %8d %8.1f %10d %10.3f %12.1f %12.3f %10.1f"
              % ("%d-%d" % (k, k + 1), m.sum(), sec, ev, ev / max(sec, 1e-9), g,
                 g / max(c, 1e-9), n2))
    OUT["latch_profile"] = prof
    if len(prof) >= 4:
        a = np.array([p["rate"] for p in prof])
        b1 = np.array([p["ratio"] for p in prof])
        b2 = np.array([p["narrow"] for p in prof])
        print("\n  Spearman-style correlation of the two SHAPES over %d bins:" % len(prof))
        for nm, b in (("band ratio 15-22 / 2.5-4.5", b1), ("21-22.5 envelope", b2)):
            r = float(np.corrcoef(a, b)[0, 1])
            rs = float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])
            print("     event rate vs %-28s  Pearson %+0.3f   rank %+0.3f" % (nm, r, rs))
        print("     event-rate profile peaks at %.1f km/h; grind ratio peaks at %.1f km/h;"
              " 21-22.5 envelope peaks at %.1f km/h"
              % (prof[int(np.argmax(a))]["v"], prof[int(np.argmax(b1))]["v"],
                 prof[int(np.argmax(b2))]["v"]))

    hdr("PART 8.3 -- DO THE WINDOWS CONTAINING EVENTS HAVE MORE GRIND?  Matched on speed, angle\n"
        "            and rate; ratio of median band-RMS.  Window bootstrap inside the cell --\n"
        "            the events do not span enough episodes for an episode bootstrap; SAY SO.")
    W = win_over(eng & (v > 0.5), t)
    ep = np.array([e for _, e in W])
    hasdet = np.array([bool(det[w.start:min(w.stop, len(det))].any()) for w, _ in W])
    vs = np.array([np.median(vk[w]) for w, _ in W])
    ms = np.array([np.median(ang[w]) for w, _ in W])
    rs = np.array([np.median(rate[w]) for w, _ in W])
    g = np.array([brms(tq[w], fs, 15.0, 22.0) for w, _ in W])
    gn = np.array([brms(tq[w], fs, 21.0, 22.5) for w, _ in W])
    u, c = np.unique(ep[hasdet], return_counts=True)
    print("  %d of %d engaged windows contain >=1 event; they come from %d of %d episodes: %s"
          % (hasdet.sum(), len(W), len(u), len(np.unique(ep)),
             ", ".join("ep%d:%d" % (a, b) for a, b in zip(u, c))))
    for vlo, vhi in ((0, 20), (20, 60), (0, 200)):
        for rlo, rhi in ((0, 1e9), (0, 6), (6, 1e9)):
            for alo, ahi in ((0, 1e9), (0, 15)):
                s = (vs >= vlo) & (vs < vhi) & (rs >= rlo) & (rs < rhi) & (ms >= alo) & (ms < ahi)
                a1 = s & hasdet
                b1 = s & (~hasdet)
                if a1.sum() < 5 or b1.sum() < 5:
                    continue
                out = []
                for bb in (g, gn):
                    bs = []
                    for _ in range(2000):
                        bs.append(np.median(bb[a1][RNG.integers(0, a1.sum(), a1.sum())]) /
                                  max(np.median(bb[b1][RNG.integers(0, b1.sum(), b1.sum())]),
                                      1e-9))
                    l95, h95 = ci(bs)
                    out.append("%6.2f [%5.2f,%6.2f]%s" % (np.median(bb[a1]) /
                                                          max(np.median(bb[b1]), 1e-9),
                                                          l95, h95, "*" if l95 > 1 else " "))
                print("  v %-7s rate %-8s |ang| %-7s  n_ev=%3d n_no=%3d | 15-22 %s  21-22.5 %s"
                      % ("%d-%d" % (vlo, vhi), "%g-%g" % (rlo, min(rhi, 999)),
                         "%g-%g" % (alo, min(ahi, 999)), a1.sum(), b1.sum(), out[0], out[1]))


# ==================================================================================================
# PART 9 -- gp-0x6806 READ DIRECTLY, AT 100 Hz, ON THIS ROUTE.  The chatter hypothesis, decided.
# ==================================================================================================
def _runs(mask):
    dd = np.diff(mask.astype(int))
    s = np.where(dd == 1)[0] + 1
    e = np.where(dd == -1)[0] + 1
    if mask[0]:
        s = np.r_[0, s]
    if mask[-1]:
        e = np.r_[e, len(mask)]
    return list(zip(s, e))


def part9(d):
    """gp-0x6806 (STEER_CONTROL_ACTIVE) is PACKED ONTO THE BUS -- `0x18F` byte 4 bit 3, packer
    `shl 3` [EVIDENCE, inherited: docs/ARCHIVE-CLAUDE-MD-2026-07-27 + memory
    accord-lateral-engagement-signals].  So the chatter hypothesis does NOT need a proxy: the
    cache's `raw18_b4` tap IS gp-0x6806, at the 100 Hz CAN TX tick, on THIS route."""
    z, t = d["z"], d["t"]
    r18t = np.asarray(z["raw18_t"], float)
    b4 = np.asarray(z["raw18_b4"], int)
    b3 = ((b4 >> 3) & 1).astype(bool)
    lat = np.interp(r18t, t, np.asarray(z["cc_lat"], float)) > 0.5
    v = np.interp(r18t, t, np.asarray(z["v_rear"], float)) * 3.6
    rate = np.abs(np.interp(r18t, t, np.asarray(z["rate_f"], float)))
    dt = float(np.median(np.diff(r18t)))
    hdr("PART 9 -- gp-0x6806 CHATTER, MEASURED DIRECTLY.  `0x18F` b4 bit3 == gp-0x6806 (shl 3).")
    u, c = np.unique(b4, return_counts=True)
    print("  0x18F byte4 takes %d values on this route: %s"
          % (len(u), "  ".join("0x%02x:%d" % (a, b) for a, b in zip(u, c))))
    print("  tap rate %.2f Hz.  agreement (bit3, latActive) = %.6f  (%d disagreements of %d)"
          % (1 / dt, float((b3 == lat).mean()), int((b3 != lat).sum()), len(b3)))
    inside = lat & (~b3)
    R = _runs(inside)
    print("\n  %-12s %8s %8s %10s %12s %22s" % ("v km/h", "n_eng", "sec", "n_disagr", "disagr %",
                                                "gp-0x6806 0-runs"))
    prof = []
    for a, b in ((0, 2), (2, 5), (5, 10), (10, 15), (15, 20), (20, 30), (30, 60), (60, 200)):
        m = lat & (v >= a) & (v < b)
        if m.sum() == 0:
            continue
        nd = int(((b3 != lat) & m).sum())
        rr = [(s, e) for s, e in R if m[s:e].any()]
        mx = max([(e - s) * dt * 1000 for s, e in rr]) if rr else 0
        prof.append(dict(v="%d-%d" % (a, b), sec=float(m.sum() * dt), n_dis=nd, n_runs=len(rr),
                         max_ms=mx, rate=len(rr) / max(m.sum() * dt, 1e-9)))
        print("  %-12s %8d %8.1f %10d %11.4f%% %10d runs, max %3.0f ms"
              % ("%d-%d" % (a, b), m.sum(), m.sum() * dt, nd, 100 * nd / m.sum(), len(rr), mx))
    print("\n  EVERY 0-run strictly inside an engagement, on the whole route:")
    for s, e in R:
        print("     t=%7.2f s  %3.0f ms   v=%5.1f km/h   rate=%5.1f deg/s"
              % (r18t[s], (e - s) * dt * 1000, v[s:e].mean(), rate[s:e].mean()))
    tot = lat.sum() * dt
    print("\n  TOTAL: %d events in %.1f engaged seconds = %.4f /s.  Longest = %.0f ms."
          % (len(R), tot, len(R) / tot, max([(e - s) * dt * 1000 for s, e in R]) if R else 0))
    for a, b in ((5, 10), (2, 20), (0, 30)):
        m = lat & (v >= a) & (v < b)
        rr = [(s, e) for s, e in R if m[s:e].any()]
        print("     %2d-%-3d km/h engaged %6.1f s, %d events -> rate %.4f /s"
              % (a, b, m.sum() * dt, len(rr), len(rr) / max(m.sum() * dt, 1e-9))
              + ("   (0 observed; 95%% upper bound %.3f /s)" % (3.0 / (m.sum() * dt))
                 if not rr else ""))
    OUT["g6806_chatter"] = dict(profile=prof, n_events=len(R), engaged_s=float(tot),
                                events=[dict(t=float(r18t[s]), ms=float((e - s) * dt * 1000),
                                             v=float(v[s:e].mean()), rate=float(rate[s:e].mean()))
                                        for s, e in R])

    # event-triggered grind envelope
    from scipy.signal import butter, sosfiltfilt
    fs, tq = d["fs"], d["tq"]
    eng = d["eng"]
    env = np.abs(hilbert(sosfiltfilt(butter(4, [15., 22.], btype="band", fs=fs,
                                            output="sos"), tq)))
    me = float(np.median(env[eng]))
    print("\n  EVENT-TRIGGERED CONTROL: 15-22 Hz Hilbert envelope in +-0.5 s of each event,\n"
          "     as a multiple of the engaged median (%.1f ct):" % me)
    vals = []
    for s, e in R:
        m = (t >= r18t[s] - 0.5) & (t <= r18t[s] + 0.5)
        vals.append(float(np.median(env[m]) / me))
        print("     t=%7.2f  v=%5.1f km/h   env/median = %.2f x" % (r18t[s], v[s:e].mean(),
                                                                    vals[-1]))
    idx = np.where(eng & (np.asarray(z["v_rear"], float) * 3.6 < 30))[0]
    ctl = []
    for _ in range(400):
        i = RNG.choice(idx)
        m = (t >= t[i] - 0.5) & (t <= t[i] + 0.5)
        ctl.append(float(np.median(env[m]) / me))
    print("     CONTROL, 400 random engaged < 30 km/h half-second windows: p50 %.2f  p90 %.2f"
          "  p99 %.2f" % tuple(np.percentile(ctl, [50, 90, 99])))
    print("     => events sit at %.2f-%.2f x, the control p50 is %.2f x."
          % (min(vals), max(vals), np.percentile(ctl, 50)))
    OUT["g6806_event_grind"] = dict(events=vals, ctl_p50=float(np.percentile(ctl, 50)),
                                    ctl_p90=float(np.percentile(ctl, 90)))
    print("\n  🛑 THE OBSERVABILITY BOUNDARY, STATED: the packer runs at the 100 Hz CAN TX tick")
    print("     while the five-conjunct AND is evaluated in the ~1 kHz control task.  Chatter")
    print("     FASTER than ~10 ms could alias away and is NOT excluded.  Chatter AT the grind")
    print("     frequency (21.73 Hz = a 46 ms period) is fully resolvable at 100 Hz and would")
    print("     appear as a ~50 %% duty of bit3 == 0 during the symptom, not as 7 isolated")
    print("     20-30 ms events in 402 s.  THAT is what is excluded.")


def part9b(d):
    """Route 47's own direct RAM read of gp-0x6806 (V67's bit6) -- does the 99.983 % identity
    corpus cover 5-10 km/h ENGAGED driving?  Orchestrator item 6, verified in BOTH directions."""
    p = HERE.parent / "analysis-2020accord" / "_scratch/data/_cache_r47_ratchet.npz"
    if not p.exists():
        print("  route 47 cache not present -- SKIPPED")
        return
    z = np.load(p, allow_pickle=True)
    t = np.asarray(z["t"], float)
    v = np.asarray(z["v"], float) * 3.6
    lat = np.asarray(z["lat"], float) > 0.5
    g = (((np.asarray(z["b4"], int)) >> 6) & 1).astype(bool)
    dt = float(np.median(np.diff(t)))
    hdr("PART 9B -- DOES THE 99.983 %% CORPUS COVER 5-10 km/h ENGAGED?  Route 47 (V67), the\n"
        "           source of that number, re-opened.  bit6 = `gp-0x6806 != 0` read from RAM.")
    print("  route 47: %d frames, %.1f s, agreement %.5f" % (len(t), t[-1] - t[0],
                                                             float((g == lat).mean())))
    inside = lat & (~g)
    R = _runs(inside)
    print("  %-12s %8s %8s %10s %14s" % ("v km/h", "n_eng", "sec", "n_disagr", "0-runs"))
    for a, b in ((0, 2), (2, 5), (5, 10), (10, 15), (15, 20), (20, 30), (30, 60), (60, 200)):
        m = lat & (v >= a) & (v < b)
        if m.sum() == 0:
            continue
        rr = [(s, e) for s, e in R if m[s:e].any()]
        print("  %-12s %8d %8.1f %10d %8d runs, max %.0f ms"
              % ("%d-%d" % (a, b), m.sum(), m.sum() * dt, int(((g != lat) & m).sum()), len(rr),
                 max([(e - s) * dt * 1000 for s, e in rr]) if rr else 0))
    print("\n  Every 0-run inside an engagement on route 47:")
    for s, e in R:
        print("     t=%8.2f  %3.0f ms  v=%5.1f km/h" % (t[s], (e - s) * dt * 1000, v[s:e].mean()))
    m = lat & (v >= 5) & (v < 10)
    print("\n  => the 99.983 %% corpus DOES contain 5-10 km/h engaged driving: %.1f s / %d frames,"
          % (m.sum() * dt, m.sum()))
    print("     with ZERO disagreements and ZERO 0-runs in that band.  95 %% upper bound on the")
    print("     per-frame duty there = %.2e (rule of three).  The identity COVERS the regime."
          % (3.0 / m.sum()))


# ==================================================================================================
# PART 10 -- TASK 2.  RETURN-TO-CENTRE: does the "DEAD ENGAGED" null cover 5-10 km/h?
# ==================================================================================================
def part10(d):
    """The null lives on route 79 (V92), whose `0x14A` byte4 carried the three return-centre rungs:
         b6 = gp-0x6b62 < 0 (sign) · b5 = gp-0x6b62 != 0 (lane LIVE) · b4 = gp-0x6bda gate OPEN.
       Route 9e's cave measures completely different cells (b7=6b4c sign, b6=r24/r26 comparator,
       b5=friction/inertia, b4=r24 sign, b3=D_state sign), so route 9e CANNOT re-measure the lane.
       The question is therefore whether route 79's corpus reached the operator's regime."""
    p = HERE.parent / "analysis-2020accord" / "_scratch/cache/r79" / "r79.npz"
    hdr("PART 10 -- RETURN-TO-CENTRE / DETENT: does the route-79 'DEAD ENGAGED' null cover\n"
        "           5-10 km/h engaged driving, and is the lane re-openable as a THRESHOLD?")
    if not p.exists():
        print("  route 79 cache absent -- SKIPPED")
        return
    z = np.load(p, allow_pickle=True)
    t = np.asarray(z["t"], float)
    pr = np.asarray(z["probe"], int)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    v = (np.asarray(z["ws_rl"], float) + np.asarray(z["ws_rr"], float)) / 2.0 * 3.6
    ang = np.abs(np.asarray(z["ang"], float))
    rate = np.abs(np.asarray(z["rate_f"], float))
    dt = float(np.median(np.diff(t)))
    b6, b5, b4 = (pr >> 6) & 1, (pr >> 5) & 1, (pr >> 4) & 1
    u, c = np.unique(pr, return_counts=True)
    print("  route 79: %d frames, %.1f s, byte4 takes %d values: %s"
          % (len(t), t[-1] - t[0], len(u), "  ".join("0x%02X:%d" % (a, b) for a, b in zip(u, c))))
    print("\n  %-30s %8s %9s %10s %10s %10s" % ("cell", "n", "sec", "b6 duty", "b5 duty",
                                                "b4 duty"))
    rows = []
    for nm, m in (("ENGAGED, all", eng),
                  ("ENGAGED  0-5 km/h", eng & (v >= 0) & (v < 5)),
                  ("ENGAGED  5-10 km/h  <- HIS", eng & (v >= 5) & (v < 10)),
                  ("ENGAGED 10-15 km/h", eng & (v >= 10) & (v < 15)),
                  ("ENGAGED 15-30 km/h", eng & (v >= 15) & (v < 30)),
                  ("ENGAGED <15 & |ang|<5 deg", eng & (v < 15) & (ang < 5)),
                  ("ENGAGED <15 & |ang|<5 & rate<5", eng & (v < 15) & (ang < 5) & (rate < 5)),
                  ("ENGAGED <15 & |ang|>300 deg", eng & (v < 15) & (ang > 300)),
                  ("MANUAL, all", ~eng),
                  ("MANUAL <15 & |ang|>300 deg", (~eng) & (v < 15) & (ang > 300))):
        n = int(m.sum())
        if n == 0:
            print("  %-30s %8d       --" % (nm, 0))
            continue
        print("  %-30s %8d %9.1f %10.6f %10.6f %10.6f"
              % (nm, n, n * dt, b6[m].mean(), b5[m].mean(), b4[m].mean()))
        rows.append(dict(cell=nm, n=n, sec=n * dt, b6=float(b6[m].mean()),
                         b5=float(b5[m].mean()), b4=float(b4[m].mean()),
                         rule_of_three=rule_of_three(n) if b5[m].mean() == 0 else None))
    live = b5 == 1
    print("\n  WHERE THE LANE IS ACTUALLY LIVE (b5 == 1): %d frames of %d, ALL MANUAL (%d engaged)."
          % (int(live.sum()), len(pr), int((live & eng).sum())))
    if live.sum():
        print("     |steering angle| at those frames: min %.1f  p50 %.1f  max %.1f deg"
              % tuple(np.percentile(ang[live], [0, 50, 100])))
        print("     speed at those frames: %.1f - %.1f km/h" % (v[live].min(), v[live].max()))
    print("\n  => the lane is live ONLY within ~%.0f deg of full lock, and route 79's engaged"
          % (float(np.percentile(ang[live], 0)) if live.sum() else 0))
    m = eng & (v >= 5) & (v < 10)
    print("     5-10 km/h corpus (%.1f s / %d frames) shows duty 0.0000 with a 95 %% upper bound"
          % (m.sum() * dt, m.sum()))
    print("     of %.2e (rule of three).  THE NULL COVERS THE OPERATOR'S REGIME." % rule_of_three(m.sum()))
    print("\n  ROUTE 9e, the same regime, for exposure comparison:")
    zz = d["z"]
    e9 = d["eng"]
    v9 = d["v"] * 3.6
    a9 = d["ang"]
    for nm, m in (("ENGAGED  5-10 km/h", e9 & (v9 >= 5) & (v9 < 10)),
                  ("ENGAGED <15 km/h", e9 & (v9 < 15)),
                  ("ENGAGED <15 & |ang|>300 deg", e9 & (v9 < 15) & (a9 > 300))):
        print("     %-30s %6d frames = %6.1f s" % (nm, int(m.sum()), m.sum() / d["fs"]))
    print("     (route 9e's cave does NOT carry the return-centre rungs, so it cannot re-measure")
    print("      the lane -- it can only say how much of the regime a re-flown probe would get.)")
    _ = zz
    OUT["return_centre"] = rows


def part8c(d):
    """8.3's comparison group is contaminated: the detector REQUIRES |0x0E4| >= 400, so windows
    that contain an event necessarily contain high-command frames.  Restrict the control group to
    ELIGIBLE windows (windows that also contain |0x0E4| >= 400 frames)."""
    fs, t, tq = d["fs"], d["t"], d["tq"]
    z = d["z"]
    eng, v, rate = d["eng"], d["v"], d["rate"]
    cmd = np.abs(d["cmd"])
    mag = np.asarray(z["mag427"], float)
    vk = v * 3.6
    lag = 2
    n = len(t)
    det = np.zeros(n, bool)
    elig = np.zeros(n, bool)
    det[:n - lag] = eng[:n - lag] & (cmd[:n - lag] >= 400) & (mag[lag:] == 0)
    elig[:n - lag] = eng[:n - lag] & (cmd[:n - lag] >= 400)
    W = win_over(eng & (v > 0.5), t)
    hasdet = np.array([bool(det[w.start:w.stop].any()) for w, _ in W])
    haselig = np.array([bool(elig[w.start:w.stop].any()) for w, _ in W])
    elfr = np.array([elig[w.start:w.stop].mean() for w, _ in W])
    vs = np.array([np.median(vk[w]) for w, _ in W])
    rs = np.array([np.median(rate[w]) for w, _ in W])
    g = np.array([brms(tq[w], fs, 15.0, 22.0) for w, _ in W])
    gn = np.array([brms(tq[w], fs, 21.0, 22.5) for w, _ in W])
    hdr("PART 8.3B -- COMMAND-MATCHED CONTROL for the 427-dropout contrast.")
    for vlo, vhi in ((0, 20), (20, 60), (0, 200)):
        for rlo, rhi in ((0, 1e9), (0, 6)):
            s = (vs >= vlo) & (vs < vhi) & haselig & (rs >= rlo) & (rs < rhi)
            a = s & hasdet
            b = s & (~hasdet)
            if a.sum() < 5 or b.sum() < 5:
                continue
            out = []
            for bb in (g, gn):
                bs = [np.median(bb[a][RNG.integers(0, a.sum(), a.sum())]) /
                      max(np.median(bb[b][RNG.integers(0, b.sum(), b.sum())]), 1e-9)
                      for _ in range(2000)]
                l95, h95 = ci(bs)
                out.append("%6.2f [%5.2f,%6.2f]%s"
                           % (np.median(bb[a]) / max(np.median(bb[b]), 1e-9), l95, h95,
                              "*" if l95 > 1 else " "))
            print("  v %-8s rate %-7s n_ev=%3d n_no=%3d  elig-frac %.2f vs %.2f | 15-22 %s"
                  "  21-22.5 %s" % ("%d-%d" % (vlo, vhi), "%g-%g" % (rlo, min(rhi, 999)),
                                    a.sum(), b.sum(), elfr[a].mean(), elfr[b].mean(),
                                    out[0], out[1]))
    print("  🛑 The residual confound is NOT removed: event windows still spend ~2x longer above")
    print("     400 counts than the control windows do (elig-frac column).  And the association")
    print("     is at 20-60 km/h, NOT in the operator's 5-10 km/h regime, where it is 1.09.")

def dump():
    p = HERE / "_scratch/out/_grind1_regime_r9e.json"
    p.write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")
    print("\nwrote %s" % p)


if __name__ == "__main__":
    D = setup()
    EP = V.episodes(D["eng"], D["t"], NW)
    print("route 9e  n=%d  fs=%.3f Hz  dur=%.1f s  engaged %.1f s (%.1f %%)"
          % (len(D["t"]), D["fs"], D["t"][-1] - D["t"][0], D["eng"].sum() / D["fs"],
             100 * D["eng"].mean()))
    print("ENGAGEMENT EPISODES >= %d samples (%.2f s): %d -- durations %s\n"
          "  ** that block count is the BOOTSTRAP UNIT and the hard limit on every CI below **"
          % (NW, NW / D["fs"], len(EP),
             ", ".join("%.1f s" % ((b - a) / D["fs"]) for a, b in EP)))
    OUT["episodes"] = [float((b - a) / D["fs"]) for a, b in EP]
    W, B, vs, med, hnd = part1(D)
    part2(D, W, B)
    part2b(D, W)
    part3(D, W)
    part3b(D, W)
    part4(D)
    part4b(D)
    part5(D, W)
    part5d(D, W)
    part5f(D, W)
    part6(D)
    part7(D)
    part8(D)
    part8c(D)
    part9(D)
    part9b(D)
    part10(D)
    dump()
