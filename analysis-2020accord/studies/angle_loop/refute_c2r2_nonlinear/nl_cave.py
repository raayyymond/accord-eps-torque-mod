# -*- coding: utf-8 -*-
r"""nl_cave.py -- C2 rev 2 NONLINEAR refuter (2026-10-01): an INDEPENDENT V850E2 mini-interpreter for the four
candidate caves (rev2-A P2 / F2, rev2-B D2a / B0r) and an INDEPENDENT scalar mirror of the cave's listed
arithmetic, checked against each other on random and edge inputs.  ANALYSIS ONLY: reads hex files, writes nothing
but its own stdout/cache.  Nothing here imports the designers' ds_asm / ds_lane / c1_lib.

Decoder written from the V850E2 ISA formats (this file's own field extraction; every form used by the caves):
  Format I    reg-reg   hw = reg2<<11 | op6<<5 | reg1     mov 0x00, jmp 0x03 (reg2=0), sub 0x0D, add 0x0E, cmp 0x0F
  Format II   imm5      hw = reg2<<11 | op6<<5 | imm5     mov 0x10, sar 0x15, shl 0x16
  Format III  bcond     hw = d8..d4<<11 | 1011<<7 | d3..d1<<4 | cccc
  Format V    jr/jarl   hw1 = reg2<<11 | 11110<<6 | d21..d16, hw2 = d15..d0 (d0 = 0)
  Format VI   addi 0x30 / movea 0x31 / andi 0x36 imm16 ; mov imm32 (op 0x31, reg2 = 0, 6 bytes)
  Format VII  ld.h 0x39 (disp even) ; ld.hu op 0x3F with hw2 bit0 = 1 (disp = hw2 & ~1)
  Format XI   op 0x3F, hw2 bit0 = 0: mul (hw2 & 0x7FF == 0x220) ; cmov reg (hw2 bits 10..5 = 011001, cccc in bits 4..1)
Memory: gp = 0xFEDF8000; the cave + its table at 0xC4C00; three RAM half-words (gp-0x6abe, gp-0x6a5e, gp-0x4f68).
"""
from __future__ import annotations

import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AL = HERE.parent
GP = 0xFEDF8000
BASE = 0xC4C00
HOOK_RET = 0x29D7A          # jarl 0xC4C00,r6 at 0x29D76 -> r6 = 0x29D7A
FRZ_RET = 0x29D7E
M32 = 0xFFFFFFFF

HEX = {
    "P2": AL / "c2" / "rev2A" / "c2_cave_P2.hex",
    "F2": AL / "c2" / "rev2A" / "c2_cave_F2.hex",
    "D2a": AL / "panel" / "D-structure" / "ds_cave_D2a.hex",
    "B0r": AL / "panel" / "D-structure" / "ds_cave_B0r.hex",
}


def load_hex(name):
    return bytes.fromhex(HEX[name].read_text().replace("\n", " "))


def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


