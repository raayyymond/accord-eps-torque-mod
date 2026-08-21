---
name: reference_accord_v101_v102_resonance_mechanism_and_biquad_direction
description: V101/V102 ~20-23Hz resonance-hunt session (task "damphunt round 2", briefed off HANDOFF-2026-08-20-v102). Traces FUN_00026c80/FUN_00025c32 to test whether REQUEST (gp-0x6bfa, one arm of the iVar6 disturbance-observer residual) echoes the LKAS command -- it does NOT (different per-slot field). Establishes a structural DIRECTIONAL argument for why the dead biquad in FUN_000352b4 is a more promising closed-loop candidate than 0xC63AC was: it REDUCES one feedback branch's HF gain (0xC63AC's edit INCREASED its branch's HF gain, which is why the full-loop Bode sum reversed it).
metadata:
  type: reference
---

# V101/V102 resonance mechanism, and why the dead biquad's DIRECTION differs from 0xC63AC's

Traced 2026-08-20, task "damphunt round 2" (orchestrator brief: find what sets the ~20-23Hz pole that
moved 20.3->23.0Hz with the LKAS gain 4x->8x, V101 flown route `0x95`). Builds directly on this same
agent's 2026-08-19 `damphunt` session ([[reference_accord_c63ac_full_loop_bode_sum_net_negative]],
[[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]]).

## 1. `gp-0x6bfa` (REQUEST) does NOT echo the LKAS command -- traced this session, EVIDENCE

Decompiled `FUN_00026c80` (the mixer) and `FUN_00025c32` (per-slot distribute, called once per lane
with a `param_1` struct) fresh. The mixer's 11-slot loop populates SEVERAL parallel accumulators from
DIFFERENT per-slot arrays that `FUN_00025c32` itself writes:

```
FUN_00025c32(param_1):                              # called once per lane/slot
  gp-0x62e0[slot] = clamp(param_1[2],  +-0x4000)     # arb signal
  gp-0x62f8[slot] = clamp(param_1[4],  +-0x2800)     # <- LKAS's own clamp width (10240)
  gp-0x6274[slot] = clamp(param_1[6],  +-0x384)
  gp-0x633c[slot] = clamp(param_1[8],  +-0x4e20)     # <- 20000, matches REQUEST's OWN final clamp
  gp-0x6230/6218/6200[slot] = clamp(param_1[10/12/14], <=0x400)
```

`FUN_00026c80`'s bottom loop:
- **`gp-0x3d88` (-> `gp-0x6b4c`, the "11-slot assist sum" STATE.md documents)** accumulates from
  `gp-0x62b0[slot]` **gated by `0xC4118[slot]`**, and `gp-0x62b0[slot]` is itself copied from
  `gp-0x62f8[slot]` (the raw arb/LKAS-clamp-width field) in modes {0,3,6,7} -- i.e. it descends from
  `param_1[4]`, the field with **LKAS's own ±0x2800 clamp width**.
