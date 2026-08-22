r"""V105 / route `a5` -- THE RELOCATION TEST, AND THE 6-9 Hz BLAST-RADIUS CHECK.

🛑 DISCLOSURE, BECAUSE IT CHANGES HOW THIS IS READ: the orchestrator specified the three-outcome
test AFTER I had already computed 18-33 Hz peak frequencies with CIs (`ra5_pole_moved.py`, reported
2026-08-22).  **This file is therefore a CONFIRMATION AND EXTENSION of a result already in hand, NOT
a blind pre-registration.**  What is genuinely new here: the exact 18-30 Hz band as specified, the
FULL 1x/4x/6x/8x ladder, total band power (not just the 21-28 window), the |H|-at-each-build's-own-
peak statistic, and the 6-9 Hz check.

=================================================================================================
THE HYPOTHESIS UNDER TEST -- describing-function relocation
=================================================================================================
STATE.md: the mode is SELF-EXCITED (`f0` = 21.90 / 23.61 / 24.90 Hz at 1x / 4x / 6x -- the
frequency MOVES WITH LOOP GAIN, which a driven response cannot do).  For a limit cycle, a notch at
the current centre does not kill the oscillation; the describing-function intersection slides to
the nearest frequency where the loop still crosses.  V105's own response leaves the door open:
    |H_V105|  =  0.5423 @ 20.5 Hz · 0.4150 @ 21.73 · 0.3070 @ 22.7 · 2.09e-6 @ 25.5 · 0.1229 @ 26.8

THE THREE OUTCOMES, AS THE ORCHESTRATOR WROTE THEM:
  (A) peak MOVED DOWN to ~21-22 Hz, band power roughly conserved  => RELOCATION, limit cycle,
      notching structurally futile.
  (B) peak STAYED at ~25-26 Hz and band power DROPPED             => the notch bit.
  (C) peak STAYED and band power did NOT drop                     => the notch is not in the loop
      that carries the mode (wrong location) -- check the coefficients are in force.

⭐ THE STATISTIC THAT DISCRIMINATES THEM WITHOUT ARGUING ABOUT BAND EDGES:
   **`|H_V105|` evaluated at each build's OWN measured peak.**  If the mode relocates to where the
   notch costs it less, that number RISES from V104 to V105.  If the notch simply attenuated a
   stationary mode, it does not.

=================================================================================================
SECOND TEST -- 6-9 Hz BLAST RADIUS
=================================================================================================
`|H_V105|(7.79 Hz)` = 0.98628 vs `|H_V104|(7.79 Hz)` = 1.81845, i.e. the LANE at 7.79 Hz changes by
0.5425x -- NOT 1.4 %.  ⚠ The orchestrator's "1.4 %" is V105 against UNITY, not against V104.  The
correct statement is that V105 REMOVES V104's 1.85x lane boost at 6-9 Hz (a reversion toward
stock's 0.9829), so 6-9 Hz is NOT protected by construction and this test is real, not a formality.
"""
import os
import sys
import json
import struct
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
BAND = (18.0, 30.0)                     # the orchestrator's band, exactly
TAGS = ('r97', 'r85', 'r96', 'r9e', 'ra4', 'r95', 'ra5')
NAMES = {'r97': 'STOCK 1x', 'r85': 'V100 4x', 'r96': 'V102 6x', 'r9e': 'V103 6x',
         'ra4': 'V104 6x', 'r95': 'V101 8x', 'ra5': 'V105 6x+NOTCH'}
FW = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
OUT = {}


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
    d, rs = run_slices(tag, vlo, vhi)
    x = d[chan].astype(float)
    per = []
    for a, b in rs:
        seg = x[a:b]
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


def pool(per):
    return None if not per else sum(p[0] for p in per) / sum(p[1] for p in per)


def bandRMS(S, lo, hi):
    k = (FB >= lo) & (FB < hi)
    return float(np.sqrt(S[k].sum() * DF))


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
                rms_ci=[float(np.percentile(pw, 2.5)), float(np.percentile(pw, 97.5))])


