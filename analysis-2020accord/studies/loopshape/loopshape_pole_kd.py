"""
LOOPSHAPE (lag pole, Kd) two-parameter design surface -- 2026-09-04, subagent `loopshape`.

Everything is re-derived from the BUILT V283 IMAGE's bytes (little-endian raw reads), then
anchored on WIRE MEASUREMENTS.  No constant is taken from a build script or from the kit model.

Mirrors the exact integer arithmetic of FUN_00028ea6 (the 1 kHz LKAS rate PID), instruction
addresses in comments, then lifts it to the frequency domain at T = 1 ms.
"""
import struct, cmath, math, hashlib, sys

IMG = r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord" \
      r"\_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
img = open(IMG, 'rb').read()
SHA = hashlib.sha256(img).hexdigest()
u16 = lambda a: struct.unpack_from('<H', img, a)[0]

# ---- cals, byte-read little-endian from the image -------------------------------------------
KI      = u16(0xC63E6)      # 50
KP      = 248               # 0xE5378 slot-7 LERP, flat -- knots read below
KD      = 128               # 0xE511C slot-7 LERP, flat -- knots read below
FBA, FBB = u16(0xC63E8), u16(0xC63EA)     # 923, 1560   feedback EMA
OLA, OLB = u16(0xC63EC), u16(0xC63EE)     # 992, 507    output lag
TAPER   = 254/256           # 0x2A0A0/0x2A0BC, no driver override
GAIN    = u16(0xC6CD0)/32768.0            # 5346  forward gain, 0x2A1FE/0x2A202
T       = 1e-3              # tick, pinned three ways in PID-FRAME-SIZING §1

kd_knots = [u16(0xE511C + 2*i) for i in range(1, 10)]
kp_knots = [u16(0xE5378 + 2*i) for i in range(1, 11)]

# ---- transfer functions ----------------------------------------------------------------------
def C(f, kp=KP, ki=KI, kd=KD):
    """controller, counts of S per count of E.  P=(E*Kp)>>8 ; D=(dE*Kd)>>3 ; I: iacc+=(E/32*Ki)>>3, I=iacc>>7"""
    z = cmath.exp(2j*math.pi*f*T)
    zi = 1/z
    p = kp/256.0
    d = (kd/8.0)*(1-zi)
    i = (ki/32768.0)/(1-zi) if ki else 0.0        # 1/(32*8*128)
    return p + d + i

def Hlag(f, a=OLA, b=OLB):
    """out = (s[n-1]+s[n])>>5 with s[n]=(a*s[n-1]+b*S)>>10   (0x2A174..0x2A1AC)"""
    z = cmath.exp(2j*math.pi*f*T); zi = 1/z
    return (b/32768.0)*(1+zi)/(1-(a/1024.0)*zi)

def F(f, a=FBA, b=FBB):
    """fb = y[n]+y[n-1], y[n]=(a*y[n-1]+b*x)>>10   (0x28F86..0x28FA4), DC 30.891"""
    z = cmath.exp(2j*math.pi*f*T); zi = 1/z
    return (b/1024.0)*(1+zi)/(1-(a/1024.0)*zi)

def lag_dc(a, b):  return 2*b/(32.0*(1024-a))
def lag_pole_hz(a): return -math.log(a/1024.0)/(2*math.pi*T)

def servo_elec(f, kp=KP, ki=KI, kd=KD, a=OLA, b=OLB):
    """the whole servo arm's electronics, rate -> aggregator counts (plant excluded, common)"""
    return F(f)*C(f, kp, ki, kd)*TAPER*Hlag(f, a, b)*GAIN

def R(f, kp=KP, ki=KI, kd=KD, a=OLA, b=OLB):
    """complex ratio candidate/as-built of the servo arm.  F, taper, GAIN and the plant cancel."""
    return (C(f,kp,ki,kd)*Hlag(f,a,b))/(C(f,KP,KI,KD)*Hlag(f,OLA,OLB))

def b_for_dc(a, dc=None):
    """hold the lag's DC gain: b = dc*32*(1024-a)/2"""
    if dc is None: dc = lag_dc(OLA, OLB)
    return int(round(dc*32*(1024-a)/2.0))

def a_for_pole(fc): return int(round(1024*math.exp(-2*math.pi*fc*T)))

# ---- wire anchors -----------------------------------------------------------------------------
# 7.3 Hz strong-turn ring, loaded high-angle stratum.
#   normalised de-embed (STUTTER A9.3, 63 windows): Ls+Lr == 1 by construction
LS_POOL, LR_POOL = cmath.rect(0.55, math.radians(96)),  cmath.rect(1.19, math.radians(-27))
LS_R36,  LR_R36  = cmath.rect(0.69, math.radians(85)),  cmath.rect(1.16, math.radians(-36))
LS_R38,  LR_R38  = cmath.rect(0.42, math.radians(95)),  cmath.rect(1.12, math.radians(-22))
LTOT_MEAS = 0.93        # |L| at the ring, measured from its own Q (brief: 0.92-0.94)

