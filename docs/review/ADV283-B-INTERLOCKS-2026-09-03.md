# Adversary B — interlocks, windup, EME dwell — V283 (Ki 0→50)

**Subagent `adv283b` (firmware-codepath-tracer role), 2026-09-03.** Job: make V283 FAIL on interlocks,
windup, and driver safety, specifically on **DWELL** (not peak) mechanisms — the two prior adversarial
passes (`ADV281R2-B`, `ADV281R3-B`) covered peak-based clamp reachability only.

**What a FAIL would look like (written before analysis):** a downstream dwell/duty-based trip (soft-EME
bound-arm integrator, a DTC dwell counter, a lockstep debounce accumulator) becomes reachable from a
sustained (not momentary) LKAS output; the accumulator fails to clear on disengage in a way that lets a
stale integral value re-arm on re-engage; a driver's hand on the wheel fails to stop the integrator from
winding; a standstill hold winds the accumulator to a value that produces a dangerous release lurch;
7 Hz/20 Hz margins move by more than triviial amounts; the build carries an undisclosed byte.

**Verdict: PASS to flash, with two disclosed residuals neither of which is a FAIL by the letter of the
pre-registration, but both of which the operator should read before driving.** Build integrity is
clean (re-run independently, 329/329 assertions, image hash reproduces exactly). No downstream PEAK
clamp becomes newly reachable. But (1) the reset-on-disengage is **not instantaneous** — it lags
disengage by roughly 0.1–1.0 s while the LKAS engagement ramp decays to zero, and (2) the integrator is
**structurally immune to a driver's hand** — the fade multiplier scales only P+D, never the error the
integrator sees — so a held hand does not stop the wind-up, and I quantified exactly how much torque
that produces against a resisting hand.

---

## §0 — Build integrity, re-derived independently

- V283 image on disk (`_v283_V283-V282BASE-KI50…_plain_image.bin`) hashes to
  `fd0c321abbf933c0d846a8eaf48b594f44f5a9bd491e4396b44abc562551ef3d` — matches the brief.
- **Independently re-ran `build_v283_tva.py` fresh** (not trusting its own printed log): **329/329
  assertions pass**, image sha256 reproduces exactly, `.rwd` sha256 `6bd088f5e7337ae2ac4be3c65d14c58b1feaa64b247f62b6d507297488e7c85d`.
  Census: 274 substantive, 29 vacuous (entailed by the base hash), 26 tautological.
- **Full byte diff V282→V283, independently computed:** exactly 5 bytes — `0xC63E6` (the Ki low byte,
  0→50) plus 4 CRC-trailer bytes at `0xC6FFC`. Nothing else moved.
- Cal cells re-read directly from the image: `0xC63E6`=50, `0xC61BA`(I clamp)=10240, `0xC62E4`
  (deadband)=4, `0xC61BE`(sum clamp)=15360, `0xC61B4`(output cap)=3072, `0xC6CD0`(GAIN)=5346 — all match
  the build script's own FROZEN assertions, confirmed from bytes not from the script's printout.

## §1 — The arithmetic, re-confirmed by direct disassembly (not taken from the build script)

Disassembled `FUN_00028ea6` myself (GhidraMCP, `code.bin`, decompile-first then assembly):

```
0x29d76  shl 0x5,r16 ; sub r26,r16          E = 32*sp - fb
0x29d7c-9a           excess = deadband(E>>5, cal 0xC62E4=4)
0x29d9c  ld.hu 0x73e6,tp,r6                 Ki  = cal(0xC63E6)     tp=0xBF000, 0xBF000+0x73E6=0xC63E6
0x29da0  ld.hu 0x71ba,tp,r13                bound = cal(0xC61BA)
0x29da4  ld.w  -0x6dd0,gp,r10               acc_old = gp-0x6dd0
0x29da8  mul   r6,r9,r0                     prod = excess*Ki
0x29dac-c2           acc_new = clamp((acc_old>>3)+(prod>>3), +-(bound<<10>>3))
0x29de4  shl 0x3,r24 ; 0x2a190 st.w r24,-0x6dd0,gp   gp-0x6dd0 = acc_new<<3 (UNCONDITIONAL store)
0x29f18  sar 0x7,r2                         I_term = acc_new>>7   -> |I_term| <= 10240
0x29f1e/24 add r9,r2 ; add r8,r2            sum = clamp(I_term+P+D, +-15360)
```

