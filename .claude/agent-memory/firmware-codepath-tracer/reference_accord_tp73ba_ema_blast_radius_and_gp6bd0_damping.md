---
name: reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping
description: tp+0x73ba's EMA is fully contained inside FUN_0003b66a (2 reads only) and is wide open at 21Hz (~0.3dB atten); gp-0x6bd0 (FUN_00034350) is the literal DSP damping term, sign forced opposite gp-0x6abe, no LKAS-only decoupling point exists anywhere in this chain.
metadata:
  type: reference
---

**Q2-Q4 from the 2026-07-30 boost-index producer-chain task.**

## Q2 — tp+0x73ba (0xC63BA=512, byte-verified) blast radius and corner

Exhaustive Python byte scan (whole 1,048,576-byte `code.bin`, both LD and the confirmed ST opcode) plus
Ghidra `search_instructions`: **tp+0x73ba has exactly 2 real reads system-wide, both at `0x3b7ba` and
`0x3b7d4`, both inside `FUN_0003b66a`.** Zero writes (it's ROM calibration). The 6-hit list
`search_instructions` returns for the substring "73ba" includes 5 false positives (branch targets whose
hex address happens to contain "73ba") — always filter by mnemonic before trusting a substring match.

**Structure** (all inside FUN_0003b66a): a **2-stage cascaded integer EMA, same alpha=512/1024=0.5 both
stages**, applied to `4 * gp-0x4f60` (driver torque sensor B): `y1[n] = y1[n-1] + 0.5*(4*torque - y1[n-1])`
(state `gp-0x364c`, sole reader+writer both here), `y2[n] = y2[n-1] + 0.5*(y1[n] - y2[n-1])` (state
`gp-0x3648`, same). **Its blast radius is 100% contained in FUN_0003b66a** — neither `gp-0x364c` nor
`gp-0x3648` is read/written anywhere else, so this specific EMA's only effect is on `gp-0x6b9a`/`gp-0x6ba6`.
(NOTE: `FUN_0003b66a` as a whole still feeds the always-running base-assist boost curve, so the function's
OUTPUT is not LKAS-exclusive — see Q3.)

**21Hz attenuation, computed directly (not via -3dB corner approximation)**: `|H_single(2π·21/1000)|² =
0.25/(1-2·0.5·cos(0.132)+0.25) = 0.966`, cascade-squared `|H_total|² = 0.934` ⇒ **only ≈0.30 dB of
attenuation at 21 Hz — functionally wide open**, confirming the qualitative claim in STATE.md
("wide open at 21Hz") though my own -3dB corner calc (single stage ≈115Hz, cascade ≈73Hz) differs somewhat
from the previously-recorded "~120Hz for the pair" figure — the exact-frequency attenuation number above
is the one to cite, not either corner-frequency approximation.

## Q3 — no LKAS-only decoupling point found in this chain, and a structural reason why

Unlike V57's `0xC646C` (6 INDEPENDENT reader sites across 3 subsystems, decoupled by giving the LKAS
forward reader its own cell `0xC6CD0`), this chain has **no fork to decouple**: `gp-0x6abc`'s producer
(`FUN_00041464`, resolver-rate pipeline) and consumer (`FUN_0003b66a`, called unconditionally every
qualifying 1kHz phase-mask tick per `FUN_0002214a`) both run regardless of LKAS engagement, and
`FUN_0003b66a`'s sole output (`gp-0x6ba6`/`gp-0x6b9a`) feeds only the ALWAYS-ACTIVE base-assist boost
curve (`FUN_00034a72`) and the damping term (`FUN_00034350`) — neither gated on LKAS state (their
validity gates test `assist_substate`/`plausibility_ok`/sensor windows, never an engage flag). Physically:
by the time a signal reaches the resolver (motor electrical angle) or the torque sensor, LKAS-applied and
driver-applied torque have ALREADY been mechanically summed by the motor+column — there is no software
point downstream of the plant where they can be told apart. A genuine decoupling point would have to be
UPSTREAM, in the command-blend stage (`gp-0x6b3c`/`gp-0x6b4c`/`gp-0x6b98`), not in this
feedback/measurement chain. **Reported honestly as a negative result**, not an unexplored gap.

## Q4 — gp-0x6bbe vs gp-0x6bd0, and a magnitude-probe candidate

Two DIFFERENT cells get called "damping" in different places:
- **`gp-0x6bbe`** = the golden model's `base_driver_assist_lane()` output (`FUN_00034a72`, already fully
  modelled in `eps_lkas_chain_model.py`) — this is literally what V58's bit6 probed (0.00-1.10 sign
  transitions/s, DC-dominated). Its own architecture comment calls it "the boost curve proper," but the
  team is using "damping" for it in the sense of "does this dominant lane's response help or hurt the
  21Hz closed loop" — a physics framing, not a DSP one.
- **`gp-0x6bd0`** (`FUN_00034350`, byte-scan-confirmed sole producer, 3 static writes at `0x34730`/
  `0x34744`/`0x34752`) is the LITERAL DSP damping term: a product of up to 5 Q10-scaled mode-indexed LERP
  gains (one of them — table via pointer array `0xC9CCC[mode]` — is keyed on the SAME index `gp-0x6ba6`
  from Q1, a THIRD consumer table beyond the two boost-amplitude curves already on record) times a
  ceiling-clamped reference term (LERP via `0xC77A0[mode]` keyed on `gp-0x6ac2`, the counter-torque cell
  from Q1's array), with **its sign forced to `-sign(gp-0x6abe)`** (disasm `0x3469e-0x346a2`: `cmp r0,r11
  / ble skip / subr r0,r8` where r11=`gp-0x6abe`) — textbook velocity-proportional damping (opposes the
  filtered resolver rate). Because the sign is deterministic by construction, a sign-comparator probe on
  `gp-0x6bd0` would be REDUNDANT with probing `gp-0x6abe`'s sign, not new information.
- **Magnitude probe candidate**: the pre-sign-flip, pre-ceiling-clamp product (computed `0x34684-0x3469c`,
  four successive `mulu ...; shr 0xa` Q10 multiplies) or equivalently `|gp-0x6bd0|` itself — a thermometer
  on this, exactly mirroring V59's boost-index-depth design, would answer "how much authority does the
  literal damping term have during a 21Hz burst — is it near its ceiling or small?" This is UNBUILT;
  reported as a design candidate only, not implemented.

**Unifying structural finding**: both the boost-amplitude index (Q1, `gp-0x6ba6` derived largely from
`gp-0x6abc`) and the literal damping term (Q4, `gp-0x6bd0`, sign-locked to `gp-0x6abe`) key off the SAME
4-cell resolver-rate array from
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]] — different derived stages of one
underlying motor-rate signal, not independent mechanisms.

Method: Ghidra decompile+disasm of `FUN_00034350` (full function read) and `FUN_0003b66a`; exhaustive
Python byte scan (see the companion memory) for write-site counts; direct Python frequency-response
calculation for the EMA attenuation figure.

Related: [[reference_accord_boost_index_input_is_resolver_rate_not_torque]]
