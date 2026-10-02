"""ADV-arithmetic V299, step 3: the cave's freeze decision (my validated mirror) driving the Honda integrator exactly as decoded
at 0x29D7A..0x29DE4 + st.w r24,-0x6dd0 @0x2A190 (deadband tp+0x72E4 = 0, Ki tp+0x73E6 = 40, ICL tp+0x71BA = 8192, read from the
image). Open loop (no plant): these isolate the ARITHMETIC of the bound/freeze, not the car's dynamics."""
import time, sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_mirror_vs_bytes import mirror99, I99, s32
t0 = time.time()
TP = 0xBF000
DB = struct.unpack_from('<H', I99, TP + 0x72E4)[0]; KI = struct.unpack_from('<H', I99, TP + 0x73E6)[0]; ICL = struct.unpack_from('<H', I99, TP + 0x71BA)[0]
assert (DB, KI, ICL) == (0, 40, 8192), (DB, KI, ICL)
def honda_I(I8, kind, Ep, r6):
    e = (Ep >> 5) if kind == 'DONE' else r6               # 0x29D7A mov r16,r6 ; sar 5  | FRZ enters 0x29D7E with r6
    if e > DB: r9 = e - DB                                # 0x29D7E..8A
    elif e < -DB: r9 = e + DB                             # 0x29D8C..9A
    else: r9 = 0
    lim = (ICL << 10) >> 3                                # 0x29DAC shl 0xa ; sar 3
    r10 = (I8 >> 3) + (s32(r9 * KI) >> 3)                 # 0x29DA4..B4
    r2 = max(-lim, min(lim, r10))                         # 0x29DB6..C2 cmovgt / cmovle
    return s32(r2 << 3)                                   # 0x29DE4 shl 3 -> st.w r24,-0x6dd0 @0x2A190
def tick(I8, v, th, E, hand=0):
    # E chosen directly via sp with r26=0: sp<<2 = E
    m = mirror99(E >> 2, 0, 0, v, 1, hand, th, I8, 0x8000)
    return honda_I(I8, m[0], m[1], m[3]), m
def S(I8): return I8 >> 10
def run(name, vs, th, E, I0=0):
    I8 = I0; peak = 0
    for v in vs:
        I8, m = tick(I8, v, th, E); peak = max(peak, abs(S(I8)))
    print('  %-58s final S=I>>7 %6d  peak %6d' % (name, S(I8), peak)); return I8
N = 3000   # 3 s at 1 kHz
th = 600; E = 16 * 100   # 60 deg held, 10 deg same-sign error (E = 16*dtheta in 0.1 deg; scaling is BELIEF, arithmetic is exact)
print('== S1/S2 constant v vs jitter across the 1382 / 2880 edges (theta 60 deg, same-sign error 10 deg) ==')
run('v=1382 constant', [1382] * N, th, E)
run('v=1383 constant', [1383] * N, th, E)
run('v alternates 1382/1383 every tick', [1382 + (i & 1) for i in range(N)], th, E)
run('v=1382 with 1-in-50 ticks at 1383', [1383 if i % 50 == 0 else 1382 for i in range(N)], th, E)
run('v=2880 constant', [2880] * N, th, E)
run('v=2881 constant', [2881] * N, th, E)
run('v alternates 2880/2881 every tick', [2880 + (i & 1) for i in range(N)], th, E)
run('v=2880 with 1-in-50 ticks at 2881', [2881 if i % 50 == 0 else 2880 for i in range(N)], th, E)
print('== S3 decel through both edges while the same-sign error persists (carry-over) ==')
vs = [3500] * 3000 + [int(3500 - (3500 - 600) * i / 4000) for i in range(4000)] + [600] * 2000
I8 = run('v 3500 (3 s) -> 600 ramp (4 s) -> 600 (2 s)', vs, th, E)
print('    at v=600 the cap is 4096, held S = %d (cap is a WINDING limit; freeze holds, never bleeds)' % S(I8))
I8 = run('  then error REVERSES (E<0) at v=600 for 0.5 s', [600] * 500, th, -E, I0=I8)
print('== S4 one-tick overshoot at a large error, low band ==')
I8 = 4095 * 1024
for k in range(3):
    I8n, m = tick(I8, 1000, 900, 16 * 900)
    print('  tick %d: S %d -> %d  exit %s bound %s' % (k, S(I8), S(I8n), m[0], m[4])); I8 = I8n
print('== S5 the ICL with an uncapped bound (v>2880, theta 3000) and the rail error ==')
I8 = 0
for k in range(2000): I8, m = tick(I8, 4000, 3000, 131068)
print('  S after 2 s at rail error: %d (ICL %d), raw I8 %d -> no wrap: %s' % (S(I8), ICL, I8, abs(I8) <= ICL * 1024))
print('== S6 sar-10 floor asymmetry at the bound (low band, theta 300 same sign) ==')
for sgn in (1, -1):
    hi = None
    for I8 in range(4095 * 1024 - 2048, 4097 * 1024 + 2048, 8):
        X = sgn * I8
        m = mirror99(sgn * 4000 >> 2, 0, 0, 1000, 1, 0, sgn * 300, X, 0x8000)
        if m[0] == 'DONE': hi = X
    print('  sign %+d: largest |I8| still winding = %d  (= %.4f S-counts)' % (sgn, abs(hi), abs(hi) / 1024))
print('== S7 hard-freeze edge: raw |tau| 1229 winds, 1230 holds ==')
for a in (1229, 1230):
    m = mirror99(1000, 0, 0, 1000, 1, a, 300, 0, 0x8000); print('  a4f68=%d -> %s r6=%s' % (a, m[0], m[3]))
print('wall %.1f s' % (time.time() - t0))
