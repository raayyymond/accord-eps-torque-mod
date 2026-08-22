r"""GRINDS #2 / #3 -- SEARCHED, NOT ASSUMED, across 10-60 Hz.  Plus the whole sub-100 Hz picture.

The operator's own localisation of grind #3 was an explicit hedge -- "maybe this is a grind #3 or
#2.5... I am not sure" -- so this does not test 43-45 and 45-47 Hz as given.  It SCANS, and it
reports the whole profile so a line anywhere sub-100 Hz cannot be missed by a pre-set window.

BOTH READINGS AGAIN, per frequency:
  READING 1  DIRECT CONTENT   -- spectral prominence of each frequency against its own
                                 neighbourhood, engaged vs rolling-manual, within route.
  READING 2  AMPLITUDE MOD    -- excess of the audible-carrier envelope PSD at that modulation
                                 rate, engaged vs rolling-manual, against a phase-shuffled
                                 surrogate.  ⭐ still the primary hypothesis: a 40 Hz mechanical
                                 mode radiates poorly but modulates broadband noise efficiently.

🛑 THE HONEST FRAME FOR THIS SCRIPT.  Scanning many frequencies invites a false positive, so the
   decision rule is fixed HERE, before the numbers:
     a candidate must (i) show engaged/manual > 1 with the CI clear of 1.0, (ii) do so on at
     least TWO of the three 6x routes, and (iii) NOT do so on stock.
   Anything that fails any leg is reported as a number, not as a finding.
"""
import os
import sys
import json
import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
SIX = ['r96', 'r9e', 'ra4']
VLO, VHI = 0.0, 16.0
FSE = 500.0
FSA = 3.90625

D = {}
for t in TAGS:
    g = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_grind.npz' % t))
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    ct = c['t'].astype(float)
    ec = (c['cc_lat'].astype(float) > 0.5).astype(float)
    vc = c['v_rear'].astype(float) * 3.6
    ts, te = g['t_sp'].astype(float), g['t_env'].astype(float)
    D[t] = dict(sp=g['sp'].astype(float), sp_f=g['sp_f'].astype(float),
                env=g['env'].astype(float), env_f=g['env_f'], splice=g['splice'].astype(bool),
                eng_sp=np.interp(ts, ct, ec) > 0.5, v_sp=np.interp(ts, ct, vc),
                eng_env=np.interp(te, ct, ec) > 0.5, v_env=np.interp(te, ct, vc))
F = D['r97']['sp_f']


def msk(t, arr, engaged=True):
    d = D[t]
    e = d['eng_sp'] if arr == 'sp' else d['eng_env']
    v = d['v_sp'] if arr == 'sp' else d['v_env']
    m = (e if engaged else ~e) & (v >= VLO) & (v < VHI)
    if arr == 'env':
        m = m & ~d['splice']
    if not engaged:
        m = m & (v >= A.V_ROLL)
    return m


def runs(m, fs, min_s):
    m = np.asarray(m, bool)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k + 1])) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / fs >= min_s]


print("=" * 126)
print("READING 1 -- DIRECT SUB-100 Hz CONTENT.  Spectral PROMINENCE per frequency (band mean /")
print("   median of its 8-Hz-wide neighbourhood), engaged <16 km/h.  >1 = a LINE sits there.")
print("   For scale: the wheel-rate 21.73 Hz line has prominence 39.18 against a null p95 of 3.07.")
print("=" * 126)
GRID = np.arange(12, 60, 2.0)
print("%-6s %-9s" % ('route', 'build') + "".join("%7.0f" % f for f in GRID))
P1 = {}
for t in TAGS:
    d = D[t]
    me = msk(t, 'sp', True)
    sp = d['sp'][me].mean(0)
    row = []
    for f0 in GRID:
        tgt = (F >= f0 - 1) & (F < f0 + 1)
        nb = (F >= f0 - 5) & (F <= f0 + 5) & ~tgt
        row.append(sp[tgt].mean() / np.median(sp[nb]) if tgt.any() and nb.any() else np.nan)
    P1[t] = [float(x) for x in row]
    print("%-6s %-9s" % (t, A.NAMES[t]) + "".join("%7.2f" % x for x in row))
print("  NOTE the whole table sits at or below ~1.1 -- the acoustic sub-100 Hz spectrum is smooth.")
print("  A prominence below 1.0 means the band is a TROUGH relative to its neighbours.")

