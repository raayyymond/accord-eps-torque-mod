---
name: reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26
description: gp-0x671a (the oscillation-reversal counter) has EXACTLY ONE writer image-wide (FUN_000428d4 @0x42a12, independently re-confirmed this session via fresh xref/disasm) and is read by AT LEAST the dead biquad's arm condition (FUN_000352b4@0x35a06) AND the r24/r26 rate-lane's "third arm" (FUN_0003aa2c@0x3aa70/0x3ac12) using the IDENTICAL threshold cal 0xC64FA=5. Per this kit's OWN prior on-car telemetry (V67: gp-0x671a>=5 measured 0.000% over 186,321 frames; V68: its precursor gp-0x67df measured 0.000% over 53,991 frames), this shared gate essentially NEVER opens in practice. CONSEQUENCE: (1) the r24/r26 cells 0xC6440/0xC643E are NOT virgin (extensively fought over V42-V88) and are independently re-confirmed UNREACHABLE, matching builds/v80_v107/build_v84_tva.py's own conclusion; (2) V103's dead-biquad arm may ALSO be gate-starved, meaning "f0 didn't move, confirming the small predicted effect" could be a null-on-the-gate, not a magnitude confirmation -- UNRESOLVED without checking gp-0x671a's actual value during route 0x9e specifically (V67/V68's zero-evidence predates the 6-8x gain era and is not itself proof for V103's drive).
metadata:
  type: reference
---

# `gp-0x671a` is a starved gate shared by the dead biquad AND the r24/r26 third arm — 2026-08-20

Found mid-`loop-lag-map` while checking an orchestrator-relayed proposal to halve `0xC6440`/`0xC643E`
("r24/r26 gains... both cal cells it reports virgin"). They are not virgin, and tracing why led to a
much bigger finding.

## Independently re-confirmed structure [EVIDENCE, fresh this session]

`search_instructions(operand_pattern="671a")` — 15 hits, adjudicated: exactly **one write**
(`0x42a12 st.b r7,-0x671a,gp`, inside `FUN_000428d4`) and reads inside `FUN_000352b4` (biquad,
`0x35a06`), `FUN_00035b20` (`0x35bea`), `FUN_00036c12` (`0x36c1e`), `FUN_0003a382` (PID, `0x3a4a6`),
`FUN_0003aa2c` (aggregator, `0x3aa70` — matches `builds/v50_v79/build_v63_tva.py`'s own cited r24-gate address
exactly), plus `FUN_000428d4`'s own two self-reads (`0x429c4`/`0x429d2`, computing its next value from
its prior one). `search_instructions(operand_pattern="67df")` — exactly 2 hits, both inside
`FUN_000428d4`: one read (`0x428e6`), one write (`0x4299c`) — confirms `gp-0x67df` (the FSM's
"left-neutral" precursor stage) is ALSO single-writer, same function.

**Two consumers' gate conditions independently confirmed identical**, both `cal(0xC64FA)=5`:
- Dead biquad (`FUN_000352b4`, this session's own earlier trace, `0x359fe-0x35a26`):
  `cal(0xC649B)==1 AND gp-0x671a >= cal(0xC64FA)=5`.
- r24/r26 "third arm" (`FUN_0003aa2c`, matches `builds/v50_v79/build_v63_tva.py`'s trace at `0x3AA70-0x3AA88` and
  `0x3AB64-0x3AC12` exactly): `gp-0x671a >= cal(0xC64FA)=5` selects `0xC6440` (r24) / `0xC643E` (r26)
  over the mode-indexed LERP default.

`FUN_000428d4` itself: a 3-state FSM on `gp-0x67df` (0=neutral, 1/2=excited each direction, entered
when `|gp-0x6c2c|` crosses a threshold `T` read from `tp+0x720a`), gp-0x671a increments/saturates off
that FSM's reversal count, capped near `cal(0xC64FA)=5`. Also gated by an early call to
`FUN_00046ea6(5)` (`0x428d8-0x428e2`) whose semantics were not traced this session — an early-return
path exists (`jr 0x42a76`) if that call's result is nonzero; NOT resolved what condition this is.

## The starvation evidence — ON-CAR, not just structural [EVIDENCE, relayed from build_v67/v68/v84_tva.py, not independently re-measured by me]

`builds/v50_v79/build_v67_tva.py`: `gp-0x671a >= 5` measured **0.000% over 186,321 frames** (routes 47 + 4a).
`builds/v50_v79/build_v68_tva.py`: re-aimed the SAME probe slot at the precursor `gp-0x67df != 0` specifically
because the `>=5` rung was frozen at 0; per `builds/v80_v107/build_v84_tva.py`'s later citation this ALSO measured
**0/53,991** on V68's own flown data. `builds/v80_v107/build_v84_tva.py` concludes explicitly: *"the state >= 5 arms
are dead in practice and a cell spent on them would buy nothing"* — and separately asserts
`0xC643E`/`0xC6440` at Honda-stock on that build, "NOT spent as a lever."

## Consequence 1 — the r24/r26 proposal is void as stated

`0xC6440` (r24 third arm, stock 2048) and `0xC643E` (r26 third arm, stock 1536) are **NOT virgin** —
touched by V42, V43, V57-V76 (explored extensively, "the rate lane" era), then reverted to stock and
asserted so on every build V81 onward including V88/V101/V102 (grep-confirmed, 24 files). They sit
BELOW two higher-priority arms (`gate_671d`/`0xC6442` for r24; a `gate_683c`-keyed arm, itself dead,
for r26) and ABOVE the mode-indexed LERP default — i.e. this is the SAME lane family as Lever B
(`0xC6446`, in the identical `R24_CALS` tuple), a different specific arm, extensively explored and
found dead by this exact mechanism. **Halving them prices at ~0 regardless of the new value, because
the gate that selects them almost never opens** — this is a structural finding, not a magnitude
argument. [BELIEF for "prices at ~0" — inherits the caveat below; EVIDENCE for "not virgin" and for
the gate structure itself]

## Consequence 2 — 🛑🛑 an open risk for V103's own headline result, NOT YET RESOLVED

If the SAME starved gate also governs the dead biquad (structurally confirmed — identical cell,
identical threshold cal), then **V103's biquad may never have actually run**, in which case "f0
didn't move (25.23 vs V102's 24.90, within the ±1.05Hz noise floor), confirming the small predicted
effect" is **potentially a null-on-the-gate, not a magnitude confirmation** — the same failure class
as `accord/builds/accord-v64-null-is-on-the-gate.md` and the CLAUDE.md standing design law about single-threshold
rungs with no positive control.

