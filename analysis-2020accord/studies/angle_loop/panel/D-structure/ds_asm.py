# -*- coding: utf-8 -*-
r"""ds_asm.py -- the D-structure CAVES as listings -> bytes (two-pass), every in-place edit, and the design-time H1: the
assembled bytes EXECUTED by a minimal V850E2 interpreter (decoding FROM THE BYTES, field by field) against the integer
lane's cave arithmetic (ds_lane.DSLane semantics, re-stated per candidate below as cave_ref) on random inputs.
ANALYSIS ONLY: nothing is written to any image.  BELIEF until a built image is decoded by Ghidra (H5).

Every encoding FORM used is controlled against an instruction of the same form already in the V295 image (CONTROLS);
the opcode-field collisions of the firmware-decompile skill are respected (hw2 bit 0 discriminates ld.w/st.w/ld.hu from
ld.h/st.h/mul/jr/jarl; Format XI cmov is hw2 bits 10..5 = 011001; only the condition nibbles 2 (Z) and B (H), which the
image itself uses, appear in a cmov here).
usage: python ds_asm.py   (writes ds_asm_out.txt and ds_cave_<id>.hex)"""
from __future__ import annotations

import glob
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as _M  # noqa: E402,F401  (sets the paths)
import c1_lib as C  # noqa: E402

CAVE = 0xC4C00
HOOK = 0x29D76
RET = 0x29D7A
FRZ_RET = 0x29D7E
GP = 0xFEDF8000
SENT = 0x7FFFFFFF
RAM_A = -0x6C44           # cave RAM word (V289 flown; GATE 1 census in the page)
RAM_B = -0x6C40
IMG = glob.glob(str(C.KIT.parent / "accord-firmwares" / "analysis-2020accord" / "_v295_*plain_image.bin"))[0]
COND = dict(be=0x2, bne=0xA, bh=0xB, bnh=0x3, br=0x5)
CMOV = dict(cmovz=0x2, cmovh=0xB)


def u16(x):
    return x & 0xFFFF


def enc(ins, pc, labels):
    op = ins[0]
    if op == "shl_i":
        return [u16((ins[2] << 11) | (0x16 << 5) | ins[1])]
    if op == "sar_i":
        return [u16((ins[2] << 11) | (0x15 << 5) | ins[1])]
    if op == "mov_i5":
        return [u16((ins[2] << 11) | (0x10 << 5) | (ins[1] & 0x1F))]
    if op == "add_i5":
        return [u16((ins[2] << 11) | (0x12 << 5) | (ins[1] & 0x1F))]
    if op == "mov":          # mov reg1, reg2
        return [u16((ins[2] << 11) | (0x00 << 5) | ins[1])]
    if op == "subr":         # subr reg1, reg2: reg2 = reg1 - reg2
        return [u16((ins[2] << 11) | (0x0C << 5) | ins[1])]
    if op == "sub":
        return [u16((ins[2] << 11) | (0x0D << 5) | ins[1])]
    if op == "add":
        return [u16((ins[2] << 11) | (0x0E << 5) | ins[1])]
    if op == "cmp":
        return [u16((ins[2] << 11) | (0x0F << 5) | ins[1])]
    if op == "jmp":
        return [u16(0x0060 | ins[1])]
    if op == "nop":
        return [0x0000]
    if op == "mov_i32":
        v = labels[ins[1]] if isinstance(ins[1], str) else ins[1]
        return [u16(0x0620 | ins[2]), u16(v), u16(v >> 16)]
    if op == "movea":
        return [u16((ins[3] << 11) | (0x31 << 5) | ins[2]), u16(ins[1])]
    if op == "addi":
        return [u16((ins[3] << 11) | (0x30 << 5) | ins[2]), u16(ins[1])]
    if op == "andi":
        return [u16((ins[3] << 11) | (0x36 << 5) | ins[2]), u16(ins[1])]
    if op == "ld_hu":
        return [u16((ins[3] << 11) | (0x3F << 5) | ins[2]), u16((ins[1] & 0xFFFE) | 1)]
    if op == "ld_h":
        assert ins[1] % 2 == 0
        return [u16((ins[3] << 11) | (0x39 << 5) | ins[2]), u16(ins[1] & 0xFFFE)]
    if op == "ld_w":
        assert ins[1] % 4 == 0
        return [u16((ins[3] << 11) | (0x39 << 5) | ins[2]), u16((ins[1] & 0xFFFE) | 1)]
    if op == "st_w":          # st.w reg2, disp16[reg1]   ins = ("st_w", reg2, disp, reg1)
        assert ins[2] % 4 == 0
        return [u16((ins[1] << 11) | (0x3B << 5) | ins[3]), u16((ins[2] & 0xFFFE) | 1)]
    if op == "mul":
        return [u16((ins[2] << 11) | (0x3F << 5) | ins[1]), u16((ins[3] << 11) | 0x220)]
    if op in CMOV:            # cmov cccc, reg1, reg2, reg3: reg3 = cond ? reg1 : reg2
        return [u16((ins[2] << 11) | (0x3F << 5) | ins[1]), u16((ins[3] << 11) | (0x19 << 5) | (CMOV[op] << 1))]
    if op in COND:
        disp = labels[ins[1]] - pc
        assert -256 <= disp < 256 and disp % 2 == 0, (ins, disp)
        d = disp & 0x1FF
        return [u16((((d >> 4) & 0x1F) << 11) | (0b1011 << 7) | (((d >> 1) & 0x7) << 4) | COND[op])]
    if op in ("jr", "jarl"):
        tgt = labels[ins[1]] if isinstance(ins[1], str) else ins[1]
        disp = tgt - pc
        assert disp % 2 == 0 and -(1 << 21) <= disp < (1 << 21)
        reg = 0 if op == "jr" else ins[2]
        return [u16((reg << 11) | (0x1E << 6) | ((disp >> 16) & 0x3F)), u16(disp & 0xFFFE)]
    if op == "half":
        return [u16(ins[1])]
    raise KeyError(op)


