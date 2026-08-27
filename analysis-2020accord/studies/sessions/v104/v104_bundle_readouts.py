"""PRE-REGISTERED READOUTS FOR THE BUNDLE BUILD (c4 k = 1.85 + Lever B), on route 0x9e's own blocks.

Endpoint 1 (CLEAN)  : 21.0-22.5 Hz band RMS of rate_f, engaged  -> attributable to LEVER B
Endpoint 2 (MUDDY)  : 6-9 Hz Re(Z), engaged                     -> not attributable, but diagnostic
Both on the frozen estimator (4 s Hann, 50 % overlap, detrended) and the same exposure rule:
ONE contiguous engaged block of >= 15 s.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
import numpy as np
import _gate2_boost_lib as L

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
c1, c2, c3, c4 = L.honda_exact()
A_FILT = 0.0457


def Hh(fc):
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


d9 = L.load('r9e')
eng = d9['cc_lat'] > 0.5
rate = d9['rate_f'].astype(float)
tq = d9['tq'].astype(float)
w = rate * L.DEG2RAD
vk = d9['v_rear'].astype(float) * 3.6
df = f[1] - f[0]


def blocks(mask, T):
    n = int(T * L.FS)
    out = []
    for a0, b0 in L.episodes(mask):
        for s in range(a0, b0 - n + 1, n):
            out.append((s, s + n))
    return out


def band_rms(seg, sig, lo, hi):
    sp = L.episode_specs(sig, sig, [seg], NPER)
    if not sp:
        return np.nan
    sel = (f >= lo) & (f < hi)
    return float(np.sqrt(sp[0][0][sel].sum() / sp[0][3] * df))


def rez(seg, lo, hi):
    sp = L.episode_specs(w, tq, [seg], NPER)
    if not sp:
        return np.nan, np.nan
    H, co = L.band_H(sp, f, lo, hi)
    return H.real, co


# =================================================================================================
print("=" * 100)
print("0. IS c4 INERT AT 21.0-22.5 Hz?  -- the premise the whole clean readout rests on")
print("=" * 100)


def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    return (L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER),
            L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float), eps, NPER))


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def ident(lo, hi, nboot=3000, seed=41):
    def one(i4, i8):
        G4 = L.band_H([G4s[j] for j in i4], f, lo, hi)[0]
        Z4 = L.band_H([Z4s[j] for j in i4], f, lo, hi)[0]
        G8 = L.band_H([G8s[j] for j in i8], f, lo, hi)[0]
        Z8 = L.band_H([Z8s[j] for j in i8], f, lo, hi)[0]
        r = Z4 / Z8
        c = (r - 1) / (G8 - r * G4)
        return c, G4, 1 + c * G4, Z4
    rng = np.random.default_rng(seed)
    n4, n8 = len(G4s), len(G8s)
    return (one(range(n4), range(n8)),
            np.array([one(rng.integers(0, n4, n4), rng.integers(0, n8, n8)) for _ in range(nboot)]))


for bb, fc in (((21, 22.5), 21.75), ((18, 22), 20.0), ((22, 26), 24.0)):
    pt, bs = ident(*bb)
    dG = 0.85 * (-A_FILT * Hh(fc))
    amp_pt = abs(pt[2]) / abs(pt[2] + pt[0] * dG)
    amp_bs = np.abs(bs[:, 2]) / np.abs(bs[:, 2] + bs[:, 0] * dG)
    ci = np.percentile(amp_bs, [2.5, 97.5])
    print("  %5.1f-%-4.1f Hz : c4 k=1.85 amplification ratio %.4f  95 %% CI [%.4f, %.4f]  "
          "P(|ratio-1| > 0.10) = %.3f"
          % (bb[0], bb[1], amp_pt, ci[0], ci[1], (np.abs(amp_bs - 1) > 0.10).mean()))
print("  => 21.0-22.5 Hz is the band where c4 does least. Lever B is attributable THERE.")

# =================================================================================================
print()
print("=" * 100)
print("1. ENDPOINT 1 (CLEAN) -- 21.0-22.5 Hz band RMS of rate_f, engaged.  ATTRIBUTABLE TO LEVER B")
print("=" * 100)
for T in (15, 20, 30):
    bl = blocks(eng, T)
    v = np.array([band_rms(s, rate, 21.0, 22.5) for s in bl])
    v = v[np.isfinite(v)]
    print("  %2d s blocks: n=%2d   p5 %.4f  p25 %.4f  p50 %.4f  p75 %.4f  p95 %.4f  (deg/s RMS)"
          % (T, len(v), *np.percentile(v, [5, 25, 50, 75, 95])))

bl15 = blocks(eng, 15)
v15 = np.array([band_rms(s, rate, 21.0, 22.5) for s in bl15])
vsp = np.array([np.median(vk[s:e]) for s, e in bl15])
v15 = v15[np.isfinite(v15)]
med = np.median(v15)
print()
print("  speed of each 15 s block (km/h): p5 %.0f  p50 %.0f  p95 %.0f ; blocks under 20 km/h: %d"
      % (*np.percentile(vsp, [5, 50, 95]), (vsp < 20).sum()))
print("  grind #1 is 9.88x stronger at 5-10 km/h than the drive average (STATE.md), so a")
print("  low-speed block is worth several high-speed ones.  Route 0x9e has %d blocks under"
      % (vsp < 20).sum())
print("  20 km/h out of %d -- the operator should aim the symptomatic block THERE." % len(vsp))

lo5, lo25 = np.percentile(v15, [5, 25])
print()
print("  BASE RATE (V103, route 0x9e, %d independent 15 s engaged blocks):" % len(v15))
print("     median %.4f deg/s RMS ; the 5th percentile is %.4f (= %.3f x median)"
      % (med, lo5, lo5 / med))
print("  LEVER B ROAD PRIOR: 0.40 [0.27, 0.58] on this band  => predicted new median %.4f"
      % (0.40 * med))
print()
sd = (np.percentile(np.log(v15), 95) - np.percentile(np.log(v15), 5)) / 3.29
print("  log-scale block SD = %.3f (from the 5-95 spread of V103's own blocks)" % sd)
for thr_name, thr in (("p5 of V103's blocks", lo5), ("p25 of V103's blocks", lo25)):
    p_null = (v15 < thr).mean()
    for eff, lbl in ((0.40, 'point'), (0.58, 'weak end'), (0.27, 'strong end')):
        z = (np.log(thr) - np.log(eff * med)) / sd
        from math import erf, sqrt
        p_alt = 0.5 * (1 + erf(z / sqrt(2)))
        if lbl == 'point':
            print("  THRESHOLD '%s' = %.4f : P(one block below | NO effect) = %.3f ; "
                  "P(below | Lever B works at %.2f) = %.3f  => LR %.1f:1"
                  % (thr_name, thr, p_null, eff, p_alt, p_alt / max(p_null, 1e-3)))
        else:
            print("       %-10s effect %.2f : P(below) = %.3f" % (lbl, eff, p_alt))

# =================================================================================================
print()
print("=" * 100)
print("2. ENDPOINT 2 (MUDDY) -- 6-9 Hz Re(Z), engaged.  What each outcome licenses")
print("=" * 100)
r15 = np.array([rez(s, 6, 9)[0] for s in bl15])
r15 = r15[np.isfinite(r15)]
print("  BASE RATE (V103, %d blocks): p5 %+.0f  p25 %+.0f  p50 %+.0f  p75 %+.0f  p95 %+.0f"
      % (len(r15), *np.percentile(r15, [5, 25, 50, 75, 95])))
sd_z = (np.percentile(r15, 95) - np.percentile(r15, 5)) / 3.29
print("  block-to-block SD = %.0f counts (5-95 spread / 3.29)" % sd_z)
print()
print("  MODEL PREDICTIONS at 6-9 Hz (exact Mobius, a_filt):")
preds = [("no effect (null)", np.median(r15)), ("Lever B alone", -1313),
         ("c4 alone", +296), ("BUNDLE", -1034)]
thr = np.percentile(r15, 95)
from math import erf, sqrt
print("  pre-registered threshold = V103's own p95 = %+.0f  (P = 0.05 under the null BY"
      " CONSTRUCTION)" % thr)
for lbl, mu in preds:
    z = (mu - thr) / sd_z
    p = 0.5 * (1 + erf(z / sqrt(2)))
    print("     %-18s predicted %+7.0f  =>  P(one block exceeds threshold) = %.3f  LR %5.1f:1"
          % (lbl, mu, p, p / 0.05))
print()
print("  *** ALL THREE hypotheses predict IMPROVEMENT. So the DIAGNOSTIC outcome is the one")
print("      none of them predicts: a block at or below V103's own MEDIAN (%+.0f)." % np.median(r15))
print("      P(that | any lever works) <= %.3f. It falsifies the identification without needing"
      % max([0.5 * (1 + erf(((np.median(r15)) - mu) / sd_z / sqrt(2))) for _, mu in preds[1:]]))
print("      attribution -- which is exactly what a muddy score can still deliver.")


# =================================================================================================
print()
print("=" * 100)
print("3. FIXING ENDPOINT 1 -- the raw band RMS is exposure-dominated. Try a BAND RATIO.")
print("=" * 100)
print("  V103's own 15 s blocks span 59x in 21.0-22.5 Hz RMS (p5 0.117, p95 6.93). That spread is")
print("  EXPOSURE (grind #1 is 9.88x stronger at 5-10 km/h than at 20-40), not build.  A ratio to a")
print("  control band cancels the common exposure factor -- the kit's own grind-#1 statistic form.")
print()
print("%22s %8s %9s %9s %9s %9s %9s" %
      ('statistic', 'n', 'p5', 'p50', 'p95', 'log SD', 'LR @0.40'))


def logsd(x):
    x = x[np.isfinite(x) & (x > 0)]
    return (np.percentile(np.log(x), 95) - np.percentile(np.log(x), 5)) / 3.29


def lr_at(x, eff=0.40, q=25):
    """Likelihood ratio for a one-block test at the q-th percentile threshold."""
    x = x[np.isfinite(x) & (x > 0)]
    s = logsd(x)
    thr = np.percentile(x, q)
    p_null = q / 100.0
    z = (np.log(thr) - np.log(eff * np.median(x))) / s
    from math import erf, sqrt
    p_alt = 0.5 * (1 + erf(z / sqrt(2)))
    return p_alt / p_null, thr, p_alt


CTRL = [(26, 31), (31, 35), (9, 13)]
cand = {'raw 21.0-22.5 RMS': np.array([band_rms(s, rate, 21.0, 22.5) for s in bl15])}
for cb in CTRL:
    num = np.array([band_rms(s, rate, 21.0, 22.5) for s in bl15])
    den = np.array([band_rms(s, rate, cb[0], cb[1]) for s in bl15])
    cand['ratio to %d-%d Hz' % cb] = num / den
for nm, x in cand.items():
    xx = x[np.isfinite(x) & (x > 0)]
    lr, thr, palt = lr_at(x)
    print("%22s %8d %9.4f %9.4f %9.4f %9.3f %9.1f:1" %
          (nm, len(xx), *np.percentile(xx, [5, 50, 95]), logsd(x), lr))

print()
print("  and the same for the 6-9 Hz endpoint's own signal, for comparison:")
num69 = np.array([band_rms(s, rate, 6, 9) for s in bl15])
for cb in CTRL:
    den = np.array([band_rms(s, rate, cb[0], cb[1]) for s in bl15])
    x = num69 / den
    print("%22s %8d %9.4f %9.4f %9.4f %9.3f" %
          ('6-9 / %d-%d Hz' % cb, np.isfinite(x).sum(), *np.percentile(x[np.isfinite(x)],
                                                                      [5, 50, 95]), logsd(x)))

print()
print("[3.1] speed conditioning -- does restricting the block's speed shrink the spread?")
print("%26s %6s %9s %9s %9s" % ('subset', 'n', 'p50', 'log SD', 'LR @0.40'))
raw = cand['raw 21.0-22.5 RMS']
for lbl, sel in (('all blocks', np.ones(len(bl15), bool)),
                 ('speed 40-70 km/h', (vsp >= 40) & (vsp <= 70)),
                 ('speed 50-80 km/h', (vsp >= 50) & (vsp <= 80)),
                 ('speed < 40 km/h', vsp < 40)):
    x = raw[sel]
    xx = x[np.isfinite(x) & (x > 0)]
    if len(xx) < 4:
        print("%26s %6d   (too few blocks to characterise)" % (lbl, len(xx)))
        continue
    lr, thr, palt = lr_at(x)
    print("%26s %6d %9.4f %9.3f %9.1f:1" % (lbl, len(xx), np.median(xx), logsd(x), lr))
