# HANDOFF - 2026-07-19 - V40 governor slew removal + flat motor-rate torque cap

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V40 is BUILT and statically VERIFIED, **NOT FLASHED**. No CAN, UDS, or flash operation occurred.
**Supersedes:** V39 entirely — V39's code cave is dropped, not carried forward.

## On-car input that started this

V39 was FLASHED and **fixed neither symptom**:

1. **tens-of-Hz vibration/grinding**, worst near 5 mph. Operator refinement that turned out to be
   decisive: it happens when the comma is **rapidly commanded a small LKAS command that crosses zero**.
2. **several-Hz ratchet on hard turns** — the wheel feels able to turn harder but is intermittently stopped.

V39's only functional change was zeroing the direct Sensor-B torque-rate lane `r24`. That lane is
therefore falsified for both symptoms.

## Elimination

Every structural candidate except one was closed out this session, mostly by subagent traces that the
lead then re-verified against raw bytes:

| Candidate | Verdict |
|---|---|
| direct rate lane `r24` | falsified on-car by V39 |
| `gp-0x6acc` ±8192 collapse | **not reachable** — envelope 4762 + 2560 = 7322 vs boundary 8192 |
| `gp-0x6bd0` hysteresis-free sign flip | **no-op** — `gp-0x6abe` is a pinned literal 32767 in normal driving |
| `gp-0x67ac` aggregator mode bypass | **unreachable** — A160 source-mode array has no 2/3/4 |
| `gp-0x6ad4` resonance IIR | overdamped, both gains 4/1024, τ ≈ 256 cycles |
| **governor `FUN_0004503c`** | **stands** |

Two numbers in that table are corrections to claims made earlier in this same session:

- **`gp-0x6ad0`'s ceiling is 2560, not 4762.** The 4762 came from a subagent and was a conflation with
  governor cal `0xC6202` in an unrelated function. LERP2's real bytes at `0xC67D2..0xC67DC` are
  breakpoints 3200/3800/4150, output floor 512, **ceiling 2560**. This restores the model's original
  7322 envelope and is what makes the ±8192 collapse unreachable.
- **`gp-0x6abe` does not cross zero.** `FUN_00041464` writes it from a literal 32767
  (`movea 0x7fff,r0,r13` @`0x419de`) whenever `|gp-0x4f50| <= 13000` — all normal driving. It only
  carries a live signed value on the abnormal branch where the resolver rate already exceeds its own
  clamp (a branch that also resets the IIR accumulators). And `FUN_00034350` independently zeroes its
  own term when `|gp-0x6abe| > 13000`, so at the sentinel the sign flip is moot.

The survivor is the only candidate that predicts a vibration keyed to **zero crossings** rather than
command magnitude. Nothing else on that list explains why a *small* command vibrates.

## Root cause — one function, both symptoms

`m_motor_torque_governor` `FUN_0004503c`, all VERIFIED at the instruction level:

```text
sign-crossing reset  @0x45420-0x45436  TARGET and HELD opposite signs ->
                                       mov 0x0,r14 ; st.h r0,-0x138a[gp]   (accumulator ZEROED)
asymmetric slew      @0x4543a-0x4545e  r10=TARGET, r14=HELD. Motion AWAY from zero is capped to
                                       HELD +/- STEP; motion TOWARD zero is immediate/unlimited.
step selector        @0x45402-0x45419  gp-0x67f5==0 -> cal 0xC6206 (512), else cal 0xC6208 (205)
```

`gp-0x67f5` is written by the driver-torque voter `FUN_00041eec` (@`0x4222a`/`0x42258`/`0x42288`):
forced to `0xFF` with **no debounce** once raw driver torque diverges from the vote by ≥65 counts, and
debounced to 1 while voted `|torque| >= 640`. Both conditions hold during a hard dynamic turn, so the
step is **pinned to the slow 205 cal exactly in the regime where the ratchet is reported**.

So every zero crossing dumps delivered torque to zero and it must climb back at a fixed step. Command
magnitude is irrelevant; only crossing *rate* matters.

### The invariant V38 broke is RAMP TIME, not step size

The step cals are absolute counts and **no build has ever touched them**, but V38 raised the target ~4×:

| Build | LKAS-only target | slow-step cycles | +assist | cycles |
|---|---:|---:|---:|---:|
| V9 stock | 417 | **3** | 1441 | 8 |
| V38 | 1782 | **9** | 2806 | **14** |

Same class of error as the pre-V31 soft-EME lineage, where the invariant turned out to be absolute
margin rather than ratio.

## The rate cap, and why it is a capability change

The cap's axis is **motor resolver electrical-angle rate**, not road speed. Its A160 table tapers
5325 → 512 and its floor is 512.

