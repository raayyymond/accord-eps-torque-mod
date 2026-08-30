# CAVE SPECS — the two instruments the remaining questions need

**Nothing here is built. This is a specification, written so the decision is informed rather than
improvised.** Code caves are this kit's **only bricking class** — V24, V27 and V48B all bricked the
ECU — so cutting either of these is the operator's call, not an agent's.

Two questions survive the calibration search, and both need an instrument rather than a lever:

| question | why it is stuck | instrument |
|---|---|---|
| **Is the frame sign such that r24 damps or pumps?** | rectified on every bus channel — verified across `r7e`/`r80`/`r81`/`r82` | **one sign bit** |
| **What is in 52–71 Hz, which aliases into the scored 30–49 Hz band?** | the fold source sits **above Nyquist** (fs ≈ 101 Hz) — it can be neither seen nor filtered | **a 1 kHz zero-crossing counter** |

**They are not equally risky, and that is the main thing this document exists to say.**

---

## Shared budget

- **Free CAN bits: 7.** `0x14A` byte4 `[7:3]` (5) + byte7 `[7:6]` (2). The gateway is a **whitelist** —
  only `0x14A`/`0x18F`/`0x1AB` cross, so a new ID can never reach openpilot. The checksum is computed
  last, so spare bits are auto-covered.
- **Proven hook: `0x55C0E`**, the `0x14A` cave call site, **100 Hz**, in place since V31p.
- **Proven patterns:** V70 flew a 4-bit sign probe; V88's `b7` carried a sign at 100 Hz. Both fine.

---

## CAVE A — the frame sign bit  ·  **LOW RISK, proven site and pattern**

**Question:** does r24's output reach the motor with the same sign as `cs_rate`? That single bit decides
whether every work-factor conclusion in `STATE.md` reads as damping or pumping.

**Design.** One bit: `sign(r24_output)` sampled at the existing 100 Hz hook. The ratchet is 7.79 Hz, so
100 Hz gives **12.8 samples/cycle** — ample; Nyquist is 50 Hz.

🛑 **The design law says a sign bit alone is not enough** — *"every probe that DECIDED something was a
SIGN BIT PAIRED WITH A MAGNITUDE CHANNEL, or a deliberately-designed CONTROL."* So:

| bit | carries | why |
|---|---|---|
| b7 | `sign(r24)` | the answer |
| b6 | `sign(cs_rate)` **as the firmware sees it** | the **pairing** — b7⊕b6 is the work-factor sign directly, with no cross-channel convention to get wrong |
| b5 | `\|r24\| ≥ 256` | the magnitude channel, so a null can be distinguished from a dead lane |
| b4 | the lane's **enable** state | *"probe the gate and the input, not just the output"* — the V64/V68/V92 failure |

**The sentence a null licenses, written in advance:** if **b5 duty is 0** the lane never reached 256
counts and the drive says nothing about the sign — that is an **instrument** result, not a physics one.
If **b5 fires and b7⊕b6 has a stable duty**, the frame is settled and every absolute damping/pumping
claim in the record resolves at once.

⭐ **Why this one is cheap:** it reuses the existing hook, needs no new timing, and both prior sign
probes flew without incident.

---

## CAVE B — the >50 Hz counter  ·  **HIGH RISK, needs a SECOND hook in task 1**

**Question:** the scored 30–49 Hz band is contaminated by 52–71 Hz folding down. Both current builds
raise that region (V222 passes **3.76×** more than the car), so the band is uninterpretable across the
boundary — and *no* bus channel can fix that, because the source is above Nyquist.

**Why it cannot use the proven site.** A counter must **accumulate** in a 1 kHz context. `0x55C0E` runs
at **100 Hz**, so it can only *read out* a value something else maintains. Nothing at 1 kHz currently
maintains one.

⇒ **CAVE B REQUIRES TWO HOOKS:** one new hook inside **task 1 (1 kHz)** to count zero crossings of the
band-limited signal, plus the existing 100 Hz hook to report the accumulated count. **A new hook in the
1 kHz control task is exactly the edit class that bricked V24, V27 and V48B.**

**Budget if ever cut:** 4 bits for a count reported per 100 Hz frame (0–15 crossings ⇒ 0–75 Hz
observable, which covers 52–71 Hz), plus b4 as an overflow/liveness flag. Both **GATE 1 (RAM ownership,
including register-indirect writers)** and **GATE 2 (closed-loop stability, magnitude *and* phase)**
apply in full, and `gp-0x1500` is the recorded case of a cell passing both static methods and still
failing on-car.

🛑 **RECOMMENDATION: do not cut Cave B.** Its question is real but it buys one band's
interpretability at the kit's highest risk class. **Cave A answers a question that re-prices the whole
record, at a fraction of the risk.** If only one is ever cut, it should be A.

---

## What neither cave changes

Neither is needed to fly V228 or V222. The flight decision rests on the operator's symptom verdict and
the pre-registered band tests, both of which work today. These instruments would settle *why*, not
*whether*.
