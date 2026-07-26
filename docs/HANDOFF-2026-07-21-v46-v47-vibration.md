# HANDOFF — 2026-07-21 — V46 (lever A, falsified) + V47 (dampers-only, unflashed)

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** V38 on-car image.
**Status:** **V46 FLASHED → did NOT move the vibration → lever A falsified. V47 BUILT + verified, UNFLASHED.**
No CAN/UDS/flash operation occurred this session beyond the operator's own V46 drive.

---

## Result in one paragraph

The ~21 Hz steering vibration is a **self-excited limit cycle** in the base-assist torque-sensor
feedback loop, not a command-path artifact. Two firmware facts define it: (1) the base-assist **viscous
damper** is gated to ≈zero hands-off by **two** independent deadzones — Factor C (driver torque) *and*
Factor E (motor rate) — and (2) an unfiltered feed-forward carrier supplies loop gain at 21 Hz. This
session ran a full multi-agent audit (six traces), which **retired the "5 mph = firmware speed gate"
theory entirely** (there is no vehicle-speed input anywhere in the command or base-assist path), pinned
the **plant** (dual-pinion EPS, one torsion-bar sensor, rack-coupled mode), and tested **lever A** (a
low-pass on the unfiltered carrier). V46 shipped lever A and **it did nothing on-car → falsified.** V47
is the other lever: **restore the hands-off damper** by opening *both* deadzones (the operator's
manual-rotation cure, turned into firmware) — built, verified, awaiting a drive.

---

## What the V46 drive established

**Lever A is falsified.** `FUN_0003a382` Stage A is an exact unity-gain, zero-lag passthrough of the
Sensor-B residual (`errorterm = gp-0x4f60 − model gp-0x6ad6`), summed into the aggregator with assist
(positive-feedback) polarity — confirmed reinforcing, not opposing, by contrast against friction's
all-negative table and damping's velocity-keyed negation (RoadFeel, disasm-verified). The structural
case that filtering it (`0xC6450` 1024→32, corner ~4.8 Hz, −12 dB at 21 Hz) would cut the loop gain was
clean — but **flashing it as V46 produced no noticeable change.** So either Stage A does not carry
significant 21 Hz content, or Stage B (the unruled-out accumulator wildcard) dominates, or the loop gain
is not the binding constraint. This joins r24 (V39), r26 (V42), Stage-C pole (V43), hands-off damping
floor (V44), and hands-off slew (V45) as **falsified vibration levers.** Six of the seven prior levers
lived on the command/reference path or were too weak; V46 was the first excitation-side lever and it
still missed.

---

## The converged diagnosis (multi-agent audit, this session)

### Plant — dual-pinion EPS, one torsion-bar sensor, rack-coupled mode (EPSArch, web research)
- **Dual-pinion variable-ratio EPS.** The assist motor drives a **second pinion** on the rack, mounted
  **off the steering axis** for vibration isolation (Showa/Hitachi-Astemo design). The torque sensor
  sits on the steering-input pinion / torsion bar.
- **Sensor A and Sensor B are the MAIN and SUB Hall channels of ONE torsion-bar sensor** at the column
  input — not two separate physical sensors. Confirmed by Honda DTC **C1420 "Main/Sub Torque Sensor
  Incorrect Correlation."** This matches the firmware (`gp-0x4f60`=Sensor-B=driver column torque).
- Motor position is a **resolver** (consistent with the firmware's sin/cos + atan2 decode of `gp-0x6ac0`).
- The 21.4 Hz, Q≈13.6 mode is therefore a **rack-coupled driveline resonance** (motor inertia +
  assist-pinion + rack + steering-pinion + torsion bar + column), sensed at the torsion bar and felt at
  the wheel. The driver's grip damps the column end — but only **rotation** (which spins up motor rate)
  cures it, not a static hold.
- **openpilot:** "Honda Bosch A connector", `minSteerSpeed=0`, `minEnableSpeed=3 mph`.

### Why exactly ~5 mph — NOT a firmware speed gate (SpeedPath + RlogMiner)
- **There is no vehicle-speed input anywhere** in the LKAS command path or the base-assist feedback loop
  (all 9 aggregator lanes decompiled and checked; the boost curve's 4 previously-undumped tables
  resolved). The only rate-adaptive tables are keyed on **motor/resolver electrical-angle rate**
  (`gp-0x6ac0`), not road speed. The firmware ingests wheel speed (CAN 0x1D0 from VSA) only for a
  DTC plausibility check, structurally separate from torque arbitration.
- The vibration turns on at **3–4 mph** = openpilot's `minEnableSpeed=3` (below it, OP can't engage → no
  LKAS → no excitation). RlogMiner (route b9, the only post-V38 route): band power near the noise floor
  <2 mph, **10–25× elevated across 3–10 mph** (peak 19–22 Hz, matching the mode), a real **dip at
  10–12 mph**, moderate at highway. So 5 mph is where excitation (assist demand highest, road noise
  lowest) peaks — **plant physics, not a cal.** `STEER_STATUS=3` ("LOW_SPEED_LOCKOUT" in the DBC) is a
  fallback for "OP not engaged-steering," not a speed comparison.

