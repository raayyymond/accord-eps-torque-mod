---
name: reference_accord_can399_0x18f_10bit_telemetry_channel_and_6ada_gate1
description: CAN 399/0x18F (FUN_00055c42, hook 0x55D50) has 10 usable bits at 100Hz for a NEW telemetry channel, byte-exact this session -- 6 clean (byte4[2:0]+byte5[7:6]+byte6[6]) plus 4 more (byte5[3:0]) that are SAFE to reclaim because the hook fires AFTER Honda's own explicit clear of that nibble, not before -- a strictly better target than CAN 427/0x1AB (DLC=3, already carries a rectified 10-bit gp-0x6b86 dose payload, 50Hz) for widening telemetry. Also carries the full 4-method GATE-1 census confirming gp-0x6ada/gp-0x6adc are still exactly 1 writer / 0 readers each.
metadata:
  type: reference
---

# CAN 399/0x18F telemetry channel design + gp-0x6ada/gp-0x6adc GATE-1 (2026-08-22, `deadband` session,
team-lead's "solve the telemetry channel for the C61F6-candidate follow-up" task)

## 399/0x18F byte map, fresh `decompile_function(0x55c42)` this session, `code.bin` stock

Hook `0x55D50` = the `movea -0x1420,gp,r6` immediately before the checksum call at `0x55D5A`
(`FUN_00057b24(gp-0x1420,7,399)`) -- same proven pre-checksum-jarl hook shape as `0x14A`'s `0x55C0E`
(2+ flown builds) and `0x1AB`'s `0x55EFA`, per `[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]]`.
Base = `gp-0x1420`, DLC=7 (bytes 0-6):
```
byte0-3 (gp-0x1420..-0x141D): tq + steer_angle_rate, 2x 16-bit, via FUN_000218be/FUN_000218de
byte4 (gp-0x141C): bit3=gp-0x6806(engaged) | bits[7:4]=gp-0x6807 | bits[2:0] UNTOUCHED -- 3 clean bits
byte5 (gp-0x141B): bits[5:4]=gp-0x6880&3 (LIVE -- matches the existing on-file correction, do NOT use) |
                   bits[3:0] `&0xf0` explicit unconditional clear, no OR term | bits[7:6] UNTOUCHED -- 2 clean bits
byte6 (gp-0x141A): bit7=gp-0x6804 | bits[5:4]=rolling counter | bits[3:0]=checksum nibble | bit6 UNTOUCHED -- 1 clean bit
```
6 clean bits (byte4[2:0]+byte5[7:6]+byte6[6]), confirmed first-hand, exactly matching the 2026-08-07
memory's count. Never touched by any build -- narrow grep on `55D50`/`gp-0x141` (not the bare `0x18F`
CAN-ID string, which false-hits many unrelated docstrings/route-decoders) across all `build_v*_tva.py`
finds zero edits.

## 🛑 NEW: the byte5[3:0] "mask-edit tier" is SAFE, not elevated-risk -- the hook runs AFTER Honda's own clear

`0x55D50` sits at the very END of `FUN_00055c42` -- 10 bytes before the checksum call, i.e. it fires
*after* every one of Honda's writes above, including byte5's explicit `&0xf0` clear. A cave stub hooked
there can simply OR its own value into byte5[3:0] *after* Honda's clear has already run -- no edit to
Honda's own clear instruction needed, same append-only reload-mask-OR-store idiom as the other 6 bits.
**That reclaims all 4 of those bits at the same safety tier as the clean 6**, giving **10 usable bits
total**, not 6 -- corrects the 2026-08-07 memory's "elevated risk, ship the clean tier first" framing,
which predates this ordering observation.

## 427/0x1AB -- tight and already carrying the dose payload, BUT has 5 free bits, not ~0

