#!/usr/bin/env python3
"""RATCHET DISCRIMINATORS -- three zero-byte tests on data already on disk.

The linear-loop-oscillation hypothesis died with V86 (ratio 1.001 [0.976, 1.060] against a
pre-registered [0.797, 0.875]).  What survives:
    H1  a structural/mechanical mode OTHER than the 12.8 Hz wheel-on-bar one
    H2  friction stick-slip driven by the assist loop     (a NON-odd-symmetric nonlinearity)
    H3  a quantiser / deadband limit cycle                (likewise)
    H4  a task-rate / scheduling beat

TEST A  does f_c move with steering LOAD, at fixed speed?      H1 predicts yes, H3 predicts no
TEST B  does the 8 Hz line depend on the FRICTION rungs?       H2's only direct instrument (r6e)
TEST C  does f_c move with the line's own AMPLITUDE?           H1 predicts NO, H2/H3 predict YES

🛑 THE INSTRUMENT IS `v86_freq_test.py`'s, IMPORTED.  `spectra` / `in_speed` / `order_clean` /
`autocorr_check` are used verbatim, and `v86_freq_part3.shift_line` is the corpus's faithful
frequency-shift surrogate, reused for the POWER curves.  `windows_ext` is `v86_freq_test.windows`
with EXTRA METADATA recorded per window and nothing else changed -- `verify_instrument()` asserts
window-for-window identity (t0, blk, v, and a SHA1 of the sample vector) against the imported
original before any test runs.

🛑 PRIMARY ARM = `V86.in_speed` (0.5-5.0 m/s), engaged, NO order-clean -- exactly the arm
   `v86_freq_part3` scored.  Order-cleaned and detection-floored variants are reported as
   robustness, never as the headline.  (order_clean drops wheel orders 1-4 from 5-12 Hz, which at
   2.6-5.0 m/s means order 4 -- it removes HALF the parking-lot windows.)
🛑 RESAMPLING UNIT = `blk` (~10.13 s contiguous block).  Never windows, never episodes.
🛑 NULLS ARE COMPUTED IN §0, BEFORE ANY EFFECT IS LOOKED AT.
🛑 The dominant artefact risk is the ESTIMATOR: a window with no line has a free 5-12 Hz argmax
   that is ~uniform, so its median sits near the band centre.  Controlled four ways --
   (a) a detection floor taken from the DISENGAGED windows in §0,
   (b) the same binning re-run on DISENGAGED windows as an explicit negative control,
   (c) amplitude/load terciles taken on the WITHIN-SPEED-BIN rank, so they are speed-balanced,
   (d) POWER CURVES: a synthetic amplitude- (or load-) dependent frequency shift of known size is
       injected with `shift_line` and re-measured, so "no effect" is only ever reported alongside
       the smallest effect that WOULD have fired.

usage:  python ratchet_discriminators.py
out:    _cache_r6f/ratchet_discriminators.json
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G            # noqa: E402,F401  (used inside V86.spectra)
import _r31_common as C31          # noqa: E402
import v86_freq_test as V86        # noqa: E402  -- THE instrument
from v86_freq_part3 import shift_line   # noqa: E402  -- the corpus's faithful surrogate

NW, HOPW = V86.NW, V86.HOPW
FLO, FHI = V86.FLO, V86.FHI
RNG = np.random.default_rng(8_790_142)
NBOOT = 4000
NPERM = 1500

SBINS = [(0.5, 1.5), (1.5, 2.78), (2.78, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 40.0)]
AMP_BAND = (5.5, 10.5)          # fixed -> amplitude does NOT depend on the argmax
AMP_BAND_TIGHT = (6.0, 9.0)

ROUTES = {
    "V86/r6f":  ("_cache_r6f",  "r6fs",  list(range(4))),
    "V85/r6e":  ("_cache_r6e",  "r6es",  list(range(7))),
    "V86B/r70": ("_cache_r70",  "r70s",  list(range(4))),
    "V84/r6d":  ("_cache_r6d",  "r6ds",  list(range(11))),
    "V81/r67":  ("_cache_r67x", "r67xs", list(range(13))),
}
SCORED = ["V86/r6f", "V86B/r70", "V85/r6e"]      # 6d/67 too thin at low speed -> census only
THIN = ["V84/r6d", "V81/r67"]
FRICTION_ROUTE = "V85/r6e"                        # the ONLY build carrying the friction rungs

OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


# =================================================================================================
#  WINDOWING -- V86.windows + extra metadata.  Nothing else differs.
# =================================================================================================
AUX = {
    "ld_ang":   ("ang",      lambda a: float(np.median(np.abs(a)))),
    "ld_tqdc":  ("tq",       lambda a: float(np.abs(np.median(a)))),
    "ld_tqabs": ("tq",       lambda a: float(np.median(np.abs(a)))),
    "ld_rate":  ("rate_c",   lambda a: float(np.median(np.abs(a)))),
    "ld_e4":    ("e4tq",     lambda a: float(np.median(np.abs(a)))),
    "ld_co":    ("co_req",   lambda a: float(np.median(np.abs(a)))),
    "ld_cstq":  ("cs_tq",    lambda a: float(np.median(np.abs(a)))),
    "f_rev":    ("cs_gear",  lambda a: float(np.mean(np.asarray(a) == 4.0))),
    "f_still":  ("cs_std",   lambda a: float(np.mean(np.asarray(a) > 0.5))),
    "f_press":  ("cs_press", lambda a: float(np.mean(np.asarray(a) > 0.5))),
}
FRIC = {                       # V85 `0x14A` byte-4 rungs -- ROUTE 6e ONLY
    "b5_fric_hi": "v85_fric_hi",    # |gp-0x6ae2| >= 8    FRICTION x1024, HIGH rung
    "b4_fric_lo": "v85_fric_lo",    # |gp-0x6ae2| >= 2    FRICTION x1024, LOW rung
    "b6_rate_hi": "v85_rate_hi",    # |gp-0x6abc| >= 512  motor RATE, HIGH rung
    "b7_rate_lo": "v85_rate_lo",    # |gp-0x6abc| >= 64   motor RATE, LOW rung
}


def windows_ext(route, cache, pfx, segs, engaged=True, sig="tq", nw=NW, hopw=HOPW):
    b_lf = butter(2, [0.5, 4.0], btype="band", fs=101.0)
    b_bp = butter(2, [6.0, 9.0], btype="band", fs=101.0)
    b_amp = butter(2, list(AMP_BAND), btype="band", fs=101.0)
    b_amt = butter(2, list(AMP_BAND_TIGHT), btype="band", fs=101.0)
    out = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, ROOT / cache, pfx)
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        x = np.asarray(d[sig], float)
        v = np.asarray(d["cs_v"], float)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        mask = lat if engaged else ~lat
        for a, b in C31.runs_of(mask, t, nw):
            x_lf = filtfilt(*b_lf, x[a:b])
            x_bp = filtfilt(*b_bp, x[a:b])
            env = np.abs(hilbert(x_bp))
            e_amp = np.abs(hilbert(filtfilt(*b_amp, x[a:b])))
            e_amt = np.abs(hilbert(filtfilt(*b_amt, x[a:b])))
            for j0 in range(0, (b - a) - nw + 1, hopw):
                sl = slice(j0, j0 + nw)
                seg = x[a:b][sl]
                if not np.all(np.isfinite(seg)):
                    continue
                vv = v[a:b][sl]
                r = dict(build=route, seg=int(s), t0=float(t[a:b][sl][0]),
                         blk=f"{s}:{a}:{j0 // (hopw * 2)}", ep=f"{s}:{a}",
                         v=float(np.median(vv)), vlo=float(np.min(vv)),
                         vhi=float(np.max(vv)), fs=float(fs),
                         x=seg, x_lf=x_lf[sl], env=env[sl])
                r["amp"] = float(np.percentile(e_amp[sl], 99))
                r["amp69"] = float(np.percentile(e_amt[sl], 99))
                for k, (fld, red) in AUX.items():
                    r[k] = red(np.asarray(d[fld], float)[a:b][sl]) if fld in d else np.nan
                for k, fld in FRIC.items():
                    r[k] = (float(np.mean(np.asarray(d[fld], float)[a:b][sl] > 0.5))
                            if fld in d else np.nan)
                out.append(r)
    return out


def verify_instrument():
    ok = {}
    for route in SCORED:
        cache, pfx, segs = ROUTES[route]
        A = V86.windows(route, cache, pfx, segs, engaged=True)
        B = windows_ext(route, cache, pfx, segs, engaged=True)
        same = len(A) == len(B)
        if same:
            for ra, rb in zip(A, B):
                if (ra["t0"] != rb["t0"] or ra["blk"] != rb["blk"] or ra["v"] != rb["v"]
                        or hashlib.sha1(ra["x"].tobytes()).hexdigest()
                        != hashlib.sha1(rb["x"].tobytes()).hexdigest()):
                    same = False
                    break
        ok[route] = dict(n_ref=len(A), n_ext=len(B), identical=bool(same))
        print(f"    {route:10s}  n={len(A):4d} vs {len(B):4d}   identical={same}")
        assert same, f"windows_ext DIVERGED from the corpus instrument on {route}"
    return ok


# =================================================================================================
#  statistics -- block resampling throughout
# =================================================================================================
def blocks_of(rs):
    g = {}
    for r in rs:
        g.setdefault(r["blk"], []).append(r)
    return g


def boot_blocks(rs, fn, nboot=NBOOT, rng=None):
    rng = rng or RNG
    g = blocks_of(rs)
    keys = list(g)
    if len(keys) < 4:
        return dict(pt=np.nan, lo=np.nan, hi=np.nan, sd=np.nan, n=len(rs), nblk=len(keys),
                    status="UNDERPOWERED")
    try:
        pt = fn(rs)
    except Exception:
        pt = np.nan
    draws = []
    for _ in range(nboot):
        idx = rng.integers(0, len(keys), len(keys))
        samp = [r for i in idx for r in g[keys[i]]]
        try:
            val = fn(samp)
        except Exception:
            val = np.nan
        if np.isfinite(val):
            draws.append(val)
    draws = np.asarray(draws, float)
    if len(draws) < 100:
        return dict(pt=float(pt), lo=np.nan, hi=np.nan, sd=np.nan, n=len(rs), nblk=len(keys),
                    ndraw=len(draws), status="UNDERPOWERED")
    return dict(pt=float(pt), lo=float(np.percentile(draws, 2.5)),
                hi=float(np.percentile(draws, 97.5)), sd=float(np.std(draws, ddof=1)),
                n=len(rs), nblk=len(keys), ndraw=len(draws), status="OK")


def sbin_of(v):
    for i, (lo, hi) in enumerate(SBINS):
        if lo <= v < hi:
            return i
    return -1


def resid_slope(rs, xkey, ykey="f_free", min_per_bin=4):
    """OLS slope of y on x after removing each SPEED BIN's median from both -> within-stratum."""
    by = {}
    for r in rs:
        if np.isfinite(r.get(xkey, np.nan)) and np.isfinite(r.get(ykey, np.nan)):
            by.setdefault(sbin_of(r["v"]), []).append(r)
    xs, ys = [], []
    for k, v in by.items():
        if k < 0 or len(v) < min_per_bin:
            continue
        mx = float(np.median([r[xkey] for r in v]))
        my = float(np.median([r[ykey] for r in v]))
        xs += [r[xkey] - mx for r in v]
        ys += [r[ykey] - my for r in v]
    if len(xs) < 8:
        return np.nan
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    sx = float(np.sum((xs - xs.mean()) ** 2))
    if sx <= 0:
        return np.nan
    return float(np.sum((xs - xs.mean()) * (ys - ys.mean())) / sx)


