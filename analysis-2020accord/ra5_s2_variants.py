r"""S2 ("hard manual turns during LKAS engagement") -- FOUR DEFINITIONS, AND THE CLAMP CHECK.

Two things `ra5_three_grinds.py` left open, both of which can change the answer:

=================================================================================================
A.  S2 IS DEFINITION-SENSITIVE, AND MY FIRST DEFINITION MAY HAVE SAMPLED THE WRONG REGIME
=================================================================================================
S2a required `|rate_c| >= 40 deg/s`.  But the corpus's own strongest result says the 21-28 Hz mode
**peaks at 15-40 deg/s and COLLAPSES above 100** (V105 handoff sec 5.3, ~90x stock at 15-40 vs
stock-level above 100), and the operator's own *"applying torque kills the buzz"* was measured at
**16.12x [5.29, 41.29]**.  ⇒ **S2a may be sampling exactly the condition that SUPPRESSES the mode.**
"Hard manual turns" may mean large TORQUE, or large ANGLE (near lock), not necessarily large RATE.
🛑 One arbitrary threshold must not decide a taxonomy question.  Four definitions, all reported:
    S2a  |tq| >= 1000  AND  |rate_c| >= 40      (as pre-registered -- push AND fast)
    S2b  |tq| >= 1000                            (push, any rate)
    S2c  |tq| >=  500  AND  15 <= |rate_c| < 40  (real push, in the mode's OWN loudest rate band)
    S2d  |ang| >= 300 counts                     (near-lock, a geometric reading of "hard turn")
  all with `engaged & v < 20 km/h`.

=================================================================================================
B.  THE CLAMP CHECK -- MEASURED, NOT RECONSTRUCTED
=================================================================================================
V106 raises `gp-0x6b26` (an ACCELERATION term) whose lane clamps at +-511.  Hard manual turns mean
large angular acceleration, so it should clamp MORE in exactly S2 -- and a clamped damper delivers
no incremental damping.  **I do not have the confirmed cascade H(f) and will not fabricate one.**
Instead: `gp-0x6b26` was ITSELF ON THE 427 WIRE on **r77 / r78 (V90/V91, `sar 3`, counts = wire x
8/5)** and **r7d (V94, `sar 1`, counts = wire x 2/5)**.  So the clamp duty is DIRECTLY MEASURABLE
there, under the same S2-style masks, at the dose those builds carried.
⚠ Those builds' Y-table doses differ from V106's, so the transfer is a SCALING argument, stated as
such: if the observed |gp-0x6b26| is at fraction `p` of 511 under S2 at dose `d`, then dose `k*d`
puts the clamp-crossing where |gp-0x6b26| >= 511/k at the CURRENT dose.  That is computable from
the measured distribution with no model at all.
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
WIN_S, MERGE_S = 1.0, 0.25
NPER = int(round(WIN_S * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
TAGS = ('r97', 'r96', 'r9e', 'ra4', 'r95', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x',
         'r95': 'V101 8x', 'ra5': 'V105 NOTCH'}
OUT = {}


def close_gaps(m, g_s=MERGE_S):
    g = int(round(g_s * FS))
    mm = m.copy()
    idx = np.flatnonzero(np.diff(mm.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mm)]))
    for a, c in zip(b[:-1], b[1:]):
        if (not mm[a]) and a > 0 and c < len(mm) and (c - a) <= g:
            mm[a:c] = True
    return mm


def runs(m, minlen):
    mm = close_gaps(m)
    idx = np.flatnonzero(np.diff(mm.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mm)]))
    return [(int(a), int(c)) for a, c in zip(b[:-1], b[1:]) if mm[a] and (c - a) >= minlen]


def s2_mask(d, which):
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = np.asarray(d['v_rear'], float) * KPH
    rc = np.abs(np.asarray(d['rate_c'], float))
    tq = np.abs(np.asarray(d['tq'], float))
    an = np.abs(np.asarray(d['ang'], float)) if 'ang' in d.files else np.zeros_like(rc)
    base = e & (v < 20.0)
    if which == 'S2a':
        return base & (tq >= 1000) & (rc >= 40)
    if which == 'S2b':
        return base & (tq >= 1000)
    if which == 'S2c':
        return base & (tq >= 500) & (rc >= 15) & (rc < 40)
    if which == 'S2d':
        return base & (an >= 300)
    raise ValueError(which)


def spec(d, m):
    x = np.asarray(d['rate_f'], float)
    per = []
    for a, c in runs(m, NPER):
        seg = x[a:c]
        acc, nw = None, 0
        for s in range(0, len(seg) - NPER + 1, NPER // 2):
            xs = seg[s:s + NPER] - seg[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            p = (X.conj() * X).real / (FS * UU)
            acc = p if acc is None else acc + p
            nw += 1
        if nw:
            per.append((acc, nw))
    return per


def peak(S, lo, hi):
    k = np.flatnonzero((FB >= lo) & (FB <= hi))
    j = k[int(np.argmax(S[k]))]
    f0 = FB[j]
    sh = (((FB >= f0 - 6) & (FB <= f0 - 2)) | ((FB >= f0 + 2) & (FB <= f0 + 6))) \
        & (FB >= lo) & (FB <= hi)
    base = float(np.median(S[sh])) if sh.sum() > 3 else float(np.median(S[k]))
    return float(f0), float(S[j]), (float(S[j] / base) if base > 0 else np.inf)


print("=" * 124)
print("A.  S2 UNDER FOUR DEFINITIONS.  Peak searched 15-48 Hz (above the driver's own input band).")
print("    `ang` is the raw steering-angle count channel; 300 counts is a large-excursion proxy.")
print("=" * 124)
for w, desc in (('S2a', '|tq|>=1000 AND |rate|>=40   (pre-registered)'),
                ('S2b', '|tq|>=1000, any rate        (push)'),
                ('S2c', '|tq|>=500 AND 15<=|rate|<40 (push, in the mode\'s loudest rate band)'),
                ('S2d', '|ang|>=300 counts           (near-lock, geometric)')):
    print("\n  %s   engaged & v<20 km/h &  %s" % (w, desc))
    print("%12s %6s %5s %5s %10s %11s %11s %12s %12s"
          % ('build', 'sec', 'eps', 'win', 'PEAK Hz', 'peak PSD', 'PROM', 'RMS 18-26', 'RMS 38-48'))
    for t in TAGS:
        d = L.load(t)
        m = s2_mask(d, w)
        per = spec(d, m)
        if not per:
            print("%12s %6.1f %5d %5d   -- no windows --" % (NAMES[t], m.sum() / FS, 0, 0))
            continue
        S = sum(p[0] for p in per) / sum(p[1] for p in per)
        f0, pv, pr = peak(S, 15.0, 48.0)
        k1 = (FB >= 18) & (FB < 26)
        k2 = (FB >= 38) & (FB < 48)
        print("%12s %6.1f %5d %5d %10.2f %11.4f %11.1f %12.4f %12.4f"
              % (NAMES[t], m.sum() / FS, len(per), sum(p[1] for p in per), f0, pv, pr,
                 np.sqrt(S[k1].sum() * DF), np.sqrt(S[k2].sum() * DF)))
        OUT.setdefault('s2', {}).setdefault(w, {})[NAMES[t]] = dict(
            sec=float(m.sum() / FS), eps=len(per), win=int(sum(p[1] for p in per)),
            f0=f0, psd=pv, prom=pr,
            rms_18_26=float(np.sqrt(S[k1].sum() * DF)),
            rms_38_48=float(np.sqrt(S[k2].sum() * DF)))

# ============================================================ B. CLAMP CHECK
print()
print("=" * 124)
print("B.  🛑 THE CLAMP CHECK -- `gp-0x6b26` MEASURED ON THE WIRE, on the routes that carried it.")
print("    r77/r78 = V90/V91, packer `|b26|*5>>3`  =>  counts = wire * 8/5")
print("    r7d     = V94,     packer `|b26|*5>>1`  =>  counts = wire * 2/5")
print("    Lane clamp +-511 (`0xC407E`).  ⚠ On r7d the 10-bit WIRE saturates at |b26| = 409.2,")
print("       BELOW the lane clamp -- so r7d censors before the clamp and its tail is a LOWER")
print("       bound.  r77/r78 map the rail (511) to wire 319 and cannot saturate.")
print("=" * 124)
SCALE = {'r77': 8.0 / 5.0, 'r78': 8.0 / 5.0, 'r7d': 2.0 / 5.0}
print("%8s %10s %8s %8s %9s %9s %9s %9s %10s %10s"
      % ('route', 'mask', 'sec', 'n', '|b26| p50', 'p90', 'p99', 'MAX',
         'duty>=511', 'duty>=256'))
for tag in ('r77', 'r78', 'r7d'):
    try:
        d = L.load(tag)
    except Exception as ex:
        print("%8s  -- cache unavailable: %s" % (tag, ex))
        continue
    if 'ab_mt' not in d.files:
        print("%8s  -- no 427 lane in cache --" % tag)
        continue
    mt = np.asarray(d['ab_mt'], float)
    abt = np.asarray(d['ab_t1ab'], float)
    t = np.asarray(d['t'], float)
    j = np.clip(np.searchsorted(abt, t, side='right') - 1, 0, len(mt) - 1)
    b26 = mt[j] * SCALE[tag]
    e = np.asarray(d['cc_lat'], float) > 0.5
    # older caches (r77/r78/r7d) predate `v_rear`; fall back to the same quantity by its
    # other names, and say which was used.
    if 'v_rear' in d.files:
        v = np.asarray(d['v_rear'], float) * KPH
        vsrc = 'v_rear*3.6'
    elif 'ws_rl' in d.files and 'ws_rr' in d.files:
        v = 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float)) * KPH
        vsrc = '0.5(ws_rl+ws_rr)*3.6'
    else:
        v = np.asarray(d['cs_v'], float) * KPH
        vsrc = 'cs_v*3.6'
    print("           speed channel: %s   (median %.2f km/h)" % (vsrc, np.nanmedian(v)))
    rc = np.abs(np.asarray(d['rate_c'], float))
    tq = np.abs(np.asarray(d['tq'], float))
    for lbl, m in (('ALL engaged', e),
                   ('S1-like', e & (v < 10) & (rc >= 5) & (rc < 40)),
                   ('S2a-like', e & (v < 20) & (tq >= 1000) & (rc >= 40)),
                   ('S2c-like', e & (v < 20) & (tq >= 500) & (rc >= 15) & (rc < 40)),
                   ('S3-like', e & (v >= 60))):
        if m.sum() < 50:
            print("%8s %10s %8.1f %8d   -- too few frames --" % (tag, lbl, m.sum() / FS, m.sum()))
            continue
        x = b26[m]
        print("%8s %10s %8.1f %8d %9.1f %9.1f %9.1f %9.1f %10.6f %10.6f"
              % (tag, lbl, m.sum() / FS, m.sum(),
                 np.percentile(x, 50), np.percentile(x, 90), np.percentile(x, 99), x.max(),
                 float(np.mean(x >= 511)), float(np.mean(x >= 256))))
        OUT.setdefault('clamp', {}).setdefault(tag, {})[lbl] = dict(
            sec=float(m.sum() / FS), n=int(m.sum()),
            p50=float(np.percentile(x, 50)), p90=float(np.percentile(x, 90)),
            p99=float(np.percentile(x, 99)), mx=float(x.max()),
            duty511=float(np.mean(x >= 511)), duty256=float(np.mean(x >= 256)))
print()
print("  ⭐ HOW TO READ IT WITHOUT A MODEL: `duty>=256` is the fraction of frames that a **x2.0**")
print("     dose would push to the +-511 rail, and `duty>=511` is the fraction already railed at")
print("     the dose that route carried.  A x3.0-stock build sits between them if the route's own")
print("     dose was x1.5-stock.  **If duty>=256 is large under an S2-like mask, V106's extra")
print("     damping does not arrive in exactly the scenario it is aimed at.**")

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '_ra5_s2_variants.json'), 'w'), indent=1, default=float)
print("\nwrote _ra5_s2_variants.json")
