# HANDOFF — Low-Speed Steer: defeating the EPS low-speed lockout

**Date:** 2026-07-24
**Firmware:** `39990-TVA-A160` (2020 Honda Accord EPS, Renesas V850E2)
**Status:** MECHANISM LOCATED. No build attempted, no flash, no CAN sent.
**Requested deliverable:** one write-up for a future session to implement. This is it.

> Self-contained for the low-speed-steer task. You do not need the vibration handoffs.

---

## 0. TL;DR

| Question | Answer |
|---|---|
| Is openpilot the obstacle? | **No.** `CP.minSteerSpeed = 0.0`. OP already commands full torque above 0.67 mph. |
| Does the EPS really refuse to steer at low speed? | **Yes — proven on-car by three independent decoders.** Not a cosmetic status. |
| Where is the threshold? | **★ FOUND: cal `0xC62EA` = 320 = 5.000 km/h** (lower bound), with `0xC62E8` = 12800 = 200.000 km/h (upper). Unit = **64 counts per km/h**. |
| Does the collaborator's Clarity recipe port? | **Yes in substance** — same two-sided window, same 200 km/h upper bound. Different address and different unit. |
| Is it a cal-only edit? | **Yes** — both are plain `ld.hu` u16s in the `0xC6000` block that every build already touches. No float mirror. `0xC62EA` has **exactly one reader image-wide**. |
| ✅ Is it the *right* lever? | **YES — SETTLED.** The window gates `STEER_STATUS=3`, which gates both `STEER_CONTROL_ACTIVE` (`gp-0x6806`) **and** the authority ramp (`gp-0x69b0`). Chain verified instruction-by-instruction. See §6. |
| Biggest hazard | `KFC_WHEELSPD_PLAUSI` / `KFC_VSA_1D0` are **hard-fault (motor-off) eligible**. Never tamper with the speed *value* — only the comparison. |
| ✅ Second 320-count gate at `0xC62EE`? | **RESOLVED — not a lockout.** It is a *permissive* inside a **CAN-commanded** assist-shutdown task, unreachable without a remote request bit. **`0xC62EA`-only is sufficient. Do NOT touch `0xC62EE`, and never RAISE it** (§6c). |

---

## 1. The goal and the collaborator's template

The operator wants LKAS/assist to work below the speed at which this EPS locks out. A collaborator did
this on a **Honda Clarity** EPS (SH-2A, same Honda design language):

```c
void update_vehicle_speed_from_can_158(uint8_t data[8]) {
    uint16_t raw_speed = ((uint16_t)data[4] << 8) | data[5];   // 0x158 XMISSION_SPEED2, 0.01 km/h
    int16_t base_speed = raw_speed / 50;                        // -> 0.5 km/h units
    if (base_speed > 510) base_speed = 510;                     // 255 km/h
    *(int16_t *)0xFFF87276 = select_or_filter_speed(base_speed);
}
void update_speed_valid_flag(void) {
    int16_t vehicle_speed  = *(int16_t *)0xFFF87276;
    int16_t speed_clamp_lo = *(int16_t *)0x13638;   // <-- the constant they modify
    int16_t speed_clamp_hi = *(int16_t *)0x1363A;   // reportedly 200 km/h
    bool speed_valid = speed_clamp_lo <= vehicle_speed && vehicle_speed <= speed_clamp_hi;
    *(uint8_t *)0xFFF87B78 = speed_valid;
}
```

**The structure ports. The numbers do not.** On the A160 the window is a `(hi, lo)` pair of `ld.hu` u16
calibrations in the tp block, the unit is **64 counts/km/h** (not 0.5 km/h/count), the speed comes from a
**5-channel redundant voter** rather than one filtered value, and the validity boolean is **never stored
to RAM** — it lives in a register. Do not go looking at `0x13638` on this firmware; that address is a
different memory map, and a scan of `[0x0,0x14100)` plus both non-payload dumps found nothing there.

---

## 2. openpilot side — RESOLVED, and it is not the obstacle

**This corrects a standing kit claim.** `memory/reference_accord_sub3mph_lkas_openpilot_gate.md` says the
~3 mph cutoff is openpilot-side, citing Accord `minSteerSpeed = 3*MPH_TO_MS` at `values.py:163`.
**Wrong.** Verified in the operator's own pinned repos (`C:\Users\dudei\Desktop\Projects\openpilots\`):

- `opendbc/car/__init__.py:154` — `class CarSpecs: ... minSteerSpeed: float = 0.0  # m/s`
- `opendbc/car/interfaces.py:140` — `ret.minSteerSpeed = platform.config.specs.minSteerSpeed`
  → reads **`CarSpecs`**, never `CarDocs`.
- `values.py:161-170` — the Accord's `CarSpecs(...)` has **no `minSteerSpeed=` kwarg** → stays `0.0`.
  (Contrast `values.py:234` HONDA_CITY_7G and `honda/interface.py:195` Odyssey, which do set it.)
- `values.py:163`'s `min_steer_speed=3.*CV.MPH_TO_MS` is a **`HondaCarDocs`** kwarg — car-compatibility
  *website metadata*, never read into `CarParams`.

⇒ **`CP.minSteerSpeed = 0.0`.** Identical in upstream and both operator forks.

**The one real OP floor:** `selfdrive/controls/controlsd.py:178`
```python
standstill = abs(CS.vEgo) <= max(self.CP.minSteerSpeed, 0.3) or CS.standstill
```
consumed by `selfdrive/controls/lib/drive_helpers.py:61-66`, which returns
`... and (not standstill or steer_at_standstill) and lateral_check`.
So a hardcoded **0.3 m/s ≈ 0.67 mph** floor, bypassable only via `CP.steerAtStandstill` — set by
**ford, hyundai, psa, tesla, tesla/preap**, and **nowhere in `opendbc/car/honda/`**.

**Minimal precedented OP change (only for true standstill):**
```python
# opendbc/car/honda/interface.py, _get_params(), Accord branch
ret.steerAtStandstill = True
```
Gate it on the fork's `HondaFlags.EPS_MODIFIED` so stock-EPS Accords are unaffected.
⚠ **Sequence it after the firmware fix** — commanding at 0 mph is pointless while the EPS declines.
⚠ Note `CS.standstill` ORs in independently of the 0.3 threshold; check it too.

