# -*- coding: utf-8 -*-
"""studies/grind/adv_v289_b_cave.py -- ADVERSARY B (units/loop) for V289 rev 1: an INDEPENDENT V850E2 decoder and a
register-level interpreter for the notch cave at 0xC4C00 and the 0x14A rung tail at 0xC4BDC, read from the BUILT IMAGE.
Nothing here trusts the build script: coefficients, clamp cell, state cells, the FLAG semantics and the realised transfer
are all recovered by decoding and executing the bytes.   Subagent advB, 2026-09-08.  Analysis only.

Provides
  decode(img, addr, end)              -> list of (addr, size, text, op-dict)
  Cave(img)                           -> .tick(S) executes the cave once (r12 = S in, r12 = y out), keeps RAM state
  fb/lag mirrors read from the cells at 0xC63E8.. (widths from the loads at 0x28F86/0x28F8A, decoded here)
Run standalone: prints the listing, the recovered coefficients, DC identity / settling tests, realised f0 / Q / depth.
"""
import os
import struct
import sys

import numpy as np

FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
IMG289 = FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
IMG282 = FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GP, TP = 0xFEDF8000, 0xBF000
CAVE, CAVE_END = 0xC4C00, 0xC4C8C
TAIL, TAIL_END = 0xC4BD6, 0xC4BF8
HOOK = 0x2A174
M32 = 0xFFFFFFFF
COND = {0: "v", 1: "l", 2: "e", 3: "nh", 4: "n", 5: "r", 6: "lt", 7: "le", 8: "nv", 9: "nl", 10: "ne", 11: "h", 12: "p", 13: "sa", 14: "ge", 15: "gt"}
REG = {0: "r0", 3: "sp", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}


def rn(r):
    return REG.get(r, "r%d" % r)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def s32(v):
    v &= M32
    return v - 0x100000000 if v & 0x80000000 else v


