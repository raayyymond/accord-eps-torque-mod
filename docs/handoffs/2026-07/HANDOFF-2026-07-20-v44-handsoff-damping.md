# HANDOFF — 2026-07-20 — V44: the hands-off damping switch

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** on-car V43 plain image.
**Status:** V44 is **BUILT and independently VERIFIED, NOT FLASHED.** No CAN, UDS, or flash operation occurred.
**Supersedes:** the vibration narrative in every prior handoff. The ratchet narrative (V42 Change 1) stands and is confirmed on-car.

---

## The result in one paragraph

The vibration is a **measured, lightly-damped mechanical resonance** (21.4 Hz, Q ≈ 13.6), not the "sharp clock-locked line" the records claimed — that was an FFT windowing artifact. Its firmware root cause is located: the base-assist **viscous damping** lane `gp-0x6bd0` (`FUN_00034350`) is a product of four Q10 factors, and the factor keyed on voted driver torque `gp-0x6a5e` has **`Y[0] = 0`**, so below 2240 counts of driver torque — **hands-off** — the whole product is multiplied by zero. The firmware carries **no notch filter anywhere** in the command path. So hands-off the resonance rings undamped; hands-on the damper engages and it disappears — the operator's exact report, reproduced from the bytes. **V44 raises `Y[0]` in the two reachable mode tables so the damper is live hands-off.** Cal-only, 12 bytes, dual-verified. Safety is closed; efficacy (is 235 counts *enough*?) is a plant question the car resolves.

---

## What the V43 drive established

V43's dirty-derivative pole (`0xC644A` 1024→32) **fixed neither symptom → falsified.** Combined with V39 (r24) and V42 (r26), the Sensor-B derivative family and the residual-lane pole are all eliminated. V42 Change 1 (the state-4 ratchet byte at `0x454FE`) remains the **confirmed** ratchet fix and is carried through unchanged.

---

## The mechanism, byte-verified

```
FUN_00034350  ->  gp-0x6bd0  (base-assist viscous damping lane)

  seed = clamp(gp-0x698a, 0, 1024)
  term = seed
         * f1(0xC9CCC)   >>10     ; flat unity for mode 10 -- no-op
         * f2(0xC9E9C)   >>10     ; LERP keyed on gp-0x6a5e (VOTED DRIVER TORQUE)   <-- THE GATE
         * f3(0xC9DB4)   >>10     ; flat unity for mode 10 -- no-op
         * f4(0xC9F84)   >>10     ; LERP keyed on |gp-0x6ac0| (MOTOR RATE) -- the viscous factor
  if (gp-0x6abe > 0) term = -term ; sign forced opposite filtered motor rate  -> velocity-opposing
  term = clamp(term, +/- 0xC77A0) -> gp-0x6bd0   (shadow gp-0x4cf2, +4 bytes after primary, all paths)
```

Four chained `mulu`+`shr 0xa` at `0x34684/0x3468a/0x34690/0x34698` — a genuine multiplicative product. For this car (variant **"TVAA1"**, HW-ID byte-read at `0xCD048`, mode-set `{10,10,11,11}`), factor 2's tables are:

```
mode 10 @0xD27BC:  X=(2240, 3840, 5120, 8960)   Y=( 0, 235, 430, 877)
mode 11 @0xD27D0:  X=(2240, 3840, 5120, 8960)   Y=( 0, 234, 431, 877)
```

`Y[0] = 0` in **both**. The LERP **clamps** below `X[0]` (verified, does not extrapolate), so the factor is a flat zero for driver torque under 2240, and one zero multiplicand kills the product. Gate semantics are inverted from intuition: `gp-0x6a5e > 32000 || gp-0x67f4 != 1 → factor = 1024 (unity)`; a *passed* plausibility check with *low* torque → factor = 0. Suppression happens only when the sensor honestly reports hands-off.

