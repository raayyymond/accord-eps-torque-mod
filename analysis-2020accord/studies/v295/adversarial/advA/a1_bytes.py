# -*- coding: utf-8 -*-
"""ADV-A a1: re-hash, whole-file diff, CRC, code-site identity vs the Ghidra listing, and every cell the lane reads,
read from the BUILT V295 image with this script's own reader (LE, tp = 0xBF000).  Writes a1_cells.json.
Nothing here imports the build script."""
import hashlib, json, os, struct, zlib

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares"
V295 = FW + "/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
V294 = FW + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
STOCK = FW + "/analysis-2020accord/stock_fw_dump/code.bin"
RWD295 = FW + "/flashing-2020accord/rwd/39990-TVA,A160-V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd"
RWD294 = FW + "/flashing-2020accord/rwd/39990-TVA,A160-V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd"
TP = 0xBF000
SEL = 7
HERE = os.path.dirname(os.path.abspath(__file__))

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

b5 = open(V295, "rb").read(); b4 = open(V294, "rb").read(); bs = open(STOCK, "rb").read()
H = dict(v295=sha(V295), v294=sha(V294), rwd295=sha(RWD295), rwd294=sha(RWD294), stock=sha(STOCK))
for k, v in H.items():
    print("sha256 %-7s %s" % (k, v))
assert H["v295"] == "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed", "F1"
assert H["v294"] == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85", "F1 base"
print("sizes", len(b5), len(b4))

# ---- whole-file diff -------------------------------------------------------------------------------------------
diff = [i for i in range(max(len(b5), len(b4))) if b5[i] != b4[i]]
print("whole-file diff V295 vs V294: %d bytes at %s" % (len(diff), [hex(i) for i in diff]))
for i in diff:
    print("   %#07x  %02x -> %02x" % (i, b4[i], b5[i]))
code_diff = [i for i in range(0x13000, 0xC0000) if b5[i] != b4[i]]
print("code region [0x13000,0xC0000) differing bytes:", len(code_diff))

u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]
print("b @0xC63EA: V294 u16 %d (bytes %s) ; V295 u16 %d (bytes %s) ; as s16 %d ; BE would be %d"
      % (u16(b4, 0xC63EA), b4[0xC63EA:0xC63EC].hex(), u16(b5, 0xC63EA), b5[0xC63EA:0xC63EC].hex(), s16(b5, 0xC63EA),
         struct.unpack_from(">H", b5, 0xC63EA)[0]))

# ---- CRC of the owning block ----------------------------------------------------------------------------------
for nm, b in (("V294", b4), ("V295", b5)):
    c = zlib.crc32(b[0xC6000:0xC6FFC]) & 0xFFFFFFFF
    tle, tbe = u32(b, 0xC6FFC), struct.unpack_from(">I", b, 0xC6FFC)[0]
    print("%s block [0xC6000,0xC6FFC) zlib.crc32 = %#010x ; trailer LE %#010x BE %#010x -> %s"
          % (nm, c, tle, tbe, "MATCH(LE)" if c == tle else ("MATCH(BE)" if c == tbe else "NO MATCH")))
# control: another block in the chain the same way (0xC5000..0xC5FFC) on the stock image, V294 and V295
for nm, b in (("stock", bs), ("V294", b4), ("V295", b5)):
    for base in (0xC5000, 0xC7000):
        c = zlib.crc32(b[base:base + 0xFFC]) & 0xFFFFFFFF
        print("  control %s block [%#x,+0xFFC) crc %#010x trailer %#010x %s" % (nm, base, c, u32(b, base + 0xFFC),
              "MATCH" if c == u32(b, base + 0xFFC) else "no"))

