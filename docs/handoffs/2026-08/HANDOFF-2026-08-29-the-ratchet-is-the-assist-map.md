# HANDOFF — 2026-08-29 · THE RATCHET IS FIRMWARE-CREATED, AND IT IS THE ASSIST MAP · **V168 BUILT**

> 🚩 **PARTIAL — covers only the first third of 2026-08-29.** The complete session handoff is
> `HANDOFF-2026-08-29-the-assist-map-session.md`: seven builds, the notch structure, the
> scorer defect, the r26 gate, the ring-down negative and the full open-items list.
>
> 🛑 **AND ITS CENTRAL CLAIM IS CORRECTED THERE**: this document says the ratchet *“has not
> moved across thirty-plus builds”* (ρ = −0.14, p 0.787). **That was an n=5 artefact.** On the
> full corpus (n=11) the ratchet gives **ρ = −0.60, p 0.052** against the grind's −0.84 — both
> fall, the grind more strongly. Body left unedited as the record of what was believed.


> **Read `docs/STATE.md` first.** This is the narrative; STATE is the live state. Everything here is
> committed and pushed on `main` in both repos.

---

## 0. THE ONE-PARAGRAPH VERSION

The session began by finding that **three of this kit's own measurement instruments were artefacts**,
rebuilt the endpoint on a slope-matched null, and with the corrected instrument established that **the
ratchet is 100 % firmware-created, engaged-only, lives in the TORQUE channel rather than wheel rate,
and has not moved across thirty-plus builds** — while the grind falls monotonically over the same
builds. Those two facts dissociate the symptoms. Tracing the dominant torque-fed lane led to the
**base power-assist map**, whose slope cap `0xC6384` **binds** and is **byte-identical on all 161
images**. GATE 2 passes. **V168** is built and unflashed: V158 + that one cell.

---

## 1. WHAT IS ON THE CAR, WHAT IS BUILT

| | build | state |
|---|---|---|
| on the car | **V122** | the flying reference for every measurement here |
| built, unflashed | **V158** | damper shape (grind lever) |
| **built, unflashed — FLY THIS** | **V168** | **V158 + `0xC6384` 2048→1536** (ratchet lever) |
| built, unflashed | V167 | Path-2 damper weight, the "worse" branch |

```
V168  image 058dd64ac442ef43c790965c9a5fc011f147f7ff0a5e7cd0c0d1bb8889c7b0ff
      .rwd  0f0ace3b5bc0a8541227e06c831c555797566374b298ba606614f5a09a1356f1
```
Both repos clean and pushed. Drive card: `docs/scoring/DRIVE-CARD-V168.md`.

---

## 2. 🛑 THREE INSTRUMENTS WITHDRAWN — the wheel-rate signal is RED

Coloured noise with **no resonance at all** reproduces what the kit's measures reported:

| control (NO resonance) | prominence | fitted Q | fit r² |
|---|---|---|---|
| 1/f^1.5 | 27.4 | 1.00 | 0.585 |
| 1/f^2.0 | 64.9 | 1.00 | 0.710 |
| real routes | 12.2–173.3 | 1.0–17.6 | 0.28–0.87 |

Withdrawn: **fixed-floor prominence** (large by construction on a red spectrum), **fitted Lorentzian
Q**, and **long-window half-power Q** (white noise alone returns Q 21.7–29.1 and cannot separate true
Q=5 from Q=20). The routes' slopes run **1/f^0.80 to 1/f^2.37**, so the tilt alone moves any
band-power measure by 6×.

**What survives:** excess over the route's *own* fitted power law, nulled at that route's *own*
slope. `rlog-tools/score/score_band_excess.py`.

⚠ **A retraction of a committed inference rule.** The V158 pre-registration said *"Q rising above
4.50 falsifies the damping account"*. Half-power Q is **non-monotone** — its null sits **above** the
data (real 13.7–34.7 vs null p95 58–78) — so a rise cannot distinguish "damping failed" from "damping
worked". Excess is monotone and does not have this defect.

---

## 3. ⭐ THE RATCHET, CHARACTERISED PROPERLY FOR THE FIRST TIME

