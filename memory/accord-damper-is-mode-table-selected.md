---
name: accord-damper-is-mode-table-selected
description: FUN_00034350 selects all five damping factors through a 13-variant mode table; V72 edited modes 10/11 and the probe proves the car is not in them — the damping lever has never been tested.
metadata:
  type: reference
---

> 🛑 **AMENDED 2026-08-05 — READ THIS FIRST.** ✅ **Resolved 2026-08-05: the live modes are 24 (manual) / 26 (engaged), row 11 `TVCA4`.** The "modes 4/5 and 12 consistent, 0-3 marginal" grading in this file is **superseded**. See [[reference-accord-car-is-tvca4-mode-24-26]].

★★★★★ **V72's damping levers were never in force, and it is provable arithmetically.**

`FUN_00034350` selects **all five** damping factors — B, C, D, E **and the ceiling** — through pointer
arrays indexed by `mode * 4`:
```
FactorB 0xC9CCC[mode]   FactorC 0xC9E9C[mode]   FactorD 0xC9DB4[mode]
FactorE 0xC9F84[mode]   ceiling 0xC77A0[mode]
mode = *(byte)(gp + 0x63fd)          <- ld.bu 0x63fd,gp  (verified in Ghidra at 0x34470)
```
**13 mode variants exist. V72 edited modes 10 and 11 only.**

## THE PROOF [EVIDENCE, arithmetic + 87,940 frames]
On V72, modes 10/11 carry `FactorC = [430,430,430,877]` (so `C >= 430` at **every** speed — below
`X[0] = 2240` it clamps to `Y[0]`) and `FactorE = [927,927,927,927]` (so `E = 927` at **every** rate):
```
|gp-0x6bd0| = 1024 * (430/1024) * (927/1024) = 389 MINIMUM, unconditionally
```
⇒ in mode 10/11 V72's `bit4` (`|gp-0x6bd0| >= 64`) fires on **100%** of frames.
**It fired on 0 of 87,940, including 0 of 34,275 above 35 km/h.**
⇒ **the car is NOT in mode 10 or 11. Levers B and C were INERT BY TABLE SELECTION.**

★ **Everything else was eliminated first, so this is not a guess:** the seed (`gp-0x698a` = the missing
"FactorA") is **pinned at 1024** — 9 of 10 channels hardcode unity at the call site, channel 1's degrade
path is a calibrated no-op, channel 10 has no runtime writer, and the `.data` boot image at flash
`0x86E80` reads eleven 1024s (two independent derivations); FactorB/D are **flat unity**; there is **no
external writer** of `gp-0x6bd0` (3 stores, all inside `FUN_00034350`); the ceiling is **>= 512
everywhere**; and the probe encoding was hand-verified byte by byte.

## HOW THE MODE IS CHOSEN
`FUN_00042746` (called from task 5) writes it from four cal tables `tp+0xe012/13/14/15`, selected by
`gp-0x67f6` (driven by **`gp-0x6806`, LKAS-applying**) and `gp-0x67e2`, **indexed by
`FUN_00057f8e() * 0x24`** — a **config lookup** matching a 5-byte ASCII key at `gp+0x6408..0x640C`
against 16 records at `0xCD000`, returning the index **or 0 on no match**:
```
i=0 '00000'->0/2   i=1 'TVAA0'->4/5   i=2 'TVAA1'->10/11  i=3 'TVAC1'->10/11
i=4 'TVAA2'->4/5   i=5 'TVAA4'->4/5   i=6 'TVAA6'->10/11  i=7 'TVAC4'->10/11
i=8 'TVAA7'->12/14  i=9..12 'TVCA*'->16..24   i=13..15 'TWAA*'->28..32
```
🛑 **`39990-TVA-A160` "reads as" `TVA`+`A1` = row 2 ⇒ modes 10/11. That mapping is an ASSUMPTION in
`BUILD-LINEAGE.md`, never a measurement** — and `build_v44_tva.py` has patched 10 **and** 11 since V44
*because of it*.

## WHICH MODE IS LIVE — [OPEN]
Graded on route 59's own telemetry against each mode's exact `bit4` trip threshold:
**modes 4/5 and 12 FULLY CONSISTENT** (highway `gp-0x6ac0` peaked at **329.8 counts** vs their **330–335**
thresholds — never reached) · **modes 0–3 marginally disfavoured** (11 of 34,277 frames exceeded their
270-count threshold, within 100 Hz sampling slop) · **10/11 EXCLUDED.**
⚠ `gp+0x6408` is **`.bss`**, zero-cleared at boot, outside the `.data` restore range, and its **only
writer is a UDS service** (`FUN_000508e8`, taking bytes from a diagnostic payload — it does **not** parse
the firmware's ID string; that hypothesis was checked and refuted). **No boot-time NVM reload was found
by two agents** — but the boot loops use `sst.w` with a **computed `ep`**, invisible to disp16/disp23
scans, `search_instructions` and `get_xrefs_to` alike, so a restore path could exist unfound.

⇒ **V73 reads `gp+0x63fd` directly (probe bits 6:3).** See [[accord-v73-built-mode-probe]].
⇒ Consequence: **every prior "damping is null" result on this kit (V44, V47, V72) is UNINTERPRETABLE,
not falsified.** Recorded as `RULE 6` in `docs/BUILD-LINEAGE.md`.

🛑 **Do NOT "fix" this by editing `0xC4124` (the dispatch role table) or `gp+0x63fd` itself** — the former
un-closes the `gp-0x67ac` vacuity gate, whose REDUCED branch zeroes r24, r26 **and** damping, making
every lever this kit has flown vacuous by construction. **Write proven values into the LIVE mode's
records instead.**
