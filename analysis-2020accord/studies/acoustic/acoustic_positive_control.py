r"""THE POSITIVE CONTROL -- can the microphone see the 21-28 Hz mode AT ALL?

WHY THIS COMES BEFORE ANY MORE ACOUSTIC CLAIMS.  Item 2 returned a clean null across 100 Hz - 8 kHz.
A null is only informative if the instrument is DEMONSTRABLY SENSITIVE.  This project has been
burned by exactly the opposite: V64's null was on the GATE, not the hypothesis; V68's detector had
never once been non-zero.  [accord-v64-null-is-on-the-gate, accord-v68-detector-still-zero]

The wheel-rate channel already separates stock from 6x on the 21-28 Hz mode almost perfectly:
burst duty 0.056 stock vs 0.93-0.95 at 6x, longest burst 0.69 s vs 7-14 s.  So:

  LEG 1  Re-run the pre-declared burst detector on the WHEEL-RATE 21-28 Hz envelope.
         If it does not reproduce those numbers, MY DETECTOR is wrong and nothing else counts.
  LEG 2  Run the identical detector on the ACOUSTIC 21-28 Hz envelope.
         Mic sees it  => the acoustic channel is calibrated, and the 100 Hz - 8 kHz null is a
                         real negative result about the audible range.
         Mic blind    => the acoustic null is UNINTERPRETABLE, not negative, and I must say so.
  LEG 3  Cross-correlate the two envelopes (brief item 5), with a phase-shuffled surrogate null.

⚠ THE STANDING CAVEAT, restated because it applies to LEG 2 in full force: below ~100 Hz a
  phone-class MEMS mic measures STRUCTURE-BORNE pressure as much as airborne sound.  A 21-28 Hz
  "acoustic" reading is a second, differently-aliased look at the SAME mode -- it is a CALIBRATION
  of the channel, NOT independent confirmation of the mode.  That is precisely what makes it a
  good positive control and a bad piece of evidence.

DETECTOR, pre-declared and used verbatim for every arm (from the wheel-rate work):
    THR_ON  = p95 of STOCK's engaged <16 km/h envelope       (one number, set once, on stock)
    THR_OFF = 0.70 x THR_ON                                  (Schmitt)
    MIN_BURST 0.25 s   MERGE_GAP 0.15 s   true analytic (Hilbert) envelope
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
VLO, VHI = 0.0, 16.0
FS_CAN = 101.14792783296437
BAND = (21.0, 28.0)
MIN_BURST, MERGE_GAP, THR_FRAC = 0.25, 0.15, 0.70


def analytic_env(x, fs, lo, hi):
    """TRUE analytic envelope of the band -- zero-phase Butterworth, then |hilbert|."""
    sos = signal.butter(4, [lo / (fs / 2), hi / (fs / 2)], btype='band', output='sos')
    y = signal.sosfiltfilt(sos, np.nan_to_num(x - np.nanmean(x)))
    return np.abs(signal.hilbert(y))


def bursts(env, m, fs, thr_on, thr_off):
    """Schmitt-trigger burst statistics over the masked frames only.

    Bursts are found on the FULL series and then intersected with the mask, so a burst is not
    manufactured by the mask's own edges.  Returns duty within the mask, in-burst level, and the
    longest burst that lies inside the mask.
    """
    on = env >= thr_on
    st = env >= thr_off
    lab = np.zeros(len(env), bool)
    i = 0
    n = len(env)
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
    # merge gaps shorter than MERGE_GAP
    g = int(round(MERGE_GAP * fs))
    idx = np.flatnonzero(np.diff(lab.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [n]))
    for k in range(1, len(b) - 2):
        if (not lab[b[k]]) and (b[k + 1] - b[k]) <= g and lab[b[k] - 1] and lab[b[k + 1]]:
            lab[b[k]:b[k + 1]] = True
    # drop bursts shorter than MIN_BURST
    mn = int(round(MIN_BURST * fs))
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
        return dict(duty=np.nan, lvl=np.nan, longest=np.nan, n=0, sec=0.0)
    duty = float((lab & m).sum() / m.sum())
    inb = env[lab & m]
    long = max([(min(e, len(m)) - s) / fs for s, e in runs
                if m[s:e].mean() > 0.5] or [0.0])
    return dict(duty=duty, lvl=float(inb.mean()) if inb.size else np.nan,
                longest=float(long), n=len([r for r in runs if m[r[0]:r[1]].mean() > 0.5]),
                sec=float(m.sum() / fs))


# ---------------------------------------------------------------- load both channels
D = {}
for t in TAGS:
    R = A.load(t)
    e = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_env.npz' % t))
    te, ev, sp = e['t'].astype(float), e['env'].astype(float), e['splice'].astype(bool)
    fre = float(e['fr'][0])
    bidx = int(np.argmin(np.abs(e['env_f'][:, 0] - BAND[0]) + np.abs(e['env_f'][:, 1] - BAND[1])))
    # CAN-side 21-28 Hz envelope on the CAN grid, then onto the 125 Hz acoustic grid
    wr = analytic_env(R['rate_f'], FS_CAN, *BAND)
    eng = np.interp(te, R['can_t'], R['can_eng'].astype(float)) > 0.5
    v = np.interp(te, R['can_t'], R['can_v'])
    D[t] = dict(t=te, fs=fre, aco=ev[:, bidx], all_env=ev, env_f=e['env_f'],
                wr=np.interp(te, R['can_t'], wr), eng=eng, v=v, ok=~sp, R=R)
    print("  %-5s %s: %d env frames @ %.1f Hz, band col %d = %s Hz, %.1f%% splice-flagged"
          % (t, A.NAMES[t], len(te), fre, bidx, e['env_f'][bidx], 100 * sp.mean()))

FS = D['r97']['fs']


def msk(t, engaged=True, vlo=VLO, vhi=VHI, rolling=True):
    d = D[t]
    m = (d['eng'] if engaged else ~d['eng']) & (d['v'] >= vlo) & (d['v'] < vhi) & d['ok']
    if not engaged and rolling:
        m = m & (d['v'] >= A.V_ROLL)
    return m


print()
print("=" * 122)
print("LEG 1 -- DOES MY DETECTOR REPRODUCE THE KNOWN WHEEL-RATE RESULT?")
print("   pre-declared: THR_ON = p95 of STOCK engaged <16 km/h envelope, THR_OFF = 0.70 x THR_ON,")
print("   MIN_BURST %.2f s, MERGE_GAP %.2f s, analytic envelope.  Target: stock duty ~0.056," % (MIN_BURST, MERGE_GAP))
print("   6x duty 0.93-0.95, longest 0.69 s vs 7-14 s.")
print("=" * 122)
THR_WR = float(np.percentile(D['r97']['wr'][msk('r97')], 95))
print("  THR_ON (wheel rate, from STOCK engaged <16 km/h p95) = %.4f\n" % THR_WR)
print("%-6s %-9s %10s %9s %10s %10s %9s | %9s %10s" %
      ('route', 'build', 'eng s', 'DUTY', 'in-burst', 'longest s', 'n', 'MAN duty', 'man long'))
WR = {}
for t in TAGS:
    be = bursts(D[t]['wr'], msk(t), FS, THR_WR, THR_FRAC * THR_WR)
    bm = bursts(D[t]['wr'], msk(t, False), FS, THR_WR, THR_FRAC * THR_WR)
    WR[t] = dict(eng=be, man=bm)
    print("%-6s %-9s %10.1f %9.3f %10.4f %10.2f %9d | %9.3f %10.2f" %
          (t, A.NAMES[t], be['sec'], be['duty'], be['lvl'], be['longest'], be['n'],
           bm['duty'], bm['longest']))

print()
print("=" * 122)
print("LEG 2 -- THE SAME DETECTOR ON THE **ACOUSTIC** 21-28 Hz ENVELOPE")
print("=" * 122)
THR_AC = float(np.percentile(D['r97']['aco'][msk('r97')], 95))
print("  THR_ON (acoustic, from STOCK engaged <16 km/h p95) = %.4f\n" % THR_AC)
print("%-6s %-9s %10s %9s %10s %10s %9s | %9s %10s" %
      ('route', 'build', 'eng s', 'DUTY', 'in-burst', 'longest s', 'n', 'MAN duty', 'man long'))
AC = {}
for t in TAGS:
    be = bursts(D[t]['aco'], msk(t), FS, THR_AC, THR_FRAC * THR_AC)
    bm = bursts(D[t]['aco'], msk(t, False), FS, THR_AC, THR_FRAC * THR_AC)
    AC[t] = dict(eng=be, man=bm)
    print("%-6s %-9s %10.1f %9.3f %10.4f %10.2f %9d | %9.3f %10.2f" %
          (t, A.NAMES[t], be['sec'], be['duty'], be['lvl'], be['longest'], be['n'],
           bm['duty'], bm['longest']))

print()
print("  SIDE BY SIDE -- the separation each channel achieves, stock vs the three 6x builds:")
print("%-14s %12s %12s %12s %12s %12s" % ('channel', 'STOCK duty', 'V102', 'V103', 'V104', 'spread'))
for nm, S in (('wheel rate', WR), ('ACOUSTIC', AC)):
    d = [S[t]['eng']['duty'] for t in ('r97', 'r96', 'r9e', 'ra4')]
    print("%-14s %12.3f %12.3f %12.3f %12.3f %12s"
          % (nm, *d, "%.1fx" % (np.mean(d[1:]) / max(d[0], 1e-6))))

print()
print("=" * 122)
print("LEG 3 -- DO THE TWO ENVELOPES TRACK?  (brief item 5)")
print("   Pearson r on log envelopes inside engaged <16 km/h, against a PHASE-SHUFFLED surrogate")
print("   null that preserves each envelope's own spectrum.")
print("=" * 122)


def surrogate(x, rng):
    X = np.fft.rfft(x - x.mean())
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))


print("%-6s %-9s %8s %10s %20s %12s" %
      ('route', 'build', 'n s', 'r(log)', 'surrogate [2.5,97.5]', 'lag@peak s'))
X = {}
rng = np.random.default_rng(7)
for t in TAGS:
    m = msk(t)
    eps = [(a, b) for a, b in A.episodes(m, min_s=4.0)]
    if not eps:
        print("%-6s %-9s   no episode >= 4 s" % (t, A.NAMES[t]))
        continue
    a = np.concatenate([np.log(np.maximum(D[t]['aco'][s:e], 1e-12)) for s, e in eps])
    w = np.concatenate([np.log(np.maximum(D[t]['wr'][s:e], 1e-12)) for s, e in eps])
    r = float(np.corrcoef(a, w)[0, 1])
    nul = []
    for _ in range(200):
        nul.append(np.corrcoef(surrogate(a, rng), w)[0, 1])
    lo, hi = np.percentile(nul, [2.5, 97.5])
    # lag: cross-correlate the longest episode
    s, e = max(eps, key=lambda p: p[1] - p[0])
    aa = D[t]['aco'][s:e] - D[t]['aco'][s:e].mean()
    ww = D[t]['wr'][s:e] - D[t]['wr'][s:e].mean()
    cc = signal.correlate(aa, ww, mode='same') / (np.std(aa) * np.std(ww) * len(aa))
    lag = (np.argmax(cc) - len(cc) // 2) / FS
    X[t] = dict(r=r, lo=float(lo), hi=float(hi), lag=float(lag), sec=float(m.sum() / FS))
    print("%-6s %-9s %8.1f %10.3f %20s %12.3f"
          % (t, A.NAMES[t], m.sum() / FS, r, "[%.3f, %.3f]" % (lo, hi), lag))

json.dump({'wheel_rate': {t: {k: WR[t][k] for k in WR[t]} for t in WR},
           'acoustic': {t: {k: AC[t][k] for k in AC[t]} for t in AC},
           'coupling': X, 'thr_wr': THR_WR, 'thr_ac': THR_AC},
          open(os.path.join(A.HERE, '_scratch/out/_acoustic_poscontrol.json'), 'w'), indent=1, default=float)
print("\n  wrote _scratch/out/_acoustic_poscontrol.json")
