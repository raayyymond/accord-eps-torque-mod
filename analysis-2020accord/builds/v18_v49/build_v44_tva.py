"""
builds/v18_v49/build_v44_tva.py -- V44 = V43 + restore the hands-off damping term, minus V43's falsified pole.

=======================================================================================================
V44 IN ONE LINE
    The base-assist DAMPING term is multiplied by EXACTLY ZERO whenever the driver's hands are off
    the wheel. V44 raises the two Y[0] cells that force that zero, so damping exists hands-off.

WHAT THE V43 DRIVE ESTABLISHED
    V43 (0xC644A 1024 -> 32, the "dirty-derivative" pole on FUN_0003a382's Stage C) did NOT change
    the vibration. That pole is FALSIFIED and V44 REVERTS it to stock 1024, following the same
    precedent V43 itself set when it reverted V42's falsified r26 surface: stock is the better
    default for a term we no longer suspect, and a null edit left riding along is a confounder.

    V42's Change 1 -- the state-4 ratchet fix at 0x454FE -- remains CONFIRMED on-car and is carried
    through untouched. It is NOT under test in V44.

THE MECHANISM  [the damping term is not weak hands-off; it is IDENTICALLY ZERO]

    FUN_00034350 produces the base-assist damping lane gp-0x6bd0 as a chained product:

        seed = clamp(gp-0x698a, 0, 1024)
        term = seed * f(0xC9CCC) * f(0xC9E9C) * f(0xC9DB4) * f(0xC9F84)     each Q10, each >>10
        if (gp-0x6abe > 0) term = -term                                     <- sign = motor rate
        term = clamp(term, +/- 0xC77A0) -> gp-0x6bd0                        (shadow gp-0x4cf2)

    Four chained `mulu`+`shr 0xa` at 0x34684 / 0x3468a / 0x34690 / 0x34698 -- a genuine
    multiplicative product, not an add or select chain. [VERIFIED]

    Factor 2 is a mode-indexed LERP keyed on VOTED DRIVER TORQUE gp-0x6a5e. For this car:

        mode 10  @0xD27BC   X=(2240,3840,5120,8960)   Y=(  0, 235, 430, 877)
        mode 11  @0xD27D0   X=(2240,3840,5120,8960)   Y=(  0, 234, 431, 877)

    *** Y[0] = 0 IN BOTH. *** One zero multiplicand kills the whole product. So below 2240 counts of
    driver torque -- i.e. hands off -- the damping lane contributes EXACTLY NOTHING. The LERP CLAMPS
    below X[0] (verified; it does not extrapolate), so this is a flat zero, not a small value.

    Gate semantics are inverted from intuition and worth stating: the gate at 0x344dc-0x344fa reads
    `if (gp-0x6a5e > 32000 || gp-0x67f4 != 1) -> factor = 1024 (UNITY)  else -> LERP`. A FAILED
    plausibility check yields unity (no suppression); a PASSED check with low torque yields ZERO.
    The suppression only happens when the sensor is working correctly and honestly reports hands-off.

WHY THIS MATTERS, AND WHAT IT IS NOT

    *** MEASURED, route b9, 307 s hands-off, 60 non-overlapping windows: ***
        peak 21.448 Hz, -3 dB width 1.576 Hz, Q = 13.6, coherence time ~0.23 s.
    That is a LIGHTLY-DAMPED MECHANICAL RESONANCE, confirmed three independent ways (instrumental
    width is only 18% of measured; coherence ~4 cycles; peak-height-vs-window-length slope +0.635,
    not the 1.0 a coherent line would give).

    *** The kit's recorded "sharp isolated 21.02 Hz line, top-5 bins within 0.09 Hz" is an ARTIFACT
    of concatenating discontiguous FFT windows. Redone properly the top five span 0.94 Hz. ***
    The clock-derived / digital-limit-cycle reading built on that number is withdrawn.

    Driver torque, measured, as a fraction of Sensor-B full scale:
        hands-off  median 0.59%     assisting  median 8.10%
    The gate sits at 2240/32000 ~= 7% of full scale. Those straddle it by MORE THAN A DECADE.
    [INFERENCE, assumption stated: that the two sensors' full scales map to comparable physical
    torque. Sensor A is NEVER transmitted on CAN, so no direct conversion exists and none is used.]

    !! HONEST SCOPE: hands-off driver torque is essentially UNCHANGED pre- vs post-V38 (0.44-0.94%
    FS across routes b9 / 77 / 79, the two pre-V38 routes BRACKETING b9). So damping was equally
    zeroed on builds that did NOT vibrate. ZERO DAMPING IS AN ENABLING CONDITION, NOT THE CHANGE.
    V38's 4x authority is what now excites the mode. V44 is therefore a MITIGATION of a real
    lightly-damped resonance, not a root-cause repair -- adding damping to a Q=13.6 mode is the
    textbook intervention, but do not expect it to explain the regression.

WHY THE RESTORED TERM CAN ACTUALLY DAMP  [three objections raised and all three refuted]

  1. "Sign-freeze": FUN_00041464 pins gp-0x6abe to 0x7fff when |gp-0x4f50| > 13000 (symmetric --
     settled from Ghidra PCODE `INT_LESS(26000, r11)` on `INT_ADD(r15, 13000)`, the standard
     unsigned(x+K)<=2K idiom). But gp-0x4f50's own producer FUN_00068f52 CLAMPS to exactly
     [-13000, +13000]. *** The pin's trigger is structurally unreachable. *** The 14-bit wraparound
     fold bounds the raw delta to +/-8192, scaled by 120000/16384 to +/-60000 pre-clamp -- so the
     clamp is genuinely active, which is precisely WHY the downstream pin can never fire.

  2. "Half-wave rectification": the V43 handoff records `ld.hu -0x6ac0[gp]` at 0x345fa as making the
     term dead for one rotation direction. *** THAT ENTRY IS WRONG. *** gp-0x6ac0's producer applies
     abs() BEFORE the store, so the value is non-negative by construction and ld.hu vs ld.h is a
     no-op. Reached independently by two tracers. The real half-cycle effect nearby is on gp-0x6ac2,
     a different output feeding the clamp BOUND -- almost certainly what the original note conflated.

  3. "Phase lag flips it to anti-damping": the sign source is a one-pole EMA, cal 0xC643C = 37,
     alpha = 37/128. Computed with the EXACT discrete response H(z) = a/(1-(1-a)z^-1), NOT the
     continuous RC approximation (which overestimates lag badly near Nyquist and produced an earlier
     wrong -78 deg figure). The tick rate is unproven, so this is evaluated across EVERY chip clock
     the SVD documents (DFLASH.DCLKWAIT: 48/64/80/160 MHz) at OSTM0 reload 79488:

         48 MHz ->  604 Hz tick -> phase -27.2 deg -> Coulomb efficacy cos = 0.890
         64 MHz ->  805 Hz      -> -21.6 deg                            = 0.930
         80 MHz -> 1006 Hz      -> -17.8 deg                            = 0.952
        160 MHz -> 2013 Hz      ->  -9.3 deg                            = 0.987

     Net-damping across the entire documented range; nowhere near the 90 deg energy-injection
     threshold. A 100 Hz tick would require a 7.95 MHz clock, which is NOT a documented option.

     *** The term is COULOMB damping -- magnitude from slow factors, SIGN from the fast filter. ***
     Energy dissipated per cycle is 4*F0*A, INDEPENDENT of frequency, degraded only by cos(phase).
     So the sign source's magnitude attenuation is irrelevant; only its phase matters. This is why
     V44's viability does NOT depend on resolving the tick rate.

     [OPEN, stated not hidden] The sign only alternates at 21 Hz if that component dominates the
     slower content of gp-0x6abe. That is an amplitude question the bytes cannot answer.

WHY BOTH TABLES  [the failover trap]

    Both mode 10 and mode 11 are reachable for this ECU. The selector is the byte gp+0x63fd, whose
    per-variant row is chosen by a 5-byte HW-ID match against the table at 0xCD000 (stride 0x24).
    Record 2's key bytes read ASCII "TVAA1" -- this car -- and its mode set is {10,10,11,11}.
    FUN_00042746 reselects among those four columns at runtime on internal sensor-quality state.
    *** Patching only mode 10 would let the fix silently vanish after a failover, with no other
    symptom. *** Both tables are patched, each to its OWN Y[1] value (235 / 234), which preserves
    the ~1% variant relationship and writes only values already present and exercised in that table.

WHY Y[1] AND NOT SOMETHING LARGER
    Setting Y[0] := Y[1] flattens the first LERP segment instead of inventing a magnitude. Every
    byte written already exists in the same table. This is the closest available approximation to
    this kit's standing rule -- WIDEN AN ALREADY-LIVE PATH, DO NOT INVENT ONE -- for an edit that
    unavoidably activates a term in a regime where it has never been active.
    [OPEN] Whether 235 Q10 is ENOUGH to damp a Q=13.6 mode is NOT established. The measured
    oscillation is ~139 counts of gp-0x4f60; the lane is range-gated at +/-0x800 in the aggregator,
    so there is headroom. This edit may be a NULL. It should not be able to make things worse.

BLAST RADIUS  [all verified, byte-level]
    - Pointer array 0xC9E9C has exactly 2 xrefs, both inside FUN_00034350. Nothing else reads it.
    - NO FLOAT MIRROR: exhaustive image-wide search for the IEEE-754 patterns of 235/1024, 430/1024
      and 877/1024 (0x3E6B0000 / 0x3ED70000 / 0x3F5B4000) returns ZERO matches. This is the failure
      class that caused V27 (an unmatched int/float edit) and it does not apply here.
    - Shadow lockstep gp-0x6bd0 / gp-0x4cf2: exactly 3 writers each, and each shadow store sits
      exactly 4 bytes after its primary in all three branches. They cannot desynchronise.
    - The other three multiplied factors default to Q10 UNITY (not zero) when their own gates fail,
      so there is no second silent zero left to block the product.
    - gp-0x6bd0 genuinely reaches the live aggregator FUN_0003aa2c (sole writer of gp-0x6b94).

CRC MECHANICS  [0xD2xxx is only the SECOND block ever touched outside the compact cal region]
    Both targets fall inside the ordinary chain-interior block [0xD2000, 0xD2FFC), present in BOTH
    the faithful bootloader walk() and walk_all_blocks(). None of V40's [0xC5000,0xC5FFC) bridge-skip
    complications apply. The block's own chain self-descriptor lives at 0xD2FF8/0xD2FFA -- inside its
    own CRC range and far from the edits -- and the descriptor for the next link lives in the
    untouched 0xD1000 block, so chain topology is unaffected by construction. No prior builder in
    this kit has ever touched 0xD2xxx (exhaustive grep of build_v18..v43).
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
    raise RuntimeError("V44 builder requires assertions; do not run with python -O")

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

# Baseline is V43 -- the build currently ON THE CAR.
V43_PLAIN = str(plain_image_path("_v43_plain_image.bin"))
V43_RWD = os.path.join(
    RWD_DIR,
    "39990-TVA,A160-V43-LKAS-4x-V38base-state4-ratchet-off-derivative-pole32-0x13000-0x100000.rwd",
)
V43_SHA256 = "5ecfddcbd74c3508e0353d8ba6065bd866aaa0ac48bdf549dc8822ba7a0adccc"
V43_RWD_SHA256 = "a039af1368d80e0996651e5b9a3c9c3c1c680c416df2d6ae445a60b0ca5f461f"

# V38 is kept only as a lineage cross-check (V44-vs-V38 must be exactly the ratchet + damping edits).
V38_PLAIN = str(plain_image_path("_v38_plain_image.bin"))
V38_SHA256 = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"

EXPECTED_HEADERS = [
    (b"#", [b"\x00"]),
    (b"?", [b"A1"]),
    (b"/", [b"39990-TVA-A110", b"39990-TVA,A160"]),
    (b"!", [b"001100121020", b"001100121020"]),
    (b"&", [b"BF109E"]),
    (b"%", [b"30"]),
]

V44_TAG = "LKAS-4x-V38base-state4-ratchet-off-handsoff-damping"
V44_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V44-{V44_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v44_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH UNCHANGED: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) --------
RATCHET_ADDR = 0x454FE
RATCHET_HW = 0x65B5                 # `br +198` -- already applied in the V43 baseline
RATCHET_TARGET = 0x455C4
COND_BR = 0x5

# ---- CHANGE 1: REVERT V43's falsified dirty-derivative pole -------------------------------------
POLE_ADDR = 0xC644A
POLE_V43 = 32                       # what V43 shipped and the road falsified
POLE_STOCK = 1024                   # Q10 unity == pole disabled == stock/V38 behaviour
POLE_SIBLING_ADDR = 0xC6450         # proportional-branch sibling; must stay at unity throughout
POLE_SIBLING_STOCK = 1024

# ---- CHANGE 2: restore hands-off damping --------------------------------------------------------
# Record layout, byte-verified: +0x00 u16 count | +0x02..+0x08 u16 X[0..3] | +0x0A..+0x10 u16 Y[0..3]
# | +0x12 u16 pad.  Stride to the next table is exactly 0x14.
DAMP_RECORDS = (
    # (table base, mode, X row, stock Y row, new Y[0])
    (0xD27BC, 10, (2240, 3840, 5120, 8960), (0, 235, 430, 877), 235),
    (0xD27D0, 11, (2240, 3840, 5120, 8960), (0, 234, 431, 877), 234),
)
DAMP_COUNT = 4
DAMP_X_OFF, DAMP_Y_OFF, DAMP_PAD_OFF, DAMP_STRIDE = 0x02, 0x0A, 0x12, 0x14

DAMP_PTR_ARRAY = 0xC9E9C            # mode-indexed pointer array; 2 xrefs, both in FUN_00034350
HWID_RECORD_2 = 0xCD048             # this car's variant row; first 5 bytes are the HW-ID key
HWID_KEY = b"TVAA1"

CAL_BLOCK = (0xC6000, 0xC6FFC)      # holds the pole revert
DAMP_BLOCK = (0xD2000, 0xD2FFC)     # holds both Y[0] edits -- NEW to this kit
MAIN_BLOCK = (0x13000, 0xC4FFC)     # holds the ratchet byte (unchanged from V43, CRC already correct)

# Float mirrors that must NOT exist for the Y values we touch (V27's failure class).
FLOAT_MIRROR_PATTERNS = {
    235: 0x3E6B0000,                # 235/1024 = 0.2294921875
    430: 0x3ED70000,                # 430/1024 = 0.419921875
    877: 0x3F5B4000,                # 877/1024 = 0.8564453125
    234: 0x3E6A0000,                # 234/1024 = 0.228515625
    431: 0x3ED78000,                # 431/1024 = 0.4208984375
}

# Cal cells that MUST remain exactly as V43/V38 left them.
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x)"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal"),
    0xC6206: (512, "governor slew step, fast -- NOT touched"),
    0xC6208: (205, "governor slew step, slow -- NOT touched"),
    0xC636E: (205, "damping lane input EMA -- NOT touched"),
    0xC6372: (205, "boost lane input EMA -- the rejected candidate B, NOT touched"),
    0xC643C: (37, "gp-0x6abe sign-source filter gain"),
    0xC64A3: (1, "pre-gain deadband enable"),
    0xC61B8: (102, "pre-gain deadband threshold"),
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


def assert_no_float_mirror(code):
    """V27's failure class: an int table edited while its float twin is left behind.

    Exhaustive image-wide byte scan for the IEEE-754 little-endian encodings of every Y value in
    both damping tables. A clean zero here is what licenses a pure-integer edit.
    """
    for value, bits in sorted(FLOAT_MIRROR_PATTERNS.items()):
        pattern = struct.pack("<I", bits)
        hits = []
        index = code.find(pattern)
        while index != -1:
            hits.append(index)
            index = code.find(pattern, index + 1)
        assert not hits, \
            f"float mirror of Y={value} ({value / 1024.0}) found at {[hex(h) for h in hits]} -- " \
            f"an integer-only edit would desynchronise it (this is the V27 failure mode)"
    print(f"  no float mirror for any Y value in either damping table "
          f"({len(FLOAT_MIRROR_PATTERNS)} IEEE-754 patterns, image-wide) [VERIFIED zero]")


def assert_damping_tables(code, label, expect_new):
    """Assert both damping records in full -- count, X row, Y row, pad -- not just Y[0]."""
    for base, mode, x_row, y_row, new_y0 in DAMP_RECORDS:
        count = struct.unpack_from("<H", code, base)[0]
        assert count == DAMP_COUNT, f"{label}: mode {mode} count {count} != {DAMP_COUNT}"
        got_x = struct.unpack_from("<4H", code, base + DAMP_X_OFF)
        assert got_x == x_row, f"{label}: mode {mode} X row moved: {got_x} != {x_row}"
        got_y = struct.unpack_from("<4H", code, base + DAMP_Y_OFF)
        want_y = (new_y0,) + y_row[1:] if expect_new else y_row
        assert got_y == want_y, f"{label}: mode {mode} Y row {got_y} != {want_y}"
        pad = struct.unpack_from("<H", code, base + DAMP_PAD_OFF)[0]
        assert pad == 0, f"{label}: mode {mode} pad {pad} != 0"
    # The two records must remain exactly one stride apart and not have collided.
    assert DAMP_RECORDS[1][0] - DAMP_RECORDS[0][0] == DAMP_STRIDE, "record stride changed"


def assert_v43_baseline(code):
    assert len(code) == 0x100000, f"V43 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V43_SHA256, "baseline is not the V43 image"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V43"

    # The ratchet fix must ALREADY be applied and must decode as an unconditional branch.
    assert struct.unpack_from("<H", code, RATCHET_ADDR)[0] == RATCHET_HW, \
        f"0x{RATCHET_ADDR:05X} is not V43's `br` halfword -- baseline is wrong"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), \
        "the state-4 ratchet fix does not decode as `br 0x455C4` in the baseline"

    # V43's pole must be present at 32 -- proving we are reverting a REAL edit, not a no-op.
    got = struct.unpack_from("<H", code, POLE_ADDR)[0]
    assert got == POLE_V43, \
        f"0x{POLE_ADDR:05X} is {got}, expected V43's {POLE_V43}; the revert would be a no-op"
    assert struct.unpack_from("<H", code, POLE_SIBLING_ADDR)[0] == POLE_SIBLING_STOCK, \
        "the proportional-branch sibling pole is not at unity"

    # Both damping tables must be at STOCK (Y[0] == 0) before we touch them.
    assert_damping_tables(code, "V43 baseline", expect_new=False)

    # This car's variant row, proving mode 11 really is reachable and must also be patched.
    assert bytes(code[HWID_RECORD_2:HWID_RECORD_2 + 5]) == HWID_KEY, \
        f"0x{HWID_RECORD_2:05X} does not hold the expected HW-ID key {HWID_KEY!r}"

    # The mode-indexed pointer array must resolve mode 10 and 11 to the tables we are patching.
    for base, mode, *_ in DAMP_RECORDS:
        pointer = struct.unpack_from("<I", code, DAMP_PTR_ARRAY + mode * 4)[0]
        assert pointer == base, \
            f"pointer array slot {mode} resolves to 0x{pointer:05X}, expected 0x{base:05X}"

    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else struct.unpack_from("<H", code, address)[0]
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"


def build():
    baseline = bytearray(open(V43_PLAIN, "rb").read())
    assert_v43_baseline(baseline)
    assert_crc_chain(baseline, "V43 baseline")
    assert walk(bytes(baseline), label="V43 baseline") == 0
    assert walk_all_blocks(bytes(baseline), label="V43 baseline") == 0
    assert_no_float_mirror(baseline)

    v38 = bytearray(open(V38_PLAIN, "rb").read())
    assert hashlib.sha256(bytes(v38)).hexdigest() == V38_SHA256, "V38 lineage image is wrong"
    assert bytes(v38[DAMP_BLOCK[0]:DAMP_BLOCK[1] + 4]) == bytes(baseline[DAMP_BLOCK[0]:DAMP_BLOCK[1] + 4]), \
        "the 0xD2000 block already differs between V38 and V43 -- investigate before editing it"

    source_rwd = open(V43_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V43_RWD_SHA256
    assert_x31_checksum(source_rwd, "V43 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["key"] == list(V9B["keys"])
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    assert decode is not None
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V43 RWD does not decode to _v43_plain_image.bin"

    code = bytearray(baseline)

    # ---- CHANGE 1: revert V43's falsified pole ---------------------------------------------------
    print("  CHANGE 1 (REVERT) -- V43's dirty-derivative pole was falsified on-car:")
    struct.pack_into("<H", code, POLE_ADDR, POLE_STOCK)
    print(f"    0x{POLE_ADDR:05X}: {POLE_V43} -> {POLE_STOCK}   "
          f"(alpha {POLE_V43 / 1024.0:.4f} -> {POLE_STOCK / 1024.0:.4f} = Q10 unity, back to stock)")
    print("    Same precedent V43 set when it reverted V42's falsified r26 surface: a null edge")
    print("    left riding along is a confounder, and stock is the better default.")
    assert struct.unpack_from("<H", code, POLE_ADDR)[0] == POLE_STOCK
    assert struct.unpack_from("<H", code, POLE_SIBLING_ADDR)[0] == POLE_SIBLING_STOCK
    assert bytes(code[POLE_ADDR:POLE_ADDR + 2]) == bytes(v38[POLE_ADDR:POLE_ADDR + 2]), \
        "the pole revert did not restore V38's exact bytes"

    # ---- CHANGE 2: restore hands-off damping -----------------------------------------------------
    print("  CHANGE 2 (NEW) -- restore the damping term hands-off, BOTH reachable modes:")
    for base, mode, x_row, y_row, new_y0 in DAMP_RECORDS:
        struct.pack_into("<H", code, base + DAMP_Y_OFF, new_y0)
        print(f"    0x{base + DAMP_Y_OFF:05X}: mode {mode:>2}  Y[0] {y_row[0]} -> {new_y0}   "
              f"(= that table's own Y[1]; X[0]={x_row[0]} unchanged)")
    print("    Below 2240 counts of driver torque the damping product was multiplied by ZERO.")
    print("    Both modes patched: {10,10,11,11} are all reachable via the runtime reselector,")
    print("    so patching only mode 10 would let the fix vanish silently after a failover.")
    assert_damping_tables(code, "V44 built", expect_new=True)
    assert_no_float_mirror(code)

    # Nothing else in the damping lane may move.
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else struct.unpack_from("<H", code, address)[0]
        assert got == value, f"0x{address:05X} moved ({note})"

    # ---- ratchet fix must survive untouched ------------------------------------------------------
    assert struct.unpack_from("<H", code, RATCHET_ADDR)[0] == RATCHET_HW, "ratchet fix disturbed"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), \
        "the state-4 ratchet branch no longer decodes as `br 0x455C4`"
    print(f"  ratchet fix CARRIED THROUGH: 0x{RATCHET_ADDR:05X} still `br 0x{RATCHET_TARGET:05X}` "
          f"(confirmed root cause, not under test)")

    # ---- CRC coverage ----------------------------------------------------------------------------
    cal_dirty = owning_block(code, POLE_ADDR)
    assert cal_dirty == CAL_BLOCK, f"pole revert lands in {cal_dirty}, expected {CAL_BLOCK}"
    damp_blocks = {owning_block(code, base + DAMP_Y_OFF) for base, *_ in DAMP_RECORDS}
    assert damp_blocks == {DAMP_BLOCK}, \
        f"damping edits land in {damp_blocks}, expected a single block {DAMP_BLOCK}"
    print(f"  CRC coverage: pole 0x{POLE_ADDR:05X} -> [0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X})")
    print(f"  CRC coverage: both damping edits -> [0x{DAMP_BLOCK[0]:X},0x{DAMP_BLOCK[1]:X})  "
          f"*** first build in this kit to touch 0xD2xxx ***")

    # The 0xD2000 block's own chain self-descriptor sits at its tail, inside its own CRC range;
    # the descriptor that finds the NEXT link lives in the untouched 0xD1000 block. Assert both.
    assert bytes(code[DAMP_BLOCK[1] - 4:DAMP_BLOCK[1]]) == \
        bytes(baseline[DAMP_BLOCK[1] - 4:DAMP_BLOCK[1]]), "0xD2FF8/0xD2FFA self-descriptor moved"
    assert bytes(code[DAMP_BLOCK[0] - 8:DAMP_BLOCK[0] - 4]) == \
        bytes(baseline[DAMP_BLOCK[0] - 8:DAMP_BLOCK[0] - 4]), "0xD1FF8 next-link descriptor moved"

    for block in sorted({cal_dirty, DAMP_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V43 -------------------------------------------------------------------------
    allowed = {POLE_ADDR, POLE_ADDR + 1}
    for base, *_ in DAMP_RECORDS:
        allowed.update({base + DAMP_Y_OFF, base + DAMP_Y_OFF + 1})
    for block in (CAL_BLOCK, DAMP_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V44-vs-V43 bytes: {sorted(set(diffs) - allowed)}"
    # 12, not 14, and the arithmetic is worth stating because it is easy to get wrong:
    #   pole    0x0020 -> 0x0400  moves BOTH bytes                        = 2
    #   mode 10 0x0000 -> 0x00EB  moves only the LOW byte (high stays 00) = 1
    #   mode 11 0x0000 -> 0x00EA  likewise                                = 1
    #   two 4-byte CRC trailers                                           = 8
    assert len(diffs) == 12, f"expected exactly 12 changed bytes vs V43, got {len(diffs)}"

    # ---- exact diff vs V38 (lineage) ---------------------------------------------------------------
    v38_diffs, v38_runs = changed_runs(v38, code)
    v38_allowed = {RATCHET_ADDR}
    for base, *_ in DAMP_RECORDS:
        v38_allowed.update({base + DAMP_Y_OFF, base + DAMP_Y_OFF + 1})
    v38_allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    v38_allowed.update(range(DAMP_BLOCK[1], DAMP_BLOCK[1] + 4))
    assert set(v38_diffs) <= v38_allowed, \
        f"unexpected V44-vs-V38 bytes: {sorted(set(v38_diffs) - v38_allowed)}"
    # 11: 1 ratchet byte + 1 + 1 damping low bytes + the 0xC4FFC and 0xD2FFC trailers (4 each).
    # The pole revert makes the whole 0xC6000 block byte-identical to V38 again, so neither it
    # nor its trailer appears in this diff at all -- which is the point of reverting it.
    assert len(v38_diffs) == 11, f"expected exactly 11 changed bytes vs V38, got {len(v38_diffs)}"
    assert bytes(code[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]) == bytes(v38[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]), \
        "the 0xC6000 block is not byte-identical to V38 after the pole revert"

    # Everything else untouched.
    assert bytes(code[0xBF000:0xC4FFC]) == bytes(baseline[0xBF000:0xC4FFC]), "cal edit in 0xBF000-0xC4FFC"
    assert bytes(code[0xC5000:0xC6000]) == bytes(baseline[0xC5000:0xC6000]), "cap tables moved"
    assert bytes(code[0xE4000:0xE6000]) == bytes(baseline[0xE4000:0xE6000]), "setpoint records moved"
    assert bytes(code[0xF9000:0x100000]) == bytes(baseline[0xF9000:0x100000]), "banks B/C moved"
    assert bytes(code[START:0xBF000]) == bytes(baseline[START:0xBF000]), "CODE changed -- V44 is cal-only"
    assert bytes(code[0xD2000:0xD27C6]) == bytes(baseline[0xD2000:0xD27C6]), "0xD2000 block head moved"
    assert bytes(code[0xD27E4:0xD2FFC]) == bytes(baseline[0xD27E4:0xD2FFC]), "0xD2000 block tail moved"

    assert_crc_chain(code, "V44 plain")
    assert walk(bytes(code), label="V44") == 0
    assert walk_all_blocks(bytes(code), label="V44") == 0

    # ---- RWD round-trip ----------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V44 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V44 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V44 RWD readback")
    assert walk(readback, label="V44 RWD readback") == 0
    assert walk_all_blocks(readback, label="V44 RWD readback") == 0
    assert_damping_tables(readback, "V44 RWD readback", expect_new=True)
    assert struct.unpack_from("<H", readback, POLE_ADDR)[0] == POLE_STOCK, \
        "the pole revert did not survive the RWD round-trip"
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), \
        "the ratchet fix did not survive the RWD round-trip"
    assert_no_float_mirror(readback)

    print(f"\n  V44-vs-V43: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == POLE_ADDR:
            kind = "CHANGE 1: revert falsified pole 0xC644A 32 -> 1024"
        elif first in (r[0] + DAMP_Y_OFF for r in DAMP_RECORDS):
            mode = next(r[1] for r in DAMP_RECORDS if r[0] + DAMP_Y_OFF == first)
            kind = f"CHANGE 2: damping mode {mode} Y[0] 0 -> nonzero"
        elif first in (CAL_BLOCK[1], DAMP_BLOCK[1]):
            kind = "CRC trailer"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"\n  V44-vs-V38 lineage: {len(v38_diffs)} changed bytes in {len(v38_runs)} runs "
          f"(ratchet fix + damping restore only)")
    for first, last in v38_runs:
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)")
    print(f"  V43 SHA-256: {V43_SHA256}")
    print(f"  V44 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V44 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V44-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V44_OUT)]
    for path in stale + [V44_OUT, BIN_OUT, V44_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V44 = V43 + hands-off damping restored, minus V43's falsified pole. Built on V43.")
    print("  CHANGE 1 (CAL, 1 halfword) -- REVERT V43's dirty-derivative pole:")
    print("      0xC644A  32 -> 1024   V43 was flashed and did NOT move the vibration; the pole is")
    print("      falsified. Reverting restores V38 behaviour so it cannot confound V44's result.")
    print("  CHANGE 2 (CAL, 2 halfwords) -- the VIBRATION, a well-founded HYPOTHESIS:")
    print("      0xD27C6  0 -> 235   (mode 10)")
    print("      0xD27DA  0 -> 234   (mode 11)")
    print("      The base-assist DAMPING term is a product of four Q10 factors, and the factor keyed")
    print("      on voted driver torque is EXACTLY ZERO below 2240 counts -- i.e. hands off. One zero")
    print("      multiplicand kills the lane. Measured: hands-off driver torque sits at 0.59% of full")
    print("      scale, assisting at 8.10%, straddling the ~7% gate by more than a decade.")
    print("      The vibration is a MEASURED mechanical resonance: 21.448 Hz, Q = 13.6.")
    print("  CARRIED THROUGH: the state-4 ratchet fix at 0x454FE (CONFIRMED on-car, not under test).")
    print("  ONE vibration change only -- two would be unattributable, which is V42's own lesson.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V44_OUT), exist_ok=True)
    with open(V44_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V44_OUT + ".tmp", V44_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V44_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  NOT FLASHED. Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    main()
