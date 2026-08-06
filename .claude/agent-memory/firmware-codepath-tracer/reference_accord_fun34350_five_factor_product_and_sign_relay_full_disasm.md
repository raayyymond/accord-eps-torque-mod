---
name: reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm
description: FUN_00034350 (FactorA/B/C/D/E damper, gp-0x6bd0) fully disassembled byte-exact — the whole output is a FIVE-term product (FactorB x FactorC x FactorD x FactorE x sign(gp-0x6abe)) clamped by a 6th table (FactorF) into shadow pair gp-0x6bd0/gp-0x4cf2. Confirms and extends reference_accord_factorc_e_damper_full_trace_r24r26_parallel and reference_accord_gp6a5e_producer_chain_and_creep_zero_damping with exact addresses, plus a NEW find (the sign relay).
metadata:
  type: reference
---

**Entry point & goal**: full byte-level disasm of `FUN_00034350` (`0x34350-0x347b4`, stock `code.bin`),
answering "what turns off at low speed AND what is discontinuous near zero" for the 2026-08-05 5mph/
near-zero-angle localisation brief. [EVIDENCE throughout — `decompile_function` then `disassemble_function`,
per standing decompile-first rule.]

## The mechanism, address-exact
Output = shadow pair `gp-0x6bd0`/`gp-0x4cf2` (fault-checked via `FUN_0006b9fa` on mismatch, same pattern
as `gp-0x6CC4`/`gp-0x4D0C`). Computed as:

```
r8 = FactorB(idx=|torque-tracking index, gp-0x4f60-derived, stored gp-0x6bcc|) / 1024   [0xC9CCC[mode]]
r8 = r8 * FactorC(idx=gp-0x6a5e voted speed, gated gp-0x67f4==1, else unity) / 1024      [0xC9E9C[mode]]
r8 = r8 * FactorD(idx=gp-0x6a10 angle-tracking-error, gated gp-0x67fe in {1,2}) / 1024   [0xC9DB4[mode]]
r8 = r8 * FactorE(idx=gp-0x6ac0 |motor/column rate|, range-gated on gp-0x6abe) / 1024    [0xC9F84[mode]]
if (gp-0x6abe > 0) r8 = -r8                                    ; 0x3469e-0x346a2, hard sign relay
gp-0x6bd0/gp-0x4cf2 = clamp(r8, symmetric ceiling from FactorF(idx=gp-0x6ac2))           [0xC77A0[mode]]
```
Five mode-indexed ptr arrays confirmed by `read_memory` (5 pointers each, mode = `gp+0x63fd`):
`0xC9CCC`(FactorB), `0xC9E9C`(FactorC), `0xC9DB4`(FactorD), `0xC9F84`(FactorE), `0xC77A0`(FactorF).
LERP struct: `[count:u16][X0..Xn-1:u16][Y0..Yn-1:u16]`, pointer target = the `count` field itself;
below X0 → flat Y0; above X[n-1] → flat Y[n-1]; standard divq interpolation between.

## FactorC = the speed floor [EVIDENCE, fresh byte reads]
- mode0 → `0xCE528`: X=(1280,5120,8960,12800)ct=(20,80,140,200)km/h, Y=(0,950,1356,1606).
- mode10 → `0xD27BC` (fresh read of `0xD27BA`, matches prior memory byte-for-byte): X0=2240ct=35km/h.
Gate: `gp-0x67f4` (voted-speed-valid flag) must ==1 AND `gp-0x6a5e` in `[0,0x7d00]`, else **defaults to
UNITY (1024) not zero** — a sensor-fault does not silently kill damping, confirms prior memory.
**Because the whole thing is a PRODUCT, FactorC=0 forces the ENTIRE term to exactly 0** — not "reduced" —
at any speed below its X0, in every mode checked. At 8km/h (512ct) this holds for every mode inspected
(20 and 35 km/h both exceed 8).

