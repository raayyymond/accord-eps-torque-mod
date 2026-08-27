---
name: reference-accord-fun34350-damping-term-live-and-gated
description: FUN_00034350/gp-0x6bd0 damping term - sign source gp-0x6abe is ALWAYS live (its 0x7fff pin is structurally unreachable, producer chain clamps to exactly +-13000), gp-0x6ac0 is a magnitude not a bipolar signal (no half-wave bug), and the alpha=37/128 filter's phase lag at 21Hz (~18-40 deg depending on the kit's unresolved task rate) stays well under the 90 deg anti-damping threshold - mechanism is structurally sound for damping a 21Hz oscillation.
metadata:
  type: reference
---

`FUN_00034350` writes `gp-0x6bd0`, the aggregator lane this kit calls "damping" — product of 5
mode-indexed LERP gain factors (pointer tables @0xC9CCC/C9E9C/C9DB4/C9F84/C77A0, mode=10 for this car),
sign-flipped and gated to zero based on `gp-0x6abe`.

**Sign [VERIFIED, `0x3469e-0x346a2`]:** `if (gp-0x6abe > 0) term = -term`. The unflipped product is
non-negative (built from unsigned LERP outputs), so `term sign = -sign(gp-0x6abe)` — genuine viscous
damping in form, not anti-damping.

**★ CORRECTION — `gp-0x6abe`'s producer gate polarity was recorded backwards in an earlier session/note.**
`gp-0x6abe`'s producer is `FUN_00041464` (same function that produces `gp-0x6ac0`). Traced the bVar2 gate
at the instruction level (`0x415be-0x415ce`, `r15=gp-0x4f50` the resolver-rate IIR):
- `r6=1` (bc NOT taken, i.e. `|gp-0x4f50|` roughly within ~13000 = **NORMAL driving**) → branches to
  `0x4169c`, which computes a live lag-filtered copy of `gp-0x4f50` (gain = cal `0xC643C`=37, Q7 shift)
  and stores it live: **`0x417a0 st.h r24,-0x6abe[gp]`**.
- `r6=0` (large/abnormal rate) → branches to `0x41902`, which **pins `gp-0x6abe` to `0x7fff` (32767)**
  at `0x41a18`.
So: **normal driving → `gp-0x6abe` LIVE; abnormal (rate already saturating) → pinned, which then trips
`FUN_00034350`'s own `|gp-0x6abe|<~13000` gate and zeroes the term.** `FUN_00034350`/`gp-0x6bd0` is
therefore NOT structurally dead in ordinary driving — it actively computes and sign-flips. Verified twice
(decompile pseudocode, then raw disassembly register trace) because it reverses a prior claim.

~~**Former finding — one-sided gate on `gp-0x6ac0` [VERIFIED, `0x345fa-0x34602`]:** `ld.hu -0x6ac0[gp],r14`
(UNSIGNED load) then `bc` zeroes the whole term if `r14>=12999` unsigned. `gp-0x6ac0` is established
elsewhere as SIGNED, clamped ±13000 (motor resolver rate). Reading it unsigned means the term only ever
fires for `gp-0x6ac0` in `[0,12998]` — one rotation direction — and is unconditionally zero for the other
half (reads as a huge unsigned value). Same "signed value read via unsigned compare" idiom as the
shaper's one-sided ±8192 gate ([[reference_accord_shaper_fun42af8]]), new location.~~
**★★★ 2026-07-20 THIRD correction — RETRACTED. `gp-0x6ac0` is NOT a bipolar signed quantity; it is a
magnitude, non-negative by construction.** `FUN_00041464`'s own production write to `gp-0x6ac0`
[VERIFIED disasm `0x41666-0x4166e` (abs) + `0x41818-0x41836` (store)] is `gp-0x6ac0 = abs(uVar16_filtered)
>> 10` — `abs()` applied BEFORE storage, on both the debug and production sub-branches. A non-negative
signed short and its unsigned reinterpretation are bit-identical, so `ld.hu` at `0x345fa` changes nothing
— there is no bipolar signal there to half-wave-rectify. The "SIGNED, clamped ±13000" characterization
in the retracted paragraph above conflated `gp-0x6ac0` with `gp-0x4f50`/`gp-0x29c4` (which genuinely are
signed and share the same `±13000` clamp bound, one hop upstream in the same producer function) — an easy
mix-up since both are written in the same tight quad-block of `FUN_00041464`. There is no half-wave gate
here. (The `bc`-taken branch, `gp-0x6ac0>=13001`, is separately unreachable anyway — see the pin-clamp
proof below.)

