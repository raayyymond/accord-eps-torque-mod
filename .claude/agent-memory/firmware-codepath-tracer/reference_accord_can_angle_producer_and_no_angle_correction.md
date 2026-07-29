---
name: reference-accord-can-angle-producer-and-no-angle-correction
description: DECISIVE CORRECTION of reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md -- the EPS DOES transmit steering angle, on CAN 0x14A/330 (STEERING_SENSORS), not the 0x156 the prior session searched for. Full producer chain traced: FUN_00040a50 (CAN-side copy) <- gp-0x6a00 (FUN_0003e6d8) <- gp-0x6cc4 (the already-documented position-tracking accumulator) + a resolver-scaled baseline from gp+0x6470. Angle RATE (gp-0x6a56, FUN_0003f776) confirmed as the shared source for both 0x14A and 0x18F rate fields.
metadata:
  type: reference
---

# CAN steering-angle producer chain, and retraction of "EPS transmits no angle" (2026-07-29/30)

Mission: anchor the CAN-broadcast STEER_ANGLE/STEER_ANGLE_RATE to internal gp-relative variables, walking
BACKWARD from the TX packers, for a return-to-center/angle-loop investigation. `code.bin` (stock), GhidraMCP
only, gp=0xFEDF8000, tp=0xBF000.

## 🛑 DECISIVE CORRECTION — `reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md` is WRONG

That memory's bottom line ("this EPS does NOT transmit/own steering-wheel angle... zero occurrences of
`0x156`... no angle message ID") is **factually wrong**, not stale. It assumed Honda's `STEERING_SENSORS`
message lives at CAN ID `0x156` (true on some Honda DBCs) and searched for that ID specifically. On
**this** platform's DBC (`honda_accord_2018_can_generated.dbc`, ground-truthed in this kit at
`rlog-tools/decode_two_angles.py`), `STEERING_SENSORS` is **`0x14A` (330)** — a message this kit has
hooked for telemetry piggybacking since V31P and already knew was "car-facing (LKAS-related)" without
ever decoding its payload semantics by name. The EPS transmits it, confirmed both by DBC ground truth and
by disassembly of the builder below.

