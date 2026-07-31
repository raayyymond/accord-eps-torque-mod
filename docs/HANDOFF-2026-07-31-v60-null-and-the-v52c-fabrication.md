# HANDOFF 2026-07-31 — V60 returns NULL and closes the pump; the V52C "halving" was never measured; V61 built; the clock tree refuted

**Predecessor:** `HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`.
**Session shape:** orchestrated, six subagents (rlog/provenance, repo archaeology, three
`firmware-codepath-tracer`, one datasheet clock audit). **V61 was BUILT and is UNFLASHED; nothing was
flashed this session.** ⚠ Sections 1-9 say "no firmware was built" was true when written — V61 came
later; see PART TWO. Every decision-bearing claim was re-derived by the orchestrator with a second,
independent method, and the most valuable results are all **corrections**: a **fabricated number
caught** (§2), **the orchestrator's own hypothesis refuted by its own subagents** (§3), and **the
kit's clock tree refuted from the datasheet** at the operator's instruction (§12).

---

## 1. What was driven

**V60 flashed and driven. Operator: *"I drove on the V60 RWD. It did not fix the vibration issue."***
**No rlogs** — V60 carries V59's probe unchanged, so there was no new telemetry to upload.

### The null is the informative outcome, exactly as specified
V60 (`0xD2006` 102 → 43) was built as a **discriminator, not a fix**, and the record predicted this:
*"Expect it to be NULL… a null closes the parametric mechanism and leaves the loop standing."*
Pump causality was **not settleable observationally** — the index is `|x|` of a bar-derived signal, so
2f coupling is arithmetically forced — and `eps_crit = 2/Q` needed a **passive Q** that V59 could not
measure (no ring-down exists: 66 candidates, longest 0.63 cycles). Only an intervention could separate
drive from echo.

⇒ **The V58/V59/V60 parametric-pump arc is CLOSED.** The 42.19 Hz index modulation is real and
engagement-gated, and it does **not** drive the grinding.

---

## 2. 🛑🛑 The headline: "V52C halved the mode" was never a measurement

The loop hypothesis's single best supporting evidence was: *"V52C — the only feedback-path lever ever
flashed — halved the mode, the largest single effect any build has had."* **It is false, and it was
false in a specific, reproducible way.**

**The arithmetic identity.** V52C's EMA at α = 74/1024, fs = 1 kHz:
`|H(20.9 Hz)| = 0.4963` = **−6.08 dB**. **−6.1 dB IS 0.496× IS "halved."** The two figures in the record
are the same statement written twice. (Computed independently by the orchestrator *before* the subagent
report arrived at the same place.)

**The textual lineage, git-traced.** The phrase was born in `f0adb24`
(`HANDOFF-2026-07-28-v55-...md:205`) as a **caveat on why V52C's NULL was weak evidence**:
> ⚠ **V52C's null is weak** — α = 74/1024 ⇒ fc ≈ 12 Hz ⇒ only −6.1 dB at 21 Hz *while adding 61° of
> lag*. **It halved the mode's content; it did not remove it.**

By `59acdd2` (the V59 handoff) it had become *"halved the mode — the largest single effect any build has
had"*, and **the word "null" was gone.** It then propagated into `STATE.md`, `BUILD-LINEAGE.md` and
`memory/reference_accord_loop_through_torque_sensor_uncompensated.md` as the retrodiction that made the
loop compelling.

