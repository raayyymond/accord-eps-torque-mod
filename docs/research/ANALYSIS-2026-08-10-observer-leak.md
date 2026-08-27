# ANALYSIS — the observer "leak" hypothesis: DEMOLISHED, with two firm closures

**2026-08-10 · agent `ObserverMatch` · persisted by the orchestrator (the harness blocked the
subagent's own file write; content is the agent's, verbatim in substance).**
**Study/analysis only. Nothing was built, flashed, or sent on CAN.**

Reproducer created and on disk: **`analysis-2020accord/studies/models/observer_leak_model.py`** — runnable and
self-checking; it asserts every calibration against its stock value before computing.

---

## HEADLINE

1. **"Two filters on one signal" is DEMOLISHED** [EVIDENCE] — the two operands of the observer's
   subtraction do not carry the same term set. The leak is a **DC gain**, not a phase residue.
2. **And the leak FALLS with frequency** [EVIDENCE] — 0.90× at 7.79 Hz and **0.56× at 21 Hz** of its
   DC value. **A low-pass leak cannot preferentially excite either symptom band.** ⇒ mechanism
   **EXONERATED**.
3. **The enable-gate dropout is dead structurally** [EVIDENCE] — `|gp-0x6b98| ≤ 0x2000` is **TRUE BY
   CONSTRUCTION**: the producer clamps to exactly ±0x2000 four instructions before the store.
   **The observer never drops out.**
4. **The `FUN_00036c12` sign is SETTLED, opposite to the standing assumption** [EVIDENCE] —
   `gp-0x6b26 = −k·(motor acceleration)`, k > 0. It is **not** inertia compensation; it **opposes
   acceleration and adds apparent inertia**.
5. 🛑 **Build nothing on this.** V86 already flew `0xC40D4` 573 → 286 to a well-powered null. A
   phase-match proposal is *the same lever pushed further in the same direction*.

---

## §A — STRUCTURE

### A.1 — filter orders CONFIRMED
`0xC40D4` (`tp+0x50d4`) **is applied twice**, through two distinct states `gp-0x3628` then
`gp-0x3624`, the coefficient re-read as `uVar8` ⇒ genuinely **2-pole, α = 573/4096**. The sensor
branch mirrors the structure with `0xC40D8` = 3686. Branch B's IIR is **single-pole**,
α = `0xC63AC`/1024 = 102/1024, state `gp-0x374c`; the `×0x10` / `>>4` pair is IIR resolution, not gain.

✅ **Self-validation.** Adding one tick of transport to `H_A` reproduces the golden model exactly:
7.79 Hz −33.25° − 2.80° = **−36.05°** (model: −36.06°); 21.09 Hz −75.25° − 7.59° = **−82.84°**
(model: −82.84°). The filter forms are right.

### A.2 — NOT THE SAME SIGNAL [EVIDENCE]
Branch B's six lanes: `gp-0x6b4e · 6b4c · 6b26 · 6b46 · 6bd0 · 6bbe`
(weights `0xC63A0`…`0xC63AA`, all byte-read **1024**).

Aggregator `FUN_0003aa2c` into `gp-0x6b94`:
`gp-0x6b62 · 6b4c · 6ade · ` **`6ad4`** ` · 6b26 · 6bbe · 6bd0 · 6b86 · r24 · r26 · FUN_00036682()`.

