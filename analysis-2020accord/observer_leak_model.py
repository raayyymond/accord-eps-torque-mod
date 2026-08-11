"""Observer leak model -- FUN_0003b8f6 / FUN_00038148, stock 39990-TVA-A160.

Tests the hypothesis that `resid = gp-0x6bfe - (iVar4 >> 4) + gp-0x6bfa` is a
difference of two filtered reconstructions of the SAME delivered motor command,
cancelling at DC and leaking near the resonance.

RESULT: the framing is wrong. The two branches do not carry the same term set,
so the leak is a DC-scale gain, not a phase residue. Run this file to reproduce.

Every constant is byte-read little-endian from the real image. Every arithmetic
line is annotated with the instruction address it mirrors.
Standing kit rule: integer >>, real Q-format, real branch conditions.
"""

import cmath
import os
import struct
import sys

ROOT = os.environ.get(
    "ACCORD_FIRMWARE_ROOT", r"C:/Users/dudei/Desktop/Projects/accord-firmwares"
)
IMG = os.path.join(ROOT, "analysis-2020accord", "stock_fw_dump", "code.bin")

FS = 1000.0  # control task rate, 1 kHz (memory: control-task-tick-confirmed-1khz)
GP = 0xFEDF8000
TP = 0x000BF000

# ---------------------------------------------------------------------------
# image access
# ---------------------------------------------------------------------------

with open(IMG, "rb") as fh:
    IMAGE = fh.read()
assert len(IMAGE) == 0x100000, len(IMAGE)


def u16(addr):
    """Little-endian u16. Offset == absolute address for this image."""
    return struct.unpack_from("<H", IMAGE, addr)[0]


def f32(addr):
    return struct.unpack_from("<f", IMAGE, addr)[0]


def tp_rel(off):
    """tp+off -> absolute. tp = 0xBF000, so tp+0x6000 = 0xC5000, NOT 0xC6000.

    The off-by-0x1000 trap has cost this kit five wrong answers; compute it,
    never eyeball it.
    """
    return TP + off


# ---------------------------------------------------------------------------
# calibrations, all byte-read
# ---------------------------------------------------------------------------

A_CMD = u16(tp_rel(0x50D4))  # 0xC40D4  command-branch EMA alpha numerator, /4096
A_SEN = u16(tp_rel(0x50D8))  # 0xC40D8  sensor-branch EMA alpha numerator, /4096
SEN_G = u16(tp_rel(0x713A))  # 0xC613A  sensor gain, /32768
A_IIR = u16(tp_rel(0x73AC))  # 0xC63AC  iVar4 IIR alpha numerator, /1024
SCALE = u16(tp_rel(0x7468))  # 0xC6468  the shared scale cell -- TWO conventions
LERP_G = u16(tp_rel(0x73AE))  # 0xC63AE  residual LERP index gain, /1024
CLAMP70 = u16(tp_rel(0x7200))  # 0xC6200  gp-0x6b70 clamp
W6 = [u16(tp_rel(0x73A0 + 2 * i)) for i in range(6)]  # 0xC63A0..0xC63AA
K1 = u16(tp_rel(0x50D2))  # 0xC40D2  |model|-proportional Coulomb friction
K0 = u16(tp_rel(0x5080))  # 0xC4080  pure Coulomb -- NEVER RAISE
CLAMP7E = u16(tp_rel(0x507E))  # 0xC407E  inertia-comp clamp / fault interlock
FIR = (f32(tp_rel(0x5048)), f32(tp_rel(0x504C)), f32(tp_rel(0x5050)))

EXPECTED = {
    "A_CMD": 573, "A_SEN": 3686, "SEN_G": 1159, "A_IIR": 102, "SCALE": 2639,
    "LERP_G": 1024, "CLAMP70": 8192, "K1": 102, "K0": 0, "CLAMP7E": 511,
}


def selfcheck_cals():
    got = {k: globals()[k] for k in EXPECTED}
    bad = {k: (v, EXPECTED[k]) for k, v in got.items() if v != EXPECTED[k]}
    assert not bad, f"cal mismatch (image not stock?): {bad}"
    assert W6 == [1024] * 6, W6
    assert FIR == (1.0, 0.0, 0.0), FIR
    print("[ok] all calibrations byte-read LE and match the recorded stock values")
    print(f"     0xC40D4={A_CMD} 0xC63AC={A_IIR} 0xC6468={SCALE} weights={W6}")


# ---------------------------------------------------------------------------
# SECOND METHOD (mandatory): raw LE byte scan for every gp-0x6b98 access.
#
# search_instructions reported 45 matches / truncated:false over 183,570
# already-analysed instructions. That count is load-bearing for section D
# (it establishes that FUN_00042af8 holds the only two normal-path writers),
# so it must be confirmed against the image bytes, not the analysis database.
# ---------------------------------------------------------------------------

