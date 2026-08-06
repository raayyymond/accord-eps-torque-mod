---
name: reference_accord_friction_lane_c407e_census_and_mode26_record_identity
description: CLOSES two open items on the friction lane (FUN_00036c12/gp-0x6b26) at mode 26 (the now-confirmed TVCA4 engaged mode) -- a 5-method-verified full census of cal 0xC407E (3 total accesses, all reads, all in FUN_00036c12, zero writers, zero extended-disp23, zero pointer-indirect) and byte-exact confirmation that 0xCBE74[26]=0xD7A54 is the SOLE record FUN_00036c12 ever dereferences (0xCBE74 has exactly one consumer, image-wide) -- i.e. "the friction record 0xD7A54" and "FUN_00036c12's gp-0x6b26 lane" are NOT two terms, they are the SAME mechanism.
metadata:
  type: reference
---

Task: operator's "drag terms" brief, 2026-08-06. Full decompile+disasm+byte-read re-verification of
`FUN_00036c12` (friction lane) and `0xC407E` (its self-clamp), against `code.bin` (confirmed via
`list_open_programs` -- 7 programs open, `code.bin` matches `stock_fw_dump/code.bin` exactly, used
exclusively this session). Extends
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]],
[[reference_accord_gp6b26_friction_lane_damping_candidate]] (kit-level memory) and
[[reference-accord-car-is-tvca4-mode-24-26]].

## 1. `0xC407E` full census -- CLOSED, 5 independent methods [EVIDENCE]

| method | result |
|---|---|
| `get_xrefs_to(0xC407E)` | **"No references found"** -- the MISLEADING ZERO the skill warns about for tp-relative displacements |
| `search_instructions(operand_pattern="507e")` | 9 raw hits; 6 are false positives (3 branch-target substring collisions to VA `0x4507e`/`0x507e2`, 3 are `gp-0x507e` -- a totally different, unrelated cell at `0xFEDA7F82`) -- **3 real hits, all in `FUN_00036c12`** |
| Python disp16 4-byte-form scan (`reg1=hw1&0x1F==5(tp)`, per-opcode table incl. store-of-zero rule) | **3 hits**, byte-identical addresses to the real `search_instructions` set: `0x36c34`, `0x36cd0`, `0x36cdc`, all `ld.h`, **zero `st.h`/`st.b`/`st.w` writers found anywhere in the image** |
| Python disp23 6-byte extended-form scan (reg1=tp, reg2=0 escape, disp23=0x507E) | **0 hits** |
| Python LE32 literal scan for `0x000C407E` | **0 hits** (no pointer-indirect access) |

**⇒ Exactly 3 accesses to `0xC407E` exist in the whole 1MB image, all reads, all inside `FUN_00036c12`,
zero writers anywhere** -- expected for a flash/ROM calibration constant (tp-relative addressing off
`tp=0xBF000` reaches the cal block, not RAM; runtime code never writes it, only the `.rwd` build
pipeline does). Independently matches `build_v73_tva.py`'s own header comment ("THREE readers, ZERO
writers, all `ld.h`") byte-for-byte -- cross-validated against the build-script record, not just Ghidra.

Reads, in `FUN_00036c12`:
- `0x36c34`: `ld.h 0x507e[tp],r16` -- loaded ONCE, early, into `r16`/`iVar10`, held for the whole function
- `0x36cd0`: `ld.h 0x507e[tp],r6` -- re-read on the "clamp to +cal" branch
- `0x36cdc`: `ld.h 0x507e[tp],r13` -- re-read on the "clamp to -cal" branch

## 2. `0xC407E`'s role, address-exact [EVIDENCE]

It is a **symmetric self-clamp on the lane's OWN raw product**, applied BEFORE the value is ever stored
to `gp-0x6b26` (and before the aggregator's separate `±0x400`(1024)-inclusive zero-reject window on
`gp-0x6b26` ever sees it):

```
0x36cbe-0x36cca: iVar5 = ((gate(gp-0x6c2c) * sVar7) >> 6) * 0x111 >> 0x12    ; raw product, pre-clamp
0x36ccc: cmp r16,r6      ; r16=cal(0xC407E), r6=iVar5
0x36cce: ble 0x36cd6     ; if iVar5 <= cal: skip the +clamp
0x36cd0: r6 = cal(0xC407E)                                                   ; iVar5 := +cal
0x36cd6-0x36ce2: (else) if iVar5 < -cal: iVar5 := -cal   (mirror test, r13=cal reloaded at 0x36cdc)
```
i.e. `iVar5 = clamp(iVar5, -cal(0xC407E), +cal(0xC407E))`. Stock cal = **511**; V73 raised it to **850**
(build-script-confirmed, see below) and it has stayed 850 through V74/V75/V76.

