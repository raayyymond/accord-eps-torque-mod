---
name: reference-accord-v100-rungs-proven-and-pid-gain-tables
description: "V100's RUNG A and RUNG D' are PROVEN correctly coded from the built image (cond nibble 0xE = GE, 32-bit abs, no guard, correct bit placement) -- so d(b5)=d(b6)=0.000000 over 249.2 s is a null on the HYPOTHESIS, not the V64/V68 gate signature; the positive controls share the same accumulator AND store as the null rungs. Plus: the PID's P/I/D gains are 4-knot LERP TABLES (0xC6B1C/0xC6B08/0xC6ADC) indexed by gp-0x6ac0 = FOC electrical rate at 4.7121 ct per column deg/s -- and the whole schedule is UNREACHABLE, so the gains are constants and the integrator is FULLY LIVE (refuting 'Ki structurally dead')."
metadata:
  type: reference
---

# V100's rungs are sound, and the PID's gain schedule is unreachable

Traced 2026-08-13, task `tracer-6ad6-terms`. V100 image imported fresh into the Ghidra project
(`V850:LE:32:default`); Ghidra `read_memory` at `0xC4B34` matched an independent Python read
byte-for-byte before any disassembly was trusted. All `disassemble_bytes` used `dry_run: true`.

## PART 1 — the rungs ARE correctly coded [EVIDENCE]

Cave `0xC4B34`–`0xC4BB7`, **132 B / 49 instructions**, hooked by `0x55C0E jarl 0x000c4b34,lp`
(straight-line, after `0x55C0A jarl 0x1fa42` = DI, before the 0x14A transmit).

```
RUNG A  0C4B34 ld.h -0x6ad6,gp,r6 / cmp 0x0,r6 / bge / subr r0,r6   -> r7 = |ref|
        0C4B40 ld.hu 0x7200,tp,r6      ; tp=0xBF000 => cal 0xC6200 = 8192 (verified in the V100 image)
        0C4B44 cmp r6,r7 ; 0C4B46 mov 0x2,r7 ; 0C4B48 bge ; 0C4B4A mov 0x0,r7
RUNG D' 0C4B66 ld.h -0x4f60 / 0C4B6A ld.h -0x6ad6 / 0C4B6E sub r7,r6  ; 32-BIT, cannot wrap
        0C4B78 movea 0x2800,r0,r6 ; cmp r6,r7 ; mov 0x4,r7 ; bge ; mov 0x0,r7
```

- **Condition nibble decoded: `ae05` = halfword `0x05AE`; bits[10:7] = `0b1011` (Bcond), bits[3:0] =
  **0xE = GE** (signed ≥); disp = 4 ⇒ target PC+4 ✓.** The inversion class is different:
  `ba05` = `0x05BA` → 0xA = NZ/NE, `b205` = `0x05B2` → 0x2 = Z/E. **Not that bug.**
- `cmp reg1,reg2` computes `reg2 − reg1`. ⚠ **`mov imm5,reg` does NOT set PSW on V850**, so the
  `mov 0x2,r7` sitting *between* the `cmp` and the `bge` is flag-transparent. Delicate, and correct.
- **abs is 32-bit** (`ld.h` sign-extends), so `−32768 → +32768` cannot overflow; and `gp-0x6ad6` is
  writer-clamped ±25600 at `0x38142` anyway. `sub` of two sign-extended int16s ∈ [−65535, 65535].
- **No guard** on either rung — the only branches are the abs and the comparator, both falling through.
- Merge: `andi 0x5f` = clears {5,7} (pass 1 owns b5,b7); `andi 0xa7` = clears {3,4,6} (pass 2 owns
  b6,b4,b3). Disjoint, and each preserves the other's bits. `shl 0x4` puts 2→bit5, 4→bit6. ✓

⭐ **THE CLINCHER — the positive controls share the ACCUMULATOR and the STORE with the null rungs.**
`b5`+`b7` are both accumulated into `r7` and written by the SAME `st.b` at `0xC4B62`; `b6`+`b4`+`b3`
likewise at `0xC4B9C`. `b7`=0.5222, `b4`=0.6057, `b3`=1.000000 ⇒ **both stores executed every frame ⇒
both rungs were evaluated every frame.** No path evaluates a control but skips its rung.
⇒ **NOT the V64/V68 "detector never armed" signature.** The detector ran 29,999 times and said false.

⊕ Structural corroboration: the reachable-clamp budget
(`3162+1024+1024+768 = 5,978 < 8,192`, see [[reference-accord-gp6ad6-eight-terms-and-the-reachability-budget]])
predicts `d(b5)=0` from **structure alone**, independent of the flight. Two lines agree.

⚠ My own Python Format-V scan for the `jarl → 0xC4B34` returned **ZERO hits** — the kit's recorded
`jarl` mask bug, a tool zero. Ghidra found it instantly. **Do not hand-decode Format V.**

## PART 2 — the PID gains are LERP TABLES, and the schedule is UNREACHABLE [EVIDENCE]

