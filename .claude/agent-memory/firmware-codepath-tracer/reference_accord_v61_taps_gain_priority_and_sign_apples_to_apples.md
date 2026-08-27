---
name: reference-accord-v61-taps-gain-priority-and-sign-apples-to-apples
description: "FUN_0003aa2c V61 edit sites (0x3ab6c mul r1,r6,r0 and 0x3ac16 mov r1,r8) byte-confirmed on stock; r24/r26 rate lanes and the resonance-lane P-term share the identical gp-0x6752 polarity multiplier (proven via the 6752 reader list including FUN_0003a382@0x3a71a), so their RELATIVE sign is polarity-independent -- lead-shaped, additive, never negated; gain-arm priority chain fully decoded incl. a newly-found DEAD gp-0x683c gate and an event-counter (not elapsed-time) gp-0x671d; all 6 r24/r26 gain/deadzone cals are FUN_0003aa2c-exclusive single-readers; gp-0x4f62 (torque RATE) producer/consumers fully enumerated with the 0xC64BE=0 dead-magnitude claim verified in decompiled C."
metadata:
  type: reference
---

Traced 2026-07-31 on stock `code.bin` (Ghidra, gp=0xFEDF8000, tp=0xBF000), tasked by team-lead after V61
(flashed) killed the shared-`r1` (clamped `gp-0x4f62` torque-RATE) tap at BOTH `FUN_0003aa2c` lanes and the
operator reported the ~21 Hz grinding got WORSE with LKAS on and appeared NEW in manual/reverse driving --
the working hypothesis (`docs/HANDOFF-2026-07-30-v59...`) is that this rate lane is net-damping and should
be RAISED, not cut further. Builds on and, in two places, CORRECTS
[[reference-accord-r26-adaptive-lane-full-trace-and-sign]] and the golden model's `_inline_torque_rate_a`.

**V61 edit sites, byte-confirmed unmutated on stock**: `0003ab6c: mul r1,r6,r0` (r26, first mul of the
`(dtorque*avg)>>10` stage) and `0003ac16: mov r1,r8` (r24, the tap that feeds `(dtorque*gain_B)>>10`).
Both consume the SAME `r1 = clamp(gp-0x4f62, +/-5120)` built at 0x3aaac-c0. V61 replaced `r1` with `r0`
(V850's hard-wired zero register) at both sites -- a clean, surgical kill of the derivative input into both
lanes, leaving every gain/deadzone/clamp stage downstream structurally intact (they just multiply zero).

**Q1/Q2 -- THE SIGN, apples-to-apples WITHOUT needing gp-0x6752's concrete value.** `gp-0x6752`
(assist_polarity, signed byte) is read by 30+ functions image-wide (confirmed by `search_instructions`,
zero writes among the sample scanned besides the 3 known config-parse sites), and CRUCIALLY is read by
BOTH `FUN_0003aa2c` (r24/r26, single load @0x3ab78, reused unmodified for both lanes) AND
`FUN_0003a382`'s resonance P/I/D lane (@0x3a71a) -- the one lane in this aggregator with a genuine
torque-PROPORTIONAL P-term (`P = LERP(motor_rate)*ERR>>10*32`, `ERR=clamp(gp-0x4f60-bias,+/-0x2800)`, per
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]]). Since the SAME polarity
byte scales both, the polarity cancels when comparing r24/r26 to the P-term -- their RELATIVE sign is
polarity-INDEPENDENT: **r24 and r26 are in phase with a RISING torque signal (same coefficient sign as the
P-term, applied to the derivative rather than the value), added -- never subtracted or negated -- into the
aggregator sum (`0x3acc8 mov r26,r6 ; 0x3acca add r24,r6`, confirmed by fresh disassembly, no `sub`
anywhere in the combine chain).** This is textbook lead-compensator shape (`Kp*x + Kd*dx/dt`, both
coefficients same-signed) in the SENSOR domain. [VERIFIED, high confidence: the shared-polarity-read fact,
the additive combine, dtorque's no-sign-flip current-minus-delayed producer.]
**Reconciling with the on-car result (operator, 2026-07-31, authoritative):** a sensor-domain lead does NOT
by itself prove closed-loop positive feedback or damping -- that depends on the motor-to-bar mechanical
transfer function's OWN phase at 21 Hz (which the handoff already established peaks near 21.09 Hz), a
firmware-external fact. The operator's empirical result (killing the lane made grinding WORSE and induced
it in manual/reverse) is the authoritative arbiter and says NET DAMPING in the real closed loop. [INFERRED,
not re-derivable from disasm alone: reconciling "sensor-domain lead" with "closed-loop damper" requires the
mechanical loop phase, outside firmware.] gp-0x6752's own resolved value for A160 remains OPEN (3 writer
functions, config-record parsed, not re-traced to a concrete +/-1 this session either -- see the prior
memory) but per the above this does NOT block the sign comparison to the P-term.

