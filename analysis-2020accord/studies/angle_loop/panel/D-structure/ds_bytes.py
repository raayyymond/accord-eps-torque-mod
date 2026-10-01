# -*- coding: utf-8 -*-
"""ds_bytes.py -- every byte each D-structure candidate changes in the V295 image, applied IN MEMORY to a copy of the
V295 plain image (nothing is written to disk as an image; no .rwd; no CRC recomputed -- the CRC trailers each region
dirties are LISTED, the builder recomputes them), then a full diff over [0x13000, 0x100000) that must contain exactly the
listed bytes and nothing else.  Every pre-edit byte is asserted against V295 before it is replaced.  ANALYSIS ONLY.
usage: python ds_bytes.py   (writes ds_bytes_out.txt)"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_asm as A  # noqa: E402
import ds_gate2 as G2  # noqa: E402

IMG = A.IMG
V = open(IMG, "rb").read()
assert hashlib.sha256(V).hexdigest().startswith("5c044d65"), "not the V295 image"

# ---- in-place CODE edits (address, V295 bytes, new bytes, decode V295 -> new, loop term)
E1 = (0x28F4C, "24 3f aa 95", "24 3f 00 96", "ld.h -0x6a56[gp],r7 -> ld.h -0x6a00[gp],r7", "operand x := theta (0.1 deg)")
E1F = (0x28F4C, "24 3f aa 95", "24 3f 42 95", "ld.h -0x6a56[gp],r7 -> ld.h -0x6abe[gp],r7",
       "operand x := gp-0x6abe (FRESH motor-rate EMA; the +-12000 bail now gates it)")
E2 = (0x28FA4, "89 d1", "c9 d1", "subr r9,r26 -> add r9,r26", "r26 = s_old + s_new (stock's sum)")
B2 = (0x29A50, "e2 47 00 00", "e0 df 34 43", "setfe r8 -> cmovne r0,r27,r8", "r8 := (request == 1) ? bVar2 : 0")
A2 = (0x29A56, "da 05", "b2 05", "bne 0x29A60 -> be 0x29A5C", "PID runs iff ramp != 0 AND r8 != 0")
E4 = (0x29D6A, "08 80 ed 80", "24 87 52 96", "mov r8,r16 ; mulh r13,r16 -> ld.h -0x69ae[gp],r16", "sp := gp-0x69ae")
HK = (0x29D76, "c2 82 ba 81", "89 37 8a ae", "shl 2,r16 ; sub r26,r16 -> jarl 0xC4C00,r6", "the hook")
E5 = [(0x29EDE, "c7 00", "80 39", "zxh r7 -> subr r0,r7", "-Kd"),
      (0x29EE0, "10 40 bb 41", "24 47 aa 95", "mov r16,r8 ; sub r27,r8 -> ld.h -0x6a56[gp],r8", "D on the HELD rate")]
OPH = (0x29EE0, "10 40 bb 41", "1a 40 00 00", "mov r16,r8 ; sub r27,r8 -> mov r26,r8 ; nop",
       "D on the cave's operand in r26 (Kd = zxh, unchanged at 0x29EDE)")
V1 = (0x1310D, "30", "41", "F181 '39990-TVA,A160' -> '...,A16A'", "the fork interlock (C1 rev 2's V1)")

CAL = dict(a=0xC63E8, b=0xC63EA, C=0xC62E6, DB=0xC62E4, Ki=0xC63E6, ICL=0xC61BA, DCL=0xC61B6)
KP_Y, KD_Y = 0xE5384, 0xE5126          # selector-7 records (C1 rev 2 sec 1.3): Kp Y x5, Kd Y x4


def cand_edits(cid):
    """-> (code edits, cal dict, Kp, Kd)"""
    import ds_final as F
    des = F.CANDS[cid]
    if des.kind == "cascade":
        code = [E1F if des.cop == "fresh" else None, E2, B2, A2, E4, HK, V1]
        code = [c for c in code if c]
        cal = dict(a=int(des.fa), b=int(des.fb), C=65535, DB=0, Ki=int(des.ki), ICL=4096, DCL=0)
        return code, cal, int(des.kp), 0
    code = [E1, E2, B2, A2, E4, HK, V1]
    if des.dsrc == "rate_held":
        code += E5
    elif des.dsrc == "op":
        code += [OPH]
    cal = dict(a=0, b=8192, C=65535, DB=0, Ki=int(des.ki), ICL=4096, DCL=10240)
    return code, cal, int(des.kp), int(des.kd)


def build(cid, tbl):
    img = bytearray(V)
    listing = []
    code, cal, kp, kd = cand_edits(cid)
    for a, old, new, dec, term in code:
        ob, nb = bytes.fromhex(old.replace(" ", "")), bytes.fromhex(new.replace(" ", ""))
        assert img[a:a + len(ob)] == ob, (cid, hex(a), img[a:a + len(ob)].hex(), old)
        img[a:a + len(nb)] = nb
        listing.append(("code", a, old, new, dec, term))
    for k, v in cal.items():
        a = CAL[k]
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H" if k != "a" else "<h", v)
        if bytes(img[a:a + 2]) != old:
            listing.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "), f"{k} {struct.unpack('<H', old)[0]} -> {v}",
                            ""))
    for i in range(5):
        a = KP_Y + 2 * i
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H", kp)
        if bytes(img[a:a + 2]) != old:
            listing.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "),
                            f"Kp record Y[{i}] {struct.unpack('<H', old)[0]} -> {kp}", ""))
    for i in range(4):
        a = KD_Y + 2 * i
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H", kd)
        if bytes(img[a:a + 2]) != old:
            listing.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "),
                            f"Kd record Y[{i}] {struct.unpack('<H', old)[0]} -> {kd}", ""))
    cave, labels, _ = A.assemble(cid if cid not in ("B0", "B0r", "D1a") else "B0", tbl)
    assert all(x == 0xFF for x in img[A.CAVE:A.CAVE + len(cave)])
    img[A.CAVE:A.CAVE + len(cave)] = cave
    return img, listing, cave, labels


def main():
    import ds_final as F
    tabs = F.tables()
    lines = []
    P = lambda s="": (print(s), lines.append(s))  # noqa: E731
    P(f"base V295 {Path(IMG).name}  sha256 {hashlib.sha256(V).hexdigest()}")
    P(f"V295 cal anchors: Kp Y {[struct.unpack_from('<H', V, KP_Y + 2 * i)[0] for i in range(5)]}  Kd Y "
      f"{[struct.unpack_from('<H', V, KD_Y + 2 * i)[0] for i in range(4)]}  " +
      " ".join(f"{k} {struct.unpack_from('<H', V, a)[0]}" for k, a in CAL.items()))
    summary = {}
    for cid in F.CANDS:
        img, listing, cave, labels = build(cid, tabs[cid])
        diff = [a for a in range(0x13000, 0x100000) if img[a] != V[a]]
        listed = set()
        for kind, a, old, new, dec, term in listing:
            n = len(bytes.fromhex(old.replace(" ", "")))
            listed |= {a + i for i in range(n) if img[a + i] != V[a + i]}
        cave_set = {a for a in range(A.CAVE, A.CAVE + len(cave)) if img[a] != V[a]}
        unlisted = [hex(a) for a in diff if a not in listed and a not in cave_set]
        n_code = sum(1 for a in listed if a < 0xC0000)
        n_cal = sum(1 for a in listed if a >= 0xC0000)
        ncode_cave = labels["TBL"] - A.CAVE
        summary[cid] = dict(in_place_code=n_code, cal=n_cal, cave_code=ncode_cave, cave_table=len(cave) - ncode_cave,
                            total=n_code + n_cal + len(cave), unlisted=unlisted)
        P("=" * 110)
        P(f"{cid}: {F.CANDS[cid].name}")
        for kind, a, old, new, dec, term in listing:
            P(f"   {kind:4s} {a:#08x}  {old:12s} -> {new:12s}  {dec:52s} {term}")
        P(f"   cave {A.CAVE:#x}..{A.CAVE + len(cave):#x}: {len(cave)} bytes ({ncode_cave} code + {len(cave) - ncode_cave} table)"
          f"  sha256 {hashlib.sha256(cave).hexdigest()[:16]}")
        P(f"   FULL DIFF vs V295 over [0x13000, 0x100000): {len(diff)} bytes; changed bytes: in-place code {n_code}, cal "
          f"{n_cal}, cave {len(cave)} (its bytes that differ from 0xFF: {len(cave_set)}); UNLISTED: {unlisted or 'none'}")
        P("   CRC trailers the builder must recompute: 0xC4FFC (cave block), 0xC6FFC (cal page), the E5xxx record block,"
          " and the main block holding 0x13100 (V1) -- verify_bootloader_crc.py on the built image (H8)")
    (HERE / "ds_bytes_out.txt").write_text("\n".join(lines), encoding="utf-8")
    (G2.OUT / "bytes_summary.json").write_text(json.dumps(summary))
    return summary


if __name__ == "__main__":
    main()
