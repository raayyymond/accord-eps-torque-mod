# Cluster 2: Mixer / Distribute / Governor — Full Touch Map

**Firmware:** 2020 Accord EPS (V850:LE:32, Ghidra image_base 0x0)
**gp = 0xFEDF8000**, **tp = 0xBF000**
**Method:** `search_instructions(operand_pattern="-0xOFF")`, program-wide, limit 200 per var.
All addresses are file-offset (== Ghidra addr). R/W classified by mnemonic (`ld.*` = READ, `st.*` = WRITE, `movea` = address-of = structural setup, not a direct R/W).

---

## 1. Per-Channel Distribute Buffers (output channels from `m_motor_cmd_distribute_clamp`)

These four are written only by `m_motor_cmd_distribute_clamp` and read by the mixer/accumulator stages.

### gp-0x62e0

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25e9a | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6 occurrences) |
| 0x25efc | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26480 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26782 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26a64 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26ad2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26dd8 | m_motor_cmd_mixer | ld.h | READ — mixer reads channel[i] |
| 0x26e74 | m_motor_cmd_mixer | ld.h | READ — mixer reads channel[i] |
| 0x26fce | m_motor_cmd_mixer | ld.h | READ — mixer reads channel[i] |
| 0x27832 | FUN_00027802 | movea | base-ptr setup (bounds validator) |
| 0x27b98 | FUN_00027b0a | movea | base-ptr setup (accumulator/LERP stage) |
| 0x27bc0 | FUN_00027b0a | movea | base-ptr setup |
| 0x27bda | FUN_00027b0a | movea | base-ptr setup |
| 0x27c62 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c82 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c9c | FUN_00027b0a | movea | base-ptr setup |
| 0x28d38 | FUN_00028d22 | movea | base-ptr setup (integrity checker) |

**Summary:** 6 writers (distribute_clamp), 3 direct reads (mixer), multiple structural setups. No unexpected writers.

---

### gp-0x62f8

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25eaa | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6) |
| 0x25f0c | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26490 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26792 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26a74 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26ae2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26d12 | m_motor_cmd_mixer | movea | base-ptr setup (mixer reads via offset) |
| 0x278b2 | FUN_00027802 | movea | base-ptr setup |
| 0x27b48 | FUN_00027b0a | movea | base-ptr setup (×6) |
| 0x27b70 | FUN_00027b0a | movea | base-ptr setup |
| 0x27be2 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c12 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c3e | FUN_00027b0a | movea | base-ptr setup |
| 0x27ca4 | FUN_00027b0a | movea | base-ptr setup |
| 0x28d58 | FUN_00028d22 | movea | base-ptr setup (integrity checker) |

**Summary:** All movea (base-pointer), actual r/w via indexed displacement within those functions. No unexpected writers.

---

### gp-0x633c

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25ec2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6) |
| 0x25f2a | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x264ac | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x267aa | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26a8c | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26afa | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26cf4 | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x27928 | FUN_00027802 | movea | base-ptr setup |
| 0x27b78 | FUN_00027b0a | movea | base-ptr setup (×5) |
| 0x27ba0 | FUN_00027b0a | movea | base-ptr setup |
| 0x27bc8 | FUN_00027b0a | movea | base-ptr setup |
| 0x27bec | FUN_00027b0a | movea | base-ptr setup |
| 0x27d60 | FUN_00027b0a | ld.h | DIRECT READ |
| 0x28d76 | FUN_00028d22 | movea | base-ptr setup (integrity checker) |

**Summary:** Written by distribute_clamp only; read directly at 0x27d60 inside FUN_00027b0a.

---

