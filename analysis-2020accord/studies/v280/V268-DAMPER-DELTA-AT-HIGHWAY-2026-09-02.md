# V268's base-assist rate-lane/boost edit at highway speed — does it explain the lane-change ring?

**Subagent `v268damper`, 2026-09-02. Reports to `main`.** Script: `v268_damper_delta_highway.py` (beside
this file; reads every number from `_v112_..._plain_image.bin` and `_v268_..._plain_image.bin` at run
time — nothing here is copied from a docstring). Consumer structure confirmed by fresh GhidraMCP
decompiles of `FUN_0003ad74`, `FUN_0003aa2c`, `FUN_00034a72` against `code.bin` (byte-identical to
V112/V268/rev 3 in these three functions — the build script asserts no code byte moves).

**Headline: V268's edit is a NO-OP for the r24 rate-damping lane at any wheel/motor rate below 84.9
deg/s, at every speed and both modes — [EVIDENCE].** A hands-light highway lane change (small angle,
low command) sits inside that dead zone. The other table V268 touches (the AMP1/AMP4 "boost" gain) does
move at low index, but it is a slow (100 Hz), amplitude-bounded (≤512-count ceiling), mean-preserving
flatten of a nonlinearity — it removes gain **modulation**, it does not remove **damping**, and its
direction argues against it being a new self-sustaining source. **V268 is not a strong candidate for the
new highway lane-change ring; the ×2 LKAS map (rev 3-specific, not in V268) remains the better-supported
suspect** per `LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md`.

---

## 1. What V268 changed, and which records are live at highway speed

`build_v268_tva.py` (BASE = V112) touches exactly two mode-indexed table families, in **all 34 modes**
(so mode selection cannot make the edit inert — that was its own design goal). Both are read from
`analysis-2020accord/builds/v108_plus/build_v268_tva.py`, addresses copied verbatim, values re-read from
the images (not the docstring):

| lane | pointer arrays | consumer | rate |
|---|---|---|---|
| **gain_B / "rate-lane surface"** | `0xCBF5C`, `0xCC044`, `0xCC12C`, `0xCC214` (mode·4 index) | `FUN_0003ad74` → `gp-0x6e38` (Y), consumed inline in `FUN_0003aa2c` as **r24** | **task 1, 1000 Hz** |
| **boost AMP1/AMP4** | `0xCA4F4`, `0xCA23C` (mode·4 index) | `FUN_00034a72` → `gp-0x6bbe` | **task 5, 100 Hz** |

Live mode: **mode 24 = manual, mode 26 = engaged** (settled on-car by V73's probe over 104,061 frames —
`reference-accord-car-is-tvca4-mode-24-26.md`; live variant = record 11 `TVCA4`, confirmed separately on
the V276 wire). It turns out not to matter here: **[EVIDENCE, byte read]** modes 24 and 26 are
byte-identical for both table families, in both V112 and V268 — Honda ships them identical and V268's
uniform 34-mode edit preserves that. Whichever mode the selector (`gp+0x63fd`) actually resolves to at
runtime, the numbers below are unchanged.

### gain_B ("rate-lane surface") — the fast lane

`FUN_0003ad74` cross-interpolates on **vehicle speed** (`gp-0x6a5e`, cross axis `0xC6010` =
`[0, 640, 3200, 6400]` ct = **0 / 9.99 / 49.95 / 99.9 km/h**), then LERPs on **motor rate**
(`gp-0x6ac0`, scale **4.7121 counts/deg-s**) inside the selected record. Record layout: `u16 npt=4`,
`X[4]`, `Y[4]`. All four speed records, mode 24/26 (byte-identical to mode 24):

| speed record | X (ct → deg/s) | V112 Y | V268 Y | delta in [0, 400 ct] = [0, 84.9 deg/s] |
|---|---|---|---|---|
| 0 km/h | 0/400/1400/3000 → 0/84.9/297.1/636.7 | 3072,3072,2322,1536 | 3072,3072,3072,3072 | **none** |
| 9.99 km/h | 0/400/1500/3000 → 0/84.9/318.3/636.7 | 2560,2560,2246,1946 | 2560,2560,2560,2560 | **none** |
| 49.95 km/h | ″ | 2303,2303,2151,1947 | 2303,2303,2303,2303 | **none** |
| **99.9 km/h (highway)** | ″ | **2150,2150,2049,1947** | **2150,2150,2150,2150** | **none** |

