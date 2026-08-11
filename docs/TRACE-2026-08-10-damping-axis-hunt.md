# TRACE 2026-08-10 — Is any damping / friction / loss axis TORQUE- or CURRENT-indexed?

Agent: `DampAxis`. Program: **stock `code.bin`** only (`get_current_program_info` →
`executable_path = /C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin`,
2086 functions). Every byte value below is a **stock** read unless explicitly stated otherwise.
`gp = 0xFEDF8000`, `tp = 0xBF000`. Method throughout: `decompile_function` first, `disassemble_function` /
`disassemble_bytes(dry_run:true)` only to confirm a framed claim, `read_memory` for table bytes,
Bash/grep for lineage.

---

## ANSWER IN ONE LINE

**A torque-magnitude-indexed damping axis exists in THREE places, and a phase-current-magnitude-indexed
gain schedule exists in a fourth — but not one of them is a clean, static, ROM-table cal lever.** The
single most useful new fact is a **one-BYTE index selector, `0xC6498`, that Honda shipped with both arms
written**, which flips the damper's FactorB axis between a rate composite and driver torque.

---

## §1 — CENSUS OF EVERY LERP IN THE ASSIST / COMPENSATION PATH

All rows EVIDENCE (decompile + `read_memory`) unless marked. "Engaged mode" = **26** per RULE 7 (car is
TVCA4, live modes 24/26).

| # | table | X base | Y base | **INDEX SIGNAL (cell + physical identity)** | consumer | mode-idx? | task | Y on mode 26 |
|---|---|---|---|---|---|---|---|---|
| 1 | **FactorB** | rec `0xD774C`+2 | +0x0A | **`gp-0x6bcc` ← `gp-0x6ba6`** = boost-amplitude index (resolver-rate-dominant composite). Selected by cal **`0xC6498`=1**. The DEAD arm computes a **driver-torque magnitude** | `FUN_00034350` | YES `0xC9CCC` | 100 Hz | X=[205,1331,2355,3072] **Y=[1024]×4 FLAT** |
| 2 | FactorC | rec `0xD77xx` | | `gp-0x6a5e` = voted vehicle speed, 64 ct/km/h | `FUN_00034350` | YES `0xC9E9C` | 100 Hz | X=[2240,3840,5120,8960] Y=[0,234,429,908] |
| 3 | FactorD | | | `gp-0x6a10` = abs steering angle | `FUN_00034350` | YES `0xC9DB4` | 100 Hz | X=[0,50,100,150,700] **Y=[1024]×5 FLAT** |
| 4 | FactorE | | | `gp-0x6ac0` = motor/column rate | `FUN_00034350` | YES `0xC9F84` | 100 Hz | X=[60,400,2500,4000] Y=[0,140,539,927] |
| 5 | FactorF (ceiling) | | | `gp-0x6ac2` = counter-torque detector | `FUN_00034350` | YES `0xC77A0` | 100 Hz | X=[300,800] Y=[512,1024] |
| 6 | Friction-comp magnitude | `0xD7A54`+2 | +0x08 | `gp-0x6a5e` = voted vehicle speed | `FUN_00036c12` | YES `0xCBE74` | **1 kHz** | X=[0,1280,5760] **Y=[−9830,−5734,−1966] NEGATIVE** |
| 7 | Mixer output scale | `0xC6ABA` | `0xC6ACA` | `gp-0x69aa` — **Q15 normalised 0…1**, NOT raw speed (see correction) | `FUN_00037fe6` | no | 1 kHz | X=[0,6554,13107,19661,22938,26214,29491,32768] **Y=[1024]×8 FLAT** |
| 8 | Residual shaping | `gp-0x64b8` (RAM) | `gp-0x641c` (RAM) | **\|Path-2 residual\| × `0xC63AE`/1024** — a torque-domain ERROR magnitude | `FUN_00038148` | no | 1 kHz | RAM-built, Y[0]=0 |
| 9 | **Assist curve + its SLOPE** | `gp-0x37fc` (RAM) | `gp-0x37d6` (RAM slopes) | **`abs( clamp(gp-0x4f60, ±cal 0xC6200) + gp-0x6b4a )` = DRIVER TORQUE MAGNITUDE** | `FUN_000352b4` → `gp-0x6b7a`/`gp-0x6b86` (assist) **and `gp-0x69a4` (r26 lane gain)** | no | **1 kHz** | RAM-built |
| 10 | Slope limiter A | `0xC6926` | `0xC692C` | `gp-0x69a8` = `FUN_0004567c(0)` = `gp-0x6958` (identity NOT resolved) | `FUN_00035b20` | no | 100 Hz | not read |
| 11 | Slope limiter B / C | `0xC6912` / `0xC6936` | `0xC691A` / `0xC693E` | `gp-0x6a64` — sole writer `FUN_00041eec` @0x42360, the 5-channel speed voter ⇒ **[BELIEF]** a speed variant | `FUN_00035b20` | no | 100 Hz | not read |
| 12 | 1 kHz angle shaper | `0xC6B66` | `0xC6B80` | `gp-0x6a10` = abs steering angle | `FUN_0003b8f6` | no | 1 kHz | Y=[899…1084] LIVE |
| 13 | Boost curve / amp family | `0xCA154`, `0xCA4F4`, `0xCA23C` | | `gp-0x6ba6` (rate-dominant composite) + `gp-0x6a10` | `FUN_00034a72` | YES | 100 Hz | Y=[552,650,659,554,448,447] |
| 14 | **FOC Iq/Id gain schedule, 12 tables** | `[0xC5462 … 0xC5540]` | | **`gp-0x4ac` = ABC-frame instantaneous PHASE-CURRENT power/torque estimate** (`Ia(Ea−Ec)+Ib(Eb−Ec)`, from current peak-trackers) | `FUN_000757a2` → `FUN_00071272` | speed-branched at `0xC50DA`=640 (10 km/h) | 1 kHz → 4 kHz ISR | see `reference_accord_fun757a2_iqid_gainschedule_bridge_resolved` |
| 15 | Return-to-centre | — | — | **NO LERP EXISTS** — pure state machine on cals `0xC718A`, `0xC727E`, `0xC73C0`, `0xC720C`, `0xC72E2` | `FUN_00036388` | no | — | n/a |

### 🛑 The payoff rows, in bold

- **Row 14 — the FOC Iq/Id gain schedule IS indexed on a phase-CURRENT magnitude.** This is literally the
  Delphi `I_MAG` axis. **But it is a current-loop PI/feedforward GAIN, not a dissipation term** (raising it
  adds loop gain), and all 12 tables sit inside **`[0xC5000, 0xC5FFC)` — the CRC-skipped block behind the
  V40 ignition brick.** Out of bounds for this kit. No lever.
- **Row 9 — `gp-0x69a4`, the r26 lane gain, IS torque-magnitude indexed, IS live at creep, and runs at
  1 kHz.** Sole caller of `FUN_000352b4` is `FUN_0002214a` (`get_function_callers`, single result). No
  speed term and no rate dead-zone anywhere on this index. **But the 10-segment curve is not a ROM table** —
  it is rebuilt every cycle by `FUN_00039702 → FUN_000389ec → FUN_000352b4`, and its ROM seed `0xC6564`
  (40 bytes) is all zero.
- **Row 1 — FactorB's axis is one cal byte away from being driver torque.** Detail below.

---

## §2 / §3 — THE ONE-BYTE INDEX REPOINT AT `0xC6498`

### The dispatch, byte-exact

```
000343ec: ld.bu 0x7498[tp],r7      ; cal 0xC6498   (0xBF000 + 0x7498, computed not eyeballed)
000343f0: cmp   0x1,r7
000343f2: be    0x00034424         ; ==1 -> TAKEN on stock
   ...ELSE ARM (0x343f4-0x3441e): |EMA(gp-0x4f60)| composite, see below...
00034424: ld.hu -0x6ba6[gp],r10    ; TAKEN ARM: index := boost-amplitude index
00034428: ld.h  -0x6b9a[gp],r13
0003442c: zxh   r10
00034438: st.h  r10,-0x6bcc[gp]    ; gp-0x6bcc = FactorB's LERP index
```