**Measured driver torque** (route b9, as fraction of Sensor-B full scale): hands-off median **0.59%**, assisting median **8.10%**; the gate sits at 2240/32000 ≈ **7%**. They straddle it by more than a decade. `gp-0x6a5e` is a magnitude (all channels `abs()`'d before the vote) and is slew-limited such that it **cannot even track a 21 Hz oscillation to the threshold** (max trackable ≈ 4.6–45 counts vs 2240) — so the gate stays firmly on the zero side hands-off regardless of the oscillation.

★ Sensor A (`gp-0x6a5e`) is **never transmitted on CAN** — it and Sensor B (`gp-0x4f60`, what CAN 399 reports, `= -floor(gp-0x4f60 × 125/128)`) are physically separate sensors. The %FS comparison is a normalised inference, flagged as such; there is no direct conversion.

---

## The edit

```
0xC644A :  32 -> 1024    revert V43's falsified pole (restores exact V38 bytes)
0xD27C6 :   0 -> 235     mode 10 Y[0], = its own Y[1]
0xD27DA :   0 -> 234     mode 11 Y[0], = its own Y[1]
```

**Both** modes because `FUN_00042746` reselects among `{10,10,11,11}` at runtime on internal sensor-quality state — patching only mode 10 would let the fix silently vanish after a failover. Each `Y[0]` is set to its own table's `Y[1]`, so every byte written already existed and was exercised in that table (flattens the first segment; invents no magnitude).

---

## Why the restored damper actually damps at 21 Hz — three objections, all refuted

1. **Sign-freeze.** `FUN_00041464` pins `gp-0x6abe` to `0x7fff` only when `|gp-0x4f50| > 13000` (symmetric — Ghidra pcode `INT_LESS(26000, r15+13000)`). But `gp-0x4f50`'s producer `FUN_00068f52` clamps to **exactly ±13000** (14-bit wraparound fold → ±8192 raw → ±60000 scaled → hard-clamped ±13000), so the pin is **structurally unreachable** and `gp-0x6abe` is always live. The golden model docstring had this backwards; corrected.
2. **Half-wave rectification.** The V43 handoff's claim that `ld.hu -0x6ac0[gp]` @`0x345fa` dead-bands one direction is **wrong** — `gp-0x6ac0`'s producer applies `abs()` before the store, so `ld.hu` vs `ld.h` is a no-op. Reached by two tracers independently.
3. **Phase lag flips it to anti-damping.** The sign source `FUN_00041464` is **confirmed ~1000 Hz** (single caller in the 1 kHz control task, state-gated not decimated). Exact discrete-filter + zero-order-hold phase:

   | producer task rate | total phase | efficacy |
   |---|---|---|
   | 1000 Hz | −21.8° | cos **+0.93** |
   | 100 Hz | −56.5° | cos **+0.55** |

   Net-dissipative at either rate. Net injection would require the producer at ~100 Hz *and* sustained worst-case staleness, landing at cos −0.09 (negligible), not the −0.91 catastrophe an earlier (wrong) continuous-RC estimate implied. **The tick rate stopped being a safety question once the sign source was pinned at 1 kHz.**

---

## The tick rate — CONFIRMED ~1000 Hz (retires a standing open item)

Two independent routes:
- **OSTM0**: `OSTM0CMP` = 79999 auto-reload / ~80 MHz PCLK = 1000 Hz. (PCLK is one of `{48,64,80,160}` MHz per `DFLASH.DCLKWAIT`; only 80 MHz gives a clean ~1 ms; a 100 Hz task would need a non-existent 7.95 MHz.)
- **The `STEER_STATUS=4` dwell**: cal `0xC64DF` = 100 cycles, measured at **100.00 ms** on the bus (dwell counter `gp-0x6757` decrements inside arbitration, measuring that task directly).

⚠ This pins the **control task** `FUN_0002214a` (arbitration, aggregator, shaper, governor, sign filter `FUN_00041464`). The **assist-shaping task** `FUN_00022ca0` (boost, damping producer `FUN_00034350`) is a *different* task; its rate is not statically determinable and is plausibly ~100 Hz (a normal fast-control / slow-input split). That affects V44's **efficacy** (strong vs moderate), not its safety.

Correction of record: CAN 399's rate is 99.99849 Hz (an earlier 100.01362 Hz figure was inflated by gap reconstruction), and 399 is a **100 Hz comms cadence inside the 1000 Hz task**, not the task rate.

---

## Effect size — bounded, adequacy unknown

With `Y[0] = 235`, the term = `clamp(gp-0x698a,0,1024) × f2 × f4 / 1024²`. `f4` saturates at 927 (motor rate ≥ 4000), so the term maxes at **~213 counts** (contingent on `gp-0x698a ≈ 1024`), against the aggregator's ±2048 gate — ~10% of the gate, nowhere near saturating it. It is **viscous** (magnitude scales with motor-rate magnitude via `f4`), not Coulomb. Whether 213 counts is *enough* to damp a Q=13.6 mode against the ~139-count measured oscillation is a **plant** question firmware cannot answer. The car resolves it: a clear drop → strong (producer fast); a modest drop → weak (producer slow, or magnitude marginal); no change → null, pivot to reducing excitation; worse → the pathological case, but cos −0.09 shouldn't be *felt*, and the floor is "≈V43".

---

## Blast radius — all byte-verified

- Pointer array `0xC9E9C`: exactly 2 xrefs, both in `FUN_00034350`. Nothing else reads it.
- **No float mirror**: exhaustive image-wide search for the IEEE-754 patterns of 234/235/430/431/877 over 1024 → zero hits (this is the V27 failure class; it does not apply).
- Shadow lockstep `gp-0x6bd0`/`gp-0x4cf2`: 3 writers each, shadow store +4 bytes after primary on all three paths — cannot desynchronise. Mismatch handler is the shared kit-wide utility `FUN_0006ce7c` (12 callers), no direct DTC reader found for its flags.
- The other three multiplied factors default to Q10 **unity** (not zero) on gate failure, so there is no second silent zero blocking the product.
- `gp-0x6bd0` genuinely reaches the live aggregator `FUN_0003aa2c` (sole writer of `gp-0x6b94`).

---

## CRC mechanics — first build to touch `0xD2xxx`

Both `Y[0]` edits fall in the ordinary chain-interior block **`[0xD2000, 0xD2FFC)`**, present in both the faithful bootloader `walk()` (49 blocks) and `walk_all_blocks()` (50 blocks) — no `0xC5000` bridge-skip subtlety applies. The block's own chain self-descriptor lives at `0xD2FF8/0xD2FFA` (inside its own CRC range, far from the edits); the next-link descriptor lives in the untouched `0xD1000` block. `0xD2000..0xD2FFC` is byte-identical between stock/V38/V43. No prior builder touched `0xD2xxx`; it follows V38's `0xE4xxx/0xE5xxx` `TOUCHED_BLOCKS` precedent exactly.

---

## Artifact

```
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V44-LKAS-4x-V38base-state4-ratchet-off-handsoff-damping-0x13000-0x100000.rwd
```

| Artifact | SHA-256 |
|---|---|
| V44 RWD | `ed8a78ced0550420ed5b93fe800adf7e670df76dc14b6a32bb990109781ea275` |
| `_v44_plain_image.bin` | `cb267d81c37fe7f4597ee11ab36630246a903c7484ed4fe7c995f531eab62389` |
| `_v43_plain_image.bin` baseline | `5ecfddcbd74c3508e0353d8ba6065bd866aaa0ac48bdf549dc8822ba7a0adccc` |

Builder: `analysis-2020accord/builds/v18_v49/build_v44_tva.py`.

## Verification performed

- **V44-vs-V43 = exactly 12 bytes in 5 runs**: `0xC644A`–`0xC644B` (pole revert) + `0xD27C6` (1B) + `0xD27DA` (1B) + the `0xC6FFC` and `0xD2FFC` CRC trailers. Every edit and the full allowed byte-set asserted, not just a count.
- **V44-vs-V38 = exactly 11 bytes**: ratchet byte + the two damping low-bytes + the `0xC4FFC` and `0xD2FFC` trailers. The pole revert makes the whole `0xC6000` block byte-identical to V38, so it does not appear.
- Bootloader walk **49/49** and full chain **50/50** on baseline, V44 image, and decoded RWD readback.
- Ratchet branch decoded before/after — still `br 0x455C4`.
- Both damping records asserted in full (count, X row, Y row, pad); mode 11's own `Y[0]` value read and patched.
- Float-mirror negative asserted inside the builder and re-derived outside it.
- **Independently re-verified by a second script sharing no helper** (`scratchpad/verify_v44_independent.py`): diff, CRC chain walk, table decode, Bcond decode, RWD checksum, IEEE-754 patterns — all re-derived from first principles. All pass.

---

## Corrections of record made this session (propagated to CLAUDE.md + the golden model)

1. The vibration is a **21.4 Hz, Q=13.6 mechanical resonance**; the "sharp 21.02 Hz clock-locked line" was an **FFT windowing artifact** (retracted).
2. The **control-task tick is ~1000 Hz** (two routes) — retires the standing "task rate unresolved" open item.
3. **`gp-0x6abe` is LIVE in normal driving** (pin structurally unreachable); the golden model had it backwards.
4. The **"half-wave rectified damper"** (`0x345fa`) is **wrong** — `gp-0x6ac0` is `abs()`'d before store.
5. The gain-rescaling-invariance framing of the vibration as "small dithering near zero" is **retracted** — it is a large-command, physical-sensor symptom.
6. **`search_instructions` undercounts** (analyzed instructions only, reports `truncated:false`) — use raw byte-pattern scans for load-bearing reader/writer counts. **`disassemble_bytes` mutates** the shared Ghidra DB unless `dry_run:true`.

## Open

- **Efficacy of V44** — is 235 counts enough? Plant question; the car answers it.
- **`FUN_00022ca0`'s exact rate** — 1 kHz vs ~100 Hz; efficacy-only, not safety. Not statically determinable; a dwell/timeout in its tree that reads the canonical tick counter `gp-0x3e54` could pin it if one is CAN-observable.
- **2–10 mph hands-off telemetry** — the one regime route b9 cannot see and the operator reports as worst. Highest-value data to collect, with or without V44.
