#!/usr/bin/env python3
"""
loop_phase_model.py  --  fw-loop, 2026-08-12.

The 6-9 Hz loop of the 2020 Accord EPS (39990-TVA-A160), mirrored from the DECOMPILE
of code.bin, integer-exact, one annotated line per instruction site.

Rule of this kit: the integer arithmetic comes FIRST; the dB/Hz interpretation comes after.
Every constant below is read little-endian from the stock image, not typed from memory.

Reference addresses:  gp = 0xFEDF8000,  tp = 0x000BF000.
Task 1 (FUN_0002214a) = 1000 Hz  [control-task-tick-confirmed-1khz, two independent methods].
FUN_00038148, FUN_00037fe6, FUN_0003a382, FUN_00036c12, FUN_0003aa2c are ALL called
once per task-1 tick -> every block below runs at 1000 Hz.
"""

import cmath
import math
import struct

FS = 1000.0                       # task-1 tick, Hz
BANDS = (6.0, 7.79, 9.0)          # the operator's band; 7.79 is the kit's measured line
IMG = ('C:/Users/dudei/Desktop/Projects/accord-firmwares/'
       'analysis-2020accord/stock_fw_dump/code.bin')

_B = open(IMG, 'rb').read()
u16 = lambda a: struct.unpack_from('<H', _B, a)[0]
s16 = lambda a: struct.unpack_from('<h', _B, a)[0]
u8 = lambda a: _B[a]

# --------------------------------------------------------------------------------------
# 1. CALIBRATION, read from the image (little-endian; V850 is LE)
# --------------------------------------------------------------------------------------
C63A0 = u16(0xC63A0)   # FUN_00038148 w[gp-0x6bd0]   ld.hu 0x73a0,tp  @0x381??
C63A2 = u16(0xC63A2)   #               w[gp-0x6bbe]
C63A4 = u16(0xC63A4)   #               w[gp-0x6b46]
C63A6 = u16(0xC63A6)   #               w[gp-0x6b26]  ld.hu 0x73a6,tp,r15 @0x381ca
C63A8 = u16(0xC63A8)   #               w[gp-0x6b4e]
C63AA = u16(0xC63AA)   #               w[gp-0x6b4c]
C63AC = u16(0xC63AC)   # gp-0x374c one-pole IIR coefficient, Q10
C63AE = u16(0xC63AE)   # |iVar6| -> RAM-LERP index scale, Q10
C6468 = u16(0xC6468)   # sum6 polarity gain, Q10   (tp+0x746a, i.e. FUN_00007462+tp+6)
C6200 = u16(0xC6200)   # gp-0x6b70 output clamp     (FUN_000071fe+tp+2)
C63D2 = u16(0xC63D2)   # FUN_00036682 output IIR coefficient, Q10  -> gp-0x6b46
C646C = u16(0xC646C)   # FUN_00036682 torque scale, Q15
C6B26 = u16(0xC6B26)   # PID Kp,  Y[0] of the gp-0x6ac0 LERP, Q10
C6B12 = u16(0xC6B12)   # PID Ki,  flat,                       Q10
C6AE6 = u16(0xC6AE6)   # PID Kd,  flat,                       Q10
C6450 = u16(0xC6450)   # PID P-term IIR coefficient, Q10   (1024 => PASS-THROUGH)
C644A = u16(0xC644A)   # PID D-term IIR coefficient, Q10   (1024 => PASS-THROUGH)
C67B8 = u16(0xC67B8)   # PID output gain, Y[0] of gp-0x671a LERP, Q10
C61FE = u16(0xC61FE)   # PID authority when gate gp-0x67f4 == 0
C407E = u16(0xC407E)   # gp-0x6b26 output clamp (FUN_0000507c+tp+2) - the fault interlock
AUTH_SPEED_X = [u16(0xC67C2 + 2 * i) for i in range(3)]   # gp-0x6a5e index, 64 ct per km/h
AUTH_SPEED_Y = [s16(0xC67C8 + 2 * i) for i in range(3)]
AUTH_6BDA_X = [s16(0xC67A2 + 2 * i) for i in range(3)]
AUTH_6BDA_Y = [s16(0xC67A8 + 2 * i) for i in range(3)]

