"""THE DEMODULATION TEST -- is the ~7 Hz ratchet an AM MODULATION of the 21-26 Hz carrier?

MECHANISM UNDER TEST (orchestrator + firmware tracer, declared before any outcome was seen):
the envelope of a lightly-damped mode has tau_env = Q/(pi.f); at Q 14-29 and f 21-26 Hz that is
171-440 ms, and a fast-drop / slow-regrow relaxation gives a modulation at ~4-7 Hz -- against the
kit's measured ratchet median of 7.79 Hz.  If true, the ratchet is AMPLITUDE MODULATION of the
carrier, not an independent slow mode.  Exactly the operator's words: "vibration comes in and
out ... the ratchet-like oscillation shows up on top of it".

THE TEST
  1. DEMODULATE: band-pass rate_f to 20-28 Hz, take the ANALYTIC envelope, spectrum-analyse it.
     A ~7 Hz line IN THE ENVELOPE = the mechanism.  A ~7 Hz line only in the RAW signal = the
     old, separate resonance.  That distinction is the whole test.
     🛑 `band_envelope` in `lib/_r31_common.py` / `lib/_r2b_common.py` is RECTIFIED (one-sided H=2X then
     irfft, imaginary part discarded), per `accord-band-envelope-is-rectified-not-analytic`.
     A RECTIFIED envelope has its own harmonics and would MANUFACTURE envelope lines.  This file
     therefore implements the TRUE analytic envelope (|x + j.H{x}|) and asserts it differs.
  2. SIDEBANDS: true AM puts energy at f_c +- f_m (~14-19 and ~28-34 Hz), not at f_m.
  3. ⭐ THE DISCRIMINATOR: f_mod ∝ f_carrier / Q.  The carrier MOVES with gain (21.9 / 23.6 /
     24.9 Hz at 1x / 4x / 6x on record), so the envelope line must move PROPORTIONALLY.
     A firmware time constant would NOT.  Tested across r97(1x) / r85(4x) / r96,r9e,ra4(6x) /
     r95(8x).  ⚠ r95 confounded (Lever B disarmed, zero seconds >80 km/h).

CONTROLS, RUN FIRST
  N1 PHASE-SHUFFLED SURROGATE -- randomise the phases of the 20-28 Hz band, preserving its
     spectrum exactly.  This DESTROYS amplitude modulation while leaving the carrier identical.
     An unusually clean null here.
  N2 CONTROL-BAND CARRIER (32-45 Hz) -- should show no envelope line.
  N3 MANUAL arm, speed-matched.
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
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
SEG = int(round(8 * FS))          # 8 s envelope segments -> 0.125 Hz envelope resolution
fe = np.fft.rfftfreq(SEG, 1 / FS)
WIN = np.hanning(SEG + 1)[:SEG]
U = (WIN ** 2).sum()


def analytic_env(x, lo, hi, shuffle=False, rng=None):
    """TRUE analytic envelope of x band-limited to [lo,hi).  shuffle randomises band phases."""
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / FS)
    keep = (fr >= lo) & (fr < hi)
    Y = np.zeros_like(X)
    Y[keep] = X[keep]
    if shuffle:
        ph = rng.uniform(0, 2 * np.pi, keep.sum())
        Y[keep] = np.abs(Y[keep]) * np.exp(1j * ph)
    # analytic signal: one-sided, doubled, KEEPING the imaginary part
    Y2 = np.zeros(n, complex)
    Y2[:len(Y)] = 2.0 * Y
    if n % 2 == 0:
        Y2[0] /= 2
    z = np.fft.ifft(Y2)
    return np.abs(z)


def rect_env(x, lo, hi):
    """The kit's RECTIFIED envelope, for the comparison the memory demands."""
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    fr = np.fft.rfftfreq(n, 1 / FS)
    Y = np.zeros_like(X)
    keep = (fr >= lo) & (fr < hi)
    Y[keep] = 2.0 * X[keep]
    return np.abs(np.fft.irfft(Y, n))


