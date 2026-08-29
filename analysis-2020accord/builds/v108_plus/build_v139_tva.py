#!/usr/bin/env python3
r"""
V139 -- V122 + BOTH r24/r26 aggregator arms sar 10 -> 11.  HALVE A CONFIRMED PUMP.

*** CO-PRIMARY WITH V147 (re-elevated 2026-08-29).  Read the honest caveat at the bottom. ***
This build was demoted earlier partly on the alpha2-vs-knee single-variable ladder.  THAT LADDER
IS RETRACTED: the between-build endpoint it used has a measured 20-36x noise floor and the
ladder differences were 1.08-1.40x.  V139's OWN rationale never used that endpoint -- it rests
on (1) gp-0x6752 = -1 verified three ways including on-car, (2) V133 doubling these exact bytes
and the operator reporting violent grinding, and (3) reducing a feedback magnitude being safe by
construction.  All three survive.  V137/V138 (the alpha2 ladder) are the builds that lost their
rationale, not this one.

WHY THIS LEVER, AND WHY NOW
-----------------------------
V133 DOUBLED these two arms (sar 10 -> 9, "V62 Lever A") and the operator reported:
    "massive, violent grinding after enabling LKAS which continues after disengaging.
     I also got some grind #2 while disengaged and doing a hard turn."
That is a LARGE, unambiguous on-car effect from these exact two bytes.  Most levers this kit tests
come back null; this one is demonstrably POTENT, and its BAD direction is now known.

AND THE MECHANISM SAYS WHICH DIRECTION IS GOOD -- READ FROM THE DISASSEMBLY
----------------------------------------------------------------------------
    0x3AB70  sar 0xa, r6            aa32
    0x3AB72  mul r8, r6, r0
    0x3AB76  sar 0xa, r6            aa32   <- r26 arm, THIS BUILD
    0x3AB78  ld.b -0x6752, gp, r14         <- THE POLARITY, loaded immediately after
    0x3AB7C  mov r14, r15
    0x3AB7E  mul r6, r15, r0               <- the arm is MULTIPLIED BY that polarity
    0x3AC20  sar 0xa, r8            aa42   <- r24 arm, THIS BUILD
    0x3AC24  cmp r12, r8                   <- vs cal 0xC61F6, a limit: a SMALLER arm cannot exceed it
gp-0x6752 is -1, VERIFIED THREE INDEPENDENT WAYS including ON-CAR (V98 b3 rung read
(gp-0x6752 >= 0) with duty 0.0000 over 17,983 frames / 5 routes).  The flash config table that
sets it lives at 0x1000-0x15xx, BELOW the 0x13000 floor every .rwd writes from, so no build in this
kit history could ever have changed it.
=> r24/r26 is a CONFIRMED PUMP.  x2 on a pump is 2x the pumping, which is exactly the violent
   oscillation V133 produced.  sar 10 -> 11 HALVES it.

SAFE BY CONSTRUCTION
--------------------
This REDUCES the magnitude of a feedback term.  Reducing a feedback magnitude cannot destabilise a
stable loop whatever its phase; RAISING is the classic destabiliser, and V133 is this kit own
fresh demonstration of that.  The r24 arm comparison against cal 0xC61F6 is only made easier.
It is a 2-byte IN-PLACE immediate edit -- no cave, no branch retarget, no displacement change --
so it is outside the class that bricked V24, V27 and V48B.

THE HONEST CAVEAT -- MONOTONICITY IS *NOT* ESTABLISHED
--------------------------------------------------------
Knowing sar 9 is much WORSE than sar 10 does NOT prove sar 11 is BETTER than sar 10.  Honda
sar 10 could be the optimum with both directions worse.  Weighing it:
  FOR : V62 measured sar 9 as a FIX (18-22 Hz down 8-42x) on a 4x-GAIN base, and the same edit is a
        REGRESSION on a 6x/8x base => the optimum MOVES DOWN as base gain rises, and this build
        moves in that direction.
  AGAINST: scaling V62 4x optimum to V122 6x base lands BETWEEN sar 9 and sar 10, which argues
        Honda sar 10 is already about right for a 6x base and sar 11 OVERSHOOTS.
=> [BELIEF, not EVIDENCE] that halving helps.  This build earns a drive because the lever is PROVEN
   POTENT and the move is SAFE, not because the direction is established.  Expected failure mode:
   the steering goes number/vaguer without the grind improving -- in which case revert to V122.

BASE = V122, THE LAST FLOWN KNOWN-GOOD BUILD.  alpha2 stays 8, gain stays 6x, clamp stays 511.
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
WRITE_MODE = os.environ.get("ACCORD_V139_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
ARMS = {0x3AB76: ("r26 arm", 0x32), 0x3AC20: ("r24 arm", 0x42)}
SAR_OLD, SAR_NEW = 0xAA, 0xAB            # sar 0xa -> sar 0xb  =  HALVE the arm
POLARITY_NOTE = "gp-0x6752 = -1, verified 3 ways incl. on-car => these arms PUMP"
ALPHA2_STOCK = 22
ALPHA2_STEPS = ((22, 14, "V91  -> V111"), (14, 8, "V112 -> V122"))   # flown, fault-free

# ---- THE V133 CELLS THIS BUILD LEAVES AT V122 (the two ARMS are THIS build edit) -------------------
REVERTED = {
    0xC407E: (2, 511, "b26 clamp = APPARENT MASS ceiling.  V133 doubled it to 1023 and the car"
                      " got VIOLENTLY worse, persisting after disengage because it is NOT"
                      " mode-gated."),
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
    print("  V139 -- V122 + BOTH r24/r26 pump arms sar 10 -> 11.  Halve a CONFIRMED pump.")
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
          f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_HELD} -- HELD; arms-only build")
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

    print("\n  [3] THE EDIT -- TWO INSTRUCTION BYTES, IMMEDIATE FIELD ONLY")
    for a_, (nm, hi) in sorted(ARMS.items()):
        check(base[a_] == SAR_OLD and base[a_ + 1] == hi,
              f"  0x{a_:05X} ({nm}) is `sar 0x{SAR_OLD & 0x1F:x}` -- bytes {SAR_OLD:02x}{hi:02x}")
        code[a_] = SAR_NEW
        attributed.add(a_)
        print(f"      0x{a_:05X}  {nm:8s}  sar 0x{SAR_OLD & 0x1F:x} -> sar 0x{SAR_NEW & 0x1F:x}"
              f"   ({SAR_OLD:02x} -> {SAR_NEW:02x})   arm HALVED")

    print("\n  [4] THE INSTRUCTION-INTEGRITY GATE -- only the shift immediate may move")
    check((SAR_OLD & ~0x1F) == (SAR_NEW & ~0x1F),
          f"  \U0001f6d1 the OPCODE field is untouched (0x{SAR_OLD & ~0x1F:02X}) -- only the low"
          f" 5 bits, which are the shift immediate, differ")
    check((SAR_NEW & 0x1F) == (SAR_OLD & 0x1F) + 1,
          f"  the immediate goes {SAR_OLD & 0x1F} -> {SAR_NEW & 0x1F}, exactly ONE more shift")
    check((SAR_NEW & 0x1F) > (SAR_OLD & 0x1F),
          "  \U0001f6d1 THE DIRECTION GATE: a LARGER right-shift means a SMALLER arm.  This"
          " REDUCES a feedback magnitude, which cannot destabilise a stable loop whatever its"
          " phase -- RAISING is the destabiliser, and V133 is this kit fresh demonstration")
    check((SAR_NEW & 0x1F) <= 31, "  the shift immediate stays inside the 5-bit field")
    for a_, (nm, hi) in sorted(ARMS.items()):
        check(code[a_ + 1] == base[a_ + 1] == hi,
              f"  0x{a_+1:05X} ({nm} second byte) untouched -- the instruction stays 2 bytes, so"
              f" NOTHING downstream shifts")
    check(len(ARMS) == 2, "  both arms move together, as V133 moved both together")
    print(f"      {POLARITY_NOTE}")
    print("      arm magnitude x0.5 on BOTH lanes;  V133 took it x2.0 and the car got violent")

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
    for a, w, nm in ((ALPHA2_CAL, 2, "alpha2 -- HELD, this build is arms-only"),
                     (KNEE_CAL, 2, "relay knee"), (K1_CAL, 2, "K1"), (OFF_CAL, 2, "relay offset"),
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
    exempt = set(ARMS)
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the two arms exempted)")

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
    check(payload == 2, f"exactly 2 payload bytes ({payload} found)")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V139 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V139-V122BASE-PUMP.ARMS.SAR11"
    img_out = plain_image_path(f"_v139_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V139_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
