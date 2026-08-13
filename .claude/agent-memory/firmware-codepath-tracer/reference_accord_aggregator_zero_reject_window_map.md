---
name: reference_accord_aggregator_zero_reject_window_map
description: The aggregator FUN_0003aa2c puts an addi/addi/cmovc ZERO-REJECT window on 8 of its 11 lanes (not all 11), and the half-widths DIFFER per lane (0x400/0x800/0x2000/0x2800/0x3000) -- full address map. gp-0x6b4c (LKAS) is verified vacuous with EXACTLY ZERO margin: its producer FUN_00026c80 clamps to the same +/-10240 the gate admits. Only 2 of 8 producer ceilings are actually verified, so the record's blanket "all eight are vacuous" is NOT closed.
metadata:
  type: reference
---

# The aggregator's 8 zero-reject windows — full map, 2026-08-12 (`fw-return`)

`FUN_0003aa2c` @`0x3aa2c` sums 11 lanes at unity weight into `gp-0x6b94`. **Eight of them pass a
zero-reject window first**, and the widths are **not uniform**.

The idiom (and the trap):
```
addi +W,        rX, rY     ; rY = lane + W
addi -(2W+1),   rY, r0     ; CY set iff rY >= 2W+1
cmovc 0x0,      rX, rZ     ; rZ = CY ? 0 : lane     -> OUT-OF-RANGE REJECTED TO 0
```
⚠ **V850 `CY` is the carry-OUT of the addition**, so a subtract sets CY when there is **no** borrow.
Reading it as a borrow inverts the gate. Same idiom as the shaper's `gp-0x6acc` gate.

## The map [EVIDENCE — `search_instructions(mnemonic="addi", function="FUN_0003aa2c")`, 25 hits, `truncated:false`, `instructions_scanned: 280`]

| lane | load | window pair | half-width | producer ceiling | vacuous? |
|---|---|---|---|---|---|
| `gp-0x6b62` end-stop | `0x3aa38`→r9 | `0x3aa50`/`0x3aa54` | ±8192 | ≲5786 | yes [BELIEF] |
| **`gp-0x6b4c` LKAS** | `0x3aa3e`→r6 | `0x3aa5c`/`0x3aa60` | **±10240** | **exactly ±10240** | **yes, ZERO margin [EVIDENCE]** |
| `gp-0x6ade` | `0x3aa48`→r14 | `0x3aa68`/`0x3aa6c` | ±1024 | — | **unverified** |
| `gp-0x6bd0` damper | `0x3ac78`→r9 | `0x3ac84`/`0x3ac88` | ±2048 | — | **unverified** |
| `gp-0x6b86` peak-hold | `0x3ac7c`→r14 | `0x3aca0`/`0x3aca4` | ±12288 | — | **unverified** |
| `gp-0x6bbe` viscous | `0x3ac80`→r6 | `0x3ac90`/`0x3ac94` | ±2048 | — | **unverified** |
| `gp-0x6b26` inertia | `0x3ac98`→r11 | `0x3acb0`/`0x3acb4` | ±1024 | ≈14-21 % of ±511 | yes (prior record) |
| `gp-0x6ad4` | `0x3aca8`→r6 | `0x3acbc`/`0x3acc0` | ±10240 | — | **unverified** |

**NO window** on the other three lanes: `r24`, `r26` (RAM-gain lanes off `gp-0x6e40/6e38/6e30/6e28`)
and `FUN_00036682()`→`gp-0x6b46`. The remaining 17 `addi` hits are single-sided (`dst=r0`, no paired
`+W`) — clamps/branches, not this gate.

## `gp-0x6b4c` — the one that looked risky, and isn't [EVIDENCE]

Producer `FUN_00026c80` clamps it to **exactly ±0x2800 = ±10240**:
```
0x276ec: movea 0x2800,r0,r8  / 0x276f0: st.h r8,-0x6b4c[gp]   UPPER CLAMP
0x27704: movea -0x2800,r0,r8 / 0x27708: st.h r8,-0x6b4c[gp]   LOWER CLAMP
0x27716: st.h r10,-0x6b4c[gp]                                 pass-through, only |r10| <= 10240
```
The gate admits `[−10240, +10240]` **inclusive**: at `x=+10240`, `0xFFFFAFFF + 0x5000 = 0xFFFFFFFF`,
no carry out ⇒ CY=0 ⇒ accepted. CY only sets at `|x| ≥ 10241`.
⇒ **producer ceiling ≡ gate width.** Vacuous by *exactly zero margin* — a corruption/plausibility
check, not a functional limiter. The LKAS command is large and still cannot trip its own gate.

## 🛑 What is NOT established
**Only 2 of 8 producer ceilings are verified** (`gp-0x6b4c` at the producer; `gp-0x6b26` from the
prior record). The matched-constant design of `gp-0x6b4c` is [BELIEF] evidence the other seven follow
the same pattern, but **the kit's blanket "all eight aggregator zero-gates are vacuous" is a claim
about REACHABILITY and is not closed.** Anyone raising a lane's producer ceiling must re-check its
window — a lever that lifts a producer above its gate width turns the gate from vacuous into a
**hard zero-reject relay**, which is the V80 failure class.

⚠ Register-indirect residual: `movea -0x6b4c, gp, r7` @`0x28b38` takes the cell's **address** into a
register (lockstep repair via `FUN_0006b9fa`). An operand-text-only writer census misses it. It writes
a repaired copy of the same clamped value, so the bound holds.

## Related
[[reference_accord_return_centre_is_an_end_stop_cushion_not_centring]] — the lane whose window
(`gp-0x6b62`, ±8192) first exposed this idiom.
