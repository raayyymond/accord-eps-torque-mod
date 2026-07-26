---
name: accord-low-speed-lockout-window-c62ea
description: SOLVED — the A160 low-speed steer lockout is a two-sided speed window (cal 0xC62EA=320 lo / 0xC62E8=12800 hi) compared against voted speed gp-0x6a5e at 0x290c8/0x290d2, gating STEER_CONTROL_ACTIVE and the authority ramp via STEER_STATUS=3.
metadata:
  type: reference
---

**The "EPS refuses steer authority below ~3 mph" behaviour is a FIRMWARE speed window, and it is a
CALIBRATION PAIR.** Fully byte- and Ghidra-verified 2026-07-24.

## The window
| cal | tp-rel | value | km/h (÷64.0625) | role | readers image-wide |
|---|---|---|---|---|---|
|`0xC62EA`|`tp+0x72ea`|**320**|**4.995** (3.104 mph)|**LO bound = the lockout**|**exactly 1** (`0x28ebc`)|
|`0xC62E8`|`tp+0x72e8`|12800|199.8 (124.2 mph)|HI bound|exactly 1 (`0x28eb6`)|

Both loaded at the very top of `FUN_00028ea6` = **`m_steer_torque_arbitration`** (the LIVE arbitration
fn, ~1 kHz; all the V36/V37 landmarks are in it — `gp-0x6807`, `gp-0x6758`, `tp+0x74b8`, `tp+0x74df`,
`FUN_00016de6(0x49,…)` @`0x291c0`):
```
0x28eb6  ld.hu  0x72e8, tp, r2      ; r2 = 12800  (HI)
0x28ebc  ld.hu  0x72ea, tp, lp      ; lp = 320    (LO)      <-- r31 prints as `lp`
...
0x290c8  cmp    r2, r10  / 0x290ce setfnh r9   ; r9 = (speed <= 12800)
0x290d2  cmp    lp, r10  / 0x290d8 setfnc r7   ; r7 = (speed >=   320)   <-- THE LOCKOUT
0x290ea  ld.bu  -0x68b3, gp, r13                ; BYPASS: if != 0 the window is ignored
0x290f2/0x290f6  r6 = 1 / 0    ; r6 = "speed in window"
0x2911c  cmp r0,r6 / be 0x29138  ; window failure kills a 5-way AND
```
⚠ **The compare is on `gp-0x6a5e` (VOTED speed), not on `gp-0x6a46`.** `gp-0x6a46` (the CAN-0x158
transmission speed, see [[accord-can-rx-descriptor-table-and-vehicle-speed]]) reaches it one hop
earlier through the voter.

## Full chain (every hop verified)
```
CAN 0x158 b4-5 (XMISSION_SPEED2, 0.01 km/h, ~97 Hz)
 -> FUN_00021706                      BE16 from 0xFEDF6BF0+4
 -> FUN_000522FE @0x5233a             raw*41>>6 (x0.640625), MIN(.,0x7fff)  [FUN_00049a78 = unsigned MIN]
      => gp-0x6a46 (0xFEDF15BA) u16 = km/h x 64.0625 ; shadow gp-0x4ca4 ; 0x7FFF = SNA
 -> FUN_00041eec  (body 0x41eec-0x42375) = THE VOTER
      inputs: 4 wheel cells gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38 + gp-0x6a46 (as uVar18, own validity bVar1)
      validity per cell = (cell + 0x1900) < 0x9601  i.e. cell in [-6400, +32000]
      picks closest-to-previous, or mean of valid wheels if >1 valid and (max-min) < tol; clamp 0x7d00=32000
      => stores gp-0x6a5e (sole writer @0x42342), gp-0x6a62, gp-0x6a64  (+ shadows -0x4caa/-0x4cae/-0x4cb0)
 -> FUN_00028ea6  window compare above
 -> @0x2918e cmp r0,r27 / bne ; @0x29192 mov 0x3,r6 ; @0x29194 st.b r6,-0x6807,gp
      => STEER_STATUS = 3 = LOW_SPEED_LOCKOUT
 -> @0x2937e ld.bu -0x6807 ; @0x29382 cmp 0x2,r6 ; @0x29384 bnh   ; ENGAGE arm needs STEER_STATUS <= 2
      @0x293a6 st.b r6,-0x6806,gp   = STEER_CONTROL_ACTIVE = 1     } BOTH SKIPPED at ST=3
      @0x293ac st.h r14,-0x69b0,gp  = authority ramp += 0xC63F8=33 }
      LAB_0002971a: gp-0x6806 = 0, gp-0x69b0 = 0                    (full disengage)
```
Ramp cals: up `0xC63F8`=33 (0x8000/33 ≈ 993 ms at 1 kHz), down `0xC63F6`=16, `0xC63F4`/`0xC63FC`=328.

