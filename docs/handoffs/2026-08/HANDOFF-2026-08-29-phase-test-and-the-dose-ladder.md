# HANDOFF 2026-08-29 — the phase test, an exhaustive adjudication, and a dose ladder

**Nothing was sent to the car this session.** No CAN, no UDS, no flash.

## THE ONE-LINE STATE

**Fly V158.** It is the first build in this kit's history to deliver **any** base-assist damping at
creep, and a power calculation demoted the previous lead (V160) because its increment is below the
instrument floor. Every branch of the drive's outcome already has a built image.

---

## WHAT CHANGED THE SESSION'S DIRECTION: THE PHASE TEST

The single most useful thing built this session is a **method**, not a build:

> **Compute the lane's magnitude AND phase at the symptom's own frequency, from the bytes, BEFORE
> building anything.**

It cost ~20 lines of Python and it killed a build I had already cut (V162/V163). CLAUDE.md's GATE 2
already demanded it; I had been treating it as a review step instead of a design step.

### Applied to every lane in the aggregator — this is exhaustive, not a survey

| lane / cal | structure at 7.8 Hz | verdict |
|---|---|---|
| r24 (Lever B `0xC6446`) | `K·d(torque)/dt`, **+90°** | **DAMPS** — at 6553 = int16 ceiling in V160 |
| `gp-0x6bd0` (V158) | `−sign(rate)·f(\|rate\|)`, f near-linear | **DAMPS** — dose 50, model's own [30,60] |
| r26 (`0xC6444`) | same class as r24 | **FALSIFIED** — flew as V71c, worse |
| `gp-0x6ad4` | P 99.88 % @ **−1.7°**, D **0.02 %** | **STIFFNESS** — structurally eliminated |
| `gp-0x6b26` | `−K·acceleration` | **ADDED INERTIA** — lowers f₀, does not damp |
| `gp-0x6bbe` | measured viscous 1.571 ct/(deg/s) | already live; raising it = more assist generally |
| `gp-0x6b46` / `0xC63D2` | corner 0.93 Hz, \|H\| 0.119, 81.8° lag | slow trim — **not a lever either direction** |
| backlash band `0xC61A0` | floor 123 ct, virgin | **closed by the limit-cycle exclusion** |
| `gp-0x6b62` return-centre | 0.0000 over 75,227 engaged frames | inert |
| `gp-0x6ade` | 0 writers image-wide | dead |
| `gp-0x6b4c` LKAS | a DC constant for 52–70 % of the return | **excluded — a constant carries no 7.8 Hz** |

⇒ **exactly two lanes damp, and V160 carries both, each at or at the model's stated limit.**

---

## BUILDS

| build | what | status |
|---|---|---|
| **V158** | damper: FactorC `Y[0]:=Y[2]` + FactorE `X[0]` 60→12 + `Y[1]:=Y[2]` | ✅ **FLY THIS** |
| V164 | low dose: FactorC `Y[0]:=Y[1]` (dose 50→27) | ✅ branch: *better but heavy* |
| V165 | high dose: FactorE `Y[1],Y[2]` 539→700 (dose 50→65) | ✅ branch: *unchanged* |
| V160 | V158 + Lever B 5244→6553 | ⚠ demoted — increment below the floor |
| V161 | V122 + Lever B 6553 (single-variable twin) | ⚠ same |
| V162/V163 | resonance-PID ceiling `0xC67C4` 1280→512 | ⛔ **SUPERSEDED — stiffness, not damping** |
| V139, V149, V154–157, V159 | (earlier this session) | ⛔ superseded |

### The dose ladder, in physical units

```
build   dose   viscous added   TOTAL creep viscous   vs stock-only
V122      0       0.000            1.571               x1.00
V164     27       1.476            3.047               x1.94
V158     50       2.733            4.304               x2.74
V165     65       3.553            5.124               x3.26
```
Baseline `gp-0x6bbe` = **1.571 ct/(deg/s) measured on-car**; **stock creep damping is exactly 0.000.**

⚠ **[BELIEF] what ×2.74 buys in ζ.** Only if the firmware's viscous term dominates would ζ go
0.017–0.036 → 0.047–0.099. **It is a firmware-side increment, not a ζ prediction.**

---

## WHY V160 WAS DEMOTED — the calculation, so it is not re-litigated

V88 measured Lever B single-variable across a **10.24×** step. V160 adds **1.2496×**.

| band | V88's step | V160 predicts | same-firmware floor |
|---|---|---|---|
| 6–9 Hz | 0.859 | **0.986** (−1.4 %) | [0.18, 5.51] ⇒ ~3–5× |
| 15–22 Hz | 0.549 | **0.944** (−5.6 %) | [0.59, 1.34] ⇒ ~40 % |

⇒ **4–30× below the floor.** Unmeasurable on one drive, adds an untested dose, and destroys
attribution if the drive is worse.
⭐ **RULE: a build is only worth a drive if its predicted effect exceeds the instrument floor.**

---

## NEGATIVE FINDINGS — recorded so they are never re-proposed

