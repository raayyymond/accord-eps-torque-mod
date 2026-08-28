# HANDOFF 2026-08-28 — V112 flew and is the best build yet; the two symptoms are now SEPARATED

## 1. THE HEADLINE

**V112 flew (routes 22, 23) and the operator calls it the best firmware yet** — grind #1 now *rare*,
least ratcheting ever. It also **measurably improved command authority**, which is his standing ask:

```
   achieved / demanded steering rate, engaged, low-torque, moving
     demand band    5-15    15-30   30-60  deg/s
     r21  V111      0.487   0.475   0.367
     r22  V112      0.669   0.590   0.432
     r23  V112      0.791   0.544   0.390     => 1.37-1.62x better at 5-15 deg/s
```

🛑 **I had WITHDRAWN V112 on a describing-function argument. He flew it anyway and was right.**
That argument is not settled physics and is not carried forward. **V113 is dead** — it was built to
be "strictly safer" than V112 against a problem that never materialised.

## 2. ⭐⭐ THE STRUCTURAL RESULT: TWO SYMPTOMS, TWO MECHANISMS

Fine `Re(Z)` spectrum on V112 (routes 22+23, 0.5 Hz bins, **coherence 0.5–0.85**): one broad
anti-damped feature **3.0 → 23.5 Hz, peak −81 at 8 Hz, f0 = 23.28 Hz** (matching a 17-route estimate
of 23.29 Hz from a different method).

| symptom | frequency | `Re(Z)` there | mechanism |
|---|---|---|---|
| **peak-turn oscillation** | **7.42 Hz** | −32, rising into the −81 peak | a **LINEAR loop instability** |
| **grind #1** | 18–22 Hz | **−1 to −10, neutral** | a **NONLINEARITY** |

⇒ **the relay knee cannot fix the oscillation and the biquad cannot fix grind #1.** That is why every
build so far moved one and not the other.

⊕ **7.42 Hz is STOCK's own ring-down f0** (ζ 0.0275–0.0321, Q 15.6–18.2). **Our ζ is 0.059–0.072 —
roughly DOUBLE stock's.** The mode is **over-excited, not under-damped**, so adding damping is the
wrong axis; `gp-0x6b26` can supply at most **9.8 %** of the deficit (int16 caps its Y row at ×1.111).

## 3. WHERE THE EXCESS COMES FROM — measured against the REAL stock dump

Same estimator on STOCK (route 97, 573 s engaged) and V112 (809 s):

```
   Hz     STOCK   V112   ratio        Hz      STOCK   V112   ratio
   7-8    -12.0  -43.1   3.58        12-14    -45.4  -57.3   1.26
   8-9    -14.1  -77.2   5.48        16-19    -13.6  -14.8   1.06
   9-12   -31.7  -66.7   2.10
```

