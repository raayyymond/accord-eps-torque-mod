---
name: reference_accord_near_centre_structure_hunt_angle_tracking_chain_found
description: Near-centre/small-signal structure hunt for grind #1 (18-22Hz, creep, engaged, near steering centre). Finds a genuine ANGLE-domain tracking-error chain (gp-0x6CC4 -> gp-0x69ca -> gp-0x6a10) that gain-modulates the boost aggregator lane via byte-dumped ROM tables (0xD24A4/0xD2528) -- but the creep-band table is confirmed FLAT ZERO, so this path is narrowed to weak-at-best in the 10-25mph band, NOT live at near-stationary creep specifically. Also confirms FactorD (damping's OWN gp-0x6a10 reader, 0xD2774) is separately flat/inert. Rules out gp-0x6752 (static cal, not a dynamic sign latch), the FUN_00042af8 "authority" deadband (permanently in one branch, not oscillating), and FUN_00036c12 friction (smooth product, matches golden model, not a bang-bang relay) as near-centre discontinuity sources. Re-confirms the pre-gain deadband 0xC61B8/0xC64A3 elimination holds independent of framing.
metadata:
  type: reference
---

# Near-centre / small-signal structure hunt (2026-08-04, team-lead brief on grind #1's centred+engaged+creep conditional)

Scope: find firmware structures that behave differently near steering-angle centre / small-signal
crossings, on the path from torque+angle sensors to the motor command. `code.bin` stock, GhidraMCP only
(`decompile_function` first, `disassemble_function`/`search_instructions` to pin bytes), gp=0xFEDF8000,
tp=0xBF000.

## Headline: a genuine ANGLE-domain tracking-error chain feeds the boost/damping aggregator lanes [EVIDENCE, fresh decompile+disasm this session]

Chases the item [[reference_accord_aggregator_domain_audit_no_angle_lane_found]] left OPEN: "`gp-0x6a10`
('tracking error')... a real, NOT-ruled-out candidate for an angle/angle-rate tracking signal." Closed
this session, angle-side:

**Producer chain, address by address:**
1. `gp-0x6CC4` -- ALREADY established elsewhere ([[reference-accord-gp6cc4-tracking-pipeline]]) as an
   angle/position-domain tracking ACCUMULATOR: 3 writers, all built from mod-2048/4096 wrap-corrected
   deltas (`addi 0x800,r28,r0`/`bge`/`addi 0x1000` idiom -- the standard signature of angle math in this
   image, matching the CORDIC/resolver's own ±2048-count domain). It also independently gates the
   decider's HOLDING-state disengage (`|gp-0x6CC4| > cal 0xC6354=4825` at `0x40e0c`, the target of V34's
   NOP patch) -- confirms the angle-domain identity from a second, independent consumer.
