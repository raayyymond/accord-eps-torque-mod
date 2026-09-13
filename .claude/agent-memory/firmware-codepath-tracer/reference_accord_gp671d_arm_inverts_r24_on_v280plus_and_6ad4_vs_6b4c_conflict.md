---
name: reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict
description: "Two additions to the well-covered r24 chain. (1) The gp-0x671d gain_B arm's CROSS-BUILD consequence: on stock it DOUBLES r24 (512->1024) but on every V280+ image it COLLAPSES it (5244->1024 = x0.195), and it is a saturating rising-edge Schmitt latch (SET |x|>=0xC61FA=5530, RELEASE |x|<0xC61F8=1024) cleared ONLY by FUN_0003bcb2 -- so one latch event removes 80% of the r24 lane for the rest of the drive cycle. Model r24 as BIMODAL, not a single gain. (2) An unresolved CONFLICT between two existing tracer memories over which aggregator term carries LKAS (gp-0x6b4c vs gp-0x6ad4); my own evidence favours gp-0x6ad4 but I did not edit either file."
metadata:
  type: reference
---

# gp-0x671d inverts r24 on V280+, and the gp-0x6ad4 / gp-0x6b4c conflict — 2026-09-13, r24-lane trace for `r24lane`/`main`

Program `code.bin` (stock, `list_open_programs` confirmed), cross-read against 10
`_vNN_plain_image.bin` (V280, V281r3, V282, V283, V284, V285, V287r2, V288r2, V289, V28).
GhidraMCP + Python; every Python scan positive-controlled (gp-relative scanner 7/7 known sites,
jarl scanner 3/3 on the skill's documented controls).

⚠ **Most of the r24 chain is ALREADY well covered in this directory** — see
[[reference_accord_r24_gainb_table_structure_and_priority_gate]] (the 4-way gain_B priority gate and
both `gp-0x671d` writers), [[reference_accord_c61f6_deadband_is_coulomb_friction_not_percentage]],
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]],
[[reference_accord_gp4f62_dt_is_dma_sensor_tick_not_cpu_ms]],
[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]],
[[reference_accord_aggregator_11term_loop_census_units_and_fork]].
**This file records only what those did not.**

## 1. 🛑 THE `gp-0x671d` ARM'S SIGN FLIPS BETWEEN STOCK AND EVERY V280+ BUILD [EVIDENCE]

The structure is already recorded. The **cross-build consequence** was not.

| cell | role | stock | V280…V289 |
|---|---|---|---|
| `0xC6446` (`tp+0x7446`) | gain_B, ENGAGED arm (`0x3ac08`) | **512** | **5244** |
| `0xC6442` (`tp+0x7442`) | gain_B, `gp-0x671d != 0` arm (`0x3abfe`) — **outranks all** | **1024** | **1024** |

Read with `struct.unpack_from('<H', img, addr)` from each image; byte `0x3aa96` reads `c5` on stock
and `fb` on every V280+ image, confirming the V104 gate repoint to `gp-0x6806`
(STEER_CONTROL_ACTIVE) is carried, i.e. the 5244 arm is the *engaged* arm.

⇒ **On stock the fault arm DOUBLES r24 (512 → 1024, ×2.0). On every V280+ image it COLLAPSES it
(5244 → 1024, ×0.195).** The arm's sign is inverted by the very lever the kit has been pushing.
**Any model that treats r24's gain as a single number is wrong on V280+ builds; r24 is BIMODAL.**

## 2. The latch is first-strike and is never re-armed during a drive [EVIDENCE]

Writer `FUN_00041d56` @`0x41ec6` (`st.b r28,-0x671d[gp]`, lockstep twin `gp-0x4c24` @`0x41eca`),
read back with a mismatch check at `0x41ebe`/`0x41ec2`:

```
0x41e40..0x41e50  cvtf.ws / mulf.s (0x44800000 = 1024.0f) / trncf.sw   -> r8   FLOAT input
0x41e5c  st.h r8,-0x6ad8[gp]          ; telemetry mirror, the ONLY touch of gp-0x6ad8 image-wide
0x41e5e..0x41e6c                       ; r8 = |r8|
0x41e6e  ld.bu -0x358a[gp],r12        ; previous latch state
0x41e76  bne 0x41e80                  ; latched -> use the RELEASE threshold
0x41e78  ld.hu 0x71fa[tp],r11         ; 0xC61FA = 5530   SET threshold
0x41e7e  bc   0x41e8a                 ; |x| < 5530 -> no set
0x41e80  ld.hu 0x71f8[tp],r9          ; 0xC61F8 = 1024   RELEASE threshold
0x41e86  cmovnc 0x1,r14,r14           ; r14 = 1 iff |x| >= 1024
0x41e90  setfh r12                    ; RISING EDGE only (r14 > previous)
0x41e94  add  r12,r28                 ; counter += edge
0x41ea0  movea 0xff,r0,r28            ; SATURATE at 255
0x41ea4  ld.bu 0x7500[tp],r7          ; 0xC6500 & 0xFF = 3   DTC maturation count
0x41eb6  jarl 0x16de6,lp              ; DTC report
```
**Schmitt trigger: SET at |x| ≥ 5530, RELEASE at |x| < 1024.** Counts *rising edges*, saturates at 255.
Cleared to 0 only by `FUN_0003bcb2` @`0x3bd2a` (a reset/init path).
🛑 **The r24 selector at `0x3abfa` tests `!= 0`, not `>= 3`** — so **ONE crossing flips the gain arm and
it stays flipped for the rest of the drive cycle**, well before any DTC matures.

