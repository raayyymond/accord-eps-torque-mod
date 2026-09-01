---
name: reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells
description: FUN_00028ea6 already stores 9 of its internal PID quantities (setpoint, error, clamped P, clamped D, I accumulator, pre-clamp sum, post-clamp sum, post-ramp, final) to gp cells nothing on the bus reads -- so every clamp's binding flag is FREE (exact equality to the cal) and any term reaches CAN 427 in a 3-byte edit. Also corrects two STATE.md claims: 0xC61B2 is NOT a clamp in this loop (it lives in FUN_0002b422), and the ld.h sign-extension defect exists on 0xC61B4 and 0xC61B2 too, not only 0xC61BE.
metadata:
  type: reference
---

# The rate PID publishes almost all of itself. Traced 2026-09-01 (GhidraMCP + Python, stock `code.bin`).

`gp=0xFEDF8000`, `tp=0xBF000`. Method: Python enumeration of every gp-relative store in
0x28EA6-0x2A93A (disp16 decoder, opcode = hw1 bits 6-10, `0x3B`=st.h/st.w by hw2 bit0, `0x3E`=st.b),
each hit then read back with `disassemble_bytes(dry_run:true)`.

## The published state [EVIDENCE]

```
0x29D72  st.h r16 -> gp-0x6a32   rate SETPOINT (map output, before the x32)
0x2A18C  st.w r16 -> gp-0x6cf8   the ERROR E = 32*setpoint - feedback   (32-bit; 0x7FFFFFFF = invalid)
0x2A188  st.h r29 -> gp-0x6b32   CLAMPED P   (r29 <- r9 @0x29E96; r9 is the 0x71BC clamp result)
0x2A19C  st.h r27 -> gp-0x6b36   CLAMPED D   (r27 <- r8 @0x29F2E; r8 is the 0x71B6 clamp result)
0x2A190  st.w r24 -> gp-0x6dd0   I accumulator (inert, Ki 0xC63E6 = 0)
0x2A1A2  st.h r22 -> gp-0x6b34   PRE-CLAMP SUM (I>>7 + P + D)   (r22 <- r2 @0x29F2A)
0x2A17C  st.h r12 -> gp-0x6b2e   post-taper, post +-0xC61BE clamp
0x2A206  st.h r9  -> gp-0x6b30   after 2nd lag + hysteresis gate + gp-0x69b0 engagement ramp
0x2A23C  st.h r1  -> gp-0x6b38   FINAL, post +-0xC61B4 clamp
```
Residual: liveness of r22/r27/r29 between assignment and store was NOT swept (assignment and store
each read directly; the fail-path zeroing at 0x2A164-0x2A172 groups them consistently).

## Consequences

* **Every clamp flag is free.** Post-clamp cell exists ⇒ "clamp binding" is exact equality to the
  cal constant. No cave, no flag bit, no code edit, for `0xC61BC` / `0xC61B6` / `0xC61BE` /
  `0xC61B4` / `0xC61BA`.
* **`0xC62E6` (feedback clamp) is the ONE exception** — the clamped value lives only in `r26`
  (`r26 = state_prev + state_new`, `0x28FA4`); `0x28FA8 st.w r9,-0x3d30` stores the lag STATE, not
  the clamped sum. Infer its duty offline instead: the lag's DC gain on `gp-0x6a56` is ~30.9, and
  `gp-0x6a56` is already on CAN 399 bytes 2-3 at full 16-bit/100 Hz.
* **Any of these reaches the wire in 3 bytes** — 2 for the disp16 at `0x55DF2`, 1 for the `sar`
  immediate at `0x55E10` (`sar imm5,r6` = halfword `0x32A0|imm`, so the byte is `0xA0|imm`).
  Wire = `clamp(min(|cell|,0xFFFF)*5 >> imm, 0, 1023)`, RECTIFIED (`FUN_00049a5a` = abs).
  Scale picks: `gp-0x6b32`/`gp-0x6b2e` -> `0xA7`; `gp-0x6b34` -> `0xA8`; `gp-0x6b38` -> `0xA4`.

## 🛑 Two corrections to STATE.md's decision box [EVIDENCE, two methods]

1. **`0xC61B2` is not a clamp in this loop.** `search_instructions(operand "0x71b2")` = 5 hits, all in
   `FUN_0002b422` (0x2B42A/0x2B436/0x2B43C/0x2B446) and `FUN_0002b57a` (0x2B5B6) — **none** in
   `FUN_00028ea6`. `0x71b4` has exactly the 4-read symmetric-clamp idiom at 0x2A1F8/0x2A20C/0x2A212/
   0x2A21C. Corroborated by the Python store/load enumeration above. ⇒ the PID output clamp is
   **symmetric ±cal(0xC61B4)**, and treating 0xC61B2/0xC61B4 as a pair is wrong (harmless only while
   both are 3072).
2. **The `ld.h` sign-extension defect is not unique to `0xC61BE`.** `0x2A20C ld.h 0x71b4,tp,r11`
   (`255fb471`) is the positive-overflow branch of the `0xC61B4` clamp — same shape. `0xC61B2` has it
   at `0x2B436`. ⇒ **`0xC61B4` also carries the hard cap "< 32768"**, and STATE.md names it as the
   next cell to raise. Re-verified clean (all `ld.hu`): `0x71BC` 4/4, `0x71B6` 4/4, `0x72E6` 3/3,
   `0x71BA` 1/1.

Also: `0xC6CD0` is **65535** in stock `code.bin` (5346 only from V112 on); `0xC61B2`/`0xC61B4` are
**512** stock, 3072 in V268/V273. Verify modded values against the modded image.

## Related
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] — the loop structure this extends.
[[reference_accord_variant_record_table_0xcd012_full_dump]] — the selector table the same session dumped.
[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] — the tap-site menu.
