# ★★ V56 FLASHED — the `0xC6AF0` mute is NULL for the 21 Hz and COSTS damping ⇒ REVERT to V55

**Route `24`, 2026-07-29** — 16 segments, **15:43**, the kit's **first road drive with a firmware probe**
(every prior vibration route was parking-lot creep). V56 = V55 + `0xC6AFC`/`0xC6AFE` 32768→0, which
zeroes the output bound of `gp-0x6ad4` unconditionally, i.e. **mutes the whole `FUN_0003a382` residual
lane, all three branches at once**.

## 1. The 21 Hz is UNCHANGED — the lane is eliminated as a class

Speed-matched creep (vEgo ≤ 1.6 m/s), engaged + hands-off, **full 16-bit** CAN `0x18F` bytes 0-1:

| build | P[15-26 Hz] engaged | disengaged | ratio |
|---|---|---|---|
| **V56 / route 24** | **1.28e8** | 1.63e5 | **786×** |
| V55 / route 1c | — | — | 877× (recorded) |

And the command still carries it: probe field P[15-26] = **182** on V56 vs **22** on V55 at matched creep
(peak 23.24 Hz), i.e. **not reduced**. Transition rate 23.9/s (V56) vs 21.9/s (V55) — the command is just
as active.

⇒ This is pre-registered **outcome (iii)**: neither the vibration nor the command's 21 Hz moved.
🛑 **`gp-0x6ad4` / `FUN_0003a382` is ELIMINATED as the 21 Hz source.** V43, V46 and V48A each attenuated
one branch; V56 killed all three via the output bound. That whole thread is closed — see
[[reference-accord-gp6ad4-lane-and-c6af0-output-gate]].

## 2. ★★ The few-Hz resonance is WHEEL ORDER 1 — a TYRE problem, not V56's doing

⚠ **This section replaces a first-pass reading that called the ~8.7 Hz line a V56-induced resonance. It
is not.** Identified on the **independent** `STEER_ANGLE_RATE` channel — `0x18F` bytes[2:4] BE signed
× **−0.1** deg/s, the 10× finer copy of the field openpilot actually reads at `0x14A[2:4]`
(r = −0.9473 vs `carState.steeringRateDeg`):

```
f = 0.4890·v − 0.186 Hz     r = +0.9970    rms residual 0.037 Hz    intercept ≈ 0  (through the ORIGIN)
implied rolling circumference 2.088 m   (p10-p90 2.076-2.099)
# a 2020 Accord on 235/45R18 is 2.05-2.11 m  =>  exactly ONE line per wheel revolution
```

| v (m/s) | n | f measured | v/2.08 predicted | v/f (m) |
|---|---|---|---|---|
| 16.5-18.0 | 32 | 8.496 | 8.568 | 2.092 |
| 18.0-19.5 | 12 | 8.691 | 8.687 | 2.083 |
| 19.5-21.0 | 11 | 9.766 | 9.772 | 2.084 |

⇒ **tyre/wheel imbalance, non-uniformity or runout** — a road input, firmware-independent, invisible on
every prior route because at 1.5 m/s wheel order 1 is 0.7 Hz. Burst-like: worst window Q=55, **1608× the
local floor**, 77× in power; the *pooled* envelope Q is only 3-4, so the sharpness lives entirely in the
bursts. ⇒ **Get a wheel balance / road-force check.** The 2.088 m fit is specific enough to test.

★ **AND there is a separate genuine FIXED ~7-8 Hz resonance on EVERY build** — V56 7.81, V55 7.03,
V54 8.59, V53 7.03, R13 7.42 Hz at creep, where wheel order is only 0.3-0.8 Hz, so it cannot be wheel
order. Both appear simultaneously in the seg-11 high-resolution spectrum (7.275/7.52/7.715 Hz **and** the
9.766 Hz wheel-order line at 20.3 m/s). **At 15-20 m/s the wheel-order line sweeps UP THROUGH that fixed
resonance** — the classic recipe for an intermittent low-frequency shake that only ever shows on the road.
**That is the most likely thing the operator felt.**

⚠ **"V56 removed damping" is NOT supported by the data — and NOT closable.** Matched creep (0.4-3.0 m/s),
engaged + hands-off, torsion bar, 1-10 Hz band variance: **V56 9.75e3** vs V55 5.70e4 (**0.17×**),
V53 9.68e4 (0.10×), R13 4.03e4 (0.24×), V54 7.38e3 (1.32×); angle-controlled (|ang|<5°, only R13 survives)
V56/R13 = **0.64×**. Envelope-decay Q: V56 **3.6**, V55 7.4, V53 14.1, V54 4.8, R13 3.5 — V56 is **not**
the least damped. 🛑 **But every one of those numbers is at CREEP, and the operator felt it at ROAD speed,
where no prior build has any data at all.** Do not use the creep table to dismiss the report.

⚠ **Control gaps:** V56 has **zero disengaged windows above 3 m/s** (the whole road drive was engaged), and
**no pre-V56 road baseline exists** — route `13` has only segments 12-15 on disk, creep, vEgo max
2.73 m/s, 250 m total.

## 3. 🛑 A partial restore (`Y = 16384`) is NOT a candidate

The lane at **100%** authority (V55) and at **0%** (V56) produced the same 21 Hz. Intermediate authority
is bounded between two measurements that already agree, so it can only deliver a fraction of an effect
that was zero. It has no experimental value — it is a partial revert wearing a candidate's clothes.

## How to apply

- **Revert to V55.** `39990-TVA,A160-V55-...rwd`, SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf`.
  Already built, already driven, known-good, and it keeps the probe.
- Do **not** re-propose any `FUN_0003a382` lever for the vibration — the branch-agnostic test is done.
- The 21 Hz must enter `gp-0x6b98` through a **different summand**. The aggregator has **9 lanes**, all
  plain `add` — enumerate the others. See [[reference-accord-fun3a382-is-a-real-pid]] for the confirmed
  lane list.
- ⚠ Every amplitude figure derived from the probe is suspect — see
  [[reference-accord-probe-underranges-to-a-one-bit-comparator]].