`read_memory 0xC6494,16` = `6400 f401 01 01 0000 0000 0101 0001 0001` ⇒ **`0xC6498` = 1, `0xC6499` = 1**.

- **Parity trap neutralised.** `ld.bu` carries displacement bit 0 in hw1 bit 5 (the `0x3C`/`0x3D` trap), so
  `0xC6498` vs `0xC6499` is normally ambiguous from a scan. **Here both bytes read 1**, so the branch is
  taken either way — the conclusion is parity-robust.
- **Off-by-0x1000 anchor.** `0xC6499` = 1 reproduces the independently-recorded "boost-curve index
  `0xC6499`=1". Address arithmetic confirmed.

### What the dead ELSE arm computes (`0x343f4`–`0x3441e`)

```python
# integer mirror of 0x34392-0x3441e, stock cals, LE
ema   = gp_m6df8 + (( (gp_4f60 * 32) - gp_m6df8) * u16(0xC636E)) >> 10   # 0xC636E = 4096
comp  = (((gp_6c2e * u16(0xC636C)) >> 5) * polarity * (polarity+1 < 3) + ema) >> 5   # 0xC636C = 0x1000
comp  = clamp(comp, -25600, +25600)
idx   = abs(comp)
if idx > gp_4f68:                      # secondary select
    idx = abs(gp_4f60 if gp_4f60*comp > 0 else -gp_4f60)
gp_6bcc = idx                          # <- A DRIVER-TORQUE MAGNITUDE
```

⇒ **setting `0xC6498` 1→0 repoints FactorB's index from a resolver-rate composite to driver torque.**
One byte. No displacement edit, no cave. The cheapest index repoint in this image.

### Dimensional sanity after the repoint — it holds

FactorB's X (byte-read, mode 24 `0xD6760` and mode 26 `0xD774C`, **byte-identical**):
`n=4, X=[205, 1331, 2355, 3072], Y=[1024,1024,1024,1024], term=0`.
Against the torque validity window ±25600, X spans **0.8 % → 12 %** of the sensor range — a sensible
low-to-mid driver-effort axis. Against the current index's ±13000 window it spans 1.6 % → 24 %. Honda
evidently calibrated an X that works in both domains, consistent with having shipped both arms.

### 🛑 Why the repoint alone buys NOTHING, and the honest price

1. **FactorB's Y is flat 1024×4 on the engaged mode.** Repointing the index of a flat table is a literal
   no-op. You would need the repoint **and** a Y reshape — two edits, and the Y edit is the real one.
2. **FactorB is a multiplier inside a pure product.** `product = seed·B·C·D·E >> 40`; `FactorC(speed)` has
   `Y[0]=0` below 2240 ct = 35 km/h, and C is applied before D. **Zero propagates.** Below 35 km/h no
   FactorB value can produce anything but 0.
3. **`FUN_00034350`'s sole caller is `FUN_00022ca0` = 100 Hz** (`get_function_callers`, single result).
   Per the brief's own ZOH table that is 38–51° of transport lag at 21–28 Hz ⇒ **structurally incapable of
   addressing grinding.** At best a ≥35 km/h, 6–9 Hz lever.

### 🛑🛑 LINEAGE — this is NOT a new discovery, and saying so matters

`grep` over `analysis-2020accord/build_v*_tva.py`:
- **`0xC6498` has NEVER been written.** It appears only in assert-stock dictionaries.
- **`build_v48b_tva.py:42` already recorded the mechanism**, in July: *"the 2 mode-gated DORMANT reads
  (`FUN_00034350` @0x34392, `FUN_00034a72` @0x34ace) — bypassed in stock cal (0xC6498/0xC6499=1), so
  repointing them buys nothing live and only adds surface."* `build_v59_tva.py:382` asserts both bytes
  are 1 as a precondition.
- What IS new here: (a) the **identity** of what the dormant arm computes (a driver-torque magnitude, with
  the exact arithmetic above), and (b) the **flat-unity Y on the engaged column**, which is the reason the
  repoint is inert and which V48B did not state.

### The other single-load repoint candidates

Every FactorX index is a single `ld.hu` with a 16-bit gp displacement — all mechanically repointable:

| index load | addr | current cell | X axis | dimensionally sane if read as torque (±25600)? |
|---|---|---|---|---|
| FactorB | `0x34424` | `gp-0x6ba6` | [205,1331,2355,3072] | **YES** — 0.8–12 % of range |
| FactorC | `0x344e0` | `gp-0x6a5e` (speed) | [2240,3840,5120,8960] | **YES — and interestingly so**, 8.8–35 % of range. Read as torque, `Y=[0,234,429,908]` becomes *exactly* the Delphi shape: zero below a torque offset, rising with torque |
| FactorD | `0x34582` | `gp-0x6a10` (angle) | [0,50,100,150,700] | marginal — top breakpoint is 2.7 % of range, the table would saturate almost immediately. Also flat-unity ⇒ inert |
| FactorE | `0x345fa` | `gp-0x6ac0` (rate) | [60,400,2500,4000] | YES dimensionally, but E's own gate (`gp-0x6ac0 ≥ 13001`) zeroes the WHOLE product and would be left reading the rate cell regardless |
| FactorF | `0x346a4` | `gp-0x6ac2` | [300,800] | n/a, ceiling only |
| Mixer (row 7) | `0x380b6` | `gp-0x69aa` (Q15 0…1) | [0…32768] | **NO** — X[7]=32768 exceeds the ±25600 validity ⇒ top segment unreachable. And Y is flat ⇒ pointless anyway |

**The FactorC repoint is the structurally interesting one** — it converts a speed dead-zone into a torque
dead-zone and reproduces `GAIN = max(0, K_G·(I_MAG − G_OFFSET))` with `G_OFFSET = 2240` counts, using
Honda's own Y values, with no step at zero rate and therefore **no V80 relay hazard**. Two caveats before
anyone prices it: **(a)** it is still 100 Hz ⇒ 6–9 Hz only, never grinding; **(b)** `FactorE`'s 60-count
rate dead-zone still multiplies in, so the product remains 0 below ~12.7 °/s. [BELIEF: I have not sized
2240 counts of `gp-0x4f60` in Nm — the sensor scale is not established in my memory, and that number
decides whether the offset is "light pressure" or "armstrong". **This is the single thing I would verify
before anyone builds it.**]

---

## §4 — TASK RATES, APPLIED

| function | sole caller | rate | can it address 18–28 Hz? |
|---|---|---|---|
| `FUN_00034350` damper (FactorA–F) | `FUN_00022ca0` | **100 Hz** | **NO** |
| `FUN_00034a72` boost | `FUN_00022ca0` | **100 Hz** | **NO** |
| `FUN_00035b20` slope limiters | `FUN_00022ca0` | **100 Hz** | **NO** |
| `FUN_000352b4` assist curve + `gp-0x69a4` | `FUN_0002214a` | **1 kHz** | **YES** |
| `FUN_00036c12` friction comp | `FUN_0002214a` | **1 kHz** | **YES** |
| `FUN_00038148` / `FUN_00037fe6` / `FUN_0003b8f6` | `FUN_0002214a` | **1 kHz** | **YES** |
| `FUN_000757a2` FOC schedule | `FUN_0002214a` → 4 kHz ISR | 1 kHz / 4 kHz | yes, but out of bounds |

All four callers confirmed this session by `get_function_callers`, each returning exactly one result.

⇒ **Every mode-indexed factor family lives on the 100 Hz task. Nothing in the FactorA–F damper can ever
touch grinding.** The only torque-indexed damping-side gain that runs fast enough is `gp-0x69a4` (row 9),
and it has no ROM table.

---

## §5 — `FUN_00036c12`'s SIGN — **SETTLED: DISSIPATIVE, same sense as the damper**

