# 2020 Accord TVA EPS — Torque Code Path (Ghidra Reference)

**Vehicle / ECU:** 2020 Honda Accord Touring, `39990-TVA-A160`, V850E2, little-endian, 1 MB  
**For build/flash mechanics:** see `HOW_TO_BUILD_ACCORD_TVA_RWD.md` (not duplicated here)

Confidence markers used throughout:
- **[V]** — verified by Ghidra decompile or byte-level disasm of `code.bin`
- **[LIKELY]** — structurally strong inference, not instruction-pinned
- **[OPEN]** — not established from the binaries in hand

---

## Before You Start: Two Pointer Bases to Know

Before navigating this path in Ghidra, resolve these two register-relative bases. Every `gp-0xNNNN` and `tp+0xNNNN` address in this guide depends on them.

### `gp` = `0xFEDF8000` (RAM global pointer) **[V, cross-checked ×2]**
Ghidra renders small-data RAM accesses as `unaff_gp - offset`. Convert to absolute:
```
absolute_RAM = 0xFEDF8000 - gp_offset
```
Example: `gp-0x69ae` → `0xFEDF8000 - 0x69AE` = `0xFEDF1652`.

Proven by: (a) `FUN_0001ce68` staging CAN bytes to `gp-0x1734` = `0xFEDF68CC` (the known STEER_TORQUE slot), and (b) `DAT_fedf55d8` = `gp-0x2A28`.

**Caveat:** gp-relative accesses are NOT cross-referenceable in Ghidra — the decompiler leaves them register-relative. Only absolute-mode accesses of the same RAM variable show up in `xrefs_list`. Use data-flow tracing, not xrefs, to follow these variables.

### `tp` = `0xBF000` (calibration base, stored in r5) **[V]**
Built in three instructions at `0x140d6`: `movhi 0xb` + `movea 0x7000` + `add r1=0x8000` (the third instruction was missing from earlier analysis, causing all slew/deadband address errors). Convert:
```
absolute_flash = 0xBF000 + tp_offset
```
Example: `tp+0x746c` → `0xC646C`.

---

## Part 1: LKAS Torque Path (CAN → Motor)

This is the path taken by a torque command sent by comma/openpilot (CAN `0xE4`, `STEER_TORQUE`). Each hop is a function you can open in Ghidra.

---

### Hop 1 — CAN Reception **[V]**

**Function:** `FUN_0001ce68` (`s_can_rx_stage_to_scratch`) (generic RX extractor)  
**What it does:** Copies all 8 bytes of any received CAN frame into a shared scratch buffer.

| Variable | Address | Role |
|---|---|---|
| Shared RX scratch | `0xFEDF68CC` (`gp-0x1734`) | Pre-route staging — overwritten every frame, not the LKAS buffer |

**Note:** This scratch buffer is a dead end for LKAS tracing. Nothing in the driver-assist chain reads `0xFEDF68CC` directly. The real LKAS data lives one hop later.

---

### Hop 2 — Frame Routing / Dispatch **[V]**

**Function:** `FUN_0001ddd0` (`s_can_rx_dispatch`)  
**What it does:** Routes each received frame to a per-message destination buffer using a slot-indexed route table. For CAN `0xE4`, this is the LKAS-specific buffer.

The route table is at **absolute flash `0xB739C`** — it is fully present in `code.bin`, not runtime-resident. Look up the chain:

| Table | Flash addr | Indexed by | What it holds |
|---|---|---|---|
| Mailbox → CAN-ID | `0xB733C` | `mailbox − 0x20` (u32) | `stdID = high16 >> 2` |
| Mailbox → slot | `0xB70F4` | `mailbox − 0x20` (u16) | Logical slot index |
| Slot → dest buffer | `0xB739C` | Slot (u32) | RAM destination pointer |

Resolving for `0xE4`: mailbox `0x36` → slot `17` → dest `0xFEDF6BD8`.

| Variable | Address | Role |
|---|---|---|
| **LKAS routed buffer** | `0xFEDF6BD8` | `STEER_TORQUE` int16 BE at bytes `+0/+1`; request flags at `+2` and `+4` |

