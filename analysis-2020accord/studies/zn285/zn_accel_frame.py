"""ZN accel-frame analysis for a Kp=0 / Kd-swept LKAS rate PID (V285 question set).

Every firmware constant is a raw little-endian byte read of the BUILT V282 image.
Nothing is quoted from a build script.  T = 1 ms (pinned three ways, PID-FRAME-SIZING sec 1).
"""
import hashlib, os, struct, cmath, math
from pathlib import Path

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
        "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
IMG = ROOT / ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-"
              "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
b = IMG.read_bytes()
print(f"image  : {IMG.name}")
print(f"bytes  : {len(b)}")
print(f"sha256 : {hashlib.sha256(b).hexdigest()}")

u16 = lambda a: struct.unpack_from("<H", b, a)[0]
s16 = lambda a: struct.unpack_from("<h", b, a)[0]
u32 = lambda a: struct.unpack_from("<I", b, a)[0]

# ---- cal cells, byte-read -----------------------------------------------------------------
Ki      = u16(0xC63E6)          # integral gain
FB_A    = u16(0xC63E8)          # feedback EMA pole
FB_B    = u16(0xC63EA)          # feedback EMA zero-gain
LAG_A   = u16(0xC63EC)          # output-lag pole
LAG_B   = u16(0xC63EE)          # output-lag gain
CLP_D   = u16(0xC61B6)
CLP_P   = u16(0xC61BC)
CLP_SUM = u16(0xC61BE)
CLP_OUT = u16(0xC61B4)
AWU     = u16(0xC61BA)
GAIN    = u16(0xC6CD0)
def lerp_rec(a):
    n = u16(a)
    X = [u16(a+2+2*i) for i in range(n)]
    Y = [u16(a+2+2*n+2*i) for i in range(n)]
    return n, X, Y
KP_REC = lerp_rec(0xE5378)
KD_REC = lerp_rec(0xE511C)
Kp = KP_REC[2][0]
Kd = KD_REC[2][0]
print(f"\n-- cals byte-read from the V282 image --")
print(f"  0xC63E6 Ki        = {Ki}")
print(f"  0xC63E8/EA fb EMA = {FB_A}/{FB_B}")
print(f"  0xC63EC/EE outlag = {LAG_A}/{LAG_B}")
print(f"  0xC61B6 D clamp   = {CLP_D}   0xC61BC P clamp = {CLP_P}")
print(f"  0xC61BE sum clamp = {CLP_SUM} 0xC61B4 out clamp = {CLP_OUT}")
print(f"  0xC61BA anti-windup base = {AWU}   0xC6CD0 fwd gain = {GAIN}")
print(f"  0xE5378 Kp record = n={KP_REC[0]} X={KP_REC[1]} Y={KP_REC[2]}")
print(f"  0xE511C Kd record = n={KD_REC[0]} X={KD_REC[1]} Y={KD_REC[2]}")

T = 1e-3
def z(f): return cmath.exp(2j*math.pi*f*T)
def C(f, kp, kd, ki):
    zz = z(f)
    out = kp/256 + (kd/8)*(1 - 1/zz)
    if ki: out += (ki/32768)/(1 - 1/zz)
    return out
def Hlag(f, a=None, bb=None):
    a = LAG_A if a is None else a; bb = LAG_B if bb is None else bb
    zz = z(f); return (bb/32768)*(1 + 1/zz)/(1 - (a/1024)/zz)
def Fb(f, a=None, bb=None):
    a = FB_A if a is None else a; bb = FB_B if bb is None else bb
    zz = z(f); return (bb/1024)*(1 + 1/zz)/(1 - (a/1024)/zz)
def pole_hz(a): return -math.log(a/1024)/(2*math.pi*T)
print(f"\n  exact out-lag pole  = {pole_hz(LAG_A):.3f} Hz   DC = {2*LAG_B/(32*(1024-LAG_A)):.4f}")
print(f"  exact feedback pole = {pole_hz(FB_A):.3f} Hz   DC = {2*FB_B/(1024-FB_A):.3f}")
print(f"  Kd/Kp corner (D=P)  = {(Kp/256)/((Kd/8)*2*math.pi*T)/(2*math.pi):.3f} Hz "
      f"[exact: {[round(f,3) for f in [0]][0] if False else ''}]")