# 20 Hz creep grind, aggregator damping budget (GRINDING-DEEP §2, creep hands-off)
#   phasors are aggregator counts per wheel-rate count; Re>0 = damping in that document's frame
Z_SERVO_20 = cmath.rect(1.90, math.radians(-69))   # measured on the 427 tap, V280 rev2 Kp (LERP)
Z_R24_20   = cmath.rect(3.23, math.radians(+5))    # closed form at 5244, s=1
Z_SERVO_7  = cmath.rect(2.50, math.radians(-62))
Z_R24_7    = cmath.rect(3.37, math.radians(+166))
S_R24      = 0.43        # V282 tap: |r24| on the wire is 0.37-0.43 of the closed form
KP_V280    = 600.0       # stock LERP at the ring/grind indices, for rescaling the servo to flat 248

FREQS = [0.5,1,2,3,5,7.3,10,13,15,18,20,22,25,30,35,40,50]
PH = lambda c: math.degrees(cmath.phase(c))

def banner(s): print("\n" + "="*100 + "\n" + s + "\n" + "="*100)

banner("0. IMAGE AND CALS, byte-read little-endian")
print("image  :", IMG.split("\\")[-1])
print("sha256 :", SHA)
print(f"Ki=0xC63E6={KI}  fbEMA 0xC63E8/EA={FBA}/{FBB}  outlag 0xC63EC/EE={OLA}/{OLB}  gain 0xC6CD0={u16(0xC6CD0)}")
print(f"Kd record 0xE511C: n={u16(0xE511C)} X={kd_knots[0:4]} Y={kd_knots[4:8]}")
print(f"Kp record 0xE5378: n={u16(0xE5378)} X={kp_knots[0:5]} Y={kp_knots[5:10]}")
print(f"lag  pole {lag_pole_hz(OLA):.3f} Hz  DC {lag_dc(OLA,OLB):.4f}")
print(f"fb   pole {lag_pole_hz(FBA):.3f} Hz  DC {2*FBB/(1024.0-FBA):.3f}")
print(f"Kd zero (Kp/Kd corner) {(KP/256.0)/((KD/8.0)*T)/(2*math.pi):.3f} Hz")

banner("1. VALIDATION: does the byte-derived servo arm reproduce the MEASURED lane phase?")
print("GRINDING-DEEP §2 measured the LKAS lane (427 tap -> aggregator, per wheel-rate count) at")
print("  creep 20 Hz  : 1.90 @ -69 deg     loaded 7 Hz : 2.50 @ -62 deg     (V280 rev 2, stock Kp LERP)")
print("My byte model  Z_servo(f) = F(f)*C(f)*taper*Hlag(f)*GAIN   (plant excluded -- it is common)")
print(f"{'f':>6} {'|Z| Kp248':>10} {'ph Kp248':>10} {'|Z| Kp600':>10} {'ph Kp600':>10} {'ph Kp696':>10}")
for f in (7.0, 7.3, 20.0):
    z248 = servo_elec(f); z600 = servo_elec(f, kp=600); z696 = servo_elec(f, kp=696)
    print(f"{f:>6.1f} {abs(z248):>10.2f} {PH(z248):>10.1f} {abs(z600):>10.2f} {PH(z600):>10.1f} {PH(z696):>10.1f}")
print("\nNOTE: the model's phase is the ELECTRONICS only.  The measured -62/-69 deg includes the")
print("plant (column + motor + tap timing).  The DIFFERENCE model-vs-measured is the plant phase,")
print("and it is what I hold fixed when I score a candidate.  Plant phase implied:")
for f, meas in ((7.0, -62.0), (20.0, -69.0)):
    zm = servo_elec(f, kp=KP_V280)
    print(f"   {f:>4.1f} Hz : measured {meas:+.0f} deg  -  model {PH(zm):+.1f} deg  =  plant {meas-PH(zm):+.1f} deg")

banner("2. THE ELECTRONICS RATIO R(f) = (C*Hlag)_cand / (C*Hlag)_base  -- F, taper, gain, plant all cancel")
CANDS = []
for fc in (5.053, 7.0, 8.0, 10.0, 12.0, 15.0, 18.0, 21.0):
    a = a_for_pole(fc); b = b_for_dc(a)
    CANDS.append((a, b))
