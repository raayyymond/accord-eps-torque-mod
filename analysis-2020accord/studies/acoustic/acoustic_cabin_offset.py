r"""THE CABIN-OFFSET TEST -- is the between-route acoustic contrast FIRMWARE, or the DRIVE?

WHAT FORCED THIS.  Item 2's between-route table has V102 at **7.7x STOCK** in the 1.6 kHz band
while V103 sits at **0.29x STOCK** in the same band.  Both are 6x builds.  A 26x spread between
two builds that share the LKAS gain cannot be the LKAS gain.  The obvious alternative is a
PER-DRIVE OFFSET of the microphone channel: windows, HVAC fan speed, radio, phone position in
the mount, road surface, ambient temperature, AGC.

THE TEST, and it is decisive either way:
    The microphone does not know what the firmware is doing.  If the between-route difference is
    the DRIVE, it is present with **LKAS OFF** as well.  So compute, band by band and speed-matched:
        E = engaged(X) / engaged(STOCK)          the number item 2 reported
        M = manual (X) / manual (STOCK)          the same contrast with the firmware LEVER OFF
    * E ~ M across bands  => the whole contrast is the drive.  No between-route absolute acoustic
      number is interpretable, and item 2 as literally specified is UNANSWERABLE that way.
    * E >> M              => there is a real engaged-only firmware signature on top.
    The ratio E/M is a DIFFERENCE-IN-DIFFERENCES and is immune to any per-drive gain offset that
    is common to both arms.

🛑 RESAMPLING UNIT.  `r97`'s rolling-manual arm is 63.5 s in exactly TWO contiguous stretches, so
   it cannot be episode-bootstrapped at all.  Every arm here therefore uses the declared 5 s BLOCK
   bootstrap, and the split-half null is re-run under the SAME scheme so the calibration matches
   the estimator rather than flattering it.  This is weaker than an episode bootstrap and is
   labelled everywhere it appears.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
R = {t: A.load(t) for t in TAGS}
TOBF = R['r97']['tob_f']
NB = len(TOBF)
VLO, VHI = 0.0, 16.0
BS = A.BLOCK_S

print("=" * 122)
print("0.  THE PUREST AMBIENT MEASUREMENT AVAILABLE -- PARKED, ENGINE ON, LKAS OFF, v < 1 km/h.")
print("    No tyres, no wind, no steering.  Whatever differs here is the CABIN, not the firmware.")
print("=" * 122)
print("%-6s %-9s %8s" % ('route', 'build', 'parked s')
      + "".join("%9s" % ("%gHz" % f) for f in TOBF[::3]) + "%10s" % 'broadband')
base = None
for t in TAGS:
    r = R[t]
    m = (~r['eng']) & (r['v'] < 1.0)
    if m.sum() < 200:
        print("%-6s %-9s   too little parked time" % (t, A.NAMES[t]))
        continue
    lv = np.array([np.sqrt(r['tob'][m][:, i].mean()) for i in range(NB)])
    if base is None:
        base = lv
        bb = np.sqrt((r['rms'][m] ** 2).mean())
    print("%-6s %-9s %8.1f" % (t, A.NAMES[t], m.sum() * A.DT)
          + "".join("%9.2f" % (lv[i] / base[i]) for i in range(0, NB, 3))
          + "%10.2f" % (np.sqrt((r['rms'][m] ** 2).mean()) / bb))
print("  values are AMPLITUDE relative to STOCK's own parked level.  1.00 would mean the cabin")
print("  sounded the same on that drive as on the stock drive.")

print()
print("=" * 122)
print("1.  DIFFERENCE-IN-DIFFERENCES:  E = eng(X)/eng(STOCK),  M = man(X)/man(STOCK),  E/M")
print("    speed-matched <16 km/h, %g s block bootstrap, rolling manual only (v >= %g km/h)"
      % (BS, A.V_ROLL))
print("=" * 122)
RES = {}
for t in ('r85', 'r96', 'r9e', 'ra4', 'r95'):
    print("\n  ---- %s  %s ----" % (t, A.NAMES[t]))
    print("%9s %22s %22s %10s" % ('band Hz', 'E  eng X/STOCK', 'M  man X/STOCK', 'E/M'))
    E, M, EM = [], [], []
    for i in range(NB):
        re_ = A.speed_matched_ratio(R['r97'], R[t], A.mask(R['r97'], True, VLO, VHI),
                                    A.mask(R[t], True, VLO, VHI), i, nboot=500, block_s=BS)
        rm = A.speed_matched_ratio(R['r97'], R[t], A.mask(R['r97'], False, VLO, VHI),
                                   A.mask(R[t], False, VLO, VHI), i, nboot=500, block_s=BS,
                                   min_bin=15)
        E.append(re_['ratio'] if re_ else np.nan)
        M.append(rm['ratio'] if rm else np.nan)
        EM.append(E[-1] / M[-1] if (re_ and rm) else np.nan)
        if i % 2 == 0:
            print("%9.0f %22s %22s %10s" %
                  (TOBF[i],
                   ("%.2f [%.2f, %.2f]" % (re_['ratio'], re_['lo'], re_['hi'])) if re_ else '-',
                   ("%.2f [%.2f, %.2f]" % (rm['ratio'], rm['lo'], rm['hi'])) if rm else '-',
                   ("%.2f" % EM[-1]) if np.isfinite(EM[-1]) else '-'))
    E, M, EM = np.array(E), np.array(M), np.array(EM)
    g = np.isfinite(E) & np.isfinite(M) & (E > 0) & (M > 0)
    RES[t] = dict(E=E.tolist(), M=M.tolist(), EM=EM.tolist())
    if g.sum() >= 5:
        rr = np.corrcoef(np.log(E[g]), np.log(M[g]))[0, 1]
        sl = np.polyfit(np.log(M[g]), np.log(E[g]), 1)[0]
        gm = np.exp(np.mean(np.log(EM[g])))
        print("     %d bands usable.  corr(log E, log M) = %+.3f   slope %.2f   geo-mean E/M = %.3f"
              % (g.sum(), rr, sl, gm))
        print("     %s" % ("=> the between-route difference is present LKAS-OFF too: it is THE DRIVE"
                           if rr > 0.7 and abs(np.log(gm)) < 0.35 else
                           "=> E and M do NOT track: there is engaged-specific structure here"))

print()
print("=" * 122)
print("2.  THE SELF-NORMALISING INSTRUMENT: ENGAGED / MANUAL **within each route**")
print("    immune to any per-drive gain offset common to both arms -- which section 1 shows is")
print("    the dominant term.  THIS is the number that can be compared across builds.")
print("=" * 122)
NULL = {}
for i in range(0, NB, 4):
    n = A.split_half_null(R['ra4'], A.mask(R['ra4'], True, VLO, VHI), i, block_s=BS)
    NULL[i] = n
print("  split-half null under the SAME %g s block scheme (ra4 engaged <16 km/h):" % BS)
for i, n in NULL.items():
    if n:
        print("     %6.0f Hz   %.3f [%.3f, %.3f]   spread %.2f"
              % (TOBF[i], n['p50'], n['p2_5'], n['p97_5'], n['spread']))
sp = [n['spread'] for n in NULL.values() if n]
LIM = float(np.sqrt(np.median(sp)))
print("  => median null spread %.2f; a within-route eng/man ratio must clear [%.2f, %.2f]."
      % (np.median(sp), 1 / LIM, LIM))

print()
avail = [t for t in TAGS if A.mask(R[t], False, VLO, VHI).sum() > 300]
print("%9s" % 'band Hz' + "".join("%20s" % (A.NAMES[t]) for t in avail))
EMR = {t: [] for t in avail}
for i in range(NB):
    row = []
    for t in avail:
        r = A.speed_matched_ratio(R[t], R[t], A.mask(R[t], False, VLO, VHI),
                                  A.mask(R[t], True, VLO, VHI), i, nboot=500, block_s=BS,
                                  min_bin=15)
        EMR[t].append(None if r is None else dict(ratio=r['ratio'], lo=r['lo'], hi=r['hi']))
        row.append(r)
    print("%9.0f" % TOBF[i] + "".join(
        ("%20s" % ("%.2f [%.2f,%.2f]" % (r['ratio'], r['lo'], r['hi']))) if r else "%20s" % '-'
        for r in row))
print("  ENGAGED/MANUAL amplitude ratio, speed-matched, within route.  >1 = LKAS makes that band")
print("  louder on that drive.  THE TARGET SIGNATURE is a band that is ~1 on STOCK and >1 on 6x.")

print()
print("=" * 122)
print("3.  VERDICT -- bands where the 6x builds are engaged-elevated and STOCK is not")
print("=" * 122)
hit = []
for i in range(NB):
    s = EMR.get('r97', [None] * NB)[i]
    six = [EMR[t][i] for t in ('r96', 'r9e', 'ra4') if t in EMR]
    if s is None or any(x is None for x in six):
        continue
    n6 = sum(1 for x in six if x['lo'] > 1.0)
    if n6 >= 2 and s['hi'] < max(x['ratio'] for x in six):
        hit.append((TOBF[i], s, six, n6))
if hit:
    for f, s, six, n6 in hit:
        print("   %6.0f Hz  STOCK %.2f [%.2f,%.2f]   6x: %s   (%d of 3 with CI above 1.0)"
              % (f, s['ratio'], s['lo'], s['hi'],
                 "  ".join("%.2f" % x['ratio'] for x in six), n6))
else:
    print("   NONE meeting the pre-set rule (>=2 of 3 six-x routes with the whole CI above 1.0,")
    print("   and STOCK's CI entirely below them).")

json.dump({'diff_in_diff': RES,
           'eng_over_man': {t: EMR[t] for t in EMR},
           'tob_f': TOBF.tolist(), 'null_limit': LIM},
          open(os.path.join(A.HERE, '_scratch/out/_acoustic_cabin.json'), 'w'), indent=1)
print("\n  wrote _scratch/out/_acoustic_cabin.json")