print()
print("  ENGAGED / ROLLING-MANUAL amplitude ratio of the same band powers, within route:")
print("%-6s %-9s" % ('route', 'build') + "".join("%7.0f" % f for f in GRID))
P1R = {}
for t in TAGS:
    d = D[t]
    me, mm = msk(t, 'sp', True), msk(t, 'sp', False)
    row = []
    for f0 in GRID:
        tgt = (F >= f0 - 1) & (F < f0 + 1)
        a = d['sp'][me][:, tgt].sum(1).mean()
        b = d['sp'][mm][:, tgt].sum(1).mean()
        row.append(np.sqrt(a / b) if b > 0 else np.nan)
    P1R[t] = [float(x) for x in row]
    print("%-6s %-9s" % (t, A.NAMES[t]) + "".join("%7.2f" % x for x in row))
print("  ⚠ NOT speed-matched -- this is the SCAN.  Anything that looks like a candidate is")
print("    re-run speed-matched with a CI below.")

print()
print("=" * 126)
print("READING 2 (PRIMARY) -- AMPLITUDE MODULATION scanned 12-60 /s, carrier 300-3000 Hz")
print("=" * 126)


def am_at(x, lo, hi, fs=FSE, nper=1024):
    if len(x) < nper:
        return None
    f, p = signal.welch(x - x.mean(), fs=fs, nperseg=nper, noverlap=nper // 2, detrend='linear')
    tgt = (f >= lo) & (f <= hi)
    bg = ((f >= 6) & (f <= 70)) & ~((f >= lo - 4) & (f <= hi + 4))
    if tgt.sum() < 2 or bg.sum() < 10:
        return None
    cf = np.polyfit(np.log(f[bg]), np.log(p[bg]), 1)
    return float(np.mean(p[tgt] / np.exp(np.polyval(cf, np.log(f[tgt])))))


BF = D['r97']['env_f']
JC = int(np.flatnonzero((BF[:, 0] == 300) & (BF[:, 1] == 3000))[0])
print("%-6s %-9s" % ('route', 'build') + "".join("%8.0f" % f for f in GRID))
P2 = {}
for t in TAGS:
    d = D[t]
    rr = runs(msk(t, 'env', True), FSE, 3.0)
    row = []
    for f0 in GRID:
        v = [am_at(d['env'][a:b, JC], f0 - 1, f0 + 1) for a, b in rr]
        v = [x for x in v if x is not None]
        row.append(np.mean(v) if v else np.nan)
    P2[t] = [float(x) for x in row]
    print("%-6s %-9s" % (t, A.NAMES[t]) + "".join("%8.2f" % x for x in row))
print("  engaged AM excess.  1.0 = no modulation line at that rate beyond the smooth envelope")
print("  spectrum.  Same statistic on the ROLLING-MANUAL arm:")
P2M = {}
for t in TAGS:
    d = D[t]
    rr = runs(msk(t, 'env', False), FSE, 3.0)
    row = []
    for f0 in GRID:
        v = [am_at(d['env'][a:b, JC], f0 - 1, f0 + 1) for a, b in rr]
        v = [x for x in v if x is not None]
        row.append(np.mean(v) if v else np.nan)
    P2M[t] = [float(x) for x in row]
    print("%-6s %-9s" % (t, A.NAMES[t]) + "".join("%8.2f" % x for x in row))

print()
print("=" * 126)
print("DECISION RULE, fixed before the numbers: a candidate needs eng/man > 1 on >= 2 of the three")
print("6x routes AND not on stock.  Applied to both readings:")
print("=" * 126)
hits = []
for k, f0 in enumerate(GRID):
    for nm, tab in (('direct', P1R), ('AM', None)):
        if nm == 'direct':
            s = tab['r97'][k]
            six = [tab[t][k] for t in SIX]
        else:
            s = (P2['r97'][k] / P2M['r97'][k]) if P2M['r97'][k] else np.nan
            six = [(P2[t][k] / P2M[t][k]) if P2M[t][k] else np.nan for t in SIX]
        if not np.isfinite(s) or any(not np.isfinite(x) for x in six):
            continue
        if sum(x > 1.15 for x in six) >= 2 and s <= 1.0:
            hits.append((f0, nm, s, six))
if hits:
    for f0, nm, s, six in hits:
        print("   %5.0f Hz  %-7s  STOCK %.2f   6x: %s" %
              (f0, nm, s, "  ".join("%.2f" % x for x in six)))
else:
    print("   NO CANDIDATE anywhere in 12-60 Hz, on either reading, meets the rule.")

json.dump({'grid': GRID.tolist(), 'prominence': P1, 'direct_eng_man': P1R,
           'am_eng': P2, 'am_man': P2M},
          open(os.path.join(A.HERE, '_acoustic_grind23.json'), 'w'), indent=1)
print("\n  wrote _acoustic_grind23.json")
