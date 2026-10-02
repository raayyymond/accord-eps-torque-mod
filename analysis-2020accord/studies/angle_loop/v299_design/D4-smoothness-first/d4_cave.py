# -*- coding: utf-8 -*-
r"""d4_cave.py -- DESIGNER D4, implementation (b): the V299-D4b flight cave as a LISTING -> bytes (two-pass relink),
EXECUTED by a V850E2 interpreter against the integer-exact mirror (H1), with the CONTROL that the unmodified listing
reproduces V298's flight cave byte for byte.  ANALYSIS ONLY: no image is written, nothing is flashed.

The edit (vs V298's flight cave, sha ef1861e10421, 260 B at 0xC4C00):
  [LP]   inserted before the camera gate: the ONE new state word h = gp-0x6a32 (s16), engage-initialised on Honda's
         first-tick sentinel (gp-0x6cf8 == 0x7FFFFFFF), h += (hs - h) >> 5 (tau 32 ticks = 32 ms at 1 kHz).
  [HAND] V298's 28-byte hand block (ld.hu -0x4f68 ; hard |tq| > 512 ; opposing |tq| > 300 & sign(tq) != sign(E'))
         replaced by: hard |h| > 512 ; opposing |h| > 300 & sign(h) != sign(E') UNLESS the wheel already moves toward the
         setpoint (sign(gp-0x6abe) != sign(E') and |gp-0x6abe| > 10)  -- the MOTION GATE.
  Everything else (head, op-skip, G walk, E', camera gate, A3 bound, ramp test, FRZ / CAM / DONE exits, the GB-P table)
  is V298's listing, relinked.
  Outside the cave (in-place, listed in the design page): 0x29D72 st.h r16,-0x6a32[gp] -> nop ; nop (the dead
  setpoint publish that would overwrite h), 0xC4B92 ld.h -0x6b4c -> ld.h -0x6a32 (0x14A b4.7 := sign(h)), 0x1310D
  'A' -> 'B' (A16B), CRC.
usage: python d4_cave.py       (< 10 s; prints the listing, the sha, the control and H1)
"""
from __future__ import annotations

import hashlib
import struct
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
for q in (AL / "panel2" / "E2-integral-most-margin", AL / "panel" / "D-structure", AL / "c3" / "rev2B", AL / "c1"):
    sys.path.insert(0, str(q))
import e2_asm as EA  # noqa: E402
import rb_table as TB  # noqa: E402

OUT = KIT / "_scratch" / "v299_D4"
CAVE = 0xC4C00
SKIP_TGT, FRZ_RET, RET = 0x2A164, 0x29D7E, 0x29D7A
POL_A3S_CAM = dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096, sgn=300, cam=True)
V298_FLIGHT_SHA = "ef1861e10421b0645b27e9ff8605a93b245f16fe2a350c65f0a067084497303a"
IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
H_RAM, SENT_RAM = -0x6A32, -0x6CF8
LP_SH, H_HARD, H_OPP, MG = 5, 512, 300, 10


def u16(x):
    return x & 0xFFFF


def enc(ins, pc, labels):
    if ins[0] == "st_h":                      # st.h reg2, disp16[reg1]   ins = ("st_h", reg2, disp, reg1)
        assert ins[2] % 2 == 0
        return [u16((ins[1] << 11) | (0x3B << 5) | ins[3]), u16(ins[2] & 0xFFFE)]
    return EA.enc(ins, pc, labels)


def size(ins):
    return 4 if ins[0] == "st_h" else EA.size(ins)


def inject_opskip(entries):                   # = build_v298_tva.reassemble_caves.inject_opskip
    out, i, n = [], 0, len(entries)
    while i < n:
        lab, ins, com = entries[i]
        if ins == ("cmovh", 0, 26, 26):
            out.append((lab, ("bnh", "CONT"), "rate valid: continue  [op-skip]"))
            out.append((None, ("jr", SKIP_TGT), "rate INVALID: jr 0x2A164 (Honda A2/B2 epilogue)  [F3]"))
            out.append(("CONT", entries[i + 1][1], entries[i + 1][2]))
            i += 2
            continue
        out.append((lab, ins, com))
        i += 1
    return out


