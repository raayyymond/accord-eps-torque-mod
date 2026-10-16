# TRACE 2026-10-05 — Is any V37 cell slot-dependent? (LX no-power-steering report)

Study artifact. Nothing was flashed or sent. Subagent `v37-slot-classifier`. Ghidra program = stock `code.bin` (confirmed by `list_open_programs`, single program). Images: stock `stock_fw_dump/code.bin`, `_v36_plain_image.bin`, `_v37_plain_image.bin` under `../accord-firmwares/analysis-2020accord/`.
Tags: **E** = evidence (method given), **B** = belief. `gp = 0xFEDF8000`, `tp = 0xBF000`.

## 0. Headline

No V37 cell is selector-indexed. Every non-CRC cell is a direct tp-relative load (E). Where a consumer also reads a slot selector, the per-slot records for slot 2 (`TVAA1`, selectors 2/1) and slot 11 (`TVCA4`, selectors 4/7) are byte-identical for everything the V37 cells touch (E). I found **no static path** from any V37 cell to a latched loss of assist at power-on or in manual operation, under any slot. The leading slot hypothesis is therefore **not supported by the V37 byte diff**. Details and what is still open are in sections 4 and 5.

## 1. Byte diff, V37 vs stock (E: Python, `[0x13000,0x100000)`, 42 bytes)

V36 vs stock is 41 bytes. V37 vs V36 is exactly 5 bytes: `0xC64B8` and the `0xC6FFC` trailer.

| cell | width | stock | V37 | first on-disk build | what it is |
|---|---|---|---|---|---|
| `0x13109`, `0x14120` | u8 x2 | `2D` | `2C` | V22 (lineage says V18) | `-` to `,` in the two copies of `39990-TVA-A160`. Read only by an ID-copy routine at `0x4F6FA`/`0x4F6D6` (no direct caller). Cosmetic (B) |
| `0xC4FFC` | u32 | `7549F248` | `EF3421CC` | per build | CRC of `[0x13000,0xC4FFC)`; changes because of the string edit |
| `0xC61B2`, `0xC61B4` | u16 x2 | 512 | 1024 | V22 | arbitration output clamp, LKAS-gain output clamp |
| `0xC646C` | u16 | 891 | 1782 | V22 | shared sensor-scale (torque sensor counts to Q15 gain) |
| `0xC64DE` | u8 | 17 | 27 | V22 (lineage: V18) | hold count of the `gp-0x6b2c` square-wave generator |
| `0xC6598`,`0xC659C` | f32 x2 | 1.0 | 4.0 | V29 (2.0), V30 (4.0) | float dir1 corridor wall |
| `0xC65AC`,`0xC65B0` | f32 x2 | -1.0 | -4.0 | V29, V30 | float dir2 corridor wall |
| `0xC65C4`,`0xC65C8`,`0xC65CC` | f32 x3 | 0 / 1.5 / 2.0 | 4.0 x3 | V31 | float boost floor Y |
| `0xC674E`,`0xC6750` | s16 x2 | 1024 | 4096 | V25 (2048), V30 | int dir1 corridor wall |
| `0xC675A`,`0xC675C` | s16 x2 | -1024 | -4096 | V25, V30 | int dir2 corridor wall |
| `0xC6768`,`0xC676A`,`0xC676C` | s16 x3 | 0 / 1536 / 2048 | 4096 x3 | V31 | int boost floor Y |
| `0xC61C0`,`C2`,`C4` | u16 x3 | 1600/896/1280 | 65535 | V36 | gentle-EME debounce rate thresholds |
| `0xC64B4`,`B5`,`B6`,`B7` | u8 x4 | 70 60 36 40 | FF x4 | V36 | debounce torque thresholds |
| `0xC64B8` | u8 | 0x70 | 0xFF | V37 | DTC-0x49 counter gate |
| `0xC6FFC` | u32 | `0C9E3CEF` | `7FFE8A14` | per build | CRC of `[0xC6000,0xC6FFC)` |

Corrections to the brief:
- `0xC6CD0` is **not** in the V37 diff (`FFFF` in both). The "2x package" in V37 is `0xC646C`, `0xC61B2`, `0xC61B4`, `0xC64DE` plus the corridor/floor cells.
- Int and float corridor/floor cells are matched exactly (4096 = 4.0 x 1024) so the lockstep monitor sees no change (E: table decode, see section 3b).
- V37 is `V31 + V36 + 0xC64B8`. V31 to V35 images carry identical corridor/floor/gain cells (E: per-build table, V22..V39).
- Image integrity: the kit's `verify_bootloader_crc.py` passes V37 on all 50 blocks, bootloader walk and full chain (E). `0xC6FFC` = `7FFE8A14` is little-endian `0x148AFE7F`, the zlib CRC32 of `[0xC6000,0xC6FFC)`.

## 2. Reader census and slot dependence per cell

Method (E): raw little-endian scan of `[0x13000,0x100000)` for reg1 = tp with every form (disp16, `ld.hu`/`ld.w` via `hw2` bit 0, `ld.bu` parity from opcode field `0x3C`/`0x3D`, 6-byte extended, `movea`/`addi` table bases). Controls passed: 64 sites for `gp-0x4f60` `ld.h`; 7 sites for `0xC61B6` at the addresses the lineage lists; `FUN_00028ea6` from `0x22522`, `FUN_00034350` from `0x23276`. First pass of the byte scan merged `0xC64B8` and `0xC64B9` (the parity trap): `0x4549E`/`0x4556E` read `0xC64B9`, not `0xC64B8`. After the fix `0xC64B8` has exactly the six readers in the V37 handoff.
Pointer scan: no LE32 pointer and no `movhi 0xC` + low-half pair hits any V37 cell or a table base that covers one. No `movea tp` base covers the scalar cells. So **all V37 cells are direct, not pointer-array indexed (E)**.

