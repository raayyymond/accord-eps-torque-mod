#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_fault_exact_model.py -- the EPS damping dose surface, mirroring FUN_00034350 EXACTLY.

(Companion to the lighter `studies/sessions/v74_v75/v75_fault_surface.py`. This one hard-codes NOTHING: every table
constant is read little-endian out of the plain images via studies/sessions/v74_v75/v75_fault_tables.py, the LERP is
the firmware's own walk-and-divq, and the output clamp is the real three-way branch, not a
`min()`. Written because a numeric fault -- if there were one -- would live precisely in the
places a textbook LERP smooths over: truncation direction, unsigned vs signed compares, and
the exact clamp branch.)

Every line is annotated with the instruction address it mirrors, from the GhidraMCP
disassembly of FUN_00034350 in the STOCK program `code.bin`.

  LERP (same shape at 0x34470 B, 0x34502 C, 0x34592 D, 0x34616 E, 0x346B4 ceiling):
      rec  = *(u32*)(PTR_ARRAY + mode*4)                 ld.w  0x0[r13]      0x34514
      X[i] = *(u16*)(rec + 2 + 2i)   Y[i] = *(u16*)(rec + 2 + 2n + 2i)
      if !(idx >u X[0])    -> Y[0]                       cmp/bh              0x3451E/20
      if !(idx <u X[n-1])  -> Y[n-1]                     cmp/bnc             0x3452A/2C
      walk k from 1 while X[k] <=u idx                   cmp/bnc             0x3453E-46
      out = SIGNED32((Y[k]-Y[k-1])*(idx-X[k-1])) / SIGNED32(X[k]-X[k-1]) + Y[k-1]
                                                          mul/divq/add        0x3455A/60/64
      out &= 0xFFFF                                      andi 0xffff         0x34566
  🛑 `divq` is SIGNED and truncates toward ZERO -- NOT Python's floor `//`. With a DESCENDING
     Y segment (V75's FactorC Y[0]=566 > Y[1]=234) the numerator is genuinely negative, so
     floor-vs-truncate differs by one count there. Modelled correctly with int(a/b).
  🛑 A zero divisor would set OV and leave the quotient UNDEFINED (V850E2 raises NO exception),
     so X[k]==X[k-1] is a real hazard -- checked separately and found absent in 510 records.

  DOSE (0x34684-0x346A2) -- UNSIGNED: `mulu` + LOGICAL `shr`:
      s = seed; if (s >= 0x401) s = 0x400        addi -0x401/setfnc/cmovne  0x344E4/E8/0x34620
      d = (s*B)>>10; d = (d*C)>>10; d = (d*D)>>10; E &= 0xFFFF; d = (d*E)>>10
                                                  mulu/shr x4               0x34684-0x3469C
      if (rate_signed > 0) d = -d                 cmp r0,r11/ble/subr       0x3469E-0x346A2
  GATES:
      FactorC used iff speed <u 0x7D00 AND gp-0x67f4==1  else 1024          0x344E0-0x344FA
      FactorE used iff |rate| <u 0x32C9 AND -13000<=rate_s<=13000 else DOSE=0  0x345FA-0x34614
  CEILING + CLAMP (0x346A4-0x3475C):
      ceil = (gp-0x6ac2 <u 0x32C9) ? LERP(0xC77A0[mode], gp-0x6ac2) : *(u16*)(tp+0x7158)=512
      if (dose >s ceil) out=+ceil; elif (dose >=s -ceil) out=dose; else out=-ceil
                                                  cmp/ble, cmp/bge          0x34724/2A, 3C/3E
      out -> gp-0x6bd0 (st.h, 16-bit) + shadow gp-0x4cf2; mismatch -> FUN_0006b9fa @0x34762

UNITS (from the kit's confirmed record, used for reporting only -- the model is in raw counts):
      column_deg_s = rate_counts / 4.7121        speed_kmh = speed_counts / 64.0
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
import os, sys
import v75_fault_tables as T

SEED_DEFAULT = 1024                # gp-0x698a, reported pinned at 1024
CEIL_FALLBACK_ADDR = 0xC6158       # tp+0x7158


def s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def lerp(X, Y, idx):
    n = len(X)
    if not (idx > X[0]):                        # 0x3451E cmp / 0x34520 bh   (UNSIGNED)
        return Y[0] & 0xFFFF                    # 0x34522 ld.hu 0x0[r10]
    if not (idx < X[n - 1]):                    # 0x3452A cmp / 0x3452C bnc  (UNSIGNED)
        return Y[n - 1] & 0xFFFF                # 0x34538 ld.hu 0x6[r10]
    k = 1                                       # 0x3452E walk starts at X[1], Y[0]
    while X[k] <= idx:                          # 0x34544 cmp / 0x34546 bnc  (UNSIGNED)
        k += 1
    num = ((Y[k] - Y[k - 1]) & 0xFFFFFFFF) * ((idx - X[k - 1]) & 0xFFFFFFFF)   # 0x34554/58/5A
    den = (X[k] - X[k - 1]) & 0xFFFFFFFF                                       # 0x3455E
    if s32(den) == 0:
        raise ZeroDivisionError("divq divisor 0 at X[%d]" % k)                 # 0x34560
    q = int(s32(num) / s32(den))                # divq truncates TOWARD ZERO
    return (q + Y[k - 1]) & 0xFFFF              # 0x34564 add / 0x34566 andi 0xffff


class Surface(object):
    def __init__(self, build, mode):
        self.build, self.mode = build, mode
        self.img = T.load(build)
        self.rec = {w: T.read_rec(self.img, w, mode) for w in ("B", "C", "D", "E", "CEIL")}
        self.ceil_fallback = T.u16(self.img, CEIL_FALLBACK_ADDR)

    def _XY(self, w):
        _, _, X, Y = self.rec[w]
        return X, Y

    def factorC(self, speed, gate_67f4=1):                      # 0x344E0-0x34566
        if not (speed < 0x7D00) or gate_67f4 != 1:
            return 0x400
        return lerp(*self._XY("C"), idx=speed)

    def factorE(self, rate_abs, rate_signed=None):              # 0x345FA-0x34682
        if rate_signed is None:
            rate_signed = rate_abs
        if not (rate_abs < 0x32C9):
            return None                                          # -> whole dose 0 (0x34612)
        if not (-13000 <= rate_signed <= 13000):
            return None
        return lerp(*self._XY("E"), idx=rate_abs)

    def ceiling(self, backdrive_idx=0):                          # 0x346A4-0x3471C
        if not (backdrive_idx < 0x32C9):
            return self.ceil_fallback                            # 0x346AE ld.hu 0x7158[tp]
        return lerp(*self._XY("CEIL"), idx=backdrive_idx)

    def dose_raw(self, speed, rate_signed, seed=SEED_DEFAULT, gate_67f4=1):
        rate_abs = abs(rate_signed)
        E = self.factorE(rate_abs, rate_signed)
        if E is None:
            return 0
        s = seed if seed < 0x401 else 0x400                       # 0x344E4 / 0x34620
        C = self.factorC(speed, gate_67f4)
        B = lerp(*self._XY("B"), idx=0)                           # flat 1024 in every record
        D = lerp(*self._XY("D"), idx=0)                           # flat 1024 in every record
        d = (s * B) >> 10                                         # 0x34684 mulu / 0x34688 shr
        d = (d * C) >> 10                                         # 0x3468A / 0x3468E
        d = (d * D) >> 10                                         # 0x34690 / 0x34696
        d = (d * (E & 0xFFFF)) >> 10                              # 0x34694 zxh / 0x34698 / 0x3469C
        if rate_signed > 0:                                       # 0x3469E cmp / 0x346A0 ble
            d = -d                                                # 0x346A2 subr r0,r8
        return d

    def output(self, speed, rate_signed, backdrive_idx=0, **kw):  # 0x34720-0x3475C
        d = self.dose_raw(speed, rate_signed, **kw)
        c = self.ceiling(backdrive_idx)
        if d > c:                                                 # 0x34724 cmp / 0x3472A ble
            v, clamped = c, True
        elif d >= -c:                                             # 0x3473C cmp / 0x3473E bge
            v, clamped = d, False
        else:
            v, clamped = -c, True
        v &= 0xFFFF                                               # st.h -- 16-bit store
        return (v - 0x10000 if v & 0x8000 else v), clamped


def launch_corner(mode=26, builds=("stock", "v74", "v75"),
                  rates=(0, 6, 12, 25, 50, 99, 150, 200, 300, 400, 800, 1555, 2500, 4000)):
    """The stoplight->launch corner. FactorC is FLAT below its X[0], so one table covers
    the whole 0 -> X[0] speed band; the speed column is verified flat, not assumed."""
    S = {b: Surface(b, mode) for b in builds}
    flat = all(S[b].factorC(0) == S[b].factorC(sp)
               for b in builds for sp in range(0, S[builds[0]].rec["C"][2][0]))
    print("MODE %d  gp-0x6bd0 (post-clamp), speeds 0..%d counts (0..%.1f km/h)  [column verified FLAT: %s]"
          % (mode, S[builds[0]].rec["C"][2][0], S[builds[0]].rec["C"][2][0] / 64.0, flat))
    print("  %8s %8s | %8s %8s %8s | %8s" % ("rate", "deg/s", "stock", "v74", "v75", "v75/v74"))
    print("  " + "-" * 62)
    for r in rates:
        vals = [S[b].output(0, r) for b in builds]
        rat = (abs(vals[2][0]) / abs(vals[1][0])) if vals[1][0] else float("nan")
        print("  %8d %8.1f | %8s %8s %8s | %8.2f"
              % (r, r / 4.7121,
                 "%d%s" % (vals[0][0], "*" if vals[0][1] else ""),
                 "%d%s" % (vals[1][0], "*" if vals[1][1] else ""),
                 "%d%s" % (vals[2][0], "*" if vals[2][1] else ""), rat))
    print("  (* = clamped at the ceiling)   ceiling(backdrive=0) = %d" % S[builds[0]].ceiling(0))
    print("\n  incremental viscous gain d|out|/d(rate) on the low-rate segment:")
    for b in builds:
        s = S[b]
        g = [abs(s.output(0, r)[0]) - abs(s.output(0, r - 1)[0]) for r in range(13, 201)]
        print("    %-6s FactorC(0)=%-5d  gain = %.4f counts opposing per count of rate"
              % (b, s.factorC(0), sum(g) / len(g)))


if __name__ == "__main__":
    for m in (26, 24):
        launch_corner(mode=m)
        print()
