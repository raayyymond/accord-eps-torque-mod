r"""ROUTE `a6` == V106 -- Q3: THE PEAK LOCATION, THE FULL PSD SHAPE, AND THE SPEED CENSUS.

THE OPERATOR SAYS THE PITCH WENT **UP** AND THE LOUDNESS **DOWN**.  Peak LOCATION is a WITHIN-DRIVE
quantity and is one of the few statistics that survived the `a5` session, so it leads.

=================================================================================================
METHOD -- FROZEN, IDENTICAL TO `studies/sessions/ra5/ra5_relocation.py` SO THE LADDER IS COMPARABLE
=================================================================================================
`rate_f` (0x18F motor-rate channel, fs = 101.148 Hz), 4 s Hann, 50 % overlap, Welch-summed INSIDE
engaged episodes only (`cc_lat > 0.5`), episodes >= 4.2 s, **bootstrap over EPISODES**.

🛑 CONTROLS RUN BEFORE THE MEASUREMENT, per `feedback-run-the-control-before-the-measurement`:
  (a) a WITHIN-DRIVE split-half-by-episode null on every band ratio quoted;
  (b) a 32-45 Hz PLACEBO band;
  (c) a PER-WINDOW SPEED CENSUS beside every averaged spectrum
      (`accord-averaged-spectrum-needs-matched-speed-distributions`);
  (d) the argmax is reported with the FULL PSD SHAPE, never alone -- a bare argmax cannot tell a
      unimodal peak from a bimodal one, and `a5`'s residual looked bimodal (open item #3).

🛑 CROSS-DRIVE BAND-POWER RATIOS ARE **NOT-CURRENTLY-DECIDABLE** on this corpus (`a5`'s own
   split-half null spans 0.26-3.8).  They are printed ONLY beside their null and are labelled.
   **Peak LOCATION is not a band-power ratio and does not inherit that limit.**

Usage:  python studies/ra6/ra6_peak.py
"""
import os
import sys
import json
import struct
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
BAND = (18.0, 30.0)
HIBAND = (30.0, 45.0)
PLACEBO = (32.0, 45.0)
TAGS = ('r97', 'ra4', 'ra5', 'ra6')
NAMES = {'r97': 'STOCK 1x', 'r85': 'V100 4x', 'r96': 'V102 6x', 'r9e': 'V103 6x',
         'ra4': 'V104 6x', 'r95': 'V101 8x', 'ra5': 'V105 NOTCH', 'ra6': 'V106 6b26x3'}
FW = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
OUT = {}

# The operator's own scenarios, as speed regimes.  "5 mph" = 8.05 km/h.
REGIMES = [('micro   < 8 km/h  (his "5 mph")', 0.0, 8.0),
           ('low     < 16 km/h (grind #1 window)', 0.0, 16.0),
           ('mid     16-40 km/h', 16.0, 40.0),
           ('hwy     40-95 km/h', 40.0, 95.0),
           ('hwy-mat 55-70 km/h (SPEED-MATCHED)', 55.0, 70.0)]


def coeffs(name):
    b = (FW / name).read_bytes()
    return [struct.unpack("<f", b[o:o + 4])[0] for o in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]


C104 = coeffs("_v104_V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4_plain_image.bin")
C105 = coeffs("_v105_V104BASE-NOTCH25.5HZ.C60A8-C60B4-PROBE.B6.6B94.GE.4F64_plain_image.bin")


def Hmag(f, c):
    a1, a2, b1, c4 = c
    z = np.exp(-2j * np.pi * np.asarray(f, float) / 1000.0)
    return np.abs(c4 * (1 + b1 * z + z * z) / (1 + a1 * z + a2 * z * z))


def run_slices(tag, vlo, vhi, minlen_s=4.2):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = e & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    ml = int(minlen_s * FS)
    return d, [(int(a), int(c)) for a, c in zip(b[:-1], b[1:]) if m[a] and (c - a) >= ml]


