"""
builds/telemetry/build_vcantx_test_tva.py -- VCANTX-TEST = V38 + the kit's FIRST ACTIVE-CAN-TRANSMIT code cave. It stands up
FCN0 hardware mailbox 16 (confirmed unclaimed) as a brand-new dedicated TX identifier 0x555 and transmits a
fixed 8-byte magic payload (A5 5A A5 5A A5 5A A5 5A) at 62.5 Hz -- GATED on the real TX-readiness interlock
gp-0x1712 bit0 (see TX-READY GATE below): when that bit is clear (bus-off/comm-fault recovery, or the
mailbox-bank reconfig in FUN_0001cf30 rewriting mailbox registers), this cave writes NOTHING to mailbox 16
and falls straight through to the restore+return, avoiding a register-rewrite race with stock code.

TX-READY GATE (added on review -- gp-0x1712 bit0 is a REAL interlock, not just table bookkeeping)
    A trace confirmed stock code checks gp-0x1712 bit0 in BOTH FUN_0001d82e and FUN_0001d68e before arming
    any mailbox: it's 1 in normal driving, but drops to 0 during bus-off/comm-fault recovery and while
    FUN_0001cf30's mailbox-bank reconfig is rewriting mailbox registers (mailbox 16 included, since that
    loop bare-izes indices 7-32). This cave originally wrote mailbox 16 unconditionally every cycle, which
    would race that reconfig. Fixed by wrapping the ENTIRE mailbox-16 body (config writes + fire strobe) in
    a top-of-cave gate:
        ld.bu -0x1712[gp],r12   ; r12 = TX-ready byte (abs 0xFEDF68EE)
        shr   0x1,r12           ; bit0 -> CY
        bnc   SKIP              ; bit0 clear (TX inhibited) -> skip straight to restore+return
        ... unchanged mailbox-16 config + payload + CTL fire ...
      SKIP:
        ... restore + return ...
    r12 is used (not r6, despite it being free after the save) because the only encoding of
    `ld.bu -0x1712,gp,r12` this session could GROUND is the literal real instruction bytes themselves --
    see ENCODING VERIFICATION's LD.BU note for why a hand-derived r6-targeted variant was rejected. r12 is
    now saved/restored alongside r6/r7/r8/r9.

PURPOSE
    Every prior telemetry cave in this kit (V31P/V49P/V50P/V51P) is PASSIVE -- it reads a RAM cell or a live
    CAN-330 frame's spare bits and never puts a new frame on the wire. This is the first cave that ACTIVELY
    ARMS AND FIRES a hardware CAN mailbox the firmware itself has never used. It shares nothing with the
    steering command path -- it does not touch gp-0x4f60, the aggregator, the governor, or any of the
    torque-shaping RAM cells this kit's other builds have gated on -- but it DOES share the physical bus that
    carries STEER_STATUS/torque-sensor frames, so correctness of the CAN-controller programming sequence
    itself (not the payload) is the entire safety question. STUDY ARTIFACT. UNFLASHED. Do NOT send CAN.

MAILBOX 16 -- CONFIRMED FREE (prior analysis pass, this session, three independent methods; see
    .claude/agent-memory/firmware-codepath-tracer/reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings.md):
      1. Boot-init bare-ization loop FUN_0001cf30 (0x1d190-0x1d1c0) STRB=0's every mailbox index 7..32
         inclusive (mailbox 16 is inside this range) and never touches it again.
      2. Zero xrefs anywhere in code.bin to any of the four mailbox-16 register addresses.
      3. The full 18-slot TX routing table (0xB7208) uses only mailboxes {0..6}; 16 never appears.

TECHNIQUE
    HOOK (VERBATIM reuse of the V31P/V49P/V50P/V51P trampoline -- proven safe, flashed+driven repeatedly):
    site 0x55C0E `movea -0x1518,gp,r6` (the CAN-330 packer FUN_00055a98's own pack-buffer-base setup) ->
    `jarl cave,lp`. The cave re-executes the displaced movea last, then `jmp [lp]` returns to 0x55C12. This
    hook site runs at 62.5 Hz (same scheduled cadence as CAN 330 itself, per
    reference_accord_can_tx_full_table_decode_and_new_id_recipe.md's cadence trace), which is exactly the
    rate this build wants for its own TX -- no extra cadence divider needed.

    CAVE BODY (`vcantx_program_and_fire`, @0xC4B34, 206 bytes -- well inside the confirmed 1212-byte free
    region 0xC4B34-0xC4FEF): every cycle, unconditionally re-programs and fires mailbox 16 in the same
    config+fire order the real emitter FUN_0001d68e uses (byte-verified this session, see below):
      STRB16(0xFF481424)  = 0x80          (SSOW bit7=1 -> TX direction)
      DTLGB16(0xFF481420) = 0x08          (DLC = 8 bytes)
      MID0W16(0xFF491428) = 0x555<<18     (= 0x15540000; IDE bit29=0 -> standard 11-bit ID, not extended)
      [di]
      DAT0..7B16 (0xFF481400,04,08,0C,10,14,18,1C) = A5 5A A5 5A A5 5A A5 5A
      [ei]
      CTL16(0xFF489438) = 0x0100 then 0x0200   (SERY then CSETR strobe -- byte-identical two-write sequence
                                                 to FUN_0001d68e's own TX-arm tail, confirmed below)
    Every register gets its OWN absolute address built fresh via the V850E2-native 6-byte MOV-imm32 idiom
    (disp=0 stores off each dedicated base) -- deliberately NOT movea+add and NOT FUN_0001d68e's own
    extended-displacement MID0W/CTL store forms (see ENCODING VERIFICATION: those extended forms turned out
    to be a DIFFERENT, 6-byte disp-forcing encoding this session discovered while cross-checking -- avoided
    entirely by giving every register disp=0 off its own base, which stays in the plain 4-byte Format VI
    range with no sign-extension trap).

    REGISTER SAFETY: r6 (address scratch), r7 (value scratch), r8/r9 (the two alternating payload byte
    constants, built once and reused for all 8 DAT writes), and r12 (the TX-ready gate byte) are saved to
    the stack on entry (`addi -0x14,sp,sp` + 5x `st.w`) and restored on exit (5x `ld.w` + `addi 0x14,sp,sp`)
    BEFORE the displaced `movea -0x1518,gp,r6` re-executes and `jmp [lp]` returns -- per the operator's
    standing instruction, this does NOT rely on any register being merely "dead at the hook's return site";
    it fully round-trips every register the cave touches through the stack, which is the same discipline
    real V850E2 function prologues/epilogues use (cross-checked against 15 real `addi ±N,sp,sp` instances
    this session). The restore+return sequence is IDENTICAL whether the gate takes the skip branch or falls
    through the mailbox-16 body -- `bnc SKIP` lands exactly on the first `ld.w`.

ENCODING VERIFICATION (every opcode below is a formula independently re-derived THIS session from real
    code.bin bytes via GhidraMCP disassemble_bytes/search_instructions -- not carried over unverified from
    an earlier memory. One assumption (that immediate-form `mov imm5,reg` shares register-form `mov reg,reg`'s
    op=0x00) was checked and found WRONG -- see MOV-imm5 below; every other formula matched on first
    cross-check.):
      MOV imm32,reg (6B):  byte0=0x20|reg2, byte1=0x06, half2=imm32&0xFFFF (LE), half3=(imm32>>16)&0xFFFF
          (LE). Verified against 3 real instances covering 3 distinct registers/immediates, disassembled
          directly this session: `mov 0xff481000,r8`@0x1d784="2806001048ff", `mov 0xff481000,r9`@0x1d7e6=
          "2906001048ff", `mov 0xfedf68bc,ep`@0x1d7cc="3e06bc68dffe".
      MOVEA imm16,reg1,reg2 (4B, op=0x31): halfword1=(reg2<<11)|(0x31<<5)|reg1, halfword2=imm16 (raw, LE).
          Verified against `movea 0x100,r0,r7`@0x1d7ee="203e0001" and the kit-standard hook stock itself,
          `movea -0x1518,gp,r6`@0x55c0e="2436e8ea" (both independently re-decoded this session).
      MOV imm5,reg2 (2B, op=0x10 -- NOT 0x00, which is register-register mov; caught by direct
          cross-check, not assumed): halfword=(reg2<<11)|(0x10<<5)|(imm5&0x1F). Verified against the real
          `mov 0x8,r7`@0x55c12="083a" (the very next instruction after this cave's own hook site) and
          `mov 0x8,r8`@0x356a="0842".
      ST.B src,disp16,base (4B, op=0x3A): halfword1=(src<<11)|(0x3A<<5)|base, halfword2=disp16 (raw, no
          masking -- byte stores have no alignment constraint). Verified against
          `st.b r0,0x24,r10`@0x1d1ac="4a072400" (the mailbox bare-ization loop's own STRB=0 write).
      ST.H src,disp16,base (4B, op=0x3B, SAME op as ST.W -- disambiguated by disp16 bit0=0 for H):
          halfword2=disp16 (raw literal; real emitted disps were all already-even, so bit0=0 naturally).
          Verified against `st.h r1,0x0,r29`@0x2f0="7d0f0000" and `st.h r0,0x0,r16`@0x98e="70070000".
      ST.W / LD.W src/dst,disp16,base (4B, op=0x3B/0x39, bit0=1 forces W-mode; real disp=field&0xFFFE):
          halfword2=(disp&0xFFFE)|1. Verified against `st.w r0,0x0,r2`@0x26e="62070100" (field=1, disp
          shown 0x0) and `st.w r16,-0x600,r0`@0x27c="608701fa" (field=0xFA01, masked disp=-0x600 exact);
          `ld.w 0x0,r2,r16`@0x282="22870100" and `ld.w -0x200,r2,r2`@0x350="221701fe" (same rule).
      ADDI imm16,reg1,reg2 (4B, op=0x30): halfword2=imm16 raw. Verified against 15 real `addi ±N,sp,sp`
          function prologue/epilogue instances, e.g. `addi -0x4,sp,sp`@0x750a="031efcff".
      DI / EI: fixed 4-byte no-operand instructions, LITERAL reuse -- `e0076001` / `e0876001` -- confirmed
          identical across 5 real instances each (program-wide `search_instructions` this session).
      JMP [lp] (2B) / the hook trampoline shape: LITERAL reuse of the V31P/V49P/V50P/V51P bytes, unchanged.
      SHR imm5,reg2 (2B, op=0x14): halfword=(reg2<<11)|(0x14<<5)|imm5, same Format-I layout as the
          already-verified SAR(0x15)/SHL(0x16). Verified against 2 real instances with different
          register/immediate: `shr 0x1,r16`@0x9cc="8182" and `shr 0x2,r2`@0xa72="8212".
      BNC disp,PC (2B, Bcond format): NOT assumed from memory or the ISA manual -- fully SOLVED and
          cross-validated this session against 54 real code.bin instances (38 `bc`, 15 `bnc`, 1 `bne`,
          spanning disp from -156 to +128, zero mismatches) because a wrong branch target on an active-TX
          cave is exactly the class of mistake that matters most. Layout (word = 16-bit LE):
            bits[3:0]   = cond (4-bit V850 condition code; BC=0x1, BNC=0x9, BNE=0xA -- BNC/BNE are BC/BE's
                          bit3-complement pair, matching the standard V850 cond table)
            bits[6:4]   = (disp//2)[2:0]      (disp must be even -- branch targets are halfword-aligned)
            bits[10:7]  = fixed marker 0b1011 (bit7=1,bit8=1,bit9=0,bit10=1 -- confirmed constant across
                          all 54 samples regardless of cond or displacement)
            bits[15:11] = (disp//2)[7:3]
          i.e. an 8-bit signed (disp//2) field split into a low-3/high-5 pair straddling the fixed marker.
          `disp` is (target_address - address_of_the_bcond_instruction_itself), matching every sample.
          Range: -256..+254 bytes from the branch's own address -- this cave's gate skips 162 bytes forward
          (well inside range, d2=81 of max 127).
      LD.BU -0x1712,gp,r12 (6B): NOT hand-derived -- LITERAL reuse of the real TX-ready-gate read at
          FUN_0001d68e@0x1d7da (`a407e566d1ff`), targeting r12 (that instance's own destination register).
          LD.BU is a KNOWN-IRREGULAR opcode in this kit (an earlier session found its op bits are "not a
          clean function of the destination register alone" across two 4-byte literal instances at
          -0x1514/-0x1511); this session's own disassembly of the -0x1712 instance shows it is a
          COMPLETELY DIFFERENT 6-byte form (not the 4-byte form used elsewhere), confirming the irregularity
          is real and deeper than parity. No attempt was made to hand-derive an r6-targeted variant of this
          instruction -- the gate uses r12 (saved/restored like every other touched register) specifically
          so the literal bytes can be reused unmodified rather than trusting an ungrounded LD.BU encoding.

    The real emitter's own TX-arm tail was re-disassembled this session (0x1d7ee-0x1d802) and matches this
    cave's CTL-fire sequence exactly in form (movea imm,r0,rX; st.h rX,disp,base -- twice, 0x0100 then
    0x0200) modulo the fact that the real emitter's base register carries a nonzero (0x8038) displacement
    that turned out to need the OTHER (6-byte, disp-forcing) store encoding -- this cave sidesteps that by
    building CTL's own base address directly, so its st.h stays in the plain disp=0 form.

SAFETY: STUDY ARTIFACT. UNFLASHED. Do NOT flash. Do NOT transmit CAN. Flash only on explicit operator
    instruction naming file + bus.
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
    raise RuntimeError("VCANTX-TEST builder requires assertions; do not run with python -O")

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

TAG = "newid0x555-mbx16-fcn0-62p5hz-fixed8B-txgate-caveC4B34-onV38"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-VCANTX-TEST-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_vcantxtest_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

CAVE_BASE = 0xC4B34
HOOK_ADDR = 0x55C0E
HOOK_STOCK = bytes.fromhex("2436e8ea")   # movea -0x1518,gp,r6

MAIN_BLOCK = (0x13000, 0xC4FFC)
EXPECTED_BLOCKS = 50

# -------------------------------------------------------------------------------------------------------
# V850E2 mini-assembler -- every encoder below is formula-checked in build() against a real code.bin
# instance disassembled this session via GhidraMCP. See the module docstring for the byte citations.
# -------------------------------------------------------------------------------------------------------

R0, SP, GP = 0, 3, 4
R6, R7, R8, R9, R12 = 6, 7, 8, 9, 12
EP, LP = 30, 31


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def _fmt1(op, reg1, reg2):
    assert 0 <= op <= 0x3F and 0 <= reg1 <= 31 and 0 <= reg2 <= 31
    return _le16((reg2 << 11) | (op << 5) | reg1)


def mov32(imm32, reg2):
    """MOV imm32,reg2 -- V850E2-native 48-bit form. byte0=0x20|reg2, byte1=0x06, then imm32 LE."""
    assert 0 <= imm32 <= 0xFFFFFFFF and 0 <= reg2 <= 31
    return bytes([0x20 | reg2, 0x06]) + _le16(imm32 & 0xFFFF) + _le16((imm32 >> 16) & 0xFFFF)


def movea(imm16, reg1, reg2):
    """MOVEA imm16,reg1,reg2 (op=0x31). Caller must ensure imm16<0x8000 when a clean positive constant
    (reg1=r0) is intended -- movea sign-extends its 16-bit field."""
    assert 0 <= imm16 <= 0xFFFF
    return _fmt1(0x31, reg1, reg2) + _le16(imm16)


def movi5(imm5, reg2):
    """MOV imm5,reg2 (op=0x10 -- distinct from register-register mov's op=0x00)."""
    assert -16 <= imm5 <= 15
    return _fmt1(0x10, imm5 & 0x1F, reg2)


def stb(src, disp, base):
    """ST.B src,disp16,base (op=0x3A). disp16 is a raw literal field, no masking."""
    assert -0x8000 <= disp <= 0x7FFF
    return _fmt1(0x3A, base, src) + _le16(disp & 0xFFFF)


def sth(src, disp, base):
    """ST.H src,disp16,base (op=0x3B). disp16 raw literal; hardware requires bit0==0 (H-mode selector)."""
    assert -0x8000 <= disp <= 0x7FFF and disp % 2 == 0
    return _fmt1(0x3B, base, src) + _le16(disp & 0xFFFF)


def stw(src, disp, base):
    """ST.W src,disp16,base (op=0x3B, shared with ST.H). bit0 forced to 1 selects W-mode; real
    displacement = field & 0xFFFE."""
    assert -0x8000 <= disp <= 0x7FFE and disp % 2 == 0
    return _fmt1(0x3B, base, src) + _le16(((disp & 0xFFFE) | 1) & 0xFFFF)


def ldw(base, disp, dst):
    """LD.W disp16,base,dst (op=0x39). Same bit0-forced-1 W-mode rule as ST.W."""
    assert -0x8000 <= disp <= 0x7FFE and disp % 2 == 0
    return _fmt1(0x39, base, dst) + _le16(((disp & 0xFFFE) | 1) & 0xFFFF)


def addi(imm16, reg1, reg2):
    """ADDI imm16,reg1,reg2 (op=0x30)."""
    return _fmt1(0x30, reg1, reg2) + _le16(imm16 & 0xFFFF)


def shr(imm5, reg2):
    """SHR imm5,reg2 (op=0x14). Same Format-I layout as SAR(0x15)/SHL(0x16)."""
    assert 0 <= imm5 <= 31
    return _fmt1(0x14, imm5, reg2)


# Bcond (BNC/BC/BNE/...) -- fully solved and cross-validated this session against 54 real code.bin
# instances (38 bc, 15 bnc, 1 bne; disp range -156..+128; zero mismatches). See module docstring
# ENCODING VERIFICATION for the full derivation. disp is relative to the bcond instruction's OWN address.
_BCOND_FIXED = (1 << 7) | (1 << 8) | (0 << 9) | (1 << 10)   # constant across every real sample
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


DI = bytes.fromhex("e0076001")
EI = bytes.fromhex("e0876001")
JMP_LP = bytes.fromhex("7f00")

# TX-ready gate read -- LITERAL reuse of the real `ld.bu -0x1712,gp,r12` from FUN_0001d68e@0x1d7da.
# NOT hand-derived: LD.BU's op bits are a known-irregular function of register/displacement in this kit
# (see module docstring). Targets r12 because that is the real instruction's own destination register.
LD_BU_TXREADY_R12 = bytes.fromhex("a407e566d1ff")

# -------------------------------------------------------------------------------------------------------
# Mailbox 16 register map (FCN0, base 0xFF480000, per-mailbox step 0x40 -- see docstring for the freecheck)
# -------------------------------------------------------------------------------------------------------

STRB16 = 0xFF481424
DTLGB16 = 0xFF481420
MID0W16 = 0xFF491428
CTL16 = 0xFF489438
DAT_BASE16 = 0xFF481400
DAT_ADDRS16 = [DAT_BASE16 + 4 * i for i in range(8)]   # 0xFF481400,04,08,0C,10,14,18,1C

NEW_CAN_ID = 0x555
MID0W_VAL = (NEW_CAN_ID << 18) & 0xFFFFFFFF
PAYLOAD = bytes.fromhex("A55AA55AA55AA55A")   # DAT0..7B, alternating A5/5A
assert len(PAYLOAD) == 8
assert MID0W_VAL == 0x15540000
assert (MID0W_VAL >> 29) & 1 == 0, "IDE bit must be 0 (standard 11-bit ID, not extended)"


def build_cave():
    """Assemble vcantx_program_and_fire: save scratch regs, gate on gp-0x1712 bit0 (TX-ready), program+fire
    mailbox 16 when the gate is open, restore scratch regs, re-execute the displaced hook instruction,
    return. Returns (bytes, listing)."""
    prologue = []
    gate_prefix = []
    body = []      # gated: mailbox-16 config + payload + CTL fire, unchanged from the pre-gate build
    epilogue = []
    tail = []

    def emit(lst, b, comment):
        lst.append((b, comment))

    # ---- prologue: save r6/r7/r8/r9/r12 ----
    emit(prologue, addi(-0x14, SP, SP), "addi -0x14,sp,sp        ; sp -= 20")
    emit(prologue, stw(R6, 0x0, SP), "st.w r6,0x0[sp]")
    emit(prologue, stw(R7, 0x4, SP), "st.w r7,0x4[sp]")
    emit(prologue, stw(R8, 0x8, SP), "st.w r8,0x8[sp]")
    emit(prologue, stw(R9, 0xC, SP), "st.w r9,0xC[sp]")
    emit(prologue, stw(R12, 0x10, SP), "st.w r12,0x10[sp]")

    # ---- TX-ready gate: gp-0x1712 bit0 (real interlock, confirmed checked by stock FUN_0001d82e/d68e) ----
    emit(gate_prefix, LD_BU_TXREADY_R12, "ld.bu -0x1712[gp],r12   ; r12 = TX-ready byte (literal reuse)")
    emit(gate_prefix, shr(0x1, R12), "shr 0x1,r12              ; bit0 -> CY")
    # bnc's displacement is filled in below once body's length is known -- placeholder appended last.

    # ---- STRB16 = 0x80 (SSOW dir bit -> TX) ----
    emit(body, mov32(STRB16, R6), f"mov 0x{STRB16:08X},r6    ; &STRB16")
    emit(body, movea(0x80, R0, R7), "movea 0x80,r0,r7        ; r7 = 0x80 (TX)")
    emit(body, stb(R7, 0x0, R6), "st.b r7,0x0[r6]         ; STRB16 = 0x80")

    # ---- DTLGB16 = 8 (DLC) ----
    emit(body, mov32(DTLGB16, R6), f"mov 0x{DTLGB16:08X},r6    ; &DTLGB16")
    emit(body, movi5(8, R7), "mov 0x8,r7               ; r7 = 8 (DLC)")
    emit(body, stb(R7, 0x0, R6), "st.b r7,0x0[r6]         ; DTLGB16 = 8")

    # ---- MID0W16 = 0x555<<18 ----
    emit(body, mov32(MID0W16, R6), f"mov 0x{MID0W16:08X},r6    ; &MID0W16")
    emit(body, mov32(MID0W_VAL, R7), f"mov 0x{MID0W_VAL:08X},r7    ; r7 = ID<<18 (IDE=0)")
    emit(body, stw(R7, 0x0, R6), "st.w r7,0x0[r6]         ; MID0W16 = 0x555<<18")

    # ---- build the two alternating payload constants once ----
    emit(body, movea(0xA5, R0, R8), "movea 0xa5,r0,r8        ; r8 = 0xA5 (payload constant)")
    emit(body, movea(0x5A, R0, R9), "movea 0x5a,r0,r9        ; r9 = 0x5A (payload constant)")

    # ---- di / write DAT0..7B / ei (mirrors FUN_0001d68e's own IRQ-disable window) ----
    emit(body, DI, "di")
    for i, addr in enumerate(DAT_ADDRS16):
        val_reg = R8 if PAYLOAD[i] == 0xA5 else R9
        assert PAYLOAD[i] in (0xA5, 0x5A)
        emit(body, mov32(addr, R6), f"mov 0x{addr:08X},r6    ; &DAT{i}B16")
        emit(body, stb(val_reg, 0x0, R6), f"st.b r{val_reg},0x0[r6]         ; DAT{i}B16 = 0x{PAYLOAD[i]:02X}")
    emit(body, EI, "ei")

    # ---- FIRE: CTL16 = 0x0100 then 0x0200 (SERY then CSETR, matches FUN_0001d68e's own tail) ----
    emit(body, mov32(CTL16, R6), f"mov 0x{CTL16:08X},r6    ; &CTL16")
    emit(body, movea(0x100, R0, R7), "movea 0x100,r0,r7       ; r7 = 0x0100 (SERY)")
    emit(body, sth(R7, 0x0, R6), "st.h r7,0x0[r6]         ; CTL16 = 0x0100")
    emit(body, movea(0x200, R0, R7), "movea 0x200,r0,r7       ; r7 = 0x0200 (CSETR)")
    emit(body, sth(R7, 0x0, R6), "st.h r7,0x0[r6]         ; CTL16 = 0x0200  <-- TX FIRE")

    # ---- epilogue: restore r6/r7/r8/r9/r12 (this is the bnc SKIP target) ----
    emit(epilogue, ldw(SP, 0x0, R6), "ld.w 0x0[sp],r6")
    emit(epilogue, ldw(SP, 0x4, R7), "ld.w 0x4[sp],r7")
    emit(epilogue, ldw(SP, 0x8, R8), "ld.w 0x8[sp],r8")
    emit(epilogue, ldw(SP, 0xC, R9), "ld.w 0xC[sp],r9")
    emit(epilogue, ldw(SP, 0x10, R12), "ld.w 0x10[sp],r12")
    emit(epilogue, addi(0x14, SP, SP), "addi 0x14,sp,sp         ; sp += 20")

    # ---- re-execute the displaced hook instruction, then return ----
    emit(tail, HOOK_STOCK, "movea -0x1518,gp,r6     ; displaced hook instruction, re-executed")
    emit(tail, JMP_LP, "jmp [lp]                 ; return to 0x55c12")

    # bnc's own address = end of prologue + end of gate_prefix (its own 2 bytes are NOT counted --
    # disp is relative to the bcond instruction's own address, per the verified formula).
    prologue_len = sum(len(b) for b, _ in prologue)
    gate_prefix_len = sum(len(b) for b, _ in gate_prefix)   # ld.bu(6) + shr(2) = 8
    body_len = sum(len(b) for b, _ in body)
    bnc_addr = prologue_len + gate_prefix_len                       # offset of the bnc instruction itself
    skip_addr = prologue_len + gate_prefix_len + 2 + body_len       # offset of epilogue[0] (SKIP target)
    disp = skip_addr - bnc_addr
    emit(gate_prefix, bnc(disp), f"bnc SKIP                 ; disp=+{disp} (skip {body_len}B gated body if TX not ready)")

    chunks = prologue + gate_prefix + body + epilogue + tail
    cave = b"".join(b for b, _ in chunks)

    # sanity: re-locate SKIP by walking the assembled bytes and confirm it lands exactly on epilogue[0]
    assert cave[bnc_addr:bnc_addr + 2] == bnc(disp), "bnc bytes not where expected"
    assert cave[skip_addr:skip_addr + len(epilogue[0][0])] == epilogue[0][0], \
        "bnc SKIP target does not land on the first restore instruction"

    return cave, chunks


CAVE_BYTES, CAVE_LISTING = build_cave()


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


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
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(CAVE_BYTES)), "cave tail is not 0xFF"
    assert CAVE_BASE + len(CAVE_BYTES) <= 0xC4FF0, "cave overruns its free region"
    assert struct.unpack_from("<H", code, 0xC646C)[0] == 3564, "not the V38 4x baseline"
    assert struct.unpack_from("<H", code, 0xC6312)[0] == 320