LP_BLOCK = [
    (None, ("ld_w", SENT_RAM, 4, 8), "r8 = gp-0x6cf8: Honda's first-tick sentinel word         [D4 LP: engage init]"),
    (None, ("mov_i32", 0x7FFFFFFF, 13), "r13 = 0x7FFFFFFF"),
    (None, ("cmp", 13, 8), "Z iff this is the first PID tick after a skip"),
    (None, ("ld_h", H_RAM, 4, 9), "r9 = h_prev = gp-0x6a32 (the D4 state word, s16)"),
    (None, ("cmovz", 0, 9, 9), "h_prev := 0 on the sentinel tick (ld does not touch the flags)"),
    (None, ("ld_h", -0x4F60, 4, 8), "r8 = hs = gp-0x4f60 (signed hand word)"),
    (None, ("sub", 9, 8), "r8 = hs - h_prev"),
    (None, ("sar_i", LP_SH, 8), "(hs - h_prev) >> 5"),
    (None, ("add", 8, 9), "r9 = h = h_prev + ((hs - h_prev) >> 5)        [1st-order LP, tau 32 ms]"),
    (None, ("st_h", 9, H_RAM, 4), "gp-0x6a32 := h"),
]
HAND_BLOCK = [
    (None, ("mov", 9, 8), "r8 = h                                         [D4 HAND: hard]"),
    (None, ("cmp", 0, 8), ""),
    (None, ("bge", "HA"), ""),
    (None, ("subr", 0, 8), "r8 = |h|"),
    ("HA", ("movea", H_HARD, 0, 13), "512"),
    (None, ("cmp", 13, 8), ""),
    (None, ("bh", "FRZ"), "|h| > 512 (unsigned): freeze"),
    (None, ("movea", H_OPP, 0, 13), "300                                            [D4 HAND: opposing]"),
    (None, ("cmp", 13, 8), ""),
    (None, ("bnh", "N2"), "|h| <= 300: no hand"),
    (None, ("xor", 16, 9), "sign(h) ^ sign(E')"),
    (None, ("bge", "N2"), "same sign: not opposing"),
    (None, ("mov", 26, 9), "r9 = op = gp-0x6abe (validated at the cave head) [D4 MOTION GATE]"),
    (None, ("xor", 16, 9), "sign(abe) ^ sign(E')   (abe = -4.712 w_motor)"),
    (None, ("bge", "FRZ"), "same sign: the wheel is NOT moving toward the setpoint -> freeze"),
    (None, ("addi", MG, 26, 9), "|abe| <= 10  <=>  (abe + 10) <= 20 unsigned"),
    (None, ("movea", 2 * MG, 0, 13), ""),
    (None, ("cmp", 13, 9), ""),
    (None, ("bnh", "FRZ"), "the wheel is ~static: freeze; else it moves toward the setpoint: no freeze"),
]


def listing_v298():
    return inject_opskip(EA.listing(POL_A3S_CAM, [tuple(r) for r in TB.GB_P]))


def listing_d4b():
    L = listing_v298()
    out = []
    i = 0
    while i < len(L):
        lab, ins, com = L[i]
        if ins == ("cmp", 0, 25):                               # the camera gate: insert the LP block before it
            out += [(lab if k == 0 else None, e[1], e[2]) for k, e in enumerate(LP_BLOCK)]
            out.append((None, ins, com))
            i += 1
            continue
        if ins == ("ld_hu", -0x4F68, 4, 8):                     # V298's hand block: replace up to the N2 label
            j = i
            while L[j][0] != "N2":
                j += 1
            out += [(e[0], e[1], e[2]) for e in HAND_BLOCK]
            out.append(("N2", L[j][1], L[j][2]))
            i = j + 1
            continue
        out.append((lab, ins, com))
        i += 1
    return out


