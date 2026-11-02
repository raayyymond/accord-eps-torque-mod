# -*- coding: utf-8 -*-
# KIT COPY (2026-11-01, T6) of scratchpad t4/cave_listing.py (agent cave-asm-2, T4c); changed only the import path / the A340 bytes source
# (re-assembled from the listing instead of read from cave_a340.hex).  Called by build_v300_a340.py.
"""cave_listing.py -- the V299/V300 rev-2 angle-loop cave as ONE parametric listing, instruction-for-instruction
the Ghidra listing a160_ref/ghidra_listing_v299_cave.json (77 insns, 0xC4C00-0xC4CD9) + the 7-row G table.
MODE 'A160' must reproduce V300's cave byte for byte (sha e22193b9...); MODE 'A340' is the re-registered port.
Encoder = e2_asm.enc / e2_asm.size (read-only import; the studies files are NOT edited).  ANALYSIS ONLY."""
from __future__ import annotations
import hashlib, struct, sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KIT / "analysis-2020accord/studies/angle_loop/panel2/E2-integral-most-margin"))
import e2_asm as EA  # noqa: E402

CAVE = 0xC4C00
V300_TBL = [(714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570),
            (4032, 1068, 2118), (6198, 2188, 0), (65535, 2188, 0)]


def half_up(x):            # round-half-up of x/2 (toward +inf on exact halves), pinned per main
    return (x + 1) >> 1     # Python >> floors: (x+1)//2 == floor(x/2 + 1/2)


A340_TBL = [(X, half_up(G), half_up(S)) for X, G, S in V300_TBL]

MODES = {
    "A160": dict(E=16, P=9, V=8, K=13, LINK=6, FO=6, RET=0x29D7A, FRZ=0x29D7E, SKIP=0x2A164, CAMSAR=6,
                 RATE=-0x6ABE, SPD=-0x6A5E, HAND=-0x4F68, ANG=-0x6A00, ISTATE=-0x6DD0, TBL=V300_TBL),
    "A340": dict(E=9, P=16, V=10, K=13, LINK=7, FO=13, RET=0x2A344, FRZ=0x2A348, SKIP=0x2A596, CAMSAR=7,
                 RATE=-0x6A8E, SPD=-0x6A2E, HAND=-0x4EC0, ANG=-0x69C8, ISTATE=-0x6DA0, TBL=A340_TBL),
}
EXP_A160_SHA = "e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608"


