"""S3 common bytes scorer for the V299 candidates (read-only; builds nothing that is written as an image).

For every candidate: (1) assert the V298 image holds the bytes each designer cites; (2) apply the candidate's
in-place edits (or splice its cave hex) to an in-memory copy, recompute the owning CRC trailers with zlib.crc32
(the build_v298_tva method; control = V298's own trailers reproduce); (3) count differing bytes, caves, cave
bytes; (4) the free-region check.  Vectorised; wall time printed.
"""
import hashlib, struct, time, zlib, glob, os
from pathlib import Path
import numpy as np

T0 = time.time()
ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
KIT = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")
IMG = Path(glob.glob(str(ROOT / "analysis-2020accord" / "_v298_*_plain_image.bin"))[0])
V298 = IMG.read_bytes()
SHA = hashlib.sha256(V298).hexdigest()
out = []
def say(s=""): out.append(s); print(s)
say(f"V298 image {IMG.name}\n  sha256 {SHA}  ({'OK 177abf04' if SHA.startswith('177abf04') else 'MISMATCH'})")

BLOCKS = [(0x13000, 0xC4FFC), (0xC6000, 0xC6FFC), (0xE5000, 0xE5FFC)]
def crc_ok(img):
    return {hex(b0): zlib.crc32(img[b0:b1]) & 0xFFFFFFFF == struct.unpack_from("<I", img, b1)[0] for b0, b1 in BLOCKS}
say(f"  control: V298 trailers reproduce with zlib.crc32: {crc_ok(V298)}")

