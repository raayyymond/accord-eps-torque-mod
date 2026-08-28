# STATE — living current state of the kit

## 🛑🛑 **V126 WAS SIZED WRONG — CAUGHT BEFORE FLIGHT. V127 IS THE BUILD.**
**The detector's input is `gp-0x6c2c`, the MOTOR-RATE DERIVATIVE — not driver torque.**
`ld.h -0x6c2c,gp,r10` @`0x428FA`, compared against `cal(0xC620A)=12800` loaded @`0x42910`.
⇒ **the branch fires HANDS-OFF**, on exactly the signal grinding and oscillation excite — and it
is the **same signal `FUN_00036c12` multiplies by `Y`**, so the detector's input and the term's
input are one signal. That is the positive feedback, stated exactly.

### 🛑 AND IT LETS THE VALUE BE SIZED — WHICH V126 WAS NOT
The branch is only ever taken **once the detector has armed**, so `Y` must be sized against the
**arming threshold**, not against "what Honda ships somewhere". Mirroring the decompiled integer
arithmetic exactly (`iVar4 = ((c2c*Y)>>6)*0x111` · `iVar5 = iVar4>>0x12` · clamp ±511):
```
   Y                       b26 at arm    rails from    state when the detector arms
   -8192  stock fallback        1706          3834     RAILED (3.34x over the clamp)
   -3277  V126 as built          682          9584     RAILED (1.33x over the clamp)
   -2453  exact break-even       510         12803     LINEAR (100 % of clamp)
   -1966  Honda Y[2], 90 km/h    409         15974     LINEAR (80 % of clamp)
```
🛑 **−3277 STILL RAILS the instant the detector arms** ⇒ **V126 would have left the term a
bang-bang Coulomb relay in exactly the state it was built to fix.** I chose −3277 for being
Honda-shipped without checking it against the detector's own threshold. ✅ **−1966 is the LARGEST
Honda-shipped value in this family that stays LINEAR at the arming threshold**, still a **strong**
term at **80 % of clamp**, with headroom to `|c2c| = 15974`. It is Honda's own **Y[2]** — the
90 km/h end of the very mode record this branch replaces.

### ✅ V127 BUILT — identical to V126 but for the one halfword
```
   0xC640A   -8192 -> -1966    the oscillation-branch Y   (V126 had -3277)
   0x55DF2    9544 -> 94DA     427 probe source, gp-0x6ABC -> gp-0x6B26
   0x55E10      a3 -> a2       packer sar 3 -> 2, sized to the +-511 clamp
```
image `706363366c017817e34f6f66ece5ea192ca98787f45e45a21e9c33d9b927ed62` ·
rwd `38181d0991ab0d5267dbc67488c5bf27cd6406b0e5eb4a86f33d0da33d2e503c` · **60/60, CRC 50/50.**
⊕ The fallback now **NEVER exceeds** the speed schedule at any speed: creep 0.22×, 24 km/h 0.36×,
44 km/h 0.44×, 64 km/h 0.58×, 90 km/h 1.00×.
✅ **THE SIZING GATE IS NOW A HARD ASSERTION** in the builder — it computes `b26` at the arming
threshold and fails the build if the value is not linear there. **It fails −3277 explicitly.**
A rule someone had to remember is now a check that cannot be forgotten.
🛑 **V126's artifacts are DELETED, not superseded** — it never flew and it does not achieve its
own stated goal, so leaving it flashable is a hazard. Same policy as V123.

### ⭐ A LARGER FINDING THAT THIS BUILD DELIBERATELY DOES **NOT** ACT ON
**The NORMAL speed LERP also rails at mid speeds**: `Y = -4442` at 44 km/h rails from
`|c2c| = 7070`; `Y = -5519` at 24 km/h rails from `5691` — **both far below the 12800 arming
threshold.** ⇒ **the term rails in ORDINARY driving at 15–40 mph, not only in the oscillation
branch**, which is precisely the speed band where the operator reports grinding. Honda's schedule
is only linear at its high-speed end (90 km/h → −1966, rails from 15974).
⇒ **the mode record `0xCBE74` is the bigger lever**, and V91/V92's INERT dose there is now
explained (a saturated counter bypasses the record). **Not taken in V127**: it would confound the
`0xC640A` change on one drive, and V127's probe measures the duty that would size it.

## ✅✅ THE FULL OSCILLATION-RESPONSE CENSUS — `0xC640A` IS THE ONLY MAGNITUDE, AND TWO CORRECTIONS
The saturated reversal counter `gp-0x671a` has **8 instruction sites, 5 consumers + the writer**
— enumerated correctly this time (see the trap below). What each does when the counter saturates:

| site | function | what saturation does |
|---|---|---|
| `0x36C1E` | `FUN_00036c12` | **`Y` = fixed −8192 instead of the speed LERP — the ONLY MAGNITUDE change, and it RAISES the term 1.21–4.17× above 15 km/h** ← **V126's target** |
| `0x3AA70` | `FUN_0003aa2c` | enable flag `0xC6138`=**1** → `0xC6136`=**0** ⇒ **DISABLES** a lane |
| `0x3A4A6` | `FUN_0003a382` | LERP `0xC67B0`: X=[5,10,15] **Y=[1024,1024,1024] — FLAT UNITY** |
| `0x35A06` | `FUN_000352b4` | boolean gate (`setfnc`) on a 2nd-order IIR update |
| `0x35BEA` | `FUN_00035b20` | boolean selector (`setfnc`) between two LERP curves at `0xC7934` |

✅ **`0xC640A` IS THE ONLY CELL IN THE WHOLE OSCILLATION RESPONSE THAT CHANGES A FEEDBACK
MAGNITUDE.** Everything else is a boolean gate or inert ⇒ **V126 targets the right cell, and there
is no second hidden gain jump to chase.**

### 🛑 CORRECTION 1 — `FUN_0003a382`'s use is INERT, not *"the worrying one"*
[[accord-gp671a-blast-radius-not-a-free-lever]] calls the PID's use *"the worrying one — it makes
`T` a shape parameter on a lane already known to be load-bearing."* **The table is FLAT UNITY at
all three points, and its first breakpoint X[0]=5 is at the counter's own CEIL**, so the LERP can
only ever return `Y[0]` = 1024. **Doubly inert.** ⇒ lowering `T` does **not** reshape the PID.
That memory's "five things at once" count should read **two live + three inert/boolean**.

### 🛑 CORRECTION 2 — HONDA'S OSCILLATION RESPONSE IS COHERENT; OUR GAIN IS WHAT BREAKS IT
My first V126 write-up framed the −8192 branch as simply *"the firmware raises a gain"*. The
census shows the design is **deliberate and sensible**: on detecting an oscillation it **disables
a destabilising lane** (`0x3AA70`) **and applies a strong FIXED acceleration feedback**
(`0xC640A`). **That would work — if the fixed term stayed LINEAR.** It does not, because
`|gp-0x6b26|` clamps at 511 and our elevated forward gain makes `|gp-0x6c2c|` far larger than
stock. ⇒ **the defect is the RAIL, not Honda's intent**, and V126's job is to keep the term
inside its linear range rather than to remove Honda's response. ⊕ This also means **−1966 is the
floor, not a target**: cutting further eventually removes the anti-oscillation response itself.

### 🛑🛑 THE SCAN TRAP THAT BIT ME — `ld.bu` ENCODES disp16 AS `(disp & 0xFFFE) | 1`
A whole-image scan for `gp-0x671a` at displacement **`0x98E6` returned ONE hit** — the `st.b`
writer — and I nearly concluded the record's *"8 hits, 6 reader functions"* was stale. **Every
reader is `ld.bu`, which stores the displacement as `0x98E7`.** Scanning both forms returns
**exactly 8**, matching the record. ⇒ [[accord-v850-scan-traps-formatv-and-storezero]]'s
`hw2 = (disp|1)` trap applies to **`ld.bu`/`ld.hu` reads, not just the forms already listed** —
and a *low* count is as much a symptom of it as a wrong one. **Always scan `disp` AND `disp|1`.**
⊕ Ghidra could not help here: `get_xrefs_to 0xFEDF18E6` returns **"No references found"**,
because gp-relative accesses are never resolved to absolute RAM addresses in this program.

## 🛑🛑🛑 **THE OSCILLATION BRANCH — THE FIRMWARE RAISES Y WHEN IT DETECTS AN OSCILLATION. V126 BUILT.**
**A NEW LEVER, and the best-targeted one in the kit's record.** `FUN_00036c12` picks the
`gp-0x6b26` acceleration-feedback scale `Y` three ways — decompiled AND disassembled this session:
```
   if (gp-0x671a < 0xff) and (gp-0x67f4 == 1):
       if gp-0x671a < cal(0xC64FD)=5:  Y = LERP(mode record, index = VOTED VEHICLE SPEED)
       else:                           Y = cal(0xC640A) = -8192   <- ld.h 0x740a,tp,r12 @0x36CB4
   else:                               Y = cal(0xC640C) = -3277   <- ld.h 0x740c,tp,r12 @0x36CBA
   gp-0x6b26 = clamp(((c2c_gated * Y) >> 6) * 273 >> 18, +-cal(0xC407E)=511)
```
🛑 **`gp-0x671a` is the hard-reversal counter and it is CLAMPED to CEIL = 5**
(`min(revcount, CEIL)` @`0x42A12`, the only `st.b` writer image-wide) ⇒ **`>= 5` is reachable ONLY
when the counter has SATURATED** = 5+ hard reversals, held 5.0 s. **The fallback IS the oscillation
branch.** And Honda's schedule tapers `Y` with speed while the fallback is a **flat −8192**:
```
   speed     LERP Y    fallback/LERP          speed     LERP Y    fallback/LERP
    5 km/h    -8806        0.93x              44 km/h    -4442        1.84x  <- HIS EVENT
   15 km/h    -6758        1.21x              64 km/h    -3366        2.43x
   24 km/h    -5519        1.48x              90 km/h    -1966        4.17x
```
⇒ **on detecting an oscillation the firmware MULTIPLIES the term by up to 4×, at exactly the
speeds where the symptoms live**, driving `|gp-0x6b26|` into its 511 rail — where it is
`sign(α)·511`, a **bang-bang Coulomb relay**, V80's measured mechanism. **A relay ratchets; it does
not damp.** A positive-feedback trap: oscillate → detector arms → bigger Y → rail → relay.

### ✅ IT EXPLAINS THREE THINGS AT ONCE, INCLUDING A NULL THE KIT COULD NOT EXPLAIN
1. the **peak-turn oscillation at 44 km/h**, hands-off, engaged — a **1.84×** jump;
2. **grinding at 15–40 mph and NEVER below 5–6 mph** — the ratio is 0.93× at creep and rises
   monotonically with speed. V107 noted *"the symptom map and the rail-duty map are the same
   map"*; **this supplies the mechanism**;
3. ⭐ **why the `0xCBE74` ×1.5 dose MEASURED INERT** — if the counter saturates during the
   manoeuvre the **mode record is BYPASSED entirely**, so no dose on it can act.
   ⇒ [[accord-cbe74-dose-measured-inert-wrong-mode-record]] is **RESOLVED**.

### ✅ V126 BUILT — 5 payload bytes on a V124 base, cal-only, no code or cave edit
```
   0xC640A   -8192 -> -3277    THE EDIT -- the oscillation-branch Y
   0x55DF2    9544 -> 94DA     427 probe source, gp-0x6ABC -> gp-0x6B26
   0x55E10      a3 -> a2       packer sar 3 -> 2, sized to the +-511 clamp
```
image `d6aacb4d563cc7726db8bcf94b659b30341a510dab64a086c93b23c0402707d0` ·
rwd `190231aa4021fe663a7490c1a966a6ef4777241044c3af2bf54caa7306d30d83` · **56/56, CRC 50/50.**
⊕ **−3277 is not invented** — it is Honda's own value at `0xC640C` for **this same variable in
this same function**, so it is inside the calibrated range by construction. New ratios: creep
0.37×, 24 km/h 0.59×, **44 km/h 0.74×**, 64 km/h 0.97×, 90 km/h 1.67× ⇒ at his event, detecting
an oscillation now **REDUCES** Y instead of raising it, a **2.5×** change in the term.
✅ **BLAST RADIUS IS THE SMALLEST IN RECENT MEMORY**: `0xC640A` has **1 reader, 0 writers**
(whole-image byte scan for the tp-displacement **and** instruction-boundary disassembly — the
scan hit `0x36CB6`, the SECOND halfword of a 4-byte `ld.h` starting at `0x36CB4`), and the branch
fires **only while the reversal counter is saturated** ⇒ **every other moment of driving is
behaviourally identical to V124.**

### ✅ THE PROBE MEASURES THE ONE QUANTITY THE KIT HAS GOT WRONG
`wire = min((|gp-0x6b26|·5) >> 2, 0x3FF)` ⇒ the 511 rail maps to **638 of 1023: no clipping**,
LSB 0.8 counts, **rail duty directly countable**. ⚠ 427 is 49.9 Hz and the lane's −3 dB band
(25–153 Hz) is above Nyquist, so this wire **cannot** measure the lane's SPECTRUM — that blindness
is exactly what voided V107's safety case. **Rail duty is a LEVEL statistic**, and undersampling
an ergodic signal leaves it unbiased. This probe measures duty, and nothing else.
🛑 [BELIEF] that lowering `0xC640A` de-rails the term on-car. **Duty CANNOT be predicted
open-loop here** — V107 predicted ≤1.05 % and measured 33.49 %, a **32× miss**, because
`gp-0x6b26 → aggregator → motor → motor rate → gp-0x6c2c` is a **CLOSED LOOP**. Hence the probe
rather than an asserted number. ⊕ Next rung if V126 under-delivers: **−1966**, which never exceeds
the schedule at any speed.