# ---- code sites: the V295 FILE bytes vs the bytes GHIDRA listed (V294 program, dry-run disassembly this session) --
GHIDRA = {  # address: hex bytes as the Ghidra listing printed them
    0x28F4C: "243faa95", 0x28F50: "075ee02e", 0x28F54: "0b063fa2", 0x28F58: "b905", 0x28F66: "844fd5c2",
    0x28F76: "ea05", 0x28F7C: "24d7d1c2", 0x28F82: "0032", 0x28F84: "00d2",
    0x28F86: "e587eb73", 0x28F8A: "254fe873", 0x28F8E: "f03f2002", 0x28F92: "fa4f2002", 0x28F96: "e56fe772",
    0x28F9A: "aa3a", 0x28F9C: "e577e772", 0x28FA0: "aa4a", 0x28FA2: "c749", 0x28FA4: "89d1", 0x28FA6: "edd1",
    0x28FA8: "644fd1c2", 0x28FAC: "b705", 0x28FAE: "0ed0", 0x28FB2: "8071", 0x28FB4: "eed1", 0x28FB6: "ce05",
    0x28FB8: "e5d7e772", 0x28FBC: "80d1", 0x28FBE: "1a80",
    0x29D6C: "ed80", 0x29D72: "6487ce95", 0x29D76: "c282", 0x29D78: "ba81",
    0x29E32: "c900", 0x29E36: "e9472002", 0x29E3A: "e537bd71", 0x29E3E: "a842",
    0x2A0B4: "e9bf2202", 0x2A0B8: "d766ffff", 0x2A0BC: "a862", 0x2A0BE: "e2672002", 0x2A0C2: "a862",
    0x2A174: "e53fef73", 0x2A178: "244fc5c2", 0x2A180: "e7672002", 0x2A184: "253fec73", 0x2A194: "e93f2002",
    0x2A198: "a587a374", 0x2A1A0: "aa62", 0x2A1A6: "aa3a", 0x2A1A8: "cc39", 0x2A1AA: "c749", 0x2A1AC: "a54a",
    0x2A1B0: "643fc5c2", 0x2A1E6: "ee4f2002", 0x2A1EA: "af4a", 0x2A1EC: "e900", 0x2A1EE: "253fd07c",
    0x2A1F2: "046fae98", 0x2A1F6: "e768", 0x2A1FC: "c959", 0x2A1FE: "ed5f2002", 0x2A202: "af5a",
    0x2A23C: "640fc894",
}
bad = [(hex(a), h, b5[a:a + len(h) // 2].hex()) for a, h in GHIDRA.items() if b5[a:a + len(h) // 2].hex() != h]
print("Ghidra-listed instruction bytes vs V295 FILE: %d sites, %d mismatch %s" % (len(GHIDRA), len(bad), bad))
print("0x28FA4 halfword %04x -> opcode field %#04x (subr=0x0C, add=0x0E); 0x29D76 %04x -> field %#04x imm %d (shl imm5=0x16)"
      % (u16(b5, 0x28FA4), (u16(b5, 0x28FA4) >> 5) & 0x3F, u16(b5, 0x29D76), (u16(b5, 0x29D76) >> 5) & 0x3F, u16(b5, 0x29D76) & 0x1F))

# ---- cells, as the code reads them (widths from the listing above) ---------------------------------------------
def rec(b, bank, n, sel=SEL):
    p = u32(b, bank + 4 * sel)
    return p, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]

def cells(b):
    c = dict(
        fb_a=s16(b, 0xC63E8), fb_b=u16(b, 0xC63EA), fb_clamp=u16(b, 0xC62E6),
        deadband=u16(b, 0xC62E4), ki=u16(b, 0xC63E6), i_clamp=u16(b, 0xC61BA),
        p_clamp=u16(b, 0xC61BC), d_clamp=u16(b, 0xC61B6), sum_clamp_u=u16(b, 0xC61BE), sum_clamp_s=s16(b, 0xC61BE),
        lag_a=s16(b, 0xC63EC), lag_b=u16(b, 0xC63EE), gate_arm=b[0xC64A3], gate_thr=s16(b, 0xC61B8),
        gain=s16(b, 0xC6CD0), t_clamp_u=u16(b, 0xC61B4), t_clamp_s=s16(b, 0xC61B4),
        idx_cl_pos=b[0xC64F0], idx_cl_neg=b[0xC64F1], flag_74e2=b[0xC64E2], ovr_cut=b[0xC64B8],
        e_shift=u16(b, 0x29D76) & 0x1F, fb_op={0x0C: "diff", 0x0E: "sum"}[(u16(b, 0x28FA4) >> 5) & 0x3F],
        pid_e_prev_lo=struct.unpack_from("<i", b, 0x29E68 + 2)[0], pid_e_prev_hi=struct.unpack_from("<i", b, 0x29E62 + 2)[0],
    )
    for nm, bank, n in (("map", 0xC9A88, 10), ("kp", 0xCB994, 5), ("kd", 0xCB7D4, 4)):
        p, X, Y = rec(b, bank, n)
        c[nm + "_rec"], c[nm + "_x"], c[nm + "_y"] = hex(p), X, Y
        c[nm + "_y_all_sel"] = sorted(set(tuple(rec(b, bank, n, s)[2]) for s in range(28)))
    return c

C5, C4 = cells(b5), cells(b4)
for k in C5:
    if k.endswith("_all_sel"):
        continue
    print("  %-14s V294 %-40s V295 %-40s %s" % (k, str(C4[k]), str(C5[k]), "" if C4[k] == C5[k] else "<-- DIFFERS"))
print("  kp Y over 28 selectors V295:", C5["kp_y_all_sel"])
print("  kd Y over 28 selectors V295:", C5["kd_y_all_sel"])
print("  map Y distinct over 28 selectors V295:", len(C5["map_y_all_sel"]))
# anchors: stock values at known cells (off-by-0x1000 guard)
print("  anchor stock fb_a 0xC63E8 = %d (expect 923), fb_b = %d (expect 1560), lag 0xC63EC/EE = %d/%d (expect 992/507)"
      % (s16(bs, 0xC63E8), u16(bs, 0xC63EA), s16(bs, 0xC63EC), u16(bs, 0xC63EE)))
json.dump(dict(sha=H, v295=C5, v294=C4, diff=[hex(i) for i in diff]), open(os.path.join(HERE, "a1_cells.json"), "w"), indent=1)
print("wrote a1_cells.json")