### gp-0x6230

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25ed2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6) |
| 0x25f3a–0x26b0a | m_motor_cmd_distribute_clamp | movea | base-ptr setup (5 more sites) |
| 0x26d0c | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x279a4 | FUN_00027802 | ld.hu | READ (bounds check) |
| 0x27ad4 | FUN_00027802 | ld.h | READ |
| 0x27b80–0x27cb0 | FUN_00027b0a | movea | base-ptr setup (×6) |
| 0x27d20 | FUN_00027b0a | ld.hu | READ |
| 0x27d42 | FUN_00027b0a | ld.hu | READ |
| 0x27d7e | FUN_00027b0a | ld.hu | READ |
| 0x28d98 | FUN_00028d22 | movea | base-ptr setup |

**Summary:** Written only by distribute_clamp. Multiple reads in FUN_00027802 (bounds validator) and FUN_00027b0a (accumulator). No unexpected writers.

---

## 2. Mixer Lane Slots

### gp-0x62b0  (mixer lane slot B)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x26cd0 | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x2723a | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x27df0 | FUN_00027b0a | ld.h | READ |
| 0x27e96 | FUN_00027b0a | ld.h | READ |
| 0x27f42 | FUN_00027b0a | ld.h | READ |
| 0x280f4 | FUN_00027b0a | ld.h | READ |
| 0x2817a | FUN_00027b0a | ld.h | READ |
| 0x286a4 | FUN_00027b0a | movea | base-ptr setup |
| 0x2870e | FUN_00027b0a | movea | base-ptr setup |
| 0x28de0 | FUN_00028d22 | movea | base-ptr setup |

**Summary:** Written by mixer (WRITE implied via distribute_clamp upstream), read heavily by FUN_00027b0a accumulator stage.

---

### gp-0x62c8  (mixer lane slot A)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x26cc8 | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x2721a | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x27dbc | FUN_00027b0a | ld.h | READ |
| 0x27e64 | FUN_00027b0a | ld.h | READ |
| 0x280d6 | FUN_00027b0a | ld.h | READ |
| 0x28160 | FUN_00027b0a | ld.h | READ |
| 0x281f6 | FUN_00027b0a | movea | base-ptr setup |
| 0x286b0 | FUN_00027b0a | movea | base-ptr setup |
| 0x2871a | FUN_00027b0a | movea | base-ptr setup |
| 0x28794 | FUN_00027b0a | movea | base-ptr setup |
| 0x28dfa | FUN_00028d22 | movea | base-ptr setup |

**Summary:** Same pattern as gp-0x62b0. Written by distribute_clamp/mixer pipeline upstream, multiple reads in FUN_00027b0a.

---

## 3. Mixer Accumulators

### gp-0x3d88  (accumulator A, int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x2730c | m_motor_cmd_mixer | st.w | WRITE — stores accumulator |
| 0x276d4 | m_motor_cmd_mixer | ld.w | READ — reads back accumulator |

**Summary:** Written and read exclusively within m_motor_cmd_mixer. Private accumulator. No cross-function zero risk.

---

### gp-0x3d8c  (accumulator B, int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27318 | m_motor_cmd_mixer | st.w | WRITE — stores accumulator |
| 0x2743e | m_motor_cmd_mixer | ld.w | READ — reads back accumulator |

**Summary:** Same as gp-0x3d88. Private to mixer. No cross-function zero risk.

---

## 4. Extended Accumulator Bank

### gp-0x3d70  (int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27310 | m_motor_cmd_mixer | st.w | WRITE only |

**Summary:** Write-only from mixer (write-once per cycle, no same-function read found in range). Likely telemetry/shadow output.

---

### gp-0x3d74  (int32, also movhi target)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27308 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27352 | m_motor_cmd_mixer | ld.w | READ |
| 0x379b8 | FUN_000378d6 | movhi | address-of (structural) |
| 0x75886 | FUN_000757a2 | movhi | address-of |
| 0x7b2cc | FUN_0007b022 | movhi | address-of (governor writer uses this as base!) |
| 0x7c616 | FUN_0007c4f2 | movhi | address-of |

