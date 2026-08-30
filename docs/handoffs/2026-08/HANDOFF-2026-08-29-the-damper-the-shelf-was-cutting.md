# HANDOFF 2026-08-29 — the damper the shelf was cutting

**Headline: the notch shelf was cutting a real 6–9 Hz damper 7.15× below the car, invisibly, inside
builds whose stated purpose was fixing grinding.** Found by chasing one outlier route. Fixed across
V214–V217. Nothing was flashed and no CAN or UDS message was sent.

**Fly `V217`** — `image f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b`.
Its entire delta from the car is **19 payload bytes, every one a deliberate lever.**

---

## 1. The headline finding

`r7d` is **the drive the operator aborted** — *"made the stuttering and grinding worse, by a lot … it
vibrated the entire car, and I decided it was not safe to drive."* It carries a measurable signature,
and every control passes:

```
  sustained engagement-gated line at ~31 Hz
  459x the CREEP-MATCHED corpus median   prominence 56x   (next highest 13.3x)
  engaged/manual contrast          54x
  survives 0.5 s edge trimming     -> not an engagement transient
  56 % of 5-49 Hz power in 30-35   -> a narrow line, not broadband
  speed-invariant across 3 episodes -> not a wheel order (would be order 75.8)
```

V94 flew it after cutting `gp-0x6b26` 6×; that cell was later measured to be a **real 6–9 Hz damper**
(+137°/+139° vs wheel rate, |cos| 0.73 ⇒ **+518/+565 counts of positive Re(Z)**).

**The defect:** the car (V108) carries `0xD7A5C` at **3.576× Honda**; every notch build carried
**0.500×** — a **7.15× cut**, reached in two *never-flown* steps (V175, V196). **Every prior check
compared this row to Honda**, which made a 7.15× change *from the car* read as a tidy "half dose".

### The fix took four builds because each exposed the next layer

| build | corrected |
|---|---|
| V214 | mode 26 inertia row → the car |
| V215 | mode 27 too — RULE 7: "27 is unused" is a *memory*, not evidence |
| V216 | the friction lane — **polarity was backwards**; more modelled friction = MORE assist = LIGHTER wheel, so the shelf's 0.10× was *removing* authority and fighting the 8× gain step in the same build |
| V217 | `0xC63A6`, the inertia lane's **weight** in the model sum — the shelf restored the row then fed it in at half weight, keeping net inertia at 0.5× the car |

⚠ **The generalisable lesson:** *comparing a cell to STOCK hides what it does to the CAR.* Three cells
(inertia row, friction lane, lane weight) all passed Honda-relative checks while sitting 7×, 10× and 2×
from what the operator drives. **Diff every candidate against the flown image.** Gate **[14]** now does.

---

## 2. Structural findings (all EVIDENCE, two methods each)

- **`FUN_00026c80` is the 11-slot lane mixer**, fully decoded. **`gp-0x6b4a` ≡ 0** — nine of ten slots
  store value A as literal `r0`, the tenth (`gp-0x6b76`) is zeroed by `0xC616C` = 0. So the mixer
  reaches the delivery chain with nothing, and **`0xC616C` is the real interlock**, not the ×0.
- **`FUN_00025c32` is a 10-client request bus** — a 16-byte record (slot, type, four values, three
  weights), exactly ten callers. **All ten slots mapped.**
- **`0xC4124` is a ROUTER, not a mute.** mode 0 → `gp-0x6b4c`; mode 5 → **`gp-0x6b4e`**. Complementary
  branches, verified verbatim.