Matches the build script's own derivation exactly; independently re-derived, not copied.

**`gp-0x6dd0` (the accumulator) has exactly TWO xrefs in the whole program** (`search_instructions`,
positive-controlled against the known live function): the read at `0x29da4` and the unconditional store
at `0x2a190`, both inside `FUN_00028ea6`. Its dead twin `FUN_0002a93a` carries a structurally identical
pair (`0x2ac96`/`0x2b05c`) but is not called from any live path. **No other function anywhere touches
this cell** — there is no separate "on-disengage, clear controller state" routine.

## §2 — The reset condition is NOT what the build script's docstring says (correction)

The build script states: *"0x2A164 -- `mov 0x0,r24` on the not-engaged/not-valid clear path (also zeros
r29,r27,r22,r16,r12) -- the normal disengage/reset arm."* **True as far as it goes, but the actual gate
is more specific and has a real consequence for driver-override behaviour.**

Traced the reset's guarding condition by matching the decompiled if/else to its compiled branches
(disassembly, `get_xrefs_to 0x2a164` → two unconditional jumps, both from `0x29a5c`/`0x29a64`) and
walking the source of each register the branch tests back to its own assignment:

```c
if ( ((uVar18 != 0) || (cVar15 == 1)) && bVar3 ) {
    /* ... normal PID computation, incl. the accumulator update at 0x29da4-0x2a190 ... */
} else {
    iVar34 = 0;   /* the reset, at 0x2a164 */
    ...
}
```
where **`uVar18 = *(gp-0x69b0)`** — traced (55 xrefs, all inside `FUN_00028ea6`) to a **ramp state
machine that increments while engaging and decrements to exactly zero while disengaging**, at rates set
by cals `0xC63F4`=328, `0xC63F8`=33, `0xC63FA`=66, `0xC63FC`=328 counts/tick from a ceiling of `0x8000`
(32768). The terminal state (`LAB_0002971a`, reached when the ramp has decayed below its own step or the
state machine idles) does `gp-0x69b0=0; gp-0x6806=0` (STEER_CONTROL_ACTIVE) together — i.e. **this is the
engagement ramp**, and `bVar3` traces to the SAME early plausibility gate (driver-torque/feedback/polarity
range check) that ALSO sets `bVar3=false` on implausible sensor values.

