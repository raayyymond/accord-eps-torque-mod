# -*- coding: utf-8 -*-
r"""e1_bytes.py -- the BYTE ACCOUNT for each E1 implementation (the fewest-bytes axis), relative to the C2 rev2-A PRIMARY
P2 (156-byte cave, 200 B written; design doc DESIGN-ANGLE-LOOP-C2-rev2-A §1).  Every implementation shares P2's in-place
edits (E1/E2/B2/A2/E4/H/OPH/V1), P2's 6-knot G cave, and P2's cal set EXCEPT the ICL cell and the integral-policy adds.

ENCODINGS confirmed against the open V294 program (Ghidra dry-run this session):
  st.w r24,-0x6dd0[gp] = 64 c7 31 92  ->  st.w r0,-0x6dd0[gp] = 64 07 31 92   (reg2 field 24->0)
  movea 512,r0,r13     = 20 6e 00 02  ->  movea 1536,r0,r13   = 20 6e 00 06 ; movea 320,r0,r13 = 20 6e 40 01
  cmp  r13,r8          = ed 41                                                 (2 B, Format I)
  bnh  (cc 0x3)        = Format III bcond, 2 B
ANALYSIS ONLY: emits a listing and a byte count; builds no image, writes nothing outside _scratch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_lane as E1

OUT = E1.KIT / "_scratch" / "angle_loop" / "E1-integral-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)

# the firm-hand reset block inserted into the cave's FRZ path (zero gp-0x6dd0 when |tq| > FIRM; r8 already = |tq|)
RESET_BLOCK = {
    "movea FIRM,r0,r13": 4,     # 20 6e <imm16>   reset threshold (1536 = 00 06)
    "cmp r13,r8": 2,            # ed 41
    "bnh .noz": 2,              # skip the store when |tq| <= FIRM
    "st.w r0,-0x6dd0[gp]": 4,   # 64 07 31 92  zero the I8 cell (the I-clamp reads I_old = 0 -> I = clamp(0+inc))
}
RESET_B = sum(RESET_BLOCK.values())   # 12

# the bleed block (drain gp-0x6dd0 by I8>>3 while BLO < |tq| <= freeze); needs two scratch (r17,r18 free at the hook)
BLEED_BLOCK = {
    "movea BLO,r0,r13": 4,      # bleed low threshold (256)
    "cmp r13,r8": 2,
    "bnh .nobleed": 2,          # |tq| <= BLO: no bleed
    "ld.w -0x6dd0[gp],r17": 4,  # I8
    "mov r17,r18": 2,
    "sar 3,r18": 2,             # I8>>3
    "sub r18,r17": 2,           # I8 - I8>>3
    "st.w r17,-0x6dd0[gp]": 4,  # write back (I-clamp reads the drained I_old)
}
BLEED_B = sum(BLEED_BLOCK.values())   # 22  (the freeze upper bound is the existing |tq|>512 test)

IMPLS = {
    "E1-cal":    dict(icl=8192, reset=None, bleed=None, freeze=512, kp=112, extra=0,
                      note="flat ICL 8192, pure cal. +0 code bytes. Meets the goal; both lurches declared."),
    "E1-reset":  dict(icl=8192, reset=1536, bleed=None, freeze=512, kp=112, extra=RESET_B,
                      note="flat ICL 8192 + firm-hand reset. +12 cave B. PRIMARY: firm lurch bounded, light declared."),
    "E1-bleed":  dict(icl=8192, reset=1536, bleed=256, freeze=512, kp=112, extra=RESET_B + BLEED_B,
                      note="flat ICL 8192 + firm reset + light-hand bleed. +34 cave B. Bounds the light lurch (hands-off risk)."),
    "E1-freeze": dict(icl=8192, reset=1536, bleed=None, freeze=320, kp=112, extra=RESET_B,
                      note="flat ICL 8192 + reset + freeze lowered to 320. +12 cave B. DOMINATED: freeze holds I high."),
    "E1-sched":  dict(icl="table", reset=1536, bleed=None, freeze=512, kp=112, extra=RESET_B + 14 + 18,
                      note="speed-scheduled ICL (col + walk + inject @0x29DA0) + reset. +~44 B. REJECTED: fails tracking."),
    "E1-splitP": dict(icl=3072, reset=1536, bleed=None, freeze=512, kp=200, extra=RESET_B,
                      note="Kp 200 record + ICL 3072 + reset. +0 code for Kp/ICL (cals). REJECTED: GATE 2 + turn-hold."),
}

P2_CAVE = 156          # design doc §1.2
P2_WRITTEN = 200       # design doc §0.2


def main():
    lines = ["# E1 byte account (vs C2 rev2-A P2: 156-byte cave, 200 B written). ICL is a CAL (0 code bytes).",
             f"# firm reset block = {RESET_B} B {list(RESET_BLOCK)}",
             f"# light bleed block = {BLEED_B} B {list(BLEED_BLOCK)}", ""]
    lines.append(f"{'impl':10s} {'cave B':>7s} {'written':>8s} {'d vs P2':>8s} {'ICL':>6s} {'reset':>6s} "
                 f"{'bleed':>6s} {'frz':>5s} {'Kp':>4s}  note")
    rows = {}
    for k, im in IMPLS.items():
        cave = P2_CAVE + im["extra"]
        written = P2_WRITTEN + im["extra"]
        rows[k] = dict(cave_bytes=cave, written=written, delta=im["extra"])
        icl = im["icl"] if im["icl"] != "table" else "sched"
        lines.append(f"{k:10s} {cave:7d} {written:8d} {im['extra']:+8d} {str(icl):>6s} "
                     f"{str(im['reset']):>6s} {str(im['bleed']):>6s} {im['freeze']:>5d} {im['kp']:>4d}  {im['note']}")
    json.dump(rows, open(OUT / "bytes.json", "w"))
    out = "\n".join(lines)
    print(out)
    (OUT / "bytes_out.txt").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
