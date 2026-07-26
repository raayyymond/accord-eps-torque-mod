"""
v52_cave_asm.py -- the V52 first-order EMA low-pass code cave. IDENTICAL to v50_cave_asm.py except
for the two GATE-driven changes below; every V850E2 encoder is the SAME byte-verified encoder as
v48b/v50 (cross-validated vs real code.bin and Ghidra-re-disassembled from the built V48B/V50 images).

V52 = V50 with THREE deltas (this file carries two of them; the 8th repoint lives in build_v52_tva.py):
  (1) STATE CELL RELOCATED gp-0x1500 -> gp-0x1300.
      gp-0x1500 (0xFEDF6B00) is slot 5 of the 0xb7260 I/O-mailbox array and has a LIVE WRITER -- the
      V50P probe drive proved it non-zero 99.47% of the drive => V50 would brick (V48B RAM-collision
      class). gp-0x1300 (0xFEDF6D00) is OUTSIDE that array (array top ~0xFEDF6C20) and OUTSIDE the
      gp-0x1401..0x1502 poison region, and the V51P probe drive (rlog 7, 4 segments, 24000 CAN-330
      frames, beacon live 100%) proved it reads 0 on EVERY frame with FULL 16-bit coverage -> no live
      writer. That is a definitive live-probe clearance, retiring V50's residual RAM-ownership doubt.
      (D=gp-0x1100 was equally clean; B=gp-0x1300 chosen as the first-listed candidate.)
  (2) ROUND-TO-NEAREST on the EMA step: y += (74*d + 512) >> 10  (was (74*d) >> 10 in V50).
      V50's arithmetic-shift floor rounds every step toward -inf, so small negative excursions kick
      the state down by a full LSB while equal positive ones do not -> a ~-6.5..-7 count DC bias +
      a local gain bump in the 11-33 count band (the adversarial swarm's GATE-2 note). Adding 512
      (= half of 1<<10) before the shift makes it round-half-up = round-to-nearest, killing the bias.
      Frequency response is UNCHANGED (alpha=74/1024 untouched) -> the GATE-2 stability verdict from
      eps_v50_gate2_lowpass.py carries and is strictly improved (bias removed, no new dynamics).
  (3) [in build_v52_tva.py] an 8th carrier repoint: FUN_0002eda8's raw gp-0x4f60 read, a live
      command-path lane V50 missed (-> gp-0x6b6c -> lane 9 -> gp-0x6ad6 -> FUN_0003a382).

FILTER (Q10, fc~=11.9 Hz), single 16-bit cell = state AND output:
    y  = ld.h  gp-0x1300            (filtered state/output)
    x  = ld.h  gp-0x4f60            (raw Sensor-B torque, s16, +/-25600)
    d  = x - y                      (s17, |d|<=51200)
    acc= 74*d                       (shift-add 74=64+8+2; NOT mulhi, which truncates d to 16 bits)
    acc= acc + 512                  (round-to-nearest)
    y += acc >> 10                  (alpha=74/1024)
    st.h y, gp-0x1300
  Overflow proof: |d|<=51200; 74*d<=3.79e6; +512 -> 3.789e6 << 2^31-1. No 32-bit signed overflow.

CAVE CONTRACT (identical hook mechanics to V50/V48B, Ghidra-verified transparent):
  Entered by `jr CAVE` planted at 0x7FEAC (displacing `cmp r0,r8` + `mov r8,r14`, 4 bytes) in the
  gp-0x4f60 producer epilogue (FUN_0007f3f8). The cave saves scratch, runs the EMA on a FRESH read of
  gp-0x4f60, writes the single cell, restores scratch, RE-EXECUTES the two displaced instructions LAST
  (PSW flags correct for the `bge 0x7feb4` at the return) and `jr 0x7FEB0`.
"""

import struct

GP = 0xFEDF8000
CAVE_BASE = 0xC4B34
HOOK = 0x7FEAC
RETURN = 0x7FEB0

# ---- filter parameters ----
ALPHA = 74          # Q10 EMA coefficient -> fc ~= 11.9 Hz at 1 kHz (eps_v50_gate2_lowpass.py)
ROUND = 512         # 1<<(10-1): round-to-nearest bias added before the >>10 (V52 delta #2)
D_SENSOR = 0x4F60   # raw gp-0x4f60 (Sensor-B driver column torque)