# ---- (1) cited cells -------------------------------------------------------------------------------------
CITED = [  # addr, expected V298 bytes (hex), who cites it, meaning
    (0xC4C62, "206e0002", "D1/D2/D3/D5", "movea 512,r0,r13 (hard freeze)"),
    (0xC4C6A, "206e2c01", "D1/D2/D3/D5", "movea 300,r0,r13 (opposing freeze)"),
    (0xC4C5E, "e44799b0", "D1", "ld.hu -0x4f68[gp],r8"),
    (0xC4C1C, "2906da4c0c00", "D1", "mov 0xC4CDA,r9 (table ptr)"),
    (0xC4CDA, "ca029a041104", "D1/D3", "GB-P row0 X 714 G 1178 S 1041"),
    (0xC4CE4, "88e7", "D4", "S1 -6264"), (0xC4CE8, "f802", "D4", "G2 760"), (0xC4CEA, "0ff8", "D4", "S2 -2033"),
    (0xC4CEE, "3002", "D4", "G3 560"), (0xC4CF0, "2206", "D4", "S3 1570"), (0xC4CF4, "2c04", "D4", "G4 1068"),
    (0xC4CF6, "4608", "D4", "S4 2118"),
    (0xC4CA2, "206e0010", "D2 graft G-b", "movea 4096 (A3 low-speed cap)"),
    (0x29D72, "6487ce95", "D4 N0", "st.h r16,-0x6a32[gp]"),
    (0xC4B92, "2437b494", "D4 T7", "ld.h -0x6b4c[gp],r6 (0x14A b4.7 rung)"),
    (0x1310D, "41", "D3/D4/D5", "F181 version byte 'A'"),
    (0xC4FFC, "f3d87c6b", "D4/D5", "main-block CRC trailer"),
    (0xC61BC, "003c", "D3b", "PCL 15360"), (0xC61BE, "003c", "D3b", "SCL 15360"),
    (0xC61B4, "000c", "D3", "OCL 3072"), (0xC6CD0, "e214", "D3", "fwd gain 5346"),
]
say("\n(1) cited cells vs the V298 image")
for a, exp, who, what in CITED:
    got = V298[a:a + len(exp) // 2].hex()
    say(f"  0x{a:05X}  {got:14s} {'OK ' if got == exp else 'DIFF expected ' + exp}  [{who}] {what}")
ver = V298[0x13100:0x13112]
say(f"  version string context 0x13100: {ver!r}")
for pat in ("206e2c01", "206e0002", "206e0010"):
    hits = [m for m in range(0, len(V298) - 4, 2) if V298[m:m + 4] == bytes.fromhex(pat)]
    say(f"  pattern {pat}: {[hex(h) for h in hits]}")
free = V298[0xC4D04:0xC4FF0]
say(f"  free run 0xC4D04..0xC4FF0: {len(free)} B, all 0xFF: {set(free) == {0xFF}}")
say(f"  bytes 0xC4FF0..0xC4FFC: {V298[0xC4FF0:0xC4FFC].hex()}")

# ---- (2) candidates ---------------------------------------------------------------------------------------
def patch(img, edits):
    b = bytearray(img)
    for a, hx in edits:
        bb = bytes.fromhex(hx); b[a:a + len(bb)] = bb
    return b

def cave_from_hex(path, base=0xC4C00):
    hx = Path(path).read_text().split()
    return bytes.fromhex("".join(hx))

def finish(name, b, caves, cave_bytes, ram, note=""):
    pre = [a for a in range(len(V298)) if False]
    diff0 = np.flatnonzero(np.frombuffer(bytes(b), np.uint8) != np.frombuffer(V298, np.uint8))
    owners = sorted({(b0, b1) for a in diff0 for (b0, b1) in BLOCKS if b0 <= a < b1})
    for b0, b1 in owners:
        struct.pack_into("<I", b, b1, zlib.crc32(bytes(b[b0:b1])) & 0xFFFFFFFF)
    diff = np.flatnonzero(np.frombuffer(bytes(b), np.uint8) != np.frombuffer(V298, np.uint8))
    stray = [hex(a) for a in diff0 if not any(b0 <= a < b1 for b0, b1 in BLOCKS)]
    say(f"  {name:22s} pre-CRC {len(diff0):4d} B | with CRC {len(diff):4d} B | CRC blocks {[hex(x) for x, _ in owners]} "
        f"| caves {caves} cave {cave_bytes} B | RAM {ram} | outside-CRC bytes {stray} | crc_ok {all(crc_ok(bytes(b)).values())} {note}")
    return bytes(b), len(diff0), len(diff)

say("\n(2) candidate byte counts (in-memory images only; nothing written)")
R = {}
R["D1a"] = finish("D1a (cal-only)", patch(V298, [(0xC4C64, "cd04"), (0xC4C6C, "cd04")]), "0 new (V298's)", 260, 0)
R["D1-a2"] = finish("D1-a2 G0-1400 (alone)", patch(V298, [(0xC4CDC, "7805"), (0xC4CDE, "ec00")]), "0 new", 260, 0)
d1c = cave_from_hex(KIT / "analysis-2020accord/studies/angle_loop/v299_design/D1-firmware-minimal/out/d1c_flight.hex")
say(f"  D1c hex: {len(d1c)} B sha {hashlib.sha256(d1c).hexdigest()[:16]} (claimed 80dd2052edc0)")
b = bytearray(V298); b[0xC4C00:0xC4D04] = d1c + b"\xff" * (260 - len(d1c))
cave_diff = sum(1 for i in range(260) if b[0xC4C00 + i] != V298[0xC4C00 + i])
say(f"  D1c cave-region bytes differing from V298: {cave_diff} (claimed 152); first diff at "
    f"{hex(0xC4C00 + next(i for i in range(260) if b[0xC4C00+i] != V298[0xC4C00+i]))}; table ptr bytes {bytes(b[0xC4C1C:0xC4C22]).hex()}")
bv = bytearray(b); bv[0x1310D] = 0x42
R["D1c"] = finish("D1c (cave, A16A kept)", b, "1 (V298's, relinked)", len(d1c), 0)
R["D1c+A16B"] = finish("D1c + A16B", bv, "1 (relinked)", len(d1c), 0)
R["D2"] = finish("D2a/D2b", bytearray(V298), "0", 0, 0)
d3 = [(0xC4C64, "cd04"), (0xC4C6C, "2003"), (0xC4CDC, "8605"), (0xC4CDE, "b900"), (0x1310D, "42")]
bd3 = patch(V298, d3)
say(f"  D3a cave sha {hashlib.sha256(bytes(bd3[0xC4C00:0xC4D04])).hexdigest()[:8]} (claimed 83b9799b)")
R["D3a"] = finish("D3a", bd3, "0 new (V298's)", 260, 0)
R["D3b"] = finish("D3b", patch(V298, d3 + [(0xC61BC, "804a"), (0xC61BE, "804a")]), "0 new", 260, 0)
d4a = [(0xC4CE4, "72ef"), (0xC4CE8, "dc03"), (0xC4CEA, "adf5"), (0xC4CEE, "d802"), (0xC4CF0, "f807"),
       (0xC4CF4, "6c05"), (0xC4CF6, "e905"), (0x1310D, "42")]
R["D4a"] = finish("D4a GB-S13", patch(V298, d4a), "0 new", 260, 0)
d4b = cave_from_hex(KIT / "_scratch/v299_D4/d4b_cave.hex")
say(f"  D4b hex: {len(d4b)} B sha {hashlib.sha256(d4b).hexdigest()[:16]} (claimed 59b90cbdf004)")
b = bytearray(V298); b[0xC4C00:0xC4C00 + len(d4b)] = d4b
b[0x29D72:0x29D76] = bytes(4); b[0xC4B92:0xC4B96] = bytes.fromhex("2437ce95"); b[0x1310D] = 0x42
cave_diff = sum(1 for i in range(len(d4b)) if b[0xC4C00 + i] != V298[0xC4C00 + i])
say(f"  D4b cave-region bytes differing: {cave_diff}; nop form at 0x29D72 = 00000000 (V850 nop is 0x0000 halfword)")
R["D4b"] = finish("D4b", b, "1 (V298's, grown)", len(d4b), 1)
R["D5b"] = finish("D5b", patch(V298, [(0xC4C64, "cd04"), (0xC4C6C, "cd04"), (0x1310D, "42")]), "0 new", 260, 0)

# slope arithmetic controls (GB walk S = (G1-G0)*4096/(X1-X0))
say("\n(3) table slope controls")
for nm, g0 in (("V298", 1178), ("D3a", 1414), ("D1-a2", 1400)):
    say(f"  {nm}: G0 {g0} S0 = {(1465 - g0) * 4096 / (1843 - 714):.1f}")
for nm, (g1, g2, x1, x2) in {"S1": (1465, 988, 1843, 2304), "S2": (988, 728, 2304, 2707),
                             "S3": (728, 1388, 2707, 4032), "S4": (1388, 2188, 4032, 6198)}.items():
    say(f"  D4a {nm} = {(g2 - g1) * 4096 / (x2 - x1):.1f}")
say(f"\nwall {time.time() - T0:.1f} s")
Path(__file__).with_suffix(".txt").write_text("\n".join(out))
