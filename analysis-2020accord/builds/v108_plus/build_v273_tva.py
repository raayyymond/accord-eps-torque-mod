# -*- coding: utf-8 -*-
r"""V273 -- THE SELECTOR TAP + THE TWO CURVES THAT SHAPE LKAS AUTHORITY.  BASE: V268.

THREE EDITS, one instrument and two calibration levers.  All three were named by the operator.

  [A] TELEMETRY -- CAN 427 repointed to the VARIANT SELECTOR.  Two code bytes + one immediate.
      This kit has spent ~180 builds dosing cells whose live slot is UNKNOWN.  Two candidate
      records fit this car and they disagree about every mode index:

          record  2  "TVAA15360YTVAA100"   gp+0x63fd in {10,11}   gp-0x674e = 1
          record 11  "TVCA45360YTVCA400"   gp+0x63fd in {24..27}  gp-0x674e = 7

      The part number says record 2.  The flown dose-response on 0xCBE74 slots 26/27 says record 11.
      BOTH selectors come from the SAME matched record, so reading EITHER settles BOTH.
      `gp-0x674e` is the cheaper read: it is a byte at an EVEN offset whose neighbour `gp-0x674d`
      is 0 in every one of the 16 records, so a single `ld.h` yields the selector with no masking.

          wire = clamp(|gp-0x674e| * 5, 0, 1023)      <- `sar 0x3` neutralised to `sar 0x0`
          record  2  =>  wire == 5
          record 11  =>  wire == 35

      The selector is a STATIC boot constant, so ANY drive of any length answers it -- parked,
      disengaged, ten seconds.  It does not need a symptomatic drive and it does not need LKAS.

  [B] OVERRIDE TAPER FLATTENED -- 0xCBA04 / 0xCBA74, Y -> 254 on all 28 records.
      Stock X = (70, 72, 78, 80), Y = (254, 234, 12, 0), indexed by |gp-0x4f60| >> 5.
      Index 0 is BELOW X[0], so hands-off already returns 254.  The curve therefore only acts
      ABOVE raw driver torque ~2240, where it currently cuts LKAS authority to ZERO by ~2560.
      Flattening changes NOTHING below that threshold and stops the cut above it.

  [C] ASSIST MAP LINEARISED -- 0xC9A88, Y = 2 * X on all 28 records.
      Stock X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
            Y = (0, 24, 42, 50, 62, 100, 126, 154, 166, 172)   <- slots 1/7, this car's candidates
      New   Y = (0, 24, 40, 48, 64, 128, 192, 256, 320, 480)

      2.0 counts/index is the map's OWN slope in its first segment, so the low-demand region is
      preserved to within 2 counts and normal steering feel is unchanged.  What goes away is the
      resolution collapse: the top segment currently spends 80 index steps climbing 6 counts
      (slope 0.075, one output level per 13.3 steps).  Linearised it is 2.0 everywhere.

      Corroboration: an independent contributor scaling the SAME table's upper knots
      (x1.5 / x1.75 / x2 / x3, top knot 172 -> 516) reports smooth 2x results on this platform.
      V273's top knot is 480 -- the same territory, reached by a rule rather than by hand.

WHAT IS **NOT** TOUCHED, and asserted byte-for-byte:
  * the code cave 0xC4B34 and its hook 0x55C0E -- V112's, carried byte-identical.  NO CAVE EDIT.
    Caves are this kit's only bricking class (V24, V27, V48B).  This build does not go near one.
  * forward gain 0xC6CD0 (5346), both forward clamps 0xC61B2/0xC61B4 (3072)
  * the rate lane `sar` immediates 0x3AB76 / 0x3AC20 -- left at STOCK 1x.  V255/V256/V269 carried
    the 2x at this gain and were UNDRIVEABLE; that lever does not belong in the same build as a
    2.8x setpoint change.
  * V268's pump flattening -- carried by construction from the base.
  * every P/I/D cal in both loops: 0xC63E6 (Ki, still 0), 0xC6B26/0xC6B12/0xC6AE6, 0xC644A.

RISK THE OPERATOR MUST WEIGH BEFORE DRIVING [B] AND [C] TOGETHER.
  They compound.  At high driver torque AND high command the setpoint is now ~2.8x its stock
  ceiling AND no longer tapers as the driver pushes back.  That is a FEEL and AUTHORITY change,
  not a bricking risk -- it is calibration-only, the engagement ramp gp-0x69b0 still gates the
  whole lane, and openpilot still owns engagement.  But it is the largest single-build authority
  change in this kit's history.  ASSESS IT STATIONARY OR AT LOW SPEED FIRST.
  The taper is the ECU's smooth "driver is fighting me" back-off.  Flattening it does not disable
  the separate override DEBOUNCE path (gp-0x682f vs cal 0xC64B8) -- which V112 already set to 255.

BASE: V268 (which is V112 + both pump families flattened across slots 0-33).
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                   # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V273_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
TAG = "V273-V268BASE-SELECTORTAP.TAPERFLAT.MAPLINEAR"

# ---- [A] telemetry -------------------------------------------------------------------------
SRC_DISP = 0x55DF2                 # the disp16 of `ld.h <disp>, gp, r6` in the 427 packer
SRC_V268 = 0x9544                  # V112/V268 read gp-0x6ABC
SRC_NEW = 0x98B2                   # -0x674e  => reads gp-0x674e (low) | gp-0x674d (high, always 0)
SAR_SITE = 0x55E10                 # `sar 0x3, r6` in the same packer
SAR_V268, SAR_NEW = 0xA3, 0xA0     # sar 0x3 -> sar 0x0, so a value of 1..7 survives the *5

# ---- [B] override taper --------------------------------------------------------------------
TAPER_PTRS = (0xCBA04, 0xCBA74)
TAPER_N = 4
# TWO distinct taper shapes exist across the 28 slots.  Both of this car's candidate slots
# (1 for record 2, 7 for record 11) are in the first group, whose Y[0] is 254.
TAPER_SHAPES = {(70, 72, 78, 80): (254, 234, 12, 0),      # slots 0-9   <- this car
                (32, 48, 64, 112): (255, 205, 154, 0)}    # slots 10-27
# flatten each record to ITS OWN Y[0] -- only ever RAISES Y, never lowers it (V268's rule)

# ---- [C] assist map ------------------------------------------------------------------------
MAP_PTR = 0xC9A88
MAP_N = 10
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
MAP_SLOPE = 2                       # counts of output per unit of index = the map's own first slope
N_SLOTS = 28

# ---- frozen, asserted ----------------------------------------------------------------------
CAVE = (0xC4B34, 0xC4BD8)
HOOK = 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
GAIN_CELL, GAIN_VAL = 0xC6CD0, 5346
CLAMP_P, CLAMP_N, CLAMP_VAL = 0xC61B2, 0xC61B4, 3072
KI_CELL = 0xC63E6
PID_B = {0xC6B26: 256, 0xC6B12: 98, 0xC6AE6: 2048, 0xC644A: 1024}
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p, n):
    return ([u16(b, p + 2 + 2 * i) for i in range(n)],
            [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])


def build():
    print("=" * 102)
    print("  V273 -- SELECTOR TAP + OVERRIDE TAPER FLAT + ASSIST MAP LINEARISED.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(u16(base, GAIN_CELL) == GAIN_VAL, f"forward gain {GAIN_VAL} (6x) present in base")
    check(u16(base, CLAMP_P) == CLAMP_VAL and u16(base, CLAMP_N) == CLAMP_VAL,
          f"forward clamps {CLAMP_VAL} present in base")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X,
          "rate lane is STOCK 1x in base -- V273 does NOT restore V62's 2x")
    check(u16(base, KI_CELL) == 0, "Ki (0xC63E6) is 0 in base -- V273 does not enable it")
    for a, v in PID_B.items():
        check(u16(base, a) == v, f"driver-side PID cal 0x{a:05X} = {v} in base")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240,
          "assist-map index clamp is +-240 -- unchanged, so the index RANGE does not move")

    code = bytearray(base)
    attributed = set()

    # ----------------------------------------------------------------------------- [A]
    print("\n  [2] TELEMETRY -- CAN 427 -> gp-0x674e (the variant selector)")
    check(u16(base, SRC_DISP) == SRC_V268, f"base 427 source disp is 0x{SRC_V268:04X} (gp-0x6ABC)")
    check(base[SAR_SITE] == SAR_V268, "base packer carries `sar 0x3, r6` (a3)")
    struct.pack_into("<H", code, SRC_DISP, SRC_NEW)
    code[SAR_SITE] = SAR_NEW
    attributed |= set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE}
    check(u16(code, SRC_DISP) == SRC_NEW, "427 source now gp-0x674e (disp 0x98B2)")
    check(code[SAR_SITE] == SAR_NEW, "packer shift neutralised to `sar 0x0, r6` (a0)")
    for nm, v in (("record 2", 1), ("record 11", 7)):
        print(f"      -> if {nm}: gp-0x674e = {v}  =>  wire = {min(1023, v * 5)}")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "cave HOOK byte-identical")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "code CAVE byte-identical")

    # ----------------------------------------------------------------------------- [B]
    print("\n  [3] OVERRIDE TAPER FLATTENED -- 0xCBA04 / 0xCBA74, all 28 records")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            p = u32(base, arr + 4 * s)
            check(START <= p < END, f"taper ptr 0x{arr:05X}[{s}] = 0x{p:05X} in range")
            tps.add(p)
    print(f"      {len(tps)} unique taper records across 2 arrays x {N_SLOTS} slots")
    _shape_count = {}
    for p in sorted(tps):
        n = s16(base, p)
        check(n == TAPER_N, f"taper record 0x{p:05X} npt == {TAPER_N}")
        X, Y = rec(base, p, n)
        key = tuple(X)
        check(key in TAPER_SHAPES, f"taper 0x{p:05X} X {key} is a KNOWN shape")
        check(tuple(Y) == TAPER_SHAPES[key], f"taper 0x{p:05X} Y == {TAPER_SHAPES[key]} before edit")
        check(all(Y[i] > Y[i + 1] for i in range(n - 1)),
              f"taper 0x{p:05X} Y strictly DECREASING before edit (it is a cut-off)")
        flat = Y[0]
        check(flat in (254, 255), f"taper 0x{p:05X} Y[0] == {flat}")
        _shape_count[key] = _shape_count.get(key, 0) + 1
        for i in range(n):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, flat)
            attributed |= {o, o + 1}
        nY = rec(code, p, n)[1]
        check(all(y == flat for y in nY), f"taper 0x{p:05X} Y -> flat {flat}")
        check(all(nY[i] >= Y[i] for i in range(n)),
              f"taper 0x{p:05X} flatten only RAISES Y -- no authority removed in any mode")
    check(all(tuple(rec(code, p, TAPER_N)[0]) in TAPER_SHAPES for p in tps),
          "every taper X untouched")
    for k, v in _shape_count.items():
        print(f"      shape X={k} -> flattened in {v} records")

    # ----------------------------------------------------------------------------- [C]
    print("\n  [4] ASSIST MAP LINEARISED -- 0xC9A88, Y = 2*X, all 28 records")
    MAP_Y_NEW = tuple(MAP_SLOPE * x for x in MAP_X)
    print(f"      X   {MAP_X}")
    print(f"      Y-> {MAP_Y_NEW}")
    mps = set()
    for s in range(N_SLOTS):
        p = u32(base, MAP_PTR + 4 * s)
        check(START <= p < END, f"map ptr [{s}] = 0x{p:05X} in range")
        mps.add(p)
    print(f"      {len(mps)} unique assist-map records across {N_SLOTS} slots")
    for p in sorted(mps):
        n = s16(base, p)
        check(n == MAP_N, f"map record 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        check(Y[0] == 0, f"map 0x{p:05X} Y[0] == 0 before edit")
        for i, y in enumerate(MAP_Y_NEW):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        nX, nY = rec(code, p, n)
        check(tuple(nY) == MAP_Y_NEW, f"map 0x{p:05X} Y -> linear")
        check(all(nY[i + 1] > nY[i] for i in range(n - 1)),
              f"map 0x{p:05X} strictly MONOTONE -- no V80 relay plateau")
        check(all(nX[i + 1] > nX[i] for i in range(n - 1)), f"map 0x{p:05X} X still monotone")
    check(all(tuple(rec(code, p, MAP_N)[0]) == MAP_X for p in mps), "every map X untouched")

    print("\n      delivered setpoint, stock vs V273 (slots 1/7 record):")

    def lerp(X, Y, x):
        if x <= X[0]:
            return Y[0]
        if x >= X[-1]:
            return Y[-1]
        for i in range(1, len(X)):
            if x <= X[i]:
                return ((Y[i] - Y[i - 1]) * (x - X[i - 1])) // (X[i] - X[i - 1]) + Y[i - 1]
    p1 = u32(base, MAP_PTR + 4)
    oX, oY = rec(base, p1, MAP_N)
    for idx in (0, 16, 32, 64, 128, 160, 200, 240):
        print(f"        index {idx:3d}   stock {lerp(oX, oY, idx):4d}   V273 {lerp(MAP_X, MAP_Y_NEW, idx):4d}")

    # ----------------------------------------------------------------------------- frozen
    print("\n  [5] FROZEN CELLS RE-ASSERTED ON THE BUILT IMAGE")
    for nm, a, v in ((f"gain 0x{GAIN_CELL:05X}", GAIN_CELL, GAIN_VAL),
                     (f"clamp 0x{CLAMP_P:05X}", CLAMP_P, CLAMP_VAL),
                     (f"clamp 0x{CLAMP_N:05X}", CLAMP_N, CLAMP_VAL),
                     (f"Ki 0x{KI_CELL:05X}", KI_CELL, 0)):
        check(u16(code, a) == v, f"{nm} still {v}")
    for a, v in PID_B.items():
        check(u16(code, a) == v, f"driver-side PID cal 0x{a:05X} still {v}")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X, "rate lane still stock 1x")
    check(code[IDX_CLAMP_P] == 240 and code[IDX_CLAMP_N] == 240, "index clamp still +-240")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "cave still byte-identical")

    # ----------------------------------------------------------------------------- CRC
    print("\n  [6] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    touched = 0
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        touched += 1
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    # ----------------------------------------------------------------------------- diff
    print("\n  [7] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE}
    for p in tps:
        allow |= {p + 2 + 2 * TAPER_N + k for k in range(2 * TAPER_N)}
    for p in mps:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    check(set(pay) <= allow, "every payload byte is a taper Y knot, a map Y knot, or one of the "
                             "3 telemetry code bytes -- no X axis, no cave, no gain, no clamp")
    codebytes = [x for x in pay if x < 0xC0000]
    check(set(codebytes) == set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE},
          f"exactly 3 code bytes move, all in the 427 packer: {[hex(x) for x in sorted(codebytes)]}")
    print(f"      {len(pay)} payload bytes, {len(codebytes)} of them code, {touched} CRC trailers")

    # ----------------------------------------------------------------------------- rwd
    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V273 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v273_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V273_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