**Consequence: the TRUE binding ceiling on `|gp-0x6b26|` in this firmware is `0xC407E`'s value (511
stock / 850 V73+), which is TIGHTER than the aggregator's own `±1024` window** -- so the aggregator's
own zero-reject band is architecturally unreachable via this lane alone (same structural pattern as
`gp-0x6bd0`'s aggregator window vs its own FactorF ceiling, per
[[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]]).
**Raising `0xC407E` raises the MAXIMUM opposing torque the friction lane can deliver at large-rate
transients; it does not change the lane's small-signal gain** (the multiply chain that produces `iVar5`
is untouched by this cal).

## 3. `0xCBE74`/`0xD7A54` -- byte-confirmed mode-26 identity, and ONE consumer image-wide [EVIDENCE]

Full 160-byte read of `0xCBE74` (40 x 4-byte-LE pointers, one per mode 0-39) decoded by hand, index =
mode directly (`byte@gp+0x63fd`, shl 2, add to `0xCBE74` -- confirmed from `FUN_00036c12`'s own disasm
`0x36c4a-0x36c58`). **`[24] = 0x000D6A64` (manual), `[26] = 0x000D7A54` (engaged)** -- matches the
task brief's stated `0xD7A54` exactly, confirmed by direct byte read, not assumed from the array-index
arithmetic alone.

Both records read (16 bytes each): **byte-identical in stock** --
`03 00 00 00 00 05 80 16 9a d9 9a e9 52 f8 00 00` at BOTH `0xD6A64` and `0xD7A54` -- decodes to
count=3, X=(0,1280,5760)=(0,20,90)km/h @ 64ct/km/h, Y=(-9830,-5734,-1966). Matches the task's stated
stock mode-26 values exactly, and matches this kit's OLDER "mode10" read
(`0xCBE74[10*4]=0xD2A44`, same Y values) byte-for-byte too -- confirming the mode-10 record used before
the TVCA4 discovery just happened to carry the same magnitude table as mode 26 (the table content
repeats across many mode rows in stock; the ADDRESSES differ, which is exactly what makes a mode-26-only
edit like V74's x1.5 raise possible without touching mode 24/manual).

**`0xCBE74` has EXACTLY ONE consumer in the whole image** -- `search_instructions(operand_pattern="cbe74")`
and `get_xrefs_to(0xCBE74)` agree: the sole `mov 0xcbe74,r12` immediate load is at `0x36c4e`, and the two
`ld.w` dereferences (`0x36c58`, `0x36c5c`) are both inside `FUN_00036c12`. **No other function anywhere
touches this table.**

## ⇒ SETTLES: "the friction record 0xD7A54" and "`FUN_00036c12`/`gp-0x6b26`" are the SAME lane, not two

`0xD7A54` IS the exact Y-array `FUN_00036c12` loads as `sVar7` (the magnitude term) when the car is in
mode 26 (engaged). There is only one friction mechanism in this firmware as traced -- not a separate
"friction record" term that adds alongside `FUN_00036c12`'s own computation. Any future V7x lever that
edits `0xD7A54`'s Y-values (e.g. V74/V75's x1.5, `-9830,-5734,-1966 -> -14745,-8601,-2949`) is editing
`FUN_00036c12`'s own input table, full stop -- not a parallel/independent path.

## 4. Speed-shaped local gain, computed at the 5 requested speeds [EVIDENCE, arithmetic from the confirmed formula]

Static per-count gain of the lane (pre-clamp) = `sVar7(speed) * 0x111 / 2^24` = `sVar7 * 1.62721e-5`,
`sVar7` = the mode-26 LERP output at that speed (speed counts = km/h x 64):

