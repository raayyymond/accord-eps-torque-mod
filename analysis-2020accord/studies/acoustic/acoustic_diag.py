r"""DIAGNOSTIC -- two things item 2 threw up that must be resolved before ANY number is quoted.

(a) STOCK's rolling-manual arm produced NO estimate at all.  Why?  Episode count, or bins?
(b) The three 6x routes DISAGREE IN DIRECTION against stock -- V102 is up to 7x UP at 1.6 kHz
    while V103 is 3-8x DOWN in the same bands.  Three builds that are all "6x" cannot differ
    from each other by 20x in the audible range because of firmware.  The obvious explanation is
    a PER-DRIVE CABIN/MIC OFFSET (windows, HVAC fan, radio, road surface, phone mount, AGC).

    THE TEST: if it is a per-drive offset, the MANUAL arm carries the SAME offset, because the
    microphone does not know what the firmware is doing.  So plot ENGAGED/STOCK against
    MANUAL/STOCK band by band.  If they lie on the identity line, the between-route contrast is
    entirely cabin condition and NO between-route absolute acoustic number is interpretable.
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
VLO, VHI = 0.0, 16.0

print("=" * 120)
print("(a) EPISODE CENSUS -- why some cells are empty.  min episode %.1f s, min %d frames/bin."
      % (A.MIN_EP, A.MIN_BIN))
print("=" * 120)
print("%-6s %-9s %26s %26s %26s" % ('route', 'build', 'ENGAGED <16', 'MANUAL <16 (all)',
                                    'MANUAL <16 ROLLING >=2 km/h'))
for t in TAGS:
    r = R[t]
    row = []
    for m in (A.mask(r, True, VLO, VHI), A.mask(r, False, VLO, VHI, rolling_manual=False),
              A.mask(r, False, VLO, VHI)):
        e = A.episodes(m)
        row.append("%2d eps / %6.1f s / %6.1f s" %
                   (len(e), m.sum() * A.DT, sum(b - a for a, b in e) * A.DT))
    print("%-6s %-9s %26s %26s %26s" % (t, A.NAMES[t], *row))
print("  'x eps / y s masked / z s inside episodes'.  An arm with <3 episodes returns nothing.")

print()
print("  SPEED-BIN OCCUPANCY (frames per 2 km/h bin), engaged | rolling-manual:")
edges = np.arange(VLO, VHI + A.SPEED_BIN, A.SPEED_BIN)
print("%-6s %-9s %s" % ('route', 'arm', "".join("%9s" % ("%g-%g" % (edges[i], edges[i + 1]))
                                                for i in range(len(edges) - 1))))
for t in TAGS:
    r = R[t]
    for lab, m in (('eng', A.mask(r, True, VLO, VHI)), ('man', A.mask(r, False, VLO, VHI))):
        eps = A.episodes(m)
        if not eps:
            print("%-6s %-9s  (no episodes)" % (t, lab))
            continue
        v = np.concatenate([r['v'][a:b] for a, b in eps])
        c, _ = np.histogram(v, edges)
        print("%-6s %-9s %s" % (t, lab, "".join("%9d" % x for x in c)))

print()
print("=" * 120)
print("(b) IS THE BETWEEN-ROUTE CONTRAST A FIRMWARE EFFECT, OR A PER-DRIVE CABIN/MIC OFFSET?")
print("=" * 120)
print("    If cabin, the MANUAL arm carries the same offset as the ENGAGED arm.")
print("    Both arms are speed-matched to STOCK independently, same estimator.")
print()
print("%9s %26s %26s %12s" % ('band Hz', 'ENGAGED  X/STOCK', 'MANUAL(roll) X/STOCK', 'eng/man'))
for t in ('r96', 'r9e', 'ra4', 'r85'):
    print("  ---- %s (%s) ----" % (t, A.NAMES[t]))
    E, M = [], []
    for i in range(len(TOBF)):
        re_ = A.speed_matched_ratio(R['r97'], R[t], A.mask(R['r97'], True, VLO, VHI),
                                    A.mask(R[t], True, VLO, VHI), i, nboot=400)
        rm = A.speed_matched_ratio(R['r97'], R[t], A.mask(R['r97'], False, VLO, VHI),
                                   A.mask(R[t], False, VLO, VHI), i, nboot=400, min_bin=15)
        E.append(re_['ratio'] if re_ else np.nan)
        M.append(rm['ratio'] if rm else np.nan)
        if i % 3 == 0:
            print("%9.0f %26s %26s %12s" %
                  (TOBF[i],
                   ("%.2f [%.2f, %.2f]" % (re_['ratio'], re_['lo'], re_['hi'])) if re_ else '-',
                   ("%.2f [%.2f, %.2f]" % (rm['ratio'], rm['lo'], rm['hi'])) if rm else '-',
                   ("%.2f" % (re_['ratio'] / rm['ratio'])) if (re_ and rm) else '-'))
    E, M = np.array(E), np.array(M)
    g = np.isfinite(E) & np.isfinite(M) & (E > 0) & (M > 0)
    if g.sum() >= 5:
        r = np.corrcoef(np.log(E[g]), np.log(M[g]))[0, 1]
        sl = np.polyfit(np.log(M[g]), np.log(E[g]), 1)[0]
        print("     across %d bands: corr(log engaged-ratio, log manual-ratio) = %.3f, slope %.2f"
              % (g.sum(), r, sl))
        print("     geometric mean eng/man = %.3f  (1.0 => the whole between-route difference is"
              % np.exp(np.mean(np.log(E[g] / M[g]))))
        print("     present with LKAS OFF as well, i.e. it is NOT the firmware)")
    else:
        print("     manual arm too thin on one side to run this test (%d usable bands)" % g.sum())
