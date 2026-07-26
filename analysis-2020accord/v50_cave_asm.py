"""
v50_cave_asm.py -- the V50 first-order EMA low-pass code cave, assembled from byte-verified V850E2
encodings (the SAME encoders as v48b_cave_asm.py, which were cross-validated against real code.bin
instructions and Ghidra-re-disassembled from the built V48B image).

WHY A LOW-PASS, NOT V48B's NOTCH (see eps_v50_gate2_lowpass.py + the 2026-07-22 handoff):
  * frequency-robust: the felt mode is speed-dependent (~21.7 Hz low-speed -> ~8-12 Hz highway); a
    low-pass attenuates the whole 8-22 Hz band, a 21.4 Hz notch misses the high-speed content.
  * alias-robust: -6 dB @21.4 Hz AND -16 dB @78.6 Hz -> works whether the true mode is 21.7 or aliased.
  * polarity-independent: no sign term (sidesteps the V49 gate we cannot currently read).
  * GATE-1 SIMPLE: a first-order EMA has ONE state word. V48B's biquad had 4 cells; its x2 cell
    gp-0x14FA aliased a live monitor byte and bricked. One clean 32-bit state removes that failure mode.

FILTER (Q10, fc~=12 Hz): 32-bit state S = filtered_value << 8  (8 fractional bits -> NO deadband).
  each control cycle:
      x    = ld.h  gp-0x4f60                 (raw Sensor-B torque, s16, +/-25600)
      S    = ld.w  STATE                      (s32)
      diff = (x << 8) - S                     (|diff| <= ~13.1M, fits s32)
      S    = S + ((ALPHA * diff) >> 10)       (ALPHA=74 -> fc~11.9 Hz; 74*diff <= ~0.97e9, fits s32)
      st.w S, STATE
      y    = S >> 8                            (s16 filtered output)
      st.h y, OUTPUT                           (the cell the repointed carriers ld.h)
  Overflow proof: x<<8 <= 25600*256 = 6.55e6; S is an EMA of that, |S| <= 6.55e6; diff <= 13.1e6;
  74*diff <= 0.97e9 < 2^31-1 (2.147e9). No 32-bit signed overflow anywhere.

CAVE CONTRACT (identical hook mechanics to V48B, which was Ghidra-verified transparent):
  Entered by `jr CAVE` planted at 0x7FEAC (displacing `cmp r0,r8` + `mov r8,r14`, 4 bytes) in the
  gp-0x4f60 producer epilogue (FUN_0007f3f8). The cave saves scratch, runs the EMA on a FRESH read of
  gp-0x4f60, writes STATE (s32) + OUTPUT (s16), restores scratch, then RE-EXECUTES the two displaced
  instructions LAST (so PSW flags are correct for the `bge 0x7feb4` at the return) and `jr 0x7FEB0`.

RAM ADDRESSES ARE PARAMETERS (filled from the Gate-1 RAM-ownership trace before build):
  D_STATE  = 32-bit EMA state (4-byte footprint, must be proven free incl. writers)
  D_OUT    = 16-bit filtered output the carriers read (V48B used gp-0x1500, flash-proven free)
"""

import struct

GP = 0xFEDF8000
CAVE_BASE = 0xC4B34
HOOK = 0x7FEAC
RETURN = 0x7FEB0

# ---- filter parameters ----
ALPHA = 74          # Q10 EMA coefficient -> fc ~= 11.9 Hz at 1 kHz (eps_v50_gate2_lowpass.py)
FRAC = 8            # fractional bits in the 32-bit state (S = y << FRAC); >>? deadband-free
D_SENSOR = 0x4F60   # raw gp-0x4f60 (Sensor-B driver column torque)

# RAM cell: gp-0x1500 (0xFEDF6B00) -- V48B-flash-proven (V48B wrote it every cycle, drove; its brick
# was gp-0x14FA, a DIFFERENT cell). Gate-1 trace: bytes 0-1 direct-clean (two methods); the paired
# CAN-0xE4 handler FUN_00052676 does NOT write it (verified). ONE 16-bit cell = state AND output.
# RESIDUAL (irreducible cave risk, for the pre-flash review): 0xFEDF6B00 appears in the 0xbb640/0xb7260
# address tables whose walker was not identified -> no register-indirect writer PROVEN absent.
D_CELL = 0x1500


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def gp_field(disp_neg):
    """disp16 field for -disp_neg[gp], halfword-aligned (bit0=0)."""
    assert 0 < disp_neg <= 0x8000 and disp_neg % 2 == 0
    return (0x10000 - disp_neg) & 0xFFFF