# ================================================================= 1. the ladder
print("=" * 122)
print("1.  THE RELOCATION TEST -- PEAK of the %g-%g Hz band, FULL LADDER, with CIs." % BAND)
print("    ⭐ Last column is `|H_V105|` at THAT build's own peak: the frequency-relocation")
print("       discriminator.  A limit cycle sliding out of the notch makes it RISE.")
print("=" * 122)
LAD = {}
for scope, vlo, vhi in (('engaged < 16 km/h  (the operator\'s grinding window)', 0.0, 16.0),
                        ('engaged 40-95 km/h  (highway)', 40.0, 95.0),
                        ('engaged 55-70 km/h  (SPEED-MATCHED highway)', 55.0, 70.0)):
    print("\n  %s" % scope)
    print("%14s %5s %9s %20s %11s %11s %20s %12s"
          % ('build', 'eps', 'peak Hz', 'peak 95 % CI', 'peak PSD',
             '%g-%g RMS' % BAND, 'RMS 95 % CI', '|H_V105| @pk'))
    for t in TAGS:
        per = welch_per_ep(t, vlo, vhi)
        if len(per) < 3:
            print("%14s %5d   -- fewer than 3 episodes --" % (NAMES[t], len(per)))
            continue
        r = peak_boot(per, *BAND)
        r['H105_at_peak'] = float(Hmag(r['peak'], C105))
        r['H104_at_peak'] = float(Hmag(r['peak'], C104))
        r['eps'] = len(per)
        LAD[(scope, t)] = (r, per)
        print("%14s %5d %9.2f %20s %11.3f %11.4f %20s %12.4f"
              % (NAMES[t], len(per), r['peak'], "[%.2f, %.2f]" % tuple(r['peak_ci']),
                 r['psd'], r['rms'], "[%.3f, %.3f]" % tuple(r['rms_ci']), r['H105_at_peak']))
    OUT.setdefault('ladder', {})[scope] = {NAMES[t]: LAD[(scope, t)][0]
                                           for t in TAGS if (scope, t) in LAD}

# paired V105/V104 band-power ratio with a joint episode bootstrap
print()
print("  V105 / V104, %g-%g Hz band RMS, episode bootstrap:" % BAND)
for scope, _, _ in (('engaged < 16 km/h  (the operator\'s grinding window)', 0, 0),
                    ('engaged 40-95 km/h  (highway)', 0, 0),
                    ('engaged 55-70 km/h  (SPEED-MATCHED highway)', 0, 0)):
    if (scope, 'ra5') not in LAD or (scope, 'ra4') not in LAD:
        continue
    P5, P4 = LAD[(scope, 'ra5')][1], LAD[(scope, 'ra4')][1]
    rg = np.random.default_rng(113)
    vals, dpk = [], []
    k = (FB >= BAND[0]) & (FB <= BAND[1])
    ff = FB[k]
    for _ in range(4000):
        o, pk = [], []
        for P in (P5, P4):
            pick = rg.integers(0, len(P), len(P))
            S = sum(P[j][0] for j in pick) / sum(P[j][1] for j in pick)
            o.append(bandRMS(S, *BAND))
            pk.append(ff[int(np.argmax(S[k]))])
        vals.append(o[0] / o[1])
        dpk.append(pk[0] - pk[1])
    q = np.percentile(vals, [2.5, 97.5])
    qd = np.percentile(dpk, [2.5, 97.5])
    print("     %-52s RMS ratio %.3f [%.3f, %.3f]   peak SHIFT %+.2f Hz [%+.2f, %+.2f]"
          % (scope, np.median(vals), q[0], q[1], np.median(dpk), qd[0], qd[1]))
    OUT.setdefault('v105_v104', {})[scope] = dict(
        rms_ratio=float(np.median(vals)), rms_ci=[float(q[0]), float(q[1])],
        peak_shift=float(np.median(dpk)), shift_ci=[float(qd[0]), float(qd[1])])

