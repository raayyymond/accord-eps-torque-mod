---
name: reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal
description: "🛑🛑 RESOLVES the kit's long-open 'gp-0x6752 sign unknown' question -- it is -1, not +1, on this car (A160), confirmed at the instruction level from the boot-time config-record table at flash 0x1000. gp-0x6752 is a literal +/-1 multiply on FUN_0003a382's ENTIRE (P+I+D) PID combine (not per-term). 🛑 CORRECTED 2026-08-20 (later, same day): the FIRST version of this file's 'consequence' section misapplied this fact to GATE2's own PUMP/DAMP LABELS and got the net classification backwards. GATE2 uses a DIFFERENT, internally-consistent sign convention (in-phase-with-velocity = pumping, i.e. the opposite of the kit's canonical Re(Z) tool, which defines in-phase = damping -- verified numerically against rlog-tools/probe/decode_v90_probe.py's actual _band_transfer code). Once BOTH the convention mismatch AND the true gp-0x6752 value are applied to GATE2's RAW NUMBERS (not its labels), the answer is: D PUMPS, P and I DAMP at 6-9Hz -- i.e. GATE2's ORIGINAL headline ('D is the sole pumping term') is RECOVERED, now on verified footing instead of an assumed +1 polarity. r24/r26's pumping conclusion (ratchet-inertia's estimate, which used the correct convention from the start) is UNAFFECTED and stands."
metadata:
  type: reference
---

# 🛑🛑 SECOND CORRECTION, same day: the §Consequence table below is WRONG — see the box just above it

