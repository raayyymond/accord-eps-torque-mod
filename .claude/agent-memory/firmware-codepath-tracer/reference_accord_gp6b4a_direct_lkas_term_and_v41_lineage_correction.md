---
name: reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction
description: gp-0x6b4a is a SECOND, direct, unconditional, ungated LKAS-descended term feeding gp-0x6ad6 (the driver-torque reference), independent of the plant-model observer path via gp-0x6b70. No cal gain exists anywhere on its path. CORRECTS build_v41_tva.py/BUILD-LINEAGE.md:705's "0xC6194 architecturally inert" claim, which is true only for the SIBLING gp-0x6b4c, not for gp-0x6b4a.
metadata:
  type: reference
---

# gp-0x6b4a — the direct LKAS term into gp-0x6ad6, full census — traced 2026-08-10, `fw-driver-model` task

Entry point: `FUN_00037fe6` (0x37fe6), the assist-reference-model aggregator that produces `gp-0x6ad6`
(the PID's bias/feedback term in `FUN_0003a382`). Full disasm this session, `code.bin` stock.

## Structure (assembly-verified, `00037fe6`-`00038146`)
```
iVar4 = 0
if |gp-0x6b4a| <= 0x6400 (25600): iVar4 = -gp-0x6b4a      # 0x37fea-0x38004, UNCONDITIONAL, no gate on gp-0x67ab
if gp-0x67ab != 1: iVar4 += Σ(7 gated terms incl. gp-0x6b70, weights 0xC64AD..B3 all =1)
gp-0x6ad6 = clamp(iVar4 * speedLERP(gp-0x69aa)/1024, ±25600)
```
`0x38002: sub r15,r10` = `0 - gp-0x6b4a`, plain, no polarity/negation trap. Re-derived from raw ASM,
not just decompile, per operator instruction after a prior sign-trap history (`ba05`/`b205`) in this kit.

## gp-0x6b4a's production — `FUN_00026c80` (0x26c80), full disasm this session
`gp-0x6b4a` is a **PURE PASS-THROUGH CLAMP, no multiplicative gain anywhere**:
```
000276ba: ld.w -0x3d80[gp],r23   ; Σ_lanes gp-0x6298[lane] where enable[lane]!=0 (straight sum)
000276be: add  r12,r8             ; + rate-limited accumulator (see below)
000276c0: add  r8,r23             ; iVar13
...
000277aa: st.h r23,-0x6b4a[gp]    ; gp-0x6b4a = clamp(iVar13, ±0x6400), PASS-THROUGH — confirmed, no mul
```
Compare the SIBLING `gp-0x6b4c` (0x27722): `gp-0x6b4c = gp-0x3d88_component + polarity(gp-0x6752)*
((iVar13*cal(0xC63CC))>>10)`, clamp ±0x2800. `0xC63CC` fresh-read this session = **0** — so gp-0x6b4c's
iVar13 contribution is nulled at stock; gp-0x6b4c reduces to gp-0x3d88 alone. **gp-0x6b4a never goes
through this multiply — it is architecturally distinct from gp-0x6b4c despite sharing the same iVar13.**

**The 11-lane enable array** `tp+0x5118..0x5122` = `0xC4118..0xC4122`, fresh byte-read = all 1 (11/11).
**The mode array** `tp+0x5124..0x512E` = `0xC4124..0xC412E`, fresh byte-read = `[0,0,5,0,5,5,0,0,0,5,0]`
(lanes 0-10) — independently cross-validated: `build_v41_tva.py` quotes this SAME array verbatim for a
different purpose ("The A160 array is (0,0,5,0,5,5,0,0,0,5,0)"). Modes 0 and 5 BOTH route
`gp-0x62e0[lane]` (raw distribute_clamp torque-channel input) into `gp-0x6298[lane]` identically, so
every lane contributes to gp-0x6b4a at unity, mode-independent. Lane 9 (driver-torque CORDIC,
`gp-0x6b6c`) does NOT reach gp-0x6298 — its struct fields are zeroed at the source (`FUN_000339cc`,
per [[reference_accord_fun2eda8_lane9_raw_torque_command_path]]).

**⇒ gp-0x6b4a = clamp(Σ_{lane=0}^{10} gp-0x62e0[lane], ±25600) at stock, essentially the raw sum of
all 11 distribute_clamp torque-channel inputs, dominated by lane 1 (LKAS, per the existing wiring
memory's "LKAS itself is source index 1").**

## 🛑🛑 LINEAGE CORRECTION — `0xC6194`/`build_v41_tva.py`/`docs/BUILD-LINEAGE.md:705` is WRONG AS STATED

`build_v41_tva.py` (2026-07-20) examined `0xC6194` (the rate-limiter step for the SAME accumulator,
`gp-0x3d6c`, that feeds `iVar13`) and concluded: *"0xC6194 is ARCHITECTURALLY INERT... it multiplies
the entire term carrying the rate-limited state gp-0x3d6c, so (state*0)>>10==0 and **gp-0x6b4c** reduces
to gp-0x3d88 alone."* **That reasoning is CORRECT for gp-0x6b4c** (which does pass through the
`×cal(0xC63CC)=0` multiply) **but WRONG for gp-0x6b4a**, which receives the SAME rate-limited state
(`gp-0x3d6c`, via `r8` at `0x276be`) **unattenuated — no `×0xC63CC` on that branch at all.**
`docs/BUILD-LINEAGE.md:705` ("0xC6194 | DEAD calibration — its gain cal 0xC63CC=0") inherits this
error and should be corrected to note it's live for `gp-0x6b4a`, dead for `gp-0x6b4c`.
🛑 Practical caveat: the rate-limiter's TARGET is `gp-0x3d84` (the enable==0 accumulator), which is
**structurally pinned to 0** since no lane ever has `enable[lane]==0` — so this branch's steady-state
contribution to gp-0x6b4a is small/decaying, not a live gain lever. **Correcting the record, not
proposing a new build from it.**

## Blast radius — gp-0x6b4a is NOT exclusive to the reference model

`search_instructions(operand_pattern="6b4a")`, 11 hits, `truncated:false`:
| function | role |
|---|---|
| `FUN_00026c80` | writer (self) |
| `FUN_00037fe6` | term 0 into `gp-0x6ad6` (this trace) |
| `FUN_00042af8` | **the shaper** — the function that produces `gp-0x6b98` (delivered motor command) |
| `FUN_00043e44` | Monitor M2, hard-shutdown monitor |
| `FUN_000352b4` | another assist lane (`gp-0x6b86`, friction-magnitude) |
| `FUN_00027b0a` | a lockstep/monitor function (3 refs) |

Confirms/extends [[reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction]]'s prior
note. **Editing gp-0x6b4a's PRODUCTION would touch the shaper and a hard-shutdown monitor — high blast
radius.** The only isolated single-point edit is inside `FUN_00037fe6`'s own read (0x37fea-0x38004,
before the negate) — a CODE edit (few instructions), NOT a cal, GATE 1/2 territory. Not recommended
without full review; named as the only clean option because no cal exists.

