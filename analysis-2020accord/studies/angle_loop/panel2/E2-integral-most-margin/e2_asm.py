# -*- coding: utf-8 -*-
r"""e2_asm.py -- designer E2's caves as listings -> bytes, and the design-time H1: the assembled bytes EXECUTED by a
V850E2 interpreter against the E2Lane cave decision (an independent scalar re-statement below, cave_ref), on random and
edge inputs.  ANALYSIS ONLY: no image is written.  BELIEF until Ghidra decodes a BUILT image (the builder's H5).

Every implementation is rev2-A's P2 cave (ds_asm.listing('D2a') with P2's 6-knot table) with ONLY the integral-policy
block changed.  CONTROL A: the builder with policy 'P2' reproduces c2/rev2A/c2_cave_P2.hex byte for byte.  CONTROL B:
this interpreter == ds_asm.run_bytes on P2's bytes (20 000 random inputs).  Forms new to the panel's listings (xor,
blt/bge, ld.h -0x4f60, ld.w -0x6dd0, sar/shl imm5 on other registers, cmp r0) are controlled against instructions of
the same form already in the V295 image (FORMS below; each also decoded by Ghidra dry-run in the design page).

POLICY BLOCK (after APPLY: r16 = E', r8 = G is dead; order = E2Lane's ordered decision):
  1  ld.hu -0x4f68[gp],r8 ; movea THR,r0,r13 ; cmp r13,r8 ; bh FRZ|LEAK          (P2's hard freeze; leak variant)
  2  movea T,r0,r13 ; cmp r13,r8 ; bnh N2 ; ld.h -0x4f60[gp],r9 ; xor r16,r9 ; blt FRZ ; N2:     (opposing hand)
  3  ld.h -0x6a00[gp],r9 ; cmp r0,r9 ; bge A1 ; subr r0,r9 ; A1: shl SH,r9 ; addi B,r9,r9 ;
     ld.w -0x6dd0[gp],r13 ; sar 10,r13 ; cmp r0,r16 ; bge A2 ; subr r0,r13 ; A2: cmp r9,r13 ; bge FRZ       (ARB)
  4  andi 0x8000,r14,r13 ; bne DONE                                                   (P2's ramp freeze)
     FRZ: mov 0,r6 ; jr 0x29D7E   |  LEAK: ld.w -0x6dd0[gp],r6 ; sar S,r6 ; subr r0,r6 ; jr 0x29D7E  |  DONE: jmp [r6]
usage: python e2_asm.py   (writes e2_asm_out.txt and e2_cave_<id>.hex)"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e2_common import AL, R  # noqa: E402,F401
sys.path.insert(0, str(AL / "panel" / "D-structure"))
import ds_asm as DA  # noqa: E402
import c1_lib as C  # noqa: E402

CAVE, RET, FRZ_RET, GP, SENT = DA.CAVE, DA.RET, DA.FRZ_RET, DA.GP, DA.SENT
COND = dict(DA.COND, bge=0xE, blt=0x6)

# the implementations (policy dicts).  thr = P2's 512; ramp = keep the ramp test
IMPL = {
    "P2": dict(),
    "S300": dict(sgn=300),
    "S200": dict(sgn=200),
    "A": dict(arb_sh=6, arb_B=1250),
    "Ah": dict(arb_sh=6, arb_B=625),
    "AS": dict(arb_sh=6, arb_B=1250, sgn=300),
    "L13": dict(leak=13),
    "A-NR": dict(arb_sh=6, arb_B=1250, ramp=False),
    "A2": dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250),
    "A2S": dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, sgn=300),
    "A3": dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096),
    "A2L": dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, sgn=200, leak=13, leak_opp=True, leak_hard=False,
                opp_first=True),
    "A2-NR": dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, ramp=False),
    "A2S-C": dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, sgn=300, cam=True),
    "K0": dict(nopol=True),
}


def u16(x):
    return x & 0xFFFF


def enc(ins, pc, labels):
    op = ins[0]
    if op == "xor":                                    # Format I xor reg1, reg2 (op 0x09): reg2 ^= reg1
        return [u16((ins[2] << 11) | (0x09 << 5) | ins[1])]
    if op in ("bge", "blt"):
        disp = labels[ins[1]] - pc
        assert -256 <= disp < 256 and disp % 2 == 0
        d = disp & 0x1FF
        return [u16((((d >> 4) & 0x1F) << 11) | (0b1011 << 7) | (((d >> 1) & 0x7) << 4) | COND[op])]
    return DA.enc(ins, pc, labels)


def size(ins):
    return 2 if ins[0] in ("xor", "bge", "blt") else DA.size(ins)


def listing(pol, tbl):
    L = []

    def A(lab, ins, com=""):
        L.append((lab, ins, com))
    A("C", ("shl_i", 2, 16), "displaced 0x29D76: 4 sp")
    A(None, ("sub", 26, 16), "displaced 0x29D78: E = 4 sp - r26 = 16 (th_sp - th)")
    A(None, ("ld_h", -0x6ABE, 4, 26), "op = gp-0x6abe (fresh 1 kHz motor-rate EMA)        [D OPERAND]")
    A(None, ("addi", 13000, 26, 8), "Honda's validity form (FUN_0003f776): op + 13000")
    A(None, ("movea", 26000, 0, 13), "")
    A(None, ("cmp", 13, 8), "")
    A(None, ("cmovh", 0, 26, 26), "op + 13000 > 26000 unsigned (incl. the 0x7FFF sentinel): op := 0")
    DA._walk(A)
    A("APPLY", ("mul", 8, 16, 0), "E * G (low word)                                 [THE SPEED GAIN]")
    A(None, ("sar_i", 8, 16), "E' = (E G) >> 8")
    if pol.get("nopol"):
        A("DONE", ("jmp", 6), "return to 0x29D7A (no I policy: Ki = 0 in this implementation)")
    else:
        leak_hard = pol.get("leak_hard", bool(pol.get("leak")) and not pol.get("leak_opp"))
        hard_tgt = "LEAK" if leak_hard else "FRZ"
        opp_tgt = "LEAK" if pol.get("leak_opp") else "FRZ"
        if pol.get("cam"):
            A(None, ("cmp", 0, 25), "r25 = (gp-0x6803 == 2), set at 0x29A82 (READ only)   [CAMERA GATE]")
            A(None, ("be", "CAM"), "not the angle fork's frame (the camera sends field 0): go inert")
        A(None, ("ld_hu", -0x4F68, 4, 8), "|driver torque| gp-0x4f68                        [HAND]")

        def hard():
            A(None, ("movea", pol.get("thr", 512), 0, 13), f"THR = {pol.get('thr', 512)}                [1 hard hand]")
            A(None, ("cmp", 13, 8), "")
            A(None, ("bh", hard_tgt), f"|tq| > THR (unsigned): {'leak' if leak_hard else 'freeze'}")

        def opp():
            A(None, ("movea", pol["sgn"], 0, 13), f"T = {pol['sgn']}                                  [2 OPPOSING HAND]")
            A(None, ("cmp", 13, 8), "")
            A(None, ("bnh", "N2"), "|tq| <= T: no hand")
            A(None, ("ld_h", -0x4F60, 4, 9), "signed hand torque gp-0x4f60 (sign = the push direction)")
            A(None, ("xor", 16, 9), "sign(hand) xor sign(E')")
            A(None, ("blt", opp_tgt), f"signs differ: the hand pushes AWAY from the setpoint -> {opp_tgt.lower()}")
            A("N2", None, "")
        if pol.get("opp_first"):
            opp()
            hard()
        else:
            hard()
            if pol.get("sgn"):
                opp()
        if pol.get("arb_sh"):
            A(None, ("ld_h", -0x6A00, 4, 9), "th = gp-0x6a00 (the held angle the P sees)    [3 ANGLE-REFERENCED BOUND]")
            A(None, ("cmp", 0, 9), "")
            A(None, ("bge", "A1"), "")
            A(None, ("subr", 0, 9), "|th|")
            if pol.get("arb_sh_lo") is not None:
                A("A1", ("ld_hu", -0x6A5E, 4, 8), "v = gp-0x6a5e (64 counts per km/h)             [two-level slope]")
                A(None, ("movea", pol["arb_vth"], 0, 13), f"VTH = {pol['arb_vth']} ({pol['arb_vth'] / 230.4:.2f} m/s)")
                A(None, ("cmp", 13, 8), "")
                A(None, ("bh", "AH"), "v > VTH (unsigned): high slope")
                A(None, ("shl_i", pol["arb_sh_lo"], 9), f"|th| << {pol['arb_sh_lo']}  (k_hat {0.160 * 10 * (1 << pol['arb_sh_lo']):.0f} T/deg)")
                A(None, ("br", "AB"), "")
                A("AH", ("shl_i", pol["arb_sh"], 9), f"|th| << {pol['arb_sh']}  (k_hat {0.160 * 10 * (1 << pol['arb_sh']):.0f} T/deg)")
                A("AB", None, "")
            else:
                A("A1", ("shl_i", pol["arb_sh"], 9), f"|th| << {pol['arb_sh']}  (k_hat {0.160 * 10 * (1 << pol['arb_sh']):.0f} T/deg)")
            A(None, ("addi", pol["arb_B"], 9, 9), f"+ B = {pol['arb_B']} S (~{0.160 * pol['arb_B']:.0f} T): the bound")
            if pol.get("arb_vcap") is not None:
                A(None, ("movea", pol["arb_vcap"], 0, 13), f"VCAP = {pol['arb_vcap']} ({pol['arb_vcap'] / 230.4:.2f} m/s)  [low-speed cap]")
                A(None, ("cmp", 13, 8), "r8 = v (still)")
                A(None, ("bh", "NC"), "v > VCAP: no cap")
                A(None, ("movea", pol["arb_cap"], 0, 13), f"CAP = {pol['arb_cap']} S (~{0.160 * pol['arb_cap']:.0f} T)")
                A(None, ("cmp", 13, 9), "")
                A(None, ("cmovh", 13, 9, 9), "bound = min(bound, CAP)")
                A("NC", None, "")
            A(None, ("ld_w", -0x6DD0, 4, 13), "I8 = gp-0x6dd0 (Honda's I state, 8 x I; READ only)")
            A(None, ("sar_i", 10, 13), "I >> 7 = the I's share of S")
            A(None, ("cmp", 0, 16), "")
            A(None, ("bge", "A2"), "")
            A(None, ("subr", 0, 13), "t = sgn(E') (I >> 7): + when the I would wind further")
            A("A2", ("cmp", 9, 13), "t - bound")
            A(None, ("bge", "FRZ"), "winding past the bound: freeze")
        if pol.get("ramp", True):
            A(None, ("andi", 0x8000, 14, 13), "r14 = the ramp gp-0x69b0                          [4 RAMP-IN]")
            A(None, ("bne", "DONE"), "ramp full: integrate")
        else:
            A("DONE", ("jmp", 6), "no ramp test: return to 0x29D7A")
        A("FRZ", ("mov_i5", 0, 6), "r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged")
        A(None, ("jr", FRZ_RET), "return past 0x29D7A/0x29D7C")
        if pol.get("leak") and (leak_hard or pol.get("leak_opp")):
            A("LEAK", ("ld_w", -0x6DD0, 4, 6), "I8                                              [LEAK]")
            A(None, ("sar_i", pol["leak"], 6), f"I8 >> {pol['leak']}")
            A(None, ("subr", 0, 6), "e5 = -(I8 >> s): inc = (e5 Ki) >> 3")
            A(None, ("jr", FRZ_RET), "return past 0x29D7A/0x29D7C")
        if pol.get("cam"):
            A("CAM", ("mov_i5", 0, 16), "E' := 0 -> P = 0")
            A(None, ("mov_i5", 0, 26), "op := 0 -> D = 0")
            A(None, ("ld_w", -0x6DD0, 4, 6), "I8")
            A(None, ("sar_i", 6, 6), "")
            A(None, ("subr", 0, 6), "e5 = -(I8 >> 6): I x 0.125 per tick (gone in ~3 ms)")
            A(None, ("jr", FRZ_RET), "")
        if pol.get("ramp", True):
            A("DONE", ("jmp", 6), "return to 0x29D7A")
    rows = []
    for (X, G, S) in tbl:
        rows += [("half", X), ("half", G), ("half", S & 0xFFFF)]
    L.append(("TBL", rows[0], "table: X u16, G u16, S s16 Q12 per row"))
    for r in rows[1:]:
        L.append((None, r, ""))
    # fold empty label lines onto the next instruction
    out, pend = [], None
    for lab, ins, com in L:
        if ins is None:
            pend = lab
            continue
        if pend:
            lab = lab or pend
            pend = None
        out.append((lab, ins, com))
    return out


def assemble(pol, tbl, base=CAVE):
    L = listing(pol, tbl)
    labels, pc = {}, base
    for lab, ins, _ in L:
        if lab:
            labels[lab] = pc
        pc += size(ins)
    out, lines, pc = bytearray(), [], base
    for lab, ins, com in L:
        bs = b"".join(struct.pack("<H", h) for h in enc(ins, pc, labels))
        assert len(bs) == size(ins), ins
        out += bs
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        pc += len(bs)
    return bytes(out), labels, lines


# --------------------------------------------------------------------------------------------- the interpreter
def s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def run_bytes(code, base, regs, mem, start, stop_at=(RET, FRZ_RET), max_steps=600):
    """V850E2 subset, decoded field by field from the bytes; flags Z S OV CY as the ISA defines them for each op."""
    r = dict(regs)
    r[0] = 0
    pc = start
    Z = S = OV = CY = False

    def get(a):
        return code[a - base] | (code[a - base + 1] << 8)

    def ld(a, n):
        return sum(mem[(a + i) & 0xFFFFFFFF] << (8 * i) for i in range(n))
    for _ in range(max_steps):
        if pc in stop_at:
            return pc, r, mem
        h1 = get(pc)
        op6 = (h1 >> 5) & 0x3F
        reg1, reg2 = h1 & 0x1F, h1 >> 11
        if (op6 >> 2) == 0b1011:                                           # Bcond
            cond = h1 & 0xF
            d = ((h1 >> 11) << 4) | (((h1 >> 4) & 7) << 1)
            d = d - 512 if d & 0x100 else d
            take = {0x2: Z, 0xA: not Z, 0xB: not (CY or Z), 0x3: (CY or Z), 0x5: True,
                    0xE: not (S ^ OV), 0x6: (S ^ OV)}[cond]
            pc = pc + d if take else pc + 2
            continue
        if op6 in (0x3C, 0x3D) and not (get(pc + 2) & 1):                  # jr / jarl
            h2 = get(pc + 2)
            d = ((h1 & 0x3F) << 16) | (h2 & 0xFFFE)
            d = d - (1 << 22) if d & (1 << 21) else d
            if reg2:
                r[reg2] = pc + 4
            pc = pc + d
            continue
        if h1 & 0xFFE0 == 0x0060:                                          # jmp [reg1]
            pc = r[reg1] & 0xFFFFFFFF
            continue
        if h1 & 0xFFE0 == 0x0620:                                          # mov imm32
            r[reg1] = s32(get(pc + 2) | (get(pc + 4) << 16))
            pc += 6
            continue
        if op6 == 0x00:                                                    # mov reg1, reg2
            r[reg2] = r[reg1]
            pc += 2
            continue
        if op6 == 0x09:                                                    # xor
            r[reg2] = s32(r[reg2] ^ r[reg1])
            Z, S, OV = r[reg2] == 0, r[reg2] < 0, False
            pc += 2
            continue
        if op6 in (0x16, 0x15, 0x10, 0x12):                                # shl / sar / mov / add imm5
            imm = h1 & 0x1F
            if op6 == 0x16:
                res = s32(r[reg2] << imm)
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
                OV = (a + si) != res
            r[reg2] = s32(res)
            if op6 != 0x10:
                Z, S = r[reg2] == 0, r[reg2] < 0
            pc += 2
            continue
        if op6 in (0x0C, 0x0D, 0x0E, 0x0F):                                # subr / sub / add / cmp
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
            Z, S = s32(res) == 0, s32(res) < 0
            if op6 != 0x0F:
                r[reg2] = s32(res)
            pc += 2
            continue
        h2 = get(pc + 2)
        if op6 in (0x31, 0x30, 0x36):                                      # movea / addi / andi
            imm = h2 - 0x10000 if (h2 & 0x8000 and op6 != 0x36) else h2
            if op6 == 0x36:
                res = (r[reg1] & 0xFFFFFFFF) & h2
                Z, S, OV = res == 0, False, False
            else:
                a = s32(r[reg1])
                res = s32(a + imm)
                if op6 == 0x30:
                    OV = (a + imm) != res
                    Z, S = res == 0, res < 0
                    CY = ((a & 0xFFFFFFFF) + (imm & 0xFFFFFFFF)) > 0xFFFFFFFF
            r[reg2] = s32(res)
            pc += 4
            continue
        if op6 == 0x3F and ((h2 >> 5) & 0x3F) == 0x19 and not (h2 & 1):   # cmov
            c = (h2 >> 1) & 0xF
            take = {0x2: Z, 0xB: not (CY or Z)}[c]
            r[h2 >> 11] = r[reg1] if take else r[reg2]
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 0x7FF) == 0x220:                         # mul
            p = s32(r[reg2]) * s32(r[reg1])
            r[reg2] = s32(p)
            if h2 >> 11:
                r[h2 >> 11] = s32(p >> 32)
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 1) and reg2:                             # ld.hu
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            r[reg2] = ld((r[reg1] + disp) & 0xFFFFFFFF, 2)
            pc += 4
            continue
        if op6 == 0x39:                                                    # ld.h / ld.w
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            a = (r[reg1] + disp) & 0xFFFFFFFF
            if h2 & 1:
                r[reg2] = s32(ld(a, 4))
            else:
                v = ld(a, 2)
                r[reg2] = v - 0x10000 if v & 0x8000 else v
            pc += 4
            continue
        raise RuntimeError(f"undecoded halfword {h1:04x} at {pc:#x}")
    raise RuntimeError("no exit")


# --------------------------------------------------------------------------------------------- the reference
def cave_ref(pol, tbl, sp, r26, cells, ramp):
    """the cave as E2Lane computes it (scalar re-statement of e2_lane.E2Lane's ordered decision).
    returns (r16_out, exit_pc, r6_on_freeze_or_leak, r26_out)."""
    G = C.cave_G(cells["6a5e"] & 0xFFFF, tbl)
    E = s32((sp << 2) - r26)
    ab = cells["6abe"]
    op = ab if ((ab + 13000) & 0xFFFFFFFF) <= 26000 else 0
    Ep = s32(E * G) >> 8
    if pol.get("nopol"):
        return Ep, RET, None, op
    if pol.get("cam") and cells.get("r25", 1) == 0:
        return 0, FRZ_RET, s32(-(cells["6dd0"] >> 6)), 0
    atq = cells["4f68"] & 0xFFFF
    leak = pol.get("leak")
    leak_hard = pol.get("leak_hard", bool(leak) and not pol.get("leak_opp"))
    LK = (Ep, FRZ_RET, s32(-(cells["6dd0"] >> leak)) if leak else 0, op)
    FZ = (Ep, FRZ_RET, 0, op)
    c1 = atq > pol.get("thr", 512)
    c2 = bool(pol.get("sgn")) and atq > pol["sgn"] and (cells["4f60"] ^ Ep) < 0
    order = (("opp", c2), ("hard", c1)) if pol.get("opp_first") else (("hard", c1), ("opp", c2))
    for nm, c in order:
        if c:
            if nm == "hard":
                return LK if leak_hard else FZ
            return LK if pol.get("leak_opp") else FZ
    if pol.get("arb_sh"):
        th = cells["6a00"]
        sh = pol["arb_sh"]
        if pol.get("arb_sh_lo") is not None and (cells["6a5e"] & 0xFFFF) <= pol["arb_vth"]:
            sh = pol["arb_sh_lo"]
        bound = s32((abs(th) << sh) + pol["arb_B"])
        if pol.get("arb_vcap") is not None and (cells["6a5e"] & 0xFFFF) <= pol["arb_vcap"] and bound > pol["arb_cap"]:
            bound = pol["arb_cap"]
        I_S = cells["6dd0"] >> 10
        t = I_S if Ep >= 0 else -I_S
        if t >= bound:
            return Ep, FRZ_RET, 0, op
    if pol.get("ramp", True) and (ramp & 0x8000) == 0:
        return Ep, FRZ_RET, 0, op
    return Ep, RET, None, op


CELLS = {"6a5e": (-0x6A5E, 2), "4f68": (-0x4F68, 2), "4f60": (-0x4F60, 2), "6abe": (-0x6ABE, 2),
         "6a00": (-0x6A00, 2), "6dd0": (-0x6DD0, 4)}
SCRATCH = (6, 8, 9, 13, 16, 26)


def h1(pol, tbl, code, N=40000, seed=11):
    rng = np.random.default_rng(seed)
    bad = 0
    edges = [0, 32000, 65535] + [x + d for x, _, _ in tbl if x < 0xFFFF for d in (-1, 0, 1)]
    thr = pol.get("thr", 512)
    T = pol.get("sgn", 300)
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 50 else 32767
        r26 = int(rng.integers(-65535, 65536))
        v = int(rng.integers(0, 32001)) if k % 7 else int(rng.choice(edges))
        tq = int(rng.integers(-3000, 3000)) if k % 3 else int(rng.choice([0, thr, thr + 1, -thr, -thr - 1, T, T + 1,
                                                                             -T, -T - 1, 32767, -32768]))
        ramp = int(rng.choice([0x8000, 0x8000, 0x8000, int(rng.integers(1, 0x8000))]))
        icl = 16384 << 7
        i8 = int(rng.integers(-icl * 8, icl * 8)) if k % 5 else int(rng.choice([0, 1023, 1024, -1024, -1025]))
        th = int(rng.integers(-12000, 12001)) if k % 4 else int(rng.choice([0, 1, -1, 12000, -12000]))
        if pol.get("arb_sh_lo") is not None and k % 3 == 0:
            v = int(rng.choice([pol["arb_vth"] - 1, pol["arb_vth"], pol["arb_vth"] + 1]))
        if pol.get("arb_vcap") is not None and k % 3 == 1:
            v = int(rng.choice([pol["arb_vcap"] - 1, pol["arb_vcap"], pol["arb_vcap"] + 1, 500]))
        if pol.get("arb_sh") and k % 2:       # put t right at the bound often
            shv = pol["arb_sh_lo"] if (pol.get("arb_sh_lo") is not None and v <= pol["arb_vth"]) else pol["arb_sh"]
            b = (abs(th) << shv) + pol["arb_B"]
            i8 = int(rng.choice([b, b - 1, b + 1, -b, -b - 1, -b + 1])) * 1024 + int(rng.integers(0, 1024))
        cells = {"6a5e": v, "4f68": min(abs(tq), 0xFFFF), "4f60": tq, "6abe": int(rng.choice(
            [32767, int(rng.integers(-14000, 14000)), -13001, 13000, -13000, 13001])), "6a00": th, "6dd0": i8}
        mem = {}
        for nm, (off, w) in CELLS.items():
            a = (GP + off) & 0xFFFFFFFF
            val = cells[nm] & ((1 << (8 * w)) - 1)
            for i in range(w):
                mem[a + i] = (val >> (8 * i)) & 0xFF
        for i, b_ in enumerate(code):
            mem[CAVE + i] = b_
        regs = {i: int(rng.integers(-2 ** 31, 2 ** 31)) for i in range(32)}
        regs.update({0: 0, 16: sp, 26: r26, 14: ramp, 4: s32(GP), 6: RET})
        r25 = int(rng.choice([0, 1, 1, 1])) if pol.get("cam") else int(rng.integers(-2 ** 31, 2 ** 31))
        regs[25] = r25
        cells["r25"] = r25
        pc_exit, rr, mem2 = run_bytes(code, CAVE, regs, mem, CAVE)
        r16, ex, r6, op = cave_ref(pol, tbl, sp, r26, cells, ramp)
        ok = rr[16] == r16 and pc_exit == ex and (r6 is None or rr[6] == r6) and rr[26] == op
        ok = ok and all(rr[i] == regs[i] for i in range(32) if i not in SCRATCH)
        ok = ok and mem2 == mem
        if not ok:
            bad += 1
            if bad <= 3:
                print("   MISMATCH", pol, dict(sp=sp, r26=r26, tq=tq, ramp=ramp), cells, "got", rr[16], rr[26], rr[6],
                      hex(pc_exit), "want", r16, op, r6, hex(ex))
    return bad


FORMS = [  # (address in V295, the form), each also decoded by Ghidra dry-run (design page sec. 6)
    (0x29D94, "ce 05", "bge (cond E) -> our bge"),
    (0x2904C, "ac 05", "bp (cond C, the Bcond Format III form) -> our blt (cond 6) shares the encoding layout"),
    (0x28F26, "24 7f a0 b0", "ld.h -0x4f60[gp],r15 -> our ld.h -0x4f60[gp],r9"),
    (0x29DA4, "24 57 31 92", "ld.w -0x6dd0[gp],r10 -> our ld.w -0x6dd0[gp],r13|r6"),
    (0x40AEA, "24 77 00 96", "ld.h -0x6a00[gp],r14 -> our ld.h -0x6a00[gp],r9"),
    (0x29DAE, "a3 6a", "sar 3,r13 -> our sar imm5"),
    (0x2904E, "80 39", "subr r0,r7 -> our subr r0,r9|r13|r6"),
    (0x504E2, "29 61", "xor r9,r12 (Ghidra: FUN_0005046c) -> our xor r16,r9 (Format I op 0x09)"),
    (0x1C006, "b6 05", "blt 0x1C00C (Ghidra: FUN_0001bf88) -> our blt (cond 6)"),
]


def find_xor(img):
    """a Format I xor in FUN_00028ea6..: the encoding-form control for 'xor r16,r9' (decoded by Ghidra in the page)."""
    for a in range(0x28EA6, 0x2A30E, 2):
        h = struct.unpack_from("<H", img, a)[0]
        if ((h >> 5) & 0x3F) == 0x09 and (h >> 11) != 0:
            return a, img[a:a + 2].hex(" ")
    return None


def main():
    tbl = [tuple(r) for r in R.tables()["P2"]]
    img = open(DA.IMG, "rb").read()
    O = []

    def P(s=""):
        print(s, flush=True)
        O.append(s)
    P("FORM CONTROLS (V295 bytes):")
    for a, exp, what in FORMS:
        got = img[a:a + len(bytes.fromhex(exp.replace(' ', '')))].hex(" ")
        P(f"  {a:#07x} {got:14s} {'OK ' if got == exp else 'BAD'} {what}")
    p2hex = (AL / "c2" / "rev2A" / "c2_cave_P2.hex").read_text().strip()
    code, labels, lines = assemble(IMPL["P2"], tbl)
    P(f"CONTROL A: builder('P2') == c2_cave_P2.hex: {code.hex(' ') == p2hex}  ({len(code)} B)")
    rng = np.random.default_rng(3)
    nbad = 0
    for k in range(20000):
        regs = {i: int(rng.integers(-2 ** 31, 2 ** 31)) for i in range(32)}
        regs.update({0: 0, 16: int(rng.integers(-16384, 16385)), 26: int(rng.integers(-65535, 65536)),
                     14: int(rng.choice([0x8000, int(rng.integers(0, 0x8000))])), 4: s32(GP), 6: RET})
        mem = {}
        for nm, (off, w) in CELLS.items():
            val = int(rng.integers(0, 1 << (8 * w)))
            for i in range(w):
                mem[(GP + off + i) & 0xFFFFFFFF] = (val >> (8 * i)) & 0xFF
        for i, b_ in enumerate(code):
            mem[CAVE + i] = b_
        a = run_bytes(code, CAVE, regs, dict(mem), CAVE)
        b = DA.run_bytes(code, CAVE, regs, dict(mem), CAVE)
        nbad += not (a[0] == b[0] and all(a[1][i] == b[1][i] for i in range(32)))
    P(f"CONTROL B: this interpreter == ds_asm.run_bytes on P2's bytes, 20000 random inputs: {nbad} differences")
    summ = {}
    for cid, pol in IMPL.items():
        code, labels, lines = assemble(pol, tbl)
        ncode = labels["TBL"] - CAVE
        P("=" * 118)
        P(f"{cid}: {pol}: cave {len(code)} B = {ncode} code + {len(code) - ncode} table; vs P2 {len(code) - 156:+d} B")
        for pc, lab, ins, bs, com in lines:
            if ins[0] == "half" and lab != "TBL":
                continue
            P(f"  {pc:#07x} {lab:6s} {bs:18s} {str(ins):42s} {com}")
        nb = h1(pol, tbl, code)
        P(f"  H1: bytes executed vs cave_ref (E2Lane's ordered decision), 40000 inputs incl. sign/threshold/bound edges: "
          f"{nb} mismatches; scratch {SCRATCH}, no RAM written")
        (HERE / f"e2_cave_{cid}.hex").write_text(code.hex(" "))
        summ[cid] = dict(cave=len(code), code=ncode, h1=nb)
    (HERE / "e2_asm_out.txt").write_text("\n".join(O) + "\n", encoding="utf-8")
    (HERE / "e2_asm_summary.json").write_text(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
