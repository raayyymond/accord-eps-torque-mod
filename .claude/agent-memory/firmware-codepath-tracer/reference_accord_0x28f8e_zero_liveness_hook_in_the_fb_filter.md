---
name: reference_accord_0x28f8e_zero_liveness_hook_in_the_fb_filter
description: "0x28F8E (`mul r16,r7,r0`, f0 3f 20 02) is a ZERO-NEW-LIVENESS-CLAIM hook: the straight-line span [0x28F8E,0x28FA2) unconditionally WRITES exactly {r7,r9,r13,r14} before reading any of them, so those four are dead at the hook by the original code's own structure. It sits AFTER the +-12000 plausibility bail, so a cave's output never re-enters Honda's implausibility test and needs no clamp -- the decisive advantage over 0x28F4C. No PSW hazard, lp untouched, zero branch targets in the span (both methods)."
metadata:
  type: reference
---

Established 2026-09-13 by subagent `cavedesign` for the V292 error-feedback cave.
Full design: `docs/specs/design/DESIGN-V292-FBLP-CAVE-2026-09-13.md`.
Re-runnable proofs: `analysis-2020accord/verify/v292_cave_census.py` (20 controls),
`analysis-2020accord/verify/v292_cave_encoder_controls.py` (19 controls).

## The span

```
28F8E  mul   r16,r7,r0     f0 3f 20 02   <-- HOOK.  4 bytes, exactly a jr.
28F92  mul   r26,r9,r0     fa 4f 20 02
28F96  ld.hu 0x72e6,tp,r13 e5 6f e7 72
28F9A  sar   0xa,r7        aa 3a
28F9C  ld.hu 0x72e6,tp,r14 e5 77 e7 72
28FA0  sar   0xa,r9        aa 4a
28FA2  add   r7,r9         c7 49         <-- RETURN POINT
```

## 🛑 Why this is the cheapest hook in the function

**Straight-line, and it unconditionally WRITES `r7`, `r9`, `r13`, `r14` before reading any of them.**
So all four are dead at `0x28F8E` **by the original code's own structure** -- a cave whose register
footprint is that same set makes **zero new liveness claims**. (Restore `r13`/`r14` by replicating the
two `ld.hu` before returning; the clamp compare at `0x28FA6` needs them.)

**Never touched, and each one matters:**

| reg | why |
|---|---|
| `r25` | `0x290AC mov 0x1,r25` / `0x290C0 mov 0x0,r25`, tested `0x29A60` -- a filter bail FORCES skip 2 |
| `r1` | `0x28F74 mov 0x1,r1` -> the sentinel store `0x290D4 st.b r1,-0x3d2c[gp]` |
| `r6` | sibling filter state, `0x28F78 ld.w -0x3d34,gp,r6` |
| `r26` | `s_old`; Honda's `add r9,r26` @`0x28FA4` needs it |
| `r2`, `r10` | live via the BAIL path only (`cmp r2,r10` @`0x290C8`, `cmp lp,r10` @`0x290D2`) -- easy to miss |
| `lp` | untouched ⇒ **`jr` only, never `jarl`** |

**No PSW hazard.** First flag consumer after the return point is `ble` @`0x28FAC`, armed by `cmp
r13,r26` @`0x28FA6` -- both downstream of `0x28FA2`. `mul` sets no flags on V850E2.

**🛑 No ±12000 exposure -- the reason this beats `0x28F4C`.** Honda's plausibility BAIL at
`0x28F50`-`0x28F58` tests `r7` while `r7` still holds the raw `x`. `0x28F8E` is AFTER it, so a cave
here can never trip the sensor-implausibility bail with its own output and **needs no clamp at all**.
A cave at `0x28F4C` MUST clamp to ±12000 (see
[[reference_accord_0x28f4c_rate_operand_hook_runs_every_tick]]).