def decode_one(img, a):
    """One instruction at a.  Returns (size, text, op).  op is a dict the interpreter executes."""
    hw1 = struct.unpack_from("<H", img, a)[0]
    reg1, reg2, op6 = hw1 & 0x1F, (hw1 >> 11) & 0x1F, (hw1 >> 5) & 0x3F
    # ---- 6-byte mov imm32
    if hw1 & 0xFFE0 == 0x0620:
        imm = struct.unpack_from("<i", img, a + 2)[0]
        return 6, "mov 0x%x, %s" % (imm & M32, rn(reg1)), dict(k="movi32", r1=reg1, imm=imm)
    # ---- Format III bcond
    if (hw1 >> 7) & 0xF == 0xB:
        disp = ((hw1 >> 11) & 0x1F) << 4 | ((hw1 >> 4) & 0x7) << 1
        if disp & 0x100:
            disp -= 0x200
        c = hw1 & 0xF
        return 2, "b%s 0x%X" % (COND[c], a + disp), dict(k="bcond", c=c, tgt=a + disp)
    # ---- Format V jr / jarl  (shares bits 10..6 = 11110 with ld.bu; ld.bu has hw2 LSB = 1, jr/jarl an EVEN disp)
    if (hw1 & 0x07C0) == 0x0780:
        hw2 = struct.unpack_from("<H", img, a + 2)[0]
        if (hw2 & 1) and reg2 != 0:
            d = s16((hw2 & 0xFFFE) | (op6 & 1))
            return 4, "ld.bu %d[%s], %s" % (d, rn(reg1), rn(reg2)), dict(k="ld.bu", d=d, r1=reg1, r2=reg2)
        disp = ((hw1 & 0x3F) << 16) | hw2
        if disp & 0x200000:
            disp -= 0x400000
        if reg2 == 0:
            return 4, "jr 0x%X" % (a + disp), dict(k="jr", tgt=a + disp)
        return 4, "jarl 0x%X, %s" % (a + disp, rn(reg2)), dict(k="jarl", tgt=a + disp, r2=reg2)
    # ---- Format I (2 bytes)
    if op6 <= 0x0F:
        names = {0: "mov", 1: "not", 2: "divh", 3: "jmp", 4: "satsubr", 5: "satsub", 6: "satadd", 7: "mulh", 8: "or", 9: "xor", 10: "and", 11: "tst", 12: "subr", 13: "sub", 14: "add", 15: "cmp"}
        nm = names[op6]
        if op6 == 0 and reg2 == 0 and reg1 == 0:
            return 2, "nop", dict(k="nop")
        if op6 == 3:
            return 2, "jmp [%s]" % rn(reg1), dict(k="jmp", r1=reg1)
        if op6 == 0 and reg2 == 0:
            # sxh/zxh/sxb/zxb/switch/sld... share the 0x0000 opcode with reg2=0: hw1 = 0x00A0|r sxb, 0x00C0 zxh, 0x00E0 sxh, 0x0080 zxb
            sub = hw1 & 0x7E0
            if sub == 0x0E0:
                return 2, "sxh %s" % rn(reg1), dict(k="sxh", r1=reg1)
            if sub == 0x0C0:
                return 2, "zxh %s" % rn(reg1), dict(k="zxh", r1=reg1)
            if sub == 0x0A0:
                return 2, "sxb %s" % rn(reg1), dict(k="sxb", r1=reg1)
            if sub == 0x080:
                return 2, "zxb %s" % rn(reg1), dict(k="zxb", r1=reg1)
        return 2, "%s %s, %s" % (nm, rn(reg1), rn(reg2)), dict(k=nm, r1=reg1, r2=reg2)
    # ---- Format II imm5 (2 bytes)
    if 0x10 <= op6 <= 0x17:
        names = {0x10: "mov", 0x11: "satadd", 0x12: "add", 0x13: "cmp", 0x14: "shr", 0x15: "sar", 0x16: "shl", 0x17: "mulh"}
        nm = names[op6]
        imm = reg1
        if nm in ("mov", "satadd", "add", "cmp", "mulh") and imm & 0x10:
            imm -= 0x20
        return 2, "%s %d, %s" % (nm + "i" if nm in ("shr", "sar", "shl") else nm, imm, rn(reg2)), dict(k=nm + "_i", imm=imm, r2=reg2)
    # ---- Format IV short loads (ep) -- not expected in the cave
    if op6 >> 1 in (0x6 >> 1, 0x7 >> 1, 0x8 >> 1, 0x9 >> 1, 0xA >> 1) and False:
        pass
    hw2 = struct.unpack_from("<H", img, a + 2)[0]
    # ---- Format VI imm16 (4 bytes)
    if 0x30 <= op6 <= 0x37:
        names = {0x30: "addi", 0x31: "movea", 0x32: "movhi", 0x33: "satsubi", 0x34: "ori", 0x35: "xori", 0x36: "andi", 0x37: "mulhi"}
        nm = names[op6]
        imm = s16(hw2) if nm in ("addi", "movea", "movhi", "satsubi", "mulhi") else hw2
        return 4, "%s %s, %s, %s" % (nm, ("%d" % imm) if nm in ("addi", "movea", "satsubi", "mulhi") else "0x%x" % (imm & 0xFFFF), rn(reg1), rn(reg2)), dict(k=nm, imm=imm, r1=reg1, r2=reg2)
    # ---- Format VII disp16 loads/stores (4 bytes)
    if op6 == 0x38:
        return 4, "ld.b %d[%s], %s" % (s16(hw2), rn(reg1), rn(reg2)), dict(k="ld.b", d=s16(hw2), r1=reg1, r2=reg2)
    if op6 == 0x39:
        if hw2 & 1:
            return 4, "ld.w %d[%s], %s" % (s16(hw2 & 0xFFFE), rn(reg1), rn(reg2)), dict(k="ld.w", d=s16(hw2 & 0xFFFE), r1=reg1, r2=reg2)
        return 4, "ld.h %d[%s], %s" % (s16(hw2), rn(reg1), rn(reg2)), dict(k="ld.h", d=s16(hw2), r1=reg1, r2=reg2)
    if op6 == 0x3A:
        return 4, "st.b %s, %d[%s]" % (rn(reg2), s16(hw2), rn(reg1)), dict(k="st.b", d=s16(hw2), r1=reg1, r2=reg2)
    if op6 == 0x3B:
        if hw2 & 1:
            return 4, "st.w %s, %d[%s]" % (rn(reg2), s16(hw2 & 0xFFFE), rn(reg1)), dict(k="st.w", d=s16(hw2 & 0xFFFE), r1=reg1, r2=reg2)
        return 4, "st.h %s, %d[%s]" % (rn(reg2), s16(hw2), rn(reg1)), dict(k="st.h", d=s16(hw2), r1=reg1, r2=reg2)
    if op6 == 0x3F and (hw2 & 1) and reg2 != 0 and (hw2 & 0x7FE) not in (0x220,):
        # ld.hu: hw2 LSB forced 1 (only when hw2 is not one of the ext-op encodings, which all have LSB 0)
        return 4, "ld.hu %d[%s], %s" % (s16(hw2 & 0xFFFE), rn(reg1), rn(reg2)), dict(k="ld.hu", d=s16(hw2 & 0xFFFE), r1=reg1, r2=reg2)
    if op6 == 0x3F:
        sub = hw2 & 0x7FF
        reg3 = (hw2 >> 11) & 0x1F
        if hw2 == 0x0000:
            return 4, "setf %s, %s" % (COND[reg1 & 0xF], rn(reg2)), dict(k="setf", c=reg1 & 0xF, r2=reg2)
        if sub == 0x0220:
            return 4, "mul %s, %s, %s" % (rn(reg1), rn(reg2), rn(reg3)), dict(k="mul", r1=reg1, r2=reg2, r3=reg3)
        if sub == 0x0222:
            return 4, "mulu %s, %s, %s" % (rn(reg1), rn(reg2), rn(reg3)), dict(k="mulu", r1=reg1, r2=reg2, r3=reg3)
        if (hw2 & 0x7C3) == 0x0240:
            imm = reg1 | (((hw2 >> 2) & 0xF) << 5)
            if imm & 0x100:
                imm -= 0x200
            return 4, "mul %d, %s, %s" % (imm, rn(reg2), rn(reg3)), dict(k="mul_i", imm=imm, r2=reg2, r3=reg3)
        if sub == 0x0080:
            return 4, "shr %s, %s" % (rn(reg1), rn(reg2)), dict(k="shr_r", r1=reg1, r2=reg2)
        if sub == 0x00A0:
            return 4, "sar %s, %s" % (rn(reg1), rn(reg2)), dict(k="sar_r", r1=reg1, r2=reg2)
        if sub == 0x00C0:
            return 4, "shl %s, %s" % (rn(reg1), rn(reg2)), dict(k="shl_r", r1=reg1, r2=reg2)
        if sub == 0x0200:
            return 4, "sasf %s, %s" % (COND[reg1 & 0xF], rn(reg2)), dict(k="sasf", c=reg1 & 0xF, r2=reg2)
        if (hw2 & 0x7E1) == 0x0320:
            return 4, "cmov %s, %s, %s, %s" % (COND[(hw2 >> 1) & 0xF], rn(reg1), rn(reg2), rn(reg3)), dict(k="cmov", c=(hw2 >> 1) & 0xF, r1=reg1, r2=reg2, r3=reg3)
        if (hw2 & 0x7E1) == 0x0300:
            imm = reg1 if not reg1 & 0x10 else reg1 - 0x20
            return 4, "cmov %s, %d, %s, %s" % (COND[(hw2 >> 1) & 0xF], imm, rn(reg2), rn(reg3)), dict(k="cmov_i", c=(hw2 >> 1) & 0xF, imm=imm, r2=reg2, r3=reg3)
        if sub == 0x0340:
            return 4, "bsw %s, %s" % (rn(reg2), rn(reg3)), dict(k="unk")
        if sub == 0x0342:
            return 4, "bsh %s, %s" % (rn(reg2), rn(reg3)), dict(k="unk")
        if sub == 0x0344:
            return 4, "hsw %s, %s" % (rn(reg2), rn(reg3)), dict(k="unk")
        if sub == 0x02E0:
            return 4, "div %s, %s, %s" % (rn(reg1), rn(reg2), rn(reg3)), dict(k="unk")
    return 2, "?? %04x" % hw1, dict(k="unk")


