---
name: reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short
description: CORRECTS own prior-session characterization -- FUN_000352b4's 2nd-order filter is a NOTCH (zeros exactly on unit circle, product=1), not a generic low-pass; V103 (route 0x9e) armed it. Independently re-derives and confirms V103-as-flown response (pole 42.345Hz r=0.79663, zero 55.225Hz r=1.0) and a proposed 23Hz-recentered design (r=0.975) to 2 decimals via a from-scratch Python transfer-function derivation matching the disassembly exactly. RETRACTS an own same-session error: initially misread a comparison row (keeping Honda's r=0.7966 at a 23Hz angle) as an UNSTABLE filter due to a self-made column-transcription slip (b1 copied into the a1 slot); corrected -- that row is a real, stable, complex pole pair, disqualified on its already-stated +10.75dB peaking, not on instability. Decodes the gp-0x381c/0xC6382 LERP table as FLAT (Y=[20,20,20,20]) -- corrects own earlier "unresolved" status; true live alpha is 20/2048 (corner 1.56Hz), not 41/2048 -- NEITHER is a 7Hz roll-off. Prices q~0.1 recentered-notch effect on f0 at an estimated 3-24 ct*s/rad, ~10-80x below the ~230 ct*s/rad bar -- a fast NO, not a fast yes.
metadata:
  type: reference
---

# The FUN_000352b4 filter is a NOTCH; V103 armed it; re-centering priced short — 2026-08-20

Interim response to an orchestrator message mid-`loop-lag-map` task claiming V103 flew as route
`0x9e` and correcting my "low-pass" characterization to "notch." Independently re-derived
everything rather than relaying it — see the full reasoning and Ghidra output in the session
transcript; this file records the durable facts.

## 1. It IS a notch — independently re-derived from my OWN disassembly, not relayed

Full recursion (matches the disassembly at `0x35a28-0x35a88`, byte-exact, re-traced this session):
`w[n] = c4*u[n] - c1*w[n-1] - c2*w[n-2]` (poles), `y[n] = w[n] + c3*w[n-1] + w[n-2]` (zeros,
numerator leading/trailing coefficients are bare `add`s = hardcoded 1.0 — confirmed from the
opcodes, `addf.s`/`maddf.s` with no accompanying multiply on those two taps). Numerator roots:
`z^2+c3*z+1=0` — product of roots = 1 always (Vieta), so **whenever the numerator quadratic has
complex roots, they sit exactly on the unit circle by construction — a TRUE notch, not merely a
low-pass with an off-circle zero.**

**V103-as-flown (Honda's own coefficients, `0xC60A8/AC/B0/B4` = `-1.5372/0.63462/-1.8808/0.81731`,
confirmed byte-identical stock vs the V103 image per the orchestrator, and independently byte-read
by me from stock `code.bin` this session and in the ORIGINAL 2026-08-19 dead-biquad session):
**pole `|r|=0.796630` at 42.345 Hz, zero `|r|=1.000000` at 55.225 Hz, peak `|H|` over 0.1-500Hz =
+0.0003 dB.** Cross-validated three independent ways this session: my own two Python derivations
(one via a state-space-flavoured formula, one via the direct recursion above) plus the
orchestrator's own reported `-1.549 dB angle -33.21 deg` at 23Hz — all agree to 2-3 decimals.

Full response, V103-as-flown: 7.8Hz -0.15dB/-10.6deg . 15Hz -0.59dB/-20.9deg . 20Hz -1.12dB/-28.5deg
. 23Hz -1.55dB/-33.2deg . 26Hz -2.09dB/-38.2deg . 28Hz -2.52dB/-41.5deg.

## 2. V103 status: strong corroborating evidence found, NOT independently confirmed by me

