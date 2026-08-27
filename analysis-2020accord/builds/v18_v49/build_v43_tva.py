"""
builds/v18_v49/build_v43_tva.py -- V43 = V38 + the KEPT state-4 ratchet fix + a NEW vibration fix.

=======================================================================================================
V43 IN ONE LINE
    Keep V42's Change 1 (the verified ratchet fix). REVERT V42's Change 2 (r26, falsified on-car).
    Add ONE calibration halfword that restores a DISABLED first-order pole on a derivative branch.

WHAT THE V42 DRIVE ESTABLISHED
    Change 1 (0x454FE bne->br, the state-4 governor substitution) FIXED THE HARD-TURN RATCHET on-car.
    That mechanism is now a CONFIRMED root cause, not a hypothesis. It is carried into V43 unchanged.

    Change 2 (zeroing the r26 adaptive torque-rate gain surface) DID NOTHING. r26 is FALSIFIED.
    Combined with V39's r24 result, the ENTIRE Sensor-B torque-rate derivative family is eliminated --
    a family-level negative neither build could deliver alone. V43 RESTORES the r26 surface to stock:
    zeroing it bought nothing, and stock is the better default for a term we no longer suspect.

THE REMAINING SYMPTOM, AND THE THREE CONSTRAINTS IT IMPOSES
    A tens-of-Hz vibration when LKAS ALONE turns the wheel; it VANISHES when the driver adds hand
    torque; speed-independent; present since V38.
      C1 the LKAS lane is a ~1-5 Hz LOW-PASS (arbitration IIR gp-0x3d3c, pole 0.96875), so a
         tens-of-Hz component CANNOT be commanded down it -- the source must be elsewhere.
      C2 downstream of the gain, V38 replays stock's exact counts for the same physical torque
         (openpilot's PID was quartered), so a downstream digital limit cannot newly bind.
      C3 something must differ between hands-off and hands-on.

THE MECHANISM -- two independent traces converged on it
    gp-0x4f60 (RAW Sensor-B column torque, a PHYSICAL sensor)
      -> FUN_0003a382 computes errorterm = clamp(gp-0x4f60 - clamp(gp-0x6ad6, +/-8192), +/-0x2800),
         where gp-0x6ad6 is a FEEDFORWARD MODEL of expected column torque, so errorterm is a
         MODEL-vs-REALITY RESIDUAL
      -> Stage C takes a RAW ONE-SAMPLE DIFFERENCE of that residual (gp-0x3684 is a pure delay
         register, rewritten unconditionally every cycle @0x3a840) -- i.e. a DERIVATIVE, a HIGH-PASS
      -> gp-0x6ad4 -> aggregator gp-0x6b94 -> which IS the governor's slew target (verified:
         FUN_0004503c's first instruction @0x453e0 is `ld.h -0x6b94[gp],r6`)

    HOW IT BEATS C2 -- the loophole that matters. The gain-rescaling invariance argument is about
    DIGITAL replay of counts. It says nothing about a term sourced from a PHYSICAL SENSOR reacting to
    REAL DELIVERED TORQUE. Motor torque ripple scales with delivered torque (standard PMSM behaviour);
    V38 delivers ~4x the torque, so the REAL ripple on gp-0x4f60 is ~4x larger, and this lane passes it
    essentially unattenuated. Nothing digital compensated, because the amplification happened in the
    PLANT. [INFERRED, physical -- the one link disassembly cannot close, and the weakest in the chain.]

    WHY NO PRIOR BUILD MOVED IT. V39 (r24), V41 (cap table) and V42 (r26) touch NONE of FUN_0003a382,
    gp-0x6ad4, gp-0x6ad6, 0xC6450, 0xC644A or the L1/L2/L3 tables. Same physical input family as
    r24/r26 -- Sensor-B torque -- via a completely independent, never-tested computational path. That
    is why falsifying two of the three routes never falsified the family.

THE CORRECTION THAT UNLOCKED IT
    The golden model recorded this lane's two lag stages as gain 4 (tau ~256 cycles, "VERY heavily
    damped ... argues against this lane resonating"). THEY ARE 1024. Two agents independently byte-read
    cals 0xC6450 and 0xC644A in stock, V38 and V42: all give 1024 = Q10 UNITY. At unity the EMA update
    `state += ((target*32 - state) * GAIN) >> 10` reduces to `state = target*32` exactly -- a DIRECT
    ASSIGNMENT, not a lag. The lane is UNFILTERED, and the recorded "heavily damped" verdict had been
    actively steering the investigation away from it.

THE EDIT -- ADD A POLE, DO NOT REMOVE A TERM
    A raw one-sample difference is an UNBOUNDED DIFFERENTIATOR. Every real controller band-limits one
    with a first-order lag: the standard "dirty derivative". Cal 0xC644A IS that lag's gain, sitting
    immediately downstream of the raw difference -- and it is calibrated to unity, i.e. SWITCHED OFF.
    Lowering it restores the pole.

    *** THIS IS SIGN-AGNOSTIC, WHICH IS WHY IT IS THE RIGHT EDIT. *** The sign of Stage C could NOT be
    settled from the bytes (it resolves only through gp-0x6752's static value AND a physical wiring
    convention -- the same irreducible gap already on record for r24/r26). Zeroing the term would
    therefore be a gamble: a residual-feedback derivative is CLASSICALLY an active damper, and this kit
    has ALREADY removed derivative feedback twice (V39, V42) while chasing this vibration. Band-limiting
    does not care: damping or anti-damping, it preserves the low-frequency action and removes only the
    tens-of-Hz content.

    An EMA's DC gain is unity IN REAL ARITHMETIC -- state = target*32 is the fixed point for any nonzero
    gain -- so GAIN sets only a settling time. In the ACTUAL integer arithmetic this is not exact: V850
    `sar` floors toward -infinity, so approaching the target from ABOVE converges exactly while
    approaching from BELOW can stall within (target - 1024/GAIN, target]. The residual is real but
    BOUNDED and ONE-SIDED (it under-reports a sustained RISING derivative, never over-reports):

        max residual ~= 32 / GAIN counts at the output    GAIN=64 -> <=0.5 counts

    Sub-count at the chosen value. Verified two ways that agree: direct integer simulation (15 state-
    counts measured) and the analytic bound (1024/GAIN = 16 state-counts). Below roughly GAIN=16-32 the
    residual stops being negligible -- that is the practical floor on this lever.

    *** GAIN = 0 IS DEGENERATE -- the state freezes and never converges. It is NOT "just slower".
    Never round a candidate down to zero. ***

WHY NOT THE OTHER TWO CANDIDATES THIS SESSION PRODUCED
    Governor slew-STEP selector (cal 0xC6206 512->205). REAL and verified: the governor's per-cycle
    slew step is switched by DRIVER TORQUE (gp-0x67f5, vote of gp-0x6a5e vs cal 0xC531E=1062, debounced
    10 cyc), giving 2.5x less damping hands-off -- the right direction for C3. Held in reserve because
    it touches the MAIN torque command path (the same cal V40 catastrophically mis-set), attenuates
    only ~2.5x, and slows LKAS response. The pole has a strictly smaller blast radius: a side lane with
    two touches image-wide, no monitors, no lockstep, and zero steady-state change.

    The one-sided `ld.hu` gate at 0x345fa (which makes the gp-0x6bd0 damping term unconditionally ZERO
    for one rotation direction -- a genuine, newly-found firmware asymmetry). NOT shipped: correcting it
    would make a term active in a direction where it has NEVER been active in ANY build including stock.
    This kit's rule -- the one that made V42's branch flip safe -- is WIDEN AN ALREADY-LIVE PATH, DO NOT
    INVENT ONE. Recorded for a later, separately-scored build.

ONE VIBRATION CHANGE ONLY. V42 got away with two changes because they hit DIFFERENT symptoms. Two
changes aimed at the SAME symptom would be unattributable, which is the lesson V42 itself taught.

CONFIDENCE. Change 1 is a CONFIRMED root cause (on-car). Change 2 is a WELL-FOUNDED HYPOTHESIS: the
mechanism is verified, the edit's safety is verified, but "this lane is the vibration" is inferred and
rests on a physical-ripple link disassembly cannot close. A null falsifies the lane without implicating
Change 1 -- and would promote the governor STEP selector to the V44 candidate.
=======================================================================================================
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
    raise RuntimeError("V43 builder requires assertions; do not run with python -O")

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

V43_TAG = "LKAS-4x-V38base-state4-ratchet-off-derivative-pole32"
V43_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V43-{V43_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v43_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CHANGE 1 (KEPT FROM V42): the state-4 governor ratchet ------------------------------------
# 0x454fe: `bne 0x455c4` -> `br 0x455c4`. V850 Bcond format III is one halfword:
#     bits[15:11] = disp[8:4] | bits[10:7] = 0b1011 (Bcond) | bits[6:4] = disp[3:1] | bits[3:0] = cond
# cond 0b1010 = BNE/BNZ, cond 0b0101 = BR (always). Only the low nibble moves, so the DISPLACEMENT
# and therefore the BRANCH TARGET are provably unchanged -- asserted below by decoding both.
# *** THIS FIX IS CONFIRMED ON-CAR (V42 drive). It is not under test in V43. ***
EDIT_ADDR = 0x454FE
EDIT_STOCK_HW = 0x65BA          # bne  +198 -> 0x455c4
EDIT_NEW_HW = 0x65B5            # br   +198 -> 0x455c4
COND_BNE, COND_BR = 0xA, 0x5

CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))    # ld.bu -0x67fa[gp],r12
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))        # cmp 0x4,r12
SUBST_BLOCK = (0x45500, 0x455C4)                       # the block the edit makes unreachable

# ---- CHANGE 2 (NEW): restore the dirty-derivative pole ------------------------------------------
# cal 0xC644A (tp+0x744a), read @0x3a860 `ld.hu 0x744a[tp],r11`, consumed @0x3a86c.
# It is the EMA gain on state gp-0x3680, whose target is
#     D_RAW = clamp(FACTOR_D * (TARGET_RAW - gp-0x3684_prev) >> 10, +/-0x2800)
# and gp-0x3684 is a PURE ONE-SAMPLE DELAY (`0x3a840 st.w r14,-0x3684[gp]`, unconditional, unfiltered).
# So 0xC644A is the pole immediately downstream of a raw discrete difference: the dirty-derivative
# pole, currently pinned at Q10 unity == DISABLED.
#
# alpha = 64/1024 = 0.0625  ->  tau ~= 15.5 cycles  ->  corner ~= 0.00995 cycles^-1
# (~10 Hz IF the tick is 1 kHz -- the tick rate is INFERRED and has never been proven for this
#  function's call rate, so the CYCLE-domain figure is the one this edit is landed against).
POLE_ADDR = 0xC644A
POLE_STOCK = 1024
# *** VALUE SET FROM MEASURED ON-CAR DATA (route b9, V38, 2026-07-20). ***
# The vibration is a SHARP, ISOLATED SPECTRAL PEAK AT 21.02 Hz in hands-off column torque
# (41 segments, 209 s; top five FFT bins all within 21.00-21.09 Hz). An earlier draft of this
# builder used 64, chosen when the symptom band was ASSUMED to be 30-50 Hz. That assumption is
# now falsified by data, so the constant is corrected:
#     GAIN=128 -> only 1.41x (-3.0 dB) at 21 Hz   -- too timid
#     GAIN= 64 -> 2.28x (-7.1 dB)                 -- the old value, calibrated to a wrong band
#     GAIN= 32 -> 4.28x (-12.6 dB) at 21 Hz, and only -1.31 dB at 3 Hz   <-- CHOSEN
#     GAIN= 16 -> 8.44x but -3.86 dB at 3 Hz and a 2-count DC residual   -- too much
# The 3 Hz cost is smaller than it looks: it applies to STAGE C's own contribution only, one
# sub-term of one lane among several. The LKAS command lane itself is untouched.
POLE_NEW = 32                    # 64 is the conservative fallback (2.28x at 21 Hz)
# The SIBLING pole on the PROPORTIONAL branch (state gp-0x367c, read @0x3a7f0). Deliberately NOT
# touched -- Stage A is not a derivative and does not need band-limiting.
POLE_SIBLING_ADDR = 0xC6450
POLE_SIBLING_STOCK = 1024

CAL_BLOCK = (0xC6000, 0xC6FFC)   # holds the pole edit; CRC @0xC6FFC

# ---- REVERTED FROM V42: the r26 adaptive torque-rate gain surface -------------------------------
# V42 zeroed all four Y rows plus two override cals. That was falsified on-car, so V43 asserts every
# one of them is back at its STOCK value. This is an explicit check that Change 2 of V42 is BACKED OUT,
# not merely "not re-applied".
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)   # u16 count, s16 X[4], s16 Y[4], u16 pad
RATE_A_X_OFFSET, RATE_A_Y_OFFSET = 2, 0xA
RATE_A_COUNT = 4
RATE_A_X_STOCK = ((0, 400, 1600, 3000), (0, 250, 1200, 3000),
                  (0, 400, 1250, 3000), (0, 400, 1250, 3000))
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))
R26_OVERRIDES = ((0xC6444, 512, "tp+0x7444, taken when gp-0x683c != 0"),
                 (0xC643E, 1536, "tp+0x743e, taken when assist_state >= cal 0xC64FA"))
R24_CALS = ((0xC6440, 2048), (0xC6442, 1024), (0xC6446, 512), (0xC61F6, 3))

# Cal cells that MUST remain stock.
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38)"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal"),
    0xC6206: (512, "governor slew step, fast -- the V44 candidate, deliberately NOT touched here"),
    0xC6208: (205, "governor slew step, slow"),
    0xC6134: (1000, "substitution scale (shared with FUN_00041464)"),
    0xC648E: (0, "substitution bias (signed; shared)"),
    0xC64A3: (1, "pre-gain deadband enable -- deliberately LEFT ON"),
    0xC61B8: (102, "pre-gain deadband threshold -- deliberately LEFT STOCK"),
    0xC6194: (3, "dead LKAS rate limiter"),
    0xC6450: (1024, "FUN_0003a382 PROPORTIONAL-branch pole -- deliberately LEFT AT UNITY"),
    0xC643C: (37, "gp-0x6abe resolver-rate filter gain (damping term producer)"),
}

# FUN_0003a382's four LERP gain tables. All asserted STOCK -- the pole edit must be the only change
# inside this lane, so that a null result falsifies the POLE and not some second simultaneous edit.
FUN3A382_TABLES = {
    0xC6B26: ((256, 256, 225, 153), "L1 Stage-A gain Y row"),
    0xC6B12: ((98, 98, 98, 98), "L2 Stage-B accumulator gain Y row"),
    0xC6AE6: ((2048, 2048, 2048, 2048), "L3 Stage-C DERIVATIVE gain Y row -- NOT zeroed, see header"),
}

EXPECTED_BLOCKS = 50


def full_image(window):
    image = bytearray(b"\xff" * 0x100000)
    image[START:END] = window
    return bytes(image)


def assert_x31_checksum(raw, label):
    stored = struct.unpack_from("<I", raw, len(raw) - 4)[0]
    calculated = sum(raw[:-4]) & 0xFFFFFFFF
    assert calculated == stored, f"{label} x31 checksum: 0x{calculated:08X} != 0x{stored:08X}"


def decode_bcond(code, address):
    """Decode a V850 format-III Bcond. Returns (cond, target) or None."""
    halfword = struct.unpack_from("<H", code, address)[0]
    if (halfword & 0x0780) != 0x0580:
        return None
    cond = halfword & 0xF
    disp = ((halfword >> 11) & 0x1F) << 4 | ((halfword >> 4) & 0x7) << 1
    if disp & 0x100:
        disp -= 0x200
    return cond, address + disp


def crc_block_map(code):
    """Follow the block linked list EXACTLY as stored (all 50 blocks, no bridge)."""
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
    blocks = crc_block_map(code)
    for block_start, trailer in blocks:
        calculated = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        stored = struct.unpack_from("<I", code, trailer)[0]
        assert calculated == stored, \
            f"{label}: CRC mismatch block 0x{block_start:X}: 0x{calculated:08X} != 0x{stored:08X}"
    assert len(blocks) == EXPECTED_BLOCKS, \
        f"{label}: expected {EXPECTED_BLOCKS} CRC blocks, traversed {len(blocks)}"
    return len(blocks)


def owning_block(code, address):
    inside = [(s, e) for s, e in crc_block_map(code) if s <= address < e]
    assert len(inside) == 1, f"0x{address:05X} lies in {len(inside)} CRC blocks ({inside})"
    return inside[0]


def changed_runs(before, after):
    diffs = [i for i in range(START, END) if before[i] != after[i]]
    runs = []
    for address in diffs:
        if runs and address == runs[-1][1] + 1:
            runs[-1][1] = address
        else:
            runs.append([address, address])
    return diffs, runs


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V38"
    for address, (value, note) in STOCK_CALS.items():
        if address == 0xC64A3:
            got = code[address]
        else:
            got = struct.unpack_from("<h" if address == 0xC648E else "<H", code, address)[0]
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"

    # The pole cell must be at its DISABLED (unity) stock value before we touch it.
    got = struct.unpack_from("<H", code, POLE_ADDR)[0]
    assert got == POLE_STOCK, \
        f"0x{POLE_ADDR:05X}: expected {POLE_STOCK} (Q10 unity, pole disabled) got {got}"
    got = struct.unpack_from("<H", code, POLE_SIBLING_ADDR)[0]
    assert got == POLE_SIBLING_STOCK, f"0x{POLE_SIBLING_ADDR:05X} sibling pole moved"

    # FUN_0003a382's LERP gain tables must all be stock.
    for address, (values, note) in FUN3A382_TABLES.items():
        assert struct.unpack_from("<4h", code, address) == values, f"0x{address:05X} ({note})"

    # *** V42's Change 2 must be BACKED OUT: the r26 surface is asserted STOCK, not zero. ***
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<H", code, base)[0] == RATE_A_COUNT, f"r26 record 0x{base:05X} count"
        assert struct.unpack_from("<4h", code, base + RATE_A_X_OFFSET) == RATE_A_X_STOCK[i], \
            f"r26 record 0x{base:05X} X row moved"
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], \
            f"r26 record 0x{base:05X} Y row is NOT stock -- V42's Change 2 must be reverted in V43"
        assert struct.unpack_from("<H", code, base + 0x12)[0] == 0, f"r26 record 0x{base:05X} pad"
    for address, value, note in R26_OVERRIDES:
        assert struct.unpack_from("<H", code, address)[0] == value, \
            f"0x{address:05X} is not stock ({note}) -- V42's Change 2 must be reverted"
    for address, value in R24_CALS:
        assert struct.unpack_from("<H", code, address)[0] == value, f"r24 cal 0x{address:05X} moved"

    for address, expected in (CTX_LD_STATE, CTX_CMP_FOUR):
        assert bytes(code[address:address + len(expected)]) == expected, \
            f"instruction context at 0x{address:05X} does not match the expected V38 bytes"
    assert struct.unpack_from("<H", code, EDIT_ADDR)[0] == EDIT_STOCK_HW, \
        f"0x{EDIT_ADDR:05X} is not the expected `bne` halfword 0x{EDIT_STOCK_HW:04X}"
    decoded = decode_bcond(code, EDIT_ADDR)
    assert decoded == (COND_BNE, SUBST_BLOCK[1]), \
        f"0x{EDIT_ADDR:05X} decodes as {decoded}, expected (BNE, 0x{SUBST_BLOCK[1]:05X})"


def assert_no_external_entry(code):
    """The substitution block must be reachable ONLY by falling through the edited branch."""
    low, high = SUBST_BLOCK
    for address in range(0x4503C, 0x45700, 2):
        if low <= address < high:
            continue
        decoded = decode_bcond(code, address)
        if decoded and low <= decoded[1] < high:
            raise AssertionError(
                f"external Bcond at 0x{address:05X} enters the substitution block at "
                f"0x{decoded[1]:05X}; the edit would not fully disable it")
        halfword = struct.unpack_from("<H", code, address)[0]
        if (halfword & 0xFFC0) == 0x0780:                      # jr/jarl disp22
            disp = ((halfword & 0x3F) << 16) | struct.unpack_from("<H", code, address + 2)[0]
            if disp & 0x200000:
                disp -= 0x400000
            if low <= address + disp < high:
                raise AssertionError(
                    f"external jr at 0x{address:05X} enters the substitution block")
    print(f"  no external entry into [0x{low:05X},0x{high:05X}) -- reachable only via 0x{EDIT_ADDR:05X}")


def assert_ema_dc_preserved(gain, verbose=True):
    """The load-bearing safety claim, checked in TRUNCATING INTEGER arithmetic, not idealised.

    state_new = state + (((target*32) - state) * GAIN) >> 10     (V850 `sar` == floor division)

    The fixed point is state == target*32 for any nonzero GAIN, so GAIN sets only the settling
    time. Truncation lets the state stall up to (1024/GAIN - 1) short of it in the 32x state
    domain. This asserts that residual is SUB-COUNT once divided by the summing junction's >>5.
    """
    assert gain > 0, "GAIN = 0 is DEGENERATE -- the state freezes and never converges"
    worst = 0
    for target in (1, 7, 100, -100, 1234, -1234, 5000, -5000, 10240, -10240):
        state = 0
        for _ in range(20000):
            nxt = state + ((((target * 32) - state) * gain) >> 10)
            if nxt == state:
                break
            state = nxt
        worst = max(worst, abs(state - target * 32))
    residual_counts = worst / 32.0
    assert worst <= (1024 // gain), \
        f"stall residual {worst} exceeds the predicted bound {1024 // gain}"
    assert residual_counts < 1.0, \
        f"GAIN={gain} leaves a {residual_counts:.3f}-count steady-state offset; DC is NOT preserved"
    if verbose:
        print(f"  DC-preservation @GAIN={gain}: worst stall residual {worst} counts in the 32x state "
              f"domain = {residual_counts:.3f} counts at the output -- SUB-COUNT [verified, integer]")
    return residual_counts


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)
    assert_crc_chain(baseline, "V38 baseline")
    assert walk(bytes(baseline), label="V38 baseline") == 0
    assert walk_all_blocks(bytes(baseline), label="V38 baseline") == 0

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
    assert_no_external_entry(code)

    # ---- CHANGE 1 (KEPT): the state-4 ratchet, confirmed on-car by the V42 drive ------------------
    print("  CHANGE 1 (KEPT FROM V42, CONFIRMED ON-CAR) -- one byte, one condition-code nibble:")
    before_cond, before_target = decode_bcond(code, EDIT_ADDR)
    struct.pack_into("<H", code, EDIT_ADDR, EDIT_NEW_HW)
    after_cond, after_target = decode_bcond(code, EDIT_ADDR)
    print(f"    0x{EDIT_ADDR:05X}: 0x{EDIT_STOCK_HW:04X} -> 0x{EDIT_NEW_HW:04X}   "
          f"(byte 0x{baseline[EDIT_ADDR]:02X} -> 0x{code[EDIT_ADDR]:02X})")
    print(f"    bne 0x{before_target:05X}  ->  br 0x{after_target:05X}   "
          f"cond 0x{before_cond:X} -> 0x{after_cond:X}")
    assert (before_cond, after_cond) == (COND_BNE, COND_BR)
    assert before_target == after_target == SUBST_BLOCK[1], \
        "branch TARGET moved -- the displacement field was disturbed"
    assert code[EDIT_ADDR + 1] == baseline[EDIT_ADDR + 1], "high byte of the branch changed"

    # ---- CHANGE 2 (NEW): restore the dirty-derivative pole ---------------------------------------
    print("  CHANGE 2 (NEW) -- restore the DISABLED pole on FUN_0003a382's derivative branch:")
    assert_ema_dc_preserved(POLE_NEW)
    struct.pack_into("<H", code, POLE_ADDR, POLE_NEW)
    alpha = POLE_NEW / 1024.0
    print(f"    0x{POLE_ADDR:05X}: {POLE_STOCK} -> {POLE_NEW}   "
          f"alpha {POLE_STOCK / 1024.0:.4f} -> {alpha:.4f}, tau 1.0 -> ~{1 / alpha:.1f} cycles")
    print(f"    (Q10 unity == pole DISABLED  ->  first-order lag RESTORED on the raw one-sample "
          f"difference)")
    assert struct.unpack_from("<H", code, POLE_ADDR)[0] == POLE_NEW
    assert struct.unpack_from("<H", code, POLE_SIBLING_ADDR)[0] == POLE_SIBLING_STOCK, \
        "the PROPORTIONAL-branch sibling pole must stay at unity"
    for address, (values, note) in FUN3A382_TABLES.items():
        assert struct.unpack_from("<4h", code, address) == values, \
            f"0x{address:05X} moved ({note}) -- the pole must be the ONLY change in this lane"

    # r26 stays stock (V42's Change 2 reverted); r24 stays stock.
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], \
            "r26 Y row is not stock -- V43 must REVERT V42's Change 2"
        assert struct.unpack_from("<4h", code, base + RATE_A_X_OFFSET) == RATE_A_X_STOCK[i]
    for address, value, note in R26_OVERRIDES:
        assert struct.unpack_from("<H", code, address)[0] == value
    for address, value in R24_CALS:
        assert struct.unpack_from("<H", code, address)[0] == value

    # ---- CRC coverage ----------------------------------------------------------------------------
    dirty = owning_block(code, EDIT_ADDR)
    print(f"  CRC coverage: 0x{EDIT_ADDR:05X} lies inside "
          f"[0x{dirty[0]:X},0x{dirty[1]:X}) -> CRC @0x{dirty[1]:X} WILL be recomputed")
    cal_dirty = owning_block(code, POLE_ADDR)
    assert cal_dirty == CAL_BLOCK, f"pole edit lands in {cal_dirty}, expected {CAL_BLOCK}"
    print(f"  CRC coverage: 0x{POLE_ADDR:05X} lies inside "
          f"[0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X}) -> CRC @0x{CAL_BLOCK[1]:X} WILL be recomputed")

    for block in sorted({dirty, cal_dirty}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff --------------------------------------------------------------------------------
    allowed = {EDIT_ADDR, POLE_ADDR, POLE_ADDR + 1}
    for block in {dirty, cal_dirty}:
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V43-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # 1 code byte + 2 pole bytes (0x0400 -> 0x0040 moves BOTH) + two 4-byte CRC trailers.
    assert len(diffs) == 11, f"expected exactly 11 changed bytes, got {len(diffs)}"

    # Everything else byte-identical to V38.
    assert bytes(code[0xBF000:0xC4FFC]) == bytes(baseline[0xBF000:0xC4FFC]), "CAL EDIT in 0xBF000-0xC4FFC"
    assert bytes(code[0xC5000:0xC6000]) == bytes(baseline[0xC5000:0xC6000]), "cap tables moved"
    cal_diffs = {i for i in range(0xC6000, 0xC7000) if code[i] != baseline[i]}
    assert cal_diffs <= allowed, f"unexpected 0xC6000-block bytes: {sorted(cal_diffs - allowed)}"
    assert bytes(code[0xE4000:0xE6000]) == bytes(baseline[0xE4000:0xE6000]), "setpoint records moved"
    assert bytes(code[0xF9000:0x100000]) == bytes(baseline[0xF9000:0x100000]), "banks B/C moved"
    assert bytes(code[START:EDIT_ADDR]) == bytes(baseline[START:EDIT_ADDR]), "code before the edit moved"
    assert bytes(code[EDIT_ADDR + 1:0xBF000]) == bytes(baseline[EDIT_ADDR + 1:0xBF000]), \
        "code after the edit moved"

    assert_crc_chain(code, "V43 plain")
    assert walk(bytes(code), label="V43") == 0
    assert walk_all_blocks(bytes(code), label="V43") == 0
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else \
            struct.unpack_from("<h" if address == 0xC648E else "<H", code, address)[0]
        assert got == value, f"0x{address:05X} moved ({note})"
    print("  all 13 tracked calibrations verified STOCK; r26 surface verified STOCK (V42 Ch2 reverted)")

    # ---- RWD round-trip ----------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V43 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V43 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V43 RWD readback")
    assert walk(readback, label="V43 RWD readback") == 0
    assert walk_all_blocks(readback, label="V43 RWD readback") == 0
    assert struct.unpack_from("<H", decoded, EDIT_ADDR - START)[0] == EDIT_NEW_HW, \
        "Change 1 did not survive the RWD round-trip"
    assert decode_bcond(readback, EDIT_ADDR) == (COND_BR, SUBST_BLOCK[1])
    assert struct.unpack_from("<H", decoded, POLE_ADDR - START)[0] == POLE_NEW, \
        "Change 2 did not survive the RWD round-trip"
    assert struct.unpack_from("<H", decoded, POLE_SIBLING_ADDR - START)[0] == POLE_SIBLING_STOCK
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", decoded, base - START + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], \
            "r26 surface is not stock in the RWD"
    for address, value in R24_CALS:
        assert struct.unpack_from("<H", decoded, address - START)[0] == value, "r24 cal moved in RWD"

    print(f"\n  V43-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == EDIT_ADDR:
            kind = "Change 1: state-4 branch nibble (KEPT, confirmed on-car)"
        elif first == POLE_ADDR:
            kind = "Change 2: dirty-derivative pole 0xC644A"
        elif first in (0xC4FFC, 0xC6FFC):
            kind = "CRC trailer"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256: {V38_SHA256}")
    print(f"  V43 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V43 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V43-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V43_OUT)]
    for path in stale + [V43_OUT, BIN_OUT, V43_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V43 = V38 + the KEPT ratchet fix + a NEW vibration fix. Built on V38, NOT on V42.")
    print("  CHANGE 1 (CODE, 1 byte) -- KEPT FROM V42, a CONFIRMED root cause (V42 drive):")
    print("      0x454FE  bne 0x455C4 -> br 0x455C4   (V850 cond nibble 0xA -> 0x5)")
    print("      Disables the state-4 governor magnitude-suppression substitution. NOT under test.")
    print("  CHANGE 2 (CAL, 1 halfword) -- the VIBRATION, a well-founded HYPOTHESIS:")
    print("      0xC644A  1024 -> 64   restores the DISABLED first-order pole sitting immediately")
    print("      downstream of FUN_0003a382's RAW ONE-SAMPLE DIFFERENCE -- a 'dirty derivative'.")
    print("      That lane is an UNFILTERED model-vs-reality residual on the PHYSICAL Sensor-B torque")
    print("      sensor, and it feeds the aggregator, which IS the governor's slew target.")
    print("      An EMA has UNITY DC GAIN, so this changes NO steady-state value -- only a settling")
    print("      time. That makes it SIGN-AGNOSTIC, which zeroing the term would not be.")
    print("  REVERTED FROM V42: the r26 gain surface is asserted back at STOCK. r26 was falsified")
    print("      on-car, and together with V39's r24 result the whole Sensor-B rate family is out.")
    print("  ONE vibration change only -- two would be unattributable, which is V42's own lesson.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V43_OUT), exist_ok=True)
    with open(V43_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V43_OUT + ".tmp", V43_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V43_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
