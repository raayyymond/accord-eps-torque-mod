# HANDOFF 2026-08-07 (late) — V76 on a V38 base, and **the hard-fault mechanism found**: the friction lane crosses a flat 512-count ceiling that V73 unlocked.

**Session shape:** orchestrator + 8 subagents. Operator brief: a new **V76** superseding V76/V77 and all
V75+ variants — **V38 base**, damper raised toward V75, **FactorC flat (ReLU, no taper)**, **fix the hard
fault**, optionally an **8× LKAS V76B** if confidence allowed, plus **CAN telemetry targets** for what
remains.

---

## 1. ★★★★★ THE HARD FAULT IS EXPLAINED — and it was never the damper

`FUN_00036d74`, called **UNCONDITIONALLY** from `FUN_0002214a` @`0x2290a` (the 1 kHz control task —
`get_xrefs_to` returns exactly that one `UNCONDITIONAL_CALL`):

```c
fVar3 = (float)(int)*(short *)(gp - 0x6b26) * 0.0009765625;   // Q10
fVar2 = *(float *)(tp + 0x5004) * -1.0;
if ((*(float *)(tp + 0x5004) < fVar3) || (fVar3 < fVar2))
    FUN_000462e6(0x39bc, ...);                                 // -> FUN_00016de6(0x1d) -> HARD FAULT
```

`tp+0x5004` = **`0xC4004`** = float `0.5` = **512 raw counts** (bytes `0000003f`, **byte-identical in
stock / V38 / V72 / V73 / V74 / V75**). 🛑 **Flat, symmetric, unconditional — no re-sampled comparator,
no race, no timing escape.** If `|gp-0x6b26|` exceeds 512, it faults.

### The interlock, and its removal

`gp-0x6b26` (the **friction** lane) is clamped to ±`0xC407E`:

| build | ceiling `0xC4004` | clamp `0xC407E` | relationship | on-car |
|---|---|---|---|---|
| stock / V38 / V72 | 512 | **511** | **1 count UNDER — structurally untrippable** | clean, always |
| **V73** | 512 | **850** | **338 counts OVER** | clean (needed a big event) |
| **V74 / V75** | 512 | 850 | 338 over + friction table **×1.5** | **BOTH HARD-FAULTED** |

★★ **Honda set the clamp exactly one count below the monitor's own trip threshold. That is an
interlock — a clamped signal cannot trip its own fault check.** **V73 raised it to 850 and removed the
interlock without knowing it was one.** V74 then multiplied the mode-26 friction table `0xD7A54`
(`Y = [−9830,−5734,−1966] → [−14745,−8601,−2949]`) by 1.5, dropping the `gp-0x6c2c` needed to cross
512 from ≈ **6258** to ≈ **4180**.

### Why this fits when nothing else did
- **Mode-proof** (`0xC407E` has no mode index) ⇒ live in MANUAL. **The only candidate that can explain
  V74 faulting with LKAS disengaged.**
- **Single-frame latch** — flat check, threshold-0 dwell on fid 28/29 ⇒ trips on the first qualifying call.
- **Matches the build history exactly** — impossible on V38–V72, hard on V73, easy on V74/V75. Faults
  are new at V74.
- **Explains why every damper theory came up empty.** Wrong lane.

⚠ **Corrections to earlier framings in this same session:** the index is `gp-0x6a5e` (**vehicle speed**),
the multiplier is `gp-0x6c2c` (**filtered motor rate**); **bar torque appears nowhere in the arithmetic**,
and there is **no bare `sign()` flip** — the sign tracks `gp-0x6c2c`'s EMA value × an always-negative
speed coefficient, so a *monotonic rise* trips it as readily as a reversal.

### The fix
**`0xC407E` → 511.** One cell, mode-proof, restores the one-count margin, closes the manual exposure,
**loosens no monitor.** ⇒ **a V38 base gets it for free.**
🛑 Recorded as **RULE 11** in `BUILD-LINEAGE.md`: *a clamp may be an interlock — never raise one without
finding its monitor.* `0xC407E` is now a **DO-NOT-RAISE** cell.

⚠ **OPEN:** `gp-0x6c2c`'s physical scale is not derived, so whether ~4180 is an ordinary or extreme
motor-rate value is unknown. ⇒ the mechanism and the breach are **[EVIDENCE]**; *"this caused both
faults"* is a strong **[BELIEF]** resting on the build history.

---

## 2. What was eliminated on the way — and how

