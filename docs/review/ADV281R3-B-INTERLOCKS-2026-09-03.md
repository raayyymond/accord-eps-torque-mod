# Adversary B — interlocks, downstream consumers, closed-loop behaviour — V281 rev 3

**Subagent `adv281r3b` (firmware-codepath-tracer role), 2026-09-03.** Job: make V281 rev 3 FAIL on
interlocks, downstream consumers, closed-loop stability, or authority. Independent of the builder's own
assertions and of the sizing doc's own printed numbers — every number below is re-derived from the images,
the disassembly, or a live re-run of the kit's own scripts, not copied from a report.

**What a FAIL would look like (written before the analysis):** a downstream consumer of the rate error, P,
the sum, or `gp-0x6b38`/`gp-0x6b3c` finding a plausibility/timeout/stall threshold newly reachable under
flat Kp 248 that was not reachable under the base 248→696 ramp; any stability stratum (highway, 10-20 m/s,
loaded high-angle, creep) showing WORSE gain/phase margin at flat 248 than base; the twist-taper multiplier
combined with flat-248 P leaving insufficient hands-on authority such that openpilot's outer loop rails
permanently in turns; or a full-file-diff/CRC/`.rwd`-decode mismatch against the claimed transformation.

**Verdict: PASS to flash on interlocks/downstream/stability/build-integrity.** No new interlock is
reachable, no stability margin is worse anywhere I could test it — flat 248 is measurably the SAFEST
margin of any Kp value examined in this whole arc, including the highway band this build newly touches —
and the build is byte-clean, CRC-clean and `.rwd`-decode-clean. Two findings for the record, neither
disqualifying: (1) the twist-taper post-PID driver-torque multiplier (not mentioned in the build's own
risk disclosure) compounds with the Kp cut under real hand-on-wheel resistance at mid demand; (2) the
build script's claim that flat 248 "clears the idx-26 episode too" is not supported by that episode's own
measured self-regulation gain — a thin, disclosed-as-BELIEF margin at one specific low-speed operating
point, not a clean clear.

---

## §0 — Build integrity, independently re-derived (not read from the build script's own printed asserts)

Both images read directly (Python, not Ghidra, per the byte-level-work rule):

