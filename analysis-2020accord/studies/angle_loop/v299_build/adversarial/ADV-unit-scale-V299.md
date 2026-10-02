# ADVERSARY (unit / scale chain), V299 rev 2 built image: verdict PASS_WITH_DEFECTS

**Status: analysis only.** Nothing was flashed or sent on CAN. No git write in either kit repo, and no Ghidra program was
saved. Two read-only `git show` calls were made on the operator's StarPilot checkout to read the DBC at `2712e1336`.
FAIL criteria were written first: `FAIL-CRITERIA-unit-scale-V299.md`. Classifier interruptions: 0.

**Image attacked:** `accord-firmwares/analysis-2020accord/_v299_V299-ANGLELOOP...A16B_plain_image.bin`, which I re-hashed
myself as sha256 `30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08`. The cave 0xC4C00..0xC4D04 hashes to
`e22193b9...`. The image differs from V298 `177abf04` in exactly 67 bytes, in nine runs: 0x1310D, 0xC4C64-65, seven runs
inside 0xC4C6A..0xC4CAB, and the trailer 0xC4FFC-FF. Script: `_scratch/adv_us_diff.py`, 0.08 s.

**Method.**
- I decompiled with Ghidra on the stock analysed program `code.bin`.
- Every Honda function I relied on is byte-identical between stock and V299. A Python check covered
  `FUN_00055c42`, `FUN_000557c8`, `FUN_0007f3f8`, `FUN_0003e6d8`, `FUN_000217c4` and `FUN_000218be`. A full
  stock-to-V299 diff over [0x13000, 0xC5000) listed every edit (`_scratch/adv_us_diffpid.py`, under 1 s).
- I read the V299 cave and the edited PID tail as a dry-run disassembly on the V299 bytes (program
  `V299_ADVARITH_DISASM_ONLY.bin`, whose bytes at 0xC4C60 I checked = V299).
- On-car checks used the route-79 caches. Every script ran in under 1 s.

---

## 1. Driver torque: raw `gp-0x4f68` against wire 0x18F, and the 1229 freeze. EVIDENCE

```python
# FUN_0007f3f8 (writer, st.h @0x7FECA, the only store image-wide: search_instructions 41 hits, 1 st.h)
u = s16(gp_4f60)                       # sensor-B column torque (every path loads uVar7 from gp-0x4f60)
gp_4f68 = min(abs(u), 0xFFFF)          # |raw|, saturating
# FUN_00055c42 (CAN 399 = 0x18F packer; checksum call FUN_00057b24(gp-0x1420, 7, 399))
wire_i16 = -((s16(gp_4f60) * 125) >> 7)          # FUN_000218be: byteswap16 store, no other scaling
# opendbc (fork 2712e1336): STEER_TORQUE_SENSOR 7|16@0- factor -1 ; steeringPressed = |steeringTorque| > 1200
#   (HONDA_ACCORD is not in STEER_THRESHOLD's overrides -> default 1200)
# cave 0xC4C5E ld.hu -0x4f68[gp],r8 ; 0xC4C62 movea 0x4cd(=1229) ; cmp ; 0xC4C68 bh FRZ   (unsigned >)
```

- **Direction.** wire = raw x 125/128, so raw = wire x 1.024. Raw 1229 is wire -(1229*125 >> 7) = -1200, which is not
  pressed. Raw 1230 is wire -1201, which is pressed. **"Raw 1229 = wire 1200" is correct in direction and value.**
  The brief's alternative reading ("1200 raw x 125/128") is the wrong direction: 1200 x 125/128 = 1171.9.
- **Same source.** The freeze reads |gp-0x4f60|, and Honda's `steeringPressed` reads the frame built from the same
  `gp-0x4f60`, so the two thresholds are on one signal. (Timing differs: the 0x18F payload is one frame stale. That is
  not a unit question.)
- **DEFECT U3, low (EVIDENCE, arithmetic).** `sar` floors toward -inf, so the mapping is asymmetric by one LSB. Raw -1229
  gives wire +1201: Honda reports pressed, but the cave does not freeze (|raw| = 1229 is not > 1229). The freeze set is
  a strict subset of the pressed set, missing that one raw value on one side. Behaviourally nil.

## 2. theta (`gp-0x6a00`) is 0.1 deg of steering-wheel angle per count. EVIDENCE (image and physics)

- The frame chain from the image:
  - `FUN_00040a50` stores `gp-0x69ec = -gp-0x6a00` in mode 3.
  - `FUN_00055a98`, the 0x14A builder, calls `FUN_00057b24(gp-0x1518, 8, 0x14a)`.
  - `FUN_000218fe` writes `byteswap16(gp-0x69ec)` to `gp-0x1518`, which is bytes 0-1 of the 0x14A frame.
  - The kit decodes 0x14A bytes 0-1 as i16be x -0.1 deg, which gives +0.1 deg per count of `gp-0x6a00`.