**Consequence: the reset is gated on the engagement ramp reaching zero, not on the instant
STEER_CONTROL_ACTIVE goes false.** `FUN_0002214a`'s state mask that gates `FUN_00028ea6` is confirmed
(this session's memory: `reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz`) to be
an ECU-state gate, not a phase divider — the whole chain runs at a uniform ~1 kHz. At the ramp's SLOWEST
observed step (33/tick), a full decay from ceiling takes **~993 ms**; at the fastest (328/tick), **~100
ms**. **So there is a genuine ~0.1–1.0 s window after disengage during which the integrator is still
live and NOT cleared** — the build script's one-line "the normal disengage/reset arm" is directionally
right but omits this lag. [EVIDENCE — traced from the disassembly and the ramp's own step cals, this
session; the exact ramp state the car is normally in at disengage, and hence which step size applies,
is **not** re-derived here — flagging as the open item, not a closed number.]

**EPS-side steering-pressed cutout:** the debounce cals `0xC64B4`–`0xC64B8` read **255/255/255/255/255**
(0xFFFF as a u16) on the V283 image — confirmed disarmed, matching the brief's premise. **The only
override mechanism live on this image is the multiplicative fade** (`0xCBC34`/`0xCBBC4`, the
`postA`/`postB` tables), which — per the arithmetic re-confirmed from `twist_taper_loop.py`'s own
decompile-derived formula (`S = m*(P+D)/256 + I`, `m` from `((A*B)&0xFFFF)>>8`) — **scales only P and D,
never the accumulator or its input `E`.** The integrator is structurally blind to the fade. Quantified
in §4.

## §3 — Standstill windup: the number the orchestrator asked for

Simulated (own script, `_scratch/v283_adv_sizing.py`, constants and tables read directly from the V283
image — Kp flat 248, Kd 128, fb clamp 46080, GAIN 5346, OA/OB 992/507, the fade tables at `0xCBC34`
X=[0,3,6,8,10,20] Y=[255,255,255,255,255,205] and `0xCBBC4` X=[16,26,38,48,64,96]
Y=[255,243,218,179,77,77]) a **rate=0 hold (v=0, wheel free, hands-off)** at several demand indices:

| idx | reference (deg/s) | time to 99% I-rail (±10240) |
|---|---|---|
| 26 | 14.5 | **1.93 s** |
| 58 | 32.3 | **0.85 s** |
| 84 | 46.8 | **0.58 s** |
| 120 | 66.8 | **0.41 s** |

**The accumulator rails to its full ±10240 anti-windup bound in well under 2 seconds for any realistic
held/stalled demand — faster than the brief's assumed 2–5 s window, and faster the higher the demand.**
Once railed, delivered torque `T` converges to a **structural ceiling of ~2481–2506 counts**
(`SUM_CLAMP(15360) × GAIN(5346)/32768 ≈ 2506`, independent of Ki once the sum is dominated by I) —
**well below the nominal 3072 output cap, which is structurally unreachable by this lane under normal
sum-clamped operation** (`15360×5346/32768 < 3072` always). [EVIDENCE — re-derived from the exact
arithmetic and the built image's own cal values.]

**Move-off after a 10 s standstill hold** (idx 58, then the wheel is released to a free-wheel plant,
load 300 ct): with Ki=50, the accumulator is fully railed (10240) at move-off; peak rate **50.8 deg/s
against a 32.3 deg/s reference (+18.5 deg/s overshoot)**, settling to within 2 deg/s of the reference in
**~2.1 s**. With Ki=0 (V282/V281 rev 3 baseline), the wheel instead chronically **undershoots** by
14–18 deg/s and never reaches the reference in the 9 s window modelled (the documented deadband/stall
problem this build exists to fix). **Neither trips the pre-registration's FAIL clauses** (overshoot
>20 deg/s, or lasting >3 s) but the overshoot (18.5 deg/s) sits at 91–93% of the 20 deg/s threshold —
close, not comfortable. [BELIEF for the absolute numbers — same plant-model class the operator's own
pre-registration already accepts (`ki_sizing.py` §C: Coulomb load + first-order plant, K 0.382, pole
0.80 Hz, delay 8.4 ms); EVIDENCE for the PID/accumulator arithmetic and the built cal values driving it.]

⚠ **The r35 23:48:21 incident itself was NOT an engaged standstill** — per `GRIND-INCIDENT-r35-2026-09-03.md`,
the car was DISENGAGED for the whole 1001.6–1014.4 s stop (brake on) and re-engaged exactly as it moved
off. So r35 does not exercise this scenario on V281 rev 3; the number above is a first-principles model
of the case the brief asked about (an engaged standstill), not a measured replay of that specific log.

## §4 — Driver override: quantified against 1500/2500 raw at idx 40–84

Same simulation, driver torque held **steady** (grab-rate term settled to zero, i.e. the fade's `A`
factor at its rest value 255) at 1500 and 2500 raw, `m=185`/`76` respectively (read from the image's own
`postB_m0` table — `torque_byte(1500)=46→B≈186`, `torque_byte(2500)=78→B=77`, both cross-checked against
`ADV281R3-B`'s independently-computed `m=178` at raw 1536, which matches this session's `B(48)=179`
table entry exactly):

| idx | tq raw | m | Ki=0, \|T\|@1s/3s | Ki=50, \|T\|@1s/3s | V280-class hands-off Ki=0 \|T\| (reference) |
|---|---|---|---|---|---|
| 40 | 0 (hands-off) | 254 | 855/855 | 2140/2481 | 855 |
| 40 | 1500 | 186 | 626/626 | 1911/2280 | — |
| 40 | 2500 | 76 | 256/256 | 1540/1910 | — |
| 58 | 0 | 254 | 1238/1238 | 2481/2481 | 1238 |
| 58 | 1500 | 186 | 906/906 | 2481/2481 | — |
| 58 | 2500 | 76 | 370/370 | 2024/2024 | — |
| 84 | 0 | 254 | 1794/1794 | 2481/2481 | 1794 |
| 84 | 1500 | 186 | 1314/1314 | 2481/2481 | — |
| 84 | 2500 | 76 | 537/537 | 2191/2191 | — |

**Reading it:** even under a firm hand (2500 raw, `m=76`, i.e. the fade already cutting authority to
~30% of hands-off), Ki=50 still drives delivered torque to **1540–2191 counts within 1–3 s** — roughly
**4–6× what Ki=0 delivers at the same grip** (256–537). This is the mechanism the brief named:
**the integrator is blind to the driver's hand.** It is not a regression against any FLOWN build's own
authority — every one of these numbers stays below the ~2506 structural ceiling and below every
downstream clamp census'd by `ADV281R2-B`/`ADV281R3-B` (10240, ~4762, 8192) — but it is a **new,
qualitatively different** behaviour: at idx≥58, a driver holding the wheel against LKAS for as little as
~1–2 s now sees the SAME delivered torque (~2481–2500) regardless of how hard they're pushing back,
because the integrator rails to the same structural ceiling independent of the fade multiplier's
instantaneous value. **Release lurch** (hold 2000 raw for 3 s at idx 58/84, then release to a free
wheel): peak overshoot **+18.2 / +14.3 deg/s**, settling to within 2 deg/s of the reference in **~2.0–2.1
s** — under the pre-registration's FAIL thresholds (>20 deg/s or >3 s) but with limited margin on the
overshoot magnitude.

## §5 — Soft-EME bound-arm dwell interlock: the one item I could NOT fully close

Per `reference-accord-soft-eme-bound-arm-gating.md` (2026-06-03, established on a MUCH earlier build):
the bound-arm integrator `gp-0x3570` is a **pure, unattenuated accumulator on `(command − bound)`**,
arming SM2 within ~153 ms of a sustained 100-count excess — genuinely dwell-sensitive, not peak-gated.
`command` there is the **post-governor** aggregate (`gp-0x6acc = governed_LKAS + COMP`), several stages
downstream of this lane's own `gp-0x6b38`/`gp-0x6b3c`.

**I re-read the bound-arm's own cal cells directly from the V283 image (fresh, not from the 2026-06
memory) and found them materially WIDER than that memory's era assumed:**

