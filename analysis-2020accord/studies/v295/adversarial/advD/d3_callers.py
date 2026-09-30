"""ADV-D step 3: are the TWIN routines at 0x2A892 (output lag + T writer, stock gain 0x746C) and FUN_0002a93a (twin PID,
reads gp-0x6a34, writes P/D/S/E) reachable?  Raw scan on the V295 image for every control transfer INTO them:
  Format V   jarl/jr disp22   (hw1>>6)&0x1F == 0x1E, hw2 bit0 == 0, target = i + sext22
  Format VI  jarl/jr disp32   hw1 & 0xFFE0 == 0x02E0 ; jmp disp32[reg1]  hw1 & 0xFFE0 == 0x06E0 (absolute-ish, reported)
  Format III bcond disp9      (hw1 & 0x0780) == 0x0580
  LE32 constant == target (function-pointer tables / mov imm32 + jmp [reg])
Positive controls: 0x22522 -> 0x28EA6, 0x22530 -> 0x2B422, 0x22514 -> 0x1CBA6 (all visible in the Ghidra listing).
"""
import struct, hashlib
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
B = open(V295, "rb").read()
assert hashlib.sha256(B).hexdigest().startswith("5c044d65")
u16 = lambda a: B[a] | (B[a + 1] << 8)
def sx(v, n):
    v &= (1 << n) - 1
    return v - (1 << n) if v >> (n - 1) else v
LO, HI = 0x13000, 0xC8000
refs = []
for i in range(LO, HI, 2):
    hw1, hw2 = u16(i), u16(i + 2)
    if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0:
        refs.append((i, "disp22 %s r%d" % ("jarl" if hw1 >> 11 else "jr", hw1 >> 11), (i + sx(((hw1 & 0x3F) << 16) | hw2, 22)) & 0xFFFFFFFF))
    if (hw1 & 0xFFE0) == 0x02E0:
        d = hw2 | (u16(i + 4) << 16)
        refs.append((i, "disp32 jarl/jr r%d" % (hw1 & 0x1F), (i + sx(d, 32)) & 0xFFFFFFFF))
    if (hw1 & 0x0780) == 0x0580:
        d = sx((((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 7) << 1), 9)
        refs.append((i, "bcond", (i + d) & 0xFFFFFFFF))
ctl = [(0x22522, 0x28EA6), (0x22530, 0x2B422), (0x22514, 0x1CBA6)]
for src, dst in ctl:
    ok = any(r[0] == src and r[2] == dst for r in refs)
    print("CONTROL 0x%X -> 0x%X found: %s" % (src, dst, ok))
    assert ok
TW = [("twin output-lag/T writer", 0x2A892, 0x2A93A), ("twin PID FUN_0002a93a", 0x2A93A, 0x2B0A0)]
for nm, a, b in TW:
    ins = [r for r in refs if a <= r[2] < b and not (a <= r[0] < b)]
    calls = [r for r in ins if not r[1].startswith("bcond")]
    br = [r for r in ins if r[1].startswith("bcond")]
    print("%s [0x%X,0x%X): calls/jumps in from outside: %s ; bcond in from outside: %s" % (
        nm, a, b, [(hex(r[0]), r[1], hex(r[2])) for r in calls], [(hex(r[0]), hex(r[2])) for r in br]))
    ptr = [i for i in range(0, len(B) - 4, 2) if a <= struct.unpack_from("<I", B, i)[0] < b]
    print("   LE32 constants pointing inside: %s" % [hex(p) for p in ptr][:40])
# where does FUN_0002a93a end? report the first 'jmp lp' / dispose after 0x2A93A
for i in range(0x2A93A, 0x2B200, 2):
    if u16(i) == 0x007F or (u16(i) & 0xFFC0) == 0x0640:
        print("first return-ish after 0x2A93A at 0x%X (hw 0x%04X)" % (i, u16(i)))
        break