class Cpu:
    def __init__(self, mem: dict):
        self.r = [0] * 32
        self.mem = mem             # byte address -> byte
        self.z = self.s = self.cy = self.ov = 0
        self.trace = []

    def rd(self, a, n):
        return int.from_bytes(bytes(self.mem[(a + i) & M32] for i in range(n)), "little")

    def setr(self, i, v):
        if i:
            self.r[i] = v & M32

    def flags_sub(self, a, b):                 # a - b
        res = (a - b) & M32
        self.cy = 1 if (a & M32) < (b & M32) else 0
        sa, sb, sr = s32(a) < 0, s32(b) < 0, s32(res) < 0
        self.ov = 1 if (sa != sb and sr != sa) else 0
        self.z = 1 if res == 0 else 0
        self.s = 1 if s32(res) < 0 else 0
        return res

    def flags_add(self, a, b):
        res = (a + b) & M32
        self.cy = 1 if (a & M32) + (b & M32) > M32 else 0
        sa, sb, sr = s32(a) < 0, s32(b) < 0, s32(res) < 0
        self.ov = 1 if (sa == sb and sr != sa) else 0
        self.z = 1 if res == 0 else 0
        self.s = 1 if s32(res) < 0 else 0
        return res

    def cond(self, c):
        z, s, cy, ov = self.z, self.s, self.cy, self.ov
        return {0x0: ov, 0x1: cy, 0x2: z, 0x3: cy | z, 0x4: s, 0x5: 1, 0x6: s ^ ov, 0x7: (s ^ ov) | z,
                0x8: 1 - ov, 0x9: 1 - cy, 0xA: 1 - z, 0xB: 1 - (cy | z), 0xC: 1 - s, 0xD: 0,
                0xE: 1 - (s ^ ov), 0xF: 1 - ((s ^ ov) | z)}[c]

    def step(self, pc):
        hw = self.rd(pc, 2)
        reg2, op6, reg1 = hw >> 11, (hw >> 5) & 0x3F, hw & 0x1F
        r = self.r
        # Format III bcond
        if (hw >> 7) & 0xF == 0xB:
            cc = hw & 0xF
            disp = sx((((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 7) << 1), 9)
            self.trace.append((pc, "b%x" % cc))
            return (pc + disp) & M32 if self.cond(cc) else pc + 2
        # Format V jr/jarl (bits 10..6 = 11110)
        if (hw >> 6) & 0x1F == 0x1E and (op6 >> 1) == 0x1E:
            hw2 = self.rd(pc + 2, 2)
            assert hw2 & 1 == 0, "odd Format-V displacement = not a jr/jarl"
            disp = sx(((hw & 0x3F) << 16) | hw2, 22)
            if reg2:
                self.setr(reg2, pc + 4)
            self.trace.append((pc, "jr" if reg2 == 0 else "jarl"))
            return (pc + disp) & M32
        if op6 == 0x00:                                   # mov reg1,reg2
            self.setr(reg2, r[reg1]); return pc + 2
        if op6 == 0x03 and reg2 == 0:                     # jmp [reg1]
            self.trace.append((pc, "jmp"))
            return r[reg1]
        if op6 == 0x0D:                                   # sub reg1,reg2 : reg2 = reg2 - reg1
            self.setr(reg2, self.flags_sub(r[reg2], r[reg1])); return pc + 2
        if op6 == 0x0E:                                   # add
            self.setr(reg2, self.flags_add(r[reg2], r[reg1])); return pc + 2
        if op6 == 0x0F:                                   # cmp reg1,reg2 : flags of reg2 - reg1
            self.flags_sub(r[reg2], r[reg1]); return pc + 2
        if op6 == 0x10:                                   # mov imm5
            self.setr(reg2, sx(reg1, 5)); return pc + 2
        if op6 == 0x15:                                   # sar imm5
            n = reg1
            v = s32(r[reg2])
            self.cy = (v >> (n - 1)) & 1 if n else 0
            res = (v >> n) & M32
            self.ov = 0; self.z = int(res == 0); self.s = int(s32(res) < 0)
            self.setr(reg2, res); return pc + 2
        if op6 == 0x16:                                   # shl imm5
            n = reg1
            v = r[reg2] & M32
            self.cy = (v >> (32 - n)) & 1 if n else 0
            res = (v << n) & M32
            self.ov = 0; self.z = int(res == 0); self.s = int(s32(res) < 0)
            self.setr(reg2, res); return pc + 2
        if op6 == 0x30:                                   # addi imm16,reg1,reg2
            imm = sx(self.rd(pc + 2, 2), 16)
            self.setr(reg2, self.flags_add(r[reg1], imm & M32)); return pc + 4
        if op6 == 0x31:
            if reg2 == 0:                                 # mov imm32,reg1 (6 bytes)
                imm = self.rd(pc + 2, 4)
                self.setr(reg1, imm); return pc + 6
            imm = sx(self.rd(pc + 2, 2), 16)              # movea imm16,reg1,reg2 (no flags)
            self.setr(reg2, (r[reg1] + imm) & M32); return pc + 4
        if op6 == 0x36:                                   # andi imm16 (zero-extended)
            imm = self.rd(pc + 2, 2)
            res = r[reg1] & imm
            self.ov = 0; self.z = int(res == 0); self.s = 0
            self.setr(reg2, res); return pc + 4
        if op6 == 0x39:                                   # ld.h disp16[reg1],reg2 (disp even)
            hw2 = self.rd(pc + 2, 2)
            assert hw2 & 1 == 0
            a = (r[reg1] + sx(hw2, 16)) & M32
            self.setr(reg2, sx(self.rd(a, 2), 16) & M32); return pc + 4
        if op6 == 0x3F:
            hw2 = self.rd(pc + 2, 2)
            if hw2 & 1:                                   # ld.hu
                a = (r[reg1] + sx(hw2 & 0xFFFE, 16)) & M32
                self.setr(reg2, self.rd(a, 2)); return pc + 4
            reg3 = hw2 >> 11
            sub = hw2 & 0x7FF
            if sub == 0x220:                              # mul reg1,reg2,reg3 : reg3:reg2 = reg2*reg1 (signed)
                prod = s32(r[reg2]) * s32(r[reg1])
                lo, hi = prod & M32, (prod >> 32) & M32
                self.setr(reg2, lo)
                if reg3 != reg2:
                    self.setr(reg3, hi)
                return pc + 4
            if (sub >> 5) == 0x19 and (sub & 1) == 0:     # cmov cccc,reg1,reg2,reg3
                cc = (sub >> 1) & 0xF
                self.setr(reg3, r[reg1] if self.cond(cc) else r[reg2]); return pc + 4
        raise NotImplementedError("pc %#x hw %#06x op6 %#x" % (pc, hw, op6))


def run_cave(code: bytes, regs: dict, ram: dict, max_steps=400):
    """execute the cave from BASE with r6 = HOOK_RET; returns (cpu, exit_pc)."""
    mem = {}
    for i, b in enumerate(code):
        mem[BASE + i] = b
    for addr, (val, n) in ram.items():
        for i in range(n):
            mem[(addr + i) & M32] = (val >> (8 * i)) & 0xFF
    cpu = Cpu(mem)
    for k, v in regs.items():
        cpu.r[k] = v & M32
    cpu.r[4] = GP
    cpu.r[6] = HOOK_RET
    pc = BASE
    for _ in range(max_steps):
        if not (BASE <= pc < BASE + len(code)):
            return cpu, pc
        pc = cpu.step(pc)
    raise RuntimeError("cave did not exit")


# ------------------------------------------------------------------------------------------------------------------
# the INDEPENDENT scalar mirror of the listed arithmetic (what the lane model uses)
# ------------------------------------------------------------------------------------------------------------------
def parse_table(code: bytes):
    """table address from the 6-byte mov imm32 (op 0x31, reg2 0) in the cave; rows (X u16, G u16, S s16) to 0xFFFF."""
    for off in range(0, len(code) - 6, 2):
        hw = code[off] | (code[off + 1] << 8)
        if (hw >> 5) & 0x3F == 0x31 and (hw >> 11) == 0 and (hw & 0x1F) == 9:
            taddr = struct.unpack_from("<I", code, off + 2)[0]
            break
    t = taddr - BASE
    rows = []
    while True:
        X, G, S = struct.unpack_from("<HHh", code, t)
        rows.append((X, G, S))
        if X == 0xFFFF:
            break
        t += 6
    return taddr, rows


def walk_G(rows, v):
    v &= 0xFFFF
    if v <= rows[0][0]:
        return rows[0][1]
    i = 0
    while v > rows[i + 1][0]:
        i += 1
    X, G, S = rows[i]
    return s32(G + (s32((v - X) * S) >> 12))


def mirror(kind, rows, r16_sp, r26, abe, v, tq_abs, ramp):
    """returns (r16 out = E', e5_or_None (None = normal return -> lane computes E'>>5 ; 0 = freeze), r26 out, exit)."""
    E = s32((r16_sp << 2) - r26)
    op = r26
    if kind == "fresh":
        a = s32(abe)
        op = a if ((a + 13000) & M32) <= 26000 else 0
    G = walk_G(rows, v)
    Ep = s32(E * G) >> 8
    frz = (tq_abs & 0xFFFF) > 512 or (ramp & 0x8000) == 0
    return Ep, (0 if frz else None), op, (FRZ_RET if frz else HOOK_RET)


def check(name, n_rand=20000, seed=3):
    code = load_hex(name)
    kind = "fresh" if code[4:8] == bytes.fromhex("24d74295") else "held"
    taddr, rows = parse_table(code)
    rnd = random.Random(seed)
    bad = 0
    edge_abe = [0x7FFF, -0x8000, 13000, 13001, -13000, -13001, 0, 1, -1, 26000, -26000]
    edge_v = sorted({r[0] for r in rows[:-1]} | {r[0] + 1 for r in rows[:-1]} | {max(r[0] - 1, 0) for r in rows[:-1]}
                    | {0, 0xFFFE, 0xFFFF})
    cases = []
    for _ in range(n_rand):
        cases.append((rnd.randint(-16384, 16384), rnd.randint(-65535, 65535), rnd.randint(-0x8000, 0x7FFF),
                      rnd.randint(0, 0xFFFF) if rnd.random() < 0.3 else rnd.randint(0, 9000),
                      rnd.randint(0, 0xFFFF) if rnd.random() < 0.2 else rnd.randint(0, 1100),
                      rnd.choice([0x8000, 0, 0x7FFF, rnd.randint(0, 0x8000), 0xFFFF, 0x8001])))
    for a in edge_abe:
        for vv in edge_v:
            for tq in (0, 511, 512, 513, 0xFFFF):
                cases.append((rnd.randint(-16384, 16384), rnd.randint(-65535, 65535), a, vv, tq, 0x8000))
    LIVE = (1, 2, 3, 5, 7, 10, 11, 12, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 31)
    for (sp, r26, abe, v, tq, ramp) in cases:
        regs = {16: sp, 26: r26, 14: ramp}
        junk = {k: rnd.getrandbits(32) for k in LIVE if k != 14}
        regs.update(junk)
        ram = {(GP - 0x6abe) & M32: (abe & 0xFFFF, 2), (GP - 0x6a5e) & M32: (v, 2), (GP - 0x4f68) & M32: (tq, 2)}
        cpu, ex = run_cave(code, regs, ram)
        Ep, e5, op, exm = mirror(kind, rows, sp, r26, abe, v, tq, ramp)
        r6 = s32(cpu.r[6])
        ok = (s32(cpu.r[16]) == Ep and ex == exm and
              (r6 == 0 if e5 == 0 else (ex == HOOK_RET)) and
              (kind == "held" or s32(cpu.r[26]) == op) and
              all(cpu.r[k] == (regs[k] & M32) for k in LIVE))
        if kind == "held":
            ok &= s32(cpu.r[26]) == s32(r26)             # B0r/F2 must leave r26 alone? (not required: r26 dead)
        if not ok:
            bad += 1
            if bad < 4:
                print("  MISMATCH", name, dict(sp=sp, r26=r26, abe=abe, v=v, tq=tq, ramp=ramp),
                      "cpu r16", s32(cpu.r[16]), "mirror", Ep, "exit", hex(ex), hex(exm), "r6", r6, "r26", s32(cpu.r[26]), op)
    # G over the whole speed word via the interpreter's own walk (r16 = 256/4 => E = 256 - r26(0) -> E' = G)
    gbad = 0
    for vv in list(range(0, 9001)) + [rnd.randint(9001, 0xFFFF) for _ in range(500)]:
        cpu, ex = run_cave(code, {16: 64, 26: 0, 14: 0x8000}, {(GP - 0x6abe) & M32: (0, 2), (GP - 0x6a5e) & M32: (vv, 2),
                                                                (GP - 0x4f68) & M32: (0, 2)})
        if s32(cpu.r[16]) != walk_G(rows, vv):
            gbad += 1
    print(f"{name:4s} kind {kind:5s} table @{taddr:#x} rows {len(rows)} code {taddr - BASE} B total {len(code)} B | "
          f"interpreter vs mirror: {bad} mismatches in {len(cases)} cases | G(v) v=0..9000+500 rnd: {gbad} mismatches")
    return dict(name=name, kind=kind, rows=rows, taddr=taddr, bad=bad, gbad=gbad, ncase=len(cases))


if __name__ == "__main__":
    out = [check(n) for n in ("P2", "F2", "D2a", "B0r")]
    for o in out:
        Gs = [walk_G(o["rows"], int(round(v * 3.6 * 64))) for v in (3.1, 8.0, 10.0, 11.75, 11.9, 15.0, 17.0, 22.0, 26.9, 30.0)]
        print(f"  {o['name']}: rows {o['rows']}\n        G at 3.1/8/10/11.75/11.9/15/17/22/26.9/30 m/s = {Gs}, min over 0..9000 = "
              f"{min(walk_G(o['rows'], v) for v in range(9001))}")
    sys.exit(0 if all(o["bad"] == 0 and o["gbad"] == 0 for o in out) else 1)