**Every contemporaneous record says NULL**, including the operator's own report
(`HANDOFF-2026-07-26-route13-...md:8`): *"V52C did not fix the vibration; it clearly changed manual
driving feel."* Also `build_v55_tva.py:24` (*"ALL NULL"*), `build_v56_tva.py:78`, and
`ARCHIVE-CLAUDE-MD-2026-07-27.md:56` (*"a fair test of the `gp-0x4f60` lane ⇒ real evidence AGAINST that
lane"*).

**There are no V52C rlogs and there never were.** Routes on disk: `13,1a,1b,1c,24,28,29,2b,2c`. The
V52C window `08`–`12` is absent machine-wide and was never in git. **`STATE.md:479` asserted "The rlogs
exist; this is analysis, not a drive" — that instruction was unexecutable.**

⇒ The loop hypothesis loses its retrodiction and now rests only on its two **measured** legs: the
**21.09 Hz command→torsion-bar transfer peak** (global max over 3–46 Hz) and the **traced absence of any
motor-command feedforward**. ⚠ **This is not a falsification of the loop** — a 2× gain cut carrying
+57–61° of lag is a poor stabiliser, so a null is also what a real loop with <6 dB gain margin gives.
But it **is** weak-to-moderate evidence against the `gp-0x4f60` **VALUE** path specifically.

### ★ And the V52C filter left the car by DRIFT, not by decision
**V52C never appears as a base image for any subsequent build.** FOURFRAME was built on `_v38`
(`build_vfourframe_tva.py:198`), V53 on FOURFRAME2, V54/V55 on V38, then V57←V55, V58←V57, V59←V58,
V60←V59. Byte-verified: all 19 carrier sites read stock `0xB0A0` in V55/V57/V58/V59/V60; a scan for
disp16 `0xED00` (gp-0x1300) returns **21 hits in `_v52c` and 0 in every other image**.

**There is no recorded decision anywhere.** The contrast is stark: V56's revert is stated explicitly in
three places (*"⇒ REVERT TO V55"*). V52C has no equivalent line. `STATE.md` mentions it once and never
notes its filter left the car; `BUILD-LINEAGE.md:209` lists it in the flashed lineage without flagging
that the trunk re-rooted. The nearest thing to a decision pre-dates V52C's build and concerns the
incomplete 10-repoint V52. ⇒ **Nobody weighed keeping it. It fell out as a side effect of a baseline
choice.**

---

## 3. The orchestrator's hypothesis — raised, then refuted by its own subagents

**Raised:** V52C filtered the torque **VALUE** `gp-0x4f60` (69 sites, 19 repointed) and left the torque
**RATE** `gp-0x4f62` (9 sites, **0** repointed) untouched. A first difference is a derivative
(≈264× at 21 Hz), so the rate looked like the dominant unfiltered carrier.

**Refuted, two ways independently, and byte-confirmed by the orchestrator:** `tp+0x74be` = `0xC64BE` =
**0**, so `FUN_0003b66a`'s `gp-0x4f62` **magnitude** term (`0x3B736-0x3B758`) is **dead code**. Two of
the three rate consumers (`0x02C4E8`, `0x03B6A8`) are **validity gates only**, not signal paths.
⇒ the boost-amplitude index is **not** rate-driven, and V60 did **not** attack the wrong end of it.

**What survives, sharper:** `0x03AA9C` in the aggregator is the **one live magnitude path**, a single
load clamped ±0x1400 shared by **both** r24 and r26, summed ungated. It is the only torque-feedback path
**V52C's mechanism was structurally incapable of reaching** — the rate is a different cell written by a
different function, so no amount of "repoint more `gp-0x4f60` sites" could ever have covered it.

### ★ The gap that is genuinely open: r24 and r26 were each killed ALONE, never together
- **V39** suppressed **r24** — *conditionally*, via a cave at `0x3AC78` that bypasses unless driver max
  torque < 320 **and** LKAS sits in a mid band. **Not an unconditional lane removal.** → null.
- **V42** zeroed **r26**; its own docstring: *"WHY r26 AND NOT r24: r24 was already zeroed by V39 and
  changed nothing on-car."* → null.

They are two gain-scalings of the **same** clamped signal, so killing one leaves the other carrying the
rate ⇒ **each null is uninformative about the lane as a whole.** Re-verified cal sets (after correcting
a sixth off-by-0x1000): r24 = `0xC6440`=2048, `0xC6442`=1024, `0xC6446`=512, `0xC61F6`=3;
r26 = `0xC6444`=512, `0xC643E`=1536. ⚠ **Adjacent to two falsified builds — state that plainly.**

---

## 4. ★ Strategy-changing result: tracking LAG, not the dead zone, is the cost of a feedback low-pass

Simulating the exact integer kernel (and correcting two defects in the orchestrator's own first model —
it used V50's floor arithmetic instead of V52C's `addi 512` round-to-nearest, which **halves** the dead
zone to `512/α`):

| α | fc Hz | dB@20.9 | phase | dead zone | lag @2166ct/1Hz |
|---|---|---|---|---|---|
| **74 (V52C)** | 11.94 | **−6.08** | −56.5° | ±6.9 | **173** |
| 32 | 5.05 | −12.57 | −72.7° | ±16.0 | 419 |
| 16 | 2.51 | −18.48 | −79.4° | ±32.0 | **790** |

The dead zone is close to feel-neutral across the range (a smaller α lets `d` grow proportionally larger
before crossing a proportionally larger zone). **Phase is cheaper than expected** past α≈74. But the
**tracking lag scales in direct proportion to the attenuation bought** — at α=16 the assist trails the
bar by ~790 counts against ~2166 counts of hands-on torque.

⇒ 🛑 **THERE IS NO LOW-PASS SETTING BOTH MATERIALLY STRONGER THAN V52C AND FEEL-NEUTRAL.**
"Filter harder" is dead as a strategy. The only families that reduce 21 Hz gain *without* broadband lag
are a **notch** (needs two more V51P-class live-probed RAM cells and a base-assist closed-loop GATE 2 —
the gate V48B never attempted; its brick was root-caused to a RAM collision, not the notch concept) and
**feedforward cancellation** (a static gain: no lag, no dead zone, no pole — but the scale factor is
unmeasured and over-compensating inverts the loop sign).

---

## 5. Other closures and corrections

- **`0xC63BA` is pre-falsified by V60's null.** It looked ideal (cal-only, 512 = 2-stage EMA α=0.5,
  ≈−0.30 dB at 21 Hz, exactly 2 readers at `0x3B7BA`/`0x3B7D4`, never edited, explicitly reserved by
  `build_v59_tva.py:444`). But readers of `gp-0x6b9a` (8) / `gp-0x6ba6` (7) are confined to
  `FUN_00034350`, `FUN_00034a72`, their producer and V59's probe ⇒ the index drives **only** the
  boost/damping amplitude LERPs — the mechanism V60 falsified.
