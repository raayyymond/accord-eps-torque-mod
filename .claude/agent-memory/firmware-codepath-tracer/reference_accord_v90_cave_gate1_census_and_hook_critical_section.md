---
name: reference-accord-v90-cave-gate1-census-and-hook-critical-section
description: Completed GATE-1 census of the cave's write target gp-0x1514 (Ghidra MISSES two register-indirect clr1 writers); the 0x55C0E hook site sits INSIDE Honda's own di/ei critical section; the cave magnitude idiom can only express power-of-two thresholds; two-threshold rungs must derive from ONE load or they tear.
metadata:
  type: reference
---

# Cave GATE-1 census, the hook's free critical section, and the threshold constraint

Measured 2026-08-10 while specifying V90's cave. Stock `code.bin` + the V89 plain image.
Extends [[reference_accord_crc_block_lookup_and_cave_hook_template]] — that file has the hook encoder
and the epilogue; this one has the RAM census and three structural constraints it did not record.

## 🛑 `gp-0x1514` — Ghidra's `search_instructions` MISSES two live writers

Complete census of the cave's only write target (`gp-0x1514 = 0xFEDF6AEC`, `0x14A` byte 4):

| method | hits |
|---|---|
| Python 4-byte Format VII | 8 |
| Python 6-byte extended-displacement | 0 |
| Python `movhi 0xFEDF` register-indirect (opcode + 96-B locality filtered) | **2** |
| Ghidra `search_instructions` operand `1514` | 8 (+2 branch-target text FPs) |

**Set-difference: Ghidra missed BOTH register-indirect writers.**

```
00055b1c: movhi -0x121,r0,r18        ; 0xFEDF
00055b20: clr1  0x1,0x6aec[r18]      ; = gp-0x1514, bit 1
00055b2c: movhi -0x121,r0,r18
00055b30: clr1  0x0,0x6aec[r18]      ; = gp-0x1514, bit 0
```

Their operand text is `0x6aec, r18` — **the string `1514` never appears**, so no operand-pattern search
can ever find them. Add the `movhi 0xFEDF,r0,rN` + `disp[rN]` form as a THIRD scan form to every
GATE-1 census, alongside the two documented gp-relative encodings.

⚠ A naive version of that third scan (no opcode filter, no locality window) returned **11 and 31** raw
hits on `gp-0x1514`/`gp-0x6c00`; the surplus were halfword coincidences inside the LERP/cal data region
(`0xD0936`, `0xD2936`, …). **Filter by opcode field and require the `movhi` within ~96 bytes.**

**Verdict on the free bits [EVIDENCE, 3 encodings, 2 tools]:** no Honda code sets or clears bits 7:3 of
`gp-0x1514`. The three `st.b` writers mask `0xfb`/`0xfd`/`0xfe` (bits 2/1/0 only); the two `clr1`s hit
bits 1/0. The one that needed checking is `FUN_0002193e`, a **32-bit** RMW straddling the byte:
`*(uint*)(gp-0x1514) = *(uint*)(gp-0x1514) & 0xff0000ff | (byteswap16(arg) << 8)` — little-endian, mask
bits 7:0 map to `gp-0x1514`, and they are `0xff` ⇒ **byte 4 preserved in full**; it writes bytes 5 and 6.

## ★★ The `0x55C0E` hook site is already INSIDE a `di`/`ei` critical section — for free

```
00055c0a: jarl 0x0001fa42,lp     ; FUN_0001fa42 = nesting counter @gp-0x163c + `di`
00055c0e: movea -0x1518,gp,r6    ; <-- THE HOOK
00055c18: jarl 0x00057b24,lp     ; FUN_00057b24(buf=gp-0x1518, len=8, id=0x14A)
00055c2e: jarl 0x0001fa72,lp     ; FUN_0001fa72 = decrement + `ei` at zero
```

The cave's read-modify-write of `gp-0x1514` is **not** wrapped in the `fa42`/`fa72` pair — and
structurally cannot be, since a `jarl` would destroy the `lp` it returns through — **but it does not
need to be: it executes inside Honda's own bracket.** This is a property of *this* hook site and does
**not** transfer to a new one; check it before reusing the template elsewhere. Corollary: a cave here
lengthens that critical section, so interrupt latency is the cost metric, not tick budget.

The same call proves the byte map from the call site rather than a table: payload base `gp-0x1518`,
length 8 ⇒ **`gp-0x1514` IS `0x14A` byte 4**, `gp-0x1511` is byte 7.

## 🛑🛑 MY OWN DEFECT: a cave payload emitted BIG-endian, and a silent check that hid it

I generated a payload with `bytes.fromhex("3a00")` for the halfword **value** `0x3A00`. That emits
`3a 00`; **V850 needs `00 3a`.** Every 2-byte instruction in that payload was byte-swapped; the 4-byte
entries, copied from real byte dumps, were fine — so the string looked plausible. It reached the
orchestrator before I caught it.

🛑 **What caught it was a branch-target validator printing NOTHING.** With bytes reversed, `ae05` parses
as `05ae`, opcode field `0xC` instead of `0xB`, so no instruction matched the branch filter and the loop
printed zero lines. **A check that produces no output is not a check that passed.**

**Two rules from this:**
1. **Never write an instruction as a hex string of its halfword VALUE.** Use an explicit
   `LE(hw) = bytes([hw & 0xFF, hw >> 8])`, or copy the byte sequence verbatim from the image / from
   Ghidra's `bytes` field (which is already in byte order). Mixing the two conventions in one table is
   how this happened.
2. **Every validator must ASSERT a boolean, never merely print.** Silence must be impossible to mistake
   for success.
