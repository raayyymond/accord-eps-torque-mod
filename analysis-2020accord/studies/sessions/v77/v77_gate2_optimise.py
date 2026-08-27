"""v77 GATE 2 -- constrained search over the FULL FactorE knot space + FactorC Y[0].

Answers the brief's own question honestly: what is the BEST surface with NO flat non-zero segment,
and how much symptom damping does that constraint actually cost?

CONSTRAINTS (all enforced, none assumed):
  * Y[0] = 0                                   (preserve the low-rate dead zone / zero at rest)
  * X strictly increasing, Y non-decreasing     (record wellformedness)
  * dose(r) <= 512 for all r                    (the ceiling FLOOR -- the kit's no-clip rule)
  * every value written is int16 and >= 0
SCORING:
  * N_peak                      -- the small-signal / chatter risk axis (V74 0.560 clean, V75 1.464 fault)
  * N(300) N(461) N(800)        -- the symptom band, 1.8-4.7 sigma of the measured rate signal
  * flat_ct                     -- longest run of |rate| (counts) over which the dose is constant & non-zero
  * entries                     -- Rice-predicted plateau/knee entries on route-5d exposure
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
import math
import itertools
from v77_gate2_describing_function import Surface, N_closed, CX, V74, V75, deg_s

SIGMA = 169.6
N_V75_ENTRIES, X1_V75 = 282, 200
CEIL = 512


def crossings(a):
    return N_V75_ENTRIES * math.exp(-(a ** 2 - X1_V75 ** 2) / (2 * SIGMA ** 2))


def mk(cy0, ex, ey):
    return Surface("cand", CX, [cy0, 234, 429, 908], list(ex), list(ey))


def flat_run(s, hi=2600):
    best, cur, prev = 0, 0, None
    for r in range(0, hi):
        d = s.g(r)
        if d > 0 and d == prev:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
        prev = d
    return best


def npeak(s):
    return max(N_closed(s, A) for A in range(5, 2001, 5))


def valid(cy0, ex, ey):
    if ey[0] != 0:
        return False
    if not all(ex[i] < ex[i + 1] for i in range(3)):
        return False
    if not all(ey[i] <= ey[i + 1] for i in range(3)):
        return False
    if (cy0 * max(ey)) >> 10 > CEIL:
        return False
    return True


# --------------------------------------------------------------------------------------------
# SEARCH 1 -- NO FLAT SEGMENT allowed below 2,600 counts (the whole reachable band)
# --------------------------------------------------------------------------------------------
print("=" * 112)
print("SEARCH 1 -- best surface with NO flat non-zero segment below 2,600 counts of rate")
print("=" * 112)
best = []
CY0S = [429, 500, 566, 650, 750, 850, 972]
X1S = [100, 150, 200, 250, 300, 400, 500]
Y1S = [60, 100, 150, 200, 250, 300, 400]
X2S = [500, 600, 700, 800, 1000, 1200, 1600, 2000, 2500]
Y2S = [300, 400, 450, 500, 539, 620, 700]
X3S = [2500, 3000, 4000]
for cy0, x1, y1, x2, y2, x3 in itertools.product(CY0S, X1S, Y1S, X2S, Y2S, X3S):
    if not (x1 < x2 < x3):
        continue
    y3 = min(927, (CEIL * 1024) // cy0)
    if y3 < y2:
        continue
    ex, ey = [12, x1, x2, x3], [0, y1, y2, y3]
    if not valid(cy0, ex, ey):
        continue
    s = mk(cy0, ex, ey)
    f = flat_run(s)
    if f > 12:                       # allow only integer-truncation flats, not a design plateau
        continue
    np_ = npeak(s)
    best.append((min(N_closed(s, 300), N_closed(s, 461), N_closed(s, 800)), np_, f, cy0, ex, ey, s))
best.sort(key=lambda t: -t[0])
print(f"  {len(best)} admissible no-flat surfaces.  Top 12 by min(N300,N461,N800):")
print(f"  {'minN':>6s} {'Npk':>6s} {'xV74':>5s} {'flat':>5s} {'CY0':>4s} {'E X':>26s} {'E Y':>24s}"
      f" {'N140':>6s} {'N300':>6s} {'N461':>6s} {'N800':>6s} {'N1184':>6s} {'entr':>6s}")
for mn, np_, f, cy0, ex, ey, s in best[:12]:
    print(f"  {mn:6.3f} {np_:6.3f} {np_/0.5598:5.2f} {f:5d} {cy0:4d} {str(ex):>26s} {str(ey):>24s}"
          f" {N_closed(s,140):6.3f} {N_closed(s,300):6.3f} {N_closed(s,461):6.3f} {N_closed(s,800):6.3f}"
          f" {N_closed(s,1184):6.3f} {crossings(ex[1]):6.1f}")

print()
print("  For comparison, the PLATEAU surfaces:")
for nm, s in (("V74", V74), ("V75", V75),
              ("V77-a C566 X1=400", mk(566, [12, 400, 2500, 4000], [0, 539, 539, 927])),
              ("V77-b C566 X1=525", mk(566, [12, 525, 2500, 4000], [0, 539, 539, 927]))):
    print(f"  {'':6s} {npeak(s):6.3f} {npeak(s)/0.5598:5.2f} {flat_run(s):5d} {s.c_creep():4d}"
          f" {str(s.EX):>26s} {str(s.EY):>24s}"
          f" {N_closed(s,140):6.3f} {N_closed(s,300):6.3f} {N_closed(s,461):6.3f} {N_closed(s,800):6.3f}"
          f" {N_closed(s,1184):6.3f} {crossings(s.EX[1]):6.1f}   <- {nm}")

# --------------------------------------------------------------------------------------------
# SEARCH 2 -- the cost of the no-flat constraint, at MATCHED peak gain
# --------------------------------------------------------------------------------------------
print()
print("=" * 112)
print("SEARCH 2 -- the PRICE of 'no flat segment', at MATCHED N_peak")
print("  For each target N_peak, the best no-flat surface vs the best plateau surface.")
print("=" * 112)
plateau_pool = []
for cy0 in (429, 500, 566):
    for x1 in range(100, 1201, 25):
        s = mk(cy0, [12, x1, 2500, 4000], [0, 539, 539, 927])
        if valid(cy0, s.EX, s.EY):
            plateau_pool.append((npeak(s), s))
print(f"  {'target Npk':>11s} | {'no-flat  N300  N461  N800  N1184':>40s} | "
      f"{'plateau  N300  N461  N800  N1184':>40s}")
for tgt in (0.40, 0.56, 0.74, 1.00, 1.46):
    nf = [t for t in best if t[1] <= tgt * 1.02]
    pl = [t for t in plateau_pool if t[0] <= tgt * 1.02]
    if not nf or not pl:
        continue
    nf_b = max(nf, key=lambda t: min(N_closed(t[6], 300), N_closed(t[6], 461), N_closed(t[6], 800)))
    pl_b = max(pl, key=lambda t: min(N_closed(t[1], 300), N_closed(t[1], 461), N_closed(t[1], 800)))
    a, b = nf_b[6], pl_b[1]
    print(f"  {tgt:11.2f} | {N_closed(a,300):13.3f} {N_closed(a,461):5.3f} {N_closed(a,800):5.3f}"
          f" {N_closed(a,1184):5.3f} | {N_closed(b,300):13.3f} {N_closed(b,461):5.3f}"
          f" {N_closed(b,800):5.3f} {N_closed(b,1184):5.3f}"
          f"   [plateau/no-flat at 461 = {N_closed(b,461)/N_closed(a,461):.2f}x]")
