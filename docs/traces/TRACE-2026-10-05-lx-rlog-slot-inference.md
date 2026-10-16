# TRACE 2026-10-05 — Inferring the 2019 Accord LX's variant slot from its rlog

**Question.** A 2019 Accord LX (dongle `b308cfc5781b463d`) could not run the operator's V37 "2x" build (no assist
after ignition; stock reflash fixed it). Does its wire show which row of the variant table `@0xCD000` it sits in —
slot 2 `TVAA1` (family 10, selector 1) like the part number suggests, or slot 11 `TVCA4` (family 24, selector 7) like
the operator's car MEASURED?

**Verdict (short).** The LX rlog **cannot place the LX in a slot**, and the reason is structural: *every* signal the
stock EPS puts on the wire in MANUAL driving is either variant-independent by construction or differs between the
TVAA1 and TVCA4 rows by ≤ 2 %, far below what two different cars can resolve. The LX's manual behaviour is
**consistent with family 10 AND family 24** (and with every other TVAA/TVCA row). The LX's EPS firmware string is
**not in the rlog** (the EPS never answered the boot-time UDS query). The only measured LX-vs-operator difference
on the wire is the 0x18F column-torque excursion at full lock, which is a driver/mechanical quantity, not a
firmware readout. The slot question stays OPEN and can only be CLOSED by a live UDS read of the HW-ID at
`gp-0x6408..640C` on the LX, exactly as `reference_accord_ecu_id_variant_table.md` already says for the
operator's car.

Everything below is EVIDENCE unless marked BELIEF. Scripts: `rlog-tools/studies/lx_slot/extract_lx_slot.py`
(one pass per route → `_scratch/cache/<route>/lx_slot.npz`, ~20 s/segment) and
`rlog-tools/studies/lx_slot/lx_slot_analysis.py` (cache-only, ~1 s). Figures: `analysis-2020accord/figures/lx_slot/`.

---

## 1. What the LX rlog says about itself

Route `b308cfc5781b463d_000000a6--f3e9e379ee`, 15 segments (every other one, 0…31), 89,832 `0x18F` frames.

| item | value | method |
|---|---|---|
| openpilot | `2026.003.000`, branch `sp-honda-dev-202608`, remote `mvl-boston/openpilot` (sunnypilot lineage), git `21d6332794` | `initData` |
| wall clock | 2026-06-05 15:37 UTC | `initData.wallTimeNanos` |
| fingerprint | `HONDA_ACCORD`, `fingerprintSource = fw`, `flags 6` | `carParams` (2 copies, identical) |
| `carParams.carFw` | **TWO entries only**: `fwdRadar 0x18dab0f1 = 36802-TVA-A170`, `fwdCamera 0x18dab5f1 = 36161-TVA-A060` | `carParams.carFw` |
| EPS fw string | **ABSENT.** openpilot sent `22 F1 81` to `0x18da30f1` on bus 1 (sendcan, and the bus-129 echo); **zero** frames from `0x18daf130` on any bus in segment 0. Only the radar (`0x18daf1b0`) and camera (`0x18daf1b5`) answered. | raw `can` scan of seg 0, all buses |

⇒ The `39990-TVA-A160` the LX was said to report did **not** come from this log. (Method control: the operator's
routes `1a`, `1e`, `21` carry the full 12-ECU `carFw` list including `eps 0x18da30f1 = 39990-TVA,A160`, comma =
the modded ECU — same parser, so the parser is not the reason.) The LX's sunnypilot build fingerprinted on radar +
camera alone.

### 1.1 CAN decode summary (bus 1 = src 1 for all three EPS frames, same as the operator's car)

| frame | rate | finding |
|---|---|---|
| `0x18F` (399) | 100 Hz, DLC 7 | `STEER_STATUS` ∈ {0: 49,847 · 3: 39,298 · 4: 687}; **no 5/6/7**; `byte5[4]` never set; `STEER_CONTROL_ACTIVE` 13.4 % of frames (= `carControl.latActive` 13.4 %) |
| `0x1AB` (427) | 49.6 Hz, DLC 3 | `MOTOR_TORQUE` 10-bit: 238 distinct values, max 366, mean 2.2, nonzero 23 %; `byte0` ∈ {128, 129} (bit 0 is `MOTOR_TORQUE[8]`, so b0=129 ⇔ mt ≥ 256); **bit 2 (DTC-active) never set; `CONFIG_VALID` (b0 bit 7) always 1; `OUTPUT_DISABLED` (b2 bit 6) never set** |
| `0x14A` (330) | 100 Hz, DLC 8 | angle max 410°, rate max 512; **no `0x7FFF` sentinel**; `0x14A` rate / `0x18F` rate = 0.1246 (operator 0.1237–0.1250) |
| `0xE4` (228) | camera (src 2) and openpilot (sendcan bus 1) both present; camera req never 1; OP req 13.4 %, max \|tq\| 3226 |