**History:** Earlier analysis traced `0xFEDF68CC` (the scratch) and concluded the LKAS consumer was data-blocked in absent memory. That was wrong — the route table is at absolute flash `0xB739C`, which is present. GAP 1 is closed.

---

### Hop 3 — LKAS Processing (Setpoint Calculation) **[V, instruction-verified]**

**Functions:**
- `FUN_00021724` (`s_get_lkas_steer_torque_be`) — reads `0xFEDF6BD8/9` in an IRQ-critical section, returns the BE int16
- `FUN_00052676` (`s_lkas_process_steer_cmd`) — applies scale and clamp

**What it does:**
```
setpoint = clamp(STEER_TORQUE × −4, ±0x4000)
```
Instruction sequence: `sxh` (sign-extend) → `shl 2` (×4) → `subr r0` (negate → ×−4) → clamp to `±0x4000`.

Fault/inhibit paths write sentinel `0x7FFF` instead. There is a 500-tick validity timeout on the input.

| Variable | Address | Role |
|---|---|---|
| LKAS setpoint | `0xFEDF1652` (`gp-0x69ae`) | Output of this hop; ±4096 input → ±0x4000 (16384) at full scale |

---

### Hop 4 — Arbitration **[V disasm]**

**Function:** `FUN_00028ea6` (`m_steer_torque_arbitration`)  
**What it does:** Table-driven speed/mode-dependent **limit** on the LKAS setpoint, then adds the driver-torque assist contribution. This is NOT a passthrough.

The limit comes from a family of 8 LERP-curve pointer arrays, indexed by a mode/gear byte at `gp-0x674e`:

| Pointer array | Role |
|---|---|
| `0xCB844` (`g_pArbSetpointLimitCurves`) | Hard setpoint magnitude limit — **mode/gear-INVARIANT**, all 12 slots identical: constant **15360**, breakpoints `[3200..8320]`. Limit tables live at `0xE4180+mode×0x28`. |
| `0xC9A88` (`g_pArbCurve_c9a88`) | Torque shaping curve — **VARIES by gear**. Axis `[0,12,20..240]`; gear0/1/2 have different value rows. Tables live at `0xE4000+`. |
| `0xCBA74`, `0xCB924`, `0xCB7D4`, `0xCBB54`, `0xCBC34`, `0xCBAE4` | Additional interp pointer arrays; role not fully traced. |

**Earlier error (corrected):** `0xC6518/0xC6534` (a speed-indexed float curve in the cal block) was thought to be the live LKAS setpoint limit. Disasm of this function shows the limit actually comes from the `0xE4xxx` LERP family. `0xC6518/0xC6534` has no confirmed runtime read on the LKAS path.

At full input (x=4096): setpoint enters this function as `−0x4000` → exits **capped at ~15360** by the invariant table.

| Variable | Address | Role |
|---|---|---|
| Arbitration final gated cmd | `0xFEDF14C4` (`gp-0x6b3c`) | Output of arbitration + assist sum |

---

### Hop 5 — Rate-Limit and Pack **[V]**

**Function:** `FUN_0002b422` (`m_steer_torque_limit_and_pack`)  
**What it does:** Applies rate limits and packs the command into a struct: `{flag, state, torque, blends, 0x400}`.

The `0x400` blend gain = unity in Q10. Rate-limit calibration values are in the cal band (see Part 3).

---

### Hop 6 — Distributor / Per-Channel Clamp **[V instr]**

**Function:** `FUN_00025c32` (`m_motor_cmd_distribute_clamp`)  
**What it does:** Per-channel state machine (6-state, jump table at `0x25d18`) that assigns source signals to lanes and applies per-lane clamp limits.

Lane clamps (code literals at `0x25c80/9c/b8/d4`):

| Lane | Clamp | Note |
|---|---|---|
| +4 | **±0x2800 (10240)** | **LKAS rides this lane** [V] |
| +2 | ±0x4000 | |
| +6 | ±0x384 | |
| +8 | ±0x4e20 | |

Blend gains (at `r6+a/+c/+e`) are clamped ≤0x400 (unity, Q10).