- **An independent physical check** (`_scratch/adv_us_theta.py`, 0.05 s, route 79): the steer ratio from yaw rate,
  where yaw = rear wheel-speed difference / 1.60 m, wheelbase 2.83 m:

  | statistic | steer ratio |
  |---|---|
  | median | 17.2 |
  | least-squares fit | 15.3 |
  | p25-p75 | 14.8-20.5 |
  | sign agreement | 99.0 % |

  This matches the Accord's ~16. A 1/16-deg-per-count unit would read 10.8.
- **The setpoint shares theta's unit and sign on-car.** `_scratch/adv_us_sp.py`, 0.04 s, V298 wire cache
  `r79_a1f5d2_al.npz`, 28,867 engaged hands-off frames: wheel angle regressed on -cmd/10 gives slope **1.005**,
  correlation **0.9987**, sign agreement 99.7 %. So 16|theta| in the bound and E = 16(theta_sp - theta) are on one
  0.1-deg scale.
- The cave reads theta at 0xC4C6A `ld.h -0x6a00[gp],r9`, signed, the same encoding as the 14 Honda readers.

## 3. The v-word (`gp-0x6a5e`) is 230.625 counts per m/s. The spec's 230.4 is 0.1 % off. EVIDENCE

```python
# FUN_00053216: wheel_i = (raw15 * 0x29) >> 6        # 41/64 ; FUN_00021646 = 15-bit Motorola field at start bit 8
#   (byte1 bit0 | byte2 | byte3>>2) = WHEEL_SPEEDS layout, 0.01 km/h per LSB   [field layout: EVIDENCE; frame ID: BELIEF]
# FUN_000522fe: 5th source = CAN16 * 41 >> 6 ; fallback = (byte km/h) << 6     # independent confirmation: 64 per km/h
# FUN_00041eec: gp-0x6a5e = vote/average of the valid wheels, rate-limited, clamped <= 0x7D00; st.h @0x42342 (sole writer)
```

- 0.01 km/h x 41/64 gives **64.0625 counts per km/h = 230.625 counts per m/s**.
- The two gates: 1382 is **5.99 m/s** and 2880 is **12.49 m/s**. The spec's "6.0 / 12.5 m/s" stands.
- Cross-check: the GB-P row knots 714 / 1843 / 2304 / 2707 / 4032 / 6198 convert to 3.10 / 7.99 / 9.99 / 11.74 /
  17.48 / 26.87 m/s, which are the fork's clip breakpoints.
- The cave reads the v-word with `ld.hu` and compares it with `bh` (unsigned), which is correct for an unsigned speed.
  The writer clamps it to <= 0x7D00, so it never reaches the 0x7FFF sentinel.

## 4. The S unit of the bound, carried through to T, the tap LSB and % of rail. EVIDENCE

```python
# PID (stock FUN_00028ea6 structure; V299 bytes 0x29D7A..0x29DC6 dry-run; tp = 0xBF000)
r9  = Ep >> 5                                      # 0x29D7C (DB tp+0x72e4 = 0 on V298/V299)
inc = (r9 * Ki) >> 3                               # Ki = 0xC63E6 = 40 ; 0x29DA8 mul, 0x29DB2 sar 3
I3  = clamp((I8 >> 3) + inc, +-(ICL << 10) >> 3)   # ICL = 0xC61BA = 8192 -> +-1048576 ; 0x29DAC..0x29DC2
I8  = I3 << 3                                      # st.w gp-0x6dd0
S_I = I3 >> 7  == I8 >> 10                         # the I term in the PID sum (the golden's 0x29F18 sar 7)
# cave 0xC4CAC ld.w -0x6dd0[gp] ; 0xC4CB0 sar 0xa   -> compares exactly S_I (previous tick's)
sum = S_I + P + D ; out = clamp(((A*F & 0xFFFF) >> 8) * sum >> 8, +-15360)   # A = F = 255 hands-off: x254/256 ; OCL 0xC61BE
y   = output lag (a 992, b 507, two-sample sum >> 5)                          # DC 0.990
T   = clamp((y*ramp >> 15) * pol * 5346 >> 15, +-3072)                        # 0x2A1EE ld.h 0x7cd0[tp] (repointed; 0xC6CD0 = 5346)
tap = sign << 9 | min(|T| >> 3, 511)                                          # 0x55DF0..0x55E12 (CAN 427 field)
```

