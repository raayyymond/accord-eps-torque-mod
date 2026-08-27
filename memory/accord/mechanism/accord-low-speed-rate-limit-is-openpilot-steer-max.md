---
name: accord-low-speed-rate-limit-is-openpilot-steer-max
description: The "max steering angular velocity is limited at low speed" symptom is COMMAND SATURATION at openpilot's STEER_MAX = 4096, not a firmware ceiling - railed 20-42 percent of hard low-speed engaged time, with the response still climbing at the rail and the rack proven able to slew 3-4x faster. No firmware calibration can raise it.
metadata:
  node_type: memory
  type: reference
---

# THE LOW-SPEED STEERING-RATE LIMIT IS **openpilot's `STEER_MAX` = 4096**, NOT THE FIRMWARE

★★★★★ **EVIDENCE**, 2026-08-27. Answers the operator's goal #5, which he has now re-reported on
**V107 and V108** and which **no build in this kit could ever have fixed.**

## 1. THE RAIL IS REAL, AND IT IS A HARD CLAMP
`e4tq` (openpilot's own transmitted torque request, CAN `0xE4`, `sendcan` src1) approaching its edge,
r77 engaged:
```
   [3500,3700)  832     [4050,4080)  112
   [3700,3900)  903     [4080,4090)   34
   [3900,4000)  394     [4090,4095)   25
   [4000,4050)  183     [4095,4095.5)  3
                        [4095.5,4096.5) 13,783   <-- a DELTA on a decaying tail
```
⭐ **Zero frames above 4096 in ~200 cache files across the entire corpus.** A smooth decay into a
spike at the boundary is a clamp, not a coincidence.

## 2. IT BINDS EXACTLY WHERE THE OPERATOR FEELS IT
Duty of `|e4tq| >= 4096` while engaged, by speed:
```
   band      r77      ra6      r1e        (exposure, s: r77 / ra6 / r1e)
   <6 mph  0.4036   0.3099   0.0745        134.3 /  45.8 /  59.9
   6-10    0.3697   0.2100   0.0684         85.1 /  58.3 /  37.5
   10-15   0.2146   0.0889   0.0615        132.9 /  50.3 / 104.5
   15-20   0.0965   0.1458   0.0521        141.0 /  30.5 /  87.6
   20-30   0.0323   0.0274   0.0503        246.7 /  71.6 / 131.6
   30-45   0.0028   0.0000   0.0087        187.7 / 166.2 / 297.8
   45+     0.0000   0.0000   0.0021        134.8 / 802.2 / 269.7
```
⭐ **Reproducible**: `rlog-tools/studies/authority/steer_max_saturation.py` (T1/T2/T3 with all three
controls). Every number in this note is that script's output, not an ad-hoc run.
⭐ **20-42 % of hard low-speed engaged time is spent pinned at the rail, falling monotonically to ~0 %
above 30 mph** — the same shape as *"below ten miles an hour the maximum steering angular velocity is
still limited"* and *"above twenty this is the best it has ever been"*.
⚠ r1e is much flatter (5-8 %) because that drive simply had gentle low-speed steering — its p99 rates
are ~4x lower than r77/ra6 throughout. **Rail duty tracks how hard you steer, not just how slow you go.**

## 3. 🛑 THE RESPONSE IS STILL CLIMBING AT THE RAIL — THE CAR IS NOT THE LIMIT
Rate in the commanded direction (sign per [[accord-steering-sign-convention-confirmed]]: `+LKAS` ⇒
negative angle, so negated), <15 mph engaged, deg/s:
```
   |cmd|        r77 p50 / p90        ra6 p50 / p90     (sec at that bin, r77 / ra6)
   0-256          0.0 /   8.1          0.0 /   6.1        50.7 / 33.4
   1k-2k         12.1 /  52.6         14.1 /  40.4        45.0 / 26.0
   2k-3k         18.2 /  66.8         20.2 /  64.7        27.4 / 11.6
   3686-4095     18.2 /  93.9         30.3 / 135.4        11.1 /  2.9
   == 4096       28.3 / 143.6         26.3 / 125.3       114.2 / 30.9   <-- still rising
```
⊕ **CONTROL — what the DRIVER achieves at the same speed:** p90 `103.2` (r77, 163.0 s) /
`161.7` (ra6, 288.6 s) / `62.7` (r1e, 284.0 s); max `459.2` / `446.7` / `402.2` deg/s. **The rack can be slewed 3-4x faster than openpilot
achieves at its rail.** ⇒ **There is plant headroom. openpilot has simply run out of command.**

## 4. 🛑🛑 THE CONSEQUENCE — AND IT IS THE UNCOMFORTABLE ONE
**No firmware calibration can raise a ceiling that lives in openpilot's message.** The 6x gain
(`0xC6CD0`) multiplies whatever arrives; when what arrives is pinned at 4096, the firmware is already
delivering 6x of the most openpilot can ask. The only two ways to more low-speed rate are:
1. **Raise `STEER_MAX` on the openpilot side** — **the operator's call.**
   🛑 [[feedback-no-openpilot-side-modifications]] is standing: openpilot is the measurement
   instrument, and changing it breaks comparability with every prior drive. **Tell him; do not do it.**
2. **Raise the firmware gain above 6x** — which is precisely the carrier of the grinding
   ([[accord-the-8x-gain-is-the-carrier]]: `0xC6CD0` causes the ~23 Hz vibration).

⇒ **GOAL #5 AND GOALS #1-3 ARE IN DIRECT TENSION, AND THE BINDING CONSTRAINT SITS OUTSIDE THE
FIRMWARE.** This is why the symptom survived every build: **none of them could have moved it.**

## 5. ✅ RETIRED IN THE SAME PASS — THE AUTHORITY RAMP IS **NOT** THE LIMIT
Pre-registered before looking, and it returned the null. `gp-0x69b0`'s climb requires
`gp-0x6807` (STEER_STATUS) `<= 2`; 3/4/7 force the down-ramp. Measured:
**STEER_STATUS is identically 0 across 3,312 s of engaged driving on r1e/r1b/r77/ra6, every speed band,
ZERO transitions.**
⊕ **The control PASSES** — `sstat` does move: status **3** appears on 4 of 6 routes, **exclusively at
0.0 mph and exclusively disengaged** (107 / 2 / 8 / 9 frames). The decode is live; the null is real.
⇒ **The ramp reaches `0x8000` ~1 s after engagement and holds. The five rate cals are RETIRED as a
low-speed-rate candidate.** See [[accord-the-authority-ramp-five-rates]].

## ⚠ WHAT THIS RESULT DOES **NOT** ESTABLISH
- Rate is quantised at **~2.02 deg/s** (angle LSB / 9.9 ms). Single-step p50 differences are noise; the
  trend across a decade of command is the robust part.
- **Command magnitude is confounded with turn intent** — you command more where you mean to turn more.
  The **non-flattening** survives that; the absolute slope does not.
- The driver control is an **upper envelope**, not a matched comparison. It is exactly what is needed to
  exclude a plant limit, and nothing more.
- ⚠ r1e's p90 *falls* at the rail (34.4 vs 61.4 one bin below) against r77/ra6 rising — but r1e has only **13.5 s** of rail
  exposure below 15 mph. **Do not read r1e as a contradiction; read it as thin.**

Related: [[accord-4x-lkas-gain-is-the-frozen-variable]] · [[accord-vibration-needs-applied-torque]] ·
[[accord-low-speed-lockout-window-c62ea]]
