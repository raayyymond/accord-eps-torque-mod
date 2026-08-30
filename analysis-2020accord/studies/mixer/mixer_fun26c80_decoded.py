# -*- coding: utf-8 -*-
"""FUN_00026c80 -- the 11-slot lane mixer, decoded and asserted from the image bytes.

Traced 2026-08-29.  This function was previously known only through ONE of its eleven
outputs (gp-0x6b4c, "an 11-slot assist sum").  The other ten were unnamed, and two of
them turned out to matter:

  * gp-0x6bfa -- the BIAS TERM the observer adds in FUN_00038148
                 (resid = gp-0x6bfe - (model>>4) + gp-0x6bfa).  Its provenance was open.
  * gp-0x6b4a -- reaches the DELIVERY CHAIN (FUN_00042af8, read at 0x42BF6), and carries
                 a complete Honda-written RATE LIMITER that is dormant.

The headline is the rate limiter, and the reason it is dormant is NOT the reason the kit
had on file.  See ASSERTIONS below.

Run:  python analysis-2020accord/studies/mixer/mixer_fun26c80_decoded.py
"""
import os
import struct
import sys

ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
IMG = os.path.join(ROOT, 'analysis-2020accord', 'stock_fw_dump', 'code.bin')
TP = 0xBF000

b = open(IMG, 'rb').read()
u8 = lambda a: b[a]
u16 = lambda a: struct.unpack_from('<H', b, a)[0]
s16 = lambda a: struct.unpack_from('<h', b, a)[0]

MODE = [u8(TP + 0x5124 + i) for i in range(11)]   # 0xC4124
ARM = [u8(TP + 0x5118 + i) for i in range(11)]    # 0xC4118

print('=' * 78)
print('FUN_00026c80 -- the 11-slot lane mixer')
print('=' * 78)
print()
print('PHASE 1  per-slot dispatch on the MODE table 0xC4124')
print('   mode :', MODE)
print('   arm  :', ARM, '  <- 0xC4118')
print('   modes present: %s' % sorted(set(MODE)))
print('   Only slots 0..9 are accumulated in phase 2; slot 10 is written but never summed.')
print('   mode-0 slots (of the 10 summed): %s' % [i for i in range(10) if MODE[i] == 0])
print('   mode-5 slots (of the 10 summed): %s' % [i for i in range(10) if MODE[i] == 5])
print()
print('PHASE 2  accumulate 10 slots -> 11 scratch cells')
print('   gp-0x3d70 = MIN over slots of gp-0x61b8[i]')
print('   gp-0x3d74 = MIN over slots of gp-0x61d0[i]')
print('   gp-0x3d78 = MIN over slots of gp-0x61e8[i]')
print('   gp-0x3d8c = SUM of gp-0x62c8[i]                      -> gp-0x6b4e  (clamp +-10240)')
print('   gp-0x3d7c = SUM of gp-0x625c[i]                      -> gp-0x69f2  (clamp +-3600)')
print('   gp-0x3d90 = SUM of gp-0x6324[i]                      -> gp-0x6bfa  (clamp +-20000)')
print('   gp-0x3d88 = SUM of gp-0x62b0[i] WHERE arm[i] != 0')
print('   gp-0x3d80 = SUM of gp-0x6298[i] WHERE arm[i] != 0')
print('   gp-0x3d84 = SUM of gp-0x6298[i] WHERE arm[i] == 0    <- the RATE LIMITER input')
print()
print('PHASE 3  the rate limiter, then the two live outputs')
print('   target   = clamp(gp-0x3d84, +-LIM)          LIM = 0xC6192=%d or 0xC6198=%d'
      % (u16(TP + 0x7192), u16(TP + 0x7198)))
print('                                               (0xC6198 once a %d-tick debounce saturates,'
      % u16(TP + 0x7284))
print('                                                counter 0xC6284)')
print('   follower = slew(follower -> target, +-%d per tick)   0xC6194   [gp-0x3d6c]'
      % u16(TP + 0x7194))
print('   residual = clamp(target - follower, +-LERP(gp-0x6a62))')
print('   iVar13   = gp-0x3d80 + follower + residual')
print('   gp-0x6b4c = clamp(gp-0x3d88 + (gp-0x6752) * ((iVar13 * 0xC63CC) >> 10), +-10240)')
print('   gp-0x6b4a = clamp(iVar13, +-25600)')
print()
CAPX = [u16(TP + 0x7700 + 2 * i) for i in range(3)]
CAPY = [u16(TP + 0x7706 + 2 * i) for i in range(3)]
print('   residual cap table   X = %s   (0xC6700)' % CAPX)
print('                        Y = %s   (0xC6706)' % CAPY)
print('                        above gp-0x6a62 > 0x7D00 the cap is 0xC6196 = %d'
      % u16(TP + 0x7196))
print('   0xC63CC = %d   (the gain on iVar13 into gp-0x6b4c)' % u16(TP + 0x73cc))
print('   gp-0x6752 = -1 (a verified RAM cell, not flash -- see the memory)')
print()

fails = []


def check(ok, label):
    print('   [%s] %s' % ('PASS' if ok else 'FAIL', label))
    if not ok:
        fails.append(label)


print('ASSERTIONS')
check(MODE == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0],
      '0xC4124 mode table is the recorded [0,0,5,0,5,5,0,0,0,5,0]')
check(all(a == 1 for a in ARM),
      '0xC4118 arm gate is ALL ONES -- so gp-0x3d84 (the limiter input) is IDENTICALLY ZERO')
check(u16(TP + 0x73cc) == 0,
      '0xC63CC == 0 -- iVar13 cannot reach gp-0x6b4c')
check(u16(TP + 0x7194) == 3,
      '0xC6194 == 3 counts/tick -- the slew rate is NOT zero, the cell is not itself dead')
check(len(set(CAPY)) == 1 and CAPY[0] == 256,
      'the residual cap table is FLAT at 256 -- no gp-0x6a62 shaping in force')
print()
print('WHAT THIS CORRECTS')
print('   memory reference-accord-lkas-only-rate-limiter-c6194 records 0xC6194 as')
print('   "DEAD calibration -- output x0".  The x0 (0xC63CC) is real, but it only covers')
print('   gp-0x6b4c.  iVar13 ALSO reaches gp-0x6b4a with NO x0, and gp-0x6b4a has 8 readers')
print('   including the delivery chain FUN_00042af8 at 0x42BF6.  The load-bearing reason the')
print('   limiter is dormant is the ARM GATE 0xC4118, not the x0.')
print()
print('   Consequence, and why this is a GATE: zeroing ANY ONE BYTE of 0xC4118 moves that')
print('   slot out of the direct sum and into the rate-limited path, arming a 3-count/tick')
print('   slew limiter with a 256-count residual clip in the LIVE delivery chain.  At the')
print('   ratchet frequency (~7.8 Hz, 64 ms half-cycle = 192 counts of follower travel) the')
print('   follower cannot track, and the path degenerates to a HARD +-256 CLIP -- a relay.')
print('   The x0 argument does not protect against that.  0xC4118 is now asserted at')
print('   close-out for every flashable build.')
print()
if fails:
    print('FAILED: %d' % len(fails))
    sys.exit(1)
print('all assertions pass')
