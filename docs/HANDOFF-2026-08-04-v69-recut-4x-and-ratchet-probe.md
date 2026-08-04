# HANDOFF 2026-08-04 — V69 RE-CUT IN PLACE: ×4 DOSE, AND THE TELEMETRY RE-AIMED AT THE RATCHET

**Predecessor: `docs/HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md`** (the ×2 cut, same day).
Read that first — everything about *shape* is unchanged and is argued there. This handoff covers only
what moved.

**Two operator instructions, both explicit, both applied in place on V69 rather than as a new build:**

1. *"we have some edits which amount to a doubling of some damping values, let's scale them to 4x
   instead, do edits in place on V69."*
2. *"change the telemetry so the provided bits also provide information on as many top candidates as
   possible for the ratcheting issue, instead of the grind(s)."*

**Artifacts.** Image SHA `48bb4192…`, RWD SHA `e62fcbba…`, file
`39990-TVA,A160-V69-LKAS-4x-mss0-decouple0xC646C-ratelane-SPEEDSHAPED-gateREVERTED-gainB-rec0rec1-x4-ratchetprobe-can330byte4-0x13000-0x100000.rwd`.
**7 edit sites / 70 changed bytes / 3 CRC blocks / cave extent UNCHANGED (66 of the proven 68 B).**
✅ 50/50 CRC, x31 PASS, RWD decodes back to the image with **every** gate re-run on the readback;
`verify_v69_image.py` all anchors PASS; `diff_build_vs_stock.py v69` **0 unattributed**.

---

## 1. THE ×4 DOSE

`0xD2A7E`/`0xD2A80` 3072 → **12288**; `0xD2ABA`/`0xD2ABC` 2561 → **10244**. Every halfword still an
exact integer multiple of the one it replaces, and the builder now reads a single `SCALE` constant so
no derived assert can drift out of step with it.

**The shape is untouched.** Delivered multiplier, low rate axis:

| km/h | 0 | 5 | 7.2 | 10 | 15 | 20 | 30 | 40 | 50 | 93 |
|---|---|---|---|---|---|---|---|---|---|---|
| ×2 (as specced) | 2.000 | 2.000 | 2.000 | 2.000 | 1.886 | 1.769 | 1.526 | 1.270 | 1.000 | 1.000 |
| **×4 (as built)** | **4.000** | 3.999 | 4.000 | 4.000 | 3.658 | 3.307 | 2.578 | 1.808 | **1.000** | **1.000** |

★ The highway **1.000× is still STRUCTURAL** — 12,221-point sweep over speed ≥ 50 km/h × rate, every
point byte-identical to stock, because ≥ 50 km/h reads only rec2/rec3 and those are untouched.
★ Still **scale-invariant** (4.000× on both candidate axis scales) and still **no hump anywhere**.

### 1.1 🛑 What ×4 costs — stated first, not buried

| | ×2 | **×4** |
|---|---|---|
| max multiplier | 2.000× | **4.000×** |
| peak gain | 6144 | **12288** |
| r24 lane rails at \|dtorque\| | 1366 | **683** |
| margin vs repo max 839 | 1.63× | **0.81×** ⇒ *it can rail* |
| margin vs V68-route max 511 | 2.67× | **1.34×** |
| fold step @ rateKey ≥ 13001, 0 km/h | 2.00 → 4.00× | 2.00 → **8.00×** |

1. 🛑 **THE FLOWN BRACKET IS BROKEN.** At 2.000×, GATE 2's magnitude leg was an *interpolation*
   between two measured points: stock (1.00×, shipped) and V62/V65 (2.00×, flown flight-clean).
   **4.000× is an extrapolation to twice the largest dose this kit has ever driven.** What still
   holds, and it is not nothing: phase is untouched (no filter, no pole, no delay, no `sar` moved),
   the lane is linear, V65 measured the aggregator never railing over 120,049 frames, and grind #1's
   dose–response was **monotone** through 2.00×.
2. 🛑 **SATURATION CROSSES THE RECORD.** At ×2 the lane could not rail in recorded driving; at ×4 it
   can. During the largest low-speed transients the damping lane goes from linear to a hard rail — a
   describing-function regime the ×2 design deliberately stayed out of. ⚠ Every `|dtorque|` figure in
   this kit is a **LOWER BOUND** (CAN's 50 Hz Nyquist hides content the finite difference is still
   *rising* through), so the true margin is **worse** than 0.81×, not better.