Open since 2026-08-06. Answer: **`gp-0x6b26` is NOT anti-dissipative. Its effective sign matches the
damper's, and the result is structurally guaranteed rather than calibration-dependent.**

### Leg 1 — the lane's own gain is NEGATIVE [EVIDENCE, fresh byte read on the ENGAGED column]

`0xCBE74 + 26*4 = 0xCBED4+8` → pointer `0x000D7A54`. `read_memory 0xD7A54,16`:
`0300 0000 0005 8016 9ad9 9ae9 52f8 0000` ⇒ `n=3, X=[0,1280,5760] ct = [0,20,90] km/h,
Y=[−9830, −5734, −1966]`. **Mode 24 (`0xD6A64`) is byte-identical.** RULE 7 satisfied.

```python
# integer mirror of 0x36c12, annotated
gain = lerp(gp_6a5e, X=[0,1280,5760], Y=[-9830,-5734,-1966])   # ALWAYS NEGATIVE
raw  = (gate(gp_6c2c) * gain) >> 6                              # 0x36cbe mulh / 0x36cc0 sar 6
out  = (raw * 0x111) >> 0x12                                    # 0x36cc4 mul / 0x36cca sar 18
gp_6b26 = clamp(out, -511, +511)                                # cal 0xC407E = 511
# net |k|: 9830*273/2**24 = 0.1600 at 0 km/h ; 0.0933 at 20 ; 0.0320 at 90
```
⇒ **`gp-0x6b26 = −k · gp-0x6c2c`, k > 0.** Clamp reached at |gp-0x6c2c| = 511/0.160 = 3194 counts.

### Leg 2 — both lanes enter the SAME node with the SAME sign and the SAME weight [EVIDENCE]

`FUN_00038148` stage 1 (decompile) sums six lanes, each `+`:

| lane | cell | weight cal | stock value | zero-reject window (from the decompile's own range test) |
|---|---|---|---|---|
| `gp-0x6b4e` | LKAS-class | `0xC63A8` | 1024 | ±0x2800 = 10240 |
| `gp-0x6b4c` | LKAS | `0xC63AA` | 1024 | ±10240 |
| **friction** | `gp-0x6b26` | **`0xC63A6`** | **1024** | **±0x400 = 1024** |
| `gp-0x6b46` | torque-domain | `0xC63A4` | 1024 | ±1024 |
| **damper** | `gp-0x6bd0` | **`0xC63A0`** | **1024** | **±0x800 = 2048** |
| boost | `gp-0x6bbe` | `0xC63A2` | 1024 | ±2048 |

`read_memory 0xC63A0,16` = `0004 0004 0004 0004 0004 0004 6600 0004` ⇒ all six weights = **+1024**,
`0xC63AC` = 102 (the α≈0.0996 EMA), `0xC63AE` = 1024. **These windows reproduce the brief's stated
zero-reject numbers exactly** — independent corroboration of both.
⇒ damper and friction lane are added with identical positive weight and identical sign. **No relative
inversion exists at the summing node.**

### Leg 3 — the phase, and why the conclusion cannot flip

Damper: `gp-0x6bd0 = −sign(gp-0x6abe) · product` (`0x3469e cmp r0,r11 / 0x346a0 ble / 0x346a2 subr r0,r8`).
Its fundamental is **180° from rate** ⇒ real part vs rate **negative** ⇒ dissipative. This is the
calibrated reference.

Friction lane: `gp-0x6b26 = −k · gp-0x6c2c`. `gp-0x6c2c`'s producer is `FUN_00041464` (`st.h r26,-0x6c2c,gp`
@`0x4184e`, `sar 0x9,r26` immediately prior; second store `0x41ac2`; **no other writer image-wide**,
`search_instructions` 8 hits, all adjudicated). That producer is a backward difference of motor rate
wrapped in first-order EMAs.

**Structural bound.** A backward difference contributes `+90° − ωT/2`. Each first-order EMA contributes a
lag strictly in `(−90°, 0°)`. With the recorded two-pole chain (α = 37/128 and 22/64, corners 54.3 Hz and
67.0 Hz at fs = 1 kHz), total phase of `gp-0x6c2c` vs rate:

| band | fs = 1000 Hz | fs = 312.5 Hz | phase of `−gp-0x6c2c` vs rate | Re(·) vs rate |
|---|---|---|---|---|
| 7.79 Hz | +76.4° | +48.9° | 256° / 229° | **negative** |
| 21.09 Hz | +54.6° | +4.2° | 235° / 184° | **negative** |
| 28.1 Hz | +44.3° | −8.1° | 224° / 172° | **negative** |

**In all six cells the real part vs rate is negative ⇒ dissipative, in the same sense as the damper.**
For the sign to flip, cumulative lag between the difference and `gp-0x6c2c` would have to exceed **180°** —
unreachable with two first-order poles, which asymptote to 180° and never reach it, plus a ≤5° ZOH term.
**The dissipative sign is therefore structural, not calibration-dependent.**

⇒ **`gp-0x6b26` currently REDUCES effective inertia / adds dissipation. It is inertia COMPENSATION, not
inertia emulation. Lowering it would remove damping.** [The absolute magnitudes in the table are
[BELIEF] to the extent they depend on the α values, which I carried from
`reference_accord_gp6b98_aggregator_definitive_lane_table_v57` rather than re-deriving from `FUN_00041464`
this session — but the **sign**, which is what was asked, does not depend on them.]

🛑 Lineage on `0xC407E`: the hard-fault interlock, 511 on stock and every build V38–V89; V73 raised it to
850 and **V74/V75 FAULTED**; V81 restored 511. Not proposed here in either direction.

---

## CORRECTIONS TO THE RECORD

1. **🛑 `reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm` is WRONG about
   FactorB's index.** It records "idx = a signed/abs quantity built from `gp-0x4f60`". That is the
   **`0xC6498`==0 arm, which is DEAD on this calibration**. The live index is `gp-0x6ba6`. The earlier
   trace read the decompile but never read the selector byte. (Memory not edited — reporting per the
   standing instruction.)
