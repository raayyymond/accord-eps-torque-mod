---
name: accord-gp6b4a-is-a-second-direct-lkas-term
description: "gp-0x6ad6 (the PID's driver-torque tracking reference) has TWO LKAS-command-descended terms, not one. Term 0 is gp-0x6b4a — direct, unconditional, NEGATED, with NO calibration weight anywhere on its path and a gate window (+/-25600) equal to the cell's own final clamp, so it can drive the reference to its full rail alone. It is structurally REINFORCING. The golden model's [VERIFIED] block at model/eps_lkas_chain_model.py:2318-2344 documented only the sibling gp-0x6b4c."
metadata:
  type: reference
---

# `gp-0x6b4a` — the SECOND, direct LKAS term into `gp-0x6ad6`. Traced 2026-08-10/11.

`FUN_00037fe6` (`0x37fe6`), the assist-reference-model aggregator that produces `gp-0x6ad6`:

```python
iVar4 = 0
if abs(gp_6b4a) <= 0x6400:      # 25600 — UNCONDITIONAL, negated, NO cal weight
    iVar4 = -gp_6b4a
if gp_67ab != 1:                # gates the OTHER SEVEN terms as a block
    iVar4 += sum(gated(term_i, window_i) * cal_weight_i for i in 1..7)
gp_6ad6 = clamp(iVar4 * speedLERP(gp_69aa) / 1024, ±25600)
```

**Two LKAS-descended terms, not one:**

| | signal | gate window | cal weight | ceiling as % of `gp-0x6ad6`'s rail |
|---|---|---|---|---|
| **term 0** | **`gp-0x6b4a`** | **±25600** | **none — implicit ×1, negated** | **100 %** |
| term 7 | `gp-0x6b70` (observer residual) | ±10240, own clamp ±8192 (`0xC6200`) | `0xC64B0` = 1 | **32 %** |

**A2 CONFIRMED by red-team, at instruction level:** every instruction from `gp-0x6b4a`'s load
(`0x37fea`) to its use in the final `add r13,r10` (`0x380b4`) is
`ld.h → addi → cmp → mov → bnc → sub → sxh → add`. **No `mulh` — no multiply of any kind — ever
executes on that path.** Contrast terms 1–7, each of which is `mulh`'d by its own cal byte
(`tp+0x74ac..0x74b3`).
**A3 CONFIRMED:** the `addi 0x6400 / ori 0xc801 / cmp / bnc` idiom is the standard `|x| ≤ K` test with
K = 25600, i.e. **term 0's own gate window is identical to the cell's own output rail** ⇒ term 0
alone, unweighted, can drive the reference to its rail.
**A5 CONFIRMED, byte-level:** `be 0x380b6` at `0x380b2` is bytes `A2 05`, low nibble `0x2` = **BE**,
distinct from `0xA` = BNE ⇒ the `gp-0x67ab == 1` gate really skips the 7-term add on **equality**. The
`be`/`bne` inversion class that has bitten this kit before **did not occur here.**

## Sign: term 0 is REINFORCING, not cancelling

`bias = clamp(gp-0x6ad6, ±8192)` → `err = clamp(gp-0x4f60 − bias, ±0x2800)` → P/I/D (all positive
gains) → `× authorityLERP(≥0) × polarity(gp-0x6752, boot-static +1)` → **ADDED** into the aggregator
(`mov`, `add`×8, no negation). Raising `gp-0x6b4a` makes term 0 more negative ⇒ bias more negative ⇒
`err` **rises** ⇒ PID rises ⇒ **more assist in the same direction as LKAS's own contribution.**
Same qualitative shape as the K1/friction mechanism. **The two negations (term 0's, and `error`'s
subtraction) cancel exactly.**

## What it corrects

- 🛑 **The golden model's `[VERIFIED]` tag was covering an incomplete picture.**
  `analysis-2020accord/model/eps_lkas_chain_model.py:2318-2344` documents `FUN_00026c80` as `[VERIFIED]` —
  "~11 LKAS-internal distribute sources summed into `gp-0x6b4c`, the LKAS lane into the aggregator."
  True, and it **missed `gp-0x6b4a`**, the wider **pre-combine sibling** from the same internal
  aggregate `iVar13` (`gp-0x6b4a = clamp(iVar13, ±0x6400)` @`0x277be`;
  `gp-0x6b4c = clamp(… + polarity × ((iVar13 × cal(0xC63CC)) >> 10), ±0x2800)` @`0x27722`).
  📋 **A `[VERIFIED]` tag certifies what was checked, not that nothing else is there.**
