# HANDOFF — 2026-07-21 — V43: the unfiltered residual lane, and the pole that was switched off

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V43 is **BUILT and independently VERIFIED, NOT FLASHED.** No CAN, UDS, or flash operation occurred.
**Supersedes:** the vibration narrative in `HANDOFF-2026-07-20-v42-state4-ratchet.md`. Its ratchet narrative stands and is now **confirmed on-car**.

## The V42 drive — a split result, and both halves matter

| Change | Result |
|---|---|
| **Change 1** — `0x454FE` `bne`→`br`, disabling the state-4 governor substitution | ✅ **FIXED THE HARD-TURN RATCHET.** The mechanism is now a **CONFIRMED root cause**, not a hypothesis. |
| **Change 2** — zero the r26 adaptive torque-rate gain surface | ❌ **No effect. `r26` is FALSIFIED.** |

Change 1 is the first symptom in this lineage traced to a specific branch and closed by a single-byte
edit. It is carried into V43 unchanged and is **not under test**.

Change 2's null is worth more than it looks. V39 zeroed `r24`; V42 zeroed `r26`. Those were the only two
Sensor-B torque-rate derivative lanes anyone had identified, so **the whole derivative family looked
eliminated** — a family-level negative neither build could deliver alone. That turned out to be wrong,
and the reason why is this session's finding.

## The operator's new datum — the most discriminating one this project has had

> Vibration is present in **all steering wheel movements driven purely by the LKAS**. When I assist the
> LKAS manually via the steering wheel, the vibration/grinding **goes away**. Confirmed at all speeds;
> audible as grinding only near 5 mph.

## A correction of record this forced immediately

The kit's central analytical tool, `gain_rescaling_invariance_analysis()`, had the vibration filed as
**"small command dithering around zero"**, which forced every search *upstream* of the gain. That premise
is contradicted: LKAS turning the wheel alone against tyre and rack load is a **large** command, and
driver assist *reduces* it. The correlation is large pure-LKAS command → vibration.

**The vibration lives in the same ">417-count, never-existed-before" downstream regime as the ratchet.**
Downstream stages went back in scope; the near-zero upstream candidates went out. Retracted in place.

## The mechanism — two independent traces converged

```
gp-0x4f60   RAW Sensor-B (TAS) column torque — a PHYSICAL sensor, unfiltered
     |
     |   errorterm = clamp( gp-0x4f60 − clamp(gp-0x6ad6, ±8192), ±0x2800 )
FUN_0003a382            gp-0x6ad6 (FUN_00037fe6) = a FEEDFORWARD MODEL of expected column torque
     |                  ⇒ errorterm is a MODEL-vs-REALITY RESIDUAL, recomputed every cycle
     |   Stage A: "lag", gain cal 0xC6450 = 1024 Q10  → PASSTHROUGH
     |   Stage B: windowed accumulator, adds L2(=98 flat) × errorterm RAW every cycle
     |   Stage C: RAW one-sample DIFFERENCE × L3(=2048 = 2.0 flat), then "lag" 0xC644A = 1024
     |            → ALSO PASSTHROUGH.  ⇒ Stage C is a pure DERIVATIVE — a HIGH-PASS, unattenuated
     v
gp-0x6ad4 → aggregator gp-0x6b94  (via a ±0x2800 ZERO-type gate)
     |
     v
gp-0x6b94 **IS the governor's slew target** — verified: `FUN_0004503c`'s first instruction @`0x453e0`
     |                                         is `ld.h -0x6b94[gp],r6`
     v
governor slew, whose STEP is DRIVER-TORQUE-GATED (see "held in reserve" below)
```

### The correction that unlocked it

The model recorded this lane's two lag stages as gain **4** — τ≈256 cycles, *"VERY heavily damped, i.e.
strongly overdamped rather than resonant… ARGUES AGAINST this lane resonating."*

**They are 1024.** Two agents, independently, with different tooling, byte-read cals `0xC6450` and
`0xC644A` in stock, V38 and V42: all give **1024 = Q10 unity**. At unity the update
`state += ((target*32 − state) * GAIN) >> 10` reduces to `state = target*32` **exactly** — a direct
assignment, not a lag. One reader sanity-checked its own addressing in the same dump by reproducing
`0xC6202 = 4762` and `0xC6204 = 3072` at their expected offsets.

