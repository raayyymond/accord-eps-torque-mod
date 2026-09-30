"""ADV-bytes (p-gain lens) step 1: every proposed cell read from the V294 IMAGE; aliasing; reader census; CRC scope.

Adversary of R1.3_8_100 (Kp bank 0xCB994, all 28 records, X [0,8,54,100,208] Y [1248,1248,1104,960,960]).
Written from scratch; independent of the designer's s9/s15 scripts. Applies the edit IN MEMORY only (no file written).
"""
import hashlib, json, os, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[3]          # analysis-2020accord
sys.path.insert(0, str(KIT / "lib"))
sys.path.insert(0, str(KIT / "builds" / "v108_plus")); [sys.path.insert(0, str(d)) for d in (KIT / "builds").iterdir() if d.is_dir()]
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = ROOT + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
IMG293 = ROOT + "/analysis-2020accord/_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
STOCK = ROOT + "/analysis-2020accord/stock_fw_dump/code.bin"
b = open(IMG, "rb").read()
h = hashlib.sha256(b).hexdigest()
print("V294 sha256", h, "len", hex(len(b)))
assert h == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"

def u16(a, B=b): return struct.unpack_from("<H", B, a)[0]
def s16(a, B=b): return struct.unpack_from("<h", B, a)[0]
def u32(a, B=b): return struct.unpack_from("<I", B, a)[0]

# ---------------------------------------------------------------- globals the arithmetic depends on
cells = {"idx clamp + 0xC64F0 (u8)": b[0xC64F0], "idx clamp - 0xC64F1 (u8)": b[0xC64F1],
         "P clamp 0xC61BC": u16(0xC61BC), "sum clamp 0xC61BE": u16(0xC61BE), "D clamp 0xC61B6": u16(0xC61B6),
         "I clamp 0xC61BA": u16(0xC61BA), "Ki 0xC63E6": u16(0xC63E6), "deadband 0xC62E4": u16(0xC62E4),
         "C 0xC62E6": u16(0xC62E6), "a 0xC63E8": s16(0xC63E8), "b 0xC63EA": u16(0xC63EA),
         "lagA 0xC63EC": s16(0xC63EC), "lagB 0xC63EE": u16(0xC63EE), "gate en 0xC64A3 (u8)": b[0xC64A3],
         "gate 0xC61B8": s16(0xC61B8), "fwd gain 0xC6CD0": s16(0xC6CD0), "lane clamp 0xC61B4": u16(0xC61B4),
         "fwd clamp 0xC61B2": u16(0xC61B2)}
for k, v in cells.items():
    print(f"  {k:28s} {v}")

# ---------------------------------------------------------------- the bank and the 28 records
KP = 0xCB994
spec = json.load(open(HERE / "out" / "V295_p-gain_candidate_spec.json"))
ptrs = [u32(KP + 4 * s) for s in range(28)]
print("Kp pointer table:", [hex(p) for p in ptrs])
print("distinct:", len(set(ptrs)), " sorted strides:", sorted(set(ptrs[i + 1] - ptrs[i] for i in range(27))))
bad = []
for s, p in enumerate(ptrs):
    r = spec["records"][s]
    assert int(r["rec"], 16) == p, (s, r["rec"], hex(p))
    n = u16(p)
    X = [u16(p + 2 + 2 * k) for k in range(5)]
    Y = [u16(p + 12 + 2 * k) for k in range(5)]
    pad = b[p + 0x16:p + 0x18].hex()
    blk = b[p + 2:p + 0x16].hex()
    if blk != r["bytes_v294"] or X != r["X_v294"] or Y != r["Y_v294"] or n != 5:
        bad.append(s)
    print(f"  slot {s:2d} rec {p:#07x} n={n} X={X} Y={Y} pad={pad} next={b[p+0x18:p+0x1C].hex()}")
print("records disagreeing with spec bytes_v294:", bad)
print("live slot 7:", hex(ptrs[7]))

# what surrounds the record blocks (other banks' records sharing the pages?)
for page in sorted(set(p & ~0xFFF for p in ptrs)):
    recs = sorted(p for p in ptrs if p & ~0xFFF == page)
    lo, hi = recs[0], recs[-1] + 0x18
    print(f"page {page:#x}: Kp records {lo:#x}..{hi:#x}; 24 B before: {b[lo-24:lo].hex()} ; 24 B after: {b[hi:hi+24].hex()}")

