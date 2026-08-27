---
name: accord-tva-hw-id-provenance
description: Provenance of the 5-byte ECU hardware ID at gp+0x6408..0x640C in Honda Accord EPS 39990-TVA-A160 (V850 code.bin). Writer function, dispatch table entry, UDS service identification.
metadata:
  type: reference
---

## Finding: 5-byte ECU HW-ID at gp+0x6408..0x640C — Accord TVA A160 V850

Verified via GhidraMCP disasm/decompile, 2026-05-26.

### RAM address
- gp = 0xFEDF8000, so gp+0x6408 = 0xFEDFE408 through 0xFEDFE40C (5 bytes)

### Sole writer: FUN_000508e8 (UDS diagnostic handler)
- Only function that stores to gp+0x6408..0x640C (confirmed by exhaustive st.b search across all 185K instructions)
- Store instructions: 0x000509D4 (byte 0), 0x000509DA (byte 1), 0x000509E0 (byte 2), 0x000509E6 (byte 3), 0x000509F0 (byte 4)

### Two code paths in FUN_000508e8:
1. **`*pcVar11 == '\0'` (init/blank path):** Sets all 5 bytes to 0x30 ('0' ASCII) explicitly in code. Also calls memcpy(gp+0x6400, 0x14500, 4) for adjacent 4-byte region. The 5 ID bytes are NOT read from flash here — they are hardcoded to '0'.
2. **`*pcVar11 == '\x01'` (write path):** Copies pcVar11[1..5] → gp+0x6408..0x640C. This is a diagnostic write from a received message buffer. Calls FUN_00057f8e() to validate the new ID against the 0xCD000 table; if invalid (returns 0), reverts and sends NRC 0x31 (requestOutOfRange).

### Protocol identification: Honda proprietary diagnostic (UDS-adjacent)
- FUN_000508e8 is reached via function pointer table at 0xB77A8 (entry: handler=0x508E8, f1=0x3B, f2=0x05, f3=0x84, f4=0x08)
- Error codes: 0x22 = conditionsNotCorrect, 0x31 = requestOutOfRange — standard UDS NRC values
- FUN_00020436 is the NRC setter; FUN_0002073a sends the negative response
- Service byte in dispatch table: 0x84 (Honda proprietary, not standard UDS)

### Boot default
- At first run (blank/uninit flag): bytes are set to `30 30 30 30 30` ("00000" ASCII) in code
- Flash at 0x14508 also contains `30 30 30 30 30` (coincidence with code default, or flash-default mirror — NOT directly read by any discovered code path)
- No ld.b from gp+0x6408 found outside FUN_00057f8e (the reader/matcher)

### No hardware register source found
- No peripheral MMIO address discovered as source
- No OTP/unique-ID hardware register path found
- Source is purely the diagnostic write path (service 0x84, sub-cmd 0x01)

### Dispatch table location
- Table base extends from ~0xB7600 to ~0xB7C00 (stride varies by section)
- FUN_000508e8 entry at 0xB77A8 confirmed by byte-pattern search for E8 08 05 00

### UDS obtainability assessment
- The 5 bytes ARE writable via Honda proprietary service 0x84 sub-function 0x01
- Readable via FUN_00057f8e (the matcher) — the reader reads them from RAM, implying they survive across sessions only if NVRAM-backed (not confirmed)
- Standard UDS 0x22 ReadDataByIdentifier with DIDs F18C/F18x: NOT confirmed to expose this specific 5-byte field — those standard DIDs likely map to a different handler
- Operator would need to identify which standard DID (if any) maps to service 0x84 reads; the adjacent 0xCC-handler at 0xB7794 (address moved/renamed since 2026-05-26, not re-located this pass) may be the read counterpart to the 0x84 write handler

## Addendum 2026-08-05 — cross-referenced against the compiled part-number ID string, re-confirms this file, closes team-lead's V72/V73 mode-selector sub-question

Dispatched to check whether the ID-string build marker (`0x13109`/`0x14120`, the "-" edited by every modified build to distinguish itself from stock) could break `FUN_00057f8e`'s 5-byte HW-ID match — which selects `gp+0x63fd`'s mode (10/11 for this car, per `builds/v18_v49/build_v44_tva.py`'s pre-existing documentation, see
[[reference_accord_mode_selector_gp63fd_hwid_failover_not_engagement_flag]]).

**Re-confirmed this file's core finding fresh** [EVIDENCE, `search_instructions` on `0x6408`/`0x640c`]: every positive-offset access is inside `FUN_000508e8` (the writer, unchanged) or `FUN_00057f8e` (the reader). No third function touches these bytes.

**Checked both ID-string sites directly** — both real, exactly where expected: `0x13100` = `"39990-TVA-A16039990-TVA-A110C308"` (two concatenated part-number strings), edited hyphen at `0x13109` = the "TVA"-"A160" hyphen of the first copy. `0x14110` region = `"...VA-A11039990-TVA-A160\0\0\0\0\0\xff\xff..."`, edited hyphen at `0x14120` = the "TVA"-"A160" hyphen of `"39990-TVA-A160"` starting at `0x14117`.

