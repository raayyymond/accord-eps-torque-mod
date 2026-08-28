---
name: accord-the-harmonics-track-neither-firmware-saturation
description: "The 7-9 Hz harmonics are real and pervasive but track neither firmware saturation axis. By SPEED (16-17 routes, tight CIs) the harmonic ratio is flat at 1.110/1.159/1.162/1.117 from 10 to 200 km/h, which REFUTES the damper's +-511 clamp as the generator since its rail duty falls from 15.46 percent at 10-25 km/h to 0.23 percent above 65. By |rate| it is 1.133/1.096/1.317/1.075/1.283 with no rise past the relay's 31.8 deg/s saturation point, which fails to support the Coulomb relay either, though that test is underpowered at 7-11 routes. A nonlinearity active uniformly across the whole operating range is more consistent with PHYSICAL friction than with any firmware clip - which weakens V121's specific mechanism while leaving its engineering properties intact."
metadata:
  node_type: memory
  type: reference
---

# 🛑 THE HARMONICS TRACK **NEITHER** FIRMWARE SATURATION — V121's mechanism weakens again

## THE DISCRIMINATOR
[[accord-the-7to9hz-energy-is-manufactured-not-commanded]] established the energy is generated inside
the loop. Two hard nonlinearities sit there and **saturate on different axes**, so they separate:
```
   A  COULOMB RELAY    clamp(POL*gp-0x6abc*12/knee, +-1)   saturates on |RATE| >= 31.8 deg/s (V112)
                       => harmonics should RISE past ~32 deg/s, largely speed-independent
   B  DAMPER's +-511 CLAMP on gp-0x6b26                    rail duty is strongly SPEED-dependent:
                       10-25 km/h <=15.46 %  ...  65-90 <=0.23 %  90+ <=0.03 %   (build_v108 E2)
                       => harmonics should be strong at 10-40 km/h and VANISH above 65
```

## [EVIDENCE] Both predictions fail
```
   by SPEED   (16-17 routes, tight CIs)
      10-25   1.110 [1.030, 1.189]      40-65   1.162 [1.088, 1.211]
      25-40   1.159 [1.046, 1.372]      65-200  1.117 [1.041, 1.159]

   by |RATE| p95   (7-11 routes, wide CIs)
      0-15    1.133 [1.089, 1.197]      32-60   1.317 [0.958, 1.887]
      15-32   1.096 [0.987, 1.132]      60-120  1.075 [0.802, 1.443]
                                        120+    1.283 [1.008, 1.475]
```
✅ **The CLAMP hypothesis is REFUTED** — this arm is well powered (16-17 routes, tight CIs) and the
ratio is **flat at 1.11-1.16 across 10-200 km/h**, while the clamp's own rail duty falls **67×** over
that range. A generator whose duty falls 67× cannot produce a flat harmonic ratio.
🛑 **The RELAY hypothesis is NOT SUPPORTED** — no rise past its 31.8 deg/s saturation point.
⚠ **But that arm is UNDERPOWERED** (7-11 routes, CIs spanning 1.0) ⇒ **not supported ≠ refuted.**
⊕ **Harmonics themselves are real and pervasive** — every bin exceeds 1.0 and most CIs exclude it.

## ⇒ WHAT IT POINTS AT INSTEAD
A nonlinearity that is **active uniformly across the entire operating range** is not a saturation at
all. That profile fits an always-on mechanism — **physical friction / stick-slip in the column and
rack** — better than any firmware clip. ⊕ It coheres with
[[accord-the-78hz-mode-does-not-move-with-firmware-gain]] (the mode is mechanical) and with
[[accord-the-antidamping-is-hondas]] (the 6-9 Hz anti-damping is present in stock).
🛑 **This does NOT overturn** [[accord-the-7to9hz-energy-is-manufactured-not-commanded]]: the energy
is still generated downstream of the command rather than commanded. **What changes is WHERE:** it may
be manufactured by the *plant*, not by the firmware — in which case no cal edit reaches it.

## 🛑🛑 HONEST CONSEQUENCE FOR V121
V121's mechanism has now failed **two independent checks**: the closed-loop simulation did not
reproduce the knee trend, and the harmonics do not track the relay's own saturation axis.
⇒ **V121 is now a build with GOOD ENGINEERING PROPERTIES and a WEAK MECHANISM CASE.** What survives
is entirely independent of the relay story: small-signal gain held **exactly** at V112's
(bit-identical ≤ 31.8 deg/s ⇒ near-zero regression risk), **more assist above** 31.8 deg/s, cal-only,
4 payload bytes, 40/40, and `knee`'s on-car track record (600→1800 coincided with the best-ever
build). **Its effect on the oscillation is UNKNOWN and should be presented that way.**
✅ The pre-registered card already scores it correctly, and its **> 1.45 = refuted** band is exactly
the outcome this result makes more likely. **Fly it as a test, not as a fix.**
Tool: `rlog-tools/studies/peakturn/harmonic_generator_discriminator.py`.
