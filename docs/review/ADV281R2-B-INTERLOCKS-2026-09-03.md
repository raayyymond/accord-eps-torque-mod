# Adversary B — interlocks, downstream consumers, closed-loop behaviour — V281 rev 2

**Subagent `adv281b` (firmware-codepath-tracer role), 2026-09-03.** Job: make V281 rev 2 FAIL on
interlocks, downstream consumers, or closed-loop behaviour. Independent of the builder's own assertions
and of the sizing doc's own printed numbers — every number below is re-derived from the images or the
disassembly, not copied.

**What a FAIL would look like (written before the analysis, per the adversarial-pass contract):**
1. A downstream interlock (corridor/lockstep, soft-EME bound, DTC/plausibility, governor) becomes
   reachable at Kp 341 that was not reachable at the as-is Kp — evidence: a threshold crossed by E, P,
   or the aggregate command that was previously below it.
2. A stratum (highway, creep, or the loaded high-angle regime itself under a second plant fit) shows
   WORSE margin (lower GM/PM, or a new resonance near 15-20 Hz) at Kp 341 than at the as-is Kp.
3. The r31 stall-stutter mechanism (P desaturating out of its rail on a stalled/loaded wheel — the kit's
   own established cause of the 7 Hz ripple) is measurably WORSENED, not just traded, by the edit.
4. The build carries an undisclosed change: a byte outside the Kp bank, a CRC that doesn't verify, or an
   .rwd that doesn't decode back to the reported image.

**Verdict: PASS to flash, with one finding the pre-registered drive must take seriously (§3).** No new
interlock is reachable (§1), no stability margin gets worse anywhere I could test it (§2), the build is
byte-clean (§4) — but the P-desaturation risk the operator's own pre-registration already flagged is
real, is narrower and higher (idx 80–111, not 40–80) than the PREREG's estimate, and the sizing doc's own
open-loop replay of the recorded episodes does NOT confirm the ripple falls at flat 341 — only the linear
closed-loop model does. This is not disqualifying (the pre-registration's on-the-wire decision rule is
built to catch exactly this), but the team should not treat V281 as a foregone win before that drive.

---

## §1 — Downstream consumers of E, P, gp-0x6b38/gp-0x6b3c: interlock census

**Method:** decompiled `FUN_00028ea6` (the rate-PID, GhidraMCP, decompile-first) to identify every clamp
and every persistent gp-cell write; decompiled `FUN_0002b422` (limit-and-pack, the function that consumes
`gp-0x6b3c`); read the full downstream delivery chain from `memory/reference/firmware/reference_accord_lkas_delivery_and_governor.md`
(xref-verified record, re-confirmed against the current images below); read the corridor/lockstep and
soft-EME bound-arm-gating records; positive-controlled every `search_instructions` scan against the two
functions' own known writers before trusting a zero.

**The chain, re-confirmed byte-for-byte on both images (Python, both base and V281r2):**

```
FUN_00028ea6 (rate PID):
  E = 32*sp(idx) - fb                         fb = clamp(feedback lag filter, ±0xC62E6=46080)
  P = clamp(E*Kp(idx)>>8, ±0xC61BC=15360)      <- Kp bank 0xCB994, THE edited table
  D = clamp(dE*Kd(idx)>>3, ±0xC61B6=10240)     Kd bank 0xCB7D4, UNCHANGED (128 flat)
  I = 0 (Ki 0xC63E6=0, inert both builds)
  sum = clamp((I>>7)+P+D, ±0xC61BE=15360) -> lag(0xC63EC/EE) -> ×polarity×GAIN(0xC6CD0=5346)>>15
      -> clamp ±0xC61B4=3072 -> gp-0x6b38 -> gp-0x6b3c (0xFEDF14C4)
 -> FUN_0002b422 limit_and_pack: clamp ±0xC61B2=3072 -> gp-0x6b3a
 -> distribute_clamp FUN_00025c32: clamp ±0x2800=10240            (inert: 3072 << 10240)
 -> mixer FUN_00026c80 -> gp-0x6b4c: clamp ±0x2800=10240           (inert)
 -> aggregator FUN_0003aa2c -> gp-0x6b94: clamp ±0x2800=10240      (inert)
 -> GOVERNOR FUN_0004503c -> gp-0x6ace: clamp ±gp-0x4f64 (typ. ~4762, MIN of nominal/adaptive/budget)
 -> FUN_000456a4 -> gp-0x6acc (governor-again + soft-EME bound-arm shaper input)
 -> shaper FUN_00042af8 -> gp-0x6b98: governor again + static ±0x2000=8192
 -> FOC / CAN packer
```