# ================================================================= 2. where the power IS
print()
print("=" * 122)
print("2.  WHERE THE BAND'S POWER ACTUALLY SITS -- sub-band decomposition of %g-%g Hz." % BAND)
print("    This is the number that says whether a 25.5 Hz notch could ever have mattered.")
print("=" * 122)
SUB = [(18, 21), (21, 23), (23, 24.5), (24.5, 26.5), (26.5, 28), (28, 30)]
for scope in [s for s in OUT.get('ladder', {})]:
    print("\n  %s" % scope)
    print("%14s" % 'build' + "".join("%12s" % ("%g-%g" % b) for b in SUB)
          + "%14s" % 'frac in notch')
    for t in TAGS:
        if (scope, t) not in LAD:
            continue
        S = pool(LAD[(scope, t)][1])
        tot = sum(bandRMS(S, *b) ** 2 for b in SUB)
        row = "".join("%12.4f" % bandRMS(S, *b) for b in SUB)
        fr = bandRMS(S, 24.5, 26.5) ** 2 / tot if tot > 0 else np.nan
        print("%14s%s%14.4f" % (NAMES[t], row, fr))
        OUT.setdefault('subband', {}).setdefault(scope, {})[NAMES[t]] = dict(
            rms={("%g-%g" % b): bandRMS(S, *b) for b in SUB}, frac_in_notch=float(fr))
print("  'frac in notch' = share of %g-%g Hz POWER inside the notch's own -20 dB region" % BAND)
print("  (24.5-26.5 Hz).  🛑 A notch can only remove what is inside its stopband.")

# ================================================================= 3. |H| stamped on the data
print()
print("=" * 122)
print("3.  IS THE NOTCH'S OWN SHAPE STAMPED ON THE MEASURED SPECTRUM?")
print("    Test: the measured V105/V104 AMPLITUDE ratio against the two images' own |H5|/|H4|.")
print("    If the lane dominated the wheel spectrum, they would coincide.")
print("=" * 122)
for scope in ('engaged < 16 km/h  (the operator\'s grinding window)',
              'engaged 55-70 km/h  (SPEED-MATCHED highway)'):
    if (scope, 'ra5') not in LAD:
        continue
    S5, S4 = pool(LAD[(scope, 'ra5')][1]), pool(LAD[(scope, 'ra4')][1])
    k = (FB >= 19.0) & (FB <= 30.0)
    ff = FB[k]
    meas = np.sqrt(S5[k] / S4[k])
    pred = Hmag(ff, C105) / Hmag(ff, C104)
    print("\n  %s" % scope)
    print("%8s %12s %12s %12s" % ('Hz', 'measured', 'predicted', 'meas/pred'))
    for i in range(len(ff)):
        star = ''
        if abs(ff[i] - 25.5) < 0.2:
            star = '   <- 25.5 Hz, the notch centre'
        print("%8.2f %12.4f %12.4f %12.4f%s" % (ff[i], meas[i], pred[i],
                                                meas[i] / pred[i], star))
    # is there a LOCAL MINIMUM of the measured ratio within +-1 Hz of 25.5?
    w = (ff >= 24.5) & (ff <= 26.5)
    jmin = int(np.argmin(meas))
    print("  measured ratio: global min at %.2f Hz (%.4f);  min inside 24.5-26.5 = %.4f at %.2f Hz"
          % (ff[jmin], meas[jmin], meas[w].min(), ff[w][int(np.argmin(meas[w]))]))
    print("  predicted ratio min: %.6f at %.2f Hz" % (pred.min(), ff[int(np.argmin(pred))]))
    OUT.setdefault('shape_stamp', {})[scope] = dict(
        meas_min_hz=float(ff[jmin]), meas_min=float(meas[jmin]),
        meas_min_in_core=float(meas[w].min()),
        meas_min_in_core_hz=float(ff[w][int(np.argmin(meas[w]))]),
        pred_min_hz=float(ff[int(np.argmin(pred))]))