2. **🛑 The brief's identity for `gp-0x69aa` is wrong.** It is not raw vehicle speed. `read_memory
   0xC6ABA,32` gives X = `[0, 6554, 13107, 19661, 22938, 26214, 29491, 32768]` = **0, 0.2, 0.4, 0.6, 0.7,
   0.8, 0.9, 1.0 × 32768** — a **Q15-normalised 0…1 ratio**, gated `< 0x8001`. 32768 raw counts would be
   512 km/h at 64 ct/km/h. It may still be *derived* from speed, but the axis is normalised.
3. **NEW: the mixer's output-scale LERP (`0xC6ABA`/`0xC6ACA`) is FLAT UNITY — `Y=[1024]×8` — hence inert.**
   Zero mentions in any build script, ever. Another Honda hook left flat, alongside FactorB and FactorD.
4. **`FUN_00036388` (return-to-centre) contains NO LERP at all** — it is a pure state machine. It should
   be dropped from any future "factor family" enumeration.

---

## LINEAGE TABLE (grep over `analysis-2020accord/build_v*_tva.py`)

| address | what | ever WRITTEN? |
|---|---|---|
| `0xC6498` | FactorB index selector byte | **NO** — assert-stock only (V48B, V50, V52, V52c, V59) |
| `0xD774C` | FactorB record, **mode 26** | **NO** — zero mentions, ever |
| `0xD6760` | FactorB record, mode 24 | NO — assert-untouched only (V77, V81, V83a, V84) |
| `0xC6ABA` / `0xC6ACA` | mixer LERP (flat) | **NO** — zero mentions, ever |
| `0xC63A6` | **friction-lane weight in the mixer** | **NO** — zero mentions, ever (siblings `0xC63A0`/`A2`/`AC`/`AE` have all been touched) |
| `0xC6178` | slot-fill snap threshold, 5274 | **NO** — zero mentions, ever |
| `0xC6564` | r26 seed, 40 bytes all zero | asserted V67–V70, V84 |
| `0xC63A0` | Path-2 damper weight | **YES** — 2048 on V72–V75/V81, silently reverted at the V38 rebase; **1024 (Honda's) on V85/V86 → current** |
| `0xC407E` | hard-fault interlock | YES — V73 raised to 850, **V74/V75 FAULTED**, V81 restored 511 |
| `0xC5462`–`0xC5540` | FOC current-indexed tables | NO — and **inside the CRC-skipped block, out of bounds** |

---

## OPEN / WOULD NEED TO VERIFY

1. **The Nm-per-count scale of `gp-0x4f60`.** Decides whether FactorC's 2240-count breakpoint, read as a
   torque offset, is light pressure or a shove. **This is the gating unknown for the only structurally
   attractive repoint in the report.** Next step: find the torque-sensor ADC scaling in the sensor
   acquisition path and pin counts→Nm.
2. `gp-0x6958` (= `gp-0x69a8` via `FUN_0004567c(0)`) — identity unresolved; row 10's axis is therefore
   unnamed.
3. `gp-0x6a64` — writer is the speed voter `FUN_00041eec` @`0x42360`; "a speed variant" is [BELIEF], not
   decompiled.
4. `FUN_00041464`'s exact EMA α values for the `gp-0x6c2c` branch were carried from memory, not
   re-derived. Does **not** affect §5's sign conclusion; does affect the phase magnitudes quoted.
5. `FUN_00034a72`'s boost family was characterised from prior memory plus the `0xC6499` byte, not
   re-decompiled in full this session.

---
---

# PART 2 — SIZING `gp-0x6b26` (2026-08-10, second tasking)

All byte reads verified on **BOTH** stock `code.bin` and
`_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin` (sha256 `6eae6826881cb5fd…`).
Sizing script: `<scratchpad>/size_6b26.py`.

## 🛑 0. THE BRIEF'S PREMISE IS STILL WRONG — `gp-0x6a5e` IS VEHICLE SPEED

Two of the four tasking messages instruct me to treat `0xCBE74`'s index as **voted driver torque**, and
build arguments on it ("strongest on-centre and hands-light", "least damping at high load, and load is
where ζ_friction is largest"). **The index is voted VEHICLE SPEED.**
`search_instructions mnemonic=st.h operand=6a5e` ⇒ **exactly ONE writer, `FUN_00041eec` @`0x42342`**, the
5-channel vehicle-speed voter. Corroborated four ways (see Part 1 §Corrections). **Every argument built
on the torque reading is void, and the correct reading points to a different and better intervention
(§6 below).**

## 1. THE PRODUCER CHAIN, byte-exact — closes the last BELIEF in Part 1 §5

`FUN_00041464`, decompiled fresh. `tp` addresses computed in code, never by eye.

```python
# gp-0x6c2c producer.  1 kHz (caller FUN_0002214a).
valid = -13000 <= gp_4f50 <= 13000        # (rate+13000) > 0x6590(26000) -> fail
x     = gp_4f50 * 1024
s1   += (x - s1) * cal(0xC643C) >> 7      # EMA1, alpha = 37/128  = 0.289063
d     = s1[n] - s1[n-1]                   # TRUE backward difference
d32   = clamp(d * 32, +-0xfa0000)         # 16,384,000
s2   += (d32 - s2) * cal(0xC40DC) >> 6    # EMA2a, alpha = 22/64  = 0.343750
gp_6c2c = s2 >> 9                         # net linear gain 1024*32/512 = 64
```
`0xC643C` = **37**, `0xC40DC` = **22** — byte-read, stock == V89. **Exactly two first-order poles and one
differencer**, which is precisely the structure Part 1 §5's bound assumed. ⇒ **§5's phase table is now
EVIDENCE end to end, not BELIEF** — the α values it used are the real ones.

**Fourth producer-clamped tautology found:** `|gp_6c2c| <= 16384000/512 = 32000` by construction, and
`FUN_00036c12`'s own guard passes exactly `[-32000,+32000]`. The guard can never fire.
**Fifth:** the validity test `[-13000,+13000]` equals `gp-0x4f50`'s own producer clamp in `FUN_00068f52`.

**Scale, DERIVED from code (not from bus torque — that route is VOID on record):** in the live branch
`gp-0x6abe = (uVar16 >> 10)` = `EMA1(gp-0x4f50)`, and the alternate arm rescales by
`cal(0xC6134)/1000` with offset `cal(0xC648E)` — byte-read **1000** and **0**, so **both arms are
numerically identical** (the config byte `0xC40ED`=0 ≠ 0xE9 selects the pass-through anyway).
EMA1 has DC gain 1 ⇒ **`gp-0x4f50` carries the same 4.7121 counts/(°/s) scale as `gp-0x6abe`.**

| band | \|gp-0x6c2c\| per count of rate | phase vs rate | Re part of `−gp-0x6c2c` vs rate |
|---|---|---|---|
| 7.79 Hz | 3.080 | +76.4° | **negative (dissipative)** |
| 21.09 Hz | 7.547 | +54.6° | **negative** |
| 28.1 Hz | 9.267 | +44.3° | **negative** |

## 2. 🛑 SATURATION DUTY — **NOT a relay. Not close.**

`k = |Y|·273/2^24` ⇒ 0.1600 at 0 km/h · 0.0933 at 20 · 0.0320 at 90. Clamp `0xC407E` = 511.

| band / speed | column amplitude needed to SATURATE |
|---|---|
| 7.79 Hz @ 0 km/h | **4.50°** (220 °/s) |
| 21.09 Hz @ 90 km/h | **3.39°** (449 °/s) |
| 28.1 Hz @ 90 km/h | 2.06° (366 °/s) |

Against the corpus's own measured ratchet amplitude (**1.29–1.92° peak-to-peak ⇒ 0.645–0.96° amplitude**):

| operating point | \|gp-0x6b26\| | % of ±511 | saturation DF |
|---|---|---|---|
| 7.79 Hz @ 0 km/h, 0.645° | 73.3 | **14.3 %** | **1.000** |
| 7.79 Hz @ 0 km/h, 0.96° | 109.1 | **21.3 %** | **1.000** |
| 21.09 Hz @ 90 km/h, 0.5° | 75.4 | 14.7 % | **1.000** |

⇒ **The term is operating in its linear region with 4.7× headroom. It is NOT already a bang-bang relay,
and raising `k` is a clean linear damping increase, not a V80-class move.** Saturation DF stays **exactly
1.000 through ×4**; first departure is ×6 (0.881), ×8 (0.700).
⚠ Amplitudes are only *measured* for the ratchet band. Pairing the ratchet's amplitude onto 28 Hz is
unphysical and I have not done it in the conclusions.

## 3. ★★ THE ZERO-REJECT QUESTION — answered, and it is the best news in this report

The brief asks: output or input? **OUTPUT** — `FUN_00038148` tests the lane value itself:
`gp-0x6b26 * (uint)((gp-0x6b26 + 0x400) < 0x801)` ⇒ passes only `[-1024, +1024]`, else the lane
contributes **0**.

🛑 **But `gp-0x6b26` is already clamped to ±511 by `0xC407E`, and 511 < 1024 ⇒ THE ZERO-REJECT IS
STRUCTURALLY UNREACHABLE.** Sixth producer-clamped tautology. Same for the damper: window ±2048, and
`gp-0x6bd0`'s ceiling is at most 1024 (FactorF table max) or **512** (scalar fallback `0xC6158` — byte
read after correcting my own off-by-0x1000; see §8) ⇒ **also unreachable.**

⇒ **Neither lane can suffer the full-magnitude dropout. The remedy does not die on deadband, and it does
not die on authority. Both failure modes that killed the rate-indexed damper are absent here.**

🛑 **Corollary, and it re-reads `0xC407E`:** the 511 clamp is doing double duty — it is also what keeps
the lane under the mixer's dropout cliff. **Raise it above 1024 and the lane ACQUIRES the ability to
zero-reject**, a discontinuous full-magnitude dropout that does not exist today. V73's 850 stayed under
1024, so that is *not* what faulted V74/V75 — but it is one more reason 511 must stay.

## 4. 🛑🛑 THE DOSE — I CANNOT GIVE ONE, AND THE REASON IS IMPORTANT

Target quoted to me: **~29 counts at creep, ~6 at highway.**
Measured now, at ×1: **73–109 counts at creep, ~75 at highway.**
⇒ implied multiplier **0.40× at creep, 0.08× at highway — BELOW UNITY.**

**The term already delivers 2.5–18× the stated requirement.** Either
**(a)** the 29/6 figures are quoted at a different node (the ring was measured at `gp-0x6b98`, not at
`gp-0x6b26`), or **(b)** the term already supplies enough dissipation and the lever is unnecessary.

**I measured the referral factor the brief told me to check rather than inherit** — `gp-0x6b26` →
`gp-0x6b70`, from the `FUN_00038148` decompile:
weight `0xC63A6`=1024 (>>10 = ×1) × cal `0xC6468`=2639 (>>10 = ×2.577) × 16, then stage-2 `>>4`
(the ×16 and >>4 cancel **exactly**), through the `0xC63AC`=102/1024 EMA:

| band | EMA \|H\| | **net referral** |
|---|---|---|
| 7.79 Hz | 0.9063 | **×2.336** |
| 21.09 Hz | 0.6212 | ×1.601 |
| 28.1 Hz | 0.5115 | ×1.318 |

**The referral makes `gp-0x6b26` LARGER downstream, not smaller** — so it moves the discrepancy the wrong
way and cannot rescue reading (a) on its own.

⇒ **STOP. The node at which "29 counts" is quoted must be stated before any multiplier can be chosen.**
Picking one now would be inventing a dose. This is the single blocking question.

## 5. SAFETY LIMIT — ×3, for two independent reasons that coincide

Column amplitude at which the ±511 clamp begins to bind:

| mult | creep 7.79 Hz @0 km/h | highway 21.09 Hz @90 km/h | Y at creep row | int16? |
|---|---|---|---|---|
| ×1 | 4.50° | 3.39° | 9,830 | ok |
| ×2 | 2.25° | 1.69° | 19,660 | ok |
| **×3** | **1.50°** | **1.13°** | **29,490** | **ok (last)** |
| ×4 | 1.12° | 0.85° | 39,320 | 🛑 **OVERFLOWS int16** |

Measured max ratchet amplitude **0.96°** ⇒ ×3 keeps a **1.56× margin**, ×4 collapses to 1.17×.
**And Y overflows `int16` at the creep row above ×3.** Two independent limits land on the same number.
⇒ **Safety limit ×3; ×2 comfortable.** Note the highway row (`|Y|`=1966) has arithmetic room to ×16.

## 6. ★★ THE SHAPE — FLATTEN, DON'T SCALE (and this only becomes visible once the axis is right)

With the axis correctly read as **speed**:

| speed | \|Y\| | k | meaning |
|---|---|---|---|
| 0 km/h | 9830 | 0.1600 | **MOST damping** |
| 20 km/h | 5734 | 0.0933 | |
| 90 km/h | 1966 | 0.0320 | **LEAST damping** |

⇒ **Honda's schedule is RIGHT-way for the creep ratchet and WRONG-way for the highway grind.** The
brief's "least damping at high load, where ζ_friction is largest" reasoning is void; the real statement
is "least damping at high SPEED", and the grinding is the highway symptom.

⇒ **Flattening — lifting the 20 and 90 km/h rows toward the 0 km/h value — is strictly better than a
uniform multiplier here:**
- it adds damping **exactly where the grind lives** and nowhere else;
- it leaves the creep row untouched, and creep is where `k` is already 5× larger and nearest the rail;
- it never approaches the int16 ceiling (the 90 km/h row has 16× of room);
- a ×5 flatten (1966 → 9830) is **×1.0 at creep**, i.e. zero change to the regime closest to saturating.

**On US7523806B2's "ramp the scaling factor from zero, never lift a `Y[0]` off zero":** that rule guards
against a step at **zero rate**. This table's axis is **speed**, so `X[0]=0` means *stationary*, not zero
rate — and `Y[0]` is already at its maximum magnitude. **The V80 step-at-zero-rate failure mode does not
apply to this table at all.** Flattening the upper rows introduces no discontinuity anywhere.

## 7. THE ENGAGEMENT / RATE-INDEPENDENCE TENSION — engaged with, not skipped

**Does `gp-0x6c2c` grow with engagement? [BELIEF, structurally supported, not measured.]** Yes in
principle: `gp-0x6c2c` ← `gp-0x4f50` = rotor-speed estimate, and under LKAS the motor is commanded, so
there is a closed physical path `gp-0x6b98 → FOC → motor → resolver → gp-0x4f50` that has no
hands-off-manual counterpart. I have not measured it.

🛑 **But the tension the brief flagged is real and I cannot dissolve it.** `gp-0x6c2c` is
acceleration-like; at fixed frequency its amplitude is proportional to the ring's rate. A term driven by
it therefore scales with rate. The corpus says the engagement amplification is **rate-INDEPENDENT**
(`eng × log rate` +0.022 [−0.070, +0.116]). **A linear rate-proportional term cannot produce a
rate-independent signature.**

⇒ **This is a genuine strike against `gp-0x6b26` as the CAUSE of the symptom, and I am recording it as
such.** It is *not* a strike against it as a **remedy**: a dissipative term does not have to be the cause
to quench an FIV limit cycle in a plant measured at `Re(Z) < 0`. **I would not defend this cell as the
mechanism. I would defend it as a damper, and only that.**

## 8. 🛑 MY OWN ERROR, CAUGHT AND CORRECTED — the off-by-0x1000, sixth recurrence

I read FactorF's scalar fallback `tp+0x7158` as **`0xC7158`** and got 45496, which would have produced a
false hazard claim ("the damper's fallback ceiling exceeds its ±2048 window ⇒ dropout risk"). The correct
address is `0xBF000 + 0x7158 =` **`0xC6158`** = **512**, which is *safe* and gives the opposite
conclusion (§3). Caught by re-checking against the documented trap before reporting. Every other `tp`
conversion in this report was computed in code and re-verified: `0x7498→0xC6498`, `0x73a0→0xC63A0`,
`0x743c→0xC643C`, `0x50dc→0xC40DC`, `0x7134→0xC6134`, `0x748e→0xC648E`, `0x507e→0xC407E`.

## 9. V89 CONFIRMATION (as instructed — not stock)

| item | stock | V89 | |
|---|---|---|---|
| `0xCBE74[24]` ptr | `0xD6A64` | `0xD6A64` | same |
| `0xCBE74[26]` ptr | `0xD7A54` | `0xD7A54` | same |
| m24 record | n=3, X=[0,1280,5760], Y=[−9830,−5734,−1966] | **identical** | |
| m26 record | same | **identical** | |
| `0xC407E` | 511 | 511 | same |
| `0xC643C` / `0xC40DC` | 37 / 22 | 37 / 22 | same |
| `0xC63A6` / `0xC63A0` / `0xC6468` / `0xC63AC` | 1024 / 1024 / 2639 / 102 | identical | |
| `0xC6158` | 512 | 512 | same |
| `0xC6498` (byte) | 1 | 1 | same |
| `0xC40D2` | 102 | **204** | ← V89's own lever |

⇒ **`0xCBE74` is virgin on V89.** Both mode records must be written together; they are byte-identical.

🛑 **Do not conflate V89's lever with this one.** `0xC40D2` is the modelled-Coulomb scale inside
`FUN_0003b8f6` (Path 2's plant model). `0xCBE74` is the inertia/friction-comp LERP inside
`FUN_00036c12`. **Two different friction terms, two different functions, unrelated cells.**

## 10. THRESHOLD CAVEAT, APPLIED

Under quasi-harmonic FIV the response to added damping is **threshold-like**: below threshold nothing
visible happens, above it the vibration quenches. ⇒ **a small-dose null on this lever must NOT be read as
falsification.** The kit's dose-ladder method is structurally prone to exactly that misreading. Given the
×3 safety ceiling there is room for **at most one meaningful rung above ×2** — so a ladder is the wrong
shape here. **Go to the safety limit or don't go.**

---
---

# PART 3 — LINEAGE CORRECTION, GATE 2, AND THE DOSE (2026-08-10, third tasking)

## 🛑🛑 0. CORRECTS PART 2 §9 — `0xCBE74` IS NOT VIRGIN. IT FLEW AT ×1.5 ON FOUR IMAGES.

Part 2 §9 said *"`0xCBE74` is virgin on V89."* That is **literally true and materially misleading** — it
scoped a virginity claim to one image, and it was read downstream as "never written". Cross-build
dereference of `0xCBE74 + mode*4` **on the images**:

```
build                         m24 Y (0xD6A64)        m26 Y (0xD7A54)          0xC407E
stock                         [-9830,-5734,-1966]    [-9830,-5734,-1966]          511
v73                           [-9830,-5734,-1966]    [-9830,-5734,-1966]          850
v74_engagedcols_x0_12_addonly [-9830,-5734,-1966]    [-14745,-8601,-2949] x1.5    850
v75_CY0.566_magprobe          [-9830,-5734,-1966]    [-14745,-8601,-2949] x1.5    850
v77                           [-9830,-5734,-1966]    [-14745,-8601,-2949] x1.5    850
v81 .. v89                    [-9830,-5734,-1966]    [-9830,-5734,-1966]          511
```

`build_v74_tva.py:79` names it: **"LEVER D' — THE FRICTION LANE ×1.5."** `BUILD-LINEAGE.md` carries a
2026-08-07 correction of record (*introduced by V73, not V74*) and **"the friction row is 14 sites, not
one"** (`0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C 0xD2A5C 0xD3A5C 0xD3A6C 0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C
0xD8A5C 0xD9A5C 0xD9A6C`; Honda `9ad99ae952f8` → ×1.5 `67c667de7bf4`).

**On-car:** V73 (×1.5 + clamp 850) **FLEW CLEAN**, n=1. **V74 and V75 HARD-FAULTED**, latched total loss
of assist — attributed to `0xC407E`=850, not this row (the clamp cell is mode-proof; V74 faulted with
LKAS *disengaged*). V81 reverted **both together** ⇒ ×1.5 and the clamp are **confounded across the whole
V73–V81 arc**. ⚠ **Mode 24 was never touched on any build** — the edit was engaged-column-only, so
"both records must be written" is a new requirement, not a restoration.

⇒ **Genuinely untried: ×1.5-or-higher WITH the clamp at 511.** No image has that pair.
⇒ **Treat ×1.5 as effectively already tested and null** — it was on the car for the V73→V77 era with
grinding present throughout. Under the FIV threshold framing it was below threshold. **A dose ladder is
the wrong shape; ×1.5 is a known-null rung.**

## 1. DOSE — on the correct (dissipative) projection, the requirement is already met at ×1

Only the **real-vs-rate** component is damping; the rest is reactive.

| case | \|6b26\| | cos | **dissipative** | →`gp-0x6ad6` | need@`6b98` | ratio |
|---|---|---|---|---|---|---|
| creep 7.79 Hz, 0.645° | 73.3 | 0.235 | 17.2 | 40.2 | 29 | **1.38×** |
| creep 7.79 Hz, 0.96° | 109.1 | 0.235 | 25.6 | 59.8 | 29 | **2.06×** |
| highway 21.09 Hz, 0.134° | 20.2 | 0.579 | 11.7 | 18.7 | 6 | **3.12×** |

Referral `gp-0x6b26 → gp-0x6ad6` = **×2.34 / ×1.60 / ×1.32** (weight byte `0xC64B0`=1 byte-read;
`0xC6468`=2639; the ×16 and stage-2 `>>4` cancel exactly; `0xC63AC`=102/1024 EMA; mixer LERP `0xC6ACA`
flat 1024 ⇒ ×1). Ladder in multiples of requirement: ×1.5 → 2.1–4.7 · ×2 → 2.8–6.2 · **×3 → 4.2–9.4**.

**Safety ceiling ×3**, two coinciding limits: clamp binds at 1.50° (vs 0.96° measured, 1.56× margin) and
`|Y|`×4 = 39320 **overflows int16**.

## 2. SATURATION — threshold yes, duty no

`|gp-0x6b26|` = **73–109 ct = 14–21 % of ±511** at the measured ring. Saturation needs **4.50°** column
amplitude at creep / 3.39° at 21 Hz. 🛑 **A ">5 % of frames" DUTY cannot be computed statically** — no
build has ever probed `gp-0x6c2c`. The probe is the instrument.
**Biased DF does not apply here**: `gp-0x6c2c` is *differenced*, rejecting a quasi-static bias 78×
relative to 7.79 Hz. DF = **1.000 through ×4** (kit scale: Honda 1.00 · V75 1.45 · V80 3.27).

## 3. ★★ GATE 2 — sign closable and total; magnitude not closable

Closed loop: `gp-0x6b26 → gp-0x6b70 → gp-0x6ad6 → PID → aggregator → gp-0x6b98 → FOC → motor →
resolver → gp-0x4f50 → gp-0x6c2c → back in`. **A loop-gain edit.**
🛑 **Magnitude NOT statically closable** — the PID gain is runtime-scheduled.
✅ **Sign closable at every frequency to Nyquist**: phase of `−gp-0x6c2c` vs rate = +76.4° @7.79, +54.6°
@21, +44.3° @28, +9.7° @60, −12.0° @100, −25.0° @200 — **never reaches −90°.** Two first-order poles
contribute ≤180° and the differencer starts at +90°, so −90° is approached asymptotically and never
crossed. ⇒ **raising this gain cannot destabilise by sign at any frequency.**

## 4. SHAPE — flatten; and `X[0]` is not a step

k = 0.1600 @0 km/h → 0.0320 @90 (axis is **speed**) ⇒ right-way for creep, wrong-way for the highway
grind. **Flattening the 20/90 km/h rows to 9830 (×1.71, ×5.0) with the creep row unchanged** targets the
grind, costs nothing where the lane is nearest its rail, and has no int16 risk.
🛑 **`X[0]=0, Y[0]=−9830` is NOT a step, and US7523806B2's "never lift Y[0]" does not apply** — that rule
guards a step at *zero rate*; this axis is speed (non-negative, no "below X[0]" region), and the
multiplied signal `gp-0x6c2c` crosses zero continuously through a smooth gain.

## 5. PROBE — sized against THIS lane's own output (511), not a downstream gate

`gp-0x6b26`: 1 writer + shadow `gp-0x4cd0` ⇒ blast-radius-safe to read.

| rung | test | purpose | pred @×1 | pred @×3 |
|---|---|---|---|---|
| b7 | `gp-0x6b26 < 0` | identity / liveness | ~50 % | ~50 % |
| b6 | `\|gp-0x6b26\| ≥ 32` | validity | high | high |
| **b5** | **`\|gp-0x6b26\| ≥ 128`** | **DOSE-IN-FORCE** | low (73–109 straddles) | **high (220–327)** |
| **b4** | **`\|gp-0x6b26\| ≥ 448`** | **SATURATION / ABORT** | **≈0 %** | **≈0 %** |

b5's predicted duty jump is the positive control (pre-registered from the transfer function, so no
pre-dose flight is needed). **b4 > 5 % ⇒ the DF argument is void and the build should be pulled.**

## 6. Not delivered
- A saturation **duty** — needs a distribution; the probe is the instrument.
- `gp-0x6ad6 → gp-0x6b98` referral — blocked on the runtime-scheduled PID.
- **V77's on-car result** — its image carries ×1.5 + 850 but I found no `BUILD-LINEAGE` row. **Confirm
  whether V77 flew before characterising the ×1.5 history to the operator.**

---
---

# PART 4 — V90 DOSE DECISION (2026-08-10, fourth tasking)

## 0. 🛑🛑 THE REQUIREMENT AND THE MEASUREMENT ARE INCOMMENSURABLE — both struck

Part 2 §4 blocked on *"at which node is ~29 counts quoted?"*. **Answer: there is no node, because there
is no conversion.** The `ring/Q` requirement is in **column-torque counts** (`e_6-9` off `0x18F`);
`|gp-0x6b26|` is in **aggregator/motor-command counts**. Converting requires the `cmd → column` plant,
which **cannot be measured on this car** — the engaged estimator returns a **negative group delay
(−8.75 ms)**, proving feedback domination, and the fit was refused at the pre-registered coherence bar
(max γ² = 0.475).

⇒ **Part 2 §4's "implied multiplier 0.40× / 0.08×" is VOID** — it compared two unit systems. So is the
"~29 counts" target. **Both are struck as sizing inputs.**
⇒ **What survives lives entirely in one unit system**: DF, clamp margin, int16 ceiling, zero-reject — all
computed at `gp-0x6b26` in aggregator counts.
⇒ **V90 is sized to the SAFETY LIMIT, not to a computed requirement.** That is a materially weaker kind of
claim than V85's "the lever delivered 7.21×", and the pre-registration should say so.

## 1. THE HAZARD MAP — and it is not where intuition puts it

Clamp-binding column amplitude (degrees), per row × frequency, **`×1 / ×3`**:

| row | k@×1 | k@×3 | 7.79 Hz | 21.09 Hz | 28.1 Hz |
|---|---|---|---|---|---|
| **0 km/h** | 0.1600 | **0.4799** | 4.497 / **1.499** | 0.678 / **0.226** | 0.414 / **0.138** |
| 20 km/h | 0.0933 | 0.2799 | 7.709 / 2.570 | 1.162 / 0.387 | 0.710 / 0.237 |
| 90 km/h | 0.0320 | 0.0960 | 22.48 / 7.494 | 3.390 / 1.130 | 2.072 / 0.691 |

🛑 **The 20 and 90 km/h rows are the SAFEST rows under uniform scaling** — they carry the lowest `k`, so
uniform ×3 spends the least headroom exactly where the concern was. The intuition is backwards.

🛑 **The real exposure uniform ×3 creates is `creep × 28 Hz`**: binding falls **0.414° → 0.138°**
amplitude. Grind #2 is recorded as *"creep cornering"*, so the combination is live. At 7.79 Hz — the band
that actually matters for the remaining symptom — the margin is sound: **1.499° vs 0.96° measured = 1.56×**.

## 2. UNIFORM ×3, over flatten and over a hybrid

Part 1 §6 / Part 3 §4 argued **flatten**. **Withdrawn** — that argument aimed at the highway grind, and
the grind is fixed. The remaining symptoms (micro-ratcheting, ratcheting) are 6–9 Hz and largest at creep,
and flatten leaves the creep row at ×1.0, i.e. it does nothing for them. **The target moved; the shape
recommendation follows it.**

Hybrid checked and rejected — all rows lifted to the creep-×3 value 29490 (= ×3 / ×5.14 / ×15.0) is
**arithmetically free**, every row inside int16, highway margin 1.69×. Rejected for three reasons:
1. **No target.** Grinding is fixed ⇒ ×5–15 on the upper rows is pure added saturation exposure for zero
   expected benefit.
2. **Two-variable experiment** — a creep dose *and* a highway dose, when the remaining symptom is
   creep-only.
3. **★ Uniform scaling preserves Honda's schedule SHAPE exactly.** Every row scales by the same factor, so
   the *speed-gradient* of wheel feel is unchanged — more damping everywhere, not a new speed-dependence.
   Flatten and hybrid both change the shape, which is a feel change the operator would have to disentangle
   from the dose. **This reason is independent of the other two and is the strongest.**

```
0xD6A64 (mode 24) and 0xD7A54 (mode 26), Y row at record base + 8
  {-9830, -5734, -1966}  ->  {-29490, -17202, -5898}
  bytes  9ad9 9ae9 52f8  ->  2e8c 4ebd 06e9        (LE int16)