| candidate | verdict |
|---|---|
| **Damper slew** (orchestrator's own hypothesis) | **REFUTED.** Nothing writes `gp-0x6bd0` between the two samplings; the race is on `gp-0x6ac2`, the *ceiling's* index, and the check is one-sided. |
| **Surface A** (`FUN_00034350`/`FUN_000347b8`, ±5/1024 on `gp-0x6bd0`) | **UNREACHABLE.** The clamp binds only within 5 counts of the ceiling floor **512**; the damper has never been measured above ~448 (V75's `≥448` rung: **0/39,961**). |
| **`FUN_00045a20`** comp/bounds mismatch | **REFUTED** by a LERP-margin check — the term generator's gate is ~2–2.5× more conservative than the monitor's widen threshold. |
| **Monitor 1/2** (`FUN_00042af8`/`FUN_00043e44`) | Never read `gp-0x6bd0`, `gp-0x6b94` or any aggregator lane ⇒ cannot be sensitised by a FactorC/E edit. Their accumulators also charge over ~0.1 s, not threshold-0. |
| **`0xC63A0`** (V77's whole lever) | Cannot reach any monitor — **all three surfaces verified blind** (see `HANDOFF-2026-08-07-v74-fault-rlogs…`). V77 was a null experiment. |

★ The elimination is what produced the answer: **friction was the only V74 delta left standing.**

---

## 3. The build — V76 on a V38 base

**Base:** `_v38_plain_image.bin`, sha256 `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8`.
**Why V38:** it predates every mode-proof suspect, so the rebase reverts them **for free**:

| suspect | arrived | V38 value | on a V38 base |
|---|---|---|---|
| `0xC407E` (the interlock) | V73 | **511** | ✅ **the fault fix, free** |
| friction m26 ×1.5 | V74 | **stock** | ✅ reverted free |
| `0xC63A0` 1024→2048 | V72 | **1024** | ✅ reverted free |

⚠ It also drops `0xC62EA`=0 (V53, confirmed working) and V57's `0xC6CD0` decouple. **Measured cost of the
lockout restoration is small**: engaged below 5 km/h is **18.6 s = 3.06%** of engaged time, and only
**1.64%** of damper-live frames; the damper's work is at 5–35 km/h, above the window.

### The damper surface (mode 26 only; mode 24 byte-stock)
```
FactorC  X = [2240, 3840, 5120, 8960]   Y = [566, 566, 566, 908]     <- flat / ReLU floor-clamp
FactorE  X = [   0,  119, 2500, 4000]   Y = [  0, 300, 539, 927]     <- plateau REMOVED
```
`k` = **1.3866** · `M` = 165 · `max|gp-0x6bd0|` = 821.

| build | k(creep) | 5 | 20 | 35 | 60 | 80 | 140 km/h |
|---|---|---|---|---|---|---|---|
| stock / V38 | 0 | 0 | 0 | 0 | 3 | 6 | 14 |
| V74 | 0.580 | 50 | 50 | 50 | 27 | 50 | 106 |
| V75 flown | 1.580 | 137 | 137 | 137 | **56** | 104 | 220 |
| **V76** | **1.387** | **137** | **137** | **137** | **137** | **137** | **220** |

★ **V75's full creep dose held flat to 80 km/h** (2.45× V75 at 60 km/h) at **12% lower loop gain than the
build that faulted**.
★ **Grind-#2 separation — below V75 at every rate**: `0.57× / 0.61× / 0.76×` at 200/400/1200 counts
(42/85/255 °/s). Removing the `E_Y1 = E_Y2` plateau costs nothing at grind #1, which sits below the knee.
Still above stock there (5.40×/2.34×/1.40×) — unavoidable, since raising low-rate dose lifts a monotone
FactorE everywhere above it.

**Guards:** add-only vs stock proven exhaustively over **182,027,001** (speed, rate) points · mode 24
untouched, nearest other record **4,026 bytes** clear, `rec_len = 0x14` · strict-X ✓ · Y monotone ✓ ·
**`E_Y[0]` = 0 retained**.

🛑 **Two proven design facts worth carrying forward:**
1. **`dose / k = r − E_X0` exactly** — `C_Y0`, `E_Y1` and `E_X1` all cancel. **`k` is simultaneously the
   ramp slope, the loop gain and the per-count slew coefficient — one number, not three.** No table shape
   escapes it; deadbands make it strictly worse (they relocate the step to the `X0` crossing and enlarge it).
2. **`E_Y[0] > 0` is a Coulomb relay.** The index (`gp-0x6ac0`) and the sign (`gp-0x6abe`) are *different
   cells*, so a non-zero `Y[0]` gives constant magnitude with a rate-flipped sign — **±55 counts at every
   zero crossing plus a static bias with the wheel held still**, describing function `4M₀/(πA)` unbounded
   as amplitude falls. **Never raise it.**

**G3 override, flagged not silently passed:** `E_X0` = 0 rather than ≥12. At `E_X0`=12 the dose-137
solution is `E_X1`=200 — **V75 byte-for-byte at k=1.5798** — and `E_X0` 12→0 *lowers* the slope
(2.857→2.521/count, **k 1.571→1.387, −13.3%**), so the guard's stated rationale points opposite to its
effect. `E_Y[0]`=0 is retained, which is the hazard the guard was actually reaching for.

### The probe (COMBO B, 62/68 B)
| bit | predicate | can it fire? |
|---|---|---|
| 7 | `\|gp-0x6b26\| > 448` | **YES** — live band **449–511** under the 511 clamp. **Measures MARGIN on the fault lane.** |
| 4 | `gp+0x63fd & 0x2` | YES when engaged — **closes the mode-lag question** |
| 3 | `gp-0x67fa == 5` | YES — positive control (96.3% / 99.999% on two drives) |
| 6, 5 | clear | — |
| 2:0 | STEER_SENSOR_STATUS preserved | — |

🛑 **A structurally-dead bit was caught before it shipped**: the first design tested `≥ 512`, which under
the 511 clamp **can never fire on any drive** — the exact failure mode that wasted V64 and V68. Corrected
to **448**.
🛑 **`r10` is LIVE across the hook** (`0x55BDA` → `0x55C20`, after the cave returns). `r6/r7/r9/r15`
formally dead via `analyze_dataflow`. **Extent stays 68 B — caves are this kit's only bricking class.**
✅ Orchestrator byte-verified stock vs V38 identical over the hook container, the cave (virgin `0xFF`),
`FUN_00036d74`, `FUN_00036c12` and `FUN_00034350` ⇒ **all stock-based proofs carry to the V38 base.**

---

## 4. 🛑 The residual risk, stated plainly

**This build has NOT been shown to be safe.** The fault mechanism is addressed by construction, but:

| speed band | engaged time (route 61) | k on V74 (flew clean) | k on V76 | step |
|---|---|---|---|---|
| 35–45 | 93.0 s | 0.529 | 1.393 | 2.63× |
| 45–55 | 79.2 s | 0.423 | 1.393 | 3.29× |
| 55–65 | 55.6 s | 0.317 | 1.393 | 4.39× |
| 65–80 | 58.5 s | 0.482 | 1.393 | 2.89× |
| **total** | **286.4 s = 47.3% of engaged** | **0.449** | **1.393** | **3.10×** |

⊕ **Decomposition** (orchestrator-verified): the flat FactorC contributes **1.72×** (weighted V74 `C` 329
→ 566); the narrowed FactorE ramp contributes the rest. **The step is driven more by holding dose at 137
than by flattening C** — dropping to dose 110 would only reach ~2.84×. **Dose is the only real lever on
this risk.**

---

## 5. V76B / the 8× LKAS — **NOT BUILT**, and why

The operator gated it on *"if we are very confident with everything."* We are not.
- **The lever**: `0xC6CD0` 3564→7128 **plus** `0xC61B2`/`0xC61B4` 2048→4096 **in lockstep** (6 cal bytes).
- **Status: NEVER BUILT, NEVER FLASHED — untested, NOT falsified.** `7128` appears in exactly two files
  repo-wide, both feasibility docs from a single 2026-08-06 session; **zero build scripts, no on-car data.**
  The docs' own closing line: ***"Do not build or flash from this document alone."***
- **The clamp is the lever, not the gain.** Delivered LKAS = `gain/2`; V74/V76 sit at **1782 = 4.27× stock**,
  clamp knee **4.91×**, only **14.9% headroom**. Gain 7128 with the clamp left at 2048 delivers *identically
  to gain 4096* and flat-clips the top **42.5%** of command range — **worse than not raising it.**
- **GATE 2 open and never quantified**: 8× puts full torque at **~21 ms**, inside the 100 ms
  `steerActuatorDelay`.
- 🛑 **On a V38 base `0xC6CD0` reads `0xFFFF` (unwritten)** — V57 created that cell. **The 8× needs V57's
  decouple (`0x2A1F0` + `0xC6CD0`) carried forward**, or the LKAS gain sits on `0xC646C`, the 6-reader
  shared cell V57 exists to get off.

⇒ **Build V76B only after V76 flies clean and the `gp-0x6ace`/`gp-0x6acc` post-governor probe has run.**
One variable at a time.

---

## 6. CAN telemetry targets — what to instrument next

The V76 probe consumes 3 of 5 bits. Ranked targets for the **next** build:

| priority | target | closes |
|---|---|---|
| **1** | **`gp-0x6ace` / `gp-0x6acc`** post-governor pair | **The 8× GATE-2 requirement** — the feasibility docs' own standing recommendation, never done. Mandatory before any 8×. |
| **2** | **`gp-0x6c2c`** magnitude thermometer | The friction lane's own input. Gives the physical scale that is currently **the** open item behind the fault mechanism. |
| **3** | **`gp-0x6b94`** | Closes the golden-model gap — the aggregator's output does **not** reach `gp-0x6b98`, and 4 readers (`FUN_00036bec`, `FUN_0004503c`, `FUN_0004595a`, `FUN_0007ff08`) are unchecked. |
| 4 | `gp+0x63fd` full 5-bit value (not just bit1) | The exact mode sequence across a disengage, if bit4 proves ambiguous. |

🛑 **Every probe must keep a known-firing positive control** (`gp-0x67fa == 5` is ideal). This kit has
burned **three** flights on probes whose null was on the gate, and nearly a fourth this session.

---

## 7. Open, in priority order

1. **`gp-0x6c2c`'s physical scale** — `FUN_00041464`'s `gp-0x35a0 → gp-0x6c2c` EMA chain (α = 22/64 on
   `gp-0x4f50<<5`, final `>>9`), or the V76 probe's bit7 answering it by telemetry.
2. **The 3.10× exposure** at 35–80 km/h — only a clean flight resolves it.
3. **`gp-0x6b94 → gp-0x6b98`** — the golden model's chain is wrong as written; ≥1 unresolved hop.
4. **The mode-lag ROM mechanism** — `gp+0x63fd`'s multi-second hold; only debounce found is `0xC624E` =
   **40 ms**. Candidate is the `gp-0x6733 == −1` sentinel (`FUN_000527da`, callers register-indirect).
5. **Monitor 1/2 numerics** against the fault conditions — untraced.
6. **A DTC re-read** — `19 02 FF`, bus 1. 🛑 Operator confirmation of payload and bus required;
   **nothing was sent this session.**

---

## 8. Artifacts

`analysis-2020accord/builds/v50_v79/build_v76_v38base_tva.py` · `studies/sessions/v76/v76_surface.py` · `studies/sessions/v76/v76_cut_spec.py` · `studies/sessions/v76/v76_final_spec.py`
`studies/sessions/v74_v75/v74fault_extract.py` · `studies/sessions/v74_v75/v74fault_orchestrator.py` · `v74base_*.py`

**V76 — BUILT, VERIFIED, UNFLASHED:**
- rwd `39990-TVA,A160-V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd-0x13000-0x100000.rwd`
  sha256 `1fba57b243534538a7d533436387a98c673bf038dc579f9a3c6796d4c6030c89`
- image `_v76_v38base_relu_damper_plain_image.bin`
  sha256 `54a212a269623ef3d674fe7711eefdf7db32ebc3f25bf3e20c7bc5a14c830f33`
- V38 -> V76 = **8 runs / 91 bytes**, all attributed; **CRC 50/50 PASS** (2 trailers: `0xC4FFC`, `0xD7FFC`).
Superseded `.rwd`s renamed `SUPERSEDED-2026-08-07-BY-V76-V38BASE-…` (V76-old, V77, V77B); their plain
images keep their original names as evidence, per the V75 precedent.

### Build-phase catches worth keeping in the template
1. **`setfe r7` is 4 bytes (Format IX, `e23f0000`), not 2.** The probe listing had it as 2 B, which would have
   desynchronised every following instruction and produced a **malformed cave**. Caught before emission.
2. **Six instruction pins sat below `0x13000`**, where the plain image is all-`0xFF` — they existed only in
   `code.bin` and were uncheckable against the artifact actually flashed. The build script now **refuses any
   pin below `0x13000`**. Keep that guard.
3. **11 table bytes, not 12** (`FactorE X[0]` 60->0 changes only its low byte) — the same "count cells, not
   bytes" trap V77 hit.
4. **`ld.bu` encodes `hw2 = disp | 1`.** Grepping a cave for `gp-0x67fa` as `0698` returns a false negative;
   the real bytes are `0798`. The orchestrator hit this while verifying and the cave was correct.
5. **`> 448` was kept over `>= 448` deliberately** — gaining one count of a 64-count band would mean flipping
   `bgt`/`bge` condition nibbles, and inverting twins (`ba05`/`b205`) are a documented failure class here.
   **The bytes win; the documentation follows the bytes.**

⚠ **Environment:** anaconda **base** has a broken numpy and no `capnp`. Everything ran under
`C:\Users\dudei\anaconda3\envs\bin_decompile\python.exe`.
