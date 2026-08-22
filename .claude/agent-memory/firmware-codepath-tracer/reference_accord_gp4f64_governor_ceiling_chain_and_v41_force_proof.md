---
name: reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof
description: Full re-verified chain for the motor-rate-scheduled torque ceiling gp-0x4f64 -- FUN_00049a90 is a real 3-arg clamp(v,lo,hi) (settled by literal Python execution of the decompile after a manual pcode trace gave a wrong answer), the axis clamp in FUN_0007b022 (cal 0xC559C=10000.0), the EMA filter in FUN_00041464 (alpha=37/128, ~54Hz corner @1kHz), gp-0x4f0c identified as a temp-compensation channel, NEW gp-0x4f64 consumers found (FUN_0006e09a/FUN_0006e140 write straight to gp-0x6b98), and V41's force independently proven (hash + fresh cipher decode, not inferred from the build script).
metadata:
  type: reference
---

# gp-0x4f64 governor-ceiling chain, fully re-verified (2026-08-22, orchestrator "ceiling-trace" mission)

Stock `code.bin`. gp=0xFEDF8000, tp=0xBF000. All claims below are EVIDENCE (GhidraMCP decompile +
disassemble + Python cross-check) unless marked BELIEF.

## The clamp helper family, settled by literal execution, NOT hand-derivation
`FUN_00049a78(a,b)` = unsigned MIN (trivial, clean decompile, no ambiguity).
`FUN_00049a70(a,b)` = signed MAX (trivial, clean decompile).
`FUN_00049a90(v,lo,hi)` = a standard 3-arg **`clamp(v,lo,hi)`**. 🛑 **My own first attempt at this
(manual CMOV/pcode trace) produced a nonsense result** ("return hi whenever v>=lo, regardless of v vs
hi") — caught before reporting by literally transcribing Ghidra's decompiled C into Python and running
concrete vectors (`clamp(50,0,100)->50`, `clamp(-50,0,100)->0`, `clamp(150,0,100)->100`, symmetric
±3000 case all correct). **Lesson: for this V850 overflow-corrected-signed-compare idiom (used all
over this codebase, see `FUN_00049a70`/`78`/`90` and their many call sites in `FUN_0004503c`'s
housekeeping loop), hand-tracing the boolean algebra is unreliable even when done carefully twice —
execute the decompiled C directly on concrete vectors instead.** This trio is reused dozens of times
across `FUN_0004503c` for a family of independently soft-started Q15 "channel" scales (targets/steps
not fully characterized this session).

## FUN_0004503c (governor), 0x453f0-0x453fe — the clamp itself
```
0x453f0  ld.hu  -0x4f64[gp],r8     ; r8 = G = gp-0x4f64 (unsigned, runtime governor value)
0x453f4  mul    r26,r8,r0          ; r8 = low32(G * chanA)   chanA = a soft-started Q15 "channel" scale
0x453f8  sar    0xf,r8             ; r8 = bound = (G*chanA)>>15
0x453fa  mov    r8,r7
0x453fc  subr   r0,r7              ; r7 = -bound
0x453fe  jarl   0x00049a90,lp      ; clamp(raw_demand=r6, -bound, +bound)   r8 still holds +bound, unclobbered
```
`raw_demand` = `gp-0x6b94` loaded at `0x453e0`, i.e. the aggregator SUM (confirms golden model). Result
feeds the existing (already golden-modeled) asymmetric slew logic. **Caller: sole caller is
`FUN_0002214a`, the confirmed ~1kHz control task — but the CALL ITSELF IS GATED, see state-mask section
below.**

## FUN_0007b022 (gp-0x4f64 writer / cap-table lookup), the axis
`gp-0x6ac0` (motor electrical rate) is read once (`ld.hu -0x6ac0[gp]`), then:
```python
z_pre = clamp(gp_6ac0_as_float, 0.0, cal(0xC559C))   # cal(0xC559C) = 10000.0 (float32), VERIFIED Python read
z = round_clamp_int16(fVar48 * z_pre, -32767, 32767)  # int16 search key into the cap table
```
`fVar48` is **NOT** the naive `gp-0x6930*0.0625` I first found (that computation is discarded/overwritten
before use — self-caught, see below). The real `fVar48` is a normalization ratio gated by comparisons
among `cal(0xC5648)=1.0`, `cal(0xC564C)=1.0` (both VERIFIED stock float32), a clamp of RAM value
`gp-0x4f0c` (scaled ×1/64) between `cal(0xC6594)=-1.0`/`cal(0xC6598)=1.0`, and raw cals `0xC60AC=0.6346`,
`0xC60D4=0.002`, `0xC60D6=-71.615` (all float32, VERIFIED). **`gp-0x4f0c`'s producer (`FUN_00063818`) is
identified this session as a dedicated ANALOG SENSOR ACQUISITION task** — direct HW ADC register reads
(`**(uint**)(gp-0x2e58)&0xffc`), `__disable_irq()/__enable_irq()` critical sections, producing a family
of Q12-EMA-filtered channels (`gp-0x4f0c`, `gp-0x4f0a`, `gp-0x4f06`, `gp-0x4f1e`, `gp-0x4f08`, `gp-0x618`)
via `raw*4096+prev*(2^n-1)>>n`, shift cals at `tp+0x5a05/06/09/0a` all =4. A sibling channel in the SAME
function, `gp-0x4e79`, is what `FUN_0007b022` itself uses as `(byte)-70.0` — a textbook ADC-to-°C
conversion, and `gp-0x4f0c` additionally goes through `FUN_0006417c` (a gain/offset LERP using another
filtered channel as blend fraction) — **BELIEF: `fVar48` is a temperature-compensation-domain scale**,
corroborating a "protective, thermally-scheduled" reading of the whole cap table. **Numeric value at a
representative operating point NOT computed this session** (would need `FUN_0006415e`/`FUN_0006417c`'s
full ADC scaling) — the reachability-in-°/s conversion this file's companion memory gives assumes
`fVar48≈1` and is BELIEF, not closed.

Cap table bytes (0xC520C/0xC5224 records, 0xC5030/0xC5038 slopes) — byte-identical to the existing kit
record: count=5, X=[1050,1700,2500,3700,4100], Y=[5325,3584,2406,1587,512], slopes Q13=
[-21940,-12059,-5593,-22021] both copies. **One correction to the existing record's pairing**: inside the
search+interpolate loop, copy-1's search (via `0xC520C`'s own X/Y arrays) draws its SLOPE from
`0xC5038` (not `0xC5030`), and copy-2 draws from `0xC5030` — CROSS-WIRED relative to the naive
same-index pairing the build scripts document. Doesn't change V41's correctness (both blocks zeroed
identically regardless) but matters for any future edit that wants the two copies to diverge.