**The lane is unfiltered, and the recorded verdict had been actively steering the investigation away
from it.**

### Why this survives the gain-rescaling invariance argument

That argument says every stage downstream of the gain replays stock's exact **counts**, because the
operator quartered openpilot's PID. It is an argument about **digital replay**. It says nothing about a
term sourced from a **physical sensor reacting to real delivered torque**.

Motor torque ripple (cogging, current ripple, backlash) scales with delivered torque — standard PMSM
behaviour. V38 delivers ~4× the torque for the same manoeuvre, so the **real** ripple on `gp-0x4f60` is
~4× larger, and this lane passes it essentially unattenuated. Nothing digital compensated, because the
amplification happened **in the plant**.

⚠ **This is the weakest link in the chain and should be treated as such.** It is `[INFERRED, physical]`
and disassembly cannot close it.

### Why no prior build moved it

V39 (`r24`), V41 (cap table) and V42 (`r26`) touch **none** of `FUN_0003a382`, `gp-0x6ad4`, `gp-0x6ad6`,
`0xC6450`, `0xC644A`, or L1/L2/L3. Same physical input family as r24/r26 — Sensor-B torque — reaching
the aggregator by a **completely independent, never-tested computational path**. Falsifying two of three
routes never falsified the family.

### A recorded elimination that has to be downgraded

**"Motor torque ripple is RULED OUT"** rested on: hand steering delivers comparable motor torque through
the same path and is smooth. Its comparison case is *always* measured with hands on the wheel — precisely
the damping condition under test. Identical excitation with different mechanical Q produces exactly that
observation.

The right conclusion was never "the motor is clean." It is **"the motor's ripple has a path back into
the torque command that nothing filters."**

## ★★ The vibration is MEASURED — route b9, the first post-V38 telemetry in this kit

12 segments, raw CAN 399 at 100.0 Hz (Nyquist 50 Hz).

**A sharp, isolated spectral peak at 21.02 Hz** in hands-off column torque — 41 hands-off LKAS-engaged
segments, 209 s, with the top five FFT bins all inside 21.00–21.09 Hz. A narrow line, not a broad hump.

**It is a V38 regression, measured** (route b9 vs routes 77/79, the 2× era, 201 s matched):

| band | V38 | pre-V38 | ratio |
|---|---|---|---|
| 0.5–5 Hz | 1131646 | 3044219 | **0.37×** — *lower* on V38 |
| 5–10 Hz | 1239069 | 878122 | 1.41× |
| 10–20 Hz | 1490254 | 707565 | 2.11× |
| **20–30 Hz** | **2794974** | **43905** | **63.66×** |
| 30–40 Hz | 100850 | 11717 | 8.61× |
| 40–50 Hz | 115255 | 23783 | 4.85× |

The 0.5–5 Hz band going **down** is a strong internal control: it is exactly what gain-rescaling
invariance predicts from the quartered PID, and it proves the 64× is not a global scale factor.

**The hands-off discriminator, speed-matched** (19–23 Hz) — this removes the speed confound that made
the pre-V38 numbers uninterpretable:

| speed | hands-off | assisting | ratio |
|---|---|---|---|
| 2–10 mph | 137668138 | 437839 | **314×** |
| 10–20 mph | 92378641 | 868225 | **106×** |
| 20–30 mph | 29087505 | 386860 | **75×** |

**A refinement of the operator's report, in their favour:** the peak is present at every speed but is
~10× *stronger* at low speed, and its ratio to the 0.5–5 Hz control band falls 21.5× → 1.0× from
2–10 mph to 30–45 mph. So it is not purely road-noise masking that makes it audible near 5 mph — it
genuinely is strongest there, consistent with low speed demanding the most motor torque.

⚠ **Two caveats.** (i) **Aliasing** — at 100 Hz sampling, 21.02 Hz is indistinguishable from 78.98 Hz.
This does not weaken the fix: a higher true frequency receives *more* attenuation from the same pole, so
designing against 21.02 Hz is the conservative choice. (ii) **Stability** — a peak holding 21.02 ±0.05 Hz
across 41 segments and a whole drive is remarkably stable for a mechanical resonance, which would
normally drift with load and temperature. Weak evidence for a clock-derived origin. `[OPEN]` — it does
not change the fix, but it would change the story.

