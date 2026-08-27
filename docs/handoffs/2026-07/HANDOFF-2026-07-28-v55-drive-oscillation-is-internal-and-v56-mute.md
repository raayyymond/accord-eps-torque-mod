# HANDOFF 2026-07-28 — the V55 drive: the oscillation is INTERNAL, and V56 mutes the carrier

**Nothing was flashed this session. No CAN was sent.** V55 was flashed and driven by the operator
*before* this session; this session analysed that drive and produced one build, unflashed.

**Predecessor:** `handoffs/2026-07/HANDOFF-2026-07-28-v54-drive-authority-resolved-and-v55-partition-probe.md`.

---

## 0. New standing instruction

🛑 **Explain firmware with simple Python that mirrors the decompiled arithmetic EXACTLY.** Integer `>>`,
the real Q-format, the real branch conditions, each line annotated with its instruction address,
constants byte-read **little-endian**. The dB/Hz interpretation comes *after* the code, never instead of
it. `memory/feedback/tooling/feedback-explain-with-python-mirroring-decompiled-arithmetic.md`.

This session is why: three of its four corrections of record were prose that sounded right over
arithmetic that was wrong.

---

## 1. The questions asked, and the answers

> *"I flashed the V55 RWD and demonstrated the vibration/grinding in a parking lot. Are you able to see
> it in the telemetry? Should we continue with addressing the closed-loop instability by moving the LKAS
> gain to drive only the LKAS demand path for V56?"*

**Yes, clearly** — and **no, not that lever.** The closed-loop *framing* is right and is now confirmed;
the `0xC646C` decoupling just cannot reach the carrier.

---

## 2. The vibration in route `1c` — two independent channels

113 s on a uniform 100 Hz grid, parking-lot creep, max **1.98 m/s (4.4 mph)**, 20.9% engaged, openpilot
railed 33.7% of engaged time.

| channel | engaged / disengaged, 15-26 Hz | peak | SNR vs the 30-45 Hz floor |
|---|---|---|---|
| CAN 399 torsion-bar torque | **877×** | 20.90 Hz | 3948× |
| CAN 399 `STEER_ANGLE_RATE` | **996×** | 20.90 Hz | 2470× |

Angle rate is a *different physical quantity in the same message*, so this is not a torque-sensor
artifact. Fits the speed trend exactly: 20.12 Hz @1.0 m/s (`1b`) → **20.90 @1.6** (`1c`) → 21.68 @4.0
(`1a`). And it is a **hands-OFF** phenomenon — on `1b`, engaged+hands-off carries **26×** the power of
engaged+hands-on. A disengaged, heavily hand-loaded column (driver torque 2106 counts) does **not**
produce it.

**The probe is live**: 10 distinct field values, 100% interior, no rails. `bit7 = 1` in 11,128/11,128
⇒ damper variant INDEX ≥ 10 ⇒ **V44/V47 hit the LIVE tables; missing-damping is genuinely falsified.**

---

## 3. ★★ The partition answered — and then some

**The ~21 Hz IS in `gp-0x6b98`**, same 0.195 Hz bin as the sensor, coherence **0.93** at the peak bin.

★ **Route `1b` is a perfect built-in null control.** V54's field is constant, so the identical pipeline
yields *exactly zero* command power and zero coherence. The peak in `1c` cannot be a processing artifact.

### openpilot is NOT the source

```python
DC  = 4.0 * 3564 / 32768         # setpoint x(-4), then Q15 gain 0xC646C   = 0.4351
IIR = 1/sqrt(1 + (21/4.97)**2)   # gp-0x3d3c pole 0.96875 @1 kHz -> fc 4.97 = 0.2314

31.7 * DC * IIR  ==   3.2   # openpilot's own 21 Hz (31.7 counts) through the LKAS lane
31.7 * DC        ==  13.8   # even with the low-pass DELETED entirely
# MEASURED in gp-0x6b98: 120.5 counts   ->  38x over budget, 8.7x even unfiltered
```

**The rail is the clincher.** While openpilot is pinned at ±4096 its own 21 Hz content is **exactly
0.0**, and the command still carries **105.8 counts** at 21 Hz (coherence 0.66).

⇒ **The oscillation is generated inside the EPS, downstream of the LKAS lane's low-pass.**

### The carrier's fingerprint: FLAT and unfiltered

H1 (`P_tc / P_tt`), engaged runs, 9 **independent** segments, coherence significance 0.312:

| f | H1, counts of `gp-0x6b98` per count of CAN-399 torque | coherence |
|---|---|---|
| 0.98 Hz | **0.192** | 0.672 |
| 21.09 Hz | **0.216** | 0.687 |

phase +171° @1 Hz → −161° @21 Hz — ~28° of rotation across the whole band. **A near-proportional,
inverted, ~4 ms-lagged feedback with no low-pass.**

⚠ **Direction is NOT proven.** H1 in closed loop with no external excitation cannot separate plant from
controller. Everything above establishes *where* the energy is, not *which element* destabilises.

---

## 4. Why the `0xC646C` decoupling cannot be the fix

