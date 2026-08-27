# HANDOFF 2026-08-05 — THE CAR IS `TVCA4`, AND THERE ARE TWO DEAD ZONES

**Session type:** operator-directed. He supplied the **V73 flight (route `5a`)** and reported: grind #2
**fully resolved** (equivalent to V72), macro ratchet **still fixed**, **grind #1 and micro ratcheting both
still present** — *"they feel like the same vibration frequency in the steering wheel; the main difference
is that Grind Number One is audible, whereas the micro ratcheting is not."* Grind #1 **at 5 mph with the
wheel near zero**; micro ratcheting **at any speed**. He asked for a V74 that keeps the macro-ratchet and
grind-#2 fixes while attacking the other two, and — mid-session, unprompted — supplied the key reframing:

> **"Grind #2 was never an independent issue. It only ever came to be through some proposed fixes for
> grind #1 in previous firmware versions."**

**Fleet:** 9 agents — 5 firmware (GhidraMCP), 3 data, 1 builder. **V74 is BUILT, VERIFIED and UNFLASHED.**

---

## ★★★★★ THE HEADLINE — THE CAR IS CONFIG ROW 11 `TVCA4`, MODES 24/26. EVERY MODE-INDEXED LEVER THIS KIT EVER FLEW WAS INERT.

V73's probe read `*(byte)(gp+0x63fd)` over **104,061 frames**. It reported **8 (manual) / 10 (engaged)**
through a **4-bit** field — and the field drops bit 4.

**[EVIDENCE, orchestrator-verified from `stock_fw_dump/code.bin`, table `0xCD000` stride `0x24`, mode
fields at +0x12..+0x15]** An observed *v* means true ∈ {*v*, *v*+16}. Observed **8** ⇒ {8, 24}, and
**raw 8 appears in NO row of the table.** ⇒ manual = **24**, forced. Only row 11 (`TVCA4`) contains 24,
and all four columns come from one row ⇒ engaged = **26**, forced.

★ **It is the MANUAL arm that closes the proof.** Observed 10 alone never would have — rows 2/3/6/7 all
carry raw 10, which is exactly why the `TVAA1` assumption survived a dozen builds.
⚠ **The part number is `39990-TVA-A160` but the ECU is coded to a `TVC` chassis row.** `builds/v50_v79/build_v73_tva.py`
explicitly asserted that every mode reachable from a `TVA*` row is < 16. **That assumption is void.**

**⇒ Inert by table selection: V44, V47, V72's Levers B/C, BOTH of V73's levers, and the entire r24 dose
of V69/V70/V72/V73.** Full rule and blast radius: `docs/BUILD-LINEAGE.md` **RULE 7**.

### ★★ The mode is not static — it TOGGLES with LKAS engagement
**[EVIDENCE]** 18 transitions, **every one an engagement edge**. Latency **1.0209 s** on rise (sd 4.9 ms,
n=9) and **2.0798 s** on fall (sd 0.8 ms, n=9); lag-matched agreement **99.09%**; **zero exceptions**
(4 residual frames of 104,061 = 0.0038%, all single-frame edge quantisation). Writer is `FUN_00042746`,
selecting one of four row columns via `gp-0x67f6`, driven by `gp-0x6806` (≈`latActive`) and `gp-0x69b0`
once the engage ramp settles at an endpoint — which is where the deterministic lag comes from.

⚠ **But it is a RELABELING, not a RETUNING.** All 21 mode-indexed records were diffed 24-vs-26: **19 are
byte-identical**, and the two that differ move 19% and 1.6% on arrays not tied to the symptom.
⇒ **The mode switch does NOT explain engagement-conditionality.** Clean negative result.

---

## ★★★★★ THE SECOND HEADLINE — TWO DEAD ZONES, AND THE SYMPTOM LIVES UNDER BOTH

`out = (((seed·B)>>10 ·C)>>10 ·D)>>10 ·E)>>10`, sign from `gp-0x6abe`. **Seed `gp-0x698a` is structurally
pinned at 1024** (11-channel MIN-reduce; 9 channels hardcoded to 1024, one calibrated to a 1024 floor,
one with no runtime writer and a 1024 boot image; DTC guards prove 1024 is the designed ceiling).
**FactorB and FactorD are flat 1024 on every mode.** ⇒ `dose = (C × E) >> 10`.

