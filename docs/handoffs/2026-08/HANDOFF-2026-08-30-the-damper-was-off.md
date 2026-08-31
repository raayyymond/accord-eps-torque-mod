# HANDOFF 2026-08-30 — THE DAMPER WAS OFF, AND THE COMMAND WAS CLIPPED

**Two sentences. (1) The ratchet is a linear anti-damping that engagement switches on at every speed,
and the lane whose entire job is to oppose it has been delivering essentially nothing — zero below
35 km/h, six counts at 80 — byte-stock in all eighteen flown builds, because the only two attempts to
open it edited the wrong mode table. (2) The command's p99 sat at exactly the clamp on every drive in
the corpus, so the top 1 % of openpilot's requests were being clipped, and railed windows carry 3.0×
the ratchet of free ones.**

**All three of the operator's symptoms now have a lever whose size is computed rather than hoped.**

---

## 1. WHAT TO FLASH, IN ORDER

```
  1.  V241   baseline. All the grinding work, the car's own 6x gain.
             rwd 57d240d77f568aac...

  2.  V249   THE DAMPER FIX. Opens BOTH dead zones, engaged only.
             ratchet + grinding, at every speed.
             rwd ffe37f2a0e329be0...      image 9c1ac13746538b45...

  3.  V251   THE RAIL FIX, and the authority answer. Clamp raised ALONE.
             rail time -23 %, delivered torque +11.7 %, ZERO ratchet cost.
             rwd 2d14f2426dfa3c7f...      image b1976f8f442e7533...

  4.  V252   8x -- ONLY after V251 flies clean. +33 % assist everywhere;
             gives back the rail headroom and adds ~13 units of ratchet.
             rwd ecd55f708ba56d0c...      image 0f3f6cf2b1eb2141...

  alt V250   damper margin (89 % -> 179 % of requirement) if V249 falls short
  alt V246   Lever B 1.5x -- a DIFFERENT lane, if the damper is not the answer
```

**Superseded, do not fly:** V247, V248 — same damper levers with the SPEED dead zone still shut, so
inert below 35 km/h (36 % of engaged driving). **V242/V243** are the old gain ladder *without* the
damper fix under them; V252 replaces V242.

Fallback at any point: **V122**. Before anything: `tmux kill-server`.

### What each build is aimed at

| symptom | lever | measured |
|---|---|---|
| grinding | V241 notch, + V249 raises the grinding band **4.1×** | notch aimed on the IMU, independent of the EPS |
| ratcheting | V249 opens both damper dead zones | 6 → 50 counts vs a ~56-count requirement, **all speeds** |
| LKAS authority | V251 clamp | **+11.7 %** delivered torque, peak +33 %, **zero** ratchet cost |
| peak command oscillation | V251 clamp | rail duty **17.6 → 13.5 %**; railed windows carry **3.0×** the ratchet |
| more torque | V252 8× | **+33 %** assist, paid for in rail headroom and ~13 units of Re(Z) |

## 2. 🛑 THE NON-STOCK DELTA — every cell on V249 that differs from Honda

Read from the built image against `stock_fw_dump/code.bin`: **346 bytes in 122 runs** across
`[0x13000, 0x100000)`. Grouped by what they are:

### The three cells THIS session added — the damper

| addr | stock | V249 | what it is | what it does |
|---|---|---|---|---|
| `0xD780E` | 60 | **12** | FactorE X[0], engaged — the damper's **rate** dead zone | the damper was off below 60 counts of motor rate; the ratchet sits at 99 |
| `0xD7818` | 140 | **539** | FactorE Y[1], engaged | gives the first segment real slope, so 99 counts lands at 120 not 16 |
| `0xD77DA` | 0 | **429** | FactorC Y[0], engaged — the damper's **speed** dead zone | the damper was *exactly zero* below 35 km/h; now live at every speed |

Net effect, through the decompiled mirror: damper **6 → 50 counts** above 35 km/h, **0 → 50** below,
against a **~56-count** requirement computed from `Re(Z) = −65`. Grinding band **41 → 167**.

### Carried from earlier builds — the cumulative delta

| addr | stock | now | what it is |
|---|---|---|---|
| `0xC6CD0` | 65535 | 5346 | **the forward LKAS gain — 6×** (V57 decoupled it from the shared cal) |
| `0xC61B3/B5` | 2 | 12 | the forward clamps that track the gain (±3072) |
| `0xC674F/51` etc. | 4 | 14 | soft-EME interlock raised to 5120 — the ceiling that makes 6× deliverable |
| `0xC6446` | 512 | 5244 | **Lever B** at V88's bracketed optimum |
| `0xC60A8–B6` | — | — | **the biquad — V241's IMU-aimed notch** (29.75 / 22.50 / 0.940) |
| `0xC649B` | 0 | 1 | biquad enabled |
| `0xC40BC` | 600 | 3000 | Coulomb relay gate, restored to the car's value by V222 |
| `0xC40D2` | 102 | 1020 | Coulomb slope k1, restored by V222 |
| `0xC62EA` | 320 | 0 | low-speed steer lockout removed (V53) |
| `0xC64B4–B8` | — | ff | gentle-EME debounce disabled (V37) |
| `0x454FE` | 26042 | 26037 | the state-4 governor ratchet fix (V42) |
| `0xD7A5C`, `0xD7A6C` | — | — | `gp-0x6b26` inertia reshape (V106 lineage) |
| `0xC4B34` +164 | ff | — | **the cave** — the telemetry probe payload |
| `0xC4FFC`, `0xC6FFC`, `0xD7FFC`, `0xE4FFC`, `0xE5FFC` | — | — | **CRC trailers — derived, not levers** |
| `0xE4195…0xE521D` | 3c | 40 | 72 single bytes in the HW-ID column tables, carried from the V38-era lineage |

