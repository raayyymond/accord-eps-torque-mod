#!/usr/bin/env python3
r"""FORWARD-PREDICT what gp-0x6b86 would return on the 427 (0x1AB) slot, route 0x9e.

Pre-registration for a c4 = 1.85x build on a V103 base (biquad armed ENGAGED-ONLY).

  ENGAGED : gp-0x6b86 = clamp( k*H(z)*gp-0x6b82 + gp-0x6b7e , +-12288 )
  MANUAL  : gp-0x6b86 = clamp(     gp-0x6b82 + gp-0x6b7e     , +-12288 )   <- literal bypass @0x35a86

The manual arm is a WITHIN-DRIVE POSITIVE CONTROL: it is k-independent by construction, so it
tests the tap and the reconstruction without testing the dose.  The engaged arm tests both.
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
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import run_clip_duty as RC
import run_clip_duty_all as RA

FS = 100.0
K = 1.85


def episodes(mask, t, min_s=1.0):
    out, i, n = [], 0, len(mask)
    dt = float(np.median(np.diff(t)))
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if (j - i) * dt >= min_s:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def biquad_armed(b82, eng, k):
    """Run H(z) only while engaged; hold state through manual (the state is not reset at 0x35a86)."""
    from assist_map_mirror import BQ_A1, BQ_A2, BQ_B1, BQ_C4
    c4 = BQ_C4 * k
    w1 = w2 = 0.0
    y = np.zeros(len(b82))
    for i, x in enumerate(b82):
        if eng[i]:
            w = c4 * (x / 1024.0) - BQ_A1 * w1 - BQ_A2 * w2
            y[i] = (w + BQ_B1 * w1 + w2) * 1024.0
            w2, w1 = w1, w
            y[i] = max(-12288.0, min(12288.0, y[i]))     # the +-12.0 float clamp
        else:
            y[i] = x                                      # bypass: mov r10,r6
    return y


def encode427(x, mul, sh, bits=10):
    return np.clip((np.abs(x).astype(int) * mul) >> sh, 0, (1 << bits) - 1)


def main():
    R = RA.run('9e')
    eng = R['eng']
    t = R['t']
    b82 = R['b82'].astype(float)
    b7e = R['b7e'].astype(float)
    y1 = biquad_armed(b82, eng, 1.00)          # V103 AS FLOWN
    yk = biquad_armed(b82, eng, K)             # the k=1.85 candidate
    m1 = np.clip(y1 + b7e, -12288, 12288)      # gp-0x6b86, as flown
    mk = np.clip(yk + b7e, -12288, 12288)      # gp-0x6b86, k=1.85
    a1, ak = np.abs(m1), np.abs(mk)

    print('=' * 100)
    print('PREDICTED |gp-0x6b86|, route 0x9e  (n=%d, engaged %d)' % (len(t), eng.sum()))
    print('=' * 100)
    for nm, v, sel in (('ENGAGED  k=1.00 (V103 as flown)', a1, eng),
                       ('ENGAGED  k=1.85 (candidate)   ', ak, eng),
                       ('MANUAL   (bypass, k-invariant)', a1, ~eng)):
        s = v[sel]
        print('  %s : p50=%6.0f p75=%6.0f p90=%6.0f p95=%6.0f p99=%6.0f max=%6.0f'
              % (nm, *np.percentile(s, [50, 75, 90, 95, 99]), s.max()))
    print('  ratio k=1.85 / k=1.00, engaged frames with |6b86|>=20 : p5=%.3f p50=%.3f p95=%.3f'
          % tuple(np.percentile((ak[eng & (a1 >= 20)] / np.maximum(a1[eng & (a1 >= 20)], 1e-9)),
                                [5, 50, 95])))

    # ---- 427 SIZING.  Current V103 form is |x|*5>>6 (=0.0781) -- sized for the SUM, not this lane.
    print('\n' + '=' * 100)
    print('427 SLOT SIZING (10-bit field, 0..1023).  GATE 3: size against THIS lane, not the clamp.')
    print('=' * 100)
    cands = [(5, 6, 'V103 as-flown (sized for gp-0x6b4c)'), (27, 5, 'x0.84375'),
             (55, 6, 'x0.859'), (3, 2, 'x0.75'), (11, 4, 'x0.6875'), (1, 1, 'x0.5')]
    print('  %-10s %-34s %8s %8s %8s %9s %10s' %
          ('mul>>sh', 'scale', 'p50', 'p90', 'p99', 'sat duty', 'LSB (ct)'))
    for mul, sh, nm in cands:
        w = encode427(mk[eng], mul, sh)
        print('  %-10s %-34s %8.0f %8.0f %8.0f %9.6f %10.2f'
              % ('%d>>%d' % (mul, sh), nm, *np.percentile(w, [50, 90, 99]),
                 (w >= 1023).mean(), (1 << sh) / mul))
    MUL, SH = 27, 5
    print('\n  RECOMMENDED: |gp-0x6b86| * %d >> %d  (x%.5f, LSB %.2f counts)' % (MUL, SH, MUL / (1 << SH), (1 << SH) / MUL))
    print('  V103 as-flown (5>>6) would put this lane at p99 = %d / 1023 -- %.1fx UNDER-RANGED.'
          % (np.percentile(encode427(mk[eng], 5, 6), 99),
             1023.0 / max(np.percentile(encode427(mk[eng], 5, 6), 99), 1)))

    # ---- DISCRIMINATION: can the wire separate k=1.85 from k=1.00 ?
    w1 = encode427(m1, MUL, SH)
    wk = encode427(mk, MUL, SH)
    d = np.abs(wk - w1)
    print('\n' + '=' * 100)
    print('DISCRIMINATION on the wire (k=1.85 vs k=1.00), engaged frames, %d>>%d encoding' % (MUL, SH))
    print('=' * 100)
    for thr in (1, 2, 5, 10, 25, 50, 100):
        print('   frames where the two builds differ by >= %3d wire codes : %6d / %d  (%.4f)'
              % (thr, (d[eng] >= thr).sum(), eng.sum(), (d[eng] >= thr).mean()))
    print('   median |difference| over engaged frames : %.0f wire codes' % np.median(d[eng]))

    # ---- PER-EPISODE PRE-REGISTRATION
    eps = episodes(eng, t)
    print('\n' + '=' * 100)
    print('PRE-REGISTRATION -- per engaged episode, route 0x9e geometry (%d episodes)' % len(eps))
    print('=' * 100)
    print('  %-4s %7s %8s | %-24s | %-24s' % ('ep', 'dur s', 'n', 'wire |6b86| k=1.85', 'wire |6b86| k=1.00'))
    print('  %-4s %7s %8s | %7s %7s %7s | %7s %7s %7s'
          % ('', '', '', 'p50', 'p90', 'p99', 'p50', 'p90', 'p99'))
    dt = float(np.median(np.diff(t)))
    rows = []
    for i, (a, b) in enumerate(eps):
        wa, wb = wk[a:b], w1[a:b]
        rows.append((np.percentile(wa, 50), np.percentile(wa, 90)))
        print('  %-4d %7.1f %8d | %7.0f %7.0f %7.0f | %7.0f %7.0f %7.0f'
              % (i, (b - a) * dt, b - a, *np.percentile(wa, [50, 90, 99]), *np.percentile(wb, [50, 90, 99])))
    r = np.array(rows)
    print('\n  ACROSS-EPISODE SPREAD at k=1.85 : p50 median %.0f, range [%.0f, %.0f] ; p90 median %.0f, range [%.0f, %.0f]'
          % (np.median(r[:, 0]), r[:, 0].min(), r[:, 0].max(),
             np.median(r[:, 1]), r[:, 1].min(), r[:, 1].max()))
    # episode bootstrap on the pooled p90
    rng = np.random.default_rng(0)
    blocks = [wk[a:b] for a, b in eps]
    bs = [np.percentile(np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), len(blocks))]), 90)
          for _ in range(2000)]
    print('  episode-bootstrap 95%% CI on the POOLED engaged p90 (k=1.85) : [%.0f, %.0f]  point %.0f'
          % (np.percentile(bs, 2.5), np.percentile(bs, 97.5), np.percentile(wk[eng], 90)))

    # ---- the k_effective estimator and its precision
    ok = eng & (np.abs(y1) >= 50)
    kest = np.abs(yk[ok]) / np.maximum(np.abs(y1[ok]), 1e-9)
    print('\n  k_effective = |6b86_measured - 6b7e| / |predicted H*6b82| , engaged, |H*6b82|>=50 (%d frames, %.1f%% of engaged)'
          % (ok.sum(), 100.0 * ok.sum() / eng.sum()))
    print('     truth 1.850 -> estimator p5=%.4f p50=%.4f p95=%.4f  (spread is pure quantisation+pedestal)'
          % tuple(np.percentile(kest, [5, 50, 95])))
    q = (1 << SH) / MUL
    print('     wire LSB %.2f ct; at the engaged p90 (%.0f ct) that is %.2f%% per frame, /sqrt(%d) -> %.4f%% pooled'
          % (q, np.percentile(ak[eng], 90), 100 * q / max(np.percentile(ak[eng], 90), 1), ok.sum(),
             100 * q / max(np.percentile(ak[eng], 90), 1) / np.sqrt(ok.sum())))

    print('\n  50 Hz NOTE: 0x1AB ships at 50 Hz on this route (32,388 frames / 647.8 s), so the tap')
    print('  aliases above 25 Hz. Amplitude/dose statistics are unaffected; a 6-9 Hz band estimate is fine.')


if __name__ == '__main__':
    main()
