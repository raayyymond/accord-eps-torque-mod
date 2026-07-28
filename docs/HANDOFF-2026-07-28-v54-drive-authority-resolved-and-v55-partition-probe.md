# HANDOFF 2026-07-28 — the V54 drive, authority resolved, and V55: the partition probe

**Nothing was flashed this session. No CAN was sent.** V54 was flashed and driven by the operator
*before* this session; this session analysed that drive and produced one build, unflashed.

**Predecessor:** `HANDOFF-2026-07-27-v53-drive-result-and-v54-authority-probe.md`.

---

## 1. The question asked, and the answer

> *"I flashed the V54 RWD on a brief drive in a parking lot. This drive exhibits the vibration issue.
> What do you see in the new rlog live telemetry?"*

**The probe fired.** After two silent new-mailbox attempts, this is the kit's **first working firmware
telemetry channel**. The A/B against the V53 drive is a single bit, and it is exactly the bit the cave
writes:

| route | build | `0x14A` byte4 | bits 7:3 | bits 2:0 |
|---|---|---|---|---|
| `1a` | V53 (no probe) | `0x07` × 5,994 (100%) | 0 | 7 |
| `1b` | **V54** | `0x0F` × 5,989 (100%) | **1** | 7 |

Fault-free: `steerFaultTemporary`/`Permanent` both 0, `canValid` true in 5,711/5,713 — the piggyback did
not break the Honda checksum.

⇒ **Retire the "firmware telemetry is unobservable" anxiety.** `0x14A` byte4 bits 7:3 is proven end to
end, wire to decoder. The `+1` liveness bias did its job.

---

## 2. ★★ Authority is ~0 BY DESIGN — the `0xC6AF0` block is lifted

`wire = 1` in **5,989/5,989** frames ⇒ `gp-0x6966` ∈ [0,127] = **0.39% of saturation**, zero variation,
*including 17% of requesting frames at openpilot's ±4096 rail*.

**The framing in the decision table was wrong.** `gp-0x6966` is not a speed-scheduled authority gain — it
is the **soft-EME wind-up integrator's magnitude**:

```
gp-0x3570 += (command − bound), clamped ±(cal 0xC61DC = 30720)
gp-0x6966  = |gp-0x3570 >> 15| × (cal 0xC61DA = 1092) >> 10      [max 32760 ≈ Q15 1.0]
```

The bound is a 3-way gated MAX/MIN of corridor (driver-override), boost (angular rate), IIR (column
velocity). **No arm is vehicle road speed.** On **stock** the boost arm's `Y[0] = 0`, so at low angular
rate the bound collapses and the integrator winds — the V30 hands-off-hard-turn EME. **V31 floored boost
to 4096; V38 raised it to 5120.** The bound cannot collapse, so `(command − bound)` stays negative and the
integrator sits pinned.

**⇒ This converts V31's fixpoint from "argued, with a residual margin caveat" into on-car evidence under
railed command.** That is the drive's real contribution.

🛑 **Do NOT re-drive at road speed to "see if authority moves."** It will not — the quantity is
wind-up-driven, not speed-driven, and provoking it needs the EME pattern V31 exists to prevent.

### The consequence

Authority ≈ 0 sits in the `0xC6AF0` table's **first flat segment** (X = 0/3277/3604/19661/32768,
Y = 32768/32768/0/0/0), so **Y = 32768 (unity) is selected in 100% of normal operation** — the
`FUN_0003a382` residual lane runs at **full output bound** always, including throughout the vibration.

⇒ **"keep-live" is a no-op; mute (`Y[0]`, `Y[1]` → 0) is the only meaningful edit**, and it is licensed.
Zeroing them disables no live protection, because the derate is never invoked.

🛑 **GATE 2 IS NOT CLOSED.** The measurement proves the lane is **live**, not that it is the **culprit**.
Its damping-vs-anti-damping sign at 20 Hz remains undetermined. **Unblocked ≠ cleared to flash.**