# RAM cell: gp-0x1300 (0xFEDF6D00) -- V51P-probe-proven free (0/24000 frames non-zero, full 16-bit,
# beacon live 100%), OUTSIDE the 0xb7260 mailbox array and the gp-0x1401..0x1502 poison region.
# This is the definitive live-probe clearance V50's gp-0x1500 never had. ONE 16-bit cell = state AND
# output. (D=gp-0x1100 was equally clean; either works.)
D_CELL = 0x1300


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def gp_field(disp_neg):
    """disp16 field for -disp_neg[gp], halfword-aligned (bit0=0)."""
    assert 0 < disp_neg <= 0x8000 and disp_neg % 2 == 0
    return (0x10000 - disp_neg) & 0xFFFF


# ---- Format encoders (identical to v50_cave_asm.py; verified vs real code.bin) ----
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

def ldst(op, reg2, reg1, field):
    return _le16((reg2 << 11) | (op << 5) | reg1) + _le16(field)

def ldh(disp_neg, reg2):  return ldst(0x39, reg2, 4, gp_field(disp_neg))     # ld.h -disp[gp],reg2
def sth(reg2, disp_neg):  return ldst(0x3B, reg2, 4, gp_field(disp_neg))     # st.h reg2,-disp[gp]
def stw_sp(reg2, off):    return ldst(0x3B, reg2, 3, (off & 0xFFFE) | 1)
def ldw_sp(reg2, off):    return ldst(0x39, reg2, 3, (off & 0xFFFE) | 1)

def jr(target, pc):
    disp = (target - pc) & 0x3FFFFF
    return _le16(0x0780 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


# displaced-instruction bytes (must match stock exactly)
CMP_R0_R8 = bytes.fromhex("e041")
MOV_R8_R14 = bytes.fromhex("0870")


def assemble_cave(base=CAVE_BASE, d_cell=D_CELL):
    """Return (bytes, annotated) for the SINGLE-CELL 16-bit EMA low-pass with round-to-nearest.

        y  = ld.h d_cell
        x  = ld.h gp-0x4f60
        d  = x - y                        (s17, |d|<=51200)
        acc= 74*d                         (shift-add, s32-safe)
        acc= acc + 512                    (V52: round-to-nearest)
        y += acc >> 10
        st.h y, d_cell
    Uses ONLY ld.h/st.h/sub/shl/add/sar/mov/addi -- every encoder verified vs real code.bin.
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
    emit(mov(R_D, R_A), "mov r11,r12")
    emit(shl(6, R_A), "shl 6,r12                 ; acc = 64*d")
    emit(mov(R_D, R_T), "mov r11,r13")
    emit(shl(3, R_T), "shl 3,r13                 ; t = 8*d")
    emit(add(R_T, R_A), "add r13,r12               ; acc = 72*d")
    emit(mov(R_D, R_T), "mov r11,r13")
    emit(shl(1, R_T), "shl 1,r13                 ; t = 2*d")
    emit(add(R_T, R_A), "add r13,r12               ; acc = 74*d")

    # V52: round-to-nearest -- acc += 512 before the >>10 so the shift rounds instead of flooring.
    emit(addi(ROUND, R_A, R_A), f"addi {ROUND},r12,r12          ; acc += 512  (round-to-nearest)")

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
          f"(cave capacity to 0xC4FEF)  [d_cell=gp-0x{D_CELL:04X}, round-to-nearest]")
    assert CAVE_BASE + len(cave) <= 0xC4FF0, "cave overruns free region"
    print(f"trampoline @0x{HOOK:05X}: {jr(CAVE_BASE, HOOK).hex()}  = jr 0x{CAVE_BASE:05X}")
    print()
    for off, b, mnem in ann:
        print(f"  0x{off:05X}: {b.hex():<8}  {mnem}")
    print(f"\nALPHA={ALPHA}/1024 (fc~11.9 Hz) + round-to-nearest, single 16-bit cell gp-0x{D_CELL:04X}.")
    print("Encoders all verified vs real code.bin. Ghidra re-disassemble the built image before flash.")
    print("Full cave hex:")
    print(cave.hex())


if __name__ == "__main__":
    main()
