---
name: reference_accord_fun34350_purely_multiplicative_and_mode_index_debounce_chain
description: FUN_00034350's below-X[0] LERP clamp and multiply chain confirmed instruction-exact (FactorC=0 forces gp-0x6bd0=0, no additive rescue); the mode-index write chain (FUN_00042746, gp+0x63fd) fully decoded with a genuine but SHORT (~40-50ms) debounce, plus an unresolved multi-second-candidate freeze via gp-0x6733's -1 sentinel (FUN_000527da, zero callers found). V74's mode24/26 FactorC/FactorE byte edits cross-confirmed at the pointer level.
metadata:
  type: reference
---

**2026-08-06, dispatched by team-lead to verify/refute "V74's damper edits were NOT in force at the V75-style
hard-fault because disengaged=mode24=byte-stock."** [EVIDENCE throughout unless flagged BELIEF/OPEN.]

## FUN_00034350's LERP struct + clamp, instruction-pinned [extends [[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]]]

Struct: `[count u16][X0..X3 u16][Y0..Y3 u16]`, 18 bytes/record, Y-array base = record+10. **Below-X[0]
behavior is a hard FLAT CLAMP to Y[0], never extrapolation** — confirmed at FactorC's own branch
`0x3451e/0x34520: cmp r13,r7 ; bh 0x34528` (r13=X[0], r7=input); NOT-taken path (input<=X[0]) falls to
`0x34522: ld.hu 0x0[r10],r9` = Y[0]. All 5 factor evaluators (B/C/D/E/ceiling-F) share the identical
branch-then-flat-load idiom (B@0x3448c, D@0x345ae, E@0x3463c, F@0x346d0).

**The seed→B→C→D→E chain (`0x34684-0x3469c`) is PURE `mulu`+`shr 0xa`, four times, zero add/or
instructions anywhere in the span.** Sign flip (`0x3469e-0x346a2`) is a conditional `subr r0,r8`
(multiplicative negate), not additive. The final clamp (`0x34720-0x3475c`) is a symmetric min/max against
a ceiling table plus a shadow-lockstep gate (`sVar2==sVar12`, else `FUN_0006b9fa` fault handler on
mismatch) — gates WHETHER a write happens, never injects a value. **⇒ FactorC=0 provably forces
gp-0x6bd0=0 with no rescue path** — settles the load-bearing step for "was V74's damper live on mode 24."

## Mode-index write chain (`gp+0x63fd`), fully decoded [new this session]

Writer `FUN_00042746`, sole caller `FUN_00022ca0` (100Hz task-5 dispatcher), gated `(1<<(gp-0x67fa&0xF))
& 0x30` = states {4,5} — live whenever `gp-0x67fa` reads 5 (confirmed live during the whole V74/V75-era
fault drive per team-lead's telemetry). Picks 1 of 4 HW-ID-row column tables (`DAT_0000e012/13/14/15` via
`FUN_00057f8e()`), selected by `gp-0x67f6`∈{0,1} × `gp-0x67e2`∈{1,2}.

