---
name: reference_accord_fun757a2_iqid_gainschedule_bridge_resolved
description: RESOLVED — FUN_000757a2's 6-branch LERP cluster is NOT a rotor-angle/cogging table. It is a speed-gated (creep <10km/h vs highway) gain-schedule for the FOC core's Iq/Id current-loop PI+feedforward gains, indexed by an instantaneous phase-current-derived power/torque estimate computed in the FOC core itself. Closes the open Iq/Id bridge question from [[reference_accord_fun757a2_torque_model_and_lerp6_cluster]].
metadata:
  type: reference
---

# The FUN_000757a2 <-> FUN_00071272 closed loop, fully traced (2026-08-04/05)

Follow-up to [[reference_accord_fun757a2_torque_model_and_lerp6_cluster]] — resolves that memory's
Open Items #1 (`fStack_b8`'s producer) and #3 (the real Iq/Id bridge; `FUN_0006964c`/`FUN_0007d16a`
were NOT it).

## The index (EVIDENCE, decompile-traced byte-exact)

`fStack_b8` (the shared LERP fractional index, `fVar46 = fStack_b8*16.0`) = `unaff_gp[-0x29]` =
`local_c8[5]`, where `local_c8` = pointer returned by `FUN_00082560(&local_c8)`. That function
(disasm-confirmed: `movea -0x26e8,gp,r14; ld.h -0x2786[gp],r15; cmp r0,r15; bne skip; addi 0x24,r14,r14`)
selects one of TWO adjacent 9-float (0x24-byte) RAM structs — `gp-0x26e8` or `gp-0x26c4` — via a
ping-pong flag at `gp-0x2786`. `local_c8[5]` = offset `0x14` into whichever struct = **`gp-0x4ac` at
the moment it was captured**.

**`gp-0x2786` is a genuine double-buffer flag, not a mode select.** Its ONLY writer is
`FUN_00082550` (`*flag = (*flag==0)`), a strict 0/1 flip. `FUN_0008253c` (get, no flip: base =
`gp-0x26e8 + flag*0x24`) and `FUN_00082550` (flip) are called ONLY from **`FUN_00071272`** (the FOC
core / 4kHz ADC ISR) — confirmed single-caller via `get_xrefs_to`. `FUN_00082560` (get, flip-aware
inverse logic) is called ONLY from `FUN_000757a2`. The polarity is deliberately inverted between the
writer-side and reader-side accessor so the reader always sees the writer's most-recently-completed
slot (worked through by hand: flag=0 -> writer writes slot0, flips to 1 -> reader-with-flag=1 reads
slot0 = same slot). **This is a real, coherent, torn-read-safe 4kHz-to-1kHz bridge.**

**`gp-0x4ac` itself (EVIDENCE, decompile `0x75322`/`0x2320`-ish region of `FUN_00071272`)**:
```
fVar18 = -(fVar33*1.1547005 - fVar42*-0.57735026)          // Clarke-shaped combo (2/sqrt3, 1/sqrt3)
fVar50 = -(sin(theta)*fVar42 - cos(theta)*fVar18)           // Park-rotate -> Id-like
fVar35' =  cos(theta)*fVar42 + sin(theta)*fVar18            // Park-rotate -> Iq-like
gp-0x4ac = fVar33*fStack_7c + fVar42*fStack_84 + fStack_80*(-fVar42-fVar33)
         = fVar33*(fStack_7c-fStack_80) + fVar42*(fStack_84-fStack_80)
```
`fVar33`/`fVar42` = **peak-hold (not raw-instantaneous) magnitude trackers** of two phase-current-
related quantities (`gp-0x43c`/`gp-0x444`, each compared/clamped against cal `tp+0x6580`=`0xC5580`
every cycle, saturation flags -> byte at `gp-0x4b0`). `fStack_7c/80/84` = `*(gp-0x38c/0x390/0x394)`,
a **3-float per-phase reference record**, refreshed each cycle from an 8-entry x 3-float RAM array at
`gp-0x4a8` via a FIXED (build-time cal, `tp+0x6708`=`0xC5708`, NOT live-varying) index — this is a
static selector, NOT a real-time rotor-sector index (see "Per-sector branch — closed negative" below).
`gp-0x4a8[0]` is ALSO written directly with live float values elsewhere in the same function
(`gp-0x4a8 = fVar50` @ decompile line 1376, `= fVar33` @ 2874) — so the array is a genuine runtime
ring/shift-register, not pure cal data; its full character was not exhaustively resolved this session.

