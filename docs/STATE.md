# STATE — living current state of the kit

**Last updated: 2026-07-28.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed and falsified — check it before
proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-28-v55-drive-oscillation-is-internal-and-v56-mute.md`.

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it. See
`memory/feedback-explain-with-python-mirroring-decompiled-arithmetic.md`.

---

## On the car right now

**V56** = V55 + the `0xC6AF0` mute (`0xC6AFC`/`0xC6AFE` 32768→0). Flashed and driven 2026-07-29,
route `24` — **16 segments, 15:43, the kit's first ROAD drive with a firmware probe.** Fault-free.

🛑 **V56 IS THE RECOMMENDED REVERT. Flash V55 back.** The mute is **null for the 21 Hz** and **costs
damping**. Full numbers in `memory/reference-accord-v56-flashed-mute-is-null-and-costs-damping.md`;
narrative in `docs/HANDOFF-2026-07-29-v56-drive-mute-is-null-and-costs-damping.md`.

| | V56 route 24 | V55 route 1c |
|---|---|---|
| 15-26 Hz engaged/disengaged, speed-matched creep, full 16-bit CAN `0x18F` | **786×** (1.28e8 / 1.63e5) | 877× |
| command's 21 Hz (probe field, matched creep) | 182 | 22 — **not reduced** |
| command transition rate, matched creep | 23.9/s | 21.9/s |

⇒ pre-registered **outcome (iii)**. 🛑 **`gp-0x6ad4` / `FUN_0003a382` is ELIMINATED as the 21 Hz source** —
V56 killed all three branches at once via the output bound, where V43/V46/V48A each killed one.

★ **GATE 2 answered, unfavourably.** The operator reports damping removed and a new few-Hz resonance;
it reproduces as an **intermittent, sharp 8.69 Hz line** (1.18e8, **6.7×** its spectral neighbours,
n=82 windows at 15-20 m/s, engaged + hands-off, NFFT=1024). Absent from every disengaged spectrum.
⚠ Two control gaps: **no disengaged windows above 15 m/s**, and **no pre-V56 road baseline exists** —
route `13` has only segments 12-15 on disk and they are creep (vEgo max 2.73 m/s).

🛑 **A 50% partial restore (`Y = 16384`) is NOT a candidate.** The lane at 100% (V55) and 0% (V56)
produced the same 21 Hz, so intermediate authority is bounded between two agreeing measurements. It is a
partial revert wearing a candidate's clothes.

**V55** (the revert target) = V38 calibration + `0xC62EA` 320→0 + the dual probe on `0x14A` byte4
(bit7 = damper variant index ≥ 10; bits 6:3 = 4-bit `gp-0x6b98` motor command). Driven 2026-07-28
(route `1c`, 113 s parking lot), fault-free. `bit7 = 1` in 11,128/11,128 and again in 94,369/94,369 on
route `24`.

🛑 **THE PROBE UNDER-RANGES — this invalidates the record's command-side amplitudes.** On the road drive,
engaged + hands-off, **99.2% of frames sit in two adjacent levels** (field 7 = 59.0%, field 8 = 40.1%)
⇒ `gp-0x6b98` lives inside **±512** while one LSB is **512 counts**. Rail occupancy is **0.0%**. We
guarded against railing and got the opposite. The probe is a **~1-bit sign comparator**.
- **Survives:** presence and frequency (a comparator preserves zero-crossing timing), and the transition
  rate as a robust statistic.
- 🛑 **Void:** *"120.5 counts at 21 Hz"* and the *"38× over openpilot's budget"* that rests on it — that
  is under a quarter of one LSB, set by the quantiser step, not the signal.
- ⚠ **Provisional:** the *"flat H1 0.192 → 0.216, coherence 0.93"* result, and therefore the
  **elimination of the `0xC646C` reader set that it licensed**. See §Corrections.
- **Any future build must re-scale**: `SHIFT = 6` (64 counts/level) or `SHIFT = 7` (128) instead of 9.
- The full 16-bit CAN `0x18F` sensor figures are **unaffected** — keep sensor-side and command-side
  numbers rigorously separate.

**V54** (previous) = the 5-bit `gp-0x6966` authority probe. Its result stands: authority ≡ 0 by design on
V31+, so the `0xC6AF0` LERP selects unity in 100% of normal operation. **V53** before it = FOURFRAME2 cave
+ `0xC62EA` 320→0; steer-to-zero confirmed. Both superseded as flash candidates.

⚠ The `0x14A` byte4 bits 7:3 piggyback is now proven across **three** flashes (V54, V55). Use it for all
future firmware telemetry; do not build another new-mailbox channel.

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
| **V55** | the **revert target** — probe intact, no mute | ✅ built, driven, fault-free. **Flash this to undo V56.** SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| ~~**V56**~~ | V55 + the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED 2026-07-29.** Null for the 21 Hz, costs damping, adds an 8.69 Hz mode. Do not re-flash |
| `0x2a1ee` retarget → `0xC6CD0` | the `0xC646C` decoupling — correctness fix | verified safe + byte-minimal, **unbuilt**. Will NOT fix the vibration (see below) |
| `0xC6372` / `0xC636E` | the untested wideband assist EMAs | candidate #2, **needs its own GATE 2 pass** first |
| FOURFRAME2 | telemetry on IDs `0x6A0`-`0x6A3` | **retired** — the channel is unobservable |
| V49, V50, V51P, V52, VCANTX-TEST | superseded or blocked | see `docs/BUILD-LINEAGE.md` |

```
_v56_plain_image.bin  SHA 8c5c8a73425bf269c03b2e93144a7b8340983e5d873d70ea6009c0e68eacc7a0
V56 .rwd              SHA ffccf6e779498379e5d31326ba5bd7ed68da189d362b5f7ed925499df68343f4
_v55_plain_image.bin  SHA 9ed79e68e1d02362efff5262a9f142e6e1a6596104d800d5fd6a95cef86e576c  (ON THE CAR)
V55 .rwd              SHA 2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf
_v54_plain_image.bin  SHA 233188ffa21d8ae685685a48410e0c15b49ffca8af2fa8d3684f987cf1a4710b
```

**V56 is exactly 6 bytes off V55** — and only **2** of them are calibration: `32768 = 00 80`
little-endian, so muting to 0 changes only the *high* byte of each halfword. 84 bytes off V38.
50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run on the readback. The
point-count word and the whole X row are asserted unchanged, `Y[2..4]` asserted stock, V55's cave and
hook byte-identical. Decoder unchanged: `rlog-tools/decode_v55_motorcmd.py`.

**`build_v56_tva.py` is a POST-PROCESSOR over `_v55_plain_image.bin`** — it transcribes nothing from V55,
not the cave, not the hook, not the encoders. Same principle V53 used with FOURFRAME2's cave.

⚠ **`V53.assert_stock_cals()` correctly refused this edit** ("the `0xC6AF0` LERP moved — its edit
direction is UNRESOLVED"). V54's drive resolved the direction. **Do not weaken that shared guard** —
five builders depend on it. V56 runs the *unmodified* guard against the pre-edit V55 source and
re-expands its other two components against the post-edit image.

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

### A. The vibration — ★★ still open; `gp-0x6ad4` ELIMINATED 2026-07-29

🛑 **Read this before the 2026-07-28 material below.** V56's branch-agnostic mute of `gp-0x6ad4` changed
**neither** the vibration (786× vs V55's 877×) **nor** the command's 21 Hz. The prime suspect named
throughout the rest of this section is **dead**. What remains true: the mode is physical, hands-off,
engagement-dependent, moves with speed, and is internal to the EPS. What is now **provisional**: every
command-side *amplitude*, because the probe under-ranges to ~1 bit (see "On the car right now").

⇒ The search moves to the **other eight aggregator lanes**, all confirmed additive at `FUN_0003aa2c`.

★ **New symptom introduced by V56:** an intermittent, sharp **8.69 Hz** line at 15-20 m/s, engaged +
hands-off — 1.18e8, 6.7× its spectral neighbours, absent from every disengaged spectrum. Expected to
disappear on reverting to V55; **confirm that on the next drive**, because it is also the cleanest
available test that the mute was genuinely live on the car.

#### Historical framing from 2026-07-28 — the suspect it names is now eliminated

**The V55 drive (route `1c`) settled the two biggest open questions.** Full numbers in
`memory/reference-accord-v55-flashed-oscillation-is-internal.md`.

1. **The vibration is unambiguous and physical.** 20.90 Hz; **877×** engaged/disengaged on the torsion
   bar and **996×** on `STEER_ANGLE_RATE` — a *different physical quantity in the same CAN message*, so
   it is not a torque-sensor artifact. It is **hands-OFF**: on `1b`, engaged+hands-off carries **26×**
   the power of engaged+hands-on.
2. **The ~21 Hz IS in `gp-0x6b98`**, the final merged command, in the same 0.195 Hz bin as the sensor
   (coherence 0.93). **Route `1b` is a clean null control** — V54's constant field gives exactly zero
   command power, so the pipeline cannot manufacture the peak.
3. ★★ **openpilot is NOT the source.**
   ```python
   DC  = 4.0 * 3564 / 32768        # setpoint x(-4) then Q15 gain 0xC646C   = 0.4351
   IIR = 1/sqrt(1 + (21/4.97)**2)  # gp-0x3d3c pole 0.96875 @1kHz            = 0.2314
   31.7 * DC * IIR  ==   3.2       # what the LKAS lane can deliver from openpilot's 21 Hz
   31.7 * DC        ==  13.8       # even with the low-pass DELETED
   # MEASURED in gp-0x6b98:  120.5 counts   -> 38x over budget, 8.7x even unfiltered
   ```
   **And while openpilot is RAILED its own 21 Hz content is exactly 0.0, yet the command still carries
   105.8 counts at 21 Hz.** The loop closes inside the EPS, downstream of the LKAS lane's low-pass.
4. ★ **The carrier is UNFILTERED.** Sensor→command transfer (H1, 9 independent segments) is **flat:
   0.192 @1 Hz → 0.216 @21 Hz**, with only ~28° of phase rotation across the band. **A lane behind a
   pole cannot produce that** — which is what eliminates the entire `0xC646C` reader set.
5. **Damper bit7 = 1** in 11,128/11,128 ⇒ V44/V47 hit the LIVE tables ⇒ the missing-damping hypothesis
   is genuinely falsified. **Thread closed.**

🛑 **Direction is still not proven.** H1 in closed loop with no external excitation cannot separate
plant from controller, so the **damping sign remains open**. That is GATE 2 for V56.

#### Historical framing kept below for context

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

1. 🛑 **Flash V55 back.** V56 is falsified *and* it degraded the car — it removed damping and added an
   8.69 Hz mode without buying anything. V55 is already built, already driven, fault-free, and keeps the
   probe. This is a straight revert, not a new experiment.
2. **Enumerate the other 8 aggregator lanes.** This is the real opening. The 21 Hz survived a
   branch-agnostic kill of `gp-0x6ad4`, so it enters `gp-0x6b98` through a **different summand** — and
   the full list is now confirmed, every one folded in by a plain `add` at `FUN_0003aa2c`:
   `gp-0x6b62`, `-0x6b4c`, `-0x6ade`, ~~`-0x6ad4`~~, `-0x6b26` (friction), `-0x6bbe` (boost),
   `-0x6bd0` (damping), `-0x6b86`, plus `FUN_00036682`'s return. Rank them by attenuation at 21 Hz
   before proposing any lever.
3. **Re-scale the probe before the next telemetry build.** `SHIFT = 9` is ~6 bits too coarse for the
   observed ±512 range; use 6 or 7. Until then, treat every command-side amplitude in the record as void.
4. **Re-establish or retract the `0xC646C` elimination.** It rests on the flat-H1 result, which is now
   known to be a few-dof estimate through a 1-bit output. Either re-derive it on a re-scaled probe or
   demote it from "eliminated" to "not yet tested".
5. **`0xC6372`/`0xC636E`** — candidate #2, the only other lanes unattenuated at 21 Hz (−1.29 dB).
   🛑 **Needs its own GATE 2 pass first**: `gp-0x6bbe` is base power steering, and adding 60-73° of lag
   to the always-on assist loop is the **V48B brick class**. ⚠ V56 is now a cautionary precedent for
   muting a lane whose damping sign is unproven.
6. **The `0xC646C` decoupling** (`0x2a1ee` retarget → `0xC6CD0`) — build it as the **correctness fix** it
   is. ⚠ It will NOT fix the vibration: `FUN_0003a382` is not among the six readers.
7. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.
8. **The take-over beep is closed and is not a firmware item** — `commIssue`/`selfdrivedLagging`
   softDisable under chronic device CPU load, with a clean CAN/EPS null. See
   `memory/accord-takeover-beep-is-openpilot-device-load.md`.

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** It will not — `gp-0x6966` is
wind-up-driven, not speed-driven, and V31's boost floor makes wind-up unreachable. Provoking it would
require the documented EME pattern (sustained hands-off hard turn), which V31 exists to prevent.

---

## Corrections of record still worth knowing

**New 2026-07-28 — four, all byte-verified:**
- 🛑 **`0xC63D2` is `6`, not `14`.** Read little-endian from `_v55_plain_image.bin` *and* stock `code.bin`
  (identical; no build touches it), confirmed three independent ways. `alpha = 6/1024` ⇒ **fc 0.933 Hz,
  −27.1 dB at 21 Hz**, not the recorded 2.18 Hz / −19.7 dB. The golden model had this right all along.
- 🛑 **LERP tables begin with a POINT-COUNT word.** `0xC6AF0` names the *table*; `Y[0]` is at
  **`0xC6AFC`** and `Y[1]` at **`0xC6AFE`**. Writing to `0xC6AF0` would clobber the count. Proved by the
  firmware's own `addi 0xc,r15,r13` / `addi 0x2,r15,ep` at `0x3a63a`/`0x3a63e`.
- 🛑 **`gp-0x67fe` is NOT an openpilot-engagement gate** — it is the EPS's own FOC/assist substate
  (`gp-0x6772 == 5 → 2`), measured by V31P at 1 in 100% of frames *including disengaged*. So
  `gp-0x6ad4` is live during manual driving, and muting it changes manual feel.
- 🛑 **V43/V46/V48A did not exonerate `FUN_0003a382`** — it has **three parallel branches** and each
  build attenuated exactly one (`0xC644A`→64 = −7.1 dB; `0xC6450`→32 = −12.6 dB; one carrier muted).
  Three nulls are precisely what you would predict. Only the `0xC6AF0` output-bound mute kills all three.
- ⚠ **V52C's null is weaker than it looks** — its EMA was `alpha = 74/1024` ⇒ **fc ≈ 12 Hz, only
  −6.1 dB at 21 Hz** while *adding* 61° of lag. It halved the 21 Hz content; it did not remove it.

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
