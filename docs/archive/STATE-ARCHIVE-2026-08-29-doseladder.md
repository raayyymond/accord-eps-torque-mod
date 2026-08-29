# STATE archive — superseded during the dose-ladder iteration

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑 **THE SIGN-AGREEMENT GATE IS DORMANT WHEN ENGAGED — LEAD CLOSED, TWO SELF-CORRECTIONS**
Last turn I flagged a sign-agreement gate on the LKAS command path as the best-shaped symptom-B
mechanism, marked the behavioural reading **BELIEF**, and said *"read all of `FUN_00028ea6` before
proposing anything."* Done. **The lead collapses, exactly where it was flagged.**

### ✅ WHAT THE FULL DECOMPILE SHOWS — the test is NESTED INSIDE AN ENABLE GATE
```c
   if ((cVar15 == '\x01') && (*(char *)(unaff_gp + -0x6806) == '\0')) {    // <-- ENABLE GATE
       if ( (deadband test on cal(0xC61B8)) || (iVar34 * *(short *)(gp - 0x6b30) < 1) ) {
           iVar23 = 0;  goto LAB_0002a1ee;                                  // zero the command
       }
   }
   iVar23 = (int)(short)((int)(iVar34 * uVar18) >> 0xf);                     // otherwise pass
   LAB_0002a1ee:
   ...
   *(short *)(unaff_gp + -0x6b30) = (short)iVar23;                           // stores the OUTPUT
```
with `cVar15 = *(char *)(unaff_tp + 0x74a3)` = **`cal(0xC64A3)`**.

### 🛑 SELF-CORRECTION 1 — THERE **IS** A CAL ON THE GATE
I wrote *"no cal on the gate — `mul`+`cmp`+`bgt`, hard-coded."* **Wrong.** `0xC64A3` is a byte
enable on the whole block. **But it is `1` in stock and in ALL 155 build images**, so it is not a
free lever and disabling it is untested territory.

### ⭐ SELF-CORRECTION 2 — THE GATE IS **DORMANT WHEN ENGAGED**, PROVED BEHAVIOURALLY
With `cal(0xC64A3)` permanently 1, the gate's activity rests entirely on **`gp-0x6806 == 0`**
(37 loads / 20 stores — a state-machine flag in the `0x29xxx` region).
**The latch reading I flagged is CORRECT, and that is exactly what closes the lead:**
```
   the block stores iVar23 back to gp-0x6b30, so once the command is zeroed,
   prev = 0  =>  iVar34 * 0 = 0 < 1  =>  the test fires AGAIN  =>  a SELF-HOLDING ZERO
```
⇒ **if this gate were active while engaged, the FIRST zero-crossing of the command would latch
LKAS at zero PERMANENTLY.** It demonstrably does not — the operator steers on LKAS every drive.
⇒ **[EVIDENCE, behavioural] `gp-0x6806 ≠ 0` whenever LKAS is steering ⇒ the deadband and the
sign-agreement test are BOTH INACTIVE WHEN ENGAGED.**
⇒ **THE SIGN GATE IS NOT SYMPTOM B'S SOURCE. LEAD CLOSED.**
⊕ It also independently re-confirms [[reference-accord-pregain-deadband-c61b8]] — the 102-count
pre-gain deadband sits in this same dormant block, which is *why* it was filed ELIMINATED.

### 🛑 WHAT THIS IMPLIES FOR SYMPTOM B — AND IT IS NOT ENCOURAGING
The engaged LKAS forward path is now traced end to end with **no switching nonlinearity active**:
```
   command -> [deadband + sign gate: DORMANT when engaged] -> x gain -> x polarity -> >>15
           -> clamp cal(0xC61B4) (record: INERT) -> gp-0x6b30
```
⇒ **no discontinuity, no relay, no slew limit on the engaged command path.**
⇒ the gain-laddered broadband excess (**1× −0.04 · 4× 0.84 · 6× 1.13 · 8× 2.24 dB**) therefore
does **not** originate in a command-path discontinuity.
⇒ **[BELIEF, and the honest reading] what remains is the motor/inverter being driven harder** —
current ripple and commutation noise rising with command amplitude, with a superlinear acoustic
response giving the observed **m^1.74**. **That is physics, not a defect, and no cal reaches it
except the LKAS gain, which is frozen in both directions.**
⇒ **🛑 SYMPTOM B MAY BE IRREDUCIBLE IN FIRMWARE.** Stating it plainly is more useful than
generating another build that cannot touch it. **If that is wrong, the disproof would be a broadband
source that is engagement-conditional and NOT proportional to command amplitude — none has been
found in the forward path.**

