---
name: reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive
description: FUN_00036388 (return-centre, gp-0x6b62) fully traced at instruction level. Its gp-0x6a82 counter drives a genuine VALUE-SNAP relay (sVar8 jumps from tracking |gp-0x6b64| to a fixed 1024 ceiling once dwelled >20 ticks) -- a real describing-function nonlinearity, cal handles (0xC618A/0xC627E) confirmed blast-radius-zero. 🛑 F6's 2026-08-05 "dead code / sign flips between brake and pump" claim about FUN_000360fe's LERP table is RETRACTED -- F6 misread tp-relative addresses off by 0x1000 (0xC7xxx instead of 0xC6xxx); F2 independently re-read the correct bytes (X=[-397,-192,140,294,384] strictly increasing, Y=[0,2560,2560,717,0] all >=0) and F6 confirmed the correction with a fresh independent read, bit-for-bit match. The lane is a PURE unconditional brake (never a pump), active only in a narrow gp-0x6bda window, inactive (Y=0, term=0) far outside it -- see F2's PART 2/3 sections for the full corrected picture including a properly build-identity-confirmed V69 telemetry decode.
metadata:
  type: reference
---

## 🛑🛑🛑🛑 2026-08-05 PART 3 (F2) — CORRECTS F6: `FUN_000360fe`'s table is NOT degenerate, NOT brake/pump-split; it is a pure unconditional brake with a narrow activation window

F6 claimed (via team-lead) that `FUN_000360fe`'s LERP has `X_lo == X_hi == 14` (a dead 3-point inner
search) and that the lane flips sign — brake below 14, pump above — citing instructions at `0x3610a`,
`0x36116`/`0x36118`, `0x36120`, `0x36124`/`0x36126`. **Independently verified by TWO methods, both
disagreeing with F6:**

1. **Fresh `disassemble_function(0x360fe)`, this session** — the instruction addresses match F6's
   citation exactly, but confirm the operands are `ld.h 0x795e[tp],r16` (X_lo) and
   `ld.h 0x7966[tp],r13` (X_hi), i.e. TWO DIFFERENT flash cells, not a repeated read of one cell.
2. **Raw PowerShell byte read of BOTH images at every cell this function touches**, cross-checked
   stock vs `_v72_plain_image.bin` (all MATCH, byte-identical):

   | cell | addr | value |
   |---|---|---|
   | count | `0xC695C` | 5 |
   | X_lo | `0xC695E` | **-397** |
   | X[1] | `0xC6960` | -192 |
   | X[2] | `0xC6962` | 140 |
   | X[3] | `0xC6964` | 294 |
   | X_hi | `0xC6966` | **384** |
   | Y_lo | `0xC6968` | 0 |
   | Y[1] | `0xC696A` | 2560 |
   | Y[2] | `0xC696C` | 2560 |
   | Y[3] | `0xC696E` | 717 |
   | Y_hi | `0xC6970` | 0 |
   | cal_73BE (final scale) | `0xC63BE` | 1024 |

**`X_lo=-397` and `X_hi=384` are NOT equal, NOT 14, and the full 5-point table `X=[-397,-192,140,294,
384]` is properly sorted and count-consistent (5 breakpoints, count field=5). The inner 3-point search
(`0x36128`-`0x36140`) is LIVE, not dead code.** F6's "14" and "+4164/-8064" numbers do not appear
anywhere in this table or its neighbourhood on either image — the source of that misread is unknown,
but it is not this table.

**Bigger correction — there is NO brake/pump sign split anywhere in this mechanism.** Every `Y` value
in the table is `>= 0` (0, 2560, 2560, 717, 0 — never negative). The tail of the function
(`sVar4 = -((Y * gp-0x6abc >> 10) * cal_73BE) >> 10`, then clamp `±0x2800` to `gp-0x6b64`) applies ONE
unconditional negation to the whole product. Since `Y >= 0` always, `sign(gp-0x6b64) = -sign(gp-0x6abc)`
whenever `Y != 0` (i.e. whenever the lane is active at all) — **the lane ALWAYS opposes motor rate. It
is a pure, unconditional brake, never a pump, regardless of `gp-0x6bda`'s value.** `gp-0x6bda` decides
only WHETHER the brake is active (`Y != 0`, i.e. `gp-0x6bda` inside roughly `[-397, 384]`) and HOW
STRONG (the plateau `Y=2560` for `gp-0x6bda` in `[-192, 140]`, tapering to `717` at `X[3]=294`, to `0`
at the edges) — never its direction.