- **`gp-0x3d90` (-> REQUEST `gp-0x6bfa`, clamp ±20000)** accumulates UNGATED from `gp-0x6324[slot]`,
  which is copied from `gp-0x633c[slot]` (**`param_1[8]`, clamp ±0x4e20=20000**) in every mode except
  {4,6,7} (where it's zeroed).

**⇒ REQUEST's raw per-slot input is `param_1[8]`, a DIFFERENT struct field from the one (`param_1[4]`)
that ends up in the LKAS-lane sum.** These are NOT the same signal. My working hypothesis going in
("REQUEST directly echoes the LKAS command, so raising `0xC6CD0` directly raises REQUEST") is **NOT
confirmed** -- corrected in place before it propagated.

**NOT resolved this session**: which caller of `FUN_00025c32` supplies the LKAS slot's data, and what
`param_1[8]` (REQUEST's source) physically is for that slot -- open, needs `get_function_callers` on
`0x25c32`, matching each call site's slot index (`param_1[0]`) to the known `0xC4124` layout
(`[0,0,5,0,5,5,0,0,0,5,0]`), then tracing that call's `param_1+8` argument back to its producer. This
is the next step to fully close (or kill) the "REQUEST scales with `0xC6CD0`" sub-hypothesis.

## 2. The mechanism does NOT depend on that unresolved link -- the ACTUAL-arm/gp-0x4f60 route is enough

`iVar6 = MODEL + REQUEST - ACTUAL`. Even with REQUEST's LKAS-dependence unresolved, `gp-0x4f60` (real,
physical torque-sensor reading) directly: (a) sets the PID error (`FUN_0003a382`, `err = gp-0x4f60 -
ref`), (b) feeds `gp-0x374c`/ACTUAL (the `0xC63AC` IIR, hence `iVar6`), and (c) is the primary input to
`FUN_000352b4`'s OWN 10-point LERP + magnitude peak-hold feeding `gp-0x6b86` (aggregator's widest lane,
±12288). The V101 handoff already measures the real-world link: delivered command `gp-0x6b94` p50
doubled almost exactly (102.4->204.8, 2.00x) between the 4x and 8x builds -- so the REAL torque the
motor puts through the column plausibly grew by a comparable factor, shifting the OPERATING POINT of
every one of these `gp-0x4f60`-keyed nonlinear/gain-scheduled stages at once. `f'` (the Stage-2 LERP's
local slope) alone moves by up to ~2.9x locally over a 2x amplitude step (computed this session, see
the retrodiction script referenced in the SendMessage to `main`, 2026-08-20). **This is the
evidence-grounded mechanism reported to the orchestrator: an amplitude-dependent re-linearization of
(at least) two gain-scheduled LERP stages that are both keyed on the real, physically-delivered torque
signal -- not a hard limit cycle (matches the measured surrogate-null/kurtosis result), and not a pure
broadband-excitation story (matches the measured "band doesn't scale with command amplitude within a
route" refutation in STATE.md's V102 block).**

## 3. ⭐ Why the dead biquad (`0xC649B`) is structurally a BETTER bet than `0xC63AC` was -- a directional argument

[[reference_accord_c63ac_full_loop_bode_sum_net_negative]] killed `0xC63AC` because raising it REMOVES
an existing pole/lag on Path 2 -- which means it **increases that branch's own gain at high frequency**
(passband widens, 1.08x@7.79Hz -> 1.38x@21Hz -> 1.75x@42Hz for cal 205). Once the loop was closed, that
HF-gain increase dominated the phase-lead credit and made `|L|`/Q worse at every dose tested (150-300).

**The dead biquad in `FUN_000352b4` is the OPPOSITE edit, structurally.** Arming it (`0xC649B` 0->1)
ADDS a real 2nd-order low-pass (ζ=0.65, corner ~42.3Hz) into the `gp-0x6b86` branch that currently has
NO such attenuation -- i.e. it **REDUCES that branch's own gain at high frequency** (-1.25dB@21Hz,
-3.0dB@30Hz, more above), at the cost of added phase lag (-30°@21Hz, -45°@30Hz). `gp-0x6b86` sums into
`gp-0x6b94` at UNITY weight, same as every other aggregator lane (confirmed, `eps_chain_control.py`'s
`motor_torque_demand_aggregator`, "ALL EIGHT ARE STRUCTURALLY VACUOUS... unweighted"), and it is fed by
`gp-0x4f60` -- so it sits inside the SAME mechanical feedback loop as Path 2, but its edit REDUCES
branch gain at the resonant band instead of increasing it. **Reducing one feedback branch's gain at the
frequency of a lightly-damped resonance, at a moderate phase cost, is the textbook STABILIZING
direction** -- the reverse of what killed `0xC63AC`. [BELIEF -- directional/qualitative argument, not a
computed |L|/Q closure] The precise margin still needs the SAME missing ingredient `0xC63AC`'s
retraction needed: the branch's ATTRIBUTION FRACTION (what share of `gp-0x6b94`'s 20-23Hz content this
lane currently carries) -- unmeasured, would need either a telemetry probe on `gp-0x6b86` or an
estimate from its own LERP+peak-hold's typical output magnitude vs the aggregator total.

**Recommendation given to the orchestrator**: rank this lever #1 (one cal byte, reuses Honda's own
coefficients, self-gates on the SAME oscillation-reversal counter `gp-0x671a>=5` used elsewhere to
detect 18-21Hz-class ringing, doesn't touch dθ/dt or add low-frequency friction) but GATE 2 is still
open -- do the same full-loop Bode-sum treatment `0xC63AC` got before cutting, using the attribution
fraction as the free parameter the way `0xC63AC`'s file swept `p`.

## 4. 🛑🛑 RESOLVED: `gp-0x6b62` is NOT the biquad's forcing input — the record's kill mis-locates the gate

Team-lead flagged a direct contradiction: this file's arm condition (`0xC649B==1 AND gp-0x671a>=5`)
vs `STATE.md`/`BUILD-LINEAGE.md`'s kill of the same cell ("forcing input gated on `gp-0x6b62≠0`,
measured duty 0.0000 over 75,227 engaged frames"). Settled by full `disassemble_function(0x352b4)`
this session (784 instructions, whole function, not a partial decompile) plus a fresh
`search_instructions(operand_pattern="6b62", function="FUN_000352b4")` — **exactly one hit, `0x3593e`**.

**Traced precisely**: `0x3593e ld.h -0x6b62,gp,r8` feeds a zero-gate (`addi 0x2000,r8,r6` /
`cmovc 0x0,r8,r12`, the same "pass unless magnitude exceeds a threshold" idiom seen at `gp-0x6acc`'s
gate in `FUN_00042af8`) whose boolean result ANDs into a flag that, at `0x359be
(cmovne r2,r11,r15)`, selects between two candidates for a value **stored ONLY to `gp-0x69a2`
(`0x359c6 st.h r15,-0x69a2,gp`)** — a cell with **no further reader anywhere in this function**.

