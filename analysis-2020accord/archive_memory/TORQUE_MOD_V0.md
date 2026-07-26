# Accord TVA EPS — Torque-Mod Attempt **V0** (instructions / build plan)

**Vehicle / target:** 2020 Honda Accord Touring, EPS `39990-TVA-A160` (V850E2, LE, 1 MB).
**Goal:** when the comma (LKAS, CAN `0xE4` STEER_TORQUE) commands full scale (±4096), deliver **more EPS assist torque than stock**, using the *minimal* static value/operand edits.
**Status:** PLANNING ONLY. Nothing built, nothing flashed. Per kit safety rules, no `.rwd` is produced and no flash happens until the operator explicitly names the file and bus. This doc is the recipe + the must-resolve list.

> **✅✅✅ RESOLVED 2026-05-26 — V14 FLASHED + ROAD-TESTED: IT WORKS.** Operator confirmed V14 delivers ~2× LKAS torque at the wheel. The three cal halfword edits (gain `0xC646C` 891→1782; clamps `0xC61B2`/`0xC61B4` 512→1024) were the real binder. The LKAS path is REQUEST-LIMITED (stock arb out ≈418, V14 ≈835) far below the 4762 governor, so the doubling reaches the motor uncut — **the governor never bound; V15/`0xC6202` edit is NOT needed for 2×.** Everything below (the descending-clamp-staircase / ±0x3FFF-ceiling / shaper-dual-check analysis) describes the *merged-signal* waterfall that sits ABOVE the governor and was NEVER the LKAS binder — preserved for the record, not the path to the win. Authoritative: `memory/reference_accord_lkas_delivery_and_governor.md` + `memory/project_accord_torque_mod_v0.md`.
>
> **⚠⚠⚠ CORRECTION 2026-05-26 (late) — supersedes the V11/V12/V13 framing AND the 2026-05-25 block below.** Authoritative record: `memory/reference_accord_lkas_delivery_and_governor.md` + `memory/project_accord_torque_mod_v0.md`. The current build is **V14** (`build_v14_tva.py`, 49/49 CRC, UNFLASHED): three flashable cal edits — gain `tp+0x746c`(`0xC646C`) 891→1782, clamps `tp+0x71b2`/`tp+0x71b4`(`0xC61B2`/`0xC61B4`) 512→1024 (`tp`=0xBF000). Verified this session: (1) the LKAS arb torque DOES reach the motor (arb→limit_and_pack→distribute_clamp src idx 1→`gp-0x6b4c`→`gp-0x6b94`→`gp-0x6ace`→`gp-0x6acc`→shaper→`gp-0x6b98`→FOC), so V14 is on a LIVE path. (2) The delivered high-end binder is the runtime governor `gp-0x4f64` = cal `0xC6202` = **4762**, NOT the ±0x2000 static and NOT the gate/shaper windows this doc fixates on. (3) The window/clamp analysis below (V11–V13) targeted levers that are NEITHER the arb-source NOR the governor — which is why those builds showed no high-end change. Two real levers: V14 arb-source scaling (LKAS share) + governor `0xC6202` (combined ceiling). Open magnitude question (LKAS share vs governor) → road test.
>
> **⚠ CORRECTION 2026-05-25 (Ghidra-verified, code.bin port 8193) — supersedes §0, §3a-iii, §4. Build result is `build_v11_tva.py` / V11A.** Verifying this plan in the disassembly overturned two load-bearing assumptions:
> 1. **Hard static-edit ceiling is ~2.0× (16383 / `0x3FFF`), NOT ~3.99×.** §0 considered only the int16 *storage* limit (`0x7FFF`). But the gate `FUN_00042ac6` (`0x42ac6/aca`) **and** the shaper input-check (`0x43ae8/aec`) both use the `+0x2800 / -0x5001` plausibility idiom; widening the window to ±W needs 2nd immediate `-(2W+1)`, and `W=0x4000` overflows imm16 → `±0x3FFF` is the max. **2.5× (`0x5000`) and 3× (`0x6000`) are NOT value edits** — they require restructuring both comparison sequences (a code rewrite).
> 2. **The shaper `FUN_00042af8` is a DUAL range-check, not a plain `±0x2000` clamp.** Before the final clamp, `0x43ae8` re-runs the gate's `±0x2800` check on `0xFEDF1502` and `cmovc 0x0,r13,r12` **ZEROES** anything outside ±0x2800 — including the gate's `0x7FFF` sentinel. **This doc's §2/§3 missed `0x43ae8/0x43aec`.** Overshooting the gate window does not add torque; it zeroes LKAS (the Civic V10A failure mode).
> 3. **Mixer LKAS lane pinned = the `0x27442` block** (`gp-0x3d8c` accumulator → `r26` → `jarl 0x42ac6` @ `0x277f6`); the other three ±0x2800 mixer blocks (§3a-iii) are NOT the LKAS lane.
> 4. **Residual runtime limiter [OPEN]:** the shaper also clamps by `*(gp-0x4f64) = 0xFEDF309C` (itself zeroed if >`0x2800`); if it sits below target at the operating point it binds first and delivered torque is < 2× regardless of these edits. Bench RAM probe only.
>
> **V11A (`build_v11_tva.py`, 2026-05-25):** the achievable ~2× ceiling-raise — widens distributor +4, mixer `0x27442` lane, gate, **shaper input-check**, shaper final clamp (to ±0x3FFF window / ±0x4000 clamp) + arb table `0xE4180`+mirror `0xE5180` (12 slots × 9: 15360→16384). 3 CRC blocks recomputed (`0xC4FFC`/`0xE4FFC`/`0xE5FFC`); **49/49 walk PASS, full byte-diff = only intended sites.** Study artifact, unflashed. Details: `memory/reference_accord_lkas_window_ceiling.md`.

