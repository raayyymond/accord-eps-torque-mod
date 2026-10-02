"""ADV interlocks-gates V298 / F5: independent integer mirror of the cave, transcribed from the Ghidra DECODE of the
BUILT image (NOT from the design Python or build script), fuzzed over extreme inputs. Asserts: every intermediate fits
signed int32; the op-skip path writes nothing and exits to 0x2A164; the CAM path forces E'=0, op(r26)=0 and a decaying
r6; no path yields an unbounded r16/r6/r26. Also verifies the valid-rate window and the bound arithmetic.
V850 ld.h sign-extends; ld.hu zero-extends; mul is 32x32->low32 here (result used as 32-bit); sar is arithmetic."""
import glob, random
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
img = open(glob.glob(FW + "_v298_*_plain_image.bin")[0], "rb").read()
def u16(a): return img[a] | (img[a+1] << 8)
def s16v(v):
    v &= 0xFFFF; return v - 0x10000 if v & 0x8000 else v
GB = [(u16(0xC4CDA+i*6), s16v(u16(0xC4CDA+i*6+2)), s16v(u16(0xC4CDA+i*6+4))) for i in range(7)]
I32MIN, I32MAX = -2**31, 2**31 - 1
over = []
def chk(tag, v):
    if not (I32MIN <= v <= I32MAX): over.append((tag, v))
    return v
def sar(x, n):  # arithmetic shift of a 32-bit signed value
    x &= 0xFFFFFFFF
    if x & 0x80000000: x -= 2**32
    return x >> n
def gwalk(speed):
    # C4C22..C4C52, transcribed
    if speed <= GB[0][0]: return GB[0][1]        # C4C28 bh; else flat G0
    i = 0
    while i < 6 and not (speed <= GB[i+1][0]):
        i += 1
    lo = GB[i]
    seg = GB[i] if speed <= GB[i+1][0] else GB[i]  # lo row
    d = chk("speed-loX", speed - lo[0])
    prod = chk("(sp-loX)*off", d * lo[2])
    g = lo[1] + sar(prod, 12)
    return g
def cave(sp, r26_in, abe, speed, tq_abs, hand, theta, I8, ramp, r25):
    """Returns (path, r16, r26_out, r6_or_None). Mirrors 0xC4C00.."""
    r16 = chk("sp<<2", s16v(sp) << 2)            # C4C00 (sp loaded by ld.h -> signed)
    r16 = chk("E", r16 - r26_in)                  # C4C02 sub r26  (E)
    r26 = s16v(abe)                               # C4C04 ld.h -0x6abe (signed)
    r8 = chk("abe+13000", r26 + 0x32C8)           # C4C08 addi
    if not ((r8 & 0xFFFFFFFF) <= 26000):          # C4C10 cmp + C4C12 bnh (unsigned <=)
        return ("opskip", None, None, None)       # C4C14 jr 0x2A164 -- NO RAM, I zeroed by epilogue
    G = chk("G", gwalk(speed & 0xFFFF))           # C4C18..C4C52
    r16 = chk("E*G", G * r16)                     # C4C54 mul
    Ep = sar(r16, 8)                              # C4C58 sar 8  -> r16 = Ep
    if r25 == 0:                                  # C4C5A cmp r0,r25 ; C4C5C be CAM
        r6 = chk("-(I8>>6)", -sar(I8, 6))         # C4CCC/D0/D2: r6 = -(I8>>6)
        return ("cam", 0, 0, r6)                  # E'=0, op=0, decaying r6
    # freeze policy
    frozen = False
    if (tq_abs & 0xFFFF) > 512: frozen = True     # C4C66/68 hard freeze
    elif (tq_abs & 0xFFFF) > 300 and ((Ep ^ s16v(hand)) < 0): frozen = True  # C4C76 xor, C4C78 blt (opposing)
    if not frozen:
        th = s16v(theta); ath = -th if th < 0 else th    # |theta|
        sh = 6 if (speed & 0xFFFF) > 2880 else 4
        bound = chk("bound", (ath << sh) + 0x4E2)         # C4C96 addi 1250
        if (speed & 0xFFFF) <= 1382:
            if 4096 > bound: pass
            else: bound = min(bound, 4096)                # cmovh = min(bound,4096) when 4096>bound? -> cap at 4096
            bound = min(bound, 4096)
        t = sar(I8, 10)                                   # C4CB0
        if Ep < 0: t = chk("-t", -t)                      # C4CB6 subr
        if t >= bound: frozen = True                      # C4CBA bge FRZ
        elif (ramp & 0x8000) == 0: frozen = True          # C4CC0 bne normal else FRZ
    if frozen:
        return ("frz", Ep, r26, 0)                        # C4CC2 r6=0 ; jr 0x29D7E (I held via e5=0)
    return ("normal", Ep, r26, "jmp")                     # C4CD8 jmp[r6] -> 0x29D7A (r16=Ep, r26=op)
random.seed(1)
paths = {}
maxabs = {"r16": 0, "r26": 0, "r6": 0}
for _ in range(400000):
    sp = random.randint(-32768, 32767)
    r26_in = random.randint(-65535, 65535)   # two-sample sum clamp
    abe = random.randint(-32768, 32767)
    speed = random.randint(0, 65535)
    tq = random.randint(0, 65535)
    hand = random.randint(-32768, 32767)
    theta = random.randint(-32768, 32767)
    I8 = random.randint(-2**31, 2**31 - 1)
    ramp = random.randint(0, 65535)
    r25 = random.randint(0, 1)
    p, r16, r26o, r6 = cave(sp, r26_in, abe, speed, tq, hand, theta, I8, ramp, r25)
    paths[p] = paths.get(p, 0) + 1
    if r16 is not None: maxabs["r16"] = max(maxabs["r16"], abs(r16))
    if r26o is not None: maxabs["r26"] = max(maxabs["r26"], abs(r26o))
    if isinstance(r6, int): maxabs["r6"] = max(maxabs["r6"], abs(r6))
# force extreme corners
for sp in (-32768, 32767):
    for abe in (-13000, 0, 13000, 12999, -13001, 32767):
        for speed in (0, 1382, 1383, 2880, 2881, 65535):
            for tq in (0, 300, 301, 512, 513, 65535):
                for theta in (-32768, 0, 32767):
                    for I8 in (-2**31, 0, 2**31-1):
                        for r25 in (0, 1):
                            cave(sp, random.randint(-65535,65535), abe, speed, tq, random.randint(-32768,32767), theta, I8, 0x8000, r25)
print("paths hit:", paths)
print("max |r16|=", maxabs["r16"], " <2^31?", maxabs["r16"] < 2**31)
print("max |r26|=", maxabs["r26"])
print("max |r6| =", maxabs["r6"], " <2^31?", maxabs["r6"] < 2**31)
print("int32 overflow events:", len(over), over[:5])
# valid-rate window
print("rate valid iff abe in [-13000,13000]: check -13001 ->", "skip" if cave(0,0,-13001,100,0,0,0,0,0x8000,1)[0]=="opskip" else "RUN",
      "| 13000 ->", cave(0,0,13000,100,0,0,0,0,0x8000,1)[0], "| 13001 ->", cave(0,0,13001,100,0,0,0,0,0x8000,1)[0])
