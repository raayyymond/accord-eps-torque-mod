# HANDOFF — 2026-08-06 — V74 flew: the damper is real, the gate criterion was broken, and two candidates are built

**Read after:** `docs/HANDOFF-2026-08-05-the-car-is-tvca4-and-both-dead-zones.md`.
**New reference documents from this session:** `docs/FEASIBILITY-8X-LKAS.md`, `docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md`.
**Route:** `5d` (`75604b0a432fdc89_0000005d`), 17 segments, 101,118 frames / 1,012.9 s.

This handoff tells the session in the order it happened, including the part where an early "clear" was
withdrawn and then restored on better evidence. That sequence is the most durable thing this session
produced — more durable than any single number in it — so Section 2 is told as a narrative, not a
verdict, deliberately.

---

## 1. V74 flew, and the damping lever reached the car for the first time in this kit's history

V74 carried `FactorC Y[0]:=Y[2]` and `FactorE X[0]: 60→12` / `Y[1]:=Y[2]` on the thirteen engaged-column
modes, opening both dead zones `docs/HANDOFF-2026-08-05-the-car-is-tvca4-and-both-dead-zones.md`
identified — this car has never had creep damping, stock included, because the base-assist damper's own
speed and rate tables both floor at zero below their first breakpoint. Its probe carried something no
prior probe had: a direct read of the damper's own output, `bit7 = (gp-0x6bd0 != 0)`, alongside
`bits 6:3 = gp-0x67fa & 0xF`, the assist-chain state. It is the positive control the previous five
probes lacked, and it fired.

Engaged creep reads 67.44% duty non-zero (7,860 frames); manual creep reads 0.29% (41,046 frames) — a
230.7× contrast. Engaged overall is 39.93% (56,753 frames), manual overall 2.13% (44,365 frames).
V72 carried an identical probe on the identical cell and read zero across its entire route — 0 of
87,940 frames — because V72's damping levers were mode-indexed to rows this car does not read (RULE 7).
This is the difference between an argued fix and a measured one, and it is now orchestrator-verified
independently of the decode agent, over the full route.

Both controls hold. The negative control: of the manual frames where `bit7` did fire, all of them sit
within 5 seconds of a disengagement — zero of 40,398 manual frames beyond the mode-byte's fall lag show
any damper output — confirming the engaged-column-only design on-car, not merely asserting it from the
build's own bytes; manual and parking steering really are byte-stock. The positive control: 157
disengaged frames that independently clear stock's own (narrower) dead-zone breakpoints read 100.000%
non-zero — the stock damper working correctly wherever its own breakpoints are met, proving the probe
bit and the damper functional in both directions. (An earlier pass reported 183 frames at 99.45% for
this cell; that used a retired 10.0 counts/deg-s rate scale. The settled scale is 4.7121, and the honest
form also has to account for the `>>10` truncation — clearing both breakpoints is not by itself
sufficient for a non-zero dose. The corrected reading is the one above.)

The same route settled a second, two-session-old question for good. `gp-0x67fa` reads a constant 5 for
101,117 of 101,118 frames; the single exception is the last frame of the route, at vEgo ≈0, in PARK,
reading state 4. Since state 5 clears every one of the three assist-chain gate masks — `0x830`, `0x930`,
`0xc30` — `0x454FE`, the state-4 governor substitution once recorded as V42's confirmed hard-turn-ratchet
fix and later re-attributed to the r26 kill instead, is now closed permanently: it cannot fire under real
driving conditions, on this build or on stock, and "starved by state gating" as a general explanation is
closed with it. This is the third independent replication of that finding. Do not re-propose either.

## 2. The gate: ambiguous on first read, investigated, and resolved clear — because the criterion itself was broken