### The limit-cycle mechanism (DampFactors)
- The damper `FUN_00034350 → gp-0x6bd0` is a **product of FIVE Q10 factors** (not four): A=seed
  `gp-0x698a` (≈1024), B=`gp-0x6bcc` (flat 1024, inert), C=voted driver torque `gp-0x6a5e`
  (`0xD27BC`/`0xD27D0`, Y=[0,235,430,877]), D=`gp-0x6a10` angle-deviation (flat 1024, inert), E=|motor
  rate| `gp-0x6ac0` (`0xD27F8`/`0xD280C`, Y=[0,140,539,927] over X=[60,400,2500,4000]).
- **Both C and E have Y0=0** → two independent hands-off deadzones. **V44 opened only C**, so E still
  zeroed the product → V44 failed. Below ~60 counts of motor rate the whole damper is zero; even at 400
  it is only 14% of table max. That deadzone is where the limit cycle hides.
- The damper's realistic hands-off magnitude with only V44 applied is **7–32 counts** — negligible vs
  the ring. The output clamp is dynamic **±512..±1024** on `gp-0x6ac2` (not flat ±2048), also small at
  low rate.
- **Manual rotation cures it** because rotation drives `gp-0x6ac0` toward its high-rate region (~900),
  engaging the damper at ~160–213 counts. That is the authority target for a real fix.

### Governor scope — corrected (Governor)
- **G1 (`FUN_0004503c`) clamps the TOTAL aggregated command `gp-0x6b94`** (LKAS + all base-assist lanes,
  driver-sourced included), verified at instruction level — not LKAS-only. Every lane funnels through
  it; no bypass.