The original §Consequence section (still shown below, struck through in spirit, kept for provenance)
said gp-0x6752=-1 makes **P the pumper and D the damper**. That is backwards. The error: it applied the
`×(-1)` correction to GATE2's own LABELS, but GATE2's labels use a DIFFERENT sign convention than the
kit's canonical Re(Z) tool (GATE2 explicitly states its own convention: *"'In phase with +velocity'
genuinely means energy-adding"* — i.e. GATE2 calls in-phase = pumping, the standard textbook power=F·v
reading). The canonical tool (`rlog-tools/probe/decode_v90_probe.py::_band_transfer`, behind the master
3-drive `-3375ct` measurement) defines the OPPOSITE: verified numerically this session (synthetic
`T=+rate` → `Re(Z)=+1.0`, matching its own docstring's `"damper 0°"`) — **in-phase = DAMPING** in the
kit-standard sense. GATE2's raw NUMBERS (not labels) are directly convention-independent
`|H|·cos(measured phase)` quantities; reading them against the CANONICAL convention and THEN applying
the real `gp-0x6752=-1`:
```
value_D = +0.076 (GATE2's number) -> canonical: positive = D_state itself is damping-like
                                   -> x(-1) for true polarity -> delivered D = PUMPING
value_P = -0.144 -> canonical: negative = P_state itself is pumping-like -> x(-1) -> delivered P = DAMPING
```
**D pumps, P (and I) damp, net P+I+D ≈ +0.121 (damping) at 6-9Hz — GATE2's original conclusion, now
verified rather than assumed.** Full derivation, with the numerical code-check, sent to `main`. The
CORE FINDING below (gp-0x6752's actual value, the assembly, the table walk) is UNCHANGED and remains
solid — only the interpretation of what it does to the PID's pump/damp classification was wrong the
first time.

# gp-0x6752 = −1, not +1 — and it flips the whole PID's pump/damp sign

Traced 2026-08-20, task `damphunt round 3`, while chasing `ratchet-inertia`'s flagged open question
(their [[reference_accord_r24r26_driver_torque_lane_reZ_estimate]]: *"the highest-leverage single fact
anyone could resolve next"*). Corrects `reference/firmware/reference-accord-fun3a382-is-a-real-pid.md` and
[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]], both of which state "polarity
gp-0x6752 = +1, boot-static" citing only the FIRST of its three writer sites.

## The resolution [EVIDENCE, instruction-level, 2 independent read methods]

`gp-0x6752` has three writer call sites (`FUN_000490ac`, `FUN_00048a40`, `FUN_000497e6`). Every prior
trace stopped at `FUN_000490ac`'s own top-level code, which does a shadow-consistency pre-seed to `+1`
(`if (gp-0x6752==gp-0x4c2d) {both=1}`) — but that same function then runs `for(...) FUN_00048a40();`
**up to 400 times, one boot-time config record per call, and `FUN_00048a40` can OVERWRITE the pre-seed**
based on the actual flash-resident config table.

`FUN_00048a40`'s type-0x54 record handler (`0x48e36-0x48e94`), fresh disassembly:
```
0x48e3e: sld.bu 0x4[ep],r15         ; discriminator byte, record offset +4
0x48e46: addi -0x2c,r15,r0 / be     ; if byte == 0x2C (',')  -> "comma" handler @0x48e56 -> gp-0x6752=1
0x48e4e: addi -0xfa,r15,r0 / bne    ; if byte == 0xFA (-6)   -> "0xfa" handler  @0x48e76 -> gp-0x6752=-1
  0x48e86: mov -0x1,r10             ; LITERAL -1, not a 0xFF-alias
  0x48e88: st.b r10,-0x6752,gp
```
Walked the flash config-record table from `0x1000` (the function's own hardcoded fallback base,
`0x48a52: mov 0x1000,ep`, used because `gp-0x350c` starts at 0 on a cold boot) two independent ways —
Ghidra `read_memory(0x1000, 64)` and a raw Python read of `stock_fw_dump/code.bin` — agreeing. Record
format is `[u16 checksum][u8 length][u8 type][payload...]`, length-prefixed, sequential. **Exactly two
type-0x54 records exist**:
```
off=0x1180  payload@+4=0x2C (comma)  -> would set gp-0x6752=+1
off=0x14c0  payload@+4=0xFA (-6)     -> sets gp-0x6752=-1        <- LAST, address 0x14c0 > 0x1180
```
The parsing loop advances strictly by address (`ep += length` each call), processing records in
increasing-address order, "last write wins" (each handler re-checks `gp-0x6752==gp-0x4c2d` for
shadow-consistency before writing, which the FIRST write already satisfies, so no fault fires).
**⇒ `gp-0x6752 = -1` (0xFF as a signed byte) is what's actually on the ECU at the end of boot.**

**Third writer checked and excluded as a risk**: `FUN_000497e6` re-derives from the SAME saved record
pointer (`gp-0x34b8`, set unconditionally by the type-0x54 handler on every occurrence, ending pointed
at the 0x14c0 record) using an equivalent comma/-6 check — **so even if it runs, it independently
arrives at the same -1**. It also has **zero callers and zero xrefs** (`get_function_callers` and
`get_xrefs_to` both empty) — genuinely dead or reachable only via a mechanism invisible to Ghidra's
static analysis (no evidence either way, but moot given the consistency above).

**Applies to the currently-flashed car (V101), not just stock**: this table sits at flash `0x1000-0x15xx`,
architecturally below `0x13000` — every `.rwd` this kit has built flashes only `0x13000-0x100000`
(confirmed by every `.rwd` filename's range suffix). The `_v101_..._plain_image.bin`/`_v102_...` snapshot
files read `0xFF` below `0x13010` — **verified this is a snapshot-tool artifact** (the cutover is exactly
at `0x13010`, and V101 matches stock byte-for-byte from `0x13010` onward except 2 known cal bytes), not a
real erasure. **No build in this kit's history could touch this region.**

## Where it bites — FUN_0003a382's combine, confirmed structurally

Fresh decompile, the exact line (`0x3a874-0x3a888`):
```c
iVar30 = ((int)((D_state + I_state + P_state) >> 5) * gainD_gated >> 10)
         * (int)*(char *)(gp - 0x6752)                          // literal signed multiply, WHOLE sum
         * (uint)((int)*(char *)(gp - 0x6752) + 1U < 3);         // validity gate, passes for {-1,0,1}
```
**One multiply on the ENTIRE (P+I+D) sum, not per-term** — confirmed via `ld.b -0x6752,gp,r16` (SIGNED
byte load, matches the `(char)` cast) plus the surrounding mul/cmovnc sequence. `reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction.md`'s note *"Sign chain confirmed
clean: gp-0x6752 boot-static +1, ADDED into aggregator, no inversion downstream"* is **WRONG on the
value** (right that it's one clean multiply with "no inversion downstream" of the multiply itself, wrong
that the multiplied value is +1).

## Consequence — reverses the P/I/D pump/damp classification kit-wide

`docs/review/GATE2-2026-08-11-cbe74-independent.md` §N1's `|H|·cos(err/v phase)` table (and my own same-day
synthesis in [[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]]) computed these
numbers on the UNSIGNED `(D+I+P)` — i.e. relative to the filter states' own arithmetic sign, upstream of
this multiply. Apply the corrected `×(−1)`:

| term | assumed +1 (existing record) | **corrected ×−1** |
|---|---|---|
| P | −0.145 damp | **+0.145 PUMP** |
| I | −0.053 damp | **+0.053 PUMP** |
| D | +0.076 pump | **−0.076 DAMP** |
| **net P+I+D @ 6-9Hz** | **−0.122 (damping)** | **+0.122 (PUMPING)** |

**P — the LARGEST term, previously believed a clean static damper — is now the dominant PID-side pump
candidate. D, this session's assigned primary lead, is now the ONE term damping.** This does not by
itself relocate the 12-16Hz weak-flip or the unresolved grinding-band (18-22/26-31Hz) gap documented in
[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]] — those still need the SAME sign
flip applied, and the grinding-band phase gap is still genuinely unmeasured, now for P's classification
instead of D's.

## Confirms, not just "resolves the flip scenario" — r24/r26

[[reference_accord_r24r26_driver_torque_lane_reZ_estimate]] (`ratchet-inertia`, same-day) explicitly
conditioned its estimate on this exact bit: *"If gp-0x6752 is actually -1 on this car... r24/r26 flips
to the kit's best pump candidate found so far... AND it would retrodict the measured 12-16Hz-to-26-31Hz
sign structure moving toward damped, which the data shows."* **That condition is now met** — r24/r26
(confirmed same `gp-0x6752` cell, same sign, per `reference-accord-r26-adaptive-lane-full-trace-and-sign.md`)
is **−431 to −1294 ct at 6-9Hz, genuinely PUMPING**, not the +1-assumed damping estimate.

## What is UNAFFECTED — do not over-apply this correction

`gp-0x6b26`'s +518/+565 ct damping finding
([[reference_accord_gp6b26_closed_both_directions_v94_aborted]]) and the whole-car measured Re(Z)
crossover (22-26Hz, 3-drive replicated) are both **direct on-car CAN/telemetry measurements of the
delivered signal against wheel rate** — neither depends on any code-domain sign assumption about
`gp-0x6752`. Both stand exactly as before.

## What still needs doing
1. **The D-term probe design in [[reference_accord_pump_hunt_comparator_probe_candidates]]
   (`gp-0x3680` D_state etc.) is correctly aimed after all** — D is confirmed (again) as the pump, per
   the second correction above. No re-aim needed; the P-focused variant in
   [[reference_accord_pterm_is_the_most_reliable_pump_and_needs_no_new_probe_state]] is the one that's
   now WRONG (P is the damper, not the pump) — see that file's own correction banner.
2. A second independent read of `0x48e56-0x48e94` and the `0x1000` table walk, given how much rides on
   this one bit — asked `main` to have this checked before it's load-bearing for any build. This part
   of the finding (the VALUE of gp-0x6752) is unaffected by the convention-mismatch correction above.
3. **NEW, from the convention-mismatch discovery**: review/GATE2-2026-08-11-cbe74-independent.md's own labels
   should be corrected for future readers — its raw numbers are right, its PUMP/DAMP words are backwards
   relative to the kit's canonical Re(Z) convention. Flagged to `main`; not edited directly (it's a
   `docs/` file, not agent memory).

## Related
[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]] — the pre-correction synthesis this
file reverses (provenance-chase and grinding-band-gap findings there are UNAFFECTED, only the final
sign table is wrong). [[reference_accord_r24r26_driver_torque_lane_reZ_estimate]] — the estimate this
resolves. [[reference_accord_pump_hunt_comparator_probe_candidates]] — probe design, still valid.