**Which velocity [VERIFIED]:** both the sign signal (`gp-0x6abe`) and the magnitude gate (`gp-0x6ac0`)
derive from `gp-0x4f50` — established elsewhere (7-hop governor trace) as MOTOR resolver electrical-angle
rate, not column/torsion-bar rate and not `gp-0x4f62` (Sensor-B torque rate, the r24/r26 lane). This term
measures and reacts on the motor side of the assist point, not the wheel/driver side.

See also [[reference_accord_fun3a382_resonance_lane_unfiltered_correction]] — the OTHER "damping"-labeled
term in the aggregator, corrected the same session (gain 1024 not 4, i.e. unfiltered not heavily lagged).

**★★ 2026-07-20 re-verification — LIVE-in-production CONFIRMED by an independent exhaustive sweep, one
correction to the gate's polarity framing.** A separate session re-derived this from scratch (29 raw hits
on `search_instructions("6abe")`, one false hit excluded — `FUN_0006a9ca@0x6abde` is a `be` branch whose
*target address text* "6abee" coincidentally contains "6abe", not a memory access) and confirmed all 4
`st.h -0x6abe[gp]` writers are exclusively in `FUN_00041464` (`0x41790`/`0x417a0`/`0x419f8`/`0x41a18`).

- **★★★ 2026-07-20 SECOND correction (retracting the "one-sided" note above) — the bVar2 selector IS
  `|gp-0x4f50| > 13000`, a genuine symmetric magnitude test.** The one-sided reading was WRONG; a teammate
  challenged it and it did not survive re-derivation. Ground truth is Ghidra's own pcode for `0x415be-0x415ce`
  (not hand-decoded V850 carry flags, which is where the original error came from): `INT_ADD(r15,13000)`
  → `PTRSUB(0,0x6590)` (materializes the literal 26000 — this is *why* the decompiler renders it as a
  bogus `&DAT_00006590` pointer compare, a Ghidra typing artifact, not a real pointer) → **`INT_LESS(26000,
  r11)`**, i.e. `unsigned(r15+13000) > 26000`. `INT_LESS` is pcode's canonical *unsigned* comparison, and
  the two-`addi`/`setfnc`/`bc` asm idiom is exactly the standard `unsigned(x+K) <= 2K ⟺ -K<=x<=K` trick —
  its whole point is a symmetric window *without* an explicit `abs()`, so "no abs() visible" is NOT
  evidence of one-sidedness here (unlike the genuinely one-sided gates elsewhere in this kit, e.g.
  [[reference_accord_shaper_fun42af8]] — that pattern is real, it just doesn't apply to this instruction
  sequence). Numeric check: r15=-20000→r11=-7000→unsigned≈4.29e9>26000→PIN (correct, |x|>13000); r15=-13000
  →r11=0→not>26000→LIVE (boundary, |x|=13000 inside); r15=+15000→r11=28000>26000→PIN. Symmetric, confirmed.
  Boundary is `|gp-0x4f50| >= 13001` pins, `<= 13000` live.
  **Methodological trap hit and avoided along the way:** a same-offset Ghidra `unique`-space varnode
  (`cc00`) reused ~300 bytes later at the `0x41696` branch is NOT proof of the same logical value —
  `unique` slot IDs get recycled once a prior value's live range ends. Do not chain identity through
  reused unique-varnode IDs across long address spans; anchor conclusions on adjacent/unambiguous
  instruction pairs (here: the LOCAL `0x415ce` branch whose target `0x415f2` is one hop from the
  decompiled `if(bVar2){uVar16=0}` label) or on independent corroboration (here: the debug-magic sub-branch
  at `0x416d8-0x416fc`, inside the `0x4169c`-initiated region, multiplies by `r15`/`iVar13` — matching the
  decompiled **`else`** (bVar2==FALSE) branch's formula exactly, not the `if`-branch's literal-`0x7fff`
  formula — which is what actually pins down that `0x4169c`→LIVE / `0x41902`→PIN, independent of the
  unique-varnode question entirely).