2. `FUN_0003bd7c` (`0x3bee0-0x3c0aa`, [EVIDENCE, disassemble_function]): reads `gp-0x6CC4` at `0x3bf0e`
   (`ld.w -0x6cc4[gp],r16`), adds the SAME mod-4096 wrapped delta (`add r16,r28`), and this feeds
   (through a conditionally-latched setpoint call `FUN_0003bd40`, gated on a `0x7fff`-sentinel validity
   check at `gp+0x6470`) into `gp-0x69ca = r26 + r25` at `0x3c09a` (`st.h r25,-0x69ca[gp]`). The whole
   `0x3bf86-0x3c118` block (which also produces `gp-0x69d0`, `gp-0x6bee`, `gp-0x6bf0`, `gp-0x6a58`,
   `gp-0x6a06`) is gated on `gp-0x67fe ∈ {1,2}` (`0x3bf76-0x3bf82`); outside that (assist not
   active/holding) the block is skipped entirely and `gp-0x69ca`/siblings are hard-zeroed / sentinel'd
   at `0x3c11e-0x3c1b8`. `gp-0x67fe==2` is the already-documented HOLDING substate (per
   [[reference-accord-damping-friction-returncentre-torque-gates]]'s correction of `FUN_00036388`).
3. `FUN_0003fc16` (`0x3fc16-0x3fc16+`, [EVIDENCE, fresh decompile]): `gp-0x6a10 = clamp(gp-0x69ca -
   slew_limited(gp-0x69e0 + gp-0x641c))` via the generic clamp helpers `FUN_00049a5a`/`FUN_00049a78`.
   Gated on the SAME `gp-0x67fe ∈ {1,2}`; else `gp-0x6a10` is forced 0. `gp-0x69e0`'s sole writer is
   `FUN_0003f884` (`0x3fc08`), itself a slower-cadence angle-domain integrator using an explicit `36000`
   (=360.00°×100) modulus/unwrap constant on the SAME `gp-0x641c`/`gp-0x69ca` family.
4. `FUN_00034a72` (boost, per [[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] section 1,
   `0x34c8c`): `r28 = r28 * LERP2(gp-0x6a10, RAM table gp-0x6394-family) `-- i.e. `gp-0x6a10` is a LERP
   **index**, gain-modulating the boost lane's torque/motor-rate baseline before it reaches `gp-0x6bbe`
   (one of the aggregator's 11 confirmed summands into `gp-0x6b98`, per
   [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]). The same aggregator-domain-audit
   memory also names `gp-0x6a10` as damping's ("Factor D") index, i.e. potentially a SECOND aggregator
   lane reads the same angle-tracking-error signal -- not independently re-confirmed this session, flag
   for follow-up.

**Net: `gp-0x6a10` is angle-tracking-error domain (target-vs-accumulated-angle, wrap-corrected, slew-limited),
not torque-domain as inherited framing assumed, and it reaches the motor command as a GAIN on the
boost baseline.** This is a genuine angle-indexed structure inside the aggregator chain, gated ON
specifically during the HOLDING substate (`gp-0x67fe==2`) -- i.e., precisely when the wheel is not being
actively driven to a new position, the closest structural proxy this kit has found yet to "near
centre, hands light, LKAS making small corrections."

## UPDATE (same session, follow-up round) — the "RAM table" IS resolvable, and it KILLS candidate #1 AT CREEP specifically

The "gp-0x6394-family is RAM-resident, not statically dumpable" framing (inherited from
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]]) was about the RUNTIME BUFFER
`gp-0x6394`/`gp-0x63a8` (rebuilt every cycle) — it is NOT true that the underlying data is unknowable.
[EVIDENCE, fresh decompile of the buffer's producer `FUN_000348e0`, `0x348e0-0x349xx`, + `read_memory`
pointer-chase]: `gp-0x6394`/`gp-0x63a8` are built by SPEED-BLENDING between two ROM tables selected from
5 mode-indexed pointer arrays (`PTR_DAT_000c92f4`/`PTR_LAB_000c93dc`/`PTR_LAB_000c95ac`/`DAT_000c94c4`/
`DAT_000c9694`, all `[mode*4]`), searched against a 5-point SPEED (`gp-0x6a5e`) breakpoint array at
`tp+0xD914[mode*4]`. For mode 10 (our car) all pointers resolve into the same `0xD2xxx` DAMP_BLOCK region
already used by FactorC/E:
```
speed axis (0xD2B64, mode10): X = [0, 512, 2560, 5120, 8960] counts = [0, 8, 40, 80, 140] km/h
table@band0 (0xD24A4, "0-8 km/h"):  X=[0,19,50,127,209,452,1019,2016,3607,4150]  Y=[0,0,0,0,0,0,0,0,0,0]  <-- FLAT ZERO
table@band1 (0xD2528, "8-40 km/h"): X=[0,34,101,245,499,846,1888,2966,3656,4150] Y=[0,678,1054,1394,1737,1915,2209,2327,2366,2360]
```
Both byte-read fresh, count=10 confirmed at offset 0, X/Y rows follow the established count-dependent
LERP struct format exactly.