# ---------------------------------------------------------------- aliasing: any LE32 (any alignment) pointing into a Kp record
rec_ranges = [(p, p + 0x18) for p in ptrs]
alias = {}
for off in range(0, len(b) - 3):
    v = u32(off)
    if 0xE4000 <= v < 0xE9000:
        for lo, hi in rec_ranges:
            if lo <= v < hi:
                alias.setdefault(hex(v), []).append(hex(off))
tbl_hits = {k: [o for o in v if not (KP <= int(o, 16) < KP + 112)] for k, v in alias.items()}
print("LE32 (any alignment) pointing INTO a Kp record, outside the 0xCB994 table:",
      {k: v for k, v in tbl_hits.items() if v})
print("  (control) table entries found by this scan:", sum(1 for v in alias.values() for o in v if KP <= int(o, 16) < KP + 112))

# aligned pointer tables: which 4-aligned LE32 words anywhere point into the 0xE4000-0xE8FFF record pages
# and at which distance from a Kp record (a neighbouring bank sharing a record would show here)
near = []
for off in range(0, len(b) - 3, 4):
    v = u32(off)
    for lo, hi in rec_ranges:
        if lo - 0x18 < v < hi + 0x18 and not (lo <= v < hi) and v != lo - 0x18 and v != hi:
            near.append((hex(off), hex(v)))
print("aligned LE32 pointing within one stride of a Kp record but not at a record start (overlap risk):", near[:20], len(near))

# ---------------------------------------------------------------- reader census of 0xCB994 and of the record addresses
def mov_imm32_hits(lo, hi):
    out = []
    for off in range(0x13000, 0xC0000, 2):
        hw1 = u16(off)
        if (hw1 & 0xFFE0) == 0x0620:
            imm = u32(off + 2)
            if lo <= imm < hi:
                out.append((hex(off), "r%d" % (hw1 & 0x1F), hex(imm)))
    return out
print("mov imm32 of 0xCB994:", mov_imm32_hits(KP, KP + 1))
print("mov imm32 into the Kp table (0xCB994..+0x70):", mov_imm32_hits(KP, KP + 0x70))
print("CONTROL mov imm32 0xCB7D4 (Kd bank):", mov_imm32_hits(0xCB7D4, 0xCB7D5), " 0xC9A88 (map):", mov_imm32_hits(0xC9A88, 0xC9A89))
print("mov imm32 into the Kp record pages 0xE4000..0xE9000:", mov_imm32_hits(0xE4000, 0xE9000))
# movhi/movea|addi pairs forming 0xCB994 (hi 0xD, lo 0xB994) or a record address
pairs = []
for off in range(0x13000, 0xC0000, 2):
    hw1 = u16(off); hw2 = u16(off + 2)
    op6 = (hw1 >> 5) & 0x3F
    if op6 in (0x30, 0x31) and hw2 == 0xB994:
        pairs.append(("addi/movea 0xB994", hex(off)))
    if op6 == 0x32 and hw2 in (0x000C, 0x000D, 0x000E):
        pairs.append(("movhi %#x" % hw2, hex(off), "r%d" % ((hw1 >> 11) & 0x1F)))
print("movhi 0xC/0xD/0xE sites:", [p for p in pairs if p[0].startswith("movhi")][:40], len([p for p in pairs if p[0].startswith("movhi")]))
print("addi/movea imm16 0xB994:", [p for p in pairs if p[0].startswith("addi")])
# 4-byte disp16 loads with disp 0xB994 (movhi 0xD base + ld disp) or disp to record addresses from a movhi 0xE base
def disp16_hits(lo16set):
    out = []
    for off in range(0x13000, 0xC0000, 2):
        hw1 = u16(off); hw2 = u16(off + 2)
        op6 = (hw1 >> 5) & 0x3F
        d = None
        if op6 in (0x38, 0x3A): d = hw2
        elif op6 in (0x39, 0x3B, 0x3F): d = hw2 & 0xFFFE
        elif op6 in (0x3C, 0x3D) and (hw2 & 1): d = (hw2 & 0xFFFE) | (op6 & 1)
        if d is not None and d in lo16set:
            out.append((hex(off), op6, "r%d" % (hw1 & 0x1F)))
    return out
print("disp16 loads with disp 0xB994..0xB9FF (movhi 0xD base):", disp16_hits(set(range(0xB994, 0xBA04))))