- **Two lanes removed from the search:** `FUN_00036c12` (`gp-0x6b26`) and `FUN_00036388` (`gp-0x6b62`,
  the operator's own return-centre hypothesis) read **no torque signal at all** — speed/motor-rate only.
- **`FUN_00036682`'s golden-model `[role OPEN]` is closed** — its own EMA α=6 (`0xC63D2`) is −27 dB at
  21 Hz, and it has zero `gp-0x4f62` dependency.
- **The rate has its own shadow-lockstep twin `gp-0x4488`** (8 sites, all producer-local;
  `0x4f60−0x4486 == 0x4f62−0x4488 == 0xADA`). Its 3 consumers are **not** shadow-checked, and nothing
  cross-checks the rate against an independent recompute ⇒ no monitor risk on that surface.
- **Cave collision resolved:** V52C's cave is `[0xC4B34,0xC4B8A)` = 86 B and V59's probe is
  `[0xC4B34,0xC4B76)` = 66 B — same base, direct overlap — but the hooks differ (`0x7FEAC` vs
  `0x55C0E`) and **1146 bytes of `0xFF` remain free to `0xC4FF0`**, so relocation is a one-constant
  change. ⚠ Layering the filter onto V59 would **corrupt V59's probe as a control** (repoint `0x3B672`
  is inside the probe's own producer).
- ⚠ **Sixth off-by-0x1000** (a subagent wrote `tp+0x743e` as `0xC743E`; it is `0xC643E`) and a
  **subagent misread the `gp-0x67fa` state masks as a 16-phase counter** — refuted from V42's state-4
  root cause and the shutdown assignment `gp-0x67fa = 8`; the agent retracted. **The settled
  state-not-phase memory stands and was NOT retired.**

---

## 6. 🛑 The open question only the operator can answer

**What did V52C actually feel like?** The entire repo contains **one sentence** — *"it clearly changed
manual driving feel"* — with **no direction, no magnitude, no descriptor.** Not heavier, not lighter,
not notchy, not better or worse. Nobody ever asked. The cost side of the whole feedback-filter family
turns on it, and §4 shows the previously-assumed explanation (the dead zone) is probably wrong — the
173 counts of tracking lag at α=74 is the far larger effect.

---

## 7. Next steps

1. ★★ **Answer §6.** If V52C felt bad, the feedback-filter family is off the table entirely.
2. ★★ **The one decisive, never-performed subtractive test:** zero the **whole** rate-lane gain surface
   in a single build so r24 **and** r26 die together, unconditionally. **Cal-only — no cave, no brick
   class.** ⚠ Adjacent to two falsified builds; its legitimacy rests entirely on "never killed together."
3. ⚠ **If that is null too, the torque-feedback hypothesis is in serious trouble** and what remains is
   base-assist **loop gain** (`0xD2834` / `0xCA154[mode]`, **zero build-script hits, never touched**) —
   the only lever that reduces loop gain rather than deleting a lane, and **a direct trade against
   steering weight ⇒ an operator decision, not an analyst's.**
4. **Do not propose** `0xC63BA` (§5), a stronger low-pass (§4), or anything on the pump (§1).

🛑 **Flash only on explicit operator instruction naming the file and the bus. Kill openpilot/pandad first.**

---

# PART TWO — written after the sections above, same session

Sections 1-9 were written mid-session. Everything below happened afterwards and changes the picture.

## 10. ★★ V61 BUILT — the one decisive subtractive test never performed

**The operator asked directly: "Has this really not been tested before?"** It had not. Byte-checked
every flashed image in the archive:

| build | r24 tap `0x3AC16` | r26 tap `0x3AB6C` | r26 gain tables | V39 cave |
|---|---|---|---|---|
| V39 | live | live | stock | **present** (conditional r24 kill) |
| V42 | live | live | **all zero** | **absent** |
| V61 | **dead** | **dead** | stock | n/a |

**No image has ever had both dead.** V42 zeroed r26's gain tables but carries no V39 cave, so r24 was
fully live; V39 had the cave but stock r26. And r24/r26 are **not independent lanes** — both are
gain-scalings of ONE value, `r1 = clamp(gp-0x4f62, ±5120)`, produced once at `0x3AAAC-0x3AAC0` and
tapped twice, same sign via a single shared polarity load @`0x3AB78`. ⇒ **each recorded null was
uninformative about the lane.**

**V61 = V59 + two single-BIT register-field edits**, `0x37E1→0x37E0` (`mul r1,r6,r0`→`mul r0,r6,r0`) and
`0x4001→0x4000` (`mov r1,r8`→`mov r0,r8`), both `reg1: r1→r0` with opcode and reg2 byte-identical —
verified on the built image independently of the builder. **No cave** ⇒ GATE 1 vacuous, the kit's only
bricking class avoided. r24's tail was **traced** to zero, not assumed (`mov 0x0,r6` @`0x3AC22` is the
default; both deadzone arms skip at `r8 = 0`). Based on **V59, not V60**, so the falsified blend reverts
by construction. 5 bytes off V59; **CAL CRC and `0xD2000`-block CRC both unchanged**.
⚠ Expect a manual-feel change; reversible via V59. ⚠ V59's probe rides along but is **not a null
control** — it reads upstream of the edit, so it is a *secondary readout*.

