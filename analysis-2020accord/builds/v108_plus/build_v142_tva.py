#!/usr/bin/env python3
r"""
V142 -- THE AUTHORITY BUILD.  0xC6CD0 6x -> 8x with its matched clamps.  Base = V141.

*** DO NOT FLY THIS UNTIL V141 HAS CONFIRMED THE GRIND FIX ON-CAR. ***
The builder ENFORCES the precondition it can check -- that the base carries V141's deadband -- but
it CANNOT check that the operator reported the grinding fixed.  That judgement is his.

WHY THIS BUILD EXISTS, AND WHY IT IS SECOND
---------------------------------------------
Measuring the operator's other two targets on r24 (V122) produced two results:

1. "PEAK COMMAND OSCILLATION" IS NOT IN THE COMMAND.  Spectral split of sc_tq, engaged:
        0.5-3 Hz   3-8 Hz   8-15 Hz  15-22 Hz
   PEAK   90.84%    0.93%     0.07%     0.13%
   LOW    82.59%    5.10%     1.38%     0.71%
   At peak the command is CLEANER, not dirtier.  The felt oscillation is generated DOWNSTREAM in
   the EPS => it is the SAME problem as the grinding, and needs no separate lever.

2. AUTHORITY IS CAPPED ON OPENPILOT'S SIDE.  It sits at its own +-4096 request limit on 2-4 % of
   engaged frames on EVERY build (V91 2.58 %, V111 3.24 %, V112 3.79 %, V122 2.70 %), and that duty
   does NOT fall as EPS gain rises across 4x -> 6x.  openpilot-side edits are forbidden by standing
   instruction, so THE ONLY AUTHORITY LEVER IS THE EPS GAIN 0xC6CD0.

=> authority and grinding are in tension through ONE cell, and the operator's own instruction fixes
   the order: "just go to 8x IF you decide to increase LKAS gain" AND "If youre going to increase
   gain make sure we dont get even more oscillation and grinding."  The rise is CONDITIONAL.

THE EDIT -- THREE CELLS, ONE LOGICAL LEVER
--------------------------------------------
    0xC6CD0   LKAS gain        5346 -> 7128     6x -> 8x, +33 % authority
    0xC61B2   forward clamp A  3072 -> 4096     must scale WITH the gain
    0xC61B4   forward clamp B  3072 -> 4096
The clamps are not a separate decision: the kit's record is explicit that they track the gain
(4x -> 2048, 6x -> 3072, 8x -> 4096), and leaving them at 3072 under an 8x gain throws away 25 % of
the rise.  The builder asserts clamp/gain ratio == 1.000 exactly.

WHAT V133 DOES AND DOES NOT SAY ABOUT 8x
------------------------------------------
V133 flew 8x and the operator reported "massive, violent grinding after enabling LKAS which
continues after disengaging".  But V133 moved SIX cells against the last flown build, including
BOTH Lever A arms (x2 on a confirmed pump, not LKAS-gated) and the b26 clamp.  The gain is
ENGAGED-ONLY and cannot produce a symptom that persists after disengaging, so it is an AMPLIFIER
suspect, not the cause.  [BELIEF] that 8x is acceptable once the grinding is fixed.  This build is
how that belief gets tested -- ONE lever, on a base whose grind behaviour is known.

IF THE GRINDING RETURNS AT 8x
-------------------------------
That means the grind fix was INSUFFICIENT, not that the gain is at fault: 8x only scales
EXCITATION into a loop whose stability V141 was supposed to have restored.  The response is to
revert to V141 and take the next grind rung (deadband 96 -> 192), NOT to abandon 8x.
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
WRITE_MODE = os.environ.get("ACCORD_V142_WRITE", "").strip().lower()

BASE_NAME = "_v141_V141-V122BASE-DEADBAND.96-427.6ADA_plain_image.bin"
BASE_SHA = "66e488549f17d7092ceb7c1b846475dbefd2e0da205b65e54b786b9a48573098"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
DB_CAL, DB_HELD = 0xC61F6, 96                # V141 deadband -- REQUIRED in the base
GAIN_CAL, GAIN_OLD, GAIN_NEW = 0xC6CD0, 5346, 7128       # 6x -> 8x
CLAMPS, CLAMP_OLD, CLAMP_NEW = (0xC61B2, 0xC61B4), 3072, 4096
GAIN_BASE = 891                              # 0xC646C, stock on every build ever made
LANE_CLAMP, AGG_CLAMP = 0x2000, 0x2800       # +-8192 lane, +-10240 aggregator
ARMS_STOCK = {0x3AB76: 0xAA, 0x3AC20: 0xAA}  # Lever A arms -- HELD stock
TAP_ADDR = 0x55DF2                           # the 427 tap displacement
TAP_OLD = (-0x6ABC) & 0xFFFF                 # V141 taps gp-0x6ABC
TAP_NEW = (-0x6ADA) & 0xFFFF                 # -> the r24 PUMP-LANE MIRROR
SAR_ADDR, SAR_HELD = 0x55E10, 0xA3           # sar 3, already in V141; NOT touched
LANE_MIRRORS = {0x6ADA: 'r24 lane (probed)', 0x6ADC: 'r26 lane'}
ALPHA2_STOCK = 22
ALPHA2_STEPS = ((22, 14, "V91  -> V111"), (14, 8, "V112 -> V141"))   # flown, fault-free

# ---- THE FIVE CELLS V133 MOVED THAT THIS BUILD DELIBERATELY LEAVES AT V141 -------------------
REVERTED = {
    0xC407E: (2, 511, "b26 clamp = APPARENT MASS ceiling.  V133 doubled it to 1023 and the car"
                      " got VIOLENTLY worse, persisting after disengage because it is NOT"
                      " mode-gated."),
    0x3AB76: (1, 0xAA, "Lever A r26 arm -- left STOCK.  Its partner caused grind #2."),
    0x3AC20: (1, 0xAA, "Lever A r24 arm -- left STOCK.  RECORDED as having CAUSED grind #2,"
                       " which the operator reported on V133 while DISENGAGED."),
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
    print("  V142 -- THE AUTHORITY BUILD: 0xC6CD0 6x -> 8x with matched clamps.  Base = V141.")
    print("=" * 102)

    print("\n  [1] BASE = V141, THE LAST FLOWN KNOWN-GOOD BUILD")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V141 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE CARRIES V141's VALUES, INCLUDING EVERY CELL V133 MOVED")
    check(u16(base, ALPHA2_CAL) == ALPHA2_HELD,
          f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_HELD} -- HELD; deadband-only build")
    for _a, _v in sorted(ARMS_STOCK.items()):
        check(base[_a] == _v,
              f"  0x{_a:05X} Lever A arm = 0x{_v:02X} STOCK -- V133 doubled these and the car got violent")
    check(u16(base, KNEE_CAL) == KNEE_VAL and u16(base, K1_CAL) == K1_VAL,
          f"  relay knee {KNEE_VAL} / K1 {K1_VAL} -- V141's tuned pair")
    check(u16(base, OFF_CAL) == OFF_VAL and u16(base, POLE_CAL) == POLE_VAL,
          "  relay offset 0 and friction EMA pole 408, both V141")
    check(u16(base, RESID_CAL) == RESID_VAL, f"  0x{RESID_CAL:05X} residual scale = {RESID_VAL}")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(base, a) if want < 0 else (base[a] if w == 1 else u16(base, a))
        check(got == want, f"  0x{a:05X} = {want} in the base -- {why.split('.')[0]}")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(abs(_fb - CEIL_F_VAL) < 1e-9 and abs(_fb * 1024 - (511 + 1)) < 1e-6,
          f"  0x{CEIL_F:05X} float twin = {CEIL_F_VAL} and float*1024 == int+1 ({_fb*1024:.0f})")

    print("\n  [3] THE PRECONDITION -- THE BASE MUST CARRY THE GRIND FIX")
    check(u16(base, DB_CAL) == DB_HELD,
          f"  \U0001f6d1 THE PRECONDITION GATE: 0x{DB_CAL:05X} = {DB_HELD} in the base, i.e. this"
          f" is built on V141 WITH the pump deadband.  Raising the gain on a base that still"
          f" grinds cannot satisfy the operator whatever it measures.")
    print("      \U0001f6d1 the builder CANNOT check that the operator reported the grinding")
    print("         FIXED on V141.  That judgement is his, and it is the real precondition.")

    print("\n  [4] THE EDIT -- THREE CELLS, ONE LOGICAL LEVER")
    check(u16(base, GAIN_CAL) == GAIN_OLD,
          f"  0x{GAIN_CAL:05X} LKAS gain = {GAIN_OLD} ({GAIN_OLD/GAIN_BASE:.0f}x) in the base")
    for _c in CLAMPS:
        check(u16(base, _c) == CLAMP_OLD, f"  0x{_c:05X} forward clamp = {CLAMP_OLD} in the base")
    struct.pack_into("<H", code, GAIN_CAL, GAIN_NEW)
    attributed |= {GAIN_CAL, GAIN_CAL + 1}
    for _c in CLAMPS:
        struct.pack_into("<H", code, _c, CLAMP_NEW)
        attributed |= {_c, _c + 1}
    print(f"      0x{GAIN_CAL:05X}  LKAS gain  {GAIN_OLD} -> {GAIN_NEW}"
          f"   ({GAIN_OLD/GAIN_BASE:.0f}x -> {GAIN_NEW/GAIN_BASE:.0f}x,"
          f" +{100*(GAIN_NEW/GAIN_OLD-1):.0f} % authority)")
    for _c in CLAMPS:
        print(f"      0x{_c:05X}  clamp      {CLAMP_OLD} -> {CLAMP_NEW}")
    check(u16(code, GAIN_CAL) == GAIN_NEW, f"  gain reads back {GAIN_NEW}")
    check(all(u16(code, _c) == CLAMP_NEW for _c in CLAMPS), f"  clamps read back {CLAMP_NEW}")
    check(abs(CLAMP_NEW / (GAIN_NEW / GAIN_BASE) / 512 - 1.0) < 1e-9,
          "  \U0001f6d1 THE MATCHED-CLAMP GATE: clamp/gain ratio is EXACTLY 1.000, so the forward"
          " path can carry the whole rise.  Leaving the clamps at 3072 under an 8x gain would"
          " throw away 25 % of it -- a silent, measurable loss the kit has made before.")
    check(CLAMP_OLD / (GAIN_OLD / GAIN_BASE) / 512 == 1.0,
          "  and the base was matched too, so this build preserves the invariant rather than"
          " restoring it")

    print("\n  [5] \U0001f6d1 EVERY CELL IMPLICATED IN V133's REGRESSION IS AT ITS V141 VALUE")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(code, a) if want < 0 else (code[a] if w == 1 else u16(code, a))
        check(got == want and rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} = {want}  -- {why}")
    check(struct.unpack_from("<f", code, CEIL_F)[0] == CEIL_F_VAL,
          f"  0x{CEIL_F:05X} float twin stays {CEIL_F_VAL}, matched to the 511 int")
    check(u16(code, GAIN_CAL) == GAIN_NEW,
          "  \U0001f6d1 THE GAIN IS THE EDIT HERE -- 8x, deliberately, and ONLY because the base"
          " carries the grind fix.  The operator's condition was 8x if we do not get more"
          " grinding; this build is how that gets tested, one lever at a time.")

    print("\n  [6] NOTHING ELSE MOVED")
    for a, w, nm in ((ALPHA2_CAL, 2, "alpha2 -- HELD, this build is deadband-only"),
                     (KNEE_CAL, 2, "relay knee"), (K1_CAL, 2, "K1"), (OFF_CAL, 2, "relay offset"),
                     (POLE_CAL, 2, "friction EMA pole"), (RESID_CAL, 2, "residual scale"),
                     (ARM_CAL, 2, "detector arm threshold"), (0xC40DA, 2, "the >>7 EMA twin")):
        check(rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} {nm} byte-identical to V141")
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
    exempt = {GAIN_CAL, GAIN_CAL + 1} | {c + i for c in CLAMPS for i in (0, 1)}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V141 base (gain + clamps exempted)")

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

    print("\n  [8] FULL BYTE DIFF vs V141 -- ZERO UNATTRIBUTED")
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
    check(payload == 4, f"exactly 4 payload bytes ({payload} found) -- gain (2) + 2 clamp high bytes")
    check(u16(code, DB_CAL) == DB_HELD and u16(code, TAP_ADDR) == u16(base, TAP_ADDR),
          "  \U0001f6d1 the V141 grind fix and its probe are CARRIED UNCHANGED -- this build adds"
          " only the gain and its matched clamps, so a result IS attributable to the gain")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V142 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V142-V141BASE-GAIN8X-CLAMPS4096"
    img_out = plain_image_path(f"_v142_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V142_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