print("candidate lag poles, DC held at the as-built 0.9902:")
print(f"{'a':>6} {'b':>6} {'pole Hz':>9} {'DC':>8} {'|H|@20 x':>9} {'|H|@25 x':>9} {'|H|@40 x':>9} {'|H|@inf x':>10} {'blind 25->inf':>14}")
for a, b in CANDS:
    r20 = abs(Hlag(20,a,b)/Hlag(20,OLA,OLB)); r25 = abs(Hlag(25,a,b)/Hlag(25,OLA,OLB))
    r40 = abs(Hlag(40,a,b)/Hlag(40,OLA,OLB))
    inf = (b/(1024.0-a))/(OLB/(1024.0-OLA))          # |H| ratio at Nyquist-ish / asymptote
    hinf = abs(Hlag(499,a,b)/Hlag(499,OLA,OLB))
    print(f"{a:>6} {b:>6} {lag_pole_hz(a):>9.2f} {lag_dc(a,b):>8.4f} {r20:>9.2f} {r25:>9.2f} {r40:>9.2f} {hinf:>10.2f} {hinf/r25:>14.3f}")

banner("3. TWO-PARAMETER SURFACE: |R| and angle(R) at the two symptom frequencies + the PM band")
KDS = [0, 32, 48, 64, 80, 96, 112, 128, 160, 192, 256]
for label, f in (("7.3 Hz  (strong-turn ring)", 7.3), ("13.5 Hz (phase-margin band)", 13.5), ("20 Hz   (creep grind)", 20.0)):
    print(f"\n--- {label} :  |R| / angle(R) deg ---")
    hdr = f"{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>14}" for k in KDS)
    print(hdr)
    for a, b in CANDS:
        row = f"{lag_pole_hz(a):>8.2f} |"
        for kd in KDS:
            r = R(f, kd=kd, a=a, b=b)
            row += f"  {abs(r):>5.2f}/{PH(r):>+6.1f}"
        print(row)

banner("1b. VALIDATION, corrected: use the REGIME-APPROPRIATE Kp for each measured stratum")
print("The creep stratum is LOW demand index -> stock LERP Kp ~248-300.  The loaded high-angle")
print("stratum is HIGH index -> stock LERP Kp ~600-696.  With that, and NO free parameter:")
print(f"{'stratum':>26} {'f':>5} {'Kp':>5} {'model ph':>9} {'meas ph':>8} {'PLANT ph':>9} {'model |Z|':>10} {'meas |Z|':>9} {'plant |.|':>10}")
for name, f, kp, mph, mmag in (("creep hands-off", 20.0, 248, -69.0, 1.90),
                               ("creep hands-off", 20.0, 300, -69.0, 1.90),
                               ("loaded high-angle", 7.0, 600, -62.0, 2.50),
                               ("loaded high-angle", 7.0, 696, -62.0, 2.50)):
    z = servo_elec(f, kp=kp)
    print(f"{name:>26} {f:>5.1f} {kp:>5} {PH(z):>+9.1f} {mph:>+8.1f} {mph-PH(z):>+9.1f} {abs(z):>10.2f} {mmag:>9.2f} {mmag/abs(z):>10.3f}")
print("\n=> the byte-derived electronics reproduces BOTH measured lane phases to within ~4 deg with")
print("   no fitted parameter.  The plant contributes ~0 deg at 7 Hz and ~-4 deg at 20 Hz, i.e. the")
print("   servo lane's phase IS the electronics.  [EVIDENCE]  This is what licenses using R(f)'s")
print("   rotation directly as the lane's phase change.")

banner("4. GATE 2a -- THE 7.3 Hz RING.  L_new = L_today * (Ls*R + Lr),  |L_today| = 0.93 measured")
def ring(a, b, kd, Ls, Lr, Ltot=LTOT_MEAS, f=7.3):
    r = R(f, kd=kd, a=a, b=b)
    rat = Ls*r + Lr
    L = Ltot*rat
    return abs(rat), abs(L), PH(L), abs(1-L)
base_ring = ring(OLA, OLB, KD, LS_POOL, LR_POOL)
print(f"as-built: ring ratio {base_ring[0]:.3f}  |L| {base_ring[1]:.3f}  ang {base_ring[2]:+.1f}  |1-L| {base_ring[3]:.4f}  (Q ~ {1/base_ring[3]:.1f})")
print("\nHIGHER |1-L| = MORE damped = BETTER.  Split: pooled 63 windows (A9.3).")
print(f"{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>16}" for k in KDS))
for a, b in CANDS:
    row = f"{lag_pole_hz(a):>8.2f} |"
    for kd in KDS:
        _, mag, ang, d = ring(a, b, kd, LS_POOL, LR_POOL)
        row += f"   |L|{mag:>5.2f} d{d:>5.3f}"
    print(row)