W6 = (C63A0, C63A2, C63A4, C63A6, C63A8, C63AA)


# --------------------------------------------------------------------------------------
# 2. INTEGER MIRRORS -- one function per decompiled block, arithmetic identical
# --------------------------------------------------------------------------------------
def sar(x, n):
    """V850 arithmetic right shift; Python >> already floors, which matches sar."""
    return x >> n


def clamp(x, lim):
    return lim if x > lim else (-lim if x < -lim else x)


def gate(x, lim):
    """The `(int)v * (uint)(v + LIM < 2*LIM+1)` idiom: pass v if |v| <= LIM, else 0."""
    return x if -lim <= x <= lim else 0


def fun38148_sum6(b4e, b4c, b26, b46, bd0, bbe):
    """FUN_00038148 @0x38148 -- the six weighted Path-2 lanes.

    Each lane:  (int)(lane * gate * (uint)w) >> 10      w = ld.hu tp+0x73aX
    Gates read from the decompile: 0x2800 for 6b4e/6b4c, 0x400 for 6b26/6b46,
    0x800 for 6bd0/6bbe.
    """
    return (sar(gate(b4e, 0x2800) * C63A8, 10)
            + sar(gate(b4c, 0x2800) * C63AA, 10)
            + sar(gate(b26, 0x0400) * C63A6, 10)     # <- 0xC63A6, the traced weight
            + sar(gate(b46, 0x0400) * C63A4, 10)
            + sar(gate(bd0, 0x0800) * C63A0, 10)
            + sar(gate(bbe, 0x0800) * C63A2, 10))


def fun38148_target(sum6, polarity):
    """@0x38148 -- sum6 -> target, the input to the gp-0x374c pole.

    (int)(((int)(sum6 * pol * (uint)cal_0xC6468) >> 10) * 0x10)
    """
    return sar(sum6 * polarity * C6468, 10) * 0x10


def fun38148_iir(state_374c, target):
    """@0x38148 -- gp-0x374c += ((target - gp-0x374c) * cal_0xC63AC) >> 10."""
    return state_374c + sar((target - state_374c) * C63AC, 10)


def fun38148_ivar6(bfe, bfa, state_374c):
    """@0x38148 -- iVar6 = gp-0x6bfe + gate(gp-0x6bfa, 20000) - (gp-0x374c >> 4)."""
    return bfe + gate(bfa, 20000) - sar(state_374c, 4)


def fun36682_iir(state_37ac, x_clamped_512):
    """FUN_00036682 @0x36682 tail -- the gp-0x6b46 output pole.

    iVar14 += ((iVar8 * 0x400 - iVar14) * cal_0xC63D2) >> 10 ; out = iVar14 >> 10
    DC gain is exactly 1 (the *0x400 and the >>10 cancel).
    """
    state = state_37ac + sar((x_clamped_512 * 0x400 - state_37ac) * C63D2, 10)
    return state, sar(state, 10)


def fun36c12(c2c, k_speed):
    """FUN_00036c12 @0x36c12 -- gp-0x6b26, a MEMORYLESS gain on gp-0x6c2c.

    iVar4 = ((int)(gate(gp-0x6c2c, 32000) * K) >> 6) * 0x111
    iVar5 = iVar4 >> 0x12 ; clamped to +-cal_0xC407E
    There is NO filter in this function -- all of gp-0x6b26's phase is upstream,
    in the gp-0x6c2c producer.
    """
    return clamp(sar(sar(gate(c2c, 32000) * k_speed, 6) * 0x111, 0x12), C407E)


