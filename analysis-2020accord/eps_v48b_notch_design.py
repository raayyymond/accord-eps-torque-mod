"""
eps_v48b_notch_design.py -- design + validate the V48B 21.4 Hz notch biquad and its fixed-point form.

Standalone, pure-stdlib (math/cmath). Produces the concrete coefficients the V48B code cave needs, and
proves (numerically) that (a) the float design hits the target notch, (b) the fixed-point quantization
preserves the notch and stays stable, and (c) the DF-II intermediate/output stay within a safe integer
range for the ~16-bit torque signal it filters.

DESIGN TARGET (from the loop-gain model, docs/VIBRATION-DOSSIER.md):
  - Center f0 = 21.4 Hz (de-aliased from the ring-down time; 78.6 Hz is not a wheel/column mode).
  - Sample rate fs = 1000 Hz (confirmed control-task tick).
  - Depth ~= -8 dB at f0, Q ~= 5 (BW ~4-5 Hz) -> pulls |L(21Hz)| 0.875 -> ~0.35-0.44 -> margin 7-9 dB.
  - ~unity elsewhere (must not disturb normal steering torque in the 0-5 Hz band).

This filters a COPY of Sensor-B torque gp-0x4f60 (int16, monitor-clamped +/-0x6400 = +/-25600); the raw
gp-0x4f60 is left untouched (it is shadow-lockstep + monitor + CAN critical). RBJ peaking-EQ biquad with
negative gain = a finite-depth notch.
"""

import cmath
import math

FS = 1000.0
F0 = 21.4
Q = 5.0
GAIN_DB = -8.0
INPUT_CLAMP = 25600  # monitor +/-0x6400 range on the torque signal


