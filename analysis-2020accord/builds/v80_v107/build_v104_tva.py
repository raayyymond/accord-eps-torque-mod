#!/usr/bin/env python3
r"""=================================================================================================
V104 -- the biquad's own gain x1.85 (E1) + LEVER B restored (E2/E3) + CAN 427 repointed to the
        BIQUAD LANE with the shift RESIZED (E4).  Cal-only + three in-place displacement/immediate
        edits.  NO NEW CAVE, NO HOT-PATH INSERTION.  The V103 cave is carried BYTE-IDENTICAL.
=================================================================================================

BASE: **V103** (`_v103_V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN.3680.6B4C.6ADA-ID.B3VARIES_plain_image.bin`)
      sha256 df6104bdf8e4fcb69f3379f5b85fb591e4c64e4c33c16f6f9bf29cc88f48f71d, 1,048,576 B.
      V103 armed Honda's dormant biquad engaged-only; V104 is the first build to DOSE it.

-------------------------------------------------------------------------------------------------
THE PLANT, DECOMPILED.  `FUN_000352b4`, and every constant read LITTLE-ENDIAN off this base.
-------------------------------------------------------------------------------------------------
Ghidra's decompile of the armed branch (tp = 0xBF000, so tp+0x70a8 = 0xC60A8 -- NOT 0xC70A8):

    cVar4 = *(char *)(tp + 0x749b);                       // 0xC649B  ARM CAL   -- V103 set it to 1
    *(short *)(gp + -0x6b7e) = (short)(iVar14 >> 7);       // p[n], the near-DC PEDESTAL
    if ((cVar4 == '\x01') && (<V103's engaged test>)) {
        fVar29 = *(float *)(gp + -0x3818);                                     // w[n-1]
        fVar37 = -( *(float*)(tp+0x70ac) * *(float*)(gp+-0x3814)               // a2 * w[n-2]
                  - -( fVar29 * *(float*)(tp+0x70a8)                           // a1 * w[n-1]
                     - (float)iVar34 * 0.0009765625 * *(float*)(tp+0x70b4) ));  // c4 * u[n]
        fVar38 = *(float*)(gp+-0x3814) + fVar29 * *(float*)(tp+0x70b0) + fVar37;
        *(float *)(gp + -0x3814) = fVar29;                 // w[n-2] <- w[n-1]
        *(float *)(gp + -0x3818) = fVar37;                 // w[n-1] <- w[n]
        ... fVar22 = clamp(fVar38, -12.0f, +12.0f) ...
        iVar34 = (int)(fVar22 * 1024.0);                   // |iVar34| <= 12288
    }
    sVar15 = (short)iVar34 + (short)(iVar14 >> 7);         // filter output + pedestal
    sVar15 = clamp(sVar15, -0x3000, +0x3000);              // +-12288
    *(short *)(gp + -0x6b86) = sVar15;                     // THE LANE OUTPUT

Unfolding the sign nest gives the recursion EXACTLY (u[n] = gp-0x6b82 / 1024):

    w[n] = c4*u[n] - a1*w[n-1] - a2*w[n-2]        a1 = -1.5372   (0xC60A8)
    y[n] = w[n] + b1*w[n-1] + w[n-2]              a2 = +0.63462  (0xC60AC)
                                                  b1 = -1.8808   (0xC60B0)
    gp-0x6b86 = clamp( clamp(y,+-12)*1024 + p, +-12288 )    c4 = +0.81731  (0xC60B4)  <-- E1

i.e. a DIRECT-FORM-II BIQUAD in which **`c4` at 0xC60B4 is a PURE SCALAR INPUT GAIN.**

    H(z) = c4 * (1 + b1*z^-1 + z^-2) / (1 + a1*z^-1 + a2*z^-2)

    zeros   0.94040 +- 0.34007j   |z| = 1.0000000   <-- ON the unit circle => a TRUE NULL
    poles   0.76860 +- 0.20946j   |p| = 0.7966304   <-- well damped, no resonant peak

-------------------------------------------------------------------------------------------------
🛑 WHAT E1 ACTUALLY DOES -- STATED PLAINLY, BECAUSE IT IS NOT WHAT "THE 6-9 Hz LEVER" IMPLIES.
-------------------------------------------------------------------------------------------------
`c4` is a scalar on the INPUT, so x1.85 scales the WHOLE response by 1.85 -- it CANNOT change the
notch's shape, depth or centre frequency.  The zeros are already ON the unit circle, so the null is
already infinitely deep at stock; there is nothing left to deepen.  Measured over the response:

    |H|          DC        Nyquist    MAX          MIN
    stock c4     1.000034  0.999999   1.000034     1.24e-05
    V104 c4      1.850063  1.849998   1.850062     2.30e-05     (max is AT DC)

    |H_new| < 1 ONLY on w/pi in [0.07367, 0.16447] = **9.08 % of the Nyquist axis**
    |H_new| >= 1 on the other **90.9 %**.  Both fractions are SAMPLE-RATE INDEPENDENT.

🛑🛑 **THE SAMPLE RATE IS 1 kHz, AND AN EARLIER DRAFT OF THIS DOCSTRING GOT IT WRONG.**
An earlier revision of this file quoted the notch window as "5.8 .. 10.8 Hz" and the 6-9 Hz band
average as "-14.05 -> -8.71 dB".  **BOTH WERE COMPUTED AT fs = 143 Hz AND ARE RETRACTED.**  The
control task is **1000 Hz**, established twice over -- `control-task-tick-confirmed-1khz` (OSTM0 +
STEER_STATUS=4 dwell), and independently from the `gp-0x381c` EMA whose alpha = 20/2048 reproduces
the observed 1.554 Hz corner only at fs = 1000.  **At fs = 1000 the notch is at 55.23 Hz and
`|H_new| < 1` only on 36.84 .. 82.23 Hz -- nowhere near any symptom band.**  Corrected table:

    f (Hz)    |H_stock|   |H_new|    ratio        <- the ratio is a FLAT SCALAR, as it must be
      6.00       0.9900    1.8314   1.8500           for a pure input gain: there is no band
      7.50       0.9842    1.8208   1.8500           in which c4 attenuates ANYTHING.
     21.73       0.8557    1.5830   1.8500
     26.00       0.7865    1.4549   1.8500
     55.23       0.0001    0.0002   1.8500        <- the null, decades above the symptom
    band-avg  6-9 Hz     -0.14 dB -> +5.20 dB   ratio 1.8500
    band-avg 21.0-22.5   -1.36 dB -> +3.99 dB   ratio 1.8500

⇒ **E1 IS A FLAT x1.85 AUTHORITY RAISE ON THIS LANE IN EVERY BAND THAT MATTERS.**  The notch exists,
but it sits at 55 Hz; it does not attenuate 6-9 Hz, it does not attenuate 20-28 Hz, and there is no
in-band/out-of-band contrast to speak of below 36 Hz.  Calling `c4` "the 6-9 Hz lever" is wrong.
[EVIDENCE -- coefficients read LE off this base image, response evaluated on 200,000 points, and
independently reproduced by the orchestrator at both candidate sample rates.]

⚠ **WHY THE MANUAL ARM IS THE CONTROL FOR ALL OF THIS.**  V103 arms the section ENGAGED-ONLY, and
the disarmed path at `0x35a86` is a literal unity pass-through of the SAME tick's `gp-0x6b82`.  So
`gp-0x6b86` is **k-invariant by construction on manual frames** while engaged frames carry the full
x1.85 -- a within-drive, same-conditions control that costs nothing and needs no extra telemetry.
That is what makes the 427 channel a sufficient in-force witness on its own, and it is why the E5
comparator (below) was judged redundant and dropped rather than traded against a Honda bit.

-------------------------------------------------------------------------------------------------
THE FIVE EDITS.  Every "current" value was read off the V103 image by this builder BEFORE this
table was written -- none of them was taken from the spec or the brief on trust.
-------------------------------------------------------------------------------------------------
| # | address | width | current (verified on V103) | new | what it does |
|---|---------|-------|-----------------------------|-----|---------------|
| E1 | 0xC60B4 | 4 B | `3a3b513f` = 0.81730998f | `fc89c13f` = 1.51202345f | biquad input gain c4, x1.850000 |
| E2 | 0x3AA96 | 1 B | `c5` (**Honda stock**) | `fb` | Lever B gate: `ld.bu -0x683c[gp],r15` -> `-0x6806[gp],r15` |
| E3 | 0xC6446 | 2 B | 512 (**Honda stock**) | 5244 | Lever B arm: r24 gain flat 5244 while LKAS applies |
| E4a| 0x55DF2 | 2 B | `b494` (V102's `gp-0x6b4c`) | `7a94` | CAN 427 source -> `gp-0x6b86`, the BIQUAD LANE |
| E4b| 0x55E10 | 1 B | `a6` (`sar 6`, V96's) | `a4` (`sar 4`) | 427 scaler RESIZED for the new source |

E2/E3 are Lever B, byte-for-byte V67's encoding as last flown on V88 -- `0x3AA96` is the ONLY byte
that moves (hw2's low half; `ld.bu` uses the `disp|1` form, so -0x683c -> 0x97C4|1 = `c5 97` and
-0x6806 -> 0x97FA|1 = `fb 97`), and the 4 bytes the repoint WRITES already exist verbatim at
0x42842 and 0x55C76 (V67's own twins, re-confirmed on this base).  V101/V102/V103 all lost this
lever; the base reads Honda stock at both cells, which this script asserts before writing.

-------------------------------------------------------------------------------------------------
🛑 GATE 3 -- SIZING THE 427 FIELD AGAINST `gp-0x6b86`'s OWN REACHABLE OUTPUT.  NOT a downstream
   clamp, NOT the writer's clamp.  V96 under-used a channel ~4x by sizing against the wrong bound.
-------------------------------------------------------------------------------------------------
THE PACKER, decompiled from `FUN_00055d80` -- it is NOT `|x| >> sar`:

    uVar3 = FUN_00049a5a(x);                                   // FUN_00049a5a IS abs()
    uVar4 = FUN_00049a78(uVar3);                               // a min() helper -- ceiling 0xFFFF
    FUN_00049a90( (int)((uVar4 & 0xffff) * 5) >> SAR, 0, 0x3ff );   // FUN_00049a90 IS clamp(v,lo,hi)

    field = clamp( (|x| * 5) >> SAR, 0, 1023 )      **FIELD IS 10 BITS**

⭐ **AND THE WHOLE PACKER IS EVIDENCE, READ AS INSTRUCTIONS OFF THE BUILT V104 IMAGE** (GhidraMCP,
`disassemble_bytes` over 0x55DF0..0x55E17) -- not inferred from the decompile alone:

    00055df0  ld.h   -0x6b86, gp, r6     24377a94   <-- E4a, the biquad LANE (was -0x6b4c)
    00055df4  jarl   0x00049a5a, lp      bfff663c       abs()
    00055dfa  ori    0xffff, r0, r7      803effff   <-- the min() ceiling IS 0xFFFF, so
    00055dfe  jarl   0x00049a78, lp      bfff7a3c       min(|x|,65535) is a PROVEN no-op here
    00055e06  mul    0x5, r6, r0         e5374002   <-- **THE *5 IS A REAL `mul` INSTRUCTION**
    00055e0a  movea  0x3ff, r0, r8       2046ff03   <-- the 10-bit field literal, 1023
    00055e0e  mov    0x0, r7             003a           clamp lo = 0
    00055e10  sar    0x4, r6             a432       <-- E4b
    00055e12  jarl   0x00049a90, lp      bfff7e3c       clamp(v, 0, 1023)

The `*5` is ALSO validated against TWO flights, exactly: (1498*5)>>6 = 117 = V103's observed max on
route 0x9e, and (1664*5)>>6 = 130 = V102's on route 0x96.  Both asserted below.

REACHABLE OUTPUT OF THE LANE AT k = 1.85 (inputs supplied by the orchestrator, 5 routes engaged):

    |gp-0x6b82| max 940   (p50 12, p95 409, p99 787)          the biquad's INPUT
    |gp-0x6b7e| max 965   (p50 0,  p95 88)                    the additive PEDESTAL
    max|H_new| = 1.850062                                     computed above, max is at DC

    |gp-0x6b86| <= min( 12288 , 1.850062*940 + 965 ) = min(12288, 2704) = **2704 counts**
                        ^ the +-0x3000 store clamp -- NOT binding, 4.5x above the reachable value

    | sar | field at 2704            | % of 1023 | counts / LSB | overflow? |
    |-----|--------------------------|-----------|--------------|-----------|
    |  3  | (2704*5)>>3 = 1690       |   165.2 % |     1.60     | **YES**   |
    |**4**| **(2704*5)>>4 =  845**   | **82.6 %**|   **3.20**   | **no**    |  <-- CHOSEN
    |  5  | (2704*5)>>5 =  422       |    41.3 % |     6.40     |    no     |
    |  6  | (2704*5)>>6 =  211       |    20.6 % |    12.80     |    no     |  <-- V103's byte

⇒ **`sar 4`.**  It is the largest field that cannot overflow: `sar 3` overruns by 1.65x, and every
larger shift wastes resolution (`sar 6`, the byte V103 carries, would under-use the channel 4.0x --
the exact V96 error the design law forbids).  Saturation would begin at ceil(1023*16/5) = **3274
counts**, which is **1.21x above the reachable bound** -- headroom, stated, not assumed away.

⭐ **ENCODING RISK IS ZERO ON BOTH E4 BYTES.**  `a4` has already flown at this exact address (V92),
and `sar 0x4,r6` = `a4 32` appears 12 times in this very image.  The displacement `7a 94` is the
plain LE int16 of -0x6b86 with bit0 = 0 (the `ld.h` form), the same rule that produces the five
`ld.h -X[gp],r6` instructions already proven inside V103's own flown cave.

⚠ **WHAT WE LOSE:** 427 no longer carries `gp-0x6b4c` (the LKAS command lane).  That lane is
characterised across four routes; `gp-0x6b86` has never been on the wire.  [Orchestrator's call --
"the binding uncertainty is the lane, not the loop identification."]

-------------------------------------------------------------------------------------------------
🛑 E5 -- A COMPARATOR RUNG WAS DESIGNED, PRICED AT 44 B, AND **DROPPED**.  THE CAVE IS UNTOUCHED.
-------------------------------------------------------------------------------------------------
Recorded so nobody re-derives it.  The proposal was `|gp-0x6b86| >= |gp-0x6b82|` -> CAN `0x14A`
byte4 **bit 0**, spliced after PASS3, growing the cave 164 -> 208 B.  It was built and verified
once (image `e5f02fec...194b0cbd`, now `SUPERSEDED-DO-NOT-FLASH-E5DROPPED-...`) and then dropped.

**WHY IT WAS DROPPED -- `0x14A` HAS NO FREE BIT.**
🛑 **THE "byte4 bits {2,1,0} ARE FREE" CLAIM IS WRONG.  THE FREE CHANNEL IS BITS 7:3, AND V103 HAS
SPENT ALL FIVE.**  The error is in the 2026-08-21 agent memory
`reference_accord_v103_byte4_free_bits_and_clip_flag_cave_design`, which enumerated which bits
V103's *cave* claims and inferred the remainder were free.  It did the equivalent Honda check for
byte7 and caught it there; it did not do it for byte4.  The older
`accord-can-tx-100hz-base-tick-and-gateway` ("usable free channel is byte4 bits 7:3") was right.
`FUN_00055a98`, decompiled this session, writes all three of bits 2/1/0 BEFORE the hook at
`0x55C0E`:

    *(gp-0x1514) = *(gp-0x1514) & 0xfb | (*(gp-0x6799) & 1) << 2;   // bit 2, UNCONDITIONALLY
    if (gp-0x67fa == 8) { ... } else {
      *(gp-0x1514) = *(gp-0x1514) & 0xfd | (*(gp-0x679b) & 1) << 1; // bit 1, only when state != 8
      *(gp-0x1514) = *(gp-0x1514) & 0xfe |  *(gp-0x679a) & 1;       // bit 0, only when state != 8
    }

and **V103's own cave masks (`0xbf`, `0xdf`, `0x67`) every one of which PRESERVES bits 2:0** --
Honda's three bits were deliberately protected on the flown build.  `andi 0xfe` would have clobbered
`gp-0x679a` on a frame that goes out on the vehicle bus, and the blast radius of that is not
determinable from a TX frame inside this firmware.  byte7 is full too (7:6 ours, 5:4 Honda's
counter, 3:0 the checksum).  ⇒ **The only options were to clobber a Honda bit or to displace one of
V103's five.  Neither was worth it, because E5 was REDUNDANT:**
- the **PASS / ARM-FAIL rule** below is itself a single-drive in-force witness at full 10-bit
  resolution, not one bit;
- the **manual-arm control** (engaged vs manual median `|gp-0x6b86|` binned by `|tq|`) is
  within-drive, scale-free, and independently detects the intermittent-gate case.
⇒ **NO CAVE CHANGE.  The cave stays BYTE-IDENTICAL to V103 at 164 B, 1048 B free**, which also
removes the last hot-path-adjacent risk from this build.

⚠ **AND A REAL BUG THE DROPPED VERSION EXPOSED, worth keeping for any future cave work:** the first
cut APPENDED the 44 B at cave offset `+0xA4`, i.e. *after* V103's `RET` block at `+0x9E`.  The RET
(`movea -0x1518,gp,r6 / jmp [lp]`) is the cave's ONLY exit, so **all 44 bytes would have been dead
code** -- the rung would have read a permanent 0 and reported "arm did not take" on a good build.
**Anything appended to this cave must be SPLICED BEFORE THE RET, never after it.**

✅ **CHECKSUM COVERAGE -- RE-TRACED THIS SESSION, no longer relayed.**  The kit record and the agent
memory both flagged "checksum runs last" as *relayed, not verified*.  It is now EVIDENCE:

    00055c0e  movea -0x1518, gp, r6   <- THE HOOK.  Cave replaces this, restores it, returns here.
    00055c12  mov   0x8, r7               len = 8
    00055c14  movea 0x14a, r0, r8         id  = 0x14A
    00055c18  jarl  0x00057b24, lp    <- THE CHECKSUM, 3 instructions after the hook
    00055c1c  ld.bu -0x1511, gp, r6       result -> byte7 low nibble

**The cave is hooked on the checksum call's own first-argument setup.**  The checksum covers the full
8-byte frame and cannot structurally precede the cave.  Every cave-written bit is covered.

⚠ **RESIDUALS, recorded not fixed.**  (1) **No latch, and it cannot have one** without a 1 kHz tap,
which was rejected -- both operands are IIR/LERP-driven continuous quantities, so a 100 Hz sample of
the inequality is a duty ESTIMATE, not an event count.  **BELIEF:** if either cell carries content
near the 50 Hz Nyquist (the biquad's own pole sits at 42.3 Hz) a plain periodic sample could bias the
duty.  Unquantified; there is no cheaper way to bound it.  (2) **The duty IS the readout** -- see the
engaged-vs-manual contrast and its falsifier above.

-------------------------------------------------------------------------------------------------
PRE-REGISTRATION -- the orchestrator's text, VERBATIM.  Frozen before the drive.
-------------------------------------------------------------------------------------------------
🛑 **ENDPOINT 0 -- DOSE DELIVERY.  THE 427 CHANNEL IS RECTIFIED, SO PRE-REGISTER 1.60, NOT 1.85.**

    ENDPOINT (dose delivery)  6-9 Hz band RMS ratio of the 427 channel, engaged, new build vs
                              V103 route 0x9e, matched exposure.  Frozen estimator.
    PASS      ratio in [1.50, 1.70]   => the c4 edit is IN FORCE.
              The channel is RECTIFIED (Honda's own abs() at 0x55DF4), which folds the spectrum
              and reads a true k=1.85 as 1.603.  This is EXPECTED, not a defect.
    ARM-FAIL  ratio ~= 1.00          => the arm did not take.
    PARTIAL   ratio between          => the engaged gate is intermittent.  Cross-check against the
                                        manual-arm control before interpreting.
    *** DO NOT PRE-REGISTER 1.85.  A RECTIFIED CHANNEL CANNOT RETURN IT. ***

**WHY 1.60 IS A PASS AND NOT A CONFOUND.**  An earlier rule called 1.60 *"confounded, do not
interpret"*, on the grounds that a true k = 1.85 read rectified and a genuinely half-failed arm both
return 1.60.  **There is no half-failed arm on this hardware.**  `c4` is ONE 4-byte cal inside a CRC
block -- it is `fc89c13f` or the image does not boot -- and `0xC649B` is ONE byte in the same block.
**No partial-write path exists, so `k` is BINARY**, and the two hypotheses that actually compete are
k = 1.85 (rectified => 1.603) and arm-did-not-take (=> 1.00), separated by **0.60** against a
**+-2.8 %** per-episode spread.  The rectification bias is also flat in the LSB -- measured 1.6031 at
LSB 4.00 and 1.6032 at LSB 8.00, flat from 1.19 to 8.0 -- so **this build's 3.20 ct/LSB sits inside
that range and the 1.603 carries.**

**Endpoint 1 -- Lever B, and it is separately attributable:**

    STATISTIC   band RMS of rate_f (deg/s), 21.0-22.5 Hz, ENGAGED, 4 s Hann / 50 % overlap /
                detrended.  Frozen estimator.
    EXPOSURE    ONE contiguous engaged block >= 15 s, HELD AT STEADY SPEED IN 50-80 km/h.
                The speed band is PART OF THE PRE-REGISTRATION, not advice.
    REFERENCE   V103 route 0x9e, same speed band, n = 8 blocks: median 1.146 deg/s RMS.
    PASS        below the p5 of that reference set.   LR 14.1:1.
    FAIL        at or above the reference MEDIAN (1.146).
    AMBIGUOUS   between -- report as partial, call it neither way.

🛑 The speed instruction is load-bearing.  Raw over all blocks the base rate spans **59x** -- that is
exposure, not build -- and Lever B's 0.40x is only **0.73 sigma, LR 3.3:1: not a readout.**  Speed-held
at 50-80 km/h it becomes **2.11 sigma, LR 14.1:1.**  Without it the drive says nothing about Lever B.
⚠ Honest limits: the reference set is **8 blocks**, so its p5 is soft; and **12 of V103's 23 blocks
are not steady-speed at all** (within-block 5-95 speed spread p90 = 47.4 km/h).

**Endpoint 2 -- 6-9 Hz `Re(Z)`, unattributable but diagnostic:**

    REFERENCE   V103 route 0x9e, 23 engaged 15 s blocks: p50 -3784, p95 -1489, block SD 1310.
    PASS        Re Z > -1489  =>  "at least one lever moved 6-9 Hz."  LR 12.7:1 for the bundle.
                *** DO NOT READ A PASS AS EVIDENCE FOR c4. ***
    DIAGNOSTIC  Re Z <= -3784 (V103's own MEDIAN) has P <= 0.030 under EVERY hypothesis in which
                either lever works => it FALSIFIES the |kG| = 0.630 / A = 0.440 identification
                WITHOUT needing attribution.

**Non-delivery detector -- within-drive, scale-free:** bin engaged and manual frames by `|tq|`; take
median `|gp-0x6b86|` per bin.  Manual runs the literal bypass (`H = 1`), engaged runs `k*H_stock`.
**At matched `|tq|` the engaged/manual ratio should be ~1.66** (if the pedestal carries ~22 %) **or
~1.85** (if negligible).  **Near 1.00 => the `c4` edit is not in force -- the gate, not the
hypothesis.**  Binning on `|tq|` removes the operating-point confound that refuted the earlier
engagement-edge version.

🛑 **BAND CORRECTION -- do not use 22-26 Hz anywhere.**  `c4` is genuinely inert at **21.0-22.5**
(ratio 0.9726, CI [0.9642, 1.0348], **0 of 3,000 bootstrap draws exceed a 10 % effect**), but it moves
**22-26 Hz to 0.893 with 61 % of draws exceeding 10 %.**  **Pre-register 21.0-22.5 only.**

⚠ **NEVER score `c4` on a broadband ratio.**  `gp-0x6b86 = k*H*gp-0x6b82 + gp-0x6b7e` and the pedestal
is NOT scaled by `c4`, so a broadband RMS ratio returns **1.535** even at zero saturation.  Band-limit
above the pedestal's 1.55 Hz corner.  Clean bands: 6-9 Hz (**1.8500**) and 20-28 Hz (**1.8501**).
⚠ `0x1AB` ships at **50 Hz**, so content above 25 Hz aliases -- **pre-register no band above 25 Hz.**

⭐ **THE MANUAL ARM IS A FREE WITHIN-DRIVE POSITIVE CONTROL.**  V103 arms the biquad engaged-only, so
manual frames run the literal bypass at `0x35a86` and `gp-0x6b86` is **k-invariant by construction**
(24,138 manual frames / 241 s in 8 runs on route `0x9e`).  **The drive answers two questions IN
ORDER:** (1) manual measured vs manual predicted tests the *tap and the reconstruction's amplitude*,
with no dose involved; (2) the engaged 6-9 Hz ratio then measures `k_effective`.  **If (1) fails, (2)
is uninterpretable -- and you will know which of the two broke.**

**Confirmed structurally:** the two levers touch **disjoint lanes** -- the biquad filters `gp-0x6b82`
only, and Lever B moves `gp-0x6ada`/`gp-0x6adc`, which enter `FUN_0003aa2c` at `0x3ab78` as separate
inline terms that never pass through `gp-0x6b86`.  **The delivered `c4` dose is measurable regardless
of Lever B.**

-------------------------------------------------------------------------------------------------
CRC -- TWO trailers, identical to V103's split.
    0x3AA96, 0x55DF2, 0x55E10, the cave  ->  main app block [0x13000,0xC4FFC)  ->  trailer 0xC4FFC
    0xC60B4, 0xC6446                     ->  cal block      [0xC6000,0xC6FFC)  ->  trailer 0xC6FFC
Both recomputed via the existing owning_block/walk_all_blocks machinery.  No new CRC path.
=================================================================================================
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import cmath
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
import build_v67_tva as V67                # noqa: E402  -- Lever B's constants, never re-typed
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V104_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = ("_v103_V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN.3680.6B4C.6ADA"
             "-ID.B3VARIES_plain_image.bin")
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "df6104bdf8e4fcb69f3379f5b85fb591e4c64e4c33c16f6f9bf29cc88f48f71d"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =================================================================================================
# E1 -- the biquad's input gain.  0xC60B4 = tp+0x70b4.
# =================================================================================================
E1_ADDR = 0xC60B4
E1_PRE = bytes.fromhex("3a3b513f")       # float32 0.81730998
E1_POST = bytes.fromhex("fc89c13f")      # float32 1.51202345
E1_K = 1.85

# the three coefficients that must NOT move -- the notch's own shape lives here
BQ_A1, BQ_A2, BQ_B1 = 0xC60A8, 0xC60AC, 0xC60B0
BQ_COEFF_BYTES = bytes.fromhex("f8c2c4bf" "7576223f" "0ebef0bf")   # 0xC60A8..0xC60B3, contiguous
BQ_ARM_CAL = 0xC649B                     # V103's arm -- must already be 1 on the base
BQ_STATE_X1, BQ_STATE_X2 = 0x3818, 0x3814
BQ_FUNC_LO, BQ_FUNC_HI = 0x352B4, 0x35B1F
BQ_OUT_CLAMP = 12288                     # +-0x3000, the gp-0x6b86 store clamp
BQ_FLOAT_CLAMP = 12.0                    # the +-12.0f clamp applied BEFORE the *1024

# =================================================================================================
# E2 / E3 -- LEVER B.  Constants imported from V67, never re-typed.  Last flown on V88.
# =================================================================================================
E2_ADDR = V67.REPOINT_BYTE               # 0x3AA96 -- the ONLY byte that moves
E2_PRE = bytes([V67.REPOINT_FROM[2]])    # c5   ld.bu -0x683c[gp],r15   (Honda's DEAD gate)
E2_POST = bytes([V67.REPOINT_TO[2]])     # fb   ld.bu -0x6806[gp],r15   ("LKAS applying")
E2_INSN_ADDR = V67.REPOINT_ADDR          # 0x3AA94 -- the full 4-byte instruction

E3_ADDR = V67.ARM_ADDR                   # 0xC6446 = tp+0x7446, ONE reader (0x3AC08)
E3_PRE = struct.pack("<H", V67.ARM_STOCK)    # 512
E3_POST = struct.pack("<H", V67.ARM_NEW)     # 5244 = 2.000x the LERP at grind #1's operating point

# =================================================================================================
# E4 -- CAN 427 repointed to the BIQUAD LANE, with the shift RESIZED.  See GATE 3 above.
# =================================================================================================
E4A_ADDR = 0x55DF2                       # displacement half-word of `ld.h ...[gp],r6` @0x55DF0
E4A_PRE = bytes.fromhex("b494")          # -0x6b4c  (V102's LKAS command lane)
E4A_POST = bytes.fromhex("7a94")         # -0x6b86  (the biquad lane output)
E4_LOAD_ADDR = 0x55DF0
E4_LOAD_HW1 = bytes.fromhex("2437")      # ld.h ...[gp],r6 -- opcode/reg fields, MUST NOT MOVE

E4B_ADDR = 0x55E10                       # `sar imm5,r6`  -- imm5 is the low nibble of byte 0
E4B_PRE = bytes.fromhex("a6")            # sar 0x6  (V96's)
E4B_POST = bytes.fromhex("a4")           # sar 0x4  (V104's -- and a byte V92 already flew here)
E4_SAR_BYTE1 = 0x32                      # the second byte of `sar imm5,r6`, unchanged
E4_MASK_ADDR = 0x55E0A                   # movea 0x03FF,r0,r8 -- the 10-bit field literal
E4_MASK_BYTES = bytes.fromhex("2046ff03")
E4_FIELD_MAX = 1023
E4_PACK_MUL = 5
E4_SAR_OLD, E4_SAR_NEW = 6, 4

# the measured input distributions the sizing is built on (orchestrator, 5 routes, engaged)
IN_MAX, IN_P99, IN_P95, IN_P50 = 940, 787, 409, 12      # |gp-0x6b82|
PED_MAX, PED_P95, PED_P50 = 965, 88, 0                  # |gp-0x6b7e|

# the two flight anchors that validate the packer model
PACKER_ANCHORS = ((1498, 6, 117, "V103 route 0x9e observed max on gp-0x6b4c"),
                  (1664, 6, 130, "V102 route 0x96 observed max on gp-0x6b4c"))

# =================================================================================================
# THE CAVE -- V103's 164 B carried BYTE-IDENTICAL, plus E5's 44 B appended after PASS3.
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V103_CAVE_LEN = 164
CAVE_LEN = 164                       # UNCHANGED -- E5 was dropped, the cave is V103's exactly
HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp

# V103's cave layout, by offset -- used to assert every carried block is byte-identical
V103_PASS1, V103_PASS2 = (0x00, 0x2E), (0x2E, 0x5C)      # b6, b5      46 B each
V103_PASS3 = (0x5C, 0x8C)                                 # b7+b4+b3   48 B
V103_BYTE7, V103_RET = (0x8C, 0x9E), (0x9E, 0xA4)         # identity 18 B, return 6 B

# 🛑 E5 (DROPPED) would have been spliced at +0x8C -- AFTER PASS3, BEFORE BYTE7.  Recorded because
# the first cut APPENDED it at +0xA4, past the RET at +0x9E, where it would have been DEAD CODE:
# the RET (`movea -0x1518,gp,r6 / jmp [lp]`) is the cave's ONLY exit.  ANY future append to this
# cave must be SPLICED BEFORE THE RET.  See the docstring for why E5 itself was dropped.
E5_DROPPED_OFF, E5_DROPPED_LEN = 0x8C, 44

# CAN 0x14A byte4 ownership on THIS build.  Honda keeps bits 2:0 -- V103's masks preserve them and
# V104 does not touch the cave at all.  🛑 The free channel is bits 7:3, NOT {2,1,0}.
BIT_OWNERS = {7: "PASS3  LKAS command sign", 6: "PASS1  |6ada| >= |6adc|",
              5: "PASS2  |6ae2| >= |6b26|", 4: "PASS3  r24 lane sign",
              3: "PASS3  D_state sign"}
HONDA_BITS_KEPT = {2, 1, 0}          # gp-0x6799, gp-0x679b, gp-0x679a -- ALL PRESERVED

# V103's Part A code edits (the biquad arm) -- carried, asserted untouched
V103_PARTA = ((0x35A06, bytes.fromhex("844ffb97"), "arm source -> gp-0x6806 engagement flag"),
              (0x35A12, bytes.fromhex("e049"), "cmp r0,r9"),
              (0x35A18, bytes.fromhex("ea370000"), "setfne r6"))

# ---- a linear decoder over the cave payload: every byte must land on an instruction boundary ----
INSN_HW1_2B = {
    "003a": "mov 0x0,r7", "013a": "mov 0x1,r7", "023a": "mov 0x2,r7", "033a": "mov 0x3,r7",
    "043a": "mov 0x4,r7", "413a": "add 0x1,r7", "483a": "add 0x8,r7",
    "c43a": "shl 0x4,r7", "c63a": "shl 0x6,r7",
    "0638": "mov r6,r7", "8031": "subr r0,r6", "6032": "cmp 0x0,r6", "e639": "cmp r6,r7",
    "0731": "or r7,r6", "7f00": "jmp [lp]", "ae05": "bge +4",
}
INSN_HW1_4B = {
    "2437": "ld.h  disp[gp],r6", "8437": "ld.bu disp[gp],r6", "a437": "ld.bu disp[gp],r6",
    "4437": "st.b  r6,disp[gp]", "2436": "movea disp,gp,r6", "c636": "andi  imm,r6,r6",
}
BRANCH_MNEM, BRANCH_SPAN = "bge +4", 4
ST_B4_INSN = bytes.fromhex("4437ecea")      # st.b r6,-0x1514[gp]
ST_B7_INSN = bytes.fromhex("4437efea")      # st.b r6,-0x1511[gp]


def decode_cave(payload, name):
    """Linear sweep.  Raises if any byte is not covered by a known instruction form."""
    i, out = 0, []
    while i < len(payload):
        hw1 = payload[i:i + 2].hex()
        if hw1 in INSN_HW1_2B:
            out.append((i, 2, INSN_HW1_2B[hw1]))
            i += 2
        elif hw1 in INSN_HW1_4B:
            if i + 4 > len(payload):
                raise SystemExit(f"{name}: truncated 32-bit instruction at +0x{i:02X}")
            out.append((i, 4, INSN_HW1_4B[hw1]))
            i += 4
        else:
            raise SystemExit(f"{name}: UNKNOWN instruction hw1 {hw1} at +0x{i:02X}")
    return out


# 🛑 THE FINAL ARTIFACT HASHES.  V104 was ACCEPTED at these values and they are FROZEN.  This file
# is documentation as well as a builder: a docstring edit must NOT move a byte.  Any future change
# that alters the output trips the assertion at the end of build().
EXPECT_IMG_SHA = "b556a0b16da5ac2ad850cae036e5533a4de347e84f2c907f37653cc0f7201a03"
EXPECT_RWD_SHA = "41e707121cf86d8fc8d8c27f98fa722632858466ebbce952a4adcf7234fd4fa2"

TOKEN = "V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4"
BIN_OUT = str(plain_image_path(f"_v104_{TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V104-{TOKEN}-0x{START:X}-0x{END:X}.rwd")

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  Carried from V103's ledger.  0x3AA96 and 0xC6446 are REMOVED --
# they are now EDIT TARGETS (E2/E3), not frozen cells.
# =================================================================================================
FROZEN = {
    0xC407E: (2, 511, "HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC40BC: (2, 300, "Coulomb ramp knee (V99's lever, carried)"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- matches 0xC63AC=102/1024"),
    0xC40D2: (2, 204, "K1 -- HELD AT 204. Instrumented by the cave's b5, NOT dosed. Carried."),
    0xC40D4: (2, 573, "command-branch EMA -- VIRGIN"),
    0xC40D6: (2, 246, "accel/inertia EMA -- VIRGIN"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP"),
    0xC63AC: (2, 102, "accumulator pole -- Honda's own value (V99's revert)"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN (the cave's b5 operand B)"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane (the cave's b7 source)"),
    0xC63AE: (2, 1024, "Stage-2 LERP index scale"),
    0xC6200: (2, 8192, "PID reference clamp -- DEAD (V100 measured 0.000000)"),
    0xC6444: (2, 512, "r26's arm -- the DECOUPLER. Deliberately stock: NOT Lever B's arm"),
    0xC6468: (2, 2639, "shared model gain"),
    0xC646C: (2, 891, "shared sensor scale -- Honda's 891 (decoupled by V57)"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
    0xC62EA: (2, 0, "steer-to-zero, V53, on the car"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through"),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN"),
    0xC6B12: (2, 98, "PID Ki -- VIRGIN"),
    0xC6B26: (2, 256, "PID Kp -- VIRGIN"),
    0xC6194: (2, 3, "the REAL LKAS slew limiter -- DEAD (0xC4118 partition)"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- V62's fix, half. Carried"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- carried"),
    0xC64A1: (1, 1, "READ-ONLY"),
    0xC63D2: (2, 6, "FUN_00036682 pole"),
    0xC640A: (2, 0xE000, "FALLBACK-2 STOCK"),
    0xC640C: (2, 0xF333, "FALLBACK-1 STOCK"),
    0xC6CD0: (2, 5346, "🛑 LKAS GAIN -- 6x, THE OPERATOR'S RULING. DOES NOT MOVE in V104."),
    0xC61B2: (2, 3072, "fwd-path clamp -- tracks the gain, frozen with it"),
    0xC61B4: (2, 3072, "arb output clamp -- tracks the gain, frozen with it"),
    0xC64FA: (1, 5, "🛑 SHARED OSCILLATION-DETECTOR CEIL -- ~18 in-code readers. V103 armed the "
                    "biquad by patching the COMPARISON privately at 0x35A12, NOT by raising this "
                    "widely-shared cell. V104 does not touch it either."),
    0xC649B: (1, 1, "🛑 V103's BIQUAD ARM -- must ALREADY be 1 on the base, or E1 doses a "
                    "DISARMED filter and the whole build is inert"),
}

# =================================================================================================
# THE FRICTION DOSE FAMILY.  Car is TVCA4: 24/25 = MANUAL, 26/27 = ENGAGED.  Carried from V103.
# =================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
REC_X_OFF, REC_Y_OFF = 0x02, 0x08
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)

# =================================================================================================
# THE EME AUDIT -- every V25 -> V37 EME-prevention fix, re-run against the BUILT image.
# =================================================================================================
EME_RANGES = [
    (0xC64B4, 0xC64BA, "V36/V37", "STEER_STATUS debounce disable + DTC-0x49 (0xC64B8 -> 0xFF)"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals maxed to 0xFFFF"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f (and -1.0f -> -5.0f)"),
    (0xC65C6, 0xC65D0, "V31->V38", "soft-EME boost floor FLOAT 0.0f/1.5f/2.0f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC64DE, 0xC64E0, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384, bank 1"),
    (0xE5180, 0xE5260, "V38", "same taper surface, bank 2"),
]
EME_SCALARS = [
    (0xC64B8, 1, 0xFF, 0x70, "DTC-0x49 counter-B gate -- 112 -> 0xFF, can never increment (V37)"),
    (0xC61C0, 2, 0xFFFF, 1600, "debounce cal 0 (V36)"),
    (0xC61C2, 2, 0xFFFF, 896, "debounce cal 1 (V36)"),
    (0xC61C4, 2, 0xFFFF, 1280, "debounce cal 2 (V36)"),
    (0xC64DE, 1, 27, 17, "re-engage ramp (pre-V38)"),
    (0xC674E, 2, 5120, 1024, "soft-EME boost floor INT -- THE AUTHORITY FLOOR"),
]
EME_FLOATS = [
    (0xC6598, 5.0, 1.0, "soft-EME boost floor FLOAT #1 (V29->V38)"),
    (0xC659C, 5.0, 1.0, "soft-EME boost floor FLOAT #2 (V29->V38)"),
    (0xC65AC, -5.0, -1.0, "soft-EME boost floor FLOAT #3, negative rail (V29->V38)"),
    (0xC65B0, -5.0, -1.0, "soft-EME boost floor FLOAT #4, negative rail (V29->V38)"),
    (0xC65C4, 5.0, 0.0, "soft-EME boost floor FLOAT #5 (V31->V38)"),
    (0xC65C8, 5.0, 1.5, "soft-EME boost floor FLOAT #6 (V31->V38)"),
    (0xC65CC, 5.0, 2.0, "soft-EME boost floor FLOAT #7 (V31->V38)"),
]

# the non-stock ledger vs HONDA STOCK.  Carried from V103 + E1/E2/E3's three new ranges.
VS_STOCK = [
    (0x13109, 0x1310A, "pre-V38", "part-number '-' -> ','"),
    (0x14120, 0x14121, "pre-V38", "part-number 2nd copy"),
    (0x2A1F0, 0x2A1F2, "V57", "forward-LKAS reader repointed tp+0x746C -> tp+0x7CD0"),
    (0x35A06, 0x35A0A, "V103", "biquad arm source, reversal-counter -> gp-0x6806 engagement flag"),
    (0x35A12, 0x35A14, "V103", "biquad arm: cmp r12,r9 -> cmp r0,r9"),
    (0x35A18, 0x35A1C, "V103", "biquad arm: setfnc -> setfne (unsigned>= -> !=0)"),
    (0x3AA96, 0x3AA97, "V104", "E2 LEVER B gate: ld.bu -0x683c[gp],r15 -> -0x6806[gp],r15"),
    (0x454FE, 0x454FF, "V42", "state-4 governor bne -> br (INERT, carried)"),
    (0x55C0E, 0x55C12, "V53+", "THE CAVE HOOK -- jarl 0xC4B34,lp"),
    (0x55DF2, 0x55DF4, "V104", "E4a CAN 427 source gp-0x6c18 (stock) -> gp-0x6b86 (biquad lane)"),
    (0x55E10, 0x55E11, "V104", "E4b CAN 427 scaler sar 0x3 (stock) -> sar 0x4"),
    (0xC40BC, 0xC40BE, "V99", "Coulomb ramp knee 600 -> 300"),
    (0xC40D2, 0xC40D3, "V89", "K1 Coulomb gain 102 -> 204 -- HELD, instrumented not dosed"),
    (0xC4B34, 0xC4B34 + CAVE_LEN, "CAVE", "the code cave -- V103's 164 B carried byte-identical "
                                          "+ E5's 44 B comparator = 208 B"),
    (0xC60B4, 0xC60B8, "V104", "E1 biquad input gain c4 0.81731f -> 1.51202f (x1.850000)"),
    (0xC61B2, 0xC61B6, "V101", "LKAS forward-path clamps -- FROZEN at the tracking value"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0"),
    (0xC6446, 0xC6448, "V104", "E3 LEVER B arm 512 -> 5244"),
    (0xC649B, 0xC649C, "V103", "arms Honda's dormant biquad, 0 -> 1"),
    (0xC64B4, 0xC64B9, "V36/V37", "STEER_STATUS debounce + DTC-0x49"),
    (0xC64DE, 0xC64DF, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor FLOAT 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC6CD0, 0xC6CD2, "V101", "the PRIVATE forward-LKAS gain -- FROZEN at 6x"),
    (0xD7A5C, 0xD7A62, "V92", "friction dose x1.5 engaged mode 26 -- MEASURED INERT"),
    (0xD7A6C, 0xD7A72, "V92", "friction dose x1.5 engaged mode 27 -- MEASURED INERT"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank"),
]

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def f32(buf, a):
    return struct.unpack_from("<f", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rdw(buf, a, w):
    return u16(buf, a) if w == 2 else (buf[a] if w == 1 else rd(buf, a, w))


def rec_addr(buf, mode):
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


def rec_x(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_X_OFF)


# =================================================================================================
# THE PLANT AND THE PACKER, mirrored from the decompiled arithmetic.  Integer where the firmware
# is integer; float32-read constants where the firmware is float.
# =================================================================================================
def biquad_H(w, a1, a2, b1, c4):
    """|H(e^jw)| for w[n] = c4*u[n] - a1*w[n-1] - a2*w[n-2] ; y[n] = w[n] + b1*w[n-1] + w[n-2]."""
    z = cmath.exp(-1j * w)
    return abs(c4 * (1.0 + b1 * z + z * z) / (1.0 + a1 * z + a2 * z * z))


def packer_field(x, sar):
    """`FUN_00055d80`'s 427 packer, EXACTLY as decompiled:
         FUN_00049a90( (int)((abs(x) & 0xffff) * 5) >> sar, 0, 0x3ff )
       -- FUN_00049a5a is abs(), FUN_00049a90 is clamp(v,lo,hi), and the *5 is in the decompile."""
    return max(0, min(E4_FIELD_MAX, ((abs(x) & 0xFFFF) * E4_PACK_MUL) >> sar))


def assert_frozen(buf, label):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


def assert_friction_family(buf, label):
    print(f"\n    friction dose family 0x{FRICTION_PTR_ARRAY:05X} ({label}) -- "
          f"CAR IS TVCA4: 24/25 MANUAL, 26/27 ENGAGED")
    bad = []
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(buf, m)
        want = FRICTION_Y_STOCK if m in MANUAL_MODES else FRICTION_Y_V92
        got = rec_y(buf, m)
        role = "MANUAL " if m in MANUAL_MODES else "ENGAGED"
        if got != want:
            bad.append(m)
        print(f"      {OK if got == want else BAD} mode {m:2d} {role}  record 0x{ra:05X}  "
              f"Y@0x{ra + REC_Y_OFF:05X} = {got}  X = {rec_x(buf, m)}")
    check(not bad, f"{label}: all 4 friction records at their expected Y "
                   f"(manual STOCK, engaged V92 x1.5 -- MEASURED INERT, carried unchanged)")


def eme_audit(img, base, stock, label):
    print(f"\n  ---- EME AUDIT ({label}) ----")
    print(f"    {'range':<21} {'B':>4} {'!=stock':>8}  {'==base':>7}  origin      what")
    allok = True
    for lo, hi, origin, what in EME_RANGES:
        same_as_base = bytes(img[lo:hi]) == bytes(base[lo:hi])
        n_vs_stock = sum(1 for i in range(lo, hi) if img[i] != stock[i])
        allok &= same_as_base and n_vs_stock > 0
        print(f"    {'0x%05X-0x%05X' % (lo, hi - 1):<21} {hi - lo:>4} {n_vs_stock:>8}  "
              f"{'YES' if same_as_base else 'NO!':>7}  {origin:<10}  {what}")
    check(allok, f"{label}: all {len(EME_RANGES)} EME ranges carried "
                 f"(identical to the audited V103 base AND non-stock)")

    print(f"\n    scalar cells:")
    bad = []
    for a, w, want, stk, why in EME_SCALARS:
        got = rdw(img, a, w)
        print(f"      {OK if got == want else BAD} 0x{a:05X}  = {got:<7} (stock {stk:<7})  {why}")
        if got != want:
            bad.append(a)
    check(not bad, f"{label}: all {len(EME_SCALARS)} EME scalar cells at their fixed values")

    print(f"\n    float cells:")
    bad = []
    for a, want, stk, why in EME_FLOATS:
        got = f32(img, a)
        print(f"      {OK if got == want else BAD} 0x{a:05X}  = {got:<7} (stock {stk:<7})  {why}")
        if got != want:
            bad.append(a)
    check(not bad, f"{label}: all {len(EME_FLOATS)} EME float cells at their fixed values")

    floor, clamp = u16(img, 0xC674E), u16(img, 0xC61B2)
    check(floor == 5120 and floor > clamp,
          f"{label}: soft-EME boost floor INT = {floor} > {clamp} (the fwd-path clamp) "
          f"=> authority sufficient")
    check(u16(img, 0xC407E) == 511,
          f"{label}: hard-fault interlock 0xC407E = 511 (Honda's own, one under its 512 trip)")
    check(u16(img, 0xC4080) == 0, f"{label}: 0xC4080 (K0) = 0 -- NEVER-RAISE, untouched")


def build():
    print("=" * 102)
    print("  V104 -- biquad gain c4 x1.85 (E1) + LEVER B restored (E2/E3) + CAN 427 -> gp-0x6b86")
    print("          with the shift RESIZED to sar 4 (E4).  Cave carried BYTE-IDENTICAL from V103.")
    print("=" * 102)

    # ==============================================================================================
    print("\n  [1] THE BASE -- V103 (the flown image)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V103, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    # ==============================================================================================
    print("\n  [2] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    assert_frozen(base, "V103 base")
    assert_friction_family(base, "V103 base")

    # ==============================================================================================
    print("\n  [3] E1 -- PRE-EDIT: the biquad, its coefficients and its ARM, read off the base")
    check(rd(base, E1_ADDR, 4) == E1_PRE,
          f"0x{E1_ADDR:05X} = {E1_PRE.hex()} = c4 = {f32(base, E1_ADDR):.8f}f")
    check(rd(base, BQ_A1, 12) == BQ_COEFF_BYTES,
          f"0x{BQ_A1:05X}/{BQ_A2:05X}/{BQ_B1:05X} = {BQ_COEFF_BYTES.hex()} -- a1/a2/b1, "
          f"the notch's OWN SHAPE, must not move")
    check(base[BQ_ARM_CAL] == 1,
          f"0x{BQ_ARM_CAL:05X} = 1 -- V103's arm is ALREADY SET on the base, so E1 doses a "
          f"filter that actually runs (a 0 here would make the whole build inert)")
    check(rd(base, BQ_A1, 12) == rd(stock, BQ_A1, 12) and rd(base, E1_ADDR, 4) == rd(stock, E1_ADDR, 4),
          "all four biquad coefficients are HONDA STOCK on the base -- E1 is the first build "
          "ever to move one")
    for a, want, why in V103_PARTA:
        check(rd(base, a, len(want)) == want, f"V103's arm edit 0x{a:05X} = {want.hex()} -- {why}")

    print("\n  [3b] E1 -- THE PLANT, evaluated from the bytes (not from the spec)")
    a1, a2, b1 = f32(base, BQ_A1), f32(base, BQ_A2), f32(base, BQ_B1)
    c4_old = struct.unpack("<f", E1_PRE)[0]
    c4_new = struct.unpack("<f", E1_POST)[0]
    check(abs(c4_new / c4_old - E1_K) < 1e-6,
          f"  c4 {c4_old:.8f} -> {c4_new:.8f} = x{c4_new / c4_old:.6f} (target x{E1_K})")
    # zeros of 1 + b1 z^-1 + z^-2  ->  z^2 + b1 z + 1
    zr = abs(complex(-b1 / 2, math.sqrt(max(0.0, 1 - (b1 / 2) ** 2))))
    pr = math.sqrt(a2)
    check(abs(zr - 1.0) < 1e-5,
          f"  zeros lie ON the unit circle (|z| = {zr:.7f}) => the null is ALREADY infinitely "
          f"deep at stock; c4 CANNOT deepen it, only scale the whole response")
    check(pr < 1.0,
          f"  poles |p| = {pr:.7f} < 1 => the filter is STABLE, and well damped (no resonant peak)")
    N = 20000
    ws = [k * math.pi / N for k in range(1, N + 1)]
    h_old = [biquad_H(w, a1, a2, b1, c4_old) for w in ws]
    h_new = [biquad_H(w, a1, a2, b1, c4_new) for w in ws]
    hmax_old, hmax_new = max(h_old), max(h_new)
    n_gt1 = sum(1 for v in h_new if v >= 1.0)
    print(f"      |H| stock : DC {h_old[0]:.6f}  Nyq {h_old[-1]:.6f}  MAX {hmax_old:.6f}  "
          f"MIN {min(h_old):.3e}")
    print(f"      |H| V104  : DC {h_new[0]:.6f}  Nyq {h_new[-1]:.6f}  MAX {hmax_new:.6f}  "
          f"MIN {min(h_new):.3e}")
    check(abs(hmax_new / hmax_old - E1_K) < 1e-5,
          f"  max|H| scales EXACTLY x{hmax_new / hmax_old:.6f} -- c4 is a PURE SCALAR INPUT GAIN, "
          f"confirmed numerically, not assumed")
    check(hmax_new > 1.0 and n_gt1 * 100.0 / N > 90.0,
          f"  🛑 STATED, NOT HIDDEN: |H_new| >= 1 on {n_gt1 * 100.0 / N:.1f}% of the Nyquist axis "
          f"(peak {hmax_new:.4f} at DC). E1 is a BROADBAND x1.85 RAISE with a narrow notch in it, "
          f"NOT a notch-depth change. See the docstring for what this does to a comparator's duty.")

    # ==============================================================================================
    print("\n  [4] E2/E3 -- LEVER B: PRE-EDIT.  Both cells must read HONDA STOCK on this base")
    check(rd(base, E2_INSN_ADDR, 4) == V67.REPOINT_FROM,
          f"0x{E2_INSN_ADDR:05X} = {V67.REPOINT_FROM.hex()} = ld.bu -0x683c[gp],r15 -- "
          f"Honda's DEAD gate, i.e. Lever B is OFF on V103 (V101/V102/V103 all lost it)")
    check(u16(base, E3_ADDR) == V67.ARM_STOCK,
          f"0x{E3_ADDR:05X} = {V67.ARM_STOCK} -- Honda stock arm, Lever B OFF")
    for t in V67.REPOINT_TWINS:
        check(rd(base, t, 4) == V67.REPOINT_TO,
              f"  the 4 bytes the repoint WRITES ({V67.REPOINT_TO.hex()}) already exist verbatim "
              f"at 0x{t:05X} -- zero encoding risk")
    print("\n  [4b] E2 -- FIELD-LEVEL DECODE, re-derived from the bits (not diffed against V88)")
    check(V67.REPOINT_FROM[:2] == V67.REPOINT_TO[:2] == bytes.fromhex("847f"),
          f"  hw1 {V67.REPOINT_FROM[:2].hex()} is IDENTICAL on both sides -- same opcode family "
          f"(ld.bu/gp), same destination register (r15). ONLY the displacement moves.")
    for raw, want, lbl in ((V67.REPOINT_FROM, -0x683C, "OLD"), (V67.REPOINT_TO, -0x6806, "NEW")):
        hw2 = struct.unpack_from("<H", raw, 2)[0]
        disp = struct.unpack("<h", struct.pack("<H", hw2 & 0xFFFE))[0]
        check(disp == want and (hw2 & 1) == 1,
              f"  {lbl}: hw2 {hw2:04x}, ld.bu `disp|1` form (bit0 = 1), displacement {disp} "
              f"(-0x{-want:04X})")
    check(len(E2_PRE) == 1 and E2_PRE != E2_POST and V67.REPOINT_FROM[3] == V67.REPOINT_TO[3],
          f"  exactly ONE byte moves: 0x{E2_ADDR:05X} {E2_PRE.hex()} -> {E2_POST.hex()} "
          f"(hw2's LOW half; the high byte 0x{V67.REPOINT_FROM[3]:02X} is unchanged)")
    check(V67.ARM_NEW == 5244 and V67.ARM_NEW == 2 * V67.GRIND1_LERP,
          f"  E3 arm {V67.ARM_NEW} = 2.000x the LERP ({V67.GRIND1_LERP}) at grind #1's measured "
          f"operating point -- V67's own derivation, recomputed here, never hard-coded")
    check(V67.FIRST_JARL_AFTER > V67.LP_CHAIN[-1][0],
          f"  the `lp` chain is intact: the first jarl in FUN_0003aa2c (0x{V67.FIRST_JARL_AFTER:05X}) "
          f"is AFTER both consumers -- lp is safe as the gate's carrier")
    for a, want, why in V67.LP_CHAIN:
        check(rd(base, a, len(want)) == want, f"  lp chain 0x{a:05X} = {want.hex()} -- {why}")

    # ==============================================================================================
    print("\n  [5] E4 -- PRE-EDIT: the 427 packer, read off the base")
    check(rd(base, E4_LOAD_ADDR, 4) == E4_LOAD_HW1 + E4A_PRE,
          f"0x{E4_LOAD_ADDR:05X} = {(E4_LOAD_HW1 + E4A_PRE).hex()} = ld.h -0x6b4c[gp],r6 "
          f"(V102's source)")
    check(rd(base, E4B_ADDR, 2) == E4B_PRE + bytes([E4_SAR_BYTE1]),
          f"0x{E4B_ADDR:05X} = {(E4B_PRE + bytes([E4_SAR_BYTE1])).hex()} = sar 0x{E4_SAR_OLD:x},r6")
    check(rd(base, E4_MASK_ADDR, 4) == E4_MASK_BYTES,
          f"0x{E4_MASK_ADDR:05X} = {E4_MASK_BYTES.hex()} = movea 0x03FF,r0,r8 -- the 10-bit field "
          f"literal is MATERIALISED in Honda's own packer, so 1023 is read from the image")
    print("\n  [5b] E4 -- THE PACKER MODEL, validated against TWO FLIGHTS before it is used")
    for x, sar, want, why in PACKER_ANCHORS:
        got = packer_field(x, sar)
        check(got == want, f"  ({x}*5)>>{sar} = {got} = {want} observed -- {why}")
    check(packer_field(1498, 6) != (1498 >> 6),
          f"  the packer is NOT |x|>>sar (that would give {1498 >> 6}, not 117) -- the *5 is real")

    print("\n  [5c] E4 -- GATE 3: SIZE AGAINST gp-0x6b86's OWN REACHABLE OUTPUT AT k = 1.85")
    reach_raw = hmax_new * IN_MAX + PED_MAX
    reach = min(BQ_OUT_CLAMP, int(reach_raw))
    print(f"      |gp-0x6b82| engaged max {IN_MAX}  (p50 {IN_P50}, p95 {IN_P95}, p99 {IN_P99})")
    print(f"      |gp-0x6b7e| engaged max {PED_MAX} (p50 {PED_P50}, p95 {PED_P95})  the pedestal")
    print(f"      max|H_new|  {hmax_new:.6f}")
    print(f"      => |gp-0x6b86| <= min({BQ_OUT_CLAMP}, {hmax_new:.4f}*{IN_MAX} + {PED_MAX}) "
          f"= min({BQ_OUT_CLAMP}, {reach_raw:.0f}) = {reach} counts")
    check(reach < BQ_OUT_CLAMP,
          f"  the +-{BQ_OUT_CLAMP} store clamp is NOT binding "
          f"({BQ_OUT_CLAMP / reach:.1f}x above the reachable value) -- so sizing against IT would "
          f"be the V96 error; we size against {reach}")
    print(f"\n      {'sar':>4}  {'field at ' + str(reach):>16}  {'% of 1023':>10}  "
          f"{'counts/LSB':>11}  verdict")
    best = None
    for sar in (3, 4, 5, 6, 7):
        raw = (reach * E4_PACK_MUL) >> sar
        ovf = raw > E4_FIELD_MAX
        if not ovf and (best is None or raw > best[1]):
            best = (sar, raw)
        print(f"      {sar:>4}  {raw:>16}  {100.0 * raw / E4_FIELD_MAX:>9.1f}%  "
              f"{2 ** sar / E4_PACK_MUL:>11.2f}  {'OVERFLOW' if ovf else 'ok'}"
              f"{'   <-- V103 carries this byte' if sar == E4_SAR_OLD else ''}")
    check(best is not None and best[0] == E4_SAR_NEW,
          f"  sar {E4_SAR_NEW} is the LARGEST field that cannot overflow "
          f"({best[1]}/{E4_FIELD_MAX} = {100.0 * best[1] / E4_FIELD_MAX:.1f}%), "
          f"at {2 ** E4_SAR_NEW / E4_PACK_MUL:.2f} counts per LSB")
    check((reach * E4_PACK_MUL) >> (E4_SAR_NEW - 1) > E4_FIELD_MAX,
          f"  sar {E4_SAR_NEW - 1} WOULD overflow "
          f"({(reach * E4_PACK_MUL) >> (E4_SAR_NEW - 1)}/{E4_FIELD_MAX} = "
          f"{((reach * E4_PACK_MUL) >> (E4_SAR_NEW - 1)) / E4_FIELD_MAX:.2f}x) -- rejected")
    under = ((reach * E4_PACK_MUL) >> E4_SAR_NEW) / float((reach * E4_PACK_MUL) >> E4_SAR_OLD)
    check(under > 3.5,
          f"  keeping V103's sar {E4_SAR_OLD} would UNDER-USE the channel {under:.1f}x -- "
          f"exactly the V96 defect the design law forbids")
    sat_onset = -(-(E4_FIELD_MAX * (2 ** E4_SAR_NEW)) // E4_PACK_MUL)
    check(sat_onset > reach,
          f"  saturation would begin at {sat_onset} counts = {sat_onset / reach:.2f}x the "
          f"reachable bound -- headroom STATED, not assumed away")
    print(f"\n      operating points at sar {E4_SAR_NEW} (worst-case |H| = {hmax_new:.4f}):")
    for p, lbl in ((IN_P50, "p50"), (IN_P95, "p95"), (IN_P99, "p99"), (IN_MAX, "max")):
        v = int(hmax_new * p)
        print(f"        |gp-0x6b82| {lbl:>3} = {p:4d}  ->  |gp-0x6b86| <= {v:5d}  ->  "
              f"field {packer_field(v, E4_SAR_NEW):4d}   (at sar {E4_SAR_OLD} it would be "
              f"{packer_field(v, E4_SAR_OLD):4d})")

    print("\n  [5d] E4 -- ENCODING, derived from the bits and cross-checked against the image")
    disp_new = struct.unpack("<h", E4A_POST)[0]
    disp_old = struct.unpack("<h", E4A_PRE)[0]
    check(disp_new == -0x6B86 and disp_old == -0x6B4C and (disp_new & 1) == 0,
          f"  ld.h displacement: {disp_old} (-0x6B4C) -> {disp_new} (-0x6B86); bit0 = 0, the "
          f"`ld.h` halfword-aligned form (unlike ld.bu's `disp|1`)")
    check(E4B_POST[0] & 0xF0 == E4B_PRE[0] & 0xF0 and (E4B_POST[0] & 0x1F) == E4_SAR_NEW
          and (E4B_PRE[0] & 0x1F) == E4_SAR_OLD,
          f"  sar imm5 is the low nibble of byte0: {E4B_PRE[0]:02x} -> {E4B_POST[0]:02x} "
          f"= sar 0x{E4_SAR_OLD:x} -> sar 0x{E4_SAR_NEW:x}; byte1 0x{E4_SAR_BYTE1:02X} unchanged")
    n_sar_twins = sum(1 for i in range(START, END)
                      if base[i:i + 2] == E4B_POST + bytes([E4_SAR_BYTE1]))
    check(n_sar_twins > 0,
          f"  `sar 0x{E4_SAR_NEW:x},r6` = {(E4B_POST + bytes([E4_SAR_BYTE1])).hex()} already "
          f"appears {n_sar_twins}x in this image -- and 0x{E4B_ADDR:05X} itself carried `a4` on V92")

    # ==============================================================================================
    print("\n  [5e] THE CAVE -- UNTOUCHED.  E5 was designed, priced at 44 B, and DROPPED")
    V103_CAVE = rd(base, CAVE_BASE, V103_CAVE_LEN)
    check(all(b == 0xFF for b in base[CAVE_BASE + V103_CAVE_LEN:CAVE_FREE_END]),
          f"cave tail is virgin 0xFF to 0x{CAVE_FREE_END:05X} "
          f"({CAVE_FREE_END - CAVE_BASE - V103_CAVE_LEN} B free -- unchanged from V103)")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp -- unchanged")
    check(CAVE_LEN == V103_CAVE_LEN == 164,
          f"cave stays {CAVE_LEN} B -- V104 adds NO cave code, so no hot-path-adjacent risk")
    ret_at = V103_CAVE.rfind(bytes.fromhex("7f00"))
    check(ret_at == V103_CAVE_LEN - 2,
          f"  the cave's ONLY exit `jmp [lp]` is at +0x{ret_at:02X}, the last 2 B -- this is why "
          f"E5's first cut (APPENDED at +0x{E5_DROPPED_OFF + E5_DROPPED_LEN:02X}) would have been "
          f"DEAD CODE, and why any future append must be SPLICED at +0x{E5_DROPPED_OFF:02X}")

    print("\n  [5f] CAN 0x14A byte4 -- HONDA KEEPS BITS 2:0.  Free channel is 7:3, NOT {2,1,0}")
    cleared = set()
    for m, bits, lbl in ((0x00BF, {6}, "PASS1 b6"), (0x00DF, {5}, "PASS2 b5"),
                         (0x0067, {7, 4, 3}, "PASS3 b7+b4+b3")):
        got = {b for b in range(8) if not (m >> b) & 1}
        check(got == bits and (m & 0x07) == 0x07,
              f"  {lbl:<16} andi 0x{m:02X} clears {sorted(bits, reverse=True)} and PRESERVES "
              f"Honda's bits 2:0")
        cleared |= bits
    check(cleared == set(BIT_OWNERS) == {7, 6, 5, 4, 3},
          f"the cave owns exactly bits {sorted(cleared, reverse=True)} -- V103's five, all of them")
    check(set(range(8)) - cleared == HONDA_BITS_KEPT,
          f"  Honda keeps bits {sorted(HONDA_BITS_KEPT, reverse=True)} -- gp-0x6799 (always), "
          f"gp-0x679b and gp-0x679a (when gp-0x67fa != 8), all written in FUN_00055a98 BEFORE the "
          f"hook. V104 preserves all three; E5's `andi 0xfe` would have destroyed gp-0x679a.")


    # ==============================================================================================
    code = bytearray(base)
    attributed = set()

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
        print(f"    0x{addr:05X}  {len(post):2d} B   {label}")

    print(f"\n  [6] THE EDITS -- five sites, all cal-only or in-place. NO CAVE CHANGE.")
    apply(E1_ADDR, E1_PRE, E1_POST,
          f"E1   BIQUAD GAIN  0xC60B4  c4 {c4_old:.5f}f -> {c4_new:.5f}f  (x{E1_K})")
    apply(E2_ADDR, E2_PRE, E2_POST,
          f"E2   LEVER B GATE 0x3AA96  ld.bu -0x683c[gp],r15 -> -0x6806[gp],r15")
    apply(E3_ADDR, E3_PRE, E3_POST,
          f"E3   LEVER B ARM  0xC6446  {V67.ARM_STOCK} -> {V67.ARM_NEW}")
    apply(E4A_ADDR, E4A_PRE, E4A_POST,
          f"E4a  427 SOURCE   0x55DF2  gp-0x6b4c -> gp-0x6b86 (the biquad lane)")
    apply(E4B_ADDR, E4B_PRE, E4B_POST,
          f"E4b  427 SCALER   0x55E10  sar 0x{E4_SAR_OLD:x} -> sar 0x{E4_SAR_NEW:x}")
    check(len(attributed) == 10,
          f"exactly {len(attributed)} bytes written: 4 (E1) + 1 (E2) + 2 (E3) + 2 (E4a) + 1 (E4b) "
          f"-- and ZERO in the cave")

    # ==============================================================================================
    print("\n  [7] POST-EDIT VERIFICATION -- read back out of the image being built")
    check(rd(code, E1_ADDR, 4) == E1_POST and abs(f32(code, E1_ADDR) - c4_new) < 1e-9,
          f"E1: 0x{E1_ADDR:05X} reads {f32(code, E1_ADDR):.8f}f")
    check(rd(code, E2_INSN_ADDR, 4) == V67.REPOINT_TO,
          f"E2: 0x{E2_INSN_ADDR:05X} reads {V67.REPOINT_TO.hex()} = ld.bu -0x6806[gp],r15")
    check(u16(code, E3_ADDR) == V67.ARM_NEW, f"E3: 0x{E3_ADDR:05X} reads {V67.ARM_NEW}")
    check(rd(code, E4_LOAD_ADDR, 4) == E4_LOAD_HW1 + E4A_POST,
          f"E4a: 0x{E4_LOAD_ADDR:05X} reads {(E4_LOAD_HW1 + E4A_POST).hex()} = ld.h -0x6b86[gp],r6")
    check(rd(code, E4B_ADDR, 2) == E4B_POST + bytes([E4_SAR_BYTE1]),
          f"E4b: 0x{E4B_ADDR:05X} reads {(E4B_POST + bytes([E4_SAR_BYTE1])).hex()} = sar 0x4,r6")

    check(rd(code, CAVE_BASE, CAVE_LEN) == V103_CAVE,
          f"E5 DROPPED: the {CAVE_LEN}-byte cave is BYTE-IDENTICAL to V103's")

    print("\n  [7b] GATE 1 -- ZERO new RAM, ZERO new code region, ZERO cave change")
    for lo, hi, lbl in ((V103_PASS1[0], V103_PASS1[1], "PASS1 b6"),
                        (V103_PASS2[0], V103_PASS2[1], "PASS2 b5"),
                        (V103_PASS3[0], V103_PASS3[1], "PASS3 b7+b4+b3"),
                        (V103_BYTE7[0], V103_BYTE7[1], "BYTE7 identity"),
                        (V103_RET[0], V103_RET[1], "RET")):
        check(rd(code, CAVE_BASE + lo, hi - lo) == V103_CAVE[lo:hi],
              f"  {lbl:<16} +0x{lo:02X}..0x{hi - 1:02X} byte-identical to V103's")
    check(not any(CAVE_BASE <= a < CAVE_FREE_END for a in attributed),
          "no edit lands anywhere inside the cave region")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"the cave tail is still virgin 0xFF to 0x{CAVE_FREE_END:05X} "
          f"({CAVE_FREE_END - CAVE_BASE - CAVE_LEN} B free)")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"the hook 0x{HOOK_ADDR:05X} is unchanged")
    n_b4 = sum(1 for i in range(len(V103_CAVE) - 3) if V103_CAVE[i:i + 4] == ST_B4_INSN)
    n_b7 = sum(1 for i in range(len(V103_CAVE) - 3) if V103_CAVE[i:i + 4] == ST_B7_INSN)
    check((n_b4, n_b7) == (3, 1),
          f"stores: {n_b4}x gp-0x1514 + {n_b7}x gp-0x1511 -- V103's set exactly, no new RAM")
    for a, want, why in V103_PARTA:
        check(rd(code, a, len(want)) == want, f"V103's arm edit 0x{a:05X} still {want.hex()}")
    check(rd(code, BQ_A1, 12) == BQ_COEFF_BYTES,
          "a1/a2/b1 UNCHANGED -- the notch's centre frequency and shape are untouched; only its "
          "scalar input gain moved")
    check(all(not (a <= x < a + 4) for a in (0x35A2C, 0x35A4C, 0x35A64, 0x35A6A)
              for x in attributed),
          f"the four gp-0x{BQ_STATE_X1:04X}/gp-0x{BQ_STATE_X2:04X} biquad-state load/store "
          f"instructions are untouched -- E1 changes a COEFFICIENT, never the state access")
    check(BQ_FUNC_LO <= 0x35A06 < BQ_FUNC_HI,
          f"V103's arm edits remain inside FUN_000352b4 [0x{BQ_FUNC_LO:05X},0x{BQ_FUNC_HI:05X})")
    check(code[0xC64FA] == 5, "0xC64FA (the shared oscillation-detector ceil) still 5")

    # ==============================================================================================
    print("\n  [8] FROZEN + the friction dose family, AFTER the edit")
    assert_frozen(code, "built image (pre-CRC)")
    assert_friction_family(code, "built image (pre-CRC)")

    print("\n  [8b] Everything outside the five edit sites is bit-for-bit V103's")
    diffs = [i for i in range(START, END) if code[i] != base[i] and i not in attributed]
    check(not diffs, f"ZERO bytes differ from the V103 base outside the six named edits "
                     f"-- the control law is otherwise UNCHANGED from V103")

    # ==============================================================================================
    eme_audit(code, base, stock, "built image, pre-CRC")

    # ==============================================================================================
    print("\n  [9] CRC RECOMPUTATION -- reusing the existing owning_block/walk_all_blocks machinery")
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    check(len(blocks) == 2,
          f"the six edits span exactly {len(blocks)} CRC blocks (expected 2: the main app block "
          f"0xC4FFC for E2/E4a/E4b/E5, and the cal block 0xC6FFC for E1/E3) -- "
          f"{[hex(b[1]) for b in blocks]}")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit on trailer 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        n_in = len([a for a in touched if blk[0] <= a < blk[1]])
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old_crc:08X} -> 0x{new_crc:08X}  "
              f"{n_in} of {len(touched)} edited bytes  (trailer 0x{blk[1]:06X})")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    # ==============================================================================================
    print("\n  [10] FULL BYTE DIFF vs HONDA STOCK")
    sruns = [i for i in range(START, END) if code[i] != stock[i]]
    scrc = {b + k for b in (0xC4FFC, 0xC5FFC, 0xC6FFC, 0xCCFFC) for k in range(4)}
    scrc |= {b + 0xFFC + k for b in range(0xCD000, 0x100000, 0x1000) for k in range(4)}
    sattr = set()
    for lo, hi, bld, what in VS_STOCK:
        sattr |= {i for i in sruns if lo <= i < hi}
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"       {len(sruns)} bytes differ from STOCK total, {len(sattr)} attributed, "
          f"{len(set(sruns) & scrc)} CRC")
    check(not sun, "ZERO unattributed bytes vs stock"
                   + ("" if not sun else "  -- " + str([hex(x) for x in sun[:16]])))

    print("\n  [10b] FULL BYTE DIFF vs THE V103 BASE -- what THIS build changed, run by run")
    bruns = [i for i in range(START, END) if code[i] != base[i]]
    runs = []
    for i in bruns:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    named = [(E1_ADDR, 4, "E1 biquad gain c4 x1.85"), (E2_ADDR, 1, "E2 LEVER B gate"),
             (E3_ADDR, 2, "E3 LEVER B arm"), (E4A_ADDR, 2, "E4a 427 source -> gp-0x6b86"),
             (E4B_ADDR, 1, "E4b 427 scaler sar 6 -> 4")]
    unnamed = []
    for lo, hi in runs:
        span = set(range(lo, hi))
        if (lo & 0xFFF) >= 0xFFC:
            tag = "CRC trailer"
        else:
            hits = [w for a, n, w in named if span & set(range(a, a + n))]
            tag = " + ".join(hits) if hits else "?? UNATTRIBUTED"
            if not hits or not span <= attributed:
                unnamed.append((lo, hi))
        print(f"       0x{lo:05X}..0x{hi - 1:05X}  {hi - lo:4d} B   {tag}")
    check(not unnamed,
          f"every one of the {len(runs)} changed runs vs V103 lies inside a named edit or a "
          f"CRC trailer" + ("" if not unnamed else f"  -- STRAY: {[(hex(a), hex(b)) for a, b in unnamed]}"))
    check(len(runs) == 7,
          f"exactly 7 changed runs vs V103: the five edits + two CRC trailers (got {len(runs)})")
    # ==============================================================================================
    print("\n  [11] .rwd ENCODE + READBACK (pipeline check -- WRITE_MODE gates whether files land)")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V104 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    check(img_sha == EXPECT_IMG_SHA,
          f"image SHA256 == the ACCEPTED FROZEN value {EXPECT_IMG_SHA[:20]}... -- a docstring "
          f"edit must not move a byte")
    check(rwd_sha == EXPECT_RWD_SHA,
          f".rwd  SHA256 == the ACCEPTED FROZEN value {EXPECT_RWD_SHA[:20]}...")

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V104_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"a DIFFERENT {OUT} already exists.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            # ======================================================================================
            # EVERYTHING BELOW READS THE SHIPPED FILE BACK OFF DISK.  No script claims.
            # ======================================================================================
            print("\n  [12] FROM-DISK VERIFICATION -- the shipped .rwd, decoded")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha, "shipped .rwd sha256 OK")
            FF.assert_x31_checksum(shipped, "V104 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "shipped .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped CRC 50/50")
            disk_img = bytearray(Path(BIN_OUT).read_bytes())
            check(hashlib.sha256(bytes(disk_img)).hexdigest() == img_sha,
                  "plain image re-read from disk, sha256 OK")
            check(bytes(disk_img) == bytes(sd), "plain image on disk == decoded shipped .rwd")
            check(rd(disk_img, E1_ADDR, 4) == E1_POST
                  and rd(disk_img, E2_INSN_ADDR, 4) == V67.REPOINT_TO
                  and u16(disk_img, E3_ADDR) == V67.ARM_NEW
                  and rd(disk_img, E4_LOAD_ADDR, 4) == E4_LOAD_HW1 + E4A_POST
                  and rd(disk_img, E4B_ADDR, 2) == E4B_POST + bytes([E4_SAR_BYTE1]),
                  "shipped: all five edits present, re-read from disk")
            check(rd(disk_img, CAVE_BASE, CAVE_LEN) == V103_CAVE,
                  f"shipped: the {CAVE_LEN}-byte cave is byte-identical to V103's, from disk")
            check(disk_img[BQ_ARM_CAL] == 1 and disk_img[0xC64FA] == 5,
                  "shipped: biquad arm still 1, 0xC64FA still 5")
            assert_frozen(disk_img, "SHIPPED image")
            assert_friction_family(disk_img, "SHIPPED image")
            eme_audit(disk_img, base, stock, "SHIPPED image, from disk")

    print("\n" + "=" * 102)
    print(f"  V104 [{TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  ({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  E1  0xC60B4  c4 {c4_old:.5f}f -> {c4_new:.5f}f (x{E1_K}) -- the biquad's SCALAR INPUT")
    print(f"      GAIN. Zeros are ON the unit circle, so the notch was already infinitely deep;")
    print(f"      this raises |H| everywhere else. |H_new| >= 1 on {n_gt1 * 100.0 / N:.1f}% of the axis,")
    print(f"      peak {hmax_new:.4f} at DC. AT fs = 1000 Hz THE NULL IS AT 55.23 Hz, so the ratio is a")
    print(f"      FLAT x{E1_K} in EVERY symptom band (6-9 Hz, 20-28 Hz). NOT a 6-9 Hz attenuator.")
    print(f"  E2/E3  LEVER B RESTORED -- 0x3AA96 c5->fb + 0xC6446 512->5244. Lost at V101; last")
    print(f"      flown on V88, the kit's best measured state. Byte-identical to V67's encoding.")
    print(f"  E4  CAN 427 -> gp-0x6b86 (the biquad LANE) with sar 6 -> sar 4. GATE 3: reachable")
    print(f"      |gp-0x6b86| <= {reach} counts at k={E1_K}; field = clamp((|x|*5)>>4,0,1023) -> "
          f"{(reach * E4_PACK_MUL) >> E4_SAR_NEW}/1023")
    print(f"      = {100.0 * ((reach * E4_PACK_MUL) >> E4_SAR_NEW) / E4_FIELD_MAX:.1f}% used, "
          f"{2 ** E4_SAR_NEW / E4_PACK_MUL:.2f} counts/LSB, saturation only above {sat_onset} "
          f"({sat_onset / reach:.2f}x the bound).")
    print(f"  E5  DROPPED -- a 44 B comparator was designed and priced, then dropped because CAN")
    print(f"      0x14A has NO free bit: the free channel is byte4 bits 7:3 (V103 spent all five),")
    print(f"      and bits 2:0 are HONDA'S (gp-0x6799 / gp-0x679b / gp-0x679a, written in")
    print(f"      FUN_00055a98 BEFORE the hook). V104 PRESERVES all three. Cave UNCHANGED at "
          f"{CAVE_LEN} B, {CAVE_FREE_END - CAVE_BASE - CAVE_LEN} B free.")
    print(f"  DOSE READOUT: the 427 channel is RECTIFIED (Honda's abs() at 0x55DF4), so a true")
    print(f"      k=1.85 reads 1.603. PRE-REGISTER PASS = [1.50,1.70]; ARM-FAIL = ~1.00. k is")
    print(f"      BINARY (one cal in a CRC block) -- there is no half-failed arm to confound it.")
    print(f"  CRC: two trailers, 0xC4FFC (E2/E4a/E4b) and 0xC6FFC (E1/E3).")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
