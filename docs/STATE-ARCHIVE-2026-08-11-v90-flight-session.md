# STATE ARCHIVE — the 2026-08-11 V90-flight-session headline, verbatim

Split out of `docs/STATE.md` at the 2026-08-12 close-out to hold the file under its size cap.
**This is a RECORD, not an instruction. Do not reason from it.** It was already self-labelled
*retained for the reasoning, NOT for its status* before it was moved, and several of its
conclusions have since been overturned by the V94 flight — in particular its section A1's
`gp-0x6bbe` = "base-assist output" identification (see
`memory/reference-accord-gp6bbe-is-rate-derived-not-base-assist.md`) and every statement that
treats `gp-0x6b26` as an inertia term (see `memory/accord-v94-flew-and-the-lane-is-a-damper.md`).

---

## ⊕ SUPERSEDED HEADLINE, 2026-08-11 (V90 flight session) — retained for the reasoning, NOT for its status

Narrative: **`docs/HANDOFF-2026-08-11-v90-flew-and-the-lever-search-closed.md`.**
Flight scoring: `docs/SCORING-2026-08-11-v90-flight.md`.

### A. WHAT IS ON THE CAR, AND WHAT HE REPORTS
**V90**, route `00000077--7411859c54`, 21 segments, 1245.3 s, cache `_cache_r77/`.
**Engaged 1074.6 s = 17.91 min = 86.41 %**; ≥50 km/h 316.4 s; ≥80 km/h 42.0 s; v_max 90.4 km/h;
micro-ratcheting regime (1–13 °/s) 437.6 s · ratcheting (13–50 °/s) 196.0 s · macro 76.7 s.
**FAULT-FREE**: `STEER_STATUS` {0: 124,358, 3: 3}, DTC-active duty **0.000000**, 0 sentinels,
`CONFIG_VALID` 1.0000, no EPS entry in 3,489 `onroadEvents`.
**IDENTITY PASS, parameter-free and single-frame: `b4 == 0` on 124,362 / 124,362 frames** — impossible
on V86B/V87/V88/V89, where `b4` railed at 1.0000 over 254,085 frames.

🛑 **V90 IS PROBE-ONLY — byte-identical to V89 in every calibration cell.** So the operator's report is
the **control condition**, not a failed fix:
> *grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt on the highway-speed
> curves or lane changes · parking lot testing · highway and street level testing.*

**NOTHING IS FIXED. All three symptoms are present.** Every band number in this file is an instrument
reading. **A band moving is not a symptom being fixed.**

His mechanism, this session: ***"the ratchet is just on a DC LKAS command."*** His constraint:
***"I do not want to just apply a damper which also limits LKAS max steering angle rate on max LKAS
command."*** And his return observation: active return-to-centre feels restricted **even when LKAS is
aligned with the return direction** — adjudicated in §D below.

### B. 🛑 SIX LEVERS CLOSED — FIVE OF THEM ON ARITHMETIC, NOT ON A NULL
A lever killed by arithmetic cannot be re-opened by more exposure or a bigger dose. **Do not
re-propose any of these.**

| lever | why it is closed |
|---|---|
| **`0xCBE74`** friction-comp gain | **No larger dose exists, ever.** int32 wraparound in `FUN_00036c12`'s `mul r13,r6,r0` (×0x111, high half discarded, **unclamped and UPSTREAM of `0xC407E`**) is structurally impossible only for **≤ 1.6005×** ⇒ **×1.5 is 94 % of the lever's ENTIRE range.** And at ×1.5 the delivered damping is **5–69× below the resolvability floor** in every band (0.16 % of the 208 ct engaged median at 6–9 Hz, 1.20 % at 18–22, 2.15 % at 26–31). ⚠ Flown anyway as V91, by the operator's explicit decision — §E |
| **`0xC63A6`** friction-lane Path-2 weight | **Inert in the regime, on a PRE-REGISTERED threshold.** Micro-regime `\|gp-0x6b26\|` **p50 = 7.1 counts = 0.22 %** of the ±8192 residual clamp, against a stated **≲32 ct do-not-fly** line. It failed a bar written before the number existed |
| **the `Kd` cut** (`0xC6AE6/E8/EA/EC`) | **A TRADE whose cost is 3–4× its benefit.** `Re(Z)` extended to 35 Hz: **D pumps ONLY 2–12 Hz and DAMPS 16–35 Hz.** Removing the +0.077 pump at 6–9 Hz costs **−0.217 at 18–22 (2.9×)** and **−0.336 at 26–31 (4.4×)** — the operator's own two grinding bands |
| **K1 / friction** (`0xC40D2`) | **STRUCTURAL, not a power problem.** Above 1 °/s friction and `\|model\|` are near-collinear: `P(b5\|b6=1)` = 0.986 → 1.000, discriminating cell `(b6=1,b5=0)` = **0.63 %** of engaged frames. The term cannot be moved independently of the model in the regime he names |
| **term 0 / mixer lane 2** into `gp-0x6ad6` | **Severed by one zero constant.** `0xC616C` (`tp+0x716c`) = **0** on stock, on the flown V90, and in every build script (0 grep hits) ⇒ `gp-0x6b76` is 0 or a `0x7fff` sentinel on every path ⇒ lane 2's contribution is **unconditionally zero** |
| **`0xC520C`** governor ceiling as the return explanation | **Misses by 8.3×** — §D |

