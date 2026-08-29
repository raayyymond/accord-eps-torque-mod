# -*- coding: utf-8 -*-
"""How much authority does the inertia lever actually have -- and when does it SATURATE?

    gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )

Two bounds matter, and the second is the sharp one:

  1. RANGE bound: the term is clamped at +-cal(0xC407E) while the aggregator spans +-10240, so it
     can never be more than a fixed fraction of the command.
  2. SATURATION: above a certain |accel| the clamp binds, and then HALVING L DOES NOT HALVE THE
     OUTPUT -- it only moves where saturation starts.  If the ratchet lives above that threshold,
     V196's half-dose is largely ineffective.

The saturation threshold is compared against T = cal(0xC620A), the detector's own threshold, because
that is the number V194's probe measures.
"""
import io,glob,struct,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
A='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
def img(v):
    g=[x for x in glob.glob(A+'/*_'+v+'_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0],'rb').read() if g else None
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def s16(b,o): return struct.unpack_from('<h',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
B={n:img(n) for n in ('v122','v195','v196')}
b=B['v196']
CLAMP=u16(b,0xC407E); T=s16(b,0xC620A); AGG=0x2800
print('cells, read from the V196 image:')
print('   0xC407E  clamp on gp-0x6b26      %d'%CLAMP)
print('   0xC620A  detector threshold T    %d'%T)
print('   aggregator output clamp          %d  (0x2800)'%AGG)
print('')
print('[1] RANGE BOUND')
print('   the inertia term is at most %d / %d = %.1f %% of the aggregator range'
      %(CLAMP,AGG,100.0*CLAMP/AGG))
print('   => halving it moves at most %.1f %% of the command.'%(50.0*CLAMP/AGG))
print('   !! that is the share of FULL RANGE.  Because the term is acceleration-derived its share')
print('      of the 8 Hz CONTENT is larger, by an amount this cannot bound.')
print('')
print('[2] SATURATION -- the sharp bound')
print('   scale = L * 273 / 2**24 ;  the clamp binds when |accel| > clamp/|scale|')
print('')
print('%-22s %10s %12s %14s'%('build / L','scale','sat |accel|','vs T=%d'%T))
print('-'*62)
rows=[]
for lbl,v,mode in (('FLYING V122 engaged','v122',26),('V195 = Honda','v195',26),
                   ('V196 = half Honda','v196',26)):
    bb=B[v]; p=u32(bb,0xCBE74+4*mode); n=s16(bb,p)
    L=s16(bb,p+2+2*n)          # Y[0], the low-index end where the micro regime sits
    sc=abs(L)*273.0/2**24
    sat=CLAMP/sc
    rows.append((lbl,L,sc,sat))
    print('%-22s %10.5f %12.0f %14s'%('%s  L=%d'%(lbl,L),sc,sat,
          'BELOW T' if sat<T else 'above T'))
print('')
sat_h=rows[1][3]; sat_v=rows[2][3]
print('=> Honda saturates at |accel| > %.0f ; the half-dose at > %.0f ; the detector fires at %d.'
      %(sat_h,sat_v,T))
if sat_h<T:
    print('')
    print('   \u26a0 THE TWO LEVERS HAVE INCOMPATIBLE OPERATING REGIMES.')
    print('     If |accel| is large enough for the DETECTOR to fire (> %d), it is far past the'%T)
    print('     inertia clamp (%0.f), so gp-0x6b26 is SATURATED and halving L only moves where'%sat_h)
    print('     saturation starts -- V196 does little there.')
    print('     If |accel| stays below %.0f, the half-dose works but the detector NEVER fires,'%sat_h)
    print('     so V191/V192/V193 are inert.')
    print('')
    print('   => V196 (inertia) and V194 (detector) are effective in MUTUALLY EXCLUSIVE regimes,')
    print('      and V194\'s probe on gp-0x6c2c measures which regime the car is actually in.')
    print('      That single measurement decides which branch is worth pursuing.')
