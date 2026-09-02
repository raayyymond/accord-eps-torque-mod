# HANDOFF — 2026-09-02 — V278: the reference brought back into reach, and a damping tap

**Predecessor:** `HANDOFF-2026-09-01-the-loop-that-stopped-damping.md` (the diagnosis, before the rlog).
**Artifact:** https://claude.ai/code/artifact/b2a2995e-e219-4e18-a2c3-e99a979d0575
**Status: V278 BUILT, written to `../accord-firmwares`, NOT flashed. V277 marked SUPERSEDED-DO-NOT-FLASH.**

---

## What shipped

```
image  4bc510734c7b53fcdb242a28ce97149ecb4eb86fd2da1f4a39dbedff2865a22c
rwd    ac9d27a974545bd9144095182d6dd95ef5dbd03056ab5a0d6529808b5ee10562
487/487 · CRC 50/50 · bootloader replay 49/49 · cipher fail-closed · independent rebuild reproduces
```
`analysis-2020accord/builds/v108_plus/build_v278_tva.py`, base **V268**:

| edit | where | V268 → V278 |
|---|---|---|
| reference map ×2 | 28 LERP records at `0xE4000`–`0xE8105` (pointer family `0xC9A88` untouched) | Honda Y knots ×2; slot 7 ceiling 172 → 344 |
| feedback clamp | `0xC62E6` | 7680 → 15360 (stored ×256: 30 → 60); ratio 1.395 preserved structurally |
| damping tap | `0x55DF0`–`0x55E11`, 34 B in place, `jarl 0x49A90` untouched | `wire = (sel & 0x0F) \| ((E ^ fb_state) >> 31) << 9` |

Everything else byte-identical to V268: `FUN_00028ea6`, Kp/Kd (all 28 slots), all four taper banks, V112's cave and hook, every FROZEN cell. 439 bytes differ, 165 runs, all attributed; 7 CRC trailers.

---

## The dose — sized from the operator's own drive, frame by frame

The V276 rlog (route `r2e`, 16 segments, 73 s engaged) was read three ways: the pre-registered spectral
instrument, a decoder-independent raw CAN read, and openpilot's own `controlsState`. Then `E` was recomputed
per frame at each K with the real command, the real rate, the exact filter and the taper
(`rlog-tools/studies/osc-2to4/dose_e_sign_by_k.py`):

| K | oscillation: lane opposes wheel | normal engaged: lane opposes wheel | ceiling crossover |
|---|---|---|---|
| 1 stock | 0.94 | 0.80 | 22.3 deg/s |
| 1.5 | 0.90 | 0.75 | 33.4 |
| **2 (V278)** | **0.86** | **0.70** | **44.5** |
| 2.5 | 0.82 | 0.65 | 55.7 |
| 6 (V276) | 0.57 | 0.48 | 134 |

🛑 **"The loop never damps" — the first handoff's framing — was WRONG.** It damps *less*: 0.57 of oscillation
frames at V276, 0.94 at stock. The **combined** loop (EPS rate lane + openpilot's angle follower, which swings
with coh ≥ 0.97 but whose desired path is flat) went unstable in between. **The crossover does not cap the
oscillation's amplitude** (V276's peaks overshot theirs 1.5–2×); the earlier "residual at ~44 deg/s" prediction is
withdrawn. K=2 restores 0.86 while keeping the ceiling crossover at twice stock's, so on turns the lane still
pushes through the median achieved rate (~27 deg/s) where stock yielded. K=1.5 (0.90) is the fallback.

**Peak torque is untouched at every K** — `0xC61B4`, `0xC6CD0` and the map's Y-ceiling are frozen.

---

## The instrument — and the one that was thrown away

The first V278 window put plain `sign(E)` on bit 9. It decoded correctly, passed 450/450 and an arithmetic
adversarial pass — and **would have measured nothing**: on the V276 log `sign(E)` reads ~0.50 at every K,
because on a straight road `E`'s sign follows the direction of motion. The quantity that discriminates is
`sign(E) != sign(fb)` — the lane OPPOSING the wheel — and that is what flies:

```
8437b398 ld.bu -0x674e[gp],r6  c6360f00 andi 0x0f,r6,r6  244f0993 ld.w -0x6cf8[gp],r9
243fd1c2 ld.w -0x3d30[gp],r7   2749 xor r7,r9   9f4a shr 0x1f,r9   c94a shl 0x9,r9   0931 or r9,r6
2046ff03 movea 0x3ff,r0,r8     003a mov 0,r7    0000 0000 nop nop
```
Every opcode field-decoded from the written bytes with a positive control on a real instance (`xor r9,r12`
at `0x504E2`; `ld.w -0x3d30,gp,r26` at `0x28F7C`). Ghidra on the built image emits
`FUN_00049a90(*(byte*)(gp-0x674e) & 0xf | ((*(uint*)(gp-0x6cf8) ^ *(uint*)(gp-0x3d30)) >> 0x1f) << 9, 0, 0x3ff)`.