- 🛑 **`builds/v18_v49/build_v41_tva.py` / `BUILD-LINEAGE.md`'s "`0xC6194` architecturally inert" claim** is true only
  for the **sibling** `gp-0x6b4c`, not for `gp-0x6b4a`.

## 🛑 CONFIRMED 2026-08-13 (later), and the bar is 3.125× LOWER than this file framed it

`tracer-6ad6` found a hard clamp `0xC6200` = 8192 inside the PID that consumes `gp-0x6ad6`
(`FUN_0003a382` @ `0x3a7a2`, all three of P/I/D driven from the clamped difference) — crux verified by
the team lead directly in Ghidra. **"Term 0 alone can rail it" is CONFIRMED, but the practically
relevant threshold is the PID's ±8192 clamp, not `gp-0x6b4a`'s own ±25600 write clamp**: reaching
`|gp-0x6b4a| > 8192` already zeroes `∂(gp-0x6ad4)/∂(gp-0x6b70)` — that is **32% of term 0's own
clamp, i.e. 3.125× less signal than "rail it" (100% of ±25600) implied.**

Every other term's own gate window, expressed against the same 8192 threshold:

| term | signal | own gate window | headroom vs 8192 |
|---|---|---|---|
| 0 | `gp-0x6b4a` | ±25600 | needs only 32% |
| — | `gp-0x6b60` | ±15360 | needs 53% |
| — | `gp-0x6bc2`/`6b2a`/`6bce`/`6b6e`/`6bbc` | ±10240 each | needs 80% |
| 7 | `gp-0x6b70` (observer residual) | ±8192 (`0xC6200`, same cell) | **1.000× — already AT the threshold, no headroom needed at all** |

⇒ Term 7's own clamp and the PID's downstream clamp are the SAME cell, `0xC6200` — it is not a
coincidence that it is the easiest term to saturate the PID with.

🛑 **NEW: `gp-0x6b4a` is shadow-lockstep protected**, at `gp-0x4cd2`
(`0x27784/88`, `0x2779c/a0`, trap `0x2777c`) — see
[[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]]. Any future cave probe near this cell
must write both halves atomically, the same discipline as the four pairs already on record there.

## 🛑🛑 SUPERSEDING CORRECTION, 2026-08-13 (`tracer-4x-to-term0`) — **TERM 0 IS ≡ 0**

The A4 open question below ("what actually drives `gp-0x6b4a` off zero") is now **CLOSED: nothing does.**
**`gp-0x6b4a ≡ 0` on stock and on V99.** [EVIDENCE — enumerated at the caller level, two methods]

`gp-0x62e0[]` (→ `gp-0x6298[]` → term 0) is written **only** by `FUN_00025c32` @`0x25c32`, the
request-registration API. Confirmed two independent ways: the `movea gp-0x62e0` census (the six write
sites are all inside it; `0x27832`/`0x27b98`/`0x27bc0`/`0x27bda`/`0x27c62`/`0x27c82`/`0x27c9c`/`0x28d38`
are all `sld.h` **loads**), and the **lockstep-shadow invariant** — `movea gp-0x4b70` (the mandatory
shadow) appears at exactly the same six sites + the read-only checker, and a writer that skipped its
shadow would trip `FUN_00028d22` → `FUN_0006b9fa`.

**The struct offset map is the crux, and it is the opposite of the natural guess:**

| field | clamp | array | terminates in |
|---|---|---|---|
| **`param_1+2`** | ±16384 | `gp-0x62e0[]` | → `gp-0x6298[]` → **`gp-0x6b4a` = TERM 0** |
| **`param_1+4`** | ±10240 | `gp-0x62f8[]` | → `gp-0x62b0[]`/`gp-0x62c8[]` → `gp-0x6b4c`/`gp-0x6b4e` |