The monitored quantity's producer inputs are **resolver/FOC domain** (`gp-0x501c`/`gp-0x4fd8`) per
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — motor-side, not steering-side.
**Crossing rate on a normal drive is UNKNOWN [BELIEF: the 5530/1024 hysteresis is wide enough to read
as a genuine fault detector rather than chatter].** `gp-0x6ad8` is computed and stored and **never
read anywhere in the image** — an inert read-only tap would settle it at zero on-car risk.

## 3. ⚠ UNRESOLVED CONFLICT — which aggregator term carries LKAS. DO NOT SILENTLY PICK ONE.

- [[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] (2026-08-01): *"`gp-0x6b4c` is the
  ONLY LKAS-sourced summand of the 11"*; labels `gp-0x6ad4` *"resonance, eliminated V56"*.
- [[reference_accord_aggregator_11term_loop_census_units_and_fork]] (2026-08-26/27): its loop-gain
  table labels **`gp-0x6ad4` the LKAS rate-PID P+I+D** (|L| = 0.2565 ∠−171.76° at 7.79 Hz).

**My evidence this session favours the second [EVIDENCE]:**
- `gp-0x6ad4`: exactly 2 touches image-wide — written `0x3a8a0` (tail of `FUN_0003a382`), read
  `0x3aca8` (the aggregator). **`FUN_0003a382` reads `gp-0x67fe`, the LKAS engage state machine, at
  `0x3a704`.**
- `FUN_00026c80` (writer of `gp-0x6b4c` @`0x276f0`/`0x27708`/`0x27716`) touches **ZERO** LKAS-domain
  cells across **49 distinct gp cells** in its whole body (0x26c80–0x27801), checked against
  gp-0x6b2c/2e/30/32/34/36/38/3a, gp-0x69b0, gp-0x6806, gp-0x6807, gp-0x67fe.

[BELIEF] that `gp-0x6ad4` is specifically the rate-PID *output* — reading `gp-0x67fe` proves gating,
not identity. **One of the two files above is stale. I did not edit either** (kit convention: ask
first). Reported to `main` 2026-09-13 for adjudication.
**The r24:LKAS ratio is unaffected either way** — whichever term it is enters the same unweighted
aggregator with a unit coefficient, so **r24 : LKAS = 1 : 1 at the motor**, sharing one downstream
path (`gp-0x6b94` → governor `FUN_0004503c` → `gp-0x6ace` → comp-add `FUN_000456a4` → `gp-0x6acc` →
shaper `FUN_00042af8` → `gp-0x6b08` → `+gp-0x6afe` → `gp-0x6b98`).

## 4. Two smaller structural notes [EVIDENCE]

- **The nine non-r24 aggregator terms are RANGE-VALIDITY GATES, not clamps.** `0x3aa50 addi 0x2000,r9,r12`
  / `0x3aa54 addi -0x4001,r12,r0` / `0x3aa58 cmovc 0x0,r9,r16` ⇒ out of range contributes **0**, not
  the limit. **r24 and r26 alone are true saturating clamps** (`0x3ac42..0x3ac54`, `cmovle`/`movea`,
  ±0x2000). Asymmetric — a describing-function analysis must not use one form for both.
- **The LKAS output shaper at `0x2a8c0..0x2a938` is in a region Ghidra has never analyzed** (read via
  `disassemble_bytes dry_run:true`). It contains the `0x2a904` cal load that `search_instructions` is
  documented to miss. `gp-0x6b38 = clamp(((gp-0x6b2c + shaped) · (pol · LE16(0xC646C))) >> 15,
  ±LE16(0xC61B4))`, Q15. **`0xC61B4` is 512 on stock and 3072 on every V280+ image — a flown 6×
  raise of the LKAS lane ceiling.** Consistent with
  [[reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers]]; that whole
  `~0x2a30e..0x2b421` block still needs analysis + `save_program` by someone with write authority.

## 5. Process note

Six tracing tasks were commissioned; **three of them (the lane form, the "is there a filter", the dt)
were already answered in this directory in more depth than I reached**, and I read the store *after*
tracing rather than before — the exact failure the two existing
`feedback_check_own_memory_before_retracing_*` memories warn about. It also cost a live error: I
offered `0xC61F6` as "a free, untouched, cheap lever" when
[[reference_accord_c61f6_deadband_is_coulomb_friction_not_percentage]] had already disqualified it on
an explicit operator constraint. **Grep this directory by address before tracing, not after.**