| cal | stock | **V283 (current)** |
|---|---|---|
| corridor dir1 `0xC674E` | 1024 | **5120** (5×) |
| corridor dir2 `0xC675A` | −1024 | **−5120** (5×) |
| boost Y1 `0xC6768` (int) | 0 | **5120** |
| boost Y2 `0xC676A` (int) | 1536 | **5120** |
| boost Y1/Y2 float `0xC65C8`/`0xC65CC` | 1.5/2.0 | **5.0/5.0** (matched int↔float) |
| COMP ceiling `0xC67DC` | 2560 | 2560 (unchanged) |

The int/float boost pair reads a **matched, FLAT 5120 / 5.0** — i.e. the V31-class boost-floor fix this
kit designed in 2026-06 (there proposed at 4096) **has since been superseded by something even more
generous (5120)**, and the corridor has independently been widened 5×. Since boost is gated only by
authority (not by driver-assist), and authority has been measured near-inert on-car
(`accord-v54-flashed-authority-is-zero-by-design`: ≤119 across 5,989 frames vs a 3,073+ knee), **the
bound floor in the worst-case hands-off/held-wheel scenario is at least 5120** — comfortably above this
lane's own new ~2506 structural ceiling.

**What I did NOT re-verify this session:** the CURRENT (V283-era) value of `COMP` and the governor's own
ceiling (`gp-0x4f64`), and whether `gp-0x6acc = governed_LKAS + COMP` is still the right composition on
this build lineage — that structure is carried from a 2026-06 memory of an EARLIER build, not re-traced
by me here. **If** that composition still holds and COMP still reaches its full 2560 ceiling
simultaneously with this lane's new sustained ~2506, the sum (5066) sits only **54 counts** under the
5120 boost floor — a thin margin, not a violated one. I flag this explicitly as **UNRESOLVED, not
FAILED**: the governor/COMP chain needs a fresh trace against the CURRENT image before this specific
number can be called closed either way. [BELIEF for the composition and margin arithmetic; EVIDENCE for
the individual cal values re-read this session.]

