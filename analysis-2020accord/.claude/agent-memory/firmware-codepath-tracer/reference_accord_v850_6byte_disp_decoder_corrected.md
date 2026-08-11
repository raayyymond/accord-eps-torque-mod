---
name: reference-accord-v850-6byte-disp-decoder-corrected
description: The 6-byte extended-displacement formula's halfword indices are off by one as commonly applied - hw1/hw2 mean the SECOND and THIRD halfwords, not the first two. Includes a validated decoder, and proof that neither Ghidra nor Python alone enumerates this image completely.
metadata:
  type: reference
---

Derived and validated 2026-08-10 on stock `code.bin`. **This corrects how this kit has been applying an
existing memory**, not the memory's algebra.

## The trap

`accord-gp4f60-two-encodings-enumeration-trap` states
`disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7F)`.
Applied to the **first two halfwords** of the 6-byte instruction this yields garbage, and a scan built that
way returns **clean-looking zeros**. I reported one such false null on 2026-08-10 and had to retract it.

`hw1`/`hw2` in that formula mean the **SECOND and THIRD** halfwords:

```python
# 6-byte gp/tp-relative load/store:  [hw0 = opcode+base]  [hw1]  [hw2]
disp  = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F)
base  =  hw0 & 0x1F            # 4 = gp, 5 = tp
opc   = (hw0 >> 5) & 0x3F      # 0x3C and 0x3D observed in this image
```

**Worked example** — `0x59bfa` = `ld.h -0x4f60[gp],r6`, bytes `84 07 07 32 61 ff`:
hw0=`0x0784`, hw1=`0x3207`, hw2=`0xff61` -> `(sext16(0xff61)<<7) | ((0x3207>>4)&0x7F)`
= `(-159<<7) | 0x20` = `-20352 + 32` = **-0x4F60**. OK

🛑 The base register is in **hw0**, and it is **4** for gp — not 0. A filter of `hw0 & 0x1F == 0` silently
returns zero hits for everything.

## Validation

The corrected scanner reproduces **all 7** of Ghidra's 6-byte `gp-0x4f60` hits at the same addresses
(`0x4c784` `FUN_0004c780`; `0x59bfa/0x59c02/0x59c44/0x59c4c` `FUN_00059912`; `0x5a0bc/0x5a0c4`
`FUN_00059e7a`), and finds **12 six-byte accesses to `gp-0x6b98`** at `0x59a44`-`0x5a0aa` (the CAN
telemetry packer band) that a 4-byte-only scan misses entirely.

Re-run with the corrected decoder, these stay at **0** six-byte hits: `gp-0x6ade`, `gp-0x6b4c`, `gp-0x6b4e`,
`gp-0x6b46`, `gp-0x6b70`, `gp-0x6bfa`, `gp-0x3d90`, `gp-0x6afe`, and tp-side `0xC40D4`, `0xC40D8`,
`0xC63AC`, `0xC4048/4C/50`, `0xC646E`, `0xC6468`, `0xC40D2`, `0xC4080`.

## 🛑 NEITHER TOOL ALONE IS COMPLETE ON THIS IMAGE

Enumerating `gp-0x4f60` three ways, 2026-08-10:

| method | count | what it uniquely sees |
|---|---|---|
| Ghidra `search_instructions -0x4f60` | 73 (`truncated:false`, `instructions_scanned: 183570`) | the **7 six-byte** accesses |
| Python 4-byte Format-VII scan | 69 | **3** Ghidra cannot see |
| union, adjudicated | **>=76** | — |

The 3 Python-only hits are `0x2d9a2`, `0x2dae6` (`hw1=0x3724 hw2=0xb0a0`) and `0x4f996` (`hw1=0x4f24`), all
decoding as valid `ld.h -0x4f60[gp]`. **`get_function_by_address` returns "No function found" for all
three** => they sit in **unanalysed regions**, which `search_instructions` cannot scan while still
reporting `truncated:false` (183,570 scanned against the ~185,693 the kit records).

⇒ **A load-bearing enumeration needs BOTH methods, with the set difference adjudicated address by address
and each residual hit given a stated reason.** Ghidra sees the second encoding; Python sees the
unanalysed regions.

Related: [[reference-accord-observer-filter-mismatch-leaks-the-command]],
[[reference-accord-assist-channel-framework-lkas-is-channel1]].

## Companion trap, hit in the SAME session: compute `tp+off` IN CODE, never by eye

2026-08-10: I reported a gate cal as `0xC50EE` = 136 when the instruction was `ld.bu 0x50ee[tp]` and
`tp = 0xBF000` gives **`0xC40EE`** = `0x00`. **Sixth recurrence of the off-by-0x1000 trap.** The conclusion
happened to survive (the branch tests `== 0xE9` and neither 136 nor 0 is 0xE9), but the address handed to
another agent was wrong and had to be retracted.

The difference between the two passes was purely mechanical: the wrong one **typed** the address into
prose, the right one **computed** `tp+off` inside the scan script and printed it. `tp+0x5000` is
`0xC4000` and `tp+0x7000` is `0xC6000` — one hex digit apart in the offset, a *different* digit apart in
the result, which is exactly why eyeballing fails and why the trap keeps recurring.

⇒ **Rule: every tp-relative address in a report must come from a line of code that computed it, and the
script should print `hex(tp+off)` beside the value it read.** Same for gp.

## Third trap, same session: do NOT append markdown to a file via a bash heredoc or a `python -c` string

Backticked spans are eaten as command substitution and the file lands silently mangled — every
`` `code` `` span in this very section was destroyed on the first attempt, and the verification
`print('ok', 'Companion trap' in s)` returned **True** against the mangled text, so the check passed while
the content was wrong. **Use the Write/Edit tools for prose, and reserve Bash for computation.** Also note
`python -c` printing to a Windows console dies on non-ASCII (`cp1252` cannot encode `⇒`) — use the Read
tool to inspect a file, not a Python print.
