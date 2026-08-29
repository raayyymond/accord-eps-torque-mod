# -*- coding: utf-8 -*-
"""GATE 2 on the base-assist lane: what the engaged/manual pole difference does to 1 - P.L.

Mirrors the decompiled integer arithmetic exactly (FUN_000352b4, 1 kHz):

    iVar24 += (iVar20 - iVar24) * k >> 11          # gp-0x381c, 32-bit state
    k = clamp(sel, 2, 0xCC)
    sel = cal(0xC6382)=41                if (iVar14 != 0 && return_centre != 0)   MANUAL
        = LERP(0xC6906..)= 20            otherwise                                ENGAGED

Return-centre is DEAD ENGAGED (0.0000 duty / 75,227 frames) and live in manual, so the two
arms genuinely take different poles.  Per the loop topology Z = (Z0 + P.F)/(1 - P.L), the
assist map is the dominant L term, so a phase change on it moves the denominator directly.

The tracer's census treated this lane as MEMORYLESS (transfer "real, 0 deg").  It is not --
this lag is in series with it.  That is a correction to the census, computed here.
"""
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 1000.0
F = 8.64                      # the measured ratchet frequency
K_ENG, K_MAN = 20, 41


def lag_H(k, f, fs=FS):
    """Exact transfer of  y[n] = y[n-1] + (x[n]-y[n-1])*k/2048  at frequency f."""
    a = k / 2048.0
    z = np.exp(2j * np.pi * f / fs)
    return a / (1 - (1 - a) * z ** -1)


def integer_check(k, f, n=200000):
    """Drive the REAL integer recursion with a sinusoid and measure gain/phase, to confirm
    the closed form. Uses the same >>11 and 32-bit state the firmware uses."""
    t = np.arange(n) / FS
    x = np.round(20000 * np.sin(2 * np.pi * f * t)).astype(np.int64)
    y = np.int64(0)
    out = np.empty(n, dtype=np.int64)
    for i in range(n):
        y = y + ((int(x[i]) - int(y)) * k >> 11)
        out[i] = y
    s = n // 2
    ref = np.exp(-2j * np.pi * f * t[s:])
    X = np.sum(x[s:] * ref)
    Y = np.sum(out[s:] * ref)
    return abs(Y / X), np.angle(Y / X, deg=True)


print('base-assist output lag at the ratchet frequency %.2f Hz\n' % F)
print('%-10s %-6s %-10s %-12s %-10s %s'
      % ('arm', 'k', 'corner Hz', '|H| closed', 'arg deg', 'integer sim |H| / arg'))
for nm, k in (('ENGAGED', K_ENG), ('MANUAL', K_MAN)):
    H = lag_H(k, F)
    a = k / 2048.0
    fc = -np.log(1 - a) * FS / (2 * np.pi)
    gi, pi_ = integer_check(k, F)
    print('%-10s %-6d %-10.2f %-12.4f %-10.2f %.4f / %.2f'
          % (nm, k, fc, abs(H), np.angle(H, deg=True), gi, pi_))

He, Hm = lag_H(K_ENG, F), lag_H(K_MAN, F)
print('\nengaged vs manual at %.2f Hz:' % F)
print('  magnitude  %.4f vs %.4f   => engaged is %.2fx SMALLER'
      % (abs(He), abs(Hm), abs(Hm) / abs(He)))
print('  phase      %.2f vs %.2f deg  => engaged lags %.2f deg MORE'
      % (np.angle(He, deg=True), np.angle(Hm, deg=True),
         np.angle(Hm, deg=True) - np.angle(He, deg=True)))

# What that does to 1 - P.L, using the tracer's byte-derived loop numbers at 7.79 Hz.
print('\neffect on the denominator 1 - P.L  (tracer census, |L| and arg at 7.79 Hz)')
print('%-24s %-16s %-16s %s' % ('case', '|1-P.L|', 'implied Q gain', 'note'))
for nm, Lmag, Larg in (('NOMINAL s=1.5', 1.876, -163.91), ('CEILING s=2.0', 2.825, -148.10)):
    for arm, H in (('as censused (no lag)', 1.0 + 0j), ('engaged lag', He / abs(He)),
                   ('manual lag', Hm / abs(Hm))):
        # the assist map is the dominant term; rotate the whole L by the lag's phase as an
        # upper bound on the effect, and note it as such
        L = Lmag * np.exp(1j * np.deg2rad(Larg)) * (H / abs(H) if abs(H) else 1)
        P = 1.0 / Lmag        # |P.L| ~ 1 at the peak, per the census
        den = abs(1 - P * L)
        print('%-24s %-16.4f %-16.2f %s'
              % ('%s / %s' % (nm.split()[0], arm), den, 1.0 / den if den > 0 else np.inf,
                 'smaller denominator = sharper, less damped'))

print("""
[BELIEF, stated as such] the rotation is applied to the WHOLE loop, which overstates it --
only the assist-map share of L actually carries this lag. The sign of the effect is what
matters here: the ENGAGED arm has the slower pole, hence MORE phase lag, hence a SMALLER
1 - P.L, hence a sharper and less-damped mode -- in the same direction as the measured
engaged-only ratchet. What would close it: the assist map's share of L at 8.64 Hz, which
needs the RAM-resident 10-knot curve (gp-0x641e.. / gp-0x6444..), not in the image.""")