| factor | indexed by | dead below | symptom sits at |
|---|---|---|---|
| **FactorC** `0xC9E9C[mode*4]` | vehicle **speed** | `X[0]` = 2240 = **35 km/h** | creep, ~8 km/h |
| **FactorE** `0xC9F84[mode*4]` | motor **rate** | `X[0]` = **60 counts** | **99 in-burst** |

**Both have `Y[0] = 0` in every one of the 34 modes.** ⇒ **This car has had exactly ZERO base-assist
damping at creep for its entire history, including stock.** Not "reduced" — architecturally zero.

### ⊕ AND THIS RETIRES V72's `bit4` NULL WITH NO EXOTIC EXPLANATION [EVIDENCE]
On engaged highway (n = 21,185), **98.72% of frames sit below `FactorE`'s `X[0] = 60`** ⇒ output **zero**.
Stock dose mean **0.10**, p99 = 1, and **0.005%** of frames reach ≥ 64. **The damper runs perfectly and
produces essentially nothing.** Nine agents chased this last session. It was the rate dead zone.

### The measured rate — and the near-miss that nearly cancelled V74
**[EVIDENCE, `gp-0x6ac0` from telemetry; conversion validated at 1.4% against route 59's independent
highway peak]** engaged creep: **18-22 Hz burst p50 = 98.9** [94.2, 113.0] · **6-9 Hz burst p50 = 127.1**
(⚠ 3 episodes, unpowered) · **out of burst p50 = 9.4**.
🛑 A firmware agent priced the lever at **9.4** — the *out-of-burst* row — and concluded correctly, given
that input, that **no** edit could ever reach a therapeutic dose and the approach should be abandoned.
**The in-burst rate is 10× higher.** Adjacent rows in the same table; opposite build decisions.

---

## 1. THE FLIGHT (route `5a`) — what V73 actually tested

| lever | in force? | result |
|---|---|---|
| **Lever E** (damping, modes 0-5/12/14) | ❌ **0 / 104,061 frames** | zero exposure — not an under-dose |
| **Lever D LERP** (friction ×1.5, `0xD2A44` = mode **10**) | ❌ **inert** | null by construction |
| **`0xC407E` 511→850** (not mode-indexed) | ✅ **live** | see below |
| probe | ✅ 100% liveness, `bits 2:0` preserved on all frames | the mode |

**The one live half is informative.** The clamp raise only changes output for |gate| ∈ (3195, 5315] and
adds **at most 339 counts** to a lane whose gain is stock; it was plausibly in force in **~80% of burst
frames** and produced **no measurable band change** (V73/V72 grind #1 **0.874 [0.621, 1.144]**, own null
[0.674, 1.465]; the 24-28 control moves identically at 0.932 ⇒ broadband, not band-specific).
⇒ A **weak but real, correctly bounded** falsification of the friction clamp as a grind-#1 lever.

---

## 2. THE SYMPTOM, RE-CHARACTERISED — one lightly-damped mode, two names

**The operator's "same frequency" report is right, and it reconciles with the kit's two-line measurement.**

- **NOT one line:** the two do not track (Theil-Sen **+0.051** [−0.140, +0.263], r = +0.007), and there is
  **no harmonic series** (fundamental prom 84.18; 2× **1.54**, 4× 3.55, 5× 0.80). The apparent "3×" at
  21.6 Hz is the independent ~21 Hz mode — a near-coincidence with 3 × 7.28, already excluded by tracking.
- **But coupled at exactly the ratchet rate:** MSC(5-12 Hz, envelope of the 12-28 Hz carrier) peaks at
  **7.81 Hz** — creep **0.285 vs 0.053** null, paired diff **+0.225 [+0.139, +0.351]**, carrier-specific.
- **Why he feels one frequency:** the hand feels **rim motion**, and 6-9 Hz dominates the *angle* envelope
  at every speed (0.280 vs 0.200 deg at creep). ⇒ **7.8 Hz is what he feels in both cases; what changes is
  whether the co-occurring 21 Hz ring is loud enough to hear.**

