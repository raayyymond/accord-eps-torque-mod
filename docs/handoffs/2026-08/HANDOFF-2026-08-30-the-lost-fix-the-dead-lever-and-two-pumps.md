# HANDOFF 2026-08-30 — the lost fix, the dead lever, and two parametric pumps

**Nothing flashed. No CAN or UDS message sent.** Both repos clean and pushed.
Everything below was read from the **images**, not the record — and in four places the record was wrong.

---

## 0. 🛑 THE BASELINE: the operator says **V112** is on the car; this kit said V122

Every "vs the car" number computed 2026-08-27 → 08-29 used V122. The whole difference is **three cells**:
`0xC40BC` knee 1800/3000 · `0xC40D2` K1 612/1020 · `0xC40DC` **alpha2 14/8**. All work below is rebased
on **V112**. ⚠ V253's rationale (hold alpha2 at 8 "because the car has 8") collapses if the car is V112,
which runs **14**. Re-flashing a known file settles it.

---

## 1. THE ONLY MEASURED GRINDING FIX HAS BEEN OFF THE CAR SINCE V65

V62 (`sar 0xa`→`sar 0x9` at `0x3AB76`/`0x3AC20`) measured **18–22 Hz down 8×** (42× at |rate| 16–32 °/s)
against a flat 30–40 Hz control, and the operator said *"Original grinding at 2–5 mph is gone!"*

```
  stock                      aa32  aa42   1x Kd
  V62 / V65                  a932  a942   2x Kd   <- the fix
  V70                        aa32  aa42   REVERTED
  V88 V100 V108 V111 V112    aa32  aa42   1x Kd   <- V112 is the car
  V131 V139                  a932  a942   2x Kd   <- restored again
  V122 V241 V251 V254        aa32  aa42   1x Kd   <- lost again
```

`BUILD-LINEAGE-PART1` says *"Restored in V71"*. **The images say it was added and dropped twice.** A
mechanical audit of every flown image vs V112 confirms this is the **only genuine lost lever** — the car
also lacks the notch, FactorC/E and the decoupling, but V112 simply **predates** them.

**Mechanism:** the grinding mode is a lightly-damped **mechanical** resonance (21.4 Hz, **Q = 13.6**),
its `phi'` coefficient is **linear in Kd**, and at Kd = 0 the mode has no damping term at all. Engaged vs
disengaged at matched speed: **9,200× more 21 Hz power engaged**, while the disengaged pool carries 6×
MORE low-frequency energy — the loop closes through the physics, not through firmware.

---

## 2. 🛑 LEVER B IS UNREACHABLE — every measurement of it is of a dead cell

`FUN_0003aa2c` picks the arm before the multiply at `0x3AC18`; the `0xC6446` (Lever B) branch tests
`gp-0x683c`, **which has zero writers**. The record carried this as *"single-method, wants a raw byte
scan"* — **the scan was never run.** Confirmed two ways: `FUN_00052e32` writes every neighbour
(`-0x683b`, `-0x683d`, `-0x683e`, `-0x6832`…`-0x6835`) and **never** `-0x683c`; and a corrected byte-form
scan shows all 14 apparent sites are aliases (🛑 **for byte forms the displacement's bit 0 lives in
`hw1` bit 5, so the opcode is bits 6–10**).

⇒ Voided: the anti-damping census collapses to **the GAIN ALONE**; V88's "bracketed optimum" of 5244;
the `_LEVER_B_LADDER`; and 8.71 units of the calibration-ceiling table. **The live arms** are
`0xC6442`=1024, `0xC6440`=2048, `0xC643E`=1536, plus a **runtime LERP** — all stock in every build.
⚠ The selector threshold `0xC64FA` is read as a **BYTE** = 5, not the 517 a halfword read gives.

---

## 3. THE GAIN/CLAMP CONFOUND — the corpus cannot say which cell owns the ratchet

16 flown builds, gain read from the images: **4× → −55.37 · 6× → −68.49 (the car) · 8× → −84.06**, a
clean monotone 3-dose response at **−6.6 per 1×** (not the −4.4 the kit quoted). But
`clamp = gain × 512 // 891` held **exactly** on all sixteen, so **gain and clamp are perfectly
collinear** and both readings fit every build. They predict **opposite** outcomes for every shelf build,
since all raise the clamp. ⇒ **V256 is the disambiguating experiment** — the first build ever to break
the tracking. ⊕ The `0xC674E` abort rule stays **unfounded**; the 5119 cap is conservatism.

---

