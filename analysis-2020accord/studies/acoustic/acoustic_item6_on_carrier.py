r"""ITEM 6 ON ITS ACTUAL CARRIER -- is the 6-12 /s ratchet a modulation of the 21-28 Hz MODE?

THE ARGUMENT FOR RUNNING THIS AND NOT STOPPING AT THE ACOUSTIC NULL.
The operator's words are "a RATCHET on top of a higher frequency vibration", 6-12 per second, and
"the vibration comes in and out ... the ratchet shows up on top of it when it's happening".

Two things are now established that make this the right pairing:
  * The "higher frequency vibration" has a name and a ladder.  The 21-28 Hz wheel-rate mode goes
    burst duty 0.072 -> 0.824 -> 0.80/0.88/0.85 -> 0.894 and in-burst LEVEL 0.88 -> 2.25 ->
    14.15/14.89/11.27 -> 18.63 across 1x / 4x / 6x / 8x.  That is the carrier.
  * The microphone cannot see that carrier at all, so the acoustic 6-12 Hz null says nothing
    about a modulation OF it.  Testing the modulation on the channel that cannot see the carrier
    was never going to work.

So: take the 21-28 Hz analytic envelope on the WHEEL-RATE channel -- the carrier's own amplitude
through time -- and ask whether THAT envelope carries 6-12 /s structure, engaged vs rolling-manual,
against a phase-shuffled surrogate.  This is the operator's sentence, tested literally.

⚠ This is a FOURTH wheel-rate instrument on a question three have already failed.  What is
  different: the previous three were a 2:1 harmonic test, an AM/demodulation test, and an envelope
  event-detector that failed its own controls.  This one is a spectral excess on the analytic
  envelope with a phase-shuffled surrogate and a matched manual arm -- and, unlike the acoustic
  version, it is run on a carrier whose presence is independently confirmed with a 21x ladder.
  If it also nulls, the honest conclusion is that the 6-12 /s ratchet is NOT an amplitude
  modulation of the 21-28 Hz mode, and the project should stop looking for it there.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import os
import sys
import json
import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
FS_CAN = 101.14792783296437
VLO, VHI = 0.0, 16.0
NPER = 256               # 2.53 s at 101 Hz -> 0.40 Hz resolution


def env(x, fs, lo, hi):
    sos = signal.butter(4, [lo / (fs / 2), hi / (fs / 2)], btype='band', output='sos')
    return np.abs(signal.hilbert(signal.sosfiltfilt(sos, np.nan_to_num(x - np.nanmean(x)))))


def excess(x, fs, tlo=6.0, thi=12.0):
    f, p = signal.welch(x - x.mean(), fs=fs, nperseg=min(NPER, len(x)),
                        noverlap=min(NPER, len(x)) // 2, detrend='linear')
    tgt = (f >= tlo) & (f <= thi)
    bg = ((f >= 2) & (f < 5)) | ((f > 14) & (f <= 25))
    if tgt.sum() < 3 or bg.sum() < 5:
        return None
    cf = np.polyfit(np.log(f[bg]), np.log(p[bg]), 1)
    return float(np.mean(p[tgt] / np.exp(np.polyval(cf, np.log(f[tgt])))))


def surro(x, rng):
    X = np.fft.rfft(x - x.mean())
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))


def runs(m, fs, min_s):
    m = np.asarray(m, bool)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k + 1])) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / fs >= min_s]


print("=" * 122)
print("ITEM 6 ON THE CARRIER -- 6-12 /s modulation of the 21-28 Hz WHEEL-RATE envelope")
print("=" * 122)
print("%-6s %-9s %8s %13s %13s %10s %24s %10s" %
      ('route', 'build', 'gain', 'ENG excess', 'MAN excess', 'eng/man', 'surrogate [2.5,97.5]',
       'verdict'))
rng = np.random.default_rng(23)
OUT = {}
for t in TAGS:
    R = A.load(t)
    e = env(R['rate_f'], FS_CAN, 21, 28)
    eng = R['can_eng'] & (R['can_v'] >= VLO) & (R['can_v'] < VHI)
    man = (~R['can_eng']) & (R['can_v'] >= A.V_ROLL) & (R['can_v'] < VHI)
    row = {}
    for nm, m in (('eng', eng), ('man', man)):
        rr = runs(m, FS_CAN, 3.0)
        v = [excess(e[a:b], FS_CAN) for a, b in rr]
        v = [x for x in v if x is not None]
        row[nm] = float(np.mean(v)) if v else None
    rr = runs(eng, FS_CAN, 3.0)
    sur = []
    for a, b in rr[:8]:
        for _ in range(30):
            s = excess(surro(e[a:b], rng), FS_CAN)
            if s is not None:
                sur.append(s)
    sl, sh = (np.percentile(sur, [2.5, 97.5]) if sur else (np.nan, np.nan))
    ok = (row['eng'] is not None) and np.isfinite(sl) and (row['eng'] > sh)
    OUT[t] = dict(eng=row['eng'], man=row['man'], sur_lo=float(sl), sur_hi=float(sh))
    print("%-6s %-9s %8.0fx %13s %13s %10s %24s %10s"
          % (t, A.NAMES[t], A.GAIN[t],
             ("%.3f" % row['eng']) if row['eng'] else '-',
             ("%.3f" % row['man']) if row['man'] else '-',
             ("%.2f" % (row['eng'] / row['man'])) if (row['eng'] and row['man']) else '-',
             "[%.3f, %.3f]" % (sl, sh) if np.isfinite(sl) else '-',
             'EXCESS' if ok else 'null'))

print()
print("  excess = mean(envelope PSD in 6-12 Hz / log-log background fitted on 2-5 and 14-25 Hz).")
print("  The surrogate preserves each engaged envelope's own spectrum and destroys only its phase")
print("  structure, so it is the right null for 'is there a LINE here, or just a smooth spectrum'.")

# ---- and the same statistic scanned across modulation rate, so a line at a DIFFERENT rate
#      than 6-12 /s is not missed by construction.
print()
print("=" * 122)
print("SCAN -- the same excess statistic across modulation rate, engaged, so a line outside")
print("        6-12 /s is not missed by the pre-set window.")
print("=" * 122)
WIN = [(1, 3), (3, 6), (6, 9), (9, 12), (12, 16), (16, 22), (22, 30), (30, 40)]
print("%-6s %-9s" % ('route', 'build') + "".join("%10s" % ("%g-%g/s" % w) for w in WIN))
for t in TAGS:
    R = A.load(t)
    e = env(R['rate_f'], FS_CAN, 21, 28)
    eng = R['can_eng'] & (R['can_v'] >= VLO) & (R['can_v'] < VHI)
    rr = runs(eng, FS_CAN, 3.0)
    row = []
    for lo, hi in WIN:
        v = [excess(e[a:b], FS_CAN, lo, hi) for a, b in rr]
        v = [x for x in v if x is not None]
        row.append(np.mean(v) if v else np.nan)
    print("%-6s %-9s" % (t, A.NAMES[t])
          + "".join(("%10.2f" % x) if np.isfinite(x) else "%10s" % '-' for x in row))
print("  🛑 the 2-5 and 14-25 /s bands are the BACKGROUND FIT for the 6-12 window, so their own")
print("     columns here are not independent of it -- read the 1-3, 22-30 and 30-40 columns as")
print("     the genuinely out-of-window comparisons.")

json.dump(OUT, open(os.path.join(A.HERE, '_scratch/out/_acoustic_item6_carrier.json'), 'w'), indent=1,
          default=float)
print("\n  wrote _scratch/out/_acoustic_item6_carrier.json")
