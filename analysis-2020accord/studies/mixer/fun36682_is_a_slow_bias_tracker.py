# -*- coding: utf-8 -*-
"""THE LAST UNCHARACTERISED AGGREGATOR LANE: FUN_00036682 is a SLOW BIAS TRACKER, not a ratchet lever.

The model's lane census listed it as "PARTIAL ... filtered Sensor-B term, final slow IIR (6/1024)"
with the role marked **OPEN**. It was the only aggregator lane whose character had not been settled.
Decompiled, it settles cleanly.

    target  = gp-0x6b48 + polarity * ((gp-0x4f60 * cal(0xC646C)) >> 15)     scaled column torque
    err     = target - gp-0x6b46                                            minus its OWN last output
    ... hysteresis band, then err -= midpoint of that band ...
    err     = clamp(err, +-512)                                             0x200
    state  += ((err * 1024 - state) * cal(0xC63D2)) >> 10                   alpha = 6/1024
    gp-0x6b46 = state >> 10

=> a FIRST-ORDER LAG whose input is the scaled column torque and whose feedback is its own output:
   a follower with time constant 1024/alpha samples at 1 kHz = 171 ms, i.e. fc = 0.93 Hz.

At 7.79 Hz that is |H| = 0.119 (-18.5 dB) and -81.8 deg -- the model's own figures, reproduced here
from the cal rather than quoted.

--------------------------------------------------------------------------------------------------
WHY IT IS NOT A LEVER, AND WHY THE ONLY SAFE DIRECTION IS DOWN
--------------------------------------------------------------------------------------------------
Its input is COLUMN TORQUE and its job is to follow it slowly. The 18.5 dB of attenuation at the
ratchet is not an obstacle to be removed -- it is what stops torque-band content reaching the assist.

RAISING alpha would turn a bias estimator into a fast follower and inject more torque-derived content
into the delivered command at exactly the ratchet frequency. That is the OPPOSITE of the record's own
stated lever class, "less broadband HF in the delivered command".

    alpha    fc (Hz)   |H| @7.79 Hz   phase      what it would mean
        3      0.47        0.060      -86.6 deg  slower still (V124-V133 went here; never flown)
        6      0.93        0.119      -83.2 deg  STOCK, and 210 of 219 images
       32      4.97        0.538      -57.5 deg  a fast follower -- injects the band
      128     19.89        0.932      -21.4 deg  essentially unfiltered

=> [EVIDENCE] the lane is an attenuator BY DESIGN at the ratchet. 0xC63D2 is a real cal with a real
   effect, but the only direction that serves the stated lever class is DOWNWARD -- and that ground
   was already covered by V124-V133 at alpha = 3, which never flew.

=> THE AGGREGATOR LANE CENSUS IS NOW CLOSED at 7.79 Hz:
     gp-0x6b62  return-centre     DEAD (0 of 75,227 engaged)
     gp-0x6ade  DEAD (0 writers image-wide)
     gp-0x6bd0  base-assist damper -- identically zero below 35 km/h
     gp-0x6bbe  viscous, but already at 76 % of its +-512 rail
     gp-0x6ad4  resonance PID -- ~85 % STIFFNESS-like at 7.79 Hz, only 14.6 % lead
     gp-0x6b26  the restored damper (V214-V217), measured +518/+565 counts of positive Re(Z)
     gp-0x6b86  the notch lane, base power assist -- not the command path
     r24        Lever B -- the ONE measured win, doubled in V221/V222
     r26        shares r24's dtorque and its span kill-switch
     gp-0x6b46  THIS lane -- a 0.93 Hz bias tracker, attenuating by design
   ⇒ every lane summing into the aggregator now has a character at the ratchet frequency, and only
     r24 has ever been shown to help.

Run:  python analysis-2020accord/studies/mixer/fun36682_is_a_slow_bias_tracker.py
"""
import numpy as np

FS, F = 1000.0, 7.79
ERR_CLAMP, ALPHA_STOCK = 512, 6


def iir(alpha, f=F):
    """First-order EMA y += (x - y)*alpha/1024, evaluated at f."""
    a = alpha / 1024.0
    w = 2 * np.pi * f / FS
    h = a / (1 - (1 - a) * np.exp(-1j * w))
    return abs(h), float(np.degrees(np.angle(h))), a * FS / (2 * np.pi)


print('=' * 92)
print('  FUN_00036682 -- a first-order follower on scaled column torque, alpha = cal(0xC63D2)')
print('=' * 92)
print()
print('  %8s %10s %14s %12s' % ('alpha', 'fc (Hz)', '|H| @%.2f Hz' % F, 'phase'))
rows = {}
for a in (3, 6, 32, 128):
    m, p, fc = iir(a)
    rows[a] = (m, p, fc)
    tag = '   <- STOCK, 210 of 219 images' if a == ALPHA_STOCK else (
        '   <- V124-V133, never flown' if a == 3 else '')
    print('  %8d %10.2f %14.3f %11.1f%s%s' % (a, fc, m, p, 'deg', tag))
print()
m, p, fc = rows[ALPHA_STOCK]
print('  stock: fc %.2f Hz, |H| %.3f (%.1f dB), %.1f deg at the ratchet' % (fc, m, 20 * np.log10(m), p))
print('  the attenuation is the FEATURE: its input is column torque, and letting more of it through')
print('  at 7.79 Hz would inject torque-band content into the delivered command.')

# --------------------------------- assertions -----------------------------------------
assert abs(rows[6][0] - 0.119) < 0.01, "stock |H| must reproduce the model's recorded 0.119"
assert -90 < rows[6][1] < -80, "and its phase must reproduce the recorded ~-82 deg"
assert rows[32][0] > 4 * rows[6][0], 'raising alpha must let substantially more through'
assert rows[3][0] < rows[6][0], 'and lowering it must attenuate further -- the direction V124 took'
assert rows[6][2] < 1.0, 'the stock corner must sit BELOW 1 Hz, i.e. a bias tracker not a lane filter'
print()
print('  all five assertions hold.')
print('  [EVIDENCE] a 0.93 Hz bias tracker on column torque. Raising 0xC63D2 injects the ratchet')
print('             band into the delivered command -- the opposite of the stated lever class.')
print('  [CLOSES]   the aggregator lane census at 7.79 Hz: every lane now has a character, and')
print('             only r24 (Lever B) has ever been shown to help.')