def asm(entries, base=CAVE):
    labels, pc = {}, base
    for lab, ins, _ in entries:
        if lab:
            labels[lab] = pc
        pc += size(ins)
    out, lines, pc = bytearray(), [], base
    for lab, ins, com in entries:
        bs = b"".join(struct.pack("<H", h) for h in enc(ins, pc, labels))
        assert len(bs) == size(ins)
        out += bs
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        pc += len(bs)
    return bytes(out), labels, lines


# ------------------------------------------------------------------------------------------------- the interpreter
def run(code, base, regs, mem, start, stop_at=(RET, FRZ_RET, SKIP_TGT), max_steps=800):
    """e2_asm.run_bytes extended with st.h (op 0x3B, hw2 bit0 = 0), cmov Z/H, and the op-skip exit."""
    r = dict(regs)
    r[0] = 0
    pc = start
    Z = S = OV = CY = False
    s32 = EA.s32

    def get(a):
        return code[a - base] | (code[a - base + 1] << 8)

    def ld(a, n):
        return sum(mem.get((a + i) & 0xFFFFFFFF, 0) << (8 * i) for i in range(n))
    for _ in range(max_steps):
        if pc in stop_at:
            return pc, r, mem
        h1 = get(pc)
        op6 = (h1 >> 5) & 0x3F
        reg1, reg2 = h1 & 0x1F, h1 >> 11
        if (op6 >> 2) == 0b1011:
            cond = h1 & 0xF
            d = ((h1 >> 11) << 4) | (((h1 >> 4) & 7) << 1)
            d = d - 512 if d & 0x100 else d
            take = {0x2: Z, 0xA: not Z, 0xB: not (CY or Z), 0x3: (CY or Z), 0x5: True,
                    0xE: not (S ^ OV), 0x6: (S ^ OV)}[cond]
            pc = pc + d if take else pc + 2
            continue
        if op6 in (0x3C, 0x3D) and not (get(pc + 2) & 1):
            h2 = get(pc + 2)
            d = ((h1 & 0x3F) << 16) | (h2 & 0xFFFE)
            d = d - (1 << 22) if d & (1 << 21) else d
            if reg2:
                r[reg2] = pc + 4
            pc = pc + d
            continue
        if h1 & 0xFFE0 == 0x0060:
            pc = r[reg1] & 0xFFFFFFFF
            continue
        if h1 & 0xFFE0 == 0x0620:
            r[reg1] = s32(get(pc + 2) | (get(pc + 4) << 16))
            pc += 6
            continue
        if op6 == 0x00:
            r[reg2] = r[reg1]
            pc += 2
            continue
        if op6 == 0x09:
            r[reg2] = s32(r[reg2] ^ r[reg1])
            Z, S, OV = r[reg2] == 0, r[reg2] < 0, False
            pc += 2
            continue
        if op6 in (0x16, 0x15, 0x10, 0x12):
            imm = h1 & 0x1F
            if op6 == 0x16:
                res, OV = s32(r[reg2] << imm), False
            elif op6 == 0x15:
                res, OV = s32(r[reg2]) >> imm, False
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
        if op6 in (0x0C, 0x0D, 0x0E, 0x0F):
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
        if op6 in (0x31, 0x30, 0x36):
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
        if op6 == 0x3F and ((h2 >> 5) & 0x3F) == 0x19 and not (h2 & 1):
            c = (h2 >> 1) & 0xF
            take = {0x2: Z, 0xB: not (CY or Z)}[c]
            r[h2 >> 11] = r[reg1] if take else r[reg2]
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 0x7FF) == 0x220:
            p = s32(r[reg2]) * s32(r[reg1])
            r[reg2] = s32(p)
            if h2 >> 11:
                r[h2 >> 11] = s32(p >> 32)
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 1) and reg2:
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            r[reg2] = ld((r[reg1] + disp) & 0xFFFFFFFF, 2)
            pc += 4
            continue
        if op6 == 0x39:
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            a = (r[reg1] + disp) & 0xFFFFFFFF
            if h2 & 1:
                r[reg2] = s32(ld(a, 4))
            else:
                v = ld(a, 2)
                r[reg2] = v - 0x10000 if v & 0x8000 else v
            pc += 4
            continue
        if op6 == 0x3B:                                                     # st.h / st.w
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            a = (r[reg1] + disp) & 0xFFFFFFFF
            n = 4 if h2 & 1 else 2
            for k in range(n):
                mem[(a + k) & 0xFFFFFFFF] = (r[reg2] >> (8 * k)) & 0xFF
            pc += 4
            continue
        raise RuntimeError(f"undecoded halfword {h1:04x} at {pc:#x}")
    raise RuntimeError("no exit")


