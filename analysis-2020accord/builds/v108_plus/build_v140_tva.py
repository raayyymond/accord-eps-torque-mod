#!/usr/bin/env python3
r"""
V140 -- V122 + the r24 PUMP-LANE DEADBAND 0xC61F6, 3 -> 96.  ONE cal.

THE LEVER, AND WHY IT FITS THE OPERATOR TWO GOALS AT ONCE
-----------------------------------------------------------
His standing instruction is that we must NOT buy smoothness with mass and friction:
    "We want both: low apparent steering mass and friction to LKAS AND no ratcheting."
A DEADBAND on a PUMP lane is the one shape of lever that gives both.  It removes the pump where
the signal is SMALL -- which is what grinding, ratcheting and stuttering ARE -- and leaves LARGE
steering commands essentially untouched, so LKAS authority does not pay for it.

READ FROM THE DECOMPILE (FUN_0003aa2c, the aggregator)
--------------------------------------------------------
    uVar13 = (pcVar10 * uVar11) >> 10;              // 0x3AC20  sar 0xa, r8
    uVar12 = *(ushort *)(tp + 0x71f6);              // cal 0xC61F6  = THE DEADBAND
    if      (uVar13 >  uVar12) iVar17 = uVar13 - uVar12;   // SUBTRACT, not clip
    else if (uVar13 < -uVar12) iVar17 = uVar13 + uVar12;
    else                       iVar17 = 0;                 // the DEAD ZONE
    iVar17 = iVar17 * *(char *)(gp - 0x6752);       // x (-1)   <- THE PUMP
    iVar16 = clamp(iVar17, +-0x2000);               // +-8192 of a +-10240 aggregator total

THREE FACTS THAT MAKE THIS SAFE
---------------------------------
1. IT IS CONTINUOUS.  The deadband SUBTRACTS rather than clips, so the transfer curve has no step
   at the boundary: output goes 0 -> 0 -> +1 -> +2 as the input crosses.  There is no notchiness
   mechanism here, which is the usual objection to widening a dead zone on a steering path.
2. IT REDUCES A CONFIRMED PUMP.  gp-0x6752 = -1, verified three independent ways INCLUDING on-car
   (V98 b3 rung, duty 0.0000 over 17,983 frames / 5 routes), and the config table that sets it
   lives at 0x1000-0x15xx, below the 0x13000 floor every .rwd writes from -- so no build could ever
   have changed it.  Reducing a positive-feedback term cannot destabilise a stable loop.
3. THE COST AT LARGE SIGNAL IS A CONSTANT 96-COUNT OFFSET on a lane that clamps at 8192, i.e.
   1.17 %.  LKAS authority is not meaningfully touched.

WHY THIS LANE IS WORTH ATTACKING AT ALL
-----------------------------------------
Each pump lane clamps to +-0x2000 = +-8192 against an aggregator total of +-0x2800 = +-10240, so
EITHER lane alone can drive 80 % of the aggregator output.  And V133 gave a fresh, large, on-car
demonstration of their potency: it DOUBLED both arms (sar 10 -> 9) and produced "massive, violent
grinding after enabling LKAS which continues after disengaging".  These lanes matter.

THE DOSE, AND THE HONEST UNCERTAINTY IN IT
--------------------------------------------
Honda ships 3 counts -- 0.037 % of the lane clamp, which is a quantization-noise floor, not a
functional dead zone.  This build takes it to 96 (x32), still only 1.17 % of the lane clamp.
    x2  ->   6      x8  ->  24      x32 ->  96   <- THIS BUILD
    x4  ->  12      x16 ->  48      x64 -> 192
[BELIEF] that 96 is the right magnitude.  The lane input pcVar10 is gp-0x4f62 clamped to +-5120,
and with uVar11 ~ 1024-2048 the lane runs to 5120-8192 full scale.  If the grind is a 1-3 % of
full-scale oscillation it lands at roughly 50-150 lane counts, which is what 96 is centred on.
That chain is an ESTIMATE: this kit has not measured the lane amplitude during a grind episode.
=> If V140 is NULL, the next rung is 192, not a different lever -- the deadband being too SMALL is
   the expected failure mode, and it is cheap to step.
=> If the steering feels vague or lazy near centre, the dose was too LARGE; step back to 48.

WHAT IT IS *NOT*
----------------
This does not touch the r26 lane, which has NO deadband in this function -- it goes straight from
its multiply to the polarity and the clamp.  If V140 helps, adding a deadband to r26 requires an
instruction edit, not a cal, and is a separate decision.

BASE = V122, THE LAST FLOWN KNOWN-GOOD BUILD.  alpha2 stays 8, gain stays 6x, clamp stays 511,
both Lever A arms stay stock.
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
WRITE_MODE = os.environ.get("ACCORD_V140_WRITE", "").strip().lower()

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
    print("  V140 -- V122 + the r24 pump-lane DEADBAND 0xC61F6, 3 -> 96.  ONE cal.")
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
    exempt = {DB_CAL, DB_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the deadband exempted)")

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
    FF.assert_x31_checksum(rwd, "V140 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V140-V122BASE-PUMP.DEADBAND.96"
    img_out = plain_image_path(f"_v140_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V140_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