The pre-registered abort criterion for V74's dose was Falsifier B, `5×f0` prominence exceeding 3.0 — the
signature a `sign()`-relay damper would leave if it started generating its own limit cycle rather than
merely opposing one. The first summary of route 5d reported this clear, at 2.227. Reading
`_r5d_falsifiers.json` directly surfaced two things that summary had omitted, both real. The K-free
per-window version of the same statistic — which the script's own comment calls the safer number when
the two disagree — put V74 at 2.884 [2.301, 3.575], the highest median of any build in the eleven-build
corpus, its confidence interval crossing 3.0. And the creep-only arm, the exact regime V75's dose lands
hardest in, read 5.844 against a pooled-corpus creep baseline of 0.632 — nearly twice the abort
threshold, uninterpretable alone at two runs but not dismissible either. The verdict was withdrawn, and
the operator was told plainly that a decision already relayed had been walked back.

What resolved it was not a more careful reading of the same statistic — it was recognizing the statistic
could not answer the question it was asked. Falsifier B's search is anchored: it looks for a peak within
four bins (NFFT 2048) or two bins (per-window, NFFT 512) of that build's OWN predicted `5×f0`, which
means it can only ever report "something prominent sits near the predicted location." It cannot
distinguish a genuine relay harmonic, whose location moves when `f0` moves, from a fixed pre-existing
line that a particular build's `f0` happens to place nearby. This kit already has a recorded fixed line
at 42.19 Hz, twice the 21.09 Hz grind-#1 mode, and V74 has the highest measured `f0` (8.46 Hz) of all
eleven corpus builds — which puts its own `5×f0` (42.31 Hz) closer to that fixed line than any other
build's. An un-anchored wideband search, 33–47 Hz, free to find the tallest peak anywhere in that range
regardless of any build's own `f0`, located V74's true dominant feature at 40.20 Hz: 0.01 Hz from
`2×grind-1` (40.19 Hz), and 2.11 Hz from `5×f0` (42.31 Hz). At NFFT 2048's 0.049 Hz bin width that
2.11 Hz gap is 43 bins — the true peak sits physically outside the anchored search's four-bin reach, so
the anchored search could not have found it and reported a weaker sidelobe (prominence 2.23) instead of
the real feature (prominence 5.27–15.70, depending on which arm is checked).

Three independent checks confirmed it, not one. A cross-build regression of the wideband peak's own
location against `5×f0`, across all eleven corpus builds, gave slope 0.165 [−0.461, 0.913], r = 0.144,
p = 0.673 — statistically indistinguishable from no relationship — while the same regression against
`2×f_grind1` gave slope 1.478 [0.477, 2.255], r = 0.759, p = 0.0068, a real and significant correlation
whose interval excludes zero and includes one. A sibling ran an independent per-window Theil-Sen tracking
test with its own positive control and reached the same conclusion by a different route: V74's slope vs
`5×f_ratchet` reads +0.046 [−0.201, +0.386], flat, while the same method's positive control — V72's
version of the same line, tracked against `2×f_grind1` — reads +0.833 [0.570, 1.016], r = 0.597, proving
the method can detect real tracking when it is present and does not detect it here. And a third,
independent diagnostic closed it further: a genuine relay excites the whole odd harmonic series, not
just the fifth, so `3×f0`'s prominence was checked directly. V74 reads 1.374, rank 5 of 11 builds —
entirely unremarkable, squarely in the corpus's normal range. The series is incomplete, which is
independent evidence against a relay. `3×f0` is not automatically clean either — for V62 and V71B it
lands within 0.6 Hz of THEIR OWN grind-1 fundamental, producing spuriously large readings for the same
structural reason. V74 happens to be the one build where the same property that confounds it at `5×f0`
— its unusually high `f0` — leaves it clean at `3×f0`, the largest gap to its own grind-1 fundamental in
the corpus.

The elevation is grind #1's pre-existing second harmonic, not a relay. V74 is simply the build whose own
`f0` happens to put `5×f0` nearest a line that was already there.

