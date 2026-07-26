---
name: reference-accord-pointer-base-audit
description: "Complete program-wide audit of every tp/gp register write in the 2020 Accord 39990-TVA-A160 code.bin (185,116 instructions). The crucial cal pointer tp is built in THREE instructions; the third (add r1, r1=0x8000) is what was missed before. Application tp=0xBF000 (VERIFIED): movhi 0xb,r0,tp @0x140ce + movea 0x7000,tp,tp @0x140d2 + add r1,tp @0x140d6. Bootloader tp=0xF8000 (@0x9152+0x9156, no add). gp=0xFEDF8000 in both app (@0x140c4..cc) and bootloader (@0x914a/4e). Steering/torque code runs under the app => tp=0xBF000 => every tp+offset cal lives at 0xBF000+off (the programmed 0xC4000-0xC6FFF band). The three add-to-tp hits at 0xCBxxx are in the cal DATA band (no containing function) = mis-disassembled data, not executable."
metadata:
  node_type: memory
  type: reference
---

# Accord TVA-A160 pointer-base audit — every tp/gp register write (2026-05-27)

Done by program-wide `search_instructions` over all 185,116 instructions of `code.bin` (V850:LE:32, image_base 0). This closes the recurring `tp`-base hazard ([[reference-accord-databin-tp-base]]) by **enumerating every write to the `tp` and `gp` registers** rather than inferring the base. Method: searched `movhi/movea/add/mov` with operand `tp` / `gp` as destination.

## The crucial subtlety: tp is built in THREE instructions

The application init `FUN_00014084` builds both pointers, and the **third instruction (`add r1`, r1=0x8000) is load-bearing** — omitting it gives the wrong base (this is the error that produced the prior `0xC71D6`/`0xC7424` slew/deadband mis-addressing, and earlier the whole `tp=0xF8000` absent-partition dead-end):

```
0x140c4 movhi -0x121,r0,gp ; 0x140c8 movea 0x0,gp,gp   ; 0x140cc add r1,gp   -> gp = 0xFEDF0000 + 0x8000 = 0xFEDF8000
0x140ce movhi  0xb,r0,tp   ; 0x140d2 movea 0x7000,tp,tp ; 0x140d6 add r1,tp   -> tp = 0xB7000   + 0x8000 = 0xBF000
```
(`r1 = 0x8000` on entry to this routine.) `movhi`+`movea` alone give `tp=0xB7000`; only the `add r1,tp` lifts it to `0xBF000`. Note `0xB7000` is itself meaningful — it is the base of the CAN route tables (`0xB70F4`/`0xB733C`/`0xB739C`), so a half-resolved `tp` is doubly misleading.

## Complete enumeration

| Reg | Context | Sites | Result |
|---|---|---|---|
| tp | reset stub | 0x1c4 `movhi 0x0` / 0x1c8 `movea 0xd38` / 0x1cc `add r1,tp` | transient (very early) |
| tp | **bootloader** | 0x9152 `movhi 0x10` / 0x9156 `movea -0x8000` (no add) | **0xF8000** |
| tp | **application** | 0x140ce `movhi 0xb` / 0x140d2 `movea 0x7000` / 0x140d6 `add r1,tp` | **0xBF000** ✓ |
| tp | 0xCBxxx | 0xcbcd4 `add r12,tp`, 0xcbe9c `add 0x4,tp`, 0xcbea0 `add -0xc,tp` | **cal DATA band, no containing function = mis-disassembled data, NOT executable** |
| gp | reset stub | 0x1ba / 0x1be / 0x1c2 | transient |
| gp | bootloader | 0x914a `movhi -0x120` / 0x914e `movea -0x8000` | 0xFEDF8000 |
| gp | application | 0x140c4 `movhi -0x121` / 0x140c8 `movea 0x0` / 0x140cc `add r1,gp` | 0xFEDF8000 ✓ |

## Consequence (load-bearing)

Steering/torque/FOC code runs under the application, so **`tp=0xBF000` and `gp=0xFEDF8000` for every torque-path access**. Every `tp+offset` calibration address used in the torque analysis (gain `0xC646C`, clamps `0xC61B2/B4`, slew `0xC61D6`, deadband `0xC6424`, ramp `0xC64DE`, governor `0xC6202`) is therefore confirmed correct. Any future analysis MUST resolve `tp` at the application definition site (the full 3-instruction sequence), not a `movhi`/`movea` pair and not a bootloader/reset value.

See [[reference-accord-databin-tp-base]] (this audit is the exhaustive confirmation of it), [[reference-accord-driver-override-plausibility-eme]] (the slew/deadband addresses this corrected), [[feedback-rigorous-validation]].


## 2026-05-30 — recurring +0x1000 address-arithmetic slip (prevention)
tp=0xBF000, so **tp+0x7NNN = 0xC6NNN, NOT 0xC7NNN**. This bit multiple subagents AND the lead
this session (0xC7420 vs 0xC6420; 0xC71F8=41060 "unreachable" vs the real 0xC61F8=1024
"easily reached" — which nearly mis-ruled a cut path). ALWAYS read_memory the computed flash
addr before trusting a cal value. Also: get_xrefs_to on an absolute RAM addr (0xFEDF…) returns
nothing (code is gp-relative); use search_instructions with operand_pattern = the hex offset
substring (e.g. "4e65"), not "-0x4e65[gp]". Detail: analysis-2020accord/SESSION-2026-05-30-EME-RESOLUTION.md.
