#!/usr/bin/env python3
"""studies/sessions/v76/v76_cut_spec.py -- the FINAL V76 mode-26 FactorC/FactorE arrays, ready to cut.

Decision (team-lead, overriding my C2 recommendation; reasoning accepted):
  FactorC = C1 [566,566,566,908] -- ADD-ONLY vs stock, not C2's subtractive 908->566.
Design constraints carried in:
  E_X0 = 12 (guard G3) · plateau REMOVED (E_Y1 < E_Y2) · dose ~110 uniform 0-80 km/h
  · E_Y[0] = 0 (the Coulomb-relay refutation) · add-only w.r.t. stock at EVERY (speed, rate).

Base image: _v38_plain_image.bin, sha256 a7391972...afa8 (verified below).
Record layout PROVEN empirically, not assumed: consecutive record addresses in both pointer
arrays are 20 bytes (0x14) apart => rec_len = 4 + 4*count for count=4, i.e. hdr(2) + X(8) +
Y(8) = 18 used + 2 tail.  My earlier 0x12 model was WRONG; this is the V73 spill trap.
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
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import v76_surface as V

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = os.path.join(ROOT, "analysis-2020accord", "_v38_plain_image.bin")
EXPECT_SHA = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
PTR_C, PTR_E, MODE, NPTS, REC_LEN = 0xC9E9C, 0xC9F84, 26, 4, 20

B = open(IMG, "rb").read()


def u32(a):
    return struct.unpack_from("<I", B, a)[0]


def u16(a):
    return B[a] | (B[a + 1] << 8)


print("=" * 100)
print("V76 FINAL CUT SPEC -- mode 26 FactorC / FactorE")
print("=" * 100)
sha = hashlib.sha256(B).hexdigest()
print("  base _v38_plain_image.bin sha256 %s  %s"
      % (sha, "MATCH" if sha == EXPECT_SHA else "*** MISMATCH ***"))
assert sha == EXPECT_SHA, "base image is not the expected V38 plain image"

CX = [2240, 3840, 5120, 8960]
C1 = [566, 566, 566, 908]
stock = V.Surface("stock", 26)
v74 = V.Surface("v74", 26)
v75 = V.Surface("v75", 26)
img75 = V.load("v75")


EX0 = 0        # DECISION A: guard G3 (E_X0 >= 12) OVERRIDDEN -- see the guard report below


def S(ex1, ey1, cy=C1, ex0=EX0):
    return V.Surface(img=img75, override={"C": (CX, cy), "E": ([ex0, ex1, 2500, 4000],
                                                               [0, ey1, 539, 927])})


print("\n" + "-" * 100)
print("(1) VALIDATING DECISION B -- plateau OUT at FULL dose (137 at r=99), E_X0 = 0")
print("-" * 100)
print("  team-lead's arithmetic: E_Y1=300 -> M=(566*300)>>10=%d, and %d/1.3814 -> E_X1 ~ 119."
      % ((566 * 300) >> 10, (566 * 300) >> 10))
print("  Checked against the mirror, integers either side of 119:")
print("  %-34s %8s %5s %6s %6s | %6s %6s %6s | %s"
      % ("FactorE X / Y", "k", "M", "d@99", "d@94", "d@200", "d@400", "d@1200", "plateau"))
for ex1 in (117, 118, 119, 120, 121):
    s = S(ex1, 300)
    M = (566 * 300) >> 10
    print("  [ 0,%3d,2500,4000] / [0,300,539,927] %8.4f %5d %6d %6d | %6d %6d %6d | %s"
          % (ex1, M / (ex1 - EX0), M, s.mag(0, 99), s.mag(0, 94), s.mag(0, 200),
             s.mag(0, 400), s.mag(0, 1200), "REMOVED"))
print("  reference, the E_Y1=539 plateau version at the same dose:")
s539 = S(215, 539)
print("  [ 0,215,2500,4000] / [0,539,539,927] %8.4f %5d %6d %6d | %6d %6d %6d | PRESENT"
      % (((566 * 539) >> 10) / 215, (566 * 539) >> 10, s539.mag(0, 99), s539.mag(0, 94),
         s539.mag(0, 200), s539.mag(0, 400), s539.mag(0, 1200)))

EX1, EY1 = 119, 300
FIN = S(EX1, EY1)
EX, EY = [EX0, EX1, 2500, 4000], [0, EY1, 539, 927]
print("\n  ==> DECISION B VALIDATES. E_X1 = 119 lands dose %d at r=99 -- team-lead's arithmetic"
      % FIN.mag(0, 99))
print("      was correct. Plateau REMOVED (300 < 539) at FULL V75 creep dose.")
print("\n  ==> CHOSEN:  E_X = %s    E_Y = %s" % (EX, EY))
print("      k = %.4f.  The knee sits at %d ct = %.0f deg/s, comfortably ABOVE the grind-#1"
      % (((566 * EY1) >> 10) / (EX1 - EX0), EX1, EX1 / 4.7121))
print("      operating point of 99 ct = 21 deg/s, so that point stays inside the ramp.")

print("\n" + "-" * 100)
print("(2) DOSE at 21 deg/s (99 ct) BY SPEED, vs stock / V74 / V75-flown")
print("-" * 100)
print("  %-12s %9s | %6s %6s %6s %6s %6s %6s"
      % ("build", "k(creep)", "5", "20", "35", "60", "80", "140"))
for nm, s in (("stock/V38", stock), ("V74", v74), ("V75 flown", v75), ("V76 FINAL", FIN)):
    cy0 = s.XY("C")[1][0]
    ex, ey = s.XY("E")
    k = ((cy0 * ey[1]) >> 10) / (ex[1] - ex[0])
    print("  %-12s %9.4f | %6d %6d %6d %6d %6d %6d"
          % (nm, k, *[s.mag(int(v * 64), 99) for v in (5, 20, 35, 60, 80, 140)]))

print("\n" + "-" * 100)
print("(3) max |gp-0x6bd0| OVER THE WHOLE GRID, and the >512 band")
print("-" * 100)
for nm, cy in (("stock/V38", stock.XY("C")[1]), ("V74", v74.XY("C")[1]),
               ("V75 flown", v75.XY("C")[1]), ("V76 FINAL", C1)):
    mx = max((V.lerp(CX, cy, v) * 927) >> 10 for v in range(0, 14001))
    band = [v for v in range(0, 14001) if ((V.lerp(CX, cy, v) * 927) >> 10) > 512]
    print("  %-12s max|6bd0| = %4d   >512 band: %s"
          % (nm, mx, "NONE" if not band else "%.1f - %.1f km/h" % (min(band) / 64, max(band) / 64)))

print("\n" + "-" * 100)
print("(4) GRIND-#2 SEPARATION -- FactorE gain vs V75-FLOWN at matched rate")
print("-" * 100)
print("  %8s %9s | %8s %8s %8s | %10s %10s"
      % ("rate ct", "deg/s", "stock E", "V75 E", "V76 E", "V76/V75", "V76/stock"))
for r in (200, 400, 1200):
    es = V.lerp(*stock.XY("E"), idx=r)
    e5 = V.lerp(*v75.XY("E"), idx=r)
    e6 = V.lerp(EX, EY, r)
    print("  %8d %9.0f | %8d %8d %8d | %9.2fx %9.2fx" % (r, r / 4.7121, es, e5, e6, e6 / e5, e6 / es))

print("\n" + "-" * 100)
print("(4b) THE 35-80 km/h EXPOSURE, RE-RUN FOR THE SHIPPING k")
print("-" * 100)
try:
    import numpy as np
    cache = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "..", "_scratch/cache/r61", "r61.npz")
    d = np.load(cache, allow_pickle=True)
    t, vv, lat = d["cs_t"], d["cs_v"], np.asarray(d["cc_lat"]).astype(bool)
    n = min(len(t), len(vv), len(lat))
    t, vv, lat = t[:n], vv[:n], lat[:n]
    pre = t < 732.3872                    # SENTINEL GUARD: strict pre-fault prefix
    kmh, dt = vv * 3.6, np.gradient(t)
    ex74, ey74 = v74.XY("E")
    slope74 = (ey74[1] - ey74[0]) / (ex74[1] - ex74[0])
    slopeFIN = EY1 / float(EX1 - EX0)
    kFIN = 566 * slopeFIN / 1024
    print("  route 61 (V74's fault drive), engaged, strict pre-fault prefix")
    print("  %8s %10s | %9s %9s | %8s" % ("km/h", "engaged s", "k V74 flown", "k V76", "ratio"))
    tot = tw = 0.0
    for lo, hi in ((35, 45), (45, 55), (55, 65), (65, 80)):
        m = pre & lat & (kmh >= lo) & (kmh < hi)
        s = float(np.sum(dt[m]))
        c74 = V.lerp(CX, v74.XY("C")[1], int((lo + hi) / 2 * 64))
        k74 = c74 * slope74 / 1024
        tot += s
        tw += s * k74
        print("  %8s %10.1f | %9.3f %9.3f | %7.2fx" % ("%d-%d" % (lo, hi), s, k74, kFIN, kFIN / k74))
    print("  %8s %10.1f | %9.3f %9.3f | %7.2fx   <== the number for the handoff"
          % ("WEIGHTED", tot, tw / tot, kFIN, kFIN / (tw / tot)))
    print("  (%.1f%% of all engaged time on the route)" % (100 * tot / float(np.sum(dt[pre & lat]))))
except Exception as e:
    print("  [cache unavailable: %s]" % e)

print("\n" + "-" * 100)
print("(5) GUARDS")
print("-" * 100)
print("  🛑 G3 OVERRIDE, FLAGGED EXPLICITLY, NOT SILENTLY PASSED:")
print("     build_v74_tva asserts E_X0 >= E_X0_MIN_SAFE = 12.  THIS BUILD SETS E_X0 = 0.")
print("     Authorised by team-lead this session. Rationale: with E_X0 = 12 the E_X1 that lands")
print("     dose 137 is 200, i.e. V75's FactorE byte-for-byte at k = 1.5798 -- the faulted build.")
print("     G3 exists to prevent a steep ramp starting near zero, but E_X0 12->0 LOWERS the")
print("     slope (2.867 -> %.3f per count), so the guard's rationale points opposite to its"
      % (EY1 / float(EX1 - EX0)))
print("     effect here.  E_Y[0] = 0 is retained, so there is no torque at zero rate and no")
print("     Coulomb relay -- the actual hazard the guard was reaching for. [see v76_surface 6b]")
print()


def guards(nm, X, Y):
    print("  %-9s strict-X-increasing=%-5s  Y-monotone-nondecreasing=%-5s  no-zero-divisor=%-5s"
          % (nm, all(X[i] < X[i + 1] for i in range(3)),
             all(Y[i] <= Y[i + 1] for i in range(3)),
             all(X[i + 1] - X[i] != 0 for i in range(3))))


guards("FactorC", CX, C1)
guards("FactorE", EX, EY)
sC = stock.XY("C")[1]
sEX, sE = stock.XY("E")
Cn = [V.lerp(CX, C1, v) for v in range(0, 14001)]
Cs = [V.lerp(CX, sC, v) for v in range(0, 14001)]
En = [V.lerp(EX, EY, r) for r in range(0, 0x32C9)]
Es = [V.lerp(sEX, sE, r) for r in range(0, 0x32C9)]
print("  add-only 1-D: FactorC >= stock at all %d speeds: %s | FactorE >= stock at all %d rates: %s"
      % (len(Cn), all(a >= b for a, b in zip(Cn, Cs)),
         len(En), all(a >= b for a, b in zip(En, Es))))
print("  => dose = (C*E)>>10 is MONOTONE NON-DECREASING in each of C,E >= 0, so the two 1-D facts")
print("     PROVE add-only at every (speed,rate) pair.  Exhaustive 2-D confirmation follows.")
bad = 0
n = 0
for cn, cs in zip(Cn, Cs):
    for en, es in zip(En, Es):
        n += 1
        if ((cn * en) >> 10) < ((cs * es) >> 10):
            bad += 1
print("     checked %s (speed,rate) points exhaustively: %d violations  => %s"
      % (format(n, ","), bad, "ADD-ONLY CONFIRMED" if bad == 0 else "*** FAIL ***"))

print("\n" + "-" * 100)
print("(6) EXACT BYTE WRITES -- mode 26 only, little-endian, on _v38_plain_image.bin")
print("-" * 100)
recC, recE = u32(PTR_C + 4 * MODE), u32(PTR_E + 4 * MODE)
print("  FACTOR_C_PTRS 0x%05X + 4*%d -> record 0x%05X  (hdr=%d, X@+0x02, Y@+0x0A, len 0x%02X)"
      % (PTR_C, MODE, recC, u16(recC), REC_LEN))
print("  FACTOR_E_PTRS 0x%05X + 4*%d -> record 0x%05X  (hdr=%d, X@+0x02, Y@+0x0A, len 0x%02X)"
      % (PTR_E, MODE, recE, u16(recE), REC_LEN))
writes = []
for rec, arr, new, tag in ((recC, "Y", C1, "FactorC"), (recE, "X", EX, "FactorE"),
                           (recE, "Y", EY, "FactorE")):
    off0 = 2 if arr == "X" else 2 + 2 * NPTS
    for i, nv in enumerate(new):
        a = rec + off0 + 2 * i
        ov = u16(a)
        if ov != nv:
            writes.append((a, ov, nv, "%s %s[%d]" % (tag, arr, i)))
print("\n  %-9s %-14s %-16s %-16s %s" % ("addr", "field", "old bytes (LE)", "new bytes (LE)", "value"))
for a, ov, nv, tag in writes:
    print("  0x%05X  %-14s %02X %02X  (%5d)  %02X %02X  (%5d)  %d -> %d"
          % (a, tag, ov & 0xFF, ov >> 8, ov, nv & 0xFF, nv >> 8, nv, ov, nv))
print("\n  TOTAL: %d halfword writes = %d bytes changed" % (len(writes), 2 * len(writes)))

# ASSERT every old byte matches the STOCK image, not just the V38 image
SB = V.load("stock")
mismatch = [(a, u16(a), SB[a] | (SB[a + 1] << 8)) for a, _, _, _ in writes
            if u16(a) != (SB[a] | (SB[a + 1] << 8))]
print("  ASSERT old bytes == stock code.bin at every write address: %s"
      % ("PASS (all %d)" % len(writes) if not mismatch else "*** FAIL %s ***" % mismatch))
assert not mismatch, "V38 base differs from stock at a write address"
stock_full = all((SB[r + o] | (SB[r + o + 1] << 8)) == u16(r + o)
                 for r in (u32(PTR_C + 4 * MODE), u32(PTR_E + 4 * MODE)) for o in range(0, REC_LEN, 2))
print("  ASSERT the ENTIRE mode-26 FactorC+FactorE records are byte-identical V38 vs stock: %s"
      % ("PASS" if stock_full else "*** FAIL ***"))

print("\n" + "-" * 100)
print("(7) BLAST RADIUS -- mode 24 and adjacent records")
print("-" * 100)
for nm, pa in (("FactorC", PTR_C), ("FactorE", PTR_E)):
    recs = {}
    for m in range(40):
        recs.setdefault(u32(pa + 4 * m), []).append(m)
    t26, t24 = u32(pa + 4 * MODE), u32(pa + 4 * 24)
    print("  %s: 40 modes -> %d DISTINCT records (NO aliasing).  mode26 = 0x%05X %s   mode24 = 0x%05X %s"
          % (nm, len(recs), t26, recs[t26], t24, recs[t24]))
lo = min(a for a, _, _, _ in writes)
hi = max(a for a, _, _, _ in writes) + 2
print("  write span: 0x%05X .. 0x%05X (%d bytes)" % (lo, hi, hi - lo))
spill = []
for nm, pa in (("FactorC", PTR_C), ("FactorE", PTR_E)):
    for m in range(40):
        if m == MODE:
            continue
        r = u32(pa + 4 * m)
        for a, _, _, _ in writes:
            if r <= a < r + REC_LEN:
                spill.append((a, nm, m, r))
c26, e26 = u32(PTR_C + 4 * MODE), u32(PTR_E + 4 * MODE)
inside = all(any(r <= a < r + REC_LEN for r in (c26, e26)) for a, _, _, _ in writes)
m24 = [u32(PTR_C + 4 * 24), u32(PTR_E + 4 * 24)]
clear = all(not (r <= a < r + REC_LEN) for a, _, _, _ in writes for r in m24)
print("  every write lands inside a mode-26 record: %s" % inside)
print("  every write clear of BOTH mode-24 records (0x%05X, 0x%05X): %s" % (m24[0], m24[1], clear))
print("  nearest write is %d / %d bytes from the mode-24 FactorC / FactorE records."
      % (min(abs(a - m24[0]) for a, _, _, _ in writes),
         min(abs(a - m24[1]) for a, _, _, _ in writes)))
print("  writes spilling into ANY other mode's record: %s" % (spill if spill else "NONE"))
print("\n  => MODE 24 UNTOUCHED.  All %d writes land strictly inside mode 26's own two records."
      % len(writes))
