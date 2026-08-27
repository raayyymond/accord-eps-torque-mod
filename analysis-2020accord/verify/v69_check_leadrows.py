#!/usr/bin/env python3
"""verify/v69_check_leadrows.py -- independent CHECK of the converged V69 candidate rows.

Answers, in order:
  1. reproduce/refute the two candidate rows
  2. is there a better SHAPE?  Pareto front over Y-only edits, then the X-moving family
  3. is the 1.836x grind #1 relaxation safe, judged against what V67 ALREADY delivers
  4. do the X breakpoints really have float mirrors (and the Y values really not)?

Every number is printed. Uses v69_surface_math's byte-read records and integer LERP.
"""
from __future__ import annotations
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

import struct
import sys

import v69_surface_math as V

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

B = V.B
STOCK = V.STOCK

# The four named points, expressed DIRECTLY in inner-axis counts (no deg/s conversion, so this
# check is independent of the unresolved counts-per-deg/s scale).
P_G1 = (7.2, 603)        # grind #1
P_G2 = (5.0, 1206)       # creep grind #2
P_HW = (93.35, 164)      # highway lane change
AXIS_MAX = 3000          # the top breakpoint; above it the LERP is flat


def Mx(kmh, ax, recs):
    return V.gain_q10(V.sc(kmh), ax, recs) / V.gain_q10(V.sc(kmh), ax, STOCK)


def rec(y0, y1, y2, y3, x=None, base=0):
    xs = STOCK[base][0] if x is None else x
    return (xs, (y0, y1, y2, y3))


def build(r0y, r1y, r0x=None, r1x=None):
    return (rec(*r0y, x=r0x, base=0), rec(*r1y, x=r1x, base=1), STOCK[2], STOCK[3])


def surface_extremes(recs, kstep=0.5, astep=5):
    """max and min multiplier over the whole reachable (speed, axis) domain."""
    hi = (0.0, None, None)
    lo = (9e9, None, None)
    k = 0.0
    while k <= 130.0:
        for a in range(0, AXIS_MAX + 200, astep):
            m = Mx(k, a, recs)
            if m > hi[0]:
                hi = (m, k, a)
            if m < lo[0]:
                lo = (m, k, a)
        k += kstep if k < 50 else 2.0
    return hi, lo


def row(name, recs, extremes=True):
    g1, g2, hw = Mx(*P_G1, recs), Mx(*P_G2, recs), Mx(*P_HW, recs)
    if extremes:
        hi, lo = surface_extremes(recs)
        return (name, g1, g2, hw, hi[0], hi[1], hi[2], lo[0], lo[1], lo[2])
    return (name, g1, g2, hw, None, None, None, None, None, None)


def show(rows):
    print(f"  {'candidate':44} {'g#1':>6} {'g#2':>6} {'hwy':>6} {'MAX':>6} {'@km/h,axis':>13} "
          f"{'MIN':>6} {'@km/h,axis':>13}")
    for r in rows:
        n, g1, g2, hw, mx, mk, ma, mn, nk, na = r
        print(f"  {n:44} {g1:6.3f} {g2:6.3f} {hw:6.3f} {mx:6.3f} "
              f"{f'{mk:.1f},{ma}':>13} {mn:6.3f} {f'{nk:.1f},{na}':>13}")