**FLAG:** FUN_0007b022 (the governor writer) constructs an address based on movhi -0x3d74. This is how it builds the RAM pointer region for its computations. Not a direct R/W of gp-0x3d74, but the governor function uses this region as a base for float math (confirmed: gp+0x184, gp+0x17c, gp+0x128, gp+0x130 are all within this band). The float speed values that determine the governor's output live in this region.

---

### gp-0x3d78  (uint16)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x2733a | m_motor_cmd_mixer | st.w | WRITE |
| 0x2737c | m_motor_cmd_mixer | ld.hu | READ |

**Summary:** Private to mixer. Used as uint16 flag/counter.

---

### gp-0x3d90  (int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27336 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27396 | m_motor_cmd_mixer | ld.w | READ |

**Summary:** Private to mixer.

---

### gp-0x3d94  (byte)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27328 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27754 | m_motor_cmd_mixer | ld.bu | READ |

**Summary:** Private to mixer. Byte flag, read as unsigned.

---

### gp-0x3d98  (byte)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27314 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27732 | m_motor_cmd_mixer | ld.bu | READ |

**Summary:** Private to mixer. Byte flag.

---

## 5. LKAS Upstream Demand: gp-0x6b4c

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x276e2 | m_motor_cmd_mixer | ld.h | READ — reads prior value |
| 0x276f0 | m_motor_cmd_mixer | st.h | WRITE — branch A write |
| 0x27708 | m_motor_cmd_mixer | st.h | WRITE — branch B write |
| 0x27716 | m_motor_cmd_mixer | st.h | WRITE — branch C write (r10) |
| 0x285b4 | FUN_00027b0a | ld.h | READ — accumulator uses it |
| 0x28b16 | FUN_00027b0a | ld.h | READ |
| 0x28b38 | FUN_00027b0a | movea | base-ptr (tolerance check) |
| 0x3816c | FUN_00038148 | ld.h | READ — unknown consumer |
| 0x3aa3e | m_motor_torque_demand_aggregator | ld.h | READ — primary consumer; clamp +-0x2800 applied inline |

**ZEROING RISK:** The decompile of m_motor_torque_demand_aggregator shows:
```c
iVar20 = (int)*(short *)(unaff_gp + -0x6b4c) *
         (uint)((int)*(short *)(unaff_gp + -0x6b4c) + 0x2800U < 0x5001);
```
This is an inline range-clamp: if the value is outside [-0x2800, +0x2800] the multiply by 0 ZEROS the LKAS contribution at the aggregator. The range is ±10240 (±0x2800) which is very wide, so this is a safety floor rather than a normal operating boundary. Under normal conditions gp-0x6b4c stays well inside ±10240.

The three st.h writes in m_motor_cmd_mixer (0x276f0, 0x27708, 0x27716) are the only producers. FUN_00027b0a also reads it for a tolerance/error check (0x3cec diagnostic via FUN_000462e6) — it does NOT write it.

---

## 6. Aggregator Output: gp-0x6b94

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x36bf0 | FUN_00036bec | ld.h | READ — unknown (diagnostic?) |
| 0x3acec | m_motor_torque_demand_aggregator | ld.h | READ — reads prior lockstep check |
| 0x3acfa | m_motor_torque_demand_aggregator | st.h | WRITE — nominal write (clamp ±0x2800 applied) |
| 0x3ad12 | m_motor_torque_demand_aggregator | st.h | WRITE — lower clamp path (-0x2800) |
| 0x3ad20 | m_motor_torque_demand_aggregator | st.h | WRITE — upper clamp path (+0x2800) |
| 0x453e0 | m_motor_torque_governor | ld.h | READ — governor input |
| 0x4595e | FUN_0004595a | ld.h | READ |
| 0x80820 | FUN_0007ff08 | ld.h | READ |