def gp_field_w(disp_neg):
    """disp for a WORD (ld.w/st.w) gp access. V850 word access: bit0 of the disp field is the
    sub-opcode bit (=0 for these), address must be 4-aligned -> disp_neg % 4 == 0."""
    assert 0 < disp_neg <= 0x8000 and disp_neg % 4 == 0
    return (0x10000 - disp_neg) & 0xFFFF


# ---- Format encoders (identical to v48b_cave_asm.py; verified vs real code.bin) ----
def fmt1(op, reg1, reg2):
    return _le16((reg2 << 11) | (op << 5) | reg1)

def mov(reg1, reg2):    return fmt1(0x00, reg1, reg2)
def sub(reg1, reg2):    return fmt1(0x0D, reg1, reg2)   # reg2 = reg2 - reg1
def add(reg1, reg2):    return fmt1(0x0E, reg1, reg2)   # reg2 += reg1

def sar(imm5, reg2):
    assert 0 <= imm5 <= 31
    return _le16((reg2 << 11) | (0x15 << 5) | imm5)

def shl(imm5, reg2):
    assert 0 <= imm5 <= 31
    return _le16((reg2 << 11) | (0x16 << 5) | imm5)

def fmt6(op, reg1, reg2, imm16):
    return _le16((reg2 << 11) | (op << 5) | reg1) + _le16(imm16 & 0xFFFF)

def addi(imm16, reg1, reg2):  return fmt6(0x30, reg1, reg2, imm16)
def mulhi(imm16, reg1, reg2): return fmt6(0x37, reg1, reg2, imm16)  # reg2 = reg1 * imm16 (32-bit)

def ldst(op, reg2, reg1, field):
    return _le16((reg2 << 11) | (op << 5) | reg1) + _le16(field)

def ldh(disp_neg, reg2):  return ldst(0x39, reg2, 4, gp_field(disp_neg))     # ld.h -disp[gp],reg2
def sth(reg2, disp_neg):  return ldst(0x3B, reg2, 4, gp_field(disp_neg))     # st.h reg2,-disp[gp]
# ld.w/st.w SHARE opcode 0x39/0x3B with ld.h/st.h; the disp field LSB=1 selects WORD (V48B's *_sp forms).
def ldw(disp_neg, reg2):  return ldst(0x39, reg2, 4, (gp_field_w(disp_neg) & 0xFFFE) | 1)  # ld.w -disp[gp]
def stw(reg2, disp_neg):  return ldst(0x3B, reg2, 4, (gp_field_w(disp_neg) & 0xFFFE) | 1)  # st.w reg2,-disp[gp]
def stw_sp(reg2, off):    return ldst(0x3B, reg2, 3, (off & 0xFFFE) | 1)
def ldw_sp(reg2, off):    return ldst(0x39, reg2, 3, (off & 0xFFFE) | 1)