**Q3 -- gain-arm priority chain, byte-verified cal values (stock):** shared state cell `r2` = 1 iff
`assist_state_671a(gp-0x671a) >= cal(tp+0x74fa=0xC64FA)`, and **`0xC64FA` (byte) = 5** -- confirmed via
`ld.bu` (byte load, not halfword) at 0x3aa78. r24 priority: (1) `gate_671d(gp-0x671d)!=0` -> cal
**0xC6442=1024** (Q10=1.0, unity); (2) else `gate_683c(gp-0x683c)!=0` -> cal **0xC6446=512** (Q10=0.5);
(3) else `state_671a>=5` -> cal **0xC6440=2048** (Q10=2.0); (4) else the natural runtime LERP
(`ASSIST_RATE_B_RECORDS`, table rebuilt each cycle by `FUN_0003ad74` from ROM, Y in [1536,3072] stock).
r26 uses a DIFFERENT 2-arm subset: `gate_683c!=0` -> cal **0xC6444=512**; else `not(state<5)` (same `r2`
flag) -> cal **0xC643E=1536**; else natural LERP (`ASSIST_RATE_A_RECORDS`). Deadzone cal **0xC61F6=3**
(r24 only, 3 separate `ld.hu` reloads of the identical address inside the compare/branch, all
`FUN_0003aa2c`-local).
**NEW FINDING -- `gp-0x683c` (assist_gate_683c) has ZERO writers image-wide** (`search_instructions`
full-scan, 183,429 instructions, `truncated:false`, both `mnemonic=st.b`+`operand=683c` and an unfiltered
`operand=683c` scan; the one non-`FUN_0003aa2c` hit is a branch-target-address collision in
`FUN_00066ab6`, excluded) -- same class of finding as the confirmed-dead `gp-0x6809` E1 gate. [Method note:
single independently-run text-pattern scan, not cross-checked with a raw byte scan this session --
recommend a raw LE byte scan of the tp+0x683c-relative encodings before fully retiring this gate.] If
correct, **priority-2 (cal 0xC6444/0xC6446) is structurally unreachable on this ROM**, collapsing the real
choice to: `gate_671d!=0 ? unity : (state_saturated_at_5 ? double/1.5x : natural_LERP)`.
**`assist_state_671a` is a BOUNDED [0,5] ramp/consistency counter**, not a mode/gear id: producer
`FUN_000428d4` (SOLE writer, `st.b` @0x42a12), gated by `FUN_00046ea6(5)==0`, tracks whether a rate signal
(`gp-0x6c2c`) has kept a CONSISTENT sign for consecutive cycles with a hold-count hysteresis
(`cal tp+0x74dd`), and its output is explicitly clamped to `cal(0xC64FA)=5` as an upper bound in every
branch -- so "state>=5" in the r24/r26 selector is really "has the persistence-ramp saturated at its own
cap", not a mode/gear comparison. Feeds `FUN_00045608(2,...)`, the authority-slot setter per
[[accord-fun45608-authority-slots-not-motoroff]].
**`gp-0x671d` (assist_gate_671d) is an EVENT/RISING-EDGE counter, NOT elapsed-time-since-startup** despite
the "startup dwell" framing in [[reference_accord_fun456a4_gate_no_hysteresis_and_index_identity]] (which
compares the SAME cell against a different cal, tp+0x7500). Producer `FUN_00041d56`: applies a
multi-coefficient LINEAR FILTER (float, tp+0x70e8..0x7120, a 3-4 tap state-space-style update) to some rate
input, thresholds the result with hysteresis (cal tp+0x71f8/0x71fa), and increments `gp-0x671d` ONLY on a
0->1 (rising-edge) transition of that threshold flag, saturating at 0xff; also drives DTC 0x5e via
`FUN_00016de6(0x5e,...)`. Reset path `FUN_0003bcb2` (`st.b r0,-0x671d,gp` @0x3bd2a) not traced this
session. Widely shared: 7+ distinct reader functions besides `FUN_0003aa2c`, including
`FUN_0003d4a2` (the hardware phase-disable dispatcher / "THE motor-off site" per
[[reference_accord_fun3d4a2_hardware_phase_disable_dispatcher]]).
[OPEN, flagged not guessed: whether `FUN_00041d56`'s filtered rate signal is excited BY the 21 Hz grinding
itself (which would make `gate_671d!=0`, hence r24's unity-gain override, self-triggering during the exact
condition under study) is plausible given the structural shape but NOT confirmed -- would need either the
input signal's identity traced fully or a live gp-0x671d read during a grinding episode.]
**Practical answer to "which arm at creep, LKAS applying" is therefore CONDITIONAL, not a single fixed
arm**: if `gate_671d==0` and the persistence ramp hasn't saturated (both plausible at smooth creep, but
NOT provably so under active 21 Hz oscillation), the natural per-cycle LERP table value applies; if
`gate_671d!=0` (event counter has fired and not yet been reset), r24 collapses to a flat Q10=1.0 gain
regardless of the table. This is a genuine runtime-state question this session could not fully pin from
statics alone.