**Verdict: `gp-0x4ac` is an ABC-frame instantaneous electrical POWER/TORQUE-like estimate
(`Ia*(Ea-Ec)+Ib*(Eb-Ec)` with `Ic` eliminated), built from phase-current peak-trackers — NOT rotor
angle, NOT a cyclometric/angle quantity of any kind.**

## The 6-LERP cluster (EVIDENCE) — a speed-gated Iq/Id PI+feedforward gain schedule, not a ripple table

Branch select (decompile, `FUN_000757a2`): `if (*(ushort*)(gp-0x6a5e) < *(ushort*)(tp+0x60da))` —
**`gp-0x6a5e` = VOTED VEHICLE SPEED** per [[reference_accord_gp6a5e_is_voted_vehicle_speed]].
`tp+0x60da` = `0xC50DA` reads **640** (raw byte scan, stock) = **10 km/h** at the established
64 counts/km/h scale. **This IS the creep/highway split the operator's symptom sits on.**

Both branches populate the SAME 6 (Y-table-pointer, gain) pairs plus one shared X-axis pointer, then
run ONE bracket search + 6 independent scaled LERPs sharing that one fraction. Table pointers and
final destinations (traced through the whole chain into `FUN_00071272`, decompile line ~2320-2380):

| LERP# | Y-ptr slot | gain slot | dest (write, `FUN_000757a2`) | dest (`FUN_00071272`, via `FUN_00082524` ping-pong) | role in current loop |
|---|---|---|---|---|---|
| 1 | `-0xa3` | `-0xa1` | `gp[0x12]` | `gp-0x4e8` | **Ki, Iq loop** (integrator gain) |
| 2 | `-0x9e` | `-0x9c` | `gp[0x13]` | `gp-0x4d0` | **Kff, Id loop** |
| 3 | `-0xad` | `-0xab` | `gp[0x10]` | `gp-0x4ec` | **Kx, Iq loop** (multiplies the *error*, not the integrator) |
| 4 | `-0xa8` | `-0xa6` | `gp[0x11]` | `gp-0x4d4` | **Kx, Id loop** |
| 5 | `-0xb7` | `-0xb5` | `gp[0x14]` | `gp-0x4f0` | **Kff, Iq loop** (multiplies the *reference*) |
| 6 | `-0xb2` | `-0xb0` | `gp[0x15]` | `gp-0x4d8` | **Ki, Id loop** |

The bridge back into `FUN_00071272` is via a SECOND ping-pong pair — `FUN_00082500`/`FUN_00082514`
(writer side, called only from `FUN_000757a2`) and `FUN_00082524` (reader side, called only from
`FUN_00071272`, at `0x713cc`) — a 19-float struct at `gp-0x2780`/`gp-0x2734`, flag `gp-0x2788`. Fields
0-5 of that struct are exactly the 6 LERP outputs above.

**In `FUN_00071272`, decompile ~2320-2380, the Iq and Id loops both take this shape** (Iq shown,
Id is the mirror using the "2/4/6" column):
```
error = Iq_ref(gp-0x458) - Iq_fb(fVar35, the Park-rotated value)
integrator(gp-0x3b4) += error * Ki(gp-0x4e8)          // clamped +-4194304
output = integrator + Iq_ref*Kff(gp-0x4f0) + error*Kx(gp-0x4ec)   // clamped
```
This is a genuine **gain-scheduled PI-plus-feedforward current-loop controller**, closing directly
inside the 4kHz FOC ISR. **This CORRECTS the "model-based FOC with no isolated PI gains" belief in
prior handoffs — isolated, gain-scheduled Ki/Kx/Kff terms for BOTH Iq and Id exist and are indexed by
the torque/power estimate above.**

## Breakpoint dump (byte-exact, Python/PowerShell raw read of stock `code.bin`, all `0xC5xxx`)

