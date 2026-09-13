---
name: accord-fb-filter-sentinel-reset-runs-disengaged-and-deadzone
description: "The fb-lag state is reset ONLY by the gp-0x3d2c sentinel (1 = normal, 2 = bailed), NOT by the 0x2A164 disengage route; the filter runs every tick including disengaged so s is never stale on re-engage; and lowering b opens a sar-floor DEAD ZONE of 1024/b counts that is asymmetric toward negative."
metadata:
  type: reference
---

Verified 2026-09-13 on `code.bin`, byte-identical in V282. Full trace:
`docs/traces/TRACE-2026-09-13-fb-lag-filter-bytes.md`.

## 1. The reset is a SENTINEL, and the disengage route does NOT clear the state

`gp-0x3d2c` has exactly one writer, `0x290D4 st.b r1,-0x3d2c[gp]`, and `r1` is:
* **1** on the normal path (`0x28F74 mov 0x1,r1`),
* **2** on the bail path (`0x290B0 mov 0x2,r1`).

The filter loads `s` only when the sentinel reads **exactly 1** (`0x28F72 cmp 0x1,r9 / bne 0x28F82`).
So **any tick that bails zeroes `s` on the next tick that runs.** Four bail sources only:
`0x28F3C`, `0x28F48`, `0x28F5A`, `0x28F62`.

🛑 **CORRECTS the record's "the three hook-skipping routes reset every PID cell".** The `0x2A164` and
`0x2A0C6` routes zero registers `r24/r29/r27/r22/r12`, set `r16 = 0x7FFFFFFF`, and write the published
cells `gp-0x6b2e/32/34/36` plus `E_prev` (`gp-0x6cf8 := 0x7FFFFFFF`) and `gp-0x6dd0 := 0`. They
**never touch `gp-0x3d30` (fb state) or `gp-0x3d3c` (output-lag state)** — consistent with those cells
having only two accesses each image-wide, both inside their own filter.

## 2. The filter runs EVERY TICK, engaged or not — so `s` is never stale on re-engage

The filter is at `0x28F4C`; the engagement guard is at `0x29A48`, **2,812 bytes later in the same
straight-line flow**. The four pre-filter bails test only `gp-0x4f60` sensor plausibility, the arm flag
`gp-0x6752`, and `|x| <= 12000` — **none is an engagement condition**. `gp-0x6752` is a **±1** flag
(writers `0x490C0` -> +1, `0x49838` -> +1, `0x49844` -> -1, each mirrored into `gp-0x4c2d`); it is
**never written 0**. ⇒ `s` tracks the wheel continuously while disengaged. This is what makes a slow
(2-8 Hz) pole safe where a stale state would otherwise be the main hazard.

🛑 **`r25` couples the two.** `0x290AC mov 0x1,r25` (normal) / `0x290C0 mov 0x0,r25` (bail), and
`0x29A60 cmp r0,r25 / 0x29A64 jr 0x2A164`. **A filter bail FORCES skip 2 — the PID cannot run on a
tick where the filter bailed.** Any cave at `0x28F4C` must not disturb `r25`.

Exhaustive branch sweep of `FUN_00028ea6`: exactly **three** skips (`0x29A5C`->`0x2A164`,
`0x29A64`->`0x2A164`, `0x29A70`->`0x2A0C6`) and exactly **four** bails to `0x290B0`. No fourth route.
Confirms the V290 trace: the skips bypass `0x29D72` but cannot bypass `0x28F4C`.

## 3. 🛑 Lowering `b` opens a quantiser DEAD ZONE — the design risk nobody had priced

The input term is `floor(b*x/1024)` (`0x28F9A`). It is **identically zero** for `0 <= x < 1024/b`, and
for a constant small `x` the state never leaves 0 — so the output is identically zero, not merely
attenuated.

| `b` | `f_c` | dead zone (raw counts) | deg/s (8 counts per deg/s) |
|---|---|---|---|
| 1560 (stock) | 16.5 Hz | 0.66 | 0.08 |
| 772 | 8.0 Hz | 1.33 | 0.17 |
| 293 | 3.0 Hz | 3.49 | 0.44 |
| 201 | 2.0 Hz | 5.09 | 0.64 |

Because `sar` floors toward −∞ it is **asymmetric**: `x=+3` with `b=293` gives 0, `x=−3` gives −1. Over
a symmetric small oscillation the mean output is **negative**. A 1-count step in `x` produces `r26` =
1,2,2,2,… at stock but **identically 0** at every candidate lowered pole — so the first-tick D from a
1-count step is −16 at stock and **0** at (1005,293)/(1013,170)/(1020,62).

**Pre-existing, not a regression:** `s = -1` is an absorbing state at every `a` in 923..1023
(`floor(-a/1024) = -1` for all `a < 1024`), so `r26` rests at **−2** with `x = 0` even on stock. What
the edit changes is the dead zone's **width**, by up to 7.7× at 2 Hz. **Check `b` against the measured
`x` distribution during a grinding episode before choosing it.**

## 4. DC-held pairs — several circulating values are WRONG
`DC = 2b/(1024-a)`, target `3120/101 = 30.8911`:
(1005,**293**) ✔ −0.16 % · (1013,**167**) ✘ −1.71 %, use **170** · (1020,**60**) ✘ −2.88 %, use **62**.
Spanning 2-8 Hz: (974,772) 8.0 Hz · (986,587) 6.0 Hz · (992,494) 5.1 Hz · (999,386) 3.9 Hz ·
(1005,293) 3.0 Hz · (1008,247) 2.5 Hz · (1011,201) 2.0 Hz.

Related: [[accord-fb-lag-filter-bytes-and-gate1-private]],
[[accord-disengage-skips-the-pid-hook-and-gp-0x6cf8-is-hondas-first-tick-sentinel]],
[[reference_accord_0x28f4c_rate_operand_hook_runs_every_tick]].
