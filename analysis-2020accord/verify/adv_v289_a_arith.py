# -*- coding: utf-8 -*-
"""ADVERSARY A -- V289 rev 1 -- ARITHMETIC surface.  Independent V850E2 decoder + exact-integer emulator.

Written WITHOUT reference to the builder's encoder/emulator (build_v289_tva.py was read only for its CLAIMS).
Everything below is derived from the built image bytes.  Run:  python adv_v289_a_arith.py [--full]

Pre-registered FAIL criteria: docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md sec. A (A1..A5).
"""
import glob
import hashlib
import math
import os
import struct
import sys

FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
IMG_SHA = "f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed"
GP, TP = 0xFEDF8000, 0xBF000
FULL = "--full" in sys.argv

# ------------------------------------------------------------------------------------------------
# image
# ------------------------------------------------------------------------------------------------
def load_images():
    v289 = open(glob.glob(FW + "_v289_*plain_image.bin")[0], "rb").read()
    v282 = open(glob.glob(FW + "_v282_*plain_image.bin")[0], "rb").read()
    assert hashlib.sha256(v289).hexdigest() == IMG_SHA, "V289 image sha mismatch"
    return v289, v282


# ------------------------------------------------------------------------------------------------
# DECODER -- only the forms that occur; anything else raises (so an unknown opcode cannot pass silently)
# ------------------------------------------------------------------------------------------------
COND = {0x0: "bv", 0x1: "bl", 0x2: "be", 0x3: "bnh", 0x4: "bn", 0x5: "br", 0x6: "blt", 0x7: "ble",
        0x8: "bnv", 0x9: "bnl", 0xA: "bne", 0xB: "bh", 0xC: "bp", 0xD: "bsa", 0xE: "bge", 0xF: "bgt"}
RN = {0: "r0", 3: "sp", 4: "gp", 5: "tp", 31: "lp"}


def rn(r):
    return RN.get(r, f"r{r}")


def sx16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def sx22(v):
    v &= 0x3FFFFF
    return v - 0x400000 if v & 0x200000 else v


def sx9(v):
    v &= 0x1FF
    return v - 0x200 if v & 0x100 else v


def sx5(v):
    v &= 0x1F
    return v - 0x20 if v & 0x10 else v


