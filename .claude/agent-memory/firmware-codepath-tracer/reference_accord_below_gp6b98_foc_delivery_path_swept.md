---
name: accord-below-gp6b98-foc-delivery-path-swept
description: FIRST full sweep BELOW gp-0x6b98 (A160 39990-TVA-A160) — complete 45-site access map, the proven 3-input boundary of the FOC core FUN_00071272, the gp-0x6c2c filtered-derivative bridge with byte-read EMA cals, and four corrections to the older downstream-chain memory. Load before any FOC / current-loop / motor-delivery work.
metadata:
  type: reference
---

# Below gp-0x6b98: the delivery / FOC path (2026-07-30 sweep, stock `code.bin`)

Method: exact V850 byte scan (disp16 + disp23 + LE32 literal, per
[[v850e2-extended-disp23-encoding-solved]]) cross-checked against GhidraMCP. Scanner validated
against 4 known-good ground-truth sites before use.

## gp-0x6b98 (0xFEDF1468) complete access map — 45 accesses, matches the old "~45" note

**33 disp16 + 12 disp23. 4 WRITERS, 41 readers.** Plus 2 LE32 literal refs to 0xFEDF1468 at
`0x89C90` and `0xBBC68` (descriptor/pointer tables, not instructions).

**Writers (only 4, image-wide):**
- `0x43B52`, `0x43DFC` — both in the soft-EME shaper `FUN_00042af8`. The normal producers.
- `0x6E104` (`FUN_0006e09a`), `0x6E1DC` (`FUN_0006e140`) — a **test-mode open-loop torque
  injector**: forces `gp-0x6b98 = gp-0x4f64 * cal(tp+0x7c3c)` and writes the lockstep shadow
  `gp-0x4ce2` too. Both have **no direct callers**; they are dispatched from a pointer table at
  **`0xBCB14`/`0xBCB18`** (adjacent entries), take `param_1` 0=init/1=run, and set a step id
  `gp-0x2908 = 8` / `9`. Duration gate `cal tp+0x7c22`. Treat as factory/EOL self-test.
  ⚠ Reachability in normal driving NOT closed — see Open items.

## 🛑 The FOC core's boundary is only THREE variables wide

`FUN_00071272` `[0x71272,0x75717]` makes **389 gp-relative accesses, 112 distinct offsets read**.
Of those, exactly **three have any writer outside the FOC region `[0x60000,0x84000)`**:

| input | meaning | written by |
|---|---|---|
| `gp-0x6c2c` | filtered ×32 derivative of rotor speed (see below) | `0x4184E`, `0x41AC2` (`FUN_00041464`) |
| `gp-0x6abe` | filtered rotor speed | `0x41790/0x417A0/0x419F8/0x41A18` (`FUN_00041464`) |
| `gp-0x6762` | mode byte; gated at `0x71298` vs 0xFA and 0x2C | `0x490FE/0x49872/0x49880` |

Everything else it reads is its own private scratch (`gp-0x3xx..0x5xx`) or FOC-internal.
**`gp-0x6b98` itself is never read inside the core** (re-confirmed).

**⇒ The torque command stays ON-DIE.** Whole-image r0-relative peripheral scan: CSIG0_B1 has
exactly 2 accesses image-wide (`0x69A1A`, `0x69A9E`, both `ld.hu 0xFFFFE442`, in `FUN_000699ea`);
no CSIG/CSIH write path exists anywhere on the command chain, and no `movhi 0xFF70/0xFF71/0xFF72`
(CSIG B0) site exists at all. The "may route off-die over CSIG0" **[OPEN]** in the golden model is
**FALSIFIED** — delivery is TSG20 on-die (TS0CMPU/V/W `0xFFFFCCB0/B4/B8`).

## The real bridge: gp-0x6b98 GATES, it does not feed, the current loop

`FUN_00041464` (1 kHz, dispatched `w_steer_control_task 0x2214a` → `FUN_0006bcb2` → here) is the
only producer of the core's two signal inputs. gp-0x6b98's role there is **only**:
- `0x41846 ld.h -0x6b98,gp,r9` → `0x41852 addi 0x2000,r9,r11` / `0x41856 addi -0x4001,r11,r0` /
  `0x4185E bc` — the ±0x2000 validity guard. Failing it jumps to the sentinel branch.
- `0x41682`-ish sign test — selects `gp-0x6ac2 = |filtered speed|>>10` when
  `sign(speed) != sign(gp-0x6b98)`, else 0. An **opposing-motion / back-drive detector**.
  gp-0x6ac2 feeds back into the app region (readers `0x346A4`, `0x347C0`, `0x42F42`, `0x4434E`,
  `0x41C78`) — a real inner→outer feedback route.

**gp-0x6c2c chain (exact integer arithmetic, addresses annotated):**
```
x   = gp-0x4f50                       # rotor-speed estimate; SOLE writer 0x68FDE (FUN_00068f52)
y0 += ((x<<10) - y0) * K0 >> 7        # 0x415F8  K0 = cal 0xC643C = 37   (alpha 0.2891, fc 54.3 Hz)
d   = y0[n] - y0[n-1]                 # 0x4160C  first difference
d32 = clamp(d*32, +-0xFA0000)         # 0x41614  (else 0xFA0000 if |d| > 0x7D000)
yA += (d32 - yA) * KA >> 6            # 0x41640  KA = cal 0xC40DC = 22   (alpha 0.3438, fc 67.0 Hz)
gp-0x6c2c = yA >> 9                   # 0x41AC2
gp-0x6c2e = yB >> 9                   # sibling, KB = cal 0xC40DA = 3 (alpha 0.0234, fc 3.77 Hz)
                                      #   NOT read by the FOC core (readers 0x343B4/0x34AFE/0x36F3A)
```
Measured response of gp-0x4f50 → gp-0x6c2c at fs=1 kHz: **+55° phase lead and 7.5x (17.5 dB) gain
at 20.9 Hz**; broad maximum 12.1x (21.6 dB) at 61 Hz. It is a **differentiator/lead term, NOT
resonant** — first-order shape, no Q peak, no notch/biquad anywhere on the path.