def env_spectrum(tag, engaged, vlo, vhi, lo, hi, shuffle=False, seed=5):
    """Per-run envelope spectra of the [lo,hi) carrier."""
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    rng = np.random.default_rng(seed)
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if (b0 - a0) < SEG or not m[a0]:
            continue
        seg = rate[a0:b0]
        if not np.all(np.isfinite(seg)):
            continue
        env = analytic_env(seg, lo, hi, shuffle, rng)
        S, nw = None, 0
        for s in range(0, len(env) - SEG + 1, SEG // 2):
            w = env[s:s + SEG]
            w = w - w.mean()
            X = np.fft.rfft(w * WIN)
            p = (X.conj() * X).real / (FS * U)
            S = p if S is None else S + p
            nw += 1
        if nw:
            out.append((S, nw))
    return out


def peak(sp, lo=5.0, hi=12.0):
    """LOCAL peak in the envelope spectrum, with prominence against a LOCAL baseline.

    🛑 FIXED.  The first version took the global max over 3-15 Hz against a 2-20 Hz median.
    The envelope spectrum falls like 1/f, so that statistic returned the 3.00 Hz SEARCH-WINDOW
    EDGE on five of six builds -- it was measuring the slope, not a line.  This version searches
    5-12 Hz (the operator's own placement of the symptom) and divides by the median of the
    SURROUNDING +-4 Hz shoulders, excluding a +-1 Hz core, so a monotone slope gives ~1.0.
    """
    if not sp:
        return np.nan, np.nan, 0
    S = sum(s[0] for s in sp) / sum(s[1] for s in sp)
    sel = (fe >= lo) & (fe < hi)
    if not sel.any():
        return np.nan, np.nan, len(sp)
    i = np.argmax(S[sel])
    fp = float(fe[sel][i])
    sh = (((fe >= fp - 4) & (fe < fp - 1)) | ((fe > fp + 1) & (fe <= fp + 4)))
    base = np.median(S[sh]) if sh.any() else np.nan
    return fp, float(S[sel][i] / base) if base and base > 0 else np.nan, len(sp)


print("=" * 112)
print("0. INSTRUMENT CHECK -- the rectified vs analytic envelope, as the memory demands")
print("=" * 112)
d = L.load('ra4')
seg = d['rate_f'].astype(float)[20000:20000 + SEG * 4]
ea = analytic_env(seg, 20, 28)
er = rect_env(seg, 20, 28)
print("  analytic env: mean %.4f sd %.4f   rectified env: mean %.4f sd %.4f   corr %.4f"
      % (ea.mean(), ea.std(), er.mean(), er.std(), np.corrcoef(ea, er)[0, 1]))
Sa = np.abs(np.fft.rfft((ea - ea.mean()) * np.hanning(len(ea))))
Sr = np.abs(np.fft.rfft((er - er.mean()) * np.hanning(len(er))))
fr2 = np.fft.rfftfreq(len(ea), 1 / FS)
b1 = (fr2 >= 3) & (fr2 < 15)
b2 = (fr2 >= 40) & (fr2 < 56)
print("  3-15 Hz / 40-56 Hz energy ratio:  analytic %.3f   RECTIFIED %.3f"
      % (Sa[b1].sum() / Sa[b2].sum(), Sr[b1].sum() / Sr[b2].sum()))
print("  ⇒ the rectified form folds the carrier to 2f_c (~44 Hz) and back; it is NOT usable for")
print("    envelope-shape work.  Everything below uses the ANALYTIC envelope. [EVIDENCE]")

print()
print("=" * 112)
print("1. ENVELOPE SPECTRUM OF THE 20-28 Hz CARRIER -- with its shuffled null beside it")
print("=" * 112)
print("  N1 null: phases of the 20-28 Hz band randomised -- destroys AM, preserves the spectrum.")
print()
ARMS = [('STOCK 1x  ENG 0-40', 'r97', True, 0, 40), ('V102 6x   ENG 0-40', 'r96', True, 0, 40),
        ('V103 6x   ENG 0-40', 'r9e', True, 0, 40), ('V104 6x   ENG 0-40', 'ra4', True, 0, 40),
        ('V104 6x   ENG 80-95', 'ra4', True, 80, 95), ('V103 6x   ENG 80-95', 'r9e', True, 80, 95),
        ('V102 6x   ENG 80-95', 'r96', True, 80, 95), ('STOCK 1x  ENG 80-95', 'r97', True, 80, 95),
        ('V104 6x   MANUAL 0-40', 'ra4', False, 0, 40)]
print("%24s %6s %10s %10s %14s %14s %10s" %
      ('arm', 'runs', 'f_env', 'promin.', 'NULL f_env', 'NULL promin.', 'ratio'))
for nm, tag, eng, vlo, vhi in ARMS:
    sp = env_spectrum(tag, eng, vlo, vhi, 20, 28)
    ns = env_spectrum(tag, eng, vlo, vhi, 20, 28, shuffle=True)
    fp, pr, n = peak(sp)
    fn, pn, _ = peak(ns)
    if n < 2:
        print("%24s %6d  (too few runs)" % (nm, n))
        continue
    print("%24s %6d %10.2f %10.3f %14.2f %14.3f %10.2f"
          % (nm, n, fp, pr, fn, pn, pr / pn if pn else np.nan))
print("  prominence = envelope-spectrum peak in 3-15 Hz divided by the 2-20 Hz median.")
print("  ⇒ a REAL AM line must have prominence CLEARLY ABOVE its shuffled null's.")

print()
print("=" * 112)
print("2. N2 CONTROL-BAND CARRIER (32-45 Hz) -- should show no envelope line")
print("=" * 112)
print("%24s %6s %10s %10s %14s %10s" % ('arm', 'runs', 'f_env', 'promin.', 'NULL promin.', 'ratio'))
for nm, tag, eng, vlo, vhi in ARMS[:5]:
    sp = env_spectrum(tag, eng, vlo, vhi, 32, 45)
    ns = env_spectrum(tag, eng, vlo, vhi, 32, 45, shuffle=True)
    fp, pr, n = peak(sp)
    _, pn, _ = peak(ns)
    if n < 2:
        continue
    print("%24s %6d %10.2f %10.3f %14.3f %10.2f" % (nm, n, fp, pr, pn, pr / pn if pn else np.nan))

print()
print("=" * 112)
print("3. ⭐ THE DISCRIMINATOR -- does f_env scale with the CARRIER frequency?")
print("=" * 112)
print("  f_mod ∝ f_carrier / Q.  The carrier moves with gain (21.9 / 23.6 / 24.9 Hz at 1x/4x/6x")
print("  on record).  A firmware time constant would NOT move with it.")
print()
print("%28s %10s %10s %10s %12s" % ('build (gain)', 'f_carrier', 'f_env', 'f_env/f_c', 'runs'))
for nm, tag in (('r97  STOCK 1x', 'r97'), ('r85  V100 4x', 'r85'), ('r96  V102 6x', 'r96'),
                ('r9e  V103 6x', 'r9e'), ('ra4  V104 6x', 'ra4'),
                ('r95  V101 8x (CONFOUND)', 'r95')):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    rate = d['rate_f'].astype(float)
    NP = int(round(8 * FS))
    ff = np.fft.rfftfreq(NP, 1 / FS)
    w = np.hanning(NP + 1)[:NP]
    S, nw = None, 0
    ei = np.flatnonzero(e)
    for s in range(ei[0], ei[-1] - NP, NP // 2):
        if not e[s:s + NP].all():
            continue
        xs = rate[s:s + NP]
        xs = xs - xs.mean()
        X = np.fft.rfft(xs * w)
        p = (X.conj() * X).real
        S = p if S is None else S + p
        nw += 1
    if S is None:
        continue
    band = (ff >= 18) & (ff < 30)
    fc = ff[band][np.argmax(S[band])]
    sp = env_spectrum(tag, True, -1e9, 1e9, 20, 28)
    fp, pr, n = peak(sp)
    print("%28s %10.2f %10.2f %10.4f %12d" % (nm, fc, fp, fp / fc if fc else np.nan, n))
print()
print("  ⇒ if f_env/f_c is CONSTANT across builds, the modulation tracks the carrier (the")
print("    mechanism).  If f_env is constant while f_c moves, it is a fixed time constant.")