3. ⚠ **Manual creep is 4.000×** on the pessimistic axis scale. Manual highway stays byte-identical
   to stock.

The builder **prints the broken-bracket warning and the saturation line on every run** rather than
silently passing a gate that no longer applies. The old `assert mx <= 2.001` is now
`assert mx <= SCALE + 0.001` with the bracket statement demoted to an explicit printed 🛑.

★ **And cost (2) is instrumented, not merely disclosed** — probe bit6 measures it on-car (§2).

**One new assert worth keeping:** the Y row must stay a **positive signed halfword**. If the
accessor's load is `ld.h`, a value ≥ 0x8000 comes back negative and inverts the lane. At ×4 the peak
is 12288 (2.7× of headroom); the assert holds the *property* so it is safe under either load width,
and it is the guard that stops a future ×8 or ×12 from silently flipping the sign.

---

## 2. THE PROBE, RE-AIMED AT THE RATCHET

### 2.1 Why re-aiming was the right trade

**The grind detector is exhausted.** `gp-0x67df` has **never been observed non-zero in this kit** —
0/53,991 frames on V68 (straight through the captured 28 Hz burst) and 0/186,321 on V67. With no
positive control, that null cannot separate *"no oscillation"* from *"detector disabled / input dead
/ `FUN_000428d4` not reached"*. Another route on the same rungs buys another uninterpretable zero.

★ **And the ratchet is the one symptom this channel can RESOLVE.** It runs at ~7.4–7.6 Hz, so a
100.000 Hz probe gets **~13.5 samples per cycle** and each bit's **own time series** carries the
line. Grind #1 (21 Hz) and grind #2 (43 Hz) sit at 0.42× and 0.86× of Nyquist — every prior probe
could only ever report *duty* for them. This is the first probe in the kit whose bits can be
**spectrally analysed for the symptom they are aimed at.**

### 2.2 Why these three cells

The ratchet's recorded signature — **symmetric waveform, amplitude-saturated, Q ≈ 36, creep,
engaged, hands-off, NOT the V42 state-4 governor** (`ST == 4` fires 0/37,922) — is the
describing-function signature of a **hard nonlinearity inside the loop**.

V65 already killed the obvious one: its 4-level ladder found the aggregator SUM `gp-0x6b94` **never
rails** over 120,049 frames, only 54 frames past ±4096. ★ **What that null never covered is each
lane's OWN nonlinearity upstream of the sum.** Re-read from the `FUN_0003aa2c` decompile this
session, the complete list (every lane a **signed** halfword, `ld.h`/`st.h`):

- **ZERO-type range gates** — out-of-window contributes **0, NOT clipped**, so a crossing is a
  *step*: `gp-0x6b62` ±0x2000 · `gp-0x6b4c` ±0x2800 · `gp-0x6ade` ±0x400 (dead) · `gp-0x6ad4` ±0x2800
  · `gp-0x6b26` ±0x400 · `gp-0x6bbe` ±0x800 · `gp-0x6bd0` ±0x800 · `gp-0x6b86` ±0x3000.
- **Saturating clips**: r24 and r26, each ±0x2000, summed ungated.

**None has ever been measured.**

| bit | cell | test | its lane's hard nonlinearity | why |
|---|---|---|---|---|
| 7 | — | 1 | — | LIVENESS; field == 0 ⇒ VOID |
| **6** | `gp-0x6ada` | ≥ +4096 | ±0x2000 **saturating clip** | **r24's lane OUTPUT** — the damping/torque-rate lane the record points at *and* the lane V69 scales. 🛑 **0 readers / 1 writer image-wide.** +4096 = half its rail ⇒ duty is a **rail-proximity meter** |
| **5** | `gp-0x6b62` | ≥ +4096 | ±0x2000 **ZERO gate** | **the operator's own hypothesis, never probed in 69 builds.** Return-to-centre: `FUN_00036388`, a slow ±1/tick accumulator **with hysteresis** |
| **4** | `gp-0x6ad4` | ≥ +4096 | ±0x2800 **ZERO gate** | the **unfiltered** residual lane (`FUN_0003a382`: raw derivative on the torque sensor, straight into the aggregator), gain LERP-indexed by `gp-0x671a` ⇒ **closes a loop from Honda's own detector back into assist**. Live hands-off, which the boost lane is not |
| 3 | — | **0** | — | V69 BUILD CLASS |

