# HANDOFF 2026-08-14 — V100 FLEW (route `0x85`), SIX LEVERS CLOSED, **NO V101 CUT**

**Read `docs/STATE.md` §1–§11 first; this is the narrative behind it.**
**Full working: `docs/archive/arc-maps/_v101_arc_map.md` (~135 KB).**

---

## THE ONE-PARAGRAPH VERSION

V100 flew as route `0x85` and gave the kit its best-ever drive: **249.2 s engaged in 6 episodes,
~4× the previous best, and the first substantially non-creep engaged exposure** (p50 39.6 km/h,
88.4 s ≥50 km/h). It answered its question in the negative — **both PID saturation clamps read
exactly zero**, so the reference-clamp hypothesis is dead and every lever V89→V99 was *delivered*,
not thrown away. The session then examined six candidate fixes and **closed all six**, two of them
on measured on-car data and one of which (`0xC4118`) would have **silently deleted LKAS steering**
had it been armed. **No V101 was built.** The operator chose an instrument-only build; the payload
was then designed, and every bit in it turned out to be vacuous, self-answered, or unable to change
a decision — so the honest recommendation was **do not cut it**, and that is what happened.
**The search space is materially smaller than it was, and nothing was spent to shrink it.**

---

## 1. WHAT FLEW, AND WHAT IT DECIDED

**V100, route `0x85`, 5 segments (15/16/18/19/20 — segment 17 absent from disk, leaving a ~60 s hole
in the route-time axis; per-segment differentiation is mandatory or the seam manufactures a
6,537 °/s artefact).** Fault-free; identity duty 1.000000; 427 unsaturated.

**E1 / E2 both read 0.000000**, in all 8 wheel-rate bins, CI [0, 0.0186]. The pre-registered ZERO
sentence is licensed verbatim, and the composite sentence closes the **whole saturation family**.

🛑 **The reason this is trustworthy is that the gate was proven, not assumed.** Two threshold rungs
both reading exactly zero is the V64/V68 signature, so the null was not accepted until:
1. **Both rungs were disassembled from the built image** — all four branches `0x05AE` = **cond `0xE`
   = signed GE** (explicitly *not* the `ba05`/`b205` inversion class that has flipped a rung's
   meaning here before), `tp+0x7200` → `0xC6200` reading 8192, `shl 0x4` placing bits at b5/b6,
   **no guard on either rung**, and — the strongest item — **the rungs share their accumulator and
   store with the controls that measured 0.5222 / 0.6057 / 1.000000**, so there is no execution path
   that evaluates a control but skips a rung. The detector provably ran 29,999 times.
2. ⭐ **The last open gap was closed empirically.** `mov`'s flag-transparency between `cmp` and `bge`
   had been carried as **BELIEF since V98**, and it lands *precisely* on the two rungs that read
   zero (the sign rungs never exercise it). **V98's cave carries the byte-identical idiom
   (`e639` / `023a`|`043a` / `ae05`) at the same bit positions, and V98's bit-6 comparator measured
   duty 0.4235 on-car.** The idiom is proven to work by a previous flight of the same bytes.
3. **Structure predicts the null independently** — see §2.

---

## 2. THE BUDGET WAS A GATE-3 ERROR, AND THE CORRECTION PREDICTS THE FLIGHT

The record's *"the terms bound to ~12× the threshold"* summed each term's **admission window**
(its zero-reject gate) rather than each lane's **own writer clamp**. Corrected from the image:

```
term 0  gp-0x6b4a  ≡ 0            (0xC616C = 0 annihilates it)
term 1  gp-0x6b6e  ±1024          (0xC617E)
term 2  gp-0x6bbc  ≡ 0            NO WRITER  (new finding)
term 3  gp-0x6b70  ±8192          (0xC6200 — the same cell as the threshold)
term 4  gp-0x6bce  ≡ 0            NO WRITER  (new finding)
term 5  gp-0x6b2a  ±1024          (0xC61C6)
term 6  gp-0x6b60  ±6144          but rides the gp-0x6bda detent gate, measured 0.0000 / 75,227 frames
term 7  gp-0x6bc2  ±512           and ZERO below ~30 km/h
                    total reachable 17,152 = 2.09x the 8192 threshold, not ~12x
```
**At creep, worst case ≈ 3,167 + 1,024 + 1,024 = 5,215 < 8,192.** The clamp *cannot* bind — derived
with no reference to the flight. **Two independent lines agreeing on a null is much stronger than
either alone**, and it is the session's cleanest structural result.

⚠ **Honest limit, carried verbatim from the tracer:** this proves the rungs *would* fire if the
quantity crossed, and that the quantity is small. It does **not** prove the quantity is small *for
the reason the budget gives* — terms 1/5/6/7 are bounded by clamps, not measured.

---

## 3. THE SIX CLOSURES — and the one that matters most for safety

Full table in `STATE.md` §3. The two worth reading twice:

