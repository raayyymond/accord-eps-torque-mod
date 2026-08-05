---
name: reference_accord_gp6abe_column_degps_scale_settled
description: SETTLES an 8x ambiguity between two candidate scale constants for gp-0x6abe/gp-0x6ac0 (motor resolver rate) in column deg/s. CORRECTED 2026-08-04 -- 4.7121 counts/column-deg/s IS the right constant (P*G=56.5), confirmed by DIRECT DISASSEMBLY of the real CAN 0x14A/0x18F packers: 0x14A truly packs (-gp-0x6a56)>>3 via a separate cell gp-0x69ea (sole producer FUN_00040a50, exact negation), 0x18F packs -gp-0x6a56 unshifted. My own first-pass reading (0.589014, P*G=7.068) used the WRONG packer's LSB and is retracted below, kept for the record of how the error happened.
metadata:
  type: reference
---

# gp-0x6abe/gp-0x6ac0 to column deg/s -- the exact scale (2026-08-04)

## 🛑 RETRACTION, confirmed by direct disassembly of the real periodic CAN TX packers

My first pass below concluded 0.589014 (P×G=7.068) by assuming `gp-0x6a56` itself carries CAN
0x14A's rate field at LSB=1deg/s. **That was the wrong packer.** Direct decompile of the actual,
confirmed periodic TX functions (`FUN_00055a98` = 0x14A/330, `FUN_00057b24(...,0x14a)` literal
proves it; `FUN_00055c42` = 0x18F/399, `FUN_00057b24(...,399)` literal proves it) shows:

- `FUN_00055c42` (0x18F/399): `FUN_000218de(-*(short*)(gp-0x6a56))` -- packs **-gp-0x6a56, unshifted**.
- `FUN_00055a98` (0x14A/330): packs `(int)*(short*)(gp-0x69ea) >> 3` -- a **different cell**, `gp-0x69ea`,
  **with an explicit `>>3`**.
- `gp-0x69ea` has **exactly one writer**, `FUN_00040a50`, which sets it via
  `*(short*)(gp-0x69ea) = -*(short*)(gp-0x6a56)` (both write sites, byte-identical) -- **an exact
  negation, no other scaling.**

⇒ **`0x14A`'s raw field = `(-gp-0x6a56)>>3` -- team-lead's/FW-surface's "0x14A is the coarse, `>>3`
copy of 0x18F's fine field" is CONFIRMED, independently, from raw bytes, not just the fleet CAN
capture.** If 0x14A's raw value is LSB=1deg/s (the fleet-measured, externally-grounded value), then
`gp-0x6a56 = -8 × 0x14A_raw ≈ 8 × column_degps` (magnitude), giving:

**`gp-0x6abe = gp-0x6a56 / 1.698046875 = 8×column_degps / 1.698046875 = 4.7113 × column_degps`**
-- matching the kit's **4.7121** constant to 4 significant figures. **4.7121 is correct.
0.58901 (my first pass, and the "other candidate" the kit carried) is wrong by exactly 8x, because
it silently applied the FINE-field LSB to a value that is actually transmitted at the COARSE-field
LSB (0x14A).** `P × G = 12 × 4.7121 = 56.5` -- ordinary for a column-EPS worm/belt reduction
(e.g. P=4, G≈14.1 or P=3, G≈18.8), resolving the earlier "P×G=7.07 is implausibly small" flag.

## The two competing constants (ORIGINAL, retracted framing below -- kept for the record)

This kit's fleet-side regression work had produced two candidate scales for
"gp-0x6ac0 counts per column deg/s": **4.7121** and **0.58901** (exactly 8x smaller), without
resolving which was correct. [[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]]
supplied the corrected 4kHz ISR rate this session, which unlocked closing it from firmware bytes
alone -- no regression needed. **This section's CONCLUSION (0.589014 is correct) is WRONG -- see the
retraction above. The cal read (`0xC613A`=1159, `gp-0x6a56 = gp-0x6abe × 1.698046875`) is CORRECT
and unaffected; only which CAN field's LSB it should be measured against was wrong.**

## The exact firmware derivation [EVIDENCE]

