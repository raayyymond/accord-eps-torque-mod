"""K1 (0xC40D2) sign chain: does more modelled Coulomb friction make the wheel lighter or heavier?

Mirrors the decompiled arithmetic of the six functions on the path, integer where the
firmware is integer, float where the firmware genuinely uses the FPU. Every step is
annotated with its instruction address. Constants are byte-read little-endian from the
stock image (V850 is LE). Run:  python analysis-2020accord/friction_k1_sign_chain.py

Frame convention established in SECTION 0 and used throughout:
    DRIVER frame     = the sign convention of gp-0x4f60 (Sensor-B column torque).
    AGGREGATOR frame = the sign convention of gp-0x6b94 / gp-0x6b98 (motor command).
    aggregator_value = POL * driver_value,  POL = gp-0x6752 = -1.
"""

import os
import struct

FW = os.environ.get(
    "ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"
)
IMG = os.path.join(FW, "analysis-2020accord/stock_fw_dump/code.bin")
B = open(IMG, "rb").read()

TP = 0xBF000  # tp+0x5004 == 0xC4004 == float 0.5, the FUN_00036d74 interlock -> anchor
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
s16 = lambda a: struct.unpack_from("<h", B, a)[0]
u8 = lambda a: B[a]
f32 = lambda a: struct.unpack_from("<f", B, a)[0]

assert f32(0xC4004) == 0.5, "tp anchor failed: tp+0x5004 must be float 0.5"


def sar(x, n):
    """V850 arithmetic shift right == Python >> on a signed int (floor). Not C's /."""
    return x >> n


def clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def sgn(x):
    return 1 if x >= 0 else -1  # 0x381c2: (iVar6>=0) - (iVar6<0), zero maps to +1


# --------------------------------------------------------------------------------------
# SECTION 0 -- the frame converter.  gp-0x6752 ("assist polarity") is applied at exactly
# the seven places a signal crosses between the driver frame and the aggregator/motor
# frame, and nowhere else.  Seven sites, one factor, zero counterexamples.
# --------------------------------------------------------------------------------------
POL = -1  # gp-0x6752; 0x48E86 "mov -0x1,r10" / 0x48E88 "st.b r10,-0x6752,gp", record 0x14C0

# ADDRESS PROVENANCE.  "V" = the instruction at this address was read from the live
# database this session (search_instructions / disassemble_bytes dry_run).  "D" = the
# operation is present in this session's decompile but the exact address was NOT pinned
# individually.  Nothing below is inherited from an older memory without re-reading.
CROSSINGS = [
    ("V", "0x3B92E", "FUN_0003b8f6", "ld.b -0x6752 -> cVar5; USED TWICE below"),
    ("D", "  (cVar5)", "FUN_0003b8f6", "gp-0x6b98 (motor cmd)  * cVar5 -> plant-model frame"),
    ("V", "0x3B91C", "FUN_0003b8f6", "ld.h -0x6abc; * cVar5 * 12 -> friction velocity sign"),
    ("V", "0x381EE", "FUN_00038148", "six aggregator lanes   * POL  -> compared vs MODEL"),
    ("V", "0x3668E", "FUN_00036682", "gp-0x4f60 * 0xC646C    * POL  -> aggregator lane gp-0x6b46"),
    ("V", "0x358C2", "FUN_000352b4", "mulh r11,r14: assist mag * POL -> gp-0x6b82 -> gp-0x6b86"),
    ("V", "0x3AB78", "FUN_0003aa2c", "r24/r26 (d/dt gp-0x4f60) * POL -> aggregator addends"),
    ("V", "0x3A71A", "FUN_0003a382", "PID(driver-frame error)  * POL -> gp-0x6ad4"),
]
# gp-0x6ad4 has EXACTLY two touches program-wide -- verified this session:
#   0x3A8A0  st.h r10,-0x6ad4,gp   (FUN_0003a382, the only writer)
#   0x3ACA8  ld.h -0x6ad4,gp,r6    (FUN_0003aa2c, the only reader)
# => no intermediate stage can negate the PID output between the two functions.
#
# SCOPE OF THE "no counterexamples" claim: the seven crossings above are the ones ON
# THIS PATH plus the aggregator's other addends.  gp-0x6752 has 55 ld.b/st.b sites
# program-wide; the other ~48 (motor control, diagnostics, CAN) were NOT audited.