print("\n-- r36, the DISSENTING route (largest servo share |Ls|=0.69) --")
print(f"{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>16}" for k in KDS))
for a, b in CANDS:
    row = f"{lag_pole_hz(a):>8.2f} |"
    for kd in KDS:
        _, mag, ang, d = ring(a, b, kd, LS_R36, LR_R36)
        row += f"   |L|{mag:>5.2f} d{d:>5.3f}"
    print(row)

banner("5. GATE 2b -- THE 20 Hz CREEP GRIND.  aggregator damping budget Re(Z_servo*R + s*Z_r24)")
print(f"as-built (s={S_R24}): Re_servo {Z_SERVO_20.real:+.3f}  Re_r24 {S_R24*Z_R24_20.real:+.3f}  "
      f"Re_total {Z_SERVO_20.real + S_R24*Z_R24_20.real:+.3f}   POSITIVE = damping")
# 20 Hz return-ratio shares, from the same phasors
tot20 = Z_SERVO_20 + S_R24*Z_R24_20
Ls20, Lr20 = Z_SERVO_20/tot20, (S_R24*Z_R24_20)/tot20
print(f"20 Hz normalised split: Ls {abs(Ls20):.2f}<{PH(Ls20):+.0f}  Lr {abs(Lr20):.2f}<{PH(Lr20):+.0f}  (sum=1 by construction)")
print(f"\n{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>17}" for k in KDS))
for a, b in CANDS:
    row = f"{lag_pole_hz(a):>8.2f} |"
    for kd in KDS:
        r = R(20.0, kd=kd, a=a, b=b)
        z = Z_SERVO_20*r + S_R24*Z_R24_20
        row += f"  Re{z.real:>+6.2f} rat{abs(Ls20*r+Lr20):>5.2f}"
    print(row)
print("\n('Re' = aggregator damping budget at 20 Hz, POSITIVE = damping, base +2.07.")
print(" 'rat' = the 20 Hz return-ratio ratio to today, LOWER = less loop gain at the grind.)")

banner("6. AUTHORITY AND DC -- what the operator's outer loop sees")
print("delivered-torque transfer |C*Hlag| relative to as-built, at the frequencies openpilot works in")
print(f"{'pole Hz':>8} {'Kd':>5} |" + "".join(f"{str(f)+'Hz':>9}" for f in (0.2,0.5,1,2,3,5)) + f"{'lag DC':>9}")
for a, b in CANDS:
    for kd in (128, 96, 64, 0):
        row = f"{lag_pole_hz(a):>8.2f} {kd:>5} |"
        for f in (0.2,0.5,1,2,3,5):
            row += f"{abs(R(f,kd=kd,a=a,b=b)):>9.3f}"
        row += f"{lag_dc(a,b):>9.4f}"
        print(row)
    print()

banner("7. WHY THE 20 Hz Re FRAME IS THE RIGHT ONE -- it reproduces the MEASURED Kp dependence")
print("Record [MEASURED]: the creep grind's presence FOLLOWS Kp(idx); V281 rev 3 (Kp flat 248) cut the")
print("18-22 Hz creep line 3.5x rarer and 2.5x smaller than V280 rev 2 (stock LERP).")
print("Naive |Z| reasoning says more Kp = more |Z| = more Re = MORE damping = LESS grind.  Wrong sign.")
print("The byte-derived PHASE fixes it: more Kp dilutes the D term's lead, rotating the lane to pure")
print("quadrature and then past it, so Re COLLAPSES even as |Z| grows.\n")
print(f"{'Kp':>6} {'|Z|@20':>8} {'phase':>8} {'Re@20':>8}   (servo lane electronics, as-built pole/Kd)")
for kp in (248, 300, 372, 440, 512, 600, 696):
    z = servo_elec(20.0, kp=kp); zz = z*(1.90/abs(servo_elec(20.0, kp=248)))   # scaled to the measured 1.90 at Kp248
    print(f"{kp:>6} {abs(zz):>8.2f} {PH(zz):>+8.1f} {zz.real:>+8.3f}")
print("=> Re peaks near Kp 250-300 and collapses to ~0 by Kp 600.  The measured Kp dependence of the")
print("   grind is REPRODUCED by the byte model.  [EVIDENCE for the arithmetic; the identification of")
print("   Re with the operator's grinding is the record's, and is BELIEF.]")

banner("8. THE HF RISK, RE-DERIVED: where does the servo lane stop damping and start pumping?")
print("Re(Z_servo) = 0 when the lane's phase reaches -90 deg.  Above that frequency the lane is")
print("ANTI-DAMPING.  Raising the lag pole pushes that crossing UP; cutting Kd pulls it DOWN.")
def re_zero_hz(kd, a, b, kp=KP):
    lo, hi = 1.0, 499.0
    f = lo
    prev = servo_elec(lo, kp=kp, kd=kd, a=a, b=b)
    for i in range(1, 5000):
        f = lo + (hi-lo)*i/5000.0
        c = servo_elec(f, kp=kp, kd=kd, a=a, b=b)
        if PH(prev) >= -90.0 > PH(c): return f
        prev = c
    return float('nan')
