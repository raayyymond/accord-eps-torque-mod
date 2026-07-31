# ★★ RTOS task 5 is 100 Hz — so the base-assist DAMPER structurally cannot damp the 20.9 Hz mode

**Resolved 2026-07-31. Closes `STATE.md`'s open gate #1, which had been "UNRESOLVED" since V59.**

## The rate table, verified two ways

`FUN_00014be4` is a mod-100 rate divider on the 1 kHz tick (counter `gp-0x4304`), decompiled fresh:

```c
if (99 < counter) counter = 0;                    // gp-0x4304 wraps at 100
FUN_000861e0(0);                                  // idx 0 -> every tick
if (counter & 1)        FUN_000861e0(1);          // idx 1
if (counter % 5 == 2)   FUN_000861e0(3);          // idx 3
if (counter % 10 == 4)  FUN_000861e0(4,10,c/10);  // idx 4   <<< task 5
if (counter == 0x10)    FUN_000861e0(5);          // idx 5
counter++;
```

The argument is a **0-based TCB slot index**, not an abstract group ID. Proof (orchestrator's own byte
read): `tp-0x3814` = `0xBB7EC` = **`0x000BB920`**, and `idx*0x30 + 0xBB920` reproduces all seven task
entry points at `+0x08` exactly — `0x2214A`, `0x22A88`, `0x22B20`, `0x22B24`, **`0x22CA0`**, `0x2351E`,
`0x14C5C`.

| idx | task | contains | rate |
|---|---|---|---|
| 0 | `FUN_0002214A` | arb, `FUN_0003b66a`, aggregator `FUN_0003aa2c`, governor, shaper | **1000 Hz** |
| 1 | `FUN_00022A88` | — | 500 Hz |
| 3 | `FUN_00022B24` | — | 200 Hz |
| **4** | **`FUN_00022CA0`** | **boost `FUN_00034a72` + damping `FUN_00034350`** | **100 Hz** |
| 5 | `FUN_0002351E` | — | 10 Hz |

Self-consistent: idx 0 every tick independently reproduces the recorded 1 kHz anchor for task 1.

## ★★ Why this matters most: a 100 Hz damper cannot damp a 20.9 Hz mode

`gp-0x6bd0` is velocity-proportional damping, sign forced to `-sign(gp-0x6abe)` @`0x3469e-0x346a2` —
correct by construction. **But damping only works when the force is in phase with velocity.** A
zero-order hold at 100 Hz costs `360 · f · T` of transport lag before any plant phase:

```python
f, T = 20.9, 1/100.0
360*f*(T/2)   # = 37.6 deg   average ZOH lag
360*f*T       # = 75.2 deg   worst case
```

⇒ **A structural explanation for why EVERY damper lever was null — V44 (FactorC alone) and V47
(FactorC + FactorE *together*, byte-verified as a genuine simultaneous test) — that does NOT depend on
the FactorC speed-axis argument.** Even with both deadzones fully opened, the damper is too slow to act
on this mode, and at 38–75° of lag it may be *anti*-damping at 21 Hz rather than merely ineffective.

⚠ This is also a candidate explanation for why the "damping sign" question flip-flopped across four
sessions: a term whose sign is correct by construction can still act with the wrong phase if it is
refreshed 10× slower than the mode it is aimed at.

## Second consequence: the V59 eps table was computed at the wrong rate

V59's parametric-pump eps table bracketed **1 kHz and 500 Hz** for task 5. Both are wrong. The
boost-amplitude LERPs are evaluated at **100 Hz**, so a 42 Hz index modulation is sampled ~2.4× per
cycle — barely above Nyquist and heavily ZOH-attenuated. **The pump could barely act at all.** That is
an independent *structural* reason for V60's null, on top of the empirical one.
(`gp-0x6ba6` itself is written by `FUN_0003b66a` in task 1 at 1 kHz; it is the *consumer* that is slow.)

## 🛑 The rule that follows

**Any fix acting through boost or damping is fighting 38–75° of architectural lag at the mode
frequency. Prefer task 1 (1 kHz)** — arbitration, `FUN_0003b66a`, the aggregator, the governor and the
shaper all live there. V61's edit (`FUN_0003aa2c`, called at `0x2291e`) is in task 1, on the right side
of this. **Any future task-5 change must carry this in its GATE 2.**

Related: [[accord-v60-null-closes-parametric-pump]], [[accord-v59-parametric-pump-marginal]],
[[reference-accord-damper-two-deadzones-factorC-factorE]],
[[reference-accord-collocation-motor-rate-damper-dead]].

## ✅ AUDIT RESOLVED 2026-07-31 — the NUMBER survives, the REASON was wrong

A datasheet-grounded clock audit (operator-instructed) **refuted two of the kit's standing figures**
and left this file's conclusion standing on a different, better foundation.

