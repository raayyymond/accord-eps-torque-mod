"""
builds/v18_v49/build_v42_tva.py -- V42 = V38 + TWO changes: kill the state-4 governor ratchet (1 byte of CODE)
                    and neutralise the r26 adaptive torque-rate lane (18 halfwords of CAL).
=======================================================================================================
Platform: 2020 Honda Accord, EPS 39990-TVA-A160, Renesas V850E2. Baseline: the exact on-car V38 image.

*** THIS IS THE FIRST CODE EDIT THIS KIT HAS SHIPPED SINCE V27, AND THE FIRST EVER THAT IS NOT A
    TRAMPOLINE INTO A CODE CAVE. It changes a single condition-code nibble, in place. ***

-------------------------------------------------------------------------------------------------------
WHAT IT FIXES -- the hard-turn ratchet, root-caused 2026-07-20
-------------------------------------------------------------------------------------------------------
Inside m_motor_torque_governor FUN_0004503c there is a substitution branch that fires while the ECU
state byte gp-0x67fa == 4:

    0x454f8  ld.bu -0x67fa[gp],r12      ; the ECU init/operating/fault state byte
    0x454fc  cmp   0x4,r12
    0x454fe  bne   0x455c4              ; NOT state 4 -> accept the freshly computed value
    ...      |fresh gp-0x6ace| vs |previous gp-0x138a|, ABS + clamped, unsigned `bnh`
             -> substitution runs ONLY when |fresh| > |previous|
    0x455cc  st.h  r6,-0x138a[gp]       ; UNCONDITIONAL writeback of whichever value won

So while state == 4 the delivered torque MAGNITUDE can decrease but can never increase, and because
the suppressed value is written back it becomes the next cycle's baseline -- the suppression is
CUMULATIVE and SELF-SUSTAINING. That is mechanically a ratchet.

State 4 is REACHABLE MID-DRIVE, non-diagnostically, on two paths (0x19bb0: 5->4 when gp-0x68ad == 0;
0x19e54: 10->4). gp-0x68ad is preserved only while gp-0x679d == 1 OR (gp-0x6a5e != 0 AND
gp-0x67f4 == 1) -- i.e. nonzero voted column torque AND the voter plausibility latch converged. A
column-torque zero crossing or a momentary plausibility drop near sensor saturation trips 5->4 on the
next dispatch cycle. Both are exactly what a hard, large-angle turn produces.

WHY IT ONLY SURFACED ON V38: the substitution caps the INCREASE, so what the driver feels is the
shortfall (demanded - held). Stock could demand at most 417 LKAS counts; V38 demands 1782, so the
ratchet is ~4x deeper. The mechanism is old -- V38 made it perceptible.

-------------------------------------------------------------------------------------------------------
WHY THIS HAD TO BE A CODE EDIT (no calibration lever exists -- structural, whole-chain walk)
-------------------------------------------------------------------------------------------------------
  (a) ENTRY: all six functions in the 5->4 / 10->4 / 3->4 chains (FUN_0001a104, FUN_00022016,
      FUN_00022034, FUN_00019d90's normal legs, FUN_000220ba, FUN_00022078) contain ZERO tp+
      calibration reads. Pure runtime flag/state/counter logic.
  (b) SUBSTITUTION VALUE: cals tp+0x7134 (0xC6134 = 1000) and tp+0x748e (0xC648E = 0) are read at
      IDENTICAL displacements in BOTH the primary block (0x454a8-0x454d8) and the substitution block
      (0x45578-0x455aa) -- the same cells, not mirrors -- and ALSO in FUN_00041464 (16 sites for
      0x7134 alone) and FUN_000456a4. Editing either changes >= 3 functions.
  (c) DECISIVE: the branch DECISION reads no cal at all. No cal value can make a result seeded from
      gp-0x138a equal one seeded from the fresh candidate, so even a "pass-through" edit is
      structurally impossible.
  (d) gp-0x679d, the other side of the OR that preserves gp-0x68ad, is likewise cal-free
      (FUN_000567c0 and FUN_0005d9c2 contain zero tp+ reads).

-------------------------------------------------------------------------------------------------------
THE SAFETY CASE -- why this does NOT reproduce the V24/V25/V26/V27 fault mode
-------------------------------------------------------------------------------------------------------
Those four builds hard-faulted from int-vs-float LOCKSTEP DIVERGENCE: an integer path moved and its
independent float twin did not, so a redundancy monitor tripped FUN_00016de6 -> motor off. Four
independent checks say that cannot happen here:

  1. FUN_00043e44 (the float watchdog, same 0xd30 state gate) reads NEITHER gp-0x67fa NOR
     gp-0x6ace / gp-0x138a / gp-0x4cca. Image-wide operand searches for all four displacements
     return zero hits inside its body 0x43e44-0x44a8b. It does not model the state-4 hold at all.
  2. gp-0x6ace's shadow gp-0x4cca is written by the SAME instruction pairs on EVERY path
     (0x454d2/0x454d8, 0x454e0/0x454e6, 0x4559c/0x455a6, 0x455ae/0x455b2), all inside this one
     function. Skipping the substitution cannot desynchronise the pair. gp-0x138a is unshadowed and
     has no reader outside FUN_0004503c.
  3. FUN_0004595a IS a real external monitor on gp-0x6ace -- no debounce, feeds
     FUN_00016de6(0x1d,...) which is hard-fault-eligible. It faults if |gp-0x6ace| overshoots
     |gp-0x6b94| or if their signs oppose. THE EDIT MOVES TOWARD ITS SAFE SIDE:
       * The PRIMARY computation reads gp-0x67fa ZERO times (verified: no -0x67fa displacement
         anywhere in 0x4503c-0x454f8), so the primary value is STATE-INDEPENDENT.
       * gp-0x6ace and its shadow ALREADY HOLD that primary value before the state-4 check runs --
         the substitution merely overwrites them afterwards.
       * Therefore after this edit, state 4 leaves gp-0x6ace holding exactly what states
         3/5/6/8/9/10/11 already produce -- the value FUN_0004595a validates continuously, on every
         drive, back to stock V9.
       * And the monitor's conditions hold by construction on that path: the slew result always lies
         between gp-0x138a and clamp(gp-0x6b94, +/-bound), so |gp-0x6ace| <= |gp-0x6b94| and the
         signs agree, for ANY held value -- including the larger ones this edit permits.
  4. ORDERING (verified): the substitution at 0x454f8 sits AFTER the slew limiter (0x4543a-0x45458,
     cals 0xC6206=512 / 0xC6208=205) and AFTER the primary rate interpolation (0x4546a-0x454e4).
     Skipping it leaves BOTH the governor clamp (<= 4762) and the per-cycle slew limit fully intact.
     It removes a second, state-4-only suppression layered on top of protection that remains.

RESIDUAL RISK, STATED PLAINLY: item 3 is an argument from verified code paths plus the empirical fact
that the unsubstituted path runs in production in seven other states. It is not a numerical proof over
every reachable input, and no live measurement was taken. If it is wrong the failure mode is
FUN_00016de6(0x1d) -> motor off + power cycle to recover, and it would appear mid-hard-turn.

-------------------------------------------------------------------------------------------------------
CHANGE 2 -- THE VIBRATION (see the module's Change-2 constants below)
-------------------------------------------------------------------------------------------------------
The vibration is speed-independent and present whenever LKAS commands torque and the wheel turns.
EIGHT firmware candidates were eliminated for it (r24 on-car via V39; the
motor-rate cap on-car via V41; FUN_000456a4's gate -- not command-derived; the +/-8192 sanitize --
unreachable; the aggregator reduced mode -- unreachable on A160; polarity -- static config byte;
gp-0x67fe -- per-drive-cycle state; and the pre-gain deadband 0xC61B8 -- gated OFF above ~4 mph,
measured across 98,053 raw CAN-399 frames). plus motor torque ripple (ruled out: hand steering
delivers comparable motor torque through the same shared path and is smooth).

What put r26 last-standing is a STRUCTURAL result: the arbitration IIR at gp-0x3d3c has pole 0.96875,
tau ~31.5 cycles => the whole LKAS command lane is a ~1-5 Hz LOW-PASS. A tens-of-Hz component therefore
CANNOT be commanded through it, which eliminates every upstream-of-gain source at once -- including
openpilot's own STEER_DELTA, previously this session's leading candidate and now downgraded to a
several-Hz explanation only. r26 is a DERIVATIVE (high-pass), so it passes exactly the band the IIR
blocks; it has no deadzone (unlike r24, cal 0xC61F6 = +/-3, which is why V39's r24 kill was a no-op near
zero); and it closes a loop through the mechanical plant.
See lkas_iir_quantization_analysis() and _inline_torque_rate_a() in model/eps_lkas_chain_model.py.

r26 is a WELL-FOUNDED HYPOTHESIS, not a verified root cause like Change 1. The two changes target
SEPARATELY OBSERVABLE symptoms and are INDEPENDENTLY BACKABLE-OUT, so a null result stays attributable.
=======================================================================================================
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V42 builder requires assertions; do not run with python -O")

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

V42_TAG = "LKAS-4x-V38base-state4-ratchet-off-r26-off"
V42_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V42-{V42_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v42_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- THE EDIT ----------------------------------------------------------------------------------
# 0x454fe: `bne 0x455c4` -> `br 0x455c4`. V850 Bcond format III is one halfword:
#     bits[15:11] = disp[8:4] | bits[10:7] = 0b1011 (Bcond) | bits[6:4] = disp[3:1] | bits[3:0] = cond
# cond 0b1010 = BNE/BNZ, cond 0b0101 = BR (always). Only the low nibble moves, so the DISPLACEMENT
# and therefore the BRANCH TARGET are provably unchanged -- asserted below by decoding both.
EDIT_ADDR = 0x454FE
EDIT_STOCK_HW = 0x65BA          # bne  +198 -> 0x455c4
EDIT_NEW_HW = 0x65B5            # br   +198 -> 0x455c4
COND_BNE, COND_BR = 0xA, 0x5

# Instruction context that must match byte-for-byte, or the baseline is not what we think it is.
CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))    # ld.bu -0x67fa[gp],r12
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))        # cmp 0x4,r12
SUBST_BLOCK = (0x45500, 0x455C4)                       # the block the edit makes unreachable

# ---- CHANGE 2: neutralise the r26 adaptive Sensor-B torque-rate lane -----------------------------
# r26 = clamp(polarity * ((dtorque * avg(gp-0x69a4)) >> 10 * gain_A) >> 10, +/-0x2000) in FUN_0003aa2c.
# Zeroing every Y row of gain_A's 4-record table makes the flat-extrapolated LERP evaluate to 0 at
# EVERY motor-rate/avg-torque combination, and zeroing the two override cals covers the two non-default
# gain paths -- so r26 == 0 unconditionally, in every reachable state, without touching gp-0x69a4's
# producer (shared with the still-live gp-0x6b86 lane).
#
# WHY r26 AND NOT r24: r24 was already zeroed by V39 and changed nothing on-car -- but r24 carries a
# +/-3 DEADZONE (cal 0xC61F6) so it was near-inert at low torque anyway. r26 has NO deadzone and is the
# only derivative lane live near zero. It is also a DERIVATIVE, i.e. HIGH-pass, so it passes exactly the
# band the arbitration IIR (pole 0.96875, tau ~31.5 cyc) blocks -- see lkas_iir_quantization_analysis()
# in the golden model for why that makes it the last mechanism standing for a fast vibration.
# Both lanes carry the SAME sign (shared dtorque register r1, single shared polarity load @0x3ab78),
# so this is not removing a counterweight to r24.
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)   # u16 count, s16 X[4], s16 Y[4], u16 pad
RATE_A_X_OFFSET, RATE_A_Y_OFFSET = 2, 0xA
RATE_A_COUNT = 4
RATE_A_X_STOCK = ((0, 400, 1600, 3000), (0, 250, 1200, 3000),
                  (0, 400, 1250, 3000), (0, 400, 1250, 3000))
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))
RATE_A_Y_NEW = (0, 0, 0, 0)
R26_OVERRIDES = ((0xC6444, 512, "tp+0x7444, taken when gp-0x683c != 0"),
                 (0xC643E, 1536, "tp+0x743e, taken when assist_state >= cal 0xC64FA"))
# r24's own cals -- asserted UNTOUCHED so the two lanes stay provably independent.
R24_CALS = ((0xC6440, 2048), (0xC6442, 1024), (0xC6446, 512), (0xC61F6, 3))

CAL_BLOCK = (0xC6000, 0xC6FFC)     # holds every r26 edit; CRC @0xC6FFC

# Cal cells that MUST remain stock.
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38)"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal"),
    0xC6206: (512, "governor slew step, fast"),
    0xC6208: (205, "governor slew step, slow"),
    0xC6134: (1000, "substitution scale (shared with FUN_00041464)"),
    0xC648E: (0, "substitution bias (signed; shared)"),
    0xC64A3: (1, "pre-gain deadband enable -- deliberately LEFT ON"),
    0xC61B8: (102, "pre-gain deadband threshold -- deliberately LEFT STOCK"),
    0xC6194: (3, "dead LKAS rate limiter"),
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
    """Decode a V850 Bcond halfword -> (cond, absolute_target). Returns None if not a Bcond."""
    halfword = struct.unpack_from("<H", code, address)[0]
    if (halfword >> 7) & 0xF != 0xB:
        return None
    cond = halfword & 0xF
    disp = (((halfword >> 11) & 0x1F) << 4) | (((halfword >> 4) & 0x7) << 1)
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


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    # The V39 cave must be absent -- V42 is V38-based, not V39-based.
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V38"
    for address, (value, note) in STOCK_CALS.items():
        got = struct.unpack_from("<h" if address == 0xC648E else "<H", code, address)[0]
        if address == 0xC64A3:
            got = code[address]
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"
    # r26 adaptive-gain table baseline: count, X rows, Y rows, pad -- all four records.
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<H", code, base)[0] == RATE_A_COUNT, f"r26 record 0x{base:05X} count"
        assert struct.unpack_from("<4h", code, base + RATE_A_X_OFFSET) == RATE_A_X_STOCK[i],             f"r26 record 0x{base:05X} X row moved"
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i],             f"r26 record 0x{base:05X} Y row is not stock"
        assert struct.unpack_from("<H", code, base + 0x12)[0] == 0, f"r26 record 0x{base:05X} pad"
    for address, value, note in R26_OVERRIDES:
        assert struct.unpack_from("<H", code, address)[0] == value, f"0x{address:05X} ({note})"
    for address, value in R24_CALS:
        assert struct.unpack_from("<H", code, address)[0] == value, f"r24 cal 0x{address:05X} moved"
    # The exact instruction context around the edit.
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

    # ---- the single edit ------------------------------------------------------------------------
    print("  THE EDIT -- one byte, one condition-code nibble:")
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

    # ---- CHANGE 2: zero the r26 adaptive-gain surface --------------------------------------------
    print("  CHANGE 2 -- r26 adaptive torque-rate lane neutralised (18 halfwords):")
    for i, base in enumerate(RATE_A_RECORDS):
        struct.pack_into("<4h", code, base + RATE_A_Y_OFFSET, *RATE_A_Y_NEW)
        print(f"    0x{base + RATE_A_Y_OFFSET:05X}: {list(RATE_A_Y_STOCK[i])} -> {list(RATE_A_Y_NEW)}  "
              f"gain_A Y row (record 0x{base:05X})")
    for address, value, note in R26_OVERRIDES:
        struct.pack_into("<H", code, address, 0)
        print(f"    0x{address:05X}: {value} -> 0  {note}")
    # X rows, counts, terminators and every r24 cal stay stock.
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_X_OFFSET) == RATE_A_X_STOCK[i], "r26 X moved"
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_NEW
        assert struct.unpack_from("<H", code, base)[0] == RATE_A_COUNT
        assert struct.unpack_from("<H", code, base + 0x12)[0] == 0, "r26 record terminator moved"
    for address, value in R24_CALS:
        assert struct.unpack_from("<H", code, address)[0] == value,             f"r24 cal 0x{address:05X} MOVED -- the two lanes must stay independent"

    # ---- everything else must be untouched ------------------------------------------------------
    dirty = owning_block(code, EDIT_ADDR)
    print(f"  CRC coverage: 0x{EDIT_ADDR:05X} lies inside "
          f"[0x{dirty[0]:X},0x{dirty[1]:X}) -> CRC @0x{dirty[1]:X} WILL be recomputed")

    cal_dirty = owning_block(code, RATE_A_RECORDS[0])
    assert cal_dirty == CAL_BLOCK, f"r26 edits land in {cal_dirty}, expected {CAL_BLOCK}"
    for address, _, _ in R26_OVERRIDES:
        assert owning_block(code, address) == CAL_BLOCK, "an override cal is outside the cal block"
    print(f"  CRC coverage: r26 edits lie inside "
          f"[0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X}) -> CRC @0x{CAL_BLOCK[1]:X} WILL be recomputed")

    for block in sorted({dirty, cal_dirty}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    allowed = {EDIT_ADDR}
    for base in RATE_A_RECORDS:
        allowed.update(range(base + RATE_A_Y_OFFSET, base + RATE_A_Y_OFFSET + 2 * RATE_A_COUNT))
    for address, _, _ in R26_OVERRIDES:
        allowed.update(range(address, address + 2))
    for block in {dirty, cal_dirty}:
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V42-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # NOTE the byte count is NOT 1 + 36 + 8 = 45. Ten of the 36 r26 bytes were ALREADY 0x00: values
    # like 3072 (0x0C00), 2048 (0x0800), 1536 (0x0600), 2560 (0x0A00) and 512 (0x0200) have a zero low
    # byte, so zeroing the halfword moves only its high byte. Actual: 26 r26 + 1 code + 8 CRC = 35.
    # The real safety check is `set(diffs) <= allowed` above plus the exact-value assertions below;
    # this bound just catches a runaway write.
    assert len(diffs) <= 1 + 36 + 8, f"too many changed bytes: {len(diffs)}"
    assert len(diffs) == 35, f"expected exactly 35 changed bytes, got {len(diffs)}"

    # Zero calibration edits: every cal block byte-identical to V38.
    # NOTE 0xC4FFC is the MAIN application block's CRC trailer, and the edit lives inside that block
    # [0x13000,0xC4FFC) -- so unlike every cal-only build in this kit, V42 legitimately rewrites it.
    # That is the ONLY byte outside 0x454FE that may move. Assert the cal region around it instead.
    assert bytes(code[0xBF000:0xC4FFC]) == bytes(baseline[0xBF000:0xC4FFC]), "CAL EDIT in 0xBF000-0xC4FFC"
    assert bytes(code[0xC5000:0xC6000]) == bytes(baseline[0xC5000:0xC6000]), "cap tables moved"
    # 0xC6000 block: only the 18 r26 halfwords + its own trailer may differ.
    cal_diffs = {i for i in range(0xC6000, 0xC7000) if code[i] != baseline[i]}
    assert cal_diffs <= allowed, f"unexpected 0xC6000-block bytes: {sorted(cal_diffs - allowed)}"
    assert bytes(code[0xE4000:0xE6000]) == bytes(baseline[0xE4000:0xE6000]), "setpoint records moved"
    assert bytes(code[0xF9000:0x100000]) == bytes(baseline[0xF9000:0x100000]), "banks B/C moved"
    # And no OTHER code moved.
    assert bytes(code[START:EDIT_ADDR]) == bytes(baseline[START:EDIT_ADDR]), "code before the edit moved"
    assert bytes(code[EDIT_ADDR + 1:0xBF000]) == bytes(baseline[EDIT_ADDR + 1:0xBF000]), \
        "code after the edit moved"

    assert_crc_chain(code, "V42 plain")
    assert walk(bytes(code), label="V42") == 0
    assert walk_all_blocks(bytes(code), label="V42") == 0
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else \
            struct.unpack_from("<h" if address == 0xC648E else "<H", code, address)[0]
        assert got == value, f"0x{address:05X} moved ({note})"
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_NEW
    for address, _, _ in R26_OVERRIDES:
        assert struct.unpack_from("<H", code, address)[0] == 0
    print("  all 11 tracked calibrations verified STOCK; r26 gain surface verified ZERO everywhere")

    # ---- RWD round-trip -------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V42 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V42 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V42 RWD readback")
    assert walk(readback, label="V42 RWD readback") == 0
    assert walk_all_blocks(readback, label="V42 RWD readback") == 0
    assert struct.unpack_from("<H", decoded, EDIT_ADDR - START)[0] == EDIT_NEW_HW, \
        "the edit did not survive the RWD round-trip"
    assert decode_bcond(readback, EDIT_ADDR) == (COND_BR, SUBST_BLOCK[1])
    for base in RATE_A_RECORDS:
        assert struct.unpack_from("<4h", decoded, base - START + RATE_A_Y_OFFSET) == RATE_A_Y_NEW,             "r26 zeroing did not survive the RWD round-trip"
    for address, _, _ in R26_OVERRIDES:
        assert struct.unpack_from("<H", decoded, address - START)[0] == 0
    for address, value in R24_CALS:
        assert struct.unpack_from("<H", decoded, address - START)[0] == value, "r24 cal moved in RWD"

    print(f"\n  V42-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == EDIT_ADDR: kind = "state-4 branch nibble"
        elif first in (0xC4FFC, 0xC6FFC): kind = "CRC trailer"
        else: kind = "r26 gain surface"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256: {V38_SHA256}")
    print(f"  V42 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V42 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V42-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V42_OUT)]
    for path in stale + [V42_OUT, BIN_OUT, V42_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V42 = V38 + TWO changes, targeting the two symptoms separately.")
    print("  CHANGE 1 (CODE, 1 byte) -- the hard-turn RATCHET, a VERIFIED root cause:")
    print("      0x454FE  bne 0x455C4 -> br 0x455C4   (V850 cond nibble 0xA -> 0x5)")
    print("      The substitution block [0x45500,0x455C4) becomes unreachable, so the governor")
    print("      stops forbidding the command MAGNITUDE from rising while gp-0x67fa == 4.")
    print("      No cave, no relocation, branch target unchanged -- first non-cave code edit here.")
    print("  CHANGE 2 (CAL, 18 halfwords) -- the VIBRATION, a last-standing HYPOTHESIS:")
    print("      r26 adaptive torque-rate gain surface zeroed; r24 cals and all X rows untouched.")
    print("      r26 is a DERIVATIVE (high-pass), so it passes the band the LKAS-lane IIR low-pass")
    print("      blocks -- which is what eliminated every upstream candidate incl. STEER_DELTA.")
    print("  SCORE THE TWO SYMPTOMS SEPARATELY. A null on the vibration falsifies r26 without")
    print("  implicating change 1. The changes are independently backable-out.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V42_OUT), exist_ok=True)
    with open(V42_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V42_OUT + ".tmp", V42_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V42_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