**ZEROING RISK:** The aggregator clamps the sum to ±0x2800 (±10240) before writing gp-0x6b94. The sum includes all demand lanes including the LKAS contribution from gp-0x6b4c. Under a hard driver override, the driver torque term dominates but does NOT itself zero gp-0x6b94 — the sign conventions mean they add, not cancel (the +-0x6752 polarity flag is applied before summation). The ±0x2800 clamp is a hard ceiling, not a zero path. **The aggregator cannot collapse to zero from normal operating conditions.**

Lockstep shadow: gp-0x4ce0. Mismatch triggers FUN_0006b9fa (safety fault). This fault handler is a potential indirect zero path — if triggered, control may be surrendered.

---

## 7. Post-Governor: gp-0x6ace

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x4545a | m_motor_torque_governor | ld.h | READ — reads prior value |
| 0x454d2 | m_motor_torque_governor | st.h | WRITE — main governor output |
| 0x454e0 | m_motor_torque_governor | st.h | WRITE — alternate path |
| 0x454f4 | m_motor_torque_governor | ld.h | READ |
| 0x45528 | m_motor_torque_governor | ld.h | READ |
| 0x4559c | m_motor_torque_governor | st.h | WRITE |
| 0x455ae | m_motor_torque_governor | st.h | WRITE |
| 0x455c0 | m_motor_torque_governor | ld.h | READ |
| 0x458bc | m_post_governor_torque_comp_add | ld.h | READ — comp-add consumes |
| 0x45980 | FUN_0004595a | ld.h | READ |
| 0x45b1e | FUN_00045a20 | ld.h | READ |

**ZEROING RISK:** The governor writes gp-0x6ace as:
```
governed = clamp(gp-0x6b94, ± ((gp-0x4f64 * speed_scale_uVar17) >> 15))
then: gp-0x6ace = rate-limited version of governed
```
If `gp-0x4f64` drops to 0 AND `speed_scale_uVar17` is also small, the governor ceiling collapses to 0 and gp-0x6ace is hard-clamped to 0. This is **the primary zeroing path** for the combined assist. See Section 9 (governor) for the drop conditions.

Lockstep shadow: gp-0x4cca. Mismatch → FUN_0006b9fa.

A second override path exists: when `gp-0x67fa == 4` (mode-4 flag), if the governor's accumulated hold value `gp-0x138a` drops below the governed value in magnitude, the hold value is substituted. This can transiently zero gp-0x6ace if `gp-0x138a` has been driven to 0.

---

## 8. Shaper Input: gp-0x6acc

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x431c4 | s_motor_torque_rate_shaper | ld.h | READ — shaper reads its input |
| 0x4467a | FUN_00043e44 | ld.h | READ |
| 0x458b8 | m_post_governor_torque_comp_add | ld.h | READ |
| 0x45932 | m_post_governor_torque_comp_add | st.h | WRITE — comp_add writes shaper input |
| 0x45942 | m_post_governor_torque_comp_add | st.h | WRITE — alternate |
| 0x45b16 | FUN_00045a20 | ld.h | READ |

**Summary:** gp-0x6acc is downstream of gp-0x6ace. Written by `m_post_governor_torque_comp_add` (which reads gp-0x6ace and adds a speed-LERP correction term). If gp-0x6ace = 0, gp-0x6acc = 0 + correction_term. The correction term is a small trim, so effectively gp-0x6acc ≈ 0 when the governor collapses.

---

## 9. Runtime Governor Limit: gp-0x4f64  **[KEY ZEROING PATH]**

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x43ae4 | s_motor_torque_rate_shaper | ld.hu | READ — shaper also reads the governor limit |
| 0x4486e | FUN_00043e44 | ld.hu | READ |
| 0x453f0 | m_motor_torque_governor | ld.hu | READ — primary consumer |
| 0x6e0f2 | FUN_0006e09a | ld.hu | READ |
| 0x6e1ca | FUN_0006e140 | ld.hu | READ |
| 0x7c2d2 | FUN_0007b022 | ld.hu | READ |
| 0x7c2e2 | FUN_0007b022 | st.h | **WRITE** — update governor |
| 0x7c3a8 | FUN_0007b022 | ld.hu | READ |
| 0x7c3b4 | FUN_0007b022 | st.h | **WRITE** — update governor (second branch) |
| 0x7c470 | FUN_0007b022 | ld.hu | READ |
| 0x7c47c | FUN_0007b022 | st.h | **WRITE** — update governor (third branch) |

