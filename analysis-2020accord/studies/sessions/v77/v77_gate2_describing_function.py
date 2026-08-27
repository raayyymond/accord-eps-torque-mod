"""v77 GATE 2 -- the describing function of the base-assist damper, stock vs V74 vs V75.

🛑 EVERY line of `damper_dose()` mirrors the decompiled integer arithmetic EXACTLY: integer `//`,
the real `>>10`, the real clamp order. dB/Hz interpretation comes after the code, never instead.

FIRMWARE FACTS USED (all byte-read this session from the plain images -- see
studies/sessions/v77/v77_gate2_extract_surfaces.py for the raw hex):

  dose_mag = clamp( (FactorC(speed_ct) * FactorE(|rate_ct|)) >> 10 , ceiling(gp-0x6ac2) )
  out      = sign(gp-0x6abe) * dose_mag                       @0x3469E cmp r0,r11 / ble / subr r0,r8

  FactorC[26] @0xD77D0  X = [2240, 3840, 5120, 8960]
                        Y = stock [  0, 234, 429, 908]
                            V74   [429, 234, 429, 908]
                            V75   [566, 234, 429, 908]
  FactorE[26] @0xD780C  X = stock [ 60, 400, 2500, 4000] / V74 [12, 400, 2500, 4000]
                                                         / V75 [12, 200, 2500, 4000]
                        Y = stock [  0, 140,  539,  927] / V74 = V75 [0, 539, 539, 927]
  ceiling[26] @0xD70A8  X = [300, 800]  Y = [512, 1024], indexed by gp-0x6ac2, a SIGN-GATED
                        BACK-DRIVE detector that reads 0 in ordinary driving => ceiling == 512.

  creep := speed_ct < 2240 (= 35.0 km/h; speed_ct = km/h * 64) => FactorC is FLAT at Y[0].
  column deg/s = rate_ct / 4.7121.

The damper at creep is therefore a STATIC ODD nonlinearity of rate alone:
      u(r) = sign(r) * g(|r|),   g(|r|) = min( (C_Y0 * E(|r|)) >> 10 , 512 )
...PROVIDED sign(gp-0x6abe) is in phase with the rate that indexes FactorE (gp-0x6ac0). That
premise is flagged [BELIEF] here and is being confirmed in Ghidra separately.
"""
import math

# ----------------------------------------------------------------------------------------------
# THE FIRMWARE ARITHMETIC -- integer, exactly as decompiled
# ----------------------------------------------------------------------------------------------
RATE_CT_PER_DEG_S = 4.7121          # column deg/s = counts / 4.7121   [kit-settled, re-verified]
SPEED_CT_PER_KMH = 64
CREEP_SPEED_CT = 0                  # any speed < FactorC X[0]=2240 gives the same answer
CEILING_FLOOR = 512


