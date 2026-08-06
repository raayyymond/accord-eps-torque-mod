# Feasibility: 8× LKAS gain on the 2020 Accord EPS (`39990-TVA-A160`)

**Status: analysis only. No build, flash, or CAN/UDS action was taken to produce this document.**
Written 2026-08-06, current as of the V74 build (built, verified, unflashed; V73 is on the car). Car
config row 11 `TVCA4`, mode 24 disengaged / 26 engaged (see `docs/BUILD-LINEAGE.md` RULE 7). This is a
feasibility report for a **future session** to act on — it recommends a staged approach, not a build.

**Evidence legend:** **[EVIDENCE]** = read/verified this session (Ghidra decompile, `read_memory` on the
live V74 program, or a from-scratch Python byte diff). **[prior EVIDENCE]** = established in an earlier
session, cited from `docs/BUILD-LINEAGE.md` / `docs/STATE.md` / `analysis-2020accord/eps_lkas_chain_model.py`,
not independently re-derived here. **[BELIEF]** = inference, flagged as such. Where a fact was relayed by
a teammate from their own Ghidra work or from route-5d telemetry I did not personally re-run, it is
marked accordingly.

---

## TL;DR

- **There is zero upstream headroom.** openpilot's `STEER_MAX` (4096) already saturates the firmware's
  setpoint clamp exactly (`4096 × 4 = 16384 = 0x4000`). All additional authority must come from firmware
  gain, applied downstream of a 4096-capped, already-rate-limited input.
- **V74 is already at 4× stock** (`0xC6CD0 = 3564` vs stock `891`) — this is the most heavily
  flight-tested stage in the kit's history, carried unchanged from V38 through V74.
- **A nominal 8× is a 2-byte, cal-only edit** and does not by itself approach any of the kit's documented
  brick classes.
- **It will not deliver a real 8× at the wheel during fast steering.** The motor-rate **adaptive
  governor cap** — confirmed byte-stock, untouched by any build V37→V74 — already partially clips
  today's 4× during moderately fast corrections and will clip harder and sooner at 8×, because it
  responds to *measured motor speed*, not to command gain.
- **A second, independent problem sits upstream, on the openpilot side**: the command's own slew
  ceiling in firmware-lane counts scales *with* the firmware gain. At V74's 4× it already crosses
  *inside* openpilot's 100 ms actuator delay — a documented "classic limit-cycle recipe." At 8× the
  time-to-full-torque halves again, to ~21 ms, tightening that mechanism further. **This is the
  strongest argument against 8× as specified**, independent of any firmware clamp.
- **The loop is not pristine today.** V74's own pre-registered abort probe measured 5×f0 relay-generation
  prominence at 2.227 against a 3.0 abort threshold, and grind #1 confirmed active at 2.72× over its
  control floor. Any 8× proposal starts from an already-marginal baseline, not a clean one.

---

## Part 1 — the V37 → V74 changelog

**Method:** whole-image byte diff, `[0x13000,0x100000)`, of
`../accord-firmwares/analysis-2020accord/_v37_plain_image.bin` vs
`_v74_engagedcols_x0_12_addonly_plain_image.bin` — **[EVIDENCE]** SHA256 of the V74 file
(`8ae58cb8f4...`) matches `docs/STATE.md`'s recorded hash for the real, flashable V74; this is not a
superseded re-cut. 431 differing bytes / 186 runs; 56 bytes are CRC-block trailers (mechanical, not
functional). **375 functional bytes, fully attributed below.**

This is a **net** diff over the whole V38→V74 arc — an address a later build rewrote (e.g. V72's
now-known-inert mode-10/11 damper edits) does not show up as a separate step. "Carried since Vnn" is
`docs/BUILD-LINEAGE.md`'s own record, not re-derived from the diff alone.

