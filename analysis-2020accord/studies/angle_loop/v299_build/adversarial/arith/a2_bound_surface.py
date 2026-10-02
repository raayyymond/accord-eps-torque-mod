"""ADV-arithmetic V299, step 2: vectorised sweeps of the bound / freeze surface from my mirror (validated 0/30000 vs bytes)."""
import numpy as np, time, glob, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_mirror_vs_bytes import I99, I98, gwalk  # noqa (a1 re-runs its check on import: ~2.6 s)
t0 = time.time()
def bound99(th, sgn, v):
    th = th.astype(np.int64); r9 = np.where(sgn < 0, -th, th); r9 = np.maximum(r9, 0)
    hi = v > 2880
    b = np.where(hi, (r9 << 6) + 1250, (r9 << 4) + 1250)
    cap = np.where(v <= 1382, 4096, 6144)
    return np.where(hi, b, np.minimum(b, cap))
def bound98(th, v):                      # V298 (decoded from 177abf04 by the same interpreter run in a1): |th|, cap 4096 only v<=1382
    r9 = np.abs(th.astype(np.int64)); hi = v > 2880
    b = np.where(hi, (r9 << 6) + 1250, (r9 << 4) + 1250)
    return np.where(v <= 1382, np.minimum(b, 4096), b)
TH = np.arange(-32768, 32768, dtype=np.int64)
VE = np.array([0, 1, 714, 1381, 1382, 1383, 1384, 2000, 2879, 2880, 2881, 2882, 6198, 65534, 65535])
print('== bound over ALL theta (s16) x sgn(Ep) in {-,0,+} x v-edges ==')
worst_up = 0
for v in VE:
    for sg in (-1, 0, 1):
        b = bound99(TH, np.full_like(TH, sg), np.full_like(TH, v))
        b8 = bound98(TH, np.full_like(TH, v))
        assert b.min() >= 1250
        up = (b - b8).max(); worst_up = max(worst_up, up)
        if sg == 1: print('v=%5d sgn=+ : bound in [%d, %d]; max(b99-b98)=%d; first theta at cap: %s' % (v, b.min(), b.max(), up,
              (TH[(b == b.max())][0] if v <= 2880 else 'uncapped')))
print('max over all of (bound99 - bound98) =', worst_up, '(<= 0 means V299 never allows more winding than V298)')
# opposing-sign: bound must be exactly 1250 whenever sign(theta) != sign(Ep) and Ep != 0
for v in VE:
    b = bound99(TH, -np.sign(TH), np.full_like(TH, v)); assert (b[TH != 0] == 1250).all()
print('opposing sign => bound == 1250 at every v edge: OK')
# Ep == 0 (cmp r0,r16 ; bge taken) treats E' as non-negative: theta<0 gets 1250, theta>0 gets 16|theta|+1250 (no increment flows at Ep=0 anyway)
print('== v regime over ALL v (u16) at theta=1000 (same-sign) ==')
V = np.arange(65536); b = bound99(np.full(65536, 1000), np.ones(65536), V)
for lo, hi in [(0, 1382), (1383, 2880), (2881, 65535)]:
    seg = b[lo:hi + 1]; print('  v %5d..%5d: bound %s' % (lo, hi, np.unique(seg)))
print('== GB-P walk over ALL v ==')
G = np.array([gwalk(I99, int(v)) for v in range(0, 65536, 1)])
print('  G min %d @v=%d, max %d, monotone pieces ok; nonpositive: %d' % (G.min(), G.argmin(), G.max(), (G <= 0).sum()))
Emax = 4 * 32768 + 65535
print('  |E| max (sp s16<<2, r26 clamp 65535 @0x28FA6) = %d ; |E|*Gmax = %d (2^31 = %d) -> wrap: %s' % (Emax, Emax * G.max(), 2**31, Emax * G.max() >= 2**31))
print('  Ep max = %d ; e5 = Ep>>5 = %d ; inc = (e5*40)>>3 = %d I-units = %.1f output counts per tick' % (
    (Emax * G.max()) >> 8, ((Emax * G.max()) >> 8) >> 5, ((((Emax * G.max()) >> 8) >> 5) * 40) >> 3, (((((Emax * G.max()) >> 8) >> 5) * 40) >> 3) / 128))
print('== one-tick overshoot past the bound (output counts, I>>7) vs angle error, G at min/max ==')
print('  dtheta(deg)  E=16*dth(0.1deg)  overshoot@G=560  @G=2188')
for dd in [1, 2, 5, 10, 20, 45, 90, 180, 409.6]:
    E = int(16 * dd * 10)
    out = []
    for g in (G.min(), G.max()):
        Ep = (E * g) >> 8; inc = (((Ep >> 5) * 40) >> 3); out.append(inc / 128)
    print('  %7.1f %10d %14.2f %10.2f' % (dd, E, out[0], out[1]))
print('wall %.2f s' % (time.time() - t0))
