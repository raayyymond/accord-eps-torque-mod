---
name: reference-accord-vibration-requires-lkas-engaged
description: Route 13 (2026-07-26) — the 21.09 Hz Q~14 steering resonance is present ONLY when openpilot is commanding lateral; matched hands-off/moving/OP-on-vs-off test gives 9,200x less 21 Hz power with LKAS disengaged. Makes it a CLOSED-LOOP LKAS instability, not the always-on base-assist limit cycle CLAUDE.md described. Also: mode spans <1.5 to ~15 m/s, not just 3-8.
metadata:
  type: reference
---

Measured on route 13 (`75604b0a432fdc89_00000013--f484e75b00--{12,13,14,15}`), a deliberate
parking-lot reproduction of the felt vibration on the FOURFRAME build (V38 torque cal + a passive
read-only telemetry cave, i.e. **V38 behaviour**). Entire route 0-2.7 m/s. Raw CAN 399
`STEER_TORQUE_SENSOR`, checksum-clean, **CAN 399 sampled at exactly 100.000 Hz** (fitted period
10.0000 ms/segment) => Nyquist 50 Hz.

**★ THE MODE REQUIRES OPENPILOT TO BE COMMANDING.** Matched test — hands-OFF, moving
(`vEgo > 0.3 m/s`), identical window length and speed gate, `carControl.latActive` on vs off:

| Nfft | condition | usable | K | peak | P(21 Hz) | P(3 Hz) | 21/3 |
|---|---|---|---|---|---|---|---|
| 1.28 s | OP steering | 23.3 s | 25 | **21.09 Hz** | 7.03e7 | 7.84e5 | 89.7 |
| 1.28 s | OP off | 16.8 s | 18 | 2.34 Hz | **7.62e3** | 4.62e6 | 0.002 |
| 2.56 s | OP steering | 14.4 s | 6 | 21.09 Hz | 1.26e8 | 2.20e6 | 57.4 |
| 2.56 s | OP off | 9.6 s | 5 | 2.34 Hz | 2.36e4 | 7.77e6 | 0.003 |

**9,200x less 21 Hz power disengaged**, and the disengaged pool is NOT a quiet condition — it carries
**6x MORE** low-frequency energy (3 Hz: 4.62e6 vs 7.84e5). So this is not an excitation-level
artifact. ⇒ **openpilot is inside the loop.** This CONTRADICTS CLAUDE.md's "self-excited limit cycle
in the base-assist loop (command-independent)" framing, while matching the operator's long-standing
report that the vibration is gone with OP disengaged. It also means an **openpilot-side notch / lateral
rolloff at 21 Hz is a zero-brick-risk experiment that should be tried BEFORE any further `.rwd`.**
(The V48B parked full-authority slam with no LKAS command is a DIFFERENT phenomenon — do not merge.)

**⚠ TWO METHOD TRAPS, both hit this session:**
1. **Never analyse mixed hands-on/hands-off data.** A naive latActive-only window peaks at
   **7.42 Hz** (Q~12) and buries the 21 Hz mode at -5.9 dB. Splitting on `steeringPressed` inverts
   it: hands-OFF -> 21.09 Hz dominant by 20x; hands-ON -> broadband 2.34 Hz, Q~0.8. The 7.42 Hz
   figure was briefly reported as "the vibration" and is **RETRACTED**.
2. **The obvious objection to that split is wrong — test it, don't assume it.** `steeringPressed`
   derives from the same CAN-399 torque channel, so it *looks* circular (the oscillation could trip
   the flag and delete its own windows). It does not: driver torque averages **2166 hands-on vs 328
   hands-off**, a clean 6.6x discriminator, and the 7-8.5 Hz band is not what trips it.
3. **Check whether your "disengaged" cell is a PARKED car.** The raw `latOFF & handsOFF` cell has
   **median vEgo 0.00 m/s, 70% of frames < 0.3 m/s** — comparing against it proves nothing. Gate on
   `vEgo > 0.3`; that leaves 20.3 s (longest runs 5.46 s and 4.15 s), which IS enough. (A subagent
   reported this cell as "0.0 s, the route structurally cannot test this" — wrong; it can.)

**Speed dependence, refined across THREE datasets** (route 13 + archived `b9` + archived manual
`aa5b3e0c01`, all effectively V38): the mode sits at **20-22 Hz continuously from <1.5 m/s through
~15 m/s** — best-sampled at 8-15 m/s (K=88/38) — and only **above 15 m/s** changes character to a
broad, low-Q **11-12.5 Hz shelf (Q 1.9-7.1, barely a resonance)**. ⇒ CLAUDE.md's "~21.7 Hz at 3-8 m/s
worst regime sliding to 8-12 Hz at highway" is **refined: 3-8 m/s is NOT special**, and route 13
confirms 21.09 Hz Q=10.2 at **<1.5 m/s** (K=9).

**Consequence for V52C** (flashed, did not fix the vibration, clearly changed manual feel): its EMA
gives **-6.1 dB at 20.9 Hz** — so it WAS a fair test of the `gp-0x4f60` lane and the null is real
evidence against that lane carrying the resonance. Confound: it also adds **-30.5 deg at 7.4 Hz /
-60 deg at 21 Hz**, which in an anti-damping loop can partly offset the magnitude cut. The felt
manual-feel change is best explained by the EMA's integer deadband: increments round to zero for
|raw-filtered| < 1024/(2*74) ~= **7 counts**, a stiction nonlinearity sitting in the assist path.

Related: [[reference-accord-lkas-lane-is-a-lowpass]], [[v44-built-handsoff-damping]],
[[accord-low-speed-lockout-window-c62ea]] (STEER_STATUS=3 covers 31-86% of this route's frames),
[[reference-accord-can-tx-100hz-base-tick-and-gateway-evidence]].