Fresh `decompile_function(0x55d80)`. DLC=**3** (24 bits total). Magnitude chain
`FUN_00049a5a`->`FUN_00049a78`->`FUN_00049a90(v,0,0x3ff)` clamps to **[0,1023], a 10-bit UNSIGNED range**
-- confirms it is genuinely RECTIFIED (floor-clamped to 0, sign destroyed regardless of source) and
already carries `gp-0x6b86` (V104's dose instrument, per `builds/v80_v107/build_v104_tva.py`'s 427 repoint, 2-byte
displacement edit at the packer's source read, NOT the same mechanism as the `0x55EFA` hook). Rate
**50Hz confirmed** (cadence-2 gate visible: `FUN_00046ea6(3)`/`(4)`/`(10)` triple in the decompile).

🛑 **UPDATE, same session, `loop-topology` cross-task follow-up**: decompiled `FUN_00021864` (the function
that actually places the 10-bit clamped magnitude into the buffer) -- `*(char*)(gp-0x13cb)=param_1&0xff`
(byte1, fully consumed) + `*(byte*)(gp-0x13cc) &= 0xfc | (param_1>>8)&3` (byte0 bits[1:0], top 2 magnitude
bits). Combined with the earlier byte0/byte2 trace: byte0 = bit7(boot-time-fixed config flag, written at
most once ever, via an init-once `gp-0x2f67` guard) + bit4(`gp-0x685a`) + bit3(`gp-0x685b`) +
bits[1:0](magnitude top bits) -- **bits[6:5] and bit2 genuinely untouched = 3 free bits**. byte2 =
bits[5:4](rolling counter) + bits[3:0](checksum) -- **bits[7:6] genuinely untouched = 2 free bits**.
**Total 5 free bits on 427 today, post-V104-repoint** -- corrects both my own "not fully resolved" framing
above and the pre-repoint 2026-08-07 memory's stale "3 bits" figure (byte0[6:5]+byte2[7] only). Same safe
append-only property as 399: the `0x55EFA` hook sits immediately before the checksum call
(`FUN_00057b24(gp-0x13cc,3,0x1ab)`), i.e. after every one of Honda's writes traced above, so a cave stub
there can OR into these 5 bits with zero edits to Honda's own instructions.
**Verdict, revised**: still worse than 399 for a wide/precise channel (DLC=3's tightness, 50Hz, and the
already-claimed 10-bit dose payload stand), but no longer "essentially nothing" -- 5 bits at 50Hz is a
real, small, usable resource, and became the deciding tiebreaker in a cross-task budget conflict with
`loop-topology`'s V106 MODEL-vs-plant validation build (see
[[reference_accord_can399_0x18f_10bit_telemetry_channel_and_6ada_gate1]]'s own message log / team-lead
thread, 2026-08-22): **recommended split is MODEL (`gp-0x6bfc`, their REQUIRED item) -> `0x18F`'s 10 bits
(9-bit mag+sign, `>>6` shift quantizer, LSB=64ct=0.32% of their ±20000 range, codes 313-511 reserved
as an explicit sentinel marker for their `0x7FFF` invalid-frame value -- do NOT let it alias into a
clamped "large real value" code); `gp-0x6ada` (this task) -> `0x1AB`'s 5 bits (4-bit mag+sign, `>>9`
shift quantizer, LSB=512ct=6.25% of ±8192, clamp at code 15 for the single edge case `x=+-8192` exactly).
This exhausts the ENTIRE remaining whitelisted-CAN telemetry budget across all 3 gateway-crossing IDs --
confirmed structural ceiling, nothing left to widen into for any future ask. `gp-0x6b98` magnitude
(loop-topology's "wanted not required") does not fit anywhere in this allocation.

## Proposed multi-bit design for gp-0x6ada (not a comparator -- team-lead's explicit requirement)

`gp-0x6ada` clamped +-8192 (confirmed prior session). Shift-only quantizer, no multiply/divide:
```python
mag9 = min(abs(gp_0x6ada) >> 4, 511)   # 9-bit magnitude, 16-count LSB
sign1 = gp_0x6ada < 0                   # 1 bit
```
Proposed bit placement: `byte5[3:0]`=mag9[8:5], `byte5[7:6]`=mag9[4:3], `byte4[2:0]`=mag9[2:0],
`byte6[6]`=sign1. **Two-tier**: Tier 1 = clean 6 bits only (5-bit mag + 1 sign, 32 levels, ~256ct LSB,
zero new risk classification); Tier 2 = add the 4 byte5[3:0] bits for the full 9-bit/512-level version.
`gp-0x6adc` (r26) does not fit alongside r24 in the same 10 bits at useful resolution -- recommended
r24-only for this pass (it's the cell the pump-vs-damp question hinges on), r26 as a follow-on.

## Sample-rate / phase feasibility at 100Hz for a 21-23Hz line

43% of the 50Hz Nyquist -- no aliasing risk for this band. "~4.6 samples/cycle" is the right caution for
*single-cycle* timing precision (marginal) but the actual need is a coherence+phase estimate accumulated
over a full burst (7-14+s = ~150-300 cycles per the duty tables) -- an ordinary cross-spectral computation
at this rate/duration, answerable. gp-0x6ada itself updates at 1kHz and gets point-sampled (not
integrated) at the 100Hz packer -- a clean ZOH sample for a sub-Nyquist band, not an aliasing source.
🛑 **Mandatory pre-flight check before trusting any phase number from this channel**: `accord-raw14-offbyone-in-every-cache`
(top-level memory) records a real prior incident where pairing a captured value with the wrong timestamp
column cost 28° of spurious phase at 7.79Hz. The cave-write-vs-CAN-tick alignment for THIS channel needs
the same scrutiny before any phase/coherence result off it is trusted.

## 0x14A byte4[2:0] re-confirmed Honda's own, first-hand [supersedes nothing, corroborates the existing V103 retraction]

Fresh `decompile_function(0x55a98)`: bit2 = `gp-0x6799`&1 UNCONDITIONAL; bits[1:0] = `gp-0x679b`/`gp-0x679a`
on the normal (`gp-0x67fa!=8`) branch. On the rare `gp-0x67fa==8` branch, bits[1:0] of the CAN buffer are
left UNWRITTEN by this function (stale from the previous cycle) rather than being written by anything
else -- still not free either way. Matches team-lead's correction exactly; b6 (`|gp-0x6ada|>=|gp-0x6adc|`
comparator, reads 0.000000 across 65,959 frames per team-lead) is a legitimate reclaim candidate on its
own terms, but **unnecessary given 399 offers 6-10 clean bits at 2x the rate with zero payload conflict**
-- recommended leaving V103's five bits untouched and building on 399 instead.

## GATE-1 census, full 4-method standard, fresh this session

Wrote a scan reusing `analysis-2020accord/studies/sessions/v70/v70_gp683c_writer_census.py`'s exact encoding logic (disp16
per-opcode rules, disp23 6-byte extended form, LE32 absolute-literal, movhi/movea pair) against
`stock_fw_dump/code.bin` (1,048,576 bytes), via `C:/Users/dudei/anaconda3/envs/bin_decompile/python`:
```
gp-0x6ada (0xFEDF1526): disp16=1 disp23=0 LE32=0 movhi/movea=0 => 1 WRITER (0x3AD5A st.h), 0 READERS
gp-0x6adc (0xFEDF1524): disp16=1 disp23=0 LE32=0 movhi/movea=0 => 1 WRITER (0x3AD4E st.h), 0 READERS
```
All 4 methods agree, nothing to adjudicate. Residual (same ceiling as every static GATE-1 pass in this
kit, explicitly the `gp-0x1500` failure class): does not rule out a computed pointer built by arithmetic
on some other base landing on this address at runtime; no available tool closes that further from a
trace-only pass.

## Related
[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] -- the 2026-08-07 hook-site
table and spare-bit budget this session re-verifies byte-for-byte and extends (the byte5[3:0]-is-safe
finding, the exact 427 magnitude-chain trace).
[[reference_accord_v103_byte4_free_bits_and_clip_flag_cave_design]] -- the 0x14A byte4 retraction this
session's fresh `0x55a98` decompile independently corroborates.
[[reference_accord_c61f6_deadband_is_coulomb_friction_not_percentage]] -- the prior finding this telemetry
channel is designed to resolve (gp-0x6ada's real burst-time magnitude and its sign relative to the mode).