| Variable | Address | Role |
|---|---|---|
| Per-channel motor cmd buffer | `0xFEDF1D20` (`gp-0x62e0`) | Output of distributor |

**V18 calibration values on this hop:** `0xC61B2` / `0xC61B4` (`tp+0x71b2`/`tp+0x71b4`) — see Part 3.

---

### Hop 7 — Mixer **[V disasm]**

**Function:** `FUN_00026c80` (`m_motor_cmd_mixer`)  
**What it does:** Reads all per-channel command buffers. Applies a cross-slot running MAX on some lanes and SUM on others into accumulators `gp-0x3d70..3d98`. Final mixer clamps: **±0x4e20** (at `0x2739e`), **±0x6400** (at `0x27772`), **±0x2800**, **±0xe10**.

The **LKAS lane accumulator** is `gp-0x3d8c`. Its value is preserved into `r26` and handed directly to the gate (Hop 8). **[V instr]**

Of the four `±0x2800` clamp blocks in this function, the LKAS lane is specifically the **`0x27442` block** — it clamps the `gp-0x3d8c` accumulator. The other three blocks (`0x26ea0`, `0x26ec4`, `0x276de`) are NOT the LKAS lane.

| Variable | Address | Role |
|---|---|---|
| LKAS lane accumulator | `gp-0x3d8c` | Handed to gate as `r26` at `0x277f2` |
| Mixed torque (gate input) | `0xFEDF1502` | Written by gate; ±0x2800 valid range |

---

### Hop 8 — Gate **[V instr]**

**Function:** `FUN_00042ac6`  
**What it does:** A plausibility sentinel — NOT a clamp. If the value is within ±0x2800 it passes unchanged; if outside that window it is replaced with sentinel `0x7FFF`.

Instruction sequence at `0x42ac6`:
```
addi 0x2800, r6, r13
addi -0x5001, r13, r0    ; overflow-detect: r6 > 0x2800 → carry
bnc  ...
movea 0x7fff, r0, r15
st.h r15, -0x6afe[gp]   ; write 0x7FFF sentinel to 0xFEDF1502
```

**Ceiling (V11A analysis):** The `+0x2800 / -0x5001` idiom means widening to ±W requires a second immediate of `-(2W+1)`. At `W=0x4000`, that becomes `-0x8001` — overflows imm16. So **±0x3FFF is the maximum value-edit window** for this gate. Anything above ±0x2800 that isn't also below ±0x3FFF will carry into the shaper's duplicate check and get zeroed (not clamped — zeroed).

---

### Hop 9 — Shaper (Final Command Output) **[V instr]**

**Function:** `FUN_00042af8`  
**What it does:** A dual-stage filter. First re-runs the gate's plausibility check, then applies a runtime limit, then a final magnitude clamp.

**Stage 9a — Duplicate plausibility check (at `0x43ae0`–`0x43af0`):**  
Reads `0xFEDF1502` (the gate output) and runs the same `±0x2800` idiom again:
```
addi 0x2800, r13, r13
addi -0x5001, r13, r0
cmovc 0x0, r13, r12      ; if |value| > 0x2800 → ZERO the command
```
This collapses anything outside ±0x2800 — **including the `0x7FFF` sentinel** — to exactly 0. This is the mechanism behind the LKAS cut observed in V10A: overshooting the window zeros the command, it doesn't just clamp it.

**Stage 9b — Runtime governor limit (at `0x43af6`):**  
```
r10 = *(gp-0x4f64) = 0xFEDF309C    ; runtime governor
```
This value is cal `tp+0x7202` = `0xC6202` = stock **4762**. It is itself zeroed if above 0x2800. This governor is the binding high-end limit for the MERGED command (LKAS + driver assist combined). For the LKAS-only path at V14 levels (arb out ≈835), the governor is never reached — the LKAS signal is well below 4762.

**Stage 9c — Final magnitude clamp (at `0x43b0e`–`0x43b1c`):**  
Clamps to **±0x2000 (8192)** stock.

| Variable | Address | Role |
|---|---|---|
| Final command | `gp-0x6b98` | Shaper output; 45 downstream readers (FOC, CAN `0x427` motor-torque) |

