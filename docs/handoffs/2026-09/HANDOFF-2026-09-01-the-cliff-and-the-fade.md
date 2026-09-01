# HANDOFF — 2026-09-01 — V277: the override cliff, softened

**Predecessor:** `HANDOFF-2026-09-01-reference-6x.md` (V276).
**Artifact:** https://claude.ai/code/artifact/0859e9d0-423c-41da-86fb-6e627db04aca

---

## What was asked, and what shipped

The operator asked for the override taper to kick in at **2.5× the driver torque**, noting himself
that it "should be a change in X points but Y points could be doable too, depending on the X values."

That instinct was right, and the ×2.5 design was **falsified before it flew**. What shipped instead,
on his decision, is a **cliff-softening**: the threshold stays where Honda put it and the dropout
becomes a linear fade. He separately directed that **variant-selector telemetry is the highest
priority channel**, which reshaped the tap.

---

## 🛑 THE FALSIFICATION — and it retires a long-open question

`FUN_00057f8e` is `i = 0; do {...} while (i < 0x10);` — only variant records **0–15** of the
0x24-stride table at `0xCD000` are ever searched. `FUN_00042692` writes byte `+0x1A` of the matched
record to `gp-0x674E` (`st.b` at `0x4272A`, the **one** writer image-wide), and `gp-0x674E` is a
**direct, unscaled word index** into every per-variant bank (`ld.bu` at `0x29AA0`, `shl 0x2` at
`0x29AAA`).

Byte `+0x1A` over those 16 records: **`{0,0,1,1,0,0,1,1,3,4,6,7,6,8,8,9}` — max 9.**

- **Taper and assist-map slots 10–27 are DEAD CALIBRATION.** So are slots 2 and 5.
- This **resolves** the open question in `accord-variant-selector-chain-0xcd000` — "record 2
  (slots 10/11) vs record 11 (24/25/26/27) UNRESOLVED, and it decides whether V112's dose is live":
  **NEITHER.**
- ⚠ **A LINEAGE RE-CHECK IS OWED.** Any earlier build that dosed only slots 10–27 dosed dead cells.
  This is the single highest-value follow-up from this session and it was **not** done here.

### What the live curve actually is

Three shapes are reachable. Only one is a cliff.

| shape | X | Y | banks | recs | character |
|---|---|---|---|---|---|
| **A** | 70,72,78,80 | 254,234,12,0 | `0xCBA04` + `0xCBA74` | 16 | **cliff: 99%→0% in 320 raw** |
| B | 32,38,80,112 | 255,255,255,0 | `0xCB8B4` | 8 | already a 1024-count linear fade |
| C | 32,42,80,112 | 255,255,255,0 | `0xCB924` | 8 | already a linear fade |

Sign agreement between LKAS command and driver torque picks the pair (`0x29A8E`); `gp-0x6803 == 2`
picks within it (`0x29A80`). Shape A is the mode==2 pair, **including the opposing-torque case** —
the actual override case.

**This is the firmware behind the operator's standing report that the assist does not fade under
load — it lets go.** The cliff sits at raw 2240–2560. His median override push is **2289 raw** — but note the
provenance: 2289 is r75's wire figure 2235 unit-converted, *not* re-derived. The census's own
override-conditioned median is the pooled **2819 raw** (index 88), which is eight steps *past* the
cliff's far end, in total dropout. The conservative figure is quoted; the pooled one drives the table.

---

## The edit — 16 records

```
X (70,72,78,80)   ->  (70, 84, 98,112)     kick-in raw 2240 UNCHANGED
Y (254,234,12,0)  ->  (254,170, 85,  0)    zero moves raw 2560 -> 3584
```

Widths 14/14/14, drops 84/85/85 — a near-straight fade. Zero lands at 112 because that is where
banks B and C **already** reach zero, so all four banks now share one full-override threshold
instead of the mode==2 pair cutting out 1024 counts early. The number is Honda's.

