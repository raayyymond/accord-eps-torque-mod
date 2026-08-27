r"""ROUTE `a6` == V106 -- THE "HIGHER PITCH" STATISTIC, THE PROMINENCE CIs, AND Q8 HOUSEKEEPING.

=================================================================================================
WHY A CENTROID AND NOT AN ARGMAX
=================================================================================================
The operator: *"the fundamental frequency has NOTABLY INCREASED in frequency (audible tone is
HIGHER PITCH and MORE QUIET)."*

`studies/ra6/ra6_peak.py` measured the 18-30 Hz ARGMAX and it went **DOWN** at low speed (22.73 -> 17.98) and
essentially nowhere at highway (26.97 -> 27.22).  That looks like a contradiction, and it is not:
`studies/ra6/ra6_peak.py` section 4 shows the 30-45 / 18-30 energy SHARE **rose in all four regimes**.  The
18-30 Hz mode was attenuated far more than the 30-45 Hz content, so the **spectral BALANCE moved
up** even though no individual line moved up.  A centroid measures balance; an argmax cannot.

⭐ THE STATISTIC: `centroid = sum(f * S(f)) / sum(S(f))` over **15-45 Hz**, engaged, per regime.
   It is a frequency, so like the peak location it is immune to the level noise that kills every
   band-power ratio on this corpus -- and unlike an argmax it does not jump between modes.

🛑 THE CEILING, STATED WHEREVER THIS IS QUOTED: `0x18F` samples at 101.15 Hz => **Nyquist
   50.57 Hz.  Nothing above ~50 Hz is observable in the CAN corpus at all.**  If the residual he
   now hears is genuinely above 50 Hz, this instrument is structurally blind to it and the
   centroid result is a LOWER bound on the shift, not a measurement of the tone he hears.

Usage:  python studies/ra6/ra6_pitch.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
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
CB = (15.0, 45.0)
TAGS = ('r97', 'ra4', 'ra5', 'ra6')
NAMES = {'r97': 'STOCK 1x', 'ra4': 'V104 6x', 'ra5': 'V105 NOTCH', 'ra6': 'V106 6b26x3'}
REGIMES = [('low  < 16 km/h', 0.0, 16.0), ('mid  16-40 km/h', 16.0, 40.0),
           ('hwy  40-95 km/h', 40.0, 95.0), ('hwy-mat 55-70 km/h', 55.0, 70.0)]
OUT = {}


def per_ep(tag, vlo, vhi, minlen_s=4.2):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = e & (v >= vlo) & (v < vhi)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    x = d['rate_f'].astype(float)
    out = []
    for a, c in zip(b[:-1], b[1:]):
        if not (m[a] and (c - a) >= int(minlen_s * FS)):
            continue
        seg = x[a:c]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            out.append((acc, nw))
    return out


def pool(per):
    return sum(p[0] for p in per) / sum(p[1] for p in per)


def centroid(S, lo=CB[0], hi=CB[1]):
    k = (FB >= lo) & (FB <= hi)
    return float((FB[k] * S[k]).sum() / S[k].sum())


def prominence(S, lo=15.0, hi=35.0):
    """Prominence of the strongest local maximum against its own +-3 Hz median background --
    a WITHIN-SPECTRUM, level-invariant statistic.  Returns (freq, prominence)."""
    k = np.flatnonzero((FB >= lo) & (FB <= hi))
    best = (np.nan, 0.0)
    for j in k:
        w = (FB >= FB[j] - 1.0) & (FB <= FB[j] + 1.0)
        if S[j] != S[w].max():
            continue
        bg = np.median(S[(FB >= FB[j] - 3) & (FB <= FB[j] + 3)])
        pr = float(S[j] / bg) if bg > 0 else np.nan
        if np.isfinite(pr) and pr > best[1]:
            best = (float(FB[j]), pr)
    return best


print("=" * 124)
print("1.  ⭐⭐ THE SPECTRAL CENTROID, %g-%g Hz -- THE 'PITCH' STATISTIC." % CB)
print("    A frequency, so it inherits the peak location's immunity to level noise.")
print("    The last two columns are the 30-45/18-30 energy SHARE and the strongest LINE's")
print("    PROMINENCE -- the two quantities that say whether a MODE still exists at all.")
print("=" * 124)
NULL = {}
for lbl, vlo, vhi in REGIMES:
    print("\n  %s" % lbl)
    print("%14s %5s %12s %22s %14s %10s %12s"
          % ('build', 'eps', 'centroid Hz', 'centroid 95 % CI', 'hi/lo share',
             'line Hz', 'PROMINENCE'))
    P = {}
    for t in TAGS:
        per = per_ep(t, vlo, vhi)
        if len(per) < 3:
            print("%14s %5d   -- fewer than 3 episodes --" % (NAMES[t], len(per)))
            continue
        P[t] = per
        S = pool(per)
        rg = np.random.default_rng(606)
        bc, bp = [], []
        for _ in range(3000):
            pick = rg.integers(0, len(per), len(per))
            Sb = sum(per[j][0] for j in pick) / sum(per[j][1] for j in pick)
            bc.append(centroid(Sb))
            bp.append(prominence(Sb)[1])
        q = np.percentile(bc, [2.5, 97.5])
        klo = (FB >= 18) & (FB <= 30)
        khi = (FB >= 30) & (FB <= 45)
        share = float(S[khi].sum() / S[klo].sum())
        f0, pr = prominence(S)
        qp = np.percentile(bp, [2.5, 97.5])
        print("%14s %5d %12.2f %22s %14.4f %10.2f %12s"
              % (NAMES[t], len(per), centroid(S), "[%.2f, %.2f]" % (q[0], q[1]),
                 share, f0, "%.1f [%.1f,%.1f]" % (pr, qp[0], qp[1])))
        OUT.setdefault('centroid', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            eps=len(per), centroid=centroid(S), ci=[float(q[0]), float(q[1])],
            hi_lo_share=share, line_hz=f0, prominence=float(pr),
            prom_ci=[float(qp[0]), float(qp[1])])
    # within-drive null on the centroid SHIFT, from route a6 itself
    if 'ra6' in P and len(P['ra6']) >= 6:
        per = P['ra6']
        rg = np.random.default_rng(707)
        nn = []
        for _ in range(2000):
            pm = rg.permutation(len(per))
            h = len(per) // 2
            A = sum(per[j][0] for j in pm[:h]) / sum(per[j][1] for j in pm[:h])
            B = sum(per[j][0] for j in pm[h:]) / sum(per[j][1] for j in pm[h:])
            nn.append(centroid(A) - centroid(B))
        NULL[lbl] = [float(x) for x in np.percentile(nn, [2.5, 97.5])]
        for other in ('ra5', 'ra4'):
            if other not in P:
                continue
            rg2 = np.random.default_rng(808)
            dd = []
            for _ in range(3000):
                a_ = centroid(pool([P['ra6'][j] for j in
                                    rg2.integers(0, len(P['ra6']), len(P['ra6']))]))
                b_ = centroid(pool([P[other][j] for j in
                                    rg2.integers(0, len(P[other]), len(P[other]))]))
                dd.append(a_ - b_)
            q = np.percentile(dd, [2.5, 97.5])
            med = float(np.median(dd))
            cl = not (NULL[lbl][0] <= med <= NULL[lbl][1])
            print("     centroid SHIFT a6 - %-11s %+7.2f Hz [%+.2f, %+.2f]   a6 null "
                  "[%+.2f, %+.2f]  =>  %s"
                  % (NAMES[other], med, q[0], q[1], NULL[lbl][0], NULL[lbl][1],
                     "CLEARS" if cl else "inside null"))
            OUT.setdefault('centroid_shift', {}).setdefault(lbl, {})['a6-%s' % other] = dict(
                shift=med, ci=[float(q[0]), float(q[1])], null=NULL[lbl], clears=bool(cl))

# ================================================================== Q8
print()
print("=" * 124)
print("2.  Q8 -- HOUSEKEEPING.  Cave rungs, faults, exposure, speed census.")
print("=" * 124)
d6 = L.load('ra6')
e6 = np.asarray(d6['cc_lat'], float) > 0.5
v6 = np.asarray(d6['v_rear'], float) * KPH
n = len(e6)
print("  frames %d   duration %.1f s   ENGAGED %.1f s (%.2f %%)   MANUAL %.1f s"
      % (n, n / FS, e6.sum() / FS, 100 * e6.mean(), (~e6).sum() / FS))
idx = np.flatnonzero(np.diff(e6.astype(np.int8)) != 0) + 1
b = np.concatenate(([0], idx, [len(e6)]))
runs = [(int(a), int(c)) for a, c in zip(b[:-1], b[1:]) if e6[a]]
ln = np.array([(c - a) / FS for a, c in runs])
print("  engagement runs: %d total;  >=2.5 s: %d;  >=10 s: %d;  >=60 s: %d;  longest %.1f s"
      % (len(ln), (ln >= 2.5).sum(), (ln >= 10).sum(), (ln >= 60).sum(), ln.max()))
low = e6 & (v6 < 16)
lidx = np.flatnonzero(np.diff(low.astype(np.int8)) != 0) + 1
lb = np.concatenate(([0], lidx, [len(low)]))
lrun = np.array([(c - a) / FS for a, c in zip(lb[:-1], lb[1:]) if low[a]])
print("  ENGAGED <16 km/h: %.1f s in %d runs;  >=4.2 s: %d;  >=8.2 s: %d   "
      "(a5 gave 87.0 s / 20 runs / 6 / 2)"
      % (low.sum() / FS, len(lrun), (lrun >= 4.2).sum(), (lrun >= 8.2).sum()))
print("\n  speed histogram (engaged / manual seconds):")
VE = [0, 5, 8, 16, 25, 40, 60, 80, 100, 1e9]
for i in range(len(VE) - 1):
    me = e6 & (v6 >= VE[i]) & (v6 < VE[i + 1])
    mm = (~e6) & (v6 >= VE[i]) & (v6 < VE[i + 1])
    print("    %6.0f-%-6.0f km/h   engaged %8.1f s   manual %8.1f s"
          % (VE[i], min(VE[i + 1], 999), me.sum() / FS, mm.sum() / FS))
    OUT.setdefault('speed_hist', {})["%g-%g" % (VE[i], min(VE[i + 1], 999))] = dict(
        engaged_s=float(me.sum() / FS), manual_s=float(mm.sum() / FS))
print("\n  cave rung duties (pooled / engaged / manual):")
for k, nm in (('v106_b7', 'b7 sign gp-0x6b4c'), ('v106_b6', 'b6 governor clip'),
              ('v106_b5', 'b5 friction>=inertia'), ('v106_b4', 'b4 sign r24'),
              ('v106_b3', 'b3 sign D-state')):
    x = np.asarray(d6[k], float)
    print("    %-24s %.4f / %.4f / %.4f" % (nm, x.mean(), x[e6].mean(), x[~e6].mean()))
    OUT.setdefault('rungs', {})[nm] = dict(pooled=float(x.mean()), engaged=float(x[e6].mean()),
                                           manual=float(x[~e6].mean()))
print("\n  FAULT CENSUS:")
print("    0x7FFF sentinels 0x14A/0x18F : %d / %d"
      % (int(np.asarray(d6['sentinels'])[0]) if 'sentinels' in d6.files else -1,
         int(np.asarray(d6['sentinels'])[1]) if 'sentinels' in d6.files else -1))
su, sc = np.unique(np.asarray(d6['sstat'], int), return_counts=True)
print("    STEER_STATUS histogram        : %s"
      % "  ".join("%d:%d" % (a, c) for a, c in zip(su, sc)))
print("    DTC bit2 duty                 : %.6f  (%d transitions)"
      % (float(np.asarray(d6['ab_dtc_bit2'], float).mean()),
         int((np.diff(np.asarray(d6['ab_dtc_bit2'], int)) != 0).sum())))
print("    CONFIG_VALID duty             : %.6f"
      % float(np.asarray(d6['ab_config_valid'], float).mean()))
print("    OUTPUT_DISABLED duty          : %.6f"
      % float(np.asarray(d6['ab_output_disabled'], float).mean()))
OUT['faults'] = dict(
    steer_status={int(a): int(c) for a, c in zip(su, sc)},
    dtc_bit2=float(np.asarray(d6['ab_dtc_bit2'], float).mean()),
    config_valid=float(np.asarray(d6['ab_config_valid'], float).mean()),
    output_disabled=float(np.asarray(d6['ab_output_disabled'], float).mean()))
OUT['exposure'] = dict(frames=int(n), sec=float(n / FS), engaged_s=float(e6.sum() / FS),
                       manual_s=float((~e6).sum() / FS), runs=int(len(ln)),
                       runs_ge_2p5=int((ln >= 2.5).sum()), longest_s=float(ln.max()),
                       low_speed_engaged_s=float(low.sum() / FS),
                       low_runs=int(len(lrun)), low_runs_ge_4p2=int((lrun >= 4.2).sum()))

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_pitch.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_pitch.json")