**Process lesson:** this was partly predictable from `memory/reference-accord-soft-eme-bound-arm-gating.md`,
which already stated V31 makes authority never climb. The deadlock that motivated building V54 could have
been broken by reading it. **Check memory before building the instrument.**

---

## 3. The vibration, characterised at creep for the first time

Route `1b` never exceeded **1.50 m/s (3.4 mph)** — it sits entirely inside the sub-5 km/h cell V53's
`0xC62EA` unlock made reachable, previously structurally empty. **The vibration reproduces there:**
**771×** engaged/disengaged in the 15–26 Hz band, sharp onset at engagement, collapse at disengagement.

**Two findings that change what a fix can look like:**

1. ★ **The mode MOVES with speed** — **20.12 Hz** at 1.03 m/s mean (route `1b`) → **21.68 Hz** at
   3.99 m/s (route `1a`). 8 bins at 0.195 Hz resolution: resolved, not noise. ⇒ **no fixed-frequency
   notch can track it.** It also argues against a fixed digital artifact at 21.09 Hz. It does **not**
   resolve the 21.09-vs-78.91 aliasing question — both aliases shift together, and any 100 Hz probe
   inherits that.

2. ★ **Saturation SUPPRESSES it, speed-controlled** — at 1.2–1.6 m/s, unsaturated `1.22e9` vs railed
   `8.6e6`, a **141×** collapse (8.8× at 0.8–1.2 m/s). At the rail openpilot's output stops responding to
   the sensor: the loop opens and the oscillation dies. ⚠ **A mechanical operating-point shift
   (backlash/stiction take-up under high torque) predicts the same observation**, and this data cannot
   separate the two. Do not overclaim "closed-loop" from it alone.

Also: hands-on correlates **negatively** (r = −0.197). The ~20 Hz *is* in the openpilot command at the
same peak bin, but at only **0.091%** of command power; coherence is symmetric, so direction is unproven.

---

## 4. The damper reappraisal — raised, investigated, and WITHDRAWN

Mid-session I proposed that V44/V47 might have edited an inert calibration variant, which would have made
their nulls uninformative and revived the missing-damping hypothesis. **That is wrong, and the correction
matters more than the original claim.**

The damper factor tables are variant-coded through **three** stages, and the selector is an **EEPROM**
value absent from every flash dump:

```
5-byte coded ID -> FUN_00057f8e() match vs 16 ASCII PN keys @0xCD000 (stride 0x24) -> ROW  (0-15)
                -> index byte @0xCD012 + ROW*0x24                                   -> INDEX (0-57)
                -> ptr_array[INDEX]                                                 -> the live table
```

🛑 **ROW is NOT INDEX.** Conflating them inverts the answer — a subagent read pointer-array entries 0–3
and called them "rows 0–3". Resolved chain:

```
row  key     idx   FactorC      X0     FactorE      X0
  0  00000     0   0xCE528    1280     0xCE550      70
  1  TVAA0     4   0xD07BC    1920     0xD07F8      60
  2  TVAA1    10   0xD27BC    2240     0xD27F8      60   <== V44 AND V47 EDITED THESE
  3  TVAC1    10   0xD27BC    2240     0xD27F8      60
  6  TVAA6    10   0xD27BC    2240     0xD27F8      60
  9  TVCA0    16   0xD47BC    1920     ...
 10  TVCA3    22   0xD67BC    2240     ...
```

Our PN **39990-TVA-A160** → key `TVAA1` → row 2 → **INDEX 10** → exactly the tables V44 and V47 edited.
Corroboration: `memory/v44-built-handsoff-damping.md` cites the deadzone edge as **2240**, a number that
exists only in index 10's table — that session had it right.

⇒ **The missing-damping hypothesis was genuinely tested and IS falsified.** Do not resurrect it on a
"wrong variant" theory.

