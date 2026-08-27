---
name: reference-accord-databin-tp-base
description: "⚠⚠ tp BASE SUPERSEDED 2026-05-26: application tp(r5) = 0xBF000, NOT 0xF8000. Bootloader sets 0xF8000 @0x9152 but the EPS APPLICATION re-sets tp=0xBF000 @0x140ce (FUN_00014084). All steer-torque code runs under the app, so every tp+offset scalar-cal read is at 0xBF000+off (the PROGRAMMED 0xBF000-0xC6FFF region), NOT 0xF8000+off (erased). THERE IS NO ABSENT CAL PARTITION. Real values: gain tp+0x746c=0xC646C=891; clamps tp+0x71b2/b4=0xC61B2/B4=512. The whole 'tp=0xF8000 / absent partition / gain=-1' framing is RETRACTED. (Also superseded earlier: the data.bin overlay model — data.bin is 32KB real flash at 0x02000000-0x02007FFF, doubled-with-tags; de-tag via strip_data_tags.py.)"
metadata:
  node_type: memory
  type: reference
---

> Source artifact: `../accord-firmware/analysis-2020accord/stock_fw_dump/data.bin`.

> ## ⚠⚠ CORRECTION (2026-05-26 eve) — `tp = 0xBF000`, NOT `0xF8000`; NO absent partition
>
> The load-bearing `tp(r5)=0xF8000` claim below (and everywhere it propagated) is WRONG. `0x9152` is the **bootloader** tp; the EPS **application re-sets tp** at `FUN_00014084`:
> `0x140c0 ori 0x8000,r0,r1` → `0x140ce movhi 0xb,r0,tp; 0x140d2 movea 0x7000,tp,tp; 0x140d6 add r1,tp` ⇒ **`tp = 0x000BF000`** (same routine derives `gp=0xFEDF8000`, matching all usage). All steer-torque code runs under the application, so every `disp[tp]` resolves to **`0xBF000+disp`** — the **programmed** `0xBF000–0xC6FFF` cal region, present in this dump — NOT `0xF8000+disp` (erased).
> - **THERE IS NO "absent `0xF8000+` calibration partition."** That conclusion, and every downstream claim built on it ("blank-in-both → absent from dump", "gain = `0xFFFF` = −1", "arb output ≈ 0", "high-end cap lives in an absent partition / source it from the `.rwd`"), is an artifact of the wrong base and is **RETRACTED**.
> - **Verified real cal values (read at `tp=0xBF000`):** LKAS output **gain `tp+0x746c` = `0xC646C` = 891 (`0x037B`)** — the true high-end LKAS-torque binder, missed by all prior analysis; **arb output clamp `tp+0x71b4` = `0xC61B4` = 512**; **limit&pack clamp `tp+0x71b2` = `0xC61B2` = 512**; pre-output sat `tp+0x71b8`=`0xC61B8`=102; integrator gains `tp+0x73e2/e4/e8`=`0xC63E2/E4/E8`=31/634/923.
> - **2× recipe (flashable `.rwd` cal):** gain `0xC646C` 891→1782, clamps `0xC61B2`/`0xC61B4` 512→1024. Downstream code clamps (mixer ±0x2800, shaper ±0x2000, FOC ±8192) have headroom (LKAS contribution is modest, not motor-scale) — verify via CAN 0x427 motor-torque telemetry.
> - **NOTE:** an earlier edit *this same session* "re-confirmed tp=0xF8000 from startup 0x9152" — that was the bootloader value and is itself superseded by this. See [[project-accord-torque-mod-v0]] and [[reference-accord-lkas-window-ceiling]] for the corrected build/ceiling layer.
>
> *Everything below this line is preserved for the record but reads cal at the WRONG base.*

