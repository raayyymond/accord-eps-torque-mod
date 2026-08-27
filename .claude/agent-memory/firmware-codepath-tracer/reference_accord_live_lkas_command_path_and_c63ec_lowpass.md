---
name: reference_accord_live_lkas_command_path_and_c63ec_lowpass
description: The live 4x LKAS command path traced end to end (gp-0x3d3c IIR -> deadband/sign-gate -> gp-0x6b38 -> gp-0x6b3c -> registration +4 -> gp-0x62b0 -> gp-0x3d88 -> gp-0x6b4c); it contains exactly ONE frequency-dependent element, a virgin cal-only ~5 Hz one-pole low-pass at 0xC63EC/0xC63EE whose DC gain is preserved if both cals move together; plus the NEVER-ARM hazard that zeroing the 0xC4118 partition deletes the LKAS command, and the 0xC6194/0xC6196 retraction.
metadata:
  type: reference
---

# The live LKAS command path, and the one filter on it — 2026-08-13, `tracer-fprime`

## 🛑🛑🛑 NEVER ARM `0xC4118` — IT DELETES THE LKAS COMMAND
`decompile_function(0x26c80)`: **the partition byte does DOUBLE DUTY** — it routes `gp-0x6298[]`
*and* **gates `gp-0x62b0[]`**, which carries the live 4× command.
```c
if (*(char*)(tp+0x5118+i) != 0) iVar11 += gp-0x62b0[i];  // -> gp-0x3d88 ** LIVE COMMAND **
if (*(char*)(tp+0x5118+i) != 0) iVar47 += gp-0x6298[i];  // -> gp-0x3d80 (bypass)
if (*(char*)(tp+0x5118+i) == 0) iVar13 += gp-0x6298[i];  // -> gp-0x3d84 (through limiter)
```
All 11 bytes = 1 ⇒ `gp-0x3d84` ≡ 0. **Zeroing the partition to "arm" the `0xC6194` limiter sets
`gp-0x3d88` = 0 ⇒ `gp-0x6b4c` = 0 ⇒ LKAS steering silently dead while openpilot believes it steers.**
⇒ **ARMING THE LIMITER AND DELETING THE COMMAND ARE THE SAME EDIT.** This is the sourced content of
the previously unattributed *"arming goes the WRONG way"* note. See
[[reference-accord-rate-limits-c6194-partition-and-c520c-ceiling-scale]].
⊕ `0xC6194`=3 @`0x27622` is a real slew step; **`0xC6196`=0 @`0x276AA` is the "output ×0"** — the kit
memory's kill reason was on the wrong cell. The limiter is dead **twice**: input ≡ 0, and its output
reaches only `gp-0x6b4a` ≡ 0 (`0xC63CC` = 0 annihilates the cross-term into `gp-0x6b4c`).

## The path, end to end [EVIDENCE — decompile + `disassemble_bytes` dry_run]
```python
# FUN_00028ea6 @0x2a174-0x2a1b0  ** THE ONLY FREQUENCY-DEPENDENT ELEMENT **
state = ((state * u16(0xC63EC)) >> 10) + ((x * u16(0xC63EE)) >> 10)   # 0x2a1a0/0x2a1a6/0x2a1a8
out   = (state + state_prev) >> 5                                     # 0x2a1aa/0x2a1ac ; st.w @0x2a1b0
# @0x2a1ae-0x2a1e2  gated hard nonlinearity (see the July memory)
if u8(0xC64A3)==1 and u8(gp-0x6806)==0:
    if abs(out) <= s16(0xC61B8): out = 0                  # DEADBAND +-102
    elif sign(out)!=sign(gp-0x6b30) or prev==0: out = 0   # SIGN GATE, state gp-0x6b30 @0x2a206
out  = (out * u16(gp-0x69b0)) >> 15                       # Q15 ramp
r11  = clamp((r11+out) * (s16(0xC746C)*s8(gp-0x6752)) >> 15, +-u16(0xC61B4))  # 0xC746C=41234, +-512
gp-0x6b38 = -r11                                          # 0x2a220 subr / 0x2a23c
gp-0x6b3c = 0 if cond else gp-0x6b38                      # leaf @0x2b418/0x2b41c
field_+4  = clamp(gp-0x6b3c, +-u16(0xC61B2))              # 0x2b42a/0x2b42e   = +-512
gp-0x3d88 = SUM over 11 partition-gated gp-0x62b0[]       # 0x2730c
gp-0x6b4c = clamp(gp-0x3d88 + pol*((iVar13*u16(0xC63CC))>>10), +-10240)   # 0xC63CC = 0
# readers: 0x3816C (FUN_00038148 Path-2), 0x3AA3E, 0x285B4, 0x28B16
```
**EVIDENCE: between the registration and the aggregator NOTHING is frequency-dependent** — copies, an
unweighted Σ, and clamps only. ⚠ That null rests on the **decompile**, not the scan: the `gp-0x62f8[]`
/ `gp-0x62b0[]` / `gp-0x6298[]` arrays return **R=0 W=0** on a displacement scan because they are
`movea`-base + runtime-index (the trap class below).

