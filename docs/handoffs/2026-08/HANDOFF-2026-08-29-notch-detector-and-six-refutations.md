# HANDOFF 2026-08-29 — the notch, Honda's oscillation detector, and six refutations

**Nothing was flashed. No CAN or UDS message was sent.** Everything below is analysis and unflown
builds. The operator drove nothing this session, so **every on-car claim in here is a prediction**.

**Shelf:** `docs/scoring/SHELF.md` — three flashable builds (V194/V195/V196); V185–V193 renamed
`SUPERSEDED-DO-NOT-FLASH-…`.

---

## 1. THE FINDING THAT CHANGED EVERYTHING ELSE — the scorer's endpoint is RELATIVE

Two endpoint families cover essentially every verdict in the arc, and **both divide by something a
broadband filter also attenuates**: the slope-corrected excess divides by a power law fitted
*outside* the band; ~every other scorer divides by a 30–40 Hz control band.

Applying V184's real `|H|²` to the real flying spectrum (`r24`):

| band | ABSOLUTE | ctrl-band ratio | slope excess |
|---|---|---|---|
| GRIND 15–25 | **×0.025 (−15.9 dB)** | **×3.0 ↑** | ×1.02 |
| RATCHET 5–12 | ×0.131 (−8.8 dB) | ×15.6 ↑ | ×1.12 |

The control band itself falls −20.8 dB, so dividing by it turns a **40× win into a 15× apparent
loss**. 🛑 **Absolute band power is restored to `score_band_excess.py`** with the worked example
printed inline. It had been withdrawn once for spectral tilt — the right handling of tilt is to
**report the slope**, not delete the level.

⇒ **RULE: compare ABSOLUTE across builds; a ratio is valid only WITHIN a build, where the divisor
is common.**

---

## 2. THE SYMPTOM MAP — all three of the operator's complaints now have a mechanism

Same slope-corrected excess across **all** channels, 1080 pooled engaged-creep windows, null ≈ 3.9×:

| channel | RATCHET 5–12 | GRIND 15–25 |
|---|---|---|
| `cs_tq` driver torque | **13.5× @ 8.01 Hz** | 5.1× @ 20.12 Hz |
| `cs_rate` steering rate | **1.7×** (below null) | **7.3× @ 20.31 Hz** |
| `sc_tq` LKAS command | 1.2× | 3.3× |

- **GRIND = a genuine motion oscillation**, strongest in RATE. Confirms the closed-loop model.
- **RATCHET = torque-dominant.** But ⚠ see §6.3 — "not in the motion" was an over-claim;
  torque and rate are **coherent 0.888 at 8 Hz**, so the motion is *small*, not absent (stiff rack).
- **COMMAND OSCILLATION = not commandable.** The LKAS lane is a ~1–5 Hz low-pass, so openpilot
  cannot command 20 Hz. Its 20 Hz content tracks the grind ⇒ **fixed by fixing the grind, no
  separate lever.**
- **LKAS AUTHORITY** — the knob is `0xC6CD0`, which is *also* the grind's carrier (§4).

---

## 3. THE LEVERS BUILT

### The notch — the grind lever
The assist section is `H(z) = B4·(z² + B0·z + 1)/(z² + A8·z + AC)`. The numerator's roots have
product 1, so they are **always on the unit circle** ⇒ it is a **perfect notch** and **B0 alone sets
its frequency**. Honda placed it at 55.226 Hz.

**The tradeoff is FORCED, not a search failure:** unity DC gain pins `B4=(1+A8+AC)/(2+B0)`, so a
notch near 8 Hz forces the poles within ~0.05 of the unit circle ⇒ *real* poles land their corner at
8 Hz too, reproducing V184's −40.5° problem. **One biquad cannot serve LKAS phase + attenuation +
55 Hz protection.**

| design | ratchet | grind | phase @3 Hz |
|---|---|---|---|
| V184 low-pass (poles 0.980) | −8.8 dB | −15.9 dB | **−40.5°** |
| notch @ 8.80 Hz | 6.0× | 0.9× | −10.0° |
| **notch @ 19.40 Hz (V188)** | 1.3× | **14.3×** | −3.8° |
| middle @ 14.10 Hz | 2.2× | 2.3× | −8.2° (**dominated**) |
| **notch @ 19.75 Hz r 0.900 (V195)** | — | **21.5× median, 14.3× p90** | −4.6° |