## The arb-side pole — quantified transfer function on the LKAS setpoint upstream of gp-0x6b3c

`FUN_00028ea6` (arbitration), a 1-pole IIR feeds the curve-clamped LKAS setpoint before it becomes
`gp-0x6b3c`'s `arb_signal` (decompile lines ~1216-1229):
```
s[n] = a*s[n-1] + b*x[n]           a=cal(0xC63EC)/1024=992/1024=0.96875, b=cal(0xC63EE)/1024=507/1024=0.49512
y[n] = (s[n-1]+s[n]) >> 5           # state persisted at gp-0x3d3c
```
fs=1000Hz (control task). Computed response (rel. to DC):
| f (Hz) | mag (dB) | phase (deg) |
|---|---|---|
| 1 | −0.17 | −11.2 |
| 3 | −1.31 | −30.7 |
| 7.79 | −5.29 | **−57.0** |
| 12 | −8.23 | −67.2 |
| 21 | −12.63 | −76.5 |
| 28 | −15.03 | −79.8 |

This likely IS (or is closely related to) the mechanism behind the standing kit memory "LKAS lane is a
~1-5Hz low-pass" — corner matches well. **A separate, EARLIER persistent-state block in the same
function (`gp-0x3d2c`/`3d30`/`3d34`) is NOT a second filter tap on the LKAS signal** — confirmed it's a
multiplicative, driver-torque/angle-rate-gated authority modulator (`iVar23 = (iVar34*uVar18)>>0xf` at
line 1245, `uVar18` from the earlier block) applied to the already-filtered LKAS content, not an
additive second pole.

**Sign direction of term 0 (BELIEF, not fully polarity-tested):** `gp-0x6752` (assist polarity) is
boot-static +1 (per [[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]]),
P/I/D all positive-gain, aggregator ADD-not-subtract confirmed elsewhere ⇒ raising gp-0x6b4a makes
term 0 more negative → bias↓ → err=gp-0x4f60-bias↑ → PID↑ → gp-0x6ad4↑ → aggregator↑, SAME direction
as gp-0x6b4a. Structurally REINFORCING, not cancelling — same shape as the established friction/K1
mechanism ([[accord-friction-polarity-more-assist]]).

## gp-0x67ab — CLOSED, always 0 at stock

Its only writer (`0x2775c`, inside the same `FUN_00026c80`) accumulates, per-lane, `(enable[lane]==0)`
gated on that lane's derived state NOT being in {2,3,4}. Since all 11 enable bytes = 1, this
accumulator (`r14`) is 0 for every lane ⇒ `gp-0x67ab = 0` unconditionally at stock. `FUN_00037fe6`'s
gate `if (gp-0x67ab != 1)` therefore ALWAYS passes ⇒ **the 7-term gated block, including term 7
(`gp-0x6b70`, the friction/observer path), is ALWAYS active alongside term 0. Neither term ever
excludes the other.**

## Related
[[reference_accord_fun2eda8_lane9_raw_torque_command_path]] — lane 9/driver-torque exclusion from this sum.
[[reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction]] — prior blast-radius note this extends.
[[accord-friction-polarity-more-assist]] — the analogous, previously-verified sign chain via gp-0x6b70.
