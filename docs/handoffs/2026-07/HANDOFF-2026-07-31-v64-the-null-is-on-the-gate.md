# HANDOFF 2026-07-31 — V64 flew, the grinding is unfixed, and the probe proves the lever was never pulled

**Session shape:** operator reported the V64 drive and asked for the next step, as orchestrator.
Three subagents (a probe decoder, an rlog spectral analyst, a firmware tracer), with the orchestrator
verifying every decision-bearing claim independently in Ghidra and against image bytes. **No build was
produced and nothing was flashed.** The deliverable is a diagnosis and a recommendation.

**One-line summary:** V64's probe read a **constant `0x87` for all 14,980 frames** — the oscillation
detector never armed, so V64's two calibration edits were **never in force for a single frame**. This is a
null on the **gate**, not on the damping hypothesis. **V62 is promoted from fallback to the recommended
next flash**; it carries no detector anywhere in its path.

---

## 1. What happened on the car

**V64 flashed and driven, route `00000035--77808fe7ce`** — 3 segments, 14,980 frames / 149.8 s, **100%
creep** (vEgo max 4.58 m/s), disengaged-then-engaged as instructed, 1,958 reverse frames, log starting
43 s **before** first engagement.

Operator: *"I drove disengaged then engaged after. The vibration/grinding at low speeds is not fixed."*

### The probe answered its question

`0x14A` byte4 = **constant `0x87`, zero variance**:

| bit | meaning | frames set |
|---|---|---|
| 7 | liveness | **14,980 / 14,980** — the cave ran, every tick |
| 6 | `gp-0x671a >= 5` — **V63/V64's raised arm selected** | **0** |
| 5 | `gp-0x671a != 0` — counter incremented at all | **0** |
| 4 | `gp-0x67df != 0` — FSM left neutral | **0** |
| 3 | `gp-0x671d != 0` — r24 override | **0** |

⇒ `|gp-0x6c2c|` **never crossed `T` = 12800 once**, the reversal counter never incremented, and
**`0xC6440`/`0xC643E` were never applied.** The grinding happened while the detector sat in neutral
throughout — **through 1,158 steering-rate sign reversals**, with angle spans of 418°/416°/601° and driver
torque to 3,893 counts. This was not a gentle drive.

🛑 **Do not record V64 as evidence against raising the rate lane.** The direction V61 signed is still
untested on-car.

**Confirmed four independent ways:** raw byte histogram · `rlog-tools/probe/decode_v64_detector.py` (run by the
orchestrator) · an independent raw-CAN rederivation sharing no code · **V59's probe ruled out** as the
source (its bit5 was set essentially always; here 0/14,981, and other routes show byte4 genuinely varying
`0xBF/0x8F/0x9F/0x87`, so the channel demonstrably carries varying upper bits).

### The spectra agree independently — V64 ≡ V59

| build | n runs | peak | prominence | abs power |
|---|---|---|---|---|
| V59 route `2c` | 9 | 21.18 Hz | 227× | 5.26e8 |
| V61 route `31` | 3 | **18.25 Hz** | 486× | **4.15e9** |
| **V64 route `35`** | 2 | **21.30 Hz** | 149× | 4.31e8 |

In the best-populated bin either build has (2–3 m/s): **V59 20.98 Hz / env99 1811 vs V64 20.99 Hz / env99
1804** — three significant figures on both observables. V61's 2.3 Hz downshift is **fully undone**, and
V61's spread into manual driving is **gone** (near-stationary high-effort manual: V61 470× median /1571×
p90 vs V64 8.9×/12.4×).

That is exactly what a build whose edits never applied should look like. **The probe and the spectrum
agree, by completely different routes, that nothing changed.**

**FLIGHT-CLEAN:** `ST==4` **0**; `ST==3` 119 frames, all disengaged at v≈0 (ordinary standstill lockout);
all six watched events **0**; `0x14A`/`0x18F` at 100.03 Hz.

---

## 2. Why the gate never opened — and it is not what anyone assumed

`gp-0x6c2c` is the FSM's only input. Traced to `FUN_00041464` @`0x4184E`; all cals byte-read LE:

