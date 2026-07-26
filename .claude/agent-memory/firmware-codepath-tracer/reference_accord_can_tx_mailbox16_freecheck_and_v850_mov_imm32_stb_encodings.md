---
name: reference_accord_can_tx_mailbox16_freecheck_and_v850_mov_imm32_stb_encodings
description: Independent re-confirmation that FCN0 mailbox 16 is unclaimed (three converging methods), a byte-verified cross-check of FUN_0001d68e's TX-arm strobe sequence, and two freshly-derived V850E2 instruction encodings (MOV imm32,reg and ST.B disp16) not previously in domain memory — assembled for a proposed new-CAN-ID (0x555) code-cave test build.
metadata:
  type: reference
---

# Mailbox 16 free-check + FUN_0001d68e cross-check + 2 new V850E2 encodings (2026-07-23)

Traced on `code.bin` (stock) via GhidraMCP disassembly (not decompiler C — the decompiler's pointer-cast
reinterpretation of `FUN_0001cf30`'s loop made the mailbox-index bounds ambiguous; raw disasm resolved it
byte-exact). Done in support of a proposed (not yet built) study-artifact cave that fires a fixed 8-byte
payload on a new CAN ID 0x555 via FCN0 hardware mailbox 16, extending
[[reference_accord_can_tx_full_table_decode_and_new_id_recipe]].

## Mailbox 16 free — CONFIRMED, three independent methods

1. **Raw disasm of the boot-init bare-ization loop**, `FUN_0001cf30` @`0x1d190`-`0x1d1c0`: entry `mov
   0x7,r28` @`0x1d164`, per-iteration `st.b r0, 0x24, r10` (bytes `4a 07 24 00`, i.e. STRB(mbx)=0), exit
   test `addi -0x21,r28,r0; bc` @`0x1d1a8/1d1b0` (carry-exits once r28==0x21=33). **Loop covers mailbox
   index 7 through 32 inclusive** — mailbox 16 is inside it and gets STRB=0 (neither RX nor TX armed) at
   boot, never touched again. This directly resolves
   [[reference_accord_can_tx_full_table_decode_and_new_id_recipe]]'s open "not yet checked: whether 7-63
   are RX-configured elsewhere" for mailbox 16 specifically: no, it's driven to disabled.
2. **Zero xrefs, all four mailbox-16 register addresses**, code.bin whole-program: `get_xrefs_to` on
   `0xff481424`(STRB16), `0xff491428`(MID0W16), `0xff489438`(CTL16), `0xff481400`(DAT0B16) all returned
   "No references found."
3. **Full 18-slot routing table** (`0xb7208`, decoded in the linked recipe memory) uses only mailbox
   values {0,1,2,3,4,5,6} across all 18 logical slots — 16 never appears.

Per the domain's null-result caveat (a bare `get_xrefs_to` zero on a tp/gp-relative or computed address
has been misleading before on this program) — method 1 is the load-bearing one here since it's a positive
byte-level observation (a specific STRB=0 write at a known PC covering mbx16), not an absence claim; methods
2-3 corroborate rather than carry the finding alone.

## FUN_0001d68e TX-arm strobe — byte-verified, matches the documented recipe exactly

Disassembled `0x1d68e` in full (not decompiled). TX-arm tail:
```
0001d7ee: movea 0x100,r0,r7
0001d7f2: st.h r7,0x8038[r27]      ; CTL(mbx) = 0x0100
0001d7f8: movea 0x200,r0,r15
0001d7fc: st.h r15,0x8038[r27]     ; CTL(mbx) = 0x0200
```
`r27 = DAT0B_base(mbx) = 0xff481000+mbx*0x40`; displacement `0x8038` added to it lands exactly on
`0xff489038+mbx*0x40` = CTL(mbx) — confirms the register math AND confirms this disp16 store form adds the
displacement as a plain unsigned 16-bit quantity here (bit15 of `0x8038` is set; sign-extension would give
the wrong address, so it is NOT sign-extended in this context).

Payload path `0x1d77c`-`0x1d7ba` writes DAT0..7B via `sst.b` at offsets `0x0,0x4,0x8,0xC,0x10,0x14,0x18,0x1c`
from the DAT0B base — **DAT0..7B are 4 bytes apart** (matches `0xFF481400,04,08,0C,10,14,18,1C` for mbx16).
Wrapped in `di`/`ei`.

**⚠ Do NOT copy the MID0W write pattern**: `st.w r13,0x10028[r28]` uses a displacement (`0x10028`) that
exceeds 16 bits — some extended/multi-word V850E2 addressing form, not decoded here. Build the MID0W
absolute address directly (see below) instead of mirroring this specific instruction.

## Two V850E2 encodings newly derived this session (not in [[reference-accord-v48b-freeram-and-v850-encoding-formulas]])

**MOV imm32,reg (48-bit/6-byte, V850E2-native format 12).** This is the form real code uses pervasively
in `FUN_0001cf30`/`FUN_0001d68e` to build every FCN0 absolute address. Derived + cross-checked against 6
register variants × 3 immediate values (18 real instances, `search_instructions`):
```
halfword1 (LE) = 0x0620 | reg        # byte0 = 0x20|reg, byte1 = 0x06
halfword2 (LE) = imm32 & 0xFFFF      # low 16, literal, NOT sign-extended
halfword3 (LE) = (imm32 >> 16) & 0xFFFF
```
Example: `mov 0xff481000,r14` → bytes `2e 06 00 10 48 ff`. Preferred over movhi+movea for constructing FCN0
register addresses: one instruction, no sign-extension trap (unlike movea, whose 16-bit field IS
sign-extended — e.g. `0xFF489438`'s low half `0x9438` has bit15 set, so a movhi+movea route needs
`movhi 0xFF49` not `0xFF48`; MOV imm32 sidesteps this).

**ST.B disp16 (4-byte).** Existing domain memory had LD.H/LD.W=0x39, ST.H/ST.W=0x3B, LD.BU=0x3C but not
ST.B. Derived from 8 real instances in `FUN_0001cf30` (includes the mailbox-16 STRB-zeroing instruction
itself):
```
halfword1 = (src_reg<<11) | (0x3A<<5) | base_reg
halfword2 = disp16 (raw)
```
Cross-checked exactly against 3 independent src/base combinations (r0/r10, r6/r10, r12/r14). `0x3A` fits
neatly between the existing LD.H/W=0x39 and ST.H/W=0x3B — a plausible contiguous opcode block worth
checking if a 4th opcode (LD.B, non-unsigned) is ever needed.

## Recommendation for the (unbuilt) mailbox-16 cave

Build each of STRB16/DTLGB16/MID0W16/DAT0..7B16/CTL16's absolute address via MOV imm32,reg (verified
above), then a plain disp0 st.b/st.h/st.w — avoids both the movea sign-extension trap and FUN_0001d68e's
unresolved extended-disp MID0W trick. Fire with CTL=0x0100 then CTL=0x0200 (byte-verified identical to the
real emitter). This was handed to `team-lead` for the actual build (out of scope for this read-only trace) —
see the session's mailbox-16 build-prep ask.

## Related
[[reference_accord_can_tx_full_table_decode_and_new_id_recipe]] — the new-ID recipe this session's checks
support; resolves one of its stated residuals (mailbox-16-specific RX-configuration check).
[[reference-accord-v48b-freeram-and-v850-encoding-formulas]] — the existing encoding-formula bank this
session adds two entries to (MOV imm32, ST.B).