🛑 **NOT SETTLED, flagged not asserted**: the V67/V68 zero-evidence is from LOWER-GAIN builds (pre-4x
era), and V103 is a 6x-gain build with a reportedly much more diverse, aggressive drive ("high-speed,
low-speed, hard turns" per the operator's own route-`0x9e` report) — it is plausible, not established,
that `gp-0x6c2c` crosses the FSM's threshold `T` more often at higher delivered torque. **The clean
resolution is to check `gp-0x671a` (or a CAN-telemetered proxy for it, if one exists) directly against
route `0x9e`'s own telemetry** — this is the concrete next step, and it is decisive: if `gp-0x671a`
never reached 5 during route `0x9e`, the biquad result is uninterpretable and needs a re-fly with an
actual gate-duty probe before any coefficient (recentering or otherwise) is evaluated on it.

## 🛑🛑 CORRECTION 2026-08-20 (same day): V103 repoints the biquad's arm source — NOT starved on V103

Orchestrator found, and I independently re-verified via a direct Python byte read of BOTH
`stock_fw_dump/code.bin` and `_v103_V102BASE-BIQUAD.ENGAGED-CAVE...plain_image.bin` (not a relay —
read the actual bytes myself):

```
0x35A06  stock: 84 4f e7 98   v103: 84 4f fb 97   (ld.bu -0x671a,gp,r9  ->  ld.bu -0x6806,gp,r9)
0x35A12  stock: ec 49         v103: e0 49         (cmp r12,r9           ->  cmp r0,r9)
0x35A18  stock: e9 37 00 00   v103: ea 37 00 00   (setfnc r6            ->  setfne r6)
0xC649B  stock: 00            v103: 01            (arm cal: disarmed   ->  armed)
```
**Confirmed three independent ways**: (1) raw byte diff, direct file reads, both images; (2)
displacement arithmetic cross-check -- hw2 delta `0x98E7-0x97FB=0xEC=236` exactly equals
`gp-0x6806 - gp-0x671a = 26630-26394 = 236`, i.e. self-consistent regardless of the exact V850
bitfield transform; (3) full instruction-semantic re-derivation -- `cmp r0,r9`+`setfne` on a register
now holding `gp-0x6806` gives exactly `gp-0x6806 != 0`, matching `gp-0x6806`'s established identity as
the engagement flag (`== latActive` on 150,302/150,327 = 99.983%, per
`reference_accord_live_lkas_command_path_and_c63ec_lowpass.md`).

**⇒ V103's biquad arm is `cal(0xC649B)==1 AND gp-0x6806!=0` (engaged), NOT starved.** Route `0x9e` was
62.74% engaged (406.4s in 7 episodes) ⇒ the biquad ran for ~406 seconds on that drive. **The V67/V68
zero-duty prior (gp-0x671a>=5) is the correct prior for the STOCK gate and does not reach V103**, which
deliberately repoints the SOURCE register, not just the threshold -- that repoint was the actual
point of "Part A" of the V103 build. My original flag was the right METHODOLOGY (never trust a
coefficient-level result without checking gate liveness) applied to the wrong image; the r24/r26 kill
(§ above) is UNAFFECTED and stands -- `0xC6440`/`0xC643E`'s gate reads `gp-0x671a` directly and V103's
edit is local to `FUN_000352b4`, so that specific gate remains starved on every build including V103.

**What is UNAFFECTED by this correction**: the r24/r26 proposal kill (different gate, not repointed).
**What IS retracted**: the suggestion that V103's own "f0 didn't move as predicted" might be a
null-on-the-gate -- it is not; the gate is live and the small measured effect is a genuine, if
modest, magnitude result.

## Related
[[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]] — the notch pricing
this bears on; its own GATE-3 ringdown analysis is UNAFFECTED (structural, not duty-dependent), but
its implicit assumption that the arm condition fires during ordinary driving is now flagged, not
assumed. [[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]] — the
original biquad characterization; its own gate description is confirmed correct, just not confirmed
LIVE. `docs/BUILD-LINEAGE.md`, `builds/v50_v79/build_v63_tva.py`, `builds/v50_v79/build_v67_tva.py`, `builds/v50_v79/build_v68_tva.py`,
`builds/v80_v107/build_v84_tva.py` — the r24/r26 lineage this corrects a sibling's "virgin" claim against.
