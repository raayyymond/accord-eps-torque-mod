---
name: accord-0x2a0c6-is-a-damper-mode-and-data-boot-values
description: 0x2A0C6 is NOT "SKIP 3"/a reset — it is a second, feedback-only viscous-damper MODE gated by gp-0x680a, which is UNREACHABLE (zero writers, boots 0); plus the .data copy loop 0x1476C-0x14794 that turns every "boot value" BELIEF in this kit into EVIDENCE
metadata:
  type: reference
---

## 1. `0x2A0C6` is a second delivery MODE, not a reset

The record (`TRACE-2026-09-13-fb-lag-filter-bytes` §6, and the V290-era traces) calls
`0x29A70 jr 0x2A0C6` **"SKIP 3"** and describes the target as a register-reset route. **It is a second
LKAS delivery lane: a pure viscous damper on the wheel rate with no command term at all.**

`disassemble_bytes(0x2A0C6, 64, dry_run:true)` on `code.bin`:

```
2A0C6  mov   0x0,r24
2A0C8  cmp   r0,r26              sign of the clamped feedback
2A0CA  ld.hu -0x6a34,gp,r8       |fb>>5|, published at 0x290CA
2A0CE  mov   0x1,r12
2A0D0  ld.hu 0x7712,tp,r9        X_min = [0xC6712] = 64
2A0D4  cmovlt -0x1,r12,r12       r12 = sign(fb)
2A0D8  movea 0x7710,tp,r7        table base 0xC6710
2A0EA  mov   0x7fffffff,r16      E_prev := the poison sentinel
2A0F4  ld.hu 0x7722,tp,r10       Y[0] = 608 (below-range)
       LERP  X [65,67,73,80,88,96,104] -> Y [608,704,704,832,832,832,832,832]
       output = -sign(fb) * LERP(|fb>>5|)   -> joins the chain at the 0xC61BE sum clamp
```

It bypasses P, I and D entirely. The table `0xC6710..0xC6730` is identical on stock, V282 and V292.

## 2. It CANNOT RUN — `gp-0x680a` has zero writers and boots to 0

| method | result |
|---|---|
| Ghidra `search_instructions(operand_pattern="-0x680a")` | 2 matches, both `ld.bu`: `0x29A68` (live) and `0x2A96A` (the dead twin `FUN_0002a93a`). Zero writers. |
| raw Python two-encoding gp scan, 8/8 controls PASS | 2 accesses, both `ld.bu`. Zero writers, any encoding. |
| `.data` boot value | flash `0x868A6` = `00` (see §3) |

⇒ `gp-0x680a ≡ 0` for the life of the ECU. **Residual:** a register-indirect `st.b` would not appear in
an operand scan, so this is strong but not airtight. Consequence: `gp-0x6a34` (`|fb>>5|`, written at
`0x290CA`) has **no live consumer**, which is why muting the feedback cannot break this lane.

## 3. ⭐ THE `.data` COPY LOOP — the general method

`disassemble_bytes(0x14750, 80, dry_run:true)`:

```
00014766  mov   0xfedf11b0, ep          RAM destination base
0001475c  mov   0x86260, r14            FLASH source base
0001476c  ld.w 0x0,r14,r8 / sst.w ...   4 words per iteration
00014786  mov   0x8ab18, r10            FLASH END
00014792  cmp r10,r14 ; 00014794 bc 0x1476c
```

⇒ **`.data` = flash `[0x86260, 0x8AB18)` → RAM `[0xFEDF11B0, 0xFEDF5A68)`, 18,616 bytes.**

```python
def data_source(gp_disp):                      # gp = 0xFEDF8000
    ram = 0xFEDF8000 + gp_disp                 # gp_disp is negative
    assert 0xFEDF11B0 <= ram < 0xFEDF5A68, "outside .data - no initialiser"
    return 0x86260 + (ram - 0xFEDF11B0)
```

**Positive control (always use it):** `gp-0x6AB0` → flash `0x86600` reads `88 02 88 02`, the known
non-zero cell that falsified an earlier "free RAM" claim.

Values this settles, all previously **BELIEF** in the record:

| cell | RAM | flash | bytes | consequence |
|---|---|---|---|---|
| `gp-0x3d30` fb filter state | `0xFEDF42D0` | `0x89380` | `00 00 00 00` | boots 0 |
| `gp-0x3d2c` sentinel | `0xFEDF42D4` | `0x89384` | `00` | boots 0 ≠ 1 ⇒ `s := 0` on the first tick. **Closes `TRACE-2026-09-13-fb-lag-filter-bytes` §5.4 and `DESIGN-V292-FBLP-CAVE` §8.2.** |
| `gp-0x680a` | `0xFEDF17F6` | `0x868A6` | `00` | the damper mode is unreachable |
| `gp-0x6D74/72/70` | `0xFEDF128C/8E/90` | `0x8633C/3E/40` | `00 00` | the V292 cave's cells, plus one more free halfword |

See [[accord-lkas-pid-pid-register-map-and-taper]] and
[[accord-v279-is-the-built-never-flown-torque-mode]].
