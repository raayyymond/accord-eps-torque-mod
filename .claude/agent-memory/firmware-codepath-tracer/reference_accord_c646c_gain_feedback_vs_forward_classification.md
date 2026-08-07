---
name: reference_accord_c646c_gain_feedback_vs_forward_classification
description: Definitive 6-reader enumeration of gain cal 0xC646C (tp+0x746c, the 4x LKAS authority gain) with FORWARD/FEEDBACK classification per site. Round 6 (2026-08-07) sharpens the verdict: only FUN_00036682 (reader #5) has a proven path to gp-0x6b98 (slow 0.93Hz-corner IIR, alpha=6/1024); FUN_00036828 (#6) reaches it only indirectly (dead-band modulation + uncertain DTC-0x23 threshold); FUN_0002b62c (#3) and FUN_0002c478 (#4) do NOT reach the motor command at all (#3 terminates in a private 2-function mode-debounce loop + diagnostics, #4's output gp-0x6b10 is proven dead 4 independent times). Also resolves a real "two different V76 images on disk" naming collision -- V78/V80 descend from _v76_v38base_relu_damper_plain_image.bin (V38 base, pre-dates the V57 decouple), NOT the earlier _v76_gate_fb_arm5244_gateprobe one.
metadata:
  type: reference
---

**Context**: team-lead hypothesis -- if `0xC646C` (raised 891->3564, 4x, in V38+ for LKAS authority) is
read anywhere OTHER than the CAN-LKAS-setpoint path, that read multiplies loop gain in a feedback path
and is a candidate root cause for the ~21Hz vibration. Investigated 2026-07-26 on `_vfourframe_plain_image.bin`
(V38 cal + passive telemetry cave; core arbitration/assist code identical to stock `code.bin`).

## Definitive reader enumeration (raw Python byte scan, whole 1MB image, BOTH tp-relative encodings)
`tp = r5` (NOT r4/gp -- confirmed by hand-decoding `ld.h 0x746c[tp],r7` bytes `25 3f 6c 74` at `0x2a1ee`:
`reg1=hw1&0x1F=5`). Scanned both the 4-byte disp16 form (reg1=5) and the 6-byte V850E2 extended-disp23
form (reg1=5, reg2==0 escape) per [[v850e2-extended-disp23-encoding-solved]]. Also ran an LE32 literal
scan for the absolute address `0xC646C` (pointer-table use). Result: **exactly 6 static references, ALL
4-byte disp16 loads, ZERO 6-byte extended-form hits, ZERO LE32 literal hits, ZERO stores (it's a pure ROM
constant).** This matches CLAUDE.md's already-corrected "6 readers" figure exactly (independently
reproduced, not just inherited) and closes the enumeration question definitively -- no further form
exists to find.

| # | Addr | Function | Bytes | Ghidra sees it? |
|---|---|---|---|---|
| 1 | `0x2a1ee` | `FUN_00028ea6` (live arbitration) | `ld.h 0x746c[tp],r7` | yes (`search_instructions`) |
| 2 | `0x2a904` | none (unclaimed gap `0x2a507-0x2a93a`) | `ld.h 0x746c[tp],r6` | **NO** -- `search_instructions` misses it (5th recorded occurrence of this undercount) |
| 3 | `0x2b656` | `FUN_0002b62c` (called by `FUN_00022ca0`, assist-shaping task) | `ld.hu 0x746c[tp],r18` | yes |
| 4 | `0x2c488` | `FUN_0002c478` (called by `FUN_0002214a`, main 1kHz task) | `ld.hu 0x746c[tp],r13` | yes |
| 5 | `0x36686` | `FUN_00036682` (called directly by aggregator `FUN_0003aa2c`) | `ld.hu 0x746c[tp],r13` | yes |
| 6 | `0x3684a` | `FUN_00036828` (called by `FUN_00022ca0`) | `ld.hu 0x746c[tp],r6` | yes |

No float mirror / no lockstep monitor reads this cal (re-confirmed this session as a corollary of the
enumeration itself: neither `FUN_00043e44` nor `FUN_00042af8`, the two hard-shutdown monitors, appear
among the 6 sites). Matches the prior "GAIN monitor-INDEPENDENT" note, now independently reproduced.

## Per-site classification

