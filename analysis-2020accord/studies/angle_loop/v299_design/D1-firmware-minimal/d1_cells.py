# -*- coding: utf-8 -*-
"""d1_cells.py -- read every cell D1 touches or depends on from the V298 image (LE), and the cave immediates.
ANALYSIS ONLY.  Wall time < 1 s."""
import glob, os, struct, sys, time, hashlib
from pathlib import Path
t0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import lane_mirror_v295 as LM
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
p = sorted(glob.glob(os.path.join(ROOT, "analysis-2020accord", "_v298_*_plain_image.bin")))
assert len(p) == 1, p
img = Path(p[0]).read_bytes()
print("image", Path(p[0]).name, hashlib.sha256(img).hexdigest()[:16])
c = LM.load_cal(Path(p[0]), check_sha=False)
for k in ("C", "a", "b", "DB", "Ki", "ICL", "PCL", "DCL", "SCL", "oa", "ob", "g74a3", "dz", "fwd", "OCL", "idx_hi", "idx_lo", "cut"):
    print(f"  {k:7s} {c[k]}")
for k in ("kp", "kd", "lim", "cliff_same", "cliff_opp", "tap_same", "tap_opp", "fadeA", "fadeA2", "fadeB", "fadeB2", "spF", "map"):
    print(f"  {k:10s} X={c[k][0]}  Y={c[k][1]}")
u32 = lambda a: struct.unpack_from("<I", img, a)[0]
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
for nm, bank, n in (("kp", 0xCB994, 5), ("kd", 0xCB7D4, 4), ("lim", 0xCB844, 9), ("cliff_same", 0xCBA74, 4), ("cliff_opp", 0xCBA04, 4)):
    q = u32(bank + 4 * 7)
    print(f"  {nm} record @ {q:#x} (selector 7)  n={u16(q)}  Yaddr={q+2+2*n:#x}")
# ramp cells
for nm, a in (("ramp_in0", 0xC63F8), ("ramp_out0", 0xC63F6), ("ramp_in2", 0xC63FC), ("ramp_out2", 0xC63FA)):
    print(f"  {nm} {a:#x} = {u16(a)}")
# cave dump
cave = img[0xC4C00:0xC4C00 + 260]
print("cave sha", hashlib.sha256(cave).hexdigest()[:12])
# find movea imm16,r0,r13 forms (Format VI: hw1 = reg2<<11 | 0x31<<5 | reg1 ; movea opcode 110001)
for off in range(0, 0xDA, 2):
    hw1 = cave[off] | cave[off + 1] << 8
    if (hw1 >> 5) & 0x3F == 0x31:
        imm = struct.unpack_from("<h", cave, off + 2)[0]
        print(f"  movea @ {0xC4C00+off:#x}: imm {imm}  r{hw1 & 31} -> r{hw1 >> 11}   bytes {cave[off:off+4].hex(' ')}")
    if (hw1 >> 5) & 0x3F == 0x30:
        imm = struct.unpack_from("<h", cave, off + 2)[0]
        print(f"  addi  @ {0xC4C00+off:#x}: imm {imm}  r{hw1 & 31} -> r{hw1 >> 11}   bytes {cave[off:off+4].hex(' ')}")
print(f"wall {time.time()-t0:.2f} s")