- `V280r2` base sha256 `b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa` — matches.
- `V281r3` sha256 `98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c` — matches the brief.
- **Full byte diff, `[0x13000, 0x100000)`, independently re-run: 218 differing bytes, 39 runs.** Code
  region `0x13000-0xC0000`: **0 diffs.** Of the 218: **198 bytes fall inside the 28 Kp-record spans**
  (`0xE4360-0xE8xxx`, the pointer bank `0xCB994`'s targets), and the remaining **20 are exactly the 5
  CRC-block trailers** (`0xE4FFC/E5FFC/E6FFC/E7FFC/E8FFC`, 4 bytes each) that own those records — matches
  the build script's own "198 payload bytes + CRC trailers" claim, independently counted from the images,
  not from the script's assertion log.
- **All 28 Kp records read directly and confirmed genuinely flat**: every record's `Y[1..4] == Y[0]`
  (dumped in full — slots 0-27, all `flat=True`). Live slot 7's LERP evaluated at every idx 0-240 (integer
  floor form) returns exactly 248 everywhere; base returns 248→696 as documented. X-knots, header, pad
  word: byte-identical to base on every record (confirmed by direct read, not by the script's own check).
- **`.rwd` decode, independently verified against the plain image** (this is the artifact that would
  actually be flashed — I did not simply trust the plain-image hash): parsed the x31 container
  (`analysis-2020accord/lib/encode_eps.parse_x31`), pulled the single payload block (`encs[0]`, 970752
  bytes, key `[0xBF, 0x10, 0x9E]` — matches the CLAUDE.md-documented TVA cipher), applied
  `((c^0xBF)^0x10)-0x9E` byte-for-byte, and compared against `img[0x13000:0x100000]`: **exact match, all
  970752 bytes, `d == region` True.** (First attempt used a naive payload slice by `payload_start+length`
  and got 692854/970752 mismatches — a framing error on my part, not a finding; `parse_x31`'s own block
  extraction resolved it, and the decoded stream opens with a readable `2018/01/30 13:04...` firmware
  timestamp, which is itself a sanity check that the cipher and offset are right.)

**Nothing outside the Kp bank changed; the flashable `.rwd` decodes to exactly the reported image.**

## §1 — Interlocks / downstream consumers: census re-derived, one prior open item closed

**Same structural census as `ADV281R2-B` applies unchanged in kind** (§0 proves only the Kp bank differs
from V280 rev 2, and V280 rev 2's own downstream chain was already re-confirmed in that pass): the chain
`FUN_00028ea6 → gp-0x6b38 → gp-0x6b3c → FUN_0002b422 → distribute_clamp → mixer → aggregator → governor →
shaper → FOC` carries clamps (10240, ~4762, 8192) all well above the LKAS lane's own 3072 ceiling, which
this build **cannot raise** — Kp Y[0] is asserted (by the build script, and re-confirmed by me directly)
to be the record's minimum, so the lane's output only ever falls, never rises, at every idx above 0. A
lower ceiling-approach speed cannot newly trip an UPPER threshold.

- **Corridor/lockstep** (`memory/reference/firmware/reference_accord_corridor_lockstep.md`,
  `reference-accord-watchdog-fault-sm-fun43e44.md`): reads its own cal cells (`0xC674E`, `0xC6598`,
  `0xC6664`, `0xC6760`...) and int/float twin re-derivations of driver-torque/corridor-floor/boost — **none
  of which is in the touched byte set** (§0's diff is entirely inside `0xE4xxx-0xE8xxx`). Structurally
  unreachable by this edit, independent of magnitude.
- **Soft-EME bound-arm, gentle-EME**: same conclusion as rev 2 — driven by the post-governor aggregate
  and by driver column torque/angle-rate respectively, not by this lane's E/P/T. The LKAS lane's ceiling
  is unchanged (3072); a slower-rising, and now uniformly lower, P reaches any given command level more
  slowly and to a lower peak — gentler on an integrator that trips on exceeding a bound, not more
  aggressive.
- **A NEW angle I checked that rev 2's pass did not need to** (rev 3's authority cut is far larger —
  -25...-48% vs rev 2's -13...-28% — so I looked specifically for a MINIMUM-torque / under-delivery /
  "not tracking" plausibility check, not just upper-threshold ones): searched
  `memory/reference/firmware/` for plausibility/DTC/minimum-torque records
  (`reference_accord_driver_override_plausibility_eme.md`, `reference-accord-watchdog-fault-sm-fun43e44.md`,
  `reference_accord_corridor_lockstep.md`). **Every plausibility/DTC mechanism on record compares a
  SAME-CYCLE int/float twin re-derivation for internal consistency (corridor lockstep, weight-summed
  7-flag watchdog) or a driver-torque-channel spread/ceiling (the override voter), not the delivered LKAS
  torque against a floor.** No under-delivery interlock exists in the kit's record, and nothing in this
  edit could create one (it changes one input constant to an unrelated function, read identically by
  whatever consumes its output).
- **The per-mode fault/DTC counter at the tail of `FUN_00028ea6`** — the one item `ADV281R2-B` flagged as
  unresolved ("did not find a path from E/P magnitude into it, but did not exhaustively rule one out
  either"). **I traced this to closure with EVIDENCE (Ghidra decompile of `FUN_00028ea6`, tail lines
  ~1290-1303, re-confirmed live in this session):**
  ```
  uVar20 = *(byte *)(*(int *)(unaff_gp + -0x257c) + 0x14);      // a mode byte, via a pointer, NOT from E/P/T
  iVar23 = min(uVar20, 7);                                       // clip to 0-7 (an 8-slot per-mode index)
  pcVar43 = (char *)(unaff_gp - 16000 + iVar23);                 // per-mode counter array
  *pcVar43 += 1; cVar15 = *pcVar43;                               // increment, read back (every call)
  gp-0x67a2 = 1; gp-0x6b3c = uVar13*bVar6; gp-0x67a7 = (iVar28!=0); gp-0x67a3 = 1;   // unconditional flag writes
  if (cVar15 != param_1 && gp-0x3e78[iVar23] == 1) FUN_0001cba6();                  // fires on a state CHANGE, gated by a per-mode enable flag
  ```
  `param_1` is the function's own call argument (an expected/previous state passed by the caller), and
  `uVar20`'s source (`gp-0x257c`'s pointed-to byte) is read fresh at this point, disconnected from the
  E/P/D/Kp/T arithmetic computed earlier in the function. **This is a per-variant-slot call-count/heartbeat
  watchdog (indices 0-7 line up with the reachable-slot structure this whole build touches), not a
  torque-magnitude or tracking-error plausibility check.** Closing the census item: no path from E, P,
  Kp, or the delivered torque into this trip, confirmed by direct trace, not by absence of a found path.

**Interlock census: PASS, and more thoroughly closed than rev 2's (one open item resolved, one new angle
checked and cleared).**