**[EVIDENCE]** `Y[0] == Y[1]` in every one of these eight records, in **stock/V112 already** — Honda's
own curve is flat from 0 to 400 counts (84.9 deg/s) at every speed, and only rolls off above that. V268
flattens every knot to `Y[0]`, which is a strict no-op wherever the curve was already flat. **A hands-light
lane change runs the wheel at a few to perhaps 15–20 deg/s — inside this flat segment at every speed
including highway.** So in the operating window the brief asked about (0–20 deg/s, 25–30 m/s), **V268's
gain_B edit is byte-for-byte, arithmetically inert.** The delta only appears above 84.9 deg/s — well past
a small-angle, low-command correction — where V268 raises the retained gain (2150→2049→1947 at the
99.9 km/h record collapses to a flat 2150), i.e. it **removes Honda's high-rate Kd rolloff**, which
*raises* damping authority at high rate; it never lowers it anywhere.

### boost AMP1/AMP4 — the slow lane, and the one that DOES move at low index

`FUN_00034a72` (task 5, 100 Hz — `reference_accord_task5_100hz_syscall8_rate_divider.md`, on-car
measurement, not the retracted derivation) indexes AMP1 (`0xCA4F4`) and AMP4 (`0xCA23C`) on
**`gp-0x6ba6 = |gp-0x6b9a|`**, a rectified, delay-line-filtered signal from `FUN_0003b66a` (task 1) —
**not** wheel/steering rate in deg/s (`accord-gp6ba6-is-the-boost-amplitude-index.md`). Both act as
**multiplicative Q14 gains** (16384 = ×1.0) on the "boost curve proper" (a speed/torque-keyed base
value), confirmed in the fresh decompile: the AMP1 and AMP4 outputs are multiplied together with the base
boost value, then the product is clamped to `±ceiling(0xC7970[mode])` — **flat 512 in every mode in this
image** — before being added directly into the aggregator sum alongside the LKAS lane.

| record | X | V112 Y | V268 Y | delta % |
|---|---|---|---|---|
| AMP1 `0xD6914`(m24)/`0xD78F8`(m26) | 0,512,1490,2529,3645,5120 | 16384,14658,11676,9362,8245,8188 | 15035,15035,15035,15035,8245,8188 | **−8.2, +2.6, +28.8, +60.6, 0, 0** |
| AMP4 `0xD68C0`(m24)/`0xD78A4`(m26) | 0,307,1024,1741,3072,6144 | 16384,14393,10269,8997,8177,8177 | 13926,13926,13926,13926,8177,8177 | **−15.0, −3.2, +35.6, +54.8, 0, 0** |

This is a real, non-zero change at low-to-mid index — but three things bound its relevance:

1. **It is not indexed by wheel rate.** `gp-0x6ba6` is a torsion-bar-torque-family magnitude, sourced
   from a different signal chain than the LKAS/wheel-rate loop this session is scoring. Reporting a
   "counts per deg/s" slope for it would misrepresent what it responds to — there isn't one.
2. **The flatten is constructed to preserve the MEAN at the measured operating distribution.** The build
   script's own `IDX_DIST` (V59's measured index histogram: 76.9% at 256, 18.5% at 768, 4.6% at 1536,
   0.04% at 2048 — all inside or just past the first knot) reproduces the flattened value to within 1
   count of the original curve's own index-weighted mean — confirmed independently in this script.
   **What changes is the curve's *shape* (it no longer dips as instantaneous amplitude grows), not its
   average level.** A curve whose gain falls as the signal's own rectified magnitude rises is exactly the
   parametric-pump shape (`accord-gp6ba6-is-the-boost-amplitude-index.md`, `HANDOFF-2026-08-30`); removing
   that dip is the documented intent of V268 and argues for **less** self-sustaining gain modulation on
   this lane, not more.
3. **The whole term is capped at ±512 counts** before it joins the aggregator sum (which itself clamps at
   ±10240, `gp-0x6b94`). For comparison, the LKAS lane alone contributes on the order of 900–1500 counts
   over a 20 deg/s excursion (below, §2). A saturating 512-count term can only ever be a minority
   contributor at this operating point, and saturation *reduces* its dynamic content further.

---

## 2. Size against the LKAS lane's own rate-feedback gain

