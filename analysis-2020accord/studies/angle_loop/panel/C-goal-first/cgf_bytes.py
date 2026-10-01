# -*- coding: utf-8 -*-
r"""cgf_bytes.py -- the exact in-place edit set for Designer-C (CGF-1 / CGF-2), verified against the V294 plain image in
Python (Ghidra-independent byte work; the encoder is positive-controlled on instructions that already exist in the image,
and each pre-edit byte is asserted).  ANALYSIS ONLY: reads the image, writes nothing to any car, builds no .rwd.

The V294 program is code-identical to V295 except cal 0xC63EA and its CRC (STATE), so the CODE edit sites read identically
on both; cals are read from V295 for the base.  gp = 0xFEDF8000, tp = 0xBF000.
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
FW = Path(os.environ["ACCORD_FIRMWARE_ROOT"]) / "analysis-2020accord"
V294 = FW / ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-"
             "R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
for _p in (str(HERE), str(AL / "c1")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def enc_ldh_gp(reg2, disp):
    assert disp % 2 == 0
    return struct.pack("<HH", (reg2 << 11) | (0x39 << 5) | 4, disp & 0xFFFF)


def enc_fmt1(op6, reg1, reg2):
    return struct.pack("<H", (reg2 << 11) | (op6 << 5) | reg1)


# in-place edits.  address: (old bytes hex, new bytes, decode)
EDITS = {
    0x28F4C: ("243faa95", enc_ldh_gp(7, -0x6a00), "ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7   (x := theta)"),
    0x28FA4: ("89d1", enc_fmt1(0x0E, 9, 26), "subr r9,r26 -> add r9,r26   (r26 = s_old + s_new)"),
    0x29A50: ("e2470000", bytes.fromhex("e0df3443"), "setfe r8 -> cmovne r0,r27,r8   (B2)"),
    0x29A56: ("da05", bytes.fromhex("b205"), "bne 0x29A60 -> be 0x29A5C   (A2)"),
    0x29D6A: ("0880ed80", enc_ldh_gp(16, -0x69ae), "mov r8,r16;mulh r13,r16 -> ld.h -0x69ae[gp],r16   (sp := gp-0x69ae)"),
    0x29D76: ("c282ba81", bytes.fromhex("89378aae"), "shl 2,r16;sub r26,r16 -> jarl 0xC4C00,r6   (the hook)"),
    # E5-fresh: ONE 4-byte edit (0x29EDE stays STOCK c700 zxh r7 = +Kd).  Reads the FRESH rate gp-0x6abe for D.
    0x29EE0: ("1040bb41", enc_ldh_gp(8, -0x6abe), "mov r16,r8;sub r27,r8 -> ld.h -0x6abe[gp],r8   (D on FRESH rate, +Kd)"),
    # V1 version marker handled separately (data, needs .rwd re-header)
    0x1310D: ("30", bytes.fromhex("41"), "F181 string '39990-TVA,A160' -> '...,A16A'   (fork interlock)"),
}


def verify():
    img = V294.read_bytes()
    print(f"image {V294.name}\n  size {len(img)}  (V294; code-identical to V295 except 0xC63EA)")
    # encoder positive controls against instructions that already exist
    assert img[0x29032:0x29036] == enc_ldh_gp(13, -0x69ae), "control ld.h -0x69ae[gp],r13"
    assert img[0x28F4C:0x28F50] == enc_ldh_gp(7, -0x6a56), "control ld.h -0x6a56[gp],r7"
    assert img[0x29EDE:0x29EE0] == bytes.fromhex("c700"), "0x29EDE is stock zxh r7 (c7 00) -- kept stock for +Kd"
    print("  encoder positive controls OK (ld.h gp forms reproduce existing image instructions)")
    print("  0x29EDE = c7 00 (zxh r7, STOCK) -- Designer-C keeps it (no subr): +Kd for the fresh-rate D")
    print("\nin-place edits (old asserted against the image):")
    nbytes = 0
    for a in sorted(EDITS):
        old_hex, new, dec = EDITS[a]
        old = bytes.fromhex(old_hex)
        got = img[a:a + len(old)]
        assert got == old, f"{a:#07x}: image has {got.hex()}, expected {old_hex}"
        assert len(new) == len(old), f"{a:#07x}: length change"
        nbytes += len(new)
        print(f"  {a:#08x}  {old.hex():>8} -> {new.hex():<8}  {dec}")
    # A2 is bne 0x29A60 (cond 0xA) -> be 0x29A5C (cond 0x2); both condition AND target change (C1 rev2's documented edit)
    assert EDITS[0x29A56][1] == bytes.fromhex("b205")
    print(f"\n  total in-place code+data bytes rewritten: {nbytes} (same 7 code sites as C1 rev2 + V1; E5 is 1 site not 2)")
    print("\n  CGF-1 cave: byte-identical to C1 rev2's 96-byte cave CODE at 0xC4C00 (the G walk + E' + I freeze); only the")
    print("  42-byte TABLE differs (cgf_design.table()).  CGF-2 adds the FF block (see the design page listing).")
    # show the CGF table bytes
    import cgf_design as D
    tb = b"".join(struct.pack("<HHh", X, G, S) for (X, G, S) in D.table())
    print(f"\n  CGF table bytes ({len(tb)} B, 7 rows incl sentinel):")
    for (X, G, S) in D.table():
        print(f"    X {X:5d} ({X/230.4:5.2f} m/s)  G {G:5d}  S {S:6d}  Kp_eff {112*G/256:6.1f}")


if __name__ == "__main__":
    verify()
