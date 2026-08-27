"""Build V41: V40's exact functional content, with the CRC of block [0xC5000,0xC5FFC) repaired.

CAL-ONLY. Zero code edits, zero code caves. Every success in this kit since V29 has been cal-only;
both trampoline builds (V24, V27) faulted. V40 deliberately returned to the cal-only class after V39's
48-byte cave produced a null result on-car, and V41 stays there.

===============================================================================================
WHY V41 EXISTS -- OPERATOR DIRECTIVE: LKAS COMMAND SHOULD REACH THE MOTOR UNFILTERED
===============================================================================================
Operator instruction, 2026-07-20: the delivered LKAS command should be as true as possible to what
openpilot asks for, relying on the comma's own peer-reviewed rate limiting. Two things to remove:
  1. the limit on how fast an LKAS command slew reaches delivered torque
  2. the cap that reduces delivered LKAS torque at high motor electrical-angle rate
(Motor electrical angle is mechanically coupled to steering angle, so (2) is a cap that tightens the
faster you turn the wheel -- which is exactly the hard-turn regime where the ratchet is felt.)

*** ONE CORRECTION TO THAT MODEL, AND IT DETERMINES WHAT THIS BUILD TOUCHES ***

NEITHER mechanism is LKAS-only where V40 attacked them:
  - the merged-command governor FUN_0004503c takes its target from gp-0x6b94 (VERIFIED at 0x453E0),
    which is the AGGREGATOR output -- LKAS *plus base assist*.
  - the 0xC5000 cap table feeds gp-0x4f64, read by that same governor at 0x453F0. It bounds the
    MERGED command, not the LKAS lane.
V40 raised the merged governor's slew cals 0xC6206/0xC6208 to 65535. That build was FLASHED and the
car came up with an EPS lamp and NO power steering, stationary and untouched. Removing the merged
slew limit is currently the best-supported cause: a slew limiter is a low-pass filter on the torque
command, at rest the target is sensor noise around zero, and the sign-crossing reset in FUN_0004503c
has NO hysteresis and NO minimum magnitude (VERIFIED) -- so it fires on every noise sign flip and the
command snaps to the full noisy target every cycle. The comma's safety rationale does not extend to
base assist, which openpilot neither commands nor observes.

SO V41 DOES THE OPERATOR'S INTENT AT THE ADDRESSES WHERE IT IS ACTUALLY LKAS-SPECIFIC:

  CHANGE 1 -- 0xC6194 (tp+0x7194) 3 -> 0xFFFF.  The LKAS-LANE-ONLY per-cycle rate limiter, inside
    FUN_00026c80, which writes gp-0x6b4c -- the LKAS lane the aggregator reads at 0x3AA3E. Single
    reader image-wide at 0x27622. Its function body consumes NO driver-torque variable: this limiter
    is genuinely LKAS-specific and base assist does not pass through it. The limited state is stepped
    toward a target bounded by 0xC6192=2048 / 0xC6198=3072, so a step of 65535 can never bind again.
    This is the real answer to "LKAS command slew should not be limited."
    NOTE: the step's UNITS are not established (it acts on a 32-bit state gp-0x3d6c that then passes
    through a LERP correction, a gain and a scale). Removing the limit does not require the units;
    SIZING a smaller value would. Do not pick an intermediate value without the transfer function.

  CHANGE 2 -- cap table flattened to Y=5325 with Q13 slopes zeroed, both mirror copies. The table
    CLAMPS at both ends (VERIFIED at 0x7b658-0x7b67a: below X[0] it returns Y[0]=5325, at/above
    X[4]=4100 it returns Y[4]=512, branches to 0x7b71a skip the interpolation entirely). So stock
    slams the cap to 512 once steering rate crosses 4100 -- an 82% instantaneous cut against V38's
    ~2806 command, since motion toward zero is unlimited in the governor. THAT is the ratchet, and
    stock V9's 417-count command was BELOW the 512 floor, so stock LKAS could never be capped at all
    -- V38's 4x raise is the first build to cross it, which is when the ratchet appeared.
    Flattening does not raise the ceiling: flat 5325 sits above the governor nominal 4762, so the
    adaptive arm simply stops binding. At rest stock and flat are IDENTICAL (both clamp to Y[0]).

  NOT TOUCHED -- 0xC6206/0xC6208, the merged-command governor slew. Left at stock 512/205.

The cap tables live in [0xC5000,0xC5FFC), whose CRC at 0xC5FFC this builder recomputes. Note the
bootloader does NOT check that block (FUN_0000b006 hard-codes a bridge past it, byte-verified) and no
app-code reader of 0xC5FFC exists -- the recompute is hygiene, not a functional requirement.

===============================================================================================
WHY V40 EXISTS -- V39 WAS FLASHED AND FIXED NEITHER SYMPTOM
===============================================================================================
V38 is fault-free on-car but shows two behaviours:
  1. tens-of-Hz vibration/grinding, worst near 5 mph, on SMALL LKAS commands that cross zero rapidly
  2. several-Hz ratchet on hard turns -- the wheel feels able to turn harder but is intermittently
     stopped

V39 zeroed the direct Sensor-B torque-rate lane r24 and changed NEITHER. That falsifies r24, and by
elimination this session closed out every other structural candidate:

  r24 direct lane .......... falsified on-car by V39
  gp-0x6acc +/-8192 collapse  NOT REACHABLE: envelope is governor 4762 + compensation ceiling 2560
                             = 7322, and the boundary is 8192 (margin 870). The compensation ceiling
                             is 2560 from the LERP2 table bytes at 0xC67D2..0xC67DC -- an earlier
                             claim of 4762 was a conflation with governor cal 0xC6202 and is retracted.
  gp-0x6bd0 sign flip ...... NO-OP: gp-0x6abe is written from a LITERAL 32767 (movea 0x7fff @0x419de)
                             whenever |gp-0x4f50| <= 13000, i.e. all normal driving. It only carries a
                             live signed value on the abnormal branch where the resolver rate has
                             already exceeded its own clamp. And FUN_00034350 independently zeroes its
                             own term when |gp-0x6abe| > 13000, so at the sentinel the flip is moot.
  gp-0x67ac mode bypass .... UNREACHABLE: the selector folds the 11-entry source-type array at
                             tp+0x5124 (0xC4124) to a boolean by testing each element against 2/3/4.
                             The A160 array is (0,0,5,0,5,5,0,0,0,5,0) -- no element matches, so the
                             aggregator takes the full 10-lane path every cycle and cannot toggle.
  gp-0x6ad4 resonance ...... overdamped, both IIR gains 4/1024 => tau ~256 cycles

The sole survivor is m_motor_torque_governor FUN_0004503c, and it is the only candidate that predicts
a vibration keyed to ZERO CROSSINGS rather than command magnitude -- which is what the operator
reports. Nothing else on that list explains why a SMALL command vibrates.

===============================================================================================
CHANGE 1 -- REMOVE THE GOVERNOR SLEW LIMIT  (0xC6206, 0xC6208)
===============================================================================================
FUN_0004503c holds a running value gp-0x138a and, VERIFIED at the instruction level:

  sign-crossing reset @0x45420-0x45436: when TARGET and HELD have opposite nonzero signs,
      `mov 0x0,r14 ; st.h r0,-0x138a[gp]` -- the accumulator is zeroed OUTRIGHT.
  asymmetric slew @0x4543a-0x4545e (r10=TARGET, r14=HELD): motion AWAY from zero is capped to
      HELD +/- STEP; motion TOWARD zero is immediate and unlimited.
  step selector @0x45402-0x45419: gp-0x67f5==0 -> cal 0xC6206 (512), else -> cal 0xC6208 (205).
      gp-0x67f5 is written by the driver-torque voter FUN_00041eec: forced to 0xFF with NO debounce
      whenever raw driver torque diverges from the voted average by >=65 counts, and debounced to 1
      while voted |torque| >= 640. BOTH conditions hold during a hard dynamic turn, so the step is
      pinned to the SLOW 205 cal exactly in the regime where the ratchet is reported.

So every zero crossing dumps delivered torque to zero and it must climb back at a fixed step. Command
MAGNITUDE is irrelevant; only crossing RATE matters -- which is why small commands vibrate.

*** THE INVARIANT V38 BROKE IS RAMP TIME, NOT STEP SIZE. *** The step cals are ABSOLUTE counts and no
build has ever touched them, but V38 raised the target ~4x. Cycles-to-full-command, slow step:

    stock V9   417 counts ->  3 cycles       V9  + assist 1441 ->  8 cycles
    V38       1782 counts ->  9 cycles       V38 + assist 2806 -> 14 cycles

Operator directed removing the limit entirely rather than restoring the stock ratio. Both cals go to
0xFFFF so the away-from-zero branch can never bind (max possible demand swing is 2*0x2800 = 20480).

OVERFLOW CLEARED BY TRACE, not assumed: the cal is consumed as
    iVar20 = (int)((uint)cal * (uVar15 & 0xffff)) >> 0xf;
an unsigned 16x16->32 multiply cast to signed then arithmetic-shifted. uVar15 is the output of a chain
of FUN_00049a78 calls, which is a plain unsigned min(a,b), seeded from the literal 0x8000 at function
entry -- so uVar15 is provably bounded to [0,32768] and cannot be raised by a corrupted operand (MIN
can only discard a large value). Worst case 65535*32768 = 0x7FFF8000 < 0x80000000: no sign flip.

===============================================================================================
CHANGE 2 -- FLATTEN THE MOTOR-RATE ADAPTIVE TORQUE CAP  (bank A, both copies)
===============================================================================================
The cap's axis is MOTOR RESOLVER ELECTRICAL-ANGLE RATE, not road speed (7-hop verified in a prior
session). Its A160 table tapers 5325 -> 512 as motor rate rises, and its FLOOR is 512.

  STOCK V9's max LKAS demand is 417 counts -- BELOW the 512 floor. Stock LKAS can NEVER be rate-capped.

V38 (1782) is the first flashed build to clear that floor, so the cap binds from motor rate z~3414,
and with base assist in the aggregate from z~2229. It cuts torque precisely when the motor is turning
fast, which is exactly the fast low-speed maneuver the operator wants for self-driving hard turns.

FLATTENING DOES NOT RAISE THE CEILING. The governor is MIN(nominal 4762, adaptive LERP, budget B).
Flat Y=5325 is above the 4762 nominal, so the adaptive arm simply never binds and the effective
governor becomes MIN(4762, budget) -- 4762 at every rate, which is exactly what the motor already
sees at low rate today. Two of the three protection arms are untouched.

A flat Y is NOT sufficient on its own: the cap evaluates Y[i] + (((z - X[i]) * slope_q13) >> 13), so
leaving the precomputed Q13 slopes non-zero would keep interpolating between flat points and produce
an internally inconsistent table. The slopes MUST go to zero in the same edit.

BANK STRUCTURE (verified by byte-read of _v38_plain_image.bin):
  bank A is the live, app-tp-addressable one -- tp=0xBF000, tp+0x620C/tp+0x6224 records and
  tp+0x6030/tp+0x6038 slopes. Every tp-relative reference to it lives inside FUN_0007b022, the writer
  of gp-0x4f64 (displacement hits cluster at 0x7B0A0/A4/A8, 0x7B0FA, 0x7B1E8/EC, 0x7B6AC, 0x7B6E4,
  0x7B7B6). Each record is a 24-byte combined block: u16 count(5), s16 X[5], s16 Y[5], u16 terminator.
  0xC5224 is a byte-for-byte duplicate of the WHOLE 0xC520C record, not a separate Y array.
  FUN_0007b022's preamble reads BOTH copies unconditionally every cycle and builds two parallel
  parameter blocks. Whether they cross-check each other is NOT ESTABLISHED -- so given this kit's V27
  asymmetric-mirror failure precedent, both copies are patched byte-identically. Never let them diverge.

  banks B (0xF9E0C/0xF9E24, slopes 0xF9C30/0xF9C38) and C (0xFAA0C/0xFAA24, slopes 0xFA830/0xFA838)
  are byte-identical replicas that are NOT reachable from app tp and are referenced by no coherent
  app code path. They sit in block [0xF9000,0xFCFFC), untouched by any build to date. LEFT ALONE.

SHADOW IS NOT VALUE-SENSITIVE -- this was the build's last blocker and it is cleared. All three
mode branches of FUN_0007b022 use a STORED-DUPLICATE consistency check, not an independent
recomputation:
    if (gp-0x4f64 == gp-0x448a) { v = round(fVar39); gp-0x4f64 = v; gp-0x448a = v; }
    else FUN_0006b9ee();   // fault 0x17, HARD-FAULT-ELIGIBLE (motor off + power cycle)
Both cells receive the SAME freshly-computed value every cycle, so the check trips only on RAM
divergence BETWEEN cycles, never on a calibration value. Flattening bank A cannot trip it.

NO FLOAT MIRROR EXISTS for either change. An image-wide scan found no f32/f64 encoding of 5325, 2406
or 1587 at raw or 1/1024 scale, and no matched 512/205 float pair (205 has no float representation
anywhere at any scale). The V27 int/float asymmetry class does not apply.

===============================================================================================
CRC
===============================================================================================
TWO blocks need a recompute, and V40 only did one of them. That omission is what V41 exists to fix.

  0xC6206/0xC6208 are in block [0xC6000,0xC6FFC) -- CRC @0xC6FFC. V40 did recompute this one.
  the bank-A cap tables are in block [0xC5000,0xC5FFC) -- CRC @0xC5FFC. V40 did NOT. <-- the bug.

There is NO gap in the chain. The claim that [0xC5000,0xC6000) was uncovered came from the bogus
0xC6000 bridge described at the top of this file; V40's own assert_crc_gap_is_real() faithfully
re-derived the gap from that same wrong walk and therefore "proved" it. A verifier and the assertion
that checks the verifier cannot share the same assumption -- that is how this reached a car.

V41 asserts the INVERSE: every address it writes must be provably INSIDE a CRC-covered block, and
every block it dirties must have its CRC recomputed. Being uncovered is now a build-stopping error.

Study artifact. This script performs NO CAN, UDS, or flash operation.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V40 builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks


START, END = 0x13000, 0x100000
V38_PLAIN = str(plain_image_path("_v38_plain_image.bin"))
V38_RWD = os.path.join(
    RWD_DIR,
    "39990-TVA,A160-V38-LKAS-4x-V37guards-softwall5120-float5-setpoint16384-0x13000-0x100000.rwd",
)
V38_SHA256 = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
V38_RWD_SHA256 = "c6fdb297635b43681d7692ebf86de2071bd687566bb96ff0ee06977cc4d4b990"
EXPECTED_HEADERS = [
    (b"#", [b"\x00"]),
    (b"?", [b"A1"]),
    (b"/", [b"39990-TVA-A110", b"39990-TVA,A160"]),
    (b"!", [b"001100121020", b"001100121020"]),
    (b"&", [b"BF109E"]),
    (b"%", [b"30"]),
]

V41_TAG = "LKAS-4x-V38base-ratecap-flat5325"
V41_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V41-{V41_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v41_plain_image.bin"))

# V40 is the flashed-and-faulted predecessor, kept only as a reference point.
V40_PLAIN = str(plain_image_path("_v40_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- change 1: governor slew steps -------------------------------------------------------------
# The LKAS-LANE-ONLY per-cycle rate limiter, in FUN_00026c80 (writes gp-0x6b4c, the LKAS lane the
# aggregator reads at 0x3AA3E). Single reader image-wide at 0x27622. Its function body consumes NO
# driver-torque variable -- this is the one slew limit that is genuinely LKAS-specific.
LKAS_STEP = 0xC6194          # tp+0x7194
LKAS_STEP_STOCK = 3
LKAS_STEP_NEW = 0xFFFF       # target is bounded to 2048/3072, so the step can never bind again

# The MERGED-command governor slew steps. DELIBERATELY LEFT STOCK -- see the header.
SLEW_FAST = 0xC6206
SLEW_SLOW = 0xC6208
SLEW_STOCK = (512, 205)

# ---- change 2: motor-rate adaptive cap, bank A, BOTH copies ------------------------------------
CAP_RECORDS = (0xC520C, 0xC5224)     # 24-byte records: count, X[5], Y[5], terminator
CAP_X_OFFSET, CAP_Y_OFFSET = 2, 12
CAP_SLOPES = (0xC5030, 0xC5038)      # s16 x 4, Q13
CAP_SHIFT = 0xC5160                  # tp+0x6160 = 13, left stock
CAP_COUNT = 5
CAP_X_STOCK = (1050, 1700, 2500, 3700, 4100)
CAP_Y_STOCK = (5325, 3584, 2406, 1587, 512)
CAP_SLOPES_STOCK = (-21940, -12059, -5593, -22021)
CAP_Y_NEW = (5325,) * CAP_COUNT      # flat at the table's own maximum
CAP_SLOPES_NEW = (0, 0, 0, 0)        # required: a flat Y with live slopes still interpolates

# banks B and C: byte-identical replicas, unreachable from app tp. Asserted UNCHANGED.
CAP_BANK_BC = (0xF9E0C, 0xF9E24, 0xFAA0C, 0xFAA24, 0xF9C30, 0xF9C38, 0xFA830, 0xFA838)

CAL_BLOCK = (0xC6000, 0xC6FFC)       # holds the slew cals
CAP_BLOCK = (0xC5000, 0xC5FFC)       # holds the cap tables -- V40 left this CRC STALE
DIRTY_BLOCKS = (CAP_BLOCK,)          # V41 writes ONLY the cap block; 0xC6000 is untouched
EXPECTED_BLOCKS = 50                 # stored linked list. The BOOTLOADER walks 49 of these,
                                     # skipping 0xC5000 via a REAL, byte-verified bridge.


def full_image(window):
    image = bytearray(b"\xff" * 0x100000)
    image[START:END] = window
    return bytes(image)


def assert_x31_checksum(raw, label):
    stored = struct.unpack_from("<I", raw, len(raw) - 4)[0]
    calculated = sum(raw[:-4]) & 0xFFFFFFFF
    assert calculated == stored, f"{label} x31 checksum: 0x{calculated:08X} != 0x{stored:08X}"


def patched_addresses():
    """Every byte V41 writes that is NOT itself a CRC trailer."""
    addresses = set()
    for record in CAP_RECORDS:
        addresses.update(range(record + CAP_Y_OFFSET, record + CAP_Y_OFFSET + 2 * CAP_COUNT))
    for slopes in CAP_SLOPES:
        addresses.update(range(slopes, slopes + 8))
    return addresses


def crc_block_map(code):
    """Follow the block linked list EXACTLY as stored. No bridge -- see this file's header."""
    start_page, num_pages = struct.unpack_from("<HH", code, END - 8)
    block_start, block_length = start_page << 12, (num_pages << 12) - 4
    blocks, visited = [], set()
    while True:
        assert block_start not in visited, f"CRC chain loop at 0x{block_start:X}"
        visited.add(block_start)
        assert block_start >= 8 and block_length >= 0, "invalid block geometry"
        trailer = block_start + block_length
        assert trailer + 4 <= len(code), f"block 0x{block_start:X} out of bounds"
        blocks.append((block_start, trailer))
        if block_start == START:
            break
        next_page, next_num_pages = struct.unpack_from("<HH", code, block_start - 8)
        next_start = next_page << 12
        assert next_start != block_start, f"CRC chain self-loop at 0x{block_start:X}"
        block_start, block_length = next_start, (next_num_pages << 12) - 4
        assert len(blocks) <= 200, "runaway CRC chain"
    return blocks