def welch_per_ep(tag, vlo, vhi, chan='rate_f'):
    """Per-episode (summed periodogram, n_windows, per-window speeds) -- the census travels
    WITH the spectrum so it can never be quoted without it."""
    d, rs = run_slices(tag, vlo, vhi)
    x = d[chan].astype(float)
    v = d['v_rear'].astype(float) * KPH
    per = []
    for a, b in rs:
        seg, vseg = x[a:b], v[a:b]
        acc, nw, sp = None, 0, []
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
            sp.append(float(np.mean(vseg[s:s + NPER])))
        if nw:
            per.append((acc, nw, np.array(sp)))
    return per


def pool(per):
    return None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)


def bandRMS(S, lo, hi):
    k = (FB >= lo) & (FB < hi)
    return float(np.sqrt(S[k].sum() * DF))


def census(per):
    if not per:
        return {}
    sp = np.concatenate([p[2] for p in per])
    return dict(nwin=int(len(sp)), sec=float(sum(p[1] for p in per) * (NPER / 2) / FS),
                v_p10=float(np.percentile(sp, 10)), v_p50=float(np.percentile(sp, 50)),
                v_p90=float(np.percentile(sp, 90)), v_mean=float(sp.mean()))


def peak_boot(per, lo, hi, nb=4000, seed=101):
    k = (FB >= lo) & (FB <= hi)
    ff = FB[k]
    rg = np.random.default_rng(seed)
    pk, pw = [], []
    for _ in range(nb):
        pick = rg.integers(0, len(per), len(per))
        S = sum(per[j][0] for j in pick) / sum(per[j][1] for j in pick)
        pk.append(ff[int(np.argmax(S[k]))])
        pw.append(bandRMS(S, lo, hi))
    S0 = pool(per)
    return dict(peak=float(ff[int(np.argmax(S0[k]))]),
                peak_ci=[float(np.percentile(pk, 2.5)), float(np.percentile(pk, 97.5))],
                psd=float(S0[k].max()), rms=bandRMS(S0, lo, hi),
                rms_ci=[float(np.percentile(pw, 2.5)), float(np.percentile(pw, 97.5))],
                eps=len(per))


def split_half_null(per, lo, hi, nb=2000, seed=137):
    """WITHIN-DRIVE resolution floor for a band-RMS ratio, AND for the peak location."""
    if len(per) < 6:
        return None
    rg = np.random.default_rng(seed)
    k = (FB >= lo) & (FB <= hi)
    ff = FB[k]
    rr, dpk = [], []
    for _ in range(nb):
        idx = rg.permutation(len(per))
        h = len(per) // 2
        A = sum(per[j][0] for j in idx[:h]) / sum(per[j][1] for j in idx[:h])
        B = sum(per[j][0] for j in idx[h:]) / sum(per[j][1] for j in idx[h:])
        rr.append(bandRMS(A, lo, hi) / bandRMS(B, lo, hi))
        dpk.append(ff[int(np.argmax(A[k]))] - ff[int(np.argmax(B[k]))])
    return dict(rms_null=[float(np.percentile(rr, 2.5)), float(np.percentile(rr, 97.5))],
                peak_null=[float(np.percentile(dpk, 2.5)), float(np.percentile(dpk, 97.5))])


# ============================================================== 0.  CONTROL FIRST
print("=" * 124)
print("0.  🛑 THE CONTROL, RUN BEFORE THE MEASUREMENT -- the WITHIN-DRIVE split-half-by-episode")
print("    null on route a6 itself, for both the band RMS and the PEAK LOCATION.")
print("    Nothing below may be called a result unless it clears the row for its own regime.")
print("=" * 124)
print("%38s %6s %26s %26s" % ('regime', 'eps', '18-30 RMS null (a6)', 'peak-shift null Hz (a6)'))
NULLS = {}
for lbl, vlo, vhi in REGIMES:
    per = welch_per_ep('ra6', vlo, vhi)
    n = split_half_null(per, *BAND)
    NULLS[lbl] = n
    if n is None:
        print("%38s %6d   -- fewer than 6 episodes, NO NULL AVAILABLE --" % (lbl, len(per)))
        continue
    print("%38s %6d %26s %26s"
          % (lbl, len(per), "[%.3f, %.3f]" % tuple(n['rms_null']),
             "[%+.2f, %+.2f]" % tuple(n['peak_null'])))
OUT['nulls_a6'] = NULLS

