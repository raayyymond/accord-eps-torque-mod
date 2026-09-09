"""
D1 RAM census v2 for V289 (advD) - CORRECTED per docs/traces/TRACE-2026-09-08...
  SECOND FINAL ADDENDUM: st.b/ld.b use disp=hw2 EXACTLY (both parities), opcodes 0x3A/0x38.
  bit-ops (set1/clr1/tst1/not1) opcode6==0x3E, reg1==4 for gp-direct base.
Target: gp-0x6c54 .. gp-0x6c29 (wider than the claimed-free 12-byte run gp-0x6c44..gp-0x6c39).
"""
import struct

PATH = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
img = open(PATH, "rb").read()
N = len(img)
GP = 0xFEDF8000
TARGET_DISPS = list(range(0x6c29, 0x6c55))
TARGET_ADDRS = set(GP - d for d in TARGET_DISPS)
addr_to_disp = {GP - d: d for d in TARGET_DISPS}
CAVE_LO, CAVE_HI = 0xC4BD6, 0xC4C8B

def u16(off): return img[off] | (img[off+1] << 8)
def s16(v): return v - 0x10000 if v & 0x8000 else v
def opfield(hw1): return (hw1 >> 5) & 0x3F
def reg1(hw1): return hw1 & 0x1F
def reg2(hw1): return (hw1 >> 11) & 0x1F

GP_REG = 4
hits = {k: [] for k in ['ld.b','st.b','ld.h','ld.w','ld.hu','st.h','st.w','bitops']}

for off in range(0, N - 4, 2):
    hw1 = u16(off)
    if reg1(hw1) != GP_REG:
        continue
    op = opfield(hw1)
    hw2 = u16(off + 2)
    if op == 0x38:   # ld.b, disp = hw2 exactly
        sdisp = s16(hw2)
        addr = (GP + sdisp) & 0xFFFFFFFF
        if addr in addr_to_disp:
            hits['ld.b'].append((off, addr_to_disp[addr], reg2(hw1)))
    elif op == 0x3A:  # st.b, disp = hw2 exactly
        sdisp = s16(hw2)
        addr = (GP + sdisp) & 0xFFFFFFFF
        if addr in addr_to_disp:
            hits['st.b'].append((off, addr_to_disp[addr], reg2(hw1)))
    elif op == 0x39:
        disp = hw2 & 0xFFFE
        sdisp = s16(disp)
        addr = (GP + sdisp) & 0xFFFFFFFF
        if addr in addr_to_disp:
            kind = 'ld.w' if (hw2 & 1) else 'ld.h'
            hits[kind].append((off, addr_to_disp[addr], reg2(hw1)))
    elif op == 0x3F:
        disp = hw2 & 0xFFFE
        sdisp = s16(disp)
        addr = (GP + sdisp) & 0xFFFFFFFF
        if addr in addr_to_disp:
            hits['ld.hu'].append((off, addr_to_disp[addr], reg2(hw1)))
    elif op == 0x3B:
        disp = hw2 & 0xFFFE
        sdisp = s16(disp)
        addr = (GP + sdisp) & 0xFFFFFFFF
        if addr in addr_to_disp:
            kind = 'st.w' if (hw2 & 1) else 'st.h'
            hits[kind].append((off, addr_to_disp[addr], reg2(hw1)))
    elif op == 0x3E:  # bit ops, gp-direct base
        # check hw2 both as signed disp and as raw unsigned disp (method per the addendum)
        for interp, sdisp in (('signed', s16(hw2)), ('raw', hw2)):
            addr = (GP + sdisp) & 0xFFFFFFFF
            if addr in addr_to_disp:
                hits['bitops'].append((off, addr_to_disp[addr], reg2(hw1), interp))

print("=== D1 RAM CENSUS v2 (corrected st.b/ld.b/bitops): gp-0x6c54..gp-0x6c29 ===")
total = 0
for kind, lst in hits.items():
    print(f"\n--- {kind}: {len(lst)} hit(s) ---")
    total += len(lst)
    for h in lst[:60]:
        off = h[0]
        tag = " [INSIDE CAVE/TAIL]" if CAVE_LO <= off <= CAVE_HI else ""
        print(f"    off={hex(off)} disp=gp-0x{h[1]:x} rest={h[2:]}{tag}")
print(f"\nTOTAL: {total}")

print("\n=== Focus: exact claimed-free run gp-0x6c44..gp-0x6c39, hits OUTSIDE cave/tail ===")
core = set(range(0x6c39, 0x6c45))
found_outside = False
for kind, lst in hits.items():
    for h in lst:
        off, disp = h[0], h[1]
        if disp in core and not (CAVE_LO <= off <= CAVE_HI):
            found_outside = True
            print(kind, hex(off), 'gp-0x%x' % disp, h)
if not found_outside:
    print("NONE — the exact 12-byte run has zero hits outside the cave/tail under this corrected scanner.")
