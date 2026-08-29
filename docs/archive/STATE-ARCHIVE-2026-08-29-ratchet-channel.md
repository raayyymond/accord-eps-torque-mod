# STATE archive — superseded during the ratchet-channel work

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑🛑 **V149 SUPERSEDED — IT REMOVES LEVER B, THE KIT'S ONLY MEASURED GRINDING FIX**
The queue audit against the golden model reaches V149, and this is the worst of the four errors.

### 🛑 MY PREMISE FOR V149 WAS WRONG
I built V149 to *"remove the 5.12x r24 switch"*, describing it as **a fault counter (`gp-0x671d`)
selecting between `cal(0xC6446)=5244` and `cal(0xC6442)=1024` at task rate** — a switching
nonlinearity inside a confirmed pump. **The selector is not a fault counter.**
```
   0x3AA96   stock c5 -> V122 fb     ld.bu -0x683c[gp]  ->  ld.bu -0x6806[gp]
                                     i.e. the flag is gp-0x6806 = LKAS CONTROL ACTIVE
   0xC6446   stock 512 -> V122 5244  the LKAS-gated arm's gain
```
⇒ **the gate is ENGAGEMENT, not a counter.** It toggles on engage/disengage, **not at 1 kHz**.
**There is no task-rate switching nonlinearity here, so V149 has nothing to remove.**

### 🛑🛑 WORSE: 5244 IS THE FIX, AND V149 DELETES IT
The golden model describes this exact pair as **the grind #1 fix**:
> *"**THE FIX: V67 = V66 + the grind #1 fix GATED ON LKAS.** Two edits, no cave: `0x3AA96 c5 -> fb`
> + `0xC6446 512 -> 5244` … its flag `lp` already selects cal `0xC6446` for r24 — **the firmware
> already HAS a conditional-gain arm and it is merely wired to a dead cell.** Repointing it makes the
> gain conditional **with no code cave, this kit's only bricking class.**
> gate FALSE (LKAS off) -> the LERP, unchanged => **byte-for-byte STOCK base steering**
> gate TRUE (LKAS on) -> flat 5244 = **2.00x the LERP at grind #1's operating point**"*

⊕ And the memory record: **V88 = “Lever B restored” is the build that FLEW with “grinding FIXED”**
([[accord-v88-flew-grinding-fixed-command-intact]]), and
[[accord-v81-carries-neither-grind1-fix]] calls Lever B **“best in kit”**.
⇒ **[EVIDENCE] Lever B is ACTIVE on the flying build (`0x3AA96` = `fb`, `0xC6446` = 5244), and
V149 sets 5244 -> 1024, collapsing the gated arm to the ungated value.**
⇒ **V149 REMOVES THE ONLY CHANGE THIS KIT HAS EVER MEASURED AS FIXING GRINDING.**
⇒ **SUPERSEDED. `.rwd` renamed. It must never be flown.**

### ⚠ AND V152/V153 CARRY THE SAME OPEN GATE 2 AS V154/V155
`tp+0x50d0` = **`0xC40D0`** is **one of the eight Path-2 loop-gain coefficients** the golden model
names as *"NEVER BYTE-READ"* and on which **GATE 2 cannot be certified**. **V152/V153 move it.**
⊕ **Their argument is better than V154/V155's**: a *pure added low-pass* lowers HF loop gain, which
is directionally stabilising, whereas a weight change had an **unresolved sign**.
⚠ **But it is still not a certification** — a low-pass also adds phase lag, and phase margin cannot
be checked without the loop gain, which needs the RAM LERP slope that `FUN_000389ec` has defeated
twice.
⇒ **V152/V153 are NOT superseded, but they are DEMOTED and flagged GATE-2-OPEN.** They must not be
flown ahead of V158, whose gate is closed by the model's own priced prescription.

### ✅ THE QUEUE AFTER THE AUDIT
```
   1. V158   damper, the golden model's own prescription      GATE 2 closed by the model     FLY THIS
   2. V139   both pump arms halved                            not yet audited
   3. V150   r26 suppression switch                           premise deserves re-checking after V149
   4. V148   deadband + probe                                 instrument, not a fix
   5. V151   knee 3000 -> 3600                                marginal, relay ~99 % unsaturated
   -  V152 / V153   observer poles                            GATE-2-OPEN, demoted
   X  V149 / V154 / V155 / V156 / V157                        SUPERSEDED
```
🛑 **FIVE of the builds I recommended this session are now superseded, all for the same root
cause: designed from `BUILD-LINEAGE` and my own decompiles instead of the GOLDEN MODEL**, which
`CLAUDE.md` names as required reading and which already contained the structure, the prescription,
the strikes and the fix.

