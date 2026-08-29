#!/usr/bin/env python3
r"""
V165 -- THE HIGH-DOSE DAMPER BRANCH.  FactorE Y[1] and Y[2] 539 -> 700.  Base = V158.
        0xD7818/0xD781A (m26) and 0xD782C/0xD782E (m27).  FOUR HALFWORDS.

WHEN TO FLY THIS
----------------
Pre-registered branch (docs/scoring/SCORING-V158-preregistered.md): fly this if V158 leaves the
ratchet UNCHANGED and the steering effort also unchanged.  That combination means x2.74 of added
firmware-side viscous damping was too small to matter, which in turn means the firmware's viscous
term does NOT dominate the plant's damping -- and that is a DATA result which overturns the golden
model's "err low" argument rather than a guess against it.

THE ARITHMETIC
--------------
        at the measured operating point gp-0x6ac0 = 99
        V158   FactorE(99) = 120 -> dose 50    viscous 2.733 ct/(deg/s)   total 4.304   x2.74
        V165   FactorE(99) = 156 -> dose 65    viscous 3.553 ct/(deg/s)   total 5.124   x3.26
        (baseline: gp-0x6bbe measures 1.571 ct/(deg/s) on-car; stock creep is 0.000)

WHY RAISE BOTH Y[1] AND Y[2], AND WHY NOT Y[3]
-----------------------------------------------
Raising Y[1] alone would push it above Y[2] and make FactorE NON-MONOTONE on the RATE axis, which is
the one axis where monotonicity is load-bearing.  Raising both keeps Y = [0, 700, 700, 927] ascending.
Y[3] is deliberately NOT raised, for two reasons:
  (1) a rising segment must survive on X 2500..4000, or the damper flattens across the whole rate
      axis into a near-BANG-BANG RELAY -- V72's error, and a relay at a lightly-damped resonance is a
      limit-cycle GENERATOR;
  (2) the build-time rule is (FactorC x FactorE[3]) >> 10 <= 512, and holding Y[3] = 927 keeps it at
      388, exactly V158's value.

WHAT IS HELD
------------
[EVIDENCE] the FactorC records are BYTE-IDENTICAL to V158 on both engaged modes -- the SPEED arm is
untouched, so this build moves ONLY the rate-axis magnitude.
[EVIDENCE] dose 65 is 12.7 % of the 512 creep ceiling, a 7.9x margin to V80's bang-bang failure.
[EVIDENCE] Lever B carried at 5244; knee, K1, alpha2 and the cave are V122/V158 values.
=> cal-only, four halfwords, outside the cave/bricking class.

WHAT IS NOT ESTABLISHED
-----------------------
[NOTE] 65 sits just ABOVE the golden model's stated requirement band of ~43 [30, 60].  That is
deliberate and conditional: this build is ONLY to be flown if V158's dose measured as insufficient,
in which case the requirement itself is what the data has contradicted.  Do NOT fly it as a first
choice -- the model argues the true delivered dose is HIGHER than computed (the rate conversion is
rigid-body and biased low through a resonance), so erring low is the correct side of that error
until a drive says otherwise.
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
WRITE_MODE = os.environ.get("ACCORD_V165_WRITE", "").strip().lower()

BASE_NAME = "_v158_V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE_plain_image.bin"
BASE_SHA = "42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
FE_Y   = {26: (0xD7818, 0xD781A), 27: (0xD782C, 0xD782E)}   # FactorE Y[1], Y[2] -- THE EDIT
FE_OLD, FE_NEW = 539, 700                      # raise BOTH so the shape stays monotone
LB_CAL, LB_HELD = 0xC6446, 5244                # Lever B -- carried from V158
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
    print("  V165 -- HIGH-dose damper branch, FactorE Y[1,2] 539 -> 700")
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

    print("\n  [3] THE EDIT -- FOUR HALFWORDS, Y[1] AND Y[2] PER ENGAGED MODE")
    for _m in (26, 27):
        for _a in FE_Y[_m]:
            check(u16(base, _a) == FE_OLD, f"  0x{_a:05X} mode {_m} FactorE Y = {FE_OLD} in the V158 base")
            struct.pack_into("<H", code, _a, FE_NEW)
            attributed |= {_a, _a + 1}
            print(f"      0x{_a:05X}  mode {_m} FactorE Y  {FE_OLD} -> {FE_NEW}")
            check(u16(code, _a) == FE_NEW, f"  reads back {FE_NEW}")

    print("\n  [4] MORE DOSE, AND THE RATE-PROPORTIONALITY IS PRESERVED")
    for _m in (26, 27):
        _rE = u32(base, 0xC9F84 + 4*_m)
        _Y = [u16(code, _rE + 0xA + 2*i) for i in range(4)]
        _X = [u16(code, _rE + 2 + 2*i) for i in range(4)]
        check(_Y == sorted(_Y),
              f"  \U0001f6d1 THE SHAPE GATE: mode {_m} FactorE Y = {_Y} is MONOTONE NON-DECREASING.")
        check(_Y[-1] > _Y[-2],
              f"  \U0001f6d1 THE ANTI-RELAY GATE: Y[3] = {_Y[-1]} still RISES above Y[2] = {_Y[-2]},"
              f" so a rising segment survives on X {_X[2]}..{_X[3]}.  Flattening FactorE across the"
              f" WHOLE rate axis is V72's error -- it turns the damper into a near-BANG-BANG RELAY,"
              f" and a relay at a lightly-damped resonance is a limit-cycle GENERATOR.")
    _E158 = 539 * (99 - 12) // (400 - 12)
    _E = FE_NEW * (99 - 12) // (400 - 12)
    _d158 = (429 * _E158) >> 10
    _d = (429 * _E) >> 10
    check(_d > _d158,
          f"  \U0001f6d1 THE DOSE GATE: at gp-0x6ac0 = 99, FactorE {_E158} -> {_E} and dose"
          f" {_d158} -> {_d} = x{_d/_d158:.3f}.  Viscous damping {2.733*_d158/50:.3f} ->"
          f" {2.733*_d/50:.3f} ct/(deg/s); total creep viscous {1.571+2.733*_d158/50:.3f} ->"
          f" {1.571+2.733*_d/50:.3f} against a measured gp-0x6bbe baseline of 1.571.")
    check(((429 * 927) >> 10) <= 512,
          f"  the build-time rule (FactorC x FactorE[3])>>10 = {(429*927)>>10} <= 512 -- Y[3] untouched")
    check(_d < 512 // 4,
          f"  \U0001f6d1 THE BANG-BANG GATE: dose {_d} is {100.0*_d/512:.1f} % of the 512 creep"
          f" ceiling, a {512/_d:.1f}x margin to V80's bang-bang failure.")
    for _m in (26, 27):
        _rC = u32(base, 0xC9E9C + 4*_m)
        check(rd(code, _rC, 0x12) == rd(base, _rC, 0x12),
              f"  mode {_m} FactorC record byte-identical -- the SPEED arm is exactly V158's")
    check(u16(code, LB_CAL) == LB_HELD, f"  Lever B carried at {LB_HELD} from V158")

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
    exempt = set(attributed)
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the edited damper cells exempted)")

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
    check(payload == 4, f"exactly 4 payload bytes ({payload} found) -- four halfwords, but 539=0x021B -> 700=0x02BC moves only the LOW byte of each")

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
    tag = "V165-V158BASE-DAMPER.HIGHDOSE.FE.Y12.700"
    img_out = plain_image_path(f"_v165_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V165_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
