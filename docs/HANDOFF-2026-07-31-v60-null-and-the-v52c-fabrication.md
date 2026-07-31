# HANDOFF 2026-07-31 — V60 returns NULL and closes the pump; the V52C "halving" turns out never to have been measured

**Predecessor:** `HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`.
**Session shape:** orchestrated, four parallel subagents (rlog/provenance, repo archaeology, two
`firmware-codepath-tracer`). **No firmware was built and nothing was flashed.** Every decision-bearing
claim was re-derived by the orchestrator with a second, independent method — and the two most important
results of the session are a **fabricated number caught** and **the orchestrator's own hypothesis
refuted by its own subagents.**

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