# ================================================================= 4. 6-9 Hz blast radius
print()
print("=" * 122)
print("4.  THE 6-9 Hz RATCHET-BAND BLAST-RADIUS CHECK.")
print("    🛑 |H_V104|(7.79) = %.5f  ->  |H_V105|(7.79) = %.5f  =  **%.4fx**, NOT 1.4 %%."
      % (Hmag(7.79, C104), Hmag(7.79, C105), Hmag(7.79, C105) / Hmag(7.79, C104)))
print("    V105 REVERTS V104's 1.85x lane boost at 6-9 Hz.  The band is NOT protected by")
print("    construction, so a move here is EXPECTED, not a blast-radius surprise.")
print("=" * 122)
for scope, vlo, vhi in (('engaged < 16 km/h', 0.0, 16.0),
                        ('engaged 40-95 km/h', 40.0, 95.0)):
    print("\n  %s" % scope)
    print("%14s %5s %12s %22s %12s" % ('build', 'eps', '6-9 Hz RMS', '95 % CI', 'x STOCK'))
    P = {}
    base = None
    for t in TAGS:
        per = welch_per_ep(t, vlo, vhi)
        if len(per) < 3:
            continue
        S = pool(per)
        rg = np.random.default_rng(127)
        bs = []
        for _ in range(2000):
            pick = rg.integers(0, len(per), len(per))
            bs.append(bandRMS(sum(per[j][0] for j in pick) / sum(per[j][1] for j in pick), 6, 9))
        q = np.percentile(bs, [2.5, 97.5])
        v = bandRMS(S, 6, 9)
        P[t] = per
        if t == 'r97':
            base = v
        print("%14s %5d %12.4f %22s %12s"
              % (NAMES[t], len(per), v, "[%.4f, %.4f]" % (q[0], q[1]),
                 '-' if base is None else "%.2fx" % (v / base)))
        OUT.setdefault('band69', {}).setdefault(scope, {})[NAMES[t]] = dict(
            rms=v, ci=[float(q[0]), float(q[1])], eps=len(per))
    if 'ra5' in P and 'ra4' in P:
        rg = np.random.default_rng(131)
        vals = []
        for _ in range(4000):
            o = []
            for Q in (P['ra5'], P['ra4']):
                pick = rg.integers(0, len(Q), len(Q))
                o.append(bandRMS(sum(Q[j][0] for j in pick) / sum(Q[j][1] for j in pick), 6, 9))
            vals.append(o[0] / o[1])
        q = np.percentile(vals, [2.5, 97.5])
        # within-drive random-split null on the same statistic
        nulls = {}
        for t in ('ra4', 'ra5'):
            Q = P[t]
            if len(Q) < 6:
                continue
            rr = []
            rg2 = np.random.default_rng(137)
            for _ in range(2000):
                idx = rg2.permutation(len(Q))
                h = len(Q) // 2
                A = sum(Q[j][0] for j in idx[:h]) / sum(Q[j][1] for j in idx[:h])
                B = sum(Q[j][0] for j in idx[h:]) / sum(Q[j][1] for j in idx[h:])
                rr.append(bandRMS(A, 6, 9) / bandRMS(B, 6, 9))
            nulls[t] = [float(x) for x in np.percentile(rr, [2.5, 97.5])]
        print("     ⇒ V105/V104 6-9 Hz = **%.3f**  [%.3f, %.3f]  (episode boot)"
              % (np.median(vals), q[0], q[1]))
        for t, n in nulls.items():
            print("       within-drive random-split null, %-12s [%.3f, %.3f]  =>  measured is %s"
                  % (NAMES[t], n[0], n[1],
                     "INSIDE (unchanged)" if n[0] <= np.median(vals) <= n[1] else "OUTSIDE"))
        OUT.setdefault('band69_ratio', {})[scope] = dict(
            point=float(np.median(vals)), ci=[float(q[0]), float(q[1])], nulls=nulls)

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '_ra5_relocation.json'), 'w'), indent=1, default=float)
print("\nwrote _ra5_relocation.json")