In the core: `0x71378 ld.h -0x6c2c,gp,r9` → `cvtf.ws` → `mulf.s` by literal `0x3783126F`
(= 1.5625e-05 = 1/64000) → `gp-0x454`. `gp-0x458 = float(gp-0x6abe)`. `gp-0x454` is genuinely
consumed in the motor model (`0x723F8` → `0x72406 mulf.s`, chained with motor-param floats
`tp+0x6698/0x669c/0x66a4/0x66b0` = `0xC5698/0xC569C/0xC56A4/0xC56B0` =
0.61538464 / 3.3653846 / 3.75 / 0.0016346154), plus reads at `0x73878`, `0x73F2C`.

## Four corrections to [[accord-tva-downstream-chain]]
1. **`gp-0x6bf6` has ZERO readers** (writers `0x3BAC0`, `0x3BC0E` in `FUN_0003b8f6`). The
   "motor current command" is **write-only / dead**, not a delivery hop.
2. **`gp-0x6c38` has ZERO readers** (writers `0x4172E`, `0x4199A`). The "feedforward term" is dead.
3. **`gp-0x6afe` has exactly 1 reader**, `0x43AE0` — back inside the shaper `FUN_00042af8`. It is
   **not** "the absolute final write before the motor command is consumed downstream".
4. `FUN_00069b8e` is **not startup-only** — it is called every 1 kHz pass under mask `0x830`. It is
   a standstill/idle monitor (|gp-0x6b98|, |gp-0x6abc|, |gp-0x4f60| all under cals + a timer).

## Other functions below the shaper
- **`FUN_00070a98`** (1 kHz, mask 0xc30) — **torque-delivery consistency monitor → DTC 0x26**.
  Synchronous demodulator (sin/cos via `FUN_0006b28e`, angle scale literal `0x39C90FDB` = pi/8192)
  producing a commanded-vs-achieved residual, a leaky residual integrator (`gp-0x2884`, cal
  `tp+0x6054`, cap `tp+0x6060`), a **shrinking** trip threshold `gp-0x5028 = cal(tp+0x605c) - integ`,
  and a saturating output integrator `gp-0x5024` (anti-windup = hard clamp to `cal tp+0x6050` or
  `tp+0x604c`). Outputs are the DTC and gp-0x50xx state only.
- `FUN_00065afe` `0x65C90` — reads gp-0x6b98 for its SIGN only (MTPA/advance-angle branch select).
- `FUN_0007c4f2`/`FUN_0007c94a`, `FUN_00081b24`, `FUN_00056420/56518/568d0`, `FUN_00059912/59e7a`
  (12 of the 12 disp23 reads live in the last two) — monitor/telemetry, not command path.

## PWM / dead-time / ripple (question: fixed-frequency artefacts)
- **Dead-time `TS0DTC0W`/`TS0DTC1W` (`0xFFFFCC6C`/`0x70`) are written ONLY at init (`0x6C498`,
  `0x6C49C`, = 80 ticks) and zeroed at shutdown (`0x6C5B6`, `0x6C5BA`). There is NO runtime
  dead-time compensation.**
- `TS0CMP0` (`0xFFFFCC58`, the period) IS written at runtime at `0x6C5E8`:
  `TS0CMP0 = (arg * 0x190) >> 12`. arg = 51200 (the FOC duty scale) gives exactly 5000 = the init
  constant, so the carrier is nominally FIXED. ⚠ It is *parameterised*, so a varying arg would
  modulate the carrier — arg's source not traced.
- Full TSG20 register census done; no angle-indexed compensation table or harmonic-injection
  table was found on this path.

## Tool notes
- 🛑 `get_xrefs_to 0xFEDF13D4` (gp-0x6c2c absolute) returned **"No references found"** — a textbook
  **misleading zero**. Ghidra does not resolve gp-relative displacements to xrefs. The byte scan
  found 2 writers + 6 readers. Never let a gp-variable xref null be load-bearing.
- `decompile_function` requires `address`, not `name`; `disassemble_bytes` requires `start_address`.

## Open items
1. **Reachability of the `0xBCB14` test-injector table in normal driving** — who indexes it, and is
   there a service-mode gate? Next step: byte-scan for the table BASE (0xBCB14 minus k*4) and find
   its indexing function.
2. **`gp-0x6762` mode byte semantics** (values 0xFA / 0x2C gate the whole FOC core at `0x71298`).
3. **Rate transition**: `gp-0x4f50` is written in the ADC ISR (~8-16 kHz) and sampled by
   `FUN_00041464` at 1 kHz with the EMA applied AFTER the downsample — no anti-alias filter.
   Aliasing to 21 Hz would need content near 979-1021 Hz; not evaluated.
4. **PCLK for TSG20 still an assumption** (80 MHz ⇒ 8 kHz carrier at period 5000, HT-PWM
   triangular). `TS0CTL5` ADC-trigger value still unread ⇒ 8 vs 16 kHz ISR unresolved.
5. No isolated Kp/Ki pair located in `FUN_00071272`; control law remains model/feedforward-heavy
   off the `0xC5xxx` motor-parameter block.

Related: [[reference_accord_foc_inner_current_loop_architecture]], [[accord-tva-downstream-chain]],
[[v850e2-extended-disp23-encoding-solved]]