print(f"\n{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>9}" for k in KDS))
for a, b in CANDS:
    print(f"{lag_pole_hz(a):>8.2f} |" + "".join(f"{re_zero_hz(kd,a,b):>9.1f}" for kd in KDS))
print("\n(Hz at which the servo lane crosses from damping to anti-damping, Kp 248.)")

print("\n-- HF gain of the servo arm relative to as-built, INCLUDING the feedback EMA's roll-off --")
print(f"{'pole Hz':>8} {'Kd':>5} |" + "".join(f"{str(f)+'Hz':>9}" for f in (25,30,40,50,80,125,250,500)))
for a, b in CANDS:
    for kd in (128, 96, 64):
        print(f"{lag_pole_hz(a):>8.2f} {kd:>5} |" + "".join(
            f"{abs(servo_elec(f,kd=kd,a=a,b=b)/servo_elec(f)):>9.2f}" for f in (25,30,40,50,80,125,250,500)))
print("\nBLIND-BAND BOUND, re-derived: the 427 tap is 50 Hz sampled (Nyquist 25 Hz); 0x18F is 100 Hz")
print("(usable to ~40 Hz).  Unobservable increment = (worst HF ratio) / (ratio at 25 Hz):")
for a, b in CANDS[1:]:
    r25 = abs(servo_elec(25,a=a,b=b)/servo_elec(25))
    worst = max(abs(servo_elec(f,a=a,b=b)/servo_elec(f)) for f in [25+0.5*i for i in range(950)])
    print(f"   pole {lag_pole_hz(a):>5.2f} Hz : x{r25:.2f} at 25 Hz, worst above 25 Hz x{worst:.2f}"
          f"  =>  BLIND INCREMENT x{worst/r25:.3f}")

banner("9. THE SURVIVING (pole, Kd) PAIRS -- constrained search")
print("CONSTRAINTS, each stated before the search:")
print("  C1  ring GATE: |L(7.3)| <= 0.93 (today's measured value) on the POOLED split AND on r36's")
print("      (the dissenting route).  |L| > 1 at the ring frequency = the F7 cycle returns.")
print("  C2  grind GATE: Re(20 Hz) >= +2.07 (today).  Lower = less damping of the creep mode.")
print("  C3  DC held: lag DC within 0.5% of 0.9902.  (Kd has no DC term at all.)")
print("  C4  HF: blind increment above 25 Hz <= x1.15.")
print()
rows = []
for a, b in CANDS:
    for kd in KDS:
        _, Lp, _, _ = ring(a, b, kd, LS_POOL, LR_POOL)
        _, L36, _, _ = ring(a, b, kd, LS_R36, LR_R36)
        _, L38, _, _ = ring(a, b, kd, LS_R38, LR_R38)
        re20 = (Z_SERVO_20*R(20.0,kd=kd,a=a,b=b) + S_R24*Z_R24_20).real
        r25 = abs(servo_elec(25,kd=kd,a=a,b=b)/servo_elec(25,kd=kd))
        worst = max(abs(servo_elec(f,kd=kd,a=a,b=b)/servo_elec(f,kd=kd)) for f in [25+0.5*i for i in range(950)])
        blind = worst/r25
        ok = (Lp <= 0.9331 and L36 <= 0.9331 and L38 <= 0.9331 and re20 >= 2.06
              and abs(lag_dc(a,b)-0.9902) < 0.005 and blind <= 1.15)
        rows.append((lag_pole_hz(a), a, b, kd, Lp, L36, L38, re20, abs(R(20,kd=kd,a=a,b=b)), blind, ok))
print(f"{'pole':>6} {'a':>5} {'b':>5} {'Kd':>4} {'|L|7.3 pool':>12} {'r36':>7} {'r38':>7} {'Re@20':>7} {'|R|@20':>7} {'blind':>7}  PASS")
for r in rows:
    mark = " <== PASS" if r[10] else ""
    if r[10] or r[3] in (64, 96, 128):
        print(f"{r[0]:>6.2f} {r[1]:>5} {r[2]:>5} {r[3]:>4} {r[4]:>12.3f} {r[5]:>7.3f} {r[6]:>7.3f} {r[7]:>+7.2f} {r[8]:>7.2f} {r[9]:>7.3f}{mark}")