**The biquad's actual forcing input is a completely different register, `r10`** (`0x35a28
cvtf.ws r10,r7`), whose lineage runs through the peak-hold comparator (`0x3588a-0x358d4`, the
`gp-0x6b7a` held-magnitude vs the 10-point LERP candidate) and ultimately `gp-0x4f60`/`gp-0x6b4a` —
**`gp-0x6b62` does not appear anywhere in `r10`'s dataflow.** The biquad's ARM test itself
(`0x359fe-0x35a26`: `cal(0xC649B)==1` AND `cal(0xC64FA) <= gp-0x671a`) is exactly what this file
already reported, confirmed again instruction-for-instruction on this pass.

**⇒ `gp-0x6b62` gates an unrelated, write-only side-output (`gp-0x69a2`) inside the SAME function —
not the biquad's arm, and not its forcing input.** This is neither clean case "(A) two valid gates,
kill stands" nor a simple wrong-address "(B) misattribution" — it's a **conflation between two
DIFFERENT signals computed in the same function body**, closer to (B)'s conclusion (**the kill's
REASONING does not apply to this lever; the biquad's own gate is `gp-0x671a`, not `gp-0x6b62`**) but
for a different reason than a simple address slip. 🛑 **NOT yet checked**: whether `gp-0x671a` itself
reaches >=5 DURING a real 20-23Hz episode specifically (only generically characterized — "saturates
>=5 in ~125-150ms of 18-21Hz oscillation" — a 20-23Hz episode should saturate it at least as fast by
the same reversal-counting logic, but this is BELIEF, not measured on this symptom). That is the
correct next duty check if this lever proceeds — analogous to, but distinct from, the `gp-0x6b62`
question just closed.

## 5. 🛑🛑 THE BIQUAD SHARES V48B'S EXPOSURE CLASS — confirmed from disassembly, not assumed

`docs/HANDOFF-2026-07-21-v48b-flashed-catastrophic.md`: V48B (a 21.4Hz notch on `gp-0x4f60`/errorterm,
"before fan-out") **bricked the car on startup, parked, no LKAS command** — full-authority oscillation.
Two causes: (1) GATE 1 — a state cell's HIGH BYTE aliased a live monitor/DTC status bitfield; (2) GATE 2
— the notch (its own resonator, r=0.979, ζ≈0.157, Q≈3.2) sat in the **ALWAYS-ON base-assist loop**
(gated only on generic EPS state `gp-0x67fa`∈{4,5,8,10,11}/`gp-0x67fe`, **no LKAS gate, no speed
gate**), whose closed-loop stability was never checked — only a single-frequency magnitude against the
*wrong* (LKAS forward) loop.

**Checked whether `FUN_000352b4` (this file's biquad) shares that exposure class** — `get_function_callers`
+ `disassemble_bytes(dry_run)` at the call site inside `FUN_0002214a`, `0x226e0-0x227b4`. **The call is
gated (`cmp r0,r28 / be <skip>`), not unconditional — but `r28` is ONE flag, set once, reused across a
run of ~10 consecutive calls in this exact code region, including `FUN_0003a9ae`/`FUN_0003aff4`/
`FUN_0003b29c` immediately before it, sitting directly between the already-confirmed PID call (`0x226a0`)
and the aggregator call (`0x2291e`) — both independently confirmed elsewhere to gate on `gp-0x67fa & 0xc30`,
the "normal-driving cluster," explicitly NOT an LKAS-engagement flag.** [BELIEF for the exact mask on
THIS run specifically — did not walk back to the `andi` immediate itself; EVIDENCE for "gated, and almost
certainly on the same non-LKAS state cluster as its immediate neighbours".]

**⇒ `gp-0x6b86`'s producer is very likely live during NORMAL EPS operation, not LKAS engagement — the
same non-LKAS exposure axis that let V48B's carriers stay active parked/hands-off.** Any GATE-2 check for
this lever must cover the BASE-ASSIST loop (not just the engaged-adjacent torque-tracking loop this
whole session has been modeling) and should explicitly include a parked/hands-off/no-LKAS scenario, the
way the V48B post-mortem's mandatory-revival checklist now requires. This does not kill the lever; it
sets the correct (higher-stakes) scope for the check it already needed.

**⚠ No on-car telemetry of `gp-0x6b86` exists anywhere in this kit's record** (`grep -n "6b86"
docs/STATE.md docs/BUILD-LINEAGE.md` → 0 matches) — the attribution-fraction sweep `0xC63AC`'s file did
has NO real anchor available for this lane the way that one did (V96's flight). Recommend: if this
lever proceeds, put `gp-0x6b86` (or its aggregator contribution) on a telemetry channel BEFORE or
alongside any arming build, per this kit's own PROBE DESIGN LAW, rather than theorising the fraction.

## 6. 🛑🛑 THE FULL GATE PACKAGE — V103 candidate cleared, arm inert (fixed in 3 bytes), GATE 2 favorable

Team-lead independently verified the gate reading (§4 above CONFIRMED) but found `gp-0x671a>=5` has
**NEVER been observed true in this kit — 0/255,292 engaged frames across V64/V67/V68**, so arming
`0xC649B` alone is INERT (STATE.md's verdict was right for the wrong reason). **Fix, team-lead's, byte
CONFIRMED by me independently**: patch `0x35A12` in place, `EC 49` (`cmp r12,r9`) -> `E0 49`
(`cmp r0,r9`) — V850 Format I, changes only bits[4:0] (reg1: r12->r0), same opcode/reg2, makes
`setfnc r6` fire unconditionally (r9 is an unsigned byte, `r9-0` never borrows). **V103 candidate =
`0xC649B` 0->1 (1B cal) + `0x35A12` `ec49`->`e049` (2B in-place branch-condition patch, NOT a cave).**

**Team-lead also corrected my filter characterization**: it is a **NOTCH centered at 55.23Hz** (zeros
exactly on the unit circle there), not a low-pass — my earlier "high-shelf, corner ~42Hz" description
undersold its structure (42.35Hz is the POLE frequency, ζ=0.6497, matches what I had; 55.23Hz is where
the numerator zeros null it out, -62.9dB). Above the notch, gain RETURNS (-3.01dB at both 30Hz AND
100Hz) and phase goes POSITIVE (+82.6°@60Hz, +45°@100Hz) — genuinely non-monotone, unlike a simple
pole. DC gain = 1.0000344 (near-exact unity).

**All four of team-lead's required checks, done this session, all favorable:**
1. **Encoding** — `read_memory(0x35A0E,10)` confirms `0x35A12` = `EC 49` = `0x49EC` =
   `cmp r12,r9` (bits[15:11]=r9, bits[4:0]=r12). Proposed `E0 49` changes only reg1->r0. Byte-exact,
   semantically confirmed (`cmp r0,r9` with r9 an unsigned byte never borrows -> CY always clear ->
   `setfnc`=1 always).
2. **GATE 1 (float zero-init)** — `gp-0x3814`/`gp-0x3818` each have exactly ONE reader+ONE writer,
   both inside `FUN_000352b4` (whole-image `search_instructions` census, no boot writer visible to a
   literal-displacement scan). Closed via [[reference_accord_app_ram_layout_and_boot_init_loops]]
   (cited, not re-derived): both cells fall inside the app's `.data` copy range (`gp-0x6E50..gp-0x2598`),
   and the specific flash bytes backing them (`0x86260+(addr-0xFEDF11B0)` = `0x89898`/`0x8989C`) are
   **`00 00 00 00`, verified two ways** (Ghidra `read_memory` + independent raw Python read of the
   flash file). **Both states boot to exactly 0.0f. No NaN/Inf risk.**
3. **GATE 3 (dropout interaction)** — re-read the existing full disassembly of `0x35a86-0x35ae2`
   (no new Ghidra calls needed): the clamped filter/passthrough output `r15` is computed FIRST,
   unconditionally; the dropout test (`|gp-0x4f60|` roughly outside `±0x6400`) reads raw `gp-0x4f60`
   fresh and, if it fires, discards `r15` for a hard literal 0 — **the filter's own recursion state
   (`gp-0x3814`/`-0x3818`) is never touched by the dropout, in either direction.** Benign.
4. **GATE 2 (closed-loop Bode sum, all 3 requested bands, q swept 0.10-1.00)** — extended
   `eps_loop_gain_model.py`'s own anchor (`|L(21.4Hz)|=0.875`, cited unchanged) via its bare-plant
   shape; modeled arming as `L_new(f) = L_total(f)·[(1-q) + q·H_biquad(f)]`. Sanity-checked my
   `H_biquad` reconstruction against team-lead's own reported table first (matched to <0.1dB/<0.1° at
   all 7 quoted points) before trusting the rest. **Result: `|L_new| < |L_total|`, margin IMPROVES, at
   EVERY frequency (6-9/20-30/55-150Hz) and EVERY q from 0.10 to 1.00, including the deliberately
   extreme q=1.00 stress case.** Structural reason, independently confirmed by a fine 0.1Hz scan across
   the full 0.1-500Hz range: **`|H_biquad(f)| <= 1.000032 everywhere, max AT DC — this filter can only
   ever REMOVE magnitude from its branch, never add it**, the polar opposite of `0xC63AC`'s edit (which
   added HF gain and got reversed once closed). Two assumptions stated explicitly in the report to
   team-lead: `L_total(f)` away from 21.4Hz is extrapolated (not measured) via the single-mode shape;
   the UNARMED baseline is modeled flat/zero-phase (its true describing-function phase above ~30Hz is
   uncharacterized — the one place a "net cancellation could exist and get removed" escape hatch lives,
   though nothing in the record suggests `gp-0x6b86`'s unarmed content is currently canceling anything).

Script: `C:\Users\dudei\AppData\Local\Temp\claude\...\scratchpad\gate2_biquad_closed_loop.py` (scratchpad).

## 7. 🛑🛑 ENGAGED-ONLY REPOINT — all 5 verification items done, byte-exact, ready to build

Team-lead proposed repointing the arm from `gp-0x671a>=5` to `gp-0x6806!=0` (the engagement flag,
≡`latActive` 99.983%) to remove the V48B-class exposure entirely (concern: `FUN_000352b4` is gated on
the non-LKAS `gp-0x67fa` normal-driving cluster per §5, so an always-on arm changes manual steering and
is live parked/hands-off). All five items VERIFIED this session, from real bytes, not hand-decoded:

1. **`ld.bu` disp for `gp-0x6806` = `0x97FB`** — confirmed from **11 real existing readers** elsewhere
   in the image (`search_instructions operand_pattern="6806"`, e.g. `0x2A1B6`,`0x2EF40`,`0x30C26`×5),
   every one showing displacement halfword `0x97FB` byte-for-byte. The record's `0x97FA|1==0x97FB`
   warning is a SCANNING artifact, not a claim `ld.bu` can't address this byte — Ghidra's hardware
   decoder resolves it unambiguously across all 11 real instances.
2. **Register-field half cross-validated arithmetically against real bytes**: `read_memory(0x35A06,4)`
   = `84 4F E7 98` (current `ld.bu -0x671a,gp,r9`). Derived halfword1 = `reg2<<11|opcode<<5|reg1` =
   `(9<<11)|(0x3C<<5)|4` = `0x4F84` → bytes `84 4F`, **matches the real bytes exactly**, validating the
   method before using it for the edit. **New bytes at `0x35A06`: `84 4F FB 97`** (halfword1 unchanged,
   only the displacement half changes, copied verbatim from the 11 real readers above).
3. **No separate "setfnz" mnemonic — it's `setfne`, condition 0xA (NE≡NZ, same Z-flag).**
   `search_instructions(mnemonic="setfnz"/"setf")` return 0 (exact-match filter). Decoded 3 real
   `setfXX` instances byte-for-byte in-context: `setfe r8`(`0x35A0E`)=`E2 47`→cond=0x2 ✓,
   `setfnc r6`(`0x35A18`)=`E9 37`→cond=0x9 ✓, `setfne r12`(`0x35950`, SAME function)=`EA 67`→cond=0xA ✓
   — matches the kit's own established Bcond table exactly (0x2=E,0x9=NC,0xA=NE). **New bytes at
   `0x35A18`: `E9 37 00 00`→`EA 37 00 00`** — a ONE-BYTE, one-nibble change, cross-validated two
   independent ways (flip `setfnc r6`'s condition nibble; flip `setfne r12`'s register field) that agree.
4. **`gp-0x6806` freshness — written EARLIER in the SAME 1kHz tick, zero skew.** Writer `FUN_00028ea6`
   called at `0x22522`; my biquad's call at `0x227B4`; `0x22522 < 0x227B4`, same `FUN_0002214a` pass.
5. **`r9`'s later use — clean, no dependency broken.** `search_instructions(operand_pattern="r9",
   function="FUN_000352b4")`, 44 hits: after the load+compare, next touch is `0x35A30: ld.w
   0x70B4,tp,r9` — a fresh overwrite before any other use of r9.

**Full engaged-only V103 candidate, all bytes pinned**: `0xC649B` 0→1 (1B cal) + `0x35A06` `84 4F E7
98`→`84 4F FB 97` (arm source: `gp-0x671a`→`gp-0x6806`) + `0x35A18` `E9 37 00 00`→`EA 37 00 00`
(comparator: NC→NE, i.e. "counter≥threshold"→"flag≠0"). Three in-place edits, no cave, no new RAM.

**Bonus — the fallback (always-on) `andi` mask, pinned as EVIDENCE not BELIEF**:
`search_instructions(mnemonic="andi", function="FUN_0002214a")` — `0x221D6: andi 0x830,r25,r28` is the
**ONLY** instruction in the whole function writing `r28`, unchanged all the way to the `0x227B4` call
site. **`0x830` = states {4,5,11}** — a SUBSET of the PID/aggregator's `0xc30`={4,5,10,11} (missing
state 10), not identical as earlier guessed, but still within the same non-LKAS "normal-driving
cluster" family.

## 8. 🛑🛑 Re(Z) SIGN ANALYSIS — direction favorable everywhere tested, magnitude falls well short

Team-lead reframed GATE 2 from a magnitude question (losing, −1.25dB vs a 10× excess) to a SIGN
question using fresh `route-stock` data: stock is DAMPED at 22-26Hz (+247 to +496 ct·s/rad, both speed
bins, non-overlapping CIs), **V102(6×) is ANTI-DAMPED at the identical band/speeds** (−134 to −99) —
the gain increase FLIPS the sign, not just the magnitude, and it's the ONE band where this happens
(6-9Hz is anti-damped in stock too).

**Fixed a real bug in my own earlier GATE-2 pass first**: that model used the bare plant's phase
directly for `L_total(f)`, giving `arg(L_total(21.4Hz))≈-90°` — but `eps_loop_gain_model.py`'s OWN
stated assumption is a +90° rate-carrier rotation cancelling the plant's -90° so `L` is real-positive
AT the resonance (its own "aligned/destabilizing" convention for the peaking formula). Corrected by
including that SAME +90° rotation (cited, not invented) — now `arg(L_total(21.4Hz))≈+3.7°`, consistent.

**Calibration**: linked `Re(L_total)`→`Re(Z)` via a constant `C`, calibrated from the ONE real
gain-driven data point available (stock 1×→V102 6×, `ΔRe(Z)=-488` at the band center), under the
anchor script's own "loop gain scales linearly with delivered-command multiple" premise (fixed phase
shape, scaled magnitude). Applied the SAME `C` to the biquad's own `Re(ΔL)=q·Re(L_total·(H_biquad−1))`.

**Result — checked BOTH directions as asked, no flip found**: at every f∈[20.3,26]Hz and every
q∈[0.10,1.00], predicted `ΔRe(Z)` from arming is **POSITIVE** (toward stock, never away). Robust
because `Re(H_biquad−1)` is strongly negative throughout this band (dominated by the magnitude cut,
−0.23 to −0.38) and `Re(L_total)` stays positive across 20.3-26Hz in the corrected model — the modest
−30°→−34° phase rotation doesn't overcome the magnitude effect here.

🛑 **But magnitude is a real shortfall**: at the extreme stress case `q=1.00`, best point (24-25Hz),
predicted correction is only **~+50 ct·s/rad** against the **−488 ct·s/rad measured gap** — roughly
**10% of the way back**, landing armed-V102 at an estimated **~−67 (still anti-damped)**. At realistic
`q` (0.10-0.25, since `gp-0x6b86` is one of ~9-10 unweighted aggregator lanes), correction is only
**+2 to +13 ct·s/rad — negligible**. **Verdict given to team-lead: directionally correct and safe
(GATE 2 passes cleanly, never predicted worse), but NOT a fix for the sign flip on its own — a small,
free, safe assist layered on top of whatever the gain-dose choice actually does, not a substitute for
it.** Stated assumptions: the +90° carrier rotation (cited), gain's linear-magnitude/fixed-phase
scaling (cited), and — the weakest link — `C` assumed UNIFORM regardless of which branch contributes
`ΔRe(L)` (a first-order, whole-loop treatment; does not separately model D's own contribution the way
`pump-hunt` is doing for the D-term specifically).

Script: `scratchpad/rez_sign_analysis.py`. Cross-referenced `pump-hunt` (D-term pump/damp hunt, same
22-26Hz crossover) and `ratchet-inertia` (6-9Hz ratchet, brackets the same crossover from below) —
both independently converged on the SAME 22-26Hz Re(Z) sign flip from different directions this session.

## 9. The original Path-2/f' retrodiction, closed to the extent the data allows — MODEST, not dramatic

`route-v102` delivered the one number the original mechanism (§2 above) needed:
`arg(csd(gp-0x6b26,tq))` at 20-23Hz = **+82° to +87°** (ZOH-corrected, 2 routes, call it +84°±5°) —
closing the retrodiction gap flagged in my very first report. **Sign convention resolved with NO
flip**: firmware packer `FUN_00055c42` gives `wire = -(gp-0x4f60×125/128)` (MEMORY_CONSTELLATION Era
18, cited); their cache is `tq = -1×wire`; substituting gives `tq ≈ +0.977×gp-0x4f60` — same sign.

**Recomputed `Q=2.5771·f′·H_iir(f)·L(f)`, `B=1+Q`, using this REAL phase** (still using the 7.79Hz
`|L|≈0.066` amplitude as an explicit, flagged PLACEHOLDER — `|L|` itself is unmeasured at 20-23Hz,
route-v102 gave phase only): `|Q|` stays **well below 1** at both f′ regimes (0.22-0.24 hands-off,
0.035-0.037 hands-on), `cos(argQ)≈+0.82` (positive — does NOT satisfy the inversion criterion, unlike
7.79Hz where it does), so **no inversion at 20-23Hz under this L phase** — Path 2 stays a small NET
LEAD (arg B = +1° to +7°) rather than flipping to lag. **The f′-driven shift itself (hands-off→hands-on)
moves `arg(B)` by only ~-5° at this band** — a real, computed effect, but **modest, not obviously large
enough alone to be the dominant driver of a 2.7Hz pole shift.** Honest read: this does not kill the
f′-compression mechanism (it's one contributing branch among several in the full loop, and the
UNMEASURED `|L|` magnitude at 20-23Hz could change this materially if it's larger than the 7.79Hz
placeholder) but it should not be oversold as a closed quantitative explanation either — **the real
remaining gap is `|L|`'s MAGNITUDE at 20-23Hz, not its phase anymore.**

This is a SUPPLEMENTARY closure of the session's original mechanism question, offered for
completeness — it does not revise the V103 biquad recommendation, which rests on the direct,
better-anchored Re(Z) stock-vs-V102 measurement in §8, not this bracket theory.

Script: `scratchpad/path2_retrodiction_final.py`.

## 9b. 🛑🛑⭐ UPDATE: route-v102 measured the real `|L|` too — |Q| was 3.9x understated, and this
##     now explains the operator's OWN reported hands-on/hands-off behavior directly

`route-v102` followed up with `|gp-0x6b26|`'s real transfer magnitude at 20-23Hz: **0.259/0.273** (two
routes, 5% agreement, 34-79× above the quantisation-noise floor — a real measurement, not noise).
This is **gp-0x6b26 ALONE**, not the 3-lane combined sum my `0.066` placeholder was (7.79Hz,
`6b26+6bbe+6b46`) — units caveat noted and confirmed with route-v102 (`gp-0x6b26` was ~67% of the
combined sum at 7.79Hz, so using it alone at 20-23Hz is a reasonable but not exact stand-in for the
true combined `L`).

**Recomputed `Q`/`B` with the real magnitude — the picture changes substantially**:
```
                    hands-off-ish (f'~2.17-2.54)         hands-on-ish (f'~0.35-0.49)
