---
name: accord-v74-fault-damper-WAS-in-force-mode-lag
description: V74's hard fault fired 2.509 s after disengagement — INSIDE the mode-lag band — so the engaged-column damper edits WERE live; refutes "the edits were not in force" and un-voids k*.
metadata:
  type: project
---

★★★★★ **The V74 bump-fault rlogs (route `61`) REFUTE the 2026-08-06 conclusion that the FactorC/E
damper edits were not in force.** The byte facts stand (mode 24 *is* byte-stock); the **inference**
was wrong. "Disengaged" was taken from the operator's verbal report and silently equated with
"mode 24 is active". It is not the same thing.

**The fault:** route `75604b0a432fdc89_00000061--3b8f2f9278`, seg 12, **t = 732.3872 s**.
`gp-0x67fa` **5 → 8**, `0x1AB` DTC-active 0→1, all three `0x14A` angle fields → `0x7FFF`,
STEER_SENSOR_STATUS 7→4, bus STEER_STATUS 0→7 — **all in ONE 100 Hz transmission**. Exactly **one**
state transition in 760.7 s; state 8 never exits. `0x14A` holds **99.97 Hz** through the 28.3 s tail
⇒ **authority/motor-off latch, not a reset.** Same class as V75's.

**Why the edits were live [EVIDENCE, three ways]:**
1. `bit7` (`gp-0x6bd0 != 0`) = **1 at the fault frame**, continuously for **560 ms** before.
2. Speed **33.29 km/h** (`vEgo`) / 33.13 (wheel speeds) — **below** stock mode-24 FactorC
   `X[0] = 2240 ct = 35.00 km/h`, where the evaluator **hard-clamps to `Y[0]` = 0**
   (disasm `0x3451e` `cmp r13,r7 ; bh 0x34528` not taken ⇒ `0x34522 ld.hu 0x0[r10]` = `Y[0]`), and the
   factor chain is **purely multiplicative** — four back-to-back `mulu`+`shr 0xa` at
   `0x34684`–`0x3469c`, **zero `add`/`or`** ⇒ FactorC = 0 forces the damper to 0, **no additive rescue**.
3. openpilot dropped lateral control **2.509 s** earlier (`latActive`, corroborated by `0x0E4` b2 b7
   at 2.500 s) ⇒ inside the mode-lag band.

⇒ **The ECU was still on the ENGAGED column (mode 26, `C_Y0` = 429).** At 2130 ct mode 26 gives 429,
mode 24 gives a hard 0.

★ **Negative control, replicated on two routes of the same build.** Manual `bit7` fires **only**
inside a ~4 s post-disengage tail and is **hard zero beyond it**:

| time since disengage | route 61 | route 5d |
|---|---|---|
| 0–1 s | 28.4% | 44.9% |
| 1–2 s | 18.3% | 41.6% |
| 2–3 s | 20.4% | 12.6% |
| 3–4 s | 3.0% | 6.7% |
| **4–6 s** | **0.000%** | **0.000%** |
| **> 6 s** | **0 of 9,286** | **0 of 39,794** |

**49,080 true-manual frames across two routes with zero damper activity.**
⊕ The apparent counter-example dissolves: route 61's three manual episodes read 0.00% / 61.5% / 70.3%,
but the **0.00% one — which *crosses* the 35 km/h knee — had never been engaged at all**, so its
time-since-disengage is infinite. Ordered by that variable they agree exactly.
⚠ **Do NOT use the 5 km/h speed-bucket table over manual frames** — n = 3 episodes;
[[feedback-episodes-not-windows]] applies. The fault-frame fact stands alone without it.

🛑 **CONSEQUENCE: `k*` is NOT void — but no dose bracket survives either.** Both hard faults now
occurred with the damper live, and **V74 faulted at k = 0.5799**, so nothing derived from "V74 flew
clean" holds. V74 flew 1,012 s clean on route 5d and 732 s on route 61 before faulting ⇒ **a trigger,
not a threshold.** See [[accord-both-faults-fired-at-max-angle-rate-slew]].

⚠ **HONEST GAP — the ROM mechanism for the multi-second hold is NOT pinned.** Mode cell is
**`gp+0x63fd`** (abs `0xFEDFE3FD`), rewritten every 100 Hz task-5 tick by `FUN_00042746` (sole caller
`FUN_00022ca0`), gated `(1 << (gp-0x67fa & 0xF)) & 0x30` = states {4,5}. The only real debounce found
is `0xC624E` = **40** → 40 ms at 1 kHz (~150 ms with ramp-settle) — **not 2.5 s.** The candidate is the
`gp-0x6733 == −1` "transitioning" sentinel written by `FUN_000527da`, which blocks the reselect from
even arming, but that function's callers resolve to **null** under both `get_function_callers` and
`get_xrefs_to` (register-indirect/RTOS dispatch). **Closeable only with a live probe on `gp+0x63fd`
across a disengage — bytes alone will not get the number.**

🛑🛑 **THE DURABLE RULE THIS PRODUCES:** *"the operator was in manual, therefore the engaged-column
edits were not in force"* is **UNSOUND**. Bus-side disengagement does **not** mean mode 24 is active;
the column lags by seconds. This exact inference produced a wrong **EVIDENCE-marked** conclusion in
one session and voided a real result. Check time-since-disengage before ever reasoning from mode.

Related: [[reference-accord-car-is-tvca4-mode-24-26]] · [[accord-damper-is-mode-table-selected]] ·
[[accord-v74-null-is-on-the-gate]] · [[feedback-verify-the-crux-yourself-it-caught-four-errors]]