**Nothing branches into the span -- EVIDENCE, both methods.** Ghidra `get_bulk_xrefs` returns empty on
all 11 halfword addresses. A raw Format-V + Format-III scan over `[0x13000,0xC5000)` finds 25,418
distinct targets and **ZERO** in `[0x28F8E,0x28FA2)`; `0x28FA2` is not a target from elsewhere either.
Scanner positively controlled 12/12 first (BAIL 4, the three engagement skips, the function's own
`jarl` caller, six in-block `Bcond`), with the Format-V traps applied: odd targets rejected
(`prepare` collision) and `hw2` bit 0 set ⇒ load, not branch.

## Encoding controls that exist for this neighbourhood

Useful for any future cave, all verified byte-identical against Ghidra's own decode of stock `code.bin`:

| form | control address | bytes |
|---|---|---|
| `add r13,r7` | `0x17B74` | `cd 39` (pins reg1=13, reg2=7) |
| `add r7,r9` | `0x28FA2` | `c7 49` (pins reg2=9) |
| `andi 0x2,r7,r13` | `0xAD7E` | `c7 6e 02 00` (pins andi reg1=7, reg2=13) |
| `andi 0x3,r13,r10` | `0x2378` | `cd 56 03 00` (pins the andi reg1 FIELD = 13) |
| `ld.hu -0x6a98,gp,r13` | `0x1982E` | `e4 6f 69 95` (gp-base `ld.hu`; disp takes `\|1`) |
| `st.h r13,-0x3ee4,gp` | `0x19C84` | `64 6f 1c c1` (gp-base `st.h`; disp EVEN or it becomes `st.w`) |

The whole stock window `0x28F86-0x28FAB` (38 B) re-encodes byte-identically from the V289 encoder, and
the Format-V `jr` round trip passes on all **2,261** `jr` sites in the code block. ⭐ **Always run the
whole-window re-encode as the encoder's positive control** -- asserting assembled bytes against a
hard-coded literal is tautological and catches nothing.

## Flash and RAM as of V291 (C10)

* **`0xC4C00-0xC4FF0` is 1008 bytes of `0xFF` on V291** -- V289's notch cave is genuinely ABSENT from
  this base. The `0x14A` telemetry cave ends at `0xC4BD8`, so 1048 B are free from there.
  ⚠ The "868 B free at `0xC4C90`" figure in the record was read from the **V289** image; do not
  inherit it for a V291-based build.
* The 12-byte structure at `0xC4FF0` is `01 01 01 01 00 00 c6 00 13 00 b2 00`, still unidentified.
* **CRC: `[0x13000,0xC4FFC)` -> `0xC4FFC` and `[0xC6000,0xC6FFC)` -> `0xC6FFC`, both `zlib.crc32`**,
  both verified matching on V291 (`34cec426`, `ed9b12bb`). A code cave touches only the first.
* **`gp-0x6D74..gp-0x6D2D` (72 B, `0xFEDF128C..0xFEDF12D3`) re-verified FREE on the V291 image** by
  every form (4-byte, 6-byte extended, absolute LE32, `movhi`/`movea`), scanner 8/8 controlled, and its
  `.data` source (flash `0x8633C+`) is all zero ⇒ **boots to 0**. Anchor control: `gp-0x6AB0`'s source
  reads `88 02 88 02`, non-zero, so the `0xFEDF11B0 -> 0x86260` mapping is right.

⭐ **Prefer `ld.hu`/`st.h` over `ld.w`/`st.w` for a small bounded cave state.** Same 4 bytes per
access, but it caps whatever the cell could ever hold at 65535, which cannot overflow a
`mul`-plus-remainder add, where a garbage 32-bit word could. It also drops the word-alignment
constraint on the displacement.

Related: [[accord-fb-lag-filter-bytes-and-gate1-private]],
[[reference_accord_fb_filter_floor_bias_is_32_counts_of_phantom_error]],
[[reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans]].


**CORRECTION 2026-09-13 (adversary D2, ADV-V292-D-INTERLOCKS §7 F1):** r7 and r9 are LIVE-IN to the span (read by the two `mul`s before being written); only r13/r14 are written-before-read. The hook is safe because the cave replicates both `mul`s first. Do not reuse the 'writes before reading' argument at a site whose live-in operands are not replicated.
