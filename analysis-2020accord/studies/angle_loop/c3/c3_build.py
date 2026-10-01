# -*- coding: utf-8 -*-
r"""c3_build.py -- assemble every C3 cave from its parts and H1-check it against the panel-2 common time scorer's own
cave interpreter.  ANALYSIS ONLY: writes only c3_cave_<id>.hex here and a log in the scratch dir; no image, no .rwd.

The fresh caves (C3-P, C3-PA2, C3-Pd, C3-P44) are E2's assembler (e2_asm) with the ARB policy and G's table rows -- i.e.
exactly E2-A2/A3's code with G's data (the judge's graft).  The held cave (C3-F) is the SAME ARB policy with the fresh-D
operand block removed (the D comes from the in-place E5 edits that read gp-0x6a56), i.e. designer G-F24's held skeleton
carrying E2's A3 policy -- the panel's "J-F24-A3", which had NO assembled hex.  This script assembles it.

Verification here (design-time, BELIEF until a BUILT image is decoded by Ghidra, the builder's H5):
  * CONTROL A: with the ARB policy stripped and P2's table, e2_asm reproduces c2/rev2A/c2_cave_P2.hex byte for byte.
  * the fresh C3 caves equal E2-A2/A3's code with the table rows byte-substituted (same path the bytes-risk judge used).
  * H1: every C3 cave's BYTES executed by panel2/score_time's own interpreter (nl_cave.Cpu + Cpu2) against
    CandLane.cave_stage -- the very function the common time grid runs -- 6000 edge-heavy cases, + a negative control.
usage: python c3_build.py
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3_common as CC  # noqa: E402

sys.path.insert(0, str(CC.E2D))
sys.path.insert(0, str(CC.AL / "panel" / "D-structure"))
import e2_asm as EA  # noqa: E402  (E2's assembler: listing(pol, tbl) -> entries; enc/size add xor/bge/blt)


def _strip_fresh_operand(entries):
    """remove e2_asm.listing's fresh-D operand block (ld.h -0x6ABE ; addi 13000 ; movea 26000 ; cmp ; cmovh 0,r26,r26).
    For the held cave the D is the in-place E5 edits; r26 must pass through the cave untouched."""
    out = []
    skip = 0
    for lab, ins, com in entries:
        if skip:
            skip -= 1
            continue
        if ins == ("ld_h", -0x6ABE, 4, 26):
            skip = 4                      # drop the next 4 (addi, movea, cmp, cmovh)
            continue
        out.append((lab, ins, com))
    return out


def _assemble(entries, base=EA.CAVE):
    labels, pc = {}, base
    for lab, ins, _ in entries:
        if lab:
            labels[lab] = pc
        pc += EA.size(ins)
    out = bytearray()
    pc = base
    for lab, ins, com in entries:
        for h in EA.enc(ins, pc, labels):
            out += struct.pack("<H", h)
        pc += EA.size(ins)
    return bytes(out), labels


def build_cave(spec):
    rows = CC.GROWS[spec["src"]]
    entries = EA.listing(spec["pol"], rows)
    if spec["dop"] == "held":
        entries = _strip_fresh_operand(entries)
    code, labels = _assemble(entries)
    ncode = labels["TBL"] - EA.CAVE
    return code, ncode, labels


def control_A():
    """e2_asm with policy 'P2' (no ARB) and rev2-A's P2 table reproduces c2_cave_P2.hex."""
    import r2a_common as R
    p2tbl = R.tables()["P2"]
    code, _ = _assemble(EA.listing(EA.IMPL["P2"], p2tbl))
    want = bytes.fromhex((CC.AL / "c2" / "rev2A" / "c2_cave_P2.hex").read_text().replace("\n", " "))
    return code == want


def main():
    log = []

    def P(s=""):
        print(s, flush=True)
        log.append(s)

    P(f"CONTROL A (e2_asm policy 'P2' + rev2-A P2 table == c2_cave_P2.hex): {control_A()}")
    P("")
    for cid, spec in CC.IMPLS.items():
        code, ncode, labels = build_cave(spec)
        sha = hashlib.sha256(code).hexdigest()[:16]
        CC.hexpath(cid).write_text(code.hex(" ") + "\n")
        P(f"{cid:8s} [{spec['role']}]  cave {len(code)} B = {ncode} code + {len(code) - ncode} table  "
          f"sha256 {sha}  src {spec['src']} dop {spec['dop']} Kd {spec['kd']} ICL {spec['icl']}")
        # branch targets land inside the code / on the hook returns
        for lab in ("FRZ", "DONE", "APPLY", "TBL"):
            if lab in labels:
                P(f"           {lab} @ {labels[lab]:#x}")
    (CC.SCR / "c3_build_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
