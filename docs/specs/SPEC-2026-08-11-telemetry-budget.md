> # 🛑🛑 SUPERSEDED — DO NOT ALLOCATE FROM THIS DOCUMENT
> **Superseded 2026-08-12 by `docs/specs/SPEC-2026-08-12-next-telemetry.md`.**
>
> **Why this matters and is not a formality:** this spec's **ADDENDUM still ranks `gp-0x6bbe` as the
> top anti-damping candidate and allocates the 427 channel plus a sign bit to it.** `gp-0x6bbe` was
> **closed as a lever on 2026-08-12** — it is rate-derived (`STATE.md` §A4). **Anyone told to "start
> from the existing telemetry budget spec" will re-propose a dead lever.**
>
> Also superseded here: any endpoint sized against matched episodes or cross-build contrasts. Standing
> operator instruction, 2026-08-12 — **builds must be interpretable from ONE short symptomatic drive
> (~15–30 s engaged); "UNINTERPRETABLE" is a design failure, not a verdict.** See `CLAUDE.md`.
>
> The bit-inventory and gateway-whitelist sections remain factually useful. **The allocations do not.**

# SPEC — telemetry budget audit, next-build allocation (`fw-dampaxis`, 2026-08-11)

SPEC ONLY per instruction — no cave designed, no bytes written. Operator's request: *"Make sure we are
getting full use out of all available telemetry bits."*

---

## T1 — free-bit census (sent first; full detail also in the SendMessage transcript)

All bit maps fresh-verified this session via full `disassemble_function` of all three builders
(`FUN_00055a98`/330, `FUN_00055c42`/399, `FUN_00055d80`/427) — not re-quoted from memory, though they
match the existing corpus exactly (which itself was independently derived, so this is a second
confirmation).

**Cadence, resolved**: a real conflict existed on record (62.5 Hz vs 100 Hz base tick). The 100 Hz claim
wins — three independent methods including a **measured** 100.000 Hz fit on CAN 399, and it matches
this session's own V90 flight (427 measured 49.81 Hz ≈ 100Hz÷2). **`0x14A`/`0x18F` = 100 Hz (Nyquist
50 Hz); `0x1AB`/427 = 50 Hz (Nyquist 25 Hz).**

| ID | free bits (clean, store-insert) | free bits (mask-edit tier) | in active use |
|---|---|---|---|
| `0x14A` (330) | byte7[7:6] = 2, **unclaimed** | 0 | byte4[7:3] = 5, V90's current field |
| `0x18F` (399) | byte4[2:0]=3 + byte5[7:6]=2 + byte6[6]=1 = **6, unclaimed** | byte5[3:0]=4 | none |
| `0x1AB` (427) | byte0[6:5]=2 + byte2[7]=1 = **3, unclaimed** | 0 | bits1:0+byte1 = the 10-bit MOTOR_TORQUE analogue field |

**Checksum covers every spare bit automatically** — confirmed fresh on all three: the checksum call
(`FUN_00057b24`) is the LAST instruction-sequence step in program order in every builder, after every
spare-bit write. No recompute needed.

**Second repointable multi-bit field? — RESOLVED via direct SSH read-only check of the comma device's
own opendbc + carstate.py + safety C code (`honda_civic_hatchback_ex_2017_can_generated.dbc`, the DBC
this platform's `CAR.HONDA_ACCORD` config actually maps to — confirmed from `values.py`).**

| signal | frame.bytes | carstate.py use | verdict |
|---|---|---|---|
| `STEER_ANGLE` (Signal-A) | `0x14A` byte0-1 | `ret.steeringAngleDeg` | **ACTIVELY USED — not repointable** |
| `STEER_ANGLE_RATE` (Signal-C) | `0x14A` byte2-3 | `ret.steeringRateDeg` | **ACTIVELY USED — not repointable** |
| `STEER_TORQUE_SENSOR` (V1) | `0x18F` byte0-1 | `ret.steeringTorque` | **ACTIVELY USED — not repointable, likely safety-adjacent (driver-override signal)** |
| `STEER_STATUS` | `0x18F` byte4[7:4] | decoded fault string | Honda-populated anyway, not a free-bit candidate |
| **`STEER_WHEEL_ANGLE` (Signal-B)** | `0x14A` byte5-6 | **zero references anywhere in `car/honda/` or `safety/`** | **DBC-defined but code-unused — a genuine second 16-bit candidate** |
| **`STEER_ANGLE_RATE` (399's own copy, V2)** | `0x18F` byte2-3 | **zero references anywhere** | **DBC-defined but code-unused — a genuine second 16-bit candidate** |
| `STEER_CONFIG_INDEX` | `0x18F` byte5[3:0] | **zero references anywhere** | resolves the "mask-edit, elevated risk" framing — DBC-defined but also confirmed unused; same tier as the two candidates above, not a new hazard |
| `STEER_CONTROL_ACTIVE`, `STEER_SENSOR_STATUS_1/2/3`, `MOTOR_TORQUE`, `OUTPUT_DISABLED`, `CONFIG_VALID` | various | **zero references anywhere** | consistent with the free-bit map above; no surprises |

**Every free bit identified in the earlier census (`0x14A` byte7[7:6], `0x18F` byte4[2:0]/byte5[7:6]/byte6[6], `0x1AB` byte0[6:5]/byte2[7]) is confirmed to have NO overlapping DBC signal at all** — clean on both the Honda-firmware side and the openpilot-DBC side.

**Safety C firmware** (`opendbc/safety/modes/honda.h`) references neither `0x14A`/330 nor `0x18F`/399 at all — no independent panda-level safety check depends on any byte in either frame. **Checksum**: the CANParser validates checksums generally (confirmed via an explicit per-message opt-out elsewhere in the file, absent for these three IDs), but the EPS's own checksum call runs after any spare-bit write and stays self-consistent — the same mechanism already proven safe by 10+ flights of the existing 5-bit channel. No new risk.

**⇒ Revised verdict: `STEER_WHEEL_ANGLE` (`0x14A` byte5-6) and 399's own `STEER_ANGLE_RATE` (`0x18F`
byte2-3) are genuine second/third 16-bit repointable channels, one tier below 427's "never even
registered" clearance (these ARE defined and parseable, just never actually read into `ret.*` or the
safety layer in the current code) — worth a second look before committing to only the 11 spare bits.**