# ============================================================== 1.  THE LADDER
print()
print("=" * 124)
print("1.  PEAK LOCATION, %g-%g Hz, PER SPEED REGIME.  ⭐ THE HEADLINE." % BAND)
print("    Last column is `|H_V105|` at THAT build's own peak (the a5 relocation discriminator),")
print("    carried so the V106 row is directly readable against the V105 result.")
print("=" * 124)
LAD = {}
for lbl, vlo, vhi in REGIMES:
    print("\n  %s" % lbl)
    print("%14s %5s %9s %20s %11s %11s %20s %11s   %s"
          % ('build', 'eps', 'peak Hz', 'peak 95 % CI', 'peak PSD', '18-30 RMS',
             'RMS 95 % CI', '|H105|@pk', 'speed census p10/p50/p90, s engaged'))
    for t in TAGS:
        per = welch_per_ep(t, vlo, vhi)
        if len(per) < 3:
            print("%14s %5d   -- fewer than 3 episodes --" % (NAMES[t], len(per)))
            continue
        r = peak_boot(per, *BAND)
        r['H105_at_peak'] = float(Hmag(r['peak'], C105))
        r['census'] = census(per)
        LAD[(lbl, t)] = (r, per)
        c = r['census']
        print("%14s %5d %9.2f %20s %11.3f %11.4f %20s %11.4f   %5.1f/%5.1f/%5.1f  %7.1f s"
              % (NAMES[t], len(per), r['peak'], "[%.2f, %.2f]" % tuple(r['peak_ci']),
                 r['psd'], r['rms'], "[%.3f, %.3f]" % tuple(r['rms_ci']), r['H105_at_peak'],
                 c['v_p10'], c['v_p50'], c['v_p90'], c['sec']))
    OUT.setdefault('ladder', {})[lbl] = {NAMES[t]: LAD[(lbl, t)][0]
                                         for t in TAGS if (lbl, t) in LAD}

# ============================================================== 2.  PAIRED SHIFT
print()
print("=" * 124)
print("2.  THE PAIRED PEAK SHIFT, a6 vs a5 and a6 vs a4, joint episode bootstrap.")
print("    ⚠ The RMS ratio column is CROSS-DRIVE and is printed BESIDE its within-drive null.")
print("=" * 124)
print("%38s %14s %26s %24s %24s"
      % ('regime', 'pair', 'peak SHIFT Hz [95 % CI]', 'RMS ratio [95 % CI]', 'a6 within-drive null'))
for lbl, _, _ in REGIMES:
    for other in ('ra5', 'ra4'):
        if (lbl, 'ra6') not in LAD or (lbl, other) not in LAD:
            continue
        P6, PO = LAD[(lbl, 'ra6')][1], LAD[(lbl, other)][1]
        rg = np.random.default_rng(113)
        vals, dpk = [], []
        k = (FB >= BAND[0]) & (FB <= BAND[1])
        ff = FB[k]
        for _ in range(4000):
            o, pk = [], []
            for P in (P6, PO):
                pick = rg.integers(0, len(P), len(P))
                S = sum(P[j][0] for j in pick) / sum(P[j][1] for j in pick)
                o.append(bandRMS(S, *BAND))
                pk.append(ff[int(np.argmax(S[k]))])
            vals.append(o[0] / o[1])
            dpk.append(pk[0] - pk[1])
        q = np.percentile(vals, [2.5, 97.5])
        qd = np.percentile(dpk, [2.5, 97.5])
        nl = NULLS.get(lbl)
        print("%38s %14s %26s %24s %24s"
              % (lbl, 'a6/%s' % other,
                 "%+.2f [%+.2f, %+.2f]" % (np.median(dpk), qd[0], qd[1]),
                 "%.3f [%.3f, %.3f]" % (np.median(vals), q[0], q[1]),
                 "[%.3f, %.3f]" % tuple(nl['rms_null']) if nl else "n/a"))
        OUT.setdefault('paired', {}).setdefault(lbl, {})['a6/%s' % other] = dict(
            peak_shift=float(np.median(dpk)), shift_ci=[float(qd[0]), float(qd[1])],
            rms_ratio=float(np.median(vals)), rms_ci=[float(q[0]), float(q[1])],
            a6_null=nl['rms_null'] if nl else None,
            rms_clears_null=bool(nl and not (nl['rms_null'][0] <= np.median(vals)
                                             <= nl['rms_null'][1])),
            peak_clears_null=bool(nl and not (nl['peak_null'][0] <= np.median(dpk)
                                              <= nl['peak_null'][1])))