⊕ Cross-check that costs nothing: assert each shared halfword against V89's flown cave bytes, and assert
every branch target lands on a known instruction offset.

## ★★ `subr r0,rN` buys TRUE `|x|` for 2 bytes — and it is `8031`, NOT `3080`

🛑 **I hand-derived `subr` as opcode `0x04` ⇒ `3080`. WRONG — `0x04` is `satsubr`; `subr` is `0x0C` ⇒
`8031`** (Ghidra `search_instructions mnemonic=subr operand="r0, r6"`, twin `0x2A150`). A `satsubr` would
have silently **saturated instead of negating**. Caught only because the kit's rule is *never ship a
halfword without a verified twin*. **Verified twins for the forms a cave needs:** `3180` `subr r0,r6`
@`0x2A150` · `05be` `bge +6` @`0x48C2`→`0x48C8` · `3266` `cmp 0x6,r6` @`0x159F6` · `2437 da94`
`ld.h -0x6b26[gp],r6` @`0x3815C` (all four bytes).

**Placing `subr r0,r6` inside the existing sign branch turns every later magnitude test into a plain
unsigned `cmp imm5 ; bnh` on `q = |x|>>6`.** That is strictly better than the `sar/+1/cmp/bnh` idiom:
exact on both signs (the old one fires at `x ≥ T ∨ x ≤ −(T+1)`), no undo, no re-load, and it makes a
3-level thermometer *cheaper* than two thresholds were — 58 B / 24 instr vs 68 B / 28 instr.

## 🛑 The OLD magnitude idiom can ONLY express power-of-two thresholds (superseded by `subr`)

`sar N ; add 1 ; cmp 1 ; bnh(UNSIGNED)` is an abs-free magnitude test that works *only* because every
`|x| < 2^N` maps to `w ∈ {0,1}`. Attempt a non-power-of-two (e.g. 192 via `sar 6 ; cmp 4`) and the band
`x ∈ [-192,-129]` yields `w ∈ {-2,-1}` = unsigned-huge ⇒ **fires wrongly**. Reachable thresholds are
**32 / 64 / 128 / 256**, one byte each (`0xA0 | shift`). Useful: it makes the threshold a single-byte
lever, which is how V89 retuned 256 → 64.

## 🛑 Two magnitude rungs on one signal MUST derive from ONE load

`gp-0x6b26`'s writer runs at 1 kHz in a different task from the 100 Hz CAN-TX task the cave lives in.
Two separate `ld.h` of the same cell can straddle a writer update and break the nesting invariant
(`b_hi=1, b_lo=0`), which is exactly the codeword a build discriminator relies on. Load once and derive:
`sar 6` → test → `add -1 ; sar 1` (= `x>>7`) → test. Nesting is then true by construction.

## ★★ Reclaiming a RAILED bit is the strongest single-frame build discriminator available

[EVIDENCE, `FlightV89`, 254,085 frames across V87/r71, V88/r73, V89/r75, V89/r76] **The 5-bit support is
IDENTICAL on V86B/V87/V88/V89 — `{3,7,15,23,31}` — so support alone CANNOT discriminate them.** Cause:
on all four, `b4` (`gp-0x67ab <u 2`) is railed at **exactly 1.0000**, and the three payload bits obey
`b6 ⇒ b5` and `b7 ⇒ b5` because all three read one cell.

⇒ **Break BOTH relations and the support moves.** A magnitude thermometer (`b4 ⊂ b5 ⊂ b6`) plus a rung
on the reclaimed b4 gives `{1,9,13,15,17,25,29,31}` — **six codewords structurally impossible on every
build since V86B, and `b4 == 0` alone is decisive**: impossible on 254k measured frames, common case on
the new build. **One frame, no thresholds, no duties, no control route, no reference cache.**

**Generalise: a rung measured at duty 1.0000 is not merely wasted — reclaiming it is worth more than the
signal you put on it, because it moves the alphabet.** Distribution-based identity (V89 was settled by
value 3 running 0.20 % → 59.45 %, a ~250× shift) needs a control build; support-based identity does not.

## Twins for the four halfwords V89's cave does not already contain

| halfword | instruction | verbatim twin in shipped code |
|---|---|---|
| `2437 da94` | `ld.h -0x6b26[gp],r6` | **`0x3815C`** — all four bytes, same dest register |
| `0094` | disp `-0x6c00` | `0x3BC16` = `644f 0094` |
| `5f32` | `add -0x1,r6` | `0x1545E`, `0x0C4E4`, `0x16900`, `0x17698` |
| `a132` | `sar 0x1,r6` | `0x1A89E`, `0x1A990`, `0x1AF94`, `0x298B8` |

## Cave occupancy update

V89 = **62 bytes**, free from `0xC4B72`. Empty-cave figure remains **1212 bytes at `0xC4B34`**
(free run to `0xC4FF0`). 68 bytes is a previously-flown extent (V72/V81/V85).

## CAN-side notes worth not re-deriving

- The `0x14A` checksum is computed inside `FUN_00057b24`, called at `0x55C18` — **after** the cave's
  write ⇒ spare bits auto-covered.
- **The FOURFRAME `STRB`/`SSAM` defect cannot recur in this cave class.** That bug was in a cave that
  *originated a frame* and had to set the message-control bits itself. This template touches **no CAN
  peripheral register** — it edits one RAM byte in a buffer Honda's own code transmits.

Related: [[reference_accord_fun3b8f6_gatefail_stale_and_gp6c00_exact_flag]],
[[reference_accord_gate1_movea_gp_array_blindspot_and_scalar_bound]],
[[reference_v850_gp_relative_opcode_field_map_validated]].