### 🛑🛑 `0xC4118` — a cal-only, 11-byte edit that would have deleted your steering
`0xC6194` is a real, calibrated slew limiter on the LKAS request (3 ct/tick, 1.37 s full scale), and
the record filed it dead with the reason **"output ×0"** — which **belongs to `0xC6196`, a different
cell two bytes away** (`0xC6194` = 3, `0xC6196` = 0, both verified). So a live cell carried a false
death certificate for ~40 builds. On the operator's `dx/dt` hypothesis, *"arm the dormant command
rate limiter"* is the obvious move.

**It would have deleted LKAS steering.** The partition byte at `0xC4118` does **double duty**: the
same byte that routes the limiter's input also *gates* the live 4×-gained command into
`gp-0x3d88 → gp-0x6b4c`. Zeroing it to arm the limiter drives the delivered command to zero —
**silently, while openpilot believes it is steering.** *Arming the limiter and deleting the command
are the same edit.* The cell is dead twice over anyway (input ≡ 0; output reaches only
`gp-0x6b4a` ≡ 0 via `0xC63CC` = 0), but **the hazard is now a hard NEVER-ARM with a mechanism**,
because a future session reading only *"the partition bypasses the limiter, all-1s"* would naturally
reach for those eleven bytes.

### The two candidates that survived longest, and how they died
- **`0xC63EC`/`0xC63EE`** — a one-pole IIR + 2-tap FIR on the live command path, **virgin on 95/95
  images**, DC-preserving by construction (so provably not an authority cut), 4 bytes. **Died on
  arithmetic that needs no unknowns:** the command's 6–9 Hz content is **8.08 % of its own total
  RMS**, so a 0.564× band cut moves the whole command by **0.223 %** — **39× below V85's
  already-not-felt 1.088.** Independently: **91.1 % of bar 6–9 Hz power is incoherent with the
  command**, and **the bar leads the command by −18.5 ms** (bar = source, command = echo).
  ⭐ **And the phase cost everyone worried about was free** — it filters an *exogenous input*,
  outside the loop, so it cannot move a closed-loop pole at any dose. *The thing we feared was a
  non-issue; the thing we hadn't priced killed it.*
- **PID Kp** — **virgin on 95/95 images, RULE-7 clean, and the only lever found all session whose
  sign is phase-independent** (`phase(H_P) = 0` exactly ⇒ P is a pure impedance-canceller with
  fractional authority exactly `Kp/1024`). **Died on the squeeze:** ×2 delivers **1.130×** at 6–9 Hz
  — *on* the 1.088 not-felt bound; ×4 delivers 1.720× (felt) but **92 % rail duty hands-on**, which
  is the V80 mechanism. *The dose that is safe is not felt, and the dose that is felt is not safe.*

---

## 4. THE OPERATOR'S OWN AXIS — HE IS RIGHT ON TWO OF THREE CLAIMS

His words: *"speed independent… the stuttering is worst when `d(LKAS demand)/dt` is high."*
🛑 **The corpus null that appeared to cover this was on WHEEL rate — a different quantity.**

| claim | verdict |
|---|---|
| harsher command ⇒ more of it | ✅ **hands-off pooled partial +0.0815 [+0.0404, +0.1244]**, 5,716 windows / **118 episodes**, 8 routes, residualised within route, bootstrapped over episodes |
| approximately speed-independent | ✅ **+0.111 / +0.077 / +0.131** across 10–30 / 30–60 / 60+ km/h |
| it selectively drives the 6–9 Hz mode | 🛑 **NO** — control-band-free sweep 2–44 Hz is **positive in every band**, floor ≈ +0.09, **6–9 Hz +0.124 on the declining shoulder of a +0.224 peak at 2–5 Hz** (the LKAS lane's own passband). Excess over the floor: **+0.03** |

⇒ **Broadband EXCITATION, not resonance selectivity** — converging with the on-record *"~28 Hz
lane-change transient is dose-independent ⇒ excitation, not gain"* from an independent direction.

🛑 **The hands-ON arm is UNRESOLVED, not null**: +0.012 [−0.097, +0.114], and **the hands-off point
estimate lies inside that CI** ⇒ the arms are **not distinguishable**. Closing it needs ~155 s more
hands-on exposure. ⚠ **Only 10 of 49 routes are cached in the current schema**; the 994.9 s corpus
needs ~40–60 min of re-extraction. **That is the top of the next session's list, script already written.**

⚠ **Two analysis defects were caught by their own authors mid-session and both ran in the operator's
favour**: a contaminated control band (20–24 Hz sits inside V68's 18–28 Hz engaged-conditional band
and over-subtracts) that had made the effect look like a null; and a **purity rule** requiring 122 of
128 consecutive frames of override against a signal whose **median run is 0.020 s — two frames**,
which had killed the hands-on arm and was mistaken for absent data.

---

## 5. WHY NO V101 WAS CUT

The operator was given the choice and selected **instrument-only**. The payload was then designed —
and every bit failed on inspection:

| bit | why it died |
|---|---|
| 427 ← `gp-0x6b4c` | the SHARE endpoint it existed for is **moot** (the low-pass died on arithmetic) ⇒ a channel with no pre-registered endpoint |
| `\|gp-0x6ad4\| ≥ 5120` | **vacuous** — `AUTH ≤ 5120 < 10240` always ⇒ the dropout is structurally unreachable. **The V69 `bit4` failure class verbatim** |
| `gp-0x69a4 ≥ 868` | **answered itself from the images** — see §6 |
| `gp-0x67ab == 1` | a confirmation of a well-supported claim; knowledge-bearing, **not drive-justifying alone** |
| AUTH comparator | four questions on one bit, **but even fully cleared it licenses only 1.13×** — an answer that cannot change a build decision |

⇒ **A build that measures dead levers is worse than no build**, and it would have been the operator's
**third consecutive** zero-calibration build. **Do not cut V101.**

---

## 6. ⭐⭐ THE SESSION'S BEST RESULT NEEDED NO DRIVE — THE RATE LANE IS CLOSED AT AN OPTIMUM

Read from the images (`0x3AA96` gate · `0xC6444` · `0xC6446`), orchestrator-verified:

```
stock/V62/V65  gate 0xC5 DEAD   512 /  512    net = (5244 + 512a)/(3072 + 3072a),  a = gp-0x69a4/1024
V67/V68/V88    gate 0xFB ARMED  512 / 5244    1.707 @a=0  ->  0.937 @a=1
V71c           gate 0xFB ARMED 3072 / 5244    1.707 @a=0  ->  1.354 @a=1
V100 (on car)  gate 0xFB ARMED  512 / 5244    = V88
```

🛑 **At `a = 0`, V88 and V71c are arithmetically identical (both 1.707)** — same gate, same r24 arm,
and `0xC6444` enters only as `arm26·a`. **On-car they are the corpus extremes**: V88 *"grinding
fixed"*; **V71c the worst build ever recorded on all three symptoms** (ratchet at the corpus record
8,521 ct p-p). ⇒ **`a` is materially non-zero and the r26 arm is load-bearing.**

