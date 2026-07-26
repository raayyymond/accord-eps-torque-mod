---
name: reference-accord-segmente-arbitration-shaper-dtc-gate-table
description: Consolidated SEGMENT E gate map (2026-07-06 tracer pass) — every point in arbitration FUN_00028ea6, re-engage manager FUN_0002a30e, rate-shaper FUN_00042af8 (soft-EME SM2/SM3), and float watchdog FUN_00043e44 (hard-DTC 0xF00049) that can zero/clamp/wind-down/fault-latch the LKAS term or merged command. Synthesizes prior sessions' scattered verified memories into one gate table + re-confirms the load-bearing addresses fresh via r2 v850.gnu this session.
metadata:
  type: reference
---

# Segment E — arbitration / command-merge / soft-EME rate-shaper / hard-DTC corridor — full gate map

2026-07-06 tracer pass. Bases `gp=0xFEDF8000`, `tp=0xBF000`. Tool: r2 5.5.0, **v850.gnu** plugin (default v850
mis-decodes). Program: `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (STOCK). This file **consolidates** —
does not replace — the many prior per-function memories it draws on (linked at bottom). Roughly 15 of the
~25 claims below were freshly re-verified this session by direct r2 disasm/byte-read (marked [V-2026-07-06]);
the rest are carried from prior sessions' own [V]-tagged instruction-level work (marked [V-prior], still
disasm-grounded, just not re-walked by me this session) or are structural inference (marked [I]).

## Scope boundary (what this file does NOT cover)
Out of segment: the engage-SM decider `FUN_00040d58` (gp-0x6a62≥cal 0xC6312, gp-0x6cc4 angle-consensus vs cal
0xC6354) — the "gentle EME" lineage V32-V35, and the deliver-commit `FUN_0003d04c` (7 pre-gates incl. gate 7
`gp-0x6a5e≥cal 0xC62FE`). Those belong to the engage-SM/deliver-commit tracer. This file starts at the deliver
flag `gp-0x6809` (their output) and covers everything from there through merge, soft-EME shaper, and the DTC
corridor watchdog.

## The three failure classes in this segment

| class | mechanism | what's cut | DTC? | driver steering |
|---|---|---|---|---|
| **gentle-EME** | engage-SM decider (OUT OF SEGMENT) | LKAS-only via `gp-0x6809`→arb | no | retained (base assist separate) |
| **soft-EME** | rate-shaper `FUN_00042af8` SM2/SM3, integrator `gp-0x3570` wind-up | MERGED cmd `gp-0x6b98` (assist+LKAS) | no | can be affected (merged) |
| **hard-DTC** | float watchdog `FUN_00043e44`/Monitor-1-in-shaper, DTC `0xF00049` | full motor (latched, power-cycle to clear) | **yes** | full assist lost |

## GATE TABLE

`GATE | function@addr | branch@addr | signal (gp-offset=absolute) | condition (cal=value) | debounce | effect | class | build touch | LIVE after V31..V35 | confidence`

1. **Arb bVar1 health gate (6 sub-checks)** | `FUN_00028ea6`@0x28ea6 | 0x28eae-0x28f22 (shared fail target 0x28f1c) | plausibility flag gp-0x67f4==1 AND ch1-5 (gp-0x6a44/40/3c/38/46) AND gp-0x6a5e all <32001 | ceiling 32000 (railed-sensor fault level) | none (per-frame) | bVar1=0 → feeds gate 2/3 below | n/a (feeds soft path) | none | LIVE, untouched by any build | [V-prior, `reference_accord_arb_bvar1_full_enumeration.md`]

2. **Arb hard-bail range checks (3)** | `FUN_00028ea6` | 0x28f22-0x28f66, shared bail `jr 0x290b0` | gp-0x4f60 (\|v\|≥25601), gp-0x6752 polarity∉{-1,0,1}, gp-0x6a56 (\|v\|≥12001) | far above real driving (torque peaks ~3400, angle-rate scale) | none | zeroes r9/r22/r26/r28/r12/r25 + gp-0x682f unconditionally | n/a | none | LIVE, untouched | [V-prior]

3. **Deliver-flag × bVar1 compound gate (site A)** | `FUN_00028ea6` | 0x2975a (`ld.bu -0x6809[gp],lp`) → 0x29766 (`cmp 1,lp`) → 0x29768 (`bne`) → **0x2976a** (`cmp r0,r29`) → 0x2976c (`be`) | gp-0x6809 (deliver flag, abs 0xFEDF17F7) AND bVar1 (r29) | gp-0x6809≠1 OR bVar1==0 → fail | none | zeroes gp-0x6b2c (`st.h r0,-0x6b2c[gp]`@0x297fa), sets gp-0x6a7e=1, gp-0x3d37=1, zeroes gp-0x6756 | gentle-EME's downstream effect (this is where an upstream `gp-0x6809≠1` from the engage-SM lands) | none | LIVE | **[V-2026-07-06 — re-disassembled this session, exact addresses confirmed: `ld.bu -26633[gp],lp`@0x2975a, `cmp r0,r29; be`@0x2976a/0x2976c]**

4. **Deliver-flag × bVar1 compound gate (site B)** | `FUN_00028ea6` | 0x29808 (`ld.bu -0x6809[gp],lp`) → 0x2980c (`cmp 1,lp`) → 0x2980e (`bne 0x29814`) → **0x29810** (`cmp r0,r29`) → 0x29812 (`bne 0x29830`) | same signals, second read site | same | none | same zeroing path @0x29814 (`st.b r0,-0x3d36[gp]`, `st.h r0,-0x6b2c[gp]`, `mov 1,r11;st.h r11,-0x6a7e[gp]`, `st.b r11,-0x3d37[gp]`, `st.b r0,-0x6756[gp]`) | same | none | LIVE | **[V-2026-07-06 — confirmed exact addr match to prior memory's claimed "0x29810"]**

5. **Re-engage ramp reset** | `FUN_0002a30e`@0x2a30e | 0x2a31c (`jarl FUN_00046ea6(9)`) → 0x2a326/0x2a32a/0x2a332 | FUN_00046ea6(9)==1 OR gp-0x67fa==8 OR gp-0x6807==7 OR param_3==0 OR ramp overflow | — | none | zeroes gp-0x6758 (ramp gain accumulator), sets gp-0x6807 (STEER_STATUS) to 7/6/3 depending on branch | annotation/ramp reset, not a torque-zero itself | none | LIVE | [V-prior, `reference_accord_arb_input_cluster.md`]

6. **STEER_STATUS=4 (no_torque_alert_2) producer — REPORT ONLY, not a gate** | `FUN_0002a30e` | countdown at 0x2a418 (`ld.b -0x6757[gp],r14; cmp r0,r14; bgt 0x2a47e`) → terminal writes **0x2a4ea** (`mov 4,r12; st.b r12,-0x6807[gp]`) and **0x2a4fa** (`mov 4,r10; st.b r10,-0x6807[gp]`) | gp-0x6757 signed counter, initialized from ±cal 0xC64E2 (=5, read as a BYTE via `ld.bu 29922[r5],r28`@0x2a322, not u16), decremented -1/cycle | cal 0xC64E2=5 (byte) | ~5-cycle countdown | writes gp-0x6807 (STEER_STATUS, abs 0xFEDF17F5-ish) = 4 | **downstream CAN annotation** | none | LIVE, unaffected by any build | **[V-2026-07-06 — freshly walked the whole countdown chain: cal byte-read confirmed 0x05, both STEER_STATUS=4 write sites found and confirmed at 0x2a4ea/0x2a4fa, gated purely by the countdown reaching its terminal value, no read-back into any LKAS-zeroing decision found in this function]**

7. **Direction-corridor arm (driver-override arm) of soft-EME bound** | `FUN_00042af8`@0x42af8 | 0x43110 (`cmp r0,r1;bne 0x43132`), **0x43112/0x43114** (`cmp r21,r13;bh 0x43132`) | \|gp-0x6bf0 driver-assist\| ≤ cal 0xC6156 (=9216) OR authority r13≠0 (r21=cal 0xC641A=0) | none | zeroes corridor r12/r7 (both arms) at 0x43132-0x43134 | soft-EME (bound arm) | V29/V30 widened (×2/×4); V31-35 keep the widen + add boost floor | LIVE (still gated off hands-off in V31-V35 — this is exactly why V30 alone had the residual) | **[V-2026-07-06 — freshly disassembled 0x43100-0x43136, exact match: `cmp r21,r13`@0x43112, `bh 0x43132`@0x43114, zero-path@0x43132]**; cal values fresh-read: 0xC6156=9216 [V-2026-07-06], 0xC641A=0 [V-2026-07-06]; corridor Y cal 0xC674E=1024, 0xC675A=0xFC00(-1024) [V-2026-07-06, STOCK values — V29+ doubles these]

8. **IIR arm** | `FUN_00042af8` | 0x43136 (`sar 8,r11`), 0x43138 (`cmp r23,r11`), 0x4313c (`cmov gt,r11,r23,r10`) | gp-0x3574 (IIR of column-velocity-input LERP), decays to 0 when column stationary | cap 0x3000 (12288), alpha cal 0xC6418=10 | none (continuous decay, τ≈102ms) | contributes to max(corridor,IIR,boost) | soft-EME (bound arm) | untouched by any build | LIVE | [V-2026-07-06 partial (max-combine instructions confirmed), V-prior for IIR decay identity/alpha]

9. **Boost arm** | `FUN_00042af8` | LERP over gp-0x6ac2 (\|angular rate\|), cal 0xC6760 table X[700,800,1100] | X breakpoints; Y stock=[0,1536,2048] confirmed at 0xC6768/6A/6C | rate≈0 → Y[0]=0 | none | contributes to max chain | soft-EME (bound arm); **V31 floors this to 4096** | V31-V35: floored 4096 int (0xC6768/6A/6C) + 4.0 float (0xC65C4/8/C) | LIVE, and in V31+ this is the arm that self-stabilizes the bound (ON at authority≈0 unlike corridor) | **[V-2026-07-06 — fresh read of STOCK cal: 0xC6768=0, 0xC676A=1536(0x0600), 0xC676C=2048(0x0800) — exact match to memory's Y[0,1536,2048] claim]**

10. **Boost-zeroing state machine** | `FUN_00042af8` | state gp-0x3562 (0x42fb4/0x42ffa/0x43010), counter gp-0x355c | 0x42fcc (`ld.hu tp+0x741e,r8`=cal 0xC641E=16384; `cmp r8,r13; bh 0x42fd6`) — counter increments while authority>16384; at ceiling ~20 cycles (cal 0xC64E3), state→2 | dwell ~20 cyc (cal 0xC64E3≈20) | 0x43004 (`cmov nz,0,r23,r23` while r13≠0) — force-zeroes boost | soft-EME (arm-latch) | untouched | LIVE (this is WHY boost alone isn't a permanent floor — but the V31 floor value is added upstream of this SM's target, and the fixpoint argument in reference_accord_soft_eme_bound_arm_gating.md shows the latch never fires at V31's steady-state) | **[V-2026-07-06 — freshly disassembled 0x42fb0-0x43026: state byte gp-0x3562 addr confirmed (-13666=-0x3562), threshold cal 0xC641E=16384 confirmed fresh-read, force-zero cmov at 0x43004 confirmed]**

11. **Authority formula** | `FUN_00042af8` | writer 0x432b0-0x432c8; read into r13 @0x42d86 | gp-0x6966 = (\|gp-0x3570>>15\| × cal 0xC61DA) >> 10 | cal 0xC61DA=1092 | n/a | feeds gates 7,10 (both key off this) | soft-EME (shared authority signal) | untouched | LIVE | **[V-2026-07-06 — fresh cal read: 0xC61DA=0x0444=1092, exact match]**

12. **Integrator wind-up → SM2 arm** | `FUN_00042af8` | integrator update 0x431c4-0x4327c; SM2 node gp-0x6962, arm compare 0x436f4/0x43746 | integrator winds on (command − bound); magnitude ≥ cal 0xC6422 | cal 0xC6422=16384 (50% Q15) | none (continuous) | sets SM2 node=0 → contributes to 3-way authority min | soft-EME (cut) | untouched (V19 proposed rescale, never adopted into the V29+ lineage) | LIVE — this is literally the mechanism V31 defuses by keeping the bound ≥ command | **[V-2026-07-06 — fresh cal read: 0xC6422=0x4000=16384, exact match]**

13. **SM3 saturation cut** | `FUN_00042af8` | SM3 node gp-0x6787; integrator clamp/trip cal 0xC61DC | integrator \|gp-0x3570>>15\| saturates ≥ cal 0xC61DC for ~cal 0xC6298(=20) cycles | cal 0xC61DC=30720 (=2×15360 stock full authority) | ~20 cycles | SM3 node=0 (cal 0xC6420=0 is the trip value) | soft-EME (cut) | untouched | LIVE | **[V-2026-07-06 — fresh cal read: 0xC61DC=0x7800=30720, exact match]**

14. **3-way authority MIN → demand gate (the actual cut point)** | `FUN_00042af8` | **0x439c0** (`cmp r12,r6; cmov nc/nl,r12,r6,r8`, part of chained min over 3 nodes each ∈{0,0x8000}) → **0x43a3a** (`mul r26,r28,r0` then `sar 15,r28`) | authority=min(SM1,SM2,SM3 nodes) then demand=blend×authority>>15 | any node=0 | instant (bypasses slew) | demand→0 → clamp ±0x2000 → gp-0x6b98=0 | soft-EME (the actual zero) | untouched (V29-V35 avoid tripping it via the bound-arm fixes, not by touching this math) | LIVE | **[V-2026-07-06 — fresh disasm at both exact claimed addresses: `cmp r12,r6`@0x439c0 (part of the 3-way min chain with `ori 0x8000` node construction @0x439bc), `mul r26,r28,r0`@0x43a3a]**

15. **Monitor-1 (in-shaper) float-vs-int lockstep** | `FUN_00042af8` | 0x43172 (`ld.w -0x6db0[gp],r8`), 0x43176 (movhi 1024.0), 0x43182 (`ld.h -0x6af6[gp],r6`) | float twin gp-0x6db0 (dir1)/gp-0x6db8 (dir2) vs int wall gp-0x6af6/gp-0x6b00, tolerance ~±5-16 LSB (sentinel -16 at one check) | ±5-15 LSB (widened proportionally in prior falsified V27/28) | ~10 fault cycles → sVar24≥100 → +0x400 → trip≥128 | `FUN_0004613e`→`FUN_00016de6(0x1c,...)` → hard shutdown | **hard-DTC** | untouched by V29-V35 (all keep int↔float matched pairs) | LIVE — this is the mechanism that bricked V25/26/27 when corridor widening broke lockstep; V29+ keep it matched | **[V-2026-07-06 — fresh disasm confirms exact addresses: `ld.w -28080[gp],r8`@0x43172 (=-0x6DB0), `ld.h -27382[gp],r6`@0x43182 (=-0x6AF6), `ld.w -28088[gp],r10`@0x43186 (=-0x6DB8) — all three exact-match the claimed addresses]**

16. **Monitor-2 (float watchdog) trip → DTC 0xF00049** | `FUN_00043e44`@0x43e44 (dir1/dir2 inline @0x4463a/0x44662; weight-32 bit @0x448d6-0x448f4) | **0x44a2e** (`cmp r12,r7` vs movhi 128.0@0x44a26) → **0x44a34** (`bgt 0x44a3e`) → **0x44a42** (`movea 0x3f1b,r0,r6`) → **0x44a4c** (`jarl FUN_000462e6,lp`) | accumulated float fault_word (weighted bit sum, incl. weight-32 delivered-torque check) ≥128.0 | dwell SM states 0→1→2→3 (~10ms typical) | `FUN_000462e6(0x3f1b)` → `FUN_00016de6(0x1d,0x3f1b,1,1)` → DTC 0xF00049 latch → `FUN_00019f7c`/`FUN_0001a16a` → `FUN_00045608(3,0,0x8000,0x8000)` motor-off, `gp-0x3ee8=1` (no re-entry until power cycle) | **hard-DTC** (the actual latch mechanism) | untouched | LIVE, **gate enable cal 0xC64A4=0 (ENABLED)** — verify fresh if any future build ever touches this block | **[V-2026-07-06 — fresh disasm of 0x44a20-0x44a50: EXACT match to memory's claimed sequence — `movhi 17152,r0,r12`@0x44a26 (=0x43000000=128.0), `cmp r12,r7`@0x44a2e, `bgt 0x44a3e`@0x44a34, `movea 16155,r0,r6`@0x44a42 (16155=0x3F1B), `jarl 0x000462e6,lp`@0x44a4c]**

17. **Monitor-2 secondary path `FUN_00044666`** | permanently gated OFF by cal `0xC74A4=0xEA` (non-zero) | — | dead code, states 2/3 unreachable | — | — | (inert) | n/a | untouched | INERT, unaffected by any build | [V-prior only, not re-walked this session — flagged for future re-verification if any build ever nears this cal]

## Boundary variables consumed from adjacent segments (report back to other tracers)

- **gp-0x6809** (deliver flag, abs `0xFEDF17F7`) — read at 0x2975a/0x29808 (gates 3/4 above). This is the engage-SM/deliver-commit segment's OUTPUT into arbitration.
- **gp-0x67a4** (ENABLE byte, abs `0xFEDF195C`) — sole writer confirmed this session at **0x2b51e** (`st.b r14,-26532[gp]`, -26532=-0x67A4) inside `m_steer_torque_limit_and_pack`; values 2/3=enabled, 0/1/4/5=LKAS zeroed (r14 built from cmov chains at 0x2b506/0x2b512/0x2b51c feeding values 3/4/0). **[V-2026-07-06 — freshly confirmed exact address and instruction]**
- **gp-0x6b3c** (LKAS-only final torque output, abs `0xFEDF14C4`) — 1 writer (arb), 1 reader (`m_steer_torque_limit_and_pack`) per prior memory; = command × (ENABLE∈{2,3}).

## Answer to mandate item 5 (STEER_STATUS direction)

**Confirmed by fresh disasm this session: STEER_STATUS (gp-0x6807/gp-0x6807-adjacent write site, byte `-0x6807[gp]`) is a pure downstream ANNOTATION, never a gate input.** Walked the entire `FUN_0002a30e` body (0x2a30e-0x2a504): every write to `-0x6807[gp]` (values 3, 6, 7, 4 at various branches) is a **store**, and no instruction in the function reads `-0x6807[gp]` back to make a zeroing decision — the actual zeroing decisions in this function key off `FUN_00046ea6(9)`, `gp-0x67fa==8`, `gp-0x6807==7` (read as an INPUT is possible elsewhere but not observed to gate LKAS output in this function's own body), and the countdown `gp-0x6757`. The STEER_STATUS=4 write (no_torque_alert_2) specifically fires purely from the countdown reaching its terminal value — confirmed at exactly 2 sites, 0x2a4ea and 0x2a4fa.

## Related
[[reference-accord-shaper-fun42af8]] · [[reference-accord-soft-eme-bound-arm-gating]] · [[reference-accord-corridor-lockstep]] · [[reference-accord-override-snap-state-machines]] · [[reference-accord-consistency-monitor-hardshutdown]] · [[reference-accord-arb-bvar1-full-enumeration]] · [[reference-accord-arb-input-cluster]] · [[reference-accord-dtc-construction-mechanism]] · [[reference-accord-lerp-envelope-gating]]