def fun3a382_pid(err, st):
    """FUN_0003a382 @0x3a382 -- the P/I/D, integer-exact, stock cals.

    st = dict with the three RAM states gp-0x367c (P), gp-0x3688 (I), gp-0x3680 (D),
    plus gp-0x3684 (previous error).  Anti-windup and the authority clamp are applied
    by the caller-level mirror below; this is the linear core.

    NOTE THE ASYMMETRY, and it is the whole story of the PID's shape:
      P and D are multiplied by 0x20 AFTER their >>10.   I IS NOT.
      All three are then summed and >>5.
    """
    e = clamp(err, 0x2800)                                   # +-10240

    # --- P: iVar14 = gp-0x367c + ((((e*Kp)>>10)*0x20 - gp-0x367c) * cal_0xC6450) >> 10
    p_in = sar(e * C6B26, 10) * 0x20
    st['p'] = st['p'] + sar((p_in - st['p']) * C6450, 10)    # C6450 = 1024 -> st['p'] = p_in

    # --- I: iVar18 = ((Ki * e) >> 10) + gp-0x3688     (no *0x20)
    st['i'] = st['i'] + sar(C6B12 * e, 10)

    # --- D: d = ((e - e_prev) * Kd) >> 10 ; clamp +-0x2800 ; then *0x20 through cal_0xC644A
    d_raw = clamp(sar((e - st['e_prev']) * C6AE6, 10), 0x2800)
    st['d'] = st['d'] + sar((d_raw * 0x20 - st['d']) * C644A, 10)   # C644A = 1024 -> = d_raw*32
    st['e_prev'] = e

    # --- sum, output gain, polarity
    return sar((st['d'] + st['i'] + st['p']), 5) * C67B8 // 1024


def pid_authority(speed_kmh, gp6bda, gate_67f4=1):
    """FUN_0003a382 @0x3a6f4..0x3a79a -- the PID output clamp.

    auth = min( LERP_{gp-0x6bda}(0xC67A2/0xC67A8),
                (gate_67f4 ? LERP_{gp-0x6a5e}(0xC67C2/0xC67C8) : cal_0xC61FE) ,
                5120 )
    then * (gp-0x6765 == 3) * LERP(gp-0x6966)/32768.
    gp-0x6a5e is 64 counts per km/h.
    """
    def lerp(x, xs, ys):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        for i in range(1, len(xs)):
            if x < xs[i]:
                return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) // (xs[i] - xs[i - 1])
        return ys[-1]

    a_speed = lerp(int(speed_kmh * 64), AUTH_SPEED_X, AUTH_SPEED_Y) if gate_67f4 else C61FE
    a_bda = lerp(gp6bda, AUTH_6BDA_X, AUTH_6BDA_Y)
    return min(a_bda, min(5120, a_speed))


# --------------------------------------------------------------------------------------
# 3. FREQUENCY RESPONSE OF EACH BLOCK -- derived FROM the mirrors above, not typed in
# --------------------------------------------------------------------------------------
def z_of(f):
    return cmath.exp(1j * 2 * math.pi * f / FS)


def one_pole(a_q10, f):
    """y += ((x - y) * a_q10) >> 10   ->   H(z) = a / (1 - (1-a) z^-1)."""
    a = a_q10 / 1024.0
    z = z_of(f)
    return a / (1 - (1 - a) / z)


def pid_response(f, kp_q10=None, ki_q10=None, kd_q10=None):
    """K(z) of fun3a382_pid, in output-counts per error-count.

    From the mirror:  out = ( P + I + D ) >> 5  with
        P = (e*Kp>>10)*32          -> Kp/1024 * 32 / 32 = Kp/1024        after the >>5
        I = sum( e*Ki>>10 )        -> (Ki/1024)/32 per tick             after the >>5
        D = ((e-e')*Kd>>10)*32     -> Kd/1024                           after the >>5
    so K(z) = Kp' + Ki'/(1-z^-1) + Kd'(1-z^-1),
       Kp' = Kp/1024, Ki' = Ki/(1024*32), Kd' = Kd/1024.
    """
    kp_q10 = C6B26 if kp_q10 is None else kp_q10
    ki_q10 = C6B12 if ki_q10 is None else ki_q10
    kd_q10 = C6AE6 if kd_q10 is None else kd_q10
    kp, ki, kd = kp_q10 / 1024.0, ki_q10 / 1024.0 / 32.0, kd_q10 / 1024.0
    d = 1 - 1 / z_of(f)
    return kp + ki / d + kd * d