**#1 `0x2a1ee` -- FORWARD, VERIFIED.** Full disasm read: `(Q10-IIR-blended, deadband-gated
LKAS-setpoint-descended term) * GAIN * POLARITY(gp-0x6752) >>15`, clamp `+/-0xC61B4`, feeds `gp-0x6b3c`
(arb command) -> `limit_and_pack` -> mixer -> `gp-0x6b4c` -> aggregator. This is the intended use.
Matches `eps_lkas_chain_model.py`'s already-VERIFIED `steer_torque_arbitration()`.

**#2 `0x2a904` -- DEAD CODE, high confidence.** Structurally a near-twin of #1 (same GAIN/POLARITY/CLAMP
idiom, same `gp-0x3d3c` IIR carrier, same `gp-0x6806` STEER_CONTROL_ACTIVE gate) but writes a DIFFERENT
cell `gp-0x6b38` and additionally touches `gp-0x69b0` (authority ramp) and `gp-0x6b2c`. Sits in an
UNCLAIMED gap `[0x2a507,0x2a93a)` between two functions (`FUN_0002a30e`, `FUN_0002a93a`) independently
established dead (0 callers) in a prior session -- `get_xrefs_to` returns zero on 5 probe points across
the whole gap this session too. Entered via a `callt 0x20` register-save-helper idiom (a genuine function
prologue Ghidra's auto-analysis didn't bound), ends in a proper `jmp lp` return -- it's real, structured
code, just never called from anywhere found. Residual uncertainty: a caller sitting in still-unanalyzed
bytes elsewhere can't be 100% excluded by a pure xref null, but two independent sessions/methods agree.

**#3 `0x2b656` -- FEEDBACK, medium-high confidence.** `FUN_0002b62c` reads ZERO CAN/LKAS-setpoint-lineage
signals anywhere in the whole function (checked its full decompile) -- its inputs are exclusively
`gp-0x6a5e`/`gp-0x6a62`-style torque voters, `gp-0x6a02`/`gp-0x6a52`/`gp-0x6a56` (rate), `gp-0x4f60`,
mode/state bytes. GAIN is read as `sVar10`, multiplied by POLARITY and cal `0xC6428`, MODE-GATED
(`gp-0x677d` in {2,3}), blended via a slew-toward selector against a per-mode table constant, output to
`gp-0x6af0` -- confirmed LIVE (2 real readers: `FUN_0002c246` and `FUN_0004e96a`, both called from the
main 1kHz task `FUN_0002214a`). **Did not hand-verify the exact SSA chain of the multiplicand at the
point of use** (Ghidra's decompiler reuses variable names like `uVar23` across the function) -- classified
FEEDBACK by elimination (no setpoint lineage exists in the function at all) + structural context, not by
a fully walked instruction-level derivation. Flagged OPEN for anyone who wants to close it further.

**#4 `0x2c488` -- FEEDBACK-SHAPED INPUT, but DEAD OUTPUT (triple-corroborated). Important nuance, don't
cite this as a live carrier.** `FUN_0002c478` (called unconditionally every cycle from the main 1kHz task
`FUN_0002214a`) computes `iVar21 = (gp-0x4f60_RAW_SENSOR * GAIN) >> 15` (direct raw-sensor gain
application) PLUS `iVar13 = POLARITY * clamp(gp-0x6b98[DELIVERED MOTOR COMMAND] - gp-0x6b12[self-state],
+/-0x4800)` -- i.e. it also reads the delivered command's own rate of change. Doubly feedback-shaped. BUT:
its immediate output `gp-0x6b10` (3 stores, `0x2c4c6`/`0x2c764`/`0x2c7c2`) and its later state-machine
outputs `gp-0x696c`, `gp-0x696a`, `gp-0x678b`, `gp-0x678d` are **PROVEN WRITE-ONLY** by three independent
methods this session: (1) whole-image disp16 byte scan, (2) `search_instructions` (decodes both
encodings but is blind outside analyzed functions), (3) whole-image 6-byte extended-disp23 byte scan.
Zero loads found by any method. The function keeps a self-referential feedback loop through `gp-0x6b12`
(read back next cycle) so it still executes every tick, but as far as could be determined this session,
nothing outside the function consumes its results -- it does not appear to close a loop back into the
motor command today. Plausible explanation: a diagnostic/telemetry producer (UDS RAM-read target), matching
the pattern of other diagnostic-only raw-`gp-0x4f60` readers already on record (`0x2EC66`/`0x2ECBA` in the
V52C carrier-surface work).

**#5 `0x36686` -- FEEDBACK, VERIFIED, full chain to the motor command.** `FUN_00036682` (decompiled in
full): `sVar15 = gp-0x6b48 + POLARITY*((gp-0x4f60_RAW_SENSOR * GAIN)>>15) - gp-0x6b46[prior output]`.
This error/delta term drives a rate-limited/hysteretic tracker (the "self-filters at fc~0.94Hz, alpha=
6/1024" EMA already on record) whose output IS `gp-0x6b46`, which the function returns. Confirmed caller:
`FUN_0003aa2c` (the motor-torque-demand aggregator) calls this directly and sums the return value
(`add r14,r10` @`0x3ace6` per the golden model) into `gp-0x6b94` -> governor -> **`gp-0x6b98`, the
delivered motor command.** This is the cleanest, fully-instruction-verified smoking gun: the raw physical
torsion-bar sensor, scaled by the SAME 4x gain applied to the LKAS setpoint, re-enters the signal that
drives the motor that moves the sensor. Textbook loop-gain multiplication.

**#6 `0x3684a` -- FEEDBACK, VERIFIED, chains directly into #5.** `FUN_00036828` (decompiled in full,
called from the ~100Hz assist-shaping task `FUN_00022ca0`): `sVar24 = ((gp-0x4f60_RAW_SENSOR *
GAIN)>>15) + clamp(gp-0x6b48,+/-3072)*POLARITY`. Feeds a DTC-0x23 rate-fault check AND produces
`gp-0x6b44`, which is READ DIRECTLY by `FUN_00036682` (#5) to scale its hysteresis-band Q15 term. #5 and
#6 are a matched companion pair sharing `gp-0x6b48`/`gp-0x6b44` state, and BOTH independently apply
GAIN*raw-sensor -- i.e. the 4x gets applied to the same physical signal TWICE in two sibling functions.
⚠ SAFETY NOTE for any fix: if #5/#6 are ever split from #1/#2/#3/#4 by pointing them at a new cal cell,
they must be changed TOGETHER (matched), since they share state and a monitor-asymmetry brick (V27-class)
is the standing risk pattern in this kit whenever paired/shadow computations diverge.

## Why is the "LKAS authority gain" read inside the assist shaper at all? (team-lead's Q3)
Evidence-grounded answer: `0xC646C` isn't exclusively an LKAS-authority cal -- it functions as the
firmware's one shared "sensor-to-command-domain" Q15 scale factor, reused across at least 4 live call
sites spanning 3 different subsystems (live arbitration, the ~100Hz assist-shaping task twice, the
aggregator-called filter). The LKAS arbitration function (#1) is just ONE consumer, not the exclusive
owner. Raising it for "4x LKAS authority" silently also raised the scale on every other consumer,
including the raw-sensor feedback lanes.

## Verdict on the team-lead's hypothesis: YES, evidenced
The 4x gain is inside at least one feedback loop, with the cleanest evidence at #5+#6
(`FUN_00036682`/`FUN_00036828`): raw torsion-bar sensor -> GAIN(4x) -> aggregator -> governor -> delivered
motor command, fully traced at the instruction level. #3 is FEEDBACK by elimination (medium-high
confidence, exact multiplicand chain not fully hand-walked). #4 reads feedback-shaped inputs but its own
output is proven dead this session -- don't cite it as a live contributor. #1 is the intended FORWARD use,
confirmed correct as-is. #2 is dead code either way.

## Tension worth flagging, not resolved this session
This is an ALWAYS-ON base-assist loop (#5/#6 run regardless of LKAS engagement -- `FUN_0003aa2c` and
`FUN_00022ca0` are unconditional). [[accord-vibration-requires-lkas-engaged]] establishes the on-car
vibration needs OP actively commanding (9200x less 21Hz power disengaged). A pure "always-on feedback gain
increase" doesn't by itself predict engagement-dependence. Plausible synthesis (NOT verified): the 4x gain
here thins the stability margin of the always-on base-assist mode generally (raises its Q), but doesn't
push it into a visible limit cycle alone -- active LKAS commanding (itself running through the SAME 4x
arbitration gain into the SAME aggregator) supplies the extra excitation that tips an already-thin-margin
mode into audible/visible oscillation. This reconciles both findings but is inference, not evidence --
flag for whoever picks this up next.

## Split-the-cal feasibility (team-lead's Q4)
`0xC646C` is a SINGLE shared ROM cal word -- confirmed by the enumeration (all 6 refs use the identical
tp+0x746c literal). Per-site different values are NOT achievable as pure calibration-table edits, because
that would require the READING INSTRUCTION's displacement operand to change (an instruction-byte edit),
not just a cal-table byte. Minimal shape of a real split: allocate a new cal cell nearby in the already-
programmed `0xC6xxx` block (spot-checked `0xC6460-0xC648F` this session -- densely packed, no obvious free
run; a real free-byte search is a next step, not done here), holding the stock 1x value (891), then
retarget the `hw2` displacement field (2 bytes each, no new instructions/branches/cave) at #3/#5/#6 (and
optionally #4 for hygiene even though its output is dead) from `0x746c`/`0x746d` to the new offset. This
is far smaller than any code cave in this kit's history (no trampoline, no new RAM state, no CALLT) but it
is NOT strictly "cal-only" in this kit's usual sense -- it touches ~3-4 instruction bytes in the executable
region, which means a CRC update for the containing MAIN block. Recommend presenting it to the operator
explicitly as "smallest code-edit class available, not a cal-only build."

See [[reference_accord_no_speed_gain_in_baseassist_feedback_loop]] (already had #5/#6's mechanism at the
single-lane level, this entry supersedes it on completeness -- that one only listed FUN_00036682, missed
that FUN_00036828/#6 is a live matched twin and missed #2/#3/#4 entirely).

## Re-verification on `code.bin` (2026-07-26, same session, second pass)
Team-lead pointed out `code.bin` (stock) is now fully analyzed (2086 functions vs the fourframe image's
1680) and is the better program for code-structure work; the fourframe image should only be used to read
calibration VALUES as-flashed. Re-ran everything on `code.bin` -- **every finding reproduces exactly, no
changes**:
- Same 6 readers, same addresses, zero 6-byte extended hits, code byte-identical at all 6 sites between
  stock and on-car.
- `0xC646C`: **stock=891, on-car(V38/FOURFRAME)=3564, ratio=4.0 exactly** (matches team-lead's
  independently-verified ground truth). NEW: the paired output clamp `0xC61B4` (+ distribute-stage sibling
  `0xC61B2`) was ALSO scaled 512->2048 (4x) in lockstep -- the operator widened the clamp alongside the
  gain at reader #1 (FORWARD/arbitration site) to get genuine 4x range, not just more saturation.
- **#2 (`0x2a904`) dead-code verdict RE-CONFIRMED on the more-complete analysis** -- `get_function_by_address`
  /`get_xrefs_to`/`get_function_callers` all still null on `code.bin` (183429 analyzed instructions vs
  171150 before). Since the MORE thoroughly analyzed program still finds nothing, the earlier "unanalyzed
  caller blind spot" caveat is now meaningfully weaker.
## Round 3 (2026-07-26, same session) -- tempering accepted, saturation checked empirically, (A)/(B) closed

**Tempering ACCEPTED, independently verified.** `tp+0x73d2` read directly = 14 (Q10 IIR coefficient on
`FUN_00036682`'s output -> fc~=2.18Hz at the 1kHz task -> -19.7dB at 21Hz). The pre-filter error term is
ALSO clamped to `iVar8=clamp(sVar15,+/-0x200)` before entering that IIR (confirmed in my own decompile,
just hadn't computed its significance). **Verdict revised: #5/#6 is a real, fully-traced feedback path
into `gp-0x6b98`, but it is SLOW (2.18Hz corner) and SMALL-AUTHORITY (+/-512 of the aggregator's +/-10240,
~5%) -- do not call it "the smoking gun" for 21Hz specifically.** It's real, just not that.

**Saturation/limit-cycle question -- quantitative, checked against REAL telemetry, comes back "no" for
21Hz.** Team-lead noted the ±512 pre-filter clamp is a saturating nonlinearity whose trigger threshold on
`|gp-0x4f60|` shifts from ~18829 (stock 891, near the ±25600 rail, effectively unreachable) to ~4707 (4x
3564, "ordinary steering torque") -- classic describing-function limit-cycle setup. Independently
rederived the same numbers from `|gp-0x4f60| >= 16777216/GAIN`: **18830 stock / 4707 at 4x**, matches. In
CAN units (`STEER_TORQUE_SENSOR = -(gp-0x4f60*125/128)`): |tbar|>=18388 stock / >=4597 at 4x. **Decoded
raw CAN 399 from two on-car datasets that both exhibit the CONFIRMED 21Hz vibration** -- route 13
(FOURFRAME, hands-off parking lot, `analysis-2020accord/rlogs/75604b0a432fdc89_00000013--f484e75b00--*`,
8102 active-LKAS frames) and the b9 route (`../Archive/accord-eps-torque-mod-old/analysis-2020accord/
rlogs/807a3c21c9f405e8_000000b9--6a1dd9d6dc--*`, 12 segments, 54445 active-LKAS frames, broader speed
range). **Combined 62,547 active-LKAS frames: `|tbar| >= 4597` triggers ZERO times on either route** (max
observed 3063/route13, 3622/b9 -- ~79% of threshold at absolute peak, p99 ~66%). **Conclusion: the
saturation threshold genuinely shifted 4x and is a real headroom regression, but it does not appear to be
the mechanism sustaining the specific 21Hz vibration -- it never fires in either dataset where that
vibration was directly measured.** Caveat: doesn't rule out rare inter-sample transients or untested
driving conditions (curb strikes, hard maneuvers).

**Free calibration word (task A) -- FOUND, high confidence: `0xC6CD0` (tp+0x7CD0).** ⚠ Caught my own
off-by-0x1000 mid-search: `tp+0x6000` = `0xC5000` (the risky model-coeff block), NOT the "0xC6000 block"
team-lead meant -- the correct window is `tp+0x7000..0x7FFF`. After fixing: found 96 `movea <disp>,tp,rX`
table bases in that window (encoding: op=0x31, reg1=5, hw2=full 16-bit disp, ground-truthed against a
known Ghidra-decoded instance first) + unioned every disp16/extended-disp23 displacement-READ byte (1934
read). One region is unambiguous regardless of table-span heuristics because it's literal unprogrammed
flash: **`0xC6CD0-0xC6FE3` = ~786 contiguous `0xFF` bytes**, zero disp16/disp23/LE32-literal references
anywhere in the image (triple-checked). Tail ~130 bytes holds a version string (`C30_801_D_03_00_T04`) +
footer magic (`affedead...beef...`) before the CRC at `0xC6FFC` -- stay clear of that. `0xC6CD0` sits dead
center of the free run. No `build_v*_tva.py` references this region.

**LKAS-only upstream gain (task B) -- NEGATIVE, well-justified.** Full decompile of `FUN_00028ea6`
(1309-line C, the whole arbitration function). Everything between the CAN setpoint write and `0x2a1ee` is
one of three kinds, none usable as a "raise this instead" substitute: (1) 8 mode-indexed LERP pointer
arrays (`0xCB844`/`0xCBA74`/`0xCB924`/`0xC9A88`/`0xCB7D4`/`0xCBB54`/`0xCBC34`/`0xCBAE4`) are CLAMP/LIMIT
curves (max-magnitude ceilings), not multiplicative gains -- raising a ceiling doesn't add torque-per-CAN-
count; (2) the Q10 IIR blend coefficients (`tp+0x73ec`/`0x73ee`) feeding the shared `gp-0x3d3c` IIR are a
two-tap filter blend, not a free scalar, and `gp-0x3d3c` is shared with other consumers, not exclusive;
(3) the other term summed before the gain multiply (`iVar28`) traces through a large engage-state dispatch
to `gp-0x69b0` (the AUTHORITY RAMP, confirmed runtime state) or literal/`gp-0x6b2c`-sourced values
depending on substate -- not a static cal either. **`0x746c` really is the single Q15 domain-conversion
gain stage for the whole LKAS arbitration output; no substitute exists.**

**Net recommendation (supersedes my round-1/round-2 split-feasibility scoping): retarget ONLY `0x2a1ee`,
not the 3 feedback sites.** Write 3564 to the new cell `0xC6CD0`; revert `0xC646C` to stock 891; change
`0x2a1ee`'s `ld.h` displacement field from `0x746c` to `0x7cd0` (hw2 bytes `6c 74`->`d0 7c`, 2 bytes, no
new instructions, no cave); leave `0x2a904`(dead)/`0x2b656`/`0x2c488`/`0x36686`/`0x3684a` untouched -- they
automatically revert to stock behavior since `0xC646C` goes back to 891. Recompute the `0xC6FFC` block CRC.
This is SMALLER than my original fallback (1 retargeted site instead of 3) for the identical net effect.

**Consequence for the 21Hz search**: given the tempering + the saturation "no", the 4x-gain-in-a-feedback-
loop finding is real but is probably NOT the 21Hz driver. The `engagement-gated-lanes` teammate's parallel
`FUN_0003a382`/`gp-0x6ad4` thread (unfiltered, engagement-coupled) remains the stronger candidate.

## ⚠ Open discrepancy (2026-07-28, lane-inventory session) — `tp+0x73d2` re-read as 6, not 14

Re-derived independently while inventorying every lane into `gp-0x6b98` (see
[[reference_accord_gp6b98_aggregator_full_lane_inventory]]). Fresh `read_memory` on `code.bin` at `0xC63D2`
(=`tp+0x73d2`) returns **6** (bytes `06 00`), not 14 as recorded in "Round 3" above. Cross-checked 3 ways
this session, all agreeing on 6: (1) direct 2-byte read at `0xC63D2`; (2) a wider 16-byte context read
`0xC63C8..0xC63D7` showing the surrounding small-constant cluster `10,719,0,1024,5,6,31,98` — no
off-by-N alignment artifact; (3) `search_instructions` on `0x73d2` independently locates the sole
reader `0x367fa: ld.hu 0x73d2,tp,r14` inside `FUN_00036682`, confirming the displacement itself, not just
my arithmetic on `tp`. Did not identify the source of the "14" figure — possibly a different program
snapshot, a transcription slip, or an address 1-2 cells off that I haven't checked. **Not resolving this
here — flagging for whoever next touches this cal.** If 6 is correct, `FUN_00036682`'s IIR is slower than
recorded (α=6/1024=0.00586, fc≈0.93Hz, ≈-26.6dB at 21Hz — an even weaker 21Hz carrier than "Round 3"
already concluded, so the qualitative verdict "small-authority, not the smoking gun" is unaffected either
way, only the exact dB number changes).

- **Float-mirror question CLOSED with positive evidence.** Diffed the full `0xC0000-0xC8000` cal block
  (767 differing bytes, stock vs on-car). The specific cells team-lead flagged as float-mirror candidates
  from that diff (`0xC659A/9E`, `0xC65AE/B2`, `0xC65C6/CA/CE`, `0xC674F-0xC676D`) are upper/lower halves of
  3 float words at `0xC6598`/`0xC65AC`/`0xC65C4` -- and `0xC65C4/C8/CC`=4.0 is the **already-documented
  V30/V31 soft-EME boost-floor float mirror** (paired with int `0xC6768/6A/6C`=4096, per the CLAUDE.md V31
  boost-floor record) -- a pre-existing, unrelated matched pair carried into V38, NOT a gain mirror. None
  of these addresses appears in any of the 6 gain-readers' decompiled code (checked every tp-relative
  literal all 6 functions touch: `0xC61Bx`, `0xC61A2-A8`, `0xC71A0-B0`, `0xC72xx-C74xx`, `0xC7332`,
  `0xC747E`, `0xC7286` -- a disjoint range from `0xC65xx`/`0xC674x`). Combined with "neither hard-shutdown
  monitor is among the 6 readers" from the first pass, this closes the float-mirror question positively,
  not just by absence.

## Round 4 (2026-07-29, V57-candidate re-verification for team-lead) -- independent re-derivation, two corrections

Re-ran the enumeration completely from scratch (fresh Python scanner, not copy-pasted from this file) on
`code.bin`, plus GhidraMCP corroboration on every hit. **Reproduced exactly: 6 readers, same addresses,
zero stores, zero 6-byte extended hits, zero LE32 hits.** `0x2A904` is now even more solidly dead --
on the fully-analyzed 2086-function `code.bin`, `get_assembly_context` returns "No instruction at
address" (not just "no caller" as before). Edit-site bytes at `0x2A1EE` read directly: `25 3f 6c 74`,
hand-decoded to `ld.h 0x746c[tp],r7` -- confirms the retarget is `6c 74`->`d0 7c` (2 bytes) exactly.
`0xC6CD0` re-scanned fresh (disp16+disp23+LE32, all zero) and byte-dumped: the preceding LERP table at
`0xC6C90` (header=4, ends at exactly `0xC6CA4`) is followed by solid `0xFF` through `0xC6FEF`, metadata
resumes `0xC6FF0` -- `0xC6CD0` sits mid-desert. New float-mirror check (different method than the Round-3
cal-block-diff): swept for ANY `ld.w`/`st.w` (32-bit) tp-relative access with disp in `[0x7440,0x74A0)`
(brackets `0xC646C` generously) -- zero hits, corroborating no float twin exists near the gain word.

**Two corrections to the record, both found by decompiling #5/#6 fresh rather than trusting the summary:**

1. **`FUN_00036682` (#5) is confirmed NOT a plain EMA, and the exact z-domain math was re-derived.** The
   decompile shows `error = x[n] - y[n-1]` (subtracting the function's OWN prior output) feeding the EMA,
   which makes the recursion `accum += ((clamp(error,±512))*1024 - accum)*alpha>>10`, `y[n]=accum>>10`.
   Substituting through: `y[n] ≈ y[n-1]*(1-2·alpha) + alpha*x[n]` -- DC gain **1/2**, pole at `1-2·alpha`
   (not `1-alpha`), i.e. genuinely double the naive EMA bandwidth. Despite this, `|H(21Hz)|` computed
   exactly from the real z-domain transfer `a/(1-(1-2a)z⁻¹)` comes out to **0.0446**, vs the simple
   single-pole approximation's 0.0444 used in prior rounds -- a 0.4% difference, immaterial, because at
   21Hz (≫ the ~1-2Hz cutoff either model implies) `|H(f)| ≈ alpha·fs/(2πf)` regardless of exact pole
   placement. **The existing -27.1dB / 0.0048-contribution figure is CONFIRMED, now by exact rather than
   approximate math.** Also newly noted: a hysteresis/dead-band stage sits between the raw error and the
   ±512 clamp (a slew-toward-selector using `tp+0x719c`/`tp+0x71a6` as half-band thresholds) -- a
   nonlinearity this linear estimate doesn't capture, which can only reduce real-world 21Hz throughput
   further. 0.0048 is therefore an upper bound, not a point estimate.

2. **Correction to the "#5/#6 matched pair, BOTH independently apply GAIN×raw-sensor to the motor"
   framing.** Confirmed `FUN_00036828` (#6) does independently compute `(gp-0x4f60_RAW*GAIN)>>15`, but its
   own output (`gp-0x6b44`/`gp-0x6b40`/`gp-0x6b42`/`gp-0x37a0`, plus a DTC-0x23 rate check) does **not**
   additively enter the aggregator on its own path. `gp-0x6b44` is read back **inside #5** to size
   `sVar12`, which widens/narrows #5's hysteresis dead-band (`sVar9=(sVar12>>1)+sVar15`,
   `sVar10=sVar15-(sVar12>>1)`) -- i.e. #6 *modulates #5's nonlinearity*, it is not a second independent
   additive summand into `gp-0x6b98`. True that both apply GAIN; **false** that both have independent
   additive paths to the motor. #6's own 21Hz contribution is second-order (a dead-band-width perturbation,
   not a direct signal path) and wasn't quantified via a describing-function treatment -- conservatively
   bound the combined #5+#6 contribution at ~2x the #5-only figure (~4.4% of measured transfer, ~0.28dB),
   almost certainly an overestimate.

**Net effect on the V57 recommendation: unchanged from Round 3 (build it as the correctness fix), now on
firmer footing** -- the loop-gain-at-21Hz question was reopened fresh (given `FUN_0003a382`'s elimination
by V56) rather than assumed still-moot, and independently re-closes on the same "too slow, too small, too
indirect" grounds via a different derivation path than before.

## Round 5 (2026-07-29, same session, follow-up) -- reader #3's GAIN-multiplicand is domain-mixed, not pure torque; one input's identity is a genuine open question shared with a parallel session

Team-lead followed up asking whether ANY reader touches the steering-ANGLE domain (operator's objection:
this kit has never mapped a position/return-to-center path, and the ECU DOES transmit `STEER_ANGLE` on CAN
`0x14A` bytes0-3 plus "a 10x finer rate copy" at `0x18F` bytes[2:4]). Ran full pcode dataflow traces
(`analyze_dataflow`, SSA-level, not manual register reading) on reader #3 (`0x2B656`, `FUN_0002b62c`).

**PROVEN (pcode-verified, 60-step forward trace from `0x2bbaa`):** `gp-0x6a56`'s SIGN (extracted via
negate+compare, `0x2bdfa-0x2be02`) multiplies an LERP-interpolated term (`0x2bf3e`), sums with another
interpolated term (`0x2c12c`), multiplies a third interpolated term to produce `r6` (`0x2c136-0x2c13e`).
`r6` is compared against `r13`=`gp-0x6a02` at `0x2c140`, and via a `cmovge`(`0x2c150`)+phi(`0x2c154`) this
selects `r10` -- **the exact value GAIN(`0xC646C`) multiplies at `0x2c1e0`** (a 3-way selector between a
fixed per-mode cal constant from table `0xC70E8` and `r6` itself). So reader #3's own GAIN-multiplicand
is NOT purely torque-domain -- its SELECTION depends on `gp-0x6a56` and `gp-0x6a02`.

**`gp-0x6a56` = MOTOR ELECTRICAL RATE, high confidence.** Traced producer `FUN_0003f776` (called from
`FUN_00022ca0`, same task as reader #3): `clamp(POLARITY*(gp-0x6abe*48*cal_0xC613A)>>15, ±12000)`.
`gp-0x6abe` is independently corroborated as "filtered MOTOR rate"/"motor electrical-rate raw" across 5
separate memory files (`reference_accord_fun34350_damping_term_live_and_gated.md`,
`reference_accord_foc_inner_current_loop_architecture.md`,
`reference_accord_fun41464_sign_filter_phase_response.md`, `reference_accord_post_governor_comp_add.md`,
`reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md`), all rooting in the same producer
`FUN_00041464`. This ALSO resolves an open item in `reference_accord_can_tx_399_427_bitmap.md`: that
memory's "`gp-0x6a56` is arbitration/setpoint-class, NOT a raw sensor" label (inferred from caller names)
is superseded -- `gp-0x6a56` is `FUN_0003f776`'s own clamp of the motor-rate signal `gp-0x6abe`, and it is
this exact cell that packs CAN 399 (`0x18F`) bytes 2:3 per that memory's byte map. Reconciles with the
team-lead's "10x finer rate copy" framing if that means motor/steering angular rate (proportional via the
fixed gear ratio), not literally the raw column-angle sensor.

**`gp-0x6a02` -- domain NOT CLOSED, shared open question with a parallel session.** Traced producer
`FUN_0003fc16` (called from confirmed-1kHz `FUN_0002214a`): `gp-0x6a02 = gp-0x69ca -
slew_limited_delta(cal 0xC733A, gp-0x69e0)`, gated on `gp-0x67fe∈{1,2}`, reset alongside `gp-0x69ca`/
`gp-0x69d4`/`gp-0x69de`/`gp-0x6bf0`/`gp-0x6bf4`/`gp-0x6bee`/`gp-0x6a10`/`gp-0x6a0a` in a shadow-lockstep
reset function (`FUN_0003e760`) on assist-substate re-init. The SAME producer also computes `gp-0x6a10 =
clamp(gp-0x6a02)` -- this is EXACTLY the "tracking error" signal a parallel teammate session (memory file
`reference_accord_aggregator_domain_audit_no_angle_lane_found.md`, same day, auditing the 11 direct
`gp-0x6b98` aggregator summands -- a different, non-overlapping consumer set from reader #3's `gp-0af0`)
flagged as "NOT closed... a real, not-ruled-out candidate for an angle/angle-rate tracking signal." I
pushed one level further: `gp-0x69ca`'s own producer is `FUN_0003bd7c` -- **the already-established EPS
assist-state-machine function that derives `gp-0x67fe` from `gp-0x6772`**
(`eps-gp67fe-trump-engaged-holding-substate.md`) -- via a call to `FUN_0003bd40` gated on a
sentinel-checked (`0x7FFF`) read at **`gp+0x6470`** (positive gp offset, same pattern as the known
variant-config byte at `gp+0x6409` in the CAN-427 bitmap). Did NOT decompile `FUN_0003bd40` or resolve what
`gp+0x6470` configures -- real gap, not closed. **Reading (not proven): this looks at least as plausibly
like an assist-state-machine/FOC-internal quantity (matching the shape of the unrelated `gp-0x6bda`/
return-centre chain the parallel session traced to state-transition-timing, NOT position) as a literal
steering-column-angle tracker.** One older memory fragment
(`reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass.md`) flatly labels `gp-0x6a02` "an
angle-domain signal" without its own producer trace -- may be right, may be a stale inference. Do not cite
either verdict as settled; the next step is decompiling `FUN_0003bd40` + the `gp+0x6470` config read.

**Driver-override gate, partial lead only.** Near the top of `FUN_0002b62c`, `bVar3`/`iVar45` are forced
false/zero if `gp-0x4f60 > 9216` OR voted quantity `gp-0x6a5e > 32000` OR `gp-0x67f4 != 1` -- a plausible
torque-threshold override. But this gates an EARLIER part of the function (a `tp-0x3d08`/`tp-0x3d0c`
ramp-rate tracker feeding later LERP interpolations that reach `r6`/`r21` above), not a direct gate on the
GAIN-multiply block itself (which is only mode-gated on `gp-0x677d∈{2,3}`). Not traced all the way through
-- flagged as a lead, not a closed finding. (The parallel session found NO such gate among the 11
aggregator summands, a negative-but-non-exhaustive result over a different function set.)

**Net effect on V57: unchanged** -- the retarget mechanics (2-byte edit, isolates forward path, reverts
#3-#6 to stock automatically) don't depend on resolving `gp-0x6a02`'s identity. What changes is reader #3's
characterization: not pure torque feedback, but torque-cal(`0xC6428`) blended with a selector gated by a
confirmed motor-rate signal and one signal of contested domain.

See [[reference_accord_aggregator_domain_audit_no_angle_lane_found]] (parallel, complementary scope) and
[[reference_accord_can_tx_399_427_bitmap]] (source of the `gp-0x6a56`/CAN-399 cross-reference, now
corrected).

## Round 6 (2026-08-07, V76/V78/V80 4x-blast-radius audit) -- fresh re-derivation, one reclassification, one build-identity finding

Re-ran the whole enumeration from scratch with an independently-written Python scanner (not copy-pasted)
plus fresh `decompile_function`/`get_assembly_context` calls, prompted by a team-lead question: V76/V78/V80
apply the 4x GAIN at `0xC646C` directly (reader #1's `ld.h` displacement stayed `0x746c`), instead of the
V62/68/74/75 family's decoupled `0xC6CD0` (reader #1 repointed to `0x7cd0`) -- so V76/V78/V80 4x every
reader, not just the forward one. **All 6 static readers, same addresses, reproduced exactly**
(`0x2a1ee`/`0x2a904`(dead)/`0x2b656`/`0x2c488`/`0x36686`/`0x3684a`); zero stores, zero 6-byte extended-disp23
hits, zero LE32-pointer hits, confirmed by a fresh whole-image LE16 scan whose "extra" 6 raw hits
(`0xbabb9`,`0xbb085`,`0xbb119`,`0xbb224`,`0xbb24c`,`0xc8200`) are ASCII bytes inside a German diagnostic
string (`"...age 0xYYYY : Ein-/ausschalten der Endstufensignal..."`, confirmed via `read_memory` at
`0xbaba0` and `get_function_by_address`/`get_assembly_context` both returning no-instruction there) --
not a 6th encoding form.

**RECLASSIFICATION: reader #3 (`0x2b656`, `FUN_0002b62c`) does NOT reach the motor command -- downgrade
from "FEEDBACK, medium-high confidence" to "feedback-shaped input, LOCALLY CONTAINED, no path to torque."**
Its output `gp-0x6af0` has exactly 2 readers (fresh raw scan + decompile, both agree):
`FUN_0002c246` (`0x2c260`, `ld.h`) and `FUN_0004e96a` (`0x4ea6a`, `ld.h`) -- no third reader exists.
- `FUN_0004e96a`: a diagnostic/UDS-style response-buffer packer (writes a 0x38-byte (56-byte) fixed-length
  record at `*(int*)(param_1+8)`, right-shifts several `gp-0x6aXX` telemetry cells by 2 into it, gated on
  bit `0x20000` at `gp+0x6400`-ish). **`get_function_callers` finds ZERO static callers** -- almost
  certainly reached only via an indirect UDS/RDBI dispatch-table call the xref engine can't see (matches
  the kit's documented `a160_rdbi_handlerptr_live_dispatch` pattern). Either way: diagnostic telemetry
  only, not a control path.
- `FUN_0002c246`: reads `gp-0x6af0` at entry (`sVar7 = *(short*)(gp-0x6af0)`), clamps it against a
  mode-indexed table (`&DAT_000c7090`), and the ONLY other thing it touches that leaves the function is
  `gp-0x677d` (`st.b r14,-0x677d,gp` @`0x2c354`) -- a state-machine byte with a debounce-counter gate
  (`FUN_0001cba6()` fires only if a transition repeats `param_1` times running). **`gp-0x677d` has exactly
  2 static references in the WHOLE image** (confirmed by `search_instructions`): the write at `0x2c354`
  (this function) and the ONE read at `0x2c1b4` inside reader #3 itself (`FUN_0002b62c`), which is exactly
  the branch that decides whether GAIN is applied at all (`gp-0x677d ∈ {2,3}`). So the entire downstream
  effect of reader #3's GAIN application is: a private, self-contained, hysteretic 2-function mode-flag
  loop that never leaves this task-local pair except into diagnostics. **Not a torque-command closed loop
  at any point.** This corrects/sharpens the Round-1 "GAIN-multiplicand is domain-mixed... classified
  FEEDBACK by elimination" note -- FEEDBACK was right about the multiplicand's domain, wrong about where
  it goes.

**RECONFIRMED (2 independent fresh methods, not reused from prior rounds): reader #4's output `gp-0x6b10`
has ZERO readers anywhere in `code.bin`.** `search_instructions` on `0x6b10` returns exactly 3 matches, ALL
`st.h` (`0x2c4c6`,`0x2c764`,`0x2c7c2`, all inside `FUN_0002c478` itself) -- zero `ld.h`/`ld.hu`. A
freshly-written raw Python LE16 scanner (independent implementation, both parities, reg1==gp(4) filter)
reproduces the identical 3 hits, still zero loads. Fourth independent confirmation of this null across two
sessions now.

**Reader #5's IIR alpha RE-READ fresh: `tp+0x73d2` = `0xC63D2` = 6** (bytes `06 00`), confirming the
2026-07-28 correction over the original "Round 3" figure of 14 -- that 14 figure is now considered
superseded, not just disputed. alpha=6/1024=0.00586, corner ≈0.93Hz, ≈-26.6dB at 21Hz. `FUN_00036682`'s
caller reconfirmed as `FUN_0003aa2c` only (the aggregator) -- this remains the ONE reader with a proven
path to `gp-0x6b98`.

**New, unresolved thread: reader #6's DTC-0x23 threshold cal reads anomalously large.**
`FUN_00036828`'s tail does `if ((uint)*(ushort*)(tp+0x71a4) <= (uint)((!bVar2*uVar19)>>5)) FUN_00016de6(0x23,0,1,1);`
-- a fresh `read_memory` at `0xC71A4` (=tp+0x71a4) returns bytes `4e a0` = unsigned 0xA04E = 41038. The
RHS (`uVar19>>5`) is bounded well under 2048 given `uVar19` is a clamped 16-bit magnitude, so at face value
this branch is structurally unreachable -- i.e. the DTC-0x23 rate-fault this function guards may never
trip regardless of GAIN. **Not fully resolved this session** -- didn't rule out a misread cal-cluster
boundary (the neighbouring `0xC719C`/`0xC71A6` cells read as an odd pair too, `0xa04a`/`0x000e`, suggesting
possibly a LERP-table fragment rather than 3 independent scalars). Flagged for whoever next needs the
DTC-0x23 reachability question, not load-bearing for the GAIN blast-radius verdict either way.

**Physical meaning / Q-format, reconfirmed for ALL 6 sites, fresh disassembly at #1 this session:**
`0x2a1ee: ld.h 0x746c[tp],r7` -> `0x2a1f6: mulh r7,r13` (r13 = POLARITY(gp-0x6752, sign-extended byte) *
GAIN, plain 16x16 multiply, no shift yet) -> `0x2a1fe: mul r13,r11,r0` (r11 = combined_torque_term *
(POLARITY*GAIN)) -> `0x2a202: sar 0xf,r11` (Q15 descale) -> clamp against `tp+0x71b4`=`0xC61B4`=512
(stock, freshly read `00 02`). Readers #3-#6's decompiled C show the identical `(x * cal_0x746c) >> 0xf`
idiom directly. **GAIN is used ONLY as the multiplicand of a `mul`/`mulh` immediately followed by `sar
0xf`/`>>0xf` at every site** -- never as a divisor operand (no `div`/`divq` touches it anywhere), never as
a pointer/array offset. Confirms: dimensionless Q15 fixed-point scale, stock 891/32768=0.02719,
V76-family 3564/32768=0.10883, **3564 = 4*891 exactly** (integer arithmetic, and independently confirmed
by direct `read_memory` at both `0xC646C` and `0xC6CD0` across 5 on-disk images this session -- see below).

**Build-identity finding: there are TWO DIFFERENT on-disk images both named "V76."** Direct `read_memory`
byte reads (this session, 5 images):

| image | reader #1 disp | `0xC646C` | `0xC6CD0` |
|---|---|---|---|
| `stock/code.bin` | `0x746c` | 891 | 0xFFFF (free) |
| `_v62_plain_image.bin` | `0x7cd0` | 891 | 3564 |
| `_v76_gate_fb_arm5244_gateprobe_plain_image.bin` | `0x7cd0` | 891 | 3564 |
| `_v76_v38base_relu_damper_plain_image.bin` | **`0x746c`** | **3564** | 0xFFFF |
| `_v78_v76base_ey1_449_dose206_plain_image.bin` | `0x746c` | 3564 | 0xFFFF |
| `_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin` | `0x746c` | 3564 | 0xFFFF |

`_v76_gate_fb_arm5244_gateprobe_...` (built by `build_v76_tva.py`, base = `_v74_engagedcols_x0_12_addonly_
plain_image.bin`, a V57-and-later-descended lineage) is a DIFFERENT, EARLIER V76 candidate that still
carries the V57 decouple -- it is NOT the ancestor of V78/V80. `_v76_v38base_relu_damper_...` (built by
`build_v76_v38base_tva.py`, base = `_v38_plain_image.bin` directly, SHA pinned) is the one V78 and V80
actually descend from (`_v78_v76base_...`/`_v80_v79base_...` filenames name it), and its own header says
so explicitly: **"V76 RE-CUT ON A V38 BASE. Supersedes V76/V77/V77B"**, and separately notes the old
`.rwd` was renamed `SUPERSEDED-2026-08-07-BY-V76-V38BASE-...` -- i.e. the kit's own re-cut safety practice
(`accord-recut-overwrites-the-previous-plain-image.md`) was correctly followed for the `.rwd`, but the
STALE plain_image snapshot for the abandoned gateprobe V76 is still on disk under a filename that reads as
current. A careless glob for `_v76*plain_image.bin` returns both and does NOT sort the right one first --
confirmed this session as a near-miss (the first file this scan read WAS the stale one). **Anyone tracing
this lineage must anchor on `_v76_v38base_relu_damper_plain_image.bin` by exact name, not a `v76*` glob.**
This also makes the mechanism concrete: rebasing onto V38 (pre-dates V57, `SRC_SHA256` pinned in
`build_v76_v38base_tva.py`) is EXACTLY why V76-v38base/V78/V80 read `0xC646C` at reader #1 instead of the
decoupled `0xC6CD0` -- V38 predates the retarget, so its own `0xC646C` was already 3564 (carried from the
pre-V57 4x-gain lineage), and nothing in the V76-v38base/V78/V80 chain re-applies V57's 2-byte fix.

**Net effect on the operator's blast-radius question: SHARPENED, not overturned.** Of the 4 live
non-forward readers, only **#5 (`FUN_00036682`) has a proven path to `gp-0x6b98`** (direct additive,
through a slow 0.93Hz-corner IIR); **#6 (`FUN_00036828`) reaches it only indirectly** (modulates #5's
dead-band width) plus an uncertain DTC-0x23 threshold; **#3 (`FUN_0002b62c`) and #4 (`FUN_0002c478`)
do NOT reach it at all** -- #3 terminates in a private mode-debounce state machine + diagnostics, #4's
numeric output is proven dead. A 4x GAIN on #3/#4 is a no-op for torque regardless of family; the
V76-family's extra exposure over the V62-family is real but concentrated in #5 (primary) and #6
(secondary/threshold), not spread evenly across all 5 non-forward sites.