# exact corner: |D|=|P| -> 2*(Kd/8)*sin(pi f T) = Kp/256
fc = math.asin((Kp/256)/(2*(Kd/8)))/(math.pi*T)
print(f"  exact |D|=|P| at    = {fc:.3f} Hz")

# =============================================================================================
print("\n" + "="*94)
print("Q2  AUTHORITY LOSS FROM Kp -> 0   (V282: Ki=0, so C = P + D exactly)")
print("="*94)
print("  ratio = |C(Kp=0)| / |C(Kp=248)| ; the output lag, taper, fwd gain, feedback and the")
print("  PLANT are common to P and D and CANCEL exactly in this ratio.")
print(f"\n  {'f Hz':>7} {'|C| Kp248':>10} {'ph':>8} {'|C| Kp0':>9} {'ph':>8} {'ratio':>7} {'loss %':>8} {'d(phase)':>9}")
for f in [0.2,0.5,1,2,3,5,7.3,9.636,13.5,20,25,30,40,60,100]:
    c0 = C(f,Kp,Kd,0); c1 = C(f,0,Kd,0)
    r = abs(c1)/abs(c0)
    dph = math.degrees(cmath.phase(c1)-cmath.phase(c0))
    print(f"  {f:>7.3f} {abs(c0):>10.4f} {math.degrees(cmath.phase(c0)):>7.1f}d "
          f"{abs(c1):>9.4f} {math.degrees(cmath.phase(c1)):>7.1f}d {r:>7.4f} {100*(r-1):>7.1f}% {dph:>+8.1f}d")

# =============================================================================================
print("\n" + "="*94)
print("Q3  Ku / Tu  --  the marginal-stability search, on the MEASURED arm split at f0 = 7.3 Hz")
print("="*94)
# Measured de-embedded arms (STUTTER-7HZ A9.3 / A13.1). Normalised shares: Ls + Lr == 1.
ARMS = {"pooled": (0.55*cmath.exp(1j*math.radians(96)), 1.19*cmath.exp(1j*math.radians(-27))),
        "r36":    (0.69*cmath.exp(1j*math.radians(85)), 1.16*cmath.exp(1j*math.radians(-36))),
        "r38":    (0.42*cmath.exp(1j*math.radians(95)), 1.12*cmath.exp(1j*math.radians(-22)))}
F0 = 7.3
LTOT = {"point":0.976, "optimistic":0.944, "pessimistic":0.990}

def R(f, kp, kd, ki=0, a=None, bb=None):
    """servo-arm ratio vs as-built V282 (Kp 248, Kd 128, Ki 0)."""
    return (C(f,kp,kd,ki)*Hlag(f,a,bb)) / (C(f,Kp,Kd,0)*Hlag(f))

def Lmag(f, kp, kd, arms="pooled", ltot="point", ki=0):
    Ls, Lr = ARMS[arms]
    return LTOT[ltot]*abs(Ls*R(f,kp,kd,ki) + Lr)

print(f"\n  |L(7.3 Hz)| as Kd is swept.  Kp = 0 (the ZN Ku-hunt configuration), Ki = 0.")
print(f"  |L| >= 1.000 = the cycle self-sustains.   as-built V282 (Kp 248, Kd 128) = "
      f"{Lmag(F0,Kp,Kd):.3f} by construction")
print(f"\n  {'Kd':>5} | {'pooled':>7} {'r36':>7} {'r38':>7} | {'pooled@0.990':>12} {'pooled@0.944':>12}")
for kd in [0,32,64,96,128,160,192,256,320,400,500,600,700,800,849,900,1000,1200]:
    print(f"  {kd:>5} | {Lmag(F0,0,kd):>7.3f} {Lmag(F0,0,kd,'r36'):>7.3f} {Lmag(F0,0,kd,'r38'):>7.3f} |"
          f" {Lmag(F0,0,kd,'pooled','pessimistic'):>12.3f} {Lmag(F0,0,kd,'pooled','optimistic'):>12.3f}")

