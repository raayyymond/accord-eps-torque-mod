# HANDOFF 2026-08-08 — V81 flew (route 67); the aggregator DOES reach the motor; V83a built

**Read `docs/STATE.md` first.** Predecessor: `HANDOFF-2026-08-07-v80-flew-the-damper-is-a-relay.md`.

---

## ★★★★★ THE HEADLINE

**Route 67 flew on V81 and was fault-free. The worst symptom is a single 11.25 s sustained ~27.7 Hz limit
cycle at 92.9 km/h during a highway lane change.** Four things came out of the session, in descending
order of durability:

1. 🛑🛑 **THE `gp-0x6b94` → MOTOR GAP IS CLOSED.** The 11-lane aggregator — damper, friction, boost,
   r24/r26 — **does** reach the delivered motor command, through a two-hop bridge nobody had checked.
   Every hop is instruction-verified; the orchestrator byte-verified the crux independently.
   ⇒ `memory/accord-aggregator-reaches-motor-via-gp6acc-bridge.md`
2. 🛑 **Honda ships mode 24 (manual) ≡ mode 26 (engaged) byte-identical for all six factor families.**
   The entire engaged-only damper is **ours**, introduced at V74. It explains the operator's
   "heavier when engaged, even turning WITH the command" exactly.
   ⇒ `memory/accord-stock-mode24-equals-mode26-damper-is-ours.md`
3. 🛑 **V81 carried NEITHER of the kit's two measured grind-#1 fixes.** Route 67's grinding is an
   **absence of any fix, not a regression** — the third silent loss of a confirmed lever.
   ⇒ `memory/accord-v81-carries-neither-grind1-fix.md`
4. **The operator's "LKAS angle rate is limited" is REFUTED as a rate deficit.** The column meets or
   exceeds demanded rate at every speed (1.88× above 86 km/h). What he felt is **impedance**.

**V83a is BUILT, VERIFIED, UNFLASHED.** Cal-only, 12 cells, **every target value is Honda's own.**

---

## 1. THE FLIGHT — route 67, V81

| | |
|---|---|
| frames / duration / fs | 78,760 / 789.35 s / 100.488 Hz |
| `latActive` | **85.23%** (668.0 s), 6 runs, median 90.6 s |
| speed | 0 … **104.2 km/h** |
| `STEER_STATUS` | **{0: 78,751, 3: 9}** — no 7, no terminal fault |
| `0x1AB` DTC | **0.0000% duty, 0 transitions** · 0 `0x7FFF` sentinels |

**V81 is fault-free — `0xC407E` = 511 did its job.** [EVIDENCE]

**Operator's report:** grinding in (a) slow turn at stops while braking and (b) highway lane change;
**all grinding stopped the instant LKAS disengaged**; the highway event persisted for seconds;
**adding hand mass did not damp it**; **highway instability was the worst part**; LKAS angle rate felt
severely limited; **manual steering much heavier when engaged, even turning the same direction as the
LKAS command.**

---

## 2. ★★★★★ THE AGGREGATOR REACHES THE MOTOR — the session's biggest result

```
gp-0x6b94   aggregator FUN_0003aa2c (1 kHz) — damper gp-0x6bd0, friction, boost, r24/r26, ±0x2800
  -> FUN_0004503c  THE GOVERNOR, slew-limited by 0xC6206 (512 <16.6 km/h) / 0xC6208 (205 >)  -> gp-0x6ace
  -> FUN_000456a4  comp-add,  st.h r8,-0x6acc,gp @0x45932                                    -> gp-0x6acc
  -> FUN_00042af8  SHAPER, ld.h @0x431C4, validity gate, mode cal 0xC64C8=0 (pass-through)   -> gp-0x6b08 @0x43206
  -> Q15 blend (mux 0xC64C9=0, scale 0xC61DA=1092) -> ADD to gp-0x6afe -> clamp gp-0x4f64 -> ±0x2000
  -> gp-0x6b98 (both writes 0x43b52/0x43dfc, same value, normal path) -> FUN_000757a2 -> Iq/Id -> FOC -> PWM
```

**Orchestrator's own byte verification of the crux** — encodings predicted from the V850 format, then
matched:

| site | predicted | actual | |
|---|---|---|---|
| `0x431C4` `ld.h -0x6acc,gp,r9` | `244f3495` | **`244f3495`** | MATCH |
| `0x43206` `st.h r11,-0x6b08,gp` | `645ff894` | **`645ff894`** | MATCH |
| `0x45932` | — | `6447 3495` ⇒ `st.h r8,-0x6acc,gp` | |
| `0xC64C8` | — | **`0x00`** on STOCK / V76 / V80 / V81 | |

**Straightforwardly ADDITIVE, same-signed, no sign flip.** The delivered command is the CAN-arbitrated
term **plus** a scaled copy of the aggregator's governor-and-comp-added contribution.

### Why eleven methods missed it — the durable lesson
Every check asked **"does the shaper reference `gp-0x6b94`?"** It does not — true, and the wrong question.
**Nobody asked about `gp-0x6acc`, two hops removed.** Compounding it, `gp-0x6b08` was written off as
"self-referential ramp state, one writer inside the function itself" — **individually true, collectively
misleading**: the check asked whether anything *outside* reads it and stopped, never asking whether the
function's **own next instructions** consume it. They do.
⊕ The chain was **already documented** in `reference_accord_post_governor_comp_add.md` (May) with the exact
address `0x431c4`, and was never cross-checked against the newer "cannot reach" conclusion.

📋 **METHOD RULE: trace the FUNCTION'S OUTPUTS forward hop by hop. Do not enumerate one cell's readers and
stop when they look like monitors.** A "monitor-only" output two hops from the motor is a red flag.

### What it resolves
- **V40's brick, mechanistically**: `0xFFFF` removes the governor slew ⇒ `gp-0x6ace` snaps to target ⇒
  unbounded step into the SM2/SM3 integrator with a divergence monitor downstream. Not a threshold story.
- **The graded V74→V81 dose-response**: dose in, dose out, every cycle.
- 🛑 **The DTC-0x1d side-channel hypothesis is SUPERSEDED** — it predicted threshold behaviour; four
  independent quantities show a graded response with **zero DTC transitions on every drive**.

### 🛑 A one-byte switch nobody has touched
**`0xC64C8` is a pure build-time cal: 0 runtime writers** (whole-image `st.b` scan, 0 hits / 183,570
instructions), **1 static reader**. Mode **1 discards the entire aggregator contribution** for a static
cal; mode 2 blends it. **UNTESTED, zero hits in any build script.** Extraordinarily clean experimental
control, extraordinarily dangerous. Also newly named and never touched: **`0xC64C9`** (blend mux, 0) and
**`0xC61DA`** (Q10 integrator scale, 1092).

---

## 3. ★★★★ THE ENGAGED-ONLY DAMPER IS OURS

**In STOCK, mode 24 ≡ mode 26 byte-identical for all six factor families** (FactorB/C/D/E, ceiling,
friction), plus the r24 `gain_B` arrays, boost curve, boost amp/ceiling and boost scalars. Honda does
**not** change the assist surface on engagement. `FactorC Y[0] == 0` in **all 13** distinct stock records.

First armed at **V74**; V22→V73 are all byte-stock. V81 = V75's surface, `k` = 1.5798.

**The sign is `−sign(motor rate)`, not `−sign(LKAS error)`** ⇒ it opposes the driver even turning WITH the
command. Engaged drag at 20 °/s creep: **stock 0 · V74 47 · V75/V81 129 · V83a 7.**
Measured on-car: effort per °/s at 10–40 km/h is **1.471× [0.980, 1.812]** engaged vs manual, outside its
own split-half null; same-direction 1.494, opposite 1.434 ⇒ **direction-independent.**

**Mode 26 = engaged confirmed two ways**: V73's `gp+0x63fd` probe (104,061 frames) and a fresh
`FUN_00042746` decompile (`gp-0x67f6`, `gp-0x6806` edge, debounce `gp-0x4f68` vs `tp+0x7180`).
★ `gp-0x67f4` **CLOSED** — it is the speed voter's validity flag (`FUN_00041eec`), not an engagement gate.

---

## 4. THE 27.7 Hz HIGHWAY LIMIT CYCLE