def resid_spearman(rs, xkey, ykey="f_free", min_per_bin=4):
    from scipy.stats import spearmanr
    by = {}
    for r in rs:
        if np.isfinite(r.get(xkey, np.nan)) and np.isfinite(r.get(ykey, np.nan)):
            by.setdefault(sbin_of(r["v"]), []).append(r)
    xs, ys = [], []
    for k, v in by.items():
        if k < 0 or len(v) < min_per_bin:
            continue
        xs += list(np.argsort(np.argsort([r[xkey] for r in v])) / max(len(v) - 1, 1))
        ys += list(np.argsort(np.argsort([r[ykey] for r in v])) / max(len(v) - 1, 1))
    if len(xs) < 8:
        return np.nan
    s = spearmanr(xs, ys).statistic
    return float(s) if np.isfinite(s) else np.nan


def within_bin_rank(rs, key):
    """Rank of `key` inside the record's OWN speed bin, in [0,1] -> terciles are speed-balanced."""
    rs = [dict(r) for r in rs]
    by = {}
    for r in rs:
        by.setdefault(sbin_of(r["v"]), []).append(r)
    for k, v in by.items():
        vals = np.array([r.get(key, np.nan) for r in v], float)
        order = np.argsort(np.argsort(np.where(np.isfinite(vals), vals, -np.inf)))
        for r, o in zip(v, order):
            r[key + "_rk"] = float(o) / max(len(v) - 1, 1)
    return rs


