"""
build_v52_tva.py -- V52 = the V50 EMA low-pass, MADE FLASHABLE. "V50 done right."

=======================================================================================================
V52 IN ONE LINE
    V50's first-order EMA low-pass (fc~=12 Hz, alpha=74/1024) on Sensor-B torque gp-0x4f60, keeping the
    4x LKAS gain and the CONFIRMED state-4 ratchet fix -- but with the THREE fixes that make it safe and
    complete to flash:
      (1) STATE CELL gp-0x1500 -> gp-0x1300.  V50's cell gp-0x1500 is slot 5 of the 0xb7260 I/O-mailbox
          array and has a LIVE WRITER (V50P probe drive: non-zero 99.47% of frames) -> V50 would brick
          (V48B RAM-collision class). gp-0x1300 (0xFEDF6D00) is OUTSIDE that array and the
          gp-0x1401..0x1502 poison region, and the V51P probe drive (rlog 7, 24000 CAN-330 frames,
          beacon live 100%) proved it reads 0 on EVERY frame at FULL 16-bit width -> definitive
          live-probe clearance. This retires V50's residual GATE-1 doubt (its only real weakness).
      (2) ROUND-TO-NEAREST EMA step: y += (74*d + 512)>>10 (V50 floored -> ~-7 count DC bias + a local
          gain bump in the 11-33 count band; the adversarial swarm's GATE-2 note). Frequency response
          unchanged -> GATE-2 stability carries and is strictly improved.
      (3) 3 MORE CARRIER REPOINTS (10 total): FUN_0002eda8's raw gp-0x4f60 reads -- a 3-way branch
          (0x2F318/0x2F330/0x2F33E) that is a live command-path lane V50 MISSED (-> gp-0x6b6c ->
          FUN_000339cc -> base-assist lane/channel 9). V50 repointed only 7; leaving these raw re-injects
          unfiltered resonance and weakens the filter. V52 repoints all 10.

GATES (applied without being asked; a code cave is the kit's only bricking class -- V24/V27/V48B):
    * GATE 1 (RAM ownership): gp-0x1300 -- DEFINITIVE. A live read-only probe (V51P) watched the full
      16-bit cell across a real drive and it never moved. This is stronger than any static clearance;
      it is exactly the test V50's gp-0x1500 failed.
    * GATE 2 (closed-loop stability): the filter is byte-for-byte V50's alpha=74/1024 EMA (see
      eps_v50_gate2_lowpass.py: STABLE under pessimistic Q_cl=13.6 and realistic Q_cl~4.8, no resonant
      pole). Round-to-nearest changes only the sub-LSB quantization, not the pole -> verdict carries.
    * The 8th repoint's monitor-safety (V27 class: no raw-vs-filtered lockstep on gp-0x6b6c/gp-0x6ad6/
      lane-9) was traced before adding it -- see the handoff / EXTRA_REPOINTS note below.

CAVE + REPOINTS: v52_cave_asm.py. Trampoline jr at 0x7FEAC displacing cmp r0,r8 + mov r8,r14
    (re-executed LAST so PSW flags are correct for the bge at the return); 8 live carrier repoints; the
    2 mode-gated DORMANT reads (0x34392/0x34ACE) left raw. Only the MAIN CRC block (0xC4FFC) is touched.
    0xC646C=3564 (4x) untouched; the damping clamp int+float mirror (DTC-0x1d trap) untouched.

STATUS: STUDY ARTIFACT, UNFLASHED. Flash ONLY on explicit operator instruction naming the file + bus,
    after a Ghidra re-disassembly of the built image (kit rule for any cave).
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V52 builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks
from v52_cave_asm import CAVE_BASE, HOOK, RETURN, D_CELL, assemble_cave, gp_field, jr

# =====================================================================================================
# GATE-1 RESULT -- the single 16-bit EMA cell is gp-0x1300 (0xFEDF6D00). Evidence: the V51P read-only
# probe (build_v51probe_tva.py) reduced the FULL 16-bit cell to a "was any bit ever set" flag, packed it
# into CAN-330 spare bits with a liveness beacon, and drove (rlog 7, 4 segments). Decode (two independent
# decoders, decode_v51p_gate1.py + lead verifier): 0/24000 frames non-zero, beacon 100% live on bus 1,
# stock-null distinguishable => NO live writer touches gp-0x1300. This is the definitive live-probe
# clearance that gp-0x1500 (V50) FAILED. Single 16-bit cell = state AND output (imported from
# v52_cave_asm). gp-0x1100 was equally clean and is the drop-in alternate if gp-0x1300 ever needs moving.
# =====================================================================================================

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

V52_TAG = "LKAS-4x-V38base-ratchet-lowpass-fc12hz-ema-gp1300-rnd-broadrepoint"
V52_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V52C-{V52_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v52c_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) -------------------
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA
RATCHET_NEW_HW = 0x65B5
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5

HOOK_STOCK = bytes.fromhex("e0410870")   # cmp r0,r8 ; mov r8,r14

# ---- the LIVE carrier repoint sites (Gate-1 reconfirmed on stock): ld.h -0x4f60[gp],rX ------------
# stock word1 = 0x24 | (byte1<<8); disp16 = 0xB0A0 (-0x4f60) -> D_CELL.
BASE_REPOINTS = [
    (0x2C480, 0x24 | (0x7F << 8), "FUN_0002c478 type-8 (r15)"),
    (0x354D2, 0x24 | (0x87 << 8), "FUN_000352b4 magnitude (r16)"),
    (0x35AA4, 0x24 | (0x77 << 8), "FUN_000352b4 magnitude (r14)"),
    (0x3A6CA, 0x24 | (0x57 << 8), "FUN_0003a382 resonance (r10)"),
    (0x3A7CA, 0x24 | (0x47 << 8), "FUN_0003a382 resonance (r8)"),
    (0x3B4A8, 0x24 | (0x6F << 8), "FUN_0003b49a -> FUN_0003a382 (r13)"),
    (0x3B672, 0x24 | (0x4F << 8), "FUN_0003b66a -> damping+boost Factor-A (r9)"),
]
# ---- V52 delta #3: the live raw gp-0x4f60 reads V50 MISSED, in FUN_0002eda8. The tracer + a byte-exact
# read_memory found THREE `ld.h -0x4f60[gp],r7` sites -- a 3-way MUTUALLY-EXCLUSIVE branch (post-hold /
# zero-init paths) that all converge at 0x2F342, so ALL THREE must be repointed. All r7 -> word1 0x3F24
# (= 0x24 | (0x3F<<8), high byte (7<<3)|7=0x3F), same disp16-only edit as the 7 base sites. These feed
# gp-0x6b6c -> FUN_000339cc -> base-assist lane/channel 9 (a live command-path lane, no dormancy gate).
# Monitor-safety: the channel-9 DTC-0x1d check derives BOTH legs from gp-0x6b6c/6b6a in the same cycle
# (shared-input, no raw-vs-filtered divergence -- same pattern validated for the V48B 0x1c/0x1d pair);
# corroborated by a raw byte-scan of gp-0x6b6c/6b6a readers+writers (see the handoff for the 0x4FFD0
# reader resolution). FUN_0002ec52 (diagnostic, ~100Hz task) is deliberately LEFT RAW.
EXTRA_REPOINTS = [
    (0x2F318, 0x24 | (0x3F << 8), "FUN_0002eda8 gp-0x4f60 raw read, branch A (r7)"),
    (0x2F330, 0x24 | (0x3F << 8), "FUN_0002eda8 gp-0x4f60 raw read, branch B (r7)"),
    (0x2F33E, 0x24 | (0x3F << 8), "FUN_0002eda8 gp-0x4f60 raw read, branch C (r7)"),
]
# ---- V52C delta: the BROAD carrier set. A definitive raw byte-scan of the V38 image found 69
# gp-relative gp-0x4f60 accesses (64 ld.h + 5 st.h) -- NOT the ~12 the V50/V52 model assumed. Every
# word1 below was read from the image, NOT taken from the handoff: the handoff's "word1" column used a
# nominal reg<<8 notation (e.g. "0x0C24" for r12) which is NOT the real encoding and would have
# corrupted 9 instructions. Real encoding is w1 = (reg2<<11)|(0x39<<5)|4 = (reg2<<11)|0x724.
# The repoint edits ONLY the disp16 halfword at addr+2 (0xB0A0 -> 0xED00), so it is register-agnostic;
# the register is recorded to assert the site has not moved.
BROAD_REPOINTS = [
    (0x29A90, 0x24 | (0x67 << 8), "FUN_00028ea6 arbitration LERP curve select (r12)"),
    (0x2B69E, 0x24 | (0xCF << 8), "FUN_0002b62c -> gp-0x6aea EMA/corridor blend (r25)"),
    (0x2DF32, 0x24 | (0x17 << 8), "FUN_0002db94 -> gp-0x6b1a LERP boost/damping blend (r2)"),
    (0x33D2A, 0x24 | (0x17 << 8), "FUN_00033d10 -> gp-0x6b78 float PID controller (r2)"),
    (0x3F8E2, 0x24 | (0x5F << 8), "FUN_0003f884 -> gp-0x6a0a angle integrator (r11)"),
    (0x3FCC6, 0x24 | (0x3F << 8), "FUN_0003fc16 -> gp-0x6a0a (r7)"),
    # --- the 3 lanes the prior handoff called "self-filtering". OPERATOR DIRECTIVE: repoint EVERY
    # command-path carrier, not only the ones with the largest individual benefit.
    #
    # RATIONALE (and it is better than the per-lane cost/benefit reasoning it replaced): a MIXED
    # raw/filtered population is itself the hazard. Any self-consistency, dual-path, lockstep or
    # mirror check that straddles the split would see a divergence that does not exist today. This
    # kit's V27 brick was caused by exactly that -- ASYMMETRY, not magnitude (a float twin scaled
    # wholesale against an int corridor scaled partially -> "divergence ~ FULL torque"). Filtering
    # every carrier keeps all downstream derived quantities on a single consistent basis.
    #
    # It is ALSO the most stable configuration measured: GATE-2's fine sweep is monotonic in the
    # filtered fraction, and f=19/19 is the best row tested (worst_re 0.189/0.193, stability edge
    # 21.2x/20.8x) vs 14.1x/16.6x at 16/19 and 4.66x/6.34x for stock V38. The cascade concern for
    # 0x36682 is covered: GATE-2 swept an existing pole as low as fc2=2 Hz and stayed stable
    # (worst_re 0.154-0.159, GM ~16 dB).
    #
    # Per-lane notes (measured, not inherited):
    #   0x36682 -- has a REAL terminal EMA, alpha=6/1024 (cal 0xC63D2, read from V38) -> fc 0.94 Hz.
    #              Contributes ~0.5% of the residual vector sum, so the benefit is small, but it is
    #              a command-path carrier and consistency is the governing criterion.
    #   0x36846 -- NOT an EMA (the handoff's label was wrong). Its gp-0x6b44 write is a cal-selected
    #              constant and the same load feeds a first-difference rate check raising DTC 0x23.
    #              DTC 0x23 is NOT hard-fault eligible (record[+8]=0x0000, verified twice), so the
    #              only consequence is a slightly desensitised secondary diagnostic. The primary
    #              sensor-health architecture (shadow lockstep gp-0x4486 -> fault 0x17, M1, M2,
    #              the 0x28F26 gate, and the FUN_0007f3f8 A/B cross-check) all still read RAW.
    #   0x3B908 -- a GENUINE carrier: its float biquad stage is degenerate in stock cal (coeffs
    #              0.0f), leaving two poles at ~366 Hz each (~236 Hz combined), so it passes 21 Hz
    #              nearly intact -- ~11.8% of the residual sum. Its single ld.h is REUSED 4
    #              instructions later by the validity gate (Ghidra-confirmed: 0x3b908 ld.h ->
    #              0x3b910 addi 0x6400,r9,r8 -> 0x3b914 cmp r16,r8 -> 0x3b916 bc, i.e.
    #              (x + 25600) < 51201). Repointing moves BOTH the gate and the filter input to the
    #              filtered copy, so the function stays internally self-consistent -- which is the
    #              point of the directive. The filtered copy is provably bounded by the same
    #              envelope as raw (the EMA never overshoots), so the gate cannot newly trip.
    (0x36682, 0x24 | (0x5F << 8), "FUN_00036682 -> gp-0x6b46, own EMA fc=0.94Hz (r11)"),
    (0x36846, 0x24 | (0x77 << 8), "FUN_00036828 -> gp-0x6b44 + DTC-0x23 rate check (r14)"),
    (0x3B908, 0x24 | (0x4F << 8), "FUN_0003b8f6 -> gp-0x6bfc/6bf6/6c00 + its validity gate (r9)"),
]
REPOINT_SITES = BASE_REPOINTS + EXTRA_REPOINTS + BROAD_REPOINTS
DISP_4F60 = (-0x4F60) & 0xFFFF   # 0xB0A0

# ---- DELIBERATE EXCLUSIONS: command-region gp-0x4f60 readers that STAY RAW, each on evidence. -----
# These are NOT oversights. Repointing any of them was considered and rejected for the stated reason.
# The builder asserts they remain raw so a future edit cannot silently sweep them in.
LEAVE_RAW_CARRIERS = {
    # EMPTY BY OPERATOR DIRECTIVE: every command-path carrier of gp-0x4f60 is repointed, so that no
    # self-consistency / dual-path / lockstep check can straddle a raw-vs-filtered split. See the
    # rationale block in BROAD_REPOINTS. The only gp-0x4f60 reads left RAW are the health gates
    # (RAW_MONITOR_SITES) and the cal-gated dormant mux arms (DORMANT_SITES) below -- neither is a
    # carrier, and both compare against LITERAL constants, so they introduce no divergence.
}

# The three direct monitor/plausibility reads. Health gates MUST see the raw sensor.
RAW_MONITOR_SITES = {
    0x42C20: "M1 FUN_00042af8 int monitor (+/-25600 -> gp-0x6af8)",
    0x43EDA: "M2 FUN_00043e44 float monitor (IEEE double 25.0)",
    0x28F26: "FUN_00028ea6 plausibility gate (+/-25600) -- same function as repointed 0x29A90",
}

# ---- SAFETY: the damping OUTPUT CLAMP BOUND + float mirror (DTC-0x1d no-debounce trap) stay stock --
CLAMP_INT_STOCK = {
    0xD209C: (2, "clamp m10 header"), 0xD209E: (300, "clamp m10 X0"), 0xD20A0: (800, "clamp m10 X1"),
    0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "clamp m11 header"), 0xD20AA: (300, "clamp m11 X0"), 0xD20AC: (800, "clamp m11 X1"),
    0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x) -- UNTOUCHED"),
    0xC4120: (0x01, "type-8 slot-8 sum gate -- stock"),
    0xC6498: (0x01, "damping mode byte -- stock (0x34392 read dormant)"),
    0xC6499: (0x01, "boost mode byte -- stock (0x34ace read dormant)"),
    0xC67B8: (1024, "FUN_0003a382 uVar27 Y0 -- stock"),
    0xC6450: (1024, "FUN_0003a382 Stage A pole -- stock"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- stock"),
}
DORMANT_SITES = {0x34392: "FUN_00034350 damping (dormant)", 0x34ACE: "FUN_00034a72 boost (dormant)"}

MAIN_BLOCK = (0x13000, 0xC4FFC)
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
    halfword = struct.unpack_from("<H", code, address)[0]
    if (halfword >> 7) & 0xF != 0xB:
        return None
    cond = halfword & 0xF
    disp = (((halfword >> 11) & 0x1F) << 4) | (((halfword >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return cond, address + disp


def crc_block_map(code):
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


def u16(code, addr):
    return struct.unpack_from("<H", code, addr)[0]


def assert_cell_ok():
    """The single 16-bit EMA cell must be halfword-aligned, in disp16 range, and the V51P-cleared cell."""
    assert D_CELL % 2 == 0, f"D_CELL gp-0x{D_CELL:04X} must be halfword-aligned for ld.h/st.h"
    assert 0 < D_CELL <= 0x8000, "gp displacement out of disp16 range"
    assert D_CELL == 0x1300, "V52 uses the V51P-probe-cleared gp-0x1300 cell; change deliberately if moved"


def assert_repoints_sane():
    """16 repoint sites (7 base + 3 FUN_0002eda8 + 6 broad), all distinct, in MAIN_BLOCK, and
    provably disjoint from the sites that must stay RAW."""
    assert len(EXTRA_REPOINTS) == 3, (
        "V52C requires the 3 FUN_0002eda8 branch repoints (0x2F318/0x2F330/0x2F33E) -- see the tracer")
    assert len(BROAD_REPOINTS) == 9, f"expected 9 broad repoints, have {len(BROAD_REPOINTS)}"
    assert len(REPOINT_SITES) == 19, f"expected 19 repoint sites, have {len(REPOINT_SITES)}"
    addrs = [a for a, _w, _n in REPOINT_SITES]
    assert len(set(addrs)) == len(addrs), "duplicate repoint site address"
    for a, _w, _n in REPOINT_SITES:
        assert MAIN_BLOCK[0] <= a < MAIN_BLOCK[1], f"repoint 0x{a:05X} outside MAIN block"
    # A repoint site may never coincide with a monitor, a dormant mux arm, or a deliberate exclusion.
    must_stay_raw = set(RAW_MONITOR_SITES) | set(LEAVE_RAW_CARRIERS) | set(DORMANT_SITES)
    overlap = set(addrs) & must_stay_raw
    assert not overlap, f"repoint set collides with must-stay-raw sites: {[hex(a) for a in overlap]}"


def assert_clamp_stock(code, label):
    for addr, (value, note) in CLAMP_INT_STOCK.items():
        assert u16(code, addr) == value, f"{label}: clamp bound 0x{addr:05X} moved ({note})"
    assert bytes(code[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, \
        f"{label}: clamp float mirror moved (DTC-0x1d trap)"


def assert_repoint_sites_stock(code):
    for addr, w1, note in REPOINT_SITES:
        assert u16(code, addr) == w1, f"repoint site 0x{addr:05X} opcode/reg word moved ({note})"
        assert u16(code, addr + 2) == DISP_4F60, f"repoint site 0x{addr:05X} disp not stock ({note})"
    for addr, note in DORMANT_SITES.items():
        assert u16(code, addr + 2) == DISP_4F60, f"dormant site 0x{addr:05X} disp moved ({note})"


def assert_raw_sites_untouched(code, label):
    """The monitors, the dormant mux arms and the deliberate exclusions must ALL still read raw
    gp-0x4f60. Health gates belong on the raw sensor; a silent sweep of one of these is exactly the
    V27-class raw-vs-filtered asymmetry that bricks an ECU."""
    for group, why in ((RAW_MONITOR_SITES, "MONITOR"), (LEAVE_RAW_CARRIERS, "DELIBERATE EXCLUSION"),
                       (DORMANT_SITES, "DORMANT MUX ARM")):
        for addr, note in group.items():
            assert u16(code, addr + 2) == DISP_4F60, \
                f"{label}: {why} site 0x{addr:05X} no longer reads raw gp-0x4f60 ({note})"


def assert_v38_baseline(code, cave_bytes):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, "0x454FE is not the stock bne"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET)
    assert bytes(code[HOOK:HOOK + 4]) == HOOK_STOCK, "0x7FEAC not stock cmp/mov"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == b"\xff" * len(cave_bytes), \
        "cave region not all-0xFF -- baseline must be V38"
    assert bytes(code[CAVE_BASE + len(cave_bytes):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(cave_bytes)), "cave tail not 0xFF"
    assert_repoint_sites_stock(code)
    assert_clamp_stock(code, "V38 baseline")
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address in (0xC4120, 0xC6498, 0xC6499) else u16(code, address)
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"


def build():
    assert_cell_ok()
    assert_repoints_sane()
    disp_out = gp_field(D_CELL)

    baseline = bytearray(open(V38_PLAIN, "rb").read())
    cave_bytes, cave_ann = assemble_cave(d_cell=D_CELL)
    assert_v38_baseline(baseline, cave_bytes)
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
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)

    print("  CHANGE 1 (CODE, 1 byte) -- state-4 ratchet fix:")
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET)
    assert code[RATCHET_ADDR + 1] == baseline[RATCHET_ADDR + 1]
    print(f"    0x{RATCHET_ADDR:05X}: bne -> br 0x{RATCHET_TARGET:05X}")

    print(f"  CHANGE 2 (CODE, {len(cave_bytes)} bytes) -- EMA low-pass cave @0x{CAVE_BASE:05X} "
          f"(gp-0x{D_CELL:04X}, round-to-nearest):")
    code[CAVE_BASE:CAVE_BASE + len(cave_bytes)] = cave_bytes
    print(f"    [0x{CAVE_BASE:05X},0x{CAVE_BASE + len(cave_bytes):05X})  {len(cave_ann)} instrs")

    print(f"  CHANGE 3 (CODE, 4 bytes) -- trampoline @0x{HOOK:05X}:")
    tramp = jr(CAVE_BASE, HOOK)
    code[HOOK:HOOK + 4] = tramp
    print(f"    0x{HOOK:05X}: {HOOK_STOCK.hex()} -> {tramp.hex()}   jr 0x{CAVE_BASE:05X}")

    print(f"  CHANGE 4 (CODE, {len(REPOINT_SITES)} x 2 bytes) -- repoint live carriers "
          f"gp-0x4f60 -> gp-0x{D_CELL:04X}:")
    for addr, w1, note in REPOINT_SITES:
        assert u16(code, addr) == w1 and u16(code, addr + 2) == DISP_4F60
        struct.pack_into("<H", code, addr + 2, disp_out)
        assert u16(code, addr + 2) == disp_out and u16(code, addr) == w1
        print(f"    0x{addr:05X}: disp {DISP_4F60:#06x} -> {disp_out:#06x}   {note}")

    assert_clamp_stock(code, "V52C")
    assert_raw_sites_untouched(code, "V52C")
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address in (0xC4120, 0xC6498, 0xC6499) else u16(code, address)
        assert got == value, f"0x{address:05X} moved ({note})"

    for addr in (RATCHET_ADDR, CAVE_BASE, CAVE_BASE + len(cave_bytes) - 1, HOOK):
        assert owning_block(code, addr) == MAIN_BLOCK
    for addr, _w, _n in REPOINT_SITES:
        assert owning_block(code, addr) == MAIN_BLOCK
    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    diffs, runs = changed_runs(baseline, code)
    allowed = {RATCHET_ADDR}
    allowed.update(range(CAVE_BASE, CAVE_BASE + len(cave_bytes)))
    allowed.update(range(HOOK, HOOK + 4))
    for addr, _w, _n in REPOINT_SITES:
        allowed.update({addr + 2, addr + 3})
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    assert set(diffs) <= allowed, f"unexpected V52-vs-V38 bytes: {sorted(set(diffs) - allowed)}"

    crc_bytes = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    intended = {RATCHET_ADDR} | set(range(CAVE_BASE, CAVE_BASE + len(cave_bytes))) | set(range(HOOK, HOOK + 4))
    for addr, _w, _n in REPOINT_SITES:
        intended.update({addr + 2, addr + 3})
    non_crc = set(diffs) - crc_bytes
    assert non_crc <= intended, f"unexpected non-CRC diffs: {sorted(non_crc - intended)}"
    for b in intended - non_crc:
        assert CAVE_BASE <= b < CAVE_BASE + len(cave_bytes) and cave_bytes[b - CAVE_BASE] == 0xFF, \
            f"intended edit at 0x{b:05X} did not land and is not a 0xFF cave byte"

    assert_crc_chain(code, "V52 plain")
    assert walk(bytes(code), label="V52") == 0
    assert walk_all_blocks(bytes(code), label="V52") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V52 emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V52 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V52 RWD readback")
    assert walk(readback, label="V52 RWD readback") == 0
    assert walk_all_blocks(readback, label="V52 RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), "ratchet lost in RWD"
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == cave_bytes, "cave lost in RWD"
    assert bytes(readback[HOOK:HOOK + 4]) == tramp, "trampoline lost in RWD"
    for addr, w1, _n in REPOINT_SITES:
        assert u16(readback, addr) == w1 and u16(readback, addr + 2) == disp_out, "repoint lost in RWD"
    assert_raw_sites_untouched(readback, "V52C RWD readback")
    assert_clamp_stock(readback, "V52C RWD readback")
    assert u16(readback, 0xC646C) == 3564, "4x forward gain not preserved in RWD readback"

    print(f"\n  V52-vs-V38: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "CHANGE 1: state-4 ratchet branch nibble"
        elif first == HOOK:
            kind = "CHANGE 3: trampoline jr -> cave"
        elif CAVE_BASE <= first < CAVE_BASE + len(cave_bytes):
            kind = "CHANGE 2: EMA low-pass cave (gp-0x1300, round-to-nearest)"
        elif any(first == a + 2 for a, _w, _n in REPOINT_SITES):
            kind = "CHANGE 4: carrier repoint (disp16)"
        elif MAIN_BLOCK[1] <= first < MAIN_BLOCK[1] + 4:
            kind = "CRC trailer (MAIN)"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:  {V38_SHA256}")
    print(f"  V52 SHA-256:  {hashlib.sha256(code).hexdigest()}")
    print(f"  V52 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd, cave_ann


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V52C-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V52_OUT)]
    for path in stale + [V52_OUT, BIN_OUT, V52_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V52 = V50 EMA low-pass MADE FLASHABLE: gp-0x1500 -> gp-0x1300 (V51P-cleared), round-to-nearest,")
    print("      8th repoint (FUN_0002eda8). Keeps 4x + the confirmed state-4 ratchet fix.")
    print("  CHANGE 1 (CODE, 1 byte)     0x454FE  bne -> br            (ratchet fix, carried)")
    print(f"  CHANGE 2 (CODE, EMA cave)   0x{CAVE_BASE:05X}  low-pass alpha=74/1024 + round-to-nearest")
    print(f"  CHANGE 3 (CODE, 4 bytes)    0x{HOOK:05X}  jr -> cave           (trampoline)")
    print(f"  CHANGE 4 (CODE, {len(REPOINT_SITES)}x2 bytes)  repoint live carriers gp-0x4f60 -> gp-0x1300")
    print("  UNTOUCHED: raw gp-0x4f60/shadow, monitors, CAN, 0xC646C=3564 (4x), clamp trap.\n")
    code, rwd, cave_ann = build()

    os.makedirs(os.path.dirname(V52_OUT), exist_ok=True)
    with open(V52_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V52_OUT + ".tmp", V52_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V52_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  *** CODE CAVE -- NOT FLASHED. *** Ghidra-re-disassemble the built image (cave+hook+8 repoints),")
    print("  run the adversarial pre-flash review, then flash only on explicit operator file+bus instruction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