**At near-stationary creep (voted speed inside [0,512] counts ≈ 0-8 km/h), the code BLENDS band0 and
band1 by fraction = speed/512.** Band0's Y-row is uniformly ZERO, so **the angle-tracking-error LERP's
contribution to the boost baseline is (fraction) × band1's (small) value** — i.e. it is genuinely near-
zero at the lowest few km/h and only ramps up as speed approaches 8 km/h and beyond. Band1 itself tops
out at Y=2366 of a Q14-ish scale (own peak ≈14% of unity, well short of saturation) at its OWN highest
breakpoint (X9=4150) — modest even once "on."

**Verdict, narrowed from the original candidate #1: this angle-tracking-gain path is essentially INERT
at the specific creep/near-stationary operating point, and only WEAKLY live as speed rises through the
0-25 mph band the operator describes** (bands 1/2, the latter — 40-80 km/h, table `0xD25AC` — not yet
dumped). This DOES NOT support a creep-specific limit cycle from this path; it MAY still be relevant at
the higher end of "low speed" (10-25 mph) where band1's rising, no longer trivial shape is live, but the
"biggest at centre + creep" reported symptom is not well explained by a term that is near-zero exactly
where the symptom is worst. Downgraded from "most promising open lead" to "narrow, speed-gated,
weak-at-creep" — record kept for completeness and because the mechanism itself (an angle-tracking-error
gain reaching the boost lane at all) remains a genuine, newly-established structural fact, useful context
for anyone chasing the 10-25 mph regime specifically.

## What is NOT resolved this session

- Band2 (`0xD25AC`, 40-80 km/h) and band3 (`0xD2630`, 80-140 km/h) Y-rows not dumped — would complete
  the picture for the upper half of "low speed."
- The only cal-addressable cell found upstream of the RAM buffer is `tp+0x7358 = 0xC6358` (stock value
  **2**, LE `02 00`, read `0x3bf86`/`0x3bf96`/`0x3bfae`), a ±2-count-per-tick STEP on `gp-0x69d0` (a
  sibling of `gp-0x69ca`, not proven to be in the `gp-0x6a10` path itself). **Not proposed as a lever**
  — not checked against `build_v*_tva.py`, and now that band0's Y-row is confirmed flat zero, editing
  anything upstream of it (in the creep band specifically) would have no effect anyway. The band0/band1
  Y-tables themselves (`0xD24A4`/`0xD2528`) ARE cal-addressable CRC-block cells, but raising a
  Y-row that is currently all-zero is a new, untested lever, not something to propose from a single
  structure-hunt session.
- The damping ("Factor D") reader of `gp-0x6a10` was named in the prior session's audit but not
  independently re-confirmed by decompile this session.
- `FUN_0003bd40`'s latch condition (the `gp+0x6470` sentinel gate feeding `gp-0x69ca`'s "r25" term) was
  read only at the disassembly level, not decompiled -- its own semantics (what event re-latches the
  target) is OPEN.

## Ruled out this session (or re-confirmed ruled out)

**1. `gp-0x6752` (assist polarity) is a STATIC calibration-record flag, not a dynamic sign latch**
[EVIDENCE, `search_instructions -0x6752`, 55 hits, 183,429 instrs scanned]. Every writer (`st.b` at
`0x48e68`/`0x48e88`/`0x490c0`/`0x49838`/`0x49844`) is inside the TLV calibration-record parser cluster
`FUN_00048a40`/`FUN_000490ac`/`FUN_000497e6` (already documented in
[[reference-accord-torque-sensor-zero-and-assist-bias-mechanism]] as boot/config-load-time only, shared
with the `gp-0x6b66` assist bias). No per-tick writer exists anywhere in the image. This closes item 4
of the brief for this specific cell: it cannot chatter, because it is never re-derived from torque or
angle at runtime.

