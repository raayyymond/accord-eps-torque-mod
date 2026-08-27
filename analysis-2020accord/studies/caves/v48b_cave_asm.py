"""
studies/caves/v48b_cave_asm.py -- the V48B notch code cave, assembled from byte-verified V850E2 encodings.

Standalone so the riskiest artifact (the cave bytes) can be inspected and Ghidra-re-disassembled in
isolation before it is embedded in builds/v18_v49/build_v48b_tva.py. Every encoding here was cross-validated by the
firmware-codepath-tracer subagents against >=2 real instructions already present in stock code.bin.

CAVE CONTRACT
  Entered by `jr CAVE` planted at 0x7FEAC (displacing `cmp r0,r8` + `mov r8,r14`, 4 bytes).
  At entry r8 = settled gp-0x4f60 (producer FUN_0007f3f8's shared epilogue). The cave:
    1. saves r10/r11/r12 to the stack (transparent -- restored before return),
    2. runs the DF-I notch biquad on a FRESH read of gp-0x4f60 (does NOT depend on r8),
    3. stores the filtered output to gp-0x1500 (the cell the repointed carriers read),
    4. restores r10/r11/r12 and sp,
    5. re-executes `cmp r0,r8` + `mov r8,r14` LAST so the PSW flags are correct for the
       `bge 0x7feb4` at the return address, then `jr 0x7FEB0`.
  Net effect: register/flag state at 0x7FEB0 is byte-identical to the original two instructions,
  PLUS the notch RAM write. Fully transparent to FUN_0007f3f8.

RAM (gp = 0xFEDF8000):
  y1 / OUTPUT = gp-0x1500 (0xFEDF6B00)  <- carriers ld.h this; V31P flash-validated free
  x1          = gp-0x14FC (0xFEDF6B04)
  x2          = gp-0x14FA (0xFEDF6B06)
  y2          = gp-0x14F8 (0xFEDF6B08)

Biquad (Q12): acc = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2 ; y = clamp(acc>>12, +/-25600).
  Folded to a uniform mulhi/add chain with immediates [b0,b1,b2,-a1,-a2] = [4045,-7949,3977,7949,-3926].
"""

import struct

GP = 0xFEDF8000
CAVE_BASE = 0xC4B34
HOOK = 0x7FEAC
RETURN = 0x7FEB0

# RAM displacements (negative gp offsets)
D_OUT = 0x1500   # y1 / output
D_X1 = 0x14FC
D_X2 = 0x14FA
D_Y2 = 0x14F8
D_SENSOR = 0x4F60  # raw gp-0x4f60

# Q12 notch coefficients (studies/models/eps_v48b_notch_design.py) and the folded mulhi immediates.
B0, B1, B2, A1, A2 = 4045, -7949, 3977, -7949, 3926
IMM = [B0, B1, B2, -A1, -A2]   # [4045, -7949, 3977, 7949, -3926]
CLAMP = 0x6400  # +/-25600


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def gp_field(disp_neg):
    """disp16 field for -disp_neg[gp], halfword-aligned (bit0=0). field = (0x10000 - disp) & 0xFFFF."""
    assert 0 < disp_neg <= 0x8000 and disp_neg % 2 == 0
    return (0x10000 - disp_neg) & 0xFFFF


# ---- Format encoders (all verified against real code.bin instructions) ----
def fmt1(op, reg1, reg2):            # 2B reg-reg: (reg2<<11)|(op<<5)|reg1
    return _le16((reg2 << 11) | (op << 5) | reg1)

def mov(reg1, reg2):    return fmt1(0x00, reg1, reg2)   # reg2 = reg1
def add(reg1, reg2):    return fmt1(0x0E, reg1, reg2)   # reg2 += reg1
def cmp_(reg1, reg2):   return fmt1(0x0F, reg1, reg2)   # flags(reg2 - reg1)

def sar(imm5, reg2):                 # 2B Format II: (reg2<<11)|(0x15<<5)|imm5
    assert 0 <= imm5 <= 31
    return _le16((reg2 << 11) | (0x15 << 5) | imm5)

def fmt6(op, reg1, reg2, imm16):     # 4B: word1=(reg2<<11)|(op<<5)|reg1 ; word2=imm16 (raw two's comp)
    return _le16((reg2 << 11) | (op << 5) | reg1) + _le16(imm16 & 0xFFFF)

def addi(imm16, reg1, reg2):  return fmt6(0x30, reg1, reg2, imm16)
def movea(imm16, reg1, reg2): return fmt6(0x31, reg1, reg2, imm16)
def mulhi(imm16, reg1, reg2): return fmt6(0x37, reg1, reg2, imm16)

def ldst(op, reg2, reg1, field):     # 4B Format VII: word1=(reg2<<11)|(op<<5)|reg1 ; word2=field
    return _le16((reg2 << 11) | (op << 5) | reg1) + _le16(field)

def ldh(disp_neg, reg2):  return ldst(0x39, reg2, 4, gp_field(disp_neg))          # ld.h -disp[gp],reg2
def sth(reg2, disp_neg):  return ldst(0x3B, reg2, 4, gp_field(disp_neg))          # st.h reg2,-disp[gp]
def stw_sp(reg2, off):    return ldst(0x3B, reg2, 3, (off & 0xFFFE) | 1)          # st.w reg2,off[sp]
def ldw_sp(reg2, off):    return ldst(0x39, reg2, 3, (off & 0xFFFE) | 1)          # ld.w off[sp],reg2

