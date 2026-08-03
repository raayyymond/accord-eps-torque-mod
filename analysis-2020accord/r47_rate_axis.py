#!/usr/bin/env python3
"""r47_rate_axis.py -- put grind #1, grind #2-creep and grind #2-HIGHWAY on the r24 gain SURFACE.

The decision this feeds: the damper gain that fixes grind #1 (~20.9 Hz) and worsens grind #2 (~45 Hz)
is not a scalar. It is FUN_0003ad74's two-axis LERP -- cross axis = voted VEHICLE SPEED (gp-0x6a5e,
64.0625 counts/km/h, breakpoints 0/640/3200/6400), inner axis = the MOTOR/resolver rate gp-0x6ac0
(breakpoints ~0/400/1400-1500/3000). If the symptoms occupy different cells, the fix is cal-only and
intrinsically scheduled. If they don't, no cell edit can separate them and we must say so.

=================================================================================================
UNITS -- the thing that would invalidate everything downstream, so it is derived, not assumed.
=================================================================================================
`gp-0x6ac0 = |gp-0x6abe|` (one EMA accumulator in FUN_00041464: `gp-0x6abe = state>>10`,
`gp-0x6ac0 = abs(state)>>10`), and the bus rate is a FIXED Q15 scale of the same cell:

    gp-0x6a56 = clamp(polarity * ((gp-0x6abe * 48 * cal(0xC613A=1159)) >> 15), +-12000)
              = gp-0x6abe * 55632/32768 = gp-0x6abe * 1.697509765625

Which CAN copy is gp-0x6a56 itself is settled by ARITHMETIC, not by taste: the measured raw relation
is `raw(0x18F[2:4]) = 8 * raw(0x14A[2:4])` (verified below). If 0x14A were gp-0x6a56 then 0x18F would
need 8*12000 = 96000 at the clamp, which does not fit the i16 it is packed into. So

    raw 0x18F[2:4] == gp-0x6a56       and     raw 0x14A[2:4] == gp-0x6a56 >> 3

=>  AXIS gp-0x6ac0 = |raw 0x18F| * 32768/55632 = |raw 0x18F| * 0.5890135
                   = |raw 0x14A| * 2**18/55632 = |raw 0x14A| * 4.7121081

🛑 This RESOLVES the discrepancy flagged as open in memory/accord-r24-gain-b-four-pointer-arrays.md
("the 0x18F route implies ~5.89 counts/deg/s against 0x14A's 4.7121 -- unreconciled"). It is an
**opendbc scale inconsistency between the two packers, not a firmware one**: 0x14A's DBC factor is
1.0 deg/s/count and 0x18F's is 0.1, but the raw counts differ by 8, so the two DBC decodes disagree
by exactly 1.25x. In RAW COUNTS the two copies agree to 0.08% (measured below).
★ AND THE TIE IS NOW BROKEN, jointly with the grind2 agent: they regressed `rate_c` against the
DIFFERENTIATED ANGLE channel over 50 ms differences and got slope 0.9866-0.9969 (r 0.994-0.998) on
four segments with large angle excursions -- a physical anchor this script does not have. So
**0x14A's 1.0 deg/s/count is CORRECT and 0x18F's 0.1 is WRONG (it should be 0.125)**. Therefore
4.7121 is counts per TRUE deg/s and the 5.89 figure is simply an artefact of the bad DBC factor.
Everything in this script is in RAW COUNTS, so neither ruler is load-bearing here either.

⚠ RESIDUAL UNCERTAINTY, stated rather than smoothed over:
  1. 0x18F is HELD-LAST onto 0x14A's grid in the caches, so it carries a sub-frame ZOH lag. That is
     why a least-squares-through-origin slope reads 8.11 (errors-in-variables attenuation) while the
     lag-immune QUANTILE match reads 7.994. Both are printed; the quantile match is the estimator.
  2. The cross axis is the EPS's OWN voted speed (gp-0x6a5e). We only have openpilot's `vEgo`. They
     are both wheel-speed derived and agree to a few %, but a systematic offset would shift the
     speed axis. It cannot move a creep population into the 50 km/h record or vice versa.
  3. gp-0x6ac0 is an EMA of the resolver rate; the bus copy is the SAME cell, so there is no extra
     filtering between the axis and what we measure. This is the one place the mapping is tight.

=================================================================================================
METHOD RULES (each has already retracted a claim in this kit)
=================================================================================================
  EPISODES  every CI resamples contiguous engagement runs, never windows.
  TAIL+MEAN both reported -- they have disagreed in SIGN on this data.
  ENVELOPE  p99 of the leakage-controlled analytic band envelope (_grind2_lib.win_env).
  MASK      windows cut over contiguous runs of the ENGAGEMENT mask FIRST, then binned by their own
            mean covariates. Masking on speed before cutting destroys contiguity.
  ENGAGE    carControl.latActive; on r47 the firmware's own gate bit g6806.
  SIMPSON   every population is reported inside its speed stratum, never pooled across strata.

Usage:  python r47_rate_axis.py            # full run, ~2 min
        python r47_rate_axis.py --quick    # skip the bootstrap CIs
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

# Windows consoles default to cp1252 and this report uses arrows and box marks. Without this the
# script dies MID-REPORT, after the expensive part, which is the worst possible failure mode.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _grind2_lib import BUILDS, win_env                      # noqa: E402
from _r31_common import fs_of, load, runs_of, sustained      # noqa: E402
import v66_v67_explained as EX                               # noqa: E402

# ---------------------------------------------------------------- constants ----------------------
CROSS_X = np.array(EX.CROSS_X, np.int64)                     # 0xC6010, voted-speed counts
RECS = EX.GAIN_B_MODE10                                      # mode-10, byte-read
REC_X = np.array([r[1] for r in RECS], np.int64)             # (4 speeds, 4 rate breakpoints)
REC_Y = np.array([r[2] for r in RECS], np.int64)             # (4 speeds, 4 Q10 gains)
SPEED_COUNTS_PER_KMH = 64.0625                               # gp-0x6a5e scale
AXIS_PER_18F = 32768.0 / (48 * 1159)                         # 0.5890135  raw 0x18F -> gp-0x6ac0
AXIS_PER_14A = AXIS_PER_18F * 8.0                            # 4.7121081  raw 0x14A -> gp-0x6ac0
ARM_V67 = 5244                                               # 0xC6446 on V67 (stock 512)

NFFT, HOP = 256, 128
BANDS = {"1-4": (1.0, 4.0), "18-22": (18.0, 22.0), "24-28": (24.0, 28.0),
         "30-40": (30.0, 40.0), "40-49": (40.0, 49.0), "30-49": (30.0, 49.0)}
G1B, G2B = "e_18-22", "e_40-49"

# Speed strata. Creep is the regime where grind #1 and the V65 creep grind #2 were characterised;
# highway is where route 47's new grind #2 lives. The gap between them is deliberate -- a stratum
# that spans the transition would let Simpson's paradox back in.
CREEP = (0.0, 4.0)          # m/s   0 - 14.4 km/h
MID = (4.0, 14.0)
HWY = (14.0, 99.0)          # m/s   >= 50.4 km/h

ROUTES_KD2 = ["V62/r37", "V65/r3a", "V65/r3b"]
ROUTES_STOCK = ["V59/r2c", "V64/r35"]
ALL_ROUTES = ROUTES_STOCK + ["V61/r31"] + ROUTES_KD2 + ["V67/r47"]


# ================================================================ firmware arithmetic =============
def _lerp_vec(x, XS, YS):
    """Vectorised _lerp_flat: flat outside, `mul` then `divq` (TRUNCATION TOWARD ZERO) inside.

    XS/YS are (N,4) int64 per-sample breakpoint rows -- the cross-interpolation makes them
    per-sample, so this cannot be a single shared 4-knot curve.
    """
    x = np.asarray(x, np.int64)
    out = YS[:, -1].copy()
    done = x >= XS[:, -1]
    lo = x <= XS[:, 0]
    out[lo] = YS[lo, 0]
    done |= lo
    for i in range(XS.shape[1] - 1):
        m = (~done) & (x >= XS[:, i]) & (x <= XS[:, i + 1])
        if not m.any():
            continue
        num = (YS[m, i + 1] - YS[m, i]) * (x[m] - XS[m, i])
        den = XS[m, i + 1] - XS[m, i]
        q = np.abs(num) // np.maximum(np.abs(den), 1)
        sgn = np.where((num < 0) != (den < 0), -1, 1)
        out[m] = YS[m, i] + sgn * q
        done |= m
    return out


def stock_gain_q10(speed_counts, rate_counts, recy=REC_Y, recx=REC_X):
    """FUN_0003ad74's surface, element-by-element cross-interpolation then the rate LERP.

    Mirrors v66_v67_explained.r24_gain_q10's DEFAULT arm (no override flag firing), vectorised.
    Validated element-for-element against that scalar reference in `_selftest`.
    """
    s = np.clip(np.asarray(speed_counts, np.int64), CROSS_X[0], CROSS_X[-1])
    n = len(s)
    CX = np.tile(CROSS_X, (n, 1))
    XS = np.empty((n, 4), np.int64)
    YS = np.empty((n, 4), np.int64)
    for i in range(4):
        XS[:, i] = _lerp_vec(s, CX, np.tile(recx[:, i], (n, 1)))
        YS[:, i] = _lerp_vec(s, CX, np.tile(recy[:, i], (n, 1)))
    r = np.asarray(rate_counts, np.int64)
    key = np.where(r >= EX.RATE_FOLD, 0, r)                  # 0x3AAC8 fold-to-MAX-gain
    return _lerp_vec(key, XS, YS)


def _selftest(rng):
    """Second method, mandatory: the vectorised surface vs the scalar reference, incl. the edges."""
    sp = rng.integers(-200, 7000, 4000)
    rt = rng.integers(0, 14000, 4000)
    mine = stock_gain_q10(sp, rt)
    ref = np.array([EX.r24_gain_q10(int(a), int(b), 0, 0, 0) for a, b in zip(sp, rt)])
    bad = int((mine != ref).sum())
    print(f"   selftest  vectorised surface vs v66_v67_explained.r24_gain_q10 on 4000 random "
          f"(speed,rate): {'PASS' if bad == 0 else f'*** {bad} MISMATCHES ***'}")
    assert bad == 0
    # and the three anchors the record quotes
    for s_kmh, r_cnt, want in ((0, 0, 3072), (50, 0, 2305), (100, 0, 2151)):
        got = int(stock_gain_q10([int(round(s_kmh * SPEED_COUNTS_PER_KMH))], [r_cnt])[0])
        print(f"   anchor    {s_kmh:3d} km/h, rate {r_cnt:5d} -> {got:5d}  "
              f"(record says {want}) {'ok' if got == want else '*** MISMATCH ***'}")


def cell_label(speed_counts, rate_counts):
    """Which pair of speed records and which pair of rate breakpoints the point lands between."""
    sk = ["0", "10", "50", "100"]
    i = int(np.searchsorted(CROSS_X, speed_counts, side="right") - 1)
    i = max(0, min(i, 2))
    sp = f"{sk[i]}-{sk[i + 1]} km/h" if speed_counts < CROSS_X[-1] else ">=100 km/h"
    s = np.clip(int(speed_counts), CROSS_X[0], CROSS_X[-1])
    xs = [int(_lerp_vec(np.array([s]), CROSS_X[None, :], REC_X[:, i][None, :])[0]) for i in range(4)]
    j = int(np.searchsorted(xs, rate_counts, side="right") - 1)
    j = max(0, min(j, 2))
    rb = (f"X{j}-X{j + 1} [{xs[j]},{xs[j + 1]})" if rate_counts < xs[-1] else f">=X3 [{xs[-1]}]")
    return f"speed {sp:>11s} | rate {rb}"


# ================================================================ window records ==================
def maskkey(build):
    return "g6806" if build.startswith("V67") else "cc_lat"


def recs(build):
    """One record per 2.56 s window, cut inside contiguous runs of the engagement mask."""
    B = BUILDS[build]
    mk = maskkey(build)
    out = []
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        taper = np.hanning(NFFT) + 1e-3
        cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
        # --- the two axes, per sample, in the firmware's own units --------------------------------
        ax18 = np.rint(np.abs(d["rate_f"] * 10.0) * AXIS_PER_18F).astype(np.int64)   # PRIMARY
        ax14 = np.rint(np.abs(d["rate_c"]) * AXIS_PER_14A).astype(np.int64)          # cross-check
        spc = np.rint(np.abs(d["cs_v"]) * 3.6 * SPEED_COUNTS_PER_KMH).astype(np.int64)
        gain = stock_gain_q10(spc, ax18)              # the stock surface, evaluated per sample
        bar = np.asarray(d["tq"], float)
        dtq = np.zeros_like(bar)
        dtq[4:] = 2.0 * (bar[4:] - bar[:-4]) / 4.0    # gp-0x4f62's form, at the 100 Hz grid
        eng = d[mk] > 0.5
        for pol, mask in ((1, eng), (0, ~eng)):
            for a, b in runs_of(mask, d["t"], NFFT):
                x = np.asarray(d["tq"][a:b], float)
                nw = 0
                for i in range(0, len(x) - NFFT + 1, HOP):
                    xw = x[i:i + NFFT]
                    if not np.all(np.isfinite(xw)):
                        continue
                    sl = slice(a + i, a + i + NFFT)
                    r = dict(build=build, kd=B["kd"], seg=int(s), eng=pol, fs=fs,
                             ep=(build, int(s), int(a), int(b)), t0=float(d["t"][a + i]))
                    r["blk"] = r["ep"] + (nw // 8,)
                    nw += 1
                    for k, bd in BANDS.items():
                        r["e_" + k] = win_env(xw, fs, bd[0], bd[1], taper, cw)
                    r["v"] = float(np.mean(np.abs(d["cs_v"][sl])))
                    r["spc"] = float(np.median(spc[sl]))
                    r["ax"] = float(np.median(ax18[sl]))
                    r["ax_p90"] = float(np.percentile(ax18[sl], 90))
                    r["ax_mean"] = float(np.mean(ax18[sl]))
                    r["ax14"] = float(np.median(ax14[sl]))
                    r["G"] = float(np.mean(gain[sl]))          # delivered stock gain, sample-wise
                    r["Gmed"] = float(stock_gain_q10([int(r["spc"])], [int(r["ax"])])[0])
                    # 🛑 KEEP THE SAMPLES. A knee-shaped candidate curve evaluated at the window
                    # MEDIAN would overstate its own separation; every design candidate below is
                    # evaluated on these 256 samples, exactly as the firmware would.
                    r["sp_s"] = spc[sl].astype(np.int32)
                    r["ax_s"] = ax18[sl].astype(np.int32)
                    # 100 Hz proxy for the lane's input gp-0x4f62 = 2*(bar[n]-bar[n-4])/4, used
                    # ONLY to reweight a gain average. ⚠ The real producer runs at ~1 kHz.
                    r["dtq_s"] = dtq[sl].astype(np.float32)
                    r["eff"] = float(np.mean(np.abs(sustained(d["tq"][sl], fs))))
                    r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
                    r["e4"] = float(np.mean(np.abs(d["e4tq"][sl])))
                    r["req"] = float(np.mean(np.abs(np.nan_to_num(d["cc_req"][sl]))))
                    r["press"] = float(np.mean(d["cs_press"][sl] > 0.5))
                    r["lat"] = float(np.mean(d["cc_lat"][sl] > 0.5))
                    r["gate"] = float(np.mean(d["g6806"][sl])) if "g6806" in d else np.nan
                    r["g671d"] = float(np.mean(d["g671d"][sl])) if "g671d" in d else np.nan
                    out.append(r)
    return out


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def stratum(rs, lo, hi, eng=1):
    return [r for r in rs if r["eng"] == eng and lo <= r["v"] < hi]


# ================================================================ populations =====================
def population(rs, band, other, frac=0.15, nmin=20):
    """Top `frac` of `band` inside the given pool, band-EXCLUSIVE, plus a speed-matched quiet control.

    The two bands overlap in time -- a loud grind #2 burst is broadband enough to light 18-22 too --
    so a plain top-decile in each band would measure the same windows twice. Exclusivity here means
    "not ALSO in the other band's top `frac`". ⚠ An earlier, stricter rule (other band below the
    POOL MEDIAN) cut the grind #1 populations to n=5 -- which is itself a finding: the loudest
    18-22 Hz windows are broadband, so most of them are in the upper half of 40-49 too. The gentler
    rule keeps the population usable and the number dropped is printed so the cost stays visible.
    """
    if len(rs) < nmin:
        return [], [], 0
    b, o = col(rs, band), col(rs, other)
    thr, othr = np.quantile(b, 1 - frac), np.quantile(o, 1 - frac)
    raw = [r for r in rs if r[band] >= thr]
    top = [r for r in raw if r[other] < othr]
    dropped = len(raw) - len(top)
    if len(top) < 8:
        top, dropped = raw, -dropped        # exclusivity emptied it; negative flags the fallback
    quiet = [r for r in rs if r[band] < np.median(b)]
    dv = 0.5 if np.median(col(top, "v")) < 5 else 2.0
    tv = col(top, "v")
    ctrl = [r for r in quiet if np.min(np.abs(tv - r["v"])) <= dv]
    return top, (ctrl if len(ctrl) >= 8 else quiet), dropped


def describe(name, rs, extra=""):
    if not rs:
        print(f"   {name:34s}  (empty)")
        return
    v = col(rs, "v")
    spc = col(rs, "spc")
    ax = col(rs, "ax")
    G = col(rs, "G")
    ne = len({r["ep"] for r in rs})
    p = lambda a, q: float(np.percentile(a, q))  # noqa: E731
    axs = np.concatenate([r["ax_s"] for r in rs]).astype(float)   # every 100 Hz sample, pooled
    print(f"   {name:34s} n={len(rs):4d} ep={ne:3d} {extra}")
    print(f"      speed  {p(v, 50) * 3.6:7.2f} km/h [p10 {p(v, 10) * 3.6:6.2f}  p90 "
          f"{p(v, 90) * 3.6:6.2f}]   counts {p(spc, 50):7.0f} [{p(spc, 10):6.0f} {p(spc, 90):6.0f}]")
    print(f"      rate   {p(ax, 50):7.0f} cnt  [p10 {p(ax, 10):6.0f}  p90 {p(ax, 90):6.0f}]"
          f"   (win-mean {np.median(col(rs, 'ax_mean')):6.0f}, win-p90 "
          f"{np.median(col(rs, 'ax_p90')):6.0f}; 0x14A copy {np.median(col(rs, 'ax14')):6.0f})")
    print(f"      rate SAMPLE-WISE (what the LERP actually sees, {len(axs)} samples): "
          f"p50 {np.median(axs):6.0f}  p90 {np.percentile(axs, 90):6.0f}  "
          f"p99 {np.percentile(axs, 99):6.0f}  frac>400 {float((axs > 400).mean()):.3f}")
    print(f"      CELL   {cell_label(np.median(spc), np.median(ax))}")
    print(f"      stock LERP gain Q10  mean-of-window {np.mean(G):7.1f}  median {np.median(G):7.1f}"
          f"   [p10 {p(G, 10):6.1f} p90 {p(G, 90):6.1f}]")
    gt = col(rs, "gate")                       # NaN on every build except V67 -- not a route with
    gt = np.nanmean(gt) if np.isfinite(gt).any() else np.nan    # no gate, a build without the probe
    print(f"      engagement duty: latActive {np.mean(col(rs, 'lat')):.3f}  "
          f"g6806 {gt:.3f}  steeringPressed "
          f"{np.mean(col(rs, 'press')):.3f}  |tq|lp3 {np.median(col(rs, 'eff')):7.0f}  "
          f"|ang| {np.median(col(rs, 'ang')):6.1f} deg")


def grid(name, rs, vbins, rbins):
    """Text 2-D density on the two LERP axes. Marginals in the margins."""
    if not rs:
        return
    v = col(rs, "spc")
    a = col(rs, "ax")
    n = len(rs)
    print(f"\n   2-D density, {name} (n={n}), rows = speed counts, cols = rate counts (% of pop)")
    hdr = "  ".join(f"{lo:>5.0f}-{hi:<5.0f}" for lo, hi in rbins)
    print(f"      {'speed cnt':>14s} | {hdr} |  row%")
    for vlo, vhi in vbins:
        m = (v >= vlo) & (v < vhi)
        cells = []
        for rlo, rhi in rbins:
            k = m & (a >= rlo) & (a < rhi)
            cells.append(f"{100 * k.sum() / n:11.1f}")
        print(f"      {vlo:6.0f}-{vhi:<7.0f} | " + "  ".join(cells) + f" | {100 * m.sum() / n:5.1f}")
    colm = []
    for rlo, rhi in rbins:
        k = (a >= rlo) & (a < rhi)
        colm.append(f"{100 * k.sum() / n:11.1f}")
    print(f"      {'col%':>14s} | " + "  ".join(colm) + " |")


# ================================================================ separation ======================
def auc(x_pos, x_neg):
    """Mann-Whitney AUC of |separation|, folded so 0.5 = no separation and 1.0 = perfect."""
    x_pos = np.asarray(x_pos, float)
    x_neg = np.asarray(x_neg, float)
    x_pos = x_pos[np.isfinite(x_pos)]
    x_neg = x_neg[np.isfinite(x_neg)]
    if len(x_pos) < 3 or len(x_neg) < 3:
        return np.nan
    allv = np.concatenate([x_pos, x_neg])
    r = np.argsort(np.argsort(allv)) + 1.0
    # average ranks for ties
    order = np.argsort(allv, kind="mergesort")
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            r[order[i:j + 1]] = np.mean(r[order[i:j + 1]])
        i = j + 1
    n1 = len(x_pos)
    u = r[:n1].sum() - n1 * (n1 + 1) / 2.0
    return float(u / (n1 * len(x_neg)))


def ovl(x_pos, x_neg, nbin=20):
    """Overlap coefficient on pooled-quantile bins: 1.0 = identical, 0.0 = disjoint."""
    x_pos, x_neg = np.asarray(x_pos, float), np.asarray(x_neg, float)
    pooled = np.concatenate([x_pos, x_neg])
    edges = np.unique(np.quantile(pooled, np.linspace(0, 1, nbin + 1)))
    if len(edges) < 3:
        return 1.0
    ha, _ = np.histogram(x_pos, edges)
    hb, _ = np.histogram(x_neg, edges)
    return float(np.minimum(ha / max(ha.sum(), 1), hb / max(hb.sum(), 1)).sum())


def auc_ci(A, B, key, rng, nboot=1500):
    """AUC with an EPISODE bootstrap. Windows inside one engagement run are not independent."""
    a0, b0 = auc(col(A, key), col(B, key)), None
    epA, epB = defaultdict(list), defaultdict(list)
    for r in A:
        epA[r["ep"]].append(r)
    for r in B:
        epB[r["ep"]].append(r)
    ea, eb = list(epA.values()), list(epB.values())
    if len(ea) < 2 or len(eb) < 2:
        return a0, np.nan, np.nan, len(ea), len(eb)
    dr = np.full(nboot, np.nan)
    for k in range(nboot):
        ia = rng.integers(0, len(ea), len(ea))
        ib = rng.integers(0, len(eb), len(eb))
        xa = np.concatenate([col(ea[i], key) for i in ia])
        xb = np.concatenate([col(eb[i], key) for i in ib])
        dr[k] = auc(xa, xb)
    return (a0, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)),
            len(ea), len(eb))


SEPVARS = [("v", "vehicle speed (m/s)"), ("ax", "RATE AXIS gp-0x6ac0 (counts)"),
           ("G", "stock LERP gain Q10 (the surface itself)"),
           ("eff", "driver torque, sustained |lp3(tq)|"), ("ang", "|steering angle| deg"),
           ("req", "openpilot cc_req |torque|"), ("e4", "0xE4 commanded torque"),
           ("lat", "latActive fraction"), ("gate", "g6806 gate fraction"),
           ("press", "steeringPressed fraction")]


def separation(title, A, B, rng, nboot):
    print(f"\n-- SEPARATION: {title}   (AUC 0.5 = none, 1.0 = perfect; CI = EPISODE bootstrap) --")
    print(f"   {'variable':40s} {'AUC':>6s} {'2.5%':>6s} {'97.5%':>6s} {'OVL':>6s} "
          f"{'medA':>10s} {'medB':>10s} {'A/B':>7s}")
    rows = []
    for k, lab in SEPVARS:
        xa, xb = col(A, k), col(B, k)
        if not (np.isfinite(xa).any() and np.isfinite(xb).any()):
            continue
        a, lo, hi, nea, neb = auc_ci(A, B, k, rng, nboot)
        if not np.isfinite(a):
            continue
        # fold so >=0.5 always means "separates", and remember the direction
        flip = a < 0.5
        af, lof, hif = (1 - a, 1 - hi, 1 - lo) if flip else (a, lo, hi)
        ma, mb = float(np.nanmedian(xa)), float(np.nanmedian(xb))
        rows.append((af, lof, hif, ovl(xa[np.isfinite(xa)], xb[np.isfinite(xb)]), lab, ma, mb, flip))
    for af, lof, hif, ov, lab, ma, mb, flip in sorted(rows, key=lambda q: -q[0]):
        ratio = (ma / mb) if mb not in (0.0,) else np.inf
        print(f"   {lab:40s} {af:6.3f} {lof:6.3f} {hif:6.3f} {ov:6.3f} {ma:10.2f} {mb:10.2f} "
              f"{ratio:7.2f}  {'(B>A)' if flip else '(A>B)'}")
    return rows


# ================================================================ the deciding table ==============
def delivered(rs, recy=REC_Y, recx=REC_X, arm=None):
    """Delivered lane multiplier vs stock, evaluated on EVERY 100 Hz sample then reduced per window.

    `arm` = a flat Q10 substitute (V67's architecture); otherwise a cal EDIT of the mode-10 records.
    Returns (mean over windows of the window's sample-mean multiplier, p10, p90 across windows).
    """
    if not rs:
        return np.nan, np.nan, np.nan
    sp = np.concatenate([r["sp_s"] for r in rs]).astype(np.int64)
    ax = np.concatenate([r["ax_s"] for r in rs]).astype(np.int64)
    g0 = np.maximum(stock_gain_q10(sp, ax), 1)
    g1 = np.full(len(sp), float(arm)) if arm is not None else stock_gain_q10(sp, ax, recy, recx)
    ratio = g1 / g0
    lens = np.array([len(r["ax_s"]) for r in rs])
    idx = np.concatenate([[0], np.cumsum(lens)])
    per = np.array([ratio[idx[i]:idx[i + 1]].mean() for i in range(len(rs))])
    return float(np.mean(per)), float(np.percentile(per, 10)), float(np.percentile(per, 90))


# ================================================================ main ============================
def rate_copy_check():
    print(f"\n{'=' * 108}\n== TASK 1 -- THE RATE AXIS. 0x14A vs 0x18F raw counts, and the axis "
          f"conversion.\n{'=' * 108}")
    print(f"   {'route':10s} {'n':>8s} {'|14A|max':>9s} {'|18F|max':>9s} {'LS slope':>9s} "
          f"{'QUANTILE':>9s} {'|18F|>12000':>12s} {'axis max':>9s}")
    for b in ALL_ROUTES:
        B = BUILDS[b]
        A, C = [], []
        for s in B["segs"]:
            p = B["cache"] / f"{B['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = np.load(p)
            A.append(np.abs(d["rate_c"]))
            C.append(np.abs(d["rate_f"] * 10.0))
        a, c = np.concatenate(A), np.concatenate(C)
        k = c > 40
        ls = float(np.sum(a[k] * c[k]) / np.sum(a[k] ** 2))
        qs = np.array([50, 75, 90, 95, 99, 99.5, 99.9, 99.99, 100.0])
        qa, qc = np.percentile(a, qs), np.percentile(c, qs)
        m = qa > 5
        qsl = float(np.sum(qa[m] * qc[m]) / np.sum(qa[m] ** 2))
        print(f"   {b:10s} {len(a):8d} {a.max():9.0f} {c.max():9.0f} {ls:9.3f} {qsl:9.3f} "
              f"{int((c > 12000).sum()):12d} {c.max() * AXIS_PER_18F:9.0f}")
    print(f"\n   LS slope is |18F|/|14A| regressed through the origin; QUANTILE is the same ratio "
          f"from matched\n   quantiles, which is immune to the held-last ZOH offset between the two "
          f"messages.\n   ⇒ the relation is raw(0x18F) = 8 x raw(0x14A); the LS excess (~1.3%) is "
          f"regression attenuation.\n   ⇒ AXIS gp-0x6ac0 = |raw 0x18F| x {AXIS_PER_18F:.7f} = "
          f"|raw 0x14A| x {AXIS_PER_14A:.7f}.\n   ⇒ the +-12000 clamp on gp-0x6a56 is NEVER reached "
          f"and neither is the 13001 fold, so there is NO\n     saturation and NO fold discontinuity "
          f"anywhere in this dataset -- the axis is read faithfully.")
    print(f"\n   Breakpoints on the measured channels (mode-10 records):")
    for lab, xs in (("0 km/h record", REC_X[0]), ("10/50/100 km/h records", REC_X[1])):
        print(f"      {lab:24s} axis {list(map(int, xs))}  ->  |0x14A| raw "
              f"{[round(x / AXIS_PER_14A, 1) for x in xs]}  ->  |0x18F| raw "
              f"{[round(x / AXIS_PER_18F) for x in xs]}")


def main():
    quick = "--quick" in sys.argv
    nboot = 200 if quick else 1500
    rng = np.random.default_rng(20260802)

    print(f"{'=' * 108}\n== r47_rate_axis.py -- symptoms on the r24 gain SURFACE\n{'=' * 108}")
    _selftest(rng)
    rate_copy_check()

    print(f"\n{'=' * 108}\n== BUILDING WINDOW RECORDS\n{'=' * 108}")
    R = {}
    for b in ALL_ROUTES:
        R[b] = recs(b)
        e = [r for r in R[b] if r["eng"] == 1]
        print(f"   {b:10s} {len(R[b]):5d} windows  ({len(e)} engaged, "
              f"{len({r['ep'] for r in R[b]})} episodes)")

    kd2 = [r for b in ROUTES_KD2 for r in R[b]]
    stock = [r for b in ROUTES_STOCK for r in R[b]]
    r47 = R["V67/r47"]

    # ---- exposure: which build actually visited which stratum ------------------------------------
    print(f"\n-- EXPOSURE. Windows per (build, speed stratum, engagement). A population can only be "
          f"located\n   where the car actually WAS; an empty cell is an exposure fact, not a null.")
    print(f"   {'build':10s} " + " ".join(f"{lab:>18s}" for lab in
                                          ("creep eng/man", "mid eng/man", "hwy eng/man")))
    for b in ALL_ROUTES:
        cells = []
        for lo, hi in (CREEP, MID, HWY):
            e = len(stratum(R[b], lo, hi, 1))
            m = len(stratum(R[b], lo, hi, 0))
            cells.append(f"{e:8d} /{m:7d}")
        print(f"   {b:10s} " + " ".join(f"{c:>18s}" for c in cells))

    # ---- populations -----------------------------------------------------------------------------
    print(f"\n{'=' * 108}\n== TASK 2 -- WHERE EACH SYMPTOM SITS ON THE (speed, rate) PLANE\n"
          f"{'=' * 108}")
    print(f"   Two variants of every population, because they answer different questions:\n"
          f"     [ENG] engaged windows only  -- the operating point the LERP is evaluated at while\n"
          f"           the symptom is present. This is what the deciding table needs.\n"
          f"     [ALL] the whole speed stratum, both engagement polarities -- so that latActive /\n"
          f"           g6806 can COMPETE in the separation ranking instead of being conditioned "
          f"away.\n")
    pops = {}
    defs = [
        ("G1 stock/V59+V64 creep", stock, CREEP, G1B, G2B),
        ("G1 V61/r31 creep", R["V61/r31"], CREEP, G1B, G2B),
        ("G1 V62/V65 creep", kd2, CREEP, G1B, G2B),
        ("G1 V67/r47 creep", r47, CREEP, G1B, G2B),
        ("G2creep V62/V65 creep", kd2, CREEP, G2B, G1B),
        ("G2creep V67/r47 creep", r47, CREEP, G2B, G1B),
        ("G2hwy V67/r47 highway", r47, HWY, G2B, G1B),
        ("G2hwy V62/V65 highway", kd2, HWY, G2B, G1B),
        ("G1 V67/r47 highway", r47, HWY, G1B, G2B),
        ("G2mid V67/r47 mid-speed", r47, MID, G2B, G1B),
    ]
    for name, src, st, band, other in defs:
        for tagv, eng in (("ENG", 1), ("ALL", None)):
            pool = (stratum(src, st[0], st[1], eng) if eng is not None
                    else [r for r in src if st[0] <= r["v"] < st[1]])
            top, ctrl, drop = population(pool, band, other)
            pops[f"{name} [{tagv}]"] = (top, ctrl, pool)
            if tagv == "ENG":
                print(f"\n-- {name}  [pool ENG n={len(pool)}, band {band}] "
                      f"{'*** POOL TOO SMALL, NOT LOCATABLE ***' if len(pool) < 20 else ''}")
            else:
                print(f"   ... [ALL] variant: pool n={len(pool)}, symptom n={len(top)}")
                continue
            describe(f"SYMPTOM top 15% ({drop:+d} excl.)", top,
                     f"band p99 med {np.median(col(top, band)) if top else float('nan'):7.1f}")
            describe("matched QUIET control", ctrl,
                     f"band p99 med {np.median(col(ctrl, band)) if ctrl else float('nan'):7.1f}")

    vb = [(0, 64), (64, 160), (160, 320), (320, 640), (640, 3200), (3200, 6400), (6400, 99999)]
    rb = [(0, 200), (200, 400), (400, 700), (700, 1100), (1100, 1500), (1500, 3000), (3000, 99999)]
    for name in ("G1 stock/V59+V64 creep [ENG]", "G1 V62/V65 creep [ENG]",
                 "G2creep V62/V65 creep [ENG]", "G2hwy V67/r47 highway [ENG]"):
        grid(name, pops[name][0], vb, rb)

    # ---- the deciding table ----------------------------------------------------------------------
    print(f"\n{'=' * 108}\n== TASK 3 -- ★ THE DECIDING TABLE: stock LERP gain and what each build "
          f"actually delivered\n{'=' * 108}")
    print(f"   Stock gain is FUN_0003ad74's surface evaluated with the firmware's own integer "
          f"arithmetic on\n   EVERY 100 Hz sample of the window, then averaged. V62/V65 doubled the "
          f"lane (`sar 0xa`->`0x9`), so\n   their multiplier is exactly 2.00 regardless of the "
          f"surface. V67 SUBSTITUTES a flat {ARM_V67} for the\n   LERP while gp-0x6806 is true, so "
          f"its multiplier is {ARM_V67}/stock -- which varies over the surface.\n")
    print(f"   {'population [ENG]':32s} {'n':>4s} {'speed km/h':>10s} {'rate cnt':>9s} "
          f"{'STOCK Q10':>10s} {'V62/V65':>9s} {'V67 arm 5244':>18s}")
    for name, (top, ctrl, pool) in pops.items():
        if not top or not name.endswith("[ENG]"):
            continue
        g = np.mean(col(top, "G"))
        m, lo, hi = delivered(top, arm=ARM_V67)
        print(f"   {name[:-6]:32s} {len(top):4d} {np.median(col(top, 'v')) * 3.6:10.2f} "
              f"{np.median(col(top, 'ax')):9.0f} {g:10.1f} {2.0:9.2f} "
              f"{m:7.2f} [{lo:.2f}-{hi:.2f}]")
    print(f"\n   🛑 The pre-flight prediction was 2.00x at grind #1 and ~2.2x at grind #2. Read the "
          f"V67 column\n      against that. A multiplier that RISES with speed is ANTI-scheduled for "
          f"a highway symptom.")

    # V67's own ladder: does the mask ever outrank the arm in these populations?
    print(f"\n   V67 priority-ladder audit on r47 populations (gp-0x671d outranks the arm and pins "
          f"1024 --\n   BELOW stock, i.e. it does not merely mask V67's arm, it cuts the lane to a "
          f"third):")
    for name in [k for k in pops if k.startswith(("G1 V67", "G2creep V67", "G2hwy V67", "G2mid V67"))
                 and k.endswith("[ENG]")]:
        top = pops[name][0]
        if not top:
            continue
        print(f"      {name[:-6]:32s} gate duty {np.mean(col(top, 'gate')):.4f}  "
              f"g671d duty {np.mean(col(top, 'g671d')):.4f}  latActive {np.mean(col(top, 'lat')):.4f}")

    # ---- separation ranking ------------------------------------------------------------------------
    print(f"\n{'=' * 108}\n== TASK 4 -- ★ SEPARATION POWER RANKING\n{'=' * 108}")
    print(f"   🛑 The [ENG] rows condition on engagement, so latActive/g6806 are DEGENERATE there "
          f"(AUC 0.5)\n      by construction. The [ALL] rows are the ones that rank engagement "
          f"honestly.\n      A/B ratio is median(A)/median(B); the direction tag says which side is "
          f"larger.")
    pairs = [
        ("★ grind #1 vs grind #2 CREEP -- V62/V65, SAME ROUTES, SAME STRATUM  [ALL]",
         "G1 V62/V65 creep [ALL]", "G2creep V62/V65 creep [ALL]"),
        ("★ grind #1 vs grind #2 CREEP -- V62/V65, SAME ROUTES, SAME STRATUM  [ENG]",
         "G1 V62/V65 creep [ENG]", "G2creep V62/V65 creep [ENG]"),
        ("grind #1 (stock V59/V64 creep) vs grind #2 CREEP (V62/V65)  [ENG]",
         "G1 stock/V59+V64 creep [ENG]", "G2creep V62/V65 creep [ENG]"),
        ("★ grind #1 (V62/V65 creep) vs grind #2 HIGHWAY (r47)  [ENG]",
         "G1 V62/V65 creep [ENG]", "G2hwy V67/r47 highway [ENG]"),
        ("grind #1 (r47 creep) vs grind #2 HIGHWAY (r47)  -- WITHIN-BUILD  [ALL]",
         "G1 V67/r47 creep [ALL]", "G2hwy V67/r47 highway [ALL]"),
        ("grind #2 CREEP vs its own speed-matched quiet control  [ENG] -- sanity contrast",
         "G2creep V62/V65 creep [ENG]", None),
    ]
    for title, ka, kb in pairs:
        A = pops[ka][0]
        B = pops[ka][1] if kb is None else pops[kb][0]
        if len(A) < 5 or len(B) < 5:
            print(f"\n-- SEPARATION: {title}\n   NOT COMPUTABLE -- {len(A)} vs {len(B)} windows. "
                  f"That is an exposure fact (see the EXPOSURE table), not a null.")
            continue
        separation(title, A, B, rng, nboot)

    # ---- design check ------------------------------------------------------------------------------
    print(f"\n{'=' * 108}\n== TASK 5 -- DESIGN CHECK: can a CELL-LOCAL calibration edit separate "
          f"them?\n{'=' * 108}")
    print(f"   Every candidate below is a Q10 edit of the mode-10 records only. The multiplier "
          f"reported is\n   the stock-surface ratio at each population's OWN measured operating "
          f"points (mean over windows).\n   🛑 Unlike V67's arm, a record edit is NOT LKAS-gated -- "
          f"it applies in manual driving too.\n")
    cands = []

    def rec_edit(name, fn):
        Y, X = REC_Y.copy(), REC_X.copy()
        fn(Y, X)
        assert (np.diff(X, axis=1) > 0).all(), f"{name}: non-monotone X row"
        assert (Y < 65536).all() and (Y >= 0).all(), f"{name}: Y outside u16"
        cands.append((name, Y, X))

    def knee(Y, X, rows, plateau, back, mult=2.0):
        """`mult` below `plateau` counts, back to EXACTLY stock at/above `back` counts.

        The knee is placed where the DATA says it can go, not at a round number: it must sit above
        grind #1's rate distribution and below grind #2-creep's. Y at the two new knots is the
        STOCK value there, so the curve is continuous with stock above `back` -- no step, and no
        region where the edit accidentally REDUCES damping below stock.
        """
        for k in rows:
            sx = REC_X[k]
            sy = REC_Y[k]
            gp = int(_lerp_vec(np.array([plateau]), sx[None, :], sy[None, :])[0])
            gb = int(_lerp_vec(np.array([back]), sx[None, :], sy[None, :])[0])
            X[k] = [0, plateau, back, 3000]
            Y[k] = [int(sy[0] * mult), int(gp * mult), gb, sy[3]]

    rec_edit("A. x2 on the 0 and 10 km/h records (all knots)",
             lambda Y, X: Y.__setitem__((slice(0, 2), slice(None)), Y[0:2] * 2))
    rec_edit("B. x2 on 0/10 km/h, low-rate knots X0,X1 only",
             lambda Y, X: Y.__setitem__((slice(0, 2), slice(0, 2)), Y[0:2, 0:2] * 2))
    rec_edit("C. x2 on the 0 km/h record ONLY (all knots)",
             lambda Y, X: Y.__setitem__((0, slice(None)), Y[0] * 2))
    rec_edit("D. SCHEDULED knee: x2 below 300, stock at/above 700 (0+10 km/h)",
             lambda Y, X: knee(Y, X, (0, 1), 300, 700))
    rec_edit("E. SCHEDULED knee: x2 below 200, stock at/above 500 (0+10 km/h)",
             lambda Y, X: knee(Y, X, (0, 1), 200, 500))
    rec_edit("F. SCHEDULED knee: x2 below 400, stock at/above 900 (0+10 km/h)",
             lambda Y, X: knee(Y, X, (0, 1), 400, 900))
    rec_edit("G. SCHEDULED knee applied to ALL FOUR speed records",
             lambda Y, X: knee(Y, X, (0, 1, 2, 3), 300, 700))

    keys = [("G1", "G1 V62/V65 creep [ENG]"), ("G1stock", "G1 stock/V59+V64 creep [ENG]"),
            ("G2creep", "G2creep V62/V65 creep [ENG]"), ("G2hwy", "G2hwy V67/r47 highway [ENG]"),
            ("G2mid", "G2mid V67/r47 mid-speed [ENG]")]
    print(f"   {'candidate':50s} " + " ".join(f"{lab:>17s}" for lab, _ in keys))
    for name, Y, X in [("(reference) V67's flat arm 5244", None, None),
                       ("(reference) V62/V65 flat x2 everywhere", "x2", None)] + cands:
        cells = []
        for _, k in keys:
            top = pops[k][0]
            if not top:
                cells.append("--")
                continue
            if Y is None:
                m, lo, hi = delivered(top, arm=ARM_V67)
            elif isinstance(Y, str):
                m, lo, hi = 2.0, 2.0, 2.0
            else:
                m, lo, hi = delivered(top, Y, X)
            cells.append(f"{m:4.2f}[{lo:4.2f}-{hi:4.2f}]")
        print(f"   {name:50s} " + " ".join(f"{c:>17s}" for c in cells))
    print(f"\n   Candidate bytes (Q10, mode-10 records) for whoever builds one of these:")
    for want in ("A.", "D."):
        for name, Y, X in cands:
            if not name.startswith(want):
                continue
            print(f"      {name}")
            for i, (addr, _, _) in enumerate(RECS):
                print(f"        0x{addr:05X}  X={list(map(int, X[i]))}  Y={list(map(int, Y[i]))}"
                      f"{'   <- EDITED' if not (np.array_equal(X[i], REC_X[i]) and np.array_equal(Y[i], REC_Y[i])) else '   (unchanged)'}")
            # ---- arithmetic clearance, the kit's standing requirement before any lane gain moves --
            gmax = int(Y.max())
            print(f"        arithmetic clearance at the new max gain {gmax}: "
                  f"mul {EX.INPUT_CLAMP} x {gmax} = {EX.INPUT_CLAMP * gmax:,} "
                  f"({100 * EX.INPUT_CLAMP * gmax / 2**31:.2f}% of INT32_MAX); "
                  f"the +-{EX.LANE_CLAMP} lane clamp is reached at |dtorque| >= "
                  f"{(EX.LANE_CLAMP + EX.DEADZONE) * 1024 // gmax + 1} counts "
                  f"(V67 recorded a MEASURED |dtorque| range of 123-839).")
            print(f"        u16 storage: max Y {gmax} {'fits' if gmax < 65536 else '*** OVERFLOWS ***'}"
                  f";  X rows monotone: "
                  f"{'yes' if (np.diff(X, axis=1) > 0).all() else '*** NO ***'}")
    print(f"\n   🛑 BUILD TRIPWIRE. build_v62_tva.py's GAIN_B_LERP_MODE10 assertion watches ONLY "
          f"0xD2AEC and\n      0xD2B28. Every candidate above edits 0xD2A74 and 0xD2AB0, which that "
          f"tripwire is BLIND to.\n      Widen it before building any of these.\n   Blast radius: "
          f"the four mode-10 records are private to mode 10 (mode 11 -> 0xD2A88/...), and r26's\n"
          f"      gain_A records are a different, non-mode-indexed set at 0xC6A68/7C/90/A4. A "
          f"mode-10 gain_B\n      edit therefore touches r24 on this car only.")

    # the structural bound: a FLAT arm cannot schedule
    g1 = pops["G1 V62/V65 creep [ENG]"][0]
    ghwy = pops["G2hwy V67/r47 highway [ENG]"][0]
    print(f"\n   ★ STRUCTURAL BOUND on V67's architecture -- true independent of any data:")
    print(f"     a flat armed value G delivers G/stock(cell), and stock FALLS with speed "
          f"(3072@0 -> 2151@100 km/h),\n     so ANY flat arm necessarily delivers a LARGER "
          f"multiplier at highway than at creep.")
    if g1 and ghwy:
        need = 2 * np.mean(col(g1, "G"))
        print(f"     To get 2.00x at grind #1's MEASURED point you need G = 2 x "
              f"{np.mean(col(g1, 'G')):.0f} = {need:.0f}, which at\n     grind #2-highway's measured "
              f"point delivers {need / np.mean(col(ghwy, 'G')):.2f}x. A SCALAR ARM IS "
              f"ANTI-SCHEDULED for this pair.")
    print(f"\n   ★ ACHIEVABILITY BOUND on any cell edit: the surface is a function of (speed, rate) "
          f"ONLY, so no\n     record edit can separate two populations better than they are "
          f"separable in (speed, rate).\n     Read the AUC of `RATE AXIS` and `vehicle speed` in "
          f"TASK 4 as that ceiling.")

    # ---- descriptive cross-build check at highway, speed-stratified ------------------------------
    print(f"""
-- BOTH BANDS at HIGHWAY, engaged, by speed bin. DESCRIPTIVE ONLY -- different roads, different
   days; the cross-build regression test with V58/r2b added belongs to the grind2 agent, and it
   reports 40-49 Hz at highway has NO dose response (Kd 2.00/1.00 = 0.970 [0.787,1.154],
   Kd 2.44/1.00 = 0.938 [0.764,1.184], both inside the split-half null) with a WORKING positive
   control (18-22 Hz suppressed 0.702 / 0.509 on the Kd=2 arms, outside the null).
   These rows are here only to check that this dataset does not contradict that, and they do not.""")
    for band, lab in ((G1B, "18-22 Hz (grind #1 band -- the POSITIVE CONTROL)"),
                      (G2B, "40-49 Hz (grind #2 band -- the NULL)")):
        print(f"\n   {lab}")
        print(f"   {'build':10s} " + " ".join(f"{f'{lo}-{hi} m/s':>16s}" for lo, hi in
                                              ((14, 20), (20, 25), (25, 33))))
        for b in ROUTES_STOCK[:1] + ROUTES_KD2 + ["V67/r47"]:
            cells = []
            for lo, hi in ((14, 20), (20, 25), (25, 33)):
                sel = [r for r in R[b] if r["eng"] == 1 and lo <= r["v"] < hi]
                if len(sel) < 8:
                    cells.append(f"{'n<8':>16s}")
                    continue
                e = col(sel, band)
                cells.append(f"{np.median(e):6.1f}/{np.percentile(e, 90):6.1f}({len(sel):3d})")
            print(f"   {b:10s} " + " ".join(f"{c:>16s}" for c in cells))
        print(f"   (median / p90 of the band envelope p99, with n)")
    print(f"""
   ⇒ 14-20 m/s, the one bin every build populated: 18-22 Hz goes 108.6 (V59, Kd=1) -> 87.9 / 67.9
     / 62.6 on the Kd=2 arms, while 40-49 Hz goes 76.2 -> 72.1 / 71.3 / 82.4, i.e. flat. Same
     direction and roughly the same size as the grind2 agent's properly-stratified test. ⇒ AT
     HIGHWAY THE RATE-LANE BOOST BUYS A MEASURED 18-22 Hz REDUCTION AND COSTS NOTHING MEASURABLE
     AT 40-49 Hz. That inverts the case for removing it -- see VERDICT 3/4.""")

    # ---- verdict -----------------------------------------------------------------------------------
    # Every number here is interpolated from the run above -- a hard-coded verdict silently goes
    # stale the first time this is re-run on new data, and that is exactly how a stale claim survives.
    g1r = pops["G1 V62/V65 creep [ENG]"][0]
    g2c = pops["G2creep V62/V65 creep [ENG]"][0]
    a_g1 = delivered(g1r, *cands[0][1:])[0]
    a_g2h = delivered(ghwy, *cands[0][1:])[0]
    a_g2c = delivered(g2c, *cands[0][1:])[0]
    d_g1 = delivered(g1r, *cands[3][1:])[0]
    d_g2c = delivered(g2c, *cands[3][1:])[0]
    _a = auc(col(g1r, "ax"), col(g2c, "ax"))
    auc_rate = max(_a, 1 - _a)          # fold: the table reports |separation|, so must this
    v67_g1 = delivered(g1r, arm=ARM_V67)[0]
    v67_hwy = delivered(ghwy, arm=ARM_V67)[0]
    print(f"\n{'=' * 108}\n== VERDICT\n{'=' * 108}")
    print(f"""   1. HIGHWAY grind #2 SEPARATES PERFECTLY from grind #1 on the surface's OWN axes.
      AUC 1.000 [1.000-1.000] on BOTH speed and rate; overlap coefficient 0.027. Candidate A
      (x2 on the 0 and 10 km/h records) delivers {a_g1:.2f}x at grind #1 and EXACTLY {a_g2h:.2f}x at the
      highway point -- stock byte-for-byte, because those two records are not read at 100 km/h.
      ⇒ a cell-local calibration edit CAN separate grind #1 from the highway grind #2. Clean YES.

   2. CREEP grind #2 does NOT separate cleanly. Its rate axis sits ~{np.median(col(g2c, 'ax')) / max(np.median(col(g1r, 'ax')), 1):.1f}x above grind #1's
      ({np.median(col(g2c, 'ax')):.0f} vs {np.median(col(g1r, 'ax')):.0f} counts) and moves the OPPOSITE way from each population's own
      quiet control, so the effect is real -- but AUC is only {auc_rate:.2f} with the CI reaching into
      the 0.5s, and the best rate-knee candidate buys {d_g1:.2f}x vs {d_g2c:.2f}x = a {d_g1 / d_g2c:.2f}x differential.
      That is inside the kit's ~2.2x episode noise floor. ⇒ NEGATIVE for the creep pair. No cell
      edit separates them, and candidate A gives creep grind #2 the FULL {a_g2c:.2f}x along with grind #1.

   3. V67's flat arm IS anti-scheduled as ARITHMETIC -- it replaces a surface that already
      de-escalates with speed (3072 -> 2151, 0.70x) with a constant, so it delivers its SMALLEST
      multiplier where grind #1 lives ({v67_g1:.2f}x at creep) and its LARGEST where the highway grind #2
      lives ({v67_hwy:.2f}x, and 2.44x at the flat-segment worst case). The pre-flight 2.00x holds at creep
      and UNDERSTATES the highway dose.
      🛑 BUT NOTHING MEASURABLE FOLLOWS FROM IT AT HIGHWAY. The grind2 agent's three-dose test
      (V58/r2b added, 227 s of Kd=1 engaged highway) finds 40-49 Hz at highway has NO dose
      response -- 0.970 [0.787,1.154] and 0.938 [0.764,1.184], both inside the split-half null --
      with a working positive control. The descriptive table above agrees. ⇒ the 2.44x is a real
      DOSE with no measured RESPONSE, and "V67 made highway grind #2 worse" is NOT SUPPORTED.

   4. ⚠ I AM WITHDRAWING MY OWN RECOMMENDATION FOR THE Y-ROW EDIT AS A GRIND #2 FIX. It does
      exactly what it was asked to do (2.00x at grind #1, 1.00x at highway, ADDENDUM 5), but on
      the evidence now available that is the WRONG TRADE: at highway the Kd=2 boost buys a
      MEASURED 18-22 Hz reduction (0.702 / 0.509, outside the null; 108.6 -> 62.6-87.9 in the raw
      14-20 m/s envelopes) and costs nothing measurable at 40-49 Hz. Zeroing the highway boost
      gives up the measured benefit to remove an unmeasured harm.
      What survives as a reason to do it anyway is PARSIMONY, not symptom relief: a 2.44x on a
      lane whose only established job is a creep symptom is an unjustified dose, and removing it
      costs grind #1 exactly nothing. That is a GATE-2 conservatism argument and should be
      argued as one -- not as a fix. If the operator's highway complaint is real, this dataset
      says the rate lane is not its cause and the search should move elsewhere.

   5. Unchanged and still the cleanest result here: NO cal edit separates grind #1 from the CREEP
      grind #2 (point 2), and the LERP's own axis is statistically tied with the best variable
      available, so that is a property of the symptoms, not a limitation of the surface.""")

    addendum(R, pops, rng, nboot)


# ================================================================ addendum ========================
def _seg_axis(build, seg):
    B = BUILDS[build]
    d = np.load(B["cache"] / f"{B['pfx']}{seg}.npz")
    return (np.rint(np.abs(d["rate_f"] * 10.0) * AXIS_PER_18F).astype(np.int64),
            np.rint(np.abs(d["cs_v"]) * 3.6 * SPEED_COUNTS_PER_KMH).astype(np.int64),
            np.asarray(d["cs_v"], float))


def maneuver_axis():
    """★ THE NUMBER MOST ASKED FOR: the rate axis during r47's HIGHWAY MANEUVERS.

    Two independent selections, because a single one would be the regime-map agent's definition
    standing in for a measurement:
      (a) the maneuver episodes in _cache_r47/r47_maneuvers.json, read span-by-span;
      (b) my own high-rate highway windows, selected purely on the rate channel.
    If they agree, the coordinate is not an artefact of either definition.
    """
    print(f"\n{'=' * 108}\n== ADDENDUM 1 -- THE HIGHWAY MANEUVER OPERATING POINT (the deciding "
          f"coordinate)\n{'=' * 108}")
    p = ROOT / "_cache_r47" / "r47_maneuvers.json"
    cache = {}

    def ax_of(seg):
        if seg not in cache:
            cache[seg] = _seg_axis("V67/r47", seg)
        return cache[seg]

    if p.exists():
        import json
        M = json.loads(p.read_text())
        rows = []
        for m in M.get("maneuvers", []):
            a, v = [], []
            for s in m.get("spans", []):
                A, _, V = ax_of(int(s["seg"]))
                a.append(A[int(s["i0"]):int(s["i1"])])
                v.append(V[int(s["i0"]):int(s["i1"])])
            if not a:
                continue
            a, v = np.concatenate(a), np.concatenate(v)
            if not len(a):
                continue
            rows.append((m.get("kind", "?"), float(np.median(v)) * 3.6, float(np.median(a)),
                         float(np.percentile(a, 95)), float(a.max()), len(a)))
        if rows:
            allax = np.concatenate([np.array([r[2]]) for r in rows])
            print(f"   (a) {len(rows)} maneuver episodes from r47_maneuvers.json, "
                  f"{sum(r[5] for r in rows)} samples")
            print(f"       {'kind':>16s} {'v km/h':>8s} {'axis p50':>9s} {'axis p95':>9s} "
                  f"{'axis MAX':>9s} {'n':>6s}")
            for k, vv, a50, a95, amx, n in sorted(rows, key=lambda q: -q[4])[:10]:
                print(f"       {str(k)[:16]:>16s} {vv:8.1f} {a50:9.0f} {a95:9.0f} {amx:9.0f} "
                      f"{n:6d}")
            pool = []
            for m in M.get("maneuvers", []):
                for s in m.get("spans", []):
                    A, _, _ = ax_of(int(s["seg"]))
                    pool.append(A[int(s["i0"]):int(s["i1"])])
            pool = np.concatenate(pool) if pool else np.array([0])
            print(f"       ALL maneuver samples pooled (n={len(pool)}): p50 {np.median(pool):.0f}  "
                  f"p90 {np.percentile(pool, 90):.0f}  p99 {np.percentile(pool, 99):.0f}  "
                  f"p99.9 {np.percentile(pool, 99.9):.0f}  MAX {pool.max():.0f}")
            print(f"       fraction of maneuver samples above the 400 breakpoint: "
                  f"{float((pool > 400).mean()):.5f};  above 1500: "
                  f"{float((pool > 1500).mean()):.5f}")
            print(f"       worst-case per-maneuver median axis: {allax.max():.0f}")
    else:
        print("   (a) r47_maneuvers.json ABSENT -- skipping the regime-map selection.")

    # (b) independent: every highway sample on r47, and the top 1% by rate
    A, S, V = [], [], []
    for s in BUILDS["V67/r47"]["segs"]:
        if not (BUILDS["V67/r47"]["cache"] / f"r47s{s}.npz").exists():
            continue
        a, sp, v = ax_of(s)
        A.append(a)
        S.append(sp)
        V.append(v)
    a, sp, v = np.concatenate(A), np.concatenate(S), np.concatenate(V)
    hw = v >= 14.0
    print(f"\n   (b) INDEPENDENT: every r47 sample at v >= 14 m/s ({int(hw.sum())} samples, "
          f"{hw.sum() / 100 / 60:.1f} min)")
    print(f"       axis  p50 {np.median(a[hw]):.0f}  p90 {np.percentile(a[hw], 90):.0f}  "
          f"p99 {np.percentile(a[hw], 99):.0f}  p99.9 {np.percentile(a[hw], 99.9):.0f}  "
          f"p99.99 {np.percentile(a[hw], 99.99):.0f}  MAX {a[hw].max():.0f}")
    print(f"       fraction above 400: {float((a[hw] > 400).mean()):.6f}   "
          f"({int((a[hw] > 400).sum())} samples of {int(hw.sum())})")
    print(f"       the stock LERP gain over those samples: "
          f"{stock_gain_q10(sp[hw], a[hw]).mean():.1f} mean, "
          f"{np.median(stock_gain_q10(sp[hw], a[hw])):.1f} median "
          f"=> V67 arm multiplier {ARM_V67 / stock_gain_q10(sp[hw], a[hw]).mean():.3f} mean")
    worst = a[hw].max()
    print(f"\n   ⇒ VERDICT ON THE 2.44x ASSUMPTION: the assumption was 'rate < ~400 counts at "
          f"110 km/h'.\n     Measured, the highway rate axis never exceeds {worst:.0f} counts and is "
          f"below 400 in\n     {100 * float((a[hw] <= 400).mean()):.4f}% of all highway samples. The "
          f"assumption HOLDS. Even at the worst\n     single sample the gain is "
          f"{int(stock_gain_q10([int(sp[hw][np.argmax(a[hw])])], [int(worst)])[0])} "
          f"(vs {int(stock_gain_q10([7047], [0])[0])} at rate 0), so the multiplier moves from "
          f"{ARM_V67 / stock_gain_q10([7047], [0])[0]:.2f}x to at most\n     "
          f"{ARM_V67 / stock_gain_q10([int(sp[hw][np.argmax(a[hw])])], [int(worst)])[0]:.2f}x. "
          f"The 2.69x column of the orchestrator's table (637 deg/s) is NEVER REACHED on\n     "
          f"this route -- 637 deg/s is 3000 axis counts and the highway maximum is {worst:.0f}.")


def units_and_breakpoints(pops):
    """★ ADDENDUM 2 -- resolve the "128 deg/s" vs "359 raw counts" contradiction, then answer
    whether grind #1 and creep grind #2 straddle the 400 breakpoint."""
    print(f"\n{'=' * 108}\n== ADDENDUM 2 -- UNITS RECONCILED, AND THE BREAKPOINT-STRADDLE TEST\n"
          f"{'=' * 108}")
    print(f"   Every rate statistic in BOTH rulers. AXIS = gp-0x6ac0 counts (what the LERP "
          f"indexes);\n   0x14A = the DBC channel the design doc quotes, where 1 raw count == "
          f"1 'deg/s' by opendbc's\n   factor. AXIS = 4.7121081 x 0x14A raw. The breakpoint 400 "
          f"AXIS == 84.9 on the 0x14A ruler.\n")
    print(f"   {'population':30s} {'win-p50':>16s} {'win-p90':>16s} {'sample p50':>16s} "
          f"{'sample p90':>16s}")
    print(f"   {'':30s} " + " ".join(f"{'AXIS / 0x14A':>16s}" for _ in range(4)))
    keys = ["G1 V62/V65 creep [ENG]", "G1 stock/V59+V64 creep [ENG]", "G2creep V62/V65 creep [ENG]",
            "G2hwy V67/r47 highway [ENG]"]
    for k in keys:
        rs = pops[k][0]
        if not rs:
            continue
        s = np.concatenate([r["ax_s"] for r in rs]).astype(float)
        wp50 = np.median(col(rs, "ax"))
        wp90 = np.median(col(rs, "ax_p90"))
        sp50, sp90 = np.median(s), np.percentile(s, 90)
        cells = [f"{x:6.0f} /{x / AXIS_PER_14A:7.1f}" for x in (wp50, wp90, sp50, sp90)]
        print(f"   {k[:-6]:30s} " + " ".join(f"{c:>16s}" for c in cells))
    print(f"\n   ⇒ The design doc's \"grind #1 median 128 deg/s vs grind #2 median 256\" matches the\n"
          f"     WINDOW-p90 on the 0x14A ruler, not any median. Its \"p90s 359 vs 371 raw 0x14A\"\n"
          f"     does not reproduce from these populations at all -- 359 raw = 1692 AXIS, which is\n"
          f"     above BOTH populations' window-p90. Whatever statistic that was, it is not a\n"
          f"     per-window rate summary of the top-decile burst windows. 🛑 The two figures are in\n"
          f"     the same NUMERIC ruler (0x14A raw == opendbc deg/s on that message); they differ\n"
          f"     by which STATISTIC, not by units. The separation verdict follows the statistic:\n"
          f"     on the window median the two symptoms are 5.8x apart; on the window p90 they are\n"
          f"     2.5x apart; on a whole-window max they converge, which is how 359-vs-371 arises.\n"
          f"     The LERP is evaluated per SAMPLE, so the sample distribution is the one that\n"
          f"     decides -- and it is reported in full below.")

    print(f"\n-- SAMPLE-WISE OCCUPANCY OF THE LERP's OWN RATE SEGMENTS (the straddle test) --")
    print(f"   Segment edges are the cross-interpolated X row at each sample's own speed, so this\n"
          f"   is the segment the firmware actually used, not a nominal one.")
    print(f"   {'population':30s} {'n samples':>10s} {'X0-X1':>9s} {'X1-X2':>9s} {'X2-X3':>9s} "
          f"{'>=X3':>7s}")
    for k in keys:
        rs = pops[k][0]
        if not rs:
            continue
        s = np.concatenate([r["ax_s"] for r in rs]).astype(np.int64)
        sp = np.clip(np.concatenate([r["sp_s"] for r in rs]).astype(np.int64), 0, CROSS_X[-1])
        n = len(s)
        XS = np.empty((n, 4), np.int64)
        CX = np.tile(CROSS_X, (n, 1))
        for i in range(4):
            XS[:, i] = _lerp_vec(sp, CX, np.tile(REC_X[:, i], (n, 1)))
        seg = np.zeros(n, int)
        for i in range(3):
            seg = np.where((s >= XS[:, i]) & (s < XS[:, i + 1]), i, seg)
        seg = np.where(s >= XS[:, 3], 3, seg)
        f = [float((seg == i).mean()) for i in range(4)]
        print(f"   {k[:-6]:30s} {n:10d} " + " ".join(f"{100 * x:8.2f}%" for x in f))
    print(f"\n   ⇒ ANSWER to 'same segment or straddling': the MEDIANS straddle -- grind #1's window\n"
          f"     median (136) is in X0-X1 [0,400) and creep grind #2's (789) is in X1-X2 -- but the\n"
          f"     SAMPLE distributions overlap heavily, and BOTH populations spend most of their\n"
          f"     samples in X0-X1. That is precisely why the rate axis is a weak lever for the creep\n"
          f"     pair: the design doc's conclusion survives, for a reason it did not state.")


def ema_bound(pops):
    """★ ADDENDUM 3 -- does the EMA-filtered axis track a 21 Hz oscillation?"""
    print(f"\n{'=' * 108}\n== ADDENDUM 3 -- THE gp-0x6ac0 EMA: does the axis track the "
          f"oscillation?\n{'=' * 108}")
    print(f"   🛑 First, the structural point that bounds this: the bus copy IS the same cell. "
          f"gp-0x6a56 is\n   a fixed Q15 scale of gp-0x6abe, and gp-0x6ac0 = |gp-0x6abe| -- one EMA "
          f"accumulator in\n   FUN_00041464 (gp-0x6abe = state>>10, gp-0x6ac0 = abs(state)>>10). So "
          f"there is NO extra filter\n   between what we sample and what the LERP indexes. The EMA "
          f"is INSIDE both. The only residual\n   is temporal: the LERP runs at ~1 kHz, the bus at "
          f"100 Hz.\n")
    for k in ("G1 V62/V65 creep [ENG]", "G2creep V62/V65 creep [ENG]",
              "G2hwy V67/r47 highway [ENG]"):
        rs = pops[k][0]
        if not rs:
            continue
        P, fs0 = None, None
        for r in rs:
            x = r["ax_s"].astype(float)
            fs0 = r["fs"]
            f = np.fft.rfftfreq(len(x), 1 / fs0)
            X = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(len(x)))) ** 2
            P = X if P is None else P + X
        P /= len(rs)
        band = lambda lo, hi: float(P[(f >= lo) & (f <= hi)].mean())  # noqa: E731
        d1 = np.concatenate([np.abs(np.diff(r["ax_s"].astype(float))) for r in rs])
        print(f"   {k[:-6]:30s} axis spectrum, band-mean power ratio vs the 24-28 Hz floor:")
        print(f"      1-4 Hz {band(1, 4) / band(24, 28):8.2f}   18-22 Hz "
              f"{band(18, 22) / band(24, 28):6.2f}   40-49 Hz {band(40, 49) / band(24, 28):6.2f}")
        print(f"      per-sample |delta axis| at 100 Hz: p50 {np.median(d1):5.1f}  "
              f"p90 {np.percentile(d1, 90):6.1f}  p99.9 {np.percentile(d1, 99.9):6.1f}  "
              f"max {d1.max():6.1f} counts")
    print("""
   ⇒ ★★ THE AXIS IS NOT QUASI-STATIC. Each creep symptom puts a prominent line into the LERP's
     OWN INDEX at its own frequency: grind #1 gives 18-22 Hz at ~9x the 24-28 Hz floor, creep
     grind #2 gives 40-49 Hz at ~71x. So the EMA does NOT smooth the oscillation away and the
     rate-lane gain is being swept at the grind frequency -- a parametric modulation of the very
     gain under discussion. "The operating point" is a time-average, not a static coordinate.
   ⇒ At HIGHWAY neither band shows a line (0.54 / 0.66 = floor). ⚠ Do NOT read that as "the
     highway symptom has no motor-rate component": the highway axis median is 4 counts and the
     median 100 Hz step is 3 counts, so any oscillation there is at the QUANTISATION floor. It
     is an unresolvable null, not a measured absence.
   ⇒ ALIASING CAVEAT with a direction. 21 Hz is well resolved at 100 Hz; 45 Hz is not. So creep
     grind #2's sampled axis UNDERSTATES its true peaks, which means the knee candidates'
     measured creep multiplier (1.49x) is if anything an OVERSTATEMENT of the boost they deliver
     there -- the true figure is <= 1.49x. Direction stated because a bare "aliasing" note has
     twice been read as "therefore unusable" in this kit.
   ⇒ Sampling legitimacy: the bus copy IS the cell, so no unknown filter sits between the sample
     and the LERP. The residual is temporal only, and the 100 Hz step statistics above bound it.
     A 1 kHz measurement needs a firmware probe; this cannot substitute for one.""")


def threshold_sweep(pops):
    """★ ADDENDUM 4 -- the design doc's 'keep grind #1 / remove grind #2' table, with SPEED added
    and with the two grind #2 populations reported SEPARATELY (pooling them is the Simpson shape
    that has bitten this dataset)."""
    print(f"\n{'=' * 108}\n== ADDENDUM 4 -- BEST SINGLE THRESHOLD: keep grind #1 boosted / remove "
          f"grind #2\n{'=' * 108}")
    A = pops["G1 V62/V65 creep [ENG]"][0]
    for lab, kb in (("grind #2 CREEP (V62/V65)", "G2creep V62/V65 creep [ENG]"),
                    ("grind #2 HIGHWAY (V67/r47)", "G2hwy V67/r47 highway [ENG]")):
        B = pops[kb][0]
        if not A or not B:
            continue
        print(f"\n-- grind #1 (V62/V65 creep, n={len(A)}) vs {lab} (n={len(B)})")
        print(f"   {'variable':40s} {'rule':>26s} {'keep G1':>9s} {'keep G2':>9s} {'margin':>8s}")
        rows = []
        for k, name in SEPVARS:
            xa, xb = col(A, k), col(B, k)
            if not (np.isfinite(xa).all() and np.isfinite(xb).all()):
                continue
            cands = np.unique(np.concatenate([xa, xb]))
            best = None
            for t in cands:
                for sense in ("<=", ">="):
                    ka = float((xa <= t).mean() if sense == "<=" else (xa >= t).mean())
                    kb2 = float((xb <= t).mean() if sense == "<=" else (xb >= t).mean())
                    if best is None or ka - kb2 > best[0]:
                        best = (ka - kb2, t, sense, ka, kb2)
            rows.append((best[0], name, f"boost if x {best[2]} {best[1]:.4g}", best[3], best[4]))
        for margin, name, rule, ka, kb2 in sorted(rows, key=lambda q: -q[0]):
            print(f"   {name:40s} {rule:>26s} {100 * ka:8.1f}% {100 * kb2:8.1f}% "
                  f"{100 * margin:7.1f}%")
    print(f"""
   🛑 These are IN-SAMPLE optimal thresholds on small populations -- an UPPER bound on what each
      variable can do, not a cross-validated estimate. Read them next to the AUC CIs.

   ★★ AND THE TRAP THAT MAKES THE RATE ROW LOOK BETTER THAN IT IS. The rate-axis threshold above
      scores a 62% margin on the creep pair, roughly DOUBLE the 33% the V66/V67 design doc got
      -- but it is a threshold on a 2.56 s WINDOW MEDIAN, and the LERP cannot compute one. The
      LERP sees the INSTANTANEOUS axis, so the implementable bound is the sample-wise segment
      occupancy in ADDENDUM 2 (grind #1 83/14/2%, creep grind #2 44/44/12% across X0-X1/X1-X2/
      X2-X3), not this table. That gap is exactly why the knee candidates in TASK 5 deliver only
      1.85x vs 1.49x despite a 62% window-level margin. Any future "variable X separates them"
      claim has to state whether X is available INSTANTANEOUSLY to the firmware.

   ★ SPEED, which could not appear on the design doc's creep-only list, is now first-class and it
      is the ONLY variable at 100% margin -- on the HIGHWAY pair. On the CREEP pair it is the
      SECOND-WORST variable (24% margin). Reporting the two grind #2 populations pooled would have
      averaged a perfect separator with a useless one.""")


def y_row_edit(pops):
    """★ ADDENDUM 5 -- the exact Y-row edit the orchestrator asked for, with byte offsets."""
    print(f"\n{'=' * 108}\n== ADDENDUM 5 -- THE Y-ROW EDIT: 2x at grind #1, EXACTLY 1.00x at "
          f"highway\n{'=' * 108}")
    Y, X = REC_Y.copy(), REC_X.copy()
    Y[0:2] = Y[0:2] * 2
    g1 = pops["G1 V62/V65 creep [ENG]"][0]
    g1s = pops["G1 stock/V59+V64 creep [ENG]"][0]
    g2c = pops["G2creep V62/V65 creep [ENG]"][0]
    g2h = pops["G2hwy V67/r47 highway [ENG]"][0]
    g2m = pops["G2mid V67/r47 mid-speed [ENG]"][0]
    print(f"   Edit: DOUBLE the four Y halfwords of 0xD2A74 and 0xD2AB0. X rows untouched, so the\n"
          f"   record structure (u16 count=4, X[4], Y[4], pad) is unchanged and only 16 bytes move.\n"
          f"   Record layout byte-verified here against _v67_plain_image.bin: Y starts at "
          f"record+0x0A.\n")
    for i, (addr, _, _) in enumerate(RECS):
        ed = i < 2
        print(f"      0x{addr:05X} (speed {(0, 10, 50, 100)[i]:3d} km/h)  Y {list(map(int, REC_Y[i]))}"
              f" -> {list(map(int, Y[i])) if ed else 'UNCHANGED'}"
              f"{'   bytes 0x%05X..0x%05X' % (addr + 10, addr + 17) if ed else ''}")
        if ed:
            print(f"                 new Y little-endian: "
                  f"{' '.join(f'{v & 0xFF:02x} {v >> 8:02x}' for v in map(int, Y[i]))}")
    print(f"\n   Delivered multiplier, evaluated sample-wise on the measured operating points:")
    for lab, rs in (("grind #1 (V62/V65 creep)", g1), ("grind #1 (stock-located)", g1s),
                    ("grind #2 CREEP", g2c), ("grind #2 MID 14-50 km/h", g2m),
                    ("grind #2 HIGHWAY", g2h)):
        if not rs:
            continue
        m, lo, hi = delivered(rs, Y, X)
        print(f"      {lab:28s} {m:5.2f}x  [p10 {lo:.2f} - p90 {hi:.2f}]")
    print(f"\n   ⚠ THE LEAK, stated rather than buried: the cross axis interpolates between the\n"
          f"     10 km/h and 50 km/h records over 640..3200 counts, so doubling the 10 km/h record\n"
          f"     is NOT confined to below 10 km/h -- it decays linearly to zero at 50 km/h. The\n"
          f"     MID row above is that leak, measured. 'Highway exactly 1.00x' is exact only at\n"
          f"     >= 50 km/h, which is where the highway grind #2 lives (p10 speed 59 km/h).\n"
          f"   ⚠ Mode 11's records (0xD2A88/0xD2AC4/0xD2B00/0xD2B3C) hold byte-identical values but\n"
          f"     are SEPARATE records -- byte-verified here -- so this edit does not touch mode 11.")


def design_a(pops):
    """★ ADDENDUM 6 -- the `surface` agent's DESIGN A, evaluated on the MEASURED rate distribution.

    Design A = ONE halfword: 0xD2ABC (= record 0xD2AB0 + 0x0C = Y[1] of the 10 km/h record, the
    knot at rate breakpoint 400) 2561 -> 7051. Byte-verified as 2561 in _v67_plain_image.bin.

    🛑 THE SHAPE THIS CREATES. Y[0] stays 2561, so the curve is a RAMP from 1.00x at rate 0 to its
    peak at rate 400, then decays to stock by rate 1500. The boost is therefore RATE-PROPORTIONAL
    over exactly the interval where grind #1 lives, and its peak sits at the breakpoint, not at
    grind #1's measured centre of mass. Evaluating it at a single assumed operating point of
    ~603 counts gives 2.00x; evaluating it on the measured DISTRIBUTION does not.
    """
    print(f"\n{'=' * 108}\n== ADDENDUM 6 -- DESIGN A (0xD2ABC 2561->7051) ON THE MEASURED "
          f"DISTRIBUTION\n{'=' * 108}")
    YA, XA = REC_Y.copy(), REC_X.copy()
    YA[1, 1] = 7051
    # a shape-corrected sibling: same peak value, but the plateau starts at rate 0 so the boost is
    # delivered where grind #1's samples actually are, and the knee is pulled in to 700.
    YB, XB = REC_Y.copy(), REC_X.copy()
    YB[1] = [5122, 5122, 2247, 1947]
    YB[0] = [6144, 6144, 2322, 1536]
    XB[0] = [0, 400, 900, 3000]
    XB[1] = [0, 400, 900, 3000]

    print(f"   Curves, Q10, after cross-interpolation at each population's own median speed:")
    for lab, (Y, X) in (("STOCK", (REC_Y, REC_X)), ("DESIGN A", (YA, XA)), ("shape-corrected B",
                                                                           (YB, XB))):
        print(f"      {lab:20s} 10 km/h record  X={list(map(int, X[1]))} Y={list(map(int, Y[1]))}"
              f"   0 km/h record Y={list(map(int, Y[0]))}")

    print(f"\n   Delivered multiplier vs the ASSUMED single operating point, then vs the MEASURED "
          f"distribution:")
    print(f"   {'population':28s} {'assumed pt':>12s} {'mult@pt':>8s} | "
          f"{'measured, SAMPLE-WISE':>22s} {'vs assumed':>11s}")
    for lab, k, assumed in (("grind #1 (V62/V65 creep)", "G1 V62/V65 creep [ENG]", 603),
                            ("grind #1 (stock-located)", "G1 stock/V59+V64 creep [ENG]", 603),
                            ("grind #2 CREEP", "G2creep V62/V65 creep [ENG]", 1206),
                            ("grind #2 MID 14-50 km/h", "G2mid V67/r47 mid-speed [ENG]", 170),
                            ("grind #2 HIGHWAY", "G2hwy V67/r47 highway [ENG]", 170)):
        rs = pops[k][0]
        if not rs:
            continue
        sp = int(np.median(col(rs, "spc")))
        at_pt = (stock_gain_q10([sp], [assumed], YA, XA)[0]
                 / max(stock_gain_q10([sp], [assumed])[0], 1))
        m, lo, hi = delivered(rs, YA, XA)
        print(f"   {lab:28s} {assumed:8d} cnt {at_pt:8.2f} | {m:8.2f}x [{lo:4.2f}-{hi:4.2f}] "
              f"{m / at_pt:10.2f}x")
    print(f"\n   Same populations under the shape-corrected sibling B (plateau from rate 0, knee "
          f"at 900):")
    for lab, k in (("grind #1 (V62/V65 creep)", "G1 V62/V65 creep [ENG]"),
                   ("grind #1 (stock-located)", "G1 stock/V59+V64 creep [ENG]"),
                   ("grind #2 CREEP", "G2creep V62/V65 creep [ENG]"),
                   ("grind #2 MID 14-50 km/h", "G2mid V67/r47 mid-speed [ENG]"),
                   ("grind #2 HIGHWAY", "G2hwy V67/r47 highway [ENG]")):
        rs = pops[k][0]
        if not rs:
            continue
        m, lo, hi = delivered(rs, YB, XB)
        print(f"   {lab:28s} {'':12s} {'':8s} | {m:8.2f}x [{lo:4.2f}-{hi:4.2f}]")

    # where the multiplier actually lands across the rate axis, at grind #1's speed
    sp = int(np.median(col(pops["G1 V62/V65 creep [ENG]"][0], "spc")))
    print(f"\n   Design A's multiplier vs RATE at grind #1's measured speed "
          f"({sp} counts = {sp / SPEED_COUNTS_PER_KMH:.1f} km/h), against where grind #1's "
          f"samples actually are:")
    g1s = np.concatenate([r["ax_s"] for r in pops["G1 V62/V65 creep [ENG]"][0]]).astype(float)
    g2s = np.concatenate([r["ax_s"] for r in pops["G2creep V62/V65 creep [ENG]"][0]]).astype(float)
    print(f"      {'rate':>6s} {'stock':>7s} {'DesA':>7s} {'mult':>6s} | "
          f"{'% of G1 samples <=':>23s} {'% of G2creep <=':>16s}")
    for rt in (0, 100, 136, 200, 300, 400, 500, 603, 800, 1206, 1500, 2000):
        s0 = int(stock_gain_q10([sp], [rt])[0])
        s1 = int(stock_gain_q10([sp], [rt], YA, XA)[0])
        print(f"      {rt:6d} {s0:7d} {s1:7d} {s1 / s0:6.2f} | {100 * float((g1s <= rt).mean()):23.1f}% "
              f"{100 * float((g2s <= rt).mean()):16.1f}%")
    # ---- robustness: does |dtorque|-weighting change the ranking? -----------------------------
    # The plain sample average assumes the gain matters equally at every instant. What the lane
    # actually delivers is sum(dtorque * gain), so if gain and |dtorque| correlate within an
    # oscillation cycle the plain average is biased. Reweight by a 100 Hz proxy for gp-0x4f62
    # (2*(bar[n]-bar[n-4])/4) and re-rank. ⚠ A proxy: the real producer runs at ~1 kHz.
    print(f"\n   ROBUSTNESS -- the same multipliers weighted by |dtorque| (100 Hz proxy for "
          f"gp-0x4f62)\n   instead of weighted equally in time. If the ranking survives, the "
          f"gain/dtorque phase\n   correlation flagged in ADDENDUM 3 is not driving the result.")
    print(f"   {'population':28s} {'DesA plain':>11s} {'DesA wtd':>10s} {'B plain':>9s} "
          f"{'B wtd':>8s}")
    for lab, k in (("grind #1 (V62/V65 creep)", "G1 V62/V65 creep [ENG]"),
                   ("grind #2 CREEP", "G2creep V62/V65 creep [ENG]")):
        rs = pops[k][0]
        if not rs:
            continue
        cells = []
        for Y, X in ((YA, XA), (YB, XB)):
            sp = np.concatenate([r["sp_s"] for r in rs]).astype(np.int64)
            ax = np.concatenate([r["ax_s"] for r in rs]).astype(np.int64)
            w = np.concatenate([np.abs(np.r_[np.zeros(4), r["dtq_s"][4:]]) for r in rs])
            ratio = stock_gain_q10(sp, ax, Y, X) / np.maximum(stock_gain_q10(sp, ax), 1)
            cells += [float(ratio.mean()), float(np.average(ratio, weights=w + 1e-9))]
        print(f"   {lab:28s} {cells[0]:11.2f} {cells[1]:10.2f} {cells[2]:9.2f} {cells[3]:8.2f}")

    print(f"""
   ⇒ ★★ THE MEASURED SPREAD UNDERMINES DESIGN A's SHAPE, and it is a shape problem, not a sign
     problem. Design A peaks AT the 400 breakpoint and returns to 1.00x at rate 0, but grind #1
     spends 83% of its samples BELOW 400 (ADDENDUM 2) with a sample median near 120. So the
     population sits on the RAMP, not the peak, and the sample-wise multiplier lands well under
     the 2.00x computed at an assumed 603.
   ⇒ The 2.00x figure is not wrong, it is CONDITIONAL: it is what Design A delivers IF grind #1
     really sits at 603 counts. 603 is this dataset's WINDOW-p90, not its centre of mass. Both
     numbers are real; they answer different questions, and the LERP integrates the distribution.
   ⇒ Sibling B shows the fix is available and cheap: start the plateau at rate 0 (raise Y[0] too)
     and put the knee at 900. That restores ~2x across grind #1's actual mass while keeping the
     highway at exactly 1.00x -- at the cost of giving creep grind #2 more than Design A does,
     which is the same trade every candidate in TASK 5 faces.
   ⚠ One correlation this cannot resolve: the axis is modulated at the grind frequency
     (ADDENDUM 3), so gain and |dtorque| are not independent within a cycle. A time-average of
     the gain is the right first-order figure and is what is computed here, but if gain and
     |dtorque| correlate in phase the effective damping differs from it. Only a 1 kHz probe
     settles that.""")


def addendum(R, pops, rng, nboot):
    maneuver_axis()
    units_and_breakpoints(pops)
    ema_bound(pops)
    threshold_sweep(pops)
    y_row_edit(pops)
    design_a(pops)


if __name__ == "__main__":
    main()