## ⭐ THE LEVER — `0xC63EC` / `0xC63EE`, 4 bytes, VIRGIN, DC-preserving
One-pole IIR `a` = 992/1024 = 0.96875 ⇒ **fc ≈ 4.97 Hz @1 kHz**, in series with a 2-tap MA ⇒ total
**DC gain 0.9902 (deliberately unity)**. DC = `(b/(1024−a))×(2/32)` ⇒ **moving `a` and `b` together
holds DC gain exactly while moving the corner — this is NOT a `0xC6CD0` authority cut.**

| `0xC63EC`/`0xC63EE` | DC | fc | ratio @7.79 Hz | Δphase @7.79 |
|---|---|---|---|---|
| **992 / 507 STOCK** | 0.9902 | 4.97 Hz | 1.000 | — |
| 1000 / 380 | 0.9896 | 3.73 Hz | **0.801** | **−7.1°** |
| **1008 / 254** | 0.9922 | 2.49 Hz | **0.564** | **−15.1°** |
| 1012 / 190 | 0.9896 | 1.87 Hz | 0.430 | −19.4° |

Bands at 1008/254: 0.5 Hz **0.984** · 3 Hz 0.744 · **7.79 Hz 0.562** · 21 Hz 0.506 — **V88's felt
0.549 at the ratchet with 0.5 Hz authority intact**, the same signature V88 measured.
**Census 2R/0W each** (`0x2A184`/`0x2A8A2`, `0x2A174`/`0x2A892`), Ghidra ∖ Python EMPTY, RULE 7 n/a
(non-indexed `tp` scalars). **Bit-identical (992,507) across all 96 images, 0 build-script hits, 0
lineage mentions — NEVER FLOWN.**

🛑 **GATE 2 COST IS REAL:** −15.1° extra lag at 7.79 Hz inside a loop with a **Q 14–29, ζ 0.017–0.036**
mode, and Path 2 enters as `B = 1+Q`. **V85 precedent: a change in this direction made the ratchet
2.89×→6.58× worse.** Start at **1000/380 (−7.1°)**, not 1008.

🛑 **UNRESOLVED BLOCKER:** a **twin block** at `0x2A89A`/`0x2A8BA` (state) reading the **same two cals**
(`0x2A892`/`0x2A8A2`), plus a second `gp-0x6b38` writer at `0x2A934`, sits in a region **Ghidra has not
defined as a function**. A cal edit hits **both**. Liveness unknown — **close this before cutting.**

## V88 did NOT attenuate this path
`0xC6446` is Lever B on the **r24 rate lane**, which sums into the **same aggregator** `gp-0x6b94`
unweighted. V88 halved the **aggregator's** HF, i.e. another term's share of the delivered command.
⇒ **"delivered command HF" ≠ "LKAS command HF"**; the IIR above is the first cal-only route to the second.

## 🛑 `gp-0x6806` IS THE ENGAGEMENT FLAG — the deadband/latch block is MANUAL-ONLY [EVIDENCE]
Written **only** by `FUN_00028ea6`'s engage-ramp SM (16 stores: 8 live there, 8 in the dead region).
`0x293A6`: `mov 0x1,r6` → `st.b r6,-0x6806,gp` **alongside `st.b r15,-0x3d38` with `r15 = 3`** — a state of
the 8-state ramp SM driving `gp-0x69b0`. 4 live sites write non-zero, 4 write `r0`.
⇒ **`!= 0` = LKAS active; `== 0` = NOT active ⇒ the `0x2a1ae`–`0x2a206` deadband + sign-latch runs in
MANUAL ONLY and cannot cause an engagement-required symptom (83.0 % engaged vs 0.0 % manual).**
⇒ **Lever B (gated `!= 0`) is UNAFFECTED — V88's attribution stands; no retraction.** Complementary halves
of one flag: Lever B on `!= 0`, this block on `== 0` (`0x2a1ba cmp r0,r12` / `0x2a1bc bne 0x2a1e6`).