```python
# FUN_00036682 (readers #5/#6). Not a plain EMA: y[n-1] is subtracted twice, so DC gain is K/2.
alpha = u16le(img, 0xC63D2)      # == 6  (NOT 14) -- identical in stock and V55
fc    = (6/1024) / (2*pi*1e-3)   # 0.933 Hz
att   = 1/sqrt(1 + (21/fc)**2)   # 0.0444 = -27.1 dB
(3564/32768) * att               # 0.0048  <- vs a MEASURED total of 0.221
```

Reader #5 is **2.2%** of the measured feedback; reverting the gain to stock removes **1.6% of loop gain
= 0.14 dB**. #6 sits behind the same pole, #4's output is dead, #2 is dead. And decisively: **the
measured transfer is flat to 21 Hz, which no lane behind a 0.93 Hz pole can produce.**

★ **The structural kill:** a function-scoped search finds **0 matches for `0xC646C` across all 468
instructions of `FUN_0003a382`**. The retarget would not touch the carrier at all.

**The decoupling is still worth building as a correctness fix** — it was independently re-verified this
session and is safe and byte-minimal: exactly 6 readers, no stores, no float mirror; `25 3f 6c 74` →
`25 3f d0 7c` preserves `ld.h`/dest `r7`/base `tp` (and `0xC6CD0` is even, which `LD.H`'s bare-
displacement form requires); the target sits 44 bytes into an 844-byte `0xFF` run with a 940-byte gap to
the next `movea` table base; inside the `0xC6000-0xC6FFC` CRC block; and reverting returns readers
#3/#5/#6 to **bit-for-bit stock** on a full cal-footprint diff.

---

## 5. V56 — the `0xC6AF0` mute

### The table, and why the addresses are what they are

These LERPs begin with a **point-count word**, so `0xC6AF0` names the *table*, not a value:

```python
count = u16le(img, 0xC6AF0)                    # 5
X     = [0, 3277, 3604, 19661, 32768]          # 0xC6AF2 .. 0xC6AFA
Y     = [32768, 32768, 0, 0, 0]                # 0xC6AFC .. 0xC6B04
#        ^Y[0]   ^Y[1]
```

Proved by the firmware's own pointer arithmetic — `addi 0xc,r15,r13` (&Y[0]) and `addi 0x2,r15,ep`
(&X[0]) at `0x3a63a`/`0x3a63e` — and corroborated on `0xD27BC`, `0xD27F8`, `0xD07BC`.

### Why the mute is COMPLETE, and not a fourth V43/V46/V48A

```python
r15     = lerp_y if authority <= 0x8000 else 0x8000   # cmovnh     @0x3a794
ceiling = (headroom * r15) >> 15                      # mul ; sar  @0x3a79e/0x3a7aa

def store(combined, ceiling):                         #            @0x3a88c-0x3a8a0
    if combined  >  ceiling: return  ceiling          # cmp r10,r14 ; bgt
    if -ceiling <=  combined: return combined         # subr ; cmp ; cmovle
    return -ceiling
# ceiling == 0  ->  EVERY path returns 0, whatever `combined` is.
```

`r10` is never redefined between `0x3a7aa` and `0x3a88c` — verified by pcode def-use *and* an explicit
destination scan of all 477 bytes. So the LERP gates the **final combined value**, after the three
parallel branches are summed.

★ **This reframes three "falsifications."** `FUN_0003a382` has **three parallel branches** and V43
(`0xC644A`→64 = −7.1 dB), V46 (`0xC6450`→32 = −12.6 dB) and V48A (one carrier muted) each attenuated
exactly one. Three nulls are precisely what that predicts. Both poles are `1024/1024` — **exact algebraic
identities, zero lag**, not "fast".

**Mute both Y[0] and Y[1]:** `bh` @`0x3a648` sends authority *exactly 0* down the below-knot path, while
1..3276 interpolates Y[0]→Y[1]; V54 measured `gp-0x6966` ∈ [0,127], straddling that boundary.

### The build

```
_v56_plain_image.bin  SHA 8c5c8a73425bf269c03b2e93144a7b8340983e5d873d70ea6009c0e68eacc7a0
V56 .rwd              SHA ffccf6e779498379e5d31326ba5bd7ed68da189d362b5f7ed925499df68343f4
```

**6 bytes off V55**, only **2** of them calibration — `32768 = 00 80` LE, so muting to 0 moves just the
high byte of each halfword. 84 off V38. 50/50 CRC blocks, both bootloader walks, RWD decode-back with
every gate re-run on the readback; count word and X row asserted unchanged, Y[2..4] asserted stock, V55's
cave and hook byte-identical.

`builds/v50_v79/build_v56_tva.py` is a **post-processor over `_v55_plain_image.bin`** — zero transcription, the V53
principle.

