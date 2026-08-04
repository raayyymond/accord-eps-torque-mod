---
name: reference_accord_gp68ad_field_dead_and_gp6d78_bit15_one_way_state4_cycle_refuted
description: Corrects reference_accord_state4_ratchet_and_gp67fa_state_graph.md's gp-0x68ad picture using the gp-0x6a5e=voted-speed reidentification -- gp-0x68ad can never be SET in the field (gp-0x679d and gp-0x437c are both permanently 0), and gp-0x6d78's sole writer is OR-only (never clears) -- so NEITHER the 4<->5 NOR the 4<->10 pathway supports periodic cycling in normal driving. Also independently confirms FUN_00034350's damping term is exactly zero below ~35 km/h.
metadata:
  type: reference
---

**Session 2026-08-04, ratchet-trace, following a team-lead priority redirect to re-derive the V42
state-4 governor-ratchet mechanism's natural period and test it against 7.79 Hz.**

Builds on and CORRECTS one part of [[reference-accord-state4-governor-ratchet]] /
`reference_accord_state4_ratchet_and_gp67fa_state_graph.md` (nested-path memory). That memory's
`gp-0x68ad` analysis was written before `gp-0x6a5e` was re-identified as VOTED VEHICLE SPEED (it called
`gp-0x6a5e` "fused/averaged column-torque magnitude"); it also left `gp-0x679d`'s own periodicity
untraced. Both are now closed.

## gp-0x68ad can NEVER be SET in the field [EVIDENCE, decompile of FUN_0001a104/FUN_00022034/FUN_00022016/FUN_000567c0]

`FUN_0001a104` (sole updater, called every cycle at the top of both state-4 and state-5 handlers):
```
bVar1 = gp-0x6a98 == 0
if ((FUN_00062c20()!=0 || gp-0x4e70!=0) && FUN_000197d0(0xf)!=1) {
    if (gp-0x68ad != 1) {
        if (gp-0x437c==1 && !bVar1) { gp-0x68ad = 1; return }   # SET path A
        FUN_00022034(); return                                    # SET path B
    }
    if (gp-0x4378!=1 || bVar1) { FUN_00022016(); return }        # CLEAR path
    # else: falls through
}
gp-0x68ad = 0   # unconditional clear
```
`FUN_00022034` (SET path B): `if (gp-0x679d==1 && (5-way OR)) gp-0x68ad = 1`.
`gp-0x679d`'s SOLE writer is `FUN_000567c0` @ `0x567e2` (25 access sites total, confirmed by
`search_instructions -0x679d`, one write). Its write logic:
```
bVar1 = (gp-0x67ba == 1)
uVar4 = bVar1 ? 1 : gp-0x67ba
if (!bVar1 && uVar4!=0) { uVar4 = FUN_0005d9c2() & 8 != 0 }
gp-0x679d = uVar4
```
`gp-0x67ba` has **exactly ONE access image-wide** (`search_instructions -0x67ba` = 1 hit, the read
inside `FUN_000567c0` itself) — **zero writers of any kind**, gp-relative or absolute (checked both;
`search_instructions fedf1846` = 0 hits, unlike `gp-0x437c`/`gp-0x4378` which DO have absolute-address
UDS-dispatch writers). It sits inside the documented zero-cleared RAM range. **⇒ `gp-0x67ba` ≡ 0 in the
field ⇒ `gp-0x679d` ≡ 0 in the field** (the `bVar1` branch needs `gp-0x67ba==1`, false; the `!bVar1 &&
uVar4!=0` branch needs `gp-0x67ba!=0`, also false — so `gp-0x679d` is written 0 every single call).

**Consequence:** SET path A requires `gp-0x437c==1` (per the prior memory, a UDS-artifact that is 0 in
the field). SET path B requires `gp-0x679d==1` (now shown ≡0 in the field). **Both SET paths are
therefore field-dead.** `gp-0x68ad` starts at its RAM zero-init and — because nothing in
`FUN_0001a104` can ever set it — **stays at 0 for the entire drive, always**, absent a diagnostic tool.

## Consequence for the {4,5} pair: the WHOLE pathway is inert, not "latched" [EVIDENCE]

`FUN_00019970` (state-4 handler, normal path): `if (gp-0x68ad != 1) return;` else `state=5`. With
`gp-0x68ad`≡0, this NEVER fires — **4→5 never happens in the field.**
`FUN_00019b10` (state-5 handler, normal path): `if (gp-0x68ad != 0) { hold; return }` else `state=4`.
Since state 5 can only be entered via the (also field-dead) 4→5 transition, or the diagnostic-only path
(`tp+0x74f9==0xAA`), **this pair is unreachable in the field, full stop** — it is not a chattering
5↔4 pathway tied to torque transients as the prior memory (built on the stale `gp-0x6a5e`=torque
reading) concluded; it is dead code in ordinary driving.

## gp-0x6d78 bit 15 (the 4↔10 pathway) is a ONE-WAY OR-only latch, not a toggle [EVIDENCE]

`search_instructions -0x6d78` = 15 access sites, **exactly ONE writer**: `FUN_000197b8` @ `0x197ca`,
decompiled as `gp-0x6d78 |= (1 << param1)` — **pure OR, no AND/clear path anywhere in the image.**
`FUN_00019970`'s normal-path 4→10 fires when `FUN_000197d0(0xf)==1` (bit 15 set); `FUN_00019d90`'s
normal-path 10→4 fires when `FUN_000197d0(0xf)==0` (bit 15 clear). **Since nothing can ever clear bit
15 once set, 10→4 can only fire if bit 15 has NEVER been set since the last full RAM clear (i.e. this
drive hasn't yet triggered whatever sets it) — once bit 15 sets, the SM leaves state 4 for state 10 (or
6/11) and cannot return via this path for the rest of the power cycle.** This is a one-shot drift, the
same shape as the already-documented `gp-0x671a` latch — not a periodic mechanism.