## 🛑🛑 **THE KNEE/K1 LADDER IS EXHAUSTED — V122/V124 IS ITS LAST RUNG**
Every build since V111 has raised the Coulomb knee with K1 scaled to hold the small-signal gain
**exactly**: `(K1/1024)·(12/knee) = 0.0039844`. That invariant has a hard end, because **K1 ≥ 1024
inverts the residual's sign** — friction would exceed `|model|`.
```
   knee    K1 required   possible?      relay saturates at   viscous slope /(deg/s)
    600        204       yes             10.6 deg/s            0.094242   <- STOCK
   1800        612       yes             31.8 deg/s            0.031414   <- V112
   2400        816       yes             42.4 deg/s            0.023561   <- V116
   3000       1020       yes             53.1 deg/s            0.018848   <- V122/V124  LAST RUNG
   3300       1122       NO -- >1023     58.4 deg/s            0.017135
   3600       1224       NO -- >1023     63.7 deg/s            0.015707
```
🛑 **`MEASURED_DUTY` still lists a 3600 rung — it is UNREACHABLE.** Do not propose knee 3300+ as a
gain-holding step; it cannot be built. **The friction axis is closed at V124.** Further grind-#1
work must come from a different lever, which is exactly why `0xC642A/C` (pending V125's probe)
matters.

### 🛑🛑 AND THE RELAY IS **SATURATED THROUGH THE OSCILLATION** — STRUCTURALLY, NOT BY CHOICE
A 2°-peak 7.8 Hz oscillation has peak rate **98 deg/s**. V124's relay saturates at **53.1 deg/s**.
⇒ through the operator's peak-turn oscillation the friction term is **past its knee**, i.e. a
**constant-magnitude force opposing motion — textbook Coulomb friction, the classic stick-slip and
limit-cycle driver.** Making it viscous across that range would need knee **5542 / K1 1884** —
**impossible** by the ceiling above.

⊕ **THE TRADE IS PICK-TWO, and it is the operator's own tension made precise.** With
`plateau = K1/1024`, `sat_rate = knee/56.545`, `slope = plateau/sat_rate`, you may choose any two:
- **grind #1** wants a **large low-rate slope**;
- **the peak-turn oscillation** wants a **small plateau** (weak Coulomb) **and a high sat rate**;
- his standing instruction wants **low apparent friction** overall.
One relay cannot serve all three. ⇒ **a genuinely new lever is required for the oscillation**, not
another rung. ⚠ The one same-axis option left is **knee 3000→4200 with K1 HELD at 1020**: low-rate
friction −29 %, saturation 53→74 deg/s, plateau unchanged — **characterised, NOT recommended**,
because it trades measured grind performance for an unmeasured oscillation benefit and would
confound V124's three existing edits.

## 🛑🛑 **V122 COULD NOT HAVE IMPROVED AUTHORITY — IT CARRIES V112'S GAIN, UNCHANGED**
The operator flew V122 and reported *"on the improved LKAS authority, it does not feel like it has
improved at all."* **That is the correct result for that build.** Byte-verified from the images:
```
   build   gain 0xC6CD0   full-command forward   clamp 0xC61B2      governor 0xC6202
   STOCK      65535             30719            512  CLIPS 98.3%     4762  9.30x free
   V112        5346              2505           3072  (82 % used)     4762  1.90x free
   V122        5346              2505           3072  (82 % used)     4762  1.90x free   <- SAME AS V112
   V124        7128              3341           4096  (82 % used)     4762  1.43x free
```
🛑 **V112 and V122 have the IDENTICAL forward gain.** V122's edits were knee 1800→3000, K1 612→1020
and α2 14→8 — **all three are friction/shape, none is authority.** ⇒ his null is **expected, not
disappointing**, and **V124 is the first build since V112 to raise authority at all** (×1.333).

### ✅ THE 8× FORWARD CHAIN IS CLEAN END TO END — NOTHING DOWNSTREAM CLIPS IT
At full LKAS command the forward value is **3341**, which sits **under the 4096 clamp (82 % used)**
and **under the 4762 governor with 1.43× headroom**. ⇒ **the whole ×1.333 reaches the motor.**
⊕ **The V123 clamp defect is now quantified, not merely asserted**: 8× against the old 3072 clamp
gives 3341 > 3072 ⇒ **8.1 % clipped**, an effective 7.34×. Raising the clamps with the gain was
necessary; the builder's `clamp/gain == 1.000` assertion is the right invariant.
⊕ **Headroom to the governor allows ~11.4× before `0xC6202` binds** — so 8× is nowhere near it, and
**`0xC6202` must NOT be raised** (it is lockstep-shadowed → fault `0x17`).
⚠ [BELIEF] the "full command = 15360 internal units" figure is from the standing record, not
re-measured here. The clamp/governor comparison is in those same units, so the ORDERING is robust
even if the scale is off; an absolute claim about clip margin is not.

### ✅ AND THE "OUR GAIN NEVER REACHES LKAS" SCARE IS REFUTED
`0xC646C` = 891 = stock on every build, and reader #3 (`FUN_0002b62c`) multiplies by it — but a
fresh decompile shows that function is the **BASE-ASSIST** path: two LERP lanes × a ramped enable,
`× polarity × 0xC646C >> 15`, clamped by a per-mode table at `0xC7090`, written to **`gp-0x6AF0`**.
It is **not** the delivered-LKAS formula. The LKAS forward reader is the one V57 moved onto
`0xC6CD0`, which every build since has scaled. ⇒ **the gain edits do reach LKAS.**

## ✅✅ THE 427 PROBE INSTRUMENT IS NOW VALIDATED — and it was BROKEN in three ways first
**Run the control before the measurement, again.** `score_v125_probe.py` was written, then run
against r24 as a dry-run *before* any V125 flight. It reported a clean-looking answer — phase
+73.9°, coherence 1.000 — that was **entirely artefact**. Three defects, each found by a control:

| # | defect | symptom | fix |
|---|---|---|---|
| 1 | `nperseg == NW` ⇒ Welch has ONE segment | coherence identically **1.000**, so the shuffled control could never fail | `NP = NW//4`, then `NW = 512` |
| 2 | **427 is a 50 Hz channel; `cs_rate` is 100 Hz** — truncated to a common INDEX, not TIME | 2× misalignment; coherence **0.512 → 0.049** | regrid both on the 427 frames' own timestamps |
| 3 | coherence **bias ≈ 1/n_segments** | at NW=128 the shuffled null read **0.347** vs a real 0.510 — almost all "coherence" was bias | permutation null (20 shuffles), bar is the **EXCESS** |

✅ **THE POSITIVE CONTROL NOW PASSES DECISIVELY.** r24 (V122) taps `gp-0x6ABC` = wheel rate
× 4.7121, so the wire *is* a scaled |rate| and the answer is known in advance:
```
   corr(|rate|, wire)                  +0.9832
   corr(packer model, wire)            +0.9832    (p50 2 vs 3, p99 319 vs 321 -- BYTE-ACCURATE)
   coherence 6-9 Hz  0.335  vs  permutation null 0.069 +- 0.004
   EXCESS 0.266   z = +60.7            => INSTRUMENT OK
```
⊕ The packer model `min((|rate|·4.7121·5)>>3, 0x3FF)` reproduces the real wire byte-accurately
⇒ **the cave, the tap and the decode are all confirmed on-car.**

### 🛑 TWO FACTS THIS TURNED UP THAT CHANGE HOW CACHES MUST BE READ
1. **`raw14_b4` / `probe` IS NOT CAVE TELEMETRY ON POST-V106 ROUTES.** It is CAN **0x14A byte 4**,
   the *legacy* 5-bit field (bits 7:3) that the V70–V88 caves wrote. V106+ caves write **427
   (0x1AB)** instead. On r24 its low 3 bits are **constant** and its 5-bit field does not track
   anything of ours (corr with |rate| **+0.06**) — yet the extractor still calls it `probe`.
   ⇒ **Any post-V106 analysis that read `probe` as cave output was reading Honda's bits.**
   The real wire is `((b0 & 3) << 8) | b1` on 0x1AB, and it is `ab_mt` in the caches.
2. **🛑 THE 427 WIRE CANNOT MEASURE GRIND #1.** It arrives at **49.9 Hz ⇒ Nyquist 24.95 Hz**,
   and grind #1's band is **21–26 Hz**, which straddles it. Cave telemetry is a **6–9 Hz
   instrument only**. (The 21–26 Hz endpoint itself is safe — it comes from `cs_rate` at 99.8 Hz.)

✅ `--control r24` is now a permanent self-test: change the scorer, re-run it, and if the EXCESS
moves the script broke rather than the car.

## 🛑 A BROAD VIRGINITY SWEEP IS THE WRONG TOOL — and V125's scorer is pre-written
**The sweep, and why it failed.** I scanned `[0xC6000, 0xC7000)` for cells that are virgin across all
117 builds and hold a plausible IIR-alpha value (1-512), then kept those whose implied corner lands
in 1-40 Hz. **It returned 266 "candidates" — which is noise.** The filter cannot tell an alpha from a
LERP table entry, a threshold or a deadband: `0xC61B8` = 102 is in the list, and the kit already knows
it is the **pre-gain deadband**, not a filter coefficient
([[reference-accord-pregain-deadband-c61b8]]).
⇒ **The targeted method works, the shotgun does not.** Every lever found this session — the forward
clamps `0xC61B2/B4`, the trim IIR `0xC63D2`, the candidate `0xC642A/C` — came from **enumerating the
readers of a specific cell and tracing what each one does**, not from scanning for value patterns.
✅ **Recorded so the next session does not repeat the sweep.** A cell is only a lever once its
CONSUMER is traced; virginity and a plausible value are necessary, nowhere near sufficient.

### ✅ `rlog-tools/score/score_v125_probe.py` — written BEFORE the drive
V125 puts `gp-0x6AF0` (reader #3's output) on CAN 427 at sar 4. The scorer asks **one** question:
```
   delivered phase of |gp-0x6af0| vs |wheel rate| at 6-9 Hz, coherence-weighted,
   with a MANDATORY shuffled control

     near +90 deg  -> reader #3 DAMPS      -> cutting 0xC642A/C is the V94 direction, lever CLOSED
     near -90 deg  -> reader #3 ANTI-DAMPS -> cutting it HELPS, build 194 -> ~29
     low coherence -> NOT RESOLVED, build neither way
```
⊕ Same method that settled `gp-0x6b26` after V94 (+137/+139° ⇒ a real damper). ⚠ The wire carries a
**magnitude**, so the sign is lost and only the ENVELOPE phase is recoverable — the scorer says so and
refuses to interpret a phase whose coherence does not clear the shuffled control.
⇒ **One drive on V125 now decides the best-shaped remaining lever**, instead of leaving it an
unbounded guess.

## 🛑 "SAFE BY CONSTRUCTION" WAS AN OVER-CLAIM — and a better-shaped lever that I am NOT proposing
### The over-claim, corrected
For V124's trim edit (`0xC63D2` 6→3) I argued *"reducing the magnitude of a feedback term cannot
destabilise a stable loop, whatever its phase."* 🛑 **That is only true for DESTABILISING feedback.
If the term is dissipative, cutting it is the V94 direction** — and V94 is exactly the case where a
term that looked structurally like **inertia** measured as a **damper** (+137° delivered vs wheel
rate), and removing it made the operator abort. **Structure ≠ delivered sign**, and I do not have the
delivered phase for these feedback paths.
✅ **But the RISK IS BOUNDED, and V124 stands:**
```
   reader #5 is clamped to +-512 = 5.00 % of the aggregator's +-10240
   7.8 Hz transmission:  cal 6 -> 0.1191   cal 3 -> 0.0598
   => the edit moves at most 0.0593 x 5.00 % = 0.297 % of aggregator authority
   V94 removed up to 5.00 % and the drive was aborted  =>  V124's edit is 17x smaller
```
⇒ **[LOW RISK, bounded at 0.297 % of aggregator authority] — not [SAFE BY CONSTRUCTION].** The build
is unchanged; the claim is downgraded.

### A better-shaped candidate, deliberately NOT proposed
```
   0xC642A / 0xC642C = 194   fc 30.15 Hz   |H(7.8 Hz)| 0.9739   VIRGIN on all 117 builds
```
These are reader #3's two input IIRs, and at **fc 30 Hz they pass 97 % of the 7.8 Hz content** — the
path is nearly unfiltered at the oscillation. Lowering 194 → ~29 (fc 4.5 Hz) would **halve** its
7.8 Hz contribution while leaving ≤2 Hz essentially untouched (|H(1 Hz)| 1.000 → 0.976) —
**better selectivity than `alpha2` achieves.**
🛑 **NOT PROPOSED.** Reader #3's output authority is **not bounded** the way reader #5's ±512 clamp
bounds it, so **the downside cannot be capped without knowing its delivered sign.** Proposing it would
repeat exactly the reasoning that this section just retracted.
✅ **What would unlock it:** the delivered phase of reader #3's output (`gp-0x6af0`) against wheel
rate at 6-9 Hz — the same measurement that settled `gp-0x6b26` after V94. **That needs the cell on the
wire, i.e. a 427 repoint** (a 2-byte displacement edit, the proven class — NOT a cave).

## 🛑 CORRECTION: THE "LKAS GAIN" HAS **NEVER** TOUCHED THE FEEDBACK PATHS
```
   build     0xC646C (readers #3/#5/#6)   0xC6CD0 (forward reader #1)
   STOCK          891                        65535
   V90            891                         3564   (4x)
   V101           891                         7128   (8x)
   V112/V122      891                         5346   (6x)
   V124           891                         7128   (8x)
```
✅ **`0xC646C` is 891 = STOCK on EVERY build ever made.** V57 decoupled only the **forward** reader
(#1, `0x2a1ee`) onto `0xC6CD0`; readers **#3 (`0x2b656`), #5 (`0x36686`), #6 (`0x3684a`)** still
multiply by `0xC646C`. Confirmed from the `FUN_0002b62c` decompile: its gain operand is
`tp+0x746c` = **`0xC646C`**, not `0xC6CD0`.
🛑 **⇒ MY V124 RATIONALE WAS WRONG ON ONE LEG.** I claimed the 8× rise multiplies the
positive-feedback trim path by 1.333× and that `0xC63D2` 6→3 pays for it. **The gain rise does not
reach that path at all.**
✅ **TWO CONSEQUENCES, BOTH GOOD:**
1. **The 8× rise is SAFER than I stated.** It touches only the forward path; **the feedback loops
   stay at stock gain**, so it cannot destabilise them. The `m^1.74` vibration law was measured with
   the feedback paths already at stock, so it still applies as measured.
2. **The `0xC63D2` trim lever still stands on its own merits** — it halves a positive-feedback
   contribution at 7.8 Hz (0.1191 → 0.0598) and lowering a feedback magnitude is safe by
   construction. **What is withdrawn is the "it pays for the gain" framing, not the lever.**
⊕ It also re-frames [[reference-accord-c646c-shared-gain-not-lkas-only]]'s warning: that note said
raising `0xC646C` for "4x authority" silently raised two raw-sensor feedback paths. **V57's decoupling
already fixed that, permanently — and no build since has re-coupled them.**
✅ The V124 builder's comments are corrected in place; the image is unchanged (the error was in the
rationale, not the bytes).

## ✅ DELIVERY IS **NOT** SATURATED — V123's gain rise should bite, but with diminishing returns
Before trusting V123's 8× I checked whether the car is already delivering its maximum at the rail.
**It is not.**
```
   30-60 deg (where the rail lives):
     cmd    0-2000   |rate| p50 18.9   p90  66.7    rate per 1000 cmd 18.93
     cmd 2000-3500              24.0        77.6                       8.72
     cmd 3500-4095              19.3        34.9                       5.09
     cmd      4096              26.5       112.1                       6.47
   manual overall:  p50 51.4   p90 123.3   p99 174.5
```
✅ **Rate still RISES with command** (p50 18.9 → 26.5, p90 66.7 → 112.1) ⇒ **nothing hard-clips the
delivery**; the efficiency fall is a **load** effect, not a rail. **This supports V123's gain rise.**
🛑 **But efficiency falls 2.9× from low command to the rail (18.93 → 6.47 per 1000 cmd)** ⇒ **8× will
NOT buy 1.33× more rate. Expect roughly 1.1-1.2×.** Do not promise the clamp ratio.
⭐ **THE AUTHORITY GAP, QUANTIFIED FOR THE FIRST TIME:** at **maximum** command in a 30-60° turn the
car manages **p50 26.5 deg/s**, against **51.4 deg/s** the driver achieves manually. ⇒ **LKAS at full
command delivers about HALF the driver's ordinary steering rate.** That is the operator's complaint,
in one number, and it is why the command winds up to the rail.
⊕ Combined with the windup finding (tracking error **101×** larger at the rail) the picture is
coherent: **the car under-delivers, openpilot winds up, the loop rings at 7.81 Hz, and the command
carries that same 7.81 Hz peak.**

## ✅ THE "r24 IS THE CORPUS MAXIMUM" ALARM IS AN **ARTEFACT OF THE RATIO** — withdrawn
I flagged V122's angle-gated 6-9 Hz ratio (**12.05**) as the corpus maximum. **The absolute levels
say otherwise:**
```
   a2   n     hi-ang p90    hi-ang p50    lo-ang p90     ratio
   22  13       6.510         2.221         ~1.7          2.86
   14   3       3.137         1.151          1.060        3.12     (r22 2.909, r23 8.320)
    8   1       9.871         2.991          0.819       12.05     (r24 = V122)
```
✅ **r24's high-angle p90 of 9.871 sits just above r23's 8.320 — INSIDE the same-firmware spread**
(the two V112 drives differ 2.909 vs 8.320, a factor of 2.9), not outside it.
✅ **The ratio blew up because the LOW-ANGLE DENOMINATOR fell to 0.819, the lowest in the corpus.**
⇒ **`alpha2 = 8` improved LOW-angle behaviour and left HIGH-angle roughly unchanged** — which is
exactly what the operator reported: *grinding better, oscillation still there.* **No evidence it hurt
anything; the implication that it did is withdrawn.**
🛑 **METHOD NOTE, worth keeping:** the angle-gated **ratio** was chosen because it cancels
route-level exposure, and that is still right for cross-build comparison — **but a ratio moves when
either end moves.** A build that improves the denominator looks worse on the ratio while being
better on the car. ✅ **Always report the absolute numerator and denominator beside the ratio.**
⊕ It also explains why the ratio-based alpha2 result earlier looked so strong: part of that signal
was the denominator, not the symptom.

## 🛑🛑 **V122 FLEW (route 24)** — grinding better, authority NOT, and the CAUSE OF THE AUTHORITY CEILING IS FOUND
Operator: *"Grinding: better, still ever so slight grinding in even more rare moments. On the improved
LKAS authority, it does not feel like it has improved at all. I can feel that the manual driving
authority has been loosened, less mass and friction. That is fine but it is only worth it if it means
LKAS authority is improved, which it has not."* Route 24: **832 s, 70.6 % engaged, 14 segments,
fault-free.**

### 🛑🛑 THE HEADLINE: **THE LKAS COMMAND RAILS IN HARD TURNS**
```
   |ang|  30- 60 deg   command RAILED at 99 % of max  51.2 % of the time,  MEDIAN = 1.000
   |ang|  60-120 deg   railed 42.7 %,  median 0.863
   |ang| 120-400 deg   railed 28.0 %,  median 0.737
   |ang|   0- 10 deg   railed  0.0 %,  median 0.032
```
⇒ **In hard turns openpilot is already commanding 100 % and cannot ask for more.** ✅ **This is the
answer to the operator's standing complaint** (*"max steering wheel acceleration and velocity still
seem low for what I would expect for 6×"*): **the ceiling is the COMMAND, not the firmware.**
⇒ **No firmware edit acting DOWNSTREAM of the command can add authority there** — which is exactly
why V122's friction change showed up in MANUAL (where the driver supplies the torque) and not in LKAS.

### ✅ THE DATA CONFIRMS HIS REPORT PRECISELY
```
                    ENGAGED p99 rate   MANUAL p99 rate   ENGAGED p99 accel
   V112 (r23)            60.5              82.2              1831
   V122 (r24)           106.9             174.5              1564
                        +76.6 %          +112.2 %           -14.6 %
   engaged/manual ratio  0.74  ->  0.61
```
✅ **Manual gained 112 % against engaged's 77 %, and engaged ACCELERATION fell 14.6 %.** He said manual
loosened and LKAS did not improve; **the measurement says exactly that.**

### 🛑 THE PRE-REGISTERED GRIND ENDPOINT SAYS "NOT RESOLVED" — AND THE OPERATOR SAYS "BETTER"
```
   21-26 Hz engaged share p90:   r22 V112 0.22264 | r23 V112 0.20845 | r24 V122 0.21898
   bands: <=0.180 CONFIRMED | 0.180-0.230 NOT RESOLVED | >0.230 refuted
```
🛑 **V122 lands at 0.21898, inside the V112 two-drive spread ⇒ NOT RESOLVED**, while the operator
reports a real improvement. ⇒ **the endpoint is not measuring what he hears**, confirming
[[accord-the-21to26hz-excess-is-not-the-audible-grind]]. **Trust the operator's report over this
instrument**, and stop treating 21-26 Hz as the grind-#1 endpoint.

### ✅ HIS OSCILLATION EVENT (seg 11) IS **NOT** A SATURATION ARTEFACT
Worst 6-9 Hz window in segment 11: **t = 673.4 s, rms 13.16 deg/s, peak 7.81 Hz, 44 km/h**, 99.6th
percentile route-wide. **Command during the event: p50 0.277, max 0.372 — nowhere near the rail.**
⇒ **the oscillation happens well BELOW saturation**, so it is a different problem from the authority
ceiling. ⊕ **7.81 Hz — identical to the V112 event.** The mode is unchanged.

### ⭐ A SURPRISE WORTH TESTING: the angle-gated oscillation may FALL with gain
```
   gain 3564 (4x)  n=6    median angle-gated 6-9 Hz ratio  3.56
   gain 5346 (6x)  n=10                                    2.15
   gain 7128 (8x)  n=1                                     1.23
```
⇒ **monotone DOWN with gain — opposite to the ~23 Hz vibration** (which rises as `m^1.74`).
🛑 **NOT established**: n = 1 at 8×, and the 6× group spans **0.66 to 12.05, a factor of 18**.
⚠ **And r24 (V122) itself is 12.05, the HIGHEST ratio in the corpus** — which cuts against the trend.
✅ But if it holds, **8× would improve BOTH complaints** (authority ×1.29 at the rail, oscillation
down) at the cost of ×1.65 on the 23 Hz vibration. **That is the trade to put to the operator.**

## 🛑 RETRACTED IMMEDIATELY: the "1.5 kHz signature" of the labelled event was MULTIPLE-COMPARISONS NOISE
The operator's labelled event (r23, t = 445.6-448.2) appeared to show a tone cluster at
**1457-1561 Hz, +11 to +14 dB over the p95 of 19 matched engaged controls**, and I called it *"the
signature to hunt"*. **The follow-up refutes it.**
```
   1539 engaged audio windows, r23
   Spearman(6-9 Hz steering share, 1.4-1.6 kHz audio share) = -0.167   p = 4.2e-11
   top-20 % oscillation vs bottom-40 %:            ratio 0.79x  CI [0.75, 0.85]
   SPEED-MATCHED 38-68 km/h (n = 184/166):         ratio 0.70x  CI [0.65, 0.77]
```
🛑 **High-oscillation windows carry LESS 1.4-1.6 kHz tone, not more** — the opposite sign, and
significant.
✅ **The error was structural and I should have caught it before claiming**: **one** labelled window
against **19** controls, scanned across **~4000 frequency bins**. The p95 of 19 samples is
essentially their maximum, so **a large number of bins clear it by chance**. A family-wise
correction was required and was not applied. ⇒ **any single-window acoustic "signature" found this
way is noise unless it replicates across windows.**
⚠ The negative correlation is probably **normalisation**, not physics: the tone share is divided by
300-3000 Hz power, and if the oscillation adds broadband energy there the share falls. **Do not read
it as "the oscillation suppresses a 1.5 kHz tone".**
⇒ **STATUS: the acoustic instrument has NOT been shown to see the peak-turn oscillation.** Combined
with the earlier engaged-only case-control finding nothing for the 21-26 Hz grind band, **no acoustic
result in this corpus is currently load-bearing.**
✅ **What would make it load-bearing:** the operator naming the **pitch** (high whine / mid buzz / low
growl), which converts an unbounded 4000-bin search into a **pre-registered band** where a null or a
hit both mean something.

## 🛑🛑 THE 21-26 Hz EXCESS AND THE **AUDIBLE** GRIND ARE NOT SHOWN TO BE THE SAME THING
Two acoustic contrasts on r22 (V112), 710 s of 16 kHz PCM:
```
   1) ENGAGED vs MANUAL  -- USELESS, hopelessly speed-confounded
      engaged median 52.8 km/h vs manual 11.5 km/h, and the excess is a UNIFORM
      +9.5 to +12.6 dB across EVERY band 20-2000 Hz = road/wind noise, not LKAS.
      The speed-matched control could not even run: the arms barely overlap in speed.

   2) ENGAGED-ONLY case-control, speed-matched 30-61 km/h, 224 high-grind vs 189 low-grind
      windows, split on the 21-26 Hz STEERING-RATE content:
        20-50 Hz  +0.78 | 50-60 -0.92 | 60-80 +0.21 | 80-120 +0.57 | 120-200 +0.50
        200-300 -0.03 | 300-800 -0.08 | 800-2000 -0.54 | 2000-5000 +0.03 dB
        strongest lines only +2-3 dB (45, 51, 86, 152, 176 Hz)
```
🛑 **Windows with high 21-26 Hz steering-rate content have NO distinct acoustic signature** —
everything within ±1 dB, with the speed confound properly controlled this time.
⇒ **THE KIT HAS BEEN CALLING TWO DIFFERENT THINGS "GRIND #1":** a **21-26 Hz steering-rate excess**
(measurable, knee- and `alpha2`-responsive) and an **audible grind** the operator actually hears.
**Nothing demonstrates they are the same phenomenon**, and this is the first test that could have.
⚠ **Do not over-read the null either.** The recording carries only **0.01 %** of its power above
2 kHz, so it is heavily band-limited by codec or cabin; a null above ~2 kHz is uninformative. And a
±1 dB resolution on 224 vs 189 windows is not sensitive to a small effect.
⇒ **CONSEQUENCE FOR V122:** its grind endpoint measures the **steering-rate** phenomenon. That is the
only measured axis available and the build stands — **but whether it moves what the operator HEARS is
now explicitly open.** ✅ **The operator's own report remains the primary evidence for the audible
grind**, which is exactly why the pitch question matters: **high whine / mid buzz / low growl** would
tell us in one sentence whether the audible grind is even inside the recording's usable band.
Tools: `rlog-tools/decode/extract_audio_v112.py`, `rlog-tools/decode/audio_engaged_vs_manual.py`.

## ✅ AUDIO IS EXTRACTABLE FOR THE CURRENT BUILD — the 50 Hz ceiling does NOT apply to it
The corpus's blindness above ~49 Hz is a property of the **CAN/IMU** channels (all 100 Hz). The rlogs
also carry **`rawAudioData`** PCM, and it is **not** subject to that limit. Extracted for **r22
(V112)**: **11,364,800 samples = 710.3 s at 16 kHz.**
`rlog-tools/decode/extract_audio_v112.py` (the pre-existing `extract_audio_grind.py` has a stale
`_cache_<tag>` path from the 2026-08-26 reorg and no longer runs).
```
   A) SPECTRUM, share of 50-7800 Hz        B) AM ENVELOPE peak modulation rate
      100- 300 Hz   34.50 %                   100-300 Hz    5.86 Hz    21-26 Hz share 11.6 %
      300- 800 Hz    3.17 %                   300-800 Hz    5.37 Hz                    3.9 %
      800-2000 Hz    5.88 %                   800-2000 Hz   5.86 Hz                    2.0 %
     2000-5000 Hz    0.01 %                   2000-5000 Hz  5.37 Hz                    5.7 %
     5000-7800 Hz    0.00 %                   5000-7800 Hz  5.86 Hz                    9.8 %
      strongest lines: 51, 52, 53, 54, 55, 56 Hz
```
⭐ **THE LEAD: the strongest audio lines are at 51-56 Hz — ABOVE the 50 Hz ceiling of every other
channel.** That is exactly the region where the operator's *"moved to a higher frequency"* would be
invisible to all previous analysis, and it is a candidate for the current grind #1.
🛑 **IT PROVES NOTHING YET.** This is the **whole drive**, not an engaged-vs-manual contrast, so
51-56 Hz could equally be engine or road. ⊕ And the AM peak is **5.4-5.9 Hz in EVERY carrier band**,
which looks like a **common source or an artifact**, not a steering signature — a real grind
modulation would not be identical across five decades of carrier.
⚠ Also note **0.01 % above 2 kHz**: the audio is heavily band-limited, by the codec or the cabin.
Any claim above ~2 kHz is unsupported by this recording.
✅ **NEXT STEP, and it needs no new drive:** align the PCM to the CAN timebase and split
**engaged vs manual**. That isolates the LKAS-specific acoustic component and would settle whether
51-56 Hz is the moved grind #1 or ordinary vehicle noise.

## 🛑 CAVEAT ON V122's ENDPOINT — GRIND #1 MAY BE **ABOVE THE CORPUS'S NYQUIST**
The operator reports grind #1 moved to a **higher** frequency. My within-corpus measures do **not**
reproduce an upward drift on recent builds:
```
   cs_rate engaged band shares (p90 of 1-49 Hz)     21-26   26-34   34-42   42-49   argmax
     V104                                           0.729   0.705   0.027   0.017   21-26
     V105                                           0.528   0.812   0.029   0.026   26-34
     V106                                           0.243   0.689   0.044   0.027   26-34
     V107                                           0.139   0.087   0.022   0.016   21-26   <- collapses
     V111                                           0.168   0.121   0.052   0.038   21-26
     V112                                           0.218   0.140   0.047   0.044   21-26
     V112                                           0.205   0.122   0.041   0.034   21-26
   imu_vert argmax is 42-49 Hz on nearly EVERY build INCLUDING stock (road/tyre background),
     but V111 0.157 and V112 0.134/0.110 sit above V102-V107 (0.073-0.106).
   Mode-frequency drift across builds: 7-9 Hz rho +0.391 p 0.134 | grind rho -0.327 p 0.216
     -- NEITHER resolved, and the grind trend points DOWN, not up.
```
🛑🛑 **BOTH CHANNELS SAMPLE AT 100 Hz ⇒ NYQUIST 50 Hz. Anything above ~49 Hz is INVISIBLE in
this entire corpus**, and the 42-49 Hz figures sit at the aliasing edge and cannot be trusted.
⇒ **The engaged-specific excess I CAN measure on current builds is at 21-23 Hz. Whether that is what
the operator now hears as grind #1 — or something above 50 Hz that no route can show — is
UNRESOLVED.** ⇒ **V122's 21-26 Hz primary endpoint may be aimed at a band the symptom has left**, the
same error class the operator already caught once.
✅ **CHEAPEST FIX, and it is not a drive:** a **phone voice memo during a grind event**, or simply the
**pitch** — high whine (>1 kHz) / mid buzz (200-800 Hz) / low growl (<100 Hz). **A hum or a recording
pins the frequency immediately** and would tell us whether the kit's instruments can see it at all.
⚠ **This does not change the decision to flash V122**: its grind lever is the only measured one, its
authority gain is independent of the band question, and it is bit-identical below 31.8 deg/s. **But
the endpoint may be unmeasurable, so the operator's own report will be the primary evidence.**

## 🛑🛑 THE PEAK-TURN OSCILLATION IS **PROBABLY MECHANICAL** — three independent lines converge
The last untested generator hypothesis was the **`|model|`-scaled signum**: `|model|` rises **7-9×**
with angle, so if it set the generator's amplitude the harmonics would be **angle-gated**. Tested:
```
   by |ANGLE|  0-5 1.102 | 5-10 1.168 | 10-20 1.058 | 20-40 1.377 | 40-400 1.107
               high/low = 1.004   CI [0.843, 1.586]        <- FLAT
   (by SPEED and by |RATE| were already flat)
```
✅ The harmonics are **REAL** (1.233× vs a non-oscillating control, CI [1.060, 1.503]) but track
**NOTHING** — not speed, not rate, not angle. ⇒ **the harmonic signature is INTRINSIC to the mode,
unmodulated by how the car is driven.** That is what a **mechanical** nonlinearity looks like.
**THREE CONVERGENT LINES:** `f0` invariant to a 2× gain change · harmonics track neither firmware
saturation axis · harmonics track no operating variable. ⊕ Plus the ring-down (ζ 0.017-0.036,
**Q 14-29**, motor/rack-side) and the 6-9 Hz anti-damping being **present in stock**.
⚠ **Firmware is not irrelevant** — the oscillation is **engagement-amplified 2.8×**, **angle-gated**,
and its energy is **manufactured downstream of the command** ⇒ **firmware supplies the EXCITATION,
the mechanics supply the MODE.** 🛑 But every firmware excitation path is now closed: move it
(refuted) · damp it (rail-closed) · relay knee (**saturating**) · model bandwidth (GATE 2) · FIR notch
(arithmetically impossible) · `0xC4080` (never-raise) · `alpha2` (**costs** the damper).
✅ **⇒ A MECHANICAL INSPECTION IS NOW WORTH MORE THAN ANOTHER CAL EDIT.** A lightly damped Q 14-29
mode at 7.8 Hz with an intrinsic nonlinearity, motor/rack-side, is the signature of **lash or a worn
compliant element** — intermediate-shaft U-joints, rack bushings, tie-rod ends, the EPS
motor-to-rack coupling. ⚠ **[BELIEF, three convergent measurements] — a direction to check, not a
diagnosis**; the kit has no mechanical instrumentation.
⊕ V122 is unaffected: its grind-#1 lever and authority gain stand either way.
memory: [[accord-the-oscillation-is-probably-mechanical-not-firmware]]

## ✅ V122 IS THE BUILD TO FLASH — and the dose check came back UNINFORMATIVE, which is itself useful
Before recommending the `alpha2 = 8` dose I checked empirically whether cutting the damper worsens
the oscillation, using V109's already-flown `alpha2` 22 → 14 step (a **−1.3 %** damper cut):
```
   large-angle 6-9 Hz p90 / small-angle p90, per route
   a2=22 (n=13) median 2.667      a2=14 (n=3) median 3.269
   a2=14 / a2=22 = 1.225   route-bootstrap CI [0.618, 5.048]
```
🛑 **NOT RESOLVED** — the CI spans a factor of **8**. ⊕ And the reason is stark: **r22 = 2.10 vs
r23 = 10.67 on the SAME FIRMWARE**, a 5× same-firmware spread that swamps any group difference.
⊕ A **1.3 %** damper cut producing a 22.5 % oscillation rise would need **17× amplification** —
implausible ⇒ **the 1.225 is route noise, not a damper penalty.**
⇒ **The empirical check cannot guide the dose in either direction.** The dose therefore rests on the
**arithmetic margin**: `alpha2 = 8` costs **4.3 %** of the damper, **1/20th** of the V94 cut that
caused an abort. **That is sound, and `alpha2 = 8` stands.**
⚠ **Recorded for reading the next drive: the r22/r23 pair spans 2.10-10.67 on identical firmware.**
Any single-drive oscillation comparison must clear that, and almost nothing will.

### ✅ V122 — THE BUILD TO FLASH
```
   39990-TVA,A160-V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST-0x13000-0x100000.rwd
   image  b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0
   .rwd   cf40e9a4af4172fe2a627517cf6657a11bf52ac50d59bb2ca01e2f8c55fcbc6b
   41/41 assertions · 50/50 CRC · 5 payload bytes · cal-only, NO CAVE · zero unattributed vs V112

              knee 0xC40BC   K1 0xC40D2   alpha2 0xC40DC
   V112 (car)     1800           612           14
   V122           3000          1020            8
```
✅ **grind #1 −21.7 %** (the only measured axis) · ✅ **more assist above 31.8 deg/s**, bit-identical
below · 🛑 **the peak-turn oscillation will probably NOT improve** — that mode is mechanical, cannot
be moved or damped further, and `alpha2` costs it 4.3 %.
⚠ Two variables move at once, at the operator's explicit request ⇒ a better or worse drive will not
say which half did it.

## 🛑 V121 WILL PROBABLY FIX **NEITHER** SYMPTOM — the knee axis is SATURATING
Operator asked directly whether V121 fixes both. **Measured answer: no.**
```
   knee   21-26 Hz share   step ratio   relay saturation duty   duty removed
    300      0.63080                        29.08 %
    600      0.24591        2.57x           19.17 %             -9.9 pp
   1800      0.21341        1.15x            6.75 %            -12.4 pp
   3000        --                            3.70 %             -3.1 pp   <- V121's step
```
🛑 **The 1800→3000 step removes only 0.25× as much relay saturation as 600→1800 did — and that
step bought only 1.15× on the band.** ⇒ **V121's expected grind-#1 gain is about 4 %.**
🛑 **On the oscillation its effect is UNKNOWN** — the mechanism failed two independent checks (the
closed-loop simulation, and the harmonics not tracking the relay's saturation axis).
```
                 grind #1                              oscillation
   V121    ~4 %, the axis is exhausted        UNKNOWN, mechanism twice unsupported
   V115    -21.7 % predicted, measured axis   -4.3 % on the damper (a COST, not a benefit)
```
⇒ **This DOWNGRADES V121 as a symptom fix**, and it is a self-correction: V121 was the standing
recommendation for many ticks, and **the corrected 21-26 Hz band is what changed it.**
✅ **V121's honest remaining value is AUTHORITY, not symptom relief**: 1.571× / 1.667× more friction
above 31.8 deg/s ⇒ by the verified polarity, **MORE ASSIST** exactly where the operator reports
acceleration feeling low — and **bit-identical below 31.8 deg/s**, so the risk is near zero.
⇒ **REVISED SEQUENCE: V115 first (grind #1, 5× the expected effect, 1 payload byte). V121 second, and
framed as an AUTHORITY build, not a fix.**

## ✅ V115 IS BYTE-VERIFIED AND **PRE-REGISTERED** — `docs/scoring/SCORING-V115-preregistered.md`
Full diff against V112: **1 payload byte + 1 CRC trailer.** The cleanest single-variable build in the
kit.
```
   0xC40DC   0e -> 08     alpha2 14 -> 8
   0xC4FFC   CRC trailer
   IDENTICAL: knee 1800 · K1 612 · K0 0 · pole 408 · clamp 511 · gain 5346 · Lever B FB / 5244
   sha256 5f804a8a2aee5e18da226cfebe4b2bec564713a4183613e3aed846460a191a97
```
**PRIMARY ENDPOINT: the 21-26 Hz engaged share**, p90, as a fraction of each window's own 1-45 Hz
power. **V112 baseline 0.21341**; lane arithmetic predicts **about 0.167**.
```
   <= 0.180        alpha2 CONFIRMED -- next step is a2 = 6 (-35.2 % grind, -8.7 % damper)
   0.180 - 0.230   NOT RESOLVED -- inside the V112 two-drive spread; call it neither way
   >  0.230        alpha2 REFUTED for grind #1 -- stop this axis, fly V121
```
🛑 **The band is 21-26 Hz, NOT 18-22** — the old bands straddle the real peak and both miss it,
which produced every grind-#1 null this session.
Secondary, reported but never overturning the primary: **peak frequency** (V112 21.09/21.29 Hz,
expect ≤ 21.1; a RISE contradicts the mechanism) · **the damper must survive** (6-9 Hz p90 at
|ang| ≥ 20°; a large rise is the **V94 signature ⇒ revert**) · **assist** (engaged p99 |rate| ≥ 77.1
deg/s) · **`STEER_STATUS == 4` must be 0**.
✅ **Honest split recorded in the card: the STRUCTURAL half is strong** (selectivity is arithmetic
from the traced lane; 20× safety margin vs V94), **the EMPIRICAL half is weak** (`alpha2 = 14` on only
3 routes ⇒ collinear with build era; arithmetic assumes the 1 kHz rate).

## ✅✅ `alpha2` **IS** THE FREQUENCY-SELECTIVE LEVER — V115 is the recommended flight for GRIND #1
`alpha2` = `cal(0xC40DC)` is the EMA-A coefficient in `FUN_00041464` (`state += (diff*alpha2)>>6`
⇒ alpha = alpha2/64), and its input is a **first difference**, so the lane is `|1-z^-1|*|H_ema|` —
**a differentiator whose response RISES with frequency.** ⇒ lowering `alpha2` cuts **high**
frequencies far more than low ones. **Selectivity by construction.**
```
   freq       a2=22      a2=14      a2=8      8/14     what lives there
    3.0 Hz   0.018831   0.018795   0.018665  0.993x   LKAS command band -- UNTOUCHED
    7.8 Hz   0.048680   0.048071   0.046008  0.957x   the oscillation / damper   -4.3 %
   23.4 Hz   0.138812   0.126319   0.098848  0.783x   GRIND #1 PEAK             -21.7 %
   50.0 Hz   0.251820   0.194102   0.122891  0.633x
```
✅ **5.07× more cut at grind #1 than at the damper; 0.993× at 3 Hz** ⇒ the band where **steering
velocity and acceleration live is untouched.** **It removes loop gain at 21-26 Hz without adding
mass, friction or inertia** — the operator's constraint, satisfied by construction.
✅ **SAFETY GATE PASSES against the kit's worst precedent:** this is the lane **V94 cut 6×**, after
which the operator **aborted** — and `alpha2` 14→8 costs only **4.3 %** of that damper, **1/20th** of
V94's change. ⊕ **The precedent is already flown**: V109's 22→14 was selective the same way
(damper −1.3 %, grind #1 −9.0 %, **7.19×**) and flew **fault-free on V111 and V112**, the operator's
best builds.
⇒ **V115 (V112 + `0xC40DC` 14→8) is BUILT AND UNFLOWN** — `5f804a8a…` / `f1a47bb7…`, **42/42**,
cal-only. Now backed by **four independent things**: measured amplitude (1.340 [1.12,2.29]), measured
frequency shift (1.113 [1.06,1.17], p 0.035), structural selectivity (5.07×), and a flown precedent.
🛑 Caveats: `alpha2=14` is only on V111/V112 (**3 routes**) ⇒ the empirical half is **collinear with
build era**; the arithmetic assumes the **1 kHz** rate; `alpha2` also cuts **35-50 Hz by 30-37 %**
(grind #2 territory — likely helpful, **unverified**).
⇒ **SEQUENCE: V115 first, then V121.** memory: [[accord-alpha2-is-the-frequency-selective-lever]]

## ✅ THE `alpha2` DOSE LADDER, AND ITS FLOOR — so the next step is chosen, not improvised
```
   a2   EMA corner   3 Hz cmd   7.8 Hz damper   23.4 Hz grind#1   selectivity   note
   14     34.8 Hz     1.000x       1.000x           1.000x           --        CURRENT (V111/V112, flown)
   12     29.8 Hz     0.999x       -0.8 %           -5.0 %          6.47x
   10     24.9 Hz     0.997x       -2.0 %          -12.0 %          5.87x
    8     19.9 Hz     0.993x       -4.3 %          -21.7 %          5.07x      <- V115, BUILT
    6     14.9 Hz     0.985x       -8.7 %          -35.2 %          4.04x      the practical knee
    5     12.4 Hz     0.977x      -12.7 %          -43.7 %          3.44x      caution
    4      9.9 Hz     0.963x      -18.8 %          -53.2 %          2.83x      caution
    3      7.5 Hz     0.934x      -28.7 %          -63.9 %          2.23x      toward the V94 direction
```
✅ **A PRINCIPLED FLOOR:** the EMA corner falls with `alpha2`, and **at `a2 = 4` it reaches 9.9 Hz —
BELOW the 23.4 Hz target and close to the 7.8 Hz mode.** Past that the filter **eats the damper faster
than it eats the grind**, which is why selectivity collapses from 5.07× to 2.83× and then 1.27×.
⇒ **`alpha2 >= 6` is the usable range; `alpha2 <= 4` is the V94 direction.**
⇒ **FLY V115 (`a2 = 8`) FIRST, NOT a bigger dose.** It is already built (42/42), it is the smaller
step from the flown 14, and the empirical half of the `alpha2` case rests on **3 routes**. **`a2 = 6`
is the identified next step** — it nearly doubles the grind cut (−35.2 % vs −21.7 %) for a damper cost
of **−8.7 %**, still ~10× smaller than V94's −83 % — **but only after V115 shows the axis works on the
road.** 🛑 **Do not build `a2 = 6` yet**: seven unflown artifacts already exist, and a bigger dose
flown first would confound a larger effect with a larger cost.

## 🛑🛑 GRIND #1 IS A **MOVABLE POLE** — and `alpha2` (`0xC40DC`) is its handle
Same test that classified the 7.8 Hz mode as **mechanical** (`f0` invariant to a 2× gain change),
applied to grind #1 on the **corrected 21-26 Hz band**, 13 Lever-B-ON routes:
```
   B) FREQUENCY   a2_C40DC (14 vs 22)  rho +0.587  p 0.035  hi/lo 1.113  CI [1.06, 1.17]  <== HIT
   A) AMPLITUDE   a2_C40DC             rho +0.537  p 0.059  hi/lo 1.340  CI [1.12, 2.29]  <== HIT
                  knee_C40BC           rho -0.406  p 0.168  0.622 [0.29, 1.52]
```
✅ **`alpha2 = 22` → ~23.5 Hz; `alpha2 = 14` → ~21.1 Hz**, both CIs excluding 1.0 ⇒ **grind #1 is a
CLOSED-LOOP POLE, relocatable in firmware, not merely dampable.** **A categorically better position
than the oscillation**, where *move it* is refuted, *damp it* is measured-closed, and only *excite it
less* remains.
✅ **`alpha2` moves BOTH endpoints the same way**, and **V109 already went 22 → 14** — correct on both,
which the kit could not have known while measuring the wrong band.
✅ **`V115` (`alpha2` 14 → 8 on a V112 base) IS ALREADY BUILT AND UNFLOWN** — `5f804a8a…` /
`f1a47bb7…`, 42/42. **The direct next step on this axis, no new build needed.**
🛑 **CONFOUND:** `alpha2 = 14` exists only on V111/V112 (3 routes) ⇒ **collinear with build era**.
⇒ **[EVIDENCE the frequency is firmware-movable; BELIEF that `alpha2` specifically moves it.]**
⚠ `K1` also hits both but is perfectly confounded with `knee`. ⚠ The friction-row `rho = +0.729,
p = 0.005` has arms of **5 vs 1** — **not a result.**
🛑 Before flying V115, check `alpha2`'s **other** role: it sets the `gp-0x6b26` bandpass upper corner,
and lowering it **rotates** that vector (damping up, mass down). **Not analysed here.**
memory: [[accord-grind1-is-a-movable-pole-and-alpha2-is-its-handle]]

## 🛑🛑 OPERATOR CORRECTION: **GRIND #1 MOVED UP** — the kit's bands miss it, and the KNEE **IS** its lever
> *"grind #1 has moved to a new, higher frequency since a few firmware versions ago."*

**Every grind-#1 measurement in this session used 18-22 Hz** — its band in the V62 era. **He is
right, and that invalidated all of them.**
```
   ENGAGED-minus-MANUAL excess, peak location (within-route, so road/exposure cancel):
     STOCK        15.0 Hz (+4.4 dB)
     V90..V96     28.1 / 20.3 / 32.8 / 28.3 / 20.5 Hz
     V100..V107   22.9 / 22.7 / 23.4 / 24.6 / 27.0 / 21.1 Hz
     V111, V112   20.9 / 23.2 / 23.4 Hz        <- recent builds cluster 21-23.4
```
🛑🛑 **Stock peaks at 15.0 Hz, every mod at 20.3-32.8 ⇒ the kit's TWO bands (18-22 and 26-31)
STRADDLE the real peak near 23 Hz and BOTH MISS IT.**

### ✅ RE-RUN ON 21-26 Hz — THE KNEE IS A MEASURED GRIND-#1 LEVER
```
   band                      knee300  knee600  knee1800   300/1800        300/600 (n=8 vs 7)
   18-22 Hz (what I used)    0.26082  0.23104   0.33799   0.772 [0.575,1.169]      --
   21-26 Hz (the real peak)  0.63080  0.24591   0.21341   2.956 [1.164,4.079] <==  2.565 [1.010,4.664] <==
   26-31 Hz (kit's other)    0.19954  0.17920   0.10255   1.946 [0.986,7.375]      --
```
✅ **Monotone across all three knee levels; BOTH contrasts exclude 1.0, including the well-powered
n=8-vs-7 arm.** Raising the knee cuts the band ~2.6-3×. On the old band the same data gives **0.772,
pointing the WRONG WAY** — exactly what I reported.
🛑 **`c91a1ba5` — "the knee has NO measured dose-response on grind #1" — is WITHDRAWN.** It was a
**band error, not a null.** ⊕ And the operator's own report — grind #1 going constant → *"rare… a few
moments"* exactly when the knee went 600 → 1800 — which I could not reproduce and treated as
unsupported, **was right; my instrument was mis-aimed.** ⊕ The earlier "four predictors at p<0.10 that
contradict the operator" result used the same wrong band.

### ✅ CONSEQUENCES
1. **V121 (knee 1800 → 3000) now has a MEASURED dose-response behind it on grind #1** — more than its
   oscillation rationale ever had.
2. **`docs/scoring/SCORING-V121-preregistered.md` is CORRECTED**: grind #1 is **no longer excluded as
   an endpoint**, and its band is **21-26 Hz**.
3. ⚠ `n = 2` at knee 1800, and knee is **perfectly confounded with K1** ⇒ what is established is
   *"the knee-or-K1 axis cuts grind #1"*, **not which cell.**
4. ⚠ **Re-examine every other grind-#1 null in this session on 21-26 Hz** before trusting it.
memory: [[accord-grind1-moved-up-and-the-knee-IS-its-lever]]

## 🛑 THE IMU LEVER HUNT RETURNS NOTHING — and it was PRE-REGISTERED as uninformative if so
Ran the natural-experiment design with the new IMU outcome on all Lever-B-ON routes:
```
   route IMU eng/man:  r77 0.795 · r22 0.801 · r7e 0.961 · r1e 1.015 · r7f 1.113
                       r78 1.138 · r21 1.176 · ra6 1.451 · ra4 2.550
   gain_C6CD0  1.134 [0.77, 2.46] not resolved      biq_C649B  1.134 [0.77, 2.46] not resolved
   knee / K1 / alpha2 / friction row : too few routes per arm (3/1, 8/1, 2/7, 4/1)
```
🛑 **Nothing resolves, and per the instrument's own pre-registration that means NOTHING.** The IMU
is **~10× diluted** ([[accord-the-imu-is-a-valid-but-weak-grind-instrument]]) and only **9 routes**
carry usable IMU with Lever B held constant, with arms of **1-4 routes**. **Only a positive IMU result
is informative; these nulls are not evidence of absence** and must not be cited as such.
⚠ One unexplained observation, recorded not acted on: **`ra4` (V104) sits at 2.550, 2.2× the next
highest.** No cal in the set explains it. It is a single route.

### ⇒ THE HONEST STATE OF THE SEARCH, AFTER CLOSING MOST OF IT
| avenue | status |
|---|---|
| move the 7.8 Hz mode | **REFUTED** — `f0` invariant to a 2× forward-gain change |
| damp it more | **MEASURED-CLOSED** — the ±511 rail; `0xC407E` faults if raised |
| excite it less — relay knee | **V121 built**, mechanism failed two independent checks |
| excite it less — model bandwidth `0xC50D8` | **GATE 2 BLOCKED** — +63.4° phase, sign undetermined |
| frequency-selective filters | **arithmetically closed** — 3-tap FIR cannot notch without killing DC |
| Coulomb floor `0xC4080` | **NEVER-RAISE**, corroborated by this session's own measurement |
| angle handle, table (b) | orthogonal, **untested**, modest (~17 %) |
| grind #1 | **unmeasurable** without creep exposure; the IMU is too diluted to substitute |
🛑 **The binding constraint on BOTH symptoms is DATA, not analysis.** Further analysis passes on this
corpus are producing underpowered results, and saying so is more useful than producing more of them.
✅ **The three asks in `docs/scoring/SCORING-V121-preregistered.md` remain the highest-value actions**,
and none needs a build or a flash.

## ✅⚠ THE IMU IS A **VALID BUT WEAK** GRIND-#1 INSTRUMENT — and it needs no creep exposure
Every grind-#1 measure so far uses **steering rate**, which needs creep exposure **no post-V107 route
has**. Grind #1 is **audible and felt** (*"it vibrated the entire car"*), so a chassis accelerometer
measures it directly. ✅ **`imu_vert`/`imu_lat` log at 100 Hz on all 17 routes** (ratio 1.00 vs
`cs_rate`, checked first) ⇒ **Nyquist 50 Hz, 18-22 Hz genuinely visible, not aliased.**
Validated on the Lever B natural experiment, engaged-vs-manual within each drive:
```
   OFF (2 routes) 1.2020    ON (9 routes) 1.0552    OFF/ON = 1.139   CI [1.005, 1.338]
```
✅ **It discriminates** — CI excludes 1.0. 🛑 **But only just** (lower bound 1.005), and it recovers
**1.139×** where the steering-rate instrument recovers **2.32×** for the same known effect ⇒
**dilution about 10×**; a true effect `X` shows as about `1 + (X-1)/10.8`, so **it needs a true effect
above ~3× to clear its own floor.**
⇒ **USE IT** as the only grind-#1 instrument that works on routes with **no creep exposure**.
🛑 **DO NOT use it to declare a null** — at 10× dilution *"the IMU shows nothing"* is consistent with a
real 2× change. **Only a POSITIVE IMU result is informative.** ⚠ Validated at 18-22 Hz only;
re-validate before using it at 6-9 Hz.
memory: [[accord-the-imu-is-a-valid-but-weak-grind-instrument]]

## ⭐ A NEW, VIRGIN CANDIDATE: the model's own bandwidth `0xC50D8` — blocked on GATE 2, not on hazard
**The mechanism, quantified for the first time.** `FUN_0003b8f6` is the **1 kHz** plant-model
observer; its input passes **two cascaded EMA stages** at `pole2 = 0xC50D8 = 122` (`alpha/4096`):
```
     1.0 Hz  two stages 0.9586      7.8 Hz  0.2758  <- THE MODE      20 Hz  0.0548
   => at the mode the MODEL sees only 27.6 % of the real content, so ~72 % of the 7.8 Hz motion is
      classified as DISTURBANCE and the friction signum CHASES it.  That IS stick-slip, quantified.
   to pass 50 %: pole2 = 196 (1.6x)    80 %: 382 (3.1x)    90 %: 560 (4.6x)
```
✅ **The hazard that would have blocked it is CLOSED.** `0xC50D8` sits in `[0xC5000, 0xC5FFC)`, and
[[reference-crc-chain-is-50-blocks-c5000-not-a-gap]] closed that block **on three independent
traces**: boot does a **blank/presence check only**, the app range contains **no CRC32 polynomial**,
and there are **zero xrefs to `0xC5FFC`** in the whole 1 MiB image ⇒ the stale CRC is a **RED HERRING
for V40's ignition fault**, which has its own explanation
([[accord-aggregator-reaches-motor-via-gp6acc-bridge]]). **It is an ordinary editable cal.**
✅ **VIRGIN on all 115 images** — `pole1 = 832`, `pole2 = 122` in stock and in every build ever cut.
✅ **Orthogonal to the K1/knee confound** — it is on neither axis.
🛑 **NOT A BUILD PROPOSAL. It is blocked on GATE 2, and squarely.** The model's input `gp-0x6b98` is
**BROADBAND** ([[accord-v87-flew-the-probe-fired-and-6b98-is-broadband]]) **and downstream of the
assist**, so feeding it into the model is a **feedback path** — widening its bandwidth widens that
feedback, in a loop containing a **lightly damped Q 14-29 mode at 7.8 Hz**. That is exactly the class
where **phase, not just magnitude, decides stability**.
⇒ **What it needs before any build: a GATE 2 magnitude-AND-phase analysis of the `gp-0x6b98` → model
→ residual → assist path at 6-9 Hz.** Until then it stays a candidate. ⊕ Both arguments are on the
record: *widening lets the model explain the oscillation so the signum stops chasing it* vs *widening
increases feedback bandwidth around a lightly damped mode*. **Neither is settled.**

## 🛑🛑 GATE 2 **FAILS IT** — the sign is undetermined, and determining it costs the bricking class
```
   pole2   |H(7.8Hz)|   phase        vs stock gain   phase ADVANCE
     122     0.2758    -113.86 deg      1.000x          +0.00 deg
     196     0.5004     -87.19 deg      1.814x         +26.67 deg
     382     0.7998     -50.42 deg      2.900x         +63.44 deg   <- the 80 %-pass dose
     560     0.9002     -34.13 deg      3.264x         +79.72 deg
```
🛑 **A 63° phase advance**, in a branch that is **added** to the model and then **subtracted**
downstream. With `|residual|² = |M|² + |A|² − 2|M||A|·cos(φ_M − φ_A)`, a 63° move swings the cosine
by up to **0.7** ⇒ **it can make the symptom better OR worse, and magnitude reasoning cannot pick
which.** ⇒ **the lever fails GATE 2 on the phase leg, which is precisely what GATE 2 exists to catch.**
⚠ (My printed rationale said *"~46 deg"* from a stale literal; the computed value is **+63.4°**.)

### 🛑 AND THE MEASUREMENT THAT WOULD SETTLE IT IS NOT CHEAPLY AVAILABLE
Needed: **`arg(ACTUAL) − arg(MODEL)` at 6-9 Hz** — the real torque-sensor response against the
model's reconstruction of it.
⊕ The kit's **+137°/+139°** result is **delivered assist vs WHEEL rate** — a *different pair* — so it
**does not transfer**, however tempting the number is.
🛑 **None of `gp-0x4f60`, the model output `gp-0x6bf6`, or the residual `gp-0x6bfc` has ever been on
the wire** ⇒ the phase cannot be obtained from existing telemetry, and obtaining it requires a
**CAVE PROBE — the only class that has ever bricked this ECU (V24, V27, V48B).**
⇒ **STATUS: BLOCKED, not deferred.** The candidate is real, virgin, hazard-free on CRC, and
orthogonal to the K1/knee confound — **and it still cannot be built**, because its sign is unknown and
the price of learning it is the one risk class this kit refuses on cal-only grounds.
✅ **Recorded so the next session does not re-derive the lever and skip the gate.** The magnitude
argument is seductive (3.6× attenuation at exactly the mode, on exactly the right sensor); **the phase
argument is what kills it.**

## 🛑 CORRECTION — WHICH POLE FILTERS WHICH BRANCH. It was backwards, and the fix STRENGTHENS it.
Re-read of `FUN_0003b8f6`, instruction by instruction:
```
   gp-0x6b98  (command / assist path)  -> TWO EMA stages at tp+0x50d4 = 0xC50D4 = pole1 = 832
   gp-0x4f60  (TORQUE SENSOR)          -> TWO EMA stages at tp+0x50d8 = 0xC50D8 = pole2 = 122
```
I recorded pole2 as filtering the model's input generally. **It filters the TORQUE-SENSOR branch
specifically**, and pole1 — much faster — filters the command branch. At 7.8 Hz, 1 kHz task:
```
   command branch   pole1 = 832  corner 36.3 Hz   two stages |H| = 0.956   <- passes fine
   torque branch    pole2 = 122  corner  4.81 Hz  two stages |H| = 0.276   <- attenuated 3.6x
```
✅ **This makes the mechanism STRONGER.** The torque sensor measures **across the torsion bar** —
**exactly the element whose resonance this is** — and it is the one branch the model attenuates
3.6×. ⇒ **the model systematically under-represents the resonance at the very sensor that sees it,
so `residual = model - actual` carries it, and the friction signum chases it.**
⊕ It also **weakens my own GATE 2 objection**: `gp-0x4f60` is a **measurement**, not a feedback of
our own assist, and the loop through it is Honda's ordinary assist loop, present in stock. The
objection is not void — assist still moves the bar which moves the sensor — but it is **a normal
sensing loop, not a novel feedback path we would be creating.**
🛑 **Still not a build.** GATE 2 needs the magnitude *and phase* of
`gp-0x4f60 → model → residual → assist` at 6-9 Hz, and raising `pole2` **advances phase** in a branch
that is subtracted — sign and phase both have to be worked through, not assumed.

## 🛑 THE MODEL PATH'S 3-TAP FIR **CANNOT** BE MADE A NOTCH — the last hidden-filter hope, closed
`FUN_0003b8f6` contains `y[n] = a·x[n] + b·x[n-1] + c·x[n-2]` with **float** coefficients at
`0xC5048/504C/5050`, feeding the same `|model|` that multiplies the Coulomb signum. Floats in the
CRC-skipped `0xC5000` block — it looked like the frequency-selective lever the kit says does not exist.
```
   a = 10.000000   b = 0.800000   c = 0.400000     sum = 11.2   IDENTICAL stock -> V121
   |H| at 7.8 Hz:  11.1974 @1 kHz (0.02 % below DC)   |   10.9515 @100 Hz (2.2 % below DC)
```
✅ **As shipped it is a near-flat GAIN of 11.2, not a filter** — `b` and `c` are tiny against `a`.
🛑 **And it cannot be retuned into one.** A 3-tap FIR notch at `f0` needs `b = -2cos(w0)`, giving DC
gain `a+b+c` ≈ **0.0024 at 1 kHz** and **0.2375 at 100 Hz** ⇒ **the notch swallows DC**, which is the
model's whole purpose. With only 3 taps the notch Q is ~1 and **7.8 Hz is far too close to DC at
either candidate task rate.** ⇒ **arithmetically closed, not merely risky.**
⊕ It also sits in the block the bootloader skips, `[0xC5000, 0xC5FFC)`
([[reference-crc-chain-is-50-blocks-c5000-not-a-gap]]) — moot now, but recorded.
✅ **What DOES shape this path: the two EMA poles** `0xC50D4` = **832** and `0xC50D8` = **122**
(`alpha/4096`), each applied **twice**. These are 16-bit cals and are genuine frequency handles —
**but they set the MODEL's own bandwidth**, and the chain is a disturbance observer
(`residual = MODEL - ACTUAL`), so detuning them **manufactures residual by mis-modelling** rather
than filtering the symptom. **Not proposed; recorded as the only remaining shaping cells here.**

## ⭐ TABLE (b) IS THE **ANGLE HANDLE INSIDE THE OBSERVER** — orthogonal to the K1/knee confound
Decompiled `FUN_0003b8f6`:
```
   uVar17 = gp-0x6a10                                 <- ABSOLUTE STEERING ANGLE
   if (uVar17 < 0x2711) { LERP tp+0x7b66 (X) / tp+0x7b80 (Y) }   = 0xC6B66 / 0xC6B80 = table (b)
   fVar18 = fVar13 * uVar17 * 0.0009765625 + fVar18;  <- scales a model component INTO the model
```
⇒ **table (b) is ANGLE-SCHEDULED and feeds `|model|` — the exact amplitude that multiplies the
Coulomb signum** (`friction_in = |model|*K1/1024*fVar13 + K0/1024*fVar13`). **It sets part of the
angle-dependence that makes the symptom angle-gated.**
```
   X (deg)  0.00 0.85 1.60 2.12 2.50 3.00 ... 11.94       Y  899 908 981 1060 1083 1084 (flat)
   rise 899 -> 1084 = 1.21x, saturating at 2.5 deg
```
⚠ `|model|` rises **7-9×** with angle and table (b) supplies only **1.21×** ⇒ **most of the rise is
the model itself, not this table.** Do not oversell it.
✅ **Why it still matters: it is ORTHOGONAL.** Every flown mod sits on `K1/knee = 0.34`
([[accord-k1-and-knee-are-perfectly-confounded]]); table (b) is on **neither** axis — it changes
neither the small-signal gain nor the relay shape ⇒ **an independent lever that adds no new point to
the confounded line**, and **angle-targeted by construction**: flattening `Y` to **899** cuts the
high-angle contribution ~**17 %** and **touches nothing below 2.5°**.
🛑 **Modest**, and [[accord-factord-is-the-angle-error-lever]] calls table (b) *"DEAD as a shaped
lever"* because **88.6 % of engaged driving is in its flat first segment** — true for broadband
driving, but the **angle-gated** symptom lives in the other 11.4 %. **A different question, not a
contradiction.** [BELIEF; NOT proposed as a build yet.]
✅ **CLOSED, so it is not re-asked:** the relay's `12` is a **hardcoded `0xc` immediate, not a cal**
⇒ **no third handle** exists to hold the gain while varying `K1` independently of `knee`. **The
confound is structural; separating them requires a gain change (V113).** ⊕ Instruction-level address
confirmations: `knee` `tp+0x50bc`=`0xC40BC` · `K1` `tp+0x50d2`=`0xC40D2` · `K0` `tp+0x5080`=`0xC4080`
· friction EMA pole `tp+0x50d0`=`0xC40D0` — all match the kit's documented addresses.

## 🛑🛑 `K1` AND `knee` ARE **PERFECTLY CONFOUNDED** — a design critique of V121
```
   K1=204 knee= 300 -> V100..V107        K1=204 knee= 600 -> V90,V91,V92,V96,V111
   K1=612 knee=1800 -> V112              STOCK K1=102 knee=600
   knee values flown with MORE THAN ONE K1:  NONE      (every mod holds K1/knee = 0.34)
```
⇒ **the kit has never learned which of the two cells matters** — every result attributed to "the
knee" is equally attributable to `K1`.
🛑 **V121 is `knee 3000 / K1 1020` — ratio 0.34, a FOURTH point on the same line** ⇒ **by
construction it cannot separate them.** *If it works we will not know why; if it fails we will not
know which half failed.*
✅ **Structural, not an oversight:** holding the small-signal gain constant **requires** `K1 ∝ knee`
⇒ **a gain-matched build is inherently confounded**, and separating them **requires a gain change**.
✅ **V113** (`knee 1800 / K1 204`) is the **only built artifact that breaks it** — same knee as V112,
same K1 as V90-V111 ⇒ two K1 levels at one knee, the first separation ever. ⚠ **Cost: gain 0.333×
V112's**, below stock, ⇒ **less assist** ([[accord-friction-polarity-more-assist]]). The mirror
(`knee 600 / K1 612`, 3× gain) is the riskier half.
⇒ **SEQUENCING, recorded so it is deliberate:** **V121 first** — the only candidate that cannot make
normal driving worse (bit-identical ≤ 31.8 deg/s) and it tests the pre-registered endpoint.
**V113 second, ONLY if V121 moves that endpoint** — it is the sole way to learn which cell did it.
**If V121 lands in the “not resolved” band, V113 is not worth its feel cost.**

## ✅ `0xC4080`'s NEVER-RAISE FLAG IS **INDEPENDENTLY CORROBORATED** — and a natural idea is killed
Reasoning that led there: if the generator is **physical** friction, the firmware's counter-lever is
its **friction compensator** — and ours has the **wrong shape**. Real Coulomb friction is
constant-magnitude; ours is `|model|`-proportional:
```
   friction = EMA( |model| * cal(0xC40D2)/1024 * fVar13  +  cal(0xC4080)/1024 * fVar13 )
                    \____ K1, |model|-proportional ____/     \__ K0 = 0, a PURE SIGNUM __/
```
⇒ *"raise `0xC4080` to add a proper constant Coulomb floor."*
🛑 **The kit already flags `0xC4080` NEVER RAISE** — one of three named *flatten-into-a-relay*
hazards ([[accord-plant-model-residual-aggregator-chain]]), and V89 explicitly left it untouched.
✅ **And this session's own discriminator says WHY, independently:** the K0 term has **no amplitude
dependence, so it does not vanish at zero command** ⇒ raising it installs a nonlinearity **active
uniformly across the whole operating range** — **exactly the profile
[[accord-the-harmonics-track-neither-firmware-saturation]] just measured as the generator.**
⇒ **The idea would ADD the thing it was meant to remove.** Correctly flagged; the flag now has a
measured rationale rather than only a structural one.
⚠ A compensator that is constant-magnitude **but gated to vanish near zero** would need a **code**
change ⇒ the cave class that bricked V24/V27/V48B. **Not available.**

## 🛑 THE HARMONICS TRACK **NEITHER** FIRMWARE SATURATION — V121's mechanism weakens again
Two hard nonlinearities sit in the loop and **saturate on different axes**, so they separate: the
**Coulomb relay** on |RATE| (≥ 31.8 deg/s on V112) and the **damper's ±511 clamp** on SPEED (rail duty
15.46 % at 10-25 km/h → 0.23 % above 65, `build_v108` E2).
```
   by SPEED  (16-17 routes, tight CIs)     10-25 1.110 | 25-40 1.159 | 40-65 1.162 | 65-200 1.117
   by |RATE| (7-11 routes, wide CIs)       0-15 1.133 | 15-32 1.096 | 32-60 1.317 | 120+ 1.283
```
✅ **CLAMP hypothesis REFUTED** — well powered, and the ratio is **flat at 1.11-1.16** while the
clamp's own duty falls **67×** across that range. 🛑 **RELAY hypothesis NOT SUPPORTED** — no rise past
31.8 deg/s — ⚠ but that arm is **underpowered**, so **not supported ≠ refuted**.
⊕ Harmonics are **real and pervasive**: every bin > 1.0, most CIs exclude it.
⇒ **A nonlinearity uniformly active across the whole range is not a saturation.** That fits an
always-on mechanism — **physical friction / stick-slip in the column and rack** — better than any
firmware clip, and coheres with the mode being **mechanical** and with the 6-9 Hz anti-damping being
**present in stock**.
🛑 This does **not** overturn [[accord-the-7to9hz-energy-is-manufactured-not-commanded]] — the energy
is still generated downstream of the command. **What changes is WHERE: possibly the PLANT, not the
firmware — in which case no cal edit reaches it.**
🛑🛑 **V121's mechanism has now failed TWO independent checks** (the closed-loop simulation, and
this). ⇒ **It is a build with good engineering properties and a weak mechanism case**: gain held
**exactly** at V112's, more assist above 31.8 deg/s, cal-only, 4 bytes, 40/40, and `knee`'s on-car
track record. **Effect UNKNOWN. Fly it as a TEST, not as a fix** — the pre-registered card's
**> 1.45 = refuted** band is exactly the outcome this makes more likely.

## ✅⭐ THE 7-9 Hz ENERGY IS **MANUFACTURED**, NOT COMMANDED — the hopeful result
16 routes, oscillating windows, band power relative to each signal's **own** 0.5-3 Hz power:
```
   median COMMAND  6-9 / 0.5-3 = 0.00528      median RESPONSE 6-9 / 0.5-3 = 0.13962
   => the response carries 26.5x more RELATIVE 6-9 Hz content than the command
   coherence(cmd, rate) @6-9 Hz = 0.488  vs shuffled 0.356   diff 0.132  CI [0.082, 0.250]
```
✅ **The energy at the resonance is GENERATED INSIDE THE LOOP, not delivered by openpilot** — the
first direct measurement of what [[reference-accord-lkas-lane-is-a-lowpass]] implied.
⭐ Coherence above chance but only 0.488 with 26.5× less relative content ⇒ the command **modulates**
the oscillation without **containing** it: **the signature of a NONLINEARITY** converting a
low-frequency drive into energy at the resonance — matching
[[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]] independently.
⭐⭐ **WHY IT MATTERS.** The mode is a **fixed mechanical resonance** that cannot be moved
([[accord-the-78hz-mode-does-not-move-with-firmware-gain]]) or damped further
([[accord-the-damping-route-is-closed-by-the-rail]]), leaving only *"excite it less"* — and the
obvious worry was that excitation is simply **proportional to 6× torque**, making the operator's two
goals irreconcilable. ✅ **It is not in the command, so it is NOT an inherent price of 6× torque.**
⇒ **the generator can be attacked without giving up torque — the first structural reason to think
both goals are compatible.**
⇒ **V121 status change:** its **PREMISE** (energy generated downstream, attackable without spending
torque) is now **[EVIDENCE]**. 🛑 **Still [BELIEF]: that the Coulomb relay SPECIFICALLY is the
generator** — no measurement isolates it from other nonlinearities. **Effect still UNKNOWN; the
pre-registered card stands as written.**
⚠ `ra4`/`r1e` show command ratios 200-400× the rest with the highest coherences — outliers of a
different kind; medians are used and are robust, but do not pool them naively.

## 🛑🛑 THE 7.8 Hz MODE **DOES NOT MOVE** WITH FIRMWARE GAIN — it is MECHANICAL
A closed-loop pole moves with loop gain; a mechanical resonance does not. The kit classified the
~23 Hz line exactly this way (it **moved 20.3 → 23.0 Hz**). Across 17 routes spanning forward gain
**3564 / 5346 / 7128** and knee **300 / 600 / 1800**:
```
   Spearman(gain 0xC6CD0, f0) = -0.015  p = 0.954     Spearman(knee, f0) = +0.332  p = 0.193
   f0 by gain: 3564 (n=6) 7.764 Hz | 5346 (n=9) 8.008 | 7128 (n=1) 7.617 | stock (n=1) 6.836
```
✅ **`f0` is invariant to a 2× forward-gain change and the group medians are non-monotone** ⇒ a
**FIXED MECHANICAL RESONANCE**, not a relocatable pole. ⊕ Consistent with the ring-down result
(ζ 0.017-0.036, Q 14-29, motor/rack-side).
⚠ **Self-correction:** my script's verdict line said *"f0 MOVES"* on a **max/min spread of 22.9 %** —
dominated by the **single stock route** (6.836 Hz, IQR [6.20, 7.86], overlapping the mods). Spread
across heterogeneous routes is not the test; **the correlation with gain is**, and it is flat.
🛑🛑 **⇒ THE THREE THINGS FIRMWARE COULD DO, AND TWO ARE NOW CLOSED:**
```
   MOVE IT         REFUTED here -- f0 invariant to 2x gain
   DAMP IT         measured-CLOSED by the +-511 rail (0xC407E cannot be raised: V73 -> V74/V75 faulted)
   EXCITE IT LESS  the ONLY route left  ==  V121
```
⇒ **The 7.8 Hz peak-turn oscillation may not be fully eliminable in firmware.** A fixed, lightly
damped mechanical mode that cannot be relocated or damped further can only be **driven less hard**.
✅ That is the correct target definition, not a counsel of despair — and it is exactly what V121 aims
at. 🛑 **Do not promise elimination of this oscillation by any firmware build**; the honest claim is
*reduce how hard it is driven*, which is what
`docs/scoring/SCORING-V121-preregistered.md` measures.

## ✅ **V121's SCORING IS PRE-REGISTERED** — `docs/scoring/SCORING-V121-preregistered.md`
Written **before** the drive so the result cannot be reinterpreted after it. **Primary endpoint: the
harmonic ratio**, one number, with the decision bands fixed now:
```
   < 1.05        relay CONFIRMED as the excitation path
   1.05 - 1.35   NOT RESOLVED -- inside V112's own two-drive spread (0.970-1.455)
   > 1.45        mechanism REFUTED; stop pursuing the relay for this symptom
```
🛑 **V112's own two drives span 0.970-1.455**, so a single V121 drive landing in that band means
**nothing** — recorded now so it is not read as a trend later.
Secondary, reported but never used to overturn the primary: 6-9 Hz p90 at |ang| ≥ 20° matched on
small-angle p90 · **assist check** (engaged p99 |rate| must be ≥ V112's **77.1 deg/s**; below ~70 ⇒
the knee cost authority and **V116 is the fallback**) · `STEER_STATUS == 4` must be **0**.
⚠ **Grind #1 is explicitly NOT an endpoint** — V121 does not target it and it is unmeasurable on
routes with no creep exposure.
✅ **Three operator asks are in the card**, each worth more than another analysis pass: creep
exposure · a mark when grind #1 happens · one stock-configuration drive (p 0.100 → 0.018).

## 🛑🛑 THE DAMPING ROUTE IS **CLOSED** — by the ±511 rail, not by int16
I was about to propose raising `Y[1]`/`Y[2]` of the engaged friction row: it is the one lever whose
direction is **measured on the road**, `Y[0]` has only 1.11× int16 headroom but `Y[1]` has **1.90×**,
and the oscillation's median speed (**35 km/h**) sits between the 20 and 90 km/h knots. `Y[1] =
-24000` is even **flight-proven** — V107 flew it.
🛑 **`build_v108_tva.py` E2 already measured it harmful** (route `1e`, episode-bootstrapped, 10 episodes):
```
   bin (km/h)    V107 rail duty (Y1=-24000)      V106/V108 (Y1=-17202)
    10-25        32.32 % [29.93, 35.68]           <= 15.46 %
    24-40        21.27 % [19.93, 22.51]           <= 10.45 %
      65+        <= 0.23 %                        <=  0.23 %
```
**A damper that hits its clamp 32 % of the time IS A RELAY** — the class that made V80 *"the worst
grinding ever recorded."* ⚠ And at **24-40 km/h, where the oscillation lives, V108 ALREADY rails
≤ 10.45 %** ⇒ **no safe headroom at the symptom's own speed.**
✅ **The binding constraint is `gp-0x6b26`'s ±511 clamp (`0xC407E`), not int16 — and it is
HARD-BLOCKED**: Honda ships 511, one count under its own 512 trip, and **V73 raised it ⇒ V74/V75
hard-faulted.** More damping needs more rail; more rail needs `0xC407E`; that faults the ECU.
⇒ **ONLY EXCITATION REDUCTION REMAINS**, which is exactly what **V121** does (knee 1800→3000,
softening the signum indicted as the excitation path). **V121's case is strengthened BY ELIMINATION**
— its mechanism is still [BELIEF] and its effect still UNKNOWN, but it is the only direction on this
symptom not measured-closed. ⊕ `Y[2]` alone has rail headroom (≥0.03 % duty at 90+) but moves the
35 km/h coefficient only **1.10×** — not worth a flight.

## 🛑 THE DECELERATION TRIGGER **DOES NOT SURVIVE STRATIFICATION** where the symptom lives
Unstratified, the threshold test looked decisive — case rate for `dv/dt` below T vs at/above T,
**all 17 routes**, paired within route:
```
   T = -1.0  8.33 % vs 4.86 %  = 1.72x  CI [1.26, 2.21]      T = -0.4  1.67x  CI [1.23, 2.21]
   T = -0.8  7.83 % vs 4.79 %  = 1.63x  CI [1.16, 2.20]      T = -0.2  1.73x  CI [1.29, 2.26]
   bins: < -1.0 -> 8.33 %   -0.2..+0.2 -> 4.85 %   > +0.2 -> 4.03 %
```
**Every CI excluded 1.0.** 🛑 **Then I stratified on speed × angle, and it largely dissolves:**
```
   stratum                        decel    accel    ratio    CI              routes
   0-25 km/h   ang > 10 deg      30.22 %  21.69 %   1.39x   [0.94, 2.33]      10
   25-50 km/h  ang > 10 deg      18.20 %  14.43 %   1.26x   [0.71, 1.92]      12
   50-80 km/h  ang < 10 deg       2.13 %   0.52 %   4.12x   [1.44, 19.00]     15   <-- only cell that resolves
   80-200 km/h ang < 10 deg       2.12 %   3.29 %   0.64x   [0.00, 12.27]      9   <-- reverses
```
🛑 **The only cell whose CI excludes 1.0 is LOW-ANGLE at 50-80 km/h — which is NOT the peak-turn
regime.** Both high-angle cells, where the operator's symptom lives, **span 1.0**.
⚠ And decelerating windows are **slower**, not faster (median 40.0 vs 48.3 km/h), so the
unstratified 1.7× was partly **composition**, not effect.
⇒ **DOWNGRADED before it was ever claimed: [BELIEF, direction consistent in 5 of 6 strata, NOT
established in the regime that matters].** ⊕ Not refuted either — the direction holds nearly
everywhere and the high-angle cells are simply underpowered (10-12 routes, wide CIs).
✅ **What would settle it: more high-angle exposure**, which is the same gap the drive card already
names. 🛑 **Do not build against this.** ⚠ Two cells report absurd upper CIs (36,631,016) — a
degenerate bootstrap where the denominator approaches zero; **read those cells as uninformative, not
as huge effects.**

## ⚠ A CANDIDATE TRIGGER — **DECELERATING INTO THE TURN.** Suggestive (12/17), NOT established
First use of the operator's **labelled** event as a CASE rather than a description. r23,
t = 445.6-448.2 (his *"exact instance"*), against controls from the **same drive** matched on speed
and |angle| ⇒ route variance cannot apply.
```
   in the 2 s BEFORE      event      control median (n=6)   percentile
   speed                  43.6 km/h        25.4               100th
   d(speed)/dt           -1.159 m/s^2     +0.619                0th
   18-22 Hz rms          14.162            9.739               83rd
   |driver torque| mean 645.1           1113.7                 33rd
```
⭐ Two channels at opposite extremes, and they are **one physical fact: BRAKING INTO A CORNER AT
SPEED** — which matches the operator's own words, *"a fixed oscillation during the peak of a hard
curve."* 🛑 At n=6 that is p ≈ 0.14 — a hypothesis, not a finding.
**Tested corpus-wide** (cases = top 5 % by 6-9 Hz per route, controls matched on speed and |angle|
**within the same route**, bootstrap unit = ROUTE):
```
   12 of 17 routes have cases decelerating MORE than their matched controls
   median difference -0.1720 m/s^2   route-bootstrap CI [-0.2486, +0.0354]
   Wilcoxon signed-rank p = 0.1889    (sign test alone: p ~ 0.07)
```
🛑 **NOT ESTABLISHED** — the CI spans 0. ⭐ **But the direction is consistent (12/17) and this is the
first candidate TRIGGER the kit has had**, as opposed to a gain or a lane.
⚠ **The operator's own event is 6.7× more extreme than the corpus effect** (-1.159 vs -0.172) ⇒
**either his labelled instance is atypical, or deceleration matters only past a threshold** — a
threshold model would not show up in a linear mean comparison. **That is the next test, and it needs
no new data.**
✅ If it holds, it is actionable in a way no previous finding has been: a trigger can be **avoided or
anticipated**, and it points at longitudinal load transfer rather than at a firmware gain.
Tools: `rlog-tools/studies/peakturn/labelled_event_case_control.py`,
`rlog-tools/studies/peakturn/deceleration_precursor_test.py`.

## ⚠ THE DAMPER'S COST IN ACCELERATION — measured, NOT resolved, but the SHAPE is informative
The engaged friction row went **×1.5 (V91..V104) → ×3.0 (V107..V121)**, a natural experiment on the
operator's own complaint. Outcome = **p99 |d(rate)/dt| engaged vs manual within the same drive**
(exposure cancels). Only 4 routes carry ≥3,000 frames in *both* arms:
```
   dose    n   median eng/man acc ratio   median engaged rate p99
   1.5x    2          3.051                     66.2 deg/s
   3.0x    2          1.689                     77.1 deg/s
   x3.0 / x1.5 = 0.554   route-bootstrap CI [0.350, 1.039]
```
🛑 **NOT RESOLVED** — CI spans 1.0 and **n = 2 per arm is below this kit's own stated minimum.**
⭐ **But the shape cuts against the simple story: engaged RATE p99 went UP (66.2 → 77.1 deg/s).**
⇒ if the damper costs anything it is **acceleration headroom, not top steering velocity.** The
operator reports both as low; **the velocity half is not visible in the data.**
⇒ **[BELIEF, ~0.55× point estimate, unresolved]** — do not quote as a measured cost. It resolves by
**instrumenting the next build**, not by re-flying a historical dose.

### ⇒ WHERE THE OSCILLATION WORK STANDS, CONSOLIDATED
| lever | status |
|---|---|
| **relay knee** (V121 `0xC40BC` 3000 / `0xC40D2` 1020) | **BUILT, 40/40.** Gain held exactly at V112's ⇒ bit-identical ≤31.8 deg/s, more assist above. Harmonic rationale **weakened**; effect **UNKNOWN**. **The recommended flight.** |
| **engaged friction row** (the 6-9 Hz damper) | **DO NOT CUT** — V94 cut it 6× and the drive was aborted; delivered +137° vs wheel rate ⇒ real damper. Only **1.11× headroom** at `Y[0]` before int16 overflow. |
| **Lever B** | **already on the car** (V104..V121) — best measured grind-#1 fix. |
| **Lever A** (V62 `sar`×2) | absent from all 25 builds, **correctly** — its r24 half caused grind #2. |
| rate-scheduled `Kd` · FactorD · table (b) · `0xC64DE` · arbitration restore · base-assist damper | **closed** — each on its own control or arithmetic. |
| **grind #1** | **unmeasurable on the current corpus** — no creep exposure since V107. |
🛑 **Two gating measurements, neither needing a build:** (1) **one stock-configuration drive** takes
the angle-gating result from p = 0.100 to p = 0.018; (2) **a creep-inclusive drive OR operator
timestamps** makes grind #1 measurable at all.

## 🛑🛑 THE ADDED LKAS "MASS" **IS** THE DAMPER THAT WORKS — a build proposal stopped one step short
I had assembled: the engaged friction row is the only engaged asymmetry · it scales `gp-0x6b26` ·
`gp-0x6c2c` is **acceleration**, pinned in assembly ⇒ `−K·α` is **apparent inertia** ⇒ *"we add 3×
engaged-only steering mass, exactly what the operator forbade, and it explains his low-acceleration
complaint."* **Every link individually correct.**
🛑 **V94 flew that argument verbatim** (*"it is apparent inertia, nothing is dissipated, lowering is
strictly safe"*), cut the cell **6×**, and on route `7d` **the operator ABORTED**:
> *"Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car,
> and I decided it was not safe to drive."*
Measured after: motor acceleration **3-7× up above 9 Hz**; column-torque↔wheel-rate coherence at
18-31 Hz **the highest of any drive in the corpus**. Then, two drives, ω-partialled, shuffled control:
```
   delivered phase vs WHEEL rate, 6-9 Hz:  +137 deg / +139 deg   =>  +518 / +565 counts POSITIVE Re(Z)
   => a REAL 6-9 Hz DAMPER.  V94 removed 6/6ths of it.  First measured d(symptom)/dK: sign UP.
```
✅ **Reconciliation, both notes stand:** [[accord-gp6b26-is-inertia-not-damping]] is right
**structurally** (built from an acceleration), but **structure is not delivered effect in a loop with
filters** — delivered, it is +137° against wheel rate, i.e. dissipative.
🛑🛑 **⇒ THE OPERATOR'S TWO GOALS ARE IN MEASURED OPPOSITION ON THIS LEVER.** The apparent mass he
feels under LKAS **is** the damper holding the oscillation down; V107's 3.0× (**90 % of the int16
ceiling 3.3335**) is a large part of why V112 is his best build. **Cutting it to buy acceleration is
REFUTED ON THE ROAD**, and "more damper" has only **1.11× headroom at Y[0]** before overflow.
✅ **Any acceleration gain must come from a DIFFERENT lever.** ⊕ This is the value of the standing
rule *check the build lineage before proposing a cal lever* — it stopped a rebuild of the worst drive
in the record.

## ✅ THE FRICTION-ROW FLAG IS **RETRACTED** — no defect on the car; the kit had already shown why
I flagged that V107..V121's engaged friction row at **3.00×** sits past a stated *"int32 wraparound at
1.6005×"*. **Verified. Wrong on three counts:**
1. 🛑 **Wrong clamp cited.** `FUN_00034350` reads FactorB/C/D/E + ceiling and clamps *their*
   product to `|gp-0x6bd0| <= 1024`; **it never reads `0xCBE74`.** The friction row's consumer is
   **`FUN_00036c12`** → `gp-0x6b26`, clamped at ±`0xC407E` = **±511**.
2. 🛑 **I scaled a MAX, not a distribution** (319.1 × 3.0 = 957). `build_v107_tva.py` has a
   section **"THE TERM IS NOT SATURATING"** with reconstructed duty on r a6's engaged distribution,
   **held-out validated on r78**:
```
      engaged all   n=123802   p50 15.1   p99 268.5   duty>=511 = 0.00121
```
   ⇒ **p99 268.5 vs a 511 clamp, duty 0.12 % — NOT a relay.**
3. ✅ **The governing bound is the int16 floor**: `Y` is signed int16, `Y[0]` stock -9830 ⇒
   **k_max = 32768/9830 = 3.3335**, and 3.00× = **90.00 % of it, chosen deliberately** (×4/×5/×6 are
   overflow). The "90.0 %" column is **percent of the int16 floor**, not clamp duty.
⇒ The **1.6005×** figure in [[accord-six-levers-closed-on-arithmetic]] does **not** describe this
row's headroom; those two records need reconciling, but **V107..V121 are inside the real bound.**
✅ **The V107 step is deliberate design**: a reshape at constant `Y[0]` (so *"creep-speed clamp duty
and the relay index are UNCHANGED BY CONSTRUCTION"*), raising only high-speed knots because Honda's
taper made the dose **4.2× weaker at highway**; V108 then reverted `Y[1]` (`GP6B26.Y1REVERT`).
🛑 **My "the shape change was never analysed" claim is withdrawn too** — V107's builder analyses
exactly that, with a four-speed delivered-coefficient table and an int16-headroom column.
⇒ **NET: the only engaged-vs-manual asymmetry is still this row (that stands), but it is not
saturating, not wrapping, and not a hidden relay. No defect in the flight build.**

## ⭐⭐ THE **ONLY** ENGAGED ASYMMETRY LEFT IS THE FRICTION ROW — and 3.0× sits past a stated wrap point
Dereferenced all fourteen mode-indexed families at `arr + mode*4`. On V112 and V121 exactly **one**
differs between mode 24 (manual) and mode 26 (engaged): **`0xCBE74` friction**. FactorB/C/D/E,
ceiling, the four r24 `gain_B` arrays, boost curve/amp/ceiling — **all byte-stock and symmetric**.
✅ **The V74-V81 engaged-only FactorC/E damper is GONE** (V90+ byte-stock, `Y[0]=0`, Honda's ramp) ⇒
[[accord-v80-damper-relay-and-grind1-inert]]'s *"restore the RAMP"* **is already satisfied — no build
needed.**
```
   build         m24 (MANUAL)           m26 (ENGAGED)              ratio
   STOCK, V90    [-9830,-5734,-1966]    [-9830,-5734,-1966]         1.00
   V91..V104     same                   [-14745,-8601,-2949]        1.50  uniform
   V107..V121    same                   [-29490,-17202,-16000]      3.00  NOT uniform
                                         Y[0] 3.00x Y[1] 3.00x Y[2] 8.14x
```
🛑 Stock's |Y| **decays 5.0×** across the axis; ours decays only **1.84×** — we tripled it **and
flattened it**. **All prior analysis of this cell was of UNIFORM scaling**; a shape change alters the
slope d|f|/dx, a different quantity, and nothing in the record addresses it.
🛑 **FLAG ON THE BUILD ON THE CAR:** [[accord-six-levers-closed-on-arithmetic]] closed this lever
partly on **"int32 wraparound at 1.6005×"** — **V107..V121 carry 3.00×.** ⚠ I have **not verified**
that claim, and two things argue against catastrophe: -29490 fits `i16`, and the evaluator's output is
**hard-clamped** to `|gp-0x6bd0| <= 1024` ([[accord-damper-evaluator-fun34350-ceiling-clamp]]) so an
oversized input should **saturate, not wrap**; V107-V112 flew fault-free. 🛑 **"Should saturate" is a
belief, not a check.** ⇒ **OPEN, highest-value verification available: does the 3.0× row overflow
anywhere between the LERP and the clamp? Pure arithmetic on a decompile — no drive, no flash.**
⚠ **NOT a build proposal**: the ×1.5 dose **measured INERT** over two flights (a candidate **T10**,
not falsified — V94's 6× cut made the operator abort, so the cell reaches the car), and delivered
damping was judged **5-69× below the resolvability floor**.

## 🛑 V121's HARMONIC RATIONALE IS **WEAKENED** — the one quantitative check does not support it
I tried to make V121 prospective, as the saturation-duty model was for V112. The relay is memoryless,
so I fed the measured V112 rate through `clamp(rate·4.7121·12/knee, ±1)` at each knee:
```
   knee     600     1800     2400     3000     4000     8000
   ratio   0.951   1.365    1.248    1.493    1.832    1.278
   knee 3000 predicted factor 1.094x  CI [0.755, 1.335]   <- slightly WORSE, not better
```
🛑 Non-monotone, and it **contradicts the cross-build trend** the mechanism rests on (wire: 600 →
1.412, 1800 → 1.213; simulation puts 600 BELOW 1800).
⚠ **The simulation is INVALID as a prediction** — the measured rate **already contains the effect of
the relay that was running**, and **a memoryless nonlinearity in a CLOSED LOOP cannot be simulated by
post-processing the loop's own output.** ⇒ it cannot confirm the mechanism. 🛑 **But it cannot be
waved away**: reproducing the trend would have been weak support, and it **fails to**. Net,
**confidence in the harmonic mechanism goes DOWN.**
⇒ **V121 is NOT withdrawn, but its case now rests on grounds independent of harmonics:** gain held
EXACTLY at V112's (bit-identical ≤ 31.8 deg/s ⇒ near-zero regression risk); **more assist above
31.8 deg/s**, serving the operator's constraint directly; `knee` has the best on-car track record of
any lever here (600→1800 coincided with the best-ever build, though confounded); cal-only, 4 bytes,
40/40.
⚠ **V116 is the conservative version of the same move** (K1 0.797 of |model| vs V121's 0.996, just
under the sign-inversion ceiling). **If the weakened mechanism argues for a smaller step, fly V116.**
🛑 **Plainly: V121 is a well-constructed build whose effect on the oscillation is UNKNOWN.**

## 🛑🛑 GRIND #1 IS **UNMEASURABLE** ON THE RECENT ROUTES — there is no creep exposure
I validated a grind-#1 pipeline against a known effect — V101/V102/V103 accidentally dropped Lever B,
and the pipeline recovered it at **OFF/ON = 2.32× [1.62, 2.94]** against the on-car **0.40
[0.27,0.58]** (≈2.5×). **The control PASSED.** Then the hunt gave four predictors at p < 0.10 and an
ordering the operator flatly contradicts:
```
   r1e V107 2.92 (best on my stat) · r21 V111 5.10 · r22 V112 7.33 · r23 V112 7.93 (worst)
   operator: V112 is "the best firmware ever... Grind #1 is now rare."
```
✅ **Cause found.** Grind #1 was characterised at **creep** — operator on V62: *"Original grinding at
**2-5 mph** is gone!"* Engaged windows in that band:
```
   r77 (V90) 39 · r85 11 · r9e 11 · ra5 11 · r1e 11 ·  r21 (V111) 0 · r22 (V112) 0 · r23 (V112) 0
```
⇒ **the all-speed statistic measured road-speed 18-22 Hz on V111/V112, NOT creep grind #1.** The four
"hits" are one collinear old-vs-new contrast — **do not act on them.**
🛑 **This weakens [[accord-knee-has-no-measured-dose-response-on-grind1]]**: it pooled all speeds
too, so that null is about **road-speed 18-22 Hz, not creep grind #1**. Its conclusion (V121 does not
fix grind #1) stands, but because **grind #1 was never measured**, not because a dose-response failed.
✅ **WHAT UNBLOCKS IT — no firmware change:** (1) **a drive with real engaged 2-5 mph creep**, which no
post-V107 route has; or (2) **operator timestamps** — he said *"I no longer have an understanding of
the kinds of scenarios that elicit grind #1"*, so **a mark at the moment it happens** converts an
unmeasurable symptom into a locatable one, exactly as the route-23 timestamp did for the oscillation.
⇒ **SECOND GATING MEASUREMENT ITEM**, alongside `docs/scoring/DRIVE-CARD-manual-at-speed.md`.

## ✅ LEVER B **IS** ON THE CAR — an alarm of mine, corrected; grind #1 needs something NEW
Byte scan, 25 built images + stock:
```
   build           0x3AA96      0xC6446     LEVER B?  |  0x3AB76 0x3AC20  LEVER A?
   STOCK           C5 stock     512 stock     no      |    AA      AA       no
   V90..V100       FB LKAS gate 5244 ARMED    YES     |    AA      AA       no
   V101,V102,V103  C5 stock     512 stock     NO   <-- a real gap, closed at V104
   V104..V121      FB LKAS gate 5244 ARMED    YES     |    AA      AA       no
   LEVER B: 22 of 25        LEVER A: 0 of 25
```
✅ **V112 (ON THE CAR) and V121 both carry Lever B** — grind #1 **0.40 [0.27, 0.58]**, *best in the
kit*, **and** creep grind #2 → **0 bursts**, mode-proof.
🛑 I raised an alarm from [[accord-v81-carries-neither-grind1-fix]] that the fix had been silently
lost. **Wrong — that memory is specific to V81.** Lever B was restored at V88 and is continuous since.
✅ **Lever A is absent, and correctly so**: its r24 half raised 40-49 Hz **×11.7 and CAUSED grind #2**,
while Lever B is equal-or-better on grind #1 *and* fixes grind #2. **Do not restore Lever A whole.**
⚠ Its **r26 half alone** (`0x3AB76` `AA`→`A9`, ONE byte) has never flown in isolation and did not
cause grind #2 — but [[accord-r26-is-structurally-inert]] leans inert (leg 2 BELIEF) ⇒ **likely a
no-op; NOT proposed on this evidence.**
🛑 ⇒ **THE REMAINING GRIND #1 IS NOT A LOST FIX.** The best measured fix is deployed and the symptom
persists ⇒ **it needs a NEW lever.** ⊕ Not the relay knee
([[accord-knee-has-no-measured-dose-response-on-grind1]]), ⊕ not the base-assist damper
([[accord-v80-damper-relay-and-grind1-inert]], inert across k = 0.58 → 4.16).

## 🛑 THE KNEE HAS **NO MEASURED** DOSE-RESPONSE ON GRIND #1 — an upgrade withdrawn before it was made
I was about to strengthen V121's claim on grind #1 using the operator's own dose-response (constant
→ *"rare… a few moments"* exactly when knee went 600→1800). **Tested it first; it does not
reproduce.** 17 routes, band power as a SHARE of each window's own 1-40 Hz power:
```
   knee   n_routes   18-22 Hz    26-31 Hz    6-9 Hz
    300       8        0.0718      0.0658     0.0427
    600       7        0.0930      0.0616     0.0659
   1800       2        0.0924      0.0532     0.0663
     18-22  rho +0.356 p 0.161   |   26-31  rho -0.158 p 0.546
```
🛑 **18-22 Hz goes the WRONG WAY**; 26-31 Hz is flat. ⇒ **V121's claim on grind #1 stays as
written — it does NOT address it.**
⚠ Not a refutation of the operator's report, for two reasons: **n = 2 routes at knee 1800**; and
🛑 **band SHARE is not severity** — it is normalised by broadband power, so a change that lowers
broadband more than the band **raises the share while the absolute level falls**. The 6-9 Hz
reference row shows the hazard: it *rises* with knee on share (rho +0.477), opposite to the harmonic
and on-road results. **The right statistic is absolute band level with exposure controlled, and this
corpus cannot deliver it at n=2. OPEN.**
⇒ V121 stands on the **harmonic** result alone (itself BELIEF). The operator's grind-#1
dose-response is also **confounded** — V112 moved `knee` **and** `K1` together — but remains the best
on-car signal the kit has for grind #1.

## 🛑 A FABRICATED "MEASURED" VALUE IN V121'S PROVENANCE — caught, removed, asserted against
Deriving `build_v121_tva.py` I wrote `MEASURED_DUTY = {..., 2400: 0.0484, 3000: 0.0370, 3600: 0.0000}`.
**`0.0370` was invented** by eye from the neighbouring rungs, inside a dict printed as
*"MEASURED relay saturation duty"* and asserted against. **The payload never depended on it — the
image SHA `ce565da7…` is unchanged** — but the provenance is what a future session trusts.
🛑 **Recomputing the ladder properly ALSO failed.** On the published gate (route 21, 5-10 mph,
engaged, hands-off, `|cmd| >= 2048`) my reconstruction gave **n = 572 vs the published 289**, and the
duties missed badly (`cs_rate` 0.9178/0.4493/0.1171/0.0087 vs 0.7439/0.4810/0.2353/0.0484).
⇒ **The ladder's exact gate is NOT recoverable from the r21 cache alone. OPEN.** Anyone extending it
must first reproduce the five published rungs; if they cannot, they must not add a sixth.
✅ **Fixed structurally**, not by resolving to be careful — the builder now asserts
`KNEE_NEW not in MEASURED_DUTY` and `2400 < KNEE_NEW < 3600`, so it **fails** if anyone adds an
unmeasured rung, and states its position as **bracketed by 0.0484 and 0.0000** rather than claiming a
value. **40/40 assertions; image unchanged.**
⇒ [[feedback-never-extend-a-measured-ladder-by-eye]]

## ✅ **V121 BUILT — THE MAXIMAL GAIN-MATCHED KNEE.** `0xC40BC` 1800→3000, `0xC40D2` 612→1020
```
image  ce565da74ad93f77c81a3e2572758d5c2df505f6d32889b65c5536904ea7596c
.rwd   8c154edb69ae4649ba55ac4760ae55aec56bd5be2b336e0d8f1e4a46b33512c9
38/38 assertions · 50/50 CRC blocks · 4 payload bytes · cal-only, NO cave · alpha2 HELD at 14
```
**A HARD SAFETY CEILING SETS THE DOSE.** `friction = |model|·(K1/1024)·clamp(·1)`, so `K1/1024` is the
friction's maximum as a **fraction of |model|**; at `K1 >= 1024` friction can exceed `|model|` and the
**residual INVERTS SIGN**. No build in the kit's history has run `K1 >= 1024`.
```
   build   knee    K1    gain        saturates   K1/1024   frames saturated
   stock    600   204   0.0039844    10.6 deg/s   0.199        19.165 %
   V112     1800   612   0.0039844    31.8         0.598         6.748 %   <- ON THE CAR
   V116     2400   816   0.0039844    42.4         0.797         4.713 %   <- still clipped at 47.06
   V121     3000  1020   0.0039844    53.1         0.996         3.697 %   <- CLEARS it
   (knee 4000 needs K1 1360 = 1.328 of |model| ⇒ REFUSED, residual inverts)
```
🛑 **V116 is a HALF-STEP**: oscillating windows have median p95 |rate| = **47.06 deg/s**, so
V116's relay is **still a signum exactly where the symptom lives.** V121 is the first gain-matched
step that clears it while staying same-signed.
✅ **Feel: bit-identical to V112 at and below 31.8 deg/s** (ratio 1.000 at 10 and 30 deg/s), then
**1.571× the friction at 50 and 1.667× at 100+** — and **more modelled friction = MORE assist**
([[accord-friction-polarity-more-assist]]) ⇒ it adds **no** drag where the LKAS command lives and
**increases** authority at high steering rate. That is the operator's constraint moved the right way.
⊕ Second, independent rationale for the knee: the 7-9 Hz mode radiates **real harmonics**
([[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]]) ⇒ a hard nonlinearity in its
excitation path; **knee is the relay's SHAPE** and the harmonic ratio is monotone in it
([[accord-knee-is-the-relay-shape-variable-k1-is-only-gain]]). V116's header said the knee *"does
NOT fix the peak-turn oscillation"* — written before that result, and **now too strong.**
🛑 **The mechanism is BELIEF, not EVIDENCE** (ρ −0.291, p 0.257). V121 is the **best-motivated
flight, not a guaranteed fix.** ⚠ `FUN_0003b8f6` is not LKAS-gated ⇒ **manual feel changes above
31.8 deg/s**, the same trade V112 made. ⚠ It does **not** address grind #1 — a separate mechanism.
✅ **FALSIFIER:** V121 should push the harmonic ratio below V112's **1.213** and be no worse on
assist. If the ratio does not move, the relay is not the excitation path.
⇒ **RECOMMENDED FLIGHT ORDER: V121 → (V116 only if V121's dose proves too large).** V120 is
withdrawn — it cuts assist and, being pure gain, cannot touch the harmonics.
⚠ Builder bug caught and fixed: the image first emitted under a `_v116_` prefix. Corrected to
`_v121_`; V116's own image was never overwritten. Builder:
`analysis-2020accord/builds/v108_plus/build_v121_tva.py`.

## ⭐⭐ `KNEE` IS THE RELAY'S SHAPE, `K1` IS ONLY GAIN ⇒ **THE RECOMMENDATION CHANGES TO V116**
🛑 My first dose-response test was **mis-constructed**: it used `fric_gain = (K1/1024)(12/knee)`,
but `K1` multiplies **after** the relay (pure gain) while `knee` sets where the clamp bites (the
**shape**) — and **a signum's harmonic ratio is scale-invariant**, so `K1` cannot move it by
construction. Re-tested on `knee` alone:
```
   knee   n_routes   median harmonic ratio     relay character
    300       8           1.743                hardest signum
    600       7           1.412                stock
   1800       2           1.213                softest        <- V112, the best build on-road
   Spearman = -0.291  p = 0.257   knee300/knee1800 = 1.437 CI [0.925, 2.258]
```
✅ Monotone across all three levels, direction as predicted. 🛑 **NOT significant** — CIs include
1.0. **[BELIEF, suggestive; a monotone ordering of 3 groups is ~1/6 by chance.]**
```
              knee    K1     small-signal gain   saturates at   assist change
   V112 (car) 1800   612        0.0039844        knee/12 = 150       --
   V116       2400   816        0.0039844        knee/12 = 200      NONE
   V120       1800   306        0.0019922        knee/12 = 150      LESS
```
✅ **V116 raises `knee` and `K1` together by 1.333× ⇒ small-signal gain EXACTLY V112's, relay
saturates 1.333× later** = *make the relay more linear without changing the assist.*
🛑 **V120 does the opposite of the operator's ask**: halving `K1` halves modelled friction, and
[[accord-friction-polarity-more-assist]] gives **more friction = MORE assist** ⇒ V120 **reduces
assist**; and being pure gain it cannot touch the harmonics on this mechanism.
⇒ **V116 SUPERSEDES V120 as the recommended flight** — already built, 38/38, cal-only.
⊕ Clean falsifier: V116 should drop the harmonic ratio below V112's 1.213 **and** be no worse on
assist. memory: [[accord-knee-is-the-relay-shape-variable-k1-is-only-gain]]

## ⭐⭐ THE 7-9 Hz MODE IS NONLINEARLY EXCITED — and that RESOLVES BOTH open contradictions
17 routes, 3,986 windows, NW=512. Peak prominence at `2f0`/`3f0` vs off-multiple controls, then
against the control that matters — **non-oscillating windows**:
```
   OSCILLATING      1.308        NON-OSCILLATING  1.061
   OSC / NON-OSC =  1.233    ROUTE-level bootstrap 95 % CI [1.060, 1.503]
   f0 = 7.81 Hz  ->  2f0 = 15.62 Hz   3f0 = 23.44 Hz
```
✅ **Harmonics are REAL** — CI excludes 1.0 with the DRIVE as the unit ⇒ the excitation path
contains a hard nonlinearity.
✅ **CONTRADICTION 1 RESOLVED — the symptoms stay TWO.** 2f0 and 3f0 land at 15.62 / 23.44 Hz;
**neither is in 18-22 or 26-31.** The 0.2-pp rate co-location is **shared exposure, not shared
mechanism** ⇒ [[accord-two-symptoms-two-mechanisms-rez-spectrum]] **wins**.
🛑 **⇒ Fixing the 7-9 Hz oscillation will NOT fix grind #1. Budget for two fixes.**
✅ **CONTRADICTION 2 RESOLVED — resonance AND nonlinearity are both true.**
[[accord-ratchet-is-a-lightly-damped-resonance]] excluded a limit cycle on a ring-down; harmonics
normally imply one. No conflict: **a linear resonance driven THROUGH a nonlinear element** gives a
clean ring-down when the drive stops *and* harmonics while driven. Both records stand as written.
⭐ **Points at the Coulomb relay** — `fVar13 = clamp(POL·gp-0x6abc·12/knee, ±1)` is a **signum**, the
textbook harmonic generator, and [[accord-engagement-amplifies-6-9hz]] already measured engagement
multiplying this band **2.8×** through it.
✅ **⇒ V120 (`0xC40D2` 612→306) now has a measured mechanism, not just reasoning.**
🛑 [BELIEF, one converging line] — nothing shows the relay is *the* path rather than *a*
nonlinearity, and [[accord-cbe74-dose-measured-inert-wrong-mode-record]] warns a relay dose can
measure inert.

## ⭐⭐ THE 18-22 Hz GRIND IS RATE-COLOCATED WITH THE OSCILLATION — a constraint on the whole search
🛑 **Correction to my own framing first.** I reported *"rate AUC 0.630 ⇒ weak, parked."* The number
is right, the framing was incomplete: 0.630 was against **hard curves** (n=106). Against **ordinary
driving** (n=4,920) rate gives **AUC 0.978** (median 47.06 vs 4.33 deg/s, **10.86×**), beating angle's
0.713. ⇒ rate separates the oscillation from ordinary driving almost perfectly; what it cannot do is
separate it from a **hard curve** — and the operator's words are *"a fixed oscillation during the peak
of a hard curve."* **The symptom IS that regime**, so the tension is structural, not a measurement
failure.
**Band power above a rate knot T, 8,200 engaged windows / 17 routes:**
```
   band                     T=20     T=40     T=60    T=100    T=140
   6-9 Hz   (oscillation)   82.7 %   59.3 %   26.2 %   15.8 %   12.2 %
   18-22 Hz (grind)         94.1 %   59.5 %   23.9 %   14.6 %   11.0 %
   26-31 Hz (grind)         92.7 %   64.4 %    2.6 %    1.1 %    0.7 %
   selectivity vs 18-22:  1.10x @T=60      vs 26-31:  10.15x @T=60
```
Archive: **D PUMPS 2-12 Hz, DAMPS 16-35 Hz** ⇒ a flat `Kd` cut needs selectivity **>2.82×** (18-22)
and **>4.36×** (26-31) to beat its own trade.
✅ **26-31 Hz cost SOLVED by scheduling** (10-17× ≫ 4.36×). 🛑 **18-22 Hz cost NOT** (1.10× vs
2.82× needed) — it sits in the **same rate regime** as the oscillation, 59.5 % vs 59.3 %.
⇒ **`Kd` stays REFUSED**, now ~2.6× against instead of 3-4×. **Not a build.**
⇒ ⭐ **GENERAL CONSTRAINT: no rate-scheduled lever can touch the 7-9 Hz oscillation without equally
touching the 18-22 Hz grind** — helping one and hurting the other in the same windows.
⊕ Raises, but does **not** establish, that the two are one mechanism; co-location is necessary, not
sufficient, and [[accord-two-symptoms-two-mechanisms-rez-spectrum]] separates them on `Re(Z)`.
**Those two records are NOT yet reconciled.**

## 🛑 …AND ITS CRUX TEST FAILED — the rate axis does NOT separate the symptom
Pre-registered above: *if `gp-0x6ac0` during the 7-9 Hz event overlaps a normal hard curve, the lever
fails.* **It ran. They overlap.** Proxy `|cs_rate|` p95, 8,200 engaged windows, 17 routes:
```
   OSCILLATING (6-9 Hz top 5 %)     n = 410   median 47.06 deg/s
   NORMAL HARD CURVE (ang>=20)      n = 106   median 24.49 deg/s
   knot T:   20 -> 83.4 % osc / 61.3 % normal    40 -> 60.2 % / 36.8 %
             60 -> 22.4 % / 27.4 %  (INVERTS)   200 -> 5.6 % / 2.8 %
   AUC = 0.630  (0.5 = none)   p = 1.9e-05
```
🛑 Every useful threshold also catches **a third to a half of normal hard curves** ⇒ **a
rate-scheduled `Kd` knot cannot spare normal steering**, the exact cost the operator forbade.
⚠ **Weak, not zero**: a LERP is smooth, medians separate **1.9×** highly significantly ⇒ a gradual
rolloff gives ~1.9× more reduction during oscillation. Modest, not clean.
⚠ The proxy may **understate** separation — the real axis is the **motor** rate and the motor sees
the oscillation more strongly than the wheel. **Resolving that needs a cave probe = the only
bricking class**, so it is not cheap.
⇒ **PARKED, not struck.** The **structure** (Honda rate-schedules the PID; `Kd` flat and virgin,
byte-identical stock vs V112) **stands as EVIDENCE**; the **discriminability** claim does not.
**Do not build it on the structure alone.**

## ⭐⭐ A FREQUENCY-SELECTIVE LEVER **DOES** EXIST — Honda rate-schedules the PID, and `Kd` is FLAT
Decompiled `FUN_0003a382`, then byte-verified: all three PID gains are four-knot LERPs on the **same
axis**, `gp-0x6ac0` (resolver/FOC electrical rate [BELIEF, kit record]):
```
  Kp 0xC6B26  X = [0, 300, 2000, 4000]   Y = [256, 256, 225, 153]   <-- NOT FLAT: Honda rolls off 40 %
  Ki 0xC6B12  X = [0, 400, 1500, 3000]   Y = [ 98,  98,  98,  98]       flat
  Kd 0xC6AE6  X = [50, 400, 1500, 3000]  Y = [2048,2048,2048,2048]      flat
  lane gate: disabled when gp-0x6ac0 >= 0x32C9 = 13001
```
✅ All three Y rows **byte-identical stock vs V112** — virgin across the entire build history.
✅ **Honda's own Kp row proves the machinery is live, wired and calibrated** — nothing to arm.
🛑 ⇒ **[[accord-factord-is-the-angle-error-lever]]'s "this firmware has NO frequency-selective
lever" is TOO STRONG and should be read as scoped to FactorD.**
⊕ `STATE-ARCHIVE-2026-08-11`: **D PUMPS ONLY 2-12 Hz and DAMPS 16-35 Hz** ⇒ Kd is an anti-damping
contributor **at exactly the symptom band**. A **rate-scheduled** rolloff — Kd unchanged at low rate,
reduced at the top knots, shaped the way Honda shapes Kp — costs no steering velocity or acceleration
where the LKAS command lives. That is the operator's constraint, satisfied by construction.
🛑 **NOT YET A BUILD. The crux is knot placement**, and it is unmeasured: nothing shows what
`gp-0x6ac0` reads during the 7-9 Hz event vs during a normal hard curve. **If those overlap, the
lever cannot separate them and the idea fails.** ✅ Measurable from existing telemetry — do that next.
⚠ Also: it changes **manual** steering (`gp-0x67fa & 0xc30`, not an LKAS flag); GATE 2 applies; and
the kit's earlier **refusal** of Kp/Ki/Kd was about *flat* scaling, which does not transfer.
✅ Cal-only, one Y row, no cave ⇒ outside the only bricking class.
Tool: `analysis-2020accord/verify/read_pid_rate_schedule.py` ·
memory: [[accord-pid-gains-are-rate-scheduled-and-kd-is-flat]]

## ✅ THE DELETION-SET HYPOTHESIS IS NOW PROVEN — and `0xC64DE` is struck
**16-route natural experiment**, 15 builds, using the route-offset-immune within-drive statistic.
Outcome = log(large-angle 6-9 Hz p90) with log(small-angle p90) regressed out (r = 0.645).
```
   predictor      levels   rho      p        predictor      levels   rho      p
   knee 0xC40BC      3    -0.158  0.546      biq  0xC649B      2    -0.072  0.783
   K1   0xC40D2      3    +0.280  0.276      fric_gain        3    +0.297  0.247
   a2   0xC40DC      2    +0.094  0.718      clamp 0xC407E    1   CONSTANT - untestable
   gain 0xC6CD0      4    -0.206  0.429      kd    0xC6AE6    1   CONSTANT - untestable
```
🛑 **NOTHING that has ever varied explains the excess** (|rho| < 0.30, p > 0.24) across knee
300-1800, K1 102-612, gain 3564-65535, biquad off/on. ⇒ **the cause is the shared SET of deleted
Honda limiters**, exactly as [[accord-the-mod-works-by-deleting-hondas-limiters]] predicted — that
note's "a reframe, not a proof" is now **proven**.
✅ The invariant set is byte-exact: `0x454FE` (governor call deleted) · `0xC61C0` (1600/896/1280 →
65535×3) · `0xC64B4` · `0xC62EA` (320→0) · `0xC674F/51/5B/5D` + the `0xC659A` f32 table (corridor
×5) · `0xC64DE`. Tool: `analysis-2020accord/verify/invariant_mod_edits_vs_stock.py`.
🛑 **`0xC64DE` IS A DEAD LEVER — do not build it.** It looked like the one non-authority member of
the set, but it is a **square-wave injector half-period whose amplitude LERP `0xC6736` is (0,0,0,0)
in stock and in every build** ⇒ structurally inert.
⇒ Every remaining member is an **authority limit**, so restoring any of them spends exactly what the
operator forbade. **The next lever must be FREQUENCY-SELECTIVE.** The dormant biquad `0x35A28`-
`0x35A50` is the only real candidate (editable 2nd-order section, armed since V103) but is tuned to
**42.3 Hz** — hence its rho = -0.072 above. ⚠ All-pole, **DC gain 8.39** ⇒ as-is it AMPLIFIES; in a
loop ⇒ GATE 2 applies. **Open question, NOT a build proposal.**

## ✅ ANGLE GATING — CONFOUND REMOVED, **9 of 9**; and ONE stock route caps p at **0.100**
Within-drive design (each route its own control ⇒ immune to route offset). Raw ratio gave STOCK
**1.46x** vs 16 mods median **2.99x**, but 3 mods fell below stock — **because the ratio's denominator
varies 10x across builds** and those 3 all had small-angle p90 > 6.
**Matched on small-angle p90** (stock ranks 3rd of 10 ⇒ exposure matched):
```
   route build   small-ang p90   LARGE-ang p90   ratio
   r97   STOCK       1.064          1.551       1.46x   <-- BELOW ALL NINE
   r22   V112        1.240          2.909       2.35x
   r23   V112        1.060          8.320       7.85x     (same firmware as r22)
   ... 7 more, large-angle 3.137 - 7.353
```
✅ **Stock's large-angle p90 is below all 9 matched mods.** The same-firmware V112 pair both sit
above stock by ≥ **1.88x**, so drive-to-drive spread does not explain it.
🛑 **Exact one-sided permutation p = 1/10 = 0.100. With ONE stock route the FLOOR is
1/(n_mod+1) — it cannot reach 0.05. The limit is the DESIGN, not the analysis.**
✅ **TWO stock routes below all nine ⇒ p = 0.0182.**
⇒ **[EVIDENCE for direction and size; NOT significant at 0.05 and cannot be, on n=1 stock drive.]**
✅ **THE GATING ITEM IS `docs/scoring/DRIVE-CARD-manual-at-speed.md` — ONE more stock-configuration
drive takes the strongest surviving finding from p=0.100 to p=0.018. No build, no flash.**
Tool: `rlog-tools/studies/peakturn/matched_denominator_angle_test.py`

## 🛑🛑 ONE ROUTE PER BUILD CANNOT RESOLVE A BAND RATIO — the K1 refutation is WITHDRAWN
`r22` and `r23` are **both V112**: identical firmware, different drives.
```
   |ang|     SAME-FIRMWARE r23/r22    95% CI          cross-build V112/V111
    0-  5           1.07x           [0.81, 1.25]            1.27x
    5- 20           0.77x           [0.55, 0.97]            0.90x
   20- 60           2.74x           [0.79, 8.87]            0.75x
```
🛑 **At 20–60° the SAME firmware varies 2.74× between drives.** A predicted 2–3× effect is below
that floor, and every cross-build ratio sits inside the same-firmware spread. My CIs were
bootstrapped over **windows**, ignoring route-level variance.
⇒ **The K1 mechanism is UNTESTED, not refuted.** The "0–5° residue" is withdrawn too.
✅ **RULE**: resample **ROUTES**, or quote the same-firmware spread beside every cross-build ratio;
a cross-build band ratio needs **≥ 2 routes per arm**, and at large angle an effect **> ~2.7×**.
⚠ [[accord-the-oscillation-excess-is-ANGLE-GATED]] **survives** — its tail effects (4.4× overall,
7.9× at 20–60°) clear the floor and it is exposure-controlled — **but it rests on ONE stock route**,
and its smaller per-band ratios (1.06–1.74×) are **not** resolved.
⇒ **V120 remains the recommended flight on REASONING, not on demonstrated mechanism.**

## 🛑🛑 THE K1 MECHANISM IS **REFUTED** — V120/V113 ARE NOT MECHANISM-BACKED FIXES
Tested on data already in hand. **V111 and V112 share a small-signal gain**, so their friction term is
identical at low rate and V112's is **1.9× at 20 °/s, 3.0× above 31.8 °/s**. If that term drove the
anti-damping, V112 must be 2–3× worse at large angle. **It is not:**
```
   |ang|     n111  n112   p90 ratio V112/V111    95% CI        verdict
    0-  5     488   424        1.27x           [1.05, 1.49]   excludes 2x
    5- 20      82   167        0.90x           [0.73, 1.22]   excludes 2x
   20- 60      25    48        0.75x           [0.48, 1.64]   excludes 2x -- V112 BETTER
   60-400      38    19        1.53x           [0.96, 4.15]   underpowered
```
⊕ At **0–5° the term is IDENTICAL and V112 is still 1.27× worse [1.05, 1.49]** — the friction term
cannot explain that at all.
✅ **STILL SOLID**: the excess IS angle-gated vs stock (exposure-controlled, confound inverted);
`|model|` rises 7–9× with angle; K1 IS ×6 on stock; the term IS in phase with rate.
🛑 **REFUTED**: the causal link from that term to the oscillation.
⇒ **V120 and V113 remain valid builds but are NOT fixes with a known mechanism.** Every earlier claim
that V113/V120 is "the targeted fix" or "evidence-backed end to end" is **WITHDRAWN**.
⚠ **Open residue**: something other than the friction term differs between V111 and V112 and shows up
even at 0–5° where their friction is identical.

## ⭐⭐⭐ V120 BUILT — **K1 612 → 306. HONDA-EQUIVALENT FEEL, HALF THE ANTI-DAMPING.**
```
builder  analysis-2020accord/builds/v108_plus/build_v120_tva.py   40/40   BASE = V112
image    a588f936e4cdfe58ece41ff4943bff532444daabc4b99a53f00c1d718950a1bb
.rwd     9d6469277a6bba995cd9d2137332d791460cc2c15f845fe00c228f13c80a67e1
0xC40D2  612 -> 306   2 payload bytes.  knee 1800, alpha2 14, cave, biquad ALL HELD.
```
🛑 **DOSE CORRECTION.** V112 raised knee ×3 AND K1 ×3, so **V111 and V112 deliver the SAME low-rate
compensation** — one number for "what he is used to". **V113's K1 = 204 is 0.333× of it, i.e. BELOW
Honda's own 0.500×** ⇒ heavier than STOCK at low rate. Not intended, not computed at the time.
```
   build      knee    K1    comp @ 3 deg/s    vs V112
   stock       600   102       0.02816         0.500   <- Honda's level
   V112       1800   612       0.05632         1.000   <- on the car
   V120       1800   306       0.02816         0.500   <- == STOCK
   V113       1800   204       0.01877         0.333   <- below stock
```
⭐ **V120 buys**: anti-damping **0.500× at every frequency** (no added inertia, no added phase);
low-rate feel **exactly Honda's**; relay **corner untouched at 31.8 °/s** so V112's 1.37–1.62×
authority win is kept; and it **self-targets** — linear in `|model|`, which rises **7–9×** with angle.
⇒ **V120 is the recommended flight; V113 is the fallback second step if 0.500× is not enough.**

## 🛑🛑⭐ K1 IS THE ANGLE-GATED ANTI-DAMPING — **V113 IS THE FIX, AND IT IS ALREADY BUILT**
Every link measured, 2026-08-28:
1. **The excess is ANGLE-GATED** — |ang| < 20° we ARE stock (1.06–1.08×); 20–60° p90 **1.74×**, max
   **16.568 vs stock's 2.111**; 60–400° p90 **3.16×**. ✅ Exposure-controlled and the confound
   **inverts**: stock drove that regime MORE (13.2 % vs 4.9 %), at higher angle and command, calmly.
2. **`|model|` RISES 7–9× WITH ANGLE** — the cave's `0x14A` byte4 **b5** is the `gp-0x6AE2` rung:
   duty **0.118→0.837** (r22) and **0.104→0.934** (r23), **monotone over four bins, two routes.**
3. `friction = EMA(|model| · K1/1024 · sat(rate·12/knee))`, **in phase with rate** (EMA adds only
   −1.1°…−11.1°) and a *compensation* ⇒ **ANTI-DAMPING**.
4. **K1 `0xC40D2` = 102 → 612 = ×6 ON STOCK** — the largest single multiplication in the live diff.
⇒ **at large angle our anti-damping is 6× stock's coefficient times a 7–9× larger `|model|`.**

```
   build    knee   K1    small-signal gain   K1 vs stock
   v112     1800   612      0.0039844          6.0x     <- ON THE CAR
   v113     1800   204      0.0013281          2.0x     <- THE FIX (already built)
   V113 vs V112 = 6 bytes / 2 runs: 0xC40D2 612->204 + the CRC trailer.  Nothing else moves.
```
⭐ **V113 = V111's K1 with V112's knee** — V111 gave *"oscillations gone, ratcheting reduced"* (at the
cost of rate) and V112's knee restored the authority (tracking **1.37–1.62×** better).
**It is the combination of the two things that each worked**, and it cuts the anti-damping term to
**0.333×** exactly where `|model|` is largest.
🛑 **I deprioritised V113 and that was wrong** — V112's flight refuted the *magnitude* of the
anti-damping risk at V112's operating point, not the mechanism.
⚠ **Cost: heavier below ~30 °/s**, manual feel included (`FUN_0003b8f6` is not LKAS-gated).
⭐⭐ **V113 CUTS THE TERM 0.333× AT EVERY RATE** — linear region and saturated plateau alike ⇒ it hits
**the anti-damping (the oscillation) AND the relay kick magnitude (grind #1)** in one 2-byte change,
while the relay **corner stays at 31.8 °/s** so V112's authority win is kept. ⭐ **Self-targeting**: the
term is linear in `|model|`, which rises **7–9×** with angle, so the absolute cut is 7–9× larger exactly
where the symptom lives. 🛑 **V113 SUPERSEDES V119 as the recommended flight** — 2 bytes vs 8, one
dynamics lever vs two, and the only one with a closed evidence chain.
🛑 **Falsifier**: if V113 flies and the large-angle oscillation is unchanged, K1 is not the
mechanism and the angle gating is plant-side. A clean single-variable read.

## ⭐⭐⭐ V119 BUILT — **BOTH LEVERS + THE PROBE.** Grind #1 AND the oscillation, one flight.
```
builder  analysis-2020accord/builds/v108_plus/build_v119_tva.py   42/42   BASE = V112
image    a39801bc621de7d6c7dd5cbb207866e70e56b43027bde3851f65d5dd717328bc
.rwd     18e3216fb6f01809bc542b82f7ffc8ec9098ade5f9037a1d4ab0c9ec05feaeba
0xC40BC  1800 -> 2400   relay knee              -> GRIND #1
0xC40D2   612 ->  816   K1, cancels the gain change EXACTLY
0xC649B     1 ->    0   disarm the biquad       -> THE OSCILLATION
0x55DF2  gp-0x6ABC -> gp-0x67FA   the 427 tap   -> THE STATE-4 DIAGNOSTIC
0x55E10  sar 3 -> sar 0
8 payload bytes.  🛑 NO CAVE EDIT.  ZERO unattributed.
```
### ⭐ WHY TWO DYNAMICS LEVERS IS STILL INTERPRETABLE HERE
The single-variable rule exists so a symptom report can be attributed. These two levers target
**two symptoms whose separation is MEASURED, not assumed** — the fine `Re(Z)` spectrum
(coherence 0.5–0.85) puts the **peak-turn oscillation at 7.42 Hz on a −81 peak** (a linear loop
instability) and **grind #1 at 18–22 Hz where `Re(Z)` is −1…−10** (neutral ⇒ a nonlinearity).
⇒ **the knee cannot fix the oscillation and the biquad cannot fix grind #1**, so *"grinding better,
oscillation unchanged"* — or the reverse — **attributes itself.**

### LEVER 1 — the relay knee, on a model that has already predicted correctly
```
   knee  600 (V111)  predicted 0.7439 [0.669,0.815]   MEASURED 0.7336            route 21
   knee 1800 (V112)  predicted 0.2353                 MEASURED 0.3102 / 0.1071   r22 / r23
   knee 2400 (V119)  predicted 0.0484                 <- this build
```
`(816/1024)(12/2400) = (612/1024)(12/1800) = 0.0039844` **exactly** ⇒ **bit-identical below 31.8 °/s.**

### LEVER 2 — disarm the biquad
One byte, coefficients untouched, revert is the same byte. Corpus point estimate **1.47×**
(OFF −37.7 / ON −55.4) but **P = 0.722, not separable** — **this build is the test.**
⊕ ~32 % is the right SIZE: the oscillation is bounded, not divergent, and no damping lane can supply
more than ~10 % of the deficit anyway.

### 🛑 SCORING IS PRE-REGISTERED — `docs/scoring/SCORING-V118-preregistered.md` applies unchanged.
**Read the identity check FIRST**: the 427 wire must come back **DISCRETE {0,5,…75}** or V119 is not
on the car. `state = wire/5`; **STATE 4 = WIRE 20**; wire ≥1023 = contamination, discard.

⚠ **Honest expectation: a REDUCTION, not elimination.** The 7–9 Hz excess is plausibly the price of
deleting Honda's four limiters, not one tunable fault
([[accord-the-mod-works-by-deleting-hondas-limiters]]).

## ⭐⭐ V118 BUILT — **BIQUAD DISARM + THE STATE-4 PROBE. One flight, two answers.**
```
builder  analysis-2020accord/builds/v108_plus/build_v118_tva.py   43/43   BASE = V112
image    8a0f0080631208dfa524e5eae54a4bcc9a9fac26759bac777e29daa1c7f7c4ce
.rwd     92b798a14abed24286e9b53a0c03bb6c97b107b5c3c8c26b9701645ea8db99e8
0xC649B   1 -> 0                    disarm the biquad        (candidate FIX)
0x55DF2   gp-0x6ABC -> gp-0x67FA    the CAN 427 tap          (candidate DIAGNOSTIC)
0x55E10   sar 3 -> sar 0            probe scaling
4 payload bytes.  🛑 NO CAVE EDIT — the 164-byte cave is byte-identical.
```
The tap repoint is a pure **displacement edit**, the class that has never failed on this ECU.

### WHY BOTH IN ONE FLIGHT
The two surviving candidates for the 7–9 Hz excess are the **armed biquad** (testable by flying the
disarm) and **`0x454FE`'s deletion of Honda's state-4 governor call** (**not** safely testable by
reverting — V42's change is a validated fix for the V38 macro ratchet). What `0x454FE` needs first is
its **duty**, which is unmeasured: `gp-0x67fa` is not on the bus and no cached build telemeters it.
⇒ **fly the disarm and measure the state simultaneously.**

### THE PROBE
`wire = min(|gp-0x67fa as halfword| × 5, 0x3FF)` ⇒ **state 0–15 maps to wire 0,5,…75; STATE 4 = WIRE
20.** `gp-0x67fb` (the high byte) has 4 writers, every one `st.b r0` = **zero**. If it is ever
non-zero the wire becomes ≥ 1285 and **CLIPS at 1023** ⇒ contamination is **self-identifying** and
those samples are discarded, not misread — the guard against a hidden 6-byte-form writer.
⊕ **What is given up:** the tap's `|gp-0x6abc|` rate, which is also on CAN as `cs_rate` — the channel
every Re(Z) measurement here already uses. **No existing analysis depends on the tap.**

### READ THE DRIVE FOUR WAYS
*oscillation weaker* ⇒ the biquad contributes; reshape its coefficients next · *no change* ⇒ biquad
eliminated · *worse* ⇒ revert the one byte. **And independently:** *state-4 duty HIGH* ⇒ `0x454FE`
becomes the prime suspect, and the fix is to restore `FUN_00049A5A` **modified**, never a blind
revert · *duty ≈ ZERO* ⇒ `0x454FE` eliminated, leaving the V57 gain repoint, the ceiling raise and
~20 cal cells.

## ⭐ V117 BUILT — **DISARM THE BIQUAD.** One byte, fully reversible.
```
builder  analysis-2020accord/builds/v108_plus/build_v117_tva.py   41/41   BASE = V112
image    ea5ad8d319cf75eca90da21cc37c337192a1ebedf77a21749ceeb1e2b3d91131
.rwd     754f15a0125f58450a3af69f8b3d218009c6da782cbedba761212621098630b7
0xC649B   1 -> 0   the biquad ARM cal.  knee 1800, K1 612, alpha2 14 all HELD.
1 payload byte (01 -> 00) + 1 CRC trailer.  All three biquad COEFFICIENTS byte-identical.
```
**The filter, read from assembly @`0x35A28`–`0x35A50`:**
`y[n] = 0.81731·x + 1.53720·y[n−1] − 0.63462·y[n−2]` — all-pole, pole radius 0.79663, angle
0.26565 rad, **DC gain 8.39**. At 1 kHz its pole is 42.3 Hz (a **flat 8.4×** through 7–12 Hz); at
100 Hz it is 4.23 Hz (a **Q-2.46 resonator** on the problem band). The task rate could not be pinned
(`FUN_000352b4` is entered from an RTOS TCB at `0xBB928`), **but either way arming it puts a large
gain into the aggregator path, and stock leaves it OFF.**
🛑 Arming needs THREE edits: `0xC649B` 0→1, `0x35A08` `e798`→`fb97` (gate input `gp-0x671a` →
`gp-0x6806`), `0x35A12` `ec`→`e0` (`cmp r12,r9` → `cmp r0,r9`). **V117 clears only the CAL byte.**

### WHY THIS, AND WHY IT IS HONEST ABOUT ITS OWN EVIDENCE
Seven candidates for the 7–9 Hz excess are eliminated, each with its own control. The biquad's
natural experiment is the **strongest surviving signal**: OFF (9 routes) median **−37.7** vs ON
(8 routes) **−55.4**, a **1.47×** point estimate — far larger than V115's ~1.05×.
🛑 **But P(ON worse) = 0.722 against chance 0.5 is NOT separable at n = 9/8, and the excess is
already present at V90, which has no biquad. The biquad is NOT the origin** — at most an additive
contributor. **This build converts an unseparable observational comparison into a single-variable
on-car test.**

### READ THE DRIVE THREE WAYS
*oscillation weaker* ⇒ real contributor, next step is reshaping its coefficients · *no change* ⇒
eliminated too, move to the remaining common edits · *worse* ⇒ arming was doing useful work, revert
the byte. ⊕ **V88 — which the operator reported as "grinding FIXED" — ran with this filter OFF.**


---

## 📚 OLDER SECTIONS ARE IN THE ARCHIVE
Everything before this point that used to live here is in
**`docs/archive/STATE-ARCHIVE-2026-08-28.md`** — retired 2026-08-28 to keep this file under the
256 KB `Read` cap. It is a **record, not an instruction**; where it disagrees with this file,
**this file wins**. Earlier archives: see `docs/archive/`.