**Predicted duty:** ~0.57 on V276 in an oscillation episode, ~0.86 on V278. Selector in bits 3:0 must read **7**.
Known imprecision, accepted: the tap reads the filter's single-tick output `y[n]` (`gp-0x3d30`), while the PID
subtracts `y[n]+y[n-1]`; their signs differ for at most one tick per zero crossing — ≤ ~0.8 % of ticks at
3.9 Hz / 1 kHz. If the PID's plausibility guards (`0x28f08`–`0x28f66`) skip a tick, both cells read stale
together; the instrument is read engaged-only where those guards do not fire (BELIEF, not traced).

### The sentence a null licenses
Duty ~0.86 and no oscillation → mechanism confirmed. Duty ~0.86 and the oscillation persists → the damping
fraction is not the whole mechanism; openpilot's follower gain is next (a comma-side lever exists). Duty ~0.57
on V278 → the map is not the live setpoint source; the selector nibble and the map bytes settle which.

---

## The adversarial pass — five agents, two revisions

| agent | surface | verdict |
|---|---|---|
| `adv278a` | arithmetic / units, rev 1 | no fail; refuted two of the orchestrator's own concerns (ratio preservation is structural; Kp/Kd are demand-indexed) — but misread the two-sample sum as 15.45 |
| `adv278b` | build script, rev 1 | rebuild reproduces; 45/53 mutations caught; **F1** no "all 28 dosed" count, **F2** live-slot identity untestable, **F4** the docstring's K table was not reproducible from the kit |
| `adv278c` | packer / interlocks, rev 1 | no bricking-class defect; r9 was dead before the edit too; clamp helper's `in_r10` inert; bit 9 lands in byte0 bit 1; **second writer of the E cell in `FUN_0002a93a`** flagged |
| `adv278d` | packer, rev 2 | formula matches; `y[n]` vs sum noted; **caught a STALE Ghidra program** serving old bytes for the same filename — re-import fresh |
| `adv278e` | build script, rev 2 | rebuild reproduces `4bc51073…`; 74/82 mutations caught; **over-dosed / reshaped non-live record passed** (readback-only check); dead `FB_STATE_DISP`; wrong 378 derivation comment; F4 closed |

**All script findings fixed after the last audit closed** (per-record compare against K × BASE Y re-read from
the base; the count; the constant made load-bearing; the comment). The image did not change.
**The `FUN_0002a93a` writer is UNREACHABLE** — no `jarl`/`jr`/`jarl32`/`jr32` or absolute pointer anywhere in
the image reaches it, positive-controlled on `FUN_00028ea6`'s real caller at `0x22522` — verified by the
orchestrator and now a build assertion. Residual: a register-indirect call, for which no pointer exists.

---

## Corrections of record, this session

1. 🛑 **The feedback operand is `s_old + s_new`** (`add r9,r26` @`0x28FA4`), DC gain **30.89**. Two agents read it
   as 15.45. Reconciles 8 counts/deg/s (measured, corr 0.997) with the 22.3 deg/s stock ceiling. Memory:
   `accord-feedback-operand-is-a-two-sample-sum-dc-30-89`.
2. 🛑 **`sign(E)` alone cannot measure damping.** Memory: `accord-sign-e-alone-cannot-measure-damping`.
   **Run the instrument's statistic offline on a flown log BEFORE cutting the tap.**
3. **The mechanism is a matter of degree.** Memory: `accord-v276-mechanism-is-a-matter-of-degree`.
4. **The live slot is 7 (record 11 `TVCA4`)**, confirmed on the wire by two decoders — the kit already knew
   (`reference-accord-car-is-tvca4-mode-24-26`, 2026-08-05); the slot-1 belief this session came from V38's
   stale docstring. `feedback-search-the-kit-before-naming-a-cause`, twice in one day.
5. **The pre-registration's "command oscillates ⇒ outer loop ⇒ do not build" branch mis-specified its own
   verdict**: it fires on a measurement-driven signal. Both agents that ran it rejected it as written.
6. **Grip kills the oscillation at ~2,500 raw driver torque — where the override cliff begins.** V277 (cliff
   softened, authority held to 3584) would have blunted the escape hatch. **V277 is withdrawn**; its `.rwd` is
   renamed `SUPERSEDED-DO-NOT-FLASH-…`.
7. **The 0x18F rate channel never approaches the believed ±12000 clamp** (route max 3190, disengaged).
8. `FUN_00055D80` is reached via a 10-entry function-pointer table at `0xB72B0` (entry 6, `0xB72C8`) — and is
   empirically live: V276's selector came through on the wire.
9. **A stale Ghidra program can serve old bytes for the same filename.** Re-import fresh before judging a
   candidate; cross-check with a direct SHA-verified file read.

---

## Open, deliberately

- The comma-side lever (openpilot's low-speed / friction feedback) is real and untested; it is the next step if
  bit-9 duty reads ~0.86 and the oscillation persists.
- `0xC61BE` (the real 2505 ceiling, virgin in 102+ builds) remains a second-stage authority lever for a stable loop.
- The PID guard chain `0x28f08`–`0x28f66` was not traced for engaged-state reachability (BELIEF: plausibility only).
- The golden model still lacks the rate loop, the taper, the two-sample sum and the selector result.
- `rlog-tools/studies/impedance/rez_by_band_all_routes.py` still globs one of two cache roots.

## Safety
**Nothing was flashed. No CAN message and no UDS read was sent at any point.** V278 is a study artifact until
the operator names the file and the bus.