## The edit — add a pole, do not remove a term

**`0xC644A`: 1024 → 64.** One calibration halfword.

`0xC644A` (read @`0x3a860` `ld.hu 0x744a[tp],r11`, consumed @`0x3a86c`) is the EMA gain on state
`gp-0x3680`, whose target is `clamp(FACTOR_D * (TARGET_RAW − gp-0x3684_prev) >> 10, ±0x2800)` — and
`gp-0x3684` is a **pure one-sample delay**, rewritten unconditionally every cycle (`0x3a840`). So
`0xC644A` is the pole sitting **immediately downstream of a raw discrete difference**: the classic
**"dirty derivative"** pole — and it is calibrated to unity, i.e. **switched off**.

A raw one-sample difference is an *unbounded differentiator*. Every real controller band-limits one.
Lowering this gain restores the pole.

**Value chosen from the measured 21.02 Hz peak.** An earlier draft used 64, picked when the symptom
band was *assumed* to be 30–50 Hz. That assumption is falsified by the data, so the constant is corrected:

| GAIN | atten @21.02 Hz | cost @3 Hz | DC residual |
|---|---|---|---|
| 128 | 1.41× (−3.0 dB) | −0.09 dB | ≤0.25 cts — too timid |
| 64 (old) | 2.28× (−7.1 dB) | −0.36 dB | ≤0.50 cts — calibrated to a wrong band |
| **32 (chosen)** | **4.28× (−12.6 dB)** | **−1.31 dB** | **≤1.00 cts** |
| 16 | 8.44× (−18.5 dB) | −3.86 dB | ≤2.00 cts — too much |

The 3 Hz cost is smaller than it looks: it applies to **Stage C's own contribution only** — one sub-term
of one lane among several. The LKAS command lane itself is untouched. If the true frequency is the
78.98 Hz alias instead, GAIN=32 gives −23.8 dB.

⚠ **Land this against the CYCLE column.** The 1 kHz tick is `[INFERRED]` from the OSTM0 reload and has
never been proven — specifically not for this function's call rate.

### Why *this* edit and not zeroing L3

**The sign of Stage C could NOT be settled from the bytes.** Every coefficient in `FUN_0003a382` is
positive and no branch conditionally negates Stage A/B/C; the only sign-bearing operation is the final
polarity multiply by `gp-0x6752`. Resolving the sign needs that byte's runtime value **and** a physical
wiring convention — the same irreducible gap already on record for r24/r26.

Zeroing the term would therefore be a gamble: a residual-feedback derivative is **classically an active
damper**, and this kit has *already removed derivative feedback twice* (V39, V42) while chasing this
vibration. **Band-limiting does not care about the sign.** Damping or anti-damping, it preserves the
low-frequency action and removes only the tens-of-Hz content.

The risk is also bounded independently: `gp-0x6752` is the same byte scaling boost, r24, r26 and every
other assist lane, with no lane-specific inversion anywhere in `FUN_0003a382`. Whatever convention makes
the already-flashed, road-validated lanes work, this lane inherits.

### The safety case

- **DC gain preserved to within a bounded, one-sided, sub-count residual.** In real arithmetic
  `state = target*32` is the fixed point for **any** nonzero GAIN, so GAIN sets only the settling time.
  In the *actual* integer arithmetic this is **not exact**: V850 `sar` floors toward −∞, so approaching
  the target from *above* converges exactly while approaching from *below* can stall within
  `(target − 1024/GAIN, target]`. The residual is therefore real, **one-sided** (it under-reports a
  sustained *rising* derivative, never over-reports), and bounded by **≈ 32/GAIN counts** at the output:

  | GAIN | max residual |
  |---|---|
  | 1024 (stock) | ≤0.03 counts |
  | 128 | ≤0.25 counts |
  | **64 (chosen)** | **≤0.5 counts** |
  | 32 | ≤1.0 counts |
  | 16 | ≤2 counts |

  Sub-count at the chosen value, against a lane contributing an estimated 150–250 counts and a
  1782-count LKAS reference. **Verified two ways that agree**: direct integer simulation (measured 15
  state-counts at GAIN=64) and an analytic bound (`1024/GAIN` = 16 state-counts). The simulation
  reproduced the asymmetry *before* the analytic explanation existed, so the two are a genuine
  cross-check rather than one restating the other.
  ⚠ **This bounds how far the lever can be pushed:** below roughly GAIN=16–32 the residual stops being
  negligible and becomes a real few-count bias. Do not push past 32 without accounting for it.