| | |
|---|---|
| duration / f₀ | **11.25 s** · **27.75 Hz** (f₀ drifts 27.37–27.95, sd 0.17) |
| amplitude | true **978 ct**, p-p ≈ **4,088** · column angle p-p **1.29°** |
| speed / context | 92.9 km/h, blinker up, lane change, engaged 99% |
| onset | openpilot command spikes to 1100 ct, then **withdraws to 84–227** while the ring grows |
| termination | stops within **~2 cycles** of `latActive` falling |

**Present on all three builds with highway data, monotone in damper dose:**

| build | k | span | within-episode duty | peak env | in-ring `MOTOR_TORQUE` |
|---|---|---|---|---|---|
| V76 | 1.3866 | 9.3 s | **72%** (modulated) | 656 | **4.0** |
| **V81** | 1.5798 | 11.1 s | **100%** | 1759 | **15.0** |
| V80 | 4.1597 | 30.4 s | 97% | 2273 | **20.0** |

### What it is NOT
- **Not a wheel order** — pooled `df/dv` = **+0.043 Hz/(m/s)** over 8.3→28.4 m/s where order 2 demands
  +0.96; over that span order 2 moves +19.4 Hz, observed **+0.9**.
- **Not road input** — IMU vertical peaks at 12.7 Hz.
- **Not openpilot windup** — **0.0000% rail duty** at highway; peak `|cmd|` 1286 = 31.4% of `STEER_MAX`.
- **Not commanded** — the planner demands 0.043× its 1–4 Hz level at f₀; openpilot's ring component
  **lags** the bar and is ~11× smaller.
- **Not a relay** — 5f/3f measured **0.023** against a relay's 0.600; faking that needs a **6.4-pole**
  filter. Odd-symmetric and **cubic-like**. (2f/f = 0.012, 3f/f = 0.321, phase-locked R = 0.607.)
- **Not a forced resonance by anything** — see below.
- **Not the alias twin** — 72.66 Hz excluded 3.8× via `|Rate|/|Ang|` = 2πF, which survives aliasing.

### ★★★ THE DECISIVE OBSERVATION — the ring STOPS, it does not decay
Bandpassing a **perfect step** (zero plant decay) through the identical filter yields apparent
**Q = 9.0–11.6**. Both analysts' ring-down Q values (10 and 7) sit **inside that artefact band**;
widening the band 8× shows no growth in data τ, and at the best-resolved widths the data decays
**faster** than the step control.
⇒ **Q ≲ 6, τ ≲ 0.067 s ≈ 1.8 cycles.** Three consequences:
1. **A plant with Q ≲ 6 cannot amplify a small drive into a 500+ ct oscillation ⇒ not a forced resonance.**
2. **It is an actively sustained limit cycle with an engaged-only energy source.**
3. **Exactly two things switch at the disengage edge**: openpilot's command, and the mode-26 damper.
   openpilot is bounded at **≲ 2.6–5.2%** as transmitted ⇒ **the damper is the prime suspect**, by a route
   independent of the harmonics and the loop gain.

### openpilot's role, bounded
Controller is **LTI at f₀** — demand/bar gain **0.320 pre-ring vs 0.318 during**, unchanged to 1%, while
demand grows ×96. **The nonlinearity is not in openpilot's controller.**
Its pre-limiter demand spikes to **259 ct at f₀** (0.66 ct pre-ring, ×393) and its own **123 ct/frame slew
cap removes ~79%** (two independent measurements). 🛑 **Do not raise the cap** — it holds on the measured
~5× multiplier and the non-damping phase, **not** on any share-of-energy percentage.

---

## 5. THE ANGLE-RATE CLAIM — REFUTED

Geometry calibrated **per speed cell from the car's own <0.5 Hz behaviour**, both sides 3 Hz low-passed:

| regime | ach/dem |
|---|---|
| creep <14 km/h | **1.09** |
| 14–40 | **1.22** |
| 40–72 | 1.02 |
| **>86** | **1.88** |

**The column meets or exceeds demanded rate everywhere.** Replicated independently at the cells that
matter (1.88 vs 1.99 above 80; 1.02 vs 1.05 at 40–80). What is true: at highway the **demanded angle is
tiny (p95 1.09°) while LKAS torque is large** — an impedance perception, not a rate limit.

🛑 **Three independent lines now say MORE AUTHORITY MAKES IT WORSE**: H1's refutation, the A/C
predictions, and openpilot's capped resonant demand. **The 8× path and the governor-slew lever are
closed, not merely deprioritised.**