**The defect outlives this build.** Falsifier B has been scoring a sidelobe rather than the dominant
feature, on every build in the corpus, because its anchoring removes the one piece of information — where
a peak sits relative to its own build's predictor — that would let it discriminate a genuine harmonic
from a coincidence. Falsifier C was separately unusable on the same route: its raw `Δf0` interval is
2.3 Hz wide against a 0.3 Hz criterion, while the corpus f0 spans 8.01–9.79 Hz build to build. Both are
retired in their anchored form, not re-sized — `docs/BUILD-LINEAGE.md` RULE 8's companion,
`memory/reference-accord-falsifier-b-anchored-search-presupposes-answer.md`, records the general lesson:
an anchored search can only confirm its own prediction, never characterize what is actually in the data.
The replacement instrument, `analysis-2020accord/r5d_tracking_test.py` and `r5d_3xf0_check.py`, runs the
wideband tracking regression as routine rather than only when a number looks concerning, adds the `3×f0`
completeness check, and checks the gap to that build's own grind-1 line before trusting either harmonic
— which one is confound-free varies build to build.

## 3. Efficacy, stated unflatteringly, because the flattering version would mislead

V74 is measurably better than stock. It is not measurably better than V73 — whose damper, per RULE 7,
was never in force at all. The one well-powered contrast this question needs is a paired ratio-of-ratios:
both symptom bands measured on the same windows, relative to their own 24–28 Hz control, so a shared
bootstrap draw cancels the route, exposure and driver effects the two bands share. `R = (6–9 relative) /
(18–22 relative) = 1.015 [0.901, 1.225]`, minimum detectable effect on R of 1.24×. There is no sign
split — the earlier anti-damping concern is dead, properly rather than by assumption — and the phase
model that predicted the damper should be roughly twice as effective at 7.79 Hz as at 21 Hz (R ≈
0.50–0.55) is excluded outright, since the interval's own lower bound is 0.901. But R ≈ 1 is also
exactly what you get if the damper did nothing in either band, and the individual legs say close to
that: at most about 12% on 6–9 Hz (1.037 [0.878, 1.290], 9% once normalized to the control).

The two bands are one system, not two. Their partial correlation, holding the 24–28 Hz control fixed, is
+0.613, clearing its own circular-shift null of [0.207, 0.347]; it reads +0.557 with the damper active
and +0.555 with it idle — the damper does not touch the coupling at all — and their cross-correlation
peaks at lag zero, consistent with a shared excitation rather than one band driving the other. Do not
split the strategy into a damper for the ratchet and a separate lever for grind #1; a fix aimed at one
without the other is not addressing the shared driver.

Grind #1's own limit-cycle metric, scored on engaged creep, tells the same story from a different angle:
V74 reads 0.518, V73 0.550, stock 0.712, V67/V68 0.273, V62/V65 0.142. V74 has not reproduced this kit's
best builds for this symptom, and its in-burst amplitude (1081) sits below the recorded corpus floor for
any arm that still carries the cycle at all (1232) — meaning even the modest improvement it shows may sit
partly inside measurement noise rather than a clean win. It is not entirely a wash: V74 does hold the
corpus's best 6–9 Hz burst numbers at run level, speed-matched — envelope 436, burst duty 0.104,
duration 425 ms — but the step from V73 to V74 specifically is not visible in these numbers. The
attenuation the operator has reported predates V74's damper.

## 4. Two candidates are built, branching from V74; the operator chooses

V75 and V76 are siblings, not a sequence. Either is a clean single-variable change from the car's current
state, and flying one does not invalidate the other.

