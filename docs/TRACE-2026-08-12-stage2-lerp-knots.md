# TRACE 2026-08-12 — the Stage-2 LERP knots, and the inversion of `|gp-0x6b70|`

Agent: `LerpKnots` (firmware-codepath-tracer). Study-only; no build, no flash, no shared-state edits.
Tooling: GhidraMCP for all decompilation/disassembly; Python for all byte-level work. Program:
`stock_fw_dump/code.bin` (confirmed current in `list_open_programs`).

**Headline: the runtime rescale that was expected to defeat this task does not exist.**
`K1 = K2 = 1024` for the life of the ECU. The Stage-2 LERP knots ARE the flash record, verbatim.
Route 80's measured `|gp-0x6b70|` inverts to **`|iVar6| ∈ [0, ~6,900]` at parking-lot creep** — a
**2.9x tighter** bound than the ±20,000 writer clamp a naive sizing would use.

Anchors verified with Python before any address arithmetic: `0xC64DF`=100, `0xC40D2`=102,
`0xC63AC`=102, `0xC6468`=2639, `0xC63AE`=1024, `0xC6200`=8192. All match. `tp = 0xBF000`.

---

## 1. The chain, confirmed end to end [EVIDENCE]

```
        gp+0x63fd (mode byte)          gp-0x6a64 (speed, 1/64 km/h)
                 |                              |
                 v                              v
   FUN_000382d8 @0x382d8   ptr[mode]  +  linear blend between two of SEVEN speed records
        0xCC9FC + mode*4   -> breakpoints [0, 960, 2560, 5120, 7680, 10240, 12800] counts
                                        = [0, 15, 40, 80, 120, 160, 200] km/h
        0xC7B40 / 0xC7C28 / 0xC7D10 / 0xC7DF8 / 0xC7EE0 / 0xC7FC8 / 0xC80B0  (+ mode*4)
        record layout: +0x00 count(=9)  +0x02..0x12 nine X shorts  +0x14..0x24 nine Y shorts
                 |
                 |  writes gp-0x6350[0..8] (Xsrc)  @0x38880/0x388aa
                 |         gp-0x630c[0..8] (Ysrc)  @0x3884c/0x38886/0x388b0
                 |  then EIGHT unconditional rungs  Ysrc[i] = max(Ysrc[i], Ysrc[i-1])  @0x388c4+
                 v
   FUN_000389ec @0x389ec   X[k] = Xsrc[k] * 1024 / K1     @0x38c64 shl / 0x38c6a divq
                           Y[k] = Ysrc[k] * K2  >> 10     @0x38c7e mul / 0x38c84 sar
                           X[0] = Y[0] = 0 (hard stores)  @0x38d1c / 0x38d22
                           X-axis truncation at a speed-scheduled cap (see §4)
                           Y[k] = max(Y[k], Y[k-1])       @0x38de2 / 0x38e48
                           Y[k] = min(Y[k], 0xC6200=8192) @0x38e9c / 0x38ea2
                           X[9] = max(0xC613C=14490, X[8]);  Y[9] = 8192
                           copy gp-0x373c[] -> gp-0x64b8[] and gp-0x3714[] -> gp-0x641c[]
                 v
   FUN_00038148 @0x38148   iVar5 = gp-0x6bfe - (gp-0x374c >> 4)          @0x38218 / 0x381fe
                           iVar6 = iVar5 + gp-0x6bfa                     @0x38208
                           uVar7 = |iVar6| * (0xC63AE = 1024) >> 10      == |iVar6| EXACTLY
                           LERP over X = gp-0x64b8[0..9], Y = gp-0x641c[0..9]
                           gp-0x6b70 = sign(iVar6) * LERP(uVar7), clamped +-(0xC6200 = 8192)
```

Both ends verified against the same ten-point table: `FUN_000389ec` writes `gp-0x64b8..gp-0x64a6`
and `gp-0x641c..gp-0x640a`; `FUN_00038148` reads exactly those.

