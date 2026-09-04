# -*- coding: utf-8 -*-
r"""PID FRAME SIZING -- Kp vs Kd of FUN_00028ea6, in the RATE frame (as built), the ANGLE frame and
the ACCELERATION frame (the operator's frame).  2026-09-04, subagent `pidframe`.

Every constant below is READ FROM THE FLOWN V283 IMAGE, not from the kit's model:
  C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/
      _v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin
  sha256 fd0c321abbf933c0d846a8eaf48b594f44f5a9bd491e4396b44abc562551ef3d
gp = 0xFEDF8000, tp = 0xBF000.  Ghidra renders a tp-relative load as `ld.hu 0x71bc, tp, rX`; the cal
address is 0xBF000 + 0x71BC = 0xC61BC.  (The off-by-0x1000 trap: it is 0xC6..., never 0xC7...)

Run:  python analysis-2020accord/studies/pidframe/pid_frame_sizing.py
"""
import math
import struct

IMG = (r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
       r"_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
       r"_plain_image.bin")
B = open(IMG, "rb").read()
U16 = lambda a: struct.unpack_from("<H", B, a)[0]          # noqa: E731  (V850 is little-endian)
U32 = lambda a: struct.unpack_from("<I", B, a)[0]          # noqa: E731

# ---------------------------------------------------------------------------------------------------
# SECTION 0 -- the cals, byte-read from the image
# ---------------------------------------------------------------------------------------------------
KI        = U16(0xC63E6)   # 0x29D9C  ld.hu 0x73e6,tp,r6    integral gain              = 50 (V283); 0 on V282
AWL       = U16(0xC61BA)   # 0x29DA0  ld.hu 0x71ba,tp,r13   anti-windup base           = 10240
I_DB      = U16(0xC62E4)   # 0x29D6E  ld.hu 0x72e4,tp,r10   integrator error deadband  = 4
P_CLAMP   = U16(0xC61BC)   # 0x29E42  ld.hu 0x71bc,tp       P clamp                    = 15360
D_CLAMP   = U16(0xC61B6)   # 0x29EE8  ld.hu 0x71b6,tp,r10   D clamp                    = 10240
SUM_CLAMP = U16(0xC61BE)   #          ld.hu 0x71be,tp       sum clamp                  = 15360
OUT_CLAMP = U16(0xC61B4)   # 0x2A1F0  ld.hu 0x71b4,tp       output clamp               = 3072
FWD_GAIN  = U16(0xC6CD0)   # 0x2A1FA  ld.h  0x7cd0,tp       forward gain               = 5346
LAG_A     = U16(0xC63EC)   # 0x2A180  output-lag pole coeff a                          = 992
LAG_B     = U16(0xC63EE)   # 0x2A194  output-lag zero coeff b                          = 507
FB_A      = U16(0xC63E8)   # 0x28F8E  feedback EMA pole coeff                          = 923
FB_B      = U16(0xC63EA)   # 0x28F92  feedback EMA input coeff                         = 1560

SEL = 7                                                    # the LIVE variant selector, measured on the wire
KP_REC = U32(0xCB994 + 4 * SEL)                            # 0x29DC6 mov 0xcb994,r10 -> 0xE5378
KD_REC = U32(0xCB7D4 + 4 * SEL)                            #                          -> 0xE511C
KP_N = U16(KP_REC)
KP_X = [U16(KP_REC + 2 + 2 * k) for k in range(5)]
KP_Y = [U16(KP_REC + 12 + 2 * k) for k in range(5)]
KD_N = U16(KD_REC)
KD_X = [U16(KD_REC + 2 + 2 * k) for k in range(4)]
KD_Y = [U16(KD_REC + 10 + 2 * k) for k in range(4)]


# ---------------------------------------------------------------------------------------------------
# SECTION 1 -- the arithmetic, mirrored EXACTLY.  One Python line per instruction, address annotated.
#              `>>` on a negative int is an arithmetic shift in Python, same as V850 `sar`.  All state
#              is int32; the image never widens past 32 bits on this path.
# ---------------------------------------------------------------------------------------------------
def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def lerp_int(xk, yk, u):
    """The image's own LERP -- integer divide (`divq`), NOT float.  0x29E26 mul / 0x29E2C divq."""
    if u <= xk[0]:
        return yk[0]
    if u >= xk[-1]:
        return yk[-1]
    for i in range(1, len(xk)):
        if u < xk[i]:
            return int((yk[i] - yk[i - 1]) * (u - xk[i - 1]) / (xk[i] - xk[i - 1])) + yk[i - 1]
    return yk[-1]