## §2 — Stability, re-derived independently in every stratum named in the brief

I did not trust the sizing doc's or the build script's printed numbers for flat 248 — I re-ran the kit's
own live scripts against the real images and, for highway, wrote a fresh point-wise check against the
raw plant data (not the parametric fit used elsewhere), specifically because flat 248 is a materially
larger dose than rev 2's flat 341, and the highway band is (per the build script's own honest disclosure)
newly touched this time, unlike rev 2.

**Loaded high-angle (`v ≤ 10, |angle| ≥ 30`), re-running `kpflat_sizing.py` live against the V280 rev 2
image** (identical script rev 2's own adversary used for 341; I re-ran it fresh, not copied its printed
table):
```
plant pole+delay, tqIV:      FLAT 248 (Kp0)  248 | 2.38 1.39 1.12 0.92 0.66 | -149 | PM 27° @ 7.6 Hz | GM 2.00x @ 12.0 Hz | Ms 2.9 @ ...
plant pole+delay, direct:    FLAT 248 (Kp0)  248 | 2.22 1.31 1.05 0.87 0.62 | -148 | PM 30° @ ...      | GM 2.16x            | ...
plant 2nd-order+delay, tqIV: FLAT 248 (Kp0)  248 | 2.50 1.42 1.11 0.89 0.60 | -150 | PM 26° @ ...      | GM 2.09x            | ...
K_crit(linear, Kd 128) = 425 / 443 / 426  (three fits, all independently re-computed by bisection)
```
**Flat 248 sits at 0.58× K_crit — the largest headroom (42-46% below the linear instability threshold)
of any Kp value examined anywhere in this arc**, versus rev 2's 341 at 0.80× K_crit (only 20% below,
called "thin" by `ADV281R2-B`). Confirmed independently, live, not quoted.

**Highway/lane-change (idx 2-12, the ONE stratum this build touches that rev 2 did not) — computed
point-wise against the raw highway-ref plant** (`v≥20, |angle|<8, |tq|<500`, the same `PI.Pool()` the kit's
scripts already validate this data through; `direct` estimator, own script, not the doc's parametric fit
which was only built for the A2/A3 stratum):
```
Kp 248 (REV3 flat)  : |L|@1/2/3/4/6/8Hz = 0.852 0.390 0.730 0.869 0.855 1.039   phase +27/-6/-17/-35/-58/-72°
Kp 255 (base idx 2) : |L|@1/2/3/4/6/8Hz = 0.876 0.401 0.748 0.890 0.872 1.056   phase +27/-6/-18/-36/-59/-73°
Kp 263 (base idx 4) : |L|@1/2/3/4/6/8Hz = 0.903 0.413 0.770 0.914 0.892 1.076
Kp 271 (base idx 6) : |L|@1/2/3/4/6/8Hz = 0.930 0.425 0.791 0.938 0.912 1.096
Kp 279 (base idx 8) : |L|@1/2/3/4/6/8Hz = 0.957 0.437 0.813 0.962 0.932 1.117
Kp 286 (base idx 10): |L|@1/2/3/4/6/8Hz = 0.981 0.448 0.832 0.983 0.950 1.135
Kp 294 (base idx 12): |L|@1/2/3/4/6/8Hz = 1.008 0.460 0.853 1.008 0.971 1.156   phase +27/-7/-20/-38/-62/-77°
```
**At EVERY frequency 1-8 Hz, `|L|` at flat 248 is strictly the LOWEST of the row, and phase is within
1-3° of every other row (essentially unchanged shape, just lower magnitude).** No crossing near unity
above 8 Hz in this band (phase only -72...-77° at 8 Hz, far from -180°). This directly cross-checks the
kit's own `part4()` "HIGHWAY" section (which prints Kp 268 vs 295 vs 645 and shows the same monotonic
trend: `|L|@1/2/3Hz` 0.92/0.42/0.78 → 1.01/0.46/0.86 → 2.20/0.99/1.82 as Kp rises 268→295→645) — **I
extended it to the exact value this build ships (248) and confirmed the trend holds through it: lowering
Kp in this band strictly adds margin, it does not spend it.** The build script's own disclosure
("the highway band is no longer inert, -3%...-16%") is honest about there being an effect, but the effect
is a further SMALL loop-gain reduction in an already heavily-margined band (LOWCMD-LOOPGAIN's independent
measurement on the same stratum: PM 48-54° at 13-15 Hz crossover, no -180° below 15 Hz, at Kp 341) — not
a new risk.