| cell(s) | reader sites (live) | function / task | slot selector read by that function? |
|---|---|---|---|
| `0xC61B2` | `0x2B42A`..`0x2B446`, `0x2B5B6` | `FUN_0002b422`, `FUN_0002b57a`, 1 kHz task | no |
| `0xC61B4` | `0x2A1F8`..`0x2A21C` (dead twin `0x2A910`..) | inside `FUN_00028ea6` | `gp-0x674e` (sel) |
| `0xC646C` | `0x2A1EE` (PID forward); `0x2B656`, `0x2C488`, `0x36686`, `0x3684A` | `FUN_00028ea6`; `FUN_0002b62c` (100 Hz); `FUN_0002c478` (1 kHz); `FUN_00036682`; `FUN_00036828` (100 Hz) | `FUN_0002b62c` only, via `gp-0x674c` |
| `0xC64DE` | `0x2976E`..`0x299AA` (8) ; 8 more in the dead island `0x2B0AA`.. | `FUN_00028ea6` | `gp-0x674e` |
| `0xC61C0/C2/C4`, `0xC64B4..B7` | `0x2923E`..`0x292E8` | debounce SM in `FUN_00028ea6` | `gp-0x674e` elsewhere in the function |
| `0xC64B8` | `0x2920A`,`0x2921C`,`0x29A78` (+3 dead) | same | the `0x29A78` branch indexes `gp-0x674e` records |
| float corridor/floor | `0x44374`..`0x44536` | `FUN_00043e44` (float watchdog, 1 kHz) | none |
| int corridor/floor | `0x42F56`..`0x430DE` | `FUN_00042af8` (soft EME, 1 kHz) | none |

Dispatch (E, decompile of `FUN_0002214a`): the 1 kHz tasks run only when `gp-0x67fa` (master state) is in the masked set. `FUN_00028ea6`: states 4,5,8,11. `FUN_0002c478`/`FUN_0002caa2`: 4,5,11. `FUN_00042af8`/`FUN_00043e44`: 4,5,8,10,11. `FUN_00042692` (the variant selector init) runs in states 1 and 3. No reader of a V37 cell runs in the init states (state numbering meaning is B; `FUN_00022ca0` gating not examined).

Slot 2 vs slot 11 records read by those consumers (E, dumped from stock `0xCD000` and the pointer families):
- Selector columns: slot 2 = (`+0x12`=10, `gp-0x674c`=2, `gp-0x674e`=1); slot 11 = (24, 4, 7). Table identical in V37 and stock.
- `gp-0x674c` bank (13 tables read by `FUN_0002b62c`/`FUN_0002c246`/`FUN_0002c3b4`: `0xC7090`, `C70E8`, `C75B8`, `C7458`, `C7484`, `C742C`, `C7248`, `C7400`, `C73D4`, `C7534`, `C737C`, `C7350`, `C7198`, `C716C`, `C721C`, `C73A8`, `C72CC`, `C71C4`, `C71F0`, `C7274`, plus LERP families `C7064`, `C758C`, `C7560`, `C7140`, `C763C`, `C7610`): **sel 2 and sel 4 are identical in every one**. Only sel 0 (blank slot) differs, and sel 5 differs by one knot in `C7610`.
- `gp-0x674e` records inside the V37 branch at `0x29A78` (`0xCBA04`, `CB8B4`, `CBA74`, `CB924`): identical for every selector (X 70..80 / 32..112, Y ends 0). Setpoint-limit `0xCB844`: identical (15360 flat). `0xC9A88`: sel 1 and sel 7 identical. `0xCB994` (downstream gain curve, not a V37 cell) differs between sel 1 and sel 7 by a few knots.
- Base-assist family (`gp+0x63fd`: 10/11 vs 24/26) does differ strongly. No V37 cell reads it directly (E). Indirect effect through the EME bound is **B** (see 3b).

## 3. Crux: any latched loss of assist at/after power-on?

### 3a. V36 seven cells and `0xC64B8` (E)
- The debounce SM (`0x29120`..`0x2931E`) is entered only when `gp-0x69aa == 0x8000` (LKAS authority node full; compare `0xC73F2` = 32768 and `<0x8001`), `gp-0x67fe == 2`, speed gate and range checks pass (decompile of `FUN_00028ea6`, lines at the `bVar2` computation). Otherwise `gp-0x6807` is set to 3 or 7 and the counters are zeroed. So V36/V37 cells are not evaluated unless LKAS is commanding.
- The arb branch at `0x29A78`: with `0xC64B8` = 0xFF the interpolation runs for torque 113..255. All four records have Y[last] = 0 and X[last] <= 112, for every selector (table above). Both arms deliver 0, exactly as stock. **Slot 2 gets the same zeros as slot 11 (E).**
- V37 keeps counter B (`gp-0x6758`) at 0: the first-phase increment needs `0xC64B8 < gp-0x682f` and `gp-0x682f` is at most 255.

