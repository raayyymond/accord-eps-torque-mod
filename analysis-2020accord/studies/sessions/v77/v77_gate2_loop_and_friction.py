"""v77 GATE 2 -- the firmware-side loop gain/phase, and the drag budget.

🛑🛑 TWO STANDING WARNINGS ADDED 2026-08-12 -- READ BEFORE CITING ANY NUMBER THIS SCRIPT PRINTS.

  (1) THE `net` COLUMN IS A SWEEP, NOT AN ESTIMATE. `g4` is the one unmeasured factor (line 87 below
      says so in its own words) and it is swept over (0.25, 0.5, 1.0, 2.0). A later session lifted
      the `g4 = 1.0` row out of that bracket and reported 0.59/0.56 -> 1.18/1.12 as "the central
      estimate" for an inversion boundary at W = 1024 -> 2048. THIS SCRIPT NEVER CLAIMED THAT.
      Cite the whole sweep or cite nothing. The qualitative point -- that `net = 1 - L` CAN cross
      zero -- survives; the specific numbers do not.

  (2) THE TOPOLOGY BELOW IS INCOMPLETE. It models two parallel FEED-FORWARD paths closing only
      through the physical plant. Path 2 is ALSO a real firmware-side CLOSED LOOP:
      gp-0x6b98[n-1] -> FUN_0003b8f6 -> gp-0x6bfc -> FUN_0003bc20 -> gp-0x6bfe, one sample of delay
      at 1 kHz, and gp-0x6bfe is one of the three terms forming iVar6. `net = 1 - L` does not
      contain that path at all. Its loop gain lives in eight float coefficients at tp+0x50d4 /
      0x50d8 / 0x504c / 0x5050 / 0x50bc / 0x50d0 / 0x50d2 / 0x50d6 -- NEVER BYTE-READ.

  => memory/accord/firmware/accord-fun38148-weights-have-an-unresolved-sign.md. This is why 0xC63A6 was struck
     NO-GO and why V95 MEASURES gp-0x374c / gp-0x6b70 instead of simulating them.

🛑 TOPOLOGY CORRECTION (the v77 session, fresh decompile of FUN_0003aa2c + FUN_00038148):
   the brief's chain `FUN_00038148 -> ... -> gp-0x6ad4 -> back into the aggregator` is NOT a closed
   firmware loop. `gp-0x6ad4` is added into **FUN_0003aa2c** (the 11-lane torque aggregator), and
   `gp-0x6ad4` does NOT appear anywhere in FUN_00038148. The damper reaches the motor by TWO
   parallel FEED-FORWARD paths and closes only through the PHYSICAL plant:

     PATH 1 (direct)  gp-0x6bd0 --[gate +/-2048, NO weight cal]--> FUN_0003aa2c   @0x3ac78 / 0x3acce
     PATH 2 (model)   gp-0x6bd0 --[x 0xC63A0/1024]--> FUN_00038148 sum
                       --[x 0xC6468/1024 = 2.5771]--> IIR(alpha = 0xC63AC/1024 = 102/1024)
                       --> gp-0x6b70 --[x1]--> FUN_00037fe6 --> gp-0x6ad6
                       --> ERR = gp-0x4f60 - clamp(gp-0x6ad6, +/-8192)      <-- SUBTRACTED
                       --> P + I + D --> gp-0x6ad4 --[plain add @0x3acd6]--> FUN_0003aa2c

   => net motor contribution of the damper = ( 1 - PID(jw) * K(jw) ) * gp-0x6bd0
      PATH 2 CANCELS PATH 1. `0xC63A0` 1024->2048 DOUBLED the cancelling replica.

ALL COEFFICIENTS BELOW ARE BYTE-READ (see the trace report): they are EVIDENCE.
"""
import cmath
import math

T = 0.001                       # 1 kHz control task [EVIDENCE: one caller FUN_0002214a for all four]

# --- FUN_0003a382, stock cals, from the decompile ------------------------------------------------
GAIN_A = 256                    # 0xC6B26 LERP Y[0..1] at |rate| < 300..2000 ct   (P schedule)
GAIN_B = 98                     # 0xC6B12..18 FLAT                                 (I schedule)
GAIN_C = 2048                   # 0xC6AE6..EC FLAT                                 (D raw schedule)
GAIN_D = 1024                   # 0xC67B8..C FLAT                                  (combine gain)
ALPHA_P = 1024                  # 0xC6450 = unity -> P's IIR is an IDENTITY at stock
ALPHA_D = 1024                  # 0xC644A = unity -> the dirty-derivative pole is an IDENTITY