def size(ins):
    return {"mov_i32": 6, "movea": 4, "addi": 4, "andi": 4, "ld_hu": 4, "ld_h": 4, "ld_w": 4, "st_w": 4, "mul": 4,
            "jr": 4, "jarl": 4, "cmovz": 4, "cmovh": 4}.get(ins[0], 2)


# ------------------------------------------------------------------------------------------------- the listings
def _walk(A, term="[G(v)]"):
    A(None, ("ld_hu", -0x6A5E, 4, 8), f"v = gp-0x6a5e (64 counts per km/h)            {term}")
    A(None, ("mov_i32", "TBL", 9), f"r9 -> table                                     {term}")
    A(None, ("ld_hu", 0, 9, 13), "X0")
    A(None, ("cmp", 13, 8), "")
    A(None, ("bh", "L1"), "v > X0 (unsigned): walk")
    A(None, ("ld_hu", 2, 9, 8), "G = G0 (clamp low)")
    A(None, ("br", "APPLY"), "")
    A("L1", ("ld_hu", 6, 9, 13), "X(i+1)")
    A(None, ("cmp", 13, 8), "")
    A(None, ("bnh", "SEG"), "v <= X(i+1): segment i")
    A(None, ("addi", 6, 9, 9), "next row (the 0xFFFF row ends the walk)")
    A(None, ("br", "L1"), "")
    A("SEG", ("ld_hu", 0, 9, 13), "X(i)")
    A(None, ("sub", 13, 8), "dv = v - X(i)")
    A(None, ("ld_h", 4, 9, 13), "S(i), Q12, signed")
    A(None, ("mul", 13, 8, 0), "dv * S(i) (low word)")
    A(None, ("sar_i", 12, 8), ">> 12")
    A(None, ("ld_hu", 2, 9, 13), "G(i)")
    A(None, ("add", 13, 8), "G = G(i) + ((v - X(i)) * S(i) >> 12)")


def _freeze_branchy(A, thr):
    """C1's I freeze (returns to 0x29D7A normally, to 0x29D7E with r6 = 0 when frozen)."""
    A(None, ("ld_hu", -0x4F68, 4, 8), "|driver torque| gp-0x4f68                       [I FREEZE on the hand]")
    A(None, ("movea", thr, 0, 13), f"THR = {thr}")
    A(None, ("cmp", 13, 8), "")
    A(None, ("bh", "FRZ"), "|tq| > THR (unsigned): freeze")
    A(None, ("andi", 0x8000, 14, 13), "r14 = the ramp gp-0x69b0                         [I FREEZE on ramp-in/out]")
    A(None, ("bne", "DONE"), "ramp full: integrate")
    A("FRZ", ("mov_i5", 0, 6), "r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged")
    A(None, ("jr", FRZ_RET), "return past 0x29D7A/0x29D7C")
    A("DONE", ("jmp", 6), "return to 0x29D7A")


def _first_tick(A, rtmp, rt2, target, value, note):
    """target := value on the first PID tick after a skip (Honda's E_prev gp-0x6cf8 == 0x7FFFFFFF)."""
    A(None, ("ld_w", -0x6CF8, 4, rtmp), "Honda's E_prev gp-0x6cf8 (0x7FFFFFFF after any skip tick)  [ENGAGE INIT]")
    A(None, ("mov_i32", SENT, rt2), "")
    A(None, ("cmp", rt2, rtmp), "")
    A(None, ("cmovz", value, target, target), note)


