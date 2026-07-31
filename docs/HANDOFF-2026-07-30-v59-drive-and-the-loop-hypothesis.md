# HANDOFF 2026-07-30 — the V59 drive: the pump is real but marginal, and the operator reframed the problem as an uncompensated feedback loop

**Predecessor:** `HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md`.
**Session shape:** orchestrated. Four parallel subagents (probe decode, spectral, health,
`firmware-codepath-tracer`) plus a second tracer pass on the operator's hypothesis. Every
decision-bearing claim was re-derived by the orchestrator with a second method — and **three subagent
claims and three of the orchestrator's own claims did not survive that check.** Those reversals are
the most useful content in this document; they are recorded in full rather than tidied away.

---

## 1. What was driven

**V59 flashed and driven, route `2c` (`75604b0a432fdc89_0000002c--eb219f392c`), 9 segments uploaded
(0 1 3 4 8 9 10 11 12 — 2/5/6/7 were not), 50,963 frames, ~8.5 min.**

⚠ **It was not the pure creep route the spec asked for** — segs 4/8/9 are sustained road speed to
23.6 m/s. But it delivered the one thing route `2b` could not: **50.2 s of engaged + creep +
SUSTAINED hands-off** (`|lowpass(tq,3Hz)| ≤ 200`), across 13 runs.

### V59 is flight-clean
`steerUnavailable` / `steerTempUnavailable` / `canError` / `steerSaturated`: **zero**.
`selfdriveState` never enters `softDisabling`. `STEER_STATUS == 4`: **0 / 50,963**. Probe **100% live,
100% thermometer-monotonic, fault sentinel 0.000%**, stock low bits `& 0x07 == 0b111` with zero
exceptions. `0x14A`/`0x18F` lock at 99.999–100.008 Hz. Two boundary transients only: a `commIssue` /
`selfdrivedLagging` cluster at seg 0 t≈8.4 s **in `wrongGear` before the drive started**, and one
`controlsMismatch` with `immediateDisable=1` at the tail of seg 12 — **parked, vEgo 0.000, LKAS off**.
Neither is mid-drive.

---

## 2. What the probe answered — the pump is REAL, and MARGINAL

`gp-0x6ba6` is a **rectified** magnitude, so it sweeps the boost-amplitude LERP at **2× the mode
frequency**. Measured, engaged + creep + hands-off (13 runs, **K=30**, periodograms averaged across
disjoint runs, never spliced):

| | engaged | disengaged |
|---|---|---|
| thermometer own-spectrum peak | **42.19 Hz, prominence 11.10×** | prominence **0.00×** |
| 18–26 Hz band | 1.23× (i.e. nothing) | — |
| bit5 toggles | 25.55 /s | **never — 0/4 runs, 61.2 s, K=90** |
| index depth `<512 / 512-1k / 1k-2k / ≥2048` | 76.93 / 18.46 / 4.57 / 0.04 | **99.83** / 0.17 / 0 / 0 |

42.19 Hz is 2 × 21.09 to within one bin. **That is the full-wave-rectification signature**, and it is
completely absent when LKAS is not applying. `corr(env, lvl)` is **positive in 11/11 hands-off runs**
(median +0.487, +0.485 partialling out driver effort); **0 of 33** windows show the index sweeping with
no grinding line.

Depth, from a reconstruction validated against the ECU's own transmitted thermometer (**93.15%
per-frame agreement, best scale 1.00**): 38–46 Hz peak-to-peak gain modulation of **11.6%** on
`0xD28DC`, **22.1%** on `0xD2888`, **33.1%** series — against a **0.30%** disengaged control (≈110×).

### 🛑 But the threshold comparison is UNDECIDABLE, and that is the honest headline
`eps_crit ≈ 2/Q` needs the **passive** Q — the mode's damping when it is *not* being driven — and V59
contains no free decay to measure it from:
- **Ring-down: none exists.** 66 candidate decays, longest **0.63 cycles**. Envelope wiggle, not damping.
- **Autocorrelation analytic envelope** gives apparent **Q 22–1083** — but that is the coherence of a
  *driven* oscillation, not passive damping, and cannot be substituted into `2/Q`.

