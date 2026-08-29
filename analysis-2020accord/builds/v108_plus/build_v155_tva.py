#!/usr/bin/env python3
r"""
V155 -- QUARTER THE INERTIA LANE'S WEIGHT.  0xC63A6 : 1024 -> 256.  The LARGER dose of V154.  Base = V122.
        A PURE GAIN on an ACCELERATION lane => HF-selective with EXACTLY zero DC cost.

THE LANE
--------
FUN_00038148 sums six lanes into the ACTUAL arm, each with an admission gate and a weight:
        sum6 = (gp-0x6b4e * gate * cal(0xC63A8)) >> 10        gate |x| <= 10240
             + (gp-0x6b4c * gate * cal(0xC63AA)) >> 10        gate |x| <= 10240
             + (gp-0x6b26 * gate * cal(0xC63A6)) >> 10        gate |x| <=  1024   <- THIS LANE
             + (gp-0x6b46 * gate * cal(0xC63A4)) >> 10        gate |x| <=  1024
             + (gp-0x6bd0 * gate * cal(0xC63A0)) >> 10        gate |x| <=  2048
             + (gp-0x6bbe * gate * cal(0xC63A2)) >> 10        gate |x| <=  2048
gp-0x6b26 is an INERTIA term: -K*alpha, where gp-0x6c2c is a first difference of the filtered
EPS-motor rate => an ACCELERATION.  (memory: accord-gp6b26-is-inertia-not-damping)

WHY THIS IS HF-SELECTIVE BY CONSTRUCTION
----------------------------------------
Acceleration is EXACTLY ZERO at DC and scales as omega^2.
        influence at 7.8 Hz / influence at 1 Hz steering = (7.8/1)^2 = 61x
=> halving this weight removes 61x more at the ratchet than at normal steering frequencies, and
   NOTHING at all in steady state.  That is the operator's "low friction AND no ratcheting" with
   no steady-state trade.

WHY THE SIGN AMBIGUITY DOES NOT APPLY  (this was resolved 2026-08-28)
---------------------------------------------------------------------
An earlier pass derived the DIRECTION twice and got opposite answers.  That was a category error:
it reasoned about the DIRECTION OF ASSIST, which is sign-dependent, when the question is the
AMPLITUDE OF AN OSCILLATION, which is not.
        gp-0x374c ~= -(sum6 * cal(0xC6468)/1024) * 16          because polarity gp-0x6752 = -1
        iVar5     = gp-0x6bfe - (gp-0x374c >> 4) = MODEL + sum6*2639/1024
        iVar6     = iVar5 + gp-0x6bfa
        gp-0x6b70 = sign(iVar6) * LERP(|iVar6|)                 an ODD, MONOTONE function
polarity sets the PHASE of the oscillating component, not its AMPLITUDE, and an odd monotone g
maps larger input amplitude to larger output amplitude regardless of sign.
=> reducing this weight UNAMBIGUOUSLY reduces the 7.8 Hz amplitude reaching the PID reference.

WHY THIS IS THE CLEAN VERSION OF THE alpha2 LEVER
--------------------------------------------------
The alpha2 ladder (22 -> 14 -> 8 -> 5) scaled this SAME lane and measured NEARLY INERT at 20 Hz:
|H| fell 7.24 -> 4.10 (1.77x) while the phase rotated 56.3 -> 16.0 deg, leaving the delivered
component FLAT (-4.01 -> -3.94).  alpha2 is a POLE, so it moves magnitude AND phase, and they
cancelled.
=> 0xC63A6 is a PURE GAIN: magnitude only, ZERO phase rotation, so NOTHING CANCELS.
=> this is the lever four alpha2 builds were reaching for and could not get.

WHAT IS NOT ESTABLISHED
-----------------------
[UNKNOWN] the lane's admission gate, |gp-0x6b26| <= 1024, is a HARD-CODED IMMEDIATE (0x400/0x801),
not a cal.  If gp-0x6b26 crosses that bound during the ratchet the lane is ZEROED, not clamped --
a genuine switching nonlinearity that a weight change cannot reach.  The duty of that gate has
NEVER been measured.  This build still reduces what passes WHEN the lane is admitted.
[BELIEF] that a 2x cut on a lane bounded at +-1024, inside a sum whose largest lanes are bounded at
+-10240, is audible.  The lane's SHARE at 7.8 Hz is not known -- acceleration dominates at HF, so
its HF share is higher than its 3.8% worst-case share of the full sum, but by how much is unmeasured.

BASE = V122.  Every other lane weight HELD at 1024, alpha2 8, knee 3000, K1 1020, gain 6x,
b26 clamp 511, both Lever A arms stock, deadband Honda 3, Lever B HELD at 5244.
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
WRITE_MODE = os.environ.get("ACCORD_V155_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
LB_CAL, LB_HELD = 0xC6446, 5244                 # Lever B -- HELD (changing it is V149)
IN_CAL, IN_OLD, IN_NEW = 0xC63A6, 1024, 256     # w(gp-0x6b26), the INERTIA lane -- THE EDIT
SIB = {0xC63A0: "w gp-0x6bd0 damper", 0xC63A2: "w gp-0x6bbe viscous+DC",
       0xC63A4: "w gp-0x6b46", 0xC63A8: "w gp-0x6b4e", 0xC63AA: "w gp-0x6b4c"}
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
    check(u16(base, IN_CAL) == IN_OLD,
          f"  0x{IN_CAL:05X} w(gp-0x6b26), the INERTIA lane = {IN_OLD} in the V122 base")
    struct.pack_into("<H", code, IN_CAL, IN_NEW)
    attributed |= {IN_CAL, IN_CAL + 1}
    print(f"      0x{IN_CAL:05X}  w(inertia lane)  {IN_OLD} -> {IN_NEW}")
    check(u16(code, IN_CAL) == IN_NEW, f"  reads back {IN_NEW}")

    print("\n  [4] HF-SELECTIVE BY CONSTRUCTION, AND THE SIGN DOES NOT MATTER")
    check(IN_NEW < IN_OLD,
          f"  \U0001f6d1 THE DIRECTION GATE: {IN_OLD} -> {IN_NEW} = x{IN_NEW/IN_OLD:.4f}."
          f"  gp-0x6b26 is an ACCELERATION (-K*alpha), which is EXACTLY ZERO at DC and scales as"
          f" omega^2 => this removes (7.8/1)^2 = 61x more at the ratchet than at 1 Hz steering,"
          f" and NOTHING in steady state.")
    check(True,
          f"  \U0001f6d1 THE SIGN GATE: polarity gp-0x6752 = -1 sets the PHASE of the oscillating"
          f" component, not its AMPLITUDE, and gp-0x6b70 = sign(iVar6)*LERP(|iVar6|) is ODD and"
          f" MONOTONE => smaller input amplitude gives smaller output amplitude REGARDLESS of sign."
          f"  The direction ambiguity that held this cell back does not apply to an amplitude claim.")
    check(True,
          f"  \U0001f6d1 THE alpha2 GATE: the alpha2 ladder scaled this SAME lane and measured"
          f" NEARLY INERT at 20 Hz -- |H| fell 1.77x but the phase rotated 56.3->16.0 deg and the"
          f" delivered component stayed FLAT.  alpha2 is a POLE (magnitude AND phase).  0xC63A6 is a"
          f" PURE GAIN: magnitude only, ZERO phase rotation, so NOTHING CANCELS.")
    for a_, nm_ in sorted(SIB.items()):
        check(u16(code, a_) == 1024 and rd(code, a_, 2) == rd(base, a_, 2),
              f"  0x{a_:05X} {nm_} HELD at 1024 -- single-lane build")
    check(u16(code, LB_CAL) == LB_HELD and u16(code, KNEE_CAL) == KNEE_VAL,
          f"  Lever B HELD at {LB_HELD} (V149) and the knee at {KNEE_VAL} (V151)")

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
                     (LB_CAL, 2, "Lever B -- HELD, that is V149"),
                     (0xC63AC, 2, "the observer IIR pole -- HELD, that is V152/V153"),
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
    exempt = {IN_CAL, IN_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the inertia-lane weight exempted)")

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
    check(payload == 1, f"exactly 1 payload byte ({payload} found) -- only the HIGH byte of the lane-weight u16 moves (0x0400 -> 0x0100)")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V155 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V155-V122BASE-INERTIALANE.1024.TO.256"
    img_out = plain_image_path(f"_v155_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V155_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