### 3b. The 2x/corridor/floor cells
- `FUN_00042af8`/`FUN_00043e44`: int and float tables carry the same values. The lockstep flags compare the float twin to `gp-0x6af6/6b00` within 5/1024 (decompile of `FUN_00043e44`, and the mirrored test inside `FUN_00042af8`). V37 changes both sides equally, so no flag. Neither function reads a slot selector (raw scan of `gp-0x674c/e`, `gp+0x63fc/d`). The floor X axis `gp-0x6ac2` is written only in `FUN_00041464` (motor-rate filter), not slot-dependent (B). The walls and floor only raise the bound in V37 (B: bound = max of the arms, from the soft-EME memory; I verified only the table values).
- `0xC646C` consumers:
  - `FUN_0002c478` computes a dither amplitude whose limit table `0xC69CA..0xC69D0` is all zero in stock and V37, so `gp-0x6b12` is identically 0 and `FUN_0002caa2`'s 307-count latch (state `gp-0x3cba` = 2, never exited) can never fire (E: table bytes, decompile).
  - `FUN_00036828` (DTC 0x23) runs only for 30..150 km/h (`0xC74EB`=30, `0xC74EA`=150, x64) and its first threshold cell `0xC602C` is 0, so its `bVar2` is always false (E: bytes; the `thunk_FUN_0000702c + tp` expression resolves to `0xC602C`).
  - `FUN_0002b62c`: the scaled term is at most 139 counts stock and 279 counts V37 against a 512 clamp (E: `0xC7428` = 1712, m <= 3072). The clamp is the same for sel 2 and 4. The follow-on range check (`FUN_0002c3b4` to `FUN_00027802` to `FUN_000462e6` to DTC 0x1D) compares two clamped copies of the same value (`FUN_00025c32` stores them) so it cannot disagree (E: decompile).
  - `FUN_00036682` feeds a low-gain aggregator summand (memory: -46 to -58 dB, B).
- `0xC64DE`: only drives the `gp-0x6b2c` square wave, which is identically zero (memory `gp6b2c_addend_is_identically_zero`, B for V37).

### 3c. Boot-time / DTC machinery (partly open)
- `FUN_00016de6` applicability uses `gp-0x3514`, which is an operating-mode mask written with 1, 2 or 4 by `FUN_00046372` callers (`0x196D8`, `0x1A16A`, `0x1A1F0`, `0x18F4A`). It is **not** derived from the HW-ID (E). The per-DTC inhibit bitmap at `gp-0x1be0` is set by routines at `0x47588`/`0x475AC` whose callers I could not find (raw jarl scan and pointer scan both empty, controls pass). Whether coding or the HW-ID can inhibit DTCs differently per slot is **unresolved**.
- Transition to the failsafe state 8 (`FUN_00019f7c`) latches via `gp-0x3ee8` when any fault class bit (`FUN_00046ea6`/`FUN_000197d0`) is set. I did not map DTC id to class for ids 0x1D, 0x23, 0x2A, 0x49.
- Not decompiled: `FUN_00022ca0` gating, `FUN_00027b0a`, `FUN_000347b8`, `FUN_00035154`, `FUN_000365d2`, `FUN_00039702`, `FUN_00041b8e`, `FUN_00042376`, `FUN_0004595a`, `FUN_00045a20` (other users of the 0x1D range-check). None of them read a V37 cell (E: reader census).

## 4. Ranked mechanisms

| # | mechanism | status | what falsifies it |
|---|---|---|---|
| 1 | Not content logic: identity/procedure/hardware difference on the LX (a second EPS bootloader or flash geometry, or a flash that did not complete). V37 integrity is clean on the kit's check (E), so this rests on exclusion (B). Record: V40 faulted at ignition with a stale, unchecked CRC block, so ignition faults can come from integrity | B | A control image that differs from stock only by the version-string byte pair and valid CRCs, flashed the same way. If it also fails, this class is confirmed; if it boots, content matters |
| 2 | `0xC646C` and the V22 clamps (`0xC61B2/B4`) on a car whose torque-sensor counts or polarity differ. Only V37 cells on manual-mode paths. All four non-PID monitors found dormant or saturating at standstill (3b) | B, low | UDS-free: capture `gp-0x4f60`, `gp-0x6752` and `gp-0x6b46` from the LX. If `|gp-0x4f60|` is large at rest, re-open. Cleanest cut: revert `0xC646C` to 891 only (costs the 2x forward gain, see below) |
| 3 | Slot-dependent monitor over a V37 cell (the lead hypothesis) | not supported (E for the cells and records above) | A reader of any V37 cell that indexes a table where slot 2 and slot 11 differ. None found. Would be falsified for good by the unexamined tasks in 3c also not reading a V37 cell (already E) |
| 4 | Corridor/floor EME or lockstep trip | very low (E for matching, B for the bound structure) | A lockstep flag sum above 128 at rest on the LX (`gp-0x6906`) |
| 5 | Debounce cells / DTC 0x49 unmasking | essentially excluded at power-on (E: needs `gp-0x69aa == 0x8000`) | LKAS never commanded on that car |
| 6 | Coding-dependent DTC inhibit (`gp-0x1be0`) makes a monitor live on the LX that is masked on the operator's car | unresolved | Find the setter callers and the coded source; then check which of 0x1D/0x23/0x2A/0x49 is masked on slot 11 |

Slot-proofing: there is nothing slot-dependent to revert. If the operator wants a bisect, the order by exposure on manual-mode paths is: (i) `0xC646C` to 891 alone, (ii) `0xC61B2`/`B4` to 512, (iii) corridor/floor to stock, (iv) V36/V37 cells. Reverting `0xC646C` alone also halves the forward LKAS gain (reader `0x2A1EE` is shared; V57 decoupled it with a private cell `0xC6CD0` and a displacement edit at `0x2A1F0`).

## 5. Stock on slot 2 vs slot 11