20-23 Hz:  |Q| = 0.85-0.92, arg(B) = +16 to +19 deg    |Q| = 0.14-0.15, arg(B) = +4 to +5 deg
           |B| ~= 1.77-1.82  (a REAL ~1.8x amplification)   |B| ~= 1.11-1.12  (modest)
```
(a +15% same-phase allowance for `6bbe`/`6b46` pushes `|Q|` to 1.02-1.06 — i.e. plausibly AT or just
past 1 in the hands-off regime specifically, though `cos(argQ)=+0.80` stays solidly positive so this
does NOT satisfy the inversion criterion — it's an AMPLIFICATION story at this band, not an inversion
one.) **This is a materially different, more significant finding than §9's placeholder-based "modest,
~5°" conclusion** — Path 2 contributes a genuine, sizeable (~1.8×) loop-gain boost at 20-23Hz
specifically when the driver's hands are OFF (`f'` on the steep part of the LERP), collapsing to a
modest ~1.1× when hands are ON (`f'` on the flat part).

⭐ **This maps directly onto the operator's own reported behavior** — *"I can actually get it to go
away, if I apply some torque to the steering wheel. However, as soon as I let go... the grinding
returns and grows"* (V101 handoff §1) — since driver torque is exactly what drives `iVar6` from the
hands-off regime (p50 188ct) to the hands-on regime (p50 2829ct, per the `f′` compression finding),
and that swing is EXACTLY what collapses Path 2's `|B|` from ~1.8× to ~1.1× in this computation.
[BELIEF — a real, quantitative, data-grounded match to the operator's report, not yet independently
confirmed by a dedicated hands-on/off telemetry contrast at 20-23Hz specifically; flagging as the most
promising SINGLE explanatory thread this session produced for the qualitative hands-on/off behavior.]