**Creep 20 Hz** (`rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md`, §1.4): this study's own L_in
table already carries a **Kp=248 row** — I did not need to extend it, since rev 3 makes 248 the value at
every idx, matching this row exactly across the whole creep operating range rather than only at idx 0:
```
direct G, Kp 248: |L(20)| 0.74 ∠-141°, PM 56° @ 7.2 Hz, Ms 1.81 @ 8.6 Hz
direct G, Kp 295: |L(20)| 0.87 ∠-146°, PM 90°(different crossing), Ms 2.03
direct G, Kp 341: |L(20)| 0.81 ∠-149°, PM 86°(different crossing), Ms 2.19
direct G, Kp 470: |L(20)| 0.91 ∠-157°, PM 35° @ 18.4 Hz, Ms 2.64
```
**Kp 248 has the lowest sensitivity peak (Ms 1.81) of every Kp value tested — the least resonant 20 Hz
line of the four.** The study's own mechanism finding (creep20 §5) — a lightly-damped resonance excited
by broadband input, not a self-sustained limit cycle, confirmed linear (clamps at 0.00-0.05 duty) in the
operator's own hands-light windows — means a lower loop gain can only reduce the excitation this mode
receives, consistent with Ms falling. **No worsening anywhere.**

**Verdict §2: in every stratum I could test — loaded high-angle, highway/lane-change (newly touched),
creep — flat 248 has EQUAL OR STRICTLY BETTER margin than V280 rev 2's ramped Kp. I could not construct a
FAIL condition on stability.** This is a stronger result than `ADV281R2-B` found for rev 2's flat 341
(which had one thin, disclosed margin in the loaded high-angle stratum); flat 248 closes that exact gap.

## §3 — Authority / the twist-taper interaction: the finding not in the build's own risk disclosure

**Independently computed** (Python, reading map/Kp/postA/postB records directly from the image, per the
`FUN_00028ea6` arithmetic pinned in `rlog-tools/studies/osc-highangle/TWIST-TAPER-LOOP-2026-09-03.md` §1):
stalled-wheel (`fb=0`) delivered `T` at each idx, **at several real driver-torque levels**, not just the
build's own hands-off (`m=254`) assumption:

```
 idx  tq_raw |    base T (m) |   rev3 T (m) | rev3/base
  26      0  |  -773.8 (254) |  -551.5 (254)|  0.71
  26   1536  |  -542.2 (178) |  -386.4 (178)|  0.71
  26   2048  |  -231.5 ( 76) |  -164.9 ( 76)|  0.71
  40      0  | -1388.7 (254) |  -854.6 (254)|  0.62
  40   1536  |  -973.2 (178) |  -598.9 (178)|  0.62
  58      0  | -2359.7 (254) | -1237.2 (254)|  0.52
  58   1536  | -1653.7 (178) |  -867.1 (178)|  0.52
  58   2048  |  -706.0 ( 76) |  -370.1 ( 76)|  0.52
  68      0  | -2462.1 (254) | -1450.9 (254)|  0.59
 100      0  | -2462.1 (254) | -2136.5 (254)|  0.87
 120+       (both railed, identical) |  1.00
```
The multiplier `m` (`0xCBC34`×`0xCBBC4`) is **independent of Kp** — it cancels in the rev3/base ratio at
fixed idx, which is exactly the idx-dependent authority-cost ratio the build script already discloses
(-29%...-48% at idx 26-80). **What the build script's own risk section does NOT compute or mention is the
COMPOUND**: at `idx 58` (a mid-demand, 32.3 deg/s-reference operating point, matching the r31 stall-stutter
class) under a firm hand grip (`tq ≥ 2048` raw, where the live twist-taper floor bites), the delivered lane
torque falls to **370 counts** — 15.6% of the ORIGINAL base-full-authority figure at that idx (2364), the
product of the Kp cut (0.52×) and the driver-torque floor (0.30×) independently justified but compounding.

