#!/usr/bin/env python3
"""Shared instruments for the GRIND #2 (30-49 Hz) cross-build regression test.

The question: V62/V65 doubled the torsion-bar torque-RATE (Kd) lane in FUN_0003aa2c
(`sar 0xa` -> `sar 0x9`). Did that DESTABILISE a higher-frequency mode? Three doses exist:

    Kd = 0    V61  route 31
    Kd = 1    V59  route 2c  and  V64 route 35 (detector never armed => a V59 replicate)
    Kd = 2    V62  route 37  and  V65 routes 3a / 3b (control path byte-identical to V62)

Method rules, each of which has already retracted a claim in this kit:

  EPISODES  A window is not a sample. Every CI here resamples EPISODES -- contiguous runs of the
            engagement mask -- with replacement. A window bootstrap shrinks the interval by
            ~sqrt(windows/episode) and manufactures significance.
  NULL      Every ratio is quoted against a SPLIT-HALF NULL computed inside a single build with the
            identical estimator. A ratio smaller than that build's own null spread is not a finding.
  ENVELOPE  p99 of the analytic band envelope, never mean Welch power: the phenomenon is bursty.
  PROMINENCE  peak / local median floor, so a driver cranking the wheel (broadband) cannot pass.
  MASK      Cut windows over contiguous runs of the ENGAGEMENT mask only, then bin windows by
            their OWN mean covariates. Masking on speed before cutting destroys 2.56 s contiguity
            and manufactures nulls (creep-script convention).
  ENGAGEMENT  carControl.latActive. NEVER cruiseState.enabled.
  EFFORT    sustained |lowpass(tq, 3 Hz)|, never raw |tq| -- the oscillation trips the raw test.

  ALIASING  fs = 99.4-101.5 Hz => Nyquist 49.7-50.8 Hz. A "40 Hz" line is indistinguishable from
            60.5 / 140.5 / ... Hz. The band edge 49 Hz sits ~1 Hz under Nyquist. This is COMMON
            MODE across builds, so it cannot affect the regression test -- only the identification.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _r31_common import (band_envelope, fs_of, load, periodogram,  # noqa: E402
                         runs_of, sustained)

NFFT = 256              # 2.56 s, 0.392 Hz bins -- the kit's standard
HOP = 128               # 50% overlap. Legitimate because CIs resample EPISODES, not windows.

# ---------------------------------------------------------------- builds ------------------------
BUILDS = {
    "V61/r31":  dict(cache=ROOT / "_scratch/cache/r31", pfx="r31s", segs=[0, 1, 2, 3], kd=0.0),
    "V59/r2c":  dict(cache=ROOT / "_scratch/cache/r2c", pfx="r2cs", segs=[0, 1, 3, 4, 8, 9, 10, 11, 12],
                     kd=1.0),
    "V64/r35":  dict(cache=ROOT / "_scratch/cache/r35", pfx="r35s", segs=[0, 1, 2], kd=1.0),
    # ★ V58 route 2b is the ONLY Kd=1.00 build with real highway exposure: 227 s engaged above
    # 20 m/s, in segments 7-10. 🛑 `_r31_common.SEGS_2B` is [0,1,2,11,12,13] -- it EXCLUDES exactly
    # those segments, which is why this baseline sat unused while three sessions recorded "no Kd=1
    # highway sample exists." All 14 segments are listed here. The cache predates the probe-era
    # extractor (no cs_gear / clk_* / probe fields); `wrecs` already guards cs_gear.
    "V58/r2b":  dict(cache=ROOT / "_scratch/cache/r2b", pfx="r2bs", segs=list(range(0, 14)), kd=1.0),
    "V62/r37":  dict(cache=ROOT / "_scratch/cache/r37", pfx="r37s", segs=list(range(0, 15)), kd=2.0),
    "V65/r3a":  dict(cache=ROOT / "_scratch/cache/r3a", pfx="r3as", segs=list(range(0, 7)), kd=2.0),
    "V65/r3b":  dict(cache=ROOT / "_scratch/cache/r3b", pfx="r3bs", segs=list(range(0, 14)), kd=2.0),
    # V67 is the first CONDITIONAL dose: Kd=2 only while the firmware's own LKAS gate gp-0x6806 is
    # true, stock LERP otherwise. `kd=2.5` is a LABEL, not a dose -- read it as "2 when gated".
    # 🛑 On route 47 the gate is g6806 == cc_lat in 150,302/150,327 frames, so the two arms of the
    # within-route A/B are ALSO the two arms of LKAS engagement. See DOSE_LABEL.
    "V67/r47":  dict(cache=ROOT / "_scratch/cache/r47", pfx="r47s", segs=list(range(0, 26)), kd=2.5),
}
ORDER = ["V61/r31", "V59/r2c", "V64/r35", "V62/r37", "V65/r3a", "V65/r3b", "V67/r47"]

# Kd dose pools -- routes merged only inside a dose, never across.
DOSE = {0.0: ["V61/r31"], 1.0: ["V59/r2c", "V64/r35"], 2.0: ["V62/r37", "V65/r3a", "V65/r3b"],
        2.5: ["V67/r47"]}
DOSE_LABEL = {0.0: "kd=0", 1.0: "kd=1 (stock)", 2.0: "kd=2", 2.5: "kd=2*gated"}

# ---------------------------------------------------------------- bands -------------------------
# 🛑 30-40 Hz was V62's own NEGATIVE CONTROL for the 18-22 Hz claim. It is the SUBJECT here, so it
# cannot also be the control. The pre-declared negative control is 24-28 Hz (between the modes);
# 1-4 Hz is the exposure-matching validity check (driver input, must NOT differ once matched).
BANDS = {
    "1-4":   (1.0, 4.0),      # driver input  -> matching validity check
    "6-9":   (6.0, 9.0),      # the ratchet
    "10-16": (10.0, 16.0),
    "18-22": (18.0, 22.0),    # GRIND #1
    "18-26": (18.0, 26.0),    # the kit's strict grinding band -- the PRESENCE test lives here
    "12-30": (12.0, 30.0),    # FREE locate band: a strict band pins f0 to its own edge (V61)
    "24-28": (24.0, 28.0),    # pre-declared NEGATIVE CONTROL
    "30-40": (30.0, 40.0),
    "40-49": (40.0, 49.0),
    "30-49": (30.0, 49.0),    # GRIND #2 candidate
}
HF = "30-49"
NEG = "24-28"

# ---------------------------------------------------------------- matching cells -----------------
V_BINS = [(0.0, 0.5), (0.5, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 14.0), (14.0, 30.0)]
E_BINS = [(0.0, 200.0), (200.0, 800.0), (800.0, 2000.0), (2000.0, 1e9)]
R_BINS = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 1e9)]


def binof(x, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= x < hi:
            return i
    return len(bins) - 1 if x >= bins[-1][0] else 0


_MASKCACHE = {}


def _nearmask(f, halfwin, exclude):
    """(nbin, nbin) boolean neighbourhood matrix, cached per (f[0], f[-1], n, halfwin, exclude)."""
    key = (len(f), float(f[1]), halfwin, exclude)
    M = _MASKCACHE.get(key)
    if M is None:
        D = np.abs(f[:, None] - f[None, :])
        M = (D <= halfwin) & (D > exclude) & (f[None, :] > 0.3)
        M[M.sum(1) < 5] = False
        _MASKCACHE[key] = M
    return M


def prom_spectrum(f, P, halfwin=6.0, exclude=1.5):
    """P divided by its own local median floor, per bin. Identical result to the loop in
    _r37_ratchet_lib.prom_spectrum; vectorised so a 6-build sweep finishes."""
    M = _nearmask(np.asarray(f, float), halfwin, exclude)
    A = np.where(M, P[None, :], np.nan)
    with np.errstate(all="ignore"):
        fl = np.nanmedian(A, axis=1)
    R = np.where((fl > 0), P / np.where(fl > 0, fl, 1.0), np.nan)
    R[~np.isfinite(fl)] = np.nan
    R[0] = R[-1] = np.nan
    return R


def locate(f, P, lo, hi, halfwin=6.0, exclude=1.5, R=None):
    """(f0, prominence) of the most PROMINENT line in [lo,hi], sub-bin refined in log power.

    argmax of the PROMINENCE spectrum, not of P: `tq` carries the driver's own 1-3 Hz input at
    10-100x any mode, so a raw-power argmax lands on the driver and a band floor pins it to the
    band edge.
    """
    if R is None:
        R = prom_spectrum(f, P, halfwin, exclude)
    m = (f >= lo) & (f <= hi) & np.isfinite(R)
    if not m.any():
        return np.nan, np.nan
    j = int(np.argmax(np.where(m, R, -np.inf)))
    if j <= 0 or j >= len(P) - 1:
        return float(f[j]), float(R[j])
    y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
    den = y0 - 2 * y1 + y2
    dl = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return float(f[j] + np.clip(dl, -0.5, 0.5) * (f[1] - f[0])), float(R[j])


def q_of(f, P, f0):
    """-3 dB Q of the peak nearest f0. Hann main lobe caps measurable Q at f0/(1.44*fs/nfft)."""
    if not np.isfinite(f0):
        return np.nan
    j = int(np.argmin(np.abs(f - f0)))
    half = P[j] / 2.0
    a = j
    while a > 1 and P[a] > half and P[a - 1] < P[a]:
        a -= 1
    b = j
    while b < len(P) - 2 and P[b] > half and P[b + 1] < P[b]:
        b += 1
    bw = max(f[b] - f[a], f[1] - f[0])
    return float(f[j] / bw)


# ---------------------------------------------------------------- window records ----------------
def wrecs(build, nfft=NFFT, hop=HOP, chan="tq", keep_P=False, maskkey="cc_lat"):
    """Every disjoint-ish window of one build, tagged with band envelopes, band prominences and
    covariates. Windows are cut inside contiguous runs of the ENGAGEMENT mask (both polarities),
    never across an engagement transition.

    `maskkey` selects the partition variable and therefore what `eng` MEANS in the records:
      "cc_lat" -- openpilot's carControl.latActive. The kit's standing convention; the only one
                  available on every route.
      "g6806"  -- V67 ONLY: the firmware's OWN gate bit, which is also what selects the Kd=2 arm.
                  Use this for the within-route dose A/B so the split is on the thing the firmware
                  actually branched on, not on openpilot's view of it.
    """
    B = BUILDS[build]
    out = []
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        f = np.fft.rfftfreq(nfft, 1 / fs)
        taper = np.hanning(nfft) + 1e-3
        cw = slice(int(0.2 * nfft), int(0.8 * nfft))
        le = d[maskkey] > 0.5
        for eng, mask in ((1, le), (0, ~le)):
            for a, b in runs_of(mask, d["t"], nfft):
                x = np.asarray(d[chan][a:b], float)
                xa = np.asarray(d["ang"][a:b], float)
                nwin = 0
                for i in range(0, len(x) - nfft + 1, hop):
                    P = periodogram(x[i:i + nfft], fs, nfft, True)
                    if P is None:
                        continue
                    sl = slice(a + i, a + i + nfft)
                    xw = x[i:i + nfft]
                    R = prom_spectrum(f, P)
                    r = dict(build=build, kd=B["kd"], seg=int(s), eng=eng, fs=fs,
                             ep=(build, int(s), int(a), int(b)), t0=float(d["t"][a + i]))
                    for k, bd in BANDS.items():
                        r["e_" + k] = win_env(xw, fs, *bd, taper, cw)
                        r["f_" + k], r["p_" + k] = locate(f, P, *bd, R=R)
                    # leakage-immune second method + a CONTROL CHANNEL from the other CAN message
                    r["zig"], r["zigamp"] = zigzag(xw, 300.0)
                    r["zig800"] = zigzag(xw, 800.0)[0]
                    r["ang_hf"] = win_env(xa[i:i + nfft], fs, 30.0, 49.0, taper, cw)
                    r["ang_lf"] = win_env(xa[i:i + nfft], fs, 1.0, 10.0, taper, cw)
                    r["Qhf"] = q_of(f, P, r["f_" + HF])
                    r["v"] = float(np.mean(np.abs(d["cs_v"][sl])))
                    r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
                    r["eff"] = float(np.mean(np.abs(sustained(d["tq"][sl], fs))))
                    r["rate"] = float(np.mean(np.abs(d["rate_c"][sl])))
                    r["ratep95"] = float(np.percentile(np.abs(d["rate_c"][sl]), 95))
                    r["e4"] = float(np.mean(np.abs(d["e4tq"][sl])))
                    r["gear"] = (float(np.median(d["cs_gear"][sl])) if "cs_gear" in d else np.nan)
                    # V67 carries the firmware's own arm selector; keep BOTH views so a window can
                    # be audited for gate/latActive disagreement instead of one silently standing in
                    # for the other.
                    r["gate"] = (float(np.mean(d["g6806"][sl])) if "g6806" in d else np.nan)
                    r["lat"] = float(np.mean(d["cc_lat"][sl] > 0.5))
                    r["cell"] = (eng, binof(r["v"], V_BINS), binof(r["eff"], E_BINS),
                                 binof(r["rate"], R_BINS))
                    r["blk"] = r["ep"] + (nwin // 8,)      # ~10.2 s blocks inside the run
                    nwin += 1
                    if keep_P:
                        r["f"], r["P"] = f, P
                    out.append(r)
    return out


def win_env(xw, fs, lo, hi, taper, cw):
    """p99 of the analytic band envelope of ONE window, leakage-controlled.

    🛑 _r31_common.band_envelope subtracts only the mean and applies no taper. On a high-effort
    window the driver's own torque RAMP has a 1/f spectrum plus a rectangular-window discontinuity,
    and both leak into 30-49 Hz in proportion to the ramp -- i.e. in proportion to driver effort,
    which is exactly the covariate that separates the routes here. Measured on one V65 burst: the
    STEERING-ANGLE channel, which is visibly smooth, reported a 35.8 deg "30-49 Hz envelope" that
    was pure leakage. So: linear-detrend, Hann-taper, then read the CENTRAL 60% with the taper
    divided back out.
    """
    r = np.arange(len(xw), dtype=float)
    c = np.polyfit(r, xw, 1)
    y = (xw - (c[0] * r + c[1])) * taper
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    a = np.abs(np.fft.irfft(H, n=len(y)))
    return float(np.percentile((a / taper)[cw], 99))


def zigzag(x, thr):
    """(count, median amplitude) of large sign-alternating turning points -- an FFT-free,
    leakage-IMMUNE detector for content near fs/2. A 45 Hz oscillation reverses almost every
    sample; an 18 Hz one of the same amplitude reverses every ~2.8 samples with small diffs at
    the reversal, so this separates the two without any spectral assumption."""
    d1 = np.diff(np.asarray(x, float))
    if len(d1) < 3:
        return 0, 0.0
    s = np.sign(d1)
    amp = np.minimum(np.abs(d1[:-1]), np.abs(d1[1:]))
    m = (s[:-1] * s[1:] < 0) & (amp > thr)
    return int(m.sum()), (float(np.median(amp[m])) if m.any() else 0.0)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


EPKEY = "ep"        # "ep" = whole engagement run (conservative) | "blk" = ~10 s block bootstrap


def episodes(rs):
    """Group window records by resampling unit. `EPKEY` selects the definition:

      "ep"  -- one contiguous run of the engagement mask. The most conservative unit and the
               kit's standing convention, but engagement runs here are 30-60 s, so a build can
               have as few as 5 of them and the split-half null becomes degenerate.
      "blk" -- a ~10.2 s block (8 windows at hop 128) nested inside one engagement run. Still far
               longer than the 1-3 s burst autocorrelation, so it does not manufacture
               significance, and it gives the null enough units to be measurable.

    Both are reported. Whichever is used, the SPLIT-HALF NULL uses the same one, so the ratio is
    always quoted against a floor computed with the identical estimator.
    """
    ep = {}
    for r in rs:
        ep.setdefault(r[EPKEY], []).append(r)
    return list(ep.values())


# ---------------------------------------------------------------- estimators --------------------
def cell_stat(rs, key, agg=np.median):
    v = col(rs, key)
    v = v[np.isfinite(v)]
    return float(agg(v)) if len(v) else np.nan


def boot_cellwise(recsA, recsB, key, rng, nboot=2000, min_ep=3, min_win=8, agg=np.median):
    """STRATIFIED log-ratio A/B over cells occupied by BOTH sides, episode-resampled.

    Weight w_c = 1/(1/nepA_c + 1/nepB_c): a cell contributes in proportion to the smaller episode
    count, so a cell that one build barely visited cannot dominate.
    Returns (ratio, lo, hi, ncells, nepA, nepB, per-cell table).
    """
    epA, epB = episodes(recsA), episodes(recsB)

    def strat(eA, eB, want_table=False):
        A, B = {}, {}
        for e in eA:
            for r in e:
                A.setdefault(r["cell"], []).append(r)
        for e in eB:
            for r in e:
                B.setdefault(r["cell"], []).append(r)
        num = den = 0.0
        tab = []
        for c in sorted(set(A) & set(B)):
            ra, rb = A[c], B[c]
            na, nb = len(ra), len(rb)
            nea = len({r[EPKEY] for r in ra})
            neb = len({r[EPKEY] for r in rb})
            if nea < min_ep or neb < min_ep or na < min_win or nb < min_win:
                continue
            sa, sb = cell_stat(ra, key, agg), cell_stat(rb, key, agg)
            if not (np.isfinite(sa) and np.isfinite(sb)) or sa <= 0 or sb <= 0:
                continue
            w = 1.0 / (1.0 / nea + 1.0 / neb)
            num += w * np.log(sa / sb)
            den += w
            if want_table:
                tab.append((c, na, nb, nea, neb, sa, sb, sa / sb, w))
        if den == 0:
            return np.nan, tab
        return num / den, tab

    point, tab = strat(epA, epB, True)
    if nboot <= 0:
        return float(np.exp(point)), np.nan, np.nan, len(tab), len(epA), len(epB), tab, None
    draws = np.full(nboot, np.nan)
    for k in range(nboot):
        ia = rng.integers(0, len(epA), len(epA))
        ib = rng.integers(0, len(epB), len(epB))
        draws[k] = strat([epA[i] for i in ia], [epB[i] for i in ib])[0]
    if not np.isfinite(draws).any():
        return float(np.exp(point)), np.nan, np.nan, len(tab), len(epA), len(epB), tab, draws
    lo, hi = (np.nanpercentile(draws, 2.5), np.nanpercentile(draws, 97.5))
    return (float(np.exp(point)), float(np.exp(lo)), float(np.exp(hi)),
            len(tab), len(epA), len(epB), tab, draws)


def split_half_null(recs, key, rng, nrep=400, **kw):
    """The build's own noise floor: randomly halve ITS OWN episodes and run the same estimator.

    Any effect inside this interval is not distinguishable from route/exposure noise.
    """
    eps = episodes(recs)
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(eps))
        h = len(eps) // 2
        a = [eps[i] for i in idx[:h]]
        b = [eps[i] for i in idx[h:]]
        ra = [r for e in a for r in e]
        rb = [r for e in b for r in e]
        v = boot_cellwise(ra, rb, key, rng, nboot=0, **kw)[0]
        if np.isfinite(v):
            out.append(v)
    out = np.array(out, float)
    if not len(out):
        return np.nan, np.nan, np.nan
    return (float(np.exp(np.nanmedian(np.log(out)))),
            float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5)))


def boot_median_ci(rs, key, rng, nboot=2000, agg=np.median):
    """(point, lo, hi) for agg(key) over windows, resampling EPISODES."""
    eps = episodes(rs)
    if not eps:
        return np.nan, np.nan, np.nan
    per = [col(e, key) for e in eps]
    allv = np.concatenate(per) if per else np.array([])
    allv = allv[np.isfinite(allv)]
    if not len(allv):
        return np.nan, np.nan, np.nan
    draws = np.full(nboot, np.nan)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        v = np.concatenate([per[j] for j in i])
        v = v[np.isfinite(v)]
        if len(v):
            draws[b] = agg(v)
    return (float(agg(allv)), float(np.nanpercentile(draws, 2.5)),
            float(np.nanpercentile(draws, 97.5)))


def perm_p(recsA, recsB, key, rng, nperm=2000, **kw):
    """Two-sided permutation p: shuffle EPISODE labels between the two builds and re-estimate.

    Note this destroys the build/route pairing, so it tests 'these two episode pools differ'
    rather than 'the firmware differs' -- read it with the split-half null beside it.
    """
    epA, epB = episodes(recsA), episodes(recsB)
    obs = boot_cellwise(recsA, recsB, key, rng, nboot=0, **kw)[0]
    if not np.isfinite(obs):
        return np.nan, np.nan
    pool = epA + epB
    nA = len(epA)
    hits = tot = 0
    for _ in range(nperm):
        idx = rng.permutation(len(pool))
        ra = [r for i in idx[:nA] for r in pool[i]]
        rb = [r for i in idx[nA:] for r in pool[i]]
        v = boot_cellwise(ra, rb, key, rng, nboot=0, **kw)[0]
        if np.isfinite(v):
            tot += 1
            if abs(np.log(v)) >= abs(np.log(obs)):
                hits += 1
    return float(obs), (float((hits + 1) / (tot + 1)) if tot else np.nan)


def hdr(s):
    print(f"\n{'=' * 110}\n{s}\n{'=' * 110}")