- **Production-configuration PROVEN, not assumed:** both writers additionally sit behind a
  shadow-lockstep check (`gp-0x6abe` vs shadow `gp-0x4cc2`, mismatch → `FUN_0006b9fa` fault call — same
  discipline as the `gp-0x4f64`/`gp-0x448a` pair) wrapping a debug/engineering-mode gate:
  `(*(uint*)(*(int*)(gp-0x3490)+4) == 0x49d6b173) && (*(char*)(tp+0x50ed) == 0xE9)`. Read the actual
  production bytes: `tp+0x50ed` (= `0xC40ED`, NOT `0xBF0ED` — that's a hex-arithmetic slip, correct sum
  is `0xBF000+0x50ED`) = `0x00`; traced `gp-0x3490`'s validated-fallback ROM record (`0xB9A7C`, via its
  writer `FUN_00049180`) and its dword at `+4` (`0xB9A80`) = `0x00000000`. **Both conjuncts independently
  false in the shipped image** → the debug/live-tuning writes (`0x41790`, `0x419f8`) are dead code in
  production; the writes that always execute are `0x417a0` (LIVE, `gp-0x4f50`-derived) when
  `|gp-0x4f50| <= 13000` and `0x41a18` (pin `0x7fff`) when `|gp-0x4f50| > 13000` — see the symmetric-window
  correction above.

**★★★ 2026-07-20 — the `0x41a18` PIN IS STRUCTURALLY UNREACHABLE. `gp-0x6abe` can never actually freeze,
in production, under any driving condition.** Traced `gp-0x4f50`'s full producer chain: `FUN_00041464`
← sole writer `FUN_00068fbe` (`0x68fde`, atomic copy under `__disable_irq`) ← `gp-0x29c4` ← sole writer
`FUN_00068f52` ← called from `FUN_00065afe` (sin/cos ADC + atan2; `& 0x3fff` mask confirms the 14-bit
counter). `FUN_00068f52` decompiled in full: wraparound-corrected delta (14-bit fold, hard structural max
`±8192` counts) is scaled `×120000/16384` (max `±60000`), 2-tap averaged, then **explicitly clamped to
`iVar2 ∈ [-13000, 13000]`** before being stored to `gp-0x29c4` — and this clamp is NOT vacuous (the
pre-clamp signal has real headroom to ±60000, so it genuinely engages under fast rotation). Since
`gp-0x4f50 = gp-0x29c4` verbatim, `gp-0x4f50`'s value is bounded to exactly `[-13000,13000]` by
construction, and `FUN_00041464`'s pin condition (`|gp-0x4f50|>13000`, i.e. `>=13001` magnitude) can
therefore never be satisfied. **`gp-0x6abe` is ALWAYS the live value in production — never `0x7fff`,
regardless of how fast the motor spins.** Same clamp bound also makes `FUN_00034350`'s own compound gate
at `0x345fa-0x34610` (`gp-0x6ac0>=13001` OR `|gp-0x6abe|>13000`) unreachable — dead code, term always
computes. [Open, unconfirmed: absolute physical units of `gp-0x4f50` — the `×120000/16384` scaling is
dimensionally consistent with degrees/sec IF the producing tick is exactly 3 ms (333⅓ Hz) and the encoder
is 14-bit/360° per rev, but no 3 ms tick period was independently confirmed in the binary — this is
`[INFERRED]`, not established, and the kit's task-rate question (100 Hz vs 1 kHz, `model/eps_lkas_chain_model.py`
line 179) remains open regardless.]

