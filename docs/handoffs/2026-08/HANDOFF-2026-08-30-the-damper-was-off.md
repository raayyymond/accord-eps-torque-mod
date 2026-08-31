# HANDOFF 2026-08-30 — THE DAMPER WAS OFF

**The one-sentence version: the ratchet is a linear anti-damping that engagement switches on at every
speed, and the lane whose entire job is to oppose it has been delivering essentially nothing — zero
below 35 km/h, six counts at 80 — byte-stock in all eighteen flown builds, because the only two
attempts to open it edited the wrong mode table.**

---

## 1. WHAT TO FLASH, IN ORDER

```
  1.  V241   baseline. All the grinding work, the car's own 6x gain.
             39990-TVA,A160-V241-V235BASE-NOTCH.IMU.29.75-22.50-0.940-...rwd
             rwd 57d240d77f568aac...

  2.  V249   THE DAMPER FIX. Opens BOTH dead zones. Engaged only.
             39990-TVA,A160-V249-V247BASE-FACTORC.SPEED.DEADZONE.OPEN-...rwd
             rwd ffe37f2a0e329be0...        image 9c1ac13746538b45...

  3.  V250   Only if V249 helped but did not finish it. Same lane, doubled.
             rwd 7528195b26b84719...        image 66f15ba3d1c6b5ce...

  4.  V246   A DIFFERENT lane (Lever B). Independent second opinion.
             rwd f336b0d53d335fde...        image c97e535f3177c564...
```

**Superseded, do not fly:** V247, V248 — same levers with the SPEED dead zone still shut, so inert
below 35 km/h (36 % of engaged driving). **Authority builds V242/V243** raise the gain, and the gain is
what the ratchet tracks — fly only after the ratchet is settled. **V245** (resonance-PID knee) parked.

Fallback at any point: **V122**. Before anything: `tmux kill-server`.

---

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