def med_of(rs, key):
    v = [r[key] for r in rs if np.isfinite(r.get(key, np.nan))]
    return float(np.median(v)) if v else np.nan


def d_terciles(rs, key, ykey="f_free"):
    hi = [r["f_free"] for r in rs if r[key + "_rk"] >= 2 / 3 and np.isfinite(r[ykey])]
    lo = [r["f_free"] for r in rs if r[key + "_rk"] <= 1 / 3 and np.isfinite(r[ykey])]
    if len(hi) < 2 or len(lo) < 2:
        return np.nan
    return float(np.median(hi) - np.median(lo))


# =================================================================================================
#  §0  NULLS
# =================================================================================================
def split_half_null(rs, key="f_free", nrep=2000, rng=None):
    rng = rng or RNG
    g = blocks_of([r for r in rs if np.isfinite(r.get(key, np.nan))])
    keys = list(g)
    if len(keys) < 6:
        return dict(nblk=len(keys), status="UNDERPOWERED")
    dif, rat = [], []
    for _ in range(nrep):
        perm = rng.permutation(len(keys))
        h = len(keys) // 2
        a = np.median([r[key] for i in perm[:h] for r in g[keys[i]]])
        b = np.median([r[key] for i in perm[h:] for r in g[keys[i]]])
        dif.append(a - b)
        rat.append(a / b)
    dif, rat = np.asarray(dif), np.asarray(rat)
    return dict(nblk=len(keys), n=sum(len(v) for v in g.values()), status="OK",
                d_p2p5=float(np.percentile(dif, 2.5)), d_p97p5=float(np.percentile(dif, 97.5)),
                d_sd=float(dif.std(ddof=1)),
                r_p2p5=float(np.percentile(rat, 2.5)), r_p97p5=float(np.percentile(rat, 97.5)))


def perm_null(rs, xkey, stat, nrep=NPERM, rng=None):
    """Block-label permutation of the x column: each block keeps its own y, but is handed a
    DIFFERENT block's x values.  Preserves both marginals and within-block structure."""
    rng = rng or RNG
    g = blocks_of([r for r in rs if np.isfinite(r.get(xkey, np.nan))
                   and np.isfinite(r.get("f_free", np.nan))])
    keys = list(g)
    if len(keys) < 6:
        return dict(nblk=len(keys), status="UNDERPOWERED")
    draws = []
    for _ in range(nrep):
        perm = rng.permutation(len(keys))
        sh = []
        for i, k in enumerate(keys):
            src = g[keys[perm[i]]]
            for j, r in enumerate(g[k]):
                q = dict(r)
                q[xkey] = src[j % len(src)][xkey]
                sh.append(q)
        try:
            s = stat(sh)
        except Exception:
            s = np.nan
        if np.isfinite(s):
            draws.append(s)
    d = np.asarray(draws, float)
    if len(d) < 100:
        return dict(nblk=len(keys), status="UNDERPOWERED", ndraw=len(d))
    return dict(nblk=len(keys), status="OK", ndraw=len(d), sd=float(d.std(ddof=1)),
                p2p5=float(np.percentile(d, 2.5)), p97p5=float(np.percentile(d, 97.5)))