Per `LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md` (subagent `loopgain`, same base — cited, not
re-derived): the LKAS PID's own `dT/d(rate)` is **45.6–73.2 counts per deg/s** at idx 12–58, identical in
V112, rev 3 and V280 (untouched by any of this arc's map/gain edits).

**V268's gain_B (fast) lane contributes exactly 0 counts/deg/s of additional rate-dependence over
0–20 deg/s, in both V112 and V268** — the segment is flat in both. **0 / 45.6–73.2 = 0 %.** Not a live
candidate for the reported symptom by this mechanism.

The boost/AMP lane has no rate-slope to compare on the same axis (§1.1), but bounding it in torque terms:
its full swing is capped at ±512 counts versus an LKAS-lane contribution of roughly 900–1500 counts over
the same 20 deg/s window (45.6–73.2 ct/deg/s × 20) — **at most ~35–55 % of the LKAS lane's swing if the
boost term swung its entire range, which it structurally cannot at this operating point** because the
edit only *raises the floor* of a curve whose mean was already there; the low-probability tail (>2048 on
`gp-0x6ba6`, 0.04 % of V59's sampled frames) is where the edit's biggest percentage deltas live (+60.6 %,
+54.8 %), and that tail sits at index 2048 of 5120–6144 — still inside the flattened, mean-preserved
region, not at the ceiling.

---

## 3. Damping or not: direction of the change

- **gain_B (r24, fast, 1 kHz):** no delta below 84.9 deg/s in the operating window that matters here.
  Above it, the edit **raises** the retained Kd-gain multiplier (Honda's rolloff removed) — if anything a
  **damping increase**, not a loss, and it is outside the reported symptom's rate range regardless.
- **boost AMP1/AMP4 (slow, 100 Hz, ZOH lag 37.6–75.2° at 21 Hz, negligible at a few-Hz lane-change
  transient):** the edit **flattens a gain dip that was itself amplitude-dependent** (a parametric-pump
  signature) while preserving its mean at the measured operating point — a move toward *less* nonlinear
  self-modulation, capped at ±512 counts absolute.

**Neither edit removes rate-proportional damping at highway speed in the low-command regime the operator
described.** The "both pumps flattened, all 34 modes" framing in `BUILD-LINEAGE`/`STATE.md` is about
killing a 2×-frequency parametric-pump risk (V58/V59's finding) — it is not a wheel-rate damper, and at
the specific speed/rate window relevant to a hands-light lane change it is measurably inert (gain_B) or
bounded and mean-preserving (boost).

## 4. What would restore V112 exactly, and whether it would help

**Cal-only, low-risk, and mechanically simple:** revert the ~900 bytes at `0xCE5BE–0xD9922` (all eight
gain_B records + all four boost records, all 34 modes) to their V112 values and recompute the one owning
CRC block. No code byte is touched by V268 in the first place (build script asserts the 164-byte cave,
both `sar` immediates, all three live cal arms, and the biquad block are all byte-stock), so this is a
pure data revert, cheap to build and to verify by full byte diff.

**But per §1–3, doing so would not be expected to touch the reported symptom** — the mechanism the
operator is describing (highway, small angle, low command) sits in exactly the range where V268's edit is
either a no-op (gain_B) or a small, mean-preserving, saturating term (boost). Reverting it removes real
value (V268/V276/rev 3's own stated goal, killing a measured 2×-frequency parametric-pump path) without a
mechanistic reason to expect it fixes the new complaint. **Recommend against reverting on this evidence
alone.** The stronger lead remains the ×2 LKAS assist map, which *is* rev-3-specific (absent from V268),
doubles openpilot's outer-loop gain at every idx with no phase change, and is speed-dependent in exactly
the way a v²-scaled lateral-accel outer loop would predict — see
`LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md` §4–5.

## Open questions / verification needed

- **Not verified here:** the actual runtime value of `gp+0x63fd` (the gain_B/boost mode selector) on this
  car during a live drive — moot for this analysis since modes 24/26 are byte-identical, but would matter
  for any future edit that breaks that symmetry.
- **Not verified here:** the base "boost curve proper" (`0xCA154[mode]`, keyed on `gp-0x6a56`/`gp-0x6a5e`)
  and the `0xCA324`/`0xCA40C` per-mode scalars that combine with AMP1/AMP4 — V268 does not touch them, so
  they were out of scope, but a full Q-format derivation of `gp-0x6bbe`'s absolute counts at a specific
  drive would need them decoded from `FUN_00034a72`'s decompile above.
- **Not attempted:** an actual rlog/CAN read of `gp-0x6ba6`'s value distribution during a real highway
  lane change on this car (V59's `IDX_DIST` is from an older drive/build and is cited, not re-measured).
  If the operator can supply a lane-change route on rev 3 with the delivered-torque tap live, checking
  where `gp-0x6ba6` actually sits during the event would directly confirm or refute the "mean-preserving,
  bounded" characterization above rather than relying on V59's distribution.