⊕ `0xC6206`/`0xC6208` are **NOT "hands-off/hands-on"** as the build scripts and BUILD-LINEAGE label them —
`gp-0x67f5` flips on **voted speed crossing 16.6 km/h** (cal `0xC531E` = 1062, debounce `0xC64E7` = 10).

---

## 6. ✅ V83a — BUILT, VERIFIED, UNFLASHED

**Cal-only. No cave, no code, no instruction byte. 12 cells. EVERY target value is Honda's own.**

| | |
|---|---|
| builder | `analysis-2020accord/build_v83a_tva.py` |
| base | `_v81_C407E.511-FRICTION.STOCK_plain_image.bin` sha `4ddbd0e2…` — **the cut that flew route 67** |
| image | `_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin` sha **`bb717ce8322d35c587e95084e697a5ad98ba6564ee9265bb09a88a2a241cd25a`** |
| rwd | `39990-TVA,A160-V83A-V81BASE-FACTORE.STOCK-GAINA.STOCK-C63A0.1024-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd` sha **`0be75e670ebf0c7e57f443eff7ff6976af1d276f54cef61a60e399827ac532aa`** (986,042 B) |

**EDIT SET** — 12 cells, 24 bytes written, **16 bytes differ**:
- **FactorE m26 → Honda's ramp**: `0xD780E` 12→60 · `0xD7810` 200→400 · `0xD7818` 539→140. `k` **1.5798 → 0.2265**.
- **`gain_A` rec0/rec1 → stock** (8 halfwords, `0xC6A72`–`0xC6A8C`). **Manual-arm revert** — engaged-inert
  once the gate is repointed; V81 was running a 6× r26 damping cut **in manual**, and V61's on-car result
  says that is the wrong direction.
- **`0xC63A0` 2048 → 1024** (one byte at `0xC63A1`). **Comparability, not efficacy** — V76 and V80 both run
  1024. 🛑 **The standing "do not double `0xC63A0`" directive was retired EXPLICITLY, by operator decision,
  on evidence** (one reader, zero writers, no data path to the faulting monitor; the real mechanism was
  `0xC407E` = 850, already reverted in V81).

**Orchestrator's own from-disk verification — ALL PASS:** 12 contiguous runs / 24 bytes (10 functional
16 B + 2 CRC 8 B), every functional run `= stock`; **value-anchored round trip reproduces V81 bit-for-bit**
(`4ddbd0e2…`), a total statement over all `0x100000`; CRC 50/50, exactly 2 blocks moved, nothing in
`[0xC5000, 0xC5FFC)`; **4× LKAS intact** (`0xC6CD0` = 3564); `0xC407E` = 511, `0xC646C` = 891, `0xC63AC` =
102, governor 512/205, `0xC64C8`/`0xC61DA` all untouched; **exactly one flashable V83 `.rwd` on disk.**

**GATE 1** vacuous (cal-only). **GATE 2** — phase literally unchanged (no filter, pole, zero, delay or
task-order change; only two static LERP tables). Magnitude, honestly: against **stock** nothing rises;
against the **flown V81** the `gain_A` r26 lane **rises 6.0× at creep**, 2.83× at 20 km/h, **1.000× at
50 and 100** (rec2/rec3 bound it).

### 🛑 PRE-REGISTERED PREDICTIONS — fixed before the flight
1. **26–31 Hz ring below V76's.** V83a's dose at the ring's operating point (100 km/h, R = 551 ct) is
   **96 = 0.42× V76** (flown ladder V76 227 · V81 310 · V80 496 = 1.00 / 1.37 / 2.19).
   **If the ring is not below V76's, the dose model is wrong and the damper is not what drives it.**
2. In-ring `MOTOR_TORQUE` below V81's **15**.
3. Engaged-vs-manual impedance asymmetry above **~60 km/h** vanishes (not 35 — `X[0]` = 2240 is where
   `Y[0]` stops being the *clamp*, but it keeps *weighting* out to `X[1]` = 3840 = 59.94 km/h).
4. 6–9 Hz ratchet **slightly worse** — magnitude cut to 32–33% at both 7.79 and 20.9 Hz, phase unchanged.
5. 18–22 Hz roughly unchanged.