## NEW: the sign(gp-0x6abe) relay [EVIDENCE, disasm 0x3469e-0x346a2]
```
0003469e: cmp r0,r11      ; r11 = gp-0x6abe (loaded 0x34604)
000346a0: ble 0x000346a4  ; if gp-0x6abe <= 0, skip
000346a2: subr r0,r8      ; negate the whole 4-factor product
```
A hard sign-flip on the FULL product at the exact zero-crossing of `gp-0x6abe` (column/motor rate,
4.7121 ct/(deg/s) per [[reference_accord_gp6abe_column_degps_scale_settled]]). Classic
`sign(rate)*magnitude(...)` friction/damping structure. **Currently inert whenever FactorC (or FactorD/E)
has already zeroed the product** — i.e. real, but silenced below the speed floor. Not previously on record.

## FactorE = near-zero |rate| dead-zone (second gate, same term)
mode0 → `0xCE550`: X=(70,450,1000,4000)ct, Y=(0,115,177,253) — max only 253/1024≈24.7%, never reaches unity.
mode10 (prior memory) → `0xD27F8`: X=(60,400,2500,4000), Y=(0,140,539,927). X0=60-70ct ≈13-15°/s: near-zero
but not literally 0 — a second, independent near-zero gate on the same output, on the RATE axis not angle.

## FactorD = confirmed flat/inert (re-derivation, matches prior memory)
`0xC9DB4[mode]`, idx=`gp-0x6a10` (angle-tracking-error), gated `gp-0x67fe∈{1,2} && <9999`. mode0 read
`0xCE4F8`: X=(0,50,100,200,400), Y=all 1024 (flat unity, no effect). Matches prior memory's mode10 read
(`0xD2774`, also flat 1024). No discontinuity here — a pass-through on this car's calibration.

## FactorB = torque-domain, not speed/angle (partial — index formula not fully hand-verified)
`0xC9CCC[mode]`, idx = a signed/abs quantity built from `gp-0x4f60` (the EMA torque index used broadly
elsewhere), `gp-0x6752` (static polarity), `gp-0x6c2e`, cals `tp+0x736c`/`0x736e`, stored to `gp-0x6bcc`.
mode0 read `0xCE4D0`: X=(0,2048,4096,6144), Y=all **4** (flat ≈0.4% of unity across its whole domain) —
a near-total attenuator regardless of index, at mode0. Mode10 NOT read this session — flag.

## Coarse-right-shift check (null result, one function only)
The 5 `shr 0xa` instructions in the product chain (`0x34688`,`0x3468e`,`0x34696`,`0x3469c`) are all
standard Q10 (1024=unity) fixed-point normalization after each `mulu` — 1 LSB ≈ 0.1% of full scale, NOT
a coarse quantizer. No relay-by-quantization found in this function. Not swept elsewhere in the chain.

## Findings
- [EVIDENCE] At 8km/h the entire `FUN_00034350` damping term is architecturally zero (FactorC alone
  suffices), independent of rate, tracking-error, or the sign relay — in every mode's FactorC table read.
- [EVIDENCE] A genuine sign(rate) relay exists in the same function but is downstream of, and currently
  masked by, the speed floor — becomes relevant only if/when FactorC's floor is lowered or removed.
- [BELIEF] This function (via `gp-0x6bd0`) is the single best-evidenced intersection of "speed-gated near
  8km/h" and "discontinuous near zero" found this session — see the 2026-08-05 near-centre hunt
  ([[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]]) for the two REJECTED
  angle-axis candidates (`0xC6B64`, boost-lane `gp-0x6a10` LERP) this supersedes as the leading candidate.

## Open questions / verification needed
1. GATE 2 at 18-22Hz specifically — prior phase data for FactorC/E is only at 7.79Hz (14-28°). Needs a
   fresh phase/magnitude measurement of this loop at the actual grind-#1 frequency before any lever.
2. `gp-0x6bd0` downstream consumers not re-enumerated this session (pull prior "FactorA seed" work first).
3. FactorB's index formula and FactorB/mode10's actual table (only mode0 read this session).
4. `FUN_0003ad74`'s `(0,640,3200,6400)ct` r24/r26 speed-blend table contents (0km/h vs 10km/h rows) not
   diffed — 8km/h sits mid-blend in the first segment, open whether the two tables differ materially.

## Related
[[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] [[reference_accord_gp6a5e_producer_chain_and_creep_zero_damping]]
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] [[reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles]]