**opendbc ground truth (`rlog-tools/decode_two_angles.py` header, itself sourced from the DBC):**
```
BO_ 330 (0x14A) STEERING_SENSORS   (TX'd BY THE EPS)
  STEER_ANGLE        bytes 0-1 BE signed, scale -0.1 deg
  STEER_ANGLE_RATE   bytes 2-3 BE signed, scale -1.0 deg/s
  STEER_WHEEL_ANGLE  bytes 5-6 BE signed, scale -0.1 deg   <- A SECOND angle field
BO_ 399 (0x18F) STEER_STATUS       (TX'd BY THE EPS)
  STEER_TORQUE_SENSOR    bytes 0-1 BE signed, scale -1.0
  STEER_ANGLE_RATE       bytes 2-3 BE signed, scale -0.1 deg/s (10x finer copy)
  STEER_CONTROL_ACTIVE   byte4 bit3
  STEER_STATUS           byte4 bits 7:4
```
The `reference_accord_can_tx_frame_0x14a_bytemap.md` memory (2026-07-13) had ALREADY found and byte-mapped
this builder (`FUN_00055a98`) and its three signal sources (`gp-0x69ec`/`gp-0x69ea`/`gp-0x69ee`) but
explicitly flagged their **semantic identity as unresolved** ("no other memory file... references these
offsets"). This session closes that gap.

**Operator-relevant consequence**: the "dash/HDS angle reads ~4° off, wants to recalibrate" question from
the earlier (wrong) memory should be revisited — there IS a live, CAN-broadcast steering angle owned by
this EPS, and (see below) it is a SYNTHESIZED quantity built from a position-tracking accumulator that
almost certainly has its own zero-calibration state, unlike what the prior memory concluded.

## Producer chain — every hop instruction/disassembly-verified

**1. `FUN_00055a98`** (0x55a98-0x55c40) = the CAN 0x14A (330) builder, confirmed by its own checksum call
`FUN_00057b24(buf,8,0x14a)` @`0x55c18`. Byte map (bytes 0-1/2-3/5-6) already recorded in
`reference_accord_can_tx_frame_0x14a_bytemap.md`. Sources, reconfirmed by decompile:
```
0x55b0e  ld.hu -0x69ec[gp],r6   -> FUN_000218fe -> byte0-1 (STEER_ANGLE)
0x55b16  ld.hu -0x69ee[gp],r6   -> FUN_0002193e -> byte5-6 (STEER_WHEEL_ANGLE)
0x55b48  ld.h  -0x69ea[gp],r6   -> (>>3, gated |raw*0.125|<=1500) -> FUN_0002191e -> byte2-3 (STEER_ANGLE_RATE)
```

**2. `FUN_00055c42`** = the CAN 0x18F (399) builder, confirmed by `FUN_00057b24(buf,7,399)`. Decompiled in
full:
```c
byte0-1 = -(gp-0x4f60 * 0x7d >> 7)     // STEER_TORQUE_SENSOR = -(Sensor-B torque * 125/128), already on record
byte2-3 = -gp-0x6a56                    // STEER_ANGLE_RATE (10x finer copy) -- SAME source var as 0x14A's rate
byte4 bit3  = gp-0x6806                 // STEER_CONTROL_ACTIVE
byte4 bits7:4 = gp-0x6807                // STEER_STATUS
byte5 bits5:4 = gp-0x6880 & 3            // already on record (reference-accord-piggyback-channel-audit-dbc-panda)
```
Confirms `gp-0x6806`=STEER_CONTROL_ACTIVE and `gp-0x6807`=STEER_STATUS as the exact bit sources (both
already suspected from DBC-side names, now pinned to firmware variables with an instruction address).

**3. `gp-0x69ec`/`gp-0x69ee` are ALWAYS bit-identical — disasm-PROVEN, not inferred.** Both are written
ONLY by `FUN_00040a50` (confirmed: `search_instructions` on `69ec`/`69ee` finds zero writers anywhere else
in the image). Disassembly of all three branches shows the **same register** stored to both addresses:
- Fault path (`0x40a92-0x40aa8`): both get the literal sentinel `0x7fff` (separate `movea` instructions,
  same immediate).
- Mode-3 (`gp-0x679c==3` via `FUN_00040a4a`, latched one cycle via `gp-0x35bc`) path (`0x40b08-0x40b52`):
  `mov r0,r26; sub r14,r26` (r26 = `-gp-0x6a00`) then **`st.h r26,-0x69ec[gp]`** and **`st.h r26,-0x69ee[gp]`**
  — literally the same register.
- Default/computed path (`0x40b64-0x40c50`): computes and clamps a value into r28, then **`mov r28,r7; st.h
  r7,-0x69ec...`** and later **`mov r28,r16; st.h r16,-0x69ee...`** — same source register, two destinations.

⇒ **`STEER_ANGLE` and `STEER_WHEEL_ANGLE` are the SAME internal quantity, redundantly stored/shadow-checked
(via `gp-0x4c80`/`gp-0x4c82`), not two independent sensors either side of the torsion bar.** This is a
material correction to the working hypothesis in `rlog-tools/decode_two_angles.py` (which frames them as
"opposite sides of the torsion bar" and proposes `twist = WHEEL_ANGLE - ANGLE` as a topology check) — at
the firmware source, that twist is identically zero by construction; any measured difference on the wire
would be transport/rounding noise, not a physical torsion-bar signal. **The topology-check item in that
script's docstring should be retired or reframed.**

**4. Which branch is "live" during normal driving is a mode question, not fully resolved.** `FUN_00040a4a()`
= `*(gp-0x679c)`, a single-byte state read. Mode 3 uses the DIRECT SENSOR composite `gp-0x6a00`; any other
mode recomputes from the resolver-accumulator chain below and explicitly RESETS the `gp-0x35bc` latch and
STOPS updating the resolver accumulator (see `FUN_00040e7e` below, which checks `FUN_00040a4a()!=3` before
advancing `gp-0x6ce0`). Structurally consistent with "estimate before calibration ready (modes 0-2), trust
the direct sensor once calibrated (mode 3, likely sticky for the rest of the drive)" — but `gp-0x679c`'s
value semantics were NOT independently re-derived this session; this is INFERENCE from control-flow shape,
not proven. A separate, unrelated `gp-0x67DC` dispatcher-state byte is already documented in
`reference_accord_gp6cc4_tracking_pipeline.md` — do not conflate the two.

**5. `gp-0x6a00` (the "direct sensor" composite) — sole writer `FUN_0003e6d8`:**
```c
// gp+0x6470 = raw resolver/electrical-angle-adjacent register (POSITIVE gp offset -- a genuinely
// different RAM region than the gp-relative cal/state block; Ghidra mis-renders this read as
// "&DAT_00006470 + gp" pointer arithmetic in the decompile -- disasm shows the true instruction:
// `ld.h 0x6470[gp],r14` -- a POSITIVE displacement, not a DAT symbol.)
if (raw_at(gp+0x6470) changed since last cycle) {
    val = FUN_0003e600(polarity * ((raw<<16)/cal(tp+0x7432) << 9) / cal(tp+0x713a));
    gp-0x3608 = polarity * val;                    // "motor-frame" baseline
}
if (gp-0x67fe == 1 || gp-0x67fe == 2) {             // EPS FOC/assist substate active (documented elsewhere)
    term = FUN_0003e600(gp-0x6cc4 - gp-0x69d0);     // gp-0x6cc4 = the ALREADY-DOCUMENTED position
                                                      // tracking accumulator (reference_accord_gp6cc4_tracking_pipeline.md)
    gp-0x6a00 = gp-0x3608 + polarity*term + (gp-0x69ca * cal(tp+0x74f2) >> 7);
} else {
    gp-0x6a00 = 0;                                   // FORCED ZERO outside FOC substates 1/2
}
```
Two of the same gain cals used elsewhere in the resolver chain (`tp+0x7432`, `tp+0x713a`) recur here,
strongly suggesting `gp+0x6470` is a raw motor resolver/electrical-angle register and these cals are a
gear-ratio / units conversion from motor-electrical-angle space into column-angle space.

**⇒ This CONFIRMS, with a hard trace rather than inference, the "plausible (NOT proven) physical identity"
flagged in `reference_accord_gp6cc4_tracking_pipeline.md`**: `gp-0x6cc4` (a wrap-corrected, consensus-gated
position accumulator, already documented as reading like "motor resolver + turns-count") is a DIRECT input
to the CAN-broadcast steering angle. The old memory's caution ("this is an inference from thematic/structural
similarity, not proven") can be upgraded to **proven, via this session's trace of `FUN_0003e6d8`**.

**6. Angle RATE — sole writer `FUN_0003f776`, feeds `gp-0x6a56`:**
```c
iVar4 = clamp(polarity * ((gp-0x6abe * 0x30 * cal(tp+0x713a)) >> 15), -12000, +12000);
gp-0x6a56 = iVar4;                  // signed, shadow-checked vs gp-0x4ca6
gp-0x6a60 = min(abs(iVar4), ...);   // unsigned/rectified twin (2nd arg to FUN_00049a78=min not resolved)
```
`gp-0x6a56` is read directly by BOTH CAN builders (`-gp-0x6a56` packed into 0x14A byte2-3 with an extra
`>>3` + a `|raw*0.125|<=1500` gate, and into 0x18F byte2-3 raw). `gp-0x6abe` (the raw input) was not traced
further this session — flagged as open (see below).

## Consumer enumeration — CAN-TX-ONLY confirmed for the packaged angle; angle RATE and the raw accumulator
reach the control path (see companion memory `reference_accord_gp6bbe_rate_error_speed_scheduled_lane.md`
for the control-path consumer of `gp-0x6a56`)

`search_instructions` (corroborating `get_xrefs_to`'s misleading zero on all three addresses, per the
kit's own documented tp/gp xref trap):
- **`gp-0x69ec`**: 2 external readers, both CAN builders — `FUN_00055a98` (0x14A) and `FUN_00055f2e` (the
  0x19F internal-only frame, packs it into a status nibble). **Zero control-path readers.**
- **`gp-0x69ea`**: 1 external reader, `FUN_00055a98` only. **Zero control-path readers.**
- **`gp-0x69ee`**: 1 external reader, `FUN_00055a98` only. **Zero control-path readers.**
- **`gp-0x6a56`** (the underlying rate, not the CAN-packed copy): **≥15 external readers** across
  `FUN_00028ea6` (arbitration output), `FUN_0002b62c`, `FUN_0002eda8`, `FUN_00034a72` (the `gp-0x6bbe`
  "boost" aggregator lane — see companion memory), `FUN_0003b49a` (feeds `gp-0x6b2a`, one of
  `FUN_0003a382`'s seven summed inputs per `reference_accord_fun2eda8_lane9_raw_torque_command_path.md`),
  `FUN_0003eb38`, `FUN_0004d8f0`, `FUN_0004de0c`, `FUN_0004e82e`, `FUN_0004fbde`, `FUN_000517ce`, plus its
  own producer and both CAN builders. **This is the real bridge between the CAN-anchored angle domain and
  the torque/control path** — see companion memory for the load-bearing one (`FUN_00034a72`).
- **`gp-0x6cc4`** (raw position accumulator): 46 references across ~16 functions, matching
  `reference_accord_gp6cc4_tracking_pipeline.md`'s prior count exactly — that memory's own conclusion
  stands: consumers are consistency/deadband/disengage-gating (`FUN_0003c7fc`, `FUN_0003d4a2`) not
  additive torque contributors, AS FAR AS THAT SESSION'S SWEEP WENT. Not independently re-verified
  function-by-function this session; treat as corroborating, not re-proven.
- **`gp-0x69e8`** (a THIRD copy of the angle, written only in `FUN_00040a50`'s default/computed branch,
  never in the mode-3 branch): **zero readers found** by `search_instructions`. Possibly dead, possibly
  read via an encoding this method misses (the kit's own documented disp16-vs-6-byte-extended trap) —
  flagged open, not declared dead.

## Open questions / next verification
1. `gp-0x679c`'s value semantics (what mode 0/1/2/3 actually mean) — inferred from control flow only.
2. `gp-0x6abe`'s own producer (the raw input to the angle-rate formula) — not traced.
3. `gp-0x69ca`, `gp-0x69d0`, `gp-0x3608`'s exact physical units — named and located, not independently
   unit-verified.
4. `gp-0x69e8`'s apparent zero-reader status — needs the extended-6-byte-encoding corroboration this kit's
   own trap list requires before treating any "zero readers" claim as final.

## Related
[[reference_accord_can_tx_frame_0x14a_bytemap]] — the byte map this session resolves the semantic identity for.
[[reference_accord_gp6cc4_tracking_pipeline]] — the position accumulator now proven to feed the CAN angle.
[[reference_accord_gp6bbe_rate_error_speed_scheduled_lane]] — the control-path consumer of the angle-rate signal.
[[reference_accord_fun2eda8_lane9_raw_torque_command_path]] — where `gp-0x6b2a` (fed partly by angle rate via `FUN_0003b49a`) ends up (the already-eliminated `FUN_0003a382`/`gp-0x6ad4` lane).