### 🛑 FLIGHT INSTRUCTION
**≥60 s of MANUAL driving above 50 km/h.** Nothing else in V83a acts there, so it is a free within-drive
control isolating `0xC63A0`. Route 67 carried only 9 s.
⚠ **Expect a feel change at parking speed** — the `gain_A` restore returns 6× of creep r26 gain the car
has not had since V71c.
🛑 **Relay-ness does NOT order the ring** — V81 is the *least* relay-like of the three and rings hardest.
Do not write "removes the relay" as the rationale; it is **delivered dose at the ring's operating point**.

---

## 7. CAN TELEMETRY

🛑 **The gateway is a WHITELIST.** V53's FOURFRAME2 was mechanically correct and got **zero** frames, as
did stock IDs `0x19F`/`0x660`/`0x32E`. **A new ID can never reach openpilot — close that branch.**
Only `0x14A`, `0x18F`, `0x1AB` cross. **16 clean spare bits vs the 5 in use.** Hooks: 330 `0x55C0E` taken;
**399 `0x55D50` and 427 `0x55EFA` byte-stock on every build ever made.** 1,144 cave bytes free at `0xC4B78`.
Checksum helper `FUN_00057b24` is called last ⇒ **auto-covers** spare-bit writes.
Spec: `.claude/agent-memory/firmware-codepath-tracer/reference_accord_v83a_telemetry_spec_final.md`.

### `MOTOR_TORQUE` — the operator's question, answered
**Both halves are true.** openpilot's Honda port **never references `0x1AB`** and never registers it
(lazy `CANParser`), so `carState.steeringTorqueEps` is an **unpopulated capnp default** — the "always 0"
was never a measurement. **And on the wire it is live**: 50.00 Hz, counter increments 99.99%, all 16
checksum values used, **non-zero 22.4% of frames, max 321/1023**, largest during manual parking.
★ **It is a near-perfect ring detector** — the only non-zero run >0.2 s in seg 8 is t 40.99–52.37 vs the
bar's ring 41.03–52.34 (**+40 ms / −30 ms**), 0.00% before, 100.00% during, 0.00% after, replicated on all
three builds with the in-ring level **monotone in dose (4 / 15 / 20)**. **A free ring detector, no probe
bits.**
🛑 **NOT repurposed** — it is a live, checksum-guarded, DTC-0x16-class fault-monitored output of a 1 kHz
torque/current model. Plausibly a current-loop tracking residual, "small by design".
✅ Safety: panda's Honda safety model has **0 matches** for `0x1AB`/427/`MOTOR_TORQUE`; not in any RxCheck,
not forwarded (Bosch PT is bus 1; `get_fwd_bus` maps only 0→2 and 2→0), not TX-listed, no liveness check.

---

## 8. FactorD — the only lever that could serve both goals