def delay(ticks, f):
    return cmath.exp(-1j * 2 * math.pi * f * ticks / FS)


def deg(h):
    return math.degrees(cmath.phase(h))


# --------------------------------------------------------------------------------------
# 4. REPORT
# --------------------------------------------------------------------------------------
def main():
    print('=' * 88)
    print('CALS READ FROM THE IMAGE (little-endian)')
    print('=' * 88)
    for nm, ad, v in [
        ('0xC63A0 w[gp-0x6bd0]', 0xC63A0, C63A0), ('0xC63A2 w[gp-0x6bbe]', 0xC63A2, C63A2),
        ('0xC63A4 w[gp-0x6b46]', 0xC63A4, C63A4), ('0xC63A6 w[gp-0x6b26]', 0xC63A6, C63A6),
        ('0xC63A8 w[gp-0x6b4e]', 0xC63A8, C63A8), ('0xC63AA w[gp-0x6b4c]', 0xC63AA, C63AA),
        ('0xC63AC gp-0x374c pole', 0xC63AC, C63AC), ('0xC63AE LERP idx scale', 0xC63AE, C63AE),
        ('0xC6468 sum6 gain', 0xC6468, C6468), ('0xC6200 6b70 clamp', 0xC6200, C6200),
        ('0xC63D2 6b46 pole', 0xC63D2, C63D2), ('0xC646C 36682 tq scale', 0xC646C, C646C),
        ('0xC6B26 PID Kp', 0xC6B26, C6B26), ('0xC6B12 PID Ki', 0xC6B12, C6B12),
        ('0xC6AE6 PID Kd', 0xC6AE6, C6AE6), ('0xC6450 PID P pole', 0xC6450, C6450),
        ('0xC644A PID D pole', 0xC644A, C644A), ('0xC67B8 PID out gain', 0xC67B8, C67B8),
        ('0xC61FE PID auth alt', 0xC61FE, C61FE), ('0xC407E 6b26 clamp', 0xC407E, C407E),
    ]:
        print(f'  {nm:26s} = {v}')
    print(f'  PID authority speed LERP  X(ct)={AUTH_SPEED_X} -> {[x/64 for x in AUTH_SPEED_X]} km/h')
    print(f'                            Y     ={AUTH_SPEED_Y}')
    print(f'  PID authority 6bda  LERP  X={AUTH_6BDA_X}  Y={AUTH_6BDA_Y}')
    print()

    print('=' * 88)
    print('A. PID SHAPE  -- the 32x P/D-vs-I asymmetry, and what it does to phase')
    print('=' * 88)
    kp, ki, kd = C6B26 / 1024.0, C6B12 / 1024.0 / 32.0, C6AE6 / 1024.0
    print(f'  Kp\' = {kp:.6f}   Ki\' = {ki:.8f} /tick   Kd\' = {kd:.6f} tick')
    print(f'  integral corner  fi = Ki\'/(2*pi*Kp\') * fs = {ki/(2*math.pi*kp)*FS:9.4f} Hz')
    print(f'  derivative corner fd = Kp\'/(2*pi*Kd\') * fs = {kp/(2*math.pi*kd)*FS:9.4f} Hz')
    print(f'  => the PID is FLAT between {ki/(2*math.pi*kp)*FS:.2f} Hz and '
          f'{kp/(2*math.pi*kd)*FS:.2f} Hz, and 6-9 Hz sits INSIDE that window.')
    print()
    print(f'  {"f":>6} {"|K|":>9} {"argK":>9} {"|P|":>9} {"|I|":>9} {"|D|":>9}')
    for f in BANDS:
        d = 1 - 1 / z_of(f)
        P, I, D = kp, ki / d, kd * d
        K = P + I + D
        print(f'  {f:6.2f} {abs(K):9.5f} {deg(K):+9.2f} {abs(P):9.5f} {abs(I):9.5f} {abs(D):9.5f}')
    print()
    print('  -> the PID contributes a net LEAD in 6-9 Hz. D beats I by ~1.6x here.')
    print('  -> P-pole 0xC6450 and D-pole 0xC644A are BOTH 1024 = PASS-THROUGH: the P and D')
    print('     terms are UNFILTERED on stock.  (V43 set 0xC644A to 32; it is 1024 now.)')
    print()

    print('=' * 88)
    print('B. PATH-2 PHASE LADDER  (torque -> gp-0x6b46 -> sum6 -> gp-0x6b70 -> reference)')
    print('=' * 88)
    hdr = f'  {"block":46s}' + ''.join(f'{f:>16.2f} Hz' for f in BANDS)
    print(hdr)
    rows = []
    rows.append(('FUN_00036682 out pole 0xC63D2=%d @0x367ee' % C63D2,
                 [one_pole(C63D2, f) for f in BANDS]))
    rows.append(('  + 1 tick (36682 runs @0x2291e, 38148 @0x22676)',
                 [delay(1, f) for f in BANDS]))
    rows.append(('gp-0x374c pole 0xC63AC=%d @0x38236' % C63AC,
                 [one_pole(C63AC, f) for f in BANDS]))
    for name, hs in rows:
        print(f'  {name:46s}' + ''.join(f'  {abs(h):6.4f} /{deg(h):+7.2f}' for h in hs))
    tot = [one_pole(C63D2, f) * delay(1, f) * one_pole(C63AC, f) for f in BANDS]
    print(f'  {"PATH-2 TOTAL (torque-derived lane 6b46)":46s}'
          + ''.join(f'  {abs(h):6.4f} /{deg(h):+7.2f}' for h in tot))
    tot26 = [delay(1, f) * one_pole(C63AC, f) for f in BANDS]
    print(f'  {"PATH-2 TOTAL for gp-0x6b26 (1 tick + pole)":46s}'
          + ''.join(f'  {abs(h):6.4f} /{deg(h):+7.2f}' for h in tot26))
    print()
    print('  Path-2 static gain from sum6 to the iVar6 subtrahend:')
    print(f'    target = sum6 * pol * {C6468} >>10 * 16 ;  iVar6 -= (gp-0x374c >> 4)')
    print(f'    => d(iVar6)/d(sum6) = -{C6468}/1024 = -{C6468/1024:.4f}  (x H_IIR)')
    print('    => d(gp-0x6b70)/d(sum6) = -%.4f * f\' * H   [the two sign(iVar6) cancel]'
          % (C6468 / 1024.0))
    print('    => d(PID error)/d(sum6) = +%.4f * f\' * H   [reference is SUBTRACTED]'
          % (C6468 / 1024.0))
    print("    f' = the RAM-LERP local slope. UNKNOWN. This is exactly V96's S1 measurement.")
    print()

    print('=' * 88)
    print('C. FAST-LOOP (Path 1 + PID) PHASE BUDGET, torque sensor -> motor command')
    print('=' * 88)
    print(f'  {"element":46s}' + ''.join(f'{f:>16.2f} Hz' for f in BANDS))
    fast = []
    fast.append(('torque sensor gp-0x4f60 (no EMA/IIR)', [1 + 0j for _ in BANDS]))
    fast.append(('PID K(z) @0x3a382', [pid_response(f) for f in BANDS]))
    fast.append(('aggregator FUN_0003aa2c (memoryless)', [1 + 0j for _ in BANDS]))
    fast.append(('governor FUN_0004503c (512 ct/tick: inactive)', [1 + 0j for _ in BANDS]))
    fast.append(('shaper FUN_00042af8 (0xC64C8=0 pass-through)', [1 + 0j for _ in BANDS]))
    fast.append(('ZOH 1 tick + FOC ~0.5 ms  => ~1.0 tick', [delay(1.0, f) for f in BANDS]))
    for name, hs in fast:
        print(f'  {name:46s}' + ''.join(f'  {abs(h):6.4f} /{deg(h):+7.2f}' for h in hs))
    ftot = []
    for i, f in enumerate(BANDS):
        h = 1 + 0j
        for _, hs in fast:
            h *= hs[i]
        ftot.append(h)
    print(f'  {"FAST-LOOP TOTAL":46s}' + ''.join(f'  {abs(h):6.4f} /{deg(h):+7.2f}' for h in ftot))
    print()
    print('  *** The firmware contributes only a few degrees of NET lag in the fast loop at')
    print('      6-9 Hz.  There is nowhere near 180 deg of firmware phase here, so 7.8 Hz')
    print('      CANNOT be a delay/filter-driven phase-crossover pole of this path. ***')
    print()

    print('=' * 88)
    print('D. THE PID AUTHORITY CLAMP  -- and why the loop is a RELAY in the symptom regime')
    print('=' * 88)
    print(f'  {"speed km/h":>11} {"auth ct":>9} {"|e| that saturates":>20}')
    kmag = abs(pid_response(7.79))
    for v in (2, 4, 6, 8, 10, 14, 20, 30):
        a = pid_authority(v, 9262)
        print(f'  {v:11.0f} {a:9d} {a/kmag:20.0f}')
    print()
    print(f'  |K(7.79 Hz)| = {kmag:.4f} output-counts per error-count.')
    print('  Measured median override torque = 2235 counts, 33-70 % of override time > 2560.')
    print('  => at 6-20 km/h the PID output is HARD AGAINST ITS CLAMP for most of the time:')
    print('     the lane delivers a near-constant +-auth and switches on the SIGN of')
    print('     (P + I + D).  That is a RELAY, and Kp/Ki/Kd still set its SWITCHING PHASE.')
    print()

    print('=' * 88)
    print('E. LEVERAGE -- d(phase at 7.79 Hz) per unit change, and the gain it moves')
    print('=' * 88)
    f0 = 7.79
    base_pid = deg(pid_response(f0))
    base_iir = deg(one_pole(C63AC, f0))
    base_36682 = deg(one_pole(C63D2, f0))
    print(f'  {"cal":>10} {"what":34s} {"stock":>7} {"->":>4} {"new":>7} '
          f'{"dphase@7.79":>12} {"dgain":>8}')

    def row(cal, what, stock, new, phase_fn, gain_fn, base_ph, base_g):
        p = phase_fn(new) - base_ph
        g = gain_fn(new) / base_g
        print(f'  {cal:>10} {what:34s} {stock:>7} {"->":>4} {new:>7} '
              f'{p:+11.2f} deg {g:7.3f}x')

    for kd in (1024, 3072, 4096):
        row('0xC6AE6', 'PID Kd (relay switching phase)', C6AE6, kd,
            lambda v: deg(pid_response(f0, kd_q10=v)),
            lambda v: abs(pid_response(f0, kd_q10=v)), base_pid, abs(pid_response(f0)))
    for kp in (128, 512):
        row('0xC6B26', 'PID Kp (Y[0], loop gain)', C6B26, kp,
            lambda v: deg(pid_response(f0, kp_q10=v)),
            lambda v: abs(pid_response(f0, kp_q10=v)), base_pid, abs(pid_response(f0)))
    for ki in (0, 196, 392):
        row('0xC6B12', 'PID Ki (flat)', C6B12, ki,
            lambda v: deg(pid_response(f0, ki_q10=v)),
            lambda v: abs(pid_response(f0, ki_q10=v)), base_pid, abs(pid_response(f0)))
    for a in (51, 204, 512):
        row('0xC63AC', 'Path-2 IIR pole', C63AC, a,
            lambda v: deg(one_pole(v, f0)), lambda v: abs(one_pole(v, f0)),
            base_iir, abs(one_pole(C63AC, f0)))
    for a in (3, 12, 102):
        row('0xC63D2', 'FUN_00036682 out pole -> gp-0x6b46', C63D2, a,
            lambda v: deg(one_pole(v, f0)), lambda v: abs(one_pole(v, f0)),
            base_36682, abs(one_pole(C63D2, f0)))
    print()
    print('  Pure-GAIN cells (zero phase authority, they scale a lane, not rotate it):')
    print('    0xC63A6 w[gp-0x6b26] Path-2 only   0xCBE74 gp-0x6b26 dose (Path 1 AND 2)')
    print('    0xC63A2 w[gp-0x6bbe]               0xC67C8 PID authority speed schedule')
    print()

    print('=' * 88)
    print('F. SELF-CHECK -- the integer mirrors actually run')
    print('=' * 88)
    st = {'p': 0, 'i': 0, 'd': 0, 'e_prev': 0}
    outs = [fun3a382_pid(int(500 * math.sin(2 * math.pi * f0 * n / FS)), st) for n in range(400)]
    tail = outs[200:]
    amp = (max(tail) - min(tail)) / 2.0
    print(f'  fun3a382_pid, e = 500*sin(2*pi*7.79t): output amplitude = {amp:.1f} counts')
    print(f'  predicted by |K| = {500*kmag:.1f} counts   ({100*amp/(500*kmag):.1f} % of prediction)')
    s6 = fun38148_sum6(0, 0, 300, 100, 50, 80)
    print(f'  fun38148_sum6(6b26=300, 6b46=100, 6bd0=50, 6bbe=80) = {s6}   (all w = 1024)')
    tgt = fun38148_target(s6, 1)
    print(f'  fun38148_target = {tgt}   (= sum6 * {C6468}/1024 * 16 = sum6 * '
          f'{C6468/1024*16:.3f})')
    print(f'  fun36c12(gp-0x6c2c=1200, K=500) = {fun36c12(1200, 500)}  '
          f'(clamped at +-{C407E})')
    print(f'  pid_authority(6 km/h, gp-0x6bda=9262) = {pid_authority(6, 9262)} counts')


