# 🛑 Explain firmware with Python that mirrors the decompiled arithmetic EXACTLY

**Standing operator instruction, 2026-07-28. Applies to every future session.**

When explaining what firmware does — a table lookup, a filter, a clamp, a gate, a lane — write **simple,
Python-style code that follows the arithmetic of the decompiled code exactly**, and lean on it heavily.
Do not explain in prose alone, and do not substitute a summary statistic (a corner frequency, a dB
figure, "flat to 21 Hz") for the arithmetic that produces it.

**Why:** the operator reasons about this ECU in terms of the actual integer operations — shifts, Q15/Q10
scaling, `cmov` selects, saturating vs zeroing gates. Prose hides exactly the details that decide whether
an edit is safe or does anything at all. Several expensive errors in this kit came from prose that
sounded right over arithmetic that was wrong:

- `0xC63D2` recorded as `14` (really **6**) — a 2.18 Hz corner that is actually 0.93 Hz.
- The off-by-`0x1000` tp slips (four occurrences).
- **"mute `0xC6AF0`"** used as shorthand for an edit that actually writes `0xC6AFC`/`0xC6AFE` — writing
  `0xC6AF0` would clobber the table's point-count word.

## How to apply

```python
# GOOD -- mirrors the instructions, annotated with addresses, constants byte-read little-endian
Y0 = u16le(img, 0xC6AFC)              # 32768   ld.hu 0x7afc,tp,r6   @0x3a650
ceiling = (headroom * lerp_y) >> 15   #         mul r15,r10 ; sar 0xf,r10  @0x3a79e/0x3a7aa

# BAD -- "the LERP scales the lane's output bound by a Q15 factor"
```

- Mirror the real operations: integer `>>` not `/`, the real Q-format, the real branch conditions.
- Annotate each line with the instruction address it came from.
- State constants as **byte reads from the image, little-endian** (V850 is LE), with the anchor check
  visible (`0xC646C` must read 3564 modified / 891 stock).
- Give the dB/Hz interpretation *after* the code, as a consequence of it — never instead of it.
- A worked numeric example (plug in the measured value, show the result) beats an adjective.

See [[accord-lerp-tables-count-word-first]], [[feedback-ghidra-mcp-only-no-rizin]],
[[accord-v850-scan-traps-formatv-and-storezero]].