⚠ **One-bit residual:** the coded row is in EEPROM, and the TVA family **splits** — `{TVAA0, TVAA2,
TVAA4}` → index 4, `{TVAA1, TVAC1, TVAA6, TVAC4}` → index 10. **V55 carries a telemetry bit for it.**

---

## 5. Steering angle and torque — traced, with an asymmetry

- **Torque: the EPS authors it, and the chain is complete.**
  `CAN399.STEER_TORQUE_SENSOR = -floor(gp-0x4f60 × 125 / 128)`, packer `FUN_00055c42`, buffer
  `0xFEDF6BE0`, setter `FUN_000218be`, store `0x218d2`. **Every FFT in this investigation is `gp-0x4f60`
  scaled by −0.9766** — a static, memoryless, linear scale with no filtering. Our measurement anchor is
  clean.
- **Angle: the EPS does NOT transmit it.** A scan for CAN-ID literals in the TX setup finds exactly seven
  — `0x14A`, `0x18F`, `0x19F`, `0x1AB`, `0x32E`, `0x64D`, `0x660` — matching the TX scheduler descriptor
  table exactly (two independent methods). `0x156` (`STEERING_SENSORS`, carrying `STEER_ANGLE`) is not
  among them.
- **Sensor A is never read by any CAN TX builder** (two exhaustive scans). Only Sensor B reaches the bus.

---

## 6. V55 — the build

```
_v55_plain_image.bin  SHA 9ed79e68e1d02362efff5262a9f142e6e1a6596104d800d5fd6a95cef86e576c
V55 .rwd              SHA 2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf
82 bytes off V38: hook 0x55C0E (4) + cave 0xC4B34 (68) + 0xC62EA (2) + two CRC trailers
```

```
bit  7    = (damper variant INDEX >= 10)                     [static]
bits 6:3  = clamp((gp-0x6b98 >> 9) + 8, 1, 15)               [motor command, 512 counts/level]
bits 2:0  = stock STEER_SENSOR_STATUS, preserved
```

**V55 is a PARTITION, not a ninth lever.** Every falsified vibration lever — V39, V41, V42 ch.2, V43,
V45, V46, V48A, V52C — sits on the **command path** and assumes the ~20 Hz is *commanded*. `gp-0x6b98` is
the final merged command and the only path to FOC:

| observation | meaning |
|---|---|
| ~20 Hz **present** | the oscillation is commanded; command path stays in scope, `0xC6AF0` mute becomes motivated |
| ~20 Hz **absent** | all eight were doomed by construction; the search moves to the plant |
| bit7 = 1 | V44/V47 hit the live damper tables — damping genuinely falsified |
| bit7 = 0 | V44/V47 hit an inert table — damping never tested; retest on index 4 |

A null **bounds** the command's 20 Hz content to ~<512 counts against the sensor's ~550 rms; it does not
prove zero, and 100 Hz cannot separate 20 Hz from 80 Hz.

**Gates:** 50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run on the
readback, and the cave + hook **re-disassembled from the written image via GhidraMCP** (SHA-verified copy
under a distinct filename, `auto_analyze=false`, `dry_run=true`, never saved — defeating both the
stale-import and modal-save traps). Ghidra resolved all three branch targets independently onto their
labels. GATE 1 vacuous (no scratch RAM; r6/r7 only). GATE 2 vacuous (report-only; `0xC6AF0` and all damper
cals asserted stock).

**Every cave instruction is either byte-identical to V54's flashed cave or differs by a single
register/condition field from a byte-confirmed real instance.** No novel opcode value.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## 7. Method traps recorded this session

1. **★ `gp-0x6b98` is SIGNED** (`st.h` writes, `ld.h` reads). V54's source `gp-0x6966` is *unsigned*
   (`ld.hu`/`shr`). Reusing V54's encoders would have corrupted every negative command. **Check the
   signedness of a new probe source before reusing an encoder.**
