"""ADV-bytes (p-gain) step 2: independent raw LE scan for every access to the cells the Kp edit changes the VALUE of:
the published PID cells gp-0x6b2e (S), -0x6b30 (yr prev), -0x6b32 (P), -0x6b34 (raw sum), -0x6b36 (D), the lane torque
gp-0x6b38 (T, the 427 tap), its forward copy gp-0x6b3c / clamped gp-0x6b3a, and the idx publish gp-0x697a / gp-0x674b.
Also 6-byte disp23 forms and absolute/disp23 reads of 0xCB994 / the Kp records. Positive controls must be found."""
import os, struct
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = ROOT + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
b = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", b, a)[0]
GP, TP = 4, 5
PID_LO, PID_HI = 0x28EA6, 0x2A30E
TWIN_LO, TWIN_HI = 0x2A30E, 0x2B422

def fmt7(target_disp, base=GP):
    """4-byte Format VII/VIII accesses with disp16 == target (byte-exact, incl. hw2 bit0 and ld.bu bit-5 parity)."""
    lo = target_disp & 0xFFFF
    out = []
    for off in range(0x13000, 0xC0000, 2):
        hw1, hw2 = u16(off), u16(off + 2)
        if (hw1 & 0x1F) != base:
            continue
        op6 = (hw1 >> 5) & 0x3F
        k = None
        if op6 == 0x38 and hw2 == lo: k = "ld.b"
        elif op6 == 0x39 and (hw2 & 0xFFFE) == lo: k = "ld.w" if hw2 & 1 else "ld.h"
        elif op6 == 0x3A and hw2 == lo: k = "st.b"
        elif op6 == 0x3B and (hw2 & 0xFFFE) == lo: k = "st.w" if hw2 & 1 else "st.h"
        elif op6 == 0x3F and (hw2 & 1) and (hw2 & 0xFFFE) == lo: k = "ld.hu"
        elif op6 in (0x3C, 0x3D) and (hw2 & 1) and ((hw2 & 0xFFFE) | (op6 & 1)) == lo: k = "ld.bu"
        elif op6 == 0x3E and hw2 == lo: k = ("set1", "not1", "clr1", "tst1")[hw1 >> 14]
        if k:
            out.append((off, k))
    return out

def fmt14(target_disp, base=None):
    """6-byte extended ld/st disp23 (V850E2): hw1 = 0000 0111 10x0 reg1 / 0000 0111 101x reg1 ; disp split hw2[10:4]/hw3."""
    out = []
    for off in range(0x13000, 0xC0000, 2):
        hw1 = u16(off)
        if (hw1 & 0xFFC0) not in (0x0780, 0x07A0) :
            continue
        if base is not None and (hw1 & 0x1F) != base:
            continue
        hw2, hw3 = u16(off + 2), u16(off + 4)
        d = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
        if d & 0x400000: d -= 0x800000
        if d == target_disp or (d & ~1) == target_disp:
            out.append((off, "fmt14 base r%d hw1 %04x hw2 %04x" % (hw1 & 0x1F, hw1, hw2)))
    return out

def where(o):
    return "PID" if PID_LO <= o < PID_HI else ("TWIN" if TWIN_LO <= o < TWIN_HI else "ELSEWHERE")

cells = [-0x6b2e, -0x6b30, -0x6b32, -0x6b34, -0x6b36, -0x6b38, -0x6b3a, -0x6b3c, -0x697a, -0x674b]
for c in cells:
    hits = fmt7(c) + fmt7(c + 1)
    six = fmt14(c, GP) + fmt14(c + 1, GP)
    rd = [(hex(o), k, where(o)) for o, k in hits if not k.startswith("st")]
    wr = [(hex(o), k, where(o)) for o, k in hits if k.startswith("st")]
    print(f"gp{c:+#x}: READERS {rd}\n          writers {wr}\n          6-byte {[(hex(o), k, where(o)) for o, k in six]}")

# positive controls
ctl6 = fmt14(-0x6752, GP)
print("CONTROL 6-byte gp-0x6752 (expect 0x48e56):", [hex(o) for o, _ in ctl6])
ctl = [hex(o) for o, k in fmt7(-0x6b32) if k == "st.h" and PID_LO <= o < PID_HI]
print("CONTROL st.h gp-0x6b32 inside the PID (the P publish):", ctl)
print("CONTROL tp+0x71bc P-clamp reads in the PID (expect 0x29e3a/44/4a/58):", [hex(o) for o, k in fmt7(0x71BC, TP) if PID_LO <= o < PID_HI])
# disp23 direct reads of 0xCB994 or any Kp record (r0 base, and tp base)
recs = [struct.unpack_from("<I", b, 0xCB994 + 4 * s)[0] for s in range(28)]
tgt = [0xCB994 + 4 * s for s in range(28)] + [r + k for r in recs for k in range(0, 0x16, 2)]
f14all = []
for off in range(0x13000, 0xC0000, 2):
    hw1 = u16(off)
    if (hw1 & 0xFFC0) not in (0x0780, 0x07A0):
        continue
    hw2, hw3 = u16(off + 2), u16(off + 4)
    d = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
    if d & 0x400000: d -= 0x800000
    base = hw1 & 0x1F
    for cand in (d, d & ~1):
        a = cand if base == 0 else (TP_ABS := 0xBF000) + cand if base == TP else None
        if a is not None and a in tgt:
            f14all.append((hex(off), base, hex(a)))
print("6-byte disp23 reads of the Kp table or a Kp record (r0 or tp base):", f14all)
# tp disp16 cannot reach: 0xCB994 - 0xBF000 =
print("tp offset of 0xCB994 = %#x (disp16 reach is +-0x8000)" % (0xCB994 - 0xBF000))