For the subsystems above stock is identical on both slots (E: same per-slot records), so a stock reflash working on the LX is consistent with the slot hypothesis but is equally consistent with hypotheses 1 and 6. The stock reflash does not discriminate.

## 6. Limits of this trace

- The LX slot is unknown (HW-ID `gp-0x6408..640C` is not in the image). I compared slot 2 against slot 11 because the brief named them.
- "Startup" is taken from the brief. If the fault appears only after driving, the LKAS-gated paths (3a) and the 100 Hz tasks matter more and the verdict on `FUN_00036828`/`FUN_0002b62c` rests on the speed gates I decoded.
- `search_instructions` was not used for any count. The Ghidra xref engine does not resolve tp-relative displacements, so Ghidra was used for function bounds, callers and decompile only.
- Memory-sourced claims (marked B) were not re-derived: soft-EME bound = max of arms, gp-0x6b2c addend zero, aggregator summand level.

## Reproduction

`C:\Users\dudei\AppData\Local\Temp\claude\...\scratchpad\v37cls\` holds `tpscan.py` (decoder with the parity fix), `cells.py` (reader census) and the dumps. Ghidra calls: `get_function_by_address`, `decompile_function` on `0x28EA6`, `0x2B62C`, `0x2C246`, `0x2C3B4`, `0x2C478`, `0x2CAA2`, `0x36682`, `0x36828`, `0x42AF8`, `0x43E44`, `0x25C32`, `0x27802`, `0x2214A`, `0x19F7C`, `0x16DE6`, `0x462E6`.

---

# FOLLOW-UP 2026-10-05 (b): manual-mode monitors downstream of V37 cells, bootloader side, sensor/data chain

Same rules. E = evidence with method, B = belief. Scripts in the scratchpad `v37cls\` (`tpscan.py`, `dtc.py`). Ghidra stock `code.bin`.

## F0. Corrections to section 3 above and to kit memories found on the way

- **`FUN_00036828`'s threshold is cell `0xC61AE`, not `0xC602C`.** Ghidra labels the `ld.hu 0x71AE[tp]` at `0x368C8` as `thunk_FUN_0000702c + tp`. My earlier "0xC602C is 0 so bVar2 is always false" is **withdrawn**. `0xC602C` is a float 5.0 read only by `FUN_00045A20` (`ld.w` at `0x45AD0`, `0x45B06`). I did not re-derive the 0x23 gating; it stays "not hard-eligible (flag word 0)".
- **The learned scale/offset gate is `tp+0x74C3` = `0xC64C3` = 0, not `0xC63C3` = 4.** The tracer memory `reference_accord_gp4f60_identity_conflict_and_producer_traced` carries the `+0x1000` slip again. With the gate at 0, `FUN_0007F3F8` skips the `gp-0x698C` / `gp-0x6B50` correction and stores the CORDIC result directly (E: byte reads `0xC64C3`=0 and `0xC63C3`=4, decompile `0x7F3F8` tail).
- Parity re-check of `0xC61B3`/`0xC61B5` (high bytes of the clamp cells): a parity-aware scan of every tp form (ld.b, ld.bu with `0x3C`/`0x3D`, ld.h/hu, ld.w, ext6, bit ops, movea/addi) over `[0x71A0,0x71B5]` finds only the 13 halfword readers already listed. No byte or word access overlaps `0xC61B3`/`0xC61B5`, and no table base covers them (E).

## F1. Manual-mode data paths from the V37 cells to hard-eligible monitors

**Hard-eligible set (E).** Flag word at `0xB7D58 + (id-1)*0x1C + 8`, hard if `& 0x41`: ids 04 06 07 08 0B 0C 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 28 2A 2B 2C 2D 2E 2F 30 31 33 36 37 3A 44 45 (37 ids). Not hard: 0x23 and 0x49. Call-site census (jarl to `0x16DE6`, constant id before the call): 0x1D is reached only through `FUN_000462E6` (12 caller functions: `0x27802`, `0x27B0A`, `0x347B8`, `0x35154`, `0x365D2`, `0x36D74`, `0x39702`, `0x41B8E`, `0x42376`, `0x43E44`, `0x4595A`, `0x45A20`). 0x2A: `FUN_00042AF8` (`0x43DE4`) plus `0x2CC2A`, `0x497E6`, `0x4C780`. NVM and coding ids 04/06/07/08 sit in `0x18D02`, `0x19204`, `0x193F0`, `0x19482`, `0x14BA0`, `FUN_00048A40`.

**None of the 12 range-check callers reads a V37 cell or a cell derived from `0xC646C`**, except `FUN_00043E44`, which reads the float corridor/floor cells and is lockstep-symmetric (reader census of the tp cells). What the V37 cells feed, in manual mode:

| V37 cell | reaches | bound in manual mode | monitor on that output |
|---|---|---|---|
| `0xC646C` via `FUN_00036682` | summand `gp-0x6B46` in `FUN_0003AA2C` | output = IIR of `clamp(.,+-0x200)`, so abs <= 512 in V37 and stock | aggregator sum clamped to +-0x2800 at `0x3AD00`, shadowed (`gp-0x4CE0`); `FUN_0004595A` compares it with the governor output (F1b) |
| `0xC646C` via `FUN_0002B62C` | `gp-0x6AF0` | term <= 139 (stock), 279 (V37), clamp 512 (`0xC7090[sel]`, same for every slot) | `FUN_0002C246`/`C3B4` + `FUN_00027802` compare two copies of one clamped value, cannot differ |
| `0xC646C` via `FUN_0002C478` | `gp-0x6B12` | identically 0 (limit table `0xC69CA..D0` all 0) | `FUN_0002CAA2` latch (`abs(gp-0x6B12) > 0xC71D2 = 307`) can never fire |
| `0xC646C` via `FUN_00036828` | `gp-0x6B44/6B42/6B40`, DTC 0x23 | not hard | none |
| `0xC61B2` (`FUN_0002B422`) | channel-1 copy, `gp-0x6B3A` | input is the arbitration output, 0 in manual | `FUN_0002B57A` + `FUN_00027802`: copy vs `clamp(.,+-0xC61B2)` of the same value, trips only if `0xC61B2 > 0x2800` (it is 1024) |
| `0xC61B4`, `0xC64DE` | LKAS lane; `gp-0x6B2C` square wave | LKAS idle: lane 0; `gp-0x6B2C` identically 0 (memory, B) | none reachable |
| corridor/floor cells | soft EME `FUN_00042AF8` and float twin `FUN_00043E44` | V37 raises every bound; both sides match | DTC 0x1D (weighted flags > 128, ~10 ms integrator) and 0x2A; see F1c |

**F1a. `FUN_00045A20`** (E: decompile + `FUN_000456A4`). Inputs are motor-rate and steering-angle cells, not torque. `gp-0x6ACC - gp-0x6ACE` equals the damper term `gp-0x6AD0` written by `FUN_000456A4`. Integer mirror of the band (counts/1024, `F = float @0xC602C = 5.0`):

```python
def t45a20(acc, ace, abe, a10):            # a10 = gp-0x6a10, abe = gp-0x6abe (signed rate)
    f = a10*0.1
    T = lerp(f, [350.0, 410.0], [5000.0, 400.0])        # 0xC6610..0xC661C
    lo = (-5.0 if T <= abe else 0.0) - 0.001
    hi = ( 5.0 if abe <= -T else 0.0) + 0.001
    c = (acc - ace)/1024.0
    return c > hi or c < lo      # -> FUN_000462E6(0x3A09) -> DTC 0x1D, no debounce