**A guard worth knowing:** if `|gp-0x6bfe| > 20000` the whole function short-circuits and
`gp-0x6b70 = 0x7FFF` (32767). That is a fault sentinel, not a curve value.

---

## 2. 🛑 The crux: the runtime rescale is the IDENTITY [EVIDENCE — this is the whole finding]

`FUN_000389ec` @`0x38bc6`/`0x38bec` computes the two factors:

```python
# 0x38bc6 ld.hu -0x6984,gp,r7   ->  K2, the Y multiplier
v = mem_u16(gp - 0x6984)
K2_target = v if (v - 204) & 0xFFFF < 1845 else 1024     # i.e. v in [204, 2048] else UNITY
if K2_target <= cal(0xC6390):                            # 2048
    K2_target = max(K2_target, cal(0xC639A))             # 204
# 0x38bec ld.hu -0x6982,gp,r16  ->  K1, the X divisor
w = mem_u16(gp - 0x6982)
K1_target = w if (w - 204) & 0xFFFF < 1845 else 1024
if K1_target <= cal(0xC6392):                            # 2048
    K1_target = max(K1_target, cal(0xC639C))             # 204
K1 = FUN_0003897a(K1_target, state=gp-0x3742, 0xC639E, 0xC6394, 0xC6396, 0xC6398)
K2 = FUN_0003897a(K2_target, state=gp-0x3744, 0xC639E, 0xC6394, 0xC6396, 0xC6398)
```

Cal values read from the image: `0xC6390 = 0xC6392 = 2048`, `0xC639A = 0xC639C = 204`,
`0xC639E = 717`, `0xC6394 = 1331`, `0xC6396 = 10`, `0xC6398 = 102`.
(`FUN_0003897a` @`0x3897a` is a generic rate limiter: inside the window `(717, 1331)` it snaps to
`clamp(target, 717, 1331)` immediately; outside it slews at 10 or 102 counts per invocation.)

### `gp-0x6982` and `gp-0x6984` are NEVER WRITTEN, and they boot to exactly 1024

Three independent methods, all agreeing:

| method | `gp-0x6982` | `gp-0x6984` |
|---|---|---|
| GhidraMCP `search_instructions operand_pattern` | 2 hits, both `ld.hu` (`0x38bec`, `0x394d6`) | 2 hits, both `ld.hu` (`0x38bc6`, `0x394e2`) |
| Python raw LE scan, 4-byte disp16 form (`hw2 = disp\|1`) | same 2, opcode `0x3F`, **zero `st.h` (`0x3B`)** | same 2, **zero `st.h`** |
| Python raw LE scan, 6-byte disp23 extended form | 0 | 0 |
| exhaustive byte-aligned search for the absolute address as a 32-bit literal (`0xFEDF167E` / `0xFEDF167C`) | **0 occurrences anywhere in the 1 MB image** | **0 occurrences** |

The last row closes the `ep`-relative / register-indirect aliasing trap: no base register pointing at
these cells can be formed from a literal anywhere in the image.

**Positive control for the scan:** the neighbours in the same block — `gp-0x6980`, `gp-0x6986`,
`gp-0x6988`, `gp-0x698A` — DO have disp16 `st.h` writers (`0x367a0`, `0x27340`, `0x27362`, `0x27384`).
The scan is demonstrably capable of finding a writer here; it found none for these two.

**The boot values settle it.** `gp-0x6982` = `0xFEDF167E` and `gp-0x6984` = `0xFEDF167C` both lie in
the app `.data` window `0xFEDF11B0..0xFEDF5A68` (boot copy at `0x1475C`: flash `0x86260..0x8AB18`
→ RAM `0xFEDF11B0`; see `reference_accord_app_ram_layout_and_boot_init_loops`).

```
gp-0x6982  RAM 0xFEDF167E  <- flash 0x8672E = 0x0400 = 1024
gp-0x6984  RAM 0xFEDF167C  <- flash 0x8672C = 0x0400 = 1024
gp-0x3742  (K1 slew state) <- flash 0x8996E = 1024
gp-0x3744  (K2 slew state) <- flash 0x8996C = 1024
```