## 🛑 CORRECTS the "STEER_STATUS=3 is REPORT-ONLY" verdict
[[reference_accord_steerstatus3_speed_gated_but_report_only]] found the 320 cal and correctly found no
*external* torque-gating reader of `gp-0x6807` — **image-wide, outside `FUN_00028ea6` and its DEAD twin
`FUN_0002a30e` (0x2a3xx-0x2a9xx), gp-0x6807 has only 2 readers: `0x4e8ec` (a `sst.b` into a diagnostic
snapshot buffer) and `0x55c96` (the CAN-399 packer).** The gating is **INTRA-FUNCTION** — the consumer
is the `cmp 0x2` at `0x29382`, 0x22 KB *inside the same function*. An "outside readers only" sweep
structurally cannot see it. **Report-only was the right observation and the wrong conclusion.**

CAN 399 (`FUN_00055c42`, buffer base `gp-0x1420`): byte4 bit3 <- `gp-0x6806` = **STEER_CONTROL_ACTIVE**;
byte4 bits 4-7 <- `gp-0x6807` = STEER_STATUS. Matches opendbc `35|1@0+` / `39|4@0+`.

## ✅ The gate IS authority-bearing — all 4 live `gp-0x6806=1` writes need STEER_STATUS <= 2
**Liveness VERIFIED, not assumed:** `FUN_00028ea6` body = `0x28ea6-0x2a30d`, **1 caller** (`jarl`
@`0x22522`). `FUN_0002a30e` + `FUN_0002a93a`: **0 `jarl` call sites, 0 LE32 pointers image-wide** = dead.
So `gp-0x6806`'s `0x293xx-0x297xx` cluster is LIVE and `0x2a5xx-0x2a8xx` is the dead copy.

`gp-0x6806` = 16 writers total; **8 live**, and the engage-SM is keyed on mode `gp-0x3d38`:
| writer | value | guard chain (all include the STEER_STATUS test) |
|---|---|---|
|`0x293a6`|1|mode==1, `gp-0x6805`==1, `gp-0x6803`==0, **`gp-0x6807<=2`** (`0x2937e`/`0x29382 cmp 0x2`/`0x29384 bnh`)|
|`0x293e4`|1|mode==1, `gp-0x6805`==1, `gp-0x6803`==2, **`gp-0x6807<=2`** (`0x293ca`/`0x293ce cmp 0x2`)|
|`0x2948c`|1|mode==3, not-fault (`!=7`,`!=4` @`0x2944a`/`0x2944e`), **NOT(`2<gp-0x6807`)**, ramp saturating 0x8000|
|`0x2958c`|1|mode==6, not-fault (`!=7`,`!=4` @`0x294cc`/`0x294d4`), **NOT(`2<gp-0x6807`)**, ramp saturating|
|`0x29696`,`0x296d2`,`0x2970e`,`0x29724`|**0** (`st.b r0`)|ramp-down / disengage arms; `0x29674`/`0x29678 cmp 0x3` tests ST==3 directly|

⇒ The dependency on the speed window is **transitive through `gp-0x6807`**, not on the `bVar2` register
directly. `bVar2` (=`r27`) is tested exactly once, `0x2918e cmp r0,r27` / `0x29190 bne`, whose false arm
is `0x29192 mov 3,r6` / `0x29194 st.b r6,-0x6807,gp`. On the `bVar2`-TRUE path STEER_STATUS becomes
0/1/2 (`cVar19` = `gp-0x68b3!=0`, or 2) — all of which pass `<=2` — or 4/7 for the separate
gentle-EME / DTC-0x49 states. **So lowering `0xC62EA` restores real authority, not just the label.**