**V75** raises the damper's dose 2.74× at the symptom's own measured rate, from 50 to 137 counts at
rate 99, via `FactorC Y[0]` 429→566 and `FactorE X[1]` 400→200 on the same thirteen engaged-column modes
V74 used; `FactorE Y[]` is untouched, since that axis has zero headroom. Image SHA256
`e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c`, rwd SHA256
`64e7c9ee50fff896ed76094b38505959d85e74c7e64d4526be0f252b2465cb27`
(`39990-TVA,A160-V75-V74BASE-ENGCOLS13-levers-CY0.566-EX1.200-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd`,
plain image `_v75_CY0.566-EX1.200_magprobe_plain_image.bin`).
⚠ Both artifacts were **renamed once** after the first cut, to encode the lever set into the filenames.
**The bytes are byte-identical across the rename** — the two SHA256s above were verified before and after
— so this was a rename, **not** a re-cut, and no orphaned plain image was left behind.
🛑 The lesson stands regardless: **verify by SHA, never by filename.** The recorded V70 hazard (two cuts
writing the same `_v70_plain_image.bin`, the second silently overwriting the first's snapshot while the
first's `.rwd` stayed flashable) is a **content** hazard, and a filename check cannot catch it in either
direction — here the names changed while the bytes did not, which is the same trap mirrored.
It is verified clip-free two ways — zero new clips on `build_v74_tva.py`'s own 98,988-point rectangular
grid (`new > old AND new > 512`), and zero clips on the 101,118 frames actually driven, where the
observed peak reached 354, 69% of the 512 ceiling — and orchestrator-verified from the bytes: 142
differing bytes across 37 runs (57 cave, 45 table, 40 CRC trailer), zero runs inside
`[0xC5000,0xC5FFC)`, all thirteen disengaged modes byte-identical on both tables, the decoder's own
`CAVE_HEX` byte-identical to the emitted cave, exactly one store and zero `st.h` twins. `566 × 927 >> 10`
resolves to exactly 512, and 567 gives 513 — 566 is the precise maximum this scheme allows, not a round
number. The per-mode picture is not perfectly uniform: modes 2 and 3 carry `X[1] = 450`, not 400, and
their `FactorC Y[0]` (1356) is correctly left alone since 566 would be a reduction there; modes 29, 32
and 33 were already at their own cap and move by one count (565→566). Mode 26, this car's live engaged
mode, is the one that matters and goes 429→566, a 32% increase — the rest of the scope is insurance
against a config change, not a functional edit on this car today. Its probe was redesigned from V74's
liveness bit — which could not distinguish V75 from V74, since `bit7` only answers whether the damper
fired at all — into a magnitude thermometer: `bit7` non-zero as a cross-build anchor, `bit6/5/4` at
`|gp-0x6bd0| ≥ 128/288/448` with the last a near-ceiling alarm, and `bit3` reading `gp-0x6ac2 != 0`, the
back-drive detector described below.

**V76** takes a different route to the same symptom, restoring V67/V68's rate-lane configuration on a
V74 base, and was still in build as this handoff was written — check `build_v76_tva.py`'s own header and
`docs/STATE.md`'s current build table before citing a SHA for it. It is a two-cell edit, not a new lever:
`0x3AA96` moves `0xC5` to `0xFB`, repointing a dead cell to `gp-0x6806` (the LKAS-applying flag), and
`0xC6446` moves 512 to 5244; `0xC6444` already equals V67/V68's value. Decompiling `FUN_0003aa2c` this
session settled why this configuration reaches the car at all: when the gate fires, `0xC6446` and
`0xC6444` are read by a plain `ld.hu` that overrides the register unconditionally, and the mode-indexed
`gain_B` LERP — the surface RULE 7 shows is inert on this car — is only the fallback branch, bypassed
entirely once the gate is active. That is the mechanism by which RULE 7 voided V69 and V70, which edited
the fallback, but never touched V67/V68's own result; their dose was genuinely delivered all along. A
correction to the existing record belongs alongside this: V67/V68's r26 cut is a flat, speed-independent
override, not the creep-only, LERP-modulated cut `docs/BUILD-LINEAGE.md` had described, which makes it
more robust against grind #2 than previously credited. V76's probe follows this kit's standing "probe the
gate, not just the output" lesson: `bit6` watches `gp-0x6806` itself — a constant reading here means the
build never engaged the mechanism — and `bit5` watches `gp-0x671d`, which outranks the arm and pins r24
to 1024 (below stock) whenever it is set, a cell checked across only 14,980 frames of one short route so
far.

## 5. The strategic finding this session's real value sits in

The two best grind-#1 results in this kit's entire corpus are rate-lane configurations, and neither is on
the car. V67 and V68's mechanism, now understood, is mode-proof by construction — the gate-active branch
bypasses the mode-indexed surface entirely, which is exactly why RULE 7 voided the builds that touched
that surface directly without touching V67/V68's own measured result. Restoring it on a V74 base is a
two-cell edit. Whatever the operator decides about V75 versus V76, the fact that this kit already found
its best-measured fix for this symptom class once, lost track of which lever produced it during a
rebase, and only recovered the reason this session, should weigh into that decision at least as heavily
as either candidate's own numbers.

## 6. Structural findings, for the record

`gp-0x6ac2` is a sign-gated back-drive detector, not a rate signal [EVIDENCE, decompile of
`FUN_00041464`]: `|rate| >> 10` when `sign(rate) != sign(gp-0x6b98)`, zero otherwise — the rack moving
against the command, not simply moving. Consequently the damper's own ceiling (`0xC77A0`,
`X=[300,800] Y=[512,1024]`, byte-identical across all 26 modes checked) sits pinned at its 512 floor in
ordinary driving and only lifts on genuine kickback; every damper lever in this family should be sized
against 512, not 1024. One open bit remains here: the validity bypass writes a `0xFFFF` sentinel at
`0x41b44`, and whether the ceiling's own reader is `ld.h` (giving −1, flooring the clamp) or `ld.hu`
(giving 65535, railing it) is a single bit with opposite answers, still unpinned.