## ⭐⭐ **A SIGN-AGREEMENT GATE SITS DIRECTLY ON THE LKAS COMMAND PATH — UPSTREAM OF THE GAIN**
Chasing symptom B's broadband source into the forward path found a **hard switching nonlinearity on
the LKAS command itself.** Disassembled from `0x2A1C0`; the region is **structurally identical to
V122** (only the 2 gain-cal bytes at `0x2A1F0-1` differ, `746c`→`7cd0`), so this reads true for the
flying build.
```asm
   0x2a1ca  ld.hu 0x71b8, tp, r8      ; cal(0xC61B8) = the pre-gain DEADBAND (102)
   0x2a1ce  subr  r0, r8              ; -deadband
   0x2a1d0  cmp   r8, r9
   0x2a1d2  bge   0x2a1e2             ; inside the deadband -> ZERO
   0x2a1d4  ld.h  -0x6b30, gp, r13    ; the PREVIOUS stored output
   0x2a1d8  mov   r9, r6
   0x2a1da  mul   r13, r6, r0         ; r6 = prev x current
   0x2a1de  cmp   r0, r6
   0x2a1e0  bgt   0x2a1e6             ; product > 0  -> pass through
   0x2a1e2  mov   0x0, r9             ; ELSE -> FORCE THE COMMAND TO ZERO
   0x2a1e6  mul   r14, r9, r0  / sar 0xf / sxh
   0x2a1ee  ld.h  <gain>, tp, r7      ; 0xC6CD0 on V122, 0xC646C on stock (V57 moved it)
   0x2a206  st.h  r9, -0x6b30, gp     ; stored back -> becomes next tick's `prev`
```
⇒ **[EVIDENCE] the LKAS command is FORCED TO ZERO whenever its sign disagrees with the previous
output's sign.** A signal zeroed on sign disagreement has **step discontinuities**, which is
precisely a broadband generator.
⇒ **⭐ AND THE GATE IS UPSTREAM OF THE GAIN MULTIPLY** (`0x2a1e2` precedes `0x2a1ee`), so the
**discontinuity amplitude scales with the gain** ⇒ **broadband ∝ gain**, which is the shape symptom B
shows (measured ladder 1× −0.04 · 4× 0.84 · 6× 1.13 · 8× 2.24 dB).
⊕ It is **engagement-conditional by construction** — there is no LKAS command when disengaged —
matching *stock does not fire, we do.*

### 🛑 WHAT I WILL NOT ASSERT — AND WHY NOBODY SHOULD BUILD ON THIS YET
**[UNRESOLVED] it READS as though it could latch.** If `prev` ever becomes 0 then `prev × current`
is 0, which fails the strict `> 0` test, forcing 0 again — a self-holding zero. **LKAS demonstrably
works**, so one of these must be true and I have not established which:
```
   (a) the SECOND store to gp-0x6b30 at 0x2A900 resets it on another path   (2 stores exist)
   (b) r14 / r6 are not what this 48-byte window implies
   (c) an entry branch (0x2a1c8 bgt -> 0x2a1d4) bypasses the deadband leg and changes the state
```
🛑 **Read the WHOLE of `FUN_00028ea6` before proposing anything here.** This is exactly the
*decompile-first* rule: I formed this claim from a 48-byte assembly window, which is the method the
kit has recorded as its most expensive mistake generator. **The instruction sequence is EVIDENCE;
the behavioural reading is BELIEF.**