def scan_gp6b98():
    """Both encodings. disp16 form: hw2 == 0x9468 (= -0x6b98 as u16, bit0 clear).

    Extended 6-byte form (observed in FUN_00059912/59e7a): hw1 in {0x0784,0x07a4},
    hw2 high byte 0x87, hw3 == 0xff28.
    """
    disp16, ext = [], []
    tgt = struct.pack("<h", -0x6B98)  # b'\x68\x94'
    for off in range(0, len(IMAGE) - 6, 2):
        if IMAGE[off + 2:off + 4] == tgt:
            hw1 = struct.unpack_from("<H", IMAGE, off)[0]
            low = hw1 & 0x07FF
            # 0x0764 = st.h ...,gp ; 0x0724 = ld.h ...,gp ; reg1 field = r4 = gp
            if low in (0x0764, 0x0724):
                disp16.append((off, "st.h" if low == 0x0764 else "ld.h", hw1 >> 11))
        if (IMAGE[off:off + 2] in (b"\x84\x07", b"\xa4\x07")
                and IMAGE[off + 2] == 0x87
                and IMAGE[off + 4:off + 6] == b"\x28\xff"):
            ext.append((off, "ld.h/ld.hu ext"))
    return disp16, ext


def report_scan():
    disp16, ext = scan_gp6b98()
    writers = [d for d in disp16 if d[1] == "st.h"]
    print(f"\n[scan] gp-0x6b98: {len(disp16)} disp16 + {len(ext)} extended "
          f"= {len(disp16) + len(ext)} total (Ghidra search_instructions: 45)")
    print(f"[scan] WRITERS (st.h), the load-bearing set:")
    for off, _, reg in writers:
        print(f"         0x{off:05x}  st.h r{reg}, -0x6b98, gp")
    return writers


# ---------------------------------------------------------------------------
# the two filters, as z-domain transfer functions
# ---------------------------------------------------------------------------

def ema(alpha_num, alpha_den, f, poles=1):
    """y[n] += (x[n] - y[n]) * alpha   ->   H(z) = a / (1 - (1-a) z^-1).

    Mirrors, for the command branch (poles=2):
      0x3B93A  fVar18 = (u - gp-0x3628) * cal(0xC40D4) * (1/4096) + gp-0x3628
      0x3B95C  fVar18 = (fVar18 - gp-0x3624) * cal(0xC40D4) * (1/4096) + gp-0x3624
    and for branch B's IIR (poles=1):
      0x381B8  gp-0x374c += (target*16 - gp-0x374c) * cal(0xC63AC) >> 10
    """
    a = alpha_num / alpha_den
    z = cmath.exp(2j * cmath.pi * f / FS)
    h = a / (1 - (1 - a) / z)
    return h ** poles


def H_A(f):
    """Command branch of the observer: 2-pole EMA at alpha = 0xC40D4/4096."""
    return ema(A_CMD, 4096, f, poles=2)


def H_B(f):
    """Branch B: single-pole IIR at alpha = 0xC63AC/1024."""
    return ema(A_IIR, 1024, f, poles=1)


# ---------------------------------------------------------------------------
# the net scale on each branch -- this is section A.4
# ---------------------------------------------------------------------------