**V11A (unflashed study artifact):** Widened the shaper window to ±0x3FFF + clamp to ±0x4000 by editing bytes at `0x43b0e/12/18/1c`.

---

### Hop 10 — FOC → Motor **[V endpoints; mixer→q-ref handoff var OPEN]**

The shaper output `gp-0x6b98` routes into a **CSIG0 serial message frame** (serializer `FUN_000564ce` → `FUN_00016de6`). From there it is consumed by the FOC current regulator and ultimately drives the TSG20 PWM.

**FOC feedback chain (ADC-complete ISR):**
```
FUN_0006404c (INTADCA0I1, EIIC=0x600)
  → 0x6428e   reads 2 phase currents
  → 0x65afe   resolver sin/cos (12-bit ±0x800) → atan2 rotor angle
  → 0x68f52   rotor-speed estimator (Δθ·120000>>14, LPF, clamp ±13000)
  → 0x71272   Park/Clarke/PI/SVPWM voltage computation (duties ×51200.0)
  → TSG20 CMPU/CMPV/CMPW at 0xFFFFCCB0/B4/B8
```

The `0x71272` chain is the FOC **feedback** regulator, not the torque demand path. It consumes a q-current reference written by the steering task. The exact variable carrying the mixer output to `FUN_00071272` was not pinned by disasm — this is GAP 2 (narrowed but not closed).

---

## Part 2: Driver-Side Torque Path

Driver steering assist is a **separate path** from LKAS. It runs in a different task slot under the same 1ms scheduler and merges downstream at the mixer.

### Task Entry **[V structure, addresses gp-resolved]**

```
1ms scheduler FUN_0002214a
  → FUN_0006bb08
  → FUN_0006bea8 (task-slot dispatch)
      slot 3: FUN_0006651e   ← TORQUE-DEMAND TASK
```

### Assist-Mode State Machine (inside `FUN_0006651e`) **[V]**

State variable at `gp-0x4e65` = `0xFEDF319B`:

| State | Handler |
|---|---|
| 0 = normal | `FUN_0006634e` (assist curve interpolation) |
| 1/2 = transition | `FUN_00068dfe` |
| 3 = active + dual-sensor plausibility check | checks `tp+0x5970` vs `tp+0x5978`; fault → `FUN_000197b8(4)` sets status bit 4, reverts to mode 1 |
| 4 = fault | — |

There is also a **thermal gain polynomial** in this task: `(T−70)²×1.7e-6 + (T−70)×0.001 + 0.968` where T = `gp-0x4e7a`.

### Assist Curve Interpolation `FUN_0006634e` **[V]**

Interpolates by **temperature** between two row pointers:
- `gp-0x34ec` = `0xFEDF4B14` (row A)
- `gp-0x34e8` = `0xFEDF4B18` (row B)

Row struct: `{+4 torque, +6 speed, +8/+9, +0xc/+0xd gains (clamped 0..0x7f), +10 tempidx}`

Outputs demand into `gp-0x4fb8 / -0x4fbc / -0x4fb6 / -0x4fba` → `FUN_000690f8`.

**What these tables are:** The `0xC4A42` / `0xC4A6E` pair (§3c in the source doc) is the Honda assist-gain archetype — monotonic saturating int16 pairs. They feed the assist curve. **These are NOT the LKAS path.**

**V10A lesson:** Doubling `0xC4A42` / `0xC4A6E` made driver steering noticeably lighter (confirmed — it IS the driver assist gain) but also killed LKAS entirely. The kill mechanism is the assist-mode state machine: inflated driver torque continuously trips the driver-override/hands-on plausibility gate, dropping state machine into mode 1 or fault 4 and blocking LKAS actuation. The tables are real; the unintended interaction with the LKAS gate is the lesson.

### Torque Sensor Plausibility `FUN_00062948` **[V]**

Reads the three raw ADC channels:

| Variable | Address | Role |
|---|---|---|
| Torque ADC ch0 | `0xFEDF3174` (`gp-0x4e8c`) | Raw column torque |
| Torque ADC ch1 | `0xFEDF3176` (`gp-0x4e8a`) | |
| Torque ADC ch2 | `0xFEDF3178` (`gp-0x4e88`) | |

