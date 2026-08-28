#!/usr/bin/env python3
r"""
V137 -- V122 + alpha2 8 -> 5.  ONE cal.  THE CORRECTION AFTER V133's ON-CAR REGRESSION.

WHY THIS BUILD EXISTS: V133 MADE THE CAR WORSE, AND IT WAS A SIX-VARIABLE BUILD
--------------------------------------------------------------------------------
Operator report, 2026-08-28, on V133:
    "V133 has a massive, violent grinding after enabling LKAS which continues after
     disengaging.  I also got some grind #2 while disengaged and doing a hard turn."

V133 was presented to him as "every measured-good edit ever flown" and as a clean test of
V62's Lever A.  IT WAS NOT.  Against V122 -- the last FLOWN build, and the one he described as
"better, still ever so slight ... in rare moments" -- V133 moved SIX cells:

    cell                                       V122      V133     direction
    0xC407E  b26 clamp = APPARENT MASS ceiling   511      1023     2.00x MORE headroom
    0xC4004    its float twin                    0.5       1.0     (matched, correct per se)
    0x3AB76  Lever A r26 arm                    0xAA      0xA9     restored
    0x3AC20  Lever A r24 arm                    0xAA      0xA9     restored  <- SEE BELOW
    0xC40DC  alpha2                                8         5     the one GOOD direction
    0xC640A  oscillation branch Y              -8192     -1966     de-fanged
    0xC6CD0  LKAS gain                          5346      7128     6x -> 8x, +33 % EXCITATION

ATTRIBUTION OF HIS TWO SYMPTOMS -- each maps to a different edit, and BOTH WERE ON RECORD
------------------------------------------------------------------------------------------
1. "grind #2 while DISENGAGED doing a hard turn"  ->  LEVER A's r24 ARM (0x3AC20).
   The LKAS gain is engaged-only and cannot produce a DISENGAGED symptom; the r24 arm is in the
   aggregator and is not LKAS-gated.  And the kit's own memory says it outright:
       accord-v81-carries-neither-grind1-fix:
       "Lever A = V62's sar x2 (r24 half CAUSED grind #2)"
   => the half with a RECORDED history of causing this exact symptom was restored anyway.
      This was a straight miss: the record existed and was not checked before recommending V133.

2. "massive violent grinding ... CONTINUES AFTER DISENGAGING"  ->  THE CLAMP (0xC407E), with the
   8x gain as a likely amplifier of its onset.
   gp-0x6b26 = -K * acceleration is APPARENT MASS.  Raising its clamp 511 -> 1023 doubles the
   peak apparent mass the lane can deliver.  Less apparent mass raises zeta = c/(2*sqrt(km)) and
   de-resonates; MORE apparent mass lowers zeta and makes the mode sharper.  V133 moved it the
   WRONG WAY.  0xC407E is NOT mode-gated, which is exactly why disengaging does not stop it.
   The V133 builder sold this edit as "de-rails without changing linear damping" -- true only of
   the LINEAR region, and it ignored that peaks may now reach twice as far.
   The 6x -> 8x gain adds 33 % more excitation into a lightly-damped resonance (zeta 0.017-0.036,
   Q 14-29), against the operator's explicit instruction: "If youre going to increase gain make
   sure we dont get even more oscillation and grinding."

WHAT THIS BUILD DOES: ONE CELL, ON THE BASE HE LIKED
------------------------------------------------------
    BASE = V122 (flown, known-good).   0xC40DC alpha2 8 -> 5.   Nothing else.
Every V133 edit implicated above stays at its V122 value: the clamp stays 511, its float twin
stays 0.5, BOTH Lever A arms stay stock 0xAA, and the LKAS gain stays 5346 (6x).

WHY alpha2, AND WHY IT IS *NOT* DAMAGED BY V133's RESULT
---------------------------------------------------------
The single-variable on-car ladder (engaged/manual 18-22 Hz at creep, speed-matched, 30-40 Hz
control guard passed on all four routes):
    V111 -> V112 : SAME alpha2 (14), same gain, same relay slope, ONLY the knee moves
                   => 4.40 -> 4.74.  THE KNEE BOUGHT NOTHING (inside V112's own 3 % spread).
    V112 -> V122 : alpha2 14 -> 8    => 4.74 -> 3.38, a 1.35x improvement ABOVE that noise.
    => alpha2 is the lever with a detectable effect; the knee is null.
And the transfer function agrees: |H| over 18-22 Hz for
H(f) = 64*H1(alpha0=37/128)*(1-z^-1)*H2(alpha2/64) falls 5.4903 (a2=8) -> 4.0982 (a2=5) = 1.34x.

*** V133's regression does NOT implicate alpha2.  It REINFORCES the mechanism. ***
V133 was, accidentally, a large experiment in the OPPOSITE direction on the same physical
quantity: it doubled the ceiling on apparent mass.  It produced a large WORSENING.  That is what
"apparent mass drives this resonance" predicts.  alpha2 lowers the same quantity's HF content.

SIZING: 8 -> 5 IS A 1.60x STEP, IN LINE WITH EVERY alpha2 STEP EVER FLOWN
--------------------------------------------------------------------------
    22 -> 14  = 1.57x   (V91  -> V111)      FLOWN, fault-free
    14 ->  8  = 1.75x   (V112 -> V122)      FLOWN, fault-free
     8 ->  5  = 1.60x   THIS BUILD
alpha2 = 5 is also a value that has already been ENCODED and verified in V124 and V133, so the
byte is not novel -- only the base it sits on is.  A more aggressive 8 -> 2 (4.00x) is built
separately as V138; after a regression, this build deliberately takes the in-family step.

EVIDENCE vs BELIEF
------------------
[EVIDENCE] the six-cell V122->V133 diff read from the two images; the flown alpha2 ladder and its
           guard-passing endpoints; the transfer function; that 0xC407E is not mode-gated; that
           the LKAS gain is engaged-only and so cannot explain a disengaged symptom; the kit
           memory tying Lever A's r24 half to grind #2.
[BELIEF]   the split of blame between the clamp and the 8x gain for symptom 1.  Both moved, and
           this build reverts BOTH, so it does not resolve that split -- it avoids it.
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
WRITE_MODE = os.environ.get("ACCORD_V137_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_OLD, ALPHA2_NEW = 0xC40DC, 8, 5
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
    print("  V137 -- V122 + alpha2 8 -> 5.  ONE cal.  The correction after V133's regression.")
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
    check(u16(base, ALPHA2_CAL) == ALPHA2_OLD, f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_OLD}")
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
    struct.pack_into("<H", code, ALPHA2_CAL, ALPHA2_NEW)
    attributed |= {ALPHA2_CAL, ALPHA2_CAL + 1}
    print(f"      0x{ALPHA2_CAL:05X}  alpha2  {ALPHA2_OLD} -> {ALPHA2_NEW}")
    check(u16(code, ALPHA2_CAL) == ALPHA2_NEW, f"  reads back {ALPHA2_NEW}")

    print("\n  [4] SIZING -- an IN-FAMILY step, deliberately conservative after a regression")
    for hi, lo, who in ALPHA2_STEPS:
        print(f"      alpha2 {hi:3d} -> {lo:3d}  = {hi/lo:.2f}x   {who}   FLOWN, fault-free")
    print(f"      alpha2 {ALPHA2_OLD:3d} -> {ALPHA2_NEW:3d}  = {ALPHA2_OLD/ALPHA2_NEW:.2f}x"
          f"   THIS BUILD")
    _max_flown = max(hi / lo for hi, lo, _ in ALPHA2_STEPS)
    check(ALPHA2_OLD / ALPHA2_NEW <= _max_flown * 1.01,
          f"  \U0001f6d1 THE SIZING GATE: {ALPHA2_OLD/ALPHA2_NEW:.2f}x is no larger than the"
          f" biggest alpha2 step ever flown ({_max_flown:.2f}x)")
    check(ALPHA2_NEW < ALPHA2_OLD < ALPHA2_STOCK, "  the edit moves DOWN the ladder, never up")
    check(ALPHA2_NEW >= 1, "  alpha2 >= 1: at 0 the EMA freezes and the lane dies")
    m_old, m_new = band_mag(ALPHA2_OLD), band_mag(ALPHA2_NEW)
    print(f"      |H| over {SIG_BAND[0]:.0f}-{SIG_BAND[1]:.0f} Hz:  {m_old:.4f} -> {m_new:.4f}"
          f"  = {m_old/m_new:.2f}x less inertia lane")
    check(m_new < m_old, "  the lane magnitude DECREASES in the grind band")

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
    for a, w, nm in ((KNEE_CAL, 2, "relay knee"), (K1_CAL, 2, "K1"), (OFF_CAL, 2, "relay offset"),
                     (POLE_CAL, 2, "friction EMA pole"), (RESID_CAL, 2, "residual scale"),
                     (ARM_CAL, 2, "detector arm threshold"), (0xC40DA, 2, "the >>7 EMA twin")):
        check(rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} {nm} byte-identical to V122")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- cal-only, OUTSIDE the"
          f" bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {ALPHA2_CAL, ALPHA2_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (alpha2 exempted)")

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
    check(payload == 1, f"exactly 1 payload byte ({payload} found)")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V137 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V137-V122BASE-ALPHA2.5"
    img_out = plain_image_path(f"_v137_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V137_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