⇒ **Account A is refuted.** *"More derivative feedback ⇒ more damping ⇒ less HF"* predicts the
**higher** net dose (V71c) should be **better**. It was dramatically worse. **The coupling in the V88
memory is right; the causal direction was wrong.**

⇒ ⭐ **Both flanks are now measured** — V61 (below V88) *"made it worse"*; V71c (above) worst in the
corpus. The standing *"2× ≈ OPTIMUM, not a point on a ramp"* now has **both sides**, and **V88 is
sitting on the optimum.** ⇒ **Lever B is off every future shortlist, in both directions**, and this
**retires the kit's self-declared "leading open question."**
✅ Checked in the safe direction: `0xC6444`'s falsification **stands** — V71c had the gate **armed**.

---

## 7. WHAT THE NEXT SESSION SHOULD KNOW

1. **Do not re-propose any of the six closures.** Grep `docs/BUILD-LINEAGE.md`'s new closure table first.
2. **RULE 14 — GATE 3 must ask whether a lane has a DROPOUT, not only a clamp.** This firmware uses
   latching zero-output dropouts as an idiom in ≥2 places, and **a dropout is invisible to every
   no-clip rule the kit runs.**
3. **RULE 15 — an implausible null is a bug report, and so is an implausible non-null.** Five
   scan-blindness classes surfaced in one session and **every one was caught by a decompile
   disagreeing with a scan, never by the scan itself.**
4. **Verify a LERP's axis — and a gate's enable — from its WRITER, not a label.** Three axis
   misidentifications are on record; the third was a repeat of the second by a session that never
   found the correction.
5. **The hands-on `dCMD/dt` arm is the one open measurement worth money**, and it needs no drive —
   just ~40–60 min of re-extraction on 3–4 large uncached routes, then `rlog-tools/studies/misc/dcmd_dt_corpus_pool.py`.
6. **Segment 17 of route `0x85`** may still be on the device. Recovering it would take engaged
   exposure from 249.2 s to ~309 s and merge three episodes into one ~180 s continuous run.

---

## ARTEFACTS

**New analysis scripts** — `rlog-tools/`: `decode/extract_r85.py` · `score/score_r85_v100.py` ·
`studies/misc/dcmd_dt_hypothesis.py` · `studies/misc/dcmd_dt_spectrum.py` · `studies/misc/dcmd_dt_grip.py` · `studies/identification/gp6ac0_operating_point.py` ·
`studies/estimator-qc/mask_reconciliation.py` · `studies/estimator-qc/lkas_command_band_content.py` · `studies/misc/dcmd_dt_corpus_pool.py`
**New reader** — `analysis-2020accord/studies/ledger/ledger_v38_to_v100_bytes.py` (90 images, anchors pass, zero
unattributed bytes).
**New caches/results** — `analysis-2020accord/_scratch/cache/r85/` (12 files) · `analysis-2020accord/sessions/v100/` (9 files).
**New doc** — `docs/archive/arc-maps/_v101_arc_map.md`.
🛑 **No firmware artefact was produced. `../accord-firmwares` is unchanged.**
