---
name: accord-v850-scan-traps-formatv-and-storezero
description: "Eight byte-scan/method traps on the V850E2 A160 that each produced a confident wrong answer — Format-V jr/jarl aliasing ld.bu (44% false positives), store-zero filtering, ld.bu/ld.hu disp|1, compare-then-store shape, LERP-vs-(lo,hi), external-readers sweeps, Ghidra false-dead, and search_instructions returning a tool zero for an unanalysed region (the tp initialiser)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 999fba26-ffc6-4a2f-9832-a51b221c590a
  modified: 2026-07-25T07:32:28.847Z
---

# Eight scan traps, each of which produced a confident wrong answer (2026-07-24/25, +1 2026-08-13)

Every one of these was hit **in session**, by the lead or a subagent, and each produced a well-evidenced
conclusion that was flatly wrong. Check a scan against all eight before trusting a count or an "absent".

**1. ★ Format-V `jr`/`jarl` ALIASES `ld.bu`.** Both use opcode field `0x3C` (`hw1` bits 10..6 = `0b11110`).
They are distinguished **only by `hw2` bit 0**: `hw2 & 1` ⇒ `ld.bu`, else branch. Omitting that test gave
a **44% false-positive rate — 10,105 spurious call sites out of 22,850** — and manufactured a phantom
caller. Correct filter, and sanity-check `reg2 ∈ {0 (jr), 31 (jarl lp)}`:
```python
if (hw1 >> 6) & 0x1F != 0x1E: not a branch
if hw2 & 1:                   ld.bu, not a branch
disp = ((hw1 & 0x3F) << 16) | hw2      # sign-extend bit 21
```

**2. Filtering `reg2 == 0` drops every store-of-zero.** For stores `reg2` is the SOURCE register, so
`st.b r0, disp16[gp]` is the `var = 0` idiom. Skip `reg2 == 0` only for loads (`0x38`/`0x39`/`0x3C`-`0x3F`);
**keep it for stores (`0x3A`/`0x3B`)**. ⚠ `st.b r0, disp16[gp]` and the 6-byte extended escape have
**byte-identical `hw1`** (both `0x0744` for op `0x3A` on gp) — only the opcode class separates them.
This hid 3 of 5 writers of one variable and 8 of 16 of another.

**3. `ld.bu`/`ld.hu` encode `hw2 = (disp | 1)`.** `ld.bu` = subop `0x3C`/`0x3D` (address LSB in the subop's
low bit); `ld.hu` = `0x3E`/`0x3F`. **Matching `hw2` against exact even displacements is blind to every byte
load** — which is exactly how a CAN frame is unpacked. This produced the wholly wrong conclusion "the CAN
mailboxes are register-indirect only; zero gp-relative accesses."

**4. Never require "two-sided compare FOLLOWED BY a boolean store."** An exhaustive scan of all 3137
tp-relative disp16 targets, checking every delta-2 pair within 32 bytes of a PC, concluded **no speed
window exists**. It does — the boolean lives in a register, is consumed immediately in an AND-chain, and
the only memory write is the status byte on the *failing* branch. **Search for the compare alone.**

**5. Adjacent int16 `(lo,hi)` pairs are confounded by LERP records.** Both the `0xD0xxx` bank and the tp
cal window hold `[count][X[0..n-1]][Y[0..n-1]]`, so `X[last]` sits immediately before `Y[0]` and reads like
a perfect `(lo,hi)`. Two candidates that matched *both* the expected 200 km/h and the measured ~5 km/h were
falsified this way. **Tell:** a `movea <disp>, tp, rN` table-base load shortly before the loads. Never
promote a pair without disassembling its load site.

**6. An "external readers" sweep cannot establish that a variable is report-only.** `gp-0x6807`
(STEER_STATUS) has no torque-gating reader *outside* its function — correct, and the wrong conclusion. The
load-bearing consumer is the intra-function `cmp 0x2` at `0x29382`. **Always check intra-function reads.**

**7. "Ghidra defined no function here" ≠ dead.** On `0x2d5xx-0x2dbxx`, `get_function_by_address`,
`get_assembly_context`, `disassemble_function` and `get_xrefs_to` all returned nothing for what is a **live
RTOS task**. Use the **task-control-block array at `0xBB928`, stride `0x30`, entry at `+0x08`** as a
liveness oracle — it self-validates against the two independently-known tasks `0x2214A` (1 kHz control) and
`0x22CA0` (assist shaping).

**8. `search_instructions` returned a TOOL ZERO for the `tp` initialiser — Ghidra never analysed that
region at all.** Added 2026-08-13, `builder-v100`. The boot code at `0x140C0-0x140D6` sets **both `gp`
and `tp` by the SAME idiom, four instructions apart, from the same `r1`** (`gp = 0xFEDF8000`,
`tp = 0x000BF000`) — so `tp` is exactly as constant and live as `gp`, and every tp-relative cal read
in this kit rests on that. A tool-reported zero for a region Ghidra never analysed is a **silence**,
not a **negative** — a raw Python byte scan found it immediately. Every other raw candidate near it had
to be adjudicated out individually (the hw2 half of a `jarl` disp22, or an `andi` imm16 — Format-V
aliasing, trap 1 above) before this one could be trusted as real.

**Validation harness for any new scanner:** it must reproduce (a) the **64** known `ld.h gp-0x4f60` disp16
sites, (b) the `0x2170e`/`0x21712` `ld.bu` pair, (c) the `0x28EB6`/`0x28EBC` `ld.hu` pair, and (d) 0 callers
for `FUN_0002a30e`/`FUN_0002a93a` with exactly 1 for `FUN_00028ea6`.

Reference encoding: `hw1 = (reg2<<11) | (subop<<5) | reg1`, `reg1` = 4 (gp) / 5 (tp); `gp = 0xFEDF8000`,
`tp = 0xBF000`. See [[accord-gp4f60-two-encodings-enumeration-trap]] and
[[accord-low-speed-lockout-window-c62ea]].