class RatePID(object):
    """FUN_00028ea6's LKAS rate PID.  Inputs per tick: sp (setpoint, the mapY LERP output, signed),
    fb (the two-sample-summed column-rate feedback), idx (the demand index, gp-0x674b)."""

    def __init__(self, ki=KI, kp_x=None, kp_y=None, kd_x=None, kd_y=None):
        self.ki = ki
        self.kp_x = kp_x or KP_X
        self.kp_y = kp_y or KP_Y
        self.kd_x = kd_x or KD_X
        self.kd_y = kd_y or KD_Y
        self.iacc8 = 0            # gp-0x6dd0 : the integrator accumulator, STORED PRE-MULTIPLIED BY 8
        self.eprev = 0x7FFFFFFF   # gp-0x6cf8 : previous error; 0x7fffffff = the "invalid" sentinel
        self.lag_s = 0            # gp-0x3d3c : the output-lag state

    def tick(self, sp, fb, idx, ramp_q15=32768, sign_6752=-1):
        # -- error -------------------------------------------------------------------------------
        # 0x29D6C  mulh  r13,r16                sp = sign * LERP(mapY, idx)
        # 0x29D72  st.h  r16,-0x6a32[gp]        publish the setpoint
        # 0x29D76  shl   0x5,r16                sp <<= 5
        # 0x29D78  sub   r26,r16                E = 32*sp - fb   (r26 = fb, summed at 0x28FA4)
        E = s32(sp * 32 - fb)

        # -- I term ------------------------------------------------------------------------------
        # 0x29D7C  sar   0x5,r6                 Ei = E >> 5
        Ei = E >> 5
        # 0x29D7E..0x29D9A                      deadband +-cal(0xC62E4)
        if Ei > I_DB:
            dbE = Ei - I_DB
        elif Ei < -I_DB:
            dbE = Ei + I_DB
        else:
            dbE = 0
        # 0x29DAC  shl 0xa,r13 ; 0x29DAE sar 0x3,r13   lim = (AWL << 10) >> 3 = AWL * 128
        lim = (AWL << 10) >> 3
        # 0x29DA8  mul r6,r9   ; 0x29DB2 sar 0x3,r9    inc  = (dbE * Ki) >> 3
        inc = (dbE * self.ki) >> 3
        # 0x29DB0  sar 0x3,r10                         iacc = iacc8 >> 3
        iacc = self.iacc8 >> 3
        # 0x29DB4  add r9,r10                          iacc += inc
        iacc = s32(iacc + inc)
        # 0x29DB6..0x29DC2  cmovgt / cmovle             clamp iacc to +-lim
        iacc = lim if iacc > lim else (-lim if iacc < -lim else iacc)
        # 0x29F18  sar 0x7,r2                          Iterm = iacc >> 7
        Iterm = iacc >> 7

        # -- P term ------------------------------------------------------------------------------
        Kp = lerp_int(self.kp_x, self.kp_y, idx)     # 0x29DC6 mov 0xcb994,r10 -> slot 7 -> 0xE5378
        # 0x29E36  mul r9,r8 ; 0x29E3E sar 0x8,r8    P = (E * Kp) >> 8
        P = s32(E * Kp) >> 8
        P = P_CLAMP if P > P_CLAMP else (-P_CLAMP if P < -P_CLAMP else P)

        # -- D term ------------------------------------------------------------------------------
        # the sentinel test: eprev outside [-0xBB800, 0x177000-0xBB800] => dE forced to 0
        eprev = E if not (-0xBB800 <= self.eprev <= 0x177000 - 0xBB800) else self.eprev
        Kd = lerp_int(self.kd_x, self.kd_y, idx)     # 0xCB7D4 -> slot 7 -> 0xE511C
        # 0x29EE0  mov r16,r8 ; 0x29EE2 sub r27,r8   dE = E - eprev
        dE = s32(E - eprev)
        # 0x29EE4  mul r7,r8 ; 0x29EEC sar 0x3,r8    D = (dE * Kd) >> 3
        D = s32(dE * Kd) >> 3
        D = D_CLAMP if D > D_CLAMP else (-D_CLAMP if D < -D_CLAMP else D)

        # -- sum, override taper, clamp ----------------------------------------------------------
        # 0x29F18 sar 0x7,r2 ; 0x29F1E add r9,r2 ; (+D)   S = (iacc >> 7) + P + D
        S = s32(Iterm + P + D)
        # 0x2A0A0 mul ; 0x2A0BC sar 0x8 ; 0x2A0BE mul ; 0x2A0C2 sar 0x8
        #   taperK = (tapA * tapB & 0xffff) >> 8 ; S = (taperK * S) >> 8   -- 254 with no driver override
        taperK = (255 * 255 & 0xFFFF) >> 8
        S = s32(taperK * S) >> 8
        S = SUM_CLAMP if S > SUM_CLAMP else (-SUM_CLAMP if S < -SUM_CLAMP else S)

        # -- output lag  (0x2A180 mul / 0x2A1A0 sar 0xa ; 0x2A194 mul / 0x2A1A6 sar 0xa ; 0x2A1AC sar 0x5)
        s_new = s32(((LAG_A * self.lag_s) >> 10) + ((S * LAG_B) >> 10))
        out = s32(self.lag_s + s_new) >> 5
        self.lag_s = s_new

        # -- engagement ramp, forward gain, output clamp -----------------------------------------
        # 0x2A1E6 mul r14,r9 ; 0x2A1EA sar 0xf,r9   out = (out * gp-0x69b0) >> 15
        out = s32(out * ramp_q15) >> 15
        # 0x2A1FE mul r13,r11 ; 0x2A202 sar 0xf,r11 T = (out * gp-0x6752 * cal(0xC6CD0)) >> 15
        T = s32(out * sign_6752 * FWD_GAIN) >> 15
        T = OUT_CLAMP if T > OUT_CLAMP else (-OUT_CLAMP if T < -OUT_CLAMP else T)

        # -- state writeback: executed on EVERY call, on BOTH branches ---------------------------
        self.eprev = E
        self.iacc8 = s32(iacc << 3)
        return dict(E=E, P=P, D=D, I=Iterm, S=S, T=T, Kp=Kp, Kd=Kd, iacc=iacc)