**STEER_STATUS by speed (0x158 XMISSION_SPEED, km/h):**

| status | n | p5 / p50 / p95 speed | meaning |
|---|---|---|---|
| 0 | 49,847 | 7.9 / 45.8 / 122.8 | normal |
| 3 | 39,298 | 0 / 0 / 3.0 | LOW_SPEED_LOCKOUT — releases at **4.9 km/h** (18 edges, IQR 4.8–5.0); the operator's STOCK route 97 releases at **4.9 km/h** (20 edges) too |
| 4 | 687 | 6.2 / 8.7 / 10.9 | NO_TORQUE_ALERT_2, 4 runs, all with LKAS off |

The lockout threshold is the bare `tp` cell `0xC62EA` (=320, not mode-indexed), so matching 4.9 km/h on both
cars confirms *same firmware behaviour*, not slot.

---

## 2. The two candidate rows, read from the stock image (`code.bin`, LE)

Variant table `@0xCD000`, re-read this session (16 rows × 0x24, key at +0x00):

| slot | key | +0x12..15 (`gp+0x63fd` family + 3 failovers) | +0x16 `gp-0x674c` | +0x17 `gp-0x674f` | +0x19 `gp-0x674d` | +0x1A `gp-0x674e` |
|---|---|---|---|---|---|---|
| 2 | `TVAA1` | 10, 10, 11, 11 | 2 | 5 | 5 | 1 |
| 11 | `TVCA4` | 24, 25, 26, 27 | 4 | 12 | 13 | 7 |

### 2.1 Base-assist boost-curve families (the `gp+0x63fd` table `@0xCA154`, 36 pointers)

| family | record | X | Y |
|---|---|---|---|
| 10 (TVAA1 manual) | `0xD2834` | 0, 640, 2560, 5120, 7808, 10240 | **541, 639, 653, 551, 439, 439** |
| 24 (TVCA4 manual) | `0xD686C` | same X | **552, 650, 659, 554, 448, 447** |
| 26 (TVCA4 engaged) | `0xD7850` | same X | 552, 650, 659, 554, 448, 447 (byte-identical to 24) |
| 0 (blank key, for scale) | `0xCE578` | 0, 640, 2560, 5120, 8960, 12800 | 612, 787, 992, 1141, 1211, 1238 (rising) |

**Family 24 is +0.5 % … +2.05 % above family 10 at every column torque** (max 11 counts of ~650) — figure
`fig1_family_curves_10_vs_24.png`. The sibling per-family tables are identical for 10 and 24: gain scalar `@0xCA324`
→ 43 / 43, clamp `@0xC7A58` → 666 / 666, byte `@0xCA40C` → 128 / 128, rate curve `@0xCA4F4` → `[16384, 14657,
11672, 9365, 8244, 8187]` vs `[16384, 14658, 11676, 9362, 8245, 8188]` (≤ 0.04 %).

⇒ **No manual-assist measurement on a different car, tyres and rack can resolve a 2 % curve difference.** This
alone makes deliverable 3 a structural null, independent of the instrument.

### 2.2 The LKAS setpoint-limit records (`gp-0x674e` → `0xCB844`)

Selectors 0, 1, 3, 4, 6, 7 all point at a byte-identical record: `N=9, X = 3200…8320, Y = 15360 flat` — as the
brief anticipated. No discriminator there.

---

## 3. What `0x1AB MOTOR_TORQUE` actually is (and why it cannot measure assist)

Decompiled this session (`mcp__ghidra__decompile_function`, stock `code.bin`):