### It is a lightly-damped RESONANCE, not stick-slip and not an impulse train [EVIDENCE]
Bursts are **ring-downs**: median **600 ms = 4.4 cycles**, duty **0.228**, onsets **0.258/s** ⇒ **Q ≈ 14**.
**No trigger in any recorded channel** — rate zero-crossings specifically **refuted** (0.051 observed vs
0.087 null; events *avoid* them), so the Coulomb sign flip is not the clock. And **f0 FALLS 9.0 → 7.7 Hz
as load rises** on three independent proxies with non-overlapping CIs — **a stick-slip rate RISES with
drive velocity.** Reads as a resonance whose effective stiffness shifts with hand-arm impedance.
🛑 Supersedes the recorded **Q ≈ 40**, which was a window artefact.

⇒ **The fix is damping at 6-9 Hz. No trigger, rail or friction-onset lever can reach something with no
trigger.**

---

## 3. WHAT THE OPERATOR WAS RIGHT ABOUT, AND WHERE THE DATA DIVERGES

| his claim | verdict |
|---|---|
| grind #2 is **iatrogenic** | ✅ **CONFIRMED** — V62's `sar 0xa→0x9` (mode-proof code) governs it; V72/V73 do not carry it. **The fix is an ABSENCE.** |
| grind #1 at **5 mph** | ✅ creep-maximal, **8.1×** over highway; peaks 1.5-2.0 m/s (exact bin not resolvable) |
| micro ratchet at **any speed** | ✅ band-relative to the 24-28 control it persists everywhere (ratio 2.1-8.9) ⚠ *absolute* level is speed-dependent |
| both on the **torque sensor** | ✅ both lines on the torsion bar; openpilot's command carries neither as a peak |
| **"near zero angle"** | ⚠ **NOT established.** Does not survive rate-matching in the only powered stratum (0.898 [0.589, 1.359]); the creep-restricted test is unpowered (2.6 s in the key cell). Likeliest reading: *"not in a turn"* |
| problem dates from **V9** | ⚠ **V9 wrote ZERO functional bytes** — a pure transport re-cipher of stock. The gain scaling is V14→V22→**V38** |

⚠ **One finding that cuts against "the loop closes inside the EPS":** openpilot's command *does* carry an
18-22 Hz line — coherence with the bar **0.412 in-burst vs 0.074** control, **5.3×** enrichment. ⇒ it is
**partly inside the loop**. Residual artefact explanation (ZOH from ~88 Hz onto the 100 Hz lattice) is not
excluded. 🛑 **No openpilot-side change is proposed** — standing instruction.

---

## 4. FIVE HYPOTHESES STRUCK, WITH THE ARITHMETIC