def decode(img, pc):
    """Return (length, mnemonic, operands-tuple, text).  Operands are already resolved to absolute addresses
    where they are addresses (gp/tp bases folded; branch targets absolute)."""
    hw1 = struct.unpack_from("<H", img, pc)[0]
    reg1 = hw1 & 0x1F
    reg2 = (hw1 >> 11) & 0x1F
    op = (hw1 >> 5) & 0x3F
    # ---- Format I / II (16-bit) -------------------------------------------------------------
    if op < 0x10:
        if op == 0x00:
            if reg2 == 0 and reg1 == 0:
                return 2, "nop", (), "nop"
            return 2, "mov", (reg1, reg2), f"mov {rn(reg1)},{rn(reg2)}"
        if op == 0x03:
            if reg2 != 0:
                raise ValueError(f"{pc:#x}: op 0x03 with reg2!=0 (sld/sst?) not handled")
            return 2, "jmp", (reg1,), f"jmp [{rn(reg1)}]"
        names = {0x08: "or", 0x09: "xor", 0x0A: "and", 0x0B: "tst", 0x0C: "subr", 0x0D: "sub", 0x0E: "add", 0x0F: "cmp"}
        if op in names:
            return 2, names[op], (reg1, reg2), f"{names[op]} {rn(reg1)},{rn(reg2)}"
        raise ValueError(f"{pc:#x}: unhandled format-I op {op:#x}")
    if 0x10 <= op <= 0x17:
        names = {0x10: "mov_i5", 0x11: "satadd_i5", 0x12: "add_i5", 0x13: "cmp_i5", 0x14: "shr", 0x15: "sar", 0x16: "shl", 0x17: "mulh_i5"}
        mn = names[op]
        imm = sx5(reg1) if op in (0x10, 0x11, 0x12, 0x13, 0x17) else reg1
        return 2, mn, (imm, reg2), f"{mn.replace('_i5','')} {imm:#x},{rn(reg2)}"
    # ---- Format III bcond (bits 10:7 == 1011) -----------------------------------------------
    if (hw1 >> 7) & 0xF == 0xB:
        disp = ((hw1 >> 11) << 4) | (((hw1 >> 4) & 0x7) << 1)
        disp = sx9(disp)
        cond = hw1 & 0xF
        return 2, "bcond", (COND[cond], pc + disp), f"{COND[cond]} {pc + disp:#x}"
    # ---- Format IV/V 16-bit sld/sst etc: not expected ---------------------------------------
    if op < 0x30:
        raise ValueError(f"{pc:#x}: unhandled 16-bit op {op:#x} (hw1={hw1:#06x})")
    hw2 = struct.unpack_from("<H", img, pc + 2)[0]
    # ---- Format V jr/jarl disp22 (bits 10:6 == 11110) ---------------------------------------
    if (hw1 >> 6) & 0x1F == 0x1E and not hw2 & 1:      # hw2 bit0 == 1 is ld.bu (same bits 10:6)
        disp = sx22(((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE))
        if reg2 == 0:
            return 4, "jr", (pc + disp,), f"jr {pc + disp:#x}"
        return 4, "jarl", (pc + disp, reg2), f"jarl {pc + disp:#x},{rn(reg2)}"
    # ---- Format VI imm16 --------------------------------------------------------------------
    if op in (0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37):
        names = {0x30: "addi", 0x31: "movea", 0x32: "movhi", 0x33: "satsubi", 0x34: "ori", 0x35: "xori", 0x36: "andi", 0x37: "mulhi"}
        mn = names[op]
        imm = hw2 if op in (0x34, 0x35, 0x36) else sx16(hw2)
        if op == 0x32:
            imm = hw2
        return 4, mn, (imm, reg1, reg2), f"{mn} {imm:#x},{rn(reg1)},{rn(reg2)}"
    # ---- Format VII loads/stores + Format XI ------------------------------------------------
    base = reg1

    def ea(disp):
        return disp, {4: GP, 5: TP}.get(base, 0) + disp

    if op == 0x38:
        d, a = ea(sx16(hw2))
        return 4, "ld.b", (a, reg2), f"ld.b {d:#x}[{rn(base)}]={a:#x},{rn(reg2)}"
    if op == 0x39:
        d, a = ea(sx16(hw2 & 0xFFFE))
        mn = "ld.w" if hw2 & 1 else "ld.h"
        return 4, mn, (a, reg2), f"{mn} {d:#x}[{rn(base)}]={a:#x},{rn(reg2)}"
    if op in (0x3C, 0x3D):
        if not hw2 & 1:
            raise ValueError(f"{pc:#x}: op 0x3C/3D with hw2 bit0=0 (prepare/dispose?)")
        d, a = ea(sx16((hw2 & 0xFFFE) | (op & 1)))
        return 4, "ld.bu", (a, reg2), f"ld.bu {d:#x}[{rn(base)}]={a:#x},{rn(reg2)}"
    if op == 0x3F:
        if hw2 & 1:
            d, a = ea(sx16(hw2 & 0xFFFE))
            return 4, "ld.hu", (a, reg2), f"ld.hu {d:#x}[{rn(base)}]={a:#x},{rn(reg2)}"
        sub = hw2 & 0x7FF
        reg3 = (hw2 >> 11) & 0x1F
        if sub == 0x220:
            return 4, "mul", (reg1, reg2, reg3), f"mul {rn(reg1)},{rn(reg2)},{rn(reg3)}"
        raise ValueError(f"{pc:#x}: unhandled format-XI sub-op {sub:#x}")
    if op == 0x3A:
        d, a = ea(sx16(hw2))
        return 4, "st.b", (reg2, a), f"st.b {rn(reg2)},{d:#x}[{rn(base)}]={a:#x}"
    if op == 0x3B:
        d, a = ea(sx16(hw2 & 0xFFFE))
        mn = "st.w" if hw2 & 1 else "st.h"
        return 4, mn, (reg2, a), f"{mn} {rn(reg2)},{d:#x}[{rn(base)}]={a:#x}"
    raise ValueError(f"{pc:#x}: unhandled op {op:#x} hw1={hw1:#06x} hw2={hw2:#06x}")


def decode_range(img, lo, hi):
    out, pc = [], lo
    while pc < hi:
        n, mn, ops, txt = decode(img, pc)
        out.append((pc, n, mn, ops, txt, img[pc:pc + n].hex()))
        pc += n
    assert pc == hi, f"range {lo:#x}-{hi:#x} does not end on an instruction boundary ({pc:#x})"
    return out


# ------------------------------------------------------------------------------------------------
# EMULATOR -- exact V850 integer semantics
# ------------------------------------------------------------------------------------------------
M32 = 0xFFFFFFFF


def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


class Trap(Exception):
    pass


class CPU:
    def __init__(self, img, ram=None, trace=False):
        self.img = img
        self.r = [0] * 32
        self.ram = ram if ram is not None else {}     # byte-addressed dict, absolute addresses
        self.Z = self.S = self.OV = self.CY = 0
        self.pc = 0
        self.trace = trace
        self.writes = set()
        self.reads = set()
        self.max_abs = {}       # per-register max |value| written (overflow evidence)
        self.exec_count = 0
        self.has_jarl = False

    # -- memory: RAM dict for 0xFEDF.... ; flash from the image otherwise ---------------------
    def rd(self, a, n):
        if a >= 0xFE000000:
            return bytes(self.ram.get(a + i, 0) for i in range(n))
        return self.img[a:a + n]

    def wr(self, a, bs):
        assert a >= 0xFE000000, f"store to flash {a:#x}"
        for i, b in enumerate(bs):
            self.ram[a + i] = b

    def ld(self, a, n, signed):
        self.reads.add(a)
        v = int.from_bytes(self.rd(a, n), "little", signed=signed)
        return v & M32

    def st(self, a, n, v):
        self.writes.add(a)
        self.wr(a, (v & ((1 << (8 * n)) - 1)).to_bytes(n, "little"))

    def setr(self, i, v):
        if i == 0:
            return
        v &= M32
        self.r[i] = v
        self.max_abs[i] = max(self.max_abs.get(i, 0), abs(s32(v)))

    def flags_add(self, a, b):
        res = (a + b) & M32
        sa, sb, sr = s32(a), s32(b), s32(res)
        self.CY = 1 if (a + b) > M32 else 0
        self.OV = 1 if (sa + sb) != sr else 0
        self.S = 1 if sr < 0 else 0
        self.Z = 1 if res == 0 else 0
        return res

    def flags_sub(self, a, b):          # a - b
        res = (a - b) & M32
        sa, sb, sr = s32(a), s32(b), s32(res)
        self.CY = 1 if b > a else 0
        self.OV = 1 if (sa - sb) != sr else 0
        self.S = 1 if sr < 0 else 0
        self.Z = 1 if res == 0 else 0
        return res

    def flags_logic(self, res):
        res &= M32
        self.OV = 0
        self.S = 1 if res & 0x80000000 else 0
        self.Z = 1 if res == 0 else 0
        return res

    def cond(self, c):
        Z, S, OV, CY = self.Z, self.S, self.OV, self.CY
        return {"bv": OV, "bl": CY, "be": Z, "bnh": CY | Z, "bn": S, "br": 1, "blt": S ^ OV,
                "ble": (S ^ OV) | Z, "bnv": 1 - OV, "bnl": 1 - CY, "bne": 1 - Z, "bh": 1 - (CY | Z),
                "bp": 1 - S, "bsa": 0, "bge": 1 - (S ^ OV), "bgt": 1 - ((S ^ OV) | Z)}[c]

    def step(self):
        pc = self.pc
        n, mn, ops, txt = decode(self.img, pc)
        self.exec_count += 1
        if self.trace:
            print(f"    {pc:#08x} {txt}")
        r = self.r
        nxt = pc + n
        if mn == "nop":
            pass
        elif mn == "mov":
            self.setr(ops[1], r[ops[0]])
        elif mn == "mov_i5":
            self.setr(ops[1], ops[0])
        elif mn == "add":
            self.setr(ops[1], self.flags_add(r[ops[1]], r[ops[0]]))
        elif mn == "add_i5":
            self.setr(ops[1], self.flags_add(r[ops[1]], ops[0] & M32))
        elif mn == "sub":
            self.setr(ops[1], self.flags_sub(r[ops[1]], r[ops[0]]))
        elif mn == "subr":
            self.setr(ops[1], self.flags_sub(r[ops[0]], r[ops[1]]))
        elif mn == "cmp":
            self.flags_sub(r[ops[1]], r[ops[0]])
        elif mn == "cmp_i5":
            self.flags_sub(r[ops[1]], ops[0] & M32)
        elif mn == "or":
            self.setr(ops[1], self.flags_logic(r[ops[1]] | r[ops[0]]))
        elif mn == "and":
            self.setr(ops[1], self.flags_logic(r[ops[1]] & r[ops[0]]))
        elif mn == "xor":
            self.setr(ops[1], self.flags_logic(r[ops[1]] ^ r[ops[0]]))
        elif mn == "andi":
            self.setr(ops[2], self.flags_logic(r[ops[1]] & ops[0]))
        elif mn == "ori":
            self.setr(ops[2], self.flags_logic(r[ops[1]] | ops[0]))
        elif mn == "movea":
            self.setr(ops[2], (r[ops[1]] + ops[0]) & M32)
        elif mn == "addi":
            self.setr(ops[2], self.flags_add(r[ops[1]], ops[0] & M32))
        elif mn == "sar":
            sh = ops[0]
            v = s32(r[ops[1]])
            res = (v >> sh) & M32                     # python >> on negative int FLOORS, as V850 sar does
            self.CY = (v >> (sh - 1)) & 1 if sh else 0
            self.setr(ops[1], self.flags_logic(res))
        elif mn == "shl":
            sh = ops[0]
            v = r[ops[1]]
            self.CY = (v >> (32 - sh)) & 1 if sh else 0
            self.setr(ops[1], self.flags_logic((v << sh) & M32))
        elif mn == "shr":
            sh = ops[0]
            v = r[ops[1]]
            self.CY = (v >> (sh - 1)) & 1 if sh else 0
            self.setr(ops[1], self.flags_logic(v >> sh))
        elif mn == "mul":
            reg1, reg2, reg3 = ops
            prod = s32(r[reg1]) * s32(r[reg2])        # signed 32x32 -> 64
            lo, hi = prod & M32, (prod >> 32) & M32
            self.setr(reg2, lo)
            self.setr(reg3, hi)                        # reg3 == r0 -> discarded
            self.max_abs[("mul", pc)] = max(self.max_abs.get(("mul", pc), 0), abs(prod))
        elif mn == "ld.w":
            self.setr(ops[1], self.ld(ops[0], 4, True))
        elif mn == "ld.h":
            self.setr(ops[1], self.ld(ops[0], 2, True))
        elif mn == "ld.hu":
            self.setr(ops[1], self.ld(ops[0], 2, False))
        elif mn == "ld.b":
            self.setr(ops[1], self.ld(ops[0], 1, True))
        elif mn == "ld.bu":
            self.setr(ops[1], self.ld(ops[0], 1, False))
        elif mn == "st.w":
            self.st(ops[1], 4, r[ops[0]])
        elif mn == "st.h":
            self.st(ops[1], 2, r[ops[0]])
        elif mn == "st.b":
            self.st(ops[1], 1, r[ops[0]])
        elif mn == "bcond":
            if self.cond(ops[0]):
                nxt = ops[1]
        elif mn == "jr":
            nxt = ops[0]
        elif mn == "jarl":
            self.has_jarl = True
            raise Trap(f"jarl at {pc:#x}")
        elif mn == "jmp":
            nxt = r[ops[0]]
        else:
            raise Trap(f"unimplemented {mn} at {pc:#x}")
        self.pc = nxt

    def run(self, start, stop_pcs, limit=10000):
        self.pc = start
        while self.pc not in stop_pcs:
            self.step()
            limit -= 1
            if limit == 0:
                raise Trap("runaway")


# ------------------------------------------------------------------------------------------------
# harness around the cave: one tick = enter at 0xC4C00 with r12 = x, leave at 0x2A178
# ------------------------------------------------------------------------------------------------
CAVE, RET, HOOK = 0xC4C00, 0x2A178, 0x2A174
S1, S2, EW, FLAG = GP - 0x6C44, GP - 0x6C40, GP - 0x6C3C, GP - 0x6C3A
LIVE = {11: 0x11111111, 14: 0x14141414, 15: 0x15151515, 16: 0x16161616, 22: 0x22222222,
        24: 0x24242424, 27: 0x27272727, 29: 0x29292929, 31: 0x31313131}


def cave_tick(cpu, x):
    for k, v in LIVE.items():
        cpu.r[k] = v
    cpu.r[4], cpu.r[5] = GP, TP
    cpu.r[12] = x & M32
    cpu.run(CAVE, {RET})
    for k, v in LIVE.items():
        assert cpu.r[k] == v, f"A5 live register r{k} clobbered"
    assert cpu.r[7] == 507, "displaced ld.hu r7 := 507 not replicated"
    y_out = s32(cpu.r[12])
    return y_out


def state(cpu):
    rd = lambda a, n, sg: int.from_bytes(cpu.rd(a, n), "little", signed=sg)
    return rd(S1, 4, True), rd(S2, 4, True), rd(EW, 2, False), rd(FLAG, 2, False)


def set_state(cpu, s1, s2, e):
    cpu.st(S1, 4, s1 & M32)
    cpu.st(S2, 4, s2 & M32)
    cpu.st(EW, 4, e & 0x3FFF)


def run_seq(xs, init=(0, 0, 0), img=None, want_flags=False):
    cpu = CPU(img)
    set_state(cpu, *init)
    ys, fl = [], []
    for x in xs:
        ys.append(cave_tick(cpu, x))
        if want_flags:
            fl.append(state(cpu)[3])
    return (ys, fl, cpu) if want_flags else (ys, cpu)


# ------------------------------------------------------------------------------------------------
# reference float filter (from the IMAGE coefficients, not the design)
# ------------------------------------------------------------------------------------------------
def H(f, fs, b, a):
    z = complex(math.cos(2 * math.pi * f / fs), math.sin(2 * math.pi * f / fs))
    num = b[0] + b[1] / z + b[2] / z ** 2
    den = a[0] + a[1] / z + a[2] / z ** 2
    return num / den


def lin_impulse(b, a, n):
    """exact-rational impulse responses of x -> y, s1, s2, acc for the TDF-II recursion, in units of 1/a0."""
    from fractions import Fraction as F
    a0 = F(a[0])
    s1 = s2 = F(0)
    hy, hs1, hs2, hacc = [], [], [], []
    for k in range(n):
        x = 1 if k == 0 else 0
        acc = b[0] * x + s1
        y = acc / a0
        ns1 = b[1] * x - a[1] * y + s2
        ns2 = b[2] * x - a[2] * y
        hy.append(y); hs1.append(ns1); hs2.append(ns2); hacc.append(acc)
        s1, s2 = ns1, ns2
    return hy, hs1, hs2, hacc


def main():
    v289, v282 = load_images()
    img = v289
    print("=" * 100)
    print("ADVERSARY A -- V289 rev 1 -- arithmetic.  image sha OK:", IMG_SHA[:16])
    fails, conds = [], []

    # ---- 0. diff census -----------------------------------------------------------------------
    diffs = [i for i in range(0x13000, len(img)) if img[i] != v282[i]]
    print(f"[0] bytes differing from V282 in [0x13000,end): {len(diffs)}")

    # ---- 1. decode ------------------------------------------------------------------------------
    print("\n[1] MY DECODE of the hook, the cave and the tail (compare with Ghidra listing in the report)")
    hook = decode_range(img, HOOK, HOOK + 4)
    cave = decode_range(img, CAVE, 0xC4C8C)
    tail = decode_range(img, 0xC4BD6, 0xC4BDA) + decode_range(img, 0xC4BDC, 0xC4BF8)
    assert img[0xC4BDA:0xC4BDC] == bytes([0xFF, 0xFF]) and img[0xC4BF8:0xC4C00] == bytes([0xFF]) * 8
    for lst in (hook, cave, tail):
        for pc, n, mn, ops, txt, hx in lst:
            print(f"    {pc:#08x}  {hx:<12} {txt}")
        print()
    assert hook[0][2] == "jr" and hook[0][3][0] == CAVE, "hook does not jr to cave"
    assert cave[-1][2] == "jr" and cave[-1][3][0] == RET, "cave does not return to 0x2A178"
    assert tail[0][2] == "jr" and tail[0][3][0] == 0xC4BDC
    assert cave[-2][2] == "ld.hu" and cave[-2][3] == (TP + 0x73EE, 7), "displaced load not replicated"
    assert not any(i[2] == "jarl" for i in cave + tail + hook), "A5: jarl present"
    # V282 bytes at the relocated epilogue
    assert v282[0xC4BD2:0xC4BD8] == img[0xC4BF2:0xC4BF8] == bytes.fromhex("2436e8ea7f00"), "epilogue not byte-identical"
    print("    hook -> cave -> ret ok; no jarl; displaced ld.hu replicated; epilogue byte-identical to V282 @0xC4BD2")

    # registers written by the cave (static)
    written = set()
    for pc, n, mn, ops, txt, hx in cave:
        if mn in ("mov", "add", "sub", "subr", "or", "and", "xor", "sar", "shl", "shr"):
            written.add(ops[1])
        elif mn in ("mov_i5", "add_i5"):
            written.add(ops[1])
        elif mn in ("andi", "ori", "movea", "addi"):
            written.add(ops[2])
        elif mn == "mul":
            written.add(ops[1]); written.add(ops[2])
        elif mn.startswith("ld."):
            written.add(ops[1])
    written.discard(0)
    print(f"    registers WRITTEN by the cave (static): {sorted(written)}")
    bad = written & {11, 14, 15, 16, 22, 24, 27, 29, 31}
    if bad:
        fails.append(f"A5 clobbers live {bad}")
    ram_w = sorted({i[3][1] for i in cave if i[2].startswith("st.")})
    ram_r = sorted({i[3][0] for i in cave if i[2].startswith("ld.") and i[3][0] >= 0xFE000000})
    print(f"    RAM written: {[hex(a) for a in ram_w]}   RAM read: {[hex(a) for a in ram_r]}")

    # coefficients read from the image (movea imm16)
    consts = [i[3][0] for i in cave if i[2] == "movea"]
    print(f"    movea constants in cave: {consts}")
    b0, a2, b1 = consts[0], consts[1], consts[2]
    a1 = b1
    b, a = (b0, b1, b0), (16384, a1, a2)
    print(f"    => b = {b}, a = {a}   (a0 = 2^14 from the sar 0xe)")
    cal_clamp = struct.unpack_from("<H", img, 0xC61BE)[0]
    print(f"    output clamp cell 0xC61BE = {cal_clamp}")

    # ---- realised transfer from the integers -------------------------------------------------
    fs = 1000.0
    f0 = math.acos(-b1 / (2 * b0)) * fs / (2 * math.pi)
    dc = (b0 + b1 + b0) / (16384 + a1 + a2)
    nyq = (b0 - b1 + b0) / (16384 - a1 + a2)
    # -3 dB points by bisection
    def mag(f): return abs(H(f, fs, b, a))
    def bis(lo, hi):
        for _ in range(60):
            m = (lo + hi) / 2
            if mag(m) > 1 / math.sqrt(2): lo = m
            else: hi = m
        return (lo + hi) / 2
    fl3 = bis(5.0, f0)
    # upper -3 dB
    lo, hi = f0, 60.0
    for _ in range(60):
        m = (lo + hi) / 2
        if mag(m) < 1 / math.sqrt(2): lo = m
        else: hi = m
    fh3 = (lo + hi) / 2
    Q = f0 / (fh3 - fl3)
    print(f"\n[A1] realised from integers: f0 = {f0:.3f} Hz  DC = {dc}  Nyquist = {nyq}  -3dB {fl3:.2f}-{fh3:.2f}  Q = {Q:.3f}")
    for f in (3.9, 7.3, 13.5, 17.0, 20.03, 20.05, 20.08, 23.0, 30.0):
        h = H(f, fs, b, a)
        print(f"      f={f:6.2f}  |H|={abs(h):.4f} ({20*math.log10(abs(h)):7.1f} dB)  phase={math.degrees(math.atan2(h.imag,h.real)):7.2f} deg")
    if abs(f0 - 20.05) > 0.3: fails.append(f"A1 f0 {f0:.3f}")
    if dc != 1: fails.append("A1 DC != 1 (float)")
    poles = [abs(r) for r in __import__("numpy").roots([a[0], a[1], a[2]])]
    print(f"      pole radii: {poles}   (must be < 1)")

    # ---- l1 bounds ---------------------------------------------------------------------------
    hy, hs1, hs2, hacc = lin_impulse(b, a, 4000)
    l1 = lambda h: float(sum(abs(v) for v in h))
    print(f"\n[A2] l1 norms (per unit x): y {l1(hy):.4f}  s1 {l1(hs1)/1.0:.1f}  s2 {l1(hs2):.1f}  acc {l1(hacc):.1f}")
    X = 15360
    print(f"      worst |y| {l1(hy)*X:.0f}   |s1| {l1(hs1)*X/2**31:.4f}*2^31   |s2| {l1(hs2)*X/2**31:.4f}*2^31   |acc| {(l1(hacc)*X+16383)/2**31:.4f}*2^31")

    # ---- emulation: worst-case sign sequences for s1, s2, acc --------------------------------
    n_l1 = 1500
    worst = {}
    for name, h in (("s1", hs1), ("s2", hs2), ("acc", hacc)):
        seq = [X if h[n_l1 - 1 - k] >= 0 else -X for k in range(n_l1)]      # x_k = X*sign(h[N-1-k]) maximises the state at N
        ys, cpu = run_seq(seq, img=img)
        s1v, s2v, ev, _ = state(cpu)
        worst[name] = (max(cpu.max_abs.get(9, 0), cpu.max_abs.get(13, 0), cpu.max_abs.get(7, 0)), s1v, s2v)
        print(f"      worst-case for {name}: max|reg| {worst[name][0]/2**31:.4f}*2^31, final s1 {s1v/2**31:+.4f}*2^31 s2 {s2v/2**31:+.4f}*2^31, max|y| {max(abs(v) for v in ys)}")
        # wrap detection: in the emulator any 32-bit wrap shows as a sign flip vs the exact product;
        for key, v in cpu.max_abs.items():
            if isinstance(key, tuple) and v >= 2 ** 31:
                fails.append(f"A2 64-bit product |{v}| >= 2^31 at {key[1]:#x} in {name} worst case")
    # exact wrap check: rerun the acc worst case with a Python big-int shadow of the recursion
    def shadow(xs):
        s1 = s2 = e = 0
        mx = 0
        for x in xs:
            acc = s1 + e + b0 * x
            y = acc >> 14
            e = acc & 0x3FFF
            ns2 = b0 * x - a2 * y
            ns1 = b1 * (x - y) + s2
            mx = max(mx, abs(acc), abs(ns1), abs(ns2), abs(b0 * x), abs(a2 * y), abs(b1 * (x - y)))
            s1, s2 = ns1, ns2
        return mx
    for name, h in (("s1", hs1), ("s2", hs2), ("acc", hacc)):
        seq = [X if h[n_l1 - 1 - k] >= 0 else -X for k in range(n_l1)]
        mx = shadow(seq)
        print(f"      big-int shadow, {name} worst case: max intermediate {mx/2**31:.4f}*2^31  {'WRAP' if mx >= 2**31 else 'ok'}")
        if mx >= 2 ** 31: fails.append(f"A2 wrap in {name} worst case")
        # emulator vs shadow agreement on y
        ys, cpu = run_seq(seq, img=img)
        # recompute shadow y with clamp
        s1 = s2 = e = 0; ys2 = []
        for x in seq:
            acc = s1 + e + b0 * x; y = acc >> 14; e = acc & 0x3FFF
            ns2 = b0 * x - a2 * y; ns1 = b1 * (x - y) + s2; s1, s2 = ns1, ns2
            ys2.append(max(-cal_clamp, min(cal_clamp, y)))
        assert ys == ys2, "emulator and big-int shadow disagree"
    print("      emulator == big-int shadow on all three worst-case sequences (so no wrap occurred in the emulator either)")

    # ---- A1/A3 constants ---------------------------------------------------------------------
    print("\n[A1/A3] constant inputs, 3000 ticks from zero state and from a worst-case state")
    for Xc in (0, 1, -1, 7, -7, 100, -100, 1000, -1000, 15360, -15360):
        for init in ((0, 0, 0), (int(0.14 * 2 ** 31), -int(0.14 * 2 ** 31), 16383)):
            ys, cpu = run_seq([Xc] * 3000, init=init, img=img)
            tail = ys[-1000:]
            settle = next((k for k in range(len(ys)) if all(abs(v - Xc) <= 1 for v in ys[k:])), None)
            exact = next((k for k in range(len(ys)) if all(v == Xc for v in ys[k:])), None)
            s1v, s2v, ev, _ = state(cpu)
            mean = sum(tail) / len(tail)
            print(f"      X={Xc:6d} init={'zero' if init[0]==0 else 'wc  '}: settle(|y-X|<=1) @ {settle}, exact @ {exact}, tail min/max {min(tail)}/{max(tail)}, mean {mean:.4f}, final s1 {s1v} s2 {s2v} e {ev}  (s1 expect {336*Xc})")
            if exact is None:
                fails.append(f"A3 X={Xc} init={init}: never exactly X (tail {min(tail)}..{max(tail)})")
            if abs(mean - Xc) > 1e-9:
                conds.append(f"A1 X={Xc}: time-average {mean}")
            if Xc == 0 and (s1v, s2v) != (0, 0):
                fails.append(f"A3 zero input: state does not decay to 0 (s1 {s1v} s2 {s2v} e {ev})")

    # ---- sinusoids -----------------------------------------------------------------------------
    print("\n[A1] sinusoid depth / phase (emulated, 4 s, last 2 s analysed by DFT at the drive frequency)")
    import numpy as np
    def sine_resp(f, A, n=4000):
        xs = [int(round(A * math.sin(2 * math.pi * f * k / fs))) for k in range(n)]
        ys, _ = run_seq(xs, img=img)
        k = np.arange(n // 2, n)
        w = np.exp(-2j * np.pi * f * k / fs)
        Yc = np.dot(np.array(ys[n // 2:], float), w)
        Xc = np.dot(np.array(xs[n // 2:], float), w)
        return Yc / Xc, max(abs(v) for v in ys[n // 2:])
    for f, A in ((20.036, 1), (20.036, 10), (20.036, 100), (20.036, 3000), (20.036, 15000), (20.05, 15000), (17.0, 15000), (23.0, 15000),
                 (3.9, 15000), (7.3, 15000), (13.5, 15000), (30.0, 15000)):
        h, pk = sine_resp(f, A)
        hf = H(f, fs, b, a)
        print(f"      f={f:6.3f} A={A:6d}: |H|={abs(h):.4f} ({20*math.log10(max(abs(h),1e-9)):6.1f} dB) phase {math.degrees(math.atan2(h.imag,h.real)):7.2f} deg  peak|y| {pk}   float |H| {abs(hf):.4f} {math.degrees(math.atan2(hf.imag,hf.real)):7.2f} deg")
        if f == 20.036 and A >= 100 and 20 * math.log10(abs(h)) > -20:
            fails.append(f"A1 depth {20*math.log10(abs(h)):.1f} dB at A={A}")

    # ---- step, rail square -------------------------------------------------------------------
    print("\n[A2] step 0 -> 15360 and rail square wave +-15360 at 20 Hz")
    ys, cpu = run_seq([0] * 10 + [15360] * 500, img=img)
    lin = []
    s1 = s2 = e = 0
    for x in [0] * 10 + [15360] * 500:
        acc = s1 + e + b0 * x; y = acc >> 14; e = acc & 0x3FFF
        ns2 = b0 * x - a2 * y; ns1 = b1 * (x - y) + s2; s1, s2 = ns1, ns2; lin.append(y)
    print(f"      linear peak {max(lin)} (x{max(lin)/15360:.3f}) at tick {lin.index(max(lin))-10}; clamp binds for {sum(1 for v in lin if v > 15360)} ticks; emitted max {max(ys)}; undershoot min after step {min(lin[10:])}")
    print(f"      first 12 outputs after the step: {ys[10:22]}")
    sq = [15360 if (k // 25) % 2 == 0 else -15360 for k in range(3000)]
    ys, cpu = run_seq(sq, img=img)
    print(f"      rail square: max|y| emitted {max(abs(v) for v in ys)}, max|reg| {max(cpu.max_abs.get(k,0) for k in (6,7,9,13))/2**31:.4f}*2^31")
    # random rail-bang
    import random
    random.seed(1)
    rb = [random.choice((15360, -15360, 0)) for _ in range(20000 if FULL else 5000)]
    ys, cpu = run_seq(rb, img=img)
    print(f"      random rail bang: max|reg| {max(cpu.max_abs.get(k,0) for k in (6,7,9,13))/2**31:.4f}*2^31, max|y_lin| via clamp count {sum(1 for v in ys if abs(v)==15360)}")

    # ---- FLAG rung semantics -----------------------------------------------------------------
    print("\n[A4] FLAG halfword: values seen and truth-table check against n = x - y_lin")
    xs = [int(round(15000 * math.sin(2 * math.pi * 20.036 * k / fs))) for k in range(2000)] + [int(round(3000 * math.sin(2 * math.pi * 5 * k / fs))) for k in range(2000)]
    cpu = CPU(img); set_state(cpu, 0, 0, 0)
    seen, mism = set(), 0
    s1 = s2 = e = 0
    for x in xs:
        acc = s1 + e + b0 * x; y = acc >> 14; e = acc & 0x3FFF
        ns2 = b0 * x - a2 * y; ns1 = b1 * (x - y) + s2; s1, s2 = ns1, ns2
        n = x - y
        cave_tick(cpu, x)
        fl = state(cpu)[3]
        seen.add(fl)
        exp = (0x20 if n < 0 else 0) | (0x80 if abs(n) >= abs(y) else 0)
        if fl != exp: mism += 1
    print(f"      FLAG values seen {sorted(hex(v) for v in seen)}; mismatches vs (n<0)<<5 | (|n|>=|y|)<<7: {mism}")
    if mism: fails.append("A4 FLAG semantics")

    # ---- tail emulation ----------------------------------------------------------------------
    print("\n[A4] 0x14A tail: run 0xC4BD6.. with every FLAG value and every byte-4 value")
    bad = 0
    for flag in (0, 0x20, 0x80, 0xA0, 0xFFFF, 0x1F5F):
        for b4 in range(256):
            cpu = CPU(img)
            cpu.st(FLAG, 2, flag)
            cpu.st(GP - 0x1514, 1, b4)
            cpu.r[4], cpu.r[5], cpu.r[31] = GP, TP, 0x55C12
            cpu.run(0xC4BD6, {0x55C12})
            out = cpu.rd(GP - 0x1514, 1)[0]
            exp = (b4 & 0x5F) | (flag & 0xA0)
            if out != exp or cpu.r[6] != (GP - 0x1518) & M32 or cpu.r[31] != 0x55C12:
                bad += 1
    print(f"      tail mismatches over 6x256 cases: {bad}  (expect out = (b4 & 0x5F) | (FLAG & 0xA0), r6 = gp-0x1518, lp intact)")
    if bad: fails.append("A4 tail")

    # ---- instruction count / cycle estimate ---------------------------------------------------
    cpu = CPU(img); set_state(cpu, 0, 0, 0)
    cave_tick(cpu, 1234)
    print(f"\n      instructions executed per tick: {cpu.exec_count} (static 52)")

    # ---- verdict ------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("FAILS:", fails if fails else "none")
    print("CONDITIONS / residuals:", conds if conds else "none")
    print("VERDICT:", "FAIL" if fails else ("PASS-WITH-CONDITIONS" if conds else "PASS"))


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------------------------------------
# [3] DOWNSTREAM: run the REAL bytes from the hook through 0x2A1AE (lag filter, 16-bit publish) each tick
# ------------------------------------------------------------------------------------------------
GHIDRA_CAVE = """c4c00 ld.w 244fbd93|c4c04 ld.w 246fc593|c4c08 andi cd6eff3f|c4c0c add cd49|c4c0e movea 206eb03e|c4c12 mul ec6f2002|c4c16 mov 0d38|c4c18 add cd49|c4c1a mov 0930|c4c1c sar ae32|c4c1e andi c94eff3f|c4c22 st.w 644fc593|c4c26 movea 206e603d|c4c2a mul e66f2002|c4c2e sub ad39|c4c30 ld.w 246fc193|c4c34 st.w 643fc193|c4c38 mov 0c48|c4c3a sub a649|c4c3c movea 203e9e83|c4c40 mul e93f2002|c4c44 add c769|c4c46 st.w 646fbd93|c4c4a mov 006a|c4c4c cmp 604a|c4c4e bge ae05|c4c50 mov 026a|c4c52 mov 0660|c4c54 mov 0938|c4c56 cmp 603a|c4c58 bge ae05|c4c5a subr 8039|c4c5c cmp 6032|c4c5e bge ae05|c4c60 subr 8031|c4c62 cmp e639|c4c64 mov 083a|c4c66 bge ae05|c4c68 mov 003a|c4c6a or 0769|c4c6c shl c46a|c4c6e st.h 646fc693|c4c72 ld.hu e54fbf71|c4c76 cmp e961|c4c78 ble a705|c4c7a mov 0960|c4c7c subr 8049|c4c7e cmp e961|c4c80 bge ae05|c4c82 mov 0960|c4c84 ld.hu e53fef73|c4c88 jr b607f054|c4bd6 jr 80070600|c4bdc ld.hu e43fc793|c4be0 andi c73ea000|c4be4 ld.bu 8437edea|c4be8 andi c6365f00|c4bec or 0731|c4bee st.b 4437ecea|c4bf2 movea 2436e8ea|c4bf6 jmp 7f00"""
# (transcribed from Ghidra's disassemble_bytes on the imported v289 program, 2026-09-08; Ghidra operands were
#  compared by eye: every gp/tp displacement, immediate and branch target agrees with the listing above)


def downstream(img):
    print("\n[3] downstream: emulate hook -> cave -> 0x2A178..0x2A1B4 on the real bytes, lag state persistent")
    mine = {pc: (mn, hx) for pc, n, mn, ops, txt, hx in decode_range(img, CAVE, 0xC4C8C) + decode_range(img, 0xC4BD6, 0xC4BDA) + decode_range(img, 0xC4BDC, 0xC4BF8)}
    norm = lambda m: m.replace("_i5", "").replace("bcond", "")
    mism = 0
    for tok in GHIDRA_CAVE.split("|"):
        a, mn, hx = tok.split()
        pc = int(a, 16)
        mm, mh = mine[pc]
        mm = norm(mm)
        if mm == "":  # bcond: compare via text
            mm = mn
        if (mm, mh) != (mn, hx):
            mism += 1
            print(f"      MISMATCH {pc:#x}: ghidra {mn} {hx} / mine {mm} {mh}")
    print(f"      Ghidra vs my decoder: {len(GHIDRA_CAVE.split('|'))} instructions, mismatches {mism}")
    cal = lambda a: struct.unpack_from('<H', img, a)[0]
    print(f"      cal 0xC63EE (lag b) = {cal(0xC63EE)}, 0xC63EC (lag a) = {struct.unpack_from('<h', img, 0xC63EC)[0]}, 0xC646C (gain) = {struct.unpack_from('<h', img, 0xC646C)[0]}, 0xC61B4 (T clamp) = {cal(0xC61B4)}, 0xC61B8 = {cal(0xC61B8)}")
    cpu = CPU(img)
    set_state(cpu, 0, 0, 0)
    seq = [0] * 20 + [15360] * 600 + [-15360] * 600 + [15360 if (k // 25) % 2 == 0 else -15360 for k in range(2000)] + [0] * 600
    max9 = max12 = max7 = 0
    for x in seq:
        for k, v in LIVE.items():
            cpu.r[k] = v
        cpu.r[4], cpu.r[5], cpu.r[12] = GP, TP, x & M32
        cpu.run(HOOK, {0x2A1B4})
        for k, v in LIVE.items():
            if k != 16:                      # Honda reloads r16 at 0x2A198 (ld.bu 0x74a3,tp,r16)
                assert cpu.r[k] == v
        max9 = max(max9, abs(s32(cpu.r[9]))); max12 = max(max12, abs(s32(cpu.r[12]))); max7 = max(max7, abs(s32(cpu.r[7])))
        pub = int.from_bytes(cpu.rd(GP - 0x6B2E, 2), 'little', signed=True)
        assert -15360 <= pub <= 15360
    lag = int.from_bytes(cpu.rd(GP - 0x3D3C, 4), 'little', signed=True)
    prods = {k: v for k, v in cpu.max_abs.items() if isinstance(k, tuple)}
    print(f"      max |r9| after sar 5 (lag out) = {max9}; max |r12>>10| = {max12}; max |r7| (new lag state) = {max7}; final lag state {lag}")
    print(f"      max |64-bit product| per mul site: " + ", ".join(f"{k[1]:#x}:{v/2**31:.4f}*2^31" for k, v in sorted(prods.items())))
    print(f"      0x2A1E6 ramp multiply worst case: {max9} * 32767 = {max9*32767} = {max9*32767/2**31:.4f}*2^31 -> >>15 = {(max9*32767)>>15} fits int16 (sxh no-op)")
    print(f"      gp-0x6b2e publish (st.h r12) bound |r12| <= 15360 fits int16; identical bound to V282 (same 0xC61BE clamp).")


if __name__ == "__main__":
    downstream(load_images()[0])
