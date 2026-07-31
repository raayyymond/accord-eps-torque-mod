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

## ⚠⚠ SEPARATE THE TWO CLAIMS — one is solid, one is provisional (flagged 2026-07-31)

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
