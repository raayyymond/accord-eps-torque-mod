---
name: reference_accord_c646c_gain_feedback_vs_forward_classification
description: Definitive 6-reader enumeration of gain cal 0xC646C (tp+0x746c, the 4x LKAS authority gain) with FORWARD/FEEDBACK classification per site; 3 of 6 sites multiply raw Sensor-B torque gp-0x4f60 directly and two (FUN_00036682/FUN_00036828) chain into gp-0x6b98, BUT that lane is slow/small-authority (2.18Hz, +/-512) and its saturation nonlinearity empirically never fires on 2 confirmed-vibration on-car datasets -- probably not the 21Hz driver. Includes a found free cal word (0xC6CD0) and a negative result on an LKAS-only upstream gain substitute.
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