if __name__ == '__main__':
    main()


# =======================================================================================
# G. THE TILT QUESTION (added 2026-08-12 after team-lead re-aimed the brief)
#    "V97 needs MORE loop gain at 0.5-2 Hz and LESS at 7.8 Hz."
# =======================================================================================
def tilt_report():
    F = (0.5, 1.0, 2.0, 3.0, 6.0, 7.79, 9.0, 21.0)
    print('=' * 96)
    print('G1. PID |K| and arg K vs Ki  -- does raising Ki tilt the loop?')
    print('=' * 96)
    print(f'  {"Ki":>6} {"corner":>8}  ' + ''.join(f'{f:>15.2f}Hz' for f in F))
    for ki in (0, 98, 196, 294, 392):
        kp = C6B26 / 1024.0
        corner = (ki / 1024.0 / 32.0) / (2 * math.pi * kp) * FS
        cells = ''
        for f in F:
            h = pid_response(f, ki_q10=ki)
            cells += f'  {abs(h):7.4f}/{deg(h):+6.1f}'
        print(f'  {ki:6d} {corner:7.3f}Hz  {cells}')
    print()
    print('  ratio |K(f)| / |K(7.79)|  -- the TILT itself (higher = more low-freq emphasis):')
    print(f'  {"Ki":>6}  ' + ''.join(f'{f:>12.2f}Hz' for f in F))
    for ki in (0, 98, 196, 294, 392):
        ref = abs(pid_response(7.79, ki_q10=ki))
        print(f'  {ki:6d}  ' + ''.join(f'{abs(pid_response(f, ki_q10=ki))/ref:14.3f}' for f in F))
    print()

    print('=' * 96)
    print('G2. THE ANTI-WINDUP BOUND -- why raising Ki buys less than the Bode plot says')
    print('=' * 96)
    print('  @0x3a7ae `shl 0x5,r16` bounds the integrator so that  P + I  lies in +-(AUTH*32).')
    print('  I accumulates  (Ki*e)>>10  per tick, in the un-x32 domain.')
    print(f'  {"speed":>7} {"AUTH":>6} {"bound=AUTH*32":>14} {"P at e":>9} '
          f'{"ticks for I to rail":>21}')
    for v, e in ((6, 2000), (10, 2000), (20, 2000), (6, 500), (20, 500)):
        a = pid_authority(v, 9262)
        bound = a * 32
        p = (e * C6B26 >> 10) * 32
        per_tick = (C6B12 * e) >> 10
        ticks = (bound - p) / per_tick if per_tick else float('inf')
        print(f'  {v:5d}km/h {a:6d} {bound:14d} {p:9d} {ticks:18.1f}  (e={e})')
    print('  => in the override/return regime the integrator RAILS in tens of milliseconds.')
    print('     Raising Ki makes it rail SOONER; it does not raise the delivered low-freq')
    print('     authority, which is set by AUTH, not by Ki.')
    print()

    print('=' * 96)
    print('G3. IS ANY TERM FREQUENCY-SHAPED INSIDE 1-10 Hz?  -- the tilt hunt')
    print('=' * 96)
    print(f'  {"block":42s}' + ''.join(f'{f:>13.2f}Hz' for f in (0.5, 1, 2, 6, 7.79, 9)))
    for nm, a in (('0xC63D2 = 6   -> gp-0x6b46 (fc 0.93 Hz)', C63D2),
                  ('0xC63AC = 102 -> gp-0x374c (fc 17.0 Hz)', C63AC),
                  ('0xC643C = 37/128 -> gp-0x6ac0 (fc 46 Hz)', 0)):
        if a == 0:
            hs = [(37 / 128.0) / (1 - (1 - 37 / 128.0) / z_of(f)) for f in (0.5, 1, 2, 6, 7.79, 9)]
        else:
            hs = [one_pole(a, f) for f in (0.5, 1, 2, 6, 7.79, 9)]
        print(f'  {nm:42s}' + ''.join(f'  {abs(h):5.3f}/{deg(h):+5.1f}' for h in hs))
    print()
    print('  TILT RATIO |H(1 Hz)| / |H(7.79 Hz)| :')
    for nm, a in (('0xC63D2 = 6', C63D2), ('0xC63AC = 102', C63AC)):
        print(f'    {nm:16s} {abs(one_pole(a,1.0))/abs(one_pole(a,7.79)):6.3f} x   '
              f'(raise to 102 -> {abs(one_pole(102,1.0))/abs(one_pole(102,7.79)):.3f} x)')
    print()

    print('=' * 96)
    print('G4. THE NAIVE LEVERS, PRICED')
    print('=' * 96)
    for nm, kw, vals in (('Kp 0xC6B26', 'kp_q10', (128, 256, 512)),
                         ('Kd 0xC6AE6', 'kd_q10', (1024, 2048, 4096))):
        for v in vals:
            h1 = pid_response(1.0, **{kw: v})
            h8 = pid_response(7.79, **{kw: v})
            tag = ' (stock)' if (v == C6B26 and kw == 'kp_q10') or \
                                (v == C6AE6 and kw == 'kd_q10') else ''
            print(f'  {nm} = {v:5d}{tag:9s}  |K(1Hz)| = {abs(h1):7.4f}   '
                  f'|K(7.79)| = {abs(h8):7.4f}   tilt = {abs(h1)/abs(h8):6.3f}x   '
                  f'arg(7.79) = {deg(h8):+6.1f} deg')
    print()
    print('  Stock tilt |K(1)|/|K(7.79)| = %.3f x' % (abs(pid_response(1.0)) /
                                                      abs(pid_response(7.79))))


if __name__ == '__main__':
    tilt_report()