- **`gp-0x6bfa`** (the observer's bias term, provenance previously open) is written by **slot 6**.
- **A float PI controller sits at `0xC60B8`–`0xC60D8`, adjacent to the biquad we edit.** One float of
  offset error lands in it. **Lane 2 is LIVE** — its output reaches `gp-0x6b4e`, read by
  `FUN_00038148` at `0x3817C` as model lane w[4]. Byte-stock on all flashable builds; now asserted.
- **The 42.19 Hz engagement-gated line is a RECTIFIER IMAGE** of the 21.09 Hz mode
  (`gp-0x6ba6 = |gp-0x6b9a|` at `0x3b87a` ⇒ 2f falls out arithmetically). It indexes boost LERPs that
  are flat at the operating point, and that arc **already flew NULL** (V58/V59/V60). **Not an
  independent mode.**
- **The parametric-pump mechanism is VOID**, re-verified rather than taking either side of the
  contested record: `K_p`/`K_i`/`K_d` at `0xC6B1E`/`0xC6B0A`/`0xC6ADE` are **flat in segment 0** at the
  operating point; the contrary reading used `0xC671E`, **off by 0x400**, landing on the square-wave
  injector block.

## 3. Negative findings — record these so they are never re-chased

- The mixer's dormant **rate limiter cannot be armed by any single-byte edit** — its input is zero on
  both sides of the arm gate.
- `0xC648E` (22 readers, reads zero) is **an additive offset** in a telemetry scaler, not a gate.
- **The ~31 Hz line is NOT explained by apparent inertia.** `gp-0x6b26` is `-K*alpha`, so a
  mass-spring resonance would give `f ~ 1/sqrt(J)`, slope **-0.5** against the `0xD7A5C` dose.
  The argmax of the 5-45 Hz creep spectrum appears to confirm it beautifully -- **slope -0.540,
  corr -0.751, n=9** -- and that number is an **artefact**. The peaks are **bimodal** (5-12 and
  15-45 Hz) and argmax hops between clusters; at dose 1.500 two routes sit in each cluster,
  **same dose, opposite answers**. Per band: LOW `corr +0.684 slope +0.061` (wrong sign, flat),
  HIGH `corr -0.845 slope -0.159` (right sign, wrong magnitude). A pure inertia effect must move
  **both** at -0.5. And the HIGH association is carried **entirely by one route**: without `r7d`
  it is `corr -0.510, slope -0.089, perm p=0.177` -- **not significant**. Within-dose spread at
  1.500 is 3.13 Hz over four routes against a 13.67 Hz total range.
  ⇒ **REFUTED. The 31 Hz line remains UNEXPLAINED**, and the corpus cannot settle it because
  only one route has a low inertia dose. `studies/mixer/inertia_dose_vs_peak_frequency.py`
  asserts both refutation conditions so it cannot be quietly re-derived.
- **RE-CENTRING THE NOTCH ON 7.8 Hz IS CLOSED — I re-proposed it and should not have.**
  `STATE.md` already carries a **29,348-candidate** sweep: at a 12° phase budget an 8 Hz notch
  buys `2.56x` on the ratchet but **forfeits the grind entirely** (`0.93x`, at Honda); at 40° it
  is `6.96x` / `1.03x` — grind WORSE than Honda. V217’s 20.5 Hz notch is `1.00x` ratchet /
  **`7.3x` grind** for only `-7.8°`. **One biquad, one zero pair: grind OR ratchet, never both,**
  and the grind is much the better trade. V184 was killed on this and the rejection was already
  re-priced after the biquad was correctly relocated to the base power-assist path.
  ⚠ **My own methodological error:** I quoted `|H|(7.8 Hz) = 0.0000`, a POINT null, where the
  symptom is a **3 Hz-wide band**. A notch narrow enough to pass GATE 2 (r ≈ 0.99) nulls a
  sliver of that band while its phase skirt reaches 1-5 Hz. **Price a band lever on the BAND.**
  ⚠ **Process:** grep the lineage BEFORE computing. CLAUDE.md warns about exactly this and I
  spent a tick reproducing a closed result.
- **THE BASE-ASSIST DAMPER INTO THE MICRO REGIME IS CLOSED** (checked again this session, and the
  memory already said *"DO NOT re-propose"*). `ch0 = (FactorC(speed) x FactorE(rate)) >> 10` is
  zero on **100 % of the micro-ratcheting regime**, but opening both dead zones gives only
  `0 / 3 / 10 / 25` counts at 2/5/10/20 deg/s out of 1024. 25 % authority at 10 deg/s needs
  `FactorE >= 288`, **unreachable by moving X**; it needs `Y[0]` off zero = a step at zero rate
  = a relay in rate = the V78/V79/V80 move = **"WORST GRINDING EVER"**.
- 🛑 **THE RATCHET HAS NO UNTRIED FIRMWARE LEVER.** Closed, each on its own terms:
  the biquad re-centring (29,348-candidate sweep) · the base-assist damper (sizing needs a
  relay) · the rate lane (V39/V42/V61/V62). **`0xC63AE` on V217 is the only untested candidate
  that exists.** Two consecutive search ticks landed on explicitly-closed levers — treat that
  as the signal that the analytical search is exhausted, and get a drive.
- **THE NOTCH CENTRE IS CONFIRMED OPTIMAL under a SECOND, independent objective.** V208/V217's
  20.50 Hz was fitted on the **median episode PEAK** (125 episodes, 20 routes). The kit's own
  scorer argues **band ENERGY** is the better statistic, so I re-optimised on energy-weighted
  removal across the same 125 episodes, under the same gates (`max|H| <= 1`, `|dphase@5Hz| <= 8`):
  V217 removes **95.3 %** of median episode band energy; the best design in the sweep removes
  **95.8 %** — and its **zeros sit at exactly 20.50 Hz**, identical to V217. Only the poles
  differ (14.50 / r 0.9650 vs 15.50 / r 0.9575) for **0.6 percentage points**, inside noise.
  ⇒ **No meaningful headroom. Do not re-tune the notch centre.**
  ⊕ Route `r1e` (999 s engaged, the corpus's longest) has its energy centroid at 17.52 Hz and
  would prefer 15.50 — that is the **documented p10 tail**, which STATE.md already anticipates
  ("the tail is where one biquad was never going to help"). **Do not re-centre on one route.**
- **THERE IS NO RELAY STEP TO REMOVE at the observer's zero crossing.** `gp-0x6b70 = sgn(resid) *
  LERP(|resid|)`, so if `LERP(0) != 0` there would be a hard step of `2*LERP(0)` at every zero
  crossing — a true relay, and **removing** a discontinuity would beat scaling it. Checked via
  `assist_map_mirror`: **`X[0] = 0, Y[0] = 0` at 640/1280/2560/5120** — the curve passes
  through the origin and is **continuous** there. The relay-like behaviour is the STEEP BUT
  CONTINUOUS origin slope (2.67x / 3.04x / 3.77x / 3.43x), not a step.
  ⇒ **`0xC63AE` scales exactly that slope and is the only lever that touches this stage alone**;
  the curve is welded to the ROM assist records, so reshaping it moves steering feel everywhere.
  This closes the last conceivable alternative for the ratchet.
- A sweep for "dormant features gated by a zero cal" has a **poor hit rate** — zero offsets and float
  low-halves dominate. The one real find (the PI block) came from tracing, not sweeping.

## 4. Retractions — all mine, all caught in-session

1. **The `0xC4118` arm-gate hazard.** I claimed zeroing one arm byte would arm a slew limiter in live
   delivery. **Wrong** — payloads are zero on both sides. I traced the plumbing correctly with two
   methods and still got the conclusion wrong **because I never checked what the slots put on the wire.**
2. **"Mode 5 discards value B".** Wrong twice — it *routes* it to `gp-0x6b4e`. Root cause: reading a
   zero-store in one arm of a mode dispatch as proof a value is dead, without checking the complement.
3. **`gp-0x6b76` as a half-wave rectifier.** Misread `r15` as the torque sensor when it was the cal.
   A far more dramatic claim than the truth; caught by going back to the instructions.
4. **The friction direction in `SHELF.md`.** I wrote that the low setting "runs in the direction you
   asked for". It is the opposite.
5. **The 30–49 Hz band needing a matched pair of drives** — the design failure the doctrine forbids.
   Replaced with a corpus baseline so one drive is interpretable.

## 4b. 🛑 THE GATES THEMSELVES WERE THE RECURRING DEFECT — audit them with two lenses

Four gates were found checking the wrong thing this session, all by the same two questions:

**Lens 1 — is it the right REFERENCE?** A cell compared to *stock* says nothing about what it does to the *car*.
**Lens 2 — does it bound BOTH ends?** A gate that caps a maximum says nothing about the floor.

| gate | what it checked | what it MISSED | lens |
|---|---|---|---|
| `[14]` damper | vs Honda | vs the **flown car** — hid a **7.15x** cut | 1 |
| `[6]` GATE 2 | `max\|H\| <= 1` | the **passband floor** — a design scored 99.0 % by attenuating 0-5 Hz to **0.62x** | 2 |
| `[8]` friction | reported the multiplier | **asserted only `knee > 0`** — no bound at all, and Honda-only | 1 + 2 |
| `[13]` gain | the gain value | that the **clamps still clear the lane max** — a raise could silently clip | 2 |

⇒ **When a gate passes, ask what it would still pass.** Two of these four surfaced only because a build tripped over the consequence; the other two were found by deliberately applying the lenses to gates that were passing quietly. **Apply them to any new gate before trusting it.**

## 4c. 🛑 THE COMPLEMENTARY AUDIT — which non-stock cells had NO gate at all

Having audited the gates that exist, the other question is which cells nothing checks. V217 differs from stock in **115 payload runs; only 16 were referenced anywhere in the close-out.**

**(a) The 164-byte code cave had NO coverage** — and caves are this kit’s **only bricking class** (V24, V27, V48B all bricked the ECU). Each builder asserts the cave equals **its own base**, which is a chain of *local* checks: one bad link and every later build inherits it and still passes. Nothing compared the cave **across** the shelf. It is identical on all nine today; gate `[16]` now pins that.

**(b) Four levers with on-car results had no assertion:**

```
  0x454FE   V42 ratchet fix       -- SILENTLY LOST at a rebase, byte-stock V53-V70
  0xC6446   Lever B (V88)         -- best measured grind lever in the kit
  0x3AA96   Lever B arm (V88)
  0xC62EA   low-speed steer lockout DISABLED (stock 320 ct ~ 5 km/h)
```

`0x454FE` is the case that proves the need: it was lost at a rebase and sat byte-stock for eighteen builds before anyone noticed. A gate would have caught it the same day.

⊕ Also checked and found fine: the `0xE4xxx`/`0xE5xxx` taper block (72 identical 15360→16384 edits) is the deliberate authority-curve raise; `0xE51A8` holds a record header (9), not a Y value, so the memory’s wording is consistent — I had read the address as a data cell.

## 4d. ✅ GATE `[17]` — the whole delta is pinned, and the gate is PROVEN to fail

Gates `[1]`–`[16]` each assert a hand-picked cell, which leaves everything nobody thought to name: even after `[16]`, only **21 of V217’s 115 non-stock runs** were referenced anywhere. `[17]` pins the **complete delta** instead — every payload byte differing from stock, CRC trailers excluded, as a count plus a digest, for all nine shelf builds.

**It is deliberately strict.** Adding a legitimate lever *will* fail it, and the fix is to re-record that build’s manifest **in the same commit as the edit**. That is the point: it turns *"did anyone check?"* into *"the manifest says so."*

**Proven to fail, not assumed to.** A gate that cannot fail is worthless, so it was negative-tested:

```
  one cave byte flipped        CAUGHT
  V42 ratchet fix reverted     CAUGHT
  ratchet cal 512 -> 128       CAUGHT
  ALL 320 payload bytes, reverted one at a time:  0 MISSED
```

⚠ My first negative test reported a MISS on the taper block. **The bug was in the test, not the gate:** `0xE41C4` holds 15360→16384, i.e. `00 3C`→`00 40`, so the changed byte is at `0xE41C5` and I had reverted the unchanged low byte. Same *derive the byte, never assume it* lesson that has bitten three builds — this time in my own verification.

## 5. Tools and gates added

- `score_drive.py`: a **30–49 Hz control band** on `cs_rate` + both IMU axes, with a 23-route corpus
  baseline, the ~15× notch-denominator correction, and an explicit statement that **one drive cannot
  resolve the 1.65× gain effect** (the corpus IQR is wider) — it is a *large-excursion detector*.
- Close-out gates **[11]–[14]**: Honda's arbitration tables · the PI block byte-stock · a gain raise
  priced across the whole band · **the damper priced against the flown car**.
- `analysis-2020accord/studies/mixer/mixer_fun26c80_decoded.py` — re-runnable, asserts its own premises.
- **297 checks, 10/10 shelf builders reproduce bit-for-bit.**

## 6. Open items, with what would close each

| item | what closes it |
|---|---|
| **A drive.** Nothing else can confirm any lever. | Fly V217; `score_drive.py <tag> V217` |
| The ~31 Hz line's *mechanism* — why 31 Hz from a 6–9 Hz damper removal | trace the loop's phase at 31 Hz on the V94 cell set |
| Whether the 8× gain costs anything at 30–40 Hz | needs a matched V216/V217 pair — one drive cannot resolve 1.65× |
| Which physical signal each of the 10 mixer slots carries | decompile each caller's *inputs* (slot indices are already mapped) |
| `r7d`'s line on **other** builds | only V94 flew it; no other route shows it creep-matched |
| Route registry stops at `r77` | rlog tails not present in `_scratch/cache` |

## 7. Standing cautions carried forward

- **Diff against the flown image, not stock.** This session's headline is one instance; there were three.
- **Trace the payload, not just the path.** Retraction 1 is the case study.
- **Read every arm of a mode dispatch** before calling a value dead. Retraction 2.
- The `tp` anchor is `0xBF000`; the off-by-0x400/0x1000 error recurred again in the record this session
  (the void parametric-pump reading).