**Q4 -- headroom (worked from the confirmed producer math, D=4, believed Fs=1000 Hz for the WHOLE chain --
see below).** `gp-0x4f60(t) ~= 1400*sin(2*pi*21.09*t)` per the operator's measured bar oscillation.
Producer `FUN_0007e74a`: `gp-0x4f62 = 2*(current - delayed_D_ticks_back)/dt`, current-minus-delayed, no
sign flip (re-confirmed in fresh decompile: `uVar7 = ((sVar1-sVar4)<<1)/iVar11`), D=4 ticks
(cal tp+0x7c42=0xC6C42=4, byte-verified this session), 8-slot circular buffer. For a pure sinusoid,
peak(current-delayed) = 2*A*sin(w*D/(2*Fs)); at A=1400, Fs=1000 Hz, D=4: w*D/(2*Fs)=0.2650 rad,
sin=0.2620 -> peak(current-delayed)=734 counts -> **peak gp-0x4f62 (with dt=D=4 in native tick units)
~=367 counts** -- only ~7% of the shared +/-5120 clamp, ~14x headroom before dtorque itself saturates.
r24 at this dtorque: `scaled=dtorque*gain_q10>>10`; even at the LERP table's own max (Y=3072, Q10=3.0),
scaled~=1101, only ~13% of the +/-8192 output clamp -- **r24 needs roughly a 7-22x gain multiplier
(depending which of the 4 arms is the baseline) before it would clip at this measured amplitude.** r26's
extra `avg(gp-0x69a4)` factor is UNRESOLVED this session (as in the prior memory) so its headroom number
is [OPEN] pending that magnitude's typical range -- the STRUCTURAL formula
(`dtorque*avg_slope*gain_A/2^20`) is confirmed, just not a concrete number.
**Fs=1000 Hz assumption for the PRODUCER chain, newly corroborated (not just inherited from context):**
`FUN_0007e74a` <- `FUN_0007f3f8` <- `FUN_0006bb08`, and `FUN_0006bb08`'s sole caller is `FUN_0002214a`
@0x221e0 -- the SAME parent function that unconditionally calls `FUN_0003aa2c` @0x2291e. Both are
unconditional calls from the same per-tick task body, strong (not airtight -- no internal skip/subdivide
logic inside `FUN_0002214a` was checked) evidence the producer and the aggregator share one task rate.