**`gp-0x6a10` is an unsigned, unclamped angle-tracking-error magnitude at 0.1°/count** (anchored two
independent ways, not from FactorD's own breakpoints). X = `[0,50,100,150,700]` = **0/5/10/15/70°**.
Flat-unity in every mode, **never written by any build**, n=5 already ⇒ no code edit needed.

★ **Why it is structurally special:** for a given rate amplitude, angle scales as 1/ω — at 7.79 Hz the
excursion is **3.6× larger** than at 27.75 Hz. **A FactorD that increases damping with angle error
preferentially damps low frequencies.** That is the only frequency-selective mechanism in this firmware,
and it is exactly what FactorE cannot do: the damper's nonlinearity is **memoryless**, so shape changes
magnitude at *every* frequency identically and never phase.

🛑 **Two measurements gate it** (both are V83b probe rungs): `gp-0x6a10`'s actual excursion during a
grinding episode (the ring's column angle is p-p 1.29° ⇒ ~6 counts, likely deep in the flat segment), and
**`gp-0x67fe` ∈ {1,2}**, which is **NOT settled** — a later handoff explicitly re-opened the single V31P
measurement.

---

## 9. INSTRUMENT CORRECTIONS — carry these

| correction | detail |
|---|---|
| **`0x18F` is one CAN frame (~10 ms) stale vs `0x14A`** | Derived from an invariant: transmitted rate must lead transmitted angle by exactly +90°, so a lead-error constant in **ms** is a timebase offset. **Corrects every `cmd`→`bar` phase this kit has computed.** |
| **`band_envelope` is PEAK-TO-PEAK scale** | `H[m]=2·X[m]` then `abs(irfft())` gives `2·|s(t)|`, not an analytic envelope. Ratios/nulls/duties unaffected (common-mode); **absolute counts fed into physics were wrong.** Use `amp_at` / √2·RMS / Hilbert. |
| 🛑 **A ring-down through a bandpass MUST be quoted against a step control through the identical filter** | Both analysts independently fitted a filter's step response (apparent Q 9–11.6) and read it as plant damping. R² 0.987 proved nothing. |
| **`rate_f` (`0x18F` bytes 2–3) scale is ~25% low** | true ≈ −0.125, not −0.1 |
| **Duplicate `logMonoTime`** (1.7% of rows) | breaks `np.gradient`; silent NaN |
| **For N ≥ 5, only a phase-lock test establishes a harmonic** | f₀ drifts 0.576 Hz ⇒ ±4 Hz smear at 7f. Complex demodulation is drift-tolerant; fold arithmetic is not. |
| **The 3f fold contaminates the >80 km/h × 18–22 Hz cell** | 3f₀ folds to 17.41 Hz. Flagged, not re-cut. |
| **Two V76 images differ at `0xC63A0`** | flown `_v76_v38base_relu_damper` = 1024; superseded `_v76_gate_fb_arm5244_gateprobe` = **2048**. |
| **`build_v30_tva.py` calls `gp-0x69ca` "driver torque"** | **WRONG** — it is the angle accumulator. |

---

## 10. WITHDRAWN THIS SESSION

`k` as the dose metric (it is small-signal; the ring is large-signal — re-score at the operating point) ·
"the damper is phase-inverted at 27.75 Hz" (memoryless nonlinearity ⇒ phase is amplitude- and
shape-invariant; it stays ~112.7°, net dissipative) · "near-pure sinusoid ⇒ not a relay" (inverted) ·
"textbook relay signature" (3f/f = 1/3 does not discriminate; the 5th does) · Q = 23.7, Q ≈ 10, Q ≈ 7,
the Q amplitude-dependence, and linewidth Q = 103 · openpilot "~93%" and "~99% without the cap" ·
`df/dv` = −0.0547 (dose-confounded) · ">80 km/h damper duty 18.6%" (was the ring) · the "16.07% of engaged
time against a rail" figure as a highway statement (it is creep-only) · both cross-correlation lag
figures (inside flat plateaus) · the DTC-0x1d side channel (superseded).

---

## ⇒ NEXT

1. **Fly V83a.** 🛑 Flash decision and bus are the operator's; name the file back. Ship the ≥60 s
   manual-highway instruction and score against the five pre-registered predictions.
2. **V83b** = the telemetry cave (one virgin hook on `0x18F` + the `0x14A` splice, 8 bits) plus the
   `0x1AB` rungs for `gp-0x6a10` and `gp-0x67fe` — which gate FactorD.
3. **Restore V67/V68's gated r24 arm** (`0x3AA96` `C5`→`FB`, `0xC6446` 512→5244) as a separate variable —
   best measured grind #1 (0.524) and creep grind #2 → 0 bursts. ⚠ Its arm **rises to 2.46× at highway**,
   the wrong shape for the worst symptom; and **ship RULE 9's ~90 s engaged creep-cornering instruction**
   or grind #2 is unmeasured again (that has now happened on V67, V68 and V70).
4. ★ **Mode-26 `gain_B` records `0xD7A88`/`0xD7AC4`** — V69/V70's speed-shaped design was correct but
   written at mode 10 (inert). At mode 26 the cross-axis makes it **exactly 1.000× above 50 km/h by
   construction** — creep dose with structurally zero highway change. Never written.
5. **`gain_A` rec2/rec3** (`0xC6A90`/`0xC6AA4`) — the ≥50 km/h r26 records, **byte-stock in every image
   ever built.** If the highway grind is the target, that is the untouched cell that reaches it.
6. **The last inherited hop**: the aggregator-leg gain from `gp-0x6b08` to `gp-0x6b98` was not reduced to
   a single scalar. Topology and sign are closed; the transfer number is not.