## ⚠ The AND-chain's OTHER conjunct shares the same `STEER_STATUS=3` write
`gp-0x69aa == 0x8000` is a second conjunct of the same 5-way AND, so **an on-car `STEER_STATUS=3`
observation cannot distinguish "speed window failed" from "derate not at unity."**
`gp-0x69aa` = `0xFEDF1656`, **sole writer `0x45342`** (independently re-confirmed), 4 readers:
```
0x45334 mov r26,r16 / 0x45336 mulu r28,r16,r0 / 0x4533e shr 0xf,r16 / 0x45342 st.h r16,-0x69aa,gp
```
= a **Q15 product of two derate factors**, unity = 0x8000. It lives in **`FUN_0004503c` = the G1
governor** (body `0x4503c-0x45607`).
🛑 **The governor DOES read vehicle speed** — `ld.hu -0x6a64,gp` at `0x451e2` and `0x45308` (2 hits;
0 in the extended form; the window cals `0x72e8`/`0x72ea` are absent from this body). **This corrects
[[reference-accord-governor-g1-total-command-not-thermal]]'s "no vehicle-speed input anywhere in the
command path".** But the speed term is NOT a derate: `0x45310 ld.hu 0x7316,tp,r16` (**cal `0xC6316`
= 640 = 9.99 km/h**) / `0x45314 cmp r16,r14` / `0x45316 bc 0x45330` **skips the slew-rate limiter**
below ~10 km/h, so `r26` tracks its MIN-chain value instantly — more responsive at low speed, not more
restrictive.
**NOT ESTABLISHED:** whether the MIN chain itself can fall below unity at low speed. Exact next step —
trace `r28` and the `FUN_00049a78` (MIN) inputs at `0x45304` (`gp-0x694c`, `gp-0x6944`, `gp-0x6946`).

## Second, independent low-speed gate (OPEN)
`0x2d84a ld.hu -0x6a62,gp,r12` / `0x2d84e ld.hu 0x72ee,tp,r14` (**`0xC62EE` = 320**, same 4.995 km/h) /
`0x2d852 cmp r14,r12` / `bc` -> `0x2d870 st.b r10,-0x680c,gp` (=1). `0xC62EC`=80 (1.25 km/h, hysteresis?)
read once at `0x2d9d0`. Region `0x2d5xx-0x2dbxx` has **no Ghidra function** (unanalyzed).
`gp-0x680c` = 0xFEDF17F4, 2 writers (`0x2d870`,`0x2d8a2`), 5 readers (`0x2d5ca`,`0x2d6da`,`0x2d80a`,
`0x2da52`,`0x2dac4`) — all in that same unanalyzed region. **Role NOT established.** A `0xC62EA`-only
edit may leave this gate in place.

## ✅ Also re-proves gp-0x6a62 / gp-0x6a64 are SPEED
`FUN_00041eec` assigns all three of `gp-0x6a5e`/`gp-0x6a62`/`gp-0x6a64` from the wheel-speed voter output
`puVar29`/`puVar26`/`uVar10`. Confirms [[reference_accord_gp6a5e_is_voted_vehicle_speed]] on fresh
evidence. **CLAUDE.md's "gp-0x6a62 = the sensor-A column-TORQUE voter" (gentle-EME / 0xC6312 framing) is
WRONG** — the 320 coincidence across the torque and speed domains is what keeps this error alive.

## Fix surface (do NOT touch the speed value or its validity)
`KFC_WHEELSPD_PLAUSI` / `KFC_VSA_1D0` are hard-fault (motor-off) eligible, so the value and the
`(cell+0x1900)<0x9601` plausibility test are off-limits. The **consumer threshold `0xC62EA` is the clean
lever: one reader, cal-only, in the routinely-edited compact `0xC6xxx` block**.
✅ Safety property: lowering the LO bound does **not** defeat SNA detection — the `0x7FFF` sentinel
(32767) still trips the HI bound (12800), so an invalid speed keeps failing the window.
Alternative lever: the bypass flag `gp-0x68b3` (single writer `0x4d148`, unexamined).