**Q5 -- blast radius, ALL 6 r24/r26 gain/deadzone cals are FUN_0003aa2c-EXCLUSIVE single-readers,
byte+xref confirmed this session** (`search_instructions` full-scan, `truncated:false`, every apparent
extra hit for 0xC6440/42/44/46/643E individually checked and excluded as a branch-target-address text
collision, not a real gp/tp-relative operand): 0xC6440 (1 hit), 0xC6442 (1 real hit + 3 collisions),
0xC6446 (1 real + 3 collisions), 0xC6444 (1 real + 1 collision), 0xC643E (1 real + 4 collisions), 0xC61F6
(3 real hits, all 3 inside FUN_0003aa2c's own deadzone compare, r24-only). No sharing with any other
subsystem. FUN_0003aa2c has zero `mulf.s`/`cvtf` in the r24/r26 stretch (fresh full disassembly of
0x3aa2c-0x3ad70 confirms, corroborating the prior memory) -- **no float mirror on the consumption side**;
not independently checked this session whether the CAL WORDS THEMSELVES have a duplicate/shadow copy
elsewhere in ROM (the governor-rate-table pattern, [[reference-accord-state4-governor-ratchet]] sibling,
shows this firmware DOES do that for SOME cal blocks) -- recommend a duplicate-byte-pattern scan of the
6 values before a build if that risk matters.

**Q6 -- gp-0x4f62 consumer enumeration, COMPLETE (search_instructions, 183,429 instrs, truncated:false,
9 total touches):** producer `FUN_0007e74a` (2 reads + 2 writes, incl. a shadow-lockstep pair at
`gp-0x4488` checked via `FUN_0006b9ee` on every write -- a pre-existing safety net on the PRODUCER, not
something a gain-cal edit downstream touches); a SECOND writer `FUN_0007f3f8` (writes zero only, on an
invalid/reset branch, also shadow-checked against `gp-0x4488`); reader `FUN_0002c478` @0x2c4e8 (one `ld.h`,
but the loaded register does not surface in the decompiled C -- could not confirm at the C level whether
this is a pure validity gate or a discarded speculative load; the raw disassembly load is real, just its
downstream use wasn't visible in this decompile pass); reader `FUN_0003b66a` @0x3b6a8 -- **VERIFIED in
decompiled C**: `gp-0x4f62`'s magnitude use is gated `if (cVar8 != '\0')` where
`cVar8 = *(char*)(tp+0x74be)`, and **cal 0xC64BE was read this session = 0x0000** -> the branch never
fires -> the magnitude term is provably dead in `FUN_0003b66a`, exactly as the team-lead's brief claimed.
`FUN_0003b66a` also uses `gp-0x4f62` in an unrelated plausibility/range gate (`+/-25600`-style bounds
check) earlier in the same function -- a genuine validity-gate use, distinct from the dead magnitude term.
**Conclusion: `FUN_0003aa2c` (r26/r24) is the ONLY live magnitude consumer of gp-0x4f62 in the image**,
matching the team-lead's framing.

[VERIFIED]: both V61 edit-site instructions on stock; the shared-polarity structural sign argument; D=4 /
0xC6C42; all 6 blast-radius single-reader results; 0xC64BE=0 dead-branch in decompiled C; the complete
9-touch gp-0x4f62 enumeration; gp-0x683c zero-writer result (single-method).
[INFERRED]: reconciling sensor-domain lead-shape with the operator's net-damping on-car result (needs
mechanical loop phase, outside firmware); Fs=1000Hz for the producer chain (shared-parent-caller evidence,
not a direct rate measurement); gp-0x671d's value at creep specifically.
[OPEN]: avg(gp-0x69a4)'s realistic magnitude (blocks a concrete r26 headroom number); gp-0x683c's
zero-writer result not yet raw-byte-cross-checked; FUN_00041d56's filter input identity (is it excited by
the 21 Hz mode itself?); FUN_0003bcb2's reset trigger for gp-0x671d.

