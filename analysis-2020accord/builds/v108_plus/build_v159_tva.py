#!/usr/bin/env python3
r"""
V159 -- FLATTEN THE K_p SCHEDULE'S FIRST SEGMENT.  0xC6728 : 832 -> 704.  Base = V122.
        Removes an 18.2% PARAMETRIC GAIN MODULATION at 2f, at the symptom's own operating point.

THE MECHANISM
-------------
FUN_0003a382 is a three-term torque-tracking servo, and its K_p is a 4-knot LERP indexed on
gp-0x6ac0 -- the RECTIFIED motor rate.  Layout confirmed from the decompile itself:
        X[0] = tp+0x7b1e   X[last] = tp+0x7b24   =>  X is 4 halfwords at 0xC671E
        Y[0] = tp+0x7b26   Y[last] = tp+0x7b2c   =>  Y is 4 halfwords at 0xC6726
        X = [96, 104, 608, 704]      Y = [704, 832, 832, 832]

The golden model records the MEASURED in-burst operating point as gp-0x6ac0 = 99 counts [94, 113].
        99 lies INSIDE the FIRST segment, X 96 -> 104, where Y rises 704 -> 832
        = an 18.2% gain swing across only 8 counts

=> and because gp-0x6ac0 is RECTIFIED, it sweeps at TWICE the oscillation frequency: during a
   7.8 Hz ratchet it traverses that window at 15.6 Hz.
=> THE PID's PROPORTIONAL GAIN IS PARAMETRICALLY MODULATED ~18% AT 2f, AT THE SYMPTOM'S OWN
   OPERATING POINT.  This is STRUCTURAL -- it is present on STOCK.

This is exactly what the golden model predicted qualitatively but never located:
    "a rate-scheduled gain on a RECTIFIED index (which sweeps at 2f) interacts with the parametric
     pump" ... "[GATE 2 -- size any FactorE edit against this, not just dose]"
and it is a candidate named source for accord-v59-parametric-pump-marginal ("the pump is real but
MARGINAL"), which has never had one.

THE EDIT, AND WHY THIS DIRECTION
---------------------------------
        stock   Y = [704, 832, 832, 832]
        V159    Y = [704, 704, 832, 832]      Y[1] := Y[0]
=> segment 0 (X 96..104) becomes FLAT, so the 2f sweep sees NO gain change there.
=> DOWNWARD is the safe direction: it LOWERS K_p between 96 and 104 rather than raising it.
=> the ramp does not vanish, it MOVES to X 104..608 -- the same 704->832 rise spread over a
   6.3x WIDER span, so the schedule's overall shape is preserved and gentled, not deleted.
=> MONOTONE NON-DECREASING is preserved ([704,704,832,832]) -- the shape rule V157 broke.

WHY IT IS SAFE
--------------
[EVIDENCE] RULE 7 SATISFIED: the decompile reads this table with BARE tp displacements
(ld.hu 0x7b1e / 0x7b20 / 0x7b24 / 0x7b26 / 0x7b2c, tp) and NO index register => it is a FLAT scalar
table shared by all modes.  There is no mode to get wrong.
[EVIDENCE] 0xC6728 is VIRGIN: 832 on all 158 build images.
[EVIDENCE] K_p only ever DECREASES here, so no clamp can be newly reached and no saturation
introduced; the servo's own +-0x2800 clamps are untouched.
=> cal-only, one halfword, outside the cave/bricking class.

WHAT IS NOT ESTABLISHED
-----------------------
[BELIEF] that removing an 18.2% parametric modulation is audible.  The mechanism and its magnitude
are EVIDENCE; its share of the symptom is not measured.
[NOTE] lanes B (tp+0x7b0a) and C (tp+0x7ade) read NON-ASCENDING X under the same layout
([256,256,0,8] and [717,0,0,5]).  That anomaly is unexplained and is left OPEN -- it does not
affect lane A, whose layout is confirmed instruction-by-instruction.
[NOTE] this does NOT close V158's shared-axis GATE 2; it addresses the PID side of that coupling,
not the FactorE side.  V158 and V159 are INDEPENDENT single-lever builds.

BASE = V122.  knee 3000 HELD, K1 1020, Lever B 5244 HELD, alpha2 8, observer poles stock.
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
WRITE_MODE = os.environ.get("ACCORD_V159_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
LB_CAL, LB_HELD = 0xC6446, 5244                 # Lever B -- HELD (changing it is V149)
LB_POST, LB_STOCK = 0xC6442, 512               # count>0 multiplier; stock Lever B
CNT_HI, CNT_LO, DTC_LIM = 0xC61FA, 0xC61F8, 0xC6500
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
KNEE_CAL, KNEE_OLD = 0xC40BC, 3000                   # the relay knee -- HELD (that is V151)
KP_X  = 0xC671E                                      # K_p LERP X[4], axis = gp-0x6ac0
KP_Y  = 0xC6726                                      # K_p LERP Y[4]
KP_Y1 = 0xC6728                                      # Y[1] -- THE EDIT
KP_Y1_OLD, KP_Y1_NEW = 832, 704                      # := Y[0], flattening segment 0
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
    check(u16(base, ALPHA2_CAL) == ALPHA2_HELD,
          f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_HELD} -- HELD; Lever-B-only build")
    check(u16(base, KNEE_CAL) == KNEE_OLD and u16(base, K1_CAL) == K1_VAL,
          f"  relay knee {KNEE_OLD} / K1 {K1_VAL} -- V122's tuned pair")
    check(u16(base, OFF_CAL) == OFF_VAL and u16(base, POLE_CAL) == POLE_VAL,
          "  relay offset 0 and friction EMA pole 408, both V122")
    check(u16(base, RESID_CAL) == RESID_VAL, f"  0x{RESID_CAL:05X} residual scale = {RESID_VAL}")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(base, a) if want < 0 else (base[a] if w == 1 else u16(base, a))
        check(got == want, f"  0x{a:05X} = {want} in the base -- {why.split('.')[0]}")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(abs(_fb - CEIL_F_VAL) < 1e-9 and abs(_fb * 1024 - (511 + 1)) < 1e-6,
          f"  0x{CEIL_F:05X} float twin = {CEIL_F_VAL} and float*1024 == int+1 ({_fb*1024:.0f})")

    print("\n  [3] THE EDIT -- ONE HALFWORD")
    _X = [u16(base, KP_X + 2*i) for i in range(4)]
    _Y = [u16(base, KP_Y + 2*i) for i in range(4)]
    check(_X == [96, 104, 608, 704], f"  K_p LERP X = {_X} at 0x{KP_X:05X} (axis gp-0x6ac0)")
    check(_Y == [704, 832, 832, 832], f"  K_p LERP Y = {_Y} at 0x{KP_Y:05X}")
    check(u16(base, KP_Y1) == KP_Y1_OLD, f"  0x{KP_Y1:05X} Y[1] = {KP_Y1_OLD} in the base")
    struct.pack_into("<H", code, KP_Y1, KP_Y1_NEW)
    attributed |= {KP_Y1, KP_Y1 + 1}
    print(f"      0x{KP_Y1:05X}  K_p Y[1]  {KP_Y1_OLD} -> {KP_Y1_NEW}")
    check(u16(code, KP_Y1) == KP_Y1_NEW, f"  reads back {KP_Y1_NEW}")

    print("\n  [4] THE 2f PARAMETRIC MODULATION AT THE OPERATING POINT IS REMOVED")
    _Yn = [u16(code, KP_Y + 2*i) for i in range(4)]
    _sw_old = 100.0 * (_Y[1] - _Y[0]) / _Y[0]
    _sw_new = 100.0 * (_Yn[1] - _Yn[0]) / _Yn[0]
    check(_sw_new == 0.0,
          f"  \U0001f6d1 THE MODULATION GATE: segment 0 spans X {_X[0]}..{_X[1]} and the golden"
          f" model's MEASURED in-burst operating point is gp-0x6ac0 = 99 [94,113] -- INSIDE it."
          f"  Swing across that segment {_sw_old:.1f}% -> {_sw_new:.1f}%.  gp-0x6ac0 is RECTIFIED,"
          f" so it sweeps at 2f = 15.6 Hz during a 7.8 Hz ratchet: this removes an 18% PARAMETRIC"
          f" modulation of K_p at the symptom's own operating point.")
    check(KP_Y1_NEW < KP_Y1_OLD,
          f"  \U0001f6d1 THE DIRECTION GATE: {KP_Y1_OLD} -> {KP_Y1_NEW} LOWERS K_p between X {_X[0]}"
          f" and {_X[1]}.  Downward cannot reach a clamp that was not already reachable, and the"
          f" servo's +-0x2800 clamps are untouched.")
    check(_Yn == sorted(_Yn),
          f"  \U0001f6d1 THE SHAPE GATE: Y = {_Yn} is MONOTONE NON-DECREASING -- the rule V157 broke."
          f"  The ramp is not deleted, it MOVES to X {_X[1]}..{_X[2]}, the same 704->832 rise over a"
          f" {(_X[2]-_X[1])/(_X[1]-_X[0]):.1f}x wider span.")
    check(_X == [u16(code, KP_X + 2*i) for i in range(4)],
          f"  the X axis is UNTOUCHED {_X} -- no knot moves")
    check(u16(code, KNEE_CAL) == KNEE_OLD and u16(code, LB_CAL) == LB_HELD,
          f"  knee HELD {KNEE_OLD} (V151) and Lever B HELD {LB_HELD}")

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
    for a, w, nm in ((ALPHA2_CAL, 2, "alpha2 -- HELD, Lever-B-only build"),
                     (0xC61F6, 2, "pump deadband -- HELD at Honda 3"),
                     (K1_CAL, 2, "K1 -- HELD, knee-only step"), (OFF_CAL, 2, "relay offset"),
                     (LB_CAL, 2, "Lever B -- HELD, that is V149"),
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
    exempt = {KP_Y1, KP_Y1 + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the K_p Y[1] knot exempted)")

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
    check(payload == 2, f"exactly 2 payload bytes ({payload} found) -- the K_p Y[1] u16")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V159 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V159-V122BASE-KP.KNEE.FLATTENED"
    img_out = plain_image_path(f"_v159_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V159_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
