# GENTLE-EME — FULL CAN→MOTOR GATING MAP (2026-07-06)

> **⚠ CORRECTION 2026-07-14 (see `handoffs/2026-07/HANDOFF-2026-07-14-v36-debounce-sm-root-cause.md`).** The V31P-V2 telemetry
> drive + a Ghidra re-trace (self-verified) supersede the cut model in this doc:
> - **Stage E1 is WRONG:** `gp-0x6809` has **zero writers** (dead code) — it is never the "physical cut," and
>   the deliver-commit→`gp-0x6809` hop this doc flagged as un-byte-traced does not exist.
> - **Stage E2 is right in spirit but is the WHOLE story:** the gentle EME IS produced by the `gp-0x6807`
>   (`STEER_STATUS`) **debounce state machine `FUN_0002a30e`** (+ an inline twin in `m_steer_torque_arbitration`)
>   — `STEER_STATUS=4` after **5 sustained cycles** (cal `0xC64E2`) of `torque gp-0x682f>0xC64B4(112) OR rate
>   param_1>0xC61C0(1600)` (multi-tier, 7 cals). `STEER_STATUS=4` is a lagging REPORT; the actual motor-zeroing
>   instruction is still unlocated.
> - The §5 "rate channel (Gate 5 `gp-0x4f68`)" prime hypothesis was **directionally correct** (rate matters) but
>   located in the wrong function; the real rate gate is `param_1>0xC61C0` inside the debounce SM.
> - **V36 was built** (this doc's §7 said "do not propose a V36 lever yet" — that hold is now released):
>   V31 + raise the 7 debounce-SM torque/rate cals to unsigned max. Cal-only, UNFLASHED.
> The gate-by-gate arithmetic below is still byte-accurate as an inventory; only the *cut-mechanism* framing
> (Stage E) is corrected.

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **Analysis image = STOCK `code.bin`**
(`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0 → file offset == address). **Bases:** `gp (r4) =
0xFEDF8000`, `tp (r5) = 0xBF000`. Tool: radare2 5.5.0 with the **`v850.gnu`** plugin (the default `v850`
mis-decodes V850E2). `af`/`pdf` mis-size functions in this cluster — hand-walked with linear `pd`.

**Why this doc exists.** The gentle EME (LKAS-only torque cut on a hard turn + bump; driver steering retained;
no DTC; CAN `STEER_STATUS = no_torque_alert_2`) **still occurs after V35 was flashed.** V33 disabled the
torque-MAX gate, V34 the angle-consensus gate, V35 the torque-AVG gate — and it survives all three. The lineage
kept finding gates one at a time and being surprised by the next. This map is the **exhaustive** enumeration of
every place LKAS torque can be gated between CAN input and motor output, produced by a 6-agent decompiling swarm
(one agent per pipeline segment), so the still-live trigger falls out by elimination instead of by guess.

**Nothing was flashed, no code was modified, no build was run.** This is a read-only mapping pass on the stock
image. It deliberately does NOT propose a V36 lever — after three confidently-wrong builds, the next step is
*discrimination* (telemetry), not another guess. See §7.

---

## ⚠ CORRECTION (2026-07-06 verification pass) — Gate 5 signal is TORQUE, not velocity

A follow-up byte-verification pass (walking each suspect's disasm directly) **overturns Segment D's identity
for Gate 5.** `gp-0x4f68 = clamp(|gp-0x4f60|, 0, 65535)`, and `gp-0x4f60` is the **column-TORQUE** signal — the
CAN-399 packer `FUN_00055c42 @0x55c50` sends `STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`, i.e. openpilot
reads `gp-0x4f60` as column torque (range ~±100 hands-off … ±3400 grab). So **Gate 5 is `|column torque| ≥
4096`, NOT a rate gate.** Consequence for the ranking below: the logged EME torque peaked ~2340 (and a hard
grab ~3560), **both under 4096**, so Gate 5 did NOT fire during the five logged events (unless a sub-CAN-frame
spike briefly exceeds 4096). This **demotes Gate 5** from "prime" and re-weights the list toward the
**angle** mechanisms (the `FUN_0003c7fc` deadband on `gp-0x6cc4` — the same angle channel V34 attacked but left
a second copy of) and the dispatcher trump. The re-arm rate gate `gp-0x6a60 ≥ 1600` IS a genuine rate gate
(`gp-0x6a60 = |clamp(gp-0x6a56 angle-rate, ±12000)|`, verified) but applies to re-arming, not the initial cut.
See §5 (revised) for the corrected ranking. The gate arithmetic in the tables below is byte-accurate; only
Gate 5's *identity label* (velocity→torque) and its ranking change.

## 0. The one-paragraph answer

The whole V32→V35 lineage neutralized the **column-TORQUE** gates (`gp-0x6a62` MAX, `gp-0x6a5e` AVG, both vs
320) and one **angle-consensus** gate. But the "+bump" trigger lives on the **steering-RATE / angular-velocity
channel**, which is gated in at least three places that **no build has touched**: the deliver-commit **Gate 5**
(`gp-0x4f68 ≥ 4096`, a column angular-velocity magnitude — identity newly solved this session), and the
engage/re-arm refusal gates (`gp-0x6a60 ≥ 1600`, also a rate magnitude; and `gp-0x4f68 ≥ 4096` again). A road
bump spikes steering angular velocity past these thresholds with **zero debounce anywhere in the rising chain**
→ delivery bails *and* re-arm is refused until the rate falls back → "LKAS drops, then re-arms a beat later,"
exactly as reported. A second, structurally-independent suspect is the dispatcher-level **`gp-0x67FE == 2`
trump override**, which discards the decider's verdict entirely and lands the SM in a non-delivering pocket.
**Prime hypothesis: the rate channel (Gate 5).** It is not yet on-car-confirmed, and there is one unclosed
structural link (below), which is why §7 recommends a telemetry drive before any V36.

---

## 1. The pipeline (CAN in → motor out) and who cuts where

```
 openpilot CAN 0xE4 STEERING_CONTROL
   │  [SEG A] FUN_00052676 → command setpoint gp-0x69ae (0xFEDF1652)
   │          5 intake gates = comms-validity only (checksum/counter/timeout/STATUS_WORD) — NOT torque/rate
   ▼          ⇒ intake CANNOT drop LKAS on a bump-via-value. RULED OUT as the trigger.
 column-torque sensor (5 coil ADC ch) + steering-rate sensors
   │  [SEG B] voter FUN_00041eec → gp-0x6a62 (MAX torque, 0xFEDF159E), gp-0x6a5e (AVG, 0xFEDF15A2), gp-0x6a64
   │          rate path FUN_0003f776 → gp-0x6a60 (RATE magnitude, 0xFEDF15A0);  gp-0x4f68 = |col ang.vel| (SEG D)
   │          ⚠ gp-0x6a62 rising edge is UNFILTERED (fall-limiter cal 0xC64ED=16 only). 0xFFFF sentinel on DMA quorum loss.
   ▼
 engage/disengage SM
   │  [SEG C] dispatcher FUN_000413ae (state gp-0x67DC) → decider FUN_00040d58 → consensus FUN_000406ae
   │          decider gates on torque/angle/RATE; dispatcher-level TRUMP overrides bypass the decider entirely
   ▼          ⇒ sets deliver flag gp-0x6809, substate, mode bytes
 per-cycle deliver-commit
   │  [SEG D] FUN_0003d04c(4,0) @0x412ae — 7 pre-gates; bail = commit skipped
   │          Gate 5 gp-0x4f68≥4096 (RATE), Gate 7 gp-0x6a5e≥320 (V35-disabled) + downstream FUN_0003c7fc angle-deadband
   ▼          ⚠ commit chain writes NO torque — only mode/angle bookkeeping (gp-0x6770/71/72). See §4 open link.
 arbitration / merge
   │  [SEG E] FUN_00028ea6 : deliver flag gp-0x6809 ≠ 1  → zero LKAS term ; STEER_STATUS=4 is a REPORT counter (no gating)
   │          soft-EME rate-shaper FUN_00042af8 (SM2/SM3, merged cmd gp-0x6b98) = DIFFERENT class; hard-DTC FUN_00043e44 = DIFFERENT class
   ▼
 delivery SM / ENABLE / limit+pack
   │  [SEG F] ENABLE FSM gp-0x67a4∈{2,3} (0xFEDF185C) gates LKAS output gp-0x6b3c (0xFEDF14C4)
   │          all tail clamps (F1/F5-F9) are magnitude truncations — NOT sensor-conditional
   ▼          ⇒ CUT IS INHERITED FROM UPSTREAM, not produced here.
 motor distribute/clamp → TSG20 PWM compare regs → CAN motor telemetry (tracks already-gated value)
```

---

## 2. Master gate table — everything that can gate LKAS torque, CAN→motor

Legend: **LIVE?** = still active after V33+V34+V35. **Bump?** = can a hard-turn+bump transient trip it.
Confidence: V = byte-verified this session by the owning tracer; V-prior = disasm-grounded from earlier work,
re-cited; I = inferred.

### Stage A — CAN RX intake (all comms-validity; none torque/rate; RULED OUT as bump trigger)
| # | signal | condition | on-trip | LIVE? | Bump? | conf |
|---|---|---|---|---|---|---|
| A1 | STATUS_WORD `gp+0x6400` bit3 | set | skip buffer → setpoint=0x7FFF | Y | no (comms) | V |
| A2 | STATUS_WORD bit23 | set | mark 0xFF + DTC log | Y | no | V |
| A3 | tick counter `gp-0xF4C` <500 | when byte2[1:0]==1 | force `gp-0x67F3`=0xFF | Y (500-cyc) | no | V |
| A4 | validator case code r6∈{1,2,3} | from unlocated caller | full sentinel + DTC latch | Y | no (value-invalid) | V (caller UNRESOLVED) |
| A5 | rx-timeout latch `gp-0x3330`==1 & r6==4 | set | full sentinel | Y | no (timeout) | V (producer UNRESOLVED) |

### Stage B — voter / signal production (produces the values the gates compare against)
| # | signal | behavior | matters because | conf |
|---|---|---|---|---|
| B-rise | `gp-0x6a62` (MAX torque) | **rising edge UNFILTERED**; fall-limiter cal `0xC64ED`=16/cyc only | no debounce in the rising chain → gates fire same-cycle | V |
| B-0xFFFF | `gp-0x6a62`=0xFFFF sentinel | `NOT(ch5 valid AND ≥3-of-4 primary valid)`, cal `0xC6501`=3 | a bump-coincident DMA-frame glitch (5 coils share one 8-byte frame) can rail it → decider sentinel gate | V |
| B-6a60 | `gp-0x6a60` = `|clamp(gp-0x6a56 angle-rate, ±12000)|` | **RATE magnitude, NOT torque**; made in `FUN_0003f776` not the voter | the engage-refuse gate `gp-0x6a60≥1600` is a RATE gate | V |

### Stage C — engage/disengage SM (decider FUN_00040d58 + dispatcher FUN_000413ae)
| # | gate | signal | condition (cal=stock) | on-trip | build touch | LIVE? | Bump? | conf |
|---|---|---|---|---|---|---|---|---|
| C1 | torque-MAX (ENGAGED/HOLDING) | gp-0x6a62 | ≥ `0xC6312` (320) | return 2 (leave) | **V33→65535** | **N** | — | V |
| C2 | torque sentinel | gp-0x6a62==0xffff | invalid-sensor | return 2 | kept | **Y** | frame-glitch | V |
| C3 | angle-consensus (ENGAGED) | gp-0x6cc4 via FUN_000406ae | dev ≥ `0xC6354` (4825) | return 4 | **V34 NOP 0x40de2** | **N** | — | V |
| C4 | angle-consensus (HOLDING) | \|gp-0x6cc4\| | > `0xC6354` (4825) | return 4 | **V34 NOP 0x40e12** | **N** | — | V |
| C5 | **engage-refuse RATE** (params 1,4) | **gp-0x6a60** | ≥ `0xC6310` (1600) | return 5 (refuse) | none | **Y** | **YES (rate)** | V |
| C6 | **engage/re-arm RATE** (params 1,4) | **gp-0x4f68** | ≥ `0xC61CE` (4096) | return 6 (refuse) | none | **Y** | **YES (rate)** | V |
| C7 | engage-3 (params 1,4) | gp-0x6ba4 | ≥ `0xC61CC` (3584) | return 7 | none | **Y** | ? | V |
| C8 | engage torque-MAX (param 1) | gp-0x6a62 | ≥ `0xC6312` (320) | return 2 | V33→65535 | N | — | V |
| C9 | **TRUMP state-2** | **gp-0x67FE** | **== 2 (unconditional, no debounce)** | commit state=3 (non-delivering pocket) | none | **Y** | **plausible** | V (struct); producer UNRESOLVED |
| C10 | TRUMP state-7/8 | gp-0x67FE==2 + latch (gp-0x138D/E, gp-0x1390) | latch set | commit state 8/3 | none | **Y** | ? | V |
| C11 | **FOC-mode** (states 2,7) | **gp-0x6772** | **!= 5** | demote → ENGAGING (state 1) | none | **Y** | plausible (FOC current) | V (struct); polarity UNRESOLVED |
| C12 | **fault-bit-13** (state 7) | `FUN_00046ea6(13)` bit of gp-0x18D4 | bit set | demote → state 1 | none | **Y** | **unknown identity** | V (struct); bit-13 setter UNRESOLVED |
| C13 | request-cancel | gp-0x138F==2 | upstream cancel | demote → state 1 | none | Y (intentional) | no | V |
| C14 | raw-sentinel | gp+0x6470==±32768/32767 | data-invalid | demote → state 1 | none | Y | frame-glitch | V |

### Stage D — per-cycle deliver-commit FUN_0003d04c (7 pre-gates; bail = commit skipped)
| # | gate | signal | condition (cal=stock) | bail→ | build touch | LIVE? | Bump? | conf |
|---|---|---|---|---|---|---|---|---|
| D1 | DTC-status 13 | `FUN_00018ce8(13)` | ==2 | ret 5 | none | Y | low (needs latched fault) | I/MED |
| D2 | DTC-status 14 | `FUN_00018ce8(14)` | ==2 | ret 5 | none | Y | low | I/MED |
| D3 | system-mode | gp-0x67FA | ==10 | ret 6 | none | Y | unknown | MED |
| D4 | unknown | gp-0x4E5F | !=1 | ret 3 | none | Y | unknown | LOW (identity UNRESOLVED) |
| **D5** | **Gate 5 (TORQUE — corrected)** | **gp-0x4f68 = \|column torque\|** | **≥ `0xC61EA` (4096)** | ret 3 = skip commit | **none** | **Y** | **only on >4096 spike (logged peak ~2340)** | **V — re-verified via CAN packer; was mislabeled velocity** |
| D6 | plausibility | gp-0x67F4 | !=1 | ret 2 | none | Y | low | V |
| D7 | torque-AVG (Gate 7) | gp-0x6a5e | ≥ `0xC62FE` (320) | ret 2 | **V35→65535** | **N** | — | V |
| D8 | **downstream angle-deadband** | \|gp-0x6cc4 − ref\| vs `0xC6354`/`0xC635C` | in FUN_0003c7fc, AFTER the 7 gates | zeroes mode byte gp-0x6770 | none | **Y** | angle (bump) | V |

### Stage E — arbitration + shaper + DTC (the cut LANDS here; soft-EME/hard-DTC are different classes)
| # | gate | signal | condition | effect | class | LIVE? | conf |
|---|---|---|---|---|---|---|---|
| E1 | deliver-flag zero (2 sites) | gp-0x6809 ≠ 1 OR bVar1==0 | @0x2975a / 0x29808 | zero LKAS-side term | **gentle-EME lands here** | Y | V |
| E2 | STEER_STATUS=4 producer | gp-0x6757 countdown, cal `0xC64E2`=5 | @0x2a4ea/0x2a4fa | writes gp-0x6807=4 | **REPORT only — no gating read-back** | Y | V |
| E3-E10 | soft-EME shaper arms/cuts | integrator gp-0x3570, 3-way bound | FUN_00042af8 | wind-down MERGED cmd gp-0x6b98 | **soft-EME (different)** | Y (V31 boost-floor mitigates) | V |
| E11-E12 | hard-DTC lockstep | float twin vs int wall | FUN_00043e44, DTC 0xF00049 | latched motor-off | **hard-DTC (different)** | Y (matched) | V |

### Stage F — delivery / ENABLE / motor (tail clamps are magnitude-only; cut is inherited)
| # | gate | signal | condition (cal=stock) | effect | LIVE? | Bump? | conf |
|---|---|---|---|---|---|---|---|
| F1 | arb GAIN+clamp (Civic-0x137F2 analog) | LKAS magnitude | GAIN `0xC646C` (891→**1782** V14+), clamp `0xC61B4` (512→**1024**) | scales magnitude | Y (doubled) | no (scaler) | V |
| **F2** | **ENABLE gate** | **gp-0x67a4** (0xFEDF185C) | ∈{2,3} else 0 | gp-0x6b3c := value or **0** | Y | via FSM | V |
| F3 | ENABLE producer FSM | gp-0x3D28 8-state handshake; AUX1 gp-0x1859 / AUX2 gp-0x185E / AUX3 gp-0x185F | ENABLE∈{0..5}, only 2/3 pass | multi-cycle "torque-blind handshake" | Y | plausible (handshake stall) | V |
| F4 | 2nd gp-0x6b3c writer (NEW) | FUN_0002b35a @0x2b41c | consumes gp-0x6809 + ENABLE-flag | gp-0x6b3c := 0 or ungated | Y | UNRESOLVED | I |
| F5-F9 | limit/distribute/mixer/governor/shaper clamps | various | ±0x2800 LKAS lane etc. | magnitude truncation | Y | no | V/V-prior |

---

## 3. The rate-channel synthesis (the load-bearing insight)

Three independent tracers converged on the same conclusion from different directions:

- **Segment D** solved Gate 5: `gp-0x4f68 = clamp(|gp-0x4f60|, 0, 65535)` = **unsigned column angular-velocity
  magnitude** (two independent derivations agree; `gp-0x4f60` is triple-confirmed elsewhere as signed steering
  rate). Cal `0xC61EA`=4096 is only ~16 % of the ±25600 window the same signal uses for its own plausibility
  ceiling — a **tight** threshold a bump easily exceeds.
- **Segment C** found the *same* `gp-0x4f68` gates the decider's engage-attempt / re-arm paths (params 1 & 4,
  cal `0xC61CE`=4096), and that the engage-refuse companion `gp-0x6a60 ≥ 1600` is *also* a rate magnitude.
- **Segment B** proved there is **no debounce on the rising edge** anywhere from coil ADC to gate — a rate
  spike reaches the gate the same cycle it happens.

Net: one bump does two things at once — **bails the current deliver-commit (Gate 5) AND refuses re-arm
(gp-0x6a60, gp-0x4f68)** until angular velocity decays below threshold. That is a mechanically exact match to
"LKAS drops on the bump, then re-arms a beat later," and it is invisible to every torque-threshold build
(V33/V35) because those raised the *torque* gates while the *rate* gates sat untouched. **This is the prime
hypothesis.**

---

## 4. The one unclosed structural link (why this is a hypothesis, not a verdict)

Segment D walked the deliver-commit chain `FUN_0003d04c → FUN_0003c4e2 → FUN_0003c6a4 → FUN_0003c7fc →
FUN_0003fd8e` to its end and found **no write to any torque or current register** — the chain updates
mode/angle bookkeeping (`gp-0x6770/71/72`, `gp+0x6470`) only, and **both call sites discard the return code.**
So the V35 handoff's premise "bail `FUN_0003d04c` ⇒ torque cut" is **not directly proven**; the effect must
propagate indirectly (mode byte `gp-0x6770→gp-0x6772` → Segment C's FOC-mode gate `gp-0x6772!=5` → state
demotion → deliver-flag `gp-0x6809` → Segment E zeroing → Segment F ENABLE). Segment F closed the *tail*
(`gp-0x6809`/`gp-0x67a4` → `gp-0x6b3c`), but the **middle hop — how a `FUN_0003d04c` pre-gate bail actually
reaches `gp-0x6809`** — is inferred, not byte-traced end-to-end. This matters two ways: (1) it means Gate 5's
"cut" power depends on that unverified chain; (2) it means the **dispatcher-level gates (C9 `gp-0x67FE==2`, C11
`gp-0x6772!=5`) have a *more direct* path to leaving the delivering state** and deserve equal weight. Honest
status: strong static case, one gap, no on-car confirmation.

---

## 5. Ranked still-live suspects (after V33+V34+V35)

1. **D5 — Gate 5 `gp-0x4f68 ≥ 4096` (column angular velocity), deliver-commit.** Rate-based, no debounce, tight
   threshold, fits "+bump," untouched. Also gates re-arm (C6). **Prime.** Caveat: §4 hand-off.
2. **C5/C6 — engage/re-arm RATE gates `gp-0x6a60 ≥ 1600` and `gp-0x4f68 ≥ 4096`.** Explain the "re-arms a beat
   later" half; same rate channel; untouched.
3. **C9 — `gp-0x67FE == 2` trump override.** Unconditional dispatcher-level bypass into a non-delivering
   pocket; the most *direct* cut mechanism, but its producer is unknown (0 store-sites found) so "a bump makes
   it 2" is unproven. Note `gp-0x67FE==2` also selects the voter's adaptive-spread mode (Seg B) — it reads like
   an "actively-engaged" mode indicator, so its polarity needs care.
4. **D8 — `FUN_0003c7fc` angle-deadband (`gp-0x6cc4` vs `0xC6354/0xC635C`).** Fires even after all 7 pre-gates
   pass; reuses the same angle accumulator V34 chased; untouched.
5. **C11 `gp-0x6772!=5` FOC-mode** and **C12 `FUN_00046ea6(13)` fault bit** — live, direct state-demotes,
   identities unresolved (highest-value next disasm hops).
6. **C2/B-0xFFFF voter sentinel** — frame-glitch class; needs a DMA glitch coincident with the shock, not just
   a mechanical transient. Lower probability, deliberately retained as a genuine dead-sensor path.

Everything the three builds touched (C1/C3/C4/C8/D7) is confirmed **neutralized** and can be crossed off.
Segment A (intake) and Segment F tail clamps are **not** the trigger.

---

## 6. Corrections of record (found by cross-checking tracers this session)
- Dispatcher state byte is **`gp-0x67DC`** (0xFEDF1824), not `gp-0x679c` (stale boot fact).
- ENABLE byte `gp-0x67a4` absolute = **`0xFEDF185C`** (0xFEDF8000−0x67A4), not `0xFEDF195C` (that is
  `gp-0x66A4`). The instruction `st.b r14,-26532[gp]`@0x2b51e was cited correctly; only the hex was wrong.
- `gp-0x6a60` is a **RATE** magnitude, not torque (confirms the V32 flag about `gp-0x6a56`).
- `gp-0x4f68` (Gate 5) identity = **column angular velocity**, previously listed identity-UNCONFIRMED.

## 7. Recommended next step — DISCRIMINATE, don't guess (V31T-style telemetry drive)

Three builds were confidently wrong; the map now gives a clean discriminator. Before any V36, piggyback these
on the CAN-0x660 telemetry channel over **one hard-turn+bump drive** and see which crosses its threshold at the
exact instant delivery drops:

| signal | absolute | tells us |
|---|---|---|
| `gp-0x4f68` | 0xFEDF3098 | Gate 5 / re-arm RATE (prime) — crosses 4096? |
| `gp-0x6a60` | 0xFEDF15A0 | engage-refuse RATE — crosses 1600? |
| `gp-0x67FE` | 0xFEDF1802 | trump override — momentarily == 2? |
| `gp-0x6772` | 0xFEDF188E | FOC-mode — leaves 5? |
| `gp-0x6a5e` / `gp-0x6a62` | 0xFEDF15A2 / 0xFEDF159E | torque AVG/MAX — confirm they DON'T (V35 disabled them) |
| deliver flag `gp-0x6809` | 0xFEDF17F7 | the moment of the physical cut |

If `gp-0x4f68` (and/or `gp-0x6a60`) crosses at the cut instant while the torque signals stay sub-threshold,
the rate channel is confirmed and a V36 would raise `0xC61EA` (+ the re-arm twins `0xC61CE`/`0xC6310`) with the
same clean-lever rigor V33/V35 used — **but only after the telemetry confirms it, and after the §4 hand-off is
byte-closed** so we know the lever actually gates torque.

## 8. Method / provenance
6 `firmware-codepath-tracer` subagents, one per segment (A CAN-intake, B voter, C engage-SM, D deliver-commit,
E arbitration/shaper, F delivery/motor), all read-only on stock `code.bin` with r2 `v850.gnu`. Per-segment
detail + method notes in `analysis-2020accord/.claude/agent-memory/firmware-codepath-tracer/reference_accord_segment*`
and `.claude/agent-memory/firmware-codepath-tracer/reference_accord_engage_sm_full_dispatcher_and_trump_exits.md`.
No code, build, binary, or flash touched.