## Session 2 addendum (2026-07-31, same day) — mode-indexed B-bank, D-cal correction, V62 built from this

Team-lead independently resolved gp-0x6752=1 (byte-verified at boot in `FUN_000490ac` 0x490b6-c0, behind
its own lockstep check against gp-0x4c2d) -- CONFIRMED, closing the one [OPEN] item above. Four more
findings this round, all now folded into `analysis-2020accord/builds/v50_v79/build_v62_tva.py` (which doubles BOTH lanes
via `sar 0xa`->`sar 0x9` immediate edits at `0x3AC20`(r24)/`0x3AB76`(r26) instead of a cal edit, precisely
BECAUSE finding 1 below made the cal-table approach unsafe):

**1. r24's DEFAULT gain arm is MODE-INDEXED (r26's is NOT) -- this is the key asymmetry that killed the
cal-edit approach.** `FUN_0003ad74`'s B-bank half reads a mode-select byte at **`gp+0x63fd`** (positive
gp-relative -- confirmed `0003ad88: ld.bu 0x63fd,gp,r16`) and uses `mode*4` to index THREE parallel
4-byte-pointer arrays in ROM -- `0xCBF5C`, `0xCC044`, `0xCC12C` -- plus a 4th indirect array at `0xCC214`
-- each entry a pointer to a `{u16 count, s16 X[4], s16 Y[4]}` record elsewhere in ROM. r26's A-bank half
of the SAME function uses fixed tp-relative bases (`tp+0x7a68/7a7c/7a90/7aa4` = `0xC6A68/7C/90/A4`,
matching [[reference-accord-r26-adaptive-lane-full-trace-and-sign]]) -- mode-INDEPENDENT, always the same
4 ROM records. Traced two specific addresses by `search_byte_patterns` on their LE pointer bytes:
`0x000D2AEC`'s bytes hit ROM at `0xCC154`; `0x000D2B28`'s at `0xCC23C`. `0xCC154` is
`(0xCC154-0xCC12C)/4 = index 10` in the `0xCC12C` array; `0xCC23C` is `(0xCC23C-0xCC214)/4 = index 10` in
the `0xCC214` array -- both mode-10 slots, consistent with each other. `0x000D6AEC`'s LE pointer bytes hit
`0xCC184`, which is `(0xCC184-0xCC12C)/4 = index 22` in the SAME `0xCC12C` array -- **`0xD6xxx` is NOT a
dead/orphan mirror, it is mode-22's independently-reachable record, which happens to be byte-identical to
mode-10's.** This REPLACES an earlier (wrong) "V27 desync twin" reading team-lead had. Byte-identical !=
mirror -- a genuine different-mode slot, confirmed structurally by direct byte-pattern search on real
pointer-table boundaries (clean multiples of 4), not inferred.
**Mode = 10 for A160 is now ESTABLISHED, but by an inference not a byte read**: `docs/BUILD-LINEAGE.md`
records PN `39990-TVA-A160` -> key `TVAA1` -> config row 2 -> index 10, and V44/V47 were confirmed on-car
2026-07-28 to have hit the live table at that index; that coded row lives in EEPROM, not the flash dump,
so it's a one-bit inference (index 10 is live), not independently byte-verified in `code.bin`. Two
DIFFERENT lanes (`FUN_00034350`'s damping "mode 10/11" thresholds, and now r24's B-bank) both resolving
through the SAME `gp+0x63fd` byte to index 10 is corroborating, not proof from a second independent method.
**Practical consequence**: any cal-only edit to r24's default/natural gain table must hit every reachable
mode's record (at minimum verify which modes are actually selectable, not just assume index 10), which is
why V62 uses the `sar 0xa`->`0x9` code edit instead -- it doubles the lane's output regardless of which
gain arm (override or table) or which mode resolved to it. V850 `mul`'s high word is discarded into `r0`;
team-lead computed doubling r26's `stage1` BEFORE the `x gain_A` multiply (i.e. editing `0x3AB70`'s sar
instead of `0x3AB76`'s) pushes the worst-case intermediate to 94% of INT32_MAX vs 47% (stock) if doubled
AFTER -- so `0x3AB76` was the correct site, `0x3AB70` was rejected on that overflow-margin basis.