**bit6 was freed from the LKAS gate** to buy the third rung. Justified, not assumed: `gp-0x6806`
agreed with `carControl.latActive` in **150,302/150,327 = 99.983%** of frames, `0x18F` b4 bit3 and
`0xE4` byte2 bit7 agree 99.94–100%, and **V69 reverts the gate** so that cell no longer steers
anything on this build — bit6 was a pure covariate and three external channels already carry it.

### 2.3 ★ A new structural finding, now in the golden model

**Both inline lanes are mirrored to RAM, post-clamp, and NOTHING reads them:**
`st.h r26 → gp-0x6adc` @`0x3AD4E` and `st.h r24 → gp-0x6ada` @`0x3AD5A`, each **0 readers / 1
writer** image-wide (re-derived from raw bytes by `V64.gp_access_census`, two decoders).

⇒ They are **free, blast-radius-zero telemetry taps on exactly the quantity every rate-lane build
scales**, and `gp-0x6ada` carries the strongest GATE-1 statement available anywhere in this chain:
*nothing consumes it*, so the probe cannot perturb anything even in principle. ⚠ `gp-0x6adc` is
expected to read ~0 (r26 is structurally inert, `0xC6564` = 40 zero bytes) — probing it would be a
rung spent on a known constant, the exact error V68's original bit4 made.

### 2.4 Encoding, budget, and the trap

**Per rung, 14 B:** `ld.h -disp[gp],r6` · `sar 0xc,r6` · `cmp 0x1,r6` · `blt +6` ·
`movea BIT,r7,r7`. `sar` is **arithmetic** and `blt` is **signed**, so a negative lane value fails
the test — asserted by an **exhaustive wire model over all 65,536 halfword patterns**, plus the
explicit unsigned counter-case (`ld.hu`/`shr` would map every negative value to a large positive one
and fire the bit on the **wrong half-cycle** of a symmetric limit cycle, which would still look
plausible on the wire).

**Budget:** proven cave 68 B; prologue 4 + epilogue 20 leaves **44 B**; 3 × 14 = 42 ≤ 44, a fourth
needs 56. **Three rungs is arithmetic, not preference.** The extent is **not** grown — caves are this
kit's only bricking class (V24, V27, V48B all bricked the ECU).

🛑🛑 **THE ONE-BIT TRAP, AND IT IS NOT HYPOTHETICAL HERE.** `ld.h` is opcode **0x39**; `st.h` is
**0x3B**. `gp-0x6ada`'s *only* real instance (`0x3AD5A`) **is** the `st.h` form and carries **the
same displacement halfword** we emit. One bit turns each read into a **write into a 1 kHz aggregator
lane**. Asserted by value in the builder **and independently** in `verify_v69_image.py`.

**Encoder provenance** — `ld.h -0x6ad4[gp],r6` is **BYTE-IDENTICAL** to the aggregator's own read at
`0x3ACA8`; `gp-0x6b62` has **eight** real `ld.h -0x6b62[gp],rN` differing from ours **only in the
reg2 field**; `gp-0x6ada` has no real `ld.h`, but its hw2 is byte-identical to the real `st.h` and
every hw1 field is pinned by the two byte-identical `ld.h …,r6` donors. `sar 0xc,r6` (`ac32`
@`0x2C0BA`), `cmp 0x1,r6` (`6132` @`0x14D46`) and `blt +6` (`b605` @`0x1C006`) are byte-identical
real instances.

### 2.5 🛑 Three residuals, stated at full strength

1. **ONE-SIDED.** Each rung tests the positive side only (two-sided costs 8 B/rung and does not fit).
   For a symmetric limit cycle the positive half-cycles alone still put 7.4 Hz in the bit's spectrum
   — that *is* the measurement. But **a rung reading 0 bounds only that lane's POSITIVE excursions.**
   Never quote a null here as two-sided.
2. **NO POSITIVE CONTROL on bit5/bit4.** Only bit6 is expected to fire on any real drive. **If bit6
   also reads 0.000%, check bit7 and the `.rwd` name BEFORE interpreting bits 5/4** — that ordering
   is the V64 lesson applied.
3. **V69-vs-V66/V67 is NOT structural.** Those builds also emit bit3 = 0 and had bits 5:4 measured 0
   over 186,321 frames, so their payloads `{0x87, 0xC7}` are a **subset** of V69's. Discrimination
   rests on bit5/bit4 ever firing plus the filename. **V68 — the build on the car — IS excluded
   absolutely** (bit3 = 1 in 100.000% of 53,991 frames), which is the discrimination that matters.

### 2.6 Considered and NOT taken