def assert_crc_chain(code, label):
    """Every block in the true 50-block chain must verify."""
    blocks = crc_block_map(code)
    for block_start, trailer in blocks:
        calculated = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        stored = struct.unpack_from("<I", code, trailer)[0]
        assert calculated == stored, \
            f"{label}: CRC mismatch block 0x{block_start:X}: 0x{calculated:08X} != 0x{stored:08X}"
    assert len(blocks) == EXPECTED_BLOCKS, \
        f"{label}: expected {EXPECTED_BLOCKS} CRC blocks, traversed {len(blocks)}"
    covered = {(s, e) for s, e in blocks}
    assert CAP_BLOCK in covered, \
        f"{label}: {CAP_BLOCK} absent from the chain -- the V40 'gap' belief has returned"
    assert CAL_BLOCK in covered, f"{label}: {CAL_BLOCK} absent from the chain"
    return len(blocks)


def assert_every_write_is_crc_covered(code, addresses):
    """The INVERSE of V40's assert_crc_gap_is_real().

    V40 asserted its cap-table writes were UNCOVERED, re-deriving that from the same bridged walk
    that created the false belief -- so the assertion agreed with the bug and the build shipped.
    V41 asserts the opposite and treats an uncovered write as fatal: every byte we touch must live
    inside a block whose CRC we then recompute.
    """
    covered = crc_block_map(code)
    dirty = set()
    for address in addresses:
        inside = [(s, e) for s, e in covered if s <= address < e]
        assert len(inside) == 1, \
            f"0x{address:05X} is in {len(inside)} CRC blocks ({inside}); refusing to emit"
        dirty.add(inside[0])
    assert dirty == set(DIRTY_BLOCKS), \
        f"writes dirty {sorted(dirty)} but DIRTY_BLOCKS declares {sorted(DIRTY_BLOCKS)}"
    for block in sorted(dirty):
        which = "cap tables" if block == CAP_BLOCK else "slew cals"
        print(f"  CRC coverage: {which} lie inside [0x{block[0]:X},0x{block[1]:X}) "
              f"-> CRC @0x{block[1]:X} WILL be recomputed")


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    digest = hashlib.sha256(code).hexdigest()
    assert digest == V38_SHA256, f"unexpected V38 baseline SHA-256: {digest}"

    # V38 lineage: 4x reach, V37 fault guards, matched walls, all reachable setpoint records.
    assert struct.unpack_from("<H", code, 0xC646C)[0] == 3564
    assert struct.unpack_from("<H", code, 0xC61B4)[0] == 2048
    assert struct.unpack_from("<H", code, 0xC61B2)[0] == 2048
    assert struct.unpack_from("<H", code, 0xC6312)[0] == 320, "strong-driver threshold moved"
    assert all(code[a] == 0xFF for a in (0xC64B4, 0xC64B5, 0xC64B6, 0xC64B7, 0xC64B8))
    assert all(struct.unpack_from("<H", code, a)[0] == 0xFFFF for a in (0xC61C0, 0xC61C2, 0xC61C4))
    assert all(struct.unpack_from("<h", code, a)[0] == v for a, v in (
        (0xC674E, 5120), (0xC6750, 5120), (0xC675A, -5120), (0xC675C, -5120),
        (0xC6768, 5120), (0xC676A, 5120), (0xC676C, 5120)))
    assert all(struct.unpack_from("<f", code, a)[0] == v for a, v in (
        (0xC6598, 5.0), (0xC659C, 5.0), (0xC65AC, -5.0), (0xC65B0, -5.0),
        (0xC65C4, 5.0), (0xC65C8, 5.0), (0xC65CC, 5.0)))
    for record in (0xE4180, 0xE41A8, 0xE41F8, 0xE4220, 0xE5180, 0xE51A8, 0xE51D0, 0xE51F8):
        assert struct.unpack_from("<9H", code, record + 0x14) == (16384,) * 9

    # V39's cave and hook must be ABSENT -- V40 baselines on V38, not V39.
    assert bytes(code[0x3AC78:0x3AC7C]) == bytes.fromhex("24 4f 30 94"), \
        "hook site is not stock: this looks like a V39 image, not V38"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V38"

    # gp-0x67ac reduced-mode reachability guard: no source-mode entry may be 2, 3 or 4.
    modes = tuple(code[0xC4124:0xC412F])
    assert modes == (0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0), f"A160 source modes changed: {modes}"
    assert not (set(modes) & {2, 3, 4}), "reduced aggregator mode became reachable; re-audit"

    # Change targets are at their exact stock values, in every copy.
    assert struct.unpack_from("<H", code, LKAS_STEP)[0] == LKAS_STEP_STOCK, "LKAS step not stock"
    assert struct.unpack_from("<H", code, SLEW_FAST)[0] == SLEW_STOCK[0]
    assert struct.unpack_from("<H", code, SLEW_SLOW)[0] == SLEW_STOCK[1]
    assert struct.unpack_from("<H", code, 0xC6192)[0] == 2048, "LKAS steady bound moved"
    assert struct.unpack_from("<H", code, 0xC6198)[0] == 3072, "LKAS transition bound moved"
    assert struct.unpack_from("<H", code, CAP_SHIFT)[0] == 13
    assert struct.unpack_from("<H", code, 0xC6202)[0] == 4762, "governor nominal moved"
    for record in CAP_RECORDS:
        assert struct.unpack_from("<H", code, record)[0] == CAP_COUNT
        assert struct.unpack_from("<5h", code, record + CAP_X_OFFSET) == CAP_X_STOCK
        assert struct.unpack_from("<5h", code, record + CAP_Y_OFFSET) == CAP_Y_STOCK
    for slopes in CAP_SLOPES:
        assert struct.unpack_from("<4h", code, slopes) == CAP_SLOPES_STOCK
    assert bytes(code[CAP_RECORDS[0]:CAP_RECORDS[0] + 24]) == \
        bytes(code[CAP_RECORDS[1]:CAP_RECORDS[1] + 24]), "bank-A record copies already diverge"
    assert bytes(code[CAP_SLOPES[0]:CAP_SLOPES[0] + 8]) == \
        bytes(code[CAP_SLOPES[1]:CAP_SLOPES[1] + 8]), "bank-A slope copies already diverge"

    assert_every_write_is_crc_covered(code, patched_addresses())
    assert_crc_chain(code, "V38 baseline")
    assert walk(bytes(code), label="V38 baseline") == 0
    assert walk_all_blocks(bytes(code), label="V38 baseline") == 0