**★★★ 2026-07-20 — phase lag from the `α=37/128` filter recomputed via exact discrete-time formula (not
continuous RC approximation), at 21 Hz, for both candidate task rates.** `phase(f) = -atan[(1-α)sin(ω) /
(1-(1-α)cos(ω))]`, ω=2πf/fs: **fs=1000Hz → ≈17.6°**, **fs=100Hz → ≈39.9°**. Both comfortably under the 90°
threshold where a velocity-opposing term would start injecting energy instead of removing it
(`cos(17.6°)=0.95`, `cos(39.9°)=0.77` — 77-95% of ideal damping effectiveness retained even at the
pessimistic rate). Note: a naive continuous-time `arctan(2πfτ)` approximation overestimates badly at
fs=100Hz (gives ~73° vs the exact 39.9°) because 21Hz is 42% of Nyquist there — worth remembering next
time a lag estimate is eyeballed instead of computed from the exact discrete transfer function.

**Net effect on the 2026-07-20 build question:** the operator's proposed fix (raise `Y[0]` from 0 to a
live value in the `gp-0x6a5e`-indexed LERP table `0xC9E9C`, to un-gate this damper hands-off) is
structurally sound — the sign source is genuinely live and correctly-signed with velocity, the magnitude
gate is not a rectifier, and the filter lag does not invert the sign at 21Hz under either task-rate
candidate. Effect SIZE (is the restored gain enough to matter) was not assessed.

**★★★ 2026-07-20 — compared against the alternative "reduce loop gain at 21Hz" fix
(`FUN_00034a72`/`gp-0x6df4` boost-lane EMA, cal `0xC6372`) and found a task-rate asymmetry that decides
between them.** `FUN_00034a72`'s EMA: `y = y_prev + ((gp-0x4f60*32 - y_prev) * tp+0x7372) >> 10`,
`tp+0x7372 = 0xC6372 = 205` [VERIFIED byte read], α=205/1024≈0.200, **note the `>>10` shift — a different
filter family from the damping-lane's `>>7`, do not conflate the two constants.** Recomputed the exact
discrete frequency response `|H(f)|=α/sqrt(1-2(1-α)cosω+(1-α)²)` for the proposed drop to cal=32 (α≈0.031)
at both candidate task rates:
- fs=1000Hz: −12.5dB @ 21Hz, only −1.3dB @ 3Hz — a genuinely surgical notch, cheap at low frequency.
- fs=100Hz: **−31.7dB @ 21Hz, but also −15.6dB @ 3Hz** — at this rate the same edit is a blunt broadband
  cut, not a notch; 21Hz (21% of Nyquist) and 3Hz aren't separated enough for the filter to discriminate.

**This is the opposite failure mode from the damping-lane's phase-lag risk**: the damper's safety margin
(lag<90°) holds at BOTH candidate rates (see above, ~18°/~40°); the gain-cut's safety margin (sparing
3Hz assist authority) holds ONLY at the 1kHz candidate and would be a serious drivability regression at
the 100Hz candidate. Given the kit's task rate is still unresolved
(`analysis-2020accord/model/eps_lkas_chain_model.py` line 179, multiple prior sessions), **the damper restore is
the more robust near-term choice specifically because its safety case does not depend on that open
question — the gain-cut's does.** Not mutually exclusive; gain-cut is a reasonable follow-up once task
rate is independently confirmed. Downstream consumers of `gp-0x6df4` beyond the boost lane itself were
not traced — open thread if the gain-cut is revisited.