### ⚠ AND THERE IS NO CAL ON THE GATE ITSELF
The sign test is `mul` + `cmp r0` + `bgt` — **hard-coded, no calibration operand.** Only the
**deadband** `0xC61B8` = 102 gates entry, and the record already files it
([[reference-accord-pregain-deadband-c61b8]], *"ELIMINATED — fixed 102-count deadband"*).
⇒ **removing or softening the sign gate would be an in-place instruction edit** — the class that
bricked V24, V27 and V48B — **and it is NOT proposed.**
⇒ **[NEXT STEP, cheap and safe] read `FUN_00028ea6` in full and settle the latching question.**
If it does not latch, this is the best-shaped symptom-B mechanism found so far; if it does, my
reading is wrong and the finding collapses.

### ✅ AND `0xC6194` IS CLOSED AS A SYMPTOM-B LEVER
`FUN_00026c80`'s **only caller is `FUN_0002214a` = TASK 1, the confirmed 1 kHz task.**
⇒ `cal(0xC6194)` = 3 counts/tick at **1 kHz** = 3000 counts/s, against a state clamped at
±cal(`0xC6192`)=2048 / ±cal(`0xC6198`)=3072 ⇒ **full-scale slew ≈ 2 s.**
⇒ **that path is ALREADY heavily smoothed and cannot be a broadband source. CLOSED.**
⊕ **This also softens my flag from last turn**: the memory's operative claim is *"no live
**LKAS-specific** slew limit"*, and this limit is on the **assist-arbitration sum**, not the LKAS
command ⇒ **the memory's claim stands**; only its *"output ×0"* phrasing mismatches the code.

## 🛑🛑 **GHIDRA'S `code.bin` IS THE *STOCK* IMAGE — EVERY DECOMPILE THIS SESSION WAS OF STOCK**
Chasing symptom B I hit a Python-vs-Ghidra disagreement and adjudicated it. **Both tools were
right; they were reading different images.**
```
   at 0x2A1EE:   Ghidra says  ld.h 0x746c, tp, r7   ->  tp+0x746C = 0xC646C
                 V122 bytes   25 3f d0 7c           ->  tp+0x7CD0 = 0xC6CD0
```
⇒ Ghidra's loaded program is `.../ghidra_project/code.bin`, **the STOCK dump** — and stock reads
`0xC646C` because **V57 is exactly the build that decoupled the forward reader onto `0xC6CD0`.**
The record predicted this ([[reference-accord-c646c-shared-gain-not-lkas-only]]); the tools agreed
all along.
✅ **THE SCAN METHOD IS VINDICATED** — the `reg1 == tp` filter reproduced the lineage's
independently-recorded *"sole reader `ld.hu 0x73ac,tp,r13` @`0x38202`"* for `0xC63AC`, and here it
read the V122 byte correctly where the stale program did not.

### ✅ WHICH OF THIS SESSION'S DECOMPILES SURVIVE — CHECKED, NOT ASSUMED
```
   FUN_0003b8f6  the PLANT MODEL   0x3B8F6-0x3BC30   IDENTICAL stock vs V122  (0 bytes)  VALID
   FUN_00038148  the ACTUAL arm    0x38148-0x38400   IDENTICAL stock vs V122  (0 bytes)  VALID
   FUN_0003aa2c  the AGGREGATOR    0x3AA2C-0x3AC60   DIFFERS   (1 byte  -- Lever B 0x3AA96)
   FUN_000352b4  the NOTCH         0x352B4-0x35C00   DIFFERS   (4 bytes)
```
⇒ **the two functions this session's structural conclusions rest on are byte-identical**, so the
`|model| × sat(angle)` correction and the signum-relay refutation **both stand.**
🛑 **STANDING RULE, ADD TO THE DECOMPILE SKILL: Ghidra holds STOCK. Before trusting any decompile
for a BUILD, diff that function's byte extent stock-vs-target in Python.** A cal that moved between
stock and the target (V57's `0xC646C`→`0xC6CD0`, V88's `0x3AA96`) will silently read wrong.

