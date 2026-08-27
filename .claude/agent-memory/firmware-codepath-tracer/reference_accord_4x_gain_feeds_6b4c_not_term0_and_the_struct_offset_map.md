---
name: accord-4x-gain-feeds-6b4c-not-term0-and-the-struct-offset-map
description: "The 4x forward LKAS gain (0xC6CD0 @0x2a1ee) reaches gp-0x6b4c ONLY -- term 0 (gp-0x6b4a) gets a hard-coded zero at 0x2b52a. The FUN_00025c32 request-struct offset map (+2 -> gp-0x62e0 -> term 0; +4 -> gp-0x62f8) is the crux and is the opposite of the natural guess. 9 of 10 registrants write r0 into +2; the sole live producer of term 0 is slot 2 / gp-0x6b76 from FUN_0003405a. Also: the 4x is UNSATURATED end to end -- its clamps tracked the gain and the next fixed clamp is 5.0x above."
metadata:
  type: reference
---

# The 4× is EXONERATED from term 0 — and it is delivering its full 4×

Traced 2026-08-13 (`tracer-4x-to-term0`), GhidraMCP + raw Python LE scan, harness-validated
(`gp-0x4f60` → 64 `ld.h` / 5 `st.h` / 7 six-byte = exact). Full trace:
`docs/traces/TRACE-2026-08-13-4x-gain-to-term0.md`.

## ⭐ THE STRUCT OFFSET MAP — the crux, and it inverts the natural guess

`FUN_00025c32(param_1)` @`0x25c32` is the **request-registration API** (10 callers, 11 slots):

| struct field | clamp | array | terminates in |
|---|---|---|---|
| `param_1+0` | — | slot index (0..10) | |
| `param_1+2` | ±`0x4000` | **`gp-0x62e0[]`** | → `gp-0x6298[]` → **`gp-0x6b4a` = TERM 0** |
| `param_1+4` | ±`0x2800` | **`gp-0x62f8[]`** | → `gp-0x62b0[]` → **`gp-0x6b4c`** |
| `param_1+6` | ±900 | `gp-0x6274[]` | |
| `param_1+8` | ±20000 | `gp-0x633c[]` | |

🛑 **The LKAS command sits at +4, NOT +2.** Getting this backwards inverts the whole verdict.

## The verdict, byte-level

`FUN_0002b422` @`0x2b422` is the only control-path consumer of the 4×:
```
0x2b52a  sst.h r0, 0x2[ep]    bytes 8104   <-- LITERAL ZERO into gp-0x62e0[1]  (TERM 0)
0x2b52c  sst.h r12,0x4[ep]    bytes 8264   <-- the 4x command into gp-0x62f8[1]
```
Slot 1 is **mode 0** (cal `0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]`) ⇒ `gp-0x62b0[1] = gp-0x62f8[1]`,
`gp-0x62c8[1] = 0`. ⇒ **4× → `gp-0x6b4c` only.**

**Forward frontier is EXHAUSTIVE — the 4×'s outputs `gp-0x6b38`/`6b3c`/`6b3a` have exactly FIVE
reader sites image-wide:** `0x2b418` (re-gate copy), `0x2b42e` (`FUN_0002b422`, the real path),
`0x2b5b2` (`FUN_0002b57a` float monitor → `FUN_00027802`, read-only: `0x2783a` is `sld.h`),
`0x4e8d2`/`0x4e8e2` (`FUN_0004e82e` CAN TX packer, frame bytes 7–8 = report only).
⚠ `get_xrefs_to` on gp-relative RAM (`0xFEDF14C8`) returns a **tool zero** — Ghidra defines no data
there. Silence, not a negative.

## What DOES feed term 0 — closes a long-standing open question

