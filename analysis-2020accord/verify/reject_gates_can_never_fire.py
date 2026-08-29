# -*- coding: utf-8 -*-
"""
CAN ANY ZERO-REJECT GATE ACTUALLY FIRE?

FUN_00038148 gates every model lane with the SAME idiom, e.g. for gp-0x6b4e:

    (int)*(short *)(gp - 0x6b4e) * (uint)( (int)*(short *)(gp - 0x6b4e) + 0x2800U < 0x5001 )

That is an UNSIGNED compare of (x + W) against 2W+1.  It is a zero-REJECT, not a saturation: a lane
outside its window contributes 0, which is a harder nonlinearity than clipping and is exactly the
kind of thing the record's "command-gated saturation" model needs.

But a gate only matters if its input can leave the window.  Mirror the compare exactly, then check
each lane's own producer bound against it.
"""


def gate(x, W):
    """The firmware's compare, bit-exact: unsigned (x + W) < 2W+1 on 32-bit."""
    return int(((x + W) & 0xFFFFFFFF) < (2 * W + 1))


print('=' * 100)
print('  THE GATE IDIOM, MIRRORED EXACTLY  --  unsigned (x + W) < 2W+1')
print('=' * 100)
W = 0x2800
for x in (-W - 1, -W, -1, 0, 1, W, W + 1):
    print('   W = %5d   x = %+7d  ->  gate %d' % (W, x, gate(x, W)))
print('   => the gate passes exactly |x| <= W, and rejects at |x| = W+1.')
print()

# lane, gate window W, the producer's own hard bound, where that bound comes from
LANES = [
    ('gp-0x6b4e', 0x2800, 10240, 'writer SATURATES to +-10240 (0x27442..0x27454 movea/cmovle)'),
    ('gp-0x6b4c', 0x2800, 10240, 'clamped +-10240; measured |.| >= 4096 duty 0.000000 / 17,614 fr'),
    ('gp-0x6b26', 0x0400, 511, 'producer clamped to 511 by cal 0xC407E'),
    ('gp-0x6b46', 0x0400, 512, 'FUN_00036682 tail clamps its driver to +-0x200, EMA converges'),
    ('gp-0x6bd0', 0x0800, 1024, '<=1024 highway, 0 in 100 % of the micro regime'),
    ('gp-0x6bbe', 0x0800, 512, 'flat +-512 bound, p50 74'),
]
print('  %-11s %8s %10s   can it EVER reject?' % ('lane', 'window W', 'producer'))
print('  ' + '-' * 92)
any_can = False
for nm, W, prod, why in LANES:
    can = gate(prod, W) == 0 or gate(-prod, W) == 0
    any_can |= can
    print('  %-11s %8d %10d   %s' % (nm, W, prod,
                                     '** CAN REJECT **' if can else 'NO -- producer <= window'))
    print('              %s' % why)

print()
print('=' * 100)
if not any_can:
    print('  ** NOT ONE OF THE SIX GATES CAN EVER FIRE. **')
    print('  Every producer is bounded at or below its own gate window, so no lane is ever')
    print('  zero-rejected.  gp-0x6b4e is the tightest case and it is EXACT: the writer saturates')
    print('  to +-10240 and the gate passes |x| <= 10240, so the saturated value passes by one count.')
    print()
    print('  COMBINED WITH LAST TICK: no clamp in the command->motor path saturates (gp-0x6b70')
    print('  measured 1/72,916), and now no gate rejects either.')
    print('  => the command-gated-saturation model has NO MECHANISM ANYWHERE IN THIS PATH.')
else:
    print('  At least one gate can fire -- see the flagged rows.')
print()
print('  WHAT THIS DOES NOT KILL: gp-0x6b4e is still SATURATED BY ITS WRITER at +-10240.')
print('  The gate passing is irrelevant to that -- the clipping already happened upstream.')
print('  Whether gp-0x3d8c actually drives it to the rail is UNMEASURED, and V204 reads it.')