def sim_prom_floor(nrep=3000, rng=None):
    """What free-argmax prominence does a FEATURELESS spectrum give?  White and red (1/f^2)
    noise through the identical periodogram + prom_spectrum + 5-12 Hz argmax."""
    rng = rng or RNG
    res = {}
    for kind in ("white", "red"):
        vals = []
        for _ in range(nrep):
            w = rng.standard_normal(NW)
            if kind == "red":
                X = np.fft.rfft(w)
                fr = np.fft.rfftfreq(NW, 1 / 101.04)
                X[1:] /= np.maximum(fr[1:], 0.1) ** 1.0
                w = np.fft.irfft(X, NW)
            q = dict(x=w, fs=101.04, v=1.0, blk="s", ep="s", t0=0.0)
            V86.spectra([q])
            if np.isfinite(q["p_free"]):
                vals.append(q["p_free"])
        v = np.asarray(vals)
        res[kind] = {f"p{k}": float(np.percentile(v, k)) for k in (50, 90, 95, 99)}
        res[kind]["n"] = len(v)
    return res


# =================================================================================================
#  POWER -- inject a KNOWN coupling with the corpus's own shift_line, re-measure
# =================================================================================================
def power_curve(rs, key, f0, deltas, ykey="f_free", nrep=1, rng=None):
    """Impose f = f0 + delta*(rank(key) - 0.5) window by window, re-run the instrument, and report
    the recovered T3-T1 difference with its block-bootstrap CI.  The smallest delta whose CI
    excludes 0 is the minimum detectable coupling."""
    rng = rng or RNG
    base = within_bin_rank(rs, key)
    out = []
    for dlt in deltas:
        rep = []
        for r in base:
            x = shift_line(r, f0, f0 + dlt * (r[key + "_rk"] - 0.5))
            q = dict(x=x, fs=r["fs"], v=r["v"], blk=r["blk"], ep=r["ep"], t0=r["t0"])
            V86.spectra([q])
            q[key + "_rk"] = r[key + "_rk"]
            rep.append(q)
        b = boot_blocks(rep, lambda z, k=key: d_terciles(z, k), nboot=1500, rng=rng)
        sig = bool(np.isfinite(b["lo"]) and (b["lo"] > 0 or b["hi"] < 0))
        out.append(dict(delta=float(dlt), recovered=b["pt"], lo=b["lo"], hi=b["hi"],
                        nblk=b["nblk"], sig=sig))
        print(f"      delta {dlt:+.2f} Hz  ->  recovered {b['pt']:+.3f} "
              f"[{b['lo']:+.3f},{b['hi']:+.3f}]  {'DETECTED' if sig else 'not detected'}")
    mde = next((o["delta"] for o in out if o["sig"] and o["delta"] > 0), None)
    return dict(curve=out, mde_delta_Hz=mde)


# =================================================================================================
def census(rs, label):
    if not rs:
        print(f"    {label:26s}  n=0")
        return dict(n=0)
    cnt = [sum(1 for r in rs if sbin_of(r["v"]) == i) for i in range(len(SBINS))]
    c = dict(n=len(rs), nblk=len(blocks_of(rs)), sbins=cnt, v_med=med_of(rs, "v"),
             rev_frac=float(np.mean([r["f_rev"] for r in rs])),
             still_frac=float(np.mean([r["f_still"] for r in rs])),
             press_frac=float(np.mean([r["f_press"] for r in rs])))
    print(f"    {label:26s}  n={c['n']:4d} blk={c['nblk']:3d} v~{c['v_med']:5.2f} "
          f"sbin={cnt} rev={c['rev_frac']:.3f} still={c['still_frac']:.3f} "
          f"press={c['press_frac']:.3f}")
    return c