**Genuine debounce found, but it is SHORT (~40-50ms), not multi-second:**
- `gp-0x68ab` = pending flag, armed at `0x42888-0x42892` when `gp-0x6733`(new target state) changes AND
  `gp-0x6733 != -1` AND `gp-0x4f68 < tp+0x7182` (=`0xC6182`, byte-read=**512**) AND not already pending;
  arming snapshots the free-running counter `gp-0x3e54` (confirmed **+1 per call of `FUN_0002214a`**, the
  kit's established 1kHz control task — `0x2217a`/`0x22182`) into `gp-0x138c`.
- Flag clears when `(gp-0x3e54 - gp-0x138c) >= tp+0x724e` (=`0xC624E`, byte-read=**40**) → **40ms**.
  While pending, the table-reselect block at the top of `FUN_00042746` is skipped wholesale
  (`0x42782: bne 0x4283e`), so `gp+0x63fd` keeps its stale value.
- Stacked with the ramp-settle requirement (`gp-0x69b0` must hit exactly 0 or -0x8000; prior kit finding
  puts worst-case decay ~99ms, see [[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]]),
  the whole chain tops out ≈150ms. **This does NOT match a ~2.5s observed lag.**

**Deeper freeze candidate, upstream producer UNRESOLVED [OPEN, flagged for a live-telemetry follow-up]:**
`gp-0x6733` is written by `FUN_000527da(param_1)`, which sets it to **-1** (transitioning sentinel) for
`param_1∈{1,2,3,5,6,7}`; the arm-gate above requires `gp-0x6733!=-1`, so while in that sentinel the
reselect can't even arm, independent of the 40ms timer. **`get_function_callers(0x527da)` AND
`get_xrefs_to(0x527da)` both return null** — matches the kit's documented register-indirect/RTOS-table
blind spot (same class as `gp-0x1426`'s zero-writer gap). Could not identify what drives `param_1` or how
long it dwells in the -1-producing states. **This — not the 40ms timer — is the more plausible candidate
for a multi-second hold, but is unverified from ROM bytes alone; needs a live `gp+0x63fd` probe across a
disengage event, or `FUN_0005462c`(4,param_1)'s downstream reads chased further.**

## V74 mode24/26 byte cross-check [EVIDENCE, raw reads, both stock `code.bin` and
`_v74_engagedcols_x12_plain_image.bin`]

Pointer arrays `FACTOR_C_PTRS=0xC9E9C`, `FACTOR_E_PTRS=0xC9F84` (stride 4, byte-identical between stock
and V74 — only record CONTENTS differ). Mode24 target: FactorC `0xD67E4`, FactorE `0xD6820`. Mode26
target: FactorC `0xD77D0`, FactorE `0xD780C`.

- **Mode 24 is byte-IDENTICAL to stock in V74** for both records — confirms "disengaged=mode24=byte-stock"
  from [[reference_accord_r24_gainb_mode10_inert_and_24v26_array_diff]]'s methodology, now directly on
  V74's own image.
- **Mode 26 in V74 carries exactly 3 edits, nothing else**: FactorC Y0 `0→429`; FactorE X0 `60→12`;
  FactorE Y1 `140→539`(=stock's own Y2, i.e. Y1:=Y2). X-breakpoints (`2240,3840,5120,8960` for FactorC)
  are UNCHANGED in both modes.
- At the fault-frame speed **2130 counts (33.29 km/h)**, input < X0=2240 in both modes ⇒ same flat-clamp
  mechanism applies, but mode24 returns Y0=0 (architecturally forced zero damper) while mode26 returns
  Y0=**429** (42% of unity, non-zero, reachable). **Prediction holds exactly.**

## Findings
- [EVIDENCE] A non-zero `gp-0x6bd0` at 2130 counts is mathematically IMPOSSIBLE while `gp+0x63fd` reads
  mode 24 (any build with stock FactorC breakpoints), and REQUIRED-non-zero-capable once it reads mode 26
  in V74 specifically.
- [EVIDENCE] The mode index does NOT snap instantly on an engagement-state change — three independent
  gates (ramp settle, ≠-1 sentinel + torque-magnitude<512, then a 40ms timer) stand between a trigger and
  a `gp+0x63fd` rewrite.
- [BELIEF/OPEN] Whether that chain, or something else entirely, produces a ~2.5s real-world lag is
  UNRESOLVED — the one quantified constant (40ms) is roughly 60x too short; the `gp-0x6733`/-1 sentinel
  freeze is structurally capable of an arbitrarily long hold but its driver (`FUN_000527da`'s caller) could
  not be located this session (zero hits, 2 independent methods).

## Related
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — prior mapping this extends
with instruction addresses for the clamp/multiply-chain claims.
[[reference_accord_r24_gainb_mode10_inert_and_24v26_array_diff]] — mode24/26 array-diff methodology reused.
[[reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays]] — `FUN_00042746` first named as
the engagement re-selector; this file adds its debounce internals and the unresolved `gp-0x6733` freeze.
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]] — source of the ~99ms ramp-settle
figure stacked into the ≈150ms total.