**FUN_0007b022 is the SOLE WRITER of gp-0x4f64.**

### How FUN_0007b022 computes the governor value

FUN_0007b022 branches on `uVar26 = gp-0x4e5a` (a mode/state byte, written by FUN_00071272 and FUN_00075718):

**Branch uVar26 == 0 (line 1081):**
```
fVar39 = (gp+0x184) * 1024.0   // speed float * 1024
// saturate to [0, 65535] (unsigned 16-bit range)
// fVar54 = MIN(gp+0x128, fVar54, gp+0x130) * 1024 (from prior calc)
gp-0x4f64 = round(fVar39)   // speed-proportional governor
```
The value written is `round(gp+0x184 * 1024)` subject to the saturation logic. **If vehicle speed (gp+0x184) is near zero, the governor limit drops toward zero.**

**Branch uVar26 == 2 (line 1139):**
Same pattern: `fVar17 = (gp+0x184) * 1024.0`, saturated, written to gp-0x4f64.

**Branch else (uVar26 != 0 and != 2, line 1197):**
Uses `fVar45 * 1024.0` (a related speed-derived float from the MIN/LERP tree at lines 1059-1080), written to gp-0x4f64.

**All three branches compute a speed-scaled value from float data in the gp+0x100–0x1b0 region.** The cal constant at `tp+0x7202 = 0xC6202 = 4762` is the nominal (highway-speed) value. At low speed (near 0 mph) gp-0x4f64 **can drop well below 4762**, and in the limit approaches 0.

### Governor drop conditions (FLAGS)

**(a) Speed → 0:** gp+0x184 is a speed float. As vehicle speed drops to zero, the governor limit computes toward 0. This is a DESIGNED feature (reduces torque authority at standstill) but creates a collapse path.

**(b) uVar26 / mode byte gp-0x4e5a:** Written by FUN_00071272 (0x712aa st.b) and FUN_00075718 (0x7577e st.b). If gp-0x4e5a changes value abruptly (e.g., mode transition during an override), the three branches compute slightly different values. Normally the result is continuous, but if the mode byte changes on the same cycle as a low-speed condition, the branch-3 path may compute a lower intermediate value.

**(c) Lockstep shadow gp-0x448a:** FUN_0007b022 checks `gp-0x4f64 == gp-0x448a` before writing both atomically. Mismatch → calls FUN_0006b9ee (fault handler), **without writing gp-0x4f64**. If a fault fires here, gp-0x4f64 is left stale (not zeroed, but also not updated). Stale at a low-speed value = sustained suppress.

---

## 10. Governor Lockstep Shadow: gp-0x448a

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x7c2da | FUN_0007b022 | ld.hu | READ — lockstep check |
| 0x7c2e6 | FUN_0007b022 | st.h | WRITE — written with gp-0x4f64 atomically |
| 0x7c2ec | FUN_0007b022 | movea | address-of |
| 0x7c3a0 | FUN_0007b022 | ld.hu | READ — branch 2 check |
| 0x7c3b8 | FUN_0007b022 | st.h | WRITE — branch 2 |
| 0x7c3be | FUN_0007b022 | movea | address-of |
| 0x7c468 | FUN_0007b022 | ld.hu | READ — branch 3 check |
| 0x7c480 | FUN_0007b022 | st.h | WRITE — branch 3 |
| 0x7c486 | FUN_0007b022 | movea | address-of |