# --------------------------------------------------------------------------------------
# SECTION 1 -- FUN_0003b8f6, the plant model.  Genuinely float (V850E2 FPU).
#   model  = lag(POL*gp-0x6b98)/1024  +  Kang * biquad(lag(gp-0x4f60)/1024)
#   ratio  = clamp(POL * gp-0x6abc * 12 / cal(0xC40BC), +-1)      <- velocity, MODEL frame
#   fric   = clamp(EMA(|model|*ratio*K1/1024 + K0/1024*ratio), +-10)
#   out    = clamp((model - fric - inertia) * cal(0xC6468), +-20000)   -> gp-0x6bfc
# --------------------------------------------------------------------------------------
K1_STOCK = u16(0xC40D2)  # 102   tp+0x50d2, read at 0x3BAFE (ld.hu, hw2 = disp|1)
K0 = u16(0xC4080)  # 0     tp+0x5080, the never-raise pure-relay cell
RATE_KNEE = u16(0xC40BC)  # 600   tp+0x50bc
G_MODEL = u16(0xC6468)  # 2639  tp+0x7468


def friction(model, motor_rate, K1):
    """0x3BB1E..0x3BB90.  Signed: sign(friction) == sign(velocity in the MODEL frame)."""
    v_model = POL * motor_rate * 12  # 0x3BB1E  iVar20 = POL * gp-0x6abc * 12
    ratio = clamp((v_model * 0.5) / (RATE_KNEE * 0.5), -1.0, 1.0)
    raw = abs(model) * ratio * K1 / 1024.0 + K0 / 1024.0 * ratio
    return clamp(raw, -10.0, 10.0)  # EMA omitted: DC gain 1, sign-preserving


def model_out(model, motor_rate, inertia, K1):
    """0x3BBC2 subf.s (model - fric - inertia), then * G_MODEL, clamp +-20000."""
    fric = friction(model, motor_rate, K1)
    return clamp(int((model - (fric + inertia)) * G_MODEL), -20000, 20000)


# --------------------------------------------------------------------------------------
# SECTION 2 -- FUN_0003bc20 @0x3BC20: gp-0x6bfe = gp-0x6bfc.  Pass-through, gain +1.
# SECTION 3 -- FUN_00038148: residual observer.
#   res      = gp-0x6bfe - (ACTUAL >> 4) + gp-0x6bfa          0x381A6 (MODEL - ACTUAL)
#   gp-0x6b70= clamp(sgn(res) * LERP(|res| * 0xC63AE >> 10), +-0xC6200)
# The LERP is on |res| and its slope f' is NON-NEGATIVE, so gp-0x6b70 is an odd,
# monotone-NON-DECREASING function of res  ==>  d(gp-0x6b70)/d(MODEL) >= 0 EVERYWHERE.
# That is what makes this chain robust: it never needs to assume where res sits.
# --------------------------------------------------------------------------------------
RES_SCALE = u16(0xC63AE)  # 1024  tp+0x73ae
REF_CLAMP = u16(0xC6200)  # 8192  tp+0x7200 -- clamps gp-0x6b70 AND the PID's reference


def observer(MODEL, ACTUAL, lerp_slope=0.35):
    res = MODEL - sar(ACTUAL, 4)  # 0x381A6
    idx = sar(abs(res) * RES_SCALE, 10)  # 0x381B4
    y = int(idx * lerp_slope)  # RAM LERP gp-0x64b8[]/gp-0x641c[]
    return clamp(sgn(res) * y, -REF_CLAMP, REF_CLAMP)


# --------------------------------------------------------------------------------------
# SECTION 4 -- FUN_00037fe6: the torque-tracking REFERENCE.
#   iVar4  = -gp-0x6b4a  (speed-scheduled base effort)   + SUM_i lane_i * w_i
#   gp-0x6ad6 = clamp((iVar4 * LERP) >> 10, +-25600)
# All seven weights tp+0x74ad..0x74b3 read 1, and the output LERP tp+0x7aca..0x7ad8 is
# FLAT [1024]*8 => the gain from gp-0x6b70 to gp-0x6ad6 is exactly +1.000.
# --------------------------------------------------------------------------------------
W = {a: u8(TP + a) for a in range(0x74AD, 0x74B4)}
LERP_Y = [u16(TP + 0x7ACA + 2 * i) for i in range(8)]
assert all(w == 1 for w in W.values()), f"weights not all 1: {W}"
assert set(LERP_Y) == {1024}, f"gp-0x6ad6 output LERP not flat: {LERP_Y}"