> ## ⚠ CORRECTION (2026-05-25) — the data.bin model in this memory is WRONG
>
> Everything below was written on a misunderstanding of `data.bin`. The corrected facts (operator-supplied base + tag structure verified by `analysis-2020accord/strip_data_tags.py`):
>
> - **`data.bin` is 32 KB of real flash at `0x02000000–0x02007FFF`** — NOT a 64 KB overlay of `0xF0000–0xFFFFF`. On the µPD70F35xx (Renesas/NEC V850) family `0x02000000` is the **data-flash** region, which fits "adaptation / learned values" far better than "code-flash calibration window."
> - **It is stored *doubled* on disk (64 KB):** each 4-byte data word is followed by a 4-byte **tag word** that reads `0xFFFFFFFF` (erased) or `0x00000000` (written/valid) — verified uniform across all 8192 units, zero exceptions. De-tag → clean 32 KB with `strip_data_tags.py`.
> - **Therefore `data.bin[addr - 0xF0000]` is meaningless** on two counts: wrong base, AND the raw on-disk offset interleaves real bytes with tag bytes (any read crossing a 4-byte boundary mixed the two). The "21,483 / 33% non-FF, populated span `0xF0010–0xFF02B`, tiny 8-byte islands" stats below are **artifacts of reading the tagged stream** (the 8-byte islands were exactly data-word+tag-word pairs; the FF fraction was inflated by the `0xFFFFFFFF` tags).
> - **Probably-wrong inferences that depended on this (flag, do not trust without re-derivation against the de-tagged 32 KB at `0x02000000`):** the two "data.bin FILLS / code.bin FILLS" bullets; the commutation-table-at-`0xF52C0`-is-in-data.bin claim; any "table real in data.bin at `0xFxxxx`" identification.
> - **What still holds:** the `tp (r5) = 0xF8000` calibration-base finding and the `gp`/`ep` bases are pure `code.bin` disasm and are **unaffected**. The "FF in BOTH files → absent from dump" conclusions retain only their **`code.bin` half**; the `data.bin` half compared a region `data.bin` does not even cover, so "absent from dump" for `0xFD8C8`/`0xFE0xx` now rests on `code.bin` alone (still plausible, but no longer corroborated by data.bin).
> - The **semantic role** of the de-tagged 32 KB (data-flash adaptation store? cal mirror?) is NOT yet re-established. Don't just swap the base — the table IDs below need redoing.
>
> *Original (uncorrected) text preserved below for the record.*

The 2020 Accord (TVA / V850, µPD70F3508, LE) firmware is **two flashed partitions**: `code.bin` (1 MB, loaded flat at 0x0) **and** `data.bin` (64 KB). **`data.bin` overlays flash `0xF0000–0xFFFFF`** (the `tp`-relative window) but is a **SPARSE overlay** — 21,483 non-FF bytes concentrated below `0xFC000`; `0xFC000–0xFF000` is ~all FF with tiny 8-byte islands. The real flash for that window = `code.bin ⊕ data.bin` merge (use whichever is non-FF), but **even merged it has holes**. Verified:
- `code.bin[0xF52C0]`=`FF…` but `data.bin[0x52C0]`=`01 00…78 dc` → data.bin FILLS this slot (commutation table, indexed `tp-0x2d40`).
- `code.bin[0xFD000]`=`00 60 0C 00…` (descriptor → `0xC6000`) but `data.bin[0xD000]`=`FF` → code.bin FILLS this one.
- **`0xFD8C8`/`0xFE084` (live control + motor params) = `FF` in BOTH** → absent from the dump.
- Always check BOTH files at `addr` (code) and `addr-0xF0000` (data) before concluding a slot is "erased"; blank-in-both ≠ erased-in-ECU.

**`tp` (r5) = `0xF8000`** is the global calibration base, set at startup `0x9152` (`movhi 16,r0,tp; movea -0x8000,tp,tp`). `gp`(r4)=`0xFEDF8000` (RAM small-data), `ep`(r30)=`0xFEDF4308` (RAM). So `disp[tp]` = calibration flash reads (e.g. `0xFD000`, `0xF29F8` carry real data); `disp[gp]`/`disp[ep]` = RAM working vars. This re-confirms the [[reference-clarity-civic-plus28]]-style "tables are base-relative" pattern but for V850.

**CORRECTED interpretation of blank-in-both (a hypothesis was retracted here):** `tp`(r5)=`0xF8000` is **verified never reloaded** in the motor/steering cluster `0x60000–0x6E000` (full-cluster scan: zero `tp` writes), so `disp[tp]` reads resolve against flash `0xF8000`. When a `tp`-relative slot reads `0xFF` in BOTH files, the correct conclusion is **"value absent from this dump"** (the `0xF8000+` control-cal partition is not fully captured here, and `data.bin` is sparse) — **NOT** "runtime-RAM / `r5` reused as a RAM base." An earlier turn wrongly hypothesized a RAM working-set base from blank-in-both reads (e.g. `tp+0x597e`, the control-param block `0xFD8C8–0xFE189`); that is **retracted** — those are flash addresses whose values our dump lacks. (Also: don't trust a tp-offset value without confirming the exact address — a wrong-address read of `data.bin[0x80A0]`=`13 00` once produced a bogus "handler index 0x13"; the correct slot `0xF0120` is blank.)

Found via lightweight scripting over the raw `.bin`s per [[feedback-lightweight-inspection-over-ghidra]]; complements [[reference-rizin-ghidra-v850-quirks]].