### C. 🛑🛑 THE SESSION'S BIGGEST OPEN QUESTION — THE ANTI-DAMPING IS **NOT** THE PID
```
   at 6-9 Hz:  P -0.145   I -0.053   D +0.077   =>  NET -0.121  == DAMPING
   measured Re(Z) at 6-9 Hz = -3375 ct*s/rad    ==  ANTI-DAMPING   (coh 0.769 vs shuffled 0.001)
```
🛑 **Two opposite sign conventions are in play and confusing them inverts this.** Per-term dissipative
products (the D-sweep's convention): **negative = damping**. `Re(Z)`: **positive = damping**.

⇒ **The anti-damping is NOT coming from `FUN_0003a382`.** It is another aggregator lane, or the plant.
**[EVIDENCE for both halves; BELIEF as to which.]** **Every remaining firmware candidate must answer
this** — a lever that trims a PID term trims something already on the damping side of the ledger.

**`Re(Z) < 0` replicated at 37× V89's exposure** — 221 windows / 884.5 s, **−3375 at 6–9 Hz** against
V89's ≈ −3300 on an independent drive; phase −125° to −152° against inertia's predicted +90°
⇒ **inertia refuted again.** ⊕ **`Re(Z)` FLIPS SIGN at ~26 Hz**: anti-damped 2–26 Hz, **positively
damped 26–35 Hz** ⇒ **grind #2's band is not anti-damped at all** — corroborating §F's dissociation
from a second, unrelated instrument.

> 🛑 **AND ONE EXPERIMENT NOW GATES THE WHOLE REMAINING SEARCH.** If the 2–26 Hz anti-damping lives in
> the **PLANT** rather than the firmware loop, **no firmware lever can remove it** — firmware could
> only *add damping against* it, and the available damping levers are spent (§B).
> **The measurement that separates the two is the MANUAL HANDS-OFF COAST, and the entire corpus
> contains 2 windows / 21.4 s of it.**

**~15–20 minutes of driving.** Yield 0.25 qualifying windows per second of continuous hands-off time
⇒ **~6 runs of 30 s** = usable-but-wide (≈40 windows); **~14 runs** = precision comparable to the
engaged arm (≈100 windows). Half at 30–50 km/h, half at 60–80 km/h. **It yields 12–16 clean ring-down
edges for free**, against the 1 the corpus has.
**Manoeuvre:** straight/empty/level road → **disengage with the CANCEL BUTTON, not the brake, not by
grabbing the wheel** → hands off, foot off the brake, steady throttle → coast 25–30 s → re-take
normally; hold ~5 s of steady engaged driving *before* pressing cancel so the edge has a pre-state.
**Invalidating:** any braking · `steeringPressed` · re-engaging · leaving the speed band · a gear
change · stopping · any steering input.
🛑 **Safety is the operator's judgement.** Hands off on a moving car — good surface, no crosswind,
short runs, hands within inches of the rim. **A missing control is a far better outcome than an
incident.**

### D. THE RETURN COMPLAINT — the mechanism exists and it does NOT bind
**No discrete `if (LKAS != 0) suppress return` branch exists anywhere in this firmware** — scoped
`search_instructions` over `FUN_00036388` (206 instr.) and `FUN_000360fe` (72), all five candidate
LKAS cells, **zero hits, `truncated:false`**. Both candidate hard gates closed: `gp-0x67ac`
structurally unreachable; `gp-0x67fa` decoupled from LKAS engagement (33-writer census).

**What exists:** return-centre (`gp-0x6b62`) and LKAS's own in-aggregator term (`gp-0x6b4c`) are
unconditionally summed and capped by a **motor-rate-adaptive governor ceiling** (`gp-0x4f64`, table
`0xC520C`). **Then it was measured (`rlog-tools/v93_return_to_centre.py`, 4 routes) and it does not
bind:**
- pooled engaged returns (27,914 samples) **median 127.2 counts** vs a first breakpoint at **1050**
  ⇒ ceiling stays at the **full 5325**, the onset is **8.3× away**. Duty above X2 = 0.00018, X3/X4 = 0.
- **40–80 km/h is definitively inert**: p50 **11.0**, **max 35.0 counts (7.4 °/s)** against a
  **222.8 °/s** onset. Zero samples ≥ 80 km/h.
- Not scale-sensitive: even at the disfavoured 10.0 scale the median still gets the full ceiling; the
  *median* return would need a scale **8.25×** the on-car-arbitrated 4.7121 to reach X0.
- ★ **The real binding test**: a falling ceiling only binds once it drops **below** the command. LKAS
  alone at 4× (1782) is capped from **3414.3 ct = 724.6 °/s — 1.3× beyond the hardest correction in
  four routes** and ~28× an ordinary return.

⇒ 🛑 **`FEASIBILITY-8X-LKAS.md` Part 2 (*"even at TODAY's 4×, moderately fast steering already clips
here"*) is REFUTED. Part 1 is CONFIRMED.** ⚠ Caveats pull opposite ways (`gp-0x6ac0` is rectified and
EMA-filtered ⇒ counts are upper bounds, *strengthening* the null; the column→motor conversion is
biased low ⇒ *weakening* it at the tail). **The median's 8.3× margin is robust to both; the p99/max
results are not, and no conclusion rests on them.**
⚠ **This says nothing about whether `0xC6CD0` should move** — a standing ★★★★★ memory freezes the 4×
gain.

### E. V91 — BUILT, VERIFIED, UNFLASHED · V92 — CUT, VERIFIED, UNFLASHED
**V91 = the flown V90 + 12 calibration bytes.** No cave change, no code change.
```
0xD7A5C  mode 26 (ENGAGED) friction LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)
0xD7A6C  mode 27 (ENGAGED) friction LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)
image sha256  0ea15ca9d5f811ddcf915b33237dc3f686461f6b84afb7c476e9f1d2b8a011b1
rwd sha256    217f9cef33eaf2544b82bc2c99e8b9e6e5ee3f09bdbe523cfc3014e722b17c0b   (986,042 B)
rwd  39990-TVA,A160-V91-V90BASE-CBE74.M26.M27.X1.5-0x13000-0x100000.rwd
```
> 🛑🛑 **THE HONEST LABEL: V91 is the SAME LEVER at the SAME ×1.5 DOSE that flew on V74 and V75, and
> BOTH of those flights HARD-FAULTED** with a latched total loss of power steering. The single
> difference is `0xC407E`: every artefact that ever carried this dose also carried **850**; V91 carries
> Honda's **511**, one count under the DTC-0x1d monitor's 512 trip. **ZERO flights have ever separated
> the dose from the 850 interlock — the separation is STRUCTURAL, never empirical.** V81 (route 67,
> fault-free) is a control for the **INTERLOCK ONLY** — it is byte-stock on the friction row in all 34
> modes, so it says nothing about the dose. **Writing only modes 26/27 is a DELIBERATE NARROWING from
> V74/V75's 14 records, not a reproduction.**

**Why it is flying anyway:** the operator's decision with the sizing verdict in front of him —
*"we are flying regardless, so the instrument is free."* Recorded as his call, not as this session's
recommendation. **Score it with `SCORING-2026-08-11-v90-flight.md` §10.1–10.6 exactly as written.**
- **Dose-in-force arms run FIRST**: engaged cell-stratified ratio must read **1.50 ± 15 %** with a CI
  excluding 1.00 · **manual must read 1.00** (it scales ⇒ wrong record ⇒ **pull the build**) · flat
  across every speed bin. 🛑 **If the ratio's CI contains 1.00, every band result is UNINTERPRETABLE**
  — V64's null was on the gate and was read as a result for weeks.
- **Revert triggers**: clamp duty above ~0 at ±511 (repeated `wire == 319`) — a railed lane is
  `sign(gp-0x6c2c) × 511`, **a Coulomb relay, the V80 mechanism itself** · `e_26-31` ≥ 1.50 outside the
  placebo band · **≥3 consecutive order-vetoed engaged windows with `p_26-31` > 37.12** (threshold
  fixed from route 77 alone before V91 existed; **measured false-positive rate on the reference build:
  ZERO**) · **the operator, overriding all of them in both directions.**
- ⚠ **The predicted effect STRADDLES the detection floor** (upper bound +50 %, lower bound 0; floor
  ±16–22 % contrasted, ±33 % raw). **If it nulls below ~16 %, that null means nothing** and his report
  is the primary endpoint. ⊕ Under friction-induced vibration the response is **threshold-like**, so
  "≈ nothing" and "a lot" are the likely outcomes and a clean ~18 % is the least likely.
  🛑 **But the usual "then dose higher" consequence DOES NOT APPLY — there is no higher.** If ×1.5
  nulls, the next step is a **different lever or injection point.**
- ⊕ **Costs nothing, buys the most: fly it on the SAME ROUTE as 77.**

**V92 = V91's 12 calibration bytes (IDENTICAL) + a 116-byte cave (43 instructions) + a 2-byte 427
repoint + a 1-halfword 427 scaling fix. FIVE edits.**
✅ **CUT, VERIFIED, UNFLASHED 2026-08-11. 198/198 assertions** (178 dry-run + 20 that only run on a real write). Reproduces bit-for-bit on a second run.
image sha256 **`c8e89fe35ebc445e4c4b19663ba9655dfeb8ba5cada2172aeb033eeb9f9eb939`**
rwd   sha256 **`388a1974d5702e17fded074457632092189eb55d806aefd4600e17d58e974245`**
`39990-TVA,A160-V92-V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4-0x13000-0x100000.rwd` (986,042 B)
Diff vs V90: **10 runs / 119 bytes, ZERO unattributed**; 140 attributed (12 cal + 2 repoint + 2 scale + 116 cave span + 8 CRC), 21 cave bytes coincide with V90's and the `sar` halfword moves only its high byte. CRC trailers **derived in code** = `{0xC4FFC, 0xD7FFC}`; chain 50/50 on the image, the readback and the shipped `.rwd`. `[0xD7000,0xD8000)` **byte-identical to V91's image**. V90 and V91 artefacts re-hashed after the cut and unchanged. Ghidra's own disassembler decoded the built cave end-to-end: **43 instructions, 116 bytes, all 7 branch targets on instruction starts, conditions only {bge, bnh}**.

⊕ *(superseded note)*  The payload changed after the artefacts
that were on disk during this close-out (`b4` swapped from `sign(gp-0x6abc)` to `gp-0x6bda`-in-window;
cave 110 → **116 B**; the 5th edit added).
**Re-hash from disk after the real cut. Do not flash on the strength of this section.**
Artefact token: `...-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4`.

> ### 🛑🛑 SUPERSEDED V92 ARTEFACTS — NEVER FLOWN, DO NOT FLASH
> An earlier V92 cut **this session** — image **`b092bf19db04f580…`**, rwd **`630248a53393fcc2…`**,
> **182/182 assertions, from-disk verified** — carried the **OLD rung map: `b4 = sign(gp-0x6abc)`, a
> 110 B cave, and no 427 `sar` fix.** It was superseded before flight by the `gp-0x6bda`-in-window swap
> and the `0x55E10` `a332`→`a432` no-clip fix.
> 🛑 **Those two hashes appear in this session's transcript with a complete PASSING assertion log
> behind them. They are DEAD.** Renamed on disk to
> `SUPERSEDED-DO-NOT-FLASH-_v92_OLDRUNGMAP-b4.6ABC-NEVER-FLOWN_plain_image.bin` and
> `SUPERSEDED-DO-NOT-FLASH-39990-TVA,A160-V92-OLDRUNGMAP-b4.6ABC-NEVER-FLOWN-0x13000-0x100000.rwd`;
> both will be deleted at the real cut. **General lesson: standing corrections, NAMED TRAP 10.**
>
> **DEAD hashes written out IN FULL, so that grepping the transcript's own string lands here:**
> ```
> DEAD - image  b092bf19db04f58047a58eeefeb784f63ff8655c573493e8d2c7f63bf4dfdce2
> DEAD - rwd    630248a53393fcc2470b66b709604e0d43cffc87fdcbf3d7962061947467fb11
> ```
> ⊕ **The BUILDER caught this and pushed back on the orchestrator's own proposed filename, which had
> called them a "dry run". They were not — they were a real, fully-verified cut, and that distinction
> is the entire hazard.**
🛑 **V92 IS A MEASUREMENT BUILD WITH A SUB-FLOOR CAL EDIT RIDING ALONG — NOT A DOSE BUILD.** Its
own header says so: the dose is **5–69× below the measurable floor**, so **the operator's report is
the PRIMARY ENDPOINT and the telemetry is the point of flying it. Do not expect the 12 calibration
bytes to show up in any band statistic; if they do, that is a surprise to be explained, not a result
to be claimed.** The V91 honest label above applies to V92 **in full and verbatim.**

🛑 **THE FIRST BUILD EVER TO WRITE CAN `0x14A` BYTE 7** — every cave V53→V90 wrote byte 4 bits 7:3 and
nothing else; the field grows **5 → 7 bits**. Payload (`0x18F` untouched, ONE hook):
`byte4 b7` `gp-0x6bbe < 0` (**sign of the BOOST lane**) · `b6` `gp-0x6b62 < 0` (**sign of the
RETURN-CENTRE lane**) · `b5` `gp-0x6b62 ≠ 0` (**lane LIVE** — separates the confirmed disable branches
from "tiny") · **`b4` `gp-0x6bda ∈ (−397, 384)`** (**the outer-gate-OPEN bit — see the validator note
below; it is what makes `b6` interpretable at all**) · `b3` fingerprint ≡ 1 ·
**`byte7 b7` `|gp-0x6b26| ≥ 15` = DOSE-IN-FORCE** (`T=15`, duty **0.242 → 0.339**; needed because 427
has moved off `gp-0x6b26`) · **`byte7 b6` `gp-0x6a82 > cal(0xC627E)=20` = the DWELL-RELAY SNAP STATE.**
**427 = `clamp(|gp-0x6bbe| × 5 >> 4, 0, 0x3FF)`** after the scaling fix.
⚠ **`sign(gp-0x6abc)` — the raw-motor-rate CONVENTION ANCHOR — was DROPPED to make room for `b4`.**
The builder's own wording for the cost: ***"recoverable at DC, unrecovered in the 6–30 Hz bands where
band-resolved phase claims live."***

★ **IDENTITY, single-frame and disjoint BY CONSTRUCTION: any frame with `0x14A` byte7[7:6] ≠ 0 proves
V92 is on the car.** No build V53–V91 can produce it — `gp-0x1511`'s only two writers (`0x55C02`
`andi 0xcf`, `0x55C2A` `andi 0xf0`) **explicitly mask bits 7:6 off**, verified two ways. It does not
depend on trusting any prior build's measured duty.