**Measured on-car:** the 6× gain, Lever B at 5244, the V42 governor fix, the V37 EME fix.
**Computed but never flown:** everything in the damper table above, and V241's notch aiming.

---

## 3. WHAT THE SESSION ESTABLISHED

1. **The ratchet is a LINEAR anti-damping** — `Re(Z) = −58` engaged vs `−0.81` manual, 31/31 routes, on
   `tq` and `cs_rate` which are **non-rectified**. Amplitude-independent once coherence is controlled.
2. **It is present at EVERY speed** (−55 to −72 from 0 to 200 km/h), not creep-only.
3. **It tracks the forward gain** (rho −0.819, n=17) — best-supported explanation, though build era
   cannot be fully separated. One era-free contrast (V101→V102 with Lever B held) supports it.
4. **An FDR census of every cal cell that ever varied** found only the gain and Lever B. **But a
   correlation census is blind to cells that never varied** — and all five damper records are
   byte-stock in every flown build. That blind spot is where V247/V249 came from.
5. **All five sensor-fed lanes are accounted for**: two built against (V246, V245), two closed by
   arithmetic (`gp-0x6bbe` reaches 3.2 % of requirement; `gp-0x6b26` adds apparent mass), one carried.
6. **The stock damper is doing nothing anywhere** — never exceeds ~11 counts, which is sub-percent
   against the torque signal, so **no flown drive can test this lane** and V249 is `0 → 50`, not "more".

## 4. WHAT WAS RETRACTED, AND WHY IT MATTERS

Four claims were written and then killed by their own controls. All four are in `STATE.md` with the
control attached:

| claim | what killed it |
|---|---|
| "`gp-0x6b4c` carries the ratchet" (300× ratio) | it is nonzero on **0.3 % of manual frames** — the ratio was measuring liveness |
| "`gp-0x6b86` is where the ratchet ENTERS" | its measured phase says the lane **damps** — an instrument, not a target |
| "a protective damping term RUNS OUT above 2 °/s" | **regression dilution** — coherence climbs 0.29→0.91 with amplitude; flat within high-coherence windows |
| "the gain reversal breaks the era confound" | V101 also **removed Lever B** in the same build — only one of the two legs is clean |

Plus one design error: a regression discontinuity at the damper's switch-on speed, when **the LERP is
continuous there** — there was never a step to find, and the control band is what caught it.

**The lesson, now a `feedback_` memory: compute the control BEFORE writing the mechanism.**

## 5. HOW THIS DIFFERS FROM THE WHOLE ARC SINCE V38

V38–V52 authority/filters/poles/caves · V53–V61 telemetry probes and lane mutes · V62–V73 the rate lane ·
V74–V83a the base-assist **damper's gains** · V84 damper reverted to Honda · V88 Lever B optimum ·
V100–V122 gain ladder and 427 taps · V172–V241 the notch arc.

**Every one of those either scaled a gain, muted a lane, moved a filter, or added a probe.** V247/V249
are the first builds to **open a dead zone** — to make a lane that was structurally OFF start working
at the operating point where the symptom lives. V74–V83a touched this lane's *gains*, which is why they
read as null: **scaling a product whose `Y[0]` is zero is structurally vacuous** (`k × 0 = 0`).

**Not a re-run.** V72/V73 attempted this exact edit and were **inert by table selection** — modes 10/11
on a car that runs 24/26. That is why it has read as a dead end for sixty builds.

---

## 6. OPEN

- **The grinding direction of V249 is untestable from data** and only a drive settles it. If grinding
  worsens, that is the signature and V241 is the way back.
- **The mechanism behind gain ↔ anti-damping is unexplained** — the LKAS lane is a 1–5 Hz low-pass, so
  the command cannot itself carry 7.8 Hz, and a uniform scaling would leave the *ratio* `Re(Z)`
  unchanged. Recorded as empirical with the mechanism open.
- **The golden model does not implement the damper lane at all** (`damping_6bd0` is a supplied input
  defaulting to 0). `model/damper_fun34350_mirror.py` fills it as a sibling module; folding it into the
  facade would change the 87-symbol contract and should be deliberate.
- **`gp-0x6abc` and `gp-0x6b4e`** cannot be ranked at 2f₀ — no decoded channel in the corpus.

