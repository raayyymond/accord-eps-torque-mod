# HANDOFF 2026-08-09 late — V87 BUILT: every control lever died, so the build measures instead

**Session shape:** orchestrator + 12 subagents, all confirmed stopped before close-out.
**Deliverable:** V87, built and verified, unflashed. Plus five dead levers, one blocked cave route,
two corrections to standing kit claims, and one record defect where an estimate had been promoted to
a measurement.

---

## 1. What was asked, and how it changed

The operator asked for a **sharp low-pass filter** — find one, and if none exists, build one with great
care and adversarial review. Three things happened in that order:

1. **No sharp filter exists.** Confirmed image-wide over the ~40 kB control region: nothing has Q > 0.52.
2. **Building one in the obvious place would disable the power steering** (§4). Not brick — *disable*,
   mid-drive, the V74/V75 class.
3. **The one cal-only candidate that looked like a damper is not one** (§3), and the sizing figure that
   would have set its dose is an unmeasured estimate (§5).

⇒ The operator's own call: *"if you NEED a probe first to not guess on things, lets do that"*, with a
specific and better idea — use a CAN message that sits near zero almost always, i.e. `MOTOR_TORQUE`.

---

## 2. V87 — built, verified, unflashed

```
image  27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034   1,048,576 B
.rwd   997002f01aa7b5bfe0ac32b8f17396a593a3e298ea11919ea2331b718f6e85f6     986,042 B
39990-TVA,A160-V87-V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98-0x13000-0x100000.rwd
base   _v38_plain_image.bin  a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8
```

| # | addr | stock | V87 | what it does | from |
|---|---|---|---|---|---|
| 1 | `0x2A1F0` | `6c74` | `d07c` | forward LKAS reader → its own cal cell | V57 |
| 2 | `0xC646C` | 891 | **891** | shared sensor scale at Honda's value ⇒ 4 FEEDBACK readers un-boosted | V57 |
| 3 | `0xC6CD0` | blank | **3564** | private forward LKAS gain = **4.000×** | V38 |
| 4 | `0x454FE` | `ba` | `b5` | state-4 command-magnitude clamp unreachable | V42 |
| 5 | `0xC62EA` | 320 | **0** | LKAS commandable to 0 km/h | V53 |
| 6 | **`0x55DF2`** | `e893` | **`6894`** | **427 `MOTOR_TORQUE` ← `\|gp-0x6b98\|`** | **NEW** |
| 7 | `0x55C0E` + `0xC4B34` | stock / FF | hook + 62 B | 330 byte-4 telemetry, V86B payload verbatim | V86B |

**Verification:** 10 runs / 85 bytes vs the V38 base, **zero unattributed**; restoring the attributed set
reproduces V38 bit-for-bit; CRC 50/50 on the built image, on the readback, and on the shipped `.rwd`
re-read from disk; the probe instruction re-decoded **from the built image** as `ld.h -0x6B98, gp, r6`.
Frozen-cell assertions cover every lever this session killed.

### Why the probe is a displacement edit and not a cave
`FUN_00055d80` packs 427 (`0x1AB`) as
`r6 = gp-0x6c18 → FUN_00049a5a → FUN_00049a78 (abs) → FUN_00049a90(x*5>>3, 0, 0x3ff) → pack`,
and calls the checksum `FUN_00057b24(gp-0x13cc, 3, 0x1ab)` **last**. Changing only the source load's
displacement makes Honda's own abs / ×5/8 / 10-bit clamp / pack / checksum chain run on our signal.
**Zero control-path effect — we change what a transmit packer READS and write nothing.** Resolution
0.625 counts/LSB up to 1637, saturating near the ±2000 rail ⇒ full resolution exactly in the ratchet
regime (~120 counts p-p), decoded natively by openpilot with no DBC change.

### 🛑 Honest label
**It will read as a NULL on the ratcheting, by design.** No damping, no filter, no new authority.
**If it moves the ratchet, the model is wrong — and that is itself information.**
⚠ **The feel change is real and comes from the REBASE.** Gone: V85's friction relay (`0xC40BC`
6000→600, a 10× revert), Lever B, and V86B's engaged creep damper — the low-speed drag the operator
disliked. Expect V38's character, plus the ratchet fix, plus steer-to-zero.

### The ratchet fix REMOVES a rate limiter — the operator asked exactly this
Stock, while `gp-0x67fa == 4`, the governor **forbids the command's magnitude from increasing** and
writes the suppressed value back, re-running a rate-interpolation block seeded from the OLD value ⇒ it
**is** a rate limiter on the LKAS command, cumulative across cycles. `0x454FE` `BA→B5` (Bcond BNE→BR)
makes `[0x45500,0x455C4)` unreachable. It matters most on this base: stock demands ≤417 LKAS counts,
**V38 demands 1782**.

---

## 3. `0xC63B8` — a real 8 Hz structure, refuted five ways

The orchestrator found, and four agents independently reproduced, a genuine band-pass in `FUN_0003b66a`
(task 1, 1 kHz): backward difference → two cascaded EMAs sharing `0xC63B4` = 51 → gain `0xC63B8` = 41.
**Peak 8.13–8.14 Hz, Q 0.501, phase +1.44°, −3 dB 3.38–19.64 Hz.** Byte-identical to stock in **all 88
images** — never touched.

**The structure is real. The orchestrator's reading of its CLASS was wrong.** Kills:
1. **Full-wave rectified** — `gp-0x6ba6 = |gp-0x6b9a|`; all 7 readers of the signed cell are
   `|x| ≤ 25600` plausibility windows. **No summing junction; `abs()` destroys the phase.** The live
   path is a **LERP index into the boost gain tables**, which fall 16384 → 8188.