🛑 **`memory/reference/firmware/reference-accord-pregain-deadband-c61b8.md`'s *"LOW-SPEED LOCKOUT, 0 % above 4 mph"* is a
CORRELATION ON A CREEP-DOMINATED CORPUS, not the flag's identity.** V67's **direct identity test —
`== latActive` on 150,302/150,327 = 99.983 %, all 25 disagreements single-frame edges** — beats it, and
route 0x85 (engaged p50 39.6 km/h, 45.5 s > 80 km/h) breaks the confound. ⊕ The symptom is
**speed-INDEPENDENT** (+0.111/+0.077/+0.131 across 10–30/30–60/60+), and a creep-only enable cannot host it.
⇒ **The `0xC62EA` 320→0 chain is MOOT for this gate** (it mattered only under the lockout reading).

## THE SELF-LATCH, adjudicated [EVIDENCE]
`0x2a1da mul r13,r6,r0` / `0x2a1e0 bgt` ⇒ `prev == 0` gives product 0, `0 > 0` false ⇒ re-zeroed and
stored at `0x2a206`: **self-sustaining.** The enable-fail path branches to **`0x2a1e6` — past the gate but
BEFORE the ramp multiply and the state store** ⇒ `prev` is refreshed ⇒ **the latch HEALS whenever
`gp-0x6806 != 0`.** ⇒ reading (B) refuted; (A) vs (C) is a cadence measurement, not a trace.
🛑 **It is a LATCHING KILLSWITCH, not a hysteresis.** Backlash outputs a *continuously lagged* input —
that is where "lag grows as amplitude falls" comes from. This block outputs the ramp-scaled input **or
exactly zero**, and latches. **Do not import backlash's describing function.** "Dual of a relay" and
"hysteresis" are both analogies; the instruction stream says latch.

## ⚠ THREE SCAN-DEFECT CLASSES I HIT IN ONE SESSION — all caught by a DECOMPILE, never by the scan
1. **`st.b` mapped to the wrong opcode** ⇒ false **"0 writers"** on a cell with 20 hits. `st.b` = **`0x3A`**.
2. **`|1` alias applied to `st.b`** ⇒ 4 phantom writers: `gp-0x6805` (`enc 0x97FB`) aliased onto
   `gp-0x6806` (`0x97FA`). **Corrected rule, validated on 5 Ghidra-decoded instructions:
   `st.b`/`ld.b` → `hw2 == enc` EXACTLY · `ld.bu` → `hw2 == enc|1` · halfword/word → either.**
3. **Scanning DATA as code** ⇒ phantom `jarl` hits sourced in the cal/table region. **Restrict jarl scans
   to `[0x13000, 0xC0000)`.**
⭐ **An implausible null is a bug report — and so is an implausible non-null. The decompile is the arbiter
either way.** Opcode map, calibrated from Ghidra: `ld.b 0x38 · ld.h/ld.w 0x39 · st.b 0x3A · st.h/st.w 0x3B
· ld.bu 0x3C/0x3D · ld.hu 0x3F · movea 0x31`.

## ⚠ TRAP CLASS — `movea` base + runtime index
Arrays reached by `movea <off>,tp/gp,rX` then indexed at runtime give **zero hits per element** on a
displacement scan and read as *"nothing accesses slot i"*. Seen on `tp+0x5118` (10 `movea` sites:
`0x27222,0x272C2,0x272E0,0x2747E,0x2756C,0x280AC,0x281FE,0x28226,0x28252,0x2837A`) and on all four
`gp-0x62xx` request arrays. **Corroborate array nulls from the decompile, never from a scan.**

Related: [[reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever]] ·
[[reference_accord_4x_gain_feeds_6b4c_not_term0_and_the_struct_offset_map]] ·
[[reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop]]
