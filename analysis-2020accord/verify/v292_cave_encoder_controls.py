"""V292 ENCODER CONTROLS -- every form the cave uses, proven against a STOCK instance with the same
hw1/hw2 pattern that Ghidra itself decodes, plus a whole-window byte-identical re-encode."""
import os, sys, struct
GR = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/grind"
sys.path.insert(0, GR)
import v292_cave_mirror as M

ROOT = r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"
STOCK = open(os.path.join(ROOT, "stock_fw_dump", "code.bin"), "rb").read()
V291 = open(os.path.join(ROOT, "_v291c10_V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
                              "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
                              "_plain_image.bin"), "rb").read()
R0, R7, R9, R13, R14, R16, R26, GP, TP = 0, 7, 9, 13, 14, 16, 26, 4, 5
ok = fail = 0


def ck(cond, msg):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {msg}")
    else:
        fail += 1
        print(f"  FAIL  {msg}")


print("=" * 112)
print("1.  FORM-BY-FORM CONTROL -- my encoder vs a STOCK instance Ghidra decodes (address, Ghidra text)")
print("=" * 112)
CASES = [
    (M.i_mul(R16, R7),              0x28F8E, 4, "mul   r16, r7, r0        @0x28F8E  (the displaced instruction itself)"),
    (M.i_mul(R26, R9),              0x28F92, 4, "mul   r26, r9, r0        @0x28F92"),
    (M.i_f2("sar", 10, R7),         0x28F9A, 2, "sar   0xa, r7            @0x28F9A"),
    (M.i_f2("sar", 10, R9),         0x28FA0, 2, "sar   0xa, r9            @0x28FA0"),
    (M.i_ld_hu(0x72E6, TP, R13),    0x28F96, 4, "ld.hu 0x72e6, tp, r13    @0x28F96"),
    (M.i_ld_hu(0x72E6, TP, R14),    0x28F9C, 4, "ld.hu 0x72e6, tp, r14    @0x28F9C"),
    (M.i_f1("add", R13, R7),        0x17B74, 2, "add   r13, r7            @0x17B74  (pins reg1=13, reg2=7)"),
    (M.i_f1("add", R7, R9),         0x28FA2, 2, "add   r7, r9             @0x28FA2  (pins reg2=9)"),
    (M.i_ld_hu(-0x6A98, GP, R13),   0x1982E, 4, "ld.hu -0x6a98, gp, r13   @0x1982E  (pins ld.hu + gp base + r13)"),
    (M.i_st_h(R13, -0x3EE4, GP),    0x19C84, 4, "st.h  r13, -0x3ee4, gp   @0x19C84  (pins st.h + gp base + r13)"),
    (M.i_andi(0x2, R7, R13),        0xAD7E,  4, "andi  0x2, r7, r13       @0xAD7E   (pins andi, reg1=7, reg2=13)"),
    (M.i_andi(0x3, R13, 10),        0x2378,  4, "andi  0x3, r13, r10      @0x2378   (pins andi reg1 field = 13)"),
]
for enc, addr, n, label in CASES:
    ck(enc == STOCK[addr:addr + n], f"{label}   enc {enc.hex(' ')}  img {STOCK[addr:addr+n].hex(' ')}")

print()
print("  DERIVED forms -- each field independently pinned by two controls above:")
for enc, label in [(M.i_f1("add", R13, R9), "add   r13,r9       (reg1=13 by 0x17B74, reg2=9 by 0x28FA2)"),
                   (M.i_andi(0x3FF, R7, R13), "andi  0x3ff,r7,r13 (hw1 by 0xAD7E; only the imm16 differs)"),
                   (M.i_andi(0x3FF, R9, R13), "andi  0x3ff,r9,r13 (reg1 field by 0x2378, reg2 by 0xAD7E)"),
                   (M.i_ld_hu(-0x6D74, GP, R13), "ld.hu -0x6d74,gp,r13 (hw1 by 0x1982E; disp|1 per the ld.hu rule)"),
                   (M.i_ld_hu(-0x6D72, GP, R13), "ld.hu -0x6d72,gp,r13"),
                   (M.i_st_h(R13, -0x6D74, GP), "st.h  r13,-0x6d74,gp (hw1 by 0x19C84; disp EVEN -> st.h not st.w)"),
                   (M.i_st_h(R13, -0x6D72, GP), "st.h  r13,-0x6d72,gp")]:
    print(f"        {enc.hex(' '):<14s} {label}")