```
 raw  | idx | V276 | V277 |
 2240 |  70 | 100% | 100% |  kick-in — both curves agree
 2289 |  71 |  96% |  97% |  operator median push
 2560 |  80 |   0% |  76% |  stock full override — the dropout is gone
 2819 |  88 |   0% |  57% |  pooled median override
 3584 | 112 |   0% |   0% |  V277 full override
```

Asserted: authority ≥ V276 at every index 0–255 (this build only **relaxes**), and the new curve is
monotone non-increasing (more push never buys more assist).

---

## Telemetry — 34 bytes, two signals, one 10-bit field

```
wire = 0x10 | (gp-0x674E & 0x0F) | ((gp-0x674B >> 3) << 5)
  bits 3:0 selector (max 9, lossless) · bit 4 liveness beacon · bits 9:5 demand/8
```

`0x55DF0`–`0x55E11` rewritten **in place**, same length, `jarl 0x55E12` untouched. The room comes
from five instructions that are dead once the source is an unsigned byte (`jarl abs`, `mov r10,r6`,
`ori 0xffff`, `jarl min`, `andi 0xffff`).

**Verified at the decompiler level on the built image.** Ghidra emits, verbatim:

```c
FUN_00049a90(*(byte *)(unaff_gp + -0x674e) & 0xf | 0x10 |
             (uint)(*(byte *)(unaff_gp + -0x674b) >> 3) << 5, 0, 0x3ff);
```

Why both: the selector is **static**, so alone it could not observe any lever in this build. The
demand index is the taper's output and the assist map's input, live at loop rate.

**Caveats, on the artifact and in the docstring:** demand is quantised to 8 counts; it is a
**magnitude** (`subr r0,r7` at `0x29CFA` discards the sign, so the probe cannot tell left from
right); the cell holds its last value when the PID path does not run; and the selector names the
**slot**, not the part number — several records share a wire value, and an unknown part number
silently defaults to record 0.

---

## Corrections of record — these outlive the build

1. **`raw = wire × 1.024`.** `wire = -(raw * 125 >> 7)` (`FUN_00055C42` → `FUN_000218BE`). Never
   applied before. The "median override torque 2235, one count below the 2240 knot" figure was in
   **wire** counts and was **route r75's p50**, not a corpus median. Corrected: r75 = **2289 raw,
   above the knot**; pooled median within override = **2819 raw**.
   ⇒ `memory/accord/calibration/accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee.md`
   is **wrong on that line** and has not been edited — ask before changing it.
2. **The delivered ceiling is 3072, not 2505.** `0xC61BC` = 15360 sits on a different leg (after
   `sar 0x8`), not upstream of the forward gain. The binding clamp is `0xC61B4` = 3072. The ×6 claim
   survives **stronger**, but its provenance was also wrong: **stock `0xC6CD0` is `0xFFFF`, erased
   flash** — the 891 lives at `0xC646C`, and V112 *redirected the gain load* (`0x2A1F0` = `d0 7c`,
   stock `6c 74`) rather than changing one cell's value. What the load *reads* goes 891 → 5346,
   exactly 6.000000, against a clamp 512→3072 that really is one cell; both scale identically, so
   the knee is unmoved at 18830. ⚠ This is the ceiling of the path terminating at
   `gp-0x6b38`; that `gp-0x6b38` is the final motor torque is **NOT proven**.
3. **The 6-byte extended-displacement gp-relative form was decoded.**
   `disp[6:0] = (hw2>>4)&0x7F`, `disp[22:7] = hw3`; example `ld.h -0x4f60,gp,r6` = `84 07 07 32 61 ff`.
   A disp16-only scan missed **7 real sites** on `gp-0x4f60`; Ghidra separately missed 3. **Every
   prior "zero readers" null in this kit built on a disp16-only scan is suspect.**
4. **The `ld.hu` opcode gap.** A decoder covering only `ld.bu` (0x3C/0x3D) and omitting `ld.hu`
   (0x3E/0x3F) returns false zeros. Same warning class as (3).