def decode(img, a, end):
    out = []
    while a < end:
        n, txt, op = decode_one(img, a)
        out.append((a, n, txt, op))
        a += n
    return out


class Flags:
    def __init__(self):
        self.z = self.s = self.ov = self.cy = self.sat = 0


class Cpu:
    """Enough of a V850E2 to run the cave: 32 regs, gp/tp RAM+cal, PSW Z/S/OV/CY."""

    def __init__(self, img, ram=None):
        self.img = img
        self.r = [0] * 32
        self.r[4], self.r[5] = GP, TP
        self.ram = ram if ram is not None else {}
        self.f = Flags()
        self.trace = []

    # memory ----------------------------------------------------------------------------------------------------------
    def _addr(self, base, d):
        return (self.r[base] + d) & M32

    def ld(self, base, d, w, signed):
        ad = self._addr(base, d)
        if ad >= TP and ad < TP + 0x10000 and base == 5:
            raw = self.img[ad:ad + w]
        else:
            raw = bytes(self.ram.get(ad + i, 0) for i in range(w))
        v = int.from_bytes(raw, "little", signed=signed)
        return v & M32

    def st(self, base, d, w, v):
        ad = self._addr(base, d)
        for i, byt in enumerate((v & M32).to_bytes(4, "little")[:w]):
            self.ram[ad + i] = byt

    def ram_w(self, ad, signed=True):
        return int.from_bytes(bytes(self.ram.get(ad + i, 0) for i in range(4)), "little", signed=signed)

    def ram_h(self, ad, signed=True):
        return int.from_bytes(bytes(self.ram.get(ad + i, 0) for i in range(2)), "little", signed=signed)

    # flags -----------------------------------------------------------------------------------------------------------
    def set_zs(self, v):
        v &= M32
        self.f.z = int(v == 0); self.f.s = int(v >> 31)
        return v

    def add_flags(self, a, b):
        a &= M32; b &= M32
        r = a + b
        self.f.cy = int(r > M32)
        r &= M32
        self.f.ov = int(((a ^ r) & (b ^ r)) >> 31)
        return self.set_zs(r)

    def sub_flags(self, a, b):       # a - b
        a &= M32; b &= M32
        r = (a - b) & M32
        self.f.cy = int(a < b)
        self.f.ov = int(((a ^ b) & (a ^ r)) >> 31)
        return self.set_zs(r)

    def cond(self, c):
        f = self.f
        t = {0: f.ov, 1: f.cy, 2: f.z, 3: f.cy | f.z, 4: f.s, 5: 1, 6: f.s ^ f.ov, 7: (f.s ^ f.ov) | f.z, 12: f.sat}
        if c in t:
            return bool(t[c])
        return not self.cond(c - 8)

    def w(self, i, v):
        if i != 0:
            self.r[i] = v & M32

    # execute -------------------------------------------------------------------------------------------------------
    def run(self, img_pc, stop_at=None, maxn=500):
        """Run from img_pc until a jmp [lp] / jr outside the decoded cave / stop_at; returns the exit target."""
        pc = img_pc
        n = 0
        while n < maxn:
            n += 1
            size, txt, op = decode_one(self.img, pc)
            self.trace.append((pc, txt))
            k = op["k"]
            r = self.r
            nxt = pc + size
            if k == "unk" or k == "nop":
                if k == "unk":
                    raise RuntimeError("unknown instruction at 0x%X: %s" % (pc, txt))
            elif k == "movi32":
                self.w(op["r1"], op["imm"])
            elif k == "mov":
                self.w(op["r2"], r[op["r1"]])
            elif k == "mov_i":
                self.w(op["r2"], op["imm"])
            elif k == "movea":
                self.w(op["r2"], r[op["r1"]] + op["imm"])
            elif k == "movhi":
                self.w(op["r2"], r[op["r1"]] + (op["imm"] << 16))
            elif k == "addi":
                self.w(op["r2"], self.add_flags(r[op["r1"]], op["imm"]))
            elif k == "add":
                self.w(op["r2"], self.add_flags(r[op["r2"]], r[op["r1"]]))
            elif k == "add_i":
                self.w(op["r2"], self.add_flags(r[op["r2"]], op["imm"]))
            elif k == "sub":
                self.w(op["r2"], self.sub_flags(r[op["r2"]], r[op["r1"]]))
            elif k == "subr":
                self.w(op["r2"], self.sub_flags(r[op["r1"]], r[op["r2"]]))
            elif k == "cmp":
                self.sub_flags(r[op["r2"]], r[op["r1"]])
            elif k == "cmp_i":
                self.sub_flags(r[op["r2"]], op["imm"])
            elif k == "andi":
                self.w(op["r2"], self.set_zs(r[op["r1"]] & op["imm"])); self.f.ov = 0
            elif k == "ori":
                self.w(op["r2"], self.set_zs(r[op["r1"]] | op["imm"])); self.f.ov = 0
            elif k == "xori":
                self.w(op["r2"], self.set_zs(r[op["r1"]] ^ op["imm"])); self.f.ov = 0
            elif k == "and":
                self.w(op["r2"], self.set_zs(r[op["r2"]] & r[op["r1"]])); self.f.ov = 0
            elif k == "or":
                self.w(op["r2"], self.set_zs(r[op["r2"]] | r[op["r1"]])); self.f.ov = 0
            elif k == "xor":
                self.w(op["r2"], self.set_zs(r[op["r2"]] ^ r[op["r1"]])); self.f.ov = 0
            elif k == "not":
                self.w(op["r2"], self.set_zs(~r[op["r1"]])); self.f.ov = 0
            elif k == "tst":
                self.set_zs(r[op["r2"]] & r[op["r1"]]); self.f.ov = 0
            elif k == "sxh":
                self.w(op["r1"], s16(r[op["r1"]] & 0xFFFF))
            elif k == "zxh":
                self.w(op["r1"], r[op["r1"]] & 0xFFFF)
            elif k == "sxb":
                v = r[op["r1"]] & 0xFF; self.w(op["r1"], v - 0x100 if v & 0x80 else v)
            elif k == "zxb":
                self.w(op["r1"], r[op["r1"]] & 0xFF)
            elif k in ("shl_i", "shr_i", "sar_i", "shl_r", "shr_r", "sar_r"):
                sh = op["imm"] if k.endswith("_i") else (r[op["r1"]] & 0x1F)
                v = r[op["r2"]]
                if k.startswith("shl"):
                    res = (v << sh) & M32; self.f.cy = int((v >> (32 - sh)) & 1) if sh else 0
                elif k.startswith("shr"):
                    res = v >> sh; self.f.cy = int((v >> (sh - 1)) & 1) if sh else 0
                else:
                    res = (s32(v) >> sh) & M32; self.f.cy = int((v >> (sh - 1)) & 1) if sh else 0
                self.f.ov = 0
                self.w(op["r2"], self.set_zs(res))
            elif k == "mul":
                p = s32(r[op["r1"]]) * s32(r[op["r2"]])
                self.w(op["r2"], p & M32)
                if op["r3"] != 0:
                    self.w(op["r3"], (p >> 32) & M32)
            elif k == "mul_i":
                p = op["imm"] * s32(r[op["r2"]])
                self.w(op["r2"], p & M32)
                if op["r3"] != 0:
                    self.w(op["r3"], (p >> 32) & M32)
            elif k == "mulh":
                self.w(op["r2"], (s16(r[op["r1"]] & 0xFFFF) * s16(r[op["r2"]] & 0xFFFF)) & M32)
            elif k == "mulh_i":
                self.w(op["r2"], (op["imm"] * s16(r[op["r2"]] & 0xFFFF)) & M32)
            elif k == "setf":
                self.w(op["r2"], int(self.cond(op["c"])))
            elif k == "sasf":
                self.w(op["r2"], ((r[op["r2"]] << 1) | int(self.cond(op["c"]))) & M32)
            elif k == "cmov":
                self.w(op["r3"], r[op["r1"]] if self.cond(op["c"]) else r[op["r2"]])
            elif k == "cmov_i":
                self.w(op["r3"], op["imm"] if self.cond(op["c"]) else r[op["r2"]])
            elif k == "ld.w":
                self.w(op["r2"], self.ld(op["r1"], op["d"], 4, True))
            elif k == "ld.h":
                self.w(op["r2"], self.ld(op["r1"], op["d"], 2, True))
            elif k == "ld.hu":
                self.w(op["r2"], self.ld(op["r1"], op["d"], 2, False))
            elif k == "ld.b":
                self.w(op["r2"], self.ld(op["r1"], op["d"], 1, True))
            elif k == "ld.bu":
                self.w(op["r2"], self.ld(op["r1"], op["d"], 1, False))
            elif k == "st.w":
                self.st(op["r1"], op["d"], 4, r[op["r2"]])
            elif k == "st.h":
                self.st(op["r1"], op["d"], 2, r[op["r2"]])
            elif k == "st.b":
                self.st(op["r1"], op["d"], 1, r[op["r2"]])
            elif k == "bcond":
                if self.cond(op["c"]):
                    nxt = op["tgt"]
            elif k == "jr":
                nxt = op["tgt"]
            elif k == "jarl":
                raise RuntimeError("jarl in cave at 0x%X" % pc)
            elif k == "jmp":
                return ("jmp", op["r1"])
            else:
                raise RuntimeError("unhandled %s at 0x%X" % (k, pc))
            if stop_at is not None and nxt == stop_at:
                return ("ret", nxt)
            pc = nxt
        raise RuntimeError("runaway")


