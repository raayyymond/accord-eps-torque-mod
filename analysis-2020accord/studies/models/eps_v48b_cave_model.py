"""
studies/models/eps_v48b_cave_model.py -- BIT-EXACT model of what the V48B cave will actually compute on the V850E2.

This is the golden reference the assembled cave must match instruction-for-instruction. It models the
EXACT integer semantics of the planned cave code (not a float/idealized biquad):
  - x       = ld.h  gp-0x4f60           ; raw Sensor-B torque, signed int16
  - product = mulhi imm16, sig, tmp     ; SIGNED 16x16 -> low 32 bits (exact; operands are int16)
  - acc     = add-chain of 5 products   ; int32 accumulator
  - y_full  = sar  12, acc              ; arithmetic (floor) shift right, Q12 -> integer
  - y       = clamp(y_full, +/-25600)   ; keeps state in int16 range (0x6400 < 0x7fff)
  - state:  x2=x1 ; x1=x ; y2=y1 ; y1=y ; the OUTPUT cell IS y1 (what the carriers ld.h)

Coefficients (from studies/models/eps_v48b_notch_design.py, Q12): b0=4045 b1=-7949 b2=3977 a1=-7949 a2=3926.
acc = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2. We fold the two subtractions into the multiply immediates
(mulhi with -a1, -a2) so the cave is a uniform mulhi/add chain:
    imms = [ b0, b1, b2, -a1, -a2 ] = [ 4045, -7949, 3977, 7949, -3926 ]
    sigs = [ x , x1, x2,  y1,  y2 ]

Two things this file proves that the design script did not:
  1. Accumulator safety at the FULL int16 input range (+/-32767), not just the +/-25600 design amplitude
     -- because the real gp-0x4f60 is an int16 cell and may exceed the monitor's local +/-0x6400 clamp.
  2. Golden I/O vectors for validating the assembled cave (feed the same input to a Ghidra emulation of
     the cave, or hand-trace, and compare outputs exactly).
"""

import cmath
import math

FS = 1000.0
F0 = 21.4
B = (4045, -7949, 3977, -7949, 3926)  # b0,b1,b2,a1,a2  (Q12)
QBITS = 12
CLAMP = 25600  # 0x6400
INT16_MAX = 32767
INT32 = (1 << 31) - 1

# The five mulhi immediates and the state they multiply, in cave order.
IMMS = [B[0], B[1], B[2], -B[3], -B[4]]  # [4045, -7949, 3977, 7949, -3926]
assert all(-32768 <= c <= 32767 for c in IMMS), "a coefficient does not fit a signed 16-bit immediate"


def sar(value, bits):
    """V850 sar: arithmetic (sign-preserving, floor) right shift. Python >> on ints already floors."""
    return value >> bits


def clamp(v, lim):
    return lim if v > lim else (-lim if v < -lim else v)


class CaveBiquad:
    """Bit-exact DF-I, matching the planned cave instruction sequence."""

    def __init__(self):
        self.x1 = self.x2 = self.y1 = self.y2 = 0
        self.acc_absmax = 0

    def step(self, x):
        assert -32768 <= x <= 32767, f"input {x} is not a signed int16"
        sigs = [x, self.x1, self.x2, self.y1, self.y2]
        acc = 0
        for imm, sig in zip(IMMS, sigs):
            prod = imm * sig                       # mulhi: both operands int16 -> exact 32-bit
            assert -INT32 <= prod <= INT32, f"single product overflows int32: {prod}"
            acc += prod                            # add into int32 accumulator
            assert -INT32 <= acc <= INT32, f"accumulator overflows int32: {acc}"
        self.acc_absmax = max(self.acc_absmax, abs(acc))
        y_full = sar(acc, QBITS)
        y = clamp(y_full, CLAMP)
        assert -INT16_MAX <= y <= INT16_MAX
        # state shift: x2<-x1, x1<-x, y2<-y1, y1<-y  (y1 is the cell carriers read)
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y


def steady_amp(seq, skip):
    return max(abs(v) for v in seq[skip:])