**2. `FUN_00042af8`'s "authority" deadband is a STATIC always-on branch, not an oscillating one**
[EVIDENCE, fresh decompile+disasm, `0x434a0-0x434ea` region]. Traced `uVar34` (the deadband's compared
quantity, gate at `tp+0x7424=0xC6424=29491`) back to its producer: `uVar34 = |soft_eme_integrator_q15
>> 15| * authority_scale(tp+0x71DA=1092) >> 10`, stored to `gp-0x6966` -- this is EXACTLY the golden
model's `authority` field. V54 already measured `authority` on-car: stays in `[0,127]` (~0.39% of the
29491 threshold) on every V31+ build, because V31's boost floor (5120) prevents windup. So the deadband
`if (uVar34 < 29491) iVar45=0` is **permanently on the zero branch** in practice -- not a discontinuity
that fires near a crossing, just a term that is always zero. This corrects the framing in
[[accord-shaper-deadband-dropout]] (a REJECTED-recommendation memory already on file) -- that memory's
"combined demand crosses zero -> dropout" story describes a different, narrower internal accumulator
(`gp-0x3570`/`gp-0x356c`, the soft-EME SM2/SM3 authority path) than a general near-centre command
deadband; it is gated on authority, and authority structurally never approaches the threshold on
V31+, so this is NOT a near-centre limit-cycle source. Re-affirms (does not merely repeat) that
memory's own "REJECTED" verdict, from a different angle.

**3. `FUN_00036c12` (friction lane, `gp-0x6b26`) is a SMOOTH product, not a bang-bang relay**
[EVIDENCE, fresh decompile]. The torque-scheduled friction-magnitude table (already known,
X=(0,1280,5760), Y=(-9830,-5734,-1966), largest magnitude at `gp-0x6a5e≈0` i.e. hands-off) is multiplied
by `gp-0x6c2c` (the motor-rate derivative used by the 1kHz oscillation detector) LINEARLY -- the
apparent "boolean" in the decompile (`(ushort)(&DAT_00007d00 + gp-0x6c2c < &DAT_0000fa01)`) is an
overflow/saturation-range guard (`|gp-0x6c2c| < ~32001`), true in all ordinary operation, not a
sign(rate) bang-bang gate. So this term is continuous in motor rate and shrinks toward zero as rate
→0 (near centre / low angular velocity) -- the OPPOSITE of a classic Coulomb-friction relay, which
would hold a constant magnitude and flip sign at zero rate. Downstream it passes through a slew-rate-
limited saturation clamp (against a prior-cycle value `iVar10`) and a shadow-lockstep pair
(`gp-0x6b26`/`gp-0x4cd0`), neither of which introduces a new discontinuity. RULED OUT as a hard-relay
near-centre source; remains torque-scheduled + motor-rate-modulated as previously known.

**4. Pre-gain deadband `0xC61B8`/`0xC64A3` -- re-examined on its own merits, elimination STILL HOLDS**
[EVIDENCE, re-read of [[reference_accord_deadband_signgate_c61b8_c64a3_routes_to_diagnostics_not_motor]],
no new disassembly needed]. The team-lead asked whether the OLD elimination (made against a hands-off-
resonance framing) survives the NEW near-centre+engaged+creep framing. It does, and for a reason that
is orthogonal to framing: Finding 2 of that memory is a WIRING fact, not a triggering-condition fact --
the gate's entire output (`gp-0x6b30`/`gp-0x6b38`/`gp-0x697e`/`gp-0x697c`) routes exclusively to a UDS
diagnostic record and a sensor-plausibility voter, and was checked exhaustively against
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]'s complete 11-lane list with NO match.
Reframing WHEN the gate fires (near centre vs hands-off) cannot change WHERE its output goes. No amount
of near-centre chatter in this gate can reach the motor command. Do not re-propose.

