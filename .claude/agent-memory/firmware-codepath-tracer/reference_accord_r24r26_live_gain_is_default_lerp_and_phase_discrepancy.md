---
name: reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy
description: r24/r26's live gain is the DEFAULT mode/speed/rate LERP table, not any of the four override cal cells (0xC6442/0xC6446/0xC6440/0xC6444/0xC643E) -- all confirmed dead/starved this session, closing the kit's O27. Mode 24/26 r24 tables read exact (byte-identical content, physically separate addresses -- an r24-only, mode-26-only edit is a genuine cal-only ENGAGEMENT-CONDITIONAL lever, r26 has no such option). 🛑🛑 A 229 phase discrepancy between the kit's "r24/r26 pumps" Re(Z) estimate (139.1 deg) and a same-day orchestrator loop-identification figure (r24+r26=0.1173∠-89.9 deg) is UNRESOLVED -- do not pick a sign for this lane until it closes.
metadata:
  type: reference
---

# r24/r26 live gain path, exact tables, and an unresolved sign contradiction -- 2026-08-21

Traced for the orchestrator's "is r24/r26 Honda's active-damping term, and is its live gain a cal
cell" question (V104-design-phase session, siblings `v104-biquad-io`/`v104-can-bits`). Full trace:
`docs/traces/TRACE-2026-08-21-r24-r26-as-active-damping.md`. GhidraMCP + independent Python LE32/byte scans
of `stock_fw_dump/code.bin`, all this session unless marked [RELAYED].

## 1. The live gain arm -- closes O27 (`handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` §8.1)

Fresh full `decompile_function`+`disassemble_function(0x3aa2c)` (`FUN_0003aa2c`, 168 instrs,
0x3aa2c-0x3ad74). r24's 4-way / r26's 3-way priority mux, all cal cells byte-read this session:

```
r24: gp-0x671d!=0 -> 0xC6442(1024) | gp-0x683c!=0 -> 0xC6446(512) | gp-0x671a>=cal(0xC64FA)=5 -> 0xC6440(2048) | DEFAULT: mode-indexed LERP
r26: gp-0x683c!=0 -> 0xC6444(512) | gp-0x671a>=5 -> 0xC643E(1536) | DEFAULT: FIXED (non-mode) LERP
```
Exact gate addresses this session: r24's mux at `0x3ab98-0x3ac16`; r26's at `0x3ab2a-0x3ab6c`; the
shared `gp-0x671a>=5` test at `0x3aa70-0x3aa8a` (`ld.bu -0x671a[gp],r12 / ld.bu 0x74fa[tp],r14 / cmp
r14,r12 / bc` -> r2=0 when 671a<5).

**All three override arms are dead/starved, confirmed BOTH structurally (this session) AND on-car
(relayed):** `0xC6442` written by 0/65 images + `gp-0x671d` reads 0/402,424 frames across 4 routes
[RELAYED, `BUILD-LINEAGE.md` RULE 4]; `gp-0x683c` zero `st.*` writers image-wide [RELAYED, multiple
prior sessions]; `gp-0x671a>=5` measured 0/186,321 (V67) + 0/53,991 (V68 precursor) [RELAYED,
[[reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26]]]. **⇒ the DEFAULT
mode/speed/rate-indexed LERP table is what's actually live, essentially 100% of the time, for BOTH
lanes.** This directly closes O27 ("G never pinned... decode curve-A's mode-indexed LERP at the real
operating point").

**Correction in passing to `reference_accord_r26_adaptive_lane_full_trace_and_sign.md`'s "hard
zero-force gate"**: tracing the raw branch at `0x3ab2a-34` shows the whole r26 block is skipped only
when BOTH `gp-0x6b5e!=0` AND the rare `gp-0x671a>=5` hold -- not `gp-0x6b5e!=0` alone. Since the
second condition is starved, this "gate" is in practice unreachable too, not merely present-but-rare.

`gp-0x671d`'s true identity remains as characterized in `docs/STATE.md:1776-1778` [RELAYED, not
re-decompiled this session]: a saturating rising-edge counter on a torque-residual/observer check
(`FUN_00041d56`), feeding DTC dispatch, reset only by `FUN_0003bcb2`'s resync -- consistent with, not
contradicting, the 0/402,424 empirical duty.

## 2. gp-0x4f62's formula, independently reconfirmed instruction-for-instruction

`decompile_function(0x7e74a)` (`FUN_0007e74a`, sole producer): 8-slot circular buffer of torque
samples + tick-timestamps; `gp-0x4f62 = (dt<1) ? 0 : 2*(T[n]-T[n-N])/dt`, `N=cal(0xC6C42)`. Byte-read
`0xC6C42=4`, `0xC61F6`(deadband)=3. Shadow-lockstep verified against `gp-0x4488` (`FUN_0006b9ee` on
mismatch) -- same redundancy-vote pattern as `gp-0x6b94`/`gp-0x4ce0`. Matches the kit's documented
formula exactly; N>=8 zeroes the derivative entirely (a built-in safety bound, not touched by anything
here).