---

## T2 — the allocation

### V90's current field, and what's dead

`0x14A` byte4[7:3], 100 Hz: **b7**=sign(`gp-0x6b26`) duty 0.524 (good) · **b6**=`|gp-0x6bf6|≥512` duty
0.254 eng (good) · **b5**=`gp-0x6ae2≠0` duty 0.675 eng (good) · **b4**=`gp-0x6c00<0` duty **0.000000,
railed dead** (the observer gate has never once failed) · **b3**=fingerprint≡1 (needed for the odd-value
validator + liveness). Plus 427 = `|gp-0x6b26|`·5≫3, 50 Hz, 0% saturation.

**Reclaim b4 in every future allocation** — a railed bit carries zero information and the record's own
rule applies (a duty-1.0000 rung is worth more reclaimed than left in place, because it moves the
alphabet).

### New signal identified this session — the D-term's own output is separable

Decompiling `FUN_0003a382` (the PID, `0x3a382`) end to end: the filtered D-term contribution is stored
to its **own persistent RAM cell, `gp-0x3680`** (`0xFEDF4980`), distinct from `gp-0x367c` (P-state),
`gp-0x3688` (I-state), and the FINAL combined output `gp-0x6ad4`:

```
0x3a5xx: gp-0x3684 = err (new "err_prev" for next cycle)     -- D differencer state
         iVar29 = (err - err_prev) * cal(Kd) >> 10           -- RAW D term
         iVar31 = clamp(iVar29, ±0x2800)
         iVar31 = EMA(iVar31*32, alphaD=cal(0xC644A)) + gp-0x3680_prev   -- filtered D
         gp-0x3680 = iVar31                                  -- <-- D's OWN output, separable
         ...
         gp-0x6ad4 = ((D + I + P) >> 5) * speedLERP >> 10 * polarity * gate   -- final PID output
```

This is a genuine third candidate beyond `gp-0x6ad4` and `gp-0x6b94`, and it is the most DIRECT possible
readout of the mechanism the Kd cut targets.

### Revised priority — a measurement build comes BEFORE any Kd dose

