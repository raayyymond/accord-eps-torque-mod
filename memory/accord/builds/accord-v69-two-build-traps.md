---
name: accord-v69-two-build-traps
description: "Two build traps found while writing V69 — an edit pair that is jointly safe but individually worse than stock, and three mode variants sharing byte-identical records within 40 bytes."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 95bceff4-4059-403e-a0cd-c57effc19f41
  modified: 2026-08-04T03:28:06.582Z
---

🛑 **TRAP 1 — AN EDIT PAIR THAT IS JOINTLY SAFE AND INDIVIDUALLY DANGEROUS.**
V69 reverts both the gate byte (`0x3AA96` `fb`→`c5`) and the arm cal (`0xC6446` 5244→512). **Writing
`0xC6446 = 512` while the gate is STILL repointed leaves the arm LIVE at 512, which is ~5× BELOW the
stock LERP** — that makes engaged steering *worse than stock everywhere*. Reverting the gate alone is
harmless (nothing then reaches the cal).
**How to apply:** when two edits are jointly safe but individually dangerous in one direction, assert
the implication **in the builder, in code that refuses to emit** — not in a comment.
`builds/v50_v79/build_v69_tva.py` asserts `arm == 512 ⟹ gate byte == 0xc5`.

🛑 **TRAP 2 — THREE MODE VARIANTS SHARE BYTE-IDENTICAL RECORDS WITHIN 40 BYTES.**
The mode-10/11/12 `gain_B` records interleave at stride `0x14`, and **mode 11's and mode 12's 0 km/h
records are BYTE-IDENTICAL to mode 10's** (`[3072, 3072, 2322, 1536]` at `0xD2A74`/`0xD2A88`/
`0xD2A9C`); the 10 km/h records sit one count below. So a target byte pattern occurs **three times
within 40 bytes**, and a pattern-based edit would silently rewrite another car variant's calibration.
⚠ **`verify/diff_build_vs_stock.py` is SPAN-based and would attribute it without complaint.**
**How to apply:** address every calibration cell **absolutely**, never by byte pattern, and assert
the neighbour records unchanged in both builder and verifier.
⚠ **And mode 12 is NOT a copy of mode 11** — `0xD2B14` is `[2303, 2303, 2151, 1947]`, not mode 11's
`[2304, 2304, 2150, 1946]`. Assuming they matched is an error `verify/verify_v69_image.py` caught on its
first run.

★ **THE GENERAL LESSON, and it is why both files exist:**
**`verify/diff_build_vs_stock.py` attributes by RANGE, so a WRONG VALUE inside an existing `EDITS` span
passes silently.** Only exact-value anchors close that hole. **Ship a value-anchored
`verify_v*_image.py` with every build and run BOTH; neither is sufficient alone.**
⚠ `verify/verify_v68_image.py` does **not** check `0xC6564` (r26's inert cal base) — `verify/verify_v69_image.py`
adds it, along with the neighbour records.

Related: [[accord-v69-built-speed-shaped-rate-lane]], [[accord-check-build-lineage-before-proposing-lever]].