- **No lockstep, no monitor.** `gp-0x6ad4` has **exactly two touches image-wide** (writer @`0x3a8a0`,
  aggregator reader @`0x3aca8`). `FUN_0003a382` contains **zero `jarl`** — a pure leaf function, so
  nothing inside it *can* raise a shadow-mismatch fault. A direct scan finds **no `-0x4c` displacement**
  anywhere in the function, so none of `gp-0x6ad4`/`0x367c`/`0x3680`/`0x3684`/`0x3688` is mirrored.
- Both reads are `ld.hu` (unsigned) — no analogue of the `0xC61B8` dual-signedness trap at these sites.
- 🛑 **GAIN = 0 IS DEGENERATE** — the state freezes and never converges. It is *not* "just slower."
  Never round a candidate down to zero. The builder asserts `gain > 0`.

## Held in reserve — the V44 candidate

**The governor slew-STEP selector `gp-0x67f5` is real, verified, and driver-torque-gated:**

```
vote of gp-0x6a5e >= cal 0xC531E (1062), debounced cal 0xC64E7 (10 cyc) -> STEP = 205  (hands ON)
                  <  1062                                               -> STEP = 512  (hands OFF)
```

A per-cycle slew limit is a **bandwidth gate** (`f_corner = STEP·tick / 2πA`), so hands-off the command
path is **2.5× wider**. And the corner scales as 1/amplitude: at stock's 417-count LKAS lane it sits at
~195 Hz; at V38's 1782 it falls to **~46 Hz**. **V38 is the first build where this limiter binds in the
symptom band at all** — an independent retrodiction of the onset.

Not shipped in V43 because it touches the **main torque command path** (the same cal V40 catastrophically
mis-set), attenuates only ~2.5×, and slows LKAS response. The pole has a strictly smaller blast radius.
A safety review attacked the `0xC6206` 512→205 edit and **could not break it** — notably `FUN_0004595a`,
the only monitor comparing output against target, explicitly *tolerates* output lagging target, which is
the direction slower tracking produces. It is ready if V43 nulls.

## Recorded, deliberately NOT shipped

**A one-sided gate makes the damping term half-blind.** `FUN_00034350` → `gp-0x6bd0` is true damping
(sign verified: `term = −sign(gp-0x6abe)`), and it is **live in normal driving** — a standing memory note
had the producer's branch polarity backwards. But:

```
0x345fa  ld.hu -0x6ac0[gp],r14      <-- UNSIGNED load of a SIGNED quantity
0x34602  bc 0x34612                 <-- zero the term if r14 >= 12999 unsigned
```

`gp-0x6ac0` is signed, clamped ±13000. Read unsigned, **the damper is unconditionally zero for one
rotation direction** — and during a tens-of-Hz oscillation the motor rate alternates sign every half
cycle, making this a **half-wave-rectified damper**.

**Not fixed in V43.** Correcting it would make a term active in a direction where it has never been
active in **any** build including stock. This kit's rule — the one that made V42's branch flip safe — is
**widen an already-live path, do not invent one**. It also measures *motor*-side rate, on the wrong side
of the torsion bar to damp a wheel-side mode. For a later, separately-scored build.

## Candidates eliminated this session

| Candidate | Eliminated by |
|---|---|
| `r26` adaptive derivative lane | **V42 on-car** |
| soft-EME wall / boost-latch relaxation oscillator | hands-off wall ≥5120 vs max command 4342–4608 → integrator never winds → latch cannot bootstrap |
| governor energy/thermal budget | **provably unreachable**: charges above 5325, but delivered torque is structurally bounded by the 4762 governor ceiling |
| deadband + sign latch (`0xC64A3`/`0xC61B8`) | gate is live only while `STEER_STATUS==3` = the low-speed lockout, **0% above 4 mph across 98k CAN-399 frames** |

## Artifact

```
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V43-LKAS-4x-V38base-state4-ratchet-off-derivative-pole32-0x13000-0x100000.rwd
```

