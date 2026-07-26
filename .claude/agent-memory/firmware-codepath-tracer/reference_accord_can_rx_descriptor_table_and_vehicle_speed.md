---
name: accord-can-rx-descriptor-table-and-vehicle-speed
description: A160 CAN RX descriptor table @0xBB550 (19 records: ID/buffer/handler) + the vehicle-speed ingest from CAN 0x158 bytes 4-5 into gp-0x6a46 in km/h x 64; also pins gp-0x1500 as the CAN 0x326 RX buffer.
metadata:
  type: reference
---

**The A160 CAN RX plumbing has THREE parallel structures. The descriptor table is the authoritative one.**

## 1. Descriptor table @ `0xBB550` — 19 records, stride `0x20` (disasm+literal verified)
Layout: `[+0]` u16 enable(0/1) · `[+2]` u16 **CAN ID** · `[+4]` u32 · `[+8]` u32 **dest buffer** ·
`[+0xC]` u32 len-mask (0x0F/0x08) · `[+0x10]` u32 **handler fn ptr** · `[+0x14]` seq idx 1..19 · `[+0x18]` group.

| ID | buffer | gp-rel | handler | en |
|---|---|---|---|---|
|0x158|0xFEDF6BF0|gp-0x1410|`FUN_000522FE`|1|
|0x13C|0xFEDF6B08|gp-0x14F8|`FUN_00052452`|1|
|0x130|0xFEDF6B10|gp-0x14F0|`FUN_00052414`|1|
|0x17C|0xFEDF6BE8|gp-0x1418|`FUN_000524BC`|1|
|0x1DC|0xFEDF6C00|gp-0x1400|`FUN_000527DA`|1|
|0x324|0xFEDF6BA0|gp-0x1460|`FUN_000525B8`|1|
|0x328|0xFEDF6B98|gp-0x1468|`FUN_00052608`|1|
|**0x0E4** (LKAS)|0xFEDF6BD8|gp-0x1428|`FUN_00052676`|1|
|**0x326**|**0xFEDF6B00**|**gp-0x1500**|`FUN_00052832`|1|
|0x374|0xFEDF6C18|gp-0x13E8|`FUN_000528B8`|1|
|0x3A1|0xFEDF6C10|gp-0x13F0|`FUN_00052960`|1|
|0x198|0xFEDF6BD0|gp-0x1430|`FUN_00052A14`|1|
|0x094|0xFEDF6BF8|gp-0x1408|`FUN_00052ADE`|1|
|0x305|0xFEDF6AF8|gp-0x1508|`FUN_00052C28`|1|
|0x1A4|0xFEDF6BC0|gp-0x1440|`FUN_00052C78`|1|
|0x1B0|0xFEDF6C28|gp-0x13D8|`FUN_00052E32`|1|
|**0x1D0** (WHEEL_SPEEDS)|0xFEDF6C20|gp-0x13E0|`FUN_000534DA`|**0**|
|0x1EA|0xFEDF6BA8|gp-0x1458|`FUN_00053CCC`|1|
|0x78E|0xFEDF6B88|gp-0x1478|`FUN_00053DE0`|**0**|

⚠ **`gp-0x1500` = the CAN `0x326` (SCM_FEEDBACK) RX buffer.** This is the *specific* root cause of the
V50 GATE-1 on-car failure — sharper than "slot 5 of the 0xb7260 array". Every one of these 19 buffers is
live CAN RAM and is **poison for a code cave**. See [[reference-accord-b7260-io-mailbox-array]].

⚠ **Handlers have ZERO Ghidra callers** — they are dispatched through this table (register-indirect).
Never conclude a `FUN_00052xxx`/`FUN_00053xxx` handler is dead from `get_function_callers`.

## 2. Acceptance filter @ `0xB733C`, written by `FUN_0001cf30`
`mailbox N -> 0xB733C + (N-32)*4`, N = 32..55. Encoding = the FCN CnMIDH/CnMIDL pair:
**bit31 = IDE**; standard `ID = value >> 18`; extended `ID = ((hi&0x1FFF)<<16)|lo`.
Both **0x1D0 (mb 46)** and **0x158 (mb 51)** are accepted. mb 32/36 are extended diag IDs
(`0x18DBEFF1`, `0x1BFC9202`).