Two of the cells below were independently byte-verified by a teammate against the flown image and match
exactly: **`0xC6CD0 = 3564`** (4.00× stock 891) and **`0xC646C = 891`** (reverted to stock for the
feedback readers by V57's decouple); V37 reads `0xC6CD0 = 0xFFFF` (cell did not exist yet) and
`0xC646C = 1782`.

### 1. Code edits (7 bytes, 3 sites) — MODE-PROOF (not table-indexed)

| addr | V37 | V74 | lever | in force? |
|---|---|---|---|---|
| `0x02A1F0-1` | `6c74` | `d07c` | V57's decouple: redirects the LKAS-forward reader of the shared Q15 gain onto private cal `0xC6CD0`, leaving `0xC646C` for the 4 feedback readers only | ✅ in force |
| `0x0454FE` | `ba` | `b5` | V42's ratchet fix (single condition-code-nibble edit), restored by V71 after V53's rebase silently dropped it (RULE 3) | present in the image, but **structurally inert on current drives** — `gp-0x67fa` reads a near-constant 5 on route 5d (state 4 appears once in ~101,117 frames, teammate relay), so the state-4 substitution this fixes essentially never arms |
| `0x055C0E-11` | `2436e8ea` | `86ff26ef` | telemetry-probe hook (`jarl` target into the cave), moved as the probe payload evolved V49p→V74 | read-only telemetry, not torque-path |

### 2. Cave payload (68 bytes, `0xC4B34-0xC4B77`) — V37 all-`FF` (unused) → V74 live probe body

**[EVIDENCE, Ghidra decompile of the cave in the live V74 program]** decodes as `ld.h -0x6bd0 → cmp r0 →
be → movea 0x10 → ld.bu -0x67fa → andi 0xf → or → shl 3 →` merge → single `st.b` to the CAN `0x14A`
staging byte. Read-only (`gp-0x67fa` state + `gp-0x6bd0` damper-output liveness), no write path into any
torque-relevant cell. Not part of the gain question.

### 3. Cal cluster, `0xC4000-0xC6FFF` (≈35 bytes) — the reach/clamp/EME lineage

| addr | V37 | V74 | lever | mode-proof? | in force on TVCA4? |
|---|---|---|---|---|---|
| `0xC407E-F` | 511 | 850 | friction floor ×1.5 (V73/V74) | ✅ RULE 7 mode-proof list | ✅ yes |
| `0xC61B3, 0xC61B5` (high bytes) | 1024 | 2048 | `arb_output_clamp` / `pack_output_clamp` doubling, V38, lockstep with the V38 gain raise | ✅ single-reader, code-literal-adjacent | ✅ yes |
| `0xC62EA-B` | 320 | 0 | `speed_window_lo` → 0 (V53, min-steer-speed removed) | ✅ | ✅ yes — **the old <5 km/h LKAS lockout no longer exists on this build** |
| `0xC63A1` | `04` | `08` | unresolved 1-byte companion of the clamp-doubling family (same `04→08` shape) | not independently confirmed this session | **[BELIEF]** only |
| `0xC646C-D` | 1782 | 891 | `shared_sensor_scale` reverted to stock for the 4 *feedback* readers only (V57 decouple; forward reader moved to `0xC6CD0`, still 4×) | ✅ | ✅ yes |
| `0xC659A/9E/AE/B2/C6/CA/CE` + `0xC674F/51/5B/5D/69/6B/6D` (14B) | int+float mirror @4096 | @5120 | soft-EME corridor/boost widening (V38); **[prior EVIDENCE]** the `FUN_00043e44` DTC-0xF00049 lockstep pair, both sides moved together, matched | ✅ | ✅ yes |
| `0xC6A73/75-77/79/87/89-8B/8D` (10B) | rec0/rec1 Y=3072 | rec0/rec1 Y=512 | `gain_A` rec0/rec1 → flat 512 (r26 kill, born V42, refined V72/73). **PARTIAL**: `rec2 0xC6A90` / `rec3 0xC6AA4` byte-stock in both V37 and V74 (RULE 4 correction #4) | ✅ fixed, non-mode-indexed records | ✅ yes, creep-only by record selection |
| `0xC6CD0-1` | `FFFF` (unused) | 3564 | new private forward-LKAS gain cell (V57), same magnitude as V38's 4× | ✅ | ✅ yes |

### 4. `arb_setpoint_limit` table, `0xE4000/E5000` blocks (72 bytes) — MODE-PROOF, `gp-0x674e` FULLY TRACED

**Closing an open RULE-7-class question, 2026-08-06**: the selector `gp-0x674e` was previously cited from
an unverified golden-model comment ("A160 → selector 1, record `0xE41A8`") — exactly the class of
assumption RULE 7 demolished for `gp+0x63fd`. It has now been fully traced statically and the record
identity is corrected.

- **Producer** — **[EVIDENCE, decompile]** `FUN_00042692` @ `0x4272a`: `st.b r8, -0x674e, gp` (bytes
  `4447b298`), inside the SAME boot-gated block (`(gp-0x6d78 & 8) != 0`) that populates `gp+0x63fd`.
  `iVar1 = FUN_00057f8e()` (the zero-argument, deterministic HW-ID row matcher already established for
  the mode byte) selects a row in the **same** `0xCD000`-base, `0x24`-stride config table; `gp-0x674e`
  is copied from **column offset `0x1A`** of that row (the mode byte uses columns `0x12`/`0x14`/`0x15`).
  Single writer — no runtime re-selector exists for this cell (unlike `gp+0x63fd`'s 3 writers).
- **Readers** — **[EVIDENCE, `search_instructions` + independent `search_byte_patterns` raw scan, both
  agree exactly]** 6 total: 4 in `FUN_00028ea6` (`0x28fc8,0x29aa0,0x29b7c,0x29cc4`, all `ld.bu -0x674e,
  gp,r12`) feeding the `arb_setpoint_limit` LERP selection below, and 2 in `FUN_0002a93a`
  (`0x2a9a6,0x2abba`) indexing an unrelated angle-tracking table family (`0xCBA74`/`0xCB924`/etc,
  distinct from `0xCB844`) — not relevant to this limiter. (First `search_instructions` attempt used
  bracket-notation operand syntax and silently returned 0 — Ghidra's actual operand string is
  comma-separated, `"-0x674e, gp, r12"`; corrected and cross-checked against the raw byte scan.)
- **Pointer array & stride** — **[EVIDENCE, read directly from `0xCB844`, not inferred from a byte
  pattern]** 12 4-byte pointers, stepping by exactly `0x28` (40 bytes) within each of two 6-record
  banks: `{0xE4180,E41A8,E41D0,E41F8,E4220,E4248}` then `{0xE5180,E51A8,E51D0,E51F8,E5220,E5248}`.
  Stride independently confirmed from the record's own layout (read from `0xE51A8`): `u16 count=9` +
  9×u16 X + 9×u16 Y + 2 pad bytes = 40 bytes exactly. (Prior [BELIEF] on a 40-byte stride is now
  [EVIDENCE], pinned two ways.)
- **Which record is live** — row 11 (`0xCD18C`) dumped directly: its bytes spell `"TVCA45360YTVCA400"`
  in ASCII (independent re-confirmation of the row-11/`TVCA4` identity), and at column offsets `0x12`
  and `0x14` read **24** and **26** — an exact, independent reproduction of the already-established
  manual/engaged mode-byte values from the *same* row. At column offset **`0x1A`, the value is `7`**.
  Since the row matcher is deterministic and the same boot gate is already known-satisfied (this car
  demonstrably runs modes 24/26), **`gp-0x674e = 7` on this car**, not the previously-assumed 1.
  Selector 7 → pointer `0xE51A8` (not `0xE41A8`).
- **Raised or stock?** — all 12 records dumped and diffed stock/V37/V74: **8 raised to 16384**
  (`{0,1,3,4,6,7,8,9}` → `0xE4180,E41A8,E41F8,E4220,E5180,E51A8,E51D0,E51F8`), **4 left stock 15360**
  (`{2,5,10,11}` → `0xE41D0,E4248,E5220,E5248`) — matching "8 reachable per-part-number records" from
  the V38 build note exactly. **Selector 7 (`0xE51A8`) is in the raised set.**

**Verdict: the car's actual record IS raised — the report's "no clipping, ±16384" conclusion holds.**
The old "selector 1" comment happened to also name a raised record (`0xE41A8`), so the *practical* answer
was accidentally right; the *reasoning* was an unverified assumption and is now corrected to a full
trace. The 4 stock records are real and would matter for a different HW-ID/row not yet identified in
this kit — not an open item for this car. No on-car probe rung is needed to close this out (the row's
own bytes independently reproduce two already-established, on-car-confirmed values at neighboring
columns), but if belt-and-suspenders confirmation is wanted, the cheap rung is a one-shot read of
`gp-0x674e` onto the `0x14A` byte4 piggyback (it's a static boot-time value — one frame after boot
settles it, no continuous telemetry needed).

Uses `gp-0x674e`, a static per-part-number selector, **not** the engagement-linked `gp+0x63fd` —
mode-proof. ✅ in force. Recovers the ~6.25% of full-scale command that V9/V31/V37 clipped at 15360.

### 5. FactorC/FactorE damping tables, 10 mode-blocks (109 bytes) — MODE-INDEXED

`0xCE000, CF000, D0000, D2000, D3000, D4000, D6000, D7000, D8000, D9000`. V74's RULE-7-aware lever:
`FactorC Y[0]:=Y[2]`, `FactorE X[0]: 60→12`, `FactorE Y[1]:=Y[2]`, written on the **13 engaged-column
modes** `{2,3,5,11,14,15,17,23,26,27,29,32,33}` — disjoint from the 13 disengaged-column modes, so
manual/parking steering is byte-stock. **[prior EVIDENCE]** closes the two dead zones (FactorC dead
<35 km/h speed, FactorE dead <60 counts rate) that left base-assist damping exactly zero at creep on
every prior build including stock. ✅ in force (mode-proof *by construction of the write pattern* — every
engaged column was written — even though the individual table addresses are mode-indexed).

Downstream of this term sits the damper's own **output ceiling**, `0xC77A0[mode*4]` — a teammate's
independent decompile gives mode 26: `X=[300,800] Y=[512,1024]` on `gp-0x6ac2`. This matches the shape
of a ceiling table already on record for modes 10/11 (`0xD209C`/`0xD20A8`, same `X=[300,800] Y=[512,1024]`
— see `memory/reference-accord-damping-clamp-dtc1d-trap.md`), consistent with V73's finding that most
mode-indexed records are byte-identical 24-vs-26 (relabeling, not retuning). This caps the *damping*
term specifically at 512–1024, unrelated to the LKAS lane, and is a minor consumer of the governor's
shared headroom (see Part 2).

### 6. Friction records, 14 mode-locations (84 bytes) — MODE-INDEXED

Byte-exact repeated pattern `9ad99ae952f8 → 67c667de7bf4` at 14 distinct addresses (`0xCF6E0/F0, 0xD0A5C,
0xD2A4C/5C, 0xD3A5C/6C, 0xD4A5C, 0xD6A5C, 0xD7A5C/6C, 0xD8A5C, 0xD9A5C/6C`) — friction ×1.5 applied per
engaged mode. ✅ in force.

### 🛑 What did NOT change V37 → V74, and why it matters

- **`0x3AB76`/`0x3AC20` (V62's `sar 0xa→0x9` grind-#1 fix) are ABSENT from both V37 and V74** — confirmed
  by their complete absence from the diff. **[prior EVIDENCE, BUILD-LINEAGE RULE 4]** this fix was only
  ever carried by V62 and V65. **The kit's only measured grind-#1 fix is currently off the car** (not on
  V73, flown, nor V74, built).
- `0xC6440/42/46` (gain_B fixed scalar arms, touched transiently by V63/64/67/68/71C) — stock in both
  V37 and V74, reverted before V72.
- **Governor nominal `0xC6202` and both governor slew steps `0xC6206`/`0xC6208`** — **byte-identical,
  stock 4762/512/205 — [EVIDENCE, fresh `read_memory` this session on the live V74 program]**: raw bytes
  `9a12000c` at `0xC6202` = 4762 exactly.
- **Motor-rate adaptive cap table `0xC520C` bank** — **byte-identical to stock**, `X=(1050,1700,2500,
  3700,4100)`, `Y=(5325,3584,2406,1587,512)` — **[EVIDENCE, fresh `read_memory`, exact byte match]**.
  Both of these last two are load-bearing for Part 2.

### Net delivered LKAS gain, V74 vs stock — the arithmetic

The LKAS arb-stage gain (`steer_torque_arbitration`, `FUN_00028ea6`) has **no speed term at all** — it's
a pure function of the CAN request and the Q15 gain. The 4× figure below is therefore constant across
creep/10/50 km/h/highway; what varies by operating point is how much headroom is left *downstream*
before something else clips it (see Part 2).

- **Setpoint stage:** `clamp(torque×-4, ±16384)` — unchanged since V9. Full-scale openpilot request
  (±4096) already saturates this at every build (see Part 2's upstream-clamp section — this is the same
  wall from the other side).
- **`arb_setpoint_limit`:** V37 clips to `±15360` (93.75% of full scale); **V74 raises to `±16384`
  (100%, no clip)** — a genuine, secondary ×1.0667 recovery at the very top of range only.
- **Q15 gain:** V9 `891` → V31/V37 `1782` (2×) → **V38-through-V74 `3564` (4×), unchanged for the whole
  V38→V74 arc**, just relocated to a private cal cell by V57.
- **arb/pack clamp:** V37 `1024` → V74 `2048`, in lockstep with the gain (an established pattern, doubled
  at every gain step so far).
- **Net full-scale LKAS-lane output:** V37 = `(15360×1782)>>15 = 835`; **V74 = `(16384×3564)>>15 = 1781`**
  → **2.13× V37, 4.27× stock** (stock = `(15360×891)>>15 = 417`) at the arb-lane output stage.
- **Never clipped by its own clamp** (1781 vs 2048, 13% margin) **or by the aggregator's LKAS-lane
  zero-reject window** (`±0x2800=10240`, nowhere close) **at any speed** — both non-binding at 4×,
  everywhere.
- **Creep / 10 km/h:** base-assist damping is architecturally zero (both FactorC/FactorE dead zones, only
  partially opened by V74's own lever on the *damping* term, not the LKAS term), so LKAS's 4× reaches the
  wheel essentially undiminished.
- **50 km/h / highway ≥20 m/s:** base-assist contributions turn on, consuming governor headroom, but
  measured on-car electrical rate at highway cruise (`gp-0x6ac0` peak 329.8, route 59) sits well below
  the adaptive rate-cap's 1050-count onset — the flat 4762 ceiling, not the rate cap, would bind first
  at these speeds, and only under combined LKAS+assist saturation, which the measured operating points
  don't reach.

---

## Part 2 — is 8× feasible, and what is the theoretical limit?

### 2.0 The problem is constrained from BOTH ends, not just downstream

**[EVIDENCE, teammate's independent Ghidra decompile of `FUN_00052676`, cross-checked against the golden
model]** `FUN_00052676` decompiles to `clamp(request × -4, ±0x4000) → gp-0x69ae`. openpilot's `STEER_MAX`
for this platform is **4096**, and **4096 × 4 = 16384 = 0x4000 exactly.** The firmware's own setpoint
clamp is sized to precisely match openpilot's transmit rail — **there is zero upstream headroom.**
Raising `STEER_MAX` on the openpilot side would be clipped straight back by this clamp; there is no "free
2×" available by touching the comma-side scaling alone. **All additional authority must come from
firmware gain, applied downstream of an already-4096-capped input** — which is exactly what the V9→V74
lineage has done (891→1782→3564).

**A second openpilot-side limiter, not previously quantified in this kit:** openpilot slew-limits the
steering command in *normalized* units, upstream of both `STEER_MAX` and the firmware gain
(`STEER_DELTA_UP/DOWN=3`, `DT_CTRL=0.01`) — **[VERIFIED against opendbc, golden model
`eps_lkas_chain_model.py:2232`]**. Measured directly on-car (route 5d, teammate relay): a hard slew cap
at **exactly 123 counts/frame = 0.03×STEER_MAX**, with **zero frames exceeding it**. It binds **8.01% of
engaged frames** overall and is the **dominant limiter at highway speed** — 9.8% of frames above
25 m/s, vs the amplitude rail at only 2.3% there. **Combined, 16.07% of engaged time is spent against
one rail or the other** (slew or amplitude) on the current 4× build.

**🛑 This slew ceiling, expressed in firmware lane counts, scales WITH the firmware gain:**
`(0.03 × STEER_MAX × 4 × gain) >> 15`. Concretely:

| build | gain | slew ceiling (counts/10 ms tick) | time to full physical torque |
|---|---|---|---|
| stock | 891 | 13.4 | ~170 ms |
| **V38→V74 (current, 4×)** | 3564 | **53.5** | **~42 ms** |
| 8× stock | 7128 | **106.9** | **~21 ms** |

openpilot's `steerActuatorDelay` is **100 ms**. Stock's slow slew (170 ms to full torque) sat *outside*
that delay and dominated/damped the loop; **V38's fast slew (42 ms) already crosses INSIDE the 100 ms
delay — a documented "classic limit-cycle recipe"** — and this is tied to V38's grind onset (engaged-only,
absent hands-on, worst at low speed, immune to firmware-only fixes that don't touch gain, e.g. V39/V41).
**At 8×, time-to-full-torque halves again to ~21 ms — 4.8× inside the actuator delay, vs V74's current
2.4×.** This is a comma-side scaling gap, not a firmware defect by itself, but **it is coupled to the
firmware gain and gets strictly worse as gain rises.** This is the single strongest argument against a
nominal 8× as specified, independent of any downstream firmware clamp.

### 2.1 Every downstream (firmware) magnitude limiter, CAN frame → motor, in binding order

1. **CAN intake** — signed16 ±4096 (DBC). Not a firmware lever (see 2.0).
2. **Setpoint scale** `×-4`, clamp `±0x4000=16384` — code literal, saturates at full-scale input already,
   exactly matched to `STEER_MAX` (see 2.0).
3. **`arb_setpoint_limit`** — V74 `±16384`, headroom already spent (V37 had 6.25% margin at `±15360`;
   V38+ recovered it). **[EVIDENCE, fully traced 2026-08-06]** the record this car actually reads
   (`gp-0x674e=7` → `0xE51A8`, see Part 1 §4) is confirmed in the raised set — this is not an assumption.
4. **Q15 gain** (`0xC6CD0`) — `3564` today (4× stock). Doubling to `7128` (8×) is a **2-byte cal edit**.
5. **`arb_output_clamp` / `pack_output_clamp`** (`0xC61B2/4`, currently `2048`) — at gain=7128, full-scale
   output computes to `(16384×7128)>>15 = 3564 > 2048` → **without a matching clamp raise, the top ~42%
   of the command's dynamic range hard-clips to one flat value** (setpoints 9418–16384 all collapse to
   2048) — *worse* for proportionality than not raising gain at all. The established, twice-precedented
   pattern (V22→V38, V31→V38) is to **double this in lockstep, 2048→4096**. Cal-only, same class of edit
   already flown safely twice.
6. **Distribute LKAS-lane clamp / mixer gate clamp** (`±0x2800=10240`) — never binds at 3564; still 2.87×
   headroom even at 8×. Not a practical ceiling.
7. **Aggregator LKAS-lane window** (`±0x2800=10240`) — **[EVIDENCE, per a teammate's decompile of
   `FUN_0003aa2c`]** the aggregator's per-lane gates are a **zero-reject**, not a clamp: implemented as
   the unsigned-wraparound idiom `v * ((v + 0x400) < 0x801)` — a lane outside its window contributes
   **zero**, not a saturated value. LKAS's own window (`±10240`) never binds at 8× (3564 << 10240).
   **The aggregator's own gates are not where 8× dies** — the *tight* zero-reject windows belong to
   OTHER lanes (friction `±1024`, damping `±2048`), not LKAS.
8. **Aggregator total/output clamp** (`±0x2800=10240`, this one IS saturating) — LKAS alone at 8×
   (3564) + base assist (a few hundred to ~1300 at the boost curve's max, plus damping now capped
   512–1024 by `0xC77A0`) stays well under 10240. Not the ceiling either.
9. **🛑 Governor flat nominal, `0xC6202=4762`** — **[EVIDENCE, fresh `read_memory`, confirmed
   stock/unchanged in V74]**, applied via `FUN_0004503c` — **[EVIDENCE, fresh decompile this session:
   confirmed the `gp-0x4f64`-based limit/scale structure, the `gp-0x67f5` step selector between
   `0xC6206`/`0xC6208`, and the `gp-0x67fa==4` substitution branch, all matching the golden model
   exactly]**. LKAS-alone at 8× (3564) fits under 4762 with 25% margin *in isolation*, but any concurrent
   base assist above the FactorC dead-zone edge (~20-35 km/h, mode-dependent) routinely pushes the
   aggregate toward/over 4762 → soft clip. **🛑 Not a safe direct-edit target**: `docs/BUILD-LINEAGE.md`
   records `0xC6202` as "investigated and REJECTED... buys nothing, and `gp-0x4f64` is shadowed → fault
   `0x17`, hard-fault-eligible."
10. **🛑🛑 Governor motor-rate ADAPTIVE cap** (`0xC520C` bank, `X=(1050,1700,2500,3700,4100)`,
    `Y=(5325,3584,2406,1587,512)`) — **[EVIDENCE, fresh `read_memory`, byte-exact stock match]**
    **untouched by any build V37→V74.** Keyed on measured **motor electrical rate**, not gain.
    **[prior EVIDENCE]** "V38 (LKAS alone 1782) binds from z~3414, or z~2229 with base assist in the
    aggregate" — i.e. even at TODAY's 4×, moderately fast steering already clips here, before the flat
    4762 ceiling matters. **At 8× this table would bind at LOWER electrical rates and clip HARDER**
    (toward the 512 floor at the high end) than it does today. **This is almost certainly the dominant
    real-world ceiling on any 8× delivery** — insensitive to gain/clamp edits, sensitive only to how fast
    the wheel is actually turning.
11. **Governor slew** (`0xC6206=512`/`0xC6208=205`, step selected by `gp-0x67f5`) — rate-of-change only,
    doesn't reduce steady-state magnitude. V42's ramp-time-parity scaling (flown, carried through V74)
    already accounts for the 4× reach; an 8× gain would need this rescaled again for the same reason, or
    ramp time doubles again — a feel issue, not by itself a fault, if left alone. (Distinct from the
    **openpilot-side** slew problem in 2.0, which is the more serious of the two.)
12. **Soft-EME shaper** — corridor/boost bound `5120` (matched int+float since V38, unchanged V37→V74)
    and final static clamp `±0x2000=8192`. Since the governor already caps the aggregate at ≤4762
    (<5120), **both stay clear at 8×, PROVIDED the governor nominal is left alone.** If a future stage
    instead raises 4762 upward to let 8× actually reach the wheel, the corridor/boost bound and its
    float mirror become live risk again (next item).
13. **Hard-DTC lockstep monitor** (`FUN_00043e44`, DTC-0xF00049) — mirrors the corridor/boost arms in
    float, ±5 LSB tolerance, **no debounce, hard motor-off**. Exactly the class that bricked V25-V27
    (asymmetric int/float edit) and nearly bricked V48B. **Not triggered by a gain-only 8×** (aggregate
    stays under 5120 as long as the governor ceiling is untouched) — becomes live risk only if a later
    stage pushes the aggregate regularly past 5120 without a bit-exact matching float edit.
14. **DTC-0x1d damping clamp lockstep** (`FUN_000347b8`, int `0xD209C/A8` vs float `0xC6554/58/5C/60`,
    ±5/1024 tolerance, feeding the `0xC77A0` ceiling family) — base-assist path, not the LKAS gain path.
    Not triggered by an LKAS-only 8× edit.
15. **DTC-0x49 gentle-EME counter** — defused since V37 (`dtc49_torque_gate=255`, never fires).
    Independent of gain magnitude; stays defused at 8×.
16. **DTC-0x18 per-task overrun watchdog** — [documented in `CLAUDE.md`/project standing instruction;
    **not independently re-derived this session** — BELIEF-tier citation] relevant only if new CODE is
    added to the 1 kHz control task (a cave). **A pure cal-edit 8× lever (gain + clamp doubling, no new
    code) does not touch this at all.**
17. **V40's ignition-brick mechanism** — **[prior EVIDENCE]** caused specifically by
    `governor_slew_step→0xFFFF` (rate limiting removed entirely, command chases power-up sensor noise,
    trips the hard-fault-eligible cross-tick monitors). **Not implicated by a gain/clamp-only 8×** as
    long as `0xC6206`/`0xC6208` are left alone.
18. **FOC current loop / PWM output** (`FUN_00071272` Park/Clarke+PI+SVPWM, `FUN_0006c5ce` duty compute,
    carrier ~4.000 kHz) — **[OPEN]**. No independent motor-current or thermal ceiling was located
    downstream of the governor this session; the golden model treats q-axis current as directly
    proportional to the merged command. Whether a hardware current/thermal limit binds before or
    alongside the governor chain is genuinely unresolved — would need a dedicated trace of
    `FUN_00071272` and the ADC/current-sense scaling to close out.

### 2.2 The hard structural ceiling, and what sets it

**There is no single flat wall at "N× stock."** In order of what actually binds as gain climbs from
today's 4× toward 8×:

1. **`arb_output_clamp` (2048)** — binds first, ~4.5-4.6× stock, IF the clamp isn't raised. Cheap fix
   (lockstep double), zero new risk.
2. **Governor flat ceiling (4762)** — binds on the *aggregate*, intermittently, once base assist is
   concurrently active. Soft clip, no fault, if `0xC6202` itself is left untouched.
3. **Governor adaptive rate cap** — binds on **any fast steering motion, at any road speed**, and gets
   **worse, not better, as gain rises** (it's a function of measured motor speed, not command magnitude).
   **This is the real ceiling for a nominal 8× during real dynamic driving** — it already partially binds
   at today's 4×.
4. **Past that**, touching either the flat governor nominal directly, or pushing the aggregate routinely
   above 5120 without a matched EME float-mirror edit, is where **brick-class risk** (DTC-0xF00049, hard-
   fault index 0x17, the V25-V27/V40 failure classes) lives. Not required to reach a *nominal* 8×, but IS
   required if you also want 8× to *survive contact with* the adaptive rate cap.
5. Motor current/thermal hardware limit: **[OPEN], unresolved.**
6. **Not downstream at all**: the **openpilot-side command slew** (§2.0) is a separate, upstream ceiling
   that gets worse with gain and is arguably the more urgent constraint of the two, because it bears
   directly on closed-loop stability rather than just delivered amplitude.

### 2.3 Is 8× reachable?

**Nominally: yes, cal-only, low risk, for slow/gentle corrections.** Double `0xC6CD0` (3564→7128) and
`0xC61B2`/`0xC61B4` (2048→4096) in lockstep, leave governor/EME/slew cals untouched. Arithmetically
clean, doesn't touch any of the kit's documented brick classes.

**In practice, no — not as a delivered multiple during real dynamic steering, and likely not safely
either, once the loop-dynamics point is weighed.** Two independent effects both work against it:

- The **untouched adaptive rate cap** already partially clips today's 4× during moderately fast
  corrections; at 8× it clips harder and at lower rates, degrading the *delivered* multiple back toward
  something closer to 4× (or less) exactly during the maneuvers — quick corrections, lane changes —
  where more authority would matter most. Slow, gentle, low-rate corrections (steady highway
  lane-centering, measured peak electrical rate 329.8, well below the cap's 1050-count onset) would see
  close to the full nominal 8×.
- The **openpilot-side slew ceiling scales with gain** and is *already* inside the actuator delay at 4×.
  Doubling gain again halves time-to-full-torque to ~21 ms — tightening a mechanism already implicated in
  the kit's engagement-conditional, low-speed grinding. This risk is **independent of any firmware clamp
  edit** and cannot be fixed by a firmware-only change; it would need a matching change on the openpilot
  side (out of scope — `docs/BUILD-LINEAGE.md` / project policy: "no openpilot-side modifications").

**To make a nominal 8× actually reach the wheel during fast maneuvers**, the adaptive rate-cap TABLE (not
the flat nominal) would need widening — raising the 512 floor and/or the mid-table knees. This is the
same region V41 already flew safely (a flatten-to-table-max variant), so there is precedent for touching
this block without a fault — but a *different* edit shape (raising values rather than flattening) is
untested, and this block sits adjacent to the still-unresolved `[0xC5000,0xC5FFC)` CRC-gap association
with V40's brick (`memory/reference-crc-chain-is-50-blocks-c5000-not-a-gap.md`: "the causal link to V40's
ignition fault is unproven"). Treat as a distinct, separately-staged, separately-monitored sub-lever, not
bundled into a first 8× cut — and doing this *without* also addressing the openpilot-side slew problem
would let more torque through faster, which is the opposite of what §2.0 argues for.

### 2.4 Closed-loop stability (GATE 2) — now has a concrete mechanism, still not a measured margin

Previously flagged as fully open; it is better characterized now, though still not quantified as a
margin number:

- **Mechanism identified**: raising firmware gain shortens the physical time-to-full-torque
  (§2.0's slew table), pushing that response time further inside openpilot's fixed 100 ms actuator
  delay. A control loop whose own actuation speed approaches or exceeds its assumed model delay loses
  phase margin at the frequencies near that crossover — the golden model calls the V38 case (42 ms inside
  100 ms) "a classic limit-cycle recipe," and it lines up with the on-car evidence (V38 grind onset,
  engaged-only, absent hands-on, worst at low speed, immune to firmware-only fixes that don't touch
  gain). At 8× (~21 ms) that mismatch roughly doubles again.
- **Baseline is not clean today.** V74's own pre-registered abort probe measured **5×f0 relay-generation
  prominence at 2.227** (NFFT 2048) against a pre-registered **3.0 abort threshold** — inside the flown
  corpus, but not by a wide margin — and **grind #1 confirmed still active at 2.72× over its control
  floor.** Any 8× proposal is evaluated relative to a loop that is *already* marginally stable at 4×, not
  a pristine one.
- **Still not quantified**: an actual gain/phase margin number at 4× or 8× against the 6-9 Hz / 18-22 Hz /
  21 Hz resonances already characterized in this kit. I did not compute one this session and don't have
  a reliable way to from static analysis alone.

### 2.5 Staged ladder — cost class and what breaks first

| stage | edit | cost class | risk | delivers |
|---|---|---|---|---|
| **2×** (stock→1782) | flown, V31 lineage | cal-only | none — years of flight history | FLOWN |
| **4×** (stock→3564) | flown, V38→V74 | cal-only | none — most battle-tested stage in the kit | **ON CAR NOW (V73)** / built (V74) |
| **8× gain+clamp** | `0xC6CD0`→7128, `0xC61B2/4`→4096, lockstep | **cal-only** | **LOW structurally** — twice-precedented pattern, doesn't touch governor/EME/DTC logic, no cave — but see the openpilot-side slew concern in §2.0/§2.4, which this stage does NOT address | Full nominal 8× only at low steering rates (highway cruise); progressively clipped toward ~4×-ish during fast corrections by the unchanged adaptive rate cap; command physically reaches full torque in ~21 ms, well inside the 100 ms actuator delay |
| **8× + rate-cap table widen** | above + raise `0xC520C` Y-values (not the flat `0xC6202`) | **cal-only**, but new edit territory | **LOW-MODERATE** — precedented block (V41 flew a flatten variant), untested edit *shape*, adjacent to the unresolved C5000-gap/V40 association | Needed for 8× to actually show up during fast maneuvers, not just steady cruise — but *worsens* the §2.0/§2.4 slew/delay concern by letting more torque through at the already-faster physical rate |
| **Touching the flat governor nominal or the EME corridor/boost bound directly** | edit `0xC6202`, or push the aggregate routinely >5120 | single in-place edit, high-consequence | **HIGH** — hard-fault index 0x17 (documented), DTC-0xF00049 hard EME with no debounce (the V25-V27/V48B brick class) | Not recommended, not necessary for a nominal 8× |
| **Any code-cave-based redesign of the governor/aggregator** | new code on the 1 kHz path | **CAVE** | **HIGHEST — this kit's only bricking class** (V24, V27, V48B all bricked the ECU) | Not indicated by anything found in this trace — every limiter identified is reachable by cal-only or single in-place edits |

**What breaks first as you climb:** soft clipping (arb clamp → governor flat ceiling → adaptive rate
cap), all three well before any brick or DTC risk. A straightforward cal-only 8× (gain+clamp doubling,
governor/EME untouched) does not by itself approach any documented brick class. **The realistic failure
mode of a naive 8× attempt is not a brick — it's disappointment on delivered amplitude, and a
plausible increase in a limit-cycle risk that is already live at 4×** (§2.0, §2.4). Verifying "did 8×
actually arrive at the wheel, and did the loop stay stable" needs an on-car probe of `gp-0x6ace`/
`gp-0x6acc` (the post-governor values) the same way V54/V55/V59 probed other stages — not assumed from
the cal alone (RULE 6's general lesson: a lever that looks flashed and correct can still be structurally
capped downstream).

---

## OPEN items — what a future session would need to close this out

1. **Motor current / thermal hardware limit** downstream of the governor and FOC chain — not located
   this session. Needs a dedicated trace of `FUN_00071272` (Park/Clarke + PI regulator) and the
   ADC/current-sense scaling.
2. **Quantified closed-loop gain/phase margin** at 4× (today) and at a hypothetical 8×, against the
   6-9 Hz / 18-22 Hz / 21 Hz resonances already characterized. A mechanism is now identified (§2.4) but
   not a number.
3. **`0xC63A1`** — a 1-byte companion of the clamp-doubling cluster, not independently attributed this
   session (**[BELIEF]** only).
4. **Whether the adaptive rate-cap table can be safely widened by *raising* values** (as opposed to V41's
   flight-proven *flattening*) — untested edit shape, in a block adjacent to the still-open
   `[0xC5000,0xC5FFC)`/V40 association.
5. **Whether any 8× stage is worth pursuing at all given §2.0/§2.4** — a firmware-only fix cannot address
   the openpilot-side slew-ceiling coupling, and this kit's standing policy is no openpilot-side
   modifications (`memory/feedback-no-openpilot-side-modifications.md`).

**Recommendation for any future work here: stage behind a report-only on-car probe of `gp-0x6ace`/
`gp-0x6acc` (post-governor command) before flying any gain change beyond 4×, rather than flying it blind.
Do not build or flash from this document alone.**

---

## Sources

`docs/STATE.md`, `docs/BUILD-LINEAGE.md` (RULES 3-7), `analysis-2020accord/eps_lkas_chain_model.py`
(`Calibration.for_build`, `steer_torque_arbitration`, `limit_distribute_mixer_gate`,
`motor_torque_demand_aggregator`, `motor_torque_governor`, `soft_eme_windup_shaper`,
`hard_dtc_lockstep_monitor`, `openpilot_command_slew_invariance`), `memory/reference-accord-damping-
clamp-dtc1d-trap.md`, `memory/reference-crc-chain-is-50-blocks-c5000-not-a-gap.md`,
`../accord-firmwares/analysis-2020accord/_v37_plain_image.bin`,
`../accord-firmwares/analysis-2020accord/_v74_engagedcols_x0_12_addonly_plain_image.bin`. Ghidra
(`mcp__ghidra__decompile_function`, `mcp__ghidra__read_memory`) against `code.bin` and the live V74
program for the governor trace and the two spot-checked cal cells (`0xC6202`, `0xC520C`).