```
FUN_00055d80 (427 packer, 50 Hz):
    r6  = FUN_00049a5a(gp-0x6c18)          # |x|   (abs with INT_MIN guard)
    r6  = FUN_00049a78(r6, ...)            # min(,)
    427 = FUN_00049a90((r6 & 0xFFFF) * 5 >> 3, 0, 0x3FF)   # clamp to 10 bits  => wire = |gp-0x6c18| * 5/8, saturates at |x| >= 1637
FUN_00056420 (writer of gp-0x6c18, the only st.h image-wide, raw LE scan 0x56458):
    gp-0x6c18 = IIR(gp-0x4f74, alpha = tp+0x73c6 >> 4)     # (sibling: gp-0x6b54 = IIR(gp-0x6b98, tp+0x73c8 >> 10))
gp-0x4f74 writer @0x7af40 inside FUN_000757a2 (the motor-control function, 0x757a2..0x7b021):
    float LERP over an int16 table (pointers gp-0x2c8/-0x2d0/-0x2d4), scaled, then a DEAD-ZONE (|v| > r26 ? v ∓ r26 : …), trncf.sw
```

So 427 is the **rectified, dead-zoned, low-passed output of a motor-side float LERP** — not the assist command.
[BELIEF: it is a motor-torque-vs-current excess/monitor quantity; its exact meaning is OPEN.] The data agree:

- it is ~0 under all normal driving on BOTH cars (nonzero 17–28 %, p50 = 0, p99 ≤ 154 on all four routes);
- in MANUAL at < 5 m/s it switches on only above ~1,400 column counts and rises to ~100–180 near 2,750–3,500;
- it **collapses to 0 at the end stops** (LX: \|tq\| > 3,500 at \|angle\| = 408° → mt median 0), consistent with the
  assist being cut at full lock while the torsion bar still reads the driver's push.