**Other verified OP facts (don't re-derive):**
- Accord is **not** in `HONDA_BOSCH_ALT_RADAR`, so `carstate.py:106-110` applies:
  `steerFaultTemporary = steer_status not in ("NORMAL","LOW_SPEED_LOCKOUT","NO_TORQUE_ALERT_2")` —
  the lockout is tolerated **unconditionally, at any speed**. Leaving it in place raises no fault.
- `carstate.py:118-122` (`lowSpeedAlert`) is **dead code** here (`1.34 < vEgo < 0.5` unsatisfiable).
- `STEER_GLOBAL_MIN_SPEED` (`values.py:41`) has **three** textual consumers
  (`carcontroller.py:227`, `carstate.py:103`, `carstate.py:118`) but **two are inert for this car** —
  103 is in the ALT_RADAR branch, 118 is dead. The live one only drives the HUD icon.
  ⚠ A fork flipping ALT_RADAR would silently activate `carstate.py:103-105`.
- **Panda safety** `opendbc/safety/modes/honda.h` `honda_tx_hook`: the `0xE4`/`0x194` steer check gates on
  `controls_allowed` only — **no speed term**. Its `vehicle_moving` (sampled from `0x158`) is **never
  read** in that file. No panda-side speed restriction on Honda lateral.
- Accord's DBC is `honda_civic_hatchback_ex_2017_can_generated`, which imports **`_bosch_2018.dbc`** —
  so the applicable `STEER_STATUS` enum is the `1 "tja_low_speed_lockout"` variant (7 bytes), **not** the
  `_steering_control_a/b/c.dbc` `1 "driver_steering"` variant (6 bytes, other cars). Values 0/3/4 are
  identical across both, so no reported number changes; quote the right one though.

---

## 3. On-car proof: the lockout is a REAL GATE, not a label

**Falsifies a standing kit inference.** `.claude/agent-memory/firmware-codepath-tracer/`
`reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md` concluded `STEER_STATUS=3` was merely
a by-product of openpilot not commanding — and that document itself labelled the conclusion
*"Inference (not proven this session)."* It is now empirically contradicted.

Signals used (all EPS-transmitted, `_bosch_2018.dbc`):
```
BO_ 399 STEER_STATUS: 7 EPS
 SG_ STEER_ANGLE_RATE     : 23|16@0- (-0.1,0) "deg/s"   bytes 2-3
 SG_ STEER_STATUS         : 39|4@0+                     byte4 bits 7:4
 SG_ STEER_CONTROL_ACTIVE : 35|1@0+                     byte4 mask 0x08
```

### 3a. Speed-correlation, engagement held constant
~305k checksum-valid CAN-399 frames, 9 routes, 0 checksum failures. `STEER_STATUS == 3`:

```
        latActive=True                     latActive=False
 0-1 mph  n=913     100.0%          0-1 mph  n=39526   99.9%
 1-2 mph  n=2634    100.0%          1-2 mph  n=4824   100.0%
 2-3 mph  n=2224     99.1%          2-3 mph  n=2235    99.7%
 3-4 mph  n=2219     10.1%          3-4 mph  n=2273    11.5%
 4-5 mph  n=3660      0.0%          4-5 mph  n=1641     0.0%
 5 mph+   n=~211k     0.0%          5 mph+   n=~14k     0.0%
```
Compare the two `latActive=False` columns: OP is not commanding in either, so **speed is the only
variable** — 100% lockout low, 0% high. An engagement artifact would appear whenever OP was disengaged at
any speed. It does not.

### 3b. Gate-or-label — the decisive discriminator (three independent decoders)
`STEER_CONTROL_ACTIVE` is the EPS's own "I am under external steer control" flag. With openpilot
actively commanding (`latActive=True`, `STEER_TORQUE_REQUEST=1`):

```
       mph        n  CTRL_ACT%     st3%   st3 AND CTRL   mean|rate|  mean|cmd|
    0.67-1      913       0.0%   100.0%             0        1.66      0.652
       1-2     2631       0.0%   100.0%             0        7.44      0.678
       2-3     2224       0.9%    99.1%             0       13.97      0.714
       3-4     2219      88.1%    10.1%             0       17.37      0.655
       4-6     5744      99.4%     0.0%             0       16.73      0.452
      6-10     8831      99.9%     0.0%             0       25.98      0.560
     10-20    31884      99.5%     0.0%             0       16.94      0.536
```

- **`STEER_CONTROL_ACTIVE=1` and `STEER_STATUS=3` NEVER co-occur — 0 frames, in every bucket.** When the
  EPS reports the lockout it is simultaneously declaring itself not under external control.
- **Commanded torque is not smaller at low speed** (`mean|cmd|` 0.65-0.71 at 0.67-3 mph vs 0.45-0.56 at
  4-10 mph), so "openpilot isn't trying" is excluded. Yet angle-rate response is 1.7-14 deg/s vs
  17-26 deg/s — **response per unit command suppressed ~10-70×**, recovering in lockstep with
  `STEER_CONTROL_ACTIVE` flipping, not merely with speed.

**Three independent implementations agree** (two by a teammate — streaming state-machine vs vectorized
`searchsorted` join, wire-domain CAN-228 torque vs `carOutput.actuatorsOutput.torque` — plus mine).
Frame-count differences (304231 / 307275 / 308316) were reconciled as a pre-first-`carState` counting
convention, not a decode disagreement. This is the kit's two-independent-decoder standard, met with three.

⇒ **The EPS genuinely refuses external steer authority below ~3.5 mph.** Hard edge 3-4 mph.

⚠ **Data gap:** no capture has `latActive=True` below 0.3 m/s (no fork sets `steerAtStandstill`), so
true-standstill behaviour is **empirically unknown**.

---

## 4. ★ THE MECHANISM — the speed window, located

### 4a. The calibration pair
**[VERIFIED: lead's own byte read + instruction decode]**
```
0xC62E8  (tp+0x72E8) = 12800  = 199.80 km/h (124.15 mph)   speed_clamp_hi
0xC62EA  (tp+0x72EA) =   320  =   4.995 km/h (3.104 mph)   speed_clamp_lo   <== THE LEVER
```
Loaded 6 bytes apart, both `ld.hu` (subop `0x3F`), in `FUN_00028ea6`. **Each has exactly ONE reader
image-wide** — `0x28EBC` for the LO, `0x28EB6` for the HI — so neither is shared with another feature:
```
0x28EB6  ld.hu tp+0x72E8, r2     ; 12800  HI
0x28EBC  ld.hu tp+0x72EA, r31    ;   320  LO
```

There is a whole **cluster of speed thresholds** here [VERIFIED: lead's byte read]:
```
0xC62E6 = 7680  (119.9 km/h)    0xC62EC =  80  (1.25 km/h)
0xC62E8 = 12800 (199.8 km/h)    0xC62EE = 320  (4.995 km/h)  <-- the SECOND gate, see 6c
0xC62EA =   320 (4.995 km/h)    0xC62F0 = 640  (9.99 km/h)
```

**Three independent lines converge:**
1. **Static:** `320` → 4.995 km/h; `12800` → 199.80 km/h — i.e. the designers' round 5 and 200 km/h.
2. **On-car:** the measured edge is **3.104 mph**, which lands inside the observed 3-4 mph transition
   bucket (§3b: 0.9% control-active at 2-3 mph → 88.1% at 3-4 mph).
3. **Cross-firmware:** the collaborator's Clarity `speed_clamp_hi` is **200 km/h** — the same design
   constant, from a different CPU and an independent reverse-engineering effort.

### 4b. The unit: ≈64 counts per km/h (implemented as ×41/64)
**Nominal 64 counts/km/h; the CAN path implements `×41 >> 6` = ×0.640625 on a 0.01 km/h raw value, i.e.
64.0625 counts/km/h** [VERIFIED: lead decoded `mul` imm-low5=9 (=41 & 0x1F) at `0x5233E` and
`sar 0x6, r10` (subop `0x15`) at `0x52346`]. Hence 320 → 4.995 km/h, not exactly 5.000.
⚠ **I earlier wrote "exactly 5.000 / 200.000 km/h" using ÷64. That was the nominal intent, not the
implemented scale — corrected here.** The two coexist: the fallback arm at `0x52382` writes
`(byte km/h) << 6` = exactly ×64 into the same cell, so the firmware itself carries both scalings with a
~0.1% discrepancy. Either way the thresholds are the designers' 5 and 200 km/h.

Corroboration: the V44/V47 damper "Factor C" axis `X = [2240, 3840, 5120, 8960]` → `/64 =
[35, 60, 80, 140]` km/h, all exact [VERIFIED: lead's byte read].
⚠ **Weaker argument, stated honestly:** "LERP X-rows are multiples of 64" holds for only ~38% of
ascending-X records in `0xD0000-0xD1000` (lead's control test), and Q10/Q6 fixed-point makes multiples of
64 common regardless. **Do not lean on that.** Lean on (1)-(3) and the decoded `×41>>6`.
The old "0.5 km/h per count" reading is falsified (it would imply 960-25600 km/h axes).

### 4b-bis. ⚠ The Clarity's `/50` and `510` clamp do NOT exist here
`FUN_000522fe`, `param_1 == 0` (live decode arm) [VERIFIED: lead confirmed the `mul`/`sar` encodings]:
```
0x5233a  jarl 0x21706        ; raw XMISSION_SPEED2 (0.01 km/h)
0x5233e  mul  0x29, r10, r0  ; x41
0x52346  sar  0x6, r10       ; >>6      => x41/64
0x52348  andi 0xffff, r10, r6
0x5234c  jarl 0x49a78        ; unsigned MIN(., 0x7fff)
0x5235c  st.h r10, -0x6a46[gp]      ; 0xFEDF15BA
0x52360  st.h r10, -0x4ca4[gp]      ; 0xFEDF335C  <-- SHADOW
```
No `/50`, no `510`. The only clamp is `MIN(·, 0x7fff)` ≈ 511.5 km/h; `0x7FFF` doubles as the **SNA
sentinel**. ⚠ **`gp-0x6a46` is a SHADOWED variable** — the shadow `gp-0x4ca4` must match or
`FUN_0006b9fa` fires. Do not write one leg without the other. (This is the V27/`0x17` failure class.)

### 4c. The AND-chain, and the `STEER_STATUS=3` writer
`STEER_STATUS = gp-0x6807 = 0xFEDF17F9` (odd address ⇒ byte). **20 `st.b` writers, 20 `ld.bu` readers,
zero 6-byte extended-displacement accesses ⇒ enumeration is total.** 10 live writers in `FUN_00028ea6`
(sole caller `FUN_0002214a` = `w_steer_control_task`); 10 in `FUN_0002a30e`, which is **DEAD** (0 callers).

**The only value-3 writer** [VERIFIED byte-exact by the lead]:
```
0x29192  mov  3, r6                  ; format II, imm5=3, reg2=r6
0x29194  st.b r6, -0x6807[gp]        ; subop 0x3A -> 0xFEDF17F9
```
It is the **`else`** of `if (bVar2)`, where `bVar2` requires **all** of:

1. `0xC62EA (320) <= gp-0x6a5e <= 0xC62E8 (12800)` — **the speed window**; bypassed if `gp-0x68b3 != 0`
2. five voter channels each within `[-6400, +32000]`, AND `gp-0x67f4 == 1`, AND `gp-0x6a5e < 0x7d01`
3. `gp-0x67fe == 2` (assist substate "engaged" — the conjunct the earlier trace stopped at)
4. `gp-0x69aa == 0x8000` (degenerate equality; cal `tp+0x73f2` = **32768** is *both* bounds — verified.
   `gp-0x69aa` is a Q15 MIN-only derate product seeded `0x8000`, sole writer `0x45342` in the governor,
   so this means "no derate active")
5. `gp-0x69ae` (LKAS setpoint) within ±`0x4000`

Independently corroborated: the lead's own gp/tp access enumeration over `[0x28EA0,0x291D0)` finds
**every** named conjunct present in coherent order — the five voter channels `gp-0x6a38/3c/40/44/46`,
both window cals, `tp+0x73f2`=32768, `gp-0x6a5e` (read twice, **`ld.hu` = unsigned**, consistent with a
speed rather than a signed torque), `gp-0x68b3`, `gp-0x67fe`, `gp-0x69aa`, `gp-0x69ae`.

**★ The standstill asymmetry is the signature of a deliberate lockout.** `gp-0x68b3` is written in
`FUN_0004d0d0` **only when `gp-0x6a62 == 0`** (exactly zero = true standstill). So **0 km/h bypasses the
window, but 1-319 counts (0 < v < 5 km/h) cannot.** That is designed, not incidental.

### 4d. ⚠ Why the exhaustive "no window exists" scan returned a false negative
An earlier pass enumerated all 3137 tp-relative disp16 targets and every delta-2 pair within 32 bytes of
a PC, and concluded **no window existed**. The pair `0xC62E8`/`0xC62EA` *is* a delta-2 pair loaded 6
bytes apart — well inside that window. The scan missed it because it required a two-sided compare
**followed by a boolean store**. **`bVar2` is never stored to RAM**: it lives in a register, is consumed
immediately in the AND-chain, and the only memory write is `st.b 3 -> gp-0x6807` in the *failing* branch.
**Methodology rule: never require "compare → boolean store". Search for the compare alone.**

### 4e. ⚠ The other trap: LERP records masquerading as `(lo,hi)` pairs
Both the `0xD0xxx` bank and the tp cal window hold records laid out
`[count][X[0..n-1]][Y[0..n-1]]` (int16), so `X[last]` sits immediately before `Y[0]` and reads exactly
like a plausible `(lo,hi)`. Two worked falsifications — **do not re-promote these:**

| Candidate | Looked like | Actually is |
|---|---|---|
| `0xC697C`/`0xC697E` = `10`/`255` | lo=5.0 km/h (3.1 mph — inside the real edge!) | `0xC6974` record `count=4, X=[4,6,8,10], Y=[255,255,255,255]`. `10` is `X[last]`. Input is `ld.bu gp-0x6830` — a byte. |
| `0xC6C1C`/`0xC6C1E` = `400`/`10` | hi=200 km/h, lo=5 km/h — matched *both* targets | Sole readers `0x6e488` and `0x6dbfe`, in **different functions** ~2.3 KB apart. No cell in that block shares a reader with its neighbour. |

**The tell:** a `movea <disp>, tp, rN` table-base load shortly before the loads means a LERP descriptor.
**Never promote a constant pair without disassembling its load site.**

---

## 5. The CAN speed path

### 5a. Source message — confirmed on both sides
**On the bus** [operator's 3 s silent listen-only capture, `tools/can_sniff_output_20260710.txt`]: bus 1
is the EPS bus (carries EPS TX `0x18F`/`0x1AB`/`0x14A`); **`0x158` is on it at 292 frames / 3 s ≈ 97 Hz**.
**In the DBC** (`_honda_common.dbc`, imported by the Accord's):
`XMISSION_SPEED : 7|16@0+ (0.01,0) "kph"` (bytes 0-1 BE) and
`XMISSION_SPEED2 : 39|16@0+ (0.01,0) "kph"` (bytes 4-5 BE) — **exact match to the Clarity decoder.**
⚠ Prior sessions hunted only `0x1D0` and dead-ended; `0x158` was never checked.

### 5b. RX tables and the correct ID↔buffer mapping
Two adjacent 24-entry u32 arrays: **filters at `0xB733C`** with **`CAN_ID = word >> 18`**, **destinations
at `0xB739C`** (`0xB733C + 4*24 == 0xB739C`, verified). Every destination is `0xFEDF6AE0 + 8n` — 8 bytes
= one CAN frame.

**⚠ They are NOT index-parallel. The mapping is `dest[i] ↔ id[i+5]`** (19 real mappings;
`dest[19..23]` unused and reader-free). Proven three ways by matching read offsets to DBC signal
positions [VERIFIED: lead]:

| ID | buffer | bytes read | signal at those bytes |
|---|---|---|---|
| `0x0E4` LKAS | `0xFEDF6BD8` | 0,1 | `STEER_TORQUE` `7|16@0-` ✓ |
| `0x094` STEERING_SENSORS | `0xFEDF6BF8` | 0,1 | `STEER_ANGLE` ✓ |
| **`0x158` ENGINE_DATA** | **`0xFEDF6BF0`** | **4,5** | **`XMISSION_SPEED2`** ✓ |

Under the naive index-parallel reading LKAS would map to `dest[22]`, which has **zero readers** —
impossible.

**★ Better still: a self-describing descriptor table at `0xBB5A0`**, stride `0x20`, with handler at
`+0x00`, **ID at `+0x12` and destination at `+0x18` in the same record** — no parallelism assumption
needed. It agrees with all three proven pairs. Full map: `0x17C`→`0xFEDF6BE8`, `0x1DC`→`0xFEDF6C00`,
`0x324`→`0xFEDF6BA0`, `0x328`→`0xFEDF6B98`, `0x326`→`0xFEDF6B00`, `0x374`→`0xFEDF6C18`,
`0x3A1`→`0xFEDF6C10`, `0x198`→`0xFEDF6BD0`, `0x305`→`0xFEDF6AF8`, `0x1A4`→`0xFEDF6BC0`,
`0x1B0`→`0xFEDF6C28`, **`0x1D0`→`0xFEDF6C20`** (handler `0x52E32`), `0x1EA`→`0xFEDF6BA8`,
`0x78E`→`0xFEDF6B88`. **Use `0xBB5A0` in preference to the parallel-array pair — it cannot be mis-paired.**

**⚠ Retraction of a correction I made earlier this session.** I claimed the legacy memory
`reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder.md` was wrong to say "slot 17 = `0xFEDF6BD8` =
the known LKAS routing." **The legacy claim was substantially RIGHT** — `0xFEDF6BD8` genuinely *is*
`0x0E4`'s buffer. Only its *"slot 17"* index attribution was off, because the tables are not
index-parallel. My "correction of record" was itself the error; this supersedes it.

**Bonus:** `gp-0x1500` = `0xFEDF6B00` is CAN `0x326`'s RX buffer — an independent **static** confirmation
of the V50 GATE-1 on-car failure (a CAN buffer with a live register-indirect writer). Any future cave RAM
candidate must be checked against `+0x18` of every `0xBB5A0` record. Note `gp-0x14E0` = `0xFEDF6B20` is
also inside that region, so the V48B post-mortem's "vetted-safe alternative" is unsafe.

### 5c. Speed decode and the voter
- **`FUN_00021706`** is the raw speed getter: `ld.bu gp-0x140c` / `ld.bu gp-0x140b`, `shl 8`, `or` →
  `(buf[4]<<8)|buf[5]` big-endian from `0x158`'s buffer = raw `XMISSION_SPEED2` in 0.01 km/h. Sole caller
  **`FUN_000522fe`** @`0x5233a`, which writes the **5th (transmission) reference channel `gp-0x6a46`**,
  scaled `raw*41>>6` (0.01 km/h × 41/64 → 64 counts/km/h; 500 raw → 320.3 counts = 5 km/h ✓).
- **`FUN_00041eec` is a 5-channel redundant speed voter**: four wheel speeds from `0x1D0`'s buffer
  (`0xFEDF6C20`) via `FUN_00021646/21622/21672/2169E`, each assembling a **15-bit** field
  (`(byte3>>2)|(byte2<<6)|((byte1&1)<<14)` = Honda `WHEEL_SPEEDS` packing) → `FUN_00053216`
  (`raw*41>>6`) → `gp-0x6e4a/4c/4e/50` → `FUN_000534da` → `gp-0x6a38/3c/40/44`; plus `gp-0x6a46`.
  Validity window `[-6400,+32000]`, takes `|x|`, picks the channel closest to the previous output or the
  mean when ≥2 valid and spread is small, clamps to `0x7d00` = 32000 = 500 km/h.
- **Outputs:** `gp-0x6a5e` (sole writer `0x42342`), `gp-0x6a62`, and slew-limited `gp-0x6a64`
  (sole writer `0x42360`, rate cal `tp+0x74ee`).

### 5d. ⚠ Encoding trap that cost this session a wrong conclusion
gp/tp Format VII: `hw1 = (regD<<11) | (subop<<5) | reg1`, `reg1` = 4 (gp) or 5 (tp).
```
subop 0x38 ld.b   0x39 ld.h/ld.w   0x3A st.b   0x3B st.h/st.w
subop 0x3C/0x3D ld.bu  -> hw2 = (disp | 1), address LSB carried in the subop low bit
subop 0x3E/0x3F ld.hu  -> hw2 = (disp | 1)
```
Anchored on the 7 known `gp-0x4f60` `ld.h` sites (all `hw2 = 0xB0A0`), on `0x2170e`/`0x21712`
(`ld.bu`), and on `0x28EB6`/`0x28EBC` (`ld.hu`). Validation: the matcher reproduces the kit's
independently-established **64** `ld.h gp-0x4f60` sites exactly.

**A scan that matches `hw2` against exact even displacements is blind to every byte and half-word-unsigned
load.** I made that error and it produced a confident, wholly wrong structural conclusion ("the CAN
mailboxes are register-indirect only; zero gp-relative accesses"). **Retracted.** The buffers are read
gp-relative, by `ld.bu`, which is the natural way to unpack a CAN frame.

---

## 6. ✅ RESOLVED — `0xC62EA` **is** the right lever

### 6a. The full chain, verified instruction-by-instruction by the lead
The apparent paradox was that `gp-0x6807` (STEER_STATUS) has **no external torque-gating reader** — yet
the EPS demonstrably declines authority. **Resolution: the real consumer is INTRA-FUNCTION.** An
"outside-the-function readers" sweep structurally cannot see it, which is why the earlier "report-only"
verdict looked airtight and was nonetheless the wrong conclusion.

```
; ---- the window (FUN_00028ea6 = live m_steer_torque_arbitration, ~1 kHz) ----
0x28EB6  ld.hu tp+0x72E8, r2      ; HI = 12800
0x28EBC  ld.hu tp+0x72EA, r31     ; LO =   320
0x290C8  cmp   r2,  r10 / setfnh  ; speed <= HI
0x290D2  cmp   r31, r10 / setfnc  ; speed >= LO      <== THE LOCKOUT
0x290EA  ld.bu gp-0x68b3          ; bypass: if != 0 the window is ignored
0x290F2/0x290F6                   ; r6 = "speed in window" (1/0)
0x2911C  cmp r0,r6 / be           ; failure kills a 5-way AND
0x29192  mov  3, r6
0x29194  st.b r6, -0x6807[gp]     ; STEER_STATUS = 3 = LOW_SPEED_LOCKOUT

; ---- the consumer, ~500 bytes later in the SAME function ----
0x2937E  ld.bu gp-0x6807, r6      ; read STEER_STATUS back
0x29382  cmp   0x2, r6
0x29384  bnh   +7 -> 0x29392      ; ST <= 2  ==> take the ENGAGE block
   ; ST >= 3 (our lockout) falls through:
0x29386  ld.hu gp-0x69b0
0x2938A  ld.bu gp-0x679e
0x2938E  jr    0x29734            ; <== JUMPS AWAY into the disengage path
   ; ST <= 2 lands here — the ENGAGE block:
0x29392  ld.hu gp-0x69b0, r12     ; current authority ramp
0x29396  ld.hu tp+0x73F8, r14     ; ramp-up step = 33
0x2939A  mov   1, r6              ; r6 = 1
0x293A6  st.b  r6, -0x6806[gp]    ; STEER_CONTROL_ACTIVE = 1
0x293AC  st.h  r14, -0x69b0[gp]   ; authority ramp advanced
   ; and on the disengage path (0x29696/0x296d2/0x2970e/0x29724): gp-0x6806 = 0, ramp = 0
```
[VERIFIED: lead's independent byte decode of every instruction above. `bnh` = cond `0x3`, disp `+7`,
target `0x29392` — landing exactly on a decoded instruction boundary. `jr` at `0x2938E` decoded as
Format V (`hw1` bits 10:6 = `0b11110`, reg2 = 0), disp22 = `0x3A6` → target `0x29734`, inside the
disengage region whose `gp-0x6806` writers (`0x29696`, `0x296D2`, `0x2970E`, `0x29724`) all store `r0`.]

⇒ **`speed < 320` → `STEER_STATUS = 3` → `jr` to disengage → `STEER_CONTROL_ACTIVE = 0` and the authority
ramp zeroed.** That is exactly the bit measured on-car in §3b. **Lowering `0xC62EA` restores real steer
authority, not merely the reported status.**

### 6b. Why the "report-only" verdict was right in its evidence and wrong in its conclusion
`gp-0x6807`'s only readers *outside* `FUN_00028ea6` and its dead twin `FUN_0002a30e` are
`FUN_00055c42` (the CAN-399 packer) and `0x4e8ec` (a `sst.b` into a diagnostic snapshot). That sweep was
correct. **But the load-bearing reader is the `cmp 0x2` at `0x29382`, inside the same function.**
**Methodology rule: an "external readers" sweep cannot establish that a variable is report-only.** Always
check intra-function reads before concluding a flag has no consumers.

`STEER_CONTROL_ACTIVE` = `gp-0x6806 & 1`, confirmed from the packer's own arithmetic
[VERIFIED byte-exact by the lead]:
```
0x55c76  ld.bu gp-0x6806, r15    ; 0xFEDF17FA
0x55c7e  andi  0x1, r15, r15
0x55c82  shl   3, r15            ; <== BIT 3 = STEER_CONTROL_ACTIVE
0x55c84  or    r15, r10          ; into frame byte 4 (TX buf gp-0x141c = 0xFEDF6BE4)
0x55c96  ld.bu gp-0x6807, r13
0x55c9e  shl   4, r13            ; <== BITS 7:4 = STEER_STATUS
0x55ca0  or    r13, r8
```
⇒ **`STEER_CONTROL_ACTIVE = gp-0x6806 & 1`.**

**And `gp-0x6806` is NOT report-only** — 16 writers, 13 readers, with readers inside the command/assist
region and beyond: `0x2ef40`, `0x2fc88`, `0x3130c`, `0x31322`, `0x31340`, `0x3134e`, `0x031354`,
`0x042842`, `0x4fa96`, `0x4fd44` (plus `0x2a1b6`, `0x2a8c0`, and the packer).
Writers: `0x293a6`, `0x293e4`, `0x2948c`, `0x2958c`, `0x29696`, `0x296d2`, `0x2970e`, `0x029724`
(first cluster, four of them writing `r0`=0), then `0x2a582`, `0x2a5b6`, `0x2a658`, `0x2a73c`, `0x2a80a`,
`0x2a842`, `0x2a862`, `0x2a87e`. The `0x2a3xx-0x2a8xx` cluster belongs to the **dead** `FUN_0002a30e`
twin; the live writers are the `0x293xx-0x297xx` set, in the same function as the speed window (§6a).

Ramp cals (for reference): up `0xC63F8` = 33 (`0x8000/33` ≈ 993 ms at 1 kHz), down `0xC63F6` = 16,
`0xC63F4`/`0xC63FC` = 328 [VERIFIED: lead's byte read]. `gp-0x69b0` is read at `0x42846`, `0x2b38e`,
`0x2b39e` — **outside** the producing function, so it is real authority, not a report.

### 6c. ⚠ REMAINING CAVEAT — a second, independent 320-count gate
[VERIFIED: lead's byte read + instruction decode]
```
0x2D84A  ld.hu gp-0x6a62, r12     ; voted speed (another voter output)
0x2D84E  ld.hu tp+0x72EE, r14     ; 0xC62EE = 320 = the SAME 4.995 km/h
0x2D852  cmp   r14, r12
0x2D870  st.b  r10, -0x680c[gp]   ; gp-0x680c = 0xFEDF17F4
```
`0xC62EC` = 80 (1.25 km/h) is read once at `0x2d9d0`, hysteresis-shaped.

**Lead's own enumeration** [VERIFIED: whole-image scan, all encodings, store-zero trap fixed, scanner
validated against the 64 known `ld.h gp-0x4f60` sites]:
```
gp-0x680c (0xFEDF17F4): 5 writers, 5 readers    (NOT 2 writers -- the three st.b r0 were missed earlier)
  W 0x2D870, 0x2D8A2, 0x2D948(r0), 0x2D980(r0), 0x2D990(r0)
  R 0x2D5CA, 0x2D6DA, 0x2D80A, 0x2DA52, 0x2DAC4
  ==> accesses OUTSIDE 0x2d500-0x2dc00: ZERO
```
**✅ Good news: `gp-0x680c` is entirely CONFINED to that region — nothing outside reads or writes it.**
So it **cannot itself gate steering**; any influence would have to flow through some *other* variable the
region writes. That materially shrinks the caveat.

**⚠ Bad news: the region is LIVE, so it does not dissolve by deadness** [VERIFIED: lead's whole-image
Format-V `jr`/`jarl` disp22 scan; only even-target hits counted, odd targets being unaligned-scan false
positives]:
- **`0x22CC0` `jarl` → `0x2D80C`** — `0x22CC0` is inside **`FUN_00022ca0`, the assist-shaping task**.
- **`0x23074` `jarl` → `0x2DB94`**
- **`0x28986` `jarl` → `0x2D846`** — and `0x2D846` is **4 bytes before the gate at `0x2D84A`**, so the
  containing function starts at/before `0x2D846` and is entered from the `0x289xx` area.
- Plus 10 LE32 pointers into the region ⇒ partly table-dispatched too.

### ✅ RESOLVED — `0xC62EE` is a CAN-commanded permissive, not a lockout
**`0xC62EA`-only is sufficient. Do NOT touch `0xC62EE` — and specifically never RAISE it.**

The `0xC62EE` compare is a *permissive* ("vehicle is slow enough that assist may now be removed") inside a
**CAN-commanded assist-shutdown** task. Its action arm cannot be entered unless a remote request bit is
set, so it does not restrict normal low-speed authority. Lowering it restores nothing; **raising it would
let a commanded assist-kill fire at higher road speed.**

**The region IS live — it does not dissolve as dead code.** It is an RTOS task, reached via a
task-control-block array at `0xBB928`, **stride `0x30`, entry point at `+0x08`**. That table is
**self-validating** [VERIFIED: lead's LE32 read]:
```
0xBB928 -> 0x2214A   <== the KNOWN 1 kHz control task
0xBB958 -> 0x22A88        0xBB988 -> 0x22B20        0xBB9B8 -> 0x22B24   <== this chain
0xBB9E8 -> 0x22CA0   <== the KNOWN assist-shaping task
0xBBA18 -> 0x2351E        0xBBA48 -> 0x14C5C        0xBBA78 -> 0x84656
```
Both independently-known live tasks sit in this array at the same stride ⇒ the structure is real, so
`0x22B24` is a genuine task. **An LE32 scan of this table should be a standing liveness method on this
kit** — it is stronger than "Ghidra defined no function here," which is false-dead on this region four
different ways (`get_function_by_address`, `get_assembly_context`, `disassemble_function`, and
`get_xrefs_to` all return nothing).

**Why the action arm is unreachable in normal driving** — guards upstream of the speed compare:
```
0x2D80A  gp-0x680c == 0 required (state dispatch)
0x2D824  (gp+0x6400) & 0x80 == 0
0x2D82E  gp-0x6814 == 0
0x2D83A  gp-0x6879 == 1   OR   0x2D842  gp-0x6877 == 1      <== THE TRIGGER
0x2D84A  ld.hu gp-0x6a62 vs tp+0x72EE (=320); acts only when speed < 320
```
**★ Both trigger flags come from CAN** [VERIFIED: lead's decode of the writers in `FUN_000524bc`]:
```
0x524E6  st.b gp-0x6879  (0xFEDF1787)      <- (canbyte << 0x1a) >> 0x1f  = bit 5
0x524EA  st.b gp-0x6877  (0xFEDF1789)      <- canbyte >> 7              = bit 7
   source byte = gp-0x1413 = 0xFEDF6BED
```
And **`0xFEDF6BED` is byte 5 of `dest[13]` = `0xFEDF6BE8`**, which under the `dest[i] ↔ id[i+5]` mapping
(§5b) is **CAN `0x17C` = POWERTRAIN_DATA** [VERIFIED: lead's table read]. In opendbc those bit positions
fall inside the undocumented `BOH3_17C` field. **So the trigger is a PCM-sourced request the EPS merely
obeys — normally 0.** (Convenient side effect: openpilot can *observe* those bits on the bus.)

**What it does when it does fire:** `0x2D876` calls `FUN_00045608(5, 0, 55, 164)` (cals `0xC6484`=0,
`0xC6482`=55, `0xC6480`=164 [VERIFIED: lead's byte read]) → sets **authority slot 5's target to 0** →
drives the governor's running MIN to 0 → **multiplies the total steering command by zero.** So it is a
real command-path kill, just remotely gated.

⚠ **Two corrections of record this produced** (see §9):
`FUN_00045608` is an **authority-slot setter**, not "motor off"; and the G1 governor's slot loop covers
**slots 0-5**, not 0-3.

**Still open (none of it blocks the edit):** which PCM function owns those `0x17C` bits (idle-stop assist
handoff / transport mode / service-tool assist-off all fit — **[INFERENCE, unresolved]**); `0xC62EC`=80
(1.25 km/h) at `0x2D9D0` is presumably this task's release hysteresis; and the `0x2D8A2` (state=2) arm was
not followed.

### 6c-bis. The guard table — every live writer, verified
[VERIFIED: lead's independent instruction decode of every site below]

| writer | value | key guard |
|---|---|---|
| `0x293A6` | 1 | `0x2937E ld.bu gp-0x6807` → `0x29382 cmp 2,r6` → `0x29384 bnh` (**ST ≤ 2**) |
| `0x293E4` | 1 | `0x293CA ld.bu gp-0x6807` → `0x293CE cmp 2,r10` → `0x293D0 bnh` (**ST ≤ 2**) |
| `0x2948C` | 1 | mode 3, not-fault: `0x2944A cmp 7,r6` / `0x2944E cmp 4,r6`; ramp saturating at `0x8000` |
| `0x2958C` | 1 | mode 6, not-fault: `0x294CC ld.bu gp-0x6807` / `0x294D4 cmp 4,r6`; ramp saturating |
| `0x29696` `0x296D2` `0x2970E` `0x29724` | **0** | disengage arms — `0x29674 ld.bu gp-0x6807` / `0x29678 cmp 3,r6` **tests ST == 3 directly** |

**The last row is the direct proof:** `STEER_STATUS == 3` is tested explicitly and the arm stores **`r0`
(zero)** into `gp-0x6806`. Combined with the two `cmp 2 / bnh` writers, `STEER_STATUS = 3` both **blocks**
the engage writes and **triggers** the zeroing writes.

**Live/dead split confirmed independently** [VERIFIED: lead's whole-image Format-V `jr`/`jarl` disp22
target scan + LE32 pointer scan]:
- `FUN_00028ea6` — **1 caller** (`jarl` @`0x22522`), 0 pointers ⇒ **LIVE**
- `FUN_0002a30e`, `FUN_0002a93a` — **0 callers, 0 pointers** ⇒ **DEAD** (so the `0x2a3xx-0x2a8xx`
  duplicate writer clusters are inert; ignore them)
- `FUN_00021706` (speed getter) — 1 caller (`jarl` @`0x5233A`) ⇒ sole caller confirmed
- `FUN_00041eec` (voter) — 1 caller (`jarl` @`0x22DAE`)
- `FUN_000522fe` — **0 `jarl` callers but 1 LE32 pointer at `0xBB5A0`** ⇒ it is **dispatched from the RX
  descriptor table**, independently confirming that `0xBB5A0` is that table and that its `+0x00` field is
  the handler.

**Coupling summary:** no `gp-0x6806` writer reads `bVar2`, `gp-0x6a5e`, or the `0xC62EA` cal *directly*.
`bVar2` (`r27`) is tested exactly once — `0x2918E cmp r0,r27` / `0x29190 bne` — and its false arm is the
`STEER_STATUS = 3` write. **The coupling is entirely transitive, through the status byte.** On the
`bVar2`-true path STEER_STATUS becomes 0/1/2 (all pass `≤ 2`), or 4/7 for the *separate* gentle-EME /
DTC-`0x49` states. **So the speed window is the only thing that forces 3, and 3 is the only value in that
set which blocks engage.**

### 6d. ⚠ Interpreting an on-car result — an ambiguity to plan for
`gp-0x69aa == 0x8000` (the derate conjunct) is part of the **same** AND-chain and therefore shares the
**same** `STEER_STATUS = 3` write. **An on-car ST=3 observation cannot distinguish "speed window failed"
from "derate not at unity."** The §3 data is consistent with either; the speed window is simply the only
conjunct that is *provably* speed-dependent.
**If a lowered `0xC62EA` does not restore authority, `gp-0x69aa` is the next suspect.** What's known:
it is a Q15 product of two derate factors (unity = `0x8000`) written at `0x45334`-`0x45342` in the G1
governor `FUN_0004503c` [VERIFIED: lead decoded `mulu`, `shr 0xf`, `st.h gp-0x69aa`]. Whether the MIN
chain can fall below unity at low speed is **NOT established** — trace `r28` and the `FUN_00049a78` (MIN)
inputs at `0x45304`: `gp-0x694c`, `gp-0x6944`, `gp-0x6946`.

### 6d-bis. ★ Correction of record — the G1 governor DOES read vehicle speed
[VERIFIED: lead's instruction decode]
```
0x451E2  ld.hu gp-0x6a64, r10       ; voted speed (slew-limited voter output)
0x45308  ld.hu gp-0x6a64, r14
0x45310  ld.hu tp+0x7316, r16       ; cal 0xC6316 = 640 = 9.99 km/h
0x45314  cmp   r16, r14
0x45316  bc    -> 0x45330           ; speed < ~10 km/h  ==>  SKIP the slew-rate limiter
```
**This falsifies the kit's standing "there is NO vehicle-speed input anywhere in the command/base-assist
path" claim** (`memory/reference-accord-governor-g1-total-command-not-thermal.md` and
`reference-accord-no-vehicle-speed-input-5mph-is-plant.md` on that specific point). Note the *direction*:
below ~10 km/h the rate limiter is **bypassed**, i.e. more responsive at low speed, not more restrictive —
so this is not itself a low-speed lockout.

### 6e. Alternative lever, not examined
`gp-0x68b3` short-circuits the entire window (`0x290EA`; if non-zero the window is ignored). Single
writer `0x4d148`, which sets it only when `gp-0x6a62 == 0` (exact standstill). Forcing it true would
bypass the window wholesale — **broader blast radius than the cal edit, so not recommended**, but recorded
as an option.

---

## 7. ⚠ SAFETY

### 7a. Hard-fault eligibility — computed and cross-checked
Rule: `FUN_0001611e` tests `record[+0x8] & 0x41`, `record = 0xB7D58 + (idx-1)*0x1c`. **Formula anchored
before use** on DTC `0x18` → `0xB7FDC`, `[+8] = 0x3D01` ✓, with controls reproducing the kit's record
exactly (`0x17`/`0x1c`/`0x1d` HARD, `0x49` not-hard).

| DTC | `record[+8]` | verdict |
|---|---|---|
| `KFC_WHEELSPD_PLAUSI` | `0x0C01` / `0x1C01` | **HARD-FAULT → motor-off** |
| `KFC_VSA_1D0` | `0x2D01` | **HARD-FAULT → motor-off** |
| `KFC_VSA_1D0_SNA` | `0x0000` | not eligible |
| `KFC_WHEEL_SPEED` | `0x0100` | not eligible |

Name-table index ≠ fault index is unproven, so both `idx` and `idx+1` were tested — **identical verdict
under both**. Computed independently by two parties with **no disagreement**.
(Do not assert the name↔index alignment elsewhere: a tp-relative scan found 0 accesses within ±0x40 of
either `0xBAEA0` or `0xB7D58`; both are reached register-indirect.)

**Mitigation for this specific edit:** the `0x1D0` handler's validity flags come from **CAN SNA bits**
(`FUN_00052cce`/`FUN_00052d5e` bit extractors), not from any locally computed magnitude window, and none
of its 48 outputs is read anywhere in `[0x28000,0x46000)` — a verified zero, with the `0x1EA` handler as
a positive control showing the method does find real links. **So editing the `[320,12800]` window does
not touch the plausibility/motor-off path.**

### 7b. Standing rules that apply
1. **Never tamper with the speed value, its scaling, or its validity** — that is what risks the
   motor-off DTCs above. Change only the **comparison**.
2. **GATE 1 — RAM ownership** for any new cell (full footprint, *including writers* and register-indirect
   access). `gp-0x1401..0x1502` is poison — §5b shows why: that range **is** the CAN RX buffer region.
   Check candidates against `+0x18` of every `0xBB5A0` record.
3. **GATE 2 — closed-loop stability** for anything touching dynamics. A threshold change probably doesn't
   engage GATE 2, but the enable path has hard-shutdown monitors — justify explicitly, don't assume.
4. **int/float mirrors:** many int cals have float twins that must be edited bit-exactly or the
   no-debounce DTC `0x1c`/`0x1d` monitors trip → motor-off. **`0xC62E8`/`0xC62EA` have no mirror** (both
   plain `ld.hu`). The nearby mirror `0xC6554-0xC6560` = `[300.0,800.0,0.5,1.0]` (int side
   `0xD209C`/`0xD20A8`) is a **separate record** — don't run them together.
5. **CRC:** the chain is **50 blocks**, `0x1000` each with the word at `+0xFFC`. `0xC62EA` lives in the
   **`0xC6000`** block (CRC `0xC6FFC`) — **already in every build's `TOUCHED_BLOCKS`, so no new block is
   needed.** For reference: `0xD0000`, `0xD2000`, `0xB7000` are **not** currently included and would have
   to be added if ever edited. `0xC4FFC` is *not* the end of coverage (V38 already edits
   `0xE4000`/`0xE5000`). A stale block CRC is implicated in the V40 ignition-fault brick.
6. **Code caves are this kit's only bricking class** (V24, V27, V48B all faulted). This fix should need
   none — but if it ever does, prefer an in-place single-instruction edit (V42 precedent: one branch
   nibble at `0x454FE`).
7. **Re-import Ghidra fresh** before any pre-flash re-disassembly: a stale open program has twice returned
   pre-edit bytes while the on-disk SHA verified correctly.

---

## 8. Plan for the next session

1. **Build:** `0xC62EA` = 320 → a small value. **`0xC62EE` stays stock** (§6c). **Do not use 0** — the
   `gp-0x68b3` standstill bypass already covers exactly-zero, and 0 would make the lower bound
   unconditionally true, changing behaviour in ways the window's designers may rely on elsewhere. A value
   like **64 (1 km/h)** or **32 (0.5 km/h)** preserves a sanity floor while clearing the 0.67-3.5 mph
   band openpilot actually needs. Keep `0xC62E8` (200 km/h) untouched.
3. **Verify the build:** full byte diff (expect exactly 2 bytes + the `0xC6FFC` CRC word), 50/50 CRC,
   x31 round-trip, RWD readback, fresh-Ghidra re-disasm of `0x28EB6`/`0x28EBC` confirming the new value.
4. **Consider telemetry first.** The kit has a **built, lead-verified, unflashed** new-ID CAN-TX
   capability (`FOURFRAME`, `build_vfourframe_tva.py`, mailboxes 16-19, IDs `0x6a0-0x6a3`, 16 signals at
   62.5 Hz, visible on a **red panda** on the EPS bus — the comma gateway whitelists IDs and drops them).
   Streaming `gp-0x6a5e`, `gp-0x6806`, `gp-0x6807` and the AND-chain conjuncts would confirm the model
   before any behavioural edit. These are the kit's first active-TX caves — doubly operator-gated.
5. **On-car validation plan:** flash, then *parked first*, then a low-speed lot. Watch raw CAN 399 for
   `STEER_CONTROL_ACTIVE` going 1 below 3 mph — that is the success criterion, directly observable, and
   `analysis-2020accord/speed_efficacy_test.py` already computes it.
6. **Then** ship the openpilot `steerAtStandstill = True` one-liner (§2) if steering to a dead stop is
   wanted, and re-record to close the <0.3 m/s data gap.

### Cheap non-flash diagnostic — offered, NOT recommended without discussion
Because `0x158` is *received*, a parked test could inject a spoofed `XMISSION_SPEED2` and watch whether
`STEER_CONTROL_ACTIVE` asserts at standstill — confirming the whole model with **no firmware change**.
⚠ It means **transmitting on the live steering bus** (operator's iron rule: explicit authorisation, exact
payload confirmed first); the real PCM keeps sending `0x158`, so two senders with mismatched
counter/checksum will likely set DTCs in several modules; other ECUs consume the same message.
**Discuss before attempting.**

---

## 9. Corrections of record

Propose folding into `memory/` + `MEMORY.md` (operator's call):

1. **`reference_accord_sub3mph_lkas_openpilot_gate.md` is WRONG on its central claim.**
   `CP.minSteerSpeed = 0.0`; `values.py:163` is `HondaCarDocs` metadata. The real OP floor is the
   hardcoded `0.3` m/s in `controlsd.py:178`, bypassable only via `steerAtStandstill`. §2.
2. **`reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md`'s top-level inference is
   FALSIFIED** — `STEER_STATUS=3` tracks *speed*, and the EPS genuinely declines authority. Its Findings
   1+2 (no speed reads *inside* arbitration) still stand: the window lives in `FUN_00028ea6`, upstream.
3. **NEW: the speed window is `0xC62EA`=320 (5 km/h) / `0xC62E8`=12800 (200 km/h), unit 64 counts/km/h.**
   §4.
4. **NEW: `STEER_CONTROL_ACTIVE = gp-0x6806 & 1`** (packer `shl 3`). 🛑 **And the kit's
   "`STEER_STATUS=3` is REPORT-ONLY" verdict is CORRECTED** — the load-bearing reader is *intra-function*
   (`cmp 0x2` at `0x29382`, gating both `gp-0x6806` and the authority ramp `gp-0x69b0`). An
   "external readers" sweep cannot establish report-only status. §6a/§6b.
4b. **NEW: `FUN_000522fe` scaling is `×41 >> 6` with `MIN(·,0x7fff)`** — the Clarity's `/50` + `510` clamp
   does **not** exist here. **`gp-0x6a46` is SHADOWED** (`gp-0x4ca4`, mismatch → `FUN_0006b9fa`). §4b-bis.
4c. **NEW: a second 320-count gate at `0xC62EE`** → `gp-0x680c`, in the unanalyzed `0x2d5xx-0x2dbxx`
   region. Role unestablished. §6c.
5. **NEW: RX descriptor table at `0xBB5A0`** (stride `0x20`, ID `+0x12`, dest `+0x18`, handler `+0x00`);
   the `0xB733C`/`0xB739C` arrays are **not** index-parallel (`dest[i] ↔ id[i+5]`). §5b.
6. **NEW: wheel-speed DTC eligibility** — `KFC_WHEELSPD_PLAUSI` and `KFC_VSA_1D0` are motor-off eligible.
   §7a.
7. **NEW: `0xC6518`/`0xC6534` readers found (`FUN_00039702`), and the axis is THERMAL, not speed** —
   closes a long-standing "no known reader" item. The sibling `0xC6BA0` (count 13,
   `X=[0,34,64,85,100,120,140,157.6…] → Y=[0.878…1.059]`) is a magnet-temperature Kt curve; `0xC6518`
   contains 25 (reference temp) and its Y falls 12000→7000 like a current derate; the axis is thresholded
   at `cal(0xC62D8)/64 = 60.0`. **Do not treat `0xC6530`=200.0 as a speed clamp.**
8. **NEW methodology — four scan traps, each of which produced a wrong conclusion this session:**
   (a) never require "two-sided compare **followed by a boolean store**" — the boolean may never reach
       memory (§4d);
   (b) the `(lo,hi)`-adjacent-int16 heuristic is confounded by `[count][X][Y]` LERP records (§4e);
   (c) `ld.bu`/`ld.hu` encode `hw2 = disp|1`, so exact-even-displacement scans are blind to every byte
       load (§5d);
   (d) **a scan that filters out `reg2 == 0` silently drops every store-of-zero.** `reg2` is the *source*
       register for stores, and `st.b r0, disp16[gp]` is the `var = 0` idiom. Correct rule: skip
       `reg2 == 0` only for the load opcodes (`0x38`/`0x39`/`0x3C`-`0x3F`); **keep it for stores
       (`0x3A`/`0x3B`)**. ⚠ `st.b r0, disp16[gp]` and the 6-byte extended escape have **byte-identical
       `hw1`** (both `0x0744` for op `0x3A` on gp) — they are distinguished only by opcode class.
   (e) **an "external readers" sweep cannot establish that a variable is report-only** — check
       intra-function reads (§6b);
   (f) **★ Format-V `jr`/`jarl` and `ld.bu` SHARE the opcode field `0x3C`** (`hw1` bits 10..6 =
       `0b11110`). They are distinguished **only by `hw2` bit 0**: `hw2 & 1` ⇒ `ld.bu`, else branch.
       **Omitting that test gave the lead a 44% false-positive rate — 10,105 spurious "call sites" out of
       22,850** [VERIFIED: lead ran the scan both ways]. It produced one wrong result I reported
       (a phantom `0x28986` → `0x2D7C6` call, actually a window straddling two `movhi`; the tell is
       `reg2 = 7`, which is neither `0` (`jr`) nor `31` (`jarl lp`)). Correct filter:
       ```python
       if (hw1 >> 6) & 0x1F != 0x1E: not a branch
       if hw2 & 1:                   it's ld.bu, not a branch
       disp = ((hw1 & 0x3F) << 16) | hw2      # sign-extend bit 21; reg2 = hw1>>11 (0 = jr)
       ```
       Sanity-check any claimed caller by requiring `reg2 ∈ {0, 31}`.
   (g) **"Ghidra defined no function here" ≠ dead.** On `0x2d5xx-0x2dbxx`, four Ghidra methods all
       returned nothing for a region that is a **live RTOS task**. Use the task-control-block array at
       `0xBB928` (stride `0x30`, entry at `+0x08`) as a liveness oracle — it self-validates against the
       two independently-known tasks `0x2214A` and `0x22CA0` (§6c).
9b. **NEW: `FUN_000522fe` is dispatched from the `0xBB5A0` descriptor table** (0 `jarl` callers, 1 LE32
   pointer at the table), independently confirming the table's `+0x00` handler field. `FUN_0002a30e` and
   `FUN_0002a93a` confirmed DEAD by a whole-image call-site + pointer scan. §6c-bis.
9d. **⚠ CORRECTION: `FUN_00045608` is NOT "motor off."** It is a generic **authority-slot setter**
   (guard `idx < 7`) writing three parallel 7-slot u16 arrays: target `gp-0x652c+2i`, up-rate
   `gp-0x64fc+2i`, down-rate `gp-0x6514+2i`. The **G1 governor `FUN_0004503c` consumes them**
   (`movea -0x652c, gp, r20` @`0x450C6` [VERIFIED: lead decoded op `0x31` = `movea`, reg2=r20, reg1=gp]),
   accumulating a **running MIN** (`FUN_00049a78` = unsigned MIN) that becomes a **Q15 authority scale on
   the TOTAL command**: `gp-0x6ace = (clamp(gp-0x6b94) * MIN) >> 15`.
   So CLAUDE.md's `FUN_00045608(3,0,0x8000,0x8000)` = "motor off" is really **slot 3's target set to 0
   with instant slew** — the *effect* (command × 0) is right, the *mechanism label* is wrong. Worth
   relabelling wherever the V25/V26 brick narrative cites it.
9e. **⚠ CORRECTION: the governor's slot loop covers slots 0-5, not 0-3.** `bVar3 = iVar20 != 1` is
   evaluated *after* the do-while body (3 passes × 2 elements), then an unrolled block handles slot 6.
   **Slot 5 IS processed** — which is exactly why the `0xC62EE` shutdown path writing slot 5 is effective.
9f. **NEW: the `0x2D876` shutdown call is `FUN_00045608(5, 0, 55, 164)`** from cals `0xC6484`=0,
   `0xC6482`=55, `0xC6480`=164 [VERIFIED: lead's byte read].
9c. **NEW: the G1 governor reads vehicle speed** (`gp-0x6a64` at `0x451E2`/`0x45308` vs cal `0xC6316`
   = 640 ≈ 10 km/h), which **falsifies "no vehicle-speed input anywhere in the command path."** Below
   ~10 km/h the slew limiter is bypassed. §6d-bis.
9. **My own two retractions, for the record:** I wrongly "corrected" the legacy `0xFEDF6BD8`↔LKAS claim
   (it was right; only its slot index was off) — §5b; and I wrongly concluded the CAN mailboxes are
   register-indirect only — §5d.
10. **⚠ HIGH-IMPACT — now corroborated by TWO independent traces, but still needs its own verification
    pass before the vibration record is rewritten:** **`gp-0x6a5e` is voted VEHICLE SPEED, not voted
    driver/column torque**, and so are `gp-0x6a62` and `gp-0x6a64` — all three are assigned from the
    wheel-speed voter `FUN_00041eec` (`gp-0x6a5e` sole writer `0x42342`, `gp-0x6a64` sole writer
    `0x42360`). Two agents reached this independently. Supporting: it is read
    `ld.hu` (unsigned); it is the output of the speed voter `FUN_00041eec`; the V44/V47 "Factor C" axis
    `[2240,3840,5120,8960]` is `/64 = [35,60,80,140]` km/h exactly (lead-verified bytes). If true this
    would mean (i) Factor C is a speed-scheduled ramp — zero damping **below 35 km/h**, not "hands-off"
    (note the 3-8 m/s buzz regime = 10.8-28.8 km/h sits entirely below `X[0]`, so V44's *direction*
    survives but its stated mechanism does not); (ii) the gentle-EME gate `gp-0x6a62 >= 0xC6312` = 320 is
    **speed ≥ 5 km/h**, not torque ≥ 320 — lead-verified that `0xC6312` = 320 = 5.000 km/h exactly; and
    (iii) the standing "no vehicle-speed input anywhere in the command/base-assist path" claim is
    falsified. **This reaches into the vibration lineage and the V33/V36/V37 framing. It must get its own
    verification pass before anything is rewritten on it.** Note `memory/reference-accord-no-vehicle-
    speed-input-5mph-is-plant.md`'s *empirical* content (band power vs speed) is unaffected either way.

---

## 10. Artefacts

- `analysis-2020accord/speed_status_engagement.py` — speed × STEER_STATUS × latActive correlation.
- `analysis-2020accord/speed_efficacy_test.py` — the gate-vs-label test (`STEER_CONTROL_ACTIVE`,
  `STEER_ANGLE_RATE`, commanded torque). **This computes the on-car success criterion for the fix.**
- Lead verification scripts (scratchpad, uncommitted): RX table decode, DTC hard-fault eligibility,
  gp/tp encoding anchor + buffer-reader enumeration, packer bit-source decode, `gp-0x6806` writer/reader
  enumeration, third independent efficacy decoder.
- ⚠ **Several local rlog segments are truncated such that capnp aborts the interpreter natively** (not a
  catchable Python exception). Any rlog sweep must run **one segment per subprocess** or it stops early
  and silently. 1-2 of 54 segments affected.

**Nothing here has been flashed. No RWD was built. No CAN was sent.**