| assumed Q | eps_crit | verdict vs measured eps (0.020 / 0.104 / 0.169) |
|---|---|---|
| 13.6 (recorded, provenance never verified) | 0.147 | marginal — crosses only at p99 |
| 22 (lowest apparent) | 0.091 | above at p90 and p99 |
| 102 (median apparent) | 0.020 | above everywhere |

⚠ **What the coherence DOES support:** a Q=13.6 mode kicked by broadband road noise would stay coherent
~`Q/(pi*f)` ≈ 205 ms. Observed is 0.33–17 s equivalent. **Far more coherent than random excitation of a
lightly-damped mode can produce ⇒ there is an active, phase-coherent drive.** Consistent with the pump;
not proof it *is* the drive.

---

## 3. ★★ The turn: the OPERATOR reframed it as an uncompensated feedback loop

Mid-session the operator asked: *"is there a way to change the driver-assist logic to account for a
predicted driver-side torque due to LKAS command? Or maybe this is already in the logic?"*

**That reframing is now the leading explanation, and it displaced three builds' worth of analysis.**

The torque sensor sits between wheel and road. LKAS motor torque twists the column, **and the sensor
reads that twist as driver input.** Base assist boosts it → more motor torque → more twist. A plain
**linear** instability, needing no threshold argument at all.

### Three findings converged on it, same day
1. **MEASURED — the command→torsion-bar transfer function peaks at 21.09 Hz, the GLOBAL maximum over
   3–46 Hz.** 15.6× baseline hands-off (K=5, coherence 0.654 vs null 0.527); **25.7× at 20.70 Hz**
   any-hands (K=53, null 0.056).
2. **TRACED — no motor-command feedforward compensation exists anywhere.** `gp-0x6b98` appears exactly
   twice in the whole torque→assist chain: as a **sign** input to the `gp-0x6ac2` counter-torque
   detector (a **ceiling** in all 4 real consumers), and in `FUN_00043e44` whose output has **zero
   readers program-wide**. `FUN_00034a72`, `FUN_00034350`, `FUN_0003aa2c`: **zero references.**
3. **BYTE-VERIFIED — the only motor-reaction-aware term is off where it matters.** Damper `gp-0x6bd0`
   (sign forced to `-sign(gp-0x6abe)`) is **arithmetically zero below 35 km/h in all 34 mode tables.**

⇒ **At creep the loop has no compensation and no damping.**

### The retrodiction that makes it compelling — and its caveat
**V52C** lowpassed the **torque sensor** `gp-0x4f60` (α = 74/1024, fc ≈ 12 Hz, −6.1 dB at 21 Hz,
+61° lag) and **halved the mode** — the largest single effect any build has had, and the **only** lever
ever flashed on the **feedback** path. Every falsified lever sat on the *command* path. The loop
predicts this; the pump does not.

🛑 **But V52C's number was never re-derived under the corrected statistics**, and this kit's "halvings"
have been **median artifacts** before. **That re-derivation is step 1 of the next session** — it either
promotes the loop to the leading explanation or removes its best evidence. It is analysis, not a drive.

---

## 4. Structural findings — the golden model was wrong twice

### `FUN_00034a72`: the two amplitude curves do NOT multiply in series
The golden model rendered `scaled = (assist*y1)>>14; scaled = (scaled*y4)>>14` and flagged that block
as its one non-literal line. **It is wrong about the structure.** `0xD2888` scales the final assist
term (`sar 0xe,r13` @`0x35008`); `0xD28DC` enters much earlier (`shr 0xe,r28` @`0x34C26`) and is
**differenced against `gp-0x6a56`** then clamped ±12000. They compose multiplicatively only while that
subtraction and two clamps do not bind.

### ★★ Both LERP outputs are SLEW-BLENDED — a filter nobody had modelled
`0xCA06C[mode 10]` → `0xD2006` = **102** (Q10), applied to **both** amplitude-LERP outputs before they
multiply anything, persisted in `gp-0x69bc`/`gp-0x69ba`, lockstep-shadowed. **Direction confirmed
@`0x34be4`** (`cmp r25,r10 / ble` ⇒ instant snap when raw ≤ old): **FALLING instant, RISING slowed** —
a fast-attack / slow-release gain reducer. This is what pulls eps down from the raw-LERP values, and it
became V60's lever.

---

## 5. 🛑 Six reversals — the most useful part of this session

