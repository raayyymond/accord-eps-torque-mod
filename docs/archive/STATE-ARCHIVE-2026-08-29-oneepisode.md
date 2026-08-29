# STATE archive — superseded during the one-episode spec work

A RECORD, NOT AN INSTRUCTION.

## ✅ **THE AUDIT IS COMPLETE — V150 IS INERT HANDS-OFF, AND THE QUEUE IS FINAL**
V150 was the last unaudited build. Its structure checks out against the golden model, **but its
effect lands outside the symptom's regime.**

### ✅ THE STRUCTURE IS RIGHT
The model confirms the gate exactly as V150's builder describes it:
> *"a hard zero-force gate (**`gp-0x6b5e != 0` AND `assist_state_671a < cal 0xC64FA`**) that r24
> lacks"* · *"**r26 == 0 IFF `gp-0x6b5e != 0`**"*

V150 sets `0xC6136` 0 -> 1, making the state term always true, so the gate reduces to
`gp-0x6b5e != 0`. **That part is correct.**

### 🛑 BUT THE MODEL ALSO SAYS THE GATE DOES NOT FIRE WHERE THE SYMPTOM IS
> *"LEG 1, the GATE — **REVERSED**. r26 == 0 iff gp-0x6b5e != 0, and gp-0x6b5e is a trapezoid LERP on
> gp-0x6bda, a **MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque**. **Hands-off the margin
> sits ~24x above the kill threshold => THE GATE LEAVES r26 LIVE in ordinary driving and most
> strongly live in hands-off creep — exactly where the grinds and the ratchet occur.**"*

⇒ **hands-off, `gp-0x6b5e == 0`**, so the reduced condition `gp-0x6b5e == 0` is **already
satisfied** — r26 is computed exactly as before.
⇒ **[EVIDENCE] V150 changes behaviour ONLY when the driver is applying torque.**
⇒ **V150 is INERT in hands-off creep — the regime of the ratchet and grind #1.** It could only touch
**grind #2** (measured at `tq_avg` 1600–2700, i.e. driver-torque-present).
⇒ **NOT superseded** — it is not harmful and it is a legitimate grind-#2 probe — **but it is
DEMOTED and must not be described as a ratchet lever.**

### ✅ THE FINAL QUEUE, AFTER AUDITING EVERY BUILD AGAINST THE GOLDEN MODEL
```
   FLY      V158   damper, the model's own measured prescription, GATE 2 closed by it
   probe    V148   deadband + gp-0x671E rung -- an INSTRUMENT, explicitly not a fix
   grind#2  V150   inert hands-off; only acts under driver torque
   marginal V151   knee 3000->3600; the relay is already ~99 % unsaturated
   demoted  V152 / V153   GATE-2-OPEN: 0xC40D0 is one of the eight uncertifiable Path-2 coefficients
   SUPERSEDED  V139 · V149 · V154 · V155 · V156 · V157
```

### 🛑 THE AUDIT'S VERDICT ON THIS SESSION'S BUILD WORK
```
   built this session   V139 V148 V149 V150 V151 V152 V153 V154 V155 V156 V157 V158   (12)
   superseded            6      -- two of which would have REMOVED measured fixes
   demoted / inert       4
   survives as a FIX     1      -- V158, the only one designed FROM the golden model
```
⊕ **V149 would have removed Lever B**, the change that flew with *"grinding FIXED"*.
⊕ **V139 was the direction memory records as CAUSING grind #2.**
🛑 **Every failure has one cause: designing from `BUILD-LINEAGE` and fresh decompiles instead of
the GOLDEN MODEL**, which `CLAUDE.md` names as required reading and which already held the
structure, the prescriptions, the strikes, the measured fixes and their gain-dependence.
⭐ **The audit was worth more than the builds it deleted.** **Read `eps_chain_*.py` FIRST.**