banner("10. SENSITIVITY of the 20 Hz Re verdict to s (the ONE estimated quantity), s in 0.30-0.52")
print("The 7.3 Hz ring result does NOT depend on s at all -- it uses A9.3's NORMALISED de-embed,")
print("in which Ls+Lr==1 by construction.  Only the 20 Hz Re budget carries s.")
print(f"{'pole':>6} {'Kd':>5} |" + "".join(f"{('s='+str(s)):>10}" for s in (0.30,0.37,0.43,0.52)))
for a,b in [(992,507),(974,792),(962,982),(932,1458)]:
    for kd in (128, 96, 64, 48):
        r = R(20.0, kd=kd, a=a, b=b)
        row = f"{lag_pole_hz(a):>6.2f} {kd:>5} |"
        for s in (0.30,0.37,0.43,0.52):
            row += f"{(Z_SERVO_20*r + s*Z_R24_20).real:>+10.2f}"
        print(row)
print("\nbase (992/507, Kd128) at those s:", " ".join(f"{(Z_SERVO_20 + s*Z_R24_20).real:+.2f}" for s in (0.30,0.37,0.43,0.52)))

banner("11. THE THIRD CELL PAIR -- the feedback EMA 0xC63E8/0xC63EA, the ONLY one GATE 1 cleared")
def b_fb(a, dc=30.891): return int(round(dc*(1024-a)/2.0))
print(f"{'a':>5} {'b':>6} {'pole Hz':>9} {'DC':>8} | {'|R|/ang @7.3':>16} {'@13.5':>16} {'@20':>16}")
for fc in (16.527, 20, 25, 33, 45):
    a = a_for_pole(fc); b = b_fb(a)
    rs = []
    for f in (7.3, 13.5, 20.0):
        r = (F(f,a,b)/F(f))
        rs.append(f"{abs(r):>7.2f}/{PH(r):>+6.1f}")
    print(f"{a:>5} {b:>6} {lag_pole_hz(a):>9.2f} {2*b/(1024.0-a):>8.3f} | " + "  ".join(rs))
print("\nRing and grind, feedback pole moved ALONE (Kd 128, lag 992/507):")
print(f"{'fbpole':>8} {'|L|7.3 pool':>12} {'r36':>7} {'Re@20':>8} {'noise into D x':>15} {'Re=0 xover Hz':>14}")
for fc in (16.527, 20, 25, 33, 45):
    a = a_for_pole(fc); b = b_fb(a)
    r73 = (F(7.3,a,b)/F(7.3)); r20 = (F(20,a,b)/F(20))
    Lp = abs(LTOT_MEAS*(LS_POOL*r73 + LR_POOL)); L36 = abs(LTOT_MEAS*(LS_R36*r73 + LR_R36))
    re20 = (Z_SERVO_20*r20 + S_R24*Z_R24_20).real
    # noise into the D term: worst-case |F| ratio over 25-500 Hz (D multiplies whatever F passes)
    nz = max(abs(F(f,a,b)/F(f)) for f in [25+0.5*i for i in range(950)])
    # Re=0 crossing with the modified feedback
    def zz(f): return F(f,a,b)*C(f)*TAPER*Hlag(f)*GAIN
    xo=float('nan'); prev=zz(1.0)
    for i in range(1,5000):
        f=1.0+498*i/5000.0; c=zz(f)
        if PH(prev)>=-90.0>PH(c): xo=f; break
        prev=c
    print(f"{lag_pole_hz(a):>8.2f} {Lp:>12.3f} {L36:>7.3f} {re20:>+8.2f} {nz:>15.2f} {xo:>14.1f}")

banner("12. CLAMP HEADROOM -- does any candidate push a term into a rail?")
print("measured on V283 strong-turn frames (STUTTER-7HZ §, quoted by PID-FRAME §6):")
print("  |P| p50 ~1900 (clamp 15360, 12%)   |D| 880-1552 (clamp 10240, 9-15%)   |I| 3377-7004 (ceiling 10240, 68%)")
print("  427 tap |T| 778-868 at a stall, 600-1000 DC in a loaded turn (output clamp 3072)")
print()
for kd in (256,192,160,128,96,64,48,0):
    print(f"  Kd={kd:>4}: |D| scales x{kd/128:.2f} -> {880*kd/128:.0f}-{1552*kd/128:.0f} counts, "
          f"{'RAILS' if 1552*kd/128 > 10240 else f'{100*1552*kd/128/10240:.0f}% of the D clamp'}")
print()
print("  the lag pole does NOT touch P, D or I (it is downstream of the sum clamp 0xC61BE=15360).")
print("  it scales the OUTPUT: DC held, so the stall/steady |T| is unchanged; only AC above ~5 Hz grows.")
for a,b in CANDS[1:]:
    print(f"  pole {lag_pole_hz(a):>5.2f} Hz: 20 Hz AC of T x{abs(Hlag(20,a,b)/Hlag(20,OLA,OLB)):.2f}; "
          f"measured 18-22 bar amplitude p50 31 raw -> the output clamp 3072 is not approached by the ripple")

