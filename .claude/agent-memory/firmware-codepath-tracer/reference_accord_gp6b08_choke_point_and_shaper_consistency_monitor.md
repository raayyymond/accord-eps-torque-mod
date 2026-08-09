---
name: reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor
description: gp-0x6b08 is the narrowest node in the whole assist chain (1 writer, 2 readers, all inside FUN_00042af8, NO shadow-lockstep partner) and in the live 0xC64C8=0 config is a pass-through copy of gp-0x6acc — but its second "reader" at 0x43A96 is a consistency MONITOR enforcing |downstream| <= |gp-0x6b08|+5 with sign match, which forbids amplification and makes attenuating the cell itself risky
metadata:
  type: reference
---

Traced 2026-08-09 (`EXCITATION-TRACER`, low-speed ratchet brief), stock `code.bin`. Closes the
"last hop `0x43226`→`gp-0x6b98` is inherited, not hand-walked" gap the brief flagged — the real store
is at `0x43B52`, not `0x43226`.

## Census — Python byte scan, validated full opcode set {0x38..0x3F}, disp and disp|1

| cell | writers | readers | shadow pair |
|---|---|---|---|
| `gp-0x6acc` | 2 (`0x45932`,`0x45942`) | 4 (`0x431C4`,`0x4467A`,`0x458B8`,`0x45B16`) | **yes** `gp-0x4cc8` |
| `gp-0x6ace` | 4 | 7 | — |
| **`gp-0x6b08`** | **1** (`0x43206`) | **2** (`0x432E6`,`0x43A96`) | **NONE** |
| `gp-0x6b94` | 3 | 4 | **yes** `gp-0x4ce0` |
| `gp-0x6b98` | 4 | 29 | **yes** `gp-0x4ce2` |

`gp-0x6b08` = `0xFEDF8000 − 0x6B08` = **`0xFEDF14F8`**. All three accesses are inside `FUN_00042af8`
(`0x42af8-0x43e43`), which runs from `FUN_0002214a` under the `0xd30` state mask ⇒ **1 kHz**.
Encodings: `st.h` = `645ff894`, `ld.h` = `245ff894`.
(The 33-hit `gp-0x6b98` count reproduces the kit's known image-wide control exactly — scan validated.)

## The write path `0x431C4`→`0x43206`, exact [EVIDENCE, disassemble_bytes dry_run]

```python
r9  = gp_6acc                                   # 0x431C4 ld.h -0x6acc,gp,r9
r7  = cal(0xC61D4)                              # 0x431C8 ld.h 0x71d4,tp,r7
r15 = cal(0xC64C8)                              # 0x431CC ld.bu 0x74c8,tp,r15   <- MODE byte
r11 = r9 if abs(r9) <= 0x2000 else 0            # 0x431D0-D8 addi 0x2000 / addi -0x4001 / cmovc
if   r15 == 1: r11 = r7                         # 0x431E6  DISCARD aggregator for a static cal
elif r15 == 2: r11 = clamp(r7 + r11, ±0x3000)   # 0x431EA-0x43204 BLEND
gp_6b08 = r11                                   # 0x43206 st.h
```
`0xC64C8` = **0x00 on stock and on V86B** ⇒ **`gp-0x6b08` is a pass-through copy of `gp-0x6acc`** with a
±8192 range gate. This confirms the constellation's `0xC64C8` mode note at the instruction level.

## 🛑 The second reader is a MONITOR, not signal path — `0x43A90`-`0x43ADE`

```python
r20 = r28 if prior_fault_flag == 0 else r11      # 0x43AA0 cmove r28,r11,r20
if abs(r20) > abs(r11) + 5:          fault = 0x10   # 0x43AB4-BA addi 0x5,r13,r8 / cmp / bh
elif abs(r11) <= 5 or abs(r20) <= 5: fault = 0      # 0x43ABC-C2
elif sign(r11) != sign(r20):         fault = 0x10   # 0x43AC4-D6
```
It enforces **|downstream| ≤ |gp-0x6b08| + 5, signs agreeing** — a "the shaper never amplifies" guard.
Consequences for any filter:
- **Attenuating BETWEEN `gp-0x6b08` and the output is SAFE** — only amplification is forbidden.
- **Attenuating `gp-0x6b08` itself risks a transient trip**, because `r28` would still carry the older,
  larger value inside the ±5 tolerance. [EVIDENCE for the arithmetic; **BELIEF** for the trip —
  depends on `r28`'s provenance at `0x43AA0`, which is **NOT resolved**. Decompile `FUN_00042af8` to
  close it before any filter build.]

The real `gp-0x6b98` store is `0x43B52` (`st.h r8,-0x6b98,gp`), guarded by a lockstep compare against
shadow `gp-0x4ce2` at `0x43B48`, with the shadow written at `0x43B56`. `r8 = r21`, **not** `r11`.

## Related
[[reference_accord_creep_damping_dead_rate_gain_max]] — the injectors this node sits downstream of.
[[reference-accord-fun456a4-gp6ad0-resolved-live-damping-no-step]] — `gp-0x6acc`'s writer.
[[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]] — why this is 1 kHz.
