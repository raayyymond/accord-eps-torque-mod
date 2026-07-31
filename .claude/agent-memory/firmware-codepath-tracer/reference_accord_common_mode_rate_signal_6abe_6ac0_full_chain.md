---
name: reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain
description: gp-0x6abe and gp-0x6ac0 are the SAME signal (signed vs rectified) from ONE producer FUN_00041464, feeding 15+ control-path consumers in phase -- the common-mode rate bus. Full chain resolver angle -> FUN_00068f52 (centred 2-sample differentiator) -> gp-0x4f50 -> EMA alpha=37/128 -> both outputs. Nets -40.4 deg vs true velocity at 21 Hz (still damping, cos=+0.76). Also CORRECTS my own fun41464 memory: the fault gate is symmetric |x|>13000 and is UNREACHABLE.
metadata:
  type: reference
---

# The common-mode motor-rate bus (traced 2026-07-30, stock `code.bin`)

## 1. One producer, one signal, two faces [VERIFIED]

Exhaustive 4-method byte scan (disp16 with per-opcode rules incl. store-of-zero, disp23 extended,
LE32 literal, movhi/movea + `movea disp,gp,rX` address-take):

| cell | writers | all inside |
|---|---|---|
| `gp-0x6abe` | `0x41790`,`0x417A0`,`0x419F8`,`0x41A18` | `FUN_00041464` |
| `gp-0x6ac0` | `0x41820`,`0x41832`,`0x41A8C`,`0x41AAC` | `FUN_00041464` |

4 stores each = 2 code paths x (diag-inject store, plain store). **`FUN_00041464` is the SOLE producer
of both.** EMA state `gp-0x359c` has exactly 2 accesses (`ld.w 0x415B4`, `st.w 0x41B74`), both inside
`FUN_00041464` — the accumulator is private.

```python
# 0x41A18 / 0x41AAC  -- both derive from the SAME uVar16 (the EMA state)
gp_6abe = (state >> 10)          # arithmetic, SIGNED
gp_6ac0 = (abs(state) >> 10)     # rectified
# => gp-0x6ac0 == |gp-0x6abe| to within +/-1 LSB of truncation. NOT independent signals.
```

**The diagnostic-injection branches are DISARMED in stock**: they require
`*(char*)(tp+0x50eb..0x50ee) == 0xE9`; byte-read `0xC40EB/EC/ED/EE = 00 00 00 00`. Plain stores are live.

## 2. Full derivation chain back to the sensor [VERIFIED]

```
FUN_00065afe (resolver sin/cos -> rotor electrical angle)
  -> FUN_00068f52  [ISR rate estimator]
       d   = wrap(theta - theta_prev, +/-0x2000)      # 0x68f70/78, modulus 0x4000 = 16384 cts/elec rev
       raw = (d * 120000) >> 14                        # 0x68f86, gain 7.32422
       y   = (raw_prev + raw) / 2                      # 0x68f96, 2-tap boxcar, C trunc-toward-zero
       gp-0x29c4 = clamp(y, +/-13000)                  # 0x68f9e
  -> FUN_00068fbe  [0x68fbe-0x69045]  __disable_irq(); gp-0x4f50 = gp-0x29c4; __enable_irq()
       # 0x68FDE `st.h r28,-0x4f50[gp]` is the SOLE writer of gp-0x4f50 (byte-scan, 11 hits, 1 store)
  -> FUN_00041464  [task level, phase-gated 5/16]
       state += ((raw*1024 - state) * 37) >> 7         # 0x415e8, cal 0xC643C = 37 (byte-read)
```

**The rate IS a differentiation of angle.** Backward-difference x 2-tap boxcar composes to
`H(z) = (1 - z^-2)/2` — a **centred 2-sample differentiator**. Against an ideal `jw` at 21 Hz it is
essentially perfect: `|H/ideal| = 0.99997`, phase `-0.76 deg` at f_isr=10 kHz (and 0.99999/-0.38 at
20 kHz). **No attenuation, full +90 deg lead — wide open at 21 Hz, exactly as feared.** The ONLY
roll-off in the whole chain is the single EMA.

## 3. Gain and phase at 21 Hz [VERIFIED arithmetic; task rate 1 kHz per kit memory]

Exact integer time-domain sim (non-uniform 5/16 gating, real `>>`, real clamps):

