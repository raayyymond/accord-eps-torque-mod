"""ITEM 1 -- THE STOCK-vs-6x CONTRAST ACROSS 100 Hz - 8 kHz, ENGAGED, < 16 km/h.

WHY THIS BAND FIRST: the operator says GRINDING, which is a SOUND, and this project has never
looked in the band where an audible grind would be.  `rate_f` is Nyquist-limited to ~50 Hz;
this channel runs to 8 kHz.  Everything below ~100 Hz is a second look at what we already
measure -- above it is unexplored.

🛑 CONTROLS FIRST, AND THEY ARE HEAVIER HERE THAN ANYWHERE ELSE TODAY
  C1 THE MANUAL / LKAS-OFF ARM, SPEED-MATCHED -- **the decisive control.**  The 21-28 Hz mode is
     engaged-only.  Road noise, wind, ENGINE ORDER and HVAC do not know whether LKAS is on, so
     an ENGAGED-ONLY acoustic signature at matched speed cannot be any of them.  Reported before
     any stock-vs-6x number.
  C2 SPEED REGRESSION -- acoustic level regressed on speed inside the stratum; the residual is
     what a build can claim.  Road/wind noise scales hard with speed.
  C3 EPISODE BOOTSTRAP, never windows.
  C4 A LOW-BAND CROSS-CHECK (21-28 Hz on the mic vs the same band on `rate_f`) is reported but
     ⚠ CARRIED AS WEAK: below ~100 Hz a MEMS mic measures structure-borne pressure as much as
     airborne sound, so it is a second differently-aliased look at the SAME mode, NOT independent
     confirmation.  Above ~100 Hz that objection weakens sharply.

⚠ ONE 60 s SEGMENT PROVES NOTHING -- every number here is over full routes with controls.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KPH = 3.6
TAGS = ('r97', 'r96', 'r9e', 'ra4')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x'}
VLO, VHI = 0.0, 16.0
FR = 62.5


def load(tag):
    a = np.load(os.path.join(HERE, '_cache_%s' % tag, '%s_audio.npz' % tag))
    d = L.load(tag)
    tc = d['t'].astype(float)
    ta = a['t'].astype(float)
    eng = np.interp(ta, tc, (d['cc_lat'] > 0.5).astype(float)) > 0.5
    v = np.interp(ta, tc, d['v_rear'].astype(float) * KPH)
    return dict(t=ta, tob=a['tob'].astype(float), tob_f=a['tob_f'], wide=a['wide'].astype(float),
                wide_lab=[str(x) for x in a['wide_lab']], rms=a['rms'].astype(float),
                eng=eng, v=v, meta=a['meta'])


A = {}
for t in TAGS:
    try:
        A[t] = load(t)
    except FileNotFoundError:
        print("  %s: audio cache not built yet" % t)
if len(A) < 2:
    raise SystemExit("need at least two routes")

print("=" * 118)
print("0. COVERAGE AUDIT -- all routes, full length")
print("=" * 118)
print("%8s %10s %14s %11s %10s %11s %12s %12s" %
      ('route', 'blocks', 'samples', 'audio s', 'clipped', 'frames', 'eng <16 s', 'man <16 s'))
for t in TAGS:
    if t not in A:
        continue
    R = A[t]
    sr, nfft, hop, nb, ns, nc = R['meta']
    e = R['eng'] & (R['v'] >= VLO) & (R['v'] < VHI)
    m = (~R['eng']) & (R['v'] >= VLO) & (R['v'] < VHI)
    print("%8s %10d %14d %11.1f %10d %11d %12.1f %12.1f"
          % (t, nb, ns, ns / sr, nc, len(R['t']), e.sum() / FR, m.sum() / FR))
print("  16 kHz PCM, 1024-pt windows / 256 hop => 62.5 Hz feature rate (Nyquist 31 Hz on the")
print("  envelope, deliberately above his 6-12 /s).")


def eps(mask):
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mask)]))
    return [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1)
            if mask[b[i]] and (b[i + 1] - b[i]) >= int(2 * FR)]


def band_level(R, mask, col, arr='tob'):
    """Mean band POWER over the mask, per episode -> pooled."""
    e = eps(mask)
    if not e:
        return np.nan, 0
    v = np.concatenate([R[arr][s:t2, col] for s, t2 in e])
    return float(v.mean()), len(e)


def boot(Ra, Rb, ma, mb, col, arr='tob', nb=3000, seed=17):
    ea, eb = eps(ma), eps(mb)
    if len(ea) < 3 or len(eb) < 3:
        return None
    pa = [Ra[arr][s:t2, col] for s, t2 in ea]
    pb = [Rb[arr][s:t2, col] for s, t2 in eb]
    pt = np.sqrt(np.concatenate(pb).mean() / np.concatenate(pa).mean())
    rg = np.random.default_rng(seed)
    d = np.array([np.sqrt(np.concatenate([pb[j] for j in rg.integers(0, len(pb), len(pb))]).mean()
                          / np.concatenate([pa[j] for j in rg.integers(0, len(pa), len(pa))]).mean())
                  for _ in range(nb)])
    return pt, np.percentile(d, 2.5), np.percentile(d, 97.5), len(eb), len(ea)


def M(R, engaged=True, vlo=VLO, vhi=VHI):
    return (R['eng'] if engaged else ~R['eng']) & (R['v'] >= vlo) & (R['v'] < vhi)


# ================================================================= C1
print()
print("=" * 118)
print("C1 -- THE DECISIVE CONTROL: ENGAGED / MANUAL at matched speed (< 16 km/h), per band.")
print("=" * 118)
print("  Road noise, wind, ENGINE ORDER and HVAC do not know whether LKAS is on.  A band that is")
print("  elevated ENGAGED-ONLY, on the 6x builds but not on stock, cannot be any of them.")
print()
TOBF = A[TAGS[0]]['tob_f']
print("%9s" % 'band Hz' + "".join("%12s" % NAMES[t] for t in TAGS if t in A))
for i, fc in enumerate(TOBF):
    row = []
    for t in TAGS:
        if t not in A:
            continue
        R = A[t]
        pe, _ = band_level(R, M(R, True), i)
        pm, _ = band_level(R, M(R, False), i)
        row.append(np.sqrt(pe / pm) if (pm and np.isfinite(pm) and pm > 0) else np.nan)
    print("%9.0f" % fc + "".join(("%12.3f" % r) if np.isfinite(r) else "%12s" % '-' for r in row))
print("  values are ENGAGED/MANUAL amplitude ratios.  ~1.0 = the band does not care about LKAS.")

# ================================================================= item 1
print()
print("=" * 118)
print("1. STOCK vs 6x ACROSS THE AUDIBLE RANGE -- ENGAGED, < 16 km/h, episode bootstrap")
print("=" * 118)
print("%9s %12s %12s %12s %12s %22s" %
      ('band Hz', 'STOCK amp', 'V102', 'V103', 'V104', 'V104/STOCK [95 % CI]'))
BEST = []
for i, fc in enumerate(TOBF):
    lv = []
    for t in TAGS:
        if t not in A:
            lv.append(np.nan)
            continue
        p, _ = band_level(A[t], M(A[t], True), i)
        lv.append(np.sqrt(p))
    r = boot(A['r97'], A['ra4'], M(A['r97'], True), M(A['ra4'], True), i) if 'ra4' in A else None
    s = "%.2f [%.2f, %.2f]" % (r[0], r[1], r[2]) if r else "-"
    if r:
        BEST.append((r[0], fc, i, r))
    print("%9.0f %12.1f %12.1f %12.1f %12.1f %22s" % (fc, *lv, s))
print("  amplitudes are sqrt(mean band power), arbitrary units (int16 PCM).")

if BEST:
    BEST.sort(reverse=True)
    print()
    print("  LARGEST V104/STOCK CONTRASTS IN THE AUDIBLE RANGE:")
    for v, fc, i, r in BEST[:5]:
        R97, RA4 = A['r97'], A['ra4']
        e97 = np.sqrt(band_level(R97, M(R97, True), i)[0] / band_level(R97, M(R97, False), i)[0])
        ea4 = np.sqrt(band_level(RA4, M(RA4, True), i)[0] / band_level(RA4, M(RA4, False), i)[0])
        print("     %5.0f Hz  V104/STOCK %.2f [%.2f, %.2f]   eng/man: STOCK %.2f  V104 %.2f"
              % (fc, r[0], r[1], r[2], e97, ea4))

# ================================================================= C2
print()
print("=" * 118)
print("C2 -- SPEED REGRESSION inside the stratum.  Road/wind noise scales hard with speed.")
print("=" * 118)
print("%9s" % 'band Hz' + "".join("%16s" % (NAMES[t] + " slope") for t in TAGS if t in A))
for i, fc in enumerate(TOBF[::4]):
    j = list(TOBF).index(fc)
    row = []
    for t in TAGS:
        if t not in A:
            continue
        R = A[t]
        m = M(R, True)
        y = 10 * np.log10(np.maximum(R['tob'][m, j], 1e-30))
        x = R['v'][m]
        ok = np.isfinite(y) & np.isfinite(x)
        if ok.sum() < 100:
            row.append(np.nan)
            continue
        X = np.vstack([x[ok], np.ones(ok.sum())]).T
        row.append(np.linalg.lstsq(X, y[ok], rcond=None)[0][0])
    print("%9.0f" % fc + "".join(("%16.3f" % r) if np.isfinite(r) else "%16s" % '-' for r in row))
print("  dB per km/h inside 0-16 km/h.  A large positive slope means the band is speed-driven and")
print("  any cross-route contrast there needs the speed distributions matched tightly.")
print("  engaged v p50 in this stratum: " +
      "  ".join("%s %.1f" % (t, np.median(A[t]['v'][M(A[t], True)])) for t in TAGS if t in A))

# ================================================================= C4
print()
print("=" * 118)
print("C4 -- THE SUB-100 Hz CROSS-CHECK (weak by construction, reported for completeness)")
print("=" * 118)
print("%12s" % 'wide band' + "".join("%12s" % NAMES[t] for t in TAGS if t in A)
      + "%22s" % 'V104/STOCK [CI]')
for i, lab in enumerate(A[TAGS[0]]['wide_lab']):
    lv = []
    for t in TAGS:
        if t not in A:
            continue
        p, _ = band_level(A[t], M(A[t], True), i, arr='wide')
        lv.append(np.sqrt(p))
    r = (boot(A['r97'], A['ra4'], M(A['r97'], True), M(A['ra4'], True), i, arr='wide')
         if 'ra4' in A else None)
    s = "%.2f [%.2f, %.2f]" % (r[0], r[1], r[2]) if r else "-"
    print("%12s" % lab + "".join("%12.1f" % x for x in lv) + "%22s" % s)
print("  🛑 below ~100 Hz a MEMS mic measures structure-borne pressure as much as airborne sound.")
print("     These rows are a SECOND, DIFFERENTLY-ALIASED look at the same mode -- NOT independent")
print("     confirmation.  The 100 Hz - 8 kHz table above is where the new information is.")