🛑 **PCLK = 40 MHz, not 80.** The likely original error is conflating **HEAPCLK** (80 MHz) with
**PCLK**: option-byte Table 6-7 makes `PCLK = HEAPCLK/2` the *only legal* setting at HEAPCLK = 80 MHz.
HEAPCLK = 80 MHz is pinned by the firmware's own CLMA1 compare values — **orchestrator-verified in the
stock dump**: literal `0x0053` @`0x5C8D8` and `0x004D` @`0x5C8E0`, written to base `0xFF80` offsets
`0x300C`/`0x3008` = `CLMA1CMPH`/`CLMA1CMPL`, an exact match to the datasheet's own worked row for
CLMA1 @ 80 MHz with a 16 MHz main oscillator. (Three CLMA blocks exist: CLMA0 `0x4E`/`0x34`,
CLMA1 `0x53`/`0x4D`, CLMA2 `0x28`/`0x19`.)
⚠ A second CAN-bit-timing chain was offered as corroboration. **It is NOT independent confirmation** —
the orchestrator could not reproduce its field decode. `FCN0CMBTCTL` = `0x030A`; whether `TS2LG` is a
3-bit or 4-bit field flips DBT between 8 and 16 TQ and the answer between **40 and 80 MHz exactly**.
The 3-bit reading gives a 62.5% sample point (plausible) vs 31.25% (implausible for automotive CAN),
which favours it — but that is a plausibility argument, not a datasheet field reading. **Treat CLMA1 as
the load-bearing chain.**

🛑🛑 **OSTM0 IS NOT THE RTOS TICK — it never was.** `OSTM0CMP+1` = 80000 counts at 40 MHz = **2.000 ms
= 500 Hz**, but that is irrelevant: **orchestrator-verified** by decompiling the EI trampoline
`FUN_0001492a`, which dispatches only EIIC `0x970/0x600/0x340/0x470/0x110/0x100/0xf0` + default —
**no OSTM0 arm exists**, and `gp-0x42fc`, the rate divider's trigger flag, is written **only** by the
`0x340` arm. `EIIC 0x340` = **TAUJ1I2**. ⇒ the whole *"OSTMnCMP = 79999 ⇒ 1 kHz control tick"* chain
this kit carried for months was a **red herring at both ends** — wrong clock AND wrong timer.

⚠ **TAUJ1's own period register was NOT located** (`search_instructions` returned nothing for
`TAUJ1CDR2` @`0xFFFFC308`; a raw LE byte scan past that tool's known blind spot is the next step).
**So the base rate is still not pinned to any register value.**

✅ **BUT THE CONCLUSION SURVIVES INTACT**, because it never depended on that chain: **task 1 = 1 kHz is
an ON-CAR MEASUREMENT** (the `STEER_STATUS=4` dwell, cal `0xC64DF` = 100 counts, measured at 100.00 ms
⇒ 1.000 ms/decrement; and CAN 399 wire-fitted at exactly 100.000 Hz), and **task 5 = task 1 / 10 is
integer arithmetic**. Neither reads a clock register. ⇒ **100 Hz and 37.6°/75.2° stand as written.**

⚠ **What DOES propagate: the FOC/PWM carrier.** The recorded "~8 kHz" was computed explicitly
*conditioned on PCLK = 80 MHz*. At 40 MHz it is **~4 kHz** — and TSG20's own clock-select register has
never been verified, so treat both numbers as open. This bounds what the actuator can do at 20.9 Hz.
⚠ Also corrected: `EIIC 0x600` is **`CSIH1IR` (serial)**, not ADC-complete, and `EIIC 0x970` is
**`TSG21I05`**, not TSG20 (`TSG20I05` is `0x860`).

🛑 **PROCESS FAILURE WORTH ITS OWN NOTE: this had already been found and recorded once**, in the
tracer's agent-memory (`reference_accord_pclk_40mhz_and_ostm0_is_500hz.md`), and **never propagated to
`docs/` or the golden model**, which went on citing 80 MHz / 1 kHz / OSTM0. Same family as
[[accord-a-caveat-can-mutate-into-a-result]]: a correct finding is worthless if it lives only where
nobody reads it. **Agent-memory findings that correct a main-doc figure must be promoted the same day.**

## (superseded) The provisional flag that prompted the audit

**SOLID and clock-independent: the DIVIDER RATIO.** Task 5 fires once per **10** task-1 invocations.
That is integer arithmetic in `FUN_00014be4` and holds whatever the clock turns out to be. So *"the
damper is refreshed 10× slower than the 1 kHz chain that feeds it"* stands unconditionally, and so does
the qualitative conclusion that a fix should prefer task 1.

⚠ **CLOCK-DEPENDENT: every ABSOLUTE Hz, and therefore every DEGREE above.** The 1 kHz base tick rests on
`OSTM0CMP = 79999` **and an assumed PCLK = 80 MHz** — and that 80 MHz was **never read from the
datasheet.** The kit derived it by elimination: *"PCLK is one of {48, 64, 80, 160} MHz per
`DFLASH.DCLKWAIT`; only 80 MHz gives a clean ~1 ms."* **That is circular** — it assumes the 1 ms answer
in order to pick the clock that produces it.

| assumed PCLK | base tick | task 5 | ZOH lag at 20.9 Hz (avg / worst) |
|---|---|---|---|
| 48 MHz | 1.67 ms | 60 Hz | 62.7° / 125.4° |
| 80 MHz (kit's figure) | 1.00 ms | 100 Hz | **37.6° / 75.2°** |
| 160 MHz | 0.50 ms | 200 Hz | 18.8° / 37.6° |

⇒ **Treat 37.6° / 75.2° as PROVISIONAL.** A datasheet-grounded audit of the full clock tree (SVD
`UPD70F3508_V850E2Px4.svd` as the only source of truth) is running at operator instruction. The on-car
**100.000 Hz** CAN cadence (`0x14A`/`0x18F` measured at 99.999–100.008 Hz across whole drives) is an
independent anchor the audit must reproduce. Note the damper conclusion survives at 48 and 80 MHz and
weakens considerably at 160.