Every downstream clamp (10240, ~4762, 8192) is well above the LKAS lane's own ceiling (3072). **V281
does not raise that ceiling** — Kp reduction lowers the *slope* (how much P a given tracking error E
produces) in the low-to-mid demand range, it does not raise the maximum T the lane can ever deliver (T
still saturates at 3072 given a large enough E; my §3 numbers show it still gets there). So no downstream
clamp, and no aggregate-command threshold gated on the LKAS lane's contribution, becomes newly reachable.

**Corridor / int-float lockstep (`gp-0x6af6`/`gp-0x6b00` vs float twins, hard-shutdown DTC `0xF00049`,**
`memory/reference/firmware/reference_accord_corridor_lockstep.md`**):** this monitor compares
`max(driver-torque IIR, corridor floor, boost)` computed twice (int cal `0xC674E`/`0xC6750`/... and a
float mirror in `FUN_00043e44`) — **it does not read `gp-0x6b38`, `gp-0x6b3c`, E, or P at all.** None of
its cal cells (`0xC674E`, `0xC6598`, `0xC6664`, `0xC6760`, ...) are in V281's changed set (confirmed: not
in the build's `FROZEN` dict, and the code region `0x13000–0xC0000` is byte-identical between the two
images — independently re-diffed, §4). **Not reachable by this edit.**

**Soft-EME bound-arm integrator (`gp-0x3570`, winds up on `command − bound`,**
`memory/reference/firmware/reference_accord_soft_eme_bound_arm_gating.md`**):** "command" here is the
post-governor, post-mixer aggregate (`gp-0x6acc`/`gp-0x6afe`), several summing stages downstream of
`gp-0x6b3c`, with a residual margin of ~512 counts against a bound floored at 4096 when boost is armed.
The LKAS lane's own ceiling (3072) hasn't moved, so this integrator's worst-case wind-up input is
unchanged. If anything, a slower-rising P at low-to-mid demand (V281's own stated cost) reaches any given
command level *more slowly*, which is gentler on an integrator that trips on *exceeding* a bound, not
more aggressive.

**Gentle-EME (`STEER_STATUS=4`, debounce SM, `gp-0x682f`/`gp-0x6757`, `memory/misc/gentle-eme-fires-on-saturated-lkas-command.md`):**
already corrected in the kit's own record — driven by **driver column torque (sensor B) and angle-rate**,
not by the LKAS setpoint or this loop's E/P. "The LKAS setpoint magnitude cannot trigger the gentle EME
at all" (EVIDENCE, that memory's 2026-07-18 update). Unaffected by construction.

**The per-mode fault/DTC counter at the tail of both `FUN_00028ea6` and `FUN_0002b422`** (a per-state-index
counter incrementing on every call, calling `FUN_0001cba6` → `FUN_00016de6(0x18,...)` — a DTC setter — when
a per-mode "N cycles in this state" count hits a threshold `param_1` AND a per-mode enable flag is set):
this is driven by a **mode/dwell-time state machine** (`gp-0x3d28` → `gp-0x67a4`, override-taper mode
gating), not directly by the magnitude of E or P as far as I traced its inputs (`gp-0x67a1`/`a3`/`a7`,
themselves override/direction flags). **I did not fully trace every input to that state machine to its
root cause** — this is the one corner of the census I could not close with full confidence; I did not
find a path from E/P magnitude into it, but I did not exhaustively rule one out either. Flagging as the
residual open item, not as a finding of risk.

**Persistent internal state cells checked for external readers** (positive-controlled: `search_instructions`
correctly found the known writers in both `FUN_00028ea6` and its dead twin `FUN_0002a93a` before I trusted
a zero elsewhere):
- `gp-0x6a32` (sp, the LKAS setpoint after the per-idx map LERP): **2 writers, 0 other readers.**
- `gp-0x6b30` (lag-filtered, pre-gain rate-loop output): **1 writer + 1 in-function reader, 0 external readers.**

Neither is read by any plausibility/"not tracking" check outside this function pair. **No evidence of a
tracking-error-magnitude interlock anywhere in the census.**

## §2 — Stability the other direction

Independently re-derived (own script, `L_in = C_ctrl(idx,f)·H_fb(f)·8·z⁻¹·G(f)`, reusing the kit's
already-validated `lowcmd_loopgain_v112_v278_v280.py` mirror — not re-typing the arithmetic — pointed at
the real images) using the sizing doc's plant fit 1 (loaded high-angle, pole+delay from the driver-torque
IV estimator: K 0.382, pole 0.80 Hz, delay 8.4 ms):