def crossings(kp, arms="pooled", ltot="point", f=F0, lo=1, hi=4000):
    """all Kd where |L| crosses 1.000"""
    xs=[]; prev=Lmag(f,kp,lo,arms,ltot)
    kd=lo
    while kd<hi:
        kd+=0.5; cur=Lmag(f,kp,kd,arms,ltot)
        if (prev-1)*(cur-1)<0:
            a_,b_=kd-0.5,kd
            for _ in range(60):
                m=(a_+b_)/2
                if (Lmag(f,kp,a_,arms,ltot)-1)*(Lmag(f,kp,m,arms,ltot)-1)<0: b_=m
                else: a_=m
            xs.append((a_+b_)/2)
        prev=cur
    return xs

print("\n  Kd values where |L(7.3)| = 1.000  (lower root = ring RE-ARMS below it; upper root = Ku):")
for arms in ARMS:
    for lt in LTOT:
        xs = crossings(0, arms, lt)
        print(f"    Kp=0  {arms:>7} L_tot={LTOT[lt]:.3f} -> " +
              (", ".join(f"Kd={x:.0f}" for x in xs) if xs else "NO CROSSING in [1,4000]"))
print()
for arms in ["pooled"]:
    for lt in LTOT:
        xs = crossings(Kp, arms, lt)
        print(f"    Kp=248 {arms:>7} L_tot={LTOT[lt]:.3f} -> " +
              (", ".join(f"Kd={x:.0f}" for x in xs) if xs else "NO CROSSING in [1,4000]"))

# --- D-clamp reachability: does the Ku dose rail the D clamp? --------------------------------
print("\n  D-CLAMP REACHABILITY.  |D| measured on V283 strong-turn frames = 880-1552 counts at Kd 128.")
print(f"  |D| scales linearly in Kd.  D clamp (0xC61B6) = {CLP_D}.")
print(f"  {'Kd':>6} {'|D| lo':>8} {'|D| hi':>8} {'% of clamp (hi)':>16}")
for kd in [128,160,256,400,600,798,859,1000]:
    lo,hi = 880*kd/128, 1552*kd/128
    print(f"  {kd:>6} {lo:>8.0f} {hi:>8.0f} {100*hi/CLP_D:>15.0f}%" + ("   <-- RAILED" if hi>=CLP_D else ""))
print(f"  => the D path saturates at Kd = {128*CLP_D/1552:.0f} (worst frames) .. {128*CLP_D/880:.0f} (best frames),")
print(f"     i.e. INSIDE the Ku band.  A clean linear Ku is NOT reachable.")

# =============================================================================================
print("\n" + "="*94)
print("Q3b  20 Hz creep-grind damping budget, Kp -> 0 and Kd swept   (plant-free aggregator budget)")
print("="*94)
Zs20 = 1.90*cmath.exp(1j*math.radians(-69))   # GRINDING-DEEP sec2, measured, at Kp 248
Zr20 = 3.23*cmath.exp(1j*math.radians(+5))
S_R24 = 0.43
def Re20(kp,kd,s=S_R24): return (Zs20*R(20,kp,kd) + s*Zr20).real
print(f"  today (Kp 248, Kd 128): Re_total = {Re20(Kp,Kd):+.2f}  (servo {(Zs20).real:+.2f}, r24 {(S_R24*Zr20).real:+.2f})")
print(f"  positive Re = damping.  Below +{Re20(Kp,Kd):.2f} is a regression.")
print(f"\n  {'Kd':>6} | {'Kp=248':>8} {'Kp=0':>8} | {'Kp=0 s=0.30':>12} {'Kp=0 s=0.52':>12}")
for kd in [0,64,96,128,160,192,256,400,600,859]:
    print(f"  {kd:>6} | {Re20(Kp,kd):>+8.2f} {Re20(0,kd):>+8.2f} | {Re20(0,kd,0.30):>+12.2f} {Re20(0,kd,0.52):>+12.2f}")

