# DRIVE CARD — V172  ·  **FLY THIS FIRST**

**Flash target:** `39990-TVA,A160-V172-V158BASE-ASSIST.SECTION.RETUNE.REALPOLE-0x13000-0x100000.rwd`
**.rwd SHA256** `c0ed77b773a7e7f300ab438450817e17f49269c67d096edefa56dea140e958a5`
**image SHA256** `ff8d07e6ba3e80484b8ef67eeb4d9fd13804ee999d35953038355ab2cd0ab830`

> 🛑 Nothing here authorises a flash. Name the file and the bus yourself; kill openpilot/pandad
> (`tmux kill-server`) before any flash operation.


> 🚩 **SUPERSEDED AS FLY-FIRST BY V173.** V173 has the same poles, the same +30.1 ms group delay
> and the same ratchet effect, but keeps **Honda's 55.23 Hz notch** which V172 displaces to 27 Hz.
> Everything below — the pass, the pre-registered outcomes, the sub-band grind attribution, the
> command-level guidance — **applies unchanged to V173**. Fly V172 only if the grind is the priority.

---

## WHY THIS ONE AND NOT V168

Both attack the ratchet through the same lane (`gp-0x6b86`, the base power-assist map — the largest
torque-fed term in the aggregator). They differ in **what they cost you**:

| | cell(s) | predicted ratchet | also grind? | what it costs |
|---|---|---|---|---|
| V168 | `0xC6384` 2048→1536 | 3.4× | no | **heavier steering near centre**, uniformly, always |
| **V172** | `0xC60A8..B4` retune | **6.2×** | **9.6×** | +30 ms group delay; 3–5 Hz content down 15–32 % |

Your standing constraint is explicitly about **apparent mass and friction**. V168 raises exactly
that. **V172 leaves it untouched** — DC gain 1.0067 — and is the only lever that also attacks the
grind. That is why it goes first.

⚠ I earlier called V172's cost "~130 ms of lag" and put it second because of that. **That figure was
step settling time, which is not what a driver feels.** The felt quantity is group delay in the band
you steer in: **+30 ms at 0.5 Hz, +21 ms at 3 Hz, +5 ms at the ratchet.** Correcting it is why the
order changed.

**V168 and its four-dose ladder stay cut and ready** if the lag turns out to be the problem.

---

## THE DRIVE — ONE CONTINUOUS 15-SECOND PASS

A single continuous 15 s engaged creep episode detected the ratchet in **11 of 11 episodes (100 %)**
on the existing corpus, at a **5–65× margin**. One pass answers it.

1. **Engaged creep, ONE continuous pass of 15 seconds, 1–24 km/h.** Do not break it up — the analysis
   window is 5.12 s.
2. **Include real curvature.** The ratchet's amplitude is monotone in command magnitude (17.0 → 58.1
   across the command range) and peaks in the **12–25 deg/s** wheel-rate band. A dead-straight crawl
   sits in the weakest stratum and will under-read the effect in both directions. A slow continuous
   lap of a car park is the right shape.
3. **Stop as soon as you know.** If the symptom is still there after one pass, the drive has answered.
4. A matched manual creep pass at the same stretch and speed, if convenient. Not required.

**Score with:** `python rlog-tools/score/score_band_excess.py <route-tag>`

---

## PRE-REGISTERED OUTCOMES

| ratchet 5–12 Hz | verdict |
|---|---|
| **below its slope-matched null** (~4) | **gone in that regime**; the loop-gain account holds |
| **unchanged** (V122 reference ≈33) | 6.2× predicted damping produced nothing ⇒ **falsifies the real-positive `P·L` assumption for V168 TOO** — the two levers share it, so this null closes both |
| **rises** | `P·L` is not real-positive; revert and re-derive the phase |

| grind 15–25 Hz | verdict |
|---|---|
| falls **further** than the ratchet | expected — filter attenuation is 9.6× at 21 Hz vs 2.2× at 8.64 Hz |
| ratchet moves but grind does not | the shared-loop account is wrong somewhere, and **that gap names where** |

**No uninterpretable branch.**

---

## 🛑 WHAT WILL FEEL DIFFERENT

- **Steering weight at rest: unchanged.** DC gain 1.0067.
- **Fast inputs: assist arrives ~30 ms later**, and 3–5 Hz content is 15–32 % down. If anything feels
  off, it will be on quick turn-in — a sense of the assist "catching up" rather than heaviness.
- **V158's damper is also on this build** (engaged modes 26/27 only). Heaviness *only* when openpilot
  is steering is that, not this.

**If the lag is the problem, say so and fly V168 instead** — it is built, and its cost is static
weight rather than response speed.

---

## IF IT FAULTS

Four float32 cells that the kit has already changed on-car without fault (V106/V107 moved exactly
these four). The enable was already on. No cave, no code edit; poles real and inside the unit circle
with margin; CRC chain 50/50 and readback byte-identical. If a DTC appears, revert to V158 and report
the code.

---

## ATTRIBUTING A GRIND CHANGE — score 15–20 and 20–25 Hz SEPARATELY

Two levers on this build act at 15–25 Hz: V158's damper and V172's filter. The manual arm cannot
separate them, because **the grind is engaged-only too** — it clears its null in manual on **0 of 7**
routes, exactly like the ratchet. What separates them is the **shape across the band**:

| | 15–20 Hz | 20–25 Hz | |
|---|---|---|---|
| V172's filter | attenuates to 0.174 | attenuates to 0.078 | **sloped — the top falls 2.2x more** |
| V158's damper | rate-proportional, dose-set | same | **roughly flat** |

- **20–25 falls much more than 15–20** ⇒ V172's filter did it.
- **both fall about equally** ⇒ V158's damper did it.

Free from the same episode — no extra exposure needed.

---

## THE TWO SYMPTOMS READ BEST AT DIFFERENT COMMAND LEVELS

| | strongest at | excess there | note |
|---|---|---|---|
| **ratchet** 5–12 Hz | **high** command (1500+ ct) | 58.1 | monotone — keeps growing with command |
| **grind** 15–25 Hz | **mid** command (600–1500 ct) | 12.6 | **dies above it** (6.0 at 1500+), consistent with saturation |

⇒ a pass spent entirely at high command reads the ratchet well and **under-reads the grind**. The
slow varied lap the card already asks for covers both — this is *why*. **Take the grind verdict from
the mid-command windows**, not pooled across the whole pass.

Both peaks are fixed in frequency (grind CV 2.1 % across command, ratchet 7.0 %), so neither verdict
depends on finding the peak in the right place.
