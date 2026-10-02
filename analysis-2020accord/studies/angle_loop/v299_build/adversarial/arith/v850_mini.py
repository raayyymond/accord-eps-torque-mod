"""Independent minimal V850E2 interpreter (ADV-arithmetic V299) -- written from the V850E2 encoding rules, NOT the kit's
panel2/score_time.Cpu2. Supports only the forms the V298/V299 caves use; any other opcode raises (so coverage is explicit).
Executes cave bytes straight from an image; RAM is a dict of the gp cells the cave may read; any store raises."""
import struct
GP = 0xFEDF8000
M32 = 0xFFFFFFFF
def s32(x): x &= M32; return x - (1 << 32) if x & 0x80000000 else x
def sx(x, b): x &= (1 << b) - 1; return x - (1 << b) if x >> (b - 1) else x
EXITS = {0x2A164: 'SKIP', 0x29D7E: 'FRZ29D7E', 0x29D7A: 'DONE'}

class Cave:
    def __init__(self, img): self.img = img
    def run(self, regs, ram, max_steps=400):
        R = [0] * 32
        for k, v in regs.items(): R[k] = v & M32
        R[4] = GP
        Z = S = OV = CY = 0
        pc = 0xC4C00; img = self.img; reads = []
        def rd(addr, size, signed):
            addr &= M32
            if addr >= 0xFE000000:
                if (addr, size) not in ram: raise KeyError('unmodelled RAM read %x/%d' % (addr, size))
                v = ram[(addr, size)]
                reads.append(addr)
            else:
                v = int.from_bytes(img[addr:addr + size], 'little')
            return sx(v, size * 8) & M32 if signed else v & ((1 << (size * 8)) - 1)
        def flags_sub(a, b):  # a - b
            nonlocal Z, S, OV, CY
            r = (a - b) & M32
            Z = int(r == 0); S = r >> 31; CY = int((a & M32) < (b & M32))
            OV = int(((a ^ b) & (a ^ r)) >> 31 & 1)
            return r
        def cond(c):
            return [OV, CY, Z, CY | Z, S, 1, S ^ OV, (S ^ OV) | Z, 1 - OV, 1 - CY, 1 - Z, 1 - (CY | Z), 1 - S, None, 1 - (S ^ OV), 1 - ((S ^ OV) | Z)][c]
        for _ in range(max_steps):
            if pc in EXITS and pc != 0xC4C00: return EXITS[pc], R, reads
            hw1 = struct.unpack_from('<H', img, pc)[0]
            op = (hw1 >> 5) & 0x3F; r1 = hw1 & 31; r2 = hw1 >> 11
            if (hw1 & 0x0780) == 0x0580 and op >> 2 == 0b1011:  # Format III bcond: bits 10:7 = 1011
                c = hw1 & 0xF; d = sx(((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1), 9)
                if cond(c): pc = (pc + d) & M32
                else: pc += 2
                continue
            if op < 0x30:
                if op == 0x00 and r2 != 0: R[r2] = R[r1]; pc += 2; continue                    # mov reg
                if op == 0x03 and r2 == 0: pc = R[r1]; continue                                # jmp [reg1]
                if op == 0x09: R[r2] = (R[r2] ^ R[r1]) & M32; Z = int(R[r2] == 0); S = R[r2] >> 31; OV = 0; pc += 2; continue  # xor
                if op == 0x0C: R[r2] = flags_sub(R[r1], R[r2]); pc += 2; continue              # subr: r2 = r1 - r2
                if op == 0x0D: R[r2] = flags_sub(R[r2], R[r1]); pc += 2; continue              # sub: r2 = r2 - r1
                if op == 0x0E: R[r2] = (R[r2] + R[r1]) & M32; pc += 2; continue                # add (flags unused here)
                if op == 0x0F: flags_sub(R[r2], R[r1]); pc += 2; continue                      # cmp reg1,reg2
                if op == 0x10: R[r2] = sx(r1, 5) & M32; pc += 2; continue                      # mov imm5
                if op == 0x15: R[r2] = (s32(R[r2]) >> r1) & M32; pc += 2; continue             # sar imm5
                if op == 0x16: R[r2] = (R[r2] << r1) & M32; pc += 2; continue                  # shl imm5
                raise NotImplementedError('pc %x hw %04x op %x' % (pc, hw1, op))
            hw2 = struct.unpack_from('<H', img, pc + 2)[0]
            if op == 0x31 and r2 == 0:                                                         # mov imm32 (6 B)
                R[r1] = struct.unpack_from('<I', img, pc + 2)[0]; pc += 6; continue
            if op == 0x30: R[r2] = (R[r1] + sx(hw2, 16)) & M32; pc += 4; continue              # addi
            if op == 0x31: R[r2] = (R[r1] + sx(hw2, 16)) & M32; pc += 4; continue              # movea
            if op == 0x36: R[r2] = R[r1] & hw2; Z = int(R[r2] == 0); S = 0; OV = 0; pc += 4; continue  # andi
            if op == 0x39:                                                                     # ld.h / ld.w
                d = sx(hw2 & 0xFFFE, 16)
                R[r2] = rd(R[r1] + d, 4, True) if hw2 & 1 else rd(R[r1] + d, 2, True); pc += 4; continue
            if op in (0x3C, 0x3D) and r2 == 0 and not (hw2 & 1):                              # jr disp22 (field 0x1E in bits 10:6; target even)
                d = sx(((hw1 & 0x3F) << 16) | hw2, 22); pc = (pc + d) & M32; continue
            if op == 0x3F:
                if hw2 & 1:                                                                    # ld.hu
                    R[r2] = rd(R[r1] + sx(hw2 & 0xFFFE, 16), 2, False); pc += 4; continue
                r3 = hw2 >> 11; sub = hw2 & 0x7FF
                if sub == 0x220:                                                               # mul reg1,reg2,reg3 (signed 64)
                    p = s32(R[r2]) * s32(R[r1]); lo = p & M32; hi = (p >> 32) & M32
                    if r3: R[r3] = hi
                    R[r2] = lo; pc += 4; continue
                if (sub >> 5) == 0x19 and not (sub & 1):                                       # cmov cccc,reg1,reg2,reg3
                    c = (sub >> 1) & 0xF
                    R[r3] = R[r1] if cond(c) else R[r2]; pc += 4; continue
                raise NotImplementedError('pc %x %04x %04x' % (pc, hw1, hw2))
            if op in (0x3A, 0x3B) or (op == 0x3F and False): raise RuntimeError('STORE at %x' % pc)
            raise NotImplementedError('pc %x hw %04x op %x' % (pc, hw1, op))
        raise RuntimeError('no exit')