def listing(cid, tbl, thr=512):
    L = []

    def A(lab, ins, com=""):
        L.append((lab, ins, com))
    if cid == "D3a" or cid == "D3b":
        # ---------------- CASCADE: r16 = gp-0x69ae (E4), r26 = R x (the fb filter on the rate) -------------------
        A("C", ("ld_h", -0x6A00, 4, 8), "th_h = gp-0x6a00 (0.1 deg)                       [OUTER angle error]")
        A(None, ("addi", 12000, 8, 9), "validity form: th + 12000 <= 24000 unsigned")
        A(None, ("shl_i", 2, 8), "4 th")
        A(None, ("sub", 8, 16), "e4 = gp-0x69ae - 4 th = 4 (th_sp - th)")
        A(None, ("movea", 24000, 0, 13), "")
        A(None, ("cmp", 13, 9), "")
        A(None, ("cmovh", 0, 16, 16), "|th| > 1200 deg (incl. the -0x8000 baseline wrap): e4 := 0  [ANGLE VALIDITY]")
        _walk(A, "[G(v) on the OUTER gain]")
        A("APPLY", ("mul", 8, 16, 0), "e4 * G                                           [the OUTER angle P]")
        A(None, ("sar_i", 6, 16), "sp_r = (e4 G) >> 6  (ka = 4)")
        A(None, ("shl_i", 2, 16), "4 sp_r (the displaced shl 2)")
        if cid == "D3a":
            A(None, ("sub", 26, 16), "E = 4 sp_r - r26 (held rate, x = gp-0x6a56)     [the INNER rate error]")
        else:
            A(None, ("add", 26, 16), "E = 4 sp_r + r26 (fresh gp-0x6abe = -x/1.698)   [the INNER rate error]")
        _freeze_branchy(A, thr)
    else:
        if cid == "D2c":
            A("C", ("ld_w", RAM_B, 4, 13), "w (cave RAM gp-0x6c40)                           [FB LEAD]")
            A(None, ("mov", 26, 8), "")
            A(None, ("sub", 13, 8), "r26 - w")
            A(None, ("sar_i", 4, 8), ">> 4")
            A(None, ("add", 8, 13), "w += (r26 - w) >> 4   (pole 10.3 Hz)")
            _first_tick(A, 8, 9, 13, 26, "first tick: w := r26")
            A(None, ("st_w", 13, RAM_B, 4), "")
            A(None, ("shl_i", 1, 26), "")
            A(None, ("sub", 13, 26), "r26L = 2 r26 - w = r26 + (r26 - w)  (zero 5.2 Hz)")
            A(None, ("shl_i", 2, 16), "displaced 0x29D76: 4 sp")
        else:
            A("C", ("shl_i", 2, 16), "displaced 0x29D76: 4 sp")
        A(None, ("sub", 26, 16), "displaced 0x29D78: E = 4 sp - r26")
        # ---------------- the D operand, left in r26 for 0x29EE0 (mov r26,r8) ----------------
        if cid == "D1b":
            A(None, ("ld_w", -0x6CC4, 4, 26), "d = gp-0x6cc4 (1 kHz motor-position accumulator)   [D OPERAND]")
            A(None, ("ld_w", RAM_A, 4, 13), "d_prev (cave RAM gp-0x6c44)")
            A(None, ("st_w", 26, RAM_A, 4), "d_prev := d")
            A(None, ("sub", 13, 26), "op = d - d_prev (= -0.2785 counts per deg/s per tick)")
            A(None, ("shl_i", 3, 26), "op << 3")
        elif cid == "D1c":
            A(None, ("ld_w", -0x3D30, 4, 8), "s_new = gp-0x3d30 (the fb state, stored at 0x28FA8)  [D OPERAND]")
            A(None, ("shl_i", 1, 8), "")
            A(None, ("sub", 26, 8), "ds = 2 s_new - r26 = s_new - s_old = 8 x the held-angle step")
            A(None, ("shl_i", 3, 8), "ds << 3")
            A(None, ("ld_w", RAM_A, 4, 13), "lp (cave RAM gp-0x6c44)")
            A(None, ("sub", 13, 8), "")
            A(None, ("sar_i", 3, 8), "")
            A(None, ("add", 13, 8), "lp += ((ds << 3) - lp) >> 3   (pole 21 Hz)")
            _first_tick(A, 13, 9, 8, 0, "first tick: lp := 0")
            A(None, ("st_w", 8, RAM_A, 4), "")
            A(None, ("subr", 0, 8), "")
            A(None, ("mov", 8, 26), "op = -lp")
        elif cid in ("D2a", "D2b", "D2c"):
            A(None, ("ld_h", -0x6ABE, 4, 26), "op = gp-0x6abe (fresh 1 kHz motor-rate EMA)        [D OPERAND]")
            A(None, ("addi", 13000, 26, 8), "Honda's validity form (FUN_0003f776): op + 13000")
            A(None, ("movea", 26000, 0, 13), "")
            A(None, ("cmp", 13, 8), "")
            A(None, ("cmovh", 0, 26, 26), "op + 13000 > 26000 unsigned (incl. the 0x7FFF sentinel): op := 0")
        _walk(A)
        A("APPLY", ("mul", 8, 16, 0), "E * G (low word)                                 [THE SPEED GAIN]")
        A(None, ("sar_i", 8, 16), "E' = (E G) >> 8")
        if cid == "D2b":
            A(None, ("ld_w", RAM_B, 4, 13), "w (cave RAM gp-0x6c40)                           [FWD LEAD]")
            A(None, ("mov", 16, 8), "")
            A(None, ("sub", 13, 8), "E' - w")
            A(None, ("sar_i", 4, 8), "")
            A(None, ("add", 8, 13), "w += (E' - w) >> 4   (pole 10.3 Hz)")
            _first_tick(A, 8, 9, 13, 16, "first tick: w := E'")
            A(None, ("st_w", 13, RAM_B, 4), "")
            A(None, ("mov", 16, 6), "e5 = E' >> 5 (Honda's 0x29D7A/7C, done here: the I integrates E')")
            A(None, ("sar_i", 5, 6), "")
            A(None, ("shl_i", 1, 16), "")
            A(None, ("sub", 13, 16), "r16 = E_L = 2 E' - w  (P sees the lead; zero 5.2 Hz)")
            A(None, ("ld_hu", -0x4F68, 4, 8), "|driver torque|                                  [I FREEZE on the hand]")
            A(None, ("movea", thr, 0, 13), f"THR = {thr}")
            A(None, ("cmp", 13, 8), "")
            A(None, ("cmovh", 0, 6, 6), "|tq| > THR: e5 := 0")
            A(None, ("andi", 0x8000, 14, 13), "ramp gp-0x69b0 (r14)                             [I FREEZE on ramp]")
            A(None, ("cmovz", 0, 6, 6), "ramp not full: e5 := 0")
            A(None, ("jr", FRZ_RET), "return to 0x29D7E (exc from r6)")
        else:
            _freeze_branchy(A, thr)
    rows = []
    for (X, G, S) in tbl:
        rows += [("half", X), ("half", G), ("half", S & 0xFFFF)]
    L.append(("TBL", rows[0], "table: X u16, G u16, S s16 Q12 per row"))
    for r in rows[1:]:
        L.append((None, r, ""))
    return L