🛑🛑 **THE `(b4, byte7 b6) = (0,0)` VALIDATOR — "SHOULD NEVER OCCUR" IS WRONG AND IS WITHDRAWN.**
`b4` exists because `|gp-0x6b64| < cal(0xC618A) = 1024` fires for **two physically different reasons**
— a genuine low wheel rate (a real detent) **or the outer LERP gate simply being shut**
(`Y1 = 0` outside `(−397, 384)` ⇒ `gp-0x6b64 ≡ 0` ⇒ trivially `<1024` ⇒ a flat −1024 bias, not a
relay). **But a shut gate SATISFIES the arm condition every tick, so the dwell counter CLIMBS to its
ceiling of 21 rather than staying down — and the climb takes 21 ticks at 1 kHz = 21 ms, during which
`b4` is already 0 while `b6` is still 0.**
⇒ **`(0,0)` occurs for ~21 ms after EVERY gate-shut edge — roughly 2 frames at 100 Hz per event.**

> **CORRECTED PRE-REGISTRATION: `(0,0)` is RARE and ALWAYS ADJACENT TO A `b4` FALLING EDGE. A
> SUSTAINED `(0,0)` RUN is what indicts the rung map — a handful of frames per event is the instrument
> working as designed.**

🛑 **A scorer expecting *never* would see a few frames per event and pull a working build.**
⊕ **And the correction STRENGTHENS the design rationale**: because a shut gate **ARMS** the counter
rather than disarming it, **`b6 = 1` is the DEFAULT state whenever the outer gate is shut** ⇒ **`b4`
is not a nice-to-have partner for `b6`; without `b4`, `b6` has no baseline.**
⊕ 🛑 **THE GENUINE never-occurs validator is a DIFFERENT cell, and keeping the two straight matters:
`(b6, b5) = (1, 0)` IS structurally unreachable** — both bits read `gp-0x6b62`, so it cannot be
negative while also being zero ⇒ **12 of the 16 odd `byte4` codewords are reachable.** That one is a
real correctness check; `(0,0)` is not.

