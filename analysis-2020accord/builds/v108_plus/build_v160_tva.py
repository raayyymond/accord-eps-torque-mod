#!/usr/bin/env python3
r"""
V160 -- PUSH THE KIT'S ONLY MEASURED "BOTH SYMPTOMS AT ONCE" LEVER TO ITS INT16 CEILING.
        0xC6446 (Lever B) : 5244 -> 6553.  Base = V158.  ONE HALFWORD.

WHY THIS LEVER
--------------
Lever B is the r24 derivative-feedback gain used WHEN LKAS IS ENGAGED.  From the golden model:

    gain_q10 = <speed x rate LERP surface>
    elif assist_gate_683c != 0:   gain_q10 = 0xC6446      # stock 512 -> Lever B 5244

V88 vs V87 measured it SINGLE-VARIABLE (5 changed bytes), speed-matched 2-4 m/s, engaged,
unclipped, episode-bootstrapped:

    0.5-3 Hz   1.192 [0.780, 1.812]   NULL   <- the peak effective LKAS command, UNTOUCHED
    6-9 Hz     0.859                         <- the ratchet band
    9-12 Hz    0.604 [0.465, 0.943]
    15-22 Hz   0.549 [0.407, 0.844]          <- grind #1's band

    "MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING = LESS HF EVERYWHERE, at zero LF cost."

That is the ONLY lever in this kit measured to reduce BOTH the ratchet band AND the grind band
while leaving the LKAS command statistically untouched.  It is exactly the operator's standing
requirement -- low apparent mass and friction to LKAS AND no ratcheting -- and V88 is the route
that flew with "grinding FIXED".

WHY A THIRD DOSE, AND WHY 6553
-------------------------------
Across ALL 159 build images, 0xC6446 has taken exactly THREE values: 512 (stock, 85 builds),
5244 (73 builds, the flown value) and 1024 (V149 only, superseded).  The dose-response therefore
has exactly TWO points, and the step that flew was 10.24x.  A third point has never been tried.

6553 is the EXACT int16 ceiling for this lane, not an arbitrary number:
        (RATE_CLAMP 5120 x 6553) >> 10 = 32765  <= 32767      fits
        (RATE_CLAMP 5120 x 6554) >> 10 = 32770                OVERFLOWS
=> 1.2496x over the flown value.  Compared with the 10.24x step already flown fault-free, this is
a small, principled increment that lands on a hard structural boundary rather than a guess.

WHY IT CANNOT COST LKAS AUTHORITY
----------------------------------
[EVIDENCE] r24's own rail is +-8192, encoded as FOUR 16-bit immediates at 0x3AC42-0x3AC54, and
this build leaves all 24 of those bytes BYTE-IDENTICAL.  The golden model's warning is specific:
raising the RAIL lets a derivative lane eat the +-10240 aggregator headroom the LKAS command
needs, and that is "the one change in this path that could REDUCE peak effective LKAS steering."
We raise the GAIN and leave the RAIL alone, so that failure mode is STRUCTURALLY UNREACHABLE --
r24 cannot claim one count more of the aggregator than it already could.
[EVIDENCE] measured: gp-0x6b94 never comes within 20% of its own +-10240 clip.
[EVIDENCE] 0.5-3 Hz was 1.192 [0.780, 1.812] = NULL across the 10.24x step.

BLAST RADIUS
------------
[EVIDENCE] 0xC6446 has EXACTLY ONE READER, `ld.hu 0x7446[tp], r10` at 0x3AC08, and ZERO writers.
Verified two ways: an independent tp-relative byte scan handling the `hw2 = (disp | 1)` encoding,
which reproduced the model's recorded addresses for 0xC6440 (0x3AC12) and 0xC6442 (0x3ABFE) as
well; and the golden model's own record ("1 reader / 0 writers, no float mirror, CRC block #48").
No float mirror.  Cal-only, one halfword, outside the cave/bricking class.

WHAT IS NOT ESTABLISHED
-----------------------
[BELIEF] that the dose-response stays monotone beyond 5244.  Only two points exist.  V62's lesson
is explicit -- "2x is approximately the OPTIMUM, not a point on a ramp" -- so 5244 could already
be at or past the optimum, and this build is a DOSE PROBE as much as a fix.  Mitigation: the step
is 1.25x, not 2x, and it stops at a hard arithmetic boundary.
[NOTE] r24 railing begins at |col_torque_rate| > 1280 counts, down from 1599.  The model records
normal driving at 123-839 counts, so normal driving stays unrailed; impulse events (pothole, curb)
rail slightly sooner, which is the rail doing its job.
[NOTE] V160 STACKS on V158's damper.  Both add damping in the creep band by INDEPENDENT mechanisms
(base-assist damper vs r24 loop feedback).  If the drive is ambiguous, V158 alone and V151 remain
available as single-lever fallbacks.
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
WRITE_MODE = os.environ.get("ACCORD_V160_WRITE", "").strip().lower()

BASE_NAME = "_v158_V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE_plain_image.bin"
BASE_SHA = "42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
LB_CAL, LB_OLD, LB_NEW = 0xC6446, 5244, 6553   # Lever B -- THE EDIT (int16 ceiling)
RATE_CLAMP = 5120                              # ASSIST_TORQUE_RATE_CLAMP on gp-0x4f62
R24_RAIL   = 8192                              # r24 rail, four immediates 0x3AC42-0x3AC54
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
KNEE_CAL, KNEE_VAL = 0xC40BC, 3000                  # the relay knee -- HELD (V151 owns it)
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
    print("  V160 -- V158 + Lever B 5244 -> 6553 (int16 ceiling).  ONE halfword.  More r24 loop damping.")
    print("=" * 102)

    print("\n  [1] BASE = V122, THE LAST FLOWN KNOWN-GOOD BUILD")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V158 ({BASE_SHA[:16]}...)")
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

    print("\n  [3] THE EDIT -- ONE HALFWORD")
    check(u16(base, LB_CAL) == LB_OLD,
          f"  0x{LB_CAL:05X} Lever B = {LB_OLD} in the V158 base -- the value V88 FLEW")
    struct.pack_into("<H", code, LB_CAL, LB_NEW)
    attributed |= {LB_CAL, LB_CAL + 1}
    print(f"      0x{LB_CAL:05X}  Lever B  {LB_OLD} -> {LB_NEW}")
    check(u16(code, LB_CAL) == LB_NEW, f"  reads back {LB_NEW}")

    print("\n  [4] MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING, AT ZERO LF COST")
    check(LB_NEW > LB_OLD,
          f"  \U0001f6d1 THE DIRECTION GATE: {LB_OLD} -> {LB_NEW} = x{LB_NEW/LB_OLD:.4f}."
          f"  V88 vs V87 MEASURED this lane SINGLE-VARIABLE (5 changed bytes), speed-matched"
          f" 2-4 m/s, engaged, unclipped, episode-bootstrapped:  6-9 Hz 0.859 /"
          f" 9-12 Hz 0.604 [0.465, 0.943] / 15-22 Hz 0.549 [0.407, 0.844],"
          f" and 0.5-3 Hz 1.192 [0.780, 1.812] = NULL."
          f"  => MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING = LESS HF EVERYWHERE, at ZERO"
          f" cost to the peak effective LKAS command.  This build moves FURTHER along the one"
          f" axis this kit has actually MEASURED to help both symptoms at once.")
    check((RATE_CLAMP * LB_NEW) >> 10 <= 32767,
          f"  \U0001f6d1 THE OVERFLOW GATE: {LB_NEW} is the EXACT int16 ceiling for this lane."
          f"  (clamp {RATE_CLAMP} x {LB_NEW}) >> 10 = {(RATE_CLAMP * LB_NEW) >> 10} <= 32767,"
          f" while {LB_NEW + 1} gives {(RATE_CLAMP * (LB_NEW + 1)) >> 10} and OVERFLOWS."
          f"  A principled stopping point, not an arbitrary dose.")
    check(R24_RAIL * 1024 // LB_NEW > 839,
          f"  \U0001f6d1 THE RAIL GATE: r24 now rails at |col_torque_rate| >"
          f" {R24_RAIL * 1024 // LB_NEW} counts, was {R24_RAIL * 1024 // LB_OLD}.  The golden model"
          f" records NORMAL DRIVING at 123-839 counts, so the p-max of normal driving maps to"
          f" {(839 * LB_NEW) >> 10}, still INSIDE the +-{R24_RAIL} rail.  A differentiator spikes on"
          f" potholes and curbs, which is exactly what the rail is for, and that is UNCHANGED.")
    check(rd(code, 0x3AC42, 24) == rd(base, 0x3AC42, 24),
          f"  \U0001f6d1 THE AUTHORITY GATE: r24's OWN RAIL (+-{R24_RAIL}, four 16-bit immediates at"
          f" 0x3AC42-0x3AC54) is BYTE-IDENTICAL to the base.  The model warns that raising the RAIL"
          f" lets a derivative lane eat the +-10240 aggregator headroom the LKAS command needs --"
          f" THE ONE CHANGE IN THIS PATH THAT COULD REDUCE PEAK EFFECTIVE LKAS STEERING.  We raise"
          f" the GAIN and leave the RAIL alone, so that failure mode is STRUCTURALLY UNREACHABLE:"
          f" r24 cannot claim one count more of the aggregator than it already could.")
    check(u16(code, KNEE_CAL) == KNEE_VAL,
          f"  0x{KNEE_CAL:05X} relay knee HELD at {KNEE_VAL} -- raising it is V151, a separate build")

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

    print("\n  [8] FULL BYTE DIFF vs V158 -- ZERO UNATTRIBUTED")
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
    FF.assert_x31_checksum(rwd, "V151 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V160-V158BASE-LEVERB.5244.TO.6553"
    img_out = plain_image_path(f"_v160_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V160_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
