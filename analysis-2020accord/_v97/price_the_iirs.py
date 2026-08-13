#!/usr/bin/env python3
"""Price the four one-pole IIRs of FUN_0003b8f6, and cross-check 0xC40D4 against V86.

Owner: close-the-sign agent. Study-only, no firmware written.

Each filter mirrors the decompiled arithmetic exactly:

    0x3b956  msubf.s r16,r13,r12,r8   e = x*(1/1024) - S      r13 = 0x3A800000 = 2^-10
    0x3b95e  mulf.s  r16,r8,r8        e = e * (float)cal
    0x3b966  maddf.s r11,r8,r12,r16   S = S + e * (1/4096)    r11 = 0x39800000 = 2^-12

=>  S += (x/1024 - S) * cal/4096      i.e.  alpha = cal / 4096
=>  H(z) = alpha / (1 - (1-alpha) z^-1)

Sample rate: 1000 Hz.  EVIDENCE, not assumption --
  FUN_0003b8f6 (jarl @0x2240e) and FUN_00038148 (jarl @0x22676) are both called
  from FUN_0002214a under the IDENTICAL guard `uVar4 != 0`, uVar4 = (1 << (gp-0x67fa & 0xf)) & 0x830.
  Same guard variable, same expression, no counter/modulo/decimation between them.
  So whatever rate one runs at, the other runs at.  fw-loop pinned FUN_00038148
  at 1 kHz; the calibration block below re-derives it independently.
"""
import cmath
import math

FS = 1000.0
BANDS = [6.0, 7.79, 9.0]


def h(alpha, f, fs=FS):
    """One-pole IIR  y += (x-y)*alpha."""
    z = cmath.exp(-2j * math.pi * f / fs)
    return alpha / (1.0 - (1.0 - alpha) * z)


def report(name, cal, stages, note=""):
    a = cal / 4096.0
    fc = -math.log(1.0 - a) * FS / (2 * math.pi)   # exact 1-pole corner
    print("  %-28s cal=%-5d alpha=%.5f  fc=%6.2f Hz  x%d %s"
          % (name, cal, a, fc, stages, note))
    for f in BANDS:
        H = h(a, f) ** stages
        print("      %5.2f Hz : |H| = %.4f   phase = %+7.2f deg"
              % (f, abs(H), math.degrees(cmath.phase(H))))
    return a


print("=" * 78)
print("CALIBRATION -- reproduce a cal whose on-car phase is already known")
print("=" * 78)
print("  0xC63AC = 102 in FUN_00038148, kit record: -18.7 / -23.6 / -26.8 deg")
print("  at 6 / 7.79 / 9 Hz.  Same IIR form, alpha = cal/1024 there (not /4096).")
known = {6.0: -18.7, 7.79: -23.6, 9.0: -26.8}
worst = 0.0
for fs_try in (1000.0, 500.0, 200.0, 100.0):
    errs = []
    for f in BANDS:
        ph = math.degrees(cmath.phase(h(102 / 1024.0, f, fs_try)))
        errs.append(abs(ph - known[f]))
    tag = "  <== MATCH" if max(errs) < 0.2 else ""
    print("    fs = %6.1f Hz -> %s   max err %6.2f deg%s"
          % (fs_try, " ".join("%+7.2f" % math.degrees(cmath.phase(h(102 / 1024.0, f, fs_try)))
                              for f in BANDS), max(errs), tag))
print()

print("=" * 78)
print("THE FOUR IIRs OF FUN_0003b8f6, at fs = 1000 Hz")
print("=" * 78)
report("0xC40D4 torque input", 573, 2, "<-- V86 flew this, 573->286")
report("0xC40D8 gp-0x4f60", 3686, 2)
report("0xC40D0 friction term", 408, 1)
report("0xC40D6 accel/inertia", 246, 2)
print()

print("=" * 78)
print("V86 CROSS-CHECK: 0xC40D4  573 -> 286  (x2 cascade)")
print("=" * 78)
print("  V86 result on-car: 1.001 [0.976, 1.060] vs pre-registered [0.797, 0.875].")
print("  Well-powered NULL, CIs disjoint from the prediction.")
print()
a0, a1 = 573 / 4096.0, 286 / 4096.0
print("  %-10s %-9s %-9s %-9s %-9s %-9s" %
      ("f", "|H|573", "|H|286", "dGain", "ph573", "ph286"))
for f in BANDS:
    H0, H1 = h(a0, f) ** 2, h(a1, f) ** 2
    p0 = math.degrees(cmath.phase(H0))
    p1 = math.degrees(cmath.phase(H1))
    print("  %-10.2f %-9.4f %-9.4f %-9.4f %+8.2f  %+8.2f   dPhase = %+6.2f deg"
          % (f, abs(H0), abs(H1), abs(H1) / abs(H0), p0, p1, p1 - p0))
print()
print("  Corner frequencies:")
for cal in (573, 286):
    a = cal / 4096.0
    print("    cal %4d -> alpha %.5f -> fc = %.1f Hz (single pole)"
          % (cal, a, -math.log(1 - a) * FS / (2 * math.pi)))
print()

print("=" * 78)
print("Where 0xC40D4 sits: it filters the PLANT-MODEL TORQUE INPUT")
print("=" * 78)
print("""  0x3b93e  mul r6,r7      x = gp-0x6b98 * polarity(gp-0x6752)
  0x3b94e  ld.hu 0x50d4[tp]  stage 1 -> state gp-0x3628
  0x3b96a  ld.hu 0x50d4[tp]  stage 2 -> state gp-0x3624   = fVar18
  0x3bac0  st.h  -0x6bf6[gp] <- clamp(uVar7 * fVar18)
  0x3bc1a  st.h  -0x6bfc[gp] <- clamp((fVar18 - friction - inertia) * uVar7)
  0x3bc3e  st.h  -0x6bfe[gp] <- gp-0x6bfc, range-validated   (FUN_0003bc20)
  0x38218  ld.h  -0x6bfe[gp]                                 (FUN_00038148, iVar6)
  => 0xC40D4 sets the phase of the DOMINANT term of iVar6.""")