**1699 checks passed · 55/55 builders bit-exact · golden model contract intact (87 symbols, 740f4bcd…).**


---

## 7. THE SECOND HALF OF THE SESSION — THE COMMAND RAIL

### The finding

Railed windows carry **3.02× the ratchet** and **1.88× the grinding** of free windows, each symptom
band normalised by a 12–18 Hz **control band** so the "hard driving" factor cancels (2,353 railed vs
5,850 free engaged windows, p ~ 0 and p 2e-265).

🛑 **The first version of that test failed and its own control said so.** Normalising by TOTAL energy
put the control band at ratio 0.250 — moving *more* than either symptom band — because railing
correlates with cornering, whose large low-frequency content inflates the denominator.

### Two of my own claims it corrected

1. **The gain ladder cannot fix rail oscillation.** The clamp *tracks* the gain as `gain*512//891`, so
   the saturation threshold is **512 counts of command at every gain**. V242/V243 buy no headroom.
2. **"A clamp-only build is inert"** — true of the *damper's magnitude* at the operating point, and
   **false of saturation**, which is what V251 is about.

### V251, and why it is the best authority lever on the shelf

```
  0xC61B2 / 0xC61B4   3072 -> 4096     (0xC6CD0 gain UNCHANGED at 6x)

  rail          512 -> 683 counts of openpilot command
  rail duty    17.6 % -> 13.5 %          = 23 % less open-loop time
  delivered     1345 -> 1502 mean        = +11.7 % authority
  p99           3072 -> 4096             the clamp value itself, on EVERY route
```

The p99 sitting at exactly the clamp on every drive means the **top 1 % of requests were all being
clipped**. They now arrive — and it is authority openpilot was *already asking for*, so the gain never
moves and the ratchet's gain dependence is not engaged.

**The trade:** V242 (8×) buys +33 % authority for ~13 units of Re(Z). V251 buys +11.7 % for **zero**.

### Safety, grounded in flight history rather than a model

The clamp/gain tracking is a **build convention, not a firmware invariant** — `0xC61B4` (arbitration
`FUN_00028ea6`) and `0xC61B2` (`limit_and_pack FUN_0002b422`) are plain clamps, compared against the
gain nowhere. And peak delivered command **is** the clamp:

| build | gain | clamp | peak | rail @cmd | status |
|---|---|---|---|---|---|
| V122 | 6× | 3072 | 3072 | 512 | FLOWN, on the car |
| V101 | 8× | 4096 | 4096 | 512 | FLOWN — rejected for GRINDING |
| V251 | 6× | 4096 | 4096 | 683 | this build |

**V251 shares V101's peak and V101 flew** — it just reaches it less often. What V101 was rejected for
came from its **8× gain**, which V251 does not carry.

EME margin on every shelf build: clamp 4096 against the interlock 5120 = **1024 counts of margin**, and
V37's gentle-EME debounce disable is carried throughout. The record's *"gentle EME fires on saturated
LKAS command"* cuts the right way — less saturation should mean **fewer** interventions.

### GATE 2 — the phase check the builds were owed

The damper's rate signal is filtered (`EMA1` @`0x415DA`, `alpha0` at `0xC643C` = 37):

```
  alpha_eff 0.2891  ->  corner 46.0 Hz
  at  7.79 Hz : lag  6.8°  cos(phi) 0.993   -> 99.3 % still opposes rate
  at 25    Hz : lag 28.5°  cos(phi) 0.879   -> 87.9 % still opposes rate
```

A 2 Hz corner would have given 76° of lag and `cos = 0.24` — three quarters of the build's output would
have been a spring term and the drive would have read as a null with no way to tell why. It is 46 Hz.

### The search is exhaustive

A mechanical sweep of every pointer-array LERP in the cal region, by *fraction of the lane's own range
available at the operating point*, finds **exactly one** starved lane:

```
  boost amp y1  91.8 %   damper FactorB 100.0 %   friction lane 87.0 %
  boost curve   84.1 %   damper FactorC  47.2 %   damper ceiling 50.0 %
  boost amp y4  84.6 %   damper FactorD 100.0 %   damper FactorE   1.7 %  <== the only one
```

🛑 **The first version of that sweep returned zero hits and was wrong** — it looked for the operating
point *below* `X[0]`, but `FactorE`'s problem is that 99 counts sits just *past* the edge of 60, where
the curve has climbed to 16 of 927.

## 8. WHAT A DRIVE SETTLES THAT ANALYSIS CANNOT

- Whether the damper direction is right at all. If V249 leaves the ratchet untouched, the mechanism is
  wrong — and that rules out the damper lane by experiment, which sixty builds of inference never did.
- Whether raising the grinding band 4.1× **helps or hurts**. Untestable from the corpus, because the
  stock damper never exceeds ~11 counts and so has no detectable effect to extrapolate from.
- Whether V251's extra delivered torque feels like better lane-holding or like aggression.

**1772 checks · 57/57 builders bit-exact · 14/14 rwd decode identically · flash readiness passing with
three flown controls · golden model contract intact.**
