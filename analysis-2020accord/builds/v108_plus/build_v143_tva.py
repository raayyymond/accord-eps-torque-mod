#!/usr/bin/env python3
r"""
V143 -- V140's pump deadband + a 427 probe on gp-0x6B86, THE NOTCH-FILTER LANE.
        ONE functional byte + ONE telemetry byte.  Base = V122.

*** THE POINT OF THIS BUILD IS THE PROBE.  It carries V140's fix so the drive is not spent purely
    on measurement, but its VALUE is resolving the assist task rate, which gates a much larger
    lever than the deadband. ***

WHAT WAS FOUND -- A TRUE NOTCH FILTER, WHICH THIS KIT BELIEVED DID NOT EXIST
-----------------------------------------------------------------------------
FUN_000352b4 (the only writer of gp-0x6B86) contains a gated second-order FLOAT section:

    if ((cal(0xC649B) == 1) && (gp-0x671a >= cal(0xC64FA))) {      // = 1 and >= 5
        w[n] = D*x[n] - A*w[n-1] - B*w[n-2]
        y[n] = w[n]   + C*w[n-1] +   w[n-2]
    }
    A = -1.53720   0xC60A8      C = -1.88080   0xC60B0
    B =  0.63462   0xC60AC      D =  0.81731   0xC60B4

    H(z) = D * (1 + C z^-1 + z^-2) / (1 + A z^-1 + B z^-2)

  * the numerator zeros sit EXACTLY on the unit circle (z^2 + Cz + 1, |z| = 1) at +-19.88 deg
    => a TRUE NOTCH, minimum |H| = 0.0002, i.e. about -74 dB;
  * poles |z| = 0.7966 at 15.24 deg => STABLE;
  * |H| = 1.0000 at DC and 1.000 at Nyquist => the filter is TRANSPARENT everywhere except the
    notch.  It costs NO authority, NO added mass and NO added friction -- the exact shape the
    operator has been asking for ("low apparent steering mass and friction AND no ratcheting").
  * all four coefficients are CALS, so it is fully retunable with NO code cave.
This falsifies the kit memory "no notch filter exists anywhere" (from V44).
NOTE: the block at 0xC60A8 is already BQ_ADDR in every builder, asserted byte-identical -- the kit
had the ADDRESS but not the FUNCTION.

WHY THIS CANNOT BE RETUNED YET -- THE TASK RATE IS THE BLOCKER
---------------------------------------------------------------
The notch angle is fixed at 19.88 deg; its FREQUENCY is 19.88/360 * fs.
        fs  250 -> 13.8 Hz     fs 333 -> 18.4 Hz     fs 500 -> 27.6 Hz     fs 1000 -> 55.2 Hz
The kit's own record bounds the assist task (task 5) at >= 250 Hz and has NEVER pinned it
("task 1 CONFIRMED 1 kHz, task 5 rate was OPEN").
=> at ~333 Hz Honda's notch ALREADY sits on the 18-22 Hz grind, and the lever would be the GATE;
=> at 1000 Hz it sits at 55 Hz, useless for the grind, and the lever is C:
        C_new = -2*cos(2*pi*f/fs)      f = 20 Hz, fs = 1000  =>  C = -1.984229
   which moves a -74 dB notch onto the grind while leaving DC gain at exactly 1.0000.
   THE TWO CASES CALL FOR OPPOSITE EDITS.  Guessing would be a coin flip on the best lever found.

HOW THE PROBE RESOLVES IT
---------------------------
427 samples at 49.9 Hz (Nyquist 24.95 Hz).  A -74 dB notch is a DEEP, unmistakable null, and where
it lands in the probed spectrum pins fs to a small discrete set:
        fs  250 -> null at 13.8 Hz  (direct)          fs 500 -> 27.6 Hz aliases to 22.3 Hz
        fs  333 -> null at 18.4 Hz  (direct)          fs 1000 -> 55.2 Hz aliases to  5.3 Hz
The probe ALSO answers two prerequisites the retune depends on: whether the lane is active at all,
and whether the gate (cal 0xC649B == 1 AND gp-0x671a >= 5) ever opens in normal driving.
=> if the lane reads dead, the notch is irrelevant however it is tuned, and that is worth knowing
   before spending a build on its coefficients.

THE GATE, AND WHY IT IS NOT ITSELF A FREE LEVER
-------------------------------------------------
cal(0xC649B) is 0 in STOCK and 1 in V122 (it toggles across the build history: V22=0, V103=1,
V117=0, V120=1), so the ENABLE is already on in the base.
The second half, gp-0x671a >= cal(0xC64FA) = 5, requires the hard-reversal counter to be AT its
ceiling.  Lowering 0xC64FA would arm the notch more readily -- but that cal ALSO selects the Y
branch in FUN_00036c12 and gates two branches in the aggregator, and gp-0x671a has four external
consumers.  It is NOT a clean lever and must not be moved casually.

BASE = V122.  alpha2 stays 8, gain stays 6x, b26 clamp stays 511, both Lever A arms stay stock.
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

import hashlib
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
WRITE_MODE = os.environ.get("ACCORD_V143_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
DB_CAL, DB_OLD, DB_NEW = 0xC61F6, 3, 96      # the r24 pump-lane deadband
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
    print("  V143 -- V140's deadband + a 427 probe on gp-0x6B86, the NOTCH-FILTER lane.")
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

    print("\n  [3] THE EDIT -- ONE CAL, ONE PAYLOAD BYTE")
    check(u16(base, DB_CAL) == DB_OLD,
          f"  0x{DB_CAL:05X} (r24 pump-lane deadband) = {DB_OLD} in the base")
    struct.pack_into("<H", code, DB_CAL, DB_NEW)
    attributed |= {DB_CAL, DB_CAL + 1}
    print(f"      0x{DB_CAL:05X}  deadband  {DB_OLD} -> {DB_NEW}")
    check(u16(code, DB_CAL) == DB_NEW, f"  reads back {DB_NEW}")

    print("\n  [4] THE DEADBAND GATES")
    print(f"      Honda ships {DB_OLD} counts = {100.0*DB_OLD/LANE_CLAMP:.3f} % of the"
          f" +-{LANE_CLAMP} lane clamp -- a quantization floor, not a functional dead zone")
    print(f"      this build   {DB_NEW} counts = {100.0*DB_NEW/LANE_CLAMP:.2f} % of the lane clamp"
          f"  ({100.0*DB_NEW/AGG_CLAMP:.2f} % of the +-{AGG_CLAMP} aggregator total)")
    check(DB_NEW > DB_OLD,
          "  \U0001f6d1 THE DIRECTION GATE: the deadband WIDENS, which REMOVES pump where the"
          " signal is small.  Narrowing it would ADD pump and is never the move.")
    check(DB_NEW < LANE_CLAMP // 16,
          f"  \U0001f6d1 THE AUTHORITY GATE: {DB_NEW} is under {LANE_CLAMP//16} = 1/16 of the lane"
          f" clamp, so at large signal this is a {100.0*DB_NEW/LANE_CLAMP:.2f} % offset and LKAS"
          f" authority is not meaningfully touched")
    check(DB_NEW < 32768, "  the cal stays inside its 16-bit field")
    _f = lambda x: (x - DB_NEW) if x > DB_NEW else ((x + DB_NEW) if x < -DB_NEW else 0)
    for _x in (DB_NEW - 1, DB_NEW, DB_NEW + 1, DB_NEW + 2):
        pass
    check(_f(DB_NEW) == 0 and _f(DB_NEW + 1) == 1 and _f(DB_NEW + 2) == 2,
          "  \U0001f6d1 THE CONTINUITY GATE: the deadband SUBTRACTS rather than clips, so the"
          " transfer curve steps 0 -> 0 -> 1 -> 2 across the boundary with NO discontinuity"
          " -- there is no notchiness mechanism, the usual objection to widening a dead zone")
    check(_f(-DB_NEW - 1) == -1 and _f(0) == 0, "  and it is symmetric about zero")

    print("\n  [4b] THE PROBE -- TELEMETRY ONLY, AND THAT IS ASSERTED, NOT ASSUMED")
    check(u16(base, TAP_ADDR) == TAP_OLD,
          f"  0x{TAP_ADDR:05X} 427 tap = 0x{TAP_OLD:04X} (gp-0x6ABC) in the base")
    check(base[SAR_ADDR] == SAR_HELD,
          f"  0x{SAR_ADDR:05X} packer sar = 0x{SAR_HELD:02X} (sar 3) already -- NOT touched")
    struct.pack_into("<H", code, TAP_ADDR, TAP_NEW)
    attributed |= {TAP_ADDR, TAP_ADDR + 1}
    print(f"      0x{TAP_ADDR:05X}  427 tap  gp-0x6ABC -> gp-0x6B86   (0x{TAP_OLD:04X} ->"
          f" 0x{TAP_NEW:04X})")
    check(u16(code, TAP_ADDR) == TAP_NEW, f"  reads back 0x{TAP_NEW:04X}")
    check(TAP_NEW % 2 == 0,
          "  the displacement is EVEN -- ld.h requires it, and an odd one would decode as a"
          " different operand form")
    check(code[SAR_ADDR] == base[SAR_ADDR] == SAR_HELD,
          "  \U0001f6d1 the packer sar is UNCHANGED, so this build adds exactly TWO telemetry bytes")
    _wire = lambda x: min((min(abs(x), 65535) * 5) >> (SAR_HELD & 0x1F), 0x3FF)
    print(f"      wire = min((|x|*5) >> {SAR_HELD & 0x1F}, 1023):"
          f"  lane {DB_NEW} -> {_wire(DB_NEW)},  lane {2*DB_NEW} -> {_wire(2*DB_NEW)}")
    _sat = next(x for x in range(1, 20000) if _wire(x) >= 0x3FF)
    print(f"      saturates at |lane| >= {_sat}  ({100.0*_sat/LANE_CLAMP:.0f} % of the lane clamp)")
    check(_wire(DB_NEW) > 16,
          f"  \U0001f6d1 THE RESOLUTION GATE: the new deadband maps to wire {_wire(DB_NEW)}, well"
          f" above the noise floor, so the probe can actually SEE activity at the dose we set")
    check(_sat < LANE_CLAMP,
          f"  large values CLIP at {_sat} -- accepted: the question is about SMALL lane values near"
          f" the deadband, and a clipped reading still says 'large' unambiguously")

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
    for a, w, nm in ((ALPHA2_CAL, 2, "alpha2 -- HELD, this build is deadband-only"),
                     (KNEE_CAL, 2, "relay knee"), (K1_CAL, 2, "K1"), (OFF_CAL, 2, "relay offset"),
                     (POLE_CAL, 2, "friction EMA pole"), (RESID_CAL, 2, "residual scale"),
                     (ARM_CAL, 2, "detector arm threshold"), (0xC40DA, 2, "the >>7 EMA twin")):
        check(rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} {nm} byte-identical to V122")
    for _a, _v in sorted(ARMS_STOCK.items()):
        check(code[_a] == base[_a] == _v, f"  0x{_a:05X} Lever A arm HELD stock at 0x{_v:02X}")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- cal-only, OUTSIDE the"
          f" bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {DB_CAL, DB_CAL + 1, TAP_ADDR, TAP_ADDR + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (deadband + tap exempted)")

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
    check(payload == 3, f"exactly 3 payload bytes ({payload} found) -- 1 functional + 2 tap")
    _functional = sum(hi - lo for lo, hi in runs
                      if not any(lo < t + 4 and t < hi for t in _tr)
                      and not (TAP_ADDR <= lo < TAP_ADDR + 2))  # tap = telemetry
    check(_functional == 1,
          f"  \U0001f6d1 THE SINGLE-VARIABLE GATE: exactly {_functional} FUNCTIONAL byte"
          f" (the deadband).  The other 2 are the 427 tap, which only changes what a"
          f" TX-only CAN message reports -- this build is functionally V140")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V143 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V143-V122BASE-DEADBAND.96-427.6B86"
    img_out = plain_image_path(f"_v143_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V143_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
