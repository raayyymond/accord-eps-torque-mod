"""Branches INTO the Kd-LERP tail: does any path reach 0x29EE0 (E5b) without passing 0x29EDE (E5a, the Kd negation)?
Format III bcond (disp9) and Format V jr/jarl (disp22, even target) over the whole code region of V295.
POSITIVE CONTROL: the known 'br 0x29ede' at 0x29E9E and 0x29EB4 (Ghidra dry-run)."""
import struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
b = open(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
targets = {0x29EDE: [], 0x29EE0: [], 0x29EE2: [], 0x29EE4: [], 0x29D7E: [], 0x29D7A: [], 0x29D80: []}
for a in range(0x13000, 0xC0000, 2):
    h = struct.unpack_from("<H", b, a)[0]
    if (h >> 7) & 0xF == 0b1011:                              # Format III
        d = (((h >> 11) & 0x1F) << 4) | (((h >> 4) & 0x7) << 1)
        if d & 0x100: d -= 0x200
        t = a + d
        if t in targets: targets[t].append((hex(a), "bcond", h & 0xF))
    if (h >> 6) & 0x1F == 0x1E and a + 4 <= len(b):          # Format V jr/jarl
        h2 = struct.unpack_from("<H", b, a + 2)[0]
        if h2 & 1: continue
        d = ((h & 0x3F) << 16) | h2
        if d & 0x200000: d -= 0x400000
        t = a + d
        if t in targets: targets[t].append((hex(a), "jr" if (h >> 11) == 0 else "jarl r%d" % (h >> 11)))
for t, v in targets.items(): print(hex(t), v)