This supersedes nothing in `honda-op-steeringtorqueeps-always-zero.md` (which already said "small, not a cut
anchor"); it adds the mechanism.

---

## 4. Manual-steering relation, LX vs operator (deliverable 3)

**Controls.** There is no operator route older than the first flash in `rlogs/` (the folder starts at counter 0x13,
FOURFRAME, 2026-07-26). But **route 97 (`75604b0a432fdc89_00000097--489d7896b3`) is the V9b STOCK flight** —
no cave, no cal edit, stock 427 packer, EPS string with the hyphen (`rlog-tools/decode/extract_r97.py` docstring,
four identity legs). It is the primary control. Secondary controls: route `2b` (V58) and `2c` (V59) — V38 cal
set + LKAS-only cells. Checked by full-image diff against `code.bin` this session: V58/V59 differ from stock
only at the FOURFRAME cave `0xC4B34…`, hook `0x55C0E`, `0x2A1F0`, `0xC6CD0`, `0xC62EA`, `0xC61B3-5`, `0xC61C0-5`,
`0xC64B4-8`, `0xC64DE`, the V38 LKAS corridor cells `0xC659A…0xC676D` (soft walls / lockstep mirrors), the
setpoint-limit records `0xE4195…0xE521D`, and CRC words. **`FUN_00055d80`, `FUN_00056420`, `FUN_000757a2`, and
every family-24 record (`0xD686C`, `0xD6914`, `0xD68C0`, `0xD6004/10/14`) are byte-stock** ⇒ valid manual controls.

**Windows.** MANUAL = `0x18F STEER_CONTROL_ACTIVE = 0` ∧ `carControl.latActive = 0` ∧ no openpilot `0xE4`
request held onto the 50 Hz `0x1AB` grid; speed = `carState.vEgo`.

**Result (`fig2_manual_1ab_vs_18f.png`, the figure that carries the verdict):**

| speed | LX n / slope ×10⁻³ [95 % CI] | r97 STOCK | r2b V58 | r2c V59 |
|---|---|---|---|---|
| 0–5 m/s | 21,698 / **12.3 [11.2, 13.5]** | 17,658 / 19.0 [18.3, 19.7] | 10,599 / 18.4 [17.5, 19.4] | 5,602 / 24.7 [23.5, 25.9] |
| 5–10 | 4,637 / 3.26 [3.09, 3.46] | 88 / — | 63 / — | 246 / 3.94 [3.33, 4.45] |
| 10–20 | 9,478 / 0.75 | 115 / — | 0 | 0 |
| 20+ | 1,048 / 0.80 | 0 | 0 | 0 |

Binned means at 0–5 m/s (mt vs \|tq\| bin centre): LX 1400→3.9, 1800→9.1, 2250→28, 2750→**134**, 3500→43 (end
stops); r97 4.7, 10.3, 22, 75, 102; r2b 2.8, 5.2, 17, 84, 160; r2c 5.3, 12, 29, 100, 173. **The LX sits inside the
spread of the operator's own three routes** on the only band where 427 is non-zero (1,400–3,000 counts). The
slope CIs do not overlap because the slope is dominated by the end-stop frames (the LX's \|tq\| reaches 10,071 at
full lock; see §5) and by a nonlinear dead-zone quantity — it is **not** an assist gain. The operator's manual
coverage above 5 m/s is near zero (LKAS engaged 64–74 % of those routes), so the higher speed bins are LX-only.

**Verdict for deliverable 3: consistent with family 10, with family 24, and with any other falling-family row
(1–8 TVAA*, 9–12 TVCA*).** What it is NOT consistent with: nothing — the instrument has no power here.
Confounds, all real: different car/rack/tyres/driver; 427 is a dead-zoned non-assist quantity; the family-10
vs family-24 difference (≤ 2 %) is below any cross-car resolution even with a perfect assist readout.

---

## 5. Other wire-visible discriminators (deliverable 4)

1. **`0x14A` rate vs `0x18F` rate scale** — 0.1246 (LX) vs 0.1237–0.1250 (operator): identical, firmware constant,
   no discriminator.
2. **Setpoint limit** — flat 15360 for every selector incl. 1 and 7 (byte-read): none, as the brief expected.
3. **Low-speed lockout release** — 4.9 km/h on both: bare cell, none.
4. **Column torque at full lock** — the one measured LX-vs-operator difference: at \|angle\| > 380° the LX reads
   \|tq\| p50 3,752 / p90 5,323 / max **10,071**; r97 stock 2,371 / 3,152 / 3,765; r2b 2,144 / 3,065 / 5,865;
   r2c 1,879 / 2,573 / 3,883. [BELIEF] this is how hard the LX driver leaned on the stops during a parking-lot
   manoeuvre (the operator's own routes vary 3.8 k–5.9 k), not a firmware scale — the `0x18F` torque packer has
   not been traced for a per-variant scale this session and is listed as OPEN below.
5. **Selector-indexed tables that DO differ between the two rows** (file
   `analysis-2020accord/figures/lx_slot/selector_table_census.txt`, raw Python LE census of 159 pointer arrays in
   `0xC0000–0xF8000`, record = one stride): comparing the record the TVAA1 row selects with the one the TVCA4
   row selects — `gp+0x63fd` 10 vs 24: **24 of 37** tables differ (mostly in the LERP Y tail, the assist curve
   among them by ≤ 2 %); `gp-0x674f` 5 vs 12: 11 of 87; `gp-0x674d` 5 vs 13: 11 of 87; `gp-0x674e` 1 vs 7:
   10 of 47; `gp-0x674c` 2 vs 4: 8 of 47. ⚠ The table→selector assignment is by array LENGTH CLASS
   (BELIEF); per-site EVIDENCE only for `0xCB844` (`gp-0x674e`), `0xC86C4`/`0xCB42C` (`gp-0x674f`, identical
   records) and `0xC7090` (`gp-0x674c`, identical: 512). `gp-0x674f` has 26 reader sites in the LKAS chain
   (`0x2E852…0x3393C`, FUN_0002e734 among them) — **these are LKAS-side**, so a discriminator would have to be an
   engaged-response measurement (LX `0xE4` command → `0x18F`/`0x14A` rate), confounded by a different
   openpilot (sunnypilot `sp-honda-dev`) with a different lateral tune. Not attempted; it would need the
   LKAS-engaged transfer function on both cars under matched commands and is the only route to a wire verdict
   short of the UDS read.

---

## 6. What would close it

- **A live UDS read of `gp-0x6408..640C`** (the 5-byte HW-ID) on the LX — the only CLOSE. Read-only, but it is
  a CAN send, so it needs the operator's explicit payload confirmation per the iron rule.
- Alternatively the LX's `39990-TVA-A160` string from a DID read on bus 1 would at least confirm the application
  part number (the LX's EPS did not answer `22 F1 81` at boot in this log — itself worth noting: the radar and
  camera did).

## 7. Files

- `rlog-tools/studies/lx_slot/extract_lx_slot.py`, `rlog-tools/studies/lx_slot/lx_slot_analysis.py`
- caches: `_scratch/cache/{b308cfc5781b463d_000000a6--f3e9e379ee, 75604b0a432fdc89_00000097--489d7896b3,
  75604b0a432fdc89_0000002b--7926e8f7e5, 75604b0a432fdc89_0000002c--eb219f392c}/lx_slot.npz`
- figures: `analysis-2020accord/figures/lx_slot/fig1_family_curves_10_vs_24.png` · **`fig2_manual_1ab_vs_18f.png`**
  · `fig3_torque_hist_and_status.png` · `fig4_1ab_onset.png` · `selector_table_census.txt`

OPEN: meaning of `gp-0x4f74` (motor-side LERP + dead-zone); the `0x18F` torque packer's scale chain for a
per-variant element; which selector indexes each of the 159 pointer arrays (only 4 pinned per-site).

---

## 8. Follow-up (same day): the LX's torque sensor vs the operator's

Orchestrator's follow-up: the only V37 cells on manual paths scale torque-sensor counts (`0xC646C` ×2) and the V40
precedent is a stationary-at-ignition fault, so compare the two cars' `0x18F` column-torque signal at rest and in
driving. Script `rlog-tools/studies/lx_slot/lx_torque_sensor.py` (cache-only, ~1 s); raw checks on one segment each.

### 8.1 Frame decode is right [EVIDENCE]
`0x18F` = bytes 0–1 BE signed `STEER_TORQUE_SENSOR` (DBC `7|16@0-`, scale −1.0 not applied here; the kit's
"raw × 1.024" scale is a firmware-side factor and applies equally to both cars), bytes 2–3 `STEER_ANGLE_RATE`, byte 4
hi-nibble `STEER_STATUS`, byte 4 bit 3 `STEER_CONTROL_ACTIVE`, byte 6 = `COUNTER[5:4]` + `CHECKSUM[3:0]`.
Honda nibble checksum (`8 − Σnibbles(addr, data)`, +3 if extended) and the 2-bit counter were recomputed on LX
segment 10 (all-stationary): **6000/6000 `0x18F` checksums pass, 0 counter skips; 2999/2999 `0x1AB` pass**;
operator r97 seg 5: 6003/6003 and 3002/3002. The LX is decoded on the same byte layout as the operator's car.

### 8.2 At rest (vEgo = 0 ≥ 3 s, `steeringPressed` = 0, LKAS off) — `fig5_rest_torque_hist.png`

| route | frames | torque mean / median / std | p1 / p99 | max \|.\| | `0x14A` rate \|max\| | `0x1AB` mt > 0 |
|---|---|---|---|---|---|---|
| LX a6 | 26,870 (8 runs) | +73.5 / +28 / 167 | −198 / +453 | 2,313 | 210 °/s | 6.5 % (max 48) |
| LX a6, **wheel-still** runs (`0x14A` rate ≤ 1 °/s, fine rate ≤ 8 all run) | 4,958 | **+204.6 / +200 / 16.3** | 191 / 245 | 254 | 0 | — |
| op r97 STOCK | 25,862 (5) | +17.1 / −8 / 78 | −72 / +101 | 1,211 | 20 | 0 % (OUTPUT_DISABLED set 45 frames) |
| op r2b V58 | 11,913 (3) | +105.5 / +128 / 61 | +10 / +156 | 1,257 | 20 | 0 % |
| op r2c V59 | 3,454 (3) | +71.8 / +74 / 32 | +38 / +256 | 373 | 2 | 0 % |

- The LX's "rest" windows include wheel handling while parked (rate up to 210 °/s, torque to 2,313) — those are
  hands-on, not sensor noise. On the **wheel-still** subset the LX sensor sits at **+200 ± 16 counts (8 distinct
  values, max 254)** — a clean zero offset with ~16-count noise. The operator's routes have no fully wheel-still run;
  their quiet-hands means are +19 (r97), +107 (r2b), +72 (r2c), i.e. the operator's own rest offset wanders over ~90
  counts route to route. [EVIDENCE for the numbers; BELIEF: the LX zero is ~+100…+180 counts above the operator's,
  which is a sensor-zero/mounting offset, 8 % of the ~2,500-count override cliff, and not a scale.]
- First 5 s of each route: LX v=0, torque mean −26, max 2,313 (hands on at start), STEER_STATUS {0,3}; r97 mean
  +81, max 101, {0,3}. `0x1AB` at rest: LX b0 = 128 only, no OUTPUT_DISABLED; mt > 0 on 6.5 % of rest frames (max
  48) — the hands-on parked frames.
- `0x14A` angle at rest: LX median −1.7°, operator −1.3…−5.6°.

### 8.3 Driving, manual, hands-on (|tq| > 50) — `fig6_driving_torque_vs_angle_rate.png`, `fig7_driving_torque_vs_latacc.png`

|tq| percentiles (p50/p90/p99): LX 5–10 m/s 667/2,324/3,208 (n 8,600) · 10–20 m/s 451/1,212/2,060 (n 17,806) ·
20+ m/s 894/2,196/2,832 (n 2,028). Operator manual-at-speed is nearly empty (r97: n 173 at 5–10, 217 at 10–20, 0
above; r2b/r2c: 0 above 10 m/s) and what exists is the hand-over moments around engagement (high torque, small
angle), so angle-matched ratios at small angles are biased and scatter 0.26–1.66.

The physically matched comparison is torque vs lateral acceleration proxy `v²·|angle|/(SR·L)` (SR 16.3, L 2.83 m),
manual, v > 3 m/s:

| a_y bin (m/s²) | LX median | r97 | r2b | r2c | LX/r97 | LX/r2b | LX/r2c |
|---|---|---|---|---|---|---|---|
| 0–0.25 | 380 (n 24,821) | 1,541 (591) | 375 (595) | 959 (611) | 0.25 [0.23, 0.27] | 1.01 [0.92, 1.10] | 0.40 [0.34, 0.44] |
| 0.25–0.5 | 977 (2,048) | 1,570 (367) | 1,483 (796) | 1,528 (162) | 0.62 [0.56, 0.67] | 0.66 [0.57, 0.71] | 0.64 [0.57, 0.72] |
| 0.5–1 | 1,249 (1,273) | 1,415 (556) | 2,299 (494) | 2,399 (279) | 0.88 [0.79, 0.93] | 0.54 [0.52, 0.60] | 0.52 [0.49, 0.57] |
| 1–1.5 | 1,888 (869) | 2,728 (362) | 2,120 (280) | 2,409 (383) | 0.69 [0.68, 0.71] | 0.89 [0.71, 1.01] | 0.78 [0.71, 0.85] |
| 1.5–2 | 1,997 (769) | — | 2,388 (84) | 2,288 (137) | — | 0.84 [0.83, 0.84] | 0.87 [0.69, 0.89] |
| 2–3 | 2,205 (1,111) | — | — | 2,516 (55) | — | — | 0.88 [0.81, 0.89] |
| 3–4 / 4–6 | 2,222 / 2,955 | — | — | — | | | |

**Verdict [EVIDENCE for the ratios, BELIEF for the reading]: NOT a different scale.** A scale error (e.g. the
×2 of `0xC646C`) would give a constant ratio across the range; the measured LX/operator ratio instead rises from
0.25–0.6 at low a_y (where the operator's "manual" frames are hand-over moments) to **0.84–0.89 at a_y ≥ 1.5 m/s²**,
where both drivers are genuinely steering, and the operator's own routes disagree with each other by as much as
they disagree with the LX (r97 vs r2b at a_y 0.5–1: 1,415 vs 2,299). The LX's torque signal is the same quantity on
the same scale within ~10–15 %, with a resting **offset** ~+200 counts (operator +19…+107). Nothing here is a
firmware readout that separates TVAA1 from TVCA4; a 2 % family difference is invisible under a 10–15 % driver/road
spread.

### 8.4 Dash-lamp / warning frames [EVIDENCE]
`0x440`/`0x450` are generic notification frames, not EPS-specific: the LX boot segment carries 8 (`d0…` at 4.77 s and
`21…` at 19.56 s, each echoed on bus 0/2); the operator's STOCK route 97 boot segment carries 182 of them with ~40
distinct codes, including the same `d0`. No EPS fault signature exists on the LX log: STEER_STATUS never 5/6/7,
`0x18F b5[4]` never set, `0x1AB` bit 2 never set, OUTPUT_DISABLED never set, no `0x7FFF` sentinel. Expected none; none.

Files added: `rlog-tools/studies/lx_slot/lx_torque_sensor.py`, `analysis-2020accord/figures/lx_slot/fig5_rest_torque_hist.png`,
`fig6_driving_torque_vs_angle_rate.png`, `fig7_driving_torque_vs_latacc.png`.