**This is not a FAIL** — 370 counts is still comparable to, or larger than, the p50 delivered torque on
ordinary hands-light cruising on the kit's own recorded routes (r32/r33/r34's `|T| p50` runs 195-1102
counts across conditions, per `LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md` §2), so the lane does not go
to zero and the override-taper mechanism (reducing LKAS push under active driver resistance) is doing what
it is designed to do, now compounded with a second, independently-justified authority cut. **Flagging it
because it is real, quantified, and absent from the build's own disclosure** — the pre-registered drive's
cost read (stalled-wheel `|T|` at idx 40-80) should specifically include a hands-on trial at this operating
point, not only the hands-off case the build script's own table covers.

**The r31-class P-unrailed window widens under flat 248** (independently re-derived by continuous bisection
search, same method `ADV281R2-B` used for rev 2's 341):
```
rate=0.0 deg/s stall (reference-scale):  base rails at idx≥59.6   rev3(flat248) rails at idx≥115.3
rate=15.0 deg/s stall (r31-realistic):   base rails at idx≥79.3   rev3(flat248) rails at idx≥142.2
```
So flat 248's "P stays linear" window (idx 58-115 or 79-142, depending on the stall model) is WIDER than
rev 2's already-flagged window (idx 60-84 / 79-111 from `ADV281R2-B`). **Per the kit's own established
mechanism** (`accord-v278r3-high-angle-stutter-is-p-desaturating-on-a-stalled-wheel.md`), the 7 Hz ripple
crosses P's linear window when P is NOT railed — so on that framing, a wider unrailed window sounds like
MORE exposure, not less. **But §2 already answers this directly**: flat 248 does not depend on P railing
to stay bounded — the LINEAR loop itself sits at 0.58× K_crit (vs rev 2's 0.80×), the largest margin of
any Kp value tested. Rev 3's stability argument is structurally different from, and more robust than, rev
2's (which partly relied on clipping to bound a marginally-unstable linear loop in parts of its range).
**Stated plainly for the record: the mechanism that stabilises rev 3 is not "P rails more/less," it is
"the linear loop itself no longer approaches instability" — a wider unrailed window is not evidence
against this, given §2's margins.**

**The idx-26 / 2.2 m/s "stiffer" operating point is NOT cleanly cleared, contra the build script's own
phrasing.** `kpflat_sizing.py`'s Part 3 describing-function measurement on the single real episode at that
operating point (r33 100.8, idx 26, 265° angle) gives `K_eff = 225` (the loop's own self-regulated gain
there). **Flat 248 (248 > 225) sits 10% ABOVE that specific episode's measured K_eff**, not below it — the
build script's claim that flat 248 "clears the idx-26 episode too" rests on the GENERIC plant-fit PM number
(27° at the pooled idx≥106 operating region), not on a re-derivation at idx 26's own stiffer point. This is
the same class of thin, single-episode margin `ADV281R2-B` flagged for rev 2's window — worth carrying into
the pre-registered drive's read (if the 7 Hz signature reappears specifically at low speed / high angle /
low demand, idx 20-30, that is the operating point to check first, not the idx≥68 class the build's own
instrument is tuned to).

## §4 — Summary against the FAIL sentence written at the top

1. Downstream interlock newly reachable: **NO** — census re-confirmed structurally (§1), one prior open
   item closed with evidence, one new angle (under-delivery/minimum-torque plausibility) checked and
   cleared.
2. Any stratum worse margin: **NO** — loaded high-angle, highway (newly touched), and creep 20 Hz all
   independently re-derived; flat 248 has the best margin of any Kp value examined in every one.
3. Twist-taper + authority cut leaves the lane unusable hands-on: **NO, but compounds further than
   disclosed** — quantified at idx 58 / firm grip: 370 counts, non-trivial but a real, undisclosed
   compound worth watching on the drive.
4. Build-integrity mismatch: **NO** — image hash, full diff scope, all 28 records, CRC, and now the
   `.rwd`'s own cipher decode all independently confirmed exact.

**No FAIL condition met. PASS to flash on interlocks/downstream/stability/build-integrity, with two
findings for the pre-registered drive's read to take seriously: the hands-on stalled-mid-demand authority
compound (§3), and the idx-26 low-speed/high-angle operating point's thinner-than-headlined margin (§3).**
Neither is disqualifying; both are the honest residuals, in the same spirit as `ADV281R2-B`'s residual for
rev 2 — and rev 3's overall margin picture is measurably safer than rev 2's on the one axis that mattered
most there (loaded high-angle K_crit headroom: 42-46% here vs 20% for rev 2's 341).