`docs/review/GATE2-2026-08-11-cbe74-independent.md` (N5, folded in per instruction, not re-derived) makes the
case that the whole "D pumps energy" finding rests on an unverified proxy: `err = gp-0x4f60 −
clamp(gp-0x6ad6,±8192)` was approximated as `≈ gp-0x4f60` because `gp-0x6ad6` was assumed slow/small at
7.79Hz, and that assumption is now shown to be wrong — `gp-0x6ad6` retains **86% magnitude at −40.3°
lag** at 7.79Hz (not small, not slow). **This is a gating measurement, not a nicety**: if `err`'s true
phase differs materially from `gp-0x4f60`'s, the D-term pumping conclusion the whole Kd-cut rationale
rests on could move. **Stage 1 should be a NO-DOSE measurement build, telemetering `gp-0x6ad6` itself**
(N5's design, which I am adopting rather than competing with):
- **427 = `\|gp-0x6ad6\|>>5`** (not `>>3` — the stock packer scaling clips immediately at `gp-0x6ad6`'s
  own ±25600 ceiling against a ±8192-tuned packer; `>>5` gives ~9.64 effective bits, never clips)
- **reclaimed b4 = `sign(gp-0x6ad6)`** at 100 Hz, same signed-reconstruction shape as V88/V90
- **identity: `b4 == (gp-0x6ad6<0)` holds every frame on the new build, near-chance on the old** (b4
  there is unrelated — `gp-0x6c00`'s sign)
- ⚠ **427's 24.91 Hz Nyquist cannot see 26–31 Hz** (28.5 Hz aliases to ≈21.3 Hz, would contaminate an
  18–22 Hz reading) — the 100 Hz sign bit is the only channel that reaches that band, same limitation
  as every prior probe in this design lineage.

**Stage 2, only if Stage 1 confirms the pumping finding survives on the real `err` phase**: the actual
Kd-cut dose, with `gp-0x3680` (below) for the dose-in-force check.

### Allocation A — Stage 2, the Kd-cut DOSE build (`0xC6AE6/E8/EA/EC`), once Stage 1 clears it

Ranked by information gained per bit:

| bit | signal | rate | what it decides |
|---|---|---|---|
| **427 (50 Hz)** | `\|gp-0x3680\|` (D-term magnitude), 10-bit analogue, same pack shape as V90's `MOTOR_TORQUE` field | 50 Hz | **the parameter-free dose-in-force test** — if `Kd` is halved, this magnitude should visibly shrink; the channel IS the dosed quantity, same property V90 had |
| **b4 (reclaimed)** | `sign(gp-0x3680)` | 100 Hz | reconstructs the D-term's SIGNED output above 427's 25 Hz Nyquist — the only channel that can see the D-term at 18–28 Hz, directly testing "D pumps energy" (Q2's finding) on-car |
| **b3** | fingerprint, unchanged | — | liveness + odd-value validator (unchanged property) |
| **b6** | `sign(gp-0x6ad4)` — the FINAL combined PID output's sign | 100 Hz | a phase-relationship check: does D's sign track the final command's sign, or lead/lag it (bears directly on whether cutting D changes the LOOP's net phase, not just its magnitude) |
| **b5** | `\|gp-0x6ad4\| ≥ threshold` (a magnitude gate on the final output, threshold picked the same way V90's b6 was — invert a duty estimate once the build's own telemetry exists) | 100 Hz | separates "D dominates a small command" from "D dominates a saturating command" — the same confound V90's (b6,b5) pair was built to resolve, applied to the PID output instead of the friction lane |

**This allocation keeps the dose-in-force property (427 carries the dosed cell) and adds a same-shape
signed reconstruction (b4/427 pair) exactly matching V88/V90's proven design**, rather than inventing a
new instrument class.

### Allocation B — if the next build is the `0xCBE74` dose (built, labelled do-not-fly-first, kept as an option)

**427 stays on `gp-0x6b26`** — unchanged, already the dose-in-force channel, already flown once (V90).
**b4 (reclaimed)**: given the recommendation is not to fly this build, I would not spend the reclaimed
bit on anything specific to it. **Best use: the return-to-centre gate** (below) — motivated directly by
the operator's own observation, valuable independent of which build actually flies next.

### Return-to-centre gate — RESOLVED by the other agent's trace, and it changes the bit design

`reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism.md` (landed after
this section was first drafted): **there is no discrete boolean gate — the operator's symptom is
explained by a shared, rate-adaptive governor CEILING** (`gp-0x4f64`, driven by a LERP on motor rate
`gp-0x6ac0` against table `0xC520C`, falling from 4762 nominal to 512 at high rate), applied to the SAME
summed signal that carries both return-centre (`gp-0x6b62`) and LKAS's in-aggregator term (`gp-0x6b4c`,
carrying the kit's own 4x forward gain `0xC6CD0`). When LKAS and return-centre push the same way, the
combined rate rises, the ceiling shrinks, and BOTH terms get capped harder — a self-throttle, not a gate.

**Revised bit design, since there's no boolean to sample**: **`gp-0x4f64 < 4762·1024` (nominal)** — is
the governor ceiling CURRENTLY reduced below its unclamped maximum. This is a genuine, meaningful
on/off-ish test of whether the mechanism the other agent identified is actually binding at a given
moment, and it directly answers whether the operator's return-to-centre symptom coincides with an active
ceiling reduction. **GATE 1 for this bit**: not checked by me this session (the other agent's trace is
the source; I have not independently censused `gp-0x4f64`'s readers/writers). ⚠ [BELIEF, flagged by the
other agent] whether an ORDINARY return-to-centre event reaches the `0xC520C` table's breakpoints
(1050-4100 counts on `gp-0x6ac0`) is not yet quantified — that number would turn this from a plausible
mechanism into a confirmed one, and it's the natural next step before committing a bit to it.

---

## ADDENDUM — RE-AIM: Problem 1 verdict + the aggregator-lane sign probe (2026-08-11, supersedes Allocation A/B above)

**Kd cut is dead** (D damps 16-35Hz, only pumps 2-12Hz — cutting it costs more than it buys in the
grinding bands). **Problem 1 verdict**: both candidate 16-bit channels (`STEER_WHEEL_ANGLE`,
399's own `STEER_ANGLE_RATE`) are CANDIDATE-BLOCKED — `STEER_WHEEL_ANGLE` for a real structural reason
(no VSA-sourced message carries any angle signal of its own, and `0x14A` conspicuously carries a SECOND,
openpilot-unused angle field alongside the one openpilot does use — the classic shape of "one feeds the
ADAS stack, one feeds something else"), mitigated but not cleared by VSA's own messages living on bus 0
while the EPS's live on bus 1 (checked via `rlog-tools/studies/radar/_can_inventory.py` against an existing local
rlog — no live capture, no flashing). 399's own `STEER_ANGLE_RATE` has a weaker specific concern (no
identified motivated consumer) but stays blocked per instruction. **Primary spec below uses only
`0x14A` byte7[7:6] (2 new bits) + the reclaimed b4 (1 bit) + 427 — all cleared today.**

### The live question: net PID damps 6-9Hz, but measured `Re(Z)` is anti-damped — enumerate every other lane

`FUN_0003aa2c` (the aggregator) sums **11 lanes** (definitive re-disassembly,
`reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md`, verified `0x3aca8-0x3ace6`):

| lane | writer | clamp | bandwidth @ ~20Hz | sign character | status for a NEW probe |
|---|---|---|---|---|---|
| **r24 / r26** (torque-RATE) | inline, physical regs | ±8192 each | **0 dB, unfiltered, 1kHz** | not established in this context (they're same-signed-reinforcing with each other, not yet scored vs column velocity) | **TOP PRIORITY — highest bandwidth, least characterized** |
| **`gp-0x6bbe` (boost)** | `FUN_00034a72` | ±2048 | -1.2 dB | **SAME-SIGNED as raw torque sensor — REINFORCING, not opposing** (already flagged in the existing inventory as *"the proportional-dominated-AND-positive-feedback shape being hunted for"*) | **SECOND PRIORITY — already flagged as the best structural match for anti-damping** |
| `gp-0x6b86` (peak-hold) | `FUN_000352b4` | ±12288 (largest) | -3.9dB at max α | not established; peak-hold resists simple phase characterization | lower priority — hardest to interpret even if measured |
| `gp-0x6bd0` (damping) | `FUN_00034350` | ±2048 | -1.2dB | **already established dissipative** (explicit sign-flip vs filtered motor rate, confirmed structurally this session) | not needed — sign already known |
| `gp-0x6b26` (friction, `0xCBE74`) | `FUN_00036c12` | ±1024 (aggregator's own window; `0xC407E` clamps it to ±511 upstream regardless) | -14.5dB vs motor rate | **already established dissipative** at every frequency to Nyquist, this session's own extensive trace | not needed — already instrumented (V90's `b7`/427) |
| `gp-0x6ad4` (PID output) | `FUN_0003a382` | ±10240 | 0dB structurally | **already being measured by the parallel PID/D-term work** (net -0.121 at 6-9Hz) | not needed — covered by a different in-flight probe |
| `gp-0x6b4c` (LKAS) | `FUN_00026c80` | ±10240 | -12dB | externally commanded, not a candidate for an internal anti-damping SOURCE | not needed |
| `gp-0x6b62` (return-centre) | `FUN_00036388` | ±8192 | ruled out — self-rate-limited to ≤7.6 counts peak at 21Hz | n/a | not needed |
| `FUN_00036682`'s return | `FUN_00036682` | ±512 | -46 to -58dB | ruled out by magnitude | not needed |
| `gp-0x6ade` (feedforward) | none found | ±1024 | n/a | corroborated dead (2 methods) | not needed |

**⇒ Three lanes are genuinely unresolved and worth new bits: r24, r26, and `gp-0x6bbe`. Everything else
in the 11-lane sum is either already-known-dissipative, already being measured by another in-flight
probe, or structurally ruled out.**

### The allocation — 3 new/reclaimed bits + 427, all on cleared capacity

| bit | signal | rate | why |
|---|---|---|---|
| **427 (50Hz)** | `\|gp-0x6bbe\|` (boost magnitude) | 50 Hz | full magnitude for the single BEST anti-damping candidate — needed to weight how much this lane's sign matters, not just whether it's positive or negative |
| **reclaimed b4** | `sign(gp-0x6bbe)` | 100 Hz | pairs with 427 for a full signed reconstruction of boost, same shape as every prior probe in this lineage; also the only channel that reaches 26-31Hz for this lane |
| **new `0x14A` byte7 bit (was unclaimed)** | `sign(r24)` | 100 Hz | r24's own sign vs wheel rate — the top-ranked, least-characterized lane |
| **new `0x14A` byte7 bit (was unclaimed)** | `sign(r26)` | 100 Hz | r26's own sign vs wheel rate — same priority as r24, and r24/r26 are known to NOT always move together (the whole point of scoring them separately) |
| **b3 (unchanged)** | fingerprint ≡ 1 | 100 Hz | liveness + odd-value validator, unchanged from every prior build in this lineage |
| **b7/b6/b5 (unchanged)** | `gp-0x6b26` sign / `\|gp-0x6bf6\|≥512` / `gp-0x6ae2≠0` | 100 Hz | left as-is — that lane is already well-understood; no reason to disturb a working instrument for a question it doesn't bear on |

**Upside, contingent, not in the primary spec**: `0x18F`'s 6 clean SPARE bits (`4[2:0]`+`5[7:6]`+`6[6]`)
remain separately cleared — Problem 1 blocked the two 16-bit FIELDS specifically (`STEER_WHEEL_ANGLE`,
399's `STEER_ANGLE_RATE`), not these bits, which have zero DBC overlap on either side. If more than 3
new lane-sign bits are wanted, `gp-0x6b86`'s sign is the next-priority candidate for them.

### Scoring rule, standing: use `0x18F`'s rate, never `0x14A`'s — and it needs NO new telemetry

Per your instruction (*"the other channel would have inverted the sign at both decision bands at
identical coherence"* — taken as given, not re-derived this session): **whoever scores this probe's
flight must correlate each lane's sign against wheel rate extracted from `0x18F`'s `STEER_ANGLE_RATE`
field (byte2-3), never `0x14A`'s `STEER_ANGLE_RATE` (Signal-C, byte2-3 of 330) — even though the latter
is the one `openpilot` itself decodes into `steeringRateDeg`.** ⊕ **This needs no new bit at all** —
`0x18F`'s rate field is DBC-defined and present in the raw CAN stream of every existing rlog
(`evt.can` events capture raw frames regardless of whether `carstate.py` decodes them), so it can be
pulled from ANY already-captured flight, past or future, by decoding the raw bytes directly.

## ADDENDUM 2 — V92 (V91's cal edit + telemetry), conflicts resolved, final allocation

Operator decision: fly V91's `0xCBE74` ×1.5 dose regardless of the sizing concerns already on record
(V91 stays frozen on disk as the cal-only variant). **V92 = V91's 12 bytes + this telemetry cave.**

### Conflict 1 — adjudicated myself, per instruction, not deferred

**Confirmed independently**: `gp-0x6abc` IS raw, unfiltered motor rate — its producer (`FUN_00041464`,
already fully traced this session for `gp-0x6c2c`) assigns it directly from `gp-0x4f50` with no EMA in
the normal-operation branch, distinct from `gp-0x6abe` (the filtered arm). Decompiled `FUN_000360fe`
fresh: `gp-0x6b64 = -(LERP(gp-0x6bda) * gp-0x6abc / scale)`, confirming **Term 1's structural form is
exactly `-sign(gp-0x6abc)` provided the LERP output stays non-negative** (not independently re-verified
the Y-table values this session, crediting that check to the source trace).

**Correction to the "Term 2" framing**: `gp-0x6bf0` is NOT inside `FUN_00036388`/`FUN_000360fe` — full
disassembly of both (already done this session for the return-centre chain) shows no reference to it.
It's computed inside a large, separate function (`FUN_0003bd7c`, torque-margin/diagnostic-flavored,
gated by the LKAS engage-state `gp-0x67fe`), and **`gp-0x6bf0` itself has 15+ readers across many
functions, including the shaper `FUN_00042af8`** — a real, live, heavily-consumed signal, just not
literally summed into `gp-0x6b62`'s own computation the way I'd traced it. (Its derivative `gp-0x6bee`,
by contrast, has zero readers anywhere — a dead diagnostic tap, not load-bearing.)

**Verdict**: the two-sign-bit rung is still well-justified — it doesn't require the two signals to be
literally the same summand, only that both are real and their sign relationship is genuinely unclosable
from statics (true for `gp-0x6abc`, and `gp-0x6bf0`'s ADC-wiring dependency is exactly what the source
trace already flagged as unresolvable). **Recommend proceeding with it, with the framing corrected**:
"two independently-verified rate/margin signals reaching the assist chain by different routes, whose
sign relationship is unresolved" rather than "two terms of one lane." Governor-ceiling (`gp-0x4f64`)
dropped from the ranking per the 4-route measurement — confirmed, not re-derived.

### Conflict 2 — resolved as option (b), `T` computed from route 77's actual percentiles

Predicted `\|gp-0x6b26\|≥T` duty at stock and ×1.5 via log-linear interpolation across the 5 measured
percentile points (p50 5.5, p95 58.3, p99 114.3, p99.9 184.7, max 319.1 — all scale by exactly ×1.5
under the dose, so `duty(T, ×1.5) = duty(T/1.5, stock)`):

| T | duty(stock) | duty(×1.5) | Δ |
|---|---|---|---|
| 10 | 0.339 | 0.447 | +0.108 |
| **15** | **0.242** | **0.339** | **+0.096** |
| 20 | 0.184 | 0.269 | +0.084 |
| 30 | 0.119 | 0.184 | +0.066 |

**Recommend `T=15`**: both duties comfortably away from 0/1, and the predicted shift (+0.096) is large
relative to typical bootstrap CIs over hundreds/thousands of frames — a single byte, movable on the next
build exactly like V90's `b6` threshold.

### Final allocation — everything fits in `0x14A`'s existing 7-bit field, `0x18F` untouched

| bit | signal | rate | role |
|---|---|---|---|
| 427 (50Hz) | `\|gp-0x6bbe\|` (boost magnitude) | 50Hz | top anti-damper candidate, full magnitude |
| **b7** (repurposed) | `sign(gp-0x6bbe)` | 100Hz | pairs with 427, reaches 26-31Hz |
| **b6** (unchanged) | `\|gp-0x6bf6\|≥512` | 100Hz | K1/observer model magnitude — still live, kept free |
| **b5** (unchanged) | `gp-0x6ae2≠0` | 100Hz | K1/observer friction relay active — still live, kept free |
| **b4** (reclaimed) | `sign(gp-0x6abc)` | 100Hz | return-centre Term 1 (raw rate) |
| **new byte7 bit** | `sign(gp-0x6bf0)` | 100Hz | the unresolved second signal |
| **new byte7 bit** | `\|gp-0x6b26\|≥15` | 100Hz | **dose-in-force**, cave-based per Conflict 2(b) |
| **b3** (unchanged) | fingerprint≡1 | 100Hz | liveness/validator |

**All 7 bits of `0x14A`'s free field used, none wasted; `0x18F` untouched (its two 16-bit fields stay
CANDIDATE-BLOCKED per the falsifier already on record — VSA needing no steering angle on this platform,
or `0x14A` not being gatewayed to bus 0, would loosen it; its 6 clean spare bits remain a contingency,
unused here since the primary allocation didn't need them).** Rate-channel rule, corrected per your
finding: **`0x14A`'s `rate_c` for absolute-magnitude work (this build's dose-in-force scaling check),
`0x18F`'s `rate_f` only for phase/impedance work — stated explicitly per question, not blanket-applied.**

### Cave-size estimate

V90's cave: 74 bytes / 29 instructions for 5 rungs (`b7`/`b6`/`b5`/`b4`/`b3`) + the `byte4` read-modify-
write epilogue. This design keeps all 5 existing rung SHAPES (load/compare/conditional-add, ~8-10B
each) just repointed to new cal/RAM sources — no byte-count change there. **Adds**: 2 new rungs
(`sign(gp-0x6bf0)`, `\|gp-0x6b26\|≥15` — ~8-10B each, same shape as the existing 5) + a new `byte7`
read-modify-write epilogue (analogous to `byte4`'s, ~14B, since byte7 has never been written before) +
the 427 packer source-load edit (a 2-byte halfword change, same class as V87/V88/V90's own repoints,
**not cave bytes at all**). **Estimated total: ~106 bytes**, against **1138 bytes free** in the cave
extent after V90 — comfortably inside budget, well under 10% of available room. Every non-trivial byte
sequence would need to be copied from a Ghidra-verified twin per your standing instruction, not
hand-encoded, when this goes to a builder.

## ADDENDUM 3 — FINAL: b5/b6 reallocated, 4-slot trade, GATE 1, identity (last round)

### Two variants, contingent on the pending dwell-relay polarity adjudication

**One nuance on the reasoning for the swap, flagged not to block it**: the stated justification
("`sign(gp-0x6b62)` already subsumes term 2's contribution, so `sign(gp-0x6bf0)` is diagnostic not
decisive") leans on the ORIGINAL "two terms of one return-centre lane" framing. My earlier correction
this session found `gp-0x6bf0` is NOT literally inside `gp-0x6b62`'s own sum — it reaches the assist
chain independently, via the shaper (`FUN_00042af8`), a separate and later stage than the aggregator
`gp-0x6b62` feeds directly. Strictly, `sign(gp-0x6b62)` does not subsume `gp-0x6bf0`'s contribution —
they are independent signals on independent paths, and both could matter for the net anti-damping
question regardless of each other. **This does not change the recommendation** — the swap's OTHER,
independent justification (a relay/detent test is a qualitatively different, currently-untested
hypothesis class — nonlinear stick-slip vs. a linear sign correlation) fully supports it on its own.
Flagging the "subsumes" wording as imprecise, not the conclusion as wrong.

### Variant A (as delivered, unconditional) — slot 4 = `sign(gp-0x6bf0)`

Fixed (unchanged): `427=|gp-0x6bbe|`, `b7=sign(gp-0x6bbe)`, `b3=`fingerprint, new-byte7-bit=`\|gp-0x6b26\|≥15`
(dose-in-force). **Four bits now open** (`b5`, `b6`, plus the second new `0x14A` byte7 bit — the K1/
observer question closed today per your measurement, `P(b5\|b6=1)`=0.986→1.000 above 1°/s, discriminating
cell 0.63% of frames).

| pick | signal | reasoning |
|---|---|---|
| **1** | `sign(gp-0x6b62)` | the lane's own OUTPUT, measured directly — no composition assumption |
| **2** | `gp-0x6b62≠0` | required to disambiguate your own flagged disable branches (`cVar16=='\0'`, the `gp-0x2588`/`gp-0x2584` fault check) — without it a "0" reads identically to "positive, tiny" |
| **3** | `sign(gp-0x6abc)` | the convention anchor — cheap, ~0.5 by construction, de-risks every future phase claim on this signal |
| **4** | `sign(gp-0x6bf0)` | the second unresolved signal (corrected framing: reaches the assist chain via the shaper, not literally summed into `gp-0x6b62`, per my earlier correction — still a real, live, unresolved-sign quantity worth measuring) |

**Excluded, deliberately: the dwell-snap-state rung.** Per your explicit instruction not to spec its
semantics until the polarity adjudication lands. **I can contribute one data point to that adjudication,
not override it**: my OWN full decompile of `FUN_00036388` earlier this session (independent of either
agent's claim) reads the increment condition as `\|gp-0x6b64\| < cal(0xC618A)=1024` (dwell/increment
while LOW-magnitude/near-center; decrement while `≥1024`), with the snap-to-1024 firing once the
counter exceeds `cal(0xC627E)=20`. This matches the framing in your first message, not the "opposite
polarity" alternative — but I'm reporting it as a data point for the adjudication, not resolving it
myself against your instruction. **`gp-0x6bda` (item 7) also excluded** — lowest-ranked, and the
`gp-0x6b62≠0` bit already gives most of what it would have (whether the lane is live right now).

**No second builder hook needed — your prior (one hook) stands.** All four picks plus the dose-in-force
bit fit inside `0x14A`'s existing `byte7[7:6]` capacity (2 bits) + the reallocated `b5`/`b6` (2 bits) —
`0x18F` stays fully untouched, no second RMW epilogue, no second place to get it wrong.

### 🛑 FINAL — polarity confirmed `<`. Variant B is the shipped spec (Variant A retained above for provenance only)

Polarity adjudicated `<` across four independent sources (a fresh `decompile_function` reading Ghidra's
own p-code-derived booleans, an independent assembly control-flow trace, three predating sessions that
converged on the same reading, and the physical-plausibility check below) — my own fresh decompile of
`FUN_00036388` earlier this session was part of that convergence; a `>` appearing in one of my own
summary lines was a transcription slip, not a second reading. **Variant B, below, is final.**

### Variant B (FINAL) — slot 4 = dwell-relay snap state

**Signal: `gp-0x6a82 > cal(0xC627E)=20`** — the exact condition `FUN_00036388` itself tests
(`0xC618A`-vs-`0xC627E` hysteresis compare, `if (uVar4 < uVar12) iVar11 = tp+0x718a` at the point the
output magnitude gets forced to the fixed 1024 ceiling) — reading this bit tells you whether the snap
is ACTIVE this cycle, not just that the counter moved.

**Why the swap, on its own independent merits** (not the "subsumes" framing above): `sign(gp-0x6b62)`
and the three other picks are all linear sign-correlation tests. **The snap state tests a qualitatively
different hypothesis — a relay/detent mechanism** — under the confirmed `<` polarity, a large fixed
resistance to small motion that releases once motion grows, a textbook stick-slip generator and the
first structural match to *"micro-ratcheting when spinning the wheel at all."* No other bit in either
variant touches this question.

**The physical reading, now that the polarity is settled**: `gp-0x6b64 ∝ Y(gp-0x6bda)·gp-0x6abc` (raw
motor rate) ⇒ `gp-0x6b64` is rate-proportional, so the arm window opens when this rate-proportional
signal is SMALL — near-zero wheel rate and direction reversals. After 20ms of sustained near-stillness,
the term snaps to a fixed 1024-count opposing torque, releasing once rate grows again. **A fixed
resistance that arms after 20ms of near-stillness and releases when you push through is a detent** — the
first structural match anyone has produced to *"micro-ratcheting when spinning the wheel at all."*

🛑 **Arithmetic caution that bounds what the rung can show — carry this into the reading, not just the
duty**: for a sustained 7.79Hz oscillation (128ms period), the rate-proportional signal is near zero only
around each zero crossing — roughly 8ms per crossing against the 20ms arm time needed. **The detent may
NOT arm during sustained ratcheting at all; it is better read as a candidate for INITIATING stick-slip
(arming during a quiet moment, releasing violently when motion starts) rather than sustaining it once
underway.** This changes how the duty should be interpreted: **a LOW duty is not automatically a null**
— it may simply mean the mechanism is a trigger, not a continuous participant, and the informative
question becomes whether it fires disproportionately often right before/at the onset of a ratchet
episode, not what fraction of all engaged time it holds.

**Duty bracket: genuinely wide, stated honestly, not assumed favorable.** Given the above, the realistic
range may skew low (arming needs sustained quiet, which competes with normal steering activity) — but
this still cannot be pinned from statics. **Both rails remain informative, which is what justifies
spending a bit on an unpredictable duty**: always-on ⇒ the counter is perpetually saturated, i.e. the
"relay" never actually releases and re-engages, so it is functionally a constant output rather than a
switching mechanism — the detent reading dies, but that itself is a real, useful finding. Never-on ⇒ the
dwell condition never sustains even during quiet moments in ordinary driving, ruling the relay out of
regime entirely rather than confirming it. **This is the distinction from V90's `b4`: there, a rail meant
nothing (the observer gate's own tautological bound made the question a foregone conclusion before any
data arrived); here, either rail is a genuine, unforeseen answer to a real question, so the probability
of an *interpretable* result is ~1.0 even though the duty itself is unpredictable** — the honest form of
the operator's own usefulness × probability criterion.

**Everything else in Variant B is identical to Variant A**: picks 1–3 (`sign(gp-0x6b62)`,
`gp-0x6b62≠0`, `sign(gp-0x6abc)`), `427`, `b3`, and the `\|gp-0x6b26\|≥15` dose-in-force bit all
unchanged. Only slot 4 differs.

### 🛑 RE-RANK — `Y1(gp-0x6bda)` confirmed zero outside `[-397,384]`, verified fresh, one-hook recommendation

Independently verified via fresh `read_memory(0xC6958,32)`: `n=5, X=[-397,-192,140,294,384],
Y=[0,2560,2560,717,0]` — **byte-exact match to the claim, confirmed, not taken on faith.** `Y1=0`
identically outside `[-397,384]` ⇒ `gp-0x6b64=0` regardless of rate whenever `gp-0x6bda` is out of
window ⇒ the snap-state bit ALONE cannot distinguish a genuine detent from the outer gate simply being
shut (a flat bias, not a relay). Adding `gp-0x6bda`-in-window disambiguates via a 2×2.

🛑🛑 **CORRECTION, 2026-08-11 (post-spec) — "`(0,0)` should be empty" IS WRONG AND IS WITHDRAWN.**
A shut outer gate forces `gp-0x6b64 = 0`, which **SATISFIES** the arm condition `|gp-0x6b64| < 1024`
on every tick — so the dwell counter **climbs** to its ceiling of 21 rather than staying down, and that
climb takes **21 ticks at 1 kHz = 21 ms**. During the climb **`b4` is already 0 while `b6` is still 0**.
⇒ **`(0,0)` occurs for ~21 ms after every gate-shut edge — roughly 2 frames at 100 Hz per event.**

> **CORRECTED PRE-REGISTRATION: `(0,0)` is RARE and always ADJACENT TO A `b4` FALLING EDGE. A
> SUSTAINED `(0,0)` RUN is what indicts the rung map — a handful of frames per event is the instrument
> working as designed.**

🛑 **Why this matters operationally:** a scorer expecting *never* would see a few frames per event and
conclude the polarity or the bit offset is wrong — **and pull a working build.**

⊕ **And the correction STRENGTHENS the design rationale.** Because a shut gate **ARMS** the counter
rather than disarming it, **`b6 = 1` is the DEFAULT state whenever the outer gate is shut.** ⇒ **`b4`
is not a nice-to-have partner for `b6`; it is what makes `b6` interpretable at all.** The `gp-0x6bda`
swap was right for a *better* reason than was given at the time: the argument made was
"disambiguate a detent from a constant"; the sharper statement is that **without `b4`, `b6` has no
baseline.**

**Recommendation: stay on ONE hook. Drop `sign(gp-0x6abc)` and `sign(gp-0x6bf0)`; keep the lane's own
3-state output (`sign(gp-0x6b62)` + `gp-0x6b62≠0`) plus the now-validated 2×2 detent diagnosis
(snap-state + `gp-0x6bda`-in-window).**

**The trade, stated plainly**: this costs the convention anchor — every FUTURE phase claim connecting
`gp-0x6abc` (internal rate) to the CAN wheel rate stays unverified until some other build spends a bit
on it — and it drops `sign(gp-0x6bf0)`, the already-lowest-priority attribution bit. **I judge this
worth it because both dropped items serve a broader/future-session value, not THIS build's two decisive
questions** (is the lane net-dissipative; is the low-magnitude window a real detent or an artifact),
both of which the kept four bits answer directly. **Against a second hook**: `0x18F`'s hook is
structurally identical to `0x14A`'s proven one (same critical-section/`lp`-dead argument, already
GATE-1-clean per this session's earlier work) but has **zero flights** — a second, first-time insertion
point is a genuine incremental risk class, not just more bytes, and it is exactly the class (novel
cave/hook combinations) this kit's three bricks came from. **One hook, fewer bits, all decisive — I
would rather deliver that than a fuller instrument with a first-flight hook.** Overturn this if you
disagree; the arithmetic for BOTH sides is now on the table.

### THE FINAL PAYLOAD, complete, one place (revised)

| channel | signal | rate | role |
|---|---|---|---|
| `0x1AB`/427 | `\|gp-0x6bbe\|` (boost magnitude) | 50Hz | top anti-damper candidate from the 11-lane aggregator enumeration; full magnitude |
| `0x14A` `b7` | `sign(gp-0x6bbe)` | 100Hz | pairs with 427; reaches 26-31Hz above 427's Nyquist |
| `0x14A` `b6` | `sign(gp-0x6b62)` | 100Hz | return-centre lane's own net dissipative sign, measured directly |
| `0x14A` `b5` | `gp-0x6b62≠0` | 100Hz | three-state disambiguation against confirmed disable branches |
| `0x14A` `b4` | `gp-0x6a82 > cal(0xC627E)=20` | 100Hz | dwell-relay snap state — is the detent-or-flat-bias branch currently active |
| `0x14A` new byte7 bit | `gp-0x6bda` within `[-397,384]` | 100Hz | **disambiguates `b4`**: in-window+snapped = genuine detent; out-of-window+snapped = flat bias, not a relay |
| `0x14A` new byte7 bit | `\|gp-0x6b26\|≥15` | 100Hz | dose-in-force for V91's `0xCBE74` ×1.5 cal edit, `T=15` from route 77's measured distribution |
| `0x14A` `b3` | fingerprint≡1 | 100Hz | liveness + odd-value map validator |

**Dropped from the prior draft, trade shown above**: `sign(gp-0x6abc)` (convention anchor — future-
session value, not needed for this build's two decisive questions) and `sign(gp-0x6bf0)` (already the
lowest-priority attribution bit once the detent pair was on the table).

**One CAN builder hook** (`0x14A`'s own, already-proven pre-checksum insertion point) — **recommended
over a second `0x18F` hook**, trade argued above. **GATE 1, `gp-0x6bda` closed fresh this round**: `search_instructions` — 9 raw hits, 1 real writer
(`FUN_00036022`@`0x3608c`), 7 real reader functions including `FUN_000360fe` (the LERP this whole
question is about), `FUN_00036388` (×2), and `FUN_0003a382` (the PID's own authority-ramp index) — 1
branch-text false positive excluded. **Every bit above is a pure read of a cell with an established sole
writer and (except `gp-0x6a82`) an already-existing external consumer — no new RAM, no writes added
anywhere.**

⊕ **For the record, not actionable now**: `gp-0x6bda` is not confined to the return-centre lane —
`FUN_0003a382` (the PID) also reads it as its own authority-ramp softstart index. A future session
reading this bit should know it reports a signal the PID consumes too, not a return-centre-exclusive one.

**Builder's final bit placement** (functionally identical to the ordering above, physical slots
assigned by the builder): `gp-0x6bda`-in-window on `b4`, dwell-snap state on the new `0x14A` byte7 `b6`,
dose-in-force on byte7 `b7`. **The identity argument is insensitive to which signal sits at which
position within byte7** — it rests on byte7 as a whole (`bits[7:6] nonzero ⇒ this build`), true
regardless of which of the two new signals occupies which bit, since no prior build ever writes either
position. **Extra validator**: the
`(b4,new-bit)=(0,0)` cell 🛑 **— "should never occur" is WITHDRAWN, see the correction above.
`(0,0)` occurs for ~21 ms (≈2 frames at 100 Hz) after every gate-shut edge, because a shut gate ARMS
the dwell counter and it needs 21 ticks to reach its ceiling. Read it as: RARE and always adjacent to
a `b4` falling edge; only a SUSTAINED `(0,0)` RUN indicts the rung map.**
⊕ **THE GENUINE never-occurs validator is a DIFFERENT one, and keeping the two straight matters:**
**`(b6, b5) = (1, 0)` IS structurally unreachable** — both bits read the same cell (`gp-0x6b62 < 0`
cannot be true while `gp-0x6b62 ≠ 0` is false) ⇒ **12 of the 16 odd `byte4` codewords are reachable.**
That one is a real correctness check; the `(0,0)` one is not.
**Identity**: any single frame with `0x14A` byte7 bits[7:6]
nonzero proves this build — a fresh capacity claim no prior build (V86B through V90) can produce,
disjoint by construction. **Cave estimate: ~106-114 bytes against 1138 free** (one more compare than
the prior draft, still comfortably inside budget).

**This is SPEC ONLY — no payload bytes, no cave written.** Ready to hand to a builder alongside V91's
12-byte `0xCBE74` cal edit.

### GATE 1 — every new read, zero blast radius (both variants)

| cell | writer(s) | readers besides this cave | new read's cost |
|---|---|---|---|
| `gp-0x6b62` | `FUN_00036388` (1kHz, sole writer) | `FUN_0003aa2c` (aggregator, already-established consumer) | a 5th reference, read-only |
| `gp-0x6abc` | `FUN_00041464` (1kHz, sole writer, already fully censused this session for `gp-0x6c2c`) | `FUN_000360fe`, `FUN_0003aff4`, `FUN_0003b66a`, `FUN_0003b8f6`, `FUN_00041b8e`, `FUN_00059912`, `FUN_00063208`/`63768`, `FUN_00069b8e`, `FUN_0007c94a`, `FUN_00081784`/`81b24` (22 raw hits, all adjudicated read-only or false-positive branch-text) | one more read, same class |
| `gp-0x6bf0` | `FUN_0003bd7c` (1kHz, sole writer) | 15+ readers already, including the shaper `FUN_00042af8` directly | one more read |
| `gp-0x6bbe` | `FUN_00034a72` (already established this session as the boost lane) | `FUN_0003aa2c` (aggregator) | already covered by the 427/`b7` pair |
| `gp-0x6a82` (Variant B only) | `FUN_00036388` (1kHz, sole writer, same function as `gp-0x6b62`) | internal to `FUN_00036388` only (feeds the snap decision the same cycle it's updated) | one more read of an already-owned cell; no external consumer today, so this read adds none |

**All four new bits are pure reads of cells with an existing sole writer and an already-established
consumer — no new RAM claimed, no write added anywhere, the same zero-blast-radius class as every prior
rung in this design lineage.** All are bare `tp`/`gp` scalars, 1kHz-sourced (same task, `FUN_0002214a`,
as everything else in this cave) — RULE 7 does not apply (no `+mode*4` indirection).

### Identity — strengthened, restated

**Primary discriminator, and the cleanest one available: any single frame with `0x14A` byte7 bits[7:6]
nonzero is proof of this build, full stop.** No prior build in this lineage — not V86B, V87, V88, V89,
or V90 — has ever written to `0x14A` byte7 (confirmed this session, full disassembly of the current
builder shows every existing writer explicitly preserves those bits). This doesn't depend on trusting
any prior build's measured duty; it's a fresh capacity claim, disjoint by construction.

**Secondary, corroborating**: `b4`/`b5`/`b6` all carry entirely new signals (`gp-0x6b62`-class,
`gp-0x6abc`-class) unrelated to K1/observer (`gp-0x6c00`, `gp-0x6ae2`, `gp-0x6bf6`) that every build
through V90 used there — so even restricted to the OLD byte4-only field, this build's achievable values
break the `{3,7,15,23,31}` pattern V86B-V89 showed and the `b4≡0`-forced pattern V90 showed, for
structural reasons (different signals, different duties), not merely different measured luck.

**`b3≡1` (fingerprint) stays the map validator**: every observed value must be odd, unchanged.

## T3 — identity, single-frame, parameter-free, disjoint from V90's support (superseded by ADDENDUM 3 above for this build; kept for provenance)

**V90's own discriminator**: `b4==1` is impossible on V86B–V89 (b4≡1 always, `gp-0x6c00<0` — wait,
correction, V90 is the build where b4 CAN be 0; the prior builds V86B–V89 had different rung maps
entirely and are excluded by other means already established in `specs/SPEC-2026-08-10-v90-cave.md`).
**V90 itself, measured**: `b4` (`gp-0x6c00<0`) read **0/62,180 frames** — railed at exactly 0.

**Both proposed allocations reuse b4 for a signal with a genuinely mixed duty** (`sign(gp-0x3680)` in
Allocation A is a PID-term sign, expected ~40–60% either way, not railed; the return-to-centre gate in
Allocation B is likewise not expected to be constant). **⇒ The discriminator is trivial and strong: `b4
== 1` is impossible on V90 (measured 0/62,180 frames, exactly the property that made V90 distinguishable
from its own predecessors) and should be common on the next build.** A single frame with `b4==1` proves
the new build is on the car; V90's own support is `{b4≡0}` = the 16 odd values with bit4 clear, and the
new build's support includes the 16 odd values with bit4 SET, which V90 could never produce. Disjoint by
construction, single-frame, no threshold to invert, no reference cache — the same shape as every prior
identity check in this design lineage, and it costs nothing extra (b4 was going to be repurposed anyway).

**b3≡1 (fingerprint) stays as the map validator**: any observed value must be odd, or the cave did not
run / the field is being read at the wrong offset — unchanged from V90.