r24 -> `gp-0x6ada` (`st.h` @`0x3ad5a`), r26 -> `gp-0x6adc` (@`0x3ad4e`), both summed with 8 other
lanes into `gp-0x6b94` at `0x3acc8-da`, clamped ±0x2800, shadow-verified via `FUN_0006b9fa`. ONE
shared `ld.b -0x6752[gp]` at `0x3ab78` for both lanes (odd parity, both). **Zero `gp-0x6806`
references anywhere in `FUN_0003aa2c`** -- read the full decompile text, not an xref-null; upgrades
"not engaged-gated" from relayed to independently reconfirmed at the CODE level (see §3 for the DATA
level, which is different).

## 3. The DEFAULT tables, exact -- and mode 24/26's r24 records specifically (not mode 10)

`FUN_0003ad74` (sole producer, confirmed this session via `search_instructions
operand_pattern="7a68"` -> exactly 1 hit, `FUN_0003ad74@0x3aecc`, `truncated:false` over 183,569
instrs) does a 2-stage LERP: speed-axis blend (cross-axis `0xC6010`=[0,640,3200,6400] = 0/10/50/100
km/h @64ct/km/h) between 2 of 4 ROM records, THEN (inside `FUN_0003aa2c` itself) a rate-axis LERP
keyed on `sVar20=min(|gp-0x6ac0|,0x32c8)` (4.7121 ct/(deg/s) scale).

**Mode 24 (manual/disengaged) / mode 26 (engaged), toggling on engagement edges** [RELAYED,
[[reference-accord-car-is-tvca4-mode-24-26]], V73's own on-car probe, 104,061 frames, 99.09%
lag-matched]. I read mode 24's AND mode 26's own record addresses/contents fresh (not mode 10, which
V69-V73 wrongly edited and which was already known-inert for this car):

```
                    mode24 addr   mode26 addr    X(cts)=0,400,1400-1500,3000   Y (Q10)              G=Y0/1024
0 km/h   (array1)   0xD6A9C       0xD7A88        0,400,1400,3000               3072,3072,2322,1536   3.000
10 km/h  (array2)   0xD6AD8       0xD7AC4        0,400,1500,3000               2560,2560,2246,1946   2.500
50 km/h  (array3)   0xD6B14       0xD7B00        0,400,1500,3000               2303,2303,2151,1947   2.249
100 km/h (array0)   0xD6B50       0xD7B3C        0,400,1500,3000               2150,2150,2049,1947   2.100
```
**Mode24≡mode26 byte-identical at all 4 breakpoints** -- new confirmation, extends
[[accord-stock-mode24-equals-mode26-damper-is-ours]] to r24's own table specifically. **Blast radius,
independent Python LE32 whole-image scan**: each of the 8 addresses has **exactly 1 pointer
reference**, at the expected array slot -- fully private, mode24 and mode26 are PHYSICALLY SEPARATE
flash records that merely hold equal values (editing one does not touch the other).

**G_r24 is flat at its plateau (Y0=Y1) for rate 0-~85 deg/s** (covers ordinary steering), ranging
**3.000× (creep) to 2.100× (highway)** -- tighter/more precise than the kit's prior "1-3×" placeholder
in [[reference_accord_r24r26_driver_torque_lane_reZ_estimate]].

r26's FIXED (non-mode-indexed) table re-confirmed byte-exact against the 2026-07-19 memory
(`0xC6A68/7C/90/A4`, X/Y arrays match digit-for-digit). Blast radius re-confirmed via
`search_instructions` (1 hit, `FUN_0003ad74` only). ⚠ A raw bare-halfword Python scan for `0x7a68`
found 6 coincidental hits elsewhere in the image (expected false-positive class for an un-adjudicated
2-byte pattern per this kit's own trap catalogue -- NOT treated as real xrefs; `search_instructions`,
which parses full instructions with base-register context, is the trustworthy count).

r26's full formula carries an EXTRA factor: `r26 = ((r1×a_smoothed)>>10) × gain_A >> 10`, where
`a_smoothed` = 2-tap boxcar of `gp-0x69a4`. Traced `gp-0x69a4`'s producer
(`disassemble_bytes(0x35520,0x355d0,dry_run:true)`, inside `FUN_000352b4`) far enough to confirm it is
forced to 0 outside a ±25600-count plausibility window on `gp-0x4f60`, else set from a DIFFERENT LERP
table at `gp-0x37fc` whose own ROM source was NOT chased down (time-boxed). **Still open -- matches
the orchestrator's own O28 exactly**, not newly closed by this session.

## 4. ⭐ NEW: r24 can be made engagement-conditional by a pure data edit; r26 cannot