# ---------------------------------------------------------------- the twin island: callers?
ISL_LO, ISL_HI = 0x2A30E, 0x2B422
def calls_into(lo, hi):
    out = []
    for off in range(0x13000, 0xC0000, 2):
        hw1 = u16(off)
        if ((hw1 >> 6) & 0x1F) == 0x1E:           # Format V jr/jarl disp22
            hw2 = u16(off + 2)
            if hw2 & 1:
                continue
            d = ((hw1 & 0x3F) << 16) | hw2
            if d & 0x200000: d -= 0x400000
            t = off + d
            if lo <= t < hi:
                out.append((hex(off), "jarl" if (hw1 >> 11) else "jr", hex(t)))
        if (hw1 & 0xFFE0) == 0x02E0:              # 6-byte jr/jarl disp32
            d = struct.unpack_from("<i", b, off + 2)[0]
            t = off + d
            if lo <= t < hi and not (d & 1):
                out.append((hex(off), "jarl32", hex(t)))
    return out
ctl = calls_into(0x28EA6, 0x28EA7)
print("CONTROL calls into FUN_00028ea6 (expect 0x22522):", ctl)
print("calls/jumps into the twin island from OUTSIDE it:", [c for c in calls_into(ISL_LO, ISL_HI) if not (ISL_LO <= int(c[0], 16) < ISL_HI)])
print("LE32 (aligned) values inside the twin island:", [(hex(o), hex(u32(o))) for o in range(0, len(b) - 3, 4) if ISL_LO <= u32(o) < ISL_HI][:20])
print("mov imm32 values inside the twin island:", mov_imm32_hits(ISL_LO, ISL_HI))

# ---------------------------------------------------------------- the edit, IN MEMORY, and the CRC scope
import build_vfourframe_tva as FF
from verify_bootloader_crc import walk, walk_all_blocks
Xn, Yn = [0, 8, 54, 100, 208], [1248, 1248, 1104, 960, 960]
e = bytearray(b)
for p in ptrs:
    for k in range(5):
        struct.pack_into("<H", e, p + 2 + 2 * k, Xn[k])
        struct.pack_into("<H", e, p + 12 + 2 * k, Yn[k])
diff = [i for i in range(len(b)) if b[i] != e[i]]
print("payload bytes changed:", len(diff), " pages:", sorted(set(hex(i & ~0xFFF) for i in diff)))
assert all(any(p + 2 <= i < p + 0x16 for p in ptrs) for i in diff)
blocks = FF.crc_block_map(bytes(b))
hit_blocks = sorted({(s_, t) for s_, t in blocks for i in diff if s_ <= i < t})
print("CRC blocks (FF.crc_block_map) covering the payload:", [(hex(s_), hex(t)) for s_, t in hit_blocks])
for s_, t in hit_blocks:
    struct.pack_into("<I", e, t, zlib.crc32(bytes(e[s_:t])) & 0xFFFFFFFF)
diff2 = [i for i in range(0x13000, 0x100000) if b[i] != e[i]]
trail = [i for i in diff2 if i not in set(diff)]
print("after CRC: total diff", len(diff2), " trailer bytes", len(trail), " trailer addrs", sorted(set(hex(i & ~3) for i in trail)))
# chain verified by two locators on the in-memory edited image
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    r1 = walk_all_blocks(bytes(e)); r2 = walk(bytes(e))
print("walk_all_blocks / walk on the edited image (0 = all good):", r1, r2)
# the V293 -> V294 diff: same CRC blocks exercised?
b3 = open(IMG293, "rb").read()
d34 = [i for i in range(0x13000, 0x100000) if b[i] != b3[i]]
blk34 = sorted({(s_, t) for s_, t in blocks for i in d34 if s_ <= i < t})
print("V293->V294 CRC blocks touched:", [(hex(s_), hex(t)) for s_, t in blk34])
print("candidate blocks subset of V294's exercised blocks:", set(hit_blocks) <= set(blk34))
print("V293->V294 bytes inside the Kp records:", sum(1 for i in d34 if any(p <= i < p + 0x18 for p in ptrs)))
# code region untouched
print("code region [0x13000,0xC0000) bytes changed by the edit:", sum(1 for i in diff2 if i < 0xC0000))
json.dump({"ptrs": [hex(p) for p in ptrs], "diff_payload": len(diff), "diff_total": len(diff2),
           "crc_blocks": [(hex(s_), hex(t)) for s_, t in hit_blocks]},
          open(HERE / "out" / "advp1_bytes.json", "w"), indent=1)