# --- the combine, mirrored exactly ----------------------------------------------------------------
# P_target = ((ERR * GAIN_A) >> 10) << 5          @0x3a7e8 / 0x3a7f4 / 0x3a7f6
# I       += (GAIN_B * ERR) >> 10                  @0x3a81a / 0x3a81c
# D_raw    = ((ERR - ERR_prev) * GAIN_C) >> 10     @0x3a836 / 0x3a838 / 0x3a844 ; then << 5
# combine  = (((D + I + P) >> 5) * GAIN_D) >> 10   @0x3a87e..0x3a886
KP = (GAIN_A / 1024) * 32 / 32 * (GAIN_D / 1024)            # per unit ERR, after the >>5
KI_PER_TICK = (GAIN_B / 1024) / 32 * (GAIN_D / 1024)        # per tick, after the >>5
KD_PER_TICK = (GAIN_C / 1024) * 32 / 32 * (GAIN_D / 1024)   # multiplies (ERR[n]-ERR[n-1])
print("=" * 100)
print("1. THE PID, as continuous coefficients (all from byte-read cals)")
print("=" * 100)
print(f"   combine = KP*ERR + I + KD*(ERR[n]-ERR[n-1]),  I += KI*ERR each 1 ms tick")
print(f"     KP = (256/1024)*32/32           = {KP:.6f}   [dimensionless]")
print(f"     KI = (98/1024)/32               = {KI_PER_TICK:.6f} per tick = {KI_PER_TICK/T:.4f} per second")
print(f"     KD = (2048/1024)                = {KD_PER_TICK:.6f} per sample"
      f" = {KD_PER_TICK*T:.6f} s of lead")
print(f"   ALPHA_P = {ALPHA_P}/1024 = {ALPHA_P/1024:.3f} and ALPHA_D = {ALPHA_D}/1024 ="
      f" {ALPHA_D/1024:.3f} -> BOTH IIRs are IDENTITIES at stock cal.")


def pid(f):
    w = 2 * math.pi * f
    return KP + (KI_PER_TICK / T) / (1j * w) + KD_PER_TICK * T * (1j * w)


def ema(f, alpha):
    """First-order EMA  y += (x-y)*alpha  at 1 kHz, exact discrete response."""
    th = 2 * math.pi * f * T
    return alpha / (1 - (1 - alpha) * cmath.exp(-1j * th))


ALPHA_IIR = 102 / 1024          # 0xC63AC -- FUN_00038148's own IIR, ~16 Hz corner
GLOBAL = 2639 / 1024            # 0xC6468 -- FUN_00038148's global gain
ALPHA_K1 = 37 / 128             # FUN_00041464's first EMA on the rate estimate  [BELIEF: applies to 6abe]

print()
print("=" * 100)
print("2. FIRMWARE-SIDE GAIN AND PHASE at the two symptom frequencies  [EVIDENCE: byte-read cals]")
print("=" * 100)
print(f"   {'f (Hz)':>8s} {'PID |.|':>9s} {'PID ang':>9s} {'IIR16 |.|':>10s} {'IIR16 ang':>10s}"
      f" {'K1 |.|':>8s} {'K1 ang':>8s} {'ZOH ang':>8s}")
for f in (7.79, 8.46, 21.0, 21.09, 42.19):
    p, h, k1 = pid(f), ema(f, ALPHA_IIR), ema(f, ALPHA_K1)
    zoh = -math.degrees(2 * math.pi * f * T / 2)
    print(f"   {f:8.2f} {abs(p):9.4f} {math.degrees(cmath.phase(p)):9.2f}"
          f" {abs(h):10.4f} {math.degrees(cmath.phase(h)):10.2f}"
          f" {abs(k1):8.4f} {math.degrees(cmath.phase(k1)):8.2f} {zoh:8.2f}")