**V195 re-fitted the notch on `cs_rate`** (where the grind lives) instead of `cs_tq`: **1.43× more
grind power removed for 0.8° more phase**, and the wider pole is **gentler on the shoulder too**
(−37.1° vs −44.3° at 18.95 Hz). The re-fit was not a trade.

🛑 **Cost: Honda's 55.226 Hz null is given up — but ONLY WHILE ENGAGED** (§5). Alias test (55.226
folds to 44.77 Hz): 295 routes, median 0.99, max 2.69, **zero above 3**, while control frequencies
reach 3.6–6.5. Evidence against a road-excited plant mode; **cannot exclude a command-excited mode
the notch currently suppresses.**

### The ratchet levers
- **K1 `0xC40D2`** — the flying build runs **1020 vs Honda's 102, ten times** the modelled Coulomb
  friction. Reverted at V177, carried on V189+.
- **Engaged inertia `0xD7A5C`** — `gp-0x6b26` is ω²-weighted (**67× at 8.2 Hz vs 1 Hz**). Ladder:
  flying ≈3× Honda **and it ratchets** → V189–V195 = Honda → **V196 = half Honda**. Engaged-only
  (m24 and m26 are distinct records), **zero at DC** ⇒ no authority cost, no steering weight.

---

## 4. LKAS AUTHORITY — sequenced, not blocked

```
   reach = (clip × cal(0xC6CD0)) >> 15
   4×  V57–V88    ← the value at which V88 CONFIRMED the grinding fixed on-car
   8×  V101       ← and the grind came back
   6×  V102–now
```
**The same cell is what the de-confounded 2×2 named as the grind's CARRIER** (effect 2.7–3.9×).
Authority and grind are **one lever pushed opposite ways** — and that coupling is exactly what the
notch breaks. ⇒ **fly the notch, confirm the grind is gone, THEN 6× → 8×.** Raising it first is the
V101 mistake.

🛑 **AND THE PRIOR ON 8× IS WORSE THAN V101 ALONE SUGGESTS.** Backfilling the lineage from the
images (§10) shows `0xC6CD0` went **V124 6×→8×, V137 back to 6×, V142 6×→8× again, V147 back to
6×** — all undocumented. **8× has been reached and abandoned THREE times, not once.** The
*sequence* is still right (the notch is what breaks the coupling, and that is new), but the
operator must be told this before 8× is proposed again.

🛑 **`0xC61BE` is mislabelled in the lineage as "the LKAS request clip".** It clamps `gp-0x6b2e` in
the **base-assist** path (driver torque → assist map), consumed at `0x2A896`. Raising it adds
*manual* assist, not LKAS authority.

⭐ **V57 is a large, undocumented authority build.** Beyond the `0xC646C` decoupling it is credited
with, it also carries: `0xC62EA` 320→0 (**the low-speed steer lockout, DISABLED**),
`0xC659A..0xC65CE` float ±1.0→±5.0 and `0xC674E..0xC676C` int ±1024→±5120 (**a saturation-limit
family raised 5×**), `0xC61C0/C2/C4` and `0xC64B4/B6/B8` saturated to −1. **Substantial authority
work has been on the car since V57.**

---

## 5. HONDA'S OSCILLATION DETECTOR — fully mapped

`gp-0x671a` is a **hard-reversal counter** on `gp-0x6c2c` (the acceleration EMA), clamped at
CEIL = 5 (`0xC64FA`), threshold T = 12800 (`0xC620A`), dwell HYST = 50 (`0xC64DD`).

**All three consumers read:**
- `FUN_00036c12` — counter ≥ 5 ⇒ `L = cal(0xC640A) = −8192` instead of the LERP. **The only place
  the assist gain itself changes.** V191 zeroes it.
- `FUN_0003a382` — two counter-indexed LERPs, `X = [5,10,15]` and `[5,8,10]`. **The counter is
  clamped at 5 and the first breakpoint IS 5, so `5 < counter` is never true ⇒ both return Y[0]
  permanently. INERT.**
- `FUN_00035b20` — switches the slew-limit curve: normal `Y=[358,358,461,512]` vs oscillating
  `Y=[358,307,307,307]` with breakpoints stretched 2×. **Honda TIGHTENS on detection — the detector
  is a DAMPING mechanism.** V192 applies Honda's own 0.60 ratio again → `[215,184,184,184]`.

