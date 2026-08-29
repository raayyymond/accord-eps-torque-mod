# HANDOFF — 2026-08-29 · **THE ASSIST MAP SESSION** · three instruments withdrawn, seven builds cut

> **Read `docs/STATE.md` first.** This is the narrative; STATE is the live state. Everything here is
> committed and pushed on `main` in both repos. This supersedes
> `HANDOFF-2026-08-29-the-ratchet-is-the-assist-map.md`, which covers only the first third.

---

## 0. THE ONE-PARAGRAPH VERSION

Three of this kit's own measurement instruments turned out to be artefacts of a spectral tilt. With a
validated replacement, **the ratchet is firmware-created, engaged-only, lives in TORQUE not wheel
rate, and falls only WEAKLY across builds where the grind falls strongly** — see the correction in
§3. That led to the **base power-assist map**, the largest torque-fed term in
the aggregator, whose slope cap and second-order section had never been touched. **Seven builds are
cut.** Fly **V173**. Every remaining lever is priced **below the measurement floor**, and the one
assumption the levers share is — demonstrably, after three estimator families failed — **testable only
by driving.**

---

## 1. WHAT IS ON THE CAR, WHAT IS BUILT

| | build | state |
|---|---|---|
| on the car | **V122** | the reference for every measurement here |
| **FLY THIS** | **V173** | V158 + assist-section **poles**, Honda's 55 Hz notch kept. 3 cells |
| alternative | V172 | same poles, all four cells — **9.6× grind** but loses Honda's notch |
| alternative class | V168 / V169 / V170 / V171 | slope cap 1536 / 1792 / 1280 / 1024 |
| grind lever alone | V158 | damper shape, the base of all the above |

```
V173  image a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7
      .rwd  5d213cf8604df90f2df2eaa2a8e40ccedde89f1d66055cb2a22c81edb7245396
V172  image ff8d07e6…  V171 image e3cbc92d…  V170 image 0c923c36…
V168  image 058dd64a…  V169 image ed9e5fec…  V158 image 42078806…
```
All seven re-hashed from disk at close-out. Both repos clean. Decision table:
`docs/scoring/BUILD-INVENTORY.md`. Card: `docs/scoring/DRIVE-CARD-V173.md`.

---

## 2. 🛑 THREE INSTRUMENTS WITHDRAWN — the signal is RED

Coloured noise with **no resonance at all** reproduces what the kit's measures reported:

| control (NO resonance) | prominence | fitted Q | fit r² |
|---|---|---|---|
| 1/f^1.5 | 27.4 | 1.00 | 0.585 |
| 1/f^2.0 | 64.9 | 1.00 | 0.710 |
| real routes | 12.2–173.3 | 1.0–17.6 | 0.28–0.87 |

Withdrawn: **fixed-floor prominence**, **fitted Lorentzian Q**, **half-power Q** (white noise alone
returns Q 21.7–29.1 at nperseg=1024 and cannot separate true Q=5 from Q=20). Route slopes run
**1/f^0.80 to 1/f^2.37**, so tilt alone moves any band measure by 6×.

**What survives:** excess over the route's *own* fitted power law, nulled at its *own* slope.

⚠ **A committed inference rule was retracted.** The V158 pre-registration said *"Q rising above 4.50
falsifies the damping account"*. Half-power Q is **non-monotone** — its null sits **above** the data
(real 13.7–34.7 vs null p95 58–78) — so a rise cannot distinguish "damping failed" from "damping
worked". Excess is monotone.

---

## 3. ⭐ THE RATCHET, CHARACTERISED

- **In TORQUE, not wheel rate.** Margins over each channel's own null: `tq` 7.62 · `cs_tq` 7.42 ·
  `ws_fr` 4.41 · **`cs_rate` 1.03 (CHANCE)** · angle 0.79–0.83 · command 0.56–0.67.
  ⇒ **every 6–9 Hz endpoint this kit ever used read the wrong channel.**
- **Engaged-only.** Engaged arm clears its null **7/7** routes, manual **0/7**, speed-matched ratio
  **19.9× [4.82, 35.64]**. Engagement *creates* it. (Supersedes the recorded 2.8×.)
- **The grind is engaged-only too** — **0/7** in manual. Both symptoms are firmware-created by
  engagement; they differ in frequency and levers, **not in class**.
- 🛑 **CORRECTED — both symptoms fall post-V102, the grind more strongly.** An earlier reading here
  said the ratchet was *untouched by 30+ builds* (ρ = −0.14, p 0.787). **That was an n=5 artefact.**
  On the full corpus with build attribution recovered (n=11): **RATCHET ρ = −0.60 (p 0.052)** vs
  **GRIND ρ = −0.84 (p 0.001)**; hard-attributions-only (n=7) gives −0.59 vs −0.76, so the effect
  size is unchanged and only the p-value moves with n. ⇒ **a difference of DEGREE, not of kind**, and
  the ratchet is **demonstrably reachable**. Frequency still pinned at **8.64 Hz ± 7.4 %**.
- **The Coulomb relay is exonerated for it**: knee spans 10× with ρ = −0.06 (p 0.874). Gain-matched,
  knee 300→1800/3000 cuts the **grind 2.8×** and moves the **ratchet 1.18×**.
- **Fixed frequency, command-proportional amplitude** (17.0 → 58.1, 3.4×) ⇒ the `1−P·L` signature.
  The **grind saturates** above 1500 ct where the ratchet keeps growing.