`FUN_0003a382`. Idiom pinned at `0x3a44a movea 0x7adc,tp,r6` / `addi 0xa,r6,r13` (Y base) /
`addi 0x2,r6,ep` (X base) — **a DIRECT `tp` displacement, NO mode index ⇒ RULE 7 PASSES**
(contrast `FUN_0003b338`, which IS mode-indexed via `PTR_DAT_000c8198[gp+0x63fd]`).

**Axis for ALL FOUR tables: `0x3a38e ld.hu -0x6ac0,gp,r12`, loaded once.**
`gp-0x6ac0` = FOC electrical-angle RATE, magnitude-only, **4.7121 counts per column °/s**
(cross-checked against `0xC520C`: knots 1050→222.8 °/s, 4100→870.1 °/s reproduce exactly).

| table | base | X (counts) | **X (column °/s)** | Y | gain |
|---|---|---|---|---|---|
| P | `0xC6B1C` | 0, 300, 2000, 4000 | 0, 63.7, 424.4, 848.9 | 256,256,225,153 | 0.250→0.149 |
| I | `0xC6B08` | 0, 400, 1500, 3000 | 0, 84.9, 318.3, 636.7 | 98×4 | 0.0957 flat |
| D | `0xC6ADC` | 50, 400, 1500, 3000 | 10.6, 84.9, 318.3, 636.7 | 2048×4 | 2.000 flat |
| anti-windup | `0xC6AF0` | 0, 3277, 3604, 19661, 32768 | 0, **695.4**, **764.8**, … | 32768,32768,0,0,0 | limit→0 above 764.8 |

**Measured `gp-0x6ac0` max ≈ 528 counts ≈ 112 °/s; 0.00 % reach 1050 ct.** ⇒
- **Kp varies 256 → 251.8 over the whole measured range = 1.6 %.** I and D flat by construction.
  ⇒ **the PID is a FIXED-GAIN controller in practice; the scheduling is dead, not the gains.**
- 🛑 **REFUTES "Ki structurally dead / integrator pinned"** — the anti-windup knee is **6.8× above**
  the measured max, occupancy 0.00 % ⇒ **the integrator's clamp is at 32768 (unlimited) always.**
⚠ The exposure figure is INHERITED from the kit's own `gp-0x6ac0` return measurement, not re-measured.

**Virginity, read from 95 built images + stock (not from scripts):** `0xC6AE6`/`0xC6AEC` = 2048,
`0xC6B12`/`0xC6B18` = 98, `0xC6B26`/`0xC6B2C` = 256/153, `0xC6ADC` = 4 — **identical on all 96.
ALL VIRGIN.** Their appearance in 6 build scripts (v43/49/97/98/99/100) is **mentions, not edits.**
Non-virgin neighbours, each ONE build: `0xC644A` **D-term filter pole** → 32 (V43), 64 (V49);
`0xC6450` I scale → 32 (V46); `0xC6AFC` anti-windup Y[0] → 0 (V56).

⭐ **Because the operating point lives entirely in the flat FIRST segment, a knot edit here is a clean
SCALAR gain change** — move Y[0] and Y[1] together and there is no slope discontinuity anywhere the
car goes. The usual table hazard inverts. 4 bytes per term, cal-only, no cave. 🛑 GATE 2 UNMADE.

## PART 3 — `gp-0x67ab` is a BOOLEAN, and that explains the V86 retraction [EVIDENCE]

`gp-0x67ab` ← `0x27754 ld.bu -0x3d94` ← **`0x27328 st.w r11,-0x3d94,gp`**.
🛑 **A byte-width scan reports 0 writers here — a FALSE ZERO. The cell is written by a WORD store**
and read back as its low byte. New trap: *scan for wider stores whose SPAN covers the target byte.*

r11 ← r10 @`0x272ce`; r10's only producers are `setfne r10`, `mov 0x1,r10`, `mov 0x0,r10`
⇒ **the byte is structurally BOOLEAN.** The gate drops terms 1–7 **iff it == 1 exactly**
(`reduce = v*(v<2)`).
⭐ **This explains the catalogued V86 retraction**: a `gp-0x67ab < 2` rung is a **TAUTOLOGY** on a
boolean byte — not a coding slip, a proposition true by construction.
`mov 0x1,r10` needs `r25 != 0`, and **`r25` is explicitly zeroed at `0x271be`** and only set from r10
⇒ closed induction, cannot bootstrap. Everything reduces to `mode[lane] ∈ {2,3,4}`.

🛑 **CORRECTS `reference_accord_gp67ac_resolved_zero_and_path1_always_live`:** the mode byte tested at
`0x27288` is `ld.bu 0x0,r9,r12` with **`r9 = gp-0x61a0` (RAM)**, NOT `tp+0x5124`. The flash array
`0xC4124` is read at `0x26d1a` (`cmp 0x7`), and `0xC4118` (partition) at `0x272c2`. Three arrays,
conflated. `gp-0x61a0[]` has **0 direct stores**, written register-indirect from ~30 `movea` bases in
`FUN_00025c32`'s region — **its value set is UNCLOSED.** If it mirrors `0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]`
(values {0,5} only, verified from the image) then `gp-0x67ab ≡ 0` and terms 1–7 always sum. **BELIEF.**

Related: [[reference-accord-gp6ad6-eight-terms-and-the-reachability-budget]] ·
[[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]] ·
[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]]