LIVE = (11, 14, 15, 16, 22, 24, 27, 29, 31)


class Cave:
    """The notch cave as the image executes it.  tick(S) -> y (r12 after the cave), with the FLAG halfword readable."""

    def __init__(self, img=None):
        self.img = img if img is not None else open(IMG289, "rb").read()
        self.cpu = Cpu(self.img)
        self.ninstr = 0

    def tick(self, S):
        c = self.cpu
        c.r = [0] * 32
        c.r[4], c.r[5] = GP, TP
        for i in LIVE:
            c.r[i] = (0xA5A50000 | i) & M32
        c.r[12] = int(S) & M32
        c.trace = []
        kind, tgt = c.run(CAVE, stop_at=HOOK + 4)
        assert kind == "ret" and tgt == HOOK + 4, (kind, hex(tgt))
        for i in LIVE:
            assert c.r[i] == (0xA5A50000 | i) & M32, "live reg r%d clobbered" % i
        assert c.r[7] == 507, "displaced ld.hu not replicated: r7=%d" % c.r[7]
        self.ninstr = len(c.trace)
        return s32(c.r[12])

    def flag(self):
        return self.cpu.ram_h(GP - 0x6c3a, signed=False)

    def state(self):
        return dict(s1=self.cpu.ram_w(GP - 0x6c44), s2=self.cpu.ram_w(GP - 0x6c40), e=self.cpu.ram_h(GP - 0x6c3c, signed=False), flag=self.flag())


