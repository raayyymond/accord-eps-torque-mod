"""V292 cave design — raw-Python census on the V291 image.

Three independent questions, each positively controlled before its null is trusted:
  A. Does ANY branch land inside the displaced/skipped span [0x28F8E, 0x28FA2)?
  B. Are gp-0x6D74 and gp-0x6D72 free of every access form, on the V291 image?
  C. What do those cells boot to?
"""
import struct, sys, os

ROOT = r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"
V291 = os.path.join(ROOT, "_v291c10_V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
                          "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
b = open(V291, "rb").read()
START, END = 0x13000, 0xC5000       # the code block
GP = 0xFEDF8000

u16 = lambda p: struct.unpack_from("<H", b, p)[0]
u32 = lambda p: struct.unpack_from("<I", b, p)[0]


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


# ===================================================================================================
# A.  Branch-target scan.  Format V (jr/jarl, disp22) + Format III (Bcond, disp9).
#     TRAPS APPLIED:  Format-V opcode field 0x1E collides with `prepare`; reject ODD targets;
#     opcode field 0x3C/0x3D and 0x3F are shared with loads -> hw2 bit 0 == 1 marks the LOAD, so a
#     Format-V candidate with hw2 bit 0 set is NOT a branch.
# ===================================================================================================
def branch_targets():
    tgt = {}
    for a in range(START, END - 4, 2):
        hw1 = u16(a)
        if hw1 == 0xFFFF:
            continue
        # ---- Format V: jr / jarl, disp22 -----------------------------------------------------
        if ((hw1 >> 6) & 0x1F) == 0x1E:
            hw2 = u16(a + 2)
            if (hw2 & 1) == 0:                      # hw2 bit0 = 1 would be the 6-byte load form
                d = sx(((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE), 22)
                t = a + d
                if t % 2 == 0 and START <= t < END:  # reject odd targets
                    tgt.setdefault(t, []).append(("jarl" if (hw1 >> 11) else "jr", a))
        # ---- Format III: Bcond, disp9 --------------------------------------------------------
        if (hw1 & 0x0780) == 0x0580:
            d = sx((((hw1 >> 11) & 0x1F) << 4) | ((hw1 >> 4) & 0x7), 9) * 2
            t = a + d
            if START <= t < END:
                tgt.setdefault(t, []).append(("bcond", a))
    return tgt


T = branch_targets()

# ---- POSITIVE CONTROLS: targets this scanner MUST find, from Ghidra's own listing ----------------
CTRL = [
    (0x290B0, "jr",   0x28F62),   # BAIL 4      (Ghidra: jr 0x000290b0 @ 0x28f62, bytes 80074e01)
    (0x28F66, "bcond", 0x28F60),  # bne 0x28f66 @ 0x28f60
    (0x28F82, "bcond", 0x28F76),  # bne 0x28f82 @ 0x28f76
    (0x28F86, "bcond", 0x28F80),  # br  0x28f86 @ 0x28f80
    (0x28FB2, "bcond", 0x28FAC),  # ble 0x28fb2 @ 0x28fac
    (0x28FBE, "bcond", 0x28FB0),  # br  0x28fbe @ 0x28fb0
    (0x28FBE, "bcond", 0x28FB6),  # bge 0x28fbe @ 0x28fb6
    (0x28FC8, "bcond", 0x28FC4),  # bp  0x28fc8 @ 0x28fc4
    (0x2A164, "jr",   0x29A5C),   # SKIP 1
    (0x2A164, "jr",   0x29A64),   # SKIP 2
    (0x2A0C6, "jr",   0x29A70),   # SKIP 3
    (0x28EA6, "jarl", 0x22522),   # the function's own caller
]
ctrl_ok = 0
for t, kind, src in CTRL:
    hit = any(k == kind and s == src for k, s in T.get(t, []))
    ctrl_ok += hit
    if not hit:
        print(f"  CONTROL FAIL: {kind} {src:#x} -> {t:#x} NOT FOUND")
print(f"A. branch scanner positive control: {ctrl_ok}/{len(CTRL)} PASS   "
      f"({len(T)} distinct targets in [{START:#x},{END:#x}))")
assert ctrl_ok == len(CTRL), "scanner is broken; its nulls are worthless"

SPAN = range(0x28F8E, 0x28FA2)
hits = {t: T[t] for t in SPAN if t in T}
print(f"A. branch targets inside the displaced/skipped span [0x28F8E,0x28FA2): "
      f"{len(hits)}  {hits if hits else '-> NONE (safe to displace)'}")

print(f"A. is 0x28FA2 (the return point) a branch target from elsewhere? "
      f"{T.get(0x28FA2, 'no')}")

# ===================================================================================================
# B.  gp-relative access census on the two candidate remainder cells.
#     9 forms: 4-byte ld.b/ld.h/ld.w/ld.bu/ld.hu/st.b/st.h/st.w  +  6-byte extended-disp
#     + absolute LE32 pointer + movhi/movea pair.  Byte-granular (a halfword access to gp-0x6D74
#     touches bytes 0x..8C and 0x..8D, so a *byte* access to either must also count).
# ===================================================================================================
def gp_accesses():
    """Return {byte_address: [(pc, form, width)]} for every gp-relative access in the code block."""
    acc = {}

    def note(addr, n, pc, form):
        for k in range(n):
            acc.setdefault(addr + k, []).append((pc, form))

    for a in range(START, END - 6, 2):
        hw1 = u16(a)
        op = (hw1 >> 5) & 0x3F
        reg1 = hw1 & 0x1F
        # ---- 4-byte disp16 forms, gp base (reg1 == 4) ------------------------------------------
        if reg1 == 4 and 0x38 <= op <= 0x3F:
            hw2 = u16(a + 2)
            if op == 0x38:                                   # ld.b
                disp, n, f = sx(hw2, 16), 1, "ld.b"
            elif op == 0x3A:                                 # st.b
                disp, n, f = sx(hw2, 16), 1, "st.b"
            elif op in (0x39, 0x3B):                         # ld.h/ld.w , st.h/st.w
                w = (hw2 & 1)
                disp, n = sx(hw2 & 0xFFFE, 16), (4 if w else 2)
                f = ("ld." if op == 0x39 else "st.") + ("w" if w else "h")
            elif op in (0x3C, 0x3D):                         # ld.bu  (disp bit0 in hw1 bit5!)
                if (hw2 & 1) == 0:
                    continue                                 # hw2 bit0==0 -> Format-V jr/jarl
                disp, n, f = sx((hw2 & 0xFFFE) | (op & 1), 16), 1, "ld.bu"
            else:                                            # 0x3E/0x3F ld.hu
                if (hw2 & 1) == 0:
                    continue                                 # mul / setfcc, not a load
                disp, n, f = sx(hw2 & 0xFFFE, 16), 2, "ld.hu"
            note(GP + disp, n, a, f)
        # ---- 6-byte extended-displacement form --------------------------------------------------
        if (hw1 & 0xFFE0) in (0x0780, 0x07A0) and reg1 == 4:
            hw2, hw3 = u16(a + 2), u16(a + 4)
            disp = (sx(hw3, 16) << 7) | ((hw2 >> 4) & 0x7F)
            note(GP + disp, 4, a, "ext6")
    return acc


ACC = gp_accesses()

# ---- POSITIVE CONTROLS on the access scanner, from Ghidra's own listing --------------------------
GCTRL = [
    (GP - 0x3D30, 0x28F7C, "ld.w"),    # 24 d7 d1 c2
    (GP - 0x3D30, 0x28FA8, "st.w"),    # 64 4f d1 c2
    (GP - 0x3D34, 0x28F78, "ld.w"),
    (GP - 0x3D2C, 0x28F66, "ld.bu"),   # 84 4f d5 c2  (ODD displacement -> op 0x3D)
    (GP - 0x674E, 0x28FC8, "ld.bu"),   # 84 67 b3 98
    (GP - 0x6A98, 0x1982E, "ld.hu"),   # e4 6f 69 95
    (GP - 0x6A56, 0x28F4C, "ld.h"),    # 24 3f aa 95
    (GP - 0x6752, 0x48E56, "ext6"),    # the 6-byte form control
]
gok = 0
for addr, pc, form in GCTRL:
    hit = any(p == pc and f == form for p, f in ACC.get(addr, []))
    gok += hit
    if not hit:
        print(f"  CONTROL FAIL: {form} @{pc:#x} -> {addr:#x} NOT FOUND; got {ACC.get(addr)}")
print(f"B. gp-access scanner positive control: {gok}/{len(GCTRL)} PASS   "
      f"({len(ACC)} distinct gp bytes touched image-wide)")
assert gok == len(GCTRL), "scanner is broken; its nulls are worthless"

# ---- absolute-pointer and movhi/movea forms -------------------------------------------------------
def abs_ptr_hits(lo, hi):
    out = []
    for a in range(START, END - 4):
        v = u32(a)
        if lo <= v <= hi:
            out.append((a, v))
    return out


def movhi_movea_hits(lo, hi):
    """movhi imm16, reg1, reg2  (op 0x32) building 0xFEDF____, followed within 16 B by a movea
    (op 0x31) whose sign-extended imm lands the effective address in [lo,hi]."""
    out = []
    for a in range(START, END - 4, 2):
        hw1 = u16(a)
        if ((hw1 >> 5) & 0x3F) != 0x32:
            continue
        hi16 = u16(a + 2)
        dst = (hw1 >> 11) & 0x1F
        base = hi16 << 16
        if not (0xFED00000 <= base <= 0xFEE00000):
            continue
        for c in range(a + 4, min(a + 20, END - 4), 2):
            h = u16(c)
            if ((h >> 5) & 0x3F) == 0x31 and (h & 0x1F) == dst:
                ea = (base + sx(u16(c + 2), 16)) & 0xFFFFFFFF
                if lo <= ea <= hi:
                    out.append((a, c, ea))
    return out


CAND = {"rem_b gp-0x6D74": GP - 0x6D74, "rem_a gp-0x6D72": GP - 0x6D72}
RUN_LO, RUN_HI = GP - 0x6D74, GP - 0x6D2D          # the certified 72-byte run
print(f"B. certified free run: gp-0x6D74..gp-0x6D2D = {RUN_LO:#010x}..{RUN_HI:#010x} "
      f"({RUN_HI - RUN_LO + 1} bytes)")
for name, addr in CAND.items():
    touched = {k: ACC[k] for k in (addr, addr + 1) if k in ACC}
    print(f"   {name} = {addr:#010x}: 4/6-byte gp-form accesses on either byte -> "
          f"{touched if touched else 'NONE'}")
run_touched = {k: ACC[k] for k in range(RUN_LO, RUN_HI + 1) if k in ACC}
print(f"   whole run, any gp form: {len(run_touched)} touched bytes "
      f"{run_touched if run_touched else '-> NONE'}")
print(f"   absolute LE32 pointers into the run: {abs_ptr_hits(RUN_LO, RUN_HI)}")
print(f"   movhi/movea pairs into the run:      {movhi_movea_hits(RUN_LO, RUN_HI)}")
# control the two indirect scanners so their nulls mean something
print(f"   [control] abs-ptr scanner finds 0xCB844 (imm32 @0x28FCE): "
      f"{[a for a, v in abs_ptr_hits(0xCB844, 0xCB844)][:4]}")
print(f"   [control] movhi/movea scanner, whole 0xFEDFxxxx window: "
      f"{len(movhi_movea_hits(0xFEDF0000, 0xFEDFFFFF))} pairs found image-wide")

# ===================================================================================================
# C.  Boot value.  The .data initialiser image maps 0xFEDF11B0 -> flash 0x86260 (prior trace).
#     Anchor the mapping on a cell whose boot value is independently known, then read ours.
# ===================================================================================================
DATA_RAM0, DATA_FLASH0 = 0xFEDF11B0, 0x86260
for name, addr in CAND.items():
    off = DATA_FLASH0 + (addr - DATA_RAM0)
    print(f"C. {name}: .data source flash {off:#07x} = {b[off:off+2].hex()} "
          f"(u16 {struct.unpack_from('<H', b, off)[0]})")
off_lo = DATA_FLASH0 + (RUN_LO - DATA_RAM0)
print(f"C. whole run .data source [{off_lo:#07x},{off_lo + 72:#07x}) = "
      f"{b[off_lo:off_lo + 72].hex()}")
print(f"C. [control] gp-0x6AB0 (known NON-zero .data, 0x02880288): "
      f"{b[DATA_FLASH0 + (GP - 0x6AB0 - DATA_RAM0):][:8].hex()}")