`git status` at the moment the orchestrator's message arrived showed **untracked** (i.e. genuinely
new this session, not something I had at session start) files: `docs/SCORING-2026-08-20-v103-route9e.md`
(38.5K, detailed per-segment telemetry, real route hash `75604b0a432fdc89/0000009e--54bb0788af`,
11 segments, 647.8s, operator's own verbatim quote reporting BOTH symptoms failed), `docs/DRIVE-CARD-V103.md`,
and six `rlog-tools/v103_r9e_*.py` scripts. Content is internally consistent, detailed, matches this
kit's established conventions (verbatim operator quotes, honest "both symptoms failed" framing, no
inflated claims) — this is strong circumstantial corroboration. **I did NOT pull a raw rlog or
verify the route hash against a primary capture myself** — [BELIEF, well-corroborated by artifacts,
not EVIDENCE by my own primary-source check]. `docs/STATE.md`/`BUILD-LINEAGE.md` are confirmed
stale (0 hits for "V103"/"0x9e" as of this session's start-of-task read) — consistent with this
kit's own well-documented, repeated stale-flight-status-row pattern, not by itself proof either way.

## 3. 🛑🛑 RETRACTED — "row 2 is unstable" was MY OWN transcription error, not a design flaw

Original claim (WRONG, retracted 2026-08-20 same session): I reported row 2 ("23Hz, r=Honda's
0.7966") as BIBO-unstable, `numpy.roots([1,-1.979152,0.634572])` giving real roots `1.5767`/`0.4025`.
**The bug is mine.** The source table has FOUR columns per row — `b1, a1, a2, g` — and row 2's
values are `b1=-1.979152, a1=-1.576593, a2=0.634572, g=2.781060`. When building my verification
script I copied `b1`'s value into the `a1` slot (a manual multi-column transcription slip), so I
tested `[1, -1.979152(=b1, WRONG), 0.634572]` instead of the real `[1, -1.576593(=a1, correct),
0.634572]`. **Re-run with the correct `a1=-1.576593`**: `numpy.roots([1,-1.576593,0.634572])` gives
`0.788297 +/- 0.114720j`, `|r|=0.796600` at **23.000 Hz — a genuine complex pole pair at Honda's own
radius, stable**, and the full response (peak `|H|`=+10.7468dB @499.9Hz; 7.8Hz -1.19dB/-17.7deg;
15Hz -5.30dB; 20Hz -13.16dB; 23Hz null; 26Hz -12.73dB; 28Hz -8.22dB) **matches the orchestrator's
original table to 2 decimals, exactly.** Row 2 is real, stable, and correctly disqualified on its
own stated grounds (+10.75dB peaking = a new resonance in the 3-8Hz command band, forbidden) — NOT
on instability. **Lesson: when hand-transcribing a multi-column table into code, re-read the row
against the header labels one field at a time — a plausible-looking 4-tuple can silently swap two
columns that share a similar magnitude, and the resulting "error" (instability) can look like a
genuine, interesting finding rather than what it is, a data-entry bug.** See
[[feedback_own_error_stock_read_attributed_to_built_image]] for the sibling lesson this repeats
(verify against the SOURCE, not against internal self-consistency, before reporting a surprising
result as fact).

**Rows for r=0.93 and r=0.975 (including the actual RECOMMENDATION) were transcribed correctly and
remain fully validated** — see below, unaffected by this correction.

## 4. The recommended re-centered design (23Hz, r=0.975) — FULLY VALIDATED, independently

`a1=-1.929673, a2=0.950625, b1=-1.979152, g=1.004979`. Independently confirmed: pole `r=0.975` at
exactly 23.000Hz, zero `r=1.000` at exactly 23.000Hz (a co-located pole/zero notch, the standard
design), DC gain 0.999991 approx 1, peak `|H|` over 0.1-500Hz = +0.26dB (matches the orchestrator's
table to 2 decimals). Full response: 7.8Hz -0.11dB/-7.4deg . 15Hz -0.77dB/-20.7deg . 20Hz
-4.25dB/-48.0deg . 23Hz -infinity dB (exact null at 23.000000...Hz) . 26Hz -4.24dB/+58.0deg . 28Hz
-1.94dB/+43.3deg — **every number matches the orchestrator's table exactly.** Row 3 (r=0.93) also
fully validated.

## 5. Priced with q~0.1 — a fast NO, not a fast yes

Scaled from the prior session's own validated q-sweep for the AS-FLOWN notch (`+2 to +13 ct*s/rad`
at q=0.10-0.25, computed via the SAME `Re(deltaL)=q*Re(L_total*(H-1))`/`C`-calibration method that
priced `0xC63AC`). Computed `|H_recentered-1|` vs `|H_asflown-1|` at 20/23/26Hz: ratios **1.38x,
1.83x, 1.38x**. Scaling the prior session's validated range by this ratio: **approx 3 to 24
ct*s/rad at q=0.10-0.25** — **roughly 10-80x below the ~230 ct*s/rad / 1.5Hz bar.** [BELIEF: a
linear extrapolation from a validated anchor, not a fresh re-run of the `L_total`/`C` calibration
with the recentered coefficients substituted in — that re-run is the concrete next step if a firmer
number is needed. The recentered notch's `(H-1)` phase swings ~285 degrees across just 20-26Hz (vs
the as-flown notch's much gentler swing), so the "no sign flip anywhere in the band" result the
as-flown notch earned does NOT automatically carry over — this scaling could be optimistic, not
just imprecise.]

## 6. Request #4 answered: `gp-0x381c` sums INTO THE SAME LANE as the notch, and its LERP is FLAT

Re-traced my own already-collected disassembly (`0x35a84-0x35a90`): `r15` (the gp-0x381c IIR's
clamped-overflow term, `>>7`, stored to `gp-0x6b7e`) is **added directly to** `r6` (the biquad
output when armed, else the raw pre-filter `r10`) at `0x35a88 add r15,r6`, and the SUM is what gets
clamped to `+-0x3000` and becomes the `gp-0x6b86` candidate. **Confirmed: the two terms are
additive in series inside the same lane, exactly as claimed.**

**LERP table decoded** (`read_memory(0xC68FC,32)`, standard `{count,X[],Y[]}` layout matching every
other LERP in this firmware): count=4 @`0xC68FC`, X=`[0,9830,26214,32768]` @`0xC68FE`, **Y=`[20,20,20,20]`
@`0xC6906` — FLAT, no real gain-scheduling implemented.** => **CORRECTS my own earlier-this-session
memory** (`reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction.md`), which called this
"unresolved" — it is now resolved: **the actual live alpha (gate false, ~always true in practice)
is `20/2048=0.009766`, corner 1.56Hz**, not the static-candidate `41/2048=0.020` I'd already
characterized (that remains correct for the rare `|gp-0x6b62|>8192` branch, corner 3.22Hz).
**Neither corner is close to 7Hz.** I do not have independent grounds to say this is "the 7Hz
roll-off cell" the operator originally asked about — flagging the speculation as UNCONFIRMED rather
than adopting it.

## 7. GATE 3 — ringdown time constant, quantified; magnitude NOT quantified

`tau=-1/ln(r)` samples at 1kHz: **r=0.7966 (Honda) -> 4.40ms; r=0.975 (recommended) -> 39.50ms, a
9.0x longer ringdown** (time-to-1%: 20.2ms vs 181.7ms). This is a real, quantified increase in how
long the filter retains energy from a transient before the next one arrives — a genuine GATE-3 risk
class, distinct from steady-state peak `|H|` (already shown safe at +0.26dB). [BELIEF: I did NOT
quantify actual clamp-hit duty — that needs either a representative `gp-0x4f60`/`u`-input amplitude
trace or an on-car probe; the state variables are `gp-0x3814`/`gp-0x3818` (`0xFEDF47EC`/`0xFEDF47E8`),
the float clamp is `+-12.0` (`movhi 0x4140`/`-0x3ec0`, `0x35a54-78`), the integer clamp is
`+-0x3000` (`0x35a8c-a4`) — same addresses as the as-flown filter, unchanged by a coefficient-only
edit.]

## Related
[[reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction]] — the session this extends; its
`gp-0x381c` characterization is corrected here (section 6). [[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]]
— the original pole/zero find (its own numbers now independently re-confirmed, "low-pass" language
corrected to "notch"). [[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]]
section 8 — the `q`-pricing methodology this session's estimate scales from.