**Summary:** gp-0x448a is exclusively maintained by FUN_0007b022, in lockstep with gp-0x4f64. No other function touches it. When gp-0x4f64 and gp-0x448a diverge (e.g., via a single-event upset or memory bit error), FUN_0006b9ee is called instead of updating — so the fault itself does NOT zero the governor, it freezes it.

---

## 11. Mode-5 Gate Lane: gp-0x6afe

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x42ad6 | FUN_00042ac6 | st.h | WRITE — sole writer |
| 0x43ae0 | s_motor_torque_rate_shaper | ld.h | READ — shaper uses as gate input |

**FUN_00042ac6 is a simple clamp wrapper:**
```c
void FUN_00042ac6(int param_1) {
  if (param_1 + 0x2800 > 0x4FFF) param_1 = 0x7fff;  // clamp to 32767
  gp-0x6afe = (short)param_1;
}
```
Called from FUN_00027b0a (the accumulator/LERP stage) as its final output step (`FUN_00042adc(iVar10)` at the end of FUN_00027b0a — this is the same address). gp-0x6afe feeds the rate shaper as a lane-5 demand value. **No zero path here** — the clamp saturates at 32767 at the high end, but the normal input is the accumulator output which can legitimately be 0 when all channels report zero demand.

---

## 12. Summary: Zeroing / Collapse Mechanisms

### MECHANISM A — Governor limit drop (gp-0x4f64 → 0, speed-driven)

**Path:** FUN_0007b022 computes gp-0x4f64 = round(gp+0x184 * 1024). At low / zero vehicle speed, gp+0x184 → 0, so gp-0x4f64 → 0. m_motor_torque_governor then clamps gp-0x6b94 to ±0, writing gp-0x6ace = 0. m_post_governor_torque_comp_add writes gp-0x6acc ≈ 0 (plus small correction). s_motor_torque_rate_shaper sees 0 input. **Full assist suppression.**

**Relevance to hard-override transient:** During a hard override at low speed (or if the speed signal transiently drops — e.g., a CAN dropout or a speed near 0 during initial engagement), the governor can legitimately suppress to near-zero, killing all assist including base power-steering torque delivered through this chain.

**Severity:** HIGH. This is the primary mechanism. The nominal governor at highway speed is 4762; at parking-lot speeds it can be much lower; at very low speed it approaches 0.

### MECHANISM B — Aggregator lockstep fault (gp-0x6b94 shadow mismatch)

**Path:** If gp-0x6b94 ≠ gp-0x4ce0 at entry to m_motor_torque_demand_aggregator (caused by, e.g., a prior FUN_0006b9fa that left the shadow stale), the function calls FUN_0006b9fa without updating gp-0x6b94. The aggregator output is frozen, not zeroed. However, if the fault response itself writes 0 to gp-0x6b94, the downstream chain collapses. **This is not confirmed from available decompile — FUN_0006b9fa behavior is unverified.**

**Severity:** MEDIUM / UNVERIFIED. Need to decompile FUN_0006b9fa to confirm whether it zeros or freezes the output variable.

### MECHANISM C — Governor hold-value collapse (gp-0x138a)

**Path:** Inside m_motor_torque_governor, when `gp-0x67fa == 4`, the hold accumulator `gp-0x138a` is substituted for the governed output if its magnitude is less than the governed value. gp-0x138a initializes to 0 (when `gp-0x5000 == 0`, a first-run flag). On first engage, or after a disengagement, gp-0x138a = 0 and the rate-limiter substitutes 0 for the commanded value, producing a soft ramp from 0 rather than a hard step. **This is the designed ramp-up behavior, not a fault.**

**Severity for "hard override" transient:** The rate-limiter accumulator in the governor means that after an override clears, the output ramps back up from its held value. If the override was sustained long enough for gp-0x138a to decay toward the driver torque direction, disengage causes a momentary near-zero before ramping.

### MECHANISM D — Deadband / slew-limiter in rate shaper (from prior Civic analysis)