# servo lane damping->anti-damping crossover (phase of Z_servo reaches -90)
def xover(kp,kd,lo=1.0,hi=400.0):
    def g(f): return (Zs20*R(f,kp,kd)).real
    if g(lo)*g(hi) >= 0: return None
    for _ in range(80):
        m=(lo+hi)/2
        if g(lo)*g(m)<0: hi=m
        else: lo=m
    return (lo+hi)/2
print(f"\n  servo-lane Re=0 crossover (above it the LKAS lane PUMPS), Hz:")
print(f"  {'Kd':>6} {'Kp=248':>9} {'Kp=0':>9}")
for kd in [64,96,128,160,192,256,400,859]:
    a,bq = xover(Kp,kd), xover(0,kd)
    print(f"  {kd:>6} {('%.1f'%a) if a else '  n/a':>9} {('%.1f'%bq) if bq else '  n/a':>9}")

print(f"\n  HF gain of the servo arm vs as-built V282 (|C*Hlag*Fb| ratio):")
print(f"  {'cand':>18} " + " ".join(f"{f:>7.0f}Hz" for f in [20,25,40,80,250,500]))
for name,(kp_,kd_) in [("Kp0 Kd128",(0,128)),("Kp0 Kd160",(0,160)),("Kp0 Kd256",(0,256)),
                       ("Kp0 Kd859 (Ku)",(0,859)),("Kp0 Kd387 (ZN-PI)",(0,387)),("Kp248 Kd160 (F)",(248,160))]:
    row=[]
    for f in [20,25,40,80,250,500]:
        rr = abs(C(f,kp_,kd_,0)*Hlag(f)*Fb(f))/abs(C(f,Kp,Kd,0)*Hlag(f)*Fb(f))
        row.append(f"{rr:>9.2f}")
    print(f"  {name:>18} " + "".join(row))

# --- corrected servo-lane Re=0 crossover: model Z_servo(f) as the full electronics chain -----
#     (LOOPSHAPE sec2.1 validated this against the wire to within 4 deg at 7 and 20 Hz)
def Zservo(f,kp,kd,ki=0):
    return Fb(f)*C(f,kp,kd,ki)*(254/256)*Hlag(f)*(GAIN/32768)
K_ANCHOR = 1.90/abs(Zservo(20,Kp,Kd))          # scale so |Z_servo(20, Kp248)| = 1.90 (measured)
PH_ERR = math.degrees(cmath.phase(Zservo(20,Kp,Kd))) - (-69.0)
print(f"\n  [anchor] modelled Z_servo(20 Hz, Kp 248) phase = "
      f"{math.degrees(cmath.phase(Zservo(20,Kp,Kd))):+.1f}d vs measured -69d  (residual {PH_ERR:+.1f}d = the plant)")
print(f"  [anchor] modelled Z_servo(7.3 Hz, Kp 600) phase = "
      f"{math.degrees(cmath.phase(Zservo(7.3,600,Kd))):+.1f}d vs measured -62d")
def xover2(kp,kd,lo=1.0,hi=499.0):
    g=lambda f: (K_ANCHOR*Zservo(f,kp,kd)).real
    if g(lo)*g(hi)>=0: return None
    for _ in range(90):
        m=(lo+hi)/2
        if g(lo)*g(m)<0: hi=m
        else: lo=m
    return (lo+hi)/2
print(f"\n  servo-lane Re=0 crossover (above it the LKAS lane PUMPS), Hz:")
print(f"  {'Kd':>6} {'Kp=248':>9} {'Kp=0':>9}")
for kd in [64,96,128,160,192,256,400,859]:
    a,bq = xover2(Kp,kd), xover2(0,kd)
    print(f"  {kd:>6} {('%.1f'%a) if a else 'none':>9} {('%.1f'%bq) if bq else 'none':>9}")

