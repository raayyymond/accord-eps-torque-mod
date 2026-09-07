---
name: reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return
description: GATE 1 PASSES for the LKAS output-lag poles 0xC63EC/0xC63EE on V282 - the second readers at 0x2A892/0x2A8A2 are UNREACHABLE. The decisive fact is that 0x2A504, the target of every jr from FUN_0002a30e, is `dispose ..., lp` - a RETURN - so there is no fall-through into the duplicate block's dispatch head at 0x2A508. This CLOSES the residual caveat left open by the earlier pole census. Zero branches enter the block from outside (7/7-controlled scan, all raw hits adjudicated as `prepare` prologues), and no immediate can construct 0x2A508 or 0x2A890.
metadata:
  type: reference
---

# GATE 1: the LKAS lag poles are safe to edit — the duplicate block is unreachable

Proved 2026-09-06 on the V282 image. **No Ghidra mutation whatsoever**: no `create_function`, no
labels, no rename, `save_program` NOT called. Dry-run `disassemble_bytes` plus raw Python only.

## 🛑 THE DECISIVE INSTRUCTION — and it closes a caveat this kit carried for months

```
0002a4e4  br       0x0002a504
0002a4f4  br       0x0002a504
0002a504  dispose  0x0, { r20,r22,r24,r26,r28,lp }, lp     <-- EPILOGUE + RETURN VIA lp
0002a508  ld.bu    -0x3d38, gp, r6                          <-- duplicate dispatch head
```

**`dispose imm, list, lp` pops the frame AND jumps to `lp`.** So `0x2A34C`, `0x2A368`, `0x2A384`,
`0x2A3BA`, `0x2A4E4`, `0x2A4F4` — every `jr`/`br` in `FUN_0002a30e` that the record flagged as
"landing at 0x2A504, next to the duplicate" — land on the function's **RETURN**. Control **never falls
through** from 0x2A507 into 0x2A508. Ghidra's bound (0x2A30E-0x2A507) is CORRECT here.

⇒ 🛑 **`FUN_0002a30e` being live (it writes STEER_STATUS=4 at `0x2A4EC`/`0x2A4FC`, seen on CAN 399)
tells us NOTHING about the duplicate block.** The residual caveat in
[[reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader]] — *"if FUN_0002a30e's entry
path is ever found it may enter the duplicate block too"* — is **CLOSED**. The two are unrelated.

## The convergent tail
`0x2A892`/`0x2A8A2` are entered only at **`0x2A890`**. All **19** branches image-wide targeting
`[0x2A880,0x2A8D0)` land on `0x2A890`, and **every source is inside the block** (`0x2A54E`..`0x2A878`).
So reachability reduces entirely to: is `0x2A508` entered?

## Every route into 0x2A508, closed
| route | result |
|---|---|
| fall-through | **blocked by the `dispose ..., lp` return at 0x2A504** |
| direct branch from outside | **ZERO.** 45,821 branches decoded, **7/7 positive controls PASS**; 3-4 raw hits ALL adjudicated as `prepare` prologues (see [[reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans]]) |
| backward branch from the live tail funcs `FUN_0002b422`/`FUN_0002b57a` (both really are jarl'd from the 1 kHz task at 0x22530/0x22572) | real targets are `0x25C32`, `0x1CBA6` x2, `0x27802` — **all outside and below the block** |
| `mov imm32` into the block | 1 hit, `0x5A366 mov 0x2b000,r8` -> immediately `st.w r8,0x1044,r17`, a DATA field; 0x2B000 is mid-body. **OUT** |
| aligned absolute dwords into the block | 3, all **OUT**: `0x1E4C8 = 0x2AE0B` is ODD (impossible as code); `0x5A368` is the immediate above; `0x75B78` is the byte pattern of the real instruction `addi 0x2,ep,r20` (`1ea60200`) read as a dword, Ghidra-confirmed |
| `movhi 0x0002/0x0003` + `movea 0xA508` | 7 movhi sites image-wide, **NONE** followed by that movea |
| halfword `0xA890` / `0xA892` anywhere | **ZERO occurrences** — no immediate can build the lag block's address at all |

## ⇒ VERDICT
**GATE 1 PASSES for `0xC63EC` and `0xC63EE`.** An edit changes exactly ONE output-lag filter, the live
one in `FUN_00028ea6` at `0x2A174`/`0x2A184`. **There is no second application and no `H^2`.**
With the feedback poles `0xC63E8`/`0xC63EA` already single-reader and their EMA state `gp-0x3d30`
private, **all four pole cells are cleared for a cal-only edit on GATE 1.**

**What the dead code is:** a duplicate compiled copy of the same LKAS assist/rate computation — same
cals, same nine pointer banks, same convergent lag tail, same six tail cells — differing only in
register allocation (`0x29322 ... r10 = 8457c9c2` vs `0x2A508 ... r6 = 8437c9c2`). **Not a second lane,
not a monitor, and it does not feed the motor.**

## The one thing this does NOT close
`jarl [reg]` / `jmp [reg]` Format-XI dispatch through a pointer computed at run time from something
other than an immediate. **I have no positive control for that encoding, so I ran no census and quote
no number for it.** What makes it implausible rather than merely unmeasured: neither `0xA890` nor
`0xA892` occurs anywhere in the 1 MiB image and `0x2A508` cannot be assembled by any movhi/movea pair
present, so a computed entry would still need its constant from somewhere.
**Cheapest definitive settle remains the wire tap on `gp-0x3d3c` (0xFEDF42C4): written once per tick
means dead, twice means live.**