# ------------------------------------------------------------------------------------------------- the mirror
def s32(x):
    return EA.s32(x)


def s16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def d4b_ref(sp, r26, c, ramp, r25):
    """THE INTEGER-EXACT MIRROR of the D4b cave (the function the design page prints).  -> (exit, r16, r6, r26, h)."""
    G = EA.C.cave_G(c["6a5e"] & 0xFFFF, [tuple(x) for x in TB.GB_P])
    E = s32((sp << 2) - r26)
    ab = c["6abe"]
    if ((ab + 13000) & 0xFFFFFFFF) > 26000:
        return SKIP_TGT, None, None, None, c["6a32"]                    # op-skip: no state update
    op = ab
    Ep = s32(E * G) >> 8
    h_prev = 0 if c["6cf8"] == 0x7FFFFFFF else c["6a32"]                # [LP] engage init
    h = s32(h_prev + (s32(c["4f60"] - h_prev) >> LP_SH))                # [LP] h += (hs - h) >> 5
    h16 = s16(h)
    if r25 == 0:                                                         # camera gate (inert lane)
        return FRZ_RET, 0, s32(-(c["6dd0"] >> 6)), 0, h16
    ah = abs(h)
    if ah > H_HARD:
        return FRZ_RET, Ep, 0, op, h16                                   # [HAND] hard
    if ah > H_OPP and (h ^ Ep) < 0:                                      # [HAND] opposing ...
        toward = ((op ^ Ep) < 0) and (((op + MG) & 0xFFFFFFFF) > 2 * MG)  # ... unless moving toward the setpoint
        if not toward:
            return FRZ_RET, Ep, 0, op, h16
    th = c["6a00"]                                                       # A3 bound (V298, unchanged)
    sh = 4 if (c["6a5e"] & 0xFFFF) <= 2880 else 6
    bound = s32((abs(th) << sh) + 1250)
    if (c["6a5e"] & 0xFFFF) <= 1382 and bound > 4096:
        bound = 4096
    I_S = c["6dd0"] >> 10
    t = I_S if Ep >= 0 else -I_S
    if t >= bound:
        return FRZ_RET, Ep, 0, op, h16
    if (ramp & 0x8000) == 0:
        return FRZ_RET, Ep, 0, op, h16
    return RET, Ep, None, op, h16


GPB = 0xFEDF8000


