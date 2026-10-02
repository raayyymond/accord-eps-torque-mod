"""ADV-arithmetic V299, step 1: my own integer mirror (transcribed from the Ghidra decode of the BUILT image) vs the image
bytes executed by my own interpreter (v850_mini.py). Also runs V298's bytes as the negative/positive control."""
import glob, time, random, struct, numpy as np, hashlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v850_mini import Cave, GP, s32, M32
t0 = time.time()
ROOT = r'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
I99 = open(glob.glob(ROOT + '_v299_*A16B_plain_image.bin')[0], 'rb').read()
I98 = open(glob.glob(ROOT + '_v298_*A16A_plain_image.bin')[0], 'rb').read()
assert hashlib.sha256(I99).hexdigest().startswith('30ff05fa'); assert hashlib.sha256(I98).hexdigest().startswith('177abf04')
u16 = lambda img, a: struct.unpack_from('<H', img, a)[0]
s16 = lambda img, a: struct.unpack_from('<h', img, a)[0]

def gwalk(img, v):                      # 0xC4C18..0xC4C52 (table ptr read from the mov imm32 @0xC4C1C)
    a = struct.unpack_from('<I', img, 0xC4C1E)[0]
    if v <= u16(img, a): return u16(img, a + 2)          # 0xC4C26 bh not taken -> ld.hu 2
    while v > u16(img, a + 6): a += 6                    # 0xC4C30..3C
    return s32((s32((v - u16(img, a)) * s16(img, a + 4)) >> 12) + u16(img, a + 2))  # 0xC4C3E..52

def mirror99(sp, r26, abe, v, r25, a4f68, th, I8, r14, img=I99):
    E = s32((s32(sp) << 2) - r26)                        # 0xC4C00 shl 2 ; 0xC4C02 sub r26,r16
    op = s16(struct.pack('<h', abe), 0) if False else ((abe + 0x8000) & 0xFFFF) - 0x8000   # 0xC4C04 ld.h
    if ((op + 13000) & M32) > 26000: return ('SKIP', E, op, None, None)   # 0xC4C08..14 (cmp unsigned, bnh)
    G = gwalk(img, v)
    Ep = s32(E * G) >> 8                                  # 0xC4C54 mul (low word) ; 0xC4C58 sar 8
    if r25 == 0: return ('FRZ29D7E', 0, 0, s32(-(s32(I8) >> 6)), None)    # 0xC4C5A be -> 0xC4CC8..D4
    if a4f68 > 1229: return ('FRZ29D7E', Ep, op, 0, None)                  # 0xC4C5E ld.hu ; movea 0x4cd ; bh
    r9 = ((th + 0x8000) & 0xFFFF) - 0x8000               # 0xC4C6A ld.h -0x6a00
    if Ep < 0: r9 = -r9                                   # 0xC4C6E cmp r0,r16 ; bge ; subr
    if r9 < 0: r9 = 0                                     # 0xC4C74 cmp r0,r9 ; bge ; mov 0
    if v > 2880: b = s32((r9 << 6) + 1250)                # 0xC4C7E movea 0xb40 ; bh -> 0xC4CA6 shl 6 ; addi 0x4e2
    else:
        b = s32((r9 << 4) + 1250)                         # 0xC4C86 shl 4 ; addi 0x4e2
        cap = 4096 if v <= 1382 else 6144                 # 0xC4C8C movea 0x566 ; bh ; movea 0x1000 | 0x1800
        if (b & M32) > cap: b = cap                       # 0xC4C9E cmp ; cmovh (unsigned)
    t = s32(I8) >> 10                                     # 0xC4CAC ld.w -0x6dd0 ; sar 0xa
    if Ep < 0: t = -t                                     # 0xC4CB2..B6
    if t >= b: return ('FRZ29D7E', Ep, op, 0, b)         # 0xC4CB8 cmp r9,r13 ; bge
    if (r14 & 0x8000) == 0: return ('FRZ29D7E', Ep, op, 0, b)   # 0xC4CBC andi ; bne
    return ('DONE', Ep, op, None, b)                      # 0xC4CD8 jmp [r6]