| f | \|H\| EMA | dB | phase |
|---|---|---|---|
| 7.4 Hz | 0.910 | -0.82 | -19.9 deg |
| **21 Hz** | **0.600** | **-4.44** | **-39.3 deg** |
| 30 Hz | 0.448 | -6.98 | -41.3 deg |

Analytic uniform-rate check at fs=312.5 Hz gives 0.633 / -39.65 deg — agrees.

**Net phase of `gp-0x6abe` vs TRUE motor velocity at 21 Hz = -40.4 deg, cos = +0.76.**
A term `T = -k*gp-0x6abe` therefore still **NET DAMPS** at 21 Hz (76% effective), with a 65%
quadrature component. It is NOT anti-damping. This holds for any f_isr in 5-20 kHz.

## 4. Why this is the COMMON-MODE bus [VERIFIED membership]

Control-region consumers, all reading the ONE filtered signal, hence all moving **in phase**:

- `gp-0x6abe` (signed): `FUN_000242a2`, `FUN_00034350` (damping), `FUN_0003bd7c` (return-centre),
  `FUN_0003f776` (-> `gp-0x6a56` = CAN `STEER_ANGLE_RATE`), `FUN_0003f884`, `FUN_000456a4` (sign of the
  post-governor comp), `FUN_00045a20` (monitor).
- `gp-0x6ac0` (magnitude): `FUN_0002c478`, `FUN_0002db94`, `FUN_00034350`, `FUN_00035ce6`,
  `FUN_00035e00`, `FUN_00036388`, `FUN_00036828`, `FUN_0003a382` (the P/I/D residual lane),
  `FUN_0003aa2c`, `FUN_000456a4` (the gate), `FUN_0004bc0e`, `FUN_0004e378`.
- Outside the control region (diagnostic/UDS/telemetry, not individually adjudicated):
  `0x56576/84/8C`, `0x569B6`, `0x59A30/3A`, `0x59BD4/DE`, `0x5A124/2E`, `0x68D06`, `0x68D82`,
  `0x70670`, `0x71372`, `0x75932`, `0x7B066`, `0x7C512`, `0x7CA54`, `0x7CCCA`, `0x7CE26`, `0x7CFEC`.

`FUN_00034350` reads BOTH (`0x345FA` magnitude, `0x34604` sign) — common mode even within one lane.

**Consequence for the 20 null builds:** any single-lane mute leaves the other 14 consumers driven by
the identical signal. If 21 Hz rides on `gp-0x6abe`, muting one lane cannot remove it. See
[[reference-accord-fun456a4-gp6ad0-resolved-live-damping-no-step]].

## 5. NO estimator/observer with its own dynamics [VERIFIED — clean negative]

There is **no PLL, no Luenberger observer, no resolver tracking loop** anywhere in this chain. The
"estimator" is one backward difference + one 2-tap FIR + one first-order EMA. Poles: the EMA's single
real pole at `z = 1 - 37/128 = 0.7109` (fs_eff ~312.5 Hz => ~17.1 Hz corner). **The only pole in the
whole rate path.** No ~20 Hz resonant estimator pole exists to be the culprit.

## 6. CORRECTION to my own earlier memory [VERIFIED]

[[reference-accord-fun41464-sign-filter-phase-response]] section 2 states the live path "only runs when
`gp-0x4f50 <= 12936` (asymmetric, positive-side-only)". **Both halves are wrong.**
- `addi 0x32c8,r15,r11` @`0x415BE` (bytes `0f 5e c8 32`) biases by **+13000**, then an UNSIGNED compare
  against **26000** -> the test is symmetric **`|gp-0x4f50| > 13000`**. A one-sided test would need no bias.
- `FUN_00068f52` clamps its output to exactly `+/-13000` (`0x68f9e`), and it is the only source of
  `gp-0x4f50`. **So `|gp-0x4f50| > 13000` is NEVER true — the fault branch is UNREACHABLE via the data
  path, and the EMA path always runs.**

⚠ I have NOT edited that older file — operator to confirm before it is rewritten.

## Related
[[reference-accord-fun456a4-gp6ad0-resolved-live-damping-no-step]] — the Target-2 consumer, resolved.
[[reference-accord-fun41464-sign-filter-phase-response]] — superseded on the gate; phase numbers refined.
[[reference-accord-rate-limiter-enumeration-gp6bb2-cluster-and-angle-rate-producer]] — `gp-0x6a56` is a
fixed Q15 scale of `gp-0x6abe`; this trace supplies `gp-0x6abe`'s own origin.