All addresses/bytes below were read from the live `code.bin` (Ghidra, port 8193) on 2026-05-25 and are byte-verified unless marked otherwise. Companion analysis: `TORQUE_PATH_AND_TABLE.md` §0.6, `memory/reference_accord_arbitration_limit_family.md`, figs `accord_bottleneck_and_limit_family.png` / `accord_plotC_by_mode.png`.

---

## 0. The multiplier baseline (read first)

The LKAS torque command runs a **descending clamp staircase**. At full-scale input (4096):

| stage | fn @ addr | limit | value |
|---|---|---|---|
| scale `x·−4` + clamp ±0x4000 | `s_lkas_process_steer_cmd` 0x526d2 / 0x526ce-d6 | ±0x4000 | **16384** (full input lands exactly on rail) |
| arbitration limit (`cb844` const) | `m_steer_torque_arbitration` 0x28ea6 | ±15360 | 15360 |
| distributor lane +4 | `m_motor_cmd_distribute_clamp` 0x25c9c | ±0x2800 | 10240 |
| mixer torque clamp | `m_motor_cmd_mixer` 0x26ea0… | ±0x2800 | 10240 |
| mixed-cmd **gate** (sentinel, not clamp!) | `FUN_00042ac6` 0x42ac6 | \|v\|≤0x2800 else 0x7fff | ≤10240 → `0xFEDF1502` |
| **shaper output (binding)** | `FUN_00042af8` 0x43b0e… | ±0x2000 | **8192** |

So **stock full-scale delivered ≈ 8192 (0x2000)** — the shaper is the binding wall, and the firmware already throttles the 16384 setpoint 2:1 before output. Define the multiplier **M relative to 8192**: 2×=16384, 3×=24576, etc.

**Hard architectural ceiling:** ~~every stage stores the command as **signed 16-bit** (`st.h`/`ld.h`), so nothing past **±32767 (0x7FFF) ≈ 3.99×** is reachable by editing values/operands.~~ **⚠ WRONG — see correction box at top.** The real value-edit ceiling is **±0x3FFF ≈ 2.0×**, set by the imm16 limit of the gate/shaper `+0x2800/-0x5001` plausibility idiom (not the int16 storage limit). So **anything above ~2× (incl. 2.5× and 3×) is NOT a static-value mod** — it requires restructuring those comparison sequences (a code rewrite). V0 targets **≤2×**, which is now known to be the entire feasible value-edit band, not its "low end."

---

## 1. MUST-RESOLVE before V0 is meaningful (pre-flight)

These gate whether *any* clamp edit reaches the motor. Do not skip.

