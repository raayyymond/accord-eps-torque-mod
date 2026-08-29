#!/usr/bin/env python3
r"""
V156 -- LET THE DAMPER REACH THE MICRO REGIME.  Base = V122.
        FactorC Y[0] 0 -> 60  AND  FactorE Y[0] 0 -> 539, engaged modes 26/27.
        The FIRST build in which the base-assist damper is non-zero where the ratchet lives.

THE MECHANISM
-------------
        ch0 = (FactorC(speed) x FactorE(rate)) >> 10        -> gp-0x6bd0, the DAMPER lane
Both factors are LERPs whose FIRST knot value is ZERO, so the product is a PRODUCT OF TWO DEAD
ZONES.  Below X[0] a LERP returns Y[0], so:
        FactorC  X = [2240, 3840, 5120, 8960]  = [35, 60, 80, 140] km/h ,  Y[0] = 0
                 => ZERO below 35 km/h  => zero at ALL creep speeds
        FactorE  X = [  60,  400, 2500, 4000] ,                           Y[0] = 0
                 X[0] = 60 <-> the recorded 12.73 deg/s dead zone => ~0.212 deg/s per count
                 => the MICRO REGIME (1-13 deg/s) sits ENTIRELY BELOW X[0], exactly where Y[0] applies
=> the damper is measured ZERO on 100% of the micro regime and 95.91% of engaged frames.
=> a resonance with zeta 0.017-0.036 is sitting in a regime with NO added damping at all.

WHY NEITHER FACTOR ALONE WORKS -- AND WHY THIS BUILD IS THE PAIR
-----------------------------------------------------------------
The kit tried each side separately and each was structurally vacuous, for the same reason:
        V134            raised FactorC Y[0] 0 -> 60          MEASURED INERT at creep
                        its own header: "FactorE Y[0] = 0 below this build raises FactorC Y[0]
                        into a product that is still zero there."
        FactorE X[0] 60->12 variant   WITHDRAWN before flight, "structurally vacuous at creep
                        (FactorC Y[0] = 0 below 34.97 km/h zeroes the product)"
=> a PRODUCT of two dead zones cannot be opened from one side.  BOTH Y[0] must move together, and
   that build has never existed.  This is it.

THE DOSE, AND THE HARD CEILING THAT SIZES IT
---------------------------------------------
V80 set FactorC FLAT 566 across all four knots and produced THE WORST GRINDING IN THE KIT'S HISTORY,
because a large product passes the per-mode ceiling and TURNS THE DAMPER INTO A BANG-BANG RELAY.
That is the failure mode to stay away from, and it bounds the dose:
        creep product = (FactorC_Y0 x FactorE_Y0) >> 10 = (60 x 539) >> 10 = 31
        ceiling = 512   =>   this build sits at 6.1% of it
FactorC Y[0] = 60 is V134's own value, chosen and safety-checked there.  FactorE Y[0] = 539 is
FactorE's OWN Y[2] -- a value already present in the table, not an invention.
=> 31 counts of damping where there are currently EXACTLY ZERO.  Small in absolute terms, but the
   step from 0 to non-zero is a change of KIND, not of degree.
=> the ladder above this is bounded by 512 and is available if the direction reads right.

WHY THIS RESPECTS THE OPERATOR'S CONSTRAINT
--------------------------------------------
His standing instruction: "Increasing mass and friction should not be our primary approach to
resolving the ratcheting IF IT COMES AT THE COST OF max steering angular velocity and acceleration."
Viscous damping costs slew rate -- but this build adds damping ONLY where FactorE Y[0] applies,
which is BELOW 12.73 deg/s.  That is the micro regime, where he is not slewing.
=> above 12.73 deg/s FactorE is UNCHANGED, so maximum angular velocity and acceleration are
   untouched.  The cost lands entirely in the regime that has the symptom.

WHAT IS NOT ESTABLISHED
-----------------------
[BELIEF] that 31 counts is enough to be felt.  It is 6.1% of the ceiling and the first non-zero
value ever placed there; no dose-response exists because no build has ever had a live damper here.
[EVIDENCE] the dead zones, the addresses, the units, the ceiling and V80's failure mode.
[NOTE] 0xC63A0, the damper's WEIGHT in Path 2, is HELD at stock 1024.  It was doubled by V72-V76 and
is EXONERATED of V74's fault (that was 0xC407E), but it multiplies whatever this build admits, so
moving both at once would not be single-variable.

BASE = V122.  Lever B HELD 5244, knee 3000, K1 1020, alpha2 8, both observer poles stock,
inertia-lane weight 1024, 0xC63A0 stock 1024.
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
WRITE_MODE = os.environ.get("ACCORD_V156_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
LB_CAL, LB_HELD = 0xC6446, 5244                 # Lever B -- HELD (changing it is V149)
FC_Y0 = {26: 0xD77DA, 27: 0xD77EE}              # FactorC Y[0] -- the SPEED dead zone
FE_Y0 = {26: 0xD7816, 27: 0xD782A}              # FactorE Y[0] -- the RATE  dead zone
FC_NEW, FE_NEW = 60, 539                        # the doses
FC_X  = {26: 0xD77D2, 27: 0xD77E6}              # asserted UNTOUCHED
FE_X  = {26: 0xD780E, 27: 0xD7822}              # asserted UNTOUCHED
CEIL  = 512                                     # V80: past this the damper is BANG-BANG
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

    print("\n  [3] THE EDIT -- FOUR CELLS, TWO FACTORS x TWO ENGAGED MODES")
    for _m in sorted(FC_Y0):
        check(u16(base, FC_Y0[_m]) == 0,
              f"  mode {_m} FactorC Y[0] = 0 in the base -- the damper is DEAD below 35 km/h")
        check(u16(base, FE_Y0[_m]) == 0,
              f"  mode {_m} FactorE Y[0] = 0 in the base -- and DEAD below 12.73 deg/s")
        struct.pack_into("<H", code, FC_Y0[_m], FC_NEW)
        struct.pack_into("<H", code, FE_Y0[_m], FE_NEW)
        attributed |= {FC_Y0[_m], FC_Y0[_m] + 1, FE_Y0[_m], FE_Y0[_m] + 1}
        print(f"      mode {_m}  0x{FC_Y0[_m]:05X} FactorC Y[0]  0 -> {FC_NEW}")
        print(f"      mode {_m}  0x{FE_Y0[_m]:05X} FactorE Y[0]  0 -> {FE_NEW}")
        check(u16(code, FC_Y0[_m]) == FC_NEW and u16(code, FE_Y0[_m]) == FE_NEW, "  both read back")

    print("\n  [4] THE PRODUCT IS NON-ZERO AT CREEP, AND FAR UNDER THE BANG-BANG CEILING")
    prod = (FC_NEW * FE_NEW) >> 10
    check(prod > 0,
          f"  \U0001f6d1 THE REACH GATE: creep product = ({FC_NEW} x {FE_NEW}) >> 10 = {prod}."
          f"  It is currently EXACTLY 0 on 100% of the micro regime, because ch0 is a PRODUCT of two"
          f" dead zones and NEITHER factor alone can open it -- V134 moved FactorC and measured"
          f" INERT; the FactorE-only variant was withdrawn as structurally vacuous.")
    check(prod < CEIL,
          f"  \U0001f6d1 THE BANG-BANG GATE: {prod} is {100.0*prod/CEIL:.1f}% of the {CEIL} ceiling."
          f"  V80 set FactorC FLAT 566, passed the ceiling, turned the damper into a BANG-BANG relay"
          f" and produced the worst grinding in the kit's history.  This build stays far under it.")
    check(FC_NEW == 60,
          f"  FactorC Y[0] = {FC_NEW} is V134's own value, chosen and safety-checked there")
    for _m in sorted(FC_X):
        _cx = [u16(code, FC_X[_m] + 2 * i) for i in range(4)]
        _bx = [u16(base, FC_X[_m] + 2 * i) for i in range(4)]
        _ex = [u16(code, FE_X[_m] + 2 * i) for i in range(4)]
        _fx = [u16(base, FE_X[_m] + 2 * i) for i in range(4)]
        check(_cx == _bx and _ex == _fx,
              f"  mode {_m} FactorC X {_cx} and FactorE X {_ex} UNTOUCHED -- no knot moves")
        check(u16(code, FC_Y0[_m] + 2) == u16(base, FC_Y0[_m] + 2)
              and u16(code, FE_Y0[_m] + 2) == u16(base, FE_Y0[_m] + 2),
              f"  mode {_m} Y[1..3] of BOTH factors UNTOUCHED -- only the Y[0] dead-zone knot moves")
    check(u16(code, 0xC63A0) == 1024,
          "  0xC63A0 the damper WEIGHT held at stock 1024 -- it multiplies what this build admits,"
          " so moving both would not be single-variable")
    check(u16(code, LB_CAL) == LB_HELD and u16(code, KNEE_CAL) == KNEE_VAL,
          f"  Lever B HELD {LB_HELD} (V149), knee {KNEE_VAL} (V151)")

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
    exempt = set()
    for _m in FC_Y0:
        exempt |= {FC_Y0[_m], FC_Y0[_m] + 1, FE_Y0[_m], FE_Y0[_m] + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the four dead-zone knots exempted)")

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
    check(payload == 6, f"exactly 6 payload bytes ({payload} found) -- 1 for each FactorC Y[0] (0->60) and 2 for each FactorE Y[0] (0->539), on 2 modes")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V156 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V156-V122BASE-DAMPER.REACHES.MICRO"
    img_out = plain_image_path(f"_v156_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V156_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