**Subagent claims that did not survive:**
1. **"`0xD28DC` is a dead end"** — argued from "3 image-wide refs to state cell `gp-0x69bc`, all
   in-function." **Structurally invalid**: a scan of a STATE CELL cannot show whether the blended value
   is consumed in a REGISTER the same tick, which is exactly what a slew-limited gain does. The
   orchestrator found `shr 0xe` @`0x34C26` inside the span the agent claimed to have traced; the agent
   then **retracted** and found the operand itself — `mulu r25,r28,r0` @`0x34c1c`. **Both curves are live.**
2. **`search_instructions` OVER-counted, twice** — 21 hits for `gp-0x6b70` of which **19 were false**
   (`jarl 0x0006b700,lp` substring collision); similar for `6bd0` (`0x00076bd0`). Every trap on record
   before this session was about *under*counting. **New trap class, now documented.**
3. **Off-by-0x1000 tp trap, fifth occurrence** (`tp+0x73a8` computed as `0xC73A8`; it is `0xC63A8`).

**The orchestrator's own claims that did not survive — recorded because the pattern matters:**
4. **Quoted coherence 0.795 as evidence** that the pump couples to the mode. It is **circular** — the
   index is arithmetically `|x|` of the bar, so 2f coupling is forced. Pooled against a circular-shift
   surrogate it does not clear the null (0.318 vs 0.312). What V59 actually establishes is **depth**.
5. **Called the FactorC damping lever "dead", then "disfavoured"**, on ~4 independent windows in a
   speed bin a second analyst independently found nearly empty. Too strong both times.
6. 🛑🛑 **RE-PROPOSED AN ALREADY-FALSIFIED LEVER.** Wrote `build_v61_tva.py` = FactorC `Y[0]` 0→64.
   **That is `V44` verbatim** (which used **235**, 3.7× stronger), flashed, **NULL** — because
   **Factor E re-zeroes the product downstream**; `V47` then attacked Factor E and got only "marginally
   quieter at 5 mph." **The operator caught it.** Script deleted unexecuted.
   **Two generalisable lessons:** (a) **a withdrawn RATIONALE is not a withdrawn RESULT** — V44's stated
   mechanism had been retracted, which made the address *feel* reopened; grep the address, do not
   re-litigate the reasoning. (b) **in a multiplicative chain, raising one factor is worthless while
   any other still zeroes the product.** The trigger pattern: **a new mechanism makes an old address
   look freshly motivated** — exactly when the check gets skipped.

---

## 6. Levers closed this session

- **Damper FactorC / Factor E** — V44 + V47, both flashed, both null. Closed, and now re-closed.
- **`gp-0x6b70` second-aggregator chain** — traced end to end: `FUN_00038148` → `gp-0x6b70` →
  `FUN_00037fe6` → `gp-0x6ad6` → `FUN_0003a382` → `gp-0x6ad4` → aggregator → `gp-0x6b98`. **All weights
  unity (1024) and stock ⇒ no hidden loop gain.** ★★ Its only output-shaping cal is **`0xC6AF0`, which
  V56 already zeroed and flashed: null + cost damping.** Since `gp-0x6ad4` has 2 accesses image-wide,
  that mute deleted the whole chain. **New structural fact kept:** boost and damper re-enter this second
  aggregator at unity gain, in parallel with `FUN_0003aa2c`.
- **FactorC float-mirror risk** — resolved NEGATIVE and it is worth keeping: `FUN_000347b8` *reads*
  `gp-0x6bd0` and only re-clamps with a recomputed **ceiling**; it never recomputes the four-factor
  product. The two ceilings are the **same table in two formats** (`INT 0xD209C X=[300,800]
  Y=[512,1024]` vs `FLOAT 0xC6554 300.0, 800.0, 0.5, 1.0`). Damper authority at creep is
  firmware-clamped to **±512 of the aggregator's ±10240 (≤5%)**.