`FUN_0003f776` -- the producer of `gp-0x6a56`, the value transmitted as CAN 0x14A/0x18F
STEER_ANGLE_RATE -- computes, verbatim from the decompile:

```
gp-0x6a56 = polarity(gp-0x6752) x ((gp-0x6abe * 0x30 * cal(tp+0x713a)) >> 15), clamp +/-12000
```

`cal(tp+0x713a)` = absolute `0xC613A`, byte-read (LE) = **1159**. So, exactly:

```
gp-0x6a56 = gp-0x6abe x (48 x 1159 / 32768) = gp-0x6abe x 3477/2048 = gp-0x6abe x 1.698046875
```

`analysis-2020accord/eps_lkas_chain_model.py` (lines ~1157-1158) documents CAN 0x14A's rate field
as **"factor 1" (deg/s)**, cross-validated (r>=0.985, slope 0.95-1.00) against the differentiated
angle channel on the same frame -- an externally-grounded (opendbc-style) physical scale, not a
value I chose. Taking `gp-0x6a56[raw] ~= column_degps` (unity LSB):

**`gp-0x6abe = column_degps / 1.698046875 = column_degps x 2048/3477 = column_degps x 0.589014...`**

This reproduces the kit's **0.58901** candidate to 5 significant figures, exactly, from firmware
arithmetic alone. ⇒ **0.58901 is the correct scale; 4.7121 was wrong by exactly 8x.**

## Combined P x G [EVIDENCE for the combining formula; VALUE corrected above]

Independently re-derived the combining formula (matches the team's own formula exactly):
`gp-0x6ac0 = 30 x f_electrical(Hz)` (this session's ISR-rate result) `= 30 x P x f_mech,motor(Hz)
= 30 x P x G x (column_degps/360) = (P x G / 12) x column_degps`, where `P` = pole-pair count,
`G` = motor:column mechanical speed ratio (>1 for a reduction).

**`P x G = 12 x 4.7121 = 56.5`** (using the corrected constant above) -- ordinary for a column-EPS
worm/belt reduction. The `7.068` figure computed in the retracted first pass used the wrong CAN
field's LSB and should not be used. **P and G individually remain unsplit** -- not needed per
team-lead (the product is all the rate-lane breakpoint conversion requires) and not pursued further
this session. If revisited: the CORDIC/resolver front-end (`FUN_00065afe`) and the motor-parameter
block (`0xC50D0-0xC5D84`) were checked for a standalone P or G literal and neither yielded one
(see "what was checked" below, unaffected by this correction).

## What was checked and did NOT yield P or G separately [EVIDENCE, negative]

- `FUN_00065afe`'s `&DAT_00006185`-gated block (MTPA/advance-angle correction, 12 floats at
  `tp+0x6000-602c`) is pure electrical-domain flux/voltage math -- no mechanical ratio found.
- `tp+0x6084` (0xC5084) = ~0.044f, used in a redundant-sensor consistency check -- not P or G.
- Byte-pattern scan of `0xC5000-0xC6000` for clean floats 2.0-8.0: `7.0f` hits only 3 addresses
  (`0x86B60`, `0xC6044`, `0xC6660`, uncontextualized); `4.0f` hits 16 places, at least one of which
  (`0xC5574`) is already attributed to an unrelated speed-clamp bound, not a pole count. Too many
  candidates to disambiguate without tracing each site's consumer -- not done this session.

## Consequence for the rate-lane damping-curve breakpoints (X=[0,400,1400,3000] on gp-0x6ac0)

Using the corrected **4.7121** scale: **400 -> 84.9, 1400 -> 297.1, 3000 -> 636.7 column deg/s**;
the 13001-count clamp fold -> **2,759 column deg/s**. (The separate `gp-0x6ac0 = 30xf_elec(Hz)`
relation is unaffected by this correction -- it only depends on the 4kHz ISR rate, not on P/G.)

## Related
[[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]] -- supplies the 30x scale constant
this derivation combines with the CAN-broadcast conversion.
[[reference_accord_c520c_cap_table_axis_provenance]] (user global memory, not this dir) -- its
1050-4100 domain converts via the *electrical-Hz* relation (unaffected), not this column-degps one.