- Shared: **4 lanes only.**
- In B but not the aggregator: `gp-0x6b4e`, `gp-0x6b46`.
- **In the delivered command but ABSENT from B:** `gp-0x6ad4` (**this loop's own PID output**), r24,
  r26, `gp-0x6b62`, `gp-0x6ade`, `gp-0x6b86`, `FUN_00036682`.
- Plus, between the aggregator and `gp-0x6b98`: the governor's **nonlinear slew**, the comp-add, the
  Q15 shaper blend, **the ADD of the CAN-arbitrated `gp-0x6afe`**, and two clamps.

### A.3 — sign and `>>4` confirmed
`resid = gp-0x6bfe (+) − (iVar4 >> 4) (−) + gp-0x6bfa (+)`; arithmetic shift on a signed int.

**`gp-0x6bfa`: 1 reader (`0x38208`), 3 writers, all inside `FUN_00026c80`.** Disassembly
`0x27396`–`0x273b8`: it is a **saturating ±0x4E20 (±20000) 16-bit view of a 32-bit accumulator
`gp-0x3d90`**, shadow `gp-0x4cfa`.
⚠ **What `gp-0x3d90` integrates was NOT resolved** — only that `gp-0x6bfa` shares the ±20000 unit
space with `gp-0x6bfc` / `gp-0x6bfe`. "Mixer output" is as far as the evidence goes. **[OPEN]**

### A.4 — the two scaling conventions CANCEL
- Branch A: `/1024` → EMA² → **raw float** × `0xC6468` (2639) = **×2.5771**.
- Branch B: `w = 1024` unity → `× 0xC6468 >> 10` = **×2.5771**.

Identical net scale **and** identical polarity handling ⇒ **[BELIEF, strong]** Honda *did* intend a
cancellation here and matched the units deliberately. **It is the term sets that do not match**, not
the scaling. The golden model's "same cal, two conventions, a 1024× trap" warning is correct as a
warning but the two conventions are consistent in effect.

---

## §B — THE LEAK, QUANTIFIED

`leak(f, κ) = |2.5771·H_A(f) − κ·2.5771·H_B(f)|`, where **κ** = the fraction of a `gp-0x6b98`
excursion that the six lanes actually reproduce. κ = 1 is the hypothesis; §A.2 forces **κ < 1**.

| κ | DC | 7.79 Hz | 21.0 Hz | 7.79/DC | 21/DC |
|---|---|---|---|---|---|
| 1.00 | 0.0000 | 0.3915 | 0.7364 | ∞ | ∞ |
| 0.80 | 0.5154 | 0.5806 | 0.6689 | 1.13 | 1.30 |
| 0.60 | 1.0309 | 0.9784 | 0.7467 | 0.95 | 0.72 |
| 0.40 | 1.5463 | 1.4191 | 0.9343 | 0.92 | 0.60 |
| 0.00 | 2.5771 | 2.3317 | 1.4555 | **0.90** | **0.56** |

**Read row-wise.** κ = 1 is the only row where the DC term vanishes and the band ratio blows up — and
it is the row ruled out by §A.2. **Every achievable row is a flat DC gain that falls with frequency.**

Per the orchestrator's own pre-stated falsifier — *"if the DC leak is already large, the
phase-mismatch story is wrong and this is just a gain"* — **the DC leak is large. The story is wrong.**

🛑 **The analysis deliberately stops at `resid`.** `resid → gp-0x6b70` passes a LERP whose **Y[0] lives
in RAM** (ep-relative: `movea -0x3714,gp,ep` @`0x39508`, `sld.hu` @`0x3950C`) and is not statically
resolvable. `FUN_00037fe6` is unity (7 enable bytes byte-read **1**; speed LERP flat at 1024).
Quoting motor-side counts would require inventing that slope. **Not done.**

---

## §C — NO FIX PROPOSED

**Reason 1 — structural.** Solving `∠H_A = ∠H_B` needs `0xC40D4` ≈ **208** at 7.79 Hz but ≈ **192** at
21 Hz. One value cannot serve both (different filter orders), exactly as predicted. Moot in any case:
at κ < 1 it buys close to nothing.

**Reason 2 — 🛑 LINEAGE: SAME LEVER, SAME DIRECTION, ALREADY FLOWN** [EVIDENCE,
`BUILD-LINEAGE.md:60`]. **V86** = `0xC40D4` 573 → **286**, flew route `6f`, fault-free.
`f(V86)/f(V85)` = **1.001 [0.976, 1.060]**, CI disjoint from the pre-registered [0.797, 0.875]; five
independent statistics null; the falsifier *could* have fired (**2.6× margin**); lever in force three
ways. The record's conclusion — *"the linear-loop hypothesis is dead … the firmware search on it is
CLOSED"* — stands. **A move to ≈208 is more of the same change, not a new lever.**

**Relay hazards:** a filter α cannot flatten a curve ⇒ **none of the three engaged.** All three
byte-confirmed stock this session: `0xC4080` = **0**, `0xC63AE` = **1024**, `0xC6200` = **8192**.

⚠ **`0xC40D4`'s full dual-encoding reader census was NOT completed.** Owed before any edit — though
§C's recommendation is not to make one. **[OPEN]**

---

## §D — THE ENABLE GATE IS A TAUTOLOGY [EVIDENCE]

Gate: `gp-0x6b98 + 0x2000U < 0x4001` ⇒ `gp-0x6b98 ∈ [−8192, +8192]`.
Producer, four instructions earlier:

```
0x43b0e  addi   -0x2000, r14, r0
0x43b12  movea   0x2000, r0, r21
0x43b16  bgt    0x00043b24
0x43b18  addi    0x2000, r14, r0
0x43b1c  movea  -0x2000, r0, r6
0x43b20  cmovle r6, r14, r21        ; r21 = clamp(r14, ±0x2000)
0x43b4e  mov    r21, r8
0x43b52  st.h   r8,  -0x6b98, gp
0x43dfc  st.h   r21, -0x6b98, gp
```

The bound **equals** the clamp and is inclusive at both rails (8192 + 8192 = 16384 < 16385).
**The gate cannot trip.** It is a defensive check on a value that cannot violate it.

**Census confirmed TWO ways:** GhidraMCP 45 hits (`truncated:false`, 183,570 instructions scanned);
raw little-endian byte scan of **both** encodings (disp16 `hw2 == 0x9468`; extended
`{8407|a407} 87?? 28ff`) = **33 + 12 = 45. Exact agreement.**
Writers: `0x43b52`, `0x43dfc` (normal path, clamped); `0x6e104`, `0x6e1dc` (**limp mode**; inherited
max 5325 < 8192 — **[BELIEF, not re-derived]**).

The other three gate conditions are equally slack: `|gp-0x4f60| ≤ 25600` is the sensor's own window;
`|gp-0x6abc| ≤ 13000` against ±1,930 reachable; `gp-0x6752` is static.

⊕ **The same idiom repeats one hop down:** `FUN_00038148`'s sentinel is `|gp-0x6bfe| ≤ 20000`, and
`gp-0x6bfc` is clamped to **exactly ±20000**. **Also tautological.** Two sentinel paths, both
unreachable from their own producers.
⊕ Consistent with the V87 flight: `gp-0x6b70` non-zero **99.80 %**.

**RANKING:** phase mismatch **exonerated** (the leak falls with frequency); gate dropout
**structurally impossible**. **Neither explains the symptom. Both CLOSED, not merely unsupported.**

---

## §E — `FUN_00036c12`: THE SIGN IS SETTLED, AND IT REVERSES THE STANDING PREMISE

```
sVar7     = LERP( gp-0x6a5e , *(u32 *)(0xCBE74 + mode*4) )
iVar4     = ((short)(gp-0x6c2c × gate(|x| ≤ 32000)) × sVar7 >> 6) × 0x111
gp-0x6b26 = clamp( iVar4 >> 0x12 , ± *(short *)(tp+0x507e) = 0xC407E = 511 )   + shadow gp-0x4cd0
```

- **No `gp-0x6752` polarity multiply anywhere in `FUN_00036c12`.** It enters both the aggregator and
  `FUN_00038148` with a plain **`+`**.
- 🛑 **Records for modes 10 / 24 / 26 are BYTE-IDENTICAL:** `count = 3`, `X = {0, 1280, 5760}`,
  `Y = {−9830, −5734, −1966}` — **NEGATIVE across the whole domain.**

⇒ **`gp-0x6b26 = −k·(motor acceleration)`, k > 0 — NEGATIVE ACCELERATION FEEDBACK. It ADDS apparent
inertia; it does NOT cancel it.** `research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` §6.1 / OPEN #3
("textbook inertia compensation", sign unknown) **is wrong on the premise and must be corrected.**

⊕ 🛑 **The LERP index is `gp-0x6a5e` = VOTED DRIVER TORQUE, not vehicle speed.** Both the feasibility
doc and the brief call `0xCBE74[mode]` a "speed LERP". **It is not.** ⇒ **k is 5.0× stronger at zero
driver torque (−9830) than at high driver torque (−1966)** — i.e. strongest **on-centre /
hands-light**, which is the operator's micro-ratcheting regime.
[EVIDENCE for the schedule; the link to the symptom is **BELIEF**.]

**`0xC407E` has NEVER been below 511** [EVIDENCE, grep of `build_v*_tva.py`]: stock / V38 / V72 = 511;
V73 / V74 / V75 = **850** (V74 and V75 **FAULTED**); V76 → V89 = 511, restored by V81
(`builds/v80_v107/build_v81_tva.py:20`, `5203` → `ff01`). Three signed `ld.h` readers, all inside `FUN_00036c12`.

### Recommendation: the LERP gain `0xCBE74[24]` / `[26]`, **NOT** the clamp
- 🛑 **Lowering `0xC407E` is the V80 relay hazard from the other side.** A clamp pulled low enough that
  the term saturates becomes **bang-bang on `sign(motor acceleration)`**. Scaling the Y-values instead
  is **memoryless: it cannot saturate, and every pole stays bit-identical.**
- **RULE 7 satisfied.** The car is TVCA4, modes 24/26; records at **`0xD6A64`** and **`0xD7A54`**,
  byte-identical to each other and to mode 10 ⇒ the dose is unambiguous, but **BOTH must be written.**
- ⚠ **Real weakness, stated plainly:** because m24 ≡ m26 byte-identically, **this term is NOT
  engagement-armed**, while the operator's symptom **is** engagement-amplified (6–9 Hz ×2.8,
  band-specific). It can only be the mechanism if it amplifies an input that itself grows with
  engagement (`gp-0x6c2c` plausibly does). **That is BELIEF.**
