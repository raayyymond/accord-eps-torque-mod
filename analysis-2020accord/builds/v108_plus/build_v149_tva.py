#!/usr/bin/env python3
r"""
V149 -- REMOVE THE 5.12x MID-DRIVE STEP IN THE r24 PUMP.  0xC6446 5244 -> 1024.  Base = V122.

THE MECHANISM, READ FROM THE DECOMPILE
----------------------------------------
The r24 multiplier is selected by gp-0x671d, read at 0x3AB98 (ld.bu -0x671d, gp, r6 / cmp r0, r6):
        gp-0x671d == 0  ->  cal(0xC6446) = 5244      (V122; STOCK is 512)
        gp-0x671d != 0  ->  cal(0xC6442) = 1024
And gp-0x671d is NOT a mode flag.  FUN_00041d56 shows it is a FAULT COUNTER:
        bVar12 = |x| >= cal(0xC61FA)=5530 , with cal(0xC61F8)=1024 as the hysteresis low
        bVar17 = gp-0x671d + (rising edge of bVar12)          // INCREMENTS, never decrements
        if (overflow) bVar17 = 0xff                            // saturates at 255
        FUN_00016de6(0x5e, 1, cal(0xC6500)=771 <= bVar17, 1)   // DTC 0x5E at 771 counts
        gp-0x671d = bVar17                                     // lockstep-shadowed at gp-0x4c24
It is zeroed only at 0x3BD2A (st.b r0, -0x671d, gp), a clear/init path.

=> gp-0x671d starts a drive at ZERO and only ever increments.
=> the MULTIPLIER switches on the FIRST increment -- nowhere near the DTC limit of 771.
=> ONE threshold crossing permanently drops the r24 multiplier 5244 -> 1024, a 5.12x cut, for the
   REST OF THE DRIVE.

WHY THAT MATTERS, AND WHAT V88 DID
------------------------------------
r24 is a CONFIRMED PUMP: gp-0x6752 = -1, verified three ways including on-car.
        STOCK:  512 -> 1024   the lane DOUBLES on fault
        V122:  5244 -> 1024   the lane is CUT 5.12x on fault
V88 set 0xC6446 from 512 to 5244, which (a) raised the pre-fault r24 pump to 10.2x STOCK and
(b) INVERTED the fault response from a 2x increase into a 5.12x cut.  Neither was documented.
=> the car currently runs a confirmed pump at 10.2x stock until the first threshold crossing, then
   steps down 5.12x mid-drive and stays down.
=> a 5.12x STEP CHANGE in a pump, part-way through a drive, is exactly the mechanism that makes a
   grind come and go unpredictably -- and it would make two routes on the SAME build differ by
   whenever the crossing happened.  That is a candidate explanation for the 20-36x between-route
   noise floor measured on this kit's own endpoint.

THE EDIT
--------
        0xC6446 : 5244 -> 1024   == cal(0xC6442)
=> the multiplier becomes 1024 REGARDLESS of the fault counter.  The step vanishes and the lane
   behaves identically before and after the crossing.
=> and it REDUCES a confirmed pump by 5.12x in the pre-fault regime, which cannot destabilise a
   stable loop whatever its phase.  SAFE BY CONSTRUCTION.

WHAT THIS IS NOT
----------------
[BELIEF] that the step is what the operator hears.  The mechanism is EVIDENCE; that it causes his
grind is not.
=> and it partially REVERTS V88, which the operator reported as a grinding fix.  The accompanying
   numbers are uninformative (0.549 = 1.8x, far below the measured 20-36x floor), but his REPORT is
   not.  If grinding gets WORSE, V88 high pre-fault value was doing something and the answer is a
   value BETWEEN 1024 and 5244 -- not a return to 5244, which restores the step.
NOT TOUCHED: 0xC61FA / 0xC61F8 (the counter thresholds) or 0xC6500 (the DTC limit).  Raising those
would keep Lever B in force longer but would also suppress DTC 0x5E, which is a fault function.

BASE = V122.  alpha2 8, gain 6x, b26 clamp 511, both Lever A arms stock, deadband at Honda 3.
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
WRITE_MODE = os.environ.get("ACCORD_V149_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
LB_CAL, LB_OLD, LB_NEW = 0xC6446, 5244, 1024   # Lever B -> match the post-fault value
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
    check(u16(base, ALPHA2_CAL) == ALPHA2_HELD,
          f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_HELD} -- HELD; Lever-B-only build")
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

    print("\n  [3] THE EDIT -- ONE CAL")
    check(u16(base, LB_CAL) == LB_OLD,
          f"  0x{LB_CAL:05X} Lever B = {LB_OLD} in the base (V88 raised it from the stock {LB_STOCK})")
    check(u16(base, LB_POST) == LB_NEW,
          f"  0x{LB_POST:05X} = {LB_NEW} -- the count>0 multiplier, and the value we match")
    struct.pack_into("<H", code, LB_CAL, LB_NEW)
    attributed |= {LB_CAL, LB_CAL + 1}
    print(f"      0x{LB_CAL:05X}  Lever B  {LB_OLD} -> {LB_NEW}")
    check(u16(code, LB_CAL) == LB_NEW, f"  reads back {LB_NEW}")

    print("\n  [4] THE STEP IS REMOVED, AND THE PUMP IS REDUCED")
    check(u16(code, LB_CAL) == u16(code, LB_POST),
          f"  \U0001f6d1 THE NO-STEP GATE: the count==0 and count>0 multipliers are now BOTH"
          f" {LB_NEW} => the 5.12x mid-drive step VANISHES and the lane behaves identically before"
          f" and after the fault-counter crossing")
    check(LB_NEW < LB_OLD,
          f"  \U0001f6d1 THE DIRECTION GATE: {LB_OLD} -> {LB_NEW} REDUCES a CONFIRMED PUMP"
          f" (gp-0x6752 = -1, verified 3 ways incl. on-car) by {LB_OLD/LB_NEW:.2f}x in the"
          f" pre-fault regime -- reducing a feedback magnitude cannot destabilise a stable loop")
    check(u16(base, CNT_HI) == 5530 and u16(base, CNT_LO) == 1024 and u16(base, DTC_LIM) == 771,
          f"  the counter thresholds 0x{CNT_HI:05X}=5530 / 0x{CNT_LO:05X}=1024 and the DTC 0x5E"
          f" limit 0x{DTC_LIM:05X}=771 are as expected")
    check(u16(code, CNT_HI) == u16(base, CNT_HI) and u16(code, CNT_LO) == u16(base, CNT_LO)
          and u16(code, DTC_LIM) == u16(base, DTC_LIM),
          "  \U0001f6d1 and NONE of them is touched -- raising them would keep Lever B in force"
          " longer but would also suppress DTC 0x5E, which is a fault function")
    print(f"      stock behaviour: {LB_STOCK} -> {LB_NEW}  (lane DOUBLES on fault)")
    print(f"      V122  behaviour: {LB_OLD} -> {LB_NEW}  (lane CUT {LB_OLD/LB_NEW:.2f}x on fault)")
    print(f"      this build:      {LB_NEW} -> {LB_NEW}  (NO STEP)")

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
    exempt = {LB_CAL, LB_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (Lever B exempted)")

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
    check(payload == 2, f"exactly 2 payload bytes ({payload} found) -- the Lever B u16")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V149 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V149-V122BASE-LEVERB.5244.TO.1024"
    img_out = plain_image_path(f"_v149_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V149_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