def assemble(cid, tbl, thr=512, base=CAVE):
    L = listing(cid, tbl, thr)
    labels = {}
    pc = base
    for lab, ins, _ in L:
        if lab:
            labels[lab] = pc
        pc += size(ins)
    out = bytearray()
    lines = []
    pc = base
    for lab, ins, com in L:
        hw = enc(ins, pc, labels)
        bs = b"".join(struct.pack("<H", h) for h in hw)
        assert len(bs) == size(ins)
        out += bs
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        pc += len(bs)
    return bytes(out), labels, lines


# ------------------------------------------------------------------------------------------------- interpreter
def s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def run_bytes(code, base, regs, mem, start, stop_at=(RET, FRZ_RET), max_steps=400):
    """mem: dict addr(u32) -> byte, both for loads and stores.  Returns (pc_at_exit, regs, mem)."""
    r = dict(regs)
    r[0] = 0
    pc = start
    Z = CY = S = OV = False

    def get(a):
        return code[a - base] | (code[a - base + 1] << 8)

    def ld(a, n):
        return sum(mem[(a + i) & 0xFFFFFFFF] << (8 * i) for i in range(n))

    def st(a, v, n):
        for i in range(n):
            mem[(a + i) & 0xFFFFFFFF] = (v >> (8 * i)) & 0xFF
    for _ in range(max_steps):
        if pc in stop_at:
            return pc, r, mem
        h1 = get(pc)
        op6 = (h1 >> 5) & 0x3F
        reg1, reg2 = h1 & 0x1F, h1 >> 11
        if (op6 >> 2) == 0b1011:                 # Format III Bcond
            cond = h1 & 0xF
            d = ((h1 >> 11) << 4) | (((h1 >> 4) & 7) << 1)
            d = d - 512 if d & 0x100 else d
            take = {0x2: Z, 0xA: not Z, 0xB: not (CY or Z), 0x3: (CY or Z), 0x5: True}[cond]
            pc = pc + d if take else pc + 2
            continue
        if op6 in (0x3C, 0x3D) and not (get(pc + 2) & 1):   # Format V jr / jarl
            h2 = get(pc + 2)
            d = ((h1 & 0x3F) << 16) | (h2 & 0xFFFE)
            d = d - (1 << 22) if d & (1 << 21) else d
            if reg2:
                r[reg2] = pc + 4
            pc = pc + d
            continue
        if h1 == 0x0000:                          # nop (mov r0, r0)
            pc += 2
            continue
        if h1 & 0xFFE0 == 0x0060:                 # jmp [reg1]
            pc = r[reg1] & 0xFFFFFFFF
            continue
        if h1 & 0xFFE0 == 0x0620:                 # mov imm32, reg1
            r[reg1] = s32(get(pc + 2) | (get(pc + 4) << 16))
            pc += 6
            continue
        if op6 == 0x00:                           # mov reg1, reg2
            r[reg2] = r[reg1]
            pc += 2
            continue
        if op6 in (0x16, 0x15, 0x10, 0x12):       # shl / sar / mov / add  imm5
            imm = h1 & 0x1F
            if op6 == 0x16:
                res = s32(r[reg2] << imm)
                CY = bool((r[reg2] >> (32 - imm)) & 1) if imm else False
                OV = False
            elif op6 == 0x15:
                res = s32(r[reg2]) >> imm
                OV = False
            elif op6 == 0x10:
                res = imm - 32 if imm & 0x10 else imm
            else:
                si = imm - 32 if imm & 0x10 else imm
                a = s32(r[reg2])
                res = s32(a + si)
                CY = ((a & 0xFFFFFFFF) + (si & 0xFFFFFFFF)) > 0xFFFFFFFF
                OV = (a + si) != res
            r[reg2] = s32(res)
            if op6 != 0x10:
                Z, S = r[reg2] == 0, r[reg2] < 0
            pc += 2
            continue
        if op6 in (0x0C, 0x0D, 0x0E, 0x0F):       # subr / sub / add / cmp
            a, b = s32(r[reg2]), s32(r[reg1])
            if op6 == 0x0C:
                res = b - a
                CY = (b & 0xFFFFFFFF) < (a & 0xFFFFFFFF)
            elif op6 in (0x0D, 0x0F):
                res = a - b
                CY = (a & 0xFFFFFFFF) < (b & 0xFFFFFFFF)
            else:
                res = a + b
                CY = ((a & 0xFFFFFFFF) + (b & 0xFFFFFFFF)) > 0xFFFFFFFF
            OV = res != s32(res)
            Z = s32(res) == 0
            S = s32(res) < 0
            if op6 != 0x0F:
                r[reg2] = s32(res)
            pc += 2
            continue
        h2 = get(pc + 2)
        if op6 in (0x31, 0x30, 0x36):             # movea / addi / andi
            imm = h2 - 0x10000 if (h2 & 0x8000 and op6 != 0x36) else h2
            if op6 == 0x36:
                res = (r[reg1] & 0xFFFFFFFF) & h2
                Z, S, OV = res == 0, False, False
            else:
                res = s32(r[reg1] + imm)
                if op6 == 0x30:
                    Z, S = res == 0, res < 0
                    CY = ((r[reg1] & 0xFFFFFFFF) + (imm & 0xFFFFFFFF)) > 0xFFFFFFFF
            r[reg2] = s32(res)
            pc += 4
            continue
        if op6 == 0x3F and ((h2 >> 5) & 0x3F) == 0x19 and not (h2 & 1):   # cmov cccc, reg1, reg2, reg3
            c = (h2 >> 1) & 0xF
            take = {0x2: Z, 0xB: not (CY or Z)}[c]
            reg3 = h2 >> 11
            r[reg3] = r[reg1] if take else r[reg2]
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 0x7FF) == 0x220:   # mul reg1, reg2, reg3
            p = s32(r[reg2]) * s32(r[reg1])
            r[reg2] = s32(p)
            reg3 = h2 >> 11
            if reg3:
                r[reg3] = s32(p >> 32)
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 1) and reg2:      # ld.hu disp16[reg1], reg2
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            r[reg2] = ld((r[reg1] + disp) & 0xFFFFFFFF, 2)
            pc += 4
            continue
        if op6 == 0x39:                            # ld.h (hw2[0]=0) / ld.w (hw2[0]=1)
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            a = (r[reg1] + disp) & 0xFFFFFFFF
            if h2 & 1:
                r[reg2] = s32(ld(a, 4))
            else:
                v = ld(a, 2)
                r[reg2] = v - 0x10000 if v & 0x8000 else v
            pc += 4
            continue
        if op6 == 0x3B and (h2 & 1):               # st.w reg2, disp16[reg1]
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            st((r[reg1] + disp) & 0xFFFFFFFF, r[reg2] & 0xFFFFFFFF, 4)
            pc += 4
            continue
        raise RuntimeError(f"undecoded halfword {h1:04x} at {pc:#x}")
    raise RuntimeError("no exit")