**The unit is consistent.** The bound, 4096 / 6144 / ICL 8192, and the I term all sit in **S = PID-sum counts**.
- The caps are below ICL, so the cap is live, not inert.
- The overshoot is one tick: the bound is checked against the previous tick's I. That is <= 28 S (~4.5 T) at the
  17-deg clip, with G <= 2188, read from the GB-P rows at 0xC4CDA.

Integer march from cold state (`_scratch/adv_us_rail.py`, 0.01 s), I term only, hands-off:

| S (bound) | T (delivered) | % of 2461 | % of 2482 | tap LSB | spec |
|---|---|---|---|---|---|
| 1250 (B) | 199 | 8.1 % | 8.0 % | 24 | — |
| 4096 | 656 | 26.7 % | 26.4 % | 82 | — |
| **6144** | **984** | **40.0 %** | 39.6 % | 123 | "~983 T, 40 % rail" — agrees |
| 8192 (ICL) | 1312 | 53.3 % | 52.9 % | 164 | — |

The fade/taper record 0xE54FC (axis = |raw| >> 5, byte `gp-0x682f`) reproduces the spec's figures:

| raw torque | spec | image (relative to the hands-off 254/256) |
|---|---|---|
| 600 | x 0.99 | 0.98 (0.99 relative) |
| 1200 | x 0.86 | 0.862 |
| 1536 | x 0.70 | 0.695 |
| >= 2048 | x 0.30 | 0.297 |

**BELIEF, not checked further.** The second taper factor A (0xE55A4, axis `gp-0x6830`, the rate of driver torque) is
255 hands-off and falls to 205. It can only **lower** T. The spec's S-to-T figures ignore it, which errs in the safe
direction.

### DEFECT U1, low (EVIDENCE, arithmetic). The spec's derivation of the rail is false

Spec §2.2, F7 reads "2461 T = SCL 15360 x 5346/32768". That product is **2505.9**. The 2461 figure is the
**P-clamp-bound** rail: P = 15360, I = D = 0, then the x254/256 taper (15240), then the floored output lag.

### DEFECT U2, low (EVIDENCE). The true ceiling is above 2461

The spec says "the lane is <= 2461 T" and the bar normaliser uses 2461. But the ceiling is the **OCL bound**:
out = 15360 gives **T = 2481 (pol +1) / -2482 (pol -1), tap 310**. That ceiling is reachable whenever
P + I + D > ~15480 S, which the angle loop can produce: P up to 15360 plus I up to 8192.
- The on-car memory "the tap reads 310 at the rail" agrees with 2481/2482, not 2461 (2461 >> 3 = 307).
- Consequences are cosmetic: the bar can reach 1.008 before the clip, and every "% of rail" on the page reads
  <= 0.8 % high. F9's LSB thresholds (250 / 230) are unaffected.

## 5. Cross-lens finding, reported as asked and not fixed

**DEFECT X1, low (EVIDENCE for the DBC; BELIEF for its consequence).** Spec §2.1 says 427 (0x1AB) "has no CHECKSUM"
in the DBC. That is wrong.
- The fork at `2712e1336` (read-only `git show`) declares `SG_ CHECKSUM : 19|4@0+` on `BO_ 427` in both
  `_honda_common.dbc` and the generated `honda_accord_2017_can_ext_generated.dbc`.
- The opendbc parser checks that checksum unless `ignore_checksum` is set (`can/parser.py`). The working-tree fork code
  sets only `ignore_counter`.
- The consequence is probably benign. The fork lists the frame with frequency `nan` (optional, per its own comment
  "never part of canValid"), so a bad-checksum frame is dropped. Route 79 was 100 % valid under the same Honda checksum.
- The fork-safety lens should confirm that an optional message's checksum failure cannot touch canValid. The spec's
  statement is factually wrong either way.

## 6. Verdict: **PASS_WITH_DEFECTS**

None of the five FAIL criteria in my pre-registration holds.

| quantity | what the bytes give | spec |
|---|---|---|
| freeze direction | raw = wire x 1.024 | agrees |
| raw 1229 | wire 1200 | agrees |
| theta unit | 0.1 deg per count, confirmed physically | agrees |
| v-word | 230.625 per m/s (gates 5.99 / 12.49 m/s) | 230.4, agrees within 0.1 % |
| bound and cap unit | S = I8 >> 10, the I term in the sum | agrees |
| 6144 S | 984 T, 40 % of rail | 983 T, 40 % |

The defects are U1 and U2 (rail text and value, 0.8 %), U3 (a one-LSB asymmetry at raw -1229), and X1 (a DBC
checksum statement). Each is page or documentation level. None changes the image or what the loop does.
