# STATE — living current state of the kit

**Last updated: 2026-07-27.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed and falsified — check it before
proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-27-v53-drive-result-and-v54-authority-probe.md`.

---

## On the car right now

**V53** = V38 calibration + the FOURFRAME2 four-frame telemetry cave + `0xC62EA` 320→0.
Flashed 2026-07-27, driven, fault-free.

✅ **Steer-to-zero WORKS — confirmed from the rlog, not just by report.** Route `1a` segment 0:
`STEER_STATUS = 0` in **5,995/5,995** frames (ST=3 never fires anywhere) and **226 frames of
`STEER_CONTROL_ACTIVE = 1` below 5 km/h**, a cell that is structurally empty on V38. The §7 prediction
from the previous handoff held exactly.

🛑 **The four-frame telemetry still never arrived.** Zero frames of `0x6A0`-`0x6A3` across 301,824 CAN
frames on buses 0/1/2/128/129. The STRB fix was necessary but not sufficient — **or it worked and the
gateway ate the frames; the rlog cannot tell.** See "the measurement problem" below.

⚠ **V53 does NOT carry the V42 ratchet fix** (`0x454FE` is stock `0x65BA`). The state-4 governor
substitution block is live on the car.

⚠ An rlog **cannot** identify which build is flashed from the version string — every modified build
reports `fw='39990-TVA,A160'`. (It *can* now be identified behaviourally: ST=3 never firing ⇒ V53+.)

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| **V54** | V38 + `0xC62EA` 320→0 + a **5-bit `gp-0x6966` authority probe** on `0x14A` byte4 bits 7:3 | ready; **the one to flash** — it is the measurement that unblocks `0xC6AF0` |
| FOURFRAME2 | FOURFRAME + STRB fix + authority/ref-model telemetry on IDs `0x6A0`-`0x6A3` | **retired** — the channel is unobservable |
| V49, V50, V51P, V52, VCANTX-TEST | superseded or blocked | see `docs/BUILD-LINEAGE.md` |

```
_v54_plain_image.bin  SHA 233188ffa21d8ae685685a48410e0c15b49ffca8af2fa8d3684f987cf1a4710b
V54 .rwd              SHA 97ea51d2fa6b21d4584247be5571c34a5d3d15df742c2033324aae456c1c7517
_v53_plain_image.bin  SHA 6be6055357506b87afe21ea622d46bda35ececfe5bb9038834e643d0f0292e1f  (ON THE CAR)
```

**V54 is 58 bytes off V38** in 5 runs: a 44-byte cave at `0xC4B34`, the 4-byte `0x55C0E` hook, `0xC62EA`,
and two CRC trailers. Built by `analysis-2020accord/build_v54_tva.py`, which imports its encoders and CRC
gates from the FOURFRAME builder and its lockout constants + safety scans from the V53 builder, so the
only thing typed fresh is the cave. 50/50 CRC blocks, both bootloader walks, RWD decode-back with every
gate re-run on the readback, and **the cave + hook re-disassembled from the written image via GhidraMCP.**

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## ★ The measurement problem — why V54 exists

The `0xC6AF0` edit has been blocked since 2026-07-27 on one runtime number, `gp-0x6966`. Two attempts to
measure it via a **new CAN mailbox** have now produced silence, and the second silence is *uninterpretable*:

- Six IDs the stock firmware genuinely broadcasts — `0x19F`, `0x32E`, `0x64D`, `0x660`, `0x722`, `0x723` —
  are **also absent** from the same rlog, while the three openpilot's DBC knows (`0x14A`, `0x18F`,
  `0x1AB`) run at 97-100 Hz.
- Non-DBC IDs **are** logged (`0x669`, `0x750`, `0x674` all appear and are in no Honda DBC), so
  "openpilot didn't know the ID" is excluded as an explanation.

⇒ **A new-mailbox null says nothing about whether the cave fired.** Do not build a third one. Firmware
telemetry rides the `0x14A` byte4 bits 7:3 piggyback — 4 successful flashes, hook at `0x55C0E`
immediately before `FUN_00057b24` computes the checksum, and openpilot reads nothing in those bits.

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
runtime value — which is not statically determinable. **Measure `gp-0x6966` on-car first.** That is what
**V54** is for; FOURFRAME2's attempt at the same measurement is retired (unobservable channel, above).

What V54 returns, and what each answer licenses:

| observation | meaning | V55 candidate |
|---|---|---|
| wire **0** | 🛑 the cave did not fire — drive is VOID, not "low authority" | rebuild, do not interpret |
| wire **1–25** | authority ≤ 3199 throughout: lane ran at FULL bound, so it **can** be the driver | **mute** it (Y→0) |
| wire **30–31** | authority ≥ 3712: lane already clamped to zero, it **cannot** be injecting | hypothesis dies; keep-live (Y→32768) |
| **mixed** | authority crosses the knee — correlate against the 21 Hz bursts | flatten the ramp |

**Unresolved and it matters:** 21.09 and 78.91 Hz sum to exactly 100.00, and CAN 399 samples
instantaneously at exactly 100.000 Hz. Indirect evidence leans 21.09 (implied Q would be 71.8 at 78.91 Hz,
not credible) but **the rlog cannot close it, and neither can V54** — `0x14A` is also 100 Hz.

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

⚠ **The engaged-at-low-speed cell is now populated but has NOT yet been analysed for the vibration.**
Route `1a` is a single 58 s segment and the operator did not report on the vibration at creep speed. The
A/B/C collinearity break is *available* and unclaimed — do this before the next build.

openpilot is not the obstacle (`CP.minSteerSpeed = 0.0`), but the StarPilot fork runs
`steerAtStandstill = False`, so at a dead stop openpilot still will not command. The real behaviour window
is roughly 0.1–3 mph: creep, parking lots, stop-and-go.

---

## Recommended next steps, in order

1. **openpilot-side 21 Hz notch.** Zero brick risk, still untested rather than null. Keep the ±4096 rail
   fraction matched between runs — 14% of frames are railed and railed windows show no 21 Hz.
2. **Mine route `1a` for the C-low cell** — free, no flash. V53 populated "engaged below 5 km/h" for the
   first time; 226 frames is thin but it is the cell route 13 structurally could not produce.
3. **Flash V54** and take one parking-lot drive. Decode with `rlog-tools/decode_v54_authority.py`.
   ⚠ Check `wire == 0` **first** — that means the cave did not fire and the drive proves nothing.
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
