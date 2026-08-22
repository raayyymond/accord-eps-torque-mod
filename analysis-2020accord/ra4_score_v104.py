"""SCORE ROUTE a4 (V104) AGAINST THE PRE-REGISTRATION WRITTEN BEFORE THE DATA EXISTED.

PRE-REGISTRATION, frozen and sent to the orchestrator before this cache was built:
  PRIMARY   6-9 Hz band RMS of `rate_f`, ENGAGED, 0-40 km/h, 4 s Hann / 50 % overlap /
            detrended, EPISODE bootstrap.
            Reference: the STOCK->6x contrast at the same speeds, 2.03x [1.42, 3.22].
            A V104 that works removes the ratchet's gain excess  =>  a4/r97 ~ 1.0.
            FAIL = a4/r97 at or above V102's 2.03x.
  CONTROLS FIRST, before the primary is quoted:
            (i)  split-half null inside a4 itself
            (ii) placebo band 26-40 Hz (c4's own model gives ~0.99 there)
            (iii) matched speed / |tq| census against r96 / r97
            (iv) the manual arm in the same speed band
  DOSE      within-drive engaged vs manual median |gp-0x6b86|, binned by |tq| AND SPEED.
            🛑 SPEED IS PART OF THE BINNING -- the assist map is speed-scheduled (near-origin
            slope 0.125 at parking vs 0.0625 at 50 km/h), and route a4's manual arm is 74 %
            PARKED, so a |tq|-only bin would compute 1.85 x 0.5 ~ 0.93 and report an arm
            failure on a perfectly delivered dose.
  SECONDARY 22-26 Hz level; clipping of the delivered lane.
  🛑 0x1AB ships at 49.83 Hz => Nyquist 24.9 Hz.  NO band above 25 Hz is scored on 427.
    All band statistics use `rate_f` (0x18F, native 100.88 Hz).

🛑 ra4 has NO x6b94 / x6b4c key by construction; `x6b86_mag` is UNSIGNED (the cave is
   byte-identical to V103, so byte4 b7 is gp-0x6b4c's sign, not this cell's).
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402
import check_427_alias as CA                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
U = (WIN ** 2).sum()
FB = [(2, 4), (4, 6), (6, 9), (9, 13), (13, 18), (18, 22), (22, 26), (26, 40)]
PRIMARY = (6, 9)
PLACEBO = (26, 40)

assert 'ra4' in CA.OTHER_CELL_ROUTES, "the alias guard does not know route ra4"
try:
    CA.assert_is_sum('ra4')
    raise SystemExit("GUARD FAILED: assert_is_sum('ra4') should have raised")
except AssertionError:
    pass
print("check_427_alias: ra4 correctly refused as a sum route; key = %s\n"
      % CA.OTHER_CELL_ROUTES['ra4'])


def arm(tag):
    d = L.load(tag)
    return dict(d=d, eng=d['cc_lat'] > 0.5, v=d['v_rear'].astype(float) * KPH,
                rate=d['rate_f'].astype(float), tq=np.abs(d['tq'].astype(float)))


A = {t: arm(t) for t in ('ra4', 'r9e', 'r96', 'r97')}


def ep_spec(tag, mask):
    """Per-EPISODE summed auto-spectra of rate_f.

    🛑 FIXED: segments on runs of `mask` ITSELF, not on runs of `eng`.  The first cut required
    `mask[a0]` at the ENGAGEMENT boundary, so an episode that began below 40 km/h was dropped
    whole even when it spent minutes in 40-80 -- which silently emptied every MID and HIGH row
    on route a4.  Caught by the empty table, not by an assertion."""
    R = A[tag]
    rate = R['rate']
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mask)]))
    tt = np.arange(NPER)
    M = np.vstack([tt, np.ones(NPER)]).T
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if (b0 - a0) < NPER or not mask[a0]:
            continue

        S, nw = None, 0
        for s in range(a0, b0 - NPER + 1, NPER // 2):
            if not mask[s:s + NPER].all():
                continue
            xs = rate[s:s + NPER]
            if not np.all(np.isfinite(xs)):
                continue
            xs = xs - M @ np.linalg.lstsq(M, xs, rcond=None)[0]
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (L.FS * U)
            S = p if S is None else S + p
            nw += 1
        if nw:
            out.append((S, nw))
    return out


def rms(sp, lo, hi):
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    return float(np.sqrt(sum(s[0] for s in sp)[sel].sum() / sum(s[1] for s in sp)
                         * (f[1] - f[0])))


def mask_of(tag, engaged=True, vlo=-1e9, vhi=1e9):
    R = A[tag]
    m = R['eng'] if engaged else ~R['eng']
    return m & (R['v'] >= vlo) & (R['v'] < vhi)


def boot_ratio(t_num, t_den, mask_num, mask_den, lo, hi, nboot=4000, seed=13):
    a_, b_ = ep_spec(t_den, mask_den), ep_spec(t_num, mask_num)
    if len(a_) < 2 or len(b_) < 2:
        return None
    rng = np.random.default_rng(seed)
    pt = rms(b_, lo, hi) / rms(a_, lo, hi)
    dr = np.array([rms([b_[j] for j in rng.integers(0, len(b_), len(b_))], lo, hi)
                   / rms([a_[j] for j in rng.integers(0, len(a_), len(a_))], lo, hi)
                   for _ in range(nboot)])
    return pt, np.percentile(dr, 2.5), np.percentile(dr, 97.5), len(b_), len(a_)


# ================================================================= CONTROLS
print("=" * 116)
print("CONTROL (i) -- SPLIT-HALF NULL INSIDE ROUTE a4 ITSELF (interleaved episodes). THE FLOOR.")
print("=" * 116)
VBS = [('LOW  0-40 km/h', 0.0, 40.0), ('MID  40-80 km/h', 40.0, 80.0),
       ('HIGH 80-130 km/h', 80.0, 130.0), ('ALL engaged', -1e9, 1e9)]
print("%20s %7s %8s" % ('speed band', 'eps', 'sec') + "".join("%11s" % ("%g-%g" % b) for b in FB))
for nm, lo_, hi_ in VBS:
    m = mask_of('ra4', True, lo_, hi_)
    sp = ep_spec('ra4', m)
    if len(sp) < 4:
        print("%20s %7d  (too few episodes for a split-half)" % (nm, len(sp)))
        continue
    row = [rms(sp[0::2], a_, b_) / rms(sp[1::2], a_, b_) for a_, b_ in FB]
    print("%20s %7d %8.1f" % (nm, len(sp), m.sum() / L.FS)
          + "".join("%11.2f" % r for r in row))
print("  ⇒ any between-build ratio must exceed this spread in the SAME band to mean anything.")

print()
print("=" * 116)
print("CONTROL (iii) -- EXPOSURE CENSUS, the four routes, ENGAGED")
print("=" * 116)
print("%6s %10s %10s %10s %10s %10s %10s %10s" %
      ('route', 'eng s', '0-40 s', '40-80 s', '80+ s', 'v p50', '|tq| p50', '|rate| p50'))
for t in ('ra4', 'r9e', 'r96', 'r97'):
    R = A[t]
    e = R['eng']
    print("%6s %10.1f %10.1f %10.1f %10.1f %10.1f %10.0f %10.2f"
          % (t, e.sum() / L.FS,
             mask_of(t, True, 0, 40).sum() / L.FS, mask_of(t, True, 40, 80).sum() / L.FS,
             mask_of(t, True, 80, 130).sum() / L.FS,
             np.median(R['v'][e]), np.median(R['tq'][e]), np.median(np.abs(R['rate'])[e])))

print()
print("=" * 116)
print("CONTROL (ii)+(iv) -- PLACEBO BAND 26-40 Hz, and the MANUAL arm, same comparisons")
print("=" * 116)
for lbl, lo_, hi_ in (('LOW 0-40 km/h', 0.0, 40.0),):
    for nm, band in (('PLACEBO 26-40', PLACEBO), ('PRIMARY  6-9 ', PRIMARY)):
        r = boot_ratio('ra4', 'r97', mask_of('ra4', True, lo_, hi_),
                       mask_of('r97', True, lo_, hi_), *band)
        if r:
            print("  %s  %s  a4/STOCK = %.3f  [%.3f, %.3f]  (eps %d vs %d)"
                  % (lbl, nm, r[0], r[1], r[2], r[3], r[4]))
    for nm, band in (('PLACEBO 26-40', PLACEBO), ('PRIMARY  6-9 ', PRIMARY)):
        r = boot_ratio('ra4', 'r97', mask_of('ra4', False, lo_, hi_),
                       mask_of('r97', False, lo_, hi_), *band)
        if r:
            print("  %s  %s  MANUAL a4/STOCK = %.3f  [%.3f, %.3f]  (eps %d vs %d)"
                  % (lbl, nm, r[0], r[1], r[2], r[3], r[4]))

# ================================================================= PRIMARY
print()
print("=" * 116)
print("*** PRIMARY ENDPOINT *** 6-9 Hz, ENGAGED, 0-40 km/h.  PRE-REGISTERED BEFORE THE DATA.")
print("=" * 116)
print("  Reference: the STOCK->6x contrast measured on r97 vs r96 at these speeds = 2.03")
print("  [1.42, 3.22].  A WORKING V104 removes the gain's ratchet excess  =>  a4/r97 ~ 1.0.")
print("  FAIL = a4/r97 at or above 2.03.")
print()
print("%34s %10s %22s %12s" % ('comparison', 'ratio', '95 % CI', 'episodes'))
for num, den, lbl in (('ra4', 'r97', 'V104 / STOCK 1x   *** PRIMARY ***'),
                      ('r96', 'r97', 'V102 6x / STOCK   (the reference)'),
                      ('r9e', 'r97', 'V103 6x / STOCK'),
                      ('ra4', 'r96', 'V104 / V102 6x'),
                      ('ra4', 'r9e', 'V104 / V103 6x')):
    r = boot_ratio(num, den, mask_of(num, True, 0, 40), mask_of(den, True, 0, 40), *PRIMARY)
    if r:
        print("%34s %10.3f   [%8.3f, %8.3f] %12s"
              % (lbl, r[0], r[1], r[2], "%d vs %d" % (r[3], r[4])))

# ================================================================= full band table
print()
print("=" * 116)
print("FULL BAND TABLE -- engaged band RMS of rate_f (deg/s), by speed.  a4 beside the others.")
print("=" * 116)
for nm, lo_, hi_ in VBS[:3]:
    print("  %s" % nm)
    print("%10s %8s" % ('route', 'sec') + "".join("%11s" % ("%g-%g" % b) for b in FB))
    for t in ('r97', 'r96', 'r9e', 'ra4'):
        m = mask_of(t, True, lo_, hi_)
        sp = ep_spec(t, m)
        if not sp:
            continue
        print("%10s %8.1f" % (t, m.sum() / L.FS)
              + "".join("%11.4f" % rms(sp, a_, b_) for a_, b_ in FB))
    print()

# ================================================================= DOSE
print("=" * 116)
print("DOSE DELIVERED -- within-drive, |gp-0x6b86| engaged vs manual, binned by |tq| AND SPEED")
print("=" * 116)
R = A['ra4']
x = np.asarray(L.load('ra4')['x6b86_mag'], float)
TQB = [(0, 50), (50, 100), (100, 200), (200, 400), (400, 800), (800, 1600)]
print("  ⚠ NAIVE (|tq| only, speed IGNORED) -- the version the pre-registration literally says,")
print("    shown to size the artifact.  a4's manual arm is 74 %% parked.")
print("%14s %10s %10s %10s %10s" % ('|tq| bin', 'n eng', 'n man', 'med eng', 'ratio'))
for lo_, hi_ in TQB:
    me = R['eng'] & (R['tq'] >= lo_) & (R['tq'] < hi_)
    mm = (~R['eng']) & (R['tq'] >= lo_) & (R['tq'] < hi_)
    if me.sum() < 200 or mm.sum() < 200:
        continue
    print("%7d-%-6d %10d %10d %10.1f %10.3f"
          % (lo_, hi_, me.sum(), mm.sum(), np.median(x[me]),
             np.median(x[me]) / max(np.median(x[mm]), 1e-9)))
print()
print("  ✅ SPEED-MATCHED (5-20 km/h, the only band with both arms: eng 126.3 s, man 50.0 s)")
print("%14s %10s %10s %10s %10s %10s" %
      ('|tq| bin', 'n eng', 'n man', 'med eng', 'med man', 'ratio'))
rat = []
for lo_, hi_ in TQB:
    sel = (R['v'] >= 5.0) & (R['v'] < 20.0) & (R['tq'] >= lo_) & (R['tq'] < hi_)
    me, mm = sel & R['eng'], sel & (~R['eng'])
    if me.sum() < 100 or mm.sum() < 100:
        continue
    a_, b_ = np.median(x[me]), np.median(x[mm])
    rat.append(a_ / max(b_, 1e-9))
    print("%7d-%-6d %10d %10d %10.1f %10.1f %10.3f"
          % (lo_, hi_, me.sum(), mm.sum(), a_, b_, rat[-1]))
if rat:
    print("  ⇒ speed-matched pooled ratio (median over |tq| bins) = %.3f" % np.median(rat))
print("  PREDICTED 1.66 (pedestal ~22 %%) to 1.85 (pedestal negligible).  ~1.00 => NOT IN FORCE.")

# ================================================================= clipping
print()
print("=" * 116)
print("CLIPPING -- the delivered lane against its own ceilings")
print("=" * 116)
e = R['eng']
print("  |gp-0x6b86| ENGAGED: p50 %.1f  p95 %.1f  p99 %.1f  p99.9 %.1f  MAX %.1f counts"
      % (np.percentile(x[e], 50), np.percentile(x[e], 95), np.percentile(x[e], 99),
         np.percentile(x[e], 99.9), x[e].max()))
for nm, ceil in (('friction-hold clamp +-12288', 12288.0),
                 ('427 field saturation (3273.6)', 3273.6),
                 ('map ceiling x k (5274 x 1.85 = 9757)', 9757.0)):
    print("     vs %-38s : max/ceiling = %.4f  (%s)"
          % (nm, x[e].max() / ceil, "CLEAR" if x[e].max() < ceil else "*** REACHED ***"))
print("  ⇒ duty at the 427 field rail: %.6f   at 90 %% of the +-12288 clamp: %.6f"
      % ((np.asarray(L.load('ra4')['mag427'], float) >= 1023).mean(), (x >= 0.9 * 12288).mean()))


# ================================================================= same-gain controls
print()
print("=" * 116)
print("CONTROL (ii-bis) -- THE PLACEBO ON A SAME-GAIN PAIR.  a4/r97 mixes c4 WITH the 6x gain,")
print("  so its placebo is meaningless.  V104 vs V103 differ ONLY by c4 + Lever B.")
print("=" * 116)
print("%28s %10s %22s %12s" % ('band', 'V104/V103', '95 % CI', 'episodes'))
for lo_, hi_ in FB:
    r = boot_ratio('ra4', 'r9e', mask_of('ra4', True, 0, 40), mask_of('r9e', True, 0, 40),
                   lo_, hi_)
    if r:
        tagn = ''
        if (lo_, hi_) == PRIMARY:
            tagn = '  <- PRIMARY (c4)'
        elif (lo_, hi_) == (18, 22):
            tagn = '  <- Lever B'
        elif (lo_, hi_) == PLACEBO:
            tagn = '  <- PLACEBO'
        print("%24.0f-%-3.0f %10.3f   [%8.3f, %8.3f] %12s%s"
              % (lo_, hi_, r[0], r[1], r[2], "%d vs %d" % (r[3], r[4]), tagn))

print()
print("=" * 116)
print("THE HIGHWAY ARM -- newly measurable (a4 has 138.6 s engaged >=80 km/h; r9e had 54.5 s)")
print("=" * 116)
for nm, lo_, hi_ in (('MID  40-80 km/h', 40.0, 80.0), ('HIGH 80-130 km/h', 80.0, 130.0)):
    print("  %s" % nm)
    print("%28s %10s %22s %12s" % ('band', 'V104/V103', '95 % CI', 'episodes'))
    for lo2, hi2 in FB:
        r = boot_ratio('ra4', 'r9e', mask_of('ra4', True, lo_, hi_),
                       mask_of('r9e', True, lo_, hi_), lo2, hi2)
        if r:
            print("%24.0f-%-3.0f %10.3f   [%8.3f, %8.3f] %12s"
                  % (lo2, hi2, r[0], r[1], r[2], "%d vs %d" % (r[3], r[4])))
    print("%28s %10s %22s %12s" % ('band', 'V104/STOCK', '95 % CI', 'episodes'))
    for lo2, hi2 in FB:
        r = boot_ratio('ra4', 'r97', mask_of('ra4', True, lo_, hi_),
                       mask_of('r97', True, lo_, hi_), lo2, hi2)
        if r:
            print("%24.0f-%-3.0f %10.3f   [%8.3f, %8.3f] %12s"
                  % (lo2, hi2, r[0], r[1], r[2], "%d vs %d" % (r[3], r[4])))
    print()

print("=" * 116)
print("SPLIT-HALF FLOOR at MID and HIGH, now that the segmentation bug is fixed")
print("=" * 116)
print("%20s %7s %8s" % ('speed band', 'runs', 'sec') + "".join("%11s" % ("%g-%g" % b) for b in FB))
for nm, lo_, hi_ in (('LOW  0-40 km/h', 0.0, 40.0), ('MID  40-80 km/h', 40.0, 80.0),
                     ('HIGH 80-130 km/h', 80.0, 130.0)):
    m = mask_of('ra4', True, lo_, hi_)
    sp = ep_spec('ra4', m)
    if len(sp) < 4:
        print("%20s %7d  (too few runs)" % (nm, len(sp)))
        continue
    print("%20s %7d %8.1f" % (nm, len(sp), m.sum() / L.FS)
          + "".join("%11.2f" % (rms(sp[0::2], a_, b_) / rms(sp[1::2], a_, b_)) for a_, b_ in FB))
