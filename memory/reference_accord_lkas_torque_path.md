---
name: reference-accord-lkas-torque-path
description: "Accord TVA LKAS steering-torque path, Ghidra-traced end to end: CAN 0xE4 STEERING_CONTROL (DBC-verified) -> FCN0 mb54 -> staging 0xFEDF68CC; motor emit FUN_0006c5ce -> TSG20 CMPU/V/W 0xFFFFCCB0/B4/B8 via ADC-ISR control law. Both ENDS verified; the CAN->control routing + the exact torque setpoint are the two open gaps (runtime-RAM routing)"
metadata:
  node_type: memory
  type: reference
---

End-to-end trace of the LKAS steering-torque command path on the 2020 Accord (TVA / V850). Both endpoints are Ghidra-verified; the two interior links are bounded open gaps.

**① CAN INPUT [VERIFIED + opendbc-cross-checked].** Inbound `STEERING_CONTROL` = **CAN ID 0xE4 (228), DLC 5**; `STEER_TORQUE` = **signed 16-bit, bytes[0:1] big-endian, range ±4096** (opendbc `_bosch_2018.dbc`; Accord 2018-22 → `honda_civic_hatchback_ex_2017` DBC, per `opendbc/car/honda/values.py` `HONDA_ACCORD`). The EPS is the DBC's `EPS` receiver, so 0xE4 is inbound — consistent with it landing on a **receive** mailbox. CAN controller = **FCN0 @ 0xFF488000**; `FUN_0001cf30` (`0x1cf30`) programs MID filters from table A `0xF033C` (data.bin) + table B `0xB733C` (code.bin); 0xE4 filter entry at `0xB7394`. → RX mailbox 54. **⚠ 2026-05-25:** the "table A `0xF033C` (data.bin)" attribution is **probably wrong** — `data.bin` does not map to `0xF0000` and was read as a tagged/doubled stream (see [[reference-accord-databin-tp-base]] CORRECTION). Table B `0xB733C` and the `0xB7394` filter entry are `code.bin` and stand.

**② RX EXTRACTION [VERIFIED].** Poll `FUN_0001df5c` → `FUN_0001df1c` → extractor `FUN_0001ce68` stages 8 data bytes to RAM **`0xFEDF68CC`** (STEER_TORQUE = `*(int16_t be*)0xFEDF68CC`).

**③ DISPATCH [mechanism verified; specific route is RUNTIME-BOUND — GAP 1].** `FUN_0001ddd0` dispatches: diagnostic msgs (handler-index 0x17-0x2A) via fn-ptr table `0xB73FC` → handlers `0x1FA92`/`0x21xxx` (NOT LKAS); other msgs are frame-copied to a per-index dest RAM buffer. The mb54→handler/buffer mapping lives in RAM routing tables built at runtime (claimed "blank in both partitions" — ⚠ the `data.bin` half of that check is invalid post-2026-05-25, see [[reference-accord-databin-tp-base]] CORRECTION; the conclusion still holds on the independent grounds below), and `FUN_0001cf30` only sets HW MID filters, not these tables. So the steering consumer **cannot be named from the static image**.

**④ CONTROL LAW [loop verified; exact torque var NOT pinned — GAP 2].** ADC-complete ISR **`FUN_0006404c`** (`0x6404c`, INTADCA0I1, EIIC=0x600) reads phase currents, runs `FUN_0006428e→FUN_00065afe→FUN_000711f8→FUN_00071272→FUN_000710d4`, producing d/q setpoint / phase duties in RAM (`gp-0x2bf0/-0x2be0/-0x2bd0`). The dispatched steering torque enters here; the exact read instruction is inside the `FUN_00065afe` chain (not decompiled through).

**⑤ MOTOR OUTPUT [VERIFIED].** Carrier-valley ISR **`FUN_0001492a`** (`0x1492a`, INTTSG20IVLY, EIIC=0x970) → `FUN_00061614` (`0x61614`) → **`FUN_0006c5ce`** (`0x6c5ce`) writes 3-phase duties (÷51200.0 scale, period-clamp) to **TSG20 CMPU/CMPV/CMPW = `0xFFFFCCB0`/`B4`/`B8`** (TSG2 base1=0xFFFFCC00; init `FUN_0006c446`). The commutation table at `tp-0x2d40`=`0xF52C0` is real **in data.bin**. **⚠ 2026-05-25: probably wrong** — this used the bad `data.bin`=`0xF0000` mapping on a tagged/doubled file; `data.bin` is 32 KB at `0x02000000`, so a `0xF52C0` table cannot be located in it as stated. Re-derive against the de-tagged image. See [[reference-accord-databin-tp-base]] CORRECTION.

**To close the gaps:** (1) find the init code that POPULATES the RAM routing tables (mb→handler/buffer registration), or do dynamic RAM/CAN capture on a bench; (2) decompile the `FUN_00065afe` chain for the torque setpoint. The flash/CRC/calibration-validation layer (`0x8AD6C` pointer table → block `0xC6000`, `FUN_0001c7c8` flash programmer, `FUN_00027802` range-validator) was investigated and **ruled OUT** as the torque path — it is integrity/update code.

Method: parallel single-goal agents per [[feedback-tight-agent-briefs]]; lightweight `.bin` scripting + Ghidra xrefs per [[feedback-lightweight-inspection-over-ghidra]]. Architecture-map §10.1 holds the same map.