0xC407E stays 511 — two independent reasons (V74/V75 faults; and >1024 would GIVE the lane a dropout)
```
×3 is the ceiling from **two independent limits that coincide**: clamp margin 1.56× at 7.79 Hz, and
`|Y|×4 = 39320` **overflows int16**.

## 3. PROBE — final rung table

| bit | test | purpose | pred @×1 | pred @×3 |
|---|---|---|---|---|
| b7 | `gp-0x6b26 < 0` | identity / liveness | ~50 % | ~50 % |
| b6 | `\|gp-0x6b26\| ≥ 32` (`sar 5`) | validity | high | high |
| **b5** | **`\|gp-0x6b26\| ≥ 128`** (`sar 7`) | **DOSE-IN-FORCE** | low (73–109 straddles from below) | high (220–327) |
| **b4** | **`\|gp-0x6b26\| ≥ 511`** | **SATURATION / ABORT** | ≈0 % | ≈0 % predicted |
| b3 | fingerprint | build identity | — | — |

**b4 changed from `≥448` to `≥511`** — the lane is hard-clamped at exactly ±511, so this is an *exact*
saturation test costing one `cmp` (and 448 is not a power of two). **Abort: b4 > 5 % of engaged frames ⇒
the term has become a relay on `sign(motor acceleration)`, the DF argument is void, pull the build.**
b4 is the instrument for the creep×28 Hz exposure in §1 — which is why the rung is mandatory.

## 4. GATE 2 RESIDUAL, restated for the pre-registration
Sign is **closed and total** — `−gp-0x6c2c` never reaches −90° vs rate at any frequency up to Nyquist.
Magnitude is **not statically closable** — the PID gain is runtime-scheduled. State both.

## 5. Open
**Did V77 fly?** Its image carries ×1.5 + clamp 850 and no `BUILD-LINEAGE` row was found. If it flew it is
a fourth data point on the ×1.5 dose and bears directly on the "×1.5 is a known-null rung" claim.

---
---

# PART 5 — TWO CORRECTIONS AND THE 14-SITE ANSWER (2026-08-10, fifth tasking)

## 🛑 0. RETRACTION — Part 3 §0's "×1.5 is a known-null rung" is WRONG. It flew THREE times, not four.

**There are TWO V76 artifacts and they differ on this exact cell:**

```
image                                    m24      m26      0xC407E
stock                                    stock    stock       511
_v73_plain_image                         stock    stock       850
_v74_engagedcols_x0_12_addonly           stock    x1.5        850
_v75_CY0.566_magprobe                    stock    x1.5        850
_v76_gate_fb_arm5244_gateprobe           stock    x1.5        850
_v76_v38base_relu_damper                 stock    STOCK       511   <== the one that FLEW
_v77_C63A0.1024_v74base                  stock    x1.5        850   (never flew)
_v78 / _v79 / _v80 / _v81 .. _v89        stock    stock       511
```

`BUILD-LINEAGE`'s V76 row is `| V76 | V38 | … | FLEW route 65, clean |` — base **V38**, matching
`_v76_v38base_relu_damper`, which is **stock friction + 511 clamp**. That row's own note explains it:
*"the V38 rebase silently reverted **seven** things, not three."* **The ×1.5 row and the 850 clamp were
two of the seven.** The lineage **forked**: V76-v38base → V78 → V79 → V80 all stock; V77 and V81 came off
the V74/V75 branch.

| build | ×1.5? | on-car |
|---|---|---|
| **V73** | yes (+850) | **FLEW CLEAN**, n=1 |
| **V74** | yes (+850) | **HARD-FAULTED** |
| **V75** | yes (+850) | **HARD-FAULTED** |
| V76 (flown) | **no** | flew route 65 clean |
| V77 | yes | **never flew** |

⇒ **ONE clean route of ×1.5 evidence, plus two hard faults — not an era.** A faulting build yields almost
no driving data. **"×1.5 is a known-null rung" does not survive; ×1.5 is close to untested as a dose.**
⇒ **×2 is a legitimate option** (clamp margin 2.25° = 2.3× on measured amplitude; creep×28 Hz binding
0.207° vs ×3's 0.138°). **×3 remains the lean under the FIV threshold argument — but it is now a
judgement call on an untested lever, not a conclusion licensed by a prior null.** State which.

## 1. THE 14-SITE QUESTION — two records is CORRECT and SUFFICIENT

Dereferenced `0xCBE74 + m*4` for all 34 modes and diffed every Y row against the V74 image:

| dosed by V74 | modes |
|---|---|
| ✅ | m2, m3, m5, m11, m14, m15, m17, m23, **m26**, **m27**, m29, m32, m33 — **the 13 ENGAGED modes** |
| ✅ | **m10** — DISENGAGED, V73's stray (`build_v74_tva.py` names it) |
| ❌ | **m24** (`0xD6A6C`), **m25** (`0xD7A4C`) |

All 14 addresses are reachable from a mode index; 34 distinct Y rows exist. **14 = 13 engaged rows +
V73's m10.** V74's design was *"dose the ENGAGED column of every row, leave manual byte-stock"* —
robustness against the row inference, which was uncertain in August.

⇒ **Writing only m24 `0xD6A64` + m26 `0xD7A54` is correct.** Those are this car's two MEASURED live
columns (V73's probe: 104,061 frames, 18 transitions on engagement edges, 99.09 % lag-matched, manual=24
/ engaged=26, forced by the manual arm — raw 8 appears in no row ⇒ 24; only row 11 `TVCA4` contains 24).

🛑 **This is NOT the V69 failure — it is the opposite error class.** V69 wrote modes **10/11**, which
belong to rows 2/3/6/7 (`TVAA1`/`TVAC1`/`TVAA6`/`TVAC4`) — *another variant's* rows, hence byte-stock
behaviour. Writing 24/26 hits the live columns exactly.

🛑 **But writing BOTH makes V90 SYMMETRIC where V74's was ENGAGED-ONLY** — m24 was never touched on any
build, so **V90 will change MANUAL steering feel, which V74/V75 never did.** Recommended anyway:
1. Honda ships **m24 ≡ m26 byte-identical**; every asymmetry on this car is *ours*, and removing one
   (V81) was noted as *"removes drag the operator is used to."* Symmetry is the conservative choice, and
   it is the same "preserve Honda's shape" logic as uniform-over-flatten.
2. The remaining symptoms are felt while driving generally, not only while engaged.
3. The counter-argument — engaged-only buys a free within-drive manual control — is **already known
   underpowered**: Lever-B × rate contrast **−0.101 [−0.381, +0.298]**, CI half-width **2.4× the effect**;
   closing it needs ~4× the episode blocks at matched engaged/manual exposure and matched wheel rate.
   **Exposure, not analysis, is the binding constraint.**

🛑 **ASSERT m25 (`0xD7A44`) and m27 (`0xD7A64`) byte-stock — do not dose them.** They are row 11's
B-branch, selected by `gp-0x67e2`, which stayed at 1 for the whole measured drive and never selected
them. **V83a's recorded defect was exactly leaving m27 carrying a package unintentionally**, and a stock
m25/m27 means a `gp-0x67e2` flip falls back to Honda's value rather than an unintended dose. Note V74
*did* dose m27, so this is a deliberate departure worth a line in the build rationale.

## 2. Method note — both of today's lineage errors have ONE root cause
A `grep` that returned seven build scripts I did not open, then a `glob` that silently picked one of two
V76 artifacts. **Matching is not reading.** When two images share a build number, the `BUILD-LINEAGE`
row's **BASE column** is the discriminator — never the filename prefix, and never a glob that hides the
second match.

---
---

# PART 6 — SECOND RETRACTION: ZERO CLEAN FLIGHTS, AND THE ADDRESSES

## 0. Part 5's V73 row is WRONG. There has never been a clean flight of this lever.

34-mode dereference of `0xCBE74` across stock / V73 / V74:

```
V73 dosed exactly ONE friction Y row:  m10 @0xD2A4C  (DISENGAGED, rows 2/3/6/7 = another variant)
V74 dosed 14: the 13 ENGAGED modes + V73's inherited m10
m24 @0xD6A6C   stock on V73, stock on V74   <== never touched on any build
m26 @0xD7A5C   stock on V73, x1.5 on V74
```

Part 5 said "V73 | yes | FLEW CLEAN, n=1" while its own byte table read `_v73_plain_image stock stock`.
A self-contradiction inside one document. **V73's x1.5 landed on mode 10 only — inert on this car.**

| build | x1.5 on a LIVE column | on-car |
|---|---|---|
| V73 | **NO** (m10 only, inert) | clean - says nothing about this lever |
| **V74** | **YES** | **HARD FAULT, latched** |
| **V75** | **YES** | **HARD FAULT, latched** |
| V76 (flown) | no - V38 rebase reverted it | clean |
| V77 / V77B | yes | never flew |

⇒ **x1.5 on a live column flew exactly TWICE and BOTH hard-faulted. ZERO clean flights.**
⇒ **The x2 option reopened in Part 5 is WITHDRAWN** - it rested on doubling a clean data point that does
not exist. The prior is **untested, with a 2-for-2 fault association.**

## 1. THE FAULT ATTRIBUTION INVERTS

| build | clamp | friction on a live column | on-car |
|---|---|---|---|
| V73 | **850** | no | **CLEAN** |
| V74 | 850 | **yes** | **HARD FAULT** |
| V75 | 850 | **yes** | **HARD FAULT** |

The record blames `0xC407E`=850. **V73 flew clean with the same 850.** Cannot be pinned - V73 to V74 is
64 differing runs, not single-variable - but **the control meant to exonerate the friction row is what
implicates it**, and V90 proposes **x3, double the dose carrying that association.**

⇒ **PROBE-ONLY endorsed; the dose recommendation is WITHDRAWN.** The safety envelope computed in Parts
2-4 (DF 1.000 through x4, clamp margin, int16, zero-reject unreachable, dissipative sign closed to
Nyquist) was computed against **saturation and dropout**. It says nothing about a **latched-fault**
mechanism, which is what actually happened twice and which has no model.

## 2. THE ADDRESSES - an ADDRESS IS NOT A MODE

```
m24 (manual) : base 0xD6A64 . X 0xD6A66 [0,1280,5760] . ** Y ARRAY 0xD6A6C **
m26 (engaged): base 0xD7A54 . X 0xD7A56 [0,1280,5760] . ** Y ARRAY 0xD7A5C **
0xD6A5C -> mode 23  (NOT 24)      0xD7A6C -> mode 27
```
Two near-misses in one session: Parts 3-4 named **record bases** where Y arrays were meant; and the
V74-dosed site list (`0xD6A5C`/`0xD7A5C`/`0xD7A6C`) is **not** the set V90 should write - it contains
mode 23 and omits mode 24, because **V74 never touched m24**.

**Writing Y values at `base+2` fails SILENTLY, not loudly**: `X` becomes `[-29490,...]`, read as
**u16 36046** by the LERP's unsigned compare, so every speed falls below `X[0]` and the table returns a
flat `Y[0]` = -9830 at all speeds - an accidental **5x at highway**, the exact shape Part 4 argued
against. Plausible output, wrong experiment. **Assert the X arrays unchanged.**

## 3. Standing build assertions, if a dose is ever cut
`0xC407E` = 511 KEEP . X arrays unchanged . m25 (`0xD7A44`) and m27 (`0xD7A64`) asserted byte-stock .
Y arrays written at `0xD6A6C` and `0xD7A5C` only.