- **`gp-0x6ad4` is structurally incapable of damping at 6–9 Hz.** For D to matter needs `Kd ≈ 1306`,
  a Q10 value of ~1.34 **million**; the cell is a **u16**, max 65535 → only +1.06°. ~1300× too weak
  *by design*. The model's "OPEN, not eliminated" was right that V56's 21 Hz null did not settle it —
  **structure settles it now.**
- **r26 (`0xC6444`) raising is falsified.** The model strikes it as *"reachable only on a build whose
  control path is already ruled out"* — that premise is stale (the repointed path has flown since
  V88) — **but V71c also carried `0x3AA96 = 0xfb`**, so 3072 really was read on-car. Verdict stands.
- **`0xC63D2` is a slow trim** (corner 0.93 Hz). Raising it to cut its 81.8° lag would raise a
  *lagging* lane's gain **8×** into the resonance — the V162 error.
- **The backlash band is cal-reachable** (`0xC61A0` floor = 123 ct, virgin) **but closed**: the ratchet
  is a resonance with **limit cycle EXCLUDED**, and a backlash oscillation *is* a limit cycle.
- **V159's mechanism does not exist** — lane A is flat at 256 through the operating point.

## RETRACTIONS

1. **"`0xCC914`/`0xCC214` are dead tables" — WRONG, twice.** Both are live. `0xCC214` is gain_B's 4th
   array (`tp+0xD214`); `0xCC914` is the **speed breakpoint vector** of `FUN_000348e0`'s blend, read at
   `0x34936` as `ld.w 0xd914[r16]` with `r16 = tp + mode*4`.
   ⭐ **Three encoding traps in one session**: `hw2 = (disp|1)` on `ld.hu`; `disp > 0x7FFF` cannot be a
   disp16; and **a computed base register** — so scanning by base-register identity is structurally
   incomplete. **Validate a scanner against a cell whose answer is known before trusting its null.**
2. **"V158 is MONOTONE" — imprecise.** Its FactorC arm is not (`[429,234,429,908]`), and that is the
   model's own prescription. **The shape law guards FactorE's RATE axis; FactorC is speed-indexed and
   speed cannot pump 7.8 Hz.** ⭐ **Name the AXIS when applying a shape law.**
3. **"resonance PID ⇒ it damps."** The model said *"the most reachable AUTHORITY"* — authority, not
   damping. ⭐ **A lane's name is not its transfer function.**

## OTHER DURABLE FINDINGS

- **The damper is FIVE tables, not four** — `FUN_00034350` also loads **`0xC77A0`, the output ceiling**
  (2-knot, axis `gp-0x6ac2` = a sign-gated kickback detector ⇒ sits on its **512** floor).
- ⭐ **Every cal LERP carries a knot-count header**: `(0, N)` inline, bare `N` at +0 in pointer records.
  **54 well-formed vs 8 false positives** in `0xC6000–0xC7000`. A correct read must satisfy
  `hdr == len(X)` with X strictly ascending — **one assertion catching a wrong address, wrong knot
  count and wrong stride at once. Put it in every build script.**
- **V158 is genuinely viscous, not a relay**: `dose/rate` is near-constant **0.375 → 0.554 across a
  6.5× rate span** (a relay would fall 6.5×).
- The golden model was corrected in place (6 arrays, not 5; the creep ramp is linear, not a dead
  zone). **Contract re-verified: 87 symbols, 2512 bytes, sha `740f4bcd…` exact.**

## OPEN ITEMS — with what would close each

| open | what would close it |
|---|---|
| **V158's on-car effect** | a creep drive **with audio** — the only remaining input |
| Does the firmware's viscous term dominate ζ? | the V158 vs V122 drive; if unchanged, it does not |
| `0xC61BC` binding | the `iVar31 ≥ 5482` probe — **a CAVE edit, needs operator authorization** |
| Authority collapse curve | barred by the monotone-non-increasing safety rule — **operator's call** |
| `FUN_000382d8` (8 pointer tables) | decompile; the largest unexamined family left |
| `FUN_0003b338`/`0003b416`/`0003b49a` roles | index variables and downstream consumers unresolved |
| The instrument gap | engaged-vs-manual collapses to **~1.1×** under controls yet V88 changed the felt symptom ⇒ **the bus is the weak link**, not the model |

## THE FLIGHT PLAN

```
FLY FIRST  V158   single-variable vs V122; the only change above the instrument floor
  better + effort OK          -> V160
  better + wheel too heavy    -> V164   (the damper IS drag; the answer is a lower dose)
  unchanged, effort unchanged -> V165   (overturns the model's "err low" WITH DATA)
  worse                       -> V122   (revert)
  no creep episodes           -> re-drive (V158 is architecturally inert above ~35 km/h)
```

🛑 **The drive must contain**: engaged creep 2–8 km/h with real steering activity · **AUDIO** · a slow
hard hands-off engaged turn · **a matched MANUAL creep segment** (three uncontrolled ratios collapsed
this session when controls were added: 2.8→1.12, 1.29→0.911, 1.309→0.958).

Pre-registered scoring: `docs/scoring/SCORING-V158-preregistered.md`, committed before any flight.
