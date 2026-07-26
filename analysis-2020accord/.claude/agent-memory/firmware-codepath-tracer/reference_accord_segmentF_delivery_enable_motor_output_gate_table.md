---
name: reference-accord-segmentF-delivery-enable-motor-output-gate-table
description: 2026-07-06 SEGMENT F — delivery SM (m_steer_torque_limit_and_pack FUN_0002b422), ENABLE byte gp-0x67a4 full producer FSM, distribute_clamp constants re-verified, gp-0x4f68 LERP-axis role in the 0x2bc00 region, a SECOND (previously undocumented) writer of gp-0x6b3c, and a candidate CAN motor-telemetry packer FUN_00059912. CORRECTS segmentE memory's gp-0x67a4 absolute address (0xFEDF195C is WRONG; correct is 0xFEDF185C).
metadata:
  type: reference
---

# Segment F — delivery SM / ENABLE gate / motor distribute-clamp / motor output — gate map

2026-07-06 tracer pass, `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (STOCK), r2 5.5.0 **v850.gnu** plugin.
gp=0xFEDF8000, tp=0xBF000. Every address below independently re-derived by direct `pd` at the exact
address (not trusted from raw-byte-grep hits alone — several grep hits were mid-instruction false
positives, discarded after direct disasm; see method note at bottom).

## ⚠ CORRECTION to segmentE's memory: gp-0x67a4 absolute address

`reference_accord_segmentE_arbitration_shaper_dtc_gate_table.md` states **gp-0x67a4 (ENABLE byte, abs
`0xFEDF195C`)**. This is an arithmetic slip. Verified independently via r2 calculator AND python:
`0xFEDF8000 - 0x67A4 = 0xFEDF185C`, NOT `0xFEDF195C` (`0xFEDF195C` = `gp-0x66A4`, a different byte, one
that also happens to be the address named in the older `reference_accord_driver_override_plausibility_eme.md`
— these are two DIFFERENT gp-offsets, 0x100 apart, and should not be conflated). The **instruction
reference** in segmentE's note (`st.b r14,-26532[gp]`@`0x2b51e`) is itself correct and matches this
session's finding exactly — only the hex conversion to an absolute address was wrong. **gp-0x67a4 =
0xFEDF185C is the correct absolute address; use this going forward.**

## ENABLE byte gp-0x67a4 (0xFEDF185C) — single reader, single direct-store writer, full producer FSM [V]

**Reader (1, whole-image byte-pattern search):** `FUN_00028ea6` (arb) @`0x2a222` (`ld.bu -26532[gp],r12`).
Compared to 2 and 3 (`cmp 2,r12`/`cmp 3,r12`, `0x2a22e`/`0x2a234`) → boolean r13 (1 iff ENABLE∈{2,3}) →
gates the sole write to `gp-0x6b3c` (LKAS-only final torque, `0xFEDF14C4`) at `0x2a2ea`
(`st.h r16,-27452[gp]`, r16 = `cmovz(r13==0, 0, r1)` — r1 is the clamped `(GAIN[tp+0x746c]×polarity[gp-0x6752]×
combined)>>15` value, clamped ±`tp+0x71b4`[=0xC61B4=512] BEFORE the enable check). **So `gp-0x6b3c = (ENABLE∈{2,3})
? clamp(gain×combined,±512) : 0` — confirms the boot-card claim exactly, instruction-verified.**
`gp-0x6b38` (`0xFEDF14C8`, `-27448[gp]`) is written UNCONDITIONALLY with the un-gated r1 value at `0x2a23c` —
this is the raw/ungated mirror consumed elsewhere (see below).

**Writer (1 direct store, whole-image byte-pattern search):** `FUN_0002b422` (`m_steer_torque_limit_and_pack`)
@`0x2b51e` (`st.b r14,-26532[gp]`). r14 is the output of an **8-state (S=0..7) handshake dispatch** keyed on
persistent state `gp-0x3D28` (`0xFEDF42D8`, read once @`0x2b450`) with a `switch`-like cascade @`0x2b460-0x2b480`:

| state S | target | consumes | produces (ENABLE r14 / next-state S) |
|---|---|---|---|
| 0 | `0x2b516` | — | ENABLE=0, S:=1 (unconditional reset) |
| 1 | `0x2b484` | AUX3=`gp-0x185F`(`-26529[gp]`), AUX1=`gp-0x1859`(`-26535[gp]`) | AUX3==5 → shared w/ S=3 (ENABLE=5,S:=2); else AUX1!=1 → ENABLE=0 (S unchanged); AUX1==1 → ENABLE=1, S:=3 |
| 2 | `0x2b49e` | AUX3 | AUX3!=0 → ENABLE=5 (S unchanged); AUX3==0 → goto S=0 reset |
| 3 | `0x2b4ac` | AUX3 | AUX3==5 → ENABLE=5, S:=2; AUX3==3 → ENABLE=2, S:=6; else → ENABLE=1 (S unchanged) |
| 4 | `0x2b4fc` | AUX3, AUX1 | AUX3==0 → shared w/ S=6 (ENABLE=4, S:=5); AUX1==1 → ENABLE=3 (S unchanged); else → ENABLE=4, S:=5 |
| 5 | `0x2b4ee` | AUX2=`gp-0x185E`(`-26530[gp]`) | AUX2!=1 → ENABLE=4 (S unchanged); AUX2==1 → S:=7 (ENABLE stays 4) |
| 6 | `0x2b4d0` | AUX3, AUX1, r6=`gp-0x185D`(`-26531[gp]`) | AUX3==0 OR AUX1!=1 → ENABLE=4,S:=5; r6==1 → ENABLE=3,S:=4; else → ENABLE=2 (S unchanged) |
| 7 (or any unhandled) | `0x2b516` | — | falls to the S=0 reset |

**ENABLE takes values {0,1,2,3,4,5} — only 2 and 3 pass LKAS torque.** This is a richer picture than
segmentE's "r14 fed from 0x2b506/0x2b512/0x2b51c → 3/4/0" summary (that captured 3 of the ~7 branch
targets); the full dispatch has 8 state-entry points. Matches the framing in
`SESSION-2026-05-30-EME-RESOLUTION.md`: "gp-0x67a4=torque-blind handshake" — this IS a handshake/sequencing
FSM, not a simple boolean.

**gp-0x185D is forced to 1 unconditionally every cycle by the arb function** (`FUN_00028ea6`@`0x2a2f4`,
`st.b r11,-26531[gp]`, r11=1, right after the ENABLE-gated `gp-0x6b3c` store) — so in steady state the S=6
sub-check `r6==1` is essentially ALWAYS true (transitions S:6→4, ENABLE:=3), UNLESS `limit_and_pack` runs
before arb has had a chance to write it that cycle (ordering-dependent edge case, not further traced).

**AUX3 (`gp-0x185F`) writer found:** `FUN_0002b57a` (the "channel_router" callback launched from inside
`limit_and_pack` after `distribute_clamp` returns) @`0x2b560` (`st.b r10,-26529[gp]`) — r10 there is a
per-channel commit/ack byte from a counter-wraparound check. **AUX1/AUX2 (`gp-0x1859`/`0x185E`) writer found:**
inside the function immediately preceding `limit_and_pack` (see next section) — both forced to fixed
values (0/1-ish) as part of an init/reset path. **Full external-signal semantics of AUX1/2/3 (what real-world
condition ultimately drives the handshake forward vs. resets it to 0) are NOT fully resolved — this would need
tracing `FUN_0002b57a`'s full body and its own caller context, which is adjacent-segment/channel-router
territory.**

## NEW FINDING — a SECOND writer of gp-0x6b3c exists (corrects "1 writer" in prior memory) [V, mechanism partially open]

The function immediately preceding `limit_and_pack` in the binary (starts `0x2b35a`, ends `0x2b420` with
`jmp[lp]` — ONE function, not two; earlier framing in this session's own notes above briefly treated it as
two, corrected here) does:
1. Re-reads ENABLE `gp-0x67a4` @`0x2b35e` (`ld.bu -26532[gp],r13`) and a companion byte `gp-0x679E`
   (`-26526[gp]`) @`0x2b35a`, computes a **driver-assist blend gain** into `gp-0x697E` (`0xFEDF6982`):
   unity `1024` when ENABLE ∉ {2,3} (`0x2b384-0x2b38c`), else a LERP blend of cal `tp+0x73DA/73DC` or
   `tp+0x73DE/73E0` (same cal family the arb function ALSO uses for an apparently-duplicate blend calc
   @`0x2a24c-0x2a296` — likely tangential to driver-assist, not LKAS-specific; not traced further, out of
   segment).
2. Reads **deliver flag `gp-0x6809`** (`0xFEDF17F7`, the segmentE-documented engage-SM output) @`0x2b3de`
   (`ld.bu -26633[gp],r8`) and derives a boolean r8 = (deliver_flag != 0).
3. Writes `gp-0x1859`(AUX1):=r8-boolean, `gp-0x185E`(AUX2):=1, `gp-0x185D`:=1 (all unconditional, @`0x2b402-0x2b410`).
4. **Directly (re-)writes `gp-0x6b3c` @`0x2b41c`** (`st.h r15,-27452[gp]`): `r15 := 0` if a flag `r16`
   (set earlier in step 1, correlated with — but not proven identical to — the ENABLE∈{2,3} test) is 0;
   else `r15 := gp-0x6b38` (the UNGATED clamped command).

**This is a genuine second writer of `gp-0x6b3c`, contradicting the "1 writer (arb)" claim in
`reference_accord_arbitration_limit_family.md` / segmentE's boundary-variable note.** Whether it is a
harmless idempotent re-assertion of the SAME gated result (r16 derived from the identical ENABLE check, so
it would agree with arb's own write every cycle) or represents a genuinely independent bypass path is
**NOT fully resolved** — r16's exact derivation across both of step-1's branches needs a full re-walk, and
neither this function's name/start-of-function marker nor its caller could be resolved via r2 `axt`
(call-xref DB not built for this raw image, consistent with prior sessions' documented tooling limits).
**Flag for next session: if a future build ever touches the ENABLE gate or `gp-0x6b3c`, re-verify this
second writer doesn't reintroduce delivery on a code path the arb-side edit didn't anticipate.**

## Motor distribute-clamp `FUN_00025c32` — constants RE-VERIFIED live [V]

Struct fields (built by `limit_and_pack` @`0x2b522-0x2b538`: `[0]`=1 source idx=LKAS, `[1]`=ENABLE-state r14,
`[2]`=0, `[4]`=clamped torque, `[6]`=0, `[8]`=0, `[10]`=r16, `[12]`=r9, `[14]`=1024) get clamped in
`FUN_00025c32` @`0x25c60-0x25cec`:
- `+2` → clamp **±0x4000 (16384)** (`0x25c84/8a/94`)
- `+4` → clamp **±0x2800 (10240)** — **this is the LKAS lane** (`0x25ca0/a6/b0`)
- `+6` → clamp **±0x384 (900)** (`0x25cbc/c2/cc`)
- `+8` → clamp **±0x4e20 (20000)** (`0x25cd8/de/e8`)
All four exactly match `reference_accord_arbitration_limit_family.md`'s prior-session claims — independently
re-derived this session, byte-identical.

## gp-0x4f68 (0xFEDF3098) uses in the "0x2bc00 region" [V — 7 confirmed reads in-region, ~37 total image-wide]

Whole-image byte-search (`/x 99b0`, the raw disp16 pattern) → **37 total occurrences** across the whole
program (confirms this is a widely-consumed runtime signal, not delivery-region-local). Within the
0x2bc00-0x2be10 delivery/limit region specifically, **7 confirmed `ld.hu -20328[gp],rX` reads**: `0x2bc02`,
`0x2bc36`, `0x2bc46`, `0x2bcd6`, `0x2bd4e`, `0x2bd82`, `0x2bdc4` (+ 2 more just outside, `0x2c50a`/`0x2ccba`,
bringing the boot-card's "~10x" estimate in line). **Role in this region: gp-0x4f68 is used as a LERP-AXIS /
breakpoint-search input**, not a simple threshold compare — at the shared landing point `0x2bdc2-0x2bdcc`:
`sld.hu 0[ep],r7` (table breakpoint) ; `cmp r7,r28` (r28=gp-0x4f68) ; `bh 0x2bdd4` (branch if breakpoint >
signal) feeding an accumulator build (`gp-0x42E0`/`gp-0x42DC`). Multiple entry points (mode bytes 2/4/6
written to `gp-0x3CE1`=`0xFEDF431F` at various branches) all funnel through a shared `jr 0x2bdde` landing —
this reads as a **mode-dispatched, gp-0x4f68-indexed LERP limit/curve lookup**, structurally consistent with
a **speed- or rate-dependent limit table** (this is a DIFFERENT function/region than `FUN_0003d04c`'s Gate 5
threshold-compare of the SAME variable against cal `0xC61EA`=4096, and different again from the adjacent
`gp-0x4f64` governor read in the shaper @`0x43ae4`, three bytes apart, easily confused — verified distinct:
`-20328[gp]`=`gp-0x4f68` vs `-20324[gp]`=`gp-0x4f64`).

**Identity now RESOLVED by segmentD (this session, parallel tracer):** `gp-0x4f68 = clamp(ABS(gp-0x4f60),
0,65535)` = unsigned COLUMN ANGULAR VELOCITY magnitude, writer `FUN_0007f3f8`@`0x7feca` (see
`reference_accord_segmentD_fun3d04c_full_gate_map.md`). This is consistent with what I found here: a
velocity/rate signal is a natural fit for a LERP-axis into a rate-dependent limit table, and for
`FUN_0003d04c`'s threshold framing (a rate-plausibility gate, cal 4096 = 16% of the ±25600 signal window per
segmentD = HIGH bump-trippability).

## Motor output / candidate CAN telemetry packer `FUN_00059912` [V structure, CAN-ID NOT confirmed]

Downstream of the shaper (`gp-0x6b98`), the documented FOC chain (`FUN_000370b6`/`FUN_0003b8f6`/
`FUN_00056420`/`FUN_0007c4f2`) drives the on-chip current regulator ending in the carrier-valley ISR
(`FUN_0001492a`→`FUN_00061614`→`FUN_0006c5ce`) which writes the **TSG20 hardware PWM compare registers
`CMPU/CMPV/CMPW` = `0xFFFFCCB0/B4/B8`** (per prior-session `TORQUE_PATH_AND_TABLE.md` §1⑤, re-cited not
re-walked this session).

**New this session:** `FUN_00059912` (a generic multi-message CAN/serial frame packer, `switch r7` dispatch
over ≥15 message-type indices, `r7` param range-checked 0-14 @`0x59922-0x59924`) has a **case body @
`0x5994a-0x59984`** that reads the SAME THREE ABSOLUTE ADDRESSES via `movea` (NOT gp-relative): `-13136`=
`0xFFFFCCB0`(CMPU), `-13132`=`0xFFFFCCB4`(CMPV), `-13128`=`0xFFFFCCB8`(CMPW) — i.e. it **packs the live
TSG20 PWM compare-register snapshot (bytes 0-5 = CMPU/V/W low+high, bytes 6-7 zeroed) into an outbound
message buffer** pointed to by `r26` (the function's first param). This is a strong STRUCTURAL candidate for
a motor-telemetry CAN frame (plausibly the Accord's `0x427`-class MOTOR_TORQUE-equivalent), but:
- **CAN ID binding NOT confirmed.** `axt` found zero callers (consistent with documented tooling limits —
  likely invoked via an indirect function-pointer table, matching the RX-side dispatch pattern), and a
  literal-pointer search for `0x00059912` as a 4-byte LE value found zero hits (not stored as a raw pointer
  either, or referenced via a computed/relative table instead).
- **Implication for "is the cut upstream of the motor clamp":** if this packer IS the motor-telemetry
  packer, it reads registers that are the LAST stage after all upstream gates (ENABLE byte, distribute_clamp,
  mixer, governor, shaper SM1/2/3 authority-gate, hard-DTC motor-off) have already had their effect — there
  is no further clamp AFTER this capture point. So **any upstream LKAS cut necessarily shows up already-
  reflected (already zeroed/reduced) in this telemetry**, mechanistically supporting (not proving, pending
  CAN-ID confirmation) the "MOTOR_TORQUE tracks the already-zeroed LKAS term, the cut is not a separate
  downstream clamp" framing from the boot card.

## Civic-0x137F2 analog verdict

**Best candidate: the arb OUTPUT gain (`tp+0x746c`=`0xC646C`, stock 891) + immediately-following clamp
(`tp+0x71b4`=`0xC61B4`, stock 512)**, both read in `FUN_00028ea6` right before the ENABLE gate (`0x2a1ee-
0x2a204`, re-observed this session, matches `reference_accord_lkas_delivery_and_governor.md` exactly). This
is the closest structural analog to Civic's `0x137F2`: a single early calibration-driven attenuation that
silently discards the overwhelming majority of the theoretical full-scale range (891/32768 Q15 ≈ 2.7%, and
the immediately-following ±512 clamp is far tighter than every downstream wall — ±2800 distribute, ±2800
mixer, governor ~4762, ±2000/±8192 shaper) BEFORE any of the mode/gear LERP tables or state-machine gates
apply. Unlike Civic's clamp (a hard truncation of an already-computed value), the Accord's binder is
predominantly a **gain**, not a clamp — the ±512 clamp itself is rarely the active constraint (891×15360>>15
≈ 418 < 512, so the clamp has ~18% headroom over the gain-limited nominal value) — so the PRIMARY silent
discard is multiplicative (the gain), with the clamp as a backstop. This nuance (gain vs clamp) is the one
place the Accord's mechanism diverges from Civic's framing; flagged explicitly rather than force-fit.

## Method note — a grep pitfall this session, and how it was caught

Raw-byte pattern search (`/x <2-byte disp16 pattern>`) is a fast candidate-discovery method (used
extensively this session to find all readers/writers of `gp-0x67a4`, `-0x185D/E/F`, `gp-0x4f68`), but
**several hits decoded to nonsense (`divh`, `not lp,gp`) when disassembled directly at the hit address** —
these were NOT false matches of the byte pattern, they were genuine occurrences of the same displacement
bytes but **starting 2 bytes EARLIER** than the reported hit offset (the hit position lands inside the
disp16 field of a 4-byte instruction, so the real instruction start is `hit_addr - 2`). Every "garbage"
result was re-checked by disassembling from `hit-2`, which recovered the real instruction in most cases and
correctly ruled out a few genuine false positives (`0x6b7c8`/`0x6b844`, generic byte-shuffling code with a
coincidental 2-byte match, confirmed NOT ld/st of our target even at `hit-2`). **Lesson for future sessions:
always check both `hit` and `hit-2` before accepting or discarding a raw-byte-search candidate.**

## Related
[[reference-accord-lkas-delivery-and-governor]] · [[reference-accord-arbitration-limit-family]] ·
[[reference-accord-segmentE-arbitration-shaper-dtc-gate-table]] ·
[[reference-accord-segmentD-fun3d04c-full-gate-map]] · [[reference-accord-override-snap-state-machines]]
