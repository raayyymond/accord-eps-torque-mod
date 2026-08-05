---
name: reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected
description: CORRECTS the FOC-loop-rate belief in reference_accord_foc_inner_current_loop_architecture.md. TSG20 carrier is 4.000 kHz not ~8kHz (PCLK=40MHz not 80MHz), TS0CTL2 confirms undivided PCLK, and TS0CTL5's runtime value (traced via a fault-mode dispatch table) shows the ADC/current-loop trigger fires once per carrier period at a dead-time-offset diagnostic compare point, not at peak/valley directly.
metadata:
  type: reference
---

# PWM carrier + current-loop rate, corrected (2026-08-04 session)

## The correction

`reference_accord_foc_inner_current_loop_architecture.md` assumed PCLK=80MHz "carried from the
OSTM0/control-task rate analysis" and concluded carrier ≈ 8kHz (or 16kHz). That 80MHz figure was
itself later shown wrong: [[accord-pclk-40mhz-and-ostm0-is-500hz]] derives **PCLK = 40.000 MHz**
two independent ways (CAN bit timing at 500kbps giving an exact Table-20-19 row; CLMA1 clock-monitor
config with the option-byte's legal-PCLK constraint) — and separately shows OSTM0 is NOT the control
tick at all. That correction was never propagated to the TSG20/FOC carrier number. Redone here.

## TS0CTL2 confirms undivided PCLK (EVIDENCE, disasm + SVD)

`FUN_0006c446` (TSG20 init) writes `_DAT_ffffcc78 = 0` — SVD offset `0x7CEA78` = **TS0CTL2**, field
`TS0CKS` = "0: PCLK, 1: PCLK gated by TSG2nCLKI". Value 0 ⇒ TSG20's counter runs at raw, undivided
PCLK — no prescaler.

## Carrier = 4.000 kHz (EVIDENCE)

`TS0CMP0` (period register, `0xFFFFCC58`) = `0x1388` = 5000 (unchanged from earlier trace).
`TS0CTL0.TS0MD` = 01 = HT-PWM (triangular up/down). One full carrier period = 2×5000 = 10000 PCLK
ticks. **40 MHz / 10000 = 4.000 kHz.** (Was previously reported ~8kHz off the wrong 80MHz PCLK.)

## TS0CTL4 = 0x160 (EVIDENCE, newly read — not in the older memory)

Offset `0x7CEA7C`. Bits: `TS0PRE`(8)=1 peak reload enabled, `TS0VRE`(7)=0 valley reload **disabled**,
`TS0PIE`(6)=1 peak interrupt enabled, `TS0VIE`(5)=1 valley interrupt enabled. Both peak AND valley
*interrupts* are armed even though only peak *reload* is — this does NOT by itself prove a
twice-per-period ADC sample; the actual ADC trigger source is TS0CTL5 (below), a separate register.

## TS0CTL5 (ADC trigger config) — runtime value traced via a fault-mode dispatch table (EVIDENCE)

`TS0CTL5` = `0xFFFFCC08` (encodes as `-0x33f8, r0` in raw disasm — **not resolvable by
`search_instructions` unless you search the raw `-0x33f8, r0` operand text; searching the resolved
hex address `cc08` returns zero, a textbook Ghidra r0-relative miss**).

- The ADC-complete ISR `FUN_0006404c` unconditionally clears it to 0 at entry
  (`0x6405c: st.h r0,-0x33f8,r0`).
- A **fault/mode-transition routine at `0x61806`-`0x61912`** (reached via a function-pointer/state
  dispatch table at `0xBC2B8`, entries `table[4..9]` = `0x61806/61866/61882/618c0/618d4/61912`;
  indexed by a byte at `gp-0x4e56` elsewhere) reprograms it per mode:
  - mode-1 branch (`gp-0x4e6d==1`, fault path): `TS0CTL5 = 2` = `TS0AT01` (peak-interrupt timing).
  - the "restore normal" branch (`0x618c0`): `TS0CTL5 = 4` = `TS0AT02` ("generate `TSnADTRG0` at
    `TSnDCMP0` match during increment").
- `TS0DCMP0W` (`0xFFFFCC5C`, offset `0x5C` = SVD `TS0DCMP0W` "Diagnostic Output Compare Register 0/1")
  is programmed at init from a ROM table (`FUN_00005932`-relative) scaled `×2 + 0x50` (+80, the
  dead-time tick count) — i.e. the ADC/diagnostic sample point is deliberately offset by one dead-time
  from a switching edge, a standard current-sense-blanking technique.
- `TS0CTL6` (`TSnADTRG1`, the second trigger channel) has **zero writers anywhere in the image** — a
  raw-operand byte scan for `-0x33f4, r0` found no hits in that pattern (all "33f4" hits were
  coincidental gp-relative/branch-target matches in unrelated functions). Confirmed by exhaustive
  `search_instructions` operand scan, 183,429 instructions. **Only TSnADTRG0 is ever armed.**

⇒ **In normal running the ADC/current-sample trigger fires once per carrier period, at the
dead-time-offset `TS0DCMP0` compare point (not center-peak/valley).** Combined with a single active
trigger channel (`TSnADTRG0` only), this settles the earlier "8kHz or 16kHz?" open item downward:
**the current-loop / FOC-ISR (`FUN_0006404c → FUN_00071272`) execution rate is 4.000 kHz**, not
8-16kHz. This also means `FUN_00068f52` (the resolver-angle differentiator feeding `gp-0x4f50` →
`gp-0x6abc/6abe/6ac0/6ac2`) samples the resolver at 4kHz, not the "8-16kHz" figure carried in
[[reference-accord-below-gp6b98-foc-delivery-path-swept]] — that memory's open item #3 (rate
transition analysis) should be re-run at 4kHz if revisited.

## Derived: `gp-0x6ac0` steady-state ≈ 30 × f_electrical(Hz) (EVIDENCE, arithmetic)

From [[reference-accord-c520c-cap-table-axis-provenance]]'s confirmed chain (`d` wrapped mod 16384
counts/electrical-rev, `raw = d*120000>>14`, ISR now known to be 4kHz not assumed):
`d = f_e(Hz) * 16384/4000` (one ISR sample's phase advance), so
`raw = d * 120000/16384 = f_e * 16384/4000 * 120000/16384 = f_e * 30` — the modulus cancels exactly.
The EMA (`gp-0x6abe`/`gp-0x6ac0`, gain 0xC643C=37) doesn't change steady-state DC gain, so
**`gp-0x6ac0`(settled) ≈ 30 × f_electrical(Hz)**. Sanity check: the `0xC520C` cap table's domain
(X: 1050→4100) corresponds to **f_e ≈ 35 Hz → 137 Hz electrical**, a plausible EPS-motor range.
⚠ This scale constant is now built on the CORRECTED 4kHz ISR rate — if a future session finds the
ISR rate is not 4kHz (e.g. TS0CTL5 is reprogrammed elsewhere beyond what this session found), this
"×30" constant must be re-derived.

## Open items
1. Who calls the `0xBC2B8` dispatch table / sets `gp-0x4e56` (the mode index)? Not traced.
2. `FUN_00005932`-relative ROM table feeding `TS0DCMP0W` — not decoded (likely a per-configuration
   or per-variant dead-time-offset table, not calibration-writable).
3. If `gp-0x4e6d` can be forced to 1 by anything reachable at runtime (vs. only at
   startup/fault-recovery), the TS0CTL5=2 (peak-trigger) path would apply instead — not ruled out.

## Related
[[accord-pclk-40mhz-and-ostm0-is-500hz]] — supplies the corrected PCLK this finding depends on.
[[reference_accord_foc_inner_current_loop_architecture]] — superseded on carrier/loop-rate only; its
FPU-census, motor-parameter-table, and "no isolated Kp/Ki" findings are unaffected and still stand.
[[reference-accord-below-gp6b98-foc-delivery-path-swept]] — its "8-16 kHz" ISR-rate assumption in
open item #3/#4 is corrected to 4 kHz by this memory.
[[reference-accord-c520c-cap-table-axis-provenance]] — supplies the raw/d/modulus arithmetic this
memory's ×30 scale constant is built from.