openpilot carries two hard rails, both measured this session, and together they account for 16.07% of
engaged time. The amplitude rail, `STEER_MAX = 4096`, is matched exactly to the firmware's own intake
clamp — `FUN_00052676` computes `clamp(request × −4, ±0x4000)`, and `4096 × 4 = 0x4000` exactly,
orchestrator-verified in Ghidra — meaning there is zero upstream headroom above today's setpoint scaling;
raising `STEER_MAX` alone, without a matching firmware gain increase, buys nothing. The second rail is a
slew cap at 123 counts/frame, exactly `0.03 × STEER_MAX`, with zero observed frames exceeding it and
dominant at highway speed. See `docs/FEASIBILITY-8X-LKAS.md` for what this means for any future
gain-increase proposal.

`gp-0x674e` reads 7 on this car, not the 1 an earlier trace assumed under the since-retired
row-2/`TVAA1` premise; the correctly identified live setpoint record is `0xE51A8`, one of the eight
records V38's raise already covers (8 of 12 reachable records raised, 4 left stock), so V74's delivered
1782 stands unchanged — only the identification of which record is this car's live one was wrong, and it
is now traced rather than assumed. `gp-0x6a5e`, FactorC's own axis, is voted vehicle speed at 64
counts/km/h, not driver torque, confirmed three separate ways this session; the golden model already had
this right, and two stale memory files have been corrected at the source. `gp-0x6ac0` converts at 30
counts per Hz of electrical frequency, and `column_deg/s = counts / 4.7121` — the firmware chain was
re-verified byte-for-byte; an on-car fit of 5.80 reflects the estimator's own column-vs-motor-rate bias
and should not be used to revise the constant.

RULE 8, newly recorded in `docs/BUILD-LINEAGE.md`, comes directly from this session's own clip-check
disagreement: a rectangular-grid no-clip rule and an observed-envelope no-clip rule answered the same
question about V75 differently, because their worst cases differ — the grid's worst corner assumes
849°/s; route 5d's actual maximum was 330°/s, with zero frames above 2000 counts. Three analysts reached
three different conclusions from identical arithmetic purely by policing different envelopes; name the
envelope in the same sentence as the clip fraction going forward. `FactorE X[1]` was identified as a free
lever inside that same investigation — steepening the low-rate ramp raises dose at the operating point
without raising the plateau that sets the surface's maximum, so it passes both the grid rule and the
observed-envelope rule at once, while `FactorE Y[]` has none of that headroom.

## 7. Be honest about the limits — read this section as carefully as any of the wins above

The torsion-bar-to-aggregator unit conversion still does not exist. V75's dose direction is solid — it
opens a dead zone dissipatively, in the correct phase, where none existed before — but its magnitude
could be off by a factor of a few in either direction, and the one attempt to bridge the units had
coherence 0.072 and was correctly refused. Do not fabricate the conversion to make a dose number sound
more precise than it is.