def jr(target, pc):
    disp = (target - pc) & 0x3FFFFF
    return _le16(0x0780 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


# displaced-instruction bytes (must match stock exactly)
CMP_R0_R8 = bytes.fromhex("e041")
MOV_R8_R14 = bytes.fromhex("0870")


def assemble_cave(base=CAVE_BASE, d_cell=D_CELL):
    """Return (bytes, annotated) for the SINGLE-CELL 16-bit EMA low-pass.

    d_cell (gp-0x1500, V48B-flash-proven, bytes 0-1 direct-clean) is BOTH the state and the output --
    the carriers ld.h it; the cave ld.h/st.h it. 16-bit integer EMA:
        y  = ld.h d_cell
        x  = ld.h gp-0x4f60
        d  = x - y                        (s17, |d|<=51200)
        y += (74*d) >> 10                 (74*d by shift-add, s32-safe; ~14-count deadband, benign)
        st.h y, d_cell
    Uses ONLY ld.h/st.h/sub/shl/add/sar/mov -- every encoder verified vs real code.bin instructions.
    """
    ann = []
    buf = bytearray()

    def emit(b, mnem):
        ann.append((base + len(buf), bytes(b), mnem))
        buf.extend(b)

    R_Y, R_D, R_A, R_T = 10, 11, 12, 13   # y(state/out), d(=x-y), acc(=74*d), tmp

    # save scratch (transparent). r14 is untouched by this cave (only the displaced `mov r8,r14` sets it).
    emit(addi(-16, 3, 3), "addi -16,sp,sp")
    emit(stw_sp(R_Y, 0), "st.w r10,0[sp]")
    emit(stw_sp(R_D, 4), "st.w r11,4[sp]")
    emit(stw_sp(R_A, 8), "st.w r12,8[sp]")
    emit(stw_sp(R_T, 12), "st.w r13,12[sp]")

    # y = ld.h d_cell ; x = ld.h gp-0x4f60 (into r11) ; d = x - y  (sub r10,r11 -> r11 = r11 - r10)
    emit(ldh(d_cell, R_Y), f"ld.h -0x{d_cell:04X}[gp],r10      ; y = filtered state/output")
    emit(ldh(D_SENSOR, R_D), "ld.h -0x4F60[gp],r11      ; r11 = x (raw Sensor-B)")
    emit(sub(R_Y, R_D), "sub r10,r11               ; r11 = d = x - y   (s17)")

    # acc = 74*d via shift-add (74 = 64+8+2). mulhi would TRUNCATE d to 16 bits (d is 17-bit) -> BUG.
    # All terms s32: |d|<=51200, 74*d<=3.79e6, no overflow.
    emit(mov(R_D, R_A), "mov r11,r12")
    emit(shl(6, R_A), "shl 6,r12                 ; acc = 64*d")
    emit(mov(R_D, R_T), "mov r11,r13")
    emit(shl(3, R_T), "shl 3,r13                 ; t = 8*d")
    emit(add(R_T, R_A), "add r13,r12               ; acc = 72*d")
    emit(mov(R_D, R_T), "mov r11,r13")
    emit(shl(1, R_T), "shl 1,r13                 ; t = 2*d")
    emit(add(R_T, R_A), "add r13,r12               ; acc = 74*d")

    # y += acc >> 10  (alpha = 74/1024, fc ~= 11.9 Hz) ; store
    emit(sar(10, R_A), "sar 10,r12                ; acc >>= 10")
    emit(add(R_A, R_Y), "add r12,r10               ; y += step")
    emit(sth(R_Y, d_cell), f"st.h r10,-0x{d_cell:04X}[gp]      ; store filtered y (carriers read this)")

    # restore scratch
    emit(ldw_sp(R_Y, 0), "ld.w 0[sp],r10")
    emit(ldw_sp(R_D, 4), "ld.w 4[sp],r11")
    emit(ldw_sp(R_A, 8), "ld.w 8[sp],r12")
    emit(ldw_sp(R_T, 12), "ld.w 12[sp],r13")
    emit(addi(16, 3, 3), "addi 16,sp,sp")

    # re-exec displaced (flags fresh for the bge at 0x7feb0), return
    emit(CMP_R0_R8, "cmp r0,r8                 ; displaced (sets flags)")
    emit(MOV_R8_R14, "mov r8,r14                ; displaced")
    emit(jr(RETURN, base + len(buf)), f"jr 0x{RETURN:05X}")
    return bytes(buf), ann


def main():
    cave, ann = assemble_cave(d_cell=D_CELL)
    print(f"CAVE @0x{CAVE_BASE:05X}  length = {len(cave)} bytes  ends 0x{CAVE_BASE + len(cave):05X}  "
          f"(cave capacity to 0xC4FEF)  [d_cell=gp-0x{D_CELL:04X}]")
    assert CAVE_BASE + len(cave) <= 0xC4FF0, "cave overruns free region"
    print(f"trampoline @0x{HOOK:05X}: {jr(CAVE_BASE, HOOK).hex()}  = jr 0x{CAVE_BASE:05X}")
    print()
    for off, b, mnem in ann:
        print(f"  0x{off:05X}: {b.hex():<8}  {mnem}")
    print(f"\nALPHA={ALPHA}/1024 (fc~11.9 Hz), single 16-bit cell gp-0x{D_CELL:04X}. Encoders (shl/sub/add/")
    print("sar/mov/ldh/sth/ldw_sp/stw_sp/jr) all verified vs real code.bin. Ghidra re-disassemble the built")
    print("image before flash (kit rule). Full cave hex:")
    print(cave.hex())


if __name__ == "__main__":
    main()