# ============================================================== 3.  THE FULL SHAPE
print()
print("=" * 124)
print("3.  🛑 THE FULL PSD SHAPE 5-45 Hz -- because an argmax cannot tell unimodal from bimodal.")
print("    Values are PSD in the pooled episode-average, 0.247 Hz bins, decimated to 0.5 Hz for")
print("    printing.  ⭐ Look for TWO local maxima: `a5`'s residual looked bimodal (open item #3).")
print("=" * 124)
GRID = np.arange(5.0, 45.01, 0.5)
for lbl, vlo, vhi in REGIMES:
    have = [t for t in TAGS if (lbl, t) in LAD]
    if not have:
        continue
    print("\n  %s" % lbl)
    print("%7s" % 'Hz' + "".join("%14s" % NAMES[t] for t in have))
    Sd = {}
    for t in have:
        S = pool(LAD[(lbl, t)][1])
        Sd[t] = np.array([S[np.argmin(np.abs(FB - g))] for g in GRID])
    for i, g in enumerate(GRID):
        print("%7.1f" % g + "".join("%14.4f" % Sd[t][i] for t in have))
    # local maxima inside 15-35 Hz on the native grid
    print("  local maxima 15-35 Hz (native 0.247 Hz grid, prominence vs 1 Hz neighbourhood):")
    for t in have:
        S = pool(LAD[(lbl, t)][1])
        k = np.flatnonzero((FB >= 15) & (FB <= 35))
        pk = []
        for j in k:
            w = (FB >= FB[j] - 1.0) & (FB <= FB[j] + 1.0)
            if S[j] == S[w].max() and S[j] > 0:
                base = np.median(S[(FB >= FB[j] - 3) & (FB <= FB[j] + 3)])
                pk.append((float(FB[j]), float(S[j]), float(S[j] / base) if base > 0 else np.nan))
        pk.sort(key=lambda r: -r[1])
        print("    %-14s " % NAMES[t] + "  ".join("%.2f Hz (PSD %.3f, prom %.1f)" % p
                                                  for p in pk[:4]))
        OUT.setdefault('shape', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            grid_hz=[float(g) for g in GRID], psd=[float(x) for x in Sd[t]],
            local_maxima=[list(p) for p in pk[:6]])

# ============================================================== 4.  DID IT LEAVE 18-30?
print()
print("=" * 124)
print("4.  DID THE MODE LEAVE 18-30 Hz OUT THE TOP?  Peak searched %g-%g Hz and the 18-30 vs"
      % HIBAND)
print("    30-45 SPLIT, per regime.  Also the %g-%g Hz PLACEBO." % PLACEBO)
print("=" * 124)
print("%38s %14s %10s %10s %10s %10s %12s"
      % ('regime', 'build', 'pk 30-45', 'pk 18-30', 'RMS 18-30', 'RMS 30-45', 'hi/lo share'))
for lbl, _, _ in REGIMES:
    for t in TAGS:
        if (lbl, t) not in LAD:
            continue
        per = LAD[(lbl, t)][1]
        S = pool(per)
        khi = (FB >= HIBAND[0]) & (FB <= HIBAND[1])
        klo = (FB >= BAND[0]) & (FB <= BAND[1])
        pkhi = float(FB[khi][int(np.argmax(S[khi]))])
        pklo = float(FB[klo][int(np.argmax(S[klo]))])
        rlo, rhi = bandRMS(S, *BAND), bandRMS(S, *HIBAND)
        print("%38s %14s %10.2f %10.2f %10.4f %10.4f %12.4f"
              % (lbl, NAMES[t], pkhi, pklo, rlo, rhi, (rhi / rlo) ** 2 if rlo > 0 else np.nan))
        OUT.setdefault('hiband', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            peak_30_45=pkhi, peak_18_30=pklo, rms_18_30=rlo, rms_30_45=rhi,
            rms_placebo=bandRMS(S, *PLACEBO))

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                 'analysis-2020accord', '_scratch/out/_ra6_peak.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_peak.json")