**It is in TORQUE, not wheel rate.** Margin over each channel's own slope-matched null:

```
tq 7.62 · cs_tq 7.42 · ws_fr 4.41 · ws_fl 3.95 · cs_rate 1.03 (CHANCE)
ang/wang/cs_ang 0.79-0.83 · sc_tq 0.56 · co_tqcan 0.59 · cc_req 0.67
```
⇒ **every 6–9 Hz endpoint this kit has ever used read the wrong channel.** Real on **9/9 routes** in
`cs_tq`. Absent from all three command channels.

**It exists only when engaged** — engaged arm clears its null **7/7**, manual arm **0/7** (manual sits
*below* its own null every time), speed-matched ratio **median 19.9× [4.82, 35.64]**. So engagement
**creates** it; it is not a mechanical mode being amplified. *(This supersedes the recorded 2.8×,
which came from the tilt-confounded band ratio.)*

**And nothing the kit has done has moved it.** Post-V102 ρ = **−0.14 (p 0.787)** against a floor that
would have shown 1.9×; frequency pinned at **8.64 Hz ± 7.4 %** across V91→V122. Meanwhile the
**grind falls ρ = −0.94 (p 0.005) in three independent channels.** ⇒ **the symptoms dissociate**, and
every lever found so far is the grind's.

**The Coulomb relay is exonerated for the ratchet.** Its knee spans 10× across the scored routes with
ρ = −0.06 (p 0.874); gain-matched, knee 300→1800/3000 cuts the **grind 2.8×** and moves the
**ratchet 1.18×**, inside its own 1.63× floor. It remains a good grind lever.

---

## 4. ⭐⭐ THE SUSPECT: `gp-0x6b86`, THE BASE POWER-ASSIST MAP

Two independent routes converge. From the data: firmware-created, engaged-only, in torque, untouched
by all 278 bytes the kit changed V91→V122. From the code (a prior tracer's loop census, re-read and
confirmed): `Z = (Z0+P·F)/(1−P·L)`, the loop cancels ~93 % of the mode's damping, and `gp-0x6b86` is
the **largest torque-fed term** — ±0x3000 window, **5.8–7.8× the entire PID**.

**The curve was never unreachable.** It is initialised data copied ROM→RAM at boot, which is why only
3 `st.h` target the 20-knot block and 2 of those are `st.h r0` clears. Found by its required shape:

```
0xCE47A  X 0 25 60 100 150 250 450 900 1800 4150
         Y 0 154 338 460 549 635 702 766 824 857
         slope 6.16 5.26 3.05 1.78 0.86 0.34 0.14 0.06 0.01   cap 2.000 BINDS 3/9 over X 0-100
0xCF372  max 16.37  binds 4/9      0xCF3CA  max 11.97  binds 3/9    (+3 duplicates)
```
All six records byte-identical across 161 images. **The cap pins the map's small-signal gain at
exactly 2.000 — the CEILING value of `s` in the census.**

### GATE 2 — anchored on the MEASURED Q ratio
The census phase (−148°) with `P` real-positive gives `|1−P·L| = 1.92 > 1`, a loop that *adds*
damping — contradicting the measured 93 % cancellation. `P`'s phase is not in the image and the sign
depends on it, so anchor on the measurement:

```
Q_eff/Q_passive = 14.3  =>  |1-P.L| = 0.0700  =>  P.L = 0.9300   [ASSUMPTION: P.L real-positive]

cap    s       |L|     |1-P.L|   Q ratio    vs stock
2048   2.000   2.825   0.0700    14.29      stock
1536   1.500   2.325   0.2346     4.26      3.4x MORE DAMPED   <- V168
1024   1.000   1.825   0.3992     2.50      5.7x
```
**MAGNITUDE passes. PHASE passes** — the term is a real gain, so lowering the cap scales `|L|` without
rotating it ⇒ monotone, no reversal at any value.