# ---------------------------------------------------------------------------------------------------
# SECTION 2 -- the same three terms as continuous-time gains, so they can be COMPARED
#   S = Ki_r * INT(E) dt  +  Kp_r * E  +  Kd_r * dE/dt          (E = the RATE error)
# ---------------------------------------------------------------------------------------------------
def term_gains(kp, kd, ki, T):
    Kp_r = kp / 256.0                                   # P  = (E*Kp)>>8
    Kd_r = (kd / 8.0) * T                               # D  = (dE*Kd)>>3, dE = T * dE/dt
    Ki_r = (ki / 8.0) / 32.0 / 128.0 / T                # I  = (((E>>5)*Ki)>>3 accumulated) >> 7
    return Kp_r, Kd_r, Ki_r


def term_mag(kp, kd, ki, T, f):
    """|term| per unit |E| at f -- EXACT discrete forms, not the s-domain approximation."""
    w = 2 * math.pi * f * T
    magP = kp / 256.0
    magD = (kd / 8.0) * abs(2 * math.sin(w / 2))        # |1 - e^-jw| = 2 sin(w/2)
    magI = (ki / 8.0) / 32.0 / 128.0 / abs(2 * math.sin(w / 2))
    return magP, magD, magI


def d_over_p_hz(kp, kd, T):
    """f where |D| == |P|:  (kd/8)*2*sin(pi f T) == kp/256."""
    r = (kp / 256.0) / (kd / 8.0) / 2.0
    return float("nan") if r > 1 else math.asin(r) / (math.pi * T)


def i_over_p_hz(kp, ki, T):
    r = (ki / 8.0) / 32.0 / 128.0 / (kp / 256.0) / 2.0
    return math.asin(r) / (math.pi * T)


# ---------------------------------------------------------------------------------------------------
# SECTION 3 -- the filters around the PID, exact discrete transfer functions
# ---------------------------------------------------------------------------------------------------
def _z(f, T):
    return complex(math.cos(-2 * math.pi * f * T), math.sin(-2 * math.pi * f * T))