**★★★ 2026-07-20 — effect size, walked end to end with byte-verified table data (mode=10).** Two of the
four multiplied LERP factors are FLAT UNITY at mode=10 and cancel out of the Q10 chain entirely:
- f1 (table `0xC9CCC`, mode-dependent-selection-indexed): X=(205,1331,2355,3072), **Y=(1024,1024,1024,1024)**.
- f3 (table `0xC9DB4`, `gp-0x6a10`-indexed): X=(0,50,100,150,700), **Y=(1024,1024,1024,1024,1024)**.
- f2 (table `0xC9E9C`, `gp-0x6a5e`-indexed, the Y[0] edit target): X=(2240,3840,5120,8960), Y=(0,235,430,877)
  [byte-verified, matches the original session's finding exactly].
- f4 (table `0xC9F84`, `gp-0x6ac0`-indexed): X=(60,400,2500,4000), **Y=(0,140,539,927)** — the only
  genuinely shaped, non-unity factor; monotonically increasing with `|gp-0x6ac0|` (motor rate magnitude),
  saturating at `Y[3]=927` for rate≥4000 (hard ceiling, no further growth by LERP-extrapolation
  construction).

**Formula collapses to `term = clamp(gp-0x698a,0,1024) × f2(gp-0x6a5e) × f4(gp-0x6ac0) / 1024²`.** With
`f2=235` (candidate `Y[0]`, hands-off) and `gp-0x698a≈1024` [INFERRED, moderate confidence — see below],
**the term is bounded `[0, ~213]` counts, with 213 being a hard ceiling (f4 cannot exceed 927), not an
estimate.** Against the aggregator's `±0x800(2048)` range gate (per team-lead's citation, not
independently re-derived this session): the term maxes at ~10% of that ceiling — never close to
saturating it; the table shape, not the aggregator, is what bounds this lane.

**`gp-0x698a` (the scale seed) — sole producer confirmed `FUN_00026c80`** (`0x27384`, only writer;
`0x27374`/`0x28650`/`0x28bdc`/`0x344d8` are reads, `0x46984`'s "698a" hit is a branch-target-text false
positive, same class as the `0x6abde` false hit earlier this session). `FUN_00026c80` is a large 8-mode
dispatch state machine (~50 locals) that MIN-reduces up to 11 per-mode Q10 slots, most defaulting to
`0x400`(unity) in the paths read — consistent with `gp-0x698a≈1024` in nominal fault-free LKAS engagement,
but the specific active dispatch state during hands-off driving was NOT traced, so this is an inference,
not a verified value; term magnitude scales linearly with it if a real number is ever obtained.
**Checked and ruled out the V38-gain wrinkle**: `FUN_00026c80` does not read cal `0xC646C` anywhere (per
the kit's existing finding that `0xC646C` has exactly 5 readers, none in this function) — `gp-0x698a` did
NOT scale with V38's 4× LKAS gain.

**Coulomb vs viscous: VISCOUS, not Coulomb.** `f4` is the only surviving rate-dependent factor and it is
not flat — magnitude scales with instantaneous `|gp-0x6ac0|` (0→140→539→927 as rate climbs 60→400→2500→
4000), the defining signature of viscous damping (force∝velocity) vs Coulomb (constant-amplitude,
sign-only). Sublinear/saturating above ~2500 (soft ceiling, not unbounded), but genuinely rate-proportional
at low-to-mid amplitude — the right shape to remove energy from a resonance, not just alternately kick it.
No stick-slip signature.

**Boundary honestly hit and named, per operator/team-lead preference for "I don't know" over a fabricated
adequacy claim**: whether ~213 counts of MOTOR-TORQUE-domain correction meaningfully damps a Q=13.6
mechanical resonance whose measured manifestation (139 counts) is in a DIFFERENT domain
(`gp-0x4f60`/Sensor-B TORQUE, not motion/rate) requires the plant transfer function (torque-to-motion
authority at 21.4Hz, the mode's effective mass/stiffness) — not determinable from firmware bytes alone.
The mechanism is verified sound and bounded safe (cannot exceed the aggregator gate); whether its
magnitude is *adequate* is an on-car question, not a static-analysis one.