def bcond(cond, disp):               # 2B Format III; disp is a small even byte offset from this insn
    d8 = (disp >> 1) & 0xFF
    return _le16(((d8 >> 3) << 11) | (0xB << 7) | ((d8 & 7) << 4) | cond)
def ble(disp): return bcond(0x7, disp)
def bge(disp): return bcond(0xE, disp)

def jr(target, pc):                  # 4B jr disp22 (V31P-proven encoder)
    disp = (target - pc) & 0x3FFFFF
    return _le16(0x0780 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


# Displaced-instruction bytes (must match stock exactly): cmp r0,r8 = e0 41 ; mov r8,r14 = 08 70
CMP_R0_R8 = bytes.fromhex("e041")
MOV_R8_R14 = bytes.fromhex("0870")
assert cmp_(0, 8) == CMP_R0_R8, "cmp r0,r8 encoder mismatch"
assert mov(8, 14) == MOV_R8_R14, "mov r8,r14 encoder mismatch"


def assemble_cave(base=CAVE_BASE):
    """Return (bytes, annotated[list of (offset, bytes, mnemonic)])."""
    ann = []
    buf = bytearray()

    def emit(b, mnem):
        ann.append((base + len(buf), bytes(b), mnem))
        buf.extend(b)

    R_ACC, R_TMP, R_SIG = 10, 11, 12

    # --- save scratch (transparent) ---
    emit(addi(-16, 3, 3), "addi -16,sp,sp")
    emit(stw_sp(R_ACC, 0), "st.w r10,0[sp]")
    emit(stw_sp(R_TMP, 4), "st.w r11,4[sp]")
    emit(stw_sp(R_SIG, 8), "st.w r12,8[sp]")

    # --- biquad: r10 = sum IMM[i]*sig[i] ; sig = [x, x1, x2, y1, y2] ---
    sigs = [D_SENSOR, D_X1, D_X2, D_OUT, D_Y2]
    for i, (imm, disp) in enumerate(zip(IMM, sigs)):
        emit(ldh(disp, R_SIG), f"ld.h -0x{disp:04X}[gp],r12   ; sig{i}")
        if i == 0:
            emit(mulhi(imm, R_SIG, R_ACC), f"mulhi {imm},r12,r10   ; acc = sig0*{imm}")
        else:
            emit(mulhi(imm, R_SIG, R_TMP), f"mulhi {imm},r12,r11")
            emit(add(R_TMP, R_ACC), "add r11,r10")

    # --- y = clamp(acc >> 12, +/-25600) ---
    emit(sar(12, R_ACC), "sar 12,r10")
    emit(movea(CLAMP, 0, R_TMP), "movea 0x6400,r0,r11   ; +25600")
    emit(cmp_(R_TMP, R_ACC), "cmp r11,r10")
    emit(ble(4), "ble +4")
    emit(mov(R_TMP, R_ACC), "mov r11,r10           ; r10 = +25600")
    emit(movea(-CLAMP, 0, R_TMP), "movea 0x9c00,r0,r11   ; -25600")
    emit(cmp_(R_TMP, R_ACC), "cmp r11,r10")
    emit(bge(4), "bge +4")
    emit(mov(R_TMP, R_ACC), "mov r11,r10           ; r10 = -25600")

    # --- state shift: x2=old x1 ; x1=x ; y2=old y1 ; y1=y ---
    emit(ldh(D_X1, R_TMP), "ld.h -0x14FC[gp],r11  ; old x1")
    emit(sth(R_TMP, D_X2), "st.h r11,-0x14FA[gp]  ; x2 = old x1")
    emit(ldh(D_SENSOR, R_TMP), "ld.h -0x4F60[gp],r11  ; x (raw)")
    emit(sth(R_TMP, D_X1), "st.h r11,-0x14FC[gp]  ; x1 = x")
    emit(ldh(D_OUT, R_TMP), "ld.h -0x1500[gp],r11  ; old y1")
    emit(sth(R_TMP, D_Y2), "st.h r11,-0x14F8[gp]  ; y2 = old y1")
    emit(sth(R_ACC, D_OUT), "st.h r10,-0x1500[gp]  ; y1 = y (output)")

    # --- restore scratch ---
    emit(ldw_sp(R_ACC, 0), "ld.w 0[sp],r10")
    emit(ldw_sp(R_TMP, 4), "ld.w 4[sp],r11")
    emit(ldw_sp(R_SIG, 8), "ld.w 8[sp],r12")
    emit(addi(16, 3, 3), "addi 16,sp,sp")

    # --- re-exec displaced (flags fresh for the bge at 0x7feb0), return ---
    emit(CMP_R0_R8, "cmp r0,r8             ; displaced (sets flags)")
    emit(MOV_R8_R14, "mov r8,r14            ; displaced")
    emit(jr(RETURN, base + len(buf)), f"jr 0x{RETURN:05X}")
    return bytes(buf), ann


def main():
    cave, ann = assemble_cave()
    print(f"CAVE @0x{CAVE_BASE:05X}  length = {len(cave)} bytes  ends 0x{CAVE_BASE + len(cave):05X}  "
          f"(cave capacity 1212 B to 0xC4FEF)")
    assert CAVE_BASE + len(cave) <= 0xC4FF0, "cave overruns free region"
    print(f"trampoline @0x{HOOK:05X}: {jr(CAVE_BASE, HOOK).hex()}  = jr 0x{CAVE_BASE:05X}")
    print()
    for off, b, mnem in ann:
        print(f"  0x{off:05X}: {b.hex():<8}  {mnem}")
    print()
    print("full cave hex:")
    print(cave.hex())


if __name__ == "__main__":
    main()