print()
print("=" * 112)
print("2.  WHOLE-WINDOW CONTROL -- re-encode stock 0x28F86-0x28FAC byte-identically")
print("=" * 112)
win = (M.i_ld_hu(0x73EA, TP, R16)            # 28F86  ld.hu 0x73ea,tp,r16   (b)
       + M.i_f67("ld.h", TP, R9, 0x73E8)     # 28F8A  ld.h  0x73e8,tp,r9    (a)  EVEN disp -> ld.h
       + M.i_mul(R16, R7)                    # 28F8E
       + M.i_mul(R26, R9)                    # 28F92
       + M.i_ld_hu(0x72E6, TP, R13)          # 28F96
       + M.i_f2("sar", 10, R7)               # 28F9A
       + M.i_ld_hu(0x72E6, TP, R14)          # 28F9C
       + M.i_f2("sar", 10, R9)               # 28FA0
       + M.i_f1("add", R7, R9)               # 28FA2
       + M.i_f1("add", R9, R26)              # 28FA4
       + M.i_f1("cmp", R13, R26)             # 28FA6
       + M.i_f67("st.h", GP, R9, (-0x3D30 & 0xFFFE) | 1))   # 28FA8 st.w r9,-0x3d30,gp
ck(win == STOCK[0x28F86:0x28FAC],
   f"0x28F86-0x28FAB ({len(win)} B) re-encodes byte-identically: ld.hu-tp/ld.h-tp/mul/sar/add/cmp/st.w")
print(f"        enc {win.hex(' ')}")
print(f"        img {STOCK[0x28F86:0x28FAC].hex(' ')}")

print()
print("=" * 112)
print("3.  FORMAT-V disp22 ROUND TRIP over every jr/jarl site in the code block")
print("=" * 112)
n = good = 0
for a in range(0x13000, 0xC4FFC - 6, 2):
    hw1, hw2 = struct.unpack_from("<HH", STOCK, a)
    if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and hw1 != 0xFFFF:
        d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
        d -= (1 << 22) if d & (1 << 21) else 0
        lnk = hw1 >> 11
        if lnk:
            continue                      # jarl: encoder below is jr-only (lnk = 0)
        n += 1
        good += (M.i_jr(a, a + d) == STOCK[a:a + 4])
ck(good == n and n > 2000, f"Format-V `jr` round trip on all {n} jr sites ({good} match)")

print()
print("=" * 112)
print("4.  THE HOOK AND THE CAVE, against the V291 IMAGE (not stock)")
print("=" * 112)
hb, cb, listing = M.build_cave()
ck(V291[M.HOOK:M.HOOK + 4] == bytes.fromhex("f03f2002"),
   f"V291 0x{M.HOOK:05X} is still the stock `mul r16,r7,r0` (f0 3f 20 02) -- the hook site is untouched")
ck(all(c == 0xFF for c in V291[M.CAVE:M.CAVE + len(cb) + 16]),
   f"V291 0x{M.CAVE:05X}..0x{M.CAVE+len(cb)+16:05X} is virgin 0xFF ({len(cb)} B cave + 16 B margin)")
ck(all(c == 0xFF for c in V291[0xC4BD8:0xC4FF0]),
   "V291 0xC4BD8..0xC4FF0 (1048 B) is all 0xFF -- the 0x14A cave ends at 0xC4BD8, V289's notch cave is ABSENT")
ck(V291[0xC4FF0:0xC4FFC].hex() == "010101010000c60013 00b200".replace(" ", ""),
   f"the 12-byte structure at 0xC4FF0 is untouched: {V291[0xC4FF0:0xC4FFC].hex(' ')}")
d_hook = M.CAVE - M.HOOK
d_ret = M.RETURN_TO - (M.CAVE + len(cb) - 4)
ck(abs(d_hook) < (1 << 21) and abs(d_ret) < (1 << 21),
   f"both jr displacements are in disp22 range: hook {d_hook:+#x}, return {d_ret:+#x}")
print()
print(f"  HOOK  0x{M.HOOK:05X}  {hb.hex(' ')}   jr 0x{M.CAVE:05X}")
for pc, by, mn, cm in listing:
    print(f"  0x{pc:05X}  {by.hex(' '):<14s} {mn:<24s} ; {cm}")
print(f"  cave {len(cb)} bytes, {len(listing)} instructions; occupies 0x{M.CAVE:05X}-0x{M.CAVE+len(cb)-1:05X}")

print()
print("=" * 112)
print(f"ENCODER CONTROLS: {ok} PASS, {fail} FAIL")
print("=" * 112)
sys.exit(1 if fail else 0)