def H_fb(f, T):
    """feedback: y[n] = (923 y[n-1] + 1560 x[n])>>10 ; fb = y[n] + y[n-1]   (0x28F8E..0x28FA4)"""
    z = _z(f, T)
    return (1 + z) * (FB_B / 1024.0) / (1 - (FB_A / 1024.0) * z)


def H_lag(f, T):
    """output lag: s[n] = (992 s[n-1] + 507 u[n])>>10 ; out = (s[n-1]+s[n])>>5  (0x2A180..0x2A1AC)"""
    z = _z(f, T)
    return (1 + z) * (LAG_B / 1024.0) / (1 - (LAG_A / 1024.0) * z) / 32.0


def H_pid(f, T, kp, kd, ki):
    z = _z(f, T)
    Hp = kp / 256.0
    Hd = (kd / 8.0) * (1 - z)
    Hi = ((ki / 8.0) / 32.0 / 128.0) / (1 - z) if ki else 0.0
    return Hp + Hd + Hi


def deg(c):
    return math.degrees(math.atan2(c.imag, c.real))


# ---------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    FS = [0.5, 1.0, 2.0, 7.3, 13.0, 20.0, 40.0]
    print("=" * 104)
    print("CALS READ FROM THE V283 IMAGE")
    print("=" * 104)
    print("  Ki 0xC63E6=%d   AWL 0xC61BA=%d (lim=%d)   I-deadband 0xC62E4=%d"
          % (KI, AWL, (AWL << 10) >> 3, I_DB))
    print("  clamps: P 0xC61BC=%d  D 0xC61B6=%d  SUM 0xC61BE=%d  OUT 0xC61B4=%d"
          % (P_CLAMP, D_CLAMP, SUM_CLAMP, OUT_CLAMP))
    print("  fwd gain 0xC6CD0=%d   out-lag 0xC63EC=%d / 0xC63EE=%d   fb EMA 0xC63E8=%d / 0xC63EA=%d"
          % (FWD_GAIN, LAG_A, LAG_B, FB_A, FB_B))
    print("  Kp rec 0x%05X n=%d X=%s Y=%s" % (KP_REC, KP_N, KP_X, KP_Y))
    print("  Kd rec 0x%05X n=%d X=%s Y=%s" % (KD_REC, KD_N, KD_X, KD_Y))

    for T, label in ((1e-3, "T = 1 ms  (1 kHz -- the PINNED rate)"),
                     (1e-2, "T = 10 ms (100 Hz -- the alternative, for comparison only)")):
        print("")
        print("=" * 104)
        print(label)
        print("=" * 104)
        Kp_r, Kd_r, Ki_r = term_gains(248, 128, 50, T)
        print("  continuous-equivalent gains, Kp=248 Kd=128 Ki=50:")
        print("    Kp_r = %.6f            (rate-frame proportional)" % Kp_r)
        print("    Kd_r = %.6f s          (rate-frame derivative)" % Kd_r)
        print("    Ki_r = %.6f /s         (rate-frame integral)" % Ki_r)
        print("    Kp_r/Kd_r = %8.3f rad/s = %7.3f Hz   <-- D overtakes P here"
              % (Kp_r / Kd_r, Kp_r / Kd_r / 2 / math.pi))
        print("    Ki_r/Kp_r = %8.3f rad/s = %7.3f Hz   <-- I overtakes P here"
              % (Ki_r / Kp_r, Ki_r / Kp_r / 2 / math.pi))
        print("")
        print("  |D|/|P| per unit E  (exact discrete)")
        print("    %-30s" % "f (Hz) ->" + "".join("%9.1f" % f for f in FS))
        for kp, tag in ((248, "Kp=248 flat (V281r3/V282/V283)"), (341, "Kp=341 (V281 rev2, unflown)"),
                        (512, "Kp=512 (M8* peak, idx 36-44)"), (696, "Kp=696 (stock LERP top)")):
            row = "".join("%9.3f" % (term_mag(kp, 128, 50, T, f)[1] / term_mag(kp, 128, 50, T, f)[0]) for f in FS)
            print("    %-30s" % tag + row)
        print("")
        print("  D-overtakes-P frequency vs Kp (Kd=128):")
        for kp in (248, 341, 512, 645, 696):
            print("    Kp=%3d -> %7.2f Hz" % (kp, d_over_p_hz(kp, 128, T)))
        print("  I-overtakes-P frequency (Kp=248, Ki=50): %.4f Hz" % i_over_p_hz(248, 50, T))

    # ------------------------------------------------------------------------------------------
    T = 1e-3
    print("")
    print("=" * 104)
    print("TERM MAGNITUDES per unit |E|, T = 1 ms, Kp=248 Kd=128 Ki=50")
    print("=" * 104)
    print("  %-7s %10s %10s %10s %10s %10s" % ("f (Hz)", "|P|/|E|", "|D|/|E|", "|I|/|E|", "D/P", "I/P"))
    for f in FS:
        mp, md, mi = term_mag(248, 128, 50, T, f)
        print("  %-7.2f %10.4f %10.4f %10.5f %10.3f %10.5f" % (f, mp, md, mi, md / mp, mi / mp))

    print("")
    print("=" * 104)
    print("THE THREE FRAMES  (T = 1 ms, Kp=248, Kd=128, Ki=50)")
    print("=" * 104)
    Kp_r, Kd_r, Ki_r = term_gains(248, 128, 50, T)
    print("  RATE frame (as built):  S = Ki_r*INT(E) + Kp_r*E + Kd_r*dE/dt")
    print("     I -> integral       %.6f /s" % Ki_r)
    print("     P -> proportional   %.6f" % Kp_r)
    print("     D -> derivative     %.6f s" % Kd_r)
    print("  ANGLE frame (E = d/dt of the angle error):  S = Kp_th*e + Kd_th*de/dt + Kdd_th*d2e/dt2")
    print("     I -> PROPORTIONAL on angle     Kp_th  = %.6f" % Ki_r)
    print("     P -> DERIVATIVE   on angle     Kd_th  = %.6f s" % Kp_r)
    print("     D -> 2nd DERIVATIVE on angle   Kdd_th = %.6f s^2" % Kd_r)
    print("     Kd_th/Kp_th = %.4f s -> D-on-angle overtakes P-on-angle at %.4f Hz"
          % (Kp_r / Ki_r, Ki_r / Kp_r / 2 / math.pi))
    print("  ACCELERATION frame (E = INT of the acceleration error): S = Ki2*INT2(a) + Ki_a*INT(a) + Kp_a*a")
    print("     I -> DOUBLE INTEGRAL on accel  %.6f /s" % Ki_r)
    print("     P -> INTEGRAL       on accel   Ki_a = %.6f" % Kp_r)
    print("     D -> PROPORTIONAL   on accel   Kp_a = %.6f s" % Kd_r)
    print("     *** THERE IS NO DERIVATIVE TERM IN THE ACCELERATION FRAME: Kd_a = 0 ***")
    print("     Ki_a/Kp_a = %.3f rad/s = %.3f Hz  <- the PI corner in the operator's frame"
          % (Kp_r / Kd_r, Kp_r / Kd_r / 2 / math.pi))
    print("")
    print("  how derivative-heavy the loop is ON ANGLE, per frequency:")
    for f in FS:
        mp, md, mi = term_mag(248, 128, 50, T, f)
        print("     %5.1f Hz : D_angle/P_angle = %9.2f x     DD_angle/D_angle = %7.3f x" % (f, mp / mi, md / mp))

    print("")
    print("=" * 104)
    print("CROSS-CHECK against the MEASURED term magnitudes, V283 r36-r38 strong-turn frames")
    print("   (STUTTER-7HZ-V283-r36-r38-2026-09-03.md: |P| p50 ~1900, |D| 880-1552, |I| 3377-7004)")
    print("=" * 104)
    Pmeas, Dlo, Dhi, Ilo, Ihi = 1900.0, 880.0, 1552.0, 3377.0, 7004.0
    Emag = Pmeas / (248 / 256.0)
    print("  |P| = (Kp/256)|E|  =>  |E| = %.0f counts" % Emag)
    for T2, tag in ((1e-3, "1 kHz "), (1e-2, "100 Hz")):
        Dpred = term_mag(248, 128, 50, T2, 7.3)[1] * Emag
        note = "  <-- D CLAMP is %d, so D would be RAILED, not 880-1552" % D_CLAMP if Dpred > D_CLAMP else ""
        print("  at %s a 7.3 Hz E of that amplitude predicts |D| = %8.0f counts%s" % (tag, Dpred, note))
    lo = math.asin((Dlo / Pmeas) * (248 / 256.0) / 16.0 / 2) / (math.pi * 1e-3)
    hi = math.asin((Dhi / Pmeas) * (248 / 256.0) / 16.0 / 2) / (math.pi * 1e-3)
    print("  inverting the MEASURED |D|/|P| = %.2f-%.2f at T=1 ms gives f = %.2f-%.2f Hz"
          % (Dlo / Pmeas, Dhi / Pmeas, lo, hi))
    Ipred = term_mag(248, 128, 50, 1e-3, 7.3)[2] * Emag
    print("  the AC part of I at 7.3 Hz would be only %.0f counts -- measured %.0f-%.0f, i.e. %.0f-%.0f x larger"
          % (Ipred, Ilo, Ihi, Ilo / Ipred, Ihi / Ipred))
    dbE = Emag / 32.0 - I_DB
    inc = (dbE * KI) / 8.0
    print("  a SUSTAINED one-sided error of that size ramps the accumulator at %.1f / tick;" % inc)
    print("    reaching |I| = %.0f (iacc = %.0f) takes %.0f ticks = %.2f s at 1 kHz"
          % (Ihi, Ihi * 128, Ihi * 128 / inc, Ihi * 128 / inc * 1e-3))
    print("  anti-windup ceiling on the I TERM = lim>>7 = %d counts" % (((AWL << 10) >> 3) >> 7))

    print("")
    print("=" * 104)
    print("CONTROLLER SHAPE  |Kp/256 + (Kd/8)(1-z^-1) + Ki'/(1-z^-1)|  and its phase, T = 1 ms")
    print("=" * 104)
    print("  %-7s %24s %24s %24s" % ("f (Hz)", "Kp248 Kd128 Ki50", "Kp512 Kd128 Ki50 (M8*)", "Kp248 Kd64 Ki50"))
    for f in FS:
        a, b, c = H_pid(f, T, 248, 128, 50), H_pid(f, T, 512, 128, 50), H_pid(f, T, 248, 64, 50)
        print("  %-7.2f %13.4f %+8.1f deg %13.4f %+8.1f deg %13.4f %+8.1f deg"
              % (f, abs(a), deg(a), abs(b), deg(b), abs(c), deg(c)))
    print("")
    print("  the filters around it (magnitude / phase):")
    print("  %-7s %22s %22s" % ("f (Hz)", "feedback EMA + sum", "output lag 992/507"))
    for f in FS:
        hf, hl = H_fb(f, T), H_lag(f, T)
        print("  %-7.2f %12.4f %+8.1f deg %12.4f %+8.1f deg" % (f, abs(hf), deg(hf), abs(hl), deg(hl)))
    print("  feedback DC gain = %.3f ; output-lag DC gain = %.4f" % (abs(H_fb(1e-9, T)), abs(H_lag(1e-9, T))))

    print("")
    print("=" * 104)
    print("M8*  vs  flat 248  --  the D-overtakes-P corner as a function of demand index")
    print("=" * 104)
    M8_X, M8_Y = (0, 32, 36, 44, 88), (248, 248, 512, 512, 248)
    STK_X, STK_Y = (0, 68, 112, 136, 208), (248, 512, 645, 696, 696)
    print("  %-6s %9s %11s %9s %11s %9s %11s"
          % ("idx", "Kp flat", "corner Hz", "Kp M8*", "corner Hz", "Kp stock", "corner Hz"))
    for idx in (0, 16, 32, 34, 36, 40, 44, 56, 68, 88, 120, 208):
        kf = lerp_int(KP_X, KP_Y, idx)
        km = lerp_int(M8_X, M8_Y, idx)
        ks = lerp_int(STK_X, STK_Y, idx)
        print("  %-6d %9d %11.2f %9d %11.2f %9d %11.2f"
              % (idx, kf, d_over_p_hz(kf, 128, T), km, d_over_p_hz(km, 128, T), ks, d_over_p_hz(ks, 128, T)))

    print("")
    print("=" * 104)
    print("MOVING Kd INSTEAD  (Kp = 248 flat, Ki = 50)")
    print("=" * 104)
    print("  %-6s %11s %13s %13s %13s %13s"
          % ("Kd", "corner Hz", "|C| @7.3Hz", "ph @7.3Hz", "|C| @20Hz", "ph @20Hz"))
    for kd in (0, 32, 64, 128, 192, 256, 384):
        c73, c20 = H_pid(7.3, T, 248, kd, 50), H_pid(20.0, T, 248, kd, 50)
        corner = d_over_p_hz(248, kd, T) if kd else float("nan")
        print("  %-6d %11.2f %13.4f %+12.1f %13.4f %+12.1f"
              % (kd, corner, abs(c73), deg(c73), abs(c20), deg(c20)))

    # a live integer run of the mirror, to prove it executes and matches the algebra
    print("")
    print("=" * 104)
    print("MIRROR SELF-RUN: 2 s of a 7.3 Hz feedback ripple, |fb| = 1961, sp = 0, idx = 60")
    print("=" * 104)
    pid = RatePID()
    peakP = peakD = peakI = 0
    for n in range(2000):
        fb = int(1961 * math.sin(2 * math.pi * 7.3 * n * 1e-3))
        r = pid.tick(sp=0, fb=fb, idx=60)
        if n > 200:
            peakP = max(peakP, abs(r["P"]))
            peakD = max(peakD, abs(r["D"]))
            peakI = max(peakI, abs(r["I"]))
    pred = term_mag(248, 128, 50, T, 7.3)[1] / term_mag(248, 128, 50, T, 7.3)[0]
    print("  peak |P| = %d   peak |D| = %d   peak |I| = %d   (D/P = %.3f, predicted %.3f)"
          % (peakP, peakD, peakI, peakD / float(peakP), pred))

    # ------------------------------------------------------------------------------------------
    print("")
    print("=" * 104)
    print("FORWARD PATH = controller x output-lag  (the torque actually delivered per unit E)")
    print("   the output lag pole a=992/1024 sits at -ln(a)/T = %.2f rad/s = %.2f Hz"
          % (-math.log(LAG_A / 1024.0) / T, -math.log(LAG_A / 1024.0) / T / 2 / math.pi))
    print("=" * 104)
    FS2 = [0.25, 0.5, 1.0, 2.0, 5.0, 7.3, 10.0, 13.0, 20.0, 30.0, 40.0]
    print("  %-7s %20s %20s %20s %20s" % ("f (Hz)", "Kd=0", "Kd=64", "Kd=128 (live)", "Kd=256"))
    for f in FS2:
        row = ""
        for kd in (0, 64, 128, 256):
            h = H_pid(f, T, 248, kd, 50) * H_lag(f, T)
            row += "%11.4f %+7.1f " % (abs(h), deg(h))
        print("  %-7.2f %s" % (f, row))
    print("")
    print("  peak of |forward path| and where it falls to half, per Kd:")
    for kd in (0, 64, 128, 192, 256):
        xs = [0.05 * k for k in range(1, 1200)]
        mags = [abs(H_pid(f, T, 248, kd, 50) * H_lag(f, T)) for f in xs]
        pk = max(range(len(xs)), key=lambda i: mags[i])
        f_half = next((xs[i] for i in range(pk, len(xs)) if mags[i] < 0.5 * mags[pk]), float("nan"))
        print("    Kd=%3d : peak |F| = %.4f at %5.2f Hz ; falls below half by %6.2f Hz"
              % (kd, mags[pk], xs[pk], f_half))
    print("")
    print("  ELECTRONICS loop shape (controller x lag x feedback, normalised to its DC value):")
    print("  %-7s %14s %14s %14s" % ("f (Hz)", "Kd=0", "Kd=128 (live)", "Kd=128 Kp=512"))
    dc0 = abs(H_pid(1e-6, T, 248, 0, 0) * H_lag(1e-6, T) * H_fb(1e-6, T))
    dc1 = abs(H_pid(1e-6, T, 248, 128, 0) * H_lag(1e-6, T) * H_fb(1e-6, T))
    dc2 = abs(H_pid(1e-6, T, 512, 128, 0) * H_lag(1e-6, T) * H_fb(1e-6, T))
    for f in FS2:
        a = abs(H_pid(f, T, 248, 0, 0) * H_lag(f, T) * H_fb(f, T)) / dc0
        b = abs(H_pid(f, T, 248, 128, 0) * H_lag(f, T) * H_fb(f, T)) / dc1
        c = abs(H_pid(f, T, 512, 128, 0) * H_lag(f, T) * H_fb(f, T)) / dc2
        print("  %-7.2f %14.4f %14.4f %14.4f" % (f, a, b, c))
