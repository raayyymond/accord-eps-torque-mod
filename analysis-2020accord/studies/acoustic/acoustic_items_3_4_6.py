r"""ITEMS 3, 4 and 6 -- the gain ladder, burst structure, and the operator's 6-12 /s.

WHAT IS ALREADY SETTLED, and constrains everything here:
  * The microphone is BLIND to the 21-28 Hz mode.  Wheel-rate in-burst level runs 0.88 -> 18.6
    across the ladder (21x) while the acoustic in-burst level is flat at 380-510 on every build,
    and the two envelopes are uncorrelated (r -0.13..+0.05, inside a phase-shuffled null).
  * The microphone IS alive in the audible range: band power rises 0.14-0.28 dB per km/h through
    100-1600 Hz, and on `r97` -- the route whose blinker arms are tightly speed-matched -- the
    envelope pipeline resolves the turn-signal click as a localised 1.2-2.2 Hz bump at z ~ 4.
  * Absolute acoustic level is NOT comparable between drives: the parked, engine-on, LKAS-off
    ambient differs by up to 12x between routes.  Only WITHIN-route contrasts travel.

SO:
  ITEM 3  THE LADDER, on the two quantities that survive -- the wheel-rate 21-28 Hz burst
          statistics (where the mode actually lives) and the WITHIN-route acoustic engaged/manual
          ratio (immune to the cabin offset).  Absolute acoustic level is not laddered at all.
  ITEM 4  BURST STRUCTURE on the AUDIBLE envelopes, pre-declared detector, verbatim.
  ITEM 6  6-12 /s STRUCTURE in the acoustic envelope -- the operator's own description, and the
          thing three wheel-rate instruments have already failed to find.  Tested engaged vs
          ROLLING-MANUAL within route, against a phase-shuffled surrogate.
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
FSE = 125.0
VLO, VHI = 0.0, 16.0
MIN_BURST, MERGE_GAP, THR_FRAC = 0.25, 0.15, 0.70
AUD = [(100, 300), (300, 800), (800, 2000), (2000, 5000), (5000, 7800), (100, 7800)]

D = {}
for t in TAGS:
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    e = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_env.npz' % t))
    te, ev, sp = e['t'].astype(float), e['env'].astype(float), e['splice'].astype(bool)
    ct = c['t'].astype(float)
    D[t] = dict(t=te, env=ev, f=e['env_f'], ok=~sp,
                eng=np.interp(te, ct, (c['cc_lat'].astype(float) > 0.5).astype(float)) > 0.5,
                v=np.interp(te, ct, c['v_rear'].astype(float)) * 3.6)
BF = D['r97']['f']
COL = {tuple(int(x) for x in BF[j]): j for j in range(len(BF))}


def msk(t, engaged=True, rolling=True):
    d = D[t]
    m = (d['eng'] if engaged else ~d['eng']) & (d['v'] >= VLO) & (d['v'] < VHI) & d['ok']
    if not engaged and rolling:
        m = m & (d['v'] >= A.V_ROLL)
    return m


def runs_of(m, min_s):
    m = np.asarray(m, bool)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k + 1])) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / FSE >= min_s]


# ============================================================== ITEM 4  burst structure
def bursts(env, m, thr_on, thr_off):
    n = len(env)
    on, st = env >= thr_on, env >= thr_off
    lab = np.zeros(n, bool)
    i = 0
    while i < n:
        if on[i]:
            a = i
            while a > 0 and st[a - 1]:
                a -= 1
            b = i
            while b < n - 1 and st[b + 1]:
                b += 1
            lab[a:b + 1] = True
            i = b + 1
        else:
            i += 1
    g = int(round(MERGE_GAP * FSE))
    idx = np.flatnonzero(np.diff(lab.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [n]))
    for k in range(1, len(b) - 2):
        if (not lab[b[k]]) and (b[k + 1] - b[k]) <= g and lab[b[k] - 1] and lab[b[k + 1]]:
            lab[b[k]:b[k + 1]] = True
    mn = int(round(MIN_BURST * FSE))
    idx = np.flatnonzero(np.diff(lab.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [n]))
    runs = []
    for k in range(len(b) - 1):
        if lab[b[k]]:
            if (b[k + 1] - b[k]) < mn:
                lab[b[k]:b[k + 1]] = False
            else:
                runs.append((b[k], b[k + 1]))
    if m.sum() == 0:
        return dict(duty=np.nan, longest=0.0, n=0)
    long = max([(e2 - s) / FSE for s, e2 in runs if m[s:e2].mean() > 0.5] or [0.0])
    return dict(duty=float((lab & m).sum() / m.sum()), longest=float(long),
                n=len([r for r in runs if m[r[0]:r[1]].mean() > 0.5]))


print("=" * 124)
print("ITEM 4 -- BURST STRUCTURE ON THE AUDIBLE ENVELOPE, engaged <16 km/h.")
print("   pre-declared detector, verbatim: THR_ON = p95 of STOCK's engaged <16 km/h envelope,")
print("   THR_OFF = 0.70 x THR_ON (Schmitt), MIN_BURST %.2f s, MERGE_GAP %.2f s, analytic envelope."
      % (MIN_BURST, MERGE_GAP))
print("   🛑 THR_ON is set on STOCK and applied unchanged everywhere -- but the parked-ambient")
print("   audit shows the mic gain itself differs up to 12x between drives, so ACROSS-ROUTE duty")
print("   on this channel is contaminated by that offset.  The MANUAL column is the reference.")
print("=" * 124)
B4 = {}
for band in AUD:
    j = COL[band]
    thr = float(np.percentile(D['r97']['env'][msk('r97'), j], 95))
    print("\n  ---- %g-%g Hz   THR_ON = %.1f ----" % (band[0], band[1], thr))
    print("%-6s %-9s %10s %10s %12s %10s %12s" %
          ('route', 'build', 'ENG duty', 'MAN duty', 'eng/man', 'longest s', 'n bursts'))
    for t in TAGS:
        be = bursts(D[t]['env'][:, j], msk(t), thr, THR_FRAC * thr)
        bm = bursts(D[t]['env'][:, j], msk(t, False), thr, THR_FRAC * thr)
        B4.setdefault("%g-%g" % band, {})[t] = dict(eng=be, man=bm)
        print("%-6s %-9s %10.3f %10.3f %12s %10.2f %12d"
              % (t, A.NAMES[t], be['duty'], bm['duty'],
                 ("%.2f" % (be['duty'] / bm['duty'])) if bm['duty'] > 1e-6 else 'inf',
                 be['longest'], be['n']))

# ============================================================== ITEM 6  6-12 /s structure
print()
print("=" * 124)
print("ITEM 6 -- IS THERE 6-12 /s STRUCTURE IN THE ACOUSTIC ENVELOPE?")
print("   The operator: 'a RATCHET on top of a higher frequency vibration', 6-12 per second, and")
print("   'the vibration comes in and out'.  THREE wheel-rate instruments have failed to find it.")
print("   Here: envelope PSD inside engaged <16 km/h episodes, excess in 6-12 Hz over a local")
print("   background fitted on 2-5 and 14-25 Hz, versus (a) the rolling-manual arm and (b) a")
print("   PHASE-SHUFFLED surrogate that preserves the envelope's own spectrum.")
print("=" * 124)
NPER = 256              # 2.05 s -> 0.49 Hz resolution; resolves a 6-12 Hz envelope line


def env_excess(x, rng=None, nsur=0):
    """Excess of the 6-12 Hz envelope PSD over a log-log background fitted OUTSIDE that band."""
    f, p = signal.welch(x - x.mean(), fs=FSE, nperseg=NPER, noverlap=NPER // 2, detrend='linear')
    tgt = (f >= 6) & (f <= 12)
    bg = ((f >= 2) & (f < 5)) | ((f > 14) & (f <= 25))
    if tgt.sum() < 3 or bg.sum() < 5:
        return None
    cf = np.polyfit(np.log(f[bg]), np.log(p[bg]), 1)
    pred = np.exp(np.polyval(cf, np.log(f[tgt])))
    exc = float(np.mean(p[tgt] / pred))
    if not nsur:
        return exc
    sur = []
    for _ in range(nsur):
        X = np.fft.rfft(x - x.mean())
        ph = rng.uniform(0, 2 * np.pi, len(X))
        ph[0] = 0
        y = np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))
        sur.append(env_excess(y))
    sur = np.array([s for s in sur if s is not None])
    return exc, sur


rng = np.random.default_rng(19)
I6 = {}
for band in AUD:
    j = COL[band]
    print("\n  ---- %g-%g Hz ----" % band)
    print("%-6s %-9s %12s %12s %12s %22s" %
          ('route', 'build', 'ENG excess', 'MAN excess', 'eng/man', 'surrogate [2.5,97.5]'))
    for t in TAGS:
        row = []
        for eng in (True, False):
            rr = runs_of(msk(t, eng), 3.0)
            if not rr:
                row.append(None)
                continue
            vals = [env_excess(D[t]['env'][a:b, j]) for a, b in rr]
            vals = [v for v in vals if v is not None]
            row.append(float(np.mean(vals)) if vals else None)
        rr = runs_of(msk(t, True), 3.0)
        sur = []
        for a, b in rr[:6]:
            r = env_excess(D[t]['env'][a:b, j], rng, 25)
            if r and r[1].size:
                sur.append(r[1])
        sl, sh = (np.percentile(np.concatenate(sur), [2.5, 97.5]) if sur else (np.nan, np.nan))
        I6.setdefault("%g-%g" % band, {})[t] = dict(eng=row[0], man=row[1],
                                                    sur_lo=float(sl), sur_hi=float(sh))
        print("%-6s %-9s %12s %12s %12s %22s"
              % (t, A.NAMES[t],
                 ("%.3f" % row[0]) if row[0] else '-', ("%.3f" % row[1]) if row[1] else '-',
                 ("%.2f" % (row[0] / row[1])) if (row[0] and row[1]) else '-',
                 "[%.3f, %.3f]" % (sl, sh) if np.isfinite(sl) else '-'))
print()
print("  excess = mean(PSD in 6-12 Hz / log-log background fitted on 2-5 and 14-25 Hz).")
print("  1.0 = no 6-12 /s structure beyond the envelope's own smooth spectrum.  The surrogate")
print("  column is the SAME statistic on phase-randomised envelopes of the engaged arm.")

# ============================================================== ITEM 3  the ladder
print()
print("=" * 124)
print("ITEM 3 -- THE GAIN LADDER, on the quantities that survive the cabin offset")
print("=" * 124)
print("  (a) WHEEL RATE 21-28 Hz -- where the mode actually lives.  From the positive control:")
print("      it is a clean monotone ladder in BOTH duty and in-burst level.")
try:
    pc = json.load(open(os.path.join(A.HERE, '_scratch/out/_acoustic_poscontrol.json')))
    print("%-6s %-9s %8s %12s %14s" % ('route', 'build', 'gain', 'burst duty', 'in-burst level'))
    for t in ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']:
        w = pc['wheel_rate'][t]['eng']
        print("%-6s %-9s %8.0fx %12.3f %14.3f" % (t, A.NAMES[t], A.GAIN[t], w['duty'], w['lvl']))
except Exception as ex:
    print("   (positive-control JSON unavailable: %s)" % ex)
print()
print("  (b) ACOUSTIC, within-route engaged/manual duty -- the only acoustic ladder that is not")
print("      contaminated by the per-drive mic offset:")
print("%-6s %-9s %8s" % ('route', 'build', 'gain')
      + "".join("%14s" % ("%g-%g" % b) for b in AUD))
for t in TAGS:
    r = []
    for band in AUD:
        e = B4["%g-%g" % band][t]
        r.append(e['eng']['duty'] / e['man']['duty'] if e['man']['duty'] > 1e-6 else np.nan)
    print("%-6s %-9s %8.0fx" % (t, A.NAMES[t], A.GAIN[t])
          + "".join(("%14.2f" % x) if np.isfinite(x) else "%14s" % 'inf' for x in r))

json.dump({'item4': B4, 'item6': I6}, open(os.path.join(A.HERE, '_scratch/out/_acoustic_346.json'), 'w'),
          indent=1, default=float)
print("\n  wrote _scratch/out/_acoustic_346.json")