## FOLLOW-UP ROUND (2026-08-05) — `0xC61B8` pre-gain deadband RE-DERIVED FRESH, on team-lead's request, after RULE-4 lineage audit showed it UNTESTED (not falsified) in 65 built images

Team-lead byte-read `0xC61B8` across all 65 `_v*_plain_image.bin` and found it has NEVER been written —
only referenced 59 times in `build_v*_tva.py` as an ASSERTION ("deliberately LEFT STOCK"), confirmed by
my own grep of the same files. This re-opened it as this session's leading candidate on priors (a fixed
102-count deadband is a textbook near-centre describing-function nonlinearity) and asked for a full
fresh re-derivation, not a recitation of the existing (2026-07-20/2026-07-29) elimination memories.

**Verdict: the elimination HOLDS, on fresh evidence gathered this round, for two independent reasons —
one a bypass, one a wiring dead-end — neither of which depended on the old hands-off-resonance framing.**

**1. `gp-0x6752` (polarity) — RE-CONFIRMED static, cannot chatter at any frequency.** [EVIDENCE, this
session's own earlier `search_instructions -0x6752`, 55 hits/183,429 instrs, every writer inside the
boot-time TLV calibration-record parser cluster.] It literally cannot change value during a drive, so it
was never a viable chatter mechanism at 18-22 Hz or any other rate. This answers the team-lead's Q1
narrowly. A SEPARATE, genuinely-present nonlinearity does exist in the same block (see #3) — team-lead's
underlying concern was right in spirit even though the specific `gp-0x6752` mechanism named in the old
memory doesn't produce it.

**2. The gate's trigger (`gp-0x6806==0`) is bypassed on the V72 CALIBRATION SPECIFICALLY — freshly byte-
read, not inherited.** [EVIDENCE, `read_memory` on `C:/Users/dudei/Desktop/Projects/accord-firmwares/
analysis-2020accord/_v72_plain_image.bin`, the actually-flown image]:
```
0xC61B8 (deadband L)      = 66 00 LE = 102   (stock, present)
0xC64A3 (deadband enable) = 01              (stock, enabled)
0xC62EA (speed-window-lo) = 00 00 = 0        (V53's speed-window-0 edit, CARRIED on V72)
```
`gp-0x6806`'s only path to 0 that survives V37+ debounce-saturation is `STEER_STATUS==3`, the low-speed-
lockout write (8 writers of gp-0x6806, all inside `FUN_00028ea6` itself, per the 2026-07-29 memory this
round re-uses without re-deriving — not re-verified instruction-by-instruction this round, flagged).
`STEER_STATUS==3` is ITSELF gated by cal `0xC62EA` (the low-speed-lockout window) — and V72 carries it at
**0**, meaning the window this trigger depends on cannot open at any speed. So on the ACTUAL flown
calibration, the deadband's own enable gate is bypassed essentially permanently (mechanism (A) from the
2026-07-20 memory's own A/B/C fork — now confirmed on V72's bytes specifically, not inferred from V53/
V37-era reasoning).