def reference(speed_term, gp6b70, others=0):
    iVar4 = -speed_term + others + gp6b70 * W[0x74B0]  # 0x38096 .. 0x380E4
    return clamp(sar(iVar4 * 1024, 10), -25600, 25600)  # 0x38136 / 0x38142


# --------------------------------------------------------------------------------------
# SECTION 5 -- FUN_0003a382: the PID, and THE MULTIPLY THE OLD MEMORY MISSED.
#   0x3A7CA  ld.h -0x4f60,gp,r8       iVar30 = gp-0x4f60 - clamp(gp-0x6ad6, +-8192)
#   0x3A7DC                           iVar31 = clamp(iVar30, +-0x2800)
#   ...      P / I / D, ALL positive-coefficient on iVar31
#   0x3A71A  ld.b -0x6752,gp,r16
#   0x3A874  iVar30 = ((P+I+D >> 5) * Kout >> 10) * POL * (POL+1 < 3)
#   0x3A8A0  st.h  r10,-0x6ad4,gp
# --------------------------------------------------------------------------------------
def pid(Td, ref, Kpid=1.0):
    ref_c = clamp(ref, -REF_CLAMP, REF_CLAMP)  # 0x3A7B4, cal 0xC6200
    e = clamp(Td - ref_c, -0x2800, 0x2800)  # 0x3A7CA / 0x3A7DC
    combine = int(e * Kpid)  # P+I+D, all + coefficients
    gate = 1 if (POL + 1) < 3 else 0  # 0x3A874 validity gate
    return combine * POL * gate  # 0x3A874 -- THE MISSING NEGATION


# --------------------------------------------------------------------------------------
# SECTION 6 -- FUN_0003aa2c @0x3ACxx: gp-0x6ad4 is added at +1 into gp-0x6b94, alongside
# r24/r26/gp-0x6b86, all of which already carry POL.  gp-0x6b94 is AGGREGATOR frame.
# --------------------------------------------------------------------------------------
def aggregate(gp6ad4, other_lanes=0):
    return clamp(gp6ad4 + other_lanes, -0x2800, 0x2800)  # 0x3ACF0 / 0x3AD0A


def delivered_driver_frame(gp6b94):
    """Convert the motor command back to the driver's frame -- SECTION 0's factor."""
    return POL * gp6b94