**Note:** The Civic firmware has a confirmed deadband/slew mechanism in s_motor_torque_rate_shaper (tp+0x71D6 step size). Whether the Accord firmware has an analogous structure needs verification — the Accord shaper function `s_motor_torque_rate_shaper` IS present and reads gp-0x4f64 and gp-0x6afe — but the specific deadband and slew constants need a separate decompile.

### MECHANISM E — gp-0x6b4c range-zero at aggregator

**Path:** m_motor_torque_demand_aggregator zeros the LKAS contribution if gp-0x6b4c is outside ±0x2800. Under normal LKAS operation gp-0x6b4c stays within ±10240 so this does not fire. However, if the mixer writes an out-of-range value (e.g., due to a stuck distribute-clamp or an upstream saturation), the LKAS lane is silently dropped from the sum without a DTC.

**Severity:** LOW under normal conditions. Would require an upstream fault in distribute_clamp.

---

## 13. Unexpected Writers / Anomalies

| Variable | Unexpected Writer | Notes |
|----------|-------------------|-------|
| gp-0x4f64 | FUN_0007b022 ONLY | This is the expected pattern, but the function is very large (50k+ char decompile) and contains 3 write paths, all speed-derived. No other function touches gp-0x4f64 — confirmed program-wide. |
| gp-0x3d74 | FUN_0007b022 uses movhi base | The governor writer uses the gp+0x184 speed region (near gp+0x3d74 as a base pointer) — not a direct write, but confirms the governor's float inputs come from this memory band. |
| gp-0x448a | FUN_0007b022 ONLY | Lockstep shadow maintained exclusively by governor writer. Clean. |
| gp-0x6b4c | FUN_00038148 reads | FUN_00038148 at 0x3816c reads gp-0x6b4c — unknown role. Not a writer. Needs decompile to classify. |
| gp-0x6b94 | FUN_0007ff08 reads | FUN_0007ff08 at 0x80820 reads aggregator output — unknown role. Likely telemetry/monitoring. Not a writer. |

---

## 14. New gp-offsets Discovered During This Trace

| Variable | Address(es) | Discovered In | Role |
|----------|-------------|---------------|------|
| gp-0x4ce0 | (aggregator shadow) | m_motor_torque_demand_aggregator decompile | Lockstep shadow of gp-0x6b94 |
| gp-0x4cca | (governor shadow) | m_motor_torque_governor decompile | Lockstep shadow of gp-0x6ace |
| gp+0x184 | FUN_0007b022 decompile | Speed float used to compute governor limit | Critical — see Section 9 |
| gp-0x67fa | m_motor_torque_governor decompile | Mode flag: ==4 activates hold/ramp path | Affects ramp-up after override |
| gp-0x5000 | m_motor_torque_governor decompile | First-run flag for gp-0x138a init | |
| gp-0x138a | m_motor_torque_governor decompile | Hold accumulator for rate-limiting | Can be 0 on first engage |
| gp-0x4e5a | FUN_0007b022 / FUN_00071272 | Branch selector for governor computation | Written by FUN_00071272, FUN_00075718 |

---

## 15. Recommended Next Steps

1. **Decompile FUN_0006b9fa** — confirm whether the safety fault handler writes 0 to gp-0x6b94 / gp-0x6ace, or only freezes them. This determines severity of Mechanism B.
2. **Decompile FUN_00038148** — classify unknown reader of gp-0x6b4c.
3. **Decompile s_motor_torque_rate_shaper** — check for Civic-style deadband/slew-limiter and confirm whether gp-0x6afe feeds a separate zeroing path.
4. **Trace gp+0x184** — confirm it is the vehicle speed CAN signal and how it is populated; verify the speed-to-governor-limit mapping.
5. **Decompile FUN_0007b022 branch entrance** — identify what gp-0x4e5a == 0/2/other maps to in the state machine.