🛑 **TWO MORE THINGS TO CARRY INTO THE SCORING:**
1. ⚠ **The detent may not arm during a SUSTAINED ratchet** — ~8 ms of near-zero signal per zero
   crossing at 7.79 Hz against a 20 ms arm time ⇒ **read a low duty as "trigger, not sustainer", NOT
   as a null.** Both rails are informative, which is what justifies the bit.
2. ✅ **The 427 saturation residual is FIXED in the cut, as the fifth edit.** At `sar 3` the packer
   would have saturated at `|gp-0x6bbe| ≥ 1639` (the lane's window is ±2048), going flat over the top
   ~20 % of its range. `0x55E10` `a332` → `a432` gives `|x|×5>>4`: max **640/1023, never clips**, half
   the resolution. 📋 The builder **reported and named** the fix rather than silently applying it,
   because the brief scoped the repoint to exactly 2 bytes; the widening was then authorised. **That
   is the escalation path working, not a scope violation.**

⊕ **Deliberate: ONE `0x14A` hook, not a second on `0x18F`** — a risk-class argument, not a capacity
one: a never-flown hook is exactly the "novel cave/hook combination" class this kit's three bricks
(V24/V27/V48B) came from. ⊕ **`b5`/`b6` were freed by a MEASUREMENT** (the (b6,b5) collinearity above),
not a guess. ⊕ **Not one of the 116 cave bytes is hand-encoded** — all copied from Ghidra-verified
twins with 116/116 coverage asserted before the build will run; that is what defeats the
`subr`=`8031`-vs-`satsubr`=`3080` trap, the `ld.h`/`ld.w` shared-hw1 trap, and the `ld.bu` op-field
`0x3D`-not-`0x3C` trap. GATE 1 verified fresh (loads only, no new RAM claimed, scratch r6/r7 only,
asserted mechanically); GATE 2 vacuous for the cave and V91's argument for the cal edit. **Two CRC
trailers, derived in code from the image's own 50-block map.**

### F. THE DISSOCIATION — the ratchet and grind #2 are NOT one problem
2,032 engaged windows / 286 blocks / four routes, 35.2× load range, route fixed effects, block
bootstrap, every coefficient a **contrast against the 32–38 Hz control**:

| axis | 6–9 Hz (ratchet) | **26–31 Hz (grind #2)** |
|---|---|---|
| `log\|cmd\|` all engaged | **+0.219 [+0.103, +0.338]** ✔ | **−0.075 [−0.135, −0.012]** ✔ |
| `log\|cmd\|` highway | +0.082 n.s. | **−0.163 [−0.258, −0.055]** ✔ |
| `log v` highway | **−1.162 [−1.497, −0.840]** ✔ | **+0.554 [+0.278, +0.825]** ✔ |
| `log\|rate\|` highway | +0.239 ✔ | **+0.553 [+0.442, +0.651]** ✔ |
| `log\|lat accel\|` highway | +0.034 n.s. | −0.080 n.s. |

🛑 **Opposite signs on BOTH the load and the speed axis, all four CIs excluding 0.** The hypothesised
replication onto grind #2 **fails by reversing, not by going null.** ⇒ **no evidence one lever touches
both**; anything reducing command load would, on these coefficients, make 26–31 Hz *worse*.
**[EVIDENCE for the coefficients; BELIEF for the mechanistic reading.]**
⚠ The ratchet's load coefficient replicates in **DIRECTION but not MAGNITUDE** (+0.219 vs the corpus's
+0.950) — this spec carries `log v` as a competitor and pools four routes. **No size claim is made.**

⊕ **Lateral acceleration is NOT the "curve" covariate** (null at 26–31 Hz on the highway cut). His
*"highway-speed curves and lane changes"* is carried by **wheel rate**: an established constant-radius
curve has *low* wheel rate; a lane change has high wheel rate. 🛑 **This CORRECTS the driving
protocol** — *"curves beat lane changes for yield"* is withdrawn. **Deliberate lane changes are the
primary instrument**: ~60–80 spread across many distinct stretches, plus winding highway, cloverleaf
ramps, continuously tightening/opening bends. **Avoid long steady sweepers** — they inflate the
≥80 km/h seconds while yielding almost nothing.

🛑 **Grind #2 is essentially UNEXPOSED**: engaged, v ≥ 22.2 m/s, |rate| ≥ 5 °/s = **7 / 33 / 1 / 6
windows** on routes 73 / 75 / 76 / 77. On the loosest populated cut the **same-firmware** r77 ÷ r75
pair returns `e_18-22` **1.504 [1.184, 1.732]** ⇒ **no grind-#2 claim is supportable in either
direction.** Needs **~15 min engaged above 80 km/h, lane-change-rich, ≥20 blocks, ON EVERY BUILD BEING
COMPARED.**

### G. WHAT V90 SETTLED [EVIDENCE]
1. **The observer gate NEVER fails** — `gp-0x6c00 < 0` on **0 of 124,362 frames**, 20.49 minutes,
   engaged and manual, every wheel-rate bin. Never measured before.
2. **`gp-0x6b26`'s full distribution, and ZERO clamp duty in every stratum.** Engaged p50 5.5 / p90
   39.1 / p99 114.3 / **max 319.1** against the ±511 clamp; wire saturation 0.000000 ⇒ every sample is
   an honest measurement. **The lane is not a relay today.** Clipping ladder 1.60× / 2.75× / 4.45×.
   🛑 **That is a CLIPPING ladder, NOT a dose budget** — the int32 wraparound at ≈1.6005× binds first,
   and **×2.75 would WRAP, not pin: a full-scale sign inversion delivered before the clamp meant to
   contain it.** ⚠ The extrapolation is open-loop and therefore conservative, but still an
   extrapolation; the binding strata are **ratchet 13–50 °/s and 5–20 km/h**, not highway.
3. 🛑 **"THE FIRMWARE CANNOT SEE THE 6–9 Hz MODE" IS REFUTED.** `R(f) = |B26/W|/|H|`, normalised at
   2–4 Hz where column and motor are rigidly coupled (all scales cancel): **2–4 = 1.000 · 6–9 =
   **1.016** (coh² **0.438** vs shuffled 0.001, the highest of any low band) · 9–12 = 0.730 · 15–22 =
   0.996.** **R is FLAT — no dip.** Aliasing cannot rescue it (shared alias energy would *decohere*).
   ⇒ **the damping lane goes back in play for the ratchet** — 2.99 vs 6.80 authority per °/s = **2.3×
   less, not zero.** What *is* attenuated toward the motor is the narrow **7.8 Hz LINE** (arg-max
   fraction 0.327 ≈ chance in motor rate vs 0.482 in the column), **not the band**. Unexplained.
4. **No measurable grinding regression from V89's K1 = 204** — `e_18-22` V89(+V90) ÷ V88 on three
   strata, all ≤ 1.03 and **FLAT** against their own constant-build placebo bands. The one stratum
   reading a rise (1.451 at v ≥ 20.46) is a **stratum artefact**: 37 V89 + 2 V88 windows carry the
   whole flip against the v ≥ 22.2 stratum's 0.986, both run on 3 V88 episodes, and the
   *no-hypothesis* placebo band `e_10-16` also reads "resolvable" there. ⇒ **reverting `0xC40D2` is
   neither supported nor contraindicated.** **Power: this corpus cannot resolve an `e_18-22` change
   below ≈ ±20 % (all-engaged) to ±30 % (order-vetoed).**
5. **The b6 threshold (512), V90's one guessed parameter, landed inside its predicted 0.10–0.50
   bracket** at 0.2535 ⇒ **do not move `0xC4B4A`.**

### H. STRUCTURAL CORRECTIONS TO THE MAP — several overturn settled entries
- 🛑 **`gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, ALWAYS, ON EVERY BUILD.** `gp-0x3d8c` sums `gp-0x62c8[0..10]`;
  the per-lane role dispatch (`0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]`) writes an explicit **zero** or
  does not write at all, **role 7 never appears on any build**, and the `.data` boot initialiser is
  **22 bytes, all zero**. ⇒ the shaper's `iVar45 = gp-0x6afe + uVar34` reduces to `iVar45 = uVar34` —
  **there is NO second, independent LKAS injection at the final stage.** **CORRECTS the starred
  `accord-aggregator-reaches-motor-via-gp6acc-bridge.md` ("CAN/arbitration term") and
  `reference-accord-shaper-fun42af8.md` ("feed-forward addend").**
- 🛑 **`gp-0x6b4a` is a SECOND, direct, unconditional, UNWEIGHTED LKAS-descended term into
  `gp-0x6ad6`** — term 0 of `FUN_00037fe6`, negated, **no cal weight anywhere on its path**, gate
  window **±25600 = the cell's own final clamp** ⇒ it can drive the reference to its full rail alone
  (term 7 is capped at 8192 = 32 %). The golden model's `[VERIFIED]` block at
  `eps_lkas_chain_model.py:2318-2344` documented only the **sibling** `gp-0x6b4c`. ⊕ **Sign: term 0 is
  structurally REINFORCING** — term 0's negation and `error = gp-0x4f60 − bias` cancel exactly.
  🛑 **But its input lane is INERT** (`0xC616C` = 0, above).
- 🛑🛑 **`0xC616C` IS A NEVER-RAISE CELL.** A future session will find it at 0, virgin across every
  build, and read it as a free never-tried lever. **It is `sign(driver torque) × constant`. Raising it
  turns it into a Coulomb relay on driver-torque SIGN, injected straight into the driver-feel
  reference `gp-0x6ad6`.** That is the V80 class, and arguably worse than the standing `0xC4080`
  hazard because driver-torque sign reverses on every micro-correction at the wheel.
- **`gp-0x6b26` has a Path 1 nobody had documented** — direct, **weight exactly 1.000**, zero extra
  phase, into `FUN_0003aa2c`'s aggregator, structurally identical to `gp-0x6bd0`'s. **The lane is not
  observer-only.** Census 1W/4R, closed by Ghidra ∪ Python with every disagreement adjudicated.
- **`0xC407E` = 511 decouples the dose from DTC-0x1d, at ANY multiplier** — `gp-0x6b26` saturates at
  ±511 before the monitor (trip at >512) ever reads it. Stronger than "the fault requires raising
  `0xC407E`". ⚠ **It does not clear the V74/V75 row on the faults themselves.**
- **`0xC646E` (INERTIA) is NOT a second candidate** — subtracted from the model inside the same
  observer with the same polarity as FRICTION/K1 ⇒ raising it makes the wheel **LIGHTER**. Mechanistic,
  not merely untested. **Do not propose it.**
- **`gp-0x4f60` is UNFILTERED and its producer is traced** (`FUN_0007f3f8`: dual-channel plausibility
  SM, cal-gated scale+offset+clamp, **no EMA/IIR/z⁻¹ in the store path**) ⇒ a 6–9 Hz reaction torque
  reaches it with **no firmware-side attenuation.** This closes a region this file listed as UNSWEPT.
  🛑 **IDENTITY CONFLICT FLAGGED, NOT RESOLVED:** `reference_accord_gp6af8_fight_trigger.md` calls the
  same cell *"signed motor/column angular velocity"* off the identical writer chain; every later and
  DBC-grounded source calls it **torque**. Working conclusion: **torque (BELIEF).**
- **All six observer lane weights enter at IDENTICAL unity** (`0xC63A0`..`0xC63AA` = 1024). The
  asymmetry is **gate-window width** (LKAS-mirror ±10240 vs friction ±1024), not weight. ⊕ The
  residual's final clamp is confirmed at the exact cal address: **`cal[0xC6200]` = ±8192.**
- **The dwell relay's polarity is SETTLED: `window_open = |gp-0x6b64| < 1024`** — opens on a **SMALL**
  signal, confirming the **detent** reading. Four independent sources converged. 🛑 **A hand-attempted
  raw-byte CMP decode gave the OPPOSITE answer and was rightly not trusted.**
  ⚠ At 7.79 Hz each zero-crossing gives only ~8 ms of near-zero signal against a 20 ms arm requirement
  ⇒ **the detent likely cannot arm during SUSTAINED ratcheting** — an *initiator* of stick-slip rather
  than a sustainer, so **a low measured duty is not automatically a null.**
  🛑 **RE-OPENED:** the LERP feeding `gp-0x6b64` (`X=[-397,-192,140,294,384]`,
  `Y=[0,2560,2560,717,0]`) is **zero outside `[-397,384]`**, so `|gp-0x6b64| < 1024` fires for **two
  physically different reasons** — a genuine low rate, **or the outer gate simply being shut.** The
  snap-state bit alone cannot separate them; V92 pairs it with a `gp-0x6bda`-in-window bit.

### I. STILL OPEN
1. 🛑🛑 **Is the EPS LOOP anti-damped, or the PLANT?** (§C) — **2 windows / 21.4 s** in the whole
   corpus. **Gates whether any firmware lever can work.**
2. **Where does the 2–26 Hz anti-damping come from, if not the PID?** The **boost lane `gp-0x6bbe`** is
   the top remaining aggregator candidate; V92 instruments it.
3. **The return-centre lane's own net sign** — traced structurally, never measured; V92's b6/b5.
4. **The detent** — genuine or an artefact of the shut outer gate; V92's b4 + `gp-0x6bda` 2×2.
5. **Grind #2 at the speed he names** — 6 windows on route 77 (§F).
6. **Why is the narrow 7.8 Hz LINE attenuated toward the motor while the 6–9 Hz BAND is not?**
7. **Is 2.64 ct/ct at 15–22 Hz a plant gain?** It survives a one-sided causality screen. That is not
   the same as being causal.

---