## 🛑 INDEX-PARALLELISM IS FALSE — `dest[i]` does NOT pair with `id[i]`
A lead independently read both 24-entry tables (contents agree with mine exactly) and paired them
**index-parallel**, yielding `0x1D0->0xFEDF6BF0`, `0x158->0xFEDF6B58`, `0xE4->0xFEDF6B80`. That pairing is
**refuted on all 10 IDs checked.** The correct relation is `dest_idx = id_idx - 5`. Three independent
refutations, none of which assumes any pairing:
1. **The descriptor table carries ID and buffer in the SAME record, 8 bytes apart.** Record 8 @`0xBB630` =
   `01 00 E4 00 | 01 00 00 00 | D8 6B DF FE | 0F 00 00 00 | 76 26 05 00` -> ID `0x0E4`, buffer
   `0xFEDF6BD8`, handler `0x00052676`. No inference involved.
2. **DLC cross-check.** `0xB7124` IS index-parallel with `dest`. `0xB7124[17]=5`, `dest[17]=0xFEDF6BD8`,
   and Honda `0xE4` STEERING_CONTROL is the only 5-byte frame -> consistent with the descriptor.
   Index-parallelism would put `0x198` (8-byte) in the DLC-5 slot and `0xE4` in a DLC-8 slot — backwards.
3. **LKAS consumer test.** `0xFEDF6BD8` has **5 accesses at offsets +0,+1,+2,+4** (exactly DLC 5);
   `0xFEDF6B80` has **0**. And `FUN_00052676` (the registered `0x0E4` handler) is semantically the LKAS
   ingest: `FUN_00021724()` -> BE16 of `0xFEDF6BD8+0/+1`, then
   `FUN_00049a90(v * -4, 0xffffc000, 0x4000)` -> **`gp-0x69ae` = the LKAS setpoint**, plus flag bits from
   `+2` (`gp-0x1426`) and `+4` (`DAT_fedf6bdc`). The `×-4` and the `±0x4000` clamp are the known
   polarity/scale and the 16384 setpoint clamp.

⚠ **Do NOT "correct" the legacy claim that slot 17 = `0xFEDF6BD8` = LKAS — that claim is RIGHT.** A
proposed correction-of-record calling it "an unverified assumption" would itself be the error.

## 3. Mailbox->buffer dest table @ `0xB739C` (= `tp-0x7C64`), 24 u32 entries; DLC table @ `0xB7124`
`dest_idx = id_table_idx - 5` (i.e. mailbox N -> dest idx N-37), **proven 16/19 against the descriptor
table**. Confirmed independently by the DLC table: `0xB7124[17] = 5` and only Honda `0xE4` is 5 bytes;
the `0xE4` buffer is read only at offsets +0..+4.
**Exceptions: 0x1D0 -> 0xFEDF6C20 and 0x1B0 -> 0xFEDF6C28 are NOT in the 0xB739C table at all.**

## Vehicle speed — CAN 0x158, `FUN_000522FE` (the Clarity-analogue, confirmed)
`FUN_00021706` = `(buf[4]<<8)|buf[5]` big-endian from `0xFEDF6BF0` = **XMISSION_SPEED2**. Then @`0x5233E`:
```
jarl 0x21706      ; r10 = raw (0.01 km/h)
mul  0x29,r10,r0  ; x41
sar  0x6,r10      ; >>6      -> x 41/64 = 0.640625
jarl 0x49a78      ; MIN(.,0x7fff)   (FUN_00049a78 = unsigned MIN)
st.h r10,-0x6a46,gp / st.h r10,-0x4ca4,gp
```
**Destination `gp-0x6a46` = `0xFEDF15BA`; shadow `gp-0x4ca4` = `0xFEDF335C`** (shadow has *no* external
readers; mismatch -> `FUN_0006b9fa`).
**Unit = km/h x 64.0625** (1 count ~ 1/64 km/h). Pinned internally, not just by DBC: the fallback arm
writes `*(byte*)(gp-0x6753) << 6` = km/h x 64 into the same cells. `0x7FFF` = **SNA sentinel**
(also written whenever the message-state arg != 0). Clamp ceiling ~511 km/h.

**Speed cell array is contiguous, 9 x u16 at `0xFEDF15BA..0xFEDF15CA`**, shadows at
`0xFEDF335C..0xFEDF336C`:
`gp-0x6a46` = 0x158 transmission speed; `gp-0x6a44..gp-0x6a36` = 8 cells written by the 0x1D0 handler.