```python
K1 = 37     # cal 0xC643C, >>7        K2 = 22   # cal 0xC40DC, >>6
x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # validity ceiling -> fault sentinel
target = x * 1024
step   = ((target - old) * K1) >> 7 ; old += step   # EMA #1 increment -- THE DIFFERENCE
acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # x32, clamp +-16,384,000
state += ((acc - state) * K2) >> 6                  # EMA #2
gp_0x6c2c = state >> 9                              # range +-32,000; T = 40.0% of that
```

⇒ **a MOTOR-RATE DERIVATIVE — an acceleration.** Not torque, not a raw per-tick difference. Differencing
kills DC, so a sustained large steering input cannot drive it; it needs the motor rate actively reversing.

**Sizing:** a 21.3 Hz sinusoid needs `|gp-0x4f50|` ≈ **1683** counts @1 kHz / **1821** @100 Hz to trip `T`
— inside that signal's own ±13000 validity ceiling. ⇒ **the detector is NOT structurally blind to the
mode; the drive was ~1.7–2× short.** Independently reproduced in the frequency domain (`|1−H1|` = 0.43041
× `|H2|` = 0.95375 ⇒ `7.5965·U` ⇒ **U = 1685**) — four significant figures by a different method. Now
embedded in the golden model as `detector_input_6c2c()`, which reproduces the threshold exactly (1683
trips, 1682 does not).

### 🛑 Three numbers are VOID

An earlier pass sized `T` from the `0x18F` torsion-bar torque channel, which assumed `gp-0x6c2c` shares
that LSB. It does not. **Withdrawn:** the "T ≈ 2048–2560" band; the "LSB at most 3.29× finer" bound; and
the "per-tick rate ⇒ effectively dead, T must fall 30–90×" row (which priced the chain at unity gain and
missed the `×1024` and `×32` pre-scales, invisible from the bus).

⚠ **General lesson: the bus can bound a signal's amplitude but not its scale.** Sizing a firmware
threshold from a bus channel requires proving the two share an LSB — and this firmware demonstrably
rescales: the two `STEER_ANGLE_RATE` copies differ by exactly **8.000×** in raw counts (corr 1.0000 across
16 segments). That measurement stands and is worth keeping.

`analysis-2020accord/studies/gates/analyze_bus_amplitude_vs_detector_T.py` has had its docstring corrected in place to
lead with the withdrawal, so the falsified framing cannot be picked up by a future session. Its
distributions, excursion figures, 8.000× result and no-railing check still stand.

---

## 3. Two alternative explanations, both closed

**(a) Was the build aimed backwards?** `builds/v50_v79/build_v63_tva.py:63` recorded a live dispute — one trace read
`0xC643E` as the `state<5` arm, which would have raised the *smooth-steering* gain. **Closed in favour of
the build**, verified by the orchestrator in Ghidra:

```
0x3AA7C  cmp r14, r12      ; state - CEIL   (CEIL = ld.bu 0x74fa[tp] = 5)
0x3AA7E  bc  -> 0x3AA88    ; carry => state < CEIL
0x3AA80  mov 0x1, r2       ;   state >= 5  =>  r2 = 1
0x3AB68  ld.hu 0x743e[tp]  ; 0xC643E loaded IFF r2 != 0    ✓
0x3AC12  ld.hu 0x7440[tp]  ; 0xC6440 loaded IFF r2 != 0    ✓
```

⚠ The golden model's `selected_state_value` refers to **`r22`** (cals `0xC6138`=1 / `0xC6136`=0), a
**different register** from the arm selector `r2`. Both model readings were right about different
variables — the "dispute" dissolves.

**(b) Did the detector run at all?** `FUN_000428d4`'s entire body is gated on `FUN_00046ea6(5) == 0` (bit
5 of `gp-0x18d0 | gp-0x18d4`); if set, it jumps `0x428E2 → 0x42A76` and **neither cell is written** —
indistinguishable from "T never crossed" on a bus log. **Closed** by raw byte scan of **all 47 `jarl`
sites** (Ghidra's search found only 44 — the documented undercount, so the conclusion survived the *more*
complete method): **bit 5 has exactly one caller image-wide, the detector itself** @`0x428DA`. The only
dynamic indices are cal bytes `0xB9A14-16` = **0, 2, 6**. The mask is DTC-driven (`tp-0x72c4`, stride 28,
u32 at +8) and **self-clearing** — `gp-0x18d4` is rebuilt by plain assignment each active-fault sweep.
⚠ Residual: 6 of 47 sites set `r6` beyond a 5-halfword window; all sit in clusters resolving to 0 or 7.

