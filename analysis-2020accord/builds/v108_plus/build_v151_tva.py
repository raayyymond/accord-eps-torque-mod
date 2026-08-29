#!/usr/bin/env python3
r"""
V151 -- RAISE THE COULOMB RELAY KNEE.  0xC40BC : 3000 -> 3600, K1 HELD.  Base = V122.
        V135's edit, REBASED off the regressed V133 base onto the last FLOWN image.

WHY THIS BUILD EXISTS
---------------------
V135 made this exact edit and is SUPERSEDED -- not because the edit was wrong, but because it sat
on a V133 base, and V133 regressed hard on-car (violent grinding after enabling LKAS).  Every
V122-based build since (V137..V150) holds the knee at 3000.
=> the raise to 3600 has NEVER been built on a flyable base.  This is that build.

THE MECHANISM -- IT REMOVES A RELAY, WHICH IS THE STICK-SLIP GENERATOR
----------------------------------------------------------------------
CORRECTED 2026-08-28 FROM THE DECOMPILE.  The kit long described this as
"friction = K1*min(|model|,knee)/knee".  THAT IS WRONG.  FUN_0003b8f6 actually computes:
        iVar20 = polarity * gp-0x6abc * 12                 <- an ANGLE, not the model
        fVar13 = clamp(iVar20 / knee, -1.0, +1.0)          <- the KNEE normalises the ANGLE
        fVar14 = |fVar18|                                  <- |model|
        term   = (fVar14*K1/1024 + OFFSET/1024) * fVar13   <- BILINEAR: |model| x sat(angle)
        then an EMA with pole cal(0xC40D0), then clamped to +-10.0
gp-0x6abc is an ANGLE, proven by its own first difference downstream:
        (iVar20 - prev) * 0.5 * 17.453293      and 17.453293 = 1000*pi/180 = deg->rad at 1 kHz.
=> THE KNEE SCALES STEERING ANGLE.  K1 SCALES |model|.  They are INDEPENDENT AXES, not a ratio.
=> this is NOT Coulomb friction: Coulomb friction switches on VELOCITY SIGN.  This is an
   angle-proportional, model-magnitude-scaled BILINEAR term, and it is CONTINUOUS through zero
   (a linear ramp near angle 0), so it has no jump and is a SOFT SATURATION, not a hard relay.
=> the term saturates at |gp-0x6abc| >= knee/12 = 250 counts, and is +-1 only past that.

MEASURED saturation duty, engaged HANDS-OFF, 5-10 mph, cmd >= 2048 -- the symptom's own regime:
        knee  600 -> 0.7439     knee 2400 -> 0.0484
        knee 1200 -> 0.4810     knee 3000 -> (V122, the current value)
        knee 1800 -> 0.2353     knee 3600 -> 0.0000   <- THIS BUILD, a MEASURED point
3600 is a MEASURED reading of 0.0000, not an interpolation.

THE COST, STATED PLAINLY
------------------------
With K1 held, friction is LOWER-OR-EQUAL EVERYWHERE and never higher:
        slope 1020/3000 = 0.340000  ->  1020/3600 = 0.283333   = x0.8333, 17% LESS friction
By the VERIFIED polarity (memory: "more modelled friction = MORE assist"), 17% less modelled
friction means SLIGHTLY LESS ASSIST.  That is a real cost and it is in tension with the LKAS
authority complaint.
GAIN-HOLDING IS NOT AVAILABLE: holding slope 0.34 at knee 3600 needs K1 = 1224, above the 1023
ceiling past which friction exceeds |model| and the residual INVERTS.  So the trade cannot be
avoided -- removing the relay necessarily costs friction.
=> the operator's standing instruction is "low apparent steering mass and friction to LKAS AND no
   ratcheting".  This is the only lever in the kit's record that moves BOTH the stated goals the
   same way; the assist reduction is the price.

BLAST RADIUS -- ESTABLISHED BY FLIGHT, NOT BY A STATIC SCAN
-----------------------------------------------------------
0xC40BC has FLOWN at 300, 600, 1800, 2400 and 3000 across V108/V111/V112/V122 with no fault.
3600 is one step beyond a demonstrated-safe family, cal-only, outside the bricking class.

WHAT IS NOT ESTABLISHED
-----------------------
[BELIEF] that the relay is what the operator HEARS.  The duty ladder is a MECHANISM measurement;
the link to the symptom rests on his dose-response across V111/V112/V122, not on an instrumented
endpoint.
[NOTE] the kit's noise floor is ~36x between routes with identical cals, so no between-build
ratio below that carries information.  This build is judged BY EAR.

BASE = V122.  alpha2 8, gain 6x, b26 clamp 511, both Lever A arms stock, deadband at Honda 3,
K1 HELD at 1020, Lever B HELD at 5244 (changing it is V149 -- separate single-lever builds).
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
WRITE_MODE = os.environ.get("ACCORD_V151_WRITE", "").strip().lower()

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
KNEE_CAL, KNEE_OLD, KNEE_NEW = 0xC40BC, 3000, 3600   # the relay knee -- THE EDIT
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

    print("\n  [3] THE EDIT -- ONE CAL")
    check(u16(base, KNEE_CAL) == KNEE_OLD,
          f"  0x{KNEE_CAL:05X} relay knee = {KNEE_OLD} in the V122 base")
    check(u16(base, K1_CAL) == K1_VAL, f"  0x{K1_CAL:05X} K1 = {K1_VAL} in the V122 base")
    struct.pack_into("<H", code, KNEE_CAL, KNEE_NEW)
    attributed |= {KNEE_CAL, KNEE_CAL + 1}
    print(f"      0x{KNEE_CAL:05X}  relay knee  {KNEE_OLD} -> {KNEE_NEW}")
    check(u16(code, KNEE_CAL) == KNEE_NEW, f"  reads back {KNEE_NEW}")

    print("\n  [4] THE RELAY IS REMOVED, AND FRICTION FALLS MONOTONICALLY")
    check(u16(code, K1_CAL) == K1_VAL,
          f"  \U0001f6d1 K1 HELD at {K1_VAL} -- this is a KNEE-ONLY step.  K1 is 3 counts under its"
          f" 1023 ceiling, above which friction exceeds |model| and the residual INVERTS.")
    old_slope, new_slope = K1_VAL / KNEE_OLD, K1_VAL / KNEE_NEW
    check(new_slope < old_slope,
          f"  \U0001f6d1 THE DIRECTION GATE: slope {old_slope:.6f} -> {new_slope:.6f}"
          f" = x{new_slope/old_slope:.4f}, {100*(1-new_slope/old_slope):.0f}% LESS friction."
          f"  the knee normalises ANGLE, so in the UNSATURATED regime -- which is ~99% of"
          f" engaged creep -- the term scales EXACTLY as 1/knee => a uniform x0.8333.  In the"
          f" saturated regime sat() is +-1 either way, so the term is UNCHANGED there."
          f"  => LOWER-OR-EQUAL everywhere, never higher: a MONOTONE reduction.")
    check(KNEE_NEW > KNEE_OLD,
          f"  \U0001f6d1 THE SATURATION GATE: raising the knee raises the ANGLE at which the"
          f" term saturates, from knee/12 = 250 to 300 counts.  MEASURED saturation duty in engaged hands-off creep:"
          f" {KNEE_OLD} -> (current), {KNEE_NEW} -> 0.0000, a measured point, not an interpolation.")
    check(K1_VAL * KNEE_NEW < 2**31 and KNEE_NEW < 2**15,
          f"  no overflow: knee {KNEE_NEW} is inside int16 and K1*knee inside int32")
    check(u16(code, LB_CAL) == LB_HELD,
          f"  0x{LB_CAL:05X} Lever B HELD at {LB_HELD} -- changing it is V149; separate"
          f" single-lever builds, do not stack before either has flown")

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
    exempt = {KNEE_CAL, KNEE_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the relay knee exempted)")

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
    check(payload == 2, f"exactly 2 payload bytes ({payload} found) -- the relay-knee u16")

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
    tag = "V151-V122BASE-KNEE.3000.TO.3600"
    img_out = plain_image_path(f"_v151_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V151_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