## 11. The Factor C / Factor E question — answered, and it cuts both ways

The operator asked whether V61's "they were only ever tested separately" argument is the same one made
about the damper's multiplicative factors, and whether C and E were ever done together.

**They ARE the same trap, with opposite arithmetic** — C×E is *multiplicative* (raising one is worthless
while another zeroes the product); r24+r26 are *additive* (killing one is worthless while the other
carries it).

**But the C/E simultaneous test WAS performed.** Byte-verified across the images: **V47 carries FactorC
`Y[0]` = 235 AND FactorE = (700,750,800)** (stock: 0 and (0,140,539)). V44 was the incomplete test; V47
was the complete one, it was flashed, and it gave *"marginally quieter at 5 mph, no effect in motion."*
⇒ The precedent **validates V61's logic** (V44's null genuinely was uninformative) while giving a
**sobering base rate** (the complete test still came back ~null). Recorded honestly rather than cited
one-sidedly.

⚠ One thing distinguishes V61: the damper is dead on the **data** regardless of how completely it was
opened — FactorC's LERP indexes on **speed** with `X[0] = 2240` ≈ 35 km/h ≈ 9.7 m/s, and the grinding is
already gone at 6 m/s. **The damper never turns on where the grinding lives.** That objection does not
apply to the rate lane, which is live at creep.

## 12. 🛑 The clock tree was wrong, and the operator called for the audit that found it

**Operator instruction: verify all clocks and task timings with the MCU datasheet as the ONLY source of
truth.** It refuted two figures the kit had carried for months.