**This one deserves emphasis: it briefly looked like it invalidated the sizing work, and the orchestrator
issued a correction to the operator before it was closed.** It resolved favourably, but that was luck
rather than design — see §6.

---

## 4. Even if the gate HAD opened, V64 delivers little

Byte-read the default arms at the hands-off-creep LERP axis (X = 0):

| lane | default arm (state<5) | osc arm stock | V64's arm | delivered vs default |
|---|---|---|---|---|
| r24 | **2305** (`0xD2AEC`) | 2048 | 4096 | ×1.78 |
| r26 | **3072** (`gain_A` rec0/rec1) | 1536 | 3072 | **×1.00 — a no-op** |

⇒ **Honda's oscillation arms are gain REDUCTIONS, not boosts.** V63/V64 largely *cancel Honda's own
de-escalation* rather than adding damping. V63's build note said "3072 is already `gain_A`'s own stock
maximum" as reassurance about arithmetic safety — true, but it also means r26's raise only reaches the
value the LERP already gives at low driver torque.

⚠ **bit3 = 0% ⇒ r24 *was* covered** — the `gp-0x671d` override was idle throughout, so r24 would have
taken `0xC6440`. And `gp-0x671d` turns out not to be "r24's override flag" at all: it is a **saturating
rising-edge counter on a torque-residual/observer check** (`FUN_00041d56`) feeding DTC `0x5e`, reset only
by `FUN_0003bcb2`'s resync, with 8 readers including the motor-off dispatcher `FUN_0003d4a2`.

---

## 5. The recommendation — flash V62

**`39990-TVA,A160-V62-LKAS-4x-mss0-decouple0xC646C-boostindexdepth-ratelane2x-can330byte4-0x13000-0x100000.rwd`**
· image SHA `80d9e1f7…` · RWD SHA `1e0806a1…`

**Re-verified from the built image this session:** exactly **6 bytes** vs V59 — `0x3AB76` `aa`→`a9` and
`0x3AC20` `aa`→`a9` (both `sar 0xa`→`sar 0x9`), plus the MAIN CRC at `0xC4FFC`. `0x3AB70` correctly still
`sar 0xa` (doubling *before* the `×gain_A` multiply would push the worst case to 94% of INT32_MAX vs 47%
after it). `0xC6440`/`0xC643E`/`0xC6442` all confirmed stock. Lane clamps re-confirmed at **±8192** each
(`0x3AB82`/`0x3AC42`) and the 11-lane aggregate at **±10240**, so it cannot produce an unbounded command.
GATE 1 vacuous — no cave, no RAM, no new opcode.

**Why it wins:** it is the matched inverse of V61, the only signed on-car result this kit has (`Kd`→0
diverged; `Kd`→2× is the same-sized step back), and it carries **no detector, gate, threshold or counter
anywhere in its path** — immune to the entire ambiguity that made V63/V64 inert. It delivers ×2 on both
lanes under every arm and every mode, against V64's ×1.78/×1.00.

⚠ **Pre-committed caveat, so it cannot drift.** r24 saturates at ±8192 once the input derivative exceeds
`8192·1024/gain` — **3639** (71% of the ±5120 input ceiling) at its stock 2305 default, **1820 (36%)**
under V62. Above that point both clamp identically, so **expect a partial improvement, not elimination**.
The benefit is that reaching the damping ceiling *earlier in each cycle* removes more energy per cycle
from a limit cycle.

**Route:** repeat route `31` for like-for-like — parking-lot creep, deliberate LKAS on/off passes at
matched speed and angle, **plus manual-forward and manual-REVERSE passes**. Manual reverse is the
highest-information single test: V61 introduced grinding there from nothing, with no LKAS in the loop.

**Interpretation, set in advance:** BETTER ⇒ direction confirmed, next question is how much more
(`sar 0x8` = 4×). NULL ⇒ the lane is **phase**-limited not gain-limited ⇒ next lever is `0xC6C42` (delay
D 4→2, confirmed this session to be aimed at r24/r26's actual input `gp-0x4f62`, though that output is
shared with `FUN_0002c478` and `FUN_0003b66a`). WORSE ⇒ past optimum, back off to 1.5×.