Compared against refs `0xFEDF316C/6E/70`; bounds from `tp+0x59ca/0x59ce`; delta limit from `tp+0x59c6`. Sets fault bits on out-of-range. These are hardware ADC values — **no software injection point here**.

---

## Part 3: Key Calibration Values (The Real Levers)

All addresses assume `tp = 0xBF000`. Addresses are in the flashed calibration band `0xC4000–0xFD0B8` inside `code.bin`. All in CRC-protected block `0xC6000` unless noted — recompute `0xC6FFC` after any edit.

### V14 Edits — Flashed and Confirmed (~2× LKAS at the wheel) **[V road-tested]**

These three values are the actual LKAS magnitude binders. The LKAS arb output (~835 at V14 vs ~418 stock) sits well below the 4762 governor, so the 2× doubling reaches the motor uncut.

| tp offset | Flash addr | Stock value | V14 value | Role |
|---|---|---|---|---|
| `tp+0x746c` | `0xC646C` | 891 | **1782** | Arb output GAIN — scales the LKAS share leaving arbitration |
| `tp+0x71b2` | `0xC61B2` | 512 | **1024** | Clamp A (positive rail) on the LKAS distributor lane |
| `tp+0x71b4` | `0xC61B4` | 512 | **1024** | Clamp B (negative rail) on the LKAS distributor lane |

### V18 Additional Change — Flashed and Road-Validated (Drives Well) **[V road-tested]**

V18 = V14 three edits above + one additional byte:

| tp offset | Flash addr | Stock value | V18 value | Role |
|---|---|---|---|---|
| `tp+0x74de` | `0xC64DE` | `0x11` (17) | **`0x1B` (27)** | Re-engage/debounce counter ceiling in `m_steer_torque_arbitration` |

**What this ramp does (corrected understanding):** `tp+0x74de` is the count ceiling of the re-engage debounce state machine (read 8× in `m_steer_torque_arbitration`). Counter is `gp-0x6756`, init = `(ceiling>>1)+1`. It operates on driver-torque input `gp-0x6a5e`, with state transitions at `gp-0x3d36` / `gp-0x6809`. Changing 17→27 **lengthens the re-engage span** (~8→~13 steps), softening recovery after a driver-override event. It is NOT "faster re-engage" — it is the recovery ratchet.

**Earlier wrong label:** this value was initially called an "output rate limiter" and described as controlling a slew on the delivered command. That framing is **RETRACTED** — there is no output rate-limiter cal value. The shaper output `gp-0x6b98` has only a ±0x2000 magnitude clamp plus a ±5 change detector (for lockstep monitor), no rate-of-change limit.

### Rejected V16 Change — Slew Lever Was Inverted **[V — do not use]**

| tp offset | Flash addr | Stock value | V16 intent | What it actually does |
|---|---|---|---|---|
| `tp+0x71d6` | `0xC61D6` | **0** | 0→14 ("re-enable slew") | Step size of a rate limiter on **internal persistent state** `gp-0x356c`; step=0 means that lane is **frozen at 0** (dormant). Setting 0→14 **activates an uncalibrated 2D shaping map** (`0xC6770` speed curve × `0xC69E8` torque curve), not a damper restore. |

**Also rejected:** Deadband `0xC6424` (`tp+0x7424`) — gates only the `gp-0x356c` limiter; with slew=0 that state is pinned at 0, so any deadband change is inert. Deadband and slew are coupled — the deadband only has meaning once slew≠0.

### Governor (Combined Ceiling) — Not Needed for 2× **[V]**

| tp offset | Flash addr | Stock value | V15 intent |
|---|---|---|---|
| `tp+0x7202` | `0xC6202` | **4762** | Raise ceiling for >2× |

This is the runtime governor `gp-0x4f64` = `0xFEDF309C`, applied in `FUN_0004503c` and the shaper. It is the binding high-end limit for the **merged** LKAS + driver command. At V14 LKAS levels (~835), the governor is never approached — the LKAS path is request-limited far below 4762. Editing this value only matters if you are trying to push the merged signal above 4762.

---

## Part 4: What the Staircase Looks Like at Full Input

