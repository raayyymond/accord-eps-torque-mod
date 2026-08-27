# ★★ The 21 Hz vibration requires APPLIED LKAS torque — and it IS in the openpilot command

**Established 2026-07-27 on route 13.** Refines and partly corrects
[[accord-vibration-requires-lkas-engaged]], whose split was on `carControl.latActive` (openpilot's
*intent*) and therefore conflated two very different conditions.

Decode from raw CAN 399: `STEER_STATUS = (d[4]>>4)&0xF`, `STEER_CONTROL_ACTIVE = (d[4]>>3)&1`.
Invariant check passes (0 frames with SCA=1 alongside ST=3). Hands-OFF, `vEgo>0.3`, Nfft=128/hop=64:

| cell | K | peak | P(21.09) | mean abs(cmd) |
|---|---|---|---|---|
| **A** openpilot off | 18 | 0.78 Hz | 5.28e3 | 0 |
| **B** commanding, EPS in lockout (SCA=0) | 5 | 0.78 Hz | 7.02e3 | 2,749 |
| **C** commanding, EPS **applying** (SCA=1) | 17 | **21.09 Hz** | **1.03e8** | 2,529 |

**C/B = 14,750x. B/A = 1.33x (noise).** openpilot commands *harder* in B than in C.
⇒ **Transmitting does nothing; the EPS must actually be APPLYING LKAS torque.**

**Confound, stated honestly:** on this route SCA is a deterministic function of speed (ST=3 *is* the
sub-5 km/h gate) and B/C have zero speed overlap. Partial rescue: cell A spans both ranges, and
**A-high (mean 1.67 m/s) vs C-slow (mean 1.67 m/s) differ by 578x**; within C, speed is irrelevant
(corr -0.040, K=102). Cannot exclude "needs v>1.4 m/s AND engaged, applied torque incidental" — the
discriminating experiment is the `0xC62EA` lockout edit (320 -> 64), which populates the empty C-low cell.

## The 21 Hz IS present in the openpilot command
The long-standing premise "we don't see the resonance in the output LKAS torque CAN signal" is **FALSE**,
and the reason is a real trap: **`0xE4` appears on src=2 and src=128, both identically zero in 100% of
~22,395 frames each.** Only **src=129 (bus 1 TX echo)** carries data (10,177 of 22,390 nonzero).
Inspecting bus 0 or bus 2 shows a flat line.

- Coherence(command, CAN399) @21 Hz = **0.685** (1/K floor 0.040, 95% null 0.117) vs **0.171** at 1-3 Hz.
  ⚠ Coherence is symmetric — it does **not** establish direction.
- The sensor carries far more *relative* 21 Hz than the command ⇒ openpilot is responding, not
  originating. `carState.steeringAngleDeg` also shows it at +23.1 dB over shoulder — the wheel really
  oscillates and openpilot measures it, which is how the command acquires the content.
- ⚠ Magnitude disputed and OPEN: the validated pipeline reports the command's 21 Hz at **+12.0 dB over
  its own shoulder (rank 1 of 47 bins, 8-45 Hz)**; an independent cruder pass got **+1.7 dB**.
- **There is NO openpilot-side low-pass at 21 Hz** — only -2.70 dB, and *less* than at 14.8 or 25 Hz
  because the peak pokes through the broadband rolloff.

⇒ **An openpilot-side 21 Hz notch is UNTESTED, not a no-op.** Zero brick risk; recommended next test.
⚠ **14.0% of gated frames sit at the ±4096 rail and railed windows show no 21 Hz** — keep the rail
fraction matched between baseline and notched runs or the comparison is confounded.

**Retracted argument, for the record:** "openpilot cannot oscillate at 21 Hz because ~100 ms latency is
756 degrees of phase" is **bad control theory**. Delay creates a *comb* of frequencies where phase wraps
to a multiple of 360; what closes a loop off at high frequency is gain rolloff, and there is almost none
here.

## 21 vs 78.91 Hz aliasing — still OPEN
21.09 + 78.91 = 100.00 exactly, and CAN 399 samples instantaneously at exactly 100.000 Hz. The comma IMU
(measured ODR **101.049 Hz**, not 104 -> alias target **22.14 Hz**, separation 1.049 Hz) is the only
non-commensurate channel in the log, and it came back a **tie at the noise floor**: steering barely
couples into a windshield mount (MSC 0.009-0.265) and the gyro's sensitivity floor is 1,770x below the
wheel's measured motion, so the null is about **coupling, not existence**.

Two indirect discriminators favour 21.09, neither airtight:
- **Linewidth -> implied Q**: measured -3 dB width 1.099 Hz gives **Q = 19.2 at 21.09** vs **Q = 71.8 at
  78.91**. Q~72 for a bushed, greased, friction-loaded steering system is not credible.
- **rate/angle amplitude ratio** (self-calibrated against the 3.12 Hz bin): measured **6.51**, predicted
  6.75 for a true 21.09 Hz derivative, **25.25** for 78.91. ⚠ **Void if the sensor forms rate as a 100 Hz
  first-difference** — both then predict 6.28, and the models could not be separated.

⚠ **FOURFRAME2 also transmits at 100 Hz and inherits this ambiguity** — FFT-ing its 16 signals shows
21.09 Hz under either hypothesis. Resolving it needs a non-commensurate transmit tick (e.g. every 7 ticks
of the 1 kHz task = 142.86 Hz) or in-firmware band power at 21 and 79 Hz.