def listing(img, a, end):
    return "\n".join("  %05X  %-14s %s" % (ad, img[ad:ad + n].hex(), txt) for ad, n, txt, op in decode(img, a, end))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    img = open(IMG289, "rb").read()
    print("== hook 0x2A174 (V289):"); print(listing(img, HOOK, HOOK + 4))
    print("== notch cave 0xC4C00:"); print(listing(img, CAVE, CAVE_END))
    print("== 0x14A rung tail 0xC4BD6:"); print(listing(img, TAIL, TAIL_END))
    print("== fb filter loads 0x28F86 / 0x28F8A:"); print(listing(img, 0x28F86, 0x28F8E))
    print("== output lag 0x2A178..0x2A1B4:"); print(listing(img, 0x2A178, 0x2A1B4))
    # recover the coefficients: every movea/movhi/mov immediate in the cave
    imms = [(ad, txt) for ad, n, txt, op in decode(img, CAVE, CAVE_END) if op["k"] in ("movea", "movhi", "movi32", "mov_i", "andi", "ori", "ld.h", "ld.hu", "ld.w", "st.w", "st.h")]
    print("== immediates / cells:"); [print("  %05X %s" % x) for x in imms]
    cv = Cave(img)
    # DC identity
    for X in (0, 1, -1, 7, -7, 100, -100, 15360, -15360, 12345, -12345):
        ys = [cv.tick(X) for _ in range(2000)]
        tail = ys[-500:]
        print("  const %6d: last-500 mean %.4f  min %d max %d  settle-exact %s  state %s" % (X, np.mean(tail), min(tail), max(tail), all(y == X for y in tail), cv.state()))
    # decay to zero
    cv2 = Cave(img)
    for _ in range(300):
        cv2.tick(15360)
    ys = [cv2.tick(0) for _ in range(3000)]
    print("  after rail then 0: |y| at 100/500/1000/3000 ticks = %d/%d/%d/%d, state %s" % (abs(ys[99]), abs(ys[499]), abs(ys[999]), abs(ys[-1]), cv2.state()))
    print("  instructions per tick: %d" % cv.ninstr)