**GATE 1 on 0xC520C/0xC5224/0xC5030/0xC5038: CLEAN.** `search_instructions` on the CORRECT tp-relative
displacements (`0x620C`/`0x6224`/`0x6030`/`0x6038` — not `0x5030`/`0x5038`, an easy off-by-0x1000-style
query mistake I made and caught) found 5/3/2/2 hits respectively, **100% inside `FUN_0007b022`, zero
readers anywhere else in the image.** Cross-checked with an independent raw Python LE scan, identical
counts.

## FUN_00041464 (gp-0x6ac0 filter), the missing dynamic element
`gp-0x6ac0`'s producer is NOT `FUN_0007b022` — one hop further upstream. `gp-0x4f50` (the filter's raw
input — already settled by a PRIOR session, `reference-accord-gp4f50-is-a-rate-not-an-angle.md`: the
wrap-corrected first difference of a 16384-count ELECTRICAL angle) feeds a genuine single-pole EMA on a
persistent 32-bit RAM accumulator `gp-0x359c`:
```python
target = raw << 10
state_new = state_old + (((target - state_old) * cal(0xC643C)) >> 7)   # cal(0xC643C)=37 VERIFIED, alpha=37/128
gp_6ac0 = abs(state_new) >> 10
```
**Corner ≈54.3 Hz** (`tau_samples=-1/ln(1-37/128)=2.929`, at the confirmed 1kHz task rate). **The
abs() happens AFTER the filter, not before** — i.e. this is [linear EMA] -> [rectify], not
[rectify]->[filter]. See the companion memory `reference_accord_rectifier_envelope_and_amplitude_bound.md`
for why this makes the 54Hz corner NOT a refutation of an HF-grind-modulates-the-ceiling mechanism (my
own first framing of the corner as "too fast to matter" was aimed at the wrong hypothesis — a linear
resonator — not the right one, a demodulator).