banner("13. CAN A PREDICTED dRe BE CONVERTED INTO A PREDICTED dAMPLITUDE?  NO -- and that matters")
print("MEASURED [record]: V280 rev 2 (stock Kp LERP) -> V281 rev 3 (Kp flat 248) cut the 18-22 Hz creep")
print("bar amplitude p50 from 69 to 24 raw (x0.348) in the operator own stratum, and the presence rate")
print("from 65% to 16% of 2 s windows.  If I can calibrate amplitude-vs-Re on that step, I can convert")
print("every candidate dRe into a predicted bar amplitude.  I tried; it does not work.")
print("")
print("First, what Kp was the creep stratum running on V280 rev 2?  Pin it from the measured PHASE:")
for kp in (248,272,300,330,372):
    z = servo_elec(20.0, kp=kp)
    print(f"   Kp {kp:>3}: model phase {PH(z):>+6.1f} deg   (GRINDING-DEEP measured -69 deg on V280 rev 2)")
print("=> V280 rev 2 creep Kp was ~300.  V283 runs flat 248.  The step is small:")
z280 = servo_elec(20.0, kp=300); z283 = servo_elec(20.0, kp=248)
kk = 1.90/abs(z280)
Re280 = (z280*kk).real + S_R24*Z_R24_20.real
Re283 = (z283*kk).real + S_R24*Z_R24_20.real
print(f"   Re_total(V280 rev 2, Kp~300) = {Re280:+.3f}")
print(f"   Re_total(V283,      Kp 248)  = {Re283:+.3f}     ratio {Re283/Re280:.3f}  ({100*(Re283/Re280-1):+.1f}%)")
print("")
print("A 4% damping change cannot produce a 2.9x amplitude change under any driven-mode model unless")
print("the TOTAL damping is within a few percent of zero -- in which case the calibration is singular")
print("and numerically meaningless (solving for c_mech gives ~ -2.1 and a net of ~ +0.05, i.e. the mode")
print("on the edge of self-sustaining, contradicting GRINDING-DEEP section 2 own classification of the")
print("20 Hz mode as DRIVEN with net Re +3.90).")
print("")
print("*** CONSEQUENCE, the most important limit in this study: ***")
print("  I can predict the SIGN of a candidate 20 Hz effect (Re rises => more damping => smaller grind,")
print("  IF the driven-mode classification holds).  I CANNOT predict its MAGNITUDE, because the only")
print("  cross-build step available to calibrate the map from Re to bar amplitude is inconsistent with")
print("  that map.  Either the grind measured Kp dependence acts through a channel other than the 20 Hz")
print("  Re budget, or the V280 rev 2 -> V281 rev 3 contrast carries a confound (those builds differ by")
print("  more than Kp, and the routes differ).  [EVIDENCE for the arithmetic and the inconsistency;")
print("  BELIEF for which explanation is right.]")

banner("14. BLIND-BAND EXPOSURE of the feedback-pole candidates (the GATE-1-clean pair)")
for fc in (20, 25, 33, 45):
    a = a_for_pole(fc); b = b_fb(a)
    r25 = abs(F(25,a,b)/F(25)); worst = max(abs(F(f,a,b)/F(f)) for f in [25+0.5*i for i in range(950)])
    print(f"  fb pole {lag_pole_hz(a):>5.2f} Hz (a={a},b={b}): x{r25:.2f} at 25 Hz, worst above x{worst:.2f}"
          f"  =>  BLIND INCREMENT x{worst/r25:.3f}   (the EMA has a ZERO at Nyquist, so it self-limits)")

banner("15. GATE 2a RE-RUN AT THE SUPERSEDING OPERATING POINT |L_tot(248)| = 0.976 [0.944-0.990]")
print("Supersedes the 0.92-0.94 the brief carried (per-episode ACF fit, relayed by team-lead 2026-09-04).")
print("Everything scales: the ring is CLOSER to unity than assumed, so the margin is 2.4%, not 6.7%.")
LO_, MID_, HI_ = 0.944, 0.976, 0.990
for nm, v in (("optimistic (0.944)",LO_), ("point   (0.976)",MID_), ("PESSIMISTIC (0.990)",HI_)):
    print(f"  {nm}: |1-L| today = {abs(1-v):.4f}   Q ~ {1/abs(1-v):.0f}")