🛑 **THE FREQUENCY WINDOW.** A reversal counts only if the opposite peak arrives within HYST ticks.
`FUN_000428d4`/`FUN_00041464`/`FUN_000352b4` share one caller (`FUN_0002214a`) ⇒ same 1 kHz task ⇒
HYST = 50 ms ⇒ **countable only above 10 Hz.** The ratchet at 7.34–8.59 Hz is **outside**; the grind
at 15–25 Hz is inside. V193 widens the dwell to 100 (window f > 5 Hz).

🛑 **T is the WRONG knob** — no amount of lowering an *amplitude* threshold makes an 8 Hz
oscillation countable when the *dwell* expires. **HYST is the binding constraint, and it had never
been touched.**

🛑 **The biquad gate is engagement-gated, and V103's patch has THREE sites, not the two the lineage
names:** `0x35A08` displacement → `gp-0x6806`, `0x35A12` `cmp r12,r9`→`cmp r0,r9`, and
**`0x35A18` `setfnc`→`setfne`** — the omitted one is what makes it correct. ⇒ **manual driving is
bit-for-bit stock, including Honda's 55 Hz null.**

---

## 6. RETRACTIONS AND REFUTATIONS — record these so they are not repeated

1. **V190 retracted, then UN-retracted.** I judged `gp-0x6bc2` in isolation, which needs the
   unproven aggregator→plant sign. The answerable question is **relative**: both inversions in the
   `gp-0x6ad6` path cancel, so `gp-0x6bc2` enters with the **same sign as `gp-0x6b26`**, which the
   ★★★★★ record calls anti-damping. ⇒ **when an absolute sign needs an unproven link, compare
   against a term already characterised through that same link — the unknown cancels.**
2. **The Coulomb sign-flip hypothesis is REFUTED.** With a matched control (dwelling at similarly
   low |rate|, no sign change): ratchet cross/dwell **3.73 [2.97,4.35]** but the **grind control
   4.96 [3.84,5.92] — higher**. Crossings excite everything; no friction-specific preference.
3. **"The ratchet is not in the motion" was OVER-CLAIMED.** The first coherence run returned
   **1.000 for everything including the shuffled surrogate** (degenerate). Redone properly:
   `cs_tq × cs_rate` = **0.888 @8 Hz vs floor 0.049** ⇒ torque and motion **are** coupled; the
   motion is small (stiff rack), not absent. ⇒ **V193's premise is not dead; V194's probe still
   decides.**
4. **The rate-scaling test is CONFOUNDED** — ratchet/ctrl rises 63.7→211 peaking at 20–40 °/s, but
   the grind control does the same and ratchet/grind stays flat at 6.2–8.5.
5. **V191's "4.2× boost" rationale is CORRECTED.** That compares the fallback against the LERP's
   *high-index* end; at creep `gp-0x6a5e` sits low (FactorC evidence: below 2240 across 100% of the
   micro regime), where the LERP returns −9830…−5734 and −8192 sits *inside*. Honest description:
   **"remove the term when the detector saturates", not "undo a boost."**
6. **Low 1 Hz command↔motion coherence (0.115) was an EXPOSURE artefact** — hands-off it is
   **0.338, ~7× floor**. Raised as a question, resolved by stratifying; never reported as lost
   authority.

**Method traps hit and fixed this session:**
- The **V850 odd/even displacement trap**: `ld.bu disp16[tp]` has two opcode fields (`0x3D`⇒odd,
  `0x3C`⇒even). Filtering on 0x3D alone caught only half and reported **every address one too low**,
  inventing a phantom cal next to the real arm. **Validate any cal scan by requiring a KNOWN cell to
  appear.**
- **Ghidra UNDERCOUNTS** (analysed code only, still says `truncated:false`) and **a byte scan
  OVERCOUNTS** (cannot tell code from data; a loose displacement rule matches neighbours). Neither
  is authoritative — **adjudicate each disagreement by disassembling the disputed address.**
  `0x2A896` was confirmed real that way; `0xBCC52` (decodes to `-0x6ad5`) was rejected.
- **A decoder that runs on the wrong build produces a plausible, specific, wrong number.**
  `decode_v194_detector_input.py` now refuses without `--v194`.

---

## 7. CARRIED-BY-ACCIDENT — found by the first full cumulative diff against stock

