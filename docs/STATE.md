# STATE — living current state of the kit

**Last updated: 2026-07-27.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed and falsified — check it before
proposing any calibration edit) and the latest handoff.

---

## On the car right now

**FOURFRAME** = V38 calibration + a passive read-only CAN-telemetry cave. Fault-free, drives normally.

⚠ **FOURFRAME is built on V38 and does NOT carry the V42 ratchet fix** (`0x454FE` is stock `0x65BA`).
The state-4 governor substitution block is live on the car.

⚠ An rlog **cannot** identify which build is flashed — every modified build reports
`fw='39990-TVA,A160'`.

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| **FOURFRAME2** | FOURFRAME + the STRB fix + authority/reference-model telemetry | ready; 12 bytes off the on-car image |
| V49, V50, V51P, V52, VCANTX-TEST | superseded or blocked | see `docs/BUILD-LINEAGE.md` |

```
_vfourframe2_plain_image.bin  SHA 826809239588355ae3724565612083a8cd219fd456d4d0a548237b7933f2976c
```

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## The two open workstreams

### A. The 4×-gain vibration — ~21 Hz, unresolved

**What is established:**
- The mode is **~21.09 Hz, Q≈19**, present continuously from <1.5 m/s to ~15 m/s; above 15 m/s it becomes
  a broad low-Q 11–12.5 Hz shelf.
- **It requires the EPS to be ACTIVELY APPLYING LKAS torque.** Three-way split on route 13: openpilot off
  → nothing; openpilot commanding *harder* but the EPS in low-speed lockout → nothing (1.33× over
  baseline); openpilot commanding **and applying** → **14,750× more 21 Hz power**.
- The 21 Hz **is** present in the openpilot command, and command/sensor coherence at 21 Hz is **0.685**
  versus 0.171 at 1–3 Hz. There is **no openpilot-side low-pass at 21 Hz** (only −2.70 dB).
- The sensor carries far more *relative* 21 Hz than the command, so openpilot is responding, not
  originating — but coherence is symmetric and does not establish direction.

**Prime suspect:** the `FUN_0003a382` → `gp-0x6ad4` lane — an unfiltered, proportional-dominated feedback
of (sensor − reference model) straight into the actuator, with no band-limit at 21 Hz, whose output bound
is gated by authority `gp-0x6966` via the LERP at `0xC6AF0` (unity below 3277, **zero above 3604**).

🛑 **The edit direction is UNRESOLVED and must not be guessed.** Two analysis passes reached opposite
conclusions (mute vs keep-live) from the same data, one turn apart, because both hinged on authority's
runtime value — which is not statically determinable. **Measure `gp-0x6966` on-car first.** That is why
FOURFRAME2 carries it.

**Unresolved and it matters:** 21.09 and 78.91 Hz sum to exactly 100.00, and CAN 399 samples
instantaneously at exactly 100.000 Hz. Indirect evidence leans 21.09 (implied Q would be 71.8 at 78.91 Hz,
not credible) but **the rlog cannot close it, and neither can FOURFRAME2** — it also transmits at 100 Hz.

### B. Low-speed steer lockout — located, cal-only, unbuilt

`0xC62EA` = 320 ≈ 5 km/h is the LO half of a two-sided window against voted speed. Failing it sets
`STEER_STATUS=3`, which zeroes `STEER_CONTROL_ACTIVE` and kills the authority ramp. Suggested value **64**
(1 km/h), not 0. One reader, no float mirror, in the cal block every build already touches.

**This is also the discriminating experiment for workstream A** — it populates the empty "engaged at low
speed" cell that route 13 structurally could not produce, breaking the speed/applied-torque collinearity.

openpilot is not the obstacle (`CP.minSteerSpeed = 0.0`).

---

## Recommended next steps, in order

1. **openpilot-side 21 Hz notch.** Zero brick risk, now known untested rather than null. Keep the ±4096
   rail fraction matched between runs — 14% of frames are railed and railed windows show no 21 Hz.
2. **Flash FOURFRAME2** for the firmware answer. One parking-lot drive measures authority and captures all
   three terms of the suspect loop.
3. **The `0xC62EA` lockout edit.**
4. **The `0xC646C` decoupling** — a correctness fix, not the vibration fix.
5. Only then a `0xC6AF0` edit, in whichever direction the telemetry indicates.

---

## Corrections of record still worth knowing

- **`0xC646C` is NOT "the LKAS authority gain."** It is the firmware's single shared Q15
  sensor-to-command-domain scale, with **6 readers across three subsystems**; two (`0x36686`, `0x3684a`)
  apply it to the **raw torsion-bar sensor** on a feedback path reaching the motor. Raising it for 4× LKAS
  authority silently raised those too. (Probably not the 21 Hz driver — that lane is low-passed at
  fc ≈ 2.2 Hz and clamped to 5% of aggregator range.)
- **The CAN-TX base tick is 100 Hz, not 62.5 Hz.**
- **The gateway per-ID whitelist is WEAKENED as an explanation.** `0x19F` is gated at its own request site
  (`0x5559E`), so it is not a clean control for "the gateway drops unknown IDs".
- **`gp-0x4f60` is Sensor-B (TAS) driver column torque** — not angular velocity, not vehicle speed.
- **The control task is ~1000 Hz** (confirmed two ways).
- **`FUN_00045608` is an authority-slot setter, not "motor off".** The governor **does** read vehicle
  speed (`0xC6316` = 640 ≈ 10 km/h, below which the slew limiter is bypassed).
- ⚠ **Flagged but NOT adopted:** two traces conclude `gp-0x6a5e`/`0x6a62`/`0x6a64` are voted **vehicle
  speed**, not voted torque. If true it reclassifies the V44/V47 damper result. Needs its own pass.