def net_scales():
    """0xC6468 is a RAW FLOAT MULTIPLIER in FUN_0003b8f6 and Q10 in FUN_00038148.

    Branch A  @0x3B90E  u  = gp-0x6b98 * polarity * 0.0009765625   (= /1024)
              @0x3BBEC  out= (int)(cal(0xC6468) * model)           (raw multiply)
              => net  SCALE/1024

    Branch B  @0x38180  per lane: (lane * gate * w) >> 10,  w = 1024 => unity
              @0x381A6  x = (sum * polarity * cal(0xC6468)) >> 10
              @0x381B8  IIR on x*16 ; @0x38214 read back as iVar4 >> 4
              => net  SCALE/1024   (the *16 / >>4 is IIR resolution only)
    """
    a = SCALE / 1024.0
    b = (SCALE * 1024 // 1024) / 1024.0  # w=1024 cancels the >>10; then /1024 net
    return a, b


# ---------------------------------------------------------------------------
# the leak
# ---------------------------------------------------------------------------

def leak(f, kappa):
    """Counts of `resid` per count of delivered command gp-0x6b98.

    resid = gp-0x6bfe - (iVar4 >> 4) + gp-0x6bfa            @0x38208-0x38218

    kappa = the fraction of a gp-0x6b98 excursion that the SIX lanes of branch B
    reproduce. kappa=1 is the hypothesis's premise (same signal, two filters);
    kappa=0 is "no shared content at all". The true value is strictly < 1
    because branch B omits gp-0x6ad4 (this loop's own PID output), r24, r26,
    gp-0x6b62, gp-0x6ade, gp-0x6b86 and FUN_00036682, and because gp-0x6b94
    reaches gp-0x6b98 only through the governor slew, the comp-add, the Q15
    shaper blend and the ADD of the CAN-arbitrated term gp-0x6afe.
    """
    sa, sb = net_scales()
    return abs(sa * H_A(f) - kappa * sb * H_B(f))


def phases(f):
    return (cmath.phase(H_A(f)) * 180 / cmath.pi,
            cmath.phase(H_B(f)) * 180 / cmath.pi)


def report_leak():
    sa, sb = net_scales()
    print(f"\n[scale] branch A net = {sa:.4f}   branch B net = {sb:.4f}  "
          f"(0xC6468={SCALE}; the two conventions CANCEL to the same factor)")

    print("\n[phase] the golden model's phase-mismatch figures, re-derived:")
    for f in (7.79, 21.09):
        pa, pb = phases(f)
        ma = 20 * cmath.log10(abs(H_A(f))).real
        mb = 20 * cmath.log10(abs(H_B(f))).real
        print(f"    {f:6.2f} Hz   A {ma:6.2f} dB {pa:7.2f} deg | "
              f"B {mb:6.2f} dB {pb:7.2f} deg | mismatch {abs(pa - pb):5.2f} deg")

    print("\n[leak] |resid| counts per count of gp-0x6b98, vs the term-overlap kappa:")
    print("        kappa      DC     7.79 Hz    21.0 Hz   |  7.79/DC   21/DC")
    for kappa in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
        d, r, g = leak(0.0, kappa), leak(7.79, kappa), leak(21.09, kappa)
        ratio_r = f"{r / d:8.2f}" if d > 1e-9 else "     inf"
        ratio_g = f"{g / d:7.2f}" if d > 1e-9 else "    inf"
        print(f"       {kappa:4.2f}  {d:8.4f}  {r:9.4f}  {g:9.4f}  |{ratio_r} {ratio_g}")

    print("\n  READ THIS ROW-WISE, NOT COLUMN-WISE:")
    print("  kappa=1 (the hypothesis's premise) is the ONLY row where the DC leak")
    print("  vanishes and the frequency ratio blows up. Every row with kappa<1 is")
    print("  dominated by a FLAT DC gain that no filter retune can remove.")


# ---------------------------------------------------------------------------
# downstream propagation -- resid -> gp-0x6b70 -> gp-0x6ad6
# ---------------------------------------------------------------------------

def downstream_note():
    """FUN_00038148 @0x382D2 -> FUN_00037fe6 @0x38142 -> FUN_0003a382.

    gp-0x6b70 = clamp(sign(resid) * LERP_RAM(|resid| * 0xC63AE >> 10), +-0xC6200)
    FUN_00037fe6: all seven enable bytes 0xC64AD..0xC64B3 read 1 and the speed
    LERP is flat 1024/1024, so it is a UNITY adder -> gp-0x6ad6.
    FUN_0003a382: gp-0x6ad6 is the PID's FEEDBACK term, err = gp-0x4f60 - it,
    so a positive residual REDUCES the error and the delivered assist.

    The resid -> gp-0x6b70 hop is a RAM-resident LERP whose Y[0] is written
    ep-relative (movea -0x3714,gp,ep @0x39508) and is NOT statically resolvable.
    Its slope is therefore an unknown multiplier on everything below; the leak
    figures above stop at `resid` deliberately, and any counts-at-the-motor
    number would be an invention. Stated as a limit, not smuggled in as a gain.
    """
    print("\n[downstream] resid -> gp-0x6b70 is a LERP whose Y[0] lives in RAM")
    print("  (ep-relative, @0x39508/0x3950C) and is NOT statically resolvable.")
    print("  Its slope multiplies everything downstream, so this model reports")
    print("  the leak AT `resid` and refuses to quote counts at the motor.")
    print("  FUN_00037fe6 is unity (7 enable bytes all 1, speed LERP flat 1024).")


def main():
    selfcheck_cals()
    report_scan()
    report_leak()
    downstream_note()
    print("\n[verdict] The DC leak is large for every kappa<1, and kappa<1 is")
    print("  forced by the term-set mismatch. => the phase-mismatch story is")
    print("  WRONG; 0xC40D4 / 0xC63AC are the wrong cells for this symptom.")
    print("  (V86 already flew 0xC40D4 573->286 and returned a well-powered null.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
