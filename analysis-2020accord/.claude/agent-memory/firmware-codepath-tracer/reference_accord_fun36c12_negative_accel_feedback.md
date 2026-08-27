---
name: reference-accord-fun36c12-negative-accel-feedback
description: FUN_00036c12's gp-0x6b26 is NEGATIVE acceleration feedback (LERP Y all negative, no polarity multiply, enters with +) — reactively it ADDS apparent inertia, though it also has a genuine dissipative real part; its 0xCBE74[mode] LERP is indexed on VOTED VEHICLE SPEED (gp-0x6a5e), so k is 5.0x stronger at CREEP than at 90 km/h.
metadata:
  type: reference
---

Settled 2026-08-10 on stock `code.bin` — this closes OPEN #3 of
`docs/research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md`, **and reverses its premise.**

## The arithmetic [EVIDENCE, `decompile_function 0x36c12` + LE byte reads]

```
sVar7     = LERP( gp-0x6a5e , record at *(u32*)(0xCBE74 + mode*4) )
iVar4     = ((short)( gp-0x6c2c × gate(|gp-0x6c2c| ≤ 32000) ) × sVar7 >> 6) × 0x111
gp-0x6b26 = clamp( iVar4 >> 0x12 , ± *(short*)(tp+0x507e) )      # tp+0x507E = 0xC407E = 511
            + shadow gp-0x4cd0
```
Net scale `273 / (64 × 262144)` = 1.6272e-5. **No `gp-0x6752` polarity multiply anywhere in the
function** — the term is sign-locked to `gp-0x6c2c`'s own convention. It enters BOTH `FUN_0003aa2c` and
`FUN_00038148` with a plain **`+`**.

## 🛑 THE SIGN: NEGATIVE ACCELERATION FEEDBACK, NOT COMPENSATION

Records for modes **10 / 24 / 26 are byte-identical**: `count=3`, `X = {0, 1280, 5760}`,
**`Y = {−9830, −5734, −1966}` — negative across the entire domain.** Pointers: mode 24 → `0xD6A64`,
mode 26 → `0xD7A54` (array base `0xCBE74`, 34 entries).

⇒ **`gp-0x6b26 = −k·(motor acceleration)`, k > 0.** It OPPOSES acceleration and ADDS apparent inertia.
It is **not** the classical `+k·α` that cancels felt inertia. The 2026-08-06 doc's "textbook inertia
compensation" reading is **wrong**.

## 🛑🛑 THE INDEX IS VEHICLE SPEED — I GOT THIS WRONG, CORRECTED 2026-08-10

**This section previously read "THE INDEX IS DRIVER TORQUE, NOT SPEED" and concluded the term is
"strongest on-centre and hands-light". THAT WAS WRONG.** Caught by agent DampAxis, verified by the
orchestrator, and **already settled three weeks earlier** by
`memory/reference/firmware/reference-accord-gp6a5e-is-speed-reclassifies-v44-v47.md` (2026-07-29, two independent traces
plus a byte-verified pointer chase) — which I failed to consult.

**`gp-0x6a5e` is VOTED VEHICLE SPEED.** Sole writer `FUN_00041eec` @`0x42342`, the 5-channel speed
voter, validity window `−6400 ≤ x ≤ 32000` (nonsensical for a torque sensor, right for a speed channel
with overrange headroom). **Dimensional check at 64 ct/km/h** (anchored on FactorC `X[0]` = 2240 =
35 km/h): the friction record's `X = [0, 1280, 5760]` reads **[0, 20, 90] km/h exactly.**

⇒ **k is 5.0× stronger at 0 km/h (−9830) than at 90 km/h (−1966) — strongest at CREEP, not
hands-light.** Both regimes are symptom-relevant, which is exactly why the error slipped through, but
the lever rationale is different: the schedule is on **road speed**, not driver effort.

🛑 **THIRD RECURRENCE of a signal-identity error in this kit; the previous two each cost a flashed
build (V44, V47).** The lesson that generalises: **the repo `memory/` tree and this agent tree are
SEPARATE and can disagree — grep BOTH before asserting a signal identity.**
⚠ **This error is not contained to this file.** The "Sensor A = driver torque" framing in
[[reference-accord-dual-torque-sensor-architecture]], [[reference-accord-can399-torque-vs-voter-scale]],
[[reference-accord-lkas-column-torque-cut-trigger]] and
[[reference-accord-segmentD-fun3d04c-full-gate-map]] inherits it. The 2026-07-29 memory states it
**retires the kit's "Sensor A" label** outright. Flagged to the orchestrator; not swept here.

## Lever guidance

**`0xC407E` has NEVER been taken BELOW 511** [EVIDENCE, grep `build_v*_tva.py`]: stock/V38/V72 = 511 ·
V73/V74/V75 = **850** (V74/V75 hard-faulted) · V76→V89 = 511, restored by V81 (`5203`→`ff01`).
3 signed `ld.h` readers, all inside `FUN_00036c12`.

**Prefer the LERP gain `0xCBE74[24]/[26]` over the clamp `0xC407E`:**
- 🛑 Lowering `0xC407E` is the **V80 flatten-to-relay hazard from the other side** — a clamp pulled low
  enough that the term saturates becomes **bang-bang on sign(motor acceleration)**. Scaling the Y-values
  is memoryless: cannot saturate, every pole stays bit-identical.
- RULE 7 satisfied (TVCA4 = modes 24/26), but they are **separate records — BOTH must be written.**
- ⚠ **Weakness:** m24 ≡ m26 byte-identically ⇒ the term is **NOT engagement-armed**, while the symptom
  IS engagement-amplified. It can only be the mechanism if it amplifies an input that itself grows with
  engagement (`gp-0x6c2c`; see [[accord-gp6c2c-is-motor-rate-derivative]]). BELIEF.
- ⚠ **NOT SIZED** — `|gp-0x6b26|`'s reachable magnitude vs the ±511 clamp was never computed, so any
  "back it down" proposal currently has **no dose**. `gp-0x6b26` is 1-writer + shadow ⇒ a cave probe is
  cheap and is the right next step.

Related: [[reference-accord-observer-gate-tautology-and-term-mismatch]] (same trace).