| idx | Kp base→V281 | base PM / GM | V281 PM / GM |
|---|---|---|---|
| 12 | 295→294 (unchanged, idx≤24) | 18.6° / 1.65× | 18.6° / 1.65× |
| 26 | 349→341 | 10.1° / 1.32× | 11.2° / 1.37× |
| 58 | 473→341 | −5.2° / 0.86× | 11.2° / 1.37× |
| 68 | 512→341 | −9.2° / 0.77× | 11.2° / 1.37× |
| 112 | 645→341 | −20.8° / 0.56× | 11.2° / 1.37× |
| 136–173 | 696→341 | −24.7° / 0.50× | 11.2° / 1.37× |

**At every idx tested, V281's margin is equal to or better than base's — never worse.** This corroborates
the sizing doc's headline numbers (PM 11°, GM 1.36×) independently, on the real built image, not the
sizing doc's synthetic override. I also checked whether D becoming relatively more dominant (P shrinks,
Kd doesn't) pushes a new mode toward 15–20 Hz: the P-fraction of |P+D| at idx 58/112 falls from ~0.66–0.97
(base) to ~0.54–0.91 (V281) across 6–20 Hz — D genuinely is relatively more dominant post-edit — but the
closed-loop margin computation above already includes D, and margin still improves, not worsens, at
every idx tested **on this one plant model.**

