---
name: reference-accord-torque-sensor-zero-and-assist-bias-mechanism
description: "2026-07-23 Ghidra-verified (code.bin): full torque-sensor read chain traced from raw ADC to gp-0x4f60 -- the sensor is a resolver/quadrature (CORDIC atan2) device with a per-channel zero-reference SUBTRACTED before the angle computation, PLUS a separate additive bias term (gp-0x6b66, +/-308 counts) applied downstream -- both loaded via distinct calibration-record parsers. Also resolves what RID 0x48F6's 5 uploaded RAM cells (gp-0x6a5c/6a8e/6ba0/6ba2/6a0c) are consumed by: a dormant-during-driving factory ramp/self-test sequencer inside the assist-shaping task, not the live torque path."
metadata:
  type: reference
---

# Accord TVA-A160 torque-sensor zero/bias chain + RID 0x48F6 consumer (2026-07-23)

Mission: operator reports a STEERING PULL (constant extra force to hold straight, post-alignment) with
steeringAngleDeg reading ~4 deg off-center — hypothesis: an EPS torque-sensor neutral/assist-bias offset,
not the (already-settled-external) angle signal. Traced on stock `code.bin`, GhidraMCP only,
gp=0xFEDF8000, tp=0xBF000.

## Q1/Q3 — YES, a stored offset IS subtracted from raw torque, AND a separate additive bias exists downstream

**Producer chain**: `FUN_0007f3f8` (+ `FUN_0007ec34` on the fault/reset sub-path), called every ~1kHz
control tick (`FUN_0006bb08` <- `FUN_0002214a`) — this is the SAME producer already documented for
`gp-0x4f60` in `reference_accord_gp4f60_notch_filter_feasibility_v48b.md`; this session traces one level
DEEPER, into the actual physical-to-torque conversion math that memory didn't cover.

Per-channel (2 channels, Sensor A/B, selected by index byte `gp-0x27fa`) raw differential ADC pair:
```
sVar11 = gp[-0x5060 + ch*2] - gp[-0x5064 + ch*2]     ; channel-1 differential MINUS a stored zero-ref
sVar12 = (gp[-0x5074 + ch*2] - gp[-0x5068 + ch*2]) * gp[-0x507c + ch*2] >> 10   ; channel-2, ref-corrected + gain
```
`gp-0x5064`/`gp-0x5068` are literally **the stored per-channel zero-reference values subtracted from the
raw ADC before use** — direct, byte-verified evidence for Q1's core question.

