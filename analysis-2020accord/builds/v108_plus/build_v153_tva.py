#!/usr/bin/env python3
r"""
V152 -- QUARTER THE OBSERVER CORNER ON BOTH ARMS, PRESERVING HONDA'S EXACT MATCH.
        0xC40D0 : 408 -> 104   AND   0xC63AC : 102 -> 26.  The LARGER dose of V152.   Base = V122.

THE STRUCTURE THIS COMES FROM
-----------------------------
FUN_0003b8f6 computes a BILINEAR term -- NOT Coulomb friction (see the 2026-08-28 correction):
        iVar20 = polarity * gp-0x6abc * 12                 an ANGLE
        fVar13 = clamp(iVar20 / cal(0xC40BC), -1.0, +1.0)  the knee normalises the ANGLE
        term   = (|model|*K1/1024 + OFFSET/1024) * fVar13  |model| x sat(angle)
        then an EMA with alpha = cal(0xC40D0)/4096, in the 1 kHz task.
That EMA is WIDE OPEN at the ratchet frequency:
        cal 408 -> alpha 0.099609  fc 16.70 Hz  |H(7.8 Hz)| = 0.906   <- 91% TRANSMITTED
        cal 204 -> alpha 0.049805  fc  8.13 Hz  |H(7.8 Hz)| = 0.720   <- THIS BUILD, 1.26x less
An EMA has DC GAIN EXACTLY 1 at any alpha, so this attenuates ONLY the fast component and leaves
steady-state friction UNTOUCHED => unlike V151 it costs NO assist.

WHY BOTH CELLS MOVE TOGETHER -- THIS IS THE WHOLE POINT OF THE BUILD
--------------------------------------------------------------------
BUILD-LINEAGE warns that 0xC63AC's alpha "matches 0xC40D0 to the last bit -- a genuine
disturbance-observer constraint, not hygiene."  CONFIRMED ARITHMETICALLY:
        alpha(0xC63AC) = 102/1024 = 0.099609375        (>>10  in FUN_00038148)
        alpha(0xC40D0) = 408/4096 = 0.099609375        (/4096 in FUN_0003b8f6)
        408 = 4 x 102 EXACTLY  =>  the match is BY CONSTRUCTION
V98's comparator established  iVar6 = gp-0x6bfe (MODEL) + gp-0x6bfa (REQUEST) - (gp-0x374c>>4)
(ACTUAL), where 0xC40D0 shapes the MODEL arm and 0xC63AC shapes the ACTUAL arm.  Honda gives both
arms the SAME time constant so their phases CANCEL in the difference.
=> moving ONE alone injects a relative phase error into the residual at 7.8 Hz, and its SIGN is
   UNRESOLVED.  That is why this build moves BOTH and keeps 204 = 4 x 51 exactly.
=> the match is NEVER broken.  Only the SHARED corner moves.

WHY THAT IS GATE-2 DEFENSIBLE
-----------------------------
With both arms moved identically, no RELATIVE phase is introduced anywhere; the residual simply
sees one extra pole at 8.13 Hz instead of 16.70 Hz.  That is a PURE ADDED LOW-PASS on the observer
=> it REDUCES high-frequency loop gain, which is the stabilising direction for a lightly-damped
resonance (Q 14-29) being excited through this loop.
And it is the direction the kit's OWN Bode sum favours: 0xC63AC was filed "Predicted WORSE" for
being RAISED (cal 205: the stage's 1.38x HF gain beat its phase credit, |L| = 0.875*1.38 = 1.208).
Lowering it moves HF gain DOWN, so |L| falls BELOW 0.875 -- inside the edge, not past it.

THE COSTS, STATED
-----------------
The observer tracks real friction changes more sluggishly (corner 16.7 -> 8.1 Hz).  DC is exactly
unchanged on BOTH arms, so steady-state assist and steady-state friction are untouched.
[BELIEF] that 1.26x less transmission at 7.8 Hz is enough to matter by ear.  It is one halving; the
ladder can go further (51->26 with 204->104) if this reads as directionally right.
[UNKNOWN] 0xC63AC = 102 is HONDA STOCK and V99 restored it deliberately after V97 flew it at 150
and came back UNINTERPRETABLE.  Moving it below stock is new territory for that cell.

BASE = V122.  knee 3000 (raising it is V151), K1 1020, alpha2 8, gain 6x, b26 clamp 511, both
Lever A arms stock, deadband Honda 3, Lever B HELD at 5244 (changing it is V149).
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
WRITE_MODE = os.environ.get("ACCORD_V153_WRITE", "").strip().lower()

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
KNEE_CAL, KNEE_VAL = 0xC40BC, 3000
K1_CAL, K1_VAL = 0xC40D2, 1020
OFF_CAL, OFF_VAL = 0xC4080, 0
POLE_CAL, POLE_OLD, POLE_NEW = 0xC40D0, 408, 104   # MODEL-arm EMA  (alpha = cal/4096)
OBS_CAL,  OBS_OLD,  OBS_NEW  = 0xC63AC, 102,  26   # ACTUAL-arm IIR (alpha = cal/1024)
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
    check(u16(base, OFF_CAL) == OFF_VAL and u16(base, POLE_CAL) == POLE_OLD,
          "  relay offset 0 and friction EMA pole 408, both V122")
    check(u16(base, RESID_CAL) == RESID_VAL, f"  0x{RESID_CAL:05X} residual scale = {RESID_VAL}")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(base, a) if want < 0 else (base[a] if w == 1 else u16(base, a))
        check(got == want, f"  0x{a:05X} = {want} in the base -- {why.split('.')[0]}")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(abs(_fb - CEIL_F_VAL) < 1e-9 and abs(_fb * 1024 - (511 + 1)) < 1e-6,
          f"  0x{CEIL_F:05X} float twin = {CEIL_F_VAL} and float*1024 == int+1 ({_fb*1024:.0f})")

    print("\n  [3] THE EDIT -- TWO CALS, MOVED TOGETHER")
    check(u16(base, POLE_CAL) == POLE_OLD,
          f"  0x{POLE_CAL:05X} MODEL-arm EMA = {POLE_OLD} in the V122 base")
    check(u16(base, OBS_CAL) == OBS_OLD,
          f"  0x{OBS_CAL:05X} ACTUAL-arm IIR = {OBS_OLD} in the V122 base (Honda stock)")
    check(POLE_OLD == 4 * OBS_OLD,
          f"  \U0001f6d1 HONDA'S MATCH, VERIFIED IN THE BASE: {POLE_OLD} = 4 x {OBS_OLD} exactly"
          f" => alpha {POLE_OLD}/4096 = {OBS_OLD}/1024 = {POLE_OLD/4096:.9f} on BOTH arms")
    struct.pack_into("<H", code, POLE_CAL, POLE_NEW)
    struct.pack_into("<H", code, OBS_CAL, OBS_NEW)
    attributed |= {POLE_CAL, POLE_CAL + 1, OBS_CAL, OBS_CAL + 1}
    print(f"      0x{POLE_CAL:05X}  MODEL-arm EMA   {POLE_OLD} -> {POLE_NEW}")
    print(f"      0x{OBS_CAL:05X}  ACTUAL-arm IIR  {OBS_OLD} -> {OBS_NEW}")
    check(u16(code, POLE_CAL) == POLE_NEW and u16(code, OBS_CAL) == OBS_NEW, "  both read back")

    print("\n  [4] THE MATCH IS PRESERVED, AND THE SHARED CORNER FALLS")
    check(POLE_NEW == 4 * OBS_NEW,
          f"  \U0001f6d1 THE MATCH GATE: {POLE_NEW} = 4 x {OBS_NEW} exactly => alpha is STILL"
          f" IDENTICAL on both arms ({POLE_NEW/4096:.9f}).  NO RELATIVE PHASE is introduced"
          f" anywhere in the observer residual -- that is the entire point of this build, and it"
          f" is what a single-cell move could not do.")
    a_old, a_new = POLE_OLD / 4096, POLE_NEW / 4096
    fc = lambda al: -math.log(1 - al) * 1000.0 / (2 * math.pi)
    def hmag(al, f=7.8):
        w = 2 * math.pi * f / 1000.0
        re, im = 1 - (1 - al) * math.cos(w), (1 - al) * math.sin(w)
        return al / math.hypot(re, im)
    check(a_new < a_old,
          f"  \U0001f6d1 THE DIRECTION GATE: shared corner {fc(a_old):.2f} -> {fc(a_new):.2f} Hz;"
          f" |H(7.8 Hz)| {hmag(a_old):.3f} -> {hmag(a_new):.3f} = {hmag(a_old)/hmag(a_new):.2f}x"
          f" LESS transmission at the ratchet frequency.  A PURE ADDED LOW-PASS on the observer =>"
          f" HF loop gain DOWN, the stabilising direction for a Q 14-29 resonance.")
    check(abs(hmag(a_old, 0.0) - 1.0) < 1e-9 and abs(hmag(a_new, 0.0) - 1.0) < 1e-9,
          f"  \U0001f6d1 THE NO-COST GATE: DC gain is EXACTLY 1.000000000 at both alphas =>"
          f" steady-state friction and steady-state assist are UNCHANGED.  This costs no authority,"
          f" unlike V151 which scales the term at DC too.")
    check(u16(code, LB_CAL) == LB_HELD and u16(code, KNEE_CAL) == KNEE_VAL,
          f"  Lever B HELD at {LB_HELD} (that is V149) and the knee HELD at {KNEE_VAL}"
          f" (raising it is V151) -- single-lever builds, do not stack before either has flown")

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
                     (RESID_CAL, 2, "residual scale"),
                     (LB_CAL, 2, "Lever B -- HELD, that is V149"),
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
    exempt = {POLE_CAL, POLE_CAL + 1, OBS_CAL, OBS_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (both observer poles exempted)")

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
    check(payload == 3, f"exactly 3 payload bytes ({payload} found) -- 2 for the 0xC40D0 u16, 1 for 0xC63AC whose high byte is already 0")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V153 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V153-V122BASE-OBSCORNER.QUARTERED.MATCHED"
    img_out = plain_image_path(f"_v153_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V153_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