def patch_u16(code, address, old, new, note):
    got = struct.unpack_from("<H", code, address)[0]
    assert got == old, f"0x{address:05X}: expected {old} got {got} ({note})"
    struct.pack_into("<H", code, address, new)
    print(f"  0x{address:05X}: {old:6} -> {new:6}  {note}")


def patch_s16_array(code, address, old, new, note):
    got = struct.unpack_from(f"<{len(old)}h", code, address)
    assert got == tuple(old), f"0x{address:05X}: expected {tuple(old)} got {got} ({note})"
    struct.pack_into(f"<{len(new)}h", code, address, *new)
    print(f"  0x{address:05X}: {list(old)} -> {list(new)}  {note}")


def changed_runs(before, after):
    diffs = [i for i in range(START, END) if before[i] != after[i]]
    runs = []
    for address in diffs:
        if runs and address == runs[-1][1] + 1:
            runs[-1][1] = address
        else:
            runs.append([address, address])
    return diffs, runs


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)

    source_rwd = open(V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V38_RWD_SHA256
    assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["key"] == list(V9B["keys"])
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    assert decode is not None
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)

    print("  change 1 -- WITHDRAWN. 0xC6194 is ARCHITECTURALLY INERT and is left STOCK at 3.")
    print("    VERIFIED at instruction level: 0x276c2 `ld.hu 0x73CC,tp,r8` reads cal 0xC63CC, whose")
    print("    bytes are 00 00 -> the gain is EXACTLY ZERO. It multiplies the entire term carrying")
    print("    the rate-limited state gp-0x3d6c, so (state * 0) >> 10 == 0 and gp-0x6b4c reduces to")
    print("    gp-0x3d88 alone -- an unlimited per-mode passthrough with no persisted state.")
    print("    gp-0x3d6c / gp-0x3d84 / gp-0x3d88 have 2 sites each, ALL inside FUN_00026c80 (swept),")
    print("    so there is no other consumer either. The LKAS lane already reaches the aggregator")
    print("    UNFILTERED: there is no LKAS-specific slew limit left to remove.")
    assert struct.unpack_from("<H", code, LKAS_STEP)[0] == LKAS_STEP_STOCK, "0xC6194 must stay stock"
    # The MERGED-command governor is NOT touched. 0xC6206/0xC6208 slew-limit gp-0x6b94, the
    # aggregator output (LKAS + BASE ASSIST). V40 raised them to 65535 and that build bricked the
    # rack at ignition. Base assist is not commanded or monitored by the comma, so the "openpilot
    # already rate-limits its request" rationale does not cover them.
    assert struct.unpack_from("<H", code, SLEW_FAST)[0] == 512, "merged governor fast step MOVED"
    assert struct.unpack_from("<H", code, SLEW_SLOW)[0] == 205, "merged governor slow step MOVED"

    print("  change 2 -- motor-rate adaptive cap flattened, bank A, both copies:")
    for record in CAP_RECORDS:
        patch_s16_array(code, record + CAP_Y_OFFSET, CAP_Y_STOCK, CAP_Y_NEW,
                        f"cap Y row @0x{record:05X}+{CAP_Y_OFFSET}")
    for slopes in CAP_SLOPES:
        patch_s16_array(code, slopes, CAP_SLOPES_STOCK, CAP_SLOPES_NEW,
                        "Q13 slopes -> 0 (a flat Y with live slopes still interpolates)")

    # Both bank-A copies must remain byte-identical to each other.
    assert bytes(code[CAP_RECORDS[0]:CAP_RECORDS[0] + 24]) == \
        bytes(code[CAP_RECORDS[1]:CAP_RECORDS[1] + 24]), "bank-A record copies diverged"
    assert bytes(code[CAP_SLOPES[0]:CAP_SLOPES[0] + 8]) == \
        bytes(code[CAP_SLOPES[1]:CAP_SLOPES[1] + 8]), "bank-A slope copies diverged"
    # Count, X breakpoints, terminator and the shift cal are untouched.
    for record in CAP_RECORDS:
        assert struct.unpack_from("<H", code, record)[0] == CAP_COUNT
        assert struct.unpack_from("<5h", code, record + CAP_X_OFFSET) == CAP_X_STOCK
        assert struct.unpack_from("<H", code, record + 22)[0] == 0, "record terminator moved"
    assert struct.unpack_from("<H", code, CAP_SHIFT)[0] == 13
    assert struct.unpack_from("<H", code, 0xC6202)[0] == 4762, "governor nominal must stay stock"
    # Banks B and C are left strictly alone.
    for address in CAP_BANK_BC:
        assert bytes(code[address:address + 24]) == bytes(baseline[address:address + 24]), \
            f"bank B/C replica @0x{address:05X} was modified"
    assert bytes(code[0xF9000:0x100000]) == bytes(baseline[0xF9000:0x100000]), \
        "block [0xF9000,0xFCFFC) must remain byte-identical"

    # Recompute EVERY dirtied block, ascending. V40 recomputed only 0xC6FFC and shipped a stale
    # 0xC5FFC -- that single omission is what disabled steering at ignition.
    assert_every_write_is_crc_covered(code, patched_addresses())
    for block_start, trailer in sorted(DIRTY_BLOCKS):
        old_crc = struct.unpack_from("<I", code, trailer)[0]
        new_crc = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        struct.pack_into("<I", code, trailer, new_crc)
        note = "  <-- the CRC V40 owed and never wrote" if (block_start, trailer) == CAP_BLOCK else ""
        print(f"  CRC [0x{block_start:X},0x{trailer:X}) @0x{trailer:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}{note}")

    allowed = set(patched_addresses())
    for _, trailer in DIRTY_BLOCKS:
        allowed.update(range(trailer, trailer + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V41-vs-V38 bytes: {sorted(set(diffs) - allowed)}"

    # No code was touched: the whole application range must be byte-identical to V38.
    assert bytes(code[START:0xBF000]) == bytes(baseline[START:0xBF000]), "APPLICATION CODE EDIT"
    assert bytes(code[0xC4FFC:0xC5000]) == bytes(baseline[0xC4FFC:0xC5000]), "main trailer moved"

    assert_crc_chain(code, "V41 plain")
    assert walk(bytes(code), label="V41") == 0
    assert walk_all_blocks(bytes(code), label="V41") == 0

    # ---- the load-bearing claims of this build ---------------------------------------------
    assert struct.unpack_from("<H", code, LKAS_STEP)[0] == LKAS_STEP_STOCK
    assert struct.unpack_from("<H", code, SLEW_FAST)[0] == 512, "merged governor must stay stock"
    assert struct.unpack_from("<H", code, SLEW_SLOW)[0] == 205, "merged governor must stay stock"
    for record in CAP_RECORDS:
        assert struct.unpack_from("<5h", code, record + CAP_Y_OFFSET) == CAP_Y_NEW
        assert struct.unpack_from("<5h", code, record + CAP_X_OFFSET) == CAP_X_STOCK, "cap X moved"
    for slopes in CAP_SLOPES:
        assert struct.unpack_from("<4h", code, slopes) == CAP_SLOPES_NEW
    print("  merged-command governor 0xC6206/0xC6208 verified STOCK at 512/205")

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V41 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V41 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V41 RWD readback")
    assert walk(readback, label="V41 RWD readback") == 0
    assert walk_all_blocks(readback, label="V41 RWD readback") == 0
    for record in CAP_RECORDS:
        assert struct.unpack_from("<5h", decoded, record - START + CAP_Y_OFFSET) == CAP_Y_NEW
    for slopes in CAP_SLOPES:
        assert struct.unpack_from("<4h", decoded, slopes - START) == CAP_SLOPES_NEW
    assert struct.unpack_from("<H", decoded, LKAS_STEP - START)[0] == LKAS_STEP_STOCK
    assert struct.unpack_from("<H", decoded, SLEW_FAST - START)[0] == 512
    assert struct.unpack_from("<H", decoded, SLEW_SLOW - START)[0] == 205

    print(f"  V41-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)")
    print(f"  V38 SHA-256: {V38_SHA256}")
    print(f"  V41 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V41 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V41-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V41_OUT)]
    for path in stale + [V41_OUT, BIN_OUT, V41_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V41 = V40's exact functional content + the CRC that V40 owed block [0xC5000,0xC5FFC)")
    print("      ROOT CAUSE of V40's ignition EPS lamp: the kit's CRC walker hard-coded a bogus")
    print("      'bridge' at 0xC6000 that skipped the 0xC5000 block, so V40 wrote the cap tables")
    print("      into a CRC-protected block and never recomputed its CRC. The chain is 50 blocks.")
    print("      CAL-ONLY: zero code edits, zero caves, V39's guard dropped entirely")
    print("      slew  0xC6206/0xC6208 -> 0xFFFF   (vibration fix -- PRESERVED from V40)")
    print("      cap   bank A both copies -> flat Y 5325, Q13 slopes 0  (ratchet fix -- PRESERVED)")
    print("      governor nominal 0xC6202=4762 and banks B/C remain byte-identical\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V41_OUT), exist_ok=True)
    with open(V41_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V41_OUT + ".tmp", V41_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V41_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