**Readers of `gp-0x6a46`: 24 total accesses, byte-scan verified, ZERO in the 6-byte extended form.**
12 writes/reads inside `FUN_000522FE`; **12 external readers**: `0x28EFE` (FUN_00028ea6), `0x2CCAC`
(FUN_0002cc2a), `0x2D7D4`, `0x2D902`, `0x2DA8A` (no Ghidra fn — unanalyzed), `0x2EC70` (FUN_0002ec52,
kit-classified diagnostic-only), `0x4206C` (FUN_00041eec), `0x423B2` (FUN_00042376), `0x4D98E`
(FUN_0004d8f0), `0x4DEAA` (FUN_0004de0c), `0x4F97C` (ld.hu, no Ghidra fn), `0x4FD56` (FUN_0004fbde).
⚠ `FUN_0004d8f0` / `FUN_0004de0c` / `FUN_0004fbde` read **both** speed and `gp-0x4f60` — the only
places both appear; prime suspects for any speed-dependent behaviour (or for `KFC_WHEELSPD_PLAUSI`).

**`FUN_0004fbde` @`0x4FD56` role ESTABLISHED = diagnostic/reporting, NOT a control gate** [disasm]:
```
ld.h  -0x6a46,gp,r10      ; speed (km/h x64)
mov r10,r14 / sar 0x1f / shr 0x1a / add r14,r10 ; +63 if negative = round-toward-zero
sar   0x6, r10            ; >>6  -> INTEGER km/h
movea 0x136,r0,r13        ; 310
addi  -0x136,r10,r0       ; flags = r10 - 310
cmovc r13,r10,r10         ; saturate at 310 km/h
mov 0xa,r14 / divq r14,r13,r12   ; /10   (dst!=src, so no Ghidra divq bug here)
```
🛑 **`0x136`=310 is 310 km/h AFTER the `>>6`, i.e. a reporting ceiling — NOT a ~3 mph lockout
threshold in counts.** I initially read 310 as counts (~4.8 km/h, inside the lockout band) off a
boundary-unaware inline decode; walking real instruction boundaries killed it. **Do not treat any
constant near a speed read as a threshold without disassembling to instruction boundaries.**
✅ **The `sar 0x6` here is a THIRD independent confirmation of the km/h x 64 unit** (alongside the
`x41/64` from 0.01 km/h raw and the `byte<<6` fallback) — the firmware itself divides the cell by 64
to recover km/h. And the only divide anywhere on this path is `/10` for reporting: **there is no `/50`
in the A160 speed path.**
Remaining reader roles NOT established.

## 0x1D0 wheel speeds — code fully present, wiring NOT established
`FUN_000534DA` -> 8x `FUN_00053216(0..3)` -> `FUN_00021622/46/72/9E(gp-0x13e0)` where
**`gp-0x13e0` = `0xFEDF6C20`** passed as a *pointer* (register-indirect: invisible to gp-relative scans).
Same `x41>>6` scale, same `0x7FFF` sentinel. Raw staging `gp-0x6e50..gp-0x6e42`
(`0xFEDF11B0..0xFEDF11BE`), shadows `gp-0x4d5c..gp-0x4d4e`.
**Two independent indicators say it is not live on this variant:** enable flag `[+0]=0` (all 16 live
records are 1), and `0xFEDF6C20` is absent from the `0xB739C` mailbox dest table (every live ID's buffer
is present). `0xFEDF6BB0` — what the acceptance-filter mapping predicts for 0x1D0 — has **exactly one
image-wide reference, the table slot itself**, and zero readers in either encoding.
🛑 **UNRESOLVED: the descriptor-table walker was not located** by LE32 pointer scan, tp-relative disp
scan, `mov imm32` scan, or movhi/movea lo16 scan. Until it is found, `[+0]`'s semantics are inference.
Related: [[reference_accord_no_vehicle_speed_in_arbitration_steerstatus3]],
[[reference_accord_no_speed_gain_in_baseassist_feedback_loop]] — those remain consistent: a decoded
speed cell existing does not put speed in the assist loop.

