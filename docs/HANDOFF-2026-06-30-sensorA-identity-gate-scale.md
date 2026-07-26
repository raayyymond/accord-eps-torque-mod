# HANDOFF — 2026-06-30 — gentle-EME gate: sensor-A identity proven, scale is the blocker

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **Currently flashed: V31** (2× LKAS + boost floor).
**STOCK Ghidra program** = `code.bin` (`/master.bin`, 2113 fns). ⚠ NEVER analyze `../accord-firmware/analysis-2020accord/_v27_plain_image.bin`.
**Bases:** `gp = 0xFEDF8000`, `tp = 0xBF000`. All facts below Ghidra-verified THIS session unless marked.

Supersedes the open questions in `docs/HANDOFF-2026-06-29-gentle-eme-v32.md`. Read that first for the road data
(5 logged gentle-EME events, the rlog decoders, the CAN signature). This handoff replaces its §5/§6 scale story
and its STEP-1 plan.

---

## 0. The one-line state

The gentle EME (LKAS-only torque cut, `STEER_STATUS=no_torque_alert_2`, no DTC) fires when **`gp-0x6a62 ≥ cal
0xC6312 = 320`**. The fix is to **raise `0xC6312`** (cal-only, lockstep-clean — see §3 of the v32 handoff). The
ONLY thing blocking the build is **choosing the value**, and that requires knowing the scale of `gp-0x6a62`
in physical torque — which, as proven below, **cannot be derived statically and cannot be read off the CAN
`STEER_TORQUE_SENSOR`** (that's a *different sensor*). **Next session: live-RAM read of `gp-0x6a62`
(`0xFEDF159E`); the operator will provide the read guide.**

---

## 1. The gate — VERIFIED, with this session's corrections

`FUN_00040d58` (the engage-SM driver-torque disengage decider), param 2 (ENGAGED) and param 3 (HOLDING) branches:
```
if (gp-0x6a62 != 0xffff && gp-0x6a62 < cal[tp+0x7312]=0xC6312=320)  -> stay engaged
else                                                                -> return 2 = DISENGAGE   (NO debounce)
```
Confirmed: `0xC6312 = 40 01 LE = 320`. The **cal** is read (`ld.hu 0x7312[r5=tp]`) at exactly 3 sites, all in
`FUN_00040d58` (`0x40db8 / 0x40dd0 / 0x40df4`). ⚠ **Corrected 2026-07-02 (radare2 v850.gnu-verified):** the
neighboring `0x40dae / 0x40dc6 / 0x40dea` are the **`gp-0x6a62` *value* reads** (`ld.hu -0x6a62[r4=gp]`), NOT
the cal — the base-register field (r5=tp for the cal vs r4=gp for the value) was decoded straight from the
instruction bytes, so this is not a gp/tp or tool ambiguity.

**Corrections to the 2026-06-29 handoff (walked the disasm this session):**
- **`FUN_00040e74` is NOT the CAN-signature writer.** It is a one-liner: `gp-0x35b5 = gp-0x35b6` (commits the
  substate byte). The decider only sets the substate byte `gp-0x35b6`; the engaged handler `FUN_00041222`
  consumes the return and drives the dispatcher state `gp-0x679c` via `FUN_00040d38(n)`.
- **The CAN-signature bytes are written indirectly.** `gp-0x6806` (CONTROL_ACTIVE), `gp-0x6807` (STEER_STATUS),
  `gp-0x6809` (deliver flag) have **zero gp-relative stores** in all 185k instructions — written via a
  pointer/struct path (unresolved, as before). This does NOT weaken the lever: in the ENGAGED/HOLDING states the
  ONLY disengage condition is `gp-0x6a62 ≥ 320`, so a mid-drive LKAS cut on a torque spike must be this gate.

---

## 2. What `gp-0x6a62` actually is — the voter transfer function (NEW, replaces the "lag" story)

`gp-0x6a62` is produced by the torque voter `FUN_00041eec`. The exact transfer function (read this session):

```
gp-0x6a62 = MAX( |ch1|,|ch2|,|ch3|,|ch4|,|ch5| )      # MAX of the 5 coil-track magnitudes
   on a RISING edge:  taken instantaneously, NO filter
   on a FALLING edge: slew-limited, 16 counts / voter-cycle  (cal 0xC64ED = 0x10)
   clamp 32000
```

**This kills the 2026-06-29 "rate-limit lags, so it crosses 320 while CAN reads ~1633" hypothesis.** The
rate-limiter is **decay-only**; on a rising transient (the EME trigger) `gp-0x6a62` tracks the **instantaneous
peak coil** with no attenuation. The 16/cycle decay only governs *recovery* (and matches the observed
~0.1–1 s re-arm; cross-checks the re-engage ramp `0xC64DE = 17`).

Two consequences:
- The gate is the **most sensitive** available signal: max-of-5-coils, no debounce → a single coil spiking past
  the threshold for one cycle trips it. This fits "**hard turn + bump**" on every logged event (a mechanical jolt
  spikes one coil).
- The threshold value must clear the **peak of `gp-0x6a62`** during legitimate hard turns — and `gp-0x6a62` is
  NOT the CAN torque signal (see §3), so the road-data CAN statistics cannot be used directly.

---

## 3. THE SCALE BLOCKER — `gp-0x6a62` (gate) and CAN `STEER_TORQUE_SENSOR` are DIFFERENT SENSORS

This is the central finding and why a live read is mandatory. There are **two independent column-torque
acquisitions** (full detail in `reference_accord_dual_torque_sensor_architecture.md`):

| | **Sensor A** = the gate signal | **Sensor B** = the CAN signal |
|---|---|---|
| RAM | `gp-0x6a62` (max), `gp-0x6a5e` (avg) | `gp-0x4f60` |
| transport | **DMA** 8-byte frame → `gp-0x1450` → `gp-0x13e0` | status-flagged FIFO → `gp-0x578` → de-frame |
| structure | 5 bit-packed coil tracks, voted | dual sub-channel (`gp-0x548`+`gp-0x544`) |
| integrity | spread + continuity vote | **4-bit CRC** per channel |
| scaling | `× 41/64` only | per-sensor + **learned** gain/offset (`gp-0x698c`/`gp-0x6b50`) |
| extra | torque only | **torque + absolute ANGLE + temp** (a TAS) |
| reported on CAN | no | yes (`STEER_TORQUE_SENSOR = -(gp-0x4f60 ×125/128)`) |

Because each carries its own (learned/embedded) calibration, **there is no static numeric bridge** between
`gp-0x6a62` and the CAN torque. The old "~1:1" claim had no basis. The road data (CAN, sensor B) shows the EME
onset at CAN ~1239–2290, with the gate at 320 — i.e. the gate scale is *much smaller* than CAN, but the exact
ratio is unpinnable on paper. **The only way to choose `0xC6312` correctly is to read `gp-0x6a62` live.**

---

## 4. Sensor A IS driver column torque — proven (so the lever is the right one)

Independent, non-circular evidence assembled this session (so we're not trusting old labels):
1. **Boost:** `gp-0x6a5e` indexes a monotonically increasing assist curve (table `0xce578`: breakpoints
   `[0,640,2560,5120,8960,12800]` → values `[612,787,992,1141,1211,1238]`), and that value is **multiplied**
   into the motor torque command in `FUN_00034a72`. More driver torque → more assist. That is power-steering.
2. **Fused with the confirmed CAN torque sensor:** in `m_steer_torque_arbitration`, sensor A (`gp-0x6a5e`) is the
   assist-curve axis and sensor B (`gp-0x4f60`) provides sign + a `±25600` fault-guard — two sensors fused as one
   quantity.
3. **Voting:** the 5 tracks are voted as redundant measurements of one quantity (spread + continuity checks).
4. **Diagnostics** log `gp-0x6a5e`, `gp-0x4f60`, delivered `gp-0x6b98` side-by-side as the torque items
   (`FUN_0001c1ce`).

**Plausibility test clarified:** the voter's `gp-0x67f4` plausibility is set when `|previous gp-0x6a5e − new
voted| < 65` — both are sensor A's own output. It is an **intra-sensor-A** continuity + channel-agreement check,
**NOT** an A-vs-B comparison.

**"Sensor A caps LKAS authority" — RETRACTED as torque-dependent.** The arbitration setpoint-limit
`g_pArbSetpointLimitCurves` (`0xCB844`, 8 mode tables at `0xE4180…`) IS indexed by `gp-0x6a5e`, but every table
is calibrated **FLAT = 15360** across the whole axis and is mode-invariant. So it is a **constant ±15360** clip,
not a sensor-A-modulated cap. (Matches the existing repo memory `reference_accord_arbitration_limit_family.md`,
which also notes the real LKAS high-end binder is the arb output gain `0xC646C=891`.) Sensor A's solid effects on
delivered torque are the **disengage gate** (`gp-0x6a62 ≥ 320`) and the **boost multiplier** (`0xce578`).

---

## 5. NEXT STEPS (the next session resumes here)

### STEP 1 — Live-RAM read of `gp-0x6a62` (operator is providing the read guide)
Read `gp-0x6a62` = **`0xFEDF159E`** (and optionally the CAN-side `gp-0x4f60` = `0xFEDF30A0`) on the car. Targets:
- A few **held-torque** points (gentle / medium / firm grab) → the linear `gp-0x6a62`-per-physical-torque scale.
- Ideally a **hard hands-off turn (+ bump)** like the logged events → the *peak* `gp-0x6a62` during a legitimate
  maneuver (this is the number the threshold must clear). `gp-0x6a62` is unfiltered on the rise, so a fast sample
  catches the true peak.
- Note: `0xFEDF159E` carries a RAM shadow `gp-0x4cae` (`0xFEDF35B2`, voter redundancy twin) — read either; they
  track.

### STEP 2 — Choose the new `0xC6312`
Threshold (in `gp-0x6a62` units) must sit **above the legitimate hard-turn peak + headroom**, while a genuine
driver grab still exceeds it (override must keep working). The live read converts the road events into
`gp-0x6a62` units and sets both the floor (legit peak) and the override margin (grab peak). The current 320 is far
too low (median normal driving already exceeds it on maneuvers). Name the safety trade plainly: raising it means
the driver must push harder to take authority from LKAS.

### STEP 3 — Build V32
`build_v32_tva.py` = copy `build_v31_tva.py` + **one new cal edit: `0xC6312` (2-byte LE) 320 → chosen value.**
Cal-only, **lockstep-clean** (3 readers, all in `FUN_00040d58`; no int/float twin; value appears once in the cal
block — see v32 handoff §3). Keep V31 rigor: 49/49 CRC, ECU-decode == patched, independent byte-diff (expect
V31's diff + 2 bytes at `0xC6312` + the recomputed block-`0xC6000` CRC). **UNFLASHED study artifact** until the
operator names file + bus.

---

## 6. KEY ADDRESSES / FILES

| thing | address / file |
|---|---|
| **THE edit** | cal `0xC6312` = 320 (`tp+0x7312`) — disengage when `gp-0x6a62 ≥` it |
| gate signal (live read) | `gp-0x6a62` = `0xFEDF159E` (shadow twin `gp-0x4cae` = `0xFEDF35B2`) |
| voter (produces gp-0x6a62) | `FUN_00041eec`; max-of-5, rising-unfiltered, decay 16/cyc cal `0xC64ED`; clamp 32000 |
| disengage decider | `FUN_00040d58` (reads **cal** 0xC6312 @ `0x40db8/0x40dd0/0x40df4`; the `gp-0x6a62` **value** @ `0x40dae/dc6/dea`); engaged handler `FUN_00041222` |
| 5 coil tracks | `gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38` (FUN_00053216←FUN_00021622/46/9e/72) + `gp-0x6a46` (FUN_000522fe←FUN_00021706); ×41/64 |
| sensor A raw frame | DMA → `gp-0x1450` (8 bytes) → `FUN_00021970` → `gp-0x13e0`; dispatch `FUN_000520d0` ch 0x10, TAUA0-paced |
| sensor B (CAN torque) | `gp-0x4f60` = `0xFEDF30A0`; `FUN_0007f3f8` ← raw `gp-0x505c` ← parser `FUN_000829e2` ← `gp-0x548`/`gp-0x544` ← `FUN_0007df80` |
| CAN 399 packer | `FUN_00055c42`: `STEER_TORQUE_SENSOR = -(gp-0x4f60 ×125/128)` |
| boost curve (sensor A) | `gp-0x6a5e` → table `0xce578` `[612..1238]`, ×'d in `FUN_00034a72` |
| LKAS setpoint cap (flat) | `g_pArbSetpointLimitCurves` `0xCB844` → `0xE4180…` = const 15360 (NOT torque-dependent) |
| motor command out | `gp-0x6b3c` → `m_steer_torque_limit_and_pack` → `m_motor_cmd_distribute_clamp` (per-phase `gp-0x62e0`) → `m_motor_cmd_mixer` → TAUJ0/1 PWM |
| rlogs + decoders | see `docs/HANDOFF-2026-06-29-gentle-eme-v32.md` §4 (`analysis-2020accord/rlogs/…`, `analyze_gentle_eme.py`) |
| V31 build script (copy) | `analysis-2020accord/build_v31_tva.py` |

---

## 7. IRON RULES (unchanged)
- No flash without the operator naming file + bus; repeat it back first. V32 is a STUDY ARTIFACT.
- V32 changes only calibration data — zero executable bytes (byte-verify, like V31).
- Before any flash on a comma device, openpilot/pandad must be killed (`tmux kill-server`).
- Analyze STOCK `code.bin` only — never `../accord-firmware/analysis-2020accord/_v27_plain_image.bin`.
- When a load-bearing claim conflicts with road data or prior work, walk the disasm yourself (this session
  corrected: the rate-limit-lag story, the "~1:1" scale, the `FUN_00040e74` role, and the "sensor A caps LKAS
  authority" claim).