## 4. ⭐ TWO PARAMETRIC PUMPS — and the intervention the kit named in 2026-07 was never run

**V59 flew 2026-07-30 and measured one:** the boost index's own spectrum peaks at **42.19 Hz = 2× the
21.09 Hz mode**, prominence **11.10×**, coherence 0.795, 13 disjoint runs, and **absent disengaged**.
The kit then wrote: *"Only an INTERVENTION (flatten the swept range, re-fly) separates drive from echo."*

**It was never built** — V58/V59/V60 studied `0xD28DC`/`0xD2888`, which are **mode slot 10**, and this car
runs **24/26**. The same table-selection trap that made V72/V73 inert.

A mechanical census (`analysis-2020accord/verify/parametric_pump_census.py`, **anchored**: slot 10
resolves to exactly the addresses the record names) then found a **second** pump of the same depth:

```
  eps    table     idx26     Y (engaged)
  0.334  0xCA23C   0xD78A4   [16384,14393,10269,8997,..]   AMP4  <- what V59 measured
  0.334  0xCA4F4   0xD78F8   [16384,14658,11676,9362,..]   AMP1  <- what V59 measured
  0.333  0xCBF5C   0xD7A88   [3072, 3072, 2322, 1536]      the RATE-LANE gain surface
```

🛑 **V263 was superseded by this.** It multiplied that surface by 2 — and a uniform scale leaves the
ratio `Ymin/Ymax` untouched, so it leaves the parametric depth **exactly as it was**, while raising
low-rate gain the operator did not want raised.

⚠ Census caveat, written into the tool: **eps only means "pump" for a MULTIPLICATIVE gain curve.** The
`Y[0]==0` rows are ADDITIVE torque curves (FactorC, FactorE) scoring 1.000 purely because Ymin = 0 —
an artefact, not a deep pump.

⚠ A follow-up attempt to map every census table to its consuming function **did not converge**: the
accesses are register-indirect (`iVar10 + tp + 0xd214`), which an operand scan structurally cannot see.
The known consumers stand from the decompiles; the rest are unattributed.

---

## 5. THE V112 SHELF — nine builds, all verified, all unflashed

```
  build  pay  Kd   gain  clamp  epsSURF  epsBOOST  no-code  targets
  CAR      0  1x   5346   3072    0.333     0.334      --   --
  V255     2  2x   5346   3072    0.333     0.334      no   grinding, 1 variable
  V256     4  2x   5346   4096    0.333     0.334      no   +authority DISAMBIGUATOR
  V258     6  2x   3564   4096    0.333     0.334      no   all four, frontier
  V259    15  2x   3564   4096    0.333     0.334      no   max ratchet (~31 %)
  V261     5  2x   5346   3072    0.333     0.334      no   + cal arms 2x
  V262     2  4x   5346   3072    0.333     0.334      no   rate lane 4x
  V264    16  1x   5346   3072    0.333     -> 0       yes  boost pump -> 0
  V265    13  1x   5346   3072    -> 0      0.334      yes  surface pump -> 0
  V266    29  1x   5346   3072    -> 0      -> 0       yes  BOTH pumps -> 0
```
*(epsBOOST "→ 0" is over **[0, 2048]**, where V59 measured **99.96 %** of frames. Over the full curve it
reads 0.295, the residual being a tail seeing 0.04 % of frames.)*

**Every mode-24 MANUAL record is byte-identical in all nine**, and V264/V265/V266 change **no code byte** —
gain, clamps, `sar` and all three live cal arms stock. ⚠ **SUPERSEDED-DO-NOT-FLASH:** V260 (dosed only
one of the two lanes) · V263 (pump unchanged). V257 is dominated — the worst of the twelve winning
(gain, clamp) configurations.

**THE TWO HYPOTHESES, and which build tests each:**

| mechanism | builds |
|---|---|
| too little damping | **V255** (2×, flight history) · V262 (4×) |
| parametric pumping at 2f | V264 (boost) · V265 (surface) · **V266 (both)** |
| ratchet / authority | **V256** (disambiguator) · V258 (frontier) |

⊕ **PRE-REGISTERED, FREE:** a flat gain cannot pump at **any** frequency, so if the parametric route is
real **V266 should move the ratchet too** (its pump would sit at 2f ≈ 15.6 Hz — a line nobody has looked
for, because V59 was chasing 21 Hz). Grinding **and** ratchet together ⇒ strong evidence for the
parametric route. Grinding only ⇒ the ratchet is a different mechanism. Ratchet only ⇒ the 21 Hz
attribution was wrong.