## Live-bus cross-validation of the filter decode (2026-07-24)
Operator's listen-only panda capture (`tools/can_sniff_output_20260710.txt`, bus 1 = EPS bus) gives an
**8-way check of `ID = value>>18`**, all passing: `0xE4`(mb54) `0x158`(mb51) `0x94`(mb55) `0x130`(mb53)
`0x17C`(mb50) all ACCEPTED; EPS-TX IDs `0x14A`/`0x18F`/`0x1AB` correctly ABSENT from the RX filter.
`0x158` measured at 292 frames/3 s ≈ **97 Hz**. ⚠ The capture also shows `0x1DF`, which is **NOT** in the
RX filter (`0x1DC` is, mb45) — **bus presence does not imply acceptance**; don't treat a sniffed ID as a
filter entry.

## ⚠ FALSIFIED LEAD — the `0xD0xxx`/`0xD2xxx` "0.5 km/h speed axis" is the DAMPER TORQUE LERP
A lead proposed record `0xD07A2` (`cnt=5, X=[0,50,100,200,400], Y=[1024]x5`) as a 0.5 km/h speed axis
(X/2 = [0,25,50,100,200] km/h, "terminating at 200 like the Clarity `speed_clamp_hi`"). **Falsified:**
- The `0xDxxxx` region is a bank of **variant blocks at 0x1000 stride** (0xD0,D1,D2,D3,D4,D5,D6,D7,D8,D9).
  This car's live block is **0xD2** ([[reference-accord-damper-two-deadzones-factorC-factorE]]). In the
  live block the same record is `X=[0,50,100,150,700]` -> X/2 = [0,25,50,75,**350**] km/h. The "tops out at
  200 km/h" coincidence exists only in the 0xD0 variant, which is not the one that runs.
- The adjacent record `+0x7BA` in the live block **is** `0xD27BC` = `cnt=4, X=[2240,3840,5120,8960],
  Y=[0,235,430,877]` — the **known driver-torque** damper LERP (V44 raised its `Y[0]`; `X[0]=2240` is the
  documented hands-off torque threshold). So this record group's X domain is **torque, not speed**.
- The 0.5 km/h unit is a Clarity import and is wrong for A160: verified unit is **km/h x 64.0625**.
🛑 **My own near-miss, worth remembering:** under the verified x64 unit `X=[1920,3840,5120,8960]` computes
to `[30.0, 59.9, 79.9, 139.9]` km/h — suspiciously round — and I briefly read that as a speed axis. It is
a **numerical coincidence**; torque counts divide into round-looking km/h. Checking the known-live anchor
(`0xD27BC`) killed it. **Never identify an axis domain from the roundness of its values — find the consumer
and read its X input.**

## OPEN LEAD (unresolved, do not act on) — the float km/h LERP at `0xC6518`
`0xC6518` = `tp+0x7518` = float X `[0,10,25,50,80,120,200]`; `0xC6534` = `tp+0x7534` = float Y
`[12000,10000,10000,7000,7000,7000,7000]` (a falling limit). **It IS consumed** — `FUN_00039702`
(0x39702-0x3A381, immediately before `FUN_0003a382`): `movea 0x7534,tp,r14` / `movea 0x7518,tp,ep` @
`0x3A016`/`0x3A01A`, with the interpolation X input read at `0x3A002` as **`ld.w -0x6d14, gp, r15`**.
`gp-0x6d14` = `0xFEDF12EC`, a **float** with exactly **1 writer** (`0x39538` `st.w r6` in `FUN_000389ec`)
and **1 reader** (the LERP).
**NOT yet established that `gp-0x6d14` is vehicle speed.** Hard negative: **neither `FUN_000389ec` nor
`FUN_00039702` touches ANY verified speed cell** (scaled array, raw wheel staging, or shadows) in any
encoding — 0 hits. So it is not fed directly by the CAN 0x158 speed. This leaves
[[reference_accord_no_speed_gain_in_baseassist_feedback_loop]] intact for now.
**Exact next step:** decompile `FUN_000389ec` and trace `r6` at `0x39538` back to its producer. Until
that is done, treat "0xC6518 is a speed schedule" as INFERENCE from axis values only — the same reasoning
that just produced the falsified lead above.

## Anchor of record
`tp+0x746c` = `0xC646C` = **891 in stock `code.bin`** (byte-verified `7B 03`). CLAUDE.md's "3564" is the
**V38** value (891 x 4 = the V38 PID gain change). `tp = 0xBF000` confirmed independently:
`FUN_0001cf30` computes `tp-0x7cc4` and the same function carries the literal `0xb733c`.