**What I could NOT independently check:** the highway (≥20 m/s, |angle|<8°) and creep (1–3 m/s) strata
need their own plant fits, which I don't have in front of me — the sizing doc's own claim there ("PM
52–59° at 13 Hz for every Kp in 248–349, nothing at risk") is BELIEF-grade and I have not re-derived it.
**What I CAN say with evidence:** the highway/lane-change regime runs at idx 2–12, and I independently
confirmed (own script, every integer idx 0–24) that **Kp is byte-identical between base and V281 at
every one of those idx values** — the controller gain in that regime does not change at all, so there is
no mechanism by which this edit could newly destabilize it, independent of any plant assumption. Creep
remains a genuine gap; I'd flag it to whichever subagent (`creep20`?) has a validated low-speed plant.

## §3 — Authority / the r31 stall class — the one finding worth flagging hard

Re-derived directly from both images (not the sizing doc's printed table), two ways:

**(a) Reference-scale stall (rate=0, i.e. the wheel doesn't move at all):** P is pinned (railed) at
idx≥59.6 under base, idx≥83.7 under V281 (continuous search, 0.001-idx resolution) — closely matching
the sizing doc's "idx≈58 / idx≈80", independently confirmed.

**(b) A wheel STUCK at 15 deg/s (not zero — the literal case named in my brief, and the more realistic
r31-class stall) against whatever idx is commanded:** P pins at idx≥**79.2** under base, idx≥**110.7**
under V281. So the window **idx 80–111** is where base's P is RAILED (saturated, sitting at the 15360
ceiling) but V281's P is back in its LINEAR window (tracking the oscillating error faithfully).

**Why this matters more than a plain authority-cost number:** the kit's own established mechanism for
this exact 7 Hz ripple (`memory/accord/mechanism/accord-v278r3-high-angle-stutter-is-p-desaturating-on-a-stalled-wheel.md`,
EVIDENCE grade, open-loop sim on measured V278r3 rate) is that **the ripple gets through precisely when P
is NOT railed** — "the ±25 deg/s 7 Hz rate ripple (±6000 in E) crosses P's linear window every cycle →
T 100% modulated," and conversely "a ×6 top... pins P: open-loop ripple/level 0.45 → 0.18." V280's own
fix worked by RAISING authority so P stays pinned more of the time. **V281's fix works by LOWERING Kp so
the loop's linear gain drops below the crossover instability threshold — the opposite lever, applied at
the SAME physical point (whether P is railed).** These are not contradictory in describing-function
theory (K_eff = N·Kp, and both a higher E-excursion and a lower Kp push K_eff down) — but they act on the
observable "is P railed" in OPPOSITE directions, and the idx 80–111 window is exactly where that
reversal is concentrated for a realistic (15 deg/s, not zero) stall.

**The sizing doc's own Section 3 (describing function on the real F7 episode frames, not a model) does
NOT unambiguously confirm the ripple falls at flat 341** — its own table shows the *open-loop* ripple/level
ratio at F341 (e.g. 0.58 on the r32 620.7 episode) HIGHER than at the as-is Kp (0.44), and the doc's own
resolution of this ("a lower Kp cuts the push faster than the ripple, so the ratio rising is expected;
the closed-loop margin table, not this open-loop replay, is the one that says the cycle dies") is
correctly graded BELIEF in the doc's own §6, not EVIDENCE, and rests on the closed loop actually
re-equilibrating rather than continuing to ring at a lower amplitude — the doc itself calls the 16% gap
between K_eff (394–575) and 341 "thin." **This is a real, disclosed tension, not a hidden one — but it
means the pre-registered drive is not a formality; it is where this decision actually gets made.**

**This is not a FAIL condition** — it is exactly what `rlog-tools/studies/osc-highangle/PREREG-V281-READ.md`
already pre-registered a decision rule for (episodes/100s ≤2, ripple/level ≤0.25, rate p50 ≥105 deg/s,
and named "stalled-wheel class... may return at idx 40–80 — count them; ≥3 per route is the cost
signal"). My contribution: **the desaturation window is idx 80–111, not the PREREG's blanket 40–80** —
tighter and shifted higher — so if the stall-stutter signature reappears, look there first.

## §4 — Independent build-integrity verification

- Both image hashes independently re-confirmed: base `b1f19d3e...`, V281r2 `4c437e3b...` (match the
  brief).
- **Every cal cell outside the Kp bank independently re-read from both images and confirmed identical**
  (Kd bank, map, all 5 clamps, Ki, the feedback-lag coefficients, the output-lag coefficients, the GAIN
  cell — 17 distinct cells, byte-read directly, not trusting the build script's own assertions).
- **Full byte diff, 0x13000–0x100000, independently re-run:** 316 differing bytes total. **0** in the
  code region (0x13000–0xC0000). **0** unattributed payload bytes (every payload diff falls inside a Kp
  LERP record span). 20 CRC-trailer bytes (5 blocks — matches 5 distinct Kp record shapes touched).
  **0 unexplained bytes anywhere.**
- **CRC re-verified independently** using the kit's own `verify_bootloader_crc.walk_all_blocks` /
  `.walk` (the real, non-4KB-uniform block map — my first naive 4KB-aligned attempt was wrong framing
  and is not a finding) against both images: **50/50 and 49/49 PASS on both.**
- The Kp table actually baked into the V281r2 image, read straight from the file: slot 7 (live) X =
  `(0, 24, 68, 136, 208)`, Y = `(248, 341, 341, 341, 341)` — matches the build script's stated target
  exactly.

**Nothing else changed. No undisclosed edit.**

---

## Verdict

**PASS — clear to flash on the interlocks/downstream/build-integrity axes.** No corridor-lockstep,
soft-EME, gentle-EME, DTC-counter, or downstream-clamp interlock becomes newly reachable; every
stability margin I could test (loaded high-angle plant, idx 12–173) is equal or better under V281;
highway/lane-change is untouched by construction (Kp byte-identical at idx≤24, independently confirmed);
the build is byte-clean and CRC-verified two ways.

**One finding for the record, not a blocker:** the P-desaturation risk in the idx 80–111 window (§3) is
real, is the SAME mechanism the kit's own memory names as the cause of this exact ripple, and the sizing
doc's own open-loop replay of real episode data doesn't unambiguously support the "ripple falls" claim —
only the linear closed-loop model does, on a thin (16%) margin. The pre-registered drive's decision rule
is correctly designed to catch this; it should be read as a live test, not a confirmation drive.

**Creep-regime stability (1–3 m/s) is an open item** — I don't have a validated plant fit for it and did
not find one in the kit's current record; flag to whoever owns the stratified plant ID.