## 🛑🛑 State-gating — I independently re-derived an ALREADY-RETRACTED misreading before catching it
`FUN_0002214a` gates calls to `FUN_00041464`, `FUN_0007b022` (via `FUN_0006bb08`), AND `FUN_0004503c`
itself on `r25 = 1 << (gp-0x67fa & 0xf)` tested against masks `0xC30`={4,5,10,11} (aggregator/writer) and
`0xD30`={4,5,8,10,11} (filter AND governor clamp — `0xD30` = `0xC30 | 0x930`, the union of the aggregator
mask and the arbitration mask `0x930`={4,5,8,11}). **I built this up fresh from a raw disassembly of
`FUN_0002214a` (`0x2214a`-`0x22207`, `0x228e0`-`0x2293e`) without first checking whether this exact
pattern was already on record — it was.** `.claude/agent-memory/firmware-codepath-tracer/
reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered.md` (2026-08-07) already
retracted the "16-phase duty cycle" reading of this exact `andi 0xNNN,r25` idiom on a DIFFERENT site,
correctly identifying `r25` as a per-STATE one-hot test, not a tick-phase divider. **I re-derived the
same shape independently on the NEW `0xD30` site before reading that memory, and self-caught it only
because I went looking for corroboration — I did not initially know the retraction existed.** ⇒ **See
`feedback_check_own_memory_before_retracing_v850_state_mask_pattern.md` for the actionable lesson.**

**Resolved: the whole chain (`gp-0x6ac0` filter, `gp-0x4f64` writer, governor clamp) is LIVE during
ordinary driving, not frozen.** `docs/LEDGER-V38-TO-V84.md` (line ~315) + two independent prior-tracer
memories converge: state 4 fires ~0% while driving (0/123,277 and 8/92,826-all-in-PARK, two routes),
state 10 = 0.0000% (V70 flown probe), but **"the standing measurement is state is a constant 5 while
driving"** — and state 5 is a member of EVERY mask on this chain. States 4/10 are rare, brief
transitional sub-states (per `analysis-2020accord/.claude/agent-memory/firmware-codepath-tracer/
reference_accord_state4_ratchet_and_gp67fa_state_graph.md`'s full state graph — `5->4`, `10->4` on
cheap-to-flip runtime flags), not the resting state.