⚠ **Does NOT establish the SAME mechanism explains the GAIN-driven frequency shift (20.3→23.0Hz across
4×→8×).** Gain's own effect on `iVar6`'s baseline (via ~2.00× more real delivered torque, V101 handoff
§2.2) is far smaller than the ~15× hands-on/off swing that actually moves `f′` across its steep-to-flat
range — so gain alone, at a given hands-on/off driving style, would NOT obviously push the operating
point out of the hands-off-ish `|B|≈1.8×` regime. **Two separate, both-real findings — do not conflate
them**: (1) hands-on/off collapses Path 2's amplification ~1.8×→1.1× at this band (strong, newly
quantitative); (2) whether/how gain alone moves the peak 20.3→23.0Hz remains the ORIGINAL open question,
not resolved by this update.

Script: `scratchpad/path2_retrodiction_updated_L.py`.

## 9c. CORRECTION from route-v102: the lanes CANCEL (vector sum), not add — |Q| back under 1

My "+15% same-phase allowance" in §9b assumed `gp-0x6bbe` ADDS to `gp-0x6b26`. route-v102 measured
BOTH lanes' complex transfer directly: `gp-0x6b26` = `0.2657∠+84.2°`, `gp-0x6bbe` = `0.0650∠-47.7°` —
**131.9° apart, so the correct combination is a VECTOR sum = `0.2275∠+72.0°`, SMALLER than `gp-0x6b26`
alone (0.856×), not larger.** The third lane (`gp-0x6b46`) is confirmed structurally negligible at
this band (`FUN_00036682`'s own 0.94Hz EMA gives -27dB at 21.5Hz, corroborated by
`build_v97_tva.py:168`'s independent "~1.1 of 342 counts" figure) — so **the 2-lane vector sum IS the
combined L**, not a placeholder.

**Recomputed: `|Q|` hands-off-ish = 0.73-0.79 (not 0.85-0.92) — back under 1, comfortably.** Growth
factor corrected: `gp-0x6b26` alone grows 6.0× from 7.79→21.5Hz; the COMBINED `L` (the one `Q` actually
uses) grows **3.45×** from my original 0.066 placeholder, not 3.9×.

⚠ **Caveat on the vector sum itself, route-v102's own, kept**: the two lanes' phases were measured on
DIFFERENT routes (r77/r78 for `6b26`, r79 for `6bbe`), not simultaneously — the 131.9° separation and
hence the 0.856× cancellation factor assumes each lane's transfer function is build-invariant, which is
plausible for a sensor-fed lane but **not proven**. The individual magnitudes (0.2657, 0.0650) are
EVIDENCE; their VECTOR COMBINATION is BELIEF.

**The hands-on/off mechanism (§9b) survives, recalibrated smaller**: ~1.5× amplification collapsing to
~1.1-1.2× (not ~1.8×→1.1×) — route-v102's own assessment: "the part of your finding that matters is
untouched" — the swing between regimes is what the operator's report needs, and the `L`-scaling largely
cancels out of that ratio regardless of its absolute value.

## 9d. 🛑🛑 FINAL STATE: the hands-on/off mechanism is NEITHER CONFIRMED NOR REFUTED — the clean test
##     does not exist in the current corpus. Do not cite it as settled in either direction.

Original framing (superseded by the analysis below): "V101 continuous / V102 intermittent, wrong
direction for a naive torque-suppression reading" was flagged as an open tension. `route-v102` then
**ran the actual within-build test** (`rlog-tools/v102_torque_intermittency.py`) and found it **is not
runnable, and the reason retracts the tension too, not just leaves it open**:

- **Grip is collinear with steering activity** (Spearman `corr(|tq|, wheel rate)` = +0.35 to +0.78
  across all four builds — the operator grips when he's steering, and steering is broadband
  excitation). Conditioning on speed×wheel-rate to remove that confound empties the cells: **0 surviving
  cells on either V101 or V102.**
- **The naive speed-only comparison is backwards AND uninterpretable**: high torque correlates with
  MORE band power on every build, **including STOCK** (4.44×/1.95×), which has **no resonance at all**
  (peak prominence 2.31, argmax CI spanning the whole search band). A trend that appears identically on
  a build with nothing to excite is measuring steering activity, not resonance interaction — **void in
  both directions**, not just weak evidence.
- ⇒ **The cross-build intermittency comparison (V101 vs V102) that motivated this whole sub-thread
  carries the exact same confound and does not resolve the mechanism either way.** `route-v102`
  explicitly retracted any weight it implied against the hypothesis.

**The clean test — engaged, straight-line cruise (`|wheel rate|<3°/s`), constant speed, grip
alternating — does not exist in the current corpus**: STOCK has 24s of it; **V100 has 1s, V101 has 5s,
V102 has ZERO seconds across 566s engaged.** Out of 1,661s of engaged driving across four builds, the
one matched cell this mechanism needs essentially doesn't exist.

**`route-v102` has already flagged the fix to `main` directly**: a ~20-30s deliberate maneuver
(engaged, straight highway, constant speed, alternating ~500-1000ct torque WITHOUT steering) — one
episode, fits the kit's "one short symptomatic drive" design law, and close to something the operator
already does by reflex per his own V101 report. Flagged with the appropriate caveat ("exposure is not
the operator's job to supply" cuts the other way here) — **his call, not either of ours.**

**⇒ STANDING STATE, do not overstate either direction**: the §9b/9c amplification-collapse mechanism
remains a structurally well-grounded HYPOTHESIS (real transfer-function measurements, a real `|Q|`
computation, a plausible qualitative match to the operator's report) that is **UNTESTED against
telemetry** — not confirmed, not refuted, blocked on exposure that doesn't exist yet. Cite it as open,
with this note, not as settled.

## 10. 🛑🛑 FINAL V103 BUILD SPEC — delivered to team-lead, all bytes re-verified against the ACTUAL V102 image

All four edit bytes (`0xC649B`, `0x35A06`, `0x35A12`, `0x35A18`) independently re-read directly from
`_v102_V101BASE-GAIN6X.C6CD0.5346-CAVE.CMP.6ADA.6AE2-SIGNS-427.6B4C-ID.ID3.6_plain_image.bin` (not
stock, not inherited) — **all match exactly** what was derived/verified earlier in this file. This is
the base the build will actually start from.

**ENGAGED-ONLY (preferred), full byte list**:
`0xC649B` `00`→`01` · `0x35A06` `84 4F E7 98`→`84 4F FB 97` (arm source `gp-0x671a`→`gp-0x6806`) ·
`0x35A12` `EC 49`→`E0 49` (comparator NC→unconditional-true-for-r9≠0-flag) · `0x35A18` `E9 37 00 00`→
`EA 37 00 00` (condition NC→NE, matches the new comparator). 4 bytes, all in-place, zero new code/RAM.

**ALWAYS-ON (fallback)**: `0xC649B` `00`→`01` + `0x35A12` `EC 49`→`E0 49` only (2 bytes). Exposure
stated: gates on `andi 0x830`={4,5,11} (§7, pinned as EVIDENCE), non-LKAS, changes manual steering,
live parked/hands-off — same exposure AXIS as V48B, NOT the V48B RAM-collision CLASS (Honda-owned state).

**Delivered to team-lead as a complete spec**: byte list (both variants) · one-paragraph GATE
summary (all 4 PASS) · the honest magnitude statement (~10% of the gap closed at best-case q=1.0,
negligible at realistic q) prominently separated from the PASSes so it can't read as "fixed" ·
the 4 stated assumptions incl. the unarmed-branch-phase residual · the probe-cave interaction check
(NO code-level interaction — `gp-0x6ada`/`gp-0x6adc` come from a disjoint function/input chain,
`gp-0x4f60` is read-only, `r9`'s reuse is locally dead; the only real interaction is the INTENDED
physical one — probe readings change post-arm because that's the effect under test) · the 8×
instrument fix (427's Nyquist 24.9Hz can't see a ~25.9Hz highway mode at 8×; use the 100.74Hz bus
channels `rate_c`/`cs_ang` instead — clean, coh²>0.94, no ZOH problem, per route-v102's §9 measurement).
Coordinated with `cave-engineer` (envelope/CRC, no conflicts) and `pump-hunt` (probe rungs, disjoint,
confirmed) before sending. **This closes my part of the V103 build unless something upstream changes.**

## Related
[[reference_accord_c63ac_full_loop_bode_sum_net_negative]] -- the reversed same-day ranking this session's #1 bet supersedes.
[[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]] -- the biquad's pole/frequency-response characterization this file's argument depends on.
[[reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop]] -- the bracket math (`B=1+Q`) underlying the amplitude-dependence argument in §2.
[[reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound]] -- the f' table used for the retrodiction.
[[reference_accord_gp6b26_closed_both_directions_v94_aborted]] -- the caution this file's §3 explicitly does NOT get to skip (isolated-branch safety is not closed-loop safety) -- GATE 2 is still open for the biquad.