print()
print("=" * 100)
print("3. THE PATH-2 CANCELLATION  net = (1 - PID*K) * damper.   K = W/1024 * 2.5771 * IIR * g4")
print("   g4 = the ONE unmeasured firmware factor: FUN_00038148's stage-2")
print("   (magnitude/sign extract + a RAM-resident LERP + clamp to +/-8192, incl. the *16 / >>n).")
print("   Everything else in K is byte-read. g4 is presented as a SWEEP, not a guess.")
print("=" * 100)
for W, tag in ((1024, "stock"), (2048, "V72..V76")):
    print(f"\n   0xC63A0 = {W} ({tag}):")
    print(f"     {'f':>7s} {'g4':>6s} {'|PID*K|':>9s} {'ang':>8s} {'net = |1-PID*K|':>17s} {'verdict':>26s}")
    for f in (7.79, 21.0):
        for g4 in (0.25, 0.5, 1.0, 2.0):
            K = (W / 1024) * GLOBAL * ema(f, ALPHA_IIR) * g4
            L = pid(f) * K
            net = 1 - L
            v = ("damper INVERTED at the motor" if net.real < 0 else
                 "damper weakened" if abs(net) < 1 else "damper intact")
            print(f"     {f:7.2f} {g4:6.2f} {abs(L):9.4f} {math.degrees(cmath.phase(L)):8.2f}"
                  f" {abs(net):17.4f} {v:>26s}")

print()
print("=" * 100)
print("4. THE DRAG BUDGET -- counts of OPPOSING torque into FUN_0003aa2c's +/-10240 sum")
print("=" * 100)
RATE_SCALE = 4.7121


def damper_dose(cy0, EX, EY, rate_ct):
    def lerp(x, xs, ys):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        for j in range(len(xs) - 1):
            if xs[j] <= x <= xs[j + 1]:
                return ys[j] + (ys[j + 1] - ys[j]) * (x - xs[j]) // (xs[j + 1] - xs[j])
        return ys[-1]
    return min((cy0 * lerp(abs(rate_ct), EX, EY)) >> 10, 512)


BUILDS = {
    "stock":  (0,   [60, 400, 2500, 4000], [0, 140, 539, 927], -9830, 511),
    "V74":    (429, [12, 400, 2500, 4000], [0, 539, 539, 927], -14745, 850),
    "V75":    (566, [12, 200, 2500, 4000], [0, 539, 539, 927], -14745, 850),
    "V77-a":  (566, [12, 400, 2500, 4000], [0, 539, 539, 927], -14745, 850),
}
# gp-0x6c2c is a DC-BLOCKED differentiator: gain ~0 at DC, 3.08x @7.79 Hz, 7.5x @20.9 Hz
# relative to the underlying rate.  [EVIDENCE: FUN_00041464 K1/K2 cascade, triple-verified prior]
C2C_GAIN = {"DC (sustained turn)": 0.0, "7.79 Hz": 3.08, "20.9 Hz": 7.50}
FRIC_PER_COUNT = 0x111 / 2 ** 24            # = sVar7 * 1.62721e-5

print(f"   {'regime':22s} {'rate ct':>8s} {'deg/s':>7s} | "
      + " | ".join(f"{b:>22s}" for b in BUILDS))
for regime, cg in C2C_GAIN.items():
    for rate in (47, 94, 236, 461):
        row = f"   {regime:22s} {rate:8d} {rate/RATE_SCALE:7.1f} | "
        cells = []
        for b, (cy0, EX, EY, fy0, clamp) in BUILDS.items():
            d = damper_dose(cy0, EX, EY, rate)
            fr_raw = abs(fy0) * FRIC_PER_COUNT * (cg * rate)
            fr = min(fr_raw, clamp)
            cells.append(f"D{d:4d} F{fr:6.0f}{'*' if fr_raw > clamp else ' '}")
        print(row + " | ".join(f"{c:>22s}" for c in cells))
print("   D = damper gp-0x6bd0 (direct lane).  F = friction gp-0x6b26.  * = 0xC407E clamp BINDING.")
print("   'DC' row: the operator's own complaint shape (strong command, wheel turns slowly).")
print("   => at DC the friction lane contributes EXACTLY ZERO (its input is DC-blocked);")
print("      the ONLY sustained new drag at creep is the DAMPER, which stock does not have at all.")
