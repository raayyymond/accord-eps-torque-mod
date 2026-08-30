# -*- coding: utf-8 -*-
"""FUN_00026c80 -- the 11-slot lane mixer, decoded and asserted from the image bytes.

Traced 2026-08-29.  Previously the kit knew ONE of its eleven outputs (gp-0x6b4c).  This decodes
all of them, maps all ten client slots, and settles what the mixer actually delivers.

HEADLINE: the mixer's delivery-bound output gp-0x6b4a is IDENTICALLY ZERO.  Nine of the ten slots
store value A as a literal r0; the tenth is gated by 0xC616C = 0.

This file also carries a RETRACTION.  An earlier pass in the same session traced every cell, clamp
and reader correctly and concluded that zeroing one 0xC4118 arm byte would arm the mixer's rate
limiter in the live delivery path.  That was wrong: the limiter's input is the value-A sum on the
other side of the arm gate, and the payloads are zero on BOTH sides.  The plumbing was right and the
conclusion was still wrong, because the payloads were never checked.  Trace the payload, not the path.

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
f32 = lambda a: struct.unpack_from('<f', b, a)[0]

MODE = [u8(TP + 0x5124 + i) for i in range(11)]   # 0xC4124
ARM = [u8(TP + 0x5118 + i) for i in range(11)]    # 0xC4118

# slot -> (caller, value-A source, value-B source, value-D source)
SLOTS = {
    0: ('FUN_0002e52e', 'r0', 'r12', '0'),
    1: ('FUN_0002b422', 'r0', 'r12', '0'),
    2: ('FUN_0003405a', 'gp-0x6b76', 'gp-0x6b78', '0'),
    3: ('FUN_0002c246', 'r0', 'r8', '0'),
    4: ('FUN_00023ad2', 'r0', 'r11', '0'),
    5: ('FUN_00023fe2', 'r0', 'r12', '0'),
    6: ('FUN_0003aff4', 'r0', '0', 'r7'),
    7: ('FUN_0003a8a8', 'r0', '0', '0'),
    8: ('FUN_0002caa2', 'r0', 'r9', '0'),
    9: ('FUN_000339cc', 'r0', 'r10', '0'),
}

print('=' * 78)
print('FUN_00026c80 -- the 11-slot lane mixer')
print('=' * 78)
print()
print('CHAIN')
print('   FUN_00025c32(rec) is the SLOT WRITER -- a 16-byte request record, 10 callers:')
print('      rec[0] slot   rec[1] type 0-5   rec[2:4] A   rec[4:6] B   rec[6:8] C')
print('      rec[8:10] D   rec[10:16] three weights (0..1024)')
print('      types 2/3/4 ACCEPT the values; 0/1/5 ZERO them and set the weights to 1024')
print()
print('   A -> gp-0x62e0[i] -> gp-0x6298 -> gp-0x3d80 -> gp-0x6b4a -> DELIVERY (FUN_00042af8)')
print('   B -> gp-0x62f8[i] -> gp-0x62b0 -> gp-0x3d88 -> gp-0x6b4c    (mode 5 zeroes gp-0x62b0)')
print('   D -> gp-0x633c[i] -> gp-0x6324 -> gp-0x3d90 -> gp-0x6bfa    the OBSERVER BIAS term')
print()
print('   The rate limiter, between gp-0x3d84 and gp-0x6b4a:')
print('      target   = clamp(gp-0x3d84, +-%d or +-%d)     0xC6192 / 0xC6198'
      % (u16(TP + 0x7192), u16(TP + 0x7198)))
print('      follower = slew(follower -> target, +-%d/tick)   0xC6194   [gp-0x3d6c]'
      % u16(TP + 0x7194))
print('      gp-0x6b4a = clamp(gp-0x3d80 + follower + clamp(target-follower, +-256), +-25600)')
print()
print('SLOT MAP -- all ten, read off each caller (ep = sp, so sst.b/sst.h give the layout)')
print('   %-4s %-14s %-5s %-12s %-8s %s' % ('slot', 'caller', 'mode', 'value A', 'value B', 'value D'))
for i in range(10):
    c, va, vb, vd = SLOTS[i]
    note = '' if MODE[i] == 0 else '(discarded)'
    print('   %-4d %-14s %-5d %-12s %-8s %s' % (i, c, MODE[i], va, vb if not note else note, vd))
print('   slot 10 is written by phase 1 but never summed by phase 2.')
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
      '0xC4118 arm gate is all ones (Honda wiring, unchanged)')
check(sum(1 for i in range(10) if SLOTS[i][1] == 'r0') == 9,
      'NINE of ten slots store value A as literal r0')
check(u16(TP + 0x716c) == 0,
      '0xC616C == 0 -- zeroes gp-0x6b76, the ONLY non-constant value-A source')
check(u8(TP + 0x749d) == 0,
      '0xC649D == 0 -- lane 1 of the FUN_00033d10 PI controller is disabled')
check(u16(TP + 0x73cc) == 0,
      '0xC63CC == 0 -- iVar13 cannot reach gp-0x6b4c')
check(u16(TP + 0x7194) == 3,
      '0xC6194 == 3 counts/tick -- the slew rate itself is NOT zero')
print()
print('   => gp-0x3d80 == gp-0x3d84 == 0, so gp-0x6b4a == 0.')
print('      The mixer reaches the delivery chain with NOTHING, and no single-byte edit to')
print('      0xC4118 can arm the rate limiter: its input is zero on both sides of the gate.')
print()
print('THE DORMANT PI CONTROLLER -- FUN_00033d10, gains ADJACENT TO THE BIQUAD WE EDIT')
print('   biquad (ours to touch):   0xC60A8 a1  0xC60AC a2  0xC60B0 b1  0xC60B4 g')
for a, nm in ((0xC60B8, 'lane2 pre-filter alpha'), (0xC60BC, 'lane1 D'), (0xC60C0, 'lane1 I clamp'),
              (0xC60C4, 'lane1 I'), (0xC60C8, 'lane1 P'), (0xC60CC, 'lane2 D'),
              (0xC60D0, 'lane2 I clamp'), (0xC60D4, 'lane2 I'), (0xC60D8, 'lane2 P')):
    print('   0x%05X  %-22s = %.8g' % (a, nm, f32(a)))
print()
print('   Gated out THREE independent ways: lane 1 by 0xC649D=0, lane 2 output gp-0x6b78')
print('   discarded by 0xC4124[2]=5, and the torque term by 0xC616C=0.')
print('   !! The notch builders write four floats at 0xC60A8-0xC60B4. One float of offset')
print('      error lands in this block. It is byte-stock on all flashable builds (checked')
print('      by closeout_verify_published.py).')
print()
print('   NOT A LEVER YET: gp-0x6b4a sign/scaling inside FUN_00042af8 is untraced, and the PI')
print('   inputs (gp-0x6bf0, gp-0x6be0, gp-0x6a58) are unidentified. Raising 0xC616C admits a')
print('   DRIVER-torque-proportional term, which on the wrong sign is added friction.')
print()
if fails:
    print('FAILED: %d' % len(fails))
    sys.exit(1)
print('all assertions pass')