2. **★ `ld.bu` encodes displacement bit 0 in the OPCODE low bit** — op `0x3C` even, `0x3D` odd, with
   `hw2 = (disp & 0xFFFE) | 1`. V54's helper hard-coded `0x3C` and could only emit even displacements;
   `gp+0x63fd` is odd *and positive*.
3. **★ Bit 0 of `hw2` discriminates width for STORES too** — `st.w` carries `|1` exactly like `ld.w`;
   only `st.h`/`st.b` are bare. `CLAUDE.md` records only the load form. A scan for a *word* variable's
   writer that assumes bare stores will miss it.
4. **★ A V54 rlog decodes as a plausible V55 reading.** V54 packs its 5-bit wire into bits 7:3 of the same
   byte; on V54 `byte4 == 0x0F` all drive, which under V55's layout reads as `field == 1, bit7 == 0` — a
   confident, actionable, fabricated answer. **Reserving a did-not-fire value does not help when another
   build writes into the same bits.** The guard that does work: a live V55 field samples the motor command
   and therefore **cannot be constant** on a driving car.
5. **ROW vs INDEX** (§4) — assume any `0xD_xxx`-region LERP is variant-coded until proven otherwise, and
   resolve the pointer before editing.
6. **Windows `MAX_PATH`** — a V54-style descriptive tag produced a 260-char output path and failed with
   `FileNotFoundError`, which looks like a missing directory but is not. Keep build tags short.

---

## 8. Recommended next steps

🛑 **NO openpilot-side modifications** (standing operator instruction, 2026-07-28). The long-running
"openpilot 21 Hz notch" recommendation is **retired**. openpilot remains a measurement instrument only.

1. **Flash V55**, one parking-lot loop. Decode with `rlog-tools/decode_v55_motorcmd.py`.
   ⚠ Check the liveness verdict **first** — the decoder refuses a constant field and says why.
2. **V56 = whichever lever V55's answer indicates** — the `0xC6AF0` mute (GATE 2 still open), or, if the
   command is exonerated, a plant-side approach.
3. **The `0xC646C` decoupling** (`0x2a1ee` retarget → `0xC6CD0`) — designed and verified, still unbuilt,
   and the strongest untested lever. The 4× gain has 6 readers across 3 subsystems and **two apply it to
   the raw torsion bar on a feedback path reaching the motor**, so the mod quadrupled *loop gain* on two
   feedback paths. ⚠ **The recorded dismissal ("−19.7 dB in-loop, so probably not the driver") is a faulty
   argument**: the low-pass attenuates stock and modified equally, so it does not defend against having
   quadrupled the loop gain at 20 Hz. Re-file it as a vibration candidate, not housekeeping.
4. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.

---

## 9. Collaterals updated this session

- `docs/STATE.md` — rewritten in place: V54 is the on-car image with its measured result; the authority
  question resolved; V55 as the flash candidate; workstream A rewritten with the creep/speed-shift/
  saturation findings; next steps renumbered and the openpilot item retired.
- `docs/BUILD-LINEAGE.md` — `0xC6AF0` moved to DIRECTION MEASURED; V44/V47 rows annotated with the
  confirmed variant chain; the ROW-vs-INDEX rule boxed in Part 1; V54 flashed + V55 added to Part 4;
  boost-floor 4096-vs-5120 clarified per build.
- `analysis-2020accord/eps_lkas_chain_model.py` — V54 block rewritten with the MEASURED result and the
  by-design explanation; `V55` added to `Calibration.for_build`; a wrong "never a store back into
  firmware RAM" claim about these caves corrected. Suite exits 0.
- `analysis-2020accord/build_v55_tva.py`, `rlog-tools/decode_v55_motorcmd.py` — new.
- `memory/` — 5 new files + `MEMORY.md` pointers, including the ROW-vs-INDEX trap and the standing
  openpilot instruction.