**3. Even on the rare tick the gate is NOT bypassed, its entire output is wiring-isolated from the motor
— corrected and re-confirmed fresh, with a stale memory conflict resolved.** [EVIDENCE, fresh decompile
of `FUN_00028ea6`'s block `0x2a1ae-0x2a23c` this round + `search_instructions` on both outputs, both
cross-checked against the 2026-07-29 agent-memory's independent count]:
```
gp-0x6b30 (self-referential sign-latch state): exactly 2 refs image-wide, BOTH inside FUN_00028ea6's own
  gate block (0x2a1d4 read = the sign-consistency "prev" test, 0x2a206 write). Never leaves the block.
gp-0x6b38 (the gate's packaged output, deadband_out + a second term, times polarity times cal 0xC646C,
  clamped ±512 via tp+0x71b2 -- NOT the same variable as gp-0x6b3c, the live arb->mixer command, despite
  the near-identical address/name): exactly 3 refs image-wide -- the one write (0x2a23c, inside
  FUN_00028ea6) plus TWO reads, BOTH inside FUN_0004e82e.
```
**`FUN_0004e82e` decompiled fresh this round: it is a pure byte-packer that writes `gp-0x69ae`/`gp-0x6802`/
`gp-0x6803`/`gp-0x6805`/`gp-0x4f60`/`gp-0x6a56`/`gp-0x6b38`/`gp-0x6807` into a caller-supplied 56-byte
buffer (`param_1+8`, length `0x38`=56 stamped at `param_1+0xc`), zero-pads the rest, and returns — a UDS/
RDBI-style diagnostic-record builder, not a live consumer.** `get_function_callers` returned no result
(tool limitation on this address, not investigated further -- the record-builder SHAPE itself is
decisive regardless of who calls it). **This corrects a stale claim in
[[accord-arb-input-cluster]]** (2026-05-27, pre-decompile era) that named `gp-0x6b38`'s reader as
`w_lkas_setpoint_consumer2` — that custom label almost certainly predates this function ever being
decompiled and is now known wrong; banner added to that file rather than silently overwritten.

Cross-checked against the complete, decompile-confirmed 11-lane `gp-0x6b98` aggregator sum
([[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]], itself re-derived from
`FUN_0003aa2c`'s decompile earlier the same day by a different session): neither `gp-0x6b30` nor
`gp-0x6b38` appears among the 11 summands. **No code path connects this deadband's output to the motor
command, at any gate state.**

**4. Physical units of the deadband's input (`iVar34`), and the 102-vs-104 comparison — NOT closed to a
literal counts conversion; domain mismatch argued instead.** [BELIEF, partial trace only] Traced `iVar34`'s
raw pre-IIR input (`iVar23`) two hops upstream: it is a product of several mode-indexed LERP curves
(pointer arrays at `0xCB7D4`/`0xCBAE4`/`0xCBB54`/`0xCBC34`/`0xCBBC4`-family, NOT yet identified against any
existing named signal) clamped to `±tp+0x71b6`, inside the SAME arbitration-core function
(`FUN_00028ea6`) that also computes the LIVE arb output `gp-0x6b3c` — i.e. this is an
arbitration/driver-torque-side quantity, structurally unrelated to grind #1's rate index (`gp-0x6ac0`,
whose entire producer chain is the motor/resolver electrical-rate cascade `FUN_00041464`, per
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]] — no shared producer, no shared cal,
no code path found connecting the two chains). **Did not close a literal counts-to-counts conversion**
(would need the arb-torque-domain scale factor, not traced this round) — but the domain-disjunction
argument stands on its own: the 102-vs-104 numeric proximity has no established basis and, given #2/#3
above, is moot regardless of its value.

**5. Address sanity + blast radius.** `0xC61B8 = tp(0xBF000)+0x71B8`, arithmetic confirms it sits inside
the main `0xC6000-0xC6FFF` cal block, NOT `[0xC5000,0xC5FFC)` (the CRC-skipped/V40-brick-precedent
block). No float-twin/lockstep monitor found on `0xC61B8` or `0xC64A3` specifically (unlike `0xD209C`,
flagged separately by team-lead as float-twin-monitored at `0xC6554` with a DTC-0x1d escalation) — an
edit here risks corrupting only the UDS diagnostic record's content, not tripping a hard-shutdown monitor.
**Direction/widen-vs-narrow question is MOOT given #2/#3: no calibration value at this address can affect
grind #1, so there is no lever to size.**

## Cross-check against team-lead's parallel FactorC/E trace — FactorD (damping's own gp-0x6a10 reader) is separately confirmed inert