All 10 `jarl → FUN_00025c32` sites decoded at the `+2` field: **NINE write `r0`.** The single live
producer is `0x34212` in **`FUN_0003405a`** (caller `FUN_00022ca0`, the *assist-shaping* task):
`0x341fa mov 0x2,r16` ⇒ **SLOT 2**, and
```
0x340a8  ld.h -0x6b76,gp,r7    ; gate PASS -> r7 = gp-0x6b76
0x34114  mov  0x0,r7           ; gate FAIL -> r7 = 0
0x341fe  sst.h r7,0x2[ep]
```
⚠ Ghidra shows this as `uStack_2a = (undefined2)iVar7` — a **reused variable**; only the assembly
resolves it. No `r7` write exists in `0x34118–0x341f6` (disassembled in full).
`gp-0x6b76` is **1 writer / 1 reader**: `0x3402c st.h r8` where
`r8 = (r1==0) ? 0x7FFF : ((r6==0) ? 0 : -r14)`. **`0x7FFF` is the invalid-sentinel and 32767 > the
gate's 20480 ⇒ the sentinel forces term 0 to ZERO.**

## The 4× is NOT self-defeating — no saturation on its path

| | stock 1× | modern 4× | ratio |
|---|---|---|---|
| gain (`0xC646C` → `0xC6CD0` at V57) | 891 | 3564 | 4.000× |
| clamps `0xC61B2` / `0xC61B4` | 512 | **2048** | 4.000× |
| ceiling into `gp-0x62b0[1]` | ±512 | **±2048** | 4.000× |
| next **fixed** clamp (`FUN_00025c32` +4, and `gp-0x6b4c`) | ±10240 | ±10240 | **5.0× headroom** |

