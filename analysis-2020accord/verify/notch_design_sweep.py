# -*- coding: utf-8 -*-
"""
RE-DESIGN THE NOTCH UNDER THE LINEAGE'S OWN CONSTRAINTS.

BUILD-LINEAGE.md, V105 section, states two rules this kit learned by nearly shipping violations:

  "THE HIDDEN ONE: fixing DC with poles at the notch angle (the textbook narrow notch) forces
   max|H| to 1.098-1.608 ... Fix: Honda's own poles-BELOW-zeros layout (stock is poles 42.3 /
   zeros 55.2).  Check max|H| over 0-500 Hz against stock's 1.0000 before shipping any biquad edit."

  V108 E1, reverting V105: "removes +14.0 dB at 61.1 Hz and restores Honda's 55.2 Hz null" --
  "across 54-74.5 Hz V105's coefficients leave the base-assist lane a geometric-mean 5.15x
   (+14.2 dB) louder than Honda's."

V195/V196 put the poles AT the notch angle.  That is the named trap.  This sweeps the poles-below-
zeros layout instead and scores every candidate on all four axes at once:

    max|H| over 0-500 Hz          must be <= 1.0000 (stock's value)          HARD GATE
    added phase at 5 Hz vs Honda  LKAS band -- the peak-oscillation currency  minimise
    54-74.5 Hz geomean vs Honda   the statistic V108 reverted V105 on (5.15x) minimise
    18-21 Hz attenuation          what the notch is FOR                       maximise
"""
import os
import struct

import numpy as np

FS = 1000.0
ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
IMG = os.path.join(ROOT, 'analysis-2020accord',
                   '_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin')
B = open(IMG, 'rb').read()
HONDA = [struct.unpack_from('<f', B, a)[0] for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]

FZ = 19.75           # the grind, where V195 fitted the notch on cs_rate
FGRID = np.concatenate([np.linspace(0.05, 100, 4000), np.linspace(100, 500, 1000)])
LKAS = (FGRID >= 1) & (FGRID <= 5)
GRIND = (FGRID >= 18) & (FGRID <= 21)
HFB = (FGRID >= 54) & (FGRID <= 74.5)


def resp(c, f):
    a1, a2, b1, g = c
    z = np.exp(2j * np.pi * f / FS)
    return g * (z * z + b1 * z + 1) / (z * z + a1 * z + a2)


def design(fz, fp, r):
    b1 = -2 * np.cos(2 * np.pi * fz / FS)
    a1 = -2 * r * np.cos(2 * np.pi * fp / FS)
    a2 = r * r
    g = (1 + a1 + a2) / (2 + b1)          # unity DC, exactly as the structure forces
    return [a1, a2, b1, g]


HH = resp(HONDA, FGRID)
phH = np.degrees(np.angle(HH))
i5 = int(np.argmin(np.abs(FGRID - 5.0)))

print('=' * 100)
print('  NOTCH RE-DESIGN -- poles BELOW zeros, the layout Honda uses and V105 adopted')
print('  Honda: max|H| %.6f   zeros %.2f Hz   poles %.2f Hz   r %.4f'
      % (np.abs(HH).max(),
         np.degrees(np.arccos(-HONDA[2] / 2)) / 360 * FS,
         np.degrees(np.arccos(-HONDA[0] / (2 * np.sqrt(HONDA[1])))) / 360 * FS,
         np.sqrt(HONDA[1])))
print('=' * 100)

rows = []
for fp in np.arange(6.0, 19.6, 0.25):
    for r in np.arange(0.86, 0.995, 0.005):
        c = design(FZ, fp, r)
        H = resp(c, FGRID)
        m = np.abs(H)
        if m.max() > 1.0000:
            continue                      # the lineage's HARD GATE
        d5 = np.degrees(np.angle(H))[i5] - phH[i5]
        hf = np.exp(np.mean(np.log(m[HFB] / np.abs(HH)[HFB])))
        att = np.exp(np.mean(np.log(m[GRIND] / np.abs(HH)[GRIND])))
        rows.append((hf, abs(d5), 1.0 / att, fp, r, m.max(), c))

if not rows:
    raise SystemExit('no candidate passes max|H| <= 1.0')

print('  %d of %d candidates pass the max|H| <= 1.0 gate' % (len(rows), 55 * 27))
print()
print('  BEST BY 54-74.5 Hz EXCESS (the statistic V108 reverted V105 on; V105 scored 5.15x)')
print('  pole Hz     r     max|H|    54-74.5 vs Honda    phase@5Hz    18-21 Hz attenuation')
print('  ' + '-' * 92)
for hf, d5, att, fp, r, mx, c in sorted(rows)[:6]:
    print('   %6.2f  %.3f   %.6f      %6.2fx (%+5.1f dB)     %+6.2f deg      %8.1fx'
          % (fp, r, mx, hf, 20 * np.log10(hf), -d5 if d5 else 0.0, att))

print()
print('  BEST BY LKAS PHASE (V196 costs -7.80 deg at 5 Hz)')
print('  pole Hz     r     max|H|    54-74.5 vs Honda    phase@5Hz    18-21 Hz attenuation')
print('  ' + '-' * 92)
for hf, d5, att, fp, r, mx, c in sorted(rows, key=lambda x: x[1])[:6]:
    print('   %6.2f  %.3f   %.6f      %6.2fx (%+5.1f dB)     %+6.2f deg      %8.1fx'
          % (fp, r, mx, hf, 20 * np.log10(hf), -d5, att))

# a balanced pick: rank-sum across the three costs, attenuation kept above a floor
cand = [x for x in rows if x[2] >= 20.0]
if cand:
    hfr = {id(x): i for i, x in enumerate(sorted(cand))}
    phr = {id(x): i for i, x in enumerate(sorted(cand, key=lambda x: x[1]))}
    best = min(cand, key=lambda x: hfr[id(x)] + phr[id(x)])
    hf, d5, att, fp, r, mx, c = best
    print()
    print('=' * 100)
    print('  BALANCED PICK (attenuation >= 20x, then rank-sum of HF excess and LKAS phase)')
    print('    zeros %.4f Hz   poles %.4f Hz   r %.4f' % (FZ, fp, r))
    print('    a1 %+.9f   a2 %+.9f   b1 %+.9f   g %+.9f' % tuple(c))
    print('    max|H| %.6f   (Honda %.6f, V196 1.7175 -- the trap)' % (mx, np.abs(HH).max()))
    print('    54-74.5 Hz vs Honda  %.2fx (%+.1f dB)   -- V105 scored 5.15x and was REVERTED'
          % (hf, 20 * np.log10(hf)))
    print('    added phase at 5 Hz  %+.2f deg           -- V196 costs -7.80 deg' % (-d5))
    print('    18-21 Hz attenuation %.1fx' % att)
    print('=' * 100)