⚠ **`V53.assert_stock_cals()` correctly refused the edit** ("the `0xC6AF0` LERP moved — its edit direction
is UNRESOLVED"). **Do not weaken that shared guard**; five builders depend on it. V56 runs the
*unmodified* guard on the pre-edit source and re-expands its other two components afterwards.

⚠ **A build gate caught a real over-specification:** the first diff assert expected 4 changed cal bytes
and got 2. The gate was right; the expectation was wrong.

### GATE 2 — stated plainly

| | status |
|---|---|
| Monitor divergence | ✅ **closed** — `gp-0x6ad4` has exactly 2 gp-relative accesses image-wide (writer `0x3a8a0` plain `st.h`, reader `0x3aca8`); no lockstep/shadow/mirror, no monitor. The V27/V48B brick mechanism does not apply. |
| Protection removal | ✅ **closed** — Y[2..4] are never invoked (V54: authority pinned in the first flat segment). |
| Damping sign at 21 Hz | 🛑 **open** — undetermined, and this data cannot settle it. |
| Manual steering feel | 🛑 **open** — `gp-0x6ad4` is **not** LKAS-gated. |

⇒ **A reversible experiment, not a known-good fix.** Revert = reflash V55.

---

## 6. Corrections of record

1. 🛑 **`0xC63D2` is `6`, not `14`** — byte-verified three ways, identical stock and V55. fc **0.933 Hz**,
   −27.1 dB at 21 Hz, not 2.18 Hz / −19.7 dB. The golden model had it right; the memory did not.
2. 🛑 **LERP tables start with a point-count word** — `Y[0]`/`Y[1]` are `0xC6AFC`/`0xC6AFE`.
3. 🛑 **`gp-0x67fe` is not an engagement gate** — it is the EPS FOC/assist substate (`gp-0x6772 == 5 → 2`),
   which V31P measured at 1 in **100% of frames including disengaged**. A subagent's "hard engagement
   gate, exactly as your measurement requires" was the most seductive wrong claim of the session: it
   *confirmed* the hypothesis, which is precisely when to check it. Caught against an existing memory.
4. ⚠ **V52C's null is weak** — `alpha = 74/1024` ⇒ fc ≈ 12 Hz ⇒ only −6.1 dB at 21 Hz *while adding 61°
   of lag*. It halved the mode's content; it did not remove it.

---

## 7. Method notes

- **Orchestration worked, but the crux still had to be checked by hand.** Two tracers ran in parallel;
  both produced genuinely useful results and both flagged their own uncertainty well. The one
  decision-bearing question — *does `0xC6AF0` bound the final output or one branch?* — was asked three
  times and answered on the third; the lead resolved it independently in Ghidra in the meantime, and the
  two derivations agreed.
- **The active Ghidra program was a 3-function scratch import** (`v54_cavecheck.bin`), not the analysed
  `code.bin`. `get_current_program_info` first, every time.
- **V850 is little-endian.** A big-endian read made `0xC646C` come back as 60429 and every anchor fail at
  once — which is exactly what the anchor rule is for. Anchor *before* interpreting.
- **`analyze_dataflow` needs the `variable` argument** on a store, or it traces the address operand
  rather than the stored value.
- **Route `1b` as a null control** was free and decisive. When a probe changes between builds, the older
  rlog is a ready-made negative control for the whole analysis pipeline — use it.

---

## 8. Recommended next steps

1. **Flash V56**, one parking-lot loop, same conditions as `1c`. Decode with the unchanged
   `rlog-tools/probe/decode_v55_motorcmd.py`. Three outcomes: vibration gone ⇒ root cause; vibration persists
   **but the command's 21 Hz drops** ⇒ carrier not loop; neither moves ⇒ `gp-0x6ad4` eliminated.
2. **`0xC6372`/`0xC636E`** — candidate #2, `alpha = 205/1024` ⇒ only **−1.29 dB at 21 Hz**, never flashed
   (V44 pins them as "the rejected candidate B"). 🛑 **Needs its own GATE 2 pass**: `gp-0x6bbe` is base
   power steering and 60-73° of added assist-loop lag is the **V48B brick class**.
3. **Build the `0xC646C` decoupling** as the correctness fix.
4. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — still does not reconcile.

🛑 **No openpilot-side modifications** (standing instruction). 🛑 **Flash only on explicit operator
instruction naming the file and the bus.**

---

## 9. Collaterals updated

- `docs/STATE.md` — rewritten in place: V55 on the car with its measured result; workstream A rewritten
  around the internal-loop finding; V56 as the flash candidate; next steps renumbered; four new
  corrections of record.
- `docs/BUILD-LINEAGE.md` — V43/V46/V48A re-framed as one-branch-of-three; V52C's null downgraded with
  its arithmetic; `0xC6AF0` row updated to BUILT; `0xC6372`/`0xC636E` added; the `0xC646C` elimination
  boxed with its Python; V55/V56 added to Parts 3 and 4.
- `analysis-2020accord/model/eps_lkas_chain_model.py` — V55 block rewritten with the measured result; **V56
  added** with a new `resonance_lane_output_bound_q15` field wired into the aggregator. Suite exits 0.
- `analysis-2020accord/builds/v50_v79/build_v56_tva.py` — new.
- `memory/` — 5 new files + `MEMORY.md` pointers; `reference/firmware/reference-accord-c646c-shared-gain-not-lkas-only.md`
  corrected in place.