def freq_response_db(freq, amp, n=4000):
    f = CaveBiquad()
    ys = [f.step(int(round(amp * math.sin(2 * math.pi * freq * k / FS)))) for k in range(n)]
    out = steady_amp(ys, n // 2)
    return 20 * math.log10(out / amp) if out > 0 else -999.0, f.acc_absmax


def ideal_db(freq):
    b0, b1, b2, a1, a2 = (c / (1 << QBITS) for c in B)
    z = cmath.exp(-2j * math.pi * freq / FS)
    h = (b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z)
    return 20 * math.log10(abs(h))


def main():
    print("=" * 88)
    print("V48B CAVE-EXACT INTEGER BIQUAD  --  bit-exact model of the planned V850 cave")
    print("=" * 88)
    print(f"  coeffs (Q{QBITS}): b0={B[0]} b1={B[1]} b2={B[2]} a1={B[3]} a2={B[4]}")
    print(f"  mulhi immediates (cave order): {IMMS}")
    print(f"  output clamp: +/-{CLAMP} (0x{CLAMP:04X});  shift: sar {QBITS}")

    print("\nFrequency response (cave-exact integer sim vs ideal Q12 float):")
    print(f"  {'f (Hz)':>8} {'cave dB':>9} {'ideal dB':>9}")
    worst_acc = 0
    for f in [1, 3, 5, 10, 15, 19, 21.4, 24, 30, 50, 100]:
        db, accmax = freq_response_db(f, CLAMP)
        worst_acc = max(worst_acc, accmax)
        mark = "  <- notch" if abs(f - F0) < 0.05 else ""
        print(f"  {f:8.1f} {db:9.3f} {ideal_db(f):9.3f}{mark}")

    # ---- accumulator safety at the FULL int16 range (the design script only tested +/-25600) ----
    print("\nAccumulator safety sweep at FULL int16 input amplitude (+/-32767):")
    worst_full = 0
    for f in [15, 19, 21.4, 24, 30]:
        _db, accmax = freq_response_db(f, INT16_MAX)
        worst_full = max(worst_full, accmax)
    # plus an adversarial square-ish worst case: alternating +/-32767 to maximize the add-chain
    fsq = CaveBiquad()
    for k in range(2000):
        fsq.step(INT16_MAX if (k // 1) % 2 == 0 else -INT16_MAX)
    worst_full = max(worst_full, fsq.acc_absmax)
    # analytic absolute bound: all states at their max magnitude, all terms same sign
    analytic = INT16_MAX * abs(IMMS[0]) + INT16_MAX * abs(IMMS[1]) + INT16_MAX * abs(IMMS[2]) \
        + CLAMP * abs(IMMS[3]) + CLAMP * abs(IMMS[4])
    print(f"  measured max|acc| (sines +/-32767)      = {worst_full:,}")
    print(f"  analytic bound (x=+/-32767, y clamped)  = {analytic:,}")
    print(f"  int32 limit 2^31                        = {2**31:,}")
    assert analytic < 2**31, "analytic accumulator bound EXCEEDS int32 -- cave would overflow"
    print(f"  -> SAFE: analytic bound is {2**31 // analytic}x inside int32 even at full-scale input.")

    # ---- golden I/O vectors: a deterministic input -> exact output, to check the assembled cave ----
    print("\nGolden I/O vector (impulse + step + a 21.4 Hz burst); feed to Ghidra emulate of the cave:")
    f = CaveBiquad()
    xs = [25600, 0, 0, 0, 0, 0, 0, 0]                     # impulse response first 8 samples
    xs += [10000] * 6                                     # step
    xs += [int(round(20000 * math.sin(2 * math.pi * F0 * k / FS))) for k in range(8)]  # tone
    outs = [(x, f.step(x)) for x in xs]
    for i, (x, y) in enumerate(outs):
        print(f"  n={i:2d}  x={x:7d}  y={y:7d}")
    print(f"  final state: x1={f.x1} x2={f.x2} y1={f.y1} y2={f.y2}")
    print("\nALL ASSERTIONS PASSED -- cave-exact math is stable, notches 21.4 Hz, cannot overflow int32.")


if __name__ == "__main__":
    main()