Because r24's default table is mode-indexed and mode 24/26 are physically separate addresses (§3),
**editing ONLY mode 26's 4 records leaves mode 24 (manual) byte-stock** -- a cal-only,
engagement-conditional lever, despite `FUN_0003aa2c` itself never reading `gp-0x6806` (§2). **r26's
table is mode-flat -- no such option exists for r26.** r24 dominates r26 on 89.9% of engaged frames,
rising to 99.2% at 25-50 deg/s [RELAYED, `handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` §6.3, `b6`
comparator], so an r24-only/mode-26-only edit captures most of the lane while respecting the
operator's "don't touch manual/base steering" constraint as far as this firmware's structure allows.
GATE 1 (RAM) is trivial for either option -- pure cal data, zero cave, zero new state.

## 5. 🛑🛑 THE SIGN DOES NOT RECONCILE -- do not pick one without closing this first

Given (this session, [RELAYED] from the orchestrator's fresh loop-ID this same day, NOT independently
re-derived by me): `P=0.630∠163.0°`, `A=1+P=0.440∠+25.0°`, `ΔP=c·ΔG` with `|c|=13.09∠+145.3°`, and
`r24+r26 = 0.1173∠−89.9°` ("the aggregator budget"). My own arithmetic (checked twice, method is
mine, inputs are relayed): favorable `arg(ΔG) = arg(A)-arg(c) = 25.0-145.3 = -120.3°`. r24+r26's own
phase is fixed at -89.9° (real multiplier can't rotate it) -> RAISE gives ΔG phase -89.9°
(cos(30.4° offset)=+0.863, favorable); LOWER gives +90.1° (cos(210.4° offset)=-0.863, unfavorable).
**⇒ raising is favorable, by this arithmetic alone.**

**This does NOT reconcile with the kit's own "r24/r26 pumps at 6-9Hz" finding**
([[reference_accord_r24r26_driver_torque_lane_reZ_estimate]], same-day `gp-0x6752` correction):
`H_diff(7.79Hz)`(+84.39°) + `Z_measured`(-125.3°, route 77) = -40.9°, +180° for the polarity flip =
**139.1°**, `cos<0` -> PUMPING (`r24=-431...-1294 ct`). **139.1° and -89.9° are ~229° apart** -- NOT
0° (agreement) and NOT a clean 180° (I checked both alternate readings, `139.1-180=-40.9°` and the
pre-correction `-40.9°` itself, neither lands within 49° of `-89.9°`).

**My best-effort read, NOT confirmed**: these may be genuinely different axes -- `139.1°` is r24's own
mechanical-impedance (`Re(Z)`, driver-torque-derivative to wheel-rate) phase; `-89.9°`, inside a
`P=κG` closed-loop framework, is r24+r26's contribution to the open-loop gain SUM, which only reaches
the pole condition after an ADDITIONAL phase contribution from `κ` (motor/PWM/plant dynamics) that a
bare `Z`-piggyback doesn't carry. A term can pump in isolation (`Re(Z)<0`) while still being
"raise-favorable" for closed-loop margin -- these are not the same question and are not guaranteed to
agree. **I could not determine whether `0.1173∠−89.9°` is a fresh cross-spectral measurement or the
same `H_diff·Z_measured` piggyback the `139.1°` figure uses** -- if the latter, one of the two has an
arithmetic error worth finding; if the former, the disagreement may be real and the two quantities
legitimately different, in which case §5's "raise" answer and the kit's "pumps, so reduce" intuition
are simply not the same claim.

🛑🛑 **DO NOT ACT ON EITHER SIGN CONCLUSION UNTIL THIS RECONCILES.** Getting it backwards is the
kit's own stated 6.7× amplification risk. **What would close it**: the derivation behind
`r24+r26=0.1173∠−89.9°` (ask whoever computed it this session, likely still only in the orchestrator's
own context, not yet in a handoff file as of this trace).

V39's null (`r24` conditionally zeroed, neither symptom improved) does NOT reach this proposal:
touched r24 only via a cave hook (not this table) [RELAYED, `BUILD-LINEAGE.md` RULE 4], predates the
mode-24-vs-26 discovery, and per the kit's own V61 record "no build ever had both r24 and r26 dead" --
uninformative, neither clearing nor indicting.

## Related
[[reference_accord_r24_gainb_table_structure_and_priority_gate]] -- the original mux discovery this
session's fresh disasm reproduces exactly and extends with byte-exact mode24/26 tables.
[[reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26]] -- the starved-gate finding this
session's structural trace corroborates independently.
[[reference-accord-car-is-tvca4-mode-24-26]] -- the mode identity this session's engagement-conditional
finding depends on (relayed, not re-verified this session -- see open item C in the trace doc).
[[reference_accord_r24r26_driver_torque_lane_reZ_estimate]] -- source of the 139.1° pumping figure
this session's phase discrepancy is checked against.
`docs/handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` O27/O28/O31 -- the open items this session
closes (O27), partially advances (O31: GATE 1 done, GATE 2 still open), or leaves untouched (O28).