- **The "thermal protection" label is FALSIFIED.** The "energy budget" accumulator is structurally
  unreachable: its charge threshold (`0xC509E`=5325) exceeds the ceiling (`0xC6202`=4762) that G1 caps
  the watched quantity below, and `0xC5164`=0 collapses the hysteresis. Correct label: a
  **motor-rate-adaptive total-command ceiling.** It does not bind at the ~139-count resonance amplitude,
  so it is neither the cause nor a useful lever. (Operator's falsification test — "if it only limits
  LKAS it can't be thermal" — was right to force this; the scope half was true, the thermal half false.)

### The DTC-0x1d clamp trap (safety, DampFactors)
`FUN_000347b8` re-derives the damping clamp bound in **float** from a mirror at
`0xC6554/58/5C/60` (=300.0/800.0/0.5/1.0) and diffs it against the int table `0xD209C/0xD20A8`; a
mismatch > 5/1024 calls `FUN_000462e6 → FUN_00016de6(0x1d)` — a **no-debounce hard shutdown**.
**Rule of record:** never edit the int clamp bound without a bit-exact matching edit to the float
mirror. V47 does not touch the clamp (and doesn't need to — see below).

---

## V47 — the build (dampers-only)

**V47 = V38 + ratchet fix + damping restore (both deadzones). Lever A dropped after V46 falsified it.**

| Change | Address | Stock → New | Note |
|---|---|---|---|
| Ratchet (code) | `0x454FE` | `bne 0x455C4 → br 0x455C4` | V42's confirmed fix, carried |
| Factor C m10 Y0 | `0xD27C6` | 0 → 235 | V44's proven cell |
| Factor C m11 Y0 | `0xD27DA` | 0 → 234 | V44's proven cell |
| Factor E m10 Y0/Y1/Y2 | `0xD2802/04/06` | 0/140/539 → 700/750/800 | aggressive reshape |
| Factor E m11 Y0/Y1/Y2 | `0xD2816/18/1A` | 0/140/539 → 700/750/800 | (both modes; failover) |

- **Sizing = AGGRESSIVE deliberately.** Opening Factor E to Y1 only (conservative, ~32 counts) repeats
  V44's already-failed magnitude. The reshape delivers ~160–213 counts across the low/mid-rate domain —
  matched to the authority the manual-rotation cure demonstrably applies. **Trade-off:** removes the
  low-rate damping deadzone across the board → expect **some low-speed steering heaviness** (parking,
  slow maneuvers). Fully reversible; a middle-ground Y0≈350 is on standby.
- **Safety, byte-verified:** Factor E tables read only by `FUN_00034350`'s own LERP — no float mirror,
  no monitor, no interlock; `FUN_00034350` is int-only; the output shadow (`gp-0x4cf2`) is report-only.
  Even aggressive damping stays under the clamp's 512 floor, so the clamp never binds and the DTC-0x1d
  float watchdog never trips. The builder **asserts** the int clamp tables and the float mirror stay
  byte-stock on baseline, built image, and RWD readback.
- **CRC:** 2 blocks touched — MAIN `0xC4FFC` (ratchet) + DAMP `0xD2FFC` (dampers). The `0xC6000` CAL
  block is byte-stock (lever A reverted). 23 changed bytes vs V38, all accounted for. 50/50 full chain +
  49/49 bootloader walk on image and decoded-RWD readback.

| Artifact | SHA-256 |
|---|---|
| V47 RWD | `1421ca1bb0af89496c5fa91e1557e981bd7578ffa315625e6b8443dcafb7bc34` |
| `_v47_plain_image.bin` | `c7fb529011230a54d3d7bb21ab5daae1a02f1f3caa6df141277135938a3222b8` |

Builder: `analysis-2020accord/build_v47_tva.py`. Filename:
`39990-TVA,A160-V47-LKAS-4x-V38base-ratchet-dampers-C235-Eaggr-0x13000-0x100000.rwd`. **UNFLASHED.**

(V46 builder — `analysis-2020accord/build_v46_tva.py`, the falsified lever-A build — is retained as the
record. Its RWD stays in `rwd/`.)

---

## Current builds (2026-07-21)

- **V38** — FLASHED, fault-free. On-car baseline.
- **V42** — state-4 ratchet fix (`0x454FE`) CONFIRMED on-car; carried into every later build.
- **V43/V44/V45** — falsified (Stage-C pole / hands-off damping floor / hands-off slew).
- **V46** — FLASHED. Lever A (Stage A carrier low-pass `0xC6450` 1024→32). **No effect → falsified.**
- **V47** — BUILT + verified, **UNFLASHED.** Ratchet + damping restore (Factor C + Factor E aggressive).
  The current candidate; tests whether real hands-off damping kills the ring.

---

## Open / next steps

- **Flash V47** and evaluate: (a) does the ring go away hands-off? (b) is low-speed steering acceptably
  heavy? If it works but feels too heavy, rebuild with Factor E middle-ground (Y0≈350). If it does
  nothing, the damping hypothesis is falsified and the limit cycle's loop gain is the remaining target —
  but note lever A already missed the most obvious carrier.
- **The highest-value missing data is still 2–10 mph hands-off telemetry** on `gp-0x6ac0` (motor rate
  during the resonance) — it would resolve whether the damper is deadzoned-off or engaged-but-weak, and
  thereby whether V47's sizing is right. Not on CAN; blocked on the comma-4 OBD-mux contention.
- If both damping and the obvious carrier miss, the resonance may be primarily **mechanical** (the
  dual-pinion rack mode) with the firmware only an enabling condition — in which case the practical
  lever is reducing overall low-speed assist authority (loop gain), accepting a feel change, rather than
  chasing a single clean cal.

---

## Corrections of record made this session (propagate; trust these)

1. Lever A (Stage A carrier filter) is **falsified on-car** (V46).
2. The damper is a **5-factor product** with **two** hands-off deadzones (Factor C driver-torque **and**
   Factor E motor-rate); V44 failed because it opened only C. Output clamp is dynamic ±512..1024, not ±2048.
3. **No vehicle-speed input exists** anywhere in the command/base-assist path; "5 mph" = `minEnableSpeed`
   + plant physics, not a firmware gate. The only rate adaptation is on **motor rate**, not road speed.
4. Governor G1 clamps the **TOTAL** command (not LKAS-only); its "energy budget" is **not** a thermal
   integrator (structurally unreachable) — relabel "motor-rate-adaptive total-command ceiling."
5. Plant is a **dual-pinion EPS**; **Sensor A/B are two channels of ONE torsion-bar sensor**; the mode
   is a rack-coupled driveline resonance.
6. The damping clamp bound has a **DTC-0x1d no-debounce float-mirror interlock** (`0xC6554`↔`0xD209C`).