---

## 4. ⭐⭐ THE LANE: `gp-0x6b86`, THE BASE POWER-ASSIST MAP

Largest torque-fed term in the aggregator — ±0x3000 window, **5.8–7.8× the entire PID**.

**The curve is in the image** (initialised data copied ROM→RAM at boot; only 3 `st.h` touch the
20-knot block and 2 are clears). Records at `0xCE47A` / `0xCF372` / `0xCF3CA` (+3 mode duplicates),
byte-identical across 161 images. **The 2.000 slope cap BINDS on 3–4 of 9 segments.**

**The section is a textbook notch and its parameters SEPARATE:**
```
H(z) = C_B4 (z² + C_B0 z + 1) / (z² + C_A8 z + C_AC)
   numerator roots have product 1  => zeros ALWAYS on the unit circle => always a true notch
   C_B0 alone sets the notch;  C_A8/C_AC alone set the poles;  C_B4 sets DC
```
Stock `C_B0` puts Honda's notch at **55.23 Hz, −43.9 dB**. **A notch cannot be moved to the ratchet**:
`C_B4 ~ 1/f²`, so 8.64 Hz needs `C_B4` = 13.58 and amplifies out-of-band **1503×**; 55 Hz needs 0.336
and amplifies 1.0×. **Honda put it there because that is the only free placement.** The **poles**, not
the notch, are the lever in the ratchet band.

**GATE 1 passes**: `gp-0x6b86` has exactly **one** consumer outside its producer (the aggregator at
`0x3AC7C`). No monitor watches it, so heavy filtering cannot trip a fault path.
**GATE 2 passes**, anchored on the measured `Q_eff/Q_passive = 14.3` (the census phase gives the
*wrong sign*, and `P`'s phase is not in the image).

---

## 5. WHAT WAS RULED OUT, WITH THE REASON

| candidate | verdict |
|---|---|
| **r26's admission gate** | Honda **already** gates it off engaged (`gp-0x6b5e` = ±4762, not 0) |
| **kill the PID / r24 / both** | marginal **1.21× / 1.14× / 1.35×** on top of V173 — below the 1.63× floor |
| **stack the cap onto V173** | **1.17–1.40×** for the *full* static weight cost |
| **a razor notch at 8.64 Hz** | complex poles r≈0.988, **Q≈40 at 3.3 Hz** in the driver's band |
| **LKAS authority** | command rails only **3.3 %** of frames, median 3–6 % of ceiling, and **is delivered** (7/7 routes above shuffled control) |
| **command oscillation** | clears its null in **exactly one band, 15–25 Hz** — the grind's. Shares its lever |

---

## 6. OPEN ITEMS, WITH WHAT WOULD CLOSE EACH

- **The `P·L` real-positive assumption.** **Closes only on the drive.** Three estimator families have
  now failed: frequency-domain Q (tilt), excess stratified by torque (rate-confounded, structurally),
  ring-down (fails its own control — 6/9 at 1.5–3.3×, one control negative, no build ordering).
- ✅ **Driven vs self-excited: CLOSED — DRIVEN.** It was inconclusive at n=7 (CI [−0.021, +0.176]
  crossed zero). The cache turned out to hold **19 usable routes, not the 9 I had scored**; at
  **n=17** the same statistic gives median **+0.1148**, CI **[+0.0274, +0.1682]** — **excludes
  zero**. Specific on 10/17, and specificity rises with window count (ρ +0.31), as an
  underpowered real effect predicts. ⚠ Not universal — `r85`/`r95`/`r97` are negative.
  ⇒ **a null on the drive can no longer be blamed on absent excitation.**
- **Honda's 55 Hz notch: purpose unknown.** V173 preserves it; V172 does not. Worth knowing before
  flying V172.
- **The absolute Q-ratio figures** carry more uncertainty than two decimals suggest, since `L_other`
  was overcounted (r26 gated off). **Ratios between builds are unaffected.**
- **13-engaged-modes claim** for V158's damper edit is still unreconciled (it edits 26/27).

---

## 7. METHOD NOTES — each cost something

- **`search_instructions` undercounts**: returned **zero** stores where a byte scan found **27**.
- **tp off-by-0x1000 recurred, 8th time** — `0xC76CE` for `0xC66CE`. **The interleaved 15s were the
  tell**; a knot table is monotone. It gave the *opposite* conclusion from the wrong cells.
- **Never read Q off a pole pair without checking it is complex.** A frontier sweep printed "ring Q
  30–53" for **real** poles and nearly killed a viable lever.
- **A time-reversed control is vacuous for a linear fit** — r² is invariant under reversing the
  x-ordering. It returned identical values on all 9 routes; that was the tell.
- **The scorer read the wrong channel** (`cs_rate`), and the **V158 card pointed at a superseded
  scorer**. Both found by **running the drive card's own command verbatim**. That check belongs in
  every close-out.
- **Never nest a file read inside the call that opens it for writing** — truncated `MEMORY-PART6.md`
  to 1 KB; restored from `540c00a3`, 84 pointers intact.
- **Enumerate the cache before trusting an n.** I scored 9 routes; there are **19**. The
  missing half **overturned one headline claim and closed one open question** — both in the
  same pass. `r77` alone holds 97 windows against `r1e`'s 42.
- **Search the kit's record first**: `MEMORY-PART5` already carried the notch discovery, with the same
  coefficients. I re-derived it without checking.
