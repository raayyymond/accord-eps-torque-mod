# -*- coding: utf-8 -*-
r"""syn_h1_inplace.py -- V299 SYNTHESIS crux check: D1c's three edits applied IN PLACE to V298's 260-B FLIGHT cave
(no relink: 21 bytes change, the table pointer and every displacement stay), EXECUTED by the kit's V850E2 interpreter
(nl_cave.Cpu / score_time.Cpu2) against D1's integer mirror d1_time.D1Lane.cave_stage (asym=True, thr 1229, sgn 0).
ANALYSIS ONLY: no image written, nothing flashed.  Harness = D3's d3_h1.run_h1, lane swapped for D1Lane.

The in-place patch (judge's construction, now H1-tested here):
  0xC4C64  imm16 of `movea 0x200,r0,r13` 512 -> 1229                                   [hard freeze = Honda pressed]
  0xC4C6A..0xC4C7D (20 B: V298's 16-B opposing block + its 4-B `ld.h -0x6a00[gp],r9`) ->
           `ld.h -0x6a00[gp],r9 ; mov r9,r13 ; xor r16,r13 ; bge +4 ; mov 0,r9` (12 B, = D1c's own bytes) + 4 x nop
Controls: V298 bytes vs V298 mirror (0); in-place bytes vs mirror WITHOUT asym and vs V298 mirror (must be > 0);
          D1c's RELINKED flight hex vs the same mirror (0) -- the two constructions implement one loop.
usage: python syn_h1_inplace.py
"""
import contextlib, hashlib, io, struct, sys, time, zlib
from pathlib import Path
import numpy as np
T0 = time.time()
HERE = Path(__file__).resolve().parent
V299 = HERE.parent
AL = V299.parent
KIT = AL.parents[2]
sys.path.insert(0, str(V299 / "D1-firmware-minimal"))
sys.path.insert(0, str(V299 / "D3-authority-first"))
with contextlib.redirect_stdout(io.StringIO()):
    import d1_time as DT          # D1Lane (asym switch) + its score_time instance
    import d3_h1 as D3H           # run_h1 harness (Cpu2 loop, op-skip / camera / valid classes)
ST = DT.ST
D3H.ST = ST                       # one score_time instance: Cand/Cpu2/CELLS/SCRATCH/NC/GP
D3H.NC, D3H.GP = ST.NC, ST.GP

import glob
img = open(glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_*_plain_image.bin")[0], "rb").read()
assert hashlib.sha256(img).hexdigest().startswith("177abf04")
code298 = img[0xC4C00:0xC4C00 + 260]
assert hashlib.sha256(code298).hexdigest().startswith("ef1861e10421")
cave = bytearray(code298)
assert cave[0x64:0x66] == struct.pack("<H", 512) and cave[0x6A:0x6E] == bytes.fromhex("206e2c01") and cave[0x7A:0x7E] == bytes.fromhex("244f0096")
cave[0x64:0x66] = struct.pack("<H", 1229)
SEQ = bytes.fromhex("244f0096" "0968" "3069" "ae05" "004a") + bytes(8)
cave[0x6A:0x7E] = SEQ
code_syn = bytes(cave)
diff = [(0xC4C00 + i, code298[i], code_syn[i]) for i in range(260) if code298[i] != code_syn[i]]
d1c_hex = bytes.fromhex("".join((V299 / "D1-firmware-minimal" / "out" / "d1c_flight.hex").read_text().split()))
assert d1c_hex[0x6A:0x76] == SEQ[:12], "the 12-B sequence differs from D1c's relinked listing"

def swap_lane(f):
    orig = ST.CandLane
    ST.CandLane = DT.D1Lane
    try:
        return f()
    finally:
        ST.CandLane = orig

c298 = DT.mk("V298", 512, 300, False, ST.ARB_A3)
csyn = DT.mk("SYN", 1229, 0, True, ST.ARB_A3)
cnoasym = DT.mk("noasym", 1229, 0, False, ST.ARB_A3)
edges = [-1230, -1229, -513, -512, -301, -300, 0, 300, 301, 512, 513, 1229, 1230, -32768, 32767]
L = [f"SYN H1 (in-place D1c on the V298 FLIGHT cave): bytes changed {len(diff)} at "
     + ", ".join(f"0x{a:05X}" for a, _, _ in diff),
     f"  in-place cave sha256 {hashlib.sha256(code_syn).hexdigest()[:16]} (260 B); D1c relinked flight sha {hashlib.sha256(d1c_hex).hexdigest()[:16]} ({len(d1c_hex)} B)"]
# whole-image diff + CRC for the record (the version byte A16B and the main-block trailer are the builder's)
new = bytearray(img); new[0xC4C00:0xC4C00 + 260] = code_syn; new[0x1310D] = ord("B")
new[0xC4FFC:0xC5000] = struct.pack("<I", zlib.crc32(bytes(new[0x13000:0xC4FFC])))
nd = sum(1 for i in range(len(img)) if img[i] != new[i])
L.append(f"  whole-image bytes differing incl. A16B + CRC trailer: {nd}; new main CRC {new[0xC4FFC:0xC5000].hex()}; image sha256 {hashlib.sha256(bytes(new)).hexdigest()[:16]} (NOT written to disk)")
for nm, code, cand, N in (("V298 bytes vs V298 mirror (control)", code298, c298, 1500),
                          ("IN-PLACE bytes vs D1c mirror (THE CHECK)", code_syn, csyn, 12000),
                          ("D1c RELINKED flight hex vs D1c mirror (consistency)", d1c_hex, csyn, 4000),
                          ("IN-PLACE bytes vs mirror without asym (negative)", code_syn, cnoasym, 1500),
                          ("IN-PLACE bytes vs V298 mirror (negative)", code_syn, c298, 1500)):
    bad, nn, first = swap_lane(lambda: D3H.run_h1(code, cand, N, 7, edges))
    L.append(f"  {nm:52s}: mismatches valid {bad['valid']}/{nn['valid']}, op-skip {bad['skip']}/{nn['skip']}, camera {bad['cam']}/{nn['cam']}"
             + (f"   first {first}" if first and "CHECK" in nm else ""))
    print(L[-1], flush=True)
L.append(f"wall {time.time() - T0:.1f} s")
print(L[-1])
(KIT / "_scratch" / "v299_SYN").mkdir(parents=True, exist_ok=True)
(KIT / "_scratch" / "v299_SYN" / "syn_h1_inplace.txt").write_text("\n".join(L), encoding="utf-8")
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "syn_inplace_cave.hex").write_text(code_syn.hex(" "), encoding="utf-8")