# =============================================================================================
print("\n" + "="*94)
print("Q3c  ZIEGLER-NICHOLS TRANSLATION BACK INTO CELL VALUES")
print("="*94)
print("""
  UNIT CHAIN (accel frame).  Let e_a = dE/dt be the acceleration error in E-counts/s.
  Then E = integral(e_a dt), and the firmware sum S = Kp_r*E + Kd_r*dE/dt + Ki_r*integral(E) becomes

      S = Kd_r * e_a           <- accel-frame PROPORTIONAL, Kp' = Kd_r = (Kd/8)*T
        + Kp_r * integral(e_a) <- accel-frame INTEGRAL,     Ki' = Kp_r = Kp/256
        + Ki_r * double int.   <- NOT part of any ZN form; must be 0
  so
      Kd = Kp' * 8 / T = Kp' * 8000          (T = 1 ms)
      Kp = Ki' * 256   = (Kp'/Ti) * 256
      Ti (as built)    = Kd_r/Kp_r = (Kd/8)*T/(Kp/256)
  Every downstream factor (254/256 taper, the output lag, the 5346 forward gain, the >>8 and >>3
  shifts, the 32x on sp and the feedback EMA) multiplies P, D and I IDENTICALLY, so none of them
  enters the ZN ratios.  They set the loop's absolute scale, which is exactly what Ku absorbs.
""")
Ti_built = (Kd/8)*T/(Kp/256)
print(f"  as built (V282): Kp' = {(Kd/8)*T:.6f} s   Ki' = {Kp/256:.6f}   Ti = {1000*Ti_built:.2f} ms"
      f"   (1/2*pi*Ti = {1/(2*math.pi*Ti_built):.2f} Hz)")

for label, Kdu, f_osc in [("pooled",859,F0), ("r36 (most servo)",673,F0), ("r38 (least servo)",1072,F0)]:
    Ku_a = (Kdu/8)*T          # accel-frame proportional gain at marginal stability
    Tu   = 1.0/f_osc
    print(f"\n  --- {label}:  Kd_u = {Kdu}  ->  Ku' = {Ku_a:.5f} s ,  f_osc = {f_osc} Hz , Tu = {1000*Tu:.1f} ms ---")
    for form, kfac, ti_fac, td_fac in [("ZN classic PID",0.6,2.0,8.0), ("ZN classic PI",0.45,1.2,None)]:
        Kp_a = kfac*Ku_a; Ti_a = Tu/ti_fac
        kd_cell = Kp_a*8/T; kp_cell = (Kp_a/Ti_a)*256
        line = (f"    {form:<15} Kp'={Kp_a:.5f} Ti={1000*Ti_a:.1f}ms -> "
                f"**Kd (0xE511C) = {kd_cell:.0f}** , **Kp (0xE5378) = {kp_cell:.0f}**")
        if td_fac:
            Td_a = Tu/td_fac
            line += f" , Td={1000*Td_a:.1f}ms -> NO CELL EXISTS (needs d2E/dt2)"
        print(line)
    print(f"    0xC63E6 (Ki) must be 0 in BOTH forms - it is a DOUBLE integral in the accel frame.")

# =============================================================================================
print("\n" + "="*94)
print("Q1  IS THE PLANT AN INTEGRATOR OR A DIFFERENTIATOR IN RATE?  -- pinned from the wire")
print("="*94)
# DC chain, all factors byte-read above.
LAG_DC  = 2*LAG_B/(32*(1024-LAG_A))      # 0.9902
FB_DC   = 2*FB_B/(1024-FB_A)             # 30.891
CNT_PER_DEGS_RAW = 8.0                   # raw rate sample counts per deg/s (kit record)
FB_PER_DEGS = FB_DC*CNT_PER_DEGS_RAW
FWD     = (GAIN/32768)                   # 0.16315 ; gp-0x6752 = -1 supplies the sign
TAPER   = 254/256
print(f"  DC chain (all factors byte-read):  S = (Kp/256)*E = {Kp/256:.5f}*E")
print(f"    -> taper {TAPER:.4f} -> out-lag DC {LAG_DC:.4f} -> fwd gain {FWD:.5f}")
print(f"    => |T| = {(Kp/256)*TAPER*LAG_DC*FWD:.5f} * E     (engagement ramp assumed unity)")
print(f"    fb = {FB_DC:.3f} * raw ; raw = {CNT_PER_DEGS_RAW:.0f} counts per deg/s  => fb = {FB_PER_DEGS:.1f} per deg/s")
T_PER_E = (Kp/256)*TAPER*LAG_DC*FWD
print(f"\n  CONSISTENCY TEST -- reconstruct the commanded rate from the MEASURED (|T|, wheel rate) pairs.")
print(f"  If the plant were an integrator in rate, a sustained |T| could not coexist with a")
print(f"  sustained BOUNDED rate.  If it were a differentiator, a sustained |T| would give rate = 0.")
print(f"\n  {'route/stratum':>22} {'|T|':>6} {'rate':>7} {'E=|T|/k':>9} {'fb':>8} {'32sp':>8} "
      f"{'=> ref deg/s':>13} {'plant g':>9} {'L_dc':>6}")