1. **GAP 2 — command→motor handoff unproven.** The shaper output routes into a **CSIG0 serial frame**; the on-chip FOC→TSG20 drive is verified but the link between them is not. If the motor is driven by an unlocated q-current reference, raising these clamps may change nothing. **Bench probe:** log `0xFEDF1502` (mixed cmd), `0xFEDF14C4` (arb out), `0xFEDF1652` (setpoint), and the CSIG0 TX frame while LKAS actuates; confirm a clamp change moves delivered motor torque.
2. **Inter-stage units unknown.** The clean 2:1 (`0x4000`→`0x2000`) may be a Q-format change, not attenuation. If so, raising the shaper number won't raise *physical* torque. No counts→Nm/amps map exists yet.
3. **FOC current loop + thermal motor-output limit ("Hard Ceiling").** Those params live in `0xFD8C8`/`0xFE000` — **absent from our dump** (the `0xF8000+` partition). They can silently cap delivered torque. Need that partition or a stock `.rwd` covering it.
4. **comma side.** A ≥2× plant-gain change without an openpilot PID retune is a known oscillation setup. Confirm openpilot actually commands up to 4096.

**Recommendation:** run probe #1 (and #2) BEFORE Stage 2. Stage 1 below is itself a cheap, low-risk version of that probe.

---

## 2. V0.1 — the minimal probe (shaper only, ≈1.25×)

Raise ONLY the final shaper clamp from ±0x2000 to ±0x2800. `0xFEDF1502` already carries valid values up to ±0x2800 (the `FUN_00042ac6` gate passes that range), so **no other site changes** — this is the single cleanest lever on the final steering torque, with the smallest blast radius. Delivered 8192 → **10240 (1.25×)**. Doubles as the GAP-2/units probe.

| addr | instr (current) | imm | new imm | byte change (LE imm16 = bytes [+2,+3]) |
|---|---|---|---|---|
| 0x43b0e | `addi -0x2000,r14,r0` | 0xE000 | -0x2800=0xD800 | `0e 06 00 e0` → `0e 06 00 d8` |
| 0x43b12 | `movea 0x2000,r0,r21` | 0x2000 | 0x2800 | `20 ae 00 20` → `20 ae 00 28` |
| 0x43b18 | `addi 0x2000,r14,r0` | 0x2000 | 0x2800 | `0e 06 00 20` → `0e 06 00 28` |
| 0x43b1c | `movea -0x2000,r0,r6` | 0xE000 | -0x2800=0xD800 | `20 36 00 e0` → `20 36 00 d8` |

> Do NOT touch `0x431d0 addi 0x2000,r9,r6` — that is a +0x2000 bias, not the clamp.

If V0.1 produces a noticeable, stable torque increase → the clamp stack does gate motor torque, proceed to V0.2. If nothing changes → GAP 2 is real; stop and resolve the handoff before any further clamp work.

---

## 3. V0.2 — toward 2× (raise the staircase)

To exceed 10240 you must raise the gate, the per-stage clamps, and (for the last 6%) the arbitration table. Two tiers:

### 3a. ≈1.875× (code-only, no data-table edit) — delivered capped by arb 15360
Raise the code clamps to ±0x4000; leave the `cb844` arb table at 15360 → it becomes the binding cap = **15360 (1.875×)**. All edits in code blocks.

**(i) Mixed-cmd gate `FUN_00042ac6`** — extend the valid window. Note `addi -0x8001` overflows imm16, so use **±0x3FFF (16383)**, not 0x4000:

| addr | instr | new | bytes |
|---|---|---|---|
| 0x42ac6 | `addi 0x2800,r6,r13` | `addi 0x3fff,r6,r13` | `06 6e 00 28` → `06 6e ff 3f` |
| 0x42aca | `addi -0x5001,r13,r0` | `addi -0x7fff,r13,r0` | `0d 06 ff af` → `0d 06 01 80` |

**(ii) Distributor lane +4** (±0x2800→±0x4000):

| addr | instr | bytes |
|---|---|---|
| 0x25c9c | `addi -0x2800,r11,r0` | `0b 06 00 d8` → `0b 06 00 c0` |
| 0x25ca2 | `movea 0x2800,r0,r14` | `20 76 00 28` → `20 76 00 40` |
| 0x25ca8 | `addi 0x2800,r11,r0` | `0b 06 00 28` → `0b 06 00 40` |
| 0x25cac | `movea -0x2800,r0,r14` | `20 76 00 d8` → `20 76 00 c0` |

**(iii) Mixer torque clamp** (±0x2800→±0x4000). ⚠ **CONFIRM LANE FIRST.** The mixer has **four** ±0x2800 clamp blocks; only the one in the SUM/MAX path feeding `0xFEDF1502` (via `FUN_00042ac6`) is the LKAS torque lane. Raising the wrong block scales *other* demand slots. Blocks (each: `addi -0x2800 / movea 0x2800 / addi 0x2800 / movea -0x2800`, change high byte `28↔40`, `d8↔c0`):
  - 0x26ea0–0x26eb2  · 0x26ec4–0x26ed6  · 0x27442–0x27450  · 0x276de–0x27704