A live reference `uVar9` (temperature-like) is subtracted with 2 more per-channel byte gains
(`gp-0x4f8a`/`gp-0x4f88`) before both differentials feed **`FUN_0006af38`** — confirmed by raw structure
(shift-add-rotate loop, phase accumulator, quadrant correction `+0x600/-0xa00/-0x200`, final wrap into
`+/-0x800`) to be a **CORDIC arctangent**. This means the torque sensor is architecturally a
**resolver/quadrature TORSION-BAR sensor** — reported "torque" is derived from a TWIST ANGLE via atan2, in
the same Q-format `+/-2048`-count angle domain used elsewhere in this firmware (see
`reference_accord_gp6cc4_tracking_pipeline.md`'s mod-2048 idiom — a sibling, not the same variable).

**The CORDIC's raw angle output then gets a SEPARATE, ADDITIVE BIAS applied in `FUN_0007f300`:**
```c
int FUN_0007f300(short param_1) {
  short sVar1 = *(short*)(gp - 0x6b66);
  if ((sVar1 + 0x134) < 0x269)      // i.e. sVar1 in roughly [-308, +308]
    param_1 = param_1 + sVar1;      // ADD the bias, unclamped case
  else if (sVar1 < 1) param_1 += -0x134;   // else clamp to -308
  else param_1 += 0x134;                    // or +308
  return param_1;
}
```
**This is exactly the "constant term not proportional to instantaneous torque" the operator's pull
hypothesis describes** — `gp-0x6b66` is added unconditionally to the raw torque-domain angle, clamped to
+/-308 counts (~15% of a 2048 full-scale count — not tiny). This is the single strongest structural
candidate found this session for an assist/torque-reading bias that could produce a directional pull.

## Where gp-0x6b66 and the sensor zero-ref come from — two DIFFERENT calibration-record parsers

**Sensor zero-ref + gain** (`gp-0x5064`/`gp-0x5068`/`gp-0x25d4` gain): loaded by `FUN_000829e2`, a
**10-state, nibble-tagged BYTE-STREAM state machine** — each call processes ONE more byte of a per-channel
record buffer (`gp-0x548 + ch*4`), tag values 0x8-0xF gate which field commits (tag 9 -> `gp-0x506c`
gain-phase + `gp-0x25d4` gain = `(cal[tp+0x59b6] * 15 * sVar3) >> 11`; tag 0xA -> `gp-0x507c` phase-gain AND
`gp-0x5064`/`gp-0x5068` themselves; tag 0xF -> **checksum verify** `gp[-0x5078] == ~gp[-0x5058]`, and on
mismatch calls `FUN_0006ff00(0,0)`/`FUN_0006ff00(1,0)` — a reset/reject). **The state advancing exactly one
step per call (not a bulk copy) is the classic shape of a live SERIAL/PWM byte decoder reading a HARDWARE
PERIPHERAL — consistent with (not proven as) the physical torque sensor continuously repeating its own
factory zero/gain/temp-comp trim in a slow/config channel (e.g. a SENT-protocol-style sensor).** If this
framing is right, this zero-reference is refreshed from the SENSOR HARDWARE ITSELF every cycle, not
EPS-persisted at all — meaning a persistent pull traced to THIS term would implicate the physical sensor,
not EPS firmware. **NOT proven — the actual byte-source peripheral/ISR driving `FUN_000829e2` was not
located this session.**

**The additive bias `gp-0x6b66`** (+ the assist-DIRECTION POLARITY flag `gp-0x6752` — the SAME gate flagged
gated/unresolved in the V49 build lineage per CLAUDE.md/`reference/builds/reference-accord-v50-lowpass-ema-cave.md`) is
loaded by a DIFFERENT function, **`FUN_00048a40`** (driven by `FUN_000490ac`): a **TLV record walker** over
a buffer at **absolute address `0x1000+`** (not gp/tp-relative — `iVar9 = *(int*)(gp-0x350c); if(iVar9==0)
iVar9=0x1000`, then `iVar9` used directly as an absolute pointer, walked by `next = current + record's own
declared length`, looped up to 400 times or until a "done" flag). **Record tag `0xA7`** (`bVar3<0xa8` branch)
writes `gp-0x6b66 = record[2]` (a signed 16-bit field) when the record's sub-type byte equals `0x10`.
Adjacent tags in the SAME parser (`0x54`, `0xA8`) write `gp-0x6752` (polarity) with a shadow-lockstep check
against `gp-0x4c2d` (mismatch -> `FUN_0006b9fa` fault) — **this ties the assist-bias load and the
polarity-gate load to the SAME record protocol**, a genuinely new connection not previously documented.
**NOT traced this session: where the `0x1000+` buffer itself gets filled** (no `movhi 0x200,` /
data-flash-region reference found anywhere near this cluster — i.e. no evidence connects this to the
`0x02000000` Data Flash found in the prior mission on this same task chain). Two live hypotheses, NOT
adjudicated: (a) a one-time boot copy from a K-line/UDS "coding" sequence (would make this look like a
factory/service-writable value); (b) a live re-parse of a continuously-repeating sensor/config message
(would make it effectively fixed at manufacture, like the zero-ref above).

## Q2 — data-flash (0x02000000) persistence: NOT established either way

No code path was found connecting `FUN_000829e2`'s byte source or `FUN_00048a40`'s `0x1000+` buffer to the
`0x02000000` Data Flash region documented in
`reference_accord_no_steering_angle_tx_eps_does_not_own_angle.md`'s addendum (that region's own driver
cluster, `movhi 0x200,` sites at `0x5112/0x520a/0x521c/0x53f0`, is entirely self-contained in the
`0x3000-0x5a00` boot range — no caller reaches the `0x24000`/`0x48000`/`0x7e000`/`0x82000` functions traced
in THIS mission). **This is a genuine gap, not a negative finding** — the actual origin of both calibration
streams (sensor-native serial vs. some other persistent store) was not resolved. Flagged as the top
open item.

## Q4 — RID 0x48F6's 5 uploaded cells: consumed by a DORMANT-DURING-DRIVING factory ramp/self-test sequencer, NOT the live torque path

