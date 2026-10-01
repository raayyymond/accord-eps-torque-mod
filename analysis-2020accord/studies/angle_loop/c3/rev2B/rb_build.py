# -*- coding: utf-8 -*-
r"""rb_build.py -- assemble the C3 rev2-B caves and H1-check them.  ANALYSIS ONLY: writes only c3b_cave_*.hex here.

Design C3B (rev2-B) = C3's A3 integral policy + THREE resolutions:
  * GB table (G >= 512 everywhere): resolves N2 (one-sided I quantum).                 [table DATA, 0 code bytes]
  * opposing-hand freeze (sgn 300): resolves N1 (outward light-hand lurch).            [+~16 cave bytes]
  * op-invalid -> skip the lane (jr 0x2a164, the A2 epilogue): resolves F3 / H-rate.   [+2 cave bytes, FLIGHT cave]
  * Ki 56 -> 40 (cal 0xC63E6): resolves F1 instability (0 exact rho>=1) and keeps the goal (real-curve hold, tracking).

Two caves per impl:
  c3b_cave_<id>_score.hex -- A3 + sgn300 + GB table, NO op-skip.  The op-skip is INERT in every goal scenario
                             (abe is valid), so this cave scores IDENTICALLY on the common scorers and its bytes are
                             H1-checked against e2_asm.cave_ref (which models sgn + the op validity -> op:=0).
  c3b_cave_<id>.hex       -- the FLIGHT cave: the above with the validity cmovh replaced by `bnh CONT ; jr 0x2a164`.
                             Decoded by Ghidra dry-run (rb_ghidra note); only those 6 bytes differ from _score.

usage: python rb_build.py
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AL / "panel2" / "E2-integral-most-margin"))
sys.path.insert(0, str(AL / "panel" / "D-structure"))
sys.path.insert(0, str(AL / "c1"))
import e2_asm as EA  # noqa: E402
import rb_table as T  # noqa: E402

CAVE = EA.CAVE
SKIP_TGT = 0x2A164                    # the A2/B2 skip epilogue (zeros I8 @-0x6dd0, sets sentinel @-0x6cf8, decays lag)

POL_A3S = dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096, sgn=300)

SPECS = {
    "C3B-P": dict(dop="fresh", tbl=T.GB_P),
    "C3B-F": dict(dop="held", tbl=T.GB_F),
}


def strip_fresh(entries):
    out, skip = [], 0
    for lab, ins, com in entries:
        if skip:
            skip -= 1
            continue
        if ins == ("ld_h", -0x6ABE, 4, 26):
            skip = 4
            continue
        out.append((lab, ins, com))
    return out


def assemble(pol, tbl, dop):
    entries = EA.listing(pol, [tuple(r) for r in tbl])
    if dop == "held":
        entries = strip_fresh(entries)
    # link
    labels, pc = {}, CAVE
    for lab, ins, _ in entries:
        if lab:
            labels[lab] = pc
        pc += EA.size(ins)
    out, pc = bytearray(), CAVE
    for lab, ins, _ in entries:
        for h in EA.enc(ins, pc, labels):
            out += struct.pack("<H", h)
        pc += EA.size(ins)
    return bytes(out), labels


def add_opskip(code, labels):
    """replace the validity `cmovh r0,r26,r26` (ds_asm enc: f0 d7 36 d3 ... actually 20 d7 36 d3?) with
    `bnh CONT ; jr 0x2a164`.  The cmovh is the 4-byte word right after `cmp r13,r8` in the fresh-operand block.
    Returns the flight bytes (code len + 2)."""
    cmovh = b"".join(struct.pack("<H", h) for h in EA.enc(("cmovh", 0, 26, 26), 0, {}))
    i = code.find(cmovh)
    assert i >= 0 and code.count(cmovh) == 1, "cmovh not uniquely found"
    pc_at = CAVE + i
    # bnh CONT (CONT = pc_at + 2 (bnh) + 4 (jr) = pc_at+6)  ; jr 0x2a164
    cont = pc_at + 6
    bnh = EA.enc(("bnh", "CONT"), pc_at, {"CONT": cont})
    jr = EA.enc(("jr", SKIP_TGT), pc_at + 2, {})
    ins_bytes = b"".join(struct.pack("<H", h) for h in bnh) + b"".join(struct.pack("<H", h) for h in jr)
    assert len(ins_bytes) == 6
    return code[:i] + ins_bytes + code[i + 4:]


def h1_score(pol, tbl, code):
    """e2_asm's H1: the scoring-cave bytes executed vs cave_ref (models sgn + op validity)."""
    return EA.h1(pol, [tuple(r) for r in tbl], code, N=30000)


def main():
    log = []

    def P(s=""):
        print(s, flush=True)
        log.append(s)
    P("C3 rev2-B caves (A3 + opposing-freeze sgn300 + GB table; flight adds op-skip jr 0x2a164)")
    for cid, sp in SPECS.items():
        code, labels = assemble(POL_A3S, sp["tbl"], sp["dop"])
        ncode = labels["TBL"] - CAVE
        (HERE / f"c3b_cave_{cid}_score.hex").write_text(code.hex(" ") + "\n")
        nb = h1_score(POL_A3S, sp["tbl"], code)
        P(f"{cid}: score cave {len(code)} B ({ncode} code + {len(code)-ncode} tbl) sha {hashlib.sha256(code).hexdigest()[:12]}"
          f"  H1 {nb} mismatches / 30000")
        if sp["dop"] == "fresh":
            flight = add_opskip(code, labels)
            (HERE / f"c3b_cave_{cid}.hex").write_text(flight.hex(" ") + "\n")
            i = code.find(b"".join(struct.pack("<H", h) for h in EA.enc(("cmovh", 0, 26, 26), 0, {})))
            P(f"      flight cave {len(flight)} B sha {hashlib.sha256(flight).hexdigest()[:12]}  (op-skip +"
              f"{len(flight)-len(code)} B at cave offset {i:#x}: cmovh -> bnh CONT ; jr 0x2a164)")
        else:
            (HERE / f"c3b_cave_{cid}.hex").write_text(code.hex(" ") + "\n")
            P("      flight cave = score cave (held D: no abe read; F3 rate-invalid PI-only declared, see design)")
        P(f"      labels: FRZ {labels.get('FRZ'):#x} DONE {labels.get('DONE'):#x} TBL {labels['TBL']:#x}")
    (HERE.parents[3] / "_scratch" / "angle_loop" / "c3-rev2B" / "rb_build_out.txt").write_text("\n".join(log))


if __name__ == "__main__":
    main()