def lerp_int(x, xs, ys):
    """The integer LERP the firmware performs inline (0x3AB80.. / 0x3AC28..).

    Below xs[0] CLAMPS to ys[0]; above xs[-1] CLAMPS to ys[-1]; between it is the decompile's
    `((y[j+1]-y[j]) * (x - x[j])) / (x[j+1]-x[j]) + y[j]` -- C integer division, truncating toward
    zero. All operands non-negative here so `//` matches.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for j in range(len(xs) - 1):
        if xs[j] <= x <= xs[j + 1]:
            span = xs[j + 1] - xs[j]
            if span == 0:
                return ys[j]
            return ys[j] + (ys[j + 1] - ys[j]) * (x - xs[j]) // span
    return ys[-1]


class Surface:
    """One build's creep-regime damper surface."""

    def __init__(self, name, CX, CY, EX, EY, ceiling=CEILING_FLOOR, damp_weight=1024):
        self.name = name
        self.CX, self.CY, self.EX, self.EY = CX, CY, EX, EY
        self.ceiling = ceiling
        self.damp_weight = damp_weight          # 0xC63A0, applied downstream in FUN_00038148

    def c_creep(self):
        return lerp_int(CREEP_SPEED_CT, self.CX, self.CY)      # == CY[0] below 2240

    def g(self, rate_ct):
        """|dose| at |rate| = rate_ct, at creep speed. Integer, exact."""
        c = self.c_creep()                                     # FactorC(speed)  -- flat at creep
        e = lerp_int(abs(int(rate_ct)), self.EX, self.EY)       # FactorE(|rate|)
        v = (c * e) >> 10                                       # 0x346xx  mul then shr 10
        return v if v <= self.ceiling else self.ceiling         # `if |v| > ceiling` -> clamp

    def u(self, rate_ct):
        """Signed damper output. sign() taken from gp-0x6abe @0x3469E (assumed in phase w/ rate)."""
        s = 1 if rate_ct >= 0 else -1
        return s * self.g(rate_ct)

    # --- real-valued piecewise-linear knots, for the CLOSED-FORM describing function -------------
    def knots(self):
        """[(breakpoint, slope_after)] for the real-valued relaxation of g() on |r| >= 0."""
        c = self.c_creep()
        pts = [(0.0, 0.0)]
        for x, y in zip(self.EX, self.EY):
            pts.append((float(x), min(c * y / 1024.0, self.ceiling)))
        pts.append((1e9, min(c * self.EY[-1] / 1024.0, self.ceiling)))
        # dedupe + build slopes
        segs = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x1 > x0:
                segs.append((x0, x1, (y1 - y0) / (x1 - x0)))
        return segs


def N_deadzone_ramp(A, b):
    """Describing function of the odd nonlinearity  sign(u)*max(|u|-b, 0), unit slope.

    Classic dead-zone DF:  N = 1 - (2/pi)[ asin(b/A) + (b/A) sqrt(1-(b/A)^2) ] for A >= b, else 0.
    """
    if A <= b:
        return 0.0
    if b <= 0:
        return 1.0
    q = b / A
    return 1.0 - (2.0 / math.pi) * (math.asin(q) + q * math.sqrt(max(0.0, 1.0 - q * q)))


def N_closed(surf, A):
    """N(A) in closed form: decompose the piecewise-linear g into shifted ramps and superpose."""
    segs = surf.knots()
    prev_slope, total = 0.0, 0.0
    for (x0, _x1, s) in segs:
        total += (s - prev_slope) * N_deadzone_ramp(A, x0)
        prev_slope = s
    return total


def N_numeric(surf, A, n=4096):
    """N(A) from the EXACT INTEGER g(): b1 = (4/pi) * int_0^{pi/2} g(A sin th) sin th dth ; N=b1/A."""
    if A <= 0:
        return 0.0
    acc = 0.0
    for k in range(n):
        th = (k + 0.5) * (math.pi / 2) / n
        acc += surf.g(A * math.sin(th)) * math.sin(th)
    b1 = (4.0 / math.pi) * acc * (math.pi / 2) / n
    return b1 / A


# ----------------------------------------------------------------------------------------------
# THE THREE FLOWN SURFACES
# ----------------------------------------------------------------------------------------------
CX = [2240, 3840, 5120, 8960]
STOCK = Surface("stock", CX, [0, 234, 429, 908], [60, 400, 2500, 4000], [0, 140, 539, 927],
                damp_weight=1024)
V74 = Surface("V74", CX, [429, 234, 429, 908], [12, 400, 2500, 4000], [0, 539, 539, 927],
              damp_weight=2048)
V75 = Surface("V75", CX, [566, 234, 429, 908], [12, 200, 2500, 4000], [0, 539, 539, 927],
              damp_weight=2048)

# The symptom amplitudes (rate-signal counts), from the kit's own measurements
A_BURST_MEDIAN = 99            # |gp-0x6ac0| p50 IN-BURST -> amplitude ~= 99/0.7071 = 140
A_BURST = 140                  # sinusoid amplitude implied by that median
A_BURST_69 = 180               # the 6-9 Hz arm's p50 127 -> amplitude 180
A_RATCHET = 461                # +/-461 counts at 7.79 Hz
A_GRIND = 1249                 # +/-1249 counts at 21 Hz