for lbl,Tm,w in [("r34 V280r2 idx40-60",663,18.5), ("r34 V280r2 idx60-80",657,34.1),
                 ("r35 V281r3 idx40-60",828,5.8), ("r35 V281r3 idx60-80",795,17.8)]:
    E = Tm/T_PER_E; fb = FB_PER_DEGS*w; sp32 = E+fb; ref = sp32/FB_PER_DEGS
    g = w/Tm                                   # deg/s per T count  (the PLANT's DC gain)
    Ldc = FB_PER_DEGS*g*T_PER_E
    print(f"  {lbl:>22} {Tm:>6} {w:>7.1f} {E:>9.0f} {fb:>8.0f} {sp32:>8.0f} {ref:>13.1f} {g:>9.4f} {Ldc:>6.2f}")
print(f"\n  The reconstructed references land at 27-39 deg/s.  The two drive reports independently")
print(f"  record the stall-run references as r35 27 deg/s (mean) and r34 30-44 deg/s.")
print(f"  => the DC chain closes to within a few percent WITHOUT a free parameter. [EVIDENCE]")
print(f"\n  VERDICT: plant DC gain from PID output to measured rate is FINITE and NON-ZERO")
print(f"           (g = 0.007-0.052 deg/s per T count, load-dependent).  L_dc = 0.27-1.99.")
print(f"           The plant is TYPE 0 in rate: constant torque -> constant, bounded, non-zero RATE.")
print(f"           NOT an integrator (L_dc would be infinite, droop zero).")
print(f"           NOT a differentiator (rate would be 0 while |T| = 795-828 counts for 1-3 s).")
print(f"\n  CONSEQUENCE.  With Kp = 0 AND Ki = 0 the controller is C(s) = Kd_r*s, so L(0) = 0 EXACTLY.")
print(f"  Steady-state rate error = 100 %.  The loop has ZERO low-frequency authority; the only")
print(f"  command that reaches the motor is d(32*sp)/dt -- a kick on command CHANGE, nothing held.")

# closed-loop step demo, 1st-order plant fitted to the loaded stall point
print(f"\n  Step response, integer mirror, plant = 1st-order lag (g = 0.030 deg/s/count, tau = 60 ms):")
def sim(kp,kd,ki,steps=4000,ref_degs=25.0,g=0.030,tau=0.060):
    lag_s=0.0; w=0.0; Ep=None; iacc=0.0; out_hist=[]
    a_p=math.exp(-T/tau)
    for n in range(steps):
        sp32 = ref_degs*FB_PER_DEGS
        E = sp32 - FB_PER_DEGS*w
        D = (0 if Ep is None else (E-Ep)*kd/8); Ep=E
        if ki:
            db = E/32; db = db-4 if db>4 else (db+4 if db<-4 else 0)
            iacc = max(-1310720,min(1310720,iacc+db*ki/8)); I=iacc/128
        else: I=0.0
        S = max(-CLP_SUM,min(CLP_SUM,(kp/256)*E + max(-CLP_D,min(CLP_D,D)) + I))*TAPER
        s_new=(LAG_A/1024)*lag_s+(LAG_B/1024)*S; o=(lag_s+s_new)/32; lag_s=s_new
        Tq=max(-CLP_OUT,min(CLP_OUT,o*FWD))
        w = a_p*w + (1-a_p)*g*Tq
        out_hist.append((w,Tq))
    return out_hist
