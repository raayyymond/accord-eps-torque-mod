---
name: reference_accord_c6200_clamps_gp6ad6_inside_the_pid
description: 0xC6200 (=8192) is read at 0x3a7a2 INSIDE FUN_0003a382 and hard-clamps gp-0x6ad6 (the PID reference) before the error subtraction, so whenever |gp-0x6ad6| >= 8192 the PID's sensitivity to gp-0x6b70 — and to every Path-2 gain above it — is EXACTLY ZERO through P, I and D at once. Closes BUILD-LINEAGE.md:490's "3 unidentified readers". Conditions the 0.2565 authority figure.
metadata:
  type: reference
---

# `0xC6200` clamps `gp-0x6ad6` inside the PID — the saturation nobody in the kit had found

Traced 2026-08-13, task `tracer-6ad6`. Program `code.bin`; byte-identical on the V98 (on-car) and
V99 images (`code[0x37FE6:0x38146]`, `code[0x38148:0x382D8]`, `code[0x3A798:0x3A7F0]` all stock).
Full trace: `docs/TRACE-2026-08-13-v100-6ad6-and-ivar6.md`.

## The mechanism [EVIDENCE — `disassemble_bytes` dry_run + `decompile_function(0x3a382)`]

```
0003a798: ld.h  -0x6ad6[gp],r7     ; the REFERENCE, written with a ±25600 clamp
0003a7a2: ld.h  0x7200[tp],r6      ; cal 0xC6200 = 8192          <-- THE CLAMP CONSTANT
0003a7b0..0x3a7c8:                 ; r7 = clamp(r7, ±8192)
0003a7ca: ld.h  -0x4f60[gp],r8     ; MEASURED DRIVER TORQUE
0003a7ce: sub   r7,r8              ; err = torque − clamp(ref, ±8192)
0003a7d0..0x3a7e2:                 ; err = clamp(err, ±10240)    <-- SECOND saturation (0x2800 IMMEDIATE)
0003a7e8: mul   lp,r8,r0           ; -> P, and I and D both derive from the SAME `err`
```

⇒ **`|gp-0x6ad6| ≥ 8192` ⇒ `∂(gp-0x6ad4)/∂(gp-0x6b70) = 0` through P, I and D simultaneously.**
`gp-0x6b70` enters `gp-0x6ad6` at **unit weight** (`0xC64B0` = 1) through an **identity speed LERP**
(Y `0xC6ACA..0xC6AD8` all 1024, fallback `0xC6448` = 1024) ⇒ no dilution to hide behind.

🛑 **CONDITIONS a result the kit accepted this week:** `d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` is the
**UNSATURATED** derivative. Never quote it without `|gp-0x6ad6| < 8192`.

## `0xC6200` is FOUR things, not one [EVIDENCE — raw tp-disp16 scan, 15 hits, matches the record's count]

| sites | function | role |
|---|---|---|
| 6 in `0x353de..0x354f0` | `FUN_000352b4` | friction-magnitude lane |
| 4 in `0x382ac..0x382c6` | `FUN_00038148` | clamps **`gp-0x6b70`** |
| `0x38a94` | `FUN_000389ec` | Stage-2 LERP `Y[9]` |
| `0x39ff6` | `FUN_00039702` | not chased |
| **`0x3a7a2`/`0x3a7b2`/`0x3a7c4`** | **`FUN_0003a382`** | **clamps `gp-0x6ad6`** — the 3 that `BUILD-LINEAGE.md:490` called unidentified |

⭐ The SAME 8192 clamps Path-2's whole output *and* the whole reference ⇒ **Path 2's full scale is
exactly the width of the window it must fit inside.**

## `gp-0x6ad6` = the sum, and term 0 alone clears the bar with 3.125× to spare

`FUN_00037fe6` @`0x37fe6`: `clamp(−gp-0x6b4a + Σ7 zero-reject-gated terms, ±25600)`, all seven
weights `0xC64AD..0xC64B3` = **1**. `gp-0x6b4a ∈ ±25600` (writer clamp `0x27772..0x277aa`).
🛑 **Term 0 needs only `|gp-0x6b4a| > 8192` = 32 % of its own clamp — NOT ±25600.** Any framing that
says "term 0 must rail gp-0x6ad6" understates the hypothesis by 3.125×.

## Census, five methods, Ghidra ∖ Python EMPTY [EVIDENCE]
1 writer (`0x38142`), 2 readers (`0x3a6ba` = a plausibility gate only; `0x3a798` = the control path).
disp23 **0** · 32-bit literal `0xFEDF152A` **0 image-wide** · `ep`-alias **0 of 1,295 candidate
bases in reach**. Two extra Python hits (`0xBCC52`, `0xBDF92`) are `st.b -0x6ad5[gp]` inside a
monotone data table with no function — **my own bit-0 alias rule over-matched; `st.b` does not use
bit 0.** ⚠ Remember that: the alias rule is for `ld.w`/`st.w`/`ld.hu` ONLY.

## `gp-0x6ad6` has NEVER been on the wire
`grep -l 6ad6 build_v*_tva.py` → v43/46/52/52c/53/96/vfourframe, **all prose, no probe**.
A `|gp-0x6ad6| ≥ cal(0xC6200)` rung costs **24 B** using only flown-cave and Ghidra-certified Honda
twins (`ld.hu 0x7200,tp,r6` = `e5370172` is verbatim Honda @`0x382BC`), r6/r7 only, `{bge}` only,
store set unchanged — **net −8 B** if it replaces V98's spent b5.

Related: [[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]] ·
[[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]] ·
[[reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound]] ·
[[reference_accord_ivar6_register_only_and_the_1khz_call_order]]