CONTROLS = [  # (address in V295, expected bytes, the form it controls)
    (0x28F0E, "e4 57 a3 95", "ld.hu -0x6a5e[gp],r10 -> our ld.hu disp[gp]"),
    (0x29D26, "e6 6f 01 00", "ld.hu 0[r6],r13 -> our ld.hu disp[r9]"),
    (0x29CFC, "30 06", "mov imm32,r16 (hw1) -> our mov imm32"),
    (0x29E62, "2d 06 01 70 17 00", "mov 0x177001,r13 -> our mov 0x7fffffff,r9|r13"),
    (0x29E50, "ed 41", "cmp r13,r8"),
    (0x29ED2, "ed 3f 20 02", "mul r13,r7,r0"),
    (0x29E3E, "a8 42", "sar 8,r8"),
    (0x29DAC, "ca 6a", "shl 0xa,r13 -> our shl imm5"),
    (0x52688, "20 6e ff 7f", "movea 0x7fff,r0,r13 -> our movea imm,r0,r13"),
    (0x28F50, "07 5e e0 2e", "addi 0x2ee0,r7,r11 -> our addi imm,reg,reg"),
    (0x29A30, "01 32", "mov 1,r6 -> our mov 0,r6"),
    (0x29D6A, "08 80", "mov r8,r16 -> our mov reg,reg"),
    (0x29D90, "80 69", "subr r0,r13 -> our subr r0,r8"),
    (0x29E8E, "4a 42", "add 0xa,r8 -> (add imm5 form; not used by the final listings)"),
    (0x29E5E, "24 47 09 93", "ld.w -0x6cf8[gp],r8 -> our ld.w disp[gp]"),
    (0x28FA8, "64 4f d1 c2", "st.w r9,-0x3d30[gp] -> our st.w reg,disp[gp]"),
    (0x3F77E, "24 47 42 95", "ld.h -0x6abe[gp],r8 (FUN_0003f776) -> our ld.h -0x6abe[gp],r26 (form)"),
    (0x3E72A, "24 47 3d 93", "ld.w -0x6cc4[gp],r8 (FUN_0003e6d8) -> our ld.w -0x6cc4[gp],r26 (form)"),
    (0x40AEA, "24 77 00 96", "ld.h -0x6a00[gp],r14 -> our ld.h -0x6a00[gp],r8 (form)"),
    (0x29E7E, "f0 47 32 db", "cmovnc r16,r8,r27 -> our cmov form (Format XI)"),
    (0x189CC, "fd 37 24 33", "cmovz (cond 2) -> our cmovz"),
    (0x3539E, "ee 47 36 43", "cmovh (cond B) -> our cmovh"),
    (0x29372, "80 07 c2 03", "jr 0x29734 -> our jr 0x29D7E"),
    (0x2A1E4, "d5 05", "br"),
    (0x29384, "f3 05", "bnh"),
    (0x29A56, "da 05", "bne"),
    (0x29D76, "c2 82 ba 81", "shl 2,r16 ; sub r26,r16 -> displaced verbatim"),
]