Investigate (disassemble the mixer's reduction + the `mov r26,r6; jarl FUN_00042ac6` feeder) to pick the correct block(s) before editing.

### 3b. Full 2× (16384) — add the arbitration table
Raise the `cb844` setpoint-limit value row 15360→16384. It is **mode/gear-invariant** (all 12 slots identical) so raise every slot + the `0x1000` mirror to be safe:
  - value row at `0xE4180 + 0x14` (9× `00 3c` = 0x3c00) → `00 40` (0x4000); repeat at `0xE4180 + n·0x28` for n=0..5 and the mirror `0xE5180 + n·0x28` for n=0..5.

---

## 4. If you want a true GAIN multiplier (slope), or >2×

Sections 2–3 are a **ceiling raise** (more torque only near full command). For a uniform **2× gain at every command level**, also change the input scale:
  - 0x526d2 `shl 0x2,r6` → `shl 0x3,r6` : single byte `c2 32` → `c3 32` (×4→×8 slope). The setpoint then saturates at the ±setpoint-clamp earlier (≈half input).

~~For **>2× up to ~3.99×**: keep `shl 0x3`, and raise the **setpoint clamp** + every downstream clamp toward 0x7FFF:~~ **⚠ WRONG — see correction box at top.** `>2×` (incl. 2.5× and 3×) is **NOT reachable by value edits.** The gate `FUN_00042ac6` **and** the shaper input-check (`0x43ae8/aec`, which this doc originally missed) both cap their plausibility window at **±0x3FFF**; a value above it is mapped to the `0x7FFF` sentinel and then **zeroed** by the shaper (`cmovc 0x0`), killing LKAS rather than adding torque. Reaching `>2×` requires restructuring both `+0x2800/-0x5001` comparison sequences (a code rewrite), and is further gated by the runtime limiter `*(gp-0x4f64)=0xFEDF309C`. For reference, the original (now-disproven) recipe was: keep `shl 0x3`, raise setpoint clamp `0x526ce`/`0x526d6` + every downstream clamp toward `0x7FFF`.
  - setpoint clamp bounds (still valid sites if a restructure is attempted): 0x526ce `movea -0x4000,r0,r7` (`20 3e 00 c0`) and 0x526d6 `movea 0x4000,r0,r8` (`20 46 00 40`).
**Real ceiling: ±0x3FFF ≈ 2.0× by value edit** (gate/shaper window, not the int16 datatype). 2.5×/3×/4×+ all need the comparison-sequence restructure.

---

## 5. Build / flash mechanics (when authorized)

1. Apply the byte edits above to the **decrypted** `code.bin` image (via the canonical builder; see `HOW_TO_BUILD_ACCORD_TVA_RWD.md`). Confirm the cipher = `((c^0xBF)^0x10)-0x9E` (proven by V9b).
2. **Recompute CRC trailers** for *every touched block* — the 49-block CRC-32 linked-list walk (`verify_bootloader_crc.py`). Sites span multiple blocks: shaper `0x43xxx`, gate `0x42xxx`, distributor/mixer `0x25–0x27xxx`, arb table `0xE4xxx`. A miss → ECU rejects with NRC 0x72.
3. Full byte-diff vs stock (per `feedback_rigorous_validation`): confirm ONLY the intended bytes differ.
4. Round-trip encrypt→decrypt must be identical.
5. Flash only with openpilot/pandad killed; operator names file + bus; repeat name back before proceeding.

## 6. Validation & rollback
- Bench (preferred): RAM/CAN capture confirming `0xFEDF1502`/serial-frame torque scales as intended (closes GAP 2).
- Road: start at V0.1 (1.25×), short low-speed test; watch for EPS noise, oscillation, fault/override drop (the Civic V10A failure mode — a big command can trip plausibility and *zero* LKAS).
- Rollback: keep the current stock/working `.rwd`; reflash it if any fault or undesired behavior.

## 7. Open questions to close (carry-forward)
- GAP 2 handoff + counts→Nm units (§1.1/1.2) — **gating.**
- Which mixer ±0x2800 block is the LKAS torque lane (§3a-iii).
- Does the arbitration shaping (`c9a88`, gear-dependent) or speed/override gating reduce the command below the clamps at the operating points we care about?
- Rate limits (`tp+0x71b2`, `DAT_000072e4`) vs the larger magnitude.
- FOC/thermal ceiling in the absent `0xF8000+` partition.
