# -*- coding: utf-8 -*-
"""The complete CUMULATIVE delta of V194 vs STOCK, read from the BUILT IMAGE.

Required by the close-out contract: every cell that differs from stock, what it physically is, what
it does to the car, which build introduced it, and whether it is measured / inert / unverified.
Read from the image -- never from the build scripts.
"""
import io, glob, os, struct, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
A = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
st = io.open(A + '/stock_fw_dump/code.bin', 'rb').read()


def img(v):
    g = [x for x in glob.glob(A + '/*_' + v + '_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0], 'rb').read() if g else None


v194 = img('v194')
v122 = img('v122')
START, END = 0x13000, 0x100000

# every differing byte, then collapse into runs
diff = [a for a in range(START, END) if v194[a] != st[a]]
runs = []
for a in diff:
    if runs and a == runs[-1][1]:
        runs[-1][1] = a + 1
    else:
        runs.append([a, a + 1])
crc = [r for r in runs if (r[0] & 0xFFF) >= 0xFFC]
pay = [r for r in runs if (r[0] & 0xFFF) < 0xFFC]
print('V194 vs STOCK: %d differing bytes in %d runs  (%d payload runs + %d CRC trailers)'
      % (len(diff), len(runs), len(pay), len(crc)))
print('')

# address -> (name, physical meaning, effect on the car, build, status)
K = {
 0x2A1F0: ('LKAS forward-path repoint', 'displacement of the instruction that reads the LKAS gain',
           'points the forward LKAS path at a PRIVATE gain word so the four feedback readers keep '
           'stock', 'V57', 'FLOWN'),
 0x3AA96: ('V88 sign fix', 'a branch/const in the aggregator arm',
           'corrects the sign of the LKAS-gated rate arm', 'V88', 'FLOWN, grinding FIXED on-car'),
 0x454FE: ('V42 ratchet fix', 'the state-4 governor substitution',
           'stops the governor forbidding command-magnitude increase in state 4',
           'V42 (lost V53-V70, restored V80+)', 'FLOWN, ratchet fixed on-car'),
 0x55DF2: ('427 probe SOURCE', 'displacement of the ld.h feeding CAN 427',
           'telemetry only -- selects which internal cell is broadcast', 'V194 (was V183)',
           'INSTRUMENT, no vehicle effect'),
 0x55E10: ('427 probe SHIFT', 'the pack shift for that channel',
           'telemetry only -- sar 6 so the signed source fits the 10-bit field', 'V194',
           'INSTRUMENT, no vehicle effect'),
 0x35A06: ('biquad gate: source', 'ld.bu displacement, gp-0x671a -> gp-0x6806',
           'makes the assist biquad ENGAGEMENT-gated instead of reversal-counter gated', 'V103',
           'FLOWN'),
 0x35A12: ('biquad gate: compare', 'cmp r12,r9 -> cmp r0,r9', 'compares the flag against zero',
           'V103', 'FLOWN'),
 0x35A18: ('biquad gate: condition', 'setfnc -> setfne',
           'the half the lineage omits; it is what makes the gate correct', 'V103', 'FLOWN'),
 0xC407E: ('hard-fault interlock', 'the +-clamp on gp-0x6b26 and the friction lane',
           'Honda ships 511, one count under its own 512 trip; V73 raised it and V74/V75 FAULTED',
           'restored to 511 at V81', 'FROZEN -- do not touch'),
 0xC40BC: ('Coulomb ramp knee', 'motor-rate divisor in the friction ramp',
           'widens the saturated ramp; no step, no relay', 'V108 (restored Honda 600)', 'UNFLOWN'),
 0xC40D2: ('K1 modelled friction', '|model|-proportional Coulomb coefficient',
           'back to Honda; removes drag V89 added', 'V177', 'UNFLOWN'),
 0xC40DC: ('accel EMA alpha', 'coefficient of the gp-0x6c2c acceleration EMA',
           'back to Honda; changes how fast the acceleration estimate tracks', 'V179', 'UNFLOWN'),
 0xC60A8: ('biquad A8', 'assist-section denominator coefficient', 'THE GRIND NOTCH', 'V188',
           'UNFLOWN'),
 0xC60AC: ('biquad AC', 'assist-section denominator coefficient', 'THE GRIND NOTCH', 'V188',
           'UNFLOWN'),
 0xC60B0: ('biquad B0', 'sets the NOTCH FREQUENCY (roots on the unit circle)',
           'moves Honda\'s notch from 55.226 Hz onto the grind at 19.40 Hz', 'V188', 'UNFLOWN'),
 0xC60B4: ('biquad B4', 'section gain, pinned for unity DC', 'keeps assist level unchanged',
           'V188', 'UNFLOWN'),
 0xC61B2: ('LKAS tracking clip', 'tracks the LKAS gain', 'keeps the clip proportional to the gain',
           'V102', 'FLOWN'),
 0xC61B4: ('LKAS tracking clip', 'tracks the LKAS gain', 'keeps the clip proportional to the gain',
           'V102', 'FLOWN'),
 0xC63A6: ('Path-2 w[3]', 'weight on the gp-0x6b26 inertia term', 'halved',
           'V181', 'UNFLOWN'),
 0xC640A: ('oscillation fallback L', 'inertia gain used when the reversal counter SATURATES',
           'removes the anti-damping term during a detected oscillation instead of fixing it '
           'at -8192', 'V191', 'UNFLOWN, and inert unless the detector fires'),
 0xC64AE: ('Path-2 enable flag', 'enables the gp-0x6bc2 acceleration term into gp-0x6ad6',
           'disables a second omega^2 acceleration feedback; ZERO effect at DC', 'V190',
           'UNFLOWN, sign rests on consistency with the gp-0x6b26 result'),
 0xC64DD: ('detector DWELL (HYST)', 'reversal-counter dwell limit, in 1 kHz ticks',
           'opens the detector window from f>10 Hz to f>5 Hz so the 8 Hz ratchet is COUNTABLE',
           'V193', 'UNFLOWN -- the only cell here that can change NORMAL driving'),
 0xC691A: ('oscillating slew curve', 'gp-0x69a0 rate limit used when the detector fires',
           'tightens it by Honda\'s own 0.60 ratio, incl. the low index where Honda gives none',
           'V192', 'UNFLOWN, inert unless the detector fires'),
 0xC6CD0: ('THE LKAS GAIN', 'private forward gain; reach = (clip * cal) >> 15',
           '6x. Was 4x when V88 confirmed the grind fixed; 8x at V101 when it came back',
           'V102', 'FLOWN -- and the 2x2 names this as the grind CARRIER'),
 0xC646C: ('shared sensor scale', 'the gain the four FEEDBACK readers use',
           'written back down to Honda 891 so only the forward path is boosted', 'V57', 'FLOWN'),
 0xD7A5C: ('friction table (m26)', 'x1.5 friction row', 'returned to Honda', 'V81', 'UNFLOWN'),
 0xD7A6C: ('friction table (m27)', 'x1.5 friction row', 'returned to Honda', 'V81', 'UNFLOWN'),
 0x13109: ('part-number MARKER', 'the ASCII part number string',
           '39990-TVA-A160 -> 39990-TVA,A160: a UDS-visible marker that the ECU is running '
           'modified firmware', 'inherited, pre-V122', 'FLOWN, cosmetic'),
 0x14120: ('part-number MARKER (2nd copy)', 'the ASCII part number string',
           'same hyphen -> comma marker', 'inherited, pre-V122', 'FLOWN, cosmetic'),
 0xC62EA: ('low-speed steer lockout', 'the speed floor below which steering assist is cut',
           '320 -> 0: the lockout is DISABLED, so the authority ramp is not killed at low speed',
           'V57', 'FLOWN'),
 0xC659A: ('limit family x5 (float)', 'float32 limits, +-1.0 -> +-5.0',
           'raises a family of saturation limits five-fold', 'V57', 'FLOWN, not individually traced'),
 0xC674E: ('limit family x5 (int)', 'integer limits, +-1024 -> +-5120',
           'the same 5x family in integer form', 'V57', 'FLOWN, not individually traced'),
 0xC61C0: ('three limits -> -1', '1600 / 896 / 1280 -> 0xFFFF',
           'saturated, i.e. effectively removed as constraints', 'V57', 'FLOWN'),
 0xC64B4: ('two limits -> -1, one -> 255', '24688 / 16438 / 112',
           'saturated', 'V57', 'FLOWN'),
 0xC6446: ('Lever B', 'the LKAS-gated r24 arm', '512 -> 5244', 'V88',
           'FLOWN, grinding FIXED on-car'),
 0xC649B: ('biquad ARM', 'the cal that enables the assist biquad',
           '0 -> 1, engagement-gated via the V103 code edits', 'V103', 'FLOWN'),
 0xC4B34: ('the 164-byte telemetry CAVE', 'code cave', 'packs probe bits into CAN',
           'V92 onward', 'FLOWN, instrument'),
 0x55C0E: ('cave HOOK', 'the jarl into the cave', 'installs the cave', 'V92 onward',
           'FLOWN, instrument'),
 0xE4194: ('assist-map ceiling x72', '8 runs x 9 LERP Y entries, 15360 -> 16384',
           'INERT: 0xC61BE still clamps this path at 15360, so every raised entry is cut back. '
           'Half of a two-part edit -- V108 raised the tables and PULLED the clamp raise',
           'V108', 'CARRIED BY ACCIDENT, provably inert'),
 0xD77EE: ('FactorC m27 Y[0]', 'base-assist damper floor at low index',
           'back to Honda 0; removes a RELAY our own chain created by accident', 'V189',
           'UNFLOWN, and INERT -- mode 27 is unreachable'),
}


def val(b, a, n):
    if n == 1:
        return b[a]
    if n == 2:
        return struct.unpack_from('<h', b, a)[0]
    return ' '.join('%02x' % x for x in b[a:a + n])


print('%-9s %-11s %-11s %-26s %s' % ('addr', 'stock', 'V194', 'what it is', 'build / status'))
print('-' * 118)
unattributed = []
for lo, hi in pay:
    n = hi - lo
    key = next((k for k in K if lo <= k < hi or k <= lo < k + 4), None)
    if key is None:
        for base, span in ((0xC659A, 0x40), (0xC674E, 0x30), (0xC61C0, 8), (0xC64B4, 8),
                           (0xC4B34, 164), (0x55C0E, 4)):
            if base <= lo < base + span:
                key = base
                if lo != base:
                    key = -1
                break
    if key == -1:
        continue
    if key is None and 0xE4000 <= lo < 0xE6000:
        key = 0xE4194   # the 72-entry assist-map ceiling block
        if lo != 0xE4194:
            continue    # report the block once
    if key is None:
        unattributed.append((lo, hi))
        continue
    nm, phys, eff, build, status = K[key]
    sv, nv = val(st, key, min(n, 2)), val(v194, key, min(n, 2))
    print('%-9s %-11s %-11s %-26s %s' % ('0x%05X' % key, sv, nv, nm[:26], build))
    print('%-9s %s' % ('', '  physically: ' + phys))
    print('%-9s %s' % ('', '  on the car: ' + eff))
    print('%-9s %s' % ('', '  STATUS: ' + status))
print('')
if unattributed:
    print('!! %d payload run(s) NOT attributed -- these must be explained before any flash:'
          % len(unattributed))
    for lo, hi in unattributed:
        print('     0x%05X..0x%05X (%d bytes)  stock %s  V194 %s'
              % (lo, hi, hi - lo,
                 ' '.join('%02x' % x for x in st[lo:hi][:8]),
                 ' '.join('%02x' % x for x in v194[lo:hi][:8])))
else:
    print('=> every payload run is attributed.')
print('')
print('--- what the FLYING build (V122) already has, for contrast ---')
fly = [a for a in range(START, END) if v122[a] != st[a] and (a & 0xFFF) < 0xFFC]
print('    V122 vs stock: %d payload bytes' % len(fly))
print('    V194 vs stock: %d payload bytes' % sum(h - l for l, h in pay))
newc = sorted({k for k in K if any(l <= k < h for l, h in pay)
               and any(v194[a] != v122[a] for a in range(k, min(k + 4, END)))})
print('    cells V194 changes RELATIVE TO WHAT HE DRIVES TODAY: %d'
      % len(newc))
for k in newc:
    print('      0x%05X  %-28s %s' % (k, K[k][0], K[k][3]))
