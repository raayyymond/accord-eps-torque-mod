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

## ✅ 2026-08-07 — RE-ENUMERATED, TWO READERS RECLASSIFIED, AND THE DECOUPLE IS OFF THE CAR

Three independent methods agree exactly (Ghidra `search_instructions`, a fresh raw Python LE scan of both
encodings, fresh decompiles): **6 readers, 0 stores, 0 disp23 hits, 0 LE32-pointer hits.** Every site is
`(x * cal) >> 0xf`; `3564 = 4 × 891` exactly.
- **#3 (`0x2b656`, `FUN_0002b62c`) RECLASSIFIED — it has NO TORQUE PATH.** Its output `gp-0x6af0` reaches
  only a private 2-function mode-flag debounce loop (`gp-0x677d` has exactly **2** static refs
  image-wide) plus a UDS packer with **0** static callers. The "FEEDBACK (by elimination)" label above is
  wrong.
- **#4 (`0x2c488`) output `gp-0x6b10` has 3 refs, ALL `st.h`, ZERO loads** — proven dead, confirming the
  "DEAD OUTPUT" call above.
- ⇒ **#5 is the ONLY reader that reaches the motor**, and the **α = 6** correction above is re-confirmed
  from a third source: corner **≈ 0.93 Hz, ≈ −26.6 dB at 21 Hz** ⇒ it **cannot drive a 21–27 Hz mode.**
  The "6 vs 14" discrepancy is settled in favour of **6**.
- ⚠ **The ±0x200 pre-filter screen, re-run on a V76-lineage log for the first time** (route 66, V80):
  `|bar|` engaged p50 174 · p90 1,424 · p99 3,346 · p99.9 3,712 · **max 3,849**; `|bar| ≥ 4707` fired
  **0 / 89,997**. **It did not bind** — but the margin is only **22%** and the CAN count scale is not
  proven identical to `gp-0x4f60`'s, so this is "did not fire on this drive", not "cannot fire".
- 🛑 **THE V57 DECOUPLE IS OFF THE CAR since the V38 rebase**: V76/V78/V79/V80 read `0x2A1F0` disp
  `0x746C` (shared `0xC646C` = **3564**) where V62/V68/V74/V75 read `0x7CD0`. A real, uncosted headroom
  regression that nobody signed off on — **and not the 27 Hz driver.** V81 removes it for free by being
  cut from the V75 base. ✅ `0xC6CD0` = `0xFFFF` on V76/V78/V80 is provably inert (0 instructions read
  `tp+0x7cd0` anywhere). See [[accord-v38-rebase-silently-reverted-three-levers]].

See [[accord-check-build-lineage-before-proposing-lever]].