**72 halfwords, `0xE4194..0xE521C`, all 15360 → 16384**, present since V108. **They are DEAD:**
`0xC61BE`, the clamp on that path, is byte-stock at 15360, so every raised entry is cut back. V108
raised the *tables* and **pulled** the clamp raise on a pre-registered null. **Half a two-part edit,
carried on every build since — including the one on the car.**

Also: the part-number marker `39990-TVA-A160` → `39990-TVA,A160` (2 copies), a UDS-visible flag.

**Measured, not asserted:** V122 (flying) **310** payload bytes vs stock · V195 **309** · V196 **315** · V194 **319**. Against the car as it stands today: **V195 and V196 each differ by only 30 payload bytes** (the same cells, different values at `0xD7A5C`), V194 by 42. Note V195 differs from stock by FEWER bytes than the flying build — it reverts more than it adds. Tool:
`analysis-2020accord/verify/cumulative_delta_vs_stock.py` — it **refuses to stay silent about
anything it cannot attribute**, which is how the 72 bytes surfaced.

---

## 8. OPEN ITEMS — each with what would close it

| open item | what would close it |
|---|---|
| **Does any of this work on the car?** Nothing was flown. | One 15 s engaged creep pass on V196 + `score_band_excess.py`. |
| Does `\|gp-0x6c2c\|` reach T = 12800? Decides whether V191–V194's detector route can act at all. | Fly **V194**, then `decode_v194_detector_input.py <tag> --v194`. |
| Is the inertia anti-damping sign right? | V196 vs V195 on-car. Ratchet **worse** ⇒ inverted ⇒ revert. |
| Is the 55 Hz null load-bearing? Unobservable at 100 Hz sampling. | A drive on any notch build. A new high note **while engaged** ⇒ yes. |
| **Hands-on is the corpus blind spot** — zero continuous 15 s hands-on engaged-creep windows; only 1 hands-on 20.5 s episode. | Pass 1b on any drive. |
| openpilot's phase margin — the estimate failed its controls (engaged Mp 0.840 vs shuffled 0.683). | Not estimable from this corpus; needs a deliberate excitation. |
| `0xC40BC` ramp knee is 3000 vs Honda's 600, unreverted since ~V122, unattributed to any stated intent. | Decide whether it is wanted; it makes the ramp shallower (less friction), which suits the operator's stated preference. |
| The 72 dead bytes — revert to stock, or complete the edit by raising `0xC61BE`? | Operator's call. Completing it adds **base-assist** authority, which he did not ask for. |
| `gp-0x6c2e`'s second EMA (`0xC40DA`, `>>7`) is unexplored. | Trace its consumers. |

---

## 9. TOOLS ADDED

| tool | what it answers |
|---|---|
| `rlog-tools/score/cross_channel_band_excess.py` | which channel a symptom lives in |
| `rlog-tools/score/coulomb_signflip_test.py` | is a band Coulomb-driven (with a matched control) |
| `rlog-tools/score/notch_shoulder_check.py` | does a notch threaten its own low shoulder |
| `rlog-tools/score/command_coupling_at_grind.py` | is the LKAS command coupled to the motion |
| `rlog-tools/probe/decode_v194_detector_input.py` | `gp-0x6c2c` vs T — refuses on pre-V194 caches |
| `analysis-2020accord/verify/cumulative_delta_vs_stock.py` | every non-stock cell, attributed |
| `analysis-2020accord/verify/xref_audit_byte_vs_ghidra.py` | byte-confirm any xref count |

---

## 10. THE LINEAGE GAP — partially closed

`docs/BUILD-LINEAGE.md` said *"THIS LINEAGE STOPS AT V121. V122–V178 HAVE NO ROWS — INCLUDING THE
FLYING BUILD."* It is a mandatory pre-read before any calibration edit, so the rule *"grep the
lineage before naming any address"* **silently passed** for every cell those builds moved — which is
how the 10× K1 dose and the 72 dead bytes stayed invisible.

✅ **`docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md`** — **generated, not narrated**: every row is
a byte diff between two images on disk. **43 cells across 57 builds, 7.4 KB.** `grep <address>` works
again for V122–V196.
Generator: `analysis-2020accord/verify/gen_lineage_address_index.py`.

⚠ Limits, stated in the file itself: it carries **no reasoning**; **not every build number has an
image** (gaps 122→124, 125→127, 127→129, 129→131, 131→137, 142→147, 161→164, 165→167, 177→179,
181→183), so a change across a gap means *"at or before this build"*; and anything load-bearing
should still be diffed **against the stock image**.