def tercile_report(rs, tag, key="amp", pfloor=None):
    if pfloor is not None:
        rs = [r for r in rs if np.isfinite(r["p_free"]) and r["p_free"] >= pfloor]
    rs = [r for r in rs if np.isfinite(r["f_free"])]
    rs = within_bin_rank(rs, key)
    T = {"T1": [r for r in rs if r[key + "_rk"] <= 1 / 3],
         "T2": [r for r in rs if 1 / 3 < r[key + "_rk"] < 2 / 3],
         "T3": [r for r in rs if r[key + "_rk"] >= 2 / 3]}
    res = {"n": len(rs), "nblk": len(blocks_of(rs))}
    for name, sel in T.items():
        if len(sel) < 5:
            res[name] = dict(status="UNDERPOWERED", n=len(sel))
            continue
        fb = boot_blocks(sel, lambda z: float(np.median([q["f_free"] for q in z])), nboot=2000)
        res[name] = dict(status=fb.get("status", "OK"), n=len(sel), nblk=fb["nblk"],
                         fc=fb["pt"], lo=fb["lo"], hi=fb["hi"],
                         amp_med=med_of(sel, key), v_med=med_of(sel, "v"),
                         p_med=med_of(sel, "p_free"),
                         sbins=[sum(1 for r in sel if sbin_of(r["v"]) == i)
                                for i in range(len(SBINS))])
    if res["T1"].get("status") == "OK" and res["T3"].get("status") == "OK":
        d = boot_blocks(rs, lambda z, k=key: d_terciles(z, k), nboot=2000)
        ar = (res["T3"]["amp_med"] / res["T1"]["amp_med"]) if res["T1"]["amp_med"] else np.nan
        res["delta_T3_T1"] = dict(df=d["pt"], lo=d["lo"], hi=d["hi"], nblk=d["nblk"],
                                  amp_ratio=float(ar),
                                  sig=bool(np.isfinite(d["lo"]) and (d["lo"] > 0 or d["hi"] < 0)))
        print(f"    {tag:24s} n={res['n']:3d} blk={res['nblk']:3d} | T1 {res['T1']['fc']:.3f}"
              f"[{res['T1']['lo']:.2f},{res['T1']['hi']:.2f}] T3 {res['T3']['fc']:.3f}"
              f"[{res['T3']['lo']:.2f},{res['T3']['hi']:.2f}] | Δ {d['pt']:+.3f}"
              f"[{d['lo']:+.3f},{d['hi']:+.3f}] Hz  {key}×{ar:.2f}  "
              f"{'SIG' if res['delta_T3_T1']['sig'] else '-'}")
    else:
        res["delta_T3_T1"] = dict(status="UNDERPOWERED")
        print(f"    {tag:24s} UNDERPOWERED  n(T1,T2,T3)="
              f"{[res[n].get('n') for n in ('T1', 'T2', 'T3')]}")
    return res