# ------------------------------------------------------------------------------------------------- the reference
def cave_ref(cid, tbl, thr, sp, r26, v, tq, ramp, cells):
    """the cave as ds_lane.DSLane computes it (scalar).  cells: dict of gp cells (signed values) incl. the cave RAM.
    returns (r16, exit_pc, r6_on_exit_or_None, r26_out, cells_after)."""
    from ds_lane import SENT as _S  # noqa: F401
    c = dict(cells)
    G = C.cave_G(v & 0xFFFF, tbl)
    frz = (tq & 0xFFFF) > thr or (ramp & 0x8000) == 0
    first = c["6cf8"] == SENT
    if cid in ("D3a", "D3b"):
        th = c["6a00"]
        e4 = s32(sp - (th << 2)) if -12000 <= th <= 12000 else 0
        spr = s32(e4 * G) >> 6
        E = s32((spr << 2) - r26) if cid == "D3a" else s32((spr << 2) + r26)
        return E, (FRZ_RET if frz else RET), (0 if frz else None), r26, c
    r26_in = r26
    if cid == "D2c":
        w = s32(c["6c40"] + (s32(r26 - c["6c40"]) >> 4))
        if first:
            w = r26
        c["6c40"] = w
        r26_in = s32(s32(r26 << 1) - w)
    E = s32((sp << 2) - r26_in)
    op = r26
    if cid == "D1b":
        op = s32(s32(c["6cc4"] - c["6c44"]) << 3)
        c["6c44"] = c["6cc4"]
    elif cid == "D1c":
        ds = s32(s32(s32(c["3d30"] << 1) - r26) << 3)
        lp = s32(c["6c44"] + (s32(ds - c["6c44"]) >> 3))
        if first:
            lp = 0
        c["6c44"] = lp
        op = s32(-lp)
    elif cid in ("D2a", "D2b", "D2c"):
        ab = c["6abe"]
        op = ab if ((ab + 13000) & 0xFFFFFFFF) <= 26000 else 0
    Ep = s32(E * G) >> 8
    if cid == "D2b":
        w = s32(c["6c40"] + (s32(Ep - c["6c40"]) >> 4))
        if first:
            w = Ep
        c["6c40"] = w
        e5 = 0 if frz else (Ep >> 5)
        return s32(s32(Ep << 1) - w), FRZ_RET, e5, op, c
    return Ep, (FRZ_RET if frz else RET), (0 if frz else None), op, c