V75 will probably not reach "imperceptible." The gap from engaged creep to the byte-stock manual floor is
5.26× on 6–9 Hz and 14.9× on 18–22 Hz; V74's damper going from fully off to fully on bought at most about
12%. On every well-powered estimate this session produced, a 2.74× crank of the same lever leaves a
residual gap of 2.9–3.7×. Only a threshold effect closes that — plausible for something that behaves like
a limit cycle, since V62/V65's roughly 2× dose took creep burst duty from 0.712 to 0.142 in one step
rather than gradually — but it is not promised, and should not be assumed.

V76's mechanism has no data at 6–9 Hz. V67 and V68 both flew before this kit characterized the
micro-ratchet band at all; their measured result — 18–22 Hz at 0.524× [0.337, 0.804] engaged, 1.055×
disengaged, no manual-feel cost across 26 segments and zero DTCs — is real for grind #1, but Section 3
already established the two bands are coupled, and nothing in the corpus says what the same lever does to
6–9 Hz specifically. Score it; do not assume either direction.

Route 5d itself under-delivered its own flight plan: 9 episodes (19 resampling runs) against roughly 40
planned, 78 seconds of engaged creep, and 200.3 of the route's 359 seconds of engaged time sitting inside
tyre order 1's contaminated speed band against only 158.7 seconds clean. That is what set the MDE at
1.3–2.9× depending on the statistic, not any property of the lever itself.

And finally, a housekeeping fact that is not being silently fixed: the golden model
(`analysis-2020accord/eps_lkas_chain_model.py`) is 3,166 lines against the 2,200-line ceiling the kit set
for itself after the 2026-07-29 distillation — 3,132 lines before this session's own +35. This predates
this session and is flagged for the operator's decision about whether and when to re-distill, not
resolved here.

## 8. Flight plan for whichever candidate flies

Register three endpoints as primary: 6–9 Hz burst duty, burst duration, and the paired ratio-of-ratios
R — the only statistic in this session with sub-1.3× power, and the one that would catch a band asymmetry
if a larger dose produced one. Do not target the stratified band median as a primary endpoint; it needs
roughly sixteen times the exposure this route delivered to resolve at the same confidence.

Drive about 14 minutes of engaged time below 12.5 m/s (3.5× route 5d's 243 seconds), which should bring
the MDE down to roughly 1.3×. Stop-and-go congestion, not continuous engagement, is what gets there — two
blocks of 198 and 167 seconds dominated route 5d's exposure, while route 5a produced 18 episodes in 120
seconds of traffic; episode count, not total duration, is the quantity that drives the MDE. Tyre order 1
sits in-band at 12.5–18.7 m/s, so the clean windows remain 9.4–12.5 m/s and 20 m/s and above. Read the
probe first, before anything else in either log: on V75 a constant thermometer field means the cave never
fired; on V76 a constant `bit6` means the gate never fired and nothing else in the log is interpretable.

If a flight order has to be chosen, V76 first is the better bet. Grind #1 is the audible complaint, and
V76 reproduces the only mechanism in this corpus with a measured effect on it. V75's expected effect, per
Section 3, is small enough that it reads more as a science flight — confirming the damper's dose-response
shape — than as a fix flight on its own. Both remain the operator's decision; neither flashes without him
naming the file and the bus.

---

## Reading order

Start with `docs/STATE.md`'s headline (updated in place this session) for the current-state summary this
handoff narrates. For the gate question specifically, read
`memory/reference-accord-falsifier-b-anchored-search-presupposes-answer.md` before trusting any future
`5×f0`/`3×f0` reading on this corpus. `docs/FEASIBILITY-8X-LKAS.md` and
`docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` are both standalone, written 2026-08-06, and answer
adjacent questions the operator has asked in the past about where this kit's authority ceiling sits and
whether a firmware-side cancellation term is buildable — both concluded staged/no-go rather than a green
light, and both are worth reading before proposing a gain increase beyond V75/V76's scope.
`docs/BUILD-LINEAGE.md` RULE 8 records the clip-check lesson; RULE 7 (2026-08-05) is still the standing
rule that makes V75 and V76's engaged-column design necessary in the first place.

Predecessor: `docs/HANDOFF-2026-08-05-the-car-is-tvca4-and-both-dead-zones.md` — the TVCA4 discovery and
V74's build. This handoff is its direct continuation: V74 as flown, not as built.
