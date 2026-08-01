# HANDOFF 2026-08-01 — grind #2 is V62's own fix, seen at high frequency

**★★★★ THE RESULT: one knob cut grind #1 by 2.9× and raised grind #2 by 11.7×.** V62's
`sar 0xa → sar 0x9` on the torsion-bar rate lane is not a fix with a side effect; it is a **broadband
high-frequency amplifier with a crossover at 22–24 Hz**, and both symptoms are the same edit read at
two frequencies.

Read alongside `docs/V66-V67-DESIGN.md` (the full design), `docs/STATE.md` (current state) and
`docs/BUILD-LINEAGE.md` (V66's row).

---

## What the operator brought

Two new routes, both on **V65** (= V62's control-path edits byte-identical + the saturation-ladder probe):
- **`3a` (`4e55c1e0f4`, 7 segs)** — parking lot, then **grind #2 demonstrated with LKAS ON**.
- **`3b` (`a4a7f4dbf1`, 14 segs)** — parking lot, **grind #2 demonstrated with LKAS OFF**, then
  unrelated highway lateral tuning.

Operator's description: *"mostly happens at low speed while I (not LKAS) am commanding significant
wheel turn… sometimes the same resonance at 10–20 mph on semi-hard turns… makes the entire car
vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."*

---

## ★★★★ The band table — the root-cause identification

Corner-conditioned extreme-tail maxima (corner = creep ∧ |driver torque| ≥ 1200 ∧ |angle| ≥ 100°),
Kd = 1× vs Kd = 2×, 219 blocks:

| band | Kd=1× | Kd=2× | **ratio** | p |
|---|---|---|---|---|
| 1–4 Hz (driver) | 4709 | 4763 | **1.01** | 1.00 |
| 6–9 Hz (ratchet) | 2773 | 3335 | 1.20 | 0.037 |
| 10–16 Hz | 2520 | 2005 | **0.80** | 1.00 |
| **18–22 Hz — GRIND #1** | 3656 | 1269 | **0.35** | 1.00 |
| 24–28 Hz | 485 | 1289 | **2.66** | 0.013 |
| 30–40 Hz | 373 | 1113 | **2.98** | 0.013 |
| **40–49 Hz — GRIND #2** | 301 | **3526** | **11.71** | **0.0003** |

**Monotone, with a crossover between 22 and 24 Hz, and the driver band flat at 1.01 as a control.**
Not generic roughness.

✅✅ **The comma IMU reproduces it on a sensor that shares no path with the EPS** — first use of the IMU
in this kit. Same corner, Kd=2×/Kd=1×: 1–4 Hz p95 **0.76** · 18–22 Hz 1.20 · 24–28 Hz **0.65** ·
30–40 Hz 1.25 · **40–49 Hz p95 6.27, max 6.71**. Medians ~1 everywhere (the phenomenon is in the tail).
⚠ The IMU does **not** show grind #1's reduction and its grind-#1 positive control is weak — a real
limitation, but coherent: grind #1 is a **torsional column mode** that need not reach the chassis;
grind #2 is the one the operator says shakes the whole car. **The IMU's selectivity matches the
operator's own description of which one shakes the car.**

## The mechanism, predicted from the arithmetic before the test was run

`gp-0x4f62` is a **4-sample finite difference at 1 kHz** — `2*(x[n]−x[n−4])/4`, delay cal `0xC6C42` = 4,
byte-read. A differentiator's gain **rises** with frequency: **1.93×** at 41.6 Hz and **2.60×** at
58.9 Hz relative to 20.9 Hz. V62's ×2 is **flat in frequency**, so it raised the high band harder, in
absolute terms, than the mode it fixed. V62's build note computed selectivity only against the
**driver** (1 Hz, 14.6:1) and never against a **higher** mode, where the ratio runs the wrong way.
`analysis-2020accord/rate_lane_frequency_response.py`.

The measured slope is steeper than the lane alone predicts because the plant carries a lightly-damped
mode at **~44.9 Hz, Q ≈ 37** that the extra loop gain pushes past its stability threshold — hence
**bursts** rather than a hum, and **zero** bursts at Kd = 0 and Kd = 1×.

## 🛑 A filter cannot fix this — structural, not numeric

A differentiator rises at +20 dB/dec; one real pole falls at −20 dB/dec, so the cascade is **flat**
above the corner. A single pole drives the 41.6/20.9 selectivity toward 1.0 and **can never push it
below**. Two poles low enough to bite by 42 Hz cost ≈2·atan(20.9/fc) at 20.9 Hz — at fc = 20 Hz that is
**−92°**, turning the lane's +75° lead into −17° and **destroying the damping V62 bought**. Raising the
delay cal `0xC6C42` fails identically (D = 24 zeroes 41.7 Hz but leaves −0.3° at 20.9 Hz = a pure
spring). **Do not re-propose either.**
✅ Independently confirmed structurally: `gp-0x4f62`'s producer `FUN_0007e74a` contains **no EMA or IIR
anywhere** — the "dirty derivative" does not exist in stock and would have to be built, i.e. a cave.
✅ And there is **no V57-style cal fork**: the torque sensor `gp-0x4f60` is a *single physical
measurement* of driver and motor-reaction torque combined, so no earlier tap separates them.

⇒ **The separation must come from an operating condition.**

## What separates the two symptoms

| discriminator | grind #1 | grind #2 | separation |
|---|---|---|---|
| **driver torque** | hands-off | `tq_avg` **1600–2700**, \|angle\| 150–265° | **>8×** ★ |
| **LKAS engagement** | top-decile creep windows **100%** engaged, p99 **6.63×** | 84.5% vs a **54.7% base rate**, p99 **1.33×** | grind #1 only |
| steering rate | med 128 counts | med 256 counts, **p90s overlap** (359 vs 371) | ~2× only |

🛑 **Gating on LKAS alone cannot remove grind #2** — it is barely engagement-associated. The operator's
*"make it LKAS-dependent"* requirement was formed before this was known; it still matters for not
disturbing base steering, but it is **not sufficient on its own**. **Driver torque is the axis.**

---

## ★★ The lever: the firmware already has a conditional-gain arm, wired to a dead cell

Orchestrator-verified first-hand (Ghidra + a raw byte scan with per-opcode displacement rules):

- `gp-0x683c` has **exactly ONE access image-wide** — `ld.bu -0x683c[gp],r15` @`0x3AA94`, bytes
  `84 7f c5 97` — and **ZERO writers**, in both encodings, at every byte offset.
- Its only consumer is `cmp r0,r15` @`0x3AAA6` → `setfne lp` @`0x3AAA8`; **r15 is dead after that**.
- `lp` gates **both** lanes: r24 `ld.hu 0x7446[tp]` @`0x3AC08` (cal `0xC6446`) and r26
  `ld.hu 0x7444[tp]` @`0x3AB5E` (cal `0xC6444`) — **one reader each**, CAL block `[0xC6000,0xC6FFC)`.
- Priority: `gp-0x671d` **outranks** it (→ `0xC6442` = 1024), then `lp`, then `gp-0x671a ≥ CEIL`.
- Arbitration (`FUN_00028ea6` @`0x22522`) runs **before** the aggregator (`FUN_0003aa2c` @`0x2291E`).

⇒ **Repointing that one load is a ONE-BYTE edit** (`0x3AA96`, even displacements only) that makes the
rate-lane gain conditional on any gp byte cell — **the only conditional-gain surface here that needs no
code cave**, and caves are this kit's only bricking class.
```
0x3AA94  84 7f c5 97   ld.bu -0x683c[gp],r15    current
0x3AA94  84 7f fb 97   ld.bu -0x6806[gp],r15    repointed -- only 0x3AA96 moves
0x02A1B6 84 67 fb 97   ld.bu -0x6806[gp],r12    a REAL instruction, differs only in reg2
```

**V67** = keep `sar 0x9`, repoint the gate, set `0xC6446` = **1536** (with ÷512 that is 3.0, exactly the
stock creep gain 3072/1024). Driver light ⇒ LERP × 2, grind #1 stays fixed; driver cranking ⇒ flat
stock, grind #2's regime removed.
🛑 **V67 is BLOCKED on a chatter measurement.** The oscillation puts **±1400 counts** on the torsion
bar; `gp-0x67f5`'s sustain is **10 ms** against a 21 Hz half-period of 24 ms, so **the mode's own
amplitude may satisfy it** and switch the gain at the mode frequency — a parametric pump, the exact
failure mode V58/V59/V60 chased for three builds. **That is V66's job.**

---

## ✅ V66 — BUILT, VERIFIED, AND IT IS THE RECOMMENDED NEXT FLASH

**V65 with both `sar` immediates reverted to stock + a 3-bit gate probe.** Exactly the operator's spec —
V38 4× LKAS reach, steer-to-zero, stock rate lane, live telemetry — and simultaneously the
**confirmatory revert** and the **pre-flight probe for V67's gate**.

Probe on `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6806 != 0` · **bit5** `gp-0x67f5 != 0` ·
**bit4** `gp-0x683c != 0` (the control — must read 0 in 100% of frames).

**61 bytes off V65**, restricted to `[0x13000,0x100000)`. ⭐ **CAL block byte-identical to V65**,
`0xD2000` block identical, **all four** mode-10 `gain_B` records unchanged = machine proof no
calibration moved. `0x3AB70` still `sar 0xa`. **`gp-0x683c`'s load UNCHANGED** — V66 must not carry
V67's repoint, and it does not. 50/50 CRC; x31 checksum PASS; **the RWD decodes exactly back to the
image**. GATE 1 vacuous. 62/68 cave bytes.
⭐ **Orchestrator-verified independently from the built image**, cave re-decoded from the bytes.
🛑 **Only three probe bits fit** (a 4th rung is 12 bytes against ~6 spare) ⇒ `gp-0x671d` and
**`gp-0x67fe`** are unmeasured.

Image SHA `56177c189deb2533c334cc465b2c7e465191c68f63df1f6cf7316ef6459acf6f`
RWD SHA `2725908e22157512cc0548663a9d15f1ef9ff7495a74fd92846602dc9db8fa04`

**Pre-committed interpretation** — see `STATE.md` step 0. Briefly: grind #2 gone ⇒ attribution closed,
build V67. Grind #2 still there ⇒ the rate lane is the wrong tree and **V62 should go back on**.
bit5 toggling at 15–60 Hz ⇒ that gate is dead. bit4 ever 1 ⇒ cancel the repoint.

---

## Record corrections made this session

- ★ **`FUN_0003ad74` resolves r24's `gain_B` through FOUR SEPARATE POINTER ARRAYS** (`0xCBF5C`,
  `0xCC044`, `0xCC12C`, `0xCC214`, each at `mode*4`) → for mode 10, records `0xD2A74` / `0xD2AB0` /
  `0xD2AEC` / `0xD2B28`. **Not four consecutive records** — reading them consecutively from `0xD2AEC`
  picks up mode 11's interleaved rows and **understates the rolloff by 2×**. `gain_A` (r26) is **not**
  mode-indexed. Cross axis is `tp+0x7010` = `0xC6010`. Golden model updated.
- ★ **At creep the r24 gain is 3072, not 2305.** The oft-quoted 2305 is the **50 km/h** record. Any ×2
  sizing must use 3072.
- ⚠ **`build_v62_tva.py`'s `GAIN_B_LERP_MODE10` tripwire watches only 2 of the 4 records** — blind to an
  edit landing on `0xD2A74` or `0xD2AB0`.
- ⚠ **`gp-0x67a4` is not "zero readers"** — 1 writer + 1 reader, and it is a **saturation-dwell** monitor
  on the LKAS command's clamp ceiling, not an engagement flag.
- ⚠ **`gp-0x67fe`'s semantics are DISPUTED** — a trace calls it the LKAS engage-SM state; the golden
  model calls it `assist_substate`, i.e. **base** assist, in which case it is worthless as a gate.
  **Unresolved, and unmeasured by V66.** Close it with a probe, not an argument.
- 🛑 **Two claims I made mid-session and withdrew**, both caught by checking rather than by an agent:
  a "6.6× steering-rate separation" that was a top-25 selection letting grind #1's road-speed windows
  in (real value ~2× at creep, p90s overlapping), and a phase-based "dirty derivative fixes it" table
  that used the *lane's* own phase while the on-car sign says the plant supplies the rest.

## 🛑 Methodology: the mean and the tail disagreed in SIGN on the same data

Matched-cell episode-bootstrapped mean: 30–49 Hz **0.913 [0.791, 1.026]** — inside the null floor, a
confident **null**. Extreme tail: **27/219 blocks vs 1/91**, max **325 → 4046** — a confident
**positive**. **Both were misleading alone.** The matched q99 threshold was **317** against burst
amplitudes of **3000–4000**: the mean test was structurally blind. And the census was uncontrolled for
exposure, with two of three high-dose routes **driven specifically to provoke the symptom**.

Resolved by measuring exposure directly: the low-dose arm had **105.3 s** in grind #2's corner against
V62's **49.8 s** — *more than twice* — and produced **1** burst block against V62's **9**. *"They never
went there"* is refuted.

⇒ **Report the mean and the tail together, print the tail thresholds next to the event amplitudes, mark
provoked routes, and report exposure in seconds in the conditioning corner.** This is the third distinct
way this kit has manufactured a wrong effect size from correct arithmetic; all three share a root —
**a statistic computed correctly over the wrong population.**

## 🛑 The alias is unresolved, and it does not block anything

CAN is a ~100.5 Hz grid ⇒ Nyquist 50 Hz, so **44.9 Hz and ~55.6 Hz are the same observation**. The IMU's
median rate is **~101 Hz** — only 0.5 Hz from CAN — so **IMU/CAN frequency agreement carries no
information about the alias** and must never be quoted as if it did. A dedicated fold test and a
Lomb–Scargle test on true arrival timestamps both came back **underpowered** (the latter leans weakly
toward the lower candidate; separation only 1.07–1.27). Recorded as open. Every candidate fix ranks
identically for both candidates, because the lane's problem is a **selectivity ratio** that is bad at
both.