CELLS = {"6a5e": -0x6A5E, "4f68": -0x4F68, "6cf8": -0x6CF8, "6abe": -0x6ABE, "6cc4": -0x6CC4, "6c44": RAM_A,
         "6c40": RAM_B, "3d30": -0x3D30, "6a00": -0x6A00}
WIDTH = {"6a5e": 2, "4f68": 2, "6cf8": 4, "6abe": 2, "6cc4": 4, "6c44": 4, "6c40": 4, "3d30": 4, "6a00": 2}
SCRATCH = {"B0": (6, 8, 9, 13, 16), "D1a": (6, 8, 9, 13, 16), "D1b": (6, 8, 9, 13, 16, 26), "D1c": (6, 8, 9, 13, 16, 26),
           "D2a": (6, 8, 9, 13, 16, 26), "D2b": (6, 8, 9, 13, 16, 26), "D2c": (6, 8, 9, 13, 16, 26),
           "D3a": (6, 8, 9, 13, 16), "D3b": (6, 8, 9, 13, 16)}
WRITES = {"D1b": {"6c44"}, "D1c": {"6c44"}, "D2b": {"6c40"}, "D2c": {"6c40"}}


def h1_test(cid, tbl, code, thr=512, N=60000, seed=7):
    rng = np.random.default_rng(seed)
    bad = 0
    edges = [0, 32000, 65535] + [x + d for x, _, _ in tbl if x < 0xFFFF for d in (-1, 0, 1)]
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 50 else 32767
        r26 = int(rng.integers(-65535, 65536))
        v = int(rng.integers(0, 32001)) if k % 7 else int(rng.choice(edges))
        tq = int(rng.integers(0, 3000)) if k % 3 else int(rng.choice([0, thr - 1, thr, thr + 1, 65535]))
        ramp = int(rng.choice([0x8000, 0x8000, 0x8000, int(rng.integers(1, 0x8000))]))
        cells = {"6a5e": v, "4f68": tq, "6cf8": int(rng.choice([SENT, int(rng.integers(-800000, 800000))])),
                 "6abe": int(rng.choice([32767, int(rng.integers(-14000, 14000)), -13001, 13000, -13000, 13001])),
                 "6cc4": int(rng.integers(-2 ** 31, 2 ** 31)), "6c44": int(rng.integers(-2 ** 31, 2 ** 31)),
                 "6c40": int(rng.integers(-400000, 400000)), "3d30": int(rng.integers(-96000, 96000)),
                 "6a00": int(rng.choice([int(rng.integers(-4000, 4000)), 32700, -32768, 12000, 12001, -12001]))}
        if cid == "D1b" and k % 3:
            cells["6c44"] = s32(cells["6cc4"] - int(rng.integers(-300, 300)))
        mem = {}
        for nm, off in CELLS.items():
            a = (GP + off) & 0xFFFFFFFF
            val = cells[nm] & ((1 << (8 * WIDTH[nm])) - 1)
            for i in range(WIDTH[nm]):
                mem[a + i] = (val >> (8 * i)) & 0xFF
        for i, b in enumerate(code):
            mem[CAVE + i] = b
        regs = {i: int(rng.integers(-2 ** 31, 2 ** 31)) for i in range(32)}
        regs.update({0: 0, 16: sp, 26: r26, 14: ramp, 4: s32(GP), 6: RET})
        pc_exit, rr, mem2 = run_bytes(code, CAVE, regs, mem, CAVE)
        r16, ex, r6, op, c2 = cave_ref(cid, tbl, thr, sp, r26, v, tq, ramp, cells)
        ok = rr[16] == r16 and pc_exit == ex and (r6 is None or rr[6] == r6)
        if cid in ("D1b", "D1c", "D2a", "D2b", "D2c"):
            ok = ok and rr[26] == op
        ok = ok and all(rr[i] == regs[i] for i in range(32) if i not in SCRATCH[cid])
        for nm in WRITES.get(cid, ()):
            a = (GP + CELLS[nm]) & 0xFFFFFFFF
            got = s32(sum(mem2[a + i] << (8 * i) for i in range(4)))
            ok = ok and got == c2[nm]
        # no other RAM changed
        for nm, off in CELLS.items():
            if nm in WRITES.get(cid, ()):
                continue
            a = (GP + off) & 0xFFFFFFFF
            ok = ok and all(mem2[a + i] == ((cells[nm] & ((1 << (8 * WIDTH[nm])) - 1)) >> (8 * i)) & 0xFF
                            for i in range(WIDTH[nm]))
        if not ok:
            bad += 1
            if bad <= 3:
                print("   MISMATCH", cid, dict(sp=sp, r26=r26, v=v, tq=tq, ramp=ramp), cells, "got", rr[16], rr[26],
                      hex(pc_exit), "want", r16, op, hex(ex))
    return bad


