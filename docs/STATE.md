# STATE — living current state of the kit

**Last updated: 2026-07-28.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed and falsified — check it before
proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-28-v54-drive-authority-resolved-and-v55-partition-probe.md`.

---

## On the car right now

**V54** = V38 calibration + `0xC62EA` 320→0 + the 5-bit `gp-0x6966` authority probe on `0x14A` byte4
bits 7:3. Flashed 2026-07-27, driven (route `1b`, 61.5 s parking lot), **fault-free**
(`steerFaultTemporary`/`Permanent` both 0; `canValid` true in 5,711/5,713 — the piggyback did not break
the Honda checksum).

✅ **THE PROBE FIRED. This is the kit's first working firmware telemetry channel.** The A/B against the
V53 drive is a single bit, and it is exactly the bit the cave writes:

| route | build | `0x14A` byte4 | bits 7:3 (`wire`) | bits 2:0 (stock status) |
|---|---|---|---|---|
| `1a` | V53 (no probe) | `0x07` × 5,994 (100%) | 0 | 7 |
| `1b` | **V54** | `0x0F` × 5,989 (100%) | **1** | 7 |

Stock's `STEER_SENSOR_STATUS` bits are preserved. **Retire the "new-mailbox is unobservable" workaround
anxiety: the `0x14A` byte4 piggyback is proven end to end, wire to decoder.**

**V53** (previous) = V38 cal + FOURFRAME2 cave + `0xC62EA` 320→0. Superseded.

✅ **Steer-to-zero WORKS — confirmed from the rlog, not just by report.** Route `1a` segment 0:
`STEER_STATUS = 0` in **5,995/5,995** frames (ST=3 never fires anywhere) and **226 frames of
`STEER_CONTROL_ACTIVE = 1` below 5 km/h**, a cell that is structurally empty on V38. The §7 prediction
from the previous handoff held exactly.

🛑 **The four-frame telemetry (V53/FOURFRAME2) never arrived** — zero frames of `0x6A0`-`0x6A3` across
301,824 CAN frames. That null remains uninterpretable and the boxed rule in `BUILD-LINEAGE.md` Part 1
stands: **do not build another new-mailbox channel.** Use the `0x14A` piggyback, which now has an on-car
proof rather than an argument.

⚠ **V54 does NOT carry the V42 ratchet fix** (`0x454FE` is stock `0x65BA`). The state-4 governor
substitution block is live on the car.

⚠ An rlog **cannot** identify which build is flashed from the version string — every modified build
reports `fw='39990-TVA,A160'`. (It *can* now be identified behaviourally: ST=3 never firing ⇒ V53+.)

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| **V55** | V38 + `0xC62EA`→0 + a **dual probe**: bit7 = damper variant index ≥ 10, bits 6:3 = 4-bit `gp-0x6b98` motor command @100 Hz | ✅ **BUILT, gated, ready — the one to flash.** It PARTITIONS the hypothesis space rather than testing another lever |
| FOURFRAME2 | FOURFRAME + STRB fix + telemetry on IDs `0x6A0`-`0x6A3` | **retired** — the channel is unobservable |
| V49, V50, V51P, V52, VCANTX-TEST | superseded or blocked | see `docs/BUILD-LINEAGE.md` |

```
_v55_plain_image.bin  SHA 9ed79e68e1d02362efff5262a9f142e6e1a6596104d800d5fd6a95cef86e576c
V55 .rwd              SHA 2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf
_v54_plain_image.bin  SHA 233188ffa21d8ae685685a48410e0c15b49ffca8af2fa8d3684f987cf1a4710b  (ON THE CAR)
V54 .rwd              SHA 97ea51d2fa6b21d4584247be5571c34a5d3d15df742c2033324aae456c1c7517
_v53_plain_image.bin  SHA 6be6055357506b87afe21ea622d46bda35ececfe5bb9038834e643d0f0292e1f
```

**V55 is 82 bytes off V38** in 5 runs: a 68-byte cave at `0xC4B34`, the 4-byte `0x55C0E` hook, `0xC62EA`,
two CRC trailers. 50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run on the
readback. **Every instruction in the cave is either byte-identical to V54's flashed cave or differs by a
single register/condition field from a byte-confirmed real instruction** — no novel opcode value.
Decoder: `rlog-tools/decode_v55_motorcmd.py`.

✅ **Pre-flash Ghidra gate CLOSED (2026-07-28).** The cave and hook were re-disassembled from the
*written* image via GhidraMCP — SHA-verified copy imported under a distinct filename
(`v55_cavecheck.bin`, `auto_analyze=false`, `dry_run=true`, never saved), defeating both the
stale-import and modal-save traps. All 22 cave instructions decode as intended, and **Ghidra resolved
all three branch targets independently onto their labels** (`bge`→`0xC4B4A`, `bnh`→`0xC4B56`,
`bc`→`0xC4B64`). The hook re-confirms its four load-bearing facts: `jarl 0xC4B34,lp`; `mov 0x8,r7` at
`0x55C12` (r7 provably dead); `movea 0x14a,r0,r8` (this IS the 330 builder); `jarl 0x57b24,lp` (the
checksum runs after us and clobbers `lp` itself).

🛑 **The V55 decoder REFUSES to interpret a V54 rlog**, and this was a real catch: V54 packs its 5-bit
wire into bits 7:3 of the same byte, so a V54 drive (`byte4` constant `0x0F`) decodes as a perfectly
plausible V55 "field == 1, bit7 == 0" — confident, actionable, fabricated. The guard is that a live V55
field samples the *motor command* and therefore **cannot be constant** on a driving car.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## ★★ RESOLVED 2026-07-28 — authority `gp-0x6966` is ≡ 0 by design on V31+

**`gp-0x6966` is not a speed-scheduled "steering authority" gain.** It is the **soft-EME wind-up
integrator's magnitude**:

```
gp-0x3570 += (command − bound), clamped ±(cal 0xC61DC = 30720)   [anti-windup integrator]
gp-0x6966  = |gp-0x3570 >> 15| × (cal 0xC61DA = 1092) >> 10      [max (1092×30720)>>10 = 32760 ≈ Q15 1.0]
```

The bound is a 3-way gated MAX/MIN of corridor (driver-override), boost (angular rate) and an IIR on
column velocity. **No arm is vehicle road speed** — confirmed by a hit-count sweep of `FUN_00042af8` for
`gp-0x6a5e`/`0x6a62`/`0x6a64` and cal `0xC6316` (0 relevant hits).

**Why it reads zero on the flashed build — verified in `_v54_plain_image.bin`, not argued:**

```
boost LERP Y   stock: 0 / 1536 / 2048      V38 & V54: 5120 / 5120 / 5120
float twin     stock: 0.0 / 1.5 / 2.0      V54:       5.0 / 5.0 / 5.0
```

On **stock**, `Y[0] = 0`: at low angular rate the boost arm vanishes, the bound collapses, the integrator
winds — that is exactly the V30 hard-hands-off-turn EME event. On **V31+ (incl. V38/V54)** the boost arm
is floored and is ungated by driver input, so the bound cannot collapse, `(command − bound)` stays
negative, and the integrator sits pinned. **The V31 fixpoint is self-stable and attracting.**

⇒ **On-car measurement, route `1b`: `wire = 1` in 5,989/5,989 frames ⇒ `gp-0x6966` ∈ [0,127]**, zero
variation, i.e. **0.39% of saturation** — including 17% of requesting frames at openpilot's ±4096 rail.
Reaching the first LERP knee needs `|gp-0x3570>>15| ≥ 3073` against an observed **≤ 119**.

**This converts V31 from "argued, with a residual margin caveat" into on-car evidence under railed
command.** That is the real contribution of the V54 drive.

⚠ **One record clarification, and one genuine open item.**

*Clarification (NOT a correction to the V31 memory):* that memory's boost floor of **4096 is correct for
V31**. **V38 raised it to 5120**, and the golden model already carries both
(`Calibration.for_build("V31").boost_floor == 4096`, `("V38") == 5120`). The car runs V38+, so 5120 is
the live value. Do not "fix" the V31 memory.

*Genuine open item:* that memory's residual-margin arithmetic (*"COMP ceiling 2560 `0xC67D8` + governed
clamp 1024 `0xC61B4` = 3584 vs 4096"*) **does not reconcile with the image** — `0xC67D8` reads 512 and
`0xC61B4` reads 2048 in V54. Those may be LERP tables where a prose address names one element; the margin
must be **re-derived** before anyone quotes it again. It no longer blocks anything, because V54 measured
the margin directly on-car.

### Verified chain (Python byte reads, independent of Ghidra and of any subagent)

```
0x3a632  0x5fe4 0x969b   ld.hu -0x6966[gp], r11    <- the ONE command-path reader
0x3a636  0x7e25 0x7af0   movea 0x7af0, tp, r15     <- tp=0xBF000 -> 0xC6AF0, 4 bytes later
0x432c8  0x6f64 0x969a   st.h  r13, -0x6966[gp]    <- st.h => 16-bit; the probe's ld.hu width is correct
0xC6AF0  X = 0 / 3277 / 3604 / 19661 / 32768   Y = 32768 / 32768 / 0 / 0 / 0
```

**Channel audit (this session, against the fork on disk):**

| byte | DBC content | openpilot reads it? | free bits |
|---|---|---|---|
| `0x14A` byte4 | bits 2:0 = `STEER_SENSOR_STATUS_1/2/3` (live in firmware) | **no** (only bytes 0-3) | **5** @100 Hz |
| `0x18F` byte5 | bits 3:0 = `STEER_CONFIG_INDEX`; **bits 5:4 LIVE** (`gp-0x6880 & 3`, packer `0x55CAE`) | no | 2 safe; no hook located |
| `0x1AB` byte0 | bit7 `CONFIG_VALID`, bit3, bits 1:0 = `MOTOR_TORQUE[9:8]` | no (427 never parsed) | 4, non-contiguous, 48.7 Hz |

Panda Honda RX checks are `0x1A6`, `0x296`, `0x158`, `0x17C`, `0x326`, `0x1BE` — **none of the three**.
⚠ opendbc *does* verify Honda checksums (`opendbc/can/dbc.py`); a bad one drops `can_valid`, which is a
**disengage**. Any piggyback must be written before the checksum call.

---

## The two open workstreams

### A. The 4×-gain vibration — ~20-22 Hz, still unresolved (but the `0xC6AF0` block is lifted)

**What is established:**
- **The mode MOVES with speed** (route `1b` vs `1a`, Welch, 0.195 Hz resolution — 8 bins apart, resolved,
  not noise): **20.12 Hz at 1.0 m/s mean → 21.68 Hz at 4.0 m/s mean.** Q ≈ 34 and ≈ 22 respectively.
  ⇒ **Any openpilot notch must be wide or speed-scheduled; a fixed 21 Hz notch misses at creep.**
  ⇒ It also argues against a fixed digital artifact pinned at 21.09 Hz. It does **not** resolve the
  21.09-vs-78.91 aliasing question — both aliases shift together.
- **It requires the EPS to be ACTIVELY APPLYING LKAS torque.** Route 13 three-way split: openpilot off →
  nothing; commanding *harder* into low-speed lockout → nothing (1.33×); commanding **and applying** →
  **14,750×**. Reconfirmed on route `1b`: **771×** engaged/disengaged in the 15-26 Hz band.
- ★ **It reproduces at parking-lot creep** — route `1b` never exceeded **1.50 m/s (3.4 mph)**. This is the
  cell V53's `0xC62EA` unlock made reachable, previously structurally empty. Onset is sharp at engagement
  and collapses at disengagement.
- ★ **Saturating the command SUPPRESSES it, controlling for speed.** At 1.2-1.6 m/s: unsaturated
  `1.22e9` → railed(>50%) `8.6e6`, a **141× collapse**. At 0.8-1.2 m/s, 8.8×. Consistent with a loop that
  opens at the rail — **but a mechanical operating-point shift (backlash/stiction take-up under high
  torque) predicts the same observation, and this data cannot separate the two.**
- The mode **is** present in the openpilot command at the same peak bin, but at only **0.091%** of command
  power. Coherence is symmetric and still does not establish direction.

**Prime suspect:** the `FUN_0003a382` → `gp-0x6ad4` lane — an unfiltered, proportional-dominated feedback
of (sensor − reference model) straight into the actuator, with no band-limit at 20 Hz, whose output bound
is gated by authority `gp-0x6966` via the LERP at `0xC6AF0`.

#### ✅ The `0xC6AF0` direction is now MEASURED, not argued

Authority is ≡ 0 on this build (section above), and 0 sits inside the table's **first flat segment**:

- **`Y = 32768` (unity) is selected in 100% of normal operation.** The residual lane runs at its **full
  output bound** always — including throughout the vibration.
- The derate never engages, because engaging it needs an EME wind-up that V31's boost floor made
  unreachable.
- ⇒ **"keep-live" is a no-op** — the lane is already live. **Mute (`Y[0]`, `Y[1]` → 0) is the only
  meaningful edit**, and the measurement licenses it.
- A genuine safety point in the mute's favour: zeroing `Y[0]/Y[1]` **does not disable a live protection**,
  because the derate is currently never invoked — and in a hypothetical wind-up it would be *more*
  conservative, not less.

🛑 **STILL OPEN — GATE 2.** The measurement proves the lane is **live**; it does **not** prove it is the
**culprit**. The lane's damping-vs-anti-damping sign at 20 Hz remains undetermined ("proportional-dominated
8-10:1, net phase −3.3° to −5.4°… a plant-transfer-function question"). Muting a possibly-*damping* term
on the 1 kHz path is a real closed-loop risk. **Do not treat "unblocked" as "cleared to flash."**

### B. Low-speed steer lockout — ✅ CLOSED, flashed and confirmed 2026-07-27

`0xC62EA` = 320 ≈ 5 km/h is the LO half of a two-sided window against voted speed. Failing it sets
`STEER_STATUS=3`, which zeroes `STEER_CONTROL_ACTIVE` and kills the authority ramp. **V53 sets it to 0**
(operator instruction). One reader, no float mirror, in the cal block every build already touches.

**Why 0 rather than the previously-suggested 64:** stock *already* unlocks true standstill — `gp-0x68b3`
(the window bypass) is written only when `gp-0x6a62 == 0`, i.e. exactly 0. Stock therefore permits 0 km/h
and forbids 1–319 counts. Choosing 0 removes that discontinuity instead of moving it.

**Safety re-verified at build time**, in Python, independently of Ghidra:
- **Exactly one reader image-wide**, both V850E2 encodings swept over `[0x13000,0xC4FFC)`: the `disp|1`
  halfword `0x72EB` occurs once, at `0x28EBE` — the displacement of `ld.hu 0x72ea[tp],lp` @`0x28EBC`. The
  single bare-`0x72EA` hit is at **odd** address `0x21167`, so it cannot be an operand.
- **No LERP masquerade:** nearest `movea …,tp,rX` table base below the lever is `0x7010`, a 4-point record
  (X = 0/640/3200/6400) ending ≥ 0x2DA bytes short.
- **SNA detection intact** — the `0x7FFF` sentinel still fails the untouched HI bound `0xC62E8` = 12800.
- **`0xC62EE` left stock** (asserted). It is a permissive on a CAN-commanded assist-shutdown task, not a
  lockout, and must never be raised.

**On-car result 2026-07-27 (route `1a`, 58 s, 301,824 CAN frames):** ST=3 never fires; 226 frames of
`STEER_CONTROL_ACTIVE=1` below 5 km/h with `TORQUE_REQUEST=1` and `|torque|>50` in 224 of them. Carried
forward into V54 unchanged.

✅ **The engaged-at-low-speed cell has now been mined (2026-07-28).** Route `1b` is *entirely* inside it
(vEgo max 1.50 m/s, 49% engaged, 2,231 carState frames engaged below 5 km/h). **The vibration reproduces
there**, 771× engaged/disengaged — see workstream A. The collinearity break is claimed.

openpilot is not the obstacle (`CP.minSteerSpeed = 0.0`), but the StarPilot fork runs
`steerAtStandstill = False`, so at a dead stop openpilot still will not command. The real behaviour window
is roughly 0.1–3 mph: creep, parking lots, stop-and-go.

---

## Recommended next steps, in order

🛑 **NO openpilot-side modifications.** Standing operator instruction, 2026-07-28. The long-running
"openpilot-side 21 Hz notch" recommendation is **retired** — the fix must be firmware-side. openpilot
remains in scope as a *measurement instrument* (rlogs, CAN decode, correlation) only. See
`memory/feedback-no-openpilot-side-modifications.md`.

1. **V55 — a telemetry build on the proven piggyback**, to partition the hypothesis space before spending
   another behavioural flash. Measurement builds are cheap: the operator can drive a parking-lot loop in
   minutes, and the vibration reproduces there.
2. **V56 = whichever lever V55's answer indicates** — the `0xC6AF0` mute, or the damper-product
   continuation of V44/V47.
3. **The `0xC646C` decoupling** (`0x2a1ee` retarget → `0xC6CD0`) — designed and verified, still unbuilt.
   Framed as a correctness fix, but it separates the 4× forward gain from two **feedback-path** readers,
   which is a loop-gain change and therefore a live vibration candidate too.
4. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking, but it is a live inconsistency in the record.

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** It will not — `gp-0x6966` is
wind-up-driven, not speed-driven, and V31's boost floor makes wind-up unreachable. Provoking it would
require the documented EME pattern (sustained hands-off hard turn), which V31 exists to prevent.

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