| hypothesis | why it is dead |
|---|---|
| **Saturation / clamp headroom** | Falsified **on data** (engaged creep: **27.7%** of rail, **0/127** in-burst frames at rail; where it *does* rail, duty **FALLS** 35.5%→12.5% — the rail is protective) **and on structure** (the four summed mixer channels are **base assist**, not LKAS; LKAS reaches the motor via a second accumulator `gp-0x62b0[ch]` → `gp-0x3d88` → `gp-0x6b4c`) |
| **A 7.8 Hz firmware divider** | The RTOS rate divider is a **mod-100** counter ⇒ only {1000, 500, 200, 100, 10} Hz reachable. Period 128 cannot exist |
| **Stick-slip** | No harmonic series, no trigger, **f0 falls with load** |
| **State 8 / any `gp-0x67fa` account of the damper null** | 🛑 **`0x830 ⊂ 0xc30` is arithmetic** ({4,5,11} ⊂ {4,5,10,11}) ⇒ every state that runs the aggregator also runs the damper |
| **`gp-0x67fa` aliasing** (orchestrator's own) | All 33 writers store literals; value set {1,3,4,5,6,7,8,9,10,11}, nothing ≥ 12 ⇒ `& 0xf` is a no-op, and V70's rung read the full unmasked byte. **State 10 really is excluded** |

---

## 5. ⇒ V74 — BUILT, VERIFIED, UNFLASHED

**Design principle, earned twice over: write the ENGAGED COLUMN OF EVERY ROW.** The engaged set
{2,3,5,11,14,15,17,23,26,27,29,32,33} and the disengaged set are **disjoint across all 16 rows**, so V74
delivers whatever row is live **while leaving manual and parking steering byte-stock.**

- **LEVER E′ (the core)** — `FactorC Y[0] := Y[2]` · **`FactorE X[0]: 60 → 12`** · `FactorE Y[1] := Y[2]`.
  ★ **It opens the RATE dead zone rather than raising a gain** — the damper becomes genuinely
  rate-proportional in the symptom's range. 🛑 **This is the OPPOSITE of V72's error, not a larger
  version of it:** V72 raised `FactorE`'s floor, producing a *constant* in the symptom's range — a
  near-bang-bang relay. Here **`Y[0] = 0` is preserved**, so magnitude vanishes with rate and the bare
  `sign()` relay multiplies a vanishing quantity ⇒ **no discontinuity, no chatter mechanism.**
  **Dose at the measured rate 99: ~50 counts** (requirement ~43 [30,60]) vs **0** stock, **6** for
  `FactorC` alone, **14** for `FactorC` at maximum — *neither factor alone can reach it.*
- **LEVER D′** — friction lane ×1.5 on the same 13 modes; `0xC407E` = 850 (⚠ **not** mode-indexed, so it
  applies in manual too — disclosed, bounded at +339 counts). 🛑 **Hard cap 1000, never 1024**: the
  aggregator's ±0x400 window is a **zero-reject**, so a lane on the cliff contributes *nothing*.
- **UNTOUCHED** — the entire r24/r26 rate lane, including V72's r26 cut (`0xC6A68`/`0xC6A7C` flat 512),
  the `sar` sites, the gate and both scalar arms. That is how the grind-#2 and macro-ratchet fixes are
  retained.
- **PROBE** — `bits 6:3 = gp-0x67fa` (4 bits, provably lossless; 0 impossible ⇒ liveness structural) ·
  **`bit7 = (gp-0x6bd0 != 0)`** — the damper's own output, **the positive control the last five probes
  lacked.**

**GATE 2 [EVIDENCE]:** both lanes dissipative at both frequencies under a common convention
(D′ +0.23 / +0.57 / +0.92 at 7.79 / 20.9 / 45 Hz; E′ +0.92 and +0.47-0.54) — and since both phasors have
positive real part, **their sum does too, by construction**, not by sampling. DTC-0x18 cost: **zero**
(cal-only, no new instructions).

### 📋 PRE-REGISTERED, before the drive
- **Success:** 6-9 Hz burst **duty AND duration both fall**, **f0 unchanged** (|Δf0| ≤ 0.3 Hz).
- **FALSIFIER A:** duty ratio > 1.2 *with* prominence ratio > 1.3 ⇒ self-excitation.
- **FALSIFIER B (clean):** **5×f0 prominence > 3.0 ⇒ the relay is generating a new cycle. ABORT the lever.**
  (baseline 5×f0 ≈ 38.5 Hz, prom 0.80; 3× is unusable — confounded with the 21 Hz ring.)
- **FALSIFIER C:** |Δf0| > 0.5 Hz ⇒ a relay picks its frequency from loop delay; damping does not.
- **Honest expectation:** *"meaningfully reduces amplitude and should shorten ring-down, plausibly enough
  to break a marginal limit cycle, but not certain to extinguish a robust one."*

---

## 6. FLIGHT INSTRUCTION — congestion beats an empty lot

🛑 **The 8-10 min continuous-lot proposal FAILS**: continuous engagement yields ~1 episode (MDE 2.91×),
and openpilot needs lane markings. **Stop-and-go traffic is strictly better** — LKAS drops at each halt
and re-engages, which is why route 5a yielded 18 episodes in 120 s.

| # | manoeuvre | cost | buys |
|---|---|---|---|
| **1 ESSENTIAL** | congested lane-marked arterial, engaged, rush hour — ordinary driving | 15 min | grind #1 to **2.0×**, ~40 events for the rate test |
| **2 ESSENTIAL** | steady cruise **≥ 20 m/s**, engaged, uninterrupted | 8-10 min | the first **tyre-order-clean** high-speed 6-9 Hz test |
| 3 opportunistic | mid-motion disengagements at 2-3 m/s, keep rolling ≥ 3 s, ×24 | folded into #1 | the only design isolating damping from command (**1.56×**) |

⚠ Tyre order 1 is in-band at **12.5-18.7 m/s**, order 2 at 6.2-9.4, order 3 at 4.2-6.2. **Clean windows:
9.4-12.5 m/s and ≥ 20 m/s.**
⚠ **Score BOTH bands** and read the probe first — if `bits 6:3` is constant for a whole drive, the cave
did not fire and nothing else is interpretable.

---

## 7. OPEN
1. ⚠ **The macro ratchet is the LEADING HYPOTHESIS, not established** — r26-driven and therefore partly
   iatrogenic (V42 killed r26 and fixed it; V71C removed the cut and carries the corpus record; V72 cut it
   and fixed it). **n = 2 improvements, operator reports not measurements, every instrument failed its own
   positive control, and the micro ratchet — the one measured thing — has never moved.**
2. ⚠ **V72/V73's r26 cut is PARTIAL** — `rec2` `0xC6A90` and `rec3` `0xC6AA4` are byte-stock.
3. ⚠ **The `0x830` gate** admits {4,5,11}; states 4 and 10 are measured out. V74's probe reads the byte.
4. ⚠ **The 6-9 Hz burst rate (127.1) rests on 3 episodes** — unpowered.
5. ⚠ **Coupling direction** (7.8 → 21, or a shared driver) is unresolved.
6. ⚠ **Column vs motor:** the rate conversion is rigid-body, exact at DC and progressively wrong through a
   torsional resonance. If the motor end swings more, the **true dose is higher** than 50.

---

## 8. 🛑🛑 A DECODER TRAP FOUND AT CLOSE-OUT — AND IT WOULD HAVE FAKED THE NEXT HEADLINE

Run against route `5a` — **V73's flight, on which V74 has never been flashed** — `probe/decode_v74_probe.py`
reported, in full confidence and with no error:

> `✅ consistent with V74: states seen [8, 10], bit7 duty 100.000%`
> `✅ bit7 fires on 100.000% of frames ⇒ **LEVER E' IS DELIVERING** and the damper is in force for the
> first time in this kit.`

**That is the exact sentence this kit would have celebrated after the V74 drive.** ★ **Why nothing caught
it: every `V7x` cave writes the SAME cell in the SAME bit positions, and the alphabets OVERLAP.** V73's
`bit7` is a hard-wired liveness `1` (reads as *"the damper is never zero"*), and V73's `bits 6:3` are
`mode & 0xF` — which on this car is **24/26 → 8/10, and BOTH are legal `gp-0x67fa` states.** There is no
internal inconsistency to trip on.

🛑 **This is the session's own headline failure in a new costume: the right number read off the wrong
object.** Same as V72's damping written to an unread table, V69/V70's ladder measuring three copies of
stock, and the `9.4`-vs-`98.9` rate row.

**Fixed** — `identify()` now separates **DECISIVE** from **corroborating** and refuses without a verdict:
- **[DECISIVE]** `bit7` duty **exactly 100.000%** is *structurally* impossible for V74, because
  `bit7 = (gp-0x6bd0 != 0)` and **FactorE's `Y[0]` is preserved at 0 by design** ⇒ at zero motor rate the
  damper output is 0 ⇒ the bit must read 0 on some frames of any real drive. Saturation ⇒ not V74's bit.
- **[DECISIVE]** field ⊆ {8,10} **AND** tracking `latActive` > 85% — V73's mode-toggle signature
  (measured **94.8%** on the test log). Works even where the first test is unpowered.
- **[corroborating only]** field ⊆ {8,10} alone — a real V74 drive could legitimately sit in two states.
✅ **Negative control run in BOTH directions:** refuses real V73 logs and a synthetic V73 signature;
accepts five synthetic V74 cases — **including `bit7` duty 0%**, because *"the cave ran and the damper is
still dead"* is a real result and a guard that swallowed it would be worse than the bug.
✅ **Exits non-zero (3) on refusal** — the banner is for a human; the exit code is for anything that
pipes, wraps or CI-checks it, which is exactly how the wrong log gets decoded silently.
⊕ The old `identify()` "illegal bits" check was **vacuous** — it masked with `PROBE_MASK` then tested for
bits outside it, so it could never fire. Removed.

🛑 **[OPEN] EVERY `decode_v7*_probe.py` IN THIS KIT HAS THE SAME EXPOSURE.** They all read `0x14A` byte4
and none of the others carries a build-identity guard. V70/V71/V72 at least had structural invariants in
their value sets; **V73's does not.** ⇒ **Before trusting any historical probe re-read, check which build
the log actually came from.**
