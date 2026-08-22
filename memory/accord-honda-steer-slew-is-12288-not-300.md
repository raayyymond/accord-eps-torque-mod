---
name: accord-honda-steer-slew-is-12288-not-300
description: "openpilot's Honda steer rate limit is 12,288 counts/s, NOT 300. STEER_DELTA_UP=3 is 3 NORMALISED units per second applied before the multiply by STEER_MAX, not 3 counts per frame. The wrong reading is 41x too tight and would falsely kill any openpilot-side excitation plan."
metadata:
  type: reference
---

# 🛑🛑★★★★★ A 41× ERROR THAT NEARLY KILLED A VIABLE MEASUREMENT PATH

Orchestrator-verified two independent ways, 2026-08-21.

## The trap
`opendbc/car/honda/values.py:38-40` reads `STEER_STEP = 1` (100 Hz), `STEER_DELTA_UP/DOWN = 3`.
The obvious reading — 3 **counts** per 10 ms frame = 300 counts/s — is **WRONG**.

## The code [EVIDENCE — orchestrator read it directly, not relayed]
```
carcontroller.py:291   limited_torque = rate_limit(torque_cmd, self.last_torque,
                                        -STEER_DELTA_DOWN * DT_CTRL, STEER_DELTA_UP * DT_CTRL)
opendbc/car/__init__.py:95   rate_limit(new,last,dw,up) = clip(new, last+dw, last+up)
opendbc/car/__init__.py:11   DT_CTRL = 0.01
carcontroller.py:305   apply_torque = int(np.interp(-limited_torque * STEER_MAX, ...))   <-- 14 LINES LATER
```
⇒ `torque_cmd` is **NORMALISED (−1..+1)** when the limiter runs. The step limit is
`3 × 0.01 = 0.03` normalised per frame = **3.0 normalised/s = full scale in 1/3 s**.
The comment on `values.py:39` says it outright: `# min/max in 0.33s for all Honda`.
`CAR.HONDA_ACCORD` gets `torqueBP/torqueV = [[0,4096],[0,4096]]` (`interface.py:137`)
⇒ **STEER_MAX = 4096** ⇒ **12,288 counts/s.**

## The car agrees [EVIDENCE — `analysis-2020accord/e4_excitation/i_measured_slew.py`]
| route | p50 abs(delta e4)/frame | p99 | vs `0.03 x 4096 = 122.88` |
|---|---|---|---|
| 75 | 13 | **123** | bit-exact |
| 76 | 8 | **123** | bit-exact |
| 73 | 14 | 244 | = 2x122, rows spanning two 0xE4 frames |

**67–73 % of engaged frames already step more than the WRONG ceiling.**

## Consequence
Max clean sine amplitude `= 12288/(2*pi*f)`: **244.5 ct at 8 Hz** · 93.1 ct at 21 Hz — out of 4096.
**Not 5.97.**

⊕ **The panda does not constrain 0xE4 at all while engaged.**
`opendbc/safety/modes/honda.h:267-275` is the only check and it is
`if (!controls_allowed) { if (data[0]|data[1]) tx = false; }` — no magnitude limit, no rate limit.
⇒ **Any openpilot-side excitation plan fits inside the stock limiter; nothing needs raising.**

Related: [[accord-lkas-lane-passes-8hz-nearly-unattenuated]] ·
[[feedback-no-openpilot-side-modifications]] · [[accord-427-source-cell-changes-by-build]]