[[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] (same day, different session) fully
mapped `FUN_00034350` (damping, `gp-0x6bd0`) and independently found **FactorD: key `gp-0x6a10`
(angle-deviation), gate `gp-0x67fe∈{1,2}` && `<9999`** — the SAME gate and SAME signal this memory's
chain traces the producer of — **ptr array `0xC9DB4[mode*4]` → mode10 `0xD2774`, byte-read
Y=(1024,1024,1024,1024,...) — flat/inert.** Two independent sessions, two independent aggregator lanes
(boost's LERP2 here vs damping's FactorD there), both consuming the SAME `gp-0x6a10` angle-tracking-error
signal, and BOTH confirm their own copy of the consuming table is flat (inert Y=1024 for damping,
inert Y=0 for boost's creep band) on this car's calibration. This is strong convergent evidence that
whatever this signal is FOR, it is not currently exercised by either aggregator lane's static table —
raises the prior (both memories') "not yet a lever" verdict to "confirmed non-lever on the current
calibration, for both known readers, at least at low-to-moderate signal / creep speed."

## Note on `FUN_000352b4` (`gp-0x6b86`+`gp-0x69a4`, "friction magnitude") — not chased, flagged for whoever picks it up

Decompiled far enough to characterize its shape, not its full semantics [EVIDENCE, partial]: it is an
**adaptive, self-fitting 10-segment piecewise curve** — each 1kHz(?)/100Hz cycle it walks a per-segment
min/max tracker seeded from `gp-0x6444`+offset and a mode-selected consistency table, producing a live
lookup structure (`gp-0x37xx`-range locals) rather than reading a fixed ROM curve directly, then indexes
it by a magnitude derived from `gp-0x4f60` (torque). This is NOT the gp-0x6a10 angle-tracking chain (no
shared variables found) and is NOT assigned to me this session (team-lead's `gp-0x6b26`/`gp-0x6b62` split
went to a sibling agent; this is a third, separate lane in the same producer list). Its outputs feed
`gp-0x6b86` (aggregator lane, already known elsewhere as "peak-hold") and `gp-0x69a4` (read back by r26,
per the golden model's `inline r26 <- gp-0x4f62 x avg(gp-0x69a4) x generated Q10 gain`). Flagging as
OPEN/self-adapting rather than chasing further — if a near-centre discontinuity exists in its 10-segment
fit, it would show up as a kink between adjacent segments, not a classic deadband/sign-flip; would need a
dedicated session.

## Related
[[reference_accord_aggregator_domain_audit_no_angle_lane_found]] -- the audit this session's headline
finding closes (gp-0x6a10 side); its "no angle/angle-rate input found in any of the 11 lanes" verdict is
now REVISED for boost (and possibly damping): angle-tracking-error is present, as a multiplicative gain
index, not an additive term -- the audit's own search scope (primary inputs) would have missed a
secondary gain-modulation index.
[[reference-accord-gp6cc4-tracking-pipeline]] -- source of `gp-0x6CC4`'s angle-domain identity, reused
here as the root of the chain.
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] -- source of the `LERP2(gp-0x6a10, ...)`
citation in boost's baseline computation (section 1), confirmed consistent with this session's producer
trace of gp-0x6a10 itself.
[[accord-shaper-deadband-dropout]] -- the REJECTED memory this session's ruled-out item 2 re-examines
from the authority-producer side.

## Open questions / next verification
1. Live-RAM or telemetry capture of `gp-0x6394`-family (LERP2's table) and `gp-0x6a10` together, to
   determine the table's shape near index≈0 -- the single highest-value next step for this thread.
2. Independently decompile/confirm damping's ("Factor D") reader of `gp-0x6a10`, if any -- named but not
   re-verified this session.
3. Decompile `FUN_0003bd40` to close `gp-0x69ca`'s latch semantics.
4. Check `0xC6358` (tp+0x7358) against `build_v*_tva.py` before ever naming it as a lever candidate --
   not done this session, and it was not proposed as one.
