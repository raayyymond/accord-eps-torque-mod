# STATE archive — superseded during the ratchet-dependency work

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **V160 BUILT — LEVER B TO ITS INT16 CEILING. THE NEW LEAD BUILD.**
`0xC6446` **5244 -> 6553**, ONE HALFWORD, base = V158. 51/51 assertions, CRC 50/50, **6 differing bytes
= 2 payload + 4 CRC, ZERO unattributed.**
```
   image  5277005735a5b2e42bf38860a7a82d1bed14126207cb376e16d0cf137f921594
   rwd    d512d8142d9f8bf9ff76919d8beb092cea8279d15b58d6535614374d48ea3096
```
### ⭐ WHY THIS LEVER — IT IS THE ONLY ONE MEASURED TO HELP BOTH SYMPTOMS AT ONCE
Lever B is the **r24 derivative-feedback gain used WHEN LKAS IS ENGAGED**:
```
   gain_q10 = <speed x rate LERP surface>
   elif assist_gate_683c != 0:   gain_q10 = 0xC6446      # stock 512 -> Lever B 5244
```
V88 vs V87, **single-variable** (5 changed bytes), speed-matched 2-4 m/s, engaged, unclipped,
episode-bootstrapped:
```
   0.5-3 Hz   1.192 [0.780, 1.812]  NULL   <- peak effective LKAS command, UNTOUCHED
   6-9 Hz     0.859                        <- the ratchet band
   9-12 Hz    0.604 [0.465, 0.943]
   15-22 Hz   0.549 [0.407, 0.844]         <- grind #1's band
```
✅ *"MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING = LESS HF EVERYWHERE, at zero LF cost."*
=> **the only lever in this kit measured to cut BOTH the ratchet band AND the grind band while
leaving the LKAS command statistically untouched** — exactly the operator's standing requirement.
V88 is also the route that flew with **"grinding FIXED"**.

### ⭐ WHY A THIRD DOSE, AND WHY EXACTLY 6553
Across **all 159 build images** `0xC6446` has taken **exactly THREE values**: 512 (stock, 85 builds),
5244 (73 builds, flown), 1024 (V149 only, superseded). **The dose-response has TWO points and the
flown step was 10.24x.** A third has never been tried.
```
   (RATE_CLAMP 5120 x 6553) >> 10 = 32765  <= 32767   fits
   (RATE_CLAMP 5120 x 6554) >> 10 = 32770             OVERFLOWS
```
=> **6553 is the EXACT int16 ceiling**, a 1.2496x increment landing on a hard arithmetic boundary
rather than a guess — small beside the 10.24x step already flown fault-free.

### ✅ WHY IT CANNOT COST LKAS AUTHORITY
**[EVIDENCE]** r24's own rail is +-8192, four 16-bit immediates at `0x3AC42-0x3AC54`, and V160 leaves
all 24 bytes **BYTE-IDENTICAL**. The model's warning is specific: raising the **RAIL** lets a
derivative lane eat the +-10240 aggregator headroom the LKAS command needs — *"the one change in this
path that could REDUCE peak effective LKAS steering."* **We raise the GAIN and leave the RAIL alone,
so that failure mode is STRUCTURALLY UNREACHABLE.** (+) measured: `gp-0x6b94` never comes within 20 %
of its +-10240 clip; and 0.5-3 Hz was NULL across the 10.24x step.
**[EVIDENCE]** `0xC6446` has **exactly ONE reader** — `ld.hu 0x7446[tp], r10` at `0x3AC08` — and
**ZERO writers**, confirmed two ways (a tp scan handling the `hw2=(disp|1)` encoding, which also
reproduced the model's `0xC6440`->`0x3AC12` and `0xC6442`->`0x3ABFE`; and the model's own record).

### ⚠ WHAT IS NOT ESTABLISHED
**[BELIEF]** that the dose-response stays monotone beyond 5244 — **only two points exist**, and V62's
lesson is explicit: *"2x is approximately the OPTIMUM, not a point on a ramp."* 5244 may already be at
or past optimum, so **V160 is a DOSE PROBE as much as a fix.** Mitigation: the step is 1.25x, not 2x.
**[NOTE]** r24 rails at `|col_torque_rate| > 1280` (was 1599); normal driving is 123-839 counts, so it
stays unrailed. **[NOTE]** V160 STACKS on V158's damper — two independent mechanisms, both adding
creep-band damping. If the drive is ambiguous, **V158 alone** and **V151** remain single-lever fallbacks.

### ✅✅ V160's PRECONDITION IS VERIFIED — LEVER B IS ACTUALLY REACHABLE
`0xC6446` is read **only** when `lp != 0`, and on a stock gate byte `lp` derives from `gp-0x683c`,
which has **ZERO writers image-wide** — so on stock that load NEVER EXECUTES and Honda's own 512 in
that cell is dead code. The V67 repoint `0x3AA96 c5 -> fb` rewires it to `gp-0x6806`:
```
   build   0x3AA96              0xC6446   Lever B reachable?
   stock   0xc5 (stock)             512   NO  -- gp-0x683c has 0 writers
   V122    0xfb (repointed)        5244   YES -- gp-0x6806
   V158    0xfb (repointed)        5244   YES
   V160    0xfb (repointed)        6553   YES
```
✅ **[EVIDENCE] the repoint is present on the V160 base, so V160 is NOT inert.**
✅ **[EVIDENCE] the gate is VALIDATED ON-CAR**: `gp-0x6806 != 0` agrees with `latActive` on
**99.90 % (route 29) / 99.94 % (route 28)**, does not drop out during steady engaged holding, and
toggles **three orders of magnitude below** the 21/45 Hz modes ⇒ it cannot parametrically pump.
⭐ **6553 IS CONFIRMED TWICE, INDEPENDENTLY**: it is the int16 overflow bound I derived from
`(5120 x g) >> 10 <= 32767`, **and** it is the ceiling the golden model already recorded for this
cell class (*"1 reader / 0 writers, no float mirror, same CRC block #48 as 0xC6446, ceiling <= 6553"*).

## ⛔⛔ **RETRACTION — "`0xCC214`/`0xCC914` ARE DEAD TABLES" IS WRONG**
`0xCC214` is **LIVE**: it is the **fourth pointer array of gain_B (r24)**, the 100 km/h speed-blend
record set, reached as **`tp+0xD214`** and hard-coded in the instruction stream — which is exactly why
it carries no `mov imm32` literal. My null scanned only `mov imm32` literals and 16-bit
`movhi`+`movea` pairs and **was blind to the long tp-relative form**, the encoding `CLAUDE.md` warns
about. ⚠ **`0xCC914` is therefore UNRESOLVED, not dead** — the question is OPEN again.
⭐ **A NULL IS ONLY AS GOOD AS ITS SCAN'S ENCODING COVERAGE.** Two encoding traps bit in one session:
the `hw2 = (disp | 1)` form (a scan for `hw2 == disp` returns **zero** readers for a cell that has
one), and `disp > 0x7FFF` cannot be a disp16 at all. **Validate any scanner against a cell whose
answer is already known BEFORE trusting its null** — doing so is what caught both.