- ⚠ **NOT SIZED.** `|gp-0x6b26|`'s reachable magnitude against the ±511 clamp was not computed, so
  "back the gain down" currently has **no dose**. `gp-0x6b26` is 1-writer + shadow ⇒ a cave probe is
  cheap. **Do this before proposing V90.**

---

## OPEN ITEMS → the exact next step for each

1. `gp-0x3d90` — what `gp-0x6bfa` integrates. → full decompile of `FUN_00026c80`.
2. `resid → gp-0x6b70` LERP slope (RAM Y[0] at `gp-0x3714`). → cave probe, or a live RAM read.
3. `0xC40D4` dual-encoding reader census — never completed.
4. **`|gp-0x6b26|` dose against ±511.** → cave probe. **Highest value of the four.**
5. Limp-mode writers `0x6e104` / `0x6e1dc` maxima. → decompile `FUN_0006e09a` / `FUN_0006e140`.

---

## CORRECTIONS TO THE RECORD

1. 🛑 **Golden model line ~1269 is FALSE.** *"🛑 A COMMAND-CONDITIONAL DISCONTINUITY: under strong
   command Path 2 goes invalid"* — the gate is a tautology against the producer's own ±0x2000 clamp.
   **The most load-bearing correction in this report.**
2. **`0xCBE74[mode]` is indexed on VOTED DRIVER TORQUE, not speed.** Wrong in
   `research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` §6.1 and in the brief that quoted it.
3. **`research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` OPEN #3's premise is wrong** — the term's sign
   *opposes* acceleration; it is not a compensator awaiting a sign check.

**Net:** the task was to verify or demolish. It demolished. The two closures — the leak falls with
frequency, and the gate cannot trip — are firmer results than a confirmation would have been.
**No build is proposed.**