- **`gp-0x6bbe` boost, ±0x800** — the narrowest gate on a live lane, but indexed on **driver torque**,
  and the ratchet is hands-off ⇒ it sits far from its gate exactly when the symptom occurs.
- **`gp-0x6bd0` damping, ±0x800** — the record has f5 = 0 at both operating points, so it likely
  reads 0; but that is a **static** claim and probing it would test a closed branch. **First cut if
  a rung ever frees up.**
- **`gp-0x6b4c` LKAS lane** — the post-mixer command, already visible on CAN `0xE4`. Redundant.
- **`gp-0x4f62` dtorque** (r24's input) — the "probe the input too" lesson; rung 4 if the cave grows.

---

## 3. THE DECODER, AND A GATE THAT CAUGHT SOMETHING

**`rlog-tools/decode_v69_ratchet.py`**, linked mechanically: `build_v69_tva.assert_decoder_matches()`
**fails the build** if the decoder's `CAVE_HEX` is not byte-for-byte the built cave, if it omits any
probed cell, if it lacks the threshold or the artifact basename — **or if it still describes the
retired grind-detector rungs as live.** (V66's decoder header was stale for one revision and claimed
`bit4 = gp-0x683c` when the image read `gp-0x67fe`; this is the fix for that class of error.)

★ **The gate fired on its first run** and caught a real gap: the decoder did not carry `0xC4124`.
That is not a formality — the role table is what makes all three bits *mean* anything. `FUN_0003aa2c`
has a **REDUCED aggregator mode** (`gp-0x67ac == 1`) that sums the LKAS lane and `gp-0x6b62` **only**,
skipping six sibling lanes **and both inline r24/r26 lanes**. In that mode bit6 and bit4 would be
reporting lanes that are not in the sum at all. It is unreachable on this ROM because
`0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]` never matches the qualifying literals `{2,3,4}` — and every
V69 build asserts that table byte-for-byte and refuses to emit if a slot ever reads 6 or 7. The
precondition is now recorded in the decoder where a reader will meet it.

**What the decoder reports:** build identification from the probe (VOID / illegal / bit3, with the
two-tier exclusion argument printed at its real strength); per-bit duty, toggle rate and 6–9 Hz peak,
stratified into WHOLE ROUTE / engaged / engaged+creep / **engaged+creep+hands-off (the ratchet's own
cell)** / manual; the ratchet test — a 6–9 Hz line in each bit's own series scored against a
**split-half null computed first, from the same data**, over episodes ≥ 2.56 s; and bit6's duty by
cell as the on-car price of the ×4 dose.
🛑 It prints the episode count **before** any statistic and says outright when there are none —
*"this route cannot speak to the ratchet in either direction"*. Route `2b` failed exactly that test
and the operator said so before the data did.

---

## 4. WHAT DID NOT CHANGE

Control path (`0x3AA96` `c5`, `0xC6446` = 512), all three `sar` sites stock, V57's private gain cell
`0xC6CD0` = 3564, `0xC646C` = 891, `0xC62EA` = 0, the role table, `0xC6564` = 40 zero bytes, V60's
falsified `0xD2000` cells, all 8 mode-11/12 neighbour records, and rec2/rec3 (which is *why* highway
is exactly 1.000×). The edit-order invariant (`arm == 512 ⟹ gate byte == 0xc5`) and the neighbour
trap are asserted as before, in **both** builder and verifier.

---

## 5. NEXT

1. 🛑 **Flash only on the operator's explicit instruction, naming the file and the bus.** Kill
   openpilot/pandad first (`tmux kill-server`).
2. **An ordinary 20–30 min engaged highway commute** tests the lane-change question (route `4e` gave
   18 maneuver windows in ~4 min at speed). No scripted drive.
3. ★ **ADD PARKING-LOT CREEP for the ratchet probe: engaged, hands-off, large angle.** The recorded
   episodes are 7.56 ± 0.36 Hz at both 9–15° and 133°. Without them bits 5/4 have nothing to say.
4. **Log from before the first engagement**, and decode with `decode_v69_ratchet.py` **before** any
   spectral work — that is the V64 lesson.
5. ⚠ **Read bit6 first.** It is the only rung with an expected positive control; if it is silent,
   nothing below it is interpretable.

**Pre-registered:** P3/P4/P5 stand unchanged and dose-independent. P1/P2/P6 were sized for ×2 and are
**not** re-derived for ×4 — read them as directions, not intervals. **P7/P8/P9 are new** and cover
the ×4 cut and the ratchet probe (`docs/V69-DESIGN.md` §9).
