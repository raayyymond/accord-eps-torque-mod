# ★ `0xC646C` is a SHARED sensor-scale with 6 readers — NOT "the LKAS authority gain"

**Correction of record, 2026-07-27.** Enumerated independently twice (subagent + lead raw byte scan over
both tp encodings including the `disp|1` form): **exactly 6 readers, no stores, no float mirror**, and
**neither hard-shutdown monitor is among them**. Stock = 891, on-car = 3564 (exactly 4x).

| # | addr | function | multiplicand | verdict |
|---|---|---|---|---|
| 1 | `0x2a1ee` | `FUN_00028ea6` arbitration | IIR-blended LKAS setpoint x gain x polarity | **FORWARD** |
| 2 | `0x2a904` | unclaimed gap `[0x2a507,0x2a93a)` | — | **DEAD** (0 xrefs, 2086-fn program) |
| 3 | `0x2b656` | `FUN_0002b62c` (~100 Hz assist) | gain x polarity x `0xC6428`, mode-gated | FEEDBACK (by elimination) |
| 4 | `0x2c488` | `FUN_0002c478` (1 kHz) | `(gp-0x4f60 x gain)>>15` + delivered-cmd delta | feedback-shaped, **DEAD OUTPUT** |
| 5 | `0x36686` | `FUN_00036682` | **`(gp-0x4f60 RAW SENSOR x gain)>>15`** | **FEEDBACK, full chain to motor** |
| 6 | `0x3684a` | `FUN_00036828` | **`(gp-0x4f60 RAW SENSOR x gain)>>15`** | **FEEDBACK, feeds #5** |

**#5 verified end-to-end:** `get_function_callers(0x36682)` returns exactly `FUN_0003aa2c`;
`jarl 0x36682` @`0x3acdc`; `add r14,r10` @`0x3ace6` sums the r10 return into the aggregator accumulator;
clamped ±0x2800; stored to `gp-0x6b94` @`0x3acfa`/`0x3ad12`/`0x3ad20`; governor reads @`0x453e0`.

**Consequence:** raising this cal for "4x LKAS authority" silently raised the gain on two raw-sensor
feedback paths. The forward path was scaled coherently (clamps `0xC61B2`/`0xC61B4` 512→2048, also 4x);
the feedback path's limit is a **hardcoded ±0x200 literal** at `0x367E0/E4/EA/EE`, byte-identical to stock.

## ★★ RULED OUT as the 21 Hz carrier — MEASURED on-car 2026-07-28, not argued
- ⚠ **CORRECTION: `tp+0x73d2` (= `0xC63D2`) is `6`, NOT `14`.** Byte-read little-endian from
  `_v55_plain_image.bin` **and** stock `code.bin` (both 6; the cal is untouched by every build). The
  golden model's "final slow IIR (6/1024)" and the V52C handoff's "fc 0.94 Hz, −27 dB at 21 Hz" were
  right; the `14`/`-19.7 dB` figures here were wrong. Correct values: **α = 6/1024 → fc = 0.933 Hz →
  −27.1 dB at 21 Hz.** `FUN_00036682`'s output is also clamped to ±512 = **5% of the aggregator's
  ±10240**. A slow, small-authority trim loop.
- ⇒ **Reader #5 contributes 0.1088 × 0.0444 = 0.0048** counts of `gp-0x6b98` per count of `gp-0x4f60`
  at 21 Hz. The **measured** on-car sensor→command transfer at 21 Hz is **0.22** (V55 probe, route
  `1c`, 9 independent segments, coherence 0.69 vs 0.31 significance). So reader #5 is **2.2%** of it,
  and reverting the gain to stock removes **1.6% of loop gain = 0.14 dB**.
- ⇒ **The measured transfer is FLAT from 1 Hz to 21 Hz** (0.192 → 0.221, ~28° total phase rotation).
  A lane behind a 0.93 Hz pole cannot produce a flat response. **The `0xC646C` readers are not the
  carrier of the vibration**, and the decoupling below is a *correctness* fix, not a vibration fix.
  See [[v55-flashed-oscillation-is-internal]].
- The saturation hypothesis (4x drops the clamp threshold from `|gp-0x4f60| >= 18829` to `>= 4707`) was
  **tested against real telemetry and is DEAD**: 0 frames of 10,178 active-LKAS route-13 frames reach it
  (max 3530 = 76.8% of threshold); also 0 on the archived b9 route.

## The minimal decoupling fix (designed, verified, UNBUILT)
No LKAS-only upstream gain exists (`FUN_00028ea6` fully decompiled — everything before `0x2a1ee` is
clamp/limit LERPs, shared IIR blend coefficients, or the runtime authority ramp). So:

1. write `3564` at **`0xC6CD0`** — inside a verified `0xFF` run `0xC6CA4`-`0xC6FEF` (844 bytes), with
   **0 displacement readers AND 0 `movea ...,tp,rX` table bases landing in it**; metadata resumes `0xC6FF0`
2. revert `0xC646C` → **891**
3. retarget **only** `0x2a1ee`: `253f6c74` → `253fd07c`. **2 bytes.**
4. recompute the `0xC6FFC` CRC

Readers #2-#6 revert to stock automatically. Safety argument: it *reduces* deviation from stock everywhere
except the one site the operator intended. One in-place displacement edit — **not** a code cave.

⚠ A displacement scan **cannot** find free cal space on its own: 1723 of 2048 words in `tp+0x6000..0x6FFE`
show zero displacement-readers purely because LERP tables are read via `movea base,tp,rX` + index.

See [[accord-check-build-lineage-before-proposing-lever]].