## GATE 1 census on gp-0x4f64 itself — 11 accesses, fully adjudicated
`search_instructions` on `-0x4f64` finds 11 (3 writers, all in `FUN_0007b022`'s three mode branches; 8
readers: `FUN_0004503c`, `FUN_00043e44`, `FUN_00042af8`, `FUN_0006e09a`, `FUN_0006e140`, plus
`FUN_0007b022` itself ×3). **Cross-checked with a corrected Python LE scan** (my first attempt used the
wrong target — `ld.hu`/`ld.w` encode `hw2=disp|1`, the documented trap; the corrected scan checking BOTH
`0xB09C` and `0xB09D` recovers all 11 plus 6 raw coincidences, **every one individually adjudicated and
rejected**: 2 are bytes inside an unrelated `mov 0xbb09c,r7` 32-bit immediate and a `jarl` call-target
encoding (confirmed via `disassemble_function`); 2 are `st.b r7,-0x4f64,r18` — same displacement NUMBER,
**base register r18, not gp** (confirmed via `disassemble_bytes` dry-run on the actual bytes — a
sequence of `st.b r7,DISP,r18` at several unrelated displacements, clearly a table-driven bulk-write
routine, not a gp-0x4f64 access); 2 are in `[0xC5000,0xD0000)` calibration data, never disassembled as
code (very likely noise, not individually confirmed).

**NEW consumer, not previously on record: `FUN_0006e09a`/`FUN_0006e140`.** Both are small state-step
handlers (`void f(byte param_1)`, `if(param_1<2){if(param_1==0){...init...}else{...}}`), reachable via
NO direct caller found statically (`get_function_callers` empty both — consistent with dispatch through
an unresolved function-pointer/state table, NOT confirmed dead). On a dwell/settle transition
(`(sVar1-sVar2) < cal(0xC6C22)=25`), both execute:
```c
gp-0x6b98 = gp-0x4f64 * cal(0xC6C3C);   // cal(0xC6C3C) = 1, VERIFIED stock
gp-0x4ce2 = gp-0x4f64 * cal(0xC6C3C);   // shadow, same
```
`gp-0x6b98` is the final merged motor command reaching FOC (established elsewhere in the kit). Because
the stock multiplier is exactly 1, this is effectively `gp-0x6b98 := gp-0x4f64` directly during whatever
state this handles — **bypassing the entire aggregator -> governor-clamp -> slew pipeline.** Reachability
during ordinary driving NOT established — the init branches call `FUN_0005a97c`/`FUN_0006d026`/
`FUN_00062c42`/six `FUN_0005a9d2` calls, reading like a resolver/FOC bring-up sequence, not obviously
ordinary-drive code. **Flag for GATE 1 on any future `gp-0x4f64` edit — the dispatch table indexing these
two functions has not been found.**

`FUN_00043e44` reads `gp-0x4f64` as one of ~7 additive terms feeding a composite anomaly score that
triggers DTC 0x3f1b at threshold 128 (`FUN_000462e6`) — already partially on record
(`reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved.md`). A bank-A edit
changes what this term contributes but the term's own reachable range (0-5325 both before/after a
flatten) is unchanged — flattening only removes the low end.

## V41 (the flatten this cap table has already been tested with) — force independently proven
`analysis-2020accord/build_v41_tva.py` + `docs/HANDOFF-2026-07-20-v41-ratecap-flat.md` +
`docs/HANDOFF-2026-07-20-v42-state4-ratchet.md`: V41 = exactly this flatten (Y row -> flat 5325, slopes
-> 0, both mirrors) plus an unrelated LKAS-lane slew removal (`0xC6194`). Flown, verbatim: *"boots and
drives cleanly, fixed neither symptom"* — for the OLD several-Hz hard-turn ratchet (later root-caused
elsewhere, the state-4 governor substitution, V42) and a ~20Hz vibration, **NOT** the operator's later
"highway grind #3 -> slow ratchet" claim, which didn't exist as a symptom description yet.

**"Prove force, do not infer it" — done two independent ways, neither reusing the build script's own
printed claims:**
1. **Fresh SHA256 of both artifacts on disk** matches the handoff's recorded values exactly (RWD
   `77fbd6aa...`, plain image `194b0903...`).
2. **Fresh, independent Python re-read of the plain image's cap table** (not the build script's
   printout): `Y=[5325]*5` both copies, slopes `[0,0,0,0]` both copies — confirmed flattened.
3. **Attempted a from-scratch cipher decode of the raw RWD** (the documented TVA cipher
   `((c^0xBF)^0x10)-0x9E`, applied with no dependency on `encode_eps.py`): calibrated a 124-byte header
   (unique match against a known version-string byte out of 4096 candidates tried) and it decodes
   correctly for ~65KB of the payload, but the RWD format has additional internal block structure past
   that point a flat header+contiguous model doesn't capture (692,463/970,752 bytes mismatch beyond
   offset ~0x25FCB) — **reported as a PARTIAL result, not used as proof.** The hash match + independent
   plain-image re-read above is what actually stands behind the force-of-proof claim.

## Related
[[reference_accord_rectifier_envelope_and_amplitude_bound]] -- the abs()-as-demodulator mechanism and
the angular-amplitude arithmetic this filter's corner feeds into.
[[feedback_check_own_memory_before_retracing_v850_state_mask_pattern]] -- the method lesson from the
state-mask re-derivation above.