| Artifact | SHA-256 |
|---|---|
| V43 RWD | `a039af1368d80e0996651e5b9a3c9c3c1c680c416df2d6ae445a60b0ca5f461f` |
| `_v43_plain_image.bin` | `5ecfddcbd74c3508e0353d8ba6065bd866aaa0ac48bdf549dc8822ba7a0adccc` |
| `_v38_plain_image.bin` baseline | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/build_v43_tva.py`. To fall back to the conservative corner, change the
single constant `POLE_NEW = 32` → `64` and rebuild.

## Verification performed

- **V43-vs-V38 = exactly 11 bytes in 4 runs**: `0x454FE` (1B) + `0xC644A`–`0xC644B` (2B) + two 4-byte
  CRC trailers. Both edits asserted to exact values, and the allowed byte-set asserted, not just a count.
- Bootloader walk **49/49** and full chain **50/50** on baseline, V43 image, and decoded RWD readback.
- Branch **target** decoded before and after — unchanged at `0x455C4`; displacement untouched.
- No external Bcond or `jr` enters `[0x45500,0x455C4)`.
- **V42's Change 2 asserted REVERTED** — r26 Y rows, X rows and both override cals verified back at
  stock, with a positive sanity check that they *were* zeroed in V42 (so the revert is real, not a no-op).
- 13 tracked calibrations asserted stock, including `0xC6206`/`0xC6208` (the V44 candidate must not be in
  this build) and `0xC6450` (the proportional-branch sibling pole, deliberately left at unity).
- `FUN_0003a382`'s L1/L2/L3 tables asserted stock — the pole must be the **only** change in this lane, so
  that a null falsifies the pole and not a second simultaneous edit.
- The integer-EMA DC-preservation claim asserted **inside the builder** and re-derived independently.
- **Re-verified outside the builder sharing no helper**: diff, Bcond decode, CRC chain walk, cal reads and
  the EMA simulation all re-derived from first principles. All pass.

## Open

- ✅ **CLOSED — the read-site scan came back clean.** An exhaustive operand/text scan over all **185,693
  analyzed instructions** (a figure matching a prior independent sweep, and reported `truncated: false`,
  `scope: program`) found **exactly ONE read of `0xC644A`** (@`0x3a860`) and **exactly ONE of `0xC6450`**
  (@`0x3a7f0`), both `ld.hu` (unsigned), both inside `FUN_0003a382`. The absolute-address form was
  searched too, in case of a `movhi`/`movea`-materialised read — none exists. **No `0xC61B8`-style
  signed/unsigned split for either cal.** All four internal states (`gp-0x367c/3680/3684/3688`) have
  **zero** reads outside `FUN_0003a382`. Every raw hit was individually inspected with its exclusion
  reason stated, so this is a *verified* zero, not a tool zero — and it was obtained by a method
  independent of the xref engine that had returned a misleading zero.
  ⚠ One item flagged rather than asserted inert: three `movhi -0x3680,r0,rX` sites in `FUN_00030c26` /
  `FUN_00032234` reuse the identical immediate for an unrelated purpose. Wrong opcode class (`movhi`
  builds an upper-half immediate; no `gp` operand, no load), so structurally not accesses of
  `gp-0x3680` — but what absolute address they *do* build was not traced.
- ✅ **CLOSED — no shadow float path exists for the driver-assist chain.** This was raised as a late
  challenge and it was the right one to raise: the standing "raising a clamp translates both sides"
  justification is about **clamps**, and V43 changes **dynamics**. Had any float path re-derived the
  aggregate from float sources with its own filtering, a lag on the integer side alone would open a
  V27-class divergence that no clamp edit could.
  It is clear, for a structural reason. `FUN_00043e44` (the only int/float lockstep function in this
  region) reads `gp-0x6acc`, `gp-0x6b98` and `gp-0x6bf0` as **integers and converts them**; `gp-0x6b94`
  does not appear in the function at all; and **none** of the aggregator lanes — boost, damping,
  friction, return-to-centre, r24/r26, or `gp-0x6ad4` itself — appear anywhere in it. What the float
  side genuinely re-derives is the **WALL/bound** (its own float LERP tables `tp+0x75d4`,
  `tp+0x7648-0x767c`, `tp+0x7594-0x75c4` and its own float lag state `gp-0x3554`/`gp-0x3558`), whose
  inputs V43 does not touch.
  **The generalisation, which outlives V43: the assist chain is integer-only end to end.** `gp-0x6acc`
  and `gp-0x6b98` are read fresh as integers every cycle with no memory of how they were computed, so
  the float side has no independent expectation of their value. There is only ONE computation of the
  assist/aggregate quantity, and nothing can fall out of step with it because no second path exists.
  **The int/float discipline in this firmware guards BOUNDS, not the COMMAND.**
  ✅ **The image-wide float-mirror residual is now also CLOSED, on two independent grounds:**
  1. **`FUN_0003a382` contains ZERO floating-point instructions** — 468/468 instructions scanned for any
     FP mnemonic (`mulf`/`addf`/`subf`/`divf`/`cvtf`/`trfsr`/`trnc`), zero hits. It is a pure-integer
     function, so nothing in this lane could read a float mirror even if one existed.
  2. **`0xC644A`/`0xC6450` sit in ordinary integer cal space.** Float-reinterpreted in place they read
     `-1.435e-42` — denormal garbage, the signature of bytes never meant to be read as a float. The
     genuine float-cal complex begins ~0x110 bytes later at `0xC6560`, is uniformly clean engineering
     constants, and is now fully mapped and attributed (below).
  **Float-cal complex map, `0xC6560`-`0xC668C`** (count-prefixed sub-tables): `0xC6598/9C` = `5.0f`
  corridor upper mirror (int `0xC674E/50` = 5120 ✓); `0xC65AC/B0` = `-5.0f` corridor lower (int
  `0xC675A/5C` = −5120 ✓); `0xC65C4/C8/CC` = `5.0f ×3` boost mirror (int `0xC6768/6A/6C` = 5120 ✓);
  `0xC6664`-`67C` = `1.0f ×7` LERP_B envelope. Every entry attributed to a known table.
  ⚠ One cluster was flagged unattributed — `0xC6634`-`40` = `0.25f ×4`. **Checked and excluded:** it is
  *not* a mirror of any `FUN_0003a382` table. L1 = `[0.25, 0.25, 0.2197, 0.1494]` — the first two match
  but the last two do not; L2 = `[0.0957 ×4]`, L3 = `[2.0 ×4]`, L4 = `[1.0 ×3]`. A casual comparison
  against L1's leading values would have produced a false match; the full row rules it out.
  Also confirmed: `gp-0x6bf0` (23 genuine touches across 13 functions) and `gp-0x6bbe` (8 touches) are
  **all `ld.h`/`st.h` 16-bit signed integer** — no float twin, no `gp-0x6dXX` companion, verified zero
  with every hit adjudicated.
  ⚠⚠ **REOPENED — THIS GATES THE FLASH. An earlier revision of this document closed it; that was
  premature and both supporting arguments are retracted. See the retraction note below.** `fVar23` traced to
  concrete registers and cross-checked against the kit's existing
  `reference_accord_eme_bit32_float_monitor.md`, which had already characterised this exact structure at
  these exact addresses — independent corroboration, not a re-derivation:
  `cmd_final` = `clamp( gp-0x6dac + [gp-0x6b04 | gp-0x6acc-rooted consensus], floor, 9.0 )`, compared at
  `0x448de` against `gp-0x6b98/1024` with a ±5/1024 (≈±5 count) tolerance.
  **Two of the three summands are traced safe** — `gp-0x4f64` (`ld.hu`) and `gp-0x6b04` (`ld.h`), and
  the selector's alternate branch roots in the same `gp-0x6acc` int-conversion. Those shift with V43.

  **`gp-0x6dac` is the third, and its writer is UNLOCATED.** Excluded by full decompile: `FUN_00043e44`
  itself (one occurrence, the read, no store), `FUN_0004503c` (the governor — pure fixed-point, zero
  float instructions), `FUN_00037fe6` (producer of `gp-0x6ad6` — also pure fixed-point).

  ### ⚠⚠ Retraction — two arguments used to close this were wrong

  **[RETRACTED] "`gp-0x6dac` is a small untouched additive offset, so V43 shifts both sides
  identically."** Wrong on magnitude. It is gated to ~±10 and `cmd_final` clamps at 9.0 — up to ~10240
  counts, **full command scale**, not a trim term. And the comparison is tight: `cmd_final × 1024` must
  match the delivered demand within **5 counts**. That is a close *expectation* of the delivered value,
  not a loose bound, so "additive offset" was never a safe reading.

  **[RETRACTED] "V43 smooths the command, so any pipeline-lag residual shrinks — it moves the monitor
  toward its safe side."** Only valid if the float side is *not* independently tracking the command. If
  `gp-0x6dac` is a float tracker with its own filtering, adding a lag to the integer side and not the
  float side makes them diverge **more** during transients — exactly backwards.

  So the case turns on what `gp-0x6dac` is:
  - **(b)** wall/bound/envelope-adjacent, or otherwise not command-tracking → additive → **V43 clear**
  - **(c)** an independent float re-derivation of the command with its own filtering → **V43 needs rework**

  Suggestive but **not** evidence: `gp-0x6dac` sits immediately adjacent to `gp-0x6db0`/`gp-0x6db4`/
  `gp-0x6db8` (the known float corridor twins and the LERP_B velocity clamp), and the kit's
  `reference_accord_eme_bit32_float_monitor.md` already labels it *"speed-scaled float"* at this exact
  address. Adjacency plus an unverified label is not a trace. **Do not close on them.**

  ### ⚠ Third retraction — the "127 < 128" backstop was much weaker than stated

  It was offered repeatedly as *"even all seven flags true cannot trip it."* Reading the dwell SM
  properly: **any single flag held for ~10 consecutive cycles** drives state 2 → 3, which adds `1024.0`
  and trips. `127 < 128` only rules out a **single-cycle** trip. Weight-32 firing continuously for 10
  cycles **is** motor-off. That makes this item more consequential, not less, and the margin should not
  have been cited as reassurance.

  ### ✅ Resolution — `gp-0x6dac` traced: verdict **(b)**, not command-tracking

  Single write site image-wide (adjudicated: 8 raw hits, 6 branch-target coincidences excluded with
  reasons, 1 read @`0x4487a`, 1 write): `0x42af2 st.w r6,-0x6dac,gp` in `FUN_00042adc` — a thin
  sanitizing setter whose **only** caller is `FUN_00027b0a`, a **multi-channel sensor redundancy /
  plausibility monitor** over a separate address family (`gp-0x61xx/62xx/63xx`) with its own DTC set
  (`0x3d00-0x3d04`, `0x3ce6-0x3cff`, `0x4157-0x4158`). Same *kind* as the 5-channel torque voter
  `FUN_00041eec`, different instance, different channels. Tail: `gp-0x6dac = clamp(agreement score, ±10)`.
  **Its inputs never touch `gp-0x6acc`, `gp-0x6b98`, `gp-0x6b94`, `gp-0x6ad4`, or anything downstream of
  the shaper/governor — so it cannot depend on V43's edit at any hop.** That is the (b) branch.
  *(The kit's `reference_accord_eme_bit32_float_monitor.md` labelled this "speed-scaled float" — wrong on
  the physical description, right on the classification. Corrected in place, since a wrong label left
  standing is exactly what cost this project multiple builds via the `FUN_0003a382` gain-4 error.)*
  ⚠ [OPEN, minor] `FUN_00027b0a`'s ~150 lines of channel arithmetic were not replayed literal-by-literal;
  the classification rests on its structure plus **zero references to any torque-command address**.

  ### Supporting arguments — these now corroborate rather than carry the verdict

  The accumulator (owned by this watchdog) is

  ```
  ∫ ( clamp(gp-0x6acc, ±12) − gp-0x4f60/1024 )
      ^ COMMANDED torque        ^ RAW Sensor-B column torque (direct, ±25 sanity, unfiltered,
        (downstream of V43)       untouched by V43)
  ```

  It measures **how well the plant follows the command**. Stage C injects fast content the plant *cannot*
  follow — that unfollowable content **is** the vibration. Removing it makes the command **more**
  followable, so the residual **shrinks**. Sized against the 5-count (`0.004883`) epsilon, for ripple
  amplitudes 100/300/1000 counts at 20/30/50 Hz, the change is **2.7× to 100× the epsilon and is a
  reduction in every case**. The *direction* is robust to the ripple amplitude (an explicit guess — no
  telemetry exists); only the magnitude is not.

  **The empirical proof-point outranks all of the above: V38 is FLASHED and FAULT-FREE with this lane
  fully unfiltered. V43 only attenuates it.** V43 cannot make the command less followable than V38's
  already is. A lag also cannot open a new command-vs-sensor gap, because the sensor responds to the
  *delivered* command — delay the command and the response delays with it.

  ⚠ [OPEN, detail-level, does not change the conclusion] Two tracers disagree on `fVar23`'s exact
  decomposition: `gp-0x6dac` (@`0x4487a`) vs `gp-0x6dc8` as the persisted term; MIN vs ADD at the
  combine; clamp ceiling 8.0 vs 9.0. They **agree** on the load-bearing structure — governor cap, a
  shaper-sibling term (`gp-0x6b04`, whose only two writers are inside `FUN_00042af8`, the same shaper
  producing `gp-0x6acc`/`gp-0x6b98`), and a persisted accumulator, compared against delivered within 5
  counts. Worth reconciling before anyone edits in this region; not worth holding V43 for.

  📌 **Process note, worth more than the bytes.** The sub-agent running this trace refused to round
  "2 of 3 inputs traced safe, 1 unlocated" up to a clean verdict, and re-sent its finding when it
  thought the caveat had been lost. The lead had already propagated the premature closure into this
  document. This kit's own standing lesson — *a verifier and the assertion that checks it must not share
  an assumption*, from V40's `assert_crc_gap_is_real()` — applies to summaries too: here the caveat was
  correct and the summary was not.

- 🟡 **[SOFT] First independent-ish evidence for the 1 kHz tick.** `tp+0x74e3`'s byte-to-float scale is
  `*0.001` — the firmware's own float math treats one cycle unit as ~1 ms. `[INFERRED]`, not a
  resolution, but more than this kit had. Every Hz figure here still rests on the unproven assumption;
  the cycle-domain figures do not.

- **No post-V38 driving telemetry exists anywhere.** Route `807a3c21c9f405e8_000000ac` (2026-07-19 00:26
  UTC, almost certainly V38) is on disk but **segment 0 only — the parked pre-drive segment**. Every build
  since V38 has been designed against the felt report alone. Pulling **segments 1+** would give the first
  V38-era data in the kit; CAN 399 samples at exactly 100 Hz, so tens-of-Hz content is observable to 50 Hz.
  Analysis script is written and ready.
- The **sign of Stage C** — sidestepped by this edit, but still needed before any *zeroing* of L3.
- The **±0x2800 zero-type gate** on `gp-0x6ad4`: out-of-window contributes exactly 0, not a clipped value.
  Whether realistic magnitudes approach that boundary is unknown; if they do, it is a chatter generator in
  its own right. The pole reduces peak excursions, so it moves *away* from this risk.
- **Task rate in Hz** — still unresolved, still blocking every cycles→time conversion.

## Recommended order

1. ✅ **All three verification gates are now closed** — the `0xC644A`/`0xC6450` read-site count, the
   shadow-float-path question, and the weight-32 monitor input. Flash only on explicit operator
   instruction naming the file and bus.
   ⚠ Note the weight-32 item was closed, **prematurely reopened by the lead's own over-claim, then
   closed again on a different and better argument**. The final basis is physical (V43 removes command
   content the plant cannot follow, so the command-vs-sensor residual shrinks) plus the empirical
   proof-point that V38 already runs this lane unfiltered and is fault-free — **not** the arithmetic
   "additive offset" argument, which is retracted, and **not** the "127 < 128" margin, which is also
   retracted as far weaker than it was stated.
2. Score the ratchet and the vibration **separately**. The ratchet should stay fixed (Change 1 is
   unchanged and confirmed); if it regresses, something is wrong with the build, not the theory.
3. If the vibration is unchanged: the residual lane is falsified, and **the governor STEP selector
   (`0xC6206` 512→205) is the V44 candidate**, already safety-reviewed.
4. If the vibration is reduced but not gone: step `POLE_NEW` 64 → 32, or stack the V44 candidate.
5. `STEER_DELTA 3 → 0.75` remains a free, reversible road experiment — but run it **separately**, never
   alongside a firmware vibration change.