# damper term (FUN_000456a4): nonzero only if gp-0x6ac0 > thrA(a10),
# thrA = lerp(a10, [3800,4000,4150], [5000,3037,1000])
```

Solving: a nonzero damper term is allowed only if `abs(gp-0x6ABE) >= T`, and `thrA(a10) >= T(a10)` for every angle (computed over 0..6000: minimum difference 0, equality at `a10 <= 3500` where both are 5000). So the only trip window is a rate that crosses 5000 in `gp-0x6AC0` before it does in `gp-0x6ABE` (two filters of one signal, B), at small angle. No torque input, same in stock and V37. This is the V40-class monitor and V37 does not touch it.

**F1b. `FUN_0004595A`** (E). OK iff `abs(b94) - abs(ace) >= -10` counts and `ace*b94 >= -10485` (counts squared; both from `float > -0.01`). `b94 = gp-0x6B94` (aggregator, +-10240), `ace = gp-0x6ACE` (governor output). Torque enters both identically through the aggregator; V37's contribution is the <= 512 summand. No torque level trips it unless the governor output exceeds the aggregator by 11 counts, which `FUN_0004503C` does not do at rest (cap `gp-0x4F64` is 5325 at rest per the V40 handoff, B).

**F1c. Soft EME (`0x2A`) and float watchdog (`0x1D` flags).** At rest the floor X (`gp-0x6AC2`, motor rate) is 0, so floor = Y[0]: stock 0, V37 4096; the corridor arms are zeroed when `abs(gp-0x6BF0) <= 9216` (hands-off) (B, memory). So at rest V37's bound is >= stock's: more permissive. SM2 integrates `(cmd - bound) << 15` per ms and cuts at `abs(I >> 15) >= 15361` (memory, B), self-clearing. A torque 2x the operator's, at rest, can only make STOCK's soft cut more likely than V37's. Lockstep flags compare the float twin with `gp-0x6AF6/6B00` within 5/1024; both are rebuilt from tables V37 changes equally (E, decompile `0x43E44`/`0x42AF8`).

**F1d. `FUN_00036D74`** (E, prior memory): `abs(gp-0x6B26)/1024 <= 0.5` (`0xC4004`), lane clamp `0xC407E` = 511. Input is filtered motor acceleration, not torque. V37 touches neither cell.

**F1e. Boot self-test.** The init states run `FUN_00042692` (variant selector) and `FUN_00014BA0` (reset-cause DTC 0x18 from NVM). No reader of any V37 cell runs in states 1 or 3 (dispatch masks in `FUN_0002214A`, E). `FUN_00019F7C` enters failsafe state 8 on any fault-class bit (`FUN_00046EA6(0)`, `(2)`, `gp-0x685C`, `FUN_000197D0(0x10|8)`), latched by `gp-0x3EE8`.

**Answer to "would a sensor offset or 2x scale cross a V37 threshold that stock does not?"** No hard-eligible inequality on the V37 path contains the torque cell. Torque-dependent differences between V37 and stock are all benign limits: `FUN_00036682` saturates at abs(x) = 512*32768/K, which is 18,835 counts stock and 9,415 counts V37 (the LX's full-lock 10,071 to 10,313 is above the V37 value and below the stock one: the summand goes from about 272 to the 512 clamp, +240 counts into the aggregator at full lock); `FUN_0002B62C` term 139 to 279 against 512. The torque-input inequalities that CAN trip hard are identical in stock and V37 (F3): range limit `abs(gp-0x4F60) <= gp-0x4F54`, jump limit `gp-0x4F56`, validity gates `abs(gp-0x4F60) <= 25600` (`0x6400`).

## F2. Bootloader side (below `0x13000`, not in the RWD)

- **Reset path (E, disassembly):** `0x6: jr 0x8000`; `0x8000` loads four words (`0x13010`, `0x14000`, `0x9060`, `0xA6000`), compares each with `0xFFFFFFFF`, and on the good path reaches `0x9060`, which clears registers and does `jr 0x14010` at `0x9070`. No CRC, no string, no app-valid flag. The kit's V40 statement holds.
- **Readers of the two ID strings:** LE32 and `movhi`/`movea` scans of the whole image find no reference to `0x13100`, `0x1310E` or `0x14117..0x14124` below `0x13000` (E, positive control passes). The only readers are app functions `FUN_0004F6FA` (`0x13100`) and `FUN_0004F6D6` (`0x1310E`), entries of the UDS DID table at `0xB7A00`/`0xB7A14` (neighbours carry DIDs `0xF180/F181/F186`), so they run on a diagnostic read, not at boot (E). **The identity-string falsifier holds: no boot-path reader of `0x13109`/`0x14120`.**
- **But `0x14120` is also a bootloader table byte (OPEN).** BL `FUN_00005BAA` and `FUN_00005C86` read `u16 [0x14102 + idx*6]` and `u8 [0x14104 + idx*6]` (a size and a mode per data-flash block). `idx` comes from `FUN_00005ED0`, a binary search over a 35-entry key table. For `idx = 5` the size field is the u16 at `0x14120`, bytes `2D 41`, which V37 turns into `2C 41`; records 1..6 overlay the ASCII ID block. Whether any block resolves to `idx` 1..6 is not established (the key-table base uses the BL `tp`, which I could not pin). The BL is common to both cars, so this would also hit the operator's car unless the block mix differs. Next step: resolve the BL key table, list the block ids the app requests, and read `0x14102+6*idx` for those.
- **`FUN_0000B006` (CheckProgrammingDependencies)** compares the computed CRC32 of each app block with the trailer word stored in that block, nothing else (E). Its only caller is the UDS routine at `0xB0AE`; its CRC primitive `FUN_0000AE4C` has one caller. The hardware CRC unit (`0xFF836020`) is also used by the app, only as a helper (`FUN_0006B700`/`B8F4`): NVM block CRC16 and the coding-record CRC16 below.
- **What the app checks at runtime that the RWD does not replace (E, decompile):**
  - Coding records at flash `0x1000..0x14CF` (TLV: u16 CRC16, len, tag, payload), walked by `FUN_00048A40`; bad length raises DTC 0x08 (hard-eligible), bad CRC16 sets `gp-0x348C`. Contents differ per ECU. Records in the operator's dump: tag `0x54` at `0x1180` (payload `2C` = polarity +1) and again at `0x14C0` (payload `FA` = polarity -1, processed later), tag `0xA8`, tags 1..E (sensor trims), `0x50..0x56` part numbers.
  - Data-flash NVM blocks: 18 descriptors at `0x8AF00` (stride 0x28), RAM image at `0xFEDFE000`, CRC16 over the RAM image checked by `FUN_00018F4A`, DTC 0x06 (hard-eligible) on mismatch.
- **Stock `data.bin` (de-tagged 32 KB at `0x02000000`)** holds the HW-ID: the record at about `0x1760` reads `34 00 00 00 | 54 56 43 41` with words in descending order, i.e. **`TVCA4`** (two copies). That matches the operator's measured slot 11 (E). The ID block (`39990-TVA-A110`/`A160`, words reversed) at about `0x1790` equals the flash default `0x14100..0x14127` (E: string match).

## F3. Torque chain, sensor ADC to 0x18F bytes 0-1 (E, decompile + disassembly)

1. Sensor frames (4 bytes, nibble tag 8..F) land in `gp-0x548 + ch*4` and are decoded by `FUN_000829E2`. Tag 9 gives the gain trim `sVar3 = (int8*0xCB66 >> 14) + 0x400` (range 617..1427), stored in `gp-0x506C`, and `gp-0x25D4 = (cal 0xC49B6 * 15 * sVar3) >> 11` with `0xC49B6` = 1280 (9600 at `sVar3` 1024). Tag A gives `gp-0x507C` gain and zero refs `gp-0x5064/5068`; tags B..D give temperature terms. These come from the **sensor hardware's own repeating trim stream**, not from the RWD.
2. `FUN_0007F3F8`: `d1 = gp[-0x5060] - gp[-0x5064]`, `d2 = ((gp[-0x5074] - gp[-0x5068]) * gp[-0x507C]) >> 10`; `FUN_0006AF38` (CORDIC atan2) on the temperature-corrected pair; `* gp[-0x25D4] >> 10`; `FUN_0007F300` adds `gp-0x6B66` clamped to +-308 (coding tag `0xA7`, 0 in the dump); range limit `gp-0x4F54 = (U*27)>>2` and jump limit `gp-0x4F56 = (U*15)>>1` with `U = (0xC49B6 * 2 * gp-0x506C) >> 10` (nominal U 2560, giving 17,280 and 19,200; scales with the sensor trim, 10,410..24,640 across its range). The learned-gain/offset block (`gp-0x698C` = 1024, `gp-0x6B50` = 0 at boot, gate `0xC64C3` = 0) is skipped.
3. `gp-0x4F60` is stored (dual store with `gp-0x4486`), then `FUN_0007E74A`.
4. Packer `FUN_00055C42` at `0x55C50`: `0x18F` bytes 0-1 = `-((gp-0x4F60 * 125) >> 7)` (`mulhi 0x7D`, `sar 7`, `subr`).

**Attribution of the LX's roughly 2x counts (B, not provable from the image):** the only firmware-side per-ECU factors are the sensor trim byte (gain ratio up to 2.31 between the extremes 617 and 1427 on `gp-0x506C` and `gp-0x25D4`) and the coding polarity record (sign only). Both come from the sensor or from data below `0x13000`, neither from the RWD. A 2x in counts at full lock is inside the trim range, so it can be data (sensor/coding) or driver push; the image cannot separate them. A direct readout would be `gp-0x506C` (or `gp-0x25D4`) and `gp-0x6752` from the LX.

## F4. What this does to the ranking

1. The V37 cells are still exonerated on every manual-mode path I could trace. The three monitors named in the V40 handoff (`FUN_0004595A`, `FUN_00045A20`, `FUN_00036D74`) contain no torque input and no V37 cell.
2. Two per-unit data stores that the RWD does not replace can differ between the cars and feed hard-eligible DTCs: the coding records (DTC 0x08, polarity, sensor trims) and the NVM blocks (DTC 0x06). V37 touches neither, so they explain a difference between cars only if stock also misbehaves; the working stock reflash argues against a pure data fault.
3. New lead for the identity class: BL `FUN_00005BAA`/`C86` read a size/mode table at `0x14100 + idx*6` that overlays the ID string including the V37 byte. Resolve the key table and the requested block ids first.
4. Smallest discriminating build remains the control image: stock content with only `0x13109`/`0x14120` = `,` and valid CRCs. A second control would change only `0x13109` (the copy with no BL reader) and leave `0x14120` stock; that splits the two copies.

---

# FOLLOW-UP 2026-10-05 (c): the bootloader table that overlays `0x14120`

Verdict first: **the "`0x14120` corrupts a bootloader data-flash descriptor" claim is FALSIFIED as a reachability claim.** `idx = 5` cannot be reached on any unit. The `u16` at `0x14120` is never read on this path, in stock or in V37. Method and bytes below. Ghidra stock `code.bin`; Python mirrors checked against both images.

## C1. The two functions, the base, the callers (E)

- `FUN_00005BAA(u16 id, u32 buf)` and `FUN_00005C86(u16 id, u32 buf)` are bootloader data-flash write/read request builders. Both start with `jarl 0x5ED0` (id to idx), then:
  - `0x5BBC  e6f74002  mul 6, ep, r0` (ep = idx*6)
  - `0x5BC4  2f06 00410100  mov 0x14100, r15` (a 32-bit **immediate**, bytes `00 41 01 00`)
  - `0x5BCA  cff1  add r15, ep` (ep = 0x14100 + 6*idx)
  - `0x5BD0  7168  sld.hu 2[ep], r13` (the size, = `u16[0x14102 + 6*idx]`), `0x5BD2  6460  sld.bu 4[ep], r12` (the mode byte)
  - `FUN_00005C86` is the same with `mov 0x14100` at `0x5C9E`, `sld.bu 4[ep]` at `0x5CAA`.
  - The size and mode go into the request block at `gp-0x7C28..` and `FUN_00004A6A` runs it. **The u16 is a transfer size/length, not a key, an address or a CRC seed.** Mode byte `1` selects 3, otherwise 1 (`0x5BF2`-style `cmove`).
- The base `0x14100` is genuinely the app-image address (immediate, not a mirror). The **key table** read by `FUN_00005ED0` is `ld.hu -0xAAF00[tp]` (`0x5ED2`, bytes `a5070780a2ea`) and `ld.hu -0xAAE34[tp]` (`0x5EE6`). With the **app tp `0xBF000`** (set by `FUN_00014084`) these are `0xBF000-0xAAF00 = 0x14100` and `0xBF000-0xAAE34 = 0x141CC`: the same table, 35 records of 6 bytes `{key u16, size u16, mode u8, pad}`. The bootloader's own `tp` is `0xF8000` (`0x9152`: `movhi 0x10,r0,tp; movea -0x8000,tp,tp`), which would point the key table at `0x4D100` (app code), so these services are designed to run with the app's `tp`.
- Callers: `FUN_00005BAA` is entry `0x2050` of the exported service table at `0x2040..0x2068`, `FUN_00005C86` is entry `0x2060`. Raw scan of every `ld.w disp[reg]` with disp in `0x2040..0x2068` over the whole image finds one app wrapper per used entry, and **none for `0x2060`**: `FUN_00005C86` is never called. `0x2050` has one wrapper, `FUN_000591E4` (`movhi 0,r0,r28; ld.w 0x2050[r28],r28; jmp [r28]`, bytes at `0x591EC..0x591FC`), called from `FUN_00059084`, an NVM request step (`FUN_000585C8(byte req+2)` = block number, then the write). No direct or pointer caller exists in the reset path (`0x8000`..`0x9070`) or the UDS flash path (`FUN_0000B006`/`0xB0AE`). It is the app NVM manager's "write block to data flash" service.

## C2. What `idx` can be (E, disassembly + exhaustive Python mirror)

`FUN_00005ED0` (`0x5ED0..0x5F2E`): returns `0xFFFF` if `id < key0` (`cmp r16,r6; bc`), `0xFFFF` if `id > key34` (`cmp r9,r6; bh`), `0` if `id == key0`, else a binary search over records 1..34. In **both images** `key0 = u16[0x14100] = 0x0000` and `key34 = u16[0x141CC] = 0x0000` (the table region past `0x14128` is zero), so the gate is `0 <= id <= 0`:

```python
def find_idx(img, pid):                      # TP = 0xBF000
    lo = u16(img, TP-0xAAF00); hi = u16(img, TP-0xAAE34)     # both 0 in stock and V37
    if pid < lo or pid > hi: return 0xFFFF
    if pid == lo: return 0
    ...binary search (never reached)