- **PCLK = 40 MHz, not 80.** Likely original error: conflating **HEAPCLK** (80 MHz) with **PCLK** —
  option-byte Table 6-7 makes `PCLK = HEAPCLK/2` the only legal setting at HEAPCLK = 80 MHz. HEAPCLK is
  pinned by the firmware's own CLMA1 compare values, **orchestrator-verified in the stock dump**:
  `0x0053` @`0x5C8D8` and `0x004D` @`0x5C8E0` → `CLMA1CMPH`/`CMPL`, an exact match to the datasheet's
  worked row for CLMA1 @ 80 MHz / 16 MHz main OSC.
  ⚠ A CAN-bit-timing chain was offered as corroboration but **is not a second witness** — the
  orchestrator could not reproduce its field decode. With `FCN0CMBTCTL` = `0x030A`, whether `TS2LG` is
  3 or 4 bits flips the answer between **40 and 80 MHz exactly**.
- 🛑🛑 **OSTM0 IS NOT THE RTOS TICK, and never was.** Orchestrator-verified by decompiling the EI
  trampoline `FUN_0001492a`: it dispatches only EIIC `0x970/0x600/0x340/0x470/0x110/0x100/0xf0` +
  default — **no OSTM0 arm** — and `gp-0x42fc`, the rate divider's trigger, is written **only** by the
  `0x340` arm = **TAUJ1I2**. ⇒ the *"OSTM0CMP = 79999 ⇒ 1 kHz control tick"* chain was a red herring at
  **both ends**. TAUJ1's own period register was **not located** — the base rate is still not pinned to
  a register value.
- ✅ **The 1 kHz / 100 Hz figures SURVIVE** because they never used that chain: task 1 = 1 kHz is an
  **on-car measurement** (`STEER_STATUS=4` dwell, cal `0xC64DF` = 100 counts at 100.00 ms; CAN 399
  wire-fitted at exactly 100.000 Hz) and task 5 = task 1 / 10 is integer arithmetic.
- ⚠ **What propagates: the FOC/TSG20 carrier.** "~8 kHz" was computed conditioned on PCLK = 80 MHz ⇒
  likely **~4 kHz**; TSG20's clock-select is unverified, so both are OPEN. It bounds what the actuator
  can do at 20.9 Hz. Also: `EIIC 0x600` is `CSIH1IR` (serial), not ADC-complete; `EIIC 0x970` is
  `TSG21I05`, not TSG20 (`0x860`).

🛑 **PROCESS FAILURE, recorded as a rule.** The PCLK/OSTM0 correction **had already been found and
written down once**, in a tracer's agent-memory, and never propagated to `docs/` or the golden model.
Second instance in one session of the same family as the V52C caveat mutation. **A finding that
corrects a main-doc figure must be promoted the same day.** A sweep for the stale figures then caught a
contradiction the orchestrator had itself just created — the golden model's `BASE TICK` header still
asserted the refuted chain directly above the corrected `TASK RATE` entry. Fixed.
⚠ Historical `HANDOFF-*`/`ARCHIVE` docs were **left as written** — records, not instructions. Rewriting
them would destroy the provenance trail that made the V52C catch possible.

## 13. Next steps (supersedes section 9)

1. ★★ **Fly V61** on the V59 route shape: parking-lot creep ≤ 5 m/s, LKAS applying, sustained hands-off
   ≥ 3 s, deliberate on/off passes at matched speed and angle, plus a 10-13 m/s under-load pass.
2. ⚠ **If V61 is null**, the torque-feedback hypothesis is in serious trouble — value path (V52C),
   amplitude index (V60), resonance lane (V56), damper (V44/V47) and the rate lane would all be closed.
   What remains is base-assist **loop gain** (`0xD2834`/`0xCA154[mode]`, **zero build-script hits**), a
   direct trade against steering weight ⇒ **an operator decision.**
3. **Feedforward is specified but NOT sizeable.** `k` is a physical column-compliance constant, not
   recoverable from any table. The dangerous failure is `k` right in magnitude and wrong in phase:
   near 90° it adds quadrature noise, near 180° it **reinforces** the loop while looking like a fix.
   Needs a phase probe read **inside the 1 kHz tick** (both signals same tick, no 100 Hz mailbox
   penalty). Use `gp-0x6b3c` (arb output, LKAS-only), **not** `gp-0x6b98` (total command — would alter
   manual feel and cancel genuine driver input). Static gain ⇒ **zero new RAM cells**.
4. **Open:** TAUJ1's period register; TSG20's clock-select (4 vs 8 kHz).