def deg_s(ct):
    return ct / RATE_CT_PER_DEG_S


def report_surface(s):
    print(f"\n{'=' * 96}")
    print(f"{s.name}:  FactorC Y[0] = {s.c_creep()}   FactorE X = {s.EX}  Y = {s.EY}"
          f"   0xC63A0 = {s.damp_weight}")
    print(f"{'=' * 96}")
    print("   |rate|ct   deg/s     E(|r|)   dose   segment")
    marks = sorted(set([0, 6, 12, 30, 60, 99, 127, 140, 180, 200, 300, 400, 461, 600, 883,
                        1000, 1249, 1500, 2000, 2500, 3000, 4000, 5000]))
    for r in marks:
        e = lerp_int(r, s.EX, s.EY)
        d = s.g(r)
        seg = ("dead zone" if r <= s.EX[0] else
               "RAMP 1" if r < s.EX[1] else
               ("PLATEAU (relay)" if s.EY[1] == s.EY[2] else "RAMP 2") if r < s.EX[2] else
               "RAMP 3" if r < s.EX[3] else "saturated")
        print(f"   {r:8d} {deg_s(r):8.1f} {e:9d} {d:6d}   {seg}")
    # incremental slopes
    print("   -- incremental slope (counts of damper torque per count of rate) --")
    c = s.c_creep()
    for j in range(3):
        dx = s.EX[j + 1] - s.EX[j]
        dy = (c * s.EY[j + 1] >> 10) - (c * s.EY[j] >> 10)
        print(f"      [{s.EX[j]:5d},{s.EX[j+1]:5d}]  ({deg_s(s.EX[j]):6.1f},{deg_s(s.EX[j+1]):7.1f} deg/s)"
              f"   slope = {dy/dx if dx else 0:8.4f}")


def report_df(surfs):
    print(f"\n{'=' * 96}")
    print("DESCRIBING FUNCTION  N(A) = (fundamental of u)/A   [counts torque per count rate]")
    print("closed form (piecewise-linear relaxation) vs numeric integral over the EXACT integer g()")
    print(f"{'=' * 96}")
    hdr = "     A(ct)   A(deg/s)"
    for s in surfs:
        hdr += f" | {s.name:>8s} clo  num"
    print(hdr)
    As = [20, 30, 50, 75, 100, 140, 180, 200, 250, 300, 400, 461, 600, 800, 1000,
          1249, 1600, 2000, 2500, 3200, 4000]
    for A in As:
        line = f"   {A:7d}   {deg_s(A):8.1f}"
        for s in surfs:
            line += f" | {N_closed(s, A):11.4f} {N_numeric(s, A):5.3f}"
        print(line)

    print(f"\n{'=' * 96}")
    print("PEAK N, and the RELAY INDEX  R = N_peak / N(A_grind=1249)")
    print("  a pure relay has N ~ 1/A  =>  R large;  a linear damper has N flat  =>  R = 1")
    print(f"{'=' * 96}")
    fine = [1.0 * i for i in range(5, 4001)]
    for s in surfs:
        vals = [(N_closed(s, A), A) for A in fine]
        npk, apk = max(vals)
        ngr = N_closed(s, A_GRIND)
        nrt = N_closed(s, A_RATCHET)
        nbr = N_closed(s, A_BURST)
        R = npk / ngr if ngr > 0 else float("inf")
        print(f"  {s.name:6s} N_peak = {npk:7.4f} at A = {apk:7.1f} ct ({deg_s(apk):6.1f} deg/s)"
              f" | N(140) = {nbr:7.4f} | N(461) = {nrt:7.4f} | N(1249) = {ngr:7.4f}"
              f" | R = {R:6.2f}")


if __name__ == "__main__":
    for s in (STOCK, V74, V75):
        report_surface(s)
    report_df([STOCK, V74, V75])