Target 1024, state 1024, and the state lies inside the snap window `(717, 1331)`, so
`FUN_0003897a` returns `clamp(1024, 717, 1331) = 1024` on every call, forever.

⇒ **`K1 = K2 = 1024`. `X[k] = Xsrc[k]`, `Y[k] = Ysrc[k]`. No rescale.**
The `[204, 2048]` cal bounds are live guard rails on a value that never varies. The feared
`>= 10x` swing in `f'` does not occur, at any speed, in any mode, on any build to date.

**Why the fallback exists** [BELIEF, well-supported]: the siblings `gp-0x6986/0x6988/0x698A` are
written by `FUN_00026c80` (the LKAS arbitration function) as **min-reductions over three 11-element
lane-gain arrays** seeded to `0x400`, each mirrored to a lockstep shadow at `gp-0x4c60/62/64`.
`gp-0x6982`/`0x6984` are two more slots of the same gain-limiter family that this part number's
software simply never populates. Honda wired the consumer, left the producer out, and the unity
default carries. The `(v-204) < 1845 else 1024` test is the plausibility guard for exactly that case.

---

## 3. The knots — modes 24 and 26, read from the image

Pointer dereference is `array + mode*4`, printed with the mode beside every address:

```
MODE 24 (MANUAL)              MODE 26 (ENGAGED)
brk  @0xCCA5C -> 0xD6BA8      brk  @0xCCA64 -> 0xD7B98     (both: 0/15/40/80/120/160/200 km/h)
rec0 @0xC7BA0 -> 0xD6158      rec0 @0xC7BA8 -> 0xD7130     bytes DIFFER  (Y[8] 4181 vs 4114)
rec1 @0xC7C88 -> 0xD61D0      rec1 @0xC7C90 -> 0xD71A8     bytes IDENTICAL
rec2 @0xC7D70 -> 0xD6248      rec2 @0xC7D78 -> 0xD7220     bytes IDENTICAL
rec3 @0xC7E58 -> 0xD62C0      rec3 @0xC7E60 -> 0xD7298     bytes DIFFER
rec4 @0xC7F40 -> 0xD6338      rec4 @0xC7F48 -> 0xD7310     bytes DIFFER
rec5 @0xC8028 -> 0xD63B0      rec5 @0xC8030 -> 0xD7388     bytes DIFFER
rec6 @0xC8110 -> 0xD6428      rec6 @0xC8118 -> 0xD7400     bytes IDENTICAL
```

⚠ Mode 24 != mode 26 in this family (unlike the damper families —
`accord-stock-mode24-equals-mode26-damper-is-ours` is scoped to those). But in the **creep** regime
the difference is confined to `Y[8]` of `rec[0]` (4181 vs 4114, 1.6 %), so mode choice barely moves
the curve where we care.

**The two creep records, verbatim from flash:**

```
rec[0]  0 km/h   X = [0, 200, 400, 800, 1200, 1800, 3000, 5000, 12000]
        m24      Y = [0, 471, 880, 1408, 1689, 1953, 2376, 2844,  4181]
        m26      Y = [0, 471, 880, 1408, 1689, 1953, 2376, 2844,  4114]
rec[1] 15 km/h   X = [0, 150, 300,  618, 1200, 1800, 3000, 5000, 10000]
        both     Y = [0, 429, 788, 1350, 2029, 2358, 2763, 3297,  4625]
```

`FUN_000382d8` @`0x385ea..0x38648` blends them with truncating integer division:
`Xsrc[i] = lo.X[i] + ((hi.X[i]-lo.X[i]) * (speed - brk[k-1])) / (brk[k] - brk[k-1])`, same for Y.
Below 15 km/h that is always `rec[0]`→`rec[1]` with `frac = speed_counts / 960`.

---

## 4. The one real schedule: a speed-scheduled X-axis cap