2. **FactorB flat `[1024]×4` in all 34 records** ⇒ the damper arm is inert at any gain.
3. **FactorC `Y[0]`=0 below 35 km/h** zeroes the damper product at creep regardless.
4. **The boost arm is the V58/V59/V60 parametric pump — already flashed and NULL**, arc marked closed.
5. **No headroom:** stock is at **37.8 % of clamp at max** (not 1–6 %); 4× reaches 151 % and clips.
   Raising it costs up to **46.9 % of parking assist** for **0.01 %** on the ratchet — **185× below the
   Mathieu threshold.** The 2f channel is structurally subordinate 3.00:1 to the DC channel.

⊕ **It is an excellent *sensor*.** `gp-0x6de8` / `gp-0x6de4` / `gp-0x6d04` / `gp-0x6d00` are 1 writer /
0 readers — a free, already-tuned, frequency-selective ratchet instrument with zero blast radius.

---

## 4. 🛑🛑 A filter in the shaper would disable the power steering

`FUN_00043e44` is a **float twin of the shaper**: reads `gp-0x6acc` at **`0x4467a`** with the SAME
`0xC64C8` mode byte and `0xC61D4` cal, compares against the delivered command with tolerance
**`0.0048828125` = 5/1024**, and after **`0x3c23d70b` = 0.01 s** escalates by +1024.0 against a 128.0
threshold ⇒ `FUN_000462e6(0x3f1b)` ⇒ **DTC 0xF00049**. At 8 Hz a half-cycle is 62 ms — **six times the
trip dwell.**

**The two "best" hook sites (`0x431C4`, `0x43206`) sit inside its coverage.** `gp-0x6b08` is the
narrowest node in the chain and is **the one node that must not be used** — narrowness is not safety.
Measured phase budget in that region: **2.4°**. The only monitor-clean single-instruction site is
**`0x453e0`** (the `gp-0x6b94` read), where everything downstream re-derives from the filtered value.

---

## 5. 🛑 Record defect — an estimate had been promoted to a measurement

`STATE.md:105` called `0xC646E` *"the one **MEASURED** cell, at 1–6 %"*. Its source memory says
**"(prior-session estimate)"**. A 4× dose recommended mid-session rested on it and was **withdrawn**.
⊕ Worse, the same figure was being transplanted onto `0xC63B8` — a cell whose scale differs by
**16,384×** (2⁻¹⁰ vs 2⁻²⁴), in a different function. Confirmed disjoint: one access each, no compounding.

---

## 6. Method results worth keeping

- 🛑 **`gp-0x1500` DOES NOT pass a correct static scan.** Its address is an image literal **twice**, in a
  13-entry 8-byte-stride registry. A **footprint-aware + both-encodings + image-wide LE32 literal** scan
  reproduces **all four** known on-car RAM failures and clears both known-good cells. Corrects
  `BUILD-LINEAGE.md:929`. ⚠ Not proof of ownership.
- 🛑 **A live 1 kHz blind spot in every kit scan:** `movea disp,gp,rN` + register add — 2,961 sites,
  796 bases, **224 provably indexed ⇒ statically unbounded extent**, invisible to disp16 and disp23.
- **The 6-byte Format XIV displacement IS byte-enumerable:** `disp = (sext16(hw2) << 7) | ((hw1>>4)&0x7F)`,
  zero over-match. ⚠ **588 six-byte STORES exist image-wide** ⇒ any disp16-only writer census is short.
- **`FUN_00041d56` is a genuine 3×3 state-space with complex poles** — but ζ = 0.975, Q = 0.513, **0
  torque-path readers**. ⇒ the closure argument's *premise* was false; its *conclusion* survives.
- 🛑 **`is_current` on the Ghidra bridge is a RACE between concurrent agents.** Pass `program="code.bin"`
  explicitly on every call; never trust a snapshot, including one taken a call ago.
- 🛑 **A notch beats a low-pass by ~5× on every phase metric** at equal 8 Hz attenuation, and the mode's
  frequency wander does **not** kill it (worst cell −9.96 dB across the whole 0–15 km/h × load box).
  But an integer 8 Hz biquad **self-oscillates at ~375 counts, at 8 Hz**, unless it is a Chamberlin SVF
  with magnitude truncation, ≥8 fractional state bits and a 64-bit product — it would manufacture the
  exact tone being treated. Direct-form II is disqualified outright (381× DC gain on the internal node).

---

## 7. What the next flight should score

1. **`|gp-0x6b98|`'s real p-p amplitude during a ratchet episode.** This is the whole point of V87. It
   sets the phase budget for any future filter (assumed 120 counts; the answer swings **5×**) and
   discriminates a passive resonance being driven from a closed-loop pole — the fork that decides
   whether a filter helps or hurts.
2. **Whether the friction lane `gp-0x6b26` rails at creep.** It runs at **5.00×** at 0 km/h vs 90 km/h
   into a ±511 clamp **5× closer to binding** — a structurally low-speed-only relay candidate. ⚠ One
   gate (`gp-0x671a` vs `0xC64FD`=5) could void it.
3. **A V38-base feel baseline.** V87 is the first build in 49 to remove rather than add. Whatever the
   operator reports about V87's *feel* is the cleanest baseline the kit has had since V38.

🛑 **Score bands; let the operator score symptoms. Never call anything fixed that he has not called fixed.**