**2. `0xC6C42` (delay D) safety -- CORRECTED, not just confirmed, and the correction is now on record in
the build script so it isn't re-derived.** Single reader image-wide (`FUN_0007e74a`, 4 `ld.hu` instructions
for different steps of the same function's circular-buffer indexing; no second reader anywhere). D feeds
ONE computation whose result is broadcast identically to BOTH lockstep cells (`gp-0x4f62`/`gp-0x4488`) in
the same instruction sequence -- editing D cannot desync that pair, by the same reasoning as this
firmware's other single-computation-dual-store lockstep pattern (the governor-rate table). **The original
concern (D edits risk the lockstep) is retracted**; the real, surviving objection is that D sets the
differentiator's TIME WINDOW (transport lag), uncharacterised at other values -- D promoted to a candidate
**V63 PHASE lever**: 4->2 halves the lead's lag, 15.1 deg -> 7.6 deg at 20.9 Hz, held in reserve as the
fallback if V62's gain-doubling proves null on-car.

**3. `gp-0x683c` zero-writers finding -- flagged SINGLE-METHOD, not yet safe to treat as fully closed.**
Full-scan `search_instructions` (both `mnemonic=st.b`+`operand=683c` and unfiltered `operand=683c`) found
zero real writers, same class as the confirmed-dead `gp-0x6809` E1 gate -- but this was ONE method. Before
anything load-bearing rests on "priority-2 (`0xC6446`/`0xC6444`) is dead", it wants an independent raw LE
byte scan of BOTH gp-relative encodings (the 4-byte disp16 form AND the 6-byte extended-displacement form)
per [[accord-gp4f60-two-encodings-enumeration-trap]] -- not performed this session.

**4. `gp-0x69a4` / r26's `avg_slope_q10` magnitude -- still OPEN, and its axis is a flagged second-order-loop
risk.** Producer `FUN_000352b4` confirmed as an unsigned-magnitude 10-segment LERP gated by the same
+/-25600 Sensor-B plausibility window as elsewhere. Its lookup key traces one level further to
**`gp-0x6b4a`, written by the MIXER `FUN_00026c80`** (3 stores: `0x27784`, `0x2779c`, `0x277aa`) -- a
sibling channel to the LKAS mixer output `gp-0x6b4c` that this project's golden model already documents.
Which specific mixer channel `gp-0x6b4a` is was NOT resolved (would need those 3 store sites decompiled).
**Flagged, not claimed**: if `gp-0x6b4a` tracks something LKAS-command-adjacent, r26's gain is itself
partly driven by the LKAS command -- a second-order feedback loop nobody has modelled yet, structurally
analogous to the `gp-0x671d` self-excitation open question from session 1. No concrete magnitude number for
`gp-0x69a4` at creep was obtained either session; the ~546 clip threshold (session 1) remains the only
quantitative anchor.

[VERIFIED, session 2]: gp-0x6752=1 at boot (team-lead, cross-confirmed); the mode-10/mode-22 pointer-table
resolution for 0xD2AEC/0xD2B28/0xD6AEC (byte-pattern-search-verified on exact array-index boundaries);
0xC6C42 single-reader; r26 A-bank mode-independence (fresh disasm of FUN_0003ad74's second half).
[INFERRED, session 2]: mode=10 is A160's actual live config index (EEPROM-sourced per BUILD-LINEAGE, not
byte-read in code.bin -- corroborated by two independent lanes sharing gp+0x63fd, not independently proven).
[OPEN, still]: gp-0x683c's zero-writer result (single method only); gp-0x69a4's realistic magnitude and
gp-0x6b4a's precise physical identity; whether other modes besides 10/22 are reachable/relevant.