def listing(m):
    E, P, V, K, LK, FO = m["E"], m["P"], m["V"], m["K"], m["LINK"], m["FO"]
    L = []

    def A(lab, ins, com=""):
        L.append((lab, ins, com))
    A("C", ("shl_i", 2, E), "displaced hook insn 1: 4*sp (stock shl 5)")
    A(None, ("sub", 26, E), "displaced hook insn 2: E = 4*sp - r26")
    A(None, ("ld_h", m["RATE"], 4, 26), "op = fresh 1 kHz rate EMA             [D OPERAND]")
    A(None, ("addi", 13000, 26, V), "Honda validity form: op + 13000")
    A(None, ("movea", 26000, 0, K), "")
    A(None, ("cmp", K, V), "")
    A(None, ("bnh", "CONT"), "rate valid: continue                  [op-skip]")
    A(None, ("jr", m["SKIP"]), "rate INVALID: Honda skip epilogue")
    A("CONT", ("ld_hu", m["SPD"], 4, V), "v = vehicle speed                     [G(v)]")
    A(None, ("mov_i32", "TBL", P), "P -> table")
    A(None, ("ld_hu", 0, P, K), "X0")
    A(None, ("cmp", K, V), "")
    A(None, ("bh", "L1"), "v > X0: walk")
    A(None, ("ld_hu", 2, P, V), "G = G0")
    A(None, ("br", "APPLY"), "")
    A("L1", ("ld_hu", 6, P, K), "X(i+1)")
    A(None, ("cmp", K, V), "")
    A(None, ("bnh", "SEG"), "v <= X(i+1): segment i")
    A(None, ("addi", 6, P, P), "next row")
    A(None, ("br", "L1"), "")
    A("SEG", ("ld_hu", 0, P, K), "X(i)")
    A(None, ("sub", K, V), "dv = v - X(i)")
    A(None, ("ld_h", 4, P, K), "S(i) Q12 signed")
    A(None, ("mul", K, V, 0), "dv*S (low word)")
    A(None, ("sar_i", 12, V), ">>12")
    A(None, ("ld_hu", 2, P, K), "G(i)")
    A(None, ("add", K, V), "G = G(i) + (dv*S >> 12)")
    A("APPLY", ("mul", V, E, 0), "E*G (low word)                        [SPEED GAIN]")
    A(None, ("sar_i", 8, E), "E' = (E*G) >> 8")
    A(None, ("cmp", 0, 25), "r25 = camera-field flag (read only)   [CAMERA GATE]")
    A(None, ("be", "CAM"), "camera frame: go inert")
    A(None, ("ld_hu", m["HAND"], 4, V), "|driver torque|                       [HARD FREEZE]")
    A(None, ("movea", 1229, 0, K), "THR = 1229")
    A(None, ("cmp", K, V), "")
    A(None, ("bh", "FRZ"), "|tq| > 1229 unsigned: freeze")
    A(None, ("ld_h", m["ANG"], 4, P), "th = held angle                       [ASYMMETRIC BOUND]")
    A(None, ("cmp", 0, E), "")
    A(None, ("bge", "A1"), "")
    A(None, ("subr", 0, P), "E'<0: th = -th")
    A("A1", ("cmp", 0, P), "")
    A(None, ("bge", "A1B"), "")
    A(None, ("mov_i5", 0, P), "th opposite to E': 0")
    A("A1B", ("ld_hu", m["SPD"], 4, V), "v                                     [TWO-LEVEL CAP]")
    A(None, ("movea", 2880, 0, K), "VNOCAP 2880")
    A(None, ("cmp", K, V), "")
    A(None, ("bh", "AH"), "v > 2880: high slope, uncapped")
    A(None, ("shl_i", 4, P), "th << 4")
    A(None, ("addi", 1250, P, P), "+ B 1250")
    A(None, ("movea", 1382, 0, K), "VCAP 1382")
    A(None, ("cmp", K, V), "")
    A(None, ("bh", "C6"), "")
    A(None, ("movea", 4096, 0, K), "CAPLO 4096 (v <= 1382)")
    A(None, ("br", "CC"), "")
    A("C6", ("movea", 6144, 0, K), "CAPHI 6144 (1382 < v <= 2880)")
    A("CC", ("cmp", K, P), "")
    A(None, ("cmovh", K, P, P), "bound = min(bound, cap)")
    A(None, ("br", "IB"), "")
    A("AH", ("shl_i", 6, P), "th << 6")
    A(None, ("addi", 1250, P, P), "+ B 1250")
    A("IB", ("ld_w", m["ISTATE"], 4, K), "I8 = Honda I state (read only)")
    A(None, ("sar_i", 10, K), "I8 >> 10")
    A(None, ("cmp", 0, E), "")
    A(None, ("bge", "A2"), "")
    A(None, ("subr", 0, K), "t = sgn(E') * (I8>>10)")
    A("A2", ("cmp", P, K), "t - bound")
    A(None, ("bge", "FRZ"), "winding past the bound: freeze")
    A(None, ("andi", 0x8000, 14, K), "r14 = ramp                            [RAMP-IN]")
    A(None, ("bne", "DONE"), "ramp full: integrate")
    A("FRZ", ("mov_i5", 0, FO), "freeze-out := 0 -> I unchanged")
    A(None, ("jr", m["FRZ"]), "freeze return")
    A("CAM", ("mov_i5", 0, E), "E' := 0 -> P = 0                      [CAM TAIL]")
    A(None, ("mov_i5", 0, 26), "op := 0 -> D = 0")
    A(None, ("ld_w", m["ISTATE"], 4, FO), "I8")
    A(None, ("sar_i", m["CAMSAR"], FO), f"I8 >> {m['CAMSAR']}")
    A(None, ("subr", 0, FO), "freeze-out = -(I8 >> s): I decays")
    A(None, ("jr", m["FRZ"]), "")
    A("DONE", ("jmp", LK), "normal return via the link")
    first = True
    for X, G, S in m["TBL"]:
        for h, nm in ((X, "X"), (G, "G"), (S & 0xFFFF, "S")):
            A("TBL" if first else None, ("half", h), f"table {nm}={h if nm != 'S' else S}")
            first = False
    return L


def assemble(m, base=CAVE):
    L = listing(m)
    labels, pc = {}, base
    for lab, ins, _ in L:
        if lab:
            labels[lab] = pc
        pc += EA.size(ins)
    out, lines, pc = bytearray(), [], base
    for lab, ins, com in L:
        bs = b"".join(struct.pack("<H", h) for h in EA.enc(ins, pc, labels))
        assert len(bs) == EA.size(ins), ins
        out += bs
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        pc += len(bs)
    return bytes(out), labels, lines


def sha(b):
    return hashlib.sha256(b).hexdigest()