# ======================================================================================
if __name__ == "__main__":
    print("=" * 78)
    print("K1 (0xC40D2) SIGN CHAIN -- stock image", os.path.basename(IMG))
    print("=" * 78)
    print(f"\nPOL = gp-0x6752 = {POL}   (config record 0x14C0, byte+4 = 0xFA)")
    print("Driver<->aggregator frame crossings, every one multiplied by POL:")
    for prov, addr, fn, what in CROSSINGS:
        print(f"  [{prov}] {addr:>9s}  {fn:14s} {what}")
    print("  [V] verified in the live DB this session; [D] in the decompile, addr not pinned")
    print(f"\nK1 stock = {K1_STOCK}   K0 = {K0}   knee 0xC40BC = {RATE_KNEE}"
          f"   G 0xC6468 = {G_MODEL}")
    print(f"weights tp+0x74ad..b3 = {sorted(set(W.values()))}   "
          f"gp-0x6ad6 out LERP = {LERP_Y[0]} (flat) => gain 1.000")

    # ---- one operating point: driver steering RIGHT into a turn, wheel following ----
    # Driver frame positive == the direction the driver is pushing.
    Td = 3000            # gp-0x4f60, counts, driver pushing
    motor_rate = -800    # gp-0x6abc, MOTOR frame; POL*rate > 0 => moving with the push
    model = 2.4          # plant-model total applied torque, driver frame, same sign as Td
    inertia = 0.0
    ACTUAL = 40000       # aggregator-frame six-lane sum, already * POL inside FUN_00038148
    speed_term = 0

    print("\n" + "-" * 78)
    print(f"operating point: Td(gp-0x4f60)={Td}  gp-0x6abc={motor_rate}  "
          f"model={model}  ACTUAL={ACTUAL}")
    print("-" * 78)
    print(f"{'K1':>6} {'fric':>8} {'MODEL':>8} {'6b70':>8} {'6ad6':>8} "
          f"{'err':>8} {'6ad4':>9} {'6b94':>9} {'assist(drv)':>12}")

    rows = {}
    for K1 in (K1_STOCK, 2 * K1_STOCK):
        f = friction(model, motor_rate, K1)
        M = model_out(model, motor_rate, inertia, K1)
        b70 = observer(M, ACTUAL)
        ref = reference(speed_term, b70)
        e = clamp(Td - clamp(ref, -REF_CLAMP, REF_CLAMP), -0x2800, 0x2800)
        u = pid(Td, ref)
        agg = aggregate(u)
        assist = delivered_driver_frame(agg)
        rows[K1] = (f, M, b70, ref, e, u, agg, assist)
        print(f"{K1:>6} {f:>8.3f} {M:>8d} {b70:>8d} {ref:>8d} "
              f"{e:>8d} {u:>9d} {agg:>9d} {assist:>12d}")

    a_lo = rows[K1_STOCK][-1]
    a_hi = rows[2 * K1_STOCK][-1]
    print(f"\ndelta assist (driver frame, same sign as Td) = {a_hi - a_lo:+d}")
    print("sign(Td) =", sgn(Td), " sign(delta assist) =", sgn(a_hi - a_lo))
    verdict = "LIGHTER" if sgn(a_hi - a_lo) == sgn(Td) else "HEAVIER"
    print(f"==> raising K1 delivers MORE torque in the driver's own direction => {verdict}")

    # ---- the closed-loop statement, which is what actually settles it ----
    print("\n" + "=" * 78)
    print("CLOSED-LOOP CHECK -- the self-checking argument")
    print("=" * 78)
    print("""
  u        = POL * K * (Ts - Tref)                       [FUN_0003a382, 0x3A874]
  Ts       = P * u + Text                                [plant: motor unwinds the bar]
  let L    = -P*POL*K  (loop gain in negative-feedback form)
      Ts   = (L*Tref + Text) / (1 + L)

  L > 0 is forced physically: at L < 0 the loop AMPLIFIES Text by 1/(1+L) > 1 (an
  anti-assist), and at L < -1 it runs away.  The car assists and does not run away.
    dTs/dText = 1/(1+L) < 1   -- assist. The loop reduces the driver's effort.
    dTs/dTref = L/(1+L) > 0   -- gp-0x6ad6 IS a TARGET FELT EFFORT.
  ==> lowering the reference lowers the felt effort. No parity count involved.
""")
    for K1 in (K1_STOCK, 2 * K1_STOCK):
        print(f"  K1={K1:>4}: gp-0x6ad6 = {rows[K1][3]:>6d}  (target felt effort, "
              f"driver frame; Td = {Td})")
    d_ref = rows[2 * K1_STOCK][3] - rows[K1_STOCK][3]
    print(f"\n  d(gp-0x6ad6)/dK1 = {d_ref:+d}, i.e. {'AGAINST' if sgn(d_ref) != sgn(Td) else 'WITH'}"
          f" the driver's push  ==> target felt effort FALLS  ==> {verdict}")

    # ---- the derivative statement, valid at every operating point ----
    print("\n" + "=" * 78)
    print("WHY THE ANSWER DOES NOT DEPEND ON THE OPERATING POINT")
    print("=" * 78)
    print("""
  d(friction)/dK1  = |model| * ratio / 1024        sign = sign(ratio) = sign(v_model)
  d(MODEL)/dK1     = -G_MODEL * |model| * ratio/1024        <- OPPOSITE to v_model
  d(res)/d(MODEL)  = +1                                     [0x381A6]
  d(6b70)/d(res)   = f' >= 0   (LERP on |res|, odd, monotone non-decreasing)
  d(6ad6)/d(6b70)  = +1 * w(0xC64B0)=1 * LERP(1024)>>10 = +1.000 exactly
  d(6ad4)/d(6ad6)  = -POL * Kpid = +Kpid   (unless |6ad6| >= 8192, where it is 0)
  d(6b94)/d(6ad4)  = +1                                     [0x3ACF0]
  delivered(drv)   = POL * gp-0x6b94

  Composing: d(delivered_driver_frame)/dK1 has the sign of +v_model, i.e. MORE assist
  in the direction the wheel is already moving.  Only two things can zero it: the +-10
  friction clamp (~50x margin at the real working point) and the +-8192 reference rail.
""")
    print(f"  cross-check vs the kit's independently MEASURED Path-2 sensitivity:")
    print(f"    d(gp-0x6b94)/d(gp-0x6b70) predicted here = +{1.0:.4f} * Kpid  (POSITIVE)")
    print(f"    measured (accord-fprime-compression): +0.2529 / +0.2565 / +0.2617")
    print(f"    ==> signs AGREE. A chain with one extra or one missing negation would")
    print(f"        have predicted a negative sensitivity and contradicted that result.")