### 🛑 Why lowering `T` ranks behind it

Viable on **sizing** (~1.7–2× short), rejected on **blast radius**. `gp-0x671a` is **not private to the
rate lanes** — byte-scanned both encodings, whole image: 8 real hits, 6 reader functions, sole writer
`0x42A12`. Four are external:

- **`FUN_0003a382`** — uses it as a **continuous LERP index**, not a gate, shaping the live P/I/D lane
  `gp-0x6ad4`. This is the worst of them: it makes `T` a *shape parameter* on a lane already known to be
  load-bearing (V56 muted its ceiling and it cost damping).
- **`FUN_00036c12`** — friction-comp `gp-0x6b26`, sums into the **same aggregator**.
- **`FUN_000352b4`** — gates a 2nd-order IIR update.
- **`FUN_00035b20`** — selects between two LERP-blend curves.

⇒ **lowering `T` changes five things at once, four uncontrolled.** Not a clean GATE 1 and not a clean
experiment. By contrast `gp-0x67df` is clean (2 hits, both internal) and `T` itself has 4 readers, all
inside the detector. `CEIL` (`0xC64FA`) is **not** private — 3 external readers — and is a **BYTE cal = 5**
(a halfword read gives 517 and is wrong).

---

## 6. The methodological lesson worth keeping

**V64's probe did its job and the session should be read as a success of instrumentation.** V63's null
would have been uninterpretable; V64 converted it into a diagnosed one on the first drive, and told us
precisely which knob the record had been about to turn for the wrong reason.

**But it measured the mechanism's OUTPUT and not its INPUT or its ENABLE**, so an all-zeros reading left a
new ambiguity one layer up — closable only by a post-hoc firmware trace, after the drive.

Every gated mechanism is a chain: **`enable → input → threshold → state → effect`.** A probe on the
*state* collapses everything upstream into one undifferentiated null. **The number of drives needed scales
with how many upstream stages you leave unmeasured.** Ask, before building: *"if every bit reads zero, how
many different stories explain that?"* If more than one, the probe is not finished.

For this detector specifically, a future probe should carry **`gp-0x6c2c`** (one gp-relative i16) and the
**bit-5 inhibit state** alongside `gp-0x671a`. ⚠ V64 used **68/68 cave bytes with zero budget left**, so
that means dropping a state bit — which is the right trade, because the state bits are the ones that go
ambiguous.

A second, smaller one: **when a detector has both a threshold and a timeout, check the threshold first.**
The record predicted this detector "arms in ~125–150 ms at 18–21 Hz because the half-period is inside the
50 ms dwell timeout." That reasoned from the timeout alone and never asked whether the input reaches `T`.
It does not.

---

## 7. State at close-out

- **On the car: V64.** Flight-clean, grinding unfixed, detector inert.
- **Recommended next flash: V62** (built, verified, unflashed). Not flashed — awaiting explicit operator
  instruction naming the file and the bus.
- **Nothing was built this session.** `accord-firmwares` is unchanged and clean.
- **Collaterals updated:** `STATE.md` (headline, "On the car right now", built/unflashed table,
  recommended steps, signal-identity corrections), `BUILD-LINEAGE.md` (V64 → flashed/null, V63 → closed,
  V62 → promoted), the golden model (`detector_input_6c2c()` added; the falsified "arms in 125–150 ms"
  prediction struck in place; the `gp-0x671a` blast radius and the `FUN_00046ea6(5)` gate documented),
  and `memory/` (detector memory extended with the on-car result, two new memories, four index pointers).

### Open, none blocking
1. **`gp-0x4f50`'s physical units** — needs the ISR writing `gp-0x29c4`, or a probe. Without it the 1683
   figure is in counts of a signal of unknown scale.
2. **Which DTCs carry inhibit bit 5**, and the active-fault sweep's task rate — bounds how long a transient
   could inhibit the detector.
3. **`gp-0x6544[2]`'s producer** — the actual DTC-0x21 trigger in `FUN_000428d4`'s tail.
4. **`gp-0x671d`'s observer residual at creep** — quiet or noisy? It read 0 on this route.
5. **`avg(gp-0x69a4)`'s magnitude** — the long-standing V61/V62 residual; still unmeasured after four
   sessions. Bounded against by the fact that a saturated r26 would dominate the ±10240 sum clamp.
