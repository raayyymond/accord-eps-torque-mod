#!/usr/bin/env python3
r"""
V144 -- RETUNE HONDA'S OWN NOTCH FROM 55.2 Hz ONTO THE 20 Hz GRIND.  Base = V122.
        FOUR float cals + a 427 probe on the lane.  NO deadband -- the notch is the only lever.

THE FILTER, AND THAT IT IS REAL
---------------------------------
FUN_000352b4, the only writer of aggregator lane gp-0x6B86, runs a gated second-order FLOAT
section (arms when cal(0xC649B)==1, already true on V122, AND gp-0x671a >= cal(0xC64FA)=5):
        w[n] = D*x[n] - A*w[n-1] - B*w[n-2]
        y[n] = w[n]   + C*w[n-1] +   w[n-2]
        H(z) = D * (1 + C z^-1 + z^-2) / (1 + A z^-1 + B z^-2)
    HONDA:  A = -1.53720  B = 0.63462  C = -1.88080  D = 0.81731
The numerator zeros lie EXACTLY on the unit circle => a TRUE NOTCH, min |H| ~ -74 dB, and
|H| = 1.0000 at DC and 1.000 at Nyquist: TRANSPARENT except at the notch.
=> it costs NO authority, NO added mass, NO added friction.  No other lever in this kit has that
   shape, and the operator has been asking for exactly it.
This falsifies the kit memory "no notch filter exists anywhere" (V44).  The block at 0xC60A8 is
already BQ_ADDR in every builder, asserted byte-identical -- the kit had the ADDRESS, never the
FUNCTION, for ~90 builds.

THE RATE IS RESOLVED -- STATICALLY, FROM THE TCB TABLE, READ OUT OF THE IMAGE
------------------------------------------------------------------------------
        0xBB928  task1 ENTRY = 0x0002214A          0xBB9E8  task5 ENTRY = 0x00022CA0
FUN_000352b4's only caller is FUN_0002214a == the TASK 1 entry, and task 1 is the kit's CONFIRMED
1 kHz task.  (Task 5, the one whose rate is still open at ">= 250 Hz", is FUN_00022ca0 -- the
base-assist damper, a DIFFERENT task.)
=> fs = 1000 Hz.  Honda's notch angle 19.88 deg => 55.23 Hz.  WELL ABOVE the 18-22 Hz grind, so as
   shipped it does nothing for the operator's symptom.

THE RETUNE, SPECIFIED BY FORMULA (NOT BY DECIMALS)
----------------------------------------------------
A standard notch with poles at the zero angle and radius r:
        th = 2*pi*f0/fs
        C  = -2*cos(th)                 zeros stay EXACTLY on the unit circle => still a true notch
        A  = -2*r*cos(th)
        B  = r*r
        D  = (1 + A + B) / (2 + C)      solved for EXACT unity DC gain -- no authority is lost
    f0 = 20.0 Hz, r = 0.98:
        A = -1.94454481   B = 0.96040000   C = -1.98422940   D = 1.00536...
Choosing r:  the "peak" in a unity-DC notch is the NYQUIST gain, not a resonance.
        r 0.80 -> Nyquist 4.12 (a large HF boost, rejected)      r 0.95 -> 1.166
        r 0.92 -> 1.439                                          r 0.98 -> 1.026, -3 dB 16.9-23.1 Hz
r = 0.98 is the widest that both covers the 18-22 Hz grind band AND keeps the HF lift near unity.
A FIRST ATTEMPT scaled Honda's pole geometry down instead and produced peak |H| = 3.82 (+11.6 dB)
just BELOW the notch -- boosting 15 Hz while notching 20 Hz.  That design was rejected by its own
check; Honda's original is peak-free at 1.0000 and any retune must stay that way.

WHY THIS IS THE BEST LEVER IN THE QUEUE
-----------------------------------------
    unity DC        => LKAS authority unchanged                (his goal 2)
    unity elsewhere => no added apparent mass or friction      (his goal 1)
    -74 dB at 20 Hz => the grind band is removed, not traded   (his goal 3)
Every other lever in this session trades one of those against another.  This one does not.

WHAT IS NOT ESTABLISHED
-------------------------
[BELIEF] that the gate opens during a grind.  The section arms only when gp-0x671a >= 5, i.e. the
hard-reversal counter at its CEILING.  A ratchet IS repeated reversals, so it should -- but this
kit has never measured it.  If the gate stays shut, this build is INERT rather than harmful.
=> the 427 probe on gp-0x6B86 is carried FOR THAT REASON: it shows whether the lane is live, and
   a -74 dB null in its spectrum is direct confirmation the notch is running and where it sits.
[BELIEF] that the grind rides this lane at all.  gp-0x6B86 is one of ten aggregator lanes.
=> if the probe shows the lane dead or the null absent, the notch is not the answer and the queue
   falls back to V141 (the pump deadband).
NOT TOUCHED: cal(0xC64FA), the gate's threshold.  Lowering it would arm the notch more readily but
it ALSO selects the Y branch in FUN_00036c12 and gates two aggregator branches, and gp-0x671a has
four external consumers.  That is a separate, much riskier decision.

BASE = V122.  alpha2 stays 8, gain stays 6x, b26 clamp stays 511, both Lever A arms stay stock,
and the pump deadband stays at Honda's 3 -- this build is the NOTCH ALONE.
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
WRITE_MODE = os.environ.get("ACCORD_V144_WRITE", "").strip().lower()

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
NOTCH_F0, NOTCH_R, NOTCH_FS = 20.0, 0.98, 1000.0
TCB_TASK1_ENTRY, TCB_TASK1_ADDR = 0x0002214A, 0xBB928
GATE_EN_CAL, GATE_EN_VAL = 0xC649B, 1        # cal == 1 arms the section
GATE_CEIL_CAL, GATE_CEIL_VAL = 0xC64FA, 5    # gp-0x671a >= this; NOT touched
LANE_CLAMP, AGG_CLAMP = 0x2000, 0x2800       # +-8192 lane, +-10240 aggregator
ARMS_STOCK = {0x3AB76: 0xAA, 0x3AC20: 0xAA}  # Lever A arms -- HELD stock
TAP_ADDR = 0x55DF2                           # the 427 tap displacement
TAP_OLD = (-0x6ABC) & 0xFFFF                 # V122 taps gp-0x6ABC
TAP_NEW = (-0x6B86) & 0xFFFF                 # -> the NOTCH-FILTER LANE gp-0x6b86
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
    print("  V144 -- retune Honda's own notch 55.2 Hz -> 20 Hz.  Four float cals + the probe.")
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
    check(_pk <= 1.05,
          f"  \U0001f6d1 THE NO-BOOST GATE: peak |H| = {_pk:.4f} <= 1.05.  A first attempt that"
          f" scaled Honda's pole geometry gave 3.82 (+11.6 dB) just BELOW the notch -- boosting"
          f" 15 Hz while notching 20 Hz.  Honda's own filter is peak-free and a retune must stay so.")
    check(_h(NOTCH_F0) < 0.01,
          f"  the notch is DEEP at {NOTCH_F0:.0f} Hz: |H| = {_h(NOTCH_F0):.6f}"
          f" ({20*math.log10(_h(NOTCH_F0)):.1f} dB)")
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
    print(f"      0x{TAP_ADDR:05X}  427 tap  gp-0x6ABC -> gp-0x6B86   (0x{TAP_OLD:04X} ->"
          f" 0x{TAP_NEW:04X})   THE NOTCH LANE ITSELF")
    check(u16(code, TAP_ADDR) == TAP_NEW and TAP_NEW % 2 == 0,
          "  reads back, and the displacement is EVEN as ld.h requires")
    check(code[SAR_ADDR] == base[SAR_ADDR] == SAR_HELD,
          "  the packer sar is UNCHANGED -- this adds exactly TWO telemetry bytes")
    print("      => a -74 dB null in the probed spectrum is DIRECT confirmation that the gate")
    print("         opens and the notch is running, and where it sits.  427 samples at 49.9 Hz")
    print("         (Nyquist 24.95), so a 20 Hz null lands DIRECTLY in band.")

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
    exempt = {TAP_ADDR, TAP_ADDR + 1} | {a2 for k in BQ for a2 in range(BQ[k], BQ[k] + 4)}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (biquad + tap exempted)")

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
    check(payload == 14, f"exactly 14 payload bytes ({payload} found)"
          " -- 12 biquad (3 of 4 bytes per float) + 2 tap")
    _functional = sum(hi - lo for lo, hi in runs
                      if not any(lo < t + 4 and t < hi for t in _tr)
                      and not (TAP_ADDR <= lo < TAP_ADDR + 2))  # tap = telemetry
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
    FF.assert_x31_checksum(rwd, "V144 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V144-V122BASE-NOTCH20HZ-427.6B86"
    img_out = plain_image_path(f"_v144_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V144_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