def _self_check_encoders():
    """Every DERIVED encoder must reproduce a REAL code.bin instance disassembled this session via
    GhidraMCP (addresses/bytes cited in the module docstring's ENCODING VERIFICATION section)."""
    assert mov32(0xFF481000, 8).hex() == "2806001048ff", "mov32 fails real mov 0xff481000,r8 @0x1d784"
    assert mov32(0xFF481000, 9).hex() == "2906001048ff", "mov32 fails real mov 0xff481000,r9 @0x1d7e6"
    assert mov32(0xFEDF68BC, EP).hex() == "3e06bc68dffe", "mov32 fails real mov 0xfedf68bc,ep @0x1d7cc"
    assert movea(0x100, R0, 7).hex() == "203e0001", "movea fails real movea 0x100,r0,r7 @0x1d7ee"
    assert movea(0x1518, GP, 6).hex() != HOOK_STOCK.hex(), "sanity: positive movea must differ from -0x1518 form"
    assert HOOK_STOCK.hex() == "2436e8ea", "hook stock literal mismatch"
    assert movi5(8, 7).hex() == "083a", "movi5 fails real mov 0x8,r7 @0x55c12 (this cave's own hook return)"
    assert movi5(8, 8).hex() == "0842", "movi5 fails real mov 0x8,r8 @0x356a"
    assert stb(0, 0x24, 10).hex() == "4a072400", "stb fails real st.b r0,0x24,r10 @0x1d1ac"
    assert sth(1, 0x0, 29).hex() == "7d0f0000", "sth fails real st.h r1,0x0,r29 @0x2f0"
    assert sth(0, 0x0, 16).hex() == "70070000", "sth fails real st.h r0,0x0,r16 @0x98e"
    assert stw(0, 0x0, 2).hex() == "62070100", "stw fails real st.w r0,0x0,r2 @0x26e"
    assert stw(16, -0x600, 0).hex() == "608701fa", "stw fails real st.w r16,-0x600,r0 @0x27c"
    assert ldw(2, 0x0, 16).hex() == "22870100", "ldw fails real ld.w 0x0,r2,r16 @0x282"
    assert ldw(2, -0x200, 2).hex() == "221701fe", "ldw fails real ld.w -0x200,r2,r2 @0x350"
    assert addi(-0x4, SP, SP).hex() == "031efcff", "addi fails real addi -0x4,sp,sp @0x750a"
    assert addi(0x4, SP, SP).hex() == "031e0400", "addi fails real addi 0x4,sp,sp @0x7528"
    assert DI.hex() == "e0076001", "DI literal mismatch"
    assert EI.hex() == "e0876001", "EI literal mismatch"
    assert JMP_LP.hex() == "7f00", "JMP [lp] literal mismatch (V31P/V49P/V50P/V51P trampoline tail)"
    assert LD_BU_TXREADY_R12.hex() == "a407e566d1ff", \
        "LD.BU -0x1712,gp,r12 literal mismatch (real FUN_0001d68e@0x1d7da bytes)"

    # SHR: op=0x14, verified against 2 real instances (different register AND immediate)
    assert shr(0x1, 16).hex() == "8182", "shr fails real shr 0x1,r16 @0x9cc"
    assert shr(0x2, 2).hex() == "8212", "shr fails real shr 0x2,r2 @0xa72"

    # Bcond: formula solved + cross-validated against 54 real instances (38 bc, 15 bnc, 1 bne) this
    # session -- spot-check a representative sample of each condition/sign/magnitude here.
    assert bcond(COND_BC, -26).hex() == "b1f5", "bcond fails real bc disp=-26 @0x290"
    assert bcond(COND_BC, +6).hex() == "b105", "bcond fails real bc disp=+6 @0x2fc"
    assert bcond(COND_BC, -156).hex() == "a1b5", "bcond fails real bc disp=-156 @0xb04 (widest-magnitude sample)"
    assert bcond(COND_BNC, -22).hex() == "d9f5", "bcond fails real bnc disp=-22 @0x30c"
    assert bcond(COND_BNC, +128).hex() == "8945", "bcond fails real bnc disp=+128 @0xa74 (largest positive sample)"
    assert bcond(COND_BNC, -140).hex() == "a9bd", "bcond fails real bnc disp=-140 @0xa46"
    assert bcond(COND_BNE, +46).hex() == "fa15", "bcond fails real bne disp=+46 @0x1d7d8"
    assert bnc(+162).hex() != "", "sanity: bnc must produce nonempty bytes for this cave's own +162 disp"


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
    print(f"  cave  @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes")
    print(f"  hook  @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  (movea -> jarl 0x{CAVE_BASE:05X},lp)")
    print(f"  new CAN ID 0x{NEW_CAN_ID:03X} via FCN0 mailbox 16, payload {PAYLOAD.hex().upper()}, 62.5 Hz")
    print(f"  gated on gp-0x1712 bit0 (TX-ready); mailbox-16 body skipped when clear")
    print()
    pc = CAVE_BASE
    for b, comment in CAVE_LISTING:
        print(f"    0x{pc:05X}: {b.hex():<16} {comment}")
        pc += len(b)
    print()

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes

    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(CAVE_BYTES)), "cave tail moved"
    assert CAVE_BASE + len(CAVE_BYTES) <= 0xC4FF0, "cave overruns its free region"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave bytes not written"

    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    allowed = set(range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES)))
    allowed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected VCANTX-TEST-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:0x100000]) == bytes(baseline[0xC5000:0x100000]), "any cal/data block moved"

    assert_crc_chain(code, "VCANTX-TEST plain")
    assert walk(bytes(code), label="VCANTX-TEST") == 0
    assert walk_all_blocks(bytes(code), label="VCANTX-TEST") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "VCANTX-TEST emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "VCANTX-TEST RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "VCANTX-TEST RWD readback")
    assert walk(readback, label="VCANTX-TEST RWD readback") == 0
    assert walk_all_blocks(readback, label="VCANTX-TEST RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert struct.unpack_from("<H", readback, 0xC646C)[0] == 3564

    cave_span = range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES))
    print(f"\n  VCANTX-TEST-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    print(f"  (cave bytes that coincide with the pre-existing 0xFF fill, e.g. the 0xFF48xxxx address")
    print(f"   literals' high halfword, do not show as 'changed' and split the cave into sub-runs below --")
    print(f"   cosmetic only; every byte in [0x{CAVE_BASE:05X},0x{CAVE_BASE+len(CAVE_BYTES):05X}) is either")
    print(f"   a written cave byte or an untouched 0xFF, confirmed by the allowed-set assertion above.)")
    for first, last in runs:
        kind = ("cave vcantx_program_and_fire" if first in cave_span else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else "UNEXPECTED")
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:          {V38_SHA256}")
    print(f"  VCANTX-TEST SHA-256:  {hashlib.sha256(code).hexdigest()}")
    print(f"  VCANTX-TEST RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-VCANTX-TEST-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(OUT)]
    for path in stale + [OUT, BIN_OUT, OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("VCANTX-TEST = V38 + FIRST ACTIVE-CAN-TX code cave: FCN0 mailbox 16 -> new ID 0x555,")
    print("  fixed 8B magic payload A5 5A A5 5A A5 5A A5 5A, 62.5 Hz (piggybacked on the CAN-330 packer hook).")
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