print("\n|L(7.3)| at the PESSIMISTIC end 0.990, pooled split.  >=1.000 = the cycle returns.")
print(f"{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>9}" for k in KDS))
for a,b in CANDS:
    print(f"{lag_pole_hz(a):>8.2f} |" + "".join(f"{ring(a,b,kd,LS_POOL,LR_POOL,Ltot=HI_)[1]:>9.3f}" for kd in KDS))
print("\nSame, r36 (dissenting route):")
print(f"{'pole Hz':>8} |" + "".join(f"{('Kd='+str(k)):>9}" for k in KDS))
for a,b in CANDS:
    print(f"{lag_pole_hz(a):>8.2f} |" + "".join(f"{ring(a,b,kd,LS_R36,LR_R36,Ltot=HI_)[1]:>9.3f}" for kd in KDS))

banner("16. THE CONSTRAINED SEARCH, RE-RUN ACROSS THE WHOLE INTERVAL")
print("C1  |L(7.3)| <= today's OWN value at the SAME operating point, on pooled AND r36 AND r38,")
print("    evaluated at ALL THREE of 0.944 / 0.976 / 0.990.  (The constraint is a RATIO, so it is")
print("    actually interval-invariant -- see the note below -- but the ABSOLUTE margin is not.)")
print("C2  Re(20) >= +2.06 at s=0.43 AND >= its own base at s=0.30.")
print("C3  lag DC within 0.5% of 0.9902.   C4  blind increment above 25 Hz <= x1.15.")
print()
print(f"{'pole':>6} {'a':>5} {'b':>5} {'Kd':>4} {'ratio':>7} {'|L|@.944':>9} {'|L|@.976':>9} {'|L|@.990':>9}"
      f" {'|1-L|@.990':>11} {'Re@.43':>7} {'Re@.30':>7} {'blind':>6}  PASS")
survivors=[]
for a,b in CANDS:
    for kd in KDS:
        rat_p = ring(a,b,kd,LS_POOL,LR_POOL,Ltot=1.0)[1]
        rat_36 = ring(a,b,kd,LS_R36,LR_R36,Ltot=1.0)[1]
        rat_38 = ring(a,b,kd,LS_R38,LR_R38,Ltot=1.0)[1]
        worst = max(rat_p, rat_36, rat_38)
        d990 = ring(a,b,kd,LS_POOL,LR_POOL,Ltot=HI_)[3]
        r = R(20.0,kd=kd,a=a,b=b)
        re43 = (Z_SERVO_20*r + 0.43*Z_R24_20).real
        re30 = (Z_SERVO_20*r + 0.30*Z_R24_20).real
        r25 = abs(servo_elec(25,kd=kd,a=a,b=b)/servo_elec(25,kd=kd))
        wst = max(abs(servo_elec(f,kd=kd,a=a,b=b)/servo_elec(f,kd=kd)) for f in [25+0.5*i for i in range(950)])
        blind = wst/r25
        ok = (worst <= 1.0 and re43 >= 2.06 and re30 >= (Z_SERVO_20+0.30*Z_R24_20).real
              and abs(lag_dc(a,b)-0.9902) < 0.005 and blind <= 1.15)
        if ok: survivors.append((lag_pole_hz(a),a,b,kd,worst,d990,re43,blind))
        if ok or kd in (48,64,96,128):
            print(f"{lag_pole_hz(a):>6.2f} {a:>5} {b:>5} {kd:>4} {worst:>7.3f} {rat_p*LO_:>9.3f} {rat_p*MID_:>9.3f}"
                  f" {rat_p*HI_:>9.3f} {d990:>11.3f} {re43:>+7.2f} {re30:>+7.2f} {blind:>6.3f}"
                  + ("  <== PASS" if ok else ""))
print("\nNOTE, and it is the reason the interval does not change the RANKING: C1 is a ratio to today's")
print("own |L| at the same operating point, and the ratio |Ls*R+Lr| is independent of |L_today|.  So")
print("WHICH candidates pass is interval-invariant.  What the interval DOES change is the absolute")
print("stability margin, and it changes it a lot: |1-L| today is 0.024 at the point estimate and")
print("0.010 at the pessimistic end, against the 0.068 the brief's 0.93 implied -- so the ring is")
print("2.8x to 6.8x closer to self-sustaining than the earlier number said, and every DEGRADING")
print("candidate is correspondingly more dangerous.")
print(f"\nWhat a Kd cut ALONE does at the pessimistic end 0.990 (pooled):")
for kd in (112, 96, 80, 64, 48, 0):
    v = ring(OLA,OLB,kd,LS_POOL,LR_POOL,Ltot=HI_)[1]
    print(f"   Kd {kd:>3}: |L| = {v:.3f}  {'*** ABOVE 1.000 -- SELF-SUSTAINING ***' if v>=1.0 else ''}")