| km/h | speed cts | sVar7 (LERP) | gain (counts opposing / count `gp-0x6c2c`) |
|---|---|---|---|
| 0  | 0    | -9830 (=Y0, at/below X0) | **-0.1600** (matches the task's stated figure to 4 sig figs) |
| 5  | 320  | -8806 (interp X0-X1)     | -0.1433 |
| 10 | 640  | -7782 (interp X0-X1)     | -0.1266 |
| 20 | 1280 | -5734 (=Y1, exactly at X1) | -0.0933 |
| 35 | 2240 | -4926 (interp X1-X2)     | -0.0802 |

Magnitude falls monotonically with speed (matches the established "largest at 0 km/h, ~5x smaller by
90 km/h" shape). This is the STATIC gain from `gp-0x6c2c` to `gp-0x6b26`; it does NOT include the
frequency-dependent K1/K2 cascade gain (rising 3.08x@7.79Hz -> 7.5x@20.9Hz -> 12.1x@61Hz, per
[[reference_accord_gp6c2c_transfer_function_triple_verified]]) that shapes `gp-0x6c2c` itself from the
root signal `gp-0x4f50` -- that is a SEPARATE, frequency-dependent multiplier on top of this table.

## 5. `gp-0x6c2c`'s gate is (moot) dual-tail, not single-tail -- minor addendum, no behavior change

Own-disassembly this session (`0x36c1a-0x36c2c`) of `gate(gp-0x6c2c)`, cross-checked against the
decompile's `(&DAT_00007d00 + gp-0x6c2c < &DAT_0000fa01)` rendering: the test is
`(gp-0x6c2c + 32000) <u 64001` (unsigned 32-bit compare after sign-extension) -- this zeroes BOTH
`gp-0x6c2c <= -32001` AND, by the same unsigned-wraparound-free arithmetic, `gp-0x6c2c >= 32001`
(0x7d00+32767=64767 >=64001). [[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]] documented
only the negative tail. **Both tails are architecturally unreachable anyway** -- `gp-0x6c2c`'s own
producer (`FUN_00041464`/`0x4184e`) already clamps it to ±32000 before this lane ever sees it (per
[[accord-gp6c2c-is-motor-rate-derivative]]) -- so this doesn't change any prior conclusion: for every
value `gp-0x6c2c` can actually take, `gate(gp-0x6c2c) = gp-0x6c2c` exactly (unconditional pass-through
in practice).

## 6. `gp-0x6c2c` is NOT literally "column/steering rate" -- correction to the operator's framing

`gp-0x6c2c` (this lane's input) and `gp-0x6abe`/`gp-0x6ac0` (the FUN_00034350 damper's sign/magnitude
inputs) share a common ROOT (`gp-0x4f50`, the resolver-derived motor ELECTRICAL rate estimate,
per [[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]]) but pass through DIFFERENT filter
cascades:
- `gp-0x6abe`/`gp-0x6ac0`: single EMA (alpha=37/128) of `gp-0x4f50` -- a plain low-pass, DC gain 1,
  physically scaled to **4.7121 counts per column deg/s** (settled,
  [[reference_accord_gp6abe_column_degps_scale_settled]]).
- `gp-0x6c2c`: difference-then-double-EMA cascade (`FUN_00041464`, K1=37/128 @`0x415e8`, K2=22/64
  @`0x41640`, `0x4184e` final `>>9`) -- a broadband DIFFERENTIATOR/lead term with **~zero DC gain**
  (a sustained slow turn barely excites it) and gain RISING with frequency (3.08x@7.79Hz to
  12.1x@61Hz, no resonant peak). It behaves like a shaped acceleration/jerk signal, not a rate, and has
  no single fixed "counts per column deg/s" conversion -- its effective scale is frequency-dependent.

**Practical consequence for "drag when LKAS commands torque but the wheel turns slowly" (a low-frequency/
steady-state framing):** this specific lane (`FUN_00036c12`) is close to inert at DC/slow-turn rates
because its input is DC-blocked upstream -- it is much more relevant to fast transients/oscillations
(where the K1/K2 cascade's gain is largest) than to a sustained slow-turn drag sensation.

## Related
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]] -- the base trace this extends (mode-10
numbers there are now understood to be numerically-identical-by-coincidence to the correct mode-26
values, not a wrong table -- only the ADDRESS attribution was stale pre-TVCA4).
[[reference-accord-car-is-tvca4-mode-24-26]] -- source of the mode 24/26 identity this confirms.
[[reference_accord_gp6c2c_transfer_function_triple_verified]] -- source of the K1/K2 frequency-response
figures cited in section 6.
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] -- the companion damper
lane (`gp-0x6bd0`), independently re-confirmed the same session (sign relay at `0x3469e-0x346a2` is a
TRUE hard sign(gp-0x6abe) relay, no proportional blending -- single `cmp r0,r11`/`ble`/`subr r0,r8`
triplet, magnitude-independent).
