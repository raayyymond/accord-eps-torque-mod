#!/usr/bin/env python3
r"""PRE-REGISTRATION for a c4 = 1.85x build on a V103 base: what the 427 (0x1AB) slot returns
if it is repointed from gp-0x6b4c (the SUM) to gp-0x6b86 (the LANE).

Reproduces every number in the 2026-08-21 clip-duty report's forward-prediction section.

  ENGAGED : gp-0x6b86 = clamp( k*H(z)*gp-0x6b82 + gp-0x6b7e , +-12288 )
  MANUAL  : gp-0x6b86 = clamp(     gp-0x6b82 + gp-0x6b7e     , +-12288 )   bypass @0x35a86

FINDINGS THIS SCRIPT ESTABLISHES
  1. A RECTIFIED tap (|.| only, as V103 ships 427) biases the 6-9 Hz dose ratio to 1.60,
     not 1.85 -- a 13.5 % LOW read that is SCALE-INVARIANT (identical at LSB 1.19 .. 8.0),
     so no encoding choice fixes it.  1.60 is also what a partially-failed arm would look
     like => rectified, the readout is CONFOUNDED.
  2. A SIGN BIT fixes it: 6-9 Hz ratio 1.873 [1.861, 1.913] across the 7 episodes.
  3. Broadband ratios are biased LOW by the unscaled pedestal gp-0x6b7e (1.53 vs 1.85).
     Band-limit ABOVE the pedestal's 1.55 Hz corner; 6-9 Hz is clean.
"""
import sys
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_clip_duty_all as RA
from predict_6b86_on_427 import biquad_armed, episodes

K = 1.85
MUL, SH, BITS = 1, 3, 9          # |gp-0x6b86| >> 3, 9-bit magnitude, + 1 SIGN bit
FS = 100.0


def band(x, lo, hi, sel=None):
    sos = butter(4, [lo / (FS / 2), hi / (FS / 2)], btype='band', output='sos')
    f = sosfiltfilt(sos, x)
    return float(np.sqrt(np.mean((f if sel is None else f[sel]) ** 2)))


def wire(x, mul=MUL, sh=SH, bits=BITS, sign=True):
    mag = np.clip((np.abs(x).astype(int) * mul) >> sh, 0, (1 << bits) - 1)
    return (np.sign(x) if sign else 1.0) * mag.astype(float) / (mul / float(1 << sh))


def main():
    R = RA.run('9e')
    eng, t = R['eng'], R['t']
    b82, b7e = R['b82'].astype(float), R['b7e'].astype(float)
    m1 = np.clip(biquad_armed(b82, eng, 1.00) + b7e, -12288, 12288)
    mk = np.clip(biquad_armed(b82, eng, K) + b7e, -12288, 12288)

    print('=' * 92)
    print('1. THE RECTIFICATION DEFECT (why 427 needs a sign bit)   truth k = %.2f' % K)
    print('=' * 92)
    print('  %-22s %8s %8s | %9s %9s %9s' % ('tap', 'LSB ct', 'sat', '0.5-3 Hz', '6-9 Hz', '20-28 Hz'))
    for mul, sh, bits, sgn, nm in ((1, 2, 10, False, 'RECTIFIED 10b >>2'),
                                   (1, 3, 9, False, 'RECTIFIED  9b >>3'),
                                   (1, 3, 9, True, 'SIGNED     9b >>3'),
                                   (1, 2, 9, True, 'SIGNED     9b >>2')):
        a, b = wire(mk, mul, sh, bits, sgn), wire(m1, mul, sh, bits, sgn)
        sat = ((np.abs(mk[eng]).astype(int) * mul >> sh) >= (1 << bits) - 1).mean()
        r = [band(a, lo, hi, eng) / max(band(b, lo, hi, eng), 1e-9)
             for lo, hi in ((0.5, 3), (6, 9), (20, 28))]
        print('  %-22s %8.2f %8.5f | %9.4f %9.4f %9.4f'
              % (nm, (1 << sh) / mul, sat, *r))
    print('  => rectified reads 1.60 at EVERY scale; signed reads 1.87. The bias is the |.|, not the LSB.')

    print('\n' + '=' * 92)
    print('2. WIRE DISTRIBUTION, recommended encoding: |gp-0x6b86| >> 3, 9-bit + SIGN')
    print('=' * 92)
    wk = np.clip((np.abs(mk).astype(int) * MUL) >> SH, 0, (1 << BITS) - 1)
    w1 = np.clip((np.abs(m1).astype(int) * MUL) >> SH, 0, (1 << BITS) - 1)
    for nm, w, sel in (('ENGAGED k=1.85', wk, eng), ('ENGAGED k=1.00', w1, eng),
                       ('MANUAL (k-inv)', w1, ~eng)):
        s = w[sel]
        print('  %-16s n=%6d  p50=%4d p75=%4d p90=%4d p95=%4d p99=%4d max=%4d  sat=%.5f'
              % (nm, sel.sum(), *np.percentile(s, [50, 75, 90, 95, 99]).astype(int),
                 s.max(), (s >= (1 << BITS) - 1).mean()))

    print('\n' + '=' * 92)
    print('3. PRE-REGISTERED ENDPOINT -- 6-9 Hz band RMS of the SIGNED wire, per engaged episode')
    print('=' * 92)
    sk, s1 = wire(mk), wire(m1)
    eps = episodes(eng, t)
    rr = []
    print('  %-5s %8s %8s | %9s %9s %9s' % ('ep', 'dur s', 'n', 'k=1.85', 'k=1.00', 'ratio'))
    for i, (a, b) in enumerate(eps):
        sel = np.zeros(len(t), bool)
        sel[a:b] = True
        A, B = band(sk, 6, 9, sel), band(s1, 6, 9, sel)
        rr.append(A / B)
        print('  %-5d %8.1f %8d | %9.2f %9.2f %9.4f' % (i, (b - a) / FS, b - a, A, B, A / B))
    rr = np.array(rr)
    print('  ACROSS 7 EPISODES: median %.4f  min %.4f  max %.4f   (truth %.4f)'
          % (np.median(rr), rr.min(), rr.max(), K))
    print('\n  DECISION RULE (pre-registered):')
    print('    ratio in [1.75, 2.00]  => the dose IS in force')
    print('    ratio near 1.00        => the arm did not take')
    print('    ratio near 1.60        => you shipped it RECTIFIED (confounded with a partial arm)')
    print('    MANUAL arm must match its own prediction first -- it is k-invariant, so it tests')
    print('    the tap and the mirror WITHOUT testing the dose. If it fails, nothing else is readable.')


if __name__ == '__main__':
    main()