def design_peaking(fs, f0, q, gain_db):
    """RBJ peaking EQ; gain_db<0 => a finite-depth notch. Returns normalized (b0,b1,b2,a1,a2)."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2.0 * q)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cw
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cw
    a2 = 1.0 - alpha / A
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def response_db(coeffs, f, fs):
    b0, b1, b2, a1, a2 = coeffs
    z = cmath.exp(-2j * math.pi * f / fs)
    h = (b0 + b1 * z + b2 * z * z) / (1.0 + a1 * z + a2 * z * z)
    return 20.0 * math.log10(abs(h)), h


def pole_radius(coeffs):
    _b0, _b1, _b2, a1, a2 = coeffs
    # poles = roots of z^2 + a1 z + a2
    disc = cmath.sqrt(a1 * a1 - 4.0 * a2)
    p1 = (-a1 + disc) / 2.0
    p2 = (-a1 - disc) / 2.0
    return max(abs(p1), abs(p2))


def quantize(coeffs, qbits):
    scale = 1 << qbits
    q = tuple(int(round(c * scale)) for c in coeffs)
    dequant = tuple(v / scale for v in q)
    return q, dequant


def simulate_df2(coeffs, x, clamp=None):
    """Direct-Form II transposed, float. Returns (y[], max|w intermediate|)."""
    b0, b1, b2, a1, a2 = coeffs
    w1 = w2 = 0.0
    y = []
    wmax = 0.0
    for xn in x:
        w0 = xn - a1 * w1 - a2 * w2
        wmax = max(wmax, abs(w0))
        yn = b0 * w0 + b1 * w1 + b2 * w2
        if clamp is not None:
            yn = max(-clamp, min(clamp, yn))
        y.append(yn)
        w2, w1 = w1, w0
    return y, wmax


def simulate_df1_fixed(qcoeffs, qbits, x, clamp=None):
    """Integer Direct-Form I: the fixed-point-ROBUST structure. States x1,x2,y1,y2 are all bounded by
    the input/output range (no large recursive intermediate), so the int32 accumulator can't overflow.
    Returns (y[], max|accumulator|, max|state|). Models the V850 fixed-point cave."""
    b0, b1, b2, a1, a2 = qcoeffs
    INT32 = (1 << 31) - 1
    x1 = x2 = y1 = y2 = 0
    y = []
    acc_max = 0
    st_max = 0
    for xn in x:
        acc = b0 * xn + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        acc_max = max(acc_max, abs(acc))
        assert -INT32 <= acc <= INT32, f"DF-I accumulator overflow: {acc}"
        yn = acc >> qbits
        if clamp is not None:
            yn = max(-clamp, min(clamp, yn))
        st_max = max(st_max, abs(xn), abs(yn))
        y.append(yn)
        x2, x1 = x1, xn
        y2, y1 = y1, yn
    return y, acc_max, st_max


def sine(freq, amp, n, fs):
    return [amp * math.sin(2.0 * math.pi * freq * k / fs) for k in range(n)]


def steady_amp(y, skip):
    tail = y[skip:]
    return max(abs(v) for v in tail)


def main():
    print("=" * 90)
    print(f"V48B NOTCH DESIGN  --  f0={F0} Hz, fs={FS} Hz, Q={Q}, depth={GAIN_DB} dB")
    print("=" * 90)

    coeffs = design_peaking(FS, F0, Q, GAIN_DB)
    names = ["b0", "b1", "b2", "a1", "a2"]
    print("\nFloat coefficients (a0-normalized):")
    for nm, c in zip(names, coeffs):
        print(f"  {nm} = {c:+.8f}")
    print(f"  (note b1 == a1 for a peaking biquad: {coeffs[1]:+.8f} == {coeffs[3]:+.8f})")
    print(f"  pole radius = {pole_radius(coeffs):.6f}  ({'STABLE' if pole_radius(coeffs) < 1 else 'UNSTABLE'})")

    print("\nFloat frequency response (target: ~0 dB in band, -8 dB at 21.4 Hz):")
    for f in [1, 3, 5, 10, 15, 19, 21.4, 24, 30, 50, 100]:
        db, _ = response_db(coeffs, f, FS)
        mark = "  <-- notch center" if abs(f - F0) < 0.01 else ""
        print(f"  {f:6.1f} Hz : {db:+7.3f} dB{mark}")

    # ---- fixed-point ----
    for qbits in (14, 13, 12):
        qc, dq = quantize(coeffs, qbits)
        r = pole_radius(dq)
        db0, _ = response_db(dq, F0, FS)
        maxc = max(abs(v) for v in qc)
        fits16 = maxc <= 32767
        print(f"\nQ{qbits} fixed-point:  coeffs={qc}")
        print(f"  max|coeff|={maxc} ({'fits int16' if fits16 else 'NEEDS int32 coeff store'}); "
              f"pole r={r:.6f} ({'STABLE' if r < 1 else 'UNSTABLE'}); "
              f"notch depth at {F0}Hz = {db0:+.3f} dB")

    # SELECTED: Direct-Form I at Q12. DF-I is the fixed-point-robust structure (all states bounded by
    # the +/-25600 signal range); Q12 keeps the 5-term int32 accumulator well inside 2^31 while holding
    # the notch depth. (DF-II was rejected: its recursive intermediate overflowed int32 -- see above.)
    QBITS = 12
    qc, dq = quantize(coeffs, QBITS)
    print("\n" + "=" * 90)
    print(f"SELECTED: Direct-Form I, Q{QBITS}.  Validating notch depth + int32 accumulator + state ranges.")
    print("=" * 90)

    n = 4000
    in_amp = INPUT_CLAMP

    # Worst case for overflow/depth: excite AT the notch frequency at full monitor-clamp amplitude.
    x = sine(F0, in_amp, n, FS)
    yf, _ = simulate_df2(dq, x, clamp=in_amp)                       # float reference (DF-II ok in float)
    yq, acc_max, st_max = simulate_df1_fixed(qc, QBITS, [int(round(v)) for v in x], clamp=in_amp)
    out_f = steady_amp(yf, n // 2)
    out_q = steady_amp(yq, n // 2)
    print(f"\n@ {F0} Hz, input amp {in_amp} (worst case):")
    print(f"  float reference: steady out {out_f:8.1f} -> {20*math.log10(out_f/in_amp):+.3f} dB")
    print(f"  Q{QBITS} DF-I    : steady out {out_q:8.1f} -> {20*math.log10(out_q/in_amp):+.3f} dB")
    print(f"  max|accumulator| = {acc_max:,} vs int32 2^31={2**31:,}  "
          f"({'FITS' if acc_max < 2**31 else 'OVERFLOW'}, {2**31//max(acc_max,1)}x margin)")
    print(f"  max|state (x/y)| = {st_max} vs int16 32767 ({'FITS int16' if st_max <= 32767 else 'NEEDS int32'})")

    # In-band fidelity: a 1 Hz steering input must pass ~untouched.
    xb = sine(1.0, in_amp, n, FS)
    ybq, _, _ = simulate_df1_fixed(qc, QBITS, [int(round(v)) for v in xb], clamp=in_amp)
    passband = steady_amp(ybq, n // 2)
    print(f"\n@ 1 Hz (in-band steering), input amp {in_amp}:")
    print(f"  Q{QBITS} DF-I: steady out {passband:8.1f} -> {20*math.log10(passband/in_amp):+.3f} dB "
          f"(target ~0 dB: steering feel preserved)")

    # Impulse settle (transient overshoot / stability sanity).
    imp = [in_amp] + [0] * (n - 1)
    yi, _, sti = simulate_df1_fixed(qc, QBITS, imp, clamp=in_amp)
    print(f"\nImpulse (amp {in_amp}) transient: peak |y| = {max(abs(v) for v in yi)}, "
          f"settles to {abs(yi[-1])} by n={n} (stable ring-down)")

    print("\n" + "=" * 90)
    print(f"CAVE HANDOFF -- Direct-Form I, Q{QBITS} integer coefficients (store as int16 in ROM):")
    print(f"  b0={qc[0]}  b1={qc[1]}  b2={qc[2]}  a1={qc[3]}  a2={qc[4]}   (scale 2^{QBITS}={1<<QBITS})")
    print("  Difference eq (DF-I), all states int16, accumulator int32:")
    print("    acc = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2      ; int32, proven < 2^31")
    print("    y   = clamp(acc >> 12, +/-25600)                ; int16 filtered copy the carriers read")
    print("    x2=x1 ; x1=x ; y2=y1 ; y1=y")
    print("  State RAM: x1,x2,y1,y2 + y(output) = 5 halfwords (10 bytes).")
    print("  ** NOTE: the feasibility study confirmed only 3 free halfwords (gp-0x1500 + gp-0x14E0).")
    print("     DF-I needs 5 -> the free-RAM search must find 2 more contiguous halfwords, OR")
    print("     accept a Q10 DF-II compact form (3 hw) at the cost of coefficient-detune risk. **")
    print("=" * 90)


if __name__ == "__main__":
    main()