### It also accounts for engaged-only
With `P` calibrated from the **engaged arm alone**, the manual arm is *predicted*: engaged |L| 2.825
⇒ Q ratio 14.29; manual |L| 2.000 (the engagement-conditional lanes drop out) ⇒ **2.93**. Predicted
engaged/manual **4.88** vs measured **19.9 [4.82, 35.64]** — consistent, at the lower edge.
**[BELIEF — the census's per-lane magnitudes carry their own assumptions.]**

### It cannot touch LKAS  [EVIDENCE]
`0xC616C` = 0 on stock and all 161 images ⇒ a clamp with limit 0 annihilates its input ⇒
`gp-0x6b76 ∈ {0, 0x7FFF}` and 0x7FFF exceeds `FUN_0003405a`'s own 20480 gate ⇒ `gp-0x62e0[] ≡ 0` ⇒
`gp-0x6298[] ≡ 0` ⇒ **`gp-0x6b4a ≡ 0`**. The map is fed by the driver torque sensor alone.

---

## 5. THE DRIVE SPEC COLLAPSED TO ONE EPISODE

The earlier 8×15 s spec was **unbuildable** under the design law and aimed at the wrong statistic.
The engaged/manual result is **presence/absence**, so killing the ratchet is an **~8× move**, not
1.7×:

```
15 s episode -> 5 windows -> ratchet detected 11/11 = 100%   (20 s: 5/5 · 30 s: 4/4)
excess 25.5-155.7  vs null 1.9-4.9  =>  5-65x margin
```
**One continuous 15 s engaged creep pass answers the primary question.** Stop as soon as you know.

---

## 6. OPEN ITEMS, WITH WHAT WOULD CLOSE EACH

- **Driven vs self-excited: INCONCLUSIVE.** Band-specific coupling (`co_tqcan`→`cs_tq`, ratchet band
  minus a 30–40 Hz control band, vs phase-shuffled surrogates) is specific on 6/9 routes but the
  pooled 95 % CI **[−0.021, +0.176] crosses zero**. `r1e`, the only route with 14 windows, gives
  **+0.522 vs a shuffled p95 of +0.097** — an underpowered real effect, not a null. **Closes with
  more continuous engaged-creep windows.** ⊕ Raw coherence is worse than useless here: the control
  band scores as high as the ratchet band, so command→torque coupling is broadband.
- **The `P·L` real-positive assumption.** **Closes on the V168 drive itself** — an unchanged excess
  falsifies it.
- **The assist-curve initialiser is unlocated.** Both byte-scan leads ruled out (store-zero clears at
  `0x38FD0`/`0x38FEE`; a fade-to-zero blend at `0x39A0C` toward `0xC6564`, which is 0 on all 161
  images). Not blocking — the curve was found in the ROM image directly.
- **`gp-0x69a6`** already holds the running max of the capped per-segment slope ⇒ a **one-cell
  telemetry read** would confirm cap-binding on-car if ever wanted. Not needed now: the static read
  settled it.
- **The 13-engaged-modes claim** for V158's damper edit is still unreconciled (it edits 26/27).

---

## 7. METHOD NOTES WORTH KEEPING

- **`search_instructions` returned ZERO** for stores into the knot block; a raw LE byte scan across
  both gp encodings found **27 accesses**. The documented undercount, again — the null was false.
- **`0xC6520–0xC6560` is a float32 array stored as (lo16,hi16) halfword pairs** (`0 16840` = 25.0).
  A naive u16 read of that neighbourhood looks like noise.
- **The hardcoded payload-byte assertion fired again.** `0x0800 → 0x0600` changes the **high byte
  only**, so V168's payload is **1 byte, not 2**. The build now asserts the **value**.
- **Never nest a file read inside the call that opens it for writing** — `io.open(p,'w').write(
  io.open(p).read()+x)` truncated `MEMORY-PART6.md` to 1 KB mid-session. Caught and restored from
  `540c00a3`, 84 pointers intact.
- Two of my own numbers were wrong and are corrected in place: a 40-byte window check on `0xC6384`
  spanned `0xC63A0`/`0xC63AC` and falsely suggested the cap had 5 variants (it has one), and the
  first GATE 2 pass used a census phase that inverts the sign of the whole result.
