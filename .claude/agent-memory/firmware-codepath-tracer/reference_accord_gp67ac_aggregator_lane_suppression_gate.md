---
name: reference-accord-gp67ac-aggregator-lane-suppression-gate
description: gp-0x67ac (byte, sole producer = LKAS mixer FUN_00026c80, sole consumer = aggregator FUN_0003aa2c @0x3aa34) is a wholesale on/off switch -- when ==1 exactly, ALL 8 base-assist aggregator lanes (resonance/friction/boost/damping/magnitude/r24/r26/filtered-Sensor-B) drop out of the torque sum, leaving only the LKAS mixer lane + small feedforward + return-centre. Trigger condition for gp-0x67ac==1 is UNRESOLVED.
metadata:
  type: reference
---

Found 2026-07-20/21 while mapping hands-on/off discriminators for team-lead (V38 21Hz hands-off-only
vibration investigation). Traced the FULL decompile of `FUN_0003aa2c` (aggregator,
`m_motor_torque_demand_aggregator`) hunting for direct branches on `gp-0x6a5e`/`gp-0x6a62`/`gp-0x4f60` —
found none (the aggregator is a pure summer; driver-torque dependence lives entirely in the lane
producer functions it calls). But it has a mode gate nobody had documented before.

## The gate [VERIFIED, instruction-level, `0x3aa34`/`0x3aa4c`]

```c
uVar_gate = *(byte *)(gp - 0x67ac);            // 0x3aa34: ld.bu -0x67ac,gp,r8
if ((byte)(uVar_gate * (uVar_gate < 2)) == 1) { // true IFF uVar_gate == 1 exactly
    // NARROW PATH -- only reachable when gp-0x67ac == 1
    return_centre_term  = return_centre_term  * (cal 0xC74AC == 0);   // else forced 0
    lkas_lane_plus_ff    = feedforward_6ade * (cal 0xC74AB == 0) + lkas_lane_6b4c;
    // NONE of: resonance(6ad4), friction(6b26), boost(6bbe), damping(6bd0),
    //          magnitude(6b86), r24, r26, filtered_36682 are summed in AT ALL.
} else {
    // FULL PATH -- gp-0x67ac == 0 or gp-0x67ac >= 2
    full_sum = lkas_lane_plus_ff + resonance(6ad4, gated +/-0x2800)
               + return_centre_term
               + friction(6b26, gated +/-0x400)
               + boost(6bbe, gated +/-0x800)
               + damping(6bd0, gated +/-0x800)
               + magnitude(6b86, gated +/-0x3000)
               + r26 + r24;
    filtered_term = FUN_00036682();   // ONLY called in this branch
}
```
Reduction check: `v * (v<2)` equals `v` when `v<2`, else `0`. Testing `==1` therefore selects
`v==1` exactly (`v==0` gives `0==1` false; `v>=2` gives `0==1` false). Confirmed by hand for
v in {0,1,2,3}.

## Provenance of gp-0x67ac [VERIFIED, exhaustive]

`search_instructions` on operand `-0x67ac` across all 185,693 instructions: exactly 3 hits total.
- `0x2772a` (`ld.bu`) / `0x2773a` (`st.b`) — both inside `FUN_00026c80` (`m_motor_cmd_mixer`, the SAME
  function documented in [[reference-accord-mixer-lkas-source-chain]] and
  [[reference-accord-gp6b4c-lane-chain]] as the LKAS mixer). Ghidra's auto-detected function body for
  `FUN_00026c80` is truncated at `0x276dd` — the real body continues past that (this write, and the
  `gp-0x6b4c` clamp writes at `0x276e2-0x27720` immediately before it, are NOT inside the recognized
  function boundary; `get_function_by_address(0x2772a)` returns "no function found"). Anyone re-tracing
  this should widen the function or work from raw `disassemble_bytes`, not `decompile_function`, past
  `0x276dd`.
- `0x3aa34` (`ld.bu`) — the aggregator's read, described above.

The write is lockstep-checked (compares shadow `gp-0x4c37` against current `gp-0x67ac` before allowing
the update, `FUN_0006b9fa` fault path on mismatch) and copies from **`gp-0x3d98`** (`st.b r8,-0x67ac,gp`
at `0x2773a`, `r8` loaded from `-0x3d98[gp]` at `0x27732`). `gp-0x3d98` itself has exactly 2 xrefs
image-wide: written once at `0x27314` (`st.w r22,-0x3d98,gp`), read once at `0x27732`. `r22` at `0x27314`
traces to `mov r12,r22` at `0x27284`, inside the mixer's 11-channel weighted-sum loop
(`0x271de-0x27304`, channel mode array at `tp+0x5124` = `[0,0,5,0,5,5,0,0,0,5,0]` per
[[reference-accord-mixer-lkas-source-chain]]) — specifically the LAST-PROCESSED channel's mode-derived
value, conditionally updated only when an `r25` flag (origin not traced) is zero on that iteration.

## What's NOT resolved

**The semantic trigger for `gp-0x67ac==1` is OPEN.** I did not finish decoding the mixer's dense
per-channel switch/dispatch logic (`0x26c80-0x27304`, ~1.5KB of interleaved `cmp`/`setfe`/branch channel
classification) to determine what real-world condition drives this byte to exactly 1 vs 0/2+. Given the
byte is copied from a "last channel's mode" register inside a loop with a conditional-update flag, it
may simply be leftover/diagnostic loop state rather than a deliberate mode selector — OR it may be a
genuine assist-mode discriminator (LKAS-only vs LKAS+base-assist) that correlates with vehicle/ignition
state, EPS calibration variant, or (less likely given the trace so far) driver engagement. **Do not
assume any of these without further tracing.**

**Why this matters**: if `gp-0x67ac==1` is EVER true during ordinary hands-off LKAS driving (even
transiently), the entire base-assist lane family — every driver-torque-keyed term this session was
tasked to map — is silently absent from the command for that window, independent of any individual
lane's own gating logic. That would be a structurally bigger hands-on/off (or mode-on/off) discriminator
than anything found inside the individual lanes. Conversely if it's permanently 0 or permanently >=2 in
this ROM (e.g. hardcoded by a boot-time mixer config pass), it's a dead branch and irrelevant.

## Next step to close this out
Fully decompile/disassemble `FUN_00026c80` from `0x26c80` through at least `0x27750` (past its
Ghidra-truncated boundary) with attention to the `r25`/`r22` channel-loop semantics, OR find any other
xref/telemetry surface that reveals gp-0x67ac's runtime value distribution.

## Related
[[reference-accord-mixer-lkas-source-chain]] — the mixer function this gate lives inside
[[reference-accord-gp6b4c-lane-chain]] — the LKAS lane (`gp-0x6b4c`) that survives the narrow path
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] — one of the 8 lanes this gate can drop
[[reference-accord-r26-adaptive-lane-full-trace-and-sign]] — r26, another of the 8 lanes this gate can drop