**Above ~12 Hz we are indistinguishable from stock. Below 12 Hz we add a NEW localized feature at
7–9 Hz**, and the shape moves (stock's worst point 12.9 Hz at −60; ours 8.6 Hz at −90).
**Stock's −13.1 lies outside the entire modified range (−31.9 … −74.8) across 16 routes** spanning
V90→V112 and 4×/6×/8×. **The excess is ours.**

## 4. ⭐ THE THESIS — the mod works by DELETING HONDA'S LIMITERS

Four are disabled in every affected build and none in stock:

| what | edit |
|---|---|
| arbitration 3-way limit cascade | `0xC61C0/C2/C4` **1600/896/1280 → 65535** |
| low-speed steer lockout | `0xC62EA` **320 → 0** |
| `0xC64B4` | 5 bytes **→ 0xFF** |
| Honda's state-4 governor call | `0x454FE` `bne` → **unconditional `br`** ⇒ `FUN_00049A5A` never called |

⊕ plus the **direction corridor widened ×5** (`0xC674E`/`0xC6750` 1024→5120, `0xC675A` −1024→−5120).

**The excess does not order by gain, build date, or the biquad** — which is what you expect if the
cause is the SET of deletions they all share. 🛑 **A reframe, not a proof.**

## 5. 🛑 ELIMINATED — ten candidates, each with its own control

| candidate | verdict |
|---|---|
| the command rail | 0.76× [0.22, 1.49] |
| driver grip | 0.79× [0.67, 1.01] (measured on **rate**, not torque) |
| command magnitude | present at \|cmd\| < 512 ⇒ command-INDEPENDENT |
| Coulomb relay switching as exciter | **0.14× [0.11, 0.19] — inverted** by a scale-free ratio |
| the armed biquad as ORIGIN | P = 0.722; the excess is already at V90, which has no biquad |
| a linear gain law | within-gain spread 41.2 vs between-gain step 19.1 |
| amplitude dependence | real, but **Honda's**; the 2.2× gap persists at matched amplitude |
| the 164-byte cave | **GATE 1 clean** — reads 7 signals, stores only to the CAN TX buffer |
| restoring the arbitration cascade | its **100-count debounce** cannot catch a 135 ms period |
| opening the base-assist damper | **already flown as V86B** — heavier, ratcheting still present |

## 6. BUILDS ON THE SHELF — all cal/displacement only, NO CAVE EDITS

| build | edits | purpose |
|---|---|---|
| **V119 ⭐ FLY THIS** | knee 1800→2400, K1 612→816, `0xC649B` 1→0, tap→`gp-0x67FA` sar 0 | **both symptoms + the state-4 probe** |
| V118 | `0xC649B` 1→0 + the probe | V119 minus the grind lever |
| V117 | `0xC649B` 1→0 | one byte, biquad only |
| V116 | knee 2400 / K1 816 | grind #1 only |
| V115 | α2 14→8 | ~5 % of the deficit; superseded |

`V119  image a39801bc…  .rwd 18e3216f…  42/42`
Scoring is **pre-registered**: `docs/scoring/SCORING-V118-preregistered.md` (applies to V119 unchanged).

## 7. OPEN ITEMS — with what would close each

- **`0xC64DE` 17→27** — `n = cal/2 + 1` is solid (arb core, count stored to `gp-0x6756`), but the
  consumer is untraced. ⇒ trace the walk at `0x29784`+ **at the correct address**.
- **the direction corridor ×5** — a monitor bound; is its cutback graded or latched?
  ⇒ trace `gp-0x6af6`/`gp-0x6b00`.
- **grind #1's trigger** — unidentified. Acoustic: r22 +0.70 dB passes both nulls, r23 **fails** the
  block-shuffled null; 120–160 Hz passes FWER on r23 only. Episodes are 0.10–0.35 s.
- **the V57 gain repoint** — **cannot be separated from "being a modified build at all"**; every
  modified route carries it and stock is the only 1× point.
- **stock data below 35 km/h** — 25 s exists, and a 25 s window swings `Re(Z)` **1.6–3.8×**.
  ⇒ `docs/scoring/DRIVE-CARD-manual-at-speed.md` (no flash needed).

## 8. 🛑 RETRACTIONS FROM THIS SESSION — all of them

1. **"the car delivers 89–107 % of demand"** — used `ct_curv` (**current** curvature) as the demand.
   Circular. The demand channels are `ct_dcurv`/`cc_curv`; corrected values run 0.92 → 0.30.
2. **"rate compresses against command"** — matched on speed and angle but **not on demand**.
3. **"grip suppresses the oscillation 6×"** — measured the oscillation and the split from the **same
   signal**. On `cs_rate` it is 0.79× [0.67, 1.01]. ⊕ `steeringPressed` is itself a ~1200-ct torque
   threshold ⇒ **no channel here can see LIGHT HANDS.**
4. **"the multiplication is ~6× at low speed"** — built on a **25 s** stock denominator.
5. **"81 calibration runs vs stock"** — diffed against **V83a**, not stock. It is **29**.
6. **"the relay is the exciter"** — inverted by its own control.
7. **the `0xC64DE` table analysis** — **off-by-0x1000**; `tp+0x7734` = `0xC6734`, not `0xC7734`.
8. **the V112 withdrawal** — refuted on-car.

## 9. WHAT I COULD NOT DO

**I did not eliminate the grinding or the ratcheting.** The honest expectation for V119 is a
**reduction, not elimination** — the 7–9 Hz excess is plausibly the price of deleting Honda's
limiters. If it comes back "grind #1 gone, oscillation somewhat better", that is the ceiling of the
present approach, and the next decision — accept it, or buy damping back with authority — is the
**operator's**, with numbers, not a build to make unilaterally.
