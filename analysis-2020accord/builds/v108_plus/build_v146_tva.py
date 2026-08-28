#!/usr/bin/env python3
r"""
V146 -- THE NOTCH, RE-SIZED FROM MEASURED GRIND DATA.  20.3 Hz, r = 0.96.  Base = V122.
        Supersedes V144/V145, which centred correctly but were TOO NARROW.

WHAT CHANGED AND WHY -- THE DOSE IS NOW MEASURED, NOT GUESSED
---------------------------------------------------------------
V144/V145 put the notch at 20.0 Hz with r = 0.98 (-3 dB span 16.9-23.1 Hz).  The centre was a
reasonable guess; the WIDTH was never checked against data.  It has now been measured.

Dominant 14-30 Hz peak of cs_rate, ENGAGED, 1-24 km/h (the operator's creep symptom regime),
pooled over 12 cached routes spanning V90 to V122:

        n = 1180 windows     p10 14.84    p25 17.19    p50 20.31    p75 21.88    p90 23.44 Hz

  * the CENTRE was right: p50 = 20.31 Hz, so 20.0 was within 0.3 Hz.
  * the WIDTH was NOT: only 68.2 % of those peaks fall inside r = 0.98's -3 dB band.
    NEARLY A THIRD OF THE GRIND ESCAPED THE NOTCH.

Re-sizing against that empirical distribution (mean |H| evaluated AT the measured peaks):

    f0    r     mean|H|   frac < -3dB    -3dB span      Nyquist lift
   20.0  0.98    0.5138      0.682       16.9-23.1         1.026     <- V144/V145
   20.0  0.96    0.3513      0.894       14.4-25.5         1.105
   20.3  0.96    0.3468      0.899       14.7-25.8         1.102     <- THIS BUILD
   20.3  0.94    0.2754      0.982       13.0-27.4         1.235     (Nyquist lift too high)

=> 20.3 Hz / r = 0.96 gives 1.48x more attenuation across the ACTUAL grind distribution and
   raises coverage from 68 % to 90 %, for a 10 % lift at 500 Hz.

    A = -1.90440325  0xC60A8      C = -1.98375338  0xC60B0
    B = +0.92160000  0xC60AC      D = +1.05848204  0xC60B4
    |H| DC 1.000000  |  1 Hz 0.9994  |  3 Hz 0.9941  |  18 Hz 0.363  |  20 Hz 0.050
    |  22 Hz 0.276  |  25 Hz 0.640  |  30 Hz 0.908

WHY THE NO-BOOST GATE HAD TO BE REPHRASED, NOT RELAXED
--------------------------------------------------------
V144's gate demanded peak |H| <= 1.05.  At r = 0.96 the peak is 1.102 -- but in a unity-DC notch
the peak is ALWAYS the NYQUIST end (500 Hz), a monotone HF shelf, NOT a resonance.  The thing that
gate exists to catch is a RESONANT PEAK NEAR the notch, which is what a first attempt at this
retune produced (3.82 = +11.6 dB just below the notch, boosting 15 Hz while notching 20 Hz).
=> the gate now asserts BOTH that the peak is <= 1.12 AND that it OCCURS ABOVE 200 Hz, i.e. that it
   is the Nyquist shelf and not a resonance.  That is strictly STRONGER than the old bound in the
   way that matters, and it stops the old bound from vetoing a better-sized filter for the wrong
   reason.

EVERYTHING ELSE IS V145
-------------------------
Same base (V122), same probe on gp-0x6C24 at sar 1 (the binary gate readout), same untouched
0xC64FA, same alpha2 8 / gain 6x / b26 clamp 511 / Lever A arms stock / pump deadband at Honda's 3.
The load-bearing BELIEF is unchanged and still unmeasured: the section arms only when
gp-0x671a >= 5.  If the gate stays shut this build is INERT rather than harmful, and the probe says
so directly.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
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

import cmath
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V146_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
DB_CAL, DB_HELD = 0xC61F6, 3                 # pump deadband -- HELD at Honda's value
BQ = {"A": 0xC60A8, "B": 0xC60AC, "C": 0xC60B0, "D": 0xC60B4}
BQ_HONDA = {"A": -1.5372, "B": 0.63462, "C": -1.8808, "D": 0.81730998}
NOTCH_F0, NOTCH_R, NOTCH_FS = 20.3, 0.96, 1000.0   # SIZED FROM MEASURED DATA
TCB_TASK1_ENTRY, TCB_TASK1_ADDR = 0x0002214A, 0xBB928
GATE_EN_CAL, GATE_EN_VAL = 0xC649B, 1        # cal == 1 arms the section
GATE_CEIL_CAL, GATE_CEIL_VAL = 0xC64FA, 5    # gp-0x671a >= this; NOT touched
LANE_CLAMP, AGG_CLAMP = 0x2000, 0x2800       # +-8192 lane, +-10240 aggregator
ARMS_STOCK = {0x3AB76: 0xAA, 0x3AC20: 0xAA}  # Lever A arms -- HELD stock
TAP_ADDR = 0x55DF2                           # the 427 tap displacement
TAP_OLD = (-0x6ABC) & 0xFFFF                 # V122 taps gp-0x6ABC
TAP_NEW = (-0x6C24) & 0xFFFF                 # -> gp-0x6c24, THE GATE-STATE MIRROR
SAR_NEW = 0xA1                               # sar 3 -> 1: the gate values are 0/1 and
                                             # (1*5)>>3 == 0 would be INVISIBLE
GATE_LO_CAL, GATE_LO_VAL = 0xC6138, 1        # written when gp-0x671a <  5  (SHUT)
GATE_HI_CAL, GATE_HI_VAL = 0xC6136, 0        # written when gp-0x671a >= 5  (OPEN)
SAR_ADDR, SAR_HELD = 0x55E10, 0xA3           # sar 3, already in V122; NOT touched
LANE_MIRRORS = {0x6ADA: 'r24 lane (probed)', 0x6ADC: 'r26 lane'}
ALPHA2_STOCK = 22
ALPHA2_STEPS = ((22, 14, "V91  -> V111"), (14, 8, "V112 -> V122"))   # flown, fault-free

# ---- THE FIVE CELLS V133 MOVED THAT THIS BUILD DELIBERATELY LEAVES AT V122 -------------------
REVERTED = {
    0xC407E: (2, 511, "b26 clamp = APPARENT MASS ceiling.  V133 doubled it to 1023 and the car"
                      " got VIOLENTLY worse, persisting after disengage because it is NOT"
                      " mode-gated."),
    0x3AB76: (1, 0xAA, "Lever A r26 arm -- left STOCK.  Its partner caused grind #2."),
    0x3AC20: (1, 0xAA, "Lever A r24 arm -- left STOCK.  RECORDED as having CAUSED grind #2,"
                       " which the operator reported on V133 while DISENGAGED."),
    0xC6CD0: (2, 5346, "LKAS gain HELD at 6x.  V133's 8x adds 33 % excitation into a zeta"
                       " 0.017-0.036 resonance, against an explicit operator instruction."),
    0xC640A: (2, -8192, "oscillation branch Y left at Honda's value -- V133's -1966 flew inside"
                        " a six-variable build and is NOT independently cleared."),
}
CEIL_F, CEIL_F_VAL = 0xC4004, 0.5           # the clamp's float twin, matched to 511
KNEE_CAL, KNEE_VAL = 0xC40BC, 3000
K1_CAL, K1_VAL = 0xC40D2, 1020
OFF_CAL, OFF_VAL = 0xC4080, 0
POLE_CAL, POLE_VAL = 0xC40D0, 408
RESID_CAL, RESID_VAL = 0xC7468, 41232
ARM_CAL, ARM_VAL = 0xC620A, 12800
BQ_ADDR, BQ_LEN = 0xC60A8, 16
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END

FS, ALPHA0 = 1000.0, 37 / 128.0
SIG_BAND = (18.0, 22.0)
OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ASSERTION FAILED: {msg}")


def band_mag(a2, n=41):
    import math
    lo, hi = SIG_BAND
    tot = 0.0
    for i in range(n):
        f = lo + (hi - lo) * i / (n - 1)
        w = 2 * math.pi * f / FS
        z = complex(math.cos(w), math.sin(w))
        a = a2 / 64.0
        tot += abs(64 * (ALPHA0 / (1 - (1 - ALPHA0) / z)) * (1 - 1 / z) * (a / (1 - (1 - a) / z)))
    return tot / n


def build():
    print("=" * 102)
    print("  V146 -- the notch RE-SIZED from measured grind data: 20.3 Hz, r = 0.96.")
    print("=" * 102)

    print("\n  [1] BASE = V122, THE LAST FLOWN KNOWN-GOOD BUILD")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V122 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE CARRIES V122's VALUES, INCLUDING EVERY CELL V133 MOVED")
    check(u16(base, DB_CAL) == DB_HELD,
          f"  0x{DB_CAL:05X} pump deadband = {DB_HELD} (Honda) -- HELD; this build is notch-only")
    check(u16(base, ALPHA2_CAL) == ALPHA2_HELD,
          f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_HELD} -- HELD; deadband-only build")
    for _a, _v in sorted(ARMS_STOCK.items()):
        check(base[_a] == _v,
              f"  0x{_a:05X} Lever A arm = 0x{_v:02X} STOCK -- V133 doubled these and the car got violent")
    check(u16(base, KNEE_CAL) == KNEE_VAL and u16(base, K1_CAL) == K1_VAL,
          f"  relay knee {KNEE_VAL} / K1 {K1_VAL} -- V122's tuned pair")
    check(u16(base, OFF_CAL) == OFF_VAL and u16(base, POLE_CAL) == POLE_VAL,
          "  relay offset 0 and friction EMA pole 408, both V122")
    check(u16(base, RESID_CAL) == RESID_VAL, f"  0x{RESID_CAL:05X} residual scale = {RESID_VAL}")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(base, a) if want < 0 else (base[a] if w == 1 else u16(base, a))
        check(got == want, f"  0x{a:05X} = {want} in the base -- {why.split('.')[0]}")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(abs(_fb - CEIL_F_VAL) < 1e-9 and abs(_fb * 1024 - (511 + 1)) < 1e-6,
          f"  0x{CEIL_F:05X} float twin = {CEIL_F_VAL} and float*1024 == int+1 ({_fb*1024:.0f})")

    print("\n  [3] THE RATE IS RESOLVED FROM THE TCB TABLE, READ OUT OF THIS IMAGE")
    _t1 = struct.unpack_from("<I", base, TCB_TASK1_ADDR)[0]
    check(_t1 == TCB_TASK1_ENTRY,
          f"  0x{TCB_TASK1_ADDR:05X} task1 ENTRY = 0x{_t1:08X} == FUN_0002214a, the ONLY caller of"
          f" FUN_000352b4 => the notch runs in TASK 1, the kit's CONFIRMED 1 kHz task")
    print(f"      => fs = {NOTCH_FS:.0f} Hz;  Honda's 19.88 deg notch sits at 55.23 Hz, well above"
          f" the 18-22 Hz grind")

    print("\n  [4] THE RETUNE -- SPECIFIED BY FORMULA, ASSERTED AGAINST THE ENCODING")
    for k, v in sorted(BQ_HONDA.items()):
        got = struct.unpack_from("<f", base, BQ[k])[0]
        check(abs(got - v) < 1e-5, f"  0x{BQ[k]:05X} {k} = {got:.8g} (Honda) in the base")
    _th = 2 * math.pi * NOTCH_F0 / NOTCH_FS
    NEW = {"C": -2 * math.cos(_th), "A": -2 * NOTCH_R * math.cos(_th), "B": NOTCH_R * NOTCH_R}
    NEW["D"] = (1 + NEW["A"] + NEW["B"]) / (2 + NEW["C"])
    for k in ("A", "B", "C", "D"):
        struct.pack_into("<f", code, BQ[k], NEW[k])
        attributed |= set(range(BQ[k], BQ[k] + 4))
        print(f"      0x{BQ[k]:05X}  {k}  {BQ_HONDA[k]:+.8g} -> {NEW[k]:+.8g}"
              f"   ({struct.pack('<f', NEW[k]).hex()})")
    for k in ("A", "B", "C", "D"):
        _rt = struct.unpack_from("<f", code, BQ[k])[0]
        check(abs(_rt - NEW[k]) < 1e-6,
              f"  \U0001f6d1 0x{BQ[k]:05X} {k} ROUND-TRIPS through float32 ({_rt:.9g}) -- asserted"
              f" against the ENCODING, not a decimal (feedback-float-spec-must-be-the-formula)")

    print("\n  [4b] THE FILTER GATES")
    _H = lambda A_, B_, C_, D_, f: abs(D_ * (1 + C_ * cmath.exp(-1j * 2 * math.pi * f / NOTCH_FS)
                                             + cmath.exp(-2j * 2 * math.pi * f / NOTCH_FS))
                                       / (1 + A_ * cmath.exp(-1j * 2 * math.pi * f / NOTCH_FS)
                                          + B_ * cmath.exp(-2j * 2 * math.pi * f / NOTCH_FS)))
    _h = lambda f: _H(NEW["A"], NEW["B"], NEW["C"], NEW["D"], f)
    check(abs(NEW["C"]) < 2.0,
          f"  \U0001f6d1 THE TRUE-NOTCH GATE: |C| = {abs(NEW['C']):.6f} < 2, so the zeros stay"
          f" COMPLEX and EXACTLY on the unit circle => a real notch, not a shelf")
    check(math.sqrt(NEW["B"]) < 1.0,
          f"  \U0001f6d1 THE STABILITY GATE: pole radius {math.sqrt(NEW['B']):.4f} < 1")
    check(abs(_h(1e-6) - 1.0) < 1e-4,
          f"  \U0001f6d1 THE AUTHORITY GATE: |H| at DC = {_h(1e-6):.6f} == 1.000 EXACTLY by"
          f" construction => LKAS authority is UNCHANGED.  D was solved for this, not guessed.")
    _pk = max(_h(f) for f in [x * 0.05 for x in range(2, 10000)])
    _pkf = max([x * 0.05 for x in range(2, 10000)], key=lambda f: _h(f))
    check(_pkf > 200.0,
          f"  🛑 THE NO-RESONANCE GATE: the peak sits at {_pkf:.0f} Hz, i.e. it is the"
          f" NYQUIST shelf of a unity-DC notch, NOT a resonance near the notch.  A first attempt at"
          f" this retune produced 3.82 (+11.6 dB) just BELOW the notch -- THAT is what this gate"
          f" exists to catch, and a magnitude bound alone would have vetoed a better-sized filter"
          f" for the wrong reason.")
    check(_pk <= 1.12,
          f"  🛑 THE NO-BOOST GATE: peak |H| = {_pk:.4f} <= 1.12 -- a 10 % HF"
          f" shelf, bought for 1.48x more attenuation across the MEASURED grind"
          f" distribution (mean |H| 0.347 vs 0.514) and coverage 90 % vs 68 %")
    check(_h(NOTCH_F0) < 0.01,
          f"  the notch is DEEP at {NOTCH_F0:.0f} Hz: |H| = {_h(NOTCH_F0):.6f}"
          f" ({20*math.log10(max(_h(NOTCH_F0), 1e-12)):.1f} dB)")
    for _f in (18.0, 22.0):
        check(_h(_f) < 0.71,
              f"  and it still attenuates {_f:.0f} Hz to |H| = {_h(_f):.4f} (better than -3 dB)"
              f" => the whole 18-22 Hz grind band is covered")
    check(_h(3.0) > 0.95 and _h(1.0) > 0.98,
          f"  \U0001f6d1 THE STEERING-BAND GATE: |H| = {_h(1.0):.4f} at 1 Hz and {_h(3.0):.4f} at"
          f" 3 Hz -- normal steering (0.5-3 Hz carries 90 % of command power) passes UNTOUCHED")

    print("\n  [4c] THE GATE THIS FILTER SITS BEHIND -- CHECKED, NOT MOVED")
    check(base[GATE_EN_CAL] == GATE_EN_VAL,
          f"  0x{GATE_EN_CAL:05X} enable = {GATE_EN_VAL} in the base (it is 0 in STOCK) => the"
          f" section is ARMED as far as this cal is concerned")
    check(base[GATE_CEIL_CAL] == GATE_CEIL_VAL and code[GATE_CEIL_CAL] == GATE_CEIL_VAL,
          f"  0x{GATE_CEIL_CAL:05X} = {GATE_CEIL_VAL} UNTOUCHED -- it has 18 READERS,"
          f" ten an unexamined cluster at 0x260BC.  The FUN_00036c12 Y branch reads 0xC64FD,"
          f" a DIFFERENT cal -- the earlier 'it rails b26' claim was WRONG")
    print("      \U0001f6d1 [BELIEF] that gp-0x671a reaches 5 during a grind.  A ratchet IS")
    print("         repeated reversals, so it should -- but it has never been measured.  If the")
    print("         gate stays shut this build is INERT, not harmful, and the probe will say so.")

    print("\n  [4d] THE PROBE -- TELEMETRY ONLY, AND IT TESTS THE LOAD-BEARING BELIEF")
    check(u16(base, TAP_ADDR) == TAP_OLD,
          f"  0x{TAP_ADDR:05X} 427 tap = 0x{TAP_OLD:04X} (gp-0x6ABC) in the base")
    struct.pack_into("<H", code, TAP_ADDR, TAP_NEW)
    attributed |= {TAP_ADDR, TAP_ADDR + 1}
    print(f"      0x{TAP_ADDR:05X}  427 tap  gp-0x6ABC -> gp-0x6C24   (0x{TAP_OLD:04X} ->"
          f" 0x{TAP_NEW:04X})   THE GATE-STATE MIRROR")
    check(u16(code, TAP_ADDR) == TAP_NEW and TAP_NEW % 2 == 0,
          "  reads back, and the displacement is EVEN as ld.h requires")
    check(base[SAR_ADDR] == SAR_HELD, f"  0x{SAR_ADDR:05X} packer sar = 0x{SAR_HELD:02X} in base")
    code[SAR_ADDR] = SAR_NEW
    attributed.add(SAR_ADDR)
    _w = lambda x, sar: min((min(abs(x), 65535) * 5) >> (sar & 0x1F), 0x3FF)
    check((SAR_HELD & ~0x1F) == (SAR_NEW & ~0x1F),
          f"  0x{SAR_ADDR:05X} sar {SAR_HELD & 0x1F} -> {SAR_NEW & 0x1F}: OPCODE field untouched"
          f" (0x{SAR_HELD & ~0x1F:02X}), only the shift immediate moves")
    check(_w(GATE_LO_VAL, SAR_HELD) == _w(GATE_HI_VAL, SAR_HELD),
          f"  🛑 WHY THE SAR HAD TO MOVE: at sar {SAR_HELD & 0x1F} the two gate values BOTH"
          f" map to wire {_w(GATE_LO_VAL, SAR_HELD)} -- the probe would have been BLIND")
    check(_w(GATE_LO_VAL, SAR_NEW) != _w(GATE_HI_VAL, SAR_NEW),
          f"  🛑 THE SEPARATION GATE: at sar {SAR_NEW & 0x1F} shut -> wire"
          f" {_w(GATE_LO_VAL, SAR_NEW)}, open -> wire {_w(GATE_HI_VAL, SAR_NEW)}; the wire is a"
          f" digital field with no noise, so the DUTY is exactly countable")
    check(struct.unpack_from("<h", base, GATE_LO_CAL)[0] == GATE_LO_VAL
          and struct.unpack_from("<h", base, GATE_HI_CAL)[0] == GATE_HI_VAL,
          f"  the two branch cals are {GATE_LO_VAL} (shut) / {GATE_HI_VAL} (open) in the base,"
          f" and are NOT touched -- their VALUE is functional (compared against 1 downstream)")
    print("      => gp-0x6c24 is written EVERY aggregator tick with which branch of")
    print("         (gp-0x671a < cal(0xC64FA)) was taken -- it IS the notch's gate condition.")
    print("         One gp-based access image-wide (the write) => nothing reads it => free.")

    print("\n  [5] \U0001f6d1 EVERY CELL IMPLICATED IN V133's REGRESSION IS AT ITS V122 VALUE")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(code, a) if want < 0 else (code[a] if w == 1 else u16(code, a))
        check(got == want and rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} = {want}  -- {why}")
    check(struct.unpack_from("<f", code, CEIL_F)[0] == CEIL_F_VAL,
          f"  0x{CEIL_F:05X} float twin stays {CEIL_F_VAL}, matched to the 511 int")
    check(u16(code, 0xC6CD0) == 5346,
          "  \U0001f6d1 THE GAIN GATE: LKAS gain stays 6x.  The operator's instruction was"
          " conditional -- 8x only if we do NOT get more oscillation and grinding.  We did.")

    print("\n  [6] NOTHING ELSE MOVED")
    for a, w, nm in ((ALPHA2_CAL, 2, "alpha2 -- HELD, this build is notch-only"),
                     (DB_CAL, 2, "pump deadband -- HELD at Honda 3"),
                     (KNEE_CAL, 2, "relay knee"), (K1_CAL, 2, "K1"), (OFF_CAL, 2, "relay offset"),
                     (POLE_CAL, 2, "friction EMA pole"), (RESID_CAL, 2, "residual scale"),
                     (ARM_CAL, 2, "detector arm threshold"), (0xC40DA, 2, "the >>7 EMA twin")):
        check(rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} {nm} byte-identical to V122")
    for _a, _v in sorted(ARMS_STOCK.items()):
        check(code[_a] == base[_a] == _v, f"  0x{_a:05X} Lever A arm HELD stock at 0x{_v:02X}")
    check(rd(code, BQ_ADDR, BQ_LEN) != rd(base, BQ_ADDR, BQ_LEN),
          "  🛑 THE BIQUAD IS THE EDIT.  Every prior builder asserts this block"
          " BYTE-IDENTICAL -- that guard is exactly why the filter sat unexamined for ~90"
          " builds.  This build deliberately reverses it, and the four coefficients above"
          " are the ONLY bytes in it that move.")
    check(all(code[a] == base[a] for a in range(BQ_ADDR + 16, BQ_ADDR + BQ_LEN)),
          f"  and the rest of the {BQ_LEN}-byte block past the four coefficients is"
          f" byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- cal-only, OUTSIDE the"
          f" bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = ({TAP_ADDR, TAP_ADDR + 1, SAR_ADDR}
              | {a2 for k in BQ for a2 in range(BQ[k], BQ[k] + 4)})
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (biquad + tap + sar exempted)")

    print("\n  [7] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [8] FULL BYTE DIFF vs V122 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(payload == 15, f"exactly 15 payload bytes ({payload} found)"
          " -- 12 biquad + 2 tap + 1 sar")
    _functional = sum(hi - lo for lo, hi in runs
                      if not any(lo < t + 4 and t < hi for t in _tr)
                      and not (TAP_ADDR <= lo < TAP_ADDR + 2)
                      and lo != SAR_ADDR)  # tap = telemetry
    check(_functional == 12,
          f"  \U0001f6d1 THE SINGLE-LEVER GATE: exactly {_functional} FUNCTIONAL bytes ="
          f" the FOUR biquad coefficients, which are ONE lever (a notch has no meaning with its"
          f" coefficients split).  The other 2 are the 427 tap, telemetry only.")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V146 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V146-V122BASE-NOTCH20.3HZ.R96-427.GATE.6C24"
    img_out = plain_image_path(f"_v146_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V146_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
