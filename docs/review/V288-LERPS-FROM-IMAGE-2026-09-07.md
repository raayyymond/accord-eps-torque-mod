# V288 LERPs and cave content, read from the images -- 2026-09-07

Method: raw little-endian byte reads of `stock_fw_dump/code.bin` and the `_v282_...plain_image.bin`
(V288's unchanged calibration surface) plus a byte-level re-decode of the shipped
`_v288_...plain_image.bin`. Script: `analysis-2020accord/_scratch/out/_v288_lerp_reader.py`.
Full data: `analysis-2020accord/_scratch/out/v288_lerps.json`.

Address key: flat binary, file offset == target address. `tp = 0xBF000`, `gp = 0xFEDF8000`.

## 1. Assist (setpoint) map, live selector 7 -- record at `0xE502C` (ptr table `0xC9A88`, slot 7)

| raw 0xE4 counts (X) | 0 | 12 | 20 | 24 | 32 | 64 | 96 | 128 | 160 | 240 |
|---|---|---|---|---|---|---|---|---|---|---|
| **stock Y** | 0 | 24 | 42 | 50 | 62 | 100 | 126 | 154 | 166 | 172 |
| **V282 = V288 Y** | 0 | 52 | 86 | 103 | 138 | 275 | 413 | 550 | 688 | 1032 |

Map idx clamp (`tp+0x74F0` = `0xC64F0`): **240** on both images -- EVIDENCE.
No cal byte changed between V282 and V288 -- confirmed by the full-window diff below.

## 2. Kp / Kd, live selector 7

| | X (idx) | stock Y | V282=V288 Y |
|---|---|---|---|
| Kp, record `0xE5378` (ptr `0xCB994[7]`) | 0, 68, 112, 136, 208 | 248, 512, 645, 696, 696 | **248, 248, 248, 248, 248 (flat)** |
| Kd, record `0xE511C` (ptr `0xCB7D4[7]`) | 0, 11, 22, 32 | 128, 128, 128, 128 | 128, 128, 128, 128 (unchanged) |

## 3. Clamps and cal cells (identical on V282 and V288 -- no cal byte moves in this build)

| cell | addr | value |
|---|---|---|
| T clamp | `0xC61B4` | 3072 |
| **D clamp** | `0xC61B6` | **10240** (V287 rev 2 had moved this to 7680; NOT carried into V288, which branches from V282) |
| deadband | `0xC61B8` | 102 |
| I anti-windup | `0xC61BA` | 10240 |
| P clamp | `0xC61BC` | 15360 |
| sum clamp | `0xC61BE` | 15360 |
| Ki | `0xC63E6` | 0 |
| fb pole (a,b) | `0xC63E8`/`EA` | 923, 1560 |
| output-lag pole (a,b) | `0xC63EC`/`EE` | 992, 507 |
| ipath cal | `0xC62E4` | 4 |
| feedback clamp | `0xC62E6` | 46080 |
| r24 arms (0/1/2/3) | `0xC6440..46` | 2048, 1024, 512, **5244** |
| carrier gain | `0xC6CD0` | 5346 |

Override/fade taper records (pointer tables, slot 7; identical stock vs V282/V288):

| taper | record | X | Y |
|---|---|---|---|
| fadeA `0xCBA04[7]` | `0xE5404` | 70,72,78,80 | 254,234,12,0 (cliff) |
| fadeB `0xCBA74[7]` | `0xE547C` | 70,72,78,80 | 254,234,12,0 (cliff) |
| `0xCB8B4[7]` | `0xE5284` | 32,38,80,112 | 255,255,255,0 |
| `0xCB924[7]` | `0xE52FC` | 32,42,80,112 | 255,255,255,0 |

## 4. The V288 cave -- full-window diff, V282 vs V288 (`0x13000`-`0x100000`)

**Exactly 5 byte runs differ, 78 bytes total** -- matches the build script's claim of "FOUR changed
regions plus one CRC trailer":

| run | size | content |
|---|---|---|
| `0x29D72`-`0x29D76` | 4 B | the hook: `st.h r16,-0x6a32,gp` -> `jr 0xC4BDC` |
| `0xC4BD6`-`0xC4BDA` | 4 B | old cave epilogue: `jmp [lp]` -> `jr 0xC4C00` |
| `0xC4BDC`-`0xC4BFE` | 34 B | **the filter body** (see below) |
| `0xC4C00`-`0xC4C20` | 32 B | **the telemetry sign rung + relocated epilogue** (see below) |
| `0xC4FFC`-`0xC5000` | 4 B | CRC trailer for the touched block |

### 🛑 Finding: the two cave regions are NOT what the current `build_v288_tva.py` source describes

Decoding the actual bytes (independently, not from the script's `FILT`/`TELE` python source):

- The **hook** (`0x29D72`) jumps to `0xC4BDC` -- which the script's own module constant calls `TELE`.
  That 34-byte region decodes to `ld.h y[n-1]`, `sub`, `mov`, `sar 0x4` (**K=4, confirmed dose**),
  the floor-fix branch pair, `add`, `st.h`, `ld.h`, `jr 0x29D76`. **This is the filter**, not telemetry.
- The old cave's `jmp[lp]` site (`0xC4BD6`) jumps to `0xC4C00` -- the script's own constant `FILT`.
  That 32-byte region decodes to `mov 0,r7`; `ld.h y[n]`; `cmp 0`; `bge +4`; **`mov 1,r7`**; `ld.bu`
  byte 4; **`andi 0xFE`**; `or`; `st.b`; `movea`; `jmp[lp]`. **This is the telemetry sign rung.**
  - The variable *names* `FILT`/`TELE` in the current script are simply swapped versus what the
    image contains at those two addresses -- cosmetic by itself.
  - **Not cosmetic:** the immediate is **1** and the mask is **`0xFE`** -- i.e. the rung targets
    **byte 4 bit 0**, mask clears only bit 0. That is the script's own documented, *retracted*
    **"rev 1"** bit choice ("REV 1's BIT CHOICE WAS A FAIL ... bits 0-2 are STOCK HONDA flags written
    by the FRAME BUILDER, not free"), **not** the "rev 2" fix the current source describes (byte 4
    bit 5, `NEW_BIT=0x20`, mask `0xDF`). The `.bin` on disk was not rebuilt after the rev-2 source
    edit, or was cut from an older revision of the script.
  - **Consequence, EVIDENCE-grade:** every time this cave fires, it overwrites a **live Honda CAN
    flag** at `0x14A` byte 4 bit 0 (stock writers `0x55AC0`/`0x55AE8`/`0x55B06`, all executing
    *before* the cave hook at `0x55C0E`) with `sign(filtered setpoint)` instead of preserving it.
  - This must be re-verified and, if confirmed on a fresh disassembly, re-cut before this specific
    `.bin` is flown. It does **not** affect the filter math itself (K=4, corner ~10.3 Hz, all
    correctly present), only the telemetry side-channel's bit choice.

Filter body (`0xC4BDC`), K confirmed **4** from the `sar 0x4` byte directly (not from the build
script's `K_SHIFT` variable) -- matches the "K=4 flown" dose in the script's own ladder table.

## 5. Filter response (linear small-signal), K=4 flown vs K=3 fallback

| K | pole a | f_c | \|H\| 3 Hz | \|H\| 20 Hz | \|H\| 40 Hz | tau | DC group delay | kick divisor |
|---|---|---|---|---|---|---|---|---|
| 4 (flown) | 0.9375 | 10.28 Hz | 0.960 | 0.457 | 0.249 | 15.5 ms | 15.0 ms | /16 |
| 3 (fallback) | 0.8750 | 21.28 Hz | 0.990 | 0.729 | 0.470 | 7.5 ms | 7.0 ms | /8 |

Full 60-point log-spaced magnitude/group-delay sweep (0.5-50 Hz) is in `v288_lerps.json`
under `filter_response.K4` / `filter_response.K3`.

## 6. Step response and per-tick kick (integer-exact V850 emulation)

D-term clamp `0xC61B6` = 10240 => **dE threshold to bind D = 640** (D = 16*dE).

| step target | path | first-tick kick | dE = 32*kick | crosses D-clamp (\|dE\|>=640)? |
|---|---|---|---|---|
| 123 (a single command step) | raw | 123 | 3936 | **YES** |
| 123 | filtered, K=4 | 7 | 224 | no |
| 1032 (full-scale, map Y max) | raw | 1032 | 33024 | **YES** |
| 1032 | filtered, K=4 | 64 | 2048 | **YES** (large enough step still rails D even filtered) |

Full 160-tick series (`filtered_y`, `filtered_kick_per_tick`, `raw_y`, `raw_kick_per_tick`) for
K=3 and K=4, targets 123 and 1032, are in `v288_lerps.json` under `step_responses`.

## 7. Signal-flow facts for the diagram (address-cited; EVIDENCE vs BELIEF marked)

See `signal_flow_facts` in the JSON. Summary:

```
0xE4 byte -> decode store 0x526F2 (gp-0x69ae) [BELIEF, cited from STATE.md]
  -> symmetric clamp, Q16 LERP scale, >>22 [BELIEF, not re-derived this pass]
  -> map idx clamp 0xC64F0 = 240 [EVIDENCE]
  -> assist map record 0xE502C, slot 7 [EVIDENCE]
  -> mulh r13,r16 @0x29D6C (sp) [BELIEF, address cited only]
  -> V288 CAVE: hook 0x29D72 -> filter body 0xC4BDC (K=4), state gp-0x6a32 [EVIDENCE]
  -> resume 0x29D76 (shl 0x5 = x32) [BELIEF, address cited only]
  -> E = 32*sp - fb [BELIEF]
  -> P (Kp flat 248, record 0xE5378) / I (Ki=0, 0xC63E6) / D (16*dE, clamp 0xC61B6=10240) [EVIDENCE]
  -> sum clamp 0xC61BE [EVIDENCE]
  -> override fade (0xCBBC4, per prior memory) [BELIEF -- NOT the same table as the 4 taper
     records read in section 3, which are the pre-PID input-side tapers, not this post-PID one]
  -> EME / governor / motor [BELIEF]
```

## Open items for the orchestrator

1. **Re-verify the telemetry-bit finding (section 4) independently before the page ships it as
   fact.** If confirmed, either re-cut the `.bin` with the rev-2 fix actually applied, or the page
   must disclose that the shipped candidate clobbers a live Honda flag rather than using bit 5.
2. The `override post-PID fade 0xCBBC4` signal-flow stage is carried as BELIEF from prior memory
   and was not read in this pass -- it is not among the four taper pointer tables read in section 3.