def main(tables=None):
    import json
    import ds_gate2 as G2
    OUT = []

    def P(s=""):
        print(s, flush=True)
        OUT.append(s)
    img = open(IMG, "rb").read()
    tabs = tables or {k: [tuple(r) for r in v] for k, v in json.loads((G2.OUT / "final_tables.json").read_text()).items()}
    P("ENCODING-FORM CONTROLS (V295 bytes):")
    for a, exp, what in CONTROLS:
        got = img[a:a + len(bytes.fromhex(exp.replace(' ', '')))].hex(" ")
        P(f"  {a:#07x} {got:18s} {'OK ' if got == exp else 'BAD'} {what}")
    hook = b"".join(struct.pack("<H", h) for h in enc(("jarl", CAVE, 6), HOOK, {}))
    v112 = b"".join(struct.pack("<H", h) for h in enc(("jarl", 0xC4B34, 31), 0x55C0E, {}))
    P(f"HOOK 0x29D76 c2 82 ba 81 -> {hook.hex(' ')} (jarl {CAVE:#x}, r6); encoder control: the flown V112 hook 0x55C0E "
      f"reads {img[0x55C0E:0x55C12].hex(' ')}, encoder {v112.hex(' ')} -> {'MATCH' if v112 == img[0x55C0E:0x55C12] else 'MISMATCH'}")
    P(f"free span 0xC4BD8..0xC4FEF all 0xFF in V295: {all(x == 0xFF for x in img[0xC4BD8:0xC4FF0])}")
    for cid in ("B0r", "D1a", "D1b", "D1c", "D2a", "D2b", "D2c", "D3a", "D3b"):
        tbl = tabs[cid]
        code, labels, lines = assemble(cid if cid not in ("D1a", "B0r") else "B0", tbl)
        ncode = labels["TBL"] - CAVE
        P("=" * 120)
        P(f"{cid}: cave at {CAVE:#x}: {len(code)} bytes = {ncode} code ({sum(1 for l in lines if l[2][0] != 'half')} "
          f"instructions) + {len(code) - ncode} table ({len(tbl)} rows incl. the 0xFFFF row)")
        for pc, lab, ins, bs, com in lines:
            if ins[0] == "half" and lab != "TBL":
                continue
            P(f"  {pc:#07x} {lab:6s} {bs:18s} {str(ins):40s} {com}")
        P("  table rows: " + " ".join(f"({x}, {g}, {s})" for x, g, s in tbl))
        NH1 = 60000
        nb = h1_test(cid if cid not in ("D1a", "B0r") else "B0", tbl, code, N=NH1)
        P(f"  H1 (design time): assembled bytes executed vs the lane's cave arithmetic, {NH1} random inputs (sentinels, "
          f"table edges, validity edges, first-tick, register file): {nb} mismatches")
        (HERE / f"ds_cave_{cid}.hex").write_text(code.hex(" "))
    (HERE / "ds_asm_out.txt").write_text("\n".join(OUT), encoding="utf-8")


if __name__ == "__main__":
    main()