**`get_xrefs_to(0x13100)`** found exactly one reference: `FUN_0004f6fa`, decompiled in full — a UDS **read-back** service (`FUN_0002114e(&DAT_00013100, 0xe)` copies the whole 14-byte string verbatim into a diagnostic response buffer, exposing the part number to a scan tool). **It does not feed `gp+0x6408`.** `get_xrefs_to(0x14117)` found nothing (this kit's known misleading-null-xref-on-data trap), but the instruction-level `0x6408`/`0x640c` search (the required second method) found no other writer either.

**Conclusion: neither ID-string copy feeds `gp+0x6408..640C` by any path found. The build marker at `0x13109`/`0x14120` cannot affect the HW-ID match** — not because the extraction is fixed-offset-safe, but because there is no extraction from that string at all. This file's original "source is purely the diagnostic write path" finding stands, now cross-checked against the specific string-edit hypothesis and found to rule it out cleanly.

**What remains open** (inherited from this file's original assessment, not newly resolved): whether the UDS-written value in `gp+0x6408` (`.bss`, boots to blank) is NVRAM-backed across power cycles. If not, and nothing else restores it, a cold boot would start at the hardcoded `"00000"` default — which happens to be team-lead's decoded **index-0 signature (modes 0/2, the all-zero-damper case)** — until a diagnostic write occurs. No boot-time restore path was found by either this file's original search or this session's. **Tie-breaker weighted most heavily**: `V44`/`V47` (already flashed and driven) edited FactorC/E specifically at mode 10/11's own tables, and the operator reported a real, if marginal, on-car difference — which would be impossible if the live mode were stuck at 0 (mode 0's tables are structurally different arrays, untouched by those builds). Indirect, not a firmware-byte proof, but evidence from the one place scan traps can't reach.

**Recommendation** (not a fix — a measurement): a V73 probe rung reading `gp+0x63fd` back (or a paired UDS read on the `0x84` service, if one exists) settles the persistence question on one drive.

Related: [[reference_accord_mode_selector_gp63fd_hwid_failover_not_engagement_flag]] — the mode-selector chain this addendum closes the string-provenance question for.

## Addendum 2026-08-05 round 2 — independent cross-check (converges) + the bit4-trip arithmetic team-lead asked for

Re-derived the writer/reader/dispatch chain from scratch (not from this file) and landed on the same
conclusions above, including the boot-value gap. Adds two things not previously recorded:

**⚠ Tension on the record, unresolved:** this file's V44/V47 tie-breaker (*"operator reported marginally
quieter at 5 mph"*) is real but weak — a subjective, non-blinded "marginal" result is hard to distinguish
from placebo/noise. It should not be weighted over V72's clean, quantitative 0/87,940-frame null, which is
structurally airtight for mode 10/11 given V72's edits (flat `FactorE=927`, `FactorC` floor `>=430` ⇒ product
`>=389` at every speed/rate once engaged — no rate-dependency left to explain silence). If these two pieces
of evidence disagree, trust the V72 measurement.

**Bit4-trip-threshold arithmetic, computed exactly for every surviving mode family** (modes 0-3 share one
table, functionally identical; modes 4-5 share another; mode 12 is close to but distinct from 4-5):
```
                          speed:  35km/h   50      60      80     100     140
modes 0-3 (i=0, "00000")        unreach.  654cts  412cts  298cts  270cts  230cts
modes 4-5 (TVAA0/A2/A4)         unreach. 1808cts 1087cts  477cts  335cts  239cts
mode 12 (TVCA3/6)               unreach. 2120cts 1137cts  467cts  330cts  235cts
                                                          (bit3 gate = 512 always)
```
(motor-rate `gp-0x6ac0` needed for `FactorC(speed)*FactorE(rate)>>10 >= 64`, per mode family; below 35 km/h
all three are structurally silent regardless of rate, `FactorC=0` there for every candidate). **Does not
cleanly separate the candidates** — all three need only ~230-300 counts at highway-top speed, well under
bit3's 512 gate, so V72's "silent above 35 km/h" datum constrains `gp-0x6ac0`'s highway distribution to
stay under roughly 230-300 counts for ALL of them alike, not just mode 10/11's rejection. Full record
addresses/stock bytes for modes 0,1,2,3,4,5,12 (independently pointer-dereferenced, none in
`[0xC5000,0xC5FFC)`, ceiling `X=[300,800] Y=[512,1024]` uniform across every mode checked) are in the
session transcript, not restated here — ask if this file needs the full table appended.

**Recommendation, sharpened**: probe `gp+0x63fd` (mode byte) AND `gp-0x67e2` (the selector that picks the
paired mode value within a record, e.g. 10 vs 11, or 0 vs 1 vs 2 vs 3) together, so a mid-family split is
visible on the drive rather than inferred.