# exhaustive over id = 0..65535: reachable idx = {0, 0xFFFF}; results for stock and V37 identical for all 65536 ids
```

- `idx = 0`: size = `u16[0x14102] = 0`, mode = `u8[0x14104] = 0` (stock and V37).
- `idx = 0xFFFF` (every nonzero id): `ep = 0x14100 + 0xFFFF*6`, size = `u16[0x740FC] = 0x6806`, mode = `u8[0x740FE] = 0x30` (same in both images).
- **`idx = 5` is unreachable on every unit**: the gate uses table bytes inside the RWD (identical on both cars), not a stored record, a coding TLV, the HW-ID or an NVM block count. The requested id (the NVM block number) never matters, because both outcomes are decided before any record 5 access. A unit-to-unit difference cannot change this unless its flashed `0x14100`/`0x141CC` bytes differ, which they cannot after a flash of the same RWD.

Per-record values `u16[0x14102 + 6*i]`, stock vs V37 (E, Python):

| i | address | key u16 | size u16 stock | size u16 V37 | mode | bytes |
|---|---|---|---|---|---|---|
| 0 | 0x14100 | 0x0000 | 0x0000 | 0x0000 | 0 | `00 00 00 00 00 00` |
| 1 | 0x14106 | 0xA100 | 0x3330 | 0x3330 | 0x39 | `00 a1 30 33 39 39` |
| 2 | 0x1410C | 0x3039 | 0x542D | 0x542D | 0x56 | `39 30 2d 54 56 41` |
| 3 | 0x14112 | 0x412D | 0x3131 | 0x3131 | 0x30 | `2d 41 31 31 30 33` |
| 4 | 0x14118 | 0x3939 | 0x3039 | 0x3039 | 0x2D | `39 39 39 30 2d 54` |
| 5 | 0x1411E | 0x4156 | **0x412D** | **0x412C** | 0x31 | `56 41 2d 41 31 36` |
| 6 | 0x14124 | 0x0030 | 0x0000 | 0x0000 | 0 | `30 00 00 00 00 00` |
| 7 | 0x1412A | 0xFFFF | 0x0000 | 0x0000 | 0 | `ff ff 00 00 00 00` |

Only record 5 differs, as stated.

## C3. What the u16 does and what a mismatch would do (E for structure, B for consequence)

It is a size passed to the data-flash driver, not a key matched against a stored value, so there is no key-mismatch DTC on this path. The NVM DTC 0x06 I named earlier comes from a different check (CRC16 over the RAM image of the block, `FUN_000193F0`/`FUN_00019482`/`FUN_00018F4A`), which does not read `0x14120`. Since `idx = 5` is unreachable the size at `0x14120` is never consumed.

## C4. Does the table look like a descriptor table? Cross-check with `data.bin` (E)

Records 1..6 are the ASCII ID block (`\0\xa1 03 9990-TVA-A110 39990-TVA-A160`), not `{key, size, mode}` data: keys `0xA100`, `0x3039`, `0x412D`, `0x3939`, `0x4156` are letter pairs, unsorted, and none is a block id of the NVM manager (descriptors `0..17`). The same 40 bytes are NVM block 2's default image (descriptor at `0x8AF50`: size `0x28`, `+0x18` source `0x14100`), and stock `data.bin` holds the same string block (words in descending order) near `0x1790`. So `0x14100..0x14127` is a data block that the bootloader's key-table address happens to cover while the table proper (35 records) is **empty (zero keys) in this app image**. I found no code that reads the descriptor `+0x18` field (candidate NVM functions scanned for `ld.w` with disp `0xC`: only a request-struct field), so even the block-2 default copy is not consumed by anything I located (B).

## C5. Verdict and the control image

- "`-`→`,` at `0x14120` corrupts a bootloader data-flash descriptor on units that reach idx 5": **falsified** (E: gate bytes `0`/`0`, exhaustive 65536-id mirror, no wrapper for `0x2060`, single wrapper for `0x2050` in app context). The identity-string class now has **no boot-path or service-path reader of either byte**; the only readers are the DID `0xF181`-class diagnostic reads.
- Control image: V37 with `0x13109` and `0x14120` back to `0x2D`. V37 differs from stock below `0xC4FFC` in exactly those two bytes, so the code block `[0x13000,0xC4FFC)` becomes **byte-identical to stock and its trailer returns to stock `75 49 f2 48`** (the recomputed CRC equals the stock value; verify with `verify_bootloader_crc.walk`). That image is bit-equivalent to stock everywhere except the cal block `0xC5000-0xC6FFF` and its trailer. On the table path it is bit-equivalent to V37 as well (the byte is unread), so a failure of that image would not be explained by this table. If it still fails on the LX, the string pair is exonerated and the cause is in the cal block cells; if it boots, the string pair (read only by diagnostic DIDs, or by a tool-side identity check) is the discriminator.

## C6. Limits

`FUN_00004A6A` (the driver that consumes the request) was not decompiled; the claim "size is a transfer length" rests on the request layout (`gp-0x7C22` size, `gp-0x7C1C` mode) and the services' names, not on the driver body. Indirect calls through the `0x2040` table by computed index would not show in my displacement scan, but no indexed access to that table exists in the image. The `idx = 0xFFFF` case reads `0x740FC/0x740FE` (app code bytes, unchanged by V37).