`FUN_000389ec` @`0x389ec..0x38a5c` LERPs vehicle speed `gp-0x6a64` through
X `0xC669A..0xC66A6` = `[0, 640, 1600, 3200, 5120, 7680, 12800]` counts = `[0, 10, 25, 50, 80, 120, 200]` km/h
Y `0xC66A8..0xC66B4` = `[12000, 10000, 10000, 7000, 7000, 7000, 7000]`
and **truncates the X axis at that value**, replicating the remaining knots flat.

At creep the cap is 12,000 (0 km/h) down to 10,681 (6.6 km/h) — it only ever bites at knot `k=8`,
far above anything observed. **Irrelevant to this inversion**, but it is the mechanism that makes
the curve saturate, and it moves with speed, so a highway-regime inversion must include it.

The other conditional floors in `FUN_000389ec` are no-ops on stock: gates `0xC613E` = `0xC6140` = 15000
(above every X in play) and floors `0xC617A` = `0xC617C` = **0**.

---

## 5. The built table at creep, and the inversion

Script (scratchpad, reproducible): mirrors the decompiled integer arithmetic line by line.

```
mode 26 (ENGAGED)  0.0 km/h   Xcap 12000
   X  = [0,  200,  400,  800, 1200, 1800, 3000, 5000, 12000, 14490]
   Y  = [0,  471,  880, 1408, 1689, 1953, 2376, 2844,  4114,  8192]
   f' =    2.355 2.045 1.320 0.703 0.440 0.352 0.234 0.181  1.638

mode 26 (ENGAGED)  3.0 km/h   Xcap 11400
   X  = [0,  190,  380,  763, 1200, 1800, 3000, 5000, 11400, 14490]
   Y  = [0,  462,  861, 1396, 1757, 2034, 2453, 2934,  4177,  8192]
   f' =    2.432 2.100 1.397 0.826 0.462 0.349 0.240 0.194  1.299

mode 26 (ENGAGED)  6.6 km/h   Xcap 10681
   X  = [0,  178,  356,  719, 1200, 1800, 3000, 5000, 10681, 14490]
   Y  = [0,  452,  839, 1382, 1838, 2131, 2546, 3043,  4245,  8192]
   f' =    2.539 2.174 1.496 0.948 0.488 0.346 0.248 0.212  1.036
```

Mode 24 is identical except `Y[8]` (4181 / 4228 / 4280) — no effect below `|gp-0x6b70|` = 4114.
`f'` near the origin is **2.36 – 2.54** and falls ~12x by 5,000 counts: a saturating assist curve.
Sanity check passes: `LERP(X[k]) == Y[k]` at all ten knots, every case.

### Inverting route 80's measured `|gp-0x6b70|`

| measured `\|gp-0x6b70\|` | 0 km/h | 3 km/h | 6.6 km/h | **creep range** |
|---|---|---|---|---|
| p50 = 320   |  136 |  132 |  126 | **126 – 136** |
| p90 = 2,534 | 3,675 | 3,337 | 2,965 | **2,965 – 3,675** |
| p99 = 3,059 | 6,185 | 5,644 | 5,076 | **5,076 – 6,185** |
| max = 3,187 | 6,891 | 6,303 | 5,681 | **5,681 – 6,891** |

(mode 26 shown; mode 24 differs by <2 % and only at p99/max.)

**⇒ `|iVar6|` reaches at most ~6,900 counts in the creep regime, and sits at ~130 half the time.**

The reason a modest `|gp-0x6b70|` inverts to a large `|iVar6|` is the saturation: above 5,000 counts
`f'` is only ~0.2, so 3,187 -> 3,187 is 39 % of the ±8,192 clamp but ~35 % of the reachable X axis.

---

## 6. What this does and does NOT bound

**BOUNDED [EVIDENCE]:** `|iVar6| <= ~6,900` at creep, `p50 ~130`. That is the LERP's own input,
`|gp-0x6bfe - (gp-0x374c>>4) + gp-0x6bfa|`.

**NOT bounded by this alone [stated plainly]:** `|gp-0x6bfe|` on its own.
`iVar6` is a three-term sum and the other two are not small in principle:

```
iVar6 = gp-0x6bfe  -  8 * polarity * SUM(w_i * lane_i / 1024)  +  gp-0x6bfa
        |<= 20000|    |<-------- structural max 212,992 ------>|  |<= 20000|
```
Per-lane structural maxima (all six weights `0xC63A0..0xC63AA` are stock 1024):

| lane | weight cal | lane clamp | max contribution |
|---|---|---|---|
| `gp-0x6bd0` | `0xC63A0` = 1024 | ±2,048  | 16,384 |
| `gp-0x6bbe` | `0xC63A2` = 1024 | ±2,048  | 16,384 |
| `gp-0x6b46` | `0xC63A4` = 1024 | ±1,024  | 8,192 |
| `gp-0x6b26` | `0xC63A6` = 1024 | ±1,024  | 8,192 |
| `gp-0x6b4e` | `0xC63A8` = 1024 | ±10,240 | 81,920 |
| `gp-0x6b4c` | `0xC63AA` = 1024 | ±10,240 | 81,920 |

(Prior finding, not re-derived here: `gp-0x6b4e ≡ 0` and `gp-0x6bd0 ≈ 0` measured —
`reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation`. That removes the two largest
rows structurally, but the remainder is still ~50,000.)

`gp-0x6bfe`'s own writer is `FUN_0003bc20` @`0x3bc3e`, sole writer, sole reader `0x38218`:
```c
sVar2 = *(short *)(gp - 0x6bfc);
if ((int)sVar2 + 20000U < 0x9c41) { flag = 0x400; }      // |x| <= 20000
else                              { flag = 0xffff; sVar2 = 0x7fff; }
*(short *)(gp - 0x6bfe) = sVar2;
*(undefined2 *)(gp - 0x695c) = flag;
```
So the writer's clamp is ±20,000 with a `0x7FFF` fault sentinel — **that is the number a naive
sizing would use, and it is 2.9x looser than the measured `|iVar6|` bound.**

**Honest statement for the next build:** if `gp-0x6bfe` is the dominant term (i.e. the Path-1
subtraction and `gp-0x6bfa` do not systematically cancel a much larger `gp-0x6bfe`), then
`|gp-0x6bfe| <~ 7,000` at creep and the field can be sized on ~7,000 rather than 20,000. That
premise is **BELIEF, not evidence** — it cannot be settled from the image. The measurement that
would settle it is telemetering `|gp-0x6bfe|` and `|iVar6|` simultaneously, or telemetering
`gp-0x374c>>4`. Sizing the field on ~7,000 while `gp-0x6bfe` can structurally reach 20,000 means a
clipped top ~3 % of the time at worst, and the clip is detectable in the data.

---

## 7. Corrections to the kit record

- **`docs/STATE.md` §A6b** — "the transfer cannot be read from the image" is FALSE and was already
  overturned; this trace additionally closes the *rescale* half of that claim. There is no runtime
  degree of freedom in this LERP at all.
- The framing that `f'` "swings >= 10x and cannot be pinned statically" (carried into the brief for
  this task) is **wrong**: the swing is exactly 1.000x. It arose from reading the `[204, 2048]` cal
  bounds as a live range without checking whether the inputs move. They do not.

## 8. Open / unverified

1. `|gp-0x6bfe|` vs `|iVar6|` decomposition — see §6. Needs a measurement, not a trace.
2. Whether any **bootloader-era** or **UDS** path can write `gp-0x6982`/`0x6984` before the app's
   `.data` copy runs. The `.data` copy at `0x1475C` runs in app init and would overwrite anything
   earlier, so this is closed for practical purposes; a UDS write *after* boot would need a base
   register formed by arithmetic (no literal exists) — **residual risk, judged very low**.
3. The highway regime was not inverted. The X cap (§4) drops to 7,000 above 50 km/h and the speed
   blend moves to `rec[3..6]`, so the creep numbers here do **not** travel.

**Scripts:** `analysis-2020accord/_v97/read_ram_lerp_provenance.py` (records dump, pre-existing);
the inversion script lives in the session scratchpad and is reproduced in full in the agent's report.