**Stock V9's max LKAS demand is 417 — below the 512 floor, so stock LKAS can never be rate-capped at
all.** V38 (1782) is the first flashed build to clear that floor: it binds from z≈3414, and with base
assist in the aggregate from z≈2229. It cuts torque precisely when the motor turns fast, which is the
fast low-speed maneuver the operator wants.

**Flattening does not raise the ceiling.** The governor is `MIN(nominal 4762, adaptive LERP, budget B)`.
Flat Y = 5325 sits above 4762, so the adaptive arm never binds and the effective governor becomes
`MIN(4762, budget)` — 4762 at every rate, exactly what the motor already sees at low rate today. Two of
the three protection arms are untouched. Verified from the built image:

```text
z=1050   V38 4762   V40 4762
z=1700   V38 3584   V40 4762
z=2500   V38 2406   V40 4762
z=4100   V38  512   V40 4762
```

⚠ **A flat Y alone is not sufficient.** The cap evaluates `Y[i] + (((z - X[i]) * slope_q13) >> 13)`, so
leaving the precomputed Q13 slopes live would keep interpolating between flat points. V40 zeroes them.

## Safety verification (this is what gated the build)

- **Shadow is NOT value-sensitive — the last blocker, cleared at RAW INSTRUCTION level.** All three
  mode branches of `FUN_0007b022` (`gp-0x4e5a` ∈ {0,2,else}) perform a *stored-duplicate* consistency
  check, not an independent recomputation. The gating compare is OLD `gp-0x4f64` against OLD
  `gp-0x448a` **to each other**, never against table bytes; then one locally-computed register is
  stored to both addresses back-to-back with no intervening load:

  ```text
  0x7c2d2  ld.hu -0x4f64[gp],r16   0x7c2da  ld.hu -0x448a[gp],r7
  0x7c2de  cmp r7,r16              0x7c2e0  bne 0x7c2ec -> jarl FUN_0006b9ee (fault 0x17)
  0x7c2e2  st.h r9,-0x4f64[gp]     0x7c2e6  st.h r9,-0x448a[gp]      (same r9)
  branch 2: st.h r7  @0x7c3b4 / 0x7c3b8      branch 3: st.h r16 @0x7c47c / 0x7c480
  ```

  Independently byte-confirmed by the lead: in every branch the two stores share an **identical
  opcode halfword** (`644f`/`643f`/`6487`), which encodes the same source register — proving a
  register-level duplicate store rather than two derivations. Displacement bytes `9c b0` (`-0x4f64`)
  and `76 bb` (`-0x448a`) sit 4 bytes apart in each pair. The `-0x448a` displacement occurs 8 times
  image-wide, 6 inside this function; the shadow has no other writer.

  So the check trips only on RAM divergence *between* cycles, never on a calibration value.
  Flattening bank A cannot trip it. Fault `0x17` is hard-fault-eligible (motor off + power cycle),
  which is why this had to be settled before building. **VERIFIED, not inferred.**
- **No float mirror for either change.** Image-wide scan found no f32/f64 encoding of 5325, 2406 or
  1587 at raw or 1/1024 scale, and no matched 512/205 pair (205 has no float representation anywhere).
  The V27 int/float asymmetry class does not apply.
- **`0xFFFF` overflow cleared by trace, not assumed.** The cal is consumed as
  `iVar20 = (int)((uint)cal * (uVar15 & 0xffff)) >> 0xf`. `uVar15` comes from a chain of
  `FUN_00049a78` (an unsigned `min(a,b)`) seeded at literal `0x8000`, so it is provably bounded to
  `[0,32768]` and cannot be raised by a corrupted operand. Worst case `65535*32768 = 0x7FFF8000` <
  `0x80000000`: no sign flip.
- **Both bank-A copies patched byte-identically.** `FUN_0007b022`'s preamble reads *both* copies every
  cycle and builds two parallel parameter blocks; whether they cross-check is NOT ESTABLISHED. Given
  the V27 asymmetric-mirror precedent, they must never diverge.
- **Banks B/C left alone.** Byte-identical replicas at `0xF9E0C`/`0xF9E24`/`0xFAA0C`/`0xFAA24` (slopes
  `0xF9C30`/`0xF9C38`/`0xFA830`/`0xFA838`), unreachable from app `tp`, no coherent app reference. All
  bank-A displacements cluster inside `FUN_0007b022` (`0x7B0A0/A4/A8`, `0x7B0FA`, `0x7B1E8/EC`,
  `0x7B6AC`, `0x7B6E4`, `0x7B7B6`); no bank-B/C displacement appears anywhere in `0x7Bxxx`.
- ⚠ **The cap tables are in the CRC chain's ONLY gap**, `[0xC5000,0xC6000)` — 4096 bytes, uncovered.
  So no CRC recompute is needed, **but the bootloader's integrity check does not protect those bytes
  and the builder's exact-changed-byte assertion is the only safety net.** Treat it as mandatory.

## Artifact