- **`0xC63BA`** — byte-verified 2-stage EMA (α = 0.5), blast radius fully contained (2 reads, both in
  `FUN_0003b66a`) — but **partial by construction**: it filters only the **torque** lane, and the index
  is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`). Both analysts were right.
- **The damping SIGN question, open since V58** — closed. `-sign(gp-0x6abe)` @`0x3469e-0x346a2`,
  textbook velocity-proportional damping, correct by construction.
- **`0xD2018`** — record correction: it is **data**, a pointer inside `FUN_00035154`'s `0xC7888[mode]`
  ceiling array, and `FUN_00035154` is simply the `gp-0x6bbe` analog of `FUN_000347b8`. Same pattern,
  not a stronger mechanism.

## 7. Confirmations

- **The frequency law is rejected a SECOND time.** Route 2c: `a = 0.177` rejected at **2.60σ**
  presence-tested (n=19, 9 runs), up to 7.08σ raw; `a = 0` fits at every cut, flat 20.4–21.1 Hz.
  Crucially the fitted subset is **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728).
  ⇒ **fixed ~20.9 Hz is now the record.**
- **V58/V59 control PASSES** — grinding statistically identical: 7 of 8 jointly speed-and-effort
  matched cells in 0.76–1.41× with no systematic direction, peak frequency within 0.7 Hz everywhere.
  Exactly what CAL-CRC-unchanged predicts.
- ⚠ **"Creep-only" needs qualifying**: true for the **hands-off** arm, but there is a second population
  at **10–13 m/s under driver load** (prominence 174–651×), verified **not** a tyre order (frequency CV
  2.2% vs order CV 9.8%). Correct wording: *strongest at creep 1–4 m/s; sampling gap at 6–10; coherent
  at 10–13 under load; absent above 14 m/s.*
- ★ **Route 2c contains hands-off engaged creep RATCHET episodes** — 7.56 ± 0.36 Hz, within-run sd
  0.07–0.10 Hz, prominence median **783×** (max 2142×), 15 windows / 5 runs. The record said route 2b
  gave zero and a dedicated route would be needed. **Mode identity unconfirmed** — found incidentally.

---

## 8. Built this session: V60 (UNFLASHED)

**V60 = V59 + ONE calibration byte:** `0xD2006` **102 → 43**, the boost-amplitude blend rate.

```
5 bytes off V59  (1 cal byte + its [0xD2000,0xD2FFC) block CRC)
⭐ MAIN CRC and CAL CRC both UNCHANGED = machine proof the cave/probe and every 0xC6xxx cal stayed put
91 bytes off V38.  50/50 CRC blocks pass.  RWD round-trips.
image SHA 6328cff064598cac8d9a7a4147626c8b55ddbad2e586ac3e1b8fca9c9459be5c
RWD   SHA 519aaab4908844d6a240d48f50d8a523b39353a3a4e3bffeb3de4bb4e1d19787
```

Attenuates the 42 Hz pump **without moving the static gain map** — the blend converges to the same
steady state, so DC assist and manual feel are untouched. Predicted **eps p99 0.169 → 0.099**.
🛑 **The effect SATURATES** — the falling edge is instant regardless of the coefficient, so it buys
~1.7× then flattens (cal 32 only reaches 0.086); **43 is the knee.** GATE 1 vacuous. GATE 2: base-assist
path with **no LKAS-only decoupling point anywhere in this chain** (traced) — but a pure *dynamics*
change on a gain-**scheduling** variable, adding no gain and moving no static map. Blast radius
byte-verified: one pointer (`0xCA094`); the three identical 102s in `0xD2000` are modes 10/11/12's
**independent** entries.

⚠ **Expect it to be NULL.** It attacks the pump, and the pump now looks like a passenger. **Fly it as a
DISCRIMINATOR** — a null closes the parametric mechanism and leaves the loop standing. V59's probe rides
along unchanged and is the **CONTROL** (it reads upstream of the blend).

---

## 9. Next steps

1. ★★★ **Re-derive V52C's result under the corrected statistics.** Before any new build. Analysis only.
2. ★★ **Flash V60 as a discriminator** on a creep/hands-off route; decode with
   `rlog-tools/decode_v59_boostindex.py` and check the index distribution returns identical to V59.
3. 🛑 **Loop phase margin needs a firmware-side probe** — one 100 Hz mailbox sample is ~76° at 21 Hz.
4. ⚠ **Base-assist loop gain (`0xCA154[mode]` → `0xD2834`) is the untested handle** — and a **direct
   trade against steering weight, so it is an operator decision.** Grep it and state its history first.
5. **Re-run the strict-band analysis over V55/V56/V57** and re-derive the historical amplitude baselines.
6. ★ **Verify the route-2c ratchet episodes** before building on them.

🛑 **Flash only on explicit operator instruction naming the file and the bus. Kill openpilot/pandad first.**