def main():
    print("=" * 118)
    print("1. THE TWO CANDIDATE ROWS -- REPRODUCED  [EVIDENCE: byte-read records + integer LERP]")
    print("   per-record inner axes, read from the image (rec0's X[2] IS 1400, the rest 1500):")
    for r in V.RECS10:
        print(f"     0x{r['rec']:05X} {r['kmh']:5.1f} km/h  X={r['xs']}  Y={r['ys']}")
    print()
    rows = [row("STOCK", STOCK)]
    for f2, tag in ((1.1, "f0=f1=2.0, f2=1.1"), (1.0, "f0=f1=2.0, f2=1.0  <-- the pick")):
        r0 = (6144, 6144, round(2322 * f2), 1536)
        r1 = (5122, 5122, round(2247 * f2), 1947)
        rows.append(row(f"{tag}   {r0} / {r1}"[:44], build(r0, r1)))
    rows.append(row("Design A  0xD2ABC 2561 -> 7051", V.DESIGN_A))
    show(rows)
    print("   lead's figures: 2.0/2.0/1.1 -> 1.851 / 1.340 / 2.000 ;"
          " 2.0/2.0/1.0 -> 1.835 / 1.267 / 2.000 ;")
    print("                   Design A    -> 2.006 / 1.250 / 2.753")

    # ---------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("2. IS THERE A BETTER SHAPE?  THE PARETO FRONT, Y-ONLY  [EVIDENCE]")
    print("""
   Both named points sit on the SAME linear segment [X1=400, X2~1450-1472], so the only lever
   that trades them is the WEIGHT each puts on Y[1] vs Y[2], and those weights are fixed by the
   axis positions. With max <= 2.00 forced, Y[1] is pinned at exactly 2x stock (the max is
   attained at the axis-400 breakpoint), which leaves rec0.Y[2] and rec1.Y[2] as the only free
   halfwords. rec1.Y[2] is the efficient one: it carries weight 0.7203 into grind #1 but only
   0.5 into creep grind #2 (the speed interpolation weights differ, 7.2 vs 5.0 km/h).
   Constraint added: multiplier >= 1.000 EVERYWHERE -- never REDUCE damping below stock, since
   V61 took Kd toward 0 and made grind #1 WORSE.""")
    print(f"   {'rec0.Y[2]':>10} {'rec1.Y[2]':>10} {'g#1':>7} {'g#2':>7} {'MAX':>7} {'MIN':>7}")
    front = []
    for d in range(2247, 5200, 100):
        r0 = (6144, 6144, 2322, 1536)
        r1 = (5122, 5122, d, 1947)
        rc = build(r0, r1)
        hi, lo = surface_extremes(rc, kstep=1.0, astep=10)
        g1, g2 = Mx(*P_G1, rc), Mx(*P_G2, rc)
        front.append((d, g1, g2, hi[0], lo[0]))
        print(f"   {2322:>10} {d:>10} {g1:7.3f} {g2:7.3f} {hi[0]:7.3f} {lo[0]:7.3f}"
              + ("   <-- the pick (rec1.Y[2] stock)" if d == 2247 else "")
              + ("   <-- C3 met, C4 BROKEN" if g1 >= 1.90 and g2 > 1.35 else ""))
    feas = [f for f in front if f[1] >= 1.90 and f[2] <= 1.35 and f[3] <= 2.0005]
    print(f"\n   feasible with C1(max<=2.00) + C3(g#1>=1.90) + C4(g#2<=1.35): "
          f"{'NONE -- JOINTLY INFEASIBLE' if not feas else feas}")
    best19 = min((f for f in front if f[1] >= 1.90), key=lambda f: f[2], default=None)
    if best19:
        print(f"   the Pareto point at exactly C3: rec1.Y[2] = {best19[0]} gives g#1 {best19[1]:.3f}"
              f" and the BEST creep grind #2 available at that dose is {best19[2]:.3f} -- "
              f"{best19[2] / 1.35:.2f}x over C4.")

    # ---------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("2b. THE X-MOVING FAMILY -- the one shape that CAN meet C1+C3+C4  [EVIDENCE]")
    print("""
   Pulling rec1's X[2] knee IN (1500 -> ~600) narrows the boosted band so it brackets grind #1's
   axis 603 and excludes creep grind #2's 1206. Y[2] must rise to compensate. This is the only
   family found that satisfies all three hard constraints.""")
    print(f"   {'rec1.X[2]':>10} {'rec1.Y[2]':>10} {'g#1':>7} {'g#2':>7} {'MAX':>7} {'MIN':>7} "
          f"{'slope':>8}")
    xbest = []
    for x2 in (500, 600, 700, 800, 1000):
        for z in range(2247, 6200, 50):
            r1x = (0, 400, x2, 3000)
            rc = build((6144, 6144, 2322, 1536), (5122, 5122, z, 1947), r1x=r1x)
            hi, lo = surface_extremes(rc, kstep=1.0, astep=10)
            if hi[0] > 2.0005:
                continue
            g1, g2 = Mx(*P_G1, rc), Mx(*P_G2, rc)
            # rate-axis slope at grind #1: |d gain / d axis| per 100 counts, normalised to stock
            gA = V.gain_q10(V.sc(7.2), 553, rc)
            gB = V.gain_q10(V.sc(7.2), 653, rc)
            sA = V.gain_q10(V.sc(7.2), 553, STOCK)
            sB = V.gain_q10(V.sc(7.2), 653, STOCK)
            slope = abs(gA - gB) / max(abs(sA - sB), 1)
            xbest.append((x2, z, g1, g2, hi[0], lo[0], slope))
        if xbest:
            ok = [b for b in xbest if b[0] == x2 and b[2] >= 1.90 and b[3] <= 1.35]
            pick = max(ok, key=lambda b: b[2]) if ok else \
                max([b for b in xbest if b[0] == x2], key=lambda b: b[2])
            print(f"   {pick[0]:>10} {pick[1]:>10} {pick[2]:7.3f} {pick[3]:7.3f} {pick[4]:7.3f} "
                  f"{pick[5]:7.3f} {pick[6]:8.2f}x" + ("   <-- MEETS C1+C3+C4" if ok else ""))
    print("""
   🛑 BUT PRICE IT BEFORE WANTING IT. This family works by making the gain a STEEP function of a
   RECTIFIED rate that sweeps at 2x the mode frequency -- exactly the parametric-pump geometry
   V58/V59/V60 chased for three builds. The slope column is the multiple of STOCK's own slope at
   grind #1's axis. It also moves an X breakpoint, which is the mirror-exposed half of the record
   (see section 4), and it is the most scale-dependent design possible: its whole benefit is that
   axis 603 and 1206 land on opposite sides of a knee, which is only true if the counts-per-deg/s
   scale is what the repo assumes.""")

    # ---------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("3. IS 1.836x AT GRIND #1 SAFE?  THE ARGUMENT IS EVIDENCE, NOT A DOSE MODEL")
    print("""
   V67/V68's arm is a FLAT 5244 while the stock LERP it replaces varies with speed. So V67 did
   NOT deliver 2.00x across grind #1's band -- it delivered 2.00x at ONE point and less below it.
   Grind #1 is a 2-5 mph symptom. What V67 actually delivered where the fix was MEASURED:""")
    print(f"   {'km/h':>7} {'mph':>6} {'stock LERP @axis 603':>21} {'V67 arm 5244':>13} "
          f"{'V67 mult':>9} {'V69 (2/2/1) mult':>17}")
    r69 = build((6144, 6144, 2322, 1536), (5122, 5122, 2247, 1947))
    for k in (0, 1.6, 3.2, 4.8, 6.4, 7.2, 8.0, 10.0, 14.4):
        st = V.gain_q10(V.sc(k), 603, STOCK)
        print(f"   {k:7.1f} {k / 1.609:6.1f} {st:21d} {V.ARM_GATE:13d} "
              f"{V.ARM_GATE / st:9.3f} {Mx(k, 603, r69):17.3f}")
    print("""
   ⇒ V67 delivered 1.71-1.94x across 0-7.2 km/h and grind #1 came back FIXED (18-22 Hz engaged
     0.524 [0.337, 0.804], and the orchestrator's independent pass 0.55 [0.35, 0.65] against a
     split-half null of [0.90, 1.12]). V69's 1.836x at grind #1's own point sits INSIDE the range
     V67 already flew and measured. This is the load-bearing argument and it needs no dose model.
   ⇒ For completeness, the log-linear dose model the ladder supports:""")
    import math
    for ref, lab in ((0.39, "Kd=2 pooled 0.39"), (0.55, "V67 0.55"), (0.58, "V67 CI upper 0.58")):
        expo = math.log(ref) / math.log(2.0)
        r = 1.836 ** expo
        d_null = 0.88 ** (1.0 / expo)
        print(f"     using {lab:20} exponent {expo:6.3f}: response at 1.836x = {r:.3f} "
              f"(null floor 0.88; dose needed to REACH the null = {d_null:.2f}x)")
    print("     ⇒ on every anchor, 1.836x lands far outside the null, and the dose that would")
    print("       merely reach it is 1.10-1.18x. The 8% cut from 2.00 is inside the CIs' own noise.")

    # ---------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("4. THE FLOAT-MIRROR CLAIM, CHECKED  [EVIDENCE: full-image scan, both endiannesses]")
    for a in (0xC661C, 0x55B5A):
        print(f"   at 0x{a:05X}: {B[a:a + 16].hex(' ')}")
        for o in range(0, 13, 2):
            f_le = struct.unpack_from("<f", B, a + o)[0]
            print(f"     +{o:2d} LE float = {f_le!r}")

    def scan_float(val):
        pat_le = struct.pack("<f", float(val))
        pat_be = struct.pack(">f", float(val))
        hits = []
        for pat, tag in ((pat_le, "LE"), (pat_be, "BE")):
            i = B.find(pat)
            while i != -1 and len(hits) < 40:
                if i % 4 == 0:
                    hits.append((i, tag))
                i = B.find(pat, i + 1)
        return hits

    print(f"\n   {'value':>8} {'role':>26} {'4-aligned float hits image-wide':>34}")
    for val, role in ((400, "X[1], all four records"), (1400, "rec0 X[2]"),
                      (1500, "rec1-3 X[2]"), (3000, "X[3], all four"),
                      (3072, "rec0 Y[0]/Y[1]"), (2561, "rec1 Y[0]/Y[1]"),
                      (2322, "rec0 Y[2]"), (2247, "rec1 Y[2]"),
                      (1536, "rec0 Y[3]"), (1947, "rec1 Y[3]"),
                      (6144, "PROPOSED rec0 Y[0]/Y[1]"), (5122, "PROPOSED rec1 Y[0]/Y[1]")):
        h = scan_float(val)
        print(f"   {val:>8} {role:>26}   " +
              (", ".join(f"0x{i:05X}({t})" for i, t in h[:6]) if h else "NONE"))
    print("""
   ⇒ read the X rows and the Y rows against each other in that table. The claim to check is
     'X has float mirrors, Y has none' -- if the X values hit and the Y values do not, the
     Y-only restriction is justified and the V27 int/float desync class stays out of scope.
     ⚠ A float constant equal to 400.0 or 3000.0 is NOT by itself a mirror of THIS table --
     those are common magnitudes. What would make it a mirror is a CLUSTERED run of them in
     table order. The hit addresses above are printed so that can be judged, not assumed.""")


if __name__ == "__main__":
    main()