## ⇒ REFUTES the "state-4 entry/exit cadence explains 7.79 Hz" hypothesis as posed

Neither transition pathway back into state 4 supports periodic cycling in normal field driving. State 4,
once entered (from the normal 3→4 path, `FUN_00019888`@`0x19952`), is **STICKY**: it stays in state 4
every dispatch cycle until one of the ONE-WAY bit15/bit16/fault conditions fires (in which case it
leaves for 10/11/6 and, per the above, effectively never returns for the rest of the drive). **There is
no evidence at instruction level of a periodic re-entry into state 4**, so the specific relaxation-
oscillator framing ("period set by how fast gp-0x67fa cycles into and out of 4") does not hold up.

**What this does NOT kill:** if state 4 is entered once early in a drive and then persists (plausible —
untraced this session: what actually sets bit 15/16, and how often that happens mid-drive), the
governor's one-sided magnitude ratchet (`FUN_0004503c`, `0x454f8-0x455cc`, unchanged from the existing
byte-verified trace) would be **continuously active** for the rest of that drive, not periodically
re-armed. That reframes the candidate from a *relaxation oscillator* to a *continuously-present hard
nonlinearity inside a closed loop* — a limit-cycle question (loop gain/phase with the ratchet embedded),
not a period-from-arithmetic question. Full loop dynamics (plant response) are needed to settle that and
are OUT OF SCOPE for a Ghidra trace.

**A real tension worth carrying alongside:** the V42 substitution is asymmetric (clamps increases only,
passes decreases freely) — a continuously-active one-sided limiter driving an oscillation should print as
an asymmetric/rectified waveform. The existing route-4f measurement found the ratchet waveform
**symmetric** (skew −0.16..+0.06) with **no flat-topping** (crest 2.07–2.45 vs a sine's 1.414) — in
tension with a one-sided-clamp explanation for what is *currently* driving the observed oscillation,
though it does not rule out the substitution as a contributing/necessary-but-not-sufficient element.

## OPEN: what sets `gp-0x6d78` bits 15/16 and how often, mid-drive — NOT traced this session

`FUN_000197b8` has 21 callers image-wide; which ones pass param `0xf`/`0x10` and under what runtime
condition was not resolved (budget). This determines whether state 4 is sticky for a WHOLE drive
(bit 15/16 rarely/never fire) or gets kicked out partway through most drives. Next step if this thread
is picked back up: disassemble each caller's immediate operand feeding the `jarl 0x197b8` call.

## Byte-identity check against the CURRENT build [EVIDENCE, raw Python diff]

`0x454f8-0x45620` (the governor substitution), `0x197ea-0x1a200` (all ten state-dispatch handlers) and
`0x1a0c0-0x22200` (the whole `gp-0x68ad` chain incl. `FUN_0001a104`/`FUN_00022016`/`FUN_00022034`) are
**byte-for-byte identical between `stock_fw_dump/code.bin` and `_v70_plain_image.bin`** (0 diff bytes in
all three ranges) — this session's stock-based decompile applies unchanged to the current build.
`0x454FE` (`ba65` = `bne`, the V42 substitution site) sits inside the single giant linked-list CRC block
`[0x13000, 0xC4FFC)` (the bridged main block), which CRC-passes on both images.

## Bonus, independently confirmed: FUN_00034350's damping term is EXACTLY ZERO at the ratchet's speed range [EVIDENCE]

Fresh byte read, `0xD27BC` (mode-10 FactorC LERP record): `04 00 c0 08 00 0f 00 14 00 23 00 00 eb 00
ae 01` → count=4, X=[2240,3840,5120,8960], Y=[**0**,235,430,...] — matches team-lead's cited table
exactly. **Correction to how it's indexed**: the decompile of `FUN_00034350` shows this LERP (pointer
array `0xC9E9C`, mode-indexed) keyed on `gp-0x6a5e` — **voted vehicle speed** (the same corrected
identity as everywhere else in this kit), not driver torque. `X[0]=2240` counts ÷ 64.0625 counts/km/h
≈ **34.97 km/h**, matching the "~35 km/h" figure exactly, via the corrected variable.
The five-factor product (`FUN_00034350`'s tail: `((((seed*FactorC)>>10)*FactorD)>>10)*FactorE>>10`) is
**straight multiplicative in Q10** — a single zero factor zeroes the whole chain regardless of the
other four. **⇒ `gp-0x6bd0` (base-assist damping) = 0 exactly whenever voted speed < 2240 counts.** The
ratchet's entire observed range (4.9–8.0 km/h ≈ 314–512 counts) sits 4.4–7.1× below that threshold.
**"Zero restoring force" (not wrong-sign active anti-damping) is a live, freshly-confirmed candidate**
for what sustains the oscillation once excited — gain is provably 0 there, independent of phase, so the
sign-vs-`gp-0x6abe` question is moot for THIS operating point (it only matters if the gate were ever
opened, e.g. by a future speed-threshold edit).

See [[reference-accord-state4-governor-ratchet]] (the mechanism this corrects one part of),
[[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]] (gp-0x6abe's phase, not
re-derived at 7.5 Hz this session — flagged BELIEF-level open item).
