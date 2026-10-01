# -*- coding: utf-8 -*-
r"""c3_bytes.py -- every byte each C3 implementation changes, applied IN MEMORY to a copy of the V295 plain image, with a
full diff over [0x13000, 0x100000) that must contain exactly the listed bytes and the cave.  Every pre-edit byte is
asserted against V295 first.  The delivered Kp_eff / T-per-deg surface is read FROM the in-memory built image's own
table, never from the script constants.  ANALYSIS ONLY: nothing is written to disk as an image, no .rwd, no CRC trailer
recomputed (that is the builder's H8 step; the regions are NAMED here).
usage: python c3_bytes.py
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3_common as CC  # noqa: E402

GP_CELLS = dict(a=0xC63E8, b=0xC63EA, C=0xC62E6, DB=0xC62E4, Ki=0xC63E6, ICL=0xC61BA, DCL=0xC61B6)
KP_Y, KD_Y = 0xE5384, 0xE5126
CAVE = 0xC4C00

# in-place code edits: (addr, V295 old hex, new hex, decode) -- confirmed by Ghidra dry-run (c3_score_freq/C3InPlace)
E1 = (0x28F4C, "24 3f aa 95", "24 3f 00 96", "ld.h -0x6a56->-0x6a00[gp],r7 : x := theta")
E2 = (0x28FA4, "89 d1", "c9 d1", "subr->add r9,r26 : r26 = s_old + s_new")
B2 = (0x29A50, "e2 47 00 00", "e0 df 34 43", "setfe->cmovne r0,r27,r8 : r8 = (req==1)?bVar2:0")
A2 = (0x29A56, "da 05", "b2 05", "bne->be : PID iff ramp!=0 AND r8!=0")
E4 = (0x29D6A, "08 80 ed 80", "24 87 52 96", "mov/mulh -> ld.h -0x69ae[gp],r16 : sp := gp-0x69ae")
HK = (0x29D76, "c2 82 ba 81", "89 37 8a ae", "shl2/sub -> jarl 0xC4C00,r6 : the hook")
OPH = (0x29EE0, "10 40 bb 41", "1a 40 00 00", "mov r16/sub -> mov r26,r8 ; nop : D on the fresh operand in r26")
E5a = (0x29EDE, "c7 00", "80 39", "zxh r7 -> subr r0,r7 : -Kd")
E5b = (0x29EE0, "10 40 bb 41", "24 47 aa 95", "mov r16/sub -> ld.h -0x6a56[gp],r8 : D on the held rate")
V1 = (0x1310D, "30", "41", "F181 '39990-TVA,A160' -> '...,A16A' : the fork interlock")


def edits(cid):
    spec = CC.IMPLS[cid]
    if spec["dop"] == "held":
        code = [E1, E2, B2, A2, E4, HK, E5a, E5b, V1]
    else:
        code = [E1, E2, B2, A2, E4, HK, OPH, V1]
    cal = dict(a=0, b=8192, C=65535, DB=0, Ki=56, ICL=spec["icl"], DCL=10240)
    return code, cal, 112, spec["kd"]


def build(cid):
    V = CC.v295_bytes()
    img = bytearray(V)
    listed = []
    code, cal, kp, kd = edits(cid)
    for a, old, new, dec in code:
        ob, nb = bytes.fromhex(old.replace(" ", "")), bytes.fromhex(new.replace(" ", ""))
        assert img[a:a + len(ob)] == ob, (cid, hex(a), img[a:a + len(ob)].hex(), old)
        img[a:a + len(nb)] = nb
        listed.append(("code", a, old, new, dec))
    for k, v in cal.items():
        a = GP_CELLS[k]
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<h" if k == "a" else "<H", v)
        if bytes(img[a:a + 2]) != old:
            listed.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "),
                           f"{k} {struct.unpack('<H', old)[0]} -> {v}"))
    for i in range(5):
        a = KP_Y + 2 * i
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H", kp)
        if bytes(img[a:a + 2]) != old:
            listed.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "),
                           f"Kp Y[{i}] {struct.unpack('<H', old)[0]} -> {kp}"))
    for i in range(4):
        a = KD_Y + 2 * i
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H", kd)
        if bytes(img[a:a + 2]) != old:
            listed.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "),
                           f"Kd Y[{i}] {struct.unpack('<H', old)[0]} -> {kd}"))
    cave = bytes.fromhex(CC.hexpath(cid).read_text().replace("\n", " "))
    assert all(x == 0xFF for x in img[CAVE:CAVE + len(cave)]), "cave region not free in V295"
    img[CAVE:CAVE + len(cave)] = cave
    return V, bytes(img), listed, cave


def surface(img, cid):
    """read the built image's own G table, compute Kp_eff and T/deg at the knot speeds."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("nl_cave_c3b", CC.AL / "refute_c2r2_nonlinear" / "nl_cave.py")
    NC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(NC)
    cave = img[CAVE:CAVE + len(bytes.fromhex(CC.hexpath(cid).read_text().replace("\n", " ")))]
    _, rows = NC.parse_table(cave)
    kp = struct.unpack_from("<H", img, KP_Y)[0]
    out = []
    for v in (3.1, 8.0, 10.0, 11.75, 15.0, 17.5, 22.0, 26.9):
        g = NC.walk_G(list(rows), int(round(v * 3.6 * 64)))
        kpeff = kp * g / 256.0
        out.append((v, g, kpeff, 0.1002 * kpeff))
    return rows, kp, out