At full LKAS input (`STEER_TORQUE = 4096`), values cascade through the path:

| Stage | Function / addr | Stock limit | Value at x=4096 |
|---|---|---|---|
| Scale ×−4, clamp ±0x4000 | `FUN_00052676` @ `0x526d2` | ±16384 | **16384** (lands on rail) |
| Arbitration limit (table) | `FUN_00028ea6` / `0xE4180` | ±15360 | 15360 |
| Distributor lane +4 | `FUN_00025c32` @ `0x25c9c` | ±0x2800 | 10240 |
| Mixer lane `0x27442` | `FUN_00026c80` | ±0x2800 | 10240 |
| Gate sentinel check | `FUN_00042ac6` @ `0x42ac6` | pass if ≤0x2800, else 0x7FFF | ≤10240 or sentinel |
| Shaper duplicate check | `FUN_00042af8` @ `0x43ae8` | collapse to 0 if >0x2800 | ≤10240 or 0 |
| Shaper governor | `0xFEDF309C` | 4762 stock | ≤4762 |
| **Shaper final clamp** | `0x43b0e` | **±0x2000 (8192)** | **8192 (binding)** |

So stock full-scale = **8192**. V14's gain/clamp edits raise the LKAS share leaving arbitration, which shifts where the signal gets cut earlier in the chain (not at the waterfall above, which bounds the merged signal).

**Hard ceiling for value edits:** The gate (`0x42ac6`) and shaper duplicate check (`0x43ae8`) both use the `+0x2800 / -0x5001` plausibility idiom. Widening to ±W requires `-(2W+1)` as the second immediate; at W=0x4000 that overflows imm16. **±0x3FFF (~2×) is the maximum window reachable by value edits.** Anything above that requires restructuring the comparison sequences (a code rewrite).

---

## Part 5: Variables to Watch in Ghidra / Bench Capture

If you have a bench RAM capture or dynamic probe, these are the key addresses to log:

| Address | gp-offset | What it tells you |
|---|---|---|
| `0xFEDF6BD8` | — | LKAS routed buffer (slot 17); `STEER_TORQUE` int16 BE at +0/+1 |
| `0xFEDF1652` | `gp-0x69ae` | LKAS setpoint after ×−4 clamp; should be ±0x4000 at full input |
| `0xFEDF14C4` | `gp-0x6b3c` | Arbitration final gated command |
| `0xFEDF1502` | `gp-0x6afe` | Mixed command entering shaper (gate output); ±0x2800 valid range |
| `gp-0x6b98` | — | Shaper final output; 45 downstream readers |
| `0xFEDF1288` | `gp-0x6d78` | Master 32-bit status bitfield; bit 0 = state handler, bit 4 = torque-sensor fault, bit 15 = motor-shell enable |
| `0xFEDF319B` | `gp-0x4e65` | Assist-mode state (0=normal, 3=active, 4=fault) |
| `0xFEDF309C` | `gp-0x4f64` | Runtime governor value (stock 4762) |
| `0xFEDF68CC` | `gp-0x1734` | Shared RX scratch (pre-route) — NOT the LKAS buffer; here for context |

**Master arbitration API** (useful for decoding mode transitions):
- `FUN_000197d0(n)` — read bit n of `0xFEDF1288`
- `FUN_000197b8(n)` — set bit n (fault/fault-clear paths call this)
- `FUN_000197ea` — clears bit 0

---

## Part 6: Tooling Notes for Ghidra (This Project)

- **CALL xrefs now work.** Earlier sessions noted call xrefs returned 0; auto-analysis was re-run and callers/callees resolve (`get_function_callers`, `get_function_callees` return real results).
- **DATA xrefs do NOT resolve gp-relative accesses.** Only absolute-mode RAM accesses of the same variable appear in `xrefs_list`. Follow data flow manually through the decompiled output.
- **`FUN_00025c32` and `FUN_00026c80` fail to decompile** with `Field TAUJ0RSF does not fit in structure TAUJ0_registers_t`. Use `disassemble_function` for these two — the decompiler has a type-definition edge case.
- **Do not re-run auto-analysis** while a subagent is using port 8193 — it disrupts the live session.