5. **`0xC6974` (grab-rate) is 4 knots flat at 255** — inert. An earlier agent memory recorded it as
   5 knots ending at 0. Corrected in agent memory.
6. **`rlog-tools/lib/v95_rez_lib.py` cache autodiscovery still globs pre-reorg paths**
   (`<repo>/_cache_r*`), so `v95_override_exposure.py` and anything else importing it prints **empty
   tables with no error**. Not fixed here. **Worth a sweep.**

---

## The adversarial pass

Three agents, disjoint surfaces, each re-deriving from the image. **None returned do-not-flash.**
Every finding below was proven, not argued.

- **arithmetic** — exhaustive 256 × 112 monotonicity scan, zero step-ups; `andi 0xffff` provably a
  no-op (max product 65025); overflow margin 0.78% unchanged; sign-aliasing closed by the firmware
  itself (`subr` before the byte store).
- **build audit** — independent from-scratch rebuild matching both hashes, deterministic across four
  hash seeds; own zlib CRC walk on both chains; non-circular cipher test; **32 injected mutations**.
- **interlocks / packer** — Ghidra decompile of the rewritten window on the built image; register
  liveness proven from prologue/epilogue (r6/r7/r8 saved but **never restored** ⇒ dead scratch); the
  clamp's `in_r10` shown to be a cmov artifact; both deleted callees proven pure leaf; di/ei balance
  untouched; no branch target inside the window; no record aliasing.

### Defects they caught, all fixed

| defect | why it mattered |
|---|---|
| **slots 10–27 premise** | the build was aimed at records that never execute |
| **2492 pooled median** | load-bearing assertion passed **only because the constant was wrong** — the V274 pattern again |
| **`X_CEIL` self-referential** | a knot at 300 shipped silently at full PASS |
| **tap displacement unverified** | wrong cell *and* the odd-disp→`ld.w` trap both passed |
| **`SAR_NEW` unverified** | `sar 0x1` passed and would have broken the decode |
| **cipher guard failed OPEN** | renaming an attribute passed while printing "validated" |
| **`andi`/`ori` reg1 unchecked** | `andi 0x0f,r0,r6` → selector field **constant zero**, indistinguishable from a genuinely selector-0 car, beacon still reading 1 |
| **TAG said `X2.5`** | a flashable `.rwd` named after a withdrawn design |
| **"only branch in the window"** | false twice over; also never mentioned the two deleted `jarl`s |

Two opcode errors were caught **before shipping** by decoding written bytes and cross-checking each
opcode against a real instance in the same image: V850 `or` derived as 0x04 when it is **0x08**, and
`andi`/`ori` as 0x06/0x04 when they are **0x36/0x34**. Both would have written wrong instructions
into a flashable image. **That cross-check is now the standing method for any instruction edit.**

---

## Open, and deliberately not done

- 🛑 **The lineage re-check for slots 10–27.** Which past builds dosed only dead cells?
- **`gp-0x6b38` → motor.** Until closed, no page may say "max LKAS torque = 3072".
- **The golden model is still not updated** for the rate-loop findings, and now also lacks the taper
  and the selector-reachability result. The 87-symbol / SHA256 `740f4bcd…` contract needs a
  dedicated pass. Stated, not skipped.
- **`v95_rez_lib` path rot** (correction 6) and any other script importing it.
- **Register-indirect and `ep`-relative `sld`/`sst` access** remain uncovered by every scan method
  used here. All nulls in this session are scoped to that limit, explicitly.
- An agent called `save_all_programs`, committing `code.bin`, the V112 and V273 Ghidra programs to
  disk. It made no edits (dry-run reads only) and `git status` shows nothing changed under
  `ghidra_project`, but if another session held unsaved work there it is now committed.

## Safety

Nothing was flashed. **No CAN message and no UDS read was sent at any point.** All `.rwd` files
remain study artifacts until the operator names a file and a bus.