def main():
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)

    V = CC.v295_bytes()
    P(f"base V295 sha256 {hashlib.sha256(V).hexdigest()}")
    P(f"V295 cals: ICL {struct.unpack_from('<H', V, GP_CELLS['ICL'])[0]}  DCL {struct.unpack_from('<H', V, GP_CELLS['DCL'])[0]}  "
      f"Kd Y {[struct.unpack_from('<H', V, KD_Y + 2 * i)[0] for i in range(4)]}")
    for cid in ("C3-P", "C3-F", "C3-PA2", "C3-Pd", "C3-P44"):
        V, img, listed, cave = build(cid)
        diff = [a for a in range(0x13000, 0x100000) if img[a] != V[a]]
        lset = set()
        for t in listed:
            a, old = t[1], t[2]
            n = len(bytes.fromhex(old.replace(" ", "")))
            lset |= {a + i for i in range(n) if img[a + i] != V[a + i]}
        caveset = {a for a in range(CAVE, CAVE + len(cave)) if img[a] != V[a]}
        unlisted = [hex(a) for a in diff if a not in lset and a not in caveset]
        n_code = sum(1 for a in lset if a < 0xC0000)
        n_cal = sum(1 for a in lset if a >= 0xC0000)
        P("=" * 100)
        P(f"{cid} [{CC.IMPLS[cid]['role']}] -- {CC.IMPLS[cid]['note']}")
        for t in listed:
            P(f"   {t[0]:4s} {t[1]:#08x}  {t[2]:12s} -> {t[3]:12s}  {t[4]}")
        P(f"   cave {CAVE:#x}: {len(cave)} B (sha256 {hashlib.sha256(cave).hexdigest()[:16]}); its bytes != 0xFF: {len(caveset)}")
        P(f"   FULL DIFF [0x13000,0x100000): {len(diff)} B; written = in-place code {n_code} + cal {n_cal} + cave "
          f"{len(cave)} = {n_code + n_cal + len(cave)}; UNLISTED: {unlisted or 'none'}")
        regions = sorted({("main block (trailer 0xC4FFC)" if a < 0xC5000 else
                           ("cal page 0xC6000-0xC6FFC" if 0xC6000 <= a < 0xC7000 else
                            ("record block 0xE5000" if 0xE5000 <= a < 0xE6000 else f"block {a & ~0xFFF:#x}")))
                          for a in diff})
        P(f"   CRC regions dirtied (builder recomputes, H8): {regions}")
        rows, kp, surf = surface(img, cid)
        P(f"   delivered surface from the BUILT image's table (Kp record {kp}):")
        P(f"     v(m/s)  G    Kp_eff   T/deg")
        for v, g, ke, t in surf:
            P(f"     {v:5.1f}  {g:5d}  {ke:7.1f}  {t:5.1f}")
    (CC.SCR / "c3_bytes_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