All **10** `jarl → FUN_00025c32` sites decoded at field `+2`: **NINE write hard `r0`**
(`0x23bc2 0x24162 0x2b52a 0x2c360 0x2cbd2 0x2e62e 0x33b48 0x3a95e 0x3b248`). Every lane puts its
payload at **+4**, not +2. The tenth, `0x341fe` (`FUN_0003405a`, **slot 2**), writes `r7` =
`gate ? gp-0x6b76 : 0` — and `gp-0x6b76 ∈ {0, 0x7FFF}` only, because its clamp cal `0xC616C` = **0**
(see [[accord-c616c-never-raise-driver-torque-relay]], independently re-derived). `0x7FFF` = 32767
exceeds that gate's own 20480 limit ⇒ forced to 0. **Both branches yield zero.**

⇒ `gp-0x6298[] ≡ 0` ⇒ `iVar13 ≡ 0` ⇒ **`gp-0x6b4a ≡ 0`.** Cal `0xC4118` = `[1]×11` ⇒ the OFF-partition
is empty, so the rate-limiter and residual terms are driven by zero too.

**Consequences:**
- **"Term 0 can drive the reference to its full rail alone" is TRUE STRUCTURALLY but VACUOUS in
  practice** — the lane carries no signal. `gp-0x6ad6` is entirely the *other seven* terms.
- **Term 0 is NOT the thing railing the PID's ±8192 clamp (`0xC6200`).** That suspect is dead.
- 🛑 **The 4× forward LKAS gain does NOT reach term 0.** `FUN_0002b422` @`0x2b52a` writes a literal
  `r0` to +2 and puts the 4×-gained command at +4 → `gp-0x62f8[1]` → (slot 1 is **mode 0**) →
  `gp-0x62b0[1]` → **`gp-0x6b4c`**. See
  [[accord-4x-gain-feeds-6b4c-not-term0-and-the-struct-offset-map]].

🛑 **Array-map correction.** `gp-0x6b4c`/`gp-0x6b4e` are **not** two partition sums of `gp-0x62c8[]`:
```
gp-0x6b4e = clamp( SUM   gp-0x62c8[i], +-10240 )          # ungated
gp-0x6b4c = clamp( SUM_ON gp-0x62b0[i], +-10240 ) + polarity*((iVar13*cal_0xC63CC)>>10)   # 0xC63CC=0
gp-0x6b4a = clamp( SUM_ON gp-0x6298[i] + rateLimited + residual, +-25600 )
```
The array actually partitioned by `tp+0x5118[]` is **`gp-0x6298[]`**, and **both halves feed
`gp-0x6b4a`**. Sources: `gp-0x6298[]←gp-0x62e0[]`, and `gp-0x62b0[]`/`gp-0x62c8[]`←`gp-0x62f8[]`
(mode-dependent; `tp+0x5124` = `[0,0,5,0,5,5,0,0,0,5,0]`).

Minor: `gp-0x6b4a`'s writers are `0x27784`/`0x2779c`/`0x277aa` (`0x277be` is the join label).
`FUN_00028d22` is a **read-only** lockstep checker. `gp-0x6b30` is the **pre-gain** accumulator.

## Open / caveats

- ⚠ **`gp-0x67ab`'s exact trigger is still unresolved** (one writer, `0x2775c`, inside the same mixer).
  **If it is usually 1, term 7 never fires and term 0 is the ENTIRE reference-model story.**
- ⚠ **`gp-0x6b4a`'s typical magnitude in real driving is UNMEASURED** — no telemetry on it exists.
- 🛑 **A4 REFUTED**: `gp-0x6b4a` is *not* "all LKAS-internal". Lane 2 is resolver-descended and
  torque-gated — **but it is also structurally inert** ([[accord-c616c-never-raise-driver-torque-relay]]),
  and **what actually drives `gp-0x6b4a` off zero is an OPEN question**: nine of ten lanes write a
  literal 0 on the traced path, lane 2 is severed, and the two remaining contributors (the rate-limited
  `Σ gp-0x625c[i]` and a `gp-0x6a62`-indexed LERP term) were not traced.

Source: `docs/traces/TRACE-2026-08-10-driver-reference-vs-lkas.md` · `docs/review/REDTEAM-2026-08-11-term0-verdict.md`
Related: [[accord-gp6afe-gp6b4e-are-always-zero]] · [[accord-c616c-never-raise-driver-torque-relay]] ·
[[feedback_eps_lkas_chain_model_golden_reference]] · [[accord-friction-polarity-more-friction-is-more-assist]]