# =================================================================================================
def main():
    hdr("§-1  INSTRUMENT IDENTITY -- windows_ext must equal v86_freq_test.windows")
    OUT["instrument_identity"] = verify_instrument()

    hdr("LOAD + SPECTRA   (primary arm = V86.in_speed 0.5-5.0 m/s, engaged, NO order-clean)")
    ENG, MAN, ENG_ALLV = {}, {}, {}
    for route, (cache, pfx, segs) in ROUTES.items():
        e = V86.spectra(windows_ext(route, cache, pfx, segs, engaged=True))
        m = V86.spectra(windows_ext(route, cache, pfx, segs, engaged=False))
        ENG_ALLV[route] = e
        ENG[route] = V86.in_speed(e)
        MAN[route] = V86.in_speed(m)
        print(f"  {route:10s} engaged all-v {len(e):4d} -> in-speed {len(ENG[route]):4d} "
              f"(order-clean {len(V86.order_clean(ENG[route])):4d})   manual in-speed "
              f"{len(MAN[route]):4d}")
    OUT["census"] = {r: dict(engaged=census(ENG[r], r + " eng 0.5-5"),
                             engaged_allv=census(ENG_ALLV[r], r + " eng all-v"),
                             manual=census(MAN[r], r + " man 0.5-5")) for r in ROUTES}

    POOL = []
    for route in SCORED:
        for r in ENG[route]:
            q = dict(r)
            q["blk"] = route + "|" + r["blk"]
            POOL.append(q)
    POOL_MAN = []
    for route in SCORED:
        for r in MAN[route]:
            q = dict(r)
            q["blk"] = route + "|" + r["blk"]
            POOL_MAN.append(q)
    print(f"\n  POOLED (6f+70+6e, engaged, 0.5-5.0 m/s):  n={len(POOL)}  "
          f"blk={len(blocks_of(POOL))}      POOLED manual: n={len(POOL_MAN)} "
          f"blk={len(blocks_of(POOL_MAN))}")
    OUT["pooled_census"] = dict(engaged=census(POOL, "POOLED engaged"),
                                manual=census(POOL_MAN, "POOLED manual"))

    # ---------------------------------------------------------------------------------------
    hdr("§0  NULLS -- computed BEFORE any effect is looked at")
    sub("0a  block-bootstrap legitimacy: lag-2 autocorrelation of f_free (must be small)")
    OUT["null_autocorr"] = {r: V86.autocorr_check(ENG[r], "f_free", r) for r in SCORED}
    OUT["null_autocorr"]["POOLED"] = V86.autocorr_check(POOL, "f_free", "POOLED")

    sub("0b  split-half null on f_free -- the frequency instrument's own floor")
    OUT["null_split_half"] = {}
    for name, rs in list((r, ENG[r]) for r in SCORED) + [("POOLED", POOL)]:
        s = split_half_null(rs)
        OUT["null_split_half"][name] = s
        print(f"    {name:10s} " + (f"nblk={s['nblk']:3d} n={s['n']:3d}  Δf 95% "
              f"[{s['d_p2p5']:+.3f},{s['d_p97p5']:+.3f}] Hz  ratio "
              f"[{s['r_p2p5']:.3f},{s['r_p97p5']:.3f}]" if s["status"] == "OK" else str(s)))

    sub("0c  SIMULATED detection floor -- free-argmax prominence on a FEATURELESS spectrum")
    OUT["null_sim_prom"] = sim_prom_floor()
    for k, v in OUT["null_sim_prom"].items():
        print(f"    {k:6s} n={v['n']}  p50={v['p50']:.2f} p90={v['p90']:.2f} "
              f"p95={v['p95']:.2f} p99={v['p99']:.2f}")

    sub("0d  EMPIRICAL detection floor -- DISENGAGED windows (pooled, 0.5-5.0 m/s)")
    pm = np.array([r["p_free"] for r in POOL_MAN if np.isfinite(r["p_free"])], float)
    fm = np.array([r["f_free"] for r in POOL_MAN if np.isfinite(r["f_free"])], float)
    OUT["null_detection_pooled_manual"] = dict(
        n=len(pm), **{f"p{k}": float(np.percentile(pm, k)) for k in (50, 75, 90, 95)},
        f_med=float(np.median(fm)),
        f_iqr=[float(np.percentile(fm, 25)), float(np.percentile(fm, 75))])
    print(f"    pooled manual n={len(pm)}  p_free p50="
          f"{np.percentile(pm, 50):.2f} p90={np.percentile(pm, 90):.2f} "
          f"p95={np.percentile(pm, 95):.2f}   f_free med={np.median(fm):.2f} "
          f"IQR[{np.percentile(fm, 25):.2f},{np.percentile(fm, 75):.2f}]")
    PFLOOR = float(np.percentile(pm, 90))
    OUT["p_free_floor"] = PFLOOR
    print(f"    ⇒ DETECTION FLOOR fixed at p_free >= {PFLOOR:.3f} (p90 of pooled disengaged). "
          f"Sim white p90={OUT['null_sim_prom']['white']['p90']:.2f}.")

    sub("0e  does the line exist?  detection rate + f_c, engaged vs disengaged")
    OUT["line_presence"] = {}
    for name, e, m in ([(r, ENG[r], MAN[r]) for r in SCORED]
                       + [("POOLED", POOL, POOL_MAN)]
                       + [(r, ENG_ALLV[r], MAN[r]) for r in THIN]):
        pe = np.array([x["p_free"] for x in e if np.isfinite(x["p_free"])], float)
        pmm = np.array([x["p_free"] for x in m if np.isfinite(x["p_free"])], float)
        b = boot_blocks([x for x in e if np.isfinite(x["f_free"])],
                        lambda z: float(np.median([q["f_free"] for q in z])), nboot=2000)
        q = boot_blocks([x for x in e if np.isfinite(x["f_free"])],
                        lambda z: float(np.median(
                            [C31.q_of(qq["f"], qq["P"], qq["f_free"], FLO, FHI)
                             for qq in z])), nboot=1000)
        OUT["line_presence"][name] = dict(
            n_eng=len(pe), n_man=len(pmm),
            det_eng=float(np.mean(pe >= PFLOOR)) if len(pe) else None,
            det_man=float(np.mean(pmm >= PFLOOR)) if len(pmm) else None,
            f_med=b["pt"], f_lo=b["lo"], f_hi=b["hi"], nblk=b["nblk"],
            Q_med=q["pt"], Q_lo=q["lo"], Q_hi=q["hi"])
        print(f"    {name:10s} det(eng)="
              f"{np.mean(pe >= PFLOOR) if len(pe) else float('nan'):.3f} det(man)="
              f"{np.mean(pmm >= PFLOOR) if len(pmm) else float('nan'):.3f}  f_c={b['pt']:.3f}"
              f"[{b['lo']:.3f},{b['hi']:.3f}] Hz  Q={q['pt']:.2f}[{q['lo']:.2f},{q['hi']:.2f}]"
              f"  nblk={b['nblk']}")

    # ---------------------------------------------------------------------------------------
    hdr("TEST A  --  df/d(LOAD) AT FIXED SPEED")
    print("  f_free regressed on each load proxy, both residualised inside the SPEED BIN.")
    print("  CI = block bootstrap over blk.  NULL = block-label permutation of the load column.")
    PROXIES = [("ld_ang", "|steer angle| deg"), ("ld_tqdc", "|DC column tq| ct"),
               ("ld_tqabs", "median|column tq| ct"), ("ld_e4", "|commanded tq| ct"),
               ("ld_co", "|carOutput tq|"), ("ld_rate", "|steer rate| deg/s"),
               ("ld_cstq", "|carState steerTq|")]
    OUT["testA"] = {}

    def run_A(rs, tag, pfloor=None):
        if pfloor is not None:
            rs = [r for r in rs if np.isfinite(r["p_free"]) and r["p_free"] >= pfloor]
        rs = [r for r in rs if np.isfinite(r["f_free"])]
        res = dict(n=len(rs), nblk=len(blocks_of(rs)), proxies={})
        sub(f"{tag}   n={len(rs)}  blk={len(blocks_of(rs))}")
        if len(rs) < 20 or len(blocks_of(rs)) < 6:
            res["status"] = "UNDERPOWERED"
            print("      UNDERPOWERED (need n>=20 and blk>=6)")
            return res
        res["status"] = "OK"
        for key, lab in PROXIES:
            vals = np.array([r[key] for r in rs if np.isfinite(r[key])], float)
            if len(vals) < 20 or np.ptp(vals) <= 0:
                res["proxies"][key] = dict(status="UNDERPOWERED", n=int(len(vals)))
                print(f"      {lab:24s}  UNDERPOWERED n={len(vals)}")
                continue
            b = boot_blocks(rs, lambda z, k=key: resid_slope(z, k), nboot=2000)
            nl = perm_null(rs, key, lambda z, k=key: resid_slope(z, k))
            rho = boot_blocks(rs, lambda z, k=key: resid_spearman(z, k), nboot=2000)
            span = float(np.percentile(vals, 90) - np.percentile(vals, 10))
            mde = 1.96 * nl["sd"] if nl.get("status") == "OK" else np.nan
            e = dict(label=lab, status="OK", slope=b["pt"], lo=b["lo"], hi=b["hi"], sd=b["sd"],
                     null_sd=nl.get("sd"), null_lo=nl.get("p2p5"), null_hi=nl.get("p97p5"),
                     rho=rho["pt"], rho_lo=rho["lo"], rho_hi=rho["hi"],
                     p10=float(np.percentile(vals, 10)), p90=float(np.percentile(vals, 90)),
                     span_p10_p90=span,
                     df_over_span=float(b["pt"] * span) if np.isfinite(b["pt"]) else None,
                     df_span_lo=float(b["lo"] * span) if np.isfinite(b["lo"]) else None,
                     df_span_hi=float(b["hi"] * span) if np.isfinite(b["hi"]) else None,
                     mde_df_over_span=float(mde * span) if np.isfinite(mde) else None,
                     sig=bool(np.isfinite(b["lo"]) and (b["lo"] > 0 or b["hi"] < 0)))
            res["proxies"][key] = e
            print(f"      {lab:24s} Δf over p10-p90 {e['df_over_span']:+.3f}"
                  f"[{e['df_span_lo']:+.3f},{e['df_span_hi']:+.3f}] Hz "
                  f"(perm-MDE ±{e['mde_df_over_span']:.3f})  rho {rho['pt']:+.3f}"
                  f"[{rho['lo']:+.3f},{rho['hi']:+.3f}]  {'SIG' if e['sig'] else '-'}")
        return res

    OUT["testA"]["POOLED"] = run_A(POOL, "POOLED 6f+70+6e, engaged, 0.5-5.0 m/s")
    OUT["testA"]["POOLED_detected"] = run_A(POOL, "POOLED, detection floor applied", PFLOOR)
    OUT["testA"]["POOLED_orderclean"] = run_A(
        [r for r in POOL
         if not any(FLO <= k * r["v"] / V86.CIRC <= FHI for k in (1, 2, 3, 4))],
        "POOLED, order-clean (robustness)")
    for route in SCORED:
        OUT["testA"][route] = run_A(ENG[route], route)
    OUT["testA"]["NEGCTRL_manual"] = run_A(POOL_MAN, "NEGATIVE CONTROL: pooled DISENGAGED")

    sub("A-extra  STATIONARY vs ROLLING, engaged")
    OUT["testA_stationary"] = {}
    for route in SCORED:
        rs = ENG[route]
        st = [r for r in rs if r["f_still"] > 0.5 or r["v"] < 0.5]
        OUT["testA_stationary"][route] = dict(
            n_still=len(st), n_roll=len(rs) - len(st),
            engaged_standstill_s=None,
            status="UNDERPOWERED" if len(st) < 8 else "OK")
        print(f"      {route:10s} engaged-stationary n={len(st)} (rolling {len(rs) - len(st)}) "
              f"-> {'UNDERPOWERED' if len(st) < 8 else 'OK'}")

    sub("A-power  minimum detectable LOAD coupling, via shift_line on the pooled arm")
    f0_pool = OUT["line_presence"]["POOLED"]["f_med"]
    OUT["testA_power"] = power_curve(POOL, "ld_ang", f0_pool, [0.0, 0.4, 0.8, 1.5, 2.5])

    # ---------------------------------------------------------------------------------------
    hdr("TEST B  --  FRICTION CONDITIONING (route 6e / V85 -- the rungs exist on NO other build)")
    OUT["testB"] = {}
    for arm, rs_all in (("lowspeed_0p5_5", ENG[FRICTION_ROUTE]),
                        ("allspeed_EXPLORATORY", ENG_ALLV[FRICTION_ROUTE])):
        rs = [r for r in rs_all if np.isfinite(r["f_free"])]
        sub(f"{arm}:  n={len(rs)}  blk={len(blocks_of(rs))}")
        duty = {k: float(np.mean([r[k] for r in rs])) for k in FRIC}
        A = dict(n=len(rs), nblk=len(blocks_of(rs)), route_duty=duty, rungs={})
        print("      duties: " + "  ".join(f"{k}={v:.4f}" for k, v in duty.items()))
        if len(rs) < 20 or len(blocks_of(rs)) < 6:
            A["status"] = "UNDERPOWERED"
            print("      UNDERPOWERED")
            OUT["testB"][arm] = A
            continue
        A["status"] = "OK"
        for k in FRIC:
            vals = np.array([r[k] for r in rs], float)
            if np.nanstd(vals) < 0.02:
                A["rungs"][k] = dict(status="UNDERPOWERED (no variance)",
                                     sd=float(np.nanstd(vals)))
                print(f"      {k:12s} UNDERPOWERED sd={np.nanstd(vals):.4g}")
                continue
            b = boot_blocks(rs, lambda z, kk=k: resid_slope(z, kk), nboot=2000)
            nl = perm_null(rs, k, lambda z, kk=k: resid_slope(z, kk))
            rs2 = within_bin_rank(rs, k)
            amp_r = boot_blocks(rs2, lambda z, kk=k: (
                float(np.median([q["amp"] for q in z if q[kk + "_rk"] >= 2 / 3]))
                / float(np.median([q["amp"] for q in z if q[kk + "_rk"] <= 1 / 3]))), nboot=2000)
            df = boot_blocks(rs2, lambda z, kk=k: d_terciles(z, kk), nboot=2000)
            hi = [r for r in rs2 if r[k + "_rk"] >= 2 / 3]
            lo = [r for r in rs2 if r[k + "_rk"] <= 1 / 3]
            A["rungs"][k] = dict(
                status="OK", n=len(vals), duty_med=float(np.median(vals)),
                sd=float(np.nanstd(vals)),
                f_slope=b["pt"], f_lo=b["lo"], f_hi=b["hi"],
                mde_f_slope=(1.96 * nl["sd"]) if nl.get("status") == "OK" else None,
                amp_ratio=amp_r["pt"], amp_lo=amp_r["lo"], amp_hi=amp_r["hi"],
                df_T3_T1=df["pt"], df_lo=df["lo"], df_hi=df["hi"],
                n_hi=len(hi), n_lo=len(lo),
                fc_hi=med_of(hi, "f_free"), fc_lo=med_of(lo, "f_free"),
                amp_sig=bool(np.isfinite(amp_r["lo"])
                             and (amp_r["lo"] > 1.0 or amp_r["hi"] < 1.0)),
                f_sig=bool(np.isfinite(df["lo"]) and (df["lo"] > 0 or df["hi"] < 0)))
            e = A["rungs"][k]
            print(f"      {k:12s} duty={e['duty_med']:.3f} | LINE AMP T3/T1 "
                  f"{amp_r['pt']:.3f}[{amp_r['lo']:.3f},{amp_r['hi']:.3f}] "
                  f"{'SIG' if e['amp_sig'] else '-'} | Δf_c T3-T1 {df['pt']:+.3f}"
                  f"[{df['lo']:+.3f},{df['hi']:+.3f}] Hz {'SIG' if e['f_sig'] else '-'}")
        OUT["testB"][arm] = A

    # ---------------------------------------------------------------------------------------
    hdr("TEST C  --  AMPLITUDE-DEPENDENT FREQUENCY")
    print("  terciles on the WITHIN-SPEED-BIN amplitude rank -> speed-balanced by construction.")
    print("  amplitude = p99 Hilbert envelope, FIXED 5.5-10.5 Hz band (argmax-independent).")
    OUT["testC"] = {}

    sub("C1  PRIMARY: pooled 6f+70+6e, engaged, 0.5-5.0 m/s, all windows")
    OUT["testC"]["POOLED"] = tercile_report(POOL, "POOLED", "amp")

    sub("C2  same, DETECTION FLOOR applied (robustness)")
    OUT["testC"]["POOLED_detected"] = tercile_report(POOL, "POOLED det", "amp", PFLOOR)

    sub("C3  NEGATIVE CONTROL -- pooled DISENGAGED, identical binning.  A trend here = artefact")
    OUT["testC"]["NEGCTRL_manual"] = tercile_report(POOL_MAN, "POOLED MANUAL", "amp")

    sub("C4  per route")
    for route in SCORED:
        OUT["testC"][route] = tercile_report(ENG[route], route, "amp")

    sub("C5  order-clean (robustness) and the TIGHT 6-9 Hz amplitude definition")
    OUT["testC"]["POOLED_orderclean"] = tercile_report(
        [r for r in POOL if not any(FLO <= k * r["v"] / V86.CIRC <= FHI for k in (1, 2, 3, 4))],
        "POOLED order-clean", "amp")
    OUT["testC"]["POOLED_amp69"] = tercile_report(POOL, "POOLED amp69", "amp69")

    sub("C6  THIN ROUTES -- census only, NOT SCORED")
    for route in THIN:
        low = [r for r in ENG[route] if np.isfinite(r["f_free"])]
        OUT["testC"][route] = dict(status="NOT SCORED (too thin at low speed)",
                                   n_lowspeed=len(low), nblk=len(blocks_of(low)),
                                   n_allspeed=len(ENG_ALLV[route]))
        print(f"    {route:10s} 0.5-5.0 m/s engaged windows n={len(low)} "
              f"(blk {len(blocks_of(low))})  all-v n={len(ENG_ALLV[route])}  -> NOT SCORED")

    sub("C-power  minimum detectable AMPLITUDE coupling, via shift_line on the pooled arm")
    OUT["testC_power"] = power_curve(POOL, "amp", f0_pool, [0.0, 0.3, 0.6, 1.0, 1.6, 2.5])

    # ---------------------------------------------------------------------------------------
    hdr("WRITE")
    p = ROOT / "_cache_r6f" / "ratchet_discriminators.json"
    p.write_text(json.dumps(OUT, indent=1, default=lambda o: None), encoding="utf-8")
    print(f"  wrote {p}")


if __name__ == "__main__":
    main()