```text
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V40-LKAS-4x-V38base-slew-off-ratecap-flat5325-0x13000-0x100000.rwd
```

| Artifact | SHA-256 |
|---|---|
| V40 RWD | `2f559e19085e901660c3f72ec0c7d19b066ebfe9977d56c3b9e5d52ae9ce56df` |
| `_v40_plain_image.bin` | `117aad4f65368acd77e480c4ba6f433bcbbe51f28104c100773e59b39fe3131b` |
| `_v38_plain_image.bin` baseline | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/build_v40_tva.py`. **CAL-ONLY — zero code edits, zero caves.**

## Edits — 40 bytes in 5 runs

| Address | Stock | V40 | What |
|---|---|---|---|
| `0xC6206` | 512 | 65535 | slew fast step (`tp+0x7206`) |
| `0xC6208` | 205 | 65535 | slew slow step (`tp+0x7208`) — the hard-turn case |
| `0xC5218` | `5325,3584,2406,1587,512` | `5325 × 5` | cap Y row, record copy 1 |
| `0xC5230` | `5325,3584,2406,1587,512` | `5325 × 5` | cap Y row, record copy 2 |
| `0xC5030` | `-21940,-12059,-5593,-22021` | `0,0,0,0` | Q13 slopes copy 1 |
| `0xC5038` | `-21940,-12059,-5593,-22021` | `0,0,0,0` | Q13 slopes copy 2 |
| `0xC6FFC` | `0x2A0A3DB1` | `0xE1D012FE` | cal-block CRC |

Left deliberately stock: governor nominal `0xC6202`=4762, shift `0xC5160`=13, all X breakpoints, record
counts and terminators, every V38 calibration, and the entire application code range.

## Verification performed

- 49/49 CRC blocks pass on the V38 baseline, the V40 plain image, and the decoded V40 RWD readback.
- Full-image diff, independently re-run outside the builder: exactly 40 bytes in the 5 runs above.
- Application code `[0x13000,0xBF000)` byte-identical to V38. Block `[0xF9000,0x100000)` byte-identical.
- Both bank-A record copies and both slope copies identical to each other post-patch.
- RWD decodes back to `_v40_plain_image.bin[0x13000:0x100000]` byte-for-byte.
- Golden model carries `Calibration.for_build("V40")` with executable self-checks for: V38 (not V39)
  lineage, 1-cycle ramp, cap never binding, flat-cap governor = 4762 at every rate, and the
  flat-Y-with-live-slopes trap.

## Road-test interpretation — score the two changes separately

- **Vibration gone, ratchet gone:** the governor slew was the whole story. Confirms the diagnosis.
- **Vibration gone, ratchet remains:** the slew fixed the zero-crossing chop; the residual ratchet is
  the rate cap or something downstream. Check whether hard turns now feel rate-limited rather than
  ratcheting.
- **Vibration remains:** the governor diagnosis is wrong and the elimination above has a hole. The most
  likely hole is `gp-0x6abe` — if `gp-0x4f50` routinely approaches 13000 during the 5 mph vibration,
  the "pinned sentinel" reasoning fails in practice even though it holds by construction. That needs
  live telemetry, not static analysis.
- **New roughness at high steering rate specifically:** the flat cap is implicated. The taper was doing
  real work; back off the cap before the slew, since the slew is what buys smoothness.
- **Anything faults:** back out entirely to V38 and report which DTC.

## Open / not established

- Whether `FUN_0007b022`'s two bank-A parameter blocks cross-check each other.
- Role of banks B/C.
- Whether a rate-of-change monitor on `gp-0x6ace` exists anywhere outside `FUN_00043e44`/`FUN_00042af8`
  (both checked, neither has one) — no image-wide sweep was done.
- Task scheduling rate is CONTESTED (100 Hz vs 1 kHz from the same `0.001`/`0.01` constants in
  `FUN_00043e44`). All cycle counts here are exact; **no wall-clock Hz claim should be made until an
  ISR/timer trace settles it.**
- The `SM1`/`SM2`-permanently-blocked finding (byte gates `0xC64CC`/`0xC64CD` = 3 on all builds
  including stock) came from decompiler pseudocode only and contradicts standing memory that
  underwrote V19. **Re-verify with raw disassembly before editing `0xC6422` or `0xC61DE`.**

## Correction to the kit's record

`0xC7C3C = 424` — cited in `CLAUDE.md` as the limp-path torque multiplier — is the `+0x1000` tp-base
slip. The real read site is **`tp+0x7c3c` = `0xC6C3C` = 1**, an identity pass-through, and the gate cal
is `tp+0x7c22` = `0xC6C22` = 25. Separately, `CLAUDE.md`'s note that the live control loop reads the
`0xF8000+` partition points at block `[0xFD000,0xFFFFC)`, which is **98.6% `0xFF` (erased)** in this
image and cannot hold live tables.