**Consequence for "gp-0x6bda's typical value" (team-lead's actual question, now correctly framed)**:
the real question is not "above or below 14" but **"is `|gp-0x6bda|` typically inside or outside
roughly `[-397, 384]` during engaged creep driving?"** Given the established hands-off value
`gp-0x6bda ≈ 9262` (`reference_accord_rate_lane_v62_to_v69_gain_arc.md`) sits FAR outside this window,
**this brake term is INACTIVE (`Y=0`, contributes nothing to `gp-0x6b64`) during light/hands-off
driving**, and only activates when driver torque `x=gp-0x6bf0` sits within a few hundred counts of its
own recently-established peak-hold edge (UPPER or LOWER) — a specific, effortful condition, not
"typical" light creep steering by itself. **Not yet resolved: how often creep steering corrections
actually push `x` that close to its own peak-hold edge — needs either live telemetry on `gp-0x6bda`
directly (not currently in any flown probe) or a numeric characterisation of the band's typical width
during a real drive, neither done this session.**

---

## 🛑🛑🛑 2026-08-05 PART 2 (F2) — gp-0x6bda traced to a TRUE no-decay peak-hold, AND the V69 bit5 telemetry decoded

**`gp-0x6bda`'s producer chain, fully closed [EVIDENCE, decompile + instruction-level]:**
`FUN_00036022` (called from the SAME `FUN_0002214a` task1/1kHz as `FUN_00036388` — confirmed via
`get_function_callers`, so no rate mismatch) computes `gp-0x6bda = margin(x=gp-0x6bf0, UPPER=gp-0x6bd8,
LOWER=gp-0x6bd6) - (cal(0xC614C)=128 unless gp-0x67fe==2)`, matching
[[reference_accord_rate_lane_v62_to_v69_gain_arc]]'s prior formula exactly. UPPER/LOWER are maintained
by `FUN_00035d38`, disassembled fresh this session (`0x35d38`-`0x35dfe`): **a TRUE one-directional
peak-hold with NO organic decay** — in the normal path (`param_2==0`, `gp-0x37ba==0`), UPPER only grows
when `x` exceeds it (peak-hold ratchet), else stays EXACTLY FROZEN; clamped at `cal(0xC614A)=10048`.
**The "recentre" branch (`gp-0x37ba!=0`) is STRUCTURALLY DEAD** — corrected `search_instructions` (plain
`"37ba"`, no bracket assumption) finds exactly 3 real `gp-0x37ba` accesses image-wide, ALL inside
`FUN_00035d38` itself: 2 reads and 1 unconditional `st.h r0,-0x37ba,gp` (zero-write) at the end of every
call — **nothing anywhere in the image ever sets it nonzero**, so that path can never execute. The only
OTHER reset is `param_2` (=`cVar6`, gated on the SAME hysteresis bytes `gp-0x6440`/`gp-0x6441` used
throughout `FUN_00036388`) — not traced to a numeric frequency, but structurally tied to the same
debounce family, plausibly rare/edge-triggered.

**Consequence for the reset-on-rise finding above**: with UPPER/LOWER frozen (the default, no-decay
case), `gp-0x6bda`'s motion becomes a DIRECT MIRROR of `x`'s (driver torque's) own instantaneous
derivative: `gp-0x6bda` RISES exactly when `x` FALLS, and is FALLING-OR-FLAT exactly when `x` RISES or
holds. So `FUN_00036388`'s counter accumulates during `x`'s rising-or-holding phase each cycle, not
during some separate slow decay. At 21 Hz, one rising half-period is `~1/(2*21)` ≈ 23.8 ms ≈ 24 ticks
at 1 kHz — **just above the 20-tick dwell cap**, a favorable coincidence for the hypothesis, not a
refutation, PROVIDED `x`'s own motion stays reasonably monotonic through each half-cycle (assumed, not
independently verified) and does not keep setting new peaks (which would re-freeze UPPER at a higher
value each time rather than genuinely reset gp-0x6bda's SIGN structure — a second-order effect not
chased further).

**★★★ THE FREE TELEMETRY TEST, RUN [EVIDENCE, `rlog-tools/probe/decode_v69_ratchet.py` against
`analysis-2020accord/rlogs/75604b0a432fdc89_0000004f--61171e660d--{0..7}--rlog.zst`, all 8 route-4f
segments, 47,996 frames, 481.7 s]:**
- Build identity CONFIRMED: byte4 = `0x87` on 100% of frames (bit7 set, bit3 clear), matching
  `docs/BUILD-LINEAGE.md`'s V69 identification for this exact route.
- **bit5 (`gp-0x6b62 >= +4096`, the operator's own hypothesis) is CONSTANT 0 — 0.0000% duty, ZERO
  toggles — across the WHOLE 481.7 s route, the WHOLE 345.7 s engaged period, engaged+creep (137.0 s),
  the ratchet-specific cell (71.7 s), AND manual.** This is a REAL, interpretable null, not a V64-style
  dead-instrument one: the script's own analog-channel check confirms the SYMPTOM (a genuine 6-9 Hz line
  in bar-torque/angle-rate, above a matched-outside-cell null) was present in 4/9 episodes on this
  route, median 7.56 Hz. **Separately and more directly relevant to grind #1**: `docs/BUILD-LINEAGE.md`
  already established THIS SAME route independently carries grind #1 (18-22 Hz, pooled f0 20.42 Hz,
  prominence 13.47, present in 6/8 segments) — and the duty table's "engaged"/"engaged+creep" rows are
  NOT frequency-filtered, so **bit5 reading constant 0 across the WHOLE 345.7 s engaged period is a
  genuine null covering the grind #1 episodes themselves**, not just the (already-fixed-by-V72) 7.56 Hz
  ratchet cell.