All 5 cells RID 0x48F6 writes (`gp-0x6a5c`, `gp-0x6a8e`, `gp-0x6ba0`, `gp-0x6ba2`, `gp-0x6a0c` — per
`reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map.md`) have **exactly ONE reader each,
all in the SAME function: `FUN_000242a2`**, called from **`FUN_00022ca0`, the confirmed assist-shaping
task**. Inside `FUN_000242a2` they're used as **clamp thresholds/setpoints** (e.g. `gp-0x6a5c` compared
against a literal `800`, `gp-0x6a8e` against `0x9ec`, `gp-0x6ba0`/`gp-0x6ba2` range-checked +/-`0x2000` then
scaled `*0.0009765625` (=1/1024), `gp-0x6a0c` range-checked against a wide band and fed through
`FUN_0003bd40`) feeding a **large (100+ sub-state) ramp/sequencer state machine** with its own private RAM
(`gp-0x3d9x`-`gp-0x3ex`-range bytes/floats) — architecturally a multi-phase "ramp to setpoint, hold,
verify, ramp to next setpoint" self-test, gated on EPS state / near-zero live torque / a fault-flag word —
**exactly the "hands-off, torque-gated" precondition shape documented for SID 0x30 RIDs 0x48F9/0x48FB/0x48FC**
in the linked memory, whose own background worker that memory explicitly could not locate. **This
function is very likely that missing worker** — same precondition shape, same scheduler task, direct
consumer of RID 0x48F6's uploaded parameters.

**Critically: exhaustive grep of this function's full 58KB decompile for every well-known live
assist/torque-command cell (`gp-0x6bd0` damping, `gp-0x6acc` governed LKAS, `gp-0x6b94` aggregator,
`gp-0x6b98` motor command, `gp-0x69ae` setpoint, `gp-0x6ac0`/`gp-0x6ac2` motor-rate) found exactly ONE hit:
a single READ of `gp-0x6b98`** (used purely as a magnitude-gate precondition, `0x4000 < |gp-0x6b98|+0x2000`
— i.e. "only run this sequence when live motor command is near zero"). **No write to any live
assist/torque-command cell was found anywhere in this function.** This is reasonably strong (not
exhaustive-proof) evidence that this whole apparatus is a **factory/service calibration-ramp sequencer that
does NOT feed the delivered torque command during normal driving** — so RID 0x48F6's 5 values, and this
consumer, are **NOT the torque-neutral/rack-center mechanism relevant to a driving-condition pull.**

## Bottom line for the operator's pull hypothesis

- **Best candidate for a real, constant, driving-relevant assist bias: `gp-0x6b66`** (the additive term in
  `FUN_0007f300`, +/-308 counts, ~15% of full scale). Loaded via a calibration-record protocol
  (`FUN_00048a40`, tag `0xA7`) whose upstream write path (UDS-writable? one-time factory only? re-parsed
  every cycle?) is **NOT resolved** — the concrete next step.
- **The sensor's own zero-reference** (`gp-0x5064`/`gp-0x5068`) is plausibly refreshed continuously from the
  physical sensor's own serial output, NOT an EPS-persisted/drifting value — if so, a hardware sensor fault
  or the sensor's own factory trim, not an EPS calibration bug, would be the cause of a zero-drift there.
- **RID 0x48F6's uploaded values are NOT the mechanism** — they feed a self-test sequencer that appears
  inert during normal driving.
- Neither calibration stream was traced to the `0x02000000` Data Flash region — Q2 (persistence across
  key-cycles) remains genuinely open.

## Open items / next verification
1. Trace `FUN_000829e2`'s byte source (which peripheral/ISR calls it, one byte per invocation) to determine
   if the sensor zero-ref is sensor-native (continuous) or EPS-loaded-once.
2. Trace `FUN_00048a40`'s `0x1000+` buffer producer — who fills it, and when (boot-once vs. cyclic vs.
   diagnostic-session-triggered) — this directly answers Q2 for the `gp-0x6b66` bias specifically.
3. Confirm (or rule out) that `FUN_000242a2` is indeed the RID 0x48F9/0x48FB/0x48FC background worker by
   cross-checking its busy/status flags (`gp-0x67ef`, status code `0x4008` pattern matching RID 0x48F6's
   `0x4001/0x4002/0x4004` bit scheme) against the busy flags (`gp-0x6837`/`gp-0x6836`/`gp-0x68b2`) already
   documented for those RIDs.
4. If `gp-0x6b66` is confirmed UDS-writable (not just factory-set), that would be the concrete "re-writable
   bias" answer the operator's recalibration goal needs.

## Related
[[reference_accord_gp4f60_notch_filter_feasibility_v48b]] — the gp-0x4f60 producer this session traces one
level deeper (into the actual sensor-physics math it didn't cover).
[[reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map]] — RID 0x48F6/0x48F9/FB/FC context
this session's Q4 finding directly extends (locates the missing A/B/C background worker).
[[reference_accord_no_steering_angle_tx_eps_does_not_own_angle]] — the Data Flash (0x02000000) region this
session could NOT connect to either calibration stream found here.
