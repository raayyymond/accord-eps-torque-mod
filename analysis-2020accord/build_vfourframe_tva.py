"""
build_vfourframe_tva.py -- FOURFRAME = V38 + a FOUR-FRAME passive READ-ONLY CAN telemetry code cave.
EXTENDS the kit's first active-CAN-TX cave (build_vcantx_test_tva.py, mailbox 16 -> new ID 0x555, a fixed
8-byte magic payload) from 1 frame to 4: mailboxes 16-19 -> new IDs 0x6A0-0x6A3, each carrying 4 live
gp-relative RAM signals (torque/command/shaper cells) as big-endian s16 pairs, 62.5 Hz. STUDY ARTIFACT.
UNFLASHED. Do NOT flash. Do NOT send CAN.

⚠ ELEVATED RISK CLASS (unchanged from the single-frame seed, now 4x the bus load): this cave shares the
    PHYSICAL BUS that carries STEER_STATUS/torque-sensor frames. Correctness of the CAN-controller register
    programming sequence -- not the payload content -- is the entire safety question, same as the seed.
    Unlike the seed's FIXED magic payload, this build's payload is READ from live RAM every cycle -- but
    every read is `ld.hu` (load only, never a store) into a scratch register that is immediately written to
    a NEW hardware mailbox's DAT register, never back into firmware RAM. It does not touch, read-modify-
    write, or in any way alter gp-0x4f60, the aggregator, the governor, the damper, or any torque-shaping
    cell -- it only OBSERVES them. Four extra 8-byte/11-bit-ID frames at 62.5 Hz add ~4*108*62.5 ~= 27 kbps
    of bus traffic (~5% of a 500 kbps bus) -- not zero, but small, and quantified here rather than asserted.

PURPOSE
    16 gp-relative RAM cells spanning the LKAS/base-assist demand aggregator, the shaper/governor chain, and
    the raw Sensor-B (TAS) torque path -- signals this kit's V44-V51 investigation has repeatedly needed
    live values for and could previously only get via CAN-330 spare-bit piggybacking (1-2 bits/cycle) or a
    UDS poll that is unreachable during LKAS (comma OBD-mux contention, see
    memory/comma4-eps-uds-poll-comma-vs-redpanda.md). Four dedicated 8-byte frames give full-resolution
    16-bit telemetry on all 16 cells simultaneously, every packer cycle.

★ SIGNAL PROVENANCE -- every gp-offset below is grounded against `eps_lkas_chain_model.py` (the kit's live
    golden reference), not re-derived here. Two of the sixteen have a DATA-QUALITY CAVEAT the operator
    should know before wiring up a decoder -- both are still SAFE to read (pure RAM loads), the caveat is
    about what the channel will actually show, not about risk:
      - gp-0x6ade (frame 0x6A2, byte6/7): eps_lkas_chain_model.py:1669/1755 -- "gp-0x6ade (DEAD -- read
        @0x3aa48, ZERO writers image-wide)". This channel will telemeter whatever stale/never-written value
        sits at that RAM address at boot and is NOT expected to vary. Included because the mission asked for
        it (labelled "feedforward" there); flagged here so it is not mistaken for a live feedforward signal.
      - gp-0x67ac (frame 0x6A3, byte6/7): eps_lkas_chain_model.py:1721-1727 -- confirmed (byte-level,
        2026-07-19) that gp-0x61a0's 11-entry source-type array on the A160 is (0,0,5,0,5,5,0,0,0,5,0), so
        the fold that would set gp-0x67ac=1 (REDUCED aggregator mode) can never trigger -- gp-0x67ac reads
        0 every cycle on THIS firmware. It DOES have a real per-cycle writer (unlike gp-0x6ade), so it is
        legitimate live telemetry -- it is just proven-constant on the A160, useful as a confirmatory
        channel (a nonzero reading would itself be diagnostic) rather than a varying "suppression gate".
    The other 14 are live, actively-written cells with no such caveat (see the per-frame table below).

TECHNIQUE (verbatim reuse of build_vcantx_test_tva.py's harness + encoders; only the cave BODY is new)
    HOOK: UNCHANGED -- site 0x55C0E `movea -0x1518,gp,r6` (CAN-330 packer FUN_00055a98's own pack-buffer-
    base setup) -> `jarl cave,lp`, re-exec the displaced movea last, `jmp [lp]` returns to 0x55C12. Same
    62.5 Hz cadence as CAN 330 itself -- no extra divider needed, same as the seed.

    MAILBOXES 16-19 -- CONFIRMED FREE, re-verified THIS session by TWO independent methods (stronger than
    the seed's mailbox-16-only check, because this session found a POOL-WIDE result covering all four):
      1. `.claude/agent-memory/firmware-codepath-tracer/reference_accord_can_mailbox_boot_init_fun1cf30_free_pool.md`
         (2026-07-24): the boot-time FCN0 init routine `FUN_0001cf30` explicitly zeroes STRB for mailbox
         indices 7-31 as a genuine free/inert pool -- "no ID or DLC written at all... left at HW power-on-
         reset". Mailboxes 16-19 are all inside this range (the seed's mailbox-16 3-method check was the
         single-index special case of this same pool).
      2. Zero xrefs, all program-wide, to every one of the STRB/MID0W/CTL register addresses for mailboxes
         17, 18, 19 (`get_xrefs_to` on 0xFF481464/0xFF4814A4/0xFF4814E4 [STRB], 0xFF491468/0xFF4914A8/
         0xFF4914E8 [MID0W], 0xFF489478/0xFF4894B8/0xFF4894F8 [CTL] -- all nine returned "No references
         found", confirmed live this session via GhidraMCP on code.bin). Mailbox 16's own four addresses
         were already re-confirmed zero-xref in the seed's own memory citation.
      Per-mailbox register map, confirmed stride 0x40 (matches mailbox 16's own already-verified constants
      exactly, formula cross-checked against STRB16/DTLGB16/MID0W16/CTL16/DAT_BASE16 in the seed):
        STRB(n)  = 0xFF481024 + n*0x40      DTLGB(n) = 0xFF481020 + n*0x40
        MID0W(n) = 0xFF491028 + n*0x40      CTL(n)   = 0xFF489038 + n*0x40
        DAT_BASE(n) = 0xFF481000 + n*0x40   (DAT0..7B(n) = DAT_BASE(n) + 4*i, i=0..7)

    GATE 1 -- gp-0x1712 bit0, TX-ready interlock (VERBATIM reuse of the seed's gate, unchanged mechanism):
        ld.bu -0x1712[gp],r12 ; shr 0x1,r12 ; [bit0->CY] ; not-ready(CY=0) -> long-jump to SKIP.

    GATE 2 -- DAT_ff48024c bit4, NEW this build. Disassembled + decompiled `FUN_0001d68e` in full this
        session (the real emitter, entry `0x1d68e`). Its OWN first branch on entry is exactly this check:
            0001d6aa: movhi -0xb8,r0,r6      ; r6 = 0xFF480000
            0001d6ae: ld.bu 0x24c,r6,r6      ; r6 = byte[0xFF48024C]  (DAT_ff48024c)
            0001d6b2: shr 0x4,r6             ; )
            0001d6b4: shr 0x1,r6             ; ) combined: CY = bit4 of DAT_ff48024c
            0001d6b6: bnc 0x0001d6cc         ; bit4 CLEAR (CY=0) -> take the REAL branch (arm+fire mailbox)
        Ghidra's decompiler independently confirms the polarity: `if ((DAT_ff48024c >> 4 & 1) == 0) { ...
        real STRB/MID0W/DAT/CTL logic... } else { table[idx]=0xFFFF; return 0; }` -- i.e. bit4 SET aborts
        (writes a "reclaim" sentinel and returns without touching hardware), bit4 CLEAR proceeds. This
        cave's gate 2 LITERALLY REUSES the real movhi+ld.bu bytes (`403648ff`+`86374d02`, targeting r6,
        re-disassembled this session, see ENCODING VERIFICATION) -- not hand-derived -- then re-applies the
        same shr 0x4/shr 0x1 reduction (already a proven encoder, see below) and inverts only the BRANCH
        (this cave needs "bit4 set -> skip", the mirror of stock's "bit4 clear -> proceed"; same bit test,
        opposite consumer, because stock's own abort path and this cave's SKIP path are different code).

    ★ LONG-RANGE SKIP -- both gates in the seed used a single 2-byte `bnc SKIP` because SKIP (the epilogue)
    was <256 bytes away. This cave's body is ~700 bytes (4 mailboxes vs 1), putting SKIP outside Bcond's
    +/-254-byte range. Standard short-branch-over-long-jump idiom, no new opcode class: each gate is
    `Bcond PAST` (2B, taken when "proceed") ; `jr SKIP` (4B, taken when "abort", 22-bit range, formula
    verified against a real code.bin instance this session -- see ENCODING VERIFICATION) ; `PAST:`. Gate 1
    uses `bc PAST1` (ready=CY=1 skips the jr); gate 2 uses `bnc PAST2` (bit4-clear=CY=0 skips the jr) --
    each is the SAME polarity as the seed's original single bnc, just indirected through one extra
    unconditional long jump when the gate says "not ready" (a rarer path than "ready").

    PER-SIGNAL READ+WRITE (16x, all identical shape, all pure RAM READS):
        ld.hu -disp[gp],r7        ; r7 = raw 16-bit cell value, zero-extended (sign irrelevant -- only the
                                   ; raw 16 bits are ever placed on the wire, see below)
        mov &DAT_lo,r6 ; st.b r7,0x0[r6]     ; DAT[lo] = r7 & 0xFF        (low byte)
        shr 0x8,r7                           ; r7 >>= 8 (now 0-255, the high byte)
        mov &DAT_hi,r6 ; st.b r7,0x0[r6]     ; DAT[hi] = r7 & 0xFF        (high byte)
    `ld.hu` (zero-extend) is used rather than a signed `ld.h` deliberately: the cave never does arithmetic
    on the value, only splits it into two bytes for the wire, so sign-extension of the unused upper 16 bits
    of the 32-bit register is irrelevant -- both loads would produce byte-identical DAT writes. This lets
    the cave reuse the SAME `ld.hu` encoder already Ghidra-verified against 4 real code.bin instances in
    build_v51probe_tva.py (op=0x3F, `field=((-disp)&0xFFFE)|1`), rather than deriving a new LD.H form.
    Per-mailbox di/ei scoping (matches the seed and stock FUN_0001d68e exactly): each mailbox's own 4-signal
    read+write block is wrapped in its OWN di/ei pair, not one di/ei spanning all 4 mailboxes -- keeps each
    interrupt-disable window to ~voltage of one mailbox's payload only (~100 bytes of instructions), not 4x.

    REGISTER SET -- SMALLER than the seed's (r6/r7/r8/r9/r12): this build needs only R6 (address scratch,
    reused ~50x/build), R7 (value scratch -- constants during config writes, the loaded signal value during
    payload writes), and R12 (gate-1 byte). R8/R9 are NOT needed because, unlike the seed's fixed A5/5A
    payload (which needed two pre-built constant registers reused across 8 DAT writes), this build's payload
    is read fresh per-signal into R7 and fully consumed (both bytes written) before the next signal's read
    overwrites it -- one value register suffices. Saved/restored via a 12-byte stack frame (3 registers vs
    the seed's 20-byte/5-register frame), same discipline: full round-trip through the stack on every path,
    not "dead at return" reasoning; identical whether either gate takes its SKIP branch or the cave runs the
    entire 4-mailbox body.

ENCODING VERIFICATION -- every encoder is EITHER (a) verbatim-reused from build_vcantx_test_tva.py or
    build_v51probe_tva.py, already Ghidra/byte-verified there (mov32, movea, movi5, stb, sth, stw, ldw, addi,
    shr, bcond/bnc/bc, DI, EI, JMP_LP, the gp-relative ld.hu formula), OR (b) newly added THIS session and
    verified below:
      GATE 2 movhi+ld.bu (8B literal): re-disassembled 0x1d6aa-0x1d6b1 on code.bin via GhidraMCP this
          session -- `movhi -0xb8,r0,r6` = `403648ff`, `ld.bu 0x24c,r6,r6` = `86374d02`. Reused verbatim,
          matching this build's own need (r6 destination, same absolute address) exactly -- no adaptation.
      SHR (0x4 and 0x1 on r6, gate 2's bit-4 reduction): the seed's shr() formula (op=0x14) was already
          verified against 2 real instances (shr 0x1,r16 / shr 0x2,r2); this session's OWN re-disassembly of
          FUN_0001d68e's gate (0x1d6b2/0x1d6b4, `shr 0x4,r6`=`8432`, `shr 0x1,r6`=`8132`) reproduces the
          SAME formula exactly for a 3rd/4th register+immediate combination -- independent corroboration,
          not a new derivation.
      JR (long-range unconditional jump, 4B, NEW this session): derived from FUN_0001d68e's own
          `jr 0x1d82a` at `0x1d6c8` (bytes `80076201`, disassembled this session): word0 = 0x0780 |
          ((disp>>16)&0x3F), word1 = disp&0xFFFF, disp=(target-pc)&0x3FFFFF -- the SAME 22-bit-disp shape as
          the already-proven `jarl_lp` encoder (0xFF80 fixed bits instead of JR's 0x0780; JARL links lp,
          JR does not). Verified: jr(0x1d82a, 0x1d6c8).hex() == "80076201" exactly reproduces the real
          instance, including both halfwords.
      BC (0x1, "branch if carry" -- the mirror of the seed's already-solved/54-real-instance-validated BNC):
          same Bcond formula, same fixed marker bits, only `cond` differs (0x1 vs 0x9); the seed's own
          self-check already includes a real `bc disp=+6 @0x2fc` instance (`bcond(COND_BC,+6)=="b105"`) --
          this build's own bc1 disp is ALSO +6 (fixed by construction: 2B bcond + 4B jr = 6), so the exact
          same real-instance byte match applies without adaptation.
      MAILBOX 17-19 register addresses: formula cross-checked against mailbox 16's OWN already-Ghidra-
          verified constants (STRB16 etc.) at n=16, then re-verified zero-xref for n=17,18,19 individually
          this session (see MAILBOXES 16-19 section above).
    The full built cave was re-disassembled from the WRITTEN image via GhidraMCP before this build was
    reported done (kit rule for any cave, no exceptions) -- see the session's verification pass.

SAFETY: STUDY ARTIFACT. UNFLASHED. Do NOT flash. Do NOT transmit CAN. Flash only on explicit operator
    instruction naming file + bus.
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("FOURFRAME builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
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

TAG = "newid0x6a0-0x6a3-mbx16-19-fcn0-62p5hz-4x4signal16bRAMtelemetry-dualgate-caveC4B34-onV38"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-FOURFRAME-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_vfourframe_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

CAVE_BASE = 0xC4B34
HOOK_ADDR = 0x55C0E
HOOK_STOCK = bytes.fromhex("2436e8ea")   # movea -0x1518,gp,r6

MAIN_BLOCK = (0x13000, 0xC4FFC)
EXPECTED_BLOCKS = 50
CAVE_HARD_LIMIT = 0xC4FF0   # cave must end at or before this (matches the seed's reserved tail)

# -------------------------------------------------------------------------------------------------------
# V850E2 mini-assembler -- encoders verbatim-reused from build_vcantx_test_tva.py / build_v51probe_tva.py
# unless marked NEW (see module docstring ENCODING VERIFICATION for every citation).
# -------------------------------------------------------------------------------------------------------

R0, SP, GP = 0, 3, 4
R6, R7, R12 = 6, 7, 12
EP, LP = 30, 31


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def _fmt1(op, reg1, reg2):
    assert 0 <= op <= 0x3F and 0 <= reg1 <= 31 and 0 <= reg2 <= 31
    return _le16((reg2 << 11) | (op << 5) | reg1)


def mov32(imm32, reg2):
    """MOV imm32,reg2 -- V850E2-native 48-bit form. Verbatim from build_vcantx_test_tva.py."""
    assert 0 <= imm32 <= 0xFFFFFFFF and 0 <= reg2 <= 31
    return bytes([0x20 | reg2, 0x06]) + _le16(imm32 & 0xFFFF) + _le16((imm32 >> 16) & 0xFFFF)


def movea(imm16, reg1, reg2):
    assert 0 <= imm16 <= 0xFFFF
    return _fmt1(0x31, reg1, reg2) + _le16(imm16)


def movi5(imm5, reg2):
    assert -16 <= imm5 <= 15
    return _fmt1(0x10, imm5 & 0x1F, reg2)


def stb(src, disp, base):
    assert -0x8000 <= disp <= 0x7FFF
    return _fmt1(0x3A, base, src) + _le16(disp & 0xFFFF)


def sth(src, disp, base):
    assert -0x8000 <= disp <= 0x7FFF and disp % 2 == 0
    return _fmt1(0x3B, base, src) + _le16(disp & 0xFFFF)


def stw(src, disp, base):
    assert -0x8000 <= disp <= 0x7FFE and disp % 2 == 0
    return _fmt1(0x3B, base, src) + _le16(((disp & 0xFFFE) | 1) & 0xFFFF)


def ldw(base, disp, dst):
    assert -0x8000 <= disp <= 0x7FFE and disp % 2 == 0
    return _fmt1(0x39, base, dst) + _le16(((disp & 0xFFFE) | 1) & 0xFFFF)


def addi(imm16, reg1, reg2):
    return _fmt1(0x30, reg1, reg2) + _le16(imm16 & 0xFFFF)


def shr(imm5, reg2):
    assert 0 <= imm5 <= 31
    return _fmt1(0x14, imm5, reg2)


def _gp_field_load(disp_neg):
    """Verbatim from build_v51probe_tva.py: gp-relative disp16 field for the ld.hu W/H-selector form."""
    assert 0 < disp_neg <= 0x8000
    return ((0x10000 - disp_neg) & 0xFFFE) | 1


def ldhu(disp_neg, reg2, reg1=GP):
    """LD.HU -disp_neg[reg1],reg2 (op=0x3F). Verbatim formula from build_v51probe_tva.py, cross-checked
    there against 4 real gp-relative code.bin instances spanning 4 different destination registers."""
    return _fmt1(0x3F, reg1, reg2) + _le16(_gp_field_load(disp_neg))


# Bcond -- verbatim from build_vcantx_test_tva.py, already cross-validated against 54 real code.bin
# instances (38 bc, 15 bnc, 1 bne) that session. disp is relative to the bcond instruction's OWN address.
_BCOND_FIXED = (1 << 7) | (1 << 8) | (0 << 9) | (1 << 10)
COND_BC, COND_BNC, COND_BE, COND_BNE = 0x1, 0x9, 0x2, 0xA


def bcond(cond, disp):
    assert 0 <= cond <= 0xF
    assert disp % 2 == 0, "branch displacement must be even (halfword-aligned target)"
    d2 = disp // 2
    assert -128 <= d2 <= 127, f"disp {disp} out of Bcond's 8-bit (d//2) range"
    d2u = d2 & 0xFF
    w = (cond & 0xF)
    w |= (d2u & 0x7) << 4
    w |= _BCOND_FIXED
    w |= ((d2u >> 3) & 0x1F) << 11
    return _le16(w)


def bnc(disp):
    return bcond(COND_BNC, disp)


def bc(disp):
    return bcond(COND_BC, disp)


def jr(target, pc):
    """JR target (unconditional, 22-bit-disp, 4B) -- NEW this session. Formula: word0 = 0x0780 |
    ((disp>>16)&0x3F), word1 = disp&0xFFFF -- same disp encoding as the already-proven jarl_lp, different
    fixed bits (0x0780 vs 0xFF80: JR doesn't link lp). Verified against real code.bin `jr 0x1d82a`@0x1d6c8."""
    disp = (target - pc) & 0x3FFFFF
    return _le16(0x0780 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


DI = bytes.fromhex("e0076001")
EI = bytes.fromhex("e0876001")
JMP_LP = bytes.fromhex("7f00")

# Gate 1 -- TX-ready gp-0x1712 bit0. LITERAL reuse of build_vcantx_test_tva.py's own literal reuse of the
# real FUN_0001d68e@0x1d7da bytes.
LD_BU_TXREADY_R12 = bytes.fromhex("a407e566d1ff")

# Gate 2 -- DAT_ff48024c bit4. LITERAL reuse of FUN_0001d68e@0x1d6aa-0x1d6b1, re-disassembled this session
# via GhidraMCP (movhi -0xb8,r0,r6 ; ld.bu 0x24c,r6,r6 -- both target r6, both usable unmodified here).
GATE2_MOVHI_R6 = bytes.fromhex("403648ff")
GATE2_LDBU_R6 = bytes.fromhex("86374d02")

# -------------------------------------------------------------------------------------------------------
# Mailbox register map (FCN0, stride 0x40) -- formula cross-checked against mailbox 16's own already-
# verified constants; re-verified zero-xref for 17/18/19 this session (see module docstring).
# -------------------------------------------------------------------------------------------------------


def strb_addr(n):
    return 0xFF481024 + n * 0x40


def dtlgb_addr(n):
    return 0xFF481020 + n * 0x40


def mid0w_addr(n):
    return 0xFF491028 + n * 0x40


def ctl_addr(n):
    return 0xFF489038 + n * 0x40


def dat_addr(n, i):
    assert 0 <= i <= 7
    return 0xFF481000 + n * 0x40 + 4 * i


# sanity: mailbox-16 formula must reproduce the seed's own already-verified constants exactly
assert strb_addr(16) == 0xFF481424
assert dtlgb_addr(16) == 0xFF481420
assert mid0w_addr(16) == 0xFF491428
assert ctl_addr(16) == 0xFF489438
assert dat_addr(16, 0) == 0xFF481400 and dat_addr(16, 7) == 0xFF48141C

# -------------------------------------------------------------------------------------------------------
# Four frames, four mailboxes, sixteen signals. See module docstring "SIGNAL PROVENANCE" for the
# gp-0x6ade / gp-0x67ac data-quality caveats (both safe to read; neither is expected to vary).
# -------------------------------------------------------------------------------------------------------

MAILBOXES = [
    dict(n=16, can_id=0x6A0, signals=[
        ("gp-0x6b98", 0x6b98, "delivered_cmd"),        # post-shaper command to the FOC loop
        ("gp-0x6acc", 0x6acc, "shaper_in"),             # shaper/integrator input
        ("gp-0x6ace", 0x6ace, "governor_out"),          # after governor clamp/Q15/slew
        ("gp-0x6b94", 0x6b94, "aggregator_sum"),        # LKAS+base-assist aggregator output
    ]),
    dict(n=17, can_id=0x6A1, signals=[
        ("gp-0x6b4c", 0x6b4c, "lkas_lane"),             # LKAS-internal lane into the aggregator
        ("gp-0x6ad4", 0x6ad4, "resonance_lane"),        # FUN_0003a382 unfiltered residual lane
        ("gp-0x6bd0", 0x6bd0, "damping"),               # FUN_00034350 base-assist viscous damping
        ("gp-0x6bbe", 0x6bbe, "boost"),                 # FUN_00034a72 boost/assist curve
    ]),
    dict(n=18, can_id=0x6A2, signals=[
        ("gp-0x6b86", 0x6b86, "magnitude"),             # FUN_000352b4 output
        ("gp-0x6b26", 0x6b26, "friction"),               # FUN_00036c12 curve x angle term
        ("gp-0x6b62", 0x6b62, "return_centre"),          # FUN_00036388 slow accumulator w/ hysteresis
        ("gp-0x6ade", 0x6ade, "feedforward_CAVEAT_DEAD"),   # see SIGNAL PROVENANCE: 0 writers image-wide
    ]),
    dict(n=19, can_id=0x6A3, signals=[
        ("gp-0x4f60", 0x4f60, "raw_sensorB_torque"),    # SENSOR-B (TAS) driver column torque
        ("gp-0x4f62", 0x4f62, "torque_rate"),           # 4-sample finite difference of Sensor-B torque
        ("gp-0x69a4", 0x69a4, "r26_gain_input"),        # r26 lane input; producer UNRESOLVED
        ("gp-0x67ac", 0x67ac, "aggreg_mode_CAVEAT_ALWAYS0"),  # see SIGNAL PROVENANCE: proven const 0 on A160
    ]),
]

for _mbx in MAILBOXES:
    assert len(_mbx["signals"]) == 4
    for _name, _disp, _label in _mbx["signals"]:
        assert 0 < _disp <= 0x8000, f"{_name} disp out of ld.hu gp-relative range"
    _mid0w_val = (_mbx["can_id"] << 18) & 0xFFFFFFFF
    assert (_mid0w_val >> 29) & 1 == 0, f"IDE bit must be 0 for mailbox {_mbx['n']} (0x{_mbx['can_id']:03X})"
    _mbx["mid0w_val"] = _mid0w_val

assert [m["n"] for m in MAILBOXES] == [16, 17, 18, 19]
assert [hex(m["can_id"]) for m in MAILBOXES] == ["0x6a0", "0x6a1", "0x6a2", "0x6a3"]
assert [hex(m["mid0w_val"]) for m in MAILBOXES] == ["0x1a800000", "0x1a840000", "0x1a880000", "0x1a8c0000"]


def build_cave():
    """Assemble fourframe_program_and_fire: save r6/r7/r12, gate on (1) gp-0x1712 bit0 TX-ready and
    (2) DAT_ff48024c bit4, then for each of 4 mailboxes program STRB/DTLGB/MID0W, read+pack 4 signals into
    DAT0..7B (di/ei-wrapped), and fire CTL 0x0100->0x0200; restore r6/r7/r12; re-execute the displaced hook
    instruction; return. Both gates skip the ENTIRE 4-mailbox body via a short-branch-over-long-jump (the
    body is far outside Bcond's +/-254B range). Returns (bytes, listing)."""
    prologue, gate1, gate2, body, epilogue, tail = [], [], [], [], [], []

    def emit(lst, b, comment):
        lst.append((b, comment))

    # ---- prologue: save r6/r7/r12 ----
    emit(prologue, addi(-0xC, SP, SP), "addi -0xc,sp,sp         ; sp -= 12")
    emit(prologue, stw(R6, 0x0, SP), "st.w r6,0x0[sp]")
    emit(prologue, stw(R7, 0x4, SP), "st.w r7,0x4[sp]")
    emit(prologue, stw(R12, 0x8, SP), "st.w r12,0x8[sp]")

    # ---- gate 1: gp-0x1712 bit0 (TX-ready). bc/jr appended after SKIP is known. ----
    emit(gate1, LD_BU_TXREADY_R12, "ld.bu -0x1712[gp],r12   ; r12 = TX-ready byte (literal reuse)")
    emit(gate1, shr(0x1, R12), "shr 0x1,r12              ; bit0 -> CY")

    # ---- gate 2: DAT_ff48024c bit4 (real FUN_0001d68e's own arm-eligibility check). bnc/jr appended after. ----
    emit(gate2, GATE2_MOVHI_R6, "movhi -0xb8,r0,r6       ; r6 = 0xFF480000 (literal reuse, FUN_0001d68e@0x1d6aa)")
    emit(gate2, GATE2_LDBU_R6, "ld.bu 0x24c,r6,r6       ; r6 = DAT_ff48024c (literal reuse, @0x1d6ae)")
    emit(gate2, shr(0x4, R6), "shr 0x4,r6               ; )")
    emit(gate2, shr(0x1, R6), "shr 0x1,r6               ; ) combined: CY = bit4 of DAT_ff48024c")

    # ---- body: 4 mailboxes ----
    for mbx in MAILBOXES:
        n, can_id, signals, mid0w_val = mbx["n"], mbx["can_id"], mbx["signals"], mbx["mid0w_val"]
        strb, dtlgb, mid0w, ctl = strb_addr(n), dtlgb_addr(n), mid0w_addr(n), ctl_addr(n)

        emit(body, mov32(strb, R6), f"mov 0x{strb:08X},r6    ; &STRB{n}")
        emit(body, movea(0x80, R0, R7), "movea 0x80,r0,r7        ; r7 = 0x80 (TX)")
        emit(body, stb(R7, 0x0, R6), f"st.b r7,0x0[r6]         ; STRB{n} = 0x80")

        emit(body, mov32(dtlgb, R6), f"mov 0x{dtlgb:08X},r6    ; &DTLGB{n}")
        emit(body, movi5(8, R7), "mov 0x8,r7               ; r7 = 8 (DLC)")
        emit(body, stb(R7, 0x0, R6), f"st.b r7,0x0[r6]         ; DTLGB{n} = 8")

        emit(body, mov32(mid0w, R6), f"mov 0x{mid0w:08X},r6    ; &MID0W{n}")
        emit(body, mov32(mid0w_val, R7), f"mov 0x{mid0w_val:08X},r7    ; r7 = 0x{can_id:03X}<<18 (IDE=0)")
        emit(body, stw(R7, 0x0, R6), f"st.w r7,0x0[r6]         ; MID0W{n} = 0x{can_id:03X}<<18")

        emit(body, DI, "di")
        for i, (name, disp, label) in enumerate(signals):
            lo_addr = dat_addr(n, 2 * i + 1)
            hi_addr = dat_addr(n, 2 * i)
            emit(body, ldhu(disp, R7), f"ld.hu -0x{disp:x}[gp],r7 ; r7 = {name} ({label})")
            emit(body, mov32(lo_addr, R6), f"mov 0x{lo_addr:08X},r6    ; &DAT{2*i+1}B{n}")
            emit(body, stb(R7, 0x0, R6), f"st.b r7,0x0[r6]         ; DAT{2*i+1}B{n} = lo({name})")
            emit(body, shr(0x8, R7), "shr 0x8,r7               ; r7 = hi byte")
            emit(body, mov32(hi_addr, R6), f"mov 0x{hi_addr:08X},r6    ; &DAT{2*i}B{n}")
            emit(body, stb(R7, 0x0, R6), f"st.b r7,0x0[r6]         ; DAT{2*i}B{n} = hi({name})")
        emit(body, EI, "ei")

        emit(body, mov32(ctl, R6), f"mov 0x{ctl:08X},r6    ; &CTL{n}")
        emit(body, movea(0x100, R0, R7), "movea 0x100,r0,r7       ; r7 = 0x0100 (SERY)")
        emit(body, sth(R7, 0x0, R6), f"st.h r7,0x0[r6]         ; CTL{n} = 0x0100")
        emit(body, movea(0x200, R0, R7), "movea 0x200,r0,r7       ; r7 = 0x0200 (CSETR)")
        emit(body, sth(R7, 0x0, R6), f"st.h r7,0x0[r6]         ; CTL{n} = 0x0200  <-- TX FIRE ID 0x{can_id:03X}")

    # ---- epilogue: restore r6/r7/r12 (the SKIP target for both gates) ----
    emit(epilogue, ldw(SP, 0x0, R6), "ld.w 0x0[sp],r6")
    emit(epilogue, ldw(SP, 0x4, R7), "ld.w 0x4[sp],r7")
    emit(epilogue, ldw(SP, 0x8, R12), "ld.w 0x8[sp],r12")
    emit(epilogue, addi(0xC, SP, SP), "addi 0xc,sp,sp          ; sp += 12")

    # ---- re-execute the displaced hook instruction, then return ----
    emit(tail, HOOK_STOCK, "movea -0x1518,gp,r6     ; displaced hook instruction, re-executed")
    emit(tail, JMP_LP, "jmp [lp]                 ; return to 0x55c12")

    # ---- resolve branch displacements now that every fixed-length chunk is known ----
    prologue_len = sum(len(b) for b, _ in prologue)
    gate1_partial_len = sum(len(b) for b, _ in gate1)   # ld.bu(6)+shr(2) = 8
    gate2_partial_len = sum(len(b) for b, _ in gate2)   # movhi(4)+ld.bu(4)+shr(2)+shr(2) = 12
    body_len = sum(len(b) for b, _ in body)
    epilogue_len = sum(len(b) for b, _ in epilogue)     # 16

    BRANCH_BLOCK_LEN = 6   # 2B bcond + 4B jr, both gates
    gate1_len = gate1_partial_len + BRANCH_BLOCK_LEN
    gate2_len = gate2_partial_len + BRANCH_BLOCK_LEN

    skip_offset = prologue_len + gate1_len + gate2_len + body_len   # epilogue's own offset = SKIP target
    skip_addr = CAVE_BASE + skip_offset

    bc1_addr = CAVE_BASE + prologue_len + gate1_partial_len
    jr1_addr = bc1_addr + 2
    past1_addr = jr1_addr + 4
    bc1_disp = past1_addr - bc1_addr
    assert bc1_disp == 6
    emit(gate1, bc(bc1_disp), f"bc PAST1                 ; disp=+{bc1_disp} (ready -> skip the long-jump)")
    emit(gate1, jr(skip_addr, jr1_addr),
         f"jr SKIP                  ; not-ready -> long-jump to epilogue (disp=+{skip_addr - jr1_addr})")

    bnc2_addr = CAVE_BASE + prologue_len + gate1_len + gate2_partial_len
    jr2_addr = bnc2_addr + 2
    past2_addr = jr2_addr + 4
    bnc2_disp = past2_addr - bnc2_addr
    assert bnc2_disp == 6
    emit(gate2, bnc(bnc2_disp), f"bnc PAST2                ; disp=+{bnc2_disp} (bit4 clear -> proceed, skip long-jump)")
    emit(gate2, jr(skip_addr, jr2_addr),
         f"jr SKIP                  ; bit4 set -> long-jump to epilogue (disp=+{skip_addr - jr2_addr})")

    chunks = prologue + gate1 + gate2 + body + epilogue + tail
    cave = b"".join(b for b, _ in chunks)

    # ---- sanity: re-locate both PAST/SKIP targets by walking the assembled bytes ----
    assert len(cave) == skip_offset + epilogue_len + sum(len(b) for b, _ in tail)
    assert cave[bc1_addr - CAVE_BASE:bc1_addr - CAVE_BASE + 2] == bc(bc1_disp), "bc1 bytes not where expected"
    assert cave[jr1_addr - CAVE_BASE:jr1_addr - CAVE_BASE + 4] == jr(skip_addr, jr1_addr), \
        "jr1 bytes not where expected"
    assert cave[bnc2_addr - CAVE_BASE:bnc2_addr - CAVE_BASE + 2] == bnc(bnc2_disp), "bnc2 bytes not where expected"
    assert cave[jr2_addr - CAVE_BASE:jr2_addr - CAVE_BASE + 4] == jr(skip_addr, jr2_addr), \
        "jr2 bytes not where expected"
    assert cave[skip_offset:skip_offset + len(epilogue[0][0])] == epilogue[0][0], \
        "SKIP target does not land on the first restore instruction"

    return cave, chunks


CAVE_BYTES, CAVE_LISTING = build_cave()


def jarl_lp(target, pc):
    disp = (target - pc) & 0x3FFFFF
    return _le16(0xFF80 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


def full_image(window):
    image = bytearray(b"\xff" * 0x100000)
    image[START:END] = window
    return bytes(image)


def assert_x31_checksum(raw, label):
    stored = struct.unpack_from("<I", raw, len(raw) - 4)[0]
    calculated = sum(raw[:-4]) & 0xFFFFFFFF
    assert calculated == stored, f"{label} x31 checksum: 0x{calculated:08X} != 0x{stored:08X}"


def crc_block_map(code):
    start_page, num_pages = struct.unpack_from("<HH", code, END - 8)
    block_start, block_length = start_page << 12, (num_pages << 12) - 4
    blocks, visited = [], set()
    while True:
        assert block_start not in visited, f"CRC chain loop at 0x{block_start:X}"
        visited.add(block_start)
        trailer = block_start + block_length
        assert trailer + 4 <= len(code), f"block 0x{block_start:X} out of bounds"
        blocks.append((block_start, trailer))
        if block_start == START:
            break
        next_page, next_num_pages = struct.unpack_from("<HH", code, block_start - 8)
        block_start, block_length = next_page << 12, (next_num_pages << 12) - 4
        assert len(blocks) <= 200, "runaway CRC chain"
    return blocks


def assert_crc_chain(code, label):
    blocks = crc_block_map(code)
    for block_start, trailer in blocks:
        calc = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        stored = struct.unpack_from("<I", code, trailer)[0]
        assert calc == stored, f"{label}: CRC mismatch 0x{block_start:X}: 0x{calc:08X}!=0x{stored:08X}"
    assert len(blocks) == EXPECTED_BLOCKS, f"{label}: {len(blocks)} blocks != {EXPECTED_BLOCKS}"
    return len(blocks)


def changed_runs(before, after):
    diffs = [i for i in range(START, END) if before[i] != after[i]]
    runs = []
    for a in diffs:
        if runs and a == runs[-1][1] + 1:
            runs[-1][1] = a
        else:
            runs.append([a, a])
    return diffs, runs


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "hook site is not stock movea"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == b"\xff" * len(CAVE_BYTES), \
        "cave target is not all 0xFF -- refusing to overwrite"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)), "cave tail is not 0xFF"
    assert CAVE_BASE + len(CAVE_BYTES) <= CAVE_HARD_LIMIT, "cave overruns its free region"
    assert struct.unpack_from("<H", code, 0xC646C)[0] == 3564, "not the V38 4x baseline"
    assert struct.unpack_from("<H", code, 0xC6312)[0] == 320


def _self_check_encoders():
    """Every encoder must reproduce either a real code.bin instance (re-disassembled via GhidraMCP this
    session, addresses cited in the module docstring ENCODING VERIFICATION) or an already-verified encoder
    from build_vcantx_test_tva.py / build_v51probe_tva.py."""
    # verbatim-reused encoders (re-asserted here so this file self-verifies without importing the seed)
    assert mov32(0xFF481000, 8).hex() == "2806001048ff", "mov32 fails real mov 0xff481000,r8 @0x1d784"
    assert mov32(0xFF481000, 9).hex() == "2906001048ff", "mov32 fails real mov 0xff481000,r9 @0x1d7e6"
    assert movea(0x100, R0, 7).hex() == "203e0001", "movea fails real movea 0x100,r0,r7 @0x1d7ee"
    assert HOOK_STOCK.hex() == "2436e8ea", "hook stock literal mismatch"
    assert movi5(8, 7).hex() == "083a", "movi5 fails real mov 0x8,r7 @0x55c12 (hook return)"
    assert movi5(8, 8).hex() == "0842", "movi5 fails real mov 0x8,r8 @0x356a"
    assert stb(0, 0x24, 10).hex() == "4a072400", "stb fails real st.b r0,0x24,r10 @0x1d1ac"
    assert sth(1, 0x0, 29).hex() == "7d0f0000", "sth fails real st.h r1,0x0,r29 @0x2f0"
    assert stw(0, 0x0, 2).hex() == "62070100", "stw fails real st.w r0,0x0,r2 @0x26e"
    assert ldw(2, 0x0, 16).hex() == "22870100", "ldw fails real ld.w 0x0,r2,r16 @0x282"
    assert addi(-0x4, SP, SP).hex() == "031efcff", "addi fails real addi -0x4,sp,sp @0x750a"
    assert DI.hex() == "e0076001" and EI.hex() == "e0876001", "DI/EI literal mismatch"
    assert JMP_LP.hex() == "7f00", "JMP [lp] literal mismatch"
    assert LD_BU_TXREADY_R12.hex() == "a407e566d1ff", "gate-1 ld.bu literal mismatch"

    # SHR -- seed-verified formula, re-corroborated this session against FUN_0001d68e's own gate-2 read
    assert shr(0x1, 16).hex() == "8182", "shr fails real shr 0x1,r16 @0x9cc"
    assert shr(0x2, 2).hex() == "8212", "shr fails real shr 0x2,r2 @0xa72"
    assert shr(0x4, R6).hex() == "8432", "shr fails real shr 0x4,r6 @0x1d6b2 (FUN_0001d68e gate 2)"
    assert shr(0x1, R6).hex() == "8132", "shr fails real shr 0x1,r6 @0x1d6b4 (FUN_0001d68e gate 2)"

    # GATE 2 literal reuse -- re-disassembled 0x1d6aa/0x1d6ae on code.bin this session
    assert GATE2_MOVHI_R6.hex() == "403648ff", "gate-2 movhi literal mismatch (real @0x1d6aa)"
    assert GATE2_LDBU_R6.hex() == "86374d02", "gate-2 ld.bu literal mismatch (real @0x1d6ae)"

    # ld.hu -- verbatim formula from build_v51probe_tva.py, cross-checked there against 4 real instances
    assert ldhu(0x1300, 7).hex() == "e43f01ed", "ldhu formula mismatch vs build_v51probe_tva.py"
    assert ldhu(0x22BA, 8).hex() == "e44747dd", "ldhu fails real code.bin ld.hu -0x22ba,r8 @0x14f0a"
    assert ldhu(0x22B8, 12).hex() == "e46749dd", "ldhu fails real code.bin ld.hu -0x22b8,r12 @0x14f12"
    assert ldhu(0x22BC, 6).hex() == "e43745dd", "ldhu fails real code.bin ld.hu -0x22bc,r6 @0x14f30"
    assert ldhu(0x24C4, 7).hex() == "e43f3ddb", "ldhu fails real code.bin ld.hu -0x24c4,r7 @0x15012"

    # Bcond (BC/BNC) -- seed-verified formula; this build's own bc1/bnc2 disps are BOTH +6 by construction,
    # matching the seed's own real "bc disp=+6 @0x2fc" cross-check exactly.
    assert bcond(COND_BC, +6).hex() == "b105", "bcond fails real bc disp=+6 @0x2fc"
    assert bc(6).hex() == "b105", "bc(6) must equal the real bc disp=+6 instance"
    assert bcond(COND_BNC, -22).hex() == "d9f5", "bcond fails real bnc disp=-22 @0x30c"
    assert bcond(COND_BNC, +128).hex() == "8945", "bcond fails real bnc disp=+128 @0xa74"

    # JR -- NEW this session, verified against real code.bin `jr 0x1d82a`@0x1d6c8 (part of FUN_0001d68e,
    # disassembled this session immediately before this gate-2 work)
    assert jr(0x1d82a, 0x1d6c8).hex() == "80076201", "jr fails real jr 0x1d82a @0x1d6c8"


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
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    _self_check_encoders()

    code = bytearray(baseline)
    hook_bytes = jarl_lp(CAVE_BASE, HOOK_ADDR)
    print(f"  cave  @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes (limit {CAVE_HARD_LIMIT - CAVE_BASE} bytes, "
          f"headroom {CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)} bytes)")
    print(f"  hook  @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  (movea -> jarl 0x{CAVE_BASE:05X},lp)")
    for mbx in MAILBOXES:
        print(f"  mailbox {mbx['n']:2d} -> ID 0x{mbx['can_id']:03X}: " +
              ", ".join(f"{name}({label})" for name, _, label in mbx["signals"]))
    print(f"  gated on gp-0x1712 bit0 (TX-ready) AND DAT_ff48024c bit4 (real emitter's own arm gate)\n")
    pc = CAVE_BASE
    for b, comment in CAVE_LISTING:
        print(f"    0x{pc:05X}: {b.hex():<16} {comment}")
        pc += len(b)
    print()

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes

    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)), "cave tail moved"
    assert CAVE_BASE + len(CAVE_BYTES) <= CAVE_HARD_LIMIT, "cave overruns its free region"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave bytes not written"

    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    allowed = set(range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES)))
    allowed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected FOURFRAME-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:0x100000]) == bytes(baseline[0xC5000:0x100000]), "any cal/data block moved"
    assert struct.unpack_from("<H", code, 0xC646C)[0] == 3564, "4x gain disturbed"

    assert_crc_chain(code, "FOURFRAME plain")
    assert walk(bytes(code), label="FOURFRAME") == 0
    assert walk_all_blocks(bytes(code), label="FOURFRAME") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "FOURFRAME emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "FOURFRAME RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "FOURFRAME RWD readback")
    assert walk(readback, label="FOURFRAME RWD readback") == 0
    assert walk_all_blocks(readback, label="FOURFRAME RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert struct.unpack_from("<H", readback, 0xC646C)[0] == 3564

    cave_span = range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES))
    print(f"\n  FOURFRAME-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        kind = ("cave fourframe_program_and_fire" if first in cave_span else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else "UNEXPECTED")
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:        {V38_SHA256}")
    print(f"  FOURFRAME SHA-256:  {hashlib.sha256(code).hexdigest()}")
    print(f"  FOURFRAME RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-FOURFRAME-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(OUT)]
    for path in stale + [OUT, BIN_OUT, OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("FOURFRAME = V38 + a FOUR-FRAME passive READ-ONLY CAN telemetry code cave: FCN0 mailboxes 16-19")
    print("  -> new IDs 0x6A0-0x6A3, 4 gp-relative RAM signals/frame (16 total), 62.5 Hz.")
    print("  ELEVATED RISK class: shares the physical bus carrying steering frames. STUDY ARTIFACT.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".tmp", "wb") as h:
        h.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as h:
        h.write(code)
    os.replace(OUT + ".tmp", OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  UNFLASHED. Do NOT flash. Do NOT send CAN. Flash only on explicit operator instruction")
    print("  naming the file + bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