- **How this interacts with the structural finding above**: `gp-0x6b62`'s reachable max is `4762+1024
  =5786` (`sVar13`+`sVar8`), and `sVar13` only approaches its ~4762 ceiling when `iVar6` (the
  `gp-0x6990` ramp) is NEAR-SATURATED, which needs `sVar10`'s sign to hold steady for ~1 s. **If grind
  #1 were a genuine ~21 Hz oscillation in the gating signal, `sVar10`'s sign would flip every ~24 ms,
  keeping `iVar6` small and the total lane output dominated by `sVar8` alone (max 1024) — comfortably
  UNDER the 4096 threshold this probe tests.** So this null RULES OUT the `iVar6`-saturated /
  `sVar13`-dominant regime (a large, steady excursion) during grind #1 on this route, but does **NOT**
  by itself rule out a small-amplitude (~1024-2000-ish), genuinely-chattering relay — exactly the
  "4096 is 4x the relay's own 1024 amplitude" caveat team-lead pre-registered. **Read as: no evidence
  of a LARGE relay excursion during the confirmed grind #1 episodes on this route; the small-amplitude
  chatter case remains open and would need a lower-threshold or raw-value probe to settle.**

**UPDATED VERDICT: WEAKENED, leaning toward REFUTED-AS-A-DOMINANT-MECHANISM, still short of clean
REFUTED.** The counter/snap machinery is real and the 24-tick/20-tick timing works out favorably, but
the on-car telemetry from the SAME route that independently confirms grind #1 shows no large excursion
of this lane at all, and the mechanism's own arithmetic predicts that IF it were chattering at grind #1's
rate, its amplitude would stay small enough to be invisible at this probe's 4096 threshold — which
means the strongest, cleanest form of "relay explains grind #1's measured amplitude" is not supported,
while a subtler "relay contributes a small chattering component" is neither confirmed nor excluded.
**Next step, if this is still worth pursuing**: a lower-threshold (e.g. >=1024 or >=2048) or raw-value
probe on `gp-0x6b62` specifically during grind #1 episodes — a new build, not a free re-analysis.

---

## 🛑🛑 2026-08-05 PART 1 RED-TEAM PASS (F2) — instruction-level confirms the relay is real, finds a reset-on-rise dependency the earlier passes missed, and corrects team-lead's raw scan

Team-lead proposed this as V73 (a lever on `0xC618A` and/or `0xC627E`) and asked me to try to break it.
Re-disassembled the WHOLE function (`0x36388`-`0x365ce`) at the instruction level, register-by-register,
specifically to nail two things the decompile alone doesn't make obvious.

**[EVIDENCE, instruction-level] The dwell counter is FORCE-RESET TO 0 every tick `gp-0x6bda` (driver
peak-hold) is RISING — not just gated, RESET.** Traced precisely: `0x3641a cmp r14(prevBda),r11(curBda);
0x36420 ble 0x3642e` (falling/flat -> `r14=gp-0x6a82`, continue counter history) vs the RISING fallthrough
at `0x36422-0x3642c`, which in stock (`cal(0xC6132)=1`, confirmed byte-identical stock/V72) executes
`cmovne 0x0,r14,r14` then `bne 0x36432` **skipping the `ld gp-0x6a82` entirely** — the register that becomes
`uVar12` (the counter used for BOTH the increment-cap test at `0x3645e` AND the snap test at `0x3649a`) is
**hard-zeroed**, not merely held. This is a genuinely separate register (`r14`) from the OTHER accumulator
this function also runs (`gp-0x6990`/`r1`, the `+-33/tick` ramp feeding `sVar13` below) — the two do NOT
share state despite superficially similar branch gating. **Consequence: the relay needs `gp-0x6bda`
non-rising for the FULL >=20-tick dwell, not just `|gp-0x6b64|<1024`.** Whether this kills the hypothesis
is genuinely two-sided and NOT resolved this session: `gp-0x6bda` is a PEAK-HOLD (per
[[reference_accord_r26_is_structurally_inert]]'s r26 constellation), so by construction it does NOT rise on
every oscillation cycle, only on a NEW maximum — a steady-amplitude 18-22Hz hand oscillation could plausibly
hold one peak and let the counter accumulate across many cycles, OR could reset it every cycle if each
half-swing sets a fresh local peak. **`gp-0x6bda`'s own time-constant/decay behavior was not traced this
session — this is the single highest-value next static check**, ahead of anything else in this file.

**[EVIDENCE, instruction-level] `sVar8` (the snap, max 1024) is added to a SEPARATE ramp-scaled term,
NOT simply summed with a static value.** `sVar13`(reused name, the ACTIVE-branch term) =
`sign(gp-0x6b5e) * min(|gp-0x6b5e|, sVar7) * (iVar6/32768)`, where `iVar6` is the SAME `gp-0x6990`
ramp (clamped `[0,0x7fff]`, `+-33/tick`, confirmed at `0x36416` and reused unmodified at `0x36500`,
independent of the reset-on-rise logic above). At `iVar6~=0` (shortly after `sVar10`'s sign last
flipped) `sVar13~=0` and the snap DOMINATES; at `iVar6` saturated (~1s of consistent sign) `sVar13` can
reach the SAME order as `gp-0x6b5e`'s own trapezoid ceiling (~4762, matching V69's `5786 = 4762+1024`
decomposition exactly) and DOMINATES the snap 4.6x. **Team-lead's Attack Line #1 is correct that this
matters — the snap's significance is CONDITIONAL on how long `sVar10`'s sign has been consistent, not
a given.**

**[EVIDENCE, instruction-level] Attack Line #4 (does lowering `0xC618A` cancel via `sVar13`) is
STRUCTURALLY CONFIRMED, magnitude UNRESOLVED.** `sVar7 = clamp(gp-0x6b96 - cal(0xC618A), 0, 0x2000)` —
lowering the cal RAISES `sVar7` before the clamp, which can raise `sVar13`'s `min(|gp-0x6b5e|,sVar7)`
term. Net direction/size depends on `gp-0x6b96`'s typical magnitude at the operating point, which prior
memory only traced to a rolling-buffer copy inside `FUN_000352b4` (`0x3574a`, from `gp-0x37d6`) without a
numeric range — **not resolved, flagged as open both times now.**

**[EVIDENCE, instruction-level] Branch reachability, checked point by point:** `cVar16`(`gp-0x67fe`)!=0 —
reachable, EPS assist substate valid in `{1,2}` per golden model. `cal(0xC64A1)=1` (dynamic/active branch,
not "coast") — confirmed BYTE-IDENTICAL stock vs V72 this session. `uVar12` genuinely IS the pre-update
counter, no decompiler reordering — confirmed by register tracking (`r11` set once at `0x3644e`, reused
unmodified at both the increment-cap test `0x3645e` and the snap test `0x3649a`). The `gp-0x6a98`/
`gp-0x2584`/`gp-0x2588` bit-6 early-out is the SAME "state word" documented independently in
`reference_accord_uds_read_surface_a160.md` (there testing bit `0x80` for UDS gating) and
`reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md` (there testing bit 31) —
a shared multi-bit status word, general pattern suggests it's fault/health-class and likely clear during
ordinary healthy driving, but **bit 6 specifically was NOT individually traced this session — genuinely
open, BELIEF not EVIDENCE.**

**🛑🛑 Corrects team-lead's raw LE byte scan for `0xC618A` readers — 5 of 6 claimed cross-function hits
are FALSE POSITIVES.** Disassembled every claimed address at its instruction boundary: `0x51c2c` (in
`FUN_00051c1c`), `0x7e812`/`0x7e828` (in `FUN_0007e74a`), `0x3780a` (in `FUN_000377ba`), `0x416c2` (in
`FUN_00041464`) are ALL the 2-byte `subr rX,rY` opcode (`8?71` byte pattern) — none of those functions
reference `tp+0x718a`/`0x718b` anywhere nearby (confirmed by full disassembly of the surrounding code;
`FUN_000377ba` reads `tp+0x50ba`=`0xC40BA` instead, `FUN_00041464` reads `tp+0x50ee`/`0x7134` instead).
**NEW V850 scan trap for the record: the common 2-byte `subr` opcode (`8?71`) collides byte-for-byte with
a fragment of the disp23/extended-displacement encoding for `0x718a`/`0x718b` — a raw LE scan for that
displacement will false-positive on every nearby `subr` instruction in the image.** The remaining claimed
hits (`0x36442`/`0x36470`/`0x364a0`, even-form `0x51c2c` doesn't count twice) are the SAME 3 genuine reads
already found inside `FUN_00036388` itself (`0x36440`, `0x3646e`, `0x3649e`), just cited at a different
byte offset within each 4-byte instruction. **Corrected finding: `0xC618A` has EXACTLY ONE reader function
image-wide (`FUN_00036388`), same exclusivity as `0xC627E` — the lever's blast radius IS clean, even
though this doesn't resolve whether the mechanism itself matters.**

**RED-TEAM VERDICT: WEAKENED, not REFUTED.** The relay-with-dwell IS real at the instruction level (not
a decompiler artifact) and its cal handles ARE isolated/clean. But it rests on an unresolved dependency
(does `gp-0x6bda` stay non-rising through an actual 18-22Hz oscillation?) that could go either way, plus
two structural couplings (`sVar13` vs `sVar8` dominance, and `sVar7`'s reaction to lowering `0xC618A`)
that are confirmed to exist but not sized. **Cheapest next step, unchanged from the previous pass and
still the highest-value action available: decode V69's already-flown `gp-0x6b62>=4096` bit5 raw series
on route 4f** — that's live telemetry that would settle the reset-on-rise question and the dominance
question simultaneously, for free, before any new build.

---

## 🛑 2026-08-05 UPDATE — re-scoped to grind #1 (18-22Hz), sharper mechanism, do not read the old title as "eliminated"

Team-lead flagged (correctly) that this file's original framing was retired against the 7.5Hz ratchet
specifically and should not be inherited against 18-22Hz without re-checking. Re-traced with fresh
`disassemble_function(0x36388)` this session, instruction-level (not just decompile) on the exact
gp-0x6a82 mechanism at `0x36432-0x364a2`:

**The snap, pinned at the instruction level [EVIDENCE]:** `r11 = (gp-0x6a82_before_this_tick <= 20)`
(`0x3644e-0x36454`) is captured BEFORE the counter's own +/-1 update, then reused at `0x3649a-0x3649e`:
`if (r11 != 0) keep r7=|gp-0x6b64|; else r7 = cal(0xC618A) = 1024` — i.e. once the dwell counter has
climbed past 20 (from sustained `|gp-0x6b64|<1024` residency), `sVar8`'s magnitude JUMPS from
continuously tracking `|gp-0x6b64|` to a FIXED value, decoupled from the instantaneous input. This is a
**relay-with-dwell-delay** (Schmitt-trigger-adjacent), a textbook describing-function limit-cycle
nonlinearity — sharper than this file's original "hysteresis and ZERO-gating" description, which didn't
spell out that the transition is a hard VALUE snap, not a continued smooth ramp.

**Timescale re-priced against grind #1, not the ratchet:** the counter's full sweep is 20 ticks = 20ms at
the confirmed 1kHz rate (`get_function_callers` -> `FUN_0002214a`, unchanged). Grind #1 (18-22Hz) has a
**22.7-27.8ms half-period** — close to the 20ms dwell time, meaning an oscillation at this rate could
plausibly dwell long enough each half-cycle to trigger the snap. Grind #2 (40-49Hz, 10.2-12.5ms
half-period) gives the counter roughly half the time it needs. **The original "20-40ms => 25-50Hz, not
7.5Hz" verdict is correct for the ratchet it was checked against, and is NOT evidence against grind #1** —
if anything the timescale match is closer for grind #1 than for anything this file previously compared it to.

**All inputs are torque-margin / motor-rate domain, confirmed AGAIN this session, NO angle term
anywhere** — corroborates and extends this file's own `gp-0x6b64` finding below: `gp-0x6b5e` (read
directly, primary sign/branch selector) = `LERP(gp-0x6bda)*polarity` per
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]]'s sibling constellation entry; `gp-0x6bda`
itself = a peak-hold envelope of driver assist torque; `gp-0x6b96` (feeds the `sVar7=clamp(gp-0x6b96-1024,
0,8192)` MAX-partner term) traced fresh this session to a writer inside `FUN_000352b4` (the magnitude/
peak-hold lane) at `0x3574a` — a rolling-buffer slot copied from `gp-0x37d6`, root signal not chased
further but same torque/peak-hold family by provenance, not independently confirmed. **This directly
answers the team-lead's Lead 2: there is no wheel-angle input anywhere in this function** — "near centre"
in the literal angular sense is NOT what gates it. It may still correlate empirically with near-centre
driving (light hands -> small torque margin -> low motor rate) without reading angle directly.

**Cal handles, fresh byte reads this session, all confirmed virgin (grep on all `build_v*_tva.py` for
`C618A|C627E|C63C0|C64A1|C6132|C62E2|C620C|6b62|6b64|6b5e|36388|6a82|6990`):** only telemetry/probe reads
of the OUTPUT `gp-0x6b62` exist (V69's bit5 CAN cave, fourframe telemetry, retired-probe cleanup lists)
— zero edits to any producer cal. `0xC618A`=1024 (window), `0xC627E`=20 (dwell cap, **the lever**),
`0xC63C0`=33 (gp-0x6990 ramp step, matches this file's original figure exactly, now byte-confirmed
fresh), `0xC64A1`=1 (stock takes the dynamic/ramped branch, not the static one), `0xC6132`=1 (nonzero,
plausibility-gate bypass NOT active), `0xC62E2`=0 (vacuous, reconfirmed).

**Preliminary lever, NOT yet build-ready:** raising `0xC627E` (dwell cap, stock 20 ticks = 20ms) would
require the input to dwell inside the window for LONGER before the snap fires — e.g. doubling to 40
would demand a full grind-#1 PERIOD (not just a half-cycle) of sustained residency, making the relay much
harder for an 18-22Hz signal to trigger, without touching the window width or ceiling value. GATE-1
monitor exposure and headroom NOT checked this session — same open-item class as
[[reference_accord_gp6b26_friction_lane_damping_candidate]] flagged for friction.

**Highest-value next step, unchanged from this file's original recommendation and still not done:**
V69 already flew a `gp-0x6b62 >= 4096` telemetry bit on route `4f` and the raw 0/1 series was never
decoded (only a summary inference). Decoding that existing data is free — no new build or drive needed —
and would directly test whether the snap already fires during real driving before any cal edit is proposed.

## 🛑🛑 2026-08-05 round 2 — DONE: decoded route 4f, and the SIGN is NOT clean (major correction to a team-lead claim), plus an identification caveat on the data itself

**bit5 decoded from `analysis-2020accord/_scratch/data/_cache_r4f_v69.npz`** (47,990 frames, 480s, `fs_lattice`=99.989Hz):
**duty is EXACTLY 0.00000 in every cell** (whole route, engaged, engaged+creep, the ratchet cell,
manual, engaged-not-creep). 95% upper bound on true duty: 0.042% at the tightest (ratchet) cell,
0.006-0.022% elsewhere (Rule-of-Three-style bound from n exposures / 0 hits).

🛑 **BUT this route's byte4 field emits ONLY `0x87` — no rung bit (5, 6, or 4) EVER fires, and per
`probe/decode_v69_ratchet.py`'s OWN embedded logic this payload space is NOT structurally distinguishable
from V66/V67** (both of which independently recorded the identical `{0x87,0xc7}` null over 186,321
frames). **bit6 (r24's lane, the script's own designated "positive control" expected to fire under
V69's 4x dose) is ALSO constant 0 here** — the script's own docstring names this exact combination
("if bit6 ALSO reads 0.000%, the most likely reading is that the cave is not the one you think — the
V64 lesson"). **I cannot confirm from this data alone that V69 (not V66/V67) was actually the image
flashed during this specific captured stretch.** Needs the actual flashed `.rwd` filename for this
route cross-checked, not assumed from the route label.

**Even setting identification aside, bit5's 4096 threshold is 4x the relay's own 1024 ceiling** — a
null here bounds the COMBINED `sVar8+sVar13`, not the relay alone; the relay could snap regularly
without the sum ever clearing 4096 unless `sVar13` is simultaneously large and same-signed. Since
bit5 never toggles, no spectral/toggle-rate test is possible on it at all (confirmed: my 18-22Hz
band-power probe on the bit returns NaN everywhere, as expected for a constant signal) — **the relay
hypothesis remains UNTESTED by this probe, not falsified.**

**Sanity check that this route DOES contain the symptom** (so a null isn't vacuous for the reason
"nothing happened"): the raw `tq`/`rate` channels in this same npz show real 18-22Hz content,
engagement-conditional — prominence ~150-995x engaged vs ~13x manual (band-power vs a 2-45Hz
background floor, longest contiguous run per cell). Consistent with, not new evidence for, the
established engagement-dependence.

### 🛑🛑🛑 RETRACTED IN FULL — see F2's PART 3 at the top of this file. I misread these addresses off by 0x1000.

Everything in this subsection (through "Magnitude sanity check") rests on bytes read at `0xC7xxx`
(e.g. `0xC795E`, `0xC7966`, `0xC7968`, `0xC7970`). **The correct addresses are `0xC6xxx`**
(`tp+0x795e = 0xC695E`, not `0xC795E` — verified `0xBF000+0x795E` by hand and in PowerShell: `C695E`).
F2 read the correct bytes independently and I re-read them myself fresh after team-lead flagged the
discrepancy: **exact bit-for-bit match to F2's table** (`count=5`, `X=[-397,-192,140,294,384]` strictly
increasing, `Y=[0,2560,2560,717,0]` all non-negative). The inner 3-point search is LIVE, not dead code.
There is no brake/pump sign split — every `Y>=0` and one unconditional negation makes this a pure,
unconditional brake, active only for `gp-0x6bda` roughly in `[-397,384]`, zero outside it. **Do not cite
"14", "dead code", "+4164/-8064", or the sign-flip claim below from any future search of this file** —
they are wrong, kept only so the error and its correction are both on record. Original text follows
unedited, for the record:

Team-lead's claim "latched output = ±1024 x sgn(motor rate)" is only half right. Full disasm of
`FUN_000360fe` (`gp-0x6b64`'s producer) at `0x360fe-0x361a0`:
```
00036106: movea 0x795c,tp,r15      ; struct BASE = tp+0x795c (confirms the 5-point-LERP layout)
0003610a: ld.h  0x795e[tp],r16     ; X_lo = tp+0x795e = 14
00036116: cmp   r16,r10 / bgt      ; if gp-0x6bda > 14: search further; ELSE: Y = tp+0x7968 = 4164
00036120: ld.h  0x7966[tp],r13     ; X_hi = tp+0x7966 = 14  <-- BYTE-IDENTICAL to X_lo, re-verified twice
00036124: cmp   r13,r10 / bge      ; if gp-0x6bda >= 14: Y = tp+0x7970 = -8064; ELSE: search (X[1..3])
```
**`X_lo` and `X_hi` are the SAME value (14, confirmed by two independent reads).** Since
`index>14 AND index<14` is impossible, the inner 3-point search (`X[1],X[2],X[3]`) is **structurally
unreachable dead code** — the "5-point LERP" this file and the prior session's memory both called it
**functionally collapses to a 2-VALUE STEP FUNCTION**: `Y = +4164` when `gp-0x6bda <= 14`, else
`Y = -8064`. Then (scale cal `0xC63BE`=1024=Q10-unity, re-verified after catching my own
mid-derivation off-by-0x1000 slip to `0xC73BE` — corrected before use, see the skill file's
recurring trap): `gp-0x6b64 = -clamp(Y * gp-0x6abc, ±0x2800)` (net, after the two `>>10` steps).

**Sign of the latched relay = sign(gp-0x6b64) = -sign(Y)*sign(motor_rate):**
- `gp-0x6bda <= 14` (Y=+4164): relay = **-sign(motor_rate)** — opposes/brakes, as team-lead assumed.
- `gp-0x6bda > 14` (Y=-8064): relay = **+sign(motor_rate)** — REINFORCES, positive feedback.

**14 counts is a tiny threshold for a quantity described elsewhere as a "peak-hold envelope margin
of driver assist torque"** [[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — if
`gp-0x6bda`'s typical operating range at creep is in the hundreds/thousands (consistent with other
torque-domain cals in this firmware), **`gp-0x6bda > 14` — the REINFORCING regime — is plausibly the
COMMON case, not an edge case.** This is NOT independently confirmed this session (I have not probed
`gp-0x6bda`'s typical creep-time value) and is the single most important open item before treating
"bang-bang relay opposing motor rate" as settled — it may just as easily be reinforcing.

### Magnitude sanity check — the relay is NOT swamped, by an exact-arithmetic argument already on file

`gp-0x6b62`'s recorded max is **5786**. This session's own prior citation: `|gp-0x6b5e| <= 4762`
(trapezoid `0xC66CC`) `+` the relay's own `|sVar8| <= 1024` ceiling `= 5786` — an EXACT match to the
recorded max. Both terms were at/near their own ceiling simultaneously in at least the recorded
instance that produced that max — the relay's full 1024 contribution is embedded in it, not swamped.
This doesn't establish the TYPICAL creep-time split (needs live `sVar8`/`sVar13` telemetry, not
available), only that the mechanism has demonstrably reached its own ceiling in recorded operation.

### `0xC618A` reader adjudication — team-lead's raw scan hits are ALL false positives [EVIDENCE, `get_assembly_context` on each]

6 additional candidate hits beyond `FUN_00036388`'s own two: `0x51c2c`, `0x7e812`, `0x7e828` (claimed
even-form `tp+0x718a`) and `0x36470`, `0x3780a`, `0x416c2`, `0x66a38` (claimed odd-form `tp+0x718b`).
**Every one adjudicated as NOT a genuine access**: `0x36470` has **no instruction at that address at
all** (it's the tail 2 bytes of the already-known `0x3646e: ld.hu 0x718a[tp],r9`, a mid-instruction
byte-scan artifact). The other five all decode to `subr r10/r11,r14/ep` — register-register ALU ops
with no `tp` operand whatsoever, in unrelated contexts (a divide-by-1000 helper, LERP array indexing,
an ABS() idiom on unrelated variables, a bitfield table lookup, an angle mod-4096 wrap correction) —
**none reference `tp+0x718a`/`0x718b` in any form.** `0xC618A`'s genuine reader set is exactly the two
instructions inside `FUN_00036388` (`0x36442`, `0x364a0`) — **blast-radius zero, same as `0xC627E`.**

## Related
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — source of `gp-0x6bda`'s "margin
to peak-hold envelope of driver assist torque" identity, now load-bearing for the sign-regime question.

---

**Session: 2026-08-04, ratchet-trace teammate, task "trace the 7.5 Hz ratchet loop inside the EPS."**

## FUN_00036388 (0x36388-0x365ce) fully traced [EVIDENCE, decompile + disassembly, code.bin stock]

Writes `gp-0x6b62` (return-to-centre lane, one of the aggregator's 8 ZERO-type range-gated lanes,
`+/-0x2000`). Called only from `FUN_0002214a` (task 1, 1 kHz), state-gated on mask `0x830` = states
`{4,5,11}` -- **same mask as the oscillation detector `FUN_000428d4`, and excludes state 10** (confirmed
against `docs/STATE.md` section 6's table, exact match, no new finding there).

**Two internal counters, both bounded and asymmetric -- NEITHER is a free-running relaxation
oscillator on its own arithmetic:**

1. `gp-0x6a82` (0x36432-0x36472): `+1/tick` if `abs(gp-0x6b64) < CAL_718A` (`tp+0x718a` = `0xC618A`,
   read = **1024**) unless already `> CAL_727E` (`tp+0x727e` = `0xC627E`, read = **20**, the ceiling);
   `-1/tick` otherwise, floored at 0. Full 0->20 sweep = 20 ticks = 20 ms; a bounce would give ~25-50 Hz,
   not 7.5 Hz, and it only bounces if `gp-0x6b64` itself crosses 1024 periodically -- it does not create
   that crossing.
2. `gp-0x6990` (0x363e8-0x3641c): steps by `+/-CAL_73C0` (`tp+0x73c0` = `0xC63C0`, read = **33**) per
   tick, clamped `[0, 0x7fff]`, gated on whether `gp-0x6bda` (the driver-torque peak-hold margin) rose
   since last tick (compared against its own 1-tick-delayed shadow `gp-0x37b0`) AND `CAL_7132`
   (`tp+0x7132` = `0xC6132`, read = **1**, nonzero so this gate passes). Full-scale sweep is ~993 ticks
   (~1 s) -- far too slow for 7.5 Hz unless only a small fraction of its range is exercised each
   half-cycle, which is undetermined without live RAM.

`gp-0x6b64`'s sole writer is `FUN_000360fe` (0x360fe-0x361be) [EVIDENCE, `search_instructions`
`-0x6b64` = exactly 2 hits image-wide, one write one read, cross-checked against the known undercount
trap]: a 5-point LERP over `gp-0x6bda` (table `tp+0x795e..0x7970`) multiplied by `gp-0x6abc` (>>10,
Q10) then by `CAL_73BE` (`tp+0x73be` = `0xC63BE`, read = **1024 = Q10 unity**), negated, clamped
`+/-0x2800`. `gp-0x6abc`'s only writers are inside `FUN_00041464` (the already-memoried "sign-filter
phase" function, `fs_eff` 312.5 Hz) -- part of the same motor/resolver-rate-derivative chain as
`gp-0x6abe`/`gp-0x6ac0` (the "common-mode rate bus", net -40.4 deg phase vs velocity per existing
memory). **`gp-0x6b64` therefore has NO direct vehicle-speed or torque-sensor term** -- confirmed
independently by `docs/STATE.md` line ~1969: *"`FUN_00036388` (`gp-0x6b62`) read[s] no torque signal at
all -- speed- and motor-rate-keyed only"* (this session's own trace and that pre-existing note agree,
two independent methods).

**Conclusion:** `FUN_00036388`'s own counters cannot be shown to generate a 7.5 Hz (133 ms) period from
their own step sizes/bounds -- the candidate period computed directly (20-40 ms or ~1 s) does not match.
Its gate variable `gp-0x6b64` is a PRODUCT of a torque-margin LERP and a motor-rate derivative, so if
either upstream signal already carries 7.5 Hz content, `FUN_00036388` would inherit/shape it (as a
nonlinear follower with hysteresis and ZERO-gating -- exactly the kind of hard nonlinearity a
describing-function argument implicates) rather than create it from nothing. **Open, not ruled out.**

## V69's bit5 ALREADY probed gp-0x6b62 on-car -- inconclusive, not falsified [EVIDENCE, build script + flight handoff]

`analysis-2020accord/builds/v50_v79/build_v69_tva.py` (~line 198-411) built a CAN 0x14A telemetry cave with
`bit5 = gp-0x6b62 >= +4096`, explicitly labelled *"the operator's own hypothesis, never probed in 69
builds."* Flown on route `4f` (`docs/handoffs/2026-08/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md` section 5.2).
Result: **"bit5 was insensitive, not vacuous"** -- `gp-0x6b62`'s reachable max is 5786
(`|gp-0x6b5e| <= 4762` from trapezoid `0xC66CC`, plus a latched `|sVar8| <= 1024`), so the 4096 threshold
sat at 71% of full range, seeing only the top 29%. **The record does NOT report an explicit observed
hit-rate/count for bit5** (unlike bit6, which got an explicit "observed 0, p=0.37"). The section header
is "ALL THREE RUNGS FAILED", implying bit5 also produced no usable signal, but this is inferred, not
quoted verbatim -- **the actual bit5 time series from route 4f's decoded probe has not been surfaced in
the written record I found.** Re-decoding `rlog-tools/probe/decode_v69_ratchet.py`'s route-4f output for
bit5's raw 0/1 series (not just a summary stat) would settle whether `gp-0x6b62` ever fired at all, which
is the single fastest way to move this candidate from OPEN to CONFIRMED or KILLED.

## Other gp-0x6806 consumers enumerated and ruled out [EVIDENCE, decompile of each]

19 access sites total (`search_instructions -0x6806`, cross-checked against the known undercount trap --
count not independently byte-scanned this session, flag if load-bearing later). 8 writers all inside
`FUN_00028ea6` (arbitration, the flag's producer). External readers, all checked:
- `FUN_0002eda8` -- already CLOSED per existing memory (lane-9 raw torque command path).
- `FUN_0002fab6` -- a huge steering-angle/yaw plausibility MONITOR with parallel 1000 ms-tick debounce
  state machines timing out at 11000 ms (11 s). Reads `gp-0x6806` once, to detect an engagement
  transition edge and reset rolling history buffers. Debounce timescale (1-11 s) is two orders of
  magnitude too slow for 7.5 Hz. RULED OUT.
- `FUN_00030c26` -- a large vehicle-dynamics/wheel estimator, called only from `FUN_0002351e` = **task 6,
  10 Hz** (per the golden model's rate table). Nyquist for a 10 Hz task is 5 Hz; it structurally CANNOT
  carry a clean 7.5 Hz component. RULED OUT by task rate alone.
- `FUN_00042746` -- sensor-fault failover reselector (per existing model comment); static reselection,
  not periodic. RULED OUT.
- `FUN_0004fbde` -- a freeze-frame/diagnostic snapshot logger (16-entry circular buffers), event-driven
  on a multi-flag AND-gate, not a periodic timer. RULED OUT.
- `FUN_00055c42` -- pure CAN 399 TX bit-packer (packs `gp-0x6806` into byte4 bit3, per the existing
  `can_tx_399_427_bitmap` memory); no dynamics. RULED OUT.

## FUN_00045608 (authority-slot setter) is NOT itself dynamic [EVIDENCE, decompile + 16 callers]

Trivial: `if (slot&0xff) < 7: write 3 params into 3 parallel 7-slot arrays at gp-0x652c/-0x64fc/-0x6514`.
No timer, no accumulator. 16 callers spanning many unrelated state-machine handlers (including the
oscillation detector `FUN_000428d4` itself as one caller) -- a shared generic utility, not a dedicated
"authority ramp." RULED OUT as a standalone oscillator source; the real ramp/period logic (if any) lives
in whichever caller drives repeated re-arming, not traced this session.

See [[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]] for the motor-rate-derivative
chain `gp-0x6b64` draws on, and [[reference_accord_r26_is_structurally_inert]] for `gp-0x6b5e`'s
trapezoid (the same LERP `gp-0x6b62`'s ceiling is built from).