def h1(code, N=20000, seed=17):
    rng = np.random.default_rng(seed)
    bad = 0
    ex = {}
    for k in range(N):
        sp = int(rng.integers(-16384, 16385))
        r26 = int(rng.integers(-65535, 65536))
        c = {"6a5e": int(rng.choice([0, 714, 1382, 1383, 2880, 2881, 4032, 6198, int(rng.integers(0, 12000))])),
             "4f60": int(rng.choice([0, 300, 301, -300, -301, 512, 513, -513, int(rng.integers(-3000, 3000)),
                                     int(rng.integers(-32768, 32768))])),
             "6abe": int(rng.choice([0, 10, 11, -10, -11, 13000, -13000, 13001, int(rng.integers(-200, 200)),
                                     int(rng.integers(-14000, 14000))])),
             "6a00": int(rng.integers(-4000, 4000)),
             "6dd0": int(rng.integers(-(8192 << 10), 8192 << 10)) & ~7,
             "6a32": int(rng.choice([0, 300, -300, 512, -513, int(rng.integers(-32768, 32768))])),
             "6cf8": int(rng.choice([0x7FFFFFFF, int(rng.integers(-(1 << 31), 1 << 31))]))}
        ramp = int(rng.choice([0x8000, 0x7FFF, 0]))
        r25 = int(rng.choice([1, 1, 1, 0]))
        mem = {CAVE + i: b for i, b in enumerate(code)}         # the table is read from the cave bytes
        for nm, (d, n) in {"6a5e": (-0x6A5E, 2), "4f60": (-0x4F60, 2), "6abe": (-0x6ABE, 2), "6a00": (-0x6A00, 2),
                           "6dd0": (-0x6DD0, 4), "6a32": (-0x6A32, 2), "6cf8": (-0x6CF8, 4)}.items():
            for b in range(n):
                mem[(GPB + d + b) & 0xFFFFFFFF] = (c[nm] >> (8 * b)) & 0xFF
        c["6a32"] = s16(c["6a32"])
        c["4f60"] = s16(c["4f60"])
        c["6abe"] = s16(c["6abe"])
        regs = {4: GPB, 6: RET, 14: ramp, 16: sp, 25: r25, 26: r26}
        pc, r, mem2 = run(code, CAVE, regs, mem, CAVE)
        ref = d4b_ref(sp, r26, c, ramp, r25)
        hm = mem2.get((GPB - 0x6A32) & 0xFFFFFFFF, 0) | (mem2.get((GPB - 0x6A31) & 0xFFFFFFFF, 0) << 8)
        got = (pc, None if pc == SKIP_TGT else s32(r[16]), (r[6] if pc == FRZ_RET else None),
               None if pc == SKIP_TGT else s32(r[26]), s16(hm))
        exp = (ref[0], ref[1], ref[2], ref[3], ref[4])
        if got != exp:
            bad += 1
            if bad <= 3:
                print("  MISMATCH", got, exp, c, sp, r26, ramp, r25)
        ex[pc] = ex.get(pc, 0) + 1
    return bad, ex


def main():
    v298_code, _, _ = asm(listing_v298())
    img = IMG.read_bytes()
    sha = hashlib.sha256(v298_code).hexdigest()
    print("CONTROL: the unmodified listing reassembles V298's flight cave: %d B, sha %s (frozen %s): %s ; == image bytes "
          "at 0xC4C00: %s" % (len(v298_code), sha[:12], V298_FLIGHT_SHA[:12], sha == V298_FLIGHT_SHA,
                              img[CAVE:CAVE + len(v298_code)] == v298_code))
    code, labels, lines = asm(listing_d4b())
    print("D4b cave: %d B (code %d + table 42), sha %s, end 0x%X (free region ends 0xC4FF0)"
          % (len(code), len(code) - 42, hashlib.sha256(code).hexdigest()[:12], CAVE + len(code)))
    for pc, lab, ins, bs, com in lines:
        if ins[0] == "half":
            continue
        print("  %06X %-5s %-34s %-18s %s" % (pc, lab, str(ins), bs, com))
    print("  table at 0x%X (mov imm32 r9 target)" % labels["TBL"])
    bad, ex = h1(code)
    print("H1 (D4b bytes EXECUTED by the interpreter vs the integer mirror d4b_ref, incl. the state word): "
          "%d mismatches of 20000 ; exits %s" % (bad, {hex(k): v for k, v in ex.items()}))
    (OUT / "d4b_cave.hex").write_text(code.hex(" ") + "\n")
    print("wall %.1f s" % (time.time() - T0))


if __name__ == "__main__":
    main()