def run_bytes(img, sp, r26, abe, v, r25, a4f68, th, I8, r14, hand=0):
    ram = {(GP - 0x6abe, 2): abe & 0xFFFF, (GP - 0x6a5e, 2): v, (GP - 0x4f68, 2): a4f68, (GP - 0x6a00, 2): th & 0xFFFF,
           (GP - 0x6dd0, 4): I8 & M32, (GP - 0x4f60, 2): hand & 0xFFFF}
    regs = {16: sp & M32, 26: r26 & M32, 25: r25, 14: r14, 6: 0x29D7A, 8: 0x11111111, 9: 0x22222222, 13: 0x33333333}
    kind, R, reads = Cave(img).run(regs, ram)
    return kind, s32(R[16]), s32(R[26]), s32(R[6]), s32(R[9]), R

def gen(rng, targeted):
    sp = rng.randint(-32768, 32767); r26 = rng.randint(-65535, 65535)
    if rng.random() < 0.3: sp = rng.randint(-600, 600); r26 = rng.randint(-2400, 2400)
    abe = rng.randint(-13000, 13000) if rng.random() < 0.9 else rng.randint(-32768, 32767)
    v = rng.choice([0, 714, 1381, 1382, 1383, 2879, 2880, 2881, 6198, 65535, rng.randint(0, 65535), rng.randint(1000, 3200)]) if targeted else rng.randint(0, 4000)
    r25 = 0 if rng.random() < 0.05 else 1
    a4f68 = rng.choice([0, 300, 512, 1228, 1229, 1230, 1231, 32768, rng.randint(0, 2000), rng.randint(0, 65535)])
    th = rng.choice([0, 1, -1, 77, 78, 177, 178, 307, -178, -307, 32767, -32768, rng.randint(-12000, 12000), rng.randint(-400, 400)])
    I8 = rng.choice([0, 4096 * 1024, 4096 * 1024 - 1, 6144 * 1024, 6144 * 1024 - 1, -4095 * 1024, -4096 * 1024, -6143 * 1024, -6144 * 1024,
                     8192 * 1024, -8192 * 1024, 1250 * 1024, -1249 * 1024, -1250 * 1024, rng.randint(-8388608, 8388608) & ~7, rng.randint(-2**31, 2**31 - 1)])
    r14 = rng.choice([0x8000, 0, 0xFFFF, 0x7FFF, rng.randint(0, M32)])
    return sp, r26, abe, v, r25, a4f68, th, I8, r14

rng = random.Random(29901); mism = 0; n = 0; kinds = {}
for i in range(30000):
    c = gen(rng, i % 2 == 0)
    k, r16, r26o, r6, r9, R = run_bytes(I99, *c)
    m = mirror99(*c)
    kinds[m[0]] = kinds.get(m[0], 0) + 1
    ok = (k == m[0]) and r16 == m[1] and r26o == m[2] and (m[3] is None or r6 == m[3]) and (m[4] is None or r9 == m[4])
    # non-scratch registers untouched (only r6,r8,r9,r13,r16,r26 may change)
    for rr in range(32):
        if rr in (6, 8, 9, 13, 16, 26): continue
        if rr == 4: continue
        exp = {25: c[4], 14: c[8]}.get(rr, 0)
        if R[rr] != (exp & M32): ok = False
    n += 1
    if not ok:
        mism += 1
        if mism < 5: print('MISMATCH', c, (k, r16, r26o, r6, r9), m)
print('V299 bytes vs my mirror: %d / %d mismatches; exit classes %s' % (mism, n, kinds))
# negative control: V298 bytes vs the V299 mirror on targeted cases (must mismatch)
rng = random.Random(7); neg = 0
for i in range(3000):
    c = gen(rng, True)
    k, r16, r26o, r6, r9, R = run_bytes(I98, *c, hand=rng.randint(-2000, 2000))
    m = mirror99(*c)
    if not ((k == m[0]) and r16 == m[1] and r26o == m[2] and (m[3] is None or r6 == m[3])): neg += 1
print('NEG CONTROL V298 bytes vs V299 mirror: %d / 3000 mismatches (must be > 0)' % neg)
print('wall %.1f s' % (time.time() - t0))
