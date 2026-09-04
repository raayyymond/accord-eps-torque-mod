---
name: reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site
description: FUN_00028ea6 reuses lp as a general-purpose scratch register mid-body (loaded at 0x28EBC and 0x29A2C, live across long windows including 0x29EE4) — a jarl inserted anywhere lp is live corrupts a real Honda gate comparison at 1kHz. 0x29EE4 (mul r7,r8,r0, dE*Kd, exactly 4 bytes) is a same-length jr swap site with r10 provably dead across it, and 0xC4BD8 onward has 168+ bytes of free flash immediately after the existing cave for a new subroutine.
metadata:
  type: reference
---

# `FUN_00028ea6`: `lp` is reused as scratch (jarl-unsafe mid-body), and `0x29EE4` is a clean same-length `jr` insertion site

2026-09-04, subagent `telem285`, V282 image, `search_instructions` + `disassemble_bytes dry_run:true`.
Produced while costing a `dE`-sign-change instrument for `team-lead`; recorded because the trap (`lp`
reuse) and the insertion technique (same-length opcode swap) both generalise to any future edit
INSIDE this function's body — a materially different, higher-risk class of edit than the CAN-packer
caves this kit has flown since V29 (those add a call without displacing anything).

## 🛑 `lp` is not safely available as a link register mid-body

`FUN_00028ea6`'s prologue (`prepare {...,lp}, 0x1`) saves the real caller return address — but the
body then repeatedly RE-USES `lp` as ordinary scratch:

```
0x28EBC  ld.hu 0x72ea, tp, lp      ; lp <- a cal value, consumed at 0x290D2 (cmp lp,r10)
0x2913E  jarl  0x46ea6, lp         ; lp <- return addr for an internal call (short-lived)
0x291CA  jarl  0x16de6, lp         ; same pattern again
0x2975A / 0x29808 / 0x29964        ; ld.bu -0x6809,gp,lp ; cmp 0x1,lp  (paired, short-lived, x3)
0x29A2C  ld.bu -0x6809, gp, lp     ; lp <- a Honda gate byte
0x2A29A  cmp   0x1, lp             ; <- NOT consumed until here — 0x86E bytes later
```

**`lp` is live from `0x29A2C` to `0x2A29A` with NO intervening reload — a window that fully contains
`0x29EE4`.** A `jarl` anywhere in `[0x29A2C, 0x2A29A)` destroys a live Honda gate comparison that
fires every 1 kHz tick while the PID runs. This is a real, confirmed collision (not a hypothetical
near-miss) — caught by `team-lead` from the prologue's `prepare` list and independently re-traced
end-to-end by me via `search_instructions operand_pattern:"lp" function:FUN_00028ea6`.

⇒ **Any call-out inserted inside this function's body must use `jr`, never `jarl`, unless `lp`'s
liveness at that EXACT point has been traced clean.** Given the density of `lp` reuse shown above,
assume it is live until proven otherwise.

## The insertion site: `0x29EE4`, a same-length swap

```
0x29EE0  mov r16, r8       ; r8 = current E
0x29EE2  sub r27, r8       ; r8 = dE = E - E_prev   (dE fully formed, unclobbered)
0x29EE4  mul r7, r8, r0    ; r8 = dE * Kd  (4 bytes — exactly a jr's length)
0x29EE8  ld.hu 0x71b6, tp, r10   ; unconditionally overwrites r10
```

**Replace `0x29EE4`'s 4-byte `mul` with a 4-byte `jr <subroutine>` — same length, no relink, no
downstream address shift.** `r10` is provably dead on entry to the subroutine (the very next
instruction after the resume point clobbers it unconditionally) — a liveness claim read directly off
the bytes, not inferred. `dE`'s sign is available in `r8` at subroutine entry (the `mul` hasn't run
yet); the subroutine must replay `mul r7,r8,r0` itself before `jr`-ing back to `0x29EE8`, since
downstream code needs the real `D` value.

`jr disp22` range from `0x29EE4` covers the existing cave trivially (`0xC4BD8 − 0x29EE4 ≈ 0x9AF34`,
~620 KB, well inside `jr`'s ±2 MB).

## Free flash for the subroutine: `0xC4BD8` onward, 168+ bytes

Raw byte read of the V282 image: the existing cave's real code ends at `0xC4BD8` (`7f00` = `jmp lp`,
the cave's own return). Every byte from `0xC4BD8` through at least `0xC4C7F` is `0xFF` (erased flash,
unused) — checked directly, not inferred from a footprint size in a memory. This is inside the same
`[0x013000, 0xC4FFC)` CRC-covered app-code block every other V282 edit already sits in, so no new
CRC-block class of risk, only the existing block's trailer needs recomputing same as any edit there.

## Scratch RAM: `gp-0x683c` — zero references of ANY kind, not just zero writers

`search_instructions operand_pattern:"0x683c"` image-wide: **zero matches**, stronger than the prior
"Lever B unreachable" finding (which only established zero writers). Checked neighbours `-0x683b`
and `-0x683d` for a word-packing overlap risk: both are live and accessed **exclusively** via
`st.b`/`ld.bu` — this whole region is byte-granular, so `gp-0x683c` sitting between two
independently byte-addressed neighbours is good evidence it's a standalone byte cell, not a fragment
of a larger packed field. One byte comfortably holds a 1-bit "last sign" + 2-bit saturating counter.

## What's still open

The 1 kHz task's actual cycle-budget headroom for ~15-20 extra cycles per tick — estimated small,
not measured. `team-lead`'s explicit standing instruction: do not let a small estimate substitute
for the measurement; this is the kit's only bricking class.