Creep branch (speed < 640 = 10 km/h), shared X = `[50, 700, 2100, 3500]` (all 6 tables, N=4):
| dest | Y values | /2048 |
|---|---|---|
| Ki_Iq (gp-0x4e8) | 512,512,451,246 | .25,.25,.220,.120 |
| Kff_Id (gp-0x4d0) | 800,800,819,676 | .391,.391,.400,.330 |
| Kx_Iq (gp-0x4ec) | 4096,4096,3584,2007 | 2.0,2.0,1.75,.980 |
| Kx_Id (gp-0x4d4) | **2990,10000,8000,4997** | 1.46,4.88,3.91,2.44 |
| Kff_Iq (gp-0x4f0) | 205,205,205,205 (flat) | .1001 x4 |
| Ki_Id (gp-0x4d8) | 205,205,205,205 (flat) | .1001 x4 |

Highway branch (speed >= 640), X = `[700,1000,2000,4000]` for the Iq-column tables and
`[0,1800,2200,4000]` for the Id-column tables (N=4 each). Iq-column Y values are BYTE-IDENTICAL to the
creep branch's Iq column (only the X breakpoints shift) — Ki_Iq/Kx_Iq/Kff_Iq schedules are literally
the same shape, just re-keyed to a higher torque range. Id-column values differ more:
Kx_Id=`12300,12500,10000,6000`, Ki_Id=`1760,1540,1150,700` (NOT flat at highway speed, unlike creep).

**Standout finding**: the creep branch's Kx_Id table has the steepest slope of the entire 12-table
set — `(10000-2990)/(700-50) = +10.78/count`, a 3.3x gain swing crammed into the FIRST 650-count
window of the index, i.e. right at the low-torque end that light creep-speed steering corrections
would sit in. This is the strongest concrete candidate this session found for a coarse-breakpoint
gain-schedule chatter mechanism specific to creep speed. **Not verified against telemetry — the
absolute physical scale/units of `gp-0x4ac` (hence how much real driver torque maps to the 50->700
window) was not fully derived; the per-phase reference floats' own units trace back to a cal default
at `tp+0x65cc`=`0xC55CC` and the partially-live `gp-0x4a8` ring array, neither pinned to physical
units this session.**

## Per-sector branch candidate — closed negative

The `gp-0x4a8` 8-entry array's selector `sVar32` (`tp+0x6708`=`0xC5708`) is a **fixed build-time
cal short, read fresh every cycle but never varying with rotor position at runtime** — confirmed by
it being a plain `tp`-relative literal load, not a function of `theta`/sector state anywhere in the
surrounding code. **This closes the "per-sector/per-sextant FOC branch" candidate as NOT a live,
angle-varying mechanism** — it's a static hardware/variant selector, not a real-time sector index.

## Blast radius (EVIDENCE)

- **All 12 table blocks (both branches, all 6 outputs) live in `[0xC5462,0xC5540]`ish, fully inside
  the CRC-skipped `[0xC5000,0xC5FFC)` block** (V40 ignition-brick precedent). Any edit here, even
  data-only, is out of bounds per this kit's hard constraints.
- `FUN_00071272` = the FOC core, single caller `FUN_0006404c` (the ADC ISR per established memory),
  4kHz, DTC-0x18 cadence-watchdog territory.
- `FUN_000757a2` = 1kHz, `mask 0xc30` aggregator-gated, bookended by the `FUN_00071166`/`FUN_00071042`
  shadow-checksum pair (DTC-0x16-class hard fault on mismatch) per
  [[reference_accord_fun757a2_torque_model_and_lerp6_cluster]] — unchanged by this session's findings.
- **grepped `analysis-2020accord/build_v*_tva.py` for every specific table/count address found this
  session (`0xC544C/C54C4/C5474/C54EC/C549C/C5514/C5460/C54D8/C5488/C5500/C54B0/C5528`, and the speed
  threshold `0xC50DA`): zero hits.** This is genuinely new, never-proposed territory — not a
  previously-falsified lever.
- **No lever recommended.** The hard constraint on `[0xC5000,0xC5FFC)` rules out editing the tables
  even though the Kx_Id creep-branch steepness is a concrete, well-evidenced mechanism.

## Related
[[reference_accord_fun757a2_torque_model_and_lerp6_cluster]] — the original discovery; its Open Items
#1 and #3 are resolved here. [[reference_accord_gp6a5e_is_voted_vehicle_speed]] — the speed signal
gating the branch. [[reference_accord_foc_inner_current_loop_architecture]] — the FOC ISR chain this
loop closes inside; its "no isolated PI gains" characterization needs revision per this memory.