for name,(kp_,kd_,ki_) in [("V282 as built Kp248 Kd128 Ki0",(248,128,0)),
                           ("V283          Kp248 Kd128 Ki50",(248,128,50)),
                           ("Kp0 Kd128 Ki0  (Ku-hunt cfg)",(0,128,0)),
                           ("Kp0 Kd859 Ki0  (at Ku)",(0,859,0)),
                           ("ZN-PI  Kp108 Kd387 Ki0",(108,387,0)),
                           ("ZN-PID Kp241 Kd515 Ki0",(241,515,0))]:
    h=sim(kp_,kd_,ki_); w_ss=h[-1][0]; T_ss=h[-1][1]
    print(f"    {name:<32} rate at 4 s = {w_ss:>6.2f} deg/s of 25.0 requested "
          f"({100*w_ss/25:>5.1f} %), |T| = {abs(T_ss):>6.0f}")

# =============================================================================================
print("\n" + "="*94)
print("Q4  GATE TABLE -- candidate F vs the ZN tunes vs the Ku-hunt configuration")
print("="*94)
print(f"  {'candidate':>26} {'Kp':>5} {'Kd':>5} {'ring':>6} {'|L|7.3':>7} {'|L|@.99':>8} "
      f"{'Re@20':>6} {'ph13.5':>7} {'HFx':>5} {'xover':>6} {'rate%':>6}")
def row(name,kp_,kd_,ki_=0):
    Ls,Lr = ARMS["pooled"]
    ring = abs(Ls*R(F0,kp_,kd_)+Lr)
    ph = math.degrees(cmath.phase(R(13.5,kp_,kd_)))
    hf = abs(C(80,kp_,kd_,0)*Hlag(80)*Fb(80))/abs(C(80,Kp,Kd,0)*Hlag(80)*Fb(80))
    xo = xover2(kp_,kd_)
    h = sim(kp_,kd_,ki_); w=h[-1][0]
    print(f"  {name:>26} {kp_:>5} {kd_:>5} {ring:>6.3f} {0.976*ring:>7.3f} {0.990*ring:>8.3f} "
          f"{Re20(kp_,kd_):>+6.2f} {ph:>+6.1f}d {hf:>5.2f} {(('%.0f'%xo) if xo else 'none'):>6} {100*w/25:>5.1f}%")
row("V282 as built",248,128)
row("V283 (Ki 50)",248,128,50)
row("F: Kd 160 alone",248,160)
row("Kd 192 alone",248,192)
row("Kd 112 alone (DO-NOT-FLASH)",248,112)
row("Kd 64 alone (DO-NOT-FLASH)",248,64)
row("Kp 0 only (Ku-hunt start)",0,128)
row("Kp 0, Kd 64",0,64)
row("Kp 0, Kd 859 = Ku",0,859)
row("ZN-PI   (0.45Ku, Tu/1.2)",108,387)
row("ZN-PID  (0.6Ku,  Tu/2)",241,515)
row("ZN-PI + Ki 50",108,387,50)
row("ZN-PID + Ki 50",241,515,50)
print("""
  ring   = |Ls*R + Lr| at 7.3 Hz, pooled arms (1.000 = today).  |L| >= 1 = the cycle sustains.
  Re@20  = aggregator damping budget at the creep line, s = 0.43 (today +2.06; lower is a regression).
  ph13.5 = change in loop phase at 13.5 Hz (+ returns margin, - spends it; the budget is ~50 deg).
  HFx    = servo-arm gain at 80 Hz vs as-built, through an UNFILTERED differentiator.
  xover  = frequency above which the LKAS lane stops damping and starts pumping.
  rate%  = steady-state rate delivered vs requested, integer mirror, mid-load plant.
""")