## §6 — 7 Hz / 20 Hz margins

Independently re-ran the build script's own `pid_tf` (`ki_sizing.py`), not trusting its printed numbers:

| f | \|pid(Ki=50)/pid(Ki=0)\| | phase |
|---|---|---|
| 7 Hz | 0.9841 | −1.38° |
| 9 Hz | 0.9870 | −0.88° |
| 20 Hz | 0.9955 | **−0.16°** |

Matches the build script's own claim exactly. **Negligible at both bands** — confirms item (5) of the
brief; no further stability concern found.

## §7 — Summary against the FAIL sentence

1. **Dwell-based downstream trip newly reachable:** structurally, no — this lane's own ceiling (~2506)
   sits under every downstream PEAK clamp censused by the prior passes, and under the current soft-EME
   boost floor (5120) with margin. **One genuinely open item** (§5): the COMP/governor composition that
   would make that margin exactly 54 counts is not re-verified on THIS build lineage — recommend a
   fresh trace before a larger Ki dose.
2. **Reset does not run reliably on disengage:** **partially true, disclosed** — the reset is gated on
   the engagement ramp reaching zero, which lags actual disengage by ~0.1–1.0 s, not on STEER_CONTROL_ACTIVE
   directly. Not a FAIL (the ramp does reliably reach zero and the accumulator does clear), but the
   build script's docstring should be corrected to say so.
3. **Driver override fails to stop the integrator:** **true by design, quantified** — the fade
   multiplier scales only P+D; the accumulator winds identically regardless of hand torque. At 2500 raw
   held, delivered torque still reaches 1540–2191 counts within 1–3 s (vs 256–537 at Ki=0). Not a FAIL
   against any flown build's own peak authority, but a real, disclosed change in how a resisting hand is
   treated.
4. **Standstill windup:** **quantified as requested** — 99% rail in 0.4–1.9 s depending on demand;
   move-off overshoot +18.5 deg/s settling in ~2.1 s, under both FAIL thresholds but with limited margin
   on the overshoot number.
5. **7/20 Hz margins:** negligible, confirmed independently.
6. **Build integrity:** clean, independently re-verified (329/329 assertions, exact hash reproduction,
   5-byte diff from V282).

**No FAIL condition met. PASS to flash**, with the two disclosed residuals above (§2's disengage lag,
§5's unresolved 54-count governor-chain margin) carried into the pre-registered drive's read, and a
recommendation that §5 be closed with a fresh governor/COMP trace before any dose beyond Ki=50 is
considered.