The clamps were raised with the gain pre-V38 (`BUILD-LINEAGE`: *"LKAS forward-path clamps 512 → 2048,
tracking the 4x gain"*). ⇒ **"extra command buys no extra authority" is REFUTED for the 4×.**

## Term 0's rail — real, but invariant to the gain

Cal `0xC4118` (`tp+0x5118`) = `[1]*11` ⇒ every slot is in the ON partition ⇒ the OFF-sum is 0 ⇒ the
rate-limiter term and its residual are both driven by zero. So
`gp-0x6b4a = clamp(gp-0x6298[2], ±25600)`, reachable **|16384|** = **2.000× the PID's 8192 threshold**
(`0xC6200`). **Term 0 CAN rail the PID clamp — via `gp-0x6b76`, and it is invariant to `0xC6CD0` at
every value.**

## 🛑🛑 FOLLOW-UP, same session — **TERM 0 IS ≡ 0. The rail suspect is DEAD.**

The sole live producer (slot 2, `gp-0x6b76`) turns out to carry nothing.
```
0x33fec / 0x34000 / 0x34010   ld.hu 0x716c,tp,rN      ; cal 0xC616C
0x34004 ble / 0x3400e bge     r14 = clamp(r2, +-cal)
0x3402c  st.h r8,-0x6b76,gp   ; r8 = (r1==0) ? 0x7FFF : ((r6==0) ? 0 : -r14)
```
**`0xC616C` = 0 in stock AND V99** (anchored: `0xC61B4`=512/2048, `0xC6200`=8192, `0xC646C`=891 all
reproduce). A clamp with limit 0 **annihilates its input** ⇒ `r14 ≡ 0` ⇒ **`gp-0x6b76 ∈ {0, 0x7FFF}`
only**, and `0x7FFF`=32767 exceeds `FUN_0003405a`'s own 20480 gate ⇒ forced to 0. **Both branches
zero.** ⇒ `gp-0x62e0[] ≡ 0` ⇒ `gp-0x6298[] ≡ 0` ⇒ **`gp-0x6b4a ≡ 0`**.

**`gp-0x62e0[]` has exactly ONE writer function, confirmed two independent ways:** the `movea`
census (all six write sites inside `FUN_00025c32`; `0x27832`, `0x27b98/bc0/bda/c62/c82/c9c`, `0x28d38`
are all `sld.h` **loads**) **and the lockstep-shadow invariant** — `movea gp-0x4b70` appears at exactly
those six sites + the read-only checker; a writer skipping its shadow trips `FUN_00028d22`→`FUN_0006b9fa`.

🛑 **This INDEPENDENTLY REPRODUCES `memory/accord/calibration/accord-c616c-never-raise-driver-torque-relay.md` (2026-08-11).**
`0xC616C` is a **NEVER-RAISE** cell — raising it injects a Coulomb relay on **driver-torque sign**
(`gp-0x4f60`, confirmed as the clamped input at `FUN_00033d10`) into the assist reference: the V80
class. ⚠ **It is NOT virgin** — `builds/v80_v107/build_v93_tva.py`/`builds/v80_v107/build_v94_tva.py` reference it. **Grep the lineage
before ever naming this cell.** Refinement only: the idiom is `clamp(driver_torque, ±cal)`, which
*saturates to* `sign×cal` — same hazard verdict, and identical at cal=0.

⇒ **`gp-0x6ad6` is entirely the OTHER SEVEN terms** (gated as a block by `gp-0x67ab`). Anything railing
the `0xC6200` ±8192 clamp comes from there, **not** from term 0 and **not** from the LKAS gain.

⊕ `gp-0x6b78` is the **live** sibling (a real PI-ish cascade output, ±`gp-0x6b96`, polarity `gp-0x6752`)
and it *does* reach slot 2 field **+4** ⇒ `gp-0x62f8[2]` ⇒ (slot 2 is **mode 5**) ⇒ `gp-0x62c8[2]` ⇒
**`gp-0x6b4e`**. ⚠ That sits uneasily with the standing "`gp-0x6b4e` ≡ 0" claim — **unresolved, flagged,
not chased.**

## 🛑 Corrections to the record

- **`gp-0x6b4c` / `gp-0x6b4e` are NOT two partition sums of `gp-0x62c8[]`.** `gp-0x6b4e = Σ gp-0x62c8[]`;
  `gp-0x6b4c = Σ_ON gp-0x62b0[]`. The array actually partitioned by `tp+0x5118[]` is **`gp-0x6298[]`**,
  and **both** halves feed `gp-0x6b4a`.
- **"`0xC63CC`=0 ⇒ `gp-0x6b4c` does NOT carry the LKAS command" is MISLEADING as indexed.** `0xC63CC`=0
  kills only the `iVar13 → gp-0x6b4c` cross-term. `gp-0x6b4c` **does** carry the 4× LKAS command, via
  `gp-0x62b0[1]`. ⚠ Ask the operator before editing that entry.
- `gp-0x6b4a`'s writers are `0x27784` / `0x2779c` / `0x277aa` (not `0x277be`, which is the join label).
- `gp-0x6b30` is the **pre-gain** accumulator ⇒ invariant to `0xC6CD0`.
- `FUN_00028d22` @`0x28d22` is a **read-only shadow-lockstep checker** over all the request arrays —
  it writes only the fault code `gp-0x690a` and index `gp-0x6909`.

## 1 kHz call order (decoded `jarl`, `FUN_0002214a`)
```
0x022522 FUN_00028ea6 (4x) -> 0x022530 FUN_0002b422 -> 0x022572 FUN_0002b57a
-> 0x0225b4 FUN_00028d22 -> 0x0225f6 FUN_00026c80 (writes 6b4a/6b4c/6b4e)
-> 0x022676 FUN_00038148 (reads 6b4c @0x3816c) -> 0x022696 FUN_00037fe6 (reads 6b4a @0x37fea)
-> 0x0226a0 FUN_0003a382 (PID, +-8192)
```
The 4× runs **before** the term-0 writer in the same tick ⇒ ordering did NOT exclude the path; only
the data did.

Related: [[accord-gp6b4a-is-a-second-direct-lkas-term]] ·
[[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]] ·
[[reference_accord_two_lkas_routes_gp6b4c_bypasses_auth]] ·
[[accord-4x-lkas-gain-is-the-frozen-variable]]
